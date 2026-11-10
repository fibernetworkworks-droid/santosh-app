"""KAAN W6 limits: quota counters + retention - the accountability layer her audio runs on.

Two honest dials, both default OFF (her box keeps everything forever until she says otherwise):
- kaan_quota_audio_min: a per-tenant monthly audio-minutes cap. The meter counts the duration_s
  of FINISHED transcriptions (kn_ rows, file + live alike) inside the calendar month; a file is
  estimated with ffprobe BEFORE the engine runs, so the cap bites before the spend, not after.
- kaan_retention_days: transcripts older than N days are swept (pinned rows survive), and the
  live-caption spine files go with their sessions. The sweep rides the worker's daily tick.

These two dials are also the unlock for voiceprint diarization (voiceprint.py): speaker
voiceprints are biometric, so matching audio against them is only allowed on a tenant that has
bounded retention. Every refusal is one honest English line (owner instruction for W5+ strings).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select

from ..db import now, session
from .models import KaanLiveSession, KaanTranscript

_last_sweep: dict[str, Any] = {"ran": False, "ts": ""}


def _settings():
    from ..config import get_settings
    return get_settings()


def month_start():
    """The calendar-month window the quota counts inside (server time)."""
    t = now()
    return t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def month_usage(tenant: str) -> dict[str, Any]:
    """The per-tenant meter: finished audio minutes this month (kn_ rows only - a live session's
    seconds are counted ONCE, by the kn_ row its stop writes, never by the in-flight session)."""
    cap = int(_settings().kaan_quota_audio_min or 0)
    ms = month_start()
    with session() as s:
        total = s.scalar(select(func.coalesce(func.sum(KaanTranscript.duration_s), 0.0)).where(
            KaanTranscript.tenant_id == tenant, KaanTranscript.created_at >= ms)) or 0.0
    used_min = round(float(total) / 60.0, 2)
    out: dict[str, Any] = {"month": f"{ms.year}-{ms.month:02d}", "audio_min_used": used_min,
                           "quota_min": cap, "unlimited": cap <= 0}
    out["remaining_min"] = None if cap <= 0 else max(0.0, round(cap - used_min, 2))
    return out


def check_quota_file(tenant: str, duration_s: float) -> None:
    """Before the engine runs: the file's ffprobe estimate must fit under the monthly cap.
    duration 0.0 (ffprobe absent) never blocks - the finished row still counts honestly after."""
    cap = int(_settings().kaan_quota_audio_min or 0)
    if cap <= 0 or duration_s <= 0:
        return
    u = month_usage(tenant)
    if u["audio_min_used"] + duration_s / 60.0 > cap:
        raise ValueError(
            f"Audio quota: this tenant has used {u['audio_min_used']} of {cap} min this month; "
            f"this file is about {duration_s / 60.0:.1f} min, which would cross the cap. "
            "Raise KAAN_QUOTA_AUDIO_MIN, or wait - the counter resets on the 1st.")


def check_quota_live_start(tenant: str) -> None:
    """A new live session starts only under the cap (its own seconds are counted at stop)."""
    cap = int(_settings().kaan_quota_audio_min or 0)
    if cap <= 0:
        return
    u = month_usage(tenant)
    if u["audio_min_used"] >= cap:
        raise ValueError(
            f"Audio quota: this tenant has used {u['audio_min_used']} of {cap} min this month - "
            "no new live session until the counter resets on the 1st (raise KAAN_QUOTA_AUDIO_MIN if needed).")


def usage_block(tenant: str) -> dict[str, Any]:
    u = month_usage(tenant)
    u["note"] = ("W6 quota: finished audio minutes this calendar month, per tenant; a file is "
                 "estimated with ffprobe BEFORE the engine runs. 0 = no cap (default). "
                 "The counter resets on the 1st.")
    return u


# ---------------------------------------------------------------- retention
def retention_sweep() -> dict[str, Any]:
    """The daily sweep: kn_ transcripts older than kaan_retention_days go (pinned survive);
    live sessions past the same cutoff go with their spine PCM files. 0 = keep forever."""
    global _last_sweep
    days = int(_settings().kaan_retention_days or 0)
    if days <= 0:
        out = {"ran": False, "days": 0, "removed_transcripts": 0, "removed_live_sessions": 0,
               "spine_files_removed": 0, "reason": "KAAN_RETENTION_DAYS is 0 - nothing expires (default: keep forever)."}
        _last_sweep = {"ran": False, "ts": now().isoformat()}
        return out
    cutoff = now() - timedelta(days=days)
    removed_files = 0
    with session() as s:
        old_sess = s.scalars(select(KaanLiveSession).where(KaanLiveSession.created_at < cutoff)).all()
        for r in old_sess:
            if r.pcm_path:
                from pathlib import Path
                try:
                    Path(r.pcm_path).unlink(missing_ok=True)
                    removed_files += 1
                except OSError:
                    pass
            s.delete(r)
        n_sess = len(old_sess)
        old_rows = s.scalars(select(KaanTranscript).where(
            KaanTranscript.created_at < cutoff, KaanTranscript.pinned == False)).all()  # noqa: E712
        n_rows = len(old_rows)
        for r in old_rows:
            s.delete(r)
        s.commit()
    out = {"ran": True, "days": days, "removed_transcripts": n_rows, "removed_live_sessions": n_sess,
           "spine_files_removed": removed_files,
           "note": f"retention sweep: rows older than {days} day(s) removed (pinned rows survive)."}
    _last_sweep = {"ran": True, "ts": now().isoformat(), "removed_transcripts": n_rows,
                   "removed_live_sessions": n_sess}
    return out


def retention_block() -> dict[str, Any]:
    days = int(_settings().kaan_retention_days or 0)
    return {"days": days, "last_sweep": dict(_last_sweep),
            "note": ("W6 retention: transcripts older than KAAN_RETENTION_DAYS are swept daily by the "
                     "worker (pinned rows survive; live spine files go with their sessions). "
                     "0 = keep forever (default).")}


def voiceprint_ready(tenant: str) -> tuple[bool, str]:
    """The W6 unlock guard: voiceprint matching is biometric, so it runs only when the owner
    flipped KAAN_VOICEPRINT AND retention is bounded - audio matched with voiceprints expires."""
    st = _settings()
    if not bool(st.kaan_voiceprint):
        return False, ("Voiceprint diarization is off - owner has not set KAAN_VOICEPRINT=1. "
                       "Voiceprints are biometric; the switch is the owner's, not the tenant's.")
    if int(st.kaan_retention_days or 0) <= 0:
        return False, ("Voiceprint diarization needs bounded retention first - set KAAN_RETENTION_DAYS "
                       "(audio matched with enrolled voiceprints must have an expiry).")
    from ..voiceid import engine as VE
    if not VE.available():                    # the voiceid lane's REAL contract: a plain bool
        return False, ("The voiceprint engine is not ready on this machine - sherpa_onnx or the "
                       "CAM++/TitaNet speaker models in voiceid_models_dir are missing.")
    from ..voiceid import service as VS
    if not VS.call_people(tenant):
        return False, ("No enrolled voiceprints for this tenant yet - finish one Awaaz Pehchaan "
                       "enrolment first, then transcribe with diarize=voiceprint.")
    return True, ""
