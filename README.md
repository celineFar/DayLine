<p align="center">
  <img src="Logo.png" alt="Dayline Logo" width="280" />
</p>

<h1 align="center">Dayline</h1>

<p align="center">
  <b>Your personal time-tracking companion on Telegram.</b><br>
  Log activities, track sleep, visualize your day — all from a chat.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-7c5cbf?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/telegram-bot-7c5cbf?style=for-the-badge&logo=telegram&logoColor=white" />
  <img src="https://img.shields.io/badge/storage-google%20sheets-7c5cbf?style=for-the-badge&logo=googlesheets&logoColor=white" />
</p>

---

## What is Dayline?

Dayline is a Telegram bot that helps you understand where your time goes. Instead of filling out spreadsheets or opening yet another app, you simply chat with the bot to log what you're doing — and it turns your day into a beautiful visual timeline.

**Log activities** with a tap. **Track sleep** effortlessly. **See your day** as a color-coded chart. **Stay accountable** with gentle idle reminders.

---

## Features

### Activity Tracking
- Start, end, and switch between activities in real time
- Create your own activity list that grows with you
- Manual time entry for retroactive logging
- Automatic midnight-splitting for sessions that cross days

### Sleep Tracking
- Record sleep start and wake-up times
- "Now" or manual entry for both
- Smart reminder if you forget to log your wake-up (fires after 10 hours)

### Visual Timeline
- Color-coded broken bar chart of your entire day
- Multiple time ranges: Today, Yesterday, This Week, Month, All, or Custom
- Summary table with totals and daily averages per activity
- Refresh without leaving the chat

### Idle Reminders & Snooze
- Periodic nudge every 10 minutes when you're not tracking anything
- Snooze for 10 min, 30 min, 1 hour, or a custom duration
- Automatically paused when you're sleeping or have an active session

---

## Quick Start

### Prerequisites

- Python 3.9+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Google Cloud service account with Sheets API enabled
- A Google Spreadsheet shared with your service account

### Installation

```bash
git clone https://github.com/your-username/dayline.git
cd dayline
pip install -r requirements.txt
```

### Configuration

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/service_account.json
SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/your_spreadsheet_id
```

**Optional settings:**

```env
SLEEP_REMINDER_SECONDS=36000    # Sleep reminder delay (default: 10 hours)
IDLE_REMINDER_SECONDS=600       # Idle reminder interval (default: 10 minutes)
```

### Run

```bash
python -m bot.main
```

---

## Commands

| Command              | Description                              |
|----------------------|------------------------------------------|
| `/start`             | Open the main menu                       |
| `/log_activity`      | Jump to the activity logging flow        |
| `/preview_activity`  | Show a 7-day timeline chart              |
| `/snooze`            | Pause idle reminders for a chosen period |
| `/cancel`            | Cancel any pending input                 |

---

## Project Structure

```
Dayline/
|-- bot/                # Telegram bot layer
|   |-- main.py         # Entry point
|   |-- handlers.py     # Command, callback & text handlers
|   |-- keyboards.py    # Inline keyboard layouts
|   |-- state.py        # User state management & persistence
|
|-- app/                # Business logic
|   |-- sleep_service.py
|   |-- activity_service.py
|   |-- preview_service.py
|
|-- domain/             # Pure domain rules
|   |-- ranges.py       # Date range helpers
|   |-- sleep_rules.py  # Sleep interval inference
|   |-- timeline.py     # Timeline data transformation
|   |-- time_normalize.py
|
|-- infra/              # External I/O
|   |-- sheets_client.py    # Google Sheets auth & connection
|   |-- activity_repo.py    # Read/write activity records
|
|-- viz/
|   |-- plotter.py      # matplotlib chart renderer
|
|-- config/
|   |-- settings.py     # Environment config & constants
|
|-- state/
|   |-- user_state.json # Persisted user state
```

---

## How It Works

```
You (Telegram)  -->  Bot Handlers  -->  App Services  -->  Google Sheets
                                    |
                                    --> Domain Rules  -->  matplotlib  -->  Chart PNG
```

1. You tap a button or send a message
2. Handlers update your state and route to the right service
3. Services validate your input and persist records to Google Sheets
4. For previews, data flows back through pandas transformations into a timeline chart

---

## Tech Stack

| Layer          | Technology                       |
|----------------|----------------------------------|
| Bot framework  | python-telegram-bot 20.x (async) |
| Data storage   | Google Sheets via gspread        |
| Data processing| pandas + numpy                   |
| Visualization  | matplotlib                       |
| Config         | python-dotenv                    |

---

## License

This project is for personal use. All rights reserved.
