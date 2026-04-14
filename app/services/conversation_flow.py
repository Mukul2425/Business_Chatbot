"""
Conversation Flow Engine - Orchestrate the bot's multi-step conversation flow
"""
from app.services.sheets_service import get_services, get_pricing
from app.services.faq_service import search_faq
from app.services.gemini_service import ask_gemini
from app.services.leads_service import capture_lead, is_valid_phone
from app.services.response_formatter import (
    format_welcome, format_service_options, format_faq_answer,
    format_error, format_lead_submission, format_contact_info,
    format_lead_name_prompt, format_lead_phone_prompt,
    format_lead_location_prompt, format_lead_saved,
    format_project_type_prompt, format_ask_anything_prompt,
    format_not_found_fallback, format_thank_you_reply,
    format_call_timing_reply
)


MAX_GEMINI_CALLS_PER_CHAT = 2


def get_initial_message():
    """Get initial welcome message"""
    return format_welcome()


def detect_service_option(user_input):
    text = (user_input or "").lower()
    if "1bhk" in text or "1 bhk" in text:
        return "1BHK"
    if "2bhk" in text or "2 bhk" in text:
        return "2BHK"
    if "3bhk" in text or "3 bhk" in text:
        return "3BHK"
    if "office" in text or "workspace" in text or "work space" in text:
        return "Office"
    return None


def detect_initial_category(user_input):
    text = (user_input or "").strip().lower()

    category_map = {
        "1": "project_type",
        "2": "pricing_budget",
        "3": "process_timeline",
        "4": "consultation_contact",
        "5": "ask_something_else",
    }
    if text in category_map:
        return category_map[text]

    if any(k in text for k in ["project", "project type", "1bhk", "2bhk", "3bhk", "office"]):
        return "project_type"
    if any(k in text for k in ["pricing", "price", "budget", "cost"]):
        return "pricing_budget"
    if any(k in text for k in ["process", "timeline", "duration", "time"]):
        return "process_timeline"
    if any(k in text for k in ["consultation", "contact", "call", "appointment"]):
        return "consultation_contact"
    if any(k in text for k in ["ask", "other", "something else", "custom"]):
        return "ask_something_else"

    return None


def is_interior_query(user_input):
    text = (user_input or "").lower()
    interior_keywords = [
        "interior", "design", "home", "office", "bhk", "renovation", "modular",
        "kitchen", "wardrobe", "living room", "bedroom", "pricing", "budget",
        "timeline", "consultation", "furniture", "false ceiling", "lighting",
    ]
    return any(keyword in text for keyword in interior_keywords)


def get_category_quick_response(category):
    if category == "pricing_budget":
        faq_answer = search_faq("pricing budget cost estimate")
        if faq_answer:
            return format_faq_answer(faq_answer)
        return (
            "For pricing and budget planning, we recommend sharing project type, "
            "approximate area, and expected quality level. "
            "I can then provide a practical estimate range."
        )

    if category == "process_timeline":
        faq_answer = search_faq("process timeline duration steps")
        if faq_answer:
            return format_faq_answer(faq_answer)
        return (
            "Our process usually covers requirement discovery, design, material finalization, "
            "and execution. Timelines vary by scope, and I can suggest a realistic range "
            "once you share your project type."
        )

    if category == "consultation_contact":
        return format_contact_info()

    return None


def detect_query_intents(user_input):
    text = (user_input or "").lower()
    intents = set()

    if any(k in text for k in ["budget", "price", "pricing", "cost", "estimate", "quote"]):
        intents.add("budget")
    if any(k in text for k in ["custom", "customize", "customisation", "customization", "personal", "personalize"]):
        intents.add("customization")
    if any(k in text for k in ["timeline", "duration", "weeks", "months", "delivery"]):
        intents.add("timeline")
    if any(k in text for k in ["time", "right time"]) and not any(
        k in text for k in ["call", "contact", "appointment", "book"]
    ):
        intents.add("timeline")
    if any(k in text for k in ["process", "steps", "workflow", "execution"]):
        intents.add("process")
    if any(k in text for k in ["consult", "consultation", "appointment", "call", "contact"]):
        intents.add("consultation")

    return intents


