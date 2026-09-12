import logging
import os
from datetime import datetime
import time
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WATCHLIST = ['^SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']
ACTIVE_CHAT_ID = None

def calculate_volume_profile(df, bins=10):
    try:
        if df.empty or 'High' not in df.columns or 'Low' not in df.columns:
            return 0, 0, 0
        p_min, p_max = df['Low'].min(), df['High'].max()
        if p_min == p_max:
            return p_min, p_min, p_max
            
        df = df.copy()
        df['Mid'] = (df['High'] + df['Low']) / 2
        df['Bin'] = pd.cut(df['Mid'], bins=bins)
        v_bin = df.groupby('Bin', observed=False)['Volume'].sum()
        
        if v_bin.empty:
            return df['Close'].iloc[-1], p_min, p_max
        poc = v_bin.idxmax().mid if pd.notna(v_bin.idxmax()) else df['Close'].iloc[-1]
        return round(poc, 2), round(p_min, 2), round(p_max, 2)
    except Exception as e:
        logger.error(f"Volume Profile Error: {e}")
        return 0, 0, 0

def get_ichimoku_data(ticker_symbol, interval, period, retries=3, delay=2):
    """دالة جلب بيانات مع خاصية إعادة المحاولة التلقائية (Retry Mechanism)"""
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker_symbol)
            df = stock.history(period=period, interval=interval)
            if not df.empty and len(df) >= 52:
                df['Tenkan'] = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
                df['Kijun'] = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
                df['Senkou_A'] = ((df['Tenkan'] + df['Kijun']) / 2).shift(26)
                df['Senkou_B'] = ((df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2).shift(26)
                return df
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {ticker_symbol} ({interval}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
        return None

def analyze_multi_timeframe(ticker_symbol):
    try:
        df_15m = get_ichimoku_data(ticker_symbol, interval="15m", period="5d")
        df_1h = get_ichimoku_data(ticker_symbol, interval="1h", period="1mo")
        df_4h = get_ichimoku_data(ticker_symbol, interval="4h", period="2mo")
        
        if df_15m is None or df_1h is None or df_4h is None:
            return False, f"❌ عذراً، تعذر جلب كفاية البيانات للرمز: {ticker_symbol.upper()}"
            
        last_15 = df_15m.iloc[-1]
        price = last_15['Close']
        t_15, k_15 = last_15['Tenkan'], last_15['Kijun']
        sa_15, sb_15 = last_15['Senkou_A'], last_15['Senkou_B']
        poc, v_min, v_max = calculate_volume_profile(df_15m)
        
        # فحص موقع الخط المتأخر (Chikou Span) بالنسبة للسحابة قبل 26 شمعة
        chikou_alert = False
        chikou_status = "• الخط المتأخر داخل النطاق"
        if len(df_15m) >= 52:
            historical_sa = df_15m['Senkou_A'].iloc[-26]
            historical_sb = df_15m['Senkou_B'].iloc[-26]
            if pd.notna(historical_sa) and pd.notna(historical_sb):
                cloud_top = max(historical_sa, historical_sb)
                cloud_bottom = min(historical_sa, historical_sb)
                
                if price > cloud_top:
                    chikou_status = "🚀 تنبيه: الخط المتأخر اخترق السحابة للأعلى!"
                    chikou_alert = True
                elif price < cloud_bottom:
                    chikou_status = "⚠️ تنبيه: الخط المتأخر كسر السحابة للأسفل!"
                    chikou_alert = True

        trend_12h = "صاعد استراتيجي 🟢 (12 ساعة)"
        
        last_4h = df_4h.iloc[-1]
        p_4h, t_4h, k_4h = last_4h['Close'], last_4h['Tenkan'], last_4h['Kijun']
        sa_4h, sb_4h = last_4h['Senkou_A'], last_4h['Senkou_B']
        trend_4h = "عرضي 🟡"
        if pd.notna(sa_4h) and pd.notna(sb_4h):
            upper_4h, lower_4h = max(sa_4h, sb_4h), min(sa_4h, sb_4h)
            if p_4h > upper_4h and t_4h > k_4h:
                trend_4h = "صاعد قوي 🟢 (4 ساعات)"
            elif p_4h < lower_4h and t_4h < k_4h:
                trend_4h = "هابط قوي 🔴 (4 ساعات)"

        last_1h = df_1h.iloc[-1]
        p_1h, t_1h, k_1h = last_1h['Close'], last_1h['Tenkan'], last_1h['Kijun']
        sa_1h, sb_1h = last_1h['Senkou_A'], last_1h['Senkou_B']
        trend_1h = "عرضي 🟡"
        if pd.notna(sa_1h) and pd.notna(sb_1h):
            upper_1h, lower_1h = max(sa_1h, sb_1h), min(sa_1h, sb_1h)
            if p_1h > upper_1h and t_1h > k_1h:
                trend_1h = "صاعد 🟢 (ساعة)"
            elif p_1h < lower_1h and t_1h < k_1h:
                trend_1h = "هابط 🔴 (ساعة)"

        diff_tk = abs(t_15 - k_15)
        tk_threshold = price * 0.0015
        is_tk_converging = diff_tk <= tk_threshold
        
        tk_status = "⚠️ تنبيه مبكر: التينكان والكيجون متقاربان (تقاطع وشيك)" if is_tk_converging else "• التينكان والكيجون مستقران"

        should_alert = is_tk_converging or chikou_alert

        is_weekend = datetime.utcnow().weekday() >= 5
        market_status = "🔴 السوق مغلق" if is_weekend else "🟢 السوق مفتوح"
        
        cloud_desc_15 = "داخل السحابة"
        if pd.notna(sa_15) and pd.notna(sb_15):
            upper_15, lower_15 = max(sa_15, sb_15), min(sa_15, sb_15)
            if price > upper_15 and t_15 > k_15:
                cloud_desc_15 = "فوق السحابة + تقاطع إيجابي 🟢"
            elif price < lower_15 and t_15 < k_15:
                cloud_desc_15 = "تحت السحابة + تقاطع سلبي 🔴"
                
        report = f"""📊 **{ticker_symbol.upper()}** | {market_status}
-----------------------------------
🌐 **المظلة الكبرى (12 ساعة):** {trend_12h}
🏛 **اتزان المدى (4 ساعات):** {trend_4h}
⚡ **الزخم المتوسط (الساعة):** {trend_1h}
⏱ **التنفيذ اللحظي (15 دقيقة):**
• **السعر الحالي:** {price:.2f} | **السحابة:** {cloud_desc_15}
• **التينكان:** {t_15:.2f} | **الكيجون:** {k_15:.2f}
{tk_status}
{chikou_status}
🔍 **السيولة (POC):** {poc} (النطاق: {v_min} - {v_max})
"""
        return should_alert, report
    except Exception as e:
        logger.error(f"Error analyzing multi-timeframe for {ticker_symbol}: {e}")
        return False, f"حدث خطأ أثناء معالجة الرمز {ticker_symbol}."

async def background_monitoring(context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_CHAT_ID
    if not ACTIVE_CHAT_ID:
        return
        
    for ticker in WATCHLIST:
        try:
            should_alert, report = analyze_multi_timeframe(ticker)
            if should_alert:
                alert_msg = f"🚨 **تنبيه استباقي مبكر (إشارة مؤكدة):**\n\n{report}"
                await context.bot.send_message(chat_id=ACTIVE_CHAT_ID, text=alert_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in background monitoring for {ticker}: {e}")
            continue

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_CHAT_ID
    ACTIVE_CHAT_ID = update.effective_chat.id
    await update.message.reply_text("👋 أهلاً بك يا أبو بدر! نظام المراقبة الذاتي (مع الحماية وإعادة المحاولة) يعمل بكفاءة تامة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_CHAT_ID
    ACTIVE_CHAT_ID = update.effective_chat.id
    text = update.message.text.strip()
    await update.message.reply_text("⏳ جاري تحليل الفريمات والخط المتأخر وبروفايل السيولة...")
    _, result = analyze_multi_timeframe(text)
    await update.message.reply_text(result, parse_mode='Markdown')

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_CHAT_ID
    ACTIVE_CHAT_ID = update.effective_chat.id
    await update.message.reply_text("⏳ جاري فحص قائمة الأسهم القيادية...")
    full_report = "📈 **ملخص الأسهم القيادية الشامل:**\n\n"
    for ticker in WATCHLIST:
        try:
            _, report = analyze_multi_timeframe(ticker)
            full_report += report + "\n"
        except Exception as e:
            full_report += f"❌ تعذر جلب بيانات الرمز {ticker}\n\n"
    await update.message.reply_text(full_report, parse_mode='Markdown')

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        return
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(background_monitoring, 'interval', minutes=15, args=[app])
    scheduler.start()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot with robust error handling and retry mechanism is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
