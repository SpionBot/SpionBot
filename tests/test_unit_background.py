import asyncio
import importlib

import pytest

import const


def _reload_background():
    if not hasattr(const, "PROMPTS"):
        const.PROMPTS = {"dota2": "prompt {Heroname}"}
    return importlib.reload(importlib.import_module("utils.background"))


def test_periodic_cleanup_runs_once(monkeypatch, fake_db):
    background = _reload_background()
    monkeypatch.setattr(background, "db", fake_db)

    async def fake_sleep(_):
        raise asyncio.CancelledError()

    monkeypatch.setattr(background.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(background.periodic_cleanup())


def test_generate_clue_updates_store(monkeypatch):
    const.PROMPTS = {"dota2": "prompt {Heroname}"}
    background = _reload_background()
    background.game_array = {"dota2": ["Hero"]}

    def fake_ask_llm(_prompt):
        return {"Hero": {"easy": ["a"], "medium": ["b"], "hard": ["c"]}}

    monkeypatch.setattr(background, "ask_llm", fake_ask_llm)

    sleep_calls = {"count": 0}

    async def fake_sleep(_):
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            raise asyncio.CancelledError()
        return None

    monkeypatch.setattr(background.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(background.generate_clue())

    assert background.clue_obj.clue_dota2["Hero"]["easy"] == ["a"]
