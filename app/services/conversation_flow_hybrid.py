"""Hybrid conversation flow: assistant Q&A + operational lead workflow."""
from datetime import datetime

from app.services.faq_service import search_faq
from app.services.semantic_service import search_semantic, confidence_level, generate_clarifying_question
from app.services.knowledge_base_service import search_knowledge_base
from app.services.gemini_service import ask_gemini
from app.services.leads_service import capture_lead, is_valid_phone, lead_exists
from app.services.calendar_service import book_calendar, validate_consultation_slot
from app.services.team_service import detect_escalation_reason, create_escalation
from app.services.call_retry_service import schedule_call
from app.services.analytics_service import track_event
from app.services.response_formatter import (
    format_consultation_confirmed,
    format_lead_captured,
    format_contact_info,
    format_escalation_message,
)


MAX_GEMINI_CALLS_PER_CHAT = 2


def get_initial_message(state=None):
    if state and state.get("lead_name"):
        return (
            f"Welcome back {state.get('lead_name')}. I can continue helping with your interiors plan.\n\n"
            "You can ask a question directly, type 'book consultation', or type 'resume booking' if you want to continue where you left off."
        )

    return (
        "Hi, welcome to SpacesTalk. I can help with interior design ideas, pricing guidance, "
        "materials, timelines, and consultation booking.\n\n"
        "You can ask any question directly, or type 'book consultation' to start a call booking."
    )


def _detect_language_mode(text):
    msg = (text or "").strip().lower()
    if any("\u0900" <= ch <= "\u097f" for ch in msg):
        return "hindi"

    hinglish_markers = {
        "kya", "kaise", "kitna", "mujhe", "mera", "meri", "ghar", "karna", "chahiye", "hai", "nahi",
        "naam", "samay", "budget", "call", "book", "consultation",
    }
    tokens = set(msg.split())
    if tokens.intersection(hinglish_markers):
        return "hinglish"
    return "english"


def _localized(state, english, hinglish=None, hindi=None):
    mode = state.get("language_pref", "english")
    if mode == "hindi" and hindi:
        return hindi
    if mode in {"hindi", "hinglish"} and hinglish:
        return hinglish
    return english


def _is_greeting(text):
    msg = (text or "").strip().lower()
    return msg in {
        "hi", "hello", "hey", "hii", "good morning", "good evening", "good afternoon",
        "namaste", "namaskar", "salam", "assalamualaikum",
    }


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
        "consultation book",
        "call schedule",
        "consultation karni",
        "consultation book karna",
        "appointment book",
        "mujhe call chahiye",
    ]
    return any(k in msg for k in keywords)


def _is_cancel_booking_intent(text):
    msg = (text or "").strip().lower()
    return msg in {"cancel", "cancel booking", "stop booking", "abort booking", "booking cancel", "radd"}


def _is_resume_booking_intent(text):
    msg = (text or "").strip().lower()
    return msg in {"resume", "resume booking", "continue booking", "continue", "booking continue"}


def _parse_phone_edit_command(text):
    msg = (text or "").strip().lower()
    if msg.startswith("edit phone "):
        return text.strip()[11:]
    if msg.startswith("change phone "):
        return text.strip()[13:]
    return None


def _is_gratitude(text):
    msg = (text or "").strip().lower()
    return msg in {
        "thanks", "thank you", "thx", "thankyou", "shukriya", "dhanyawad", "dhanyavaad", "bahut shukriya",
    }


def _is_interior_query(text):
    msg = (text or "").lower()
    keywords = [
        "interior", "design", "home", "office", "kitchen", "wardrobe", "false ceiling", "lighting",
        "budget", "price", "pricing", "timeline", "consultation", "materials", "furniture", "renovation",
        "1bhk", "2bhk", "3bhk", "bhk",
    ]
    return any(k in msg for k in keywords)


