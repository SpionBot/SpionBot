import asyncio

import handlers.commands as commands


def test_e2e_create_join_start_game(
    monkeypatch, patched_commands, fake_context, make_update
):
    monkeypatch.setattr(commands.random, "randint", lambda a, b: 1234)
    monkeypatch.setattr(
        commands,
        "get_words_and_cards_by_mode",
        lambda mode: (["ALPHA"], {"ALPHA": "http://card"}),
    )

    def choice(seq):
        if seq and isinstance(seq[0], str):
            return "ALPHA"
        return seq[0]

    monkeypatch.setattr(commands.random, "choice", choice)

    creator_update = make_update(user_id=1, text="/create")
    commands.SINGLE_MODE_SESSIONS.clear()

    asyncio.run(commands.create_room(creator_update, fake_context))

    assert creator_update.message.replies
    assert "1234" in creator_update.message.replies[0]["text"]

    joiner_update = make_update(user_id=2, text="/join 1234")
    fake_context.args = ["1234"]
    asyncio.run(commands.join_room(joiner_update, fake_context))

    assert joiner_update.message.replies
    assert "1234" in joiner_update.message.replies[0]["text"]

    fake_context.args = []
    asyncio.run(commands.start_game(creator_update, fake_context))

    room = patched_commands.db.rooms["1234"]
    assert room["game_started"] is True
    assert room["word"] == "ALPHA"
    assert room["spy_id"] == 1

    assert len(fake_context.bot.sent_photos) == 2
    assert len(fake_context.bot.sent_messages) >= 2
