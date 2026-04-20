import google.generativeai as genai
import os
import json




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
    
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    model = genai.GenerativeModel("gemini-2.5-flash")
    

    response = model.generate_content(prompt)

    content = response.text.strip()

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