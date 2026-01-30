import handlers.commands as commands


def test_build_single_mode_selection_keyboard_contains_all_options():
    keyboard = commands._build_single_mode_selection_keyboard()
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    for count in commands.SINGLE_MODE_PLAYER_OPTIONS:
        assert f"single:select:{count}" in callbacks
    assert "single:cancel" in callbacks


def test_build_single_mode_caption_hides_word_when_not_revealed():
    session = commands.SingleModeSession(
        chat_id=1,
        message_id=1,
        word="ALPHA",
        card_url="",
        player_count=3,
        spy_index=2,
        current_index=0,
        mode="test",
        revealed=False,
    )
    caption = commands._build_single_mode_caption(session)
    assert "ALPHA" not in caption


def test_build_single_mode_caption_reveals_word_for_non_spy():
    session = commands.SingleModeSession(
        chat_id=1,
        message_id=1,
        word="ALPHA",
        card_url="",
        player_count=3,
        spy_index=2,
        current_index=0,
        mode="test",
        revealed=True,
    )
    caption = commands._build_single_mode_caption(session)
    assert "ALPHA" in caption


def test_build_single_mode_caption_hides_word_for_spy():
    session = commands.SingleModeSession(
        chat_id=1,
        message_id=1,
        word="ALPHA",
        card_url="",
        player_count=3,
        spy_index=1,
        current_index=1,
        mode="test",
        revealed=True,
    )
    caption = commands._build_single_mode_caption(session)
    assert "ALPHA" not in caption


def test_create_single_mode_session_uses_words_and_random(monkeypatch):
    monkeypatch.setattr(
        commands,
        "get_words_and_cards_by_mode",
        lambda mode: (["ALPHA"], {"ALPHA": "URL"}),
    )
    monkeypatch.setattr(commands.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(commands.random, "randrange", lambda n: 1)

    session = commands._create_single_mode_session(3, "test")

    assert session.word == "ALPHA"
    assert session.card_url == "URL"
    assert session.spy_index == 1
    assert session.player_count == 3
