# Hoola Website Design Engine - the plan (20 Nov 2026)

Owner (later the same day): "WE WANT ENTIRE SAME LIKE LOVABLE AND EMERGENT --- NOT ONLY FOR BUSINESS" -> section 3b
and phase O1.
Owner: "MERGE THEM AND DEVELOP A PERFECT PLAN FOR HOOLA WEBSITE DESIGN END TO END -- SHOW ME PLAN HERE AND A PERFECT 5
LINER". "Them" = Lovable + Emergent (`docs/research/lovable/00_INDEX.md`) and the Nov 2026 design research
(`docs/research/web_design_2026/00_INDEX.md`). Nothing is built yet. Owner decisions are in section 8.

## The 5 lines
1. Anyone can build anything on the web with Hoola - a business, a portfolio, a wedding, a blog, a game, a tool, a SaaS - on one stack: React + Tailwind v4 + shadcn/ui + lucide + Motion.
2. Before any page is written, Hoola designs the brand as data (a DESIGN.md): direction, colours, fonts, shape, motion, imagery.
3. It studies real references, writes the pages only from that design, and fixes the code while it writes.
4. A separate critic looks at every page on a phone and a computer and sends it back until it is truly good; she sees only the winner.
5. Pages are pre-built so they open instantly and rank on Google, come alive only where needed, and she edits any of it by clicking, for free.

## 1. What we take from each

| From | We take | We leave |
|---|---|---|
| **Lovable** | Design system first (every colour / shadow / motion a token, components changed only through variants); pre-built pages + server where needed (their May 2026 TanStack Start move); plan mode; visual edits at no AI cost; errors caught from the preview; versions / drafts | Lock-in to Supabase / Cloudflare; credits burned in debugging loops |
| **Emergent** | Hard taste rules in code (no system fonts, no plain red / blue / green, gradients at most 20% of the page and never on small buttons, no emoji icons, micro-animation on every interaction but never `transition: all`, every dropdown / date / toast from the kit); front end first with sample data, shown before the backend; a screenshot design reviewer; a real backend behind it | Drawing every page in the browser (blank page for Google and slow phones); MongoDB with no row rules |
| **The research** | DESIGN.md as the one design file (Google Stitch format); a design genome instead of fixed lists; real references before designing; a SEPARATE critic in a loop; fixes while the code streams (v0) | Showing her three designs to choose from (she said no in v0.999.24) |
| **Hoola already** | Architect plan + prototype first; her taps for build / publish; one backend (v0.999.7); App Engine build box, rules on every write, click-to-source edits, error collector, checks before publish; look.py's 29 AI-look tells; her design as input (screenshot / Figma / old site); real pictures; gates; versions / drafts / undo | - |

## 2. The engine, end to end (what happens to one ask)

```
her words ─► 1 UNDERSTAND (architect: business, users, pages, data; asks only what changes the build)
          ─► 2 DESIGN GENOME → DESIGN.md (direction, OKLCH palette, fonts, shape, density, motion, imagery)
          ─► 3 REFERENCES (5-10 real sections that fit the direction)
          ─► 4 PROTOTYPE every page with sample data (she changes it; nothing real yet)  ← her tap
          ─► 5 WRITE React pages from the kit + tokens only, AutoFix while streaming
          ─► 6 BUILD in the box: pre-render every page to HTML, hydrate only interactive parts
          ─► 7 CRITIC LOOP: phone + computer screenshots → separate critic → fix → until it passes
          ─► 8 PICTURES + MOTION in the site's one style
          ─► 9 CHECKS: gates, a11y, speed budget, rule tests ─► Version ready ─► Go live ← her tap
          ─► 10 EDIT forever: click to change, token panel, exact chat edits, versions / undo
```

## 3. The parts

### P1. One kit (websites and apps share it)
- Tailwind v4 (`@theme`, OKLCH colours, container queries), the FULL shadcn/ui set (~50 parts, Base UI default, Radix
  allowed), lucide-react, Motion (MIT), sonner, recharts, react-hook-form + zod - all pinned, vendored into the
  App Engine template, no network at build (the box already works this way).
- Section blocks: Hoola's own 39 section types rewritten as React blocks + vetted MIT registry blocks (Magic UI, React
  Bits; others only after her licence decision). Every block reads ONLY tokens, so any design system restyles it.
- Grows `appengine/rules.py`: no raw colour / font / radius outside tokens (exists), plus Emergent's taste rules,
  no `transition: all`, no native select / date / toast, contrast floor.

