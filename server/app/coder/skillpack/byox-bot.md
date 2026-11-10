---
name: byox-bot
description: Build a chat bot: Telegram/Slack commands, state, webhooks
when_to_use: telegram bot, slack bot, chat bot, chatbot banana, discord bot, bot with commands
---
GOAL: a bot that handles commands, remembers user state, and calls an external API.

PHASES
1. Connect to Telegram Bot API (long-poll getUpdates); echo every message.
2. Command parser: /help /status /start; send formatted reply.
3. User state: Python dict keyed by chat_id; remember previous choice.
4. External API integration (weather / quote); format and reply.
5. Webhook mode (HTTPS endpoint + setWebhook); deploy 24/7 on a VPS.

CORE CONCEPTS
- Long-poll: getUpdates?offset=last_update_id+1&timeout=30; ack by consuming.
- Webhook: Telegram POSTs each update to your URL; must be HTTPS.
- State machines: WAITING_FOR_CITY, WAITING_FOR_DATE — drives multi-step flows.

VERIFY: /weather Delhi returns current temperature via a real API call.
