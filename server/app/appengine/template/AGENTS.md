# How this app is built (Hoola App Engine)

- React 18 + TypeScript + Vite + Tailwind v4: the one template; no other framework.
- Colours, corners, shadows and fonts come ONLY from `src/styles/tokens.css` (bg, surface, ink, muted, line, primary,
  primary-ink, accent, ok, warn, bad): a raw colour, a Tailwind palette colour or a one-off `[value]` is refused.
- Change a component's look through its `cva` variants in `src/components/ui/`, never one-off classes on a page.
- Packages: only the vetted list (`app_engine action=add_dependency`); never a guessed name.
- Data, sign-in, files, payments, AI: only through `src/lib/hoola.ts` (Hoola Cloud, not connected yet).
- Pages in `src/pages/`, routes in `src/App.tsx`, shared parts in `src/components/`.
