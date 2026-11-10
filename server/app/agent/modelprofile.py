"""v0.739 MODEL PROFILE (owner: "WHY EVERY NEW MODEL NEED UPDATE IN CODE EVERY TIME --- WHY IT IS NOT GENERALIZE"
-> "GO"): what the configured chat model can do is READ, not written into the code.

Before this, every model swap needed a release: whether it reads pictures (v0.735), whether it needs / refuses a
reasoning field (v0.699 / v0.700), which fields only GLM understands (v0.697) were all hand-written per provider.
OpenRouter publishes every model's own facts at GET {base}/models/{model}/endpoints - its input kinds (text / image /
video / file), the parameters its providers accept (tools, reasoning, ...), its context length and its price. This
module reads that once at start (and once a day), keeps it in memory and on disk, and the request builder asks it:

- `reads("image")`        -> send pictures to the model as pictures (else they go to Claude / a text note)
- `supports("reasoning")` -> send the reasoning field (else none: a non-reasoning model is never sent one)
- `supports("tools")`     -> a model without tools is named loudly at start (Hoola cannot work without tools)
- `context()`             -> the model's own window, used as the chat window when it is smaller than the setting
- `learn(...)`            -> what a model's own error taught (e.g. "reasoning is mandatory") is remembered for it

Unknown (not OpenRouter, the read failed, nothing on disk) = `known` False and the callers keep their old settings,
so nothing breaks when the list cannot be reached. Switch `model_profile` (default on); off = the old hand-written
behaviour exactly. A new model = `GLM_MODEL=<slug>` in .env + a restart - no code change.
"""
from __future__ import annotations

import json
import re
import logging
import threading
import time
from pathlib import Path
from typing import Any

from ..config import get_settings

log = logging.getLogger("santosh.modelprofile")

TTL_S = 24 * 3600
_MEM: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_BUSY: set[str] = set()


def on() -> bool:
    try:
        return bool(getattr(get_settings(), "model_profile", False))
    except Exception:
        return False


def current_model() -> str:
    """The model THIS turn runs on: her choice from the console dropdown (v0.740, llm.MODEL_NOW), else GLM_MODEL."""
    try:
        from .llm import MODEL_NOW
        m = MODEL_NOW.get()
    except Exception:
        m = ""
    return m or (get_settings().glm_model or "")


def _key(model: str = "") -> str:
    from . import providers as pv
    model = model or current_model()
    return f"{pv.base_of(pv.split(model)[0])}|{model}"


def _dir() -> Path:
    d = str(getattr(get_settings(), "model_profile_dir", "") or "")
    return Path(d) if d else Path("data") / "modelprofile"


def _file(key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:180]
    return _dir() / f"{safe}.json"


def _openrouter(base: str) -> bool:
    return "openrouter.ai" in (base or "")


def parse(model: str, data: dict) -> dict[str, Any]:
    """OpenRouter's /models/{id}/endpoints answer -> a profile. Pure (tested on its real shape)."""
    d = (data or {}).get("data") or {}
    arch = d.get("architecture") or {}
    inputs = sorted({str(x).lower() for x in (arch.get("input_modalities") or []) if x})
    if not inputs:   # older shape: "modality": "text+image->text"
        mod = str(arch.get("modality") or "").split("->")[0]
        inputs = sorted({x.strip().lower() for x in mod.split("+") if x.strip()})
    eps = [e for e in (d.get("endpoints") or []) if isinstance(e, dict)]
    params: set[str] = set()
    for e in eps:
        params |= {str(p) for p in (e.get("supported_parameters") or [])}
    ctx = max([int(e.get("context_length") or 0) for e in eps] + [int(d.get("context_length") or 0), 0])
    price = {}
    for e in eps[:1]:
        p = e.get("pricing") or {}
        price = {"prompt": p.get("prompt"), "completion": p.get("completion"), "image": p.get("image")}
    return {"model": model, "known": bool(inputs or params), "source": "openrouter", "inputs": inputs or ["text"],
            "params": sorted(params), "context": ctx, "price": price, "providers": len(eps), "learned": {},
            "at": time.time()}


