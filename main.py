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
# 🔥 CONFIG
# =========================
TOKEN_IN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
TOKEN_OUT = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")

QUOTER = Web3.to_checksum_address("0x78D78E420Da98ad378D7799bE8f4AF69033EB077")

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
    return "V3 AutoFee Bot activo"

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
# 💥 AUTO FEE DETECTION (CLAVE)
# =========================
FEE_CACHE = None

FEES = [500, 3000, 10000]

def detect_fee():
    global FEE_CACHE

    if FEE_CACHE:
        return FEE_CACHE

    amount_in = 10**18  # 1 token base

    print("🔍 Detectando fee V3...")

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

        except Exception as e:
            print(f"❌ fee {fee} failed:", repr(e))
            continue

    print("❌ No se pudo detectar fee")
    return None

# =========================
# 💰 PRECIO REAL SWAP V3
# =========================
def get_price():
    try:
        print("🔥 TEST QUOTER")

        fee = 3000

        result = quoter.functions.quoteExactInputSingle(
            TOKEN_IN,
            TOKEN_OUT,
            fee,
            10**18,
            0
        ).call()

        print("AMOUNT OUT:", result)

        return result / 10**18

    except Exception as e:
        print("❌ REAL ERROR:", repr(e))
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

            if text == "/start":
                send_telegram("🤖 V3 AutoFee Bot activo", chat_id)

            elif text == "/precio":
                price = get_price()
                if price:
                    send_telegram(f"💰 Swap V3: {price:.8f}\n🔥 Fee: {FEE_CACHE}", chat_id)
                else:
                    send_telegram("❌ Error obteniendo precio", chat_id)

            elif text == "/status":
                send_telegram("✅ Bot OK", chat_id)

    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 🔁 LOOP PRINCIPAL
# =========================
last_price = None

def bot_loop():
    global last_price

    print("🚀 V3 AutoFee Bot iniciado")

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
                send_telegram(f"🚀 SUBIÓ\n💰 {price}")
                last_price = price

            elif price <= last_price - STEP_DOWN:
                send_telegram(f"📉 BAJÓ\n💰 {price}")
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
