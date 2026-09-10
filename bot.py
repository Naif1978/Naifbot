import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# إعدادات بوت تليجرام من متغيرات البيئة في ريلواي
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        print("Telegram token or chat ID is missing. Please check Railway Variables.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
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
    # تحليل بيانات مؤشر SPX المستهدف
    ticker_symbol = "^GSPC"
    
    # الفريمات المطلوبة متوافقة تماماً مع قيود yfinance المسموحة
    intervals = {
        "خمس دقايق": {"period": "5d", "interval": "5m"},
        "ربع ساعة": {"period": "5d", "interval": "15m"},
        "ساعة": {"period": "730d", "interval": "60m"},
        "أربع ساعات": {"period": "730d", "interval": "60m"},
        "يومي": {"period": "6mo", "interval": "1d"},
        "أسبوعي": {"period": "2y", "interval": "1wk"}
    }
    
    report = f"📊 *تقرير قمم ونسب الفريمات لـ (SPX)*:\n\n"
    
    for frame_name, params in intervals.items():
        try:
            data = yf.download(ticker_symbol, period=params["period"], interval=params["interval"], progress=False)
            
            if data is None or data.empty:
                continue
                
            # التعامل مع الأعمدة المتعددة في الإصدارات الحديثة
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
                
            current_price = float(data['Close'].iloc[-1])
            highest_high = float(data['High'].max())
            lowest_low = float(data['Low'].min())
            
            if highest_high == lowest_low:
                percentage = 0.0
            else:
                percentage = ((current_price - lowest_low) / (highest_high - lowest_low)) * 100
                
            report += f"🔹 *{frame_name}*:\n"
            report += f"   • السعر الحالي: `{current_price:.2f}`\n"
            report += f"   • القمة: `{highest_high:.2f}` | القاع: `{lowest_low:.2f}`\n"
            report += f"   • نسبة الموقع: `{percentage:.1f}%`\n\n"
        except Exception as e:
            print(f"Error processing {frame_name}: {e}")
            
    return report

if __name__ == "__main__":
    print("Bot is running 24/7...")
    # تأخير بسيط للتأكد من استقرار الاتصال عند بدء التشغيل
    time.sleep(5)
    while True:
        try:
            msg = calculate_levels_and_percentages()
            if msg:
                send_telegram_message(msg)
        except Exception as e:
            print(f"Main loop error: {e}")
        # الانتظار لمدة ساعة قبل التحديث التالي لتجنب الحظر
        time.sleep(3600)
