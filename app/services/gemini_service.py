import requests
from app.config import GEMINI_API_KEY  
from app.services.sheets_service import get_faq, get_pricing, get_inventory, get_contact
from app.services.knowledge_base_service import get_knowledge_base_context


def build_context(query=None, current_step=None, selected_category=None):
    """Build rich business context for Gemini from all sheets"""
    context_parts = []
    
    # Company info
    contact = get_contact()
    if contact is not None and len(contact) > 0:
        context_parts.append("=== COMPANY INFO ===")
        for _, row in contact.iterrows():
            context_parts.append(f"{row.get('Type', '')}: {row.get('Value', '')}")
    
    # Pricing
    pricing = get_pricing()
    if pricing is not None and len(pricing) > 0:
        context_parts.append("\n=== PRICING ===")
        for _, row in pricing.head(4).iterrows():
            context_parts.append(f"{row.get('Category', '')}: ₹{row.get('Min Price', '')} - {row.get('Max Price', '')}")
    
    # Inventory
    inventory = get_inventory()
    if inventory is not None and len(inventory) > 0:
        context_parts.append("\n=== PRODUCTS ===")
        for _, row in inventory.head(5).iterrows():
            context_parts.append(f"• {row.get('Item', '')}: {row.get('Availability', '')}")
    
    # FAQ
    faq = get_faq()
    if faq is not None and len(faq) > 0:
        context_parts.append("\n=== FAQ ===")
        for _, row in faq.head(4).iterrows():
            context_parts.append(f"Q: {row.get('Question', '')}\nA: {row.get('Answer', '')}")

    # Local knowledge base docs
    kb_context = get_knowledge_base_context(query)
    if kb_context:
        context_parts.append(f"\n{kb_context}")
    
    context = "\n".join(context_parts)
    return context[:4000]


def ask_gemini(query, current_step=None, selected_category=None, context_hint=None):
    """Ask Gemini with rich business context and conversation history"""
    context = build_context(query, current_step, selected_category)
    
    conversation_context = ""
    if context_hint:
        conversation_context = f"\nRECENT CONVERSATION:\n{context_hint}\n"
    
    prompt = f"""You are SpacesTalk customer service assistant for Delhi interior design.

CONTEXT:
{context}
{conversation_context}
RULES:
1) Answer ONLY interior design and home/office service questions.
2) Use only the provided context and general domain-safe guidance.
3) Do NOT fabricate prices, timelines, policies, or availability.
4) If exact answer is not present, say this clearly and suggest booking a consultation call.
5) Keep the response professional, concise, and easy to read.
6) Reference previous conversation if relevant to provide continuity.

Question: {query}
Response:"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if res.status_code != 200:
            print(f"Gemini API error: HTTP {res.status_code} - {res.text}")
            return (
                "I could not process that right now. "
                "For personal customizations, please book an appointment or call us at +91-9876543119."
            )
        
        response = res.json()
        
        # Check for error in response
        if "error" in response:
            print(f"Gemini error: {response['error']}")
            return (
                "I could not process that right now. "
                "For personal customizations, please book an appointment or call us at +91-9876543119."
            )
        
        # Check for candidates in response
        if "candidates" not in response or len(response["candidates"]) == 0:
            print(f"Gemini error: No candidates in response - {response}")
            return (
                "I could not process that right now. "
                "For personal customizations, please book an appointment or call us at +91-9876543119."
            )
        
        candidate = response["candidates"][0]
        if "content" not in candidate or "parts" not in candidate["content"] or len(candidate["content"]["parts"]) == 0:
            print(f"Gemini error: Invalid candidate structure - {candidate}")
            return (
                "I could not process that right now. "
                "For personal customizations, please book an appointment or call us at +91-9876543119."
            )
        
        text = candidate["content"]["parts"][0].get("text", "").strip()
        if not text or len(text) < 3:
            return (
                "I could not find an exact answer in our current data. "
                "For personal customizations, you can book an appointment or call us at +91-9876543119."
            )
        return text
    except Exception as e:
        print(f"Gemini error: {e}")
        return (
            "I could not process that right now. "
            "For personal customizations, please book an appointment or call us at +91-9876543119."
        )
