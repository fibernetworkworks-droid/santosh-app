"""Settings file and the device token (encrypted with Windows DPAPI on Windows)."""
from __future__ import annotations

import base64
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def app_dir() -> Path:
    if os.environ.get("SANTOSH_DESKTOP_HOME"):
        d = Path(os.environ["SANTOSH_DESKTOP_HOME"])
    elif sys.platform == "win32":
        d = Path(os.environ.get("APPDATA", Path.home())) / "Santosh"
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / "Santosh"
    else:
        d = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "santosh"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_inbox() -> str:
    docs = Path.home() / "Documents"
    return str((docs if docs.exists() else Path.home()) / "Santosh Inbox")


# ---- token protection: DPAPI on Windows (only this Windows user can decrypt), plain elsewhere (file is 0600) ----
def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI failed")
    out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return out


def seal(token: str) -> str:
    if not token:
        return ""
    if sys.platform == "win32":
        try:
            return "dpapi:" + base64.b64encode(_dpapi(token.encode(), True)).decode()
        except Exception:
            pass
    return "plain:" + token


def unseal(v: str) -> str:
    if not v:
        return ""
    if v.startswith("dpapi:"):
        return _dpapi(base64.b64decode(v[6:]), False).decode()
    return v.removeprefix("plain:")


@dataclass
class Config:
    server: str = ""
    device_id: str = ""
    token_sealed: str = ""
    folders: list[str] = field(default_factory=list)
    inbox: str = field(default_factory=default_inbox)
    paused: bool = False
    tally_host: str = "localhost"
    tally_port: int = 9000
    name: str = field(default_factory=lambda: platform.node() or "PC")

    @property
    def token(self) -> str:
        return unseal(self.token_sealed)

    @token.setter
    def token(self, v: str) -> None:
        self.token_sealed = seal(v)

    @property
    def paired(self) -> bool:
        return bool(self.server and self.device_id and self.token_sealed)


def path() -> Path:
    return app_dir() / "config.json"


def load() -> Config:
    p = path()
    if not p.exists():
        return Config()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return Config()
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known)


def save(cfg: Config) -> None:
    p = path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(p)
