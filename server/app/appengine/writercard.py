"""v0.999.65 D4 THE WRITER CARD: the D0 design card's 40 briefs (quality/design_asks.py, 20 business + 20 not) each
go plan -> prototype -> React website through the writer, into an App Engine app of the hidden tenant `__writercard__`,
and are BUILT in the box (pre-rendered pages + islands). The D4 done-line is read off it: every brief builds, with 0
refused writes left.

Per brief it records: built, TypeScript clean, pages pre-rendered (and any that could not be), files written, what
AutoFix repaired, writes refused at first and refused at the end (must be 0), custom sections written by the model or
drawn as a block instead, the kit's sample sentences found on the built pages (must be none), her facts left blank
("(add yours)", blocking going live), seconds.

Two ways to run:
- FREE (`python -m app.appengine writer-card`, vps-ops site_writer_card): no model at all. The plan comes from Hoola's
  own library + the sections the brief names; the prototype's words are written by code in the prototype's own shapes
  ("Name - detail - Rs 499 (sample)", "Label: value", questions with and without answers); every 5th brief gets a
  section the kit has no block for, written by a scripted "model" that makes the slips real models make (palette
  colours, hex, one-off values, transition-all, an emoji, alert(), no alt, two h1, a browser <select>, unsafe HTML) -
  so AutoFix, the refusal + one retry, and the fall back to a block are all walked. Synthetic contact facts on even
  briefs only (never real numbers).
- LIVE (`--live --budget-inr N`): the prototype copy and the custom sections by the real model on the web tier.
  NOT RUN when this was written.

Said plainly: the free card proves the writer, AutoFix and the build on all 40 briefs; it does not judge design (that
is D5's critic) and its words are code-written stand-ins for the model's."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

TENANT = "__writercard__"
SECTION_WORDS = [
    ("menu_list", r"\bmenu\b"), ("booking_slots", r"book(?:ing)?\b|appointment|pick a time|slot"),
    ("reviews", r"review|testimonial|stories|what (?:people|clients) say"), ("gallery_masonry", r"photo|gallery|pictures"),
    ("pricing_table", r"price|plans|packages|fees|membership"), ("faq", r"\bfaq\b|questions"),
    ("team", r"doctor|stylist|trainer|faculty|partners|team|bakers|our people"), ("results_toppers", r"topper|results"),
    ("courses_list", r"course|batch|class(?:es)?\b"), ("map_hours", r"map|directions|timing|hours|reach us"),
    ("intro_story", r"story|since \d{4}|about (?:me|us)"), ("contact_block", r"form|enquir|contact|request"),
    ("products_grid", r"product|sarees|cakes|breads|store\b|shop\b"), ("process_steps", r"step by step|how (?:we|it) work"),
    ("portfolio_grid", r"projects|portfolio|our work|gallery of"), ("timeline_history", r"schedule|programme|agenda|journey"),
    ("stats_counters", r"years|numbers|impact"), ("offers_banner", r"offer|diwali|sale"),
    ("coverage_areas", r"delivery area|areas we|we deliver"), ("donate_impact", r"donat|give|volunteer"),
    ("blog_list", r"\bblog|posts|articles|notices"), ("video_showcase", r"video"), ("cta_band", r"whatsapp|call"),
    ("certificates_trust", r"certif|registered|licen[cs]e|accredit"), ("logos_marquee", r"brands we|clients|partners we"),
    ("features_split", r"facilities|what you get|features"), ("projects_case", r"case stud"),
]
APP_WORDS = r"sign.?in|log.?in|portal|dashboard|upload|members? area|my account|track"


# ---------------------------------------------------------------- 1. a plan + prototype pages, no model
def name_of(ask: dict) -> str:
    m = re.search(r"\bfor ([A-Z][\w'&.]*(?:\s+(?:and|&|of|the|[A-Z][\w'&.]*))*)", ask["ask"])
    return (m.group(1).strip() if m else (ask.get("must") or ["My site"])[0])[:60]


def plan_pages(ask: dict) -> list[dict[str, Any]]:
    """The library's plan for the brief's field, its home page widened with the sections the brief names, plus
    signed-in pages when the brief asks for a portal / sign-in / uploads; then the prototype's own skeleton."""
    from ..site import library as L
    from ..site import prototype as PT
    from ..site import service as S
    from ..site import taxonomy as T
    text = ask["ask"]
    got = L.match(text, top=1, meaning=False) or [{"id": next(iter(L.fields()))}]
    br = L.brief(got[0]["id"], L.guess_goal(text))
    plan = S.make_plan(br, {})
    low = text.lower()
    home = next((p for p in plan["pages"] if p["slug"] == "home"), plan["pages"][0])
    have = {s["type"] for s in home["sections"]}
    for typ, rx in SECTION_WORDS:
        if re.search(rx, low) and typ not in have and typ in T.SECTIONS and len(home["sections"]) < 9:
            home["sections"].append({"type": typ, "label": T.SECTIONS[typ]["label"], "design": ""})
            have.add(typ)
    if re.search(APP_WORDS, low):
        plan["spec"] = {"app_pages": [
            {"title": "Sign in", "for": "member", "shows": ["Sign in"], "types": ["screen_signin"]},
            {"title": "Your dashboard", "for": "member", "shows": ["Overview", "Your records"],
             "types": ["screen_dashboard", "screen_table"]},
            {"title": "Requests", "for": "member", "shows": ["New request", "Board"], "types": ["screen_form", "screen_board"]},
        ]}
    return PT.skeleton(plan)


