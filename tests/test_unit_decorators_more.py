import asyncio

import utils.decorators as decorators
from utils.decorators import BotDecorators, RateLimiter, RoomLocks


def test_private_chat_only_blocks(make_update, fake_context, fake_db):
    decorators = BotDecorators(fake_db)
    called = {"value": False}

    @decorators.private_chat_only()
    async def handler(update, context):
        called["value"] = True

    update = make_update(user_id=1, text="/x", chat_type="group")
    asyncio.run(handler(update, fake_context))
    assert called["value"] is False
    assert update.message.replies


def test_creator_only_blocks_and_allows(make_update, fake_context, fake_db):
    decorators = BotDecorators(fake_db)

    @decorators.creator_only()
    async def handler(update, context):
        return "ok"

    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {"id": "1", "creator_id": 2, "game_started": False}
    fake_db.room_players["1"] = [1, 2]
    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert update.message.replies

    fake_db.rooms.pop("1", None)
    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False}
    update = make_update(user_id=1, text="/x", chat_type="private")
    result = asyncio.run(handler(update, fake_context))
    assert result == "ok"


def test_game_not_started_blocks_when_started(make_update, fake_context, fake_db):
    decorators = BotDecorators(fake_db)

    @decorators.game_not_started()
    async def handler(update, context):
        return "ok"

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": True}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"]["game_started"] = False
    update = make_update(user_id=1, text="/x", chat_type="private")
    result = asyncio.run(handler(update, fake_context))
    assert result == "ok"


def test_room_lock_runs(make_update, fake_context, fake_db):
    decorators = BotDecorators(fake_db)
    called = {"value": False}

    @decorators.room_lock()
    async def handler(update, context):
        called["value"] = True

    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert called["value"] is True


def test_game_command_combines_decorators(make_update, fake_context, fake_db):
    decorators = BotDecorators(fake_db)
    called = {"value": False}

    @decorators.game_command()
    async def handler(update, context):
        called["value"] = True

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert called["value"] is True


def test_room_lock_exception_path(make_update, fake_context, fake_db):
    decorators = BotDecorators(fake_db)

    @decorators.room_lock()
    async def handler(update, context):
        raise ValueError("boom")

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/x", chat_type="private")
    try:
        asyncio.run(handler(update, fake_context))
    except ValueError:
        pass


def test_rate_limiter_cleanup_and_warning(monkeypatch, make_update, fake_context, fake_db):
    limiter = RateLimiter(max_requests=1, period=10.0)
    monkeypatch.setattr(decorators.time, "time", lambda: 0.0)
    asyncio.run(limiter.is_allowed(1))
    limiter._requests[2].append(-1000)
    limiter.cleanup_old_users(max_inactive_hours=0)

    decorators_obj = BotDecorators(fake_db)
    rate_limit = decorators_obj.rate_limit(max_requests=1, period=10.0)

    @rate_limit
    async def handler(update, context):
        return "ok"

    monkeypatch.setattr(decorators.time, "time", lambda: 10.0)
    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    asyncio.run(handler(update, fake_context))
    assert update.message.replies

    async def raise_reply(*args, **kwargs):
        raise RuntimeError("fail")

    update.message.reply_text = raise_reply
    monkeypatch.setattr(decorators.time, "time", lambda: 20.0)
    asyncio.run(handler(update, fake_context))


def test_game_not_started_missing_room(make_update, fake_context, fake_db):
    decorators_obj = BotDecorators(fake_db)

    @decorators_obj.game_not_started()
    async def handler(update, context):
        return "ok"

    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert update.message.replies

    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/x", chat_type="private")
    asyncio.run(handler(update, fake_context))
    assert update.message.replies


def test_protected_command_allows(make_update, fake_context, fake_db):
    decorators_obj = BotDecorators(fake_db)

    @decorators_obj.protected_command()
    async def handler(update, context):
        return "ok"

    update = make_update(user_id=1, text="/x", chat_type="private")
    result = asyncio.run(handler(update, fake_context))
    assert result == "ok"


def test_roomlocks_cleanup_pass():
    locks = RoomLocks()
    locks.cleanup()
