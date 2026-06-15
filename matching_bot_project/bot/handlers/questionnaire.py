import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from matching_bot_project.bot.core.loader import bot, redis_client, dp
from matching_bot_project.bot.states.states import QuestionnaireStates, ChatStates
from matching_bot_project.bot.keyboards.inline import get_question_reply_keyboard, get_chat_approval_keyboard
from matching_bot_project.database.queries import crud
from matching_bot_project.database.models.models import Question, UserAnswer, MatchHistory

logger = logging.getLogger(__name__)
router = Router(name="questionnaire_handler")


@router.callback_query(QuestionnaireStates.answering_questions, F.data.startswith("ans_"))
async def register_question_response(call: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Handles an answer callback selection, saving it and evaluating partner synchronization."""
    tg_id = call.from_user.id
    data = await state.get_data()

    match_history_id = data.get("match_history_id")
    current_q_index = data.get("current_question_index", 0)

    # FIX: validate callback data format before unpacking to avoid IndexError on malformed payloads
    parts = call.data.split("_")
    if len(parts) < 3:
        logger.warning("Malformed answer callback from user %s: %s", tg_id, call.data)
        await call.answer("⚠️ خطای داخلی: داده نامعتبر.", show_alert=True)
        return

    option_selected = parts[1].upper()  # A or B
    try:
        question_id = int(parts[2])
    except ValueError:
        logger.warning("Non-integer question_id in callback from user %s: %s", tg_id, call.data)
        await call.answer("⚠️ خطای داخلی: شناسه سوال نامعتبر.", show_alert=True)
        return

    # FIX: validate that FSM state data is intact before proceeding
    if not match_history_id:
        logger.error("Missing match_history_id in FSM state for user %s", tg_id)
        await call.answer("⚠️ خطای داخلی: جلسه مچ یافت نشد. لطفاً دوباره تلاش کنید.", show_alert=True)
        return

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
        logger.warning("Failed to save answer for user %s, question %s: %s", tg_id, question_id, e)
        await db_session.rollback()
        # FIX: do not silently continue after a save failure — the answer wasn't recorded
        await call.answer("⚠️ خطا در ثبت پاسخ. لطفاً دوباره امتحان کنید.", show_alert=True)
        return

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(f"✅ پاسخ شما به سوال {current_q_index + 1} با موفقیت ثبت شد.")

    # Retrieve match record and derive partner ID
    active_match = await db_session.get(MatchHistory, match_history_id)
    if not active_match:
        logger.error("MatchHistory %s not found for user %s", match_history_id, tg_id)
        await call.answer()
        return

    partner_id = active_match.user_two_id if active_match.user_one_id == tg_id else active_match.user_one_id

    answers = await crud.check_question_status(db_session, match_history_id, question_id)

    if len(answers) == 2:
        next_q_index = current_q_index + 1

        # FIX: handle None/missing Redis key gracefully instead of crashing on .split()
        q_ids_raw = await redis_client.get(f"match:questions:{match_history_id}")
        if not q_ids_raw:
            logger.error("Redis key for match questions missing for match %s", match_history_id)
            await call.answer()
            return

        try:
            q_ids = [int(qid) for qid in q_ids_raw.split(",")]
        except ValueError:
            logger.error("Corrupt Redis question list for match %s: %s", match_history_id, q_ids_raw)
            await call.answer()
            return

        # FIX: use len(q_ids) instead of hardcoded 20 so the logic stays correct
        # if the question pool size ever changes
        if next_q_index >= len(q_ids):
            active_match.questionnaire_completed = True
            await db_session.commit()
            await finalize_questionnaire_and_request_approval(db_session, match_history_id, active_match)
        else:
            next_question_id = q_ids[next_q_index]
            next_question = await db_session.get(Question, next_question_id)

            # FIX: guard against a missing question record in DB
            if not next_question:
                logger.error("Question %s not found in DB for match %s", next_question_id, match_history_id)
                await call.answer()
                return

            for uid in [tg_id, partner_id]:
                u_context = dp.fsm.resolve_context(bot=bot, chat_id=uid, user_id=uid)
                await u_context.update_data(current_question_index=next_q_index)
                await u_context.set_state(QuestionnaireStates.answering_questions)

                txt = (
                    f"❓ *سوال {next_q_index + 1} از {len(q_ids)}:*\n\n"
                    f"{next_question.question_text}\n\n"
                    f"🅰️ گزینه اول: {next_question.option_a}\n"
                    f"🅱️ گزینه دوم: {next_question.option_b}"
                )
                # FIX: wrap each send in try/except so one user's failure doesn't block the other
                try:
                    await bot.send_message(
                        chat_id=uid,
                        text=txt,
                        reply_markup=get_question_reply_keyboard(next_question_id),
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error("Failed to send next question to user %s: %s", uid, e)
    else:
        # FIX: set state BEFORE sending the wait message to avoid a brief window where the
        # user could send another answer callback before the state transition completes
        await state.set_state(QuestionnaireStates.waiting_for_partner_answer)
        await call.message.answer("⏳ در انتظار پاسخ پارتنر شما به این سوال جهت عبور به سوال بعدی...")

    await call.answer()


@router.callback_query(QuestionnaireStates.waiting_for_partner_answer)
async def ignore_input_on_wait_state(call: CallbackQuery):
    """Ignores interaction while partner answers."""
    await call.answer("⏳ لطفا شکیبا باشید، همسر مچ به پاسخ هنوز جواب نداده است.", show_alert=True)


async def finalize_questionnaire_and_request_approval(session: AsyncSession, match_id: int, match_row: MatchHistory):
    """Calculates final compatibility score and asks consent to open chat."""
    stmt = select(UserAnswer).where(UserAnswer.match_history_id == match_id)
    res = await session.execute(stmt)
    all_ans = list(res.scalars().all())

    answers_map: dict[int, list[tuple[int, str]]] = {}
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
        # FIX: set state to a defined approval-waiting state so the approval keyboard callbacks
        # are only accepted in the correct FSM state and stale inputs are rejected
        await u_context.set_state(ChatStates.waiting_for_approval)
        # FIX: wrap each send in try/except so one user's failure doesn't block the other
        try:
            await bot.send_message(
                chat_id=uid,
                text=intro_approval_text,
                reply_markup=get_chat_approval_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error("Failed to send approval request to user %s: %s", uid, e)