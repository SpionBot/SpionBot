import asyncio
import logging

import asyncpg

logger = logging.getLogger(__name__)


TRANSIENT_DB_ERRORS = (
    asyncpg.ConnectionDoesNotExistError,
    asyncpg.InterfaceError,
    asyncpg.PostgresConnectionError,
    ConnectionError,
    OSError,
    asyncio.TimeoutError,
)


class _ResilientAcquireContext:
    def __init__(self, owner: "CreateDB", timeout=None):
        self._owner = owner
        self._timeout = timeout
        self._acquire_ctx = None
        self._conn = None

    async def __aenter__(self):
        last_error = None
        for attempt in range(2):
            raw_pool = self._owner._raw_pool
            if raw_pool is None:
                await self._owner.reconnect_pool()
                raw_pool = self._owner._raw_pool
            try:
                self._acquire_ctx = raw_pool.acquire(timeout=self._timeout)
                self._conn = await self._acquire_ctx.__aenter__()
                return self._conn
            except TRANSIENT_DB_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "PostgreSQL acquire failed on attempt %s/2: %s. Recreating pool.",
                    attempt + 1,
                    exc,
                )
                await self._owner.reconnect_pool()
        raise last_error

    async def __aexit__(self, exc_type, exc, tb):
        if self._acquire_ctx is None:
            return False
        return await self._acquire_ctx.__aexit__(exc_type, exc, tb)


class ResilientPool:
    def __init__(self, owner: "CreateDB"):
        self._owner = owner

    def acquire(self, *, timeout=None):
        return _ResilientAcquireContext(self._owner, timeout=timeout)

    async def close(self):
        if self._owner._raw_pool is not None:
            await self._owner._raw_pool.close()

    def __getattr__(self, item):
        raw_pool = self._owner._raw_pool
        if raw_pool is None:
            raise AttributeError(item)
        return getattr(raw_pool, item)


class CreateDB:
    """
    Подключение и создание базы данных
    """

    def __init__(self):
        self.pool = None
        self._raw_pool = None
        self._pool_lock = asyncio.Lock()
        self._dsn = None
        self._min_size = 5
        self._max_size = 20

    async def connect(self, dsn: str, min_size: int = 5, max_size: int = 20):
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        await self._open_pool()
        if self.pool is None:
            self.pool = ResilientPool(self)
        logger.info("Connected to PostgreSQL")
        await self.init_db()

    async def _open_pool(self):
        self._raw_pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=60,
            max_inactive_connection_lifetime=300,
            server_settings={
                "application_name": "spy_game_bot",
                "idle_in_transaction_session_timeout": "60000",
            },
        )
        return self._raw_pool

    async def reconnect_pool(self):
        if not self._dsn:
            raise RuntimeError("Database DSN is not configured")
        async with self._pool_lock:
            try:
                current_pool = self._raw_pool
                if current_pool is not None and not getattr(current_pool, "_closed", False):
                    await current_pool.close()
            except Exception as exc:
                logger.warning("Failed to close broken PostgreSQL pool cleanly: %s", exc)
            self._raw_pool = None
            await self._open_pool()
            logger.info("PostgreSQL pool recreated")

    async def init_db(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id VARCHAR(10) PRIMARY KEY,
                    creator_id BIGINT NOT NULL,
                    mode VARCHAR(20) DEFAULT 'clash',
                    is_public BOOLEAN NOT NULL DEFAULT FALSE,
                    word VARCHAR(100),
                    spy_id BIGINT,
                    spy_count INTEGER NOT NULL DEFAULT 1,
                    spectators BIGINT[] DEFAULT '{}',
                    initial_player_count INTEGER,
                    non_spy_kicks INTEGER NOT NULL DEFAULT 0,
                    card_url TEXT,
                    game_started BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '24 hours'
                )
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS rooms_creator_created_idx ON rooms (creator_id, created_at DESC)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS rooms_public_open_idx ON rooms (is_public, game_started, expires_at, created_at DESC)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS rooms_expires_at_idx ON rooms (expires_at)"
            )
            await conn.execute(
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS spy_count INTEGER NOT NULL DEFAULT 1"
            )

            await conn.execute(
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE"
            )
            await conn.execute(
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS spectators BIGINT[] DEFAULT '{}'"
            )
            await conn.execute(
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS initial_player_count INTEGER"
            )
            await conn.execute(
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS non_spy_kicks INTEGER NOT NULL DEFAULT 0"
            )


            await conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT,
                    room_id VARCHAR(10),
                    role VARCHAR(20),
                    word VARCHAR(100),
                    card_url TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, room_id),
                    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
                )
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS players_room_id_idx ON players (room_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS players_room_joined_idx ON players (room_id, joined_at)"
            )
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_accounts (
                    user_id BIGINT PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    hard_hints INTEGER DEFAULT 0,
                    medium_hints INTEGER DEFAULT 0,
                    easy_hints INTEGER DEFAULT 0,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    spy_games_played INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(
                "ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS games_played INTEGER NOT NULL DEFAULT 0"
            )
            await conn.execute(
                "ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS spy_games_played INTEGER NOT NULL DEFAULT 0"
            )
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    user_id BIGINT PRIMARY KEY,
                    inviter_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS referrals_inviter_id_idx ON referrals (inviter_id)"
            )
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS image_cache (
                    url TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    mode VARCHAR(20),
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS image_cache_cached_at_idx ON image_cache (cached_at)"
            )
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_reports (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    content TEXT,
                    files BYTEA,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Ensure user_reports supports multiple reports per user (migration from older schema).
            cols = await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'user_reports'"
            )
            colset = {row["column_name"] for row in cols}
            has_file = "file" in colset
            has_updated_at = "updated_at" in colset
            if "files" not in colset:
                await conn.execute("ALTER TABLE user_reports ADD COLUMN files BYTEA")
            if "created_at" not in colset:
                await conn.execute(
                    "ALTER TABLE user_reports ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                )
            if "id" not in colset:
                await conn.execute("ALTER TABLE user_reports ADD COLUMN id BIGSERIAL")
            if "user_id" not in colset:
                await conn.execute("ALTER TABLE user_reports ADD COLUMN user_id BIGINT")

            if has_file:
                await conn.execute(
                    "UPDATE user_reports SET files = file WHERE files IS NULL AND file IS NOT NULL"
                )
            if has_updated_at:
                await conn.execute(
                    "UPDATE user_reports SET created_at = updated_at WHERE created_at IS NULL AND updated_at IS NOT NULL"
                )

            await conn.execute("UPDATE user_reports SET id = DEFAULT WHERE id IS NULL")
            await conn.execute("ALTER TABLE user_reports ALTER COLUMN id SET NOT NULL")

            pk = await conn.fetchrow(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'user_reports'::regclass AND contype = 'p'"
            )
            pk_cols = await conn.fetch(
                """
                SELECT a.attname
                FROM pg_constraint c
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
                WHERE c.conrelid = 'user_reports'::regclass AND c.contype = 'p'
                """
            )
            pk_col_names = {row["attname"] for row in pk_cols}
            if pk and "id" not in pk_col_names:
                await conn.execute(
                    f'ALTER TABLE user_reports DROP CONSTRAINT "{pk["conname"]}"'
                )
                pk = None
            if not pk:
                await conn.execute("ALTER TABLE user_reports ADD PRIMARY KEY (id)")

            await conn.execute(
                "CREATE INDEX IF NOT EXISTS user_reports_user_id_idx ON user_reports (user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS user_reports_created_id_idx ON user_reports (created_at DESC, id DESC)"
            )
db_init = CreateDB()
