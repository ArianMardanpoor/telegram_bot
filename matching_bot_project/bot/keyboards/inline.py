from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

# --- CallbackData Factories ---

class GenderCallback(CallbackData, prefix="gen"):
    gender: str

class MatchCallback(CallbackData, prefix="mat"):
    type: str

class AnswerCallback(CallbackData, prefix="ans"):
    q_id: int
    choice: str

class ChatActionCallback(CallbackData, prefix="chat"):
    action: str

# --- Keyboard Generators ---

def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard selecting gender details during onboarding."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🙋‍♂️ آقا (Male)", 
                callback_data=GenderCallback(gender="male").pack()
            ),
            InlineKeyboardButton(
                text="🙋‍♀️ خانم (Female)", 
                callback_data=GenderCallback(gender="female").pack()
            )
        ]
    ])


def get_matching_type_keyboard() -> InlineKeyboardMarkup:
    """Returns matching selection panel (Free vs VIP matching type)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🎲 مچ تصادفی (رایگان)", 
                callback_data=MatchCallback(type="random").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="⭐ مچ پیشرفته VIP (فیلتردار)", 
                callback_data=MatchCallback(type="vip").pack()
            )
        ]
    ])


def get_question_reply_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Inline options corresponding to the active questionnaire bank query."""
    # The AnswerCallback factory natively ensures type safety and handles the
    # string conversion. Using 'q_id' keeps the payload well under 64 bytes.
    if not isinstance(question_id, int) or question_id < 0:
        raise ValueError(f"Invalid question_id for keyboard generation: {question_id!r}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🅰️ گزینه اول", 
                callback_data=AnswerCallback(q_id=question_id, choice="a").pack()
            ),
            InlineKeyboardButton(
                text="🅱️ گزینه دوم", 
                callback_data=AnswerCallback(q_id=question_id, choice="b").pack()
            )
        ]
    ])


def get_chat_approval_keyboard() -> InlineKeyboardMarkup:
    """End-game consent panel enabling anonymous chat rooms."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ موافقم؛ شروع گفتگو ناشناس", 
                callback_data=ChatActionCallback(action="approve").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ خیر؛ خروج از لیست", 
                callback_data=ChatActionCallback(action="decline").pack()
            )
        ]
    ])


def get_active_chat_controls() -> InlineKeyboardMarkup:
    """Active controls during anonymized chat streams."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🛑 پایان دادن به چت و مچ یابی جدید", 
                callback_data=ChatActionCallback(action="end").pack()
            )
        ]
    ])