def _extract_quick_intents(text):
    msg = (text or "").lower()
    intents = set()
    if any(k in msg for k in ["budget", "price", "pricing", "cost", "kitna", "daam"]):
        intents.add("budget")
    if any(k in msg for k in ["timeline", "time", "duration", "kab", "kitne din", "kitna samay"]):
        intents.add("timeline")
    if any(k in msg for k in ["material", "materials", "laminate", "plywood", "wood", "samagri"]):
        intents.add("materials")
    if any(k in msg for k in ["process", "steps", "kaise", "workflow", "execution"]):
        intents.add("process")
    return intents


def _quick_answer_templates(state, intents):
    if not intents:
        return None

    parts = []
    if "budget" in intents:
        parts.append(
            _localized(
                state,
                "Budget depends on space type, scope, and finish level. If you share your unit type and priorities, I can suggest a realistic bracket.",
                "Budget space type, scope, aur finish level par depend karta hai. Aap unit type aur priorities batao, main realistic bracket suggest kar dunga.",
                "Budget space type, scope, aur finish level par nirbhar karta hai. Aap unit type aur priorities batayein, main realistic bracket suggest kar dunga.",
            )
        )
    if "timeline" in intents:
        parts.append(
            _localized(
                state,
                "Typical interior execution is often completed in a few weeks after design freeze, depending on scope and material availability.",
                "Typical interior execution design freeze ke baad kuch hafton mein ho jata hai, scope aur material availability par depend karta hai.",
                "Typical interior execution design freeze ke baad kuch hafton mein ho jata hai, scope aur material availability par nirbhar karta hai.",
            )
        )
    if "materials" in intents:
        parts.append(
            _localized(
                state,
                "For cabinets, common options are BWP plywood with laminate, or premium veneer/acrylic based on budget and durability goals.",
                "Cabinets ke liye common options BWP plywood + laminate hote hain, ya premium veneer/acrylic budget aur durability goals ke hisaab se.",
                "Cabinets ke liye common options BWP plywood + laminate hote hain, ya premium veneer/acrylic budget aur durability goals ke anusaar.",
            )
        )
    if "process" in intents:
        parts.append(
            _localized(
                state,
                "Our process is: requirement understanding, design proposal, material finalization, execution, and handover.",
                "Hamare process mein requirement understanding, design proposal, material finalization, execution, aur handover aata hai.",
                "Hamare process mein requirement understanding, design proposal, material finalization, execution, aur handover shamil hai.",
            )
        )

    if not parts:
        return None
    return "\n\n".join(parts)


def _parse_yes_no(text):
    msg = (text or "").strip().lower()
    if msg in {"yes", "y", "1", "yeah", "yep"}:
        return True
    if msg in {"no", "n", "2", "not now", "later"}:
        return False
    return None


def _is_skip(text):
    msg = (text or "").strip().lower()
    return msg in {"skip", "na", "n/a", "not sure", "dont know", "don't know"}


