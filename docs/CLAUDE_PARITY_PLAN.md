# Claude Parity Plan: how Claude chat handles a message, and how Hoola gets there

Owner's ask (9 Nov 2026): "Go deep into the Claude ecosystem, extract the flow of how Claude chat does every task end to
end, and give a detailed plan so Hoola can do the same Claude-level work in chat. Go to every point. This is the final
work to improve Hoola."

Sources: Anthropic's public documentation and engineering posts (Building effective agents; Effective context
engineering for AI agents; Writing effective tools for agents; How we built our multi-agent research system; Agent
Skills; the API docs for tool use, tool search, context editing, the memory tool, extended thinking, citations, the
code execution tool and prompt caching), plus how Claude.ai behaves in public use. Claude.ai's private internals are
not published; where this plan says "Claude does X" it means the published pattern or the visible behaviour, not a
claim about hidden code.

Hoola facts below are measured in this repo on 9 Nov 2026 (v0.727), not guessed.

---

## Part 1. The flow: what happens when you send a message to Claude

Claude's chat is one simple loop with good parts. The parts matter more than the loop.

### Stage 1. Your message goes to the model, always
Every message you send reaches the model. Nothing answers in its place: no keyword shortcut approves a card, no side
model gives a quick reply, no classifier rewrites what you said. While Claude is working you can press Stop, and in
Claude Code you can type a new message that joins the running work.

### Stage 2. The request is built from four layers
1. **A fixed system prompt**: who Claude is, how it writes, safety rules, how to use tools. The same text every turn,
   so it is cached (prompt caching) and costs little after the first turn.
2. **Small per-chat context**: date, the user's preferences or style, the project's instructions, a short memory
   summary if memory is on. Short, and only what applies to everyone in every turn.
3. **The whole conversation, word for word**: every earlier message, including Claude's own replies and the tool
   calls and results. Nothing is shortened while it fits.
4. **The tool list**: the tools for this chat, each with a clear description of when to use it. With many tools,
   only the main ones are loaded; the rest are found on demand with tool search.

Anything else (old chats, files, project documents, a user's past work) is not pasted in. Claude fetches it with a
tool when the message needs it ("just in time" retrieval).

### Stage 3. One model for the whole chat
The user picks the model (or the default). That model answers every turn of the chat. It is not swapped mid-chat for
a cheaper one, and a long job is not handed to a different model.

### Stage 4. The model thinks, then answers or calls tools
With extended thinking, the model reasons first (shown in a collapsible "Thought for 8s" row). Then it either writes
the answer or calls one or more tools. Independent tool calls run in parallel.

### Stage 5. The loop
```
model -> tool calls -> results -> model -> more tool calls -> ... -> final answer (no tool call)
```
The turn ends only when the model writes an answer with no tool call. Progress text the model writes between tool
calls ("Searching for X…") streams to the screen as it goes. Thinking can happen between tool calls too (interleaved
thinking), so the model reflects on each result before the next step.

### Stage 6. Tools are few, clear and well described
Anthropic's guidance for tools: a small number of tools with clear, non-overlapping jobs; descriptions written like
instructions to a new colleague (what it does, when to use it, when not to, what each parameter means); results that
return only what the model needs, with ids and links kept, and errors that say how to fix the call. The core tools in
Claude.ai: web search, web fetch, code execution (a Python sandbox that can also create .docx / .xlsx / .pptx / .pdf
files), artifacts (pages and apps in the side panel), past-chat search and memory, and the user's connectors
(Gmail, Drive, Calendar, MCP servers).

### Stage 7. Long work stays in the same turn
Claude does long tasks inside the turn: it keeps calling tools for minutes, with every step visible in the working
row. Research mode runs for several minutes and the report arrives as the reply in the same chat. Nothing goes to a
separate background queue that reports back later as a different message.

### Stage 8. Hard or wide tasks use sub-agents, inside the turn
Anthropic's Research system: a lead agent plans, writes the plan to memory, starts 3-5 sub-agents in parallel (each
with its own clean context and a clear task), each sub-agent searches and returns a short, condensed finding, the lead
combines them, and a final pass attaches citations. The user sees one reply. Anthropic reports this beat a single
agent by 90% on their research evaluation, at about 15 times the tokens, so it is used only for tasks that need it.

### Stage 9. Files and artifacts
- **Files**: the model writes Python in a sandbox that makes the real file (Word, Excel, PowerPoint, PDF) and returns
  it as a download card.
