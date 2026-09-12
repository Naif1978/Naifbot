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

        df_data = result[0]
        timestamps = df_data.get('timestamp', [])
        quotes = df_data.get('indicators', {}).get('quote', [{}])[0]
        
        if not timestamps or not quotes:
            return f"⚠️ البيانات غير متوفرة للفريم {timeframe_name}."

        df = pd.DataFrame({
            'Datetime': [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in timestamps],
            'Open': quotes.get('open', []),
            'High': quotes.get('high', []),
            'Low': quotes.get('low', []),
            'Close': quotes.get('close', []),
            'Volume': quotes.get('volume', [])
        }).dropna()

        if df.empty or len(df) < 26:
            return f"⚠️ بيانات غير كافية للتحليل للفريم {timeframe_name}."

        # حساب مؤشر Ichimoku Kinko Hyo
        high_9 = df['High'].rolling(window=9).max()
        low_9 = df['Low'].rolling(window=9).min()
        tenkan = (high_9 + low_9) / 2

        high_26 = df['High'].rolling(window=26).max()
        low_26 = df['Low'].rolling(window=26).min()
        kijun = (high_26 + low_26) / 2

        senkou_a = ((tenkan + kijun) / 2).shift(26)
        high_52 = df['High'].rolling(window=52).max()
        low_52 = df['Low'].rolling(window=52).min()
        senkou_b = ((high_52 + low_52) / 2).shift(26)

        close_price = df['Close'].iloc[-1]
        tenkan_val = tenkan.iloc[-1]
        kijun_val = kijun.iloc[-1]
        senkou_a_val = senkou_a.iloc[-1]
        senkou_b_val = senkou_b.iloc[-1]

        if tenkan_val > kijun_val and close_price > max(senkou_a_val, senkou_b_val):
            trend = "🟢 صاعد قوي"
        elif tenkan_val < kijun_val and close_price < min(senkou_a_val, senkou_b_val):
            trend = "🔴 هابط قوي"
        else:
            trend = "🟡 عرضي / متذبذب"

        cloud_color = "🟢 أخضر" if senkou_a_val > senkou_b_val else "🔴 أحمر"
        
        report = (
            f"📌 **الإطار:** {timeframe_name}\n"
            f" • **السعر:** `{close_price:.2f}` | **الاتجاه:** {trend}\n"
            f" • **السحابة:** ({cloud_color})\n"
            f" • **Tenkan:** `{tenkan_val:.2f}` | **Kijun:** `{kijun_val:.2f}`"
        )
        return report
    except Exception as e:
        return f"⚠️ خطأ في الفريم {timeframe_name}: {str(e)[:50]}"

def get_full_analysis(symbol):
    sessions_status = get_market_session_status()
    msg_15m = analyze_timeframe(symbol, "15m", "15 (لحظي)")
    msg_1h = analyze_timeframe(symbol, "1h", "1h (ساعة)")
    msg_4h = analyze_timeframe(symbol, "4h", "4h (4 ساعات)")
    msg_1d = analyze_timeframe(symbol, "1d", "Daily (اليومي)")
    msg_1wk = analyze_timeframe(symbol, "1wk", "Weekly (الأسبوعي)")

    clean_symbol = symbol.replace("^", "")
    full_msg = (
        f"📊 **تقرير السهم / المؤشر:** (`{clean_symbol.upper()}`)\n"
        f"============================\n"
        f"{sessions_status}\n"
        f"----------------------------------------\n"
        f"{msg_15m}\n"
        f"----------------------------------------\n"
        f"{msg_1h}\n"
        f"----------------------------------------\n"
        f"{msg_4h}\n"
        f"----------------------------------------\n"
        f"{msg_1d}\n"
        f"----------------------------------------\n"
        f"{msg_1wk}\n"
        f"============================"
    )
    return full_msg

async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            await update.message.reply_text("⚠️ أرجو تحديد اسم السهم، مثال:\n`/stock tsla` أو `/stock spy`", parse_mode="Markdown")
            return
        
        symbol = args[0]
        msg = await update.message.reply_text(f"🔍 جاري فحص السهم: `{symbol.upper()}`...", parse_mode="Markdown")
        
        # تنفيذ التحليل
        analysis_result = get_full_analysis(symbol)
        
        await msg.edit_text(analysis_result, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء تنفيذ الأمر: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("stock", stock_command))
    application.run_polling()
