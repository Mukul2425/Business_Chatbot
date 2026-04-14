#!/usr/bin/env python3
"""Quick test of the bot components"""
import sys
sys.path.insert(0, '/Users/mukul/Documents/PROJECTS/Telegram_ai_bot')

from app.services.sheets_service import load_all_data, get_faq, get_services, get_pricing

print("Loading sheets...")
load_all_data()

print("✅ All sheets loaded!\n")
print(f"📋 FAQ: {len(get_faq())} questions")
print(f"🔀 Services Flow: {len(get_services())} flow steps")  
print(f"💰 Pricing: {len(get_pricing())} categories")
print(f"\nServices available: {get_pricing()['Category'].tolist()}")
