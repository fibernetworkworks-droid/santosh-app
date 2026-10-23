# WIRING for seva
summary: Seva Sahayak (customer support agent: instant answers only from her Gyaan with source + confidence, tickets with SLA timers / duplicates / customer status line, refunds and exceptions only on her tap with fingerprint for money, macros in 4 languages, FRT / resolution / deflection / CSAT / gaps, morning note)
db: app.seva.service            (tables seva_settings, seva_entries, seva_macros, seva_tickets, seva_exceptions, seva_questions, seva_counters)
router: app.seva.api            (make_router(require_key, current_tenant); all routes under /api/seva, none public)
tools: app.agent.seva_tools     (SEVA_TOOLS / SEVA_LABELS / SEVA_HANDLERS) ; voice: yes ("seva", "seva_dekho" in VOICE_TOOL_NAMES; NOT the biz_seva_* tools)
  - SEVA_HANDLERS also contains the 5 customer tools (biz_seva_answer, biz_seva_ticket, biz_seva_status, biz_seva_request, biz_seva_rate) so dispatch finds them; SEVA_TOOLS (offered to her model) does NOT contain them.
  - Customer tools: add `app.agent.seva_tools.BIZ_SEVA_TOOLS` to `employee.inbox.BIZ_TOOLS` (put biz_seva_answer FIRST in the list) and their names to `employee.roles.CUSTOMER_TOOLS`. Handlers are already in SEVA_HANDLERS (BIZ_SEVA_HANDLERS = just those five).
  - Suggested one line for `employee.inbox._system` (after the "Kabhi nahi" line): "Har sawaal par pehle biz_seva_answer: jawab sirf usme se (source wala), 'unknown' par andaza nahi, biz_handover; refund / chhoot / maafi ki baat par biz_seva_request, waada kabhi nahi; status poochhein to biz_seva_status (sirf unke apne ticket); band ticket ke baad 1-5 ka jawab aaye to biz_seva_rate."
employee: duty support_work = [seva, seva_dekho] ; duty customers += [biz_seva_answer, biz_seva_rate] ; duty tickets += [biz_seva_ticket, biz_seva_status, biz_seva_request] ; role support_agent {label: "Customer support (Seva)", say: "Sawaalon ka turant jawab apne Gyaan se, shikayat ka ticket + samay-seema, graahak ko haal batana; refund / niyam ke bahar sirf aapki haan se", duties: [customers, tickets, support_work, reminders, records, email]} ; preset support {label: "Customer support desk", role: support_agent, kind: "shop", after_hours: "note", about_hint: "Timings, daam / plans, delivery, refund / exchange niyam, warranty, contact"} ; also add support_work to roles support_collect and the isp / ecommerce-like presets if wanted ; READ tools: [seva_dekho, biz_seva_answer, biz_seva_status, biz_seva_request]
  - Why biz_seva_request is READ: it only creates a card; the money / exception decision is a separate tap (`/api/seva/exceptions/{id}/decide`). Classing it as an action would make her approve twice at "seekh" trust. biz_seva_ticket / biz_seva_rate stay "action" like biz_complaint.