def is_gratitude(user_input):
    text = (user_input or "").strip().lower()
    gratitude_phrases = [
        "thanks", "thank you", "thankyou", "ok thank you", "thx", "great thanks",
        "shukriya", "dhanyawad", "dhanyavaad",
    ]
    return any(phrase in text for phrase in gratitude_phrases)


def is_call_timing_query(user_input):
    text = (user_input or "").strip().lower()
    if "time" not in text and "timing" not in text:
        return False
    return any(k in text for k in ["call", "contact", "phone"])


def is_appointment_booking_request(user_input):
    text = (user_input or "").strip().lower()
    # Treat explicit booking intent only; informational questions should not auto-trigger lead capture.
    if "?" in text and any(k in text for k in ["appointment", "call"]):
        return False
    if "kya" in text and any(k in text for k in ["appointment", "call"]):
        return False

    booking_keywords = [
        "book an appointment", "book appointment", "schedule appointment",
        "schedule a call", "book a call", "arrange a call", "appointment",
        "book for me", "appointment for me", "call back", "callback",
    ]
    return any(k in text for k in booking_keywords)


def _normalize_service_name(service_name):
    return (service_name or "").strip().lower().replace(" ", "")


def get_pricing_range_for_service(service_name):
    pricing_df = get_pricing()
    if pricing_df is None or len(pricing_df) == 0:
        return None

    target = _normalize_service_name(service_name)
    for _, row in pricing_df.iterrows():
        category = str(row.get("Category", "")).strip()
        if _normalize_service_name(category) == target:
            return {
                "category": category,
                "min": str(row.get("Min Price", "")).strip(),
                "max": str(row.get("Max Price", "")).strip(),
            }
    return None


def _normalize_price_label(value):
    clean = (value or "").strip()
    if not clean:
        return clean
    if clean.startswith("₹"):
        return clean
    return f"₹{clean}"


def format_budget_customization_response(selected_service, intents):
    service_label = selected_service or "your project"
    lines = []

    pricing = get_pricing_range_for_service(selected_service)

    if "budget" in intents:
        if pricing and pricing.get("min") and pricing.get("max"):
            min_price = _normalize_price_label(pricing["min"])
            max_price = _normalize_price_label(pricing["max"])
            lines.append(
                f"For {service_label}, a typical budget range is approximately "
                f"{min_price} to {max_price}."
            )
            lines.append(
                "As a practical example: essential finishes generally stay near the lower range, "
                "while premium materials and added scope move toward the upper range."
            )
        else:
            lines.append(
                "Budget depends on project size, material choices, and scope. "
                "Share your project type and area, and I can suggest a realistic range."
            )

    if "customization" in intents:
        lines.append(
            "Customization options are wide: modular kitchen layout, wardrobe internals, "
            "lighting design, false ceiling, storage optimization, and finish upgrades."
        )
        lines.append(
            "Customization cost varies by materials, brand selection, and design complexity, "
            "so a short consultation helps us provide an accurate breakup."
        )

    if "timeline" in intents:
        lines.append(
            "Timeline is typically affected by design approvals, material lead times, and site readiness. "
            "A standard home scope is often completed in a few weeks, while premium customization can take longer."
        )

    if "process" in intents:
        lines.append(
            "Our process includes requirement discussion, design proposal, material finalization, "
            "execution, and quality handover."
        )

    if "consultation" in intents or "customization" in intents:
        lines.append(
            "For personal customizations, you can book an appointment or call us at +91-9876543119."
        )

    if not lines:
        return None

    return "\n\n".join(lines)


def maybe_get_smart_response(user_input, state):
    intents = detect_query_intents(user_input)
    if not intents:
        return None

    # Provide deterministic blended response for common service-intent questions.
    if intents.intersection({"budget", "customization", "timeline", "process", "consultation"}):
        return format_budget_customization_response(state.get("selected_service"), intents)

    return None


def can_use_gemini(state):
    return int(state.get("gemini_calls", 0)) < MAX_GEMINI_CALLS_PER_CHAT


