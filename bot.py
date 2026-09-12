import os
import time
import threading
import requests
import pandas as pd
import pandas_ta as ta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot_client = Bot(token=TOKEN)

def get_spx_analysis():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=15m&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': quotes['open'],
            'high': quotes['high'],
            'low': quotes['low'],
            'close': quotes['close'],
            'volume': quotes['volume']
        }).dropna()

        ichimoku_df, span = ta.ichimoku(df['high'], df['low'], df['close'])
        df = pd.concat([df, ichimoku_df], axis=1)
        
        latest = df.iloc[-1]
        close_price = latest['close']
        
        tenkan = latest.get('ITS_9', 0)
        kijun = latest.get('IKS_26', 0)
        senkou_a = latest.get('ISA_9', 0)
        senkou_b = latest.get('ISB_26', 0)
        
        # استخراج قيمة Chikou Span وتجنب الـ NaN نهائياً
        chikou = 0
        # البحث عن عمود يبدأ بـ ICS في الجدول المستخرج
        ics_cols = [col for col in df.columns if col.startswith('ICS')]
        if ics_cols and not pd.isna(latest.get(ics_cols[0])):
            chikou = latest.get(ics_cols[0])
        elif len(df) >= 26:
            # طريقة بديلة دقيقة: السعر الحالي يعادل سعر إغلاق قبل 26 شمعة للخط المتأخر
            chikou = df.iloc[-26]['close']
        else:
            chikou = close_price

        # تقييم الاتجاه والسحابة بناءً على شروطك
        if tenkan > kijun and close_price > max(senkou_a, senkou_b):
            trend = "صاعد 🟢"
        elif tenkan < kijun and close_price < min(senkou_a, senkou_b):
            trend = "نازل 🔴"
        else:
            trend = "عرضي / متذبذب 🟡"
            
        cloud_color = "خضراء 🟢" if senkou_a > senkou_b else "حمراء 🔴"
        
        # فحص كفاءة السحابة (ضعيفة أو قوية)
        cloud_thickness = abs(senkou_a - senkou_b)
        cloud_status = "ضعيفة (مناسبة للدخول)" if cloud_thickness < 15 else "قوية"

        message = (
            f"📊 *تحليل مؤشر SPX اللحظي (إيتشيموكو)*\n\n"
            f"• *السعر الحالي:* `{close_price:.2f}`\n"
            f"• *الاتجاه العام:* {trend}\n"
            f"• *لون السحابة:* {cloud_color} (السحابة: {cloud_status})\n"
            f"• *الخط المتأخر (Chikou):* `{chikou:.2f}`\n"
            f"• *Tenkan-sen (الأحمر):* `{tenkan:.2f}`\n"
            f"• *Kijun-sen (الأزرق):* `{kijun:.2f}`"
        )
        return message
    except Exception as e:
        return f"خطأ أثناء التحليل: {e}"

def background_monitor():
    time.sleep(15)
    while True:
        try:
            msg = "⚠️ *تنبيه مبكر قبل إغلاق الشمعة بـ 15 دقيقة*:\n\n" + get_spx_analysis()
            if CHAT_ID:
                bot_client.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"خطأ في المراقبة: {e}")
        time.sleep(900) # فحص كل 15 دقيقة

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت يعمل وجاهز، تم تصحيح مشكلة الخط المتأخر.")

async def spx_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = get_spx_analysis()
    await update.message.reply_text(report, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("spx", spx_command))
    
    t = threading.Thread(target=background_monitor, daemon=True)
    t.start()
    
    app.run_polling()

if __name__ == "__main__":
    main()
