import os
import json
import re
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------------------
# Initialization
# ---------------------------
load_dotenv()

app = Flask(__name__)

# Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GEMINI_API_KEY or not TELEGRAM_TOKEN:
    raise ValueError("❌ Environment variables GEMINI_API_KEY or TELEGRAM_BOT_TOKEN missing")

# Clean token (prevents 404 error if .env has spaces)
TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip()
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")  # Use the latest flash model for best performance

# ---------------------------
# Logic Functions
# ---------------------------

def fallback_parse(text):
    """Parses message using RegEx if AI fails."""
    duration = 60
    text_lower = text.lower()
    
    # hours: 2h, 1.5h
    match = re.search(r"(\d+(\.\d+)?)\s*h", text_lower)
    if match:
        duration = int(float(match.group(1)) * 60)
    
    # minutes: 30m
    match = re.search(r"(\d+)\s*m", text_lower)
    if match:
        duration = int(match.group(1))

    return {
        "project": "General",
        "task": "Work",
        "duration_minutes": duration,
        "description": text
    }

def parse_message_with_ai(text):
    """Sends user text to Gemini and returns structured JSON."""
    prompt = f"""
Convert this message into structured JSON.
Message: "{text}"

Return ONLY JSON:
{{
  "project": "",
  "task": "",
  "duration_minutes": number,
  "description": ""
}}
"""
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        # Clean Markdown formatting if present
        content = content.replace("```json", "").replace("```", "").strip()
        print(f"✅ AI Response: {content}")
        return json.loads(content)
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return fallback_parse(text)

def send_telegram_message(chat_id, text):
    """Sends response back to Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Telegram Error {response.status_code}: {response.text}")
    return response.json()

# ---------------------------
# Webhook Route
# ---------------------------

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # Ensure we have a message
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        # 1. Process with AI
        structured_data = parse_message_with_ai(user_text)
        
        # 2. Format Response
        reply = (
            f"*✅ Task Parsed Successfully*\n\n"
            f"📂 *Project:* {structured_data.get('project')}\n"
            f"📝 *Task:* {structured_data.get('task')}\n"
            f"⏱️ *Duration:* {structured_data.get('duration_minutes')} mins\n"
            f"📖 *Desc:* {structured_data.get('description')}"
        )
        
        # 3. Send Back
        send_telegram_message(chat_id, reply)
        
    return "OK", 200

if __name__ == '__main__':
    # Use port 5000 for local development (or whatever matches your webhook config)
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, debug=True , host="0.0.0.0")