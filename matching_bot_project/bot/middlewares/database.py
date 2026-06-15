from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from matching_bot_project.database.session import async_session_factory


class DbSessionMiddleware(BaseMiddleware):
    """
    Injects an active async SQLAlchemy Database Session into the routing stack.
    Each handler can access the session by defining a `db_session` parameter.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_factory() as session:
            data["db_session"] = session
            try:
                result = await handler(event, data)
                # FIX: removed automatic session.commit() here.
                # Committing unconditionally at the middleware level is dangerous:
                # handlers that intentionally do partial work (e.g. deduct VIP quota,
                # then fail before creating the match) would have their incomplete
                # state silently committed. Each handler is responsible for calling
                # db_session.commit() only when its own work is fully complete.
                return result
            except Exception:
                await session.rollback()
                raise
            # FIX: removed explicit session.close() from finally block.
            # async_session_factory() is an AsyncSession context manager — it already
            # calls close() on __aexit__. Calling it again is redundant and can cause
            # a warning or error depending on the SQLAlchemy version.