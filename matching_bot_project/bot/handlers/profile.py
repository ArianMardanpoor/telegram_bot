import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import crud
from bot.core.config import settings

logger = logging.getLogger(__name__)
router = Router(name="profile_handler")


@router.message(F.text == "👤 پروفایل من")
async def view_user_profile(message: Message, db_session: AsyncSession):
    """Generates user registered dashboard."""
    tg_id = message.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if not user or not user.completed_registration:
        await message.answer("⚠️ شما هنوز ثبت نام نکرده‌اید! لطفا دکمه /start را ارسال کنید.")
        return

    gender_txt = "آقا 🙋‍♂️" if user.gender == "Male" else "خانم 🙋‍♀️"
    vip_status = "👑 عضو VIP" if user.is_vip else "🏷️ عضو عادی"

    profile_card = (
        "👤 *پروفایل کاربری همسریابی شما:*\n\n"
        f"🆔 شناسه تلگرام: `{user.tg_id}`\n"
        f"🏷️ نام: *{user.first_name}*\n"
        f"🙋‍♂️ جنسیت: *{gender_txt}*\n"
        f"🎂 سن: *{user.age}* سال\n"
        f"📍 شهر: *{user.city.replace('_', ' ')}*\n"
        f"⚡ وضعیت اشتراک: *{vip_status}*\n"
        f"🔋 سهمیه مچینگ ویژه (VIP): *{user.vip_quota} عدد*\n"
    )

    await message.answer(text=profile_card, parse_mode="Markdown")


@router.message(F.text == "🎁 زیرمجموعه‌گیری & VIP")
async def view_referral_panel(message: Message, db_session: AsyncSession):
    """Displays user invite link, rewards, and total referrals."""
    tg_id = message.from_user.id
    user = await crud.get_user_by_tg_id(db_session, tg_id)

    if not user:
        await message.answer("⚠️ کاربری یافت نشد. لطفا /start را بزنید.")
        return

    # Compile the special referral entry point URL
    bot_name = "MatchmakingDatingBot" # Can be loaded from config file
    invite_link = f"https://t.me/{bot_name}?start=ref_{tg_id}"

    ref_text = (
        "🎁 *سیستم کسب سهمیه رایگان مچینگ پیشرفته (VIP):*\n\n"
        "دوستان خود را به ربات همسریابی دعوت کنید و به ازای هر دعوت موفق که ثبت‌نام خود را تکمیل کند، "
        "*۱ سهمیه مچ ویژه (فیلتردار)* دریافت کنید!\n\n"
        f"🔗 *لینک اختصاصی دعوت شما:*\n`{invite_link}`\n\n"
        f"🔋 تعداد مچ‌های پیشرفته باقیمانده شما: *{user.vip_quota} عدد*"
    )

    await message.answer(text=ref_text, parse_mode="Markdown")


@router.message(F.text == "❔ راهنما و پشتیبانی")
async def view_help_panel(message: Message):
    """Displays standard FAQ and support contacts."""
    help_text = (
        "❔ *راهنمای استفاده از ربات همسریابی:*\n\n"
        "1️⃣ ابتدا با منوی پروفایل مشخصات خود را دقیق تنظیم کنید.\n"
        "2️⃣ با دکمه *شروع دیت یابی* وارد صف انتظار مچینگ شوید.\n"
        "3️⃣ سیستم به طور هوشمند و خودکار کاربران جنس مخالف نزدیک شما را پیشنهاد می‌دهد.\n"
        "4️⃣ پس از اتصال، باید در مسابقه پرسشنامه ۲۰ سوالی تفاهم‌سنجی شرکت کنید.\n"
        "5️⃣ در صورتی که پاسخ‌های شما و پارتنر مشترک تایید شود، سیستم چت ناشناس امن را برقرار می‌سازد.\n\n"
        "📌 *پشتیبانی ربات:* @your_support_id"
    )
    await message.answer(text=help_text, parse_mode="Markdown")
