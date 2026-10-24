"""v0.92 Hoola Jaanch: one button that checks every part of Hoola live and says the fix in plain words.

Roadmap day 1 ("measure"). Every check runs at the same time with its own short time limit, so the whole check takes
about 10 seconds. Nothing is sent anywhere except harmless reads (model list, a TCP handshake to a site, the browser
worker's /healthz). Keys are never shown: a check only says "set" / "not set" / "refused".

Also the work report of the last 14 days (chat tasks, website jobs, PC jobs, lessons, crashes), which used to need a
command on the VPS.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import socket
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import get_settings

log = logging.getLogger("santosh.jaanch")
CHECK_TIMEOUT = 9.0
PORTALS = [("UIDAI (Aadhaar)", "myaadhaar.uidai.gov.in"), ("Income Tax", "www.incometax.gov.in"),
           ("DigiLocker", "www.digilocker.gov.in"), ("IRCTC", "www.irctc.co.in"),
           ("EPFO", "unifiedportal-mem.epfindia.gov.in"), ("Passport Seva", "www.passportindia.gov.in"),
           ("MSEDCL", "wss.mahadiscom.in"), ("GST", "www.gst.gov.in")]


def _c(cid: str, name: str, ok: bool | None, detail: str = "", fix: str = "") -> dict[str, Any]:
    """ok True = fine, False = broken (with a fix), None = works but needs attention / not set up."""
    return {"id": cid, "name": name, "ok": ok, "detail": detail[:300], "fix": fix[:300]}


def _tcp(host: str, port: int, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return False, "naam nahi mila (DNS)"
    ips = sorted({i[4][0] for i in infos}, key=lambda x: ":" in x)
    last = "nahi juda"
    for ip in ips[:3]:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True, ""
        except socket.timeout:
            last = "jawab nahi diya (timeout)"
        except OSError as e:
            last = f"{type(e).__name__}: {str(e)[:60]}"
    return False, last


# ---------------------------------------------------------------- the checks (each returns one line)
async def _claude() -> dict[str, Any]:
    st = get_settings()
    if not st.anthropic_api_key:
        return _c("claude", "Dimaag (Claude)", False, "ANTHROPIC_API_KEY set nahi hai", "VPS .env mein ANTHROPIC_API_KEY daaliye")
    try:
        from .agent.santosh import get_client
        client = get_client()
        if hasattr(client, "models"):
            await client.models.list(limit=1)
        else:
            ok, why = await asyncio.to_thread(_tcp, "api.anthropic.com", 443)
            if not ok:
                raise ConnectionError(why)
        return _c("claude", "Dimaag (Claude)", True, f"model {st.anthropic_model}")
    except Exception as e:
        t = str(e)
        fix = "key badliye (console.anthropic.com)" if "401" in t or "auth" in t.lower() else "thodi der baad phir jaanchiye"
        return _c("claude", "Dimaag (Claude)", False, f"Anthropic ne mana kiya: {type(e).__name__}", fix)


async def _app_model() -> dict[str, Any]:
    """v0.140 App Sahayak designs and builds only with Claude Opus 5.5: is that model open on this key?"""
    from .site import ai as SA
    st = get_settings()
    label = SA.app_model_label()
    if not st.anthropic_api_key:
        return _c("app_model", "App design (" + label + ")", False, "ANTHROPIC_API_KEY set nahi hai",
                  "VPS .env mein ANTHROPIC_API_KEY daaliye")
    try:
        from .agent.santosh import get_client
        client = get_client()
        if hasattr(client, "models") and hasattr(client.models, "retrieve"):
            await client.models.retrieve(SA.app_model())
        s = SA.STATS
        return _c("app_model", "App design (" + label + ")", True,
                  f"{label} khula hai · {s['app_calls']} calls, {s['app_retries']} dobara, {s['app_failed']} fail")
    except Exception as e:
        t = str(e)
        fix = ("console.anthropic.com par is key ke liye Opus 5.5 kholiye" if "404" in t or "not_found" in t.lower()
               else "thodi der baad phir jaanchiye")
        return _c("app_model", "App design (" + label + ")", False, f"{label} nahi khula: {type(e).__name__}", fix)


async def _gemini() -> dict[str, Any]:
    st = get_settings()
    if not st.gemini_api_key:
        return _c("gemini", "Awaaz + Google search (Gemini)", False, "GEMINI_API_KEY set nahi hai",
                  "VPS .env mein GEMINI_API_KEY daaliye (voice call aur Google search isi se chalte hain)")
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("https://generativelanguage.googleapis.com/v1beta/models",
                            params={"pageSize": 1}, headers={"x-goog-api-key": st.gemini_api_key})
        if r.status_code == 200:
            return _c("gemini", "Awaaz + Google search (Gemini)", True, f"live model {st.gemini_live_model}")
        return _c("gemini", "Awaaz + Google search (Gemini)", False, f"Google ne HTTP {r.status_code} diya",
                  "key check kijiye (aistudio.google.com)")
    except Exception as e:
        return _c("gemini", "Awaaz + Google search (Gemini)", False, f"pahunch nahi: {type(e).__name__}", "server ka internet dekhiye")


async def _parallel() -> dict[str, Any]:
    st = get_settings()
    if not st.parallel_search:
        return _c("parallel", "Backup search (Parallel)", None, "band hai (PARALLEL_SEARCH=false)")
    ok, why = await asyncio.to_thread(_tcp, "search.parallel.ai", 443)
    return _c("parallel", "Backup search (Parallel)", ok, "" if ok else why, "" if ok else "server ka internet dekhiye")


async def _email(tenant: str) -> dict[str, Any]:
    st = get_settings()
    api = []
    try:
        from .mailbox.accounts import boxes
        api = [b.address for b in await asyncio.to_thread(boxes, tenant) if getattr(b, "kind", "") in ("gmail", "outlook")]
    except Exception:
        pass
    smtp_ok, smtp_why = None, ""
    if st.email_address and st.email_password:
        from . import mail
        try:
            _, _, host, port = mail._hosts()
            smtp_ok, smtp_why = await asyncio.to_thread(_tcp, host, int(port), 6.0)
        except Exception as e:
            smtp_ok, smtp_why = False, str(e)[:80]
    if api:
        d = "Gmail / Outlook sign-in se jata hai: " + ", ".join(api[:2])
        if smtp_ok is False:
            d += "; server ka SMTP band hai (koi baat nahi, sign-in wala raasta kaam karta hai)"
        return _c("email", "Email bhejna", True, d)
    if smtp_ok:
        return _c("email", "Email bhejna", True, "server ke SMTP se")
    if smtp_ok is False:
        return _c("email", "Email bhejna", False, f"server se SMTP nahi pahunchta ({smtp_why}); cloud server SMTP port rokte hain",
                  "App > Profile > Email mein Google se sign in kijiye: email Gmail ke raaste (HTTPS) jayega")
    return _c("email", "Email bhejna", None, "koi email nahi juda", "App > Profile > Email mein Gmail / Outlook jodiye")


async def _operator() -> dict[str, Any]:
    from .operator import service as ops
    from .operator.display import chrome_installed
    if not ops.available():
        return _c("operator", "Website kaam (Computer Operator)", False, "Playwright / Chromium nahi mila",
                  "VPS par: bash ~/santosh_app/server/deploy/setup_operator.sh")
    chrome, xvfb = chrome_installed(), bool(shutil.which("Xvfb"))
    if chrome and xvfb:
        return _c("operator", "Website kaam (Computer Operator)", True, "asli Chrome window (virtual screen) taiyaar")
    miss = ", ".join(x for x, ok in (("Google Chrome", chrome), ("Xvfb", xvfb)) if not ok)
    return _c("operator", "Website kaam (Computer Operator)", None,
              f"{miss} nahi mila: browser 'HeadlessChrome' ban jata hai, kai sites rok deti hain",
              "VPS par: bash ~/santosh_app/server/deploy/setup_operator.sh")


async def _worker() -> dict[str, Any]:
    st = get_settings()
    if not st.browser_worker_url:
        return _c("browser", "Jaldi website dekhna (browse_web)", None, "browser worker set nahi hai (BROWSER_WORKER_URL)")
    import httpx
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.get(st.browser_worker_url.rstrip("/") + "/healthz")
        ok = r.status_code == 200
        return _c("browser", "Jaldi website dekhna (browse_web)", ok, "" if ok else f"HTTP {r.status_code}",
                  "" if ok else "pm2 restart santosh-browser")
    except Exception as e:
        return _c("browser", "Jaldi website dekhna (browse_web)", False, f"worker band hai ({type(e).__name__})",
                  "pm2 restart santosh-browser")


async def _pc(tenant: str) -> dict[str, Any]:
    try:
        from .pc.hub import hub
        conns = hub.online(tenant)
    except Exception:
        conns = []
    if not conns:
        return _c("pc", "Mera PC (Santosh Desktop)", None, "PC abhi juda nahi hai",
                  "PC par Santosh Desktop kholiye; jo sites server se nahi khultin (UIDAI) woh PC se hongi")
    control = bool((conns[-1].info or {}).get("control"))
    return _c("pc", "Mera PC (Santosh Desktop)", True if control else None,
              "juda hai" + ("" if control else ", par PC chalane ki permission band hai"),
              "" if control else "Santosh Desktop > Settings > 'Santosh ko PC chalane dein' on kijiye")


async def _push() -> dict[str, Any]:
    from . import push
    ok = push.configured()
    return _c("push", "Phone par notification (FCM)", ok if ok else None, "" if ok else "FCM set nahi hai",
              "" if ok else "VPS par FCM service-account file ka path FCM_SERVICE_ACCOUNT_FILE mein daaliye")


async def _mcp_runner() -> dict[str, Any]:
    from .bazar import runner as mcp_runner
    h = await asyncio.to_thread(mcp_runner.health)
    if not h.get("configured"):
        return _c("mcp_runner", "Ek-tap MCP (runner)", None, "MCP runner set nahi hai: npm / PyPI servers ek tap mein nahi judenge",
                  "Alag machine par server/deploy/setup_mcp_runner.sh chalaiye, phir MCP_RUNNER_URL / MCP_RUNNER_SECRET .env mein")
    if h.get("ok"):
        return _c("mcp_runner", "Ek-tap MCP (runner)", True, f"{h.get('running', 0)} chal rahe, {h.get('instances', 0)} jude", "")
    return _c("mcp_runner", "Ek-tap MCP (runner)", False, h.get("error", "runner jawab nahi de raha"),
              "Runner machine par: systemctl status hoola-mcp-runner")


async def _google(tenant: str) -> dict[str, Any]:
    try:
        from .google_check import diagnose
        d = await asyncio.to_thread(diagnose, tenant, False)
    except Exception as e:
        return _c("google", "Google (Drive / Gmail / Calendar)", None, f"jaanch nahi ho payi ({type(e).__name__})")
    if not d.get("signin"):
        return _c("google", "Google (Drive / Gmail / Calendar)", None, "Google se sign in nahi hai", "App > Profile mein Google jodiye")
    probs = d.get("problems") or []
    return _c("google", "Google (Drive / Gmail / Calendar)", not probs, "; ".join(probs)[:200] or "juda hai",
              "App mein 'Google jodiye' dobara dabaiye" if probs else "")


async def _disk() -> dict[str, Any]:
    u = shutil.disk_usage(".")
    free = u.free / 1e9
    ok = free >= 2
    return _c("disk", "Server ki jagah (disk)", ok if free >= 2 else (None if free >= 0.5 else False), f"{free:.1f} GB khaali",
              "" if ok else "purani files / logs hataiye (pm2 flush)")


async def _memory(tenant: str) -> dict[str, Any]:
    """v0.108 Hoola ki yaad: auto memory on, meaning search, index filling up."""
    from . import yaad
    h = await asyncio.to_thread(yaad.health, tenant)
    probs = []
    if not h["auto_memory"]:
        probs.append("apne aap yaad rakhna band hai (MEMORY_AUTO=false)")
    if not h["meaning_search"]:
        probs.append("matlab se dhoondhna band (fastembed / model nahi); sirf shabd se milta hai")
    detail = f"{h['items']} yaadein, {h['facts']} facts ({h['auto_facts']} apne aap), window {h['window']} baatein"
    return _c("memory", "Hoola ki yaad", None if probs else True, detail + ("; " + "; ".join(probs) if probs else ""),
              "VPS: .venv/bin/pip install fastembed (ek baar ~220 MB model)" if not h["meaning_search"] else "")


async def _chat(tenant: str) -> dict[str, Any]:
    """v0.158 Chat sehat: one current chat, cards waiting for her across chats, what the app's self-check fixed."""
    from . import convs
    h = await asyncio.to_thread(convs.health, tenant)
    detail = (f"{h['chats']} chats, {h['waiting']} card haan ke intezaar mein, self-check ne {h['self_fixes_7d']} baar theek kiya (7 din)"
              + (f"; call mein bahar rakhe: {', '.join(h['held_in_calls'][:4])}" if h["held_in_calls"] else ""))
    return _c("chat", "Chat sehat", True if h["ok"] else None, detail + ("; " + " ".join(h["problems"]) if h["problems"] else ""),
              "Chat mein upar 'Aapki haan chahiye' dabaiye" if h["waiting_old"] else "")


