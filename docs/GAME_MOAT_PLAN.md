# The Game AI Employee — what makes it a moat (deep analysis, 2 Nov 2026)

Owner's ask: *"FIND MORE DEEP ANALYSIS WHAT IT NEED THUS HOOLA AI EMPLOYEE THIS SECTION WILL BE VERY POWERFULL AND MOAT."*

Written after Phase 10 shipped (v0.444.0, all ten Game Engine plan phases built). Three parallel research streams
(competitors, Indian market + law, engine / platform gates) plus a code audit of `server/app/gamedesk/` (17,217 lines).
Every number below carries its source. Everything that could not be verified is listed at the end and must not be
quoted as fact.

---

## 0. The one-paragraph answer

**The moat is not making games. It is finishing them, and proving they are worth finishing.** Two independent
researchers, looking at different questions, named the same white space in the market: *essentially nobody covers
QA → builds → store submission → live ops as one product for a non-studio user.* That is precisely where Hoola already
is (v0.416 QA farm + platforms, v0.432 live ops) and it is the one part of the pipeline no competitor owns. Meanwhile
the part we just spent Phase 10 on — an agent driving a real engine over MCP — **is already free, plural and
first-party from Unity and Roblox**, so it is a commodity we must have but can never win on. And the market data says
the product proposition cannot be "ship more games": India's whole mobile-game IAP market is ~$400M/year and the
median new Steam release earns under $2,000. The honest proposition is **"spend nothing to find out whether anyone
wants this one"** — which is a QA-and-measurement product, not a generation product.

---

## 1. What is commodity (do not try to win here)

**"AI writes your game code" is free and plural.** At least seven community MCP servers already connect Claude Code to
Godot, one updated 29 Oct 2026 (`npgamedev/Godot MCP Toolkit`, 113 tools, Godot 4.2–4.7; `hi-godot/godot-ai`, ~43 tools;
`IvanMurzak/Godot-MCP`; `Coding-Solo/godot-mcp`; GDAI; and others).

