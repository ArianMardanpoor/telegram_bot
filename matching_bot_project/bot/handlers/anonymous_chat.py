import re
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.loader import bot, dp, redis_client
from bot.states.states import ChatStates
from bot.keyboards.inline import get_active_chat_controls
from bot.keyboards.reply import get_main_menu_keyboard
from database.models.models import MatchHistory
from database.queries import crud

logger = logging.getLogger(__name__)
router = Router(name="anonymous_chat_handler")

# Security filters regex patterns
USERNAME_REGEX = re.compile(r"@[a-zA-Z0-9_]{3,32}")
URL_REGEX = re.compile(r"(https?://\S+|www\.\S+|\S+\.(com|ir|org|net|info|me|co)\b)")
PHONE_REGEX = re.compile(r"(\+98|0)?9\d{9}")


def apply_security_filters(text: str) -> tuple[str, bool]:
    """
    Applies all security filters to a text string.
    Returns (filtered_text, was_filtered).
    """
    filtered = False

    if USERNAME_REGEX.search(text):
        text = USERNAME_REGEX.sub("[⚠️ آیدی فیلتر شد]", text)
        filtered = True

    if URL_REGEX.search(text):
        text = URL_REGEX.sub("[⚠️ لینک فیلتر شد]", text)
        filtered = True

    if PHONE_REGEX.search(text):
        text = PHONE_REGEX.sub("[⚠️ تلفن فیلتر شد]", text)
        filtered = True

    return text, filtered


