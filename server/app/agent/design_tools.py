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
        "she shares it (the tool never makes a public link: she taps Share in the editor) | to_app (file, nodes = frame ids or "
        "names - left out = every phone-size frame, app? = an App Studio app id / number, brief? = what a NEW app is for) "
        "-> hands those frames to App Studio as the design of the matching screens (structure only from here; the pictures "
        "come when she sends from the editor); never approves, builds or publishes - her OK stays in App Studio | import_figma (url "
        "= her Figma design file link) -> starts importing that Figma file into a NEW Hoola Design file through HER saved "
        "Figma token and answers the job + where she watches it; never takes a token (she saves it herself in Hoola "
        "Design > Import from Figma, never in chat) | to_site (file, node = ONE frame id or name, site? = a "
        "Web Studio site id / number to add it to - left out = a NEW website, page? = that site's page slug, default home) -> "
        "the frame becomes clean responsive HTML + CSS in Web Studio through Web Studio's own checks and a checked version; "
        "never publishes - going live stays her tap in Web Studio | templates (q?, category?) -> the template gallery "
        "(posters, festival greetings, social posts, cards, invitations, menus, app screens, slides...) and her own saved "
        "templates | use_template (template = its id or name, name?) -> a NEW file in her files from that template + its link | "
        "make_plugin (prompt = what the plugin should do) -> a Hoola Design plugin DRAFT (manifest + code, statically checked, "
        "smallest permissions) for her to review; it is NEVER installed here - installing is her Install in the editor's review "
        "dialog. Presets: phone 390x844, "
        "android 360x800, web 1440, instagram 1080x1080, story / whatsapp 1080x1920, poster (A4), card (business "
        "card), slide 1920x1080, logo; leave it out and the words decide. Facts nobody gave (a price, a phone number, "
        "an address) come out as marked [blanks] - never invent them in the prompt either. The answer is a LINK to "
        "the editor, not a picture (there is no server-side render): give her the link. NOT for: a finished picture "
        "or photo from words (photo_banao), editing her photo (image_edit), a branded poster PNG from her Brand kit "
        "(brand), a real website she can publish (website), a PDF / Word / PPT document (doc_studio), a video."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["create", "list", "add", "share", "to_app", "import_figma", "to_site",
                                                    "templates", "use_template", "make_plugin"]},
         "prompt": {"type": "string", "description": "What to design, in her words (create / add). Up to 2000 characters."},
         "name": {"type": "string", "description": "Name of the new file (create). Left out = taken from the prompt."},
         "file": {"type": "string", "description": "File id (df_...) or its name (add / share)."},
         "preset": {"type": "string", "enum": list(PRESETS)},
         "q": {"type": "string", "description": "Search her files by name (list)."},
         "nodes": {"type": "array", "items": {"type": "string"},
                   "description": "to_app: the frames (ids or names) that are screens of the app."},
         "app": {"type": "string", "description": "to_app: an existing App Studio app (id or number like A-0001); "
                                                  "left out = a new app plan."},
         "brief": {"type": "string", "description": "to_app with no app: what the new app is for, in her words."},
         "url": {"type": "string", "description": "import_figma: the link of her Figma design file (figma.com/design/...)."},
         "node": {"type": "string", "description": "to_site: the ONE frame (id or name) to send to Web Studio."},
         "site": {"type": "string", "description": "to_site: an existing Web Studio site (id or number like S-0001); "
                                                   "left out = a new website."},
         "page": {"type": "string", "description": "to_site with a site: the page slug to add the section to (default home)."},
         "template": {"type": "string", "description": "use_template: the template's id (from action=templates) or its name."},
         "category": {"type": "string", "description": "templates: one category, e.g. Festivals, Social media, App screens."},
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
    if action == "to_app":                             # D7 bridge C: design -> App Studio (design/toapp.py)
        from ..design import toapp
        from ..design.room import HUB
        file = await asyncio.to_thread(_find, tenant, str(a.get("file") or ""))
        got = await HUB.read(file["id"], tenant)
        if got is None:
            raise ToolError("That design file could not be read.")
        refs = [str(x) for x in a.get("nodes") or []] if isinstance(a.get("nodes"), list) else []
        try:
            ids = await asyncio.to_thread(toapp.frames_by_name, got[1], refs)
            out = await asyncio.to_thread(toapp.send, tenant, file, got[1], ids, str(a.get("app") or "").strip(),
                                          str(a.get("brief") or "")[:600], None, ctx.conversation_id or "")
        except toapp.BridgeError as e:
            raise ToolError(str(e)) from None
        from ..config import get_settings
        base = str(getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
        return {"status": "sent", "app": out["app"], "url": base + out["url"], "say": out["say"],
                "screens": [{"frame": s["name"], "screen": s["screen"], "label": s["label"], "state": s["state"],
                             "size": s["size_class"]} for s in out["screens"]],
                "warnings": [w for w in out["warnings"] if not w.startswith("No pictures came")],
                "pictures_note": "Structure only from the chat: the picture of each frame comes when she sends it from the "
                                 "editor (select the frames > Send to App Studio). App Studio reads the structure either way.",
                "note": "Nothing is approved, built or published: the screens wait for HER OK in App Studio (Approve design)."}
    if action == "import_figma":                       # D7 bridge A: Figma import (design/figma.py)
        from ..design import figma
        if any(k in a for k in ("token", "figma_token", "key", "pat")) or re.search(r"\bfig[a-z]_[A-Za-z0-9_\-]{20,}", str(a.get("url") or "")):
            raise ToolError("A Figma token is never taken in chat. She saves it herself in Hoola Design > Import from Figma "
                            "(stored sealed); if she pasted one in the chat, tell her to make a new one in Figma and delete the old.")
        try:
            job = await figma.start(tenant, str(a.get("url") or ""), str(a.get("name") or ""))
        except figma.FigmaError as e:
            raise ToolError(str(e)) from None
        base = link_of("").rsplit("#", 1)[0]
        return {"status": "started", "job": job["id"], "watch": base + "#/import/" + job["id"],
                "note": "The import runs in the background. Give her the watch link: it shows the progress and opens the new "
                        "file when it is done (it also appears in her Hoola Design files). Figma is only read, never changed."}
    if action == "to_site":                            # D7 bridge B: design -> Web Studio (design/toweb.py)
        from ..design import toweb
        from ..design.doc import loads
        from ..design.room import HUB
        _gate_actor(ctx)
        file = await asyncio.to_thread(_find, tenant, str(a.get("file") or ""))
        got = await HUB.read(file["id"], tenant)
        if got is None:
            raise ToolError("That design file could not be read.")
        doc = await asyncio.to_thread(loads, got[1])
        try:
            node = await asyncio.to_thread(toweb.frame_by_name, doc, str(a.get("node") or ""))
            body = {"node": node, "site": str(a.get("site") or "").strip(), "page": str(a.get("page") or "").strip(),
                    "mode": "section" if str(a.get("site") or "").strip() else "new", "brief": str(a.get("brief") or "")[:600]}
            out = await asyncio.to_thread(toweb.send, tenant, file, doc, body)
        except toweb.ToWebError as e:
            raise ToolError(str(e)) from None
        from ..config import get_settings
        base = str(getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
        return {"status": "sent", "site": out["site"], "number": out["number"], "page": out["page"], "url": base + out["url"],
                "warnings": out["warnings"], "say": out["say"],
                "note": "Give her the Web Studio link. Nothing is published: going live stays her tap in Web Studio."}
    if action in ("templates", "use_template", "make_plugin"):           # D8b (design/gallery.py, design/plugin_ai.py)
        return await _d8b(ctx, action, a)
    if action not in ("create", "add"):
        raise ToolError(f"hoola_design has no action '{action}': create | list | add | share | to_app | import_figma | to_site | "
                        "templates | use_template | make_plugin.")
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


async def _d8b(ctx: Ctx, action: str, a: dict) -> dict[str, Any]:
    """templates | use_template | make_plugin: the gallery, a new file from a template, a plugin draft (never installed)."""
    from ..design import ai, gallery, plugin_ai
    tenant = ctx.tenant_id
    if action == "templates":
        got = await asyncio.to_thread(gallery.listing, tenant, str(a.get("q") or ""), str(a.get("category") or ""))
        row = lambda t: {"template": t["id"], "name": t["name"], "category": t["category"],                 # noqa: E731
                         "size": f"{int(t.get('w') or 0)} x {int(t.get('h') or 0)}"}
        return {"templates": [row(t) for t in got["templates"]], "mine": [row(t) for t in got["mine"]],
                "categories": got["categories"], "open_gallery": link_of("").rsplit("#", 1)[0] + "#/",
                "note": "Offer her the ones that fit; action=use_template makes a NEW file from one (her files are never "
                        "changed). Every [blank] in a template is a fact only she knows."}
    if action == "use_template":
        ref = str(a.get("template") or "").strip()
        if not ref:
            raise ToolError("Which template? Give its id or name; action=templates lists them.")
        got = await asyncio.to_thread(gallery.listing, tenant, "", "")
        rows = got["templates"] + got["mine"]
        hit = next((t for t in rows if t["id"] == ref), None) or next((t for t in rows if t["name"].lower() == ref.lower()), None)
        if hit is None:
            close = [t for t in rows if ref.lower() in t["name"].lower()]
            if len(close) != 1:
                raise ToolError(f"No single template matches '{ref[:60]}'. action=templates lists them"
                                + (": " + "; ".join(f"{t['name']} ({t['id']})" for t in close[:6]) if close else "."))
            hit = close[0]
        _gate_actor(ctx)
        f = await asyncio.to_thread(gallery.use, tenant, hit["id"], str(a.get("name") or "")[:120])
        return {"status": "done", "file_id": f["id"], "name": f["name"], "template": hit["name"], "link": link_of(f["id"]),
                "preview": None, "note": "A NEW file in her files, made from the template; give her the link. Every [blank] "
                                         "(phone number, price, date, address ...) is hers to fill - never fill them in yourself."}
    _gate_actor(ctx)
    try:
        d = await plugin_ai.draft(a.get("prompt"), tenant)
    except ai.AiError as e:
        raise ToolError(str(e)) from None
    m = d["manifest"]
    return {"status": "draft", "installed": False, "name": m["name"], "description": m["description"],
            "permissions": d["permissions"], "manifest": m, "code": d["code"], "notes": d["notes"],
            "note": "This is a DRAFT for her review; it is NOT installed and you can not install it. Tell her in plain words "
                    "what it does and what it asks for. To use it she opens Hoola Design > Ask Hoola to make a plugin (main menu) "
                    "and asks there - the editor shows the code and every permission and only her Install installs it."}


DESIGN_HANDLERS = {"hoola_design": hoola_design}
