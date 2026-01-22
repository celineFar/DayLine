# bot/handlers.py

import logging
import io
from datetime import datetime, timedelta

from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.state import get_state
from bot.keyboards import (
    start_keyboard,
    preview_range_keyboard,
    record_keyboard,
    sleep_resolution_keyboard,
    overwrite_confirm_keyboard,
    sleep_start_choice_keyboard,
    wake_up_choice_keyboard,
)
from app import sleep_service
from config.settings import SLEEP_REMINDER_DELAY
from app.preview_service import render_timeline_png
from domain.ranges import last_n_days, last_month

logger = logging.getLogger(__name__)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def cleanup_sleep_state(state):
    state.sleep_start_dt = None
    if state.sleep_reminder_job_id:
        state.sleep_reminder_job_id = None


# --------------------------------------------------
# Command handlers
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.debug("start command received from user_id=%s", user_id)

    await update.message.reply_text(
        "Welcome! What would you like to do?",
        reply_markup=start_keyboard(),
    )


# --------------------------------------------------
# Callback handler
# --------------------------------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    state = get_state(user_id)

    logger.debug(
        "callback received: user_id=%s data=%s",
        user_id,
        data,
    )

    # ---------- Preview ----------
    if data in {"preview", "preview_7d"}:
        start, end = last_n_days(7)
        await send_or_update_preview(
            update=update,
            context=context,
            start_date=start,
            end_date=end,
        )

    elif data == "preview_1m":
        start, end = last_month()
        await send_or_update_preview(
            update=update,
            context=context,
            start_date=start,
            end_date=end,
        )

    elif data == "preview_custom":
        state.awaiting_custom_range = True
        await query.message.reply_text(
            "Send a date range like:\n`2025-12-01 to 2025-12-07`",
            parse_mode="Markdown",
        )

    # ---------- Navigation ----------
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

    # ---------- Sleep start (choice) ----------
    elif data == "sleep_start":
        await query.message.reply_text(
            "How would you like to record sleep start?",
            reply_markup=sleep_start_choice_keyboard(),
        )

    elif data == "sleep_start_now":
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

        cancel_sleep_reminder(context, state)

        job = context.job_queue.run_once(
            callback=sleep_reminder_job,
            when=SLEEP_REMINDER_DELAY,
            data={"user_id": user_id},
            name=f"sleep_reminder_{user_id}",
        )

        state.sleep_reminder_job_id = job.name

        await query.message.reply_text(
            f"😴 Sleep start recorded at {now.strftime('%Y-%m-%d %H:%M')}",
            reply_markup=record_keyboard(),
        )

    elif data == "sleep_start_manual":
        state.awaiting_sleep_start_time = True
        await query.message.reply_text(
            "Enter sleep start time like:\n`YYYY-MM-DD HH:MM`",
            parse_mode="Markdown",
        )

    # ---------- Sleep end (choice) ----------
    elif data == "sleep_end":
        if state.sleep_start_dt is None:
            await query.message.reply_text(
                "I don’t have a sleep start time yet. Press 😴 Record Sleep first.",
                reply_markup=record_keyboard(),
            )
            return

        await query.message.reply_text(
            "How would you like to record wake up?",
            reply_markup=wake_up_choice_keyboard(),
        )

    elif data == "sleep_end_now":
        state.pending_action = "sleep_end"
        await query.message.reply_text(
            "⚠️ Are you sure you want to record wake up now?",
            reply_markup=overwrite_confirm_keyboard(),
        )

    elif data == "sleep_end_manual":
        state.awaiting_wake_time = True
        await query.message.reply_text(
            "Send wake up time like:\n`YYYY-MM-DD HH:MM`",
            parse_mode="Markdown",
        )

    # ---------- Overwrite confirmation ----------
    elif data == "confirm_overwrite":
        action = state.pending_action
        state.pending_action = None

        if action == "sleep_start":
            cancel_sleep_reminder(context, state)

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
            cancel_sleep_reminder(context, state)
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

    # ---------- Reminder resolution ----------
    elif data == "sleep_fix_time":
        state.awaiting_wake_time = True
        await query.message.reply_text(
            "Send wake up time like:\n`YYYY-MM-DD HH:MM`",
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

        cancel_sleep_reminder(context, state)
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
        logger.warning("unknown callback data: %s", data)


# --------------------------------------------------
# Text handler
# --------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    state = get_state(user_id)

    # Manual sleep start
    if getattr(state, "awaiting_sleep_start_time", False):
        state.awaiting_sleep_start_time = False
        start_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        state.sleep_start_dt = start_dt
        cancel_sleep_reminder(context, state)

        job = context.job_queue.run_once(
            callback=sleep_reminder_job,
            when=SLEEP_REMINDER_DELAY,
            data={"user_id": user_id},
            name=f"sleep_reminder_{user_id}",
        )
        state.sleep_reminder_job_id = job.name

        await update.message.reply_text(
            f"😴 Sleep start set to {start_dt.strftime('%Y-%m-%d %H:%M')}",
            reply_markup=record_keyboard(),
        )
        return

    # Manual wake up
    if state.awaiting_wake_time:
        state.awaiting_wake_time = False
        wake_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")

        cancel_sleep_reminder(context, state)
        sleep_service.record_sleep_end(
            user_id=user_id,
            start_dt=state.sleep_start_dt,
            end_dt=wake_dt,
        )

        cleanup_sleep_state(state)
        await update.message.reply_text("✅ Sleep saved.")
        return

    # Duration input
    if state.awaiting_sleep_duration:
        state.awaiting_sleep_duration = False
        hours = float(text)
        end_dt = state.sleep_start_dt + timedelta(hours=hours)

        cancel_sleep_reminder(context, state)
        sleep_service.record_sleep_end(
            user_id=user_id,
            start_dt=state.sleep_start_dt,
            end_dt=end_dt,
        )

        cleanup_sleep_state(state)
        await update.message.reply_text("✅ Sleep saved.")
        return

    # Custom preview
    if state.awaiting_custom_range:
        state.awaiting_custom_range = False
        start, end = [t.strip() for t in text.split("to")]

        await send_or_update_preview(
            update=update,
            context=context,
            start_date=start,
            end_date=end,
        )


# --------------------------------------------------
# Registration
# --------------------------------------------------

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


# --------------------------------------------------
# Preview
# --------------------------------------------------

async def send_or_update_preview(
    *,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    start_date: str,
    end_date: str,
):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    state = get_state(user_id)

    png_bytes = render_timeline_png(start_date, end_date)
    image = InputFile(io.BytesIO(png_bytes), filename="timeline.png")

    if state.preview_message_id:
        await context.bot.edit_message_media(
            chat_id=chat_id,
            message_id=state.preview_message_id,
            media=image,
            reply_markup=preview_range_keyboard(),
        )
    else:
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=image,
            reply_markup=preview_range_keyboard(),
        )
        state.preview_message_id = msg.message_id


# --------------------------------------------------
# Reminder job
# --------------------------------------------------

async def sleep_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    state = get_state(user_id)

    if (
        state.sleep_start_dt is None
        or state.sleep_reminder_job_id != context.job.name
    ):
        return
    
    #   TODO: make the time lapsed dynamic
    hours = int((datetime.now() - state.sleep_start_dt).total_seconds() // 3600)
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"⏰ You started sleep {hours} hours ago.\n\n"
            "How would you like to record your wake up?"
        ),
        reply_markup=sleep_resolution_keyboard(),
    )


def cancel_sleep_reminder(context, state):
    if state.sleep_reminder_job_id:
        for job in context.job_queue.jobs():
            if job.name == state.sleep_reminder_job_id:
                job.schedule_removal()
                break
        state.sleep_reminder_job_id = None
