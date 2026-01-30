from telegram import ReplyKeyboardMarkup,InlineKeyboardMarkup,InlineKeyboardButton
from utils.gameMod import get_theme_name
from const import HINT_TEXT,HINT_LABELS, HINT_PRICES,DONATE_AMOUNTS

def get_main_keyboard(admin : str | None = None) -> ReplyKeyboardMarkup:
    keyboard = [
            ["🎮 Создать комнату", "🔗 Присоединиться"],
            ["👤 Личный кабинет", "📖 Правила"],
            ["🃏 Сингл мод", "❓Поддержка"],
        ]
    if admin is not None:
        keyboard.append([admin])
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def get_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📊 Стата сингл мода","📈 Общая стата"],
            ["📢 Запустить рассылку","👤 Жалобы"], 
            ["⬅️ Назад"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_room_keyboard(admin : bool = False,is_public: bool = False) -> ReplyKeyboardMarkup:
    toggle_label = ["🔒 Закрыть комнату"] if is_public else ["🌐 Открыть комнату"]
    toggle_label.append("🗳️ Голосование")
    admin_func = ["▶️ Начать игру", "🔄 Перезапустить"]
    keyboard = [
            ["🚪 Выйти из комнаты", "🏠 Главное меню"],
    ]
    if admin:
        keyboard.append(admin_func)
        keyboard.append(toggle_label)

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def build_vote_keyboard(players: list[tuple[int, str]], room_id: str, row_size: int = 2) -> InlineKeyboardMarkup:
    if row_size < 1:
        row_size = 1
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(players), row_size):
        row: list[InlineKeyboardButton] = []
        for player_id, name in players[i : i + row_size]:
            label = name or "Игрок"
            if len(label) > 24:
                label = label[:23] + "…"
            row.append(
                InlineKeyboardButton(
                    text=label, callback_data=f"vote:{room_id}:{player_id}"
                )
            )
        if row:
            rows.append(row)
    return InlineKeyboardMarkup(rows)
def get_game_inline_button(easy: int, medium: int, hard: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{HINT_TEXT['hard']} ({hard})", callback_data="check_clue:hard"
                ),
                InlineKeyboardButton(
                    f"{HINT_TEXT['medium']} ({medium})",
                    callback_data="check_clue:medium",
                ),
                InlineKeyboardButton(
                    f"{HINT_TEXT['easy']} ({easy})", callback_data="check_clue:easy"
                ),
            ]
        ]
    )


def get_inline_keyboard(place : str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="💡Подсказки", callback_data=f"show_clues:{place}")]]
    )
def get_room_mode_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🎲 Дота 2", "🃏 Clash Royale", "🎮 Brawl Stars"],
         ["🚪 Выйти из комнаты", "🏠 Главное меню"],
         ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
def get_message_start(status : bool,room_id: str, players: int, mode: str, spy_count: int = 1) -> str:
    status_room = (
        "🔒 Закрытая комната" if not status else "🌐 Открытая комната"
    )
    return (
        f"ID комнаты: <code>{room_id}</code>\n"
        f"Отправьте этот ID другим игрокам\n\n"
        f"👥 Игроков: {str(players)}/15\n"
        f"🎴 Режим: {mode}\n"
        f"ℹ️ Статус комнаты: {status_room}\n"
        f"🕵️ Шпионов: {spy_count}\n"
        f"🕵️ Сменить: /spies &lt;число&gt;\n"
        f"⬇️ Выберите режим через кнопки снизу\n"
        f"🔄 Для быстрой смены режима можно использовать команды\n"
        f"📲 /mode_clash, /mode_dota или /mode_brawl \n"
        f"🔥 Тыкни на подсказки и узнай как побеждать проще 🙂"
    )
def get_restart_room_text(status : bool,room_id,players,room) -> str:
    status_room = (
        "🔒 Закрытая комната" if not status else "🌐 Открытая комната"
    )
    return (
    f"🔄 Игра перезапущена!\n\n"
    f"ID комнаты: <code>{room_id}</code>\n"
    f"👥 Игроков: {len(players)}\n"
    f"🎴 Режим: {get_theme_name(room['mode'])}\n"
    f"ℹ️ Статус комнаты:{status_room}\n"
    f"🕵️ Шпионов: {room.get('spy_count', 1)}\n"
    f"🕵️ Сменить: /spies &lt;число&gt;\n"
    f"🎱 Используй для смены режимы \n /mode_clash /mode_dota /mode_brawl \n"
    f"Для начала новой игры нажмите '▶️ Начать игру'")

