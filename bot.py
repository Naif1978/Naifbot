import os
import time
import threading
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timezone, timedelta
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot_client = Bot(token=TOKEN)

def get_market_session_status():
    sa_tz = timezone(timedelta(hours=3))
    now = datetime.now(sa_tz)
    hour = now.hour
    minute = now.minute
    total_minutes = hour * 60 + minute
    
    session_info = "\n📊 **حالة الجلسات العالمية المالية:**"
    if 180 <= total_minutes < 660:
        session_info += " • **آسيا (طوكيو):** 🟢 - سيولة هادئة وتأسيس نطاق"
    elif 600 <= total_minutes < 1140:
        session_info += " • **لندن (أوروبا):** 🟢 - تداولات قوية وبدء الزخم"
    elif 960 <= total_minutes < 1380:
        session_info += " • **أمريكا (نيويورك):** 🟢 - السيولة الكبرى والحرارة العالية"
    else:
        session_info += " • **حالة السوق:** 🟡 - فترة بين الجلسات / إغلاق رئيسي"
    return session_info

def analyze_timeframe(symbol, interval_str, timeframe_name):
    try:
        if interval_str in ["15m"]:
            range_val = "5d"
        elif interval_str in ["1h", "4h"]:
            range_val = "60d"
        elif interval_str in ["1d"]:
            range_val = "1y"
        else:
            range_val = "max"

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval_str}&range={range_val}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            response = requests.get(url, headers=headers, timeout=7)
            if response.status_code != 200:
                return f"⚠️ عذراً، تعذر جلب بيانات السهم {symbol} حالياً."
            data = response.json()
        except requests.exceptions.Timeout:
            return f"⚠️ انتهت مهلة الاتصال أثناء جلب بيانات {symbol}، يرجى المحاولة لاحقاً."
        except Exception as e:
            return f"⚠️ حدث خطأ في الاتصال: {str(e)}"

        result = data.get('chart', {}).get('result')
        if not result:
            return f"⚠️ لم يتم العثور على بيانات صحيحة للرمز {symbol}."

        # تكميل بقية تحليل المؤشرات والدوال الخاصة بك هنا...
        
    except Exception as e:
        return f"⚠️ حدث خطأ غير متوقع: {str(e)}"
