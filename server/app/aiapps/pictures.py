"""v0.999.126: her AI App makes pictures for her visitors - only when SHE switched it on in the app's Settings.

Every picture goes through the same doors as her app's answers, and more:
- the app is live and the visitor agreed to its notice (their session);
- her own refused topics, Hoola's picture rules (photogen.problem: no nude / sexual pictures, no fake IDs, certificates,
  banknotes or stamps, no face swaps, no real well-known people, no national emblems) and no secrets, all in code BEFORE
  any picture is made;
- a cap per visitor a day (her number, 1-10) and the app's monthly cost ceiling (each picture is counted into it);
- every picture carries the AI mark drawn on it and in its file (photogen.label);
- the picture is kept on Hoola and opened only with its own signed link (the visitor who made it, and her logs).
Her words for the app (`pictures.hint`) frame what it makes; the visitor's words are data, never instructions."""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

from ..db import new_id, now, session
from .models import AiApp, AiAppMessage

log = logging.getLogger("santosh.aiapps")
MAX_WORDS = 500
MAKE: list[Any] = []                                   # tests put a fake picture maker here


class PictureError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def _dir(app_id: str) -> Path:
    from ..config import get_settings
    base = Path(getattr(get_settings(), "data_dir", "") or "data")
    d = base / "aiapps" / "pictures" / re.sub(r"[^A-Za-z0-9_-]", "", app_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _secret() -> bytes:
    from ..site import webapp as W
    return W._secret()


def sign(pid: str) -> str:
    return hmac.new(_secret(), f"aiapp-picture:{pid}".encode(), hashlib.sha256).hexdigest()[:32]


def file_of(a: AiApp, pid: str, key: str) -> Path | None:
    """The picture file, only with its own signed key."""
    if not re.fullmatch(r"aip_[A-Za-z0-9]{6,40}", pid or "") or not hmac.compare_digest(sign(pid), str(key or "")):
        return None
    f = _dir(a.id) / f"{pid}.png"
    return f if f.is_file() else None


def made_today(a: AiApp, session_id: str) -> int:
    since = now() - timedelta(hours=24)
    with session() as s:
        return s.query(AiAppMessage).filter(AiAppMessage.app_id == a.id, AiAppMessage.session_id == session_id,
                                            AiAppMessage.outcome == "picture", AiAppMessage.created_at >= since).count()


def _make(prompt: str) -> dict[str, Any]:
    if MAKE:
        return MAKE[0](prompt)
    from .. import photogen as PG
    return PG.make(prompt, quality="fast")


def make(a: AiApp, session_id: str, channel: str, words: str) -> dict[str, Any]:
    from .. import photogen as PG
    from . import runtime as RT
    from . import store as ST
    soul, version = ST.live_soul(a)
    pic = soul.get("pictures") or {}
    if not pic.get("on"):
        raise PictureError("This assistant does not make pictures.", 404)
    w = " ".join(str(words or "").split())[:MAX_WORDS]
    if len(w) < 3:
        raise PictureError("Say in a few words what picture to make.", 400)
    if RT._secret(w):
        raise PictureError("Please do not share an OTP, PIN, password or card number here.", 400)
    low = w.lower()
    for topic in soul.get("refuse") or []:
        if topic and str(topic).lower() in low:
            raise PictureError("This assistant does not make pictures about that.", 400)
    why = PG.problem(w)
    if why:
        raise PictureError(why, 400)
    per = int(pic.get("per_visitor_day") or 3)
    if made_today(a, session_id) >= per:
        raise PictureError(f"That is {per} pictures today - the most for one visitor. Try again tomorrow.", 429)
    cap = float((soul.get("limits") or {}).get("monthly_cap_inr", 0) or 0)
    cost = float(PG.COST_INR["fast"])
    if cap <= 0 or RT.month_spend(a.id) + cost > cap:
        raise PictureError("The assistant cannot make more pictures this month.", 429)
    about = str(pic.get("hint") or "").strip()
    prompt = (f"{about}. " if about else "") + f"The visitor asks for: {w}"
    try:
        got = _make(prompt)
    except PG.Refused as e:
        raise PictureError(str(e), 400)
    except Exception as e:                            # noqa: BLE001 - the picture engine failed: said, not counted
        log.info("ai app picture failed: %s", e)
        raise PictureError("The picture could not be made right now. Please try again in a minute.", 503)
    pid = new_id("aip").replace("-", "")[:40]
    (_dir(a.id) / f"{pid}.png").write_bytes(got["png"])
    with session() as s:
        m = AiAppMessage(app_id=a.id, tenant_id=a.tenant_id, session_id=session_id or "", channel=channel, version=version,
                         question=RT._mask(w)[:4000], answer=f"(picture {pid})", outcome="picture", sources="[]",
                         action="", ms=0, calls=1, tok_in=0, tok_out=0, inr=float(got.get("cost_inr") or cost))
        s.add(m)
        s.flush()
        mid = m.id
    return {"id": pid, "message_id": mid, "key": sign(pid), "aspect": got.get("aspect") or "1:1",
            "label": "AI-generated", "left_today": max(0, per - made_today(a, session_id))}
