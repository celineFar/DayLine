# bot/handlers.py

import logging
import io

from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.state import get_state
from datetime import datetime, timedelta

from bot.keyboards import (
    start_keyboard, 
    preview_range_keyboard, 
    record_keyboard, 
    sleep_resolution_keyboard,
    overwrite_confirm_keyboard
)
from app import sleep_service

from config.settings import SLEEP_REMINDER_DELAY


from app.preview_service import render_timeline_png
from domain.ranges import last_n_days, last_month

# from datetime import timedelta
# import os

# SLEEP_REMINDER_DELAY = timedelta(
#     seconds=int(os.getenv("SLEEP_REMINDER_SECONDS", 10 * 60 * 60))
# )

logger = logging.getLogger(__name__)


def cleanup_sleep_state(state):
    state.sleep_start_dt = None

    if state.sleep_reminder_job_id:
        # Job already ran, but good hygiene
        state.sleep_reminder_job_id = None



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣")
    print("JobQueue:", context.job_queue)
    user_id = update.effective_user.id
    logger.debug("start command received from user_id=%s", user_id)

    await update.message.reply_text(
        "Welcome! What would you like to do?",
        reply_markup=start_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    logger.debug(
        "callback received: user_id=%s data=%s message_id=%s",
        user_id,
        data,
        query.message.message_id if query.message else None,
    )

    state = get_state(user_id)

    if data == "preview":
        logger.debug("handling preview (default 7d) for user_id=%s", user_id)
        start, end = last_n_days(7)
        await send_or_update_preview(
            update=update,
            context=context,
            start_date=start,
            end_date=end,
        )

    elif data == "preview_7d":
        logger.debug("handling preview_7d for user_id=%s", user_id)
        start, end = last_n_days(7)
        await send_or_update_preview(
            update=update,
            context=context,
            start_date=start,
            end_date=end,
        )

    elif data == "preview_1m":
        logger.debug("handling preview_1m for user_id=%s", user_id)
        start, end = last_month()
        await send_or_update_preview(
            update=update,
            context=context,
            start_date=start,
            end_date=end,
        )

    elif data == "preview_custom":
        logger.debug("entering custom range mode for user_id=%s", user_id)
        state.awaiting_custom_range = True
        await query.message.reply_text(
            "Send a date range like:\n`2025-12-01 to 2025-12-07`",
            parse_mode="Markdown",
        )
    elif data == "record":
        await query.message.reply_text(
            "Sleep tracking:",
            reply_markup=record_keyboard(),
        )

    elif data == "back_home":
        await query.message.reply_text(
            "Welcome! What would you like to do?",
            reply_markup=start_keyboard(),
        )
    # elif data == "sleep_start":
    #     now = datetime.now()
    #     state.sleep_start_dt = now

    #     job = context.job_queue.run_once(
    #         callback=sleep_reminder_job,
    #         # when=10 * 60 * 60,  # 10 hours
    #         when=SLEEP_REMINDER_DELAY,
    #         data={"user_id": user_id},
    #         name=f"sleep_reminder_{user_id}",
    #     )

    #     state.sleep_reminder_job_id = job.name

    #     await query.message.reply_text(
    #         f"😴 Sleep start recorded at {now.strftime('%Y-%m-%d %H:%M')}.\n"
    #         f"Press ⏰ Record Wake Up when you wake up.",
    #         reply_markup=record_keyboard(),
    #     )

    elif data == "sleep_start":
        if state.sleep_start_dt is not None:
            state.pending_action = "sleep_start"
            await query.message.reply_text(
                "⚠️ You already have a sleep session started.\n"
                "Do you want to overwrite the existing start time?",
                reply_markup=overwrite_confirm_keyboard(),
            )
            return

        now = datetime.now()
        state.sleep_start_dt = now

        job = context.job_queue.run_once(
            callback=sleep_reminder_job,
            when=SLEEP_REMINDER_DELAY,
            data={"user_id": user_id},
            name=f"sleep_reminder_{user_id}",
        )

        state.sleep_reminder_job_id = job.name

        await query.message.reply_text(
            f"😴 Sleep start recorded at {now.strftime('%Y-%m-%d %H:%M')}.\n"
            f"Press ⏰ Record Wake Up when you wake up.",
            reply_markup=record_keyboard(),
        )


    # elif data == "sleep_end":
    #     if state.sleep_start_dt is None:
    #         await query.message.reply_text(
    #             "I don’t have a sleep start time yet. Press 😴 Record Sleep first.",
    #             reply_markup=record_keyboard(),
    #         )
    #         return
        
    #     start_dt = state.sleep_start_dt
    #     end_dt = datetime.now()

    #     try:
    #         sleep_service.record_sleep_end(
    #             user_id=user_id,
    #             start_dt=start_dt,
    #             end_dt=end_dt,
    #         )
    #     except Exception as e:
    #         await query.message.reply_text(
    #             f"Failed to save sleep: {e}",
    #             reply_markup=record_keyboard(),
    #         )
    #         return

    #     state.sleep_start_dt = None

    #     await query.message.reply_text(
    #         f"✅ Saved sleep: {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%Y-%m-%d %H:%M')}",
    #         reply_markup=record_keyboard(),
    #     )


    elif data == "sleep_end":
        if state.sleep_start_dt is None:
            await query.message.reply_text(
                "I don’t have a sleep start time yet. Press 😴 Record Sleep first.",
                reply_markup=record_keyboard(),
            )
            return

        state.pending_action = "sleep_end"
        await query.message.reply_text(
            "⚠️ Are you sure you want to record wake up now?",
            reply_markup=overwrite_confirm_keyboard(),
        )

    elif data == "confirm_overwrite":
        action = state.pending_action
        state.pending_action = None

        if action == "sleep_start":
            now = datetime.now()
            state.sleep_start_dt = now

            job = context.job_queue.run_once(
                callback=sleep_reminder_job,
                when=SLEEP_REMINDER_DELAY,
                data={"user_id": user_id},
                name=f"sleep_reminder_{user_id}",
            )
            state.sleep_reminder_job_id = job.name

            await query.message.reply_text(
                f"😴 Sleep start overwritten.\n"
                f"New start time: {now.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=record_keyboard(),
            )

        elif action == "sleep_end":
            start_dt = state.sleep_start_dt
            end_dt = datetime.now()

            sleep_service.record_sleep_end(
                user_id=user_id,
                start_dt=start_dt,
                end_dt=end_dt,
            )

            cleanup_sleep_state(state)

            await query.message.reply_text(
                f"✅ Saved sleep: {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=record_keyboard(),
            )

    elif data == "cancel_overwrite":
        state.pending_action = None
        await query.message.reply_text(
            "❌ Action cancelled.",
            reply_markup=record_keyboard(),
        )


    elif data == "sleep_fix_time":
        state.awaiting_wake_time = True
        await query.message.reply_text(
            "Send wake up time like:\n`2026-01-21 07:30`",
            parse_mode="Markdown",
        )


    elif data == "sleep_fix_duration":
        state.awaiting_sleep_duration = True
        await query.message.reply_text(
            "Enter sleep duration in hours (e.g. `7.5`)",
            parse_mode="Markdown",
        )


    elif data == "sleep_fix_8h":
        start_dt = state.sleep_start_dt
        end_dt = start_dt + timedelta(hours=8)

        sleep_service.record_sleep_end(
            user_id=user_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        cleanup_sleep_state(state)

        await query.message.reply_text(
            "✅ Recorded 8-hour sleep.",
            reply_markup=record_keyboard(),
        )



    else:
        logger.warning(
            "unknown callback data: user_id=%s data=%s",
            user_id,
            data,
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    logger.debug(
        "text message received: user_id=%s text=%r",
        user_id,
        text,
    )

    state = get_state(user_id)

    # -----------------------
    # Wake-up time input
    # -----------------------
    if state.awaiting_wake_time:
        state.awaiting_wake_time = False

        try:
            wake_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Use:\n`YYYY-MM-DD HH:MM`",
                parse_mode="Markdown",
            )
            return

        if state.sleep_start_dt is None:
            await update.message.reply_text("❌ No active sleep session.")
            return

        sleep_service.record_sleep_end(
            user_id=user_id,
            start_dt=state.sleep_start_dt,
            end_dt=wake_dt,
        )

        cleanup_sleep_state(state)

        await update.message.reply_text("✅ Sleep saved.")
        return

    # -----------------------
    # Sleep duration input
    # -----------------------
    if state.awaiting_sleep_duration:
        state.awaiting_sleep_duration = False

        try:
            hours = float(text)
        except ValueError:
            await update.message.reply_text(
                "Invalid duration. Enter a number like `7.5`.",
                parse_mode="Markdown",
            )
            return

        if state.sleep_start_dt is None:
            await update.message.reply_text("❌ No active sleep session.")
            return

        end_dt = state.sleep_start_dt + timedelta(hours=hours)

        sleep_service.record_sleep_end(
            user_id=user_id,
            start_dt=state.sleep_start_dt,
            end_dt=end_dt,
        )

        cleanup_sleep_state(state)

        await update.message.reply_text("✅ Sleep saved.")
        return

    # -----------------------
    # Custom preview range
    # -----------------------
    if not state.awaiting_custom_range:
        logger.debug(
            "ignoring text (no input mode): user_id=%s",
            user_id,
        )
        return

    state.awaiting_custom_range = False

    try:
        start, end = [t.strip() for t in text.split("to")]
    except ValueError:
        await update.message.reply_text(
            "Invalid format. Use:\n`YYYY-MM-DD to YYYY-MM-DD`",
            parse_mode="Markdown",
        )
        return

    logger.debug(
        "parsed custom range: user_id=%s start=%s end=%s",
        user_id,
        start,
        end,
    )

    await send_or_update_preview(
        update=update,
        context=context,
        start_date=start,
        end_date=end,
    )


# async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_id = update.message.from_user.id
#     text = update.message.text

#     logger.debug(
#         "text message received: user_id=%s text=%r",
#         user_id,
#         text,
#     )

#     state = get_state(user_id)
    
#     if state.awaiting_wake_time:
#         state.awaiting_wake_time = False

#         wake_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
#         start_dt = state.sleep_start_dt

#         sleep_service.record_sleep_end(
#             user_id=user_id,
#             start_dt=start_dt,
#             end_dt=wake_dt,
#         )

#         cleanup_sleep_state(state)

#         await update.message.reply_text("✅ Sleep saved.")


#     if state.awaiting_sleep_duration:
#         # TODO: text validation
#         hours = float(text)
#         end_dt = state.sleep_start_dt + timedelta(hours=hours)

#         sleep_service.record_sleep_end(...)
#         cleanup_sleep_state(state)

#     if not state.awaiting_custom_range:
#         logger.debug(
#             "ignoring text (not awaiting custom range): user_id=%s",
#             user_id,
#         )
#         return

#     state.awaiting_custom_range = False

#     try:
#         start, end = [t.strip() for t in text.split("to")]
#         logger.debug(
#             "parsed custom range: user_id=%s start=%s end=%s",
#             user_id,
#             start,
#             end,
#         )
#     except ValueError:
#         logger.warning(
#             "invalid custom range format: user_id=%s text=%r",
#             user_id,
#             text,
#         )
#         await update.message.reply_text(
#             "Invalid format. Use:\n`YYYY-MM-DD to YYYY-MM-DD`",
#             parse_mode="Markdown",
#         )
#         return

#     await send_or_update_preview(
#         update=update,
#         context=context,
#         start_date=start,
#         end_date=end,
#     )


def register_handlers(app):
    logger.debug("registering bot handlers")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


async def send_or_update_preview(
    *,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    start_date: str,
    end_date: str,
):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    logger.debug(
        "send_or_update_preview called: user_id=%s chat_id=%s start=%s end=%s",
        user_id,
        chat_id,
        start_date,
        end_date,
    )

    state = get_state(user_id)

    logger.debug(
        "current preview_message_id=%s for user_id=%s",
        state.preview_message_id,
        user_id,
    )

    png_bytes = render_timeline_png(start_date, end_date)
    logger.debug(
        "rendered timeline PNG: %d bytes for user_id=%s",
        len(png_bytes),
        user_id,
    )

    image = InputFile(io.BytesIO(png_bytes), filename="timeline.png")

    if state.preview_message_id:
        logger.debug(
            "editing existing preview message: message_id=%s user_id=%s",
            state.preview_message_id,
            user_id,
        )
        await context.bot.edit_message_media(
            chat_id=chat_id,
            message_id=state.preview_message_id,
            media=image,
            reply_markup=preview_range_keyboard(),
        )
    else:
        logger.debug(
            "sending new preview message for user_id=%s",
            user_id,
        )
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=image,
            reply_markup=preview_range_keyboard(),
        )
        state.preview_message_id = msg.message_id
        logger.debug(
            "stored new preview_message_id=%s for user_id=%s",
            msg.message_id,
            user_id,
        )


async def sleep_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]

    state = get_state(user_id)

    # User already woke up → do nothing
    if state.sleep_start_dt is None:
        return

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "⏰ You started sleep 10 hours ago.\n\n"
            "How would you like to record your wake up?"
        ),
        reply_markup=sleep_resolution_keyboard(),
    )


