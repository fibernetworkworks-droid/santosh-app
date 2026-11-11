# Game Tool Hub — connecting Hoola Game Dev to the world's game-making tools (research, 11 Nov 2026)

Owner's ask: connect Hoola's game engine (Godot 4.7 builds on Hoola's server + the Unity / Unreal editor plugins of
v0.444) to the best game-making tools in the world.

Method: every row was checked against the **vendor's own page** (docs, API reference, pricing, licence / terms, MCP
page) in this session, 11 Nov 2026, unless its **Check** column says otherwise. Facts already researched in
`docs/GAME_MOAT_PLAN.md` were reused, not redone, and are marked `M`. Where a primary source could not be read, the row
says **NOT VERIFIED** and why. Nothing here is a guess presented as a fact.

Rules this plan obeys (CLAUDE.md, NON-NEGOTIABLE): official routes only (no scraping, **no unofficial MCP servers**,
no consumer-subscription OAuth); her keys only in the app / VPS `.env`, sealed, never in chat; money never moves
without her tap (every paid call = a price card first). Anything that would run through Hoola's **Windows desktop app**
is in the owner-frozen Mera PC area and is marked **needs her OK (PC freeze)**. Plugins that run *inside* Unity /
Unreal / Godot editors (the v0.444 Big-Studio mode) are outside the freeze.

**Check column key:** `V` = verified on the vendor's own page this session · `M` = verified in GAME_MOAT_PLAN.md
(its sources) · `H` = Hoola already runs it (code in this repo is the evidence) · `S` = secondary sources only, vendor
page not readable · `NV` = NOT VERIFIED (reason in the row or in section 5).

---

## 1. The one-paragraph answer

