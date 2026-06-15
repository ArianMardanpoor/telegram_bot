import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.core.loader import bot, redis_client, dp
from bot.states.states import QuestionnaireStates, ChatStates
from bot.keyboards.inline import get_question_reply_keyboard, get_chat_approval_keyboard
from database.queries import crud
from database.models.models import Question, UserAnswer, MatchHistory

logger = logging.getLogger(__name__)
router = Router(name="questionnaire_handler")


@router.callback_query(QuestionnaireStates.answering_questions, F.data.startswith("ans_"))
async def register_question_response(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Handles an answer callback selection, saving it and evaluating partner synchronization."""
    tg_id = call.from_user.id
    data = await state.get_data()
    
    match_history_id = data.get("match_history_id")
    current_q_index = data.get("current_question_index", 0)
    
    # Parse callback values
    parts = call.data.split("_")
    option_selected = parts[1].upper() # A or B
    question_id = int(parts[2])

    # Save to SQL UserAnswer repository
    try:
        await crud.save_user_answer(
            session=db_session,
            user_id=tg_id,
            question_id=question_id,
            match_history_id=match_history_id,
            selected_option=option_selected
        )
        await db_session.commit()
    except Exception as e:
        logger.warning(f"Failed to double register answer for safety (already saved or index mismatch): {str(e)}")
        await db_session.rollback()

    # Inform the active sender that their vote is recorded
    await call.message.edit_reply_markup(reply_markup=None) # Delete buttons to avoid double clicks
    await call.message.answer(f"✅ پاسخ شما به سوال {current_q_index + 1} با موفقیت ثبت شد.")

    # Retrieve partner ID
    active_match = await db_session.get(MatchHistory, match_history_id)
    partner_id = active_match.user_two_id if active_match.user_one_id == tg_id else active_match.user_one_id

    # Check database to see if both parties have completed response for this specific question
    answers = await crud.check_question_status(db_session, match_history_id, question_id)
    
    if len(answers) == 2:
        # Both parties answered question ID! We can advance to next step or evaluate end sequence
        next_q_index = current_q_index + 1
        
        # Pull saved list of full 20 questions
        q_ids_serialized = await redis_client.get(f"match:questions:{match_history_id}")
        q_ids = [int(qid) for qid in q_ids_serialized.split(",")]

        if next_q_index >= 20:
            # All 20 game queries accomplished successfully! Proceed to approval stage
            active_match.questionnaire_completed = True
            await db_session.commit()
            await finalize_questionnaire_and_request_approval(db_session, match_history_id, active_match)
        else:
            # Advance index
            next_question_id = q_ids[next_q_index]
            next_question = await db_session.get(Question, next_question_id)
            
            # Send question to both parties concurrently
            for uid in [tg_id, partner_id]:
                u_context = dp.fsm.resolve_context(bot=bot, chat_id=uid, user_id=uid)
                await u_context.update_data(current_question_index=next_q_index)
                await u_context.set_state(QuestionnaireStates.answering_questions)
                
                txt = (
                    f"❓ *سوال {next_q_index + 1} از ۲۰:*\n\n"
                    f"{next_question.question_text}\n\n"
                    f"🅰️ گزینه اول: {next_question.option_a}\n"
                    f"🅱️ گزینه دوم: {next_question.option_b}"
                )
                await bot.send_message(
                    chat_id=uid,
                    text=txt,
                    reply_markup=get_question_reply_keyboard(next_question_id),
                    parse_mode="Markdown"
                )
    else:
        # User N answered, but partner has not finished Question N yet! Enforce wait state
        await state.set_state(QuestionnaireStates.waiting_for_partner_answer)
        await call.message.answer("⏳ در انتظار پاسخ پارتنر شما به این سوال جهت عبور به سوال بعدی...")
    
    await call.answer()


@router.callback_query(QuestionnaireStates.waiting_for_partner_answer)
async def ignore_input_on_wait_state(call: CallbackQuery):
    """Ignores interaction while partner answers."""
    await call.answer("⏳ لطفا شکیبا باشید، همسر مچ به پاسخ هنوز جواب نداده است.", show_alert=True)


async def finalize_questionnaire_and_request_approval(session: AsyncSession, match_id: int, match_row: MatchHistory):
    """Calculates final compatibility score and asks consent to open chat."""
    # Compute compatibility score based on identical answers
    stmt = select(UserAnswer).where(UserAnswer.match_history_id == match_id)
    res = await session.execute(stmt)
    all_ans = list(res.scalars().all())
    
    # Map questions to responses
    answers_map = {}
    for ans in all_ans:
        if ans.question_id not in answers_map:
            answers_map[ans.question_id] = []
        answers_map[ans.question_id].append((ans.user_id, ans.selected_option))
        
    identical_cnt = 0
    total_compared = 0
    for q_id, pairs in answers_map.items():
        if len(pairs) == 2:
            total_compared += 1
            if pairs[0][1] == pairs[1][1]:
                identical_cnt += 1
                
    comp_pct = int((identical_cnt / total_compared) * 100) if total_compared > 0 else 50

    intro_approval_text = (
        "🏁 *همکاری و آزمایش تفاهم به پایان رسید!*\n\n"
        f"📊 میزان تفاهم و اشتراک فکری شما و پارتنر بر اساس پاسخ‌ها: *{comp_pct}%*\n\n"
        "در صورتی که مایل به شروع گفتگوی ناشناس عاطفی با این شخص هستید، "
        'موافقت خود را با زدن روی دکمه "موافقم" اعلام کنید 👇\n'
        "(مکالمه تنها در صورت تایید دو طرفه باز خواهد شد)"
    )

    for uid in [match_row.user_one_id, match_row.user_two_id]:
        u_context = dp.fsm.resolve_context(bot=bot, chat_id=uid, user_id=uid)
        await u_context.update_data(compatibility_pct=comp_pct)
        await bot.send_message(
            chat_id=uid,
            text=intro_approval_text,
            reply_markup=get_chat_approval_keyboard(),
            parse_mode="Markdown"
        )
