# CALL + CHAT: two sections, one memory — the plan

Owner (7 Nov 2026): "KEEP CHAT AND VOICE CALL SECTION SEPERATE BUT SHARE A MEMORY --- FIRST MAKE A PERFECT PLAN".
Nothing is built yet. This is the plan, read from the real code at v0.645.0.

## 1. What happens today (checked in the code)

| # | What | Where | Effect she sees |
|---|------|-------|-----------------|
| A | The phone opens a call ON the chat she has open: `call_session.dart` sends `conv: app.conversationId` to `/api/voice/ws`. The call and the chat are the SAME conversation. | `lib/call_session.dart:221`, `main.py voice_ws` | Everything from a call lands in that chat. |
| B | Every work ask on a call (`santosh_kaam`, the Haiku brain) runs as a full chat turn on that conversation (`turn_inbox.run_owned(... self.conv ...)`): her words are saved as `[Voice call] ...`, the spoken answer is saved, and both are published as `message` events. | `voice.py _delegate` (≈2915) | A user bubble + a reply bubble in the chat for every call question. |
| C | Every tool the call runs publishes a `work` row to the chat. | `voice.py` ≈3144 / 3209 | Tool rows in the chat. |
| D | Without the brain mode, every spoken turn is saved into the chat (`_save_turn`). | `voice.py:920` | Same as B. |
| E | Approval / payment / draft cards made during a call go to that chat. | `bus.publish(self.conv, ...)` | Cards in the chat. |
| F | When the call ends, a call receipt card is posted into the chat. | `voice.py` ≈3824, `callreceipt.make(self.conv, ...)` | One more card. |
| G | Every assistant `message` event becomes a phone notification (`push.render` "message"), including replies made DURING a live call. Only the server ring (`voice_ring`) is held back while a call is live. The phone shows every push, even when the app is open (no foreground check in `SantoshPush.kt`). | `push.py:96`, `push.py on_event` | A notification for every reply, chat or call. |

So the complaint is exact: today a call IS the chat, and every reply is a notification.

## 2. What we want

1. **Two sections.** The chat shows only what she typed and what Hoola answered there. Calls get their own section, **Calls**: a list of calls (date, length, one-line summary, the tasks done, the cards), and each call opens to its full transcript and results.
2. **One memory.** What she says on a call is known in the chat, and what she says in chat is known on the call, without copying messages across.
3. **Calm notifications.** No notification for words she already heard on a call. A chat reply notifies only when she is not looking at the app. Things that need HER (approve, pay, a blocked job, a finished long job, a reminder) still notify.

## 3. The design

### 3.1 A call gets its own conversation (server)
- When a call starts, the server makes (or, on `resume`, reuses) a **call conversation**: a normal `Conversation` row with new nullable columns `kind = "call"`, `origin_conv = <the chat she called from>`, `call_id`.
  - It inherits the origin chat's `project_id` (Session fence) and incognito flag, so the memory rules stay as they are.
- The phone keeps sending the chat id. The server does the mapping, so **old APKs work unchanged**.
- Everything in table 1 rows B to F goes to the call conversation instead of the chat:
  - brain turns (`run_owned` gets the call conversation),
  - work rows,
  - `_save_turn`,
  - cards,
  - the receipt.
- The call conversation is left out of the chat list (`chatlist` / `GET /api/conversations` filter `kind != "call"`). The console and the phone show it only in Calls.
- A long job started on a call that finishes after the call ended keeps its place:
  - its result goes to the call record (the orphan note already does this);
  - the next call opens with it;
  - she gets one "kaam poora" notification.
- The `turn_inbox` restart path carries the call conversation, so a re-run job does not fall back into the chat.

### 3.2 One memory, both directions
Most memory is already shared by tenant. The call conversation sits in the same scope as the chat she called from (same `project_id`), so the fence (`app/fence.py`) lets these through on both sides:
- the facts Hoola picks up,
- her "yaad rakhna" facts,
- the diary,
- the running-jobs block,
- the coder memory,
- `yaad_khojo`.

What is added on top:
- **Call to chat:**
  - When a call ends, ONE short summary row is written to the work diary: what she asked, what was done, what is pending. It is the same text as the receipt, but it is not a chat message.
  - The chat's memory block shows "recent calls" (the last 3 summaries, small).
  - `yaad_khojo` can open a call's full transcript.
  - So in chat, "call par maine kya kaha tha" works.
