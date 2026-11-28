"""HOOLA DOD - "done" means checked (v0.999.334; owner, after the kwant read: '"Done" means checked ... work on it').

When her coworker says it is finished (hoola_done), Hoola itself runs the task's checks - the coworker's word is never
the proof:

- file_exists / file_contains: a file it handed her (Hoola's own copy, taken at hand-over, which the coworker cannot
  change afterwards) or one in its workspace.
- web: a public web address answers (status, and text on it when given). Public addresses only, each redirect checked.
- page: text on the page its browser has open for this task (OpenClaw's own browser tool, read only).
- command: a command run in a fresh, locked box - her coworker's own image, her workspace mounted READ-ONLY, no network,
  capped memory / CPU / processes / time. Exit 0 = passed.

Who may add a check: she (counts at once), or the coworker with hoola_check - its own check waits for HER approval, so it
can never verify its own work. Then a reviewer on another model (never the coworker's company) reads her request part by
part against what was done and what the checks found: each part Passed / Not met / No check. The reviewer can stop a
Pass (a part not met) but can never make one: Passed needs at least one check that Hoola ran itself and passed, and no
check that failed.

Verdict: passed | failed | needs_you | not_checked, plus "couldn't check" - each with its reason.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings

log = logging.getLogger("hoola.dod")

KINDS = ("file_exists", "file_contains", "web", "page", "command")
LABEL = {"file_exists": "File", "file_contains": "Text in a file", "web": "Web address", "page": "Text on its page",
         "command": "Command"}
MAX_CHECKS = 12
READ_CAP = 2 * 1024 * 1024
TRANSPORT: httpx.AsyncBaseTransport | None = None   # tests put a fake web here
DOCKER = None                                        # tests put a fake docker here (else gateway's)


def _rel(path: str) -> str:
    p = str(path or "").strip().replace("\\", "/")
    for pre in ("/home/node/.openclaw/workspace/", "home/node/.openclaw/workspace/", "workspace/", "./"):
        if p.startswith(pre):
            p = p[len(pre):]
    if not p or p.startswith("/") or ".." in p.split("/") or len(p) > 300:
        raise ValueError("Give the file's name inside the coworker's workspace, like report.pdf or out/list.csv.")
    return p


def normalize(spec: dict[str, Any]) -> dict[str, Any]:
    """A check as she or the coworker described it -> its stored shape. ValueError with a plain reason."""
    if not isinstance(spec, dict):
        raise ValueError("A check needs its details.")
    kind = str(spec.get("kind") or "")
    if kind not in KINDS:
        raise ValueError("A check is one of: a file, text in a file, a web address, text on its page, a command.")
    out: dict[str, Any] = {"kind": kind}
    if kind in ("file_exists", "file_contains"):
        out["path"] = _rel(spec.get("path") or "")
    if kind in ("file_contains", "page"):
        text = " ".join(str(spec.get("text") or "").split())[:300]
        if not text:
            raise ValueError("Say which words must be there.")
        out["text"] = text
    if kind == "web":
        url = str(spec.get("url") or "").strip()
        if not re.match(r"^https?://", url, re.I) or len(url) > 2000:
            raise ValueError("Give a full web address starting with https://")
        out["url"] = url
        if spec.get("text"):
            out["text"] = " ".join(str(spec["text"]).split())[:300]
        want = spec.get("code", spec.get("status"))
        if want not in (None, ""):
            try:
                st = int(want)
            except (TypeError, ValueError):
                raise ValueError("The answer code is a number, like 200.") from None
            if not 100 <= st <= 599:
                raise ValueError("The answer code is between 100 and 599.")
            out["code"] = st
    if kind == "command":
        cmd = str(spec.get("command") or "").strip()
        if not cmd or len(cmd) > 600 or "\x00" in cmd:
            raise ValueError("Give the command to run, under 600 characters.")
        out["command"] = cmd
    return out


def new(spec: dict[str, Any], by: str, why: str = "") -> dict[str, Any]:
    """A check row. Hers counts at once; the coworker's waits for her approval."""
    c = normalize(spec)
    from .. import db
    mine = by == "you"
    c.update({"id": "ck" + uuid.uuid4().hex[:10], "by": by, "approved": mine,
              "status": "pending" if mine else "needs_approval", "why": str(why or "")[:300], "result": "",
              "at": db.now().isoformat()})
    return c


