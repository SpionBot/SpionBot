import random

from utils.clue import UserClue


def test_found_clue_picks_expected_index(monkeypatch):
    clues = UserClue()
    clues.clues["dota2"]["Hero"] = {
        "easy": ["e0", "e1", "e2", "e3", "e4", "e5"],
        "medium": ["m0", "m1", "m2", "m3", "m4", "m5"],
        "hard": ["h0", "h1", "h2", "h3", "h4", "h5"],
    }

    monkeypatch.setattr(random, "randint", lambda a, b: 2)
    assert clues.found_clue("dota2", "Hero", "easy") == "e2"
    assert clues.found_clue("dota2", "Hero", "hard") == "h2"
