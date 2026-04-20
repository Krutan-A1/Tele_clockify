from flask import Flask, request
import requests
import os
import uuid
from parser import parse_message
from clockify import create_time_entry

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
# Webhook
# ---------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # Handle confirm button
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        action = callback["data"]

        if action in pending_requests:
            parsed = pending_requests[action]

            status, res = create_time_entry(parsed)

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

    if not text:
        return "ok"

    # Step 1: Parse using Gemini
    parsed = parse_message(text)

    # Step 2: Save request
    request_id = str(uuid.uuid4())
    pending_requests[request_id] = parsed

    # Step 3: Ask for confirmation
    confirm_text = f"""
Confirm entry:

Project: {parsed['project']}
Task: {parsed['task']}
Duration: {parsed['duration_minutes']} min
Desc: {parsed['description']}
"""

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Confirm", "callback_data": request_id}
        ]]
    }

    send_message(chat_id, confirm_text, keyboard)

    return "ok"

# ---------------------------
@app.route("/")
def home():
    return "Bot running 🚀"

# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)