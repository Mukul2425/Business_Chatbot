"""Hybrid conversation flow: assistant Q&A + operational lead workflow."""
from datetime import datetime

from app.services.faq_service import search_faq
from app.services.semantic_service import search_semantic, confidence_level, generate_clarifying_question
from app.services.knowledge_base_service import search_knowledge_base
from app.services.gemini_service import ask_gemini
from app.services.leads_service import capture_lead, is_valid_phone
from app.services.calendar_service import book_calendar
from app.services.team_service import detect_escalation_reason, create_escalation
from app.services.call_retry_service import schedule_call
from app.services.response_formatter import (
    format_consultation_confirmed,
    format_lead_captured,
    format_contact_info,
    format_escalation_message,
)


MAX_GEMINI_CALLS_PER_CHAT = 2


def get_initial_message():
    return (
        "Welcome to SpacesTalk. I can help with interior design queries, pricing guidance, "
        "materials, timelines, and booking consultations.\n\n"
        "You can ask a question directly, or type: book consultation"
    )


def _is_greeting(text):
    msg = (text or "").strip().lower()
    return msg in {"hi", "hello", "hey", "hii", "good morning", "good evening", "good afternoon"}


def _is_booking_intent(text):
    msg = (text or "").lower()
    keywords = [
        "book consultation",
        "book a consultation",
        "book call",
        "schedule consultation",
        "schedule call",
        "appointment",
        "callback",
        "call me",
    ]
    return any(k in msg for k in keywords)


def _is_interior_query(text):
    msg = (text or "").lower()
    keywords = [
        "interior", "design", "home", "office", "kitchen", "wardrobe", "false ceiling", "lighting",
        "budget", "price", "pricing", "timeline", "consultation", "materials", "furniture", "renovation",
        "1bhk", "2bhk", "3bhk", "bhk",
    ]
    return any(k in msg for k in keywords)


def _parse_yes_no(text):
    msg = (text or "").strip().lower()
    if msg in {"yes", "y", "1", "yeah", "yep"}:
        return True
    if msg in {"no", "n", "2", "not now", "later"}:
        return False
    return None


