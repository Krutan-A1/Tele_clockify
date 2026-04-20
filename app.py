from flask import Flask, request
import requests
import os
import uuid
from parser import parse_message
from clockify import create_time_entry
import logging


app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Temporary storage (replace with DB later)
pending_requests = {}

# ---------------------------
# Send Telegram Message
# ---------------------------
def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    }

    requests.post(url, json=payload)

# ---------------------------
@app.route("/")
def home():
    return "Bot running 🚀"


logging.basicConfig(level=logging.INFO)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    logging.info(f"Incoming request: {data}")

    # Handle confirm button
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        action = callback["data"]

        logging.info(f"User clicked confirm: {action}")

        if action in pending_requests:
            parsed = pending_requests[action]

            logging.info(f"Sending to Clockify: {parsed}")

            status, res = create_time_entry(parsed)

            logging.info(f"Clockify response: {status} - {res}")

            if status == 201:
                send_message(chat_id, "✅ Time entry created!")
            else:
                send_message(chat_id, f"❌ Error: {res}")

            del pending_requests[action]

        return "ok"

    # Handle normal message
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    logging.info(f"User message: {text}")

    parsed = parse_message(text)

    logging.info(f"Parsed JSON: {parsed}")

# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)