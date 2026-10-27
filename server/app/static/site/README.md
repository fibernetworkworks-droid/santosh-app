# Hoola website on the Hoola server, with the Console button
- Owner: "make the entire website, the website will have a Console option, the user will click on it".
- `/` = home, `/employee`, `/network` (the three pages approved as Claude artifacts "Hoola" / "Hoola Employee" /
  "Hoola Network"), served from `server/app/static/site/{home,employee,network}.html` with `_SITE_CSP` (script-src 'self',
  no inline script: each page's script is its own file `{slug}.js`, GSAP 3.12.5 + ScrollTrigger self-hosted in
  `static/site/vendor/`; Google Fonts only), X-Frame-Options DENY. Sites Hoola launched for owners still win by hostname
  (`_hosted_sites` middleware runs first). The old one-page web chat that was at `/` is now `/chat`.
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