def _unknown(model: str) -> dict[str, Any]:
    return {"model": model, "known": False, "source": "none", "inputs": ["text"], "params": [], "context": 0,
            "price": {}, "providers": 0, "learned": {}, "at": 0.0}


def _load_disk(key: str) -> dict[str, Any] | None:
    try:
        return json.loads(_file(key).read_text())
    except Exception:
        return None


def _save_disk(key: str, prof: dict[str, Any]) -> None:
    try:
        _dir().mkdir(parents=True, exist_ok=True)
        _file(key).write_text(json.dumps(prof, ensure_ascii=False, indent=1))
    except Exception as e:   # noqa: BLE001 - a read-only disk never breaks a chat
        log.info("model profile not saved: %s", e)


_CAT: dict[str, Any] = {"at": 0.0, "data": []}


def catalogue(timeout: float = 20.0) -> list[dict]:
    """OpenRouter's public model catalogue (no key), kept 24 h - used to describe a model served by another provider
    that publishes no abilities of its own (Gemini / Groq / NVIDIA / Z.ai OpenAI-compatible lists are names only)."""
    if _CAT["data"] and time.time() - _CAT["at"] < TTL_S:
        return _CAT["data"]
    try:
        import httpx
        r = httpx.get("https://openrouter.ai/api/v1/models", timeout=timeout)
        if r.status_code < 400:
            _CAT.update(at=time.time(), data=list((r.json() or {}).get("data") or []))
    except Exception as e:   # noqa: BLE001
        log.info("OpenRouter catalogue not read: %s", str(e)[:120])
    return _CAT["data"]


def _norm(x: str) -> str:
    x = (x or "").lower().split("/")[-1]
    x = re.sub(r":free$|-latest$|-instruct$|-it$", "", x)
    return re.sub(r"[^a-z0-9]+", "", x)


def match(provider: str, slug: str) -> dict | None:
    """The catalogue entry for the same model (by its own name), preferring the provider's own vendor + a paid id."""
    from . import providers as pv
    want = _norm(slug)
    hits = [m for m in catalogue() if _norm(m.get("id", "")) == want]
    if not hits:
        return None
    vendor = pv.PROVIDERS.get(provider, ("", "", "", ""))[3]
    hits.sort(key=lambda m: (not (vendor and m["id"].startswith(vendor + "/")), m["id"].endswith(":free"), m["id"]))
    return hits[0]


def refresh(timeout: float = 15.0, model: str = "") -> dict[str, Any]:
    """Read a model's facts now (sync; call from a thread). Keeps what was learned before.
    OpenRouter model -> its own endpoints list; another provider's model -> the same model in OpenRouter's catalogue
    (v0.741); nothing found -> unknown (the callers keep their safe defaults: text only, no extra fields)."""
    from . import providers as pv
    model = model or current_model()
    key = _key(model)
    prov, slug = pv.split(model)
    old = _MEM.get(key) or _load_disk(key) or {}
    if model and pv.is_openrouter(model):
        try:
            import httpx
            k = pv.key_of(prov)
            h = {"Authorization": f"Bearer {k}"} if k else {}
            r = httpx.get(f"{pv.base_of(prov)}/models/{slug}/endpoints", headers=h, timeout=timeout)
            if r.status_code >= 400:
                raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
            prof = parse(model, r.json())
            prof["name"] = str(((r.json() or {}).get("data") or {}).get("name") or model)
            prof["learned"] = old.get("learned") or {}
        except Exception as e:   # noqa: BLE001
            log.warning("model profile for %s could not be read (%s) - keeping %s", model, str(e)[:160],
                        "the saved one" if old else "the old settings")
            if old:
                return _remember(key, old)
            prof = {**_unknown(model), "source": "read failed"}
    elif model and prov:
        hit = match(prov, slug)
        if hit:
            prof = parse(model, {"data": {"architecture": hit.get("architecture") or {}, "endpoints": [
                {"supported_parameters": hit.get("supported_parameters") or [],
                 "context_length": hit.get("context_length") or 0}]}})
            prof.update(name=f"{hit.get('name') or slug} ({pv.label_of(prov)})", price={},
                        source=f"openrouter catalogue ({hit['id']})", learned=old.get("learned") or {})
        else:
            prof = {**_unknown(model), "name": f"{slug} ({pv.label_of(prov)})", "learned": old.get("learned") or {}}
    else:
        prof = {**_unknown(model), "learned": old.get("learned") or {}}
    _report(prof)
    _save_disk(key, prof)
    return _remember(key, prof)


