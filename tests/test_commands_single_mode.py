import asyncio
import inspect

import pytest
from telegram.error import BadRequest

import handlers.commands as commands
from handlers.commands import SingleModeSession

pytestmark = pytest.mark.usefixtures("patched_commands")


def _orig(func):
    return inspect.unwrap(func)


def test_get_single_mode_photo_variants(monkeypatch):
    session = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="http://card",
        player_count=2,
        spy_index=0,
        current_index=0,
        mode="mode",
        revealed=True,
    )
    assert commands._get_single_mode_photo(session) == commands.SINGLE_MODE_SPY_IMAGE_URL

    session.current_index = 1
    assert commands._get_single_mode_photo(session) == "http://card"

    session.revealed = False
    session.back_card_file_id = "file_id"
    assert commands._get_single_mode_photo(session) == "file_id"

    session.back_card_file_id = None
    monkeypatch.setattr(commands, "BACK_CARD_BYTES", b"data")
    photo = commands._get_single_mode_photo(session)
    assert photo is not None

    monkeypatch.setattr(commands, "BACK_CARD_BYTES", None)
    assert commands._get_single_mode_photo(session) == commands.SINGLE_MODE_PLACEHOLDER_URL


def test_build_single_mode_keyboard_spy_label():
    session = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="",
        player_count=2,
        spy_index=0,
        current_index=0,
        mode="mode",
        revealed=True,
    )
    keyboard = commands._build_single_mode_keyboard(session)
    center_text = keyboard.inline_keyboard[0][1].text
    assert "шпион" in center_text.lower()


def test_create_single_mode_session_empty(monkeypatch):
    monkeypatch.setattr(commands, "get_words_and_cards_by_mode", lambda mode: ([], {}))
    assert commands._create_single_mode_session(2, "mode") is None


def test_send_single_mode_card_success_and_fallback(monkeypatch, fake_context):
    session = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="http://card",
        player_count=2,
        spy_index=0,
        current_index=0,
        mode="mode",
        revealed=False,
    )
    result = asyncio.run(commands._send_single_mode_card(1, fake_context, session))
    assert session.back_card_file_id
    assert result is not None

    async def raise_badrequest(*args, **kwargs):
        raise BadRequest("fail")

    monkeypatch.setattr(fake_context.bot, "send_photo", raise_badrequest)
    asyncio.run(commands._send_single_mode_card(1, fake_context, session))
    assert fake_context.bot.sent_messages


def test_update_single_mode_message_fallback(monkeypatch):
    session = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="http://card",
        player_count=2,
        spy_index=0,
        current_index=0,
        mode="mode",
        revealed=False,
    )

    from tests.conftest import FakeCallbackQuery, FakeMessage

    message = FakeMessage()
    query = FakeCallbackQuery("single:noop", user_id=1, message=message)

    async def raise_badrequest(*args, **kwargs):
        raise BadRequest("fail")

    monkeypatch.setattr(query, "edit_message_media", raise_badrequest)
    asyncio.run(commands._update_single_mode_message(query, session))
    assert message.edits

    query = FakeCallbackQuery("single:noop", user_id=1, message=FakeMessage())
    query.message = None
    asyncio.run(commands._update_single_mode_message(query, session))

    async def raise_caption(*args, **kwargs):
        raise BadRequest("fail")

    message = FakeMessage()
    message.edit_caption = raise_caption
    query = FakeCallbackQuery("single:noop", user_id=1, message=message)
    monkeypatch.setattr(query, "edit_message_media", raise_badrequest)
    asyncio.run(commands._update_single_mode_message(query, session))


