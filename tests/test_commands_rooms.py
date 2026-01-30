import asyncio
import inspect
from datetime import datetime

import pytest

import handlers.commands as commands

pytestmark = pytest.mark.usefixtures("patched_commands")


def _orig(func):
    return inspect.unwrap(func)


def test_create_room_success(monkeypatch, fake_db, fake_context, make_update):
    monkeypatch.setattr(commands.random, "randint", lambda a, b: 1234)
    update = make_update(user_id=1, text="/create")
    asyncio.run(_orig(commands.create_room)(update, fake_context))
    assert update.message.replies
    assert "1234" in update.message.replies[0]["text"]


def test_create_room_failure_when_taken(monkeypatch, fake_db, fake_context, make_update):
    async def always_room(room_id):
        return {"id": room_id}

    monkeypatch.setattr(fake_db, "get_room", always_room)
    update = make_update(user_id=1, text="/create")
    asyncio.run(_orig(commands.create_room)(update, fake_context))
    assert update.message.replies


def test_join_room_prompt_and_usage(fake_context, make_update):
    update = make_update(user_id=1, text="📎 Присоединиться")
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies

    update = make_update(user_id=1, text="not-id")
    fake_context.args = []
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies


def test_join_room_not_found(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/join 1234")
    fake_context.args = ["1234"]
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies


def test_join_room_game_started(fake_db, fake_context, make_update):
    fake_db.rooms["1234"] = {"id": "1234", "creator_id": 1, "game_started": True}
    fake_db.room_players["1234"] = [1]
    update = make_update(user_id=2, text="/join 1234")
    fake_context.args = ["1234"]
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies


def test_join_room_already_in_room(fake_db, fake_context, make_update):
    fake_db.rooms["1234"] = {"id": "1234", "creator_id": 1, "game_started": False}
    fake_db.room_players["1234"] = [2]
    update = make_update(user_id=2, text="/join 1234")
    fake_context.args = ["1234"]
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies


def test_join_room_in_other_room(fake_db, fake_context, make_update):
    fake_db.rooms["1111"] = {"id": "1111", "creator_id": 1, "game_started": False}
    fake_db.rooms["2222"] = {"id": "2222", "creator_id": 2, "game_started": False}
    fake_db.room_players["1111"] = [2]
    fake_db.room_players["2222"] = []

    update = make_update(user_id=2, text="/join 2222")
    fake_context.args = ["2222"]
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies


def test_join_room_full(fake_db, fake_context, make_update):
    fake_db.rooms["1234"] = {"id": "1234", "creator_id": 1, "game_started": False}
    fake_db.room_players["1234"] = list(range(1, 16))
    update = make_update(user_id=99, text="/join 1234")
    fake_context.args = ["1234"]
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies


def test_join_room_success(fake_db, fake_context, make_update):
    fake_db.rooms["1234"] = {"id": "1234", "creator_id": 1, "game_started": False}
    fake_db.room_players["1234"] = [1]
    update = make_update(user_id=2, text="/join 1234")
    fake_context.args = ["1234"]
    asyncio.run(_orig(commands.join_room)(update, fake_context))
    assert update.message.replies
    assert fake_context.bot.sent_messages


def test_start_game_no_room(fake_context, make_update):
    update = make_update(user_id=1, text="/startgame")
    asyncio.run(_orig(commands.start_game)(update, fake_context))
    assert update.message.replies


def test_start_game_room_missing(fake_db, fake_context, make_update):
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/startgame")
    asyncio.run(_orig(commands.start_game)(update, fake_context))
    assert update.message.replies


def test_start_game_not_enough_players(fake_db, fake_context, make_update):
    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/startgame")
    asyncio.run(_orig(commands.start_game)(update, fake_context))
    assert update.message.replies


def test_start_game_success_cached_and_uncached(monkeypatch, fake_db, fake_context, make_update):
    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1, 2]
    monkeypatch.setattr(
        commands,
        "get_words_and_cards_by_mode",
        lambda mode: (["ALPHA"], {"ALPHA": "http://card"}),
    )

    def choice(seq):
        return seq[0]

    monkeypatch.setattr(commands.random, "choice", choice)

    spy_url = "https://i.pinimg.com/originals/41/15/70/4115707ee950d4b0aba69664f7986ae5.png"
    fake_db.image_cache[spy_url] = "spy_file"
    fake_db.image_cache["http://card"] = "card_file"

    update = make_update(user_id=1, text="/startgame")
    asyncio.run(_orig(commands.start_game)(update, fake_context))
    assert fake_context.bot.sent_photos

    fake_context.bot.sent_photos.clear()
    fake_db.image_cache.clear()
    asyncio.run(_orig(commands.start_game)(update, fake_context))
    assert fake_db.image_cache


