"""v0.999.254 MAKE PARITY - bring in a Make scenario (the blueprint JSON Make exports: scenario menu > Export
Blueprint). Own code; it reads Make's published blueprint shape ({name, flow: [modules], metadata}).

- the first module -> the route's start (Custom webhook -> webhook; a watch module of Sheets / Gmail / RSS / Drive /
  Calendar -> an app event; anything else -> by hand, the module itself kept as a step)
- each module -> a Hoola step: Router (+ its filters), Iterator / Repeater + the aggregator that closes them (Array,
  Text, Numeric, Table, Aggregate to JSON) -> Repeat for each with collect, Set variable(s), Get variable(s),
  Increment function, Sleep, Switch, Compose a string, JSON / XML / CSV, Text parser (match pattern, replace,
  HTML to text), HTTP (every request module), Webhook response, Data store (all eight), Archive
- filters between modules -> filter steps; error handler routes (Break, Resume, Ignore, Commit, Rollback and the
  modules before them) -> the step's on_error with its own steps
- Make formulas ({{1.name}}, {{formatDate(now; "YYYY-MM-DD")}}, {{if(2.total > 100; "big"; "small")}}) -> Hoola
  expressions: module numbers become step names, ';' becomes ',', Make's 1-based [1] becomes [0]
- the scenario settings -> the route's settings
- anything Hoola cannot do the same way becomes a named stop step (a placeholder) and the report says so. Sign-ins
  are never in a blueprint - she adds them under Sign-ins. The route lands switched OFF.
"""
from __future__ import annotations

import json
import re
from typing import Any

BYTES_MAX = 1_000_000
MODULES_MAX = 400

_TRIGGER_EVENTS = {"google-sheets:watchRows": ("sheet_row", "spreadsheetId"), "google-sheets:watchNewRows": ("sheet_row", "spreadsheetId"),
                   "gmail:TriggerWatchEmails": ("email", ""), "gmail:watchEmails": ("email", ""), "email:TriggerNewEmail": ("email", ""),
                   "rss:TriggerWatchRss": ("rss", "url"), "rss:watchRssItems": ("rss", "url"),
                   "google-drive:watchFilesInAFolder": ("drive_file", "folderId"), "google-drive:TriggerWatchFiles": ("drive_file", "folderId"),
                   "google-calendar:watchEvents": ("calendar_event", ""), "google-forms:watchResponses": ("form_answer", "formId")}
_AGG = ("builtin:BasicAggregator", "util:TextAggregator", "util:NumericAggregator", "util:TableAggregator",
        "json:AggregateToJSON", "xml:AggregateToXML", "csv:CreateCSV", "csv:CreateAdvancedCSV")
_ITER = ("builtin:BasicFeeder", "builtin:BasicRepeater")
_OPS = {"exist": "exists", "notexist": "not_exists", "text:equal": "eq", "text:equal:ci": ("eq", True),
        "text:notequal": "ne", "text:notequal:ci": ("ne", True), "text:contain": "contains", "text:contain:ci": ("contains", True),
        "text:notcontain": "not_contains", "text:notcontain:ci": ("not_contains", True), "text:startwith": "starts_with",
        "text:startwith:ci": ("starts_with", True), "text:endwith": "ends_with", "text:endwith:ci": ("ends_with", True),
        "text:notstartwith": "", "text:notendwith": "", "text:pattern": "matches", "text:pattern:ci": ("matches", True),
        "text:notpattern": "", "number:equal": "eq", "number:notequal": "ne", "number:greater": "gt", "number:less": "lt",
        "number:greaterorequal": "gte", "number:lessorequal": "lte", "date:equal": "eq", "date:notequal": "ne",
        "date:greater": "after", "date:less": "before", "date:greaterorequal": "gte", "date:lessorequal": "lte",
        "time:equal": "eq", "time:greater": "gt", "time:less": "lt", "boolean:equal": "eq", "boolean:notequal": "ne",
        "array:contain": "contains", "array:notcontain": "not_contains", "array:contain:ci": ("contains", True),
        "array:length:equal": "length_eq", "array:length:greater": "length_gt", "array:length:less": "length_lt",
        "array:length:notequal": "", "array:length:greaterorequal": "", "array:length:lessorequal": ""}
_DS_OPS = {"datastore:AddRecord": "add", "datastore:UpdateRecord": "update", "datastore:GetRecord": "get",
           "datastore:ExistRecord": "exists", "datastore:DeleteRecord": "delete", "datastore:DeleteRecords": "delete_all",
           "datastore:SearchRecord": "search", "datastore:CountRecords": "count"}
_STR = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
_REF = re.compile(r"(?<![\w.\]])(\d+)((?:\.(?:`[^`]+`|[A-Za-z_$][\w$]*)|\[\d+\])*)")


class MakeError(ValueError):
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


