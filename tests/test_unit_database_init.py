import asyncio

from database.init import CreateDB
from tests.conftest import FakeConn, FakePool


def test_connect_creates_pool_and_inits(monkeypatch):
    conn = FakeConn()
    pool = FakePool(conn)

    async def fake_create_pool(*args, **kwargs):
        return pool

    import database.init as db_init

    monkeypatch.setattr(db_init.asyncpg, "create_pool", fake_create_pool)

    db = CreateDB()
    asyncio.run(db.connect("dsn://test", min_size=1, max_size=2))
    assert db.pool is pool
    assert len(conn.executed) == 3
