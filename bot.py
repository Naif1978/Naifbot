import os
import time
import threading
import requests
import pandas as pd
import pandas_ta as ta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
        chikou = latest.get('ICS_26', 0)
        
        if tenkan > kijun and close_price > senkou_a:
            trend = "صاعد 🟢"
        elif tenkan < kijun and close_price < senkou_b:
            trend = "نازل 🔴"
        else:
            trend = "عرضي / متذبذب 🟡"
            
        cloud_color = "خضراء 🟢" if senkou_a > senkou_b else "حمراء 🔴"
        
        message = (
            f"📊 *تحليل مؤشر SPX اللحظي (إيتشيموكو)*\n\n"
            f"• *السعر الحالي:* `{close_price:.2f}`\n"
            f"• *الاتجاه العام:* {trend}\n"
            f"• *لون السحابة:* {cloud_color}\n"
            f"• *الخط المتأخر (الأسود / Chikou):* `{chikou:.2f}`\n"
            f"• *Tenkan-sen:* `{tenkan:.2f}`\n"
            f"• *Kijun-sen:* `{kijun:.2f}`"
        )
        return message
    except Exception as e:
        return f"خطأ أثناء جلب وتحليل بيانات SPX: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك يا أبو بدر! البوت يعمل الآن بكفاءة.\n"
        "- يتم فحص مؤشر SPX تلقائياً.\n"
        "- يمكنك طلب تحليل SPX فوراً عبر الأمر /spx"
    )

async def spx_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    analysis_text = get_spx_analysis()
    await update.message.reply_text(analysis_text, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("spx", spx_command))
    
    print("البوت يعمل الآن ويستقبل الأوامر...")
    app.run_polling()

if __name__ == "__main__":
    main()
