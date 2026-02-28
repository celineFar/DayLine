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
from telegram import InputMediaPhoto

from bot.state import get_state, save_state_to_disk
from bot.keyboards import (
    start_keyboard,
    preview_range_keyboard,
    record_keyboard,
    sleep_resolution_keyboard,
    overwrite_confirm_keyboard,
    sleep_start_choice_keyboard,
    wake_up_choice_keyboard,
    cancel_input_keyboard,
    log_menu_keyboard,
    ongoing_activity_keyboard,
    activity_select_keyboard,
    confirm_new_activity_keyboard,
    activity_time_keyboard,
    end_confirm_keyboard,
    switch_confirm_keyboard,
    idle_reminder_keyboard,
    snooze_duration_keyboard,
)
from app import sleep_service
from app import activity_service
from config.settings import SLEEP_REMINDER_DELAY, IDLE_REMINDER_INTERVAL, MAX_SNOOZE_HOURS
from app.preview_service import render_timeline_png
from domain.ranges import last_n_days, last_month, today, yesterday, this_week

logger = logging.getLogger(__name__)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def cleanup_sleep_state(state):
    state.sleep_start_dt = None
    if state.sleep_reminder_job_id:
        state.sleep_reminder_job_id = None


def _format_duration(start_dt, end_dt):
    delta = end_dt - start_dt
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{minutes}m"


def _get_user_activities(state):
    """Get the user's saved activity list, initializing if needed."""
    if state.activities is None:
        state.activities = []
    return state.activities


# --------------------------------------------------
# Command handlers
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_state(user_id)
    logger.debug("start command received from user_id=%s", user_id)

    state.clear_input_flags()
    state.preview_message_id = None

    await update.message.reply_text(
        "Welcome! What would you like to do?",
        reply_markup=start_keyboard(),
    )


async def log_activity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut /log_activity command."""
    user_id = update.effective_user.id
    state = get_state(user_id)
    state.clear_input_flags()

    if state.current_activity is not None and state.activity_start_dt is not None:
        elapsed = _format_duration(state.activity_start_dt, datetime.now())
        await update.message.reply_text(
            f"⏱ You are currently doing: **{state.current_activity}**\n"
            f"Started at: {state.activity_start_dt.strftime('%H:%M')}\n"
            f"Duration so far: {elapsed}",
            parse_mode="Markdown",
            reply_markup=ongoing_activity_keyboard(),
        )
    else:
        await update.message.reply_text(
            "What would you like to log?",
            reply_markup=log_menu_keyboard(),
        )


async def preview_activity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut /preview_activity command."""
    state = get_state(update.effective_user.id)
    state.clear_input_flags()
    start_date, end_date = last_n_days(7)
    await send_or_update_preview(
        update=update,
        context=context,
        start_date=start_date,
        end_date=end_date,
    )


