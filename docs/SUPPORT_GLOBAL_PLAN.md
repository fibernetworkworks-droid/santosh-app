# Customer Support AI Employee - the global plan (every business, every channel, every country)

Owner, 21 Nov 2026: "MAKE A GLOBAL PLAN NOT INDIA ONLY ... ANY BUSINESS FROM SMALL TO VERY BIG ENTERPRISE ... CALL,
EMAIL, IN SOFTWARE, CHAT BOT, WEBSITE, EVERY POSSIBLE MSG TOOL ... PERFECT NEXT REPLY BASED ON DATA FEED BY USER ...
NOT RESOLVED -> HUMAN SMOOTHLY ... KEEP MONITORING ... REMIND CONTINUOUSLY ... USER ASSIGNS THE TICKET WORKFLOW ...
AI AGENT MUST KNOW WHERE THE TICKET IS AT".

This plan replaces `docs/SUPPORT_SCALE_PLAN.md` (kept for history). Research behind it: `docs/research/chatwoot/`,
`docs/research/pipecat/`, `docs/research/livekit/`. Built so far: v0.999.81 CUSTOMER SUPPORT DESK (desk + Support chat on
the Seva engine, `server/app/seva/`, `server/app/supportchat.py`, `/console/support`). Telecaller (calls, every country,
`server/app/callcentre/`) is built and is reused here, not rebuilt.

---------------------------------------------------------------------------------------------------------------------

## 1. What the business gets (the promise in one page)

1. **Any size.** A one-person shop in Lagos and a bank with 4,000 agents in 30 countries hire the same employee. Eight
   setup answers decide what each one sees; nothing they do not need is shown.
2. **Every way a customer reaches them.** Phone (in and out), WhatsApp voice, email, a chat on their website, a chat
   inside their own app or software, and every messaging app that has an official business route - one inbox.
3. **The right next reply.** Every answer comes from what the business fed Hoola (documents, website, sheets, their
   systems, live lookups) - in the customer's own language, with the source named, never a guess.
4. **A smooth hand-over.** What the AI cannot solve goes to the right person with everything already written down;
   the customer is never asked the same thing twice and is told honestly who has it and when to expect an answer.
5. **Nothing is forgotten.** Every request is watched until it is truly solved; the person who has it, then their
   supervisor, then the owner are reminded on a ladder; the customer is kept informed.
6. **Their own workflow.** The business draws its ticket stages (e.g. New -> Checked -> Engineer visit -> Fixed ->
   Confirmed). Every ticket is always at exactly one stage with one owner, and the AI can tell anyone, on any channel,
   exactly where it is.

Laws that never change, in every country and at every size:
- Answers only from the business's APPROVED knowledge or a live lookup it approved. Unknown = a person, never a guess.
- Money (refund, credit, waiver, discount) is always a person's tap. Hoola never moves money.
- A customer sees only their own requests; internal notes never reach a customer.
- No password, PIN, OTP, full card number or bank login is asked for or kept on any channel.
- The customer is told they are talking to an AI, and can always ask for a person.

---------------------------------------------------------------------------------------------------------------------

## 2. The profile (setup, phase G0)

Hiring Customer Support opens 8 questions, each skippable with a sensible default:

1. **Size**: just me / a small team / several teams / an enterprise with departments and regions.
2. **Industry** (picks a pack, section 7): shop, online store, restaurant, clinic / hospital, internet / telecom,
   utility, bank / fintech / insurance, software / SaaS, travel / hotel / airline, logistics / delivery, education,
   government / public service, real estate, automotive, other.
