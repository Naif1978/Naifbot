import os
import time
import requests
import pandas as pd
import pandas_ta as ta
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

def send_alert(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
        print("تم إرسال التنبيه بنجاح")
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

def check_ichimoku_strategy():
    try:
        # جلب البيانات الحية لمؤشر SPX (^GSPC) من فريم 15 دقيقة
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

        # حساب مؤشر إيتشيموكو (pandas_ta يرجع الأعمدة بأسماء محددة مثل ITS, IKS, ISA, ISB, ICS)
        ichimoku_df, span = ta.ichimoku(df['high'], df['low'], df['close'])
        df = pd.concat([df, ichimoku_df], axis=1)
        
        latest = df.iloc[-1]
        close_price = latest['close']
        
        # استخراج القيم الأساسية لإيتشيموكو
        tenkan = latest.get('ITS_9', 0)       # الخط التحويلي
        kijun = latest.get('IKS_26', 0)       # الخط الأساسي
        senkou_a = latest.get('ISA_9', 0)     # سحابة أ
        senkou_b = latest.get('ISB_26', 0)    # سحابة ب
        chikou = latest.get('ICS_26', 0)      # الخط المتأخر (الأسود)
        
        # 1. تحديد الاتجاه (حسب تقاطع Tenkan مع Kijun أو موقع السعر)
        if tenkan > kijun and close_price > senkou_a:
            trend = "صاعد 🟢"
        elif tenkan < kijun and close_price < senkou_b:
            trend = "نازل 🔴"
        else:
            trend = "عرضي / متذبذب 🟡"
            
        # 2. تحديد لون السحابة
        cloud_color = "خضراء 🟢" if senkou_a > senkou_b else "حمراء 🔴"
        
        # 3. صياغة التنبيه بالمتطلبات اللي طلبته
        message = (
            f"📊 *تحليل مؤشر SPX اللحظي (إيتشيموكو)*\n\n"
            f"• *السعر الحالي:* `{close_price:.2f}`\n"
            f"• *الاتجاه العام:* {trend}\n"
            f"• *لون السحابة:* {cloud_color}\n"
            f"• *الخط المتأخر (الأسود / Chikou):* `{chikou:.2f}`\n"
            f"• *Tenkan-sen:* `{tenkan:.2f}`\n"
            f"• *Kijun-sen:* `{kijun:.2f}`"
        )
        
        send_alert(message)
        
    except Exception as e:
        print(f"خطأ أثناء التحليل: {e}")

if __name__ == "__main__":
    print("بدء تشغيل بوت تحليل SPX للإيتشيموكو...")
    while True:
        check_ichimoku_strategy()
        # فحص وتحديث البيانات كل 15 دقيقة
        time.sleep(900)
