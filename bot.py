import os
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

# ==========================
# CONFIG
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

IST = timezone("Asia/Kolkata")

# ==========================
# LOGGING
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("PivotBot")

# ==========================
# FLASK
# ==========================

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ NIFTY Woodie Pivot Bot Running"

# ==========================
# SCHEDULER
# ==========================

scheduler = BackgroundScheduler(timezone=IST)

def test_job():
    logger.info("Scheduler is working successfully.")

scheduler.add_job(
    test_job,
    trigger="interval",
    minutes=1,
)

scheduler.start()

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    logger.info("Starting Pivot Bot...")
    # ==========================================================
# ParthTraderAlerts Telegram Pivot Bot
# bot.py
# Telegram Bot Module
# ==========================================================

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

from config import BOT_TOKEN, CHAT_ID, FOOTER
from data import get_all_market_data


# ==========================================================
# Logging
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ==========================================================
# Format Pivot Message
# ==========================================================

def create_pivot_message():

    market_data = get_all_market_data()

    if not market_data:

        return """
⚠️ ParthTraderAlerts

Market data unavailable.

Please try again later.
"""


    today = datetime.now().strftime("%d-%m-%Y")


    message = f"""
📊 <b>ParthTraderAlerts</b>

🗓 Date : {today}
⏰ Time : 09:15 AM IST

━━━━━━━━━━━━━━
"""


    for name, data in market_data.items():


        pivot = data["pivot"]

        cpr = data["cpr"]


        bias_icon = "🟢" if data["bias"] == "Bullish" else "🔴"


        message += f"""

<b>📈 {name}</b>

Previous Close : {data['close']}

<b>Pivot Levels</b>

🟡 Pivot : {pivot['Pivot']}

🟢 R1 : {pivot['R1']}
🟢 R2 : {pivot['R2']}
🟢 R3 : {pivot['R3']}

🔴 S1 : {pivot['S1']}
🔴 S2 : {pivot['S2']}
🔴 S3 : {pivot['S3']}


<b>CPR</b>

TC : {cpr['TC']}
BC : {cpr['BC']}


{bias_icon} Bias : {data['bias']}

━━━━━━━━━━━━━━
"""


    message += f"""

🚀 Trade With Discipline

{FOOTER}
"""


    return message



# ==========================================================
# Send Telegram Message
# ==========================================================

async def send_pivot_message(context):

    try:

        message = create_pivot_message()


        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="HTML"
        )


        logging.info("Pivot message sent successfully")


    except Exception as e:

        logging.error(
            f"Telegram Send Error : {e}"
        )



# ==========================================================
# Manual /pivot Command
# ==========================================================

async def pivot_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    message = create_pivot_message()


    await update.message.reply_text(
        message,
        parse_mode="HTML"
    )
    # ==========================================================
# Telegram Commands
# ==========================================================


async def start_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    text = """
🤖 <b>ParthTraderAlerts Pivot Bot</b>

✅ Bot is Active

Available Commands:

/pivot
➡️ Get Today's Pivot Levels

/help
➡️ Show Bot Commands

━━━━━━━━━━━━━━

Daily Automatic Pivot Update:
⏰ 09:15 AM IST

📊 NIFTY 50
🏦 BANKNIFTY
📈 SENSEX

🚀 Trade Smart
"""

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )



async def help_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    text = """
<b>📌 ParthTraderAlerts Commands</b>


/start
➡️ Start Bot


/pivot
➡️ Current Pivot Levels


/help
➡️ Help Menu


━━━━━━━━━━━━━━

Daily Auto Update:
⏰ 09:15 AM IST

Powered by:
ParthTraderAlerts
"""

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )



# ==========================================================
# Bot Setup
# ==========================================================


def main():

    print("Starting ParthTraderAlerts Bot...")


   app = (
    Application
    .builder()
    .token(BOT_TOKEN)
    .build()
)

setup_scheduler(app)


    # Commands

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )


    app.add_handler(
        CommandHandler(
            "pivot",
            pivot_command
        )
    )


    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )


    logging.info(
        "ParthTraderAlerts Bot Started"
    )


    app.run_polling()



# ==========================================================
# Run Bot
# ==========================================================


if __name__ == "__main__":

    main()
    # ==========================================================
# Auto Daily Scheduler
# ==========================================================

from datetime import time as dt_time
from zoneinfo import ZoneInfo

from config import TIMEZONE, SEND_TIME


# ==========================================================
# Schedule Daily Pivot Message
# ==========================================================

def setup_scheduler(app):

    hour, minute = map(
        int,
        SEND_TIME.split(":")
    )


    app.job_queue.run_daily(
        send_pivot_message,
        time=dt_time(
            hour=hour,
            minute=minute,
            tzinfo=ZoneInfo(TIMEZONE)
        ),
        name="Daily_Pivot_Update"
    )


    logging.info(
        "Daily 09:15 AM Pivot Scheduler Added"
    )

   
