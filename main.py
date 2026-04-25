import os
import time
import threading
import requests
from flask import Flask
from web3 import Web3

bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot activo"

session = requests.Session()

def safe_get_env(name):
    value = os.getenv(name)
    if not value:
        print(f"❌ FALTA VARIABLE: {name}")
    return value

BOT_TOKEN = safe_get_env("BOT_TOKEN")
CHAT_ID = safe_get_env("CHAT_ID")

POOL = Web3.to_checksum_address("0x7E4259eAAc5CA2Bc855C728e162d4d7782E52b7B")

abi = [
    {
        "name": "slot0",
        "outputs": [{"type": "uint160"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function"
    }
]

pool = bsc.eth.contract(address=POOL, abi=abi)

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

def get_price():
    try:
        slot0 = pool.functions.slot0().call()
        sqrtPriceX96 = slot0[0]
        return (sqrtPriceX96 ** 2) / (2 ** 192)
    except Exception as e:
        print("Price error:", repr(e))
        return None

def bot():
    print("🚀 Bot iniciado correctamente")

    while True:
        price = get_price()

        if price:
            print("💰", price)
        else:
            print("❌ sin precio")

        time.sleep(10)

def start():
    try:
        threading.Thread(target=bot, daemon=True).start()
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    except Exception as e:
        print("🔥 FATAL ERROR:", repr(e))

if __name__ == "__main__":
    start()