def test_single_mode_callback_select_and_cancel(monkeypatch, fake_context):
    commands.SINGLE_MODE_SESSIONS.clear()

    def fake_create(count, mode):
        return SingleModeSession(
            chat_id=0,
            message_id=0,
            word="WORD",
            card_url="",
            player_count=count,
            spy_index=0,
            current_index=0,
            mode=mode,
        )

    class Msg:
        def __init__(self):
            self.message_id = 42

    async def fake_send_card(user_id, context, session):
        return Msg()

    monkeypatch.setattr(commands, "_create_single_mode_session", fake_create)
    monkeypatch.setattr(commands, "_send_single_mode_card", fake_send_card)

    from tests.conftest import FakeCallbackQuery, FakeMessage

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("single:select:2", user_id=1, message=FakeMessage())

    asyncio.run(commands.single_mode_callback(update, fake_context))
    assert commands.SINGLE_MODE_SESSIONS[1].message_id == 42

    async def raise_delete():
        raise BadRequest("fail")

    msg = FakeMessage()
    msg.delete = raise_delete
    update.callback_query = FakeCallbackQuery("single:select:2", user_id=1, message=msg)
    asyncio.run(commands.single_mode_callback(update, fake_context))

    async def raise_edit(*args, **kwargs):
        raise BadRequest("fail")

    msg = FakeMessage()
    msg.edit_text = raise_edit
    update.callback_query = FakeCallbackQuery("single:cancel", user_id=1, message=msg)
    asyncio.run(commands.single_mode_callback(update, fake_context))


def test_single_mode_callback_actions(monkeypatch, fake_context):
    commands.SINGLE_MODE_SESSIONS.clear()
    session = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="",
        player_count=2,
        spy_index=0,
        current_index=0,
        mode="mode",
    )
    commands.SINGLE_MODE_SESSIONS[1] = session

    called = {"updates": 0, "show_menu": 0}

    async def fake_update_message(query, sess):
        called["updates"] += 1

    async def fake_show_menu(user_id, context):
        called["show_menu"] += 1

    monkeypatch.setattr(commands, "_update_single_mode_message", fake_update_message)
    monkeypatch.setattr(commands, "show_main_menu", fake_show_menu)

    from tests.conftest import FakeCallbackQuery, FakeMessage

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("single:prev", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    update.callback_query = FakeCallbackQuery("single:next", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    update.callback_query = FakeCallbackQuery("single:reveal", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    def fake_create(count, mode):
        return SingleModeSession(
            chat_id=0,
            message_id=0,
            word="NEW",
            card_url="",
            player_count=count,
            spy_index=0,
            current_index=0,
            mode=mode,
        )

    monkeypatch.setattr(commands, "_create_single_mode_session", fake_create)
    update.callback_query = FakeCallbackQuery("single:restart", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    update.callback_query = FakeCallbackQuery("single:exit", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    assert called["updates"] >= 3
    assert called["show_menu"] == 1


def test_single_mode_callback_invalid_and_missing(monkeypatch, fake_context):
    commands.SINGLE_MODE_SESSIONS.clear()

    update = type("Update", (), {})()
    update.callback_query = None
    asyncio.run(commands.single_mode_callback(update, fake_context))

    from tests.conftest import FakeCallbackQuery, FakeMessage

    update.callback_query = FakeCallbackQuery("single", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    update.callback_query = FakeCallbackQuery("single:select", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    update.callback_query = FakeCallbackQuery("single:select:abc", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))

    update.callback_query = FakeCallbackQuery("single:select:99", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))
    assert update.callback_query.answered

    monkeypatch.setattr(commands, "_create_single_mode_session", lambda *_: None)
    update.callback_query = FakeCallbackQuery("single:select:2", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))
    assert update.callback_query.answered

    update.callback_query = FakeCallbackQuery("single:prev", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))
    assert update.callback_query.answered

    commands.SINGLE_MODE_SESSIONS[1] = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="",
        player_count=0,
        spy_index=0,
        current_index=0,
        mode="mode",
    )
    update.callback_query = FakeCallbackQuery("single:prev", user_id=1, message=FakeMessage())
    asyncio.run(commands.single_mode_callback(update, fake_context))
    assert update.callback_query.answered

    async def raise_delete():
        raise BadRequest("fail")

    message = FakeMessage()
    message.delete = raise_delete
    commands.SINGLE_MODE_SESSIONS[1] = SingleModeSession(
        chat_id=1,
        message_id=1,
        word="WORD",
        card_url="",
        player_count=2,
        spy_index=0,
        current_index=0,
        mode="mode",
    )
    update.callback_query = FakeCallbackQuery("single:exit", user_id=1, message=message)
    asyncio.run(commands.single_mode_callback(update, fake_context))
