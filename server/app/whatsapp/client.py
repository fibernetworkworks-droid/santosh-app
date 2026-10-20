"""WhatsApp Cloud API client (Meta Graph API) plus a simulator with the same interface."""
from __future__ import annotations

import asyncio
import random
import time
import uuid
from datetime import datetime, timezone

import httpx

from ..config import get_settings

# Meta error codes worth retrying: rate limits and temporary failures.
RETRYABLE_CODES = {1, 2, 4, 17, 80007, 130429, 131000, 131016, 131056, 133004}


class WhatsAppError(Exception):
    def __init__(self, message: str, code: int | None = None, retryable: bool = False, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.status = status


class MetaWhatsApp:
    """Talks to graph.facebook.com. Needs WA_TOKEN, WA_WABA_ID and WA_PHONE_NUMBER_ID."""

    dry_run = False

    def __init__(self, token: str, waba_id: str, phone_number_id: str, version: str = "v21.0",
                 http: httpx.AsyncClient | None = None):
        missing = [n for n, v in (("WA_TOKEN", token), ("WA_WABA_ID", waba_id), ("WA_PHONE_NUMBER_ID", phone_number_id)) if not v]
        if missing:
            raise WhatsAppError(f"Live WhatsApp needs {', '.join(missing)} in the settings (or set WA_DRY_RUN=true).")
        self.base = f"https://graph.facebook.com/{version}"
        self.waba_id = waba_id
        self.phone_number_id = phone_number_id
        self.http = http or httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {token}"})

    async def _call(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None,
                    attempts: int = 4) -> dict:
        delay = 1.0
        for i in range(attempts):
            try:
                r = await self.http.request(method, f"{self.base}/{path}", json=json, params=params)
            except httpx.HTTPError as e:
                if i == attempts - 1:
                    raise WhatsAppError(f"Could not reach Meta: {e}", retryable=True)
                await asyncio.sleep(delay); delay *= 2
                continue
            if r.status_code < 400:
                return r.json()
            try:
                err = r.json().get("error", {})
            except ValueError:
                err = {}
            code = err.get("code")
            msg = err.get("error_user_msg") or err.get("message") or r.text[:300]
            retryable = r.status_code in (429, 500, 502, 503, 504) or code in RETRYABLE_CODES
            if retryable and i < attempts - 1:
                await asyncio.sleep(delay + random.random()); delay *= 2
                continue
            raise WhatsAppError(msg, code=code, retryable=retryable, status=r.status_code)
        raise WhatsAppError("Meta request failed after retries", retryable=True)

    async def create_template(self, name: str, language: str, category: str, body: str,
                              example_values: list[str], footer: str | None = None) -> dict:
        body_comp: dict = {"type": "BODY", "text": body}
        if example_values:
            body_comp["example"] = {"body_text": [list(example_values)]}
        components = [body_comp]
        if footer:
            components.append({"type": "FOOTER", "text": footer})
        data = await self._call("POST", f"{self.waba_id}/message_templates", json={
            "name": name, "language": language, "category": category.upper(), "components": components})
        return {"meta_id": data.get("id"), "status": data.get("status", "PENDING")}

    async def get_template_status(self, meta_id: str, created_at: datetime | None = None) -> dict:
        try:
            data = await self._call("GET", meta_id, params={"fields": "name,status,rejected_reason"})
        except WhatsAppError as e:
            if e.status == 400:
                data = await self._call("GET", meta_id, params={"fields": "name,status"})
            else:
                raise
        reason = data.get("rejected_reason")
        return {"status": data.get("status", "PENDING"), "reason": None if reason in (None, "NONE") else reason}

    async def send_template(self, to: str, name: str, language: str, params: list[str]) -> str:
        template: dict = {"name": name, "language": {"code": language}}
        if params:
            template["components"] = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]
        data = await self._call("POST", f"{self.phone_number_id}/messages", json={
            "messaging_product": "whatsapp", "recipient_type": "individual", "to": to,
            "type": "template", "template": template}, attempts=3)
        msgs = data.get("messages") or []
        if not msgs:
            raise WhatsAppError("Meta accepted the request but returned no message id")
        return msgs[0]["id"]

    async def send_text(self, to: str, text: str, phone_number_id: str = "", token: str = "") -> str:
        """Free-form reply. Meta only allows it within 24 h of the customer's last message (customer service window)."""
        headers = {"Authorization": f"Bearer {token}"} if token else None
        pnid = phone_number_id or self.phone_number_id
        body = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to, "type": "text",
                "text": {"preview_url": False, "body": text[:4096]}}
        if headers:
            r = await self.http.post(f"{self.base}/{pnid}/messages", json=body, headers=headers)
            if r.status_code >= 400:
                try:
                    err = r.json().get("error", {})
                except ValueError:
                    err = {}
                raise WhatsAppError(err.get("message") or r.text[:300], code=err.get("code"), status=r.status_code)
            data = r.json()
        else:
            data = await self._call("POST", f"{pnid}/messages", json=body, attempts=3)
        msgs = data.get("messages") or []
        if not msgs:
            raise WhatsAppError("Meta accepted the request but returned no message id")
        return msgs[0]["id"]

    async def poll_simulated_events(self) -> list[dict]:
        return []   # real statuses arrive through the webhook

    async def aclose(self):
        await self.http.aclose()