def _remember(key: str, prof: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        _MEM[key] = prof
    return prof


def _report(prof: dict[str, Any]) -> None:
    if not prof.get("known"):
        return
    log.info("model profile %s: reads %s, params %s, context %s, %s providers", prof["model"],
             "/".join(prof["inputs"]), ",".join(p for p in prof["params"] if p in ("tools", "reasoning",
                                                                                 "response_format")) or "-",
             prof["context"], prof["providers"])
    if "tools" not in prof["params"]:
        log.error("MODEL %s DOES NOT ACCEPT TOOLS on OpenRouter - Hoola cannot do work with it; pick another GLM_MODEL",
                  prof["model"])


def refresh_in_background(model: str = "") -> None:
    model = model or current_model()
    key = _key(model)
    if key in _BUSY:
        return
    _BUSY.add(key)

    def go():
        try:
            refresh(model=model)
        finally:
            _BUSY.discard(key)
    threading.Thread(target=go, name="model-profile", daemon=True).start()


def get(model: str = "") -> dict[str, Any]:
    """The profile for a model (default: this turn's). Never blocks on the network: memory, else disk (and a
    background read when it is missing or a day old), else unknown."""
    model = model or current_model()
    key = _key(model)
    prof = _MEM.get(key)
    if prof is None:
        prof = _load_disk(key)
        if prof is not None:
            _remember(key, prof)
    if prof is None or (time.time() - float(prof.get("at") or 0)) > TTL_S:
        if on() and model:
            refresh_in_background(model)
    return prof or _unknown(model)


def known() -> bool:
    return on() and bool(get().get("known"))


def reads(kind: str) -> bool | None:
    """True / False when the profile knows; None = unknown (the caller keeps its old setting)."""
    if not known():
        return None
    return kind.lower() in get().get("inputs", [])


def supports(param: str) -> bool | None:
    if not known():
        return None
    p = get()
    learned = p.get("learned") or {}
    if param == "reasoning" and learned.get("reasoning_mandatory"):
        return True
    if param == "reasoning" and learned.get("reasoning_refused"):
        return False
    return param in p.get("params", [])


def context() -> int:
    return int(get().get("context") or 0) if known() else 0


def learn(**facts: Any) -> None:
    """Remember what the model's own answer taught (e.g. reasoning_mandatory=True), for this model, on disk."""
    if not on():
        return
    key = _key()
    prof = dict(get())
    prof["learned"] = {**(prof.get("learned") or {}), **facts}
    log.info("model profile %s learned %s", prof.get("model"), facts)
    _save_disk(key, prof)
    _remember(key, prof)


def summary() -> dict[str, Any]:
    p = get()
    return {"on": on(), "model": p.get("model"), "known": p.get("known"), "source": p.get("source"),
            "inputs": p.get("inputs"), "tools": "tools" in (p.get("params") or []),
            "reasoning": supports("reasoning"), "context": p.get("context"), "price": p.get("price"),
            "learned": p.get("learned") or {}, "read_at": p.get("at")}


def _reset_for_tests() -> None:
    _MEM.clear()
    _BUSY.clear()


if __name__ == "__main__":   # python -m app.agent.modelprofile  -> read now and print what the model can do
    import pprint
    logging.basicConfig(level=logging.INFO)
    refresh()
    pprint.pprint(summary())
