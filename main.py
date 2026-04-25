import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# 🔗 BSC RPC
# =========================
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# =========================
# 🔥 POOL (GeckoTerminal)
# =========================
POOL = Web3.to_checksum_address("0x7e4259eaac5ca2bc855c728e162d4d7782e52b7b")

# TU TOKEN
TOKEN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")

# =========================
# ⚙️ CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STEP_UP = 0.1
STEP_DOWN = 0.1

# =========================
# 🌐 FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "GeckoTerminal bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

session = requests.Session()

# =========================
# 📲 TELEGRAM
# =========================
def send_telegram(msg, chat_id=CHAT_ID):
    try:
        session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 📡 POOL ABI (Uniswap V2 style)
# =========================
abi = [
    {
        "name": "getReserves",
        "outputs": [
            {"type": "uint112"},
            {"type": "uint112"},
            {"type": "uint32"}
        ],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "name": "token0",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

pool = bsc.eth.contract(address=POOL, abi=abi)

# =========================
# 💰 PRECIO REAL (GECKO STYLE)
# =========================
def get_price():
    try:
        reserves = pool.functions.getReserves().call()
        token0 = pool.functions.token0().call()

        r0 = reserves[0]
        r1 = reserves[1]

        if r0 == 0 or r1 == 0:
            return None

        # precio estilo AMM
        if token0.lower() == TOKEN.lower():
            price = r1 / r0
        else:
            price = r0 / r1

        return price

    except Exception as e:
        print("❌ POOL ERROR:", repr(e))
        return None

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
            text = msg.get("text", "")

            if text == "/precio":
                price = get_price()

                if price:
                    send_telegram(f"💰 PRECIO POOL REAL:\n${price:.6f}", chat_id)
                else:
                    send_telegram("❌ No hay liquidez en el pool", chat_id)

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🔁 LOOP PRINCIPAL
# =========================
last_price = None

def bot_loop():
    global last_price

    print("🚀 Bot GeckoTerminal iniciado")

    while True:
        try:
            check_messages()

            price = get_price()
            if price is None:
                time.sleep(5)
                continue

            if last_price is None:
                last_price = price

            if price >= last_price + STEP_UP:
                send_telegram(f"🚀 SUBIÓ\n💰 ${price}")
                last_price = price

            elif price <= last_price - STEP_DOWN:
                send_telegram(f"📉 BAJÓ\n💰 ${price}")
                last_price = price

            time.sleep(5)

        except Exception as e:
            print("Loop error:", repr(e))
            time.sleep(10)

# =========================
# 🚀 START
# =========================
threading.Thread(target=bot_loop, daemon=True).start()
run_web()
