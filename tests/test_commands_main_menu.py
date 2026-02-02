import asyncio

import pytest

import handlers.commands as commands

pytestmark = pytest.mark.usefixtures("patched_commands")


def test_show_main_menu_with_and_without_room(patched_commands, fake_db, fake_context):
    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "mode": commands.MODE_DOTA}
    fake_db.room_players["1"] = [1]

    asyncio.run(commands.show_main_menu(1, fake_context))
    assert fake_context.bot.sent_messages

    fake_context.bot.sent_messages.clear()
    fake_db.room_players.clear()
    asyncio.run(commands.show_main_menu(1, fake_context))
    assert fake_context.bot.sent_messages


def test_start_subscription_gate(monkeypatch, fake_context, make_update):
    async def always_false(bot, user_id):
        return False

    monkeypatch.setattr(commands, "is_subscribed", always_false)
    update = make_update(user_id=1, text="/start")
    asyncio.run(commands.start(update, fake_context))
    assert update.message.replies


def test_start_subscribed_calls_menu(monkeypatch, fake_context, make_update):
    async def always_true(bot, user_id):
        return True

    called = {"value": False}

    async def fake_menu(user_id, context):
        called["value"] = True

    monkeypatch.setattr(commands, "is_subscribed", always_true)
    monkeypatch.setattr(commands, "show_main_menu", fake_menu)
    update = make_update(user_id=1, text="/start")
    asyncio.run(commands.start(update, fake_context))
    assert called["value"] is True


def test_check_subscription_callback_paths(monkeypatch, fake_context):
    async def always_true(bot, user_id):
        return True

    async def always_false(bot, user_id):
        return False

    called = {"value": False}

    async def fake_show_main_menu(user_id, context):
        called["value"] = True

    from tests.conftest import FakeCallbackQuery, FakeMessage

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("check_subscription", user_id=1, message=FakeMessage())

    monkeypatch.setattr(commands, "is_subscribed", always_true)
    monkeypatch.setattr(commands, "show_main_menu", fake_show_main_menu)
    asyncio.run(commands.check_subscription_callback(update, fake_context))
    assert called["value"] is True

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("check_subscription", user_id=1, message=FakeMessage())
    monkeypatch.setattr(commands, "is_subscribed", always_false)
    asyncio.run(commands.check_subscription_callback(update, fake_context))
    assert update.callback_query.message.edits

    def raise_edit(*args, **kwargs):
        from telegram.error import BadRequest

        raise BadRequest("fail")

    update = type("Update", (), {})()
    message = FakeMessage()
    message.edit_text = raise_edit
    update.callback_query = FakeCallbackQuery("check_subscription", user_id=1, message=message)
    monkeypatch.setattr(commands, "is_subscribed", always_false)
    asyncio.run(commands.check_subscription_callback(update, fake_context))


def test_single_mode_reply(monkeypatch, fake_context, make_update):
    update = make_update(user_id=1, text="/single")
    asyncio.run(commands.single_mode(update, fake_context))
    assert update.message.replies


def test_error_handler_swallows_exceptions(make_update, fake_context):
    update = make_update(user_id=1, text="x")
    update.effective_chat = type("Chat", (), {"send_message": lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail"))})()
    fake_context.error = RuntimeError("boom")
    asyncio.run(commands.error_handler(update, fake_context))


def test_donate_and_precheckout(make_update, fake_context, make_precheckout_update):
    update = make_update(user_id=1, text="/donate")
    asyncio.run(commands.donate(update, fake_context))
    assert fake_context.bot.sent_invoices

    update = make_precheckout_update(user_id=1)
    asyncio.run(commands.precheckout_callback(update, fake_context))
    assert update.pre_checkout_query.answered


def test_successful_payment_callback_updates_balance(patched_commands, fake_db, make_payment_update, fake_context):
    fake_db.accounts[1] = {"user_id": 1, "balance": 0, "hard_hints": 0, "medium_hints": 0, "easy_hints": 0}
    update = make_payment_update(user_id=1, total_amount=250)
    asyncio.run(commands.successful_payment_callback(update, fake_context))
    assert update.message.replies
