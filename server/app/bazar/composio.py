"""v0.276 COMPOSIO: Slack, Notion, Jira, HubSpot ... for every Hoola user through ONE Newtika Composio project.

How it is multi-tenant:
- Newtika holds one Composio project key (COMPOSIO_API_KEY, VPS .env only). Users never make a Composio account.
- Every Hoola user is a separate Composio user_id, derived by the SERVER from her tenant id (`composio_user`). The
  model, the chat text and other avatars never choose it. Each run also names her own connected account id, which
  only her Connection row holds, so one user's request can never reach another user's Slack.
- She signs in on the app's own login page (Composio's hosted Connect Link, official OAuth). The account id is kept
  sealed in her Connection row; "pending" until Composio says ACTIVE.
- Reads run; everything else (send / create / update / delete ...) is a confirm card with the exact call frozen.
- Per-user and whole-app monthly call caps keep the bill bounded (free plan = 1 lakh calls a month).
Apps Hoola already runs itself (Gmail, Calendar, Drive, GitHub, WhatsApp ...) and scraping apps are never offered.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import logging
import re
import time
from typing import Any

from sqlalchemy import func, select

from ..config import get_settings as core_settings
from .db import ComposioUsage, Connection
from .packs.registry import Pack, add_resolver

log = logging.getLogger(__name__)

PREFIX = "cmp-"
PROVIDER = "composio:"

# slug -> (name, what she can do). Only apps Hoola has no direct connection for.
DEFAULT_TOOLKITS: dict[str, tuple[str, str]] = {
    "slack": ("Slack", "channels, messages, threads, reminders"),
    "notion": ("Notion", "pages, databases, notes"),
    "jira": ("Jira", "issues, sprints, projects"),
    "confluence": ("Confluence", "team pages and spaces"),
    "trello": ("Trello", "boards, lists, cards"),
    "asana": ("Asana", "tasks and projects"),
    "clickup": ("ClickUp", "tasks, lists, docs"),
    "linear": ("Linear", "issues and cycles"),
    "airtable": ("Airtable", "bases, tables, records"),
    "hubspot": ("HubSpot", "CRM contacts, deals, companies"),
    "salesforce": ("Salesforce", "CRM leads, accounts, opportunities"),
    "pipedrive": ("Pipedrive", "sales deals and contacts"),
    "zendesk": ("Zendesk", "support tickets"),
    "freshdesk": ("Freshdesk", "support tickets"),
    "mailchimp": ("Mailchimp", "audiences and email campaigns"),
    "zoom": ("Zoom", "meetings and recordings"),
    "calendly": ("Calendly", "booking links and events"),
    "dropbox": ("Dropbox", "files and folders"),
    "todoist": ("Todoist", "to-do lists"),
    "figma": ("Figma", "design files and comments"),
    "miro": ("Miro", "whiteboards"),
}
# Hoola does these itself (cheaper, private) or they break the official-routes rule: never through Composio.
NEVER = {"gmail", "googlecalendar", "googledrive", "googlesheets", "googledocs", "googleslides", "googlephotos",
         "youtube", "outlook", "github", "shopify", "supabase", "whatsapp", "apify", "firecrawl", "scrapingbee",
         "browserbase", "browser_tool", "serpapi", "linkedin", "instagram", "facebook", "twitter"}

READ_VERBS = {"GET", "LIST", "FETCH", "SEARCH", "FIND", "RETRIEVE", "READ", "QUERY", "VIEW", "DESCRIBE", "CHECK",
              "COUNT", "LOOKUP", "EXPORT", "DOWNLOAD"}
WRITE_WORDS = {"SEND", "POST", "CREATE", "UPDATE", "DELETE", "REMOVE", "ARCHIVE", "INVITE", "KICK", "SET", "ADD",
               "MOVE", "SHARE", "PUBLISH", "UPLOAD", "MERGE", "CLOSE", "EXECUTE", "RUN", "TRIGGER", "PAY", "TRANSFER",
               "CANCEL", "REVOKE", "PIN", "UNPIN", "REACT", "EDIT", "MODIFY", "REPLACE", "RENAME", "ASSIGN", "LEAVE",
               "JOIN", "SCHEDULE", "START", "STOP", "APPROVE", "REJECT", "MARK", "CONVERT", "DUPLICATE",
               "COPY", "RESTORE", "ENABLE", "DISABLE", "BULK", "BATCH", "UPSERT", "PUT", "PATCH", "WRITE", "APPEND",
               "INSERT", "COMMENT", "REPLY", "FORWARD", "DRAFT", "SUBSCRIBE", "UNSUBSCRIBE", "MUTE"}


class ComposioError(Exception):
    """Composio refused or failed. `auth` = her sign-in is gone (she links again)."""

    def __init__(self, msg: str, status: int = 0, auth: bool = False):
        super().__init__(msg)
        self.status, self.auth = status, auth


def configured() -> bool:
    return bool(core_settings().composio_api_key)


def toolkits() -> dict[str, tuple[str, str]]:
    raw = (core_settings().composio_toolkits or "").strip()
    if not raw:
        return dict(DEFAULT_TOOLKITS)
    out: dict[str, tuple[str, str]] = {}
    for slug in re.split(r"[,\s]+", raw.lower()):
        if re.fullmatch(r"[a-z0-9_]{2,40}", slug or "") and slug not in NEVER:
            out[slug] = DEFAULT_TOOLKITS.get(slug, (slug.replace("_", " ").title(), "its tools"))
    return out


def composio_user(tenant_id: str) -> str:
    """Her Composio user_id. Server-derived and opaque, so Composio never sees the raw tenant id."""
    salt = core_settings().secret_key or "hoola"
    return "hoola-" + hmac.new(salt.encode(), tenant_id.encode(), hashlib.sha256).hexdigest()[:32]


def is_read(slug: str, toolkit: str) -> bool:
    """SLACK_LIST_ALL_CHANNELS = read; SLACK_SEND_MESSAGE = write. Unsure = write (a card she taps)."""
    words = slug.upper().split("_")
    head = toolkit.upper().split("_")
    if words[:len(head)] == head:
        words = words[len(head):]
    if not words or words[0] not in READ_VERBS:
        return False
    return not any(w in WRITE_WORDS for w in words)


# ---------------------------------------------------------------- HTTP client (Composio REST v3.1, no SDK)
class Client:
    def __init__(self, key: str, base: str, http=None):
        import httpx
        self.key, self.base = key, base.rstrip("/")
        self.http = http or httpx.Client(timeout=40)
        self._auth_cfg: dict[str, str] = {}

    def _req(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict[str, Any]:
        import httpx
        try:
            r = self.http.request(method, self.base + path, params=params, json=body,
                                  headers={"x-api-key": self.key, "Accept": "application/json"})
        except httpx.HTTPError as e:
            raise ComposioError(f"Composio not reachable ({type(e).__name__})")
        if r.status_code >= 400:
            try:
                err = r.json().get("error") or {}
                msg = err.get("message") if isinstance(err, dict) else str(err)
            except ValueError:
                msg = r.text[:200]
            raise ComposioError(f"HTTP {r.status_code}: {(msg or '')[:240]}", r.status_code,
                                auth=r.status_code in (401, 403, 410) and "api key" not in (msg or "").lower())
        if not r.content:
            return {}
        try:
            return r.json()
        except ValueError:
            return {}

    def auth_config_id(self, toolkit: str) -> str:
        if toolkit in self._auth_cfg:
            return self._auth_cfg[toolkit]
        res = self._req("GET", "/auth_configs", params={"toolkit_slug": toolkit, "limit": 20})
        ids = [i.get("id") for i in res.get("items") or []
               if i.get("id") and str(i.get("status", "ENABLED")).upper() == "ENABLED"
               and ((i.get("toolkit") or {}).get("slug", toolkit) == toolkit)]
        if not ids:
            made = self._req("POST", "/auth_configs", body={"toolkit": {"slug": toolkit},
                                                            "auth_config": {"type": "use_composio_managed_auth"}})
            ids = [(made.get("auth_config") or {}).get("id")]
        if not ids or not ids[0]:
            raise ComposioError(f"Composio has no sign-in set up for {toolkit}.")
        self._auth_cfg[toolkit] = ids[0]
        return ids[0]

    def link(self, toolkit: str, user_id: str, callback_url: str) -> dict[str, Any]:
        res = self._req("POST", "/connected_accounts/link",
                        body={"auth_config_id": self.auth_config_id(toolkit), "user_id": user_id,
                              "callback_url": callback_url})
        if not res.get("redirect_url") or not res.get("connected_account_id"):
            raise ComposioError("Composio did not give a sign-in link.")
        return res

    def account(self, ca_id: str) -> dict[str, Any]:
        return self._req("GET", f"/connected_accounts/{ca_id}")

    def delete(self, ca_id: str) -> None:
        self._req("DELETE", f"/connected_accounts/{ca_id}")

    def tools(self, toolkit: str, query: str = "", important: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"toolkit_slug": toolkit, "limit": max(1, min(limit, 100)), "toolkit_versions": "latest"}
        if query:
            params["query"] = query[:120]
        if important:
            params["important"] = "true"
        return [t for t in self._req("GET", "/tools", params=params).get("items") or [] if not t.get("is_deprecated")]

    def tool(self, slug: str) -> dict[str, Any]:
        return self._req("GET", f"/tools/{slug}", params={"toolkit_versions": "latest"})

    def execute(self, slug: str, user_id: str, ca_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._req("POST", f"/tools/execute/{slug}",
                         body={"user_id": user_id, "connected_account_id": ca_id, "arguments": arguments,
                               "version": "latest"})


_client: Client | None = None


def client() -> Client:
    global _client
    if _client is None:
        st = core_settings()
        if not st.composio_api_key:
            raise ComposioError("Composio is not set up on this server yet (COMPOSIO_API_KEY).")
        _client = Client(st.composio_api_key, st.composio_base_url)
    return _client


def set_client(c: Client | None) -> None:   # tests
    global _client
    _client = c
    TOOL_CACHE.clear()


# ---------------------------------------------------------------- tool lists (same for every user: cached globally)
TOOL_CACHE: dict[str, tuple[float, Any]] = {}
TOOL_TTL = 3600


def _cached(key: str, fn):
    hit = TOOL_CACHE.get(key)
    if hit and time.time() - hit[0] < TOOL_TTL:
        return hit[1]
    val = fn()
    TOOL_CACHE[key] = (time.time(), val)
    return val


def tool_list(toolkit: str, query: str = "", important: bool = True, limit: int = 25) -> list[dict[str, Any]]:
    return _cached(f"list:{toolkit}:{query}:{important}:{limit}",
                   lambda: client().tools(toolkit, query=query, important=important, limit=limit))


def tool_info(slug: str) -> dict[str, Any]:
    return _cached("tool:" + slug, lambda: client().tool(slug))


def spec_of(t: dict[str, Any], toolkit: str) -> dict[str, Any]:
    slug = str(t.get("slug") or "")
    return {"tool": slug, "description": str(t.get("description") or t.get("name") or slug)[:600],
            "input_schema": t.get("input_parameters") or {"type": "object", "properties": {}},
            "tier": 0 if is_read(slug, toolkit) else 2}


# ---------------------------------------------------------------- packs: cmp-<toolkit>, resolved on demand
def pack_for(toolkit: str) -> Pack | None:
    kits = toolkits()
    if toolkit not in kits:
        return None
    name, what = kits[toolkit]
    return Pack(id=PREFIX + toolkit, name=name, category="Apps via Composio", sub_category="App connection",
                pack_type="Composio", layer="L1", phase="MVP", priority="P1",
                description=f"{name}: {what} (her own {name} account, official sign-in via Composio)",
                master_list_row=0, executor="composio",
                config={"provider": PROVIDER + toolkit, "toolkit": toolkit, "composio": True},
                tools=[], keywords=[toolkit, name.lower()])


def _resolve(pack_id: str) -> Pack | None:
    if not pack_id.startswith(PREFIX):
        return None
    return pack_for(pack_id[len(PREFIX):])


add_resolver(_resolve)


def match(query: str, limit: int = 4) -> list[Pack]:
    """Apps whose name / slug appears in her words ('slack pe message', 'notion page')."""
    q = query.lower()
    out = []
    for slug, (name, _) in toolkits().items():
        if re.search(rf"\b({re.escape(slug)}|{re.escape(name.lower())})\b", q):
            p = pack_for(slug)
            if p:
                out.append(p)
    return out[:limit]


# ---------------------------------------------------------------- her accounts
def _seal(d: dict[str, Any]) -> str:
    from .security import vault
    return vault().seal(json.dumps(d))


def _unseal(c: Connection) -> dict[str, Any]:
    from .security import vault
    try:
        return json.loads(vault().open(c.token_enc)) if c.token_enc else {}
    except Exception:   # noqa: BLE001
        return {}


def _rows(s, user_id: str, toolkit: str, statuses=("active", "pending")) -> list[Connection]:
    return list(s.scalars(select(Connection).where(Connection.user_id == user_id,
                                                   Connection.provider == PROVIDER + toolkit,
                                                   Connection.status.in_(statuses))).all())


def _status_of(acc: dict[str, Any]) -> str:
    return str(acc.get("status") or "").upper()


def account(s, user_id: str, toolkit: str, check: bool = True) -> tuple[Connection | None, str]:
    """(her connection, its connected_account_id). A pending one is checked with Composio once and becomes active
    when her sign-in finished; a failed / expired one is closed."""
    for c in sorted(_rows(s, user_id, toolkit), key=lambda r: r.status != "active"):
        ca = _unseal(c).get("ca", "")
        if not ca:
            continue
        if c.status == "active":
            return c, ca
        if not check:
            continue
        try:
            st = _status_of(client().account(ca))
        except ComposioError:
            continue
        if st == "ACTIVE":
            c.status = "active"
            s.flush()
            return c, ca
        if st in ("FAILED", "EXPIRED", "INACTIVE", "DELETED"):
            c.status = "expired"
            s.flush()
    return None, ""


def status(s, user_id: str, toolkit: str) -> str:
    if not configured():
        return "not_configured"
    rows = _rows(s, user_id, toolkit)
    if any(r.status == "active" for r in rows):
        return "ready"
    return "pending" if rows else "needs_link"


def mark_expired(s, user_id: str, toolkit: str) -> None:
    for c in _rows(s, user_id, toolkit):
        c.status = "expired"
    s.flush()


# ---------------------------------------------------------------- monthly caps
def _month() -> str:
    ist = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5, minutes=30)
    return ist.strftime("%Y-%m")


def used(s, user_id: str | None = None) -> int:
    q = select(func.coalesce(func.sum(ComposioUsage.calls), 0)).where(ComposioUsage.month == _month())
    if user_id is not None:
        q = q.where(ComposioUsage.user_id == user_id)
    return int(s.scalar(q) or 0)


class CapReached(Exception):
    pass


def take_call(s, user_id: str) -> None:
    """Counts one call; refuses when her month or the whole app's month is full."""
    st = core_settings()
    if st.composio_user_monthly_calls and used(s, user_id) >= st.composio_user_monthly_calls:
        raise CapReached(f"Is mahine ke {st.composio_user_monthly_calls} app-calls poore ho gaye; agle mahine phir chalega.")
    if st.composio_monthly_calls and used(s) >= st.composio_monthly_calls:
        raise CapReached("Hoola ke sab users ki is mahine ki app-calls ki seema poori ho gayi; agle mahine phir chalega.")
    row = s.scalars(select(ComposioUsage).where(ComposioUsage.user_id == user_id, ComposioUsage.month == _month())).first()
    if row is None:
        s.add(ComposioUsage(user_id=user_id, month=_month(), calls=1))
    else:
        row.calls += 1
    s.flush()


