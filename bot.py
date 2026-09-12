import os
import datetime
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# نسبة الاقتراب المبكر (0.5%) لتنبيهك بمسافة كافية جداً
PROXIMITY_THRESHOLD = 0.005 

def check_market_status():
    """التحقق مما إذا كان السوق في عطلة نهاية الأسبوع (السبت والأحد بتوقيت نيويورك/السوق الأمريكي)"""
    # استخدام توقيت نيويورك لتحديد عطلة السوق بدقة
    now_et = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4))) # EDT تقريباً
    weekday = now_et.weekday() # 5 = السبت، 6 = الأحد
    if weekday in [5, 6]:
        return "🔴 **حالة السوق:** مغلق حالياً (عطلة نهاية الأسبوع - السبت والأحد). البيانات المعروضة تعكس إغلاق يوم الجمعة الأخير."
    return "🟢 **حالة السوق:** مفتوح أو في ساعات التداول/التسوية."

def calculate_ichimoku_advanced_alerts(data):
    """حساب الإيشيموكو مع تحديد لون السحابة ومراقبة اقتراب الخط المتأخر"""
    if data.empty or len(data) < 52:
        return None, None, None, None, [], "بيانات غير كافية"

    high_9 = data['High'].rolling(window=9).max()
    low_9 = data['Low'].rolling(window=9).min()
    tenkan_sen = (high_9 + low_9) / 2

    high_26 = data['High'].rolling(window=26).max()
    low_26 = data['Low'].rolling(window=26).min()
    kijun_sen = (high_26 + low_26) / 2

    senkou_span_a = (tenkan_sen + kijun_sen) / 2

    high_52 = data['High'].rolling(window=52).max()
    low_52 = data['Low'].rolling(window=52).min()
    senkou_span_b = (high_52 + low_52) / 2

    close = data['Close'].iloc[-1]
    tenkan = tenkan_sen.iloc[-1]
    kijun = kijun_sen.iloc[-1]
    
    # السحابة المسقطة
    span_a = senkou_span_a.shift(26).iloc[-1]
    span_b = senkou_span_b.shift(26).iloc[-1]

    if pd.isna(span_a) or pd.isna(span_b):
        span_a = senkou_span_a.iloc[-1]
        span_b = senkou_span_b.iloc[-1]

    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)

    # تحديد لون السحابة
    if span_a > span_b:
        cloud_color = "سحابة خضراء 🟢"
    else:
        cloud_color = "سحابة حمراء 🔴"

    if close > cloud_top:
        cloud_status = f"فوق السحابة ({cloud_color})"
    elif close < cloud_bottom:
        cloud_status = f"تحت السحابة ({cloud_color})"
    else:
        cloud_status = f"داخل السحابة ({cloud_color})"

    alerts = []
    
    # فحص اقتراب الخط المتأخر (Chikou Span)
    if len(data) > 35:
        historical_close_26 = data['Close'].iloc[-26]
        historical_tenkan_26 = tenkan_sen.iloc[-26]
        historical_kijun_26 = kijun_sen.iloc[-26]

        # 1. اقتراب الخط المتأخر من الشموع التاريخية
        dist_to_price = abs(close - historical_close_26) / close
        if dist_to_price <= PROXIMITY_THRESHOLD:
            if close > historical_close_26:
                alerts.append("⚠️ تنبيه مبكر: الخط المتأخر يوشك على اختراق الشموع من الأعلى!")
            else:
                alerts.append("⚠️ تنبيه مبكر: الخط المتأخر يوشك على كسر الشموع من الأسفل!")

        # 2. اقتراب الخط المتأخر من خط التحويل (Tenkan)
        if pd.notna(historical_tenkan_26):
            dist_to_tenkan = abs(close - historical_tenkan_26) / close
            if dist_to_tenkan <= PROXIMITY_THRESHOLD:
                alerts.append(f"🎯 تنبيه قوي جداً: الخط المتأخر يقترب للغاية من خط التحويل (Tenkan) عند `{historical_tenkan_26:.2f}`!")

        # 3. اقتراب الخط المتأخر من خط الأساس (Kijun)
        if pd.notna(historical_kijun_26):
            dist_to_kijun = abs(close - historical_kijun_26) / close
            if dist_to_kijun <= PROXIMITY_THRESHOLD:
                alerts.append(f"🎯 تنبيه قوي جداً: الخط المتأخر يقترب للغاية من خط الأساس (Kijun) عند `{historical_kijun_26:.2f}`!")

    return close, tenkan, kijun, cloud_status, alerts, None

def get_multi_timeframe_analysis(symbol):
    market_note = check_market_status()
    report = f"📊 **تحليل الإيشيموكو الشامل والخط المتأخر للرمز: {symbol.upper()}**\n"
    report += f"{market_note}\n"
    report += "━━━━━━━━━━━━━━━━━━━\n"

    try:
        raw_1h = yf.download(tickers=symbol, interval="1h", period="60d", progress=False)
        if raw_1h.empty:
            return f"❌ تعذر العثور على بيانات للرمز: {symbol.upper()}"
        
        if isinstance(raw_1h.columns, pd.MultiIndex):
            raw_1h.columns = raw_1h.columns.get_level_values(0)

        timeframes_data = {
            "⏱ 15 دقيقة": yf.download(tickers=symbol, interval="15m", period="5d", progress=False),
            "⏱ ساعة (1h)": raw_1h,
            "⏱ 4 ساعات (4h)": raw_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(),
            "⏱ 12 ساعة": raw_1h.resample('12h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(),
            "📅 يومي (Daily)": yf.download(tickers=symbol, interval="1d", period="1y", progress=False),
            "📈 أسبوعي (Weekly)": yf.download(tickers=symbol, interval="1wk", period="2y", progress=False)
        }

        for tf_name, df in timeframes_data.items():
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            c, t, k, st, alerts_list, err = calculate_ichimoku_advanced_alerts(df)
            if not err:
                report += f"• **{tf_name}:** السعر `{c:.2f}` | التينكان `{t:.2f}` | الكيجون `{k:.2f}` | {st}\n"
                for al in alerts_list:
                    report += f"  └ {al}\n"

        report += "\n🔍 *النظام يعمل 24/7 لمراقبة السحب والخط المتأخر.*"
        return report

    except Exception as e:
        return f"حدث خطأ أثناء جلب وتحليل البيانات: {e}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if len(text) <= 6:
        await update.message.reply_text("⏳ جاري سحب البيانات وفحص السحب والخط المتأخر...")
        result = get_multi_timeframe_analysis(text)
        await update.message.reply_text(result, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    print("🚀 البوت يعمل 24/7 ومزود بالتحقق من عطلة السوق...")
    main()
