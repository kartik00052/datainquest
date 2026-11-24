"""Run with: python -m daginquest.telegram.bot  (long polling, no public URL needed)."""
import asyncio
import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from daginquest.config import get_settings
from daginquest.db import session
from daginquest.telegram import handlers

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    await session.init_pool(settings.database_url)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("incidents", handlers.incidents))
    app.add_handler(CommandHandler("incident", handlers.incident))
    app.add_handler(CommandHandler("status", handlers.status))
    app.add_handler(CallbackQueryHandler(handlers.decision_callback, pattern=r"^(approve|reject):\d+$"))

    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
