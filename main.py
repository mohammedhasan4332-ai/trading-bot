import os
import sys
import time
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

print(">>> [1/3] Starting script...", flush=True)

BOT_TOKEN = "8934348047:AAFXG8pcMiR4_94JZJu-EzTk3JwerkhR9xQ"
CHAT_ID = "8961115746"

PAIRS = {
    "EUR/USD OTC": "EURUSD=X",
    "EUR/CHF OTC": "EURCHF=X",
    "CAD/CHF OTC": "CADCHF=X",
    "AUD/CAD OTC": "AUDCAD=X"
}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        time.sleep(2)
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)

def get_candles_5m(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=5d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            return [c for c in closes if c is not None]
    except Exception:
        pass
    return []

def calculate_ema(prices, period=50):
    if len(prices) < period: return None
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0 and avg_gain == 0: return 50
    if avg_loss == 0: return 100
    if avg_gain == 0: return 0
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

def calculate_bollinger(prices, period=20, mult=2):
    if len(prices) < period: return None, None
    sub = prices[-period:]
    sma = sum(sub) / period
    variance = sum((x - sma) ** 2 for x in sub) / period
    std = variance ** 0.5
    return sma + (mult * std), sma - (mult * std)

def evaluate_trade(pair_name, ticker, direction, entry_price):
    time.sleep(10 * 60)
    prices = get_candles_5m(ticker)
    if not prices: return
    exit_price = prices[-1]
    won = False
    
    if direction == "CALL" and exit_price > entry_price: won = True
    elif direction == "PUT" and exit_price < entry_price: won = True
        
    if won:
        send_telegram(f"✅ **تحديث النتيجة: ربح!**\nصفقة {pair_name} التي دخلتها قبل 10 دقائق انتهت بنجاح.")
    else:
        send_telegram(f"❌ **تحديث النتيجة: خسارة.**\nعكس السوق في صفقة {pair_name}.")

def bot_loop():
    time.sleep(5)
    print(">>> [2/3] Bot loop started, sending start message...", flush=True)
    send_telegram("🚀 **تم تشغيل البوت بنجاح على سيرفر Render السحابي!**\n(يعمل الآن 24/7 باستقرار تام - شموع 5د، صفقات 10د)")
    last_alerts = {}

    while True:
        for name, ticker in PAIRS.items():
            try:
                prices = get_candles_5m(ticker)
                if len(prices) < 55:
                    continue
                
                rsi = calculate_rsi(prices, period=14)
                upper, lower = calculate_bollinger(prices, period=20, mult=2)
                ema_50 = calculate_ema(prices, period=50)
                last_price = prices[-1]
                
                now = time.time()
                if name in last_alerts and now - last_alerts[name] < 900:
                    continue
                
                target_time = (datetime.now() + timedelta(minutes=1)).strftime("%H:%M:00")
                
                if lower and ema_50 and last_price <= lower and rsi <= 30 and last_price >= ema_50 * 0.995:
                    send_telegram(f"⏳ **تنبيه صفقة ذهبية (استعد!)**\n\n📊 الزوج: {name}\n🎯 الصفقة: 🟢 **شراء / صعود (CALL)**\n⏰ وقت الدخول: تمام الساعة **{target_time}**\n⏳ المدة: **10 دقائق**\n\n👉 جهز المنصة وانتظر إشارة التأكيد!")
                    time.sleep(45)
                    send_telegram(f"🚀 **ادخل الآن فوراً!**\n📊 الزوج: {name}\n🎯 الإجراء: 🟢 **شراء**\n⏱ المدة: **10 دقائق**")
                    last_alerts[name] = time.time()
                    threading.Thread(target=evaluate_trade, args=(name, ticker, "CALL", last_price)).start()

                elif upper and ema_50 and last_price >= upper and rsi >= 70 and last_price <= ema_50 * 1.005:
                    send_telegram(f"⏳ **تنبيه صفقة ذهبية (استعد!)**\n\n📊 الزوج: {name}\n🎯 الصفقة: 🔴 **بيع / هبوط (PUT)**\n⏰ وقت الدخول: تمام الساعة **{target_time}**\n⏳ المدة: **10 دقائق**\n\n👉 جهز المنصة وانتظر إشارة التأكيد!")
                    time.sleep(45)
                    send_telegram(f"🚀 **ادخل الآن فوراً!**\n📊 الزوج: {name}\n🎯 الإجراء: 🔴 **بيع**\n⏱ المدة: **10 دقائق**")
                    last_alerts[name] = time.time()
                    threading.Thread(target=evaluate_trade, args=(name, ticker, "PUT", last_price)).start()

            except Exception as e:
                print(f"Error checking {name}: {e}", flush=True)
            time.sleep(10)

        time.sleep(45)

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 8080))
    print(f">>> [3/3] Web server running on port {port}...", flush=True)
    server = HTTPServer(("0.0.0.0", port), HealthCheckServer)
    server.serve_forever()
