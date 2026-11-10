"""MASTER ARCHITECT: the extra sections of the document (Markdown + the printed HTML), one place for both formats.

kind_blocks() = the job's own part (assessment / migration / decision / threat model / scale plan), shown right after
the summary because it IS the answer; tail_blocks() = growth scenarios, boundary rules, API contract, the peer review
and the design checks, shown before the open questions. Every number shown here was computed by `master` / `repomap`.
"""
from __future__ import annotations

import html as H
from typing import Any

from . import capacity, master


def _e(x: Any) -> str:
    return H.escape(str(x if x is not None else ""))


# ---------------------------------------------------------------- Markdown
def _row(cells: list[Any]) -> str:
    return "| " + " | ".join(str(c if c is not None else "").replace("|", "/").replace("\n", " ") for c in cells) + " |"


def _table(head: list[str], rows: list[list[Any]]) -> list[str]:
    return [_row(head), "|" + "---|" * len(head)] + [_row(r) for r in rows]


def kind_md(x: dict[str, Any]) -> list[str]:
    out: list[str] = []
    a = x.get("assessment") or {}
    if a:
        sc = x.get("scorecard_result") or {}
        out += ["", "## Assessment of the system as it is", a.get("as_is", "")]
        if a.get("scorecard"):
            out += ["", f"**Scorecard** - average {sc.get('average', '-')} / 5 (weakest: {', '.join(sc.get('weakest') or [])})", ""]
            out += _table(["Dimension", "Score", "Why"], [[s["dimension"], f"{s['score']}/5", s["why"]] for s in a["scorecard"]])
        if a.get("strengths"):
            out += ["", "**Strengths**"] + [f"- {s}" for s in a["strengths"]]
        if a.get("problems"):
            out += ["", "**Problems found**", ""]
            out += _table(["Severity", "Area", "Finding", "Evidence", "Fix"],
                          [[p["severity"], p["area"], p["finding"], p["evidence"], p["fix"]] for p in a["problems"]])
    m = x.get("migration") or {}
    if m:
        out += ["", "## Migration plan", f"**From:** {m.get('from')}", "", f"**To:** {m.get('to')}", "",
                f"**Strategy:** {m.get('strategy')} - {m.get('why_strategy')}", ""]
        out += _table(["Phase", "What", "Rollback", "Done when", "Risk"],
                      [[p["phase"], p["what"], p["rollback"], p["exit"], p["risk"]] for p in m.get("phases") or []])
        out += ["", f"**Data migration:** {m.get('data_migration')}", "", f"**Cut-over:** {m.get('cutover')}"]
    dc, res = x.get("decision") or {}, x.get("decision_result") or {}
    if dc:
        out += ["", "## Decision", f"**Question:** {dc.get('question')}", ""]
        if res.get("totals"):
            out += [f"**Winner (computed): {res['winner']}** by {res['margin']} points"
                    + (" - a close call" if res.get("close") else "")
                    + ("; robust to every +-1 weight change" if res.get("robust") else "; changes when: " + "; ".join(res["flips"])), ""]
            out += _table(["Rank", "Option", "Weighted score / 100"], [[t["rank"], t["option"], t["score"]] for t in res["totals"]])
        elif res.get("error"):
            out += [res["error"]]
        crit = dc.get("criteria") or []
        out += ["", "**Scores (1-5) by criterion and weight**", ""]
        out += _table(["Option"] + [f"{c['name']} (w{c['weight']})" for c in crit],
                      [[o["name"]] + [o["scores"].get(c["name"]) or "-" for c in crit] for o in dc.get("options") or []])
        for o in dc.get("options") or []:
            out += ["", f"### {o['name']}", o.get("summary", "")]
            out += [f"- + {p}" for p in o.get("pros") or []] + [f"- - {c}" for c in o.get("cons") or []]
        out += ["", f"**Recommendation:** {dc.get('recommendation')}"]
    tr = x.get("threat_result") or {}
    if tr.get("rows"):
        out += ["", "## Threat model (STRIDE)",
                f"{tr['total']} threats, {tr['open_high']} high-risk ones not yet fully mitigated."]
        if x.get("trust_boundaries"):
            out += ["", "**Trust boundaries**"] + [f"- {b}" for b in x["trust_boundaries"]]
        out += [""] + _table(["Risk", "Target", "STRIDE", "Threat", "Mitigation", "Status"],
                             [[t["risk"], t["target"], master.STRIDE[t["stride"]], t["threat"], t["mitigation"], t["status"]]
                              for t in tr["rows"]])
        if tr.get("letters_unused"):
            out += ["", "Not considered yet: " + ", ".join(tr["letters_unused"])]
    if x.get("scale_plan"):
        out += ["", "## Scale plan"] + _table(["At", "What breaks", "Early signal", "Change"],
                                              [[s["at"], s["breaks"], s["signal"], s["change"]] for s in x["scale_plan"]])
    return out