@router.callback_query(F.data.startswith("approve_chat_"))
async def register_chat_consent(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Logs consent replies and opens secure direct channels when mutual agreement is reached."""

    # FIX #5: call.answer() guaranteed to run — answer immediately to prevent Telegram loading state
    await call.answer()

    tg_id = call.from_user.id
    agreement = call.data == "approve_chat_yes"

    active_m = await crud.get_active_match(db_session, tg_id)
    if not active_m:
        await call.message.edit_text("⚠️ دیت مورد نظر یافت نشد یا منقضی شده است.")
        return

    # Delete inline consent buttons
    await call.message.edit_reply_markup(reply_markup=None)

    partner_id = active_m.user_two_id if active_m.user_one_id == tg_id else active_m.user_one_id

    if not agreement:
        # Deactivate match
        active_m.is_active = False
        await db_session.commit()

        # FIX #1: Clear the rejecting user's FSM state
        await state.clear()
        await call.message.answer("❌ گفتگو رد شد. به منوی اصلی بازگشتید.", reply_markup=get_main_menu_keyboard())

        # Notify partner and clear their state
        try:
            p_context = dp.fsm.resolve_context(bot=bot, chat_id=partner_id, user_id=partner_id)
            await p_context.clear()
            await bot.send_message(
                chat_id=partner_id,
                text="⚠️ متاسفانه پارتنر شما با برقراری چت موافقت نکرد. دیت پایان یافت.",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to notify partner {partner_id} of rejection: {e}")

        return

    # User agrees to direct contact — record approval
    if active_m.user_one_id == tg_id:
        active_m.user_one_approved = True
    else:
        active_m.user_two_approved = True

    await db_session.commit()

    if active_m.user_one_approved and active_m.user_two_approved:
        # Dual consent acquired — activate anonymous chat for both parties
        active_m.chat_approved = True
        await db_session.commit()

        # Update Redis status states
        await redis_client.hset(f"user:state:{tg_id}", "status", "chatting")
        await redis_client.hset(f"user:state:{partner_id}", "status", "chatting")

        chat_inst = (
            "🗣️ *اتصال با موفقیت برقرار شد! گفتگو آغاز گردید.*\n\n"
            "🔒 امنیت شما محفوظ است. تلگرام پارتنر پنهان است. "
            "قوانین نظارتی ربات:\n"
            "🚫 فیلتر شدید آیدی تلگرام، شماره تلفن و لینک‌های وب جهت حفظ حریم شخصی فعال است.\n\n"
            "برای پایان گفتگو دکمه شیشه‌ای زیر را بزنید 👇"
        )

        # Setup FSM transitions for both users
        for uid in [tg_id, partner_id]:
            c = dp.fsm.resolve_context(bot=bot, chat_id=uid, user_id=uid)
            await c.set_state(ChatStates.anonymous_chat_active)
            await c.update_data(
                match_history_id=active_m.id,
                partner_id=partner_id if uid == tg_id else tg_id
            )
            await bot.send_message(
                chat_id=uid,
                text=chat_inst,
                reply_markup=get_active_chat_controls(),
                parse_mode="Markdown"
            )
    else:
        await call.message.answer("⏳ موافقت شما ثبت شد. منتظر تایید طرف مقابل بمانید...")


@router.message(ChatStates.anonymous_chat_active)
async def route_anonymous_chat_message(message: Message, state: FSMContext):
    """
    Filters direct chat streams for hyperlinks or usernames.
    Reroutes filtered messages securely using copy_message.
    """
    user_data = await state.get_data()
    partner_id = user_data.get("partner_id")

    if not partner_id:
        await message.answer("⚠️ مکالمه به اتمام رسیده است یا خطایی رخ داد.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return

    if message.text:
        # Filter plain text messages
        filtered_text, was_filtered = apply_security_filters(message.text)

        if was_filtered:
            await message.reply("⚠️ پیام شما به دلیل نقض حریم امنیتی اصلاح و سپس ارسال شد:")

        # FIX #2: Wrap send_message in try/except — partner may have blocked the bot
        try:
            await bot.send_message(chat_id=partner_id, text=f"💬: {filtered_text}")
        except Exception as e:
            logger.error(f"Failed to deliver text message to partner {partner_id}: {e}")
            await message.reply("⚠️ پیام به پارتنر تحویل داده نشد. ممکن است اتصال قطع شده باشد.")

    else:
        # FIX #4: Filter captions on media messages (photo, video, etc.) before forwarding
        raw_caption = message.caption or ""
        filtered_caption, caption_was_filtered = apply_security_filters(raw_caption) if raw_caption else ("", False)

        if caption_was_filtered:
            await message.reply("⚠️ کپشن پیام شما به دلیل نقض حریم امنیتی اصلاح و سپس ارسال شد:")

        try:
            await bot.copy_message(
                chat_id=partner_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                # Pass filtered caption; if no caption existed, pass None to avoid overwriting
                caption=filtered_caption if raw_caption else None
            )
        except Exception as e:
            logger.error(f"Error forwarding media message to partner {partner_id}: {e}")
            await message.reply("⚠️ متاسفانه ارسال این نوع فایل در چت پشتیبانی نمی‌شود.")


@router.callback_query(F.data == "end_active_chat")
async def end_active_anonymous_chat(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Closes dating pipeline and sets users free."""

    # FIX #5: call.answer() guaranteed to run — answer immediately
    await call.answer()

    tg_id = call.from_user.id
    data = await state.get_data()
    partner_id = data.get("partner_id")
    match_id = data.get("match_history_id")

    # Deactivate database match row
    if match_id:
        match_row = await db_session.get(MatchHistory, match_id)
        if match_row:
            match_row.is_active = False
            await db_session.commit()

    # Clean Redis and FSM state for the initiating user
    await redis_client.delete(f"user:state:{tg_id}")
    await state.clear()

    await call.message.edit_text("🛑 گفتگو را پایان دادید. به منوی اصلی بازگشتید.")
    await call.message.answer("منوی اصلی بالا آمد:", reply_markup=get_main_menu_keyboard())

    # FIX #3: Wrap ALL partner cleanup in a single try/except block
    if partner_id:
        try:
            await redis_client.delete(f"user:state:{partner_id}")
            p_context = dp.fsm.resolve_context(bot=bot, chat_id=partner_id, user_id=partner_id)
            await p_context.clear()
            await bot.send_message(
                chat_id=partner_id,
                text="🛑 پارتنر شما گفتگو را خاتمه داد. به منوی اصلی بازگشتید.",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to clean up partner {partner_id} session: {e}")