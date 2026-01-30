import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from const import (
    MODE_CLASH,
    HINT_PRICES,
    ADMIN
)
from database.actions import db
from handlers.button import (
    get_game_inline_button,
    get_inline_keyboard,
    get_room_keyboard,
    get_message_start,
    get_join_room_text,
    get_restart_room_text

)
from handlers.commands import _show_public_rooms
from database.redis import get_clue_hero
from utils.decorators import hint_guard, room_locks
from utils.gameMod import get_theme_name, get_words_and_cards_by_mode

logger = logging.getLogger(__name__)

DEFAULT_MODE = MODE_CLASH


async def set_spies_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 4:
        return
    _, action, room_id, count_raw = parts
    if action != "set":
        return
    user_id = query.from_user.id
    try:
        requested = int(count_raw)
    except ValueError:
        await query.answer("Введите число.", show_alert=True)
        return

    room = await db.get_room(room_id)
    if not room:
        await query.answer("Комната не найдена.", show_alert=True)
        return
    if room.get("creator_id") != user_id:
        await query.answer("Только создатель может менять шпионов.", show_alert=True)
        return
    if room.get("game_started"):
        await query.answer("Игра уже началась — перезапустите.", show_alert=True)
        return

    players = await db.get_room_players(room_id)
    max_spies = max(1, len(players) - 1)
    if requested < 1:
        requested = 1
    if requested > max_spies:
        requested = max_spies

    await db.update_room_spy_count(room_id, requested)
    await query.answer(f"Шпионов: {requested}")
    try:
        await query.message.edit_text(
            f"✅ Кол-во шпионов установлено: {requested}\n"
            f"ℹ️ Можно изменить командой: /spies <число>"
        )
    except Exception:
        pass

async def show_clues_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Сработал show_clues_callback")
    query = update.callback_query
    data = query.data or ""
    source = data.split(":")[1]
    await query.answer()

    await query.message.edit_text(
        f"💡 Подсказки:\n\n"
        f"Подсказки помогут тебе быстрее понять, какой персонаж загадан!\n\n"
        f"Существует 3 вида подсказок:\n"
        f"1) Hard — абстрактный факт, который максимально обобщённо описывает персонажа "
        f"(Цена: {HINT_PRICES['hard']}✨)\n"
        f"2) Medium — факт, который поймут любители и профессионалы, но не многие новички "
        f"(Цена: {HINT_PRICES['medium']}✨)\n"
        f"3) Easy — факт, который будет понятен даже новичкам! "
        f"(Цена: {HINT_PRICES['easy']}✨)\n\n"
        f"Если у вас нет подсказок — их можно приобрести в в личном кабинете.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_room:{source}")]]
        ),
    )


async def back_to_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Сработал back_to_room_callback")
    query = update.callback_query
    data = query.data or ""
    source = data.split(":")[1]
    await query.answer()
    user_id = query.from_user.id
    room_id = await db.get_user_room(user_id)
    if not room_id:
        await query.message.edit_text("Нет комнаты. Создай новую: /create")
        return
    room = await db.get_room(room_id)
    if not room:
        return None, None
    words, _ = get_words_and_cards_by_mode(DEFAULT_MODE)
    reply_keyboard = get_inline_keyboard(source)
    players = await db.get_room_players(room_id)
    spy_count = room.get("spy_count", 1)
    is_public = room.get("is_public", False)
    mode = room.get("mode", DEFAULT_MODE)
    call_text = {
        'join_game': get_join_room_text(
            is_public, room_id, len(players), get_theme_name(mode), spy_count=spy_count
        ),
        'start_game': get_message_start(
            is_public, room_id, len(players), get_theme_name(mode), spy_count=spy_count
        ),
        'restart_game': get_restart_room_text(is_public, room_id, players, room),
    }
    await query.message.edit_text(
        text=call_text[source],
        parse_mode=ParseMode.HTML,
        reply_markup=reply_keyboard,
    )


async def public_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 2:
        return
    _, room_id = parts
    if not room_id:
        return

    user_id = query.from_user.id
    chat_id = query.message.chat_id if query.message else user_id

    lock = room_locks.get_lock(room_id)
    async with lock:
        room = await db.get_room(room_id)
        if not room:
            await context.bot.send_message(chat_id=chat_id, text="❗Комната не найдена.")
            return
        if room.get("game_started"):
            await context.bot.send_message(chat_id=chat_id, text="❗Игра уже началась.")
            return
        current_room = await db.get_user_room(user_id)
        if current_room:
            if current_room == room_id:
                await context.bot.send_message(
                    chat_id=chat_id, text="❗Вы уже в этой комнате."
                )
                return
            await context.bot.send_message(
                chat_id=chat_id,
                text="❗Вы уже в другой комнате. Сначала выйдите из неё.",
            )
            return
        success = await db.add_player_to_room(user_id, room_id)
        if not success:
            await context.bot.send_message(
                chat_id=chat_id, text="❗Комната заполнена или недоступна."
            )
            return
    if query.message:
        try:
            await query.message.delete()
        except Exception:
            try:
                await query.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass

    players = await db.get_room_players(room_id)
    inline_keyboard = get_inline_keyboard("join_game")
    keyboard = get_room_keyboard(is_public=room.get("is_public", False))
    spy_count = room.get("spy_count", 1)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Вы присоединились к комнате {room_id}!",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=get_join_room_text(
             room['is_public'],room_id, len(players), get_theme_name(DEFAULT_MODE), spy_count=spy_count
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=inline_keyboard,
    )

    creator_id = room.get("creator_id")
    if creator_id:
        try:
            await context.bot.send_message(
                creator_id,
                f"📢 Игрок присоединился! Теперь игроков: {len(players)}",
            )
        except Exception:
            pass


async def public_rooms_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 3:
        return
    _, action, page_raw = parts
    if action != "page":
        return
    try:
        page = int(page_raw)
    except ValueError:
        return
    await query.answer()
    await _show_public_rooms(update, context, page=page, edit_message=True)


@hint_guard
async def check_clue_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, clue_type: str
):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    hint_type = f"{clue_type}_hints"
    user_id = query.from_user.id
    room_id = await db.get_user_room(user_id)
    if not room_id:
        await context.bot.send_message(chat_id=chat_id, text="Вы находитесь не в игры!")
        return

    room = await db.get_room(room_id)
    word = room.get("word")
    if not room or not room.get("word"):
        await context.bot.send_message(chat_id=chat_id, text="Вы находитесь не в игры!")
        return
    logger.info("Получен герой из комнаты")
    mode = room.get("mode")
    game_key = mode.lower()
    count = await db.get_user_account(user_id)
    if count is None:
        logger.info("Произошла ошибка взятия подсказок")
        return
    count_hints = {
        "easy": count["easy_hints"],
        "medium": count["medium_hints"],
        "hard": count["hard_hints"],
    }
    if count_hints[clue_type] <= 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ У вас нет подсказок,для данного типа.Приобрести подсказку можно в личном кабинете",
        )
        logger.info(f"У пользователя нет подсказок типа {clue_type}")
        return
    clue = "Подсказка: " + get_clue_hero(word, clue_type)
    await db.update_user_hint(user_id, hint_type)
    count_hints[clue_type] -= 1
    logger.info("Удалены подсказка у пользователя.")
    await query.edit_message_reply_markup(
        get_game_inline_button(
            count_hints["easy"], count_hints["medium"], count_hints["hard"]
        )
    )
    await context.bot.send_message(chat_id=chat_id, text=clue)