- **Artifacts**: the model itself writes the page or app (HTML / React / Markdown / SVG) straight into the side panel,
  streaming. A change is an edit to the same artifact (a new version), not a rebuild from scratch.

### Stage 10. Memory and long chats
- **Memory**: a short summary of the user (editable by the user) rides in each chat; past chats are searched with a
  tool when the message refers to them.
- **Projects**: instructions + knowledge files shared by every chat in the project; the files are searched on demand.
- **Long chats**: when a chat nears the window, older parts are summarised (compaction) and the recent messages stay
  word for word. Old tool results can be cleared (the call stays, the bulky result is replaced by a stub) before
  anything else is cut.

### Stage 11. The answer
The reply streams at reading speed in Markdown, length matched to the question, in the user's language. It answers
the question asked, says plainly what it did and what it could not do, cites sources for web facts, and ends with a
question or offer only when one is useful. Nothing is stapled on afterwards: no status lines, no machine notes, no
lists of other work.

### Stage 12. After the answer
Copy, retry (a new answer to the same message), edit your message (a new branch from there), thumbs up / down. Tool
steps and thinking stay folded under the answer.

---

## Part 2. Hoola today, stage by stage

| Stage | Claude | Hoola now (measured) | Gap |
|---|---|---|---|
| 1 Every message reaches the model | Always | v0.724 turned off the quick lane and the bare-"haan" card approval. Still before the model: the research plan gate (`research_plan.gate`), stop words (`kaamstop`), the "aage badho" goal reopen, `resume_on_answer` | Small, mostly fixed |
| 2a System prompt | Fixed, cached | ~50,000-57,000 characters a turn, built from 16+ blocks (memory, sites, apps, cards, job state, coder primer, diary, focus notes, skills, family guides...), different every turn, so not cached well | **Large** |
| 2b Tools in the request | Few core + tool search | System prompt + tools in view = 97,000-127,000 characters (~33,000-42,000 tokens) before any conversation; ~616 tools registered, ~60 in view | **Large** |
| 2c Conversation | Word for word | Word for word since v0.724 (1M window). Before that, cut to ~7k tokens on GLM | Fixed |
| 3 One model per chat | Yes | Up to five routes in one chat: GLM door (`glmdoor`, all calls when `CLAUDE_ALL_GLM`), Haiku for simple asks (`chat_simple_model`), Sonnet for long jobs, Opus for hard asks, `claude_one_model` rewriting everything to Haiku; fallbacks to other models on failure | **Large** |
| 4 Thinking | Adaptive, shown folded | Only for long jobs / hard asks (`think_wanted`); off on GLM | Medium |
| 5 The loop | Plain loop | Plain loop plus nudges after the "final" answer: promise nudge (`aage`), goal nudge, `_pakka_check` self-check, held hard answers (`_hard_check` + reviewer), research claim checks, corrections sent as extra messages | Medium |
| 6 Tools | Few, sharp descriptions | Many overlapping tools (scrape_page / scrape / reach / open_website / duniya fetch / jharokha; 5 memory systems), descriptions of mixed quality, some in Hinglish | **Large** |
| 7 Long work in the turn | Yes | Big asks go to background crews / jobs; results return later through a "wake" turn (v0.722 fixed the answer getting lost) | **Large** |
| 8 Sub-agents | Lead + 3-5 workers in the turn | `deploy_agents` crews run in the background, report through the follow-up row | Medium |
| 9a Files | Code sandbox makes real files | `doc_studio` / HOOLA PRINT / `pylab` (no network); works, several paths | Small |
| 9b Artifacts | The model writes the page, streams, edits in place | `artifact_make` hands the request to a separate builder model call (16k tokens) that rebuilds the whole page; 20-90 s with no streaming; every change rebuilds | **Large** |
| 10 Memory | Short summary + search tool | yaad facts, diary, focus notes, coder vault, knowledge graph, Mere baare mein, card news, job state - several injected every turn | Medium |
| 11 The answer | Answer only | Extra lines added to replies: the "(Kaam: 4/24 steps · 2 calls · done ✓ · tool_names)" ledger, honesty notes, correction messages | **Large** (visible every reply) |
| 12 After | Copy, retry, edit/branch, feedback | Copy, retry, feedback; edit exists | Small |

