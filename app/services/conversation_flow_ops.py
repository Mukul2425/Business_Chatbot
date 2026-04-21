"""
Operational conversation flow for SpacesTalk lead management.

Priority Order (from the system prompt):
1. Call lead within 3 minutes ⚡
2. Save data to Sheets 📊
3. Book calendar if agreed 📅
4. Send WhatsApp confirmation 💬
5. Call team if needed 📞
"""
from datetime import datetime
from app.services.response_formatter import (
    format_initial_greeting,
    format_lead_name_prompt,
    format_lead_phone_prompt,
    format_lead_location_prompt,
    format_lead_space_type_prompt,
    format_lead_budget_prompt,
    format_lead_timeline_prompt,
    format_consultation_prompt,
    format_consultation_datetime_prompt,
    format_lead_captured,
    format_consultation_confirmed,
    format_escalation_message,
    format_contact_info,
)
from app.services.leads_service import capture_lead, is_valid_phone
from app.services.calendar_service import book_calendar
from app.services.team_service import detect_escalation_reason, create_escalation
from app.services.call_retry_service import schedule_call


def _validate_date_input(date_str):
    """Validate date format DD-MMM-YYYY HH:MM"""
    try:
        dt = datetime.strptime(date_str.strip(), "%d-%b-%Y %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def process_message(chat_id, user_input, user_state):
    """
    Main operational flow:
    1. Immediately trigger CallLead
    2. Capture lead details through guided flow
    3. Save to sheets once complete
    4. Book calendar if agreed
    5. Escalate if needed
    6. Send confirmations
    """
    
    # Initialize user state if new
    if chat_id not in user_state:
        user_state[chat_id] = {
            "current_step": "greeting",
            "lead_name": None,
            "lead_phone": None,
            "lead_location": None,
            "lead_space_type": None,
            "lead_budget": None,
            "lead_timeline": None,
            "lead_consultation_agreed": None,
            "lead_consultation_datetime": None,
            "call_lead_triggered": False,
            "escalation_triggered": False,
        }
    
    state = user_state[chat_id]
    user_input = user_input.strip()
    
    # ============================================
    # PRIORITY 1: Call lead within 3 minutes
    # ============================================
    if not state.get("call_lead_triggered"):
        state["call_lead_triggered"] = True
        try:
            # Schedule call in retry queue
            if state.get("lead_phone"):
                schedule_call(
                    state.get("lead_phone"),
                    state.get("lead_name") or "Lead"
                )
        except:
            pass  # Call scheduling is background task
    
    # ============================================
    # Conversation Flow States
    # ============================================
    
    if state.get("current_step") == "greeting":
        # First message - advance to name collection and process input
        state["current_step"] = "name"
        # Fall through to process name below
    
    if state.get("current_step") == "name":
        state["lead_name"] = user_input
        state["current_step"] = "phone"
        return format_lead_phone_prompt(), user_state
    
    elif state.get("current_step") == "phone":
        if not is_valid_phone(user_input):
            return "Please enter a valid 10-digit Indian phone number.", user_state
        
        state["lead_phone"] = user_input
        state["current_step"] = "location"
        
        # Now that we have phone, trigger CallLead
        try:
            schedule_call(state["lead_phone"], state["lead_name"])
        except:
            pass
        
        return format_lead_location_prompt(), user_state
    
    elif state.get("current_step") == "location":
        state["lead_location"] = user_input
        state["current_step"] = "space_type"
        return format_lead_space_type_prompt(), user_state
    
    elif state.get("current_step") == "space_type":
        space_mapping = {
            "1": "1BHK", "2": "2BHK", "3": "3BHK", "4": "Office",
            "1bhk": "1BHK", "2bhk": "2BHK", "3bhk": "3BHK", "office": "Office"
        }
        
        space_type = space_mapping.get(user_input.lower(), user_input)
        state["lead_space_type"] = space_type
        state["current_step"] = "budget"
        return format_lead_budget_prompt(), user_state
    
    elif state.get("current_step") == "budget":
        state["lead_budget"] = user_input
        state["current_step"] = "timeline"
        return format_lead_timeline_prompt(), user_state
    
    elif state.get("current_step") == "timeline":
        state["lead_timeline"] = user_input
        state["current_step"] = "consultation"
        return format_consultation_prompt(), user_state
    
    elif state.get("current_step") == "consultation":
        response = user_input.lower()
        
        if response in ["1", "yes", "yeah", "yep"]:
            state["lead_consultation_agreed"] = True
            state["current_step"] = "consultation_datetime"
            return format_consultation_datetime_prompt(), user_state
        else:
            state["lead_consultation_agreed"] = False
            state["current_step"] = "complete"
            return _process_lead_complete(chat_id, state, user_state)
    
    elif state.get("current_step") == "consultation_datetime":
        validated_datetime = _validate_date_input(user_input)
        
        if not validated_datetime:
            return "Please enter date in format: DD-MMM-YYYY HH:MM\nExample: 21-Apr-2026 14:30", user_state
        
        state["lead_consultation_datetime"] = validated_datetime
        state["current_step"] = "complete"
        return _process_lead_complete(chat_id, state, user_state)
    
    elif state.get("current_step") == "complete":
        # Lead flow already completed, offer contact info
        return format_contact_info(), user_state
    
    return "Please start over or type 'help' for assistance.", user_state


def _process_lead_complete(chat_id, state, user_state):
    """
    Handle lead completion:
    1. Save to sheets
    2. Book calendar if agreed
    3. Send confirmation
    4. Escalate if needed
    """
    
    # ============================================
    # PRIORITY 2: Save data to Sheets
    # ============================================
    try:
        lead = capture_lead(
            name=state.get("lead_name"),
            phone=state.get("lead_phone"),
            location=state.get("lead_location"),
            space_type=state.get("lead_space_type"),
            budget=state.get("lead_budget"),
            timeline=state.get("lead_timeline"),
            consultation_agreed=state.get("lead_consultation_agreed", False),
            preferred_datetime=state.get("lead_consultation_datetime")
        )
    except Exception as e:
        print(f"Error saving lead: {e}")
        return f"Error saving lead. Please contact us at +91-9876543119", user_state
    
    confirmation_parts = []
    
    # ============================================
    # PRIORITY 3: Book calendar if agreed
    # ============================================
    if state.get("lead_consultation_agreed"):
        try:
            booking = book_calendar(
                state.get("lead_name"),
                state.get("lead_phone"),
                state.get("lead_consultation_datetime")
            )
            if booking:
                state["booking_id"] = booking["id"]
                confirmation_parts.append("✅ Consultation booked successfully!")
        except Exception as e:
            print(f"Error booking calendar: {e}")
            confirmation_parts.append("⚠️ Calendar booking pending confirmation")
    
    # ============================================
    # PRIORITY 4: Send confirmation
    # ============================================
    if state.get("lead_consultation_agreed") and state.get("lead_consultation_datetime"):
        confirmation_parts.append(
            format_consultation_confirmed(
                state.get("lead_name"),
                state.get("lead_consultation_datetime")
            )
        )
    else:
        confirmation_parts.append(
            format_lead_captured(
                state.get("lead_name"),
                state.get("lead_phone")
            )
        )
    
    # ============================================
    # PRIORITY 5: Call team if needed
    # ============================================
    escalation_reason = detect_escalation_reason(
        user_state.get(chat_id, {}).get("user_input", ""),
        state.get("lead_phone")
    )
    
    if not escalation_reason and state.get("lead_budget"):
        escalation_reason = detect_escalation_reason(
            state.get("lead_budget"),
            state.get("lead_phone")
        )
    
    if escalation_reason and not state.get("escalation_triggered"):
        state["escalation_triggered"] = True
        try:
            create_escalation(
                state.get("lead_phone"),
                state.get("lead_name"),
                escalation_reason,
                {
                    "space_type": state.get("lead_space_type"),
                    "budget": state.get("lead_budget"),
                    "timeline": state.get("lead_timeline"),
                }
            )
            confirmation_parts.append(format_escalation_message())
        except Exception as e:
            print(f"Error creating escalation: {e}")
    
    final_response = "\n".join(confirmation_parts)
    state["current_step"] = "complete"
    return final_response, user_state


def get_initial_message():
    """Get initial message when user first starts."""
    return format_initial_greeting()
