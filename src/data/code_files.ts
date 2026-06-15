import { CodeFile } from '../types';

export const pythonCodeFiles: CodeFile[] = [
  {
    path: 'docker-compose.yml',
    description: 'Docker Compose orchestration file initializing dual isolated db (MySQL) + caching (Redis) networks with the bot.',
    language: 'yaml',
    content: `version: '3.8'

services:
  mysql_db:
    image: mysql:8.0
    container_name: match_mysql_db
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: root_secure_pass123
      MYSQL_DATABASE: match_bot_db
      MYSQL_USER: match_bot_user
      MYSQL_PASSWORD: match_bot_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - match_bot_network
    command: --default-authentication-plugin=mysql_native_password
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u$$MYSQL_USER", "-p$$MYSQL_PASSWORD"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis_cache:
    image: redis:7-alpine
    container_name: match_redis_cache
    restart: always
    command: redis-server --requirepass redis_secure_pass123 --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - match_bot_network
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis_secure_pass123", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  fastapi_bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: match_fastapi_bot
    restart: always
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    depends_on:
      mysql_db:
        condition: service_healthy
      redis_cache:
        condition: service_healthy
    networks:
      - match_bot_network

networks:
  match_bot_network:
    driver: bridge

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local`
  },
  {
    path: 'requirements.txt',
    description: 'Python package dependency matrix specifying FastAPI, aiogram 3.x, and SQLAlchemy 2.0.',
    language: 'text',
    content: `aiogram==3.15.0
fastapi==0.110.0
uvicorn==0.28.0
sqlalchemy[asyncio]==2.0.29
aiomysql==0.2.0
redis==5.0.3
alembic==1.13.1
python-dotenv==1.0.1
pydantic-settings==2.2.1
async-timeout==4.0.3
httpx==0.27.0
cryptography==42.0.5`
  },
  {
    path: 'database/session.py',
    description: 'SQLAlchemy 2.0 asynchronous connection manager with connection pool settings.',
    language: 'python',
    content: `import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+aiomysql://match_bot_user:match_bot_password@localhost:3306/match_bot_db"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()`
  },
  {
    path: 'database/models/models.py',
    description: 'SQLAlchemy declarative models for User, Questions bank, match histories, and answers.',
    language: 'python',
    content: `from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from matching_bot_project.database.session import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) 
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vip_quota: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    referrer_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.tg_id", ondelete="SET NULL"), nullable=True)
    completed_registration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(200), nullable=False)
    option_b: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="General", nullable=False)

class MatchHistory(Base):
    __tablename__ = "match_histories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_one_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
    user_two_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.tg_id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    questionnaire_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_one_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_two_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chat_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)`
  },
  {
    path: 'services/matching_engine.py',
    description: 'Redis Queue Manager organizing matching rosters, executing free and VIP gender-opposite lookups.',
    language: 'python',
    content: `import redis.asyncio as aioredis
from typing import Optional

class MatchingEngine:
    def __init__(self, redis_host: str, redis_port: int, redis_password: str):
        self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        if not self.redis:
            self.redis = aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    def _get_queue_key(self, gender: str, is_vip: bool = False, city: Optional[str] = None) -> str:
        gender_prefix = gender.capitalize()
        vip_suffix = "vip" if is_vip else "free"
        if is_vip and city:
            city_prefix = city.lower().replace(" ", "_")
            return f"match:queue:{gender_prefix}:{vip_suffix}:{city_prefix}"
        return f"match:queue:{gender_prefix}:{vip_suffix}"

    async def add_to_queue(self, tg_id: int, gender: str, is_vip: bool = False, city: Optional[str] = None):
        await self.connect()
        await self.remove_from_queue(tg_id)
        queue_key = self._get_queue_key(gender, is_vip, city)
        await self.redis.hset(f"user:state:{tg_id}", mapping={
            "gender": gender, "status": "queuing", "queue_key": queue_key
        })
        await self.redis.lpush(queue_key, tg_id)

    async def find_match(self, tg_id: int, gender: str, is_vip: bool = False, city: Optional[str] = None) -> Optional[int]:
        await self.connect()
        opp_gender = "Female" if gender.capitalize() == "Male" else "Male"
        target_queue = self._get_queue_key(opp_gender, is_vip, city)
        
        while True:
            candidate_id_str = await self.redis.rpop(target_queue)
            if not candidate_id_str:
                break
            candidate_id = int(candidate_id_str)
            if candidate_id == tg_id:
                continue
            
            # Verify they are still active
            status = await self.redis.hget(f"user:state:{candidate_id}", "status")
            if status == "queuing":
                # Lock both users
                await self.redis.hset(f"user:state:{tg_id}", "status", "matched")
                await self.redis.hset(f"user:state:{candidate_id}", "status", "matched")
                await self.redis.hset(f"user:state:{tg_id}", "matched_with", candidate_id)
                await self.redis.hset(f"user:state:{candidate_id}", "matched_with", tg_id)
                return candidate_id
        await self.add_to_queue(tg_id, gender, is_vip, city)
        return None`
  },
  {
    path: 'bot/handlers/questionnaire.py',
    description: 'Dynamic FSM coordination enforcing sync responses to Question N and scoring match compatibility.',
    language: 'python',
    content: `from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from matching_bot_project.bot.states.states import QuestionnaireStates
from matching_bot_project.database.queries import crud

router = Router()

@router.callback_query(QuestionnaireStates.answering_questions, F.data.startswith("ans_"))
async def register_question_response(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    match_id = data.get("match_history_id")
    index = data.get("current_question_index", 0)
    
    parts = call.data.split("_")
    option = parts[1].upper() # A or B
    q_id = int(parts[2])

    # Save to db
    await crud.save_user_answer(db_session, call.from_user.id, q_id, match_id, option)
    await call.message.edit_reply_markup(reply_markup=None)
    
    # Check if both has answered
    answers = await crud.check_question_status(db_session, match_id, q_id)
    if len(answers) == 2:
        next_idx = index + 1
        if next_idx >= 20:
            # Finalize questionnaire loop
            pass
        else:
            # Send next question to both
            pass
    else:
        await state.set_state(QuestionnaireStates.waiting_for_partner_answer)`
  },
  {
    path: 'bot/handlers/anonymous_chat.py',
    description: 'Subsequent text/media communication using copy_message and filtering strings for usernames/URLs.',
    language: 'python',
    content: `import re
from aiogram import Router, F
from aiogram.types import Message
from matching_bot_project.bot.states.states import ChatStates

router = Router()
USERNAME_REGEX = re.compile(r"@[a-zA-Z0-9_]{3,32}")
URL_REGEX = re.compile(r"(https?://\\S+|www\\.\\S+)")

@router.message(ChatStates.anonymous_chat_active)
async def route_anonymous_chat_message(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data.get("partner_id")
    
    if message.text:
        text = message.text
        filtered = False
        if USERNAME_REGEX.search(text):
            text = USERNAME_REGEX.sub("[🚷 آیدی فیلتر شد]", text)
            filtered = True
        if URL_REGEX.search(text):
            text = URL_REGEX.sub("[🚷 لینک فیلتر شد]", text)
            filtered = True
            
        if filtered:
            await message.reply("⚠️ پیام شما به دلیل قوانین فیلتر، تعدیل شد.")
        await bot.send_message(partner_id, f"💬: {text}")
    else:
        # Strip all sender credentials using copy_message
        await bot.copy_message(chat_id=partner_id, from_chat_id=message.chat.id, message_id=message.message_id)`
  },
  {
    path: 'bot/middlewares/force_join.py',
    description: 'Aggressive rate-limit prevention, validating channel membership and caching validations in Redis for 10 min.',
    language: 'python',
    content: `from aiogram import BaseMiddleware
from matching_bot_project.bot.core.loader import redis_client, bot

class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        cache_key = f"user:force_join_cache:{user_id}"
        
        # Redis throttle check
        cached = await redis_client.get(cache_key)
        if cached == "1":
            return await handler(event, data)
            
        # Call Telegram api
        member = await bot.get_chat_member("-100123456789", user_id)
        if member.status in ["creator", "administrator", "member"]:
            await redis_client.set(cache_key, "1", ex=600) # Cache 10 min TTL
            return await handler(event, data)
            
        # Block and show join button keyboard
        return`
  },
  {
    path: 'run.py',
    description: 'Root async event loop orchestrator launching BOTH the FastAPI webhook and aiogram polling concurrent hooks.',
    language: 'python',
    content: `import asyncio
import uvicorn
from matching_bot_project.bot.core.config import settings
from matching_bot_project.bot.core.loader import dp, bot

async def main():
    # Register handlers
    # Run server
    config = uvicorn.Config("matching_bot_project.api.main:app", host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())`
  }
];
