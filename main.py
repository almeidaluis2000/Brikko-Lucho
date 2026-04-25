import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# 🔗 RPC BSC
# =========================
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# =========================
# 🔥 CONFIG
# =========================
TOKEN_IN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
TOKEN_OUT = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")  # WBNB

# PancakeSwap V3 Quoter (BSC)
QUOTER = Web3.to_checksum_address("0x7e4259eaac5ca2bc855c728e162d4d7782e52b7b")

FEE = 3000  # 0.3% (ajusta si tu pool es otro: 500 / 3000 / 10000)

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
    return "Quoter V3 Bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# 🌐 HTTP SESSION
# =========================
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
        print("Telegram error:", e)

# =========================
# 📡 QUOTER ABI
# =========================
quoter_abi = [
    {
        "name": "quoteExactInputSingle",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"}
        ],
        "outputs": [{"name": "amountOut", "type": "uint256"}]
    }
]

quoter = bsc.eth.contract(address=QUOTER, abi=quoter_abi)

# =========================
# 💰 REAL SWAP PRICE (QUOTER)
# =========================
def get_price(amount_in=10**18):
    try:
        amount_out = quoter.functions.quoteExactInputSingle(
            TOKEN_IN,
            TOKEN_OUT,
            FEE,
            amount_in,
            0
        ).call()

        price = amount_out / amount_in
        return price

    except Exception as e:
        print("❌ QUOTER ERROR:", repr(e))
        return None

# =========================
# 🤖 TELEGRAM COMMANDS
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

            if text == "/start":
                send_telegram("🤖 Quoter V3 Bot activo", chat_id)

            elif text == "/precio":
                price = get_price()
                if price:
                    send_telegram(f"💰 Swap price: {price:.8f}", chat_id)
                else:
                    send_telegram("⚠️ Error precio", chat_id)

            elif text == "/status":
                send_telegram("✅ OK", chat_id)

    except Exception as e:
        print("Telegram error:", e)

# =========================
# 🔁 LOOP
# =========================
last_price = None

def bot_loop():
    global last_price

    print("🚀 Quoter V3 Bot iniciado")

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
                send_telegram(f"🚀 SUBIÓ SWAP PRICE\n💰 {price}")
                last_price = price

            elif price <= last_price - STEP_DOWN:
                send_telegram(f"📉 BAJÓ SWAP PRICE\n💰 {price}")
                last_price = price

            time.sleep(5)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(10)

# =========================
# 🚀 START
# =========================
threading.Thread(target=bot_loop, daemon=True).start()
run_web()
