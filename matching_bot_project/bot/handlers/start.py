import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from matching_bot_project.bot.core.loader import bot, redis_client
from matching_bot_project.bot.core.config import settings
from matching_bot_project.bot.states.states import OnboardingStates
from matching_bot_project.bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from matching_bot_project.bot.keyboards.inline import get_gender_keyboard
from matching_bot_project.database.queries import crud

logger = logging.getLogger(__name__)
router = Router(name="start_handler")


@router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext, db_session: AsyncSession):
    """
    Handles user first system contact (/start).
    Supports Deep Linking for referral checking.
    Syntax: /start ref_12345678
    """
    await state.clear()
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if user and user.completed_registration:
        await message.answer(
            text=f"👋 خوش آمدید مجدد، *{user.first_name}*!\nآماده شروع دیت عاطفی جدید هستید؟ از منوی زیر استفاده کنید👇",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # Check for deep-linked referral code
    referrer_id = None
    command_args = message.text.split()
    if len(command_args) > 1 and command_args[1].startswith("ref_"):
        try:
            ref_id_candidate = int(command_args[1].split("_")[1])
            if ref_id_candidate != tg_id:
                # FIX: verify that the referrer actually exists in DB before storing the ID;
                # otherwise a fake ref_ link silently stores a non-existent user as referrer
                referrer = await crud.get_user_by_tg_id(db_session, ref_id_candidate)
                if referrer:
                    referrer_id = ref_id_candidate
                else:
                    logger.warning("Referral link used with unknown referrer_id=%s", ref_id_candidate)
        except (ValueError, IndexError):
            pass

    if not user:
        user = await crud.create_user(
            session=db_session,
            tg_id=tg_id,
            first_name=first_name,
            username=username,
            referrer_id=referrer_id
        )
        await db_session.commit()

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
    # FIX: unknown gender values (e.g. future "gender_other") silently became "Female";
    # now only known values are accepted and unknown ones are rejected explicitly
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
    # FIX: cancel button must be handled at every FSM step, not only at the city step;
    # otherwise pressing cancel during age entry keeps the user stuck in waiting_for_age
    if message.text == "❌ انصراف و منوی اصلی":
        await state.clear()
        await message.answer("فرآیند ثبت‌نام لغو شد.", reply_markup=get_main_menu_keyboard())
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
        await message.answer("فرآیند ثبت‌نام لغو شد.", reply_markup=get_main_menu_keyboard())
        return

    city_raw = message.text.strip()

    # FIX: validate that city input is not empty after stripping whitespace
    if not city_raw:
        await message.reply("⚠️ نام شهر نمی‌تواند خالی باشد. لطفاً نام شهر خود را وارد کنید:")
        return

    city = city_raw.replace(" ", "_")
    data = await state.get_data()

    gender = data.get("gender")
    age = data.get("age")
    tg_id = message.from_user.id

    # FIX: guard against corrupted/missing FSM data (e.g. if bot restarted mid-registration)
    if not gender or not age:
        logger.error("Missing FSM data during city registration for user %s: gender=%s age=%s", tg_id, gender, age)
        await state.clear()
        await message.answer(
            "⚠️ اطلاعات ثبت‌نام ناقص است. لطفاً دوباره از /start شروع کنید.",
            reply_markup=get_main_menu_keyboard()
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
                "از منوی اصلی زیر استفاده کنید"
            ),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("⚠️ مشکلی در ثبت اطلاعات به وجود آمد. لطفا /start را مجددا ارسال کنید.")