**The short version:** Hoola's tools and features are wide, but the request the model gets is crowded (a 50k
system prompt that changes every turn, ~40k tokens before the chat starts), the model changes inside a chat, long work
leaves the turn, and extra text is stapled onto replies. Each of those makes even a strong model answer worse.

---

## Part 3. The plan

Ten phases, in order of impact. Each one is a separate version with a switch, so it can be turned off if it makes
things worse. Phase 0 comes first because every later phase is judged by it.

### Phase 0. Measure first: the Claude Parity Card
**What:** a scored set of 60 real multi-turn conversations, replayed through the real `run_turn`, scored in code
plus a judge model.
- 15 follow-ups that depend on the previous reply: "yes", "the second one", "make it shorter", "in Hindi", "why?",
  "do it" after an offer.
- 10 single tasks that need one tool: mail, calendar, web fact, file read.
- 10 long tasks: research with sources, a 5-step job, an Excel from data, a PDF report.
- 10 make-something asks: a page / app / chart, then two edits to it.
- 5 memory asks across chats ("what did I decide about NetMitra last week").
- 5 traps: ambiguous asks (should ask one question), impossible asks (should say so), "stop".
- 5 Hinglish / Marathi conversations.

**Scores per conversation:** answered the actual question; followed the previous turn; right tool first; no
invented "done"; no text the user did not ask for; time to first word; total time; cost in rupees.

**Also:** an endpoint `GET /api/conversations/{id}/request/{turn}` that shows exactly what the model received for that
turn (system prompt, tool names, messages). Most of this week's bugs were found by reading what the model saw.

**Files:** `server/app/quality/paritycard.py`, `parity_convs.py`; vps-ops job `parity_card`.
**Done when:** the card runs on the live server and gives a baseline score. Every later phase must raise it.

### Phase 1. One model per chat
**What:** a chat runs on one model from start to end, like Claude.
- New setting `chat_model` (default: Claude Sonnet). Every step of every chat turn uses it, including long jobs and
  hard asks. Opus is the user's choice (a model picker in the composer), not a silent switch.
- GLM, Haiku and the other cheap models stay for background work only: summaries, compaction, memory extraction,
  reviewers, Studio sub-steps. The GLM door (`glmdoor`) is kept off chat turns.
