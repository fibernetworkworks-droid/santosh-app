"""v0.479 R8 KAAGAZ - the research REPORT as a DOCUMENT she can hand over.

Plan: `docs/RESEARCH_PRO_PLAN.md` part 10 ("a perfect research doc is a document, not a chat reply"). The report the model writes (R3 / R4) is only the BODY here. Everything
that makes it a document she can hand to someone is built IN CODE from the dossier, so the model cannot forget it, shorten it or invent it:

  AT A GLANCE      up to four key figures chosen by code: verified, figures in the page's own words, confidence high / medium, different sites first - never a model's pick.
  THE REPORT       as written, headings shifted under the document's own title; its own "Sources" tail is dropped (ours replaces it).
  KEY FIGURES      every verified figure: what, the period it is about, its source [n], its confidence - and the figures that are NOT confirmed, labelled as such.
  NOT CONFIRMED    the FULL list, always: every unresolved item the engine reported, every note whose words were not on its page, every figure outrunning its quote, anything a
                   vendor could not source. A report that hides its gaps cannot become a document (`research_tools.research_document` refuses it through the R3 claim check).
  SOURCES          numbered table: the site, its link, the date its figures are about, whether it looks primary BY ITS NAME, whether the page was really read, how many findings stand on it.
  HOW IT WAS MADE  engine, goals, pages read, findings checked against their pages, confidence counts, the run's date, the cost line (optional), and the one sentence that matters:
                   "figures are traced to the pages listed; traced is not the same as correct".
  CHARTS           only when a calculation of the run printed a real SERIES (label + number, 3+ rows): drawn in the workbook. Nothing is plotted from prose and nothing is invented.
                   (HOOLA PRINT and the Word writer have no chart path today, so a PDF / Word file points at the workbook rather than carry a picture of nothing.)

Her brand kit drives the PDF look (colours, name, kicker) WITHOUT a model call (`brand_art`); the Word file and the workbook keep the topic's look. Files: PDF (HOOLA PRINT, ReportLab
fallback), Word, and a workbook with the same tables as real sheets. NOT built: a Google Doc (her Google sign-in is the dependency); the Word file opens in Google Docs as is.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any

from . import figures as F

CONF_RANK = {"high": 3, "medium": 2, "low": 1, "unconfirmed": 0}
CAVEAT = ("The figures in this document are traced to the pages listed under Sources: each one was found in a page's own words or in a calculation shown here. "
          "Traced is not the same as correct - a page can be wrong or out of date. Items under 'Not confirmed' are not claims.")


def _short(s: Any, n: int) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _cell(s: Any) -> str:
    """A table cell: no pipes or newlines, no leading '=' (a sheet would read it as a formula)."""
    t = re.sub(r"\s+", " ", str(s or "")).replace("|", "/").strip()
    return ("'" + t) if t[:1] in "=+-@" and not re.match(r"^[-+]?\d", t) else t


# ---------------------------------------------------------------- the pieces
def title_of(dossier: dict, override: str = "") -> str:
    if override.strip():
        return _short(override, 90)
    q = re.sub(r"(?i)^(do\s+(?:deep\s+)?research\s+(?:on|about)|research\s+(?:karo[:,]?|the|on|about)?|deep\s+research[:,]?)\s*", "", str(dossier.get("question") or "")).strip(" :,-")
    q = re.split(r"[.?!]\s", q or str(dossier.get("question") or "Research"), maxsplit=1)[0]
    return _short(q[:1].upper() + q[1:], 90) or "Research report"


def figure_text(claim: str) -> str:
    """The figure as the claim writes it ('412.5', '18,240 units', '6.04 percent')."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?\s?(?:%|percent|per cent|lakh|crore|units?|million|billion|km|kg|MW|GW|tonnes?)?", str(claim or ""))
    return m.group(0).strip() if m else ""


