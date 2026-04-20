from openai import OpenAI
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv("NVIDIA_BASE_URL")
)


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
        "project": "General",
        "task": "Work",
        "duration_minutes": duration,
        "description": text
    }


def parse_message(text):
    prompt = f"""
Convert this message into structured JSON.

Message: "{text}"

Rules:
- Extract project name (like Vigil, Kore, Weldsense)
- Extract task (short)
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
            model="nvidia/nemotron-3-super",
            messages=[
                {"role": "system", "content": "You are a strict JSON generator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()

        # clean JSON if wrapped
        content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except Exception as e:
        print("⚠️ AI failed, using fallback:", e)
        return fallback_parse(text)