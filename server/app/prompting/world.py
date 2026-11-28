"""World prompts: the whole prompts.chat library (CC0 1.0, public domain) as a read-only shelf in Hoola Prompting.

Built from prompts.chat's own full export (https://prompts.chat/prompts.json?full_content=true) or its prompts.csv by
`python -m app.prompting.world build <prompts.json|prompts.csv> [commit]` into world/world.json.gz (committed).
EVERY prompt is kept (owner, 28 Nov 2026: "INCLUDE ALL 100 %"). Nothing is dropped; what Hoola's checks found is shown
on the prompt as a note instead: too long for a brief, a JSON / YAML block, code only, too short, not English,
unsafe words, fails Hoola's share screen, gibberish, many blanks, near copy of another prompt.
How a prompt is used depends on its notes:
  - a prompt that fits a brief (2,000 characters) and has no safety note opens in her workbench like a recipe
  - a longer one is filled in place (her blanks in, empty ones left [Name]) and copied or put in her Hoola chat
  - one with a safety note (unsafe words / fails the share screen) is shown and can be copied, but Hoola does not
    run it through its own workbench or chat
Every blank shape is read by the paste reader and becomes a named blank; the author's default is shown as an example,
never used. The prompt text is the author's, kept word for word. Outcomes go into the ledger under recipe
`world:<id>`. These are not shown on Hoola's public /prompts pages (they are someone else's words)."""
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

_UNSAFE = re.compile(                         # a safety note only for real jailbreak / sexual / malware prompts
    r"\b(nsfw|porn\w*|nude|naked|erotic\w*|fetish\w*|onlyfans|uncensored|unfiltered|no (?:restrictions|filters)|"
    r"without (?:any )?(?:restrictions|filters)|developer mode|jailbr\w*|dan mode|do anything now|ransomware|"
    r"keylogger)\b", re.I)
_IGNORE_RULES = re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|above|earlier|prior|all)\b.{0,30}"
                           r"\b(instructions?|rules?|guidelines?)\b", re.I)

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
    if re.search(r"([a-zA-Z])\1{5,}", text):
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


NOTES = {
    "long": "Too long for a brief",
    "structured": "Written as a JSON or YAML block",
    "code": "Code only, for developers",
    "short": "Very short",
    "lang": "In another language",
    "unsafe": "Has unsafe words",
    "screen": "Asks the AI to ignore its rules",
    "gibberish": "Looks like gibberish",
    "blanks": "Many blanks",
    "copy": "Near copy of another prompt",
}
SAFETY = ("unsafe", "screen")                 # Hoola shows and copies these, but does not run them itself
BRIEF_MAX = 2000                              # a brief's text (brief.MAX_TEXT)
KINDS = [("text", "Text"), ("image", "Pictures"), ("video", "Video"), ("skill", "Agent skills"),
         ("taste", "Code style"), ("audio", "Audio"), ("structured", "JSON / YAML")]
KIND_LABEL = dict(KINDS)


# Pictures and videos the authors made with their prompts. Only from the hosts prompts.chat really uses, https only;
# they are fetched once by the server and kept as small copies (worldmedia.py), never hot-linked to her browser.
MEDIA_HOSTS = ("prompts-chat-space.fra1.digitaloceanspaces.com", "v3b.fal.media", "cdn1.wiro.ai", "i.ibb.co",
               "pbs.twimg.com", "ik.imagekit.io")
_VIDEO_EXT, _AUDIO_EXT = (".mp4", ".webm", ".mov"), (".wav", ".mp3", ".m4a", ".ogg")


def media_url(url: Any) -> str:
    """The author's picture / video link when it is https on a known host, else ''."""
    from urllib.parse import urlsplit
    u = str(url or "").strip()
    try:
        p = urlsplit(u)
    except ValueError:
        return ""
    if p.scheme != "https" or (p.hostname or "").lower() not in MEDIA_HOSTS or p.username or p.password or p.port:
        return ""
    return u[:500]


def media_type(url: str) -> str:
    path = url.split("?", 1)[0].lower()
    return "video" if path.endswith(_VIDEO_EXT) else "audio" if path.endswith(_AUDIO_EXT) else "image"


# The site's 53 categories in 8 families, for the category rail and the Make-a-prompt list. A category not listed
# here (a new one on prompts.chat) goes to "Everything else" - nothing is ever hidden.
FAMILIES: list[tuple[str, str, tuple[str, ...]]] = [
    ("media", "Pictures, video & sound", ("image-generation", "video-generation", "design", "music")),
    ("code", "Code & building", ("coding", "web-development", "vibe-coding", "devops", "data-science",
                                 "mobile-development", "github-sponsors-profile")),
    ("agents", "Agents & automation", ("agent-skill", "agent-workflows", "automations", "workflows",
                                       "automation-workflows")),
    ("writing", "Writing", ("creative", "writing", "academic-writing", "technical-writing", "blog-writing",
                            "email-communication", "copywriting")),
    ("work", "Business & work", ("productivity", "business", "marketing", "finance-budgeting", "hr-recruiting",
                                 "startup-entrepreneurship", "sales", "market-analysis", "business-planning",
                                 "note-taking", "leadership-management", "business-strategy", "marketing-sales",
                                 "meeting-collaboration")),
    ("learning", "Learning & research", ("research-analysis", "education", "learning-skills", "teaching-instruction",
                                         "exam-preparation", "language-learning", "stem-science",
                                         "kids-early-learning", "tutoring-homework-help", "course-creation")),
    ("life", "Life & wellbeing", ("health-wellness", "self-improvement", "mindset-motivation", "habits-routines",
                                  "journaling-reflection")),
    ("other", "Everything else", ()),
]
FAMILY_OF = {g: k for k, _, gs in FAMILIES for g in gs}
# Which Hoola section a category's "Make a prompt" opens in (the workbench, then the engine's own screen).
CAT_SECTION = {"image-generation": "image", "design": "image", "video-generation": "video", "music": "music",
               "web-development": "web", "mobile-development": "app", "vibe-coding": "code", "coding": "code",
               "devops": "code", "github-sponsors-profile": "code", "data-science": "data",
               "research-analysis": "research", "market-analysis": "research", "marketing": "marketing",
               "marketing-sales": "marketing", "sales": "marketing", "copywriting": "marketing",
               "blog-writing": "marketing", "email-communication": "marketing", "business": "doc",
               "business-planning": "doc", "business-strategy": "doc", "finance-budgeting": "doc",
               "hr-recruiting": "doc", "startup-entrepreneurship": "doc", "leadership-management": "doc",
               "agent-skill": "aiapp", "agent-workflows": "aiapp"}


def families(counts: dict[str, list] | None = None) -> list[dict[str, Any]]:
    """[{key, label, total, cats: [{key, label, n, section}]}] in the order above, each family's categories by size."""
    if counts is None:
        counts = {}
        for e in _load()["items"]:
            c = counts.setdefault(e["group"], [e.get("cat") or GROUP_LABEL.get(e["group"], e["group"]), 0])
            c[1] += 1
    out = []
    for key, label, _ in FAMILIES:
        cats = sorted(({"key": g, "label": v[0], "n": v[1], "section": CAT_SECTION.get(g, "chat")}
                       for g, v in counts.items() if FAMILY_OF.get(g, "other") == key), key=lambda c: -c["n"])
        if cats:
            out.append({"key": key, "label": label, "total": sum(c["n"] for c in cats), "cats": cats})
    return out


def outline(text: str, most: int = 10) -> dict[str, Any]:
    """A long prompt as its parts: the lines before the first heading, then each heading (a line in CAPITALS or a
    Markdown heading) with the start of what follows. Only for showing it; the prompt itself is never changed."""
    lines = text.split("\n")
    heads = []
    for i, ln in enumerate(lines):
        t = ln.strip()
        md = re.match(r"#{1,4}\s+(.{2,80})$", t)
        caps = re.fullmatch(r"[A-Z0-9][A-Z0-9 &/:,.'()\-]{2,60}", t) and sum(c.isalpha() for c in t) >= 3
        if md or caps:
            heads.append((i, (md.group(1) if md else t).strip().rstrip(":")))
    if len(heads) < 2:
        return {"lead": "", "parts": []}
    lead = " ".join(" ".join(lines[:heads[0][0]]).split())[:600]
    parts = []
    for n, (i, h) in enumerate(heads[:most]):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        body = " ".join(" ".join(lines[i + 1:end]).split())
        parts.append({"head": h[:80], "first": body[:220] + ("…" if len(body) > 220 else "")})
    return {"lead": lead, "parts": parts, "more": max(0, len(heads) - most)}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")[:40] or "other"


