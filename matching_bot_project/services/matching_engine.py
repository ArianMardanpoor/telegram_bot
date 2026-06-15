import logging
from typing import Optional
import redis.asyncio as aioredis
from redis.exceptions import WatchError

logger = logging.getLogger(__name__)

# TTL for user state keys in Redis — if cleanup is never called (e.g. crash),
# stale "queuing" or "matched" states expire automatically instead of leaking forever
_USER_STATE_TTL_SECONDS = 3600  # 1 hour


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
        normalized_gender = gender.strip().capitalize()
        vip_suffix = "vip" if is_vip else "free"

        if is_vip and city:
            normalized_city = city.strip().lower().replace(" ", "_")
            return f"match:queue:{normalized_gender}:{vip_suffix}:{normalized_city}"

        return f"match:queue:{normalized_gender}:{vip_suffix}"

    async def add_to_queue(self, tg_id: int, gender: str, is_vip: bool = False, city: Optional[str] = None) -> bool:
        """
        Locks a user inside the matching pool.
        Ensures a user is not added to multiple queues.
        """
        await self.connect()
        await self.remove_from_queue(tg_id)

        user_state_key = f"user:state:{tg_id}"
        queue_key = self._get_queue_key(gender, is_vip, city)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(user_state_key, mapping={
                "gender": gender,
                "is_vip": str(int(is_vip)),
                "city": city or "",
                "queue_key": queue_key,
                "status": "queuing"
            })
            # FIX: set TTL on user state key so stale entries expire automatically
            # if the bot crashes or cleanup is never triggered
            pipe.expire(user_state_key, _USER_STATE_TTL_SECONDS)
            pipe.lpush(queue_key, tg_id)
            await pipe.execute()

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
        Uses RPOP to pop a candidate from the opposite gender queue.
        Returns matched user's TG ID, or None if no match is found.
        """
        await self.connect()
        user_state_key = f"user:state:{tg_id}"

        opp_gender = "Female" if gender.strip().capitalize() == "Male" else "Male"
        target_queue_key = self._get_queue_key(opp_gender, is_vip, city)

        # FIX: added iteration limit to prevent infinite loop if the queue is being
        # rapidly repopulated by other concurrent callers. In practice the queue is
        # finite, but without a cap a thundering-herd scenario could stall the engine.
        max_attempts = 50
        attempts = 0

        while attempts < max_attempts:
            attempts += 1
            candidate_id_str = await self.redis.rpop(target_queue_key)
            if not candidate_id_str:
                break

            candidate_id = int(candidate_id_str)

            if candidate_id == tg_id:
                continue

            candidate_state_key = f"user:state:{candidate_id}"

            # FIX: use WATCH to detect if the candidate's state changes between our
            # status check and our pipeline execution. Without WATCH, a candidate who
            # cancels (deletes their state) between hget and pipe.execute would have
            # their state silently recreated as "matched" — leaving them stuck.
            try:
                async with self.redis.pipeline() as pipe:
                    await pipe.watch(candidate_state_key)
                    candidate_status = await pipe.hget(candidate_state_key, "status")

                    if candidate_status != "queuing":
                        await pipe.reset()
                        continue

                    pipe.multi()

                    # FIX: initialize the FULL state for the current user in the same
                    # atomic pipeline. Previously only "status" and "matched_with" were
                    # set, leaving gender/is_vip/city/queue_key absent — which caused
                    # remove_from_queue to silently skip the lrem step on cleanup.
                    queue_key = self._get_queue_key(gender, is_vip, city)
                    pipe.hset(user_state_key, mapping={
                        "gender": gender,
                        "is_vip": str(int(is_vip)),
                        "city": city or "",
                        "queue_key": queue_key,
                        "status": "matched",
                        "matched_with": str(candidate_id)
                    })
                    pipe.expire(user_state_key, _USER_STATE_TTL_SECONDS)

                    pipe.hset(candidate_state_key, "status", "matched")
                    pipe.hset(candidate_state_key, "matched_with", str(tg_id))
                    pipe.expire(candidate_state_key, _USER_STATE_TTL_SECONDS)

                    await pipe.execute()

                logger.info("Redis Matchmaking succeeded: %s <-> %s", tg_id, candidate_id)
                return candidate_id

            except WatchError:
                # Candidate state changed between our read and our write — skip and retry
                logger.debug("WatchError on candidate %s during match attempt, skipping.", candidate_id)
                continue

        # No candidate found — add user to their own queue to wait
        await self.add_to_queue(tg_id, gender, is_vip, city)
        return None

    async def get_user_match_partner(self, tg_id: int) -> Optional[int]:
        """Utility to retrieve active partner ID of a matched user."""
        await self.connect()
        partner = await self.redis.hget(f"user:state:{tg_id}", "matched_with")
        return int(partner) if partner else None