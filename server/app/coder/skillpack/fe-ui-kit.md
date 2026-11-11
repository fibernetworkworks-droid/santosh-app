---
name: fe-ui-kit
description: Hoola UI kit tokens - har screen ek family
when_to_use: brand colors, colours, fonts, theme, design tokens, consistent look, style guide, Hoola look
---
GOAL: jo bhi Hoola likhti hai - HyperFrames composition, email, console card, HTML
page - SAB ek hi family mein dikhe. Design-system ka rule: tokens pehle, naya rang
sirf jab token na ho.

PHONE APP TOKENS (lib/ui/glass.dart class C - the source of truth; v0.832 neutral dark):
- Ground: one flat neutral #151515. Surface (composer, tab pill, cards) #202020;
  her message bubble #2A2A28; hairline border #30302D. Koi gradient background nahi.
- Text: ink #F3F1EC (main), muted #A09B93 (secondary), faint #8E8981 (captions).
- Action: saffron #F4A24C (primary buttons, active tab, "Hoola kaam kar rahi hai");
  text on saffron #1B1305.
- Support: violet #7C5CFF + magenta #C055F5 (sirf avatar orb), teal #2DD4BF,
  ok #44CF95, warn #F4B85C, bad #F2706F, chip ink #E2DFD8.
- Avatar orb gradient: #FFD9A8 -> #FF9A3C -> #C055F5 (topLeft se bottomRight) - bas orb par.
- Panels: surface + hairline border; blur, glow aur heavy shadow nahi.

TYPE:
- Display/headings: Schibsted Grotesk, semibold, height 1.15, letterSpacing -1%.
- Body/reply: serif 16px, weight 400, height 1.5 (Claude-style reading comfort).
- Ek screen ek display font; sizes clear steps mein (12/14/16/20/28/40).

THE LAWS:
- Token pehle: naya shade mat gholo - existing token uthao. Contrast: ink on bg
  7:1 se kam kabhi; onAccent par saffron hi.
- Ek accent per screen: saffron = sirf the action. ok/warn/bad = status ke liye,
  decoration ke liye nahi.
- Motion ek family: 150-250ms fades, 80-120ms stagger, ek easing (ease-out) -
  video ho ya console card, wahi feel.
- Dark on dark: surface + hairline se hierarchy banao, black box na chhapo.
- Yeh tokens HTML/CSS mein bhi waise hi (hex), Dart mein class C se.
NEVER: rainbow screens (2 se zyada accent), light-theme colors utha ke neutral dark
par chadhana, decorative motion jo padhne mein rukavat hai, tokens se alag random
hex chunna jab token maujood hai.