def _row(raw: dict[str, Any]) -> dict[str, Any]:
    """A prompts.json prompt or a prompts.csv row -> one shape."""
    if "content" in raw or "category" in raw:
        cat = raw.get("category") or {}
        return {"title": str(raw.get("title") or "").strip()[:80], "text": str(raw.get("content") or ""),
                # the site's own category; one it left without a category is its "Other", never Hoola's guess
                "type": str(raw.get("type") or "TEXT").upper(), "cat": str(cat.get("name") or "").strip() or "Other",
                "code": False, "by": str((raw.get("author") or {}).get("username") or "")[:40],
                "tags": [str(t.get("name")) for t in (raw.get("tags") or []) if t.get("name")][:8],
                "votes": int(raw.get("voteCount") or 0),
                "name": str((raw.get("author") or {}).get("name") or "").strip()[:60],
                "desc": " ".join(str(raw.get("description") or "").split())[:900],
                "media": media_url(raw.get("mediaUrl")), "created": str(raw.get("createdAt") or "")[:10],
                "needs": (str(raw.get("requiredMediaType") or "").lower() or "image") if raw.get("requiresMediaUpload") else ""}
    return {"title": str(raw.get("act") or "").strip()[:80], "text": str(raw.get("prompt") or ""),
            "type": str(raw.get("type") or "TEXT").upper(), "cat": "",
            "code": str(raw.get("for_devs") or "").strip().upper() == "TRUE",
            "by": str(raw.get("contributor") or "").strip()[:40], "tags": [], "votes": 0,
            "name": "", "desc": "", "media": "", "created": "", "needs": ""}


def judge(raw: dict[str, Any]) -> dict[str, Any]:
    """One prompt -> its shelf entry. Never dropped; what the checks found is in `notes`."""
    r = _row(raw)
    title = r["title"] or "Untitled prompt"
    text = r["text"].replace("\r\n", "\n").strip()
    typ = r["type"]
    notes = []
    if len(text) > BRIEF_MAX:
        notes.append("long")
    if typ == "STRUCTURED" or re.match(r"\s*[\[{]", text) and re.search(r'"\s*:', text[:400]) \
            or re.match(r"\s*(---\s*\n)?[a-z_]+:\s", text) and typ != "SKILL":
        notes.append("structured")
    if r["code"] or typ == "TASTE":
        notes.append("code")
    if len(text) < MIN_CHARS:
        notes.append("short")
    if not _english(title + " " + text[:4000]):
        notes.append("lang")
    if _gibberish(text[:4000]):
        notes.append("gibberish")
    if _UNSAFE.search(title + " " + text):
        notes.append("unsafe")
    if _IGNORE_RULES.search(text):
        notes.append("screen")
    blanks = P.blanks(text, limit=40)
    if len(blanks) > MAX_BLANKS:
        notes.append("blanks")
    kind = {"IMAGE": "image", "VIDEO": "video", "SKILL": "skill", "TASTE": "taste", "AUDIO": "audio",
            "STRUCTURED": "structured"}.get(typ, "text")
    sec = "image" if kind == "image" else "video" if kind == "video" else (
        _kind(title, text, typ) if kind == "text" and not r["cat"] else "chat")
    if kind == "text" and sec in ("image", "video"):
        kind = sec
    cat = r["cat"] or GROUP_LABEL[_group(title, text, sec)]
    return {"id": _id(title, text), "title": title, "section": sec, "kind": kind, "group": _slug(cat), "cat": cat,
            "text": _mark(text), "blanks": blanks, "by": r["by"], "tags": r["tags"], "votes": r["votes"],
            "notes": notes, "name": r.get("name") or "", "desc": r.get("desc") or "", "media": r.get("media") or "",
            "created": r.get("created") or "", "needs": r.get("needs") or ""}


