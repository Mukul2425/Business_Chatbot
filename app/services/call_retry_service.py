"""Call retry service for handling unanswered lead calls."""
from datetime import datetime, timedelta
import json
import os


CALL_QUEUE_FILE = os.path.join("data", "call_queue.json")
CALL_QUEUE = []

MAX_CALL_ATTEMPTS = 3
RETRY_INTERVAL_MINUTES = 10


def _ensure_queue_file():
    global CALL_QUEUE
    os.makedirs(os.path.dirname(CALL_QUEUE_FILE), exist_ok=True)
    if not os.path.exists(CALL_QUEUE_FILE):
        with open(CALL_QUEUE_FILE, "w") as f:
            json.dump([], f)
    elif len(CALL_QUEUE) == 0:
        # Only load from file if we haven't already loaded/modified it
        with open(CALL_QUEUE_FILE, "r") as f:
            try:
                CALL_QUEUE = json.load(f)
            except:
                CALL_QUEUE = []


def _save_queue():
    _ensure_queue_file()
    with open(CALL_QUEUE_FILE, "w") as f:
        json.dump(CALL_QUEUE, f, indent=2)


def schedule_call(lead_phone, lead_name):
    """Schedule a call attempt for a lead."""
    _ensure_queue_file()
    
    call_entry = {
        "id": f"call_{lead_phone}_{int(datetime.now().timestamp())}",
        "lead_phone": lead_phone,
        "lead_name": lead_name,
        "attempt_number": 1,
        "max_attempts": MAX_CALL_ATTEMPTS,
        "first_attempt_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_attempted_at": None,
        "next_retry_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",  # pending, in_progress, answered, failed
        "call_logs": [],
    }
    
    CALL_QUEUE.append(call_entry)
    _save_queue()
    
    print(f"📞 Call scheduled for {lead_name} ({lead_phone}) - Attempt 1/3")
    return call_entry


def mark_call_started(call_id):
    """Mark a call as in progress."""
    _ensure_queue_file()
    for call in CALL_QUEUE:
        if call["id"] == call_id:
            call["status"] = "in_progress"
            call["last_attempted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _save_queue()
            return call
    return None


def mark_call_answered(call_id):
    """Mark a call as answered (successful)."""
    _ensure_queue_file()
    for call in CALL_QUEUE:
        if call["id"] == call_id:
            call["status"] = "answered"
            call["call_logs"].append({
                "attempt": call["attempt_number"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": "answered",
            })
            _save_queue()
            print(f"✅ Call answered: {call['lead_name']}")
            return call
    return None


def mark_call_unanswered(call_id):
    """Mark a call as unanswered and schedule retry if attempts remain."""
    _ensure_queue_file()
    for call in CALL_QUEUE:
        if call["id"] == call_id:
            call["call_logs"].append({
                "attempt": call["attempt_number"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": "unanswered",
            })
            
            if call["attempt_number"] < call["max_attempts"]:
                # Schedule next retry
                next_retry = datetime.now() + timedelta(minutes=RETRY_INTERVAL_MINUTES)
                call["attempt_number"] += 1
                call["next_retry_at"] = next_retry.strftime("%Y-%m-%d %H:%M:%S")
                call["status"] = "pending"
                _save_queue()
                print(f"⏱️ Retry scheduled for {call['lead_name']} - Attempt {call['attempt_number']}/3 at {call['next_retry_at']}")
                return call
            else:
                # Max attempts reached
                call["status"] = "failed"
                _save_queue()
                print(f"❌ Call failed after 3 attempts: {call['lead_name']}")
                return call
    return None


def get_pending_calls():
    """Get all pending calls ready to be dialed now."""
    _ensure_queue_file()
    now = datetime.now()
    pending = []
    
    for call in CALL_QUEUE:
        if call["status"] == "pending":
            retry_dt = datetime.strptime(call["next_retry_at"], "%Y-%m-%d %H:%M:%S")
            if now >= retry_dt:
                pending.append(call)
    
    return pending


def process_due_calls(auto_mark_unanswered=True):
    """
    Process all due calls in queue.

    If auto_mark_unanswered=True, calls are marked unanswered immediately
    and retried/safely failed as per retry policy. This is a simulation-friendly
    default for automation in environments without telephony callbacks.
    """
    due_calls = get_pending_calls()
    processed = []

    for call in due_calls:
        call_id = call.get("id")
        started = mark_call_started(call_id)
        if not started:
            continue

        if auto_mark_unanswered:
            updated = mark_call_unanswered(call_id)
            if updated:
                processed.append(updated)
        else:
            processed.append(started)

    return processed


def get_call_history_by_phone(lead_phone):
    """Get call history for a lead."""
    _ensure_queue_file()
    calls = [c for c in CALL_QUEUE if c["lead_phone"] == lead_phone]
    return calls


def format_call_log(call):
    """Format call attempt details."""
    log_str = f"""
📞 Call Log: {call['lead_name']} ({call['lead_phone']})

Status: {call['status'].upper()}
Attempts: {call['attempt_number']}/{call['max_attempts']}
First Attempt: {call['first_attempt_at']}
Last Attempted: {call['last_attempted_at']}
Next Retry: {call['next_retry_at']}

Call History:
"""
    for log in call["call_logs"]:
        log_str += f"  Attempt {log['attempt']}: {log['result']} at {log['timestamp']}\n"
    
    return log_str
