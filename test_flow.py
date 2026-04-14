#!/usr/bin/env python3
"""Test the conversation flow"""
import sys
sys.path.insert(0, '/Users/mukul/Documents/PROJECTS/Telegram_ai_bot')

from app.services.sheets_service import load_all_data
from app.services.conversation_flow import process_message, get_initial_message

# Load data
load_all_data()
print("✅ Data loaded\n")

# Simulate conversation
user_state = {}
chat_id = 123456

# Step 1: Initial message
print("📌 [BOT SENDS] Initial Message:")
response = get_initial_message()
print(response[:100] + "...\n")

# Step 2: User chooses 1BHK
print("👤 [USER] 1BHK")
response, user_state = process_message(chat_id, "1BHK", user_state)
print(f"📌 [BOT SENDS]\n{response}\n")

# Step 3: User asks about budget
print("👤 [USER] 2-5L")
response, user_state = process_message(chat_id, "2-5L", user_state)
print(f"📌 [BOT SENDS]\n{response}\n")

# Step 4: User says yes to consultation
print("👤 [USER] Yes")
response, user_state = process_message(chat_id, "Yes", user_state)
print(f"📌 [BOT SENDS]\n{response}\n")

print("\n✅ Conversation flow test complete!")
