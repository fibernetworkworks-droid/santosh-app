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


KEY_SCHEMES = ("API_KEY", "BEARER_TOKEN", "BASIC")   # v0.296 she types her own key; Newtika needs no credentials
SETUP_TEXT = ("{name} ka login Composio khud nahi deta (API-key / company app). Newtika ko ek baar Composio dashboard > "
              "Auth Configs mein {name} jodna hoga; uske baad sab users ke liye 'Jodiye' chalega.")


class ComposioError(Exception):
    """Composio refused or failed. `auth` = her sign-in is gone (she links again)."""

    def __init__(self, msg: str, status: int = 0, auth: bool = False):
        super().__init__(msg)
        self.status, self.auth = status, auth


def configured() -> bool:
    return bool(core_settings().composio_api_key)


def toolkits() -> dict[str, tuple[str, str]]:
    """Every app she may connect: Composio's live catalogue when the key works (about 1,600), else the built-in 21.
    COMPOSIO_TOOLKITS (comma list) narrows it. Hoola's own apps and scraping apps are never in it."""
    cat = catalog()
    base = {s: (a["name"], a["desc"] or "its tools") for s, a in cat.items()} if cat else dict(DEFAULT_TOOLKITS)
    raw = (core_settings().composio_toolkits or "").strip()
    if not raw:
        return base
    out: dict[str, tuple[str, str]] = {}
    for slug in re.split(r"[,\s]+", raw.lower()):
        if re.fullmatch(r"[a-z0-9_]{2,60}", slug or "") and slug not in NEVER:
            out[slug] = base.get(slug) or DEFAULT_TOOLKITS.get(slug, (slug.replace("_", " ").title(), "its tools"))
    return out


# ---------------------------------------------------------------- v0.294 the live catalogue (GET /toolkits)
CATALOG_TTL = 12 * 3600
CATALOG_RETRY = 600          # Composio down / key wrong: try again after 10 min, built-in list meanwhile
_catalog: tuple[float, dict[str, dict[str, Any]]] | None = None
_catalog_fail = 0.0
_configs: tuple[float, set[str]] | None = None


