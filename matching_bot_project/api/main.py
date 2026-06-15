import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from bot.core.config import settings
from bot.core.loader import bot, matching_engine, dating_scheduler
from api.routes import webhook, admin
from database.session import engine, Base, async_session_factory
from database.queries.crud import seed_sixty_question_bank_if_empty

# 👉 IMPORTANT: force load .env
load_dotenv()

logger = logging.getLogger(__name__)


def log_env():
    logger.info(f"DB_HOST = {os.getenv('DB_HOST')}")
    logger.info(f"DATABASE_URL = {os.getenv('DATABASE_URL')}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_env()

    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Seed data
        async with async_session_factory() as session:
            await seed_sixty_question_bank_if_empty(session)

        # Matching engine
        await matching_engine.connect()

        # Scheduler
        dating_scheduler.start_polling()

        # webhook setup
        if settings.BASE_URL and "yourdomain.com" not in settings.BASE_URL:
            webhook_url = f"{settings.BASE_URL}{settings.WEBHOOK_PATH}"
            logger.info(f"Setting webhook: {webhook_url}")

            await bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query", "my_chat_member"],
                drop_pending_updates=True
            )
        else:
            logger.warning("Polling mode enabled (no webhook).")
            await bot.delete_webhook(drop_pending_updates=True)

    except Exception as e:
        logger.exception(f"Startup failed: {e}")
        raise

    yield

    # shutdown
    await matching_engine.disconnect()
    await bot.session.close()
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Telegram Matchmaker API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}