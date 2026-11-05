---
name: th-vision-lane
description: Vision-lane syllabus - screenshot to action, ground first
---
GOAL: Hoola ka PC operator khud ek screenshot->action model hai -
screenshot from the PC, Claude (vision) picks ONE action with a tool,
desktop does it, naya screenshot. Awesome-vlm-architectures (gokayfem,
200+ VLM/MLLM architecture catalog - papers, diagrams, training
recipes, datasets, release timeline) uski syllabus hai: naya vision
idea pehle catalog me dhoondo, khud se model invent kabhi nahi.

THE LOOP (Hoola ka asli loop, isi order me):
1. SCREENSHOT lo - monitor primary default; monitor="all" = sab
   monitors ek picture me (doosri screen blind nahi rehti, uspe click
   sahi land karta hai).
2. GROUND karo - coordinates US screenshot ke pixels hain, duniya ke
   nahi; window title + open windows list bhi padho (jo chahiye wo
   pehle se khula ho to naya kholna nahi).
3. EK action per turn - click/type/key/scroll/drag/done me se ek hi;
   ek turn me doosra screen action kabhi nahi (screen move ho sakti
   hai; purana action run hi nahi hota, naya screenshot dekho pehle).
4. REPEAT - har action ke baad naya screenshot hi sach hai.

THE TWO LANES (is syllabus ka sabse bada architecture lesson):
- SEMANTIC lane pehle: ax_find (element by role/name, jaise
  role=button name=Save - screenshot padhne se exact) aur
  page_fill_form (poora form EK step me, DevTools protocol) jahan
  available ho. Dozen screenshot rounds se ek exact door behtar.
- PIXEL lane fallback: screenshot + click x,y - sab jagah chalega.
  Semantic fail ho jaye to screenshot hi wajah batata hai.

SYLLABUS FAMILIES (catalog me SEARCH TERMS hain, model ids nahi):
- Screenshot parsing / UI grounding: element coordinates, OCR-free
  document understanding, set-of-mark style prompting.
- GUI navigation agents: web/mobile UI agents, screenshot sequences,
  action histories.
- VLM architectures: dual-encoder vs connector, any-resolution
  tiling, training recipes, datasets. Zoo ke image models alag lane
  hai (creative images); YE lane CONTROL ke liye hai.

EVAL: vision lane me koi bhi badlav? SAME golden screenshot suite
dobara chalao (bd-eval-benchmarks ka tareeka - chhota suite, printed
score, ledger row). Andaz se "behtar lag raha hai" nahi, score se.

NEVER: stale screenshot pe click (coordinates uske pixels the, ab ke
nahi); ek turn me do screen actions; semantic door khula ho tab bhi
pixel rounds khinchte rehna; CAPTCHA khud type karna - pehle
ask_approval ("CAPTCHA mein '<jo padha>' likhu?"), wahi operator ka
rule; syllabus ke bahar model/architecture ka naam jodna - na mile to
"unverified" bolo; pc lane ke bahar kisi ki screen chhoo-na.
