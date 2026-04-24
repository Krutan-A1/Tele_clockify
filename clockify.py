import os
import json
import requests
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("CLOCKIFY_API_KEY")
WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID")
BASE_URL = "https://api.clockify.me/api/v1"
CACHE_FILE = "clockify_cache.json"


def headers():
    return {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    }


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def clear_cache():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)


def get_projects(force_refresh=False):
    cache = load_cache()
    if not force_refresh and "projects" in cache:
        return cache["projects"]

    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects"
    res = requests.get(url, headers=headers(), timeout=20)
    res.raise_for_status()
    projects = res.json()
    
    cache["projects"] = projects
    save_cache(cache)
    return projects


def get_tasks(project_id, force_refresh=False):
    cache = load_cache()
    if not force_refresh and f"tasks_{project_id}" in cache:
        return cache[f"tasks_{project_id}"]

    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects/{project_id}/tasks"
    res = requests.get(url, headers=headers(), timeout=20)
    res.raise_for_status()
    tasks = res.json()

    cache[f"tasks_{project_id}"] = tasks
    save_cache(cache)
    return tasks


def create_task(project_id, name):
    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/projects/{project_id}/tasks"
    payload = {"name": name}

    res = requests.post(url, json=payload, headers=headers(), timeout=20)
    print("➕ Create Task:", res.status_code, res.text)
    task = res.json()
    
    # Update cache
    cache = load_cache()
    if f"tasks_{project_id}" in cache:
        cache[f"tasks_{project_id}"].append(task)
        save_cache(cache)
        
    return task


def create_time_entry(data):
    # Use provided start_time or default to now
    if "start_time" in data and data["start_time"]:
        start_str = data["start_time"]
        # Ensure it's in Z format
        if "+" in start_str:
            # Simple convert to Z for Clockify
            from dateutil import parser
            dt = parser.isoparse(start_str).astimezone(timezone.utc)
            start_str = dt.isoformat().replace("+00:00", "Z")
    else:
        dt = datetime.now(timezone.utc)
        start_str = dt.isoformat().replace("+00:00", "Z")

    # Parse the start_str back to calculate end
    from dateutil import parser
    start_dt = parser.isoparse(start_str.replace("Z", "+00:00"))
    end_dt = start_dt + timedelta(minutes=int(data["duration_minutes"]))
    end_str = end_dt.isoformat().replace("+00:00", "Z")

    payload = {
        "description": data["description"],
        "start": start_str,
        "end": end_str,
        "billable": False,
        "projectId": data["projectId"],
        "taskId": data["taskId"]
    }

    print("➡️ CLOCKIFY PAYLOAD:", payload)

    url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time-entries"
    res = requests.post(url, json=payload, headers=headers(), timeout=20)

    print("⬅️ CLOCKIFY RESPONSE:", res.status_code, res.text)

    return res.status_code, res.text