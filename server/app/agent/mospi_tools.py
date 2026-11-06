"""v0.348 MOSPI BUILT IN: `mospi` = official Government of India statistics (MoSPI eSankhyiki MCP, app/mospi.py).
Built in for every user, no Connect tap. Read-only. Numbers come from MoSPI's own data, never from a search summary."""
from __future__ import annotations

import json

from .. import mospi as ms
from ..config import get_settings
from .tools import Ctx, ToolError

MOSPI_TOOLS = [
    {"name": "mospi", "description": (
        "Official Government of India statistics straight from MoSPI (eSankhyiki): CPI retail inflation (mehngai), WPI, "
        "IIP industrial output, GDP / GVA (NAS), PLFS jobs and unemployment, ASI factories, HCES household spending, NFHS "
        "health, AISHE / UDISE education, energy, gender, RBI series and NSS surveys - by state, sector, year, month. Use it "
        "for ANY Indian official number instead of google_search. Four steps, each needs the one before: action=datasets "
        "-> action=indicators dataset=CPI -> action=metadata (dataset, indicator_code or base_year: gives the valid filter "
        "codes) -> action=data (dataset, filters from metadata, e.g. CPI: {base_year:'2024', series:'Current', year:'2026', "
        "state_code:'1', sector_code:'3'}). Filter codes are dataset-specific: never guess them, read metadata."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(ms.TOOLS)},
         "dataset": {"type": "string", "description": "CPI, WPI, IIP, ISP, NAS, PLFS, ASI, HCES, NFHS, AISHE, UDISE, ENERGY, GENDER, RBI, ASUSE, ENVSTATS, TUS, EC, MNRE, CPIALRL, NSS..."},
         "indicator_code": {"type": "integer", "description": "From action=indicators (not for CPI, IIP, ISP, ASI, WPI)"},
         "base_year": {"type": "string", "description": "CPI '2024' (latest) / '2012'; IIP '2011-12'; NAS '2022-23' / '2011-12'"},
         "frequency": {"type": "string", "description": "e.g. IIP 'Monthly' / 'Annually'"},
         "classification_year": {"type": "string"},
         "filters": {"type": "object", "additionalProperties": True, "description": "action=data only: codes from action=metadata"},
         "user_query": {"type": "string", "description": "Her question, as she asked it"}},
         "required": ["action"]}},
]

MOSPI_LABELS = {"mospi": "MoSPI ke sarkari aankde dekh raha hoon"}

MAX_CHARS = 14000


def _compact(out):
    """Rows without their empty fields; whole rows dropped from the end (never a cut in the middle of the JSON)."""
    if not isinstance(out, dict) or not isinstance(out.get("data"), list):
        text = json.dumps(out, ensure_ascii=False, default=str)
        return (out if len(text) <= MAX_CHARS else text[:MAX_CHARS]), 0
    rows = [{k: v for k, v in r.items() if v not in (None, "")} if isinstance(r, dict) else r for r in out["data"]]
    keep = {k: v for k, v in out.items() if k != "data"}
    n = len(rows)
    while rows and len(json.dumps({**keep, "data": rows}, ensure_ascii=False, default=str)) > MAX_CHARS:
        rows = rows[:max(1, int(len(rows) * 0.8))] if len(rows) > 1 else []
    return {**keep, "data": rows}, n - len(rows)


async def mospi(ctx: Ctx, action="", dataset="", indicator_code=None, base_year="", frequency="", classification_year="",
                filters=None, user_query="", **_):
    if not getattr(get_settings(), "mospi_enabled", True):
        raise ToolError("MoSPI statistics are off on this server (MOSPI_ENABLED).")
    try:
        out = await ms.call(action, dataset=str(dataset or "").strip().upper(), indicator_code=indicator_code,
                            base_year=base_year, frequency=frequency, classification_year=classification_year,
                            filters=filters if isinstance(filters, dict) else None, user_query=str(user_query or "")[:300])
    except ms.MospiError as e:
        raise ToolError(str(e))
    out, dropped = _compact(out)
    res = {"source": "MoSPI eSankhyiki (mospi.gov.in), official", "result": json.dumps(out, ensure_ascii=False, default=str)}
    if dropped:
        res["note_cut"] = (f"{dropped} more rows not shown: narrow the filters (state_code, sector_code, month_code, "
                           "division / group / item code, limit) and ask again.")
    if str(action).lower() == "data":
        res["note"] = ("These are MoSPI's own figures: quote the number with its month / year, state, sector and base year, "
                       "and say 'MoSPI' as the source. Provisional figures stay marked provisional. Do not add numbers "
                       "that are not in this result.")
    return res


MOSPI_HANDLERS = {"mospi": mospi}
