# The Hoola website (v0.999.29 HOOLA WEBSITE)
- Owner: the old site "LOOKS AI MADE AND NON PROFESSIONAL" -> a new site in the console's own design, with motion drawn in code
  and a showcase of every tool -> preview of every page (claude.ai artifact "Hoola Website") -> "GO".
- Pages (each its own route + `_site_page(slug)` in `server/app/main.py`): `/` home, `/employee`, `/tools`, `/studio`
  (the real Create Studio screens in `studio/*.webp`), `/websites` (Web Studio + App Studio; `/apps` 301s to `/websites#app-studio`),
  `/code`, `/computer`, `/network`, `/pricing`. Sites Hoola launched for owners still win by hostname (`_hosted_sites`).
- One stylesheet `site.css` (the console tokens, light + dark, Literata / Schibsted Grotesk / JetBrains Mono, Google Fonts only)
  and one script `site.js` (no library, no inline script - `_SITE_CSP` is `script-src 'self'`). Each moving scene finds its own
  `data-*` element, plays only while on screen, and holds a complete still frame under prefers-reduced-motion. The words are in
  the HTML; the script only moves and switches them, so the page reads fully without it.
- Prices on `/pricing` are `server/app/credits/plans.py`; `test_website.py` fails if they drift. Bump `?v=site<N>` when
  site.css or site.js changes.
- The pages were generated once from shared parts; the HTML files are now the source. Keep the header, footer and icon sprite
  the same on every page when you edit one.
- Downloads: every download button is `/download` (302 to the newest APK). Console: header button, menu and closing call to
  action on every page go to `/console/`; tool cards open their console studio.
- Tests: `server/tests/test_website.py`, `test_v0351_studio_page.py`, `test_v0462_logo.py` (icons on every page).
