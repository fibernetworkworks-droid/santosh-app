"""v0.531 PRAYOGSHALA step 2 - the bridge between Developer Sahayak and the lab (`app/devlab`).

Step 1 built the box; it had no caller, which by this repo's own rule means it did not work yet. This is the caller.
What it gives the coding loop is the one thing the research says decides everything (docs/CODING_HARNESS_PLAN.md 1.2):
a command that comes back pass or fail, in seconds, on the code as it is RIGHT NOW - the model's in-memory edits
written over a real checkout, not the base commit and not her CI minutes later.

Guards, all of them before anything runs:
- the switch `dev_lab` must be on (it is OFF until `lab_check` passes on her VPS);
- Docker must answer;
- a command must be DECLARED (her word / .hoola/lab.json / the repo's rules / its CI / a language default), and one
  that Hoola merely READ waits for her tap - the lab simply stays shut for that task and says why;
- one clone per task, reused for every check in it, deleted at the end."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("santosh.devsahayak.lab")

MAX_RUNS = 12            # checks one task may run (a loop that re-runs for ever is a loop that is stuck)
PROOF_RUNS = 2           # the local red-then-green proof


def ready(tenant: str = "") -> dict[str, Any]:
    """Is the lab usable at all right now? Cheap: a settings read and `docker version`."""
    from ..config import get_settings
    if not bool(getattr(get_settings(), "dev_lab", False)):
        return {"ok": False, "why": "the lab is off (dev_lab off - lab_check must pass on the VPS first)"}
    from ..devlab import box
    av = box.available()
    return {"ok": bool(av["ok"]), "why": av.get("why", "")}


class Lab:
    """One task's workspace. Open it once, run checks as the work goes, close it at the end."""

    def __init__(self, tenant: str, t: Any, token: str, hers: dict[str, str] | None = None, ref: str = ""):
        from ..devlab import service as LS
        self.LS = LS
        self.tenant, self.task, self.number = tenant, getattr(t, "id", ""), getattr(t, "number", "")
        self.repo, self.ref = getattr(t, "repo", ""), ref or getattr(t, "base", "") or ""
        self.ws = LS.open_workspace(self.repo, self.ref, token, hers)
        self.runs = 0
        self.last: dict[str, Any] = {}
        self.why = self.ws.get("why", "") if not self.ws.get("ok") else ""
        if self.ws.get("ok") and self.ws.get("confirm"):
            self.why = (f"this repo's check command `{self.ws['spec']['test']}` was read from {self.ws['source']} - "
                        "approve it once and I will use the lab")
        elif self.ws.get("ok") and not self.ws.get("cmd"):
            self.why = self.ws.get("why") or "no check command is declared"

    # ------------------------------------------------------------ what the loop asks
    @property
    def usable(self) -> bool:
        return bool(self.ws.get("ok") and self.ws.get("cmd") and not self.ws.get("confirm"))

    @property
    def cmd(self) -> str:
        return str(self.ws.get("cmd") or "")

    @property
    def source(self) -> str:
        return str(self.ws.get("source") or "")

    def run(self, overlay: dict[str, str] | None = None, only: str = "", label: str = "") -> dict[str, Any]:
        """One check. `only` narrows it to a single test file when that can be done honestly."""
        if not self.usable:
            return {"ok": False, "stage": "shut", "why": self.why or "lab shut"}
        if self.runs >= MAX_RUNS:
            return {"ok": False, "stage": "cap", "why": f"this task has already run {MAX_RUNS} checks - that is the limit"}
        cmd = ""
        note = ""
        if only:
            from ..devlab import spec as SP
            cmd = SP.one_file(self.cmd, self.ws["spec"].get("lang", ""), only)
            if not cmd:
                note = (f"[{only} cannot run alone with this command - ran the full check: {self.cmd}]\n")
        self.runs += 1
        res = self.LS.run_on(self.ws, cmd, overlay or {}, label=label or f"run{self.runs}")
        res["note"] = note
        self.last = res
        return res

    def grep(self, pattern: str) -> str:
        from ..devlab import out as O
        log_path = str((self.last or {}).get("log") or self.ws.get("last_log") or "")
        if not log_path:
            return "Run run_check first - after that you can search its log."
        return O.grep_log(log_path, pattern)

    def close(self) -> None:
        try:
            self.LS.close_workspace(self.ws)
        except Exception:  # noqa: BLE001 - closing a temp folder must never break a task
            log.info("lab close failed for %s", self.task)

    # ------------------------------------------------------------ the local proof of a bug (v0.447, measured here)
    def proof(self, changes: list[dict[str, Any]], tests: list[str]) -> dict[str, Any]:
        """Red-then-green, locally, in seconds: the TEST files alone on the unfixed code (must FAIL - that is the
        proof the bug is real), then the whole change (must PASS). Returns the verdict with both outputs as evidence.
        `{}` = could not be measured here, and the caller falls back to the CI proof (v0.447)."""
        if not self.usable or not tests or len(tests) >= len(changes):
            return {}
        test_only = {c["path"]: c["new"] for c in changes if c["path"] in tests}
        full = {c["path"]: c["new"] for c in changes}
        red = self.run(test_only, label="proof-red")
        if red.get("stage") in ("box", "setup", "command", "shut", "cap"):
            return {}
        green = self.run(full, label="proof-green")
        if green.get("stage") in ("box", "setup", "command", "shut", "cap"):
            return {}
        if red.get("ok") and green.get("ok"):
            state = "not_proven_local"          # the test passes without the fix: it proves nothing
        elif not red.get("ok") and green.get("ok"):
            state = "proven_local"              # red without the fix, green with it
        elif not red.get("ok") and not green.get("ok"):
            state = "still_failing"             # the fix does not make her check pass
        else:
            state = "odd"                       # passed without the fix and fails with it
        return {"state": state, "cmd": self.cmd, "source": self.source,
                "red": {"ok": red.get("ok"), "seconds": red.get("seconds"), "log": red.get("log"),
                        "tail": (red.get("shown") or "")[-1500:]},
                "green": {"ok": green.get("ok"), "seconds": green.get("seconds"), "log": green.get("log"),
                          "tail": (green.get("shown") or "")[-1500:]}}

    def done_when(self, lines: list[str], overlay: dict[str, str], cap: int = 2) -> list[dict[str, Any]]:
        """v0.451's plan said how anyone could check the work. Where a line IS a runnable command, run it instead of
        taking its word (ECC's verification-loop: report VERIFIED or FAILED with its evidence, else NOT PERFORMED)."""
        from ..devlab import spec as SP
        out: list[dict[str, Any]] = []
        for line in (lines or []):
            if len(out) >= cap:
                break
            c = SP._clean(str(line))
            if not c or SP.refuse_reason(c) or not SP._CMDISH.match(c):
                out.append({"line": str(line)[:200], "verdict": "not performed", "why": "this is not a command "
                            "that can be run"})
                continue
            r = self.run(overlay, label="done_when")
            if r.get("stage") in ("box", "setup", "command", "shut", "cap"):
                out.append({"line": c, "verdict": "not performed", "why": r.get("why", "")})
                continue
            res = self.LS.run_on(self.ws, c, {}, label="done_when") if c != self.cmd else r
            out.append({"line": c, "verdict": "VERIFIED" if res.get("ok") else "FAILED",
                        "seconds": res.get("seconds"), "log": res.get("log"),
                        "tail": (res.get("shown") or "")[-800:]})
        return out


def for_task(tenant: str, t: Any, token: str, hers: dict[str, str] | None = None, ref: str = "") -> Lab | None:
    """A Lab for this task, or None with the reason already logged. Never raises: a task must survive a shut lab."""
    r = ready(tenant)
    if not r["ok"]:
        log.info("lab shut for %s: %s", getattr(t, "number", "?"), r["why"])
        return None
    try:
        lab = Lab(tenant, t, token, hers, ref)
    except Exception as e:  # noqa: BLE001
        log.info("lab could not open for %s: %s", getattr(t, "number", "?"), e)
        return None
    if not lab.ws.get("ok"):
        log.info("lab shut for %s: %s", getattr(t, "number", "?"), lab.why)
        lab.close()
        return None
    return lab
