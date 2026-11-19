"""v0.999.25 HOOLA CREDITS - routes.

/api/credits                    her wallet, the price list for her country, her orders, her employee packages
/api/credits/checkout           start a purchase (plan / top-up / employee package) with the provider for her country
/api/credits/orders/{id}        the order, checked against the provider's own record
/api/credits/ledger             what came in and went out
/api/credits/webhook/{provider} the providers' signed webhooks (no key: the signature is the check)
/pay/credits/{id}?k=...         the pay page she opens in any browser (India: Razorpay / Cashfree checkout); also where
                                every provider sends her back, showing the order's real state"""
from __future__ import annotations

import html
import json
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from . import pay, plans as P, service as S, wallet as W


class CheckoutIn(BaseModel):
    sku: str
    provider: str = ""
    employee: str = ""
    country: str = ""
    email: str = ""
    name: str = ""
    phone: str = ""


def _country(request, asked: str = "") -> str:
    if asked:
        return asked
    h = request.headers
    c = h.get("cf-ipcountry") or h.get("x-country") or ""
    if c:
        return c
    lang = (h.get("accept-language") or "").split(",")[0]
    if "-" in lang:
        return lang.split("-", 1)[1][:2]
    return ""


def _base(request) -> str:
    from ..config import get_settings
    return (get_settings().public_base_url or str(request.base_url)).rstrip("/")


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException
    from fastapi.responses import HTMLResponse

    r = APIRouter()

    def _err(e: Exception):
        return HTTPException(getattr(e, "code", 400), str(e))

    @r.get("/api/credits", dependencies=[Depends(require_key)])
    def _overview(request: Request, country: str = "", tenant: str = Depends(current_tenant)):
        return S.overview(tenant, _country(request, country))

    @r.post("/api/credits/checkout", dependencies=[Depends(require_key)])
    def _checkout(body: CheckoutIn, request: Request, tenant: str = Depends(current_tenant)):
        try:
            kind, item, region = P.parse_sku(body.sku)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if region != P.region_of(_country(request, body.country)):   # her country's prices only
            raise HTTPException(400, "That price is for another country.")
        try:
            return S.checkout(tenant, body.sku, body.provider, body.employee,
                              {"email": body.email, "name": body.name, "phone": body.phone}, _base(request))
        except S.CreditError as e:
            raise _err(e)

    @r.get("/api/credits/orders/{order_id}", dependencies=[Depends(require_key)])
    def _order(order_id: str, tenant: str = Depends(current_tenant)):
        from ..db import session
        with session() as s:
            o = s.get(W.CreditOrder, order_id)
            if o is None or o.tenant_id != tenant:
                raise HTTPException(404, "No such order.")
        try:
            return S.check(order_id)
        except S.CreditError as e:
            raise _err(e)

    @r.get("/api/credits/ledger", dependencies=[Depends(require_key)])
    def _ledger(n: int = 50, tenant: str = Depends(current_tenant)):
        return {"rows": W.ledger(tenant, n)}

    @r.post("/api/credits/webhook/{provider}")
    async def _webhook(provider: str, request: Request):
        raw = await request.body()
        try:
            out = S.webhook(provider, dict(request.headers), raw)
        except S.CreditError as e:
            raise _err(e)
        if not out.get("ok"):
            raise HTTPException(401, "Signature not valid.")
        return out

    @r.get("/pay/credits/{order_id}", response_class=HTMLResponse)
    def _page(order_id: str, k: str = "", payment_id: str = "", subscription_id: str = ""):
        if not S.token_ok(order_id, k):
            raise HTTPException(404, "No such order.")
        try:
            v = S.check(order_id, payment_id)
            co = S.order_checkout(order_id)
        except S.CreditError as e:
            raise _err(e)
        return HTMLResponse(page(order_id, k, v, co), headers={"Content-Security-Policy": CSP, "Cache-Control": "no-store"})

    @r.get("/pay/credits/{order_id}/state")
    def _state(order_id: str, k: str = "", payment_id: str = ""):
        if not S.token_ok(order_id, k):
            raise HTTPException(404, "No such order.")
        v = S.check(order_id, payment_id)
        return {"status": v["status"], "granted": v["granted"]}

    return r


CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://checkout.razorpay.com https://sdk.cashfree.com; "
       "frame-src https://api.razorpay.com https://checkout.razorpay.com https://*.cashfree.com; "
       "connect-src 'self' https://*.razorpay.com https://*.cashfree.com; img-src 'self' data: https:; "
       "style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'self' https://*.cashfree.com")


def page(order_id: str, k: str, v: dict[str, Any], co: dict[str, Any]) -> str:
    """The small pay / thank-you page. Paid only when the provider said so (the server checked)."""
    name = html.escape(v.get("name") or "Hoola credits")
    cur = "Rs " if v.get("currency") == "INR" else "$"
    amt = f"{cur}{v.get('amount', 0):,.2f}".replace(".00", "")
    status = v.get("status")
    msg = {"paid": f"Payment received. {('%s credits added.' % format(int(v.get('granted') or 0), ',')) if v.get('granted') else 'Your package is active.'} You can close this page and go back to Hoola.",
           "failed": "The payment did not go through. Nothing was charged by Hoola. You can try again from Hoola.",
           "refunded": "This payment was refunded."}.get(status, "Waiting for the payment service to confirm...")
    data = json.dumps({"order": order_id, "k": k, "status": status, "provider": co.get("provider"),
                       "checkout": co.get("checkout") or {}}).replace("</", "<\\/")
    js = ""
    if status == "pending" and co.get("provider") in pay.INDIA:
        js = """<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script src="https://sdk.cashfree.com/js/v3/cashfree.js"></script>"""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hoola credits</title><style>
:root{{--bg:#fff;--ink:#1B1A17;--mut:#6F6C65;--line:#E5E3DD;--pri:#5B45E0}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141413;--ink:#E6E5E1;--mut:#94928B;--line:#3C3B38;--pri:#9C88FF}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;padding:0 16px}}
.card{{max-width:420px;width:100%;border:1px solid var(--line);border-radius:16px;padding:24px}}h1{{font-size:20px;margin:0 0 4px}}
.amt{{font-size:28px;font-weight:600;margin:8px 0}}p{{color:var(--mut)}}button{{height:44px;padding:0 18px;border:0;border-radius:999px;background:var(--ink);color:var(--bg);font:500 15px system-ui;cursor:pointer}}
</style>{js}</head><body><main class="card"><h1>{name}</h1><div class="amt">{amt}</div><p id="msg">{html.escape(msg)}</p>
{'<button id="pay" type="button">Pay now</button>' if status == 'pending' and co.get('provider') in pay.INDIA else ''}
</main><script>
const D={data};
const msg=document.getElementById('msg');
async function poll(pid){{for(let i=0;i<40;i++){{const q='/pay/credits/'+D.order+'/state?k='+D.k+(pid?'&payment_id='+encodeURIComponent(pid):'');
 try{{const r=await (await fetch(q)).json(); if(r.status!=='pending'){{location.reload();return;}}}}catch(e){{}}
 await new Promise(r=>setTimeout(r,3000));}}}}
function startPay(){{const c=D.checkout||{{}};
 if(D.provider==='razorpay'&&window.Razorpay){{const rz=new Razorpay({{key:c.key,order_id:c.order_id,amount:c.amount,currency:c.currency,
   name:'Hoola',description:'Hoola credits',prefill:c.prefill||{{}},theme:{{color:'#5B45E0'}},
   handler:r=>{{msg.textContent='Checking the payment...';poll(r.razorpay_payment_id);}}}});rz.open();}}
 else if(D.provider==='cashfree'&&window.Cashfree){{Cashfree({{mode:c.mode||'production'}}).checkout({{paymentSessionId:c.session,redirectTarget:'_self'}});}}
}}
const b=document.getElementById('pay'); if(b) b.addEventListener('click',startPay);
if(D.status==='pending'&&!b) poll('');
</script></body></html>"""
