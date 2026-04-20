from flask import Flask, request
import requests
import os
import uuid
import logging
from dotenv import load_dotenv

from parser import parse_message

load_dotenv()

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLOCKIFY_API_KEY = os.getenv("CLOCKIFY_API_KEY")
WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID")

pending_requests = {}


# ---------------------------
# Telegram Send Message
# ---------------------------
def send_message(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(url, json=payload)


# ---------------------------
# Clockify API
# ---------------------------
def create_time_entry(data):
    url = f"https://api.clockify.me/api/v1/workspaces/{WORKSPACE_ID}/time-entries"

    payload = {
        "start": "2026-01-01T09:00:00Z",
        "duration": f"PT{data['duration_minutes']}M",
        "description": data["description"]
    }

    headers = {
        "X-Api-Key": CLOCKIFY_API_KEY,
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)

    return res.status_code, res.text


# ---------------------------
# Webhook
# ---------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Incoming request: {data}")

    # ---------------------------
    # Handle Confirm Button
    # ---------------------------
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
                send_message(chat_id, f"❌ Clockify error: {res}")

            del pending_requests[action]

        return "ok"

    # ---------------------------
    # Handle Message
    # ---------------------------
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    logging.info(f"User message: {text}")

    # Handle commands
    if text.startswith("/"):
        send_message(chat_id, "👋 Send something like:\nWorked 2h on vigil API")
        return "ok"

    # ---------------------------
    # Parse with AI
    # ---------------------------
    try:
        parsed = parse_message(text)

    except Exception as e:
        error_msg = str(e)

        if error_msg.startswith("RATE_LIMIT"):
            wait_time = error_msg.split(":")[1]

            send_message(
                chat_id,
                f"⏳ AI quota reached.\nPlease try again in {wait_time} seconds."
            )
            return "ok"

        send_message(chat_id, "❌ Error parsing message. Try again.")
        return "ok"

    logging.info(f"Parsed JSON: {parsed}")

    # ---------------------------
    # Ask for confirmation
    # ---------------------------
    request_id = str(uuid.uuid4())
    pending_requests[request_id] = parsed

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
# Health Check
# ---------------------------
@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    app.run(debug=True)