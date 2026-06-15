import logging
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from matching_bot_project.bot.core.config import settings
from matching_bot_project.bot.core.loader import redis_client, bot

logger = logging.getLogger(__name__)

# FIX: "restricted" and "left"/"kicked" are not in this set, so they correctly block access.
# Added "restricted" users are still channel members by Telegram's definition but have
# limited permissions — excluding them is the safer default for a forced-join gate.
_ALLOWED_STATUSES = {"creator", "administrator", "member"}


class ForceJoinMiddleware(BaseMiddleware):
    """
    Enforces subscription to a mandatory Telegram channel.
    Caches successful checks in Redis (10 minutes TTL) to reduce Telegram API calls.
    """
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id

        # FIX: admin bypass moved BEFORE the Redis cache check.
        # Previously, if an admin happened to have a stale/missing cache entry,
        # the code would hit the Telegram API unnecessarily (or worse, block them
        # if the API call failed) before reaching the admin check.
        if user_id in settings.parsed_admin_ids:
            return await handler(event, data)

        cache_key = f"user:force_join_cache:{user_id}"
        cached_joined = await redis_client.get(cache_key)
        if cached_joined == "1":
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(
                chat_id=settings.REQUIRED_CHANNEL_ID,
                user_id=user_id
            )

            if member.status in _ALLOWED_STATUSES:
                await redis_client.set(cache_key, "1", ex=600)
                return await handler(event, data)

        except TelegramAPIError as e:
            logger.error("ForceJoin membership lookup failed for user %s: %s", user_id, e)
            # Fail open: if the channel is misconfigured or deleted, don't lock out all users
            return await handler(event, data)

        # User is not a member — prompt subscription and block further processing
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 عضویت در کانال", url=settings.CHANNEL_INVITE_LINK)
            ],
            [
                InlineKeyboardButton(text="✅ بررسی عضویت مجدد", callback_data="check_membership")
            ]
        ])

        alert_text = (
            "⚠️ *جهت استفاده از ربات همسریابی، ابتدا باید عضو کانال پشتیبانی ما شوید!*\n\n"
            "پس از عضویت در کانال از دکمه زیر جهت فعالسازی ربات استفاده کنید."
        )

        if isinstance(event, Message):
            await event.answer(text=alert_text, reply_markup=keyboard, parse_mode="Markdown")
        elif isinstance(event, CallbackQuery):
            await event.message.answer(text=alert_text, reply_markup=keyboard, parse_mode="Markdown")
            await event.answer("نیاز به تایید عضویت!")

        return None