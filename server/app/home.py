"""v0.479.0 HOOLA SMART HOME — Home Assistant par ghar ka control, the W1 workstream of the Platforms plan
(owner: "START bolo aur W1 (0.473.0 smart home)" — re-versioned 0.473.0 -> 0.479.0: the dev's parallel chain
took 0.473…0.478 first; REBASE PROTOCOL respected, rebuilt fresh on ae5bfc58).

Server-only: no desktop file, no new binary. Hoola talks to a Home Assistant instance over its official
REST API (GET /api/states, POST /api/services/<domain>/<service>, `Authorization: Bearer <token>`), so
ESPHome / Zigbee / Matter devices all arrive through HA — raw MQTT is deliberately deferred.

SAFETY (the CLAUDE.md non-negotiable, now executable):
- The HOME gate `home_control` (default OFF — bake on the VPS, then flip) is SEPARATE from PC control.
  Every tool refuses with a clear line while it is off.
- The HA long-lived token lives ONLY in the VPS .env (HOME_ASSISTANT_URL / HOME_ASSISTANT_TOKEN), the zoo
  BYOK pattern — never in chat, never in the repo, never returned to the model (only a masked preview).
- Locks are CONFIRM-ONLY and never autonomous: the model must have asked and carry confirm=true, and a
  routine turn (actor="routine") can never confirm — refused outright.
- Home-safety rules from the frozen brief: AC temperature clamped 20–28 °C, media volume clamped to <= 90 %,
  fridge / washing machine / geyser / heater class appliances are READ-ONLY (name-matched, because they
  usually surface as plain switch/plug entities).
- Every control attempt (success or refusal) lands in the home_audit table.
"""
from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .config import get_settings
from .db import Base, new_id, now, session

GATE_OFF = ("Home control is off right now - the owner has not turned on the 'home_control' switch. "
            "Set HOME_CONTROL=1 in the VPS .env and restart; then I can control the home devices.")

NO_LINK = ("Home Assistant is not connected. Setup: HA app/website → profile (bottom left) → Security → "
           "Long-lived access tokens → Create token. Then add HOME_ASSISTANT_URL (for example "
           "http://192.168.1.10:8123) and HOME_ASSISTANT_TOKEN to the VPS .env and restart.")

# domains Hoola may switch (turn_on / turn_off or their domain-native service); lock rides the
# confirm-only branch of the guard, never the plain path
CONTROL_OK = {"light", "switch", "fan", "cover", "media_player", "humidifier", "input_boolean",
              "scene", "script", "button", "climate", "lock"}
# appliances the frozen brief keeps out of Hoola's hands even when they look like a switch (name-matched)
READONLY_WORDS = re.compile(
    r"fridge|refrigerat|washing|washer|washing_machine|geyser|water_heater|heater|oven|microwave|"
    r"induction|dishwasher|dryer|iron|geaser", re.I)
VOLUME_MAX = 0.9          # speaker <= 90 % (frozen brief)
AC_MIN, AC_MAX = 20.0, 28.0   # AC 20–28 °C (frozen brief)


