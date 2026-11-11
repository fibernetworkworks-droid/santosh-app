"""v0.814 APP ENGINE 1 - ONE tool, `app_engine`, for the React apps of the Web Studio (L8 of LOVABLE_STUDIO_PLAN.md).

The plan's tool set (5.3) as actions of one tool: view / search / edit_lines / write / rename / delete /
add_dependency / logs / build, plus create / list / status / tokens / check. Every write goes through
appengine/rules.py (paths, safety, design drift): a refused write changes nothing and names the line and the fix.
Going live is NOT here - it is her tap in the Studio. In Plan / Chat mode only the reading actions run."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

READS = {"list", "status", "view", "search", "logs", "files", "check", "cloud", "cloud_rows"}
CHANGES = {"create", "write", "edit_lines", "rename", "delete", "add_dependency", "tokens", "build", "cloud_change"}

APPENGINE_TOOLS = [
    {"name": "app_engine", "description": (
        "[APP ENGINE] Real React apps (React 18 + TypeScript + Vite + Tailwind v4) built in Hoola's locked box - for "
        "web APPS with screens, forms, lists, dashboards (a brochure website stays with the `website` tool). Work "
        "like a careful engineer: action=view or search BEFORE you change a file; action=edit_lines for small exact "
        "changes (edits=[{search, replace, first_line?, last_line?}] - the search text must appear exactly once, in "
        "the line range if given; a line that is just '...' inside search skips a long middle; line numbers are the "
        "ORIGINAL file's, so several edits from one view are fine); action=write for a new file or a full rewrite; "
        "rename / delete; add_dependency only from the vetted list; tokens to change colours / corners / fonts "
        "(values {bg, surface, ink, primary, accent, radius, head, body} as #rrggbb / number / sans|serif|rounded|mono, "
        "or palette calm|warm|fresh|bold|night). RULES the tool enforces: colours only as tokens (bg-bg bg-surface "
        "bg-primary text-ink text-muted text-primary border-line ...), never a hex / rgb colour, a Tailwind palette "
        "colour (bg-blue-500, text-white) or a one-off [value]; no outside address (no fetch to http...; data will come "
        "through src/lib/hoola.ts, not connected yet - keep sample data on the page and say it is sample); pages in "
        "src/pages, routes in src/App.tsx, shared parts in src/components (the ui kit: button card input textarea "
        "label badge tabs dialog table). Your changes are built (and shown to her) only when your turn ends or you call "
        "action=build - so finish the whole change set, then call action=build and read its answer before you say it is "
        "done; a failed build names file and line, and action=logs also lists errors the preview itself reported (with "
        "the app's file and line). When she selected a part, her message names its file:line - view that line first. "
        "Going live is HER tap in the Studio - never claim it is live. `app` = the app's id or number (the Studio "
        "turn already names it). HOOLA CLOUD (saved data + sign-in): action=cloud shows its lists, rules in plain words and "
        "the rule audit; action=cloud_change changes=[...] applies changes as ONE run - ops: add_list {key, label, fields: "
        "[{key, label, type: text|long_text|number|phone|email|date|choice|yes_no|url, required, options, admin_only, "
        "private}], rules: {create: public|member|admin, read: public|members|own|admin, update: own|admin, delete: "
        "own|admin}, samples}, add_field {list, ...field}, add_option {list, field, option}, hide_field / show_field "
        "{list, field}, hide_list / show_list {list}, label {list, field?, label}, rules {list, create?, read?, update?, "
        "delete?}, signup {on}. Only ADDITIVE changes: drop / rename / type change / remove_option are never done by you "
        "(they wait for her 'I accept data loss' tap; use hide + add instead). Personal data (email, phone, name, address) "
        "is never readable by anyone on the internet unless she said so (then confirm_public: true). The app uses it ONLY "
        "via src/lib/hoola.ts: hoola.db.collection(\"list\").list() / create / update / remove, hoola.auth.signUp / "
        "signIn / signOut / me / onChange; every rule is checked on the server. action=cloud_rows {list} reads the PREVIEW "
        "(sample) data only - her visitors' live data is never read by you."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": sorted(READS | CHANGES)},
         "app": {"type": "string", "description": "the app id or number (default: the app this Studio chat is about)"},
         "name": {"type": "string", "description": "create: the app's name"},
         "brief": {"type": "string", "description": "create: what she asked for, in her words"},
         "palette": {"type": "string", "enum": ["calm", "warm", "fresh", "bold", "night"]},
         "values": {"type": "object", "description": "tokens: {bg, surface, ink, primary, accent: #rrggbb, radius: number, head, body}"},
         "path": {"type": "string", "description": "a file, e.g. src/pages/Home.tsx"},
         "to": {"type": "string", "description": "rename: the new path"},
         "code": {"type": "string", "description": "write: the whole file"},
         "edits": {"type": "array", "items": {"type": "object", "properties": {
             "search": {"type": "string"}, "replace": {"type": "string"},
             "first_line": {"type": "integer"}, "last_line": {"type": "integer"}}, "required": ["search", "replace"]}},
         "from_line": {"type": "integer"}, "to_line": {"type": "integer"},
         "query": {"type": "string", "description": "search: text to find"},
         "package": {"type": "string", "description": "add_dependency: a vetted package name"},
         "changes": {"type": "array", "items": {"type": "object"}, "description": "cloud_change: the Hoola Cloud changes, applied as one run"},
         "list": {"type": "string", "description": "cloud_rows: the list to read (preview data)"}},
         "required": ["action"]}},
]

APPENGINE_LABELS = {"app_engine": "Working on the app"}


def _default_app(app: str) -> str:
    if app:
        return str(app)
    from . import turnmode as TM
    a = TM.APP.get()
    if not a:
        raise ToolError("Which app? Give app=<id or number> (action=list shows them).")
    return a


def _call(ctx: Ctx, action: str, app: str, kw: dict[str, Any]) -> dict[str, Any]:
    from ..appengine import service as AE
    from ..config import get_settings
    if not getattr(get_settings(), "app_engine", True):
        raise ToolError("The App Engine is switched off on this server.")
    t = ctx.tenant_id
    if action == "list":
        return {"apps": AE.list_(t)}
    if action == "status":
        return AE.status()
    if action == "create":
        from . import turnmode as TM
        conv = ctx.conversation_id if TM.APP.get() == "" else ""
        return AE.create(t, kw.get("name") or "", kw.get("brief") or "", kw.get("palette") or "",
                         kw.get("values") or None, conversation_id=conv)
    a = _default_app(app)
    if action == "files":
        r = AE._load(t, a)
        return {"files": AE.files_list(r)}
    if action == "view":
        return AE.read_file(t, a, kw.get("path") or "", kw.get("from_line") or 0, kw.get("to_line") or 0)
    if action == "search":
        return AE.search(t, a, kw.get("query") or "")
    if action == "logs":
        return AE.logs(t, a)
    if action == "check":
        return AE.check_all(AE._load(t, a))
    if action == "write":
        return AE.write(t, a, kw.get("path") or "", kw.get("code") or "")
    if action == "edit_lines":
        return AE.edit_lines(t, a, kw.get("path") or "", kw.get("edits") or [])
    if action == "rename":
        return AE.rename(t, a, kw.get("path") or "", kw.get("to") or "")
    if action == "delete":
        return AE.delete(t, a, kw.get("path") or "")
    if action == "add_dependency":
        return AE.add_dependency(t, a, kw.get("package") or "")
    if action == "tokens":
        return AE.set_tokens(t, a, kw.get("values") or {}, kw.get("palette") or "")
    if action == "build":
        return AE.wait_build(t, a)
    if action in ("cloud", "cloud_rows", "cloud_change"):
        from ..appengine import cloud as CL
        r = AE._load(t, a)
        try:
            if action == "cloud":
                o = CL.overview(r)
                return {k: o[k] for k in ("schema", "audit", "pending", "datasets", "not_built")}
            if action == "cloud_rows":
                return {"dataset": "preview", "rows": CL.owner_rows(r, "preview", kw.get("list") or "", 50)}
            return CL.apply_changes(r, kw.get("changes") or [], "hoola")
        except CL.CloudError as e:
            if action == "cloud_change" and isinstance(e.data, dict) and e.data.get("destructive"):
                CL.queue_pending(r, e.data["destructive"])
                raise ToolError(str(e) + " The data-loss card is now waiting in the Studio's Cloud tab; tell her what it "
                                "would delete and that it is her choice.")
            raise ToolError(str(e))
    raise ToolError(f"Unknown action '{action}'.")


async def app_engine(ctx: Ctx, action: str, app: str = "", **kw: Any) -> dict:
    from ..appengine import service as AE
    from . import turnmode as TM
    action = str(action or "").strip().lower()
    if action in ("publish", "go_live", "unpublish"):
        raise ToolError("Going live is her tap in the Studio (App > Publish), never this tool. Tell her the version is "
                        "ready and where the button is.")
    if action in CHANGES and TM.MODE.get() in ("plan", "chat"):
        TM.STATS["refused"] += 1
        raise ToolError(TM.refusal(f"app_engine action={action}"))
    if action in CHANGES and ctx.actor not in ("owner",) and not str(ctx.actor).startswith("approved:"):
        raise ToolError("Only the owner's own turns change an app.")
    tok = AE.TURN_CONV.set(ctx.conversation_id or "")       # v0.825 the HMR gate: this turn's writes wait for its end
    try:
        return await asyncio.to_thread(_call, ctx, action, app, kw)
    except AE.AppEngineError as e:
        raise ToolError(str(e))
    finally:
        AE.TURN_CONV.reset(tok)


APPENGINE_HANDLERS = {"app_engine": app_engine}
