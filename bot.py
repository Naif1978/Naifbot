import logging
import os
from datetime import datetime
import pandas as pd
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WATCHLIST = ['^SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']

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

def analyze_ichimoku(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="5d", interval="15m")
        
        if df.empty or len(df) < 52:
            return f"❌ عذراً، البيانات غير كافية للرمز: {ticker_symbol.upper()}"
            
        df['Tenkan'] = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
        df['Kijun'] = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
        df['Senkou_A'] = ((df['Tenkan'] + df['Kijun']) / 2).shift(26)
        df['Senkou_B'] = ((df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2).shift(26)
        
        last = df.iloc[-1]
        price, tenkan, kijun = last['Close'], last['Tenkan'], last['Kijun']
        sa, sb = last['Senkou_A'], last['Senkou_B']
        poc, v_min, v_max = calculate_volume_profile(df)
        
        is_weekend = datetime.utcnow().weekday() >= 5
        market_status = "🔴 السوق مغلق (عطلة نهاية الأسبوع)" if is_weekend else "🟢 السوق مفتوح"
        
        trend_status = "neutral"
        cloud_desc = "داخل السحابة (تذبذب)"
        if pd.notna(sa) and pd.notna(sb):
            upper_c, lower_c = max(sa, sb), min(sa, sb)
            if price > upper_c and tenkan > kijun:
                trend_status = "bullish"
                cloud_desc = "فوق السحابة + تقاطع إيجابي 🟢"
            elif price < lower_c and tenkan < kijun:
                trend_status = "bearish"
                cloud_desc = "تحت السحابة + تقاطع سلبي 🔴"
                
        signal_emoji = "🟢 إيجابية (صاعد)" if trend_status == "bullish" else ("🔴 سلبية (هابط)" if trend_status == "bearish" else "🟡 حيادية")
        
        report = f"""📊 **{ticker_symbol.upper()}** | {market_status}
-----------------------------------
⚖️ **الحالة:** {signal_emoji}
• **السعر:** {price:.2f} | **السحابة:** {cloud_desc}
• **التينكان:** {tenkan:.2f} | **الكيجون:** {kijun:.2f}
• **نقطة السيولة (POC):** {poc} (النطاق: {v_min} - {v_max})
"""
        return report
    except Exception as e:
        logger.error(f"Error analyzing {ticker_symbol}: {e}")
        return f"حدث خطأ أثناء معالجة الرمز {ticker_symbol}."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    await update.message.reply_text("⏳ جاري فحص السحابة والسيولة...")
    result = analyze_ichimoku(text)
    await update.message.reply_text(result, parse_mode='Markdown')

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري فحص قائمة الأسهم القيادية والمؤشرات...")
    full_report = "📈 **ملخص الأسهم القيادية والمؤشرات:**\n\n"
    for ticker in WATCHLIST:
        full_report += analyze_ichimoku(ticker) + "\n"
    await update.message.reply_text(full_report, parse_mode='Markdown')

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        return
        
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