def _validate_consultation_dt(date_str):
    try:
        dt = datetime.strptime((date_str or "").strip(), "%d-%b-%Y %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _start_lead_capture(state):
    state["current_step"] = "lead_capture"
    state["lead_stage"] = "name"
    return (
        "Great. I can help book your consultation.\n\n"
        "Please share your full name."
    )


def _run_assistant_answer(state, user_input):
    faq_answer = search_faq(user_input)
    if faq_answer:
        return faq_answer

    semantic_answer, semantic_question, semantic_score = search_semantic(user_input, threshold=0.35)
    conf = confidence_level(semantic_score)
    if conf == "high":
        return semantic_answer
    if conf == "medium":
        clarifying = generate_clarifying_question(user_input)
        return f"One quick clarification before I answer:\n\n{clarifying}"

    kb_answer, kb_source, kb_score = search_knowledge_base(user_input, threshold=0.35)
    kb_conf = confidence_level(kb_score)
    if kb_conf == "high":
        return f"From our knowledge base ({kb_source}):\n\n{kb_answer}"
    if kb_conf == "medium":
        clarifying = generate_clarifying_question(user_input)
        return f"I found partial info. Could you clarify this first?\n\n{clarifying}"

    if not _is_interior_query(user_input):
        return (
            "I can best help with interior design and consultation queries for SpacesTalk.\n\n"
            + format_contact_info()
        )

    if int(state.get("gemini_calls", 0)) >= MAX_GEMINI_CALLS_PER_CHAT:
        return (
            "I could not find a confident answer in current data. "
            "If you want, I can connect you to our team or book a consultation."
        )

    llm_response = ask_gemini(
        user_input,
        current_step=state.get("current_step"),
        selected_category=state.get("lead_space_type"),
    )
    state["gemini_calls"] = int(state.get("gemini_calls", 0)) + 1
    return llm_response


def _maybe_escalate(state, user_input):
    reason = detect_escalation_reason(user_input, state.get("lead_phone"))
    if not reason:
        return None
    if state.get("escalation_triggered"):
        return None

    state["escalation_triggered"] = True
    create_escalation(
        state.get("lead_phone") or "unknown",
        state.get("lead_name") or "Unknown Lead",
        reason,
        {
            "space_type": state.get("lead_space_type"),
            "budget": state.get("lead_budget"),
            "timeline": state.get("lead_timeline"),
            "latest_user_message": user_input,
        },
    )
    return format_escalation_message()


def process_message(chat_id, user_input, user_state):
    if chat_id not in user_state:
        user_state[chat_id] = {
            "current_step": "assistant",
            "lead_stage": None,
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
            "gemini_calls": 0,
        }

    state = user_state[chat_id]
    text = (user_input or "").strip()

    if state.get("current_step") == "lead_capture":
        stage = state.get("lead_stage")

        if stage == "name":
            state["lead_name"] = text
            state["lead_stage"] = "phone"
            return "Thank you. Please share your 10-digit phone number.", user_state

        if stage == "phone":
            if not is_valid_phone(text):
                return "Please enter a valid 10-digit Indian phone number.", user_state

            state["lead_phone"] = text
            state["lead_stage"] = "location"

            if not state.get("call_lead_triggered"):
                schedule_call(state["lead_phone"], state.get("lead_name") or "Lead")
                state["call_lead_triggered"] = True

            return "Please share your location/area.", user_state

        if stage == "location":
            state["lead_location"] = text
            state["lead_stage"] = "space_type"
            return "What space type should we plan for? (1BHK/2BHK/3BHK/Office/Other)", user_state

        if stage == "space_type":
            state["lead_space_type"] = text
            state["lead_stage"] = "budget"
            return "Please share your budget range.", user_state

        if stage == "budget":
            state["lead_budget"] = text
            state["lead_stage"] = "timeline"
            escalation_msg = _maybe_escalate(state, text)
            response = "What is your expected timeline?"
            if escalation_msg:
                response = response + "\n\n" + escalation_msg
            return response, user_state

        if stage == "timeline":
            state["lead_timeline"] = text
            state["lead_stage"] = "consultation_agreed"
            return "Would you like to book a consultation call? (yes/no)", user_state

        if stage == "consultation_agreed":
            agreed = _parse_yes_no(text)
            if agreed is None:
                return "Please reply with yes or no for consultation booking.", user_state
            state["lead_consultation_agreed"] = agreed
            if agreed:
                state["lead_stage"] = "consultation_datetime"
                return "Please share preferred date/time in format DD-MMM-YYYY HH:MM", user_state

            capture_lead(
                name=state.get("lead_name"),
                phone=state.get("lead_phone"),
                location=state.get("lead_location"),
                space_type=state.get("lead_space_type"),
                budget=state.get("lead_budget"),
                timeline=state.get("lead_timeline"),
                consultation_agreed=False,
                preferred_datetime=None,
            )
            state["current_step"] = "assistant"
            state["lead_stage"] = None
            return (
                format_lead_captured(state.get("lead_name"), state.get("lead_phone"))
                + "\n\nMeanwhile, feel free to ask any design or pricing question."
            ), user_state

        if stage == "consultation_datetime":
            normalized = _validate_consultation_dt(text)
            if not normalized:
                return "Invalid format. Please use DD-MMM-YYYY HH:MM (example: 25-Apr-2026 14:30)", user_state

            state["lead_consultation_datetime"] = normalized

            capture_lead(
                name=state.get("lead_name"),
                phone=state.get("lead_phone"),
                location=state.get("lead_location"),
                space_type=state.get("lead_space_type"),
                budget=state.get("lead_budget"),
                timeline=state.get("lead_timeline"),
                consultation_agreed=True,
                preferred_datetime=normalized,
            )

            booked = book_calendar(state.get("lead_name"), state.get("lead_phone"), normalized)
            state["current_step"] = "assistant"
            state["lead_stage"] = None

            parts = []
            if booked:
                parts.append("Action confirmed: BookCalendar completed.")
            parts.append(format_consultation_confirmed(state.get("lead_name"), normalized))
            parts.append("Action confirmed: SaveToSheets completed.")
            parts.append("You can continue asking any question. I am here to help.")
            return "\n\n".join(parts), user_state

    if _is_greeting(text):
        return get_initial_message(), user_state

    if text.lower() in {"help", "contact", "phone", "email"}:
        return format_contact_info(), user_state

    escalation_msg = _maybe_escalate(state, text)
    if escalation_msg:
        return escalation_msg, user_state

    if _is_booking_intent(text):
        return _start_lead_capture(state), user_state

    assistant_reply = _run_assistant_answer(state, text)
    return assistant_reply, user_state
