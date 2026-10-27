"""Memory of the Computer Operator (from the owner's hoola-browser engine): task recipes learned from real runs,
site notes, playbooks from research, and recipe replay. One folder per owner (data/operator/<tenant>/memory).

A recipe stores *what each element means* (role, label, name, id...) rather than brittle positions, so replay can
find the same field after a website redesign. Personal values are never stored: they become {variables}. Fields
only the owner fills (passwords, OTP, Aadhaar...) and payments are stored as owner steps, asked again on replay.
"""
from __future__ import annotations

import asyncio
import copy
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from .browser import Operator, OperatorError, Session, fmt_item, fmt_snapshot, gate_of, site_of

VAR = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "recipe"


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9ऀ-෿]+", " ", (s or "").lower()).strip()


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if len(t) > 1}


def match_score(d: dict, c: dict) -> float:
    """How well a page element c matches a recorded element description d."""
    sc = 0.0
    if d.get("role"):
        sc += 2 if c.get("role") == d["role"] else -3
    dn, cn = _norm(d.get("name")), _norm(c.get("name"))
    dl, cl = _norm(d.get("label")), _norm(c.get("label"))
    if dn and dn == cn:
        sc += 6
    elif dn and cn and (dn in cn or cn in dn):
        sc += 3
    elif dn and cn:
        a, b = _tokens(dn), _tokens(cn)
        if a and b:
            sc += 3 * len(a & b) / len(a | b)
    if dl and dl == cl:
        sc += 2
    if d.get("id") and d["id"] == c.get("id"):
        sc += 4
    if d.get("nameAttr") and d["nameAttr"] == c.get("nameAttr"):
        sc += 3
    if d.get("placeholder") and d["placeholder"] == c.get("placeholder"):
        sc += 2
    if d.get("type") and d["type"] == c.get("type"):
        sc += 1
    if d.get("href") and c.get("href"):
        if d["href"] == c["href"]:
            sc += 3
        elif d["href"].split("?")[0] == c["href"].split("?")[0]:
            sc += 2
    if d.get("css") and d["css"] == c.get("css"):
        sc += 1.5
    if d.get("group") and d["group"] == c.get("group"):
        sc += 1
    return sc


def best_match(d: dict, items: list[dict]) -> tuple[dict | None, str]:
    scored = sorted(((match_score(d, c), c) for c in items), key=lambda x: -x[0])
    if not scored or scored[0][0] < 6:
        return None, f"no element on the page looks like {d.get('role')} \"{d.get('name')}\""
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 1.5:
        return None, (f"two elements look like \"{d.get('name')}\": {fmt_item(scored[0][1])} / {fmt_item(scored[1][1])}")
    return scored[0][1], ""


