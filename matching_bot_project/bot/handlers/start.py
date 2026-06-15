import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from matching_bot_project.bot.core.loader import bot, redis_client
from matching_bot_project.bot.core.config import settings
from matching_bot_project.bot.states.states import OnboardingStates, ChatStates, MatchingStates, QuestionnaireStates
from matching_bot_project.bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from matching_bot_project.bot.keyboards.inline import get_gender_keyboard
from matching_bot_project.database.queries import crud

logger = logging.getLogger(__name__)
router = Router(name="start_handler")


@router.message(CommandStart())
async def handle_start_command(message: Message, command: CommandObject, state: FSMContext, db_session: AsyncSession):
    """
    Handles user first system contact (/start).
    Supports Deep Linking for referral checking via aiogram CommandObject.
    """
    tg_id = message.from_user.id
    
    # CRITICAL FIX 1: Prevent FSM Hijacking if user sends /start while in an active match/chat
    current_state = await state.get_state()
    active_states = [
        ChatStates.anonymous_chat_active.state,
        MatchingStates.waiting_in_queue.state,
        QuestionnaireStates.answering_questions.state,
        QuestionnaireStates.waiting_for_partner_answer.state
    ]
    if current_state in active_states:
        await message.answer("⚠️ شما در میانه یک فرآیند فعال (مچینگ، پرسشنامه یا چت) هستید. لطفاً ابتدا آن را پایان دهید.")
        return

    # Now it's safe to clear any residual broken states
    await state.clear()

    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if user and user.completed_registration:
        await message.answer(
            text=f"👋 خوش آمدید مجدد، *{user.first_name}*!\nآماده شروع دیت عاطفی جدید هستید؟ از منوی زیر استفاده کنید👇",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # CRITICAL FIX 2: Correct Deep Link parsing using Aiogram 3.x CommandObject
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            ref_id_candidate = int(command.args.split("_")[1])
            if ref_id_candidate != tg_id:
                referrer = await crud.get_user_by_tg_id(db_session, ref_id_candidate)
                if referrer:
                    referrer_id = ref_id_candidate
                else:
                    logger.warning("Referral link used with unknown referrer_id=%s", ref_id_candidate)
        except (ValueError, IndexError):
            pass

    if not user:
        try:
            user = await crud.create_user(
                session=db_session,
                tg_id=tg_id,
                first_name=message.from_user.first_name or "کاربر",
                username=message.from_user.username,
                referrer_id=referrer_id
            )
            await db_session.commit()
        except IntegrityError:
            # CRITICAL FIX 3: Handle Race Condition if user spams /start before DB commits
            await db_session.rollback()
            user = await crud.get_user_by_tg_id(db_session, tg_id)

    await message.answer(
        text=(
            "🎉 *به بزرگترین ربات مچ‌یابی و دیت‌یابی ناشناس خوش آمدید!*\n\n"
            "برای شروع مچینگ اصولی، لازم است در کمتر از ۱ دقیقه اطلاعات هویتی خود را ثبت کنید.\n\n"
            "جنسیت خود را انتخاب کنید 👇"
        ),
        reply_markup=get_gender_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(OnboardingStates.waiting_for_gender)


@router.callback_query(OnboardingStates.waiting_for_gender, F.data.startswith("gender_"))
async def register_gender(call: CallbackQuery, state: FSMContext):
    """Registers user gender details and shifts states to age capture."""
    if call.data == "gender_male":
        gender = "Male"
        gender_txt = "آقا 🙋‍♂️"
    elif call.data == "gender_female":
        gender = "Female"
        gender_txt = "خانم 🙋‍♀️"
    else:
        logger.warning("Unexpected gender callback value: %s", call.data)
        await call.answer("⚠️ گزینه نامعتبر. لطفاً یکی از دکمه‌های موجود را انتخاب کنید.", show_alert=True)
        return

    await state.update_data(gender=gender)
    await call.message.edit_text(
        text=f"✅ جنسیت شما ثبت شد: *{gender_txt}*\n\nسن خود را وارد کنید (مثال: 25) 👇",
        parse_mode="Markdown"
    )
    await state.set_state(OnboardingStates.waiting_for_age)
    await call.answer()


@router.message(OnboardingStates.waiting_for_age)
async def register_age(message: Message, state: FSMContext):
    """Validates user age input and prompts city onboarding."""
    # CRITICAL FIX 4: Prevent giving main menu to an unregistered user
    if message.text == "❌ انصراف و منوی اصلی":
        await state.clear()
        await message.answer("فرآیند ثبت‌نام لغو شد. برای شروع مجدد /start را ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return

    try:
        age = int(message.text)
        if age < 18 or age > 75:
            await message.reply("⚠️ سن شما باید عددی بین ۱۸ تا ۷۵ باشد. مجدداً سن خود را وارد کنید:")
            return
    except ValueError:
        await message.reply("⚠️ سن را به صورت عددی وارد کنید. سن شما چیست؟")
        return

    await state.update_data(age=age)
    await message.answer(
        text="✅ سن شما ثبت شد.\n\nاکنون نام شهر محل سکونت خود را تایپ کنید (مثال: تهران) 👇",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OnboardingStates.waiting_for_city)


@router.message(OnboardingStates.waiting_for_city)
async def register_city(message: Message, state: FSMContext, db_session: AsyncSession):
    """Saves city, completes registration, rewards referrers, and launches main menu."""
    if message.text == "❌ انصراف و منوی اصلی":
        await state.clear()
        await message.answer("فرآیند ثبت‌نام لغو شد. برای شروع مجدد /start را ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return

    city_raw = message.text.strip()

    # CRITICAL FIX 5: Validate text length to prevent DB String overflow attacks
    if not city_raw or len(city_raw) > 30:
        await message.reply("⚠️ نام شهر نامعتبر است یا بسیار طولانی است. لطفاً یک نام معتبر وارد کنید:")
        return

    city = city_raw.replace(" ", "_")
    data = await state.get_data()

    gender = data.get("gender")
    age = data.get("age")
    tg_id = message.from_user.id

    if not gender or not age:
        logger.error("Missing FSM data during city registration for user %s: gender=%s age=%s", tg_id, gender, age)
        await state.clear()
        await message.answer(
            "⚠️ اطلاعات ثبت‌نام ناقص است. لطفاً دوباره از /start شروع کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    success = await crud.complete_user_registration(
        session=db_session,
        tg_id=tg_id,
        gender=gender,
        age=age,
        city=city
    )

    if success:
        await db_session.commit()
        await state.clear()
        await message.answer(
            text=(
                "🥳 *ثبت نام شما با موفقیت تکمیل شد!*\n"
                "حالا می‌توانید وارد مچ یابی یا دیت یابی شده و نیمه گم‌شده خود را پیدا کنید.\n\n"
                "از منوی اصلی زیر استفاده کنید👇"
            ),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("⚠️ مشکلی در ثبت اطلاعات به وجود آمد. لطفا /start را مجددا ارسال کنید.")import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from matching_bot_project.bot.core.loader import bot, redis_client
from matching_bot_project.bot.core.config import settings
from matching_bot_project.bot.states.states import OnboardingStates, ChatStates, MatchingStates, QuestionnaireStates
from matching_bot_project.bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from matching_bot_project.bot.keyboards.inline import get_gender_keyboard
from matching_bot_project.database.queries import crud

logger = logging.getLogger(__name__)
router = Router(name="start_handler")


@router.message(CommandStart())
async def handle_start_command(message: Message, command: CommandObject, state: FSMContext, db_session: AsyncSession):
    """
    Handles user first system contact (/start).
    Supports Deep Linking for referral checking via aiogram CommandObject.
    """
    tg_id = message.from_user.id
    
    # CRITICAL FIX 1: Prevent FSM Hijacking if user sends /start while in an active match/chat
    current_state = await state.get_state()
    active_states = [
        ChatStates.anonymous_chat_active.state,
        MatchingStates.waiting_in_queue.state,
        QuestionnaireStates.answering_questions.state,
        QuestionnaireStates.waiting_for_partner_answer.state
    ]
    if current_state in active_states:
        await message.answer("⚠️ شما در میانه یک فرآیند فعال (مچینگ، پرسشنامه یا چت) هستید. لطفاً ابتدا آن را پایان دهید.")
        return

    # Now it's safe to clear any residual broken states
    await state.clear()

    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if user and user.completed_registration:
        await message.answer(
            text=f"👋 خوش آمدید مجدد، *{user.first_name}*!\nآماده شروع دیت عاطفی جدید هستید؟ از منوی زیر استفاده کنید👇",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # CRITICAL FIX 2: Correct Deep Link parsing using Aiogram 3.x CommandObject
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            ref_id_candidate = int(command.args.split("_")[1])
            if ref_id_candidate != tg_id:
                referrer = await crud.get_user_by_tg_id(db_session, ref_id_candidate)
                if referrer:
                    referrer_id = ref_id_candidate
                else:
                    logger.warning("Referral link used with unknown referrer_id=%s", ref_id_candidate)
        except (ValueError, IndexError):
            pass

    if not user:
        try:
            user = await crud.create_user(
                session=db_session,
                tg_id=tg_id,
                first_name=message.from_user.first_name or "کاربر",
                username=message.from_user.username,
                referrer_id=referrer_id
            )
            await db_session.commit()
        except IntegrityError:
            # CRITICAL FIX 3: Handle Race Condition if user spams /start before DB commits
            await db_session.rollback()
            user = await crud.get_user_by_tg_id(db_session, tg_id)

    await message.answer(
        text=(
            "🎉 *به بزرگترین ربات مچ‌یابی و دیت‌یابی ناشناس خوش آمدید!*\n\n"
            "برای شروع مچینگ اصولی، لازم است در کمتر از ۱ دقیقه اطلاعات هویتی خود را ثبت کنید.\n\n"
            "جنسیت خود را انتخاب کنید 👇"
        ),
        reply_markup=get_gender_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(OnboardingStates.waiting_for_gender)


@router.callback_query(OnboardingStates.waiting_for_gender, F.data.startswith("gender_"))
async def register_gender(call: CallbackQuery, state: FSMContext):
    """Registers user gender details and shifts states to age capture."""
    if call.data == "gender_male":
        gender = "Male"
        gender_txt = "آقا 🙋‍♂️"
    elif call.data == "gender_female":
        gender = "Female"
        gender_txt = "خانم 🙋‍♀️"
    else:
        logger.warning("Unexpected gender callback value: %s", call.data)
        await call.answer("⚠️ گزینه نامعتبر. لطفاً یکی از دکمه‌های موجود را انتخاب کنید.", show_alert=True)
        return

    await state.update_data(gender=gender)
    await call.message.edit_text(
        text=f"✅ جنسیت شما ثبت شد: *{gender_txt}*\n\nسن خود را وارد کنید (مثال: 25) 👇",
        parse_mode="Markdown"
    )
    await state.set_state(OnboardingStates.waiting_for_age)
    await call.answer()


@router.message(OnboardingStates.waiting_for_age)
async def register_age(message: Message, state: FSMContext):
    """Validates user age input and prompts city onboarding."""
    # CRITICAL FIX 4: Prevent giving main menu to an unregistered user
    if message.text == "❌ انصراف و منوی اصلی":
        await state.clear()
        await message.answer("فرآیند ثبت‌نام لغو شد. برای شروع مجدد /start را ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return

    try:
        age = int(message.text)
        if age < 18 or age > 75:
            await message.reply("⚠️ سن شما باید عددی بین ۱۸ تا ۷۵ باشد. مجدداً سن خود را وارد کنید:")
            return
    except ValueError:
        await message.reply("⚠️ سن را به صورت عددی وارد کنید. سن شما چیست؟")
        return

    await state.update_data(age=age)
    await message.answer(
        text="✅ سن شما ثبت شد.\n\nاکنون نام شهر محل سکونت خود را تایپ کنید (مثال: تهران) 👇",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OnboardingStates.waiting_for_city)


@router.message(OnboardingStates.waiting_for_city)
async def register_city(message: Message, state: FSMContext, db_session: AsyncSession):
    """Saves city, completes registration, rewards referrers, and launches main menu."""
    if message.text == "❌ انصراف و منوی اصلی":
        await state.clear()
        await message.answer("فرآیند ثبت‌نام لغو شد. برای شروع مجدد /start را ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return

    city_raw = message.text.strip()

    # CRITICAL FIX 5: Validate text length to prevent DB String overflow attacks
    if not city_raw or len(city_raw) > 30:
        await message.reply("⚠️ نام شهر نامعتبر است یا بسیار طولانی است. لطفاً یک نام معتبر وارد کنید:")
        return

    city = city_raw.replace(" ", "_")
    data = await state.get_data()

    gender = data.get("gender")
    age = data.get("age")
    tg_id = message.from_user.id

    if not gender or not age:
        logger.error("Missing FSM data during city registration for user %s: gender=%s age=%s", tg_id, gender, age)
        await state.clear()
        await message.answer(
            "⚠️ اطلاعات ثبت‌نام ناقص است. لطفاً دوباره از /start شروع کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    success = await crud.complete_user_registration(
        session=db_session,
        tg_id=tg_id,
        gender=gender,
        age=age,
        city=city
    )

    if success:
        await db_session.commit()
        await state.clear()
        await message.answer(
            text=(
                "🥳 *ثبت نام شما با موفقیت تکمیل شد!*\n"
                "حالا می‌توانید وارد مچ یابی یا دیت یابی شده و نیمه گم‌شده خود را پیدا کنید.\n\n"
                "از منوی اصلی زیر استفاده کنید👇"
            ),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("⚠️ مشکلی در ثبت اطلاعات به وجود آمد. لطفا /start را مجددا ارسال کنید.")