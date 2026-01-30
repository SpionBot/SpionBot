import asyncio

import utils.decorators as decorators


def test_rate_limiter_blocks_after_limit(monkeypatch):
    limiter = decorators.RateLimiter(max_requests=2, period=10.0)

    monkeypatch.setattr(decorators.time, "time", lambda: 0.0)

    assert asyncio.run(limiter.is_allowed(1)) is True
    assert asyncio.run(limiter.is_allowed(1)) is True
    assert asyncio.run(limiter.is_allowed(1)) is False

    monkeypatch.setattr(decorators.time, "time", lambda: 11.0)
    assert asyncio.run(limiter.is_allowed(1)) is True


def test_subscription_required_blocks_when_not_subscribed(monkeypatch, make_update, fake_context):
    async def always_false(bot, user_id):
        return False

    monkeypatch.setattr(decorators, "is_subscribed", always_false)

    called = {"value": False}

    @decorators.subscription_required
    async def handler(update, context):
        called["value"] = True

    update = make_update(user_id=100, text="/start")
    asyncio.run(handler(update, fake_context))

    assert called["value"] is False
    assert update.message.replies


def test_subscription_required_allows_when_subscribed(monkeypatch, make_update, fake_context):
    async def always_true(bot, user_id):
        return True

    monkeypatch.setattr(decorators, "is_subscribed", always_true)

    called = {"value": False}

    @decorators.subscription_required
    async def handler(update, context):
        called["value"] = True

    update = make_update(user_id=101, text="/start")
    asyncio.run(handler(update, fake_context))

    assert called["value"] is True