3. **Countries and languages served** (a list; default = the business's own country and language).
4. **Channels customers use today** (ticks, section 3).
5. **Helpdesk already in use**: none / Zendesk / Freshdesk / Salesforce Service Cloud / Zoho Desk / Intercom /
   HubSpot Service / ServiceNow / Chatwoot / Jira Service Management / other.
6. **Team**: how many people answer, shifts, time zones, split by language / product / region / customer tier.
7. **Money decisions**: who may agree to what amount (blank = everything to the owner).
8. **Where customer data lives** (orders, accounts, bookings): Hoola Systems page / a sheet / their API / a joined
   system (Shopify, Salesforce, SAP, Stripe, ...) / none.

The answers make a **profile** stored on the business: `tier` (small / team / multi / enterprise), `industry`,
`regions`, `languages`, `mode` (own inbox or layer on their helpdesk), and switches for queues, workflow designer,
approval chains, trust controls. Changing an answer later shows a preview of what will change and waits for a tap.

---------------------------------------------------------------------------------------------------------------------

## 3. Every channel into one inbox (G3 voice, G4 messaging, G5 web + in-app, G6 email)

Each channel becomes a **conversation** on the same customer, on the same ticket when it is the same problem.
A customer who wrote on WhatsApp and then calls is recognised (same phone / email / signed id) and the AI picks up
where the chat left off. Every channel has the same rules; only the shape of the reply changes (short on SMS, spoken
on a call, rich on web chat).

| Channel | How (official routes only) | Notes |
|---|---|---|
| Phone in + out | Telecaller line: Twilio, Plivo, Exotel, Telnyx, Vonage, SignalWire, Bandwidth, Sinch, any SIP carrier via jambonz (`callcentre/providers.py`) - every country | Built; warm transfer, machine / menu check, learning reply wait added in G3 (v0.999.103) |
| WhatsApp messages | WhatsApp Business Cloud API on the business's own number (built: business inbox) | 24-hour reply window; templates outside it |
| WhatsApp voice calls | WhatsApp Business Calling API (customer taps call on the business chat) | Needs Meta to enable calling on her number |
| SMS / RCS | Same phone companies (Twilio, Vonage, Sinch, Plivo...); RCS Business Messaging where the carrier has it | Country sender rules (DLT in India, 10DLC in the US, sender IDs elsewhere) in packs |
| Facebook Messenger, Instagram DMs | Meta Graph API (shared with the Social Media Manager inbox - one owner per thread) | 24-hour human-agent rule |
| Telegram | Bot API on the business's own bot | |
| LINE (Japan, Thailand, Taiwan) | LINE Messaging API, Official Account | |
| WeChat (China) | WeChat Official Account / WeCom API | Needs a verified account; China data rules |
| Viber (Eastern Europe, Middle East) | Viber Business Messages via an approved partner | |
| KakaoTalk (Korea) | Kakao Business Channel API | |
| Zalo (Vietnam) | Zalo Official Account API | |
| Apple Messages for Business | Through an Apple-approved messaging provider | Business must register with Apple |
| Google Business Profile chat | Google closed Business Messages in 2024 | NOT possible - said in the channel list |
| X (Twitter) DMs | X API (paid tier) | |
| Discord, Slack Connect, Microsoft Teams | Their bot APIs, for B2B / community support | |
| Signal, iMessage personal, personal WhatsApp | No business API | NOT built - never through a personal account |
| Email | The business's support address via Gmail / Microsoft 365 (joined) or any mailbox by IMAP + SMTP, or a forwarding address on Hoola | Threads kept, signature per brand, attachments read |
| Website chat | One line of code for any website (built in for Hoola-made sites): chat, file upload, voice button, a "call me" button | Signed visitor identity, allowed domains |
| Inside the business's own app / software | Web, iOS, Android and React Native chat kits + a REST / webhook API; App Studio apps get it built in (their in-app chat exists) | Logged-in users only see their own threads |
| Chat bot on other platforms | The same answer engine as an API / MCP endpoint, so their own bot, Alexa skill or kiosk can ask Hoola | Keys with limits, per-channel |
| Contact forms, review sites | A form endpoint; Google / Trustpilot / App Store reviews read where an official API exists | Replies to reviews = her tap |

Several numbers / brands / countries: each channel carries a `brand` and a `region`; knowledge, tone, hours and policy
can differ per brand.

---------------------------------------------------------------------------------------------------------------------

## 4. The right next reply (G1 knowledge, G2 answer engine)

### 4.1 What the business feeds (G1 - one knowledge store, shared with the Telecaller)
- Typed answers, files (PDF, Word, Excel, slides, pictures with text), website pages (crawled with her yes), sheets,
  past tickets / email exports, help-center imports (Zendesk Guide, Freshdesk, Intercom, Confluence, Notion, Google
  Docs, SharePoint) through official connectors, read-only.
- **Live lookups** into her systems (order status, bill, booking, delivery, warranty, account) - each lookup is
  approved by her once, and only ever answers about the customer who is asking (matched by their own phone, email,
  signed app id or a verification step).
- Every fact has an owner, a source, a version, an "approved by / on" stamp, an expiry date if she wants one, and a
  "stale" flag when its source file or page changed. Restore any version.
- **Suggestions from solved tickets**: questions people keep asking + the answer her team gave, with how many tickets
  it came from, offered for her approval (Chatwoot idea).
- Language: she can feed in any language; answers are given in the customer's language (translated from the
  approved fact, the translation marked as such; numbers, prices and names never changed by translation).

