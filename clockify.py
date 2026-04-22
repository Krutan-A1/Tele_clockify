import os
import requests
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("CLOCKIFY_API_KEY")
WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID")
BASE_URL = "https://api.clockify.me/api/v1"


def headers():
    return {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    }


def get_projects():
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects"
    res = requests.get(url, headers=headers(), timeout=20)
    res.raise_for_status()
    return res.json()


def get_tasks(project_id):
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects/{project_id}/tasks"
    res = requests.get(url, headers=headers(), timeout=20)
    res.raise_for_status()
    return res.json()


def create_task(project_id, name):
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects/{project_id}/tasks"
    payload = {"name": name}

    res = requests.post(url, json=payload, headers=headers(), timeout=20)
    print("➕ Create Task:", res.status_code, res.text)
    return res.json()


def create_time_entry(data):
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=int(data["duration_minutes"]))

    payload = {
        "description": data["description"],
        "start": start.isoformat().replace("+00:00", "Z"),
        "end": end.isoformat().replace("+00:00", "Z"),
        "billable": False,
        "projectId": data["projectId"],
        "taskId": data["taskId"]
    }

    print("➡️ CLOCKIFY PAYLOAD:", payload)

    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time-entries"
    res = requests.post(url, json=payload, headers=headers(), timeout=20)

    print("⬅️ CLOCKIFY RESPONSE:", res.status_code, res.text)

    return res.status_code, res.text