"""Official appliance clouds, behind one normalised interface.

- Samsung SmartThings REST API (OAuth 2.0)        https://developer.smartthings.com/docs/api/public
- LG ThinQ Connect API (personal access token)     https://smartsolution.developer.lge.com/  (thinqconnect SDK)
- Bosch/Siemens Home Connect API (OAuth 2.0)       https://api-docs.home-connect.com/

Normalised device: {"id", "name", "kind": ac|fridge|washer|tv|other, "provider", "online"}
Normalised status:
  ac      {"power", "mode", "temp_c", "room_c", "fan"}
  fridge  {"fridge_c", "freezer_c", "door_open"}
  washer  {"state": running|finished|paused|idle|error, "remaining_min"}

Santosh only *controls* ACs through these clouds. Fridges and washers are read-only (temperature, door, cycle done):
no remote start, no fridge setpoint or power changes.

Field names follow each provider's public docs/SDK; confirm them against a live device of each type before launch.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from .base import ToolError

PROVIDERS = {
    "smartthings": "Samsung SmartThings",
    "lg_thinq": "LG ThinQ",
    "home_connect": "Bosch/Siemens Home Connect",
}
TIMEOUT = 15.0


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Token:
    """Stored (encrypted) as JSON: {"access_token", "refresh_token", "expires_at"} or a bare LG PAT."""

    def __init__(self, access: str, refresh: str = "", expires_at: str = ""):
        self.access, self.refresh, self.expires_at = access, refresh, expires_at

    @classmethod
    def parse(cls, raw: str) -> Token:
        try:
            d = json.loads(raw)
            if isinstance(d, dict) and d.get("access_token"):
                return cls(d["access_token"], d.get("refresh_token", ""), d.get("expires_at", ""))
        except ValueError:
            pass
        return cls(raw)

    def dump(self) -> str:
        return json.dumps({"access_token": self.access, "refresh_token": self.refresh, "expires_at": self.expires_at})

    def expired(self) -> bool:
        if not self.expires_at:
            return False
        return _now() >= dt.datetime.fromisoformat(self.expires_at) - dt.timedelta(minutes=2)

    @classmethod
    def from_oauth(cls, body: dict[str, Any], old_refresh: str = "") -> Token:
        exp = (_now() + dt.timedelta(seconds=int(body.get("expires_in", 3600)))).isoformat()
        return cls(body["access_token"], body.get("refresh_token") or old_refresh, exp)


# ------------------------------------------------------------------ base
class CloudClient:
    provider = ""
    base_url = ""

    def __init__(self, token: Token, transport: httpx.BaseTransport | None = None,
                 on_token: Callable[[Token], None] | None = None, settings: Any = None):
        self.token = token
        self.transport = transport
        self.on_token = on_token
        self.settings = settings
        self._http = httpx.Client(base_url=self.base_url, timeout=TIMEOUT, transport=transport)

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token.access}", "Accept": "application/json"}

    def refresh(self) -> bool:
        return False

    def _req(self, method: str, path: str, **kw: Any) -> Any:
        if self.token.expired():
            self.refresh()
        r = self._http.request(method, path, headers=self.headers(), **kw)
        if r.status_code == 401 and self.refresh():
            r = self._http.request(method, path, headers=self.headers(), **kw)
        if r.status_code == 401:
            raise ToolError(f"Your {PROVIDERS[self.provider]} link has expired. Please link the account again.")
        if r.status_code == 429:
            raise ToolError(f"{PROVIDERS[self.provider]} says too many requests. Try again in a minute.")
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise ToolError(f"{PROVIDERS[self.provider]} returned an error ({r.status_code}).")
        return r.json() if r.content else {}

    # interface
    def list_devices(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def status(self, device_id: str, kind: str) -> dict[str, Any]:
        raise NotImplementedError

    def set_ac(self, device_id: str, power: bool, mode: str | None = None, temp_c: int | None = None,
               fan: str | None = None) -> None:
        raise NotImplementedError


# ------------------------------------------------------------------ SmartThings
ST_KIND = {"AirConditioner": "ac", "Refrigerator": "fridge", "Washer": "washer", "Television": "tv",
           "Dryer": "washer", "WasherDryer": "washer"}
ST_FAN = {"auto": "auto", "low": "low", "medium": "medium", "high": "high"}


class SmartThings(CloudClient):
    provider = "smartthings"
    base_url = "https://api.smartthings.com/v1"
    token_url = "https://auth-global.api.smartthings.com/oauth/token"
    authorize_url = "https://api.smartthings.com/oauth/authorize"
    scopes = "r:devices:* x:devices:*"

    def refresh(self) -> bool:
        s = self.settings
        if not (self.token.refresh and s and s.smartthings_client_id):
            return False
        c = httpx.Client(transport=self.transport, timeout=TIMEOUT)
        r = c.post(self.token_url, data={"grant_type": "refresh_token", "refresh_token": self.token.refresh,
                                         "client_id": s.smartthings_client_id},
                   auth=(s.smartthings_client_id, s.smartthings_client_secret))
        if r.status_code != 200:
            return False
        self.token = Token.from_oauth(r.json(), self.token.refresh)
        if self.on_token:
            self.on_token(self.token)
        return True

    def list_devices(self) -> list[dict[str, Any]]:
        body = self._req("GET", "/devices") or {}
        out = []
        for d in body.get("items", []):
            cats = [c.get("name") for comp in d.get("components", []) for c in comp.get("categories", [])]
            kind = next((ST_KIND[c] for c in cats if c in ST_KIND), "other")
            out.append({"id": d["deviceId"], "name": d.get("label") or d.get("name") or "Samsung device", "kind": kind,
                        "provider": self.provider, "online": True})
        return out

    def status(self, device_id: str, kind: str) -> dict[str, Any]:
        body = self._req("GET", f"/devices/{device_id}/status")
        if body is None:
            raise ToolError("SmartThings can't find this device any more.")
        comps = body.get("components", {})
        main = comps.get("main", {})

        def v(comp: dict[str, Any], cap: str, attr: str) -> Any:
            return ((comp.get(cap) or {}).get(attr) or {}).get("value")

        if kind == "ac":
            return {"power": v(main, "switch", "switch") == "on", "mode": v(main, "airConditionerMode", "airConditionerMode"),
                    "temp_c": v(main, "thermostatCoolingSetpoint", "coolingSetpoint"),
                    "room_c": v(main, "temperatureMeasurement", "temperature"),
                    "fan": v(main, "airConditionerFanMode", "fanMode")}
        if kind == "fridge":
            fridge_c = v(comps.get("cooler", {}), "temperatureMeasurement", "temperature")
            freezer_c = v(comps.get("freezer", {}), "temperatureMeasurement", "temperature")
            door = v(main, "contactSensor", "contact")
            return {"fridge_c": fridge_c, "freezer_c": freezer_c, "door_open": door == "open"}
        if kind == "washer":
            machine = v(main, "washerOperatingState", "machineState")
            job = v(main, "washerOperatingState", "washerJobState")
            done = v(main, "washerOperatingState", "completionTime")
            state = ("running" if machine == "run" else "paused" if machine == "pause"
                     else "finished" if job in ("finish", "finished") else "idle")
            remaining = None
            if state == "running" and done:
                try:
                    t = dt.datetime.fromisoformat(str(done).replace("Z", "+00:00")).replace(tzinfo=None)
                    remaining = max(0, int((t - _now()).total_seconds() // 60))
                except ValueError:
                    remaining = None
            return {"state": state, "remaining_min": remaining}
        return {"power": v(main, "switch", "switch") == "on"}

    def _cmd(self, device_id: str, commands: list[dict[str, Any]]) -> None:
        body = self._req("POST", f"/devices/{device_id}/commands", json={"commands": commands})
        if body is None:
            raise ToolError("SmartThings can't find this device any more.")

    def set_ac(self, device_id: str, power: bool, mode: str | None = None, temp_c: int | None = None,
               fan: str | None = None) -> None:
        cmds: list[dict[str, Any]] = [{"component": "main", "capability": "switch", "command": "on" if power else "off"}]
        if power:
            if mode:
                cmds.append({"component": "main", "capability": "airConditionerMode", "command": "setAirConditionerMode",
                             "arguments": [mode]})
            if temp_c is not None:
                cmds.append({"component": "main", "capability": "thermostatCoolingSetpoint", "command": "setCoolingSetpoint",
                             "arguments": [temp_c]})
            if fan:
                cmds.append({"component": "main", "capability": "airConditionerFanMode", "command": "setFanMode",
                             "arguments": [ST_FAN.get(fan, "auto")]})
        self._cmd(device_id, cmds)


# ------------------------------------------------------------------ LG ThinQ Connect
LG_KIND = {"DEVICE_AIR_CONDITIONER": "ac", "DEVICE_REFRIGERATOR": "fridge", "DEVICE_KIMCHI_REFRIGERATOR": "fridge",
           "DEVICE_WASHER": "washer", "DEVICE_WASHTOWER": "washer", "DEVICE_WASHTOWER_WASHER": "washer",
           "DEVICE_DRYER": "washer"}
LG_MODE_IN = {"COOL": "cool", "AIR_DRY": "dry", "FAN": "fan", "AUTO": "auto", "HEAT": "heat"}
LG_MODE_OUT = {v: k for k, v in LG_MODE_IN.items()}
LG_FAN_OUT = {"auto": "AUTO", "low": "LOW", "medium": "MID", "high": "HIGH"}
LG_WASH = {"RUNNING": "running", "RINSING": "running", "SPINNING": "running", "DRYING": "running", "STEAM_SOFTENING": "running",
           "COOL_DOWN": "running", "DETECTING": "running", "END": "finished", "PAUSE": "paused", "POWER_OFF": "idle",
           "INITIAL": "idle", "SLEEP": "idle", "ERROR": "error"}
# Public API key shipped in LG's official thinqconnect SDK for ThinQ Connect clients.
LG_API_KEY = "v6GFvkweNo7DK7yD3ylIZ9w52aKBU0eJ7wLXkSR3"


class LgThinq(CloudClient):
    provider = "lg_thinq"

    def __init__(self, token: Token, transport: httpx.BaseTransport | None = None,
                 on_token: Callable[[Token], None] | None = None, settings: Any = None):
        region = getattr(settings, "lg_thinq_region", "kic") or "kic"
        self.base_url = f"https://api-{region}.lgthinq.com"
        super().__init__(token, transport, on_token, settings)

    def headers(self) -> dict[str, str]:
        s = self.settings
        msg = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")
        return {"Authorization": f"Bearer {self.token.access}", "x-country": getattr(s, "lg_thinq_country", "IN") or "IN",
                "x-message-id": msg, "x-client-id": getattr(s, "lg_thinq_client_id", "") or "santosh-coworker",
                "x-api-key": LG_API_KEY, "x-service-phase": "OP", "Content-Type": "application/json"}

    def list_devices(self) -> list[dict[str, Any]]:
        body = self._req("GET", "/devices") or {}
        out = []
        for d in body.get("response", []) or []:
            info = d.get("deviceInfo", {})
            out.append({"id": d["deviceId"], "name": info.get("alias") or info.get("modelName") or "LG device",
                        "kind": LG_KIND.get(info.get("deviceType", ""), "other"), "provider": self.provider,
                        "online": True})
        return out

    def status(self, device_id: str, kind: str) -> dict[str, Any]:
        body = self._req("GET", f"/devices/{device_id}/state")
        if body is None:
            raise ToolError("LG ThinQ can't find this device any more.")
        st = body.get("response", body)
        if kind == "ac":
            t = st.get("temperature", {}) or {}
            return {"power": (st.get("operation", {}) or {}).get("airConOperationMode") == "POWER_ON",
                    "mode": LG_MODE_IN.get((st.get("airConJobMode", {}) or {}).get("currentJobMode", ""), None),
                    "temp_c": t.get("targetTemperature"), "room_c": t.get("currentTemperature"),
                    "fan": {v: k for k, v in LG_FAN_OUT.items()}.get((st.get("airFlow", {}) or {}).get("windStrength", ""))}
        if kind == "fridge":
            temps = st.get("temperature", []) or []
            temps = temps if isinstance(temps, list) else [temps]
            by = {x.get("locationName"): x.get("targetTemperature") for x in temps}
            doors = st.get("doorStatus", []) or []
            doors = doors if isinstance(doors, list) else [doors]
            return {"fridge_c": by.get("FRIDGE"), "freezer_c": by.get("FREEZER"),
                    "door_open": any(x.get("doorState") == "OPEN" for x in doors)}
        if kind == "washer":
            item = st[0] if isinstance(st, list) and st else st
            cur = ((item or {}).get("runState", {}) or {}).get("currentState", "")
            timer = (item or {}).get("timer", {}) or {}
            remaining = None
            if "remainHour" in timer or "remainMinute" in timer:
                remaining = int(timer.get("remainHour", 0)) * 60 + int(timer.get("remainMinute", 0))
            return {"state": LG_WASH.get(cur, "idle"), "remaining_min": remaining}
        return {}

    def _control(self, device_id: str, payload: dict[str, Any]) -> None:
        body = self._req("POST", f"/devices/{device_id}/control", json=payload)
        if body is None:
            raise ToolError("LG ThinQ can't find this device any more.")

    def set_ac(self, device_id: str, power: bool, mode: str | None = None, temp_c: int | None = None,
               fan: str | None = None) -> None:
        self._control(device_id, {"operation": {"airConOperationMode": "POWER_ON" if power else "POWER_OFF"}})
        if not power:
            return
        if mode and mode in LG_MODE_OUT:
            self._control(device_id, {"airConJobMode": {"currentJobMode": LG_MODE_OUT[mode]}})
        if temp_c is not None:
            self._control(device_id, {"temperature": {"targetTemperature": temp_c, "unit": "C"}})
        if fan:
            self._control(device_id, {"airFlow": {"windStrength": LG_FAN_OUT.get(fan, "AUTO")}})


# ------------------------------------------------------------------ Home Connect
HC_KIND = {"Washer": "washer", "WasherDryer": "washer", "Dryer": "washer", "Dishwasher": "washer",
           "Refrigerator": "fridge", "FridgeFreezer": "fridge", "Freezer": "fridge"}
HC_OP = {"Run": "running", "Finished": "finished", "Pause": "paused", "Ready": "idle", "Inactive": "idle",
         "DelayedStart": "running", "ActionRequired": "paused", "Aborting": "idle", "Error": "error"}


class HomeConnect(CloudClient):
    provider = "home_connect"
    base_url = "https://api.home-connect.com/api"
    token_url = "https://api.home-connect.com/security/oauth/token"
    authorize_url = "https://api.home-connect.com/security/oauth/authorize"
    scopes = "IdentifyAppliance Monitor Settings"  # read-only: no Control scope requested

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token.access}", "Accept": "application/vnd.bsh.sdk.v1+json"}

    def refresh(self) -> bool:
        s = self.settings
        if not (self.token.refresh and s and s.home_connect_client_id):
            return False
        c = httpx.Client(transport=self.transport, timeout=TIMEOUT)
        r = c.post(self.token_url, data={"grant_type": "refresh_token", "refresh_token": self.token.refresh,
                                         "client_id": s.home_connect_client_id,
                                         "client_secret": s.home_connect_client_secret})
        if r.status_code != 200:
            return False
        self.token = Token.from_oauth(r.json(), self.token.refresh)
        if self.on_token:
            self.on_token(self.token)
        return True

    def list_devices(self) -> list[dict[str, Any]]:
        body = self._req("GET", "/homeappliances") or {}
        return [{"id": a["haId"], "name": a.get("name") or f"{a.get('brand', '')} {a.get('type', '')}".strip(),
                 "kind": HC_KIND.get(a.get("type", ""), "other"), "provider": self.provider,
                 "online": bool(a.get("connected", True))}
                for a in (body.get("data", {}) or {}).get("homeappliances", [])]

    @staticmethod
    def _kv(items: list[dict[str, Any]]) -> dict[str, Any]:
        return {i.get("key"): i.get("value") for i in items}

    def status(self, device_id: str, kind: str) -> dict[str, Any]:
        body = self._req("GET", f"/homeappliances/{device_id}/status")
        if body is None:
            raise ToolError("Home Connect can't find this appliance any more.")
        st = self._kv((body.get("data", {}) or {}).get("status", []))
        if kind == "washer":
            op = str(st.get("BSH.Common.Status.OperationState", "")).rsplit(".", 1)[-1]
            state = HC_OP.get(op, "idle")
            remaining = None
            if state == "running":
                prog = self._req("GET", f"/homeappliances/{device_id}/programs/active")
                if prog:
                    opts = self._kv((prog.get("data", {}) or {}).get("options", []))
                    secs = opts.get("BSH.Common.Option.RemainingProgramTime")
                    remaining = int(secs) // 60 if secs is not None else None
            return {"state": state, "remaining_min": remaining}
        if kind == "fridge":
            door_vals = [v for k, v in st.items() if k and (k.startswith("Refrigeration.Common.Status.Door") or k == "BSH.Common.Status.DoorState")]
            settings = self._req("GET", f"/homeappliances/{device_id}/settings") or {}
            s = self._kv((settings.get("data", {}) or {}).get("settings", []))
            return {"fridge_c": s.get("Refrigeration.FridgeFreezer.Setting.SetpointTemperatureRefrigerator"),
                    "freezer_c": s.get("Refrigeration.FridgeFreezer.Setting.SetpointTemperatureFreezer"),
                    "door_open": any(str(v).endswith(".Open") for v in door_vals)}
        return {}

    def set_ac(self, device_id: str, power: bool, mode: str | None = None, temp_c: int | None = None,
               fan: str | None = None) -> None:
        raise ToolError("Santosh only reads Home Connect appliances (washer done, fridge door and temperature).")


CLIENTS: dict[str, type[CloudClient]] = {"smartthings": SmartThings, "lg_thinq": LgThinq, "home_connect": HomeConnect}


def authorize_url(provider: str, settings: Any, state: str) -> str:
    redirect = f"{settings.public_base_url.rstrip('/')}/v1/oauth/callback/{provider}"
    if provider == "smartthings":
        if not settings.smartthings_client_id:
            raise ToolError("SmartThings linking is not set up yet (SANTOSH_SMARTTHINGS_CLIENT_ID).")
        q = {"client_id": settings.smartthings_client_id, "response_type": "code", "redirect_uri": redirect,
             "scope": SmartThings.scopes, "state": state}
        return SmartThings.authorize_url + "?" + urlencode(q)
    if provider == "home_connect":
        if not settings.home_connect_client_id:
            raise ToolError("Home Connect linking is not set up yet (SANTOSH_HOME_CONNECT_CLIENT_ID).")
        q = {"client_id": settings.home_connect_client_id, "response_type": "code", "redirect_uri": redirect,
             "scope": HomeConnect.scopes, "state": state}
        return HomeConnect.authorize_url + "?" + urlencode(q)
    if provider == "lg_thinq":
        # ThinQ Connect personal access tokens: the user creates one and pastes it in the app.
        return "https://connect-pat.lgthinq.com"
    raise ToolError(f"Unknown provider {provider}")


def exchange_code(provider: str, settings: Any, code: str, transport: httpx.BaseTransport | None = None) -> Token:
    redirect = f"{settings.public_base_url.rstrip('/')}/v1/oauth/callback/{provider}"
    c = httpx.Client(transport=transport, timeout=TIMEOUT)
    if provider == "smartthings":
        r = c.post(SmartThings.token_url, data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect,
                                                "client_id": settings.smartthings_client_id},
                   auth=(settings.smartthings_client_id, settings.smartthings_client_secret))
    elif provider == "home_connect":
        r = c.post(HomeConnect.token_url, data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect,
                                                "client_id": settings.home_connect_client_id,
                                                "client_secret": settings.home_connect_client_secret})
    else:
        raise ToolError(f"{provider} does not use OAuth codes")
    if r.status_code != 200:
        raise ToolError(f"{PROVIDERS[provider]} did not accept the sign-in ({r.status_code}). Please try again.")
    return Token.from_oauth(r.json())