def _sample_items(typ: str, n: str) -> tuple[list[str], dict[str, Any]]:
    S = " (sample)"
    table = {
        "hero": ["Open six days a week", "Two minutes from the main road", f"Trusted since 2009{S}"],
        "intro_story": [f"{n} began with one small room and a big promise.", "Today the same family still answers the phone."],
        "services_grid": [f"First visit - a full look and a clear plan - Rs 500{S}", f"Follow-up - Rs 300{S}",
                          "Home visit - when you cannot come to us", f"Same-day help - from Rs 800{S}"],
        "products_grid": [f"Kaju katli - 500 g box - Rs 450{S}", f"Gift hamper - 12 pieces - Rs 1,200{S}",
                          "Seasonal special - ask in the shop", f"Mini box - Rs 199{S}"],
        "menu_list": [f"Paneer tikka - chargrilled - Rs 280{S}", f"Dal makhani - slow cooked - Rs 240{S}",
                      f"Butter naan - Rs 60{S}", f"Gulab jamun - two pieces - Rs 90{S}"],
        "gallery_masonry": ["The front of the place", "Inside on a busy day", "A finished piece", "The team at work"],
        "process_steps": ["Call or message - tell us what you need", "We plan it - a clear price before we start",
                          "We do it - on the day we promised", "We check back - a week later"],
        "stats_counters": [f"Years open: 15+{S}", f"Happy customers: 4,800+{S}", f"Rating: 4.8/5{S}"],
        "reviews": [f'"Kind people and quick work." - Priya{S}', f"Rahul: Booked at night, sorted by morning.{S}",
                    f'"I keep coming back." - Anita{S}'],
        "pricing_table": [f"Basic - Rs 999 a month - three visits{S}", f"Plus - Rs 1,999 a month - unlimited visits{S}",
                          f"Single visit - Rs 400{S}"],
        "faq": ["Do you open on Sundays? Yes, from 10 am to 2 pm (sample)", "Can I pay by UPI?",
                "How do I book? Call or WhatsApp us (sample)", "Is parking available?"],
        "team": [f"Dr Asha - lead doctor{S}", f"Rohan - front desk{S}", f"Meera - specialist{S}"],
        "timeline_history": ["2009 - opened the first small room", "2015 - moved to a bigger place",
                             f"2024 - {n} today"],
        "features_split": ["Clean - everything sterilised and checked", "On time - your slot is your slot",
                           "Clear prices - written before we start"],
        "booking_slots": [f"First visit - 30 min - Rs 500{S}", f"Follow-up - 15 min - Rs 300{S}"],
        "courses_list": [f"JEE Main - 2 years - Rs 1,20,000{S}", f"NEET - 1 year - Rs 90,000{S}", "Foundation - 3 years"],
        "results_toppers": [f"Aarav S - JEE Advanced 2025 - 99.2%{S}", f"Isha K - NEET 2025 - 98.6%{S}"],
        "portfolio_grid": ["Sea-view flat - two bedrooms, warm wood", "Small office - forty desks in one floor",
                           "Corner cafe - a counter that sells"],
        "projects_case": ["The old kitchen had no light and no storage.", "We opened one wall and added tall units.",
                          "Twice the storage, and the family cooks together now."],
        "offers_banner": [f"Festival box - 20% off till Sunday{S}", f"Second visit free - with a friend{S}"],
        "logos_marquee": [f"Green School - education{S}", f"City Hospital - health{S}", f"Mehta Traders - retail{S}"],
        "video_showcase": ["A day with us - two minutes", "How we make it - one minute"],
        "blog_list": ["Five things to ask before you choose - a short guide", "Our new timings - from next month"],
        "certificates_trust": ["Registered - every certificate on the wall", "Insured - your work is covered",
                               "Trained - every person, every year"],
        "coverage_areas": ["Old city", "New town", "Station road", "Airport side"],
        "donate_impact": [f"Rs 500 - feeds a child for a month{S}", f"Rs 2,000 - books for a class{S}",
                          f"Children helped: 1,200+{S}"],
        "screen_dashboard": ["Open requests: 12", "Paid this month: Rs 48,000", "On time: 96%"],
        "screen_signin": ["Your records", "Your bills", "Your requests"],
        "screen_form": ["Your name", "Mobile number", "What you need"],
        "contact_block": ["A first visit", "A follow-up", "Something else"],
    }
    extra: dict[str, Any] = {}
    if typ in ("screen_table", "screen_board", "screen_approvals"):
        extra = {"cols": ["To do", "Doing", "Done"] if typ == "screen_board" else ["Name", "Date", "Status"],
                 "rows": [["Sample row", "1 Nov", "Open"]]}
    return table.get(typ, [f"{n} - what this part says", "A second point", "A third point"]), extra


