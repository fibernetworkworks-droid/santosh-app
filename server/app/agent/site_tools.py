"""v0.121 Website Sahayak tools. `website` builds and changes sites; `website_dekho` only reads. The plan and the look are
chosen by HER on the cards in the app (the tool can approve the plan / choose a look only when the owner herself says so
in chat or on a call). Hosting, domains, DNS and going live come in later versions, each behind her tap."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SITE_TOOLS = [
    {"name": "website", "description": (
        "Build HER business a stunning, fast website (hand-made design with motion graphics, any Indian language) and show "
        "her every part as it is built. A few words are enough: the 1 lakh brief library knows 1,000 kinds of business. "
        "action=new: brief (her words, e.g. 'mithai dukaan ki website, online order WhatsApp par'), name, goal (enquiry|"
        "booking|catalogue|menu_order|portfolio|admissions|event|personal|cause|info; guessed), style (optional), answers "
        "{name, phone, whatsapp, email, address, city, hours}. Returns the PLAN card and up to 3 questions: ask them in ONE "
        "message (or ask_form). action=answer: site + answers. action=plan_ok: ONLY when she clearly said yes to the plan "
        "-> 3 looks are made (takes a few minutes; the cards update by themselves, don't poll). action=look: site + index "
        "(0-2) she chose (+ colors_from index for 'pehle wala, doosre ke rang') -> building starts; she watches the live board. "
        "BIG SITES (any size, up to 150 pages): action=new + page_count (e.g. 100) when she asks for a big / complete / "
        "N-page site -> Opus plans the whole site map first (menu groups, sub pages, and LISTS such as products, areas, "
        "courses, doctors, posts: one designed template, one page per item made by code, no AI cost per item); the plan "
        "card comes in a minute or two. action=grow + site (+ page_count, + instruction = what to add) = make or grow the "
        "site map of a site she has (a built site then builds only the new parts). Items of a list are added / removed "
        "with action=change in her words. "
        "SHOP (v0.351 DUKAAN): action=shop + site + shop {on, cod, pickup, delivery (rupees), free_above, min_order, pincodes, upi} "
        "+ products [{title, price (rupees), stock, unit}] (+ from_lists true = her priced list items become products) = her "
        "online shop: cart, checkout, UPI to HER UPI ID or cash on delivery; only HER prices, never invented. Customers pay in "
        "their own UPI app; YOU never mark money received - action=shop_order + site + number (O-1001) + to (confirmed | packed "
        "| shipped | delivered | cancelled) only on her word (confirmed = she saw the money). website_dekho what=orders. "
        "CATALOGUE (v0.538, 100s-10,000s of products / doctors / properties from HER data): action=catalog + site + coll "
        "(the list address: products / doctors / flats) + sheet (her Google Sheet link / name, + tab) OR dataset (a ds_ id "
        "from data_fetch / an ERP read) -> a PREVIEW only (new / changed / rejected rows, thin + duplicate pages, the column "
        "mapping); nothing is written - SHE taps Apply on the console's Catalogue card (a file she has goes there too). "
        "Never type thousands of items into action=change. "
        "SMALL EXACT CHANGES FIRST (v0.789): for a change of one word, colour, price, link, class or button text, use "
        "website_dekho what=search + q (the text / colour / class) -> it names the file and line; then action=edit_lines + "
        "site + file + search (the EXACT text from that file, it must appear once) + replace. No AI rewrite, the same safety "
        "cleaner, one Undo, a version checked on that page in seconds. action=write_file + file + code = the whole file (rare). "
        "action=change only for new sections, layout changes or many parts at once. "
        "action=restore_version + site + version = put the WORKING site back to that version's code and design (v0.808: it "
        "becomes a new version, undoable; enquiries / orders / data are never touched) - for 'v3 wapas lao', 'pehle jaisa "
        "karo'; action=rollback is only for her LIVE address. "
        "action=change: site + instruction (her words: 'hero mein meri photo', 'rang halka', 'price list hatao', 'Hindi "
        "version') -> only those parts are rebuilt, new version. action=photo: site + file_id (+ about: 'shop front', "
        "'owner'). action=undo: her last own-hand edit (words / link / photo / colours she changed in the preview's Edit "
        "mode, free, no AI) goes back. Small word / price / link fixes: tell her to tap Edit on the preview and type it there "
        "(instant, free). action=languages + languages (up to 4 extra: en, hi, mr, hinglish, gu, bn, ta, te, kn, ml, pa, or, ur; "
        "[] = only the first) = the whole site (blog posts too) in those languages with a language menu + hreflang (Opus "
        "translates, new version); action=language + second = the old one-language form. BLOG: posts are WRITTEN by the "
        "kalam tool (kind blog) and published with kalam action=publish dest=site where=<website> (+ when) -> her Haan "
        "card; never write a post here. action=blog + slug + blog_action hide|show|cover (+ cover = one of her site photo "
        "names) changes a post (a new version; she makes it live). Deleting a post is ONLY her tap in the app's Blog tab. "
        "CODE MODE: action=code + instruction (+ file = a code path like pages/home/pricing.html from website_dekho "
        "what=code) = Opus changes the site's REAL code (HTML / CSS / small scripts, cleaned like every build, a diff she "
        "sees in the studio's Code tab, one Undo); use it when she talks about the code or asks for something precise in "
        "one section (a 3-plan comparison table, a sticky header, an animation). action=booking + lead + yes = HER answer to a website booking "
        "request (only when she said pakka / mana). action=app + instruction (her words: 'customers login karke apna "
        "order track karein', 'students marks dekhein', 'staff complaints ka status badle') = a WEB APP on the site: logins, "
        "lists of data with rules, a My account page and a staff panel at /admin/ (her data; she sees it in the studio's "
        "Data tab). ARCHITECT (v0.407, for a portal / web app / anything with logins + data + rules, e.g. 'school ka portal', "
        "'society ka maintenance system', 'clinic with appointments'): action=architect + brief (her one line) = a spec CARD "
        "(pages, users, data lists, rules / workflows / approvals, features) - nothing is built; show its lines and ask. "
        "action=architect_change + spec + instruction = her change to ANY part of the card (pages, users, data, payments, "
        "notifications...; after the build only what it touches is rebuilt / drafted). action=architect_data + spec (A-00xx) + instruction = redo only the data / rules part. "
        "action=phone_app + site = the website's app as an Android / iPhone app on the SAME data (App Sahayak's plan card). action=architect_ok + spec + "
        "hash (+ modules to keep: pages, users, data, logic, features) ONLY after she clearly said yes to THAT card -> the "
        "website + its app backend are built. LOGIC on an existing site (relations, formulas, workflows, maker-checker "
        "approvals, SLA reminders): action=logic + instruction = a checked DRAFT; action=logic_ok + hash ONLY after her "
        "clear yes to that draft. action=export + format react = a React (Vite) project ZIP for a developer. Her UPI ID for Pay buttons: action=answer with answers {upi: 'name@bank'} "
        "(only the ID she typed; never a PIN). action=stop / resume. action=export: ZIP of the built site (file_id). "
        "GOING LIVE (each a card SHE taps, never live by itself): action=launch (free: true = also on the free Hoola "
        "address <name>.<hoola sites domain>) sends the 'live karo' card; action=domain + domain ('sharmasweets.in') joins "
        "her own domain and sends the DNS card (Hoola applies it only on her tap when her DNS is on her Cloudflare, else "
        "the card lists the records for her registrar; + primary root|www = which address is main, default root, the other "
        "redirects); status then goes Verifying -> Setting up -> Live by itself (website_dekho what=hosting); action=dns_check + plan (is it visible worldwide?); action=email_dns "
        "+ domain + provider (google|zoho) + report_to = mail records card; action=rollback + version = card to put an "
        "older version live; action=takedown* stops the live site. "
        "DOMAINS (her name, her account; you NEVER buy): action=domain_ideas (+ name / city) = free names with first-year AND "
        "renewal price in rupees from the registry; action=domain_check + domains [list]; action=domain_buy + domain (+ "
        "auto_renew) = sends HER fingerprint card (no refunds; .in needs her own NIXI e-KYC on the registrar page); "
        "action=domain_kyc + domain when she says KYC is done. "
        "HER OWN DESIGN (v0.565): action=design_from + source screenshot (file_id of the picture she sent) | figma (url of HER "
        "Figma file; her Figma token is added only in the console, never in chat) | site (url of HER OWN old website; she proves "
        "it is hers once with a TXT record or meta tag the answer gives) = a PREVIEW of the design (colours measured, type, "
        "corners, section order; from her own site also her words, phone, photos) - nothing changes yet; action=design_use + "
        "token (+ site; empty = a NEW site from her old site / Figma words) ONLY after she said yes to that preview: look 1 "
        "becomes her design, the other two stay Hoola alternatives. A screenshot of someone else's site gives only a STYLE, "
        "never their words / logo / photos; 'exactly like their site' stays refused. HER OWN OLD SITE MOVING (v0.622): "
        "design_use + keep=true when she says 'purana jaisa rakho' (her page list + section order kept); action=moves = her "
        "old addresses -> new pages (the list + hash, nothing served yet); action=moves_ok + hash (+ drop: old paths she "
        "unticked) ONLY after her yes = live 301s; action=compare_old + url (old path) = old page vs new at the same width. "
        "ANIMATION / 3D (v0.568): action=animation + file_id (her Lottie .json file) + name = keep her own animation for "
        "the site (checked; a link to another server or a file over 1.5 MB is refused); then action=change can put it on a "
        "page by name. Built-in animations (pulse, check, sparkle, scroll, dots, wave) and 3D hero scenes (orb, knot, "
        "particles, waves, blocks) need no file: ask for them with action=change (e.g. 'hero mein 3D orb lagao'). "
        "AFTER LAUNCH: action=care (+ days) = visits, enquiries, uptime, SSL / domain dates, what to improve; action=github (+ "
        "repo, private) = card to put the code in HER GitHub (her tap pushes). AGENCY: action=assign* + client / staff (staff "
        "member id) = whose site it is and who may work on it (a staff member only touches sites given to them); "
        "action=client_report + client. action=delete*. (* owner only)"),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "grow", "shop", "shop_order", "answer", "plan_ok", "look", "change", "edit_lines", "write_file", "restore_version", "photo", "undo", "language", "languages", "blog", "code", "booking", "app", "architect", "architect_data", "architect_change", "architect_ok", "logic", "logic_ok", "phone_app", "catalog", "design_from", "design_use", "moves", "moves_ok", "compare_old", "animation", "stop", "resume",
                                               "export", "launch", "domain", "dns_check", "email_dns", "rollback",
                                               "takedown", "domain_ideas", "domain_check", "domain_buy", "domain_kyc",
                                               "care", "github", "assign", "client_report", "delete"]},
         "site": {"type": "string", "description": "site number (S-0001) or name; empty = the latest"},
         "file": {"type": "string", "description": "edit_lines / write_file / code: a code file path from website_dekho what=search|code (pages/<page>/<section>.html|css|js or design/kit.css)"},
         "search": {"type": "string", "description": "edit_lines: the EXACT text in the file (must appear once; copy it from website_dekho)"},
         "replace": {"type": "string", "description": "edit_lines: the new text"},
         "code": {"type": "string", "description": "write_file: the whole new file"},
         "brief": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string"}, "style": {"type": "string"},
         "answers": {"type": "object"}, "index": {"type": "integer"}, "colors_from": {"type": "integer"},
         "instruction": {"type": "string"}, "file_id": {"type": "string"}, "about": {"type": "string"},
         "pages": {"type": "array", "items": {"type": "string"}}, "client": {"type": "string"},
         "page_count": {"type": "integer", "description": "pages she wants in total (10-150) for a big site"},
         "shop": {"type": "object", "description": "shop settings: on, cod, pickup, delivery, free_above, min_order, pincodes, upi"},
         "products": {"type": "array", "items": {"type": "object"}, "description": "[{title, price, stock, unit, active}]"},
         "from_lists": {"type": "boolean"}, "number": {"type": "string"}, "to": {"type": "string"},
         "free": {"type": "boolean"}, "second": {"type": "string", "enum": ["", "en", "hi", "mr", "hinglish"]},
         "languages": {"type": "array", "items": {"type": "string"}, "description": "extra language codes, max 4"},
         "slug": {"type": "string"}, "blog_action": {"type": "string", "enum": ["hide", "show", "cover"]}, "cover": {"type": "string"},
         "source": {"type": "string", "enum": ["", "screenshot", "figma", "site"]}, "url": {"type": "string"}, "token": {"type": "string"},
         "keep": {"type": "boolean", "description": "design_use from HER OWN old site: keep its page list + section order"},
         "drop": {"type": "array", "items": {"type": "string"}, "description": "moves_ok: old paths she unticked"},
         "lead": {"type": "string"}, "yes": {"type": "boolean"}, "format": {"type": "string", "enum": ["zip", "react"]}, "domain": {"type": "string"}, "primary": {"type": "string", "enum": ["root", "www"]}, "plan": {"type": "string"},
         "provider": {"type": "string"}, "report_to": {"type": "string"}, "version": {"type": "integer"},
         "city": {"type": "string"}, "domains": {"type": "array", "items": {"type": "string"}},
         "auto_renew": {"type": "boolean"}, "days": {"type": "integer"},
         "registrant": {"type": "object", "description": "domain owner on the registry record: owner (person), business, email, phone, address, city, pin, state"}, "repo": {"type": "string"},
         "private": {"type": "boolean"}, "staff": {"type": "string"},
         "spec": {"type": "string", "description": "architect spec card number (A-0007) or id"},
         "hash": {"type": "string", "description": "the card / draft hash she said yes to"},
         "coll": {"type": "string", "description": "catalogue: the list address (products / doctors / flats)"},
         "sheet": {"type": "string", "description": "catalogue: her Google Sheet link / name"}, "tab": {"type": "string"},
         "dataset": {"type": "string", "description": "catalogue: a dataset id (ds_...)"},
         "modules": {"type": "array", "items": {"type": "string", "enum": ["pages", "users", "data", "logic", "features"]}}},
         "required": ["action"]}},
    {"name": "website_dekho", "description": (
        "Read her websites (nothing changes). what=sites | site (site: board, pages, sections, scores, preview link, "
        "versions) | hosting (site: live addresses, DNS / SSL state, DNS plans) | domains (domains bought through Hoola, KYC, expiry) | care (site, days: visits / enquiries / uptime / tips) | dashboard (site, days: day-by-day visits, enquiries, orders, sales, top pages / products, web-app records + change vs the previous period; she sees the charts in the website's Dashboard tab) | ops (site, days: her VISITORS' JavaScript errors (top messages + pages), real-visit speed as p75 bands (LCP / first paint / server answer / layout shift; INP not measured), AI cost of the site, last backup + whether it restored cleanly - use for 'website ki galti dekho', 'site dheemi kyun hai', 'backup theek hai?') | code (site, + file: the code files of the site / one file's code) | search (site, q: where a word / colour / class is in the site's code - file + line, for action=edit_lines) | errors (site: what broke in her PREVIEW - page / data / build errors with file, line, page, how often, and every earlier fix attempt and whether it held; read before fixing) | blog (site: her posts - published / scheduled / hidden - and the site's languages) | clients (agency: sites by client) | checks (site: what failed / warnings) | leads (site: enquiries from the site forms) | library (q: "
        "find a business type, or industry) | brief (field, goal, style: the full ready brief) | understand (q: what a "
        "short ask means: business type, goal, 3 looks)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["sites", "site", "hosting", "domains", "care", "dashboard", "ops", "blog", "code", "search", "errors", "clients", "checks", "leads", "orders", "library", "brief", "understand"]},
         "site": {"type": "string"}, "q": {"type": "string"}, "industry": {"type": "string"}, "field": {"type": "string"},
         "goal": {"type": "string"}, "style": {"type": "string"}, "days": {"type": "integer"}, "file": {"type": "string"}},
         "required": ["what"]}},
]
SITE_LABELS = {"website": "Website bana raha hoon", "website_dekho": "Website dekh raha hoon"}
_OWNER_ONLY = {"delete", "takedown", "domain_buy", "domain_kyc", "assign", "github"}
_NO_SITE = {"new", "domain_check", "client_report", "architect", "architect_data", "architect_change", "architect_ok", "design_from", "design_use"}
_TAP_LIKE = {"plan_ok", "look", "architect_ok", "logic_ok", "design_use", "moves_ok"}


def _owner(ctx: Ctx) -> bool:
    return ctx.actor == "owner" or str(ctx.actor).startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..site import service as S
    t, site = ctx.tenant_id, str(a.get("site") or "")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Only the owner can do this.")
    if action in _TAP_LIKE and not _owner(ctx):
        raise ToolError("Only the owner picks the plan / look (on the card in the app).")
    conv = ctx.conversation_id or ""
    if action not in _NO_SITE and str(ctx.actor).startswith("staff:"):
        from ..site import care as SC
        if not SC.staff_ok(t, site, ctx.actor):
            raise ToolError("This website was not given to you; ask the owner to assign it to you.")
    if action == "new":
        v = S.new(t, str(a.get("brief") or ""), conv, str(a.get("name") or ""), "", str(a.get("goal") or ""),
                  str(a.get("style") or ""), a.get("answers") if isinstance(a.get("answers"), dict) else None,
                  str(a.get("client") or ""), "" if _owner(ctx) else str(ctx.actor), int(a.get("page_count") or 0))
        return {k: v.get(k) for k in ("id", "number", "name", "status", "field_label", "goal_label", "plan", "questions",
                                      "understood", "say", "mapping")}
    if action == "shop":
        v = S.shop_setup(t, site, a.get("shop") if isinstance(a.get("shop"), dict) else None,
                         a.get("products") if isinstance(a.get("products"), list) else None, bool(a.get("from_lists")))
        return {k: v.get(k) for k in ("settings", "upi", "summary", "say")} | {"products": len(v.get("products") or [])}
    if action == "shop_order":
        return S.shop_move(t, site, str(a.get("number") or ""), str(a.get("to") or ""))
    if action == "animation":                     # v0.568 her own Lottie file
        return S.add_lottie(t, site, None, str(a.get("file_id") or ""), str(a.get("name") or ""))
    if action in ("design_from", "design_use"):   # v0.567 KOI BHI DESIGN: her screenshot / Figma / own old site
        from ..site import inspire as IN
        try:
            if action == "design_from":
                out = IN.read(t, str(a.get("source") or ""), str(a.get("url") or ""), str(a.get("file_id") or ""))
                out["ref"] = {k: v for k, v in out["ref"].items() if k != "content"} | {
                    "content": {k: v for k, v in (out["ref"].get("content") or {}).items() if k != "texts"}}
                return out
            return IN.use(t, str(a.get("token") or ""), str(a.get("site") or ""), ctx.conversation_id or "", str(a.get("brief") or ""),
                          bool(a.get("keep")))
        except IN.InspireError as e:
            return {"error": str(e), **e.extra}
    if action in ("moves", "moves_ok", "compare_old"):   # v0.622 KOI PATA NA KHOYE: her own old site's addresses
        from ..site import moved as MV
        try:
            if action == "moves":
                v = MV.propose(t, site)
                return {**{k: v[k] for k in ("site", "from_host", "hash", "guesses", "approved", "say")},
                        "rows": v["rows"][:60], "total": len(v["rows"])}
            if action == "moves_ok":
                return MV.apply(t, site, str(a.get("hash") or ""), [str(x) for x in (a.get("drop") or [])][:500])
            v = MV.compare(t, site, str(a.get("url") or "/"), str(a.get("slug") or ""))
            return {k: v[k] for k in ("old", "new_page", "differences", "widths", "note", "say")}
        except MV.MovedError as e:
            return {"error": str(e)}
    if action == "catalog":                       # v0.538 a preview only; her Apply tap writes it (console Catalogue card)
        from ..site import catalog as CAT
        try:
            if a.get("sheet"):
                rows = CAT.from_sheet(t, str(a["sheet"]), str(a.get("tab") or "") or None)
            elif a.get("dataset"):
                rows = CAT.from_dataset(t, str(a["dataset"]))
            else:
                return {"error": "A Google Sheet (sheet) or a dataset id is needed; for a file, upload it in console > Website > App & data > Catalogue."}
            v = CAT.preview(t, site, str(a.get("coll") or ""), rows, None, str(a.get("name") or ""), "", "chat")
        except CAT.CatalogError as e:
            return {"error": str(e)}
        return {k: v.get(k) for k in ("coll", "items", "new", "changed", "same", "rejected", "thin", "dup", "photos", "mapping")} | {
            "rejected_rows": v["rejected_rows"][:5],
            "say": v["say"] + " Apply: console > Website > App & data > Catalogue (her tap). A new version is made after that."}
    if action == "grow":
        v = S.grow(t, site, int(a.get("page_count") or 0), str(a.get("instruction") or a.get("brief") or ""))
        return {k: v.get(k) for k in ("id", "number", "status", "mapping", "say")}
    if action == "answer":
        return S.answer(t, site, a.get("answers") if isinstance(a.get("answers"), dict) else {})
    if action == "plan_ok":
        v = S.approve_plan(t, site, conv, a.get("pages") if isinstance(a.get("pages"), list) else None)
        return {"status": v["status"], "say": "3 looks are being made; they will arrive on the card (do not poll)."}
    if action == "look":
        cf = a.get("colors_from")
        v = S.choose_look(t, site, int(a.get("index") or 0), int(cf) if cf is not None else None, conv)
        return {"status": v["status"], "preview": v["preview"],
                "say": "Build started. Each section shows in the live preview as soon as it is made."}
    if action == "change":
        return S.change(t, site, str(a.get("instruction") or ""), conv)
    if action == "restore_version":              # v0.808 WAPAS: any version, before launch too
        from ..site import wapas as WP
        try:
            return WP.restore(t, site, int(a.get("version") or 0))
        except WP.WapasError as e:
            raise S.SiteError(str(e))
    if action in ("edit_lines", "write_file"):    # v0.789 CHHOTA BADLAAV: exact search / replace, no AI rewrite
        from ..site import lineedit as LE
        try:
            if action == "edit_lines":
                return LE.edit(t, site, str(a.get("file") or ""), str(a.get("search") or ""), str(a.get("replace") or ""))
            return LE.write(t, site, str(a.get("file") or ""), str(a.get("code") or ""))
        except LE.LineEditError as e:
            raise S.SiteError(str(e))
    if action == "photo":
        return S.add_photo(t, site, None, str(a.get("file_id") or ""), str(a.get("about") or ""))
    if action == "undo":
        return S.undo_edit(t, site)
    if action == "app":
        return S.design_app(t, site, str(a.get("instruction") or ""), conv)
    if action in ("architect", "architect_data", "architect_change", "architect_ok", "logic", "logic_ok", "phone_app"):
        return _architect(ctx, action, a)
    if action == "language":
        return S.set_language(t, site, str(a.get("second") or ""))
    if action == "code":                         # v0.373 CODE MODE (a site job; the diff shows in the Code tab)
        return S.code_ask(t, site, str(a.get("instruction") or ""), str(a.get("file") or ""), conv)
    if action == "languages":                    # v0.366 BHASHAYEN
        return S.set_languages(t, site, a.get("languages") if isinstance(a.get("languages"), list) else [])
    if action == "blog":                         # v0.366 hide / show / cover from chat (never delete: her tap only)
        return S.blog_act(t, site, str(a.get("slug") or ""), str(a.get("blog_action") or ""), str(a.get("cover") or ""), False)
    if action == "booking":
        return S.booking_decide(t, str(a.get("lead") or ""), bool(a.get("yes")))
    if action == "stop":
        return S.stop(t, site)
    if action == "resume":
        return S.resume(t, site)
    if action == "export":
        return S.export(t, site, "react" if str(a.get("format") or "") == "react" else "zip")
    if action in ("launch", "domain", "dns_check", "email_dns", "rollback", "takedown"):
        return _hosting(ctx, action, a)
    if action in ("domain_ideas", "domain_check", "domain_buy", "domain_kyc"):
        return _domains(ctx, action, a)
    if action == "care":
        from ..site import care as SC
        r = SC.report(t, site, int(a.get("days") or 30))
        r.pop("site", None)
        return r
    if action == "github":
        from ..site import github as GH
        c = GH.request(t, site, str(a.get("repo") or ""), a.get("private", True) is not False, conv)
        return {"repo": c["repo"], "private": c["private"], "files": c["files"], "say": c["say"] + " (She must say yes on the card.)"}
    if action == "assign":
        from ..site import care as SC
        return SC.assign(t, site, a.get("client") if a.get("client") is not None else None,
                         a.get("staff") if a.get("staff") is not None else None)
    if action == "client_report":
        from ..site import care as SC
        return SC.client_report(t, str(a.get("client") or ""))
    if action == "delete":
        return S.delete(t, site)
    raise ToolError(f"Unknown action {action}")


def _architect(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    """v0.407 HOOLA ARCHITECT + the site's DIMAAG logic. Drafts are free to make; only her clear haan builds / applies."""
    from ..site import applink as AL
    from ..site import architect as AR
    from ..site import webapp as W
    t, site, conv = ctx.tenant_id, str(a.get("site") or ""), ctx.conversation_id or ""
    try:
        if action == "architect":
            c = AR.draft(t, str(a.get("brief") or a.get("instruction") or ""), conv)
        elif action == "architect_data":
            c = AR.redraft_data(t, str(a.get("spec") or ""), str(a.get("instruction") or ""))
        elif action == "architect_change":
            out = AR.revise(t, str(a.get("spec") or ""), str(a.get("instruction") or ""))
            return {k: out.get(k) for k in ("id", "number", "modules", "hash", "say", "added_pages", "removed_pages", "logic_draft")
                    if k in out}
        elif action == "phone_app":
            out = AL.phone_app(t, site, conv)
            return {k: out.get(k) for k in ("app", "number", "status", "say")}
        elif action == "architect_ok":
            mods = a.get("modules") if isinstance(a.get("modules"), list) and a.get("modules") else None
            return AR.approve(t, str(a.get("spec") or ""), str(a.get("hash") or ""), mods, conv)
        elif action == "logic":
            return AL.logic_draft(t, site, str(a.get("instruction") or ""))
        else:
            return AL.logic_apply(t, site, str(a.get("hash") or ""))
    except (AR.ArchError, W.AppError) as e:
        raise ToolError(str(e)) from e
    return {k: c.get(k) for k in ("id", "number", "name", "summary", "modules", "hash", "questions", "data_ready", "warnings", "say")}


