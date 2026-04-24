import os
import json
import requests
from datetime import datetime, timedelta, timezone

CACHE_FILE = "clockify_cache.json"

def get_env():
    workspace_id = os.getenv("CLOCKIFY_WORKSPACE_ID")
    api_key = os.getenv("CLOCKIFY_API_KEY")
    
    if not workspace_id:
        print("❌ CRITICAL: CLOCKIFY_WORKSPACE_ID is missing from environment!", flush=True)
    if not api_key:
        print("❌ CRITICAL: CLOCKIFY_API_KEY is missing from environment!", flush=True)
        
    return {
        "API_KEY": api_key,
        "WORKSPACE_ID": workspace_id,
        "BASE_URL": "https://api.clockify.me/api/v1"
    }

def headers():
    env = get_env()
    return {
        "X-Api-Key": env["API_KEY"],
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

    env = get_env()
    url = f"{env['BASE_URL']}/workspaces/{env['WORKSPACE_ID']}/projects"
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

    env = get_env()
    url = f"{env['BASE_URL']}/workspaces/{env['WORKSPACE_ID']}/projects/{project_id}/tasks"
    res = requests.get(url, headers=headers(), timeout=20)
    res.raise_for_status()
    tasks = res.json()

    cache[f"tasks_{project_id}"] = tasks
    save_cache(cache)
    return tasks

def create_task(project_id, name):
    env = get_env()
    url = f"{env['BASE_URL']}/workspaces/{env['WORKSPACE_ID']}/projects/{project_id}/tasks"
    payload = {"name": name}

    res = requests.post(url, json=payload, headers=headers(), timeout=20)
    print("➕ Create Task:", res.status_code, res.text, flush=True)
    task = res.json()
    
    # Update cache
    cache = load_cache()
    if f"tasks_{project_id}" in cache:
        cache[f"tasks_{project_id}"].append(task)
        save_cache(cache)
        
    return task

def create_time_entry(data):
    env = get_env()
    from dateutil import parser
    import pytz

    # Use provided start_time or default to now
    if "start_time" in data and data["start_time"]:
        try:
            start_str = data["start_time"]
            dt = parser.isoparse(start_str)
            
            # If no timezone is provided, assume Asia/Kolkata
            if dt.tzinfo is None:
                local_tz = pytz.timezone("Asia/Kolkata")
                dt = local_tz.localize(dt)
            
            # Convert to UTC for Clockify
            dt_utc = dt.astimezone(timezone.utc)
            start_str = dt_utc.isoformat().replace("+00:00", "Z")
        except Exception as e:
            print(f"⚠️ Start time parse error: {e}, falling back to now", flush=True)
            dt_utc = datetime.now(timezone.utc)
            start_str = dt_utc.isoformat().replace("+00:00", "Z")
    else:
        dt_utc = datetime.now(timezone.utc)
        start_str = dt_utc.isoformat().replace("+00:00", "Z")

    # Calculate end time based on duration (minimum 1 minute to avoid Clockify errors)
    duration = int(data.get("duration_minutes", 1))
    if duration < 1: duration = 1
    
    end_dt = dt_utc + timedelta(minutes=duration)
    end_str = end_dt.isoformat().replace("+00:00", "Z")

    payload = {
        "description": data["description"],
        "start": start_str,
        "end": end_str,
        "billable": False,
        "projectId": data["projectId"],
        "taskId": data["taskId"] if data.get("taskId") else None,
        "type": "REGULAR"
    }

    print("➡️ CLOCKIFY PAYLOAD:", json.dumps(payload, indent=2), flush=True)

    url = f"{env['BASE_URL']}/workspaces/{env['WORKSPACE_ID']}/time-entries"
    res = requests.post(url, json=payload, headers=headers(), timeout=20)

    print(f"⬅️ CLOCKIFY RESPONSE ({res.status_code}):", res.text, flush=True)

    return res.status_code, res.text