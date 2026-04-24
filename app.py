import platform
import os
import json
import threading
from difflib import get_close_matches

import requests
from flask import Flask, request
from dotenv import load_dotenv
load_dotenv()

from parser import parse_message
from clockify import get_projects, get_tasks, create_task, create_time_entry, clear_cache

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN").strip()
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# persistence file - Using /tmp for Linux/Render, local folder for Windows
if platform.system() == "Windows":
    PENDING_FILE = "pending_context.json"
else:
    PENDING_FILE = "/tmp/pending_context.json"

def load_pending():
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Load error: {e}")
            return {}
    return {}

def save_pending(context):
    try:
        with open(PENDING_FILE, "w") as f:
            json.dump(context, f, indent=2)
    except Exception as e:
        print(f"⚠️ Save error: {e}")


# ---------------------------
# Helpers
# ---------------------------

def send(chat_id, text, keyboard=None):
    try:
        payload = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", data=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Send error: {e}", flush=True)

def answer(cb_id):
    try:
        requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", data={"callback_query_id": cb_id}, timeout=5)
    except:
        pass


def keyboard():
    return {
        "inline_keyboard": [[
            {"text": "✅ Confirm", "callback_data": "confirm"},
            {"text": "✏️ Edit", "callback_data": "edit"},
            {"text": "❌ Cancel", "callback_data": "cancel"}
        ]]
    }


def norm(x):
    return (x or "").lower().strip()


def match(name, items):
    if not name or not isinstance(items, list):
        return None

    name = norm(name)
    
    # Safety: filter out items that don't have a 'name' key
    valid_items = [i for i in items if isinstance(i, dict) and "name" in i]
    mapping = {norm(i["name"]): i for i in valid_items}

    if name in mapping:
        return mapping[name]

    for k, v in mapping.items():
        if name in k:
            return v

    close = get_close_matches(name, mapping.keys(), n=1, cutoff=0.6)
    if close:
        return mapping[close[0]]

    return None


# ---------------------------
# Routes
# ---------------------------

