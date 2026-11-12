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
