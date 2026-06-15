import os
import asyncio
import logging
import sys

from dotenv import load_dotenv

import uvicorn

from bot.core.config import settings
from bot.core.loader import dp, bot

from bot.middlewares.database import DbSessionMiddleware
from bot.middlewares.force_join import ForceJoinMiddleware
from bot.middlewares.anti_spam import ThrottlingMiddleware

from bot.handlers import (
    start,
    profile,
    matching,
    questionnaire,
    anonymous_chat
)

# =========================
# ENV LOAD (IMPORTANT FIX)
# =========================
load_dotenv()

print("DB_HOST =", os.getenv("DB_HOST"))
print("DATABASE_URL =", os.getenv("DATABASE_URL"))

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("launcher")


# =========================
# BOT SETUP
# =========================
def register_bot_middlewares_and_routers():
    """Attach middlewares and routers to dispatcher."""

    # DB middleware (must be first)
    dp.message.outer_middleware(DbSessionMiddleware())
    dp.callback_query.outer_middleware(DbSessionMiddleware())

    # throttling
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    # force join
    dp.message.middleware(ForceJoinMiddleware())
    dp.callback_query.middleware(ForceJoinMiddleware())

    # routers
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(matching.router)
    dp.include_router(questionnaire.router)
    dp.include_router(anonymous_chat.router)

    logger.info("Bot handlers and middlewares initialized.")


# =========================
# FASTAPI SERVER
# =========================
async def run_fastapi_server():
    logger.info("Starting FastAPI via Uvicorn...")

    config = uvicorn.Config(
        app="api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info",
        reload=False
    )

    server = uvicorn.Server(config)
    await server.serve()


# =========================
# TELEGRAM BOT
# =========================
async def run_bot_polling():
    logger.info("Starting Telegram bot polling...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


# =========================
# MAIN ENTRY
# =========================
async def main():
    register_bot_middlewares_and_routers()

    base_url = getattr(settings, "BASE_URL", "")

    # DEV mode: run both
    if "localhost" in base_url or "127.0.0.1" in base_url or "dev" in base_url:
        logger.info("DEV mode: running bot + API concurrently")

        await asyncio.gather(
            run_fastapi_server(),
            run_bot_polling()
        )

    # PROD mode: API only
    else:
        logger.info("PROD mode: running API only")
        await run_fastapi_server()


# =========================
# START
# =========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown complete.")