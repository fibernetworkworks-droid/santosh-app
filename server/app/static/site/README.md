# Hoola website on the Hoola server, with the Console button
- Owner: "make the entire website, the website will have a Console option, the user will click on it".
- `/` = home, `/employee`, `/network`, `/studio` (the pages approved as Claude artifacts "Hoola" / "Hoola Employee" /
  "Hoola Network" + the Create Studio page v0.349), served from `server/app/static/site/{home,employee,network,studio}.html`
  with `_SITE_CSP` (script-src 'self', no inline script: each page's script is its own file `{slug}.js`, GSAP 3.12.5 +
  ScrollTrigger self-hosted in `static/site/vendor/`; Google Fonts only), X-Frame-Options DENY. Sites Hoola launched
  for owners still win by hostname (`_hosted_sites` middleware runs first). The old one-page web chat that was at `/`
  is now `/chat`.
- `/websites` and `/apps` (v0.739, the Web Development and App Development pages): the Web Studio (/console/web) and
  the App Studio (/console/apps) shown in drawn CSS scenes (no real screenshots yet); the console sidebar's
  "Web Development" / "App Development" rows open those same two studios. Each page deep-links its studio as a
  secondary CTA; the primary CTA still lands on /console/.
- Nav crowding (same change): adding Websites + Apps to every page's nav pushed the 1240px header row over on all
  pages but home (labels wrapped to two lines; network was already over before). Every page's nav is now compact
  (`.links` gap 14px — 10px on employee/network/studio — font 14px, home keeps 15px), long labels shortened
  ("Watch it work"->"Watch", "What's inside"->"Inside", "Three looks"->"Looks", "Price first"->"Price",
  "How it works"->"How", "All jobs"->"Jobs", "The knock"->"Knock", network's "Beyond" anchor dropped), and the nav
  hides below 1280px on every page (was 860/980/1060) - below that the cbtn + Get the app remain. Verified
  single-line at 1296/1440/1920 on all six pages.
- Console option everywhere: header button "Hoola Console" (`.cbtn`, "Console" on phones), a Console link in the menu, a
  Console button next to the last download button of each page, and on home a "Hoola on your computer" section (`#console`,
  just before `#get`) with a small console picture and "Open Hoola Console". The console login links back to `/`.
- Downloads: every download button is `/download` = 302 to the newest APK from `appupdate.latest()` (GitHub releases,
  cached 10 min; github.com only; GitHub unreachable -> the releases page). No version number is written in the pages.
- `static/site/site.css` = the shared Console styles (section classes prefixed `cx-` so page styles never clash) +
  `main{overflow-x:clip}` (slide-in animations wait off-screen until scrolled to; clip keeps sticky panels working).
- The files in `static/site/` are now the source: edit them directly (keep scripts out of the HTML; bump `?v=site<N>` when a file changes; a new page needs its own route + `_site_page`).
- Tests `server/tests/test_website.py`. The v0.142 console test now compares the version with `main.app.version`.

Add this as a CLAUDE.md section with the next version (left out of this change so it applies on any version).
