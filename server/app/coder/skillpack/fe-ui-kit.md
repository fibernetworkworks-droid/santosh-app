---
name: fe-ui-kit
description: Hoola UI kit tokens - har screen ek family
when_to_use: brand colors, colours, fonts, theme, design tokens, consistent look, style guide, Hoola look
---
GOAL: jo bhi Hoola likhti hai - HyperFrames composition, email, console card, HTML
page - SAB ek hi family mein dikhe. Design-system ka rule: tokens pehle, naya rang
sirf jab token na ho.

NIGHT GLASS TOKENS (lib/ui/glass.dart class C - the source of truth):
- Background: deep indigo night #0B0A1A -> #120E2A (upar se neeche).
- Text: ink #F4F2FF (main), muted #B9B3DA (secondary), faint #9C96C2 (captions).
- Action: saffron #FFB15C (primary buttons, active tab); text on saffron #1B1030.
- Support: violet #7C5CFF (user/you side), magenta #C055F5, teal #2DD4BF,
  ok #34D399, warn #FFC27A, bad #F87171, chip #D7D2F2.
- House gradient: #FFD9A8 -> #FF9A3C -> #C055F5 (topLef se bottomRight). You-side
  gradient: #7C5CFF -> #B44CF0.
- Panels/glass: white at 8% (#FFFFFF14) panel fill aur line color - dark background
  par halka glass, heavy border nahi.

TYPE:
- Display/headings: Sora, bold, height 1.12, letterSpacing -1.5%.
- Body/reply: serif 16px, weight 400, height 1.5 (Claude-style reading comfort).
- Ek screen ek display font; sizes clear steps mein (12/14/16/20/28/40).

THE LAWS:
- Token pehle: naya shade mat gholo - existing token uthao. Contrast: ink on bg
  7:1 se kam kabhi; onAccent par saffron hi.
- Ek accent per screen: saffron = sirf the action. ok/warn/bad = status ke liye,
  decoration ke liye nahi.
- Motion ek family: 150-250ms fades, 80-120ms stagger, ek easing (ease-out) -
  video ho ya console card, wahi feel.
- Dark on dark: panel + line tokens se hierarchy banao, black box na chhapo.
- Yeh tokens HTML/CSS mein bhi waise hi (hex), Dart mein class C se.
NEVER: rainbow screens (2 se zyada accent), light-theme colors utha ke Night Glass
par chadhana, decorative motion jo padhne mein rukavat hai, tokens se alag random
hex chunna jab token maujood hai.
