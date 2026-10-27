"""v0.87 Lekhak Sahayak tools. `lekhak_dekho` only reads; `lekhak` writes letters from her words / voice notes, translates
with locked facts, fixes grammar with small checked edits, types photos / old Kruti Dev text into Unicode, makes Word / PDF.
Signing is never done here: sign_request puts a card on her phone and only her tap signs."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

LEKHAK_TOOLS = [
    {"name": "lekhak", "description": (
        "Typist + translator coworker. Use for any letter / application / complaint / NOC / leave / bank letter / authority "
        "letter / affidavit draft, typing a photo or scan, Kruti Dev -> Unicode, translation between Indian languages, and "
        "grammar fixing. "
        "action=write: dictation = HER OWN WORDS exactly as she said them (on a call pass her full words, never a summary; "
        "spoken 'poorn viram', 'naya para' are fine), or file_id of her voice note; kind application|leave|complaint|noc|bank|"
        "authority|certificate|office|reply|affidavit|letter, lang hi|mr|en|..., to (a saved recipient name like 'Tehsildar "
        "Akot') or to_lines, subject, reference, enclosures. Result has blanks [..] she must fill and missing_facts: tell her. "
        "action=revise: doc (L-0003 / last) + instruction in her words ('subject chhota karo', 'Marathi mein'). "
        "action=translate: text | file_id | doc, to (language), src, register formal|simple. Names, numbers, dates, IDs and her "
        "keep words are locked automatically; a back-check is run; tell her any difference it reports. "
        "action=grammar: text | doc | file_id, lang: only real mistakes fixed, every change listed, meaning never changed. "
        "action=type: file_id (photo / scan / Kruti Dev file) or text: clean Unicode text, no rewriting. "
        "action=files: doc -> Word + PDF cards. action=sign_request: doc -> a sign card on her phone (ONLY her tap signs; "
        "never say it is signed). action=share: doc + phone / email -> message draft she sends. action=copy: doc. "
        "action=contact: name (e.g. 'Tehsildar Akot') + lines (the To block) + email / phone. "
        "action=glossary: src + dst + lang (always translate src as dst). action=settings (owner only): my_name, my_lines, "
        "my_phone, place, gender f|m, lang, letterhead, keep [words never translated], rules [her sentences], digits latin|native."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["write", "revise", "translate", "grammar", "type", "files", "sign_request", "share",
                                               "copy", "contact", "glossary", "settings"]},
         "dictation": {"type": "string"}, "text": {"type": "string"}, "file_id": {"type": "string"},
         "kind": {"type": "string"}, "lang": {"type": "string"}, "to": {"type": "string"},
         "to_lines": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"},
         "reference": {"type": "string"}, "enclosures": {"type": "array", "items": {"type": "string"}},
         "doc": {"type": "string"}, "instruction": {"type": "string"}, "src": {"type": "string"},
         "register": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"},
         "name": {"type": "string"}, "lines": {"type": "array", "items": {"type": "string"}}, "dst": {"type": "string"},
         "my_name": {"type": "string"}, "my_lines": {"type": "array", "items": {"type": "string"}}, "my_phone": {"type": "string"},
         "place": {"type": "string"}, "gender": {"type": "string"}, "letterhead": {"type": "string"},
         "keep": {"type": "array", "items": {"type": "string"}}, "rules": {"type": "array", "items": {"type": "string"}},
         "digits": {"type": "string"}},
         "required": ["action"]}},
    {"name": "lekhak_dekho", "description": (
        "Read typist / translator work (nothing changes). what=docs (q) | doc (doc: full text, checks, files) | contacts (q) | "
        "kinds (letter types) | settings (her name, lines, glossary, keep words, rules, learned style) | krutidev (text: "
        "convert old Kruti Dev text to Unicode and show it)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["docs", "doc", "contacts", "kinds", "settings", "krutidev"]},
         "q": {"type": "string"}, "doc": {"type": "string"}, "text": {"type": "string"},
         "to": {"type": "string", "enum": ["unicode", "krutidev"]}},
         "required": ["what"]}},
]
LEKHAK_LABELS = {"lekhak": "Likh raha hoon", "lekhak_dekho": "Likhe hue kaagaz dekh raha hoon"}
_OWNER_ONLY = {"settings"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..lekhak import service as L
    actor = getattr(ctx, "actor", "owner") or "owner"
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action in _OWNER_ONLY and actor != "owner" and not actor.startswith("approved:"):
            raise ToolError("Lekhak ki settings sirf owner badal sakti hain.")
        if action == "write":
            return L.write_letter(t, _s(a.get("dictation") or a.get("text")), _s(a.get("kind")), _s(a.get("lang")), _s(a.get("to")),
                                  a.get("to_lines"), _s(a.get("subject")), _s(a.get("reference")), a.get("enclosures"),
                                  _s(a.get("file_id")), "chat", conv)
        if action == "revise":
            return L.revise(t, _s(a.get("doc")), _s(a.get("instruction") or a.get("text")), conv)
        if action == "translate":
            return L.translate(t, _s(a.get("text")), _s(a.get("to") or a.get("lang")), _s(a.get("src")), _s(a.get("file_id")),
                               _s(a.get("doc")), _s(a.get("register")) or "formal", True, conv)
        if action == "grammar":
            return L.fix_grammar(t, _s(a.get("text")), _s(a.get("lang")), _s(a.get("doc")), _s(a.get("file_id")), conv)
        if action == "type":
            return L.type_text(t, _s(a.get("text")), _s(a.get("file_id")), _s(a.get("lang")), conv)
        if action == "files":
            return L.make_files(t, _s(a.get("doc")), conv)
        if action == "sign_request":
            return L.sign_request(t, _s(a.get("doc")), conv)
        if action == "share":
            return L.share_draft(t, _s(a.get("doc")), _s(a.get("phone")), _s(a.get("email")))
        if action == "copy":
            return L.copy_doc(t, _s(a.get("doc")), conv)
        if action == "contact":
            return {"contact": L.contact_save(t, _s(a.get("name") or a.get("to")), a.get("lines") or a.get("to_lines"),
                                              _s(a.get("lang")), _s(a.get("email")), _s(a.get("phone"))), "say": "Pata save."}
        if action == "glossary":
            return {"settings": L.glossary_add(t, _s(a.get("src") or a.get("text")), _s(a.get("dst")), _s(a.get("lang"))),
                    "say": "Shabdkosh mein jod diya."}
        if action == "settings":
            keys = ("my_name", "my_lines", "my_phone", "place", "gender", "lang", "letterhead", "keep", "rules", "digits")
            return {"settings": L.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
    except L.LekhakError as e:
        raise ToolError(str(e))
    raise ToolError("action = write | revise | translate | grammar | type | files | sign_request | share | copy | contact | glossary | settings")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..lekhak import service as L
    t = ctx.tenant_id
    try:
        if what == "docs":
            return {"docs": L.docs(t, _s(a.get("q")), 30)}
        if what == "doc":
            return L.get_doc(t, _s(a.get("doc")))
        if what == "contacts":
            return {"contacts": L.contacts(t, _s(a.get("q")))}
        if what == "kinds":
            return {"kinds": L.KINDS}
        if what == "settings":
            return L.settings(t)
        if what == "krutidev":
            return L.krutidev(_s(a.get("text")), _s(a.get("to")) or "unicode")
    except L.LekhakError as e:
        raise ToolError(str(e))
    raise ToolError("what = docs | doc | contacts | kinds | settings | krutidev")


async def lekhak(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def lekhak_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


LEKHAK_HANDLERS = {"lekhak": lekhak, "lekhak_dekho": lekhak_dekho}
