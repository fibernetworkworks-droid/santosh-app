# How this app is built (Hoola App Engine)

- React 18 + TypeScript + Vite + Tailwind v4: the one template; no other framework.
- Colours, corners, shadows and fonts come ONLY from `src/styles/tokens.css` (bg, surface, ink, muted, line, primary,
  primary-ink, accent, ok, warn, bad): a raw colour, a Tailwind palette colour or a one-off `[value]` is refused.
- Change a component's look through its `cva` variants in `src/components/ui/`, never one-off classes on a page.
- Packages: only the vetted list (`app_engine action=add_dependency`); never a guessed name.
- Data, sign-in, files, payments, AI: only through `src/lib/hoola.ts` (Hoola Cloud, not connected yet).
- Pages in `src/pages/`, routes in `src/App.tsx`, shared parts in `src/components/`.
- The kit (v0.999.51): `src/components/ui/` = the full shadcn-style set (Select, DatePicker, Calendar, Accordion,
  Sheet, Drawer, Command, DropdownMenu, Tooltip, Carousel, Chart, Form...), `src/components/effects/` = CSS-only
  moments (Reveal, NumberTicker, Marquee, patterns, SpotlightCard, WordRotate, BorderBeam), `src/components/blocks/` =
  one React block per section type (hero, services-grid, pricing-table, faq, screen-dashboard ...), each with
  `variants` and sample defaults. Build pages from blocks; pass her real words as props.
- Taste rules (refused on write): never transition-all; never the browser's own <select>, date box or alert(); no
  emoji as icons (lucide-react); never a gradient on a button, at most 3 gradients a file.
- The design (v0.999.58): DESIGN.md = this app's own design genome (direction, colours from one brand hue checked in
  light and dark, bundled fonts incl. Indian scripts, corners, density, motion, imagery); tokens.css and the fonts in
  src/styles/fonts are written from it. Never edit them by hand: `app_engine action=design_new` (or design_import).
- Pages go out pre-rendered (v0.999.64): the build renders every page to finished HTML. Put ONE `<Seo title
  description jsonLd>` (`@/lib/seo`) on every page; link pages with `<Link to>` (React Router) so the build finds them;
  never touch `window` / `document` while a component renders (only in effects or handlers).
- A SITE app (render "site"): every page is plain HTML that loads no script, except its ISLANDS - a component file in
  `src/components/` or `src/islands/` that starts with `"use client";` (forms, booking, accordions, carts, filters).
  Island props must be plain data. A page for signed-in people or live data is wrapped in `<AppPage>` (`@/lib/seo`)
  and runs as the full app. An APP (render "app") runs whole in the browser after its first pre-rendered paint.
