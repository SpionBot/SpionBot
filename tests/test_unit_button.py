from telegram import ReplyKeyboardMarkup

from handlers.button import get_main_keyboard, get_room_keyboard


def test_get_main_keyboard_structure():
    keyboard = get_main_keyboard()
    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 3
    assert "Создать" in keyboard.keyboard[0][0].text


def test_get_room_keyboard_structure():
    keyboard = get_room_keyboard()
    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 2
    assert "Начать" in keyboard.keyboard[0][0].text