def parse(raw: Any) -> dict:
    if isinstance(raw, str):
        if len(raw.encode()) > BYTES_MAX:
            raise MakeError("The Make blueprint is too big (up to 1 MB)")
        try:
            raw = json.loads(raw)
        except ValueError:
            raise MakeError("That is not a Make blueprint (in Make: the scenario's menu > Export Blueprint)")
    if isinstance(raw, dict) and isinstance(raw.get("blueprint"), dict):
        raw = raw["blueprint"]
    if not isinstance(raw, dict) or not isinstance(raw.get("flow"), list):
        raise MakeError("That is not a Make blueprint: it has no flow of modules")
    n = [0]

    def count(fl):
        for m in fl or []:
            n[0] += 1
            for rt in (m.get("routes") or []) if isinstance(m, dict) else []:
                count(rt.get("flow") if isinstance(rt, dict) else [])
            count(m.get("onerror") if isinstance(m, dict) else [])
    count(raw["flow"])
    if n[0] > MODULES_MAX:
        raise MakeError(f"Up to {MODULES_MAX} modules can be brought in at once")
    return raw


class _Conv:
    def __init__(self, doc: dict):
        self.doc = doc
        self.used: set[str] = set()
        self.root: dict[str, str] = {}       # module id -> the Hoola path its output is read from
        self.kind: dict[str, str] = {}       # module id -> Make module name
        self.report: dict[str, list] = {"converted": [], "check": [], "placeholders": [], "skipped": [], "notes": []}
        self.stores: set[str] = set()

    # ---------------------------------------------------------------- formulas
    def ex(self, v: Any, where: str = "") -> Any:
        if isinstance(v, dict):
            return {k: self.ex(x, where) for k, x in v.items()}
        if isinstance(v, list):
            return [self.ex(x, where) for x in v]
        if not isinstance(v, str) or "{{" not in v:
            return v
        return re.sub(r"\{\{(.*?)\}\}", lambda m: "{{" + self._inner(m.group(1), where) + "}}", v, flags=re.S)

    def _inner(self, src: str, where: str) -> str:
        parts, last = [], 0
        for m in _STR.finditer(src):
            parts.append(("code", src[last:m.start()]))
            parts.append(("str", m.group(0)))
            last = m.end()
        parts.append(("code", src[last:]))
        out = []
        for kind, t in parts:
            if kind == "str":
                out.append(t)
                continue
            t = t.replace(";", ",")
            t = re.sub(r"(?<![!<>=])=(?!=)", "==", t)
            t = re.sub(r"\s&\s", " and ", t)
            t = re.sub(r"\s\|\s", " or ", t)

            def ref(m):
                mid, path = m.group(1), m.group(2) or ""
                if mid not in self.root:
                    return m.group(0)
                base = self.root[mid]
                segs = re.findall(r"\.(`[^`]+`|[A-Za-z_$][\w$]*)|\[(\d+)\]", path)
                kind_ = self.kind.get(mid, "")
                out_p = base
                first = True
                for name, idx in segs:
                    if idx:
                        out_p += f"[{max(0, int(idx) - 1)}]"          # Make counts from 1
                        continue
                    nm = name.strip("`")
                    if first and kind_ in ("compose", "numagg", "builtin:BasicRepeater"):
                        first = False                            # {{N.value}} / {{N.result}} / {{N.i}} = the value itself
                        continue
                    if first and kind_.startswith("http:"):
                        nm = {"data": "json", "statusCode": "status"}.get(nm, nm)
                    if first and kind_ == "builtin:BasicAggregator":
                        nm = {"array": "results"}.get(nm, nm)
                    if first and kind_ == "util:FunctionIncrement":
                        nm = {"i": "value"}.get(nm, nm)
                    if first and kind_.startswith("datastore:Get") and nm not in ("key",):
                        out_p += ".data"
                    first = False
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nm):
                        out_p += "." + nm
                    else:
                        out_p += "[" + json.dumps(nm) + "]"
                return out_p
            out.append(_REF.sub(ref, t))
        res = "".join(out).strip()
        try:
            from ..agent import dhara_data as DD
            why = DD.check(res) if not re.fullmatch(r"[a-z_][\w.\[\]\"']*", res) else ""
        except Exception:   # noqa: BLE001
            why = ""
        if why:
            self.report["check"].append({"node": where, "why": f"The formula {{{{{src.strip()[:60]}}}}} needs a look: {why}"})
        return res

    # ---------------------------------------------------------------- pieces
    def _name(self, m: dict, fallback: str = "") -> str:
        md = (m.get("metadata") or {}).get("designer") or {}
        return str(md.get("name") or fallback or m.get("module") or "step")

    def sid(self, m: dict, hint: str = "") -> str:
        mod = str(m.get("module") or "")
        base = hint or (self._name(m) if (m.get("metadata") or {}).get("designer", {}).get("name") else mod.split(":")[-1])
        return _slug(base, self.used)

    def place(self, m: dict, why: str) -> dict:
        mod = str(m.get("module") or "?")
        name = self._name(m)
        self.report["placeholders"].append({"node": f"{m.get('id')} {name}", "type": mod, "why": why})
        sid = _slug(f"redo {mod.split(':')[0]} {m.get('id')}", self.used)
        self.root[str(m.get("id"))] = f"steps.{sid}.output"
        self.kind[str(m.get("id"))] = mod
        return {"id": sid, "type": "stop", "as": "error", "label": ("Redo: " + name)[:80],
                "message": f"Redo this step in Hoola: module {m.get('id')} '{name}' ({mod}) came from Make - {why}"[:480],
                "make": {"module": mod}}

    def conds(self, f: Any, where: str) -> dict | None:
        """Make filter conditions: an outer list of OR groups, each a list of AND conditions {a, o, b}."""
        if not isinstance(f, dict) or not isinstance(f.get("conditions"), list):
            return None
        ors = []
        for grp in f["conditions"]:
            ands = []
            for c in grp if isinstance(grp, list) else []:
                if not isinstance(c, dict):
                    continue
                o = _OPS.get(str(c.get("o") or ""), None)
                ci = False
                if isinstance(o, tuple):
                    o, ci = o
                if not o:
                    self.report["check"].append({"node": where, "why": f"A filter test '{c.get('o')}' has no twin here - "
                                                 "it was left out; set it again"})
                    continue
                cond = {"left": self.ex(str(c.get("a") or ""), where), "op": o}
                if o not in ("exists", "not_exists", "empty", "not_empty", "is_true", "is_false"):
                    cond["right"] = self.ex(c.get("b") if c.get("b") is not None else "", where)
                if ci:
                    cond["ci"] = True
                ands.append(cond)
            if ands:
                ors.append(ands[0] if len(ands) == 1 else {"all": ands})
        if not ors:
            return None
        return ors[0] if len(ors) == 1 else {"any": ors}

    def kv(self, v: Any) -> dict:
        if isinstance(v, dict):
            return v
        out = {}
        for x in v or []:
            if isinstance(x, dict) and str(x.get("name") or x.get("key") or "").strip():
                out[str(x.get("name") or x.get("key"))] = x.get("value")
        return out

    def on_error(self, m: dict, where: str) -> dict | None:
        oe = m.get("onerror")
        if not isinstance(oe, list) or not oe:
            return None
        directive = None
        hs = []
        for h in oe:
            mod = str((h or {}).get("module") or "")
            if mod.startswith("builtin:") and mod.split(":")[1] in ("Break", "Resume", "Ignore", "Commit", "Rollback"):
                directive = h
            else:
                hs.append(h)
        out: dict[str, Any] = {}
        if hs:
            out["steps"] = self.flow(hs, where + " error handler")
        if directive is not None:
            d = directive["module"].split(":")[1].lower()
            out["do"] = d
            p = {**(directive.get("parameters") or {}), **(directive.get("mapper") or {})}
            if d == "break":
                if p.get("retry") is False:
                    out["retries"] = 0
                else:
                    out["retries"] = int(p.get("count") or 3)
                    out["wait_min"] = max(1, int(p.get("interval") or 15))
            if d == "resume":
                out["value"] = self.ex(p, where)
        elif hs:
            out["do"] = "ignore"
        self.report["converted"].append({"node": where, "type": "error handler", "as": f"on_error {out.get('do')}"})
        return out

    # ---------------------------------------------------------------- one module
    def module(self, m: dict) -> list[dict]:
        mod = str(m.get("module") or "")
        mid = str(m.get("id"))
        name = self._name(m)
        where = f"{mid} {name}"
        p = {**(m.get("parameters") or {}), **(m.get("mapper") or {})}
        self.kind[mid] = mod
        conv = lambda typ: self.report["converted"].append({"node": where, "type": mod, "as": typ})   # noqa: E731
        st: dict[str, Any] | None = None
        sid = None

        named = bool(((m.get("metadata") or {}).get("designer") or {}).get("name"))

        def mk(typ: str, label: str, **kw) -> dict:
            nonlocal sid
            sid = self.sid(m) if named else _slug(f"{label} {mid}", self.used)
            self.root[mid] = f"steps.{sid}.output"
            conv(label)
            return {"id": sid, "type": typ, "label": (name if named else label[:1].upper() + label[1:])[:80], **kw}

        if mod in ("util:SetVariable", "util:SetVariable2"):
            nm = _slug(str(p.get("name") or "value"), set(), "value")
            st = mk("set", "set a value", name=nm, value=self.ex(p.get("value"), where))
            self.root[mid] = "vars"
            self.kind[mid] = "var"
            # a later {{N.name}} reads vars.name
        elif mod == "util:SetVariables":
            vals = {_slug(str(x.get("name") or "v"), set(), "value"): self.ex(x.get("value"), where)
                    for x in (p.get("variables") or []) if isinstance(x, dict)}
            st = mk("var", "set several values", op="set_many", values=vals)
            self.root[mid] = "vars"
        elif mod in ("util:GetVariable", "util:GetVariable2"):
            nm = _slug(str(p.get("name") or "value"), set(), "value")
            st = mk("var", "get a value", op="get", name=nm)
            self.root[mid] = "vars"
        elif mod == "util:GetVariables":
            names = [_slug(str(x.get("name") if isinstance(x, dict) else x), set(), "value") for x in (p.get("variables") or [])]
            st = mk("var", "get values", op="get_many", names=names)
            self.root[mid] = "vars"
        elif mod == "util:FunctionIncrement":
            st = mk("var", "increment", op="increment", name=f"counter_{mid}",
                    reset="run" if str(p.get("reset") or "").lower() in ("scenario", "run", "cycle", "1", "2") else "never")
            self.root[mid] = f"steps.{sid}.output"
            self.report["notes"].append(f"Module {mid}: its counter is read as {{{{steps.{sid}.output.value}}}} (Make's 'i')")
        elif mod == "util:FunctionSleep":
            st = mk("wait", "wait", amount=self.ex(p.get("duration") or 1, where), unit="seconds")
        elif mod == "util:Switcher":
            cases = []
            for c in p.get("casesTable") or []:
                if isinstance(c, dict):
                    cases += [json.dumps(c.get("pattern")), json.dumps(c.get("output"))]
            inp = self.ex(str(p.get("input") or ""), where)
            inp = inp[2:-2] if inp.startswith("{{") and inp.endswith("}}") else json.dumps(inp)
            els = json.dumps(p.get("elseOutput")) if p.get("useElseOutput", True) and p.get("elseOutput") is not None else "null"
            st = mk("set", "switch", name=f"switch_{mid}", value="{{switch(" + ", ".join([inp] + cases + [els]) + ")}}")
            self.root[mid] = f"vars.switch_{mid}"
            self.kind[mid] = "compose"
        elif mod == "util:ComposeTransformer":
            st = mk("set", "compose a string", name=f"text_{mid}", value=self.ex(p.get("value") or "", where))
            self.root[mid] = f"vars.text_{mid}"
            self.kind[mid] = "compose"
        elif mod == "json:ParseJSON":
            st = mk("data", "read JSON", op="text", action="json_parse", value=self.ex(p.get("json") or "", where))
        elif mod in ("json:CreateJSON", "json:TransformToJSON"):
            st = mk("data", "make JSON", op="text", action="json_text", value=self.ex(p.get("object") if mod.endswith("TransformToJSON") else
                                                                               {k: x for k, x in p.items() if k not in ("type", "space")}, where))
        elif mod == "xml:ParseXML":
            st = mk("data", "read XML", op="text", action="xml_to_data", value=self.ex(p.get("xml") or "", where))
        elif mod == "xml:CreateXML":
            st = mk("data", "make XML", op="text", action="data_to_xml", value=self.ex({k: x for k, x in p.items() if k != "type"}, where))
        elif mod == "csv:ParseCSV":
            st = mk("data", "read CSV", op="text", action="csv_to_rows", value=self.ex(p.get("csv") or "", where),
                    separator=str(p.get("delimiter") or p.get("delimiterType") or ",")[:1] if str(p.get("delimiterType") or "") not in ("tab",) else "\t")
        elif mod == "regexp:Parser":
            st = mk("data", "match pattern", op="text", action="regex_match", value=self.ex(p.get("text") or "", where),
                    pattern=str(p.get("pattern") or ""), **{"global": bool(p.get("global", False)),
                                                            "case_sensitive": bool(p.get("sensitive", True)),
                                                            "multiline": bool(p.get("multiline", False)),
                                                            "singleline": bool(p.get("singleline", False))})
            self.report["notes"].append(f"Module {mid}: Make gives one bundle per match; here the matches are one list "
                                        f"({{{{steps.{sid}.output}}}}), each with $1, $2 ...")
        elif mod == "regexp:Replace":
            st = mk("data", "replace", op="text", action="regex_replace", value=self.ex(p.get("text") or "", where),
                    pattern=str(p.get("pattern") or ""), replace=self.ex(p.get("value") or "", where),
                    **{"global": bool(p.get("global", True)), "case_sensitive": bool(p.get("sensitive", True))})
        elif mod == "regexp:HTMLToText":
            st = mk("data", "HTML to text", op="text", action="html_text", value=self.ex(p.get("html") or "", where))
        elif mod in ("markdown:Compile", "markdown:ConvertMarkdownToHtml"):
            st = mk("data", "markdown to HTML", op="text", action="markdown_to_html", value=self.ex(p.get("markdown") or "", where))
        elif mod.startswith("http:"):
            st = self.http(m, mod, p, where, mk)
        elif mod == "gateway:WebhookRespond":
            st = mk("respond", "answer the caller", status=self.ex(p.get("status") or 200, where), body=self.ex(p.get("body") or "", where))
        elif mod in _DS_OPS:
            op = _DS_OPS[mod]
            store = f"store_{p.get('datastore') or 'make'}"
            self.stores.add(store)
            kw: dict[str, Any] = {"op": op, "store": store}
            if p.get("key") not in (None, ""):
                kw["key"] = self.ex(p.get("key"), where)
            if op in ("add", "update"):
                kw["data"] = self.ex(p.get("data") or {}, where)
                if op == "add" and p.get("overwrite") is False:
                    kw["overwrite"] = False
                if op == "update" and p.get("insert"):
                    kw["insert_missing"] = True
            if op == "delete_all":
                kw["confirm"] = True
            if op in ("search", "count") and p.get("filter"):
                f = self.conds({"conditions": p.get("filter")}, where)
                if f:
                    kw["filter"] = f
            if op == "search" and p.get("limit"):
                kw["limit"] = self.ex(p.get("limit"), where)
            st = mk("store", "data store " + op, **kw)
            if op == "search":
                self.report["notes"].append(f"Module {mid}: Make gives one bundle per record; here the records are one list")
        elif mod == "archive:CreateArchive":
            st = mk("data", "make a ZIP", op="file", action="zip", items=self.ex(p.get("files") or "", where), name="files")
            self.report["check"].append({"node": where, "why": "Point the ZIP at the files' ids from earlier steps"})
        elif mod in ("archive:ExtractArchive", "archive:Extract"):
            st = mk("data", "open a ZIP", op="file", action="unzip", file_id=self.ex(p.get("data") or "", where))
            self.report["check"].append({"node": where, "why": "Point it at the ZIP file's id from an earlier step"})
        elif mod in ("builtin:BasicRouter",):
            st = self.router(m, where)
            conv("switch (every way whose filter passes runs)")
        else:
            app = mod.split(":")[0]
            return [self.place(m, f"Hoola has no '{app}' module - use one of Hoola's tools for {app} (Add a step > search "
                                  f"'{app}') or a Web request to its API")]
        if st is None:
            return []
        oe = self.on_error(m, where)
        if oe:
            st["on_error"] = oe
        return [st]

    def http(self, m: dict, mod: str, p: dict, where: str, mk) -> dict:
        act = "download" if mod.endswith("GetFile") or mod.endswith("DownloadFile") else \
            "resolve" if "Resolve" in mod else "request"
        kw: dict[str, Any] = {"action": act, "url": self.ex(p.get("url") or "", where),
                              "method": str(p.get("method") or "get").upper()}
        hd = self.kv(p.get("headers"))
        if hd:
            kw["headers"] = self.ex(hd, where)
        q = self.kv(p.get("qs"))
        if q:
            kw["query"] = self.ex(q, where)
        bt = str(p.get("bodyType") or "")
        if bt == "raw":
            ct = str(p.get("contentType") or "application/json")
            if "json" in ct:
                kw["body_type"] = "raw" if "{{" in str(p.get("data") or "") else "json"
                if kw["body_type"] == "json":
                    try:
                        kw["body"] = json.loads(p.get("data") or "{}")
                    except ValueError:
                        kw["body_type"] = "raw"
                if kw["body_type"] == "raw":
                    kw["body"] = self.ex(p.get("data") or "", where)
                    kw["content_type"] = "application/json"
            else:
                kw["body_type"], kw["body"], kw["content_type"] = "raw", self.ex(p.get("data") or "", where), ct
        elif bt in ("x_www_form_urlencoded", "urlencoded"):
            kw["body_type"], kw["form"] = "form", self.ex(self.kv(p.get("fields")), where)
        elif bt in ("multipart_form_data", "multipart"):
            kw["body_type"], kw["form"] = "multipart", self.ex({k: v for k, v in self.kv(p.get("fields")).items()
                                                               if not isinstance(v, dict)}, where)
            self.report["check"].append({"node": where, "why": "File fields of a multipart request: add the files' ids "
                                         "under Files"})
        if p.get("parseResponse") is False:
            kw["parse"] = False
        if p.get("timeout"):
            kw["timeout"] = self.ex(p.get("timeout"), where)
        if p.get("followRedirect") is False:
            kw["redirects"] = False
        if p.get("shareCookies"):
            kw["share_cookies"] = True
        if p.get("gzip"):
            kw["compressed"] = True
        if p.get("handleErrors") is False:
            kw["fail_on_error"] = False
        if "Auth" in mod or p.get("authenticationType") or p.get("username") or p.get("apiKey"):
            self.report["check"].append({"node": where, "why": "It signs in - Make keeps sign-ins out of blueprints. Save "
                                         "one under Sign-ins and pick it in this step"})
        return mk("http", "web request" if act == "request" else ("download a file" if act == "download" else "resolve a URL"), **kw)

    def router(self, m: dict, where: str) -> dict:
        sid = self.sid(m) if ((m.get("metadata") or {}).get("designer") or {}).get("name") else _slug(f"router {m.get('id')}", self.used)
        self.root[str(m.get("id"))] = f"steps.{sid}.output"
        routes = []
        for i, rt in enumerate(m.get("routes") or []):
            fl = list((rt or {}).get("flow") or [])
            flt = None
            if fl and isinstance(fl[0], dict) and fl[0].get("filter"):
                flt = self.conds(fl[0]["filter"], where + f" way {i + 1}")
                fl[0] = {**fl[0], "filter": None}
            steps = self.flow(fl, where + f" way {i + 1}")
            if not steps:
                steps = [{"id": _slug(f"{sid}_way_{i + 1}_empty", self.used), "type": "set", "name": f"way_{i + 1}", "value": True}]
            label = (((fl[0].get("metadata") or {}).get("designer") or {}).get("name") if fl else "") or f"Way {i + 1}"
            routes.append({"label": str((((m.get("routes") or [])[i] or {}).get("label")) or label)[:80], "steps": steps,
                           **({"filter": flt} if flt else {})})
        if len(routes) > 8:
            self.report["check"].append({"node": where, "why": f"Make's router had {len(routes)} routes; a Hoola switch "
                                         "has up to 8 - the rest were left out"})
            routes = routes[:8]
        if not routes:
            routes = [{"label": "Way 1", "steps": [{"id": _slug(sid + "_way", self.used), "type": "set", "name": "way", "value": True}]}]
        return {"id": sid, "type": "router", "label": self._name(m, "Router")[:80], "routes": routes}

    # ---------------------------------------------------------------- a run of modules
    def flow(self, mods: list, where: str = "") -> list[dict]:
        out: list[dict] = []
        i = 0
        mods = [x for x in mods or [] if isinstance(x, dict)]
        while i < len(mods):
            m = mods[i]
            mod = str(m.get("module") or "")
            if m.get("filter"):
                f = self.conds(m["filter"], f"{m.get('id')} {self._name(m)}")
                if f:
                    out.append({"id": _slug(f"filter_before_{m.get('id')}", self.used), "type": "filter",
                                "label": str((m.get("filter") or {}).get("name") or "Filter")[:80], "filter": f})
            if mod in _ITER:
                j = i + 1
                depth = 0
                while j < len(mods):
                    mj = str(mods[j].get("module") or "")
                    if mj in _ITER:
                        depth += 1
                    elif mj in _AGG:
                        if depth == 0:
                            break
                        depth -= 1
                    j += 1
                out.append(self.loop(m, mods[i + 1:j], mods[j] if j < len(mods) else None))
                i = j + 1
                continue
            if mod in _AGG:
                self.report["check"].append({"node": f"{m.get('id')} {self._name(m)}", "why": "An aggregator with no "
                                             "iterator before it - it was left out"})
                i += 1
                continue
            out.extend(self.module(m))
            i += 1
        return out

    def loop(self, it: dict, body: list, agg: dict | None) -> dict:
        mod = str(it.get("module"))
        mid = str(it.get("id"))
        p = {**(it.get("parameters") or {}), **(it.get("mapper") or {})}
        sid = self.sid(it, ("repeat " if mod.endswith("Repeater") else "each ") + mid) if not \
            ((it.get("metadata") or {}).get("designer") or {}).get("name") else self.sid(it)
        self.kind[mid] = mod
        self.root[mid] = "item"
        st: dict[str, Any] = {"id": sid, "type": "loop",
                              "label": self._name(it, "Repeat" if mod.endswith("Repeater") else "Repeat for each")[:80]}
        if mod.endswith("Repeater"):
            st["repeat"] = {"times": self.ex(p.get("repeats") or 1, ""), "start": self.ex(p.get("start") or 1, ""),
                            "step": self.ex(p.get("step") or 1, "")}
            self.root[mid] = "item"           # Make's {{N.i}} -> {{item}}
            self.report["notes"].append(f"Module {mid}: the repeater's i is {{{{item}}}}")
        else:
            st["items"] = self.ex(p.get("array") or "", f"{mid} iterator")
        self.report["converted"].append({"node": f"{mid} {self._name(it)}", "type": mod, "as": "repeat for each"})
        st["body"] = self.flow(body, f"{mid} loop") or [{"id": _slug(sid + "_round", self.used), "type": "set",
                                                         "name": "round", "value": "{{item}}"}]
        if agg is not None:
            amod = str(agg.get("module"))
            aid = str(agg.get("id"))
            ap = {**(agg.get("parameters") or {}), **(agg.get("mapper") or {})}
            self.kind[aid] = amod
            if amod == "util:TextAggregator":
                st["collect"] = self.ex(ap.get("value") or "{{item}}", aid)
                st["join"] = str(ap.get("rowSeparator") or "\n").replace("\\n", "\n") if str(ap.get("rowSeparator")) != "other" \
                    else str(ap.get("otherRowSeparator") or "\n")
                self.root[aid] = f"steps.{sid}.output"
            elif amod == "util:NumericAggregator":
                st["collect"] = self.ex(ap.get("value") or "{{item}}", aid)
                self.root[aid] = f"steps.{sid}.output"
                fn = str(ap.get("fn") or "SUM").lower()
                self.report["notes"].append(f"Module {aid}: its {fn.upper()} is worked out by a Summarise step after the loop")
            elif amod in ("util:TableAggregator", "csv:CreateCSV", "csv:CreateAdvancedCSV", "json:AggregateToJSON", "xml:AggregateToXML"):
                st["collect"] = self.ex(ap.get("value") or ap.get("fields") or "{{item}}", aid) if not isinstance(ap.get("value"), dict) \
                    else self.ex(ap["value"], aid)
                self.root[aid] = f"steps.{sid}.output"
            else:                                         # builtin:BasicAggregator (Array aggregator)
                fields = ap.get("value") or ap.get("fields")
                st["collect"] = self.ex(fields if isinstance(fields, (dict, str)) and fields else "{{item}}", aid)
                self.root[aid] = f"steps.{sid}.output"
            self.report["converted"].append({"node": f"{aid} {agg.get('metadata', {}).get('designer', {}).get('name') or amod}",
                                             "type": amod, "as": "collected by the loop"})
            out = [st]
            if amod == "util:NumericAggregator":
                fn = {"sum": "sum", "avg": "avg", "average": "avg", "count": "count", "min": "min", "max": "max"}.get(
                    str(ap.get("fn") or "SUM").lower(), "sum")
                nid = _slug(f"total_{aid}", self.used)
                self.root[aid] = f"steps.{nid}.output"
                self.kind[aid] = "numagg"
                return {"_multi": out + [{"id": nid, "type": "data", "op": "aggregate", "items": f"{{{{steps.{sid}.output.results}}}}",
                                          "field": "", "how": fn}]}
            if amod in ("util:TableAggregator",):
                tid = _slug(f"table_{aid}", self.used)
                self.root[aid] = f"steps.{tid}.output"
                self.kind[aid] = "compose"
                return {"_multi": out + [{"id": tid, "type": "data", "op": "text", "action": "rows_to_table",
                                          "value": f"{{{{steps.{sid}.output.results}}}}",
                                          "column_sep": str(ap.get("columnSeparator") or "\t"),
                                          "row_sep": str(ap.get("rowSeparator") or "\n")}]}
            if amod in ("csv:CreateCSV", "csv:CreateAdvancedCSV"):
                tid = _slug(f"csv_{aid}", self.used)
                self.root[aid] = f"steps.{tid}.output"
                self.kind[aid] = "compose"
                return {"_multi": out + [{"id": tid, "type": "data", "op": "text", "action": "rows_to_csv",
                                          "value": f"{{{{steps.{sid}.output.results}}}}"}]}
            if amod in ("json:AggregateToJSON", "xml:AggregateToXML"):
                tid = _slug(f"{'json' if 'JSON' in amod else 'xml'}_{aid}", self.used)
                self.root[aid] = f"steps.{tid}.output"
                self.kind[aid] = "compose"
                return {"_multi": out + [{"id": tid, "type": "data", "op": "text",
                                          "action": "json_text" if "JSON" in amod else "data_to_xml",
                                          "value": f"{{{{steps.{sid}.output.results}}}}"}]}
        return st

    # ---------------------------------------------------------------- the whole scenario
    def start(self, first: dict) -> tuple[str, dict, bool]:
        mod = str(first.get("module") or "")
        mid = str(first.get("id"))
        p = {**(first.get("parameters") or {}), **(first.get("mapper") or {})}
        self.kind[mid] = mod
        if mod in ("gateway:CustomWebHook", "gateway:CustomWebhook"):
            self.root[mid] = "vars.body"
            self.report["converted"].append({"node": f"{mid} webhook", "type": mod, "as": "start: webhook"})
            self.report["notes"].append("It starts when data is sent to its address. Hoola makes a new address - "
                                        "point the app that called Make's webhook at it")
            return "webhook", {}, True
        if mod in ("gateway:CustomMailHook",):
            self.root[mid] = "vars.event"
            self.report["check"].append({"node": f"{mid} mailhook", "why": "A mailhook - start it from new email in your "
                                         "inbox instead (an app event: new email); it starts by hand for now"})
            return "manual", {}, True
        if mod in _TRIGGER_EVENTS:
            app, key = _TRIGGER_EVENTS[mod]
            sp: dict[str, Any] = {"app": app}
            if app == "sheet_row":
                sp["spreadsheet"] = str(p.get(key) or p.get("spreadsheet") or "")
                if p.get("sheetId") or p.get("sheet"):
                    sp["tab"] = str(p.get("sheetId") or p.get("sheet"))
            elif app == "rss":
                sp["url"] = str(p.get(key) or "")
            elif app == "form_answer":
                sp["form"] = str(p.get(key) or "")
            elif app == "drive_file" and p.get(key):
                sp["folder"] = str(p.get(key))
            self.root[mid] = "vars.event"
            self.report["converted"].append({"node": f"{mid} {self._name(first)}", "type": mod, "as": f"start: app event ({app})"})
            return "event", sp, True
        if mod in ("builtin:BasicFeeder",) or not mod:
            return "manual", {}, False
        if mod.endswith(":watch") or ":watch" in mod.lower() or "trigger" in mod.lower():
            self.root[mid] = "vars.event"
            self.report["check"].append({"node": f"{mid} {self._name(first)}", "why": f"Make's '{mod}' watches an app Hoola "
                                         "does not watch - it starts by hand (or on a schedule) for now; read the app "
                                         "with a tool step"})
            return "manual", {}, True
        self.report["notes"].append("Make started this scenario on a schedule or by hand - set the start's schedule here")
        return "manual", {}, False

    def run(self) -> dict:
        flow = [x for x in self.doc.get("flow") or [] if isinstance(x, dict)]
        if not flow:
            raise MakeError("This Make blueprint has no modules")
        kind, spec, used_first = self.start(flow[0])
        body = flow[1:] if used_first else flow
        steps = []
        for s in self.flow(body, ""):
            steps.extend(s["_multi"] if "_multi" in s else [s])

        def unmulti(lst):
            out = []
            for s in lst or []:
                if "_multi" in s:
                    out.extend(unmulti(s["_multi"]))
                    continue
                for k in ("then", "else", "body", "fallback"):
                    if isinstance(s.get(k), list) and (k != "body" or s.get("type") == "loop"):
                        s[k] = unmulti(s[k])
                for rt in s.get("routes") or []:
                    rt["steps"] = unmulti(rt.get("steps"))
                oe = s.get("on_error")
                if isinstance(oe, dict) and oe.get("steps"):
                    oe["steps"] = unmulti(oe["steps"])
                out.append(s)
            return out
        steps = unmulti(steps)
        meta = ((self.doc.get("metadata") or {}).get("scenario")) or {}
        settings: dict[str, Any] = {}
        if meta.get("sequential"):
            settings["in_order"] = True
        if meta.get("confidential"):
            settings["confidential"] = True
        if "dlq" in meta:
            settings["keep_incomplete"] = bool(meta.get("dlq"))
        if meta.get("autoCommit"):
            settings["auto_commit"] = True
        if meta.get("maxErrors"):
            settings["stop_after_errors"] = max(1, min(int(meta.get("maxErrors") or 3), 20))
        if meta.get("roundtrips") and int(meta.get("roundtrips") or 1) > 1:
            self.report["notes"].append(f"Make ran up to {meta['roundtrips']} cycles a run; Hoola starts one run per call "
                                        "(an app event starts one run per new item)")
        if self.stores:
            self.report["check"].append({"node": "(data stores)", "why": "Make the data store(s) "
                                         + ", ".join(sorted(self.stores)) + " on the Data stores page (or rename them in "
                                         "the steps to one of yours) - their records stay in Make"})
        name = _slug(str(self.doc.get("name") or "make_route"), set(), "route")
        return {"name": name, "description": ("Brought in from Make: " + str(self.doc.get("name") or ""))[:500],
                "trigger": kind, "trigger_spec": spec, "settings": settings, "steps": steps, "report": self.report,
                "stores": sorted(self.stores), "counts": {k: len(v) for k, v in self.report.items()}}


