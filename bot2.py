import os
import time
import requests

# طباعة تأكيد بداية التشغيل لضمان ظهورها في سجلات رايلواي
print("🚀 Naif Edge Bot is starting up...", flush=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

print(f"Token loaded: {'Yes' if TELEGRAM_TOKEN else 'No'}", flush=True)
print(f"Polygon API loaded: {'Yes' if POLYGON_API_KEY else 'No'}", flush=True)

# باقي الكود الموجود عندك
TOKEN = "..." 
CHAT_ID = "..."

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}", flush=True)

def check_ichimoku_breakout_15m(df):
    # حسابات الإشيموكو والبيانات
    pass
