"""v0.70 "Hoola mera Google Drive kyun nahi khol raha?" - one honest check of her Google connection.

Looks at: the server's Google sign-in setup, her Google sign-in (which permissions she ticked, whether Google refused the
last refresh), Drive accounts linked in Profile > Google Drive, the owner's service account, and (live) asks Google Drive
who it is talking to. Every problem comes with the fix in her words. Never shows a token.
"""
from __future__ import annotations

from typing import Any

from .config import get_settings

FEATURES = {"drive": "https://www.googleapis.com/auth/drive", "gmail": "https://www.googleapis.com/auth/gmail.modify",
            "gmail_settings": "https://www.googleapis.com/auth/gmail.settings.basic",
            "calendar": "https://www.googleapis.com/auth/calendar", "sheets": "https://www.googleapis.com/auth/spreadsheets",
            "docs": "https://www.googleapis.com/auth/documents"}


def diagnose(tenant: str, live: bool = True) -> dict[str, Any]:
    from .db import session
    from .drive import accounts as da
    from .drive.client import API
    from .google_auth import _google_conn, reconnect_message
    st = get_settings()
    out: dict[str, Any] = {"server_ready": da.oauth_ready(), "signin": None, "drive": [], "problems": [], "ok": False}
    problems: list[str] = out["problems"]

    def add(p: str) -> None:
        if p and p not in problems:
            problems.append(p)

    if not out["server_ready"]:
        add("Server par Google sign-in set nahi hai: VPS ki .env mein GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, "
            "PUBLIC_BASE_URL aur SECRET_KEY chahiye.")
    try:
        clients = da.clients(tenant)
    except Exception as e:
        clients = []
        add(f"Drive accounts padhne mein dikkat: {e}")
    # live first: a refresh that works clears an old error, one that fails records it
    for cl in clients:
        row: dict[str, Any] = {"account": cl.address, "kind": cl.kind, "ok": None, "error": ""}
        if live:
            try:
                info = cl._req("GET", API + "/about", params={"fields": "user(emailAddress)"})
                row["ok"], row["seen_as"] = True, (info.get("user") or {}).get("emailAddress", "")
            except Exception as e:
                row["ok"], row["error"] = False, str(e)[:400]
                add(str(e) if cl.address and cl.address in str(e) else f"{cl.address or 'Drive'}: {e}")
        out["drive"].append(row)
    with session() as s:
        c = _google_conn(s, tenant)
        if c is not None:
            granted = set((c.scopes or "").split())
            out["signin"] = {"email": c.account_email, "allowed": {k: v in granted for k, v in FEATURES.items()},
                             "refresh_token": bool(c.refresh_token_enc), "last_error": c.last_error or ""}
            if c.last_error:
                add(reconnect_message(c.account_email, c.last_error))
            elif not c.refresh_token_enc:
                add(reconnect_message(c.account_email, "no refresh token"))
    signin = out["signin"]
    drive_ok = any(r.get("ok") for r in out["drive"]) if live else bool(clients)
    if signin and not signin["allowed"]["drive"] and not drive_ok:
        add(da.why_not(tenant))
    if not clients:
        add(da.why_not(tenant))
    out["ok"] = drive_ok
    if tenant == st.tenant_id:
        from . import gdrive
        out["service_account"] = gdrive.configured(None)
    out["say"] = ("Google Drive theek chal raha hai." if drive_ok and not problems else
                  " ".join(problems[:2]) or "Google Drive juda nahi hai.")
    return out
