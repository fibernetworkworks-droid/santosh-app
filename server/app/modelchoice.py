"""v0.740 MODEL DROPDOWN (owner: "IN WEB CONSOLE LETS USER CHOOSE THE MODEL VIA DROPDOWN"): each user picks the
chat model from the owner's list in the console composer; her chat turns run on it.

- The list is the OWNER's (`chat_models`, comma-separated OpenRouter slugs, plus GLM_MODEL as the default) - a user
  can never pick a model the owner did not allow (cost + safety: an expensive or untrusted model needs her word).
- Each entry is described from its own OpenRouter list (v0.739 model profile): name, free or priced, reads pictures,
  takes tools. A model without tools is shown but cannot be picked (Hoola cannot work without tools).
- Her choice lives per tenant in data/model_choice/<tenant>.json; '' = the default. `santosh._run_turn` sets
  llm.MODEL_NOW from it, so the whole turn (every step, picture / PDF routing, reasoning field, window) follows the
  chosen model through the same model profile.
- Only for the OpenRouter GLM brain: on any other setup the dropdown says why it is not offered.
Switch `chat_model_choice` (default on).
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from .config import get_settings

_LOCK = threading.Lock()


class ChoiceError(ValueError):
    pass


def _dir() -> Path:
    d = str(getattr(get_settings(), "model_choice_dir", "") or "")
    return Path(d) if d else Path("data") / "model_choice"


def _file(tenant: str) -> Path:
    return _dir() / (re.sub(r"[^A-Za-z0-9_-]+", "_", tenant or "main")[:80] + ".json")


def offered() -> tuple[bool, str]:
    st = get_settings()
    if not bool(getattr(st, "chat_model_choice", False)):
        return False, "Model choice is switched off on this server."
    if not st.glm_api_key or "openrouter.ai" not in (st.glm_base_url or ""):
        return False, "Model choice works when the chat runs on OpenRouter."
    if (st.chat_llm or "auto").lower() == "claude":
        return False, "This server's chat runs on Claude."
    return True, ""


def allowed() -> list[str]:
    st = get_settings()
    out: list[str] = []
    for m in [st.glm_model or ""] + str(getattr(st, "chat_models", "") or "").split(","):
        m = m.strip()
        if m and m not in out:
            out.append(m)
    return out


def chosen(tenant: str) -> str:
    """Her pick, '' = the default. A pick the owner later removed from the list falls back to the default."""
    if not offered()[0]:
        return ""
    try:
        m = str(json.loads(_file(tenant).read_text()).get("model") or "")
    except Exception:
        return ""
    return m if m in allowed() else ""


def _entry(slug: str, selected: str) -> dict[str, Any]:
    from .agent import modelprofile as mp
    p = mp.get(slug)
    price = p.get("price") or {}
    free = slug.endswith(":free") or (str(price.get("prompt")) in ("0", "0.0") and
                                      str(price.get("completion")) in ("0", "0.0"))
    known = bool(p.get("known"))
    tools = "tools" in (p.get("params") or []) if known else None
    return {"id": slug, "name": p.get("name") or slug.split("/")[-1].replace(":free", ""),
            "free": free, "reads": p.get("inputs") if known else ["text"], "tools": tools,
            "context": p.get("context") or 0, "default": slug == (get_settings().glm_model or ""),
            "selected": slug == selected, "pickable": tools is not False,
            "note": "" if tools is not False else "This model takes no tools, so Hoola cannot work with it."}


def view(tenant: str) -> dict[str, Any]:
    ok, why = offered()
    if not ok:
        return {"available": False, "reason": why, "models": [], "selected": ""}
    sel = chosen(tenant) or (get_settings().glm_model or "")
    return {"available": True, "reason": "", "selected": sel, "models": [_entry(m, sel) for m in allowed()]}


def choose(tenant: str, model: str) -> dict[str, Any]:
    ok, why = offered()
    if not ok:
        raise ChoiceError(why)
    model = (model or "").strip()
    if model and model not in allowed():
        raise ChoiceError("That model is not on this server's list.")
    if model and _entry(model, "").get("tools") is False:
        raise ChoiceError("That model takes no tools, so Hoola cannot work with it.")
    if model == (get_settings().glm_model or ""):
        model = ""                        # the default is stored as no choice
    with _LOCK:
        _dir().mkdir(parents=True, exist_ok=True)
        tmp = _file(tenant).with_suffix(".tmp")
        tmp.write_text(json.dumps({"model": model}))
        tmp.replace(_file(tenant))
    return view(tenant)


def warm() -> None:
    """Read every listed model's profile in the background (start), so the dropdown has names and abilities."""
    if not offered()[0]:
        return
    from .agent import modelprofile as mp
    for m in allowed():
        mp.refresh_in_background(m)
