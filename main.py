import os
import time
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

BOT_TOKEN = "8934348047:AAFXG8pcMiR4_94JZJu-EzTk3JwerkhR9xQ"
CHAT_ID = "8961115746"

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "EUR/CHF": "EURCHF=X",
    "CAD/CHF": "CADCHF=X",
    "AUD/CAD": "AUDCAD=X"
}

def send_telegram(msg, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)

def get_candles_5m(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=2d"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            return [c for c in closes if c is not None]
    except Exception:
        pass
    return []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calculate_bollinger(prices, period=20, mult=1.8):
    if len(prices) < period:
        return None, None, None
    sub = prices[-period:]
    sma = sum(sub) / period
    variance = sum((x - sma) ** 2 for x in sub) / period
    std = variance ** 0.5
    return sma + (mult * std), sma, sma - (mult * std)

def build_market_report():
    lines = ["📊 **تقرير السوق المباشر الآن:**\n"]
    for name, ticker in PAIRS.items():
        prices = get_candles_5m(ticker)
        if len(prices) >= 25:
            rsi = calculate_rsi(prices)
            last_p = round(prices[-1], 5)
            status = "🟢 تشبع بيعي (قريب من صعود)" if rsi <= 35 else ("🔴 تشبع شرائي (قريب من هبوط)" if rsi >= 65 else "⚪ مستقر")
            lines.append(f"▪️ **{name}**: السعر `{last_p}` | RSI: `{rsi}` ({status})")
        else:
            lines.append(f"▪️ **{name}**: جاري جلب البيانات...")
    lines.append("\n✅ البوت يعمل بنشاط ويراقب الصفقات 24/7.")
    return "\n".join(lines)

def evaluate_trade(pair_name, ticker, direction, entry_price):
    time.sleep(10 * 60)
    prices = get_candles_5m(ticker)
    if not prices:
        return
    exit_price = prices[-1]
    won = (direction == "CALL" and exit_price > entry_price) or (direction == "PUT" and exit_price < entry_price)
    if won:
        send_telegram(f"✅ **نتيجة الصفقة: ربح ناجح!**\n📊 الزوج: {pair_name}\nسعر الدخول: {round(entry_price, 5)} | الإغلاق: {round(exit_price, 5)}")
    else:
        send_telegram(f"❌ **نتيجة الصفقة: انتهت بانعكاس.**\n📊 الزوج: {pair_name}\nسعر الدخول: {round(entry_price, 5)} | الإغلاق: {round(exit_price, 5)}")

# 1. نظام الرد الفوري على رسائلك في تليجرام
def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            res = requests.get(url, timeout=25).json()
            if res.get("ok"):
                for item in res.get("result", []):
                    offset = item["update_id"] + 1
                    msg = item.get("message", {})
                    text = msg.get("text", "")
                    sender_id = str(msg.get("chat", {}).get("id", CHAT_ID))
                    if text:
                        send_telegram("⏳ جاري فحص الأزواج وجلب الأسعار اللحظية...", sender_id)
                        report = build_market_report()
                        send_telegram(report, sender_id)
        except Exception:
            time.sleep(5)

# 2. نظام منع النوم التلقائي لسيرفر Render
def keep_alive_ping():
    time.sleep(15)
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    port = os.environ.get("PORT", "8080")
    while True:
        try:
            if external_url:
                requests.get(external_url, timeout=10)
            requests.get(f"http://127.0.0.1:{port}", timeout=5)
            print(">>> Ping sent to keep server awake.", flush=True)
        except Exception:
            pass
        time.sleep(240)  # ينبه السيرفر كل 4 دقائق

# 3. محرك فحص الصفقات والتقارير الدورية
def bot_loop():
    time.sleep(3)
    startup_msg = (
        "🚀 **تم تشغيل النسخة الذكية من البوت بنجاح (24/7)!**\n\n"
        "💡 **مميزات البوت الآن:**\n"
        "1️⃣ منبه ذاتي يمنع السيرفر من التوقف.\n"
        "2️⃣ أرسل أي كلمة هنا (مثل: `فحص`) وسيرد عليك البوت فوراً بأسعار السوق.\n"
        "3️⃣ يرسل لك تقرير فحص تلقائي كل 30 دقيقة + تنبيهات الصفقات المباشرة."
    )
    send_telegram(startup_msg)
    send_telegram(build_market_report())

    last_alerts = {}
    last_heartbeat = time.time()

    while True:
        now = time.time()
        # إرسال تقرير نبض كل 30 دقيقة (1800 ثانية)
        if now - last_heartbeat >= 1800:
            send_telegram("🔄 **تقرير النبض الدوري (كل 30 دقيقة):**\n" + build_market_report())
            last_heartbeat = now

        for name, ticker in PAIRS.items():
            try:
                prices = get_candles_5m(ticker)
                if len(prices) < 25:
                    continue

                rsi = calculate_rsi(prices, period=14)
                upper, mid, lower = calculate_bollinger(prices, period=20, mult=1.8)
                last_price = prices[-1]

                if name in last_alerts and time.time() - last_alerts[name] < 600:
                    continue

                target_time = (datetime.now() + timedelta(minutes=1)).strftime("%H:%M:00")

                # شروط صفقة شراء (CALL)
                if lower and ((last_price <= lower and rsi <= 38) or rsi <= 28):
                    send_telegram(
                        f"⏳ **إشارة صفقة جديدة (استعد!)**\n\n"
                        f"📊 الزوج: **{name}**\n"
                        f"🎯 الاتجاه: 🟢 **شراء / صعود (CALL)**\n"
                        f"📉 مؤشر RSI الحالي: `{rsi}`\n"
                        f"⏰ وقت الدخول: **{target_time}**\n"
                        f"⏱ المدة: **10 دقائق**"
                    )
                    time.sleep(40)
                    send_telegram(f"🚀 **ادخل الآن فوراً!**\n📊 الزوج: **{name}**\n🎯 الإجراء: 🟢 **شراء (CALL)**\n💰 السعر الحالي: `{round(last_price, 5)}`")
                    last_alerts[name] = time.time()
                    threading.Thread(target=evaluate_trade, args=(name, ticker, "CALL", last_price), daemon=True).start()

                # شروط صفقة بيع (PUT)
                elif upper and ((last_price >= upper and rsi >= 62) or rsi >= 72):
                    send_telegram(
                        f"⏳ **إشارة صفقة جديدة (استعد!)**\n\n"
                        f"📊 الزوج: **{name}**\n"
                        f"🎯 الاتجاه: 🔴 **بيع / هبوط (PUT)**\n"
                        f"📈 مؤشر RSI الحالي: `{rsi}`\n"
                        f"⏰ وقت الدخول: **{target_time}**\n"
                        f"⏱ المدة: **10 دقائق**"
                    )
                    time.sleep(40)
                    send_telegram(f"🚀 **ادخل الآن فوراً!**\n📊 الزوج: **{name}**\n🎯 الإجراء: 🔴 **بيع (PUT)**\n💰 السعر الحالي: `{round(last_price, 5)}`")
                    last_alerts[name] = time.time()
                    threading.Thread(target=evaluate_trade, args=(name, ticker, "PUT", last_price), daemon=True).start()

            except Exception as e:
                print(f"Scan error on {name}: {e}", flush=True)
            time.sleep(4)

        time.sleep(25)

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    threading.Thread(target=bot_loop, daemon=True).start()

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckServer)
    server.serve_forever()
