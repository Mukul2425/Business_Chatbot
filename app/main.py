from fastapi import FastAPI, Request
import logging
import asyncio
from app.services.sheets_service import load_all_data
from app.services.conversation_flow_hybrid import process_message, get_initial_message
from app.bot.telegram import send_message
from app.services.automation_service import run_automation_tick
from app.services.analytics_service import get_latest_events
from app.services.profile_memory_service import bootstrap_state, save_profile

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 🔥 USER STATE MANAGEMENT
user_state = {}


async def _automation_loop():
    """Run reminder + retry automation periodically."""
    while True:
        try:
            result = run_automation_tick()
            if result.get("reminders_sent") or result.get("retries_processed"):
                logger.info(f"🔁 Automation tick: {result}")
        except Exception as e:
            logger.error(f"❌ Automation tick error: {e}")
        await asyncio.sleep(60)

# Load all sheets at startup
try:
    load_all_data()
    logger.info("✅ All data sheets loaded successfully")
except Exception as e:
    logger.error(f"❌ Error loading sheets: {e}")


@app.on_event("startup")
async def _startup_tasks():
    asyncio.create_task(_automation_loop())


@app.post("/webhook")
async def webhook(req: Request):
    """
    Main webhook handler for Telegram messages.
    Hybrid workflow:
    - Assistant answers interior-design queries
    - Lead capture + booking flow runs when requested
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
            default_state = {
                "current_step": "assistant",
                "lead_stage": None,
                "lead_name": None,
                "lead_phone": None,
                "lead_location": None,
                "lead_space_type": None,
                "lead_budget": None,
                "lead_timeline": None,
                "lead_consultation_agreed": None,
                "lead_consultation_datetime": None,
                "call_lead_triggered": False,
                "escalation_triggered": False,
                "gemini_calls": 0,
                "language_pref": "english",
            }
            user_state[chat_id] = bootstrap_state(chat_id, default_state)
            response = get_initial_message(user_state[chat_id])
            send_message(chat_id, response)
            logger.info(f"👤 New user initialized: {chat_id}")
            return {"ok": True}

        # Store user input for escalation detection
        user_state[chat_id]["user_input"] = text
        
        # Process message through operational flow
        response, updated_state = process_message(chat_id, text, user_state)
        user_state = updated_state
        save_profile(chat_id, user_state.get(chat_id, {}))
        
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


@app.get("/health")
def health():
    return {"status": "healthy", "service": "SpacesTalk Operational Lead Bot"}


@app.post("/automation/run")
def run_automation_once():
    """Manual trigger for reminders and call retries."""
    result = run_automation_tick()
    return {"ok": True, "result": result}


@app.get("/analytics/events")
def analytics_events(limit: int = 50):
    events = get_latest_events(limit=limit)
    return {"count": len(events), "events": events}