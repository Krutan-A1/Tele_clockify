import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENROUTER_BASE_URL")
)

MODEL = os.getenv("OPENROUTER_MODEL")


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
        "description": text
    }


def parse_message(text, project_list=None):
    prompt = f"""
Convert message into JSON.

Message: "{text}"

Available projects:
{project_list}

Rules:
- Choose project ONLY from available list
- If unsure, return empty ""
- Extract task
- Convert time into minutes

Return ONLY JSON:
{{
  "project": "",
  "task": "",
  "duration_minutes": number,
  "description": ""
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a strict JSON generator."},
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