def tail_md(x: dict[str, Any]) -> list[str]:
    out: list[str] = []
    sc = x.get("scenarios") or {}
    if sc.get("rows"):
        out += ["", "## Growth scenarios (computed)"] + _table(
            ["Users / day", "Peak req/s", "Peak writes/s", "App servers (N+1)", "Storage", "Outbound"],
            [[f"{r['x']}x = {r['dau']:,.0f}", f"{r['peak_rps']:,.1f}", f"{r['write_rps']:,.1f}", r["servers"],
              capacity._human_bytes(r["storage_bytes"]), capacity._human_bytes(r["egress_bps"]) + "/s"] for r in sc["rows"]])
        out += [f"- **{b['at']}: {b['what']}** - {b['why']}" for b in sc.get("breaks") or []] or ["- Nothing crosses a stated limit up to 100x."]
    if x.get("fitness_rules"):
        out += ["", "## Boundary rules (checked by code on every pull request)"]
        out += [f"- **{r['name']}** - `{r['from']}` must not depend on `{r['must_not_depend_on']}`. {r['why']}" for r in x["fitness_rules"]]
        now = x.get("fitness_now")
        if now is not None:
            out += [f"- Today's code: {len(now)} break(s)" + (": " + "; ".join(f"{b['from']} -> {b['to']}" for b in now[:8]) if now else " - clean")]
    api = x.get("api_check") or {}
    if api and not api.get("skipped"):
        out += ["", "## API contract", f"OpenAPI: {'valid' if api.get('ok') else 'needs work'} - {api.get('operations', 0)} operations"
                + (f" ({api.get('error')})" if api.get("error") else "") + " - file api.yaml"]
    rv = x.get("review") or {}
    if rv:
        out += ["", "## Peer review", f"A second principal architect reviewed the draft: {len(rv.get('issues') or [])} issue(s)"
                + (" - all high / medium ones fixed in this version." if rv.get("revised") else ".")]
        out += [f"- [{i['severity']}] {i['area']}: {i['issue']}" for i in rv.get("issues") or []]
    if x.get("checks"):
        ok = sum(1 for c in x["checks"] if c["ok"])
        out += ["", f"## Design checks (code): {ok}/{len(x['checks'])} pass"]
        out += [f"- {'PASS' if c['ok'] else 'FAIL'} {c['check']}" + (f" - {c['detail']}" if c.get("detail") and not c["ok"] else "")
                for c in x["checks"]]
    return out


# ---------------------------------------------------------------- printed HTML
def _t(head: list[str], rows: list[list[Any]], raw_cols: tuple[int, ...] = (), cls: str = "") -> str:
    return (f"<table class='{cls}'><thead><tr>" + "".join(f"<th>{_e(h)}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c if i in raw_cols else _e(c)}</td>" for i, c in enumerate(r)) + "</tr>"
                      for r in rows) + "</tbody></table>")


def _chip(level: str) -> str:
    return f"<span class='chip {_e(level)}'>{_e(level)}</span>"


def _bar(score: float, top: float) -> str:
    w = 0 if not top else max(2, min(100, round(100 * score / top)))
    return f"<span class='bar'><i style='width:{w}%'></i></span> {score:g}"


