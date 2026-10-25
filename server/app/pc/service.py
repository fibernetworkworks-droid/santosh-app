"""PC bridge storage: pairing codes, devices, activity log, and the short-lived file relay."""
from __future__ import annotations

import hashlib
import hmac
import logging
import queue
import secrets
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from ..config import get_settings
from ..db import PcDevice, PcFile, PcJob, PcPairCode, new_id, session

log = logging.getLogger("santosh.pc")
PAIR_MINUTES = 10

# Writes made from the live socket loop go through one background thread: the event loop never waits on a database
# lock (SQLite allows one writer, and a Connector call may hold it while it waits for this very PC).
_q: queue.Queue = queue.Queue()
_writer: threading.Thread | None = None


def _write_loop() -> None:
    from sqlalchemy.exc import OperationalError
    while True:
        fn = _q.get()
        for attempt in range(120):
            try:
                fn()
                break
            except OperationalError:
                time.sleep(min(5.0, 0.2 * (attempt + 1)))
            except Exception:
                log.exception("pc background write failed")
                break
        _q.task_done()


def _bg(fn) -> None:
    global _writer
    if _writer is None or not _writer.is_alive():
        _writer = threading.Thread(target=_write_loop, name="santosh-pc-writer", daemon=True)
        _writer.start()
    _q.put(fn)


def flush_writes(timeout: float = 5.0) -> None:
    """Tests and shutdown: wait until queued writes are stored."""
    end = time.time() + timeout
    while _q.unfinished_tasks and time.time() < end:
        time.sleep(0.02)
_fails: dict[str, list[float]] = {}


class PairError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _aware(d: datetime | None) -> datetime | None:
    if d is not None and d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d


# ---------------- pairing ----------------
def pair_start(tenant_id: str) -> dict[str, Any]:
    code = f"{secrets.randbelow(10**6):06d}"
    with session() as s:
        s.execute(delete(PcPairCode).where(PcPairCode.tenant_id == tenant_id))
        s.add(PcPairCode(code_hash=_h(code), tenant_id=tenant_id, expires_at=_now() + timedelta(minutes=PAIR_MINUTES)))
    return {"code": code, "expires_in": PAIR_MINUTES * 60}


def _limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _fails.get(ip, []) if now - t < 600]
    _fails[ip] = hits
    return len(hits) >= 10


def pair_finish(code: str, name: str, os_name: str, ip: str = "") -> dict[str, Any]:
    from .hub import new_token
    if _limited(ip):
        raise PairError("Too many wrong codes. Wait 10 minutes and try again.")
    code = "".join(ch for ch in str(code) if ch.isdigit())
    with session() as s:
        row = s.get(PcPairCode, _h(code)) if len(code) == 6 else None
        if row is None or row.used or _aware(row.expires_at) < _now():
            _fails.setdefault(ip, []).append(time.time())
            raise PairError("Code galat hai ya purana ho gaya. Phone par naya code banaiye.")
        row.used = True
        token = new_token()
        dev = PcDevice(tenant_id=row.tenant_id, name=(name or "PC")[:120], os=(os_name or "")[:60], token_hash=_h(token))
        s.add(dev)
        s.flush()
        return {"device_id": dev.id, "token": token}


def device_for_token(token: str) -> PcDevice | None:
    if not token or not token.startswith("spc_"):
        return None
    with session() as s:
        d = s.scalars(select(PcDevice).where(PcDevice.token_hash == _h(token), PcDevice.revoked.is_(False))).first()
        if d is not None:
            s.expunge(d)
        return d


def touch_device(device_id: str) -> None:
    def w():
        with session() as s:
            d = s.get(PcDevice, device_id)
            if d:
                d.last_seen = _now()
    _bg(w)


def save_info(device_id: str, info: dict[str, Any]) -> None:
    def w():
        with session() as s:
            d = s.get(PcDevice, device_id)
            if d:
                d.info = info
                if info.get("name"):
                    d.name = str(info["name"])[:120]
                if info.get("os"):
                    d.os = str(info["os"])[:60]
                d.last_seen = _now()
    _bg(w)


def devices(tenant_id: str) -> list[dict[str, Any]]:
    from .hub import hub
    with session() as s:
        rows = s.scalars(select(PcDevice).where(PcDevice.tenant_id == tenant_id, PcDevice.revoked.is_(False))
                         .order_by(PcDevice.created_at)).all()
        out = []
        for d in rows:
            live = hub.info_of(tenant_id, d.id)
            info = live if live is not None else (d.info or {})
            out.append({"id": d.id, "name": d.name, "os": d.os, "online": live is not None,
                        "last_seen": _aware(d.last_seen).isoformat() if d.last_seen else None,
                        "folders": info.get("folders") or [], "tally": info.get("tally") or {},
                        "version": info.get("version") or "", "indexed": info.get("indexed") or 0,
                        "inbox": info.get("inbox") or "", "paused": bool(info.get("paused"))})
        return out


