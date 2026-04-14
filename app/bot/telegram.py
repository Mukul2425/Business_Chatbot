import requests
from app.config import TELEGRAM_TOKEN

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id, text, parse_mode="HTML"):
    """
    Send message to Telegram chat.
    parse_mode: 'HTML', 'Markdown', 'MarkdownV2', or None
    """
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    try:
        response = requests.post(f"{BASE_URL}/sendMessage", json=payload)
        if not response.ok:
            print(f"Telegram error: {response.text}")
    except Exception as e:
        print(f"Error sending message: {e}")