def key_cards(fields: list[dict], n: int = 4) -> list[dict]:
    """The 'at a glance' figures, chosen by code: verified, supported, high / medium, one per distinct figure, different sites first, in the order the questions were asked."""
    pool = [f for f in fields if f["verified"] and f["supported"] and f["figures"] and f["confidence"] in ("high", "medium") and figure_text(f["claim"])]
    pool.sort(key=lambda f: -CONF_RANK[f["confidence"]])
    out, seen_fig, seen_host = [], set(), set()
    for passno in (0, 1):                                  # pass 0: a site not used yet; pass 1: fill up
        for f in pool:
            fig = round(f["figures"][0], 4)
            h = F.host_of(f["url"])
            if fig in seen_fig or len(out) >= n or (passno == 0 and h in seen_host):
                continue
            seen_fig.add(fig)
            seen_host.add(h)
            out.append(f)
    order = {f["id"]: i for i, f in enumerate(fields)}
    out.sort(key=lambda f: order[f["id"]])
    return [{"value": figure_text(f["claim"]), "label": _short(f["claim"], 70) + (f" ({f['date']})" if f.get("date") and f["date"].lower() not in f["claim"].lower() else "") + f" [{f['n']}]",
             "n": f["n"], "confidence": f["confidence"]} for f in out]


def figures_rows(fields: list[dict]) -> list[list[str]]:
    rows = []
    for f in sorted(fields, key=lambda f: (-CONF_RANK[f["confidence"]], f["id"])):
        rows.append([_short(f["claim"], 110), _short(f.get("date") or "-", 24), f"[{f['n']}]", f["confidence"] if f["verified"] and f["supported"] else f"{f['confidence']} - NOT CONFIRMED"])
    return rows


def unconfirmed(dossier: dict) -> list[str]:
    """Everything the document must NOT present as fact, from the dossier itself."""
    out: list[str] = []
    for t in dossier.get("tasks", []):
        for part in re.split(r";\s+", str(t.get("unresolved") or "")):
            if part.strip():
                out.append(_short(part, 200))
        if t.get("error"):
            out.append(f"This question could not be finished: {_short(t['error'], 160)}")
    for f in dossier.get("fields", []):
        if not f["verified"]:
            out.append(f"Not found on its cited page: \"{_short(f['claim'], 120)}\" [{f['n']}]")
        elif not f["supported"]:
            out.append(f"The figure is not in the quoted words: \"{_short(f['claim'], 120)}\" [{f['n']}]")
        elif f["confidence"] == "low":
            out.append(f"Only a search excerpt, the page was not read: \"{_short(f['claim'], 120)}\" [{f['n']}]")
    seen, uniq = set(), []
    for x in out:
        if x.lower() not in seen:
            seen.add(x.lower())
            uniq.append(x)
    return uniq


def sources_rows(dossier: dict) -> list[list[str]]:
    by_src: dict[int, list[dict]] = {}
    for f in dossier.get("fields", []):
        by_src.setdefault(f["n"], []).append(f)
    rows = []
    for s in dossier.get("sources", []):
        mine = by_src.get(s["n"], [])
        dates = sorted({f.get("date") for f in mine if f.get("date")})
        best = max((f["confidence"] for f in mine), key=lambda c: CONF_RANK[c], default="-")
        rows.append([f"[{s['n']}]", _short(s["host"], 40), _short(s["url"], 90), _short(", ".join(dates) or "-", 30),
                     "looks primary (by its name)" if s.get("primary_looking") else "-", "read" if s.get("read") else "search excerpt only", str(len(mine)), best])
    return rows


def series_from_calcs(dossier: dict) -> list[dict]:
    """A real series a calculation of the run printed: 3+ consecutive 'label<sep>number' lines. Nothing else is ever plotted."""
    out = []
    for t in dossier.get("tasks", []):
        for c in t.get("calcs", []):
            if not c.get("ok"):
                continue
            rows: list[tuple[str, float]] = []
            for line in str(c.get("output") or "").splitlines():
                m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9 /_\-().%]{0,40}?)\s*(?:[,:|\t]|\s{2,}|=)\s*(-?\d[\d,]*\.?\d*)\s*$", line)
                if m:
                    try:
                        rows.append((m.group(1).strip(), float(m.group(2).replace(",", ""))))
                        continue
                    except ValueError:
                        pass
                if len(rows) >= 3:
                    break
                rows = []
            if len(rows) >= 3:
                out.append({"purpose": _short(c.get("purpose") or "Series", 60), "rows": rows[:24]})
    return out[:3]


