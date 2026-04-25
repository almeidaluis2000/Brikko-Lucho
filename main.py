import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

# =========================
# 🔗 BSC CONNECTION
# =========================
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# =========================
# 🔥 CONFIG
# =========================
TOKEN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
PAIR = Web3.to_checksum_address("0x7e4259eaac5ca2bc855c728e162d4d7782e52b7b")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STEP_UP = 0.1
STEP_DOWN = 0.1

# =========================
# 🌐 FLASK APP
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# 🌐 HTTP SESSION (OPTIMIZED)
# =========================
session = requests.Session()

# =========================
# 📡 ERC20 ABI (DECIMALS)
# =========================
erc20_abi = [
    {
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

token_contract = bsc.eth.contract(address=TOKEN, abi=erc20_abi)
token_decimals = token_contract.functions.decimals().call()

# =========================
# 🔥 PAIR ABI
# =========================
pair_abi = [
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
    },
    {
        "name": "token1",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

pair = bsc.eth.contract(address=PAIR, abi=pair_abi)

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
# 💰 PRICE FUNCTION (CORRECTED)
# =========================
def get_price():
    try:
        reserves = pair.functions.getReserves().call()
        token0 = pair.functions.token0().call()
        token1 = pair.functions.token1().call()

        reserve0 = reserves[0]
        reserve1 = reserves[1]

        # normalización con decimals
        if token0.lower() == TOKEN.lower():
            price = (reserve1 / 1e18) / (reserve0 / 10**token_decimals)
        else:
            price = (reserve0 / 1e18) / (reserve1 / 10**token_decimals)

        return price

    except Exception as e:
        print("Price error:", e)
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

        response = session.get(url, timeout=15).json()

        for update in response.get("result", []):
            last_update_id = update["update_id"]

            message = update.get("message")
            if not message:
                continue

            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if text == "/start":
                send_telegram("🤖 Bot activo (precio real pool)", chat_id)

            elif text == "/precio":
                price = get_price()
                if price:
                    send_telegram(f"💰 Precio: {price:.8f}", chat_id)
                else:
                    send_telegram("⚠️ Error precio", chat_id)

            elif text == "/status":
                send_telegram("✅ Bot OK", chat_id)

            else:
                send_telegram("❓ Comando inválido", chat_id)

    except Exception as e:
        print("Telegram loop error:", e)

# =========================
# 🔁 MAIN LOOP
# =========================
last_price = None

def bot_loop():
    global last_price

    print("🚀 Bot iniciado")

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
