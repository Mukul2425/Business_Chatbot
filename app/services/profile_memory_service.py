"""Persistent profile memory for chat continuity across restarts."""
import json
import os
from datetime import datetime


PROFILES_FILE = os.path.join("data", "chat_profiles.json")
_CACHE = None


def _ensure_file():
    os.makedirs(os.path.dirname(PROFILES_FILE), exist_ok=True)
    if not os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


def _load_cache():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    _ensure_file()
    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        try:
            _CACHE = json.load(f)
        except json.JSONDecodeError:
            _CACHE = {}
    return _CACHE


def _save_cache():
    _ensure_file()
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(_CACHE or {}, f, indent=2, ensure_ascii=False)


def get_profile(chat_id):
    cache = _load_cache()
    return cache.get(str(chat_id))


def save_profile(chat_id, state):
    cache = _load_cache()
    profile = {
        "chat_id": str(chat_id),
        "lead_name": state.get("lead_name"),
        "lead_phone": state.get("lead_phone"),
        "lead_location": state.get("lead_location"),
        "lead_space_type": state.get("lead_space_type"),
        "lead_budget": state.get("lead_budget"),
        "lead_timeline": state.get("lead_timeline"),
        "lead_consultation_agreed": state.get("lead_consultation_agreed"),
        "lead_consultation_datetime": state.get("lead_consultation_datetime"),
        "language_pref": state.get("language_pref", "english"),
        "current_step": state.get("current_step", "assistant"),
        "lead_stage": state.get("lead_stage"),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    cache[str(chat_id)] = profile
    _save_cache()


def bootstrap_state(chat_id, default_state):
    """Load prior profile if available and merge into default session state."""
    profile = get_profile(chat_id)
    if not profile:
        return default_state

    merged = dict(default_state)
    for key in [
        "lead_name",
        "lead_phone",
        "lead_location",
        "lead_space_type",
        "lead_budget",
        "lead_timeline",
        "lead_consultation_agreed",
        "lead_consultation_datetime",
        "language_pref",
        "current_step",
        "lead_stage",
    ]:
        if profile.get(key) is not None:
            merged[key] = profile.get(key)

    # Always resume in assistant mode if a prior flow was left half-way.
    if merged.get("current_step") == "lead_capture" and not merged.get("lead_stage"):
        merged["current_step"] = "assistant"

    return merged