- On overload or error: retry the SAME model with backoff; if it still fails, say so plainly ("Claude is busy, try in
  a minute") instead of answering with a different model mid-chat.
- Prompt caching on (Phase 2 makes the prefix stable, which is what makes caching pay).

**Why first:** the model is the biggest single factor. Mixed models in one chat give mixed tone, mixed tool habits and
lost context.
**Cost:** higher per message than GLM-Flash. Caching (Phase 2) cuts the repeated prefix to ~10% of its price. Add a
per-user daily cap with a plain message when reached.
**Files:** `config.py` (`chat_model`, `chat_model_lock`), `agent/santosh.py` (`model_for`, brain choice), `usage.py`
(`one_model` off for chat), `glmdoor.py` (chat turns bypass).
**Done when:** the request dump shows one model for every step of a 20-turn chat; parity card up.

### Phase 2. A small, fixed system prompt
**What:** cut the per-turn system prompt from ~50k characters to under ~12k, and make it the same every turn.
- **Core prompt (fixed, cached):** identity (her avatar's name), how to write (from `replystyle`, trimmed), safety and
  approval rules (money, sending, deleting need her card), tool-use rules, the language rule. Target 8-10k characters.
- **Per-chat block (small, changes rarely):** date and time, her name and language, her memory summary (under ~1,500
  characters, written by the memory job, editable on her "Mere baare mein" page), the project's instructions if the
  chat is in a project.
- **Everything else becomes a tool, fetched only when the message needs it:** her sites and apps (`website_dekho`,
  `app_dekho`), running and waiting work (`kaam_status`), waiting cards (`cards_dekho`), diary / past chats / facts
  (`yaad_khojo`), coder notes, focus notes, skills (tool search already lists them).
- The per-turn "news" (a job finished, a card answered) goes into the conversation as one short system note at the
  point it happened, not into the system prompt.

**Files:** `agent/prompts.py` (split `system_prompt` into `core_prompt` + `chat_context`), the `*_block` callers in
`santosh._build_context`, `agent/cache.py` (cache breakpoints after core prompt and after tools).
**Done when:** the request dump shows the system prompt under 12k characters; the cached prefix is reused (cache-read
tokens in the usage log); parity card holds or rises. Measure the old blocks first: each one removed must not drop a
card score; if it does, it becomes a tool rather than coming back.

### Phase 3. Clean tools
**What:** apply Anthropic's tool-writing guidance to the toolbox.
- **Core set always in view (about 20):** `web_search`, `web_fetch` (one reader replacing scrape_page / scrape /
  reach / open_website / duniya fetch for normal reading), `pylab` (code + file making), `artifact`, `file_read`,
  `yaad_khojo` (one memory search over all memory stores), `chat_search`, email (read / draft), calendar, drive,
  `kaam_plan` (her to-do list for long work), `agents` (sub-agents), `ask_form`, `tool_search`.
- **Everything else** stays behind `tool_search` (already built in v0.565).
- **Merge overlaps:** one web reader with a `mode` (fast / browser / stealth) instead of six tools; one memory search
  instead of five; one status tool for all work.
- **Rewrite every core description** in clear English: what it does, when to use it, when not to, each parameter,
  one example. Hinglish only in user-facing text, never in tool descriptions.
- **Results:** return what the model needs (ids, links, numbers, the error and how to fix it); cut big results with
  head + tail; never raw Python errors.
- **Tool card:** the existing `toolchoice` card extended to the new core set; every merge must keep or raise it.

**Files:** `agent/tools.py`, `agent/admit.py` (core set), the merged tool modules, `quality/toolchoice.py`.
**Done when:** ~20 tools in view, tool card at or above today's 26/26, request size down.

### Phase 4. Long work stays in the turn
**What:** like Claude, a long task runs inside the turn with live steps, and the answer is the reply.
- Raise the turn budget for chat turns (e.g. 20 minutes, 200 tool calls) with the working row (v0.721) showing each
  step and the clock.
- `deploy_agents` / crews run INSIDE the turn by default: the lead plans, starts 3-5 sub-agents in parallel (each with
  its own clean context and a one-paragraph task), waits for their short results, combines them, and answers. This is
  the Research pattern; the code for parallel agents exists (`agent/team.py`), it needs an in-turn mode.
- Background jobs only for work that truly takes longer than the turn budget (video renders, app builds, website
  builds). Their finish note keeps today's v0.722 behaviour: the result is written into the same chat.
- Stop button cancels the turn and every sub-agent.

**Files:** `agent/team.py` (in-turn mode), `agent/santosh.py` (turn budget for chat), `config.py`.
**Done when:** the $5M-idea style ask returns its full answer in the same turn, with the agent steps folded under it;
parity card long-task scores up.

### Phase 5. Remove what gets stapled onto replies
**What:** the reply is only what the model wrote.
- The "(Kaam: 4/24 steps · 2 calls (2 ok) · done ✓ · tool_names)" ledger line moves out of the reply text into the
  folded steps row (it is useful for debugging, not for her).
- Honesty checks stay, but act BEFORE the answer is final: if a claim is not backed by a tool result, the model is
  asked once to correct itself (as `aage` / `_pakka_check` already do); no note is stapled on after, and no second
  "correction" message is sent unless a real action claim was false.
- Held answers (`_hard_check`): keep for maths / research with sources, where checking matters, but stream the
  thinking so she sees it working.

**Files:** `agent/kaam_laws.py` (ledger to step data), `agent/draftcheck.py`, `agent/santosh.py`
(correction path), console `v2.js` (show the ledger in the steps dropdown).
**Done when:** zero added lines in 60 parity conversations; false-done score unchanged or better.

### Phase 6. Artifacts the Claude way
**What:** the chat model writes the page itself, into the side panel, and edits it in place.
- New tool shape `artifact` with actions `create` (title, type html / react / markdown / svg / mermaid, content) and
  `update` (exact old text -> new text, like a code edit), plus `rewrite` for big changes. The content streams into
  the panel as the model writes it.
- Every change is a new version; the panel shows versions and Undo. The current version's code is in the
  conversation (as the tool call), so "make the header blue" is a small edit, not a full rebuild.
- The v0.725 page card stays as the chat-side card (clock, steps, Open).
- The old `artifact_make` builder path stays for her Studio-quality pages behind a "polish" action.

**Files:** `app/artifacts.py` (versions from tool content), new `agent/artifact_tools.py` actions, console
`panel.js` (stream into the panel), `v2.js`.
**Done when:** a dashboard page appears and grows in the panel within seconds of the ask; an edit takes seconds and
changes only what was asked; parity make-something scores up.

### Phase 7. One memory, Claude style
**What:**
- **One short memory summary** per user (the "Mere baare mein" page, v0.250), rewritten by a nightly job from her
  chats, editable by her, under ~1,500 characters, in the per-chat block (Phase 2).
- **One search tool** (`yaad_khojo`, v0.608 already searches all stores) for everything else: facts, past chats,
  diary, coder notes, knowledge graph.
- **Past-chat search** returns chat titles + the relevant lines + a link to open the chat.
- Stop injecting facts, diary, focus notes, coder primer and card news into every turn.
- Incognito chats and her memory switches keep working as today.

**Files:** `app/memory.py`, `app/aboutme.py`, `app/yaad.py` (turn blocks off), `agent/prompts.py`.
**Done when:** memory quiz (`server/tools/memory_quiz.py`) stays at 20/20 with the smaller prompt; parity memory
scores up.

### Phase 8. Projects like Claude Projects
**What:** a project = instructions + knowledge files + its chats.
- Project instructions ride in the per-chat block of every chat in the project.
- Project files are searched on demand (`project_search` over the existing gyaan index), not pasted.
- New chats started inside a project inherit it; the console's Projects page shows instructions, files and chats.

**Files:** console `projects.js`, `app/gyaan` (per-project index), `agent/prompts.py`.
**Done when:** a chat in the "NetMitra" project answers from its files and follows its instructions without being
told again.

### Phase 9. Research mode on the composer chip
**What:** the "Deep research" chip runs Hoola's research engine (R2-R9, already built) in the turn: plan -> parallel
workers -> verified notes -> report with numbered citations -> optional PDF / Word. Progress shows in the working row
("Reading 12 sources"); the report is the reply.
**Files:** console composer chip -> turn flag; `agent/research_tools.py` in-turn path.
**Done when:** the research card (R0) runs live with scores, and the report arrives in the same chat.

### Phase 10. Finishing touches
- Model picker in the composer (Sonnet / Opus), remembered per chat.
- Edit message = new branch (old branch kept, switchable), like Claude.
- "Searched 8 sources" row with the source chips under research and web answers.
- Thinking row ("Thought for 8s") folded, as today's steps row.
- Errors in one plain sentence with a Retry button; never a raw error.

---

## Part 4. What Hoola keeps that Claude does not have

These are Hoola's strengths. Nothing in this plan removes them:
- **Her approval on every send, payment, delete and public change** (cards). Claude also asks before consequential
  actions; Hoola's card is the better version.
- **Hinglish and Indian languages** in replies, and voice calls.
- **Phone actions, WhatsApp campaigns, Indian business desks** (GST, khata, maps, IndiaMART...). They become
  tool-search tools behind the core set, not removed.
- **Background jobs that take hours** (website builds, app builds, video renders). They stay background, and report
  into the same chat.

---

## Part 5. Order, effort, and how to know it worked

| Phase | Effort | Main risk | Switch |
|---|---|---|---|
| 0 Parity card + request dump | 2-3 days | none | n/a |
| 1 One model per chat | 1 day | cost | `chat_model`, `chat_model_lock` |
| 2 Small fixed prompt | 3-4 days | a removed block was doing real work | `prompt_core_only` |
| 3 Clean tools | 4-5 days | tool card drops after merges | `tools_core_set` |
| 4 Long work in the turn | 3 days | very long turns time out | `turn_inline_agents` |
| 5 Nothing stapled on | 1 day | a false "done" slips through | `reply_clean` |
| 6 Artifacts the Claude way | 4-5 days | panel streaming on phone | `artifact_inline` |
| 7 One memory | 2 days | memory quiz drops | `memory_lean` |
| 8 Projects | 2-3 days | none big | `projects_v2` |
| 9 Research chip | 1-2 days | cost of long research | existing research switches |
| 10 Finishing touches | 3 days | none big | per item |

Order: 0 -> 1 -> 5 -> 2 -> 3 -> 4 -> 6 -> 7 -> 9 -> 8 -> 10. Phase 1 and 5 are cheap and give the biggest visible
change; 2 and 3 make every later phase better; 6 is the largest single piece of work.

**How we know it worked:** the parity card score after each phase, against the Phase 0 baseline, plus her own
verdicts on live chats (her verdict outranks the card, as in the other quality cards).

**Not verified in this plan:** no phase has been built or measured yet. The Claude-side facts are from Anthropic's
public material and visible behaviour; the Hoola-side numbers were measured in this repo on 9 Nov 2026.