# ---------------------------------------------------------------- connect / disconnect (her taps or the chat)
def _state(user_id: str, toolkit: str) -> str:
    exp = int(time.time()) + 3600
    msg = f"{user_id}|{toolkit}|{exp}"
    sig = hmac.new((core_settings().secret_key or "hoola").encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(f"{msg}|{sig}".encode()).decode().rstrip("=")


def read_state(state: str) -> tuple[str, str] | None:
    try:
        raw = base64.urlsafe_b64decode(state + "=" * (-len(state) % 4)).decode()
        user_id, toolkit, exp, sig = raw.rsplit("|", 3)
        good = hmac.new((core_settings().secret_key or "hoola").encode(), f"{user_id}|{toolkit}|{exp}".encode(),
                        hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good) or int(exp) < time.time():
            return None
    except Exception:   # noqa: BLE001
        return None
    return user_id, toolkit


def start_link(s, user_id: str, toolkit: str) -> dict[str, Any]:
    """Her own sign-in page for this app. The callback carries a signed (user, app) state; the account id Composio
    returns is sealed in her pending Connection, never shown to the model."""
    if toolkit not in toolkits():
        raise ComposioError(f"'{toolkit}' Hoola ki app list mein nahi hai.")
    from .config import get_settings
    cb = f"{get_settings().public_base_url}/bazar/composio/callback?st={_state(user_id, toolkit)}"
    res = client().link(toolkit, composio_user(user_id), cb)
    for c in _rows(s, user_id, toolkit, statuses=("pending",)):
        c.status = "replaced"
    s.add(Connection(user_id=user_id, provider=PROVIDER + toolkit,
                     token_enc=_seal({"ca": str(res["connected_account_id"])}), status="pending"))
    s.flush()
    return {"url": str(res["redirect_url"]), "name": toolkits()[toolkit][0], "pack_id": PREFIX + toolkit}


def finish_link(s, state: str) -> tuple[str, str, bool]:
    """Her browser came back. (user_id, app name, linked?) - linked only when Composio says ACTIVE."""
    got = read_state(state)
    if not got:
        raise ComposioError("Yeh link purana ya galat hai. Hoola se dobara 'jodo' boliye.")
    user_id, toolkit = got
    conn, _ = account(s, user_id, toolkit)
    return user_id, toolkits().get(toolkit, (toolkit, ""))[0], conn is not None


def disconnect(s, user_id: str, toolkit: str) -> bool:
    rows = _rows(s, user_id, toolkit)
    for c in rows:
        ca = _unseal(c).get("ca", "")
        if ca and configured():
            try:
                client().delete(ca)
            except ComposioError as e:
                log.warning("composio delete %s failed: %s", toolkit, e)
        c.status, c.token_enc = "revoked", ""
    s.flush()
    return bool(rows)


def apps(s, user_id: str) -> list[dict[str, Any]]:
    return [{"toolkit": slug, "pack_id": PREFIX + slug, "name": name, "does": what, "status": status(s, user_id, slug)}
            for slug, (name, what) in toolkits().items()]


# ---------------------------------------------------------------- webhook: a sign-in expired at the app
def verify_webhook(raw: bytes, wid: str, ts: str, sig_header: str, now: float | None = None) -> bool:
    secret = core_settings().composio_webhook_secret
    if not secret or not wid or not ts or not sig_header:
        return False
    try:
        if abs((now or time.time()) - int(ts)) > 300:
            return False
    except ValueError:
        return False
    keys = [secret.encode()]
    if secret.startswith("whsec_"):
        try:
            keys.append(base64.b64decode(secret.removeprefix("whsec_")))
        except ValueError:
            pass
    signed = f"{wid}.{ts}.".encode() + raw
    for key in keys:
        good = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        for part in sig_header.split():
            got = part.split(",", 1)[1] if "," in part else part
            if hmac.compare_digest(got, good):
                return True
    return False


def on_expired(s, ca: str) -> tuple[str, str] | None:
    """Closes the connection that holds this account id. (user_id, app name) to tell her, else None."""
    for c in s.scalars(select(Connection).where(Connection.provider.like(PROVIDER + "%"),
                                                Connection.status.in_(("active", "pending")))).all():
        if _unseal(c).get("ca") == ca:
            c.status = "expired"
            s.flush()
            kit = c.provider[len(PROVIDER):]
            return c.user_id, toolkits().get(kit, (kit, ""))[0]
    return None
