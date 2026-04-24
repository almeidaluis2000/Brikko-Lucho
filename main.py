import requests
import time
import os
from flask import Flask
import threading
from web3 import Web3

# 🔗 conexión BSC
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# 🔥 TU TOKEN
TOKEN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")

# 🔥 TU POOL (LP)
PAIR = Web3.to_checksum_address("0x7e4259eaac5ca2bc855c728e162d4d7782e52b7b")

# 🔐 TELEGRAM
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ⚙️ CONFIG
STEP_UP = 0.1
STEP_DOWN = 0.1

last_price = None
last_update_id = None
processed_updates = set()

# 🌐 servidor fake (Render)
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 📲 enviar mensaje
def send_telegram(msg, chat_id=CHAT_ID):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Error Telegram:", e)

# 💰 PRECIO REAL DESDE POOL
def get_price():
    try:
        print("🔥 Leyendo pool...")

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

        reserves = pair.functions.getReserves().call()
        token0 = pair.functions.token0().call()
        token1 = pair.functions.token1().call()

        reserve0 = reserves[0]
        reserve1 = reserves[1]

        print("Reserves:", reserve0, reserve1)

        # calcular precio
        if token0.lower() == TOKEN.lower():
            price = reserve1 / reserve0
        else:
            price = reserve0 / reserve1

        print("💰 Precio pool:", price)
        return price

    except Exception as e:
        print("❌ Error pool:", e)
        return None

# 🤖 comandos Telegram
def check_messages():
    global last_update_id, processed_updates

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

        if last_update_id:
            url += f"?offset={last_update_id + 1}"

        response = requests.get(url, timeout=10).json()

        for update in response["result"]:
            update_id = update["update_id"]

            if update_id in processed_updates:
                continue

            processed_updates.add(update_id)
            last_update_id = update_id

            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")

                if text == "/start":
                    send_telegram("🤖 Bot activo (precio real pool)", chat_id)

                elif text == "/precio":
                    price = get_price()
                    if price is not None:
                        send_telegram(f"💰 Precio real: {price}", chat_id)
                    else:
                        send_telegram("⚠️ Error obteniendo precio", chat_id)

                elif text == "/status":
                    send_telegram("✅ Bot corriendo correctamente", chat_id)

                else:
                    send_telegram("❓ Comando no reconocido", chat_id)

    except Exception as e:
        print("Error mensajes:", e)

# 🔁 loop principal
def bot_loop():
    global last_price
    print("🚀 Bot iniciado...")

    while True:
        try:
            check_messages()

            price = get_price()

            if price is None:
                time.sleep(10)
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
            print("🔥 ERROR:", e)
            time.sleep(15)

# 🚀 ejecutar
threading.Thread(target=bot_loop).start()
run_web()
