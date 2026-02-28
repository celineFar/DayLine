# bot/keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Preview", callback_data="preview"),
            InlineKeyboardButton("📝 Log Activity", callback_data="log_activity"),
        ]
    ])


def preview_range_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Today", callback_data="preview_today"),
            InlineKeyboardButton("Yesterday", callback_data="preview_yesterday"),
        ],
        [
            InlineKeyboardButton("This Week", callback_data="preview_week"),
            InlineKeyboardButton("1 Month", callback_data="preview_1m"),
        ],
        [
            InlineKeyboardButton("All Recorded", callback_data="preview_all"),
            InlineKeyboardButton("Custom Range", callback_data="preview_custom"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="preview_refresh"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="back_home"),
        ],
    ])


def log_menu_keyboard():
    """Main log activity menu: Sleep or Other Activity."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💤 Log Sleep", callback_data="record"),
            InlineKeyboardButton("🏃 Log Other Activity", callback_data="activity_select"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_home"),
        ],
    ])


def ongoing_activity_keyboard():
    """Shown when there's an ongoing activity."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛑 End Activity", callback_data="end_activity"),
            InlineKeyboardButton("🔄 Switch Activity", callback_data="switch_activity"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_home"),
        ],
    ])


def record_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😴 Record Sleep", callback_data="sleep_start"),
            InlineKeyboardButton("⏰ Record Wake Up", callback_data="sleep_end"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="log_activity"),
        ],
    ])


def activity_select_keyboard(activities):
    """Dynamic keyboard from user's saved activity list."""
    rows = []
    # Two activities per row
    for i in range(0, len(activities), 2):
        row = [InlineKeyboardButton(activities[i], callback_data=f"act:{activities[i]}")]
        if i + 1 < len(activities):
            row.append(InlineKeyboardButton(activities[i+1], callback_data=f"act:{activities[i+1]}"))
        rows.append(row)

    rows.append([InlineKeyboardButton("➕ Add New Activity", callback_data="add_new_activity")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="log_activity")])
    return InlineKeyboardMarkup(rows)


def confirm_new_activity_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_new_activity"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_new_activity"),
        ]
    ])


def activity_time_keyboard():
    """Start time selection for an activity."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🕒 Start Now", callback_data="activity_start_now"),
            InlineKeyboardButton("✏️ Enter Manually", callback_data="activity_start_manual"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="activity_select"),
        ],
    ])


def end_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_end_activity"),
            InlineKeyboardButton("✏️ Edit End Time", callback_data="edit_end_time"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_end_activity"),
        ],
    ])


def switch_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_switch"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_switch"),
        ]
    ])


def sleep_resolution_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕘 Enter wake up time", callback_data="sleep_fix_time")],
        [InlineKeyboardButton("⏱ Enter sleep duration", callback_data="sleep_fix_duration")],
        [InlineKeyboardButton("😴 Use 8-hour sleep", callback_data="sleep_fix_8h")],
        [InlineKeyboardButton("❌ Dismiss", callback_data="dismiss_reminder")],
    ])


def overwrite_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_overwrite"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_overwrite"),
        ]
    ])


def sleep_start_choice_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😴 Now", callback_data="sleep_start_now"),
            InlineKeyboardButton("✏️ Enter manually", callback_data="sleep_start_manual"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="record"),
        ],
    ])


def wake_up_choice_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏰ Now", callback_data="sleep_end_now"),
            InlineKeyboardButton("✏️ Enter manually", callback_data="sleep_end_manual"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="record"),
        ],
    ])


def idle_reminder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Log Activity", callback_data="log_activity")],
        [InlineKeyboardButton("😴 I'm Resting", callback_data="idle_resting")],
        [InlineKeyboardButton("🔕 Snooze 10 min", callback_data="snooze_10m")],
    ])


def snooze_duration_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🕒 30 Minutes", callback_data="snooze_30m"),
            InlineKeyboardButton("🕐 1 Hour", callback_data="snooze_1h"),
        ],
        [
            InlineKeyboardButton("✏️ Custom", callback_data="snooze_custom"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_snooze"),
        ],
    ])


def cancel_input_keyboard():
    """Shown when awaiting text input to allow canceling."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_input")],
    ])
