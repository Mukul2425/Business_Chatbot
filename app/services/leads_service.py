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
                fieldnames=["Name", "Phone", "Location", "Requirement", "Timestamp", "Status"],
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


def capture_lead(name, phone, location, requirement="General inquiry"):
    """Capture lead information in memory and CSV file."""
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        raise ValueError("Invalid phone number")

    lead = {
        "name": (name or "").strip(),
        "phone": normalized_phone,
        "location": (location or "").strip(),
        "requirement": (requirement or "General inquiry").strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "new",
    }
    captured_leads.append(lead)

    _ensure_leads_file()
    with open(LEADS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Name", "Phone", "Location", "Requirement", "Timestamp", "Status"],
        )
        writer.writerow(
            {
                "Name": lead["name"],
                "Phone": lead["phone"],
                "Location": lead["location"],
                "Requirement": lead["requirement"],
                "Timestamp": lead["timestamp"],
                "Status": lead["status"],
            }
        )

    print(f"Lead captured: {lead['name']} - {lead['phone']}")
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


def format_lead_message(lead):
    """Format lead for display"""
    return f"""
👤 **{lead['name']}**
📱 {lead['phone']}
📍 {lead['location']}
❓ {lead['requirement']}
⏰ {lead['timestamp']}
🏷️ Status: {lead['status'].upper()}
"""
