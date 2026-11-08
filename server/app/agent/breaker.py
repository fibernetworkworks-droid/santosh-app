"""Circuit breaker for one agent turn / one call / one customer chat (idea from Munder Difflin): an agent that loops is
first steered (a note instead of running the same call again), then constrained (a tool that keeps failing is taken
away for the rest of the turn), then stopped (too many failures in a row or too many calls), and the owner is told.

Enforced here, in code: the model cannot talk its way past it."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

SAME_CALL_STEER = 2        # the 3rd identical call (same tool + same input) is not run
TOOL_FAILS_CONSTRAIN = 3   # a tool that failed 3 times in this turn is taken away
FAILS_IN_ROW_STOP = 4      # 4 failed calls in a row: stop
MAX_CALLS = 48             # more tool calls than this in one turn: stop (v0.311: 30 -> 48, so the step-24 long-job
                           # switch is reached first; a parallel look-up batch counts once - see Breaker.batch)
NAME_STEER = 12           # v0.705 the 13th call of the SAME tool in one turn (inputs differing) is paused once
NAME_STOP = 30            # ... and the 31st stops the turn (her archive job looped 40 rounds, every input new)
FAILS_IN_ROW_GOAL = 7      # v0.186 goal mode: more patience before a hard stop (one replan rescue first)

STATS: Counter = Counter()   # steer / constrain / stop, since start (GET /api/agent/stats)


def _key(name: str, args: dict[str, Any] | None) -> str:
    try:
        return name + "|" + json.dumps(args or {}, sort_keys=True, default=str)[:2000]
    except Exception:
        return name + "|?"


class Breaker:
    def __init__(self, max_calls: int = MAX_CALLS, fails_in_row: int = FAILS_IN_ROW_STOP, rescue: bool = False):
        self.max_calls = max_calls
        self.fails_in_row = fails_in_row
        self.rescue = rescue          # v0.186 goal mode: the first stop becomes one replan rescue instead
        self.rescued = False
        self.rescue_note = ""        # the replan message for the model (read by the turn right after it trips)
        self.calls = 0
        self.same: Counter = Counter()
        self.names: Counter = Counter()
        self._bsize = 0
        self._bleft = 0              # v0.705 calls still to come from the current parallel batch (counted once by name)
        self.fails: Counter = Counter()
        self.in_row = 0
        self.blocked: set[str] = set()
        self.stopped = ""          # why the turn must stop ('' = go on)
        self.trips: list[str] = []

    def before(self, name: str, args: dict[str, Any] | None) -> str | None:
        """None = run it. A string = don't run; give this to the model as the tool's result."""
        if self.stopped:
            return self.stopped
        self.calls += 1
        if self.calls > self.max_calls:
            return self._stop(f"ek hi kaam mein {self.max_calls} se zyada kadam ho gaye")
        if name in self.blocked:
            self._trip("constrain")
            if self._insisting():
                return self.stopped
            return (f"{name} is baar baar fail ho raha hai, isliye is kaam mein ab nahi chalega. Koi aur tarika lo, ya "
                    "owner ko seedha batao kya atka.")
        if self._bleft > 0:
            first = self._bleft == self._bsize
            self._bleft -= 1
        else:
            first = True
        if first:
            self.names[name] += 1
        if first and self.names[name] > NAME_STOP:
            return self._stop(f"{name} ek hi kaam mein {NAME_STOP} se zyada baar chala")
        if first and self.names[name] == NAME_STEER + 1:
            self._trip("steer")
            return (f"{name} is kaam mein {NAME_STEER} baar chal chuka hai. Ruko aur dekho: kya har baar nateeja BADAL raha "
                    "hai? Agar wahi cheezein baar baar aa rahi hain to yeh loop hai - aur mat chalao, owner ko 1-2 line mein "
                    "batao kya hua. Agar har call sach mein naya kaam hai (alag log / alag cheez), to agli call chala sakte ho.")
        k = _key(name, args)
        self.same[k] += 1
        if self.same[k] > SAME_CALL_STEER:
            self._trip("steer")
            if self._insisting():
                return self.stopped
            return ("Yeh bilkul same kaam (same input ke saath) pehle ho chuka hai; dobara mat chalao. Jo nateeja mila "
                    "usi se aage badho, ya alag input / alag tarika lo, ya owner ko batao.")
        return None

    def batch(self, n: int) -> None:
        """v0.311 a parallel batch of n pure look-ups is ONE step of work: it costs one call against max_calls,
        not n. (RCA: a research job doing 4 searches a round, every call fine, was stopped at round 8 as 'atak
        gaya'.) Same-call steering and failure counting still see every single call."""
        if n > 1:
            self.calls -= n - 1
            self._bleft = self._bsize = n

    def after(self, name: str, ok: bool) -> None:
        if ok:
            self.in_row = 0
            return
        self.in_row += 1
        self.fails[name] += 1
        if self.fails[name] >= TOOL_FAILS_CONSTRAIN and name not in self.blocked:
            self.blocked.add(name)
            self._trip("constrain")
        if self.in_row >= self.fails_in_row and not self._rescue_or_stop(name):
            self._stop(f"{self.in_row} kaam lagatar fail hue")

    def _rescue_or_stop(self, name: str) -> bool:
        """v0.186 goal mode: the FIRST trip of the in-a-row cap is one replan rescue, not a stop: the failing tool
        is taken away and the model is told to search + read docs and pick a different route. Only the second trip
        really stops. True when a rescue was given (the turn goes on)."""
        if not (self.rescue and not self.rescued and not self.stopped):
            return False
        self.rescued = True
        self.in_row = 0
        if name:
            self.blocked.add(name)
        self.rescue_note = (f"[replan: {name or 'yeh raasta'} lagatar fail ho gaya; is tool ke bina kaam karo. "
                            "google_search/web_sources se dekho yeh kaam hota kaise hai, docs padho (open_website) "
                            "aur doosra tool ya doosra route chuno. Jo ho chuka woh batao, phir naye raaste se aage badho.]")
        self._trip("rescue")
        return True

    def _insisting(self) -> bool:
        """A refused call counts as one more failure in a row: insisting on a blocked path ends the turn."""
        self.in_row += 1
        if self.in_row >= self.fails_in_row and not self._rescue_or_stop(""):
            self._stop("baar baar wahi atka hua kaam")
            return True
        return False

    def _trip(self, kind: str) -> None:
        STATS[kind] += 1
        self.trips.append(kind)

    def _stop(self, why: str) -> str:
        if not self.stopped:
            self._trip("stop")
            self.stopped = f"Ruko: {why}. Ab aur koi tool mat chalao; owner ko 1-2 line mein batao kya hua aur kahan atka."
        return self.stopped

    def final_text(self) -> str:
        return ("Main ek jagah atak gaya tha, isliye maine yeh kaam rok diya. Thoda aur bataiye ya alag tarike se kahiye, "
                "main phir koshish karta hoon.")
