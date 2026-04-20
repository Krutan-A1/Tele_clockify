import requests
import os
from datetime import datetime, timedelta

API_KEY = os.getenv("CLOCKIFY_API_KEY")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")

def create_time_entry(data):
    start = datetime.utcnow()
    end = start + timedelta(minutes=data["duration_minutes"])

    payload = {
        "description": data["description"],
        "start": start.isoformat() + "Z",
        "end": end.isoformat() + "Z",
        "billable": False
    }

    headers = {
        "X-Api-Key": API_KEY
    }

    url = f"https://api.clockify.me/api/v1/workspaces/{WORKSPACE_ID}/time-entries"

    res = requests.post(url, json=payload, headers=headers)

    return res.status_code, res.text