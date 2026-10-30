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
        "message (or ask_form). action=answer: site + answers. action=plan_ok: ONLY when she clearly said haan to the plan "
        "-> 3 looks are made (takes a few minutes; the cards update by themselves, don't poll). action=look: site + index "
        "(0-2) she chose (+ colors_from index for 'pehle wala, doosre ke rang') -> building starts; she watches the live board. "
        "action=change: site + instruction (her words: 'hero mein meri photo', 'rang halka', 'price list hatao', 'Hindi "
        "version') -> only those parts are rebuilt, new version. action=photo: site + file_id (+ about: 'shop front', "
        "'owner'). action=undo: her last own-hand edit (words / link / photo / colours she changed in the preview's Edit "
        "mode, free, no AI) goes back. Small word / price / link fixes: tell her to tap Edit on the preview and type it there "
        "(instant, free). action=language + second (en | hi | mr | hinglish, '' = remove) = the whole site in a second "
        "language with a switch (Opus translates, new version). action=booking + lead + yes = HER answer to a website booking "
        "request (only when she said pakka / mana). action=app + instruction (her words: 'customers login karke apna "
        "order track karein', 'students marks dekhein', 'staff complaints ka status badle') = a WEB APP on the site: logins, "
        "lists of data with rules, a My account page and a staff panel at /admin/ (her data; she sees it in the studio's "
        "Data tab). action=export + format react = a React (Vite) project ZIP for a developer. Her UPI ID for Pay buttons: action=answer with answers {upi: 'name@bank'} "
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
        "AFTER LAUNCH: action=care (+ days) = visits, enquiries, uptime, SSL / domain dates, what to improve; action=github (+ "
        "repo, private) = card to put the code in HER GitHub (her tap pushes). AGENCY: action=assign* + client / staff (staff "
        "member id) = whose site it is and who may work on it (a staff member only touches sites given to them); "
        "action=client_report + client. action=delete*. (* owner only)"),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "answer", "plan_ok", "look", "change", "photo", "undo", "language", "booking", "app", "stop", "resume",
                                               "export", "launch", "domain", "dns_check", "email_dns", "rollback",
                                               "takedown", "domain_ideas", "domain_check", "domain_buy", "domain_kyc",
                                               "care", "github", "assign", "client_report", "delete"]},
         "site": {"type": "string", "description": "site number (S-0001) or name; empty = the latest"},
         "brief": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string"}, "style": {"type": "string"},
         "answers": {"type": "object"}, "index": {"type": "integer"}, "colors_from": {"type": "integer"},
         "instruction": {"type": "string"}, "file_id": {"type": "string"}, "about": {"type": "string"},
         "pages": {"type": "array", "items": {"type": "string"}}, "client": {"type": "string"},
         "free": {"type": "boolean"}, "second": {"type": "string", "enum": ["", "en", "hi", "mr", "hinglish"]},
         "lead": {"type": "string"}, "yes": {"type": "boolean"}, "format": {"type": "string", "enum": ["zip", "react"]}, "domain": {"type": "string"}, "primary": {"type": "string", "enum": ["root", "www"]}, "plan": {"type": "string"},
         "provider": {"type": "string"}, "report_to": {"type": "string"}, "version": {"type": "integer"},
         "city": {"type": "string"}, "domains": {"type": "array", "items": {"type": "string"}},
         "auto_renew": {"type": "boolean"}, "days": {"type": "integer"},
         "registrant": {"type": "object", "description": "domain owner on the registry record: owner (person), business, email, phone, address, city, pin, state"}, "repo": {"type": "string"},
         "private": {"type": "boolean"}, "staff": {"type": "string"}},
         "required": ["action"]}},
    {"name": "website_dekho", "description": (
        "Read her websites (nothing changes). what=sites | site (site: board, pages, sections, scores, preview link, "
        "versions) | hosting (site: live addresses, DNS / SSL state, DNS plans) | domains (domains bought through Hoola, KYC, expiry) | care (site, days: visits / enquiries / uptime / tips) | clients (agency: sites by client) | checks (site: what failed / warnings) | leads (site: enquiries from the site forms) | library (q: "
        "find a business type, or industry) | brief (field, goal, style: the full ready brief) | understand (q: what a "
        "short ask means: business type, goal, 3 looks)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["sites", "site", "hosting", "domains", "care", "clients", "checks", "leads", "library", "brief", "understand"]},
         "site": {"type": "string"}, "q": {"type": "string"}, "industry": {"type": "string"}, "field": {"type": "string"},
         "goal": {"type": "string"}, "style": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
SITE_LABELS = {"website": "Website bana raha hoon", "website_dekho": "Website dekh raha hoon"}
_OWNER_ONLY = {"delete", "takedown", "domain_buy", "domain_kyc", "assign", "github"}
_NO_SITE = {"new", "domain_check", "client_report"}
_TAP_LIKE = {"plan_ok", "look"}


def _owner(ctx: Ctx) -> bool:
    return ctx.actor == "owner" or str(ctx.actor).startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..site import service as S
    t, site = ctx.tenant_id, str(a.get("site") or "")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf maalkin yeh kar sakti hain.")
    if action in _TAP_LIKE and not _owner(ctx):
        raise ToolError("Plan / look sirf maalkin chunti hain (app ke card par).")
    conv = ctx.conversation_id or ""
    if action not in _NO_SITE and str(ctx.actor).startswith("staff:"):
        from ..site import care as SC
        if not SC.staff_ok(t, site, ctx.actor):
            raise ToolError("Yeh website aapko di nahi gayi; maalkin se kahiye ki aapko assign karein.")
    if action == "new":
        v = S.new(t, str(a.get("brief") or ""), conv, str(a.get("name") or ""), "", str(a.get("goal") or ""),
                  str(a.get("style") or ""), a.get("answers") if isinstance(a.get("answers"), dict) else None,
                  str(a.get("client") or ""), "" if _owner(ctx) else str(ctx.actor))
        return {k: v.get(k) for k in ("id", "number", "name", "status", "field_label", "goal_label", "plan", "questions",
                                      "understood", "say")}
    if action == "answer":
        return S.answer(t, site, a.get("answers") if isinstance(a.get("answers"), dict) else {})
    if action == "plan_ok":
        v = S.approve_plan(t, site, conv, a.get("pages") if isinstance(a.get("pages"), list) else None)
        return {"status": v["status"], "say": "3 looks ban rahe hain; card par aa jayenge (poll mat kariye)."}
    if action == "look":
        cf = a.get("colors_from")
        v = S.choose_look(t, site, int(a.get("index") or 0), int(cf) if cf is not None else None, conv)
        return {"status": v["status"], "preview": v["preview"],
                "say": "Banana shuru. Har section ban-te hi live preview mein dikhega."}
    if action == "change":
        return S.change(t, site, str(a.get("instruction") or ""), conv)
    if action == "photo":
        return S.add_photo(t, site, None, str(a.get("file_id") or ""), str(a.get("about") or ""))
    if action == "undo":
        return S.undo_edit(t, site)
    if action == "app":
        return S.design_app(t, site, str(a.get("instruction") or ""), conv)
    if action == "language":
        return S.set_language(t, site, str(a.get("second") or ""))
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
        return {"repo": c["repo"], "private": c["private"], "files": c["files"], "say": c["say"] + " (Card par haan unhe deni hai.)"}
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
                "say": c["say"] + " (Card par fingerprint se haan unhe hi deni hai; aap khud nahi khareed sakte.)"}
    return DM.kyc_done(t, str(a.get("domain") or ""))


def _hosting(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..db import session
    from ..site import dns as D
    from ..site import hosting as H
    from ..site import service as S
    t, site, conv = ctx.tenant_id, str(a.get("site") or ""), ctx.conversation_id or ""
    if action == "launch":
        c = H.launch_request(t, site, a.get("free", True) is not False, conv)
        return {"hosts": c["hosts"], "blockers": c["blockers"], "say": c["say"] + " (Card par 'Haan, live karo' unhe hi dabana hai.)"}
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
                                   "say": f"{d} par email ke liye {p['todo']} DNS badlav; aapki haan se."}, conv)
        return {"plan": p["id"], "changes": p["words"], "say": "Email DNS ka card bhej diya (haan unhe dena hai)."}
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
    if what == "clients":
        from ..site import care as SC
        return {"clients": SC.clients(t)}
    if what == "leads":
        return {"leads": S.leads(t, site, 30)}
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
        raise ToolError(str(e) or "Nahi mila")


SITE_HANDLERS = {"website": website, "website_dekho": website_dekho}