def revoke(tenant_id: str, device_id: str) -> bool:
    with session() as s:
        d = s.get(PcDevice, device_id)
        if not d or d.tenant_id != tenant_id or d.revoked:
            return False
        d.revoked = True
    try:   # v0.173 her memory of that PC's recent work goes with the pairing
        from . import memory
        memory.forget(tenant_id)
    except Exception:
        log.exception("pc memory forget failed")
    return True


# ---------------- activity log ----------------
def log_job(tenant_id: str, device_id: str, action: str, summary: str) -> str:
    jid = new_id("job")
    at = _now()

    def w():
        with session() as s:
            s.add(PcJob(id=jid, tenant_id=tenant_id, device_id=device_id, action=action, summary=summary, created_at=at))
    _bg(w)
    return jid


def finish_job(job_id: str, status: str, error: str = "") -> None:
    at = _now()

    def w():
        with session() as s:
            j = s.get(PcJob, job_id)
            if j:
                j.status, j.error, j.finished_at = status, error[:300], at
    _bg(w)


def jobs(tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(PcJob).where(PcJob.tenant_id == tenant_id).order_by(PcJob.created_at.desc())
                         .limit(max(1, min(limit, 200)))).all()
        return [{"id": j.id, "device_id": j.device_id, "action": j.action, "summary": j.summary, "status": j.status,
                 "error": j.error, "at": _aware(j.created_at).isoformat()} for j in rows]


# ---------------- file relay ----------------
def files_dir() -> Path:
    p = Path(get_settings().pc_files_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sign_key() -> bytes:
    st = get_settings()
    if st.secret_key:
        return hashlib.sha256(("pcfiles:" + st.secret_key).encode()).digest()
    f = files_dir() / ".sign_key"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        f.chmod(0o600)
    return bytes.fromhex(f.read_text().strip())


def sign(file_id: str, exp: int) -> str:
    return hmac.new(_sign_key(), f"{file_id}:{exp}".encode(), hashlib.sha256).hexdigest()[:40]


def download_path(file_id: str, hours: int | None = None) -> str:
    exp = int(time.time()) + 3600 * (hours or get_settings().pc_file_hours)
    return f"/api/pc/files/{file_id}?exp={exp}&sig={sign(file_id, exp)}"


def check_sig(file_id: str, exp: int, sig: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(sign(file_id, exp), sig or "")


def max_bytes() -> int:
    return get_settings().pc_max_file_mb * 1024 * 1024


def safe_name(name: str) -> str:
    name = Path(str(name or "file")).name
    name = "".join(ch for ch in name if ch not in '<>:"/\\|?*\x00').strip(" .") or "file"
    return name[:200]


async def store_upload(upload, tenant_id: str, device_id: str, direction: str, pc_path: str = "",
                       limit_mb: int | None = None) -> PcFile:
    """Streams an UploadFile to disk with a size cap. Returns the saved row."""
    fid_dir = files_dir()
    tmp = fid_dir / ("up_" + secrets.token_hex(8))
    h = hashlib.sha256()
    size = 0
    limit = limit_mb * 1024 * 1024 if limit_mb else max_bytes()
    try:
        with tmp.open("wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise PairError(f"File is bigger than {limit_mb or get_settings().pc_max_file_mb} MB")
                h.update(chunk)
                out.write(chunk)
        import asyncio
        fid = new_id("file")
        final = fid_dir / fid
        shutil.move(str(tmp), final)

        def w() -> PcFile:
            with session() as s:
                row = PcFile(id=fid, tenant_id=tenant_id, device_id=device_id, direction=direction,
                             name=safe_name(upload.filename), size=size, sha256=h.hexdigest(), pc_path=pc_path[:2000],
                             stored_path=str(final))
                s.add(row)
                s.flush()
                s.expunge(row)
                return row
        return await asyncio.to_thread(w)
    finally:
        if tmp.exists():
            tmp.unlink()


def get_file(file_id: str) -> PcFile | None:
    with session() as s:
        f = s.get(PcFile, file_id)
        if f is not None:
            s.expunge(f)
        return f


def public_file(f: PcFile) -> dict[str, Any]:
    return {"file_id": f.id, "name": f.name, "size": f.size, "url": download_path(f.id), "pc_path": f.pc_path}


def cleanup_files() -> int:
    cutoff = _now() - timedelta(hours=get_settings().pc_file_hours)
    n = 0
    with session() as s:
        for f in s.scalars(select(PcFile)).all():
            if _aware(f.created_at) >= cutoff:
                continue
            if f.stored_path and Path(f.stored_path).exists():
                Path(f.stored_path).unlink()
            s.delete(f)
            n += 1
        for c in s.scalars(select(PcPairCode)).all():
            if _aware(c.expires_at) < _now() - timedelta(hours=1):
                s.delete(c)
    return n
