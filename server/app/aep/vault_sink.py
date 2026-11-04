"""HOOLA AEP run persistence - the vault sink (v0.521.0 HOOLA TRACE).

The tracers module is pure library code; THIS is where the flag law lives. A finished
run lands as an ordinary vault observation typed 'aep_run' (the docs7 law: no new
tables, the machinery that searches/consolidates her memory sees the rows too).

Laws carried over from docs7:
  flag default OFF     - aep_trace gates every write (and the /api/aep/runs explorer).
                         Bake on the VPS, then flip via the reviewed trace_flip job.
  redaction before storage - run IO can carry her words: strip_private + redact_secrets
                         run over the serialized row BEFORE it lands. aep_trace_redact
                         exists for the tests; production keeps it True.
  fail-closed          - every failure returns/leaves a clean None, never an exception
                         out of the sink. Telemetry never breaks the run it watches.
  one write per run    - finished runs only; a run is saved once (the snapshot copy).
"""
from __future__ import annotations

import json
import threading

# honest counters the agent stats block prints
STATS = {"saved": 0, "skipped_flag": 0, "skipped_error": 0}
_STATS_LOCK = threading.Lock()


def _settings():
    try:
        from ..config import get_settings
        return get_settings()
    except Exception:
        return None


def trace_enabled() -> bool:
    st = _settings()
    return bool(getattr(st, "aep_trace", False))


def _redact(text: str) -> str:
    st = _settings()
    if getattr(st, "aep_trace_redact", True):
        try:
            from ..coder.redact import redact_secrets, strip_private
            text = redact_secrets(strip_private(text))
        except Exception:  # noqa: BLE001 - redaction must never be the thing that breaks
            pass
    return text


def _row(run) -> dict:
    """The observation-shaped row for one finished run (redacted before it leaves)."""
    d = run.to_dict()
    narrative = _redact(json.dumps(d, default=str, ensure_ascii=False))[:8000]
    status = d.get("status", "ok")
    return {
        "type": "aep_run",
        "title": f"Run {run.name} ({run.run_type}) - {status}",
        "subtitle": f"{run.ms} ms, {status}" + (f": {str(run.error)[:120]}" if run.error else ""),
        "narrative": narrative,
        "facts": [f"run_type:{run.run_type}", f"name:{run.name}", f"status:{status}",
                  f"ms:{run.ms}", f"trace:{run.trace_id[:12]}"],
        "concepts": [run.run_type, run.name],
        "files_read": [],
        "files_modified": [],
    }


class VaultRunSink:
    """Runs -> vault observations typed 'aep_run'. Flag OFF = a silent no-op sink."""

    def __init__(self, tenant: str = "", conv: str = "") -> None:
        self.tenant = tenant or "-"
        self.conv = conv or ""

    def save(self, run) -> int | None:
        if not trace_enabled():
            with _STATS_LOCK:
                STATS["skipped_flag"] += 1
            return None
        try:
            from ..coder import store
            store.ensure()
            obs_id = store.store_observation(self.conv, self.tenant, _row(run),
                                             actor="aep_trace")
            with _STATS_LOCK:
                STATS["saved"] += 1
            return obs_id
        except Exception:  # noqa: BLE001 - fail-closed, the run itself never knows
            with _STATS_LOCK:
                STATS["skipped_error"] += 1
            return None


def vault_sink_for(tenant: str = "", conv: str = "") -> VaultRunSink:
    return VaultRunSink(tenant=tenant, conv=conv)


def attach_vault_sink(tracer, tenant: str = "", conv: str = "") -> None:
    """Wire the flag-gated vault sink into a tree tracer (idempotent per tenant)."""
    for s in tracer.sinks:
        if isinstance(s, VaultRunSink) and s.tenant == (tenant or "-"):
            return
    tracer.sinks.append(vault_sink_for(tenant, conv))


def vault_runs(tenant: str, limit: int = 20) -> list[dict]:
    """The persisted side of the explorer: recent 'aep_run' observations for a tenant."""
    from ..coder import store
    store.ensure()
    with store.db() as c:
        rows = c.execute(
            "SELECT id, title, subtitle, narrative, facts, created_at FROM observations "
            "WHERE tenant=? AND type='aep_run' AND superseded_by=0 "
            "ORDER BY id DESC LIMIT ?", (tenant, max(1, min(int(limit), 200)))).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["facts"] = json.loads(d.get("facts") or "[]")
        except Exception:  # noqa: BLE001
            d["facts"] = []
        d["narrative"] = d.get("narrative") or ""
        out.append(d)
    return out


def vault_run_by_id(tenant: str, obs_id: int) -> dict | None:
    from ..coder import store
    store.ensure()
    with store.db() as c:
        row = c.execute(
            "SELECT id, title, subtitle, narrative, facts, created_at FROM observations "
            "WHERE tenant=? AND id=? AND type='aep_run'", (tenant, obs_id)).fetchone()
    if row is None:
        return None
    d = dict(row)
    try:
        d["facts"] = json.loads(d.get("facts") or "[]")
    except Exception:  # noqa: BLE001
        d["facts"] = []
    return d
