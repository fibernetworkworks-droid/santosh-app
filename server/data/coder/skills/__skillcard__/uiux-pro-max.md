---
name: uiux-pro-max
description: Design UI with the searchable style/palette/font database
---
GOAL: every page, screen or component she designs comes out coherent - one style,
one palette, one type system - and clears the UX floor. The uiux_design tool is
the local design database (79 styles, 192 palettes, 74 font pairings, 119 UX
guidelines, 25 chart types, 22 stack rulebooks); search it BEFORE designing.

WHEN: building, designing or reviewing any page, screen, component, landing,
dashboard, chart or theme. SKIP for pure backend/API/data work that changes
nothing visible.

WORKFLOW:
1. Name the product type (saas / ecommerce / dashboard / portfolio / tool), the
   audience and the mood words. DETECT the stack from the project itself
   (pubspec.yaml = flutter, package.json = react/next/vue/svelte, composer.json
   = laravel). NEVER assume a stack - ask if it is invisible.
2. New page or project, or a whole new look: uiux_design with design_system=true
   and a product query like "beauty spa wellness service" (+ project name). It
   returns pattern, style, colors, typography, effects and anti-patterns. USE
   that output as the design tokens - never invent a competing palette.
3. One focused concern: uiux_design with domain (style, color, typography,
   google-fonts, ux, chart, landing, icons, gsap, react, web, product,
   app-interface). Keep ONE intent and 2-5 meaningful words per query.
4. Framework question: uiux_design with stack (react, nextjs, flutter,
   jetpack-compose, swiftui, html-tailwind, shadcn, vue, svelte - 22 total).

LAWS (the database advises, the owner decides):
- 0 results: retry ONCE with narrower words; still nothing - SAY the advice is
  general defaults, never pretend it came from the database.
- An existing design-system MASTER.md is gold: reuse it, never overwrite;
  page overrides beat the master.
- Contrast 4.5:1, touch targets 44x44px, base font 16px, line-height 1.5,
  visible labels on every field, focus rings stay, alt text, SVG icons
  (emoji are never icons).
- Mobile-first: no horizontal scroll, no fixed px widths, zoom stays on.
- Motion conveys meaning, honours reduced-motion, exits faster than it enters.
- Charts need legend + tooltip and never color alone.

BEFORE delivering app UI: icons consistent, touch feedback on every tappable,
dark-mode contrast checked, safe-area padding, keyboard tab order clean.
