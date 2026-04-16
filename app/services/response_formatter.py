"""
Format responses nicely for Telegram with proper structure and emojis.
"""


def format_welcome():
    """Welcome message with category-first options"""
    return """Welcome to SpacesTalk.

How can we help you today?

Please choose one option:
- 1. Explore by Project Type
- 2. Pricing and Budget
- 3. Process and Timeline
- 4. Consultation and Contact
- 5. Ask Something Else

You can reply with the option number or the option name."""


def format_project_type_prompt():
    """Prompt user to select project type after category selection"""
    return """Please choose your project type:

- 1. 1BHK
- 2. 2BHK
- 3. 3BHK
- 4. Office

You can reply with the number or project name."""


def format_ask_anything_prompt():
    """Prompt user for free-text query"""
    return """Please share your question in one message.

I will answer based on our available data and interior design knowledge.
If your request needs personalization, we can schedule a consultation call."""


def format_service_options(service_type):
    """Format service description with next options"""
    return f"""Project selected: {service_type}

What would you like to know next?
- Price: Budget and pricing details
- Timeline: Estimated delivery duration
- Process: Design and execution steps
- Other: Ask a custom question"""


def format_faq_answer(answer, question=None):
    """Format FAQ answer nicely"""
    if question:
        return f"""Question: {question}\n\nAnswer: {answer}"""
    return f"""Answer: {answer}"""


def format_knowledge_answer(answer, source=None):
    """Format answer sourced from local knowledge base documents"""
    if source:
        return f"""From our knowledge base ({source}):

{answer}"""
    return f"""From our knowledge base:

{answer}"""


def format_projects_fallback():
    """Fallback when project/case-study data is unavailable"""
    return (
        "I could not find a clear case-study match in the current project portfolio data. "
        "If you share your preferred style, budget, and project type, I can suggest relevant project directions. "
        "You can also book a consultation at +91-9876543119 for a curated walkthrough of past work."
    )


def format_materials_fallback():
    """Fallback when material-specific data is unavailable"""
    return (
        "Typical interior materials include plywood or blockboard for cabinetry, laminates or veneers for finishes, "
        "engineered hardware, and gypsum with paint-based finishes for ceilings and walls. "
        "Final material selection depends on budget, durability needs, and style preferences."
    )


def format_project_portfolio_answer(text):
    """Format a portfolio-style answer from case studies"""
    return text


def format_materials_answer(text):
    """Format a materials answer from the knowledge base"""
    return text


def format_pricing_info(pricing_data):
    """Format pricing information"""
    msg = "💰 **Pricing Information**\n\n"
    for category, min_price, max_price, notes in pricing_data:
        msg += f"**{category}**: ₹{min_price} - ₹{max_price}\n"
        msg += f"  _{notes}_\n\n"
    return msg


def format_inventory_list(inventory_data):
    """Format available products"""
    msg = "📦 **Available Products**\n\n"
    for item, availability, price, notes in inventory_data:
        status = "✅" if availability == "Yes" else "⚠️"
        msg += f"{status} **{item}** - {price}\n"
        if notes:
            msg += f"   _{notes}_\n"
    return msg


def format_error():
    """Format error message"""
    return """I could not map that clearly.

Please choose one of these options:
- Explore by Project Type
- Pricing and Budget
- Process and Timeline
- Consultation and Contact
- Ask Something Else

For custom requirements, we recommend booking a consultation call at +91-9876543119."""


def format_not_found_fallback():
    """Fallback when question is not available in trusted data"""
    return """I could not find an exact answer in our current data.

For personal customizations, you can book an appointment or call our team at +91-9876543119.
If you want, share your project type and budget range, and I can provide a practical starting estimate."""


def format_thank_you_reply():
    """Friendly closing reply for gratitude"""
    return (
        "You are welcome. Happy to help. "
        "If you want, I can also guide you on project scope, budget, and next steps."
    )


def format_call_timing_reply():
    """Reply for contact timing questions"""
    return (
        "You can call us between 10 AM and 7 PM. "
        "If you prefer, I can also help you start an appointment request right now."
    )


