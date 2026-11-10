"""v0.311 AAGE BADHO - a reply that only PROMISES more work never ends the job.

The RCA (docs/LONG_TASK_RCA.md, reproduced on the real run_turn): after a silent tool round the v0.258 narrate ask
says "say one short line". A model that answers with ONLY that line ("Status mein 3 kaam mile. Ab doosra hissa dekh
raha hoon.") returns end_turn, and with no kaam_plan open the loop took the line as the final answer - she read
"dekh raha hoon" and nothing ever happened. Claude never stops on such a line: its progress text rides in the same
message as the next tool call, and the turn ends only when no tool is called AND the work is done.

`promised(text)` reads the LAST sentence of a text-only reply: future / ongoing work announced by Hoola ("...kar
raha hoon", "ab ... dekhta hoon", "next I'll", "let me") = the job is not over. A line that waits on HER (a question,
a card to tap, an OTP) is never a promise - that turn really must stop. The caller sends one continue nudge, at most
MAX_PER_TURN times, so a model that keeps promising cannot loop."""
from __future__ import annotations

import re

MAX_PER_TURN = 2
STATS: dict[str, int] = {"nudged": 0}

# Hoola announcing ITS OWN next / ongoing work (Hinglish, English, Devanagari)
_PROMISE = re.compile(
    r"\b(?:raha|rahi)\s+(?:hoon|hun|hu)\b"                                         # dekh raha hoon / bana rahi hun (first person only)
    r"|\b(?:karta|karti|dekhta|dekhti|nikalta|nikalti|banata|banati|likhta|likhti|bhejta|bhejti|padhta|padhti|"
    r"dhoondhta|dhoondhti|dhundhta|dhundhti|laata|laati|lata|lati|chalata|chalati|kholta|kholti|jodta|jodti|"
    r"badhta|badhti|shuru\s+karta|shuru\s+karti)\s+(?:hoon|hun|hu)\b"                   # ab dekhta hoon
    r"|\b(?:karunga|karungi|dekhunga|dekhungi|nikalunga|nikalungi|banaunga|banaungi|likhunga|likhungi|"
    r"bhejunga|bhejungi|laaunga|laaungi|chalaunga|chalaungi)\b"                          # karunga / dekhungi
    r"|\b(?:i'?ll|i\s+will|let\s+me|i'?m\s+(?:now\s+)?(?:going\s+to|checking|looking|fetching|building|writing|"
    r"searching|opening|reading|creating|making|pulling|running)|next,?\s+i|now\s+i'?m|now\s+i\s+will)\b"
    r"|(?:रहा|रही)\s+(?:हूँ|हूं)|(?:करता|करती|देखता|देखती)\s+(?:हूँ|हूं)|(?:करूँगा|करूंगा|करूँगी|करूंगी)",
    re.I)

# v0.727 the same promise with no "I": "Now starting one fresh, simple demo-only build." / "Starting the build now." /
# "Rebuilding it now." - her NetMitra chat ended twice on such a line with no build ever started (no card, no work)
_PROMISE_LEAD = re.compile(
    r"^(?:(?:ok(?:ay)?|so|and|now|right|great|sure|theek\s+hai|ab|abhi),?\s+)*"
    r"(?:starting|building|rebuilding|creating|making|working\s+on|setting\s+up|launching|preparing|generating|"
    r"restarting|kicking\s+off|writing|drafting|fetching|pulling|running|opening|searching|looking\s+into|"
    r"moving\s+on\s+to|on\s+it)\b",
    re.I)

# the turn really waits on her: never pushed back to work
_WAITS_ON_HER = re.compile(
    r"\?|intezaar|intzaar|wait(?:ing)?\s+for\s+(?:you|your)|aap(?:ka|ke|ki)?\s+(?:jawab|haan|tap|otp|reply)|"
    r"\bcard\b|\btap\b|\bhaan\s+(?:karein|kijiye|boliye|likhiye)|\botp\b|\bpassword\b|bataiye|batayein|"
    r"aap\s+(?:kahein|kahen|bolein|batayein)|\bconfirm\b|manzoori|इंतज़ार|बताइए|बताइये",
    re.I)

_SENT = re.compile(r"(?<=[.!।])\s+|\n+")


def promised(text: str) -> bool:
    """True when the reply's last sentence announces more of Hoola's own work and asks nothing of her."""
    t = " ".join(str(text or "").split())
    if not t:
        return False
    parts = [p for p in _SENT.split(t) if p.strip()]
    last = parts[-1] if parts else t
    if _WAITS_ON_HER.search(last):
        return False
    return bool(_PROMISE.search(last) or _PROMISE_LEAD.search(last.strip(" -–—*_")))


NUDGE = ("[System: you just wrote that you are continuing the work, but you made no tool call - this is how work stops "
         "here. Do what you said NOW with tools (put the next tool call in this same reply, beside your line). If "
         "everything is really done, give the final answer right away with no further promise: what happened, what was made.]")
