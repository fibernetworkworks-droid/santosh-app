"""v0.129 photo_banao: make a picture from her words, or change her own photo with words (chat + calls)."""
from __future__ import annotations

import asyncio
import re

from ..events import bus
from .tools import Ctx, ToolError

PHOTO_TOOLS = [
    {"name": "photo_banao", "description": (
        "Make a NEW picture from her words, or CHANGE her own photo with words. action=make (prompt: what to draw - "
        "greeting, festival wish, poster idea, product on a nice background, illustration, logo idea; write a rich "
        "prompt in English with what / style / colours / mood and any words to show in the picture), action=edit "
        "(file_ids: 1-3 photos SHE attached; prompt: the change - 'background white karo', 'saree ka rang laal karo', "
        "'peeche ki cheezein hatao', 'ise cartoon jaisa banao'). aspect 1:1 | 4:5 (Insta post) | 9:16 (Status / story) | "
        "16:9 (YouTube / banner) | 3:4 | 4:3. quality fast (default, ~Rs 3) or best (~Rs 12, only when she asks for top "
        "quality). The picture comes back as her file with a card (save / share / change again) and carries an 'AI se "
        "bana' label. Refused: fake IDs / certificates / notes / bills made to look real, signatures / seals, nudity, "
        "face swaps, famous / public people, national emblems. For brand posters in her colours in every size use "
        "brand; for a passport photo id_photo; for just a white background on a product photo_clean is free."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["make", "edit"]}, "prompt": {"type": "string"},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "aspect": {"type": "string"}, "quality": {"type": "string", "enum": ["fast", "best"]},
         "filename": {"type": "string"}}, "required": ["action", "prompt"]}},
]
PHOTO_LABELS = {"photo_banao": "Photo bana raha hoon"}


async def photo_banao(ctx: Ctx, action="make", prompt="", file_ids=None, aspect="", quality="fast", filename="", **_):
    from .. import photogen, usage
    from .make_tools import _owner_bytes, _safe
    prompt = str(prompt or "").strip()
    ids = [str(x) for x in (file_ids or []) if str(x).strip()][:photogen.MAX_INPUTS]
    if action == "edit" and not ids:
        raise ToolError("Kaunsi photo badalni hai? Pehle photo bhejne ko kahiye (chat ka paperclip / call mein 'Photo "
                        "dikhaiye'), phir uska file_id do.")
    if not str(getattr(ctx, "actor", "owner") or "owner").startswith(("owner", "approved")):
        if not usage.allowed(ctx.tenant_id, "routine"):
            raise ToolError(usage.blocked_text(ctx.tenant_id))
    why = photogen.problem(prompt, edit=bool(ids))
    if why:
        raise ToolError(why + " (Dobara mat try karo; unhe yahi bata do.)")
    imgs = []
    for fid in ids:
        _, data = _owner_bytes(ctx, fid)
        imgs.append(data)
    try:
        res = await asyncio.to_thread(photogen.make, prompt, imgs, str(aspect or ""), str(quality or "fast"))
    except photogen.Refused as e:
        raise ToolError(str(e) + " (Dobara mat try karo.)")
    except photogen.PhotoError as e:
        raise ToolError(str(e))
    base = filename or re.sub(r"\s+", " ", prompt)[:40] or "Hoola photo"
    from ..mailbox import service as ms
    from ..pc.service import public_file
    row = ms.store_bytes(ctx.tenant_id, _safe(base, ".png"), res["png"], "to_phone")
    view = public_file(row)
    view.pop("pc_path", None)
    card = {**view, "prompt": prompt[:300], "quality": res["quality"], "aspect": res["aspect"], "edit": res["edit"],
            "model": res["model"], "from": ids, "label": photogen.LABEL}
    bus.publish(ctx.conversation_id, "photo_made", card)
    return {"status": "done", "file_id": view["file_id"], "name": view["name"], "aspect": res["aspect"],
            "quality": res["quality"], "about_inr": res["cost_inr"],
            "note": ("Photo ban gayi aur chat mein card ke saath dikh rahi hai (save / share / badlav). Use email / "
                     "hoola_send mein file_id se bhej sakte ho. Ek line mein batao kya bana; 'AI se bana' label laga hai.")}


PHOTO_HANDLERS = {"photo_banao": photo_banao}
