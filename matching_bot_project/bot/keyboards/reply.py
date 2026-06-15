from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Returns the primary Persian reply keyboard overlay."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 شروع دیت یابی (Matching)")
            ],
            [
                KeyboardButton(text="👤 پروفایل من"),
                KeyboardButton(text="🎁 زیرمجموعه‌گیری & VIP")
            ],
            [
                KeyboardButton(text="❔ راهنما و پشتیبانی")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="منوی خود را انتخاب کنید"
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Standard operation interruption Reply overlay."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❌ انصراف و منوی اصلی")
            ]
        ],
        resize_keyboard=True,
        # FIX: added input_field_placeholder so the user sees a contextual hint
        # instead of the default Telegram placeholder while waiting in queue
        input_field_placeholder="در صف انتظار..."
    )