def kind_html(x: dict[str, Any], h2) -> str:
    out: list[str] = []
    a = x.get("assessment") or {}
    if a:
        sc = x.get("scorecard_result") or {}
        out += [h2("Assessment of the system as it is"), f"<div class='summary'>{_e(a.get('as_is'))}</div>"]
        if a.get("scorecard"):
            out += [f"<p class='kpi'><b>{sc.get('average', '-')}</b> / 5 average · weakest: {_e(', '.join(sc.get('weakest') or []))}</p>",
                    _t(["Dimension", "Score", "Why"], [[s["dimension"], _bar(s["score"], 5), s["why"]] for s in a["scorecard"]], (1,))]
        if a.get("strengths"):
            out += ["<h4>Strengths</h4><ul>" + "".join(f"<li>{_e(s)}</li>" for s in a["strengths"]) + "</ul>"]
        if a.get("problems"):
            out += ["<h4>Problems found</h4>", _t(["", "Area", "Finding", "Evidence", "Fix"],
                                                  [[_chip(p["severity"]), p["area"], p["finding"], p["evidence"], p["fix"]]
                                                   for p in a["problems"]], (0,), "small")]
    m = x.get("migration") or {}
    if m:
        out += [h2("Migration plan"),
                f"<div class='two'><div class='box'><b>From</b><p>{_e(m.get('from'))}</p></div>"
                f"<div class='box'><b>To</b><p>{_e(m.get('to'))}</p></div></div>",
                f"<p><b>Strategy: {_e(m.get('strategy'))}.</b> {_e(m.get('why_strategy'))}</p>",
                _t(["Phase", "What", "Rollback", "Done when", "Risk"],
                   [[p["phase"], p["what"], p["rollback"], p["exit"], _chip(p["risk"])] for p in m.get("phases") or []], (4,), "small"),
                f"<h4>Data migration</h4><p>{_e(m.get('data_migration'))}</p><h4>Cut-over</h4><p>{_e(m.get('cutover'))}</p>"]
    dc, res = x.get("decision") or {}, x.get("decision_result") or {}
    if dc:
        out += [h2("Decision"), f"<p class='kpi'>{_e(dc.get('question'))}</p>"]
        if res.get("totals"):
            top = res["totals"][0]["score"]
            out += [f"<p><b>Winner (computed): {_e(res['winner'])}</b> by {res['margin']} points"
                    + (" - <b>a close call</b>" if res.get("close") else "")
                    + ("; the winner stays the same when any one weight moves by 1." if res.get("robust")
                       else "; <b>it changes when</b> " + _e("; ".join(res["flips"]))) + "</p>",
                    _t(["Rank", "Option", "Weighted score / 100"],
                       [[t["rank"], f"<b>{_e(t['option'])}</b>" if t["rank"] == 1 else _e(t["option"]), _bar(t["score"], 100)]
                        for t in res["totals"]], (1, 2))]
        elif res.get("error"):
            out += [f"<p>{_e(res['error'])}</p>"]
        crit = dc.get("criteria") or []
        out += ["<h4>Scores (1-5, 5 = best) by criterion and its weight</h4>",
                _t(["Option"] + [f"{c['name']} ×{c['weight']}" for c in crit],
                   [[o["name"]] + [o["scores"].get(c["name"]) or "-" for c in crit] for o in dc.get("options") or []], (), "small")]
        for o in dc.get("options") or []:
            out += [f"<section class='adr'><h3>{_e(o['name'])}</h3><p>{_e(o.get('summary'))}</p>"
                    "<div class='two'><div><b>For</b><ul>" + "".join(f"<li>{_e(p)}</li>" for p in o.get("pros") or [])
                    + "</ul></div><div><b>Against</b><ul>" + "".join(f"<li>{_e(c)}</li>" for c in o.get("cons") or [])
                    + "</ul></div></div>" + (f"<p class='note'>Cost: {_e(o.get('cost_note'))}</p>" if o.get("cost_note") else "")
                    + "</section>"]
        out += [f"<p><b>Recommendation.</b> {_e(dc.get('recommendation'))}</p>"]
    tr = x.get("threat_result") or {}
    if tr.get("rows"):
        out += [h2("Threat model (STRIDE)"),
                f"<p class='kpi'><b>{tr['total']}</b> threats · <b>{tr['open_high']}</b> high-risk not yet fully mitigated</p>"]
        if x.get("trust_boundaries"):
            out += ["<h4>Trust boundaries</h4><ul>" + "".join(f"<li>{_e(b)}</li>" for b in x["trust_boundaries"]) + "</ul>"]
        out += [_t(["Risk", "Target", "STRIDE", "Threat", "Mitigation", "Status"],
                   [[f"<span class='risk r{t['risk']}'>{t['risk']}</span>", t["target"], master.STRIDE[t["stride"]], t["threat"],
                     t["mitigation"], t["status"]] for t in tr["rows"]], (0,), "small")]
        if tr.get("matrix"):
            out += ["<h4>Coverage: threats per target and STRIDE letter</h4>",
                    _t(["Target"] + list(master.STRIDE), [[tg] + [v or "·" for v in row.values()] for tg, row in tr["matrix"].items()],
                       (), "small mat")]
        if tr.get("letters_unused"):
            out += [f"<p class='warn'>Not considered yet: {_e(', '.join(tr['letters_unused']))}</p>"]
    if x.get("scale_plan"):
        out += [h2("Scale plan"), _t(["At", "What breaks first", "Early signal", "Change"],
                                     [[s["at"], s["breaks"], s["signal"], s["change"]] for s in x["scale_plan"]])]
    return "".join(out)


