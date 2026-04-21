"""
Conversation Flow Engine - Orchestrate the bot's multi-step conversation flow
"""
from app.services.sheets_service import get_services, get_pricing
from app.services.faq_service import search_faq
from app.services.semantic_service import (
    search_semantic, search_pricing_semantic, confidence_level,
    generate_clarifying_question
)
from app.services.knowledge_base_service import search_knowledge_base
from app.services.knowledge_base_service import (
    build_case_studies_reply,
    build_materials_reply,
    build_materials_quality_breakdown,
)
from app.services.gemini_service import ask_gemini
from app.services.leads_service import capture_lead, is_valid_phone
from app.services.session_memory_service import (
    init_conversation_memory, add_to_history, is_follow_up,
    get_previous_context, should_use_previous_context,
    build_contextual_query, get_conversation_summary
)
from app.services.response_formatter import (
    format_welcome, format_service_options, format_faq_answer,
    format_error, format_lead_submission, format_contact_info,
    format_contact_timing_reply,
    format_lead_name_prompt, format_lead_phone_prompt,
    format_lead_location_prompt, format_lead_saved,
    format_project_type_prompt, format_ask_anything_prompt,
    format_not_found_fallback, format_thank_you_reply,
    format_call_timing_reply, format_clarifying_question,
    format_medium_confidence_answer, format_knowledge_answer,
    format_projects_fallback, format_materials_fallback,
    format_project_portfolio_answer, format_materials_answer,
    get_varied_budget_response,
    get_varied_customization_response, get_varied_timeline_response,
    get_varied_process_response
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

    if any(k in text for k in ["project type", "1bhk", "2bhk", "3bhk", "office"]):
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


def normalize_command(user_input):
    """Normalize Telegram-style commands like /start and /menu."""
    return (user_input or "").strip().lower().lstrip("/")


def is_interior_query(user_input):
    text = (user_input or "").lower()
    interior_keywords = [
        "interior", "design", "home", "office", "bhk", "renovation", "modular",
        "kitchen", "wardrobe", "living room", "bedroom", "pricing", "budget",
        "timeline", "consultation", "furniture", "false ceiling", "lighting",
        "project", "projects", "case study", "portfolio", "materials", "material",
    ]
    return any(keyword in text for keyword in interior_keywords)


def is_project_portfolio_query(user_input):
    text = (user_input or "").lower()
    portfolio_markers = [
        "past project", "past projects", "current project", "current projects",
        "worked on", "case study", "case studies", "portfolio", "projects you have",
        "previous work", "previous projects", "work you've done", "work you have done",
    ]
    return any(marker in text for marker in portfolio_markers)


def is_materials_quality_breakdown_request(user_input):
    """Detect request to break down materials by quality/budget level"""
    text = (user_input or "").lower()
    breakdown_markers = [
        "break", "breakdown", "quality", "budget level", "premium level", "luxury level",
        "by budget", "by premium", "by luxury", "quality breakdown", "material options",
    ]
    return (any(marker in text for marker in breakdown_markers) and
            any(quality in text for quality in ["budget", "premium", "luxury", "quality", "level", "standard"]))


def is_materials_query(user_input):
    text = (user_input or "").lower()
    materials_markers = [
        "materials", "material", "what materials", "which materials", "used material",
        "wood", "plywood", "laminate", "finish", "hardware",
    ]
    return any(marker in text for marker in materials_markers)


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


def is_conversational_acknowledgement(user_input):
    """Detect short conversational confirmations that are not new questions."""
    text = (user_input or "").strip().lower()
    normalized = text.replace("?", "").replace("!", "").replace(".", "").strip()

    acknowledgements = {
        "ok", "okay", "ok great", "okay great", "great", "cool", "nice", "awesome",
        "sounds good", "got it", "understood", "alright", "all right", "perfect",
        "fine", "good", "yep", "yup", "yeah",
    }
    return normalized in acknowledgements


def build_acknowledgement_response(state):
    """Return a context-aware continuation message for small-talk acknowledgements."""
    if state.get("current_step") == "lead_capture":
        lead_stage = state.get("lead_stage")
        if lead_stage == "name":
            return "Great. Please share your full name so I can continue the booking."
        if lead_stage == "phone":
            return "Perfect. Please share your phone number so we can connect."
        if lead_stage == "location":
            return "Thanks. Please share your location to complete the request."

    if state.get("pending_clarification_topic") == "service_scope":
        return "Are you interested in a full home makeover or specific room design?"

    selected_service = state.get("selected_service")
    if selected_service:
        return (
            f"Great. For {selected_service}, I can share pricing, timeline, process details, "
            "or help you book a consultation."
        )

    if state.get("entry_stage") == "project_selection":
        return format_project_type_prompt()

    return (
        "Great. I am here to help. You can ask about pricing, timeline, materials, "
        "past projects, or consultation."
    )


def is_contact_timing_query(user_input):
    """Detect queries about when/what time to contact or business hours"""
    text = (user_input or "").strip().lower()
    
    if not text:
        return False
    
    # Direct time/timing questions
    if text in ["when?", "when", "what time", "what timing", "hours", "working hours"]:
        return True
    
    if "hours" in text and any(k in text for k in ["your", "working", "business", "office"]):
        return True

    # Questions combining when with contact/call
    timing_markers = ["when", "what time", "what hrs", "timing", "hours", "open", "availability"]
    contact_markers = ["contact", "call", "reach", "connect", "appointment", "consultation", "available"]
    
    has_timing = any(marker in text for marker in timing_markers)
    has_contact = any(marker in text for marker in contact_markers)
    
    return has_timing and has_contact


def is_call_timing_query(user_input):
    text = (user_input or "").strip().lower()
    if "time" not in text and "timing" not in text and "when" not in text:
        return False
    return any(k in text for k in ["call", "contact", "phone", "reach"])


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


def format_budget_customization_response(selected_service, intents, pricing_match=None):
    """Build varied response for mixed intents using templates"""
    service_label = selected_service or "your project"
    lines = []

    pricing = get_pricing_range_for_service(selected_service)
    if pricing is None and pricing_match:
        pricing = {
            "category": pricing_match.get("category", ""),
            "min": pricing_match.get("min", ""),
            "max": pricing_match.get("max", ""),
        }
        if not selected_service and pricing.get("category"):
            service_label = pricing["category"]

    if "budget" in intents:
        if pricing and pricing.get("min") and pricing.get("max"):
            min_price = _normalize_price_label(pricing["min"])
            max_price = _normalize_price_label(pricing["max"])
            lines.append(get_varied_budget_response(service_label, min_price, max_price))
        else:
            lines.append(
                "Budget depends on project size, material choices, and scope. "
                "Share your project type and area, and I can suggest a realistic range."
            )

    if "customization" in intents:
        lines.append(get_varied_customization_response())

    if "timeline" in intents:
        lines.append(get_varied_timeline_response())

    if "process" in intents:
        lines.append(get_varied_process_response())

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
        pricing_match = None
        if "budget" in intents and not state.get("selected_service"):
            pricing_match, _ = search_pricing_semantic(user_input, threshold=0.30)
        return format_budget_customization_response(state.get("selected_service"), intents, pricing_match)

    return None


def _adaptive_semantic_threshold(query, state):
    """Use a slightly lower threshold for richer/longer queries to reduce false negatives."""
    words = len((query or "").split())
    threshold = 0.35
    if words >= 6:
        threshold = 0.32
    if state.get("selected_service"):
        threshold = min(threshold, 0.30)
    return threshold


def infer_clarification_topic(query):
    text = (query or "").lower()
    if any(k in text for k in ["design", "interior", "home", "makeover", "room"]):
        return "service_scope"
    if is_contact_timing_query(text):
        return "contact_timing"
    if any(k in text for k in ["budget", "price", "cost", "estimate"]):
        return "budget"
    return "general"


def resolve_pending_clarification(user_input, state):
    """Resolve short follow-up replies after a clarifying question."""
    topic = state.get("pending_clarification_topic")
    if not topic:
        return None

    text = (user_input or "").strip().lower()

    if topic == "service_scope":
        if any(k in text for k in ["full home", "full-home", "makeover", "whole house", "entire home"]):
            state["pending_clarification"] = None
            state["pending_clarification_topic"] = None
            return (
                "Great. We specialize in end-to-end full home interior design, including modular kitchen, wardrobes, "
                "TV units, false ceiling, lighting, and custom space planning.\n\n"
                + format_project_type_prompt()
            )

        if any(k in text for k in ["room", "specific room", "bedroom", "kitchen", "living room"]):
            state["pending_clarification"] = None
            state["pending_clarification_topic"] = None
            return (
                "Perfect. We can work room-by-room as well. Share which room you want to start with "
                "(kitchen, bedroom, living room, etc.), and I will suggest a practical scope and budget range."
            )

    if topic == "contact_timing" and is_contact_timing_query(text):
        state["pending_clarification"] = None
        state["pending_clarification_topic"] = None
        return format_contact_timing_reply()

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
    Main message processor - handles FAQ, flow, and LLM fallback with conversation memory.
    
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
    
    # Initialize conversation memory
    init_conversation_memory(chat_id, state)
    
    current_step = state["current_step"]
    user_input = user_input.strip()
    
    # Detect if this is a follow-up message and use previous context
    is_follow_up_msg, follow_up_type = is_follow_up(user_input)
    prev_context = get_previous_context(state) if is_follow_up_msg else None
    should_use_context = should_use_previous_context(user_input, prev_context)
    
    query_to_search = user_input
    context_metadata = {}
    if should_use_context and prev_context:
        query_to_search, context_metadata = build_contextual_query(user_input, prev_context)

    pending_resolved = resolve_pending_clarification(user_input, state)
    if pending_resolved:
        add_to_history(chat_id, state, user_input, pending_resolved, {"intent": "clarification_resolved"})
        return pending_resolved, user_state

    is_docs_priority_query = is_project_portfolio_query(user_input) or is_materials_query(user_input)
    
    # Special commands
    if user_input.lower() in ["help", "contact", "phone", "email"]:
        return format_contact_info(), user_state

    if is_gratitude(user_input):
        return format_thank_you_reply(), user_state

    if is_conversational_acknowledgement(user_input):
        response = build_acknowledgement_response(state)
        add_to_history(chat_id, state, user_input, response, {"intent": "acknowledgement"})
        return response, user_state

    # Check for contact timing questions (when to contact, business hours) BEFORE other timing checks
    if is_contact_timing_query(user_input):
        response = format_contact_timing_reply()
        add_to_history(chat_id, state, user_input, response, {"intent": "contact_timing"})
        return response, user_state

    if is_call_timing_query(user_input):
        return format_call_timing_reply(), user_state

    if is_appointment_booking_request(user_input) and state.get("current_step") != "lead_capture":
        state["current_step"] = "lead_capture"
        state["lead_stage"] = "name"
        return format_lead_submission() + "\n\n" + format_lead_name_prompt(), user_state
    
    normalized_command = normalize_command(user_input)
    if normalized_command in ["start", "menu", "home"]:
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
            # Check for follow-ups to previous context (e.g., breakdown request after materials)
            if should_use_context and prev_context:
                prev_bot_resp = prev_context.get("prev_bot_response", "").lower()
                # If previous was materials and user is asking for breakdown by budget/premium/luxury
                if ("material" in prev_bot_resp and is_materials_quality_breakdown_request(user_input)):
                    breakdown = build_materials_quality_breakdown()
                    if breakdown:
                        response = breakdown
                        add_to_history(chat_id, state, user_input, response, {"intent": "materials_quality_breakdown", "follow_up": True})
                        return response, user_state
                    # Fallback to full materials if breakdown unavailable
                    structured = build_materials_reply()
                    if structured:
                        response = structured
                        add_to_history(chat_id, state, user_input, response, {"intent": "materials_follow_up", "follow_up": True})
                        return response, user_state
                
                # If user just says "yeah please" after materials offer, return breakdown
                if ("break" in prev_bot_resp and "material" in prev_bot_resp and 
                    is_follow_up(user_input)[0] and is_follow_up(user_input)[1] == "affirmation"):
                    breakdown = build_materials_quality_breakdown()
                    if breakdown:
                        response = breakdown
                        add_to_history(chat_id, state, user_input, response, {"intent": "materials_quality_affirmed", "follow_up": True})
                        return response, user_state
            
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
                
                # For consultation/contact, don't force project type prompt
                # For pricing/timeline, do ask for project type
                if category == "consultation_contact":
                    return quick_response, user_state
                else:
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

            if is_docs_priority_query:
                kb_answer, kb_source, kb_score = search_knowledge_base(query_to_search, threshold=0.30)
                kb_conf_level = confidence_level(kb_score)
                if kb_conf_level in {"high", "medium"}:
                    state["entry_stage"] = "category"
                    if is_project_portfolio_query(user_input):
                        structured = build_case_studies_reply()
                        if structured:
                            return format_project_portfolio_answer(structured), user_state
                    if is_materials_query(user_input):
                        structured = build_materials_reply()
                        if structured:
                            return format_materials_answer(structured), user_state
                    return format_knowledge_answer(kb_answer, kb_source), user_state
                state["entry_stage"] = "category"
                if is_project_portfolio_query(user_input):
                    structured = build_case_studies_reply()
                    if structured:
                        return format_project_portfolio_answer(structured), user_state
                    return format_projects_fallback(), user_state
                if is_materials_query(user_input):
                    structured = build_materials_reply()
                    if structured:
                        return format_materials_answer(structured), user_state
                    return format_materials_fallback(), user_state

            faq_answer = search_faq(query_to_search)
            if faq_answer:
                state["entry_stage"] = "category"
                response = format_faq_answer(faq_answer)
                add_to_history(chat_id, state, user_input, response, {"intent": "faq"})
                return response, user_state

            # Try semantic search (with confidence routing)
            semantic_threshold = _adaptive_semantic_threshold(query_to_search, state)
            semantic_answer, semantic_question, semantic_score = search_semantic(query_to_search, threshold=semantic_threshold)
            conf_level = confidence_level(semantic_score)
            
            if conf_level == "high":
                state["entry_stage"] = "category"
                response = format_faq_answer(semantic_answer, semantic_question)
                add_to_history(chat_id, state, user_input, response, {"intent": "semantic_high", "score": semantic_score})
                return response, user_state
            elif conf_level == "medium":
                clarifying = generate_clarifying_question(query_to_search)
                response = format_clarifying_question(clarifying)
                add_to_history(chat_id, state, user_input, response, {"intent": "semantic_medium", "score": semantic_score})
                state["pending_clarification"] = query_to_search
                state["pending_clarification_topic"] = infer_clarification_topic(query_to_search)
                return response, user_state

            # Try document knowledge base next
            kb_answer, kb_source, kb_score = search_knowledge_base(query_to_search, threshold=0.35)
            kb_conf_level = confidence_level(kb_score)

            if kb_conf_level == "high":
                state["entry_stage"] = "category"
                response = format_knowledge_answer(kb_answer, kb_source)
                add_to_history(chat_id, state, user_input, response, {"intent": "knowledge_high", "source": kb_source, "score": kb_score})
                return response, user_state
            elif kb_conf_level == "medium":
                clarifying = generate_clarifying_question(query_to_search)
                response = format_clarifying_question(clarifying)
                add_to_history(chat_id, state, user_input, response, {"intent": "knowledge_medium", "score": kb_score})
                return response, user_state

            if not is_interior_query(user_input):
                state["entry_stage"] = "category"
                response = format_not_found_fallback()
                add_to_history(chat_id, state, user_input, response, {"intent": "not_interior_query"})
                return response, user_state

            if not can_use_gemini(state):
                state["entry_stage"] = "category"
                response = format_not_found_fallback()
                add_to_history(chat_id, state, user_input, response, {"intent": "gemini_limit_exceeded"})
                return response, user_state

            # Include conversation context in Gemini prompt
            conv_summary = get_conversation_summary(state, max_lines=2)
            llm_response = ask_gemini(
                user_input,
                current_step=current_step,
                selected_category=state.get("selected_service"),
                context_hint=conv_summary
            )
            state["gemini_calls"] = int(state.get("gemini_calls", 0)) + 1
            state["entry_stage"] = "category"
            add_to_history(chat_id, state, user_input, llm_response, {"intent": "gemini_llm", "gemini_call": state.get("gemini_calls")})
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
            state["lead_saved_recently"] = True
            state["last_saved_lead_name"] = name
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
        add_to_history(chat_id, state, user_input, smart_response, {"intent": "smart_response"})
        return smart_response, user_state

    if is_docs_priority_query:
        kb_answer, kb_source, kb_score = search_knowledge_base(query_to_search, threshold=0.30)
        kb_conf_level = confidence_level(kb_score)
        if kb_conf_level in {"high", "medium"}:
            if is_project_portfolio_query(user_input):
                structured = build_case_studies_reply()
                if structured:
                    response = format_project_portfolio_answer(structured)
                    add_to_history(chat_id, state, user_input, response, {"intent": "portfolio_docs", "score": kb_score})
                    return response, user_state
            if is_materials_query(user_input):
                structured = build_materials_reply()
                if structured:
                    response = format_materials_answer(structured)
                    add_to_history(chat_id, state, user_input, response, {"intent": "materials_docs", "score": kb_score})
                    return response, user_state
            response = format_knowledge_answer(kb_answer, kb_source)
            add_to_history(chat_id, state, user_input, response, {"intent": "docs_knowledge", "source": kb_source, "score": kb_score})
            return response, user_state
        if is_project_portfolio_query(user_input):
            structured = build_case_studies_reply()
            if structured:
                response = format_project_portfolio_answer(structured)
                add_to_history(chat_id, state, user_input, response, {"intent": "portfolio_fallback"})
                return response, user_state
            response = format_projects_fallback()
            add_to_history(chat_id, state, user_input, response, {"intent": "portfolio_empty"})
            return response, user_state
        if is_materials_query(user_input):
            structured = build_materials_reply()
            if structured:
                response = format_materials_answer(structured)
                add_to_history(chat_id, state, user_input, response, {"intent": "materials_fallback"})
                return response, user_state
            response = format_materials_fallback()
            add_to_history(chat_id, state, user_input, response, {"intent": "materials_empty"})
            return response, user_state

    if is_appointment_booking_request(user_input):
        state["current_step"] = "lead_capture"
        state["lead_stage"] = "name"
        return format_lead_submission() + "\n\n" + format_lead_name_prompt(), user_state
    
    # Try keyword FAQ search first
    faq_answer = search_faq(query_to_search)
    if faq_answer:
        response = format_faq_answer(faq_answer)
        add_to_history(chat_id, state, user_input, response, {"intent": "faq"})
        return response, user_state

    # Try semantic search over FAQ (confidence-based routing)
    semantic_threshold = _adaptive_semantic_threshold(query_to_search, state)
    semantic_answer, semantic_question, semantic_score = search_semantic(query_to_search, threshold=semantic_threshold)
    conf_level = confidence_level(semantic_score)
    
    if conf_level == "high":
        # High confidence: return answer directly
        response = format_faq_answer(semantic_answer, semantic_question)
        add_to_history(chat_id, state, user_input, response, {"intent": "semantic_high", "score": semantic_score})
        return response, user_state
    elif conf_level == "medium":
        # Medium confidence: ask clarifying question instead of guessing
        clarifying = generate_clarifying_question(query_to_search)
        response = format_clarifying_question(clarifying)
        add_to_history(chat_id, state, user_input, response, {"intent": "semantic_medium", "score": semantic_score})
        state["pending_clarification"] = query_to_search
        state["pending_clarification_topic"] = infer_clarification_topic(query_to_search)
        return response, user_state

    # Try document knowledge base next
    kb_answer, kb_source, kb_score = search_knowledge_base(query_to_search, threshold=0.35)
    kb_conf_level = confidence_level(kb_score)

    if kb_conf_level == "high":
        response = format_knowledge_answer(kb_answer, kb_source)
        add_to_history(chat_id, state, user_input, response, {"intent": "kb_high", "source": kb_source, "score": kb_score})
        return response, user_state
    elif kb_conf_level == "medium":
        clarifying = generate_clarifying_question(query_to_search)
        response = format_clarifying_question(clarifying)
        add_to_history(chat_id, state, user_input, response, {"intent": "kb_medium", "score": kb_score})
        state["pending_clarification"] = query_to_search
        state["pending_clarification_topic"] = infer_clarification_topic(query_to_search)
        return response, user_state
    
    # No keyword or semantic match; check if interior-related
    if not is_interior_query(user_input):
        response = format_not_found_fallback()
        add_to_history(chat_id, state, user_input, response, {"intent": "not_interior"})
        return response, user_state

    # Out of API quota
    if not can_use_gemini(state):
        response = format_not_found_fallback()
        add_to_history(chat_id, state, user_input, response, {"intent": "gemini_limit"})
        return response, user_state
    
    # Use Gemini as final fallback with conversation context
    conv_summary = get_conversation_summary(state, max_lines=2)
    llm_response = ask_gemini(
        user_input, 
        current_step=current_step,
        selected_category=state.get("selected_service"),
        context_hint=conv_summary
    )
    state["gemini_calls"] = int(state.get("gemini_calls", 0)) + 1
    add_to_history(chat_id, state, user_input, llm_response, {"intent": "gemini_final", "gemini_call": state.get("gemini_calls")})
    
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