def _clean_app(it: dict[str, Any]) -> dict[str, Any] | None:
    slug = str(it.get("slug") or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{2,60}", slug) or slug in NEVER or str(it.get("type") or "native") == "custom":
        return None
    meta = it.get("meta") or {}
    cats = [str(c.get("name") or c.get("slug") or "") if isinstance(c, dict) else str(c)
            for c in (meta.get("categories") or [])]
    managed = bool(it.get("composio_managed_auth_schemes"))
    schemes = [str(x).upper() for x in (it.get("auth_schemes") or [])]
    key_scheme = next((x for x in KEY_SCHEMES if x in schemes), "")
    return {"slug": slug, "name": str(it.get("name") or slug.replace("_", " ").title())[:80],
            "desc": re.sub(r"\s+", " ", str(meta.get("description") or ""))[:220],
            "logo": str(meta.get("logo") or "")[:400], "cats": [c for c in cats if c][:4],
            "app_url": str(meta.get("app_url") or "")[:300],
            "tools": int(meta.get("tools_count") or 0), "managed": managed, "no_auth": bool(it.get("no_auth")),
            "schemes": schemes[:4], "key_scheme": key_scheme}


def catalog(force: bool = False) -> dict[str, dict[str, Any]]:
    """slug -> app, in Composio's own usage order. {} when not configured or never reachable."""
    global _catalog, _catalog_fail
    if not configured():
        return {}
    now = time.time()
    if not force and _catalog and now - _catalog[0] < CATALOG_TTL:
        return _catalog[1]
    if not force and now - _catalog_fail < CATALOG_RETRY:
        return _catalog[1] if _catalog else {}
    try:
        items: list[dict[str, Any]] = []
        cursor = None
        for _ in range(10):
            params: dict[str, Any] = {"limit": 1000, "sort_by": "usage"}
            if cursor:
                params["cursor"] = cursor
            res = client()._req("GET", "/toolkits", params=params)
            items += res.get("items") or []
            cursor = res.get("next_cursor")
            if not cursor:
                break
    except ComposioError as e:
        log.warning("composio catalogue failed: %s", e)
        _catalog_fail = now
        return _catalog[1] if _catalog else {}
    out: dict[str, dict[str, Any]] = {}
    for it in items:
        a = _clean_app(it) if isinstance(it, dict) else None
        if a and a["slug"] not in out:
            out[a["slug"]] = a
    if out:
        _catalog = (now, out)
    else:
        _catalog_fail = now
    return out or (_catalog[1] if _catalog else {})


def configured_apps(force: bool = False) -> set[str]:
    """Apps Newtika set up in the Composio dashboard (an ENABLED auth config): API-key apps become connectable."""
    global _configs
    if _configs and not force and time.time() - _configs[0] < 600:
        return _configs[1]
    slugs: set[str] = set()
    try:
        cursor = None
        for _ in range(5):
            params: dict[str, Any] = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            res = client()._req("GET", "/auth_configs", params=params)
            for i in res.get("items") or []:
                if str(i.get("status", "ENABLED")).upper() == "ENABLED":
                    slugs.add(str((i.get("toolkit") or {}).get("slug") or "").lower())
            cursor = res.get("next_cursor")
            if not cursor:
                break
    except ComposioError as e:
        log.warning("composio auth configs failed: %s", e)
        return _configs[1] if _configs else set()
    _configs = (time.time(), slugs)
    return slugs


def mode(toolkit: str) -> str:
    """managed = her own sign-in works now; no_auth = nothing to connect; key = she types HER key for that app in the
    Hoola app (v0.296, Newtika needs nothing); setup = an OAuth app Composio has no login for (Newtika's own developer
    app once in the dashboard); unknown = not in the live catalogue."""
    a = catalog().get(toolkit)
    if a is None:
        return "managed" if toolkit in DEFAULT_TOOLKITS and not catalog() else "unknown"
    if a["no_auth"]:
        return "no_auth"
    if a["managed"]:
        return "managed"
    if a.get("key_scheme"):
        return "key"
    if toolkit in configured_apps():
        return "managed"
    return "setup"


def key_fields(toolkit: str) -> list[dict[str, Any]]:
    """What she types for a key app, from GET /toolkits/{slug} (auth_config_details[mode].fields
    .connected_account_initiation). Composio documents the list but not each item's keys, so every common spelling is
    read; when nothing usable comes back, the scheme's plain fields are used."""
    a = catalog().get(toolkit) or {}
    scheme = a.get("key_scheme") or "API_KEY"

    def go() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            det = client()._req("GET", f"/toolkits/{toolkit}")
        except ComposioError:
            det = {}
        for d in det.get("auth_config_details") or []:
            if str(d.get("mode") or "").upper().replace("-", "_") != scheme:
                continue
            init = ((d.get("fields") or {}).get("connected_account_initiation") or {})
            for need, items in ((True, init.get("required") or []), (False, init.get("optional") or [])):
                for f in items:
                    if not isinstance(f, dict):
                        continue
                    name = str(f.get("name") or f.get("key") or "").strip()
                    if not re.fullmatch(r"[A-Za-z0-9_]{1,60}", name):
                        continue
                    label = str(f.get("displayName") or f.get("display_name") or f.get("label") or name.replace("_", " ").title())
                    secret = bool(f.get("is_secret") or f.get("isSecret") or f.get("secret")) or bool(
                        re.search(r"key|token|secret|password", name, re.I))
                    out.append({"name": name, "label": label[:60], "required": need, "secret": secret,
                                "hint": str(f.get("description") or "")[:200]})
        if not out:
            out = {"BEARER_TOKEN": [{"name": "token", "label": "Token", "required": True, "secret": True, "hint": ""}],
                   "BASIC": [{"name": "username", "label": "Username", "required": True, "secret": False, "hint": ""},
                             {"name": "password", "label": "Password", "required": True, "secret": True, "hint": ""}],
                   }.get(scheme, [{"name": "api_key", "label": "API key", "required": True, "secret": True, "hint": ""}])
        return out[:8]
    return _cached("fields:" + toolkit, go)


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
            m = mode(toolkit)
            name = toolkits().get(toolkit, (toolkit, ""))[0]
            if m == "key":   # v0.296 her key comes at connect time: no Newtika credentials (empty credentials)
                body = {"toolkit": {"slug": toolkit},
                        "auth_config": {"type": "use_custom_auth", "authScheme": catalog()[toolkit]["key_scheme"],
                                        "name": f"Hoola {name}"[:60], "credentials": {}}}
            elif m == "managed":
                body = {"toolkit": {"slug": toolkit}, "auth_config": {"type": "use_composio_managed_auth"}}
            else:
                raise ComposioError(SETUP_TEXT.format(name=name))
            made = self._req("POST", "/auth_configs", body=body)
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
        body: dict[str, Any] = {"user_id": user_id, "arguments": arguments, "version": "latest"}
        if ca_id:                       # a no-login app (weather, maths ...) has no account to name
            body["connected_account_id"] = ca_id
        return self._req("POST", f"/tools/execute/{slug}", body=body)


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
    global _client, _catalog, _catalog_fail, _configs
    _client = c
    _catalog, _catalog_fail, _configs = None, 0.0, None
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
    """v0.294 many apps mark no tool 'important': then the first tools of the app (it was an empty list before,
    so Hoola had nothing to run)."""
    def go():
        items = client().tools(toolkit, query=query, important=important, limit=limit)
        if not items and important:
            items = client().tools(toolkit, query=query, important=False, limit=limit)
        return items
    return _cached(f"list:{toolkit}:{query}:{important}:{limit}", go)


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
    what = (what or "its tools")[:160]
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


def match(query: str, limit: int = 4, mine: tuple[str, ...] = ()) -> list[Pack]:
    """Apps her words name ('slack pe message', 'notion page'). Only the well-known apps and the ones she already
    joined are matched by name - with 1,600 apps a plain word ('box', 'news', 'weather') would pick a random one;
    the rest are found with composio_apps action=list query=...."""
    q = query.lower()
    kits = toolkits()
    out = []
    for slug in list(DEFAULT_TOOLKITS) + [m for m in mine if m not in DEFAULT_TOOLKITS]:
        if slug not in kits:
            continue
        name = kits[slug][0]
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
    """ready / pending / needs_link / needs_setup (Newtika must set the app up once) / not_configured."""
    if not configured():
        return "not_configured"
    rows = _rows(s, user_id, toolkit)
    if any(r.status == "active" for r in rows):
        return "ready"
    m = mode(toolkit)
    if m == "no_auth":
        return "ready"
    if m in ("setup", "unknown"):
        return "needs_setup"
    if m == "key":
        return "needs_key"
    return "pending" if rows else "needs_link"


def joined(s, user_id: str) -> list[str]:
    rows = s.scalars(select(Connection.provider).where(Connection.user_id == user_id,
                                                       Connection.provider.like(PROVIDER + "%"),
                                                       Connection.status.in_(("active", "pending")))).all()
    return sorted({r[len(PROVIDER):] for r in rows})


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


def connect_key(s, user_id: str, toolkit: str, values: dict[str, Any]) -> dict[str, Any]:
    """v0.296 her own key for a key app, typed in the Hoola app (never in chat), goes straight to Composio, which checks
    it with the app before saving. Hoola keeps only the account id (sealed), never the key."""
    if mode(toolkit) != "key":
        raise ComposioError("Is app mein key nahi, sign-in hota hai: 'Jodiye' dabaiye.")
    fields = {f["name"]: f for f in key_fields(toolkit)}
    clean: dict[str, str] = {}
    for k, v in (values or {}).items():
        if k in fields and isinstance(v, (str, int)) and str(v).strip():
            val = str(v).strip()
            if len(val) > 4000:
                raise ComposioError(f"{fields[k]['label']} bahut lamba hai.")
            clean[k] = val
    missing = [f["label"] for f in fields.values() if f["required"] and f["name"] not in clean]
    if missing:
        raise ComposioError("Yeh bhi chahiye: " + ", ".join(missing))
    scheme = catalog()[toolkit]["key_scheme"]
    cl = client()
    try:
        res = cl._req("POST", "/connected_accounts",
                      body={"auth_config": {"id": cl.auth_config_id(toolkit)},
                            "connection": {"user_id": composio_user(user_id),
                                           "state": {"authScheme": scheme, "val": {"status": "ACTIVE", **clean}}}})
    except ComposioError as e:
        if "Validation" in str(e) or e.status in (400, 422):
            raise ComposioError(f"{toolkits()[toolkit][0]} ne yeh key nahi maani. Sahi key dobara daaliye.", e.status)
        raise
    ca = str(res.get("id") or (res.get("connected_account") or {}).get("id") or "")
    if not ca:
        raise ComposioError("Composio ne account nahi banaya; thodi der baad try kijiye.")
    for c in _rows(s, user_id, toolkit):
        c.status = "replaced"
    st = _status_of(res) or "ACTIVE"
    s.add(Connection(user_id=user_id, provider=PROVIDER + toolkit, token_enc=_seal({"ca": ca}),
                     status="active" if st == "ACTIVE" else "pending"))
    s.flush()
    return {"status": "ready" if st == "ACTIVE" else "pending", "name": toolkits()[toolkit][0], "pack_id": PREFIX + toolkit}


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


def apps(s, user_id: str, q: str = "", category: str = "", offset: int = 0, limit: int = 40) -> dict[str, Any]:
    """The catalogue for her screen / the chat: her joined apps first, then Composio's usage order; search + category."""
    cat = catalog()
    kits = toolkits()
    mine = set(joined(s, user_id))
    q = (q or "").strip().lower()[:60]
    category = (category or "").strip().lower()
    rows = []
    for slug, (name, what) in kits.items():
        a = cat.get(slug) or {"logo": "", "cats": [], "tools": 0}
        if q and q not in slug and q not in name.lower() and q not in (what or "").lower():
            continue
        if category and category not in [c.lower() for c in a["cats"]]:
            continue
        rows.append((slug, name, what, a))
    rows.sort(key=lambda r: (r[0] not in mine, q and not (r[0].startswith(q) or r[1].lower().startswith(q))))
    counts: dict[str, int] = {}
    for a in cat.values():
        for c in a["cats"]:
            counts[c] = counts.get(c, 0) + 1
    offset, limit = max(0, int(offset or 0)), max(1, min(int(limit or 40), 200))
    from .logos import composio_logo
    page = [{"toolkit": slug, "pack_id": PREFIX + slug, "name": name, "does": (what or "")[:160],
             "logo": composio_logo(slug) if slug in cat else None,
             "category": (a["cats"] or [""])[0], "tools": a["tools"], "status": status(s, user_id, slug)}
            for slug, name, what, a in rows[offset:offset + limit]]
    return {"total": len(rows), "all": len(kits), "offset": offset, "apps": page, "live": bool(cat),
            "categories": sorted(counts.items(), key=lambda x: -x[1])[:40]}


def check() -> dict[str, Any]:
    """v0.294 the self-check she runs on the VPS (python -m app.bazar.composio check): no secrets in the output."""
    out: dict[str, Any] = {"key_set": configured()}
    if not configured():
        out["fix"] = "COMPOSIO_API_KEY ~/apps/santosh-core/.env mein nahi hai."
        return out
    try:
        res = client()._req("GET", "/toolkits", params={"limit": 1})
        out["key_works"] = True
        out["composio_says_total"] = res.get("total_items")
    except ComposioError as e:
        out["key_works"] = False
        out["error"] = str(e)
        out["fix"] = ("Key galat / purani hai: platform.composio.dev > project > Settings > API Keys se project key "
                      "copy karke .env mein dobara daaliye." if e.status in (401, 403) else "Composio tak pahunch nahi.")
        return out
    cat = catalog(force=True)
    conf = configured_apps(force=True)
    modes = {"managed": 0, "no_auth": 0, "key": 0, "setup": 0}
    for slug in cat:
        modes[mode(slug)] = modes.get(mode(slug), 0) + 1
    out.update({"apps_in_catalogue": len(cat), "connect_now": modes["managed"], "no_login_needed": modes["no_auth"],
                "key_apps_user_types_own_key": modes["key"], "need_newtika_setup": modes["setup"],
                "dashboard_auth_configs": len(conf)})
    out["built_in_21"] = {slug: (mode(slug) if slug in cat else "NOT IN COMPOSIO") for slug in DEFAULT_TOOLKITS}
    return out


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


if __name__ == "__main__":   # python -m app.bazar.composio check | list [query]
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "trykey":   # live check of one key app: mode, fields, and the auth config Hoola creates (no user key used)
        slug = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
        catalog(force=True)
        out: dict[str, Any] = {"app": slug, "mode": mode(slug), "fields": key_fields(slug) if mode(slug) == "key" else []}
        if out["mode"] == "key":
            try:
                out["auth_config_id"] = client().auth_config_id(slug)
            except ComposioError as e:
                out["auth_config_error"] = str(e)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        sys.exit(0)
    if cmd == "list":
        q = " ".join(sys.argv[2:]).lower()
        for slug, a in catalog(force=True).items():
            if not q or q in slug or q in a["name"].lower() or q in a["desc"].lower():
                print(f"{slug:32} {a['name'][:30]:30} {mode(slug):8} {a['tools']:4} tools  {', '.join(a['cats'][:2])}")
    else:
        print(json.dumps(check(), indent=2, ensure_ascii=False))