def describe(c: dict[str, Any]) -> str:
    k = c.get("kind")
    if k == "file_exists":
        return f"The file {c['path']} is there"
    if k == "file_contains":
        return f"{c['path']} contains \"{c['text']}\""
    if k == "web":
        return f"{c['url']} answers" + (f" with \"{c['text']}\"" if c.get("text") else "")
    if k == "page":
        return f"Its page shows \"{c['text']}\""
    return f"`{c.get('command', '')}` runs without an error"


# ------------------------------------------------------------------------------------------------ running one check
def _file(tenant: str, task_id: str, files: list[dict], rel: str) -> Path | None:
    """Her copy first (taken when it was handed over - the coworker cannot touch it), else the workspace."""
    from . import gateway as GW
    name = rel.rsplit("/", 1)[-1]
    for f in files:
        if f.get("name") == name and f.get("path") and Path(f["path"]).is_file():
            return Path(f["path"])
    ws = GW.workspace_dir(tenant).resolve()
    p = (ws / rel).resolve()
    if ws in p.parents and p.is_file():
        return p
    return None


def _norm(s: str) -> str:
    return " ".join((s or "").split())


async def _web(c: dict[str, Any]) -> tuple[str, str]:
    from ..agent.scrape_tools import _guard_url
    url = c["url"]
    async with httpx.AsyncClient(transport=TRANSPORT, timeout=20, follow_redirects=False,
                                 headers={"User-Agent": "Hoola-DOD-check/1"}) as cl:
        for _hop in range(6):
            try:
                _guard_url(url)
            except Exception as e:  # noqa: BLE001 - the house guard's own reason
                return "error", f"Not a public web address: {str(e)[:120]}"
            r = await cl.get(url)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url = str(r.url.join(r.headers["location"]))
                continue
            break
        else:
            return "error", "It kept sending the check elsewhere."
    want = c.get("code")
    ok_status = (r.status_code == want) if want else (200 <= r.status_code < 300)
    if not ok_status:
        return "failed", f"It answered {r.status_code}" + (f", not {want}." if want else ".")
    if c.get("text"):
        if _norm(c["text"]).lower() not in _norm(r.text[:READ_CAP]).lower():
            return "failed", f"It answered {r.status_code}, but \"{c['text']}\" is not on it."
        return "passed", f"It answered {r.status_code} and shows \"{c['text']}\"."
    return "passed", f"It answered {r.status_code}."


async def _command(tenant: str, c: dict[str, Any]) -> tuple[str, str]:
    """Her coworker's own image, a fresh container, her workspace read-only, no network. Exit 0 = passed."""
    from . import gateway as GW
    s = get_settings()
    ws = GW.workspace_dir(tenant).resolve()
    if not ws.is_dir():
        return "error", "Its workspace is empty: nothing to run the command on."
    docker = DOCKER or GW.DOCKER
    name = "hoola-dodck-" + uuid.uuid4().hex[:10]
    args = ["run", "--rm", "--name", name, "--network", "none", "--read-only", "--tmpfs", "/tmp:size=64m",
            "--memory", "512m", "--memory-swap", "512m", "--cpus", "1", "--pids-limit", "256",
            "--security-opt", "no-new-privileges", "--user", f"{s.dod_uid}:{s.dod_uid}",
            "-e", "HOME=/tmp", "-v", f"{ws}:/work:ro", "-w", "/work", "--entrypoint", "sh",
            s.dod_image, "-c", c["command"]]
    try:
        code, out = await docker(*args, timeout=float(getattr(s, "dod_check_command_s", 120) or 120))
    except asyncio.TimeoutError:
        return "failed", "It ran past its time limit."
    except Exception as e:  # noqa: BLE001
        return "error", f"The locked box could not start: {str(e)[:120]}"
    if code == 124:   # the docker client was cut: the box itself must go too
        await docker("rm", "-f", name, timeout=30)
        return "failed", "It ran past its time limit."
    tail = (out or "")[-1200:].strip()
    if code == 0:
        return "passed", ("It ran without an error." + (f"\n{tail}" if tail else ""))[:1300]
    return "failed", (f"It stopped with code {code}." + (f"\n{tail}" if tail else ""))[:1300]


