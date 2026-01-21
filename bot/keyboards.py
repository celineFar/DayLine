# bot/keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Preview", callback_data="preview"),
            InlineKeyboardButton("🛌 Record", callback_data="record"),
        ]
    ])


def preview_range_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 Week", callback_data="preview_7d"),
            InlineKeyboardButton("1 Month", callback_data="preview_1m"),
        ],
        [
            InlineKeyboardButton("Custom Range", callback_data="preview_custom"),
        ],
    ])


def record_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😴 Record Sleep", callback_data="sleep_start"),
            InlineKeyboardButton("⏰ Record Wake Up", callback_data="sleep_end"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="back_home"),
        ],
    ])

def sleep_resolution_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕘 Enter wake up time", callback_data="sleep_fix_time")],
        [InlineKeyboardButton("⏱ Enter sleep duration", callback_data="sleep_fix_duration")],
        [InlineKeyboardButton("😴 Use 8-hour sleep", callback_data="sleep_fix_8h")],
    ])


def overwrite_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_overwrite"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_overwrite"),
        ]
    ])