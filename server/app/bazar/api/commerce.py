"""Commerce API (v0.4): MCP access tokens, ONDC network callbacks and onboarding, orders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..commerce.mcp_server import issue_token
from ..commerce.ondc import crypto
from ..commerce.providers.ondc import make_buyer
from ..commerce.service import CommerceService
from ..config import get_settings
from ..db import McpToken, User, get_session

router = APIRouter(tags=["commerce"])   # API token
public = APIRouter(tags=["ondc"])       # called by the ONDC network

ON_ACTIONS = {"on_search", "on_select", "on_init", "on_confirm", "on_status", "on_track", "on_cancel", "on_update",
              "on_rating", "on_support"}


class TokenIn(BaseModel):
    label: str = Field(default="My AI assistant", max_length=80)


def _user(s: Session, uid: str) -> User:
    u = s.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    return u


@router.post("/v1/users/{uid}/mcp-tokens")
def create_mcp_token(uid: str, body: TokenIn, s: Session = Depends(get_session)):
    """Token for connecting Claude / ChatGPT / Gemini / any MCP client to Santosh Commerce. Shown once."""
    _user(s, uid)
    tok = issue_token(s, uid, body.label)
    base = get_settings().public_base_url.rstrip("/")
    return {"token": tok, "mcp_url": f"{base.replace(':8000', ':8100')}/mcp", "label": body.label,
            "note": "Keep it secret. Anyone with this token can shop as you (payments still need your UPI PIN)."}


@router.get("/v1/users/{uid}/mcp-tokens")
def list_mcp_tokens(uid: str, s: Session = Depends(get_session)):
    return [{"id": t.id, "label": t.label, "created_at": t.created_at.isoformat(timespec="minutes"), "revoked": t.revoked}
            for t in s.scalars(select(McpToken).where(McpToken.user_id == uid)).all()]


@router.delete("/v1/users/{uid}/mcp-tokens/{tid}")
def revoke_mcp_token(uid: str, tid: str, s: Session = Depends(get_session)):
    t = s.get(McpToken, tid)
    if not t or t.user_id != uid:
        raise HTTPException(404, "Token not found")
    t.revoked = True
    s.commit()
    return {"revoked": tid}


@router.get("/v1/users/{uid}/orders")
def orders(uid: str, open_only: bool = False, s: Session = Depends(get_session)):
    return CommerceService(s, get_settings()).list_orders(_user(s, uid), open_only, 30)


# ------------------------------------------------------------------ ONDC network
@public.get("/ondc-site-verification.html", response_class=HTMLResponse)
def ondc_site_verification():
    st = get_settings()
    if not (st.ondc_request_id and st.ondc_signing_private_key):
        raise HTTPException(404, "Not configured")
    return HTMLResponse(crypto.site_verification_html(st.ondc_request_id, st.ondc_signing_private_key))


class ChallengeIn(BaseModel):
    subscriber_id: str
    challenge: str


@public.post("/ondc/on_subscribe")
def ondc_on_subscribe(body: ChallengeIn):
    st = get_settings()
    if body.subscriber_id != st.ondc_subscriber_id:
        raise HTTPException(400, "Unknown subscriber")
    try:
        answer = crypto.decrypt_challenge(body.challenge, st.ondc_encryption_private_key, st.ondc_registry_public_key)
    except Exception as e:
        raise HTTPException(400, "Could not decrypt the challenge") from e
    return {"answer": answer}


@public.post("/ondc/{action}")
async def ondc_callback(action: str, request: Request, s: Session = Depends(get_session)):
    if action not in ON_ACTIONS:
        return JSONResponse({"message": {"ack": {"status": "NACK"}}, "error": {"code": "10002", "message": "Unsupported action"}},
                            status_code=400)
    body = await request.body()
    res = make_buyer(s, get_settings()).receive(action, request.headers.get("authorization", ""), body)
    ok = ((res.get("message") or {}).get("ack") or {}).get("status") == "ACK"
    return JSONResponse(res, status_code=200 if ok else 401)