async def _voice_settings() -> dict[str, Any]:
    """v0.108 a Gemini that refused session resumption / context compression makes every network blip a fresh call."""
    from . import voice
    dropped = sorted(voice.UNSUPPORTED)
    key = [f for f in dropped if f in ("session_resumption", "context_window_compression", "sliding_window")]
    r = dict(voice.RESUME)
    detail = (f"resume {r['resumed']}, naya session {r['fresh_after_drop']} (resume fail {r['resume_failed']})"
              + (f"; Gemini ne mana kiya: {', '.join(dropped)}" if dropped else ""))
    if key:
        return _c("voice_memory", "Call ki yaad (Gemini)", False, detail,
                  "Gemini Live model badaliye (GEMINI_LIVE_MODEL) jo session resumption + compression maanta ho; "
                  "tab tak har reconnect par Hoola pichhli baat se dobara samjhata hai")
    if "language_codes" in dropped:   # v0.114 the transcript language hint was refused: back to auto-detect
        return _c("voice_memory", "Call ki yaad (Gemini)", None, detail + "; transcript ki bhasha ka hint Gemini ne nahi liya",
                  "GEMINI_LIVE_MODEL badal kar dekhiye; tab tak bhasha sirf prompt ke lock se pakki hai")
    if "custom_vocabulary" in dropped:   # v0.119 her words as transcript vocabulary were refused (prompt list still works)
        return _c("voice_memory", "Call ki yaad (Gemini)", None, detail + "; aapke shabdon ki list transcript ne nahi li",
                  "Koi baat nahi: naam / shabd prompt mein jaate hain; GEMINI_LIVE_MODEL badal kar dekh sakte hain")
    bad = r["resume_failed"] > max(3, r["resumed"])
    return _c("voice_memory", "Call ki yaad (Gemini)", None if bad else True, detail,
              "pm2 logs santosh | grep -i 'resume failed' dekhiye" if bad else "")


