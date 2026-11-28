# Chatwoot, read for the Customer Support scale plan (21 Nov 2026)

Owner: "https://github.com/chatwoot/chatwoot.git --- FIRST READ THIS REPO" (after docs/SUPPORT_SCALE_PLAN.md).
Read at commit 5d1afdf (20 Nov 2026), shallow clone, Ruby on Rails + Vue. Nothing copied into Hoola.

## Licence (decides what we may take)
- Everything OUTSIDE `enterprise/` = MIT (Expat). Ideas and even code may be reused with the notice.
- `enterprise/` = Chatwoot Enterprise licence: production use only with a paid Chatwoot subscription; changes belong to
  Chatwoot. Their AI agent (Captain), SLA policies, custom roles, agent capacity, SAML, audit logs live here.
  RULE for Hoola: read enterprise/ for ideas only, never copy code, never port a file. (We write Python anyway.)

## What Chatwoot is
An omnichannel support desk: one inbox for web widget, email, WhatsApp, Facebook, Instagram, Telegram, LINE, SMS, Twilio,
TikTok, X, plus an API channel; teams, assignment, automation, macros, help center, reports. Self-hostable. It is the
closest open model of the "Several teams / Enterprise" columns of our plan.

## Their model (MIT part) and what it means for us
| Chatwoot | What it is | Hoola today | Take for the plan |
|---|---|---|---|
| Inbox + Channel::* | one inbox per channel, a polymorphic channel row; inbox_members = who works it | one Seva inbox, channel is a column | S3: an inbox per channel / brand, members per inbox |
| Conversation status open / pending / snoozed / resolved; priority low-urgent | | Seva status new / open / pending / on_hold / resolved / closed | add `snoozed until` (reopens by itself) |
| Team + team_members; conversation.team | | TeamMember (manager / staff) only | S4: teams = our queues |
| AssignmentPolicy: round robin, earliest_created or longest_waiting first, skip backlog older than N h, fair-distribution limit per window | auto_assignment/*, rate_limiter | assignee by hand / tool | S4 routing: same knobs, as data |
| AutomationRule: event (conversation created / updated / message created) + conditions (content, status, inbox, team, priority, labels, language, country, email, referer...) + actions (assign team / agent, label, priority, status, snooze, send message / email / webhook, private note, transcript); optional delay 10 min - 30 days | the general rule engine | Seva has fixed rules in code | S4/S5: one rule engine (when / if / then) for routing, auto-replies, escalation; delayed rules = "if still open after 2 h" |
| Macro | a named list of actions run by an agent in one click | saved replies (text only) | saved replies grow into macros (reply + label + status + assign) |
| CannedResponse | short-code text | saved replies | same |
| Label, CustomAttributeDefinition, CustomFilter | tags, typed custom fields on contact / conversation, saved views | categories only | S4: custom fields per profile (plan, area, order no.) + saved views |
| WorkingHour per inbox + out-of-office message | | seva morning_time, Employee hours | S4: hours per queue, out-of-hours reply |
| CsatSurveyResponse + templates | rating after resolve | Seva CSAT 1-5 | same |
| Portal / Category / Article (help center), per locale, own domain | public knowledge base | knowledge is private (answers only) | new: optional public help center from approved knowledge |
| AgentBot (webhook bot per inbox) | an outside bot answers first, hands over | Hoola is the bot | layer mode the other way round: Hoola as an AgentBot inside a customer's Chatwoot |
| Webhook, Integrations::Hook, PlatformApp, API channel | events out, apps in | — | S6: events out to her systems |
| Web widget with HMAC identity (`hmac_mandatory`, identifier_hash), allowed_domains, continuity via email | | — | S3 widget: copy the IDEAS - signed visitor identity so a logged-in customer sees only their own threads; allowed domains |
| ReportingEvent + rollups | first response, resolution, reply time events -> fast reports | Seva computes on read | S8: write events, roll up per day / queue / agent |
| DataImport / DataExport, contact merge, companies | | — | S7 export, merge duplicates |

## Enterprise (ideas only)
- SlaPolicy: first response / NEXT response / resolution thresholds, `only_during_business_hours`, applied per conversation
  with SlaEvents (missed first reply etc.). Ours lacks NEXT response time and business-hours-only clocks: add both (S4).
- AgentCapacityPolicy + InboxCapacityLimit: max open conversations per agent per inbox, exclusion rules. Add to S4 routing.
- CustomRole: permissions as a list (conversation manage, contact manage, report view...). S4 roles become permission lists.
- AccountSamlSettings: SAML SSO (S7).
- Captain (their AI): an Assistant per product with description, response guidelines, GUARDRAILS, scenarios (sub-agents
  with their own instruction + tools, reached by `handoff_to_*`), documents -> FAQ, tools (faq_lookup, handoff to a
  person, resolve, label, priority, private note, HTTP / MCP tools, email verification by code), a playground, Copilot
  for agents (reply suggestions, review findings), FAQ SUGGESTIONS mined from resolved conversations (question + answer +
  how many conversations it came from, open / approved / dismissed), auto-resolve after inactivity, a FALSE-PROMISE
  check on every reply (decision safe / future_work_promise; reasons "future callback or email", "background escalation
  promise"...), a channel length limit with a rewrite.

## What Hoola already does better / differently
- Money and exceptions: Chatwoot has no approval-by-tap for refunds; ours is the core law (keep).
- Answers only from APPROVED knowledge with the source named, unknown = never a guess (Captain is instructed to look up
  first but can still answer from the model). Keep ours stricter.
- Live lookups bound to the customer's OWN number (Telecaller knowledge) - Captain's HTTP tools are general; ours are
  narrower on purpose.
- India rules (E-Commerce 48 h acknowledgement, RBI / IRDAI / TRAI timelines) built in.
- Voice: the Telecaller answers calls; Chatwoot is text.

## Changes to docs/SUPPORT_SCALE_PLAN.md from this read
1. S4 gets: assignment policy knobs (round robin / least busy, earliest vs longest waiting, skip backlog older than N h,
   a fair limit per hour), capacity per agent per queue, NEXT-response time and business-hours-only reply clocks,
   snooze-until, custom fields + saved views, permission-list roles.
2. One rule engine (event + conditions + actions, optional delay) replaces hard-coded routing / escalation; it also
   drives "still open after 2 h -> supervisor".
3. Saved replies grow into MACROS (several actions in one click).
4. S2 gets FAQ suggestions mined from solved tickets (question + answer + how many tickets), approved / dismissed by her
   - the gaps list today only shows questions with no answer.
5. Every AI reply gets a FALSE-PROMISE check (no "we will call you back / I have escalated" unless a real ticket / task
   exists) - Hoola's draftcheck idea applied to customer replies.
6. S3 web widget: signed visitor identity (HMAC) + allowed domains.
7. S6 layer mode adds Chatwoot itself (MIT, self-hosted by many Indian SMBs): Hoola joins a customer's Chatwoot as an
   Agent Bot / via its API - the cheapest helpdesk to support first, since its API is open and free to run.
8. New optional: a public help center built from approved knowledge (per language, her domain).
