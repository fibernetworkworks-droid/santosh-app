"""One-time pages for the things that must never pass through the chat (plan law 4.4): a password Hoola made for her
locked PDF, the password she types to lock or unlock a PDF, and the redaction she is about to apply.

A token is 32 random bytes; it opens ONE page, expires (24 h for passwords made by Hoola, 2 h for the forms), and is
burnt when used. What is kept on disk is sealed with the server's SECRET_KEY (Fernet); without a SECRET_KEY nothing
is written to disk at all - it lives in this process only (a restart forgets it, which is the safe failure)."""
from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any

_MEM: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
MAX_TRIES = 5


def _dir() -> Path:
    from ..config import get_settings
    d = Path(get_settings().pc_files_dir).parent / "dockit_vault"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sealer():
    from ..config import get_settings
    if not get_settings().secret_key:
        return None
    from ..accounts import _fernet
    return _fernet()


def put(kind: str, tenant: str, conversation_id: str, payload: dict[str, Any], hours: float = 2) -> str:
    token = secrets.token_urlsafe(32)
    row = {"kind": kind, "tenant": tenant, "conv": conversation_id, "exp": time.time() + hours * 3600, "tries": 0}
    f = _sealer()
    with _LOCK:
        if f is None:
            _MEM[token] = row | {"payload": payload}
        else:
            row["sealed"] = f.encrypt(json.dumps(payload).encode()).decode()
            (_dir() / f"{token}.json").write_text(json.dumps(row))
    return token


def _load(token: str) -> dict[str, Any] | None:
    if not token or len(token) < 30 or not all(c.isalnum() or c in "-_" for c in token):
        return None
    with _LOCK:
        row = _MEM.get(token)
        if row is None:
            p = _dir() / f"{token}.json"
            if not p.exists():
                return None
            row = json.loads(p.read_text())
            f = _sealer()
            if f is None:
                return None
            try:
                row["payload"] = json.loads(f.decrypt(row.pop("sealed").encode()))
            except Exception:
                return None
    if row["exp"] < time.time():
        burn(token)
        return None
    return row


def peek(token: str) -> dict[str, Any] | None:
    """The row WITHOUT the secret payload (what the GET page may know)."""
    row = _load(token)
    if row is None:
        return None
    pay = row.get("payload", {})
    return {k: v for k, v in row.items() if k != "payload"} | {"meta": pay.get("meta", {})}


def take(token: str) -> dict[str, Any] | None:
    """The whole row, and the token is burnt."""
    row = _load(token)
    if row is not None:
        burn(token)
    return row


def get(token: str) -> dict[str, Any] | None:
    """The whole row, the token stays (a form she may get wrong and try again)."""
    return _load(token)


def fail(token: str) -> int:
    """One wrong try; at MAX_TRIES the page closes for good. Returns tries left."""
    row = _load(token)
    if row is None:
        return 0
    row["tries"] = int(row.get("tries", 0)) + 1
    left = MAX_TRIES - row["tries"]
    if left <= 0:
        burn(token)
        return 0
    with _LOCK:
        if token in _MEM:
            _MEM[token]["tries"] = row["tries"]
        else:
            p = _dir() / f"{token}.json"
            if p.exists():
                disk = json.loads(p.read_text())
                disk["tries"] = row["tries"]
                p.write_text(json.dumps(disk))
    return left


def burn(token: str) -> None:
    with _LOCK:
        _MEM.pop(token, None)
        try:
            (_dir() / f"{token}.json").unlink(missing_ok=True)
        except Exception:
            pass


def sweep() -> int:
    n = 0
    now = time.time()
    with _LOCK:
        for t, r in list(_MEM.items()):
            if r["exp"] < now:
                _MEM.pop(t, None)
                n += 1
    try:
        for p in _dir().glob("*.json"):
            try:
                if json.loads(p.read_text()).get("exp", 0) < now:
                    p.unlink(missing_ok=True)
                    n += 1
            except Exception:
                p.unlink(missing_ok=True)
    except Exception:
        pass
    return n


def link(token: str) -> str:
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/")
    return f"{base}/pdf/key/{token}"
