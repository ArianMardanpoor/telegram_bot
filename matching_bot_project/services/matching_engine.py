import logging
from typing import Optional, Tuple
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

class MatchingEngine:
    """
    High-performance Matchmaking Engine powered by Redis.
    Uses Redis Lists as atomic queues divided by gender, and hashes for fast lookup.
    """
    def __init__(self, redis_host: str, redis_port: int, redis_password: str):
        self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Initialise async Redis connection pool."""
        if not self.redis:
            self.redis = aioredis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True,
                max_connections=50
            )
            logger.info("Connected to Redis Matchmaking engine successfully.")

    async def disconnect(self):
        """Close connection pool gracefully."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis Matchmaking engine.")

    def _get_queue_key(self, gender: str, is_vip: bool = False, city: Optional[str] = None) -> str:
        """Helper to compute specific queue keys."""
        normalized_gender = gender.strip().capitalize() # Male or Female
        vip_suffix = "vip" if is_vip else "free"
        
        if is_vip and city:
            # VIP matching filters localized by city
            normalized_city = city.strip().lower().replace(" ", "_")
            return f"match:queue:{normalized_gender}:{vip_suffix}:{normalized_city}"
        
        return f"match:queue:{normalized_gender}:{vip_suffix}"

    async def add_to_queue(self, tg_id: int, gender: str, is_vip: bool = False, city: Optional[str] = None) -> bool:
        """
        Locks a user inside the matching pool.
        Ensures a user is not added to multiple queues.
        """
        await self.connect()
        # Clean any existing active queues for this user
        await self.remove_from_queue(tg_id)

        # Main active match hash state
        user_state_key = f"user:state:{tg_id}"
        queue_key = self._get_queue_key(gender, is_vip, city)

        await self.redis.hset(user_state_key, mapping={
            "gender": gender,
            "is_vip": str(int(is_vip)),
            "city": city or "",
            "queue_key": queue_key,
            "status": "queuing"
        })
        
        # Add to the left side of the list (FIFO queue)
        await self.redis.lpush(queue_key, tg_id)
        return True

    async def remove_from_queue(self, tg_id: int) -> bool:
        """Removes user from the Redis queue and deletes their queue state."""
        await self.connect()
        user_state_key = f"user:state:{tg_id}"
        state = await self.redis.hgetall(user_state_key)
        
        if not state:
            return False

        queue_key = state.get("queue_key")
        if queue_key:
            await self.redis.lrem(queue_key, 0, tg_id)
        
        await self.redis.delete(user_state_key)
        return True

    async def find_match(self, tg_id: int, gender: str, is_vip: bool = False, city: Optional[str] = None) -> Optional[int]:
        """
        Attempts to match an active user with an opposing queue participant atomically.
        Uses RPOP to pop out a candidate from the opposite gender queue.
        Returns matched user's TG ID, or None if no match is found.
        """
        await self.connect()
        user_state_key = f"user:state:{tg_id}"
        
        # Determine opposite gender
        opp_gender = "Female" if gender.strip().capitalize() == "Male" else "Male"
        
        # Match from corresponding opposite queue type
        target_queue_key = self._get_queue_key(opp_gender, is_vip, city)
        
        # Clean and verify queue
        while True:
            # Atomically pop a contestant
            candidate_id_str = await self.redis.rpop(target_queue_key)
            if not candidate_id_str:
                break # Queue is empty
                
            candidate_id = int(candidate_id_str)
            
            # Avoid matching oneself
            if candidate_id == tg_id:
                continue

            candidate_state_key = f"user:state:{candidate_id}"
            candidate_status = await self.redis.hget(candidate_state_key, "status")
            
            # Ensure the contestant is still actively queuing in Redis
            if candidate_status == "queuing":
                # Lock both users in Redis by changing states
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.hset(user_state_key, "status", "matched")
                    pipe.hset(candidate_state_key, "status", "matched")
                    pipe.hset(user_state_key, "matched_with", candidate_id)
                    pipe.hset(candidate_state_key, "matched_with", tg_id)
                    await pipe.execute()
                
                logger.info(f"Redis Matchmaking Succeeded: {tg_id} <-> {candidate_id}")
                return candidate_id
                
        # No candidate found, add user to their own queue to wait
        await self.add_to_queue(tg_id, gender, is_vip, city)
        return None

    async def get_user_match_partner(self, tg_id: int) -> Optional[int]:
        """Utility to retrieve active partner ID of a matched user."""
        await self.connect()
        partner = await self.redis.hget(f"user:state:{tg_id}", "matched_with")
        return int(partner) if partner else None