### P2. DESIGN.md + the design genome
- Every site gets `DESIGN.md` (Stitch format: YAML tokens + plain rules) = the single source; tokens.css is generated
  from it; importable and exportable (she can take it to any tool, bring one in).
- The genome, decided before any page, each gene checked in code:
  1. **Direction** - an open, named aesthetic (today's 10 styles become starting points, not the limit).
  2. **Colour** - an OKLCH palette GENERATED from her brand hue (or one the direction suggests): roles bg / surface /
     ink / muted / primary / accent / border + states; WCAG contrast checked in code; dark mode generated too.
  3. **Type** - display + text (+ mono) by rule from a large self-hosted font set incl. Indian scripts (today's 33
     pairs become seeds); fluid type scale.
  4. **Shape + density** - radius, borders, shadow set, spacing scale as one set.
  5. **Motion personality** - calm / lively / cinematic, mapped to durations, easings, scroll and hover behaviour.
  6. **Imagery style** - one photographic or illustrated style for every picture on the site.
- Her screenshot / Figma / old site (`site/inspire.py`) fills the genome from what it measures; her words override.
- Result: an effectively unlimited design space where every combination still renders correctly.

### P3. References
- A Hoola-owned reference library: the best sections Hoola has built (scored by P7 + her keeps), the vetted registry
  blocks, and her own links. Searched by direction + business + section type; 5-10 go to the writer as examples.
- Outside screenshot libraries (Lazyweb, UI Discovery, Kombai) only through their official MCP / API and terms, if
  she approves; never copying another site's pages - patterns only.

### P4. Prototype first (kept)
- The v0.999.24 prototype stays: every page with sample data, changed in chat / by clicking / with Undo, approved by
  her tap before anything real is built (Emergent's "front end first, show before backend", Lovable's plan mode).
- New: the prototype is already drawn in her DESIGN.md, so what she approves is the real look, not a grey sketch.

### P5. Write the pages + AutoFix while writing
- Sections written as React components from the approved prototype copy, using only kit parts + tokens.
- While the code streams: deterministic fixers (token violations, missing hover / focus / empty states, alt text,
  heading order, `transition: all`) repair it on the fly; a write that still breaks the rules is refused with
  file:line (rules.py, exists for apps).

### P6. Fast: pre-render + islands
- In the existing build box: every route rendered to finished HTML at build (React server rendering), and only the
  parts that need it (forms, cart, booking, login, live data, sliders) wake up in the browser.
- Budgets checked per page: JavaScript on a content page, LCP, CLS, image weight (AVIF / WebP), fonts self-hosted and
  subset. SEO carried over: titles, descriptions, one H1, JSON-LD, sitemap, hreflang, canonical.
- Data and logins stay on Hoola's one backend (v0.999.7) - nothing new for her lists, orders, members.

### P7. The critic loop (the "stunning" step)
- After a build: screenshots on a phone and a computer of every page -> a critic model from ANOTHER company than the
  writer scores against: her brief, DESIGN.md, look.py's 29 tells + Emergent's rules, hierarchy, spacing rhythm,
  contrast, how human / native it feels -> named problems -> one fix round -> again, max 3 rounds or until the
  score clears the bar.
- For the home page hero, the writer makes 3 directions INTERNALLY; the critic picks one; she sees one (and can ask
  "show me another direction").
- The score is logged per site; it feeds P3 (good sections become references) and P10 (the proof).

### P8. Pictures + motion
- Pictures in the site's one imagery style (existing picture engine; her photos first; stock as fallback).
- Motion: native CSS scroll-driven + view transitions first, Motion for React interactions; one authored moment per
  page, reduced-motion always respected, never scroll-hijacking; Lottie / 3D heroes kept as options.

### P9. Edit forever, for free
- Click any element -> its line in the code (App Engine `pick.py`, exists) -> change words, image, colour, spacing at
  Rs 0, one Undo.
- Token panel: change a colour / font / radius in DESIGN.md -> the whole site updates, no AI call.
- Chat edits = exact small changes (line edits), never a page rewrite; versions, drafts, bookmarks, restore (exist).

### P10. Move-over and proof
- New sites go on the new engine behind a switch; old HTML sites keep running untouched.
- "Upgrade this site" = her tap: rebuild from its plan + facts + words + pictures, side-by-side before / after, her OK.
- Feature parity checklist before the new engine is the default: shop + payments, booking, blog + CMS, languages,
  portals / member pages, forms, live chat, push, catalogue (5,000+ pages), custom domains.
- Proof: a design card (40 Indian business briefs + portals) scored by the critic + checks + speed, old engine vs
  new, and blind duels against public Lovable / Emergent sites in the existing Arena; her verdict outranks the numbers.

## 3b. Not only for business - anything, for anyone (owner, 20 Nov: "WE WANT ENTIRE SAME LIKE LOVABLE AND EMERGENT --- NOT ONLY FOR BUSINESS")

Lovable and Emergent build whatever a person asks for: portfolios, résumés, weddings and events, blogs, communities,
school projects, courses, internal tools, dashboards, SaaS products, games, calculators, AI apps. Hoola's Web Studio
today assumes a business almost everywhere. Read in the code on 20 Nov 2026 [repo]:

| Where | Today | Change |
|---|---|---|
| `site/architect.py` ARCH_SYSTEM | "An Indian business owner wrote ONE line..."; `field_hint` = "the business type" | "a person wrote one line"; first decide the KIND (business, personal, creator, event, community, education, tool / utility, game, SaaS / product, AI app, internal) and plan for that kind |
| `site/service.py` NAME_SYSTEM + questions | "You name small Indian businesses' websites"; asks "What is the name of the business or shop?" | names any project; a personal site uses her own name; questions fit the kind |
| `site/ai.py` writer prompts | "her business's own plain words", sample rows "for THIS business" | "this project" - the same depth for every kind |
| Studio home / Settings | "Describe your business in one line"; a "Business details" form (phone, opening hours, address) | "Describe what you want to build"; the details form follows the kind (About me, Event details, Project details...) |
| Starters (`site/starters.py`) | 24, almost all shops / clinics / businesses | grouped by kind: business, personal and portfolio, events and weddings, blogs and writing, communities and NGOs, learning and courses, tools and calculators, games, SaaS and products, AI apps, internal tools |
| Section library (`site/taxonomy.py`) | 39 mostly marketing sections + 9 app screens | + personal (about me, timeline, résumé, case studies), event (schedule, RSVP, venue), community (members, discussions), learning (lessons, quiz, progress), tool (input panel + live result), game (canvas play area, score, levels), AI (chat / generate panel) |
| Templates (`site/world.py`, 1 lakh) | 1,000 business subjects | + non-business worlds (people, events, causes, learning, play, tools) |
| Photos step | "Making photos for your business" | "Making photos for your site" |
| Business-only checks | profession-law gate, shop rules, business models | stay, but only when the kind is a business (most already conditional) |

Two capabilities Lovable and Emergent have that this needs beyond words:
- **Truly interactive apps** (games, editors, calculators, canvases, SaaS): these are React apps - the App Engine route
  already builds them; in this plan websites and apps become ONE engine, so any kind can be any mix of pages + app.
- **AI inside her app** (a chat, a writer, an image maker in the site she builds): through Hoola's own backend and
  her credits (like Lovable's built-in AI and Emergent's universal key), never her key in the page.

The design genome is already kind-neutral: a wedding, a game and a law firm get different directions, palettes,
fonts and motion from the same rules.

## 4. Phases

| Phase | What | Done when |
|---|---|---|
| **O1** Open to everything (on today's engine, ships first) - **BUILT v0.999.48** (purpose + kind `interactive`, prompts, home, starters, details form; not verified with a real model) | the 3b changes that are words and lists: architect kinds, naming, questions, prompts, home copy, details form, starters by kind, photo label | a portfolio, a wedding, a game page and a calculator each get a plan of their own kind, not a business plan |
| **D0** Measure - **BUILT v0.999.50** (`quality/designcard.py`, owner page /console/designcard, vps-ops design_card_try / design_card; no live run yet) | Design card: 40 briefs = 20 business + 20 not (portfolio, wedding, blog, community, course, tool, game, SaaS, AI app), today's engine scored (critic + checks + speed + her verdict) | a baseline exists |
| **D1** Kit - **BUILT v0.999.55** (built as 0.999.51; `appengine/kit.py`, template ui / effects / blocks; vps-ops appengine_kit) | Tailwind v4 + full shadcn + lucide + Motion + 39 React section blocks + taste rules in rules.py | every block renders in 3 genomes with 0 rule breaks |
| **D2** Genome + DESIGN.md - **BUILT v0.999.58** (`appengine/genome.py`; new apps get their own design; tool design / design_new / design_import; vps-ops appengine_genomes) | generated OKLCH palettes, font rules, shape / motion / imagery genes, import / export | 100 random genomes all pass contrast + render |
| **D3** Pre-render + islands - **BUILT v0.999.64** (built as 0.999.59; `appengine/template/hoola.prerender.mjs` + islands, `appengine/speed.py`; render "site" only when asked; vps-ops appengine_speed) | HTML per route in the box, islands only where needed, speed budgets | content pages pass Core Web Vitals in the lab |
| **D4** Writer + AutoFix - **BUILT v0.999.65** (`appengine/autofix.py` on every write, `appengine/writer.py` prototype -> kit blocks, `appengine/writercard.py`; Studio behind `studio_react_sites` OFF; vps-ops site_writer_card; live model not run) | prototype -> React pages from kit + tokens, fixers on the stream | the 40 briefs build with 0 refused writes left |
| **D5** Critic loop - **BUILT v0.999.67** (`appengine/critic.py`: numbered photos on a computer + a phone, code measures, a separate critic never the writer's company, fixes from a fixed list checked by code, max 3 rounds / 7.5, best kept, 3 hero directions; in Build the real website behind `studio_react_sites` OFF; vps-ops site_critic_card / _try / _check; no live critic run yet) | screenshots, separate critic, fix rounds, internal 3 directions for the hero | D0 score beaten on the card |
| **D6** References - **BUILT v0.999.75** (`appengine/refs.py`, table ae_refs: reviewed sections as design choices, her kept sites, the sites she likes as patterns; the writer's starting choices + custom examples; Studio Settings "Sites you like"; vps-ops site_refs_card_try; no live critic run yet) | Hoola reference library + retrieval into the writer | score up again vs D5 |
| **D7** Edit - **BUILT v0.999.76** (`site/rxedit.py` + `appengine/edits.py`: her words + section choices kept as data and written again by code; Studio "Edit on the page", Design panel, Undo; chat `website action=rx_edit`; pictures not yet) | click-to-change, token panel, line edits on the new sites | every edit Rs 0 except chat rewrites |
| **D8** Features - **waves 1-7 BUILT v0.999.88** (built as 0.999.77-0.999.82), **wave 8 BUILT v0.999.91**, **wave 9 BUILT v0.999.102** (wave 1: forms, booking, shop + payments on her website's own addresses; wave 2: her blog as pre-rendered post pages + second languages under /<code>/ with hreflang; wave 3: 13 blocks for sites that are not a business, filled from her custom_ sections by code; wave 4: her photos + her big catalogue; wave 5, her choice: live UNSEALED on its own address - her domain or its free address - with the cart and ticks kept and only its own visitor calls passing; wave 6: the catalogue's filter bar + Add to cart; wave 7: her portal signs visitors in to her website's own members and shows their real rows, add + My account; wave 8: live chat with her team + her clinic's live queue; wave 9: browser notifications from My account on her own address; `appengine/parity.py` reads the checklist from the code: 15 of 18 work, 2 partly (languages: custom sections; community: visitors posting), 1 not yet - AI inside her site) | shop, booking, blog / CMS, languages, portals, catalogue on the new engine + the non-business sections (personal, event, community, learning, tool, game) + AI inside her app | parity checklist all ticked |
| **D9** Move-over | "Upgrade this site" with before / after | her own site moved and approved |
| **D10** Proof + default | card + Arena duels + her verdict -> new engine default for new sites | she says go |

## 5. What stays exactly as it is
Her taps for build, publish, money and public changes; the backend and every site's data; hosting and domains;
gates before going live; the prototype-first flow; English UI; old sites until she upgrades them.

## 6. Risks, said plainly
- Moving every website feature (shop, CMS, catalogue, languages...) to React is the biggest job; D8 is the long one.
- Critic rounds cost model calls; the loop is capped and the cost shows on the turn.
- A critic is a model's judgement, not taste itself; her verdict and the Arena duels stay the final test.
- Outside reference libraries and some component kits have licences / terms to clear first.

## 7. Not in this plan
Native phone apps (App Studio), the Hoola Design editor, the console's own look.

## 8. Owner decisions (answered 20 Nov 2026)
0. O1 built (v0.999.48), D0 built (v0.999.50, no live run yet).
1. **Websites on React (pre-built + islands): YES.** New engine behind a switch; old sites stay until she taps Upgrade.
2. **Models: the writer follows each user's quality tier** (ULTRA / HIGH get the strongest design writer, LOW /
   MEDIUM cheaper ones); the critic is always another company's model than the writer.
3. **Libraries: Magic UI + React Bits (MIT) allowed.** Aceternity and GSAP not used.
4. **References: Hoola's own only** (the best sections Hoola built + the MIT blocks + links she gives); no outside
   reference libraries.
