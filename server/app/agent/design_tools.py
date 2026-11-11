"""Tool `hoola_design`: Hoola Design (her own design editor, /console/design) from the chat. ONE tool, four actions:
create (a new design file from one line), list (her files), add (more frames into a file), share (how she shares it).

The design itself is made by app/design/ai.py: the model only writes a validated spec, code lays it out, checks the
contrast of every text and applies the ops THROUGH the file's room - so an editor she has open sees it appear.
There is no server-side renderer, so this tool returns a LINK, never a picture (said in every answer).
A share link is a PUBLIC change: the tool never makes one. She taps Share in the editor herself."""
from __future__ import annotations

import asyncio
import re
from typing import Any

from .tools import Ctx, ToolError

PRESETS = ("phone", "android", "web", "instagram", "story", "whatsapp", "poster", "card", "slide", "logo")

DESIGN_TOOLS = [
    {"name": "hoola_design", "description": (
        "HOOLA DESIGN, her own design editor (like Figma, at /console/design): make an EDITABLE design file - a UI "
        "screen or app mockup, a wireframe, a web page layout, a poster / social post / story layout, a business "
        "card, a slide, a logo lockup - as real layers she can open and change, with auto layout. Actions: create "
        "(prompt = what to design in her own words, name?, preset?) -> a new file + its link | list (q?) -> her "
        "design files | add (file = id or name, prompt, preset?) -> more frames in that file | share (file) -> how "
        "she shares it (the tool never makes a public link: she taps Share in the editor). Presets: phone 390x844, "
        "android 360x800, web 1440, instagram 1080x1080, story / whatsapp 1080x1920, poster (A4), card (business "
        "card), slide 1920x1080, logo; leave it out and the words decide. Facts nobody gave (a price, a phone number, "
        "an address) come out as marked [blanks] - never invent them in the prompt either. The answer is a LINK to "
        "the editor, not a picture (there is no server-side render): give her the link. NOT for: a finished picture "
        "or photo from words (photo_banao), editing her photo (image_edit), a branded poster PNG from her Brand kit "
        "(brand), a real website she can publish (website), a PDF / Word / PPT document (doc_studio), a video."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["create", "list", "add", "share"]},
         "prompt": {"type": "string", "description": "What to design, in her words (create / add). Up to 2000 characters."},
         "name": {"type": "string", "description": "Name of the new file (create). Left out = taken from the prompt."},
         "file": {"type": "string", "description": "File id (df_...) or its name (add / share)."},
         "preset": {"type": "string", "enum": list(PRESETS)},
         "q": {"type": "string", "description": "Search her files by name (list)."},
     }, "required": ["action"]}},
]
DESIGN_LABELS = {"hoola_design": "Designing in Hoola Design"}