The table has **116 rows for 110 unique tools** (six rows are a second face of a vendor already listed: Meshy and
Tripo rigging, Stable Fast 3D self-hosted, Roblox Cube / Creator Store / Open Cloud). Of the 110: **62 have an official
route Hoola can use today** (an open-source licence that allows server use, a documented vendor API, a vendor-published
MCP server, or an official in-tool scripting API) — by primary lane **Lane 1 (Hoola's own workspace): 15 · Lane 2
(cloud API, her key): 25 · Lane 3 (official vendor MCP): 13 · Lane 4 (her own machine): 9**; **8 need a partner
application or a vendor deal** (Kaedim, Move.ai, Freesound commercial, CGTrader, Adobe Firefly / Substance cloud,
Xbox, Nintendo, PlayStation); **9 are blocked** (no API at all: Mixamo, Udio, Suno self-serve, Fab / Megascans,
OpenGameArt; the licence forbids the Hoola shape: Stable Fast 3D self-hosted without Enterprise, Hunyuan3D on the server
without a GPU + EU/UK/KR geo-fence, Defold as a sold "Game Engine Product", Aseprite on a server); and **31 are
unverified or not worth it now** (named in section 5). **Verification: 41 rows checked on the vendor's own page this
session (V), 15 already running in Hoola (H), 3 resting on GAME_MOAT_PLAN's sources (M), 35 secondary-only (S), 16 NOT
VERIFIED (NV).** Already **built: 19** of the 62 (Godot, Blender, the Unity / Unreal plugins, Gemini art, Lyria, TTS,
code-made SFX, FFmpeg, scenes-as-data, GitHub, Actions, itch butler, Play, App Store Connect, live ops, translation,
Google docs). The two biggest findings: **every serious AI-3D vendor's terms forbid the "Newtika's pooled account"
shape** (Meshy: "solely for your internal use", no resale; Tripo: may not make the service "available to any third
party", API keys non-transferable) — so Lane 2 must be **her key, her account, her plan**, never Newtika credits
resold; and **Epic now ships an official MCP server inside Unreal 5.8** (Epic's own docs, Experimental), which
GAME_MOAT_PLAN listed as unconfirmed.

---

## 2. The table

Lanes: **1** Hoola's own workspace (open source, headless on Hoola's Linux server) · **2** cloud API (her key sealed on
the server, price card + her tap before paid calls) · **3** official vendor MCP (Hoola as MCP client — it already has
one: `bazar/connectors/mcp_remote.py`, `mcp_session.py`) · **4** her own machine (official plugin / scripting API inside
a tool she licenses).

Hoola status: **built** (exists in code) · **easy** (official route, no account decision, a few days) · **her
account** (works once she makes / links her own account or key) · **deal** (needs a Newtika partner agreement or
vendor approval) · **blocked** (reason given).

### 2.1 Engines

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Godot 4.7 | Engine | 1 | Engine itself, headless CLI | None from the Foundation (all ~7 Godot MCPs are community) | MIT; only obligation = keep the notice; console export templates deliberately not distributed | Free | **built** (v0.370 → v0.545) | V | S43, S65, M |
| 2 | Unity 6 | Engine | 4 | Editor scripting (C#) | **Yes** — Unity MCP via the Unity CLI + official plugin for Claude Code / Codex / Grok; free, no concurrency limit, no credits via the AI gateway; Unity 6+ | Unity licence is hers; ToS update eff. 30 Jun 2026: training ML on Unity data needs written authorisation (Unity says local MCP / AI integrations stay allowed) | MCP free; Unity plan hers | **built** (v0.444 UPM package, NOT VERIFIED in a real editor) — easy to also speak to Unity's own MCP | V | S38, S39, S80 |
| 3 | Unreal Engine 5.8 | Engine | 4 | Unreal Python + Editor Utility | **Yes — "Unreal MCP" plugin, Epic docs, marked Experimental**; HTTP on 127.0.0.1:8000/mcp, **no auth layer**, tools from the AllToolsets registry, one call at a time on the game thread | Her Epic EULA (5% royalty rules are hers) | Free plugin | **built** (v0.444 Python plugin, NOT VERIFIED in editor) — easy to pair with Epic's MCP | V | S40 |
| 4 | Roblox Studio | Engine / platform | 4 | Luau in Studio | **Yes — built into Studio** (execute_luau, generate_mesh / generate_material, insert_asset, search_asset, playtest, screen_capture...) | Roblox ToS; output lives only on Roblox | Free | easy (her Studio, her MCP client) | V | S41 |
| 5 | Roblox Open Cloud | Publishing API | 2 | **Yes** — Assets API, place publishing, x-api-key or OAuth 2 | Studio MCP above | Keys scoped on her Creator Dashboard | Free | her account | V | S42 |
| 6 | UEFN (Fortnite) | Engine | 4 | Verse | Epic reportedly extended Unreal MCP to UEFN (20 Aug 2026) | Epic creator terms | Free | NV — secondary only | S | S40 (5.8 page silent on UEFN) |
| 7 | Defold | Engine | 1 | Engine + `bob.jar` build tool | None found | Defold License 1.0 (Apache-derived) **forbids commercialising the engine "as a Game Engine Product"** — whether a paid Hoola that wraps it counts is not answered | Free | blocked until a lawyer / the Defold Foundation answers | V | S46 |
| 8 | Cocos (COCOS 4 / Creator) | Engine | 1 | Engine + CLI, "headless IDE mode" per reports | None found | Reported MIT for COCOS 4 (2026); GitHub metadata says "other" | Free | NV — licence file not read | S | S48 |
| 9 | GameMaker | Engine | 4 | GML in IDE | None found | Free = non-commercial; Professional one-time licence for sale; new GMRT runtime free commercially from 2027 | $99.99 one-time (secondary) | NV | S | S47 |
| 10 | Bevy | Engine | 1 | Rust crate | None | MIT OR Apache-2.0 | Free | not a fit (Rust, no editor) — skip | V | S49 |
| 11 | Stride | Engine | 1 | C# | None | MIT (from memory) — NOT read | Free | NV, low priority (Windows-centric) | NV | — |
| 12 | O3DE | Engine | 1 | Python / C++ | None found | Apache-2.0 / MIT (from memory) — NOT read | Free | NV, low priority | NV | — |

### 2.2 3D DCC (modelling, sculpting, procedural)

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 13 | Blender 5.x | 3D DCC | 1 | bpy (Python), headless `-b` | **Yes — Blender Lab MCP server** (Blender 5.1+, add-on + server); the page itself warns it "will execute LLM generated code in Blender without any guards" | GPL; **"what you create with Blender is your sole property"**; commercial use explicit | Free | **built** (3D Studio `blender3d/` with its own guard + sandbox). Do NOT swap in Blender Lab's MCP on the server — it has no guard | V | S44, S45 |
| 14 | Autodesk Maya | 3D DCC | 4 | Python / MEL / C++ | **None for Maya** (Autodesk's official MCPs found: Fusion, Product Help docs); community Maya MCPs only | Her Autodesk subscription, per seat | Hers | easy via a Hoola plugin in Maya — **needs her OK (PC freeze)** if it rides the desktop app | S | S51 |
| 15 | Autodesk 3ds Max | 3D DCC | 4 | pymxs / MAXScript | None (community only) | Per seat | Hers | as Maya | S | S51 |
| 16 | Houdini (SideFX) | Procedural | 4 | hou Python, Houdini Engine | **Partial** — "Apex Script MCP" early preview in Houdini 22, **rigging only** (analyst report; no SideFX page read) | Indie / Apprentice limits are hers | Hers | NV | S | S52 |
| 17 | Cinema 4D 2026.4 | 3D DCC | 4 | Python SDK | **Yes — built-in MCP server**, off by default, adapter token, separate Python-execution control | Maxon subscription | Hers | easy (her machine) | V | S50 |
| 18 | ZBrush | Sculpt | 4 | ZBrush Python SDK | None found | Maxon subscription | Hers | low priority | S | S50 |
| 19 | Modo | 3D DCC | 4 | Python | None found | Status of the product NOT checked | — | NV | NV | — |
| 20 | Autodesk Product Help MCP | Docs | 3 | — | Yes (docs only, no app control) | Autodesk | Free | easy, low value | S | S51 |
| 21 | glTF-Transform / Khronos glTF Validator | Mesh tooling | 1 | CLI / JS | None | MIT / Apache (from memory, NOT read) | Free | easy — the right checker for every GLB Hoola receives from Lane 2 | NV | — |

### 2.3 AI 3D, texture and 2D generation

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 22 | **Meshy** | AI 3D | 2 | **Yes** (text/image/multi-image → 3D, retexture, rigging, animation, text-to-motion) | **Yes** — `@meshy-ai/meshy-mcp-server`, github.com/meshy-dev, reads MESHY_API_KEY | **Free plan: Meshy owns the output, CC BY 4.0, credit Meshy. Paid: customer owns it.** "Solely for your internal use"; **no resale / redistribution of the Service**; no one account for many users; no training competing models; **non-Enterprise API output deleted after 3 days** (Hoola must download at once); non-Enterprise inputs may be used for training (opt-out by email) | Prepaid credits: image→3D 5–35, text→3D 5–20, rig 5, animation 3/action ($ per credit not on page) | **her account** (BYOK, her paid plan; free plan only with the credit line in the game) | V | S1, S2, S3 |
| 23 | **Tripo** (VAST / Holymolly) | AI 3D + rig + animation | 2 | **Yes** — openapi.tripo3d.ai/v3, Bearer; 1 credit = $0.01 | "Official" Tripo MCP repo (alpha, 8 commits) — **drives a local Blender + Tripo add-on**, not usable on the server | **Free users: "Tripo retains all rights"** (stricter than "non-commercial"). Paid users: "generally have all rights". **May not make the service available to any third party** without written consent; API keys may not be transferred; no exclusivity; Tripo does not train on inputs/outputs | Model $0.10–0.30, retopo / texture $0.05–0.40, auto-rig $0.25, retarget $0.10 | **her account** (BYOK, paid plan only). Ask Holymolly in writing whether BYOK-through-Hoola counts as "making it available" | V | S4, S5, S6 |
| 24 | Hunyuan3D 2.x (Tencent, open weights) | AI 3D | 1 | Self-host weights | None | Tencent Community Licence: **Territory excludes EU, UK, South Korea**; **>1M MAU needs Tencent's licence**; Tencent claims no rights in outputs; **outputs may not improve other AI models**; a hosted service must name its provider prominently; no military use | Free; needs a GPU | blocked on server until (a) Hoola has a GPU and (b) EU/UK/KR users are geo-fenced | V | S7 |
| 25 | Hyper3D Rodin | AI 3D | 2 | **Yes** — api.hyper3d.com/api/v2, Bearer | None on docs | Terms NOT read | Credits; per-call price not on docs (resellers ~$0.10–0.75) | her account after terms are read | V (API) / NV (terms) | S8 |
| 26 | TRELLIS (Microsoft) | AI 3D | 1 | Self-host | None | **MIT for models and most code**; two submodules (diffoctreerast, modified FlexiCubes) carry their own licences — NOT read | Free; NVIDIA GPU ≥16 GB | strongest Lane-1 candidate once Hoola rents a GPU (the Modal pattern of the Interactive lab) and the two submodule licences are read | V (partial) | S14 |
| 27 | Stable Fast 3D — Stability **cloud API** | AI 3D | 2 | **Yes** — Fast 3D = 10 credits (~$0.10) | None | API customer terms (Hoola as a customer, not a provider) | ~$0.10 / model | easy (her key) | S | S13 |
| 28 | Stable Fast 3D — **self-hosted** | AI 3D | 1 | Weights | None | Community licence <$1M revenue, **but "API providers" need the Enterprise licence** — Hoola running it for users is that | — | **blocked** without an Enterprise licence | V | S12 |
| 29 | CSM Cube | AI 3D | 2 | **Yes** — REST + Python SDK, image→3D sessions, GLB | None found | Terms NOT read; API reportedly only on mid / enterprise plans | NV | NV | S | S15 |
| 30 | Kaedim | AI 3D (human-in-loop) | 2 | **Yes, Enterprise customers only** | None | Enterprise contract | Quote | **deal** (Enterprise) | V | S16 |
| 31 | Luma (Genie 3D) | AI 3D | 2 | Reported (2024 launch); current status unclear | None | — | — | NV — no Luma page read | NV | — |
| 32 | **Scenario** | AI 2D / 3D / game assets (40+ partner models) | 3 | **Yes** REST | **Yes — mcp.scenario.com/mcp**, OAuth (individual) or API key+secret (automation); spends the same Compute Units | Output rights not on the MCP page — terms NOT read | Compute Units | her account; read output-rights terms first | V (MCP) / NV (rights) | S9, S10 |
| 33 | Leonardo.ai | AI image / video | 2 | **Yes** | **Yes** per Leonardo docs (mcp.leonardo.ai/v1/mcp) — page only partly read | API outputs commercial "subject to our Terms"; terms page returned 403 | Credits | NV until terms are read | S | S11 |
| 34 | Hoola picture engine (Gemini photogen) | AI 2D | 2 | Google API | — | Google terms (already accepted by Newtika) | ~₹3 / sprite | **built** (v0.416 style-locked sprites) | H | assets.py |
| 35 | Adobe (Photoshop, Illustrator, Firefly, Stock... connector) | 2D / AI image | 3 | Firefly Services APIs (enterprise) | **Yes — Adobe's own connector**, launched for Claude 28 Apr 2026, renamed "Adobe", >80 tools (Sep 2026); Adobe says "not optimized for enterprise", no EDU | Her Adobe account | Her plan | her account; whether Hoola's own MCP client may use it (vs Claude only) NOT confirmed | V | S53 |
| 36 | Adobe Firefly Services / Substance 3D API (cloud) | AI image + 3D render | 2 | **Yes** — REST (Substance 3D API: cloud render + generative) | — | Enterprise contract (PSLT terms) | Enterprise quote | **deal** | S | S54 |
| 37 | Roblox Cube (generate_mesh) | AI 3D | 3 | Only inside Roblox | Via Roblox Studio MCP (row 4) | Output only on Roblox | Free | only for Roblox games | V | S41 |

### 2.4 Animation and motion

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 38 | Meshy rig + animation | Auto-rig, library | 2 | Yes (row 22) | Yes (row 22) | As row 22 | 5 + 3/action credits | her account | V | S3 |
| 39 | Tripo auto-rig + retarget | Auto-rig | 2 | Yes (row 23) | — | As row 23 | $0.25 + $0.10 | her account | V | S4 |
| 40 | DeepMotion Animate 3D | Video → mocap | 2 | **Yes** REST (FBX / BVH), access by request form | None | Commercial terms on request; free tier reportedly non-commercial (secondary) | NV | her account + approval | V (API) / S (price) | S17 |
| 41 | Move.ai | Video → mocap | 2 | **Yes** — GraphQL api.move.ai, Python SDK; **key issued by Move AI staff** (early access) | None | Terms NOT read | NV | **deal** (early access) | V | S18 |
| 42 | Mixamo | Rig + animation library | — | **No API** | None | Adobe additional terms bar using it to train / improve ML systems | Free (Adobe ID) | **blocked** — no official route; scripting the website = scraping | S | S19 |
| 43 | Cascadeur | Physics animation | 4 | Python API in the app | None | Indie licence only under $100k revenue / funding | Hers | low priority, her machine | S | S20 |
| 44 | Spine (Esoteric) | 2D skeletal | 4 | Spine CLI / export | None | **Every user of the runtimes must hold their own Spine Editor licence** (Runtimes licence, Apr 2025) — Hoola cannot ship Spine runtimes in a user's game unless she owns Spine | Hers | her account; never default | S | S21 |
| 45 | DragonBones | 2D skeletal | 1 | Runtimes | None | Project status + licence NOT read | Free | NV | NV | — |
| 46 | Godot AnimationPlayer (scenes as data) | Animation | 1 | Godot | — | MIT | Free | **built** (v0.545 `scene.py` animation tracks) | H | scene.py |

### 2.5 Materials and textures

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 47 | **Poly Haven** | HDRIs, PBR textures, models | 2 | **Yes** — api.polyhaven.com, no key | None | Assets **CC0**. API ToS: **free for anyone incl. commercial**, no special agreement; "Powered by Poly Haven" credit only where live API content is shown; **must send a unique User-Agent / Referer** | Free (optional sponsorship) | **easy** — first thing to build | V | S28, S29 |
| 48 | **ambientCG** | PBR materials | 1 | API exists (terms not read) | None | Assets **CC0**, no credit needed | Free | easy — mirror a curated set onto Hoola's disk (CC0 allows it); API terms NV | V (assets) | S30 |
| 49 | **Kenney** | 2D / 3D / audio game kits | 1 | **No API** | None | **CC0**, commercial OK; do not use the Kenney logo alone | Free | **easy** — download packs once, ship as Hoola's local library | V | S31 |
| 50 | Substance 3D Painter / Designer / Sampler | Texturing | 4 | Python + JS in-app APIs | None official (community Painter bridge only) | Adobe subscription per seat | Hers | her machine — **needs her OK (PC freeze)** if via the desktop app | S | S54 |
| 51 | Substance 3D Automation Toolkit (SAT / pysbs) | .sbsar batch | 1 / 4 | Python, CLI | None | Adobe enterprise / licence terms for server use NOT read | Enterprise | NV | S | S54 |
| 52 | Quixel Megascans (now in Fab) | Scans | — | **No public API found** | None | Fab Standard licence; **"NoAI" content may not be used as inputs to generative AI** | Paid on Fab | **blocked** | S | S34 |
| 53 | Material Maker | Procedural textures | 1 | Godot-based app; CLI args file present, headless export NOT confirmed | None | MIT | Free | easy if headless works (same engine Hoola already runs) | V (licence) | S57 |
| 54 | ArmorPaint | Painting | 1 | — | None | Licence NOT read | — | NV | NV | — |

### 2.6 2D, pixel art and level tools

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 55 | Aseprite | Pixel art | 4 | CLI batch + Lua scripting | None | Proprietary EULA since 2016; **no redistribution; server-side commercial use unanswered** by the developers | $19.99 per user (from memory, NV) | her machine only; **blocked on the server** | S | Aseprite forum thread (S85) |
| 56 | Krita | Painting | 1 / 4 | Python API | None | GPL (from memory) | Free | NV — low value headless | NV | — |
| 57 | Tiled | Tile maps | 1 | CLI tools (export) | None | GPL-2.0 editor + BSD / Apache libraries | Free | easy — needed for v0.545's missing TileMaps (TMX → Godot TileSet) | V (licence) | S55 |
| 58 | LDtk | Level editor | 1 | JSON format + Haxe API | None | MIT | Free | easy — read LDtk JSON she exports; headless export NV | V (licence) | S56 |
| 59 | Inkscape | Vector | 1 | CLI | None | GPL (from memory) | Free | NV | NV | — |
| 60 | Pixelorama | Pixel art (Godot-based) | 1 | — | None | NOT read | Free | NV | NV | — |

### 2.7 Audio

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 61 | **ElevenLabs** (voice, SFX, music) | Audio | 3 | **Yes** — TTS, **Sound Effects** (≤30 s, loopable), Music API | **Yes — hosted api.elevenlabs.io/v1/mcp, OAuth** (local server deprecated) | **Commercial licence starts at Starter**; Free shows none; "Music commercial use" listed from Starter | Starter $6/mo (30k credits) | **her account** (Starter or above, never Free) | V | S22, S23, S24 |
| 62 | Google Lyria (music) | Music | 2 | Google API | — | Newtika's Google terms | ~₹7 / track | **built** (v0.416 music) | H | assets.py |
| 63 | Hoola TTS (voice lines) | Voice | 2 | Existing voice stack | — | — | ~₹1 / line | **built** | H | assets.py |
| 64 | Code-made SFX (sfx.py, Bfxr-style presets + seed) | SFX | 1 | Hoola's own code | — | Hoola's own | Free | **built** | H | sfx.py |
| 65 | Suno | Music | — | **No self-serve API**; curated partner programme opened Jul 2026 | None | Commercial embedding without Suno's written permission = legal exposure | — | **blocked** (deal only); never via unofficial wrappers | S | S25 |
| 66 | Udio | Music | — | **No public API** found | None | — | — | **blocked** | S | S26 |
| 67 | Stable Audio (Stability API) | Music / SFX | 2 | Yes (Stability platform) | None | API customer terms | Credits (price cut Oct 2026 per secondary) | easy-ish; NV price | S | S12, S13 |
| 68 | Freesound | SFX library | 2 | **Yes** — APIv2, OAuth2 for downloads | None | **API free only for non-commercial use; commercial use needs a licence from Freesound**; each sound's own CC licence (CC0 / BY / BY-NC) must be honoured | Free non-commercial | **deal** (Newtika must ask Freesound) | V | S27 |
| 69 | FMOD Studio | Audio middleware | 4 | Studio API | None | Free indie tier reportedly < $200k revenue and < $500k budget — vendor page empty when read | Hers | NV; no official Godot integration checked | S | S84 |
| 70 | Wwise | Audio middleware | 4 | WAAPI | None | Free under $250k budget (vendor blog, secondary; pricing page 403) | Hers | NV | S | S86 |
| 71 | FFmpeg | Audio / video | 1 | CLI | — | LGPL/GPL (legal page 503 when read) | Free | **built** (OGG conversion) | H | assets.py |

### 2.8 Asset stores and libraries

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 72 | **Sketchfab** | 3D library | 2 | **Yes** — Data API v3 + Download API | **None** (gregkop's is community → not allowed) | **End user must log in with her own Sketchfab account (OAuth)**; app must show each model's CC licence + author + "provided by Sketchfab"; licence must follow the asset everywhere; API account 18+; per-model CC (BY / BY-NC / ND) decides commercial use | Free (CC) / paid store | **her account** — and provenance (v0.536) must carry the CC licence + author | V | S32, S33 |
| 73 | Fab (Epic) | Marketplace | — | **No public buyer API found** | None (the "Fab MCP" found is third-party and downloads without login → not allowed) | Standard / CC-BY; **NoAI content may not be used as inputs to generative AI** | Paid / free | **blocked** | S | S34 |
| 74 | Unity Asset Store | Marketplace | 4 | Via Unity Package Manager in her editor | None | **Asset Store content may not train AI/ML**; EULA engine-scope NOT read | Hers | her editor only | S | S35 |
| 75 | itch.io asset packs | Marketplace | — | No purchase / download API found | None | Per-pack licence | — | NV | NV | — |
| 76 | OpenGameArt | Library | — | No official API found (site returned 403) | None | Mixed CC0 / CC-BY / GPL / OGA-BY | Free | NV — blocked until an official route exists | NV | — |
| 77 | CGTrader | Marketplace | 2 | **Yes** — OAuth 2.0, keys by application ("partners") | None | Partner terms | — | **deal** | S | S36 |
| 78 | TurboSquid | Marketplace | 2 | Publishing API (bulk upload for sellers); **no buyer API found** | None | — | — | not useful for buying | S | S37 |
| 79 | Roblox Creator Store | Library | 3 | Via Studio MCP `search_asset` / `insert_asset` | Yes (row 4) | Roblox only | Free | only for Roblox | V | S41 |

### 2.9 Design, collaboration, version control

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 80 | Figma | UI design | 3 | REST | **Yes** (official Figma MCP; this session is connected to it) | Her plan | Hers | her account | S (self-description of the connected server) | S81 |
| 81 | Miro | Boards | 3 | REST | **Yes — mcp.miro.com**, OAuth 2.1, admin must enable for orgs | Her plan | Hers | her account | V | S75 |
| 82 | Notion | Docs | 3 | REST | **Yes — mcp.notion.com/mcp** (hosted; old local server unmaintained) | Her plan | Hers | her account | V | S76 |
| 83 | Jira / Confluence (Atlassian Rovo MCP) | Production | 3 | REST | **Yes — mcp.atlassian.com/v1/mcp**; Cloud only (no Data Center) | Her plan | Hers | her account | V | S77 |
| 84 | Linear | Production | 3 | GraphQL | Official MCP believed to exist — NOT read | — | — | NV | NV | — |
| 85 | GitHub | Version control | 2 | REST / GraphQL | Official github-mcp-server (not re-read) | Her account | Free tier | **built** (v0.386 game GitHub card, Developer Sahayak) | H | studio.py / github.py |
| 86 | Perforce P4 | Version control (big studios) | 3 | P4 API | **Perforce-published p4mcp-server** (2026.1: streams, central HTTP deploy, MCP registry); one source still calls it "community supported" | Her Perforce server | Hers | her account, big-studio mode only | S | S78 |
| 87 | Unity Version Control (Plastic) | Version control | 2 | REST / CLI (not read) | None found | Mar 2026: no per-seat charge for cloud VCS, 25 GB free storage, egress $0.10/GB after 100 GB | Metered | NV (API) | S | S83 |
| 88 | Google Docs / Sheets / Drive | Docs | 2 | Google APIs | — | Her Google sign-in (currently expired on the VPS, per CLAUDE.md) | Free | **built** | H | CLAUDE.md |

### 2.10 Build and CI

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 89 | Godot export templates (server builds) | Build | 1 | Godot CLI | — | MIT | Free | **built** (Linux / Windows / macOS ad-hoc / Web; Android in her repo) | H | platforms.py |
| 90 | GitHub Actions (her builds repo) | CI | 2 | Yes | — | Her account | Free tier | **built** (hoola-game.yml) | H | platforms.py |
| 91 | GameCI (unity-builder) | Unity CI | 2 | GitHub Action | None | MIT; needs **her** Unity licence as a repo secret (GameCI docs, not read) | Free | easy for Big-Studio Unity users | V (licence) | S59 |
| 92 | Unity Build Automation | Unity cloud build | 2 | REST (not read) | None | Metered; 200 free Windows minutes, $0.02–0.07/min (secondary) | Metered | NV (API) | S | S60 |

### 2.11 Publishing and stores

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 93 | Steamworks / SteamPipe (steamcmd) | Store | 2 | steamcmd + app-build scripts | None | **$100 Steam Direct fee per product, recouped after $1,000 AGR**; dedicated build account with only "Edit App Metadata" + "Publish App Changes"; Steam Guard; **default branch can only be set live in the App Admin panel** (a human step, by design) | $100 / game | **built** as scripts in the store kit (Hoola never logs into her Steam). Next: run steamcmd for a *beta* branch with her sealed build account, her tap | V | S61, S62 |
| 94 | itch.io butler | Store | 2 | **Yes** — butler + BUTLER_API_KEY | None | Her itch account | Free | **built** (v0.416, her tap) | H + V | S63 |
| 95 | Google Play Developer API | Store | 2 | Yes | — | Her Play account (service-account key sealed) | $25 once (Google) | **built** (App Sahayak v0.331, games via hoola-game.yml) | H | platforms.py, appmaker |
| 96 | App Store Connect API | Store | 2 | Yes | — | Her Apple account; runs in her builds repo | $99/yr (Apple) | **built** for apps (v0.339); **iOS game builds not built** | H | appmaker/ios |
| 97 | Epic Games Store (BuildPatchTool + Dev Portal) | Store | 2 | BPT CLI with client id / secret from her Dev Portal | None | Fee: sources conflict ($100 vs free) | NV | her account; NV | S | S64 |
| 98 | Xbox (ID@Xbox) | Console | — | Partner only | — | Free, solo-friendly application (10–15 business days); NDA | — | **deal** (her application) | M | S65 / moat 5.6 |
| 99 | Nintendo Switch | Console | — | Partner only | — | Licensed-developer status, NDA | — | **deal** | M | moat 5.6 |
| 100 | PlayStation | Console | — | Partner only | — | Licensed-developer status, NDA | — | **deal** | M | moat 5.6 |

### 2.12 Backend, live ops, analytics

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 101 | Hoola Live Ops (own) | Live config, A/B, crashes | 1 | Hoola's own | Hoola's own /mcp/gamedesk | — | Free | **built** (v0.432) | H | liveops.py |
| 102 | Nakama (Heroic Labs) | Game backend | 1 | Server + official Godot client | None | **Apache-2.0, self-hostable** (needs Postgres-wire DB) | Free (self-host) | easy — the right multiplayer / accounts backend for Hoola games; keeps v0.422's "portable netcode" promise | V | S58 |
| 103 | Firebase | Backend / Crashlytics | 3 | Yes | **Yes — in firebase-tools (`npx firebase-tools mcp`)**, stdio, local | Her Google project | Free tier | her account | V | S67 |
| 104 | PlayFab | Backend | 2 | REST | None found | **Dev mode: 1,000 lifetime players per title**; Foundation mode free only with an Xbox publishing agreement | $99 / $1,999 per month + meters | her account; weak fit for small games after the cut | V | S66 |
| 105 | GameAnalytics | Analytics | 2 | Collection API (events); Metrics / Org API + **MCP server only in PipelineIQ (from $499/mo)** | Paid tier only | — | Free plan "no MAU cap" | easy for collection; MCP = deal | V | S68 |
| 106 | Photon (Realtime / Fusion / Quantum) | Netcode cloud | 2 | SDKs | None | **Free 20 CCU = development & non-commercial only; free 100 CCU commercial = Fusion / Quantum only, one app per customer** | 500 / 1,000 / 2,000 CCU plans | her account | V | S69 |
| 107 | Epic Online Services | Accounts / lobbies | 2 | SDK | None | Described by Epic as free, any store | Free | NV (terms not read) | S | S70 |
| 108 | Unity Gaming Services | Backend | 2 | REST | — | Not read | — | NV | NV | — |
| 109 | AWS GameLift | Dedicated servers | 2 | AWS API | Not checked | Not read | Metered | NV | NV | — |

### 2.13 Localisation, QA / crash, ratings

| # | Tool | Category | Lane | Official API | Official MCP | Licence / terms that matter | Cost | Hoola status | Check | Sources |
|---|---|---|---|---|---|---|---|---|---|---|
| 110 | Crowdin | Localisation | 3 | REST | **Yes — hosted mcp.crowdin.com/v2/mcp**, PAT as Bearer; enterprise per-org subdomain | Her plan | Free tier exists | her account | V | S71 |
| 111 | Lokalise | Localisation | 3 | REST | **Yes — cloud-hosted, beta**, OAuth (docs also show API-token setup) | Her plan | Hers | her account | V | S72 |
| 112 | Hoola translation (Indian languages) | Localisation | 2 | Existing model stack | — | — | Model calls | **built** (store texts, app strings) | H | storelang.py |
| 113 | Sentry | Crash / errors | 3 | REST | **Yes — mcp.sentry.dev/mcp**, OAuth, org / project scoping | Her plan | Free tier | her account (Godot SDK support NOT checked) | V | S73 |
| 114 | Bugsnag (SmartBear) | Crash | 3 | REST | **Yes — SmartBear MCP** (`@smartbear/mcp`, MIT; remote bugsnag.mcp.smartbear.com) | Her plan | Hers | her account | V | S74 |
| 115 | Backtrace | Crash | 2 | REST (not read) | None found | — | — | NV | NV | — |
| 116 | IARC | Age rating | 2 (inside each store's console) | **No developer API found** — ratings come through a participating storefront's questionnaire (Play Console etc.); IARC says "at no cost" | — | — | Free | **built** as a draft (v0.416 age-rating draft); filing stays inside each store | S | S79 |

> 116 rows, 110 unique tools: rows 5, 28, 37, 38, 39 and 79 are a second face of a vendor listed elsewhere and are
> left out of the counts in section 1.

---

## 3. Blocked or no-route — and exactly why

| Tool | Why there is no route today | What would open it |
|---|---|---|
| **Mixamo** | No API at all; Adobe's additional terms bar ML use. Automating the website would be scraping. | Nothing on our side. Use Meshy / Tripo rigging (rows 38-39) instead. |
| **Udio** | No public developer API; only third-party wrappers (unofficial = forbidden). | An official Udio API. |
| **Suno** | No self-serve API; invite-only partner programme (Jul 2026); embedding outputs commercially without written permission is legal exposure. | Newtika applies to the partner programme. Until then: Lyria + ElevenLabs music. |
| **Fab / Quixel Megascans** | No public buyer API; NoAI-tagged content may not be an input to generative AI; the "Fab MCP" found downloads without a login (unofficial). | An Epic buyer API. |
| **Unity Asset Store (from the server)** | No download API outside her Unity editor; Asset Store content may not train AI. | Only inside her own editor (Lane 4). |
| **OpenGameArt, itch asset packs** | No official API found. | Her manual upload (Hoola's v0.416 upload path already checks bytes). |
| **Stable Fast 3D self-hosted** | Stability's licence puts "API providers" on the Enterprise tier. | An Enterprise licence — or use Stability's cloud API (row 27). |
| **Hunyuan3D on Hoola's server** | Territory excludes EU / UK / South Korea; >1M MAU needs Tencent; no GPU on the VPS. | A GPU host + EU/UK/KR geo-fence + provider disclosure; or TRELLIS (MIT) instead. |
| **Defold as Hoola's runtime** | "May not commercialise … as a Game Engine Product" — unclear for a paid platform. | A written answer from the Defold Foundation. Not needed: Godot already fills this slot. |
| **Aseprite on the server** | Proprietary EULA, no redistribution, server use unanswered by the developers. | A written licence. Her own copy on her machine is fine. |
| **Community MCP servers** (every Godot MCP, Sketchfab MCP, Maya / Max / Houdini community MCPs, Tripo "unofficial" servers, Leonardo / Scenario / Lokalise community ones) | NON-NEGOTIABLE: no unofficial MCP. | The vendor publishing its own. |
| **Consoles (Switch, PlayStation, Xbox)** | Partner-only, NDA, non-public certification; Godot ships no console templates by design. | Her ID@Xbox application (the one solo-friendly door) or a licensed porting house. |
| **Partner-gated APIs: Kaedim, Move.ai, CGTrader, Freesound commercial, Firefly / Substance cloud, GameAnalytics MCP** | Approval or enterprise contract required. | A Newtika application per vendor; Freesound is the cheapest to ask (it is a non-profit). |

---

## 4. Recommended build waves (biggest lift in game quality per rupee first)

**Ground rule for every Lane-2 wave:** **her key, her account, her paid plan** — sealed on the server the way itch /
Play / Meshy-style keys already are. Meshy's "solely for your internal use / no resale" and Tripo's "may not make the
service available to any third party" both forbid Newtika buying credits and reselling them. Every generated asset
lands in the v0.416 asset registry, passes `check_file`, gets her OK, and its provenance row (v0.536) records vendor,
model, plan type (free = CC BY credit line for Meshy) and the source licence.

### Wave 1 — free CC0 libraries + the cheapest real 3D (weeks 1-3, ~₹0 for Newtika)
- **Poly Haven API** (row 47): HDRI skies, PBR textures and models into 3D Studio and Godot scenes. CC0, commercial use
  free, one "Powered by Poly Haven" line, a unique User-Agent. *She gets:* real-looking ground, walls, sky in every 3D
  game for nothing.
- **Kenney + ambientCG local library** (rows 48-49): download once, keep on Hoola's disk (CC0 allows it), index by tag,
  Bible-palette check on pull. *She gets:* instant placeholder-quality-or-better sprites, tiles, UI and sounds with
  zero cost and zero waiting — the free first draft before any paid generation.
- **Tiled / LDtk import** (rows 57-58): finishes v0.545's honest gap (no TileMaps). *She gets:* platformer levels.
- **glTF validation** (row 21) on every GLB that arrives from anywhere.

### Wave 2 — her-key AI generation (weeks 3-6, every call a price card)
- **Meshy** (rows 22, 38): image/text → textured 3D + auto-rig + animation, in one vendor. Download within 3 days
  (non-Enterprise API output is deleted). Free plan allowed only with the CC BY credit written into the game credits.
- **Tripo** (rows 23, 39): the cheaper second engine ($0.10-0.30/model, rig $0.25), **paid plan only** (free = Tripo
  keeps all rights). Ask Holymolly in writing about BYOK-through-Hoola first.
- **Stability Fast 3D cloud** (row 27): ~$0.10 fast drafts.
- **ElevenLabs** (row 61): voice + SFX + music on Starter or above — the moat plan's own finding is that **AI voice and
  localisation correlate with success, AI art with flops**; this is the highest-value audio row.
- **Sketchfab Download API** (row 72) with her own Sketchfab login: CC models, licence + author carried into
  provenance and the game's credits; CC-BY-NC filtered out for anything she sells.
- *She gets:* real 3D characters and props, rigged and animated, with real voices — each one priced before it runs.

### Wave 3 — official vendor MCPs through Hoola's existing MCP client (weeks 6-9)
- **Scenario** (row 32, after its output-rights terms are read), **Crowdin / Lokalise** (rows 110-111), **Sentry /
  Bugsnag** (113-114), **Figma / Miro / Notion / Jira** (80-83), **Firebase** (103), **ElevenLabs hosted MCP** (61).
- Open question for the owner before this wave: these MCPs sign in with **OAuth to her own vendor account**. That is
  the vendors' documented route, not a consumer-subscription OAuth used in place of an API key — but the rule is hers
  to interpret. Where a vendor offers a key (Scenario, Crowdin PAT, Meshy), prefer the key.

### Wave 4 — Lane 4: meet the engines' own MCPs (weeks 9-12)
- Teach the v0.444 Unity package and Unreal plugin to **sit beside Unity MCP and Epic's Unreal MCP** rather than
  re-invent their tools: Hoola keeps the board, the checks, the Apply step and the fix rounds; the vendor MCP does the
  editor actions. Unreal MCP has **no auth layer** and binds localhost — never expose it. Add **Roblox Studio MCP**
  (row 4) for Roblox users and **Cinema 4D MCP** (row 17).
- Anything that would run through Hoola's Windows desktop app (Maya / Max / Substance / Aseprite on her PC) — **needs
  her OK (PC freeze)**; none is in this wave.

### Wave 5 — finishing and running (after Wave 2 proves real games)
- **Steam beta-branch upload** with her sealed build account (row 93; the default branch stays a human click in Steam by
  Valve's design), **Epic BPT** once its fee is verified, **Roblox Open Cloud place publish** (row 5).
- **Nakama** self-hosted as the Hoola-game backend (row 102), Photon only for Fusion / Quantum users.
- **TRELLIS on a rented GPU** (row 26) as Hoola's own free image→3D once its two submodule licences are read — the one
  route that removes per-model vendor cost entirely.

### Top 10 to connect first
1. **Poly Haven API** — CC0 HDRIs / PBR / models, free commercially, one credit line.
2. **Kenney packs (local)** — CC0 2D / 3D / audio kits on Hoola's disk, zero cost, zero wait.
3. **ambientCG (local)** — CC0 PBR materials, no credit needed.
4. **Meshy (her key)** — image→3D + rig + animation in one API; official MCP exists; download within 3 days.
5. **ElevenLabs (her key, Starter+)** — voice, SFX, music; the AI use that correlates with success.
6. **Tripo (her key, paid only)** — cheapest per-model 3D + auto-rig ($0.10-0.30, rig $0.25).
7. **Tiled / LDtk import** — the missing TileMap pipeline for platformers.
8. **Sketchfab Download API (her login)** — CC models with licence + author carried into provenance.
9. **Crowdin official MCP** — professional localisation on top of Hoola's own Indian-language pass.
10. **Sentry official MCP** — real crash streams from shipped builds, beside v0.432's Godot Logger.

---

## 5. Could not verify (do not quote these as fact)

| Item | Why not | What would settle it |
|---|---|---|
| Tripo / Holymolly: is BYOK through a platform "making the service available to a third party"? | Terms are silent on the BYOK case | A written answer from business@tripo3d.ai |
| Hyper3D Rodin terms + per-call price | Docs give no price; terms not read | hyper3d.ai terms + pricing page |
| CSM Cube terms and which plan includes the API | Only secondary | csm.ai terms / pricing |
| Scenario output rights | MCP page silent | scenario.com terms of service |
| Leonardo terms, free-tier commercial rights, full MCP page | leonardo.ai returned 403 | Read leonardo.ai/terms and docs.leonardo.ai MCP page from another network |
| Luma Genie 3D API status | No Luma page read | lumalabs.ai API docs / changelog |
| TRELLIS submodule licences (diffoctreerast, modified FlexiCubes) | Not read | Their LICENSE files |
| Stable Fast 3D API price | platform.stability.ai/pricing not loaded; figure from Stability's Aug 2025 price note via search | The live pricing page |
| Meshy $ per credit and which plan unlocks the API | Not on the pricing doc | meshy.ai/pricing |
| ElevenLabs game-music carve-out (from GAME_MOAT_PLAN) | Pricing page only says "Music commercial use" from Starter | ElevenLabs Terms / Music terms |
| Epic's UEFN MCP extension (20 Aug 2026) | Secondary only; Epic's 5.8 page is silent on UEFN | Epic UEFN docs |
| Houdini 22 Apex Script MCP | Analyst article only | SideFX Houdini 22 release notes |
| Unity's in-Editor MCP deprecation in favour of the CLI | One third-party guide; the 2.7 reference page shows no banner, unity.com/features/ai describes the CLI route | Latest com.unity.ai.assistant docs |
| Perforce p4mcp-server: official vs "community supported" | Sources disagree | perforce/p4mcp-server README support statement |
| Linear, GitHub official MCPs | Not re-read this session | linear.app / github.com docs |
| Cocos 4 MIT licence | Secondary; GitHub metadata "other" | github.com/cocos/cocos4 LICENSE |
| GameMaker prices and GMRT 2027 terms | Secondary | gamemaker.io pricing |
| Stride, O3DE, Krita, Inkscape, DragonBones, ArmorPaint, Pixelorama, glTF-Transform licences | Stated from memory; GitHub API blocked for non-session repos | Each project's LICENSE file |
| Aseprite server-use answer | Developers have not answered publicly | Written licence from Igara Studio |
| FMOD and Wwise current free-tier rules | fmod.com/licensing rendered empty; audiokinetic pricing 403 | Both vendors' licensing pages |
| Epic Games Store fee | Sources conflict ($100 vs free) | Epic Developer Portal terms |
| IARC process and any API | globalratings.com pages did not answer / 404 | globalratings.com "How IARC works" + storefront list |
| Photon paid prices | Pricing doc links out | photonengine.com Fusion / Realtime pricing pages |
| EOS current cost; UGS; GameLift; Backtrace; Unity VCS / Build Automation APIs | Not read | Each vendor's docs |
| Poly Haven: whether caching / mirroring API results is fine | API ToS silent on caching | Ask Poly Haven (assets are CC0, so mirroring the *files* is fine) |
| ambientCG API terms | Licence page covers assets only | docs.ambientcg.com API section |
| Freesound commercial licence price | Must be negotiated | Freesound contact form |
| Adobe connector: usable from Hoola's own MCP client (not Claude)? | Adobe documents it for Claude / Gemini | Adobe developer terms for the connector |

---

## 6. Findings that change or contradict `docs/GAME_MOAT_PLAN.md`

1. **Epic DOES ship an official MCP server.** GAME_MOAT_PLAN §6 says "Whether Epic ships an official MCP server in UE
   5.8 — two reports conflict … Epic's is not [confirmed]." Epic's own 5.8 documentation describes **Unreal MCP**, an
   Experimental plugin embedded in the editor (localhost, no auth, toolsets via AllToolsets). Confirmed first-party.
2. **Tripo's free tier is stricter than "non-commercial".** The terms say free users' outputs belong to Tripo ("Tripo
   retains all rights"); and the terms forbid making the service available to any third party and transferring API
   keys — which also constrains *paid* use through Hoola.
3. **Meshy's terms forbid the pooled-account model** ("solely for your internal use", no resale / redistribution, no
   shared account) and **delete non-Enterprise API output after 3 days**. GAME_MOAT_PLAN only had the CC BY free-tier
   point (now confirmed at source).
4. **Hunyuan3D terms now confirmed at source**, plus two clauses the moat doc lacked: outputs may not be used to
   improve other AI models, and a hosted service must name its real provider prominently.
5. **Photon's "free 100-CCU tier" is narrower than the moat doc says:** commercial 100 CCU is for **Fusion / Quantum
   only, one app per customer**; the Realtime free tier is **20 CCU, non-commercial**.
6. **Blender now has an official MCP server** (Blender Lab) — and it runs model code with no guard, so Hoola's own
   guarded `blender3d/` runner stays the right server path.
7. **Stability's Community licence does not cover Hoola self-hosting** — "API providers" are on the Enterprise tier.
8. **Unity's 30 Jun 2026 ToS**: AI/ML training on Unity data needs written authorisation; Asset Store content may never
   train AI. Unity says local MCP use stays allowed. (Not a contradiction — a new constraint.)
9. **PlayFab's free tier is now 1,000 lifetime players per title** (Foundation mode free only with an Xbox publishing
   agreement) — it should not be a default backend for Hoola games; Nakama (Apache-2.0, self-host) is.
10. **Freesound's API is non-commercial unless licensed** — a CC0 sound fetched through the API for a sold game still
    needs Freesound's commercial API permission.

---

## 7. Sources (all accessed 2026-11-11)

- S1 https://docs.meshy.ai/en/api/ai
- S2 https://www.meshy.ai/terms-of-use
- S3 https://docs.meshy.ai/en/api/pricing
- S4 https://developers.tripo3d.ai/ (redirect from platform.tripo3d.ai/docs)
- S5 https://developers.tripo3d.ai/en/terms
- S6 https://github.com/VAST-AI-Research/tripo-mcp
- S7 https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE
- S8 https://docs.hyper3d.ai/ (redirect from developer.hyper3d.ai)
- S9 https://help.scenario.com/articles/2664328768-getting-started-with-the-scenario-mcp-server
- S10 https://docs.scenario.com/get-started/mcp/mcp
- S11 https://docs.leonardo.ai/docs/connect-to-leonardoai-mcp (search excerpt only); https://www.leonardo.ai/api (403)
- S12 https://stability.ai/license
- S13 https://stability.ai/api-pricing-update-25 (via search excerpt)
- S14 https://github.com/microsoft/TRELLIS
- S15 https://docs.csm.ai
- S16 https://docs.kaedim3d.com/enterprise-features/custom-integrations/apis/web-api
- S17 https://deepmotion.com/animate-3d-api
- S18 https://developers.move.ai/docs
- S19 https://wwwimages2.adobe.com/content/dam/cc/en/legal/servicetou/Mixamo-Addl-Terms-en_US-20210623.pdf (search excerpt)
- S20 https://cascadeur.com/plans ; https://cascadeur.com/blog/general/cascadeurs-new-licensing-structure-comprehensive-faq (search excerpts)
- S21 https://esotericsoftware.com/spine-runtimes-license (search excerpt)
- S22 https://github.com/elevenlabs/elevenlabs-mcp
- S23 https://elevenlabs.io/pricing
- S24 https://elevenlabs.io/docs/overview/capabilities/sound-effects
- S25 https://www.digitalmusicnews.com/2026/07/03/suno-is-opening-an-api-partner-program/ (secondary)
- S26 https://apis.io/providers/udio/ (secondary)
- S27 https://freesound.org/docs/api/terms_of_use.html
- S28 https://polyhaven.com/license
- S29 https://github.com/Poly-Haven/Public-API/blob/master/ToS.md
- S30 https://docs.ambientcg.com/license/
- S31 https://kenney.nl/support
- S32 https://sketchfab.com/developers/download-api/guidelines
- S33 https://sketchfab.com/developers/terms (search excerpt)
- S34 https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab ; https://fab.com/terms-of-service (search excerpts)
- S35 https://unity.com/legal/as-terms ; https://support.unity.com/hc/en-us/articles/16455448218516-Can-I-use-assets-to-train-AI-models (search excerpts)
- S36 https://www.cgtrader.com/developers ; https://help.cgtrader.com/hc/en-us/articles/360015168418 (search excerpts)
- S37 https://docs.api.turbosquid.com/ (search excerpt)
- S38 https://unity.com/features/ai
- S39 https://docs.unity3d.com/Packages/com.unity.ai.assistant@2.7/manual/reference/unity-mcp-reference.html
- S40 https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor?application_version=5.8
- S41 https://create.roblox.com/docs/en-us/studio/mcp
- S42 https://create.roblox.com/docs/cloud/guides/usage-assets ; https://create.roblox.com/docs/cloud/open-cloud/usage-place-publishing (search excerpts)
- S43 https://godotengine.org/license/
- S44 https://www.blender.org/about/license/
- S45 https://www.blender.org/lab/mcp-server/
- S46 https://defold.com/license/
- S47 https://www.pocketgamer.biz/gamemaker-makes-gmrt-free-for-commercial-use-from-2027/ (secondary)
- S48 https://itsfoss.com/news/cocos-4-game-engine/ (secondary)
- S49 https://github.com/bevyengine/bevy
- S50 https://help.maxon.net/c4d/en-us/Content/html/MCPADAPTERPREFS.html ; https://digitalproduction.com/2026/10/01/cinema-4d-2026-4-mcp/ (search excerpts)
- S51 https://cgpress.org/archives/autodesk-releases-mcp-server-for-product-help-documentation.html (secondary)
- S52 https://www.jonpeddie.com/news/sidefx-and-nvidia-bring-mcp-powered-ai-agents-to-houdini-22s-rigging-workflow-at-siggraph-2026/ (secondary)
- S53 https://blog.adobe.com/en/publish/2026/04/28/adobe-for-creativity-connector ; https://blog.adobe.com/en/publish/2026/09/24/adobe-comes-to-gemini-expands-what-you-can-do-in-claude ; https://helpx.adobe.com/creative-cloud/apps/integration-with-other-apps/adobe-connectors/adobe-for-claude.html (search excerpts)
- S54 https://developer.adobe.com/firefly-services/docs/s3dapi ; https://helpx.adobe.com/substance-3d-sat.html (search excerpts)
- S55 https://github.com/mapeditor/tiled
- S56 https://github.com/deepnight/ldtk
- S57 https://github.com/RodZill4/material-maker
- S58 https://github.com/heroiclabs/nakama
- S59 https://github.com/game-ci/unity-builder
- S60 https://docs.unity.com/en-us/build-automation/manage-consumption-costs ; https://activation.unity3d.com/pricing (search excerpts)
- S61 https://partner.steamgames.com/steamdirect
- S62 https://partner.steamgames.com/doc/sdk/uploading
- S63 https://itch.io/docs/butler/login.html ; https://itch.io/docs/butler/pushing
- S64 https://forums.unrealengine.com/t/tutorial-how-to-upload-your-binaries-using-build-patch-tool/1858080 (secondary)
- S65 https://godotengine.org/article/about-official-console-ports/ (via GAME_MOAT_PLAN)
- S66 https://developer.microsoft.com/en-us/games/products/playfab/pricing/
- S67 https://firebase.google.com/docs/cli/mcp-server (search excerpt)
- S68 https://gameanalytics.com/pricing
- S69 https://doc.photonengine.com/photon/current/pricing
- S70 https://www.epicgames.com/help/ (EOS description, search excerpt)
- S71 https://support.crowdin.com/developer/crowdin-mcp-server/ (search excerpt)
- S72 https://lokalise.com/product/mcp-server/ ; https://docs.lokalise.com/en/articles/13547066-setting-up-and-using-the-lokalise-mcp-server (search excerpts)
- S73 https://docs.sentry.io/product/sentry-mcp (search excerpt)
- S74 https://developer.smartbear.com/smartbear-mcp (search excerpt)
- S75 https://developers.miro.com/docs/miro-mcp (search excerpt)
- S76 https://developers.notion.com/docs/get-started-with-mcp (search excerpt)
- S77 https://github.com/atlassian/atlassian-mcp-server (search excerpt)
- S78 https://www.perforce.com/press-releases/MCP-Enablement ; perforce/p4mcp-server releases (search excerpts)
- S79 https://www.globalratings.com/
- S80 https://unity.com/legal ; https://roboin.io/article/en/2026/07/02/unity-denies-concerns-over-ban-on-third-party-ai/ (secondary)
- S81 The Figma MCP server connected to this session describes itself as "The official Figma MCP server" (not a web page)
- S83 https://discussions.unity.com/t/unity-devops-updates-in-2026/1711090 (search excerpt)
- S84 https://www.fmod.com/licensing (rendered empty) ; https://www.gamasutra.com/audio/small-developers-and-creators-can-now-use-fmod-studio-for-free (secondary)
- S85 https://community.aseprite.org/t/what-is-aseprites-stance-on-commercial-server-side-usage-for-file-conversion/28691 (secondary)
- S86 https://blog.audiokinetic.com/free-wwise-indie-license (secondary); https://www.audiokinetic.com/en/wwise/pricing/ (403)
- Repo evidence (H rows): `server/app/gamedesk/assets.py`, `platforms.py`, `scene.py`, `liveops.py`, `sfx.py`,
  `server/app/blender3d/`, `server/app/bazar/connectors/mcp_remote.py`, `docs/GAME_MOAT_PLAN.md`, `docs/HOOLA_GAME_ENGINE_PLAN.md`
