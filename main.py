import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# 🔗 BSC
# =========================
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# =========================
# 🔥 TOKENS
# =========================
TOKEN_IN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
TOKEN_OUT = Web3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")

# PancakeSwap V3 Router (NO QUOTER)
ROUTER = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# 🌐 FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Router bot activo"

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
# 📡 ABI MINIMAL ROUTER
# =========================
router_abi = [
    {
        "name": "getAmountsOut",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"type": "uint256"},
            {"type": "address[]"}
        ],
        "outputs": [{"type": "uint256[]"}]
    }
]

router = bsc.eth.contract(address=ROUTER, abi=router_abi)

# =========================
# 💰 PRECIO REAL (MULTI-HOP REAL)
# =========================
def get_price():
    try:
        amount_in = 10**18

        path = [
            TOKEN_IN,
            TOKEN_OUT
        ]

        amounts = router.functions.getAmountsOut(amount_in, path).call()

        price = amounts[-1] / amount_in
        return price

    except Exception as e:
        print("❌ ROUTE ERROR:", repr(e))
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
                    send_telegram(f"💰 PRECIO REAL (ROUTER):\n{price:.6f} USDT", chat_id)
                else:
                    send_telegram("❌ No hay ruta disponible", chat_id)

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🔁 LOOP
# =========================
def bot_loop():
    print("🚀 Router bot iniciado")

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