@app.route("/")
def home():
    return "Server running 🚀"


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}
        event_type = "message" if "message" in data else ("callback_query" if "callback_query" in data else "unknown")
        print(f"📢 RECEIVED TYPE: {event_type}", flush=True)
        print("🔥 Incoming Raw:", json.dumps(data, indent=1), flush=True)

        pending_context = load_pending()

        # 1. BUTTONS (Check this first)
        if "callback_query" in data:
            cb = data["callback_query"]
            chat_id = str(cb["message"]["chat"]["id"])
            action = cb["data"]
            
            print(f"🔘 Button Clicked by {chat_id}: {action}", flush=True)

            # Give immediate visual feedback in Telegram (shows a small "Processing" toast)
            try:
                requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", 
                              data={"callback_query_id": cb["id"], "text": "⌛ Processing..."}, 
                              timeout=5)
            except:
                pass

            pending = pending_context.get(chat_id)

            if not pending:
                print(f"⚠️ No pending task found for chat_id: {chat_id}", flush=True)
                send(chat_id, "❌ No pending task found. Please send a new message.")
                return "OK", 200

            if action == "cancel":
                pending_context.pop(chat_id, None)
                save_pending(pending_context)
                send(chat_id, "❌ Cancelled")
                return "OK", 200

            if action == "edit":
                pending["state"] = "editing"
                save_pending(pending_context)
                send(chat_id, "✏️ What would you like to change? (Just tell me the update, e.g. 'change duration to 45 mins')")
                return "OK", 200

            if action == "confirm":
                print(f"🚀 Attempting Clockify log for {chat_id}...", flush=True)
                # Calculate end time based on duration (minimum 1 minute to avoid Clockify errors)
                duration = int(pending["parsed"].get("duration_minutes", 1))
                if duration < 1: duration = 1
                
                payload = {
                    "description": pending["parsed"]["description"],
                    "duration_minutes": duration,
                    "projectId": pending["project"]["id"],
                    "taskId": pending["task"]["id"],
                    "start_time": pending["parsed"].get("start_time")
                }

                status, resp = create_time_entry(payload)

                if 200 <= status < 300:
                    send(chat_id, "✅ Entry created successfully in Clockify!")
                    pending_context.pop(chat_id, None)
                    save_pending(pending_context)
                else:
                    send(chat_id, f"❌ Clockify Error:\n{resp}")

            return "OK", 200

        # 2. MESSAGES
        if "message" in data and "text" in data["message"]:
            chat_id = str(data["message"]["chat"]["id"])
            text = data["message"]["text"]
            
            print(f"📩 Message from {chat_id}: {text}", flush=True)

            # Handle Commands (Case-insensitive)
            cmd = text.lower().strip()
            if cmd.startswith("/"):
                if cmd == "/sync":
                    clear_cache()
                    get_projects(force_refresh=True)
                    send(chat_id, "✅ Clockify cache cleared and projects synced.")
                    return "OK", 200
                elif cmd == "/start":
                    send(chat_id, "Welcome! Just tell me what you're working on, e.g., '2 hours on Project X task Y description Z'")
                    return "OK", 200
                elif cmd == "/confirm":
                    # Manually trigger confirm logic
                    print("⌨️ Manual /confirm command received", flush=True)
                    pending = pending_context.get(chat_id)
                    if pending:
                        # Safety: duration minimum 1 min
                        duration = int(pending["parsed"].get("duration_minutes", 1))
                        if duration < 1: duration = 1
                        
                        payload = {
                            "description": pending["parsed"]["description"],
                            "duration_minutes": duration,
                            "projectId": pending["project"]["id"],
                            "taskId": pending["task"]["id"],
                            "start_time": pending["parsed"].get("start_time")
                        }
                        status, resp = create_time_entry(payload)
                        if 200 <= status < 300:
                            send(chat_id, "✅ Entry created successfully via command!")
                            pending_context.pop(chat_id, None)
                            save_pending(pending_context)
                        else:
                            send(chat_id, f"❌ Failed:\n{resp}")
                        return "OK", 200
                elif cmd == "/cancel":
                    print("⌨️ Manual /cancel command received", flush=True)
                    pending_context.pop(chat_id, None)
                    save_pending(pending_context)
                    send(chat_id, "❌ Cancelled")
                    return "OK", 200

            # Handle Editing State
            prev_pending = pending_context.get(chat_id)
            if prev_pending and prev_pending.get("state") == "editing":
                previous_parsed = prev_pending.get("parsed")
            else:
                previous_parsed = None

            projects = get_projects()
            project_names = [p["name"] for p in projects]

            parsed = parse_message(text, project_names, previous_context=previous_parsed)
            print("🧠 Parsed:", parsed, flush=True)

            project = match(parsed.get("project"), projects)

            if not project:
                send(chat_id, f"❌ Project not found.\nTry: {', '.join(project_names[:5])}")
                return "OK", 200
            
            tasks = get_tasks(project["id"])
            task = match(parsed.get("task"), tasks)

            if not task:
                task_name = parsed.get("task") or "General"
                # auto create task
                new_task_resp = create_task(project["id"], task_name)
                
                # If task already exists, find it in the list
                if "id" not in new_task_resp:
                    tasks = get_tasks(project["id"], force_refresh=True)
                    task = match(task_name, tasks)
                    if task:
                        task_id = task["id"]
                        task_name = task["name"]
                    else:
                        # Fallback
                        task_id = None
                        task_name = "General (Created)"
                else:
                    task_id = new_task_resp["id"]
                    task_name = new_task_resp["name"]
            else:
                task_id = task["id"]
                task_name = task["name"]

            pending_context[chat_id] = {
                "parsed": parsed,
                "project": project,
                "task": {"id": task_id, "name": task_name},
                "state": "pending"
            }
            save_pending(pending_context)

            # Format start time for display
            st = parsed.get("start_time", "Now")
            if "T" in st:
                st = st.split("T")[1][:5] # HH:MM

            msg = (
                f"📂 Project: {project['name']}\n"
                f"📝 Task: {task_name}\n"
                f"⏱ Duration: {parsed['duration_minutes']} mins\n"
                f"🕒 Start: {st}\n"
                f"📖 Desc: {parsed['description']}\n\nConfirm?"
            )

            send(chat_id, msg, keyboard())
            return "OK", 200

    except Exception as e:
        import traceback
        print(f"🚑 WEBHOOK ERROR: {e}")
        traceback.print_exc()
        return "Internal Server Error", 500

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)