class HomeAudit(Base):
    """Every control attempt - the trail the owner reads when she asks 'aaj ghar mein kya hua'."""
    __tablename__ = "home_audit"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("hme"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    actor: Mapped[str] = mapped_column(String(40), default="owner")
    entity_id: Mapped[str] = mapped_column(String(120), default="")
    friendly: Mapped[str] = mapped_column(String(160), default="")
    action: Mapped[str] = mapped_column(String(24), default="")            # on | off | lock | unlock | refused
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[str] = mapped_column(Text, default="")                  # service + why-not, never the token
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_table_ready = False
_ready_engines: set[int] = set()


def ensure_table() -> None:
    """Self-heal (the v0.190.1 lesson): a DB born before this module was registered gets its table
    on the first audit write - no manual SQL, no restore. Keyed by engine id so a fresh engine
    (tests, a pm2 restart) always creates checkfirst exactly once."""
    global _table_ready
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _ready_engines:
        _table_ready = eng is not None
        return
    HomeAudit.__table__.create(eng, checkfirst=True)
    _ready_engines.add(id(eng))
    _table_ready = True


def audit(tenant: str, conv: str, actor: str, entity_id: str, friendly: str, action: str,
          ok: bool, detail: str = "") -> None:
    try:
        ensure_table()
        with session() as s:
            s.add(HomeAudit(tenant_id=tenant, conversation_id=conv[:40], actor=(actor or "owner")[:40],
                            entity_id=entity_id[:120], friendly=friendly[:160], action=action[:24],
                            ok=ok, detail=detail[:2000]))
    except Exception:                                    # noqa: BLE001 - audit never breaks a home action
        pass


# ----------------------------------------------------------------------------- link (env, zoo pattern)
def _link() -> tuple[str, str] | None:
    st = get_settings()
    base = (getattr(st, "home_assistant_url", "") or "").strip().rstrip("/")
    token = (getattr(st, "home_assistant_token", "") or "").strip()
    if base and token and token not in ("changeme",):
        return base, token
    return None


def link_status() -> dict:
    """What the model may see: connected-or-not + a masked token. NEVER the token itself."""
    lk = _link()
    if lk is None:
        return {"linked": False, "how": NO_LINK}
    base, token = lk
    masked = (token[:4] + "…" + token[-4:]) if len(token) >= 10 else "…" * len(token)
    return {"linked": True, "base": base, "token_masked": masked}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _client(base: str, token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base, headers=_headers(token), timeout=httpx.Timeout(6.0))


async def ping() -> dict:
    """GET /api/ - HA answers 'API running.' when the link is good."""
    lk = _link()
    if lk is None:
        return {"ok": False, "why": "not connected", "status": 0}
    base, token = lk
    try:
        async with _client(base, token) as c:
            r = await c.get("/api/")
            if r.status_code == 200:
                return {"ok": True, "message": r.json().get("message", ""), "status": 200}
            return {"ok": False, "why": f"HA answered {r.status_code}", "status": r.status_code}
    except Exception as e:                               # noqa: BLE001 - network errors are a status, not a crash
        return {"ok": False, "why": f"Could not reach HA: {e.__class__.__name__}", "status": 0}


# ----------------------------------------------------------------------------- reads
def _friendly(st: dict) -> str:
    return (st.get("attributes") or {}).get("friendly_name") or st.get("entity_id", "")


def _domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0].strip().lower()


def _view(st: dict) -> dict:
    at = st.get("attributes") or {}
    out = {"entity_id": st.get("entity_id", ""), "domain": _domain_of(st.get("entity_id", "")),
           "name": _friendly(st), "state": st.get("state", ""),
           "unit": at.get("unit_of_measurement", ""), "controllable": _domain_of(st.get("entity_id", "")) in CONTROL_OK}
    for k in ("temperature", "current_temperature", "brightness", "volume_level", "hvac_action",
              "hvac_mode", "humidity", "battery", "device_class"):
        if at.get(k) is not None:
            out[k] = at[k]
    return out


async def states(domain: str = "", q: str = "", limit: int = 200) -> dict:
    """GET /api/states - the whole house (filtered). Token never leaves this module."""
    lk = _link()
    if lk is None:
        return {"ok": False, "why": NO_LINK, "devices": []}
    base, token = lk
    try:
        async with _client(base, token) as c:
            r = await c.get("/api/states")
        if r.status_code != 200:
            return {"ok": False, "why": f"HA answered {r.status_code} (check the token or URL)", "devices": []}
        rows = r.json() or []
    except Exception as e:                               # noqa: BLE001
        return {"ok": False, "why": f"Could not reach HA: {e.__class__.__name__}", "devices": []}
    dom = (domain or "").strip().lower()
    needle = (q or "").strip().lower()
    out = []
    for st in rows:
        eid = st.get("entity_id", "")
        if not eid or eid.startswith("group."):
            continue
        if not dom and _domain_of(eid) == "binary_sensor":
            continue                       # the noise floor of a house; ask for it by name when wanted
        if dom and _domain_of(eid) != dom:
            continue
        if needle and needle not in eid.lower() and needle not in _friendly(st).lower():
            continue
        out.append(_view(st))
        if len(out) >= max(1, min(int(limit or 200), 400)):
            break
    return {"ok": True, "count": len(out), "devices": out}


