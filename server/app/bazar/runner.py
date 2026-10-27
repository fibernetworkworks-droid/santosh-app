"""One-tap MCP (v0.154): a directory server that is only a package (npm / PyPI / Docker's MCP catalogue) is run for the
user on the MCP runner box (server/mcp_runner, a SEPARATE machine), then joined like any hosted server.

Flow of `connect(tenant, ref, keys)`: refused if the directory blocks it or it works on her own computer -> safety
(trusted servers: OSV.dev malware lookup only; others: the runner's full check; 'caution' needs her OK, 'block' never
runs) -> the keys it needs (names from the listings' setup configs, or the names the server itself complains about) ->
the runner starts it in a locked container and lists its tools -> a normal MCP server row (`custom_mcp`) whose address is
the runner instance and whose key is that instance's own bearer token; her keys for the server are sealed here
(`RunnerSpec.env_enc`) and sent only on signed control calls. After a runner restart `ensure` registers it again.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any

from sqlalchemy import select

from .connectors.base import ToolError
from .db import CustomMcp, PackageCheck, RunnerSpec, now

CHECK_DAYS = 7
_ENSURED: dict[str, float] = {}
ENSURE_EVERY_S = 60
STATS = {"connected": 0, "checks": 0, "blocked": 0, "needs_keys": 0, "start_failed": 0, "ensured": 0}
_MISSING = re.compile(r"\b([A-Z][A-Z0-9]*_(?:[A-Z0-9_]*_)?(?:KEY|TOKEN|SECRET|PASSWORD|API_KEY|ID|URL|HOST|USER(?:NAME)?|"
                      r"PROJECT|ACCOUNT|DOMAIN|REGION|ORG|WORKSPACE|EMAIL))\b")


def _settings():
    from ..config import get_settings
    return get_settings()


def configured() -> bool:
    st = _settings()
    return bool(st.mcp_runner_url and st.mcp_runner_secret)


def sign(secret: str, method: str, path: str, ts: str, body: bytes) -> str:
    msg = f"{method}\n{path}\n{ts}\n".encode() + hashlib.sha256(body).hexdigest().encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


_client_factory = None   # tests put an httpx client here


def _ctl(method: str, path: str, obj: dict | None = None, timeout: float = 30) -> dict:
    import httpx
    st = _settings()
    body = json.dumps(obj or {}).encode() if method != "GET" else b""
    ts = str(int(time.time()))
    headers = {"X-Hoola-Time": ts, "X-Hoola-Sign": sign(st.mcp_runner_secret, method, path, ts, body),
               "Content-Type": "application/json"}
    client = _client_factory() if _client_factory else httpx.Client(timeout=timeout)
    try:
        r = client.request(method, st.mcp_runner_url.rstrip("/") + path, content=body or None, headers=headers,
                           timeout=timeout)
    except Exception as e:
        raise ToolError(f"MCP runner not reachable ({type(e).__name__}). Ask the admin to check it (Hoola Jaanch).")
    finally:
        if not _client_factory:
            client.close()
    if r.status_code == 401:
        raise ToolError("MCP runner refused Hoola's signature: MCP_RUNNER_SECRET differs on the two machines.")
    try:
        data = r.json()
    except ValueError:
        raise ToolError(f"MCP runner answered {r.status_code}.")
    if r.status_code >= 400:
        raise ToolError(f"MCP runner: {data.get('error', r.status_code)}")
    return data


def health() -> dict[str, Any]:
    if not configured():
        return {"configured": False, "say": "MCP runner set nahi hai (MCP_RUNNER_URL / MCP_RUNNER_SECRET)."}
    try:
        return {"configured": True, **_ctl("GET", "/v1/health", timeout=8)}
    except ToolError as e:
        return {"configured": True, "ok": False, "error": str(e)}


# ------------------------------------------------------------------------------------------------------------ safety
def check(s, kind: str, package: str, trusted: bool) -> dict[str, Any]:
    key = f"{kind}:{package}"[:240]
    row = s.get(PackageCheck, key)
    if row and now() - row.checked_at < dt.timedelta(days=CHECK_DAYS):
        return {"verdict": row.verdict, "reasons": row.reasons or [], "facts": row.facts or {}, "cached": True}
    STATS["checks"] += 1
    res = _ctl("POST", "/v1/check", {"kind": kind, "package": package}, timeout=90)
    verdict = res.get("verdict", "caution")
    if trusted and verdict == "caution" and not any("known security" in r for r in res.get("reasons", [])):
        verdict = "ok"     # trusted publishers: only malware / known-vulnerability findings slow them down
    if row is None:
        row = PackageCheck(key=key, verdict=verdict)
        s.add(row)
    row.verdict, row.reasons, row.facts, row.checked_at = verdict, res.get("reasons") or [], res.get("facts") or {}, now()
    return {"verdict": verdict, "reasons": row.reasons, "facts": row.facts, "cached": False}


def key_kind(name: str) -> str:
    return "secret" if re.search(r"KEY|TOKEN|SECRET|PASSWORD|PASS|PAT|CREDENTIAL", name) else "plain"


def _wanted(stderr: str, known: list[str]) -> list[str]:
    """Key names the server says it is missing ("FOO_API_KEY is required / not set / missing")."""
    out = []
    for line in stderr.splitlines()[-40:]:
        if re.search(r"(?i)required|missing|not set|must be set|no .* provided|environment variable|undefined|is empty", line):
            for n in _MISSING.findall(line):
                if n not in out and n not in ("NODE_ENV",):
                    out.append(n)
    return out[:6] or ([] if not known else [])


# ----------------------------------------------------------------------------------------------------------- connect
def connect(tenant_id: str, ref: str, keys: dict[str, str] | None = None, accept_caution: bool = False,
            probe_client=None) -> dict[str, Any]:
    """One tap on a directory server. Returns status ready | needs_keys | caution | blocked | failed."""
    from . import directory, service
    from .security import vault
    entry = directory.get(ref)
    if entry is None:
        raise ToolError("That server is not in the directory.")
    if entry.get("blocked"):
        raise ToolError(directory.NOT_ALLOWED.get(entry["blocked"], "This server can't be connected."))
    keys = {str(k).strip(): str(v).strip() for k, v in (keys or {}).items() if str(v).strip()}
    if entry.get("u"):        # hosted already: the normal add path (Apify ones take her Apify token)
        key = keys.get("APIFY_TOKEN") or keys.get("API_KEY") or next(iter(keys.values()), "")
        if entry.get("src") == "apify" and not key:
            return {"status": "needs_keys", "keys": [{"name": "APIFY_TOKEN", "kind": "secret"}],
                    "say": "Is Apify actor ke liye apna Apify API token app mein daaliye (Apify Console > Settings > "
                           "Integrations). Har run aapke Apify credit kharch karta hai."}
        return service.mcp_add(tenant_id, entry["u"], entry.get("t", ""), ref, key=key,
                               key_header="Authorization" if key else "", probe_client=probe_client)
    pkg = entry.get("pkg") or []
    if not pkg:
        raise ToolError(f"{entry.get('t')} has no package or address Hoola can run. See its page: {entry.get('l')}")
    if entry.get("pc"):
        return {"status": "pc_only", "say": f"{entry.get('t')} aapke apne computer ki files / apps par kaam karta hai, "
                                            "isliye ise aapke PC par chalana hoga (Hoola ke runner par nahi)."}
    if not configured():
        raise ToolError("One-tap MCP needs the MCP runner box (MCP_RUNNER_URL / MCP_RUNNER_SECRET on the server). "
                        "Ask the admin; until then add the server's https address by hand.")
    kind, package = pkg[0], pkg[1]
    from .db import session_factory
    s = session_factory()
    try:
        from .service import ensure_user
        user = ensure_user(s, tenant_id)
        verdict = check(s, kind, package, bool(entry.get("trusted")))
        s.commit()
        if verdict["verdict"] == "block":
            STATS["blocked"] += 1
            return {"status": "blocked", "reasons": verdict["reasons"],
                    "say": f"{entry.get('t')} suraksha jaanch mein fail hua, Hoola ise nahi chalayega: "
                           + "; ".join(verdict["reasons"][:3])}
        if verdict["verdict"] == "caution" and not accept_caution:
            return {"status": "caution", "reasons": verdict["reasons"],
                    "say": f"{entry.get('t')} mein kuch savdhani wali baatein mili: " + "; ".join(verdict["reasons"][:3])
                           + ". Aap kahein to phir bhi jodun? (app mein 'Phir bhi jodo')"}
        # keys: what the listing says it needs + what she saved before for this server
        old = s.scalars(select(RunnerSpec).join(CustomMcp, CustomMcp.id == RunnerSpec.id).where(
            RunnerSpec.user_id == user.id, RunnerSpec.package == package, CustomMcp.status == "active")).first()
        env: dict[str, str] = {}
        if old and old.env_enc:
            env.update(json.loads(vault().open(old.env_enc)))
        env.update(keys)
        missing = [n for n in entry.get("env") or [] if n not in env]
        if missing:
            STATS["needs_keys"] += 1
            return {"status": "needs_keys", "keys": [{"name": n, "kind": key_kind(n)} for n in missing],
                    "say": f"{entry.get('t')} ko ye chahiye: {', '.join(missing)}. App mein (Connect > MCP servers > "
                           f"{entry.get('t')}) daaliye; chat mein kabhi na bhejein."}
        iid = old.iid if old else secrets.token_hex(12)
        token = secrets.token_urlsafe(32)
        res = _ctl("POST", "/v1/instances", {"iid": iid, "kind": kind, "package": package, "version": "", "env": env,
                                             "token_sha256": hashlib.sha256(token.encode()).hexdigest(), "start": True},
                   timeout=240)
        if not res.get("ok"):
            STATS["start_failed"] += 1
            want = [n for n in _wanted(res.get("stderr", ""), entry.get("env") or []) if n not in env]
            if want:
                STATS["needs_keys"] += 1
                return {"status": "needs_keys", "keys": [{"name": n, "kind": key_kind(n)} for n in want],
                        "say": f"{entry.get('t')} chalne ke liye ye maang raha hai: {', '.join(want)}. App mein daaliye."}
            return {"status": "failed", "error": res.get("error", ""), "detail": (res.get("stderr") or "")[-600:],
                    "say": f"{entry.get('t')} runner par shuru nahi hua. Hoola ki galti nahi: package ne error diya."}
        url = _settings().mcp_runner_url.rstrip("/") + f"/mcp/{iid}"
    finally:
        s.close()
    out = service.mcp_add(tenant_id, url, entry.get("t", ""), ref, key=token, key_header="Authorization",
                          probe_client=probe_client, caution=verdict["verdict"] == "caution")
    s = session_factory()
    try:
        spec = s.get(RunnerSpec, out["pack_id"])
        if spec is None:
            spec = RunnerSpec(id=out["pack_id"], user_id=tenant_id, iid=iid, kind=kind, package=package)
            s.add(spec)
            if old and old.id != out["pack_id"]:
                s.delete(s.get(RunnerSpec, old.id))
        spec.iid, spec.env_enc = iid, vault().seal(json.dumps(env)) if env else ""
        spec.token_enc = vault().seal(token)
        s.commit()
    finally:
        s.close()
    _ENSURED[iid] = time.time()
    STATS["connected"] += 1
    out.update(tools=res.get("tools", []), runs_on="hoola_runner", checked=verdict["verdict"],
               say=f"{entry.get('t')} jud gaya ({len(res.get('tools', []))} tools), Hoola ke runner par chal raha hai.")
    return out


def runner_url(url: str) -> bool:
    base = _settings().mcp_runner_url.rstrip("/")
    return bool(base) and url.startswith(base + "/mcp/")


def ensure(s, row_id: str) -> None:
    """Before using a runner-backed server: make sure the runner knows it (after a runner restart it doesn't)."""
    from .security import vault
    spec = s.get(RunnerSpec, row_id)
    if spec is None or time.time() - _ENSURED.get(spec.iid, 0) < ENSURE_EVERY_S:
        return
    token = vault().open(spec.token_enc) if spec.token_enc else ""
    env = json.loads(vault().open(spec.env_enc)) if spec.env_enc else {}
    _ctl("POST", "/v1/instances", {"iid": spec.iid, "kind": spec.kind, "package": spec.package, "version": spec.version,
                                   "env": env, "token_sha256": hashlib.sha256(token.encode()).hexdigest()})
    _ENSURED[spec.iid] = time.time()
    STATS["ensured"] += 1


def forget(s, row_id: str) -> None:
    spec = s.get(RunnerSpec, row_id)
    if spec is None:
        return
    try:
        _ctl("DELETE", f"/v1/instances/{spec.iid}", {})
    except ToolError:
        pass
    _ENSURED.pop(spec.iid, None)
    s.delete(spec)