def tail_html(x: dict[str, Any], h2) -> str:
    out: list[str] = []
    sc = x.get("scenarios") or {}
    if sc.get("rows"):
        out += [h2("Growth scenarios"), "<p class='note'>The capacity sheet worked out again at 10x and 100x the users, in code.</p>",
                _t(["Users / day", "Peak req/s", "Peak writes/s", "App servers (N+1)", "Storage", "Outbound"],
                   [[f"{r['x']}x · {r['dau']:,.0f}", f"{r['peak_rps']:,.1f}", f"{r['write_rps']:,.1f}", r["servers"],
                     capacity._human_bytes(r["storage_bytes"]), capacity._human_bytes(r["egress_bps"]) + "/s"] for r in sc["rows"]])]
        out += ["<ul>" + "".join(f"<li><b>{_e(b['at'])}: {_e(b['what'])}</b> - {_e(b['why'])}</li>" for b in sc["breaks"]) + "</ul>"
                if sc.get("breaks") else "<p class='note'>Nothing crosses a stated limit up to 100x.</p>"]
    if x.get("fitness_rules"):
        now = x.get("fitness_now")
        out += [h2("Boundary rules"), "<p class='note'>Checked by code on her repo now and on every pull request.</p>",
                _t(["Rule", "Module", "Must not depend on", "Why"],
                   [[r["name"], f"<code>{_e(r['from'])}</code>", f"<code>{_e(r['must_not_depend_on'])}</code>", r["why"]]
                    for r in x["fitness_rules"]], (1, 2), "small")]
        if now is not None:
            out += [f"<p class='{'warn' if now else 'ok'}'>Today's code: " + (f"{len(now)} break(s) - " + _e("; ".join(
                f"{b['from']} → {b['to']}" for b in now[:8])) if now else "follows every rule") + "</p>"]
    api = x.get("api_check") or {}
    if api and not api.get("skipped"):
        out += [h2("API contract"), f"<p>OpenAPI 3 contract <b>{'valid' if api.get('ok') else 'needs work'}</b> · "
                f"{api.get('operations', 0)} operations on {api.get('paths', 0)} paths"
                + (f" · {_e(api.get('error'))}" if api.get("error") else "") + " · delivered as <code>api.yaml</code>.</p>"]
    rv = x.get("review") or {}
    if rv:
        iss = rv.get("issues") or []
        out += [h2("Peer review"), f"<p>A second principal architect reviewed the draft before you saw it: <b>{len(iss)}</b> issue(s)"
                + (" - every high and medium one is fixed in this version." if rv.get("revised") else ".") + "</p>"]
        if iss:
            out += [_t(["", "Area", "Issue raised", "Fix"], [[_chip(i["severity"]), i["area"], i["issue"], i["fix"]] for i in iss],
                       (0,), "small")]
    if x.get("checks"):
        ok = sum(1 for c in x["checks"] if c["ok"])
        out += [h2(f"Design checks · {ok}/{len(x['checks'])} pass"),
                "<ul class='checks'>" + "".join(
                    f"<li class='{'ok' if c['ok'] else 'no'}'>{'✓' if c['ok'] else '✗'} {_e(c['check'])}"
                    + (f" <span class='note'>({_e(c['detail'])})</span>" if c.get("detail") and not c["ok"] else "") + "</li>"
                    for c in x["checks"]) + "</ul>"]
    return "".join(out)


CSS = (".kpi{font-size:10.5pt}.kpi b{color:#3a2a8f;font-size:13pt}.box{flex:1;border:.6pt solid #e2def2;border-radius:5pt;"
       "padding:6pt 8pt}.bar{display:inline-block;width:60pt;height:5pt;background:#eee;border-radius:3pt;vertical-align:1pt}"
       ".bar i{display:block;height:5pt;background:#5b3fd6;border-radius:3pt}.risk{display:inline-block;min-width:14pt;"
       "text-align:center;border-radius:3pt;font-weight:600}.r1,.r2{background:#e3f4ea}.r3,.r4{background:#fff1d6}"
       ".r6,.r9{background:#fde4e4;color:#a61b1b}table.mat td{text-align:center}table.mat td:first-child{text-align:left}"
       ".warn{color:#a61b1b}.ok{color:#17663a}ul.checks{list-style:none;padding-left:0}ul.checks li.ok{color:#17663a}"
       "ul.checks li.no{color:#a61b1b}")