def get_join_room_text(status : bool,room_id,players,mode, spy_count: int = 1) -> str:
    status_room = (
        "🔒 Закрытая комната" if not status else "🌐 Открытая комната"
    )
    return (
        f"ID комнаты: <code>{room_id}</code>\n"
        f"Отправьте этот ID другим игрокам\n\n"
        f"ℹ️ Статус комнаты:{status_room}\n"
        f"👥 Игроков: {str(players)}/15\n"
        f"🎴 Режим: {mode}\n"
        f"🕵️ Шпионов: {spy_count}\n"
        f"🔥 Тыкни на подсказки и узнай как побеждать проще 🙂")


def build_spy_count_keyboard(room_id: str, max_spies: int = 7) -> InlineKeyboardMarkup:
    options = list(range(1, max_spies + 1))
    rows = []
    for i in range(0, len(options), 3):
        rows.append(
            [
                InlineKeyboardButton(
                    f"{count}", callback_data=f"spies:set:{room_id}:{count}"
                )
                for count in options[i : i + 3]
            ]
        )
    return InlineKeyboardMarkup(rows)
def _build_cabinet_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="cabinet:menu"),
                InlineKeyboardButton(
                    "🛒 Купить подсказки", callback_data="cabinet:buy_hints"
                ),
            ],
            [
                InlineKeyboardButton(
                    "💳 Пополнить баланс", callback_data="cabinet:donate"
                ),
                InlineKeyboardButton("🎁 Реферальная система",callback_data="cabinet:referal")
            ],
        ]
    )

def _build_hint_selection_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                f"{HINT_LABELS[hint_type]} — {HINT_PRICES[hint_type]} ⭐",
                callback_data=f"buy_type:{hint_type}",
            )
        ]
        for hint_type in ["easy", "medium", "hard"]
    ]
    keyboard.append(
        [InlineKeyboardButton("⬅️ Назад", callback_data="cabinet:account")]
    )
    return InlineKeyboardMarkup(keyboard)
def _personal_account_text(
    user, balance, hard, medium, easy, games_played=None, spy_games_played=None
):
    games_played = games_played or 0
    spy_games_played = spy_games_played or 0

    stats_block = (
        f"\n\n🎮Сыграно игр: {games_played}\n"
        f"🕵️Сыграно за шпиона: {spy_games_played}"
    )

    name = user.full_name or user.username or "Игрок"
    base_text = (
        "<b>👤 Личный кабинет</b>\n\n"
        f"🔸 Имя: <b>{name}</b>\n\n"
        f"⭐ Баланс: <b>{balance}</b> ⭐\n\n"
        "📦 На счету подсказок:\n"
        f"• {HINT_LABELS['hard']}: {hard} шт.\n"
        f"• {HINT_LABELS['medium']}: {medium} шт.\n"
        f"• {HINT_LABELS['easy']}: {easy} шт.\n\n"
        "💳 Чтобы пополнить баланс, используйте /donate или меню ниже\n"
        "🛒 Чтобы купить подсказки, воспользуйтесь меню ниже."
)
    return base_text + stats_block


def _build_donate_keyboard():
    buttons = [
        InlineKeyboardButton(
            f"{amount} ⭐", callback_data=f"donate_amount:{amount}"
        )
        for amount in DONATE_AMOUNTS
    ]
    buttons.append(
        InlineKeyboardButton("⬅️ Назад", callback_data="cabinet:account")
    )
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)

def get_keyboard_report() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["⬅️ Назад"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def get_report_inline_keyboard(
    index: int, total: int, report_user_id: int, report_id: int
) -> InlineKeyboardMarkup:
    if total > 1:
        prev_index = (index - 1) % total
        next_index = (index + 1) % total
        nav_row = [
            InlineKeyboardButton("⬅️", callback_data=f"report:nav:{prev_index}"),
            InlineKeyboardButton(f"{index + 1}/{total}", callback_data="report:noop"),
            InlineKeyboardButton("➡️", callback_data=f"report:nav:{next_index}"),
        ]
    else:
        nav_row = [InlineKeyboardButton("1/1", callback_data="report:noop")]

    return InlineKeyboardMarkup(
        [
            nav_row,
            [
                InlineKeyboardButton(
                    "🗑️ Удалить", callback_data=f"report:delete:{report_id}:{index}"
                )
            ],
            [
                InlineKeyboardButton(
                    "✉️ Написать", callback_data=f"report:reply:{report_user_id}:{index}"
                )
            ],
        ]
    )
