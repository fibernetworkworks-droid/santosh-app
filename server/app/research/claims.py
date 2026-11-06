"""v0.474 R3 SABOOT - a research report is built from FIELDS, and a report is checked against them before she sees it.

Plan: `docs/RESEARCH_PRO_PLAN.md` part 7. The model is Parallel's `field_basis` (`docs/research/research_apis/01_techniques.md` s4): not
"a report with footnotes" but evidence attached to each field - its reasoning, its citations with the page's own EXCERPTS, and a
confidence. Hoola's version, all of it computed in code from what the run really fetched:

  a FIELD     claim + the page's own words + the page + the date + whether those words are on the page (R2) + whether the
              figures the CLAIM states are in those words or in a calculation of this run (new here) + a CONFIDENCE:
                high        verified, figures supported, the site looks primary (government / regulator / university /
                            standards body by its name) and the field is dated - OR verified, supported and a different website
                            carries the same figure
                medium      verified and figures supported
                low         verified but the figure is not in the quoted words (a claim that outruns its evidence), or the page
                            was not read (search excerpt only)
                unconfirmed the words were not found on the page
              Confidence is a RULE, printed with its reasons - never a model's feeling.
  the CHECK   `check_report(report, dossier)`: before she sees a research answer, every figure in it must be carried by a field
              whose words say it (or by a calculation of this run); a figure cited to [n] must be in source n's field; a link
              that is not a source of this run, a figure only a NOT VERIFIED note carries, and a report that hides the gaps
              all come back as fix notes in the model's own working language. A model reads the notes and fixes the draft once.

WHAT IT DOES NOT DO, said plainly: it cannot tell whether a page is RIGHT (traceable is not true), it does not re-open the live page
(the worker's read of it is the evidence; R4 can re-read on a schedule), and it does not detect two sources that disagree with each other
unless both are stated figures of the same field - that stays the worker's job and the report's "where sources disagree" line.
"""
from __future__ import annotations

import re
from typing import Any

from . import figures as F

CONF_ORDER = ("unconfirmed", "low", "medium", "high")
MAX_FINDINGS = 5


def _num_pool(text: str) -> list[float]:
    return F.numbers(text)


def build_fields(tasks: list[dict], sources: list[dict], page_text: dict[str, str], calc_numbers: list[float],
                 is_primary) -> list[dict]:
    """One field per note. `tasks` = the dossier's tasks, `sources` its numbered source list, `page_text` url -> text read."""
    prim = {s["url"]: bool(s.get("primary_looking")) for s in sources}
    read = {s["url"]: bool(s.get("read")) for s in sources}
    flat = [(t["goal"], n) for t in tasks for n in t["notes"]]
    fields: list[dict] = []
    for i, (goal, n) in enumerate(flat, 1):
        claim_figs = F.key_figures(n["claim"])
        words = _num_pool(n["excerpt"])
        gaps = [v for v in claim_figs if not F.near(v, words) and not F.near(v, calc_numbers)]
        fields.append({"id": f"f{i}", "goal": goal, "claim": n["claim"], "url": n["url"], "n": n["n"], "excerpt": n["excerpt"],
                       "verified": bool(n["verified"]), "date": n.get("date", ""), "figures": [round(v, 4) for v in claim_figs],
                       "figures_in_words": [round(v, 4) for v in words], "unsupported_figures": [round(v, 4) for v in gaps],
                       "supported": not gaps, "primary": prim.get(n["url"], False), "read": read.get(n["url"], False),
                       "dated": bool(n.get("date")) and (not F.YEAR.search(n["date"]) or
                                                        any(y in (page_text.get(n["url"], "") + " " + n["excerpt"])
                                                            for y in F.YEAR.findall(n["date"])))})
    # a figure two DIFFERENT websites carry in their own words
    for f in fields:
        hosts = {F.host_of(o["url"]) for o in fields if o["verified"] and o["supported"] and o is not f
                 and any(F.near(v, o["figures_in_words"]) for v in f["figures"])}
        f["corroborated_by"] = sorted(h for h in hosts if h != F.host_of(f["url"]))
        f["confidence"], f["why"] = confidence(f)
    return fields