def is_greeting_only(user_input):
    text = (user_input or "").strip().lower()
    greetings = {
        "hi", "hello", "hey", "hii", "yo", "good morning", "good afternoon", "good evening"
    }
    return text in greetings


def get_next_step(current_step, user_input):
    """
    Flow engine: Determine next step and response from services_flow sheet.
    Returns (response, next_step) or (None, None) if no match found.
    """
    df = get_services()

    for _, row in df.iterrows():
        if (str(row.get("Step", "")).strip().lower() == str(current_step).strip().lower() and 
            str(row.get("Option", "")).strip().lower() == str(user_input).strip().lower()):
            response = row.get("Response", "")
            next_step = row.get("Next Step", "start")
            return response, next_step

    return None, None


def process_message(chat_id, user_input, user_state):
    """
    Main message processor - handles FAQ, flow, and LLM fallback.
    
    Returns: (response_text, updated_user_state)
    """
    
    # Initialize user state if new
    if chat_id not in user_state:
        user_state[chat_id] = {
            "current_step": "start",
            "entry_stage": "category",
            "selected_service": None,
            "gemini_calls": 0,
            "lead_name": None,
            "lead_phone": None,
            "lead_location": None,
            "lead_stage": None,
        }
    
    state = user_state[chat_id]
    current_step = state["current_step"]
    user_input = user_input.strip()
    
    # Special commands
    if user_input.lower() in ["help", "contact", "phone", "email"]:
        return format_contact_info(), user_state

    if is_gratitude(user_input):
        return format_thank_you_reply(), user_state

    if is_call_timing_query(user_input):
        return format_call_timing_reply(), user_state

    if is_appointment_booking_request(user_input) and state.get("current_step") != "lead_capture":
        state["current_step"] = "lead_capture"
        state["lead_stage"] = "name"
        return format_lead_submission() + "\n\n" + format_lead_name_prompt(), user_state
    
    if user_input.lower() in ["start", "menu", "home"]:
        state["current_step"] = "start"
        state["entry_stage"] = "category"
        state["selected_service"] = None
        state["gemini_calls"] = 0
        state["lead_stage"] = None
        return get_initial_message(), user_state

    # Friendly greeting handling
    if is_greeting_only(user_input):
        return get_initial_message(), user_state

    # Entry flow: category first, then project type selection if needed.
    if state.get("current_step") == "start":
        entry_stage = state.get("entry_stage") or "category"

        if entry_stage == "category":
            direct_service = detect_service_option(user_input)
            if direct_service:
                response, next_step = get_next_step("start", direct_service)
                if response:
                    state["selected_service"] = direct_service
                    state["current_step"] = next_step
                    state["entry_stage"] = None
                    response = response + "\n\n" + format_service_options(direct_service)
                    return response, user_state

            category = detect_initial_category(user_input)
            if category == "project_type":
                state["entry_stage"] = "project_selection"
                return format_project_type_prompt(), user_state

            if category == "ask_something_else":
                state["entry_stage"] = "ask_anything"
                return format_ask_anything_prompt(), user_state

            if category in {"pricing_budget", "process_timeline", "consultation_contact"}:
                quick_response = get_category_quick_response(category)
                state["entry_stage"] = "category"
                response = quick_response + "\n\n" + format_project_type_prompt()
                return response, user_state

        elif entry_stage == "project_selection":
            detected_service = detect_service_option(user_input)
            if detected_service:
                response, next_step = get_next_step("start", detected_service)
                if response:
                    state["selected_service"] = detected_service
                    state["current_step"] = next_step
                    state["entry_stage"] = None
                    response = response + "\n\n" + format_service_options(detected_service)
                    return response, user_state
            return format_project_type_prompt(), user_state

        elif entry_stage == "ask_anything":
            if is_appointment_booking_request(user_input):
                state["entry_stage"] = None
                state["current_step"] = "lead_capture"
                state["lead_stage"] = "name"
                return format_lead_submission() + "\n\n" + format_lead_name_prompt(), user_state

            smart_response = maybe_get_smart_response(user_input, state)
            if smart_response:
                state["entry_stage"] = "category"
                return smart_response, user_state

            faq_answer = search_faq(user_input)
            if faq_answer:
                state["entry_stage"] = "category"
                return format_faq_answer(faq_answer), user_state

            if not is_interior_query(user_input):
                state["entry_stage"] = "category"
                return format_not_found_fallback(), user_state

            if not can_use_gemini(state):
                state["entry_stage"] = "category"
                return format_not_found_fallback(), user_state

            llm_response = ask_gemini(
                user_input,
                current_step=current_step,
                selected_category=state.get("selected_service")
            )
            state["gemini_calls"] = int(state.get("gemini_calls", 0)) + 1
            state["entry_stage"] = "category"
            return llm_response, user_state

    # Natural language service intent handling (e.g. "I need office interiors")
    detected_service = detect_service_option(user_input)
    if detected_service and state.get("current_step") != "lead_capture":
        response, next_step = get_next_step("start", detected_service)
        if response:
            state["selected_service"] = detected_service
            state["current_step"] = next_step
            response = response + "\n\n" + format_service_options(detected_service)
            return response, user_state

    # Lead capture flow (name -> phone -> location)
    if state.get("current_step") == "lead_capture":
        lead_stage = state.get("lead_stage")

        if lead_stage is None:
            state["lead_stage"] = "name"
            return format_lead_name_prompt(), user_state

        if lead_stage == "name":
            state["lead_name"] = user_input
            state["lead_stage"] = "phone"
            return format_lead_phone_prompt(), user_state

        if lead_stage == "phone":
            if not is_valid_phone(user_input):
                return "Please enter a valid 10-digit Indian phone number.", user_state
            state["lead_phone"] = user_input
            state["lead_stage"] = "location"
            return format_lead_location_prompt(), user_state

        if lead_stage == "location":
            state["lead_location"] = user_input
            capture_lead(
                name=state.get("lead_name", ""),
                phone=state.get("lead_phone", ""),
                location=state.get("lead_location", ""),
                requirement=state.get("selected_service") or "General inquiry",
            )
            name = state.get("lead_name", "there")
            state["current_step"] = "start"
            state["selected_service"] = None
            state["lead_name"] = None
            state["lead_phone"] = None
            state["lead_location"] = None
            state["lead_stage"] = None
            return format_lead_saved(name), user_state
    
    # Try flow engine first
    response, next_step = get_next_step(current_step, user_input)
    
    if response:
        # Found in flow
        if current_step == "start":
            state["selected_service"] = user_input
            state["entry_stage"] = None
            response = response + "\n\n" + format_service_options(user_input)
        
        state["current_step"] = next_step
        
        if next_step == "lead_capture":
            state["lead_stage"] = "name"
            response = response + "\n\n" + format_lead_submission()
        elif next_step == "end":
            state["current_step"] = "start"
            state["entry_stage"] = "category"
            state["lead_stage"] = None
            response = response + "\n\nNeed anything else? Type /menu to start again."
        
        return response, user_state

    smart_response = maybe_get_smart_response(user_input, state)
    if smart_response:
        return smart_response, user_state

    if is_appointment_booking_request(user_input):
        state["current_step"] = "lead_capture"
        state["lead_stage"] = "name"
        return format_lead_submission() + "\n\n" + format_lead_name_prompt(), user_state
    
    # Try FAQ search
    faq_answer = search_faq(user_input)
    if faq_answer:
        return format_faq_answer(faq_answer), user_state

    if not is_interior_query(user_input):
        return format_not_found_fallback(), user_state

    if not can_use_gemini(state):
        return format_not_found_fallback(), user_state
    
    # Fallback to Gemini LLM
    llm_response = ask_gemini(
        user_input, 
        current_step=current_step,
        selected_category=state.get("selected_service")
    )
    state["gemini_calls"] = int(state.get("gemini_calls", 0)) + 1
    
    return llm_response, user_state


def reset_user_state(chat_id, user_state):
    """Reset user's conversation state"""
    if chat_id in user_state:
        user_state[chat_id] = {
            "current_step": "start",
            "entry_stage": "category",
            "selected_service": None,
            "gemini_calls": 0,
            "lead_name": None,
            "lead_phone": None,
            "lead_location": None,
            "lead_stage": None,
        }
    return user_state