push: seva_exception -> ("Aapki haan chahiye: {kind_label}", "{say}")
push: seva_sla -> ("Shikayat ka samay: {ticket}", "{text}")   (push only when payload.breach is true, or for every one if simpler)
push: seva_ticket -> ("Nayi shikayat {number}", "{customer}: {text}")   (push only when payload.event == "new" and payload.priority == "urgent")
push: seva_day -> ("Seva: aaj", "{text}")
worker: app.seva.service.tick   (call once a minute; adopts Hoola Network / older biz_complaint tickets, SLA warnings at 80% and breach (once each), morning note at her morning_time)
prompt: SEVA: graahakon ke sawaal sirf unke Gyaan (seva kb, FAQ + niyam) se, source ke saath; jo Gyaan mein nahi woh andaza nahi, owner ko do aur `seva_dekho what=gaps` mein dikhta hai. Asli dikkat = `seva action=ticket` (priority + SLA khud lagta hai, ek hi graahak ki doosri baar wali shikayat usi mein judti hai). Refund / chhoot / maafi / niyam ke bahar kuch bhi = `seva action=exception` sirf card; faisla sirf owner ki tap, Hoola paise kabhi nahi bhejta. Andar ke note graahak ko kabhi nahi.
persona: Graahak seva (seva / seva_dekho): shikayat darj karo, haal batao, Gyaan mein jawab jodo; refund ya niyam ke bahar ki baat par sirf card bhejo, "haan" kabhi khud mat kaho.
flutter: SevaScreen in lib/ui/seva_screen.dart ; profile tile title "<name> · Customer support" subtitle "Gyaan se turant jawab, shikayat + samay-seema, refund aapki haan se" icon Icons.support_agent_rounded ; cards: seva_exception -> SevaExceptionCard (also in calls: yes) ; seva_ticket -> SevaTicketCard (also in calls: no) ; seva_sla -> SevaTicketCard (also in calls: no) ; seva_day -> SevaDayCard (also in calls: no)
  - Cards for one exception should be updated in place by payload.id (the same id is published again after her decision).
  - Uses `widget.app.api!.call(method, path, body:, query:, timeout:)` (the coordinator's generic helper), `Api.uploadFile` (kb file import), `Native.approveKeySign` and `ApiException` from api.dart. Imports file_picker + url_launcher (already in pubspec).
features: seva
env: none
requirements: none
android: none (uses the existing ApproveKey.kt fingerprint signing through Native.approveKeySign)
approvekey: no edit needed. seva signs its own challenges with approvekey's table and checker (`ApproveChallenge` kind "seva", `approvekey._check`), via `POST /api/seva/exceptions/{id}/challenge`. Optional later: add kind "seva" to approvekey.card_digest / needed / challenge (card = app.seva.service.approval_card, needed = app.seva.service.money_card) so the generic `/api/approvekey/challenge` works too.
claude_md: |
  ## v0.1xx Seva Sahayak: Hoola as the customer support agent (answers from her Gyaan, tickets with SLA, exceptions on her tap)
  - Owner's spec (Employee page "Customer support agent"): answers common questions instantly -> creates tickets for real problems
    -> tells customers the status -> waits for her Haan on REFUNDS AND EXCEPTIONS (anything outside her written policy).
  - Server `server/app/seva/{rules,service,api}.py`, tools `seva` / `seva_dekho` (`agent/seva_tools.py`, chat + calls) + customer
    tools `biz_seva_answer` / `biz_seva_ticket` / `biz_seva_status` / `biz_seva_request` / `biz_seva_rate` in the business WhatsApp
    inbox (BIZ_TOOLS, CUSTOMER_TOOLS), role `support_agent` + preset `support`, duty `support_work`, API `/api/seva/*`, app Profile >
    "<name> · Customer support" (`lib/ui/seva_screen.dart`: Aaj / Shikayat / Gyaan / Jawab / Niyam / Hisaab, `SevaTicketPage`), cards
    `SevaExceptionCard` (also in calls), `SevaTicketCard` (seva_ticket, seva_sla), `SevaDayCard`. Tests `server/tests/test_seva_seva.py` (8).
  - Gyaan (knowledge base): FAQ + policy entries in her words (live at once) or imported from her file (docread) / website page
    (web.open_website) / pasted text as DRAFTS she approves (model extraction with a Q:/A: fallback; an extracted answer with a number
    not in her text is dropped). `answer` = word overlap with Hinglish / Hindi / Marathi synonyms (+ FastEmbed meaning when present):
    >= 0.6 answered (her text, optionally re-phrased in the customer's language by the model; a phrasing that adds a number is thrown
    away) with the source + confidence; 0.38-0.6 clarify (ask which one); below = unknown -> never a guess, handover; OTP / PIN / card
    talk refused; refund / discount words add "biz_seva_request, no promise". Every question logged masked (seva_questions):
    deflection, top questions, `gaps` (unanswered, grouped) shown in the app with "Jawab do".
  - Macros: one text -> Hinglish / Hindi / Marathi / English (a translation that changes numbers or placeholders is dropped); only
    {name} {ticket} {status} {business}; usable only after her approval; an empty placeholder refuses to send.
  - Tickets (seva_tickets; number from the Hoola business counter so Network tickets and these never clash): channel whatsapp | hoola |
    phone | walkin | email | other, category + priority guessed from words (aag / fraud / paise kat gaye / court = urgent; 3 din se /
    baar baar / gussa = high), SLA per priority from her preset (shop / isp / ecommerce / clinic) or her own hours; the law is the outer
    limit (E-Commerce Rules 2020: 48 h acknowledgement, 1 month redress when she sells online; DPDP 90 days for data complaints).
    Clock pauses while status = pending (waiting on the customer); auto-acknowledgement is not a first response; warnings at 80% and
    breach once each (`seva_sla`). Same customer + similar text within 7 days = joined to the open ticket; merge only within one customer.
    Internal notes never reach the customer; status line + her public line do (business WhatsApp via inbox.notice_by_phone inside Meta's
    window, Hoola Network via business.update_ticket, else a wa.me draft she sends). Older `biz_complaint` / Network tickets are
    adopted once. WhatsApp tickets also write a hoola_tickets row so `biz_ticket_status` still works. CSAT 1-5 asked after resolve.
  - Exceptions (X-0001): refund / waiver / goodwill / replacement / extension / other, checked against HER written policy (refund_days,
    refund_max, replace_days, goodwill_max) -> within / outside with reasons; same pending ask never twice. `seva_exception` card;
    ONLY `POST /api/seva/exceptions/{id}/decide` (her tap, card hash must match) decides; a money card needs her phone's fingerprint once
    a phone key is active (own challenge `/challenge`, kind "seva", verified with approvekey's checker); she can approve less, never more.
    Hoola tells the customer the decision; "Maine paise bhej diye" (her own app) -> customer told with the ref tail. Money never moves.
  - Numbers (`report`): first response / resolution median (pauses out), % within SLA, deflection = KB answers / (answers + chat
    tickets + unanswered), CSAT % 4-5, by category, top questions, exceptions asked / approved / amount. Morning note `seva_day`.
  - Research (22-23 Oct 2026): Consumer Protection (E-Commerce) Rules 2020 grievance officer for e-commerce entities AND marketplace
    sellers, acknowledge 48 h, redress 1 month (indialaw.in; lakshmisri.com); NCH 1915 / NCH 2.0 (17 languages, WhatsApp) and e-Jagriti
    from 1 Jan 2025 (storyboard18.com Jan 2026); DPDP Rules 2025 notified 13-14 Nov 2025, grievances within 90 days, core duties from
    13 May 2027 (Khaitan ERGO Nov 2025); RBI TAT circular RBI/2019-20/67 (20 Sep 2019): failed UPI / IMPS reversal T+1 else Rs 100 a day
    (rbi.org.in Id=11693) - said to the owner as a fact, never as a promise; TRAI broadband QoS (2006: fault next working day / 3 days,
    rebates after 3 / 7 / 15 days; 2024 Regulations 06 of 2024 in force 1 Oct 2024) -> ISP preset; WhatsApp Cloud API pricing
    (developers.facebook.com, Oct 2026): 24 h window, from 1 Oct 2026 1,000 free service messages a month then charged, utility templates
    inside the window charged again. Support practice: SLA per priority, pause on pending, ack != first response, CSAT right after
    resolution, deflection and unanswered questions as KB gaps.
not_verified: Flutter screen not compiled here (no SDK): check CI annotations for lib/ui/seva_screen.dart (uses api.call which the coordinator adds). The full WhatsApp loop (inbox.answer choosing biz_seva_answer first) is not tested end to end because BIZ_TOOLS / CUSTOMER_TOOLS / HANDLERS are not wired yet; the handlers are tested directly with customer actors. Model phrasing / extraction / translation run only with a real model (tests use the no-model path and scripted JSON). Fingerprint path tested with a software EC key, not a real phone. Real Meta delivery of notices (window / charges from 1 Oct 2026) not tried.