def test_start_game_card_without_image(monkeypatch, fake_db, fake_context, make_update):
    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1, 2]
    monkeypatch.setattr(
        commands, "get_words_and_cards_by_mode", lambda mode: (["ALPHA"], {"ALPHA": ""})
    )
    monkeypatch.setattr(commands.random, "choice", lambda seq: seq[0])
    update = make_update(user_id=1, text="/startgame")
    asyncio.run(_orig(commands.start_game)(update, fake_context))
    assert fake_context.bot.sent_messages


def test_restart_game_paths(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/restart")
    asyncio.run(_orig(commands.restart_game)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": True, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1, 2]
    update = make_update(user_id=1, text="/restart")
    asyncio.run(_orig(commands.restart_game)(update, fake_context))
    assert update.message.replies


def test_get_word_paths(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/word")
    asyncio.run(_orig(commands.get_word)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/word")
    asyncio.run(_orig(commands.get_word)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"]["game_started"] = True
    update = make_update(user_id=1, text="/word")
    asyncio.run(_orig(commands.get_word)(update, fake_context))
    assert update.message.replies

    fake_db.player_data[(1, "1")] = {"role": "шпион", "word": None, "card_url": None}
    update = make_update(user_id=1, text="/word")
    asyncio.run(_orig(commands.get_word)(update, fake_context))
    assert fake_context.bot.sent_photos

    fake_context.bot.sent_photos.clear()
    fake_db.player_data[(1, "1")] = {"role": "мирный", "word": "ALPHA", "card_url": ""}
    update = make_update(user_id=1, text="/word")
    asyncio.run(_orig(commands.get_word)(update, fake_context))
    assert update.message.replies


def test_show_players_and_leave_room(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/players")
    asyncio.run(_orig(commands.show_players)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1, 2]
    fake_db.player_data[(1, "1")] = {"role": "мирный"}
    fake_db.player_data[(2, "1")] = {"role": None}
    update = make_update(user_id=1, text="/players")
    asyncio.run(_orig(commands.show_players)(update, fake_context))
    assert update.message.replies

    update = make_update(user_id=1, text="/leave")
    asyncio.run(_orig(commands.leave_room)(update, fake_context))
    assert update.message.replies


def test_rules_show_cards_and_stats(monkeypatch, fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/rules")
    asyncio.run(_orig(commands.rules)(update, fake_context))
    assert update.message.replies

    monkeypatch.setattr(
        commands,
        "get_words_and_cards_by_mode",
        lambda mode: (["A", "B"], {"A": "url", "B": ""}),
    )
    update = make_update(user_id=1, text="/cards")
    asyncio.run(_orig(commands.show_cards)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {
        "id": "1",
        "creator_id": 1,
        "game_started": True,
        "mode": commands.DEFAULT_MODE,
        "created_at": datetime(2024, 1, 1, 12, 0),
    }
    fake_db.room_players["1"] = [1]
    fake_db.player_data[(1, "1")] = {"role": "мирный"}
    update = make_update(user_id=1, text="/stats")
    asyncio.run(_orig(commands.show_stats)(update, fake_context))
    assert update.message.replies

    fake_db.room_players.clear()
    update = make_update(user_id=1, text="/stats")
    asyncio.run(_orig(commands.show_stats)(update, fake_context))
    assert update.message.replies


def test_set_mode_clash_dota(fake_db, fake_context, make_update):
    update = make_update(user_id=1, text="/mode")
    asyncio.run(_orig(commands.set_mode_clash)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"] = {"id": "1", "creator_id": 1, "game_started": False, "mode": commands.DEFAULT_MODE}
    fake_db.room_players["1"] = [1]
    update = make_update(user_id=1, text="/mode")
    asyncio.run(_orig(commands.set_mode_clash)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"]["game_started"] = True
    update = make_update(user_id=1, text="/mode")
    asyncio.run(_orig(commands.set_mode_clash)(update, fake_context))
    assert update.message.replies

    fake_db.rooms["1"]["game_started"] = False
    update = make_update(user_id=1, text="/mode")
    asyncio.run(_orig(commands.set_mode_dota)(update, fake_context))
    assert update.message.replies
