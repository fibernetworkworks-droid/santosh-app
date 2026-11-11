---
name: th-vision-lane
description: Vision-lane syllabus - screenshot to action, ground first
when_to_use: screenshot, vision model, computer use, click on screen, pc operator, screen reading
---
GOAL: Hoola's PC operator is itself a screenshot->action model -
screenshot from the PC, Claude (vision) picks ONE action with a tool,
desktop does it, new screenshot. Awesome-vlm-architectures (gokayfem,
a catalog of 200+ VLM / MLLM architectures - papers, diagrams,
training recipes, datasets, release timeline) is its syllabus: look
for a new vision idea in the catalog first, never invent a model
yourself.

THE LOOP (Hoola's real loop, in this order):
1. Take a SCREENSHOT - the primary monitor by default; monitor="all"
   = all monitors in one picture (the second screen is not blind,
   and a click lands on it correctly).
2. GROUND it - coordinates are pixels of THAT screenshot, not of
   the world; read the window title + the list of open windows too
   (if what you need is already open, do not open a new one).
3. ONE action per turn - only one of click / type / key / scroll /
   drag / done; never a second screen action in one turn (the
   screen can move; the old action does not run at all - look at
   the new screenshot first).
4. REPEAT - after every action only the new screenshot is the truth.

THE TWO LANES (the biggest architecture lesson of this syllabus):
- SEMANTIC lane first: ax_find (an element by role / name, such as
  role=button name=Save - more exact than reading a screenshot) and
  page_fill_form (a whole form in ONE step, DevTools protocol)
  wherever available. One exact door beats a dozen screenshot
  rounds.
- PIXEL lane as fallback: screenshot + click x,y - works everywhere.
  If the semantic lane fails, the screenshot shows the reason.

SYLLABUS FAMILIES (in the catalog these are SEARCH TERMS, not model
ids):
- Screenshot parsing / UI grounding: element coordinates, OCR-free
  document understanding, set-of-mark style prompting.
- GUI navigation agents: web / mobile UI agents, screenshot
  sequences, action histories.
- VLM architectures: dual-encoder vs connector, any-resolution
  tiling, training recipes, datasets. The zoo's image models are a
  different lane (creative images); THIS lane is for CONTROL.

EVAL: any change in the vision lane? Run the SAME golden screenshot
suite again (the bd-eval-benchmarks way - a small suite, a printed
score, a ledger row). Not "it feels better" from a guess - from the
score.

NEVER: click on a stale screenshot (the coordinates were its pixels,
not the current ones); two screen actions in one turn; keep pulling
pixel rounds when the semantic door is open; type a CAPTCHA yourself
- ask_approval first ("Shall I type '<what I read>' in the
CAPTCHA?"), that is the operator's rule; add a model / architecture
name from outside the syllabus - if it is not found say
"unverified"; touch anyone's screen outside the pc lane.

ALSO ASKED AS (Hinglish asks this skill answers): pc ki screen dekh ke
action lo, screenshot padh ke click karo
