# bot/main.py
from telegram.ext import Application

from config.settings import TELEGRAM_BOT_TOKEN
from bot.handlers import register_handlers
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logging.getLogger("bot").setLevel(logging.DEBUG)
logging.getLogger("app").setLevel(logging.DEBUG)


# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
# )
# # Silence HTTP internals
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.WARNING)


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(app)
    app.run_polling()


if __name__ == "__main__":
    main()
