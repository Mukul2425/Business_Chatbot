"""
Session Memory Service - Track conversation history and context for semantic continuity
"""
from datetime import datetime
from typing import Optional, List, Dict, Tuple


def init_conversation_memory(chat_id: str, state: dict) -> None:
    """Initialize conversation history for a new user"""
    if "conversation_history" not in state:
        state["conversation_history"] = []
    if "last_query_intent" not in state:
        state["last_query_intent"] = None
    if "last_bot_context" not in state:
        state["last_bot_context"] = None


def add_to_history(chat_id: str, state: dict, user_msg: str, bot_response: str, context: Optional[Dict] = None) -> None:
    """
    Add exchange to conversation history
    
    Args:
        chat_id: Telegram chat ID
        state: User state dict
        user_msg: User message
        bot_response: Bot's response (first 500 chars for context)
        context: Optional dict with intent info (e.g., {"intent": "materials", "action_offered": True})
    """
    if "conversation_history" not in state:
        state["conversation_history"] = []
    
    # Keep only last 10 exchanges to avoid memory bloat
    max_history = 10
    if len(state["conversation_history"]) >= max_history:
        state["conversation_history"] = state["conversation_history"][-(max_history - 1):]
    
    exchange = {
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "bot": bot_response[:500],  # Store truncated response for efficiency
        "context": context or {},
    }
    state["conversation_history"].append(exchange)


def is_follow_up(user_msg: str) -> Tuple[bool, str]:
    """
    Detect if message is a follow-up/continuation (affirmation, yes/no, short response)
    
    Returns: (is_follow_up, follow_up_type)
        - Types: "affirmation", "request_clarification", "request_more", "yes_no", "breakdown_request"
    """
    text = user_msg.strip().lower()
    
    # Short affirmations indicating follow-up to previous context
    affirmations = {
        "yes", "yep", "yeah", "sure", "ok", "okay", "alright", "fine", "good",
        "please", "why not", "you bet", "sounds good", "definitely",
        # Hindi
        "haan", "theek", "bilkul", "theek hai", "shukriya", "bilkul karo",
    }
    
    # Affirmations often combined with "please"
    extended_affirmations = {"yeah please", "yes please", "ok please", "sure please", 
                             "please", "all of them", "everything", "all"}
    
    # Yes/no questions or short responses
    yes_no = {"yes", "no", "yep", "nope", "maybe", "perhaps", "ok"}
    
    # Request for clarification/more info
    clarification = {
        "explain", "tell me more", "more details", "how", "what", "why", "when",
        "what do you mean", "elaborate", "detail",
    }
    
    # Request for more/all options (including breakdown)
    more_requests = {"all", "more", "everything", "all options", "show all", "batao",
                     "break it down", "breakdown", "by budget", "by premium", "by luxury"}
    
    # Requests with preceding context
    if text in extended_affirmations or text == "please":
        return True, "affirmation"
    
    if text in affirmations:
        return True, "affirmation"
    
    if text in yes_no:
        return True, "yes_no"
    
    if any(word in text for word in clarification):
        return True, "request_clarification"
    
    # Check for breakdown requests (may not be short but follow previous context)
    if any(keyword in text for keyword in more_requests):
        return True, "breakdown_request"
    
    # Very short messages (1-3 words) that look like follow-ups
    word_count = len(text.split())
    if word_count <= 3 and text in affirmations:
        return True, "affirmation"
    
    return False, ""


def get_previous_context(state: dict) -> Optional[Dict]:
    """
    Extract previous bot's context to understand what follow-up refers to
    
    Returns dict with:
        - prev_user_msg: Previous user message
        - prev_bot_response: Previous bot response (truncated)
        - prev_intent: What was the previous intent
        - prev_action_offered: Was there an action offered (yes/no question)?
    """
    if "conversation_history" not in state or len(state["conversation_history"]) == 0:
        return None
    
    last_exchange = state["conversation_history"][-1]
    return {
        "prev_user_msg": last_exchange["user"],
        "prev_bot_response": last_exchange["bot"],
        "prev_context": last_exchange.get("context", {}),
    }


