import asyncio

import handlers.commands as commands


def test_process_hint_purchase_success(monkeypatch, fake_db):
    monkeypatch.setattr(commands, "db", fake_db)

    asyncio.run(fake_db.add_balance(1, 10))
    success, _ = asyncio.run(commands._process_hint_purchase(1, "easy", 2))

    assert success is True
    account = asyncio.run(fake_db.get_user_account(1))
    assert account["easy_hints"] == 2
    assert account["balance"] == 4


def test_process_hint_purchase_insufficient_balance(monkeypatch, fake_db):
    monkeypatch.setattr(commands, "db", fake_db)

    asyncio.run(fake_db.add_balance(2, 1))
    success, _ = asyncio.run(commands._process_hint_purchase(2, "medium", 1))

    assert success is False
