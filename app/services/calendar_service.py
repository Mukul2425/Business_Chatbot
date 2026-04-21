"""Calendar booking service for consultation scheduling."""
from datetime import datetime, timedelta
import json
import os


BOOKINGS_FILE = os.path.join("data", "calendar_bookings.json")
BOOKINGS = []


def _ensure_bookings_file():
    global BOOKINGS
    os.makedirs(os.path.dirname(BOOKINGS_FILE), exist_ok=True)
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "w") as f:
            json.dump([], f)
    elif len(BOOKINGS) == 0:
        # Only load from file if we haven't already loaded/modified it
        with open(BOOKINGS_FILE, "r") as f:
            try:
                BOOKINGS = json.load(f)
            except:
                BOOKINGS = []


def _save_bookings():
    _ensure_bookings_file()
    with open(BOOKINGS_FILE, "w") as f:
        json.dump(BOOKINGS, f, indent=2)


def book_calendar(lead_name, lead_phone, datetime_str):
    """
    Book a consultation in calendar and set reminder 1 hour before.
    
    datetime_str format: "2026-04-21 14:30" (YYYY-MM-DD HH:MM)
    
    Returns booking record or None if invalid.
    """
    try:
        booking_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        reminder_dt = booking_dt - timedelta(hours=1)
        
        booking = {
            "id": f"booking_{lead_phone}_{int(booking_dt.timestamp())}",
            "lead_name": lead_name,
            "lead_phone": lead_phone,
            "consultation_datetime": datetime_str,
            "reminder_datetime": reminder_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "confirmed",
            "reminder_sent": False,
        }
        
        _ensure_bookings_file()
        BOOKINGS.append(booking)
        _save_bookings()
        
        print(f"✅ Calendar booking confirmed: {lead_name} for {datetime_str}")
        return booking
    except ValueError as e:
        print(f"❌ Invalid datetime format: {e}")
        return None


def get_booking_by_phone(phone):
    """Retrieve booking for a lead by phone."""
    _ensure_bookings_file()
    for booking in BOOKINGS:
        if booking["lead_phone"] == phone and booking["status"] == "confirmed":
            return booking
    return None


def get_all_bookings():
    """Get all confirmed bookings."""
    _ensure_bookings_file()
    return [b for b in BOOKINGS if b["status"] == "confirmed"]


def get_pending_reminders():
    """Get bookings that need reminder sent (1 hour before consultation)."""
    _ensure_bookings_file()
    now = datetime.now()
    pending = []
    
    for booking in BOOKINGS:
        if booking["status"] == "confirmed" and not booking["reminder_sent"]:
            reminder_dt = datetime.strptime(booking["reminder_datetime"], "%Y-%m-%d %H:%M:%S")
            if now >= reminder_dt:
                pending.append(booking)
    
    return pending


def mark_reminder_sent(booking_id):
    """Mark reminder as sent for a booking."""
    _ensure_bookings_file()
    for booking in BOOKINGS:
        if booking["id"] == booking_id:
            booking["reminder_sent"] = True
            _save_bookings()
            return booking
    return None


def format_booking_confirmation(booking):
    """Format booking details for confirmation message."""
    return f"""
✅ Consultation Booked!

📅 Date & Time: {booking['consultation_datetime']}
⏰ Reminder: 1 hour before ({booking['reminder_datetime']})
👤 Consultant: SpacesTalk Team
📱 You'll receive a reminder at {booking['reminder_datetime']}

Looking forward to transforming your space!
"""
