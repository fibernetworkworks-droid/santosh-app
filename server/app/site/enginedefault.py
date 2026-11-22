"""D10 of docs/WEB_DESIGN_ENGINE_PLAN.md: which engine NEW websites are built on - decided by the owner's tap only.

Until she says go, new websites are built on the old engine (HTML) unless the server's `studio_react_sites` switch is
on. On the owner page (/console/proofcard) she sees the proof card (old engine vs new on the same briefs, the
critic, the speed lab, the Arena duels and her own picks) and the recommendation code makes from them; her tap "Make
the new engine the default" is bound to the fingerprint of exactly that evidence (if a pick or a pair changed since
she looked, it is refused and she looks again). Her tap "Back to the old engine" undoes it at once.

What it changes: only which engine a NEW build uses (the Studio's "Build the real website"). Websites already built
stay on the engine they were built on; an HTML website moves only by her "Upgrade this site" tap (D9). Each decision
is kept with who, when and the evidence she saw."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"mtime": None, "data": {}}
FORCE: dict[str, str] = {"engine": ""}         # the proof card's own process forces each build's engine ("" = no force)


class DefaultError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def _file() -> Path:
    from ..config import get_settings
    d = Path(getattr(get_settings(), "data_dir", "") or "data")
    d.mkdir(parents=True, exist_ok=True)
    return d / "engine-default.json"


def state() -> dict[str, Any]:
    """The current decision (read from disk, cached by its modification time so every build reads it cheaply)."""
    f = _file()
    try:
        mt = f.stat().st_mtime_ns
    except OSError:
        return {"engine": "old", "history": []}
    if _CACHE["mtime"] != mt:
        try:
            _CACHE["data"] = json.loads(f.read_text("utf-8")) or {}
        except (OSError, ValueError):
            _CACHE["data"] = {}
        _CACHE["mtime"] = mt
    d = dict(_CACHE["data"])
    d.setdefault("engine", "old")
    d.setdefault("history", [])
    return d


def new_default() -> bool:
    """True when she made the new engine the default for new websites."""
    return state().get("engine") == "new"


def evidence(run: str = "") -> dict[str, Any]:
    """What she decides on: the newest (or named) live proof card's summary, its duels and the recommendation."""
    from ..quality import proofcard as PC
    card = PC.load(run)
    if not card:
        return {"card": None, "hash": "", "recommendation": PC.recommend({})}
    keep = ("run", "version", "set", "briefs", "planned", "old", "new", "critic", "her", "design_gain_median",
            "recommendation", "duels", "spent_inr", "running")
    return {"card": {k: card.get(k) for k in keep}, "hash": card["hash"], "recommendation": card.get("recommendation")}


def decide(go: bool, h: str = "", run: str = "", by: str = "owner") -> dict[str, Any]:
    """HER TAP ONLY (the owner route): go = the new engine becomes the default for new websites, bound to the evidence
    fingerprint she saw; not go = back to the old engine (no fingerprint needed: going back is always allowed)."""
    with _LOCK:
        cur = state()
        hist = list(cur.get("history") or [])[-40:]
        if go:
            ev = evidence(run)
            if not ev["card"]:
                raise DefaultError("There is no proof card yet: run it first (VPS ops > proof_card_try), then decide.", 409)
            if ev["card"].get("running"):
                raise DefaultError("The proof card is still running; decide when it has finished.", 409)
            if not h or h != ev["hash"]:
                raise DefaultError("The proof changed since you looked (a pick, a pair or a duel); look at it again, then decide.", 409)
            rec = {"engine": "new", "at": time.time(), "by": by[:40], "run": ev["card"].get("run"), "hash": h,
                   "recommendation": (ev.get("recommendation") or {}).get("say"),
                   "seen": {k: ev["card"].get(k) for k in ("old", "new", "critic", "her", "duels")}}
        else:
            rec = {"engine": "old", "at": time.time(), "by": by[:40]}
        hist.append({k: rec.get(k) for k in ("engine", "at", "by", "run", "hash", "recommendation")})
        data = {**rec, "history": hist}
        f = _file()
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(f)
        _CACHE["mtime"] = None
    say = ("New websites are now built on the new engine. Websites already built stay as they are; an older one moves "
           "only when you tap Upgrade this site." if go else
           "New websites are built on the old engine again. Websites already built on the new engine stay as they are.")
    return {**view(), "say": say}


def view() -> dict[str, Any]:
    from ..config import get_settings
    st = state()
    switch = bool(getattr(get_settings(), "studio_react_sites", False))
    return {"engine": st.get("engine"), "at": st.get("at"), "run": st.get("run"), "history": st.get("history")[-10:],
            "server_switch": switch, "new_sites_on": "new" if (switch or st.get("engine") == "new") else "old"}
