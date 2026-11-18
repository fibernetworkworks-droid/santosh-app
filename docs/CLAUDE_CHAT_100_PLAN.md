# Claude Chat 100%: what makes Claude chat reliable and smooth, where Hoola stands, and the plan

Owner's ask (18 Nov 2026): "Check how Claude chat can do all work properly and reliably. Also every output and
conversation feels relevant and smooth. We want 100% same for Hoola chat. First go deep and find Claude chat all details,
every feature and smoothness strategy."

The research behind this is in `docs/research/claude_chat/` (read `00_INDEX.md` there). It covers Anthropic's help
centre, release notes, the claude.ai system prompts Anthropic publishes, Anthropic's engineering posts and API docs, and a
code audit of Hoola at v0.997. Claude.ai's private code is not published. Where this says "Claude does X", it means the
published rule or the documented behaviour.

This builds on `docs/CLAUDE_PARITY_PLAN.md` (9 Nov). Its Phases 0-7 are built and on by default (v0.732-v0.738). This
plan covers what that one did not, and what has drifted since: the Box (v0.958-v0.979), the extra lines added to
replies, and the screen.

---

## 1. The short answer

Claude chat feels reliable and smooth because of three layers, and each one matters.

1. **The words.** Every reply follows a small set of published rules:
   - the answer comes first, with no opener;
   - the length matches the ask, and conversation is written as plain prose;
   - it asks at most one question;
   - it never claims work that a tool did not show;
   - it does a step instead of announcing it;
   - when part of a job is blocked, it finishes the rest and names the gap.
   Nothing is added to the reply that the model did not write.
2. **The work.** One strong model runs a plain loop (think, call tools, read the results, repeat) until it has an
   answer. Errors come back as instructions, tools are few and distinct, and the prompt is stable and cached. A done
   claim needs evidence, and old tool results are cleared so a long chat stays sharp.
3. **The screen.** Words land at a steady pace and the view stays pinned to the bottom until she scrolls up. There is
   one working row with a timer, "Thinking" folds to a summary, and web answers carry their sources. Stop is clean, and
   leaving a running chat and coming back shows it exactly as it is.

**The honest part.** Most of layer 2, and some of layer 1, depends on the model. Hoola's live chat brain today is
**Qwen 3.8 27B** through OpenRouter (healthz, 18 Nov). It is a small, cheap model. On top of that, the Box can change
the model between messages, or even inside one. Even a perfect copy of Claude's harness on that model will not answer
like Claude Opus or Sonnet. The model choice is the biggest single lever, and it is her decision (section 6).

---

## 2. Claude chat, feature by feature, against Hoola

Status: **Same** = Hoola already has it. **Close** = small difference. **Gap** = missing or clearly different.