async def state_one(entity: str) -> dict:
    eid = (entity or "").strip().lower()
    if not eid:
        return {"ok": False, "why": "Give the entity_id or the device name"}
    lk = _link()
    if lk is None:
        return {"ok": False, "why": NO_LINK}
    base, token = lk
    try:
        async with _client(base, token) as c:
            if "." in eid:
                r = await c.get(f"/api/states/{eid}")
                if r.status_code == 200:
                    return {"ok": True, **_view(r.json())}
                if r.status_code == 404:
                    return {"ok": False, "why": f"{eid} was not found in HA (see the full name with action=devices)"}
                return {"ok": False, "why": f"HA answered {r.status_code}"}
            r = await c.get("/api/states")
            if r.status_code != 200:
                return {"ok": False, "why": f"HA answered {r.status_code}"}
            for st in r.json() or []:
                if eid in st.get("entity_id", "").lower() or eid in _friendly(st).lower():
                    return {"ok": True, **_view(st)}
            return {"ok": False, "why": f"no device with this name was found: {eid}"}
    except Exception as e:                               # noqa: BLE001
        return {"ok": False, "why": f"Could not reach HA: {e.__class__.__name__}"}


# ----------------------------------------------------------------------------- guards
def _guard(entity_id: str, friendly: str, actor: str, confirm: bool) -> tuple[str, str, str] | None:
    """'' when the action may proceed, else (refusal, action_label, detail)."""
    dom = _domain_of(entity_id)
    if dom == "lock":
        if actor == "routine":
            return ("A lock is never opened or closed from a routine - locks are never touched without asking.",
                    "refused", "lock in routine turn")
        if not confirm:
            return ("A lock only after confirmation: ask the user first, and once they say yes send home_on/home_off "
                    "with confirm=true.", "refused", "lock without confirm=true")
        return None
    if dom not in CONTROL_OK:
        return (f"I do not control a device of this type ({dom}): {friendly or entity_id} - only lights, fans, "
                f"switches, covers, media, climate, scenes and scripts. To read it, ask for its state.",
                "refused", f"domain {dom} not controllable")
    blob = f"{entity_id} {friendly}"
    m = READONLY_WORDS.search(blob)
    if m:
        return (f"I do not touch {friendly or entity_id} (a fridge / washer / geyser / heater kind of appliance) - "
                f"big home appliances are read-only. Please turn it on/off yourself.",
                "refused", f"read-only appliance word: {m.group(0)}")
    return None


# ----------------------------------------------------------------------------- controls
_SERVICES = {"cover": ("cover/open_cover", "cover/close_cover"),
             "scene": ("scene/turn_on", "scene/turn_on"),
             "script": ("script/turn_on", "script/turn_on"),
             "button": ("button/press", "button/press"),
             "lock": ("lock/lock", "lock/unlock")}   # home_on = band karna, home_off = kholna


def _service_of(dom: str, on: bool) -> str:
    pair = _SERVICES.get(dom)
    if pair:
        return pair[0] if on else pair[1]
    return f"{dom}/{'turn_on' if on else 'turn_off'}"


async def _post(domain_service: str, payload: dict) -> dict:
    lk = _link()
    if lk is None:
        return {"ok": False, "why": NO_LINK}
    base, token = lk
    try:
        async with _client(base, token) as c:
            r = await c.post(f"/api/services/{domain_service}", json=payload)
        if r.status_code in (200, 201):
            return {"ok": True, "status": r.status_code}
        return {"ok": False, "why": f"HA answered {r.status_code} ({domain_service})", "status": r.status_code}
    except Exception as e:                               # noqa: BLE001
        return {"ok": False, "why": f"Could not reach HA: {e.__class__.__name__}"}


async def _settle(entity_id: str, want: str, wait_s: float = 1.2) -> dict | None:
    """HA services return before the state flips; one short re-read so the say() is honest."""
    if want not in ("on", "off"):
        return None
    t0 = time.monotonic()
    got: dict = {}
    while time.monotonic() - t0 < wait_s:
        got = await state_one(entity_id)
        if got.get("ok") and str(got.get("state", "")).lower() == want:
            return got
        await asyncio.sleep(0.25)
    return got if got.get("ok") else None


def _say_on(friendly: str, dom: str) -> str:
    if dom == "cover":
        return f"{friendly} is open."
    if dom in ("scene", "script"):
        return f"{friendly} has been run."
    if dom == "button":
        return f"{friendly} has been pressed."
    return f"{friendly} is on."


def _say_off(friendly: str, dom: str) -> str:
    return f"{friendly} is off."


