"""Santosh's Google Slides work. Blocking; tools run it in a thread.

Santosh writes the outline (slides with a layout, title, points, notes) and this module turns it into a real Google
Slides deck with the API. Decks can be named the way the user says them, by link, or by id. Creating, adding,
editing, reordering and exporting happen at once; deleting slides and sharing wait for the user's tap.
"""
from __future__ import annotations

import re
import secrets
from typing import Any

from sqlalchemy import select

from ..db import now, session
from ..events import bus
from .accounts import clients, get_client
from .client import EXPORT, SlidesClient, SlidesError, id_from
from .models import SlidesPending, SlidesRecent

LAYOUTS = ("title", "section", "bullets", "two_columns", "big_number", "quote", "table", "image", "closing")
# our layout -> (Google predefined layout, {role: (placeholder type, index)})
PREDEFINED = {
    "title": ("TITLE", {"title": ("CENTERED_TITLE", 0), "subtitle": ("SUBTITLE", 0)}),
    "section": ("SECTION_HEADER", {"title": ("TITLE", 0)}),
    "bullets": ("TITLE_AND_BODY", {"title": ("TITLE", 0), "body": ("BODY", 0)}),
    "two_columns": ("TITLE_AND_TWO_COLUMNS", {"title": ("TITLE", 0), "left": ("BODY", 0), "right": ("BODY", 1)}),
    "big_number": ("BIG_NUMBER", {"title": ("TITLE", 0), "body": ("BODY", 0)}),
    "quote": ("MAIN_POINT", {"title": ("TITLE", 0)}),
    "closing": ("MAIN_POINT", {"title": ("TITLE", 0)}),
    "table": ("TITLE_ONLY", {"title": ("TITLE", 0)}),
    "image": ("TITLE_ONLY", {"title": ("TITLE", 0)}),
}
EMU = 12700        # 1 pt
MAX_SLIDES = 60


def _oid(prefix: str) -> str:
    return f"s_{prefix}_{secrets.token_hex(5)}"


def _hex_rgb(h: str | None) -> dict | None:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", (h or "").strip())
    if not m:
        return None
    v = m.group(1)
    return {"red": int(v[0:2], 16) / 255, "green": int(v[2:4], 16) / 255, "blue": int(v[4:6], 16) / 255}


# ---------------- finding the deck ----------------
def _remember(tenant: str, c: SlidesClient, pid: str, title: str) -> None:
    with session() as s:
        r = s.scalar(select(SlidesRecent).where(SlidesRecent.tenant_id == tenant, SlidesRecent.presentation_id == pid))
        if r is None:
            r = SlidesRecent(tenant_id=tenant, presentation_id=pid)
            s.add(r)
        r.title, r.account, r.used_at = title[:300], c.key, now()


def recent(tenant: str, limit: int = 15) -> list[dict[str, Any]]:
    with session() as s:
        return [{"id": r.presentation_id, "title": r.title, "used": r.used_at.isoformat()[:10]}
                for r in s.scalars(select(SlidesRecent).where(SlidesRecent.tenant_id == tenant)
                                   .order_by(SlidesRecent.used_at.desc()).limit(limit)).all()]


def find(tenant: str, query: str = "", limit: int = 15) -> dict[str, Any]:
    out, seen, notes = [], set(), []
    for c in clients(tenant) or [get_client(tenant)]:
        try:
            for f in c.search(query, limit):
                if f["id"] not in seen:
                    seen.add(f["id"])
                    out.append({**f, "account": c.address})
        except SlidesError as e:
            notes.append(str(e))
    q = (query or "").lower()
    for r in recent(tenant, 30):
        if r["id"] not in seen and (not q or q in r["title"].lower()):
            seen.add(r["id"])
            out.append({"id": r["id"], "title": r["title"], "modified": r["used"], "recent": True,
                        "link": f"https://docs.google.com/presentation/d/{r['id']}/edit"})
    res: dict[str, Any] = {"count": len(out), "presentations": out[:limit]}
    if notes:
        res["notes"] = notes
    return res


