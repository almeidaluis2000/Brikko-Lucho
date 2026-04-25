import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# 🔗 RPC BSC (fallback)
# =========================
RPCS = [
    "https://bsc-dataseed1.binance.org/",
    "https://bsc-dataseed2.defibit.io/",
    "https://bsc-dataseed3.defibit.io/"
]

bsc = None
for rpc in RPCS:
    w3 = Web3(Web3.HTTPProvider(rpc))
    if w3.is_connected():
        bsc = w3
        print("✅ RPC conectado:", rpc)
        break

if not bsc:
    raise Exception("No RPC available")

# =========================
# 🔥 CONFIG
# =========================
TOKEN_IN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
TOKEN_OUT = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")  # WBNB ejemplo

POOL = Web3.to_checksum_address("0x7e4259eaac5ca2bc855c728e162d4d7782e52b7b")

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
    return "V3 Bot activo"

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
# 📡 V3 POOL ABI (slot0)
# =========================
pool_abi = [
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

pool = bsc.eth.contract(address=POOL, abi=pool_abi)

# =========================
# 💰 PRICE V3 (CORRECTO)
# =========================
def get_price():
    try:
        slot0 = pool.functions.slot0().call()
        sqrtPriceX96 = slot0[0]

        token0 = pool.functions.token0().call()
        token1 = pool.functions.token1().call()

        # Precio raw V3
        price_raw = (sqrtPriceX96 * sqrtPriceX96) / (2 ** 192)

        # Decimals (IMPORTANTE)
        decimals0 = 18
        decimals1 = 18

        # Ajuste real de decimales
        price = price_raw * (10 ** (decimals0 - decimals1))

        # Corrección de dirección del par
        if token0.lower() != TOKEN_IN.lower():
            price = 1 / price

        return price

    except Exception as e:
        print("❌ PRICE ERROR:", repr(e))
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
                send_telegram("🤖 V3 Bot activo", chat_id)

            elif text == "/precio":
                price = get_price()
                if price:
                    send_telegram(f"💰 Precio V3: {price:.10f}", chat_id)
                else:
                    send_telegram("⚠️ Error precio", chat_id)

            elif text == "/status":
                send_telegram("✅ OK", chat_id)

    except Exception as e:
        print("Telegram error:", e)

# =========================
# 🔁 BOT LOOP
# =========================
last_price = None

def bot_loop():
    global last_price

    print("🚀 V3 Bot iniciado")

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
            print("Loop error:", e)
            time.sleep(10)

# =========================
# 🚀 START
# =========================
threading.Thread(target=bot_loop, daemon=True).start()
run_web()
