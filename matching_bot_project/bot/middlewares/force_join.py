import logging
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from bot.core.config import settings
from bot.core.loader import redis_client, bot

logger = logging.getLogger(__name__)


class ForceJoinMiddleware(BaseMiddleware):
    """
    Enforces subscription to a mandatory Telegram channel.
    Caches successful controls in Redis (10 minutes TTL) to bypass Telegram API rate limit errors.
    """
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Ignore events without a sender
        if not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        cache_key = f"user:force_join_cache:{user_id}"
        
        # Check if user is cached as registered/joined
        cached_joined = await redis_client.get(cache_key)
        if cached_joined == "1":
            return await handler(event, data)

        # Skip checks for bot admins
        if user_id in settings.parsed_admin_ids:
            return await handler(event, data)

        # Check membership status live via Bot API
        try:
            member = await bot.get_chat_member(
                chat_id=settings.REQUIRED_CHANNEL_ID, 
                user_id=user_id
            )
            
            # Approved statuses: creator, administrator, member
            if member.status in ["creator", "administrator", "member"]:
                # Save status in Redis cache for 10 mins (600 seconds)
                await redis_client.set(cache_key, "1", ex=600)
                return await handler(event, data)
                
        except TelegramAPIError as e:
            logger.error(f"Force Join membership lookup error for user ID {user_id}: {str(e)}")
            # Fail silently to user if channel is inaccessible/deleted, allowing continued access
            return await handler(event, data)

        # Prompt subscription and halt standard message process if not a member
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
            
        return None # Prevent event from reaching handlers
