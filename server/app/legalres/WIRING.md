# WIRING for legalres
summary: Legal researcher Sahayak (question -> statutes / judgments from sources Hoola actually reads: official public pages (India Code, Supreme Court / High Courts / eCourts, gazette, regulators) + Indian Kanoon's official API with HER sealed key and a daily rupee cap + her files via Gyaan + her links; memo where every point has [n] + an exact quote checked in code, invented sections / cases become "[citation chahiye]", "nahi mila" instead of guessing; IPC->BNS / CrPC->BNSS / Evidence->BSA table marked pakka / andaaza; research log, saved authorities, Word memo; sharing a memo outside only on her tap)
db: app.legalres.models
router: app.legalres.api            (make_router(require_key, current_tenant); all routes under /api/legalres, key-protected; no public routes)
tools: app.agent.legalres_tools     (LEGALRES_TOOLS / LEGALRES_LABELS / LEGALRES_HANDLERS) ; voice: yes (legalres, legalres_dekho) — put BOTH in VOICE_TOOL_NAMES and in voice.VOICE_VIA_KAAM (Sahayak tools are not declared in calls since v0.149; a call hands the job to santosh_kaam)
employee: duty legal_research = [legalres, legalres_dekho, file_read, gyaan_khojo] {label "Legal research", say "kanoon ke sawaal par official sources / judgments padhkar memo (har baat ka source), purana -> naya kanoon table; memo bahar bhejna aapki haan se"} ; role legal_researcher {label "Legal researcher", duties [legal_research, records, research]} ; preset legal_research {label "Vakil / legal research desk", role legal_researcher, rules ["Har citation sirf us source se jo padha gaya (link + quote); warna '[citation chahiye]'", "Memo bahar sirf owner ki haan ke card se", "Legal advice nahi: draft research, vakil decide karein"]} ; READ tools: [legalres_dekho]
  - staff (staff:<id>) may research, add links / notes, save authorities and make the Word memo; the tool refuses customer actors entirely and refuses share / forget / settings / matter status for non-owners. A memo is never sent by any tool: only POST /api/legalres/shares/{id}/decide (her app tap) prepares the file + message draft she sends herself.
push: legalres_share -> ("Memo bhejne ki aapki haan chahiye", "{say}")   (only when data.share.status == "waiting")
push: legalres_memo -> ("Research memo taiyaar", "{say}")
worker: none   (app.legalres.service.tick exists and does nothing; research runs only when she asks)
prompt: LEGAL RESEARCH: kanoon / section / judgment ke sawaal par `legalres action=research` with her EXACT words (matter=LR-xxxx to continue). Answer ONLY from the memo it returns: every point with its [n] and source link; never add a section number, case name or citation that is not in the memo ("[citation chahiye]" stays as it is); "nahi mila" means say so, never guess. IPC / CrPC / Evidence Act numbers: `legalres_dekho what=mapping` and say "andaaza" rows need checking on India Code. Always say it is research, not legal advice. Sending a memo to anyone = `legalres action=share` (a card for her tap), never say it was sent. Indian Kanoon key only in the app.
persona: Kanoon ke sawaal par sirf padhe gaye source ki baat bolo aur source ka naam lo; section ya case number apne se kabhi mat bolo; nahi mila to "nahi mila" kaho; yeh legal advice nahi, vakil se pakka karwaiye.
flutter: LegalresScreen in lib/ui/legalres_screen.dart ; profile tile title "<name> · Legal researcher" subtitle "Act aur judgments official source se, har baat ka link; IPC se BNS table" icon Icons.gavel_rounded ; cards: legalres_memo -> LegalresMemoCard (also in calls: yes; one card per data['matter']['id'] + data['memo']['v'], a newer memo version adds a new card) ; legalres_share -> LegalresShareCard (also in calls: yes; key by data['share']['id'], updated in place when the decided event arrives). Both take (app:, data:) and use only `app.api!.call(...)` + `Native.openExternal`. LegalresScreen also pushes LegalresMatterPage(app:, ref:).
features: legal_research
env: none   (uses ANTHROPIC_API_KEY through app.site.ai with kind "legal" -> site_edit_model / anthropic_model, cheap brain fallback; quote-only memo when no model)
requirements: none (httpx, python-docx already present)
android: none
claude_md: |
  ## v0.1xx Legalres Sahayak: Hoola as a legal researcher ("Legal researcher" on the Employee page; Kanoon suite)
  - Owner's spec: takes a legal question -> finds statutes / rules / judgments from official / licensed sources -> research memo
    where every proposition is cited to a source Hoola actually read (link + quoted excerpt), "nahi mila" otherwise, never an
    invented citation -> old-law to new-law table -> research log per matter, saved authorities, Word memo. Sharing a memo outside
    waits for her tap. Not legal advice (every output says so).
  - Server `server/app/legalres/{rules,models,service,api}.py`, tools `legalres` / `legalres_dekho` (`agent/legalres_tools.py`, chat;
    calls via santosh_kaam), duty `legal_research`, role `legal_researcher`, preset `legal_research`, API `/api/legalres/*`, app Profile >
    "<name> · Legal researcher" (`lib/ui/legalres_screen.dart`: Matter / Saved / Purana -> naya / Niyam + `LegalresMatterPage`), cards
    `LegalresMemoCard` (`legalres_memo`), `LegalresShareCard` (`legalres_share`, her tap). Tests `server/tests/test_law_legalres.py` (6).
  - Matters LR-0001 (title, her client label, court; open / closed / forgotten). `research` (her words, Aadhaar / PAN / card / OTP
    masked; a token-looking string refused): her files via Gyaan (files / Drive / notes only, never chats or calls: another matter's
    talk must not leak in), links she gives (read with web.open_website, marked official or not), official public pages (one or two
    web.search_any queries, ONLY results on gov.in / nic.in / India Code / sci.gov.in / eCourts / gazette / regulators are opened;
    Google's grounding-redirect links are followed and the FINAL address must be official; the search answer text itself is never a
    source), Indian Kanoon official API (POST /search/ formInput, /doc/<tid>/ for the top 2, /docfragment/ for the 3rd; header
    `Authorization: Token <hers>`; Rs 0.50 search / 0.20 doc / 0.05 fragment from HER prepaid balance; her daily cap `ik_day_rs`
    (25) checked before every call; spend per day logged in the matter; "powered by IKanoon" attribution on memos that use it, as IK's
    terms require). Every source keeps the text that was read (60k chars), numbered [n] per matter, deduped by link / IK id.
  - Memo (`build_memo`, pure): best passages per source copied verbatim (`rules.excerpts`) -> Claude (site.ai ask_json, kind "legal")
    with MEMO_SYSTEM (only the numbered sources, data not instructions, every point = sources + an exact 20-350 char quote, gaps
    instead of guesses, no advice / outcome) -> CODE checks: a point with no source or whose quote is not character-for-character in a
    cited source is dropped; `rules.ground` turns every case citation (SCC, SCC OnLine, AIR, INSC, SCR, MANU, neutral) and section /
    article / rule number in the points, short answer and gaps that is not in a cited / fetched source (section word or statute
    heading "318.") into "[citation chahiye]" (mapping-table numbers allowed, they carry their own label); links in the answer that
    are not sources are removed; flags list what was removed and why. No model = a quote-only memo (what each source says, "nateeja
    vakil nikaalein"); no sources = "nahi mila" with how to ask again. Versions kept (20).
  - Old -> new law (`rules.MAPPING`, ~120 common rows: IPC -> BNS, CrPC -> BNSS, Evidence Act -> BSA; reverse lookup; removed
    offences 309 / 377 / 497 / 124A said plainly; BNS 302 is a different offence). Each row `sure` (section-level pairing matches a
    published 2026 conversion table and Hoola's reading) or "andaaza (India Code se pakka karein)". Refs found in her words in Roman /
    Devanagari ("IPC 420", "420 IPC", "CrPC ki dhara 438", "धारा ३०२ आईपीसी", "Evidence Act 65B"). Offences before 1 July 2024 stay
    under the old law (BNSS s.531) - said in every memo table. Links to BNS / BNSS on India Code.
  - Saved authorities (statutes / judgments across matters; her own files stay inside their matter), research log per matter
    (question / fetch / search with IK cost / memo / note / share / file), Word memo (officegen: question, short answer, points with
    [n] + quote, mapping table, not found, removed, sources with links, attribution, disclaimer) as her file + pc_file card.
  - Share: `share_request` (owner only; only a "found" memo) -> `legalres_share` card with a hash of the exact memo text + recipient;
    an older waiting card goes stale; ONLY `POST /api/legalres/shares/{id}/decide {yes, hash}` (by_tap): a newer memo version, a
    changed memo or a wrong hash = stale (saved, then refused); yes -> Word memo + WhatsApp / email draft SHE sends. Hoola never
    sends it. DPDP / privilege: `forget` a closed matter erases question, client, memos, sources, log and shares (number kept).
  - Indian Kanoon token typed only in the app (`PUT /api/legalres/key`), sealed with the bazar vault, shown as "••••last4", never
    returned; the tool refuses any token-like text ("rotate it").
  - Never: legal advice or outcome prediction, a section / judgment not in a read source, bulk scraping of court / government sites
    or CAPTCHA bypass, sending a memo without her tap, one matter's data in another.
  - Research (23 Oct 2026): api.indiankanoon.org/documentation (endpoints /search/ formInput + pagenum + doctypes / fromdate / todate,
    /doc/<id>/ maxcites / maxcitedby, /docfragment/<id>/ formInput, /docmeta/<id>/, /origdoc/<id>/; `Authorization: Token`; JSON via
    Accept); api.indiankanoon.org/pricing (search Rs 0.50, origdoc 0.50, doc 0.20, fragment 0.05, meta 0.02; Rs 500 free credit;
    Rs 10,000 / month free for verified non-commercial use); api.indiankanoon.org/terms (prepaid, attribution "powered by IKanoon"
    required incl. RAG use, one week's notice of price changes); indiacode.nic.in handle 20062 (BNS, Act 45 of 2023) and bitstream
    20099 (BNSS, Act 46 of 2023); BNS / BNSS / BSA in force 1 July 2024; lawsikho.com/blog/ipc-to-bns-conversion (2026 conversion table:
    IPC 302 -> BNS 103(1), 420 -> 318, 498A -> 85, 304B -> 80, 376 -> 64, 506 -> 351, CrPC 154 -> 173, 438 -> 482, 439 -> 483, 482 -> 528,
    Evidence 27 -> 23 proviso, 45 -> 39, 65B -> 63(4); BNS 302 = wounding religious feelings); uppolice.gov.in "IPC vis-a-vis BNS"
    correspondence PDF and keralaprisons.gov.in BNS-IPC comparison (official correspondence tables to check rows against). eCourts has
    no public research API for third parties (case status is hers to check on services.ecourts.gov.in; vakil Sahayak covers hearings).
  - Neighbours: vakil (case diary, hearings, limitation, drafts for the advocate), compliance, contracts, cosec, notary, pidesk, dpo (Kanoon
    suite); reuses gyaan (her files), web (search_any / open_website), officegen (Word), chatfiles, site.ai (model), bazar vault.
not_verified: No real Indian Kanoon call was made (fake httpx transport shaped from the documentation: search `docs[].tid/title/headline/docsource`, doc `doc` HTML); IK's exact behaviour for form-encoded POST bodies and the `maxcites=0` value should be checked once with her token (docs show POST; the Python sample sends query parameters - if a body is refused, move `data=` to `params=` in `service._ik`). Real web.search_any / open_website not exercised (sandbox has no DNS); Google grounding redirect URLs are assumed to resolve to the publisher's page through open_website's checked redirects. India Code section pages are often JavaScript / PDF: open_website may get little text from them (then the memo says "nahi mila" or uses other sources) - reading India Code PDFs is not built. The mapping table's "andaaza" rows are from Hoola's own reading and a secondary 2026 table, not the official MHA correspondence table row by row. Model prompts tested only with scripted JSON. Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/legalres_screen.dart (Dart 3 records in `for (final (k, _) in fields)` / `.indexed`).