def convert(raw: Any) -> dict:
    """The Hoola route a Make blueprint becomes, and the report - nothing is saved."""
    return _Conv(parse(raw)).run()


def bring_in(tenant: str, raw: Any, new_name: str = "", conversation_id: str = "") -> dict:
    """Convert and save it as a new route, switched OFF; a name that is taken is refused."""
    from ..agent import dhara_tools as D
    from ..agent.tools import ToolError
    from . import triggers as TR
    plan = convert(raw)
    nm = str(new_name or plan["name"]).strip().lower().replace(" ", "_")
    if not D._PATH_RE.match(nm):
        raise MakeError("Give the route a name in lowercase_with_underscores")
    if D.get_workflow(tenant, name=nm) is not None:
        raise MakeError(f"A route named '{nm}' is already there - give this one another name")
    if not plan["steps"]:
        raise MakeError("This Make scenario has no steps Hoola could bring in")
    try:
        st = D.validate_settings(plan["settings"], tenant) if plan["settings"] else None
    except ToolError as e:
        plan["report"]["check"].append({"node": "(settings)", "why": str(e)})
        st = None
    kind, spec = plan["trigger"], plan["trigger_spec"]
    try:
        spec = TR.validate(kind, spec, st)
    except Exception as e:   # noqa: BLE001
        plan["report"]["check"].append({"node": "(start)", "why": f"{e} - it starts by hand for now"})
        kind, spec = "manual", {}
    try:
        steps = D.validate_steps(plan["steps"])
    except ToolError as e:
        raise MakeError(f"It could not be brought in: {e}")
    wf, _ = D.save_workflow(tenant, nm, plan["description"], kind, spec, steps, conversation_id, settings=st,
                            note="Brought in from Make")
    D.set_enabled(tenant, wf["id"], False)
    if kind in ("schedule", "event"):
        con = D._con(tenant)
        try:
            con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (D.next_due(wf), wf["id"]))
            con.commit()
        finally:
            con.close()
    return {"ok": True, "workflow_id": wf["id"], "name": nm, "trigger": kind, "enabled": False,
            "report": plan["report"], "counts": plan["counts"], "stores": plan["stores"]}