def _domains(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..site import domains as DM
    t, site, conv = ctx.tenant_id, str(a.get("site") or ""), ctx.conversation_id or ""
    if action == "domain_ideas":
        return DM.suggest(t, site, str(a.get("name") or ""), str(a.get("city") or ""), conv)
    if action == "domain_check":
        doms = a.get("domains") if isinstance(a.get("domains"), list) else [a.get("domain") or ""]
        return {"results": DM.check(t, [str(d) for d in doms][:20])}
    if action == "domain_buy":
        c = DM.buy_request(t, site, str(a.get("domain") or ""), bool(a.get("auto_renew")), conv,
                           a.get("registrant") if isinstance(a.get("registrant"), dict) else None)
        return {"card": c["id"], "amount": c["amount"], "renew_inr": c["renew_inr"], "lines": c["lines"],
                "say": c["say"] + " (Only she can say yes on the card, with her fingerprint; you cannot buy it yourself.)"}
    return DM.kyc_done(t, str(a.get("domain") or ""))


def _hosting(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..db import session
    from ..site import dns as D
    from ..site import hosting as H
    from ..site import service as S
    t, site, conv = ctx.tenant_id, str(a.get("site") or ""), ctx.conversation_id or ""
    if action == "launch":
        c = H.launch_request(t, site, a.get("free", True) is not False, conv)
        return {"hosts": c["hosts"], "blockers": c["blockers"], "say": c["say"] + " (Only she can press the go-live button on the card.)"}
    if action == "domain":
        c = H.connect_domain(t, site, str(a.get("domain") or ""), conv, str(a.get("primary") or ""))
        return {"domain": c["domain"], "provider": c["plan"]["provider"], "changes": c["plan"]["words"],
                "manual_steps": c["plan"]["manual_steps"], "records": c.get("records", []), "say": c["say"]}
    if action == "dns_check":
        return D.check(t, str(a.get("plan") or ""))
    if action == "email_dns":
        with session() as s:
            sid = S._find(s, t, site).id
        d = D.norm_domain(str(a.get("domain") or ""))
        p = D.make_plan(t, sid, d, D.email_records(d, str(a.get("provider") or ""), str(a.get("report_to") or "")), "email")
        S._publish(t, "site_dns", {"kind": "dns", "domain": d, "plan": p, "push": True,
                                   "say": f"{p['todo']} DNS changes for email on {d}; with her yes."}, conv)
        return {"plan": p["id"], "changes": p["words"], "say": "The email DNS card was sent (she must say yes)."}
    if action == "rollback":
        c = H.rollback_request(t, site, int(a.get("version") or 0), conv)
        return {"say": c["say"]}
    if action == "takedown":
        return H.take_down(t, site)
    raise ToolError(f"Unknown action {action}")


async def website(ctx: Ctx, action: str, **a) -> dict[str, Any]:
    from ..site import dns as D
    from ..site import hosting as H
    from ..site import service as S
    try:
        return await asyncio.to_thread(_act, ctx, action, a)
    except (S.SiteError, H.HostError, D.DnsError) as e:
        raise ToolError(str(e))
    except Exception as e:
        from ..site import domains as DM
        from ..site import github as GH
        if isinstance(e, (DM.DomainError, GH.GithubError)):
            raise ToolError(str(e))
        raise


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> Any:
    from ..site import library as L
    from ..site import service as S
    t, site = ctx.tenant_id, str(a.get("site") or "")
    if what == "sites":
        return {"sites": S.sites(t)}
    if what == "site":
        v = S.get(t, site)
        v.pop("facts", None)
        return v
    if what == "checks":
        return S.get(t, site).get("checks")
    if what == "hosting":
        from ..site import hosting as H
        return H.status(t, site)
    if what == "domains":
        from ..site import domains as DM
        return {"domains": DM.domains(t)}
    if what == "care":
        from ..site import care as SC
        r = SC.report(t, site, int(a.get("days") or 30))
        r.pop("site", None)
        return r
    if what == "errors":                          # v0.802 GALTI PAKDO: the preview's errors + the fix ledger
        from ..site import galti as G
        try:
            out = G.errors(t, site, bool(a.get("all")))
        except G.GaltiError as e:
            raise S.SiteError(str(e))
        out["say"] = (f"{out['open']} open error(s) in the preview." if out["open"] else "No open errors in the preview.")
        return out
    if what == "search":                          # v0.789 where a text is in the site's code (for edit_lines)
        from ..db import session
        from ..site import lineedit as LE
        with session() as s_:
            r = S._find(s_, t, site)
            s_.expunge(r)
        try:
            return LE.search(r, str(a.get("q") or ""))
        except LE.LineEditError as e:
            raise S.SiteError(str(e))
    if what == "code":                            # v0.373 CODE MODE
        if a.get("file"):
            return S.code_read(t, site, str(a.get("file")))
        return S.code_tree(t, site)
    if what == "blog":                            # v0.366 her posts + languages
        return S.blog_info(t, site)
    if what == "dashboard":                       # v0.357 the numbers behind her Dashboard tab
        from ..site import dash as SD
        r = SD.dashboard(t, site, int(a.get("days") or 30))
        sr = r.pop("series")
        r["busiest_days"] = sorted(zip(sr["days"], sr["visits"]), key=lambda x: -x[1])[:5]
        return r
    if what == "ops":                             # v0.564 CHALTI WEBSITE: errors, real speed, cost, backup restore test
        from ..site import ops as OPS
        return OPS.owner_view(t, site, int(a.get("days") or 30))
    if what == "clients":
        from ..site import care as SC
        return {"clients": SC.clients(t)}
    if what == "leads":
        return {"leads": S.leads(t, site, 30)}
    if what == "orders":                          # v0.351 her shop's orders (newest first)
        out = S.shop_orders(t, site, str(a.get("status") or ""))
        return {"summary": out["summary"], "orders": out["orders"][:30]}
    if what == "library":
        return L.browse(str(a.get("industry") or ""), str(a.get("q") or ""), 30)
    if what == "brief":
        b = L.brief(str(a.get("field") or ""), str(a.get("goal") or ""), str(a.get("style") or ""))
        return {k: b[k] for k in ("id", "field_label", "goal_label", "style_label", "pages", "sections", "questions", "text")}
    if what == "understand":
        return L.understand(str(a.get("q") or ""))
    raise ToolError(f"Unknown what {what}")


async def website_dekho(ctx: Ctx, what: str, **a) -> Any:
    from ..site import hosting as H
    from ..site import service as S
    try:
        return await asyncio.to_thread(_read, ctx, what, a)
    except (S.SiteError, H.HostError, KeyError) as e:
        raise ToolError(str(e) or "Not found")


SITE_HANDLERS = {"website": website, "website_dekho": website_dekho}
