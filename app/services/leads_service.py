"""Leads management service with CSV persistence."""
import csv
import os
import re
from datetime import datetime


captured_leads = []
LEADS_CSV_PATH = os.path.join("data", "leads.csv")
VALID_STATUSES = {"new", "contacted", "qualified", "converted"}


def _ensure_leads_file():
    os.makedirs(os.path.dirname(LEADS_CSV_PATH), exist_ok=True)
    if not os.path.exists(LEADS_CSV_PATH):
        with open(LEADS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Name", "Phone", "Location", "Space Type", "Budget", 
                    "Timeline", "Consultation Agreed", "Preferred Date/Time",
                    "Timestamp", "Status", "Call Attempts", "Last Call Attempt"
                ],
            )
            writer.writeheader()


def _normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 13 and digits.startswith("091"):
        return f"+91{digits[3:]}"
    return None


def is_valid_phone(phone):
    return _normalize_phone(phone) is not None


def capture_lead(name, phone, location, space_type="General", budget=None, 
                 timeline=None, consultation_agreed=False, preferred_datetime=None):
    """Capture comprehensive lead information in memory and CSV file."""
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        raise ValueError("Invalid phone number")

    lead = {
        "name": (name or "").strip(),
        "phone": normalized_phone,
        "location": (location or "").strip(),
        "space_type": (space_type or "General").strip(),
        "budget": (budget or "").strip(),
        "timeline": (timeline or "").strip(),
        "consultation_agreed": consultation_agreed,
        "preferred_datetime": (preferred_datetime or "").strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "new",
        "call_attempts": 0,
        "last_call_attempt": None,
    }
    captured_leads.append(lead)

    _ensure_leads_file()
    with open(LEADS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Name", "Phone", "Location", "Space Type", "Budget", 
                "Timeline", "Consultation Agreed", "Preferred Date/Time",
                "Timestamp", "Status", "Call Attempts", "Last Call Attempt"
            ],
        )
        writer.writerow(
            {
                "Name": lead["name"],
                "Phone": lead["phone"],
                "Location": lead["location"],
                "Space Type": lead["space_type"],
                "Budget": lead["budget"],
                "Timeline": lead["timeline"],
                "Consultation Agreed": lead["consultation_agreed"],
                "Preferred Date/Time": lead["preferred_datetime"],
                "Timestamp": lead["timestamp"],
                "Status": lead["status"],
                "Call Attempts": lead["call_attempts"],
                "Last Call Attempt": lead["last_call_attempt"],
            }
        )

    print(f"Lead captured: {lead['name']} - {lead['phone']} ({lead['space_type']})")
    return lead


def get_all_leads():
    """Get all captured leads"""
    return captured_leads


def update_lead_status(phone, new_status):
    """Update lead status (new, contacted, qualified, converted)."""
    if new_status not in VALID_STATUSES:
        return None
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None

    for lead in captured_leads:
        if lead["phone"] == normalized_phone:
            lead["status"] = new_status
            return lead
    return None


def get_leads_by_status(status):
    """Get leads filtered by status"""
    return [lead for lead in captured_leads if lead["status"] == status]


def update_lead_call_attempt(phone):
    """Record a call attempt for a lead."""
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None
    
    for lead in captured_leads:
        if lead["phone"] == normalized_phone:
            lead["call_attempts"] = lead.get("call_attempts", 0) + 1
            lead["last_call_attempt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return lead
    return None


def update_lead_consultation(phone, consultation_agreed, preferred_datetime=None):
    """Update consultation agreement status for a lead."""
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None
    
    for lead in captured_leads:
        if lead["phone"] == normalized_phone:
            lead["consultation_agreed"] = consultation_agreed
            if preferred_datetime:
                lead["preferred_datetime"] = preferred_datetime
            return lead
    return None


def get_lead_by_phone(phone):
    """Retrieve a lead by phone number."""
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None
    
    for lead in captured_leads:
        if lead["phone"] == normalized_phone:
            return lead
    return None


def format_lead_message(lead):
    """Format lead for display"""
    return f"""
👤 **{lead['name']}**
📱 {lead['phone']}
📍 {lead['location']}
🏠 Space Type: {lead['space_type']}
💰 Budget: {lead.get('budget', 'N/A')}
⏱️ Timeline: {lead.get('timeline', 'N/A')}
📅 Consultation Agreed: {lead.get('consultation_agreed', False)}
🕐 Preferred: {lead.get('preferred_datetime', 'N/A')}
⏰ {lead['timestamp']}
🏷️ Status: {lead['status'].upper()}
📞 Call Attempts: {lead.get('call_attempts', 0)}
"""
