"""P0 sources (plan 8.2 + the feed table). Every network read goes through `_get` / `_page_text` - tests replace them.

Allowed by their terms (16 Nov 2026): the LMArena dataset (CC-BY-4.0, via Hugging Face's public dataset server - no
library, plain JSON), OpenRouter's public models API (their terms bar scraping the site; the API is the route), the
voiceofindia.ai boards (no download offered - one browser read a month). Artificial Analysis is NOT read (its site
licence is personal / non-commercial; plan 8.2).
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any

log = logging.getLogger("santosh.pipeline")

DS = "https://datasets-server.huggingface.co"
DATASET = "lmarena-ai/leaderboard-dataset"
OR_MODELS = "https://openrouter.ai/api/v1/models?output_modalities=all"
VOI = "https://voiceofindia.ai/leaderboards"


def _get(url: str, timeout: float = 40.0) -> Any:
    import httpx
    r = httpx.get(url, timeout=timeout, headers={"User-Agent": "Hoola-pipeline-feed/1.0"})
    r.raise_for_status()
    return r.json()


_CONFIG: dict[str, list[dict]] = {}


def config_rows(config: str, page: int = 100, max_rows: int = 20000) -> list[dict]:
    """Every row of one LMArena board (latest split), paged through the public /rows endpoint (no key, no library).
    Kept for the run, so a board read for several categories is fetched once."""
    if config in _CONFIG:
        return _CONFIG[config]
    rows: list[dict] = []
    off = 0
    while off < max_rows:
        last: Exception | None = None
        for _ in range(3):                       # the dataset server has short hiccups; three tries per page
            try:
                d = _get(f"{DS}/rows?dataset={urllib.parse.quote(DATASET)}&config={config}&split=latest"
                         f"&offset={off}&length={page}")
                break
            except Exception as e:   # noqa: BLE001
                last = e
        else:
            raise last or RuntimeError("rows not read")
        got = [r.get("row") or {} for r in (d.get("rows") or [])]
        rows += got
        total = int(d.get("num_rows_total") or 0)
        off += page
        if not got or off >= total:
            break
    _CONFIG[config] = rows
    return rows


def board(config: str, category: str) -> list[dict]:
    """One LMArena board, one category -> rows (model_name, rating | score + rank, vote_count, publish date)."""
    return [r for r in config_rows(config) if str(r.get("category") or "overall") == category]


def reset() -> None:
    _CONFIG.clear()


def openrouter() -> list[dict]:
    d = _get(OR_MODELS)
    return list((d or {}).get("data") or [])


def _page_text(url: str, click: str = "") -> str:
    """The rendered text of a page that draws its table with JavaScript (headless Chromium, as the server already has)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        try:
            from ..docstudio.htmlpdf import _launch_kw      # the same Chromium Hoola's PDF maker uses (HOOLA_CHROMIUM)
            kw = _launch_kw()
        except Exception:   # noqa: BLE001
            kw = {}
        b = pw.chromium.launch(**kw)
        try:
            p = b.new_page()
            p.goto(url, wait_until="networkidle", timeout=60000)
            p.wait_for_timeout(2000)
            if click:
                p.evaluate("""(t) => { const el=[...document.querySelectorAll('*')].find(e=>e.childElementCount===0
                    && e.textContent.trim()===t); if (el) (el.closest('button,a,[role=tab]')||el).click(); }""", click)
                p.wait_for_timeout(4000)
            return p.evaluate("() => document.body.innerText")
        finally:
            b.close()


_NUM = re.compile(r"^[\d,]+$")


def parse_voi_tts(text: str) -> list[dict]:
    """voiceofindia text-to-speech board text -> [{name, org, elo, votes}] in board order. Pure.

    A row reads: rank, '⇄a-b', name, 'Org · Licence' (licence can be missing), '1,119', '±16', '56%<tab>834'."""
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    out = []
    for i in range(1, len(lines) - 4):
        if not (lines[i - 1].startswith("⇄") and _NUM.match(lines[i + 2]) and lines[i + 3].startswith("±")):
            continue
        m = re.search(r"([\d,]+)\s*$", lines[i + 4].split("%")[-1])
        out.append({"name": lines[i], "org": lines[i + 1].split(" · ")[0], "elo": int(lines[i + 2].replace(",", "")),
                    "votes": int(m.group(1).replace(",", "")) if m else 0})
    return out


_STT = re.compile(r"^(\d+)$")


def parse_voi_stt(text: str) -> list[dict]:
    """voiceofindia speech-to-text board text -> [{name, org, wer}] (OI-WER %, lower = better), board order. Pure."""
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    out, seen = [], set()
    for i in range(len(lines) - 3):
        if _STT.match(lines[i]) and " · " in lines[i + 2]:
            m = re.match(r"^([\d.]+)%$", lines[i + 3])
            if m and lines[i + 1] not in seen:
                seen.add(lines[i + 1])
                out.append({"name": lines[i + 1], "org": lines[i + 2].split(" · ")[0], "wer": float(m.group(1))})
    return out


def voi_tts() -> list[dict]:
    return parse_voi_tts(_page_text(VOI))


def voi_stt() -> list[dict]:
    return parse_voi_stt(_page_text(VOI, click="Speech-to-Text"))