def link_of(file_id: str) -> str:
    from ..config import get_settings
    base = str(getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
    return f"{base}/console/design#/f/{file_id}"


def _on() -> None:
    from ..config import get_settings
    st = get_settings()
    if not getattr(st, "design_page", False):
        raise ToolError("Hoola Design is switched off on this server.")


def _gate_actor(ctx: Ctx) -> None:
    from .. import usage
    if not str(getattr(ctx, "actor", "owner") or "owner").startswith(("owner", "approved", "goal")):
        if not usage.allowed(ctx.tenant_id, "routine"):
            raise ToolError(usage.blocked_text(ctx.tenant_id))


def _title(prompt: str) -> str:
    from ..design import templates
    head, about = templates.subject(prompt)
    words = (head or about or re.sub(r"\s+", " ", prompt).strip())[:60].strip()
    return words or "Untitled"


def _find(tenant: str, ref: str) -> dict:
    """Her file by id, else by name (one clear match)."""
    from ..design import store
    ref = str(ref or "").strip()
    if not ref:
        raise ToolError("Which design file? Give its id (df_...) or its name; action=list shows her files.")
    got = store.get_file(tenant, ref)
    if got and not got.get("trashed"):
        return got
    rows = store.list_files(tenant, ref)
    exact = [r for r in rows if r["name"].strip().lower() == ref.lower()]
    rows = exact or rows
    if len(rows) == 1:
        return store.get_file(tenant, rows[0]["id"]) or rows[0]
    if not rows:
        raise ToolError(f"No design file called '{ref[:60]}'. action=list shows her files.")
    raise ToolError("More than one design file matches: " + "; ".join(f"{r['name']} ({r['id']})" for r in rows[:6])
                    + ". Ask her which one, then pass its id.")


def _result(file: dict, out: dict) -> dict[str, Any]:
    frames = [f"{f.get('name') or 'Frame'} ({int(f.get('w') or 0)} x {int(f.get('h') or 0)})" for f in out.get("frames", [])]
    res: dict[str, Any] = {"status": "done", "file_id": file["id"], "name": file["name"], "link": link_of(file["id"]),
                           "engine": out.get("engine"), "frames": frames, "layers": out.get("nodes"),
                           "preview": None, "preview_note": "No picture: this server has no renderer for design files. "
                                                            "She sees the design by opening the link."}
    if out.get("engine") == "template":
        res["note"] = ("No AI model is configured on this server, so this is one of Hoola's BUILT-IN layouts filled from her "
                       "words - say that plainly, do not call it a custom design. Every [blank] is a fact only she knows.")
    else:
        res["note"] = ("Give her the link in one line and say what is in the file. Facts nobody gave are marked [blanks] "
                       "for her to fill in; she can change anything in the editor or ask for changes there (Ask Hoola).")
    if out.get("notes"):
        res["design_notes"] = out["notes"]
    if out.get("blanked"):
        res["blanked"] = out["blanked"]
    if out.get("contrast_fixed"):
        res["contrast_fixed"] = out["contrast_fixed"]
    return res


async def hoola_design(ctx: Ctx, action: str = "list", **a: Any):
    from ..design import ai, store
    from ..design.doc import dumps_nodes, new_document
    action = (action or "list").strip().lower()
    _on()
    tenant = ctx.tenant_id
    if action == "list":
        rows = await asyncio.to_thread(store.list_files, tenant, str(a.get("q") or ""))
        return {"files": [{"file_id": r["id"], "name": r["name"], "updated_at": r["updated_at"], "layers": r["nodes"],
                           "link": link_of(r["id"])} for r in rows[:30]],
                "total": len(rows), "open_all": link_of("").rsplit("#", 1)[0]}
    if action == "share":
        file = await asyncio.to_thread(_find, tenant, str(a.get("file") or ""))
        share = file.get("share") or {}
        out: dict[str, Any] = {"file_id": file["id"], "name": file["name"], "link": link_of(file["id"])}
        if share.get("token") and share.get("role") == "view":
            base = link_of("").rsplit("#", 1)[0]
            out.update(status="already_shared", view_link=f"{base}#/s/{share['token']}",
                       note="She already switched a view-only link on for this file; this is that link. Switching it off is "
                            "hers too (Share in the editor).")
        else:
            out.update(status="her_tap", note=(
                "A share link is PUBLIC (anyone with it can view the file), so this tool does not make one. Tell her: "
                "open the file with the link, tap Share in the top bar and switch on 'Anyone with the link can view'; "
                "the editor then shows the link to copy. She can switch it off there any time."))
        return out
    if action not in ("create", "add"):
        raise ToolError(f"hoola_design has no action '{action}': create | list | add | share.")
    prompt = re.sub(r"[ \t]+", " ", str(a.get("prompt") or "")).strip()
    if not prompt:
        raise ToolError("prompt is missing: say in her words what to design (e.g. 'a home screen for a food delivery app').")
    if len(prompt) > ai.PROMPT_MAX:
        raise ToolError(f"The prompt is too long: keep it under {ai.PROMPT_MAX} characters.")
    preset = str(a.get("preset") or "").strip().lower()
    if preset and preset not in PRESETS:
        raise ToolError("preset is one of: " + ", ".join(PRESETS) + " (or leave it out).")
    _gate_actor(ctx)
    made = None
    if action == "create":
        nodes = new_document("")
        name = str(a.get("name") or "").strip() or _title(prompt)
        file = made = await asyncio.to_thread(store.create_file, tenant, name, dumps_nodes(nodes), len(nodes))
    else:
        file = await asyncio.to_thread(_find, tenant, str(a.get("file") or ""))
    try:
        out = await ai.design(tenant, file["id"], prompt, preset=preset, brand=True)
    except ai.AiError as e:
        if made is not None:                              # never leave an empty file behind a failed design
            await asyncio.to_thread(store.set_trashed, tenant, made["id"], True)
        raise ToolError(f"{e} (Nothing was made" + (", and the empty file was not kept" if made is not None else "") + ".)")
    return _result(file, out)


DESIGN_HANDLERS = {"hoola_design": hoola_design}
