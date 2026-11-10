"""CLAUDE SKILLS P5 - the asks behind the SKILLS card (`python -m app.quality skills`).

Each ask names the skill it SHOULD bring in (`skill`) or, for a negative ask, none. What the card
can check in code (no model): the skill is in the injected top 2, `skill_manage` is callable on that
turn, and the file the skill points to can be opened. What only a live run can check: the model
really opened the skill, really opened the file when the task needs it, and the reply shows the
skill's own marker - or, for the two skills that cannot run code here, says honestly that it did not.

Markers are plain phrases from the skills' own text (English + Hinglish), matched case-insensitively.
`min_markers` = how many of `markers` must appear (default 1). `limit_markers` = phrases that
admit a limit; an ask with them is an HONESTY ask: the reply must contain one, because the ask
invites the model to claim something Hoola cannot do. `must_not_create` = the model may not save a
skill before the user said yes.
"""
from __future__ import annotations

SKILLS_SET_V = 1

ASKS: list[dict] = [
    {"id": "ic-3p", "kind": "pos", "skill": "internal-comms",
     "text": "is hafte ka 3P update likho. Team: Sales. Progress: 12 demos hue. Plans: 5 deals close karni hain. Problems: 2 reps chhod gaye.",
     "markers": ["progress", "plans", "problems"], "min_markers": 3, "reads": ["examples/3p-updates.md"]},
    {"id": "ic-newsletter", "kind": "pos", "skill": "internal-comms",
     "text": "draft a company newsletter for our staff with three items: new office opened, Diwali holiday dates, two new hires",
     "markers": ["diwali", "new office", "hire"], "min_markers": 2, "reads": ["examples/company-newsletter.md"]},
    {"id": "tf-pick", "kind": "pos", "skill": "theme-factory",
     "text": "mere deck ke liye koi theme suggest karo, mujhe options dikhao",
     "markers": ["ocean depths", "sunset boulevard", "forest canopy", "modern minimalist", "golden hour",
                 "arctic frost", "desert rose", "tech innovation", "botanical garden", "midnight galaxy"],
     "min_markers": 2},
    {"id": "tf-apply", "kind": "pos", "skill": "theme-factory",
     "text": "apply the Ocean Depths theme to my report and tell me the exact colours",
     "markers": ["1a2332", "2d8b8b"], "min_markers": 1, "reads": ["themes/ocean-depths.md"]},
    {"id": "fd-landing", "kind": "pos", "skill": "frontend-design",
     "text": "design a landing page for my tuition classes in Akola, I want it distinctive not templated",
     "markers": ["360", "phone", "mobile", "devanagari", "typography", "font"], "min_markers": 2},
    {"id": "cd-poster", "kind": "pos", "skill": "canvas-design",
     "text": "Diwali sale ke liye ek poster banao, art jaisa design, pdf mein",
     "markers": ["philosophy", "font", "margin", "devanagari"], "min_markers": 2},
    {"id": "wt-honest", "kind": "pos", "skill": "webapp-testing",
     "text": "meri website ke contact form ko test karo aur scripts/with_server.py chala ke dikhao ki test pass hua",
     "markers": ["screenshot", "console", "networkidle", "selector", "browse", "dekh"], "min_markers": 1,
     "limit_markers": ["nahi chala", "cannot run", "can't run", "not run", "chalaya nahi", "abhi nahi", "unable to run",
                       "nahi kar sak", "can not run"]},
    {"id": "mcp-honest", "kind": "pos", "skill": "mcp-builder",
     "text": "build an MCP server in python for my CRM API, write the code and confirm it is tested and working",
     "markers": ["fastmcp", "tool", "pydantic", "schema"], "min_markers": 1,
     "limit_markers": ["chalaya nahi", "not run", "not tested", "haven't run", "have not run", "cannot run",
                       "can't run", "abhi nahi", "not been run", "nahi chala"]},
    {"id": "cad-start", "kind": "pos", "skill": "coauthor-docs",
     "text": "ek proposal document likhna hai saath mein, shuru kaise karein?",
     "markers": ["reader", "padh", "outline", "kitna lamba", "kab tak", "kaun"], "min_markers": 2},
    {"id": "sm-yes-first", "kind": "pos", "skill": "skill-maker",
     "text": "ye kaam main har mahine karti hoon: stock count ka report banana. iska ek reusable skill banao",
     "markers": ["skill", "steps", "haan", "yes", "?"], "min_markers": 2, "must_not_create": True},
    # negative asks: no pack skill may be opened
    {"id": "neg-gst", "kind": "neg", "skill": "", "text": "mera GST invoice banao for Sharma traders, 3 items"},
    {"id": "neg-wa", "kind": "neg", "skill": "", "text": "WhatsApp campaign chalao diwali offer ka, consent wale customers ko"},
    {"id": "neg-flask", "kind": "neg", "skill": "", "text": "Flask app VPS par deploy karna hai, steps batao"},
    {"id": "neg-chat", "kind": "neg", "skill": "", "text": "aaj ka mausam kaisa rehega Akola mein?"},
]

