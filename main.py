import requests
import time
import os
from flask import Flask
import threading

# 🔗 API precio
URL = "https://api.dexscreener.com/latest/dex/pairs/bsc/0x7E4259eAAc5CA2Bc855C728e162d4d7782E52b7B"

# 🔐 variables de entorno
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ⚙️ configuración
STEP_UP = 0.1
STEP_DOWN = 0.1

last_price = None
last_update_id = None

# 🌐 servidor fake (para Render)
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

# 💰 obtener precio (FIX REAL)
def get_price():
    try:
        r = requests.get(URL, timeout=10)
        data = r.json()

        if "pairs" in data and len(data["pairs"]) > 0:
            return float(data["pairs"][0]["priceUsd"])
        else:
            print("⚠️ No hay datos en 'pairs'")
            return None

    except Exception as e:
        print("Error precio:", e)
        return None

# 🤖 leer mensajes (SIN DUPLICADOS)
def check_messages():
    global last_update_id

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

        if last_update_id:
            url += f"?offset={last_update_id + 1}"

        response = requests.get(url, timeout=10).json()

        for update in response["result"]:
            last_update_id = update["update_id"]

            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")

                if text == "/start":
                    send_telegram("🤖 Bot activo y funcionando", chat_id)

                elif text == "/precio":
                    price = get_price()
                    if price is not None:
                        send_telegram(f"💰 Precio actual: {price}", chat_id)
                    else:
                        send_telegram("⚠️ No se pudo obtener el precio", chat_id)

                elif text == "/status":
                    send_telegram("✅ Bot corriendo correctamente", chat_id)

                else:
                    send_telegram("❓ Comando no reconocido", chat_id)

    except Exception as e:
        print("Error leyendo mensajes:", e)

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

            print("💰 Precio:", price)

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

# 🚀 correr todo
threading.Thread(target=bot_loop).start()
run_web()
