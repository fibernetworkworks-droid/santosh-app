# Claude Android app as the design reference (owner's report, 12 Nov 2026)

Source: owner's PDF "Claude Android App - Complete Reverse Engineering Report" (com.anthropic.claude 1.261104.19,
18 pages, prepared by FNW). We take DESIGN IDEAS and NUMBERS only. Nothing of theirs ships in Hoola: not their fonts
(Anthropic Sans / Serif), Lottie files, sound files, shader code or icons, and Hoola never calls their endpoints.
Everything below gets rebuilt in Hoola's own Night Glass look.

## What the report says, and what it means for the Hoola app

| Claude Android (report) | Hoola phone app today (audit 00-04) | What Hoola takes |
|---|---|---|
| ONE theme layer: body 15sp, display 22sp, H1 20sp, H2 16sp, mono for code; warm palette #faf9f5 light / #141413 dark | 29 font sizes, 679 texts < 12px, no type scale | D1 type scale: caption 12, label 13, body 15, reply 16 (Literata), title 17, H2 16 / H1 20, display 22, hero 28; weight max 700 |
| Model sends plain Markdown -> AST parser -> styled spans; code = mono on a tinted chip; H2 = 20sp / 600 | md_text.dart already parses + renders (v0.284 soft breaks, 22/20/17 headings) | Keep; align heading sizes to the scale; one code style token |
| Streaming tail fade: last N chars fade in (GPU effect), catch-up rate with min / max chars per second | phone `_Reveal` paces words (v0.283); no tail fade on phone | Add a soft fade on the newest words (console has it since v0.716) |
| Step list is SERVER data, one row per tool with a KIND (shell, browser, web search, fetch, file read / write / edit / search / share, agent, skill, question, task list, scheduled task, card, generic) + a label | step rows built per screen, labels from labels_en, no kind icon set | One StepRow widget: icon chosen by kind + server label; same on Today, Chat and the Kaam sheet |
| Turn status: DONE / WAITING / RUNNING / FAILED / NETWORK_BLOCKED / PAUSED / NOT_RUNNING / PENDING | job states differ per screen; emoji as status in ~16 files | One StatusPill with these 8 states (icon + colour token), replaces every emoji status |
| ~110 typed content blocks (chart, map, itinerary, file, diff, product, quiz, todo, next-step offer, question...) | any_card.dart default card + ~10 one-off card styles in chat_screen | One card shell + typed bodies; add next-step offer + question card first |
| 12 named screen transitions (enter from right, modal slide up, expand / shrink, headline crossfade) | one global page transition + ad-hoc AnimatedSwitchers | A named transitions set in glass.dart, used by every push / sheet |
| Voice orb = a shader driven by voice level, phase, reduce-motion | live_voice_screen orb + Aurora | Drive Hoola's orb from her live level + Hoola's speaking phase, honour reduce motion |
| 8 sound cues (mic opens / closes, thinking, reconnecting, reconnected, disconnected, permission needed, user finished) | voice clips were removed for sounding like a radio (v0.625) | Optional, very short, Hoola's own tones only, off by default - owner decides |
| Small pictogram animations for success / empty / billing / login | emoji + plain spinners | Hoola's own small line pictograms for empty, done, needs-you |
| Artifact WebView pre-warmed (800 ms -> < 50 ms) | artifact_screen opens cold | Keep one WebView warm while a chat is open |

## Order this changes in the plan (00_INDEX D0-D4)
D1 now = Claude's numbers in Hoola's look (type scale, status set, step row kinds, card shell, transitions).
D3 Chat gets the step row + status pill + tail fade first. The rest is unchanged.

## Not verified
The report's numbers are the owner's research, not checked here. Sizes are in sp on Android; Flutter logical px match
sp only at the default text scale.

## Addendum - the owner's 5 HTML pages (endpoints, artifacts, chat timing, text pipeline, summary system)

Only the design-relevant parts are taken. Endpoints, analytics event names, proto / service names and network probes are
not used by Hoola and are not copied.

**Type scale (text-pipeline page) - corrects the PDF:** display 22 / 700, H1 18 / 600, H2 16 / 600, H3 14 / 600,
body 15 / 400, secondary 13 / 400, code 12 mono, prose serif 15. (The PDF said H1 20 - the pages say 18; Hoola's D1
takes 22 / 18 / 16 / 14 / 15 / 13 / 12 and keeps the 16px Literata reply already approved in v0.249.)
Markdown spacing: paragraph gap 8, list indent 16 per level, code block corner 8 + padding 12, table cell padding 8,
bold = 700, link = underline, inline code = mono on a 8 %-tint chip.

**Colour roles, not raw colours:** text primary / secondary / danger / success / info / warning, the same six as
backgrounds, plus border primary / danger / success / info. Hoola's C has ok / warn / bad / teal but no "background"
and "border" roles - that is why 680 raw Color(0x..) exist. D1 adds `C.okBg / warnBg / badBg / infoBg` + borders.

**Step row = structured data:** each tool row carries kind (16 kinds), label, an action verb (ran / read / searched /
wrote), a short input summary, and a housekeeping flag that HIDES internal steps. A sub-agent's steps fold under the
row that started it. A one-line thinking title sits above the group. -> Hoola's StepRow takes the same fields from the
server's step events (labels_en already gives the label); hide housekeeping steps; fold crew-agent steps.

**After the turn (PostTurnSummary):** status (8 states), status detail, needs-action flag, noteworthy flag, recent
action ("ran 3 commands"), one description line, links to what was made. It drives the notification text, the session
card preview and the status dot. -> Hoola: one "turn result" shape for the chat list row, the Kaam sheet, the Today
"Working" card and the push text, so all four always agree.

**Notification actions:** approve a tool and reply straight from the notification. -> Hoola: "Haan / Not now" on an
approval push (money still only inside the unlocked app - the NON-NEGOTIABLE rule stands).

**Bottom sheets as the standard for detail:** tool-call detail, thinking, plan, diff, attachments, usage, model choice,
task list, schedule detail all open as sheets over the chat. -> Hoola desks open detail as full pages today; D2's
DeskScaffold uses one sheet style for detail / pickers.

**Waiting + failure states:** an animated thinking mark between send and first word (TTFT 150-500 ms), stream stalled
-> reconnect after 15 s with a visible "Reconnecting" state, a retry budget, then a clear failure. -> Every Hoola desk
needs the same: loading mark, error + Retry, and the chat's reconnect state (the audit found none of this in the desks).

**Streaming text:** ~55 tokens / s; an opening `**` renders plain until the closing `**` then bolds the range; an opening
code fence switches to code at once; unclosed marks at the end stay literal; parse errors fall back to plain text.

**Artifacts:** pre-warmed WebView (300-800 ms cold -> < 50 ms); the page reports which edge is visible so the app hides
the input bar while reading; the page can send a message back into the chat ("Ask Hoola" buttons). -> Hoola
artifact_screen: warm slot, hide composer on scroll, a bridge for an in-page "Ask Hoola".

Not verified: these pages mix measured probes with estimates ("estimated", "reconstructed from smali").