class Memory:
    def __init__(self, home: Path):
        self.root = home / "memory"
        for d in ("recipes", "sites", "playbooks"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- recipes
    def recipe_path(self, name: str) -> Path:
        return self.root / "recipes" / f"{slug(name)}.json"

    def load(self, name: str) -> dict:
        p = self.recipe_path(name)
        if not p.exists():
            found = self.find(name, limit=3)
            hint = f" Similar: {[r['name'] for r in found['recipes']]}" if found["recipes"] else ""
            raise OperatorError(f"No recipe '{name}'.{hint}")
        return json.loads(p.read_text(encoding="utf-8"))

    def save(self, r: dict) -> dict:
        p = self.recipe_path(r["name"])
        if p.exists():
            old = json.loads(p.read_text(encoding="utf-8"))
            r["version"] = old.get("version", 1) + 1
            r["created"] = old.get("created", r.get("created"))
            r["runs"] = old.get("runs", 0)
            (p.parent / f"{p.stem}.v{old.get('version', 1)}.json").write_text(json.dumps(old, indent=1, ensure_ascii=False))
        r.setdefault("version", 1)
        r["updated"] = dt.datetime.now().isoformat(timespec="seconds")
        p.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        return r

    def from_trace(self, s: Session, name: str, task: str, literal_steps: list[int] | None = None,
                   variable_steps: list[int] | None = None, notes: str = "") -> dict:
        # literal_steps / variable_steps are numbers from session_trace; keep them attached to the steps
        for k, st in enumerate(s.trace):
            st["_n"] = k
        literal_n = set(literal_steps or [])
        variable_n = set(variable_steps or [])
        raw = [copy.deepcopy(st) for st in s.trace if not st.get("failed")]
        steps: list[dict] = []
        for i, st in enumerate(raw):
            # a field filled again later on the same page (mistake fixed during the run) keeps only the last value
            if st["action"] in ("fill", "type", "select", "check", "upload") and st.get("target"):
                later = False
                for nx in raw[i + 1:]:
                    if nx.get("after_url") or nx["action"] == "open":
                        break
                    if nx["action"] == st["action"] and nx.get("target") == st.get("target"):
                        later = True
                        break
                if later:
                    continue
            steps.append(st)
        literal = {i for i, st in enumerate(steps) if st.get("_n") in literal_n}
        variable = {i for i, st in enumerate(steps) if st.get("_n") in variable_n}
        for st in steps:
            st.pop("_n", None)
        for st in s.trace:
            st.pop("_n", None)
        variables: dict[str, dict] = {}
        used: set[str] = set()
        for i, st in enumerate(steps):
            hint = st.pop("var_hint", None)
            if st["action"] not in ("fill", "type", "select", "check", "upload"):
                continue
            make_var = st.get("sensitive") or (st["action"] in ("fill", "type", "upload") and i not in literal) or i in variable
            if st.get("radio") and i in variable:
                # a radio choice per person: store the group, choose the option by its label at replay
                g = (st.get("target") or {}).get("group") or "choice"
                vname = re.sub(r"[^a-z0-9]+", "_", g.lower()).strip("_") or "choice"
                used.add(vname)
                st["value"] = "{" + vname + "}"
                variables[vname] = {"step": i, "field": "choose one of the options (radio)", "action": "choose",
                                    "example_option": (st.get("target") or {}).get("name")}
                continue
            if not make_var:
                continue
            if isinstance(st.get("value"), str) and VAR.fullmatch(st["value"]):
                vname = VAR.fullmatch(st["value"]).group(1)
            else:
                vname = hint or (st.get("target") or {}).get("name") or "value"
                vname = re.sub(r"[^a-z0-9]+", "_", vname.lower()).strip("_")[:40] or "value"
            base, k = vname, 2
            while vname in used:
                vname = f"{base}_{k}"
                k += 1
            used.add(vname)
            st["value"] = "{" + vname + "}"
            variables[vname] = {"step": i, "field": (st.get("target") or {}).get("name", ""), "action": st["action"]}
        first_url = next((st["url"] for st in steps if st.get("url")), "")
        r = {"name": name, "task": task, "site": site_of(first_url), "start_url": first_url,
             "created": dt.datetime.now().isoformat(timespec="seconds"), "steps": steps, "variables": variables,
             "human_steps": sum(1 for st in steps if st["action"] == "human") + sum(1 for st in steps if st.get("gate")),
             "notes": notes, "runs": 0}
        return self.save(r)

    def find(self, query: str, site: str | None = None, limit: int = 8) -> dict:
        q = _tokens(query)
        out = {"recipes": [], "playbooks": []}
        for p in (self.root / "recipes").glob("*.json"):
            if re.search(r"\.v\d+\.json$", p.name):
                continue
            r = json.loads(p.read_text(encoding="utf-8"))
            if site and site_of("https://" + site) not in r.get("site", ""):
                continue
            words = _tokens(f"{r['name']} {r['task']} {r.get('site', '')} {r.get('notes', '')}")
            score = len(q & words) / max(1, len(q))
            if score > 0 or not q:
                out["recipes"].append({"name": r["name"], "task": r["task"], "site": r.get("site"), "score": round(score, 2),
                                       "variables": list(r.get("variables", {})),
                                       "version": r.get("version"), "runs": r.get("runs", 0), "updated": r.get("updated")})
        for p in (self.root / "playbooks").glob("*.md"):
            txt = p.read_text(encoding="utf-8")
            score = len(q & _tokens(p.stem + " " + txt[:400])) / max(1, len(q))
            if score > 0:
                out["playbooks"].append({"task": p.stem, "score": round(score, 2), "preview": txt[:200]})
        for k in out:
            out[k] = sorted(out[k], key=lambda x: -x["score"])[:limit]
        return out

    # ---------------------------------------------------------------- notes and playbooks
    def site_note_add(self, site: str, note: str) -> str:
        site = site_of(site if "://" in site else "https://" + site)
        p = self.root / "sites" / f"{site}.md"
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"- {dt.date.today().isoformat()}: {note.strip()}\n")
        return site

    def site_notes(self, site: str) -> str:
        site = site_of(site if "://" in site else "https://" + site)
        p = self.root / "sites" / f"{site}.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def playbook_save(self, task: str, steps_markdown: str, sources: list[str] | None = None) -> str:
        p = self.root / "playbooks" / f"{slug(task)}.md"
        src = "\n".join(f"- {u}" for u in (sources or []))
        p.write_text(f"# {task}\n_saved {dt.date.today().isoformat()}_\n\n{steps_markdown.strip()}\n\n## Sources\n{src}\n",
                     encoding="utf-8")
        return p.stem

    def playbook_get(self, task: str) -> str:
        p = self.root / "playbooks" / f"{slug(task)}.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
        f = self.find(task)["playbooks"]
        if f:
            return (self.root / "playbooks" / f"{f[0]['task']}.md").read_text(encoding="utf-8")
        return ""


