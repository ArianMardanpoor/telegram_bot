import time
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from bot.core.loader import redis_client


class ThrottlingMiddleware(BaseMiddleware):
    """
    Prevents message flood attacks on active bot sessions.
    Locks operations for 1.5 seconds per user on a Redis cache register.
    """
    def __init__(self, limit: float = 1.5):
        super().__init__()
        self.limit = limit

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        cache_key = f"throttling:{user_id}"
        
        # Check if user has sent a message too recently
        last_message_time = await redis_client.get(cache_key)
        now = time.time()
        
        if last_message_time:
            time_diff = now - float(last_message_time)
            if time_diff < self.limit:
                # Discard user message without notice
                if isinstance(event, CallbackQuery):
                    await event.answer("⚠️ لطفا اسپم نکنید! کمی صبور باشید.", show_alert=True)
                return None
        
        # Save timestamp
        await redis_client.set(cache_key, str(now), px=int(self.limit * 1000))
        return await handler(event, data)