def sample_copy(pages: list[dict[str, Any]], name: str, brief: str) -> list[dict[str, Any]]:
    """The prototype's words, written by code in the shapes the model gives (the free card has no model)."""
    first = re.split(r"(?<=[.:])\s", brief)[0][:200]
    out = []
    for pg in pages:
        secs = []
        for k, s in enumerate(pg["sections"]):
            items, extra = _sample_items(s["type"], name)
            heading = name if (s["type"] == "hero" and pg["slug"] == "home") else s.get("label") or pg["title"]
            secs.append({**s, "heading": heading, "line": first if k == 0 else f"{s.get('label') or ''} at {name}.",
                         "items": items, "cta": "Book a visit" if s["type"] in ("hero", "cta_band") else "", **extra})
        out.append({**pg, "sections": secs})
    return out


# ---------------------------------------------------------------- 2. the scripted custom-section "model"
GOOD_CUSTOM = '''import { Sparkles } from "lucide-react";
import { Section, Container, SectionHead } from "@/components/blocks/_kit";

const POINTS = %s;

export default function %s() {
  return (
    <Section block="%s">
      <Container>
        <SectionHead title=%s intro=%s />
        <ul className="grid gap-4 sm:grid-cols-3">
          {POINTS.map((p) => (
            <li key={p} className="flex items-start gap-3 rounded-card border border-line bg-surface p-5">
              <Sparkles className="size-5 text-primary" aria-hidden="true" />
              <span>{p}</span>
            </li>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
'''
SLOPPY = '''import { Section, Container } from "@/components/blocks/_kit";

export default function %s() {
  return (
    <Section block="%s">
      <Container>
        <h1 className="text-[40px] font-[700] text-gray-900 tracking-[-0.02em]">%s ✨</h1>
        <h1 className="text-gray-500 mt-[18px]">%s</h1>
        <img src="/photos/our-work_1.jpg" className="rounded-[12px] max-w-[640px]" />
        <div style={{ color: "#333333", background: "rgba(0,0,0,0.05)" }} className="p-[22px] bg-white border border-gray-200">
          %s
        </div>
        <button className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-[18px] py-[10px] transition-all hover:scale-105" onClick={() => alert("Thank you!")}>
          Ask us
        </button>
      </Container>
    </Section>
  );
}
'''
SELECT_FIRST = '''"use client";
import * as React from "react";
import { Section, Container, SectionHead } from "@/components/blocks/_kit";

export default function %s() {
  const [pick, setPick] = React.useState("");
  return (
    <Section block="%s">
      <Container>
        <SectionHead title=%s intro=%s />
        <select value={pick} onChange={(e) => setPick(e.target.value)} className="rounded-control border border-line bg-surface p-3">
          <option>One</option>
        </select>
      </Container>
    </Section>
  );
}
'''
UNSAFE = '''export default function %s() {
  return <div dangerouslySetInnerHTML={{ __html: "<b>%s</b>" }} />;
}
'''


