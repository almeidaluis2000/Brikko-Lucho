import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# 🔗 RPC
# =========================
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# =========================
# 🔥 TOKENS (TU LINK)
# =========================
TOKEN_IN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
TOKEN_OUT = Web3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")  # USDT

# PancakeSwap V3 Quoter (BSC oficial)
QUOTER = Web3.to_checksum_address("0x78D78E420Da98ad378D7799bE8f4AF69033EB077")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# 🌐 FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "V3 swap bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# 🌐 SESSION
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
        print("Telegram error:", repr(e))

# =========================
# 📡 QUOTER ABI
# =========================
quoter_abi = [
    {
        "name": "quoteExactInputSingle",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"type": "address"},
            {"type": "address"},
            {"type": "uint24"},
            {"type": "uint256"},
            {"type": "uint160"}
        ],
        "outputs": [{"type": "uint256"}]
    }
]

quoter = bsc.eth.contract(address=QUOTER, abi=quoter_abi)

# =========================
# 💥 AUTO FEE INTELIGENTE
# =========================
FEES = [500, 3000, 10000]
FEE_CACHE = None

def detect_fee():
    global FEE_CACHE

    if FEE_CACHE:
        return FEE_CACHE

    amount_in = 10**18

    for fee in FEES:
        try:
            out = quoter.functions.quoteExactInputSingle(
                TOKEN_IN,
                TOKEN_OUT,
                fee,
                amount_in,
                0
            ).call()

            if out > 0:
                FEE_CACHE = fee
                print(f"✅ Fee detectado: {fee}")
                return fee

        except Exception:
            continue

    return None

# =========================
# 💰 PRECIO REAL SWAP
# =========================
def get_price():
    try:
        fee = detect_fee()

        if not fee:
            return None

        amount_in = 10**18

        amount_out = quoter.functions.quoteExactInputSingle(
            TOKEN_IN,
            TOKEN_OUT,
            fee,
            amount_in,
            0
        ).call()

        price = amount_out / amount_in
        return price

    except Exception as e:
        print("❌ PRICE ERROR:", repr(e))
        return None

# =========================
# 🤖 LOOP TELEGRAM
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
                    send_telegram(f"💰 PRECIO REAL SWAP V3:\n{price:.6f} USDT", chat_id)
                else:
                    send_telegram("❌ No se pudo obtener precio (pool sin ruta directa)", chat_id)

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🔁 LOOP
# =========================
def bot_loop():
    print("🚀 Bot V3 real iniciado")

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