def _validate_consultation_dt(date_str):
    try:
        dt = datetime.strptime((date_str or "").strip(), "%d-%b-%Y %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _normalize_space_type(text):
    value = (text or "").strip()
    if _is_skip(value):
        return "General"

    mapping = {
        "1": "1BHK",
        "2": "2BHK",
        "3": "3BHK",
        "4": "Office",
        "1bhk": "1BHK",
        "2bhk": "2BHK",
        "3bhk": "3BHK",
        "office": "Office",
    }
    return mapping.get(value.lower(), value)


def _start_lead_capture(state):
    state["current_step"] = "lead_capture"
    state["lead_stage"] = "name"
    return (
        "Perfect, I will help you book this quickly.\n\n"
        "First, may I have your full name?"
    )


def _run_assistant_answer(state, user_input):
    quick_intents = _extract_quick_intents(user_input)
    quick_answer = _quick_answer_templates(state, quick_intents)
    if quick_answer and len(quick_intents) >= 2:
        return quick_answer

    if _is_interior_query(user_input) and len(user_input.split()) <= 2:
        return _localized(
            state,
            "Could you share a little more detail so I can answer accurately?",
            "Thoda aur detail share karoge? Tab main accurate answer de paunga.",
            "Kripya thoda aur vivaran dein, tab main sahi jawab de paunga.",
        )

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
            "I mainly support interior design and consultation queries for SpacesTalk.\n\n"
            + format_contact_info()
        )

    if int(state.get("gemini_calls", 0)) >= MAX_GEMINI_CALLS_PER_CHAT:
        return (
            "I could not find a strong answer in current data right now. "
            "If you want, I can connect you to our team or book a consultation call."
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
            "language_pref": "english",
        }

    state = user_state[chat_id]
    text = (user_input or "").strip()
    state["language_pref"] = _detect_language_mode(text)

    if _is_cancel_booking_intent(text) and state.get("current_step") == "lead_capture":
        state["current_step"] = "assistant"
        state["lead_stage"] = None
        track_event(chat_id, "booking_cancelled")
        return _localized(
            state,
            "No problem, I have cancelled the booking flow. You can continue asking questions anytime.",
            "Theek hai, maine booking flow cancel kar diya. Aap ab normal questions pooch sakte hain.",
            "Theek hai, booking process cancel kar diya gaya hai. Aap ab sawal pooch sakte hain.",
        ), user_state

    if _is_resume_booking_intent(text):
        if state.get("current_step") == "lead_capture" and state.get("lead_stage"):
            return _localized(
                state,
                "Sure, let's continue your booking. Please continue from where we left off.",
                "Bilkul, booking continue karte hain. Jahan rukey the wahi se start karte hain.",
                "Bilkul, booking jaari rakhte hain. Jahan rukey the wahi se shuru karte hain.",
            ), user_state
        return _start_lead_capture(state), user_state

    if state.get("current_step") == "lead_capture":
        stage = state.get("lead_stage")

        edited_phone = _parse_phone_edit_command(text)
        if edited_phone is not None:
            if not is_valid_phone(edited_phone):
                return _localized(
                    state,
                    "That phone number looks invalid. Use: edit phone 9876543210",
                    "Yeh phone number valid nahi lag raha. Is format mein bhejein: edit phone 9876543210",
                    "Yeh phone number sahi nahi lag raha. Is format mein bhejein: edit phone 9876543210",
                ), user_state
            state["lead_phone"] = edited_phone
            return _localized(
                state,
                "Phone number updated successfully.",
                "Phone number successfully update ho gaya.",
                "Phone number safalta se update ho gaya.",
            ), user_state

        if stage == "name":
            state["lead_name"] = text
            state["lead_stage"] = "phone"
            track_event(chat_id, "lead_stage_completed", {"stage": "name"})
            return _localized(
                state,
                "Thanks. Please share your 10-digit phone number so we can schedule your callback.",
                "Shukriya. Callback schedule karne ke liye apna 10-digit phone number share karein.",
                "Dhanyavaad. Callback schedule karne ke liye apna 10-digit phone number dein.",
            ), user_state

        if stage == "phone":
            if not is_valid_phone(text):
                return _localized(
                    state,
                    "That looks invalid. Please share a valid 10-digit Indian phone number.",
                    "Yeh invalid lag raha hai. Kripya valid 10-digit Indian phone number share karein.",
                    "Yeh number invalid lag raha hai. Kripya valid 10-digit Indian phone number dein.",
                ), user_state

            state["lead_phone"] = text
            state["lead_stage"] = "location"
            track_event(chat_id, "lead_stage_completed", {"stage": "phone"})

            if not state.get("call_lead_triggered"):
                schedule_call(state["lead_phone"], state.get("lead_name") or "Lead")
                state["call_lead_triggered"] = True
                track_event(chat_id, "call_lead_triggered")

            return _localized(
                state,
                "Great. Please share your location or area.",
                "Great. Ab apni location/area share karein.",
                "Bahut accha. Ab apni location/area bataiye.",
            ), user_state

        if stage == "location":
            state["lead_location"] = text
            state["lead_stage"] = "space_type"
            track_event(chat_id, "lead_stage_completed", {"stage": "location"})
            return _localized(
                state,
                "What space should we plan for? (1BHK, 2BHK, 3BHK, Office, or Other). You can also type 'skip'.",
                "Hum kis type ke space ke liye plan karein? (1BHK, 2BHK, 3BHK, Office, ya Other). Aap 'skip' bhi type kar sakte hain.",
                "Kis type ke space ke liye plan karein? (1BHK, 2BHK, 3BHK, Office, ya Other). Aap 'skip' bhi type kar sakte hain.",
            ), user_state

        if stage == "space_type":
            state["lead_space_type"] = _normalize_space_type(text)
            state["lead_stage"] = "budget"
            track_event(chat_id, "lead_stage_completed", {"stage": "space_type"})
            return _localized(
                state,
                "Please share your budget range so we can suggest the right scope. You can also type 'skip'.",
                "Budget range share karein taki hum sahi scope suggest kar saken. Aap 'skip' bhi type kar sakte hain.",
                "Kripya budget range bataiye taki hum sahi scope suggest kar saken. Aap 'skip' bhi type kar sakte hain.",
            ), user_state

        if stage == "budget":
            state["lead_budget"] = "Not shared" if _is_skip(text) else text
            state["lead_stage"] = "timeline"
            track_event(chat_id, "lead_stage_completed", {"stage": "budget", "skipped": _is_skip(text)})
            escalation_msg = _maybe_escalate(state, text)
            response = _localized(
                state,
                "Got it. What is your expected timeline for starting or completing the project? You can type 'skip' if unsure.",
                "Samajh gaya. Project start ya completion ka expected timeline kya hai? Agar sure nahi hain to 'skip' type kar sakte hain.",
                "Samajh gaya. Project shuru ya complete karne ka expected timeline kya hai? Agar pakka nahi hai to 'skip' type kar sakte hain.",
            )
            if escalation_msg:
                response = response + "\n\n" + escalation_msg
            return response, user_state

        if stage == "timeline":
            state["lead_timeline"] = "Not shared" if _is_skip(text) else text
            state["lead_stage"] = "consultation_agreed"
            track_event(chat_id, "lead_stage_completed", {"stage": "timeline", "skipped": _is_skip(text)})
            return _localized(
                state,
                "Would you like me to book a consultation call for you now? (yes/no)",
                "Kya main abhi aapke liye consultation call book kar du? (yes/no)",
                "Kya main abhi aapke liye consultation call book kar doon? (yes/no)",
            ), user_state

        if stage == "consultation_agreed":
            agreed = _parse_yes_no(text)
            if agreed is None:
                return _localized(
                    state,
                    "Please reply with 'yes' or 'no' so I can proceed with booking.",
                    "Booking continue karne ke liye please 'yes' ya 'no' reply karein.",
                    "Booking continue karne ke liye kripya 'yes' ya 'no' reply karein.",
                ), user_state
            state["lead_consultation_agreed"] = agreed
            if agreed:
                state["lead_stage"] = "consultation_datetime"
                track_event(chat_id, "lead_stage_completed", {"stage": "consultation_agreed", "value": True})
                return _localized(
                    state,
                    "Please share your preferred date/time in format DD-MMM-YYYY HH:MM (example: 25-Apr-2026 14:30)",
                    "Apni preferred date/time is format mein share karein: DD-MMM-YYYY HH:MM (example: 25-Apr-2026 14:30)",
                    "Apni preferred date/time is format mein dein: DD-MMM-YYYY HH:MM (example: 25-Apr-2026 14:30)",
                ), user_state

            capture_lead(
                name=state.get("lead_name"),
                phone=state.get("lead_phone"),
                location=state.get("lead_location"),
                space_type=state.get("lead_space_type"),
                budget=state.get("lead_budget"),
                timeline=state.get("lead_timeline"),
                consultation_agreed=False,
                preferred_datetime=None,
                chat_id=chat_id,
            )
            state["current_step"] = "assistant"
            state["lead_stage"] = None
            track_event(chat_id, "lead_saved", {"consultation_agreed": False})
            return (
                format_lead_captured(state.get("lead_name"), state.get("lead_phone"))
                + "\n\n"
                + _localized(
                    state,
                    "I am still here to help. You can continue asking any design, pricing, or materials question.",
                    "Main yahin hoon. Aap design, pricing, ya materials se related koi bhi question pooch sakte hain.",
                    "Main yahin hoon. Aap design, pricing, ya materials se juda koi bhi sawal pooch sakte hain.",
                )
            ), user_state

        if stage == "consultation_datetime":
            normalized = _validate_consultation_dt(text)
            if not normalized:
                return _localized(
                    state,
                    "Invalid format. Please use DD-MMM-YYYY HH:MM (example: 25-Apr-2026 14:30)",
                    "Format sahi nahi hai. Please DD-MMM-YYYY HH:MM use karein (example: 25-Apr-2026 14:30)",
                    "Format sahi nahi hai. Kripya DD-MMM-YYYY HH:MM use karein (example: 25-Apr-2026 14:30)",
                ), user_state

            slot_ok, slot_msg = validate_consultation_slot(normalized)
            if not slot_ok:
                return _localized(
                    state,
                    f"That slot is not available: {slot_msg}",
                    f"Yeh slot available nahi hai: {slot_msg}",
                    f"Yeh slot uplabdh nahi hai: {slot_msg}",
                ), user_state

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
                chat_id=chat_id,
            )

            booked = book_calendar(state.get("lead_name"), state.get("lead_phone"), normalized, chat_id=chat_id)
            state["current_step"] = "assistant"
            state["lead_stage"] = None
            track_event(chat_id, "lead_saved", {"consultation_agreed": True})

            parts = []
            if booked:
                parts.append("Action confirmed: BookCalendar completed.")
                track_event(chat_id, "calendar_booked")
            parts.append(format_consultation_confirmed(state.get("lead_name"), normalized))
            parts.append("Action confirmed: SaveToSheets completed.")
            parts.append("You can continue asking questions anytime. I am here to help.")
            return "\n\n".join(parts), user_state

    if _is_greeting(text):
        track_event(chat_id, "greeting")
        return get_initial_message(state), user_state

    if _is_gratitude(text):
        return _localized(
            state,
            "You are welcome. I am here if you want help with pricing, timeline, or booking next steps.",
            "Welcome. Agar aap chaho to pricing, timeline, ya booking next steps mein help kar sakta hoon.",
            "Aapka swagat hai. Agar aap chahen to pricing, timeline, ya booking next steps mein madad kar sakta hoon.",
        ), user_state

    if text.lower() in {"help", "contact", "phone", "email"}:
        track_event(chat_id, "contact_requested")
        return format_contact_info(), user_state

    escalation_msg = _maybe_escalate(state, text)
    if escalation_msg:
        track_event(chat_id, "escalation_triggered")
        return escalation_msg, user_state

    if _is_booking_intent(text):
        track_event(chat_id, "booking_intent_detected")
        if state.get("lead_phone") and lead_exists(state.get("lead_phone")):
            return _localized(
                state,
                "I already have your lead details. If you want, I can still continue and update booking information.",
                "Aapke lead details pehle se save hain. Agar chaho to main booking details update kar deta hoon.",
                "Aapke lead details pehle se save hain. Agar chahen to main booking details update kar deta hoon.",
            ) + "\n\n" + _start_lead_capture(state), user_state
        return _start_lead_capture(state), user_state

    assistant_reply = _run_assistant_answer(state, text)
    track_event(chat_id, "assistant_answered")
    return assistant_reply, user_state
