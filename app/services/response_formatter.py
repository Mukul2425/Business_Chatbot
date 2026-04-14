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


def wrap_markdown(text):
    """Wrap text safely for Telegram markdown"""
    return text.replace("_", "\\_").replace("*", "\\*")
