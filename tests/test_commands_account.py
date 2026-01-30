import asyncio
import inspect

import pytest

import handlers.commands as commands

pytestmark = pytest.mark.usefixtures("patched_commands")


def _orig(func):
    return inspect.unwrap(func)


def test_price_list_and_keyboards():
    text = commands._format_price_list()
    assert isinstance(text, str) and text

    keyboard = commands._build_hint_selection_keyboard()
    callbacks = [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "buy_type:easy" in callbacks
    assert "cabinet:account" in callbacks

    qty_keyboard = commands._build_quantity_keyboard("easy")
    callbacks = [b.callback_data for row in qty_keyboard.inline_keyboard for b in row]
    assert "buy_type:back" in callbacks


def test_personal_account_text_name():
    user = type("User", (), {"full_name": "Name", "username": "user"})
    text = commands._personal_account_text(user, 1, 2, 3, 4)
    assert "Name" in text


def test_send_donate_invoice(fake_context):
    asyncio.run(commands._send_donate_invoice(1, fake_context, 5))
    assert fake_context.bot.sent_invoices


def test_get_account_summary_and_personal_account(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/account")
    asyncio.run(_orig(commands.personal_account)(update, fake_context))
    assert update.message.replies

    result = asyncio.run(commands._get_account_summary(1))
    assert result == (0, 0, 0, 0)


def test_buy_hint_command_paths(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/buy_hint")
    fake_context.args = []
    asyncio.run(_orig(commands.buy_hint)(update, fake_context))
    assert update.message.replies

    update = make_update(user_id=1, text="/buy_hint")
    fake_context.args = ["unknown", "1"]
    asyncio.run(_orig(commands.buy_hint)(update, fake_context))
    assert update.message.replies

    update = make_update(user_id=1, text="/buy_hint")
    fake_context.args = ["easy", "abc"]
    asyncio.run(_orig(commands.buy_hint)(update, fake_context))
    assert update.message.replies

    update = make_update(user_id=1, text="/buy_hint")
    fake_context.args = ["easy", "0"]
    asyncio.run(_orig(commands.buy_hint)(update, fake_context))
    assert update.message.replies

    asyncio.run(fake_db.add_balance(1, 10))
    update = make_update(user_id=1, text="/buy_hint")
    fake_context.args = ["easy", "2"]
    asyncio.run(_orig(commands.buy_hint)(update, fake_context))
    assert update.message.replies


def test_buy_hint_callbacks(monkeypatch, fake_context):
    from tests.conftest import FakeCallbackQuery, FakeMessage

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("buy_type:back", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_type_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("buy_type:unknown", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_type_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("buy_type:easy", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_type_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("buy_confirm:easy:bad", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_confirm_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("buy_confirm:unknown:1", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_confirm_callback(update, fake_context))
    assert update.callback_query.message.edits

    async def fake_process(user_id, hint_type, quantity):
        return True, "ok"

    monkeypatch.setattr(commands, "_process_hint_purchase", fake_process)
    update.callback_query = FakeCallbackQuery("buy_confirm:easy:1", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_confirm_callback(update, fake_context))
    assert update.callback_query.message.edits

    async def fake_process_fail(user_id, hint_type, quantity):
        return False, "no"

    monkeypatch.setattr(commands, "_process_hint_purchase", fake_process_fail)
    update.callback_query = FakeCallbackQuery("buy_confirm:easy:1", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_confirm_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("buy_cancel", user_id=1, message=FakeMessage())
    asyncio.run(commands.buy_hint_cancel_callback(update, fake_context))
    assert update.callback_query.message.edits


def test_cabinet_actions(monkeypatch, fake_context):
    from tests.conftest import FakeCallbackQuery, FakeMessage

    called = {"menu": 0}

    async def fake_show_menu(user_id, context):
        called["menu"] += 1

    monkeypatch.setattr(commands, "show_main_menu", fake_show_menu)

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("cabinet:menu", user_id=1, message=FakeMessage())
    asyncio.run(commands.cabinet_action_callback(update, fake_context))
    assert called["menu"] == 1

    update.callback_query = FakeCallbackQuery("cabinet:buy_hints", user_id=1, message=FakeMessage())
    asyncio.run(commands.cabinet_action_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("cabinet:donate", user_id=1, message=FakeMessage())
    asyncio.run(commands.cabinet_action_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("cabinet:account", user_id=1, message=FakeMessage())
    asyncio.run(commands.cabinet_action_callback(update, fake_context))
    assert update.callback_query.message.edits


def test_donate_amount_callback(monkeypatch, fake_context):
    from tests.conftest import FakeCallbackQuery, FakeMessage

    update = type("Update", (), {})()
    update.callback_query = FakeCallbackQuery("donate_amount:bad", user_id=1, message=FakeMessage())
    asyncio.run(commands.donate_amount_callback(update, fake_context))
    assert update.callback_query.message.edits

    update.callback_query = FakeCallbackQuery("donate_amount:5", user_id=1, message=FakeMessage())
    asyncio.run(commands.donate_amount_callback(update, fake_context))
    assert fake_context.bot.sent_invoices
