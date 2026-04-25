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
TOKEN = "0xec9742f992ACc615C4252060D896c845ca8fC086"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
def send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram no configurado")
        return

    try:
        session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🟢 1. GECKOTERMINAL (PRINCIPAL)
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
# 🟡 2. WEB3 FALLBACK (V2 SIMPLE)
# =========================
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

def price_web3():
    try:
        abi = [
            {
                "name": "getReserves",
                "outputs": [{"type": "uint112"}, {"type": "uint112"}, {"type": "uint32"}],
                "inputs": [],
                "stateMutability": "view",
                "type": "function"
            }
        ]

        contract = bsc.eth.contract(address=POOL, abi=abi)
        r0, r1, _ = contract.functions.getReserves().call()

        if r0 == 0 or r1 == 0:
            return None

        return r1 / r0

    except Exception as e:
        print("WEB3 FAIL:", repr(e))
        return None

# =========================
# 💰 PRICE ENGINE (HÍBRIDO)
# =========================
def get_price():
    price = price_gecko()

    if price:
        return price

    # fallback
    price = price_web3()

    return price

# =========================
# 🤖 TELEGRAM LOOP
# =========================
last_price = None
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
            text = msg.get("text", "")

            if text == "/precio":
                price = get_price()

                if price:
                    send(f"💰 PRECIO REAL:\n${price:.6f}")
                else:
                    send("⚠️ No se pudo obtener precio")

            elif text == "/status":
                send("✅ Bot híbrido funcionando")

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🔁 LOOP PRINCIPAL
# =========================
def bot_loop():
    global last_price

    print("🚀 Hybrid bot definitivo iniciado")

    while True:
        try:
            check_messages()

            price = get_price()

            if price is None:
                time.sleep(5)
                continue

            if last_price is None:
                last_price = price

            if price > last_price * 1.001:
                send(f"🚀 SUBIÓ\n💰 ${price}")
                last_price = price

            elif price < last_price * 0.999:
                send(f"📉 BAJÓ\n💰 ${price}")
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
