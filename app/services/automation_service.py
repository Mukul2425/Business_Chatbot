"""Automation routines for reminders and call retries."""
from app.services.calendar_service import get_pending_reminders, mark_reminder_sent
from app.services.call_retry_service import process_due_calls
from app.bot.telegram import send_message


def run_automation_tick():
    """
    Process pending reminders and due call retries.

    Returns a small summary dict for logging/health endpoints.
    """
    reminders_sent = 0
    retries_processed = 0

    reminders = get_pending_reminders()
    for booking in reminders:
        chat_id = (booking.get("chat_id") or "").strip()
        if chat_id:
            msg = (
                f"Reminder: your SpacesTalk consultation is at {booking.get('consultation_datetime')}. "
                "We look forward to speaking with you."
            )
            try:
                send_message(int(chat_id), msg)
            except Exception:
                # Ignore delivery errors; we still mark this reminder to avoid repeated spam.
                pass
        mark_reminder_sent(booking.get("id"))
        reminders_sent += 1

    processed = process_due_calls(auto_mark_unanswered=True)
    retries_processed = len(processed)

    return {
        "reminders_sent": reminders_sent,
        "retries_processed": retries_processed,
    }
