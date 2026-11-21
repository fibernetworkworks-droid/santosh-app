# Customer Support - from a small shop to a very large enterprise (plan)

Owner, 21 Nov 2026: "CUSTOMER SUPPORT AI EMPLOYEE IS VERY VAST AND MIGHT NEED DIFFERENT INPUT. HOW TO MAKE IT GENERALIZE
FOR SMALL TO VERY LARGE ENTERPRISES" -> "PLAN AND DESIGN".
Design canvas: claude.ai/artifact/5jfZyfhs92TJ7oqAiK2U4b (7 screens: setup, what each size sees, queues + routing,
one knowledge store, approval chains, channels + existing helpdesk, answer quality + controls).
Built so far: v0.999.81 CUSTOMER SUPPORT DESK (the desk + Support chat on the Seva engine, `server/app/seva/`,
`server/app/supportchat.py`, `/console/support`).

## 0. Updated after reading Chatwoot (docs/research/chatwoot/00_READ.md)
Chatwoot (MIT outside `enterprise/`; its enterprise folder is a paid licence - ideas only) adds to this plan: a rule
engine (event + conditions + actions, optional delay) under routing and escalation (S4/S5); assignment knobs (round robin
/ least busy, longest waiting first, skip old backlog, fair limit, capacity per agent); NEXT-response and business-hours
reply clocks; snooze-until; custom fields + saved views; permission-list roles; saved replies grow into macros; FAQ
suggestions mined from solved tickets (S2); a false-promise check on every AI reply; a signed visitor identity for the
web widget (S3); Chatwoot itself as the first helpdesk for layer mode (S6); an optional public help center.

## 1. The one idea

ONE Customer Support employee, ONE engine. What a business sees and what it is asked for is decided by a **profile**
picked from a few setup answers - not by separate products. A small shop keeps today's simple desk; a large company gets
teams, queues, approval chains, its own helpdesk joined and the trust controls. Every part that is not needed stays
hidden, and every part can be switched on later from Channels & settings.

Laws that never change with size:
- A customer is answered only from APPROVED knowledge or a live lookup she approved; unknown = a person, never a guess.
- Every refund / waiver / discount / exception is decided by a person's tap; Hoola never moves money.
- A customer only ever sees their own tickets; internal notes never reach a customer.
- No OTP, PIN, password or card number is asked or kept.

## 2. What differs by size (the inputs)

| | Small (1-3 people) | Mid (5-50 people) | Large (50+ people, many units) |
|---|---|---|---|
| Who answers | The owner | One team | Many teams, supervisors, shifts, regions |
| Knowledge | Typed answers, a PDF | Website, sheets, policies | Thousands of articles + live lookups in their systems |
| Channels | One WhatsApp number | WhatsApp, email, web chat, phone | Many numbers / brands / countries |
| Tools already used | None | Maybe a spreadsheet | Zendesk / Freshdesk / Salesforce Service Cloud / Zoho Desk |
| Refund rules | "7 days, owner decides" | Limits per product | Rules per product, customer tier, region; approval chains |
| Must prove | Nothing | Reports | Audit, SSO, retention, answer-quality sampling, data region |

## 3. The profile (S0 - setup)

Hiring Customer Support opens a setup of 8 questions (each skippable, each with a sensible default):
1. Size: just me / a small team / several teams / an enterprise with departments.
2. Industry: shop, online seller, clinic / hospital, internet / telecom, bank / finance / insurance, software / SaaS,
   hotel / travel, education, utilities, other.
3. Channels customers use today (ticks).
4. Do you already use a helpdesk? none / Zendesk / Freshdesk / Salesforce / Zoho Desk / other.
5. Team: how many people answer customers, and do they work in shifts / by language / by product / by region?
6. Money decisions: up to what amount may a staff member agree alone? a supervisor? (blank = everything to the owner).
7. Languages and countries served.
8. Where orders / accounts live (Systems page, sheet, own API, none) - for live lookups.

Answers -> `profile` (stored on seva_settings): `tier` small | team | multi | enterprise, `industry`, `mode` own | layer
(layer = Hoola works on top of her existing helpdesk), switches for teams, routing, chains, trust controls. The desk reads
the profile to show / hide pages and fields. Changing an answer later re-applies only what she agrees to (a preview of
what will change, then her tap).

## 4. Phases

### S1 Industry packs (data, not code)
`seva/packs/<industry>.json`: ticket categories with keywords, priority words, reply-time presets, policy fields
(refund days, warranty, cancellation, chargeback window...), the legal notes that apply per country (India: E-Commerce
Rules 2020, RBI Integrated Ombudsman, IRDAI, TRAI, CERT-In, DPDP - the ones `seva/rules.py` already holds move here with
their source + checked date), starter questions to ask her for the knowledge, saved-reply starters. Today: 4 presets
(shop, isp, ecommerce, clinic) -> 10 packs. Unverified law = shown as "check this", never applied silently.

