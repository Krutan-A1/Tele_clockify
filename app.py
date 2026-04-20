from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# -----------------------------------
# Test route
# -----------------------------------
@app.route("/")
def home():
    return "Server is running ✅"

# -----------------------------------
# Telegram webhook route
# -----------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("Incoming Data:", data)

    # Extract message safely
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    print("Chat ID:", chat_id)
    print("Text:", text)

    # Reply back
    if chat_id and text:
        send_message(chat_id, f"Received: {text}")

    return "ok"


# -----------------------------------
# Function to send message to Telegram
# -----------------------------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    response = requests.post(url, json=payload)

    print("Telegram response:", response.text)


# -----------------------------------
# Run server
# -----------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)