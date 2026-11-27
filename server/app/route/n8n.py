"""v0.999.248 HOOLA ROUTE R8: bring in an n8n workflow (the JSON n8n exports: Download / copy the nodes).

Own code; it reads n8n's published export shape (nodes + connections) and turns it into a Hoola route:
- the start (manual, schedule, webhook, form, chat, error, another route, app events) -> a Hoola trigger
- each node -> a Hoola step (web request, fields, if / switch / filter, wait, loop, merge, sort, limit,
  remove duplicates, split out, aggregate, respond, stop, sub-route, the AI nodes)
- n8n expressions ({{ $json.x }}, {{ $('Node').item.json.x }}, $env, $now) -> Hoola expressions
- anything Hoola cannot do the same way becomes a clearly named stop step (a placeholder), and the report says
  what came in, what to check and what to redo. JavaScript code is never run or translated.
The route lands switched OFF; nothing runs until she has read it and switched it on. Sign-ins are never
carried over (n8n exports leave them out) - she adds them under Sign-ins.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

BYTES_MAX = 1_000_000
NODES_MAX = 300
BASE, LC = "n8n-nodes-base.", "@n8n/n8n-nodes-langchain."

TRIGGERS = {"manualTrigger": "manual", "start": "manual", "scheduleTrigger": "schedule", "cron": "schedule",
            "interval": "schedule", "webhook": "webhook", "formTrigger": "form", "chatTrigger": "chat",
            "errorTrigger": "error", "executeWorkflowTrigger": "route", "rssFeedReadTrigger": "event",
            "gmailTrigger": "event", "googleSheetsTrigger": "event", "googleDriveTrigger": "event",
            "googleCalendarTrigger": "event", "mcpTrigger": "tool"}
SUB_NODE = re.compile(r"(lmChat|lmOpenAi|lm[A-Z]|memory|tool[A-Z]|toolWorkflow|embeddings|vectorStore|outputParser|"
                      r"textSplitter|document[A-Z]|retriever|reranker)")
OPS = {"equals": "eq", "equal": "eq", "notEquals": "ne", "notEqual": "ne", "contains": "contains",
       "notContains": "not_contains", "startsWith": "starts_with", "endsWith": "ends_with", "gt": "gt", "gte": "gte",
       "lt": "lt", "lte": "lte", "larger": "gt", "largerEqual": "gte", "smaller": "lt", "smallerEqual": "lte",
       "after": "gt", "afterOrEquals": "gte", "before": "lt", "beforeOrEquals": "lte", "exists": "exists",
       "notExists": "not_exists", "empty": "empty", "isEmpty": "empty", "notEmpty": "not_empty",
       "isNotEmpty": "not_empty", "regex": "matches", "true": "eq", "false": "eq", "notRegex": "",
       "lengthEquals": "", "lengthGt": "", "lengthLt": ""}
DAYNAMES = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class N8nError(ValueError):
    pass


def _slug(name: str, used: set, prefix: str = "step") -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")[:40] or prefix
    if not s[0].isalpha():
        s = prefix + "_" + s
    out, i = s, 2
    while out in used:
        out, i = f"{s}_{i}", i + 1
    used.add(out)
    return out


def _short(t: str) -> str:
    t = str(t or "")
    for p in (BASE, LC):
        if t.startswith(p):
            return t[len(p):]
    return t.rsplit(".", 1)[-1]


def _rl(v: Any) -> str:
    """n8n 'resource locator' values: {"__rl": true, "value": ..., "cachedResultName": ...}."""
    if isinstance(v, dict):
        return str(v.get("cachedResultName") or v.get("value") or "")
    return str(v or "")


def parse(raw: Any) -> dict:
    """The export as a dict - from the JSON text or an object; refuses what is not an n8n workflow."""
    if isinstance(raw, str):
        if len(raw.encode()) > BYTES_MAX:
            raise N8nError("The n8n file is too big (up to 1 MB)")
        try:
            raw = json.loads(raw)
        except ValueError:
            raise N8nError("That is not the JSON n8n exports (Download in n8n, or copy the nodes)")
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
        raw = raw[0]
    if not isinstance(raw, dict) or not isinstance(raw.get("nodes"), list):
        raise N8nError("That is not an n8n workflow: it has no nodes")
    if len(json.dumps(raw, default=str)) > BYTES_MAX:
        raise N8nError("The n8n file is too big (up to 1 MB)")
    if len(raw["nodes"]) > NODES_MAX:
        raise N8nError(f"Up to {NODES_MAX} nodes can be brought in at once")
    return raw


class _Conv:
    def __init__(self, doc: dict):
        self.doc = doc
        self.nodes: dict[str, dict] = {}
        for n in doc.get("nodes") or []:
            if isinstance(n, dict) and n.get("name"):
                self.nodes[str(n["name"])] = n
        self.out: dict[str, list[list[tuple[str, int]]]] = {}
        self.inc: dict[str, list[tuple[str, int, int]]] = {}
        self.ai_links: dict[str, list[str]] = {}
        for src, kinds in (doc.get("connections") or {}).items():
            if not isinstance(kinds, dict):
                continue
            for kind, outs in kinds.items():
                for oi, targets in enumerate(outs or []):
                    for t in targets or []:
                        if not isinstance(t, dict) or str(t.get("node")) not in self.nodes:
                            continue
                        tn, ti = str(t["node"]), int(t.get("index") or 0)
                        if kind == "main":
                            lst = self.out.setdefault(src, [])
                            while len(lst) <= oi:
                                lst.append([])
                            lst[oi].append((tn, ti))
                            self.inc.setdefault(tn, []).append((src, oi, ti))
                        else:
                            self.ai_links.setdefault(tn, []).append(src)
        self.subs = {x for lst in self.ai_links.values() for x in lst}
        self.used: set = set()
        self.ids: dict[str, str] = {}
        self.refs: dict[str, str] = {}
        self.form_names: dict[str, str] = {}
        self.chat = False
        self.done: set = set()
        # v0.999.264 WORKFLOW LIBRARY: n8n nodes that ADD a field to the item (dates, hashes, html picks) become
        # their own Hoola step; a later {{ $json.<that field> }} reads that step's output instead
        self.fieldmap: dict[tuple[str, str], str] = {}
        self.trig_app = ""
        self.textsrc: set = set()
        self.report: dict[str, list] = {"converted": [], "check": [], "placeholders": [], "skipped": [], "notes": []}

    # ------------------------------------------------------------------ helpers
    def sid(self, name: str) -> str:
        if name not in self.ids:
            self.ids[name] = _slug(name, self.used)
        return self.ids[name]

    def check(self, node: str, why: str) -> None:
        self.report["check"].append({"node": node, "why": why})

    def targets(self, name: str, i: int = 0) -> list[str]:
        outs = self.out.get(name) or []
        return [t for t, _ in outs[i]] if i < len(outs) else []

    def joins(self, name: str) -> bool:
        return len({s for s, _, _ in self.inc.get(name) or []}) > 1

    # ------------------------------------------------------------------ expressions
    def _path(self, ref: str, rest: str) -> str:
        """`.a.b` / `["a b"]` after an n8n reference -> Hoola dots (form labels and chat fields renamed)."""
        parts = re.findall(r"\s*\.\s*([A-Za-z_$][A-Za-z0-9_$]*)|\s*\[\s*['\"]([^'\"]+)['\"]\s*\]|\s*\[\s*(\d+)\s*\]", rest)
        out = ref
        first = True
        for a, b, c in parts:
            key = a or b
            if c:
                out += f"[{c}]"
                continue
            if first and (ref, key) in self.fieldmap:
                out, first = self.fieldmap[(ref, key)], False
                continue
            if first and ref == "vars.form" and key in self.form_names:
                key = self.form_names[key]
            if first and ref == "vars" and self.chat:
                key = {"chatInput": "message", "sessionId": "session"}.get(key, key)
            first = False
            out += "." + key if _ID.match(key) else f'["{key}"]'
        return out

    _REF = re.compile(
        r"""\$\(\s*['"]([^'"]+)['"]\s*\)\s*\.\s*(?:item|first\(\)|last\(\)|all\(\)(?:\[\d+\])?)\s*(?:\.\s*json)?"""
        r"""|\$node\s*\[\s*['"]([^'"]+)['"]\s*\]\s*\.\s*json"""
        r"""|\$items\(\s*['"]([^'"]+)['"]\s*\)"""
        r"""|\$input\s*\.\s*(?:item|first\(\)|last\(\)|all\(\))\s*(?:\.\s*json)?"""
        r"""|\$json|\$env|\$vars|\$now|\$today|\$execution|\$workflow|\$prevNode|\$runIndex|\$itemIndex""")
    _TAIL = re.compile(r"""^((?:\s*\.\s*[A-Za-z_$][A-Za-z0-9_$]*(?!\s*\()|\s*\[\s*(?:['"][^'"]+['"]|\d+)\s*\])*)""")

    def _inner(self, src: str, prev: str) -> str | None:
        """One {{ }} body -> Hoola, or None when it holds something Hoola's expressions cannot take."""
        from ..agent import dhara_data as DD
        out, i = [], 0
        for m in self._REF.finditer(src):
            out.append(src[i:m.start()])
            tok = m.group(0)
            tail = self._TAIL.match(src[m.end():]).group(1)
            end = m.end() + len(tail)
            node = m.group(1) or m.group(2) or m.group(3)
            if node:
                if node not in self.nodes:
                    return None
                base = self.refs.get(node) or f"steps.{self.sid(node)}.output"
                out.append(self._path(base, tail))
            elif tok.startswith("$input") or tok == "$json":
                out.append(self._path(prev, tail))
            elif tok in ("$env", "$vars"):
                out.append(self._path("env", tail))
            elif tok == "$now":
                out.append("now()")
                if tail:
                    return None
            elif tok == "$today":
                out.append("today()")
                if tail:
                    return None
            else:
                return None
            i = end
        out.append(src[i:])
        res = "".join(out).strip()
        if not res or DD.check(res):
            return None
        return res

    def expr(self, v: Any, prev: str, node: str = "") -> Any:
        if isinstance(v, dict):
            return {k: self.expr(x, prev, node) for k, x in v.items()}
        if isinstance(v, list):
            return [self.expr(x, prev, node) for x in v]
        if not isinstance(v, str):
            return v
        if not v.startswith("="):
            if not re.search(r"\{\{[^}]*\$", v):
                return v
            v = "=" + v
        body = v[1:]
        bad: list[str] = []

        def one(m: re.Match) -> str:
            got = self._inner(m.group(1), prev)
            if got is None:
                bad.append(m.group(1).strip()[:120])
                return "[n8n: " + m.group(1).strip()[:200] + "]"
            return "{{" + got + "}}"
        res = re.sub(r"\{\{(.*?)\}\}", one, body, flags=re.S)
        if bad and node:
            self.check(node, "This expression could not be brought in - write it again in Hoola: " + "; ".join(bad))
        return res

    # ------------------------------------------------------------------ the start
    def trigger(self) -> tuple[str, str, dict, dict]:
        """(node name, kind, spec, settings) of the start; the other starts are reported."""
        starts = [n for n in self.nodes.values() if _short(n.get("type")) in TRIGGERS
                  or (str(n.get("type") or "").endswith("Trigger") and not n.get("disabled"))]
        starts = [n for n in starts if not n.get("disabled")] or starts
        settings: dict[str, Any] = {}
        tz = (self.doc.get("settings") or {}).get("timezone")
        if tz and tz != "DEFAULT":
            settings["timezone"] = str(tz)
        if (self.doc.get("settings") or {}).get("errorWorkflow"):
            self.report["notes"].append("In n8n this workflow had an error workflow - pick the route to start when it "
                                        "fails in its Settings (When it fails)")
        if not starts:
            return "", "manual", {}, settings
        starts.sort(key=lambda n: (0 if _short(n.get("type")) in TRIGGERS else 1,
                                   (n.get("position") or [0, 0])[0] if isinstance(n.get("position"), list) else 0))
        main, rest = starts[0], starts[1:]
        for n in rest:
            self.report["skipped"].append({"node": n["name"], "why": "A Hoola route has one start; make another route "
                                           "for this one, or run it by hand"})
            self.done.add(n["name"])
        name, t, p = main["name"], _short(main.get("type")), main.get("parameters") or {}
        kind = TRIGGERS.get(t, "manual")
        spec: dict[str, Any] = {}
        self.refs[name] = "vars"
        self.done.add(name)
        if kind == "schedule":
            spec = self._schedule(name, t, p)
        elif kind == "webhook":
            self.report["notes"].append("It starts when data is sent to its address. Its n8n address does not move: "
                                        "make the new address on the route's page and give it to the sender")
            if str(p.get("httpMethod") or "GET").upper() == "GET":
                self.check(name, "The n8n webhook took GET; Hoola's address takes the data as POST JSON")
        elif kind == "form":
            fields = []
            for f in (p.get("formFields") or {}).get("values") or []:
                label = str(f.get("fieldLabel") or "field")
                nm = _slug(label, {x["name"] for x in fields} | {"form"}, "field")
                self.form_names[label] = nm
                typ = {"textarea": "textarea", "email": "email", "number": "number", "date": "date",
                       "dropdown": "select", "checkbox": "checkbox", "password": "text", "file": "text"}.get(
                    str(f.get("fieldType") or "text"), "text")
                d = {"name": nm, "label": label[:120], "type": typ, "required": bool(f.get("requiredField"))}
                if typ == "select":
                    d["options"] = [str(o.get("option")) for o in (f.get("fieldOptions") or {}).get("values") or []
                                    if o.get("option")][:50] or ["Yes", "No"]
                if str(f.get("fieldType")) == "file":
                    self.check(name, f"The form field '{label}' took a file in n8n; here it is a text field")
                fields.append(d)
            spec = {"title": str(p.get("formTitle") or self.doc.get("name") or "Form")[:120],
                    "fields": fields or [{"name": "message", "label": "Message", "type": "textarea", "required": True}]}
            if p.get("formDescription"):
                spec["intro"] = str(p["formDescription"])[:500]
            self.refs[name] = "vars.form"
        elif kind == "chat":
            self.chat = True
            if p.get("initialMessages"):
                spec = {"greeting": str(p["initialMessages"])[:500]}
        elif kind == "error":
            self.check(name, "The error start gives the failed route, run and error ({{vars.failed_route}}, "
                             "{{vars.error}}) - n8n's execution fields are named differently")
        elif kind == "route":
            self.report["notes"].append("It starts when another route runs it (a sub-route step)")
        elif kind == "tool":
            self.report["notes"].append("It is offered to AI apps as a tool (Hoola's MCP address)")
        elif kind == "event":
            spec = self._event(name, t, p)
            self.refs[name] = "vars.event"
        if t not in TRIGGERS:
            kind, spec = "manual", {}
            self.report["placeholders"].append({"node": name, "type": t, "why": "This start is not one Hoola has - it "
                                                "starts by hand until you pick what starts it"})
        else:
            self.report["converted"].append({"node": name, "type": t, "as": "start: " + kind})
        return name, kind, spec, settings

    def _schedule(self, name: str, t: str, p: dict) -> dict:
        if t != "scheduleTrigger":
            self.check(name, "An older n8n timer: check when it runs")
            return {"every_hours": 1}
        ivs = (p.get("rule") or {}).get("interval") or [{}]
        if len(ivs) > 1:
            self.check(name, "n8n had several times; only the first came in - add the others in What starts it")
        iv = ivs[0] or {}
        field = str(iv.get("field") or "days")
        hm = f"{int(iv.get('triggerAtHour') or 0):02d}:{int(iv.get('triggerAtMinute') or 0):02d}"
        if field in ("seconds", "minutes"):
            n = int(iv.get("minutesInterval") or 1) if field == "minutes" else 1
            if n < 15:
                self.check(name, f"It ran every {n} {field[:-1] if n == 1 else field} in n8n; the fastest a Hoola "
                                 "schedule runs is every 15 minutes")
            return {"every_minutes": max(15, n)}
        if field == "hours":
            return {"every_hours": max(1, int(iv.get("hoursInterval") or 1))}
        if field == "days":
            if int(iv.get("daysInterval") or 1) > 1:
                self.check(name, "It ran every few days in n8n; here it runs every day at that time")
            return {"at": [hm]}
        if field == "weeks":
            days = iv.get("triggerAtDay") or [1]
            return {"days": [DAYNAMES[int(d) % 7] for d in (days if isinstance(days, list) else [days])], "at": [hm]}
        if field == "months":
            return {"monthdays": [max(1, min(int(iv.get("triggerAtDayOfMonth") or 1), 31))], "at": [hm]}
        if field == "cronExpression":
            got = self._cron(str(iv.get("expression") or ""))
            if got:
                return got
            self.check(name, f"The cron time '{iv.get('expression')}' could not be read - set when it runs")
            return {"every_hours": 1}
        return {"at": [hm]}

    @staticmethod
    def _cron(e: str) -> dict | None:
        f = e.split()
        if len(f) == 6:
            f = f[1:]
        if len(f) != 5:
            return None
        mi, hr, dom, mon, dow = f
        if mon != "*":
            return None
        if re.fullmatch(r"\*/(\d+)", mi) and hr == "*" and dom == "*" and dow == "*":
            return {"every_minutes": max(15, int(mi[2:]))}
        if mi.isdigit() and re.fullmatch(r"\*/(\d+)|\*", hr) and dom == "*" and dow == "*":
            return {"every_hours": int(hr[2:]) if "/" in hr else 1}
        if not mi.isdigit() or not re.fullmatch(r"\d+(,\d+)*", hr):
            return None
        out: dict[str, Any] = {"at": [f"{int(h):02d}:{int(mi):02d}" for h in hr.split(",")]}
        if dow != "*":
            if not re.fullmatch(r"\d(,\d)*", dow):
                return None
            out["days"] = [DAYNAMES[int(d) % 7] for d in dow.split(",")]
        if dom != "*":
            if not re.fullmatch(r"\d+(,\d+)*", dom):
                return None
            out["monthdays"] = [int(d) for d in dom.split(",")]
        return out

    def _event(self, name: str, t: str, p: dict) -> dict:
        if t == "rssFeedReadTrigger":
            return {"app": "rss", "url": str(p.get("feedUrl") or "")}
        if t == "gmailTrigger":
            sp: dict[str, Any] = {"app": "email"}
            q = (p.get("filters") or {}).get("q")
            if q:
                sp["search"] = str(q)[:300]
            sp["unread_only"] = str((p.get("filters") or {}).get("readStatus") or "") == "unread"
            return sp
        if t == "googleSheetsTrigger":
            sp = {"app": "sheet_row", "spreadsheet": _rl(p.get("documentId")) or "(pick the sheet)"}
            if _rl(p.get("sheetName")):
                sp["tab"] = _rl(p.get("sheetName"))
            return sp
        if t == "googleDriveTrigger":
            sp = {"app": "drive_file"}
            if _rl(p.get("folderToWatch")):
                sp["folder"] = _rl(p.get("folderToWatch"))
            return sp
        return {"app": "calendar_event"}

    # ------------------------------------------------------------------ the steps
    def place(self, node: str, why: str, prev: str, extra: str = "") -> dict:
        t = _short((self.nodes.get(node) or {}).get("type"))
        self.report["placeholders"].append({"node": node, "type": t, "why": why + (". " + extra if extra else "")})
        self.refs[node] = prev
        return {"id": self.sid(node), "type": "stop", "as": "error", "label": node[:80],
                "message": f"Redo this step in Hoola: '{node}' ({t}) came from n8n - {why}"[:480],
                "n8n": {"type": t}}

    def conds(self, node: str, p: dict, prev: str) -> dict | None:
        """n8n conditions (both the new and the old shape) -> a Hoola filter group."""
        items, ci, comb = [], False, "all"
        c = p.get("conditions") or {}
        if isinstance(c, dict) and isinstance(c.get("conditions"), list):
            comb = "any" if str(c.get("combinator") or "and") == "or" else "all"
            ci = not bool((c.get("options") or p.get("options") or {}).get("caseSensitive", True))
            for x in c["conditions"]:
                o = x.get("operator") or {}
                op = OPS.get(str(o.get("operation") or "equals"), "")
                if not op:
                    self.check(node, f"The n8n check '{o.get('operation')}' is not one Hoola has; it became 'equals'")
                    op = "eq"
                right = x.get("rightValue")
                if o.get("operation") in ("true", "false"):
                    right = o.get("operation") == "true"
                item = {"left": self.expr(x.get("leftValue"), prev, node), "op": op}
                if op not in ("exists", "not_exists", "empty", "not_empty"):
                    item["right"] = self.expr(right, prev, node)
                if ci:
                    item["ci"] = True
                items.append(item)
        elif isinstance(c, dict):
            comb = "any" if str(p.get("combineOperation") or "all") == "any" else "all"
            for kind in ("string", "number", "boolean", "dateTime"):
                for x in c.get(kind) or []:
                    op = OPS.get(str(x.get("operation") or "equal"), "eq") or "eq"
                    item = {"left": self.expr(x.get("value1"), prev, node), "op": op}
                    if op not in ("exists", "not_exists", "empty", "not_empty"):
                        item["right"] = self.expr(x.get("value2"), prev, node)
                    items.append(item)
        if not items:
            return None
        return {comb: items}

    def chain(self, start: str, prev: str, stop: set, first: bool = False) -> tuple[list[dict], str, str]:
        """Steps from `start` on, until a join (a node two ways lead into), a node in stop or the end.
        -> (steps, ref of the last output, the join reached). `first`: start itself may be a join."""
        steps: list[dict] = []
        cur = start
        while cur:
            if cur in stop:
                return steps, prev, cur
            if self.joins(cur) and not (first and cur == start):
                return steps, prev, cur
            if cur in self.done:
                return steps, prev, ""
            self.done.add(cur)
            got, prev, cur = self.node(cur, prev, stop)
            steps.extend(got)
        return steps, prev, ""

    def follow(self, name: str, prev: str, stop: set, out: int = 0) -> tuple[list[dict], str, str]:
        """What comes after node `name` on output `out` (several targets run one after another here)."""
        tg = self.targets(name, out)
        if not tg:
            return [], prev, ""
        if len(tg) == 1:
            return [], prev, tg[0]
        self.report["notes"].append(f"After '{name}' n8n went on to {len(tg)} steps side by side; here they run "
                                    "one after another")
        steps, join = [], ""
        for t in tg:
            if self.joins(t):
                join = join or t
                continue
            s, _last, j = self.chain(t, prev, stop)
            steps.extend(s)
            join = join or j
        if steps:
            return steps, prev, join
        return [], prev, join

    def node(self, name: str, prev: str, stop: set) -> tuple[list[dict], str, str]:
        """One node -> (steps, ref of its output, next node). v0.999.253: a setting Hoola cannot read (a number
        written as an n8n expression, an odd shape) makes the node a placeholder instead of a failed import."""
        try:
            return self._node(name, prev, stop)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.report["converted"] = [c for c in self.report["converted"] if c.get("node") != name]
            why = ("a number in it was an n8n expression - type the number in Hoola" if "invalid literal" in str(e)
                   else "one of its settings could not be read")
            return self.placeholder(name, why, prev, stop)

    def _node(self, name: str, prev: str, stop: set) -> tuple[list[dict], str, str]:
        n = self.nodes[name]
        t = _short(n.get("type"))
        p = n.get("parameters") or {}
        sid = self.sid(name)
        conv = lambda typ: self.report["converted"].append({"node": name, "type": t, "as": typ})   # noqa: E731

        def then(step: dict | None, ref: str, typ: str) -> tuple[list[dict], str, str]:
            self.refs[name] = ref
            if step is not None:
                step.setdefault("label", name[:80])
                conv(typ)
            more, _r, nxt = self.follow(name, ref, stop)
            return ([step] if step else []) + more, ref, nxt

        if n.get("disabled"):
            self.report["skipped"].append({"node": name, "why": "It was switched off in n8n"})
            return then(None, prev, "")
        if t in ("noOp", "stickyNote", "start"):
            if t == "stickyNote" and p.get("content"):
                self.report["notes"].append("Note in n8n: " + str(p["content"])[:300])
            return then(None, prev, "")
        if name in self.subs or SUB_NODE.match(t):
            self.report["skipped"].append({"node": name, "why": "A part of an n8n AI node (its model, memory or a "
                                           "tool) - Hoola's AI step uses Hoola's own model"})
            return then(None, prev, "")
        if t == "httpRequest":
            if not str(p.get("url") or "").strip():
                return self.placeholder(name, "it named no web address", prev, stop)
            return then(self._http(name, p, prev), f"steps.{sid}.output.json", "web request")
        if t == "set":
            vals: dict[str, Any] = {}
            for a in (p.get("assignments") or {}).get("assignments") or []:
                vals[str(a.get("name") or "field")] = self.expr(a.get("value"), prev, name)
            for kind in ("string", "number", "boolean"):
                for a in (p.get("values") or {}).get(kind) or []:
                    vals[str(a.get("name") or "field")] = self.expr(a.get("value"), prev, name)
            if not vals and str(p.get("mode") or "") == "raw":
                vals = self._raw_json(p.get("jsonOutput"), prev, name)
            if not vals:
                return self.placeholder(name, "it set fields with a JSON block Hoola could not read", prev, stop)
            if p.get("includeOtherFields") or str(p.get("include") or "") == "all":
                self.check(name, "n8n kept the other fields too; here only these fields come out")
            return then({"id": sid, "type": "data", "op": "fields", "values": vals}, f"steps.{sid}.output", "fields")
        if t in ("if", "filter"):
            f = self.conds(name, p, prev)
            if f is None:
                return self.placeholder(name, "its check could not be read", prev, stop)
            if t == "filter":
                return then({"id": sid, "type": "filter", "filter": f}, prev, "filter")
            return self._branches(name, sid, prev, stop, [("then", 0), ("else", 1)], filt=f)
        if t == "switch":
            return self._switch(name, sid, p, prev, stop)
        if t in ("textClassifier", "sentimentAnalysis"):
            return self._ai_ways(name, sid, t, p, prev, stop)
        if t == "wait":
            return then(self._wait(name, sid, p, prev), prev, "wait")
        if t in ("splitInBatches",):
            return self._loop(name, sid, n, prev, stop)
        if t == "merge":
            return self._merge(name, sid, p, prev, stop)
        if t == "sort":
            fs = (p.get("sortFieldsUi") or {}).get("sortField") or []
            if not fs:
                return self.placeholder(name, "it sorted in a way Hoola cannot read", prev, stop)
            if len(fs) > 1:
                self.check(name, "n8n sorted by several fields; here by the first")
            return then({"id": sid, "type": "data", "op": "sort", "items": "{{" + prev + "}}",
                         "by": str(fs[0].get("fieldName") or ""), "order": "desc" if fs[0].get("order") == "descending"
                         else "asc"}, f"steps.{sid}.output", "sort")
        if t == "limit":
            return then({"id": sid, "type": "data", "op": "limit", "items": "{{" + prev + "}}",
                         "count": int(p.get("maxItems") or 1),
                         "keep": "last" if p.get("keep") == "lastItems" else "first"}, f"steps.{sid}.output", "limit")
        if t == "removeDuplicates":
            fields = str(p.get("fieldsToCompare") or "").split(",") if p.get("compare") == "selectedFields" else [""]
            if len(fields) > 1:
                self.check(name, "n8n compared several fields; here the first")
            return then({"id": sid, "type": "data", "op": "dedupe", "items": "{{" + prev + "}}",
                         "by": fields[0].strip()}, f"steps.{sid}.output", "remove duplicates")
        if t == "splitOut":
            f = str(p.get("fieldToSplitOut") or "").split(",")[0].strip()
            if not f:
                return self.placeholder(name, "it named no field to split out", prev, stop)
            return then({"id": sid, "type": "data", "op": "split", "items": "{{" + prev + "}}", "field": f},
                        f"steps.{sid}.output", "split out")
        if t in ("aggregate", "summarize"):
            return self._aggregate(name, sid, t, p, prev, stop, then)
        if t == "respondToWebhook":
            code = (p.get("options") or {}).get("responseCode") or 200
            how = str(p.get("respondWith") or "firstIncomingItem")
            body: Any = {"ok": True} if how == "noData" else "{{" + prev + "}}"
            if how in ("json", "text"):
                body = self.expr(p.get("responseBody") if how == "json" else p.get("responseBody") or "", prev, name)
                if isinstance(body, str) and how == "json" and not body.startswith("{{"):
                    try:
                        body = json.loads(body)
                    except ValueError:
                        pass
            return then({"id": sid, "type": "respond", "status": int(code), "body": body}, prev, "answer the caller")
        if t == "stopAndError":
            return then({"id": sid, "type": "stop", "as": "error",
                         "message": self.expr(str(p.get("errorMessage") or "Stopped"), prev, name)}, prev, "stop")
        if t == "executeWorkflow":
            route = _slug(_rl(p.get("workflowId")) or "other_route", set(), "route")
            self.report["notes"].append(f"'{name}' runs another workflow - bring that one in too, as '{route}'")
            vars_ = (p.get("workflowInputs") or {}).get("value") or {}
            return then({"id": sid, "type": "subroute", "route": route,
                         **({"vars": self.expr(vars_, prev, name)} if isinstance(vars_, dict) and vars_ else {})},
                        f"steps.{sid}.output", "sub-route")
        if t in ("agent", "chainLlm", "chainSummarization", "informationExtractor", "chainRetrievalQa", "openAi"):
            return then(self._clip(name, self._ai(name, sid, t, p, prev)), f"steps.{sid}.output", "AI step")
        got = self._more(name, sid, t, p, prev, stop, then)
        if got is not None:
            return got
        if t in ("code", "function", "functionItem", "executeCommand", "ssh"):
            code = str(p.get("jsCode") or p.get("pythonCode") or p.get("functionCode") or p.get("command") or "")
            return self.placeholder(name, "it ran code in n8n; Hoola does not run that code. Rewrite it as a Code "
                                    "step (Python) or a Data step", prev, stop, extra=("Its code began: " + code[:300])
                                    if code else "")
        if t in ("dateTime", "crypto", "html", "xml", "markdown", "convertToFile", "extractFromFile", "itemLists",
                 "compareDatasets", "renameKeys"):
            return self.placeholder(name, "make it with a Data step (dates, text, files, compare, rename)", prev, stop)
        app = t.replace("Tool", "")
        app = app[:1].upper() + app[1:]
        what = " / ".join(str(x) for x in (p.get("resource"), p.get("operation")) if x)
        return self.placeholder(name, f"connect {app} in Connectors and pick its action in Add a step"
                                + (f" ({what})" if what else ""), prev, stop)

    # ------------------------------------------------------------------ v0.999.264 WORKFLOW LIBRARY: more nodes
    def _raw_json(self, raw: Any, prev: str, name: str) -> dict:
        """A Set node in JSON mode: {"a": "{{ $json.x }}", "n": {{ $json.n }}} -> Hoola field values."""
        if isinstance(raw, dict):
            return {str(k): self.expr(v, prev, name) for k, v in raw.items()}
        text = str(raw or "").strip()
        if text.startswith("="):
            text = text[1:]
        held: list[str] = []

        def hold(m: re.Match) -> str:
            held.append(m.group(0))
            return f"@@HX{len(held) - 1}@@"
        body = re.sub(r"\{\{.*?\}\}", hold, text, flags=re.S)
        # a held expression outside a JSON string (a number, a whole object) gets quotes so the text parses
        out, ins, esc_, i = [], False, False, 0
        while i < len(body):
            ch = body[i]
            if ins:
                out.append(ch)
                esc_ = (ch == "\\") and not esc_
                if ch == '"' and not esc_:
                    ins = False
                i += 1
                continue
            m = re.match(r"@@HX\d+@@", body[i:])
            if m:
                out.append('"' + m.group(0) + '"')
                i += len(m.group(0))
                continue
            if ch == '"':
                ins = True
            out.append(ch)
            i += 1
        try:
            obj = json.loads("".join(out))
        except ValueError:
            return {}
        if not isinstance(obj, dict):
            return {}

        def back(v: Any) -> Any:
            if isinstance(v, dict):
                return {k: back(x) for k, x in v.items()}
            if isinstance(v, list):
                return [back(x) for x in v]
            if isinstance(v, str) and "@@HX" in v:
                return self.expr("=" + re.sub(r"@@HX(\d+)@@", lambda m: held[int(m.group(1))], v), prev, name)
            return v
        return {str(k): back(v) for k, v in obj.items()}

    def _clip(self, name: str, step: dict) -> dict:
        for k in ("prompt", "text", "question"):
            v = step.get(k)
            if isinstance(v, str) and len(v) > 1990:
                step[k] = v[:1990]
                self.check(name, "Its prompt was longer than a Hoola step takes (2,000 characters); the end was cut - "
                                 "shorten it or put the long part in a Variable")
        return step

    def _add(self, name: str, sid: str, step: dict, field: str, prev: str, then, typ: str, out: str = ""):
        """A node that added `field` to the item: its own step; later {{ $json.field }} reads that step."""
        self.fieldmap[(prev, field)] = out or f"steps.{sid}.output"
        return then(step, prev, typ)

    def _as(self, name: str, t2: str, p2: dict, prev: str, stop: set):
        """Convert this node as if it were n8n's `t2` node (itemLists' operations are other nodes)."""
        real = self.nodes[name]
        self.nodes[name] = {**real, "type": BASE + t2, "parameters": p2}
        try:
            return self._node(name, prev, stop)
        finally:
            self.nodes[name] = real

    def _field(self, dp: str, prev: str, name: str) -> Any:
        return self.expr("={{ $json[\"" + str(dp or "data").replace('"', "") + "\"] }}", prev, name)

    def _more(self, name: str, sid: str, t: str, p: dict, prev: str, stop: set, then):
        """The nodes Hoola has its own step for (data, files, Google apps, messages) - None = not one of them."""
        op = str(p.get("operation") or "")
        E = lambda v: self.expr(v, prev, name)                      # noqa: E731
        if t == "dateTime":
            return self._date(name, sid, p, prev, then)
        if t == "crypto":
            act = str(p.get("action") or "hash")
            field = str(p.get("dataPropertyName") or "data")
            if act == "generate":
                kind = str(p.get("encodingType") or "uuid")
                step = {"id": sid, "type": "data", "op": "crypto", "action": "uuid" if kind == "uuid" else "random"}
                if kind != "uuid":
                    step["length"] = int(p.get("stringLength") or 32)
                return self._add(name, sid, step, field, prev, then, "hash and IDs")
            algo = {"MD5": "md5", "SHA1": "sha1", "SHA256": "sha256"}.get(str(p.get("type") or "MD5").upper())
            if act not in ("hash", "hmac") or not algo or (act == "hmac" and algo != "sha256"):
                return self.placeholder(name, "it used a hash Hoola does not make (Hoola makes MD5, SHA-1, SHA-256 "
                                        "and HMAC SHA-256)", prev, stop)
            if str(p.get("encoding") or "hex") != "hex":
                self.check(name, "n8n gave the hash in base64; here it comes as hex")
            step = {"id": sid, "type": "data", "op": "crypto", "action": "hmac_sha256" if act == "hmac" else algo,
                    "value": E(p.get("value"))}
            if act == "hmac":
                step["secret"] = E(p.get("secret"))
            return self._add(name, sid, step, field, prev, then, "hash and IDs")
        if t == "html":
            return self._html(name, sid, op or "generateHtmlTemplate", p, prev, stop, then)
        if t == "markdown":
            to_html = str(p.get("mode") or "htmlToMarkdown") == "markdownToHtml"
            step = {"id": sid, "type": "data", "op": "text", "action": "markdown_to_html" if to_html else "html_to_markdown",
                    "value": E(p.get("markdown") if to_html else p.get("html"))}
            return self._add(name, sid, step, str(p.get("destinationKey") or "data"), prev, then, "text and formats")
        if t == "xml":
            dp = str(p.get("dataPropertyName") or "data")
            if str(p.get("mode") or "xmlToJson") == "jsonToxml":
                step = {"id": sid, "type": "data", "op": "text", "action": "data_to_xml", "value": "{{" + prev + "}}"}
            else:
                step = {"id": sid, "type": "data", "op": "text", "action": "xml_to_data", "value": self._field(dp, prev, name)}
            return self._add(name, sid, step, dp, prev, then, "text and formats")
        if t == "renameKeys":
            mp, bad = {}, False
            for k in (p.get("keys") or {}).get("key") or []:
                a, b = str(k.get("currentKey") or ""), k.get("newKey")
                if not a or not isinstance(b, str) or b.startswith("="):
                    bad = True
                    continue
                mp[a] = b
            if not mp:
                return self.placeholder(name, "the new names were n8n expressions", prev, stop)
            if bad:
                self.check(name, "Some new names were n8n expressions; those were left out")
            return then({"id": sid, "type": "data", "op": "rename", "items": "{{" + prev + "}}", "map": mp},
                        f"steps.{sid}.output", "rename fields")
        if t == "compareDatasets":
            return self._compare(name, sid, p, prev, stop)
        if t == "itemLists":
            op = op or "splitOutItems"
            p2 = dict(p)
            if op == "removeDuplicates" and isinstance(p.get("fieldsToCompare"), dict):
                p2["fieldsToCompare"] = ",".join(str(x.get("fieldName") or "") for x in
                                                 (p["fieldsToCompare"].get("fields") or []))
            t2 = {"splitOutItems": "splitOut", "aggregateItems": "aggregate", "concatenateItems": "aggregate",
                  "removeDuplicates": "removeDuplicates", "sort": "sort", "limit": "limit",
                  "summarize": "summarize"}.get(op)
            if not t2:
                return self.placeholder(name, f"its '{op}' is not one Hoola has", prev, stop)
            return self._as(name, t2, p2, prev, stop)
        if t == "rssFeedRead":
            url = E(str(p.get("url") or ""))
            if not url:
                return None
            g = sid + "_get"
            self.used.add(g)
            self.report["converted"].append({"node": name, "type": t, "as": "web request + read XML"})
            self.check(name, "The feed comes as its whole XML tree (rss > channel > item); point the next step at "
                             f"{{{{steps.{sid}.output.rss.channel.item}}}}")
            self.refs[name] = f"steps.{sid}.output"
            more, _r, nxt = self.follow(name, self.refs[name], stop)
            return [{"id": g, "type": "http", "method": "GET", "url": url, "label": (name + " (fetch)")[:80]},
                    {"id": sid, "type": "data", "op": "text", "action": "xml_to_data",
                     "value": "{{steps." + g + ".output.text}}", "label": name[:80]}] + more, self.refs[name], nxt
        if t in ("extractFromFile", "spreadsheetFile") and (t == "extractFromFile" or (op or "fromFile") == "fromFile"):
            if prev in self.textsrc:
                self.report["converted"].append({"node": name, "type": t, "as": "(nothing - the file is read as text here)"})
                return then(None, prev, "")
            return self.placeholder(name, "it read a file n8n carried along; in Hoola use 'Make or read a file' "
                                    "(Read) with the file's id from the step that brings the file", prev, stop)
        if t in ("convertToFile", "spreadsheetFile"):
            fmt = str(p.get("fileFormat") or op or "csv")
            act = {"csv": "make_csv", "xlsx": "make_xlsx", "toFile": "make_csv"}.get(fmt)
            if not act:
                return self.placeholder(name, f"it made a {fmt} file; Hoola makes CSV, Excel and PDF files", prev, stop)
            nm = (p.get("options") or {}).get("fileName")
            step = {"id": sid, "type": "data", "op": "file", "action": act, "items": "{{" + prev + "}}"}
            if nm:
                step["name"] = E(nm)
            return then(step, f"steps.{sid}.output", "make a file")
        if t == "openWeatherMap":
            if op and op != "currentWeather":
                self.check(name, "n8n read the forecast; here it is today's weather")
            return then({"id": sid, "type": "tool", "name": "get_weather", "args": {"city": E(p.get("cityName") or "")}},
                        f"steps.{sid}.output", "weather")
        if t == "googleSheets":
            return self._sheets(name, sid, op or "read", p, prev, stop, then)
        if t in ("gmail", "emailSend"):
            return self._mail(name, sid, t, op, p, prev, stop, then)
        if t == "googleDrive":
            return self._drive(name, sid, op, p, prev, stop, then)
        if t == "googleCalendar":
            res = str(p.get("resource") or "event")
            op = op or "create"
            if res != "event" or op not in ("create", "getAll"):
                return None
            if op == "getAll":
                o = {**(p.get("options") or {}), **{k: p[k] for k in ("timeMin", "timeMax") if p.get(k)}}
                args = {}
                if o.get("timeMin"):
                    args["from_date"] = E(o["timeMin"])
                if o.get("timeMax"):
                    args["to_date"] = E(o["timeMax"])
                self.check(name, "Hoola reads your calendar by date (YYYY-MM-DD); check the From and To dates")
                return then({"id": sid, "type": "tool", "name": "calendar_agenda", "args": args},
                            f"steps.{sid}.output", "calendar")
            af = p.get("additionalFields") or {}
            args = {"title": E(af.get("summary") or "Event"), "start": E(p.get("start") or ""), "end": E(p.get("end") or "")}
            for a, b in (("description", "description"), ("location", "location")):
                if af.get(a):
                    args[b] = E(af[a])
            if af.get("attendees"):
                args["attendees"] = E(af["attendees"])
            if not args["end"]:
                args.pop("end")
            return then({"id": sid, "type": "tool", "name": "calendar_add_event", "args": args},
                        f"steps.{sid}.output", "calendar")
        if t in ("telegram", "slack", "discord", "mattermost"):
            return self._message(name, sid, t, op, p, prev, stop, then)
        return None

    _LUX = (("yyyy", "%Y"), ("yy", "%y"), ("MMMM", "%B"), ("LLLL", "%B"), ("MMM", "%b"), ("LLL", "%b"), ("MM", "%m"),
            ("LL", "%m"), ("dd", "%d"), ("EEEE", "%A"), ("cccc", "%A"), ("EEE", "%a"), ("ccc", "%a"), ("HH", "%H"),
            ("hh", "%I"), ("mm", "%M"), ("ss", "%S"), ("a", "%p"), ("M", "%m"), ("L", "%m"), ("d", "%d"), ("H", "%H"),
            ("h", "%I"))
    _MOM = (("YYYY", "%Y"), ("YY", "%y"), ("MMMM", "%B"), ("MMM", "%b"), ("MM", "%m"), ("DD", "%d"), ("dddd", "%A"),
            ("ddd", "%a"), ("HH", "%H"), ("hh", "%I"), ("mm", "%M"), ("ss", "%S"), ("A", "%p"), ("M", "%m"), ("D", "%d"))

    def _fmt(self, f: str, moment: bool = False) -> tuple[str, bool]:
        """A Luxon (n8n v2) or Moment (v1) date format -> Python's; False when a part had no match."""
        out, i, ok = [], 0, True
        table = self._MOM if moment else self._LUX
        while i < len(f):
            if f[i] in "'[":
                end = "'" if f[i] == "'" else "]"
                j = f.find(end, i + 1)
                j = len(f) if j < 0 else j
                out.append(f[i + 1:j].replace("%", "%%"))
                i = j + 1
                continue
            for a, b in table:
                if f.startswith(a, i):
                    out.append(b)
                    i += len(a)
                    break
            else:
                if f[i].isalpha():
                    ok = False
                out.append("%%" if f[i] == "%" else f[i])
                i += 1
        return "".join(out), ok

    def _date(self, name: str, sid: str, p: dict, prev: str, then):
        E = lambda v: self.expr(v, prev, name)                      # noqa: E731
        unit = lambda u: str(u or "days")                            # noqa: E731
        if p.get("action") or "toFormat" in p or "value" in p:      # version 1 (Moment formats)
            act = str(p.get("action") or "format")
            field = str(p.get("dataPropertyName") or "data")
            if act == "calculate":
                step = {"id": sid, "type": "data", "op": "date", "action": "subtract" if p.get("operation") == "subtract"
                        else "add", "value": E(p.get("value")), "amount": p.get("duration") or 1, "unit": unit(p.get("timeUnit"))}
            else:
                f, ok = self._fmt(str(p.get("toFormat") or "YYYY-MM-DD"), moment=True)
                if not ok:
                    self.check(name, "Part of its date format has no match here; check the format")
                step = {"id": sid, "type": "data", "op": "date", "action": "format", "value": E(p.get("value")), "format": f}
            return self._add(name, sid, step, field, prev, then, "date and time")
        op = str(p.get("operation") or "getCurrentDate")
        tz = str((p.get("options") or {}).get("timezone") or "")
        if op == "getCurrentDate":
            step = {"id": sid, "type": "data", "op": "date", "action": "now"}
            field = "currentDate"
        elif op in ("addToDate", "subtractFromDate"):
            u = unit(p.get("timeUnit"))
            if u in ("quarters", "milliseconds"):
                self.check(name, f"Hoola counts days, weeks, months, years, hours, minutes and seconds - not {u}")
            step = {"id": sid, "type": "data", "op": "date", "action": "add" if op == "addToDate" else "subtract",
                    "value": E(p.get("magnitude")), "amount": E(p.get("duration") if p.get("duration") is not None else 1),
                    "unit": u}
            field = "newDate"
        elif op == "formatDate":
            raw = str(p.get("customFormat") if p.get("format") == "custom" else p.get("format") or "yyyy-MM-dd")
            if raw in ("X", "x"):
                self.check(name, "n8n gave a Unix timestamp; here it is a date text - use timestamp() in an expression")
                raw = "yyyy-MM-dd HH:mm:ss"
            f, ok = self._fmt(raw)
            if not ok:
                self.check(name, "Part of its date format has no match here; check the format")
            step = {"id": sid, "type": "data", "op": "date", "action": "format", "value": E(p.get("date")), "format": f}
            field = "formattedDate"
        elif op == "getTimeBetweenDates":
            us = p.get("units") or ["days"]
            step = {"id": sid, "type": "data", "op": "date", "action": "diff", "value": E(p.get("startDate")),
                    "other": E(p.get("endDate")), "unit": str(us[0] if isinstance(us, list) and us else us)}
            field = "timeDifference"
        else:
            return None
        if tz:
            step["tz"] = tz
        return self._add(name, sid, step, str(p.get("outputFieldName") or field), prev, then, "date and time")

    def _html(self, name: str, sid: str, op: str, p: dict, prev: str, stop: set, then):
        if op == "generateHtmlTemplate":
            step = {"id": sid, "type": "data", "op": "fields", "values": {"html": self.expr(p.get("html") or "", prev, name)}}
            return self._add(name, sid, step, "html", prev, then, "fields", f"steps.{sid}.output.html")
        if op != "extractHtmlContent":
            return None
        vals = (p.get("extractionValues") or {}).get("values") or []
        if not vals:
            return self.placeholder(name, "it named nothing to pick from the page", prev, stop)
        src = self.expr(p.get("dataPropertyName") and "={{ $json[\"%s\"] }}" % p.get("dataPropertyName")
                        or "={{ $json.data }}", prev, name)
        steps = []
        for v in vals[:8]:
            key = str(v.get("key") or "value")
            x = sid if len(vals) == 1 else _slug(sid + "_" + key, self.used)
            st = {"id": x, "type": "data", "op": "text", "action": "html_select", "value": src,
                  "selector": str(v.get("cssSelector") or ""), "label": (name + (" - " + key if len(vals) > 1 else ""))[:80]}
            rv = str(v.get("returnValue") or "text")
            if rv == "attribute":
                st["attr"] = str(v.get("attribute") or "")
            elif rv in ("html", "value"):
                self.check(name, f"'{key}': n8n took the {rv} of the element; here it takes its text")
            if "script" in st["selector"]:
                self.check(name, f"'{key}': Hoola leaves script tags out when it reads a page")
            steps.append(st)
            self.fieldmap[(prev, key)] = f"steps.{x}.output" + ("" if v.get("returnArray") else "[0]")
        if len(vals) > 8:
            self.check(name, "Only the first 8 picks came in")
        self.refs[name] = prev
        self.report["converted"].append({"node": name, "type": "html", "as": "pick from a page"})
        more, _r, nxt = self.follow(name, prev, stop)
        return steps + more, prev, nxt

    def _compare(self, name: str, sid: str, p: dict, prev: str, stop: set):
        ins = sorted(self.inc.get(name) or [], key=lambda x: x[2])
        a = self.refs.get(ins[0][0], prev) if ins else prev
        b = self.refs.get(ins[1][0], prev) if len(ins) > 1 else prev
        mf = ((p.get("mergeByFields") or {}).get("values") or [{}])[0]
        step = {"id": sid, "type": "data", "op": "compare", "a": "{{" + a + "}}", "b": "{{" + b + "}}",
                "key": str(mf.get("field1") or "id"), "label": name[:80]}
        if mf.get("field2") and mf.get("field2") != mf.get("field1"):
            self.check(name, "n8n matched different field names on each side; here both sides use " + step["key"])
        self.refs[name] = f"steps.{sid}.output"
        self.report["converted"].append({"node": name, "type": "compareDatasets", "as": "compare two lists"})
        steps, join = [step], ""
        for oi, key in enumerate(("removed", "same", "changed", "added")):
            for x in self.targets(name, oi):
                s_, _l, j = self.chain(x, f"steps.{sid}.output.{key}", stop)
                steps += s_
                join = join or j
        if sum(1 for oi in range(4) if self.targets(name, oi)) > 1:
            self.report["notes"].append(f"After '{name}' the ways (only in A, same, different, only in B) run one "
                                        "after another here")
        return steps, self.refs[name], join

    @staticmethod
    def _rlv(v: Any) -> str:
        """A resource locator's link or id (not its display name)."""
        if isinstance(v, dict):
            return str(v.get("cachedResultUrl") or v.get("value") or "")
        return str(v or "")

    def _sheets(self, name: str, sid: str, op: str, p: dict, prev: str, stop: set, then):
        E = lambda v: self.expr(v, prev, name)                      # noqa: E731
        doc = E(self._rlv(p.get("documentId")) or str(p.get("sheetId") or ""))
        sn = p.get("sheetName")
        tab = (str(sn.get("cachedResultName") or "") if isinstance(sn, dict) else str(sn or ""))
        if isinstance(sn, dict) and not tab and not str(sn.get("value") or "").startswith("gid="):
            tab = str(sn.get("value") or "")
        if not tab and "!" in str(p.get("range") or ""):
            tab = str(p["range"]).split("!")[0].strip("'")
        if not doc:
            return self.placeholder(name, "it named no sheet", prev, stop)
        base = {"spreadsheet": doc, **({"tab": E(tab)} if tab else {})}
        cols = (p.get("columns") or {})
        vals = cols.get("value") if isinstance(cols.get("value"), dict) else {}
        if op in ("read", "lookup"):
            f = ((p.get("filtersUI") or {}).get("values") or [])
            if op == "lookup" and p.get("lookupColumn"):
                f = [{"lookupColumn": p.get("lookupColumn"), "lookupValue": p.get("lookupValue")}]
            if f:
                where = [{"column": str(x.get("lookupColumn") or ""), "op": "=", "value": E(x.get("lookupValue"))}
                         for x in f if x.get("lookupColumn")]
                return then({"id": sid, "type": "tool", "name": "sheet_query", "args": {**base, "where": where}},
                            f"steps.{sid}.output", "Google Sheets")
            return then({"id": sid, "type": "tool", "name": "sheet_read", "args": base}, f"steps.{sid}.output", "Google Sheets")
        if op == "append":
            rows: Any = [{str(k): E(v) for k, v in vals.items()}] if vals else "{{" + prev + "}}"
            return then({"id": sid, "type": "tool", "name": "sheet_append", "args": {**base, "rows": rows}},
                        f"steps.{sid}.output", "Google Sheets")
        if op in ("update", "appendOrUpdate"):
            mc = (cols.get("matchingColumns") or [p.get("columnToMatchOn")] or [""])[0] or ""
            if not vals or not mc or mc not in vals:
                return self.placeholder(name, "it updated rows by a column Hoola could not read", prev, stop)
            if op == "appendOrUpdate":
                self.check(name, "n8n added the row when no row matched; here only matching rows are updated")
            return then({"id": sid, "type": "tool", "name": "sheet_update",
                         "args": {**base, "set": {str(k): E(v) for k, v in vals.items() if k != mc},
                                  "where": [{"column": str(mc), "op": "=", "value": E(vals[mc])}]}},
                        f"steps.{sid}.output", "Google Sheets")
        return None

    def _mail(self, name: str, sid: str, t: str, op: str, p: dict, prev: str, stop: set, then):
        E = lambda v: self.expr(v, prev, name)                      # noqa: E731
        res = str(p.get("resource") or "message")
        if t == "emailSend" or (res in ("message", "draft") and (op or ("create" if res == "draft" else "send")) in ("send", "create")):
            if op == "sendAndWait":
                return None
            to = p.get("toEmail") if t == "emailSend" else (p.get("sendTo") or p.get("toList"))
            body = p.get("message") if t == "gmail" else (p.get("text") or p.get("html") or p.get("message"))
            args = {"to": E(to or ""), "subject": E(p.get("subject") or ""), "body": E(body or "")}
            if not args["to"]:
                args.pop("to")
                self.check(name, "Say who the mail goes to")
            if res != "draft":
                self.check(name, "n8n sent this mail at once; here it is a draft that waits for your OK in Hoola")
            return then({"id": sid, "type": "tool", "name": "email_draft", "args": args}, f"steps.{sid}.output", "email")
        if t == "gmail" and res == "message" and op == "reply":
            return then({"id": sid, "type": "tool", "name": "email_draft",
                         "args": {"reply_to_id": E(p.get("messageId") or ""), "body": E(p.get("message") or "")}},
                        f"steps.{sid}.output", "email")
        if t == "gmail" and res == "message" and op == "getAll":
            fl = p.get("filters") or {}
            q = " ".join(str(x) for x in [fl.get("q"), ("from:" + str(fl["sender"])) if fl.get("sender") else ""] if x)
            args: dict[str, Any] = {"limit": min(int(p.get("limit") or 10), 50) if not p.get("returnAll") else 50}
            if q:
                args["search"] = E(q)
            if fl.get("receivedAfter") or fl.get("receivedBefore"):
                self.check(name, "n8n read mail between two dates; put the dates in the search (after:YYYY/MM/DD)")
            return then({"id": sid, "type": "tool", "name": "email_check", "args": args}, f"steps.{sid}.output", "email")
        if t == "gmail" and res == "message" and op == "get":
            return then({"id": sid, "type": "tool", "name": "email_read", "args": {"id": E(p.get("messageId") or "")}},
                        f"steps.{sid}.output", "email")
        return None

    def _drive(self, name: str, sid: str, op: str, p: dict, prev: str, stop: set, then):
        E = lambda v: self.expr(v, prev, name)                      # noqa: E731
        res = str(p.get("resource") or "file")
        op = op or ("search" if res == "fileFolder" else "create" if res == "folder" else "upload")
        if op == "download":
            ref = f"steps.{sid}.output"
            self.textsrc.add(ref)
            return then({"id": sid, "type": "tool", "name": "drive_read_file", "args": {"file": E(self._rlv(p.get("fileId")))}},
                        ref, "Google Drive")
        if op == "createFromText":
            args = {"title": E(p.get("name") or "From n8n"), "text": E(p.get("content") or "")}
            fo = self._rlv(p.get("folderId"))
            if fo and fo != "root":
                args["folder"] = E(fo)
            return then({"id": sid, "type": "tool", "name": "drive_create_doc", "args": args}, f"steps.{sid}.output",
                        "Google Drive")
        if op == "search":
            q = p.get("queryString") or ((p.get("filter") or {}).get("query"))
            return then({"id": sid, "type": "tool", "name": "drive_find", "args": {"query": E(q)} if q else {}},
                        f"steps.{sid}.output", "Google Drive")
        if res == "folder" and op == "create":
            args = {"name": E(p.get("name") or "New folder")}
            fo = self._rlv(p.get("folderId"))
            if fo and fo != "root":
                args["parent"] = E(fo)
            return then({"id": sid, "type": "tool", "name": "drive_create_folder", "args": args}, f"steps.{sid}.output",
                        "Google Drive")
        return None

    def _message(self, name: str, sid: str, t: str, op: str, p: dict, prev: str, stop: set, then):
        app = {"telegram": "Telegram", "slack": "Slack", "discord": "Discord", "mattermost": "Mattermost"}[t]
        res = str(p.get("resource") or "message")
        if res != "message" or (op and op not in ("sendMessage", "post", "send")):
            return None
        text = p.get("text") or p.get("content") or p.get("message")
        if not text:
            return None
        if self.trig_app == t:
            return self.placeholder(name, f"it answers people who write to a {app} bot; connect {app} in Connections "
                                    "and use its 'send message' action here", prev, stop)
        where = p.get("chatId") or p.get("channelId") or p.get("channel") or p.get("webhookUri") or ""
        self.check(name, f"n8n posted this to {app}" + (f" ({_rl(where)[:60]})" if where and not str(_rl(where)).startswith("=")
                   else "") + "; here Hoola tells you in your Hoola chat. To post to " + app +
                   " instead, connect it in Connections and swap this step")
        said = self.expr(text, prev, name)
        if not str(said).strip():
            return None
        return then({"id": sid, "type": "notify", "text": said}, prev, "tell me")

    def placeholder(self, name: str, why: str, prev: str, stop: set, extra: str = "") -> tuple[list[dict], str, str]:
        step = self.place(name, why, prev, extra)
        more, _r, nxt = self.follow(name, prev, stop)
        return [step] + more, prev, nxt

    def _http(self, name: str, p: dict, prev: str) -> dict:
        sid = self.sid(name)
        method = str(p.get("method") or p.get("requestMethod") or "GET").upper()
        url = self.expr(str(p.get("url") or ""), prev, name)
        if method not in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            self.check(name, f"It used {method} in n8n; it is POST here")
            method = "POST"
        q = [(x.get("name"), x.get("value")) for x in (p.get("queryParameters") or {}).get("parameters") or []] + \
            [(x.get("name"), x.get("value")) for x in (p.get("queryParametersUi") or {}).get("parameter") or []]
        if q:
            pieces = []
            for k, v in q:
                v2 = self.expr(v, prev, name)
                v2 = v2 if isinstance(v2, str) and "{{" in v2 else quote(str(v2 if v2 is not None else ""), safe="")
                pieces.append(f"{quote(str(k or ''), safe='')}={v2}")
            url = str(url) + ("&" if "?" in str(url) else "?") + "&".join(pieces)
        headers = {str(x.get("name")): self.expr(x.get("value"), prev, name)
                   for x in ((p.get("headerParameters") or {}).get("parameters") or [])
                   + ((p.get("headerParametersUi") or {}).get("parameter") or []) if x.get("name")}
        step: dict[str, Any] = {"id": sid, "type": "http", "method": method, "url": url}
        if headers:
            step["headers"] = headers
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            bp = ((p.get("bodyParameters") or {}).get("parameters") or []) + \
                 ((p.get("bodyParametersUi") or {}).get("parameter") or [])
            if bp:
                step["body"] = {str(x.get("name")): self.expr(x.get("value"), prev, name) for x in bp if x.get("name")}
            elif p.get("jsonBody") or p.get("bodyParametersJson"):
                raw = p.get("jsonBody") or p.get("bodyParametersJson")
                if isinstance(raw, str) and not raw.startswith("="):
                    try:
                        step["body"] = json.loads(raw)
                    except ValueError:
                        step["body"] = raw
                else:
                    step["body"] = self.expr(raw, prev, name)
        if str(p.get("authentication") or "none") not in ("none", ""):
            self.check(name, "It signed in to the site in n8n. Sign-ins do not come across: add it under Sign-ins and "
                             "pick it on this step (Sign in with)")
        return step

    def _branches(self, name: str, sid: str, prev: str, stop: set, outs: list[tuple[str, int]],
                  filt: dict) -> tuple[list[dict], str, str]:
        self.refs[name] = prev
        got: dict[str, list] = {}
        back: set = set()
        join = ""
        for key, oi in outs:
            got[key] = []
            for x in self.targets(name, oi):
                s, _l, j = self.chain(x, prev, stop)
                got[key] += s
                if j and j in stop:
                    back.add(key)              # this way goes back to the loop: on to the next item
                else:
                    join = join or j
        if join:                 # an empty way ends there in n8n too: it never reaches the steps after
            for k in got:
                if not got[k] and k not in back:
                    got[k] = [self._end_here(name, k)]
        if not any(got.values()):
            if back:
                self.report["skipped"].append({"node": name, "why": "Both ways went straight on"})
                return [], prev, join
            self.check(name, "Nothing came after this check in n8n")
            got["then"] = [self._end_here(name, "then")]
        step: dict[str, Any] = {"id": sid, "type": "condition", "filter": filt, "label": name[:80]}
        for k, v in got.items():
            if v:
                step[k] = v
        self.report["converted"].append({"node": name, "type": "if", "as": "if / else"})
        return [step], prev, join

    def _end_here(self, name: str, way: str) -> dict:
        return {"id": _slug(f"{name}_{way}_end", self.used), "type": "stop", "as": "done",
                "label": f"Ends here ({way})", "message": ""}

    def _ways(self, name: str, sid: str, prev: str, stop: set, ways: list[tuple[str, dict | None, int]],
              fb: int | None, extra: dict | None = None, ai: bool = False) -> tuple[list[dict], str, str]:
        self.refs[name] = prev
        routes, join = [], ""
        for label, f, oi in ways:
            steps: list[dict] = []
            goes_back = False
            for x in self.targets(name, oi):
                s, _l, j = self.chain(x, prev, stop)
                steps += s
                if j and j in stop:
                    goes_back = True
                else:
                    join = join or j
            routes.append({"label": label[:80], **({"filter": f} if f else {}), "steps": steps, "_back": goes_back})
        fallback: list[dict] = []
        if fb is not None:
            for x in self.targets(name, fb):
                s, _l, j = self.chain(x, prev, stop)
                fallback += s
                if not (j and j in stop):
                    join = join or j
        kept = []
        for rt in routes:
            back = rt.pop("_back")
            if not rt["steps"]:
                if back or not join:           # nothing to do on this way: no way matches = the run goes on
                    continue
                rt["steps"] = [self._end_here(name, rt["label"])]
            kept.append(rt)
        routes = kept
        if not routes:
            self.report["skipped"].append({"node": name, "why": "None of its ways had steps"})
            return fallback, prev, join
        step: dict[str, Any] = {"id": sid, "type": "router", "routes": routes, "label": name[:80], **(extra or {})}
        if fallback:
            step["fallback"] = fallback
        self.report["converted"].append({"node": name, "type": _short(self.nodes[name].get("type")),
                                         "as": "ways (the AI picks)" if ai else "ways"})
        return [step], prev, join

    def _switch(self, name: str, sid: str, p: dict, prev: str, stop: set) -> tuple[list[dict], str, str]:
        if str(p.get("mode") or "rules") != "rules":
            return self.placeholder(name, "its way was worked out by an expression - make the ways again", prev, stop)
        ways: list[tuple[str, dict | None, int]] = []
        rules = (p.get("rules") or {}).get("values")
        if isinstance(rules, list):
            for i, r in enumerate(rules):
                f = self.conds(name, r, prev)
                ways.append((str(r.get("outputKey") or f"Way {i + 1}"), f, i))
            fbo = (p.get("options") or {}).get("fallbackOutput")
            fb = len(rules) if fbo == "extra" else (int(fbo) if isinstance(fbo, int) else None)
        else:
            old = (p.get("rules") or {}).get("rules") or []
            for i, r in enumerate(old):
                op = OPS.get(str(r.get("operation") or "equal"), "eq") or "eq"
                ways.append((f"Way {i + 1}", {"all": [{"left": self.expr(p.get("value1"), prev, name), "op": op,
                                                         "right": self.expr(r.get("value2"), prev, name)}]},
                             int(r.get("output") or i)))
            fb = int(p["fallbackOutput"]) if str(p.get("fallbackOutput") or "-1").lstrip("-").isdigit() \
                and int(p.get("fallbackOutput") or -1) >= 0 else None
        if not ways:
            return self.placeholder(name, "it had no ways", prev, stop)
        if (p.get("options") or {}).get("allMatchingOutputs"):
            self.check(name, "n8n sent data down every matching way; Hoola takes every way that matches too - check it")
        return self._ways(name, sid, prev, stop, ways, fb)

    def _ai_ways(self, name: str, sid: str, t: str, p: dict, prev: str, stop: set) -> tuple[list[dict], str, str]:
        text = self.expr(p.get("inputText") or "={{ $json }}", prev, name)
        if t == "textClassifier":
            cats = [str(c.get("category")) for c in (p.get("categories") or {}).get("categories") or [] if c.get("category")]
        else:
            cats = [x.strip() for x in str((p.get("options") or {}).get("categories") or "Positive, Neutral, Negative").split(",")
                    if x.strip()]
        if len(cats) < 2:
            return self.placeholder(name, "it had fewer than two kinds to sort into", prev, stop)
        ai_sid = sid
        step_ai = {"id": ai_sid, "type": "ai", "op": "classify" if t == "textClassifier" else "sentiment", "text": text,
                   "label": name[:80]}
        if t == "textClassifier":
            step_ai["categories"] = cats
        field = "category" if t == "textClassifier" else "label"
        ways = [(c, {"all": [{"left": f"{{{{steps.{ai_sid}.output.{field}}}}}", "op": "eq",
                              "right": c if t == "textClassifier" else c.lower()}]}, i) for i, c in enumerate(cats)]
        rsid = _slug(name + "_ways", self.used)
        steps, _ref, join = self._ways(name, rsid, prev, stop, ways, None, ai=True)
        self.refs[name] = f"steps.{ai_sid}.output"
        return [step_ai] + steps, prev, join

    def _wait(self, name: str, sid: str, p: dict, prev: str) -> dict:
        how = str(p.get("resume") or "timeInterval")
        if how == "webhook":
            return {"id": sid, "type": "wait", "for": "call", "timeout_s": 86400, "on_timeout": "continue"}
        if how == "specificTime":
            u = str(self.expr(p.get("dateTime") or "", prev, name) or "")
            if "{{" not in u:
                u = u.replace("T", " ")[:16]
            return {"id": sid, "type": "wait", "until": u or "09:00"}
        if how != "timeInterval":
            self.check(name, "It waited for a form in n8n; here it waits for its resume link to be called")
            return {"id": sid, "type": "wait", "for": "call", "timeout_s": 86400, "on_timeout": "continue"}
        unit = str(p.get("unit") or "hours")
        unit = unit if unit in ("seconds", "minutes", "hours", "days", "weeks") else "hours"
        amount = p.get("amount", 1)
        try:
            secs = float(amount) * {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}[unit]
            if secs > 30 * 86400:
                self.check(name, "It waited longer than 30 days in n8n; a Hoola wait is up to 30 days")
                amount, unit = 30, "days"
        except (TypeError, ValueError):
            amount = self.expr(amount, prev, name)
        return {"id": sid, "type": "wait", "amount": amount, "unit": unit}

    def _loop(self, name: str, sid: str, n: dict, prev: str, stop: set) -> tuple[list[dict], str, str]:
        if float(n.get("typeVersion") or 1) < 3:
            self.check(name, "An older n8n batch loop: check the steps inside the loop")
        body_start = self.targets(name, 1)
        self.refs[name] = prev
        body: list[dict] = []
        for b in body_start:
            s, _l, _j = self.chain(b, "item", stop | {name})
            body += s
        size = int((n.get("parameters") or {}).get("batchSize") or 1)
        if size > 1:
            self.check(name, f"n8n took {size} items at a time; here the loop goes through them one by one")
        steps: list[dict] = []
        if body:
            steps = [{"id": sid, "type": "loop", "items": "{{" + prev + "}}", "body": body, "label": name[:80]}]
            self.report["converted"].append({"node": name, "type": "splitInBatches", "as": "repeat for each"})
        else:
            self.report["skipped"].append({"node": name, "why": "The loop had nothing inside it"})
        done = self.targets(name, 0)
        if not done:
            return steps, prev, ""
        if len(done) == 1:
            return steps, prev, done[0]
        for d in done:
            s, _l, _j = self.chain(d, prev, stop)
            steps += s
        return steps, prev, ""

    def _merge(self, name: str, sid: str, p: dict, prev: str, stop: set) -> tuple[list[dict], str, str]:
        ins = sorted(self.inc.get(name) or [], key=lambda x: x[2])
        a = self.refs.get(ins[0][0], prev) if ins else prev
        b = self.refs.get(ins[1][0], prev) if len(ins) > 1 else prev
        mode = str(p.get("mode") or "append")
        step: dict[str, Any] = {"id": sid, "type": "data", "op": "merge", "a": "{{" + a + "}}", "b": "{{" + b + "}}",
                                "label": name[:80]}
        if mode == "append":
            step["mode"] = "append"
        elif mode in ("combine", "mergeByKey", "mergeByIndex"):
            by = str(p.get("combineBy") or p.get("combinationMode") or "")
            if mode == "mergeByIndex" or by in ("combineByPosition", "mergeByPosition"):
                step["mode"] = "by_position"
            elif by in ("combineAll", "multiplex", "combineBySql"):
                return self.placeholder(name, "it joined every item with every item - make it with a Data step", prev,
                                        stop)
            else:
                key = str(p.get("fieldsToMatchString") or p.get("propertyName1") or
                          (((p.get("mergeByFields") or {}).get("values") or [{}])[0].get("field1")) or "id")
                join = str(p.get("joinMode") or "keepMatches")
                step["key"] = key.split(",")[0].strip()
                if join == "keepNonMatches":
                    step["mode"] = "keep_non_matches"
                else:
                    step["mode"] = "by_key"
                    step["join"] = {"keepMatches": "inner", "keepEverything": "outer",
                                    "enrichInput1": "left"}.get(join, "inner")
                    if join == "enrichInput2":
                        step["a"], step["b"], step["join"] = step["b"], step["a"], "left"
        elif mode == "chooseBranch":
            self.refs[name] = a if str(p.get("output") or "input1") != "input2" else b
            self.report["converted"].append({"node": name, "type": "merge", "as": "waits for both ways"})
            more, _r, nxt = self.follow(name, self.refs[name], stop)
            return more, self.refs[name], nxt
        else:
            return self.placeholder(name, "its way of merging is not one Hoola has", prev, stop)
        self.refs[name] = f"steps.{sid}.output"
        self.report["converted"].append({"node": name, "type": "merge", "as": "merge lists"})
        more, _r, nxt = self.follow(name, self.refs[name], stop)
        return [step] + more, self.refs[name], nxt

    def _aggregate(self, name, sid, t, p, prev, stop, then):
        if t == "aggregate":
            if str(p.get("aggregate") or "aggregateIndividualFields") == "aggregateAllItemData":
                self.report["converted"].append({"node": name, "type": t, "as": "(nothing - already a list here)"})
                return then(None, prev, "")
            fs = (p.get("fieldsToAggregate") or {}).get("fieldToAggregate") or []
            if not fs:
                return self.placeholder(name, "it named no field", prev, stop)
            return then({"id": sid, "type": "data", "op": "aggregate", "items": "{{" + prev + "}}",
                         "field": str(fs[0].get("fieldToAggregate") or ""), "how": "list"},
                        f"steps.{sid}.output", "aggregate")
        fs = (p.get("fieldsToSummarize") or {}).get("values") or []
        if not fs:
            return self.placeholder(name, "it named nothing to summarise", prev, stop)
        how = {"count": "count", "countUnique": "unique", "sum": "sum", "average": "avg", "min": "min", "max": "max",
               "append": "list", "concatenate": "join"}.get(str(fs[0].get("aggregation") or "count"), "count")
        if len(fs) > 1 or p.get("fieldsToSplitBy"):
            self.check(name, "n8n summed several fields or grouped them; here the first field, not grouped")
        return then({"id": sid, "type": "data", "op": "aggregate", "items": "{{" + prev + "}}",
                     "field": str(fs[0].get("field") or ""), "how": how}, f"steps.{sid}.output", "summarise")

    def _ai(self, name: str, sid: str, t: str, p: dict, prev: str) -> dict:
        text = p.get("text") or p.get("prompt")
        if t == "openAi":
            msgs = (p.get("messages") or {}).get("values") or []
            text = "\n".join(str(m.get("content") or "") for m in msgs) or text
        if not text:
            text = "={{ $json.chatInput }}" if self.chat else "={{ $json }}"
        txt = self.expr(text, prev, name)
        if not str(txt).strip():
            txt = "{{" + prev + "}}"
        if self.ai_links.get(name):
            self.report["notes"].append(f"'{name}' used an n8n model and parts ({', '.join(self.ai_links[name][:6])}) - "
                                        "here it uses Hoola's model")
        if t == "agent":
            sysm = str(self.expr((p.get("options") or {}).get("systemMessage") or "", prev, name))
            tools = [x for x in self.ai_links.get(name, []) if "tool" in _short((self.nodes.get(x) or {}).get("type")).lower()]
            if tools:
                self.check(name, "The agent had n8n tools (" + ", ".join(tools[:6]) + ") - pick the Hoola tools it may use")
            return {"id": sid, "type": "ai", "op": "agent", "prompt": (sysm + "\n\n" if sysm else "") + str(txt)}
        if t == "chainSummarization":
            return {"id": sid, "type": "ai", "op": "summarise", "text": "{{" + prev + "}}"}
        if t == "informationExtractor":
            attrs = (p.get("attributes") or {}).get("attributes") or []
            fields = [{"name": _slug(a.get("name") or "field", set(), "field"), "description": str(a.get("description") or "")[:200]}
                      for a in attrs if a.get("name")]
            if not fields:
                fields = [{"name": "value", "description": "what to pull out"}]
                self.check(name, "Its fields came from a JSON schema in n8n - name the fields to pull out")
            return {"id": sid, "type": "ai", "op": "extract", "text": txt, "fields": fields}
        if t == "chainRetrievalQa":
            self.check(name, "It answered from an n8n vector store; here it answers from her Knowledge")
            return {"id": sid, "type": "ai", "op": "answer", "question": txt, "knowledge": True}
        return {"id": sid, "type": "ai", "op": "write", "prompt": txt}

    # ------------------------------------------------------------------ the whole workflow
    def _tidy(self, steps: list) -> None:
        """v0.999.264: the last pass - an n8n expression Hoola cannot read is shown as text (never a broken route),
        and a step's text is kept within what a step takes."""
        from ..agent import dhara_data as DD
        from ..agent.dhara_tools import _EXPR_CHARS
        plain = re.compile(r"^\s*[a-zA-Z_][a-zA-Z0-9_.\[\]\"' ]{0,200}\s*$")

        def fix(v: Any, label: str) -> Any:
            if isinstance(v, dict):
                return {k: fix(x, label) for k, x in v.items()}
            if isinstance(v, list):
                return [fix(x, label) for x in v]
            if not isinstance(v, str) or "{{" not in v:
                return v
            bad: list[str] = []

            def one(m: re.Match) -> str:
                b = m.group(1)
                if "$" not in b and (plain.match(b) or not DD.check(b.strip())):
                    return m.group(0)
                bad.append(b.strip()[:80])
                return "[n8n: " + b.strip()[:200] + "]"
            out = re.sub(r"\{\{(.{1,2000}?)\}\}", one, v, flags=re.S)
            if bad:
                self.check(label, "This expression could not be brought in - write it again in Hoola: " + "; ".join(bad[:3]))
            return out
        for st in steps:
            if not isinstance(st, dict):
                continue
            label = str(st.get("label") or st.get("id") or "")
            for k in list(st):
                if k in ("then", "else") or (k == "body" and st.get("type") == "loop"):
                    if isinstance(st[k], list):
                        self._tidy(st[k])
                elif k == "routes" and isinstance(st[k], list):
                    for r in st[k]:
                        if isinstance(r, dict) and isinstance(r.get("steps"), list):
                            self._tidy(r["steps"])
                elif k == "on_error" and isinstance(st[k], dict) and isinstance(st[k].get("steps"), list):
                    self._tidy(st[k]["steps"])
                elif k not in ("id", "type"):
                    st[k] = fix(st[k], label)
                    if isinstance(st[k], str) and len(st[k]) > _EXPR_CHARS:
                        st[k] = st[k][:_EXPR_CHARS - 10]
                        self.check(label, "Its text was longer than a Hoola step takes (2,000 characters); the end "
                                          "was cut")

    def run(self) -> dict:
        try:
            tname, kind, spec, settings = self.trigger()
            self.trig_app = _short((self.nodes.get(tname) or {}).get("type")).replace("Trigger", "")
        except (ValueError, TypeError, KeyError, AttributeError):   # v0.999.253: an unreadable start = by hand
            heads = [n for n in self.nodes if n not in self.inc]
            tname = heads[0] if heads else ""
            kind, spec, settings = "manual", {}, {}
            if tname:
                self.done.add(tname)
                self.check(tname, "its start could not be read - the route starts by hand now; set its start again")
        steps: list[dict] = []
        if tname:
            more, prev, cur = self.follow(tname, self.refs.get(tname, "vars"), set())
            steps += more
        else:
            heads = [n for n in self.nodes if n not in self.inc and _short(self.nodes[n].get("type")) != "stickyNote"]
            prev, cur = "vars", (heads[0] if heads else "")
            for h in heads[1:]:
                self.report["notes"].append(f"'{h}' was not joined to the start; it was left out")
        while cur:
            s, prev, cur = self.chain(cur, prev, set(), first=True)
            steps += s
        for nm, nd in self.nodes.items():
            if nm in self.subs or SUB_NODE.match(_short(nd.get("type"))):
                if nm not in self.done:
                    self.report["skipped"].append({"node": nm, "why": "A part of an n8n AI node (its model, memory or "
                                                   "a tool) - Hoola's AI step uses Hoola's own model"})
            elif nm not in self.done and _short(nd.get("type")) != "stickyNote":
                self.report["skipped"].append({"node": nm, "why": "It was not reached from the start"})
            elif _short(nd.get("type")) == "stickyNote" and nm not in self.done and nd.get("parameters", {}).get("content"):
                self.report["notes"].append("Note in n8n: " + str(nd["parameters"]["content"])[:300])
        self._tidy(steps)
        self.report["notes"].append("n8n runs a step once for every item; a Hoola step runs once with the whole list. "
                                    "Where a step must run per item, put it in a Repeat for each.")
        name = _slug(str(self.doc.get("name") or "n8n_route"), set(), "route")
        return {"name": name, "description": ("Brought in from n8n: " + str(self.doc.get("name") or ""))[:500],
                "trigger": kind, "trigger_spec": spec, "settings": settings, "steps": steps, "report": self.report,
                "counts": {k: len(v) for k, v in self.report.items()}}


def convert(raw: Any) -> dict:
    """The Hoola route an n8n export becomes, and the report - nothing is saved."""
    return _Conv(parse(raw)).run()


def bring_in(tenant: str, raw: Any, new_name: str = "", conversation_id: str = "") -> dict:
    """Convert and save it as a new route, switched OFF. Refuses a name that is taken (her routes are never
    overwritten by an import)."""
    from ..agent import dhara_tools as D
    from ..agent.tools import ToolError
    from . import triggers as TR
    plan = convert(raw)
    nm = str(new_name or plan["name"]).strip().lower().replace(" ", "_")
    if not D._PATH_RE.match(nm):
        raise N8nError("Give the route a name in lowercase_with_underscores")
    if D.get_workflow(tenant, name=nm) is not None:
        raise N8nError(f"A route named '{nm}' is already there - give this one another name")
    if not plan["steps"]:
        raise N8nError("This n8n workflow has no steps Hoola could bring in")
    try:
        st = D.validate_settings(plan["settings"], tenant) if plan["settings"] else None
    except ToolError as e:
        plan["report"]["check"].append({"node": "(settings)", "why": str(e)})
        st = None
    kind, spec = plan["trigger"], plan["trigger_spec"]
    try:
        spec = TR.validate(kind, spec, st)
    except Exception as e:   # noqa: BLE001 - a start Hoola cannot take: by hand, said in the report
        plan["report"]["check"].append({"node": "(start)", "why": f"{e} - it starts by hand for now"})
        kind, spec = "manual", {}
    try:
        steps = D.validate_steps(plan["steps"])
    except ToolError as e:
        raise N8nError(f"It could not be brought in: {e}")
    wf, _ = D.save_workflow(tenant, nm, plan["description"], kind, spec, steps, conversation_id, settings=st,
                            note="Brought in from n8n")
    D.set_enabled(tenant, wf["id"], False)
    if kind in ("schedule", "event"):
        con = D._con(tenant)
        try:
            con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (D.next_due(wf), wf["id"]))
            con.commit()
        finally:
            con.close()
    return {"ok": True, "workflow_id": wf["id"], "name": nm, "trigger": kind, "enabled": False,
            "report": plan["report"], "counts": plan["counts"]}
