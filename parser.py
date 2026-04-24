import os
import json
import re
from datetime import datetime
import pytz
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL")
)

MODEL = os.getenv("OPENROUTER_MODEL")
TIMEZONE = "Asia/Kolkata"


def safe_json_parse(content):
    content = content.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        content = match.group(0)
    return json.loads(content)


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

Return ONLY JSON:
{
  "project": "",
  "task": "",
  "duration_minutes": number,
  "description": "",
  "start_time": "ISO_TIMESTAMP"
}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a strict JSON generator for Clockify time entries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        print("🧠 RAW AI:", content)

        return safe_json_parse(content)

    except Exception as e:
        print("⚠️ AI failed, using fallback:", e)
        return fallback_parse(text)