def should_use_previous_context(user_msg: str, prev_context: Optional[Dict]) -> bool:
    """
    Decide if we should use previous context for this message
    
    Only use if:
    - Message is a follow-up AND
    - Previous context exists AND
    - Previous exchange was not lead capture (ambiguous context)
    """
    if not prev_context or not prev_context.get("prev_context"):
        return False
    
    is_follow, _ = is_follow_up(user_msg)
    if not is_follow:
        return False
    
    # Don't use context if previous was lead capture (different domain)
    if prev_context.get("prev_context", {}).get("stage") == "lead_capture":
        return False
    
    return True


def build_contextual_query(user_msg: str, prev_context: Dict) -> Tuple[str, Dict]:
    """
    Expand a follow-up message with previous context
    
    Examples:
    - User: "yeah please" (after bot asked about budget/premium/luxury breakdown)
      → "break down by budget premium and luxury levels" + context
    - User: "can you break it down" (after materials answer)
      → "Break down materials by budget premium and luxury" + full context
    
    Returns: (expanded_query, context_metadata)
    """
    if not prev_context:
        return user_msg, {}
    
    prev_msg = prev_context.get("prev_user_msg", "").lower()
    prev_response = prev_context.get("prev_bot_response", "").lower()
    prev_context_dict = prev_context.get("prev_context", {})
    intent = prev_context_dict.get("intent")
    action_offered = prev_context_dict.get("action_offered")
    
    # If bot asked a yes/no or offered action, and user says yes/ok/please
    is_follow, follow_type = is_follow_up(user_msg)
    
    if not is_follow:
        return user_msg, {"follow_up": False}
    
    metadata = {
        "follow_up": True,
        "follow_up_type": follow_type,
        "prev_intent": intent,
        "action_responded": action_offered,
    }
    
    # For affirmations responding to an offered action
    if follow_type == "affirmation" and action_offered:
        # User agreed to the action, expand query with context
        expanded = f"{prev_msg} {user_msg}".strip()
        metadata["expanded_context"] = prev_context_dict
        return expanded, metadata
    
    # For breakdown requests
    if follow_type == "breakdown_request":
        # Check if previous response mentioned breakdown option
        if "break" in prev_response or "budget" in prev_response:
            # User wants breakdown by budget/premium/luxury
            if "materials" in prev_msg or "materials" in prev_response:
                expanded = f"materials break down by budget premium and luxury {user_msg}".strip()
                metadata["expanded_context"] = {"prev_intent": "materials"}
                return expanded, metadata
            else:
                expanded = f"{prev_msg} {user_msg}".strip()
                metadata["expanded_context"] = prev_context_dict
                return expanded, metadata
    
    # For "request more" after bot mentioned options
    if follow_type == "request_more":
        expanded = f"{prev_msg} all options".strip()
        metadata["expanded_context"] = prev_context_dict
        return expanded, metadata
    
    # For clarification requests, add previous intent
    if follow_type == "request_clarification":
        if intent:
            expanded = f"{prev_msg} {user_msg}".strip()
            metadata["expanded_context"] = prev_context_dict
            return expanded, metadata
    
    # For simple affirmations on materials breakdown offer
    if follow_type == "affirmation":
        # If previous was offering materials breakdown
        if "break this down for budget" in prev_response or "break it down for" in prev_response:
            expanded = f"provide materials breakdown by budget premium and luxury".strip()
            metadata["expanded_context"] = {"prev_intent": "materials_breakdown"}
            return expanded, metadata
    
    return user_msg, metadata


def get_conversation_summary(state: dict, max_lines: int = 3) -> str:
    """
    Get brief summary of recent conversation for context injection into Gemini
    
    Returns: Formatted string of recent exchanges (max 3 exchanges)
    """
    if "conversation_history" not in state or len(state["conversation_history"]) == 0:
        return ""
    
    history = state["conversation_history"]
    recent = history[-(max_lines):]
    
    summary_lines = []
    for exc in recent:
        user_brief = exc["user"][:80]  # Truncate for summary
        bot_brief = exc["bot"][:100]
        summary_lines.append(f"User: {user_brief}")
        summary_lines.append(f"Bot: {bot_brief}")
    
    return "\nRecent conversation context:\n" + "\n".join(summary_lines)
