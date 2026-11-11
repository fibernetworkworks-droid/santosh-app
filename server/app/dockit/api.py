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


# ------------------------------------------------------------------------------------------- /sign/<key> (D5)
def _sign_headers(nonce: str) -> dict[str, str]:
    return HEADERS | {"Content-Security-Policy": f"default-src 'none'; img-src data:; style-src 'unsafe-inline'; "
                                                 f"script-src 'nonce-{nonce}'; form-action 'self'"}


def _sign_page(title: str, body: str, nonce: str = "", status: int = 200) -> HTMLResponse:
    r = _page(title, body, status)
    if nonce:
        r.headers.update(_sign_headers(nonce))
    return HTMLResponse(r.body.decode().replace("<p><small>Hoola never sees or keeps this password. This page works "
                                                "once.</small></p>", ""), status_code=status,
                        headers=_sign_headers(nonce) if nonce else HEADERS)


@router.get("/sign/{key}")
async def sign_page(key: str):
    import secrets as _s
    import time as _t
    from . import sign
    got = sign.load_request(key)
    if got is None:
        return _sign_page("Signing link", "<h1>This signing link is not valid</h1><p>Ask the sender for a new one.</p>",
                          status=404)
    req, signer, idx = got
    fn = html.escape(req["file_name"])
    if req["expires"] < _t.time():
        return _sign_page("Signing link", f"<h1>This link has expired</h1><p>{fn} can no longer be signed here.</p>",
                          status=410)
    if signer["signed_at"]:
        return _sign_page("Signed", f"<h1 class=\"ok\">You have signed {fn}</h1><p>Thank you. Nothing more to do.</p>")
    turn = sign.turn_of(req)
    if turn != idx:
        who = html.escape(req["signers"][turn]["name"])
        return _sign_page("Not your turn yet", f"<h1>Waiting for {who}</h1><p>{fn} is signed in order. Open this same "
                          "link again after they have signed.</p>")
    nonce = _s.token_urlsafe(12)
    import asyncio as _a
    pics = "".join(f'<img alt="page {i + 1}" src="{u}" style="width:100%;border:1px solid #ddd;border-radius:8px;'
                   f'margin:6px 0">' for i, u in enumerate(await _a.to_thread(sign.page_pictures, req)))
    msg = f"<p>{html.escape(req['message'])}</p>" if req.get("message") else ""
    body = f"""<h1>Sign {fn}</h1><p>Hello {html.escape(signer['name'])}. Please read the document, then sign below.</p>
{msg}<details><summary>Read the document</summary>{pics}</details>
<form method="post" id="f" autocomplete="off">
<p><b>Your signature</b> (draw with your finger or mouse)</p>
<canvas id="c" width="600" height="200" style="width:100%;height:160px;border:1px dashed #8a86a8;border-radius:10px;
touch-action:none;background:#fff"></canvas>
<p><a href="#" id="clr">Clear</a></p>
<input name="sig" id="sig" type="hidden">
<input name="name" placeholder="Type your full name" required maxlength="80">
<label style="display:block;margin:10px 0"><input type="checkbox" name="agree" required style="width:auto">
I have read this document and I agree to sign it electronically.</label>
<button>Sign</button></form>
<p><small>Your name, the time, your IP address and device are recorded on a signing page added to the document.</small></p>
<script nonce="{nonce}">
const c=document.getElementById('c'),x=c.getContext('2d');let d=false,inked=false;x.lineWidth=4;x.lineCap='round';
x.strokeStyle='#14205a';
const p=e=>{{const r=c.getBoundingClientRect(),t=e.touches?e.touches[0]:e;return[(t.clientX-r.left)*c.width/r.width,
(t.clientY-r.top)*c.height/r.height]}};
const s=e=>{{d=true;const[a,b]=p(e);x.beginPath();x.moveTo(a,b);e.preventDefault()}};
const m=e=>{{if(!d)return;const[a,b]=p(e);x.lineTo(a,b);x.stroke();inked=true;e.preventDefault()}};
const u=()=>{{d=false}};
['mousedown','touchstart'].forEach(k=>c.addEventListener(k,s));['mousemove','touchmove'].forEach(k=>c.addEventListener(k,m));
['mouseup','mouseleave','touchend'].forEach(k=>c.addEventListener(k,u));
document.getElementById('clr').onclick=e=>{{e.preventDefault();x.clearRect(0,0,c.width,c.height);inked=false}};
document.getElementById('f').onsubmit=e=>{{if(!inked){{e.preventDefault();alert('Please draw your signature.');return}}
document.getElementById('sig').value=c.toDataURL('image/png')}};
</script>"""
    return _sign_page(f"Sign {req['file_name']}", body, nonce)


@router.post("/sign/{key}")
async def sign_submit(key: str, request: Request):
    import base64 as _b
    from . import sign
    from .core import DocError
    got = sign.load_request(key)
    if got is None:
        return _sign_page("Signing link", "<h1>This signing link is not valid</h1>", status=404)
    req, signer, idx = got
    try:
        form = await request.form()
    except Exception:
        form = {}
    sig = str(form.get("sig") or "")
    if not sig.startswith("data:image/png;base64,") or len(sig) > 3_000_000 or not form.get("agree"):
        return _sign_page("Sign", "<h1>Please draw your signature and tick the box</h1><p><a href=\"\">Back</a></p>",
                          status=400)
    try:
        png = _b.b64decode(sig.split(",", 1)[1], validate=True)
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "") or "").split(",")[0]
        import asyncio as _a                       # pyHanko runs its own event loop: never on the server's loop
        res = await _a.to_thread(sign.complete_one, req, signer, idx, png, str(form.get("name") or ""), ip.strip(),
                                 request.headers.get("user-agent") or "")
    except DocError as e:
        return _sign_page("Sign", f"<h1>Could not sign</h1><p class=\"bad\">{html.escape(str(e))}</p>", status=400)
    except Exception as e:
        log.info("sign page failed: %s", type(e).__name__)
        return _sign_page("Sign", "<h1>Could not sign</h1><p class=\"bad\">Something went wrong; try again.</p>", status=500)
    fn = html.escape(req["file_name"])
    try:
        from ..agent.make_tools import _safe
        if res.get("done"):
            _deliver(req | {"tenant": req["tenant"], "conv": req["conv"]}, _safe(f"{req['file_name'].rsplit('.', 1)[0]} "
                                                                                  "(signed)", ".pdf"), res["bytes"])
        else:
            from ..events import bus
            bus.publish(req["conv"], "message", {"role": "assistant", "text": f"{signer['name']} signed {req['file_name']}. "
                        f"Next: {req['signers'][sign.turn_of(req)]['name']}.", "source": "pdf_kit"})
    except Exception as e:
        log.info("sign delivery failed: %s", type(e).__name__)
    return _sign_page("Signed", f"<h1 class=\"ok\">Thank you - you have signed {fn}</h1>" +
                      ("<p>Everyone has signed. The sender now has the signed copy with the signing record.</p>"
                       if res.get("done") else "<p>The next person has been told it is their turn.</p>"))
