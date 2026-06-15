import asyncio
import logging
from typing import List, Union
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

logger = logging.getLogger(__name__)

class BroadcastWorker:
    """
    Asynchronous notification broadcast service.
    Sends bulk messages and media without locking the primary thread of aiogram or FastAPI.
    Gracefully catches and filters out BotBlocked (forbidden) or deactivated user exceptions.
    """
    def __init__(self, bot: Bot):
        self.bot = bot
        self._is_running = False

    async def broadcast_message(self, user_ids: List[int], text: str, delay_ms: int = 50) -> dict:
        """
        Sends an asynchronous broadcast message.
        Rate limiting is respected (Telegram allows 30 messages per second).
        
        :param user_ids: Target telegram user IDs
        :param text: Text string content
        :param delay_ms: Millisecond sleep interval between delivery tasks (to stay within rate limits)
        :return: Metrics status dictionary
        """
        sent_count = 0
        blocked_count = 0
        error_count = 0
        
        logger.info(f"Starting async broadcast message to {len(user_ids)} users.")
        
        for index, tg_id in enumerate(user_ids):
            try:
                await self.bot.send_message(chat_id=tg_id, text=text)
                sent_count += 1
            except TelegramForbiddenError:
                # User has blocked the bot or chat was deleted
                logger.warning(f"Failed delivery: Bot was blocked by user ID {tg_id}")
                blocked_count += 1
            except TelegramAPIError as e:
                logger.error(f"Telegram API Exception sending broadcast to {tg_id}: {str(e)}")
                error_count += 1
            except Exception as e:
                logger.error(f"General exception sending broadcast to {tg_id}: {str(e)}")
                error_count += 1

            # Sleep briefly to ensure compliance with Telegram API rate-limiting rules (30 msgs/sec max)
            if index < len(user_ids) - 1:
                await asyncio.sleep(delay_ms / 1000.0)

        logger.info(f"Broadcast completed. Success: {sent_count}, Blocked: {blocked_count}, Failed: {error_count}")
        return {
            "success": sent_count,
            "blocked": blocked_count,
            "failed": error_count,
            "total_scope": len(user_ids)
        }

    def start_background_broadcast(self, user_ids: List[int], text: str, delay_ms: int = 50):
        """Dispatches the broadcast inside the container event loop asynchronously."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.broadcast_message(user_ids, text, delay_ms))
