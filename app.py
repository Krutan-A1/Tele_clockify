import os
import json
import threading
from difflib import get_close_matches

import requests
from flask import Flask, request
from dotenv import load_dotenv

from parser import parse_message
from clockify import get_projects, get_tasks, create_task, create_time_entry

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN").strip()
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

pending_context = {}
lock = threading.Lock()


# ---------------------------
# Helpers
# ---------------------------

def send(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)

    requests.post(f"{TELEGRAM_API_URL}/sendMessage", data=payload)


def answer(cb_id):
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", data={"callback_query_id": cb_id})


def keyboard():
    return {
        "inline_keyboard": [[
            {"text": "✅ Confirm", "callback_data": "confirm"},
            {"text": "❌ Cancel", "callback_data": "cancel"}
        ]]
    }


def norm(x):
    return (x or "").lower().strip()


def match(name, items):
    if not name:
        return None

    name = norm(name)
    mapping = {norm(i["name"]): i for i in items}

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
    data = request.get_json(silent=True) or {}
    print("🔥 Incoming:", json.dumps(data, indent=2))

    # MESSAGE
    if "message" in data and "text" in data["message"]:
        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"]["text"]

        projects = get_projects()
        project_names = [p["name"] for p in projects]

        parsed = parse_message(text, project_names)
        print("🧠 Parsed:", parsed)

        project = match(parsed.get("project"), projects)

        if not project:
            send(chat_id, f"❌ Project not found.\nTry: {', '.join(project_names[:5])}")
            return "OK", 200

        tasks = get_tasks(project["id"])

        task = match(parsed.get("task"), tasks)

        if not task:
            # auto create task
            new_task = create_task(project["id"], parsed.get("task") or "General")
            task_id = new_task["id"]
            task_name = new_task["name"]
        else:
            task_id = task["id"]
            task_name = task["name"]

        pending_context[chat_id] = {
            "parsed": parsed,
            "project": project,
            "task": {"id": task_id, "name": task_name}
        }

        msg = (
            f"📂 {project['name']}\n"
            f"📝 {task_name}\n"
            f"⏱ {parsed['duration_minutes']} mins\n"
            f"📖 {parsed['description']}\n\nConfirm?"
        )

        send(chat_id, msg, keyboard())
        return "OK", 200

    # BUTTON
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = str(cb["message"]["chat"]["id"])
        action = cb["data"]

        answer(cb["id"])

        pending = pending_context.get(chat_id)

        if not pending:
            send(chat_id, "❌ No pending task")
            return "OK", 200

        if action == "cancel":
            pending_context.pop(chat_id, None)
            send(chat_id, "❌ Cancelled")
            return "OK", 200

        if action == "confirm":
            payload = {
                "description": pending["parsed"]["description"],
                "duration_minutes": pending["parsed"]["duration_minutes"],
                "projectId": pending["project"]["id"],
                "taskId": pending["task"]["id"]
            }

            status, resp = create_time_entry(payload)

            if 200 <= status < 300:
                send(chat_id, "✅ Entry created")
                pending_context.pop(chat_id, None)
            else:
                send(chat_id, f"❌ Failed:\n{resp}")

        return "OK", 200

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)