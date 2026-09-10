import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# إعدادات بوت تيليجرام من متغيرات البيئة في ريلواي
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# يمكنك وضع معرف الدردشة الخاص بك هنا أو جلبه ديناميكياً
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") 

def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        print("Telegram token or chat ID is missing.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_icon": "📈",
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")

def calculate_levels_and_percentages():
    # الرمز المستهدف SPX (أو SPY كبديل بيانات حي)
    ticker_symbol = "^GSPC" 
    
    # الفريمات المطلوبة (تشمل الأسبوعي واليومي والفريمات اللحظية)
    intervals = {
        "خمس دقائق": {"period": "5d", "interval": "5m"},
        "ربع ساعة": {"period": "5d", "interval": "15m"},
        "ساعة": {"period": "1mo", "interval": "1h"},
        "أربع ساعات": {"period": "2mo", "interval": "60m"}, # تجميعية أو ساعة
        "يومي": {"period": "6mo", "interval": "1d"},
        "أسبوعي": {"period": "1y", "interval": "1wk"}
    }
    
    report = "📊 *تقرير قمم ونسب الفريمات (SPX)* 📊\n\n"
    
    for frame_name, params in intervals.items():
        try:
            data = yf.download(ticker_symbol, period=params["period"], interval=params["interval"], progress=False)
            if data.empty:
                continue
            
            # التعامل مع الأعمدة المتاحة
            high_col = 'High' if 'High' in data.columns else data.columns[1]
            low_col = 'Low' if 'Low' in data.columns else data.columns[2]
            close_col = 'Close' if 'Close' in data.columns else data.columns[4]
            
            highest_high = data[high_col].max()
            lowest_low = data[low_col].min()
            current_price = data[close_col].iloc[-1]
            
            # حساب النسبة المئوية للموقع الحالي بين القمة والقاع
            range_val = highest_high - lowest_low
            if range_val > 0:
                position_pct = ((current_price - lowest_low) / range_val) * 100
            else:
                position_pct = 0.0
                
            report += f"🔹 *فريم {frame_name}:*\n"
            report += f"   • السعر الحالي: `{current_price:.2f}`\n"
            report += f"   • أعلى قمة: `{highest_high:.2f}`\n"
            report += f"   • أدنى قاع: `{lowest_low:.2f}`\n"
            report += f"   • النسبة: `{position_pct:.1f}%`\n\n"
        except Exception as e:
            print(f"Error processing {frame_name}: {e}")
            
    return report

if __name__ == "__main__":
    print("Bot is running 24/7...")
    while True:
        msg = calculate_levels_and_percentages()
        if CHAT_ID:
            send_telegram_message(msg)
        else:
            print(msg) # للطباعة في السيرفر إذا لم يتم ضبط الـ Chat ID بعد
        # يرسل تحديث دوري كل ساعة (أو يمكنك التحكم بالوقت)
        time.sleep(3600)