# -------------------------------------------------------------------- replay
async def run_recipe(op: Operator, mem: Memory, s: Session, name: str, variables: dict[str, str] | None = None,
                     start_step: int = 0, approval_id: str | None = None) -> dict:
    """Replay a recipe step by step. Pauses for humans at gates, and hands back to the AI (status needs_help)
    when a page no longer matches, with the step and a fresh snapshot, so the AI can fix it and continue."""
    r = mem.load(name)
    variables = {k: str(v) for k, v in (variables or {}).items()}
    steps = r["steps"]
    needed = sorted({m for st in steps for m in VAR.findall(str(st.get("value", "")) + str(st.get("url", "")))})
    missing = [v for v in needed if v not in variables]
    if missing and start_step == 0:
        return {"status": "needs_input", "missing_variables": missing,
                "fields": {v: r["variables"].get(v, {}).get("field") for v in missing},
                "message": "Ask the owner for these values (ask_owner kind='question'), then run again."}

    def sub(v: Any) -> Any:
        return VAR.sub(lambda m: variables.get(m.group(1), m.group(0)), v) if isinstance(v, str) else v

    log = []
    for i in range(start_step, len(steps)):
        st = steps[i]
        act = st["action"]
        try:
            if act == "open":
                res = await op.goto(s, sub(st["url"]))
                log.append(f"{i}: open {res['url']}")
                continue
            if act == "human":
                if st["kind"] in ("approve", "question", "choice"):
                    continue  # the gated click asks for approval itself; questions were for that one run
                ref = None
                if st.get("target"):
                    snap = await op.snapshot(s)
                    it, _ = best_match(st["target"], snap["items"])
                    ref = it["ref"] if it else None
                if st["kind"] in ("otp", "captcha", "secret", "payment") and not ref:
                    return {"status": "needs_help", "failed_step": i, "step": st, "done": log, "page": fmt_snapshot(await op.snapshot(s)),
                            "reason": f"the box / button for the owner's {st['kind']} step is not on this page",
                            "message": f"Find it yourself, ask_owner, then recipe_run(..., start_step={i + 1})."}
                a = await op.request_human(s, st["kind"], st.get("reason", "Your help is needed"), ref)
                return {"status": "waiting_human", "request": a.public(), "resume_step": i + 1, "done": log,
                        "message": "Call wait_for_human(request_id), then recipe_run(..., start_step=resume_step)."}
            # find the element again by meaning, retrying briefly while the page loads
            it, why = None, ""
            want = sub(st.get("value"))
            for attempt in range(6):
                snap = await op.snapshot(s)
                if st.get("radio") and isinstance(st.get("value"), str) and VAR.search(st["value"]):
                    radios = [c for c in snap["items"] if c["role"] == "radio"]
                    grp = [c for c in radios if c.get("group") == (st["target"] or {}).get("group")] or radios
                    it = next((c for c in grp if _norm(c["name"]) == _norm(want)), None) or \
                        next((c for c in grp if _norm(want) and _norm(want) in _norm(c["name"])), None)
                    why = f"no option \"{want}\" among {[c['name'] for c in grp]}"
                    if it:
                        st = dict(st, value="true")
                else:
                    it, why = best_match(st["target"], snap["items"])
                if it:
                    break
                await asyncio.sleep(0.7)
            if not it:
                return {"status": "needs_help", "failed_step": i, "step": st, "reason": why, "done": log,
                        "page": fmt_snapshot(snap),
                        "message": "Do this step yourself with the normal tools, then continue with "
                                   f"recipe_run(..., start_step={i + 1}). Save the run again to update the recipe."}
            value = sub(st.get("value"))
            g = gate_of(it) if act == "click" else ""
            if g == "payment":
                a = await op.request_human(s, "payment", st.get("reason") or f"Payment: \"{it['name']}\" - aap khud dabaiye", it["ref"])
                return {"status": "waiting_human", "request": a.public(), "resume_step": i + 1, "done": log,
                        "message": "The owner presses the payment button herself; then continue at resume_step."}
            if act == "click" and (st.get("gate") or g == "commit"):
                if not approval_id:
                    a = await op.request_human(s, "approve", st.get("reason") or f"About to press \"{it['name']}\"", it["ref"])
                    return {"status": "waiting_human", "request": a.public(), "resume_step": i, "done": log,
                            "message": "Gate: call wait_for_human(request_id); if approved run "
                                       f"recipe_run(..., start_step={i}, approval_id=<id>)."}
                res = await op.act(s, "click", it["ref"], approval_id=approval_id)
                approval_id = None
            else:
                res = await op.act(s, act, it["ref"], value=value)
            if not res.get("ok"):
                return {"status": "needs_help", "failed_step": i, "step": st, "reason": res.get("message"), "done": log}
            if st.get("after_url") and not res["url_changed"] and res.get("alerts"):
                return {"status": "needs_help", "failed_step": i, "step": st, "done": log,
                        "reason": "the page showed an error instead of moving on: " + " | ".join(res["alerts"]),
                        "page": fmt_snapshot(await op.snapshot(s))}
            log.append(f"{i}: {act} \"{it['name']}\"" + (f" = {res.get('value')}" if res.get("value") else ""))
        except OperatorError as e:
            return {"status": "needs_help", "failed_step": i, "step": st, "reason": str(e), "done": log}
    r["runs"] = r.get("runs", 0) + 1
    r["last_run"] = dt.datetime.now().isoformat(timespec="seconds")
    mem.recipe_path(name).write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    snap = await op.snapshot(s)
    return {"status": "done", "done": log, "downloads": s.downloads[-5:], "page": fmt_snapshot(snap)}