def format_clarifying_question(question):
    """Format a clarifying question when confidence is medium"""
    return f"One quick clarification before I answer:\n\n{question}"


def format_medium_confidence_answer(answer_snippet):
    """Format answer with a note about partial confidence"""
    return f"""Based on available info:

{answer_snippet}

If you want more specific details, feel free to share more context, or we can pair you with our design team for a personalized consultation."""


def get_varied_budget_response(service_label, min_price, max_price):
    """Get budget response with variation"""
    import random
    
    variants = [
        f"For {service_label}, the typical budget range is {min_price} to {max_price}. "
        "The lower range covers essential finishes with standard materials, while the upper range allows for premium options and custom design elements.",
        
        f"{service_label} projects usually range from {min_price} to {max_price}, depending on material choices and customization. "
        "A mid-range budget typically gives you quality work with good material selection and design flexibility.",
        
        f"You can plan for {service_label} within {min_price} to {max_price}. "
        "The exact amount depends on the scope, finishes you choose, and any special customizations you're looking for.",
    ]
    
    return random.choice(variants)


def get_varied_customization_response():
    """Get customization response with variation"""
    import random
    
    variants = [
        "Customization is very flexible. You can modify modular kitchen layouts, wardrobe internals, lighting designs, false ceilings, and storage solutions. "
        "Since each choice affects cost, we recommend a quick consultation to plan the perfect mix for your needs.",
        
        "We offer wide customization: from kitchen finishes and wardrobe organization to lighting schemes, ceiling designs, and space optimization. "
        "Different combinations affect the budget differently, so discussing your priorities with our team helps us nail the estimate.",
        
        "You have options for nearly everything: kitchen design, wardrobe types, lighting, false ceilings, and more. "
        "The challenge is fitting it within budget, which is why a short consultation helps us find the best balance for you.",
    ]
    
    return random.choice(variants)


def get_varied_timeline_response():
    """Get timeline response with variation"""
    import random
    
    variants = [
        "Timeline varies by scope. A standard home interior typically takes a few weeks from design approval to completion. "
        "Premium customization or complex layouts can take longer, and it also depends on material availability and your site readiness.",
        
        "Most projects complete within a few weeks of execution, but the full timeline includes design approvals and material sourcing, which adds time. "
        "Exact duration depends on your project size and how quickly approvals come through.",
        
        "We usually complete work in a reasonable timeframe, but the exact schedule depends on design complexity, customization choices, and material lead times. "
        "We'll give you a precise timeline once we understand your project details.",
    ]
    
    return random.choice(variants)


def get_varied_process_response():
    """Get process response with variation"""
    import random
    
    variants = [
        "Our process is straightforward: we start with understanding your needs and space, create a design proposal, finalize materials with you, execute the work, and hand over the finished project. "
        "Each step involves your feedback to ensure the result matches your vision.",
        
        "We work in phases: initial consultation and space analysis, design creation, client approval, material sourcing, execution, and final handover. "
        "You're involved at every stage to make sure we're on the right track.",
        
        "From discussion to completion, we follow a structured path: requirement gathering, design mock-ups, material selection, on-site execution, and quality checks. "
        "Your input at each stage keeps us aligned with your expectations.",
    ]
    
    return random.choice(variants)


def format_clarification_pending(question, answer_hint=None):
    """Format a medium-confidence reply that asks for clarification"""
    if answer_hint:
        return f"""Based on what I found so far:

{answer_hint}

{question}"""
    return f"""{question}"""


def format_lead_submission():
    """Format lead capture message"""
    return """Great. We would be happy to connect.

Please share these details:
1. Full Name
2. Phone Number
3. Location (Area/City)

Our design team will contact you shortly."""


def format_lead_name_prompt():
    return "Please share your full name."


def format_lead_phone_prompt():
    return "Thank you. Please share your 10-digit phone number."


def format_lead_location_prompt():
    return "Please share your location or area."


def format_lead_saved(name):
    return (
        f"Thank you, {name}. Your request has been recorded. "
        "Our team will contact you soon during working hours."
    )


def format_contact_info():
    """Format contact information"""
    return """Contact SpacesTalk

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
