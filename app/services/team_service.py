"""Team escalation service for handling special lead conditions."""
from datetime import datetime
import json
import os
import re


ESCALATIONS_FILE = os.path.join("data", "escalations.json")
ESCALATIONS = []

BUDGET_ESCALATION_THRESHOLD = 20_00_000  # 20 lakhs

HUMAN_REQUEST_MARKERS = (
    "talk to human",
    "real person",
    "human agent",
    "connect me to team",
    "speak to someone",
    "call me now",
    "agent",
    "representative",
)

FRUSTRATION_MARKERS = (
    "frustrated",
    "angry",
    "upset",
    "worst",
    "pathetic",
    "not happy",
    "terrible",
    "useless",
    "waste",
)


def _ensure_escalations_file():
    global ESCALATIONS
    os.makedirs(os.path.dirname(ESCALATIONS_FILE), exist_ok=True)
    if not os.path.exists(ESCALATIONS_FILE):
        with open(ESCALATIONS_FILE, "w") as f:
            json.dump([], f)
    elif len(ESCALATIONS) == 0:
        # Only load from file if we haven't already loaded/modified it
        with open(ESCALATIONS_FILE, "r") as f:
            try:
                ESCALATIONS = json.load(f)
            except:
                ESCALATIONS = []


def _save_escalations():
    _ensure_escalations_file()
    with open(ESCALATIONS_FILE, "w") as f:
        json.dump(ESCALATIONS, f, indent=2)


def _extract_budget_rupees(text):
    """Extract rough budget estimate in rupees from free-text."""
    t = (text or "").lower().replace(",", "")

    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|l|lac|lacs)", t)
    if lakh_match:
        return int(float(lakh_match.group(1)) * 100000)

    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(crore|crores|cr)", t)
    if crore_match:
        return int(float(crore_match.group(1)) * 10000000)

    raw_num_match = re.search(r"\b(\d{6,9})\b", t)
    if raw_num_match:
        return int(raw_num_match.group(1))

    return None


def detect_escalation_reason(user_input, lead_phone=None):
    """
    Detect if lead should be escalated to team.
    Returns reason string or None.
    """
    text = (user_input or "").lower()

    if any(marker in text for marker in HUMAN_REQUEST_MARKERS):
        return "Lead requested human representative"

    if any(marker in text for marker in FRUSTRATION_MARKERS):
        return "Lead appears frustrated or angry"

    budget = _extract_budget_rupees(user_input)
    if budget and budget >= BUDGET_ESCALATION_THRESHOLD:
        return f"Budget above threshold (₹{budget:,})"

    return None


def create_escalation(lead_phone, lead_name, reason, context_data=None):
    """Create an escalation ticket for the team."""
    _ensure_escalations_file()
    
    escalation = {
        "id": f"escalation_{lead_phone}_{int(datetime.now().timestamp())}",
        "lead_phone": lead_phone,
        "lead_name": lead_name,
        "reason": reason,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
        "context": context_data or {},
    }
    
    ESCALATIONS.append(escalation)
    _save_escalations()
    
    print(f"🚨 Escalation created: {lead_name} ({lead_phone}) - {reason}")
    return escalation


def get_escalations_by_status(status="pending"):
    """Get escalations filtered by status."""
    _ensure_escalations_file()
    return [e for e in ESCALATIONS if e["status"] == status]


def mark_escalation_handled(escalation_id):
    """Mark an escalation as handled by team."""
    _ensure_escalations_file()
    for e in ESCALATIONS:
        if e["id"] == escalation_id:
            e["status"] = "handled"
            e["handled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _save_escalations()
            return e
    return None


def format_escalation_summary(escalation):
    """Format escalation details for team."""
    return f"""
🚨 ESCALATION: {escalation['reason']}

Lead: {escalation['lead_name']}
Phone: {escalation['lead_phone']}
Created: {escalation['created_at']}
Status: {escalation['status'].upper()}

Context: {json.dumps(escalation['context'], indent=2)}
"""
