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

# إعداد السجلات (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WATCHLIST = ["SPX", "SPY", "QQQ", "AAPL", "TSLA", "NVDA"]
ACTIVE_CHAT_ID = None


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


# تعريف الجدول الخلفي بدون مشاكل Asyncio
scheduler = BackgroundScheduler()


# دالة لبدء تشغيل البوت
def main():
  # استخراج التوكن من متغيرات البيئة في المنصة
  TOKEN = os.getenv("TELEGRAM_TOKEN")
  if not TOKEN:
    logger.error("TELEGRAM_TOKEN is not set in environment variables!")
    return

  application = ApplicationBuilder().token(TOKEN).build()

  # يمكنك إضافة الهاندلر والأوامر هنا حسب الحاجة
  # مثال: application.add_handler(CommandHandler("start", start))

  # تشغيل الجدولة
  scheduler.start()
  logger.info("Scheduler started successfully with BackgroundScheduler.")

  # بدء استقبال الرسائل والتشغيل
  application.run_polling()


if __name__ == "__main__":
  main()
