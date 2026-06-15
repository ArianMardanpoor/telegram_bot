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
    # FIX: validate question_id range so the generated callback_data never exceeds
    # Telegram's 64-byte hard limit (e.g. "ans_a_" + 58-digit number would be silently
    # truncated or rejected by the API, breaking the ans_ parser in the handler)
    if not isinstance(question_id, int) or question_id < 0:
        raise ValueError(f"Invalid question_id for keyboard generation: {question_id!r}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🅰️ گزینه اول", callback_data=f"ans_a_{question_id}"),
            InlineKeyboardButton(text="🅱️ گزینه دوم", callback_data=f"ans_b_{question_id}")
        ]
    ])


def get_chat_approval_keyboard() -> InlineKeyboardMarkup:
    """End-game consent panel enabling anonymous chat rooms."""
    # FIX: two buttons with long Persian text placed side by side will overflow on narrow
    # screens and become untappable; split into separate rows for reliable UX on mobile
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقم؛ شروع گفتگو ناشناس", callback_data="chat_approve")
        ],
        [
            InlineKeyboardButton(text="❌ خیر؛ خروج از لیست", callback_data="chat_decline")
        ]
    ])


def get_active_chat_controls() -> InlineKeyboardMarkup:
    """Active controls during anonymized chat streams."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛑 پایان دادن به چت و مچ یابی جدید", callback_data="end_chat")
        ]
    ])