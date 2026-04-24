import os
import json
import re
from datetime import datetime
import pytz
import requests
from dateutil import parser
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENROUTER_MODEL")
TIMEZONE = "Asia/Kolkata"

TIMEZONE = "Asia/Kolkata"


def safe_json_parse(content):
    try:
        # Try finding JSON within markdown blocks
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        
        # Fallback to finding first { and last }
        match = re.search(r"(\{.*\})", content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
            
        return json.loads(content)
    except:
        return {}


def fallback_parse(text):
    duration = 60
    text_lower = text.lower()

    match = re.search(r"(\d+(\.\d+)?)\s*h", text_lower)
    if match:
        duration = int(float(match.group(1)) * 60)

    match = re.search(r"(\d+)\s*m", text_lower)
    if match:
        duration = int(match.group(1))

    return {
        "project": "",
        "task": "",
        "duration_minutes": duration,
        "description": text,
        "start_time": datetime.now(pytz.timezone(TIMEZONE)).isoformat()
    }


def parse_message(text, project_list=None, previous_context=None):
    now = datetime.now(pytz.timezone(TIMEZONE))
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""
Convert message into JSON for a time tracking app.
Current Time ({TIMEZONE}): {current_time_str}

Message: "{text}"

Available projects:
{project_list}

"""
    if previous_context:
        prompt += f"""
Previous Context:
{json.dumps(previous_context, indent=2)}

The message is a CORRECTION or UPDATE to the previous context. Merge them sensibly.
"""

    prompt += """
Rules:
- Choose project ONLY from available list
- If unsure, return empty ""
- Extract task
- Convert duration into minutes (number)
- Extract "start_time" in ISO 8601 format. 
  If user says "started at 2pm", calculate the date based on current time.
  If no time mentioned, use current time.
- Description should be a short summary.

Return ONLY the raw JSON object. Do NOT include any conversational text, explanations, or markdown formatting blocks.

{
  "project": "",
  "task": "",
  "duration_minutes": number,
  "description": "",
  "start_time": "ISO_TIMESTAMP"
}
"""

    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
        model = os.getenv("OPENROUTER_MODEL") or "google/gemini-2.0-flash-001"

        if not api_key:
            print("⚠️ OPENROUTER_API_KEY is missing!", flush=True)
            return fallback_parse(text)

        # Using direct requests to avoid DLL/jiter issues with openai SDK
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a strict JSON generator for Clockify time entries."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            },
            timeout=30
        )
        
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        print("🧠 RAW AI:", content, flush=True)
        return safe_json_parse(content)

    except Exception as e:
        print("⚠️ AI failed, using fallback:", e, flush=True)
        return fallback_parse(text)