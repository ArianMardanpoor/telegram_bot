import asyncio
import logging
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models.models import MatchHistory

logger = logging.getLogger(__name__)


class DatingScheduler:
    """
    Schedules and tracks questionnaire timeouts.
    If a matched user doesn't answer the active question within 180 seconds (3 minutes),
    this service notifies both users and closes the matched date connection to avoid queuing freezes.
    """

    def __init__(
        self,
        bot: Bot,
        dp: Dispatcher,
        redis_client: aioredis.Redis,
        session_factory: async_sessionmaker,
        timeout_seconds: int = 180,
    ):
        self.bot = bot
        self.dp = dp
        self.redis = redis_client
        self.session_factory = session_factory
        self.timeout_seconds = timeout_seconds
        self._running_task: Optional[asyncio.Task] = None

    async def register_match_timeout(
        self,
        match_history_id: int,
        user_one_id: int,
        user_two_id: int,
    ):
        """
        FIX #2: Called once when a match starts to register BOTH partner IDs.
        Previously, update_user_activity stored only one user_id (last caller),
        making the second partner untraceable at timeout.
        """
        key = f"date:timeout:{match_history_id}"
        now_epoch = float(datetime.utcnow().timestamp())
        await self.redis.hset(key, mapping={
            "last_activity": str(now_epoch),
            "user_one_id": str(user_one_id),
            "user_two_id": str(user_two_id),
        })
        await self.redis.expire(key, 300)

    async def update_user_activity(self, match_history_id: int, tg_id: int):
        """
        Refreshes the last_activity timestamp when a user answers a question.
        Partner IDs are NOT overwritten — they were set once in register_match_timeout.
        """
        key = f"date:timeout:{match_history_id}"
        now_epoch = float(datetime.utcnow().timestamp())
        # Only update the timestamp, never touch user_one_id / user_two_id
        await self.redis.hset(key, "last_activity", str(now_epoch))
        await self.redis.expire(key, 300)

    async def verify_timeout_loops(self):
        """
        Background polling task scanning all active timeout keys in Redis.
        Triggered in a cycle to check if users exceeded the duration allowance.
        """
        while True:
            try:
                # FIX #5: Use scan (non-blocking) instead of redis.keys()
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(
                        cursor=cursor, match="date:timeout:*", count=100
                    )
                    for key in keys:
                        try:
                            # Handle both bytes and str depending on decode_responses config
                            key_str = key.decode() if isinstance(key, bytes) else key
                            match_history_id = int(key_str.split(":")[-1])

                            raw_data = await self.redis.hgetall(key)
                            if not raw_data:
                                continue

                            # Normalize bytes → str
                            data = {
                                (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                                for k, v in raw_data.items()
                            }

                            last_activity = float(data.get("last_activity", 0))
                            now_epoch = float(datetime.utcnow().timestamp())

                            if (now_epoch - last_activity) > self.timeout_seconds:
                                await self.close_inactive_date(match_history_id, key_str, data)

                        except Exception as e:
                            logger.error(f"Error checking key {key}: {e}")

                    if cursor == 0:
                        break

            except Exception as e:
                logger.error(f"Global exception in scheduling check loop: {e}")

            await asyncio.sleep(15)

    async def close_inactive_date(self, match_id: int, redis_key: str, data: dict):
        """Terminates a timed-out match and notifies both users."""

        # FIX #2: Read both partner IDs directly from the timeout key
        user_one_str = data.get("user_one_id")
        user_two_str = data.get("user_two_id")

        if not user_one_str or not user_two_str:
            logger.error(
                f"Missing partner IDs for match {match_id} in key {redis_key}. "
                f"Data: {data}. Cleaning orphan key."
            )
            await self.redis.delete(redis_key)
            return

        partners = [int(user_one_str), int(user_two_str)]

        # FIX #4: Deactivate the MatchHistory record in the database
        try:
            async with self.session_factory() as session:
                match_row = await session.get(MatchHistory, match_id)
                if match_row:
                    match_row.is_active = False
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to deactivate match {match_id} in DB: {e}")

        # FIX #1 + FIX #3: Iterate only over the two specific partners (not all users),
        # and clear their FSM states so they are no longer stuck in QuestionnaireStates.
        for user_id in partners:
            # Clear Redis user-state key
            await self.redis.delete(f"user:state:{user_id}")

            # FIX #3: Clear aiogram FSM state
            try:
                context = self.dp.fsm.resolve_context(
                    bot=self.bot, chat_id=user_id, user_id=user_id
                )
                await context.clear()
            except Exception as e:
                logger.error(f"Failed to clear FSM state for user {user_id}: {e}")

            # Notify the user
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "⏳ *زمان پاسخگویی به پایان رسید!*\n"
                        "به دلیل عدم مشارکت یکی از کاربران در ۳ دقیقه گذشته، "
                        "مکالمه خاتمه یافت.\n"
                        "برای مچ جدید از دکمه 🎯 در منوی اصلی استفاده کنید."
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                pass  # Bot blocked or invalid user ID

        # FIX #6: Clean up all match-related Redis keys to prevent memory leaks
        await self.redis.delete(redis_key)
        await self.redis.delete(f"match:questions:{match_id}")
        await self.redis.delete(f"match:current_q_index:{match_id}")

        logger.info(f"Dating scheduler ended inactive match ID: {match_id}")

    def start_polling(self):
        """Launches the runner in the event loop background."""
        self._running_task = asyncio.create_task(self.verify_timeout_loops())