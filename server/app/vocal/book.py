"""v0.999.143 STUDIO, PREMIUM (owner: the Studio design canvas -> "GO BUILD").

The parts of a long reading that the Studio page shows beside the chapters:

- importing a book with a look first: the parts found, the ones that are not the story (contents, copyright, thanks)
  left out unless she ticks them, the title, author and cover read from the book itself (EPUB / Word / PDF details),
  and what the whole book would take (words, about how long, about how many credits),
- the people of the whole book: every chapter's speakers found, how many lines each says, a line of theirs, two names
  that may be one person (she decides), and the narrator reading the people with fewer than 3 lines when she asks,
- one paragraph played on its own, from the recording kept when the chapter was made,
- a sound check of the made chapters, measured by ffmpeg (loudness, peaks), and which chapters are still to make.

The audiobook itself (pace, quiet between chapters, evening out the loudness, the cover and author in the file, a short
spoken line saying AI voices read it, or one MP3 per chapter in a zip) is made by `service.project_export`.
"""
from __future__ import annotations

import io
import re
import secrets
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from . import engines as EN
from . import service as V

FRONT = re.compile(r"^\s*(?:\d+\s*[·.:-]\s*)?(copyright|contents|table of contents|acknowledg\w*|thanks|dedication|about the author"
                   r"|also by\b|praise for|title page|index|imprint|colophon|bibliography)\b", re.I)
TOC_LINE = re.compile(r"(?:\.{3,}|\s{3,}|\t)\s*\d{1,4}\s*$")     # "Chapter 1 ........ 12": a contents line
WORDS_PER_MIN = 150          # an easy narrating pace
SMALL_LINES = 3              # fewer lines than this = a small part


