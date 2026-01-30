import asyncio

from telegram.error import BadRequest

from utils import subscription


class BotMember:
    def __init__(self, status):
        self.status = status


def test_is_subscribed_true(monkeypatch):
    async def fake_get_chat_member(chat_id, user_id):
        return BotMember("member")

    monkeypatch.setattr(subscription, "CHANNEL_USERNAME", "@test")
    bot = type("Bot", (), {"get_chat_member": fake_get_chat_member})
    assert asyncio.run(subscription.is_subscribed(bot, 1)) is True


def test_is_subscribed_false_on_bad_request(monkeypatch):
    async def fake_get_chat_member(chat_id, user_id):
        raise BadRequest("fail")

    bot = type("Bot", (), {"get_chat_member": fake_get_chat_member})
    assert asyncio.run(subscription.is_subscribed(bot, 1)) is False


def test_subscribe_keyboard():
    keyboard = subscription.subscribe_keyboard()
    assert keyboard.inline_keyboard
