"""Working on top of a helpdesk she already has - "layer" mode (G12 of docs/SUPPORT_GLOBAL_PLAN.md).

Through each helpdesk's own official API, with a key she types in the app (sealed, never shown again):
Chatwoot, Zendesk, Freshdesk, ServiceNow (incidents) and Jira Service Management. Every few minutes (or when her
helpdesk pings the webhook) Hoola reads new and changed tickets and, by her switches:
  - sorts them: category, priority, language and her queue, written back as tags / labels (+ priority if she allows);
  - adds a SUGGESTED REPLY as an internal note with where it came from (her approved knowledge), or a note that a person
    should take it and why; a public reply only when she turned public replies on AND that topic's trust level is
    "answer alone";
  - summarises long threads as an internal note;
  - answers "where is my ticket" on Hoola's own channels from her helpdesk's own status;
  - reminds her (once a day) about tickets where the customer is still waiting past her hours;
  - closes a ticket only when her rule allows it (the customer confirmed it is fixed).
Tickets stay in her tool. Hoola never deletes anything there. Every write is a note / tag her tool records under the
key's user, and logged here too (`seva_layer_log`).
NOT BUILT (need an OAuth app registered by Newtika first): Zoho Desk, Salesforce Service Cloud, HubSpot, Intercom.
Built from each company's public API documentation; NOT VERIFIED against a live account of any of them.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.seva.layer")


class LayerError(Exception):
    pass


class SevaLayer(Base):
    __tablename__ = "seva_layer"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="")
    base: Mapped[str] = mapped_column(String(300), default="")
    sealed: Mapped[str] = mapped_column(Text, default="")              # {user, token, account}
    hints: Mapped[str] = mapped_column(Text, default="{}")
    settings: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="new")     # new | ok | error | off
    note: Mapped[str] = mapped_column(Text, default="")
    hook: Mapped[str] = mapped_column(String(48), default="", index=True)
    cursor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SevaLayerTicket(Base):
    __tablename__ = "seva_layer_tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("slt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ext_id: Mapped[str] = mapped_column(String(80), index=True)
    number: Mapped[str] = mapped_column(String(40), default="")
    customer: Mapped[str] = mapped_column(String(200), default="", index=True)
    category: Mapped[str] = mapped_column(String(30), default="")
    lang: Mapped[str] = mapped_column(String(10), default="")
    queue: Mapped[str] = mapped_column(String(30), default="")
    decision: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(16), default="")
    raw_status: Mapped[str] = mapped_column(String(40), default="")
    msgs: Mapped[int] = mapped_column(Integer, default=0)
    summarized_at: Mapped[int] = mapped_column(Integer, default=0)       # message count of the last summary
    answered_at: Mapped[int] = mapped_column(Integer, default=0)         # message count Hoola last suggested for
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    waiting_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaLayerLog(Base):
    __tablename__ = "seva_layer_log"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sll"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ext_id: Mapped[str] = mapped_column(String(80), default="")
    action: Mapped[str] = mapped_column(String(20), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ok: Mapped[int] = mapped_column(Integer, default=1)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


_READY: set = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in (SevaLayer, SevaLayerTicket, SevaLayerLog):
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service
    return service


def _j(v, d):
    try:
        return json.loads(v) if v else d
    except Exception:   # noqa: BLE001
        return d


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _http(method, url, headers=None, json_body=None, auth=None):
    from . import channels as CH
    return CH._http(method, url, headers=headers or {}, json_body=json_body, auth=auth)


SIGN = "\n\n— Hoola (automatic, suggested by your AI support assistant)"
DEFAULTS = {"tags": True, "priority": False, "notes": True, "public_replies": False, "summaries": True, "summary_after": 6,
            "close_on_confirm": False, "remind_h": 8}


# ---------------------------------------------------------------- the helpdesks (each company's documented REST API)
class Desk:
    kind, name = "", ""
    fields = ("base", "token")
    help = ""

    def __init__(self, base: str, creds: dict):
        self.base = base.rstrip("/")
        self.c = creds

    def _get(self, path, **kw):
        code, body = _http("GET", self.base + path, self.headers(), auth=self.auth(), **kw)
        if code >= 300:
            raise LayerError(f"{self.name} answered {code} on {path.split('?')[0]}.")
        return body

    def _send(self, method, path, body):
        code, out = _http(method, self.base + path, self.headers(), json_body=body, auth=self.auth())
        if code >= 300:
            raise LayerError(f"{self.name} refused {method} {path.split('?')[0]} ({code}).")
        return out

    def headers(self) -> dict:
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def auth(self):
        return None

    # normalized: {ext_id, number, subject, text, messages:[{who: customer|agent|note|system, text}], status, raw_status,
    #              priority, tags, requester:{name,email,phone}, updated}
    def check(self) -> str: ...
    def recent(self, since: datetime | None) -> list[dict]: ...
    def thread(self, t: dict) -> list[dict]: ...
    def note(self, t: dict, text: str) -> None: ...
    def reply(self, t: dict, text: str) -> None: ...
    def tag(self, t: dict, tags: list[str]) -> None: ...
    def set_priority(self, t: dict, p: str) -> None: ...
    def solve(self, t: dict, text: str) -> None: ...
    def find(self, email: str = "", phone: str = "") -> list[dict]: ...


def _norm_status(raw: str) -> str:
    r = str(raw or "").lower()
    for k, v in (("new", "new"), ("open", "open"), ("in progress", "open"), ("progress", "open"), ("pending", "pending"),
                 ("waiting", "pending"), ("hold", "pending"), ("snooze", "pending"), ("resolved", "solved"), ("solved", "solved"),
                 ("done", "solved"), ("closed", "closed"), ("cancel", "closed")):
        if k in r:
            return v
    return "open"


class Chatwoot(Desk):
    kind, name = "chatwoot", "Chatwoot"
    fields = ("base", "account", "token")
    help = "Profile settings > Access token in Chatwoot; the account id is the number in your Chatwoot address (/app/accounts/<id>)."
    PRI = {"urgent": "urgent", "high": "high", "normal": "medium", "low": "low"}

    def headers(self):
        return super().headers() | {"api_access_token": str(self.c.get("token") or "")}

    def _a(self) -> str:
        return f"/api/v1/accounts/{int(self.c.get('account') or 0)}"

    def check(self):
        me = self._get("/api/v1/profile")
        return f"signed in as {me.get('name') or me.get('email') or 'the key user'}"

    def _one(self, c: dict) -> dict:
        snd = ((c.get("meta") or {}).get("sender") or {})
        first = next((m.get("content") or "" for m in (c.get("messages") or []) if m.get("message_type") == 0), "")
        return {"ext_id": str(c.get("id")), "number": f"#{c.get('id')}", "subject": "", "text": first or str(c.get("last_non_activity_message", {}) .get("content") or ""),
                "status": _norm_status(c.get("status")), "raw_status": str(c.get("status") or ""), "priority": c.get("priority") or "",
                "tags": list(c.get("labels") or []),
                "requester": {"name": snd.get("name") or "", "email": snd.get("email") or "", "phone": snd.get("phone_number") or ""},
                "updated": datetime.fromtimestamp(int(c.get("last_activity_at") or c.get("timestamp") or 0), timezone.utc)}

    def recent(self, since):
        out = []
        for st in ("open", "pending"):
            body = self._get(f"{self._a()}/conversations?status={st}&page=1")
            for c in ((body.get("data") or {}).get("payload") or []):
                t = self._one(c)
                if not since or t["updated"] >= since:
                    out.append(t)
        return out

    def thread(self, t):
        body = self._get(f"{self._a()}/conversations/{t['ext_id']}/messages")
        out = []
        for m in body.get("payload") or []:
            mt = m.get("message_type")
            who = "note" if m.get("private") else "customer" if mt in (0, "incoming") else "agent" if mt in (1, "outgoing") else "system"
            out.append({"who": who, "text": str(m.get("content") or "")})
        return out

    def note(self, t, text):
        self._send("POST", f"{self._a()}/conversations/{t['ext_id']}/messages", {"content": text, "message_type": "outgoing", "private": True})

    def reply(self, t, text):
        self._send("POST", f"{self._a()}/conversations/{t['ext_id']}/messages", {"content": text, "message_type": "outgoing", "private": False})

    def tag(self, t, tags):
        self._send("POST", f"{self._a()}/conversations/{t['ext_id']}/labels", {"labels": sorted(set(t.get("tags") or []) | set(tags))})

    def set_priority(self, t, p):
        self._send("POST", f"{self._a()}/conversations/{t['ext_id']}/toggle_priority", {"priority": self.PRI.get(p, "medium")})

    def solve(self, t, text):
        self.note(t, text)
        self._send("POST", f"{self._a()}/conversations/{t['ext_id']}/toggle_status", {"status": "resolved"})

    def find(self, email="", phone=""):
        q = email or phone
        body = self._get(f"{self._a()}/contacts/search?q={q}")
        out = []
        for c in body.get("payload") or []:
            convs = self._get(f"{self._a()}/contacts/{c.get('id')}/conversations")
            out += [self._one(x) for x in (convs.get("payload") or [])]
        return out


class Zendesk(Desk):
    kind, name = "zendesk", "Zendesk"
    fields = ("base", "user", "token")
    help = "Admin Center > Apps and integrations > Zendesk API > add an API token; the user is the agent's email."

    def auth(self):
        return (f"{self.c.get('user')}/token", str(self.c.get("token") or ""))

    def check(self):
        me = (self._get("/api/v2/users/me.json") or {}).get("user") or {}
        if not me.get("id"):
            raise LayerError("Zendesk did not accept the email + API token.")
        return f"signed in as {me.get('name') or me.get('email')}"

    def _one(self, z: dict, users: dict | None = None) -> dict:
        u = (users or {}).get(z.get("requester_id")) or {}
        upd = z.get("updated_at") or z.get("created_at") or ""
        return {"ext_id": str(z.get("id")), "number": f"#{z.get('id')}", "subject": z.get("subject") or "", "text": z.get("description") or "",
                "status": _norm_status(z.get("status")), "raw_status": z.get("status") or "", "priority": z.get("priority") or "",
                "tags": list(z.get("tags") or []), "requester_id": z.get("requester_id"),
                "requester": {"name": u.get("name") or "", "email": u.get("email") or "", "phone": u.get("phone") or ""},
                "updated": datetime.fromisoformat(upd.replace("Z", "+00:00")) if upd else datetime.now(timezone.utc)}

    def recent(self, since):
        q = "type:ticket status<solved"
        if since:
            q += f" updated>{since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        body = self._get(f"/api/v2/search.json?query={q}&sort_by=updated_at&sort_order=desc")
        return [self._one(z) for z in body.get("results") or []]

    def thread(self, t):
        body = self._get(f"/api/v2/tickets/{t['ext_id']}/comments.json")
        out = []
        for c in body.get("comments") or []:
            who = "note" if not c.get("public", True) else "customer" if c.get("author_id") == t.get("requester_id") else "agent"
            out.append({"who": who, "text": str(c.get("plain_body") or c.get("body") or "")})
        return out

    def _upd(self, t, ticket):
        self._send("PUT", f"/api/v2/tickets/{t['ext_id']}.json", {"ticket": ticket})

    def note(self, t, text):
        self._upd(t, {"comment": {"body": text, "public": False}})

    def reply(self, t, text):
        self._upd(t, {"comment": {"body": text, "public": True}})

    def tag(self, t, tags):
        self._upd(t, {"additional_tags": tags})

    def set_priority(self, t, p):
        self._upd(t, {"priority": p if p in ("urgent", "high", "normal", "low") else "normal"})

    def solve(self, t, text):
        self._upd(t, {"status": "solved", "comment": {"body": text, "public": False}})

    def find(self, email="", phone=""):
        q = f"type:ticket requester:{email}" if email else f"type:ticket {phone}"
        return [self._one(z) for z in (self._get(f"/api/v2/search.json?query={q}").get("results") or [])]


class Freshdesk(Desk):
    kind, name = "freshdesk", "Freshdesk"
    fields = ("base", "token")
    help = "Profile settings > Your API key in Freshdesk; the address is https://<yours>.freshdesk.com."
    ST = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}
    PRI = {1: "low", 2: "normal", 3: "high", 4: "urgent"}

    def auth(self):
        return (str(self.c.get("token") or ""), "X")

    def check(self):
        me = self._get("/api/v2/agents/me") or {}
        return f"signed in as {((me.get('contact') or {}).get('name')) or 'the key user'}"

    def _one(self, f: dict) -> dict:
        rq = f.get("requester") or {}
        st = self.ST.get(f.get("status"), str(f.get("status") or ""))
        upd = f.get("updated_at") or f.get("created_at") or ""
        return {"ext_id": str(f.get("id")), "number": f"#{f.get('id')}", "subject": f.get("subject") or "",
                "text": f.get("description_text") or f.get("subject") or "", "status": _norm_status(st), "raw_status": st,
                "priority": self.PRI.get(f.get("priority"), ""), "tags": list(f.get("tags") or []),
                "requester": {"name": rq.get("name") or "", "email": rq.get("email") or "", "phone": rq.get("phone") or rq.get("mobile") or ""},
                "updated": datetime.fromisoformat(upd.replace("Z", "+00:00")) if upd else datetime.now(timezone.utc)}

    def recent(self, since):
        s = (since or datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = self._get(f"/api/v2/tickets?updated_since={s}&include=requester,description&per_page=30")
        return [self._one(f) for f in (body if isinstance(body, list) else []) if f.get("status") in (2, 3)]

    def thread(self, t):
        body = self._get(f"/api/v2/tickets/{t['ext_id']}/conversations")
        out = [{"who": "customer", "text": t.get("text") or ""}]
        for c in body if isinstance(body, list) else []:
            who = "note" if c.get("private") else "customer" if c.get("incoming") else "agent"
            out.append({"who": who, "text": str(c.get("body_text") or "")})
        return out

    def note(self, t, text):
        self._send("POST", f"/api/v2/tickets/{t['ext_id']}/notes", {"body": text.replace("\n", "<br>"), "private": True})

    def reply(self, t, text):
        self._send("POST", f"/api/v2/tickets/{t['ext_id']}/reply", {"body": text.replace("\n", "<br>")})

    def tag(self, t, tags):
        self._send("PUT", f"/api/v2/tickets/{t['ext_id']}", {"tags": sorted(set(t.get("tags") or []) | set(tags))})

    def set_priority(self, t, p):
        self._send("PUT", f"/api/v2/tickets/{t['ext_id']}", {"priority": {"low": 1, "normal": 2, "high": 3, "urgent": 4}.get(p, 2)})

    def solve(self, t, text):
        self.note(t, text)
        self._send("PUT", f"/api/v2/tickets/{t['ext_id']}", {"status": 4})

    def find(self, email="", phone=""):
        q = f"email={email}" if email else f"phone={phone}"
        body = self._get(f"/api/v2/tickets?{q}&include=requester,description")
        return [self._one(f) for f in (body if isinstance(body, list) else [])]


class ServiceNow(Desk):
    kind, name = "servicenow", "ServiceNow"
    fields = ("base", "user", "token")
    help = "A ServiceNow user with the itil role; the token is its password (basic auth on the Table API)."

    def auth(self):
        return (str(self.c.get("user") or ""), str(self.c.get("token") or ""))

    def check(self):
        self._get("/api/now/table/incident?sysparm_limit=1")
        return "the Table API answered"

    def _one(self, r: dict) -> dict:
        def dv(v):
            return v.get("display_value") if isinstance(v, dict) else v
        upd = str(dv(r.get("sys_updated_on")) or "")
        try:
            at = datetime.strptime(upd, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            at = datetime.now(timezone.utc)
        st = str(dv(r.get("state")) or "")
        pr = str(dv(r.get("priority")) or "").lower()
        return {"ext_id": str(dv(r.get("sys_id")) or ""), "number": str(dv(r.get("number")) or ""), "subject": str(dv(r.get("short_description")) or ""),
                "text": str(dv(r.get("description")) or dv(r.get("short_description")) or ""), "status": _norm_status(st), "raw_status": st,
                "priority": "urgent" if "critical" in pr or pr.startswith("1") else "high" if "high" in pr or pr.startswith("2") else
                            "low" if "low" in pr or "planning" in pr else "normal",
                "tags": [], "requester": {"name": str(dv(r.get("caller_id")) or ""), "email": "", "phone": ""}, "updated": at}

    def recent(self, since):
        q = "active=true"
        if since:
            q += f"^sys_updated_on>{since.strftime('%Y-%m-%d %H:%M:%S')}"
        body = self._get(f"/api/now/table/incident?sysparm_query={q}^ORDERBYDESCsys_updated_on&sysparm_limit=30&sysparm_display_value=true")
        return [self._one(r) for r in body.get("result") or []]

    def thread(self, t):
        return [{"who": "customer", "text": t.get("text") or ""}]

    def note(self, t, text):
        self._send("PATCH", f"/api/now/table/incident/{t['ext_id']}", {"work_notes": text})

    def reply(self, t, text):
        self._send("PATCH", f"/api/now/table/incident/{t['ext_id']}", {"comments": text})

    def tag(self, t, tags):
        self.note(t, "Hoola sorted this: " + ", ".join(tags))       # incidents have no free tags: the sort goes in a work note

    def set_priority(self, t, p):
        self._send("PATCH", f"/api/now/table/incident/{t['ext_id']}",
                    {"impact": {"urgent": "1", "high": "2"}.get(p, "3"), "urgency": {"urgent": "1", "high": "2"}.get(p, "3")})

    def solve(self, t, text):
        self._send("PATCH", f"/api/now/table/incident/{t['ext_id']}", {"state": "6", "close_code": "Solved (Permanently)", "close_notes": text})

    def find(self, email="", phone=""):
        q = f"caller_id.email={email}" if email else f"caller_id.phone={phone}"
        body = self._get(f"/api/now/table/incident?sysparm_query={q}&sysparm_limit=10&sysparm_display_value=true")
        return [self._one(r) for r in body.get("result") or []]


class JiraSM(Desk):
    kind, name = "jira", "Jira Service Management"
    fields = ("base", "user", "token")
    help = "id.atlassian.com > Security > API tokens; the user is the agent's Atlassian email; the address is https://<site>.atlassian.net."

    def auth(self):
        return (str(self.c.get("user") or ""), str(self.c.get("token") or ""))

    def check(self):
        body = self._get("/rest/servicedeskapi/servicedesk")
        return f"{len(body.get('values') or [])} service desk(s) reachable"

    def _one(self, r: dict) -> dict:
        vals = {v.get("fieldId"): v.get("value") for v in r.get("requestFieldValues") or []}
        rep = r.get("reporter") or {}
        st = ((r.get("currentStatus") or {}).get("status")) or ""
        ms = ((r.get("currentStatus") or {}).get("statusDate") or {}).get("epochMillis") or ((r.get("createdDate") or {}).get("epochMillis")) or 0
        desc = vals.get("description")
        return {"ext_id": str(r.get("issueKey") or r.get("issueId") or ""), "number": str(r.get("issueKey") or ""),
                "subject": str(vals.get("summary") or ""), "text": str(desc if isinstance(desc, str) else vals.get("summary") or ""),
                "status": _norm_status(st), "raw_status": st, "priority": "", "tags": [],
                "requester": {"name": rep.get("displayName") or "", "email": rep.get("emailAddress") or "", "phone": ""},
                "updated": datetime.fromtimestamp(int(ms) / 1000, timezone.utc) if ms else datetime.now(timezone.utc)}

    def recent(self, since):
        body = self._get("/rest/servicedeskapi/request?requestStatus=OPEN_REQUESTS&requestOwnership=ALL_REQUESTS&limit=30")
        out = [self._one(r) for r in body.get("values") or []]
        return [t for t in out if not since or t["updated"] >= since]

    def thread(self, t):
        body = self._get(f"/rest/servicedeskapi/request/{t['ext_id']}/comment")
        out = [{"who": "customer", "text": t.get("text") or ""}]
        rep = (t.get("requester") or {}).get("email")
        for c in body.get("values") or []:
            who = "note" if not c.get("public", True) else "customer" if (c.get("author") or {}).get("emailAddress") == rep else "agent"
            out.append({"who": who, "text": str(c.get("body") or "")})
        return out

    def note(self, t, text):
        self._send("POST", f"/rest/servicedeskapi/request/{t['ext_id']}/comment", {"body": text, "public": False})

    def reply(self, t, text):
        self._send("POST", f"/rest/servicedeskapi/request/{t['ext_id']}/comment", {"body": text, "public": True})

    def tag(self, t, tags):
        self._send("PUT", f"/rest/api/3/issue/{t['ext_id']}", {"update": {"labels": [{"add": x} for x in tags]}})

    def set_priority(self, t, p):
        self._send("PUT", f"/rest/api/3/issue/{t['ext_id']}", {"fields": {"priority": {"name": {"urgent": "Highest", "high": "High",
                                                                                                   "low": "Low"}.get(p, "Medium")}}})

    def solve(self, t, text):
        self.note(t, text + " (Hoola does not move Jira workflows; resolve it in Jira.)")

    def find(self, email="", phone=""):
        return [t for t in self.recent(None) if email and (t["requester"].get("email") or "").lower() == email.lower()]


KINDS = {k.kind: k for k in (Chatwoot, Zendesk, Freshdesk, ServiceNow, JiraSM)}
NOT_BUILT = {"zoho_desk": "Zoho Desk (needs an OAuth app registered by Newtika)", "salesforce": "Salesforce Service Cloud (needs a connected app)",
             "hubspot": "HubSpot (needs an app; notes need associations)", "intercom": "Intercom (needs an app + an admin id for notes)"}


# ---------------------------------------------------------------- connecting
def _seal(d: dict) -> str:
    from . import channels as CH
    return CH._seal(json.dumps(d))


def _open(v: str) -> dict:
    from . import channels as CH
    try:
        return json.loads(CH._open(v) or "{}")
    except Exception:   # noqa: BLE001
        return {}


def _hint(v: str) -> str:
    v = str(v or "")
    return ("…" + v[-4:]) if len(v) > 6 else ("set" if v else "")


def _private(url: str) -> bool:
    import ipaddress
    host = re.sub(r"^https://", "", url).split("/")[0].split(":")[0].lower()
    if host in ("localhost",) or host.endswith((".local", ".internal", ".localhost")):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def connect(tenant: str, body: dict) -> dict:
    _ensure()
    b = body if isinstance(body, dict) else {}
    kind = str(b.get("kind") or "")
    if kind in NOT_BUILT:
        raise LayerError(f"{NOT_BUILT[kind]} is not built yet.")
    k = KINDS.get(kind)
    if k is None:
        raise LayerError("Helpdesk: " + ", ".join(x.name for x in KINDS.values()))
    base = str(b.get("base") or "").strip().rstrip("/")
    if not re.fullmatch(r"https://[A-Za-z0-9.\-]+(:\d+)?(/[\w\-./]*)?", base):
        raise LayerError("Write your helpdesk's https:// address.")
    if _private(base):
        raise LayerError("That address is not on the public internet.")
    with session() as s:
        r = s.get(SevaLayer, tenant)
        old = _open(r.sealed) if r is not None and r.kind == kind else {}
        if r is None:
            r = SevaLayer(tenant_id=tenant, hook=secrets.token_urlsafe(24))
            s.add(r)
        cred = {}
        for f in ("user", "token", "account"):
            v = str(b.get(f) or "").strip()
            cred[f] = v or old.get(f, "")
        missing = [f for f in k.fields if f != "base" and not cred.get(f)]
        if missing:
            raise LayerError("Missing: " + ", ".join(missing))
        r.kind, r.base, r.sealed = kind, base, _seal(cred)
        r.hints = json.dumps({"user": cred.get("user", ""), "token": _hint(cred.get("token")), "account": cred.get("account", "")})
        st = DEFAULTS | _j(r.settings, {})
        for key in DEFAULTS:
            if key in (b.get("settings") or {}):
                st[key] = type(DEFAULTS[key])((b["settings"] or {})[key])
        r.settings, r.status, r.note = json.dumps(st), "new", ""
    return check(tenant)


def _desk(tenant: str) -> tuple[Desk, dict]:
    _ensure()
    with session() as s:
        r = s.get(SevaLayer, tenant)
        if r is None or not r.kind or r.status == "off":
            raise LayerError("No helpdesk is joined.")
        return KINDS[r.kind](r.base, _open(r.sealed)), DEFAULTS | _j(r.settings, {})


def check(tenant: str) -> dict:
    d, _ = _desk(tenant)
    try:
        say = d.check()
        status, note = "ok", say
    except Exception as e:   # noqa: BLE001
        status, note = "error", str(e)[:300]
    with session() as s:
        r = s.get(SevaLayer, tenant)
        r.status, r.note = status, note
    _log(tenant, "", "check", note, status == "ok")
    return view(tenant)


def save_settings(tenant: str, settings: dict) -> dict:
    _ensure()
    with session() as s:
        r = s.get(SevaLayer, tenant)
        if r is None:
            raise LayerError("Join your helpdesk first.")
        st = DEFAULTS | _j(r.settings, {})
        for key in DEFAULTS:
            if key in (settings or {}):
                st[key] = type(DEFAULTS[key])(settings[key])
        st["summary_after"] = max(3, min(50, int(st["summary_after"])))
        st["remind_h"] = max(1, min(240, int(st["remind_h"])))
        r.settings = json.dumps(st)
    return view(tenant)


def disconnect(tenant: str) -> dict:
    _ensure()
    with session() as s:
        r = s.get(SevaLayer, tenant)
        if r is not None:
            r.status, r.sealed = "off", ""
    return {"say": "Your helpdesk is no longer joined; its key was forgotten. Nothing in it was changed."}


def view(tenant: str) -> dict:
    _ensure()
    from ..config import get_settings
    with session() as s:
        r = s.get(SevaLayer, tenant)
        if r is None:
            return {"joined": False, "kinds": [{"kind": k.kind, "name": k.name, "fields": list(k.fields), "help": k.help} for k in KINDS.values()],
                    "not_built": list(NOT_BUILT.values())}
        base = (get_settings().public_base_url or "").rstrip("/")
        out = {"joined": r.status != "off", "kind": r.kind, "name": KINDS[r.kind].name if r.kind in KINDS else r.kind, "base": r.base,
               "hints": _j(r.hints, {}), "settings": DEFAULTS | _j(r.settings, {}), "status": r.status, "note": r.note,
               "last_run": _aware(r.last_run).isoformat() if r.last_run else "",
               "webhook": f"{base}/api/support/layer/{r.hook}" if r.hook else ""}
    out["kinds"] = [{"kind": k.kind, "name": k.name, "fields": list(k.fields), "help": k.help} for k in KINDS.values()]
    out["not_built"] = list(NOT_BUILT.values())
    out["log"] = logs(tenant, 30)
    with session() as s:
        out["seen"] = s.query(SevaLayerTicket).filter_by(tenant_id=tenant).count()
    return out


def _log(tenant: str, ext_id: str, action: str, detail: str, ok: bool = True) -> None:
    with session() as s:
        s.add(SevaLayerLog(tenant_id=tenant, ext_id=str(ext_id)[:80], action=action[:20], detail=_S().mask(str(detail))[:600], ok=int(ok),
                           at=_S().clock()))


def logs(tenant: str, n: int = 50) -> list[dict]:
    _ensure()
    with session() as s:
        return [{"ext_id": x.ext_id, "action": x.action, "detail": x.detail, "ok": bool(x.ok), "at": _aware(x.at).isoformat()}
                for x in s.scalars(select(SevaLayerLog).where(SevaLayerLog.tenant_id == tenant).order_by(SevaLayerLog.at.desc()).limit(n)).all()]


# ---------------------------------------------------------------- the work
class _T:      # a ticket-like object so her routing (G10) can read a helpdesk ticket
    def __init__(self, t: dict, cat: str, pri: str, lang: str):
        self.text, self.category, self.priority, self.lang = (t.get("subject", "") + " " + t.get("text", "")).strip(), cat, pri, lang
        rq = t.get("requester") or {}
        self.customer = ("email:" + rq["email"].lower()) if rq.get("email") else ("phone:" + re.sub(r"\D", "", rq.get("phone", ""))) if rq.get("phone") else ""
        self.channel, self.custom, self.labels, self.status, self.stage, self.assignee, self.queue = "email", "", "", "open", "", "", ""
        self.awaiting_since, self.created_at = None, datetime.now(timezone.utc)


_CONFIRM = re.compile(r"\b(fixed|solved|resolved|works now|working now|it works|all good|sorted|ho gaya|theek ho gaya|chal raha hai)\b", re.I)


def _summary(thread: list[dict]) -> str:
    S = _S()
    convo = "\n".join(f"{m['who']}: {S.mask(m['text'])[:400]}" for m in thread if m["who"] in ("customer", "agent"))[-6000:]
    words = (S._ai("Summarise this support conversation for the agent in at most 4 short lines: the problem, what was tried, what "
                   "the customer wants now, any deadline. Facts from the text only; no advice.", convo, 300) or "").strip()
    if words:
        return words
    cust = [m["text"] for m in thread if m["who"] == "customer"]
    return (f"{len(thread)} messages. First: \"{S.mask(cust[0])[:200]}\". Latest from the customer: \"{S.mask(cust[-1])[:200]}\"."
            if cust else f"{len(thread)} messages.")


def _one(tenant: str, d: Desk, st: dict, t: dict) -> dict:
    """One ticket of her helpdesk: sort it (once), suggest (when the customer wrote since), summarise, close by her rule."""
    S = _S()
    from . import engine as E
    did = []
    with session() as s:
        row = s.scalars(select(SevaLayerTicket).where(SevaLayerTicket.tenant_id == tenant, SevaLayerTicket.ext_id == t["ext_id"])).first()
        new = row is None
        if new:
            row = SevaLayerTicket(tenant_id=tenant, ext_id=t["ext_id"], number=t["number"][:40], seen_at=S.clock())
            s.add(row)
            s.flush()
        rid, answered_at, summarized_at = row.id, row.answered_at, row.summarized_at
    thread = d.thread(t)
    cust_msgs = [m for m in thread if m["who"] == "customer" and m["text"].strip()]
    last = cust_msgs[-1]["text"] if cust_msgs else (t.get("text") or "")
    full = (t.get("subject", "") + "\n" + (t.get("text") or "")).strip()
    u = E.understand(tenant, last or full)
    ut = E.understand(tenant, full) if full else u
    cat, pri, lang = ut["category"], ut["priority"], ut["lang"]
    obj = _T(t, cat, pri, lang)
    if new:
        tags = [f"hoola-{cat}", f"lang-{lang[:5]}"]
        q = ""
        try:
            from . import teams as TM
            q = TM.queue_for(tenant, obj)
        except Exception:   # noqa: BLE001
            q = ""
        if q:
            tags.append(f"queue-{q}")
        if st["tags"]:
            d.tag(t, tags)
            did.append("tagged " + ", ".join(tags))
        if st["priority"] and pri in ("urgent", "high") and t.get("priority") not in ("urgent", "high"):
            d.set_priority(t, pri)
            did.append(f"priority {pri}")
        with session() as s:
            r = s.get(SevaLayerTicket, rid)
            r.category, r.lang, r.queue, r.customer = cat, lang[:10], q, obj.customer[:200]
    # the customer wrote since Hoola last looked: a suggestion (or a public answer only if she allows and trust says alone)
    n_cust = len(cust_msgs) or 1
    last_who = next((m["who"] for m in reversed(thread) if m["who"] in ("customer", "agent")), "customer")
    if n_cust > answered_at and last_who == "customer" and last.strip():
        if st["close_on_confirm"] and t["status"] == "pending" and _CONFIRM.search(last) and u["intent"] in ("thanks", "question", "problem"):
            d.solve(t, "The customer said it is fixed, so Hoola marked it solved (her rule)." + SIGN)
            did.append("solved (the customer confirmed)")
        else:
            dec = E.reply(tenant, last, "email", obj.customer, "layer")
            decision = dec.get("decision", "")
            if decision in ("answer", "status") and dec.get("reply"):
                public_ok = st["public_replies"] and dec.get("level", "answer") == "answer" and decision == "answer"
                if public_ok:
                    d.reply(t, dec["reply"])
                    did.append("answered (public)")
                elif st["notes"]:
                    d.note(t, f"Suggested reply (from {dec.get('source') or 'your approved knowledge'}):\n\n{dec['reply']}{SIGN}")
                    did.append("suggested a reply")
            elif decision == "draft" and st["notes"]:
                d.note(t, f"Suggested reply (draft - this topic is set to 'a person sends it'):\n\n{dec.get('reply') or ''}{SIGN}"
                       if dec.get("reply") else "Hoola has a draft for this topic in the support desk." + SIGN)
                did.append("draft noted")
            elif st["notes"] and decision in ("person", "request", "no_answer", "refuse", "clarify"):
                why = "; ".join(str(x) for x in dec.get("why") or [])[:300]
                d.note(t, f"Hoola thinks a person should take this ({decision}): {why}." + SIGN)
                if st["tags"]:
                    d.tag(t, ["hoola-person"])
                did.append(f"noted: {decision}")
            with session() as s:
                r = s.get(SevaLayerTicket, rid)
                r.decision = decision[:16]
        with session() as s:
            s.get(SevaLayerTicket, rid).answered_at = n_cust
    if st["summaries"] and len(thread) >= st["summary_after"] and len(thread) >= summarized_at + st["summary_after"]:
        d.note(t, "Summary so far:\n" + _summary(thread) + SIGN)
        did.append("summarised")
        with session() as s:
            s.get(SevaLayerTicket, rid).summarized_at = len(thread)
    with session() as s:
        r = s.get(SevaLayerTicket, rid)
        r.status, r.raw_status, r.msgs = t["status"], t["raw_status"][:40], len(thread)
        r.waiting_since = (r.waiting_since or S.clock()) if last_who == "customer" and t["status"] in ("new", "open") else None
    for x in did:
        _log(tenant, t["ext_id"], x.split(" ")[0].rstrip(":"), f"{t['number']}: {x}")
    return {"ticket": t["number"], "did": did}


def run(tenant: str, force: bool = False) -> dict:
    """Read new / changed tickets of her helpdesk and do what her switches allow."""
    d, st = _desk(tenant)
    S = _S()
    with session() as s:
        r = s.get(SevaLayer, tenant)
        if not force and r.last_run and S.clock() - _aware(r.last_run) < timedelta(minutes=3):
            return {"skipped": True}
        since = _aware(r.cursor)
        r.last_run = S.clock()
    try:
        tix = d.recent(since)
    except Exception as e:   # noqa: BLE001
        _log(tenant, "", "read", str(e), False)
        with session() as s:
            r = s.get(SevaLayer, tenant)
            r.status, r.note = "error", str(e)[:300]
        return {"error": str(e)}
    done = []
    for t in tix[:50]:
        try:
            done.append(_one(tenant, d, st, t))
        except Exception as e:   # noqa: BLE001
            _log(tenant, t.get("ext_id", ""), "error", f"{t.get('number')}: {str(e)[:200]}", False)
    newest = max([t["updated"] for t in tix], default=None)
    with session() as s:
        r = s.get(SevaLayer, tenant)
        if newest:
            r.cursor = newest - timedelta(seconds=1)
        r.status = "ok"
    reminded = remind(tenant)
    return {"read": len(tix), "done": [x for x in done if x["did"]], "reminded": reminded}


def run_all() -> int:
    _ensure()
    with session() as s:
        tenants = [r.tenant_id for r in s.scalars(select(SevaLayer).where(SevaLayer.status.in_(("ok", "new")))).all()]
    n = 0
    for t in tenants:
        try:
            got = run(t)
            n += got.get("read", 0)
        except Exception:   # noqa: BLE001
            log.exception("seva layer run")
    return n


def by_hook(token: str) -> str:
    _ensure()
    with session() as s:
        r = s.scalars(select(SevaLayer).where(SevaLayer.hook == str(token or ""))).first()
        return r.tenant_id if r is not None and r.status != "off" else ""


def remind(tenant: str) -> int:
    """Customers still waiting on her helpdesk past her hours: once a day per ticket, to her chat + the desk."""
    S = _S()
    st = DEFAULTS | settings_of(tenant)
    cut = S.clock() - timedelta(hours=st["remind_h"])
    n = 0
    with session() as s:
        rows = s.scalars(select(SevaLayerTicket).where(SevaLayerTicket.tenant_id == tenant, SevaLayerTicket.waiting_since.is_not(None),
                                                       SevaLayerTicket.waiting_since <= cut)).all()
        due = [(r.id, r.number) for r in rows if not r.reminded_at or S.clock() - _aware(r.reminded_at) > timedelta(hours=24)]
        for rid, _ in due:
            s.get(SevaLayerTicket, rid).reminded_at = S.clock()
    for _, number in due:
        S._publish(tenant, "seva_remind", {"ticket": number, "text": f"{number} in your helpdesk: the customer is still waiting.", "level": "owner"})
        S._note_chat(tenant, f"{number} in your helpdesk: the customer has waited more than {st['remind_h']} hours (information, not an instruction).")
        _log(tenant, number, "remind", f"{number}: customer waiting past {st['remind_h']} h")
        n += 1
    return n


def settings_of(tenant: str) -> dict:
    with session() as s:
        r = s.get(SevaLayer, tenant)
        return _j(r.settings, {}) if r is not None else {}


def status_for(tenant: str, customer: str) -> list[dict]:
    """'Where is my ticket?' on Hoola's own channels for a business that keeps its tickets in her helpdesk: the
    customer's own tickets there (by their email / phone), with that tool's own status. [] when not joined."""
    try:
        d, _ = _desk(tenant)
    except LayerError:
        return []
    email = customer.split(":", 1)[1] if customer.startswith("email:") else ""
    phone = "+" + re.sub(r"\D", "", customer.split(":", 1)[1]) if customer.startswith(("phone:", "wa:", "sms:", "twilio_sms:")) else ""
    if not (email or phone):
        return []
    try:
        mine = d.find(email=email, phone=phone)
    except Exception as e:   # noqa: BLE001
        _log(tenant, "", "status", str(e), False)
        return []
    out = []
    for t in mine[:3]:
        word = {"new": "received", "open": "being worked on", "pending": "waiting for your reply", "solved": "solved", "closed": "closed"}[t["status"]]
        out.append({"number": t["number"], "status": t["status"], "line": f"Your request {t['number']} is {word} ({t['raw_status']})."})
    return out
