import asyncio
import logging
import os

import httpx

import nest_asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

load_dotenv()
from telegram.request import HTTPXRequest
from database.actions import db
from handlers.commands import (
    admin_broadcast_confirm_callback,
    admin_panel,
    buy_hint,
    buy_hint_cancel_callback,
    buy_hint_confirm_callback,
    buy_hint_type_callback,
    cabinet_action_callback,
    check_subscription_callback,
    create_room,
    donate,
    donate_amount_callback,
    error_handler,
    get_word,
    handle_text_message,
    join_room,
    leave_room,
    make_room_private,
    make_room_public,
    personal_account,
    precheckout_callback,
    restart_game,
    room_status,
    rules,
    set_mode_brawl,
    set_mode_clash,
    set_mode_dota,
    show_cards,
    show_players,
    show_stats,
    start,
    start_game,
    set_spies,
    successful_payment_callback,
    single_mode,
    single_mode_callback,
)
from handlers.callback import (
    check_clue_callback,
    show_clues_callback,
    back_to_room_callback,
    set_spies_callback,
    public_join_callback,
    public_rooms_page_callback,

)
from utils.background import generate_clue, periodic_cleanup,update_connect,cleanup_single_mode
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
nest_asyncio.apply()
logger = logging.getLogger(__name__)

def _httpx_supports_proxy_kw() -> bool:
    parts = []
    for part in httpx.__version__.split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        if not num:
            break
        parts.append(int(num))
    return tuple(parts[:2]) >= (0, 28)


def _normalize_httpx_proxy(proxy):
    if not isinstance(proxy, dict):
        return proxy
    for key in ("all", "all://", "http://", "https://", "http", "https"):
        value = proxy.get(key)
        if value:
            return value
    for value in proxy.values():
        if value:
            return value
    return None


class CompatHTTPXRequest(HTTPXRequest):
    def _build_client(self) -> httpx.AsyncClient:
        kwargs = dict(self._client_kwargs)
        proxy = kwargs.pop("proxies", None)
        if proxy is not None:
            if _httpx_supports_proxy_kw():
                proxy = _normalize_httpx_proxy(proxy)
                if proxy is not None:
                    kwargs["proxy"] = proxy
            else:
                kwargs["proxies"] = proxy
        return httpx.AsyncClient(**kwargs)
async def main():
    API_TOKEN = os.getenv("API_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not API_TOKEN:
        print("❌ Установите API_TOKEN в .env файле!")
        return

    if not DATABASE_URL:
        print("❌ Установите DATABASE_URL в .env файле!")
        return

    try:
        await db.connect(DATABASE_URL, min_size=5, max_size=20)
        logger.info("database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return

    asyncio.create_task(periodic_cleanup())
    asyncio.create_task(generate_clue())
    asyncio.create_task(update_connect())
    asyncio.create_task(cleanup_single_mode())
    # Separate pools: long polling occupies one connection, so allocate more for bot API calls.
    request = CompatHTTPXRequest(connection_pool_size=20, pool_timeout=20)
    builder = Application.builder().token(API_TOKEN).request(request)
    if hasattr(builder, "get_updates_request"):
        builder = builder.get_updates_request(
            CompatHTTPXRequest(connection_pool_size=1, pool_timeout=20)
        )
    application = builder.build()
    handlers = [
        CommandHandler("start", start),
        CommandHandler("create", create_room),
        CommandHandler("join", join_room),
        CommandHandler("public", make_room_public),
        CommandHandler("private", make_room_private),
        CommandHandler("startgame", start_game),
        CommandHandler("restart", restart_game),
        CommandHandler("admin", admin_panel),
        CommandHandler("word", get_word),
        CommandHandler("players", show_players),
        CommandHandler("leave", leave_room),
        CommandHandler("rules", rules),
        CommandHandler("cards", show_cards),
        CommandHandler("mode_clash", set_mode_clash),
        CommandHandler("mode_dota", set_mode_dota),
        CommandHandler("mode_brawl", set_mode_brawl),
        CommandHandler("menu", start),
        CommandHandler("single", single_mode),
        CommandHandler("stats", show_stats),
        CommandHandler("account", personal_account),
        CommandHandler("buy_hint", buy_hint),
        CommandHandler("spies", set_spies),
        CommandHandler("room", room_status),
    ]
    application.add_handler(
        CallbackQueryHandler(check_subscription_callback, pattern="check_subscription")
    )
    application.add_handler(
        CallbackQueryHandler(single_mode_callback, pattern=r"^single:")
    )
    application.add_handler(
        CallbackQueryHandler(buy_hint_type_callback, pattern=r"^buy_type:")
    )
    application.add_handler(
        CallbackQueryHandler(buy_hint_confirm_callback, pattern=r"^buy_confirm:")
    )
    application.add_handler(
        CallbackQueryHandler(buy_hint_cancel_callback, pattern="buy_cancel")
    )
    application.add_handler(
        CallbackQueryHandler(cabinet_action_callback, pattern=r"^cabinet:")
    )
    application.add_handler(
        CallbackQueryHandler(donate_amount_callback, pattern=r"^donate_amount:")
    )
    application.add_handler(
        CallbackQueryHandler(
            admin_broadcast_confirm_callback, pattern=r"^admin_broadcast:"
        )
    )
    application.add_handler(
        CallbackQueryHandler(check_clue_callback, pattern=r"^check_clue:")
    )
    application.add_handler(
        CallbackQueryHandler(show_clues_callback, pattern="show_clues")
    )
    application.add_handler(
        CallbackQueryHandler(back_to_room_callback, pattern="back_to_room")
    )
    application.add_handler(
        CallbackQueryHandler(set_spies_callback, pattern=r"^spies:set:")
    )
    application.add_handler(
        CallbackQueryHandler(public_rooms_page_callback, pattern=r"^public_rooms:page:")
    )
    application.add_handler(
        CallbackQueryHandler(public_join_callback, pattern=r"^public_join:")
    )
    application.add_handler(CommandHandler("donate", donate))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )
    for handler in handlers:
        application.add_handler(handler)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    application.add_error_handler(error_handler)
    logger.info("🚀 Bot starting...")
    try:
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False,
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if db.pool:
            await db.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
