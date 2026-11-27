"""v0.999.232 ASK HOOLA IN THE ROUTE EDITOR: each route has its own chat beside the canvas.

The chat is a Conversation with kind 'route', kept out of her chat lists (callconv.not_call) like the desks' chats; what
she tells it still reaches her one memory. A turn in it gets the route's current steps as a block and the workflow
tools (family dhara) in view, so Hoola changes THIS route with dhara_save and the canvas redraws it.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from ..db import Conversation, Message, session

log = logging.getLogger("santosh.routechat")

KIND = "route"
FAMILIES = ["dhara"]
_OF: dict[str, tuple[str, str]] = {}      # conv -> (tenant, wf_id)
_GRAPH_CHARS = 18000


def _nice(name: str) -> str:
    return str(name or "").replace("_", " ")


def chat_for(tenant: str, wf: dict) -> dict[str, Any]:
    from . import editor as E
    cid = E.chat_of(tenant, wf["id"])
    if cid:
        with session() as s:
            c = s.get(Conversation, cid)
            if c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted:
                _OF[cid] = (tenant, wf["id"])
                return {"id": cid, "new": False}
    with session() as s:
        c = Conversation(tenant_id=tenant, kind=KIND, title=f"Route: {_nice(wf['name'])}"[:120])
        s.add(c)
        s.flush()
        cid = c.id
        hi = ("Tell me what this route should do, or what to change, and I'll draw it on the canvas. "
              "Nothing runs until you switch it on.")
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False,
                      delivered_to_agent=True))
    E.set_chat(tenant, wf["id"], cid)
    _OF[cid] = (tenant, wf["id"])
    return {"id": cid, "new": True}


def _route_of(conv: str) -> tuple[str, str]:
    if not conv:
        return "", ""
    if conv in _OF:
        return _OF[conv]
    tenant, wf_id = "", ""
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None and (c.kind or "") == "call" and c.origin_conv:
                c = s.get(Conversation, c.origin_conv)
            if c is not None and (c.kind or "") == KIND:
                tenant = c.tenant_id
                cid = c.id
        if tenant:
            from . import editor as E
            wf_id = E.route_of_chat(tenant, cid)
    except Exception:   # noqa: BLE001
        log.exception("route chat read failed")
        return "", ""
    _OF[conv] = (tenant, wf_id)
    return tenant, wf_id


def is_route(conv: str) -> bool:
    return bool(_route_of(conv)[1])


RULES = ("You are Hoola, working inside the Hoola Route editor beside one of her routes (a saved automation). She sees "
         "the route drawn on a canvas and every change you save appears there at once. To change it, call dhara_save "
         "with name exactly \"{name}\" and the WHOLE route: every step she did not ask to change stays exactly as it is "
         "(same ids, same settings). Keep step ids stable and give every step a short label in plain words (label: "
         "'Add the order to my sheet'). If the route is only the placeholder step 'Tell me it ran', replace it with the "
         "real steps she asks for. Use her own connected apps (tool steps); put an approval step before anything that "
         "sends money, writes to many people or deletes. Do not switch the route on and do not run it unless she asks: "
         "it stays off until she switches it on, and she tests it with Test route. After saving, say in 1-3 short "
         "sentences what changed, by step label. If something you need is missing (which sheet, which number, which "
         "account), ask one short question instead of guessing. Shape data with data steps (sort, summarise, dates, files, "
         "text formats - see dhara_save) and write maths or functions inside {{ }} instead of a code step when you can. "
         "For flow use merge, a sub-route (run another route), stop, respond (the webhook's answer) and waits of up to 30 days "
         "or until a reply (wait for: call, with {{vars.resume_url}} sent in an earlier step). "
         "A route can start: by hand, on a schedule, from a webhook, on an app event (trigger event: a new email, sheet row, "
         "form answer, calendar event, Drive file, feed item, or any app's list through a tool that only reads - "
         "{{vars.event}}), from a Hoola form (trigger form, {{vars.form.<field>}}), from a Hoola chat (trigger chat, "
         "{{vars.message}}, reply with a respond step), when another route fails (trigger error), when another route runs "
         "it (trigger route) or as a tool for AI apps (trigger tool, needs a description). Change the trigger only when "
         "she asks for it. AI steps (type ai: write, summarise, classify, extract, sentiment, answer from her files, an agent "
         "with the tools she names) and a Switch where the AI picks the way are there for reading, sorting and writing text. Her variables are "
         "{{env.NAME}}; a web request signs in with a saved sign-in by its name (auth: 'NAME') - never ask her for a key or a "
         "password in the chat: she saves it under Sign-ins on the page. Every save is kept as a version she can bring back.")


def block(tenant: str, conv: str) -> str:
    from ..agent import dhara_tools as D
    _, wf_id = _route_of(conv)
    try:
        wf = D.get_workflow(tenant, wf_id=wf_id) if wf_id else None
        if wf is None:
            return "\n\n<route_editor>This route was deleted. Tell her, and offer to build a new one.</route_editor>"
        body = {"name": wf["name"], "trigger": wf.get("trigger_kind"), "trigger_spec": wf.get("trigger_spec") or {},
                "enabled": bool(wf.get("enabled")), "settings": wf.get("settings") or {}, "steps": wf.get("steps") or []}
        txt = json.dumps(D._masked(body), ensure_ascii=False)
        if len(txt) > _GRAPH_CHARS:
            txt = txt[:_GRAPH_CHARS] + " …(cut)"
        last = D.latest_run(tenant, wf["id"])
        run = (f"\nLast run: {last['status']}" + (f" - {str(last.get('error') or '')[:300]}" if last.get("error") else "")
               ) if last else "\nIt has not run yet."
        return f"\n\n<route_editor>{RULES.format(name=wf['name'])}\nThe route now: {txt}{run}</route_editor>"
    except Exception:   # noqa: BLE001
        log.exception("route block failed")
        return "\n\n<route_editor>The route could not be read just now.</route_editor>"


def stamp() -> float:
    return time.time()
