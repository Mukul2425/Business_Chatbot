#!/usr/bin/env python3
"""Test the operational lead management flow"""
import sys
sys.path.insert(0, '/Users/mukul/Documents/PROJECTS/Telegram_ai_bot')

from app.services.sheets_service import load_all_data
from app.services.conversation_flow_ops import process_message, get_initial_message

# Load data
load_all_data()
print("✅ Data loaded\n")

# Simulate conversation (mimic webhook behavior)
user_state = {}
chat_id = 123456

# Initial bot greeting (sent on first contact by webhook)
print("📌 [BOT SENDS] Initial Greeting:")
response = get_initial_message()
print(response + "\n")
# Note: webhook initializes state here but doesn't process first input

# Now simulate subsequent messages
test_inputs = [
    ("Mukul Kumar", "Name input"),
    ("9876543210", "Phone input"),
    ("Gurgaon", "Location input"),
    ("3", "Space type (3BHK)"),
    ("15-20 lakhs", "Budget"),
    ("Within 3 months", "Timeline"),
    ("1", "Consultation agreement (Yes)"),
    ("25-Apr-2026 14:30", "Preferred datetime"),
]

for user_input, description in test_inputs:
    print(f"👤 [USER] {user_input} ({description})")
    response, user_state = process_message(chat_id, user_input, user_state)
    print(f"📌 [BOT SENDS]\n{response}\n")

print("\n✅ Operational flow test complete!")
print("\nFinal User State:")
import json
for key, value in user_state.get(chat_id, {}).items():
    print(f"  {key}: {value}")

