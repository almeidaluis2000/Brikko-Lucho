import requests
import time
import os
from flask import Flask
import threading
from web3 import Web3

# 🔗 conexión BSC (más estable)
bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))

# 🔥 Router PancakeSwap
router_address = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")

router_abi = [{
    "name": "getAmountsOut",
    "outputs": [{"type": "uint256[]"}],
    "inputs": [
        {"type": "uint256", "name": "amountIn"},
        {"type": "address[]", "name": "path"}
    ],
    "stateMutability": "view",
    "type": "function"
}]

router = bsc.eth.contract(address=router_address, abi=router_abi)

# 🔥 TOKENS
TOKEN = Web3.to_checksum_address("0xec9742f992ACc615C4252060D896c845ca8fC086")
USDT = Web3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")
WBNB = Web3.to_checksum_address("0xBB4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")

# 🔐 TELEGRAM
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ⚙️ CONFIG
STEP_UP = 0.1
STEP_DOWN = 0.1

last_price = None
last_update_id = None
processed_updates = set()

# 🌐 servidor fake
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 📲 TELEGRAM
def send_telegram(msg, chat_id=CHAT_ID):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Error Telegram:", e)

# 💰 PRECIO REAL PANCAKE (ROBUSTO)
def get_price():
    try:
        print("🔥 Calculando precio Pancake...")

        amount_in = Web3.to_wei(1, 'ether')

        paths = [
            [TOKEN, USDT],
            [TOKEN, WBNB, USDT],
            [TOKEN, WBNB]
        ]

        for path in paths:
            try:
                amounts = router.functions.getAmountsOut(amount_in, path).call()
                price = amounts[-1] / 1e18

                print(f"✅ Ruta usada: {path}")
                print(f"💰 Precio: {price}")

                return price

            except Exception:
                print(f"❌ Ruta falló: {path}")

        return None

    except Exception as e:
        print("❌ Error pancake:", e)
        return None

# 🤖 TELEGRAM COMMANDS
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
                    send_telegram("🤖 Bot activo (precio Pancake real)", chat_id)

                elif text == "/precio":
                    price = get_price()
                    if price is not None:
                        send_telegram(f"🔥 Precio real Pancake: {price}", chat_id)
                    else:
                        send_telegram("⚠️ No se pudo calcular el precio", chat_id)

                elif text == "/status":
                    send_telegram("✅ Bot corriendo correctamente", chat_id)

                else:
                    send_telegram("❓ Comando no reconocido", chat_id)

    except Exception as e:
        print("Error leyendo mensajes:", e)

# 🔁 LOOP
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

# 🚀 RUN
threading.Thread(target=bot_loop).start()
run_web()
