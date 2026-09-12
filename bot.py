import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

# إعدادات اللوقينغ (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # أمر /start
    welcome_message = (
        "أهلاً بك يا أنور! البوت يعمل الآن بأفضل مرونة ليسن السوق"
    )
    await update.message.reply_text(welcome_message)

async def check_market(context: ContextTypes.DEFAULT_TYPE):
    # دالة لفحص السوق الدورية
    logger.info("Running market check scheduler...")
    # هنا يتم وضع منطق فحص السوق والأرباح

def main():
    # سحب التوكن من متغيرات البيئة في المنصة (Railway)
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    if not TOKEN:
        logger.error("Please set the TELEGRAM_TOKEN environment variable!")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # إضافة معلّقات الأمر
    application.add_handler(CommandHandler("start", start))

    # إعداد المجدول الزمني
    scheduler = BackgroundScheduler()
    
    # إضافة المهام الدورية (مثلاً كل 30 ثانية)
    scheduler.add_job(check_market, 'interval', seconds=30)
    
    scheduler.start()

    # تشغيل البوت
    application.run_polling()

if __name__ == '__main__':
    main()
