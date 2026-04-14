# SpacesTalk Hybrid AI Chatbot

Hybrid chatbot for SpacesTalk that uses:
- Flow engine from Google Sheets for deterministic conversations
- FAQ keyword matching for common questions
- Gemini fallback only when needed
- Lead capture with local persistence in CSV

## Current Architecture

1. User message arrives on /webhook
2. Bot tries flow match from services_flow sheet
3. If no flow match, bot tries FAQ search
4. If no FAQ match, bot calls Gemini with business context
5. If consultation is selected, bot captures lead in data/leads.csv

## Project Setup

### 1. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

Create .env from .env.example:

```bash
cp .env.example .env
```

Set values:
- TELEGRAM_TOKEN from BotFather
- GEMINI_API_KEY from Google AI Studio

### 3. Run server

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/
```

Expected: {"status":"running"}

## Test With Telegram (Real Bot)

Telegram requires a public HTTPS webhook URL.

### Option A: Local testing with ngrok

1. Start app locally on port 8000
2. Run ngrok:

```bash
ngrok http 8000
```

3. Copy HTTPS URL from ngrok, for example:
https://abc123.ngrok-free.app

4. Set Telegram webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://abc123.ngrok-free.app/webhook"
```

5. Verify webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebhookInfo"
```

6. Open Telegram and send message to your bot.

### Option B: Production deployment

Deploy FastAPI app to a public host with HTTPS (Railway, Render, Fly.io, VM + Nginx).
Set webhook URL to: https://your-domain.com/webhook

## Google Sheets Template Recommendations

Use these sheets and columns:

1. pricing
- Category | Min Price | Max Price | Notes

2. services_flow
- Step | Option | Response | Next Step

3. faq
- Question | Keywords | Answer | Category

4. inventory
- Item | Availability | Price | Notes

5. contact
- Type | Value

6. leads
- Name | Phone | Location | Requirement | Timestamp | Status

Current code saves leads to local data/leads.csv.

## How Lead Capture Works

When user reaches consultation yes path:
1. Ask name
2. Ask phone
3. Ask location
4. Save lead with status=new into data/leads.csv

## Troubleshooting

1. ModuleNotFoundError: pandas
- Activate venv and reinstall requirements.

2. Telegram sends no messages
- Check TELEGRAM_TOKEN in .env
- Check getWebhookInfo output for last_error_message

3. Gemini fallback not working
- Verify GEMINI_API_KEY
- Check logs for Gemini error message

4. Sheets not loading
- Ensure published Google Sheets CSV URLs are valid and public

## If You Move From Telegram To WhatsApp Later

Do not change core logic. Replace only transport/integration layer.

What changes:
1. Replace Telegram webhook payload parsing in app/main.py with WhatsApp payload format.
2. Replace app/bot/telegram.py with a WhatsApp sender service.
3. Add provider credentials and webhook verification flow.

What remains same:
1. app/services/conversation_flow.py
2. app/services/faq_service.py
3. app/services/gemini_service.py
4. app/services/sheets_service.py
5. app/services/leads_service.py

Typical WhatsApp providers:
- Meta WhatsApp Cloud API
- Twilio WhatsApp API
- Gupshup/360dialog

Minimal migration plan:
1. Create app/channels/whatsapp.py sender
2. Create app/routes/whatsapp_webhook.py parser
3. Call existing process_message(chat_id, text, user_state)
4. Send response through WhatsApp API

## Quick Start Checklist

1. Fill .env
2. Start uvicorn
3. Start ngrok
4. Set Telegram webhook
5. Send test message: Hi
6. Complete flow: 1BHK -> 2-5L -> Yes -> provide details
7. Check saved leads in data/leads.csv
