"""ONDC buyer app (BAP): signed requests to the gateway / seller apps, async callback receiver, registry lookup.

Flow: search (gateway) -> on_search from many seller apps -> select -> on_select (quote) -> init -> on_init (payment
terms) -> [user approves + pays by UPI] -> confirm -> on_confirm -> status / cancel / update(return).

Callbacks reach ``POST {subscriber_uri}/on_<action>`` (mounted in app/main.py). Each is signature-checked against the
sender's key from the ONDC registry, stored in ``ondc_messages`` and ACKed; the waiting request picks it up.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...connectors.base import ToolError
from ...db import OndcMessage
from . import beckn
from .crypto import parse_auth_header, sign_body, verify_body

ACK = {"message": {"ack": {"status": "ACK"}}}


def nack(code: str, msg: str) -> dict[str, Any]:
    return {"message": {"ack": {"status": "NACK"}}, "error": {"type": "CONTEXT-ERROR", "code": code, "message": msg}}


class Registry:
    """ONDC registry lookup (v2.0, signed) with an in-memory key cache."""

    def __init__(self, settings: Any, http: httpx.Client):
        self.s, self.http = settings, http
        self.cache: dict[tuple[str, str], str] = {}

    def signing_key(self, subscriber_id: str, unique_key_id: str) -> str | None:
        k = (subscriber_id, unique_key_id)
        if k in self.cache:
            return self.cache[k]
        body = json.dumps({"subscriber_id": subscriber_id, "ukId": unique_key_id, "country": "IND"}).encode()
        headers = {"Content-Type": "application/json",
                   "Authorization": sign_body(body, self.s.ondc_subscriber_id, self.s.ondc_unique_key_id,
                                              self.s.ondc_signing_private_key)}
        try:
            r = self.http.post(self.s.ondc_registry_url, content=body, headers=headers)
        except httpx.HTTPError:
            return None
        if r.status_code != 200:
            return None
        rows = r.json() if isinstance(r.json(), list) else []
        for row in rows:
            if row.get("subscriber_id") == subscriber_id and row.get("ukId", row.get("unique_key_id")) == unique_key_id:
                self.cache[k] = row["signing_public_key"]
                return self.cache[k]
        return None


class OndcBuyer:
    def __init__(self, session: Session, settings: Any, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.db, self.s, self.sleep = session, settings, sleep
        self.http = httpx.Client(timeout=10.0, transport=transport)
        self.registry = Registry(settings, self.http)
        if not settings.ondc_signing_private_key:
            raise ToolError("ONDC keys are not set (SANTOSH_ONDC_SIGNING_PRIVATE_KEY). Run scripts/ondc_keys.py.")

    # ------------------------------------------------------------------ outbound
    def _ctx(self, action: str, domain: str, txn: str, bpp_id: str = "", bpp_uri: str = "") -> dict[str, Any]:
        return beckn.context(action, domain=domain, bap_id=self.s.ondc_subscriber_id, bap_uri=self.s.ondc_subscriber_uri,
                             city=self.s.ondc_city_code, core_version=self.s.ondc_core_version, transaction_id=txn,
                             bpp_id=bpp_id, bpp_uri=bpp_uri)

    def _post(self, url: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        headers = {"Content-Type": "application/json",
                   "Authorization": sign_body(body, self.s.ondc_subscriber_id, self.s.ondc_unique_key_id,
                                              self.s.ondc_signing_private_key)}
        try:
            r = self.http.post(url, content=body, headers=headers)
        except httpx.HTTPError as e:
            raise ToolError(f"The ONDC network didn't respond ({type(e).__name__}). Please try again.") from e
        ack = {}
        try:
            ack = r.json()
        except ValueError:
            pass
        if r.status_code >= 400 or ((ack.get("message") or {}).get("ack") or {}).get("status") != "ACK":
            err = (ack.get("error") or {}).get("message") or f"HTTP {r.status_code}"
            raise ToolError(f"The ONDC seller app refused the request: {err}")

    def _wait(self, message_id: str, action: str, many: bool = False) -> list[OndcMessage]:
        deadline = time.monotonic() + (self.s.ondc_wait_seconds if self.s.ondc_mode != "sandbox" else 0)
        while True:
            self.db.expire_all()
            rows = list(self.db.scalars(select(OndcMessage).where(OndcMessage.message_id == message_id,
                                                                  OndcMessage.action == action)).all())
            if (rows and not many) or time.monotonic() >= deadline:
                return rows
            self.sleep(0.25)

    def call(self, action: str, domain: str, txn: str, bpp_id: str, bpp_uri: str, message: dict[str, Any]) -> dict[str, Any]:
        ctx = self._ctx(action, domain, txn, bpp_id, bpp_uri)
        self._post(bpp_uri.rstrip("/") + "/" + action, {"context": ctx, "message": message})
        rows = self._wait(ctx["message_id"], "on_" + action)
        if not rows:
            raise ToolError("The seller didn't answer in time on ONDC. Please try again in a minute.")
        return rows[-1].payload

    def search(self, query: str, pincode: str, gps: str, domains: list[str]) -> list[dict[str, Any]]:
        offers: list[dict[str, Any]] = []
        for domain in domains:
            txn = beckn.new_id()
            ctx = self._ctx("search", domain, txn)
            self._post(self.s.ondc_gateway_url, {"context": ctx, "message": beckn.search_message(
                query, pincode, gps, self.s.ondc_finder_fee_percent)})
            for row in self._wait(ctx["message_id"], "on_search", many=True):
                for o in beckn.parse_catalog(row.payload):
                    o["ref"]["transaction_id"] = txn
                    offers.append(o)
        return offers

    # ------------------------------------------------------------------ inbound
    def receive(self, action: str, auth_header: str, body: bytes) -> dict[str, Any]:
        """Handle a callback from a seller app / gateway. Returns the ACK/NACK body."""
        if not action.startswith("on_"):
            return nack("10002", "Unsupported action")
        p = parse_auth_header(auth_header or "")
        sub, ukid = p.get("subscriber_id"), p.get("unique_key_id")
        if not sub or not ukid:
            return nack("10001", "Missing or invalid Authorization header")
        key = self.registry.signing_key(sub, ukid)
        if not key or not verify_body(auth_header, body, key):
            return nack("10001", "Invalid signature")
        try:
            payload = json.loads(body)
        except ValueError:
            return nack("10002", "Invalid JSON")
        ctx = payload.get("context") or {}
        if ctx.get("bap_id") != self.s.ondc_subscriber_id:
            return nack("10002", "Not addressed to this buyer app")
        self.db.add(OndcMessage(transaction_id=ctx.get("transaction_id", ""), message_id=ctx.get("message_id", ""),
                                action=action, bpp_id=ctx.get("bpp_id", ""), payload=payload))
        self.db.commit()
        return ACK
