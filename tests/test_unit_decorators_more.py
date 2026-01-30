import asyncio

from utils.decorators import BotDecorators


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

    fake_db.rooms["1"]["creator_id"] = 1
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