### S2 One knowledge store (shared with the Telecaller)
Support and the Telecaller each keep knowledge today (`seva_entries`, `callcentre/knowledge.py`). Merge into one
business brain both employees read: typed answers, files, website pages, sheets, her API, joined systems, and LIVE
lookups ("order status by the caller's / sender's own number") - the Telecaller's source engine already does sources,
approval by hash, sync and live mode; Seva's answer matcher becomes its reader. New: import from Zendesk Guide /
Freshdesk solutions / Confluence (read-only, via the connector), knowledge versions (who approved what, when, restore),
"stale" flag when a source changed, owner per article for large tiers. Customers still see only approved facts.

### S3 Every channel into one inbox
- Website chat: a small widget (one line of code) for any site + on for Web Studio sites; visitor messages become
  conversations / tickets; the visitor sees only their own.
- Email: her support address (Gmail / Outlook already joined) -> a label or alias the desk reads; replies go from her
  address after her tap (small tier) or by trust level (team+).
- Phone: Telecaller incoming calls with a problem open a ticket with the call summary attached.
- Instagram / Facebook messages: shared with the Social Media Manager's inbox (one place, one owner per thread).
- Several numbers / brands: each channel carries a `brand`; replies, knowledge and policy are per brand.

### S4 Teams, queues, routing, shifts
- Queues (e.g. Billing, Technical, Sales, Region North), each with members (TeamMember), languages, hours / shifts,
  reply times, and an overflow queue.
- Routing rules as data: category / product / language / region / customer tier / channel -> queue; within a queue
  round-robin or least-busy among members on shift; VIP and urgent jump the line.
- Roles: agent (works tickets), supervisor (reassigns, approves within a limit, sees queue health), admin (rules,
  knowledge, settings). Hoola itself is a member of every queue it is allowed in.
- Hand-over AI -> person carries the whole conversation + what Hoola already checked; a person can hand back.
- Supervisor view: queue length, oldest waiting, late soon, who is on shift.

### S5 Rules as data + approval chains
- Policy rules: `when` (kind, product, customer tier, region, days since, amount) -> `then` (allowed / needs approval
  by role / never). Checked in code; the card shows which rule decided it.
- Chains: amount bands -> who must approve (agent <= X, supervisor <= Y, owner / finance above). Every step is a
  person's tap, bound to the card's hash; the money step keeps the fingerprint on a phone.
- Limits per person per day / month; a decision above them goes up a level automatically.

### S6 Work on top of an existing helpdesk ("layer" mode)
For Zendesk / Freshdesk / Salesforce Service Cloud / Zoho Desk through their official APIs (Composio where it covers it,
else the vendor API with her sealed key): read new tickets -> sort (category, priority, language), suggest a reply from
approved knowledge as an INTERNAL note or a draft, answer simple ones only at her chosen trust level, summarise long
threads, find knowledge gaps, report. Tickets stay in her tool; Hoola never deletes or closes without the rule allowing
it. Writes are logged both sides.

### S7 Trust controls for large companies
- SSO (SAML / OIDC) for her staff on the desk; roles from her identity provider groups.
- Audit log of every AI answer, approval, rule change and knowledge change (export).
- Personal data: masking in stored text (exists), retention days per channel, delete on request (DPDP / GDPR).
- Data region note (where data is kept) - honest, not a promise the server cannot keep.
- Answer quality: a sample of AI answers each day for a supervisor to mark right / wrong / should have gone to a person;
  wrong answers lower that topic's trust and feed the knowledge gaps; a monthly accuracy number per topic.
- Sandbox: try a rule / knowledge change against last week's real questions before it goes live.

### S8 Reports at every size
Today's numbers + per queue / agent / channel / brand / product / region; AI resolved without a person; cost per
ticket (credits); trend vs last period; exports (CSV, PDF monthly).

## 5. Order and size of work
S1 + S0 first (every new customer starts right), then S2, S3, S4, S5, S6, S7, S8. Each phase ships alone, with tests and a
browser walk, and is switched by the profile so a small shop never sees it.

## 6. Decisions only the owner can make
1. Layer mode: which helpdesks first (suggest Chatwoot first - open API, free to run, used by many Indian SMBs - then Zendesk + Freshdesk, Zoho Desk, Salesforce).
2. Website chat widget on any website (not only Hoola sites) - yes / later.
3. SSO and the enterprise controls as a paid add-on or part of the package.
4. Which industry packs first (suggest online seller, internet / telecom, clinic, bank / finance, SaaS).
5. Whether Support and Telecaller share ONE knowledge store from now on (recommended).

## 7. Not verified / risks
- No vendor helpdesk API has been called from here; their write limits and rate limits decide how fast layer mode works.
- Law notes per country need a checked source each; unchecked ones are shown as "check this".
- Routing quality needs real volume to tune; first versions are rules she can read, not a model.
