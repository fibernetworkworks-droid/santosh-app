---
name: fe-ui-kit
description: Hoola UI kit tokens - every screen one family
when_to_use: brand colors, colours, fonts, theme, design tokens, consistent look, style guide, Hoola look
---
GOAL: whatever Hoola writes - a HyperFrames composition, an email, a console card,
an HTML page - ALL of it looks like one family. The design-system rule: tokens
first, a new color only when no token exists.

NIGHT GLASS TOKENS (lib/ui/glass.dart class C - the source of truth):
- Background: deep indigo night #0B0A1A -> #120E2A (top to bottom).
- Text: ink #F4F2FF (main), muted #B9B3DA (secondary), faint #9C96C2 (captions).
- Action: saffron #FFB15C (primary buttons, active tab); text on saffron #1B1030.
- Support: violet #7C5CFF (user/you side), magenta #C055F5, teal #2DD4BF,
  ok #34D399, warn #FFC27A, bad #F87171, chip #D7D2F2.
- House gradient: #FFD9A8 -> #FF9A3C -> #C055F5 (topLeft to bottomRight). You-side
  gradient: #7C5CFF -> #B44CF0.
- Panels/glass: white at 8% (#FFFFFF14) as panel fill and line color - light glass
  on a dark background, no heavy border.

TYPE:
- Display/headings: Sora, bold, height 1.12, letterSpacing -1.5%.
- Body/reply: serif 16px, weight 400, height 1.5 (Claude-style reading comfort).
- One display font per screen; sizes in clear steps (12/14/16/20/28/40).

THE LAWS:
- Token first: do not mix a new shade - take an existing token. Contrast: ink on
  bg never below 7:1; on saffron only the onAccent text.
- One accent per screen: saffron = only the action. ok/warn/bad = for status,
  not for decoration.
- Motion, one family: 150-250ms fades, 80-120ms stagger, one easing (ease-out) -
  the same feel in a video or a console card.
- Dark on dark: build hierarchy with the panel + line tokens, do not print a
  black box.
- These tokens are the same in HTML/CSS (hex), and in Dart from class C.
NEVER: rainbow screens (more than 2 accents), light-theme colors laid over Night
Glass, decorative motion that gets in the way of reading, a random hex outside the
tokens when a token exists.

ALSO ASKED AS (Hinglish asks this skill answers): video aur card ke colors
Hoola ke brand jaise rakho, har jagah ek jaisa look chahiye
