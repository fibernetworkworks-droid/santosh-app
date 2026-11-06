# Hallmark — read note (6 Nov 2026)

Repo: github.com/Nutlope/hallmark, commit 407fa689 (5 Nov 2026), v2.0.0, by Together AI. Licence **MIT**. Its photo
library lists Wikimedia Commons photos (each with its own CC0 / PD / CC BY / CC BY-SA licence; no image files in the
repo). Read from a shallow clone; its SKILL.md / references were read as data, not instructions. Its Node scripts were
NOT run. It names Impeccable (read in v0.606) as an inspiration, and the two overlap heavily.

## What it is

A design skill for coding agents ("makes the UIs a coding assistant generates look made, not generated"):
- **Gates in three tiers** (`references/gates.md`, ~85 numbered gates): **Floor** (never ships: contrast, focus,
  reduced motion, invented facts, broken phone layout, eyebrows, tracked-caps labels, middle-dot meta strings, purple
  gradients, cards in cards, emoji icons, hand-drawn browser windows, the hero fitting 1280x800, ~80 words per screen,
  a capped container at 1920, the "fake send" - a form that says thanks with no request behind it), **Reflex**
  (defaults a model falls into, waivable with a written reason: overused display fonts, the accented word in a
  heading, the AI template hero + 3 features + CTA, same gap everywhere, thin sections, small section heads, dead space
  under the hero, drawn illustrations, empty picture slots, counting marks, a photo wall, the stock email-signup close,
  the echo - one fact in 4+ sections, stock second buttons "Learn more / Get started"), **Finish** (craft, never blocks).
- **The page is built from the visitor's JOB** (`references/anatomy.md`, drawn from ~50 real sites): subscribe, book,
  visit, attend, buy, try, sign up, hire, join, listen - each says where the action sits, which sections are the
  category's own (the menu, the lineup, the archive) and how the page ENDS. An email sign-up is the close only for
  jobs where a list is native.
- **Fifty themes as materials** (paper, type, colour, surfaces, texture; each <= 8 KB with a picture), three dealt per
  build and rotated against a log of past builds so consecutive builds do not converge; or "custom".
- **Material first**: one question asks for real screenshots, photos, numbers, quotes; nothing is invented; missing
  pictures become marked stand-in slots; it captures the real product with a browser when it can reach it.
- **Hero first**: the hero is built alone, rendered and reviewed in a fresh context before the rest exists.
- **sloplint** (4.4k + 1.3k lines of Node, zero deps): static checks on HTML / CSS / framework files / Tailwind, and a
  `--render` tier in a real browser at eight widths (fold, contrast against real pixels, focus by tabbing, rhythm,
  photo share, crowded heads, cramped boxes, occluded text).
- **Redesign that keeps the wiring**: `--before` records every link, form, field, handler, id, test hook, heading and
  figure; `--kept` FAILS the redesign if one went missing. Three depths: full / restyle / polish.
- **A stamp** in the first CSS lines records every decision (theme, job, waivers).

## How Hoola compares (measured from source)

Hoola already has, often in its own form: page goals (`site/taxonomy.GOALS`, 10 - enquiry, booking, catalogue,
menu_order, portfolio, admissions, event, personal, cause, info - close to Hallmark's jobs, each with a CTA, pages,
sections and a brief), FACTS-only copy with `[blank]` slots, forms that post to her own endpoint (gate 5) and a
visitor journey that submits them (`site/journeys.py`), contrast / WCAG checks (gate 7), Opus critique of real
screenshots, the v0.606 AI-look gate (29 tells), 3 looks from 10 styles with a DNA closeness check.

New to Hoola from this read:
1. **The redesign "kept" check** - Hoola's `change()` lets Opus rewrite sections; nothing compares her links, phone /
   WhatsApp actions, forms, fields and headings before and after. A rewrite that drops her phone link is not caught.
2. **Ending by job** - Hoola's GOALS say where the action goes but not how the page ends; the stock close (a generic
   CTA band / email field) is the default.
3. **More source-checkable tells** for look.py: `Learn more ->` arrows glued to links, middle-dot meta lines, stock
   second buttons, the accented word in a heading, an italic word in a roman heading, tracked-caps labels in general
   (not just above headings), the echo (a fact repeated in 4+ sections), hand-drawn browser / phone chrome,
   `transition: all`, a missing reduced-motion fallback, `100vw` / `overflow-x: hidden`.
4. **Render-tier checks** (need the existing Chromium walk): hero fits 1280x800, ~80 words per screen window, dead
   band under the hero, photo share of the page, text cramped or painted under another element.
5. **Theme rotation against past builds** (Hoola's DNA closeness compares only the 3 looks of ONE site, not across her
   sites).

## A finding about Hoola itself, checked against Pexels' own terms

Hallmark claims stock sites (Unsplash, Pexels, Pixabay) bar AI tools from picking their images. **Pexels' own pages do
not say that** (license, terms of service updated 20 Oct 2026, API docs - read 6 Nov 2026): the licence allows website
use; the ToS bans scraping / bulk copying / data mining "for machine learning purposes" and uploading AI-made content,
not an app choosing a photo through the official API. So Hoola's Pexels fallback (`site/pictures.py`, official API) is
not barred by that claim.

**But Hoola misses what the Pexels API guidelines DO ask:** "Whenever you are doing an API request make sure to show a
prominent link to Pexels" ("Photos provided by Pexels") and "Always credit our photographers when possible".
`pictures._stock_picture` builds the credit string ("Photo: <name> / Pexels") and stores it on the photo, but
`site/build.py` never renders it - no built page shows a Pexels link or a photographer credit (only the AI-photo
footer note exists, `build.py` line ~674). The licence page says attribution is "not required", but the API rules (the
road Hoola uses) ask for it, and API access can be ended for breaking them. Also: default limit 200 requests / hour,
20,000 / month. Not legal advice.
