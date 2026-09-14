import os
import time
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from collections import defaultdict

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

TICKER = "I:SPX"  # مؤشر SPX عند Polygon
COOLDOWN = 45 * 60
ADX_MIN = 25
last_sent = defaultdict(float)

TIMEFRAMES = {
    "week":  {"mult": 1, "span": "week", "days": 800, "name": "أسبوعي"},
    "day":   {"mult": 1, "span": "day",  "days": 400, "name": "يومي"},
    "hour4": {"mult": 4, "span": "hour", "days": 180, "name": "4 ساعات"},
    "hour":  {"mult": 1, "span": "hour", "days": 90,  "name": "ساعة"},
}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)

def fetch_candles(tf):
    end = datetime.utcnow().date()
    start = end - timedelta(days=tf["days"])
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{TICKER}"
        f"/range/{tf['mult']}/{tf['span']}/{start}/{end}"
        f"?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_API_KEY}"
    )
    res = requests.get(url, timeout=20).json()
    results = res.get("results") or []
    df = pd.DataFrame(results)
    if df.empty:
        return None
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df

def classify_kumo(span_a, span_b, close):
    thick = abs(span_a - span_b)
    pct = (thick / close) * 100 if close else 0
    if pct < 0.25:
        level = "رفيعة"
    elif pct < 0.60:
        level = "متوسطة"
    else:
        level = "سميكة"
    color = "خضراء" if span_a > span_b else "حمراء"
    return thick, pct, level, color

def analyze(tf_key, tf):
    df = fetch_candles(tf)
    if df is None or len(df) < 70:
        return None

    ichi = ta.ichimoku(df["high"], df["low"], df["close"])
    df = pd.concat([df, ichi[0]], axis=1)
    df = pd.concat([df, ta.stochrsi(df["close"], length=14, rsi_length=14, k=3, d=3)], axis=1)
    df = pd.concat([df, ta.adx(df["high"], df["low"], df["close"], length=14)], axis=1)
    df = pd.concat([df, ta.atr(df["high"], df["low"], df["close"], length=14)], axis=1)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = float(last["close"])
    tenkan = float(last.get("ITS_9", 0))
    kijun = float(last.get("IKS_26", 0))
    span_a = float(last.get("ISA_9", 0))
    span_b = float(last.get("ISB_26", 0))
    chikou = float(last.get("ICS_26", close))
    k = float(last.get("STOCHRSIk_14_14_3_3", 50))
    d = float(last.get("STOCHRSId_14_14_3_3", 50))
    prev_k = float(prev.get("STOCHRSIk_14_14_3_3", 50))
    prev_d = float(prev.get("STOCHRSId_14_14_3_3", 50))
    adx = float(last.get("ADX_14", 0))
    atr = float(last.get("ATRr_14", 0))

    cloud_top = max(span_a, span_b)
    cloud_bot = min(span_a, span_b)
    thick, thick_pct, thick_level, color = classify_kumo(span_a, span_b, close)

    above = close > cloud_top
    below = close < cloud_bot
    inside = cloud_bot <= close <= cloud_top

    if above:
        dist = ((close - cloud_top) / cloud_top) * 100
    elif below:
        dist = ((cloud_bot - close) / cloud_bot) * 100
    else:
        dist = 0

    near_from_below = below and dist < 0.40
    near_from_above = above and dist < 0.40
    cross_up = prev_k <= prev_d and k > d
    cross_down = prev_k >= prev_d and k < d
    strong_move = atr > 0 and abs(close - float(prev["close"])) >= (0.6 * atr)
    thick_ok = thick_level in ["متوسطة", "سميكة"]

    name = tf["name"]

    if near_from_below and k < 30 and adx > 18:
        return ("early_buy", name,
                f"🟡 مبكر | شراء\n{name} | {close:.2f}\nيقترب من سحابة {color} {thick_level}\nيبعد {dist:.2f}% | StochRSI {k:.1f}")

    if near_from_above and k > 70 and adx > 18:
        return ("early_sell", name,
                f"🟡 مبكر | بيع\n{name} | {close:.2f}\nيقترب من سحابة {color} {thick_level}\nيبعد {dist:.2f}% | StochRSI {k:.1f}")

    if above and tenkan > kijun and k < 32 and cross_up and adx >= ADX_MIN and thick_ok and strong_move:
        strength = "قوية جداً" if thick_level == "سميكة" and k < 22 else "قوية"
        return ("buy", name,
                f"🟢 حركة {strength} | شراء\n{name} | {close:.2f} فوق سحابة {color} {thick_level}\nتينكان {tenkan:.0f} | كيجون {kijun:.0f} | تشيكو {chikou:.0f}\nStochRSI {k:.1f} | ADX {adx:.1f}")

    if below and tenkan < kijun and k > 68 and cross_down and adx >= ADX_MIN and thick_ok and strong_move:
        strength = "قوية جداً" if thick_level == "سميكة" and k > 78 else "قوية"
        return ("sell", name,
                f"🔴 حركة {strength} | بيع\n{name} | {close:.2f} تحت سحابة {color} {thick_level}\nتينكان {tenkan:.0f} | كيجون {kijun:.0f} | تشيكو {chikou:.0f}\nStochRSI {k:.1f} | ADX {adx:.1f}")

    if inside and thick_level == "سميكة" and adx > 25:
        return ("wait", name, f"⚪ انتظار | {name}\n{close:.2f} داخل سحابة سميكة")

    return None

def can_send(key):
    now = time.time()
    if now - last_sent[key] < COOLDOWN:
        return False
    last_sent[key] = now
    return True

def main():
    send_telegram("🚀 رصد SPX شغال\nتنبيه مبكر + حركة قوية")
    while True:
        early, buys, sells, waits = [], [], [], []

        for key, tf in TIMEFRAMES.items():
            try:
                result = analyze(key, tf)
                if not result:
                    continue
                typ, name, msg = result
                if typ.startswith("early"):
                    early.append(msg)
                elif typ == "buy":
                    buys.append((key, msg))
                elif typ == "sell":
                    sells.append((key, msg))
                else:
                    waits.append(msg)
            except Exception as e:
                print("خطأ", key, e)
            time.sleep(1)

        parts = []
        for msg in early:
            if can_send("early:" + msg[:20]):
                parts.append(msg)

        if len(buys) >= 2 and can_send("buy"):
            parts.append(f"🟢 تأكيد شراء من {len(buys)} فريمات")
            parts.extend(m for _, m in buys)

        if len(sells) >= 2 and can_send("sell"):
            parts.append(f"🔴 تأكيد بيع من {len(sells)} فريمات")
            parts.extend(m for _, m in sells)

        for msg in waits:
            if can_send("wait:" + msg[:20]):
                parts.append(msg)

        if parts:
            text = "رصد SPX\n\n" + "\n\n".join(parts)
            text += f"\n\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            send_telegram(text)
            print("تم إرسال تنبيه")
        else:
            print(datetime.now().strftime("%H:%M"), "لا توجد حركة قوية")

        time.sleep(8 * 60)

if __name__ == "__main__":
    main()
