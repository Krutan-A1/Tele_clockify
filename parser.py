import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv

# ---------------------------
# Load ENV only once
# ---------------------------
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found")

genai.configure(api_key=api_key)

# Initialize model ONCE
model = genai.GenerativeModel("models/gemini-pro")


# ---------------------------
# Fallback Parser
# ---------------------------
def fallback_parse(text):
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


# ---------------------------
# Main Parser
# ---------------------------
def parse_message(text):
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
        content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except Exception as e:
        error_text = str(e).lower()

        # 🔴 Handle quota error
        if "quota" in error_text or "429" in error_text:
            retry_time = 30

            if "retry_delay" in error_text:
                try:
                    retry_time = int(
                        error_text.split("seconds")[0].split()[-1]
                    )
                except:
                    pass

            raise Exception(f"RATE_LIMIT:{retry_time}")

        # 🟡 fallback instead of crash
        print("⚠️ AI failed, using fallback:", e)

        return fallback_parse(text)