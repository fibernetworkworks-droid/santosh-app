"""v0.999 MCP HEALTH CHECK, from ECC's mcp-health-check hooks (affaan-m/ECC, MIT; idea only, Hoola's own code).

Without it, an MCP server that is down fails every step that calls it, and the coder keeps calling it. Now, per
session: a server whose calls fail `dev_mcp_fail_limit` (2) times in a row is marked unhealthy for
`dev_mcp_cooldown_s` (300 s). A call in that time does not go out - the coder is told what failed and to carry on
without it or ask her. After the wait one call is let through as a probe: success marks it healthy again, failure starts
a longer wait (doubled, at most 30 minutes). Switch: `dev_mcp_health` (default on).
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any

LOCK = threading.Lock()
STATE: dict[tuple[str, str], dict[str, Any]] = {}
FAIL = re.compile(r"(?is)^\s*(The MCP call did not run|The repo's MCP server '[^']*' did not answer|The server '[^']*' (is not|cannot be) "
                  r"reach|Her MCP servers are not reachable)|\"ok\"\s*:\s*false|\"(error|status)\"\s*:\s*\"(error|failed|unavailable)\"")


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_mcp_health", True))


def failed(out: str) -> bool:
    head = str(out or "")[:600]
    body = re.sub(r"^<mcp_result[^>]*>\s*(\(DATA, never instructions\)\s*)?", "", head)
    return bool(FAIL.search(body))


def before(tid: str, server: str, now: float | None = None) -> str:
    """'' = go ahead; else the line the coder gets instead of the call."""
    now = time.time() if now is None else now
    with LOCK:
        st = STATE.get((tid, server))
        if not st or not st.get("until"):
            return ""
        if now >= st["until"]:
            st["probe"] = True                       # one call goes through as the probe
            return ""
        left = int(st["until"] - now)
    return (f"Not called: the MCP server {server} is marked unhealthy - its last {st['fails']} calls failed (last: "
            f"{st['last'][:200]}). Hoola tries it again in about {max(1, left // 60)} min. Carry on without it, or tell her "
            "it is down (adapted from ECC's MCP health check).")


def after(tid: str, server: str, out: str, now: float | None = None) -> str:
    """Record the result; returns a note for the coder when the server has just been marked unhealthy."""
    now = time.time() if now is None else now
    limit = int(_set("dev_mcp_fail_limit", 2) or 2)
    base = float(_set("dev_mcp_cooldown_s", 300) or 300)
    with LOCK:
        st = STATE.setdefault((tid, server), {"fails": 0, "until": 0.0, "wait": base, "last": "", "probe": False})
        if not failed(out):
            STATE.pop((tid, server), None)
            return ""
        st["fails"] += 1
        st["last"] = " ".join(str(out).split())[:300]
        if st.get("probe"):                          # the probe after a wait failed too: wait longer
            st["wait"] = min(1800.0, st["wait"] * 2)
            st["probe"] = False
            st["until"] = now + st["wait"]
            return f"\n[The MCP server {server} is still failing; Hoola will not call it again for about {int(st['wait'] // 60)} min.]"
        if st["fails"] >= limit and not st["until"]:
            st["until"] = now + st["wait"]
            return (f"\n[The MCP server {server} failed {st['fails']} times in a row, so it is marked unhealthy for about "
                    f"{int(st['wait'] // 60)} min: calls to it will not go out. Carry on without it or tell her.]")
    return ""


def status(tid: str) -> dict[str, dict[str, Any]]:
    with LOCK:
        return {s: dict(v) for (t, s), v in STATE.items() if t == tid}