async def _portals() -> list[dict[str, Any]]:
    from .operator import reach

    def one(name: str, host: str) -> dict[str, Any]:
        rec = reach.remembered(host)
        ok, why = reach.probe(host, timeout=5)
        if ok and not rec:
            return _c("site:" + host, name, True, "server se khulta hai")
        why = why or (rec or {}).get("why") or "pichhle kaam mein nahi khula"
        if not ok:
            reach.note_fail(host, f"jaanch: {why}")
        return _c("site:" + host, name, False, f"server se nahi khulta ({why})",
                  "PC (Santosh Desktop) se hoga; ya office proxy lagaiye (deploy/office_proxy.md)")
    return list(await asyncio.gather(*[asyncio.to_thread(one, n, h) for n, h in PORTALS]))


async def _guard(coro, cid: str, name: str):
    try:
        return await asyncio.wait_for(coro, CHECK_TIMEOUT)
    except asyncio.TimeoutError:
        return _c(cid, name, False, "jaanch mein bahut der lagi", "thodi der baad phir jaanchiye")
    except Exception as e:
        log.exception("jaanch %s", cid)
        return _c(cid, name, None, f"jaanch nahi ho payi ({type(e).__name__})")


# ---------------------------------------------------------------- the report of real work
def report(tenant: str, days: int = 14) -> dict[str, Any]:
    from sqlalchemy import select

    from .agent.pakka import Lesson, TaskRun
    from .db import session
    from .operator.models import OperatorTask
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: dict[str, Any] = {"days": days}
    with session() as s:
        runs = s.scalars(select(TaskRun).where(TaskRun.tenant_id == tenant, TaskRun.created_at >= since)).all()
        out["chat"] = {"total": len(runs), "outcomes": dict(Counter(r.outcome for r in runs)),
                       "avg_seconds": round(sum(r.seconds for r in runs) / max(1, len(runs))),
                       "not_done": [{"request": r.request[:140], "outcome": r.outcome, "left": (r.left or "")[:140]}
                                    for r in runs if r.outcome in ("partial", "stuck", "stopped")][-10:]}
        ops = s.scalars(select(OperatorTask).where(OperatorTask.tenant_id == tenant, OperatorTask.created_at >= since)).all()
        out["website"] = {"total": len(ops), "status": dict(Counter(o.status for o in ops)),
                          "not_done": [{"task": o.task[:140], "status": o.status, "site": (o.url or "")[:80],
                                        "why": (o.error or o.summary or o.stage or "")[:160]}
                                       for o in ops if o.status not in ("done", "running", "waiting", "queued")][-10:]}
        out["lessons"] = [{"tool": x.tool, "problem": x.problem[:140], "fix": x.fix[:100]}
                          for x in s.scalars(select(Lesson).where(Lesson.tenant_id == tenant)
                                             .order_by(Lesson.created_at.desc()).limit(10)).all()]
    try:
        from pathlib import Path
        p = Path("data") / "crashes" / f"{tenant}.jsonl"
        out["crashes"] = sum(1 for _ in p.open()) if p.exists() else 0
    except Exception:
        out["crashes"] = 0
    try:
        from .offline import STATS as off
        out["email_digest"] = dict(off)
    except Exception:
        pass
    return out


