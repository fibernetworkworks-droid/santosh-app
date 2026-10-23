# WIRING for product
summary: Product Sahayak (product manager: Feedback themes + Seva tickets / unanswered questions + Telecaller objections + her ideas / competitor notes -> an opportunity backlog with evidence, RICE / ICE only with her numbers, Kano, Now / Next / Later with capacity + dependencies + suggested plan; specs with Given / When / Then + dev / QA tasks; release notes in Hinglish + English with Play 500 / App Store 4,000 text and a Keep a Changelog entry from her words, shipped items and merged PRs; GitHub release / public page only on her tap; before / after for shipped items)
db: app.product.models
router: app.product.api            (make_router(require_key, current_tenant); key-protected routes under /api/product; ONE public route GET /api/product/page/{token} (random 24-char token made only on her publish tap, read-only HTML, CSP default-src 'none', noindex). Include it like the others: app.include_router(_product_router(require_key, current_tenant)))
tools: app.agent.product_tools     (PRODUCT_TOOLS / PRODUCT_LABELS / PRODUCT_HANDLERS) ; voice: yes (product, product_dekho)
employee: duty product_work = [product, product_dekho, file_read] {label "Product manager", say "feedback / support / sales se roadmap, specs aur release notes (bahar bhejna aapke tap se)"} ; role product_manager {label "Product manager", duties [product_work, records, research, reminders]} ; preset product {label "Product / app team", role product_manager, rules ["Reach / effort / revenue ke number sirf owner se, khud kabhi mat gadho", "Roadmap ya release notes bahar sirf owner ke tap se"]} ; READ tools: [product_dekho]
  - staff (staff:<id>) may add ideas / opportunities, score with numbers the owner gave, write specs / release drafts; the tool refuses customer actors entirely and keeps settings / kpi / plan apply=true owner-only. Publishing is never done by a tool: only POST /api/product/publish/{id}/decide (her app tap, card hash). Any token-looking text in tool args is refused (token only via PUT /api/product/github from the app).
push: product_publish -> ("Bahar bhejna hai: aapki haan", "{say}")
push: product_day -> ("Aaj ka product note", "{say}")
push: product_backlog -> ("Nayi dikkatein backlog mein", "{say}")
  (product_spec, product_release: no push; publish only)
