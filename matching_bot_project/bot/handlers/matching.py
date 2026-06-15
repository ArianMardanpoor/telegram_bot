import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from sqlalchemy.ext.asyncio import AsyncSession

from matching_bot_project.bot.core.loader import bot, matching_engine, dp
from matching_bot_project.bot.states.states import MatchingStates, QuestionnaireStates
from matching_bot_project.bot.keyboards.inline import get_matching_type_keyboard, get_question_reply_keyboard
from matching_bot_project.bot.keyboards.reply import get_cancel_keyboard, get_main_menu_keyboard
from matching_bot_project.database.queries import crud

logger = logging.getLogger(__name__)
router = Router(name="matching_handler")


def get_user_state(user_id: int) -> FSMContext:
    """Helper method to correctly resolve FSM context for any user in aiogram 3.x"""
    return FSMContext(
        storage=dp.storage,
        key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    )


@router.message(F.text == "🎯 شروع دیت یابی (Matching)")
async def prompt_matching_options(message: Message, db_session: AsyncSession):
    """Presents user with selection options: Free or VIP matching."""
    tg_id = message.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if not user or not user.completed_registration:
        await message.answer("⚠️ شما هنوز ثبت نام نکرده‌اید! لطفا دکمه /start را ارسال کنید.")
        return

    active_match = await crud.get_active_match(db_session, tg_id)
    if active_match:
        await message.answer("⚠️ شما در حال حاضر در یک دیت فعال حضور دارید! لطفاً ابتدا آن را پایان دهید.")
        return

    await message.answer(
        text=(
            "🎯 *نوع مچ‌یابی و دیت مورد نظر خود را انتخاب کنید:*\n\n"
            "🎲 *مچ تصادفی:* دیت با جنس مخالف به صورت کاملا رایگان و کشوری.\n\n"
            "👑 *مچ پیشرفته (VIP):* مچینگ اختصاصی با پارتنر هم‌شهری شما (نیاز به سهمیه)."
        ),
        reply_markup=get_matching_type_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "❌ انصراف و منوی اصلی")
async def cancel_queue_operations(message: Message, state: FSMContext):
    """Gracefully exits wait queues and clears states."""
    tg_id = message.from_user.id
    
    # Check if user is actually in queue before removing
    current_state = await state.get_state()
    if current_state == MatchingStates.waiting_in_queue:
        await matching_engine.remove_from_queue(tg_id)
    
    await state.clear()
    await message.answer(
        text="🛑 عملیات لغو شد. به منوی اصلی بازگشتید.",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "match_random")
