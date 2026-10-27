"""v0.122 Cloudflare API client (official v4 REST API, documented endpoints only): token check, zones, DNS records, and
Cloudflare for SaaS custom hostnames (her domain -> Hoola's origin, SSL issued by Cloudflare). Tokens never leave the
server; errors come back in plain words. `CF_API_BASE` points tests at a fake server."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger("santosh.site")


class CfError(Exception):
    pass


def base() -> str:
    return (os.environ.get("CF_API_BASE") or "https://api.cloudflare.com/client/v4").rstrip("/")


_TRANSPORT: httpx.BaseTransport | None = None     # tests plug a MockTransport here


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


class Cloudflare:
    def __init__(self, token: str):
        if not token:
            raise CfError("Cloudflare token nahi hai.")
        self.token = token

    def _req(self, method: str, path: str, json: Any = None, params: dict | None = None) -> Any:
        try:
            with httpx.Client(timeout=30, transport=_TRANSPORT) as c:
                r = c.request(method, base() + path, json=json, params=params,
                              headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        except httpx.HTTPError as e:
            raise CfError(f"Cloudflare tak nahi pahunch paya: {e.__class__.__name__}")
        try:
            body = r.json()
        except ValueError:
            raise CfError(f"Cloudflare ka jawab samajh nahi aaya ({r.status_code}).")
        if r.status_code >= 400 or not body.get("success", False):
            errs = "; ".join(f"{e.get('code')}: {e.get('message')}" for e in body.get("errors") or []) or str(r.status_code)
            if r.status_code in (401, 403):
                raise CfError(f"Cloudflare ne mana kiya (token ki permission kam hai ya galat): {errs}")
            raise CfError(f"Cloudflare: {errs}")
        return body.get("result")

    # -------- token / zones
    def verify(self) -> dict[str, Any]:
        return self._req("GET", "/user/tokens/verify") or {}

    def zones(self, name: str = "") -> list[dict[str, Any]]:
        return self._req("GET", "/zones", params={"name": name} if name else {"per_page": 50}) or []

    def zone_for(self, domain: str) -> dict[str, Any] | None:
        """The zone that holds this name (example.co.in for shop.example.co.in)."""
        parts = domain.lower().strip(".").split(".")
        for i in range(len(parts) - 1):
            cand = ".".join(parts[i:])
            z = self.zones(cand)
            if z:
                return z[0]
        return None

    # -------- DNS records
    def records(self, zone_id: str, name: str = "", type_: str = "") -> list[dict[str, Any]]:
        params: dict[str, Any] = {"per_page": 100}
        if name:
            params["name"] = name
        if type_:
            params["type"] = type_
        return self._req("GET", f"/zones/{zone_id}/dns_records", params=params) or []

    def create_record(self, zone_id: str, rec: dict[str, Any]) -> dict[str, Any]:
        return self._req("POST", f"/zones/{zone_id}/dns_records", json=_clean(rec)) or {}

    def update_record(self, zone_id: str, rid: str, rec: dict[str, Any]) -> dict[str, Any]:
        return self._req("PATCH", f"/zones/{zone_id}/dns_records/{rid}", json=_clean(rec)) or {}

    def delete_record(self, zone_id: str, rid: str) -> None:
        self._req("DELETE", f"/zones/{zone_id}/dns_records/{rid}")

    # -------- Cloudflare for SaaS custom hostnames (on Hoola's own zone)
    def custom_hostname_create(self, zone_id: str, hostname: str) -> dict[str, Any]:
        return self._req("POST", f"/zones/{zone_id}/custom_hostnames",
                         json={"hostname": hostname, "ssl": {"method": "http", "type": "dv",
                                                             "settings": {"min_tls_version": "1.2"}}}) or {}

    def custom_hostname_get(self, zone_id: str, hid: str) -> dict[str, Any]:
        return self._req("GET", f"/zones/{zone_id}/custom_hostnames/{hid}") or {}

    def custom_hostname_find(self, zone_id: str, hostname: str) -> dict[str, Any] | None:
        res = self._req("GET", f"/zones/{zone_id}/custom_hostnames", params={"hostname": hostname}) or []
        return res[0] if res else None

    def custom_hostname_delete(self, zone_id: str, hid: str) -> None:
        self._req("DELETE", f"/zones/{zone_id}/custom_hostnames/{hid}")


def _clean(rec: dict[str, Any]) -> dict[str, Any]:
    out = {k: rec[k] for k in ("type", "name", "content", "ttl", "proxied", "priority", "comment") if k in rec and rec[k] is not None}
    out.setdefault("ttl", 1)
    if out.get("type") not in ("A", "AAAA", "CNAME"):
        out.pop("proxied", None)
    return out
