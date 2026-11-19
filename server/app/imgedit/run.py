"""One pipeline over a photo: local steps and at most ONE AI step, in the order given. Everything is validated before
anything is paid for, and the report says exactly what ran (and on which engine)."""
from __future__ import annotations

import asyncio
import io
from typing import Any

from PIL import Image

from . import ai, ops


def validate(steps: list[dict], filename: str = "") -> list[dict]:
    """Cheap checks first (names, count, safety words). Raises ops.EditError / ai.AIError; touches no engine."""
    if not isinstance(steps, list) or not steps:
        raise ops.EditError("Which changes should be made? Write at least one op in steps (see the guide).")
    if len(steps) > ops.MAX_STEPS:
        raise ops.EditError(f"Up to {ops.MAX_STEPS} steps at a time.")
    clean, n_ai = [], 0
    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict) or not st.get("op"):
            raise ops.EditError(f"Step {i} needs an 'op' name.")
        name = str(st["op"]).lower().strip()
        if name in ai.AI_OPS:
            n_ai += 1
            if n_ai > 1:
                raise ops.EditError("Only ONE AI step on a photo at a time (for both cost and quality). "
                                    "Do the second change in a separate run.")
            what = str(st.get("what") or st.get("prompt") or st.get("background") or st.get("style")
                       or st.get("instruction") or "").strip()
            why = ai.check_words(what, name, filename)
            if why:
                raise ai.AIError(why)
        elif name not in ops.OPS:
            raise ops.EditError(f"Step {i}: '{name}' does not exist. Local: {', '.join(sorted(ops.OPS))}. "
                                f"AI: {', '.join(sorted(ai.AI_OPS))}.")
        clean.append({**st, "op": name})
    return clean


async def process(data: bytes, steps: list[dict], *, fmt: str = "", quality: int = 92, compress_kb: float | None = None,
                  tenant: str = "", filename: str = "", fallback_local: bool = True) -> dict[str, Any]:
    steps = validate(steps, filename)
    im = await asyncio.to_thread(ops.load, data)
    start = im.size
    report: list[dict] = []
    notes: list[str] = []
    engines: list[str] = []
    ai_used = False
    run: list[dict] = []

    async def flush():
        nonlocal im, run
        if run:
            im, rep = await asyncio.to_thread(ops.run, im, run)
            report.extend(rep)
            run = []

    for st in steps:
        if st["op"] in ai.AI_OPS:
            await flush()
            before = im.size
            try:
                res = await ai.run_op(st["op"], im, st, tenant=tenant, filename=filename)
            except ai.NoEngine:
                if st["op"] == "upscale" and fallback_local:
                    im = await asyncio.to_thread(ops.op_upscale_local, im, st.get("factor", 2))
                    report.append({"op": "upscale", "from": f"{before[0]}x{before[1]}", "to": f"{im.width}x{im.height}",
                                   "engine": "local enlargement (no AI engine set)"})
                    notes.append("No AI upscaler was set up: the photo was only enlarged (Lanczos), no new detail was added.")
                    continue
                raise
            im = res["image"]
            if res.get("label") and not res.get("labelled"):          # generative zoo output gets the AI corner label
                from .. import photogen
                im = Image.open(io.BytesIO(await asyncio.to_thread(photogen.label, ai._png(im)))).convert("RGB")
            ai_used = True
            engines.append(res["engine"])
            report.append({"op": st["op"], "from": f"{before[0]}x{before[1]}", "to": f"{im.width}x{im.height}",
                           "engine": res["engine"]})
            if res.get("note"):
                notes.append(res["note"])
        else:
            run.append(st)
    await flush()
    out, ext = await asyncio.to_thread(ops.encode, im, fmt, quality, compress_kb)
    return {"bytes": out, "ext": ext, "size_in": f"{start[0]}x{start[1]}", "size_out": f"{im.width}x{im.height}",
            "kb_out": round(len(out) / 1024, 1), "report": report, "engines": engines, "ai": ai_used, "notes": notes,
            "image": im}