async def snooze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /snooze command."""
    await update.message.reply_text(
        "How long would you like to pause reminders?",
        reply_markup=snooze_duration_keyboard(),
    )


# --------------------------------------------------
# Log menu helper
# --------------------------------------------------

async def _show_log_menu(message, state):
    """Show the log activity menu, checking for ongoing activity."""
    if state.current_activity is not None and state.activity_start_dt is not None:
        elapsed = _format_duration(state.activity_start_dt, datetime.now())
        await message.edit_text(
            f"⏱ You are currently doing: **{state.current_activity}**\n"
            f"Started at: {state.activity_start_dt.strftime('%H:%M')}\n"
            f"Duration so far: {elapsed}",
            parse_mode="Markdown",
            reply_markup=ongoing_activity_keyboard(),
        )
    else:
        await message.edit_text(
            "What would you like to log?",
            reply_markup=log_menu_keyboard(),
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

    logger.debug("callback received: user_id=%s data=%s", user_id, data)

    # ========== Preview ==========
    if data in {"preview", "preview_7d"}:
        start_date, end_date = last_n_days(7)
        state.last_preview_start = start_date
        state.last_preview_end = end_date
        await send_or_update_preview(
            update=update, context=context,
            start_date=start_date, end_date=end_date,
        )

    elif data == "preview_today":
        start_date, end_date = today()
        state.last_preview_start = start_date
        state.last_preview_end = end_date
        await send_or_update_preview(
            update=update, context=context,
            start_date=start_date, end_date=end_date,
        )

    elif data == "preview_yesterday":
        start_date, end_date = yesterday()
        state.last_preview_start = start_date
        state.last_preview_end = end_date
        await send_or_update_preview(
            update=update, context=context,
            start_date=start_date, end_date=end_date,
        )

    elif data == "preview_week":
        start_date, end_date = this_week()
        state.last_preview_start = start_date
        state.last_preview_end = end_date
        await send_or_update_preview(
            update=update, context=context,
            start_date=start_date, end_date=end_date,
        )

    elif data == "preview_1m":
        start_date, end_date = last_month()
        state.last_preview_start = start_date
        state.last_preview_end = end_date
        await send_or_update_preview(
            update=update, context=context,
            start_date=start_date, end_date=end_date,
        )

    elif data == "preview_all":
        state.last_preview_start = None
        state.last_preview_end = None
        await send_or_update_preview(
            update=update, context=context,
            start_date=None, end_date=None,
        )

    elif data == "preview_refresh":
        await send_or_update_preview(
            update=update, context=context,
            start_date=state.last_preview_start,
            end_date=state.last_preview_end,
        )

    elif data == "preview_custom":
        state.clear_input_flags()
        state.awaiting_custom_range = True
        state.return_to = "preview"
        await query.message.reply_text(
            "Send a date range like:\n`2025-12-01 to 2025-12-07`",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    # ========== Navigation ==========
    elif data == "log_activity":
        state.clear_input_flags()
        await _show_log_menu(query.message, state)

    elif data == "record":
        state.clear_input_flags()
        await query.message.edit_text(
            "Sleep tracking:",
            reply_markup=record_keyboard(),
        )

    elif data == "back_home":
        state.clear_input_flags()
        if state.preview_message_id == query.message.message_id:
            state.preview_message_id = None
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Welcome! What would you like to do?",
                reply_markup=start_keyboard(),
            )
        else:
            await query.message.edit_text(
                "Welcome! What would you like to do?",
                reply_markup=start_keyboard(),
            )

    # ========== Activity Selection ==========
    elif data == "activity_select":
        state.clear_input_flags()
        activities = _get_user_activities(state)
        await query.message.edit_text(
            "Choose an activity:",
            reply_markup=activity_select_keyboard(activities),
        )

    elif data.startswith("act:"):
        activity_name = data[4:]
        state.selected_activity = activity_name
        await query.message.edit_text(
            f"Activity: **{activity_name}**\n\nWhen did you start?",
            parse_mode="Markdown",
            reply_markup=activity_time_keyboard(),
        )

    elif data == "add_new_activity":
        state.clear_input_flags()
        state.awaiting_new_activity_name = True
        state.return_to = "activity_select"
        await query.message.reply_text(
            "Enter the name of the new activity:",
            reply_markup=cancel_input_keyboard(),
        )

    elif data == "confirm_new_activity":
        name = state.pending_new_activity
        state.pending_new_activity = None
        if name:
            activities = _get_user_activities(state)
            if name not in activities:
                activities.append(name)
                save_state_to_disk()
            state.selected_activity = name
            await query.message.edit_text(
                f"Activity **{name}** added!\n\nWhen did you start?",
                parse_mode="Markdown",
                reply_markup=activity_time_keyboard(),
            )
        else:
            await query.message.edit_text(
                "No activity name found. Try again.",
                reply_markup=activity_select_keyboard(_get_user_activities(state)),
            )

    elif data == "cancel_new_activity":
        state.pending_new_activity = None
        activities = _get_user_activities(state)
        await query.message.edit_text(
            "Choose an activity:",
            reply_markup=activity_select_keyboard(activities),
        )

    # ========== Activity Start Time ==========
    elif data == "activity_start_now":
        if state.selected_activity is None:
            await query.message.edit_text(
                "No activity selected. Please choose one.",
                reply_markup=activity_select_keyboard(_get_user_activities(state)),
            )
            return

        now = datetime.now()
        state.current_activity = state.selected_activity
        state.activity_start_dt = now
        state.selected_activity = None

        stop_idle_reminder(context, state)

        save_state_to_disk()

        await query.message.edit_text(
            f"▶️ **{state.current_activity}** started at {now.strftime('%H:%M')}",
            parse_mode="Markdown",
            reply_markup=start_keyboard(),
        )

    elif data == "activity_start_manual":
        state.clear_input_flags()
        state.awaiting_activity_start_time = True
        state.return_to = "activity_time"
        await query.message.reply_text(
            "Enter start time like:\n`YYYY-MM-DD HH:MM`\n\n"
            "Example: `2025-01-20 14:30`",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    # ========== End Activity ==========
    elif data == "end_activity":
        if state.current_activity is None:
            await query.message.edit_text(
                "⚠️ No activity is currently running.",
                reply_markup=start_keyboard(),
            )
            return

        now = datetime.now()
        duration = _format_duration(state.activity_start_dt, now)
        await query.message.edit_text(
            f"End **{state.current_activity}** now ({now.strftime('%H:%M')})?\n"
            f"Duration: {duration}",
            parse_mode="Markdown",
            reply_markup=end_confirm_keyboard(),
        )

    elif data == "confirm_end_activity":
        if state.current_activity is None or state.activity_start_dt is None:
            await query.message.edit_text(
                "⚠️ No activity is currently running.",
                reply_markup=start_keyboard(),
            )
            return

        end_dt = datetime.now()
        start_dt = state.activity_start_dt
        activity_name = state.current_activity

        try:
            activity_service.record_activity(
                user_id=user_id,
                activity_name=activity_name,
                start_dt=start_dt,
                end_dt=end_dt,
            )
        except ValueError as e:
            await query.message.edit_text(
                f"Error: {e}",
                reply_markup=start_keyboard(),
            )
            return

        duration = _format_duration(start_dt, end_dt)
        state.current_activity = None
        state.activity_start_dt = None
        save_state_to_disk()

        start_idle_reminder(context, user_id, state)

        await query.message.edit_text(
            f"✅ **{activity_name}** ended.\nDuration: {duration}",
            parse_mode="Markdown",
            reply_markup=start_keyboard(),
        )

    elif data == "edit_end_time":
        state.clear_input_flags()
        state.awaiting_activity_start_time = True
        state.pending_action = "edit_end_time"
        state.return_to = "end_activity"
        await query.message.reply_text(
            "Enter end time like:\n`YYYY-MM-DD HH:MM`",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    elif data == "cancel_end_activity":
        await _show_log_menu(query.message, state)

    # ========== Switch Activity ==========
    elif data == "switch_activity":
        if state.current_activity is None:
            await query.message.edit_text(
                "⚠️ No activity is currently running.",
                reply_markup=start_keyboard(),
            )
            return

        await query.message.edit_text(
            f"Switching will end **{state.current_activity}**. Continue?",
            parse_mode="Markdown",
            reply_markup=switch_confirm_keyboard(),
        )

    elif data == "confirm_switch":
        if state.current_activity and state.activity_start_dt:
            end_dt = datetime.now()
            try:
                activity_service.record_activity(
                    user_id=user_id,
                    activity_name=state.current_activity,
                    start_dt=state.activity_start_dt,
                    end_dt=end_dt,
                )
            except ValueError as e:
                await query.message.edit_text(f"Error ending current activity: {e}")
                return

            duration = _format_duration(state.activity_start_dt, end_dt)
            old_activity = state.current_activity
            state.current_activity = None
            state.activity_start_dt = None
            save_state_to_disk()

            activities = _get_user_activities(state)
            await query.message.edit_text(
                f"✅ **{old_activity}** ended ({duration}).\n\nChoose next activity:",
                parse_mode="Markdown",
                reply_markup=activity_select_keyboard(activities),
            )
        else:
            activities = _get_user_activities(state)
            await query.message.edit_text(
                "Choose an activity:",
                reply_markup=activity_select_keyboard(activities),
            )

    elif data == "cancel_switch":
        await _show_log_menu(query.message, state)

    # ========== Sleep start (choice) ==========
    elif data == "sleep_start":
        await query.message.edit_text(
            "How would you like to record sleep start?",
            reply_markup=sleep_start_choice_keyboard(),
        )

    elif data == "sleep_start_now":
        if state.sleep_start_dt is not None:
            state.pending_action = "sleep_start"
            await query.message.edit_text(
                "⚠️ You already have a sleep session started.\n"
                "Do you want to overwrite the existing start time?",
                reply_markup=overwrite_confirm_keyboard(),
            )
            return

        now = datetime.now()
        state.sleep_start_dt = now

        # End any ongoing activity
        if state.current_activity and state.activity_start_dt:
            try:
                activity_service.record_activity(
                    user_id=user_id,
                    activity_name=state.current_activity,
                    start_dt=state.activity_start_dt,
                    end_dt=now,
                )
            except ValueError:
                pass
            state.current_activity = None
            state.activity_start_dt = None

        cancel_sleep_reminder(context, state)
        stop_idle_reminder(context, state)

        job = context.job_queue.run_once(
            callback=sleep_reminder_job,
            when=SLEEP_REMINDER_DELAY,
            data={"user_id": user_id},
            name=f"sleep_reminder_{user_id}",
        )

        state.sleep_reminder_job_id = job.name
        save_state_to_disk()

        await query.message.edit_text(
            f"😴 Sleep start recorded at {now.strftime('%Y-%m-%d %H:%M')}",
            reply_markup=record_keyboard(),
        )

    elif data == "sleep_start_manual":
        state.clear_input_flags()
        state.awaiting_sleep_start_time = True
        state.return_to = "sleep_start"
        await query.message.reply_text(
            "Enter sleep start time like:\n`YYYY-MM-DD HH:MM`\n\n"
            "Example: `2025-01-20 23:30`",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    # ========== Sleep end (choice) ==========
    elif data == "sleep_end":
        if state.sleep_start_dt is None:
            await query.message.reply_text(
                "I don't have a sleep start time yet. Press 😴 Record Sleep first.",
                reply_markup=record_keyboard(),
            )
            return

        await query.message.edit_text(
            "How would you like to record wake up?",
            reply_markup=wake_up_choice_keyboard(),
        )

    elif data == "sleep_end_now":
        state.pending_action = "sleep_end"
        await query.message.edit_text(
            "⚠️ Are you sure you want to record wake up now?",
            reply_markup=overwrite_confirm_keyboard(),
        )

    elif data == "sleep_end_manual":
        state.clear_input_flags()
        state.awaiting_wake_time = True
        state.return_to = "sleep_end"
        sleep_info = ""
        if state.sleep_start_dt:
            sleep_info = f"\n\nSleep started: `{state.sleep_start_dt.strftime('%Y-%m-%d %H:%M')}`"
        await query.message.reply_text(
            f"Send wake up time like:\n`YYYY-MM-DD HH:MM`{sleep_info}",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    # ========== Overwrite confirmation ==========
    elif data == "confirm_overwrite":
        action = state.pending_action
        state.pending_action = None

        if action == "sleep_start":
            cancel_sleep_reminder(context, state)
            stop_idle_reminder(context, state)

            now = datetime.now()
            state.sleep_start_dt = now

            job = context.job_queue.run_once(
                callback=sleep_reminder_job,
                when=SLEEP_REMINDER_DELAY,
                data={"user_id": user_id},
                name=f"sleep_reminder_{user_id}",
            )
            state.sleep_reminder_job_id = job.name
            save_state_to_disk()

            await query.message.edit_text(
                f"😴 Sleep start overwritten.\n"
                f"New start time: {now.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=record_keyboard(),
            )

        elif action == "sleep_end":
            start_dt = state.sleep_start_dt
            if start_dt is None:
                await query.message.edit_text(
                    "No sleep start time found.",
                    reply_markup=record_keyboard(),
                )
                return

            end_dt = datetime.now()
            cancel_sleep_reminder(context, state)

            try:
                sleep_service.record_sleep_end(
                    user_id=user_id,
                    start_dt=start_dt,
                    end_dt=end_dt,
                )
            except ValueError as e:
                await query.message.edit_text(
                    f"Error: {e}",
                    reply_markup=record_keyboard(),
                )
                return

            cleanup_sleep_state(state)
            save_state_to_disk()

            start_idle_reminder(context, user_id, state)

            await query.message.edit_text(
                f"✅ Saved sleep: {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=record_keyboard(),
            )

    elif data == "cancel_overwrite":
        state.pending_action = None
        await query.message.edit_text(
            "❌ Action cancelled.",
            reply_markup=record_keyboard(),
        )

    # ========== Cancel input ==========
    elif data == "cancel_input":
        return_to = state.return_to
        state.clear_input_flags()

        if return_to == "preview":
            await query.message.edit_text("❌ Input cancelled.")
            s, e = last_n_days(7)
            await send_or_update_preview(
                update=update, context=context,
                start_date=s, end_date=e,
            )
        elif return_to == "sleep_start":
            await query.message.edit_text(
                "❌ Input cancelled.\n\nHow would you like to record sleep start?",
                reply_markup=sleep_start_choice_keyboard(),
            )
        elif return_to == "sleep_end":
            await query.message.edit_text(
                "❌ Input cancelled.\n\nHow would you like to record wake up?",
                reply_markup=wake_up_choice_keyboard(),
            )
        elif return_to == "reminder":
            elapsed = ""
            if state.sleep_start_dt:
                delta = datetime.now() - state.sleep_start_dt
                hours = int(delta.total_seconds() // 3600)
                mins = int((delta.total_seconds() % 3600) // 60)
                elapsed = f"\n\nSleep started {hours}h {mins}m ago."
            await query.message.edit_text(
                f"❌ Input cancelled.\n\nHow would you like to record your wake up?{elapsed}",
                reply_markup=sleep_resolution_keyboard(),
            )
        elif return_to == "activity_select":
            await query.message.edit_text(
                "❌ Input cancelled.\n\nChoose an activity:",
                reply_markup=activity_select_keyboard(_get_user_activities(state)),
            )
        elif return_to == "activity_time":
            activity_name = state.selected_activity or "activity"
            await query.message.edit_text(
                f"❌ Input cancelled.\n\nActivity: **{activity_name}**\n\nWhen did you start?",
                parse_mode="Markdown",
                reply_markup=activity_time_keyboard(),
            )
        elif return_to == "end_activity":
            await _show_log_menu(query.message, state)
        elif return_to == "snooze":
            await query.message.edit_text(
                "❌ Input cancelled.",
                reply_markup=start_keyboard(),
            )
        else:
            await query.message.edit_text(
                "❌ Input cancelled.\n\nWhat would you like to do?",
                reply_markup=start_keyboard(),
            )

    # ========== Dismiss reminder ==========
    elif data == "dismiss_reminder":
        sleep_info = ""
        if state.sleep_start_dt:
            sleep_info = f"\n\nSleep started: {state.sleep_start_dt.strftime('%Y-%m-%d %H:%M')}"
        await query.message.edit_text(
            f"Reminder dismissed. Your sleep session is still active.{sleep_info}",
            reply_markup=start_keyboard(),
        )

    # ========== Reminder resolution ==========
    elif data == "sleep_fix_time":
        state.clear_input_flags()
        state.awaiting_wake_time = True
        state.return_to = "reminder"
        sleep_info = ""
        if state.sleep_start_dt:
            sleep_info = f"\n\nSleep started: `{state.sleep_start_dt.strftime('%Y-%m-%d %H:%M')}`"
        await query.message.reply_text(
            f"Send wake up time like:\n`YYYY-MM-DD HH:MM`{sleep_info}",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    elif data == "sleep_fix_duration":
        state.clear_input_flags()
        state.awaiting_sleep_duration = True
        state.return_to = "reminder"
        sleep_info = ""
        if state.sleep_start_dt:
            sleep_info = f"\n\nSleep started: `{state.sleep_start_dt.strftime('%Y-%m-%d %H:%M')}`"
        await query.message.reply_text(
            f"Enter sleep duration in hours (e.g. `7.5`){sleep_info}",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    elif data == "sleep_fix_8h":
        start_dt = state.sleep_start_dt
        if start_dt is None:
            await query.message.reply_text(
                "No sleep start time found.",
                reply_markup=record_keyboard(),
            )
            return

        end_dt = start_dt + timedelta(hours=8)

        cancel_sleep_reminder(context, state)

        try:
            sleep_service.record_sleep_end(
                user_id=user_id,
                start_dt=start_dt,
                end_dt=end_dt,
            )
        except ValueError as e:
            await query.message.reply_text(f"Error: {e}")
            return

        cleanup_sleep_state(state)
        save_state_to_disk()

        start_idle_reminder(context, user_id, state)

        await query.message.reply_text(
            "✅ Recorded 8-hour sleep.",
            reply_markup=record_keyboard(),
        )

    # ========== Idle reminder actions ==========
    elif data == "idle_resting":
        stop_idle_reminder(context, state)
        await query.message.edit_text(
            "😌 Enjoy your rest! Reminders paused.",
            reply_markup=start_keyboard(),
        )

    elif data == "snooze_10m":
        state.snooze_until = datetime.now() + timedelta(minutes=10)
        save_state_to_disk()
        await query.message.edit_text(
            f"🔕 Reminders snoozed for 10 minutes.\n"
            f"Resuming at {state.snooze_until.strftime('%H:%M')}.",
            reply_markup=start_keyboard(),
        )

    # ========== Snooze system ==========
    elif data == "snooze_30m":
        state.snooze_until = datetime.now() + timedelta(minutes=30)
        save_state_to_disk()
        await query.message.edit_text(
            f"🔕 Reminders paused for 30 minutes.\n"
            f"Resuming at {state.snooze_until.strftime('%H:%M')}.",
            reply_markup=start_keyboard(),
        )

    elif data == "snooze_1h":
        state.snooze_until = datetime.now() + timedelta(hours=1)
        save_state_to_disk()
        await query.message.edit_text(
            f"🔕 Reminders paused for 1 hour.\n"
            f"Resuming at {state.snooze_until.strftime('%H:%M')}.",
            reply_markup=start_keyboard(),
        )

    elif data == "snooze_custom":
        state.clear_input_flags()
        state.awaiting_snooze_duration = True
        state.return_to = "snooze"
        await query.message.reply_text(
            "Enter snooze duration in minutes (e.g. `45`)\n"
            "or in format `HH:MM` (e.g. `1:30`)",
            parse_mode="Markdown",
            reply_markup=cancel_input_keyboard(),
        )

    elif data == "cancel_snooze":
        await query.message.edit_text(
            "What would you like to do?",
            reply_markup=start_keyboard(),
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

    # --- Manual sleep start ---
    if state.awaiting_sleep_start_time:
        return_to = state.return_to
        state.clear_input_flags()
        try:
            start_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Please use: `YYYY-MM-DD HH:MM`\n"
                "Example: `2025-01-20 23:30`",
                parse_mode="Markdown",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_sleep_start_time = True
            state.return_to = return_to
            return

        now = datetime.now()
        if start_dt > now + timedelta(hours=1):
            await update.message.reply_text(
                "Sleep start time cannot be in the future. Try again:",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_sleep_start_time = True
            state.return_to = return_to
            return

        state.sleep_start_dt = start_dt
        cancel_sleep_reminder(context, state)
        stop_idle_reminder(context, state)

        job = context.job_queue.run_once(
            callback=sleep_reminder_job,
            when=SLEEP_REMINDER_DELAY,
            data={"user_id": user_id},
            name=f"sleep_reminder_{user_id}",
        )
        state.sleep_reminder_job_id = job.name
        save_state_to_disk()

        await update.message.reply_text(
            f"😴 Sleep start set to {start_dt.strftime('%Y-%m-%d %H:%M')}",
            reply_markup=record_keyboard(),
        )
        return

    # --- Manual wake up ---
    if state.awaiting_wake_time:
        return_to = state.return_to
        state.clear_input_flags()
        try:
            wake_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Please use: `YYYY-MM-DD HH:MM`\n"
                "Example: `2025-01-21 07:30`",
                parse_mode="Markdown",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_wake_time = True
            state.return_to = return_to
            return

        if state.sleep_start_dt is None:
            await update.message.reply_text(
                "No sleep start time found. Please record sleep start first.",
                reply_markup=record_keyboard(),
            )
            return

        if wake_dt <= state.sleep_start_dt:
            await update.message.reply_text(
                f"Wake time must be after sleep start ({state.sleep_start_dt.strftime('%Y-%m-%d %H:%M')}). Try again:",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_wake_time = True
            state.return_to = return_to
            return

        cancel_sleep_reminder(context, state)
        try:
            sleep_service.record_sleep_end(
                user_id=user_id,
                start_dt=state.sleep_start_dt,
                end_dt=wake_dt,
            )
        except ValueError as e:
            await update.message.reply_text(
                f"Error: {e}",
                reply_markup=record_keyboard(),
            )
            return

        cleanup_sleep_state(state)
        save_state_to_disk()

        start_idle_reminder(context, user_id, state)

        await update.message.reply_text(
            "✅ Sleep saved.",
            reply_markup=record_keyboard(),
        )
        return

    # --- Duration input ---
    if state.awaiting_sleep_duration:
        return_to = state.return_to
        state.clear_input_flags()
        try:
            hours = float(text)
        except ValueError:
            await update.message.reply_text(
                "Invalid number. Please enter hours as a number.\n"
                "Example: `7.5`",
                parse_mode="Markdown",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_sleep_duration = True
            state.return_to = return_to
            return

        if hours <= 0 or hours > 24:
            await update.message.reply_text(
                "Sleep duration must be between 0 and 24 hours. Try again:",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_sleep_duration = True
            state.return_to = return_to
            return

        if state.sleep_start_dt is None:
            await update.message.reply_text(
                "No sleep start time found. Please record sleep start first.",
                reply_markup=record_keyboard(),
            )
            return

        end_dt = state.sleep_start_dt + timedelta(hours=hours)

        cancel_sleep_reminder(context, state)
        try:
            sleep_service.record_sleep_end(
                user_id=user_id,
                start_dt=state.sleep_start_dt,
                end_dt=end_dt,
            )
        except ValueError as e:
            await update.message.reply_text(
                f"Error: {e}",
                reply_markup=record_keyboard(),
            )
            return

        cleanup_sleep_state(state)
        save_state_to_disk()

        start_idle_reminder(context, user_id, state)

        await update.message.reply_text(
            "✅ Sleep saved.",
            reply_markup=record_keyboard(),
        )
        return

    # --- Custom preview range ---
    if state.awaiting_custom_range:
        return_to = state.return_to
        state.clear_input_flags()
        try:
            parts = text.split("to")
            if len(parts) != 2:
                raise ValueError("Missing 'to' separator")
            start_str, end_str = [t.strip() for t in parts]
            datetime.strptime(start_str, "%Y-%m-%d")
            datetime.strptime(end_str, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Please use: `YYYY-MM-DD to YYYY-MM-DD`\n"
                "Example: `2025-01-01 to 2025-01-07`",
                parse_mode="Markdown",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_custom_range = True
            state.return_to = return_to
            return

        state.last_preview_start = start_str
        state.last_preview_end = end_str
        await send_or_update_preview(
            update=update, context=context,
            start_date=start_str, end_date=end_str,
        )
        return

    # --- New activity name ---
    if state.awaiting_new_activity_name:
        state.clear_input_flags()
        name = text.strip()
        if not name or len(name) > 50:
            await update.message.reply_text(
                "Activity name must be 1-50 characters. Try again:",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_new_activity_name = True
            state.return_to = "activity_select"
            return

        state.pending_new_activity = name
        await update.message.reply_text(
            f'Add activity: **"{name}"** ?',
            parse_mode="Markdown",
            reply_markup=confirm_new_activity_keyboard(),
        )
        return

    # --- Manual activity start time ---
    if state.awaiting_activity_start_time:
        return_to = state.return_to
        state.clear_input_flags()

        try:
            start_dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Please use: `YYYY-MM-DD HH:MM`",
                parse_mode="Markdown",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_activity_start_time = True
            state.return_to = return_to
            return

        now = datetime.now()
        if start_dt > now + timedelta(minutes=5):
            await update.message.reply_text(
                "Start time cannot be in the future. Try again:",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_activity_start_time = True
            state.return_to = return_to
            return

        # Handle edit_end_time action
        if state.pending_action == "edit_end_time":
            state.pending_action = None
            if state.current_activity is None or state.activity_start_dt is None:
                await update.message.reply_text(
                    "⚠️ No activity is currently running.",
                    reply_markup=start_keyboard(),
                )
                return

            end_dt = start_dt
            act_start = state.activity_start_dt
            activity_name = state.current_activity

            try:
                activity_service.record_activity(
                    user_id=user_id,
                    activity_name=activity_name,
                    start_dt=act_start,
                    end_dt=end_dt,
                )
            except ValueError as e:
                await update.message.reply_text(
                    f"Error: {e}",
                    reply_markup=start_keyboard(),
                )
                return

            duration = _format_duration(act_start, end_dt)
            state.current_activity = None
            state.activity_start_dt = None
            save_state_to_disk()

            start_idle_reminder(context, user_id, state)

            await update.message.reply_text(
                f"✅ **{activity_name}** ended.\nDuration: {duration}",
                parse_mode="Markdown",
                reply_markup=start_keyboard(),
            )
            return

        # Normal: set activity start time
        if state.selected_activity is None:
            await update.message.reply_text(
                "No activity selected.",
                reply_markup=start_keyboard(),
            )
            return

        state.current_activity = state.selected_activity
        state.activity_start_dt = start_dt
        state.selected_activity = None

        stop_idle_reminder(context, state)
        save_state_to_disk()

        await update.message.reply_text(
            f"▶️ **{state.current_activity}** started at {start_dt.strftime('%H:%M')}",
            parse_mode="Markdown",
            reply_markup=start_keyboard(),
        )
        return

    # --- Custom snooze duration ---
    if state.awaiting_snooze_duration:
        state.clear_input_flags()

        minutes = None
        # Try minutes format (plain number)
        try:
            minutes = int(text)
        except ValueError:
            pass

        # Try HH:MM format
        if minutes is None:
            try:
                parts = text.split(":")
                if len(parts) == 2:
                    h, m = int(parts[0]), int(parts[1])
                    minutes = h * 60 + m
            except (ValueError, IndexError):
                pass

        if minutes is None or minutes <= 0:
            await update.message.reply_text(
                "❌ Invalid duration. Please enter a valid time.",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_snooze_duration = True
            state.return_to = "snooze"
            return

        if minutes > MAX_SNOOZE_HOURS * 60:
            await update.message.reply_text(
                f"❌ Maximum snooze is {MAX_SNOOZE_HOURS} hours.",
                reply_markup=cancel_input_keyboard(),
            )
            state.awaiting_snooze_duration = True
            state.return_to = "snooze"
            return

        state.snooze_until = datetime.now() + timedelta(minutes=minutes)
        save_state_to_disk()

        await update.message.reply_text(
            f"🔕 Reminders paused until {state.snooze_until.strftime('%H:%M')}.",
            reply_markup=start_keyboard(),
        )
        return


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any pending input mode."""
    user_id = update.effective_user.id
    state = get_state(user_id)

    has_pending = any([
        state.awaiting_custom_range,
        state.awaiting_wake_time,
        state.awaiting_sleep_duration,
        state.awaiting_sleep_start_time,
        state.awaiting_new_activity_name,
        state.awaiting_activity_start_time,
        state.awaiting_snooze_duration,
    ])

    if not has_pending:
        await update.message.reply_text(
            "Nothing to cancel. What would you like to do?",
            reply_markup=start_keyboard(),
        )
        return

    return_to = state.return_to
    state.clear_input_flags()

    if return_to == "preview":
        await update.message.reply_text("❌ Input cancelled.")
        s, e = last_n_days(7)
        await send_or_update_preview(
            update=update, context=context,
            start_date=s, end_date=e,
        )
    elif return_to == "sleep_start":
        await update.message.reply_text(
            "❌ Input cancelled.\n\nHow would you like to record sleep start?",
            reply_markup=sleep_start_choice_keyboard(),
        )
    elif return_to == "sleep_end":
        await update.message.reply_text(
            "❌ Input cancelled.\n\nHow would you like to record wake up?",
            reply_markup=wake_up_choice_keyboard(),
        )
    elif return_to == "reminder":
        elapsed = ""
        if state.sleep_start_dt:
            delta = datetime.now() - state.sleep_start_dt
            hours = int(delta.total_seconds() // 3600)
            mins = int((delta.total_seconds() % 3600) // 60)
            elapsed = f"\n\nSleep started {hours}h {mins}m ago."
        await update.message.reply_text(
            f"❌ Input cancelled.\n\nHow would you like to record your wake up?{elapsed}",
            reply_markup=sleep_resolution_keyboard(),
        )
    elif return_to == "activity_select":
        await update.message.reply_text(
            "❌ Input cancelled.\n\nChoose an activity:",
            reply_markup=activity_select_keyboard(_get_user_activities(state)),
        )
    elif return_to == "activity_time":
        await update.message.reply_text(
            "❌ Input cancelled.\n\nWhen did you start?",
            reply_markup=activity_time_keyboard(),
        )
    else:
        await update.message.reply_text(
            "❌ Input cancelled.\n\nWhat would you like to do?",
            reply_markup=start_keyboard(),
        )


# --------------------------------------------------
# Registration
# --------------------------------------------------

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("log_activity", log_activity_cmd))
    app.add_handler(CommandHandler("preview_activity", preview_activity_cmd))
    app.add_handler(CommandHandler("snooze", snooze_cmd))
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

    try:
        png_bytes, summary_text = render_timeline_png(start_date, end_date)
    except Exception as e:
        logger.error("Failed to render timeline: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Failed to generate preview. Please check the date range.",
        )
        return

    image_file = InputFile(io.BytesIO(png_bytes), filename="timeline.png")

    caption = summary_text[:1024] if summary_text else None

    if state.preview_message_id:
        try:
            media = InputMediaPhoto(
                media=image_file,
                caption=caption,
                parse_mode="Markdown",
            )
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=state.preview_message_id,
                media=media,
                reply_markup=preview_range_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to edit message, sending new: %s", e)
            state.preview_message_id = None
            image_file = InputFile(io.BytesIO(png_bytes), filename="timeline.png")

    if not state.preview_message_id:
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_file,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=preview_range_keyboard(),
        )
        state.preview_message_id = msg.message_id


