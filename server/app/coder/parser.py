"""HOOLA CODER parser - XML in, structured memory out (v0.473.0).

The observer answers in XML (or a skip sentinel, or prose when a cheaper model misbehaves). The
parser is tolerant on purpose: it extracts every <observation> block field-by-field, caps the
title at 120 chars, keeps only taxonomy-valid types/concepts, and - when the answer is prose with
no XML at all - salvages it into a single discovery observation marked schema_drift rather than
throwing the batch away. An answer with no salvageable content is a retry, then a drop.
"""
from __future__ import annotations

import re

_TITLE_MAX = 120
_OBS_RE = re.compile(r"<observation>([\s\S]*?)</observation>", re.IGNORECASE)
_SUMMARY_RE = re.compile(r"<summary>([\s\S]*?)</summary>", re.IGNORECASE)
_SKIP_RE = re.compile(r"<skip_summary\s+reason=\"([^\"]*)\"\s*/?>", re.IGNORECASE)
_FIELD_RE = {f: re.compile(rf"<{f}>([\s\S]*?)</{f}>", re.IGNORECASE)
             for f in ("type", "title", "subtitle", "narrative", "request", "investigated", "learned",
                       "completed", "next_steps", "notes")}
_LIST_RE = {"fact": re.compile(r"<fact>([\s\S]*?)</fact>", re.IGNORECASE),
            "concept": re.compile(r"<concept>([\s\S]*?)</concept>", re.IGNORECASE),
            "file": re.compile(r"<file>([\s\S]*?)</file>", re.IGNORECASE)}
_FILES_READ_RE = re.compile(r"<files_read>([\s\S]*?)</files_read>", re.IGNORECASE)
_FILES_MOD_RE = re.compile(r"<files_modified>([\s\S]*?)</files_modified>", re.IGNORECASE)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _field(block: str, name: str) -> str:
    m = _FIELD_RE[name].search(block)
    return _clean(m.group(1)) if m else ""


def _list(block: str, kind: str) -> list[str]:
    return [_clean(x) for x in _LIST_RE[kind].findall(block) if _clean(x)]


def _files(block: str, wrap_re) -> list[str]:
    m = wrap_re.search(block)
    return _list(m.group(1), "file") if m else []


class ParsedObservation(dict):
    """{type,title,subtitle,facts,narrative,concepts,files_read,files_modified,schema_drift}"""


def parse_observations(text: str, valid_types: set[str] | None = None,
                       valid_concepts: set[str] | None = None) -> list[ParsedObservation]:
    """Every well-formed <observation> block; invalid types fall back to 'discovery' (claude-mem's
    schema-drift rule: keep the fact, lose the bad label)."""
    out: list[ParsedObservation] = []
    for block in _OBS_RE.findall(text or ""):
        title = _field(block, "title")[:_TITLE_MAX]
        if not title:
            continue                                   # untitled = nobody's memory (store drops it too)
        typ = _field(block, "type").lower()
        if valid_types and typ not in valid_types:
            typ = "discovery" if "discovery" in (valid_types or {"discovery"}) else typ
        obs = ParsedObservation(
            type=typ or "discovery", title=title, subtitle=_field(block, "subtitle")[:300],
            facts=_list(block, "fact")[:16], narrative=_field(block, "narrative")[:8000],
            concepts=[c for c in _list(block, "concept")[:6]
                      if not valid_concepts or c in valid_concepts],
            files_read=_files(block, _FILES_READ_RE)[:32],
            files_modified=_files(block, _FILES_MOD_RE)[:32],
            schema_drift=False)
        out.append(obs)
    return out


def parse_summary(text: str) -> dict | None:
    m = _SUMMARY_RE.search(text or "")
    if not m:
        return None
    block = m.group(1)
    s = {k: _field(block, k) for k in ("request", "investigated", "learned", "completed", "next_steps",
                                       "notes")}
    return s if any(s.values()) else None


def parse_skip(text: str) -> str | None:
    m = _SKIP_RE.search(text or "")
    return m.group(1) if m else None


_JUNK_WORDS = {"ok", "okay", "done", "skip", "skipped", "skipping", "noise", "nothing", "observed",
               "observe", "to", "no", "the", "a", "an", "is"}


def salvage_prose(text: str) -> list[ParsedObservation]:
    """A cheap model sometimes answers in plain sentences. One durable sentence beats a dropped
    batch: the whole answer becomes one discovery observation, flagged schema_drift. Pure
    interjections ("ok done", "nothing observed") are junk, not memory."""
    t = (text or "").strip()
    if not t or parse_skip(t):
        return []
    if _OBS_RE.search(t) or _SUMMARY_RE.search(t):
        return []                                     # real XML handled elsewhere; not prose
    words = {w.strip(".,!?;:") for w in t.lower().split()}
    if words <= _JUNK_WORDS:
        return []
    title = t[:_TITLE_MAX]
    return [ParsedObservation(type="discovery", title=title, subtitle="",
                              facts=[], narrative=t[:8000], concepts=[], files_read=[],
                              files_modified=[], schema_drift=True)]
