"""L1 packs: apps that publish an official agent endpoint (MCP) — Swiggy Food, Instamart, Dineout, Zomato, Zepto.

The user links their account once (the provider's OAuth/OTP flow, done in the app); the token is stored encrypted.
Santosh lists the provider's own tools and calls them. Any tool that places an order, pays or books is Tier 2:
the call is frozen server-side, the user sees a confirm card built from the provider's latest cart result, and only
then is the exact frozen call sent.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Protocol

from sqlalchemy import select

from ..db import Connection, Transaction
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees

CART_WORDS = ("cart", "checkout", "review", "summary", "bill")
TOTAL_KEYS = ("grand_total", "total_payable", "to_pay", "total_amount", "order_total", "total", "amount")


class RemoteTools(Protocol):
    def list_tools(self) -> list[dict[str, Any]]: ...
    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]: ...


class RemoteAuthError(Exception):
    """v0.162 the server refused the sign-in / key (HTTP 401 / 403)."""

    def __init__(self, status: int, www: str = ""):
        super().__init__(f"HTTP {status}")
        self.status, self.www = status, www


class RemoteError(Exception):
    """v0.162 any other failure, with the real reason instead of 'unhandled errors in a TaskGroup'."""


def _leaves(e: BaseException) -> list[BaseException]:
    subs = getattr(e, "exceptions", None)
    if subs:
        out: list[BaseException] = []
        for x in subs:
            out += _leaves(x)
        return out
    return [e]


def plain_error(e: BaseException) -> str:
    """The first real reason inside an exception group, in one short line."""
    for leaf in _leaves(e):
        msg = str(getattr(leaf, "message", "") or leaf).strip()
        if "TaskGroup" in msg:
            continue
        return (msg or type(leaf).__name__)[:300]
    return str(e)[:300]


class McpHttpRemote:
    """Sync wrapper over the official MCP Python SDK (streamable HTTP transport)."""

    def __init__(self, url: str, token: str | dict[str, str]):
        self.url, self.token = url, token
        self.seen: list[tuple[int, str]] = []   # v0.162 (status, www-authenticate) of every HTTP answer

    async def _note(self, r: Any) -> None:
        self.seen.append((r.status_code, r.headers.get("www-authenticate", "")))

    async def _with_session(self, fn: Callable[[Any], Any]) -> Any:
        self.seen = []
        try:
            return await self._session(fn)
        except BaseException as e:   # noqa: BLE001  ExceptionGroups from anyio task groups
            if isinstance(e, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
                raise
            for status, www in self.seen:
                if status in (401, 403):
                    raise RemoteAuthError(status, www) from None
            bad = [st for st, _ in self.seen if st >= 400]
            raise RemoteError((f"HTTP {bad[0]}: " if bad else "") + plain_error(e)) from None

    async def _session(self, fn: Callable[[Any], Any]) -> Any:
        from mcp import ClientSession
        if isinstance(self.token, dict):   # servers the user added: ready-made auth headers
            headers = dict(self.token)
        else:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:  # MCP Python SDK 2.x
            from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
        except ImportError:  # SDK 1.x
            from mcp.client.streamable_http import streamablehttp_client
            async with streamablehttp_client(self.url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await fn(session)
        async with create_mcp_http_client(headers=headers) as http:
            http.event_hooks["response"].append(self._note)
            async with streamable_http_client(self.url, http_client=http) as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await fn(session)

    @staticmethod
    def _attr(obj: Any, *names: str) -> Any:
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return None

    def list_tools(self) -> list[dict[str, Any]]:
        async def go(s):
            res = await s.list_tools()
            out = []
            for t in res.tools:
                ann = self._attr(t, "annotations")
                ro = self._attr(ann, "read_only_hint", "readOnlyHint") if ann is not None else None
                out.append({"name": t.name, "description": t.description or "",
                            "input_schema": self._attr(t, "input_schema", "inputSchema") or {"type": "object"},
                            "read_only": ro if isinstance(ro, bool) else None})   # v0.91 the server's hint (only a hint)
            return out
        return asyncio.run(self._with_session(go))

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        async def go(s):
            res = await s.call_tool(name, args)
            texts = [c.text for c in res.content if getattr(c, "type", "") == "text"]
            out: dict[str, Any] = {"is_error": bool(self._attr(res, "is_error", "isError")), "text": "\n".join(texts)}
            structured = self._attr(res, "structured_content", "structuredContent")
            if structured:
                out["data"] = structured
            else:
                for t in texts:
                    try:
                        out["data"] = json.loads(t)
                        break
                    except ValueError:
                        continue
            return out
        return asyncio.run(self._with_session(go))


def _refreshable(conn: Connection) -> bool:
    from ..security import vault
    try:
        raw = vault().open(conn.token_enc) if conn.token_enc else ""
        return raw.startswith("{") and bool(json.loads(raw).get("refresh_token"))
    except Exception:   # noqa: BLE001
        return False


def _find_total(obj: Any) -> int | None:
    """Best-effort: provider cart payloads differ. Returns paise. Rupee floats/strings are converted."""
    if isinstance(obj, dict):
        for k in TOTAL_KEYS:
            if k in obj and isinstance(obj[k], (int, float, str)):
                v = obj[k]
                try:
                    f = float(str(v).replace("₹", "").replace(",", ""))
                except ValueError:
                    continue
                if k.endswith("_paise") or (isinstance(v, int) and v > 100_000):
                    return int(f)
                return int(round(f * 100))
        for v in obj.values():
            t = _find_total(v)
            if t is not None:
                return t
    if isinstance(obj, list):
        for v in obj:
            t = _find_total(v)
            if t is not None:
                return t
    return None


def _find_items(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, dict):
        for k in ("items", "cart_items", "line_items", "products"):
            if isinstance(obj.get(k), list):
                out = []
                for it in obj[k][:20]:
                    if isinstance(it, dict):
                        name = it.get("name") or it.get("title") or it.get("item_name") or "Item"
                        q = it.get("quantity") or it.get("qty")
                        out.append({"name": f"{name}" + (f" × {q}" if q else ""), "price_paise": None})
                return out
        for v in obj.values():
            r = _find_items(v)
            if r:
                return r
    return []


class McpExecutor:
    name = "mcp"
    _cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    def __init__(self, remote_factory: Callable[[str, str], RemoteTools] | None = None):
        self.remote_factory = remote_factory or (lambda url, tok: McpHttpRemote(url, tok))

    def _endpoint(self, pack: Pack, ctx: Ctx) -> str:
        if pack.config.get("endpoint"):
            from ..custom_mcp import UrlError, check_url
            try:
                return check_url(pack.config["endpoint"])   # re-checked every time: DNS may have changed
            except UrlError as e:
                raise ToolError(f"{pack.name}: {e}")
        url = getattr(ctx.settings, pack.config["endpoint_setting"], "")
        if not url:
            raise ToolError(f"{pack.name} agent access is not configured yet.")
        return url

    def _conn(self, pack: Pack, ctx: Ctx) -> Connection | None:
        cfg = pack.config
        if cfg.get("custom") and cfg.get("auth") == "none":
            return None
        return ctx.session.scalars(select(Connection).where(Connection.user_id == ctx.user.id,
                                                            Connection.provider == cfg.get("provider"),
                                                            Connection.status == "active")).first()

    def _run(self, pack: Pack, ctx: Ctx, op: Callable[[RemoteTools], Any]) -> Any:
        """v0.162 one MCP round trip. A refused sign-in is refreshed once and tried again; still refused = she links
        it again (plain words, never 'unhandled errors in a TaskGroup')."""
        try:
            return op(self._remote(pack, ctx))
        except RemoteAuthError:
            conn = self._conn(pack, ctx)
            if conn is not None and _refreshable(conn):
                try:
                    return op(self._remote(pack, ctx, force=True))
                except (RemoteAuthError, ToolError):   # refresh refused too
                    pass
            if conn is not None:
                conn.status = "expired"   # kept even though the turn fails: the sign-in is really dead
                ctx.session.commit()
                self._cache.pop(pack.id + ":" + ctx.user.id, None)
            if pack.config.get("custom") and pack.config.get("auth") == "key":
                raise ToolError(f"NOT_LINKED: {pack.name} ne aapki API key / token mana kar di (galat, purani ya band). "
                                "Nayi key Hoola app > Connect > MCP servers mein daaliye (chat mein kabhi nahi).")
            raise ToolError(f"NOT_LINKED: {pack.name} ka sign-in khatam ho gaya. App > Connect > MCP servers > {pack.name} "
                            "par ek baar phir 'Link' dabaiye.")
        except RemoteError as e:
            raise ToolError(f"{pack.name} se baat nahi ho payi: {e}")

    def _remote(self, pack: Pack, ctx: Ctx, force: bool = False) -> RemoteTools:
        if pack.config.get("custom"):
            if pack.config.get("owner") != ctx.user.id:
                raise ToolError("Unknown pack. Use bazar_find first.")
            from ..custom_mcp import headers_for
            from ..mcp_auth import LinkError
            try:
                headers = headers_for(ctx.session, pack, ctx.user.id, force=force)
            except LinkError:
                headers = None
            if headers is None:
                if pack.config.get("auth") == "key":
                    raise ToolError(f"NOT_LINKED: {pack.name} needs its API key. Add it in the Hoola app > Connect > "
                                    "MCP servers (never send keys in chat).")
                raise ToolError(f"NOT_LINKED: Sign in to {pack.name} once (Hoola app > Connect > MCP servers > Link).")
            endpoint = self._endpoint(pack, ctx)
            from .. import runner as mcp_runner
            if mcp_runner.runner_url(endpoint):   # v0.154 one-tap server on the runner box: make sure it knows it
                mcp_runner.ensure(ctx.session, pack.id)
            return self.remote_factory(endpoint, headers)
        conn = ctx.session.scalars(select(Connection).where(Connection.user_id == ctx.user.id,
                                                            Connection.provider == pack.config["provider"],
                                                            Connection.status == "active")).first()
        if not conn:
            raise ToolError(f"NOT_LINKED: Link your {pack.name} account once (Hoola app > Connect tab > {pack.name}), "
                            "then I can order for you.")
        from ..mcp_auth import LinkError, access_token
        try:
            token = access_token(ctx.session, conn, force=force)
        except LinkError:
            raise ToolError(f"NOT_LINKED: Your {pack.name} sign-in expired. Please link it again in the Hoola app.")
        return self.remote_factory(self._endpoint(pack, ctx), token)

    def tool_specs(self, pack: Pack, ctx: Ctx, include_off: bool = False) -> list[ToolSpec]:
        key = pack.id + ":" + ctx.user.id
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < 600:
            tools = hit[1]
        else:
            tools = self._run(pack, ctx, lambda r: r.list_tools())
            self._cache[key] = (time.time(), tools)
        if pack.config.get("custom"):
            # v0.91 her switches: tools she turned off are never offered; the server's read-only hint is remembered
            from ...mcp_prefs import note_hints, prefs
            note_hints(pack.id, tools)
            if not include_off:
                mine = prefs(ctx.user.id, pack.id)
                tools = [t for t in tools if mine.get(t["name"], (True, None))[0]]
        return [ToolSpec(t["name"], f"[{pack.name}] {t['description']}"[:1000], t["input_schema"] or {"type": "object"},
                         pack.tier_of(t["name"])) for t in tools]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        if pack.config.get("custom"):
            from ...mcp_prefs import enabled
            if not enabled(ctx.user.id, pack.id, tool):
                raise ToolError(f"Owner ne {pack.name} ka '{tool}' tool band kar rakha hai (Connect > MCP servers > Tools). "
                                "Yeh nahi chalega; koi aur tarika batao ya owner se chalu karne ko kaho.")
        tier = pack.tier_of(tool)
        if tier >= 2 and pack.config.get("custom"):
            # a server the user added: show exactly what will be sent, run only that frozen call after the tap
            shown = json.dumps(args, ensure_ascii=False, default=str)
            shown = shown if len(shown) <= 600 else shown[:600] + "…"
            warn = " (handles money/code — check carefully)" if pack.config.get("caution") else ""
            return NeedsApproval(tier=2, title=f"{pack.name}: {tool}{warn}"[:200], payee=pack.name, amount_paise=0,
                                 items=[{"name": f"{tool}({shown})", "price_paise": None}],
                                 pay_method="No payment by Santosh; the server does this action",
                                 action={"executor": "mcp", "pack_id": pack.id, "name": tool, "args": args})
        state = dict((ctx.task.result or {}).get("mcp_last") or {}) if ctx.task else {}
        if tier >= 2:
            last = state.get(pack.id, {})
            total = _find_total(last.get("data")) if last else None
            low = tool.lower()
            if total is None and any(w in low for w in ("book", "reserv", "cancel")):
                # table bookings / cancellations have no cart: show exactly what will be sent
                summary = ", ".join(f"{k}: {v}" for k, v in list(args.items())[:8])[:300] or tool
                return NeedsApproval(tier=2, title=f"{pack.name}: {tool.replace('_', ' ')}", payee=pack.name, amount_paise=0,
                                     items=[{"name": summary, "price_paise": None}], pay_method=f"As per {pack.name}",
                                     action={"executor": "mcp", "pack_id": pack.id, "name": tool, "args": args})
            if total is None:
                raise ToolError("Show me the cart first: call the provider's cart or review tool before placing the order.")
            return NeedsApproval(tier=2, title="Confirm order", payee=pack.name, amount_paise=total,
                                 items=_find_items(last.get("data")) or [{"name": "Cart on " + pack.name, "price_paise": total}],
                                 pay_method=f"Payment inside {pack.name}",
                                 action={"executor": "mcp", "pack_id": pack.id, "name": tool, "args": args},
                                 preview={"provider_total": rupees(total)})
        res = self._run(pack, ctx, lambda r: r.call_tool(tool, args))
        if res.get("is_error"):
            raise ToolError(f"{pack.name} said: {res.get('text', '')[:300]}")
        if any(w in tool.lower() for w in CART_WORDS) and res.get("data") is not None:
            state[pack.id] = {"tool": tool, "data": res["data"], "at": time.time()}
            if ctx.task is not None:
                from sqlalchemy.orm.attributes import flag_modified
                ctx.task.result = {**(ctx.task.result or {}), "mcp_last": state}
                flag_modified(ctx.task, "result")
        return {"text": res.get("text", "")[:4000], "data": res.get("data")}

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        res = self._run(pack, ctx, lambda r: r.call_tool(action, args))
        if res.get("is_error"):
            raise ToolError(f"{pack.name} could not place it: {res.get('text', '')[:300]}")
        if pack.config.get("custom"):
            ctx.session.add(Transaction(user_id=ctx.user.id, task_id=ctx.task.id if ctx.task else "", kind="action",
                                        provider=pack.id, amount_paise=0, status="completed",
                                        meta={"tool": action, "args": args, "response": res.get("data") or res.get("text", "")[:2000]}))
            return {"status": "done", "provider": pack.name, "message": f"{pack.name}: {action} ho gaya.",
                    "response": res.get("data") or res.get("text", "")[:2000]}
        last = ((ctx.task.result if ctx.task else {}).get("mcp_last") or {}).get(pack.id, {})
        total = _find_total(last.get("data")) or 0
        ctx.session.add(Transaction(user_id=ctx.user.id, task_id=ctx.task.id if ctx.task else "", kind="order",
                                    provider=pack.id, amount_paise=total, status="completed",
                                    meta={"tool": action, "response": res.get("data") or res.get("text", "")[:2000]}))
        return {"status": "placed", "provider": pack.name, "response": res.get("data") or res.get("text", "")[:2000]}
