import requests
import time
import os

# 🔗 API precio
URL = "https://api.dexscreener.com/latest/dex/pairs/bsc/0x7E4259eAAc5CA2Bc855C728e162d4d7782E52b7B"

# 🔐 variables (las pondrás en Render, NO aquí)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ⚙️ configuración
STEP_UP = 0.0001
STEP_DOWN = 0.0001

last_price = None

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )
    except Exception as e:
        print("Error Telegram:", e)

def get_price():
    try:
        r = requests.get(URL, timeout=10)
        data = r.json()
        return float(data["pair"]["priceUsd"])
    except Exception as e:
        print("Error precio:", e)
        return None

print("🚀 Bot iniciado...")

while True:
    try:
        price = get_price()

        if price is None:
            time.sleep(15)
            continue

        print("💰 Precio:", price)

        if last_price is None:
            last_price = price

        level_up = last_price + STEP_UP
        level_down = last_price - STEP_DOWN

        if price >= level_up:
            msg = f"🚀 SUBIÓ +{STEP_UP}\n💰 Precio: {price}"
            print(msg)
            send_telegram(msg)
            last_price = price

        elif price <= level_down:
            msg = f"📉 BAJÓ -{STEP_DOWN}\n💰 Precio: {price}"
            print(msg)
            send_telegram(msg)
            last_price = price

        time.sleep(10)

    except Exception as e:
        print("🔥 ERROR:", e)
        time.sleep(20)
