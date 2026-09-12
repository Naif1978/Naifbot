import os
import time
import threading
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot_client = Bot(token=TOKEN)

def get_market_session_status():
    sa_tz = timezone(timedelta(hours=3))
    now = datetime.now(sa_tz)
    hour = now.hour
    minute = now.minute
    total_minutes = hour * 60 + minute
    
    session_info = "🌍 *حالة الجلسات العالمية الحالية:*\n"
    if 180 <= total_minutes < 660:
        session_info += "• الجلسة النشطة حالياً: 🟢 **آسيا (طوكيو)** - سيولة هادئة وتأسيس نطاق."
    elif 600 <= total_minutes < 1140:
        session_info += "• الجلسة النشطة حالياً: 🟢 **لندن (أوروبا)** - تداولات قوية وبدء الزخم."
    elif 960 <= total_minutes < 1380:
        session_info += "• الجلسة النشطة حالياً: 🟢 **أمريكا (نيويورك)** - السيولة الكبرى والحرارة العالية 🔥."
    else:
        session_info += "• حالة السوق: 🟡 **فترة بين الجلسات / إغلاق رئيسي**."
    return session_info

def analyze_timeframe(interval_str, timeframe_name):
    try:
        if interval_str in ["15m"]:
            range_val = "5d"
        elif interval_str in ["1h", "4h"]:
            range_val = "60d"
        elif interval_str in ["1d"]:
            range_val = "1y"
        else:
            range_val = "max"

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval={interval_str}&range={range_val}"
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
        
        diff = abs(tenkan - kijun)
        price_threshold = close_price * 0.0015
        
        df['tenkan_above'] = df['ITS_9'] > df['IKS_26']
        df['cross_change'] = df['tenkan_above'] != df['tenkan_above'].shift(1)
        cross_indices = df.index[df['cross_change']].tolist()
        
        if cross_indices:
            last_cross_idx = cross_indices[-1]
            candles_since_cross = len(df) - 1 - df.index.get_loc(last_cross_idx)
        else:
            candles_since_cross = 999

        if candles_since_cross == 0:
            cross_status = "⚡ تقاطع حدث للتو في هذه الشمعة!"
        elif diff <= price_threshold:
            cross_status = f"⚠️ *تنبيه مبكر:* الخطين متقاربين جداً والتقاطع وشيك على هذا الفريم!"
        elif candles_since_cross <= 5:
            cross_status = f"✅ تقاطع قائم ومستقر منذ {candles_since_cross} شمعات."
        else:
            cross_status = f"⏳ التقاطع صار له فترة ({candles_since_cross} شمعة)."

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
            f"• *السعر:* `{close_price:.2f}` | *الاتجاه:* {trend}\n"
            f"• *السحابة:* {cloud_color} ({cloud_status})\n"
            f"• *حالة التقاطع:* {cross_status}\n"
            f"• *Chikou:* `{chikou:.2f}` | *Tenkan:* `{tenkan:.2f}` | *Kijun:* `{kijun:.2f}`\n"
        )
        return report
    except Exception as e:
        return f"📌 *الفريم: {timeframe_name}*\n❌ خطأ في الجلب: {e}\n"

def get_full_analysis():
    sessions_status = get_market_session_status()
    msg_15m = analyze_timeframe("15m", "15 دقيقة (لحظي)")
    msg_1h = analyze_timeframe("1h", "الساعة (1H)")
    msg_4h = analyze_timeframe("4h", "4 ساعات (4H)")
    msg_1d = analyze_timeframe("1d", "اليومي (Daily)")
    msg_1wk = analyze_timeframe("1wk", "الأسبوعي (Weekly)")
    
    full_msg = (
        f"📊 *تقرير مؤشر SPX وجلسات الأسواق (إيتشيموكو)*\n"
        f"===================================\n"
        f"{sessions_status}\n"
        f"-----------------------------------\n"
        f"{msg_15m}\n-----------------------------------\n"
        f"{msg_1h}\n-----------------------------------\n"
        f"{msg_4h}\n-----------------------------------\n"
        f"{msg_1d}\n-----------------------------------\n"
        f"{msg_1wk}"
    )
    return full_msg

def background_monitor():
    time.sleep(15)
    while True:
        try:
            msg = "⚠️ *تنبيه دوري لحالة الأسواق والفريمات*:\n\n" + get_full_analysis()
            if CHAT_ID:
                bot_client.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"خطأ في المراقبة: {e}")
        time.sleep(900)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت يعمل بنجاح، وتمت إزالة فريم 6 ساعات.")

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
