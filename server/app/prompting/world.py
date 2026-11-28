"""World prompts: the prompts.chat library (CC0 1.0, public domain) as a read-only shelf in Hoola Prompting.

Built once from prompts.chat's prompts.csv by `python -m app.prompting.world build <prompts.csv>` into
world/world.json.gz (committed). The build keeps only what fits Hoola, each drop counted by its reason:
  - not code-only (their for_devs column), not a JSON / YAML block (their STRUCTURED type): text and picture prompts
  - 80 to 1,800 characters (a brief's text holds 2,000; room is left for her values)
  - English, not gibberish, at most 8 blanks
  - Hoola's share screen passes (no "ignore your rules", no jailbreak, no password / OTP / card ask, no link, no
    send-or-pay-without-asking) and none of the unsafe words below
  - not a near copy of a prompt already kept (dupe.SAME)
Every blank shape is read by the paste reader and becomes a named blank. Opening one makes a brief in her workbench:
a blank she fills is put in, a blank she leaves empty stays as [Name] - the author's default is shown as an example,
never used. The prompt text itself is the author's, kept word for word; the brief's source says so. Outcomes go into
the ledger under recipe `world:<id>`. These are not shown on Hoola's public /prompts pages (they are someone else's
words; Hoola's own pages carry Hoola's own recipes)."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import dupe as DU
from . import paste as P

DATA = Path(__file__).resolve().parent / "world" / "world.json.gz"
PREFIX = "world:"
SOURCE = {"name": "prompts.chat", "url": "https://github.com/f/prompts.chat", "licence": "CC0 1.0 (public domain)"}
MIN_CHARS, MAX_CHARS, MAX_BLANKS = 80, 1800, 8
PAGE = 24

_UNSAFE = re.compile(
    r"\b(nsfw|porn\w*|nude|nudity|naked|erotic\w*|sexual\w*|sexy|fetish\w*|onlyfans|explicit|gore|uncensored|"
    r"unfiltered|no (?:restrictions|limits|filters|rules)|without (?:any )?(?:restrictions|filters|limits)|"
    r"developer mode|jailbr\w*|dan mode|do anything now|malware|ransomware|phishing|keylogger|exploit\w*|"
    r"hack(?:ing|er)?|drugs?|weapons?|bomb|suicid\w*|self[- ]harm|racis\w*|hate speech)\b", re.I)

GROUPS: list[tuple[str, str, tuple[str, ...]]] = [
    ("pictures", "Pictures", ()),
    ("video", "Video clips", ()),
    ("business", "Business and marketing", ("market", "sales", "business", "brand", "seo", "advert", "customer", "startup",
                                            "product", "copywrit", "social media", "instagram", "linkedin", "email",
                                            "entrepreneur", "ecommerce", "e-commerce", "finance", "invest", "accountant")),
    ("writing", "Writing", ("writer", "write", "story", "poet", "poem", "novel", "essay", "blog", "edit", "proofread",
                            "screenwrit", "journalist", "content", "translat", "grammar", "lyric")),
    ("learning", "Learning and teaching", ("teacher", "tutor", "teach", "explain", "learn", "student", "course",
                                           "lesson", "quiz", "exam", "professor", "math", "language", "study")),
    ("career", "Career and work", ("interview", "career", "resume", "cv", "job", "recruit", "hr ", "manager",
                                   "meeting", "productiv", "coach", "negotiat", "leader")),
    ("life", "Health and life", ("health", "doctor", "fitness", "diet", "nutrition", "therap", "mental", "travel",
                                 "chef", "cook", "recipe", "relationship", "parent", "lifestyle", "mindful", "yoga")),
    ("fun", "Fun and games", ("game", "play", "fun", "joke", "comedian", "riddle", "trivia", "character", "rpg",
                              "adventure", "magician", "movie", "music")),
    ("experts", "Experts and advisors", ("analyst", "consultant", "advisor", "adviser", "expert", "specialist", "lawyer",
                                         "legal", "engineer", "architect", "scientist", "researcher", "strategist",
                                         "planner", "designer", "reviewer", "auditor", "historian", "psycholog")),
    ("other", "Everything else", ()),
]
GROUP_LABEL = {k: v for k, v, _ in GROUPS}


def _group(title: str, text: str, kind: str) -> str:
    if kind == "image":
        return "pictures"
    if kind == "video":
        return "video"
    hay = (title + " " + title + " " + text[:300]).lower()
    best, hits = "other", 0
    for key, _, words in GROUPS:
        n = sum(1 for w in words if w in hay)
        if n > hits:
            best, hits = key, n
    return best


_EN = set("the and to of a an in you is for with your that on as be this are it will i me my or by from at not".split())


def _english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(1 for c in letters if c.isascii()) / len(letters) < 0.98:
        return False
    words = re.findall(r"[a-z']+", text.lower())
    return bool(words) and sum(1 for w in words if w in _EN) / len(words) >= 0.08


_PIC = ("photorealistic", "cinematic lighting", "highly detailed", "ultra detailed", "8k", "4k", "--ar", "midjourney",
        "depth of field", "bokeh", "shot on", "lens", "render", "illustration", "portrait of", "wide shot", "close-up",
        "close up", "soft light", "golden hour", "aspect ratio", "hyperrealistic", "photography", "studio lighting",
        "realistic photo", "image of", "an image", "the image", "watercolor", "oil painting", "concept art")
_VID = ("video", "camera pans", "camera moves", "tracking shot", "slow motion", "the camera", "seconds", "scene 1",
        "frames", "footage", "drone shot", "dolly")


def _kind(title: str, text: str, kind: str) -> str:
    if kind == "IMAGE":
        return "image"
    low = (title + " " + text).lower()
    if re.match(r"\s*(act as|i want you to act|you are)\b", text.lower()):
        return "chat"
    vid, pic = sum(1 for w in _VID if w in low), sum(1 for w in _PIC if w in low)
    if vid >= 2 and vid >= pic:
        return "video"
    return "image" if pic >= 2 else "chat"


def _gibberish(text: str) -> bool:
    if re.search(r"(.)\1{5,}", text):
        return True
    low = text.lower()
    if any(p in low for p in ("qwerty", "asdfgh", "zxcvbn")):
        return True
    v = len(re.findall(r"[aeiou]", low))
    c = len(re.findall(r"[bcdfghjklmnpqrstvwxyz]", low))
    return c > 0 and v / c < 0.15


def _id(title: str, text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "prompt"
    return f"{slug}-{hashlib.sha1(text.encode()).hexdigest()[:6]}"


def _mark(text: str) -> str:
    """Every blank written one way: ${key}, so use() fills them all with one rule."""
    parts, last = [], 0
    for v in P.find(text):
        parts += [text[last:v["start"]], "${" + v["key"] + "}"]
        last = v["end"]
    return "".join(parts) + text[last:]


def judge(row: dict[str, str]) -> tuple[dict[str, Any] | None, str]:
    """One CSV row -> (kept entry, "") or (None, why dropped)."""
    from . import store as S
    title = (row.get("act") or "").strip()[:80]
    text = (row.get("prompt") or "").replace("\r\n", "\n").strip()
    kind = (row.get("type") or "TEXT").strip().upper()
    if str(row.get("for_devs") or "").strip().upper() == "TRUE":
        return None, "code only"
    if kind not in ("TEXT", "IMAGE"):
        return None, "JSON or YAML block"
    if not title or len(text) < MIN_CHARS:
        return None, "too short"
    if len(text) > MAX_CHARS:
        return None, "too long for a brief"
    if not _english(title + " " + text):
        return None, "not English"
    if _gibberish(text):
        return None, "gibberish"
    if _UNSAFE.search(title + " " + text):
        return None, "unsafe words"
    if S.screen({"intent": text, "slots": {}}):
        return None, "fails Hoola's share screen"
    blanks = P.blanks(text)
    if len(blanks) > MAX_BLANKS:
        return None, "too many blanks"
    sec = _kind(title, text, kind)
    return {"id": _id(title, text), "title": title, "section": sec, "group": _group(title, text, sec),
            "text": _mark(text), "blanks": blanks, "by": (row.get("contributor") or "").strip()[:40]}, ""


def build(csv_path: str | Path, out: str | Path = DATA, commit: str = "") -> dict[str, Any]:
    csv.field_size_limit(10 ** 8)
    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    kept: list[dict[str, Any]] = []
    dropped: dict[str, int] = {}
    seen_ids: set[str] = set()
    norms: list[str] = []
    for row in rows:
        e, why = judge(row)
        if e is not None:
            norm = DU.normalise(e["text"])
            if e["id"] in seen_ids or any(DU.similarity(norm, other) >= DU.SAME for other in norms
                                          if abs(len(other) - len(norm)) < max(len(norm), 1) * 0.3):
                e, why = None, "near copy of another prompt"
            else:
                norms.append(norm)
                seen_ids.add(e["id"])
        if e is None:
            dropped[why] = dropped.get(why, 0) + 1
        else:
            kept.append(e)
    meta = {**SOURCE, "commit": commit, "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "read": len(rows),
            "kept": len(kept), "dropped": dict(sorted(dropped.items(), key=lambda x: -x[1]))}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump({"meta": meta, "items": kept}, f, ensure_ascii=False, separators=(",", ":"))
    _load.cache_clear()
    return meta


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    if not DATA.exists():
        return {"meta": {**SOURCE, "kept": 0}, "items": []}
    with gzip.open(DATA, "rt", encoding="utf-8") as f:
        d = json.load(f)
    d["by_id"] = {e["id"]: e for e in d["items"]}
    for e in d["items"]:
        e["_hay"] = (e["title"] + " " + e["title"] + " " + e["text"]).lower()
    return d


def on() -> bool:
    from ..config import get_settings
    return bool(getattr(get_settings(), "prompting_world", True))


def meta() -> dict[str, Any]:
    return dict(_load()["meta"])


def _public(e: dict[str, Any], full: bool = False) -> dict[str, Any]:
    out = {"id": PREFIX + e["id"], "section": e["section"], "title": e["title"], "group": e["group"],
           "group_label": GROUP_LABEL.get(e["group"], ""), "makes": GROUP_LABEL.get(e["group"], ""),
           "blanks": e["blanks"], "starter": False, "world": True, "by": e.get("by") or ""}
    if full:
        out["text"] = e["text"]
    return out


def search(q: str = "", group: str = "", page: int = 1) -> dict[str, Any]:
    if not on():
        return {"on": False, "items": [], "total": 0, "groups": [], "source": SOURCE}
    d = _load()
    words = [w for w in (q or "").lower().split() if w][:8]
    hits = []
    for e in d["items"]:
        if group and e["group"] != group:
            continue
        if words and not all(w in e["_hay"] for w in words):
            continue
        score = sum(3 if w in e["title"].lower() else 1 for w in words)
        hits.append((score, e))
    if words:
        hits.sort(key=lambda x: -x[0])
    try:                                         # NATIJA KHATA: kept counts, as on Hoola's own recipes
        from . import ledger as L
        rates = {k: v for k, v in L.recipe_rates().items() if k.startswith(PREFIX)}
    except Exception:       # noqa: BLE001
        rates = {}
    page = max(1, int(page or 1))
    items = []
    for _, e in hits[(page - 1) * PAGE: page * PAGE]:
        x = _public(e)
        if x["id"] in rates:
            x["kept"] = rates[x["id"]]
        items.append(x)
    counts: dict[str, int] = {}
    for e in d["items"]:
        counts[e["group"]] = counts.get(e["group"], 0) + 1
    return {"on": True, "items": items, "total": len(hits), "page": page, "pages": max(1, -(-len(hits) // PAGE)),
            "groups": [{"key": k, "label": lab, "n": counts.get(k, 0)} for k, lab, _ in GROUPS if counts.get(k)],
            "source": {**SOURCE, "kept": d["meta"].get("kept", 0)}}


def get(wid: str) -> dict[str, Any] | None:
    if not on():
        return None
    e = _load()["by_id"].get(wid.removeprefix(PREFIX))
    return _public(e, full=True) if e else None


def texts() -> list[dict[str, str]]:
    """For the duplicate check: {id, title, text}."""
    return [{"id": PREFIX + e["id"], "title": e["title"], "text": e["text"]} for e in _load()["items"]]


def use(wid: str, values: dict[str, str] | None = None) -> dict[str, Any]:
    """A world prompt with her values -> {"brief": ...}. Empty blanks stay [Name]; defaults are never used."""
    from . import brief as B
    e = _load()["by_id"].get(wid.removeprefix(PREFIX)) if on() else None
    if e is None:
        raise ValueError("No such prompt.")
    got = P.fill(e["text"], values or {})
    slots: dict[str, Any] = {}
    if e["section"] == "chat":
        slots["goal"] = {"value": f"Use the \"{e['title']}\" prompt", "source": "recipe"}
    raw = {"section": e["section"], "intent": got["text"], "slots": slots, "recipe_id": PREFIX + e["id"]}
    return {"brief": B.validate(raw)}


if __name__ == "__main__":          # python -m app.prompting.world build <prompts.csv> [commit]
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        print(json.dumps(build(sys.argv[2], commit=sys.argv[3] if len(sys.argv) > 3 else ""), indent=1))
    else:
        print("usage: python -m app.prompting.world build <prompts.csv> [commit]")