async def run(tenant: str) -> dict[str, Any]:
    t0 = time.time()
    singles = [(_claude(), "claude", "Dimaag (Claude)"), (_app_model(), "app_model", "App design (Opus)"), (_gemini(), "gemini", "Awaaz + Google search (Gemini)"),
               (_parallel(), "parallel", "Backup search (Parallel)"), (_email(tenant), "email", "Email bhejna"),
               (_operator(), "operator", "Website kaam (Computer Operator)"), (_worker(), "browser", "Jaldi website dekhna"),
               (_pc(tenant), "pc", "Mera PC"), (_push(), "push", "Phone par notification"),
               (_mcp_runner(), "mcp_runner", "Ek-tap MCP (runner)"),
               (_google(tenant), "google", "Google"), (_disk(), "disk", "Server ki jagah"),
               (_memory(tenant), "memory", "Hoola ki yaad"), (_voice_settings(), "voice_memory", "Call ki yaad (Gemini)"),
               (_chat(tenant), "chat", "Chat sehat")]
    parts = await asyncio.gather(*[_guard(c, i, n) for c, i, n in singles],
                                 _guard(_portals(), "portals", "Sarkari / roz ki websites"))
    checks: list[dict[str, Any]] = []
    for p in parts:
        checks.extend(p if isinstance(p, list) else [p])
    bad = [c for c in checks if c["ok"] is False]
    warn = [c for c in checks if c["ok"] is None]
    say = ("Sab theek hai." if not bad and not warn else
           f"{len(bad)} cheez kharab" + (f", {len(warn)} par dhyan dena hai" if warn else "") + ": " +
           "; ".join(f"{c['name']} - {c['detail']}" for c in (bad + warn)[:4]))
    rep = await asyncio.to_thread(report, tenant)
    return {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1),
            "ok": len(checks) - len(bad) - len(warn), "bad": len(bad), "warn": len(warn), "total": len(checks),
            "checks": checks, "say": say, "report": rep}