| Area | What Claude does (source in research files) | Hoola v0.997 | Status |
|---|---|---|---|
| Every message reaches the model | Always | Yes, since v0.738 (OTP / PC answers excepted, by design) | Same |
| One model per chat | User picks; switches only on a flagged request, with a notice and a label | The Box picks per message, can hand over mid-message, 1 in 10 messages use the old routing, a failed check posts a correction from another model | **Gap** |
| Effort / thinking setting | Low → Max picker; thinking shown as "Thinking" + timer, an expandable summary above the reply | Adaptive thinking on; console "thought for" fold is dead code (`v2.js:1059`); thinking never stored | **Gap** |
| Streaming at reading speed | Steady word pacing | Pacer ~20 ms a word on requestAnimationFrame | Same |
| Stick to bottom + jump to latest | Follows while at the bottom, stops when she scrolls up | Yes (`v2.js:674-686`, wheel / touch / keys, ResizeObserver, Jump button) | Same |
| Stop | Stop or redirect while it works | Stop + steering a running job | Same |
| Edit + branch | Edit makes a new version (not in the new experience) | Edit / branches exist | Same |
| Retry | Retry the reply | Newest reply only, not while working | Close |
| Copy / feedback | Copy, thumbs | Yes | Same |
| Working rows | One indicator; progress per step in agentic work | One working row, steps fold under "Worked for" | Same |
| Progress words between steps | One line before starting, an update only on an important find or a change of direction, a recap that stands on its own | Prompt says "one short line after EACH step" and the server adds narration lines | **Gap** |
| Web search + citations | "Every response includes citations", searching indicator | Links in text by prompt rule; a Sources card only for her knowledge base | **Gap** |
| Research mode | Chained searches, 5-45 min, one cited report | Research chip, in-turn research engine | Close |
| Artifacts | Side panel, versions, edit in place, share levels, export to Word / PDF / Slides | Artifact panel, versions, undo, share; `update` not streamed; two overlapping artifact tools | Close |
| Inline visuals | Charts / diagrams drawn inside the reply | None in the reply | **Gap** |
| File upload | 20 files × 500 MB, PDFs with pictures ≤100 pages | 20 × 30 MB, archives opened (v0.997) | Close |
| File creation | Real .docx / .xlsx / .pptx / .pdf from a code sandbox | pylab + doc_studio | Same |
| Projects | Instructions + knowledge + its own memory; RAG search when large | Instructions + notes; project files not used in small mode; no project search | **Gap** |
| Memory | Topic entries read and updated during chats, "remember this", pause / reset, sensitive topics off | Memory page, remember, switches (v0.611) | Same |
| Past-chat search | Shown as a tool call with links to the source chats | yaad_khojo / haal_ki_chats | Same |
| Incognito | Not saved, not in memory | Yes (v0.250) | Same |
| Long tasks | New experience: runs in the cloud, continues if she leaves, results land in the conversation | Long turns in the chat; goal rounds + job results come back as follow-up messages | Close |
| Leave and come back | Running work shown as it is | Fixed in v0.996 | Same |
| Long chats | Summarises early messages near the limit, history kept | Compaction at 60 / 75 % | Same |
| Approval before actions | Allow once / Always allow / Auto / Manual | Confirm cards; money always her tap | Same (stricter on purpose) |
| Voice | Voice mode with Stop, transcript kept | Live call, transcript, receipts | Same |
| Errors and limits | Exact, calm messages ("5-hour limit reached - resets 3 pm") | Canned lines; some mid-reply errors replace the reply | Close |
| Nothing added to the reply | The reply is the model's words only | Several lines added (section 3, item 3) | **Gap** |

---

## 3. Where Hoola differs: the things she feels

Listed in the order she would notice them.

1. **The model changes under her.**
   - The Box chooses a model for each message (`turnbox.begin`, `agent/santosh.py:3250`).
   - It can hand a call to a backup model in the middle of a message (`pipeline/runner.py`).
   - One message in ten uses the old routing (`pipeline_holdout_pct` 10).
   - A failed final check posts a separate correction message, written by a model one level up
     (`pipeline/turnbox.py:452-519`).
   - On a small model this shows up as replies that change voice and quality from one message to the next.
2. **Too many progress words.**
   - Hoola's prompt asks for "one short line after each step" (`agent/core_prompt.py`).
   - The server adds narration lines on top (`agent/santosh.py:2776-2793`).
   - Claude says one line before it starts, gives an update only when something important changes, and ends with a
     recap that stands on its own.
3. **Lines the model did not write**, which Claude never shows:
   - "Made with …" receipt (`pipeline/receipt.py`).
   - The fix-round correction message (Box).
   - The "(Dhyaan: …)" note under knowledge-base answers (`gyaan/answer.py:78-101`).
   - "One second, looking into it…" (the ack).
   - "Changing my approach - taking a different route."
   - "Done." / "Sorry, I did not understand…" when the model said nothing.
   - The ▶ / 🔄 / ⚠ / ⏹ job-watch lines (`kaamwatch.py`).
4. **Missing reply rules.** The core prompt has "answer first", "length follows the question" and "one question". It does
   not have these Claude rules:
   - no bullets in casual or emotional talk, or when declining;
   - a change to one part gives back the change, not the whole piece;
   - do the step instead of announcing it ("I'll…", "Shall I…?");
   - when blocked, finish everything else and name what was left;
   - check a correction before accepting it, and own a mistake without grovelling;
   - never open with praise;
   - write the final recap for someone who saw none of the work.
