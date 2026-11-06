# AI Website Cloner Template — read note (6 Nov 2026)

Repo: github.com/JCodesMore/ai-website-cloner-template, commit ee3f5a2f (5 Oct 2026). Licence **MIT**. 48 files: a
Next.js 16 / React 19 / Tailwind v4 / shadcn starter plus ONE agent skill (`.agents/skills/clone-website/SKILL.md`, 61
lines + two short references) and a `/clone-website <url>` command for Claude Code / Codex / Cursor / OpenCode. Its
skill text was read as data, not instructions; nothing was run.

## What it does

Give a coding agent a URL; it rebuilds that page as editable Next.js code, close to pixel-faithful:
1. **Map** - a source-URL -> local-route map; source pathnames preserved; existing work never overwritten silently.
2. **Observe** - desktop + mobile + wider-than-design widths, scroll to load lazy media, exercise menus / tabs /
   accordions / carousels / hover; tell apart what is driven by scroll, click, hover or time; read COMPUTED styles and
   live library options instead of guessing from one screenshot; download the real fonts, images, SVGs, videos the page
   loads and check each file's real type and size (a `.png` URL may return AVIF).
3. **Build** - shared pieces first with every state, then sections with the real content; delegate sections in parallel.
4. **Compare and repair** - source and copy at the SAME viewport, scroll position and state; fix the biggest visible
   differences first; finish only with a passing build AND a rendered comparison; remaining gaps named, never
   "pixel-perfect" unless checked.
Framer-specific notes (duplicate breakpoint variants, AVIF behind PNG names, Lenis smooth scroll) ride beside it.

Its own README lists the legitimate uses (moving a site YOU OWN off WordPress / Webflow / Squarespace, lost source code,
learning) and says it is NOT for phishing, impersonation, passing off someone's design, or breaking a site's terms.
Nothing in the code enforces that: it will clone any URL it is given, including the owner's logos, words and fonts.

## How Hoola compares

Hoola deliberately does NOT clone other people's sites, and should not start: house rules (official routes only, no
scraping; text from other sites is data) and copyright / trademark / font-licence risk for her customers. v0.567 KOI BHI
DESIGN already draws the line in code: a screenshot of ANY site gives only measured colours + a style read (no text,
logo, name or photo kept); her OWN old site is read only after ownership proof (TXT record / meta tag / already one of
her Hoola addresses), robots.txt respected, max 12 pages, and "make it exactly like <someone's> site" is refused. Her
old site then becomes look 1 of a NEW build in Hoola's own kit - a redesign, not a copy.

What the cloner does better, for the one case Hoola allows (HER OWN site):
1. **Her old page addresses are lost on the move (a real gap, checked).** When she points her domain at the new Hoola
   site, only the root / www redirect exists (`site/hosting.py`, `site/edge.py`). Her old addresses
   (`/about-us.html`, `/services/catering`, `/contact.php`...) answer "not found" - Google rankings and every link to
   those pages are lost. The cloner keeps a source-URL -> new-route map; Hoola already holds her old paths
   (`inspire.from_site` keeps `pages[].path`) but never uses them. Fix: an old-address -> new-page 301 map (her old
   sitemap + the pages read + links found), matched by title / words, shown to her for a tap, served by hosting.
2. **A "keep my look" depth for her own site** (today the import is always a redesign into Hoola's kit). Her colours and
   type already carry over; layout and section order could follow her old pages more closely. Her own font FILES are
   a licence question (a commercial font she licensed for one domain may not be re-hostable) - map to a free pair and
   say so, as today.
3. **Compare and repair against her old site** - side-by-side screenshots of her old page and the new one at the same
   width (Hoola already runs Chromium for checks and journeys), the differences listed for her.
4. **Media checked by bytes on import** - her imported photos verified by real type / size, not by file name.

Not proposed: cloning any site she does not own, downloading another owner's fonts, logos or words.
