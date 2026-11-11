"""Game Desk jobs: her words -> a short design doc (her OK first) -> GDScript -> Hoola's guard -> a headless play run
(script errors) -> Web export -> Hoola plays it in Chromium (frames, screenshots, errors) -> fixed from the REAL errors
(max 2 rounds each) -> a private playable link + source zip on her desk + a live `game_desk` card.
Changes in her words make a new version from the current code.

Nothing here spends money (only model calls, counted as feature 'game' in AI kharcha) and nothing is published: the
play link is private (a random token) until SHE shares it."""
from __future__ import annotations

import io
import json
import logging
import os
import re
import secrets
import shutil
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from ..events import bus
from . import ai, engine, guard, playtest, template

log = logging.getLogger("santosh.gamedesk")

ORIENTATIONS = tuple(template.SIZES)
BUSY = ("designing", "queued", "writing", "building", "testing")
FIX_ROUNDS = 2
KEEP_PROJECTS = 40
KEEP_BUILDS = 3
STATS = {"designs": 0, "builds": 0, "ok": 0, "fixed": 0, "guard_refused": 0, "failed": 0}

_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gamedesk")
_RUNNING: dict[str, dict] = {}
_LOCK = threading.Lock()


class GameError(Exception):
    pass


class GameProject(Base):
    __tablename__ = "game_projects"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    number: Mapped[str] = mapped_column(String(16), default="")
    title: Mapped[str] = mapped_column(String(120), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    orientation: Mapped[str] = mapped_column(String(12), default="portrait")
    status: Mapped[str] = mapped_column(String(20), default="designing")  # designing|design_ready|queued|writing|building|testing|done|failed|cancelled
    stage: Mapped[str] = mapped_column(String(160), default="")
    pct: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    design: Mapped[str] = mapped_column(Text, default="")
    pending: Mapped[dict] = mapped_column(JSON, default=dict)            # what the next run does {mode, words, feedback}
    versions: Mapped[list] = mapped_column(JSON, default=list)
    token: Mapped[str] = mapped_column(String(48), default="", index=True)
    actor: Mapped[str] = mapped_column(String(64), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    """Self-heal (also created by db.init_db): once per database engine."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameProject.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ---------------------------------------------------------------- folders, links
def root() -> Path:
    p = Path(os.environ.get("GAME_DIR", "./data/games"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pdir(tenant: str, pid: str) -> Path:
    return root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / pid


def base_url() -> str:
    return (get_settings().public_base_url or "").rstrip("/")


def play_url(token: str) -> str:
    return f"{base_url()}/play/{token}/" if token else ""


def _vdir(r: GameProject, n: int) -> Path:
    return _pdir(r.tenant_id, r.id) / f"v{n}"


def _good(r: GameProject) -> list[dict]:
    """Versions that played fine and that she did not send back (v0.386 Studio: a rejected task's version is skipped,
    so the play link and the next change go back to the version before it)."""
    return [v for v in (r.versions or []) if v.get("ok") and not v.get("rejected")]


def shot_url(r: GameProject, n: int, name: str) -> str:
    return f"{play_url(r.token)}shots/v{n}/{name}" if r.token else ""


def play_file(token: str, path: str) -> tuple[Path | None, str]:
    """The file a play link asks for: the newest good build, or a screenshot. (path, media type) or (None, '')."""
    token = str(token or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,48}", token):
        return None, ""
    path = (path or "index.html").lstrip("/") or "index.html"
    if ".." in path or path.startswith("."):
        return None, ""
    ensure_table()
    with session() as s:
        r = s.scalars(select(GameProject).where(GameProject.token == token)).first()
        if r is not None:
            s.expunge(r)
    if r is None:                                       # v0.420 a role pack's demo (e.g. walk the generated world)
        from . import packs
        d = packs.demo_build(token)
        if d is None:
            return None, ""
        m = re.fullmatch(r"shots/(shot\d\.png|preview\.png)", path)
        if m:
            p = d.parent / "shots" / m.group(1) if m.group(1).startswith("shot") else d.parent / m.group(1)
            return (p, "image/png") if p.is_file() else (None, "")
        if not re.fullmatch(r"index(\.[a-z0-9.]+)?|index\.(html|js|wasm|pck|png|icon\.png|apple-touch-icon\.png|"
                            r"audio\.worklet\.js|audio\.position\.worklet\.js)", path):
            return None, ""
        p = d / path
        media = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".wasm": "application/wasm",
                 ".pck": "application/octet-stream", ".png": "image/png"}.get(p.suffix, "application/octet-stream")
        return (p, media) if p.is_file() else (None, "")
    m = re.fullmatch(r"shots/v(\d{1,3})/(shot\d\.png)", path)
    if m:
        p = _vdir(r, int(m.group(1))) / "shots" / m.group(2)
        return (p, "image/png") if p.is_file() else (None, "")
    good = _good(r)
    if not good or not re.fullmatch(r"index(\.[a-z0-9.]+)?|index\.(html|js|wasm|pck|png|icon\.png|apple-touch-icon\.png|"
                                     r"audio\.worklet\.js|audio\.position\.worklet\.js)", path):
        return None, ""
    p = _vdir(r, good[-1]["n"]) / "build" / path
    media = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".wasm": "application/wasm",
             ".pck": "application/octet-stream", ".png": "image/png"}.get(p.suffix, "application/octet-stream")
    return (p, media) if p.is_file() else (None, "")


# ---------------------------------------------------------------- views
def view(r: GameProject, full: bool = False) -> dict[str, Any]:
    vers = r.versions or []
    last = vers[-1] if vers else {}
    good = _good(r)
    live = good[-1] if good else {}
    url = play_url(r.token) if good else ""
    say = {"designing": "Design doc likh raha hoon", "design_ready": "Design taiyaar hai: padhiye aur 'theek hai' boliye",
           "queued": "Line mein", "writing": "Code likh raha hoon", "building": "Godot mein bana raha hoon",
           "testing": "Khud khel kar jaanch raha hoon", "done": "Game taiyaar hai: link kholkar khelo",
           "failed": "Nahi ban paya", "cancelled": "Rok diya"}.get(r.status, r.status)
    d = {"id": r.id, "number": r.number, "title": r.title or r.brief[:60], "brief": r.brief if full else r.brief[:400], "status": r.status,
         "stage": r.stage, "pct": r.pct, "error": r.error, "orientation": r.orientation, "say": say,
         "design": r.design if (full or r.status == "design_ready") else "", "url": url, "play_url": url,
         "version": live.get("n", 0), "versions": len(vers), "notes": live.get("notes", ""),
         "shots": [shot_url(r, live["n"], s) for s in live.get("shots", [])] if live else [],
         "numbers": live.get("numbers", {}), "warnings": (last.get("warnings") or [])[:6],
         "checks": last.get("checks", []), "created_at": r.created_at.isoformat() if r.created_at else None,
         "conversation_id": r.conversation_id or ""}   # v0.785 Hoola Game Dev opens the game's OWN thread on any browser
    if full:
        d["history"] = [{"n": v.get("n"), "words": v.get("words", ""), "ok": v.get("ok"), "notes": v.get("notes", ""),
                         "at": v.get("at"), "fixed": v.get("fixed", 0), "errors": (v.get("errors") or [])[:4]} for v in vers]
        d["files"] = sorted(live.get("files", [])) if live else []
    return d


def _publish(r: GameProject) -> None:
    if r.conversation_id:
        try:
            bus.publish(r.conversation_id, "game_desk", view(r))
        except Exception as e:
            log.info("game publish: %s", e)


def _save(r: GameProject, **fields) -> GameProject:
    with session() as s:
        row = s.get(GameProject, r.id)
        for k, v in fields.items():
            setattr(row, k, v)
            setattr(r, k, v)
        row.updated_at = now()
    return r


def _stage(r: GameProject, status: str, stage: str, pct: int) -> None:
    _save(r, status=status, stage=stage, pct=pct)
    _publish(r)


# ---------------------------------------------------------------- starting jobs
CLONE = re.compile(r"\b(clone|copy|same as|exactly like|replica|jaisa hi|jaisi hi|hubahu)\b", re.I)
FAMOUS = re.compile(r"\b(subway surfers?|candy crush|pubg|bgmi|free ?fire|minecraft|fortnite|pac-?man|super mario|mario|"
                    r"tetris|flappy bird|angry birds|temple run|among us|gta|clash of clans|pok[eé]mon|sonic|call of duty|"
                    r"ludo king|roblox|fruit ninja|plants vs\.? zombies|valorant|counter[- ]strike|genshin)\b", re.I)
MONEY = re.compile(r"\b(real money|real-money|betting|bet karo|satta|casino|gambl\w*|cash prize|paise jeeto|rummy|teen ?patti|"
                   r"poker|fantasy (cricket|team)|matka|lottery)\b", re.I)
# v0.447: the Promotion and Regulation of Online Gaming Act 2025 + Rules 2026 (in force 1 May 2026) turn on a STAKE plus an
# expectation of monetary return, and Rule 9 weighs whether a reward is TRANSFERABLE, REDEEMABLE or MONETISABLE OUTSIDE the
# game. Offering such a game is cognisable and non-bailable for whoever publishes it, so the words that describe cashing an
# in-game reward out are refused even when "betting" never appears: an in-game value word near a money-out word.
_EARNED = (r"coins?|points?|gems?|tokens?|credits?|rewards?|prizes?|winnings?|chips?|stars?|diamonds?|cash|balance|wallet|"
           r"skins?|items?|cards?|score|sikke|ank")
_CASHOUT = (r"withdraw\w*|cash ?out|cashout|payout|pay ?out|redeem\w*|encash\w*|convert\w* (?:to|into|in)|transfer\w*|"
            r"exchang\w*|sell|trade|bank account|upi|paytm|phonepe|gpay|google pay|bhim|neft|imps|rtgs|real cash|"
            r"asli paise|paise nikal\w*|nikal\w* (?:sakte|sakta|sakti)|paise mein|rupees?|rupaye|₹")
MONEY_OUT = re.compile(rf"\b(?:{_EARNED})\b[^.;!?\n]{{0,60}}\b(?:{_CASHOUT})\b|"
                       rf"\b(?:{_CASHOUT})\b[^.;!?\n]{{0,60}}\b(?:{_EARNED})\b", re.I)
# a few shapes that need no pairing at all
MONEY_OUT_FLAT = re.compile(r"\b(play to earn|play-to-earn|p2e|earn real (?:money|cash)|paisa kamao|paise kamao|"
                            r"nft|crypto|cryptocurrenc\w*|token sale|airdrop|entry fee|buy-?in|stake\w*|wager\w*)\b", re.I)
MONEY_OUT_SAY = ("Aisa game Hoola nahi bana sakta: us mein jeeta hua coin / point / item game ke BAAHAR paise mein badla ja "
                 "sakta hai (withdraw, redeem, UPI, trade). India ke Online Gaming Act 2025 + Rules 2026 mein yeh 'online "
                 "money game' hai - jo use publish karta hai uske liye yeh non-bailable jurm hai (3 saal tak, ₹1 crore tak). "
                 "Coins / points sirf game ke andar chalein (naye level, skins, power-ups) - aisa game khushi se bana dunga.")
WEAPON_SIM = re.compile(r"\b(weapon targeting|missile|target acquisition|bomb(ing)? run|military (strike|targeting)|"
                        r"sniper training sim|kill chain)\b", re.I)


def problem(brief: str) -> str:
    """Asks the Game Desk never builds, in plain words with the honest alternative."""
    b = brief or ""
    if MONEY.search(b):
        return ("Real-money, betting ya jua wale games Hoola nahi banata (India mein online money games band hain). "
                "Points / coins wala normal game bana sakta hoon.")
    if MONEY_OUT.search(b) or MONEY_OUT_FLAT.search(b):
        return MONEY_OUT_SAY
    if WEAPON_SIM.search(b):
        return "Hathiyar nishana / military targeting simulator Hoola nahi banata. Flying, driving ya safety training sim bana sakta hoon."
    m = FAMOUS.search(b)
    if m and CLONE.search(b):
        return (f"'{m.group(0)}' ki copy nahi banaunga (naam, characters, levels unke hain). Usi type ka ek naya, apna "
                "original game bana deta hoon: bas 'original banao' boliye.")
    return ""


def _limits(tenant: str) -> None:
    with session() as s:
        rows = s.scalars(select(GameProject).where(GameProject.tenant_id == tenant)).all()
    if any(r.status in BUSY for r in rows):
        raise GameError("Ek game pehle se ban raha hai; khatam hone dijiye.")
    day = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    runs = sum(1 for r in rows for v in (r.versions or []) if (v.get("at") or "") >= day)
    designs = sum(1 for r in rows if r.created_at and (r.created_at if r.created_at.tzinfo else
                                                        r.created_at.replace(tzinfo=timezone.utc)).isoformat() >= day)
    if runs >= int(os.environ.get("GAME_DAY_BUILDS", "15")) or designs >= int(os.environ.get("GAME_DAY_NEW", "10")):
        raise GameError("Aaj ki game banane ki seema poori ho gayi; kal phir.")


def _number(tenant: str) -> str:
    with session() as s:
        n = len(s.scalars(select(GameProject.id).where(GameProject.tenant_id == tenant)).all())
    return f"G-{n + 1:04d}"


def start(tenant: str, conv: str, brief: str, orientation: str = "portrait", actor: str = "owner") -> dict[str, Any]:
    ensure_table()
    brief = re.sub(r"\s+", " ", str(brief or "")).strip()[:2000]
    if len(brief) < 8:
        raise GameError("Kaisa game? Do-teen line mein bataiye: kya karna hai, kaise jeetna hai, kis ke liye.")
    why = problem(brief)
    if why:
        raise GameError(why)
    _limits(tenant)
    r = GameProject(tenant_id=tenant, conversation_id=conv or "", number=_number(tenant), brief=brief,
                    orientation=orientation if orientation in ORIENTATIONS else "portrait", status="designing",
                    stage="design doc", pct=5, actor=actor or "owner", pending={"mode": "design"})
    with session() as s:
        s.add(r)
    _prune(tenant)
    _publish(r)
    _submit(r.id)
    return view(r)


def approve(tenant: str, pid: str, feedback: str = "") -> dict[str, Any]:
    """Her OK on the design (build starts) - or her changes to it (a new design doc, still waiting for her OK)."""
    r = _get(tenant, pid)
    if r.status != "design_ready":
        raise GameError("Is game ka design abhi OK karne layak nahi (pehle design doc banne dijiye).")
    feedback = re.sub(r"\s+", " ", str(feedback or "")).strip()[:1500]
    if feedback:
        why = problem(feedback)
        if why:
            raise GameError(why)
        _save(r, status="designing", stage="design badal raha hoon", pct=5, pending={"mode": "design", "feedback": feedback})
    else:
        _limits_build(tenant)
        _save(r, status="queued", stage="line mein", pct=10, pending={"mode": "build"}, error="")
    _publish(r)
    _submit(r.id)
    return view(r)


def _limits_build(tenant: str) -> None:
    with session() as s:
        rows = s.scalars(select(GameProject).where(GameProject.tenant_id == tenant)).all()
    if any(r.status in ("queued", "writing", "building", "testing") for r in rows):
        raise GameError("Ek game pehle se ban raha hai; khatam hone dijiye.")
    day = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    if sum(1 for r in rows for v in (r.versions or []) if (v.get("at") or "") >= day) >= int(os.environ.get("GAME_DAY_BUILDS", "15")):
        raise GameError("Aaj ki game banane ki seema poori ho gayi; kal phir.")


def change(tenant: str, pid: str, words: str, task: str = "") -> dict[str, Any]:
    r = _get(tenant, pid)
    if r.status in BUSY:
        raise GameError("Abhi bana raha hoon; khatam hote hi badlav bataiye.")
    if not bool(_good(r)):
        raise GameError("Abhi koi chalne wala version nahi; pehle design OK karke banwaiye.")
    words = re.sub(r"\s+", " ", str(words or "")).strip()[:1500]
    if not words:
        raise GameError("Kya badalna hai? Ek line mein bataiye.")
    why = problem(words)
    if why:
        raise GameError(why)
    _limits_build(tenant)
    _save(r, status="queued", stage="line mein", pct=10, pending={"mode": "change", "words": words, "task": task or ""}, error="")
    _publish(r)
    _submit(r.id)
    return view(r)


def restore(tenant: str, pid: str, n: int, task: str = "") -> dict[str, Any]:
    """v0.386: an older version's code back as a NEW version (no model call; the same checks + playtest run again)."""
    r = _get(tenant, pid)
    if r.status in BUSY:
        raise GameError("Abhi bana raha hoon; khatam hone dijiye.")
    old = next((v for v in (r.versions or []) if v.get("n") == int(n or 0) and v.get("ok")), None)
    if old is None or not (_vdir(r, old["n"]) / "proj" / "main.gd").is_file():
        raise GameError("Woh version nahi mila (sirf chalne wale version wapas aa sakte hain).")
    _limits_build(tenant)
    _save(r, status="queued", stage="line mein", pct=10, error="",
          pending={"mode": "restore", "n": old["n"], "words": f"version {old['n']} wapas", "task": task or ""})
    _publish(r)
    _submit(r.id)
    return view(r)


def data_build(tenant: str, pid: str, bible_version: int, task: str = "", words: str = "") -> dict[str, Any]:
    """v0.395 Game Bible applied to the live game: the SAME code + the new hoola_bible.gd, no model call, full checks."""
    r = _get(tenant, pid)
    if r.status in BUSY:
        raise GameError("Abhi bana raha hoon; khatam hone dijiye.")
    if not _good(r):
        raise GameError("Pehle game ka pehla version banne dijiye.")
    _limits_build(tenant)
    _save(r, status="queued", stage="line mein", pct=10, error="",
          pending={"mode": "data", "words": words or f"Bible v{int(bible_version)} game mein", "task": task or ""})
    _publish(r)
    _submit(r.id)
    return view(r)


def _bible(r: GameProject) -> tuple[str, int] | None:
    try:
        from . import bible
        return bible.for_game(r.tenant_id, r.id)
    except Exception:                                   # noqa: BLE001 - a game without a Studio Bible builds as before
        log.exception("bible for game %s", r.id)
        return None


def _assets(r: GameProject) -> tuple[str, dict[str, Path]] | None:
    try:
        from . import assets
        return assets.for_game(r.tenant_id, r.id)
    except Exception:                                   # noqa: BLE001 - a game without assets builds as before
        log.exception("assets for game %s", r.id)
        return None


def _scenes(r: GameProject) -> dict[str, str]:
    """v0.456: the approved scenes of this game's Studio project. Hoola generated them from a checked spec and the
    engine already loaded them; a game without any builds exactly as before."""
    try:
        from . import scene
        return scene.for_game(r.tenant_id, r.id)
    except Exception:                                   # noqa: BLE001 - a scene problem must never stop a build
        log.exception("scenes for game %s", r.id)
        return {}


def _packs(r: GameProject) -> dict[str, tuple[str, dict[str, Path]]]:
    try:
        from . import packs
        return packs.for_game(r.tenant_id, r.id)
    except Exception:                                   # noqa: BLE001 - a game without packs builds as before
        log.exception("packs for game %s", r.id)
        return {}


def _own_packs(files: dict[str, str], pk: dict[str, tuple[str, dict[str, Path]]]) -> None:
    """v0.420: the role packs' files are Hoola's: whatever the model wrote under those names is dropped, a pack whose
    data is gone leaves no stale file behind, and the current ones go in."""
    from . import packs
    for name in packs.files():
        files.pop(name, None)
    for name, (txt, _x) in pk.items():
        files[name] = txt


def _copy_assets(proj: Path, ast: tuple[str, dict[str, Path]] | None) -> None:
    for rel, src in ((ast or ("", {}))[1]).items():
        dst = proj / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def reject_version(tenant: str, pid: str, n: int) -> None:
    """v0.386: she sent a task back - that version stops being the live one (kept in history, marked)."""
    with session() as s:
        row = s.get(GameProject, pid)
        if row is None or row.tenant_id != tenant:
            raise GameError("Yeh game nahi mila.")
        vers = [dict(v) for v in (row.versions or [])]
        for v in vers:
            if v.get("n") == int(n or 0):
                v["rejected"] = True
        row.versions = vers
        row.updated_at = now()


def cancel(tenant: str, pid: str) -> dict[str, Any]:
    r = _get(tenant, pid)
    h = _RUNNING.get(pid)
    if h:
        engine.kill(h)
    if r.status in BUSY:
        task = (r.pending or {}).get("task", "")
        _save(r, status="cancelled", stage="rok diya", error="")
        _publish(r)
        _studio_hook(r, task, None, "cancelled")
    return view(r)


def delete(tenant: str, pid: str) -> None:
    r = _get(tenant, pid)
    if r.status in BUSY:
        cancel(tenant, pid)
    shutil.rmtree(_pdir(tenant, pid), ignore_errors=True)
    with session() as s:
        row = s.get(GameProject, pid)
        if row is not None:
            s.delete(row)


def _get(tenant: str, pid: str) -> GameProject:
    ensure_table()
    with session() as s:
        r = s.get(GameProject, pid)
        if r is None:
            r = s.scalars(select(GameProject).where(GameProject.tenant_id == tenant,
                                                    GameProject.number == str(pid).upper())).first()
        if r is None or r.tenant_id != tenant:
            raise GameError("Yeh game nahi mila.")
        s.expunge(r)
        return r


def get(tenant: str, pid: str) -> dict[str, Any]:
    return view(_get(tenant, pid), full=True)


def projects(tenant: str, limit: int = 30) -> list[dict[str, Any]]:
    ensure_table()
    _heal(tenant)
    with session() as s:
        rows = s.scalars(select(GameProject).where(GameProject.tenant_id == tenant)
                         .order_by(GameProject.created_at.desc()).limit(limit)).all()
    return [view(r) for r in rows]


def source_zip(tenant: str, pid: str) -> tuple[bytes, str]:
    """Her game's whole Godot project (opens in the Godot editor), newest good version. Never a key: there are none."""
    r = _get(tenant, pid)
    good = _good(r)
    if not good:
        raise GameError("Abhi koi chalne wala version nahi.")
    proj = _vdir(r, good[-1]["n"]) / "proj"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(proj.iterdir()):
            if p.is_file() and p.suffix in (".gd", ".godot", ".tscn", ".cfg"):
                z.write(p, f"{r.number}/{p.name}")
        for p in sorted((proj / "assets").glob("*")) if (proj / "assets").is_dir() else []:   # v0.416 approved assets
            if p.is_file() and p.suffix in (".png", ".wav", ".ogg", ".glb"):
                z.write(p, f"{r.number}/assets/{p.name}")
        z.writestr(f"{r.number}/DESIGN.md", r.design or "")
        z.writestr(f"{r.number}/README.txt", "Made by Hoola Game Desk with Godot 4 (godotengine.org, MIT).\n"
                   "Open project.godot in the Godot editor 4.7+. Export: Project > Export > Web.\n")
    return buf.getvalue(), f"{r.number}-{re.sub(r'[^A-Za-z0-9]+', '-', r.title or 'game').strip('-')[:40]}.zip"


def _heal(tenant: str) -> None:
    """A job that was running when the server restarted is said plainly, not left spinning."""
    with session() as s:
        for r in s.scalars(select(GameProject).where(GameProject.tenant_id == tenant)).all():
            if r.status in BUSY and r.id not in _RUNNING:
                upd = r.updated_at if r.updated_at.tzinfo else r.updated_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - upd > timedelta(minutes=20):
                    r.status, r.error = "failed", "server restart ho gaya tha; 'dobara' boliye"


def _prune(tenant: str) -> None:
    with session() as s:
        rows = s.scalars(select(GameProject).where(GameProject.tenant_id == tenant)
                         .order_by(GameProject.created_at.desc())).all()
        for r in rows[KEEP_PROJECTS:]:
            shutil.rmtree(_pdir(tenant, r.id), ignore_errors=True)
            s.delete(r)


def _submit(pid: str) -> None:
    if os.environ.get("GAME_WORKER", "true").lower() in ("0", "false", "off"):
        return                                   # tests call run_job themselves
    _POOL.submit(_safe_run, pid)


def _safe_run(pid: str) -> None:
    try:
        run_job(pid)
    except Exception as e:  # never kill the pool thread
        log.exception("game job %s: %s", pid, e)


# ---------------------------------------------------------------- the job
def run_job(pid: str) -> None:
    from .. import usage
    with session() as s:
        r = s.get(GameProject, pid)
        if r is None or r.status == "cancelled":
            return
        s.expunge(r)
    holder: dict = {}
    with _LOCK:
        _RUNNING[pid] = holder
    try:
        with usage.scope(r.tenant_id, "game"):
            mode = (r.pending or {}).get("mode", "design")
            if mode == "design":
                _design(r)
            else:
                _build(r, holder)
    except (ai.AiError, engine.EngineError, GameError) as e:
        STATS["failed"] += 1
        _fail(r, str(e)[:400])
    except Exception as e:
        STATS["failed"] += 1
        log.exception("game job %s", pid)
        _fail(r, f"andar ki gadbad: {type(e).__name__}")
    finally:
        with _LOCK:
            _RUNNING.pop(pid, None)


def _fail(r: GameProject, err: str) -> None:
    task = (r.pending or {}).get("task", "")
    # a game that already plays stays 'done' (its live version still works); only a first build is 'failed'
    _save(r, status="done" if _good(r) else "failed", stage="", error=err, pending={})
    _publish(r)
    _studio_hook(r, task, None, err)


def _studio_hook(r: GameProject, task: str, ver: dict | None, err: str = "") -> None:
    """v0.386 Studio Project: a build that was a board task tells the board (review / blocked / back to do)."""
    if not task:
        return
    try:
        from . import studio
        studio.after_build(r.tenant_id, task, ver, err)
    except Exception:                                   # noqa: BLE001 - the game itself is already saved
        log.exception("studio hook %s", task)


def _design(r: GameProject) -> None:
    STATS["designs"] += 1
    fb = (r.pending or {}).get("feedback", "")
    doc = ai.design(r.brief, r.orientation, feedback=fb, old=r.design if fb else "")
    m = re.match(r"#\s*(.+)", doc)
    title = (m.group(1).strip() if m else r.brief[:60])[:120]
    _save(r, design=doc, title=title, status="design_ready", stage="aapki haan ka intezaar", pct=20, pending={}, error="")
    _publish(r)


def _cancelled(r: GameProject, holder: dict) -> bool:
    if holder.get("cancelled"):
        return True
    with session() as s:
        row = s.get(GameProject, r.id)
        return row is None or row.status == "cancelled"


def _current_files(r: GameProject) -> dict[str, str]:
    good = _good(r)
    if not good:
        return {}
    proj = _vdir(r, good[-1]["n"]) / "proj"
    return {p.name: p.read_text(encoding="utf-8") for p in proj.glob("*.gd") if p.name != "hoola_probe.gd"}


def _write(proj: Path, r: GameProject, scripts: dict[str, str], scenes: dict[str, str] | None = None) -> None:
    shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    for name, txt in template.files(r.title or "Hoola game", r.orientation, scripts, scenes).items():
        (proj / name).write_text(txt, encoding="utf-8")


def _build(r: GameProject, holder: dict) -> None:
    STATS["builds"] += 1
    size = template.SIZES.get(r.orientation, template.SIZES["portrait"])
    mode = (r.pending or {}).get("mode", "build")
    words = (r.pending or {}).get("words", "")
    n = (max([v.get("n", 0) for v in (r.versions or [])] or [0])) + 1
    vdir = _vdir(r, n)
    shutil.rmtree(vdir, ignore_errors=True)
    vdir.mkdir(parents=True)
    _stage(r, "writing", "code likh raha hoon" if mode == "build" else "badlav kar raha hoon", 30)
    task = (r.pending or {}).get("task", "")
    if mode == "restore":
        src = _vdir(r, int((r.pending or {}).get("n") or 0)) / "proj"
        files = {p.name: p.read_text(encoding="utf-8") for p in src.glob("*.gd") if p.name != "hoola_probe.gd"}
        files["__notes__"] = f"Version {(r.pending or {}).get('n')} ka code wapas (koi naya code nahi likha)."
    elif mode == "data":
        files = _current_files(r)
        files["__notes__"] = "Game Bible ke naye naam / numbers (koi naya code nahi likha)."
    elif mode == "change":
        files = ai.change(r.design, _current_files(r), words, r.orientation, size)
    else:
        files = ai.code(r.design, r.orientation, size)
    notes = files.pop("__notes__", "")
    bib = _bible(r)                                     # v0.395: the Bible is always Hoola's own file, never the model's
    if bib:
        files["hoola_bible.gd"] = bib[0]
    ast = _assets(r)                                    # v0.416: approved assets + HoolaAssets, also Hoola's own
    files.pop("hoola_assets.gd", None)
    if ast:
        files["hoola_assets.gd"] = ast[0]
    pk = _packs(r)                                      # v0.420 role packs (HoolaWorld, HoolaPhysics...): Hoola's own
    _own_packs(files, pk)
    scn = _scenes(r)                                    # v0.456 approved scenes (checked spec -> Hoola generated them)
    checks: list[dict[str, Any]] = []
    fixed = 0
    smoke: dict[str, Any] = {}
    exp: dict[str, Any] = {}
    play: dict[str, Any] = {}
    for rnd in range(FIX_ROUNDS * 2 + 1):
        if _cancelled(r, holder):
            return
        bad = guard.problems(files, scn)
        if bad:
            STATS["guard_refused"] += 1
            checks.append({"step": "guard", "ok": False, "errors": bad[:6]})
        else:
            _stage(r, "building", "Godot mein chala kar dekh raha hoon", 45 + rnd * 3)
            _write(vdir / "proj", r, files, scn)
            _copy_assets(vdir / "proj", ast)
            for _f, (_t, extra) in pk.items():
                _copy_assets(vdir / "proj", ("", extra))
            smoke = engine.smoke(vdir, holder=holder)
            checks.append({"step": "play_headless", "ok": smoke["ok"], "errors": smoke["errors"][:6]})
            bad = smoke["errors"]
            if not bad:
                _stage(r, "building", "Web ke liye bana raha hoon", 60)
                exp = engine.export_web(vdir, holder=holder)
                checks.append({"step": "export_web", "ok": exp["ok"], "errors": exp["errors"][:4]})
                bad = exp["errors"]
                if not bad:
                    if _cancelled(r, holder):
                        return
                    _stage(r, "testing", "khud khel kar jaanch raha hoon", 80)
                    play = playtest.run(_play_build(vdir, holder), vdir / "shots", r.orientation)
                    checks.append({"step": "playtest", "ok": play["ok"], "errors": play["errors"][:6]})
                    bad = play["errors"]
        if not bad or fixed >= FIX_ROUNDS * 2:
            break
        fixed += 1
        _stage(r, "writing", f"galti theek kar raha hoon ({fixed})", 35 + rnd * 5)
        new = ai.fix(r.design, files, bad, r.orientation, size)
        notes = new.pop("__notes__", "") or notes
        if new.get("main.gd"):
            files = new
            if bib:
                files["hoola_bible.gd"] = bib[0]
            files.pop("hoola_assets.gd", None)
            if ast:
                files["hoola_assets.gd"] = ast[0]
            _own_packs(files, pk)
    shutil.rmtree(vdir / "build_debug", ignore_errors=True)    # v0.416 the played debug build is not kept
    ok = bool(checks) and all(c["ok"] for c in checks[-3:]) and checks[-1]["step"] == "playtest" and checks[-1]["ok"]
    if fixed and ok:
        STATS["fixed"] += 1
    errors = [] if ok else (checks[-1]["errors"] if checks else ["kuch nahi bana"])
    ver = {"n": n, "at": now().isoformat(), "words": words, "ok": ok, "task": task, "base": (_good(r)[-1]["n"] if _good(r) else 0),
           "src": _src_hash(vdir / "proj"), "bible": bib[1] if bib else 0,
           # v0.455 PROVENANCE: the model(s) that wrote THIS build's code, so the store disclosure is a fact she can
           # read off rather than a guess. Empty when nothing was asked (a data-only rebuild writes no new code).
           "models": ai.used(),
           "assets": sorted(((ast or ("", {}))[1]).keys()), "packs": sorted(pk), "scenes": sorted(scn), "notes": notes, "fixed": fixed, "checks": checks[-4:],
           "errors": errors[:6], "files": sorted(files), "shots": play.get("shots", []) if ok else [],
           "warnings": play.get("warnings", []),
           "numbers": {"fps_server": play.get("fps"), "load_s": play.get("load_s"),
                       "download_mb": round((exp.get("download_bytes") or 0) / 1048576, 1) or None,
                       "build_s": exp.get("seconds")} if ok else {}}
    token = r.token or secrets.token_urlsafe(18)
    if ok and bib:
        try:
            from . import bible as _B
            _B.mark_applied(r.tenant_id, r.id, bib[1])
        except Exception:                               # noqa: BLE001
            log.exception("bible applied mark")
    if ok:
        STATS["ok"] += 1
        _save(r, versions=(r.versions or []) + [ver], token=token, status="done", stage="", pct=100, pending={}, error="")
        _trim_builds(r)
    else:
        had_good = bool(_good(r))
        _save(r, versions=(r.versions or []) + [ver], token=token, status="done" if had_good else "failed", stage="",
              pct=100, pending={}, error=("Naya badlav nahi chala, purana version abhi bhi khelne layak hai: " if had_good
                                          else "Game nahi chal paya: ") + "; ".join(errors[:2])[:300])
    _publish(r)
    _studio_hook(r, task, ver, "" if ok else "; ".join(errors[:3])[:400])


def _play_build(vdir: Path, holder: dict) -> Path:
    """v0.416: Hoola plays a DEBUG web build when the debug template is there - a release web build prints no script
    errors, so a crash that only happens on a key / tap passed the playtest and went live (found by the QA farm on a
    real build). The play link still serves the release build. Without the debug template: the release build, as before."""
    try:
        if engine.debug_template():
            ex = engine.export_web(vdir, holder=holder, debug=True)
            if ex.get("ok"):
                return vdir / "build_debug"
    except engine.EngineError:
        pass
    return vdir / "build"


def _src_hash(proj: Path) -> str:
    """The code's fingerprint (every .gd / project file): the nightly build proves the same code still builds the same."""
    import hashlib
    h = hashlib.sha256()
    for p in sorted(proj.glob("*")):
        if p.is_file() and p.suffix in (".gd", ".godot", ".tscn", ".cfg"):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _trim_builds(r: GameProject) -> None:
    """Keep the Web builds of the newest few good versions (each ~40 MB); older versions keep code + screenshots.
    The debug build Hoola played (v0.416) is never kept."""
    for v in r.versions or []:
        shutil.rmtree(_vdir(r, v.get("n", 0)) / "build_debug", ignore_errors=True)
    good = [v["n"] for v in _good(r)]
    for n in good[:-KEEP_BUILDS]:
        shutil.rmtree(_vdir(r, n) / "build", ignore_errors=True)


def health() -> dict[str, Any]:
    h = engine.health()
    h["ready"] = bool(h["installed"] and h["web_templates"])
    return h


def check() -> dict[str, Any]:
    """`python -m app.gamedesk check`: Godot + Web templates installed, the box has no network, a sample game builds,
    exports and plays (no model call, nothing saved)."""
    import tempfile
    out: dict[str, Any] = {"health": health()}
    if not out["health"]["ready"]:
        out["ok"] = False
        return out
    sample = ("extends Node\n\nvar box: ColorRect\n\nfunc _ready() -> void:\n\tbox = ColorRect.new()\n"
              "\tbox.color = Color(1, 0.6, 0.1)\n\tbox.size = Vector2(120, 120)\n\tbox.mouse_filter = Control.MOUSE_FILTER_IGNORE\n"
              "\tadd_child(box)\n\nfunc _process(delta: float) -> void:\n\tbox.position.x = fmod(box.position.x + 200.0 * delta, 600.0)\n")
    with tempfile.TemporaryDirectory(prefix="hoola-game-check-") as d:
        job = Path(d)
        (job / "proj").mkdir()
        for name, txt in template.files("Hoola check", "portrait", {"main.gd": sample}).items():
            (job / "proj" / name).write_text(txt, encoding="utf-8")
        out["smoke"] = engine.smoke(job)
        out["export"] = engine.export_web(job) if out["smoke"]["ok"] else {"ok": False}
        out["playtest"] = playtest.run(job / "build", job / "shots") if out["export"].get("ok") else {"ok": False}
    out["ok"] = bool(out["smoke"]["ok"] and out["export"].get("ok") and out["playtest"].get("ok"))
    return out