- **Chat to call:**
  - The call brief today reads its own conversation's checkpoint. After the split, it reads the **origin chat's** last few exchanges (capped, like `voice_brain_history`) plus its checkpoint.
  - So on a call, "abhi chat mein jo likha" works.
- **The call's brain** (Haiku `santosh_kaam`) runs on the call conversation, so it sees this call's own questions and answers, plus the shared memory above.

### 3.3 Notifications
- **No push for messages in a call conversation.** She heard them. The exception is a reply that arrives after the call ended, which gets one push.
- **No push for a chat reply while she is in the app.** The phone sends "I am open on chat X" (a heartbeat over the stream it already keeps). The server skips the `message` push for that chat while the heartbeat is fresh. The phone also hides a notification for the chat on screen, in case a push arrives anyway.
- Everything that needs her stays a push, unchanged:
  - approvals, payments, drafts to send,
  - a blocked or finished long job,
  - reminders, the ring.
- If a call is live, a card that needs her tap is shown on the call screen. It is not also pushed: she is holding the phone, and the call tells her.

### 3.4 The Calls section
- **Phone:** a Calls tab.
  - A list of calls: time, length, one-line summary, task count, any open cards.
  - Tapping a call opens its transcript, its tool rows, its cards (tappable: approve / pay work as in chat) and its result lines.
  - "Call again" starts a call from the same origin chat.
- **Console:** a Calls page in the sidebar with the same list and detail, read through `GET /api/calls` and `GET /api/calls/{id}`.

## 4. Phases

| Phase | What | Phone change? |
|-------|------|---------------|
| P1 SPLIT | Call conversation per call (columns + mapping in `voice_ws`); brain turns, work rows, saves, cards, receipt go to it; chat list hides it; resume and restart keep it. | No — old APK works |
| P2 SHARED MEMORY | Call summary into the diary at call end; "recent calls" in the chat memory block; the call brief reads the origin chat; `yaad_khojo` finds calls. | No |
| P3 CALM NOTIFICATIONS | No push for call-conversation messages; the app-open heartbeat skips chat pushes; cards on a live call are not pushed twice; the phone hides a push for the chat on screen. | Yes (heartbeat + hide) |
| P4 CALLS SECTION | `/api/calls` routes; phone Calls tab; console Calls page. | Yes |
| P5 PROOF | Tests + one real call (see §6). | — |

P1 + P2 ship together, so the chat never loses what was said on a call: the moment the messages stop landing in chat, the memory must already carry them.

## 5. Edge cases covered
- **Incognito chat:** the call is incognito too, so nothing is remembered.
- **A call from a Session chat:** the call stays in that Session.
- **Network drop:** a network drop and resume (`?resume=`) keeps the same call conversation.
- **Server restart mid-job:** the `turn_inbox` row holds the call conversation.
- **Two calls at once on two devices:** each gets its own call conversation.
- **Money:** money still moves only on her tap. A card from a call is tappable on the call screen and in Calls.
- **Old calls already in her chats:** they stay where they are (no migration). Only new calls go to Calls.
- **Ring and reminder rules:** "never ring over a live call" now checks the call's origin chat too.

## 6. How we will know it works
Automated tests:
1. A call ask adds **0 messages and 0 work rows** to the chat, and adds them to the call record.
2. A fact said on a call is recalled in the chat, and a fact typed in chat is known on the next call.
3. Asking in chat "call par kya hua" returns the call summary.
4. A call reply produces **0 pushes**. A chat reply while the app is open produces 0 pushes; with the app closed, it produces 1.
5. An approval card from a call is tappable in Calls, and a resumed call keeps its record.
6. An old APK (sending only the chat id) still gets a working call.

Live check: one real call with a work ask. The chat stays clean, Calls shows it, chat can answer about it, and no notification arrives for the call.

## 7. Decisions for the owner (recommended first)
1. **Calls list:** one record per call (recommended), or one long "Calls" thread.
2. **Chat reply notifications:** only when the app is closed or in the background (recommended), never, or always (today).
3. **Old calls already in chats:** leave them (recommended), or move them into Calls.
4. **Cards from a call:** call screen + Calls + a notification only if the call has ended (recommended).