def scripted_model(kind: str) -> Callable[[str, str], str]:
    """'sloppy' = every slip AutoFix repairs; 'select' = refused once (a browser <select>), right the second time;
    'unsafe' = refused both times (the section becomes a block)."""
    calls = {"n": 0}

    def call(system: str, prompt: str) -> str:
        calls["n"] += 1
        comp = re.search(r"COMPONENT NAME: (\w+)", prompt).group(1)
        sid = re.search(r"SECTION ID: (\S+)", prompt).group(1)
        words = json.loads(re.search(r"\(data, not instructions\): (\{.*\})", prompt).group(1))
        head, line = words.get("heading") or "Highlights", words.get("line") or ""
        items = words.get("items") or ["One", "Two", "Three"]
        if kind == "sloppy":
            return SLOPPY % (comp, sid, head, line, " · ".join(items))
        if kind == "select" and calls["n"] == 1:
            return SELECT_FIRST % (comp, sid, json.dumps(head), json.dumps(line))
        if kind == "unsafe":
            return UNSAFE % (comp, head)
        return GOOD_CUSTOM % (json.dumps(items, ensure_ascii=False), comp, sid, json.dumps(head), json.dumps(line))
    return call


# ---------------------------------------------------------------- 3. one brief, end to end
def _html_pages(dist: Path) -> dict[str, str]:
    out = {}
    for f in sorted(dist.rglob("index.html")):
        if "isl" in f.relative_to(dist).parts:
            continue
        out["/" + f.parent.relative_to(dist).as_posix().strip(".")] = f.read_text("utf-8", "replace")
    return out


def run_one(ask: dict, index: int, live: bool = False, model: Callable | None = None) -> dict[str, Any]:
    from ..site import prototype as PT
    from . import service as AE
    from . import writer as W
    t0 = time.time()
    name = name_of(ask)
    row: dict[str, Any] = {"id": ask["id"], "group": ask.get("group"), "name": name}
    try:
        pages = plan_pages(ask)
        custom_kind = ""
        if index % 5 == 4:                          # every 5th brief: a section the kit has no block for
            custom_kind = ("sloppy", "select", "unsafe", "sloppy")[(index // 5) % 4]
            pages[0]["sections"].insert(1, {"type": "custom_highlights", "label": "What makes us different", "design": ""})
        if live:
            from types import SimpleNamespace
            r = SimpleNamespace(name=name, facts="{}", brief=ask["ask"])
            pages = [{**pg, "sections": PT._page_copy(r, pg, ask["ask"])} for pg in pages]
        else:
            pages = sample_copy(pages, name, ask["ask"])
        facts = {"phone": f"+91 90000 000{index:02d}", "whatsapp": f"9190000000{index:02d}",
                 "address": f"{index + 1}, Main Road, Sample Nagar", "hours": "Mon-Sat 10am-8pm"} if index % 2 == 0 else {}
        app = AE.create(TENANT, name=name, brief=ask["ask"], render="site")
        mdl = model if live else (scripted_model(custom_kind) if custom_kind else None)
        st = W.write_app(TENANT, app["id"], pages, name=name, facts=facts, model=mdl, seed=ask["id"])
        res = AE.build(TENANT, app["id"])
        r = AE._load(TENANT, app["id"])
        lb = json.loads(r.last_build or "{}")
        pre = lb.get("prerender") or {}
        html = _html_pages(AE.ver_dir(r, r.version) / "dist") if res.get("built") else {}
        own = json.dumps(pages, ensure_ascii=False) + "".join(   # her words + what the writer itself wrote
            f.read_text("utf-8", "replace") for f in (AE.src_dir(r) / "src").rglob("*.tsx")
            if "components/blocks" not in f.as_posix() and "components/ui" not in f.as_posix())
        found = sorted({q for h in html.values() for q in W.leaks(h, own)})
        row.update({
            "built": bool(res.get("built")), "types_ok": bool(lb.get("types_ok")),
            "types": [f"{x.get('file')}:{x.get('line')} {x.get('message')}" for x in (lb.get("types") or [])][:6],
            "pages_planned": len(pages), "pages_rendered": pre.get("pages") or 0, "prerender_failed": pre.get("failed") or [],
            "written": st["written"], "fixed": st["fixed"], "refused_first": st["refused_first"],
            "refused_left": st["refused_left"], "custom": custom_kind, "custom_written": st["custom_written"],
            "custom_fallback": st["custom_fallback"], "blocks": sorted({s["block"] for s in st["sections"] if s.get("block")}),
            "left_out": [f"{s['page']}:{s['type']}" for s in st["sections"] if not s.get("block")],
            "sample_leaks": found[:8], "blanks": st["blanks"], "app": app["id"],
            "problems": [] if res.get("built") else [res.get("say", "")[:400]],
            "refusals": st["refusals"][:4], "fixes": [f"{x['file']}:{x['line']} {x['was']} -> {x['now']}" for x in st["fixes"][:12]]})
    except Exception as e:                           # noqa: BLE001 - one brief's failure is a row, never the card's end
        row.update({"built": False, "problems": [f"{type(e).__name__}: {e}"[:400]], "refused_left": 0})
    row["seconds"] = round(time.time() - t0, 1)
    row["ok"] = bool(row.get("built")) and row.get("refused_left", 1) == 0 and not row.get("sample_leaks") \
        and not row.get("prerender_failed")
    return row


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from . import writer as W
    built = sum(1 for r in rows if r.get("built"))
    left = sum(int(r.get("refused_left") or 0) for r in rows)
    used = sorted({b for r in rows for b in r.get("blocks") or []})
    allb = sorted(W.MAPPERS)
    return {"briefs": len(rows), "built": built, "ok": sum(1 for r in rows if r.get("ok")),
            "refused_first": sum(int(r.get("refused_first") or 0) for r in rows), "refused_left": left,
            "fixed": sum(int(r.get("fixed") or 0) for r in rows), "written": sum(int(r.get("written") or 0) for r in rows),
            "types_clean": sum(1 for r in rows if r.get("types_ok")),
            "pages": sum(int(r.get("pages_rendered") or 0) for r in rows),
            "sample_leaks": sum(len(r.get("sample_leaks") or []) for r in rows),
            "blocks_used": len(used), "blocks_unused": [b for b in allb if b not in used],
            "median_s": sorted(r.get("seconds") or 0 for r in rows)[len(rows) // 2] if rows else 0,
            "verdict": "PASS" if rows and built == len(rows) and left == 0 and all(r.get("ok") for r in rows) else "FAIL"}


def run(limit: int = 0, only: str = "", live: bool = False, budget_inr: float = 0.0, out: str = "",
        say: Callable[[str], None] = print) -> dict[str, Any]:
    from ..quality.design_asks import ASKS, SET_V
    from . import runner as RN
    av = RN.available()
    if not av["ok"]:
        return {"verdict": "FAIL", "why": "the App Engine box is not here: " + av["why"], "rows": []}
    asks = [a for a in ASKS if not only or a["id"] in only.split(",")]
    if limit:
        asks = asks[:limit]
    model = None
    if live:
        if budget_inr <= 0:
            return {"verdict": "FAIL", "why": "a live card needs --budget-inr N (the model is paid)", "rows": []}
        from ..site import ai as AI
        model = lambda system, prompt: AI.ask(system, prompt, 6000, "section")   # noqa: E731 - her tier's web writer
    from . import service as AE
    for old in AE.list_(TENANT):                    # the card's own apps from an earlier run (never anyone else's)
        try:
            AE.delete_app(TENANT, old["id"])
        except Exception:                            # noqa: BLE001
            pass
    rows = []
    for i, a in enumerate(asks):
        idx = next(k for k, x in enumerate(ASKS) if x["id"] == a["id"])
        row = run_one(a, idx, live=live, model=model)
        rows.append(row)
        say(json.dumps({k: row.get(k) for k in ("id", "ok", "built", "types_ok", "pages_rendered", "written", "fixed",
                                                "refused_first", "refused_left", "custom", "sample_leaks", "seconds",
                                                "problems")}, ensure_ascii=False))
        if live and budget_inr and _spent() >= budget_inr:
            say(f"stopped: the budget of Rs {budget_inr:g} is used")
            break
    card = {"set": SET_V, "kind": "live" if live else "free", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary": summarise(rows), "rows": rows}
    if out:
        Path(out).write_text(json.dumps(card, indent=2, ensure_ascii=False), "utf-8")
    return card


def _spent() -> float:
    try:
        from ..usage import spent_inr
        return float(spent_inr(TENANT) or 0)
    except Exception:                                # noqa: BLE001
        return 0.0