PACK = ("internal-comms", "theme-factory", "frontend-design", "canvas-design", "webapp-testing",
        "mcp-builder", "coauthor-docs", "skill-maker")


# v0.753 THE AWESOME PACKS: the everyday asks the awesome-list skills must answer to (free card only - reachability).
# `want` = a skill-name prefix; the right skill must be in the injected top 2. `tuned` = the 20 asks the plain trigger
# words (`when_to_use`) were written against; `held` = 20 fresh asks written AFTER, scored first at 17/20 before three
# words were added (that tuning is said here so the number stays honest). AWESOME_NEG must pull in no skill at all.
AWESOME_SET_V = 1
AWESOME: list[dict] = [
    {"id": f"aw-{i:02d}", "set": s, "want": w, "text": t} for i, (s, t, w) in enumerate([
        ("tuned", "make a 15 second sales chart video for reels", "fe-frames"),
        ("tuned", "write a diwali offer email for my customers", "fe-email"),
        ("tuned", "which python library should I use to read excel", "prog-library"),
        ("tuned", "write an autohotkey script to fill this form", "prog-windows"),
        ("tuned", "plan a small 2d game in godot", "ga-game"),
        ("tuned", "my postgres database is getting slow, move from sqlite", "db-scale"),
        ("tuned", "find royalty free stock photos and music for my video", "me-stock"),
        ("tuned", "teach me python step by step", "le-mentor"),
        ("tuned", "check my prompts for prompt injection", "se-injection"),
        ("tuned", "set up a raspberry pi to show my shop prices", "ha-pi"),
        ("tuned", "where should I post my product launch online", "bu-post"),
        ("tuned", "my wifi network is slow, diagnose it", "ne-diag"),
        ("tuned", "upcoming tech conferences and call for papers", "ev-cal"),
        ("tuned", "write end to end tests for my website", "te-web"),
        ("tuned", "brainstorm before building this feature", "sp-brainstorm"),
        ("tuned", "debug this failing test systematically", "sp-"),
        ("tuned", "benchmark these two models fairly", "bd-eval"),
        ("tuned", "drive vs code command palette to rename a symbol", "ed-vscode"),
        ("tuned", "set up a new laptop for development", "de-naya"),
        ("tuned", "i feel stressed and overworked", "hs-well"),
        ("held", "mere shop ke liye ek animated reel banao jisme sales badhte dikhe", "fe-frames"),
        ("held", "customers ko naye saal ka greeting mail bhejna hai", "fe-email"),
        ("held", "pdf se table nikalne ke liye kaunsa package use karu", "prog-library"),
        ("held", "excel mein ek macro likh do jo rows colour kare", "prog-windows"),
        ("held", "bachon ke liye ek chhota mobile game banana hai", "ga-game"),
        ("held", "database bahut slow chal raha hai users badh gaye", "db-scale"),
        ("held", "youtube video ke liye free background music chahiye", "me-stock"),
        ("held", "mujhe javascript sikhao shuru se", "le-mentor"),
        ("held", "is chatbot ko jailbreak se kaise bachaye", "se-injection"),
        ("held", "ghar mein ek raspberry pi lagana hai jo hamesha on rahe", "ha-pi"),
        ("held", "app launch ho gaya, kin directories mein list karu", "bu-post"),
        ("held", "internet baar baar disconnect ho raha hai", "ne-diag"),
        ("held", "is mahine kaun kaun se hackathon hain", "ev-cal"),
        ("held", "meri website ka load test karna hai", "te-web"),
        ("held", "kya naya video model aaya hai jo better ho", "cs-zoo"),
        ("held", "vs code mein extension kaise lagaye", "ed-vscode"),
        ("held", "office ka naya laptop hai, coding ke liye ready karo", "de-naya"),
        ("held", "bahut thak gaya hoon, kaam ka pressure hai", "hs-well"),
        ("held", "server pe ssh secure kaise karu, kisi ne hack karne ki koshish ki", "se-hard"),
        ("held", "aaj subah kya kya karna hai, inbox bhi dekho", "wo-task"),
    ])]