def resolve(tenant: str, deck: str) -> tuple[SlidesClient, dict[str, Any]]:
    text = str(deck or "").strip()
    if not text:
        raise SlidesError("Kaunsi presentation? Naam, link ya id dijiye.")
    cs = clients(tenant) or [get_client(tenant)]
    pid = id_from(text)
    if not pid:
        with session() as s:
            rows = s.scalars(select(SlidesRecent).where(SlidesRecent.tenant_id == tenant)
                             .order_by(SlidesRecent.used_at.desc())).all()
            hits = [r for r in rows if r.title.lower() == text.lower()] or [r for r in rows if text.lower() in r.title.lower()]
            if len(hits) == 1:
                pid = hits[0].presentation_id
        if not pid:
            found = []
            for c in cs:
                try:
                    found += [(c, f) for f in c.search(text, 10)]
                except SlidesError:
                    continue
            exact = [x for x in found if x[1]["title"].lower() == text.lower()]
            pick = exact or found
            if not pick:
                raise SlidesError(f"'{text}' naam ki presentation nahi mili. slides_find se dekhiye ya link dijiye.")
            if len({f["id"] for _, f in pick}) > 1:
                raise SlidesError("Is naam ki kai presentations hain: " + "; ".join(
                    f"{f['title']} (id {f['id']}, {f['modified']})" for _, f in pick[:6]) + ". User se poochiye kaunsi.")
            cs = [pick[0][0]] + [c for c in cs if c is not pick[0][0]]
            pid = pick[0][1]["id"]
    last: Exception | None = None
    for c in cs:
        try:
            p = c.get(pid)
            _remember(tenant, c, pid, p.get("title", ""))
            return c, p
        except SlidesError as e:
            last = e
    raise last or SlidesError("Presentation nahi khuli")


def link_of(pid: str) -> str:
    return f"https://docs.google.com/presentation/d/{pid}/edit"


# ---------------- reading ----------------
def _shape_text(el: dict) -> str:
    out = []
    for te in ((el.get("shape") or {}).get("text") or {}).get("textElements", []):
        if "textRun" in te:
            out.append(te["textRun"].get("content", ""))
    return "".join(out).strip()


def _table_text(el: dict) -> list[list[str]]:
    rows = []
    for r in (el.get("table") or {}).get("tableRows", []):
        row = []
        for cell in r.get("tableCells", []):
            row.append("".join(te.get("textRun", {}).get("content", "")
                               for te in (cell.get("text") or {}).get("textElements", [])).strip())
        rows.append(row)
    return rows


def _slide_view(n: int, sl: dict, with_ids: bool = False) -> dict[str, Any]:
    title, texts, tables = "", [], []
    for el in sl.get("pageElements", []):
        ph = ((el.get("shape") or {}).get("placeholder") or {}).get("type", "")
        if "table" in el:
            tables.append(_table_text(el))
            continue
        t = _shape_text(el)
        if not t:
            continue
        if ph in ("TITLE", "CENTERED_TITLE") and not title:
            title = t
        else:
            texts.append(t)
    notes = ""
    np_ = (sl.get("slideProperties") or {}).get("notesPage") or {}
    nid = (np_.get("notesProperties") or {}).get("speakerNotesObjectId")
    for el in np_.get("pageElements", []):
        if el.get("objectId") == nid:
            notes = _shape_text(el)
    v: dict[str, Any] = {"n": n, "title": title, "text": "\n".join(texts)[:3000], "notes": notes[:2000]}
    if tables:
        v["tables"] = tables
    if with_ids:
        v["id"] = sl.get("objectId")
    return v


def read(tenant: str, deck: str) -> dict[str, Any]:
    c, p = resolve(tenant, deck)
    slides = [_slide_view(i + 1, s) for i, s in enumerate(p.get("slides", []))]
    return {"id": p["presentationId"], "title": p.get("title", ""), "link": link_of(p["presentationId"]),
            "slide_count": len(slides), "slides": slides}


