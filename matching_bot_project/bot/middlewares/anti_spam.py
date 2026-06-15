from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from matching_bot_project.bot.core.loader import redis_client


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

        # FIX: replaced manual timestamp comparison with Redis SET NX (set-if-not-exists).
        # The old approach had a race condition: two near-simultaneous requests could both
        # read "no key" before either had written, and both would pass the throttle check.
        # SET NX is atomic — only one request can win the write, the other is blocked.
        # Also removed `import time` since it is no longer needed.
        key_set = await redis_client.set(
            cache_key,
            "1",
            px=int(self.limit * 1000),
            nx=True  # Only set if key does not already exist
        )

        if not key_set:
            # Key already existed — user is sending too fast
            if isinstance(event, CallbackQuery):
                await event.answer("⚠️ لطفا اسپم نکنید! کمی صبور باشید.", show_alert=True)
            return None

        return await handler(event, data)