class DryRunWhatsApp:
    """Behaves like Meta without sending anything: templates approve after a delay,
    messages get delivered/read/replied on a realistic schedule."""

    dry_run = True

    def __init__(self, approval_seconds: int = 20, read_ratio: float = 0.45, reply_ratio: float = 0.08,
                 seed: int | None = None):
        self.approval_seconds = approval_seconds
        self.read_ratio = read_ratio
        self.reply_ratio = reply_ratio
        self.rng = random.Random(seed)
        self._pending: list[tuple[float, dict]] = []

    async def create_template(self, name, language, category, body, example_values, footer=None) -> dict:
        return {"meta_id": f"dry_{uuid.uuid4().hex[:10]}", "status": "PENDING"}

    async def get_template_status(self, meta_id: str, created_at: datetime | None = None) -> dict:
        created = created_at or datetime.now(timezone.utc)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - created).total_seconds()
        return {"status": "APPROVED" if age >= self.approval_seconds else "PENDING", "reason": None}

    async def send_template(self, to: str, name: str, language: str, params: list[str]) -> str:
        wamid = f"wamid.DRY{uuid.uuid4().hex[:16]}"
        t = time.monotonic()
        r = self.rng.random()
        if r < 0.03:   # a few numbers are not on WhatsApp
            self._pending.append((t + 1.5, {"id": wamid, "status": "failed", "recipient_id": to,
                                            "errors": [{"code": 131026, "title": "Message undeliverable"}]}))
            return wamid
        self._pending.append((t + self.rng.uniform(1, 3), {"id": wamid, "status": "sent", "recipient_id": to}))
        self._pending.append((t + self.rng.uniform(2, 5), {"id": wamid, "status": "delivered", "recipient_id": to}))
        if self.rng.random() < self.read_ratio:
            self._pending.append((t + self.rng.uniform(4, 12), {"id": wamid, "status": "read", "recipient_id": to}))
            if self.rng.random() < self.reply_ratio / max(self.read_ratio, 0.01):
                self._pending.append((t + self.rng.uniform(8, 18), {"reply_from": to, "text": "Interested hoon, details bhejiye"}))
        return wamid

    async def send_text(self, to: str, text: str, phone_number_id: str = "", token: str = "") -> str:
        self.sent_texts = getattr(self, "sent_texts", [])
        self.sent_texts.append({"to": to, "text": text})
        return f"wamid.DRYT{uuid.uuid4().hex[:16]}"

    async def poll_simulated_events(self) -> list[dict]:
        t = time.monotonic()
        due = [e for when, e in self._pending if when <= t]
        self._pending = [(w, e) for w, e in self._pending if w > t]
        return due

    def flush_all(self) -> list[dict]:
        """Testing helper: release every scheduled event now."""
        due = [e for _, e in sorted(self._pending, key=lambda x: x[0])]
        self._pending = []
        return due

    async def aclose(self):
        pass


_client = None


def get_whatsapp():
    global _client
    if _client is None:
        s = get_settings()
        if s.wa_dry_run:
            _client = DryRunWhatsApp(s.dry_run_approval_seconds, s.dry_run_read_ratio, s.dry_run_reply_ratio)
        else:
            _client = MetaWhatsApp(s.wa_token, s.wa_waba_id, s.wa_phone_number_id, s.wa_graph_version)
    return _client


def set_whatsapp(client) -> None:
    global _client
    _client = client