def confidence(f: dict) -> tuple[str, list[str]]:
    if not f["verified"]:
        return "unconfirmed", ["the quoted words were not found on the page"]
    if not f["supported"]:
        return "low", ["the figure(s) " + ", ".join(f"{v:g}" for v in f["unsupported_figures"]) +
                       " are not in the quoted words or in any calculation of this run"]
    if not f["read"]:
        return "low", ["only a search excerpt - the page itself was not read"]
    why = ["the words are on the page", "the figures are in the words" if f["figures"] else "no figure to check"]
    if f["corroborated_by"]:
        return "high", why + ["a different website carries the same figure: " + ", ".join(f["corroborated_by"][:3])]
    if f["primary"] and f["dated"]:
        return "high", why + ["the site looks primary by its name", "dated"]
    return "medium", why + (["the site does not look primary by its name"] if not f["primary"] else []) + \
        ([] if f["dated"] else ["no date on the field"])


def summary(fields: list[dict]) -> dict[str, int]:
    out = {k: 0 for k in CONF_ORDER}
    for f in fields:
        out[f["confidence"]] += 1
    return out


# ---------------------------------------------------------------- the check a report passes before she sees it
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def check_report(report: str, dossier: dict | None) -> list[str]:
    """Fix notes for a research report written from `dossier` ([] = nothing found, or nothing to check against)."""
    if not dossier or not dossier.get("fields") and not dossier.get("tasks"):
        return []
    fields: list[dict] = dossier.get("fields") or []
    calc_nums = [v for t in dossier.get("tasks", []) for c in t.get("calcs", []) if c.get("ok") for v in F.numbers(c.get("output", ""))]
    body, _src = F.split_report(report)
    out: list[str] = []

    # 1. a link that is not a source of THIS run
    listed = {F.norm_url(s["url"]) for s in dossier.get("sources", [])}
    stray = [u for u in dict.fromkeys(F.norm_url(u) for u in F.URL.findall(report or "")) if u.split("?")[0] not in listed
             and not any(u.split("?")[0] == s.split("?")[0] for s in listed)]
    if stray:
        out.append("These links are not sources of this research (cite only the dossier's sources): " + ", ".join(stray[:4]) + ".")

    good = [f for f in fields if f["verified"] and f["supported"]]
    weak = [f for f in fields if not (f["verified"] and f["supported"])]
    asked = dossier.get("question", "")
    flagged: set[float] = set()
    for seg in _SENT.split(body):
        seg = seg.strip()
        if not seg:
            continue
        refs = {int(x) for x in F.REF.findall(seg)}
        for v in F.key_figures(seg, asked):
            if round(v, 4) in flagged:
                continue
            by_good = [f for f in good if F.near(v, f["figures_in_words"]) or F.near(v, f["figures"])]
            if F.near(v, calc_nums):
                continue
            if not by_good:
                by_weak = [f for f in weak if F.near(v, f["figures_in_words"]) or F.near(v, f["figures"])]
                if by_weak and any(w in seg.lower() for w in F.UNSURE):
                    continue            # v0.477: the report states that figure AS unconfirmed in the same sentence - exactly what it should do
                flagged.add(round(v, 4))
                if by_weak:
                    out.append(f"The figure {v:g} comes only from a note that is NOT VERIFIED or whose claim outruns its quoted words "
                               f"([{by_weak[0]['n']}]). State it as unconfirmed, or drop it.")
                else:
                    out.append(f"The figure {v:g} is in no note of the research dossier and no calculation. Remove it, or say it could "
                               f"not be confirmed; do not write a number from memory.")
            elif refs and not any(f["n"] in refs for f in by_good):
                flagged.add(round(v, 4))
                out.append(f"The figure {v:g} is cited to [{', '.join(str(r) for r in sorted(refs))}] but those sources' own words do "
                           f"not carry it; the dossier has it under [{by_good[0]['n']}]. Cite the right source.")
            if len(out) >= MAX_FINDINGS:
                return out[:MAX_FINDINGS]

    # 3. the gaps must not be hidden
    gaps = any(t.get("unresolved") for t in dossier.get("tasks", [])) or any(not f["verified"] for f in fields)
    if gaps and not any(w in str(report or "").lower() for w in F.UNSURE):
        out.append("The dossier lists things that could NOT be confirmed (or notes that are NOT VERIFIED) but the report does not say so. "
                   "Add a short section saying what could not be confirmed.")
    return out[:MAX_FINDINGS]
