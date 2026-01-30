import asyncio

import pytest

import handlers.commands as commands
from handlers.button import get_main_keyboard, get_room_keyboard

pytestmark = pytest.mark.usefixtures("patched_commands")


def test_handle_text_message_dispatch(monkeypatch, fake_context, make_update, fake_db):
    called = {}

    async def make_handler(name):
        async def _handler(update, context):
            called[name] = True

        return _handler

    monkeypatch.setattr(commands, "create_room", asyncio.run(make_handler("create")))
    monkeypatch.setattr(commands, "join_room", asyncio.run(make_handler("join")))
    monkeypatch.setattr(commands, "start_game", asyncio.run(make_handler("start_game")))
    monkeypatch.setattr(commands, "restart_game", asyncio.run(make_handler("restart")))
    monkeypatch.setattr(commands, "rules", asyncio.run(make_handler("rules")))
    monkeypatch.setattr(commands, "single_mode", asyncio.run(make_handler("single")))
    monkeypatch.setattr(commands, "show_cards", asyncio.run(make_handler("cards")))
    monkeypatch.setattr(commands, "get_word", asyncio.run(make_handler("word")))
    monkeypatch.setattr(commands, "show_players", asyncio.run(make_handler("players")))
    monkeypatch.setattr(commands, "leave_room", asyncio.run(make_handler("leave")))
    monkeypatch.setattr(commands, "personal_account", asyncio.run(make_handler("account")))
    monkeypatch.setattr(commands, "start", asyncio.run(make_handler("start")))

    main_keyboard = get_main_keyboard().keyboard
    room_keyboard = get_room_keyboard().keyboard

    texts = [
        (main_keyboard[0][0].text, "create"),
        (main_keyboard[0][1].text, "join"),
        (room_keyboard[0][0].text, "start_game"),
        (room_keyboard[0][1].text, "restart"),
        (main_keyboard[1][1].text, "rules"),
        (main_keyboard[2][0].text, "single"),
        ("🎴 Все карты", "cards"),
        ("👤 Моя роль/слово", "word"),
        ("👥 Игроки в комнате", "players"),
        (room_keyboard[1][0].text, "leave"),
        (main_keyboard[1][0].text, "account"),
    ]

    for text, name in texts:
        update = make_update(user_id=1, text=text)
        asyncio.run(commands.handle_text_message(update, fake_context))
        assert called.get(name) is True

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="ℹ️ Помощь")
    asyncio.run(commands.handle_text_message(update, fake_context))
    assert called.get("start") is True

    update = make_update(user_id=1, text="1234")
    asyncio.run(commands.handle_text_message(update, fake_context))
    assert called.get("join") is True

    update = make_update(user_id=1, text="unknown")
    asyncio.run(commands.handle_text_message(update, fake_context))
    assert update.message.replies
