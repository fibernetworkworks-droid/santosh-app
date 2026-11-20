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