def method_rows(dossier: dict, include_cost: bool = True, as_of: str = "") -> list[list[str]]:
    s = dossier.get("stats", {})
    cf = s.get("confidence") or {}
    rows = [["Engine", str(dossier.get("engine") or "Hoola's own research engine")],
            ["Questions asked", str(s.get("goals", len(dossier.get("tasks", []))))],
            ["Pages read", str(s.get("pages_read", 0))],
            ["Findings checked against their page", f"{s.get('verified_notes', 0)} of {s.get('notes', 0)}"],
            ["Confidence of the findings", ", ".join(f"{k} {cf.get(k, 0)}" for k in ("high", "medium", "low", "unconfirmed"))],
            ["Run ended", str(dossier.get("stop_reason") or "-")],
            ["Prepared", as_of or _dt.date.today().strftime("%d %b %Y")]]
    if dossier.get("after_date"):
        rows.append(["Material preferred from", str(dossier["after_date"])])
    if include_cost and dossier.get("cost"):
        from . import bill
        rows.append(["Cost of the research", bill.format_line(dossier["cost"], hi=False)])
    return rows


def _shift_headings(body: str) -> str:
    """The report's own headings go one level down so the document's sections sit above them (h1 -> h2, h2 -> h3, h3 stays)."""
    out = []
    for ln in body.splitlines():
        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        out.append(("#" * min(3, len(m.group(1)) + 1) + " " + m.group(2)) if m else ln)
    return "\n".join(out)


def _table(header: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"] +
                     ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows])


def build_markdown(report: str, dossier: dict, *, title: str = "", include_cost: bool = True, as_of: str = "") -> tuple[str, str]:
    """(title, markdown) in the document mini-language of Document Studio. Sections that have nothing to say are still present when the document needs them."""
    title = title_of(dossier, title)
    fields = dossier.get("fields", [])
    body, _tail = F.split_report(report)
    body = _shift_headings(re.sub(r"^#\s+.*\n+", "", body.strip(), count=1) if body.lstrip().startswith("# ") else body.strip())
    cards = key_cards(fields)
    when = as_of or _dt.date.today().strftime("%d %b %Y")
    s = dossier.get("stats", {})
    md = [f"# {title}", "", "## At a glance", "", f"> [!note] As of {when}. {s.get('pages_read', 0)} page(s) read; {s.get('verified_notes', 0)} of {s.get('notes', 0)} findings were found in the words of the page they cite."]
    md += [f"[stat: {c['value']} | {c['label']}]" for c in cards]
    if not cards:
        md += ["", "No figure reached the confidence needed to be shown here; see Key figures and Not confirmed."]
    md += ["", "## The report", "", body, ""]
    md += ["## Key figures", "", _table(["Finding", "Period", "Source", "Confidence"], figures_rows(fields)) if fields else "No findings were recorded.", ""]
    nc = unconfirmed(dossier)
    md += ["## Not confirmed", "", *(["- " + x for x in nc] if nc else ["Nothing was left unconfirmed by the research run itself."]), ""]
    md += ["## Sources", "", _table(["#", "Site", "Link", "Period", "Kind", "Page", "Findings", "Best"], sources_rows(dossier)) if dossier.get("sources") else "No sources.", ""]
    md += ["## How this was made", "", _table(["Item", "Detail"], method_rows(dossier, include_cost, when)), "", f"> [!important] {CAVEAT}"]
    ser = series_from_calcs(dossier)
    if ser:
        md += ["", f"{len(ser)} chart(s) of the calculations are drawn in the workbook."]
    return title, "\n".join(md)