worker: app.product.service.tick   (call every few minutes, e.g. `await asyncio.to_thread(product.tick)`; once a day after her morning_time per tenant that has product settings: harvest without a model call, saves 30-day before / after results, one product_day card only when there is news)
prompt: PRODUCT: feedback / support / sales se "kya banaye" -> `product action=harvest` aur `product_dekho what=backlog|roadmap`. Score (reach, impact, confidence, effort) sirf UNKE number se: khaali ho to unka andaaza poochho, kabhi khud mat bharo. Spec = `product action=spec` (Given / When / Then); release notes = `product action=release`; bahar (GitHub / public page / graahak) bhejna sirf card se (`action=publish`), kehna "aapke tap ka card bheja hai". GitHub token kabhi chat mein mat lo: app ke Niyam mein.
persona: Product ke kaam mein reach / effort jaise number kabhi khud mat bolo, unka andaaza poochho; release notes ya roadmap bahar bhejne ko "card bheja hai, aap tap kijiye" kaho.
flutter: ProductScreen in lib/ui/product_screen.dart (+ ProductOppPage, ProductSpecPage, ProductReleasePage) ; profile tile title "<name> · Product manager" subtitle "Feedback se roadmap, specs, release notes" icon Icons.route_rounded ; cards: product_publish -> ProductPublishCard (also in calls: yes; key by data['id'], updated in place) ; product_backlog -> ProductNoteCard (also in calls: no) ; product_spec -> ProductNoteCard (also in calls: no; key by data['spec']['id']) ; product_release -> ProductNoteCard (also in calls: no; key by data['release']['id']) ; product_day -> ProductNoteCard (also in calls: no). All widgets take (app:, data:) and use only `app.api!.call(...)`, `Native.openExternal`, `Clipboard`.
features: product
env: none (uses PUBLIC_BASE_URL for the public page link when set; GitHub token per owner in table product_keys, sealed with the bazar vault)
requirements: none (httpx, openpyxl, python-docx already present)
android: none
neighbours: devsahayak (Developer Sahayak) and qa (QA Sahayak) can take `product.service.tasks(tenant, spec)` -> {dev_tasks [{id, title, story, acceptance[], events[]}], qa_cases [{id, given, when, then}], gherkin} (also GET /api/product/specs/{ref}/tasks and the .feature file from spec_files). docwriter can reuse `spec_markdown` / release `changelog`. appreview / appmaker / site: release_new reads App Sahayak `AppProject.versions` (settings.app_ref) and Website `SiteVersion.note` (settings.site_ref) as change sources.
claude_md: |
  ## v0.1xx Product Sahayak: Hoola as the product manager (feedback -> roadmap -> specs -> release notes)
  - Owner's spec (Employee page "Product manager"): turns feedback into a roadmap, writes specs, prepares release notes. House rule:
    anything going OUTSIDE (GitHub release, public roadmap / notes page, customers) is a card she taps.
  - Server `server/app/product/{rules,models,service,api}.py`, tools `product` / `product_dekho` (`agent/product_tools.py`, chat +
    calls), duty `product_work`, role `product_manager`, preset `product`, API `/api/product/*`, app Profile > Product sahayak
    (`lib/ui/product_screen.dart`: Aaj / Backlog / Roadmap / Specs / Release / Niyam + ProductOppPage / ProductSpecPage /
    ProductReleasePage), cards ProductPublishCard (`product_publish`), ProductNoteCard (`product_backlog`, `product_spec`,
    `product_release`, `product_day`). Tests `server/tests/test_tech_product.py` (9).
  - Inputs: `harvest` reads Feedback Sahayak `themes` (negative themes seen 2+ times or urgent: count, people, masked quotes,
    trend, rupees only from her own order value), Seva `report` (ticket categories 2+, unanswered Gyaan questions asked 2+, quotes
    masked), Telecaller `objection_library` (2+ calls); her ideas in words / a file (docread) and competitor notes (model extracts
    customer problems, else one per line). Every source has a key ("feedback:delivery:neg", "seva:delivery") so a re-harvest
    refreshes numbers instead of doubling; a new item that reads like an open one (word overlap / difflib >= 0.75) joins it;
    `duplicates` suggests merges (>= 0.55), `merge` carries evidence, keys, solutions and dependencies.
  - Opportunities (O-001) are customer problems (opportunity solution tree: solutions listed under them, "compare 3+"), scored
    RICE (reach x impact 3/2/1/0.5/0.25 x confidence 100/80/50 % / effort person-months; "2 hafte" / "10 din" understood) or ICE
    (1-10 each) ONLY with her numbers: a missing one = score blank + "Aapka andaaza?" line; `use_seen` lets HER accept "people seen
    in the evidence" as a reach floor (said so). Confidence < 50% = moonshot note. Kano from customers' functional / dysfunctional
    answers (standard table) or her pick.
  - Roadmap Now / Next / Later: her capacity per bucket (person-months), themes, goals = her KPIs / north star; problems listed:
    over capacity, effort missing, an item before its dependency, dependency cycles, items not tied to a KPI. `plan` suggests a
    placement by score (Kano must-be first), capacity and dependencies (unscored items listed, never guessed); `apply` only on her
    word. Word / Markdown / Excel; a public roadmap shows titles only (no scores / quotes / numbers, "plan badal sakta hai").
  - Specs (SP-001): model JSON from the opportunity + evidence + her note + KPIs (only her facts, [blank] for missing), else an
    honest template with blanks; sections problem, users, goals, non-goals, user stories with Given / When / Then, flows, edge
    cases, analytics events (snake_case), metrics, risks, open questions, rollout; checks (no story / criteria / G-W-T gaps /
    [blank] = draft; numbers not in the evidence flagged; customer phone / email flagged); versions kept (20); her edits and
    "badlav bolo"; files Word + Markdown + Gherkin .feature; `tasks` = dev task list + QA cases for the Developer / QA Sahayaks.
  - Releases (R-001): her lines + shipped opportunities + merged PRs (her fine-grained GitHub token typed only in the app, sealed,
    `GET /repos/{o}/{r}/pulls?state=closed` filtered by merged_at since the last release) + App / Website Sahayak versions;
    duplicates dropped; internal work (chore / deps / refactor / CI / tests labels) only in the changelog; Keep a Changelog types
    (Added / Changed / Deprecated / Removed / Fixed / Security) by words; customer notes Hinglish + English (model, else template)
    without PR numbers / handles / commit ids; Play "What's new" <= 500 chars per language (whole lines + "aur bhi"), App Store
    <= 4,000, internal changelog with PR links. Checks: [blank], personal data (block), promises ("guarantee", "100%"), numbers not
    in the changes.
  - Publishing: `publish_request` (release or roadmap; dest github (POST /repos/{o}/{r}/releases, needs Contents: write) | page
    (Hoola public page, random token, CSP default-src 'none', noindex, unpage to take it down) | copy (she pastes into Play
    Console / App Store / WhatsApp)) -> `product_publish` card with a hash of the exact text; ONLY `POST
    /api/product/publish/{id}/decide {yes, hash}` (by_tap) sends; once; editing the notes makes the card stale; a GitHub refusal =
    failed + back to draft. Published release marks its opportunities shipped.
  - Metrics: north star + up to 12 KPIs she defines, numbers she reports (`metric`); `before_after` for a shipped item = the same
    feedback theme / ticket category in the 30 days before vs after (scaled when fewer days passed) + her KPI averages before /
    after, said as "saath-saath hua, sirf isi wajah se pakka nahi"; saved when 30 days have passed (worker).
  - Never: inventing reach / effort / revenue / dates, customer names / phones in specs or notes, publishing without her tap,
    taking a GitHub token in chat, writing to her repo except the release she tapped.
  - Research (23 Oct 2026): RICE (Sean McBride, Intercom blog Jan 2018; scales via resources.rework.com/libraries/project-management/
    rice-prioritization), ICE (Sean Ellis), Kano model (Noriaki Kano 1984, standard evaluation table), opportunity solution tree
    (Teresa Torres, producttalk.org/opportunity-solution-trees, Dec 2023: outcome -> opportunities = needs not solutions -> 3+
    solutions -> assumption tests), Keep a Changelog 2.0.0 (keepachangelog.com, 7 Jun 2026: six change types, newest first,
    dated, for humans), Google Play "What's new" 500 characters per language incl. spaces (deku.posstree.com, 25 May 2026), App
    Store Connect "What's New in This Version" 4,000 / promotional text 170 (developer.apple.com App Store Connect help),
    GitHub REST releases (Contents read to list, write to create; generate-notes endpoint exists) docs.github.com/en/rest/releases
    and pulls list (merged_at). PRD practice: problem, goals and non-goals, user stories with testable Given / When / Then,
    analytics events, risks, open questions, rollout (common 2026 PRD templates).
not_verified: Flutter screen + cards could not be compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/product_screen.dart (uses api.call, Glass(border:), Pill(fg:, bg:), Caption, GradientButton(height:), Native.openExternal). GitHub calls only against a fake transport (MockTransport): real fine-grained tokens report `permissions.push` for the user, not the token, so `can_write` may be optimistic; a 403 on release creation is reported plainly. Model prompts (idea extraction, spec, release notes, spec revise) were tested only via stubs / the no-model fallbacks. Feedback / Seva / Telecaller reads use their public service functions (themes, report, gaps, objection_library) and their tables (FbItem, SevaTicket) for before / after; if those modules change shape, harvest degrades to a note ("... nahi padh paya"). Push titles are suggestions for push.PUSH_KINDS.
