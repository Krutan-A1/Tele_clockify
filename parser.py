import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

def parse_message(text):
    prompt = f"""
Convert this message into structured JSON.

Message: "{text}"

Rules:
- Extract project name
- Extract task
- Extract duration in minutes
- Clean description

Return ONLY JSON:

{{
  "project": "",
  "task": "",
  "duration_minutes": number,
  "description": ""
}}
"""

    response = model.generate_content(prompt)
    content = response.text.strip()

    # Fix common AI formatting issues
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(content)
    except:
        return {
            "project": "General",
            "task": "Work",
            "duration_minutes": 60,
            "description": text
        }