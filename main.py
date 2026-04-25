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
# 🔥 POOL REAL V3
# =========================
POOL = Web3.to_checksum_address("0x7E4259eAAc5CA2Bc855C728e162d4d7782E52b7Bec")

# =========================
# ⚙️ CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# 🌐 FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "V3 slot0 bot activo"

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
# 📡 ABI V3 POOL
# =========================
abi = [
    {
        "name": "slot0",
        "outputs": [
            {"type": "uint160"},
            {"type": "int24"},
            {"type": "uint16"},
            {"type": "uint16"},
            {"type": "uint16"},
            {"type": "uint8"},
            {"type": "bool"}
        ],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

pool = bsc.eth.contract(address=POOL, abi=abi)

# =========================
# 💰 PRECIO REAL V3 (CORRECTO)
# =========================
def get_price():
    try:
        slot0 = pool.functions.slot0().call()
        sqrtPriceX96 = slot0[0]

        # fórmula Uniswap V3 real
        price = (sqrtPriceX96 / (2**96)) ** 2

        return price

    except Exception as e:
        print("❌ SLOT0 ERROR:", repr(e))
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
                    send_telegram(f"💰 PRECIO V3 REAL:\n{price:.8f}", chat_id)
                else:
                    send_telegram("❌ Pool sin datos slot0", chat_id)

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🔁 LOOP
# =========================
def bot_loop():
    print("🚀 V3 slot0 bot iniciado")

    while True:
        try:
            check_messages()
            time.sleep(5)

        except Exception as e:
            print("Loop error:", repr(e))
            time.sleep(10)

# =========================
# 🚀 START
# =========================
threading.Thread(target=bot_loop, daemon=True).start()
run_web()
