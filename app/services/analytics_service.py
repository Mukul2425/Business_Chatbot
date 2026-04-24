"""Lightweight analytics events for conversation funnel tracking."""
from datetime import datetime
import json
import os


ANALYTICS_FILE = os.path.join("data", "analytics_events.jsonl")


def track_event(chat_id, event_name, metadata=None):
    os.makedirs(os.path.dirname(ANALYTICS_FILE), exist_ok=True)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chat_id": str(chat_id),
        "event": event_name,
        "metadata": metadata or {},
    }
    with open(ANALYTICS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def get_latest_events(limit=50):
    if not os.path.exists(ANALYTICS_FILE):
        return []
    with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    selected = lines[-limit:]
    output = []
    for line in selected:
        line = line.strip()
        if not line:
            continue
        try:
            output.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return output
