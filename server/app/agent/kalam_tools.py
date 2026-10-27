"""v0.101 Kalam Sahayak tools (content writer). `kalam` writes / changes / checks / asks to publish; `kalam_dekho` only reads.
Publishing itself happens only on her tap (card) — the model can ask for it, never do it."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

KALAM_TOOLS = [
    {"name": "kalam", "description": (
        "Content writer: blogs, product pages / marketplace listings, marketing emails, newsletters, social captions, website "
        "pages, Google Business posts, in HER brand voice, from HER facts only (unknowns become [blanks]). "
        "action=write: brief (her words), kind blog|product|email|newsletter|social|page|gbp (guessed if empty), title, keyword, "
        "words, lang (hinglish|hi|en|mr...), audience, experience (her own first-hand line), paid (sponsored post), file_ids / "
        "urls (her brochure, price list, product sheet, old post, link: read as facts), product {maker, generic_name, "
        "net_quantity, mrp, made_on, origin, care, fssai, best_before, packaged, + any specs}. "
        "action=revise: piece + instruction (her words; 'hamesha / kabhi mat ...' also becomes a rule). action=edit: piece + "
        "body / title (her own text; Hoola learns her style from the change). action=check: piece (claims looked up on the web, "
        "law / SEO / email / voice checks; run before publishing). action=publish: piece + dest wordpress|email|page|copy "
        "(+ where for copy: instagram / amazon / shopify..., to = emails for email (<= 50), status publish|draft|future + when "
        "for WordPress, force=true only if SHE said publish anyway) -> a card she taps (email -> the normal email card). "
        "action=repurpose: piece + kinds (blog -> email + social...). action=files: Word / HTML / Markdown. action=result: piece + "
        "views / clicks / orders / url (learns what works). action=fact: fact + source (her fact list). action=rule: rule. "
        "action=voice: text / file_ids / urls of her OWN writing -> learns her voice. action=copy / delete / unpage. "
        "action=settings (owner only): business, about, audience, language, address, contact, website, cta, tone, do_words, "
        "dont_words, rules, ai_note. WordPress is joined ONLY in the app (Profile > Content writer > Niyam: site, username, "
        "Application Password); never ask for any password in chat. action=wordpress forget=true (owner only) unlinks it. Never say something was published until the result says so."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["write", "revise", "edit", "check", "publish", "repurpose", "files", "result",
                                               "fact", "rule", "voice", "copy", "delete", "unpage", "settings", "wordpress"]},
         "piece": {"type": "string"}, "brief": {"type": "string"}, "kind": {"type": "string"}, "title": {"type": "string"},
         "keyword": {"type": "string"}, "words": {"type": "integer"}, "lang": {"type": "string"}, "audience": {"type": "string"},
         "experience": {"type": "string"}, "paid": {"type": "boolean"},
         "file_ids": {"type": "array", "items": {"type": "string"}}, "urls": {"type": "array", "items": {"type": "string"}},
         "product": {"type": "object"}, "instruction": {"type": "string"}, "body": {"type": "string"}, "text": {"type": "string"},
         "dest": {"type": "string"}, "where": {"type": "string"}, "to": {"type": "array", "items": {"type": "string"}},
         "status": {"type": "string"}, "when": {"type": "string"}, "force": {"type": "boolean"},
         "kinds": {"type": "array", "items": {"type": "string"}}, "views": {"type": "integer"}, "clicks": {"type": "integer"},
         "orders": {"type": "integer"}, "url": {"type": "string"}, "note": {"type": "string"}, "fact": {"type": "string"},
         "source": {"type": "string"}, "rule": {"type": "string"}, "web": {"type": "boolean"},
         "business": {"type": "string"}, "about": {"type": "string"}, "language": {"type": "string"},
         "address": {"type": "string"}, "contact": {"type": "string"}, "website": {"type": "string"}, "cta": {"type": "string"},
         "tone": {"type": "array", "items": {"type": "string"}}, "do_words": {"type": "array", "items": {"type": "string"}},
         "dont_words": {"type": "array", "items": {"type": "string"}}, "rules": {"type": "array", "items": {"type": "string"}},
         "ai_note": {"type": "boolean"},
         "forget": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "kalam_dekho", "description": (
        "Read the content work (nothing changes). what=pieces (kind, status draft|checked|waiting|published|rejected, q) | piece "
        "(piece: full text, meta, checks, claims) | checks (piece) | ideas (days: festival / season ideas for her business) | "
        "settings (brand voice, fact list, rules, WordPress joined?) | kinds."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["pieces", "piece", "checks", "ideas", "settings", "kinds"]},
         "piece": {"type": "string"}, "kind": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"},
         "days": {"type": "integer"}},
         "required": ["what"]}},
]
KALAM_LABELS = {"kalam": "Likh raha hoon", "kalam_dekho": "Lekh dekh raha hoon"}
_OWNER_ONLY = {"settings", "wordpress"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..kalam import service as K
    actor = getattr(ctx, "actor", "owner") or "owner"
    t, conv = ctx.tenant_id, ctx.conversation_id
    piece = _s(a.get("piece"))
    try:
        if action in _OWNER_ONLY and actor != "owner" and not actor.startswith("approved:"):
            raise ToolError("Yeh sirf owner kar sakti hain.")
        if action == "write":
            return K.write(t, _s(a.get("brief") or a.get("text")), _s(a.get("kind")), _s(a.get("title")), _s(a.get("keyword")),
                           a.get("words"), _s(a.get("lang")), _s(a.get("audience")), a.get("file_ids"), a.get("urls"),
                           a.get("product") if isinstance(a.get("product"), dict) else None, _s(a.get("experience")),
                           bool(a.get("paid")), conv, by=actor)
        if action == "revise":
            return K.revise(t, piece, _s(a.get("instruction") or a.get("text")), conv)
        if action == "edit":
            return K.edit(t, piece, a.get("body"), a.get("title"), None, conv)
        if action == "check":
            r = K.check(t, piece, web=a.get("web", True) is not False, conv=conv)
            return {k: r[k] for k in ("summary", "items", "claims", "say")} | {"piece": r["piece"]["number"]}
        if action == "publish":
            return K.publish_request(t, piece, _s(a.get("dest")), _s(a.get("where")), a.get("to"),
                                     _s(a.get("status")) or "publish", _s(a.get("when")), bool(a.get("force")), conv)
        if action == "repurpose":
            return K.repurpose(t, piece, a.get("kinds"), conv)
        if action == "files":
            return K.make_files(t, piece, conv)
        if action == "result":
            return K.result(t, piece, a.get("views"), a.get("clicks"), a.get("orders"), _s(a.get("url")), _s(a.get("note")))
        if action == "fact":
            return K.add_fact(t, _s(a.get("fact") or a.get("text")), _s(a.get("source")))
        if action == "rule":
            return K.add_rule(t, _s(a.get("rule") or a.get("text")))
        if action == "voice":
            return K.learn_voice(t, _s(a.get("text") or a.get("body")), a.get("file_ids"), a.get("urls"))
        if action == "copy":
            return K.copy_piece(t, piece)
        if action == "delete":
            return K.delete(t, piece)
        if action == "unpage":
            return K.unpublish_page(t, piece)
        if action == "settings":
            keys = ("business", "about", "audience", "language", "address", "contact", "website", "cta", "tone", "do_words",
                    "dont_words", "rules", "ai_note")
            return {"settings": K.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
        if action == "wordpress":
            if a.get("forget"):
                return K.forget_wordpress(t)
            raise ToolError("WordPress app mein hi jodiye: Profile > Content writer > Niyam > WordPress (password chat mein nahi).")
    except K.KalamError as e:
        raise ToolError(str(e))
    raise ToolError("action = write | revise | edit | check | publish | repurpose | files | result | fact | rule | voice | "
                    "copy | delete | unpage | settings | wordpress")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..kalam import service as K
    t = ctx.tenant_id
    try:
        if what == "pieces":
            return {"pieces": K.pieces(t, _s(a.get("kind")), _s(a.get("status")), _s(a.get("q")))}
        if what == "piece":
            return K.get(t, _s(a.get("piece")))
        if what == "checks":
            v = K.get(t, _s(a.get("piece")))
            return {"number": v["number"], "checks": v["checks"], "fresh": v["fresh_check"]}
        if what == "ideas":
            return K.ideas(t, int(a.get("days") or 45))
        if what == "settings":
            return K.settings(t)
        if what == "kinds":
            return {"kinds": [{"id": k, "label": v[0], "words": v[1]} for k, v in K.KINDS.items()]}
    except K.KalamError as e:
        raise ToolError(str(e))
    raise ToolError("what = pieces | piece | checks | ideas | settings | kinds")


async def kalam(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def kalam_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


KALAM_HANDLERS = {"kalam": kalam, "kalam_dekho": kalam_dekho}
