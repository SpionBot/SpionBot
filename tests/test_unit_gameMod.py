from const import CARDS_CLASH, MODE_CLASH, MODE_DOTA, WORDS_CLASH, dotaImages, namesDota
from utils.gameMod import get_theme_name, get_words_and_cards_by_mode


def test_get_words_and_cards_by_mode_dota():
    words, cards = get_words_and_cards_by_mode(MODE_DOTA)
    assert words == namesDota
    assert cards == dotaImages


def test_get_words_and_cards_by_mode_default():
    words, cards = get_words_and_cards_by_mode("unknown")
    assert words == WORDS_CLASH
    assert cards == CARDS_CLASH


def test_get_theme_name_contains_mode_marker():
    assert "Dota" in get_theme_name(MODE_DOTA)
    assert "Clash" in get_theme_name(MODE_CLASH)
