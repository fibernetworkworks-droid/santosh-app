---
name: whatsapp-campaign
description: Run a WhatsApp campaign the official Meta way, consent first
when_to_use: whatsapp campaign, whatsapp broadcast, bulk whatsapp, whatsapp marketing
---
GOAL: messages reach real customers with zero rule breaks.

1. CONSENT FIRST: only rows with an opt-in column marked yes may be messaged.
   No consent column = ask the owner before anything is prepared.
2. Clean the sheet: fix Indian number formats (+91), drop duplicates, mark bad
   numbers failed - they are never retried.
3. Template: write it in her language, check it against WhatsApp's rules
   (no surprising content, variables mapped), submit through the OFFICIAL
   Cloud API only. Test mode approves in ~20s; live waits for Meta.
4. Send law: dry-run unless she clearly said send; daily limit respected across
   ALL campaigns; leftovers go after the reset; one tap before the first send.
5. Track sent/delivered/read/replied and post the report back into her chat.
NEVER: personal WhatsApp automation, unofficial bridges, buying lists.
