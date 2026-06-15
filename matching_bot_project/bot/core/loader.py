import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.client.default import DefaultBotProperties
from redis.asyncio import Redis

from bot.core.config import settings
from services.matching_engine import MatchingEngine
from services.scheduler import DatingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ✅ Bot instance (aiogram 3.7+ style)
bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

# Redis client
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

# FSM storage
fsm_storage = RedisStorage(
    redis=redis_client,
    key_builder=DefaultKeyBuilder(with_destiny=True)
)

# Dispatcher
dp = Dispatcher(storage=fsm_storage)

# Matching engine
matching_engine = MatchingEngine(
    redis_host=settings.REDIS_HOST,
    redis_port=settings.REDIS_PORT,
    redis_password=settings.REDIS_PASSWORD
)

# Scheduler
dating_scheduler = DatingScheduler(
    bot=bot,
    redis_client=redis_client,
    timeout_seconds=180
)