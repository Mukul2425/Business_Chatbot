from fastapi import FastAPI, Request
import logging
from app.services.sheets_service import load_all_data
from app.services.conversation_flow import process_message, get_initial_message
from app.bot.telegram import send_message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 🔥 USER STATE MANAGEMENT
user_state = {}

# Load all sheets at startup
try:
    load_all_data()
    logger.info("✅ All data sheets loaded successfully")
except Exception as e:
    logger.error(f"❌ Error loading sheets: {e}")


@app.post("/webhook")
async def webhook(req: Request):
    """
    Main webhook handler for Telegram messages.
    Processes message through: Flow Engine → FAQ → Gemini LLM
    """
    data = await req.json()
    global user_state

    try:
        message = data.get("message")
        if not message:
            return {"ok": True}

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return {"ok": True}

        logger.info(f"📨 [{chat_id}] {text}")

        # Initialize new user
        if chat_id not in user_state:
            user_state[chat_id] = {
                "current_step": "start",
                "selected_service": None,
                "lead_name": None,
                "lead_phone": None,
                "lead_location": None,
                "lead_stage": None,
            }
            response = get_initial_message()
            send_message(chat_id, response)
            logger.info(f"👤 New user initialized: {chat_id}")
            return {"ok": True}

        # Process message through conversation flow
        response, updated_state = process_message(chat_id, text, user_state)
        user_state = updated_state
        
        # Send response
        send_message(chat_id, response)
        logger.info(f"✅ Response sent to {chat_id}")

    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        try:
            send_message(chat_id, "Sorry, something went wrong. Please try again! 🔄")
        except:
            pass

    return {"ok": True}


@app.get("/")
def home():
    return {"status": "running"}