import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

POOL = Web3.to_checksum_address("0x7E4259eAAc5CA2Bc855C728e162d4d7782E52b7Bec")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

session = requests.Session()

app = Flask(__name__)

@app.route("/")
def home():
    return "V3 FIX activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# 📡 ABI V3 COMPLETO
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
    },
    {
        "name": "token0",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "name": "token1",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

pool = bsc.eth.contract(address=POOL, abi=abi)

# =========================
# 📲 TELEGRAM
# =========================
def send_telegram(msg):
    try:
        session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", repr(e))

# =========================
# 💰 PRECIO V3 REAL CORRECTO
# =========================
def get_price():
    try:
        slot0 = pool.functions.slot0().call()
        sqrtPriceX96 = slot0[0]

        token0 = pool.functions.token0().call()
        token1 = pool.functions.token1().call()

        # DECIMALS estándar BSC
        decimals0 = 18
        decimals1 = 18

        price_raw = (sqrtPriceX96 ** 2) / (2 ** 192)

        # ajuste de decimales
        price = price_raw * (10 ** (decimals0 - decimals1))

        return price

    except Exception as e:
        print("❌ ERROR SLOT0:", repr(e))
        return None

# =========================
# 🤖 LOOP
# =========================
def bot_loop():
    print("🚀 V3 FIX PRO iniciado")

    while True:
        try:
            price = get_price()

            if price is None or price == 0:
                print("sin liquidez real o pool vacío")
            else:
                print("💰 PRICE:", price)

            time.sleep(5)

        except Exception as e:
            print("loop error:", repr(e))
            time.sleep(10)

threading.Thread(target=bot_loop, daemon=True).start()
run_web()
