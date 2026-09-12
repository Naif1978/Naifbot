import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

# إعداد السجلات (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دالة الترحيب عند إرسال أمر /start"""
    welcome_message = (
        "أهلاً بك يا أبو بدر! البوت يعمل الآن بكامل ميزاته لفحص السوق "
        "والسحابة."
    )
    await update.message.reply_text(welcome_message)

async def check_market(context: ContextTypes.DEFAULT_TYPE):
    """دالة فحص السوق الدورية"""
    logger.info("Running market check scheduler...")
    # هنا يتم وضع منطق فحص السوق والإرسال (مثل السحابة أو التنبيهات)

def main():
    # توكن البوت الحقيقي
    TOKEN = "8724416568:AAFXBsrKKEem5NuM9MKeo3Yb5FHbYe_B4IU"

    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Please insert your actual Telegram bot token in the code!")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))

    # إعداد الجدول الخلفي الآمن
    scheduler = BackgroundScheduler()
    
    # جدولة المهام الدورية (كل 30 دقيقة)
    scheduler.add_job(
        check_market, "interval", minutes=30, args=[application]
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully.")

    # تشغيل البوت بأمان
    application.run_polling()

if __name__ == "__main__":
    main()
