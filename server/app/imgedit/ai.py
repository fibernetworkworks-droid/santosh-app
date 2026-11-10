"""AI image edits: the jobs a model has to do. Engines are tried in a fixed order and the first one that is REALLY set up
runs; the answer always says which engine did the work. Nothing here pretends: no engine = a plain sentence saying what to
set on the server, and (for upscaling only) an honest plain enlargement instead.

Engines, in order of preference:
  rembg   local, MIT, no key (background removal) - only if the package and its model are present
  gemini  photogen (GEMINI_API_KEY): generative edits, the same path photo_banao uses
  zoo     the BYOK gateways (ZOO_KIE_KEY / ZOO_MUAPI_KEY), models named in ROUTES below
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Any

from . import ops

log = logging.getLogger("santosh.imgedit")


class AIError(Exception):
    pass


class NoEngine(AIError):
    """No engine is set up for this job. The message says what to set."""


# --------------------------------------------------------------------------- what each job is
# Generative jobs: one instruction template each. The words the user gives are checked first (safety), then dropped into
# the template - the template itself says "keep faces and everything else unchanged".
KEEP = "Keep every person's face, identity, body shape, skin, expression and pose exactly as they are. Change nothing else."
TEMPLATES = {
    "edit": "{what}. " + KEEP,
    "remove_object": "Remove {what} from this photo and fill the space naturally to match the surroundings. " + KEEP,
    "replace_bg": "Replace only the background with {what}. Keep the subject's edges clean and the lighting believable. " + KEEP,
    "restyle": "Restyle this picture as {what}. Keep the same composition and the same people.",
    "restore": ("Restore this old photograph: remove scratches, dust, stains and fading, even out the tone and make it "
                "sharper. " + KEEP + " Do not add people or objects."),
    "colorize": ("Colourise this black-and-white photograph with natural, realistic colours. " + KEEP +
                 " Do not add or remove anything."),
}
NEEDS_WHAT = {"edit", "remove_object", "replace_bg", "restyle"}
GENERATIVE = set(TEMPLATES)
TECHNICAL = {"remove_bg", "upscale"}
AI_OPS = GENERATIVE | TECHNICAL

# zoo model ids per job, best first. A test pins every id against zoo_catalog.json.
ROUTES: dict[str, list[str]] = {
    "remove_bg": ["i2i:kie:recraft-remove-background", "i2i:ai-background-remover"],
    "upscale": ["i2i:kie:topaz-image-upscale", "i2i:topaz-image-upscale", "i2i:seedvr2-image-upscale",
                "i2i:ai-image-upscaler"],
    "generative": ["i2i:kie:nano-banana-edit", "i2i:kie:qwen-image-edit", "i2i:nano-banana-edit",
                   "i2i:qwen-image-edit", "i2i:flux-2-dev-edit"],
}

# --------------------------------------------------------------------------- safety
_WATERMARK = re.compile(r"\b(water ?mark|copyright|getty|shutterstock|istock|adobe stock|alamy|dreamstime|stock photo mark|"
                        r"logo of (the )?(photographer|studio)|credit line|photographer'?s? (name|mark|logo)|"
                        r"signature|dastakhat|hastakshar)\b", re.I)
_DOC_NAME = re.compile(r"(aadhaa?r|aadhar|pan[ _-]?card|voter|licen[cs]e|passport|marksheet|certificate|cheque|"
                       r"bank[ _-]?statement|invoice|salary|payslip|\bid\b|identity)", re.I)
_DOC_EDIT = re.compile(r"\b(name|number|date|dob|birth|photo|address|amount|marks|grade|seal|stamp|sign)\b", re.I)
_MINOR = re.compile(r"\b(child|kid|baby|boy|girl|toddler|minor|school ?(boy|girl)|bachcha|bachchi|beti|beta)\b", re.I)
_BODY = re.compile(r"\b(body|figure|waist|chest|bust|thigh|skinny|slim|bigger|smaller|curvy|abs|muscle)\b", re.I)


def check_words(words: str, op: str, filename: str = "") -> str:
    """'' when fine, else the plain reason Hoola will not do it. Runs BEFORE any engine is touched."""
    from .. import photogen
    w = " ".join(str(words or "").split())
    if op in GENERATIVE and op in NEEDS_WHAT and not w:
        return "Kya badalna hai, ek line mein bataiye."
    if op in GENERATIVE:
        why = photogen.problem(w or op, edit=True)
        if why:
            return why
        if _WATERMARK.search(w):
            return ("Watermark, copyright mark, photographer ka naam ya signature hatana Hoola nahi karta - woh doosre ki "
                    "mehnat hai. Apni photo ho to original bina-watermark file bhejiye.")
        if filename and _DOC_NAME.search(filename):
            return ("Yeh kisi sarkari / bank / marks ke kaagaz ki photo lagti hai; AI se uska andar ka likha hua badalna "
                    "Hoola nahi karta (nakli kaagaz ban sakta hai). Sirf size / crop / compress jaise badlav ho sakte hain.")
        if _BODY.search(w) and _MINOR.search(w):
            return "Bachchon ki tasveer mein aise badlav Hoola nahi karta."
    elif w:
        why = photogen.problem(w, edit=True)
        if why:
            return why
    return ""


# --------------------------------------------------------------------------- engine discovery (no network)
def _rembg_ok() -> bool:
    try:
        import rembg  # noqa: F401
        return True
    except Exception:
        return False


def _gemini_ok() -> bool:
    try:
        from ..config import get_settings
        return bool(get_settings().gemini_api_key)
    except Exception:
        return False


def _zoo_candidates(op: str) -> list[dict]:
    from .. import zoo
    key = "generative" if op in GENERATIVE else op
    out = []
    for mid in ROUTES.get(key, []):
        try:
            m = zoo.model(mid)
        except Exception:
            continue
        out.append(m)
    return out


def plan(op: str) -> list[dict]:
    """The ordered engines for a job with whether each is usable RIGHT NOW. No network, no cost."""
    from .. import zoo
    rows: list[dict] = []
    if op == "remove_bg":
        rows.append({"engine": "rembg", "id": "rembg", "ready": _rembg_ok(),
                     "why": "" if _rembg_ok() else "rembg package server par nahi hai"})
    if op in GENERATIVE:
        rows.append({"engine": "gemini", "id": "photogen", "ready": _gemini_ok(),
                     "why": "" if _gemini_ok() else "GEMINI_API_KEY server par nahi hai"})
    for m in _zoo_candidates(op):
        ok = zoo.ready_for(m)
        gw = zoo.gateway_of(m)
        rows.append({"engine": "zoo", "id": m["id"], "name": m.get("name"), "gateway": gw, "ready": bool(ok),
                     "why": "" if ok else ("ZOO_KIE_KEY" if gw == "kie" else "ZOO_MUAPI_KEY") + " server par nahi hai"})
    return rows


def status() -> dict[str, Any]:
    """What can run today, per job - for the guide. Honest: ready means a key / package is there, not that it was tested."""
    out = {}
    for op in sorted(AI_OPS):
        p = plan(op)
        ready = [r for r in p if r["ready"]]
        out[op] = {"ready": bool(ready), "first": (ready[0]["engine"] + ":" + ready[0]["id"]) if ready else None,
                   "needs": sorted({r["why"].split(" ")[0] for r in p if not r["ready"] and r["why"]}) if not ready else []}
    return out


# --------------------------------------------------------------------------- running
def _png(im, ) -> bytes:
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()


def _jpeg_for_model(im, limit: int = 2048) -> bytes:
    """What goes to a model: a flattened JPEG, longest side <= limit, EXIF gone."""
    rgb = ops.flatten(im)
    rgb.thumbnail((limit, limit))
    out = io.BytesIO()
    rgb.save(out, "JPEG", quality=92)
    return out.getvalue()


def _remove_bg_local(im):
    from rembg import remove
    from PIL import Image
    out = remove(ops.flatten(im))
    if not isinstance(out, Image.Image):
        out = Image.open(io.BytesIO(out))
    return out.convert("RGBA")


async def _fetch(url: str, limit: int = 30_000_000) -> bytes:
    import httpx
    from .. import zoo
    zoo._public(url)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=20), follow_redirects=False) as c:
        r = await c.get(url)
        if r.status_code >= 400:
            raise AIError(f"result download HTTP {r.status_code}")
        if len(r.content) > limit:
            raise AIError("result bahut bada hai")
        return r.content


def _skip(e: Exception) -> bool:
    s = str(e).lower()
    return isinstance(e, AIError) is False and any(w in s for w in ("404", "403", "not found", "not support", "unsupported",
                                                                       "permission", "no longer", "does not exist"))


async def run_op(op: str, im, params: dict, tenant: str = "", filename: str = "") -> dict[str, Any]:
    """Run one AI job. Returns {"image": PIL image, "engine": ..., "label": bool (generative), "note": ...}.
    Raises AIError with a plain reason; NoEngine when nothing is set up."""
    if op not in AI_OPS:
        raise AIError(f"'{op}' AI op nahi hai. AI ops: " + ", ".join(sorted(AI_OPS)))
    what = str(params.get("what") or params.get("prompt") or params.get("background") or params.get("style")
               or params.get("instruction") or "").strip()
    why = check_words(what, op, filename)
    if why:
        raise AIError(why)
    rows = plan(op)
    tried: list[str] = []
    for r in rows:
        if not r["ready"]:
            continue
        try:
            if r["engine"] == "rembg":
                img = await asyncio.to_thread(_remove_bg_local, im)
                return {"image": img, "engine": "rembg (local)", "label": False, "note": ""}
            if r["engine"] == "gemini":
                from .. import photogen
                prompt = TEMPLATES[op].format(what=what)
                res = await asyncio.to_thread(photogen.make, prompt, [_jpeg_for_model(im)], "", "best")
                from PIL import Image
                # photogen.label() already added the small "AI se bana" corner label to this picture
                return {"image": Image.open(io.BytesIO(res["png"])).convert("RGB"),
                        "engine": f"gemini ({res.get('model')})", "label": False, "labelled": True, "note": ""}
            if r["engine"] == "zoo":
                img = await _zoo_run(op, r["id"], im, what, tenant, params)
                return {"image": img, "engine": f"zoo:{r['id']}", "label": op in GENERATIVE, "note": ""}
        except Exception as e:                          # one engine failing moves on to the next, and is reported
            log.warning("imgedit %s via %s failed: %s", op, r["id"], str(e)[:200])
            tried.append(f"{r['id']}: {str(e)[:120]}")
            continue
    if tried:
        raise AIError("Engine chale par sab fail: " + " | ".join(tried[:3]))
    need = sorted({r["why"] for r in rows if r["why"]})
    raise NoEngine("Is kaam ka koi engine abhi set nahi hai (" + "; ".join(need) + "). Owner VPS .env mein key daale, "
                   "tab chalega." + (" Tab tak 'upscale_local' se seedha bada kar sakta hoon (naya detail nahi aata)."
                                      if op == "upscale" else ""))


async def _zoo_run(op: str, model_id: str, im, what: str, tenant: str, params: dict):
    from PIL import Image
    from .. import zoo
    m = zoo.model(model_id)
    ref = "data:image/jpeg;base64," + __import__("base64").b64encode(_jpeg_for_model(im)).decode()
    extra: dict[str, Any] = {}
    if op == "upscale" and "topaz" in model_id and "kie" in model_id:
        extra["upscale_factor"] = str(int(max(1, min(8, float(params.get("factor", 2))))))
    prompt = TEMPLATES[op].format(what=what) if op in GENERATIVE else ""
    r = await zoo.run(m, prompt, tenant=tenant, image_urls=[ref], extra=extra, wait_s=110.0)
    if r["status"] == "failed":
        raise AIError(r.get("error") or "engine ne fail bataya")
    if r["status"] != "done" or not r.get("urls"):
        raise AIError("engine ne abhi tak jawab nahi diya (der lag rahi hai)")
    data = await _fetch(r["urls"][0])
    try:
        out = Image.open(io.BytesIO(data))
        out.load()
    except Exception:
        raise AIError("engine ka result photo nahi nikla") from None
    return out.convert("RGBA") if out.mode in ("RGBA", "LA", "P") else out.convert("RGB")
