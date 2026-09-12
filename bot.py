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

def analyze_timeframe(interval_str, timeframe_name):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval={interval_str}&range=5d"
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
        
        chikou = 0
        ics_cols = [col for col in df.columns if col.startswith('ICS')]
        if ics_cols and not pd.isna(latest.get(ics_cols[0])):
            chikou = latest.get(ics_cols[0])
        elif len(df) >= 26:
            chikou = df.iloc[-26]['close']
        else:
            chikou = close_price

        if tenkan > kijun and close_price > max(senkou_a, senkou_b):
            trend = "صاعد 🟢"
        elif tenkan < kijun and close_price < min(senkou_a, senkou_b):
            trend = "نازل 🔴"
        else:
            trend = "عرضي / متذبذب 🟡"
            
        cloud_color = "خضراء 🟢" if senkou_a > senkou_b else "حمراء 🔴"
        cloud_thickness = abs(senkou_a - senkou_b)
        cloud_status = "ضعيفة (مناسبة للدخول)" if cloud_thickness < 15 else "قوية"

        report = (
            f"📌 *الفريم: {timeframe_name}*\n"
            f"• *السعر الحالي:* `{close_price:.2f}`\n"
            f"• *الاتجاه العام:* {trend}\n"
            f"• *لون السحابة:* {cloud_color} ({cloud_status})\n"
            f"• *الخط المتأخر (Chikou):* `{chikou:.2f}`\n"
            f"• *Tenkan (الأحمر):* `{tenkan:.2f}` | *Kijun (الأزرق):* `{kijun:.2f}`\n"
        )
        return report
    except Exception as e:
        return f"📌 *الفريم: {timeframe_name}*\n❌ خطأ في الجلب: {e}\n"

def get_full_analysis():
    msg_15m = analyze_timeframe("15m", "15 دقيقة (لحظي)")
    msg_1h = analyze_timeframe("1h", "الساعة (Hourly)")
    
    full_msg = (
        f"📊 *تحليل مؤشر SPX متعدد الفريمات (إيتشيموكو)*\n"
        f"-----------------------------------\n"
        f"{msg_15m}\n"
        f"-----------------------------------\n"
        f"{msg_1h}"
    )
    return full_msg

def background_monitor():
    time.sleep(15)
    while True:
        try:
            msg = "⚠️ *تنبيه مبكر قبل إغلاق الشمعة بـ 15 دقيقة*:\n\n" + get_full_analysis()
            if CHAT_ID:
                bot_client.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"خطأ في المراقبة: {e}")
        time.sleep(900)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت يعمل، وتم إضافة الفريمات (15 دقيقة والساعة).")

async def spx_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = get_full_analysis()
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
