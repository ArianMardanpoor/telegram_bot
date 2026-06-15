from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """FSM states managing initial registration sequences."""
    waiting_for_gender = State()
    waiting_for_age = State()
    waiting_for_city = State()


class MatchingStates(StatesGroup):
    """FSM states managing match making loops."""
    waiting_in_queue = State()
    matched_active = State()


class QuestionnaireStates(StatesGroup):
    """FSM states managing the 20-question FSM synchronization phase."""
    answering_questions = State()
    waiting_for_partner_answer = State()


class ChatStates(StatesGroup):
    """FSM states managing direct anonymous routing."""
    anonymous_chat_active = State()
