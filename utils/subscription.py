
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

CHANNEL_USERNAME = "@it_tut0"
CHANNEL_URL = "https://t.me/it_tut0"
async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in (
            "member",
            "administrator",
            "creator",
        )
    except BadRequest:
        return False


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Подписаться", url=CHANNEL_URL)],
            [
                InlineKeyboardButton(
                    "✅ Я подписался", callback_data="check_subscription"
                )
            ],
        ]
    )
 