import os
import time
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests

# إعدادات بوت التليجرام (تأكد من وضع التوكن ورقم الكود الخاص بك أو ربطه بمتغيرات البيئة)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

# قائمة الأسهم والمؤشرات المستهدفة للمراقبة
WATCHLIST = ["SPY", "QQQ", "TSLA", "NVDA", "AAPL"]

def send_telegram_message(message):
    """إرسال إشعار نصي عبر بوت التليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

def check_ichimoku_strategy(symbol):
    """تحليل مؤشر الإشيموكو وفلتر خط الشيكو سبان للأسهم"""
    try:
        # جلب بيانات الشموع اليومية أو لكل ساعة
        data = yf.download(symbol, period="60d", interval="1h", progress=False)
        if data.empty:
            return None

        # حساب مؤشر الإشيموكو باستخدام pandas_ta
        ichimoku = ta.ichimoku(data['High'], data['Low'], data['Close'])
        
        # أسماء الأعمدة الناتجة من الإشيموكو
        tenkan_col = [c for c in ichimoku[0].columns if 'ITS' in c][0]
        kijun_col = [c for c in ichimoku[0].columns if 'IKS' in c][0]
        senkou_a_col = [c for c in ichimoku[0].columns if 'ISA' in c][0]
        senkou_b_col = [c for c in ichimoku[0].columns if 'ISB' in c][0]
        
        df = data.copy()
        df['Tenkan'] = ichimoku[0][tenkan_col]
        df['Kijun'] = ichimoku[0][kijun_col]
        df['Senkou_A'] = ichimoku[0][senkou_a_col]
        df['Senkou_B'] = ichimoku[0][senkou_b_col]
        
        # الشيكو سبان (Chikou Span) - السعر الحالي مزاح للخلف، أو السعر السابق مقارنة بالسحابة
        # كفلتر اتجاه: السعر الحالي يجب أن يكون خارج السحابة ويفضل فوقها للشراء
        current_close = df['Close'].iloc[-1]
        current_tenkan = df['Tenkan'].iloc[-1]
        current_kijun = df['Kijun'].iloc[-1]
        prev_tenkan = df['Tenkan'].iloc[-2]
        prev_kijun = df['Kijun'].iloc[-2]
        
        senkou_a_val = df['Senkou_A'].iloc[-1]
        senkou_b_val = df['Senkou_B'].iloc[-1]
        upper_cloud = max(senkou_a_val, senkou_b_val)
        lower_cloud = min(senkou_a_val, senkou_b_val)

        # شروط التقاطع (Tenkan تقاطع Kijun) مع وجود السعر فوق السحابة
        bullish_cross = (prev_tenkan < prev_kijun) and (current_tenkan > current_kijun)
        above_cloud = current_close > upper_cloud

        if bullish_cross and above_cloud:
            msg = (
                f"🚀 **إشارة إشيموكو إيجابية (BUY)** 🚀\n"
                f"الرمز: `{symbol}`\n"
                f"السعر الحالي: `{current_close:.2f}`\n"
                f"الحالة: تقاطع Tenkan/Kijun للأعلى فوق سحابة الكومو السحابية."
            )
            send_telegram_message(msg)
            return symbol

    except Exception as e:
        print(f"خطأ أثناء تحليل السهم {symbol}: {e}")
    
    return None

def main():
    print("بدء تشغيل بوت الإشيموكو لمراقبة السوق...")
    send_telegram_message("🟢 تم تشغيل بوت الإشيموكو بنجاح وجاهز للمراقبة.")
    
    while True:
        for symbol in WATCHLIST:
            check_ichimoku_strategy(symbol)
            time.sleep(5)  # فاصل قصير بين كل سهم لتجنب الضغط على الخادم
        
        # الانتظار لمدة ساعة قبل الفحص القادم (أو حسب رغبتك)
        time.sleep(3600)

if __name__ == "__main__":
    main()
