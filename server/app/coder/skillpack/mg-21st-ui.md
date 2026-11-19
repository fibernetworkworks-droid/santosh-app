---
name: mg-21st-ui
description: 21st.dev UI components - catalog first, then craft
when_to_use: ui component, react component, pricing section, hero section, navbar, dashboard ui, tailwind, shadcn, landing page section
---
GOAL: whenever a UI element has to be built / added (pricing section, hero,
navbar, dashboard, form, testimonials), look in the 21st.dev CATALOG first -
10,000+ production-ready React / Tailwind (shadcn-compatible) components are
there, with dependencies + demos + responsive / dark-mode support. Writing from
scratch is the LAST option (the search-first law).

THE DOOR: the `magic21` tool (v0.512). The kill switch coder_magic21 is OFF by
default - when it is off, the other laws of this skill (family, tokens, honesty)
still apply, only the network part does not. When it is off: work with
uiux_design + fe-ui-kit + docs7 - the design family stays the same.

WORKFLOW 1 - install from the catalog (the DEFAULT path):
1. magic21 op=search, a SHORT natural query ("pricing table", "animated hero") -
   one thing per query, not a long story.
2. Pick the best match for your stack + style; when the choice is not obvious,
   show the user 1-3 candidates first.
3. Get the full code + metadata with magic21 op=get (get_component).
4. Install as the result says (a shadcn-style registry add, or by writing the
   files), then wire it into the page and adapt it to the project's DESIGN
   SYSTEM - Tailwind config, cn helper, component folder layout, Hoola's
   fe-ui-kit tokens. The component arrives; you make it part of the family.

WORKFLOW 2 - generate (only when the catalog gives nothing):
1. FIRST magic21 op=usage (get_usage.aiGenerationEnabled) - hosted AI only when
   the entitlement is ON. A missing / unknown status is NOT permission.
2. AI off: take it with search + get_component and adapt it by YOUR OWN coding.
   Generate tools, legacy aliases (21st_magic_component_builder / refiner), the
   CLI - NO workaround.
3. AI on: op=call generate with purpose + layout + content + style + stack.
   It uses AI credits; a preview URL comes back.
4. If `ai_subscription_required` shows, STOP - do not try again (not through
   the legacy names, not through the CLI). Refresh the tool list after AI is
   enabled. aiGenerationEnabled reports ACCESS, not the credit BALANCE.

LOGOS: op=call search_logo - one brand per call, ready-to-paste JSX / TSX comes
back.

FREE TIER HONESTY: catalog search is free; 2 component installs/day; the code of
paid components only after an unlock. Say what is true: "this component is
paid" - never claim to have unlocked it yourself.

LAWS:
- The legacy names still work (logo_search, 21st_magic_component_builder,
  21st_magic_component_inspiration, 21st_magic_component_refiner) but use the
  NEW names: search, get_component, generate, get_inspiration, search_logo.
- Secrets (keys, passwords, personal data) NEVER go into a query / arguments -
  Hoola redacts before sending, but do not write them in the first place.
- On an auth error tell the user: a fresh key comes from https://21st.dev/mcp,
  then the key goes into magic21_api_key (NEVER into chat).
- Every component joins the project's family - tokens first (fe-ui-kit), a new
  color only when no token exists.

ALSO ASKED AS (Hinglish asks this skill answers): website ke liye pricing
section banao, hero section chahiye, sundar UI component lagao
