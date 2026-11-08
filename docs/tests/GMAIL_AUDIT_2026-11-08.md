# Gmail deep audit - 8 Nov 2026 (v0.706)

Three read-only audits of the Gmail lane (provider layer, agent tools, speed / call path), every finding checked in
the code. Owner ask: "GO DEEP IN GMAIL --- FIND ALL POSSIBLE FLAWS --- THAT HOOLA AI IS STRUGLING AND FAILING".

## Fixed in v0.706
| # | Flaw | What she saw | Fix |
|---|------|--------------|-----|
| 1 | New HTTPS client per Gmail request + one request per mail, in a row | email_check 7-27 s | one pooled keep-alive client, metadata 8 at a time, token read once |
| 2 | Model saw only 6 of 50 fetched mails (6k result cap, ~720 chars a row) | it re-asked / looped | slim rows (no to / message_id / false flags, 140-char snippet), cap 12k |
| 3 | No "more mails" signal | check -> archive loop | `more: true` + a stop-if-same note |
| 4 | `email_threads act=trash` trashed whole conversations with NO card / cap | silent delete risk | refused, routed to email_delete (card) |
| 5 | `email_thread` with a reply's message id -> 404 | "Yeh email nahi mila (shayad hata di gayi)" for real mails | th: stripped, message id -> thread id fallback |
| 6 | Watcher's 2nd history page = TypeError | new-mail alerts stall on a busy inbox | history(page_token) |
| 7 | 429 / 5xx went straight to the model as raw JSON | random "Gmail error 429" | 3 retries with backoff / Retry-After |
| 8 | Typo address accepted (kunaltelgote23 vs kunaltlgt23) | draft to a wrong person | near-miss check vs known contacts, `check_address` on the draft |
| 9 | A fix made a 2nd live card (no edit / cancel tool) | two cards, tap the wrong one | email_draft `replace_id` cancels the old card |
| 10 | Reply with another `account` sent from the wrong box | thread split / refused | a reply always goes from the box the mail came to |
| 11 | Recipient name with a comma ("Sharma, Ravi") refused at send | send failed | getaddresses |
| 12 | Editing a Gmail draft dropped its Bcc | Bcc vanished | Bcc carried over |
| 13 | "primary" tab refused by set_category | "primary mein daalo" failed | alias to CATEGORY_PERSONAL |

## Still open (next wave)
- Settings that need scopes consumer OAuth cannot get: delete-forever (`https://mail.google.com/`), forwarding / send-as
  create (`gmail.settings.sharing`) -> they 403 and say "Gmail dobara jodiye" in a loop. Needs a plain "not supported" line.
- Expired sign-in (invalid_grant / GoogleReconnect) reaches the model as raw JSON / a non-MailError instead of NotConnected.
- Snooze says done when the archive / wake step failed; archiving one message of a thread leaves the thread in the inbox.
- Two `draft_id` meanings (Hoola card id vs Gmail draft id) on email_draft vs email_drafts.
- No server-side "act on every mail matching this query" (paged, with a card above N) - bulk jobs still loop check -> act.
- Bulk archive has no confirm card (archive is reversible; her G19 expected one) - her decision.
- Chat turns resend the whole chat (165-180k chars a step) to GLM, no prompt cache; old tool results cleared only past 40k.
- Voice-started background work loses the call history trim inside goals / crews.
- GLM door has no streaming: the call hears nothing until the whole answer is written.
- `email_drafts edit` writes To / Cc without resolving names; > 10 visible recipients not warned; a bare id with 2 boxes
  goes to the default box; `email_thread` up to 90k chars in one result; undo window shows as "SCHEDULED".