# ---------------------------------------------------------------- brand + files
def brand_art(brand: dict | None):
    """The PDF look from her brand kit WITHOUT a model call: the colours and name, in the fixed parts Document Studio allows. None = no kit set up."""
    if not brand or not brand.get("ready"):
        return None
    c = brand.get("colors") or {}
    pick = {"primary": c.get("primary"), "accent": c.get("accent"), "cover": "band", "kicker": str(brand.get("name") or "")[:48]}

    def ask(system, prompt, kind, images, timeout):
        return dict(pick)
    return ask


def workbook_sheets(dossier: dict, include_cost: bool = True) -> tuple[dict, list[dict]]:
    f_rows = [["#", "Finding", "Period", "Source #", "Link", "Confidence", "Why", "The page's words", "Found on the page"]]
    for f in sorted(dossier.get("fields", []), key=lambda f: f["id"]):
        f_rows.append([f["id"], _cell(f["claim"]), _cell(f.get("date") or ""), f["n"], _cell(f["url"]), f["confidence"], _cell("; ".join(f.get("why") or [])),
                       _cell(_short(f["excerpt"], 300)), "yes" if f["verified"] else "NO"])
    sheets: dict[str, Any] = {"Figures": f_rows,
                              "Sources": [["#", "Site", "Link", "Period", "Kind", "Page", "Findings", "Best"]] + sources_rows(dossier),
                              "Not confirmed": [["Item"]] + [[x] for x in (unconfirmed(dossier) or ["Nothing was left unconfirmed by the research run itself."])],
                              "Method": [["Item", "Value"]] + method_rows(dossier, include_cost)}
    charts = []
    for i, s in enumerate(series_from_calcs(dossier), 1):
        name = f"Series {i}"
        sheets[name] = [["Label", "Value"]] + [[a, b] for a, b in s["rows"]]
        n = len(s["rows"])
        charts.append({"sheet": name, "type": "bar" if n <= 8 else "line", "categories": f"A2:A{n + 1}", "values": f"B2:B{n + 1}", "title": s["purpose"]})
    return sheets, charts


def build_files(report: str, dossier: dict, kinds: list[str] | None = None, brand: dict | None = None, *, title: str = "", include_cost: bool = True) -> dict[str, Any]:
    """Make the requested files. Returns {title, files: [{kind, data, notes}], notes}. Blocking (Chromium prints the PDF): call in a thread."""
    from ..agent import docstudio_tools as DT
    from ..docstudio import docxgen, xlsxgen
    kinds = [k for k in (kinds or ["pdf"]) if k in ("pdf", "docx", "xlsx")] or ["pdf"]
    ttl, md = build_markdown(report, dossier, title=title, include_cost=include_cost)
    files, notes = [], []
    author = str((brand or {}).get("name") or "Hoola") if brand and brand.get("ready") else "Hoola"
    for k in kinds:
        if k == "pdf":
            art = brand_art(brand)
            try:
                from ..docstudio import htmlpdf
                if htmlpdf.available():
                    res = htmlpdf.make_pdf(ttl, md, author=author, prepared_for="", subject=_short(dossier.get("question"), 140), art=art)
                else:
                    raise RuntimeError("no Chromium")
            except Exception as e:      # noqa: BLE001 - the file must still reach her
                notes.append(f"HOOLA PRINT could not print ({_short(e, 80)}); the plain PDF writer was used")
                res = DT.pdfgen.make_pdf(ttl, md, author=author, subject=_short(dossier.get("question"), 140))
            if art:
                notes.append("PDF in her brand colours")
        elif k == "docx":
            res = docxgen.make_docx(ttl, md, subject=_short(dossier.get("question"), 140), author=author)
            notes.append("Word keeps the topic's look; her brand colours apply to the PDF")
        else:
            sheets, charts = workbook_sheets(dossier, include_cost)
            res = xlsxgen.make_xlsx(ttl, sheets, charts=charts)
            if charts:
                notes.append(f"{len(charts)} chart(s) from the calculation series")
        files.append({"kind": k, "data": res["data"], "qa": res.get("qa"), "pages": res.get("pages")})
    return {"title": ttl, "files": files, "notes": notes, "sections": ["At a glance", "The report", "Key figures", "Not confirmed", "Sources", "How this was made"]}
