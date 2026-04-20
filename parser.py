import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted



def fallback_parse(text):
    """Simple manual parser if AI fails"""
    duration = 60

    # extract hours like 2h, 1.5h
    match = re.search(r"(\d+(\.\d+)?)\s*h", text.lower())
    if match:
        duration = int(float(match.group(1)) * 60)

    # extract minutes like 30m
    match = re.search(r"(\d+)\s*m", text.lower())
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

Return ONLY JSON:

{{
  "project": "",
  "task": "",
  "duration_minutes": number,
  "description": ""
}}
"""
    
    load_dotenv()

    # Configure Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found")

    genai.configure(api_key=api_key)

    # Use stable model
    model = genai.GenerativeModel("models/gemini-pro")


    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except ResourceExhausted as e:
        retry_time = 20
        try:
            retry_time = int(e.retry_delay.seconds)
        except:
            pass

        raise Exception(f"RATE_LIMIT:{retry_time}")

    except Exception as e:
        print("⚠️ AI failed, using fallback:", e)
        return fallback_parse(text)