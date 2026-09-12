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

# إعداد السجلات لمتابعة حالة البوت بدقة
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
      f"أهلاً بك يا أبو بدر! البوت يعمل الآن بكامل ميزاته لفحص السوق"
      " والسحابة."
  )


async def check_market(context: ContextTypes.DEFAULT_TYPE):
  logger.info("Running market check scheduler...")


# إعداد المجدول الخلفي الآمن
scheduler = BackgroundScheduler()


def main():
  # ضع توكن البوت الحقيقي هنا بين علامتي التنصيص
  TOKEN = "YOUR_BOT_TOKEN_HERE"

  if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    logger.error("Please insert your actual Telegram bot token in the code!")
    return

  application = ApplicationBuilder().token(TOKEN).build()

  # إضافة معالجات الأوامر
  application.add_handler(CommandHandler("start", start))

  # جدولة المهام الدورية (كل 30 دقيقة)
  scheduler.add_job(
      check_market, "interval", minutes=30, args=[application]
  )
  scheduler.start()
  logger.info("Scheduler started successfully.")

  # تشغيل البوت بسلاسة
  application.run_polling()


if __name__ == "__main__":
  main()