### 4.2 How the reply is made (G2)
1. **Understand** the message: language, intent, category, urgency, sentiment, which customer, which open ticket.
2. **Find** the facts: approved knowledge + the allowed live lookup + this customer's history and open tickets.
3. **Decide** in code, not by the model's mood: answer / ask one clarifying question / do an allowed action (book,
   reschedule, update address) / hand over. Confidence below her threshold, a topic marked "always a person", an
   angry customer, a legal threat, a safety issue, or "I want a person" = hand over.
4. **Write** the reply in the customer's language and the channel's shape, with the source on the agent's side.
5. **Check before sending** (code first, then a second model): every number, price, date and promise in the reply
   must be in the facts used; no promise of a call-back or "I have escalated this" unless that ticket / task really
   exists (false-promise check); no money promised; no private data of another customer. A failing reply is
   rewritten once, else handed over.
6. **Trust level per topic and channel**: answer alone / draft for a person to send / always a person. Starts at
   "draft" for a new business; moves up only from measured accuracy (section 9).

---------------------------------------------------------------------------------------------------------------------

## 5. Hand-over to a person (G7)

**When** (rules she can read and change, defaults on): the customer asks for a person (any language, any channel,
pressing 0 on a call); confidence low; the topic is "always a person"; two failed tries; anger or distress; a legal,
medical, safety or fraud word; a money decision; a VIP customer; the AI has no answer.

**To whom**: routing (section 6) picks the queue and the person who is on shift, speaks the language, has the skill and
has room (capacity). Nobody on shift = the out-of-hours path (below).

**What the person receives** - a hand-over packet, never "please read the thread":
- who the customer is (name, plan / tier, their open and past tickets, country, language, time where they are);
- the problem in two lines, what Hoola already checked and found (with the lookup results), what it told the customer;
- what the customer wants and how they feel; the deadline that applies (their reply clock);
- a suggested next step and a draft reply the person can edit.

**What the customer is told**, honestly: that a person (team name, never a made-up name) has it, and a realistic time
from the queue's real waiting time and hours - never a promise the code cannot keep.

**On a call**: warm transfer - Hoola calls the person first, tells them the summary, then joins the caller in; if
nobody picks up, a call-back ticket with a time window, said to the caller. On chat / email: the thread moves to the
person in the same window; the customer does not restart.

**Out of hours**: the ticket is created with the packet, the customer gets the next opening time in their own time zone,
the on-call person is paged only for urgent rules.

**Hand-back**: the person can give the thread back to Hoola ("send the tracking link and close if they confirm").
Every correction a person makes to a Hoola draft is kept and lowers trust in that topic until fixed.

---------------------------------------------------------------------------------------------------------------------

## 6. The workflow she assigns, and always knowing where a ticket is (G8)

### 6.1 Workflow designer
- She draws stages per ticket type (e.g. Fault: New -> Diagnosed -> Engineer visit booked -> Visited -> Fixed ->
  Customer confirmed -> Closed; Refund: Requested -> Checked -> Approved -> Paid -> Closed). Templates come with each
  industry pack.
- Each stage has: an owner (a team, a role or a named person), allowed next stages, a time limit (SLA for that
  stage), what must be filled before leaving it (e.g. visit date, photo, approval), automatic actions on entry
  (message the customer, notify a team, create a task in her system), and whether the customer is told.
