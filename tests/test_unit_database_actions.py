import asyncio

import asyncpg

from database.actions import ButtonCommand
from tests.conftest import FakeConn, FakePool


def test_create_room_success_and_unique_violation():
    conn = FakeConn(fetchval_results=[0])
    cmd = ButtonCommand(FakePool(conn))
    assert asyncio.run(cmd.create_room("1", 10, "clash")) is True

    async def raise_unique(*args, **kwargs):
        raise asyncpg.UniqueViolationError()

    conn_fail = FakeConn()
    conn_fail.execute = raise_unique
    cmd_fail = ButtonCommand(FakePool(conn_fail))
    assert asyncio.run(cmd_fail.create_room("1", 10, "clash")) is False


def test_add_player_to_room_limits_and_errors():
    conn_full = FakeConn(fetchval_results=[15])
    cmd_full = ButtonCommand(FakePool(conn_full))
    assert asyncio.run(cmd_full.add_player_to_room(1, "room")) is False

    async def raise_error(*args, **kwargs):
        raise RuntimeError("db error")

    conn_err = FakeConn(fetchval_results=[0])
    conn_err.execute = raise_error
    cmd_err = ButtonCommand(FakePool(conn_err))
    assert asyncio.run(cmd_err.add_player_to_room(1, "room")) is False


def test_get_room_and_players():
    conn = FakeConn(
        fetchrow_results=[{"id": "1", "creator_id": 5}],
        fetch_results=[[{"user_id": 1}, {"user_id": 2}]],
    )
    cmd = ButtonCommand(FakePool(conn))
    room = asyncio.run(cmd.get_room("1"))
    assert room["id"] == "1"
    players = asyncio.run(cmd.get_room_players("1"))
    assert players == [1, 2]


def test_get_user_room_and_creator():
    conn = FakeConn(fetchrow_results=[{"room_id": "99"}, {"creator_id": 7}])
    cmd = ButtonCommand(FakePool(conn))
    assert asyncio.run(cmd.get_user_room(1)) == "99"
    assert asyncio.run(cmd.get_room_creator("99")) == 7


def test_update_and_reset_room_game_state():
    conn = FakeConn()
    cmd = ButtonCommand(FakePool(conn))
    asyncio.run(cmd.update_room_game_state("1", "word", 2, "url"))
    asyncio.run(cmd.reset_room_game("1"))
    assert len(conn.executed) == 3


def test_stats_and_cache_helpers():
    conn = FakeConn(fetchval_results=[3, 2, 10], fetchrow_results=[{"file_id": "f1"}])
    cmd = ButtonCommand(FakePool(conn))
    stats = asyncio.run(cmd.get_all_rooms_stats())
    assert stats["total_rooms"] == 3
    assert asyncio.run(cmd.get_cached_image("url")) == "f1"
    asyncio.run(cmd.cache_image("url", "file", "mode"))
    assert conn.executed


def test_user_account_and_balance():
    conn = FakeConn(fetchrow_results=[{"user_id": 1, "balance": 5}])
    cmd = ButtonCommand(FakePool(conn))
    asyncio.run(cmd.ensure_user_account(1))
    account = asyncio.run(cmd.get_user_account(1))
    assert account["balance"] == 5

    conn_balance = FakeConn(fetchrow_results=[{"balance": 10}])
    cmd_balance = ButtonCommand(FakePool(conn_balance))
    assert asyncio.run(cmd_balance.add_balance(1, 0)) is None
    assert asyncio.run(cmd_balance.add_balance(1, 5)) == 10


def test_purchase_hints_paths():
    conn = FakeConn(fetchrow_results=[None, {"balance": 1, "hard_hints": 1, "medium_hints": 0, "easy_hints": 0}])
    cmd = ButtonCommand(FakePool(conn))

    assert asyncio.run(cmd.purchase_hints(1, -1)) is None
    assert asyncio.run(cmd.purchase_hints(1, 5)) is None
    result = asyncio.run(cmd.purchase_hints(1, 1, hard=1))
    assert result["hard_hints"] == 1


def test_misc_db_methods_execute():
    conn = FakeConn(fetchrow_results=[{"user_id": 1, "room_id": "1"}])
    cmd = ButtonCommand(FakePool(conn))
    asyncio.run(cmd.delete_room("1"))
    asyncio.run(cmd.update_room_mode("1", "mode"))
    asyncio.run(cmd.remove_player_from_room(1, "1"))
    asyncio.run(cmd.remove_player_from_all_rooms(1))
    player = asyncio.run(cmd.get_player_data(1, "1"))
    assert player["user_id"] == 1
    asyncio.run(cmd.update_player_role(1, "1", "role", "word", "url"))
    asyncio.run(cmd.transfer_room_ownership("1", 2))
    asyncio.run(cmd.cleanup_old_rooms())
    asyncio.run(cmd.cleanup_image_cache())
    assert conn.executed
