import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.loader import bot, redis_client
from bot.core.config import settings
from bot.states.states import OnboardingStates
from bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from bot.keyboards.inline import get_gender_keyboard
from database.queries import crud

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

    # Check if user already exists
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
            # Ensure they aren't trying to invite themselves
            if ref_id_candidate != tg_id:
                referrer_id = ref_id_candidate
        except (ValueError, IndexError):
            pass

    # Create user in DB if brand new
    if not user:
        user = await crud.create_user(
            session=db_session,
            tg_id=tg_id,
            first_name=first_name,
            username=username,
            referrer_id=referrer_id
        )
        await db_session.commit()

    # Initiate registration onboarding sequence
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
    gender = "Male" if call.data == "gender_male" else "Female"
    await state.update_data(gender=gender)
    
    # Visual edit callback
    gender_txt = "آقا 🙋‍♂️" if gender == "Male" else "خانم 🙋‍♀️"
    await call.message.edit_text(
        text=f"✅ جنسیت شما ثبت شد: *{gender_txt}*\n\nسن خود را وارد کنید (مثال: 25) 👇",
        parse_mode="Markdown"
    )
    
    await state.set_state(OnboardingStates.waiting_for_age)
    await call.answer()


@router.message(OnboardingStates.waiting_for_age)
async def register_age(message: Message, state: FSMContext):
    """Validates user age input and prompts city onboarding rules."""
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
    """Saves city onboarding details, completes registration, rewards referrers, and launches main menu."""
    if message.text == "❌ انصراف و منوی اصلی":
        await state.clear()
        await message.answer("فرآیند ثبت نام خروج شدی.", reply_markup=get_main_menu_keyboard())
        return

    city = message.text.strip().replace(" ", "_")
    data = await state.get_data()
    
    gender = data.get("gender")
    age = data.get("age")
    tg_id = message.from_user.id

    # Complete DB registration and reward potential invite referrers automatically
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
