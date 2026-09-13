import time
import requests

# ضع التوكن الخاص ببوتك الجديد هنا بين علامتي التنصيص
TOKEN = 'ضع_التوكن_هنا'
CHAT_ID = '1127310227'


def send_telegram_alert(message):
  url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
  payload = {'chat_id': CHAT_ID, 'text': message}
  try:
    response = requests.post(url, json=payload)
    return response.json()
  except Exception as e:
    print(f'خطأ في إرسال التنبيه: {e}')


def check_ichimoku_breakout_15m(df):
  df['Tenkan_sen'] = (
      df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()
  ) / 2
  df['Kijun_sen'] = (
      df['High'].rolling(window=26).max() + df['Low'].rolling(window=26).min()
  ) / 2
  df['Senkou_Span_A'] = (
      (df['Tenkan_sen'] + df['Kijun_sen']) / 2
  ).shift(26)
  df['Senkou_Span_B'] = (
      (df['High'].rolling(window=52).max() + df['Low'].rolling(window=52).min())
      / 2
  ).shift(26)
  df['Volume_SMA'] = df['Volume'].rolling(20).mean()

  last = df.iloc[-1]
  prev = df.iloc[-2]

  upper_cloud = max(last['Senkou_Span_A'], last['Senkou_Span_B'])
  is_vol_spike = last['Volume'] > (1.5 * last['Volume_SMA'])
  is_breaking_out = prev['Close'] <= upper_cloud and last['Close'] > upper_cloud

  if is_breaking_out and is_vol_spike:
    alert_msg = (
        '🚨 تنبيه إشيميكو انفجاري (البوت الثاني):\nتم رصد اختراق ناجح على'
        ' فريم 15 دقيقة مع سيولة عالية.'
    )
    send_telegram_alert(alert_msg)
    return True

  return False
