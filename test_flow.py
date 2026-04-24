#!/usr/bin/env python3
"""Test hybrid assistant + lead workflow"""
import sys
sys.path.insert(0, '/Users/mukul/Documents/PROJECTS/Telegram_ai_bot')

from app.services.sheets_service import load_all_data
from app.services.conversation_flow_hybrid import process_message, get_initial_message

# Load data
load_all_data()
print("✅ Data loaded\n")

# Simulate conversation (assistant first, booking later)
user_state = {}
chat_id = 123456

# Initial bot greeting (sent on first contact by webhook)
print("📌 [BOT SENDS] Initial Greeting:")
response = get_initial_message()
print(response + "\n")

# Now simulate mixed interaction
test_inputs = [
    ("Namaste", "Hindi greeting"),
    ("3BHK ka timeline kya hota hai?", "Hinglish assistant Q&A"),
    ("book consultation", "Lead flow trigger"),
    ("Mukul Kumar", "Name input"),
    ("9876543210", "Phone input"),
    ("Gurgaon", "Location input"),
    ("skip", "Space type skipped"),
    ("skip", "Budget skipped"),
    ("change phone 9899991111", "Edit phone command during lead flow"),
    ("skip", "Timeline skipped"),
    ("resume booking", "Resume booking command"),
    ("yes", "Consultation agreement"),
    ("25-Apr-2026 14:30", "Preferred datetime"),
    ("What materials do you recommend for kitchen cabinets?", "Assistant Q&A after booking"),
    ("book consultation", "Second booking trigger"),
    ("cancel booking", "Cancel booking command"),
]

for user_input, description in test_inputs:
    print(f"👤 [USER] {user_input} ({description})")
    response, user_state = process_message(chat_id, user_input, user_state)
    print(f"📌 [BOT SENDS]\n{response}\n")

print("\n✅ Hybrid flow test complete!")
print("\nFinal User State:")
for key, value in user_state.get(chat_id, {}).items():
    print(f"  {key}: {value}")

