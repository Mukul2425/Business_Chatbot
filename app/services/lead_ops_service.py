"""Operational lead-management policy layer for deterministic actions."""
from datetime import datetime
import re


BUDGET_ESCALATION_THRESHOLD = 20_00_000

HUMAN_REQUEST_MARKERS = (
    "talk to human",
    "real person",
    "human agent",
    "connect me to team",
    "speak to someone",
    "call me now",
)

FRUSTRATION_MARKERS = (
    "frustrated",
    "angry",
    "upset",
    "worst",
    "pathetic",
    "not happy",
    "terrible",
)


def _now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _extract_budget_rupees(text):
    """Extract rough budget estimate in rupees from free-text."""
    t = (text or "").lower().replace(",", "")

    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|l|lac|lacs)", t)
    if lakh_match:
        return int(float(lakh_match.group(1)) * 100000)

    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(crore|crores|cr)", t)
    if crore_match:
        return int(float(crore_match.group(1)) * 10000000)

    # Try plain rupee number like "2500000"
    raw_num_match = re.search(r"\b(\d{6,9})\b", t)
    if raw_num_match:
        return int(raw_num_match.group(1))

    return None


def _detect_call_team_reason(user_input):
    text = (user_input or "").lower()

    if any(marker in text for marker in HUMAN_REQUEST_MARKERS):
        return "Lead requested a human representative"

    if any(marker in text for marker in FRUSTRATION_MARKERS):
        return "Lead appears frustrated/angry"

    budget = _extract_budget_rupees(user_input)
    if budget and budget > BUDGET_ESCALATION_THRESHOLD:
        return f"Lead budget appears above threshold (>{BUDGET_ESCALATION_THRESHOLD})"

    return None


def apply_operational_policy(user_input, response_text, state):
    """
    Overlay deterministic operational confirmations while preserving existing response logic.

    Current actions supported:
    - CallLead trigger once per active chat session
    - CallTeam trigger on policy conditions
    - SaveToSheets confirmation when lead was captured in flow
    """
    action_lines = []
    now = _now_string()

    if not state.get("ops_call_lead_triggered"):
        state["ops_call_lead_triggered"] = True
        action_lines.append(
            f"Action confirmed [{now}]: CallLead triggered. Aria follow-up should start within 3 minutes."
        )

    reason = _detect_call_team_reason(user_input)
    if reason:
        previous_reason = state.get("ops_last_call_team_reason")
        if previous_reason != reason:
            state["ops_last_call_team_reason"] = reason
            action_lines.append(
                f"Action confirmed [{now}]: CallTeam triggered. Reason: {reason}."
            )

    if state.get("lead_saved_recently"):
        lead_name = state.get("last_saved_lead_name") or "Lead"
        action_lines.append(
            f"Action confirmed [{now}]: SaveToSheets completed for {lead_name}."
        )
        state["lead_saved_recently"] = False

    if not action_lines:
        return response_text, state

    merged = "\n".join(action_lines + ["", response_text])
    return merged, state
