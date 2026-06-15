from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard selecting gender details during onboarding."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🙋‍♂️ آقا (Male)", callback_data="gender_male"),
            InlineKeyboardButton(text="🙋‍♀️ خانم (Female)", callback_data="gender_female")
        ]
    ])


def get_matching_type_keyboard() -> InlineKeyboardMarkup:
    """Returns matching selection panel (Free vs VIP matching type)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 مچ تصادفی (رایگان)", callback_data="match_random")
        ],
        [
            InlineKeyboardButton(text="⭐ مچ پیشرفته VIP (فیلتردار)", callback_data="match_vip")
        ]
    ])


def get_question_reply_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Inline options corresponding to the active questionnaire bank query."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🅰️ گزینه اول", callback_data=f"ans_a_{question_id}"),
            InlineKeyboardButton(text="🅱️ گزینه دوم", callback_data=f"ans_b_{question_id}")
        ]
    ])


def get_chat_approval_keyboard() -> InlineKeyboardMarkup:
    """End-game consent panel enabling anonymous chat rooms."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقم؛ شروع گفتگو ناشناس", callback_data="approve_chat_yes"),
            InlineKeyboardButton(text="❌ خیر؛ خروج از لیست", callback_data="approve_chat_no")
        ]
    ])


def get_active_chat_controls() -> InlineKeyboardMarkup:
    """Active controls during anonymized chat streams."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛑 پایان دادن به چت و مچ یابی جدید", callback_data="end_active_chat")
        ]
    ])
