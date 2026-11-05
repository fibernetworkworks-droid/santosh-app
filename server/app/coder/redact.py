"""HOOLA CODER redaction - secrets never reach the memory (v0.473.0).

Two layers, both ALWAYS ON (claude-mem makes secret redaction opt-in; the Hoola golden rule is
stricter: secrets never cross the wire, and a memory file is a wire):

  strip_private(text)   balanced <private>...</private> blocks (plus the house noise tags) are
                        removed at every capture boundary. A prompt that is empty after the strip
                        marks the whole turn private - nothing from it is stored.
  redact_secrets(text)  ~20 patterns (cloud keys, tokens, JWTs, PEM blocks, labeled secrets like
                        `password=`, `otp: 4821`) are masked BEFORE anything is spooled, shown to
                        the observer, or written to a row. Labels survive, values never do.

Every capture path funnels through capture.py, which calls both - there is no unredacted path.
"""
from __future__ import annotations

import re

_TAGS = ("private", "claude-mem-context", "system-reminder", "system_instruction", "system-instruction",
         "persisted-output")


def strip_private(text: str) -> str:
    """Remove balanced <tag>...</tag> blocks for the noise/privacy tags. Linear, no regex cleverness:
    a scanner that walks the string once and never nests wrong."""
    if not text:
        return ""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        lt = text.find("<", i)
        if lt < 0:
            out.append(text[i:])
            break
        out.append(text[i:lt])
        m = re.match(r"</?\s*([a-zA-Z][\w-]*)\s*[^<>]*?/?>", text[lt:])
        if not m:
            out.append("<")
            i = lt + 1
            continue
        name = m.group(1).lower()
        closing = m.group(0).startswith("</")
        selfclose = m.group(0).endswith("/>")
        end = lt + m.end()
        if name in _TAGS and not closing:
            if selfclose:
                i = end                      # nothing to skip
            else:
                close_re = re.compile(rf"</\s*{re.escape(name)}\s*>", re.IGNORECASE)
                cm = close_re.search(text, end)
                i = cm.end() if cm else n    # unbalanced block: drop to the end, never leak
            continue
        out.append(m.group(0))
        i = end
    return "".join(out)


# --- secret patterns: label kept, value masked ----------------------------------------------

# whole-match masks: the match IS the secret (a key, a token, a PEM block)
_WHOLE: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret", re.compile(r"(?i)aws.{0,20}?['\"]?[a-zA-Z0-9/+=]{40}['\"]?")),
    ("github_pat", re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}\b")),
    ("pem_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
]
# labeled masks: group 1 = the label kept visible, the value after it is masked
_LABELED: list[tuple[str, re.Pattern[str]]] = [
    ("bearer", re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer|token)\s+)[A-Za-z0-9._-]{8,}")),
    ("password", re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key|auth[_-]?token)"
                            r"((?:\s*[:=]\s*)|\s+)[^\s,;&'\"]{4,}")),
    ("otp_like", re.compile(r"(?i)\b(otp|one[- ]?time (?:code|password)|pin)\b(\s*(?:is|:|=)?\s*)[0-9]{4,8}\b")),
]

_MASK = "***redacted***"


def redact_secrets(text: str) -> str:
    if not text:
        return ""
    t = text
    for _name, pat in _WHOLE:
        t = pat.sub(_MASK, t)
    for _name, pat in _LABELED:
        t = pat.sub(lambda m: (m.group(1) + (m.group(2) if m.lastindex and m.lastindex > 1 else "")) + _MASK, t)
    return t


def redact(obj) -> object:
    """Redact every JSON string inside a payload (args / results), recursively, depth-capped."""
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, dict):
        return {k: redact(v) for k, v in list(obj.items())[:64]}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in list(obj)[:64]]
    return obj