**The engine vendors have made it first-party and free.** Unity ships an official MCP server, CLI and plugin that
install *into Claude Code, Codex and Grok* — free, no concurrency limits, Unity 6+ — plus an AI gateway for a
third-party agent you already pay for that **does not consume Unity credits**
(https://unity.com/features/ai). Unity has also **deprecated Muse** and is retiring the "Unity AI" brand. Roblox, the
most walled platform in existence, **exposed Cube 3D's `generate_mesh` to Claude and Cursor over MCP** in its 19 Mar
2026 Assistant update (https://devforum.roblox.com/t/assistant-updates-mesh-generation-new-mcp-server-tools-screenshot-tool-and-more/4527258).

Read that as the vendors conceding that **the agent belongs to the developer and the engine's job is to be reachable.**
Our Phase 10 plugins are table stakes, not differentiation. Their value is entirely in *what sits behind them*.

**Asset generation is infrastructure, not a competitor.** Unity's own Assistant routes image→3D through **Tripo**;
Scenario routes 3D through 40+ partners including **Meshy**. Buying this layer is correct; building it is waste.
Licence terms are the only thing that matters here and they differ sharply (Meshy's free tier is CC BY 4.0 — usable
commercially *with credit*; Tripo's free tier is non-commercial; ElevenLabs' free tier has no commercial licence).

**Breadth of "AI employees" is copyable in a week.** Ten role prompts are ten prompts.

---

## 2. What the market actually is (this changes the product, not just the pitch)

**There is no consumer game market in India to sell into.**
- India's games market excluding real-money gaming was **~$1.5bn in CY2025**, projected $3.2bn by CY2030 (Lumikai,
  *State of India Interactive Media 2025*). The real-money category it replaced was **$2.3bn and collapsed** after the
  August 2025 ban; the gamer base **fell 609M → 555M**.
- But mobile **game** IAP is only **~$100–106M per quarter** (Sensor Tower Q1/Q2 2026) — roughly **$400M/year, about
  0.3% of global mobile gaming** — and **games are losing share of Indian app spend**: non-gaming took 68% of India's
  app revenue in H1 2026, up from 58% three years earlier.
- Per-head numbers are tiny: **casual ARPPU $3**, mid-core $15, blended **eCPM $1.1**, **D7 retention under 10%**
  (Lumikai). GDAI puts annual revenue per user at **$2.04**.
- **All top 10 grossing titles in India are global franchises** (Lumikai).

**Globally, the median game earns nothing, and AI has not changed that.** This is the single most important evidence in
the whole analysis, because it is an independent census rather than a vendor claim — Sulka Haro, **53,597 Steam "Games"
releases, Jul 2023 – Jul 2026**, with Wayback-dated AI flags (https://fragwyz.substack.com/p/three-years-of-ai-on-steam):
- AI-disclosure share of releases: **10.9% (2024) → 19.9% (2025) → 30.8% (2026 to July)**.
- Non-AI launches grew modestly (~1,030 → ~1,320/month). **AI-flagged launches went ~13 → ~530/month — 60–90% of all
  release growth on Steam.**
- **AI-disclosed games reach the ≥100-review tier at ~55% of the non-AI rate, and that ratio has been flat for two
  years.** Haro's conclusion: *a volume effect, not a quality effect.*
- Market shape regardless of AI: **top 1% of titles take ~94% of estimated revenue; the median game with reviews earns
  ~$300; ~28% have no reviews at all.**
- Corroboration by a different method (Totally Human Media): 10,258 disclosing titles grossing ~$660M, but **12 games
  at 8 figures, 33 at 7, 170 at 6, 487 at 5, and 9,556 below that** — and the 8-figure earners are *Stellaris*, *Black
  Ops 6*, *inZOI*: **big studios using AI marginally, not AI-made games.**

**The one empirical finding that should steer our generation work:** in Haro's census, **flops disclose AI *art* more
often (72% vs 57%), while successes disclose AI *voice* (24% vs 8%) and *localization* (18% vs 6%) far more.** The AI
uses that correlate with success are the invisible ones. Hoola already has voice and already has Indian languages. We
should lean hard into those and be careful about AI art as the visible surface of a game.

**Developer sentiment is hostile and worsening fast** — GDC 2026 State of the Game Industry, >2,300 respondents
(https://gdconf.com/article/gdc-2026-state-of-the-game-industry-reveals-impact-of-layoffs-generative-ai-and-more/):
**52% say generative AI is having a negative impact (up from 30% in 2025 and 18% in 2024); only 7% say positive.** The
most hostile disciplines are nearest the craft: visual/technical art **64%**, design/narrative **63%**, programming
**59%**. And the reputational risk is now priced in: *Clair Obscur: Expedition 33* was **stripped of Indie Game Awards
GOTY** (Dec 2025) after confirming genAI use it had denied at submission; the **human-made** RPG *Shrine's Legacy* was
review-bombed as "AI slop" despite using only human artists.

**Who actually has budget** (ranked by whether the money demonstrably exists):

| Segment | Budget exists? | What they buy |
|---|---|---|
| **Schools & colleges** | **Yes, appropriated.** Union Budget 2026-27 funds **AVGC Content Creator Labs in 15,000 secondary schools and 500 colleges** with IICT Mumbai, confirmed to Parliament July 2026, against a projected **2M AVGC professionals needed by 2030**. | A curriculum deliverable: game-making that runs on school hardware, produces a gradeable artefact, collects **no** student telemetry. Teacher-facing. |
| **Outsourcing / art-services shops** | **Yes — this is where India's game money is.** Bill **$15–65/hr**, already save foreign clients ~35% on asset work; creative exports >$11bn. | Throughput on work already sold. Saving a $25/hr artist 10 hrs/week ≈ **$1,000/month** — the only ROI in this table a buyer can compute on a spreadsheet. |
| **Ad agencies / brands** | **Yes, growing.** India in-game advertising ~$772.7M (2025) → $1.2bn (2030). | Many disposable brand-skinned playables on a campaign deadline. **The best possible fit for generated content, because nobody expects a playable to last.** |
| **Pivoting real-money-gaming firms** | **Yes, cash + urgency, closing window.** Dream11 now free-to-play at 10M DAU; Zupee cut ~40% of staff; MPL halted money ops. | Volume casual content to fill apps they already own. Buyers of *output*, not tools. |
| **Small studios** | **Weak.** 75% name capital as the growth barrier (GDAI, 104 respondents). | Cheaper failure. |
| **Solo creators** | **Weakest.** Median Steam release under ~$2,000 gross. | Aspiration. Will not fund the product. |

**The uncomfortable read: the segments that want an AI game-maker have no money; the segments with money want something
that is not a game business** — a skilling deliverable, a billable-hour multiplier, or a campaign asset.

---

## 3. Where every competitor stops

Nothing today takes a non-programmer from one sentence to a published, commercially sellable game. The three closest:

- **Rosebud AI** ($50/mo Pro) goes furthest: prompt → playable → art → sound → **downloadable code → Windows .exe →
  Steam** (export added ~May 2026; pre-May claims of "browser only" are stale). Commercial rights start at $30/mo.
  **Stops at:** no QA, no store submission, no ratings, no live ops; Windows-only export. And its one *verifiable*
  shipped game — **Hollow Signal**, Steam app 4841030, released 14 Jul 2026 at $6.99 — has **2 user reviews**, and was
  built in ~8 weeks by **a 25-year AAA veteran** (Relic, Capcom). The pipeline was completed by expertise, not by the
  tool.
- **Google Playground** (Google Labs, launched 7 Oct 2026): the smoothest prompt-to-playable, 2D/3D, multiplayer,
  leaderboards. **Dead at "sellable"** — no export, no build, no source, no store, no creator monetization, US-only,
  18+. A Unity Spark integration is planned, with no timeline.
- **Summer Engine** (Godot-based desktop app, $20–$200/mo): the only one whose artifact is unambiguously yours — a
  standard Godot 4 project, free export, **no royalties**. **Stops at:** it hands a non-programmer a real Godot
  project, which is exactly where a non-programmer is stuck. No QA, no store pipeline, no live ops.
- **Roblox** is the real exception and proves the rule by changing the definition: mobile "Build" (16 Jul 2026, alpha
  NZ-only, 9+) takes a child from one sentence to a published, monetized, retention-ranked experience, and Roblox paid
  **~$1.7B to creators in 12 months**. But it is not a sellable game, you cannot take it anywhere, and the **median
  DevEx participant earned ~$1,500/year** while the top 10 averaged $65.7M.

**What the walled gardens teach:** Astrocade raised **$56M** (Sequoia, Sea) to ~5M MAU in 8 months — and its **$10M
creator fund has paid out $50,000**. **HiberWorld shut down 29 May 2026** with ~5M hosted worlds. Scale does not equal
value capture, and a hosted sandbox can die.

**And own-engine AI is where professionals actually pay:** Ludus AI charges **$25–$180/seat/month** for Unreal work,
versus $15–$50 consumer pricing in the sandboxes — 3–7x willingness to pay. Unity's own survey reports **50% of
developers use MCP servers**, 90% of that for engine/editor connectivity, and **62% use AI for coding assistance**.

**The failure mode after the demo, consistently:** the first 80% arrives in minutes, then the complexity cliff. Unity's
own Assistant **stalled with no timeout for 4,500+ seconds** on an open-ended world build and **failed outright** on
"drivable car with WASD and physics" — oversized colliders, car spun out and floated (hands-on review, 8 May 2026,
https://darkounity.com/blog/unity-ai-assistant-review-not-ready-for-real-work). A developer who vibe-coded a 2D MMO
reports the model **persistently crammed rendering, networking and game rules into one file**. And the pricing model
taxes exactly the phase where the tools are weakest, because **debugging *is* iteration**: Rosebud's free tier is
8,000 credits/week while one premium-model edit costs ~20,000.

---

## 4. The five moats, ranked

### Moat 1 — The finishing pipeline (we have it; nobody else does; it is not proven)
Named independently by two researchers as the market's white space: **QA → builds → store submission → live ops as one
product for a non-studio user.** Every competitor covers some span of design → code → art → audio and then stops. The
pieces that follow live in separate tools aimed at studios with QA budgets (modl.ai — whose own site names no
customers, no engines and no pricing, latest confirmed funding 2022; Regression Games).

We already have: a bot QA farm on phone-speed CPUs with numbered bugs and bug-closed-only-when-the-bot-cannot-find-it
(v0.416), desktop + Android builds with store kit and age-rating drafts (v0.416), replay determinism in the real engine
(v0.427), and A/B tests, live events, crash grouping, patch checks and retention (v0.432).

**What it needs: to be true end to end for one real game, and said as one promise.** Today it is ten features. The
promise is *"Hoola does not hand you a game; it hands you a finished, tested, shippable one — and tells you when it
isn't."* Nobody can say that sentence today.

### Moat 2 — Measured quality (the Game Arena) — the hardest thing to copy
We already proved this mechanism works, on websites: `site/arena.py` — **1,000 fixed briefs**, runs built as a hidden
tenant, an **independent judge** with its own rubric (not the builder's self-critique), **originality measured as
distance from every other output in the run**, cost in rupees and minutes, **run-against-run comparison**, and **blind
duels against Lovable / Wix** scored A-vs-B without the judge knowing which is ours. That is how "more powerful"
became a number instead of a claim, and it is what caught four versions of invisible regressions.

**The game desk has no equivalent at all.** QA proves a game *runs*. Nothing measures whether it is worth playing.

This is the strongest technical moat available because it is not a feature — it is a *history*. A competitor can copy
an Arena in a month; they cannot copy two years of the same 1,000 briefs measured version over version. And it is now
also a **store-compliance requirement**, not a matter of taste: **Apple guideline 4.3(b)** rejects apps
"indistinguishable from what's already widely available," Play enforces the same against low-value apps, and Steam Next
Fest 2026 was criticised as a flood of AI games with Valve "working on other solutions". Measuring originality is
measuring shippability.

### Moat 3 — "Spend nothing to find out" (positioning that the data forces)
Given that the median release earns ~$300 and AI games succeed at 55% of the non-AI rate, **a tool sold on "publish a
game and earn" is selling a lottery ticket.** The thing the market lacks is the cheap *no*. Hoola is unusually well
placed to sell it: bots that play the game, a replay for every bug, a balance simulation, difficulty-spike detection,
and a free play link to send to ten real people before anyone commits months. That is the one proposition the data
supports, and it is a QA product wearing a creation product's clothes.

### Moat 4 — Schools, joined to the education suite (the only funded buyer)
**AVGC Content Creator Labs in 15,000 secondary schools and 500 colleges**, with IICT Mumbai, confirmed to Parliament —
the single funded line item in the entire market report. India's institutional gaming history is ~5 years old, so
curriculum and teacher capability **do not exist yet**.

Hoola is the only competitor in this analysis that already owns the other half: Shiksha (classes, learners, guardian
consent, question bank, gradebook), Pathyakram (curriculum and exam design), Guru Sahayak (tutor with a hint ladder),
Daftar (school office), Prayogshala (3D practical labs with a checked kernel). **A game-making module that drops into
an AVGC lab, produces a gradeable artefact, and collects no student data is a product no foreign competitor will
build, sold into a procurement budget that already exists.** This is the strongest *commercial* moat and it is mostly
integration work, not new engine work.

Design constraint, hard: the DPDP children's carve-out is **purpose-bound and narrow** — an institution may monitor
only for its own educational activities or the safety of enrolled children.

### Moat 5 — Indian compliance and provenance as features
Nobody else will build these, and two of them are legally load-bearing:
- **DPDP-safe by default.** Section 9(3) bans tracking, behavioural monitoring and targeted advertising for anyone
  **under 18** — read as absolute, no consent available, exposure to ₹200 crore. Our telemetry is already off by
  default and refused for children's games. That is the compliant posture; it needs saying out loud, and the under-18
  reality (not just "a game described as for kids") needs to drive the default.
- **The money-game refusal, done properly** (see §5.1 — currently a real gap with criminal exposure).
- **Per-asset provenance.** Steam's Content Survey requires declaring **"any kind of content that ships with your game
  and is consumed by players"** made with AI; Unity's Asset Store requires disclosure; Fab requires a `CreatedWithAI`
  tag. We record none of it. The researcher called provenance *"the single highest-leverage thing to build, because it
  converts an unanswerable legal question into a declarable fact."*
- **Human-authorship record.** The US Copyright Office (Jan 2025, Part 2) holds prompt-only output **not
  copyrightable**; India's Act requires a human who "causes the work to be created" and the Copyright Office rejected
  an AI as author in 2026. So a game made mostly of AI assets **may have little or nothing enforceable in it** — no
  copyright, no claim against a cloner. What *is* protectable is human creative selection, arrangement and
  modification. Recording what the owner chose, changed and rejected turns an invisible defence into a documented one.
  This is also the honest answer to the hostility in §2: the games that succeed disclose AI in the invisible layers and
  write **longer, more hedged disclosures** (median 22 vs 13 words).

---

## 5. What it needs, in order

### 5.1 Fix first — small, and two of them are liabilities

1. **The money-game guard misses what the law actually turns on.** The Act and Rules (in force 1 May 2026) turn on
   *stake plus expectation of monetary return*, and **Rule 9 weighs whether rewards are transferable, redeemable or
   monetisable outside the game.** Offering such a game is **cognisable and non-bailable** (to 3 years / ₹1 crore).
   Our `service.MONEY` catches betting / casino / rummy / teen patti / poker / fantasy cricket / lottery / cash prize.
   It does **not** catch "coins players can withdraw to UPI", redeemable points, tradable skins, cashing out, or a
   transferable token — each of which builds a game that makes *her user* a criminal defendant. Fix: extend the
   refusal, and add a Bible-economy check so a currency can never be marked withdrawable, convertible or transferable.
2. **Our MCP server speaks only the dead dialect.** The current MCP revision is **`2026-07-28`**, which **removed the
   `initialize` handshake**: every request now declares its version in `_meta`
   (`io.modelcontextprotocol/protocolVersion`) and in the `MCP-Protocol-Version` header, and **`server/discover` is
   MUST-implement**. We declare `2025-06-18` / `2025-03-26` / `2024-11-05`. The spec's own compatibility table: a
   dual-era client falls back and **works**; a modern-only client **fails**. Our own plugins are fine; Claude Desktop
   and Cursor may not connect. Fix: support the current revision alongside the legacy handshake.
3. **Per-asset provenance** (model, prompt hash, date, cost, and every human edit after), surfaced as a
   ready-to-paste Steam Content Survey answer and a Unity/Fab disclosure field.
4. **Say the under-18 rule out loud** in the live-ops UI, and make the school carve-out the only way telemetry turns on
   for a classroom game.

### 5.2 Raise the ceiling — the thing that caps us at T1/T2

**Every Hoola game is at most 12 GDScript files (120 KB) on a single plain root node, building every node in code.**
There are no `.tscn` scenes, no animation tracks, no tilemaps. Levels, enemies and items *are* handled well as Bible
data with balance simulation — which is exactly right for match-3, idle, runner and puzzle, where one engine plus a lot
of data *is* the game. It is not enough for a platformer or a story game, where the game largely **is** its scenes.

**What it needs: scenes and animation as checked data**, the same pattern that already works for the Bible — Hoola
generates `.tscn` and animation resources from a declarative description it validates, rather than the model writing
scene files freehand. Without this, every "bigger game" claim is false, and with it the Arena's scores have somewhere
to climb.

**SHIPPED in v0.545 (`server/app/gamedesk/scene.py`, tool `game_scenes`).** Exactly that pattern: the model writes a
declarative spec, Hoola validates it in code and generates the `.tscn`; nodes come from a 44-type allowlist, properties
from a property allowlist (an unknown key is dropped and named), and a scene may instance another scene of the same
game, which is how content scales. One finding hardened the rule beyond the plan: measured in Godot 4.7.2, a
`[sub_resource type="GDScript"]` embedded in a `.tscn` RUNS and reached `DirAccess` — so a model-written scene file
would be a hole through `guard.py`. Script source is therefore refused in three independent places. Every scene is
loaded in the real engine before she sees it, and since an unknown node type yields a silent placeholder rather than an
error, the log's own trouble lines decide the verdict. Still not built: TileMaps (a TileSet plus atlas art is a second
pipeline), 3D scenes, shaders.

### 5.3 Build the Game Arena (Moat 2)

Transplant `site/arena.py` to games, with the parts that transfer and the parts that must be new:
- **Fixed brief set** (never changed without a bump), spread across genres, seeded — so two Hoola versions are judged
  on identical work.
- **Judged by playing, not by looking:** bots play the real build (we have this), and the judge scores from recorded
  play, golden frames and probe state — first-30-seconds legibility, whether the goal is discoverable, whether a bot
  can reach a win and a loss, difficulty curve from the balance sim, input-to-response latency, frame stability.
- **Originality measured** as distance from every other game in the run — and reported as a *shippability* number,
  because Apple 4.3(b) is the rule it answers.
- **Rupees and minutes to ready.** Compare run against run. **Blind duels** against a Rosebud or Summer Engine build of
  the same brief, and against a human-made itch.io game.
- Honest from day one: a game's *fun* is not fully measurable. Score what is measurable and print **NOT ASSESSED** for
  the rest — which is already the house rule.

### 5.4 Reposition around the finishing pipeline (Moat 1)

Prove the whole chain on one real game, end to end, and make that the claim. Concretely: finish the iOS gap (the only
missing platform — it needs the owner's Apple account and a rented Mac, both already solved patterns in this repo), and
write the one-sentence promise into the product.

### 5.5 Go where the money is (Moats 4 and 3)

- **Schools:** a game-making module for the AVGC labs, joined to Shiksha / Pathyakram, gradeable, telemetry-free.
- **Outsourcing shops:** the only buyer who can compute ROI today — price against a billable hour.
- **Agencies:** brand-skinned playables on a campaign deadline; the one place where disposable generated content is
  exactly what is wanted.

### 5.6 Never (write it into the plan as "never", not "later")

**Console builds.** Godot ships no console export templates **by design**: no engine may legally distribute them
without proof of licensed-developer status, and the Foundation's own article names NDA-mandated closed-door development
and the need for a distribution-restricted licence as the reasons
(https://godotengine.org/article/about-official-console-ports/). Only Steam Deck is official. Switch / PlayStation /
Xbox can come only from a licensed party or a porting house (Pineapple Works, Seaven, Sickhead; or W4 Games
middleware). **ID@Xbox is free and explicitly solo-friendly** (10–15 business days) and is the one reachable door —
everything else is a human-reviewed application, an NDA and a non-public certification checklist that software cannot
hold on a user's behalf.

---

## 6. Could not verify (do not quote these as fact)

- **Rosebud's other claimed shipped titles.** *Quantum Agent* ("live on Steam") has no findable Steam listing;
  *Legion Hunters* and *Polity Painter* are listed with a month but no year. And the **Hollow Signal attribution is
  unreconciled**: Steam credits "Dev-Solo Studio" / "Deadline Interactive", Rosebud credits Damian Pannell, and the
  Steam page does not mention Rosebud. The game and its AI disclosure are verified; the causal link is vendor-claimed.
- **No shipped commercial game could be found for any of:** Ludus AI, Summer Engine, Convai, Astrocade, Google
  Playground, Upit, Buildbox 4.
- **Astrocade's scale** — company says 20M engaged users, Naavik says ~5M MAU. Unreconciled.
- **Hiber3D's official status** (fan-wiki shutdown evidence; hiber3d.com returned 403) and **Buildbox 4's** (Steam page
  internally contradictory; pricing page 404s).
- **Steam revenue distribution, rigorously.** Valve publishes nothing; all medians are modelled from review counts and
  the two circulating 2025/2026 medians (**$249** and **$1,728**) differ by 7x and cannot both be right. Use Haro's
  *ratios*, not absolutes. The "7,000 wishlists" figure is folklore and Valve's own docs reportedly say wishlists are
  not an algorithmic visibility factor.
- **A studio census for India.** The 275-studio / 15,000-developer figure is **from 2021**; GDAI 2026 is a
  104-respondent sample that disclaims national representativeness. **Nobody knows how many Indian game studios exist.**
- **The ₹250 crore AVGC allocation** — single-sourced (Deccan Herald). The 15,000 schools / 500 colleges / IICT Mumbai
  scheme is multiply confirmed including a Parliament answer; the rupee figure is not.
- **DPDP Rules commencement dates** (~13–14 May 2027 for the tranche containing Rule 10) — consistent across compliance
  vendors, **not read from G.S.R. 846(E) itself**. Sources also disagree on whether the Fourth Schedule exemptions sit
  under Rule 10 or Rule 12.
- **Whether any category of online social game has been notified for registration under Rule 12.** If one has, the
  "no registration needed" conclusion narrows.
- **Whether the ₹20 lakh GST threshold protects a small service exporter**, or s.24 CGST compels registration.
- **Apple's AI-disclosure position** — I read the guidelines (last updated 16 Oct 2026) and found **no AI-asset
  disclosure rule**; secondary sources contradict each other. **Google Play's claimed April 2026 in-app AI label** is
  in compliance blogs only and is **not** in the policy text.
- **Whether Epic ships an official MCP server** in UE 5.8 — two reports conflict (full-engine plugin vs UEFN-only
  beta), no Epic first-party confirmation. **Unity's is confirmed official; Epic's is not.**
- **Licence terms for Meshy (CC BY 4.0 free tier), Tripo (non-commercial free tier), Hunyuan3D (1M MAU cap, EU/UK/South
  Korea exclusion) and ElevenLabs' game-music carve-out** — all third-party. **Read these at source before shipping;
  the ElevenLabs music threshold is shipping-blocker class.**
- **Godot's animation tooling and Asset Library gaps** vs Unity/Unreal — widely assumed, no source found.
- **Any verified per-player multiplayer cost.** Derived from Edgegap's published unit prices ($0.00115/vCPU-min,
  $0.10/GB egress), a modest session game is **~1.1–1.5 US cents per player-hour** — that is arithmetic, not a quote.
  Photon's **free 100-CCU tier** is the most useful number for a solo creator. Note **Hathora shut down 5 May 2026**
  with ~2 months' notice, so the netcode kit must stay portable.
- **Direct user-complaint threads** — Reddit was blocked to the crawler, so §3's failure-mode evidence leans on
  review-blog summaries plus in-product failures that were directly verified. **Worth reading r/gamedev, r/Unity3D and
  the Rosebud Discord directly before betting on it.**

---

## 7. The five sentences that matter

1. **Making games is a commodity; finishing them is not** — and the finishing pipeline is the one part of the market
   nobody owns, which we already mostly built.
2. **We cannot tell whether a Hoola game is any good**, and until there is a Game Arena, every "more powerful" claim is
   a claim rather than a number.
3. **The ceiling is 12 code files**, so "bigger games" is false until scenes and animation become checked data.
4. **The money is in schools, outsourcing shops and agencies** — not in solo creators publishing games, because the
   median game earns ~$300 and AI games succeed at 55% of the non-AI rate.
5. **Two liabilities are live right now**: a game with withdrawable in-game currency passes our guard, and that is a
   non-bailable offence for whoever publishes it.