async def run_one(tenant: str, task_id: str, files: list[dict], c: dict[str, Any]) -> tuple[str, str]:
    """-> (status, what Hoola saw). status: passed | failed | error (could not run)."""
    k = c["kind"]
    try:
        if k in ("file_exists", "file_contains"):
            p = _file(tenant, task_id, files, c["path"])
            if p is None:
                return "failed", f"There is no file {c['path']}."
            if k == "file_exists":
                return "passed", f"{c['path']} is there ({p.stat().st_size:,} bytes)."
            raw = p.read_bytes()[:READ_CAP]
            text = _text_of(p, raw)
            if text is None:
                return "error", f"{c['path']} is not a file Hoola can read as text."
            if _norm(c["text"]).lower() in _norm(text).lower():
                return "passed", f"{c['path']} contains \"{c['text']}\"."
            return "failed", f"{c['path']} does not contain \"{c['text']}\"."
        if k == "web":
            return await _web(c)
        if k == "page":
            from . import gateway as GW
            text = await GW.page_text(tenant, f"hoola-dod-{task_id}")
            if text is None:
                return "error", "Its browser has no page open for this task, or its computer is off."
            if _norm(c["text"]).lower() in _norm(text).lower():
                return "passed", f"Its page shows \"{c['text']}\"."
            return "failed", f"Its page does not show \"{c['text']}\"."
        if k == "command":
            return await _command(tenant, c)
    except Exception as e:  # noqa: BLE001 - a check that breaks is "couldn't check", never a pass
        log.warning("dod check %s failed to run: %s", k, e)
        return "error", f"The check could not run: {str(e)[:140]}"
    return "error", "Unknown check."


def _text_of(p: Path, raw: bytes) -> str | None:
    suf = p.suffix.lower()
    if suf == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(raw)).pages[:60])
        except Exception:  # noqa: BLE001
            return None
    if suf in (".docx", ".xlsx", ".pptx"):
        try:
            import io
            import zipfile
            z = zipfile.ZipFile(io.BytesIO(raw))
            xml = " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist()
                           if n.endswith(".xml") and ("word/" in n or "sharedStrings" in n or "ppt/slides" in n or "worksheets" in n))
            return re.sub(r"<[^>]+>", " ", xml)
        except Exception:  # noqa: BLE001
            return None
    if b"\x00" in raw[:4096]:
        return None
    return raw.decode("utf-8", "ignore")


# ------------------------------------------------------------------------------------------------ the reviewer
REVIEW_SYSTEM = (
    "You review work a coworker did for its owner. Split HER request into its parts, in her own words (at most 8). "
    "For each part say: passed (a check Hoola ran shows it), not_met (what was done shows it is missing or wrong), or "
    "no_check (nothing shown proves it either way). Base every answer only on the facts given: the coworker's own words "
    "are a claim, never proof. Answer only JSON: {\"parts\": [{\"part\": \"...\", \"result\": \"passed|not_met|no_check\", "
    "\"why\": \"one short sentence\"}]}")


def review_model() -> str:
    """Another company than the coworker's model (a model never reviews its own family's work)."""
    s = get_settings()
    co = str(s.dod_model).replace("openrouter/", "").split("/", 1)[0]
    for m in [getattr(s, "dod_review_model", "") or "", "z-ai/glm-5.3", "qwen/qwen3.8-27b", "deepseek/deepseek-v4.1-flash-1017"]:
        if m and m.split("/", 1)[0] != co:
            return m
    return ""


async def _review_call(model: str, msg: str) -> str:
    from ..agent import llm
    tok = llm.MODEL_NOW.set("openrouter:" + model)
    own = llm.BOX_OWNS.set(True)
    try:
        blocks, _stop, _u = await asyncio.wait_for(
            llm._openai_create("glm", REVIEW_SYSTEM, [], [{"role": "user", "content": msg}], 900), 45)
    finally:
        llm.BOX_OWNS.reset(own)
        llm.MODEL_NOW.reset(tok)
    return "".join(x.get("text", "") for x in blocks if isinstance(x, dict) and x.get("type") == "text")


REVIEW = _review_call   # tests swap this


async def review(ask: str, summary: str, steps: list[dict], files: list[dict], checks: list[dict]) -> dict[str, Any]:
    """-> {model, parts: [{part, result, why}]} or {model, error}. Never raises."""
    model = review_model()
    if not model or not getattr(get_settings(), "dod_review", True):
        return {"model": "", "parts": [], "error": "No second reviewer on this server."}
    if REVIEW is _review_call:
        from ..agent import providers
        if not providers.key_of("openrouter"):
            return {"model": "", "parts": [], "error": "No second reviewer on this server (no OpenRouter key)."}
    lines = [f"- {s.get('title', '')}" + (f": {s.get('detail', '')}" if s.get("detail") else "")
             for s in steps if not s.get("you")][-30:]
    flist = []
    for f in files[:6]:
        p = Path(f.get("path") or "")
        excerpt = ""
        if p.is_file():
            t = _text_of(p, p.read_bytes()[:200_000])
            excerpt = _norm(t or "")[:1200]
        flist.append(f"- {f.get('name')} ({f.get('size', 0)} bytes)" + (f": {excerpt}" if excerpt else ""))
    clist = [f"- {describe(c)}: {c.get('status')} - {c.get('result', '')[:300]}" for c in checks]
    msg = (f"HER REQUEST:\n{ask[:4000]}\n\nTHE COWORKER SAYS (a claim):\n{summary[:2000]}\n\n"
           f"ITS STEPS:\n" + ("\n".join(lines) or "- (none)") + "\n\nFILES IT HANDED OVER:\n" + ("\n".join(flist) or "- (none)")
           + "\n\nCHECKS HOOLA RAN ITSELF:\n" + ("\n".join(clist) or "- (none)"))
    try:
        text = await REVIEW(model, msg)
    except Exception as e:  # noqa: BLE001 - a reviewer that fails is said, never a pass
        log.warning("dod review on %s failed: %s", model, str(e)[:120])
        return {"model": model, "parts": [], "error": "The second reviewer did not answer."}
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    parts = []
    for p in (d.get("parts") or [])[:8] if isinstance(d, dict) else []:
        if not isinstance(p, dict) or not str(p.get("part") or "").strip():
            continue
        res = p.get("result") if p.get("result") in ("passed", "not_met", "no_check") else "no_check"
        parts.append({"part": str(p["part"])[:200], "result": res, "why": str(p.get("why") or "")[:240]})
    if not parts:
        return {"model": model, "parts": [], "error": "The second reviewer's answer could not be read."}
    return {"model": model, "parts": parts}


# ------------------------------------------------------------------------------------------------ the verdict
async def verify(tenant: str, task_id: str, ask: str, summary: str, steps: list[dict], files: list[dict],
                 checks: list[dict], prior_parts: list[dict] | None = None) -> dict[str, Any]:
    """Run every approved check, ask the reviewer, decide. -> {verdict, checks, parts, couldnt, model}."""
    from .. import db
    out: list[dict] = []
    for c in checks:
        c = dict(c)
        if c.get("approved") and c.get("status") != "declined":
            c["status"], c["result"] = await run_one(tenant, task_id, files, c)
            c["ran_at"] = db.now().isoformat()
        out.append(c)
    rv = (await review(ask, summary, steps, files, out)) if prior_parts is None else {"model": "", "parts": prior_parts}
    couldnt: list[dict] = []
    for c in out:
        if c.get("status") == "error":
            couldnt.append({"what": describe(c), "why": c.get("result") or "It could not run."})
        elif c.get("status") == "needs_approval":
            couldnt.append({"what": describe(c), "why": "Your coworker suggested it; it runs once you approve it."})
    for p in rv.get("parts") or []:
        if p["result"] == "no_check":
            couldnt.append({"what": p["part"], "why": p.get("why") or "Nothing Hoola could run shows it."})
    if rv.get("error"):
        couldnt.append({"what": "A second look by another AI", "why": rv["error"]})
    passed = [c for c in out if c.get("status") == "passed"]
    failed = [c for c in out if c.get("approved") and c.get("status") == "failed"]
    waiting = [c for c in out if c.get("status") == "needs_approval"]
    not_met = [p for p in (rv.get("parts") or []) if p["result"] == "not_met"]
    if failed:
        verdict = "failed"
    elif waiting or not_met:
        verdict = "needs_you"
    elif passed:
        verdict = "passed"
    else:
        verdict = "not_checked"
    return {"verdict": verdict, "checks": out, "parts": rv.get("parts") or [], "couldnt": couldnt,
            "model": rv.get("model") or "", "at": db.now().isoformat()}
