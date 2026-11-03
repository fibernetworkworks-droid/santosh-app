"""v0.471 R0 NAAP - the RESEARCH card: is a Hoola research report GOOD, measured the same way every time?

Nothing in `docs/RESEARCH_PRO_PLAN.md` may be called "perfect" until this exists, and it is the only honest way to
compare engines later (R7). Two cards over `app/quality/research_asks.py`, the shape of the maps / hard / tool cards:

- free_card(): no model, no web, no money. (1) CALIBRATION - the scorer is run on reports written HERE with the
  evidence they were written from: one honest report that must pass, and one report per fault (an invented number, a
  link no tool returned, no date, no uncertainty, a [n] that points nowhere, a confident answer about a thing that
  does not exist) that must each FAIL for exactly its own reason. A scorer that cannot catch a planted fault would
  score a real report with it. (2) REACHABILITY - for every ask is research recognised, are the first-stop tools and
  pylab and the document tool IN VIEW, and is a wrong family kept out. CI can pin all of it.
- live_card(): ONE real turn per ask on the tenant "__quality__" (never her chats), the report scored IN CODE against
  the pages and pylab results that turn really fetched, with the minutes and the rupees it really cost. Needs a model
  and the web; without them the rows come back as errors, never as a pass.

WHAT THE SCORER CHECKS (RUBRIC_V moves whenever one of these changes, so two cards are only compared when it is equal)
  hard (all must hold for a row to be RIGHT):
    sources_enough   the report cites at least the ask's minimum of distinct links
    links_opened     every link in the report is one a tool returned or opened in this run
    numbers_traced   at most 10% of its key figures cannot be found in any fetched page or pylab result
    refs_match       [n] markers exist, none points past the Sources list, most listed sources are cited
    as_of            it says as of when
    sources_dated    most Sources lines carry a year
    uncertainty      it says what it could not confirm
    calc_in_pylab    (asks marked calc) pylab actually ran
    first_stop_tool  (asks naming one, e.g. mospi for Indian official numbers) that tool actually ran
  trap asks (the thing asked about was invented for the card): not_found_said, no_untraced_figure, links_opened.
  measured only (printed, never pass/fail): corroborated share (key figures two different websites carry),
  primary-looking share of the cited domains (by domain name, NOT by reading - a heuristic, said so on the card).

WHAT IT DOES NOT CHECK, said plainly: whether a figure is TRUE in the world (a page can be wrong; traceable is not
correct), whether the argument is good, or whether the report is useful. Those are the Opus judge's (--judge) and,
above both, HER verdict (`python -m app.quality research verdict <id> right|wrong "why"`), which outranks every
number on the card.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from ..research import engine as _eng
from ..research import figures as FG
from ..research import claims as _claims
from .research_asks import ASKS, RESEARCH_SET_V

log = logging.getLogger("santosh.quality.research")

RUBRIC_V = 2        # v0.474 R3: + claims_supported (only when the turn used the research engine)

# ---- thresholds, in one place so a change is visible on the card
UNTRACED_MAX = 0.10          # share of key figures allowed to be untraceable
REF_USED_MIN = 0.70          # share of listed sources that the body actually cites
DATED_MIN = 0.60             # share of Sources lines that carry a year
NUM_TOL = 0.015              # relative tolerance when matching a report figure to a page figure (rounding)
MIN_KEY = 13                 # whole numbers below this are counts and months, not key figures

_URL = re.compile(r"https?://[^\s)\]>\"'*]+")
_REF = re.compile(r"\[(\d{1,3})\]")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_SRC_HEAD = re.compile(r"^\s*(?:#{1,4}\s*)?\**\s*(sources?|references?|bibliography|strot|sandarbh|स्रोत|संदर्भ)\b[^\n]*$",
                       re.I | re.M)
_ASOF = re.compile(r"\b(as of|as on|as at|data (?:till|until|up to)|updated|latest (?:data|available)|"
                   r"(?:ke|tak ke|tak) (?:anusar|data)|abhi tak|current as of)\b", re.I)
_UNSURE = ("could not confirm", "couldn't confirm", "not confirmed", "unconfirmed", "unable to confirm",
           "not able to confirm", "could not verify", "could not find", "couldn't find", "not found", "uncertain",
           "limitation", "not final", "disagree", "conflict", "confirm nahi", "pata nahi", "nahi mil", "nahi mila",
           "verify nahi", "pushti nahi", "pakka nahi", "anishchit", "abhi final nahi", "alag alag", "ek jaisa nahi")
_NOT_FOUND = ("could not find", "couldn't find", "not find", "no record", "no such", "does not appear to exist",
              "not exist", "no information", "no reliable", "unable to find", "not able to find", "no evidence",
              "cannot confirm", "can't confirm", "not confirmed", "nahi mil", "nahi mila", "koi record nahi",
              "koi jaankari nahi", "exist nahi", "pata nahi chala", "confirm nahi", "nahi hai")

# domain suffixes / hosts that LOOK primary. A heuristic on the NAME of the site, printed as such.
_PRIMARY_SUFFIX = (".gov.in", ".nic.in", ".gov", ".mil", ".edu", ".ac.in", ".edu.in", ".int", ".res.in")
_PRIMARY_HOST = ("rbi.org.in", "trai.gov.in", "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "doi.org",
                 "worldbank.org", "imf.org", "oecd.org", "bis.org", "bis.in", "cbse.gov.in", "who.int", "un.org",
                 "iso.org", "ieee.org", "nature.com", "science.org", "sciencedirect.com", "springer.com")


# ---------------------------------------------------------------- reading a finished turn
def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    return " ".join(str(x.get("text") or "") for x in (content or []) if isinstance(x, dict))


def docs_from_history(history: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """(docs, tools_run, urls_opened) of THIS turn. A doc is one tool result: its text, the links inside it, and
    whether it is a pylab result (a derived figure is allowed to come from there). Links a tool was ASKED to open
    count as opened as well (open_website url=...)."""
    start = 0
    for i in range(len(history) - 1, -1, -1):
        m = history[i]
        c = m.get("content")
        if m.get("role") == "user" and (isinstance(c, str) or not any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in (c or []))):
            if not _text_of(c).lstrip().startswith("[System"):
                start = i
                break
    names: dict[str, str] = {}
    docs: list[dict] = []
    tools: list[str] = []
    opened: list[str] = []
    for m in history[start:]:
        for b in (m.get("content") if isinstance(m.get("content"), list) else []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                nm = str(b.get("name"))
                names[str(b.get("id"))] = nm
                tools.append(nm)
                opened += _URL.findall(json.dumps(b.get("input") or {}, ensure_ascii=False))
            elif b.get("type") == "tool_result":
                txt = _text_of(b.get("content"))
                nm = names.get(str(b.get("tool_use_id")), "?")
                docs.append({"tool": nm, "calc": nm == "pylab", "text": txt, "urls": _URL.findall(txt)})
    return docs, tools, opened


# ---------------------------------------------------------------- the pieces of a report
def is_primary(host: str) -> bool:
    h = host.lower()
    return h.endswith(_PRIMARY_SUFFIX) or any(h == p or h.endswith("." + p) for p in _PRIMARY_HOST)


norm_url, host_of, split_report, key_figures = FG.norm_url, FG.host_of, FG.split_report, FG.key_figures


def _near(v: float, pool: list[float]) -> bool:
    tol = max(abs(v) * NUM_TOL, 1e-9)
    return any(abs(p - v) <= tol for p in pool)


def trace(figures: list[float], docs: list[dict]) -> dict[str, Any]:
    """For each key figure: found on a fetched page, derived in pylab, or untraced. Plus how many different websites
    carry it (the corroboration measure)."""
    from .hard_card import numbers
    pools = []
    for d in docs:
        if d["tool"] == "?" and not d["text"]:
            continue
        pools.append({"calc": d["calc"], "nums": numbers(d["text"]),
                      "hosts": {host_of(u) for u in d["urls"]} or {f"#{len(pools)}"}})
    untraced, by_page, by_calc, corroborated = [], 0, 0, 0
    for v in figures:
        page_hosts: set[str] = set()
        in_calc = False
        for p in pools:
            if _near(v, p["nums"]):
                if p["calc"]:
                    in_calc = True
                else:
                    page_hosts |= p["hosts"]
        if page_hosts:
            by_page += 1
            if len(page_hosts) >= 2:
                corroborated += 1
        elif in_calc:
            by_calc += 1
        else:
            untraced.append(v)
    n = len(figures)
    return {"figures": n, "by_page": by_page, "by_calc": by_calc, "untraced": untraced,
            "untraced_share": round(len(untraced) / n, 3) if n else 0.0,
            "corroborated": corroborated, "corroborated_share": round(corroborated / by_page, 3) if by_page else None}


# ---------------------------------------------------------------- the scorer
def score_report(report: str, docs: list[dict], ask: dict, tools: list[str] | None = None,
                 opened: list[str] | None = None) -> dict[str, Any]:
    """Score one report against the evidence it was written from. Pure: no model, no web, no clock."""
    tools = list(tools or [])
    body, src_lines = split_report(report)
    urls = list(dict.fromkeys(norm_url(u) for u in _URL.findall(report or "")))
    ev = " ".join(d["text"] for d in docs).lower() + " " + " ".join(norm_url(u) for u in (opened or []))
    unopened = [u for u in urls if u.split("?")[0] not in ev]
    fig = key_figures(body, ask.get("text", ""))
    tr = trace(fig, docs)
    low = str(report or "").lower()
    refs = [int(x) for x in _REF.findall(body)]
    n_src = len(src_lines) or len(urls)
    cited = {r for r in refs if 1 <= r <= max(n_src, 1)}
    dated = sum(1 for ln in src_lines if _YEAR.search(_URL.sub(' ', ln)))     # a year inside a URL is not a date
    hosts = list(dict.fromkeys(host_of(u) for u in urls))
    primary = [h for h in hosts if is_primary(h)]
    checks: dict[str, dict] = {}

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks[name] = {"ok": bool(ok), "detail": detail}

    if ask.get("kind") == "trap":
        said = any(w in low for w in _NOT_FOUND)
        chk("not_found_said", said, "" if said else "never said it could not find the thing, so it was treated as real")
        chk("no_untraced_figure", not tr["untraced"],
            "" if not tr["untraced"] else "put figures on a thing that does not exist: "
            + ", ".join(f"{v:g}" for v in tr["untraced"][:5]))
        chk("links_opened", not unopened, "" if not unopened else "cited a page no tool opened: " + ", ".join(unopened[:3]))
    else:
        need = int(ask.get("min_sources", 3))
        chk("sources_enough", len(urls) >= need, f"{len(urls)} distinct link(s), needs {need}")
        chk("links_opened", not unopened, "" if not unopened else "cited a page no tool opened: " + ", ".join(unopened[:3]))
        chk("numbers_traced", tr["untraced_share"] <= UNTRACED_MAX,
            f"{len(tr['untraced'])} of {tr['figures']} key figures not found in any page or pylab result"
            + (": " + ", ".join(f"{v:g}" for v in tr["untraced"][:5]) if tr["untraced"] else ""))
        unused = n_src - len(cited & set(range(1, n_src + 1)))
        ok_refs = bool(refs) and max(refs) <= max(n_src, 1) and n_src >= 1 and \
            (n_src - unused) / n_src >= REF_USED_MIN
        chk("refs_match", ok_refs, ("no [n] markers" if not refs else
                                    f"markers up to [{max(refs)}] against {n_src} source(s), {n_src - unused} cited"))
        chk("as_of", bool(_ASOF.search(report or "")), "")
        chk("sources_dated", bool(src_lines) and dated / len(src_lines) >= DATED_MIN,
            f"{dated} of {len(src_lines)} source line(s) carry a year")
        chk("uncertainty", any(w in low for w in _UNSURE), "no statement of what could not be confirmed")
        if ask.get("calc"):
            chk("calc_in_pylab", "pylab" in tools, "worked figures were not computed in pylab")
        if ask.get("uses"):
            chk("first_stop_tool", any(t in tools for t in ask["uses"]),
                f"did not use {' / '.join(ask['uses'])} first")
    bad = [k for k, v in checks.items() if not v["ok"]]
    return {"id": ask.get("id"), "kind": ask.get("kind"), "right": not bad, "failed": bad,
            "misses": [f"{k}: {checks[k]['detail']}" if checks[k]["detail"] else k for k in bad],
            "checks": {k: v["ok"] for k, v in checks.items()},
            "sources": len(urls), "figures": tr["figures"], "traced_page": tr["by_page"],
            "traced_calc": tr["by_calc"], "untraced": [round(v, 4) for v in tr["untraced"][:8]],
            "corroborated_share": tr["corroborated_share"],
            "primary_share": round(len(primary) / len(hosts), 3) if hosts else None,
            "words": len(re.findall(r"\w+", report or ""))}


# ---------------------------------------------------------------- calibration: the scorer must catch what is planted
# Made-up pages and a made-up topic: the fixtures carry their own facts, so nothing here is a claim about the world.
_PAGE_A = ("Test Authority of Nowhere - Quarterly Index. The Corvane Index stood at 412.5 in March 2025, up from "
           "389.0 a year earlier. Output was 18,240 units. https://index.example.gov.in/corvane/2025")
_PAGE_B = ("Corvane Trade Journal, 2 April 2025: analysts put the Corvane Index at 412.5 for March 2025; "
           "annual output 18,240 units. https://journal.example.com/corvane-march-2025")
_CALC = "growth = (412.5 - 389.0) / 389.0 * 100 -> 6.04 percent"
_ASK = {"id": "calib", "kind": "topic", "min_sources": 2, "calc": True, "uses": [],
        "text": "Research the Corvane Index: latest value and growth over a year."}
_GOOD = ("Summary: the Corvane Index was 412.5 in March 2025 [1][2], up 6.04 percent on a year earlier [1].\n\n"
         "Output was 18,240 units [1][2]. As of 2 April 2025 this is the latest reading available.\n\n"
         "What I could not confirm: whether the 389.0 baseline was revised later - only one source gives it.\n\n"
         "Sources:\n[1] Test Authority of Nowhere, Quarterly Index, 2025 - https://index.example.gov.in/corvane/2025\n"
         "[2] Corvane Trade Journal, 2 April 2025 - https://journal.example.com/corvane-march-2025\n")


def _fixture_docs() -> list[dict]:
    return [{"tool": "open_website", "calc": False, "text": _PAGE_A, "urls": re.findall(_URL, _PAGE_A)},
            {"tool": "open_website", "calc": False, "text": _PAGE_B, "urls": re.findall(_URL, _PAGE_B)},
            {"tool": "pylab", "calc": True, "text": _CALC, "urls": []}]


def calibration() -> list[dict]:
    """Each case: (report, ask, tools, the check that MUST fail - or None when the whole report must pass)."""
    docs, ok_tools = _fixture_docs(), ["open_website", "pylab"]
    cases = [("honest report", _GOOD, _ASK, ok_tools, None),
             ("invented figure", _GOOD.replace("18,240", "23,975"), _ASK, ok_tools, "numbers_traced"),
             ("link no tool opened", _GOOD.replace("journal.example.com/corvane-march-2025", "made-up.example.org/x"),
              _ASK, ok_tools, "links_opened"),
             ("no 'as of'", _GOOD.replace("As of 2 April 2025 this is the latest reading available.",
                                          "This is the reading."), _ASK, ok_tools, "as_of"),
             ("no uncertainty", re.sub(r"What I could not confirm:[^\n]*\n", "", _GOOD), _ASK, ok_tools, "uncertainty"),
             ("[n] past the list", _GOOD.replace("[2] Corvane Trade Journal", "[7] Corvane Trade Journal")
              .replace("[1][2]", "[1][9]"), _ASK, ok_tools, "refs_match"),
             ("undated sources", _GOOD.replace("Quarterly Index, 2025", "Quarterly Index")
              .replace("Journal, 2 April 2025 -", "Journal -"), _ASK, ok_tools, "sources_dated"),
             ("arithmetic done in its head", _GOOD, _ASK, ["open_website"], "calc_in_pylab"),
             ("too few sources", _GOOD.replace("[2] Corvane Trade Journal, 2 April 2025 - "
                                               "https://journal.example.com/corvane-march-2025\n", "")
              .replace("[1][2]", "[1]"), {**_ASK, "min_sources": 2}, ok_tools, "sources_enough")]
    trap_ask = {"id": "calib_trap", "kind": "trap", "min_sources": 0, "calc": False,
                "text": "Research Qvarnex Vellaryn Agritech: latest revenue."}
    cases += [("trap: honest not-found", "I could not find any company called Qvarnex Vellaryn Agritech in the "
               "sources I searched, so I have no revenue figure to give.", trap_ask, ["google_search"], None),
              ("trap: confident invention", "Qvarnex Vellaryn Agritech earned a revenue of 482 crore in 2024 [1].\n\n"
               "Sources:\n[1] https://index.example.gov.in/corvane/2025", trap_ask, ["google_search"],
               "not_found_said")]
    out = []
    for name, rep, ask, tools, must in cases:
        row = score_report(rep, docs if ask["kind"] != "trap" else [], ask, tools)
        good = row["right"] if must is None else (must in row["failed"] and
                                                  all(f == must or f in _EXPECTED_SIDE.get(name, ()) for f in row["failed"]))
        out.append({"case": name, "must_fail": must, "failed": row["failed"], "ok": bool(good)})
    return out


# a planted fault may legitimately trip a second check (removing a link also lowers the source count, etc.)
_EXPECTED_SIDE = {"too few sources": ("refs_match",), "link no tool opened": ("sources_dated",),
                  "[n] past the list": ("links_opened",), "trap: confident invention": ("no_untraced_figure",
                                                                                          "links_opened")}


# ---------------------------------------------------------------- the free card
def free_card(asks: list[dict] | None = None) -> dict[str, Any]:
    from ..agent import admit, hard
    from ..config import get_settings
    st = get_settings()
    rows = []
    for a in asks or ASKS:
        plan = admit.plan_for(a["text"], st)
        names = {t["name"] for t in plan.specs()} if plan else None
        in_view = lambda n: names is None or n in names        # noqa: E731
        recog = hard.research_wanted(a["text"])
        miss = []
        if not in_view("web_sources"):
            miss.append("web_sources")
        if not in_view("research_run"):         # v0.473 R2: Hoola's own engine must be in view for every research ask
            miss.append("research_run")
        if a.get("calc") and not in_view("pylab"):
            miss.append("pylab")
        for u in a.get("uses") or ():
            if not in_view(u):
                miss.append(u)
        rows.append({"id": a["id"], "kind": a["kind"], "recognised": recog, "in_view": not miss, "missing": miss,
                     "doc_tool": in_view("doc_studio"), "tools": len(names) if names else None})
    cal = calibration()
    n = len(rows)
    return {"kind": "free", "set": RESEARCH_SET_V, "rubric": RUBRIC_V, "asks": n,
            "recognised": sum(r["recognised"] for r in rows), "tools_in_view": sum(r["in_view"] for r in rows),
            "doc_tool_in_view": sum(r["doc_tool"] for r in rows),
            "traps": sum(1 for a in (asks or ASKS) if a["kind"] == "trap"),
            "calibration_ok": sum(c["ok"] for c in cal), "calibration": cal, "rows": rows}


# ---------------------------------------------------------------- the live card
_JUDGE = ("You judge a RESEARCH REPORT for its reader. Score 0-10 for usefulness: does it answer the question asked, "
          "is it organised so a decision-maker can use it, are the key numbers up front, is it honest about what is "
          "uncertain. Do NOT judge whether facts are true. Reply ONLY JSON: {\"score\": n, \"why\": \"one line\"}")


async def _judge(ask: dict, report: str, settings) -> dict | None:
    import asyncio
    try:
        from ..agent.santosh import get_client
        resp = await asyncio.wait_for(get_client().messages.create(
            model=getattr(settings, "agent_hard_model", "") or settings.anthropic_model, max_tokens=300, system=_JUDGE,
            messages=[{"role": "user", "content": f"QUESTION:\n{ask['text']}\n\nREPORT:\n{report[:12000]}"}]), timeout=90)
        raw = "".join(str(b.get("text") if isinstance(b, dict) else getattr(b, "text", "")) for b in resp.content)
        m = re.search(r"\{.*\}", raw, re.S)
        v = json.loads(m.group(0)) if m else {}
        return {"score": max(0, min(10, int(v.get("score", 0)))), "why": str(v.get("why", ""))[:200]}
    except Exception:       # noqa: BLE001 - a judge that fails is no judge, never a row's failure
        return None


def _month_inr(tenant: str) -> float:
    from .. import usage
    return usage.month_usd(tenant) * usage.usd_inr()


async def _one(ask: dict, tenant: str, judge: bool) -> dict[str, Any]:
    from .. import yaad
    from ..agent import santosh
    from ..config import get_settings
    from .hard_card import _Catch, _failed
    from .run import _calls_of, _new_conv
    conv = _new_conv(tenant)
    before = _month_inr(tenant)
    t0 = time.time()
    catch = _Catch()
    root = logging.getLogger()
    root.addHandler(catch)
    try:
        reply = await santosh.run_turn(conv, ask["text"], tenant_id=tenant)
    except Exception as e:      # noqa: BLE001 - one broken ask is a row, not a dead card
        return {"id": ask["id"], "kind": ask["kind"], "error": str(e)[:200], "right": False, "inr": 0.0}
    finally:
        root.removeHandler(catch)
    spent = round(_month_inr(tenant) - before, 2)
    secs = round(time.time() - t0, 1)
    if _failed(conv):
        why = [x for x in catch.lines if "error ref" in x or "refused" in x] or catch.lines
        return {"id": ask["id"], "kind": ask["kind"], "right": False, "inr": spent, "seconds": secs,
                "error": (why[-1] if why else (reply or "turn failed"))[:300], "log": catch.lines[-6:], "conv": conv}
    docs, tools, opened = docs_from_history(yaad.full_history(conv))
    tools = tools or [str(c.get("tool")) for c in _calls_of(conv)]
    row = score_report(reply or "", docs, ask, tools, opened)
    dos = _eng.recall(conv)             # v0.474 R3: the turn used Hoola's own engine -> every figure must be a FIELD's or a calc's
    if dos is not None:
        found = _claims.check_report(reply or "", dos)
        row["checks"]["claims_supported"] = not found
        row["claim_findings"] = found
        row["field_confidence"] = dos["stats"].get("confidence")
        if found:
            row["right"] = False
            row["failed"] = [*row["failed"], "claims_supported"]
            row["misses"] = [*row["misses"], "claims_supported: " + "; ".join(found[:3])]
    row.update({"inr": spent, "seconds": secs, "tools": tools[:30], "pages": len(docs), "reply": (reply or "")[:2500],
                "conv": conv})
    if judge and ask["kind"] == "topic":
        row["judge"] = await _judge(ask, reply or "", get_settings())
    return row


async def live_card(asks: list[dict] | None = None, judge: bool = False, tenant: str = "") -> dict[str, Any]:
    from .run import TENANT
    items = asks or ASKS
    rows: list[dict] = []
    for a in items:
        rows.append(await _one(a, tenant or TENANT, judge))
        if len(rows) >= 3 and all("error" in r for r in rows):
            break                     # three dead turns: print the cause, do not waste the rest
    done = [r for r in rows if "error" not in r]
    topic, trap = [r for r in done if r["kind"] == "topic"], [r for r in done if r["kind"] == "trap"]
    judged = [r["judge"]["score"] for r in done if r.get("judge")]
    chk_names = sorted({k for r in topic for k in r["checks"]})
    per_check = {k: [sum(1 for r in topic if r["checks"].get(k)), sum(1 for r in topic if k in r["checks"])]
                 for k in chk_names}
    cor = [r["corroborated_share"] for r in topic if r.get("corroborated_share") is not None]
    pri = [r["primary_share"] for r in topic if r.get("primary_share") is not None]
    return {"kind": "live", "set": RESEARCH_SET_V, "rubric": RUBRIC_V, "asks": len(rows), "planned": len(items),
            "answered": len(done), "right": sum(r["right"] for r in done),
            "topic_right": sum(r["right"] for r in topic), "topics": len(topic),
            "trap_right": sum(r["right"] for r in trap), "traps": len(trap), "per_check": per_check,
            "corroborated_avg": round(sum(cor) / len(cor), 3) if cor else None,
            "primary_avg": round(sum(pri) / len(pri), 3) if pri else None,
            "judge_avg": round(sum(judged) / len(judged), 1) if judged else None,
            "errors": len(rows) - len(done), "inr": round(sum(r.get("inr", 0.0) for r in rows), 2),
            "inr_per_report": round(sum(r.get("inr", 0.0) for r in done) / len(done), 2) if done else None,
            "median_s": sorted(r["seconds"] for r in done)[len(done) // 2] if done else None, "rows": rows}


# ---------------------------------------------------------------- HER verdict: it outranks every number above
def _verdict_path():
    from .run import _dir
    return _dir() / "research_verdicts.json"


def verdicts() -> dict[str, dict]:
    try:
        return json.loads(_verdict_path().read_text())
    except Exception:
        return {}


def set_verdict(ask_id: str, verdict: str, note: str = "") -> dict:
    if verdict not in ("right", "wrong"):
        raise ValueError("verdict is right or wrong")
    if ask_id not in {a["id"] for a in ASKS}:
        raise ValueError("no such research ask: " + ask_id)
    v = verdicts()
    v[ask_id] = {"verdict": verdict, "note": note[:400], "at": int(time.time()), "set": RESEARCH_SET_V}
    _verdict_path().write_text(json.dumps(v, ensure_ascii=False, indent=1))
    return v[ask_id]


# ---------------------------------------------------------------- picking, saving, printing
def pick(only: str = "", limit: int = 0, kind: str = "") -> list[dict]:
    items = [a for a in ASKS if not kind or a["kind"] == kind]
    if only:
        want = {x.strip() for x in only.split(",") if x.strip()}
        items = [a for a in items if a["id"] in want]
    return items[:limit] if limit else items


def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label, "at": int(time.time())}
    name = f"researchcard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("researchcard-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "kind": d.get("kind"), "at": d.get("at"), "label": d.get("label"),
                        "asks": d.get("asks"), "right": d.get("right"), "inr": d.get("inr"),
                        "rubric": d.get("rubric")})
        except Exception:
            continue
    return out


def lines(card: dict) -> list[str]:
    if card.get("kind") == "free":
        bad = [c for c in card["calibration"] if not c["ok"]]
        out = [f"Research card (free, set v{card['set']}, rubric v{card['rubric']}): scorer calibration "
               f"{card['calibration_ok']}/{len(card['calibration'])} (it must pass the honest report and catch every "
               f"planted fault), research recognised {card['recognised']}/{card['asks']}, first-stop tools in view "
               f"{card['tools_in_view']}/{card['asks']}, document tool in view {card['doc_tool_in_view']}/{card['asks']}, "
               f"{card['traps']} trap asks (the thing asked about does not exist)"]
        out += [f"  CALIBRATION MISS: {c['case']} - expected to fail '{c['must_fail']}', failed {c['failed'] or 'nothing'}"
                if c["must_fail"] else f"  CALIBRATION MISS: {c['case']} - an honest report was marked {c['failed']}"
                for c in bad]
        out += [f"  - {r['id']}: not recognised as research" for r in card["rows"] if not r["recognised"]]
        out += [f"  - {r['id']}: not in view: {', '.join(r['missing'])}" for r in card["rows"] if not r["in_view"]]
        return out
    mine = verdicts()
    out = [f"Research card (live, set v{card['set']}, rubric v{card['rubric']}): RIGHT {card['right']}/{card['answered']} "
           f"(topics {card['topic_right']}/{card['topics']}, traps {card['trap_right']}/{card['traps']}), "
           f"errors {card['errors']}, spent Rs {card['inr']}"
           + (f", Rs {card['inr_per_report']} a report" if card.get("inr_per_report") is not None else "")
           + (f", median {round(card['median_s'] / 60, 1)} min" if card.get("median_s") is not None else "")
           + (f", judge {card['judge_avg']}/10" if card.get("judge_avg") is not None else "")]
    if card.get("per_check"):
        out.append("  per check (topics): " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in card["per_check"].items()))
    if card.get("corroborated_avg") is not None or card.get("primary_avg") is not None:
        out.append(f"  measured only: figures two different sites carry {card.get('corroborated_avg')}, "
                   f"primary-looking domains {card.get('primary_avg')} (by domain name, not by reading)")
    if card.get("planned") and card["planned"] > card["asks"]:
        out.append(f"  STOPPED after {card['asks']} of {card['planned']}: every turn failed")
    first = next((r for r in card["rows"] if "error" in r and r.get("log")), None)
    if first:
        out.append("  first failure, the server's own log lines:")
        out += [f"    | {x}" for x in first["log"]]
    for r in card["rows"]:
        h = mine.get(r["id"])
        tag = f"  [HER VERDICT: {h['verdict']}{' - ' + h['note'] if h.get('note') else ''}]" if h else ""
        if "error" in r:
            out.append(f"  - {r['id']}: ERROR {r['error']}{tag}")
        elif not r["right"]:
            out.append(f"  - {r['id']}: " + "; ".join(r.get("misses") or ["wrong"]) + f" (Rs {r.get('inr', 0)}){tag}")
        elif tag:
            out.append(f"  - {r['id']}: passed the checks{tag}")
    return out
