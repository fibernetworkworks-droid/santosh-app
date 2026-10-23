"""Gyaan chunking: boring on purpose (research: fixed-size chunks split on structure beat "semantic" chunking).

- documents: headings and paragraphs, ~1,100 characters a chunk (max 1,600), the last sentence carried into the next one
- sheets / tables: rows, the header line repeated at the top of every chunk so a row is never read without its columns
- emails: one chunk, quoted older replies removed
- every chunk gets a deterministic prefix (title, kind, date) that is indexed with it (free "contextual" retrieval)"""
from __future__ import annotations

import re
from typing import Any

TARGET = 1100
MAX = 1600
OVERLAP = 220

_HEAD = re.compile(r"^(#{1,6}\s+.+|[A-Zऀ-ॿ][^.!?।\n]{2,70}:)\s*$")
_SENT = re.compile(r"(?<=[.!?।])\s+|\n")


def _sentences(p: str) -> list[str]:
    parts = [s.strip() for s in _SENT.split(p) if s and s.strip()]
    out: list[str] = []
    for s in parts:
        while len(s) > MAX:                      # a "sentence" with no stop (a table cell dump, OCR): hard cut at a space
            cut = s.rfind(" ", 0, TARGET) or TARGET
            out.append(s[:cut].strip())
            s = s[cut:].strip()
        if s:
            out.append(s)
    return out


def _is_table(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False
    piped = sum(1 for ln in lines if ln.count("|") >= 2)
    comma = sum(1 for ln in lines if ln.count(",") >= 2 or ln.count("\t") >= 2)
    return piped >= len(lines) * 0.6 or comma >= len(lines) * 0.7


def _table_chunks(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() and not re.fullmatch(r"[\s|:\-+]+", ln)]
    if not lines:
        return []
    head, rows = lines[0], lines[1:]
    out: list[str] = []
    cur: list[str] = []
    size = len(head)
    for r in rows:
        if cur and size + len(r) > TARGET:
            out.append("\n".join([head] + cur))
            cur, size = [], len(head)
        cur.append(r)
        size += len(r) + 1
    if cur:
        out.append("\n".join([head] + cur))
    return out


def strip_quoted(mail: str) -> str:
    """Drop quoted older replies from an email body ("> ..." lines and everything after "On ... wrote:")."""
    keep: list[str] = []
    for i, ln in enumerate((mail or "").splitlines()):
        if i >= 4 and re.match(r"^\s*(On .{6,120} wrote:|-{2,}\s*Original Message|From: .+@.+|\d{1,2}/\d{1,2}/\d{2,4}.* ने लिखा:)", ln):
            break
        if ln.lstrip().startswith(">"):
            continue
        keep.append(ln)
    return "\n".join(keep).strip()


def split(text: str, kind: str = "doc") -> list[dict[str, Any]]:
    """-> [{text, page}] (page from form-feed page breaks, else 0)."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if kind == "mail":
        text = strip_quoted(text)
    pages = text.split("\f") if "\f" in text else [text]
    out: list[dict[str, Any]] = []
    for pno, page in enumerate(pages, start=1 if len(pages) > 1 else 0):
        page = re.sub(r"[ \t]+", " ", page).strip()
        if not page:
            continue
        if kind in ("sheet", "table") or _is_table(page):
            out += [{"text": c, "page": pno} for c in _table_chunks(page)]
            continue
        if kind == "mail" and len(page) <= MAX:
            out.append({"text": page, "page": pno})
            continue
        paras = [p.strip() for p in re.split(r"\n\s*\n", page) if p.strip()]
        cur: list[str] = []
        size = 0

        def flush() -> None:
            nonlocal cur, size
            if cur:
                out.append({"text": " ".join(cur).strip(), "page": pno})
                tail = cur[-1] if len(cur[-1]) <= OVERLAP else ""
                cur, size = ([tail] if tail else []), len(tail)
        for p in paras:
            first = p.split("\n", 1)[0]
            if _HEAD.match(first) and size > TARGET * 0.4:
                flush()
                cur, size = [], 0            # a heading starts clean (no carry-over across sections)
            for s in _sentences(p):
                if size + len(s) > TARGET and size > 0:
                    flush()
                cur.append(s)
                size += len(s) + 1
        if cur and not (len(cur) == 1 and out and cur[0] in out[-1]["text"]):
            out.append({"text": " ".join(cur).strip(), "page": pno})
    return [c for c in out if len(c["text"]) >= 2]


def prefix(title: str, kind: str, at: str = "", extra: str = "") -> str:
    bits = [b for b in (title.strip()[:120] if title else "", kind, (at or "")[:10], extra[:80]) if b]
    return "[" + " · ".join(bits) + "]" if bits else ""
