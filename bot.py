import os
import logging
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = update.effective_chat.id
    
    welcome_message = (
        "أهلاً بك يا أبو بدر! البوت يعمل الآن بكفاءة.\n"
        "- يتم فحص مؤشر SPX تلقائياً في الخلفية عند انتهاء الفريمات (ربع ساعة، ساعة، 4 ساعات، 12 ساعة).\n"
        "- يمكنك طلب سهم تسلا في أي وقت عبر الأمر /tsla"
    )
    await update.message.reply_text(welcome_message)

async def tsla_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = yf.Ticker("TSLA")
        todays_data = stock.history(period="1d")
        if not todays_data.empty:
            price = todays_data['Close'].iloc[-1]
            await update.message.reply_text(f"سعر سهم تسلا (TSLA) الحالي: {round(price, 2)} دولار")
        else:
            await update.message.reply_text("عذراً، لم نتمكن من جلب بيانات السهم حالياً.")
    except Exception as e:
        logger.error(f"Error fetching stock data: {e}")
        await update.message.reply_text("حدث خطأ أثناء جلب بيانات السهم.")

async def spx_price_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        spx = yf.Ticker("^GSPC")
        todays_data = spx.history(period="1d")
        if not todays_data.empty:
            price = todays_data['Close'].iloc[-1]
            await update.message.reply_text(f"مؤشر S&P 500 (SPX) الحالي: {round(price, 2)}")
        else:
            await update.message.reply_text("عذراً، لم نتمكن من جلب بيانات المؤشر حالياً.")
    except Exception as e:
        logger.error(f"Error fetching SPX data: {e}")
        await update.message.reply_text("حدث خطأ أثناء جلب بيانات المؤشر.")

def check_timeframes():
    logger.info("Checking market across timeframes: 15m, 1h, 4h, 12h...")
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="2d", interval="15m")
        if not data.empty:
            latest_close = data['Close'].iloc[-1]
            logger.info(f"SPX Timeframe check completed. Latest Price: {round(latest_close, 2)}")
    except Exception as e:
        logger.error(f"Error in timeframe check: {e}")

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    if not TOKEN:
        logger.error("Please set the TELEGRAM_TOKEN environment variable!")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tsla", tsla_price))
    application.add_handler(CommandHandler("spx", spx_price_manual))

    scheduler = BackgroundScheduler()
    # فحص دوري كل 15 دقيقة لتغطية الفريمات المطلوبة
    scheduler.add_job(check_timeframes, 'interval', minutes=15)
    scheduler.start()

    application.run_polling()

if __name__ == '__main__':
    main()