5. **Thinking is invisible on the console and gone after a reload.**
6. **Web answers have no sources row.**
7. **No prompt caching on the OpenRouter path.** The fixed ~10k-character prompt is paid for and re-read in full every
   turn, which makes it slower and costlier. Needs measuring first.
8. **Smaller items:**
   - two artifact tools in the core list;
   - no charts inside a reply;
   - project files are not used by the chat;
   - retry works only on the newest reply.

---

## 4. The smoothness strategy, as rules Hoola will follow

**The words** (`docs/research/claude_chat/02_reply_rules.md`, ranked list at the end):
1. Answer first, with no preamble or praise.
2. Match the length and effort to the ask.
3. Write prose by default. Use bullets, headings and bold only when asked or when the content needs them, and never in
   chat, emotional talk or a refusal.
4. Try to answer an unclear ask before asking about it; ask at most one short question.
5. Never claim work a tool did not show. Say plainly what failed, what was skipped and what was not checked.
6. Do the step instead of announcing it.
7. When something is blocked, finish the rest and name the gap.
8. Push back honestly and kindly.
9. Keep caveats few and short.
10. Own mistakes without grovelling.
11. Reply in her language and tone.
12. In long work: one line before starting, then updates only when something changes.
13. The recap leads with the outcome, in plain words.
14. Search for anything that may have changed.
15. Leave the machinery out of the reply.

**The work** (`03_reliability.md`, ranked list at the end):
1. A pass / fail check with evidence before "done".
2. A separate check decides "done".
3. Durable state outside the conversation.
4. Correct loop mechanics: every tool call paired with its result, every stop reason handled.
5. Error results that say what to try next.
6. Few, distinct tools.
7. Clear old tool results.
8. Compaction.
9. Sub-agents only for parallel work.
10. Thinking kept on, with effort high enough that checks are not skipped.
11. Gates on money and other actions that cannot be undone, in code.
12. Graded evals measured as pass^k, not a single pass.

**The screen** (`04_smoothness.md`, ranked list at the end):
1. The server owns the reply, and the screen reattaches to it.
2. Finished blocks never redraw.
3. Append text, with one paint per frame.
4. Stick to the bottom until she scrolls up.
5. A "jump to latest" button.
6. Steady word pacing.
7. Half-written markdown is closed before it is drawn.
8. Code and tables are drawn as code and tables from the first line.
9. Her message appears at once, with a working row and a timer.
10. Thinking and tool rows are folded, present tense while running and past tense when done.
11. A clean Stop.
12. An error mid-reply keeps the words and adds Retry.
13. Retry and edit make versions.
14. Only new words fade in.
15. The phone list behaves the same way.

Hoola already has items 1, 3-6, 9 and 11 of the screen list.

---

## 5. The plan

Each phase ships as its own version with a switch, so it can be turned off if it makes things worse. C0 comes first,
because every later phase is judged by it.

### C0. The Claude Chat card (measure first)
- 40 real asks taken from her own chats: the BSNL RAR email, GST questions, a casual "kaise ho", a correction, a vague
  ask, a blocked job, a long research ask, an edit to one paragraph.
- Each ask is run 3 times through the real pipeline. The checks are in code:
  - the first sentence answers the ask;
  - no line in the reply that the model did not write;
  - every figure traced to a tool result;
  - one model for the whole chat;
  - the formatting rules;
  - the length band;
  - for actions, the end state really exists.
- The score is **pass^3** (all three runs pass), not the best of three.
- `python -m app.quality claudechat`, plus a vps-ops job.
- Prints the score per rule, so each later phase shows what it moved.

### C1. One model per chat
- The Box chooses once, at the first message, and the chat keeps that model.
- A hand-over happens only on a hard failure (error, refusal, timeout). It is shown once as a small notice: "Switched to
  X for this reply because Y".
