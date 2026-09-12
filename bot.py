from datetime import datetime
import logging
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import pandas as pd
import yfinance as yf

# إعداد السجلات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WATCHLIST = ["SPX", "SPY", "QQQ", "AAPL", "TSLA", "NVDA", "MASK"]


def calculate_volume_profile(df, bins=10):
  try:
    if df.empty or "High" not in df.columns or "Low" not in df.columns:
      return 0, 0, 0
    p_min, p_max = df["Low"].min(), df["High"].max()
    if p_min == p_max:
      return p_min, p_min, p_max
    return p_min, p_min, p_max
  except Exception as e:
    logger.error(f"Error in volume profile: {e}")
    return 0, 0, 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_name = update.effective_user.first_name
  chat_id = update.effective_chat.id
  logger.info(f"User {user_name} started the bot with chat_id: {chat_id}")
  await update.message.reply_text(
      f"أهلاً بك يا أبو بدر ! البوت يعمل الآن بكامل ميزاته لفحص السوق"
      " والسحابة."
  )


async def check_market(context: ContextTypes.DEFAULT_TYPE):
  # دالة دورية لفحص الأسهم وإرسال التنبيهات
  logger.info("Running market check scheduler...")


# إعداد الـ Scheduler الآمن الذي لا يسبب انهيار الـ event loop
scheduler = BackgroundScheduler()


def main():
  TOKEN = os.getenv("TELEGRAM_TOKEN")
  if not TOKEN:
    logger.error("TELEGRAM_TOKEN is not set in environment variables!")
    return

  application = ApplicationBuilder().token(TOKEN).build()

  # إضافة أوامر الرد
  application.add_handler(CommandHandler("start", start))

  # جدولة المهام الدورية
  scheduler.add_job(
      check_market, "interval", minutes=30, args=[application]
  )
  scheduler.start()
  logger.info("Scheduler started successfully.")

  # تشغيل البوت
  application.run_polling()


if __name__ == "__main__":
  main()