def front_matter(title: str, text: str) -> str:
    """'' for the story; why not, for the parts around it."""
    body = (text or "").strip()
    if FRONT.match(title or "") or FRONT.match(body.split("\n", 1)[0]):
        return "Not the story"
    lines = [x for x in body.splitlines() if x.strip()]
    if lines and sum(1 for x in lines if TOC_LINE.search(x)) >= max(2, len(lines) // 2):
        return "Not the story"
    if len(body.split()) < 150 and re.search(r"©|all rights reserved|\bisbn\b", body, re.I):
        return "Not the story"
    return ""


def split(body: str) -> list[dict[str, str]]:
    """A book's text -> chapters: by its chapter headings, else in parts of about 12,000 characters. A chapter over
    the limit is split at a paragraph, never cut short."""
    heads = list(re.finditer(r"(?m)^(?:#{1,3}\s+(.{1,80})|((?:chapter|chapitre|capítulo|kapitel|capitolo|глава|adhyay|अध्याय)\s+\w+.{0,60}))\s*$", body, re.I))
    heads = [m for m in heads if not TOC_LINE.search(m.group(0))]
    chapters: list[dict[str, str]] = []
    if len(heads) >= 2:
        pre = body[:heads[0].start()].strip()
        if len(pre) > 5:
            chapters.append({"title": "Before the first chapter", "text": pre})
        for i, m in enumerate(heads):
            seg = body[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(body)].strip()
            if len(seg) > 5:
                chapters.append({"title": (m.group(1) or m.group(2) or f"Chapter {len(chapters) + 1}").strip(), "text": seg})
    if not chapters:
        cur = ""
        for para in re.split(r"\n\s*\n", body):
            if cur and len(cur) + len(para) > 12000:
                chapters.append({"title": f"Part {len(chapters) + 1}", "text": cur.strip()})
                cur = ""
            cur += para.strip() + "\n\n"
        if cur.strip():
            chapters.append({"title": f"Part {len(chapters) + 1}", "text": cur.strip()})
    out = []
    for c in chapters:
        while len(c["text"]) > V.MAX_CHAPTER:
            cut = c["text"].rfind("\n\n", 0, V.MAX_CHAPTER)
            cut = cut if cut > V.MAX_CHAPTER // 2 else V.MAX_CHAPTER
            out.append({"title": c["title"], "text": c["text"][:cut].strip()})
            c = {"title": c["title"] + " (cont.)", "text": c["text"][cut:].strip()}
        out.append(c)
    return out


def _x(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.S | re.I)
    return re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip() if m else ""


def meta_of(file_path: str) -> dict[str, Any]:
    """Title, author and the cover picture from the book's own details (EPUB, Word, PDF). Missing = empty."""
    out: dict[str, Any] = {"title": "", "author": "", "cover": b"", "cover_ext": ""}
    try:
        data = Path(file_path).read_bytes()
    except OSError:
        return out
    try:
        if data[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(data))
            names = z.namelist()
            if "docProps/core.xml" in names:
                core = z.read("docProps/core.xml").decode("utf-8", "ignore")
                out.update(title=_x(core, "dc:title"), author=_x(core, "dc:creator"))
                return out
            opf_path = ""
            if "META-INF/container.xml" in names:
                m = re.search(r'full-path="([^"]+)"', z.read("META-INF/container.xml").decode("utf-8", "ignore"))
                opf_path = m.group(1) if m else ""
            opf_path = opf_path or next((n for n in names if n.endswith(".opf")), "")
            if not opf_path:
                return out
            opf = z.read(opf_path).decode("utf-8", "ignore")
            out.update(title=_x(opf, "dc:title"), author=_x(opf, "dc:creator"))
            href = ""
            m = re.search(r'<item\b[^>]*properties="[^"]*cover-image[^"]*"[^>]*>', opf)
            if m:
                h = re.search(r'href="([^"]+)"', m.group(0))
                href = h.group(1) if h else ""
            if not href:
                m = re.search(r'<meta\b[^>]*name="cover"[^>]*content="([^"]+)"', opf) or re.search(r'<meta\b[^>]*content="([^"]+)"[^>]*name="cover"', opf)
                if m:
                    it = re.search(rf'<item\b[^>]*id="{re.escape(m.group(1))}"[^>]*>', opf)
                    h = re.search(r'href="([^"]+)"', it.group(0)) if it else None
                    href = h.group(1) if h else ""
            if href:
                base = opf_path.rsplit("/", 1)[0] + "/" if "/" in opf_path else ""
                full = base + href
                ext = full.rsplit(".", 1)[-1].lower()
                if ext in ("jpg", "jpeg", "png") and full in names:
                    img = z.read(full)
                    if len(img) <= 5 * 1024 * 1024 and (img[:3] == b"\xff\xd8\xff" or img[:8] == b"\x89PNG\r\n\x1a\n"):
                        out.update(cover=img, cover_ext="png" if img[:4] == b"\x89PNG" else "jpg")
        elif data[:4] == b"%PDF":
            from pypdf import PdfReader
            info = PdfReader(io.BytesIO(data)).metadata or {}
            out.update(title=str(info.get("/Title") or "").strip(), author=str(info.get("/Author") or "").strip())
    except Exception:   # noqa: BLE001 - details are a help, never a reason to refuse the book
        pass
    out["title"], out["author"] = V._clean(out["title"], 80), V._clean(out["author"], 80)
    return out


def _cover_ext(img: bytes) -> str:
    return "png" if img[:8] == b"\x89PNG\r\n\x1a\n" else "jpg" if img[:3] == b"\xff\xd8\xff" else ""


def _estimate(chars: int, words: int) -> dict[str, Any]:
    return {"seconds": round(words / WORDS_PER_MIN * 60), "credits": EN.quote("chapter", chars=chars)["credits"] if chars else 0}


def preview(tenant: str, file_path: str = "", url: str = "", text: str = "", title: str = "") -> dict[str, Any]:
    """What an import would make, saved nowhere: the parts found (the ones that are not the story unticked), title,
    author, language, the cover (kept for 2 hours under a token) and the totals."""
    from . import langs as L
    t_title, body = V.source_text(tenant, file_path, url, text)
    body = body.strip()
    if len(body) < 50:
        raise V.VocalError("There were no words to read in that.")
    chs = split(body)
    meta = meta_of(file_path) if file_path else {}
    parts = []
    for i, c in enumerate(chs):
        words = len(c["text"].split())
        why = front_matter(c["title"], c["text"])
        first = re.sub(r"\s+", " ", c["text"]).strip()[:140]
        parts.append({"n": i, "title": c["title"], "first": first, "words": words, "chars": len(c["text"]), "skip": bool(why),
                      "why": why, **_estimate(len(c["text"]), words)})
    token = ""
    if meta.get("cover"):
        token = "cv_" + secrets.token_hex(6)
        (V._home(tenant) / "pending" / f"{token}.{meta['cover_ext']}").write_bytes(meta["cover"])
    keep = [x for x in parts if not x["skip"]]
    return {"title": V._clean(title, 80) or meta.get("title") or V._clean(t_title, 80).rsplit(".", 1)[0] or "Imported reading",
            "author": meta.get("author") or "", "lang": L.detect(body[:3000]) or "en", "cover": token, "parts": parts,
            "words": sum(x["words"] for x in keep), "chars": sum(x["chars"] for x in keep),
            **_estimate(sum(x["chars"] for x in keep), sum(x["words"] for x in keep)), "max_chapters": V.MAX_CHAPTERS}


def cover_file(tenant: str, pid: str = "", token: str = "") -> Path:
    home = V._home(tenant)
    if token:
        if not re.fullmatch(r"cv_[0-9a-f]{12}", token):
            raise V.VocalError("That cover was not found.")
        f = next((x for x in (home / "pending").glob(f"{token}.*")), None)
    else:
        p = V._project(V._load(tenant), pid)
        f = home / "covers" / f"{p['id']}.{p.get('cover')}" if p.get("cover") else None
    if not f or not f.is_file():
        raise V.VocalError("That cover was not found.")
    return f


def keep_cover(tenant: str, pid: str, img: bytes) -> str:
    ext = _cover_ext(img)
    if not ext or len(img) > 5 * 1024 * 1024:
        raise V.VocalError("A cover is a JPG or PNG picture of up to 5 MB.")
    d = V._home(tenant) / "covers"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob(f"{pid}.*"):
        old.unlink(missing_ok=True)
    (d / f"{pid}.{ext}").write_bytes(img)
    return ext


def set_cover(tenant: str, pid: str, file_path: str) -> dict[str, Any]:
    """Her own picture as the cover of a reading."""
    ext = keep_cover(tenant, pid, Path(file_path).read_bytes())
    with V._LOCK:
        d = V._load(tenant)
        p = V._project(d, pid)
        p["cover"] = ext
        V._store(tenant, d)
    return p


# ---------------------------------------------------------------- the people of the whole book
KIN = [{"papa", "father", "dad", "daddy", "baba", "appa", "abba", "pitaji", "pa"},
       {"mama", "mother", "mom", "mum", "mummy", "maa", "amma", "ammi", "mataji", "ma"},
       {"grandma", "granny", "grandmother", "nani", "dadi", "gran", "nana ji"},
       {"grandpa", "grandfather", "grandad", "granddad", "dada", "nana"}]


def _same(a: str, b: str) -> str:
    """Why two names may be one person ('' when not)."""
    x, y = a.lower().strip(), b.lower().strip()
    if any(x in g and y in g for g in KIN):
        return f"“{a}” and “{b}” may be the same person."
    wx, wy = set(re.findall(r"\w{3,}", x)), set(re.findall(r"\w{3,}", y))
    if wx and wy and (wx <= wy or wy <= wx) and x != y:
        return f"“{a}” and “{b}” may be the same person (one name is part of the other)."
    return ""


def _counts(p: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for n, c in enumerate(p.get("chapters") or []):
        for para in c.get("paragraphs") or []:
            w = para.get("who") or "Narrator"
            e = out.setdefault(w, {"lines": 0, "chapters": [], "quote": ""})
            e["lines"] += 1
            if n not in e["chapters"]:
                e["chapters"].append(n)
            if not e["quote"]:
                e["quote"] = re.sub(r"\s+", " ", para.get("text") or "")[:140]
    return out


def small_people(p: dict[str, Any]) -> set[str]:
    """The people the narrator reads when she asks for it (fewer than SMALL_LINES lines in the whole book)."""
    if not p.get("small"):
        return set()
    return {w for w, e in _counts(p).items() if w != "Narrator" and e["lines"] < SMALL_LINES}


def people(tenant: str, pid: str) -> dict[str, Any]:
    p = V._project(V._load(tenant), pid)
    cnt = _counts(p)
    cast = {**(p.get("cast") or {})}
    narr = cast.get("Narrator") or p.get("voice") or ""
    small = small_people(p)
    rows = [{"name": "Narrator", "lines": cnt.get("Narrator", {}).get("lines", 0), "chapters": cnt.get("Narrator", {}).get("chapters", []),
             "quote": cnt.get("Narrator", {}).get("quote", ""), "voice": narr, "small": False}]
    names = sorted((w for w in set(cnt) | {k for k in cast if k != "Narrator"} if w != "Narrator"), key=lambda w: -cnt.get(w, {}).get("lines", 0))
    for w in names:
        e = cnt.get(w, {"lines": 0, "chapters": [], "quote": ""})
        rows.append({"name": w, "lines": e["lines"], "chapters": e["chapters"], "quote": e["quote"], "voice": cast.get(w, ""),
                     "small": w in small})
    apart = {tuple(sorted(x)) for x in p.get("apart") or []}
    sugg = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            why = _same(a, b)
            if why and tuple(sorted((a, b))) not in apart:
                sugg.append({"a": a, "b": b, "why": why})
    found = sum(1 for c in p.get("chapters") or [] if c.get("paragraphs"))
    return {"people": rows, "found": found, "total": len(p.get("chapters") or []), "small": bool(p.get("small")),
            "suggestions": sugg[:4], "small_lines": SMALL_LINES}


async def find_people(tenant: str, pid: str) -> dict[str, Any]:
    """Who speaks in every chapter not looked at yet (one model call a chapter, nothing read aloud)."""
    p = V._project(V._load(tenant), pid)
    todo = [n for n, c in enumerate(p.get("chapters") or []) if not c.get("paragraphs") and (c.get("text") or "").strip()]
    for n in todo:
        await V.project_cast(tenant, pid, n)
    out = people(tenant, pid)
    out["looked"] = len(todo)
    return out


def merge(tenant: str, pid: str, keep: Any, drop: Any) -> dict[str, Any]:
    """Two names made one person: every line of `drop` goes to `keep`, and `drop` leaves the cast."""
    keep, drop = V._clean(keep, 40), V._clean(drop, 40)
    if not keep or not drop or keep == drop or "Narrator" in (keep, drop):
        raise V.VocalError("Choose two different people to make one.")
    with V._LOCK:
        d = V._load(tenant)
        p = V._project(d, pid)
        for c in p.get("chapters") or []:
            for para in c.get("paragraphs") or []:
                if para.get("who") == drop:
                    para["who"] = keep
        (p.get("cast") or {}).pop(drop, None)
        V._store(tenant, d)
    return people(tenant, pid)


def apart(tenant: str, pid: str, a: Any, b: Any) -> dict[str, Any]:
    a, b = V._clean(a, 40), V._clean(b, 40)
    with V._LOCK:
        d = V._load(tenant)
        p = V._project(d, pid)
        pair = sorted([a, b])
        if pair not in (p.get("apart") or []):
            p.setdefault("apart", []).append(pair)
        V._store(tenant, d)
    return people(tenant, pid)


def set_people(tenant: str, pid: str, voices: Any = None, small: Any = None) -> dict[str, Any]:
    """Her voices for the people (checked) and whether the narrator reads the small parts."""
    with V._LOCK:
        d = V._load(tenant)
        p = V._project(d, pid)
        cast = dict(p.get("cast") or {})
        for name, vid in (voices or {}).items() if isinstance(voices, dict) else []:
            name = V._clean(name, 40)
            if not name or not vid:
                continue
            v = V._voice(d, str(vid))
            if v.get("ready") is False:
                raise V.VocalError(f"{v.get('name') or 'That voice'} is not ready yet.")
            cast[name] = v["id"]
            if name == "Narrator":
                p["voice"] = v["id"]
        p["cast"] = cast
        if small is not None:
            p["small"] = bool(small)
        V._store(tenant, d)
    return people(tenant, pid)


# ---------------------------------------------------------------- one paragraph, and the sound check
def para_file(tenant: str, pid: str, n: Any, k: Any) -> Path:
    """The kept recording of paragraph k of chapter n, as it reads now (her words, its speaker's voice, the pace)."""
    d = V._load(tenant)
    p = V._project(d, pid)
    try:
        c = p["chapters"][int(n)]
    except (IndexError, TypeError, ValueError):
        raise V.VocalError("That chapter was not found.") from None
    paras = V._paragraphs(c)
    try:
        para = paras[int(k)]
    except (IndexError, TypeError, ValueError):
        raise V.VocalError("That paragraph was not found.") from None
    f = V._home(tenant) / "para" / f"{V._para_key(d, p, para)[0]}.wav"
    if not f.is_file():
        raise V.VocalError("This paragraph has not been read as it is now. Make the changes to hear it.")
    return f


def set_who(tenant: str, pid: str, n: Any, k: Any, who: Any) -> dict[str, Any]:
    """Who says paragraph k of chapter n (the narrator, or a person of the book). It is read again in that voice the
    next time the chapter's changes are made."""
    who = V._clean(who, 40) or "Narrator"
    with V._LOCK:
        d = V._load(tenant)
        p = V._project(d, pid)
        try:
            c = p["chapters"][int(n)]
            paras = V._paragraphs(c)
            paras[int(k)]["who"] = who
        except (IndexError, TypeError, ValueError):
            raise V.VocalError("That paragraph was not found.") from None
        c["paragraphs"] = paras
        V._store(tenant, d)
        return p


def _measure(path: Path) -> dict[str, float]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=900)
    tail = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    i = re.search(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", tail)
    pk = re.search(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", tail)
    val = lambda m: -70.0 if not m or m.group(1) == "-inf" else float(m.group(1))  # noqa: E731
    return {"lufs": round(val(i), 1), "peak": round(val(pk), 1)}


def check(tenant: str, pid: str) -> dict[str, Any]:
    """The sound check before the audiobook is put together: every chapter made, the loudness of each made chapter and
    its loudest peak (measured by ffmpeg, kept per recording), one voice per person across the made chapters."""
    d = V._load(tenant)
    p = V._project(d, pid)
    chs = p.get("chapters") or []
    made = [(n, c) for n, c in enumerate(chs) if c.get("audio")]
    missing = [n for n, c in enumerate(chs) if not c.get("audio")]
    rows = [{"id": "made", "name": "Every chapter made", "ok": not missing and bool(chs),
             "note": "All chapters are made." if not missing else f"{_list(missing)} {'is' if len(missing) == 1 else 'are'} not made yet.",
             "value": f"{len(made)} of {len(chs)}"}]
    home = V._home(tenant)
    if not shutil.which("ffmpeg"):
        rows.append({"id": "loud", "name": "Loudness", "ok": None, "note": "Not measured: ffmpeg is not installed on this server.", "value": ""})
    elif made:
        seen = dict(p.get("loud") or {})
        res = []
        for n, c in made:
            got = seen.get(c["audio"])
            if not got:
                f = home / "audio" / f"{c['audio']}.wav"
                if not f.is_file():
                    continue
                got = _measure(f)
                seen[c["audio"]] = got
            res.append(got)
        with V._LOCK:
            d2 = V._load(tenant)
            p2 = V._project(d2, pid)
            p2["loud"] = {k: v for k, v in seen.items() if any(x.get("audio") == k for x in p2.get("chapters") or [])}
            V._store(tenant, d2)
        if res:
            lo, hi = min(x["lufs"] for x in res), max(x["lufs"] for x in res)
            even = hi - lo <= 3 and -24 <= lo and hi <= -14
            rows.append({"id": "loud", "name": "Loudness", "ok": even,
                         "note": "Even across chapters, right for listening apps." if even else
                         "The chapters are not equally loud. “Even out the loudness” fixes it when the book is put together.",
                         "value": f"{lo} LUFS" if lo == hi else f"{lo} to {hi} LUFS"})
            peak = max(x["peak"] for x in res)
            rows.append({"id": "peak", "name": "Peaks", "ok": peak <= -1.0,
                         "note": "Nothing clips." if peak <= -1.0 else "Some peaks are too loud. “Even out the loudness” brings them down.",
                         "value": f"{peak} dB"})
    gap = V._gap(p)
    rows.append({"id": "gap", "name": "Quiet between chapters", "ok": 0.5 <= gap <= 5.0,
                 "note": "Between half a second and 5 seconds.", "value": f"{gap} s"})
    voices: dict[str, set[str]] = {}
    for _, c in made:
        for s in c.get("segments") or []:
            if s.get("voice"):
                voices.setdefault(s.get("who") or "Narrator", set()).add(s["voice"])
    if voices:
        two = [w for w, vs in voices.items() if len(vs) > 1]
        rows.append({"id": "voices", "name": "One voice per person", "ok": not two,
                     "note": "Each person has the same voice in every made chapter." if not two else
                     f"{', '.join(two[:3])} {'has' if len(two) == 1 else 'have'} a different voice in some chapters. Make those chapters again.",
                     "value": f"{len(voices)} {'voice' if len(voices) == 1 else 'people'}"})
    return {"checks": rows, "ready": not missing and bool(chs), "missing": missing, "seconds": round(sum(float(c.get("seconds") or 0) for _, c in made)),
            "chapters": len(chs), "made": len(made), "gap": V._gap(p), "ffmpeg": bool(shutil.which("ffmpeg"))}


def _list(ns: list[int]) -> str:
    s = [f"Chapter {n + 1}" for n in ns[:4]]
    more = f" and {len(ns) - 4} more" if len(ns) > 4 else ""
    return (", ".join(s[:-1]) + " and " + s[-1] if len(s) > 1 else s[0]) + more if s else ""
