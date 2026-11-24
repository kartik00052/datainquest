from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from daginquest.config import get_settings


def allowed_only(handler):
    """Reject any update that does not come from an allow-listed chat."""
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if chat is None or chat.id not in get_settings().allowed_chat_ids:
            return
        return await handler(update, context)
    return wrapper
