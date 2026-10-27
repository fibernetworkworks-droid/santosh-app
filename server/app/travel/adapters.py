"""Official partner fare sources, read-only, with HER own keys (typed in the app, sealed with the bazar vault, never shown to the
model). Hoola never scrapes IRCTC / airline / OTA sites: without a partner key she pastes the quotes she sees, or opens the links.

Adapter contract: `search(creds, query) -> list[option dict]` with the same keys as rules.parse_quotes (mode, name, code,
depart, arrive, duration_min, price_paise, ...). Prices come only from the partner's answer.

Amadeus for Developers "Flight Offers Search" (POST /v1/security/oauth2/token client_credentials, GET /v2/shopping/flight-offers)
is the first adapter. IRCTC has no public API for third parties: train data stays links + what she pastes (authorised agents /
B2B partners get access only through IRCTC's own agreements)."""
from __future__ import annotations

from typing import Any

import httpx

from . import rules as R

_TRANSPORT: httpx.BaseTransport | None = None


def set_transport(t: httpx.BaseTransport | None) -> None:
    """Tests plug a MockTransport here."""
    global _TRANSPORT
    _TRANSPORT = t


def _client() -> httpx.Client:
    return httpx.Client(timeout=20, transport=_TRANSPORT) if _TRANSPORT else httpx.Client(timeout=20)


class PartnerError(Exception):
    pass


class Amadeus:
    name = "amadeus"
    label = "Amadeus (flights)"
    modes = ("flight",)
    HOSTS = {"test": "https://test.api.amadeus.com", "prod": "https://api.amadeus.com"}

    def _token(self, c: httpx.Client, base: str, creds: dict[str, str]) -> str:
        r = c.post(f"{base}/v1/security/oauth2/token", data={"grant_type": "client_credentials",
                                                             "client_id": creds.get("key", ""), "client_secret": creds.get("secret", "")})
        if r.status_code != 200:
            raise PartnerError("Amadeus ne key nahi maani (key / secret dobara app mein daaliye).")
        return str(r.json().get("access_token") or "")

    def verify(self, creds: dict[str, str]) -> bool:
        base = self.HOSTS.get(creds.get("env") or "test", self.HOSTS["test"])
        with _client() as c:
            return bool(self._token(c, base, creds))

    def search(self, creds: dict[str, str], q: dict[str, Any]) -> list[dict[str, Any]]:
        base = self.HOSTS.get(creds.get("env") or "test", self.HOSTS["test"])
        orig, dest, day = (q.get("origin_code") or "").upper(), (q.get("dest_code") or "").upper(), q.get("day") or ""
        if not (len(orig) == 3 and len(dest) == 3 and len(day) == 10):
            raise PartnerError("Flight dhoondhne ke liye airport code (jaise BOM, DEL) aur date (YYYY-MM-DD) chahiye.")
        with _client() as c:
            tok = self._token(c, base, creds)
            r = c.get(f"{base}/v2/shopping/flight-offers", headers={"Authorization": f"Bearer {tok}"},
                      params={"originLocationCode": orig, "destinationLocationCode": dest, "departureDate": day,
                              "adults": max(1, int(q.get("adults") or 1)), "currencyCode": "INR", "max": 10, "nonStop": "false"})
            if r.status_code != 200:
                raise PartnerError(f"Amadeus se jawab nahi aaya ({r.status_code}).")
            data = r.json()
        carriers = ((data.get("dictionaries") or {}).get("carriers") or {})
        out = []
        for off in (data.get("data") or [])[:10]:
            try:
                it = (off.get("itineraries") or [])[0]
                segs = it.get("segments") or []
                first, last = segs[0], segs[-1]
                total = (off.get("price") or {}).get("grandTotal") or (off.get("price") or {}).get("total")
                cur = (off.get("price") or {}).get("currency") or ""
                price = int(round(float(total) * 100)) if total is not None and cur == "INR" else None
                code = f"{first.get('carrierCode', '')} {first.get('number', '')}".strip()
                name = carriers.get(first.get("carrierCode", ""), first.get("carrierCode", "")).title()
                stops = len(segs) - 1
                out.append({"mode": "flight", "name": f"{name} {code}" + (f" ({stops} stop)" if stops else " (non-stop)"),
                            "code": code, "depart": str(first.get("departure", {}).get("at", ""))[11:16],
                            "arrive": str(last.get("arrival", {}).get("at", ""))[11:16],
                            "duration_min": R.minutes_of(it.get("duration") or ""), "price_paise": price,
                            "rating": None, "stars": None, "per_night": False, "refundable": None, "cls": "",
                            "raw": f"Amadeus offer {off.get('id', '')} {total or ''} {cur}".strip()})
            except (IndexError, KeyError, TypeError, ValueError):
                continue
        return out


ADAPTERS: dict[str, Any] = {"amadeus": Amadeus()}


def get(name: str):
    a = ADAPTERS.get((name or "").lower())
    if a is None:
        raise PartnerError("Yeh partner abhi Hoola mein nahi hai. Abhi: " + ", ".join(ADAPTERS))
    return a
