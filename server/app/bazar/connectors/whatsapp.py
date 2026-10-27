"""WhatsApp Cloud API adapter (Meta Graph API): templates, template status, template sends and text sends."""
from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from .base import ToolError


class WhatsApp:
    def __init__(self, s: Settings, client: httpx.Client | None = None):
        self.s = s
        self.client = client or httpx.Client(base_url=f"https://graph.facebook.com/{s.wa_api_version}", timeout=20)

    @property
    def configured(self) -> bool:
        return bool(self.s.wa_token and self.s.wa_phone_number_id)

    def _h(self) -> dict[str, str]:
        if not self.configured:
            raise ToolError("WhatsApp is not connected yet. Add your WhatsApp Business number in settings.")
        return {"Authorization": f"Bearer {self.s.wa_token}"}

    def create_template(self, name: str, language: str, category: str, body: str, example: list[str] | None = None) -> dict[str, Any]:
        comp: dict[str, Any] = {"type": "BODY", "text": body}
        if example:
            comp["example"] = {"body_text": [example]}
        r = self.client.post(f"/{self.s.wa_business_account_id}/message_templates", headers=self._h(),
                             json={"name": name, "language": language, "category": category, "components": [comp]})
        if r.status_code >= 400:
            raise ToolError(f"Meta rejected the template: {r.text[:200]}")
        return r.json()

    def template_status(self, name: str) -> dict[str, Any]:
        r = self.client.get(f"/{self.s.wa_business_account_id}/message_templates", headers=self._h(),
                            params={"name": name, "fields": "name,status,language,category"})
        r.raise_for_status()
        data = r.json().get("data", [])
        return data[0] if data else {"name": name, "status": "NOT_FOUND"}

    def send_template(self, to: str, name: str, language: str, params: list[str]) -> dict[str, Any]:
        tpl: dict[str, Any] = {"name": name, "language": {"code": language}}
        if params:
            tpl["components"] = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]
        r = self.client.post(f"/{self.s.wa_phone_number_id}/messages", headers=self._h(),
                             json={"messaging_product": "whatsapp", "to": to, "type": "template", "template": tpl})
        return {"to": to, "ok": r.status_code < 400, "response": r.json() if r.content else {}}

    def send_text(self, to: str, text: str) -> dict[str, Any]:
        r = self.client.post(f"/{self.s.wa_phone_number_id}/messages", headers=self._h(),
                             json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})
        return {"to": to, "ok": r.status_code < 400}