async def switch(entity: str, on: bool, tenant: str, conv: str, actor: str = "owner",
                 confirm: bool = False, extra: dict | None = None) -> dict:
    """The one funnel behind home_on / home_off (+ locks, scenes, climate temperature, volume).
    Order: gate FIRST (cheap, no HA call), then resolve, then guards, then the service call."""
    eid = (entity or "").strip().lower()
    if not eid:
        return {"ok": False, "why": "Give the entity_id or the device name (see home_devices)."}

    if not get_settings().home_control:
        audit(tenant, conv, actor, eid, eid, "refused", False, "gate off")
        return {"ok": False, "why": GATE_OFF, "gate_off": True}

    got = await state_one(eid)
    if not got.get("ok"):
        audit(tenant, conv, actor, eid, eid, "refused", False, got.get("why", "device not found"))
        return {"ok": False, "why": got.get("why", "device not found")}
    eid = got.get("entity_id", eid)
    friendly = got.get("name", eid)
    dom = _domain_of(eid)

    why = _guard(eid, friendly, actor, confirm)
    if why:
        refusal, label, detail = why
        audit(tenant, conv, actor, eid, friendly, label, False, detail)
        return {"ok": False, "why": refusal, "refused": True}

    payload: dict[str, Any] = {"entity_id": eid}
    ex = extra or {}
    if dom == "climate" and on and "temperature" in ex:
        try:
            t = round(float(ex["temperature"]), 1)
        except (TypeError, ValueError):
            audit(tenant, conv, actor, eid, friendly, "refused", False, "bad temperature")
            return {"ok": False, "why": "Give the temperature as a number (for example 24)."}
        if not (AC_MIN <= t <= AC_MAX):
            audit(tenant, conv, actor, eid, friendly, "refused", False, f"temperature {t} out of 20-28")
            return {"ok": False, "why": f"I set the AC temperature only between {AC_MIN:.0f} and {AC_MAX:.0f} °C "
                                        f"(you said {t}). That range is the safe one for the home."}
        payload["temperature"] = t
    if dom == "media_player" and "volume_level" in ex:
        try:
            v = round(float(ex["volume_level"]), 2)
        except (TypeError, ValueError):
            audit(tenant, conv, actor, eid, friendly, "refused", False, "bad volume")
            return {"ok": False, "why": "Give the volume as a number between 0.0 and 1.0."}
        if v > VOLUME_MAX:
            v = VOLUME_MAX
        payload["volume_level"] = v

    svc = _service_of(dom, on)
    if dom == "climate":
        svc = ("climate/set_temperature" if ("temperature" in payload) else
               ("climate/set_hvac_mode" if on else svc))
        if svc == "climate/set_hvac_mode":
            payload["hvac_mode"] = (ex.get("hvac_mode") or ("cool" if on else "off")).lower()
        if not on:
            payload["hvac_mode"] = "off"
            svc = "climate/set_hvac_mode"
    if dom == "light" and on and "brightness" in ex:
        try:
            payload["brightness"] = max(1, min(255, int(float(ex["brightness"]))))
        except (TypeError, ValueError):
            pass

    r = await _post(svc, payload)
    ok = bool(r.get("ok"))
    audit(tenant, conv, actor, eid, friendly, ("lock" if dom == "lock" and on else
                                               "unlock" if dom == "lock" else "on" if on else "off"),
          ok, svc if ok else f"{svc} {r.get('why', '')}")
    if not ok:
        return {"ok": False, "why": r.get("why", "the service call failed"), "entity_id": eid}
    settled = await _settle(eid, "on" if on else "off")
    out = {"ok": True, "entity_id": eid, "name": friendly, "service": svc, "say": (_say_on if on else _say_off)(friendly, dom)}
    if settled:
        out["state"] = settled.get("state", "")
        out["name"] = settled.get("name", friendly)
    if dom == "lock":
        out["say"] = (f"{friendly} is locked." if on else f"{friendly} is unlocked. Take care.")
    return out


def recent_audit(tenant: str, limit: int = 20) -> dict:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(HomeAudit).where(HomeAudit.tenant_id == tenant)
                         .order_by(HomeAudit.created_at.desc()).limit(max(1, min(int(limit or 20), 100)))).all()
        return {"count": len(rows), "entries": [
            {"at": r.created_at.isoformat() if r.created_at else "", "entity": r.entity_id, "name": r.friendly,
             "action": r.action, "ok": r.ok, "detail": r.detail} for r in rows]}