# --------------------------------------------------
# Sleep reminder job
# --------------------------------------------------

async def sleep_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    state = get_state(user_id)

    if (
        state.sleep_start_dt is None
        or state.sleep_reminder_job_id != context.job.name
    ):
        return

    elapsed = datetime.now() - state.sleep_start_dt
    total_minutes = int(elapsed.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)

    if hours > 0 and minutes > 0:
        time_str = f"{hours}h {minutes}m"
    elif hours > 0:
        time_str = f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"⏰ You started sleep {time_str} ago.\n\n"
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


# --------------------------------------------------
# Idle reminder system
# --------------------------------------------------

async def idle_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Recurring job that reminds user to log activity when idle."""
    user_id = context.job.data["user_id"]
    state = get_state(user_id)

    # Don't remind if there's an ongoing activity
    if state.current_activity is not None:
        return

    # Don't remind if sleeping
    if state.sleep_start_dt is not None:
        return

    # Don't remind if snoozed
    if state.snooze_until and datetime.now() < state.snooze_until:
        return

    # Clear expired snooze
    if state.snooze_until and datetime.now() >= state.snooze_until:
        state.snooze_until = None
        save_state_to_disk()

    await context.bot.send_message(
        chat_id=user_id,
        text="⏰ What are you doing right now?\n\nDon't waste time — log your activity!",
        reply_markup=idle_reminder_keyboard(),
    )


def start_idle_reminder(context, user_id, state):
    """Start the recurring idle reminder for a user."""
    stop_idle_reminder(context, state)

    # Don't start if user has an ongoing activity or is sleeping
    if state.current_activity is not None or state.sleep_start_dt is not None:
        return

    job = context.job_queue.run_repeating(
        callback=idle_reminder_job,
        interval=IDLE_REMINDER_INTERVAL,
        first=IDLE_REMINDER_INTERVAL,
        data={"user_id": user_id},
        name=f"idle_reminder_{user_id}",
    )
    state.idle_reminder_job_id = job.name


def stop_idle_reminder(context, state):
    """Stop the recurring idle reminder."""
    if state.idle_reminder_job_id:
        for job in context.job_queue.jobs():
            if job.name == state.idle_reminder_job_id:
                job.schedule_removal()
                break
        state.idle_reminder_job_id = None
