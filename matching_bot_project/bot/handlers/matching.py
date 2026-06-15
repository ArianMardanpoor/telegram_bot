import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.loader import bot, matching_engine, dp
from bot.states.states import MatchingStates, QuestionnaireStates
from bot.keyboards.inline import get_matching_type_keyboard, get_question_reply_keyboard
from bot.keyboards.reply import get_cancel_keyboard, get_main_menu_keyboard
from database.queries import crud

logger = logging.getLogger(__name__)
router = Router(name="matching_handler")


@router.message(F.text == "🎯 شروع دیت یابی (Matching)")
async def prompt_matching_options(message: Message, db_session: AsyncSession):
    """Presents user with selection options: Free or VIP matching."""
    tg_id = message.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if not user or not user.completed_registration:
        await message.answer("⚠️ شما هنوز ثبت نام نکرده‌اید! لطفا دکمه /start را ارسال کنید.")
        return

    # Check database or redis states to block double-queue searches
    active_match = await crud.get_active_match(db_session, tg_id)
    if active_match:
        await message.answer("⚠️ شما در حال حاضر در یک دیت فعال حضور دارید! لطفاً ابتدا آن را پایان دهید.")
        return

    await message.answer(
        text=(
            "🎯 *نوع مچ‌یابی و دیت مورد نظر خود را انتخاب کنید:*\n\n"
            "🎲 *مچ تصادفی:* همسر مچینگ با جنس مخالف به صورت کاملا رایگان و کشوری.\n\n"
            "👑 *مچ پیشرفته (VIP):* مچینگ اختصاصی با پارتنر جنس مخالف هم‌شهری شما (نیاز به سهمیه)."
        ),
        reply_markup=get_matching_type_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "❌ انصراف و منوی اصلی")
async def cancel_queue_operations(message: Message, state: FSMContext, db_session: AsyncSession):
    """Gracefully exits wait queues and clears states."""
    tg_id = message.from_user.id
    await matching_engine.remove_from_queue(tg_id)
    
    # Also reset FSM context
    await state.clear()
    await message.answer(
        text="🛑 صف جستجو برای همسان‌یابی لغو شد. به منوی اصلی بازگشتید.",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "match_random")
async def start_free_matching_process(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Launches opposite gender list pooling via Redis."""
    tg_id = call.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    # Trigger wait queue screen overlay
    await call.message.edit_text(
        text="🔍 *در حال جستجوی پارتنر مناسب (جنس مخالف) برای شما...*\n\nلطفا شکیبا باشید. به محض یافتن جفت، ربات اطلاع خواهد داد.",
        parse_mode="Markdown"
    )
    
    # Show main cancel button overlay
    await call.message.answer(
        text="می‌توانید هر زمان خواستید از دکمه لغو زیر استفاده کنید:",
        reply_markup=get_cancel_keyboard()
    )

    # Try matching immediately
    matched_partner_id = await matching_engine.find_match(
        tg_id=tg_id,
        gender=user.gender,
        is_vip=False
    )

    if matched_partner_id:
        await handle_successful_match(db_session, tg_id, matched_partner_id, state)
    else:
        # User registered inside the queue list
        await state.set_state(MatchingStates.waiting_in_queue)
        
    await call.answer()


@router.callback_query(F.data == "match_vip")
async def start_vip_matching_process(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Enforces VIP and location matching matching rules."""
    tg_id = call.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if user.vip_quota <= 0 and not user.is_vip:
         await call.message.edit_text(
             text="❌ *خطا: سهمیه مچ ویژه شما به پایان رسیده است!*\n\nجهت دریافت سهمیه رایگان، از دکمه *🎁 زیرمجموعه‌گیری* در منوی اصلی اقدام کنید.",
             parse_mode="Markdown"
         )
         await call.answer()
         return

    # Deduct quota from User record
    if not user.is_vip:
         user.vip_quota -= 1
         
    await call.message.edit_text(
        text=f"🔍 *در حال مچ‌یابی فیلتردار (هم‌شهری شما در '{user.city.replace('_', ' ')}') ...*\n\n(۱ عدد سهمیه مصرف شد. سهمیه باقیمانده: {user.vip_quota} عدد)",
        parse_mode="Markdown"
    )
    await call.message.answer(text="در صورت تمایل به خروج از صف:", reply_markup=get_cancel_keyboard())

    # Locate filtered matches utilizing locations
    matched_partner_id = await matching_engine.find_match(
        tg_id=tg_id,
        gender=user.gender,
        is_vip=True,
        city=user.city
    )

    if matched_partner_id:
        await handle_successful_match(db_session, tg_id, matched_partner_id, state)
    else:
        await state.set_state(MatchingStates.waiting_in_queue)

    await call.answer()


async def handle_successful_match(session: AsyncSession, user_one_id: int, user_two_id: int, state: FSMContext):
    """Initializes dating session between two users simultaneously."""
    # Write Match record logger to base tables
    match_history = await crud.create_match_history(session, user_one_id, user_two_id)
    await session.commit()

    # Retrieve partner profiles
    user_one = await crud.get_user_by_tg_id(session, user_one_id)
    user_two = await crud.get_user_by_tg_id(session, user_two_id)

    # Gather random questions for this specific round from SQL Questions library
    pool = await crud.get_random_questions(session, 20)
    
    # Store active questions IDs in redis for fast synchronization index matching
    q_ids_serialized = ",".join([str(q.id) for q in pool])
    await matching_engine.redis.set(f"match:questions:{match_history.id}", q_ids_serialized)
    await matching_engine.redis.set(f"match:current_q_index:{match_history.id}", "0")

    # Notify USER ONE
    await deliver_match_start_notification(
        target_id=user_one_id,
        partner_name=user_two.first_name,
        partner_age=user_two.age,
        partner_city=user_two.city,
        match_history_id=match_history.id,
        first_question=pool[0]
    )

    # Notify USER TWO
    await deliver_match_start_notification(
        target_id=user_two_id,
        partner_name=user_one.first_name,
        partner_age=user_one.age,
        partner_city=user_one.city,
        match_history_id=match_history.id,
        first_question=pool[0]
    )


async def deliver_match_start_notification(target_id: int, partner_name: str, partner_age: int, partner_city: str, match_history_id: int, first_question):
    """Constructs match text overlay and posts first questions."""
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

    # Set FSM state on partner contexts
    # Since we can obtain user context by using dispatcher fsm, we set custom state via key
    context = dp.fsm.resolve_context(bot=bot, chat_id=target_id, user_id=target_id)
    await context.set_state(QuestionnaireStates.answering_questions)
    await context.update_data(
        match_history_id=match_history_id,
        current_question_index=0
    )

    await bot.send_message(
        chat_id=target_id,
        text=intro_txt,
        reply_markup=get_question_reply_keyboard(first_question.id),
        parse_mode="Markdown"
    )
