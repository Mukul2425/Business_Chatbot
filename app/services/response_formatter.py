"""
Format responses for Telegram with operational action confirmations.
"""
from datetime import datetime, timedelta


def _now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_action_banner(action_type, status="confirmed"):
    """Format action execution banner."""
    icons = {
        "CallLead": "📞",
        "SaveToSheets": "📊",
        "BookCalendar": "📅",
        "SendWhatsApp": "💬",
        "CallTeam": "🚨",
    }
    icon = icons.get(action_type, "✅")
    now = _now_string()
    
    if status == "confirmed":
        return f"{icon} Action: {action_type} - CONFIRMED at {now}"
    elif status == "pending":
        return f"{icon} Action: {action_type} - PENDING at {now}"
    else:
        return f"{icon} Action: {action_type} - {status.upper()} at {now}"


def format_initial_greeting():
    """Initial greeting with lead capture intent."""
    return """🏠 Welcome to SpacesTalk!

Thank you for reaching out. We're here to help you create your perfect space.

To get started, please share:
1️⃣ Your full name
2️⃣ Phone number (for quick callback)
3️⃣ Location/Area
4️⃣ Space type (1BHK, 2BHK, 3BHK, Office, etc.)
5️⃣ Budget range
6️⃣ Timeline expectations

Let's begin! What's your name?"""


def format_lead_name_prompt():
    """Prompt for lead name."""
    return "What is your full name?"


def format_lead_phone_prompt():
    """Prompt for lead phone."""
    return "Thank you. Please share your 10-digit phone number for our callback."


def format_lead_location_prompt():
    """Prompt for lead location."""
    return "Which area or locality are you in? (e.g., Gurgaon, Delhi, Bangalore)"


def format_lead_space_type_prompt():
    """Prompt for space type."""
    return """What type of space do you need designed?

- 1 (1BHK)
- 2 (2BHK)
- 3 (3BHK)
- 4 (Office)
- 5 (Other - please specify)"""


def format_lead_budget_prompt():
    """Prompt for budget."""
    return """What's your budget range? (You can say something like: "5-10 lakhs" or "20 lakhs")

This helps us suggest designs within your comfort zone."""


def format_lead_timeline_prompt():
    """Prompt for timeline."""
    return """When are you looking to start/complete this project?

(e.g., "Within 2 months", "By June 2026", "ASAP")"""


def format_consultation_prompt():
    """Prompt for consultation agreement."""
    return """Would you like to book a consultation with our design team?

- 1️⃣ Yes, let's book a call
- 2️⃣ No, just exploring for now
- 3️⃣ Tell me more about the process"""


def format_consultation_datetime_prompt():
    """Prompt for preferred consultation date/time."""
    return """When would you prefer a consultation call?

Please share in format: DD-MMM-YYYY HH:MM
(e.g., 21-Apr-2026 14:30)

Our working hours: 10:00 AM - 6:00 PM (Mon-Sat)"""


def format_lead_captured(lead_name, lead_phone):
    """Confirmation message after lead capture."""
    return f"""✅ Lead Information Recorded!

Name: {lead_name}
Phone: {lead_phone}

Our team will review your details and connect with you shortly.

Thanks for choosing SpacesTalk. 🏠"""


def format_consultation_confirmed(lead_name, consultation_datetime):
    """WhatsApp-style confirmation for booked consultation."""
    return f"""Namaste {lead_name}! 🏠

Thank you for reaching out to SpacesTalk!

✅ Consultation booked for {consultation_datetime}
📍 Our team will contact you shortly

Looking forward to transforming your space!

— SpacesTalk ✨"""


def format_escalation_message():
    """Escalation confirmation to lead."""
    return """🚨 Escalating Your Request

Thanks for your patience. I have escalated your request to our senior team for priority attention.

A team specialist will contact you within the next hour to assist further.

— SpacesTalk Team"""


def format_call_team_notification(lead_name, reason):
    """Internal notification when lead is escalated to team."""
    return f"""
🚨 TEAM ALERT: Escalation Required

Lead: {lead_name}
Reason: {reason}

⏱️ Priority: HIGH
🎯 Action: Team member should contact lead within 1 hour

Status: PENDING HUMAN RESPONSE
"""


def format_call_lead_initiated(lead_name, lead_phone):
    """Notification that CallLead has been triggered."""
    return f"""📞 INITIATED: CallLead Trigger

Lead: {lead_name}
Phone: {lead_phone}
⏰ Aria will call within 3 minutes

Status: IN PROGRESS"""


def format_save_to_sheets_confirmation(lead_name):
    """Confirmation that data was saved to sheets."""
    return f"""📊 SAVED: Lead Data to Google Sheets

Lead: {lead_name}
✅ All details synced to team dashboard

Team visibility: ACTIVE"""


def format_book_calendar_confirmation(lead_name, datetime_str):
    """Confirmation that consultation was booked to calendar."""
    return f"""📅 BOOKED: Consultation Calendar Entry

Lead: {lead_name}
Date/Time: {datetime_str}
⏰ Reminder: 1 hour before ({calculate_reminder_time(datetime_str)})

Status: CONFIRMED & SYNCED"""


def calculate_reminder_time(datetime_str):
    """Calculate 1 hour before datetime string."""
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        reminder = dt - timedelta(hours=1)
        return reminder.strftime("%H:%M")
    except:
        return "N/A"


def format_workflow_error():
    """Error message when something goes wrong."""
    return """❌ Something went wrong.

Please try again or contact us directly:
📞 +91-9876543119

We're here to help! 🏠"""


def format_not_interior_query():
    """Response for non-interior-design queries."""
    return """I'm here specifically to help with interior design questions for SpacesTalk.

For other inquiries, please contact us at:
📞 +91-9876543119
📧 info@spacestalk.com"""


def format_human_handoff():
    """Message when conversation is handed to human."""
    return """🤝 Connecting You to Our Team

Our human team member will take over shortly to provide personalized assistance.

⏳ Please wait while we connect you..."""


def format_contact_info():
    """Format contact information"""
    return """Here is how you can reach SpacesTalk:

- Phone: +91-9876543119
- Email: info@spacestalk.com
- Location: Gurgaon, Haryana
- Hours: 10 AM to 7 PM
- Service Region: Delhi NCR and nearby areas"""


def format_contact_timing_reply():
    """Format response for contact timing/hours queries"""
    return """We're available for consultations during:

📞 Business Hours: 10 AM to 7 PM (Monday to Saturday)

Contact us:
- Phone: +91-9876543119
- Email: info@spacestalk.com

You can call us within these hours, or drop an email anytime and we'll get back to you soon!"""


def wrap_markdown(text):
    """Wrap text safely for Telegram markdown"""
    return text.replace("_", "\\_").replace("*", "\\*")
