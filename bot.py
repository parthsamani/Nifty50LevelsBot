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
   