async def start_free_matching_process(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Launches opposite gender list pooling via Redis."""
    # CRITICAL FIX 1: Prevent duplicate queueing on spam clicks
    current_state = await state.get_state()
    if current_state == MatchingStates.waiting_in_queue:
        await call.answer("⚠️ شما در حال حاضر در صف انتظار هستید!", show_alert=True)
        return

    # Lock the state immediately to prevent race conditions
    await state.set_state(MatchingStates.waiting_in_queue)
    await call.answer()

    tg_id = call.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    await call.message.edit_text(
        text="🔍 *در حال جستجوی پارتنر مناسب (جنس مخالف) برای شما...*\n\nلطفا شکیبا باشید. به محض یافتن جفت، ربات اطلاع خواهد داد.",
        parse_mode="Markdown"
    )
    await call.message.answer(
        text="می‌توانید هر زمان خواستید از دکمه لغو استفاده کنید:",
        reply_markup=get_cancel_keyboard()
    )

    matched_partner_id = await matching_engine.find_match(
        tg_id=tg_id,
        gender=user.gender,
        is_vip=False
    )

    # CRITICAL FIX 3: Prevent Ghost Matches (Self-Matching)
    if matched_partner_id and matched_partner_id != tg_id:
        await _clear_user_queue_state(matched_partner_id)
        await state.clear()
        await handle_successful_match(db_session, tg_id, matched_partner_id)
    elif matched_partner_id == tg_id:
        logger.error(f"Ghost match detected! User {tg_id} matched with themselves.")
        await matching_engine.remove_from_queue(tg_id)
        await state.clear()
        await call.message.answer("⚠️ خطای سیستم در مچ‌یابی. لطفاً دوباره تلاش کنید.", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "match_vip")
async def start_vip_matching_process(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Enforces VIP and location matching rules."""
    # CRITICAL FIX 1: Prevent duplicate queueing and quota drain on spam clicks
    current_state = await state.get_state()
    if current_state == MatchingStates.waiting_in_queue:
        await call.answer("⚠️ شما در حال حاضر در صف انتظار هستید!", show_alert=True)
        return

    tg_id = call.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if user.vip_quota <= 0 and not user.is_vip:
        await call.answer("❌ سهمیه VIP شما کافی نیست!", show_alert=True)
        await call.message.edit_text(
            text="❌ *خطا: سهمیه مچ ویژه شما به پایان رسیده است!*\n\nجهت دریافت سهمیه رایگان، از دکمه *🎁 زیرمجموعه‌گیری* در منوی اصلی اقدام کنید.",
            parse_mode="Markdown"
        )
        return

    # Lock state immediately before DB transaction
    await state.set_state(MatchingStates.waiting_in_queue)

    if not user.is_vip:
        user.vip_quota -= 1
        await db_session.commit()
        await db_session.refresh(user)

    await call.message.edit_text(
        text=f"🔍 *در حال مچ‌یابی فیلتردار (هم‌شهری شما در '{user.city.replace('_', ' ')}') ...*\n\n(۱ عدد سهمیه مصرف شد. سهمیه باقیمانده: {user.vip_quota} عدد)",
        parse_mode="Markdown"
    )
    await call.message.answer(text="در صورت تمایل به خروج از صف:", reply_markup=get_cancel_keyboard())
    await call.answer()

    matched_partner_id = await matching_engine.find_match(
        tg_id=tg_id,
        gender=user.gender,
        is_vip=True,
        city=user.city
    )

    if matched_partner_id and matched_partner_id != tg_id:
        await _clear_user_queue_state(matched_partner_id)
        await state.clear()
        await handle_successful_match(db_session, tg_id, matched_partner_id)
    elif matched_partner_id == tg_id:
        logger.error(f"Ghost match detected! User {tg_id} matched with themselves.")
        await matching_engine.remove_from_queue(tg_id)
        await state.clear()
        
        # Rollback the quota since match failed
        if not user.is_vip:
            user.vip_quota += 1
            await db_session.commit()
            
        await call.message.answer("⚠️ خطای سیستم در مچ‌یابی. سهمیه شما بازگردانده شد. لطفاً دوباره تلاش کنید.", reply_markup=get_main_menu_keyboard())


async def _clear_user_queue_state(tg_id: int) -> None:
    """Clears FSM queue state for a user who was waiting in queue and has now been matched."""
    try:
        context = get_user_state(tg_id)
        await context.clear()
    except Exception as e:
        logger.warning("Could not clear queue state for user %s: %s", tg_id, e)


async def handle_successful_match(session: AsyncSession, user_one_id: int, user_two_id: int):
    """Initializes dating session between two users simultaneously."""
    match_history = await crud.create_match_history(session, user_one_id, user_two_id)
    await session.commit()

    user_one = await crud.get_user_by_tg_id(session, user_one_id)
    user_two = await crud.get_user_by_tg_id(session, user_two_id)

    pool = await crud.get_random_questions(session, 20)

    if not pool:
        logger.error("No questions available in the database for match %s.", match_history.id)
        for uid in (user_one_id, user_two_id):
            await bot.send_message(
                chat_id=uid,
                text="⚠️ متأسفانه در حال حاضر سوالی برای شروع مسابقه وجود ندارد. لطفاً دوباره تلاش کنید.",
                reply_markup=get_main_menu_keyboard()
            )
        return

    q_ids_serialized = ",".join([str(q.id) for q in pool])
    await matching_engine.redis.set(f"match:questions:{match_history.id}", q_ids_serialized)
    await matching_engine.redis.set(f"match:current_q_index:{match_history.id}", "0")

    await deliver_match_start_notification(
        target_id=user_one_id,
        partner_name=user_two.first_name,
        partner_age=user_two.age,
        partner_city=user_two.city,
        match_history_id=match_history.id,
        first_question=pool[0]
    )

    await deliver_match_start_notification(
        target_id=user_two_id,
        partner_name=user_one.first_name,
        partner_age=user_one.age,
        partner_city=user_one.city,
        match_history_id=match_history.id,
        first_question=pool[0]
    )


async def deliver_match_start_notification(
    target_id: int,
    partner_name: str,
    partner_age: int,
    partner_city: str,
    match_history_id: int,
    first_question
) -> None:
    """Constructs match text overlay, sets FSM state, and posts the first question."""
    intro_txt = (
        "🔥 *تبریک! یک پارتنر همسان پیدا شد!*\n\n"
        f"👤 نام: *{partner_name}*\n"
        f"🎂 سن: *{partner_age}* سال\n"
        f"📍 شهر سکونت: *{partner_city.replace('_', ' ')}*\n"
        "─────────────────\n"
        "🎮 *شروع مسابقه تفاهم‌سنجی (۲۰ سوال):*\n"
        "جهت شروع چت و تایید اتصال نهایی، هر دو نفر باید به پرسشنامه تفاهم پاسخ دهید.\n"
        "اگر ظرف ۳ دقیقه به سوال پاسخ ندهید، دیت برای هر دو طرف لغو می‌شود.\n\n"
        f"❓ *سوال اول:* {first_question.question_text}\n"
        f"🅰️ گزینه اول: {first_question.option_a}\n"
        f"🅱️ گزینه دوم: {first_question.option_b}"
    )

    # CRITICAL FIX 4: Correct FSM Context manipulation
    try:
        context = get_user_state(target_id)
        await context.set_state(QuestionnaireStates.answering_questions)
        await context.update_data(
            match_history_id=match_history_id,
            current_question_index=0
        )
    except Exception as e:
        logger.error("Failed to set FSM state for user %s: %s", target_id, e)
        return

    try:
        await bot.send_message(
            chat_id=target_id,
            text=intro_txt,
            reply_markup=get_question_reply_keyboard(first_question.id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error("Failed to send match notification to user %s: %s", target_id, e)