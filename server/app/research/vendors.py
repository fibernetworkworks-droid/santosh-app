"""v0.477 R6 PARAYA ENGINE - the vendors' research engines behind the SAME job, gated, capped, and re-checked by Hoola's own fetch.

Plan: `docs/RESEARCH_PRO_PLAN.md` R6. Every wire format below was read from the vendor's OWN shipped SDK (`docs/research/research_apis/01_techniques.md`);
nothing here has ever been answered by a live vendor. What that means in the design:

  OFF BY DEFAULT   a vendor engine runs only when ALL of these hold (`check`): it is built; she listed it in `research_engines_allowed`; its key is set;
                   she listed it in `research_vendor_terms_ack` (the vendors' terms on storing and showing their output could NOT be read from here -
                   the doc hosts are blocked - so the ACT of reading them is hers, and nothing is assumed); she set its per-run PRICE in rupees (a ceiling
                   needs a price: 0 = refused); that price fits under the run ceiling (R5); and today's room can take it.
  A GATHERER       the vendor's answer is never handed over as Hoola's. Its claims (one statement + the page it cites + the page's own words if it gave
                   them) are turned into NOTES by `to_dossier`: Hoola FETCHES each cited page itself (url discipline + source policy apply), and a claim is
                   VERIFIED only when its words / its figures are found on that page by Hoola's own read. The vendor's prose is not carried at all. From
                   there it is the same R3 dossier: fields, confidence, the claim check before she sees the report, the R5 cost line.
  NEVER PAYS TWICE `start` is never retried (a create that may have succeeded is not repeated); the vendor's run id is written to the run's checkpoint the moment
                   it exists, so a restart RE-ATTACHES to that run instead of starting and paying for another one.
  HONEST COST      Exa reports `costDollars` (and takes `budget.maxCostDollars`, a vendor-side ceiling): that is used. For the others the price she set is the cost,
                   shown as "an ESTIMATE - the vendor did not report its cost".

Built: parallel (Task API, per-field basis with excerpts), exa (Agent API, grounding without excerpts + a spend budget), openai (Responses deep research,
url_citation annotations), linkup (/research structured). NOT built, said plainly: perplexity (async chat), valyu (deepresearch tasks), gemini (Interactions
agent + collaborative planning) - their wire formats have not been read yet.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx

from . import engine as E
from . import figures as F

log = logging.getLogger("santosh.research.vendors")

_transport: httpx.AsyncBaseTransport | None = None      # tests plug in httpx.MockTransport

REGISTRY: dict[str, dict[str, Any]] = {
    "hoola": {"label": "Hoola's own engine", "built": True},
    "parallel": {"label": "Parallel Task API", "built": True, "base": "https://api.parallel.ai", "key": "parallel_api_key",
                 "price": "research_parallel_run_inr", "env": "PARALLEL_API_KEY", "cancel": False},
    "exa": {"label": "Exa Agent API", "built": True, "base": "https://api.exa.ai", "key": "exa_api_key",
            "price": "research_exa_run_inr", "env": "EXA_API_KEY", "cancel": True},
    "openai": {"label": "OpenAI deep research (Responses)", "built": True, "base": "https://api.openai.com/v1", "key": "openai_api_key",
               "price": "research_openai_run_inr", "env": "OPENAI_API_KEY", "cancel": True},
    "linkup": {"label": "Linkup research", "built": True, "base": "https://api.linkup.so/v1", "key": "linkup_api_key",
               "price": "research_linkup_run_inr", "env": "LINKUP_API_KEY", "cancel": False},
    "perplexity": {"label": "Perplexity deep research", "built": False, "why": "async chat completions - wire format not read yet"},
    "valyu": {"label": "Valyu deep research", "built": False, "why": "deepresearch tasks - wire format not read yet"},
    "gemini": {"label": "Google deep research (Interactions)", "built": False, "why": "Interactions agent + collaborative planning - wire format not read yet"},
}


class VendorError(Exception):
    """A vendor call failed in a way the run should report (never carries a key)."""


class StoppedByHer(Exception):
    pass


def _csv(s: str) -> set[str]:
    return {x.strip().lower() for x in str(s or "").split(",") if x.strip()}


# ---------------------------------------------------------------- the gate
def check(engine: str, tenant: str = "", st: Any = None) -> tuple[bool, str]:
    """May this engine run research now? (ok, the first reason it may not - with how to fix it). 'hoola' always may."""
    from ..config import get_settings
    st = st or get_settings()
    engine = (engine or "hoola").lower()
    if engine == "hoola":
        return True, ""
    r = REGISTRY.get(engine)
    if r is None:
        return False, f"'{engine}' is not a research engine Hoola knows (known: {', '.join(REGISTRY)})."
    if not r["built"]:
        return False, f"{r['label']} is registered but NOT built yet: {r['why']}."
    if engine not in _csv(st.research_engines_allowed):
        return False, f"{r['label']} is not allowed: add '{engine}' to RESEARCH_ENGINES_ALLOWED (only you can turn a paid engine on)."
    if not str(getattr(st, r["key"], "") or "").strip():
        return False, f"{r['label']} has no key: set {r['env']} on the server."
    if engine not in _csv(st.research_vendor_terms_ack):
        return False, (f"{r['label']}: its terms on storing and showing its output have not been marked as read. Read the vendor's current terms, "
                       f"then add '{engine}' to RESEARCH_VENDOR_TERMS_ACK.")
    price = float(getattr(st, r["price"], 0.0) or 0.0)
    if price <= 0:
        return False, (f"{r['label']}: no per-run price is set, so no ceiling can be kept. Read the vendor's plan and set "
                       f"{r['price'].upper()} (rupees for one run).")
    from . import bill
    c = bill.caps()
    if price + c["reserve_inr"] > c["run_inr"]:
        return False, (f"{r['label']}: one run is priced at Rs {price:.0f} but the run ceiling is Rs {c['run_inr']:.0f}. "
                       f"Raise RESEARCH_RUN_CAP_INR or lower the price you set.")
    if tenant:
        from . import store
        spent = store.spent_since(tenant, bill.day_start_utc())
        if spent + price + c["reserve_inr"] > c["day_inr"]:
            return False, f"{r['label']}: today's room is Rs {max(0.0, c['day_inr'] - spent):.0f}; one run is priced at Rs {price:.0f}."
    return True, ""


def status_table(st: Any = None) -> list[dict[str, Any]]:
    """Every engine, whether it may run, and why not - for the usage report."""
    from ..config import get_settings
    st = st or get_settings()
    out = []
    for name, r in REGISTRY.items():
        ok, why = check(name, "", st)
        out.append({"engine": name, "label": r["label"], "built": r["built"], "ready": ok, "why_not": why,
                    "terms_read": name == "hoola" or name in _csv(st.research_vendor_terms_ack),
                    "run_price_inr": float(getattr(st, r["price"], 0.0) or 0.0) if r.get("price") else None})
    return out


# ---------------------------------------------------------------- what every vendor is asked, and what comes back
FINDINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "description": "Each finding is ONE verifiable statement taken from a source page.",
                     "items": {"type": "object", "properties": {
                         "claim": {"type": "string", "description": "one statement with its figure, e.g. 'The index was 412.5'"},
                         "period": {"type": "string", "description": "the date or period the statement is about"},
                         "source_url": {"type": "string", "description": "the page the statement comes from"},
                         "quote": {"type": "string", "description": "the source page's own words that carry the statement"}},
                         "required": ["claim", "period", "source_url", "quote"], "additionalProperties": False}},
        "not_found": {"type": "array", "items": {"type": "string"}, "description": "things asked for that could not be found"}},
    "required": ["findings", "not_found"], "additionalProperties": False}


@dataclass
class Claim:
    claim: str
    urls: list[str] = field(default_factory=list)
    excerpts: list[str] = field(default_factory=list)      # candidate words, the vendor's own quote / excerpts (checked against the page)
    period: str = ""
    confidence: str = ""                                     # the vendor's own label, kept for the audit only
    title: str = ""


@dataclass
class VendorResult:
    engine: str
    run_id: str
    claims: list[Claim]
    not_found: list[str] = field(default_factory=list)
    cost_inr: float | None = None                            # the vendor's OWN reported cost in rupees, when it reports one
    stop: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class Req:
    question: str
    goals: list[str]
    include_domains: list[str]
    exclude_domains: list[str]
    after_date: str
    price_inr: float
    st: Any


def instruction(req: Req) -> str:
    qs = "\n".join(f"{i}. {g}" for i, g in enumerate(req.goals, 1))
    rules = ("Rules: use primary sources (a regulator, ministry, company filing, standards body, the paper itself) over blogs and summaries. Report each "
             "finding as ONE verifiable statement with its figure and the date or period it is about, the page it comes from, and the page's own words "
             "that carry it. Do not infer, estimate or combine figures yourself - give the figures as the pages state them. If something cannot be found or "
             "confirmed, list it under not_found. If the thing asked about does not seem to exist, say so there; do not invent it.")
    extra = []
    if req.after_date:
        extra.append(f"Prefer material dated on or after {req.after_date}.")
    return f"RESEARCH QUESTION: {req.question}\nSUB-QUESTIONS:\n{qs}\n{rules}" + ("\n" + " ".join(extra) if extra else "")


def _findings(obj: Any) -> tuple[list[dict], list[str]]:
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except ValueError:
            return [], []
    if not isinstance(obj, dict):
        return [], []
    f = [x for x in (obj.get("findings") or []) if isinstance(x, dict) and str(x.get("claim") or "").strip()]
    return f, [str(x)[:300] for x in (obj.get("not_found") or []) if str(x).strip()]


def _uniq(xs: list[str]) -> list[str]:
    seen, out = set(), []
    for x in xs:
        x = str(x or "").strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------- the adapters
class Vendor:
    name = ""

    def __init__(self, st: Any):
        self.st = st
        reg = REGISTRY[self.name]
        self.base = reg["base"]
        self.key = str(getattr(st, reg["key"], "") or "")

    # -- http
    def headers(self) -> dict[str, str]:
        return {"x-api-key": self.key, "content-type": "application/json"}

    async def _req(self, method: str, path: str, body: dict | None = None, retry: bool = False) -> dict:
        """One call. Only a READ is ever retried (once); a create is never repeated - it may have succeeded."""
        last: Exception | None = None
        for attempt in range(2 if retry else 1):
            try:
                async with httpx.AsyncClient(base_url=self.base, headers=self.headers(), timeout=60, transport=_transport) as c:
                    r = await c.request(method, path, json=body)
            except httpx.HTTPError as e:
                last = VendorError(f"{self.name}: could not reach the service ({type(e).__name__})")
                if attempt == 0 and retry:
                    await asyncio.sleep(1.0)
                    continue
                raise last
            if r.status_code in (401, 403):
                raise VendorError(f"{self.name}: the key was refused ({r.status_code}) - check {REGISTRY[self.name]['env']}")
            if r.status_code in (402, 429):
                raise VendorError(f"{self.name}: out of credit or rate limited ({r.status_code})")
            if r.status_code >= 500 and attempt == 0 and retry:
                await asyncio.sleep(1.0)
                continue
            if r.status_code >= 400:
                raise VendorError(f"{self.name}: the service answered {r.status_code}: {r.text[:200].replace(self.key, '***') if self.key else r.text[:200]}")
            try:
                return r.json()
            except ValueError:
                raise VendorError(f"{self.name}: the service answered something that is not JSON")
        raise last or VendorError(f"{self.name}: failed")

    # -- the contract
    async def start(self, req: Req) -> str:
        raise NotImplementedError

    async def poll(self, run_id: str) -> tuple[str, VendorResult | None, str]:
        """(state, result, detail): state is 'running' | 'done' | 'failed'."""
        raise NotImplementedError

    async def cancel(self, run_id: str) -> bool:
        return False


class Parallel(Vendor):
    name = "parallel"

    async def start(self, req: Req) -> str:
        sp: dict[str, Any] = {}
        if req.include_domains:
            sp["include_domains"] = req.include_domains
        if req.exclude_domains:
            sp["exclude_domains"] = req.exclude_domains
        if req.after_date:
            sp["after_date"] = req.after_date
        body: dict[str, Any] = {"input": instruction(req), "processor": str(self.st.research_parallel_processor or "core"),
                                "task_spec": {"output_schema": {"type": "json", "json_schema": FINDINGS_SCHEMA}},
                                "metadata": {"source": "hoola"}}
        if sp:
            body["source_policy"] = sp
        r = await self._req("POST", "/v1/tasks/runs", body)
        rid = str(r.get("run_id") or "")
        if not rid:
            raise VendorError("parallel: no run id came back")
        return rid

    async def poll(self, run_id: str):
        r = await self._req("GET", f"/v1/tasks/runs/{run_id}", retry=True)
        s = str(r.get("status") or "")
        if s in ("queued", "running", "cancelling"):
            return "running", None, s
        if s != "completed":
            err = (r.get("error") or {}).get("message") if isinstance(r.get("error"), dict) else ""
            return "failed", None, f"{s} {err}".strip()
        res = await self._req("GET", f"/v1/tasks/runs/{run_id}/result", retry=True)
        return "done", self.parse(res, run_id), "completed"

    def parse(self, res: dict, run_id: str) -> VendorResult:
        out = res.get("output") or {}
        findings, nf = _findings(out.get("content"))
        basis = [b for b in (out.get("basis") or []) if isinstance(b, dict)]
        claims = []
        for i, f in enumerate(findings):
            cites, conf = [], ""
            for b in basis:
                fld = str(b.get("field") or "")
                if fld == f"findings.{i}" or fld.startswith(f"findings.{i}."):
                    cites += [c for c in (b.get("citations") or []) if isinstance(c, dict)]
                    conf = conf or str(b.get("confidence") or "")
            urls = _uniq([f.get("source_url")] + [c.get("url") for c in cites])
            ex = _uniq([f.get("quote")] + [e for c in cites for e in (c.get("excerpts") or [])])
            claims.append(Claim(claim=str(f["claim"]), urls=urls, excerpts=ex, period=str(f.get("period") or ""), confidence=conf))
        return VendorResult("parallel", run_id, claims, nf)


class Exa(Vendor):
    name = "exa"

    async def start(self, req: Req) -> str:
        from .. import usage
        usd = max(1.0, min(100.0, round(req.price_inr / usage.usd_inr(), 2)))      # Exa's own ceiling: 1 to 100 US dollars
        body = {"query": instruction(req), "outputSchema": FINDINGS_SCHEMA, "effort": str(self.st.research_exa_effort or "auto"),
                "budget": {"maxCostDollars": usd}, "metadata": {"source": "hoola"}}
        r = await self._req("POST", "/agent/runs", body)
        rid = str(r.get("id") or "")
        if not rid:
            raise VendorError("exa: no run id came back")
        return rid

    async def poll(self, run_id: str):
        r = await self._req("GET", f"/agent/runs/{run_id}", retry=True)
        s = str(r.get("status") or "")
        if s in ("queued", "running"):
            return "running", None, s
        if s != "completed":
            err = (r.get("error") or {}).get("message") if isinstance(r.get("error"), dict) else ""
            return "failed", None, f"{s} {err}".strip()
        return "done", self.parse(r, run_id), "completed"

    def parse(self, r: dict, run_id: str) -> VendorResult:
        from .. import usage
        out = r.get("output") or {}
        findings, nf = _findings(out.get("structured") if out.get("structured") is not None else out.get("text"))
        grounding = [g for g in (out.get("grounding") or []) if isinstance(g, dict)]
        all_cites = [c for g in grounding for c in (g.get("citations") or []) if isinstance(c, dict)]
        claims = []
        for i, f in enumerate(findings):
            mine = [g for g in grounding if str(g.get("field") or "") in (f"findings.{i}", f"findings[{i}]") or str(g.get("field") or "").startswith((f"findings.{i}.", f"findings[{i}]."))]
            cites = [c for g in mine for c in (g.get("citations") or []) if isinstance(c, dict)] or all_cites   # a field name we cannot match: every citation of the run
            conf = next((str(g.get("confidence")) for g in mine if g.get("confidence")), "")
            claims.append(Claim(claim=str(f["claim"]), urls=_uniq([f.get("source_url")] + [c.get("url") for c in cites]),
                                excerpts=_uniq([f.get("quote")]), period=str(f.get("period") or ""), confidence=conf))
        cd = r.get("costDollars") or {}
        cost = round(float(cd["total"]) * usage.usd_inr(), 4) if isinstance(cd, dict) and cd.get("total") is not None else None
        return VendorResult("exa", run_id, claims, nf, cost_inr=cost, stop=str(r.get("stopReason") or ""), usage=r.get("usage") or {})

    async def cancel(self, run_id: str) -> bool:
        try:
            await self._req("POST", f"/agent/runs/{run_id}/cancel")
            return True
        except VendorError:
            return False


class OpenAI(Vendor):
    name = "openai"

    def headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.key}", "content-type": "application/json"}

    async def start(self, req: Req) -> str:
        tool: dict[str, Any] = {"type": str(self.st.research_openai_search_tool or "web_search_preview")}
        if req.include_domains and tool["type"] == "web_search":
            tool["filters"] = {"allowed_domains": req.include_domains}
        text = (instruction(req) + "\nWrite the answer as short factual statements, one per line, each carrying its figure and its period, "
                "each with its source cited. End with a line 'NOT FOUND:' listing what could not be confirmed.")
        body = {"model": str(self.st.research_openai_model or "o4-mini-deep-research"), "input": text, "background": True, "tools": [tool],
                "max_tool_calls": int(self.st.research_openai_max_tool_calls or 40), "reasoning": {"summary": "auto"}}
        r = await self._req("POST", "/responses", body)
        rid = str(r.get("id") or "")
        if not rid:
            raise VendorError("openai: no response id came back")
        return rid

    async def poll(self, run_id: str):
        r = await self._req("GET", f"/responses/{run_id}", retry=True)
        s = str(r.get("status") or "")
        if s in ("queued", "in_progress"):
            return "running", None, s
        if s != "completed":
            err = (r.get("error") or {}).get("message") if isinstance(r.get("error"), dict) else ""
            return "failed", None, f"{s} {err}".strip()
        return "done", self.parse(r, run_id), "completed"

    def parse(self, r: dict, run_id: str) -> VendorResult:
        from .. import usage
        text, ann = "", []
        for item in r.get("output") or []:
            if isinstance(item, dict) and item.get("type") == "message":
                for part in item.get("content") or []:
                    if isinstance(part, dict) and part.get("type") == "output_text":
                        base = len(text)
                        text += str(part.get("text") or "")
                        for a in part.get("annotations") or []:
                            if isinstance(a, dict) and a.get("type") == "url_citation":
                                ann.append({"url": a.get("url"), "title": a.get("title"), "s": base + int(a.get("start_index") or 0),
                                            "e": base + int(a.get("end_index") or 0)})
        claims, nf, pos = [], [], 0
        for line in re.split(r"(?<=\n)", text):
            s, e = pos, pos + len(line)
            pos = e
            body = line.strip(" \n-*•\t")
            if not body:
                continue
            if body.upper().startswith("NOT FOUND"):
                nf += [x.strip() for x in re.split(r"[;\n]|NOT FOUND:?", body, flags=re.I) if x.strip()]
                continue
            cites = [a for a in ann if a["s"] < e and a["e"] > s]
            if not cites:
                continue                                  # a statement with no citation is not a claim Hoola can check
            clean = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\(\[[^\]]*\]\([^)]*\)\)|\[[^\]]*\]\([^)]*\)", "", body)).strip()
            claims.append(Claim(claim=clean or body, urls=_uniq([a["url"] for a in cites]), title=str(cites[0].get("title") or "")))
        u = r.get("usage") or {}
        model = str(r.get("model") or self.st.research_openai_model)
        known = usage.price_of(model)[1]
        cost = round(usage.cost(model, int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)) * usage.usd_inr(), 4) if known and u else None
        return VendorResult("openai", run_id, claims, nf, cost_inr=cost, usage=u)

    async def cancel(self, run_id: str) -> bool:
        try:
            await self._req("POST", f"/responses/{run_id}/cancel")
            return True
        except VendorError:
            return False


class Linkup(Vendor):
    name = "linkup"

    def headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.key}", "content-type": "application/json"}

    async def start(self, req: Req) -> str:
        body: dict[str, Any] = {"q": instruction(req), "outputType": "structured", "structuredOutputSchema": json.dumps(FINDINGS_SCHEMA),
                                "reasoningDepth": str(self.st.research_linkup_depth or "L"), "mode": str(self.st.research_linkup_mode or "research")}
        if req.include_domains:
            body["includeDomains"] = req.include_domains
        if req.exclude_domains:
            body["excludeDomains"] = req.exclude_domains
        if req.after_date:
            body["fromDate"] = req.after_date
        r = await self._req("POST", "/research", body)
        rid = str(r.get("id") or "")
        if not rid:
            raise VendorError("linkup: no research id came back")
        return rid

    async def poll(self, run_id: str):
        r = await self._req("GET", f"/research/{run_id}", retry=True)
        s = str(r.get("status") or "")
        if s in ("pending", "processing"):
            return "running", None, s
        if s != "completed":
            return "failed", None, f"{s} {r.get('error') or ''}".strip()
        findings, nf = _findings(r.get("output"))
        claims = [Claim(claim=str(f["claim"]), urls=_uniq([f.get("source_url")]), excerpts=_uniq([f.get("quote")]), period=str(f.get("period") or ""))
                  for f in findings]
        return "done", VendorResult("linkup", run_id, claims, nf), "completed"


ADAPTERS: dict[str, type[Vendor]] = {"parallel": Parallel, "exa": Exa, "openai": OpenAI, "linkup": Linkup}


# ---------------------------------------------------------------- run one vendor job (start or re-attach, poll, stop)
async def run_vendor(engine: str, req: Req, step: Callable[[str, str, str], None], stopped: Callable[[], bool],
                     on_id: Callable[[str], None], resume_id: str = "", sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> VendorResult:
    v = ADAPTERS[engine](req.st)
    rid = resume_id
    if not rid:
        step(req.question, "wait", f"{engine}: starting")
        rid = await v.start(req)                         # NEVER retried: a create that may have succeeded is not repeated
        on_id(rid)                                       # persisted at once, so a restart re-attaches instead of paying again
    poll_s = max(0.0, float(req.st.research_vendor_poll_s))
    deadline = time.time() + float(req.st.research_vendor_wait_s)
    while True:
        if stopped():
            await v.cancel(rid)
            raise StoppedByHer()
        state, result, detail = await v.poll(rid)
        if state == "done":
            return result                               # type: ignore[return-value]
        if state == "failed":
            raise VendorError(f"{engine}: the run ended without a result ({detail})")
        step(req.question, "wait", f"{engine}: {detail}")
        if time.time() > deadline:
            await v.cancel(rid)
            raise VendorError(f"{engine}: did not finish within {int(req.st.research_vendor_wait_s)} s (it may still bill the run)")
        await sleep(poll_s)


# ---------------------------------------------------------------- verification: Hoola reads the cited pages itself
def best_sentence(claim: str, text: str) -> str:
    """A sentence ON the page that carries the claim: every key figure of the claim in one sentence, or (no figure) a strong word overlap."""
    figs = F.key_figures(claim)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if 25 <= len(s.strip()) <= 600]
    if figs:
        for s in sents:
            nums = F.numbers(s)
            if all(F.near(v, nums) for v in figs):
                return s
        return ""
    words = set(re.findall(r"[a-zA-Zऀ-ॿ]{4,}", claim.lower()))
    if len(words) < 3:
        return ""
    best, score = "", 0.0
    for s in sents:
        ov = len(words & set(re.findall(r"[a-zA-Zऀ-ॿ]{4,}", s.lower()))) / len(words)
        if ov > score:
            best, score = s, ov
    return best if score >= 0.6 else ""


async def to_dossier(result: VendorResult, question: str, goals: list[str], policy: "E.Policy", fetch: Callable[[str], Awaitable[dict]],
                     step: Callable[[str, str, str], None] = lambda g, k, d: None, parallel: int = 4) -> dict[str, Any]:
    """The vendor's claims, re-checked by Hoola's own fetch, as the SAME dossier the own engine makes."""
    state = E.State(question=question, policy=policy)
    urls = _uniq([u for c in result.claims for u in c.urls])
    urls = [u for u in urls if policy.allows(u)[0]][:policy.pages_total]
    for u in urls:
        state.admitted[u] = "vendor"
    sem = asyncio.Semaphore(max(1, parallel))
    pages: dict[str, E.Page | None] = {}

    async def get(u: str) -> None:
        async with sem:
            try:
                step(question, "read", E._host(u))
                got = await fetch(u)
                final = str(got.get("url") or u)
                pg = E.Page(final, str(got.get("title") or ""), str(got.get("text") or ""), E._host(final))
                state.pages[u] = pg
                state.pages[final] = pg
                state.counts["reads"] += 1
                pages[u] = pg
            except asyncio.CancelledError:
                raise
            except Exception as e:     # noqa: BLE001 - a page that cannot be read means its claims stay unverified, not a dead run
                log.info("vendor claim page not readable %s: %s", u, e)
                pages[u] = None
    await asyncio.gather(*(get(u) for u in urls))
    res = E.TaskResult(goal=question[:300], round=1)
    no_cite, unreadable = [], 0
    for c in result.claims:
        usable = [u for u in c.urls if policy.allows(u)[0]]
        if not usable:
            no_cite.append(c.claim)
            continue
        chosen: tuple[str, str, bool] | None = None
        for u in usable:                                        # the vendor's own words, if they are really on the page
            pg = pages.get(u)
            if pg is None:
                continue
            for ex in c.excerpts:
                if E.excerpt_in(ex, pg.text):
                    chosen = (u, ex, True)
                    break
            if chosen:
                break
        if chosen is None:                                      # else a sentence on the page that carries the claim's figures
            for u in usable:
                pg = pages.get(u)
                if pg is None:
                    continue
                s = best_sentence(c.claim, pg.text)
                if s:
                    chosen = (u, s, True)
                    break
        if chosen is None:
            u = usable[0]
            unreadable += 1 if pages.get(u) is None else 0
            chosen = (u, c.excerpts[0] if c.excerpts else "", False)
        res.notes.append(E.Note(goal=res.goal, claim=c.claim[:600], url=chosen[0], excerpt=chosen[1][:900], verified=chosen[2],
                                title=(pages.get(chosen[0]).title if pages.get(chosen[0]) else c.title), date=c.period[:60]))
    res.pages = [p.url for p in {id(p): p for p in pages.values() if p}.values()]
    ok = sum(1 for n in res.notes if n.verified)
    res.summary = f"{result.engine}: {len(result.claims)} claims, {ok} found on their cited page by Hoola's own read"
    gaps = []
    if no_cite:
        gaps.append(f"{len(no_cite)} claim(s) came with no usable source and were dropped (e.g. \"{no_cite[0][:80]}\")")
    if len(res.notes) - ok:
        gaps.append(f"{len(res.notes) - ok} claim(s) could not be found on their cited page" + (f" ({unreadable} page(s) could not be read)" if unreadable else ""))
    gaps += result.not_found[:6]
    res.unresolved = "; ".join(gaps)[:900]
    E.STATS["notes"] += len(res.notes)
    d = E.dossier(question, policy, state, [res], [{"round": 1, "goals": list(goals)}], f"vendor {result.engine}: finished")
    d["engine"] = result.engine
    d["vendor"] = {"engine": result.engine, "run_id": result.run_id, "claims": len(result.claims), "verified_by_hoola": ok,
                   "dropped_no_source": len(no_cite), "stop": result.stop, "reported_cost_inr": result.cost_inr}
    return d


# ---------------------------------------------------------------- one vendor job, end to end (shared by the background runner and the run-off card)
async def gather(engine: str, question: str, goals: list[str], pol: "E.Policy", deps: "E.Deps", meter: Any, st: Any, over: dict | None = None,
                 on_id: Callable[[str], None] = lambda rid: None, on_cost: Callable[[], None] = lambda: None, resume_id: str = "") -> dict[str, Any]:
    """Gate re-check, price committed on the meter, the vendor run (start or re-attach), then Hoola's own verification -> the dossier.
    `StoppedByHer` propagates (the caller records the stop)."""
    ok, why = check(engine, "", st)                         # keys / allow-list / terms / price can change between the ask and the start
    if not ok:
        raise VendorError(why)
    price = float(getattr(st, REGISTRY[engine]["price"]))
    if not meter.vendor:                                    # a resumed run already carries its vendor line
        meter.set_vendor(engine, price, False, "the price you set; the vendor has not reported a cost")
    over = over or {}
    req = Req(question=question, goals=list(goals), include_domains=list(over.get("include_domains") or pol.include_domains),
              exclude_domains=list(over.get("exclude_domains") or pol.exclude_domains), after_date=str(over.get("after_date") or pol.after_date),
              price_inr=price, st=st)
    result = await run_vendor(engine, req, deps.step, deps.stopped, on_id, resume_id)
    if result.cost_inr is not None:
        meter.set_vendor(engine, result.cost_inr, True, "reported by the vendor")
    on_cost()
    d = await to_dossier(result, question, goals, pol, deps.fetch, deps.step)
    d["cost"] = meter.breakdown()                           # page fetches were counted by the step callback as they happened
    d["stats"]["cost_inr"] = d["cost"].get("total_inr")
    return d


# ---------------------------------------------------------------- which engine is the DEFAULT (v0.478 R7: the run-off's decision, if she applied one)
def default_file():
    from ..quality.run import _dir
    return _dir() / "research_default.json"


def read_default() -> dict[str, Any] | None:
    try:
        d = json.loads(default_file().read_text())
        return d if isinstance(d, dict) and d.get("engine") in REGISTRY else None
    except Exception:       # noqa: BLE001
        return None


def effective_engine(st: Any = None) -> tuple[str, str]:
    """(engine, why). `research_engine` = "auto" (the default) means the run-off's applied winner, else Hoola's own; any other value is her explicit choice."""
    from ..config import get_settings
    st = st or get_settings()
    eng = str(getattr(st, "research_engine", "auto") or "auto").lower()
    if eng != "auto":
        return eng, "set in the settings"
    d = read_default()
    if d:
        return d["engine"], f"the run-off winner applied on {d.get('decided_at', '?')}"
    return "hoola", "no run-off has been applied: Hoola's own engine"