- The fix round runs **before** she sees the answer and replaces the draft. It never posts a second message.
- The holdout share, if she keeps it, is chosen per chat, not per message.
- The "Made with" receipt moves into the folded steps, not under the reply.
- Files: `pipeline/turnbox.py`, `pipeline/box.py`, `pipeline/receipt.py`, `agent/santosh.py`, `static/console/v2.js`,
  `lib/ui/model_receipt.dart`.

### C2. Nothing stapled on
- Removed from replies, or folded into the working row, and kept as data (no information lost):
  - the Dhyaan note;
  - "Changing my approach…";
  - "Done." / "Sorry, I did not understand…";
  - the ack placeholder;
  - the ▶ / 🔄 / ⚠ / ⏹ watch lines.
- A finished background job comes back as **one** message written by the model, in the chat it belongs to.
- When the model said nothing, it is asked once more instead of a canned line being shown.

### C3. Claude's reply rules + the progress pace
- `agent/core_prompt.py` gains the missing rules listed in section 3, item 4, written in the "do this" form Anthropic
  recommends.
- The pace rule changes from "a line after each step" to:
  - one line before starting;
  - an update only when something changes;
  - a recap that stands on its own.
- The server narration (`santosh.py:2776-2793`) is off by default, keeping only the "she has heard nothing for five
  steps" nudge Anthropic publishes.
- `agent/replystyle.py` is aligned with the same rules.

### C4. Thinking you can see
- Console: a live "Thinking · 7s" row that folds to "Thought for 7s", with a one-line summary.
- The summary is stored, so a reload or a return to the chat shows it.
- Phone: the same, in the new design's Soch card.
- Files: `livereply.py`, `static/console/v2.js` (thinkEvent / THINKS), `lib/ui/chat/hoola_chat.dart`.

### C5. Sources on web answers
- When the turn used google_search / web_fetch, a folded "Searched N sources" row appears under the reply, with titles
  and links.
- Inline [n] markers link to the sources.
- Same drawing as the knowledge-base Sources card.

### C6. Reliability under the hood
- Prompt caching on the OpenRouter path, where the provider supports it, with first-word time and cost measured before
  and after.
- One artifact tool in the core list.
- `artifact update` streams like create.
- An error in the middle of a reply keeps the words and adds an inline Retry.
- Retry on any reply, which makes a version.

### C7. Charts inside a reply
- A fenced data block in the reply is drawn as a chart inside the message, with the existing `charts.js`.
- Copy as image / Download.

### C8. Projects like Claude Projects
- Project files are searchable from the chat with a `project_search` tool (gyaan, scoped to the project).
- The project's instructions ride in every chat of that project.

Order: C0, then C1 + C2 + C3 together (the biggest change in feel), then C4 + C5, then C6, then C7 + C8. C0 runs again
after each step.

---

## 6. Decisions only she can make

1. **The chat model.** Recommended: one model per chat (C1).
   - Which model: keep Qwen 3.8 27B (cheapest), or move the chat to a stronger model through OpenRouter.
   - A stronger model is the only way to get close to Claude's own answer quality. Everything else in this plan improves
     the feel but not the model's intelligence.
   - C0 can run the same 40 asks on two or three candidate models, so she picks with numbers in front of her.
2. **The Box's holdout share** (1 in 10 messages on the old routing, for the P7 week's watch). Keep it per chat, or
   turn it off once the watch is done.
3. **English.** The console adds "reply in English" to every message (her v0.728 decision, SAB ENGLISH). Claude replies
   in the user's own language. This plan keeps her decision unless she says otherwise.

## 7. What Hoola keeps that Claude does not do
- Money never moves without her tap, and payments are cards only.
- Sending, deleting and sharing need a confirm card.
- Her Pehchaan Locker for ID numbers (Claude never saves ID numbers).
- Live voice calls in Hinglish.
- Hoola Network avatars.
- Her PC and Hoola PC.

These stay as they are. The plan changes how chat feels, not what Hoola is allowed to do.