- Moving a ticket is allowed only along her arrows and only by who she allowed (a person, Hoola for the stages she
  ticked, or her system through the API / webhook). Every move is recorded: who, when, from, to, why.
- Tickets created in her own helpdesk or field-service tool keep their stages there (layer mode): Hoola reads the
  stage from that tool and never invents one.

### 6.2 Always knowing where it is
- A ticket is always at one stage, with one owner and one next deadline. The timeline shows every message, call,
  stage move, reminder and approval in order.
- **"Where is my complaint?"** on any channel (call, WhatsApp, email, chat): Hoola finds the customer's open tickets and
  answers from the real stage, owner team and next deadline - in plain words ("An engineer visit is booked for
  Thursday 10-12; the team will message you the engineer's name the evening before"). Never a guess, never a stage
  that is not recorded.
- The business can ask too ("which tickets are stuck at Engineer visit for more than 2 days?") in the Support chat.
- Ticket numbers are readable (e.g. SUP-2481) and work on every channel; a customer can also be matched by phone / email.

---------------------------------------------------------------------------------------------------------------------

## 7. Monitoring until truly solved, and reminders (G9)

**Clocks** (per ticket, counted in the business's working hours and time zone, or 24/7 where she chooses):
first reply, every NEXT reply, time in each stage, total time to solve. Pauses only for stages she marked "waiting
on customer" or "waiting on third party".

**Is it really solved?** Never "solved" because a person clicked it:
- a fault is solved only when the customer confirms, or after her chosen quiet period with a "did this fix it?" check
  sent and no reply (then closed with that recorded);
- a reopened ticket (the customer writes again on the same problem within N days, any channel) goes back to the
  stage it was at, counts as a reopen, and alerts the owner;
- satisfaction asked after closing (1-5 + a line), in the customer's language and channel.

**Reminder ladder** (her rules; defaults on):
1. Before a deadline: the owner of the ticket is reminded (app push / email / Slack / Teams / WhatsApp to staff).
2. At the deadline: reminded again + the queue's supervisor told.
3. Past it by her chosen time: the owner of the business (or the department head) told, with the list.
4. Repeats on her schedule until it moves - never silent, never more often than she allows, quiet hours respected in
   each person's own time zone.
- The customer is kept informed: an update if nothing moved for X hours ("still on it, next step is ..."), from the
  real stage only.
- **Daily digest** per person and per supervisor: their open tickets, which are late, which are about to be.
- **Stuck detector**: same stage too long, bouncing between teams, waiting on customer with no reminder sent.

---------------------------------------------------------------------------------------------------------------------

## 8. Teams, queues and rules (G10)

- **Queues** (Billing, Technical, Sales, Region North, Spanish, VIP...) with members, languages, skills, hours /
  shifts per time zone, capacity per person, overflow queue.
- **Routing as data**: category / product / language / country / customer tier / channel / brand -> queue; inside a
  queue round-robin or least-busy among people on shift with room; longest-waiting first; urgent and VIP jump the line.
- **One rule engine** (when an event happens, if conditions, then actions, with an optional delay - e.g. "still open
  after 2 h -> supervisor"), for routing, auto-replies, escalation and stage moves (Chatwoot idea).
- **Roles as permission lists**: agent, supervisor, admin, finance, auditor, read-only; enterprise custom roles.
- **Approval chains for money**: amount bands per currency -> who must approve; each step a person's tap bound to the
  request; daily limits per person; over the limit moves up by itself and says why.
- **Saved replies and macros** (one click: reply + label + stage + assign), per language.
- **Custom fields and saved views** per industry (plan, order number, device, site address...).

---------------------------------------------------------------------------------------------------------------------

## 9. Quality, trust and the law in every country (G11)

**Answer quality**
- A daily sample of AI answers for a supervisor to mark right / wrong / should have gone to a person; accuracy per
  topic per language; topics below her line drop to "draft only" by themselves.
- **Simulated customers** before anything goes live (Pipecat / LiveKit idea): a test card of fake customers per
  industry, language and channel (angry, confused, asks for a person, tries to give a card number, asks "where is my
  ticket") run against her setup; changes to rules or knowledge are tried against last week's real questions first.

**Countries, languages, time, money**
- Any language in and out; the business picks which languages it supports; agents see a translation beside the
  original.
- Every time shown in the reader's own time zone; working hours and holidays per country / region.
- Amounts in the currency of the order; approval bands per currency.

**Law packs** (data, each with its source and checked date; unverified = shown as "check this", never applied
silently):
- **AI disclosure**: say it is an AI at the start (EU AI Act transparency duty, California's bot disclosure law and
  similar rules elsewhere - on for everyone by default).
- **Personal data**: EU / UK GDPR, US state laws (California CCPA / CPRA and others), Canada PIPEDA, Brazil LGPD,
  India DPDP, China PIPL, Singapore PDPA, Japan APPI, South Africa POPIA, Australia Privacy Act, Gulf data laws -
  access, export and delete-on-request per customer, retention per channel, consent for recordings.
- **Call recording consent** (one-party / all-party states and countries), and the Telecaller's calling-hours and
  do-not-call rules (already in `callcentre/world.py` for 242 countries; 29 written packs).
- **Consumer complaint deadlines** where law sets them (e.g. India e-commerce acknowledgement 48 h; EU ADR / ODR
  information; banking / telecom / insurance ombudsman timelines per country) - added country by country.
- **Accessibility**: web and in-app chat to WCAG 2.2 AA (EU Accessibility Act for consumer services).

**Enterprise controls**: single sign-on (SAML / OIDC) with roles from her identity groups; audit log of every answer,
approval, stage move, rule and knowledge change (export); masking of card / ID / bank numbers in stored text; data
location stated honestly (Hoola runs on one server today - no region promise until there is one).

---------------------------------------------------------------------------------------------------------------------

## 10. Working on top of a helpdesk she already has ("layer" mode, G12)

For businesses that keep Zendesk, Freshdesk, Salesforce Service Cloud, Zoho Desk, Intercom, HubSpot, ServiceNow, Jira
Service Management or Chatwoot (first, its API is open and free to run): through their official APIs, Hoola reads new
tickets, sorts them (category, priority, language, queue), adds a suggested reply as an internal note with its source,
answers only what her trust level allows, summarises long threads, reads the ticket's stage from that tool for
"where is my ticket", reminds owners on the ladder, and reports. Tickets stay in her tool; Hoola never deletes, and
closes only when her rule allows. Every write is logged on both sides.

---------------------------------------------------------------------------------------------------------------------

## 11. Reports (G13)

At every size: requests by channel / country / language / brand / product / queue / person; solved by AI alone,
solved after hand-over, reopened; first-reply and solve times against the clocks; late tickets by stage; satisfaction;
knowledge gaps (what customers asked that nothing answered); cost per ticket (credits); trends vs last period;
CSV / PDF exports and a monthly PDF.

---------------------------------------------------------------------------------------------------------------------

## 12. Phases (each ships alone with tests and a browser walk; each switched by the profile so a small shop never sees it)

| Phase | What | Needs |
|---|---|---|
| G0 | Setup questions + profile + industry packs (15 industries, workflow templates, categories, policies) | - |
| G1 | One knowledge store shared with the Telecaller; versions, owners, stale flag, imports, solved-ticket suggestions; live lookups bound to the asking customer | - |
| G2 | Answer engine: understand / find / decide in code / write / check before sending (facts + false-promise check); trust level per topic + channel | - |
| G3 | Voice: Telecaller lines feed the inbox; warm transfer; machine / phone-menu check; learning reply wait; fillers; WhatsApp voice calls | Meta enabling calling |
| G4 | Messaging: WhatsApp, Messenger, Instagram, Telegram, SMS first; then LINE, WeChat, Viber, KakaoTalk, Zalo, Apple Messages, X, Discord / Slack / Teams | Each business's own accounts |
| G5 | Website chat widget (any site) + in-app chat kits (web, iOS, Android) + API / MCP for her own bot | - |
| G6 | Email: support address via Gmail / Microsoft 365 / IMAP, threads, per-brand signature | - |
| G7 | Hand-over: rules, routing to the right person, hand-over packet, honest wait times, out-of-hours, hand-back | - |
| G8 | Workflow designer + stage history + "where is my ticket" on every channel | - |
| G9 | Clocks in business hours per time zone, solved-only-when-confirmed, reopen, reminder ladder, customer updates, digests, stuck detector | - |
| G10 | Queues, routing rules, rule engine, roles, approval chains per currency, macros, custom fields | - |
| G11 | Quality sampling, simulated-customer card, law packs per country, enterprise controls (SSO, audit, retention) | Legal sources per country |
| G12 | Layer mode on her helpdesk (Chatwoot first, then Zendesk, Freshdesk, Zoho, Salesforce, Intercom, HubSpot, ServiceNow, Jira SM) | Her helpdesk keys |
| G13 | Reports at every size | - |

Suggested order: **G0 -> G1 -> G2 -> G8 -> G9 -> G7** (a single business on one WhatsApp number already gets the full
promise: right answers, her workflow, monitoring, hand-over), then G5 + G6, G3, G4, G10, G11, G12, G13.

---------------------------------------------------------------------------------------------------------------------

## 13. Decisions only the owner can make

1. Order: start with G0 -> G2 + G8 -> G9 -> G7 as above, or channels first?
2. Website chat widget and in-app kits for ANY site / app (not only Hoola-made) - yes / later.
3. Which messaging apps after the first five (suggest LINE, WeChat, Viber, Apple Messages).
4. Which helpdesk first for layer mode (suggest Chatwoot, then Zendesk + Freshdesk).
5. Enterprise controls (SSO, audit export, custom roles) as a paid add-on or inside the package.
6. Support and Telecaller share ONE knowledge store from now on (recommended).
7. Hosting outside India (a second server region) for EU / US customers who require it - later or now.

## 14. Not verified / risks, said plainly

- No helpdesk vendor API, WeChat / LINE / Kakao / Zalo / Viber / Apple Messages, or WhatsApp Calling has been called
  from here; each needs the business's own account and approval, and their rate limits decide speed.
- Law packs need a checked source each; many countries start as "check this".
- One server today: speed and data location for far-away customers are limited until there is a second region.
- Routing and trust levels need real volume to tune; first versions are rules she can read, not a model.
- Built: G0 (v0.999.85: setup questions, profile, 15 industry packs), G1 (v0.999.86: one business brain), G2 (v0.999.87: the answer engine), G8 (v0.999.89: her ticket workflow), G9 (v0.999.94: watching every ticket until it is truly solved - working hours, customer confirmation, reopening, reminder ladder, updates, list per person, stuck reasons), G7 (v0.999.95: handing a customer to a person - rules, packet, honest wait times, out of hours, take / hand back), G4 (v0.999.97: 12 messaging apps on her own accounts - Telegram, Messenger, Instagram, SMS, LINE, Viber, Slack, X, Zalo, KakaoTalk, WeChat), G5 (v0.999.99: website chat, hosted chat page, contact form, her app API + signed webhook), G6 (v0.999.100: support email over IMAP / SMTP or forwarding, threads, ticket replies, no loops), G3 (v0.999.103: phone calls on the desk, warm transfer with a whisper, machine / phone-menu check, learned reply wait, idle / hold / fillers, WhatsApp calls declined with a call-back - their voice not built), G10 (v0.999.105: people with shifts, queues, routing, a rule engine, roles, money approval chains on one-time links, macros with actions, custom fields, saved views), G11 (v0.999.108: answer sample with weak topics dropping to drafts, pretend customers + replay, law rows with sources, AI disclosure, customer data export / erase / retention, audit log), G12 (v0.999.110: Hoola on top of Chatwoot, Zendesk, Freshdesk, ServiceNow and Jira Service Management - sort, suggested replies as notes, summaries, close by her rule, reminders, where-is-my-ticket; Zoho / Salesforce / HubSpot / Intercom not built). Every other phase waits for her GO.
