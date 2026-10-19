"""Offline stand-ins for the SmartThings, LG ThinQ Connect and Home Connect APIs, at the HTTP level.

Used when SANTOSH_DEVICE_CLOUD_MODE=sandbox (dev, demo, tests). The real client code (paths, headers, JSON parsing)
runs unchanged against these responses, so switching to "live" only changes the transport.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from typing import Any

import httpx

_SEED: dict[str, Any] = {
    "smartthings": {
        "st-fridge-1": {"label": "Samsung Fridge", "category": "Refrigerator", "status": {
            "main": {"contactSensor": {"contact": {"value": "closed"}}},
            "cooler": {"temperatureMeasurement": {"temperature": {"value": 4, "unit": "C"}}},
            "freezer": {"temperatureMeasurement": {"temperature": {"value": -18, "unit": "C"}}}}},
        "st-washer-1": {"label": "Samsung Washer", "category": "Washer", "status": {
            "main": {"washerOperatingState": {"machineState": {"value": "stop"}, "washerJobState": {"value": "finish"},
                                              "completionTime": {"value": None}}}}},
        "st-ac-1": {"label": "Guest room AC", "category": "AirConditioner", "status": {
            "main": {"switch": {"switch": {"value": "off"}}, "airConditionerMode": {"airConditionerMode": {"value": "cool"}},
                     "thermostatCoolingSetpoint": {"coolingSetpoint": {"value": 24, "unit": "C"}},
                     "temperatureMeasurement": {"temperature": {"value": 31, "unit": "C"}},
                     "airConditionerFanMode": {"fanMode": {"value": "auto"}}}}},
    },
    "lg_thinq": {
        "lg-ac-1": {"type": "DEVICE_AIR_CONDITIONER", "alias": "LG Hall AC", "state": {
            "operation": {"airConOperationMode": "POWER_OFF"}, "airConJobMode": {"currentJobMode": "COOL"},
            "temperature": {"currentTemperature": 30, "targetTemperature": 24, "unit": "C"},
            "airFlow": {"windStrength": "AUTO"}}},
        "lg-fridge-1": {"type": "DEVICE_REFRIGERATOR", "alias": "LG Fridge", "state": {
            "temperature": [{"targetTemperature": 3, "locationName": "FRIDGE", "unit": "C"},
                            {"targetTemperature": -20, "locationName": "FREEZER", "unit": "C"}],
            "doorStatus": [{"doorState": "OPEN", "locationName": "MAIN"}]}},
    },
    "home_connect": {
        "BOSCH-WAT-1": {"type": "Washer", "name": "Bosch Washer", "brand": "Bosch",
                        "status": [{"key": "BSH.Common.Status.OperationState", "value": "BSH.Common.EnumType.OperationState.Run"}],
                        "options": [{"key": "BSH.Common.Option.RemainingProgramTime", "value": 1500, "unit": "seconds"}]},
    },
}
STATE: dict[str, Any] = {}


def reset() -> None:
    STATE.clear()
    STATE.update(copy.deepcopy(_SEED))


reset()


def _json(code: int, body: Any) -> httpx.Response:
    return httpx.Response(code, content=json.dumps(body).encode(), headers={"content-type": "application/json"})


def _auth_ok(req: httpx.Request) -> bool:
    return req.headers.get("authorization", "").startswith("Bearer ") and "expired" not in req.headers.get("authorization", "")


def _smartthings(req: httpx.Request) -> httpx.Response:
    st = STATE["smartthings"]
    p = req.url.path.removeprefix("/v1")
    if p == "/devices" and req.method == "GET":
        return _json(200, {"items": [{"deviceId": k, "label": v["label"], "name": v["label"],
                                      "components": [{"id": "main", "categories": [{"name": v["category"]}]}]}
                                     for k, v in st.items()]})
    parts = p.strip("/").split("/")
    if len(parts) == 3 and parts[0] == "devices":
        d = st.get(parts[1])
        if d is None:
            return _json(404, {"error": "not found"})
        if parts[2] == "status":
            return _json(200, {"components": d["status"]})
        if parts[2] == "commands" and req.method == "POST":
            main = d["status"]["main"]
            for c in json.loads(req.content)["commands"]:
                cap, cmd, args = c["capability"], c["command"], c.get("arguments", [])
                if cap == "switch":
                    main.setdefault("switch", {"switch": {}})["switch"]["value"] = cmd
                elif cmd == "setAirConditionerMode":
                    main["airConditionerMode"]["airConditionerMode"]["value"] = args[0]
                elif cmd == "setCoolingSetpoint":
                    main["thermostatCoolingSetpoint"]["coolingSetpoint"]["value"] = args[0]
                elif cmd == "setFanMode":
                    main["airConditionerFanMode"]["fanMode"]["value"] = args[0]
                else:
                    return _json(422, {"error": f"unsupported {cap}.{cmd}"})
            return _json(200, {"results": [{"status": "ACCEPTED"}]})
    return _json(404, {"error": "not found"})


def _lg(req: httpx.Request) -> httpx.Response:
    for h in ("x-api-key", "x-country", "x-message-id", "x-client-id"):
        if not req.headers.get(h):
            return _json(400, {"error": {"code": "1101", "message": f"missing {h}"}})
    lg = STATE["lg_thinq"]
    parts = req.url.path.strip("/").split("/")
    if parts == ["devices"]:
        return _json(200, {"messageId": req.headers["x-message-id"], "response": [
            {"deviceId": k, "deviceInfo": {"deviceType": v["type"], "alias": v["alias"], "modelName": "demo"}} for k, v in lg.items()]})
    if len(parts) == 3 and parts[0] == "devices":
        d = lg.get(parts[1])
        if d is None:
            return _json(404, {"error": {"code": "1222", "message": "Not found device"}})
        if parts[2] == "state":
            return _json(200, {"response": d["state"]})
        if parts[2] == "control" and req.method == "POST":
            body = json.loads(req.content)
            for k, v in body.items():
                d["state"].setdefault(k, {}).update(v)
            return _json(200, {"response": {}})
    return _json(404, {"error": {"code": "1222", "message": "Not found"}})


def _hc(req: httpx.Request) -> httpx.Response:
    hc = STATE["home_connect"]
    parts = req.url.path.removeprefix("/api").strip("/").split("/")
    if parts == ["homeappliances"]:
        return _json(200, {"data": {"homeappliances": [{"haId": k, "name": v["name"], "type": v["type"], "brand": v["brand"],
                                                        "connected": True} for k, v in hc.items()]}})
    if len(parts) >= 3 and parts[0] == "homeappliances":
        d = hc.get(parts[1])
        if d is None:
            return _json(404, {"error": {"key": "SDK.Error.HomeAppliance.NotFound"}})
        tail = "/".join(parts[2:])
        if tail == "status":
            return _json(200, {"data": {"status": d["status"]}})
        if tail == "settings":
            return _json(200, {"data": {"settings": d.get("settings", [])}})
        if tail == "programs/active":
            if "options" not in d:
                return _json(404, {"error": {"key": "SDK.Error.NoProgramActive"}})
            return _json(200, {"data": {"key": "LaundryCare.Washer.Program.Cotton", "options": d["options"]}})
    return _json(404, {"error": {"key": "SDK.Error.NotFound"}})


def _token(req: httpx.Request) -> httpx.Response:
    form = dict(x.split("=", 1) for x in req.content.decode().split("&") if "=" in x)
    if form.get("grant_type") in ("authorization_code", "refresh_token"):
        stamp = dt.datetime.now().strftime("%H%M%S%f")
        return _json(200, {"access_token": f"sandbox-access-{stamp}", "refresh_token": "sandbox-refresh",
                           "expires_in": 86400, "token_type": "bearer"})
    return _json(400, {"error": "invalid_grant"})


def handler(req: httpx.Request) -> httpx.Response:
    host = req.url.host
    if req.url.path.endswith("/oauth/token"):
        return _token(req)
    if not _auth_ok(req):
        return _json(401, {"error": "unauthorized"})
    if host == "api.smartthings.com":
        return _smartthings(req)
    if host.endswith("lgthinq.com"):
        return _lg(req)
    if host == "api.home-connect.com":
        return _hc(req)
    return _json(404, {"error": "unknown host"})


def transport() -> httpx.MockTransport:
    return httpx.MockTransport(handler)