def _read(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        d = json.loads(path.read_text(encoding="utf-8"))
        return list(d.get("prompts") or d) if isinstance(d, dict) else list(d)
    csv.field_size_limit(10 ** 8)
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build(src: str | Path, out: str | Path = DATA, commit: str = "") -> dict[str, Any]:
    rows = _read(src)
    kept: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    norms: list[tuple[str, int]] = []
    found: dict[str, int] = {}
    for raw in rows:
        e = judge(raw)
        if e["id"] in seen:                     # same title + same words: still kept, under its own id
            seen[e["id"]] += 1
            e["id"] = f"{e['id']}-{seen[e['id']]}"
        seen.setdefault(e["id"], 1)
        norm = DU.normalise(e["text"][:3000])
        if any(DU.similarity(norm, other) >= DU.SAME for other, _ in norms[-4000:]
               if abs(len(other) - len(norm)) < max(len(norm), 1) * 0.3):
            e["notes"].append("copy")
        norms.append((norm, len(kept)))
        for n in e["notes"]:
            found[n] = found.get(n, 0) + 1
        kept.append(e)
    meta = {**SOURCE, "commit": commit, "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "read": len(rows),
            "kept": len(kept), "notes": {NOTES[k]: v for k, v in sorted(found.items(), key=lambda x: -x[1])}}
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


def _use_how(e: dict[str, Any]) -> str:
    """workbench = opens as a brief; fill = filled in place, then copied or put in her chat; copy = copy only."""
    if any(n in SAFETY for n in e.get("notes") or ()):
        return "copy"
    return "fill" if len(e["text"]) > BRIEF_MAX else "workbench"


def _public(e: dict[str, Any], full: bool = False) -> dict[str, Any]:
    out = {"id": PREFIX + e["id"], "section": e["section"], "title": e["title"], "group": e["group"],
           "group_label": e.get("cat") or GROUP_LABEL.get(e["group"], ""), "makes": e.get("cat") or "",
           "kind": e.get("kind", "text"), "kind_label": KIND_LABEL.get(e.get("kind", "text"), "Text"),
           "blanks": e["blanks"], "starter": False, "world": True, "by": e.get("by") or "",
           "notes": [NOTES[n] for n in e.get("notes") or () if n in NOTES], "use": _use_how(e),
           "safety": any(n in SAFETY for n in e.get("notes") or ()), "chars": len(e["text"]),
           "name": e.get("name") or e.get("by") or "", "votes": e.get("votes") or 0, "created": e.get("created") or "",
           "family": FAMILY_OF.get(e["group"], "other"), "make_in": CAT_SECTION.get(e["group"], "chat"),
           "needs": e.get("needs") or ""}
    desc = e.get("desc") or ""
    out["desc"] = desc if full else desc[:220] + ("…" if len(desc) > 220 else "")
    # her browser never loads the author's host: the picture / video comes through Hoola's own copy, and a prompt
    # Hoola's checks flagged shows none
    if e.get("media") and not out["safety"]:
        out["media"] = {"type": media_type(e["media"]), "thumb": f"/api/prompting/world-media/{e['id']}?size=thumb",
                        "full": f"/api/prompting/world-media/{e['id']}?size=full"}
    else:
        out["media"] = None
    if not full and not out["media"]:
        ex = re.sub(r"\$\{([^}:]+)(?::[^}]*)?\}", r"[\1]", e["text"][:600])
        ex = re.sub(r"(?m)^\s*(#{1,6}\s*|[-*>]\s+|-{3,}\s*$)", "", ex)            # Markdown marks, not words
        out["excerpt"] = " ".join(re.sub(r"\*\*|__|`+", "", ex).split())[:360]
    if full:
        out["text"] = e["text"]
        out["tags"] = e.get("tags") or []
        out["outline"] = outline(e["text"]) if len(e["text"]) > 1200 else {"lead": "", "parts": []}
    return out


def search(q: str = "", group: str = "", page: int = 1, kind: str = "", sort: str = "loved",
           family: str = "", per: int = 0) -> dict[str, Any]:
    if not on():
        return {"on": False, "items": [], "total": 0, "groups": [], "kinds": [], "families": [], "source": SOURCE}
    d = _load()
    words = [w for w in (q or "").lower().split() if w][:8]
    hits = []
    for e in d["items"]:
        if group and e["group"] != group:
            continue
        if kind and e.get("kind", "text") != kind:
            continue
        if family and FAMILY_OF.get(e["group"], "other") != family:
            continue
        if words and not all(w in e["_hay"] for w in words):
            continue
        score = sum(3 if w in e["title"].lower() else 1 for w in words) * 1000 + min(e.get("votes") or 0, 999)
        if sort == "new":
            score = (sum(3 if w in e["title"].lower() else 1 for w in words), e.get("created") or "")
        elif sort == "media":           # loved, with the ones that show a picture or video first
            score = (1 if e.get("media") and not any(n in SAFETY for n in e.get("notes") or ()) else 0, score)
        hits.append((score, e))
    hits.sort(key=lambda x: x[0], reverse=True)
    per = max(1, min(int(per or PAGE), 60))
    try:                                         # NATIJA KHATA: kept counts, as on Hoola's own recipes
        from . import ledger as L
        rates = {k: v for k, v in L.recipe_rates().items() if k.startswith(PREFIX)}
    except Exception:       # noqa: BLE001
        rates = {}
    page = max(1, int(page or 1))
    items = []
    for _, e in hits[(page - 1) * per: page * per]:
        x = _public(e)
        if x["id"] in rates:
            x["kept"] = rates[x["id"]]
        items.append(x)
    cats: dict[str, list] = {}
    kinds: dict[str, int] = {}
    for e in d["items"]:
        c = cats.setdefault(e["group"], [e.get("cat") or GROUP_LABEL.get(e["group"], e["group"]), 0])
        c[1] += 1
        kinds[e.get("kind", "text")] = kinds.get(e.get("kind", "text"), 0) + 1
    return {"on": True, "items": items, "total": len(hits), "page": page, "pages": max(1, -(-len(hits) // per)),
            "all": len(d["items"]), "families": families(cats),
            "groups": [{"key": k, "label": v[0], "n": v[1]} for k, v in sorted(cats.items(), key=lambda x: -x[1][1])],
            "kinds": [{"key": k, "label": lab, "n": kinds[k]} for k, lab in KINDS if kinds.get(k)],
            "source": {**SOURCE, "kept": d["meta"].get("kept", 0), "read": d["meta"].get("read", 0)}}


def get(wid: str) -> dict[str, Any] | None:
    if not on():
        return None
    e = _load()["by_id"].get(wid.removeprefix(PREFIX))
    return _public(e, full=True) if e else None


def texts() -> list[dict[str, str]]:
    """For the duplicate check: {id, title, text}."""
    return [{"id": PREFIX + e["id"], "title": e["title"], "text": e["text"]} for e in _load()["items"]]


def _entry(wid: str) -> dict[str, Any]:
    e = _load()["by_id"].get(str(wid or "").removeprefix(PREFIX)) if on() else None
    if e is None:
        raise ValueError("No such prompt.")
    return e


def fill(wid: str, values: dict[str, str] | None = None) -> dict[str, Any]:
    """Any world prompt with her values, word for word otherwise: {text, filled, open, use, safety}.
    Empty blanks stay [Name]; the author's defaults are never used."""
    e = _entry(wid)
    got = P.fill(e["text"], values or {})
    return {**got, "use": _use_how(e), "safety": any(n in SAFETY for n in e.get("notes") or ())}


def use(wid: str, values: dict[str, str] | None = None) -> dict[str, Any]:
    """A world prompt with her values -> {"brief": ...}. Empty blanks stay [Name]; defaults are never used.
    Only prompts that fit a brief and carry no safety note open in the workbench; the rest use fill()."""
    from . import brief as B
    e = _entry(wid)
    how = _use_how(e)
    if how == "copy":
        raise ValueError("Hoola's checks flagged this prompt, so Hoola does not run it. You can copy it.")
    if how == "fill":
        raise ValueError("This prompt is longer than a brief holds. Fill it in place and copy it or put it in "
                         "your Hoola chat.")
    got = P.fill(e["text"], values or {})
    slots: dict[str, Any] = {}
    if e["section"] == "chat":
        slots["goal"] = {"value": f"Use the \"{e['title']}\" prompt", "source": "recipe"}
    raw = {"section": e["section"], "intent": got["text"], "slots": slots, "recipe_id": PREFIX + e["id"]}
    return {"brief": B.validate(raw)}


ADAPT_SYSTEM = (
    "You change a prompt the way the person asks and keep everything else exactly as it was: same structure, same "
    "headings, same level of detail, same language as the prompt. Do not add new instructions to an AI that the person "
    "did not ask for, never add rules about ignoring other instructions, never add personal data. Reply with ONLY the "
    "new prompt text, no notes before or after it.")


def _default_adapt(system: str, prompt: str, max_tokens: int) -> str:
    from ..net.ai import llm
    return llm(system, prompt, max_tokens, timeout=120)


ADAPT: list[Any] = [_default_adapt]           # tests replace ADAPT[0]
ADAPT_MAX = 12000


def adapt(wid: str, change: str, values: dict[str, str] | None = None) -> dict[str, Any]:
    """"Make it yours": the prompt rewritten the way she says (one model call), checked before she sees it.
    Never for a prompt Hoola's checks flagged; the new text must not carry unsafe words or ignore-your-rules lines,
    must keep a real share of the original, and stays her copy - the shelf is never changed."""
    e = _entry(wid)
    if _use_how(e) == "copy":
        raise ValueError("Hoola's checks flagged this prompt, so Hoola does not rewrite it. You can copy it.")
    change = " ".join(str(change or "").split())[:300]
    if len(change) < 3:
        raise ValueError("Say what to change, in a few words.")
    if _UNSAFE.search(change) or _IGNORE_RULES.search(change):
        raise ValueError("Hoola cannot make that change.")
    base = P.fill(e["text"], values or {})["text"]
    if len(base) > ADAPT_MAX:
        raise ValueError("This prompt is too long for Hoola to rewrite. Copy it and change it yourself.")
    got = str(ADAPT[0](ADAPT_SYSTEM, f"THE PROMPT:\n{base}\n\nTHE CHANGE SHE WANTS: {change}",
                       min(6000, len(base) // 3 + 600)) or "").strip()
    got = re.sub(r"^```[a-z]*\n|\n```$", "", got).strip()
    if not got:
        raise ValueError("Hoola could not rewrite it this time. Try again.")
    if len(got) > max(len(base) * 2 + 1500, 3000):
        raise ValueError("The rewrite came back much longer than the prompt, so Hoola did not use it. Try again.")
    if (_UNSAFE.search(got) and not _UNSAFE.search(base)) or (_IGNORE_RULES.search(got) and not _IGNORE_RULES.search(base)):
        raise ValueError("The rewrite failed Hoola's checks, so Hoola did not use it.")
    words = set(re.findall(r"[a-z]{4,}", base.lower()))
    kept = len(words & set(re.findall(r"[a-z]{4,}", got.lower()))) / max(len(words), 1)
    if words and kept < 0.2 and _english(base):
        raise ValueError("The rewrite lost too much of the prompt, so Hoola did not use it. Try a smaller change.")
    return {"text": got, "chars": len(got), "fits_brief": len(got) <= BRIEF_MAX, "section": e["section"],
            "make_in": CAT_SECTION.get(e["group"], "chat")}


if __name__ == "__main__":          # python -m app.prompting.world build <prompts.json|prompts.csv> [commit]
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        print(json.dumps(build(sys.argv[2], commit=sys.argv[3] if len(sys.argv) > 3 else ""), indent=1))
    else:
        print("usage: python -m app.prompting.world build <prompts.json|prompts.csv> [commit]")
