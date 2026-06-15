import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as aioredis
from aiogram import Bot

logger = logging.getLogger(__name__)

class DatingScheduler:
    """
    Schedules and tracks questionnaire timeouts.
    If a matched user doesn't answer the active question within 180 seconds (3 minutes),
    this service notifies both users and closes the matched date connection to avoid queuing freezes.
    """
    def __init__(self, bot: Bot, redis_client: aioredis.Redis, timeout_seconds: int = 180):
        self.bot = bot
        self.redis = redis_client
        self.timeout_seconds = timeout_seconds
        self._running_task: Optional[asyncio.Task] = None

    async def update_user_activity(self, match_history_id: int, tg_id: int):
        """Saves timestamp in Redis to monitor response pace."""
        key = f"date:timeout:{match_history_id}"
        # Store epoch timestamp of the activity pulse
        now_epoch = float(datetime.utcnow().timestamp())
        await self.redis.hset(key, mapping={
            "last_activity": str(now_epoch),
            "user_id": str(tg_id)
        })
        # TTL of hash key set to 5 minutes to prevent storage leaks
        await self.redis.expire(key, 300)

    async def verify_timeout_loops(self):
        """
        Background polling task scanning all active timeout keys in Redis.
        Triggered in a cycle to check if users exceeded duration allowance.
        """
        while True:
            try:
                # Find all timeout trackers
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(cursor=cursor, match="date:timeout:*", count=100)
                    for key in keys:
                        try:
                            match_history_id = int(key.split(":")[-1])
                            data = await self.redis.hgetall(key)
                            if not data:
                                continue

                            last_activity = float(data.get("last_activity", 0))
                            now_epoch = float(datetime.utcnow().timestamp())
                            
                            # If expired, end matched dating questionnaire
                            if (now_epoch - last_activity) > self.timeout_seconds:
                                # Trigger close date operation
                                await self.close_inactive_date(match_history_id, key)
                        except Exception as e:
                            logger.error(f"Error checking key {key} state: {str(e)}")
                    
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error(f"Global exception in scheduling check loop: {str(e)}")
            
            # Delay check cycle
            await asyncio.sleep(15)

    async def close_inactive_date(self, match_id: int, redis_key: str):
        """Terminates matched couple and displays warnings to both sides."""
        # Find who they were from the match state hashes
        state_keys = await self.redis.keys(f"user:state:*")
        partners = []
        for state_key in state_keys:
            tg_id = int(state_key.split(":")[-1])
            mid = await self.redis.hget(state_key, "matched_with")
            if mid:
                partners.append(tg_id)
        
        # Free partners in Redis states
        for user_id in partners:
            await self.redis.delete(f"user:state:{user_id}")
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text="⏳ *زمان پاسخگویی به پایان رسید!*\nبه دلیل عدم مشارکت یکی از کاربران در ۳ دقیقه گذشته، مکالمه خاتمه یافت. برای مچ جدید از دکمه /matching استفاده کنید.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass # Bot blocked or invalid user ID
                
        # Clean Redis timeout key
        await self.redis.delete(redis_key)
        logger.info(f"Dating scheduler ended inactive match ID: {match_id}")

    def start_polling(self):
        """Launches the runner in the event loop background."""
        self._running_task = asyncio.create_task(self.verify_timeout_loops())
