"""The one-time pages (/pdf/key/<token>): she sees the password Hoola made, or types her own to lock / unlock a PDF.
Nothing here is ever sent to the model or written into the chat; the page answers only the person holding the link,
once. A GET never reveals a secret (link previews and fetchers see a button, not a password) - only her tap (POST)."""
from __future__ import annotations

import html
import logging
from types import SimpleNamespace

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from . import check, secure, vault

log = logging.getLogger("santosh.dockit")
router = APIRouter()

HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow",
           "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'",
           "X-Frame-Options": "DENY"}


def _page(title: str, body: str, status: int = 200) -> HTMLResponse:
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{html.escape(title)}</title><style>
body{{margin:0;background:#f6f5fb;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#17152a}}
main{{max-width:440px;margin:40px auto;padding:28px 24px;background:#fff;border-radius:16px;box-shadow:0 6px 24px #17152a14}}
h1{{font-size:20px;margin:0 0 8px}} p{{margin:8px 0;color:#4a4766}} .pw{{font:600 24px/1.4 ui-monospace,Menlo,monospace;
letter-spacing:1px;background:#f1effa;border-radius:10px;padding:14px;text-align:center;user-select:all;margin:16px 0}}
input{{width:100%;box-sizing:border-box;font-size:17px;padding:12px;border:1px solid #cfcbe6;border-radius:10px;margin:6px 0}}
button{{width:100%;font-size:16px;font-weight:600;padding:13px;border:0;border-radius:10px;background:#5b3df5;color:#fff;
margin-top:10px;cursor:pointer}} .bad{{color:#b3261e}} .ok{{color:#1b6e2d}} small{{color:#77739a}}</style></head>
<body><main>{body}<p><small>Hoola never sees or keeps this password. This page works once.</small></p></main></body></html>"""
    return HTMLResponse(doc, status_code=status, headers=HEADERS)


GONE = ("Link used or expired", "<h1>This link has been used or has expired</h1><p>For safety it works only once. "
        "Ask Hoola again in the chat for a new one.</p>")


def _name(row: dict) -> str:
    return html.escape(str(row.get("meta", {}).get("name") or "your PDF"))


@router.get("/pdf/key/{token}")
async def key_page(token: str):
    row = vault.peek(token)
    if row is None:
        return _page(*GONE, status=410)
    n = _name(row)
    if row["kind"] == "show_password":
        return _page("Your PDF password", f"<h1>Password for {n}</h1><p>Tap to see it. Write it down or save it in "
                     "your password manager: Hoola cannot show it again, and without it the PDF cannot be opened.</p>"
                     '<form method="post"><button>Show the password</button></form>')
    if row["kind"] == "set_password":
        return _page("Lock your PDF", f"<h1>Lock {n}</h1><p>Type the password the PDF will ask for. It goes into "
                     "the PDF only.</p><form method=\"post\" autocomplete=\"off\"><input type=\"password\" name=\"p1\" "
                     "placeholder=\"Password\" required minlength=\"8\" autocomplete=\"new-password\"><input "
                     "type=\"password\" name=\"p2\" placeholder=\"Type it again\" required minlength=\"8\" "
                     "autocomplete=\"new-password\"><p><small>At least 8 characters, with three of: small letters, "
                     "capitals, numbers, symbols.</small></p><button>Lock the PDF</button></form>")
    if row["kind"] == "unlock":
        left = vault.MAX_TRIES - int(row.get("tries", 0))
        return _page("Unlock your PDF", f"<h1>Unlock {n}</h1><p>Type the password this PDF opens with (for a bank "
                     "statement it is often written in the bank's email). An unlocked copy will arrive in your chat."
                     f"</p><form method=\"post\" autocomplete=\"off\"><input type=\"password\" name=\"p1\" "
                     f"placeholder=\"The PDF's password\" required autocomplete=\"off\"><button>Unlock</button></form>"
                     f"<p><small>{left} tries left.</small></p>")
    return _page(*GONE, status=410)


def _ctx(row: dict) -> SimpleNamespace:
    return SimpleNamespace(tenant_id=row["tenant"], conversation_id=row["conv"], actor="owner")


def _file(row: dict) -> tuple[str, bytes]:
    from pathlib import Path
    from ..mailbox import service as ms
    f = ms._file_row(row["tenant"], str(row["payload"]["file_id"]))
    return f.name, Path(f.stored_path).read_bytes()


def _deliver(row: dict, name: str, data: bytes) -> dict:
    from ..agent.make_tools import _deliver as deliver
    return deliver(_ctx(row), name, data, "pdf_kit")


@router.post("/pdf/key/{token}")
async def key_submit(token: str, request: Request):
    row = vault.get(token)
    if row is None:
        return _page(*GONE, status=410)
    n = _name(row)
    if row["kind"] == "show_password":
        row = vault.take(token)
        if row is None:
            return _page(*GONE, status=410)
        pw = html.escape(row["payload"]["password"])
        return _page("Your PDF password", f"<h1>Password for {n}</h1><div class=\"pw\">{pw}</div><p>Save it now. "
                     "If you lose it, the locked copy cannot be opened (the original is still in your chat for 24 "
                     "hours).</p>")
    try:
        form = await request.form()
    except Exception:
        form = {}
    p1, p2 = str(form.get("p1") or ""), str(form.get("p2") or "")
    if row["kind"] == "set_password":
        if p1 != p2:
            return _page("Lock your PDF", f"<h1>Lock {n}</h1><p class=\"bad\">The two passwords are not the same."
                         "</p><p><a href=\"\">Try again</a></p>", status=400)
        why = secure.password_problem(p1)
        if why:
            return _page("Lock your PDF", f"<h1>Lock {n}</h1><p class=\"bad\">{html.escape(why)}</p>"
                         "<p><a href=\"\">Try again</a></p>", status=400)
        row = vault.take(token)
        if row is None:
            return _page(*GONE, status=410)
        try:
            name, data = _file(row)
            allow = list(row["payload"].get("allow") or ["print", "copy", "accessibility"])
            locked = secure.protect(data, p1, allow, True)
            secure.check_protected(locked, p1, True, allow)
            check.pdf_out(secure.unlock(locked, p1)[0], None, name)
            _deliver(row, row["payload"]["out_name"], locked)
        except Exception as e:
            log.info("pdf lock page failed: %s", type(e).__name__)
            return _page("Lock your PDF", f"<h1>Could not lock {n}</h1><p class=\"bad\">{html.escape(str(e)[:200])}"
                         "</p>", status=400)
        return _page("Locked", f"<h1 class=\"ok\">{n} is locked</h1><p>The locked copy is in your chat now. It asks "
                     "for the password you just typed.</p>")
    if row["kind"] == "unlock":
        try:
            name, data = _file(row)
            out, kind = secure.unlock(data, p1)
        except secure.NeedsPassword:
            out = None
        except Exception as e:
            if "not right" not in str(e):
                return _page("Unlock", f"<h1>Could not unlock {n}</h1><p class=\"bad\">{html.escape(str(e)[:200])}"
                             "</p>", status=400)
            out = None
        if out is None:
            left = vault.fail(token)
            if left <= 0:
                return _page("Unlock", f"<h1>{n} stays locked</h1><p class=\"bad\">That password was not right, "
                             f"{vault.MAX_TRIES} times. For safety this page is closed; Hoola never tries passwords "
                             "itself.</p>", status=403)
            return _page("Unlock", f"<h1>Unlock {n}</h1><p class=\"bad\">That password is not right. {left} tries "
                         "left.</p><p><a href=\"\">Try again</a></p>", status=400)
        vault.take(token)
        check.pdf_out(out, None, name)
        _deliver(row, row["payload"]["out_name"], out)
        return _page("Unlocked", f"<h1 class=\"ok\">{n} is unlocked</h1><p>A copy without the password is in your "
                     "chat now. Your password was used once and is not kept.</p>")
    return _page(*GONE, status=410)
