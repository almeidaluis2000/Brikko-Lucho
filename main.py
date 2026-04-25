import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# CONFIG
# =========================
POOL = "0x7e4259eaac5ca2bc855c728e162d4d7782e52b7b"

BOT_TOKEN = os.getenv("BOT_TOKEN")

session = requests.Session()

# =========================
# FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Hybrid bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# TELEGRAM
# =========================
def send(msg, chat_id):
    try:
        session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🟢 GECKO (PRINCIPAL)
# =========================
def price_gecko():
    try:
        url = f"https://api.geckoterminal.com/api/v2/networks/bsc/pools/{POOL}"
        r = session.get(url, timeout=10).json()

        price = r["data"]["attributes"]["base_token_price_usd"]
        return float(price)

    except Exception as e:
        print("GECKO FAIL:", repr(e))
        return None

# =========================
# 💰 PRICE ENGINE
# =========================
def get_price():
    return price_gecko()

# =========================
# 🤖 TELEGRAM LOOP
# =========================
last_update_id = 0

def check_messages():
    global last_update_id

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=10"

        if last_update_id:
            url += f"&offset={last_update_id + 1}"

        data = session.get(url, timeout=15).json()

        for update in data.get("result", []):
            last_update_id = update["update_id"]

            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            text = msg.get("text", "").lower()

            # =========================
            # COMANDOS
            # =========================
            if text == "/start":
                send("🤖 Bot activo\n\nUsa:\n/precio\n/status", chat_id)

            elif text == "/status":
                send("✅ Bot funcionando correctamente", chat_id)

            elif text == "/precio":
                price = get_price()

                if price:
                    send(f"💰 PRECIO ACTUAL:\n${price:.6f}", chat_id)
                else:
                    send("⚠️ No se pudo obtener precio", chat_id)

            else:
                send("❓ Comando no reconocido", chat_id)

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# LOOP
# =========================
def bot_loop():
    global last_price

    print("🚀 Bot final sin duplicados iniciado")

    while True:
        try:
            check_messages()

            price = get_price()

            if price is None:
                time.sleep(5)
                continue

            if last_price is None:
                last_price = price
                time.sleep(5)
                continue

            # 🔥 SOLO ALERTAS REALES (no spam)
            if price > last_price * 1.01:
                send(f"🚀 SUBIÓ\n💰 ${price:.6f}", CHAT_ID)
                last_price = price

            elif price < last_price * 0.99:
                send(f"📉 BAJÓ\n💰 ${price:.6f}", CHAT_ID)
                last_price = price

            time.sleep(5)

        except Exception as e:
            print("Loop error:", repr(e))
            time.sleep(10)

# =========================
# START
# =========================
threading.Thread(target=bot_loop, daemon=True).start()
run_web()