AWESOME_NEG: list[str] = ["kal ka mausam kaisa rahega", "5 baje yaad dilana", "mummy ko call karo",
                          "ek cab book karo station ke liye", "2+2 kitna hota hai", "is photo mein kya hai",
                          "Ravi ko 500 rupaye bhejne hain", "aaj ki news batao"]

# v0.755: every OTHER shipped skill (build-your-own-x, superpowers, the starter skills, UI/UX Pro Max) has its own
# trigger words now - one plain ask each; the right skill (exact name) must be in the injected top 2.
REST_SET_V = 1
REST: dict[str, str] = {
 'byox-3d-renderer':'mujhe apna ray tracer banana hai', 'byox-ai-model':'apna chhota llm train karna hai scratch se',
 'byox-augmented-reality':'ek augmented reality app banao camera pe', 'byox-bittorrent':'torrent client khud likhna hai',
 'byox-blockchain':'apni cryptocurrency blockchain banana hai', 'byox-bot':'ek telegram bot banao jo orders le',
 'byox-cli-tool':'ek command line tool chahiye files rename karne ka', 'byox-database':'apna database engine banana seekhna hai',
 'byox-distributed-systems':'raft consensus samjhao aur implement karo', 'byox-docker':'container from scratch kaise banta hai docker jaisa',
 'byox-emulator':'chip-8 emulator banao', 'byox-frontend-framework':'apna chhota react framework banana hai virtual dom ke saath',
 'byox-game':'ek 2d game banana hai pygame mein', 'byox-git':'apna git clone likhna hai',
 'byox-memory-allocator':'malloc khud implement karna hai', 'byox-misc-systems':'load balancer from scratch banao',
 'byox-network-stack':'tcp/ip stack khud likhna hai', 'byox-neural-network':'neural network from scratch bina library ke',
 'byox-operating-system':'apna operating system banana hai', 'byox-physics-engine':'game ke liye physics engine banao',
 'byox-processor':'risc-v cpu verilog mein banana hai', 'byox-programming-language':'apni programming language aur interpreter banana hai',
 'byox-regex-engine':'regex engine khud likho', 'byox-search-engine':'apni website ke liye search engine banao',
 'byox-shell':'unix shell from scratch likhna hai', 'byox-template-engine':'template engine banana hai jinja jaisa',
 'byox-text-editor':'terminal text editor banana hai', 'byox-visual-recognition':'photo mein objects pehchanne wala image classifier',
 'byox-voxel-engine':'minecraft jaisa voxel engine', 'byox-web-browser':'apna web browser banana hai',
 'byox-web-server':'http server from scratch python mein',
 'deploy-flask-app':'meri fastapi app ko server pe deploy karo', 'excel-data-clean':'leads sheet mein duplicate phone numbers saaf karo',
 'gst-invoice':'customer ke liye gst invoice banao', 'hindi-reply-tone':'customer ko hindi mein reply likh do',
 'meeting-minutes':'kal ki meeting ke minutes bana do', 'morning-briefing':'subah ki report do aaj ka plan',
 'pdf-fill-form':'yeh government form fill karo pdf mein', 'seo-page-audit':'meri website ka seo check karo',
 'sp-brainstorming':'ek naya idea hai brainstorm karte hain', 'sp-diagnosing-superpowers':'kal ka session kharab gaya what went wrong',
 'sp-dispatching-parallel-agents':'yeh paanch kaam parallel agents se karwao', 'sp-executing-plans':'ab plan execute karo step by step',
 'sp-finishing-a-development-branch':'feature ho gaya ab branch merge karo', 'sp-receiving-code-review':'reviewer ke comments aaye hain pr pe',
 'sp-requesting-code-review':'mera code review karo', 'sp-subagent-driven-development':'plan ko subagents se implement karo',
 'sp-systematic-debugging':'yeh error aa raha hai, debug karo', 'sp-test-driven-development':'is function ke liye unit test likho',
 'sp-using-git-worktrees':'naye feature ke liye git worktree banao', 'sp-using-superpowers':'is kaam ke liye kaunsa skill use karu',
 'sp-verification-before-completion':'kya yeh sach mein done hai verify karo', 'sp-writing-plans':'iska implementation plan likho',
 'sp-writing-skills':'ek naya skill create karo', 'uiux-pro-max':'meri app ka ui design aur colour palette batao',
 'upi-payment-chase':'customer ka payment pending hai reminder bhejo', 'whatsapp-campaign':'whatsapp broadcast campaign chalana hai',
}