# ---------------- building slides ----------------
def _placeholders(layout: str) -> tuple[str, dict[str, tuple[str, int]], list[dict], dict[str, str]]:
    pre, roles = PREDEFINED[layout]
    ids = {role: _oid(role[:3]) for role in roles}
    mappings = [{"layoutPlaceholder": {"type": t, "index": i}, "objectId": ids[r]} for r, (t, i) in roles.items()]
    return pre, roles, mappings, ids


def _text(oid: str, text: str) -> list[dict]:
    text = str(text or "").strip()
    return [{"insertText": {"objectId": oid, "insertionIndex": 0, "text": text}}] if text else []


def _bullets(oid: str, items: list) -> list[dict]:
    lines = [str(x).strip() for x in items or [] if str(x).strip()]
    if not lines:
        return []
    return [{"insertText": {"objectId": oid, "insertionIndex": 0, "text": "\n".join(lines)}},
            {"createParagraphBullets": {"objectId": oid, "textRange": {"type": "ALL"},
                                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}}]


def slide_requests(spec: dict, index: int | None, accent: dict | None) -> tuple[list[dict], str, str]:
    """Requests that create one slide from Santosh's spec. Returns (requests, slide objectId, notes text)."""
    layout = str(spec.get("layout") or ("bullets" if spec.get("bullets") else "title")).lower()
    if layout not in LAYOUTS:
        raise SlidesError(f"layout: {', '.join(LAYOUTS)}")
    pre, roles, mappings, ids = _placeholders(layout)
    sid = _oid("slide")
    req: dict[str, Any] = {"objectId": sid, "slideLayoutReference": {"predefinedLayout": pre},
                           "placeholderIdMappings": mappings}
    if index is not None:
        req["insertionIndex"] = index
    reqs: list[dict] = [{"createSlide": req}]
    title = spec.get("title") or ""
    if layout == "big_number":
        reqs += _text(ids["title"], spec.get("number") or title)
        reqs += _text(ids["body"], spec.get("caption") or (title if spec.get("number") else ""))
    elif layout in ("quote", "closing"):
        q = spec.get("quote") or title
        reqs += _text(ids["title"], (f"“{q}”" if layout == "quote" and spec.get("quote") else q)
                      + (f"\n— {spec['caption']}" if spec.get("caption") else ""))
    else:
        reqs += _text(ids["title"], title)
    if layout == "title":
        reqs += _text(ids["subtitle"], spec.get("subtitle", ""))
    if layout == "bullets":
        reqs += _bullets(ids["body"], spec.get("bullets") or [])
    if layout == "two_columns":
        reqs += _bullets(ids["left"], spec.get("left") or [])
        reqs += _bullets(ids["right"], spec.get("right") or [])
    if layout == "table":
        rows = [[str(c) for c in r] for r in (spec.get("rows") or [])][:20]
        if rows:
            ncols = max(len(r) for r in rows)
            tid = _oid("tbl")
            reqs.append({"createTable": {"objectId": tid, "rows": len(rows), "columns": ncols, "elementProperties": {
                "pageObjectId": sid, "size": {"width": {"magnitude": 620 * EMU, "unit": "EMU"},
                                             "height": {"magnitude": 40 * len(rows) * EMU, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 50 * EMU, "translateY": 110 * EMU, "unit": "EMU"}}}})
            for ri, r in enumerate(rows):
                for ci, cell in enumerate(r):
                    if cell:
                        reqs.append({"insertText": {"objectId": tid, "cellLocation": {"rowIndex": ri, "columnIndex": ci},
                                                    "text": cell, "insertionIndex": 0}})
            for ci, cell in enumerate(rows[0]):          # header row in bold
                if cell:
                    reqs.append({"updateTextStyle": {"objectId": tid, "cellLocation": {"rowIndex": 0, "columnIndex": ci},
                                                     "style": {"bold": True}, "textRange": {"type": "ALL"}, "fields": "bold"}})
    if layout == "image":
        url = str(spec.get("image_url") or "")
        if not url.startswith("https://"):
            raise SlidesError("image layout ke liye public https image_url chahiye.")
        reqs.append({"createImage": {"objectId": _oid("img"), "url": url, "elementProperties": {
            "pageObjectId": sid, "size": {"width": {"magnitude": 520 * EMU, "unit": "EMU"},
                                         "height": {"magnitude": 290 * EMU, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": 100 * EMU, "translateY": 95 * EMU, "unit": "EMU"}}}})
    if accent and "title" in ids and (title or layout in ("big_number", "quote", "closing")):
        reqs.append({"updateTextStyle": {"objectId": ids["title"], "textRange": {"type": "ALL"},
                                         "style": {"foregroundColor": {"opaqueColor": {"rgbColor": accent}}},
                                         "fields": "foregroundColor"}})
    return reqs, sid, str(spec.get("notes") or "")


def _add_notes(c: SlidesClient, pid: str, notes_by_slide: dict[str, str]) -> None:
    notes_by_slide = {k: v for k, v in notes_by_slide.items() if v.strip()}
    if not notes_by_slide:
        return
    p = c.get(pid)
    reqs = []
    for sl in p.get("slides", []):
        text = notes_by_slide.get(sl.get("objectId"))
        if not text:
            continue
        nid = (((sl.get("slideProperties") or {}).get("notesPage") or {}).get("notesProperties") or {}).get("speakerNotesObjectId")
        if nid:
            reqs.append({"insertText": {"objectId": nid, "insertionIndex": 0, "text": text}})
    c.batch(pid, reqs)


def _check_specs(slides: list) -> list[dict]:
    if not slides:
        raise SlidesError("Slides do: har slide {layout, title, bullets / subtitle / rows, notes}.")
    if len(slides) > MAX_SLIDES:
        raise SlidesError(f"Ek baar mein {MAX_SLIDES} slides tak.")
    return [s if isinstance(s, dict) else {"layout": "bullets", "title": str(s)} for s in slides]


def create(tenant: str, title: str, slides: list[dict], accent: str | None = None, account: str | None = None) -> dict[str, Any]:
    c = get_client(tenant, account)
    specs = _check_specs(slides)
    p = c.create(str(title or "Santosh presentation")[:200])
    pid = p["presentationId"]
    default_slide = [s["objectId"] for s in p.get("slides", [])]
    rgb = _hex_rgb(accent)
    reqs, notes = [], {}
    for i, spec in enumerate(specs):
        r, sid, n = slide_requests(spec, i, rgb)
        reqs += r
        notes[sid] = n
    reqs += [{"deleteObject": {"objectId": o}} for o in default_slide]     # the blank slide every new deck starts with
    c.batch(pid, reqs)
    _add_notes(c, pid, notes)
    _remember(tenant, c, pid, p.get("title", title))
    return {"id": pid, "title": p.get("title", title), "link": link_of(pid), "slide_count": len(specs), "account": c.address}


def add_slides(tenant: str, deck: str, slides: list[dict], position: int | None = None, accent: str | None = None) -> dict:
    c, p = resolve(tenant, deck)
    specs = _check_specs(slides)
    count = len(p.get("slides", []))
    at = count if position is None else max(0, min(int(position) - 1, count))
    rgb = _hex_rgb(accent)
    reqs, notes = [], {}
    for i, spec in enumerate(specs):
        r, sid, n = slide_requests(spec, at + i, rgb)
        reqs += r
        notes[sid] = n
    c.batch(p["presentationId"], reqs)
    _add_notes(c, p["presentationId"], notes)
    return {"title": p.get("title", ""), "added": len(specs), "at": at + 1, "slide_count": count + len(specs),
            "link": link_of(p["presentationId"])}


def _slide_at(p: dict, n: int) -> dict:
    sl = p.get("slides", [])
    if not 1 <= int(n) <= len(sl):
        raise SlidesError(f"Slide {n} nahi hai (is deck mein {len(sl)} slides hain).")
    return sl[int(n) - 1]


def edit_slide(tenant: str, deck: str, n: int, title: str | None = None, body: list | str | None = None,
               notes: str | None = None) -> dict[str, Any]:
    c, p = resolve(tenant, deck)
    sl = _slide_at(p, n)
    reqs = []
    title_el = body_el = None
    for el in sl.get("pageElements", []):
        ph = ((el.get("shape") or {}).get("placeholder") or {}).get("type", "")
        if ph in ("TITLE", "CENTERED_TITLE") and title_el is None:
            title_el = el
        elif ph in ("BODY", "SUBTITLE") and body_el is None:
            body_el = el
    for el, new in ((title_el, title), (body_el, body)):
        if new is None:
            continue
        if el is None:
            raise SlidesError(f"Slide {n} par {'title' if el is title_el else 'body'} box nahi hai; slides_add se nayi slide banaiye.")
        if _shape_text(el):
            reqs.append({"deleteText": {"objectId": el["objectId"], "textRange": {"type": "ALL"}}})
        if isinstance(new, list):
            reqs += _bullets(el["objectId"], new)
        else:
            reqs += _text(el["objectId"], new)
    if notes is not None:
        np_ = (sl.get("slideProperties") or {}).get("notesPage") or {}
        nid = (np_.get("notesProperties") or {}).get("speakerNotesObjectId")
        if nid:
            had = any(el.get("objectId") == nid and _shape_text(el) for el in np_.get("pageElements", []))
            if had:
                reqs.append({"deleteText": {"objectId": nid, "textRange": {"type": "ALL"}}})
            reqs += _text(nid, notes)
    if not reqs:
        raise SlidesError("Kya badalna hai? title, body ya notes do.")
    c.batch(p["presentationId"], reqs)
    return {"title": p.get("title", ""), "slide": int(n), "link": link_of(p["presentationId"])}


def replace_text(tenant: str, deck: str, find: str, replace: str, match_case: bool = False) -> dict[str, Any]:
    if not find:
        raise SlidesError("Kya dhoondh kar badalna hai?")
    c, p = resolve(tenant, deck)
    res = c.batch(p["presentationId"], [{"replaceAllText": {"containsText": {"text": find, "matchCase": bool(match_case)},
                                                            "replaceText": str(replace)}}])
    n = 0
    for r in res.get("replies", []):
        n += int((r.get("replaceAllText") or {}).get("occurrencesChanged", 0))
    return {"title": p.get("title", ""), "replaced": n, "link": link_of(p["presentationId"])}


def move_slide(tenant: str, deck: str, n: int, to: int) -> dict[str, Any]:
    c, p = resolve(tenant, deck)
    sl = _slide_at(p, n)
    count = len(p["slides"])
    to = max(1, min(int(to), count))
    # insertionIndex is counted before the move; moving down needs +1
    idx = to if to > int(n) else to - 1
    c.batch(p["presentationId"], [{"updateSlidesPosition": {"slideObjectIds": [sl["objectId"]], "insertionIndex": idx}}])
    return {"title": p.get("title", ""), "moved": int(n), "to": to, "link": link_of(p["presentationId"])}


def duplicate_slide(tenant: str, deck: str, n: int) -> dict[str, Any]:
    c, p = resolve(tenant, deck)
    sl = _slide_at(p, n)
    c.batch(p["presentationId"], [{"duplicateObject": {"objectId": sl["objectId"]}}])
    return {"title": p.get("title", ""), "duplicated": int(n), "new_slide": int(n) + 1, "link": link_of(p["presentationId"])}


def plan_delete(tenant: str, deck: str, numbers: list[int]) -> dict[str, Any]:
    c, p = resolve(tenant, deck)
    nums = sorted({int(x) for x in numbers or []})
    if not nums:
        raise SlidesError("Kaunsi slides hatani hain? numbers do.")
    if len(nums) >= len(p.get("slides", [])):
        raise SlidesError("Saari slides nahi hata sakte; kam se kam ek rehni chahiye.")
    picked = [(_slide_at(p, x), x) for x in nums]
    return {"client": c, "pid": p["presentationId"], "title": p.get("title", ""),
            "ids": [s["objectId"] for s, _ in picked],
            "lines": [f"Slide {x}: {_slide_view(x, s)['title'] or '(bina title)'}" for s, x in picked]}


def export(tenant: str, deck: str, fmt: str = "pdf") -> tuple[str, bytes, dict]:
    fmt = "pptx" if str(fmt).lower() in ("pptx", "ppt", "powerpoint") else "pdf"
    c, p = resolve(tenant, deck)
    pid = p["presentationId"]
    try:
        data = c.export(pid, fmt)
    except SlidesError as first:
        data = None
        try:      # decks Santosh didn't create: Google Drive's connection (if any) can export them
            from ..drive.accounts import clients as drive_clients
            for dc in drive_clients(tenant):
                try:
                    data = dc.export(pid, EXPORT[fmt][0])
                    break
                except Exception:
                    continue
        except Exception:
            pass
        if data is None:
            raise SlidesError(f"{first} Iske liye Profile > Google Drive bhi jodiye (doosron ki banayi decks export karne ke liye).")
    safe = re.sub(r"[^\w\- ]+", "", p.get("title", "")).strip() or "presentation"
    return safe + EXPORT[fmt][1], data, p


# ---------------- confirm cards ----------------
def pend(tenant: str, conv: str, action: str, payload: dict, summary: dict) -> str:
    with session() as s:
        row = SlidesPending(tenant_id=tenant, conversation_id=conv, action=action, payload=payload, summary=summary)
        s.add(row)
        s.flush()
        return row.id


def pending(tenant: str, pid: str) -> dict | None:
    with session() as s:
        row = s.get(SlidesPending, pid)
        if row is None or row.tenant_id != tenant:
            return None
        return {"id": row.id, "action": row.action, "payload": row.payload, "summary": row.summary, "status": row.status,
                "conversation_id": row.conversation_id}


def run_pending(tenant: str, pend_id: str) -> dict[str, Any]:
    p = pending(tenant, pend_id)
    if p is None or p["status"] != "pending":
        raise SlidesError("Yeh badlav ab baaki nahi hai.")
    pl = p["payload"]
    c = get_client(tenant, pl["account"])
    try:
        if p["action"] == "delete":
            current = {s["objectId"] for s in c.get(pl["pid"]).get("slides", [])}
            gone = [i for i in pl["ids"] if i not in current]
            if gone:
                raise SlidesError("Card banne ke baad deck badal gaya; slides dobara chun kar boliye.")
            c.batch(pl["pid"], [{"deleteObject": {"objectId": i}} for i in pl["ids"]])
            msg = f"{p['summary']['title']}: {len(pl['ids'])} slides hata di. (Version history se wapas la sakte hain.)"
        elif p["action"] == "share":
            for e in pl["emails"]:
                c.share(pl["pid"], e, pl["role"])
            msg = f"{p['summary']['title']} share kar di: {', '.join(pl['emails'])}."
        else:
            raise SlidesError("unknown action")
    except SlidesError:
        with session() as s:
            s.get(SlidesPending, pend_id).status = "failed"
        raise
    with session() as s:
        s.get(SlidesPending, pend_id).status = "done"
    if p["conversation_id"]:
        bus.publish(p["conversation_id"], "slides", {"id": pl["pid"], "title": p["summary"]["title"],
                                                     "link": link_of(pl["pid"]), "status": p["action"] + "d"})
    return {"message": msg}
