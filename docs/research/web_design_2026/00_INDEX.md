# AI website design, the state of the art (research, 20 Nov 2026)

Owner, 20 Nov 2026: "React + Tailwind CSS + shadcn/ui (built on Radix) + lucide-react icons --- SAME FOR HOOLA WEBSITE
--- FIRST EVEN FIND A LATEST ADVANCEMENT IN AI WEB UI / UX --- THAT WILL DESIGN IT STUNNING AND USER HUMAN NATIVE
PERFECT BASED ON USER PROMPT --- DESIGN IS SOUL OF WEBSITE --- DO DEEP RESEARCH AND FIND THE ADVANCE, FAST, ALL
INFINITE DESIGN POSSIBILITIES ETC FIRST".

This file is research only. Nothing has been built. It sits beside `docs/research/lovable/00_INDEX.md` (Lovable read
end to end) and `docs/research/impeccable/00_READ.md` (the anti-AI-look skill Hoola's `site/look.py` came from).

How sure each line is:
- **[official]** the vendor's own page or changelog.
- **[paper]** an arXiv / ACM paper.
- **[3rd]** blogs, reviews, aggregators - directional only, several disagree on dates and numbers.
- **[leak]** a community copy of a system prompt - unofficial, may be outdated.
- **[repo]** Hoola's own code or research files.

---

## 1. The one-line answer

Every serious AI site builder in Nov 2026 designs the same way, and none of them leaves the look to chance:

1. **One fixed stack** - React + Tailwind + shadcn/ui + lucide icons (Lovable, Emergent, v0, Figma Make's code).
2. **The design system is written FIRST, as data** - colours, fonts, spacing, corners, shadows, motion as named
   tokens; components get their look only from those tokens and from variants. The page is written last.
3. **A committed direction + a list of banned "AI looks"** - pick one aesthetic on purpose, refuse the defaults.
4. **Real references, not imagination** - the model is shown real, good designs (screenshot libraries, a site she
   points at, a DESIGN.md of a known brand) before it designs.
5. **It looks at its own work and fixes it** - render, screenshot, a separate critic model, fix, repeat.
6. **Small exact edits after that** - point and click, change a token, never rewrite the page.

"Stunning" comes from 2 + 3 + 4 + 5 together. The component library (shadcn) only makes it consistent and fast; on
its own it gives the familiar "every AI site looks the same" result, which every source below complains about.

## 2. What each leading tool actually does

| Tool | Front end | How it gets a good look | Source |
|---|---|---|---|
| **Lovable** | React + Vite + Tailwind + shadcn (Radix) + lucide; since May 2026 TanStack Start + Tailwind v4 | "Design system first": every colour / gradient / shadow a semantic HSL token in `index.css`, no `text-white` in components, shadcn changed only through `cva` variants (`hero`, `premium`); first message = feeling -> tokens -> variants -> real images; Visual Edits (no AI, Rs 0); Plan mode; browser testing for visual bugs | [repo] lovable research, [official] [3rd] |
| **Emergent** | React (CRA + craco) + Tailwind 3.4 + ~50 shadcn components + Radix + lucide + sonner; FastAPI + MongoDB; Expo for phones | Rules in the prompt: no system fonts, no plain red/blue/green, no purple-blue default, gradients on at most 20% of the page and never on small buttons, no emoji icons, micro-animation on every interaction but never `transition: all`; front end first with mock data, shown before any backend; a screenshot "design reviewer" | [leak] Oct 2025, [3rd] |
| **v0 (Vercel)** | Next.js + shadcn | A "composite model": a frontier model + retrieval + a quick-edit model + **AutoFix** that checks the code WHILE it streams and repairs it mid-stream, then a final pass. Vercel reported 94% error-free generations vs 65% for a plain model (their own test) | [official] |
| **Google Stitch** | Gemini; exports HTML / Figma / code | Extracts a design system from any URL; exports **DESIGN.md** (tokens in YAML + the reasons in words), now an open draft spec with a linter (`npx @google/design.md lint`) and an MCP server | [official] |
| **Claude Design** (Anthropic, Apr 2026) | Canvas + code | Expert-designer framing; avoids the default "AI look"; community reconstructions describe a "four directions" step (show four different directions before committing) and a slop check | [3rd] [leak-ish] |
| **Figma Make** | Code from Figma | Builds generic code unless given "Make kits" (her components + tokens + guidelines); reviewers say reference-based prompting is far better than prompt-only | [3rd] |

## 3. The advances that matter, ranked by how much they lift the design

### A. Design system first (the biggest single lever)
- Everything visual is a token: colour roles (background, surface, ink, muted, primary, accent, border...), type
  scale, spacing scale, corner radius, shadow set, motion durations / easings.
- **DESIGN.md** (Google Stitch, open draft spec) is becoming the shared file for this: YAML tokens + plain-language
  rules ("buttons are pill-shaped, never more than one accent per screen"). The community `awesome-design-md` repo
  has ~70 DESIGN.md files extracted from known sites (Stripe, Linear, Vercel, Notion...) - [3rd]; these are
  third-party extractions, not the brands' own.
- **shadcn/cli v4 (Mar 2026)**: a *preset* = one short code that holds the whole design system (colours, theme,
  icon set, fonts, radius); `registry:base` ships a whole design system as one payload, `registry:font` ships fonts;
  `--dry-run / --diff` before anything is written. Since ~Jul 2026 new projects use **Base UI** under shadcn by
  default; Radix is opt-in and not deprecated - [official].
- **Tailwind v4**: tokens live in CSS (`@theme`), colours are **OKLCH** (perceptually even - you can generate a
  whole palette from one hue and keep contrast predictable), container queries built in; targets Safari 16.4+,
  Chrome 111+, Firefox 128+ - [3rd, consistent across sources].

### B. A committed direction + banned defaults
- Anthropic's own frontend guidance names the generic choices to avoid (Inter / Roboto / Arial / system fonts...);
  community reconstructions add the 2026 model default "cream background, serif display, terracotta accent" as a
  new slop look to catch - [3rd].
- Practitioners agree: pick ONE named aesthetic first ("editorial calm", "brutalist", "warm craft"...), then
  build; a prompt alone does not fix it - [3rd].
- Hoola already has this half: `site/look.py` = 29 AI-look tells (warn only), built from Impeccable [repo].

### C. Real references before designing
- Screenshot libraries built for agents: UI Discovery (~111k sections with palette + fonts, MCP), Lazyweb (281k app
  screens, MCP), Kombai Gallery (20k curated designs + prompts), Nicelydone MCP - [3rd].
- Figma Make users: reference-based generation is "substantially" better than prompt-only - [3rd].
- Caveat repeated everywhere: references raise the floor, they do not give taste or brand fit on their own.
- Hoola already reads her screenshot / Figma / own old site (`site/inspire.py`) [repo] - but has no reference
  LIBRARY of good designs to pull from when she gives nothing.

### D. Look at the result and fix it (critic in the loop)
- "Vision-Guided Iterative Refinement for Frontend Code Generation" (arXiv 2604.05839, 2026): a vision model
  critiques the rendered page; the best result came after one or more critique rounds in **86%** of tasks; cost
  rises with each round - [paper].
- A **separate** evaluator beats the generator judging itself - [3rd, practitioner].
- DesignTaste (arXiv 2611.16442) benchmarks generated visual design against award-winning work (ADC 2026, 100 Beste
  Plakate) - images not web pages, but it is the first "taste" benchmark - [paper].
- v0's AutoFix shows the cheap half of this: deterministic + model fixers on the code stream - [official].
- Hoola has a browser check + an Opus critique pass + look.py; what is missing is a *design* score that decides
  "go round again", and the round itself.

### E. Show several directions, then commit
- Claude Design (reported) and Hoola's own old "3 looks" did this; Hoola replaced the 3 looks with one prototype in
  v0.999.24 at the owner's request ("DONT SHOW THE 3 DESIGNS") [repo]. A middle path the research supports: make
  several directions *internally*, let the critic pick, show her one.

### F. The model is a lever
- Design Arena (human votes, official board updated 19 Nov 2026, full-stack): **Claude Fable 5.2 1402, Claude Opus
  5.5 1383** at the top; third-party copies of the website board put Meta Muse Wonder first (~1367) - [official]
  [3rd]. Hoola's Web Studio runs on Qwen 3.8 27B since v0.984 (and the tier rows since v0.999.21) [repo]. Model
  choice is the owner's decision; it is named here because it matters as much as the stack.

### G. Real pictures
- Text-in-image is solved at the top; GPT Image 2 and Nano Banana Pro follow layout best; Flux (open weights + LoRA)
  is the route to a brand-consistent series - [3rd]. Hoola already makes pictures for sites (`site/pictures.py`).

### H. Motion that feels native, not "AI"
- Native CSS now covers most of it: **scroll-driven animations** and **view transitions** (same-page is Baseline;
  cross-page view transitions still Chrome + Safari only) - [3rd, sources disagree on exact support, check MDN].
- **Motion** (motion.dev, MIT): React layout / exit animations, springs, scroll; small with tree-shaking.
  **GSAP** is now free but not open-source-licensed - [official] [3rd].
- Rule every source repeats: purposeful motion only, respect reduced-motion, never hijack the scroll, INP counts.

## 4. The component ecosystem on top of shadcn (the "infinite pieces")
All of these install through the same shadcn registry format into one `components/` folder - [3rd]:
- **Magic UI** (MIT, ~150-250 animated components and effects), **Aceternity UI** (cinematic hero / section blocks,
  freemium), **React Bits** (interactive effects), **Shadcnblocks / Tailark** (whole page sections),
  **21st.dev** (12,000+ community components + themes; Hoola already has a `magic21` tool since v0.512 [repo]).
- Advice repeated in the sources: shadcn as the base, at most ONE motion library on top.

## 5. Speed: React for a website without a slow website
- For content sites (most of what Hoola's users ask for), **Astro + React islands** ships near-zero JavaScript and
  hydrates only the interactive parts; Next.js can match it only with careful tuning - [3rd consensus].
- One field-data claim (HTTP Archive, Sep 2026): 71% of Astro origins pass all Core Web Vitals on mobile vs 36% of
  Next.js origins - [3rd, unverified, correlational].
- shadcn / Tailwind / Motion all work inside Astro islands. So "React + Tailwind + shadcn + lucide" does NOT force
  a heavy single-page app: the same components can render to plain HTML at build time and wake up only where a page
  needs interaction.

## 6. "Infinite design possibilities" - how the best tools get variety without randomness
Not a bigger list of templates. A **design genome** of independent choices, each generated or chosen by rules, then
checked:

| Gene | Today in Hoola Web Studio [repo] | What the leaders do |
|---|---|---|
| Aesthetic direction | 10 styles | open vocabulary, named on purpose, refs per direction |
| Colour | 50 fixed palettes | OKLCH palette GENERATED from one brand hue + contrast rules (any brand colour works) |
| Type | 33 bundled font pairs | any public font pair by rule (display + text + mono), `registry:font` |
| Shape | radius token | radius + border + shadow + density as a set |
| Layout | 39 section types, 24 heroes | thousands of real section blocks (registries) + AI-written custom sections |
| Motion | 60 presets + Lottie + 5 three.js scenes | native CSS scroll / view transitions + Motion, one "motion personality" per site |
| Imagery | generated / Pexels / hers | generated in one consistent style per site |

Multiply 7 independent genes with generated colour and open fonts and the space is effectively unlimited - and
because every gene is a TOKEN or a REGISTRY block, any combination still renders correctly and stays editable.

## 7. Where Hoola stands against this (honest)

Already there: a design kit per site (`site/kit.py`), an AI-look check (`look.py`), her design as input
(`inspire.py`), plan-first + prototype-first (v0.709 / v0.999.24), visual edits without AI (v0.295), a browser check,
an Opus critique, Lucide icons, real pictures, motion presets, Lottie + 3D heroes, a React App Engine that already
uses Tailwind v4 + Radix/cva + lucide + tokens-only (v0.824) [repo].

The real gaps:
1. **Two systems.** Websites are plain HTML on Hoola's own CSS; React apps are Tailwind + shadcn-style. A site and
   its portal do not share one design system, and the website's "React export" is only a wrapper [repo].
2. **Closed lists instead of a genome.** 50 palettes / 33 font pairs / 10 styles: good, but finite; the leaders
   generate colour from a hue and pick fonts by rule.
3. **No reference library** when she gives nothing to copy.
4. **No design score that drives another round** - checks warn, they do not loop.
5. **No DESIGN.md** - the site's design system is not a file she or another tool can read, import or export.
6. **Small component kit** in the App Engine (9 parts vs ~50 in Lovable / Emergent; none of the animated
   registries).
7. **Model**: Web Studio on Qwen 3.8 27B vs the design leaders on Claude Fable 5.2 / Opus 5.5 (her decision).

## 8. What a plan would build (direction only - nothing decided)
One design engine for websites AND apps:
- **Stack**: React + Tailwind v4 (OKLCH, `@theme`) + shadcn/ui (full set, Base UI default, Radix allowed) +
  lucide-react + Motion; websites rendered static with React islands (Astro or Vite SSG) so they stay fast; apps
  stay on the App Engine. One component kit for both.
- **DESIGN.md per site** = the single source of tokens + rules (Stitch format), importable / exportable.
- **Design genome** step before any page: direction -> generated OKLCH palette from the brand hue -> font pair by rule
  -> shape / density -> motion personality -> imagery style; each with contrast / readability checks in code.
- **Reference step**: pull 5-10 real, good sections that fit the direction (from her links, the shadcn ecosystem
  blocks, a curated library) before writing.
- **Critic loop**: render -> screenshot (phone + computer) -> a SEPARATE critic scores against the brief + DESIGN.md +
  look.py tells -> fix -> repeat until the score clears or 2-3 rounds pass; she sees only the winner.
- **AutoFix while writing**: deterministic checks on the code as it streams (banned colours outside tokens, missing
  states, `transition: all`, contrast).
- Keep: prototype-first, her taps for building / publishing, visual edits at Rs 0.

Owner decisions this needs (not answered yet):
1. Websites on React (static + islands) instead of today's HTML engine - yes / no, and what happens to existing sites
   (keep them as they are, or move them).
2. Which model writes and which critiques web design (today Qwen 3.8 27B).
3. Which outside component / motion libraries Hoola may ship (Magic UI MIT, React Bits, Aceternity freemium, GSAP's
   licence).

---

## Sources
- Lovable: `docs/research/lovable/00_INDEX.md`; https://lovable.dev/guides/emergent-vs-lovable ;
  https://lovable.dev/blog/visual-edits ; https://muz.li/blog/lovable-for-designers-the-complete-guide-to-building-apps-with-ai-2026/
- Emergent: https://emergent.sh/enterprise ; https://help.emergent.sh/mobile-app-development ;
  https://github.com/EliFuzz/awesome-system-prompts/blob/main/leaks/emergent/2025-10-15_prompt.md (unofficial)
- v0: https://vercel.com/blog/v0-composite-model-family ; https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent ;
  https://arxiv.org/pdf/2411.01606 (DesignRepair)
- Stitch / DESIGN.md: https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-design-md/ ;
  https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/ ;
  https://www.mindstudio.ai/blog/awesome-design-md-github-claude-code-brand-systems
- Claude Design / anti-slop: https://www.theadpharm.com/insights/claude-design-without-the-ai-slop-look ;
  https://github.com/Trystan-SA/claude-design-system-prompt ; https://www.mindstudio.ai/blog/claude-design-avoid-ai-slop-design-system
- Figma Make: https://www.figma.com/solutions/design-to-code/ ; https://aitoolsatlas.ai/tools/figma-make/review
- Tool comparisons: https://mowgli.ai/blog/figma-make-vs-stitch-vs-claude-design-vs-v0-vs-lovable ;
  https://dev.to/hadil/top-5-ai-ui-design-tools-in-2026-i-tested-them-all-with-the-same-prompt-hm7
- shadcn: https://ui.shadcn.com/docs/changelog/2026-03-cli-v4 ; https://ui.shadcn.com/docs/changelog ;
  https://blog.openreplay.com/shadcn-ui-radix-base-ui-switch/ ; https://shadcnstudio.com/blog/shadcn-cli-v4-registry-base-and-registry-font/
- Ecosystem: https://21st.dev/blog/shadcn-compatible-component-libraries ; https://adminlte.io/blog/shadcn-ui-block-libraries/
- Critic loop / taste: https://arxiv.org/html/2604.05839v1 ; https://arxiv.org/abs/2611.16442v1 ;
  https://dl.acm.org/doi/10.1145/3772318.3791567 ; https://www.maheshblog.in/blog/dev/2026-04-12-improving-ui-design-with-a-generator-evaluator-loop/
- References: https://webiano.digital/ui-discovery-turned-111083-screenshots-into-something-an-ai-agent-can-build-from/ ;
  https://app.lazyweb.com/ ; https://www.producthunt.com/p/kombai/kombai-gallery ;
  https://www.candede.com/articles/escaping-ai-slop-in-web-design
- Model board: https://www.designarena.ai/leaderboard/fullstack ; https://benchlm.ai/benchmarks/designarenawebsite
- Tailwind v4: https://noqta.tn/en/tutorials/tailwind-css-v4-complete-guide-2026 ; https://infoq.com/news/2026/04/tailwind-css-4-2-webpack
- Motion: https://motion.dev/docs/gsap-vs-motion ; https://motion.dev/docs/feature-comparison ;
  https://motionkit.io/blog/web-animation-trends-2026 ; https://mintec.co/blog/scroll-driven-view-transitions-css-2026/
- Speed: https://www.cosmicjs.com/blog/astro-vs-nextjs-2026 ; https://webyansh.com/post/astro-vs-next-js
- Images: https://www.atlascloud.ai/blog/guides/2026-ai-image-api-benchmark-gpt-image-2-vs-nano-banana-2-pro-vs-seedream-5-0 ;
  https://wavespeed.ai/blog/posts/seedream-5-0-vs-nano-banana-pro-gpt-image-flux-klein-qwen-image-comparison-2026
