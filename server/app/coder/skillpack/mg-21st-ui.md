---
name: mg-21st-ui
description: 21st.dev UI components - pehle catalog, phir craft
when_to_use: ui component, react component, pricing section, hero section, navbar, dashboard ui, tailwind, shadcn, landing page section
---
GOAL: jab bhi UI element banana/add karna ho (pricing section, hero, navbar,
dashboard, form, testimonials), pehle 21st.dev ke CATALOG se dekho - 10,000+
production-ready React/Tailwind (shadcn-compatible) components wahan pade hain,
dependencies + demos + responsive/dark-mode ke saath. From-scratch likhna LAST
option hai (the search-first law).

THE DOOR: `magic21` tool (v0.512). Kill switch coder_magic21 default OFF hai -
band ho to ye skill ke baaki laws (family, tokens, honesty) waise hi lagte hain,
sirf network wala hissa nahi. Band hone par: uiux_design + fe-ui-kit + docs7 se
kaam chalao - design family wahi rehti hai.

WORKFLOW 1 - catalog se install (DEFAULT rasta):
1. magic21 op=search, CHHOTA natural query ("pricing table", "animated hero") -
   ek baat ek query, lambi kahani nahi.
2. Best match chuno apne stack + style ke hisaab se; choice obvious na ho to
   use pehle 1-3 candidates dikhao.
3. magic21 op=get (get_component) se poora code + metadata lo.
4. Install karo jaise result bole (shadcn-style registry add ya files likh kar),
   phir page mein wire karo aur project ke DESIGN SYSTEM mein adapt karo -
   Tailwind config, cn helper, component folder layout, Hoola ke fe-ui-kit
   tokens. Component aata hai, family tum banati ho.

WORKFLOW 2 - generate (sirf jab catalog kuch na de):
1. PEHLE magic21 op=usage (get_usage.aiGenerationEnabled) - hosted AI sirf tab
   jab entitlement ON ho. Missing/unknown status = permission NAHI.
2. AI off: search + get_component se lo, APNE coding haath se adapt karo.
   Generate tools, legacy aliases (21st_magic_component_builder/refiner), CLI -
   koi workaround NAHI.
3. AI on: op=call generate with purpose + layout + content + style + stack.
   AI credits lagte hain; preview URL aata hai.
4. `ai_subscription_required` dikhe to RUK JAO - dobara try nahi (na legacy
   naamaon se, na CLI se). AI enable hone ke baad tool list refresh karo.
   aiGenerationEnabled ACCESS batata hai, credit BALANCE nahi.

LOGOS: op=call search_logo - ek brand per call, ready-to-paste JSX/TSX aata hai.

FREE TIER HONESTY: catalog search free; 2 component installs/day; paid
components ka code unlock ke baad hi. Bolna sach: "ye component paid hai" -
khud se unlock ka dawa nahi.

LAWS:
- Legacy naame abhi chalte hain (logo_search, 21st_magic_component_builder,
  21st_magic_component_inspiration, 21st_magic_component_refiner) par NAYE
  naam use karo: search, get_component, generate, get_inspiration, search_logo.
- Secrets (keys, passwords, personal data) kabhi query/arguments mein NAHI -
  Hoola bhejne se pehle redact karta hai, par pehle hi mat likho.
- Auth error aaye to use se kaho: fresh key https://21st.dev/mcp se leni hai,
  phir key magic21_api_key mein (chat mein KABHI nahi).
- Har component project ki family mein jaata hai - tokens pehle (fe-ui-kit),
  naya rang sirf jab token na ho.
