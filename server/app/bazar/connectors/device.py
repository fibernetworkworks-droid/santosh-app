"""Home devices executor (v0.3).

Four routes, all official:
1. Bluetooth speaker  — the phone's media session (play/pause/next/volume, play-from-search). Channel ``phone_media``.
2. Smart TV           — the phone acts as a Bluetooth keyboard/remote (Android BluetoothHidDevice) + DIAL on Wi-Fi
                        to open YouTube/Netflix. Channel ``bt_hid``.
3. AC (any remote)    — the phone's IR blaster (Android ConsumerIrManager). Channel ``ir``.
4. Appliance clouds   — Samsung SmartThings, LG ThinQ Connect, Bosch/Siemens Home Connect. Channel ``cloud``.

Routes 1–3 run on the phone: the server builds the exact command (HID usages, IR pattern) and the phone executes it,
then reports back to ``POST /api/bazar/devices/commands/{id}/result``.

Safety: AC temperature is kept between 20 and 28 °C (24 °C default). Fridges and washers are read-only. No device
is ever switched on remotely for heating/washing, and fridge power is never touched.
"""
from __future__ import annotations

import re
from typing import Any

import httpx
from sqlalchemy import select

from ..db import Connection, Device, DeviceCommand
from ..packs.registry import Pack
from ..security import vault
from . import device_hid as hid
from . import device_ir as ir
from .base import Ctx, ToolError, ToolSpec
from .device_cloud import CLIENTS, PROVIDERS, CloudClient, Token

MEDIA_KEYS = {"play": "PLAY", "pause": "PAUSE", "resume": "PLAY", "next": "NEXT", "previous": "PREVIOUS", "stop": "STOP",
              "play_pause": "PLAY_PAUSE"}
# v0.126 music apps she can name; play happens on her phone through Android's "play from search" (no app API, no limits)
MUSIC_APPS = {
    "spotify": ("com.spotify.music", "Spotify", "spotify:search:{q}"),
    "youtube_music": ("com.google.android.apps.youtube.music", "YouTube Music", "https://music.youtube.com/search?q={q}"),
    "jiosaavn": ("com.jio.media.jiobeats", "JioSaavn", ""),
    "wynk": ("com.bsbportal.music", "Wynk Music", ""),
    "gaana": ("com.gaana", "Gaana", ""),
    "amazon_music": ("com.amazon.mp3", "Amazon Music", ""),
    "apple_music": ("com.apple.android.music", "Apple Music", ""),
}
MUSIC_ALIASES = {"spotify": "spotify", "spotyfy": "spotify", "spotifi": "spotify", "youtube music": "youtube_music",
                 "yt music": "youtube_music", "youtube_music": "youtube_music", "jiosaavn": "jiosaavn", "saavn": "jiosaavn",
                 "jio saavn": "jiosaavn", "wynk": "wynk", "gaana": "gaana", "gana": "gaana", "amazon music": "amazon_music",
                 "amazon_music": "amazon_music", "apple music": "apple_music", "apple_music": "apple_music"}
MUSIC_KINDS = ("song", "artist", "album", "playlist")


def music_app(name: str) -> str:
    """'' = her phone's default music app; else a MUSIC_APPS key (unknown names raise)."""
    n = re.sub(r"\s+", " ", str(name or "").lower().replace("-", " ")).strip()
    if n in ("", "any", "default", "phone"):
        return ""
    if n in MUSIC_ALIASES:
        return MUSIC_ALIASES[n]
    raise ToolError("Yeh music app main nahi jaanta. Chal sakte hain: " + ", ".join(v[1] for v in MUSIC_APPS.values()) + ".")


FRIDGE_WARM_C = 8

# Safety tier 4 (never): Santosh does not switch heaters/heavy loads or start/stop fridges, washers, ovens, locks.
# Geysers need a 16A smart plug with an auto-off timer (not built yet), so they are refused too.
UNSAFE = re.compile(r"\b(geyser|gizer|water heater|heater|oven|microwave|induction|cooktop|stove|chulha|iron|"
                    r"fridge|refrigerator|freezer|washing|washer|dryer|lock|camera)\b", re.I)


def refuse_unsafe(tool: str, args: dict[str, Any]) -> None:
    """Server-side guard for every control tool; the model's wording can't get around it."""
    if tool in ("device_status", "ac_status", "sync_devices", "media", "volume"):
        return
    words = " ".join(str(v) for k, v in (args or {}).items() if k in ("device", "app", "query", "kind") and v is not None)
    m = UNSAFE.search(words)
    if tool in ("tv_keys", "tv_open_app", "tv_search", "tv_youtube"):
        return  # TV search words ("washing machine review") are just text typed on the TV
    if m or str((args or {}).get("kind", "")) in ("fridge", "washer"):
        what = m.group(1).lower() if m else "that appliance"
        raise ToolError(f"For safety Santosh only reads {what} status; it never switches it on/off or changes it. "
                        "Use the brand's own app for that.")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def cloud_transport(settings: Any) -> httpx.BaseTransport | None:
    if settings.device_cloud_mode == "sandbox":
        from .device_sandbox import transport
        return transport()
    return None


def cloud_client(ctx: Ctx, provider: str) -> CloudClient:
    conn = ctx.session.scalars(select(Connection).where(Connection.user_id == ctx.user.id, Connection.provider == provider,
                                                        Connection.status == "active")).first()
    if conn is None:
        raise ToolError(f"Link your {PROVIDERS[provider]} account first (Santosh app › Ghar › Link {PROVIDERS[provider]}).")

    def save(tok: Token) -> None:
        conn.token_enc = vault().seal(tok.dump())

    return CLIENTS[provider](Token.parse(vault().open(conn.token_enc)), transport=cloud_transport(ctx.settings),
                             on_token=save, settings=ctx.settings)


def describe_status(dev: Device, st: dict[str, Any]) -> str:
    if dev.kind == "ac":
        if not st.get("power"):
            room = f" Room is {st['room_c']}°C." if st.get("room_c") is not None else ""
            return f"{dev.name} is off.{room}"
        room = f", room {st['room_c']}°C" if st.get("room_c") is not None else ""
        return f"{dev.name} is on: {st.get('mode') or 'cool'} at {st.get('temp_c')}°C{room}."
    if dev.kind == "fridge":
        parts = []
        if st.get("fridge_c") is not None:
            parts.append(f"fridge {st['fridge_c']}°C")
        if st.get("freezer_c") is not None:
            parts.append(f"freezer {st['freezer_c']}°C")
        door = "Door is OPEN — please close it." if st.get("door_open") else "Door is closed."
        warm = " It's warmer than it should be (keep the fridge at 1–5°C)." if (st.get("fridge_c") or 0) > FRIDGE_WARM_C else ""
        return f"{dev.name}: {', '.join(parts) or 'temperature not shared by this model'}. {door}{warm}"
    if dev.kind == "washer":
        s = st.get("state")
        if s == "running":
            left = f" About {st['remaining_min']} min left." if st.get("remaining_min") is not None else ""
            return f"{dev.name} is still running.{left}"
        if s == "finished":
            return f"{dev.name}: washing is done. Clothes are ready to take out."
        if s == "paused":
            return f"{dev.name} is paused."
        if s == "error":
            return f"{dev.name} is showing an error. Please check the machine."
        return f"{dev.name} is idle."
    return f"{dev.name}: {st}"


class DeviceExecutor:
    name = "device"

    # ------------------------------------------------------------------ tool specs
    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        ch = pack.config["channel"]
        dev = {"type": "string", "description": "Device name or room, e.g. 'bedroom AC'. Optional if there is only one."}
        if ch == "phone_media":
            return [
                ToolSpec("media", "Control music on the phone and the Bluetooth speaker connected to it. action: play, pause, "
                         "next, previous, stop. Give query to start specific songs (e.g. 'Arijit Singh'); app = which music app "
                         "(spotify, youtube_music, jiosaavn, wynk, gaana, amazon_music, apple_music), kind = song / artist / "
                         "album / playlist.",
                         {"type": "object", "properties": {"action": {"type": "string", "enum": list(MEDIA_KEYS)},
                                                           "query": {"type": "string"},
                                                           "app": {"type": "string", "enum": list(MUSIC_APPS)},
                                                           "kind": {"type": "string", "enum": list(MUSIC_KINDS)}},
                          "required": ["action"]}, 1),
                ToolSpec("volume", "Change speaker volume: direction up/down with steps, or an exact percent.",
                         {"type": "object", "properties": {"direction": {"type": "string", "enum": ["up", "down"]},
                                                           "steps": {"type": "integer"}, "percent": {"type": "integer"}}}, 1),
            ]
        if ch == "bt_hid":
            return [
                ToolSpec("tv_keys", "Press TV remote keys: " + ", ".join(hid.TV_KEYS) + ". repeat for many presses, "
                         "hold_ms for a long press.",
                         {"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}},
                                                           "repeat": {"type": "integer"}, "hold_ms": {"type": "integer"},
                                                           "device": dev},
                          "required": ["keys"]}, 1),
                ToolSpec("tv_channel", "Go to a channel number on the TV (types the digits, then OK).",
                         {"type": "object", "properties": {"number": {"type": "string"}, "device": dev}, "required": ["number"]}, 1),
                ToolSpec("tv_open_app", "Open an app on the TV: youtube, netflix, hotstar, prime video, zee5, sonyliv, spotify.",
                         {"type": "object", "properties": {"app": {"type": "string"}, "device": dev}, "required": ["app"]}, 1),
                ToolSpec("tv_search", "Search on the TV (opens search and types the words).",
                         {"type": "object", "properties": {"query": {"type": "string"}, "device": dev}, "required": ["query"]}, 1),
                ToolSpec("tv_youtube", "Play one YouTube video on the TV (video_id = 11-character id, title for the fallback search).",
                         {"type": "object", "properties": {"video_id": {"type": "string"}, "title": {"type": "string"},
                                                           "device": dev}, "required": ["video_id"]}, 1),
            ]
        if ch == "ir":
            return [
                ToolSpec("set_ac", "Control an AC through the phone's IR blaster. power on/off, temp_c (20–28), mode "
                         "(cool, dry, fan, auto), fan (auto, low, medium, high), or delta (+1 / -1 degrees).",
                         {"type": "object", "properties": {"device": dev, "power": {"type": "boolean"},
                                                           "temp_c": {"type": "integer"}, "delta": {"type": "integer"},
                                                           "mode": {"type": "string", "enum": list(ir.MODES)},
                                                           "fan": {"type": "string", "enum": list(ir.FANS)}}}, 1),
                ToolSpec("ac_status", "What Santosh last set on this AC (IR can't read the AC back).",
                         {"type": "object", "properties": {"device": dev}}, 0),
            ]
        if ch == "cloud":
            specs = [
                ToolSpec("sync_devices", f"Fetch the user's appliances from {pack.name}.", {"type": "object", "properties": {}}, 0),
                ToolSpec("device_status", "Read an appliance: AC state, fridge temperature and door, washer cycle and time left.",
                         {"type": "object", "properties": {"device": dev, "kind": {"type": "string", "enum": ["ac", "fridge", "washer"]}}}, 0),
            ]
            if pack.config.get("ac_control"):
                specs.append(ToolSpec("set_ac", "Control an AC through the brand's cloud: power, temp_c (20–28), mode, fan, delta.",
                                      {"type": "object", "properties": {"device": dev, "power": {"type": "boolean"},
                                                                        "temp_c": {"type": "integer"}, "delta": {"type": "integer"},
                                                                        "mode": {"type": "string", "enum": list(ir.MODES)},
                                                                        "fan": {"type": "string", "enum": list(ir.FANS)}}}, 1))
            return specs
        return []

    # ------------------------------------------------------------------ dispatch
    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        ch = pack.config["channel"]
        refuse_unsafe(tool, args)
        if ch == "phone_media":
            if tool == "media":
                return self._media(pack, args, ctx)
            if tool == "volume":
                return self._volume(pack, args, ctx)
        if ch == "bt_hid":
            dev = self.pick(ctx, pack, "tv", args.get("device"))
            if tool == "tv_keys":
                keys = args.get("keys") or []
                if isinstance(keys, str):
                    keys = [keys]
                try:
                    ops = [hid.key_op(k, args.get("repeat", 1), args.get("hold_ms", 0)) for k in keys]
                except ValueError as e:
                    raise ToolError(str(e)) from e
                return self._phone(ctx, dev, ops, hid.keys_message([hid.norm_key(k) for k in keys], dev.name))
            if tool == "tv_channel":
                try:
                    ops = hid.number_ops(str(args.get("number", "")))
                except ValueError as e:
                    raise ToolError(str(e)) from e
                return self._phone(ctx, dev, ops, f"Channel {args.get('number')} on {dev.name}.")
            if tool == "tv_open_app":
                app = str(args.get("app", "")).strip()
                if not app:
                    raise ToolError("Which app should I open on the TV?")
                label = hid.APP_LABELS.get(app.lower(), app.title())
                return self._phone(ctx, dev, hid.open_app_ops(app), f"Opening {label} on {dev.name}.")
            if tool == "tv_youtube":
                try:
                    ops = hid.youtube_video_ops(str(args.get("video_id", "")).strip(), str(args.get("title", "") or ""))
                except ValueError as e:
                    raise ToolError("Yeh YouTube video id sahi nahi hai.") from e
                t = str(args.get("title", "") or "video")[:80]
                return self._phone(ctx, dev, ops, f"Playing '{t}' on YouTube on {dev.name}.")
            if tool == "tv_search":
                q = str(args.get("query", "")).strip()
                if not q:
                    raise ToolError("What should I search on the TV?")
                ops = hid.search_ops(q)
                return self._phone(ctx, dev, ops, f"Searching '{q}' on {dev.name}.")
        if ch == "ir":
            if tool == "set_ac":
                return self._ir_ac(pack, args, ctx)
            if tool == "ac_status":
                dev = self.pick(ctx, pack, "ac", args.get("device"))
                st = ir.AcState.from_dict(dev.state.get("ac"))
                d = st.to_dict()
                msg = describe_status(dev, d) + " (Last setting sent by Santosh; IR can't read the AC back.)"
                return {"device": dev.name, **d, "message": msg}
        if ch == "cloud":
            prov = pack.config["provider"]
            if tool == "sync_devices":
                return self.sync(ctx, pack)
            if tool == "device_status":
                dev = self.pick(ctx, pack, args.get("kind"), args.get("device"), autosync=True)
                st = cloud_client(ctx, prov).status(dev.external_id, dev.kind)
                return {"device": dev.name, "kind": dev.kind, **st, "message": describe_status(dev, st)}
            if tool == "set_ac" and pack.config.get("ac_control"):
                return self._cloud_ac(pack, args, ctx)
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        raise ToolError("Device commands don't need approval cards")

    # ------------------------------------------------------------------ helpers
    def devices(self, ctx: Ctx, pack: Pack | None = None, kind: str | None = None) -> list[Device]:
        q = select(Device).where(Device.user_id == ctx.user.id, Device.active.is_(True))
        if pack is not None:
            q = q.where(Device.pack_id == pack.id)
        if kind:
            q = q.where(Device.kind == kind)
        return list(ctx.session.scalars(q.order_by(Device.created_at)).all())

    def pick(self, ctx: Ctx, pack: Pack, kind: str | None, name: str | None, autosync: bool = False) -> Device:
        devs = self.devices(ctx, pack, kind)
        if not devs and autosync and pack.config["channel"] == "cloud":
            self.sync(ctx, pack)
            devs = self.devices(ctx, pack, kind)
        what = {"ac": "AC", "tv": "TV", "fridge": "fridge", "washer": "washing machine"}.get(kind or "", "device")
        if not devs:
            if pack.config["channel"] == "bt_hid":
                raise ToolError("Pair the TV with Hoola once: say 'TV ko Bluetooth se jodo' (bluetooth action=tv_pair) or "
                                "open Hoola › Ghar › TV.")
            if pack.config["channel"] == "ir":
                raise ToolError("Add your AC once: Santosh app › Ghar › Add AC. I'll test the remote signal with you.")
            raise ToolError(f"I couldn't find a {what} in your {pack.name} account.")
        if name:
            n = _norm(name)
            hits = [d for d in devs if _norm(d.name) in n or n in _norm(d.name) or (d.room and _norm(d.room) in n)]
            if len(hits) == 1:
                return hits[0]
            if hits:
                devs = hits
        if len(devs) == 1:
            return devs[0]
        raise ToolError(f"Which {what}? " + ", ".join(d.name for d in devs) + ".")

    def _phone(self, ctx: Ctx, dev: Device | None, ops: list[dict[str, Any]], message: str,
               new_state: dict[str, Any] | None = None, channel: str | None = None) -> dict[str, Any]:
        cmd = DeviceCommand(user_id=ctx.user.id, device_id=dev.id if dev else "phone", task_id=ctx.task.id if ctx.task else "",
                            channel=channel or (dev.channel if dev else "phone_media"), payload={}, new_state=new_state or {})
        ctx.session.add(cmd)
        ctx.session.flush()
        payload = {"command_id": cmd.id, "channel": cmd.channel,
                   "device": {"id": dev.id, "name": dev.name} if dev else {"id": "phone", "name": "Phone audio"},
                   "target": dict(dev.target) if dev else {}, "ops": ops,
                   "report_to": f"/api/bazar/devices/commands/{cmd.id}/result"}
        cmd.payload = payload
        if ctx.task is not None:
            res = dict(ctx.task.result or {})
            res["device_actions"] = [*res.get("device_actions", []), payload][-10:]  # one task lives for a whole chat
            ctx.task.result = res
        return {"device_action": payload, "message": message}

    # ------------------------------------------------------------------ speaker
    def _speaker(self, ctx: Ctx, pack: Pack) -> Device | None:
        devs = self.devices(ctx, pack, "speaker")
        return devs[0] if devs else None

    def _media(self, pack: Pack, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        action = str(args.get("action", "play")).lower()
        if action not in MEDIA_KEYS:
            raise ToolError("I can play, pause, skip to next or previous, or stop the music.")
        dev = self._speaker(ctx, pack)
        where = dev.name if dev else "your speaker"
        q = str(args.get("query", "")).strip()
        app = music_app(str(args.get("app", "")))
        if action == "play" and q:
            op: dict[str, Any] = {"op": "play_from_search", "query": q[:80]}
            kind = str(args.get("kind", "")).lower()
            if kind in MUSIC_KINDS:
                op["kind"] = kind
            label = "your music app"
            if app:
                pkg, label, link = MUSIC_APPS[app]
                op["package"] = pkg
                if link:
                    from urllib.parse import quote
                    op["fallback"] = link.format(q=quote(q[:80]))
            uri = str(args.get("uri", "")).strip()
            # v0.136.1 the exact item (spotify:track:..., music.youtube.com/watch?v=...) found and checked by the server;
            # the phone opens it straight in the app and presses play, instead of only searching
            if uri and app and re.fullmatch(r"(spotify:(track|album|artist|playlist):[A-Za-z0-9]{22}|"
                                            r"https://music\.youtube\.com/watch\?v=[\w-]{11})", uri):
                op["uri"] = uri
            shown = str(args.get("title", "")).strip()[:120] or q
            return self._phone(ctx, dev, [op], f"Playing {shown} in {label} on {where}.", channel="phone_media")
        word = {"play": "Playing", "resume": "Playing", "pause": "Paused", "next": "Next song", "previous": "Previous song",
                "stop": "Stopped", "play_pause": "Done"}[action]
        return self._phone(ctx, dev, [{"op": "media_key", "key": MEDIA_KEYS[action]}], f"{word} on {where}.",
                           channel="phone_media")

    def _volume(self, pack: Pack, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        dev = self._speaker(ctx, pack)
        where = dev.name if dev else "the speaker"
        cap = int((dev.target if dev else {}).get("max_percent", 90))
        cap = max(0, min(cap, 90))   # ear safety: never above 90%
        if args.get("percent") is not None:
            try:
                want = int(float(args["percent"]))
            except (TypeError, ValueError) as e:
                raise ToolError("Give the volume as a percent, e.g. 40.") from e
            args = {**args, "percent": want}
            pct = max(0, min(cap, want))
            note = f" (kept at {cap}% to protect your ears)" if int(args["percent"]) > cap else ""
            return self._phone(ctx, dev, [{"op": "volume_set", "percent": pct, "max_percent": cap}],
                               f"Volume set to {pct}% on {where}{note}.", channel="phone_media")
        direction = "down" if str(args.get("direction", "up")).lower() == "down" else "up"
        steps = max(1, min(10, int(args.get("steps") or 2)))
        return self._phone(ctx, dev, [{"op": "volume", "direction": direction, "steps": steps, "max_percent": cap}],
                           f"Volume {direction} on {where}.", channel="phone_media")

    # ------------------------------------------------------------------ AC
    @staticmethod
    def _apply(cur: ir.AcState, args: dict[str, Any]) -> tuple[ir.AcState, list[str]]:
        notes: list[str] = []
        st = ir.AcState(cur.power, cur.mode, cur.temp_c, cur.fan)
        if args.get("power") is False:
            st.power = False
            return st, notes
        st.power = True
        if args.get("mode") in ir.MODES:
            st.mode = args["mode"]
        if args.get("fan") in ir.FANS:
            st.fan = args["fan"]
        want = None
        if args.get("temp_c") is not None:
            want = args["temp_c"]
        elif args.get("delta"):
            try:
                want = st.temp_c + max(-8, min(8, int(args["delta"])))
            except (TypeError, ValueError) as e:
                raise ToolError("Say how many degrees, e.g. +1 or -1.") from e
        if want is not None:
            st.temp_c, clamped = ir.clamp_temp(want)
            if clamped:
                notes.append(f"I keep ACs between {ir.MIN_TEMP_C} and {ir.MAX_TEMP_C}°C, so set {st.temp_c}°C. "
                             f"Every degree higher saves about 6% on the AC's electricity.")
        return st, notes

    @staticmethod
    def _ac_message(name: str, st: ir.AcState, notes: list[str]) -> str:
        if not st.power:
            msg = f"{name} turned off."
        else:
            mode = "fan only" if st.mode == "fan" else st.mode
            msg = f"{name} on: {mode}" + ("" if st.mode == "fan" else f" at {st.temp_c}°C") + f", fan {st.fan}."
        return " ".join([msg, *notes])

    def _ir_ac(self, pack: Pack, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        dev = self.pick(ctx, pack, "ac", args.get("device"))
        if not dev.protocol:
            raise ToolError(f"{dev.name}'s remote isn't confirmed yet. Open Santosh app › Ghar › {dev.name} › Test remote.")
        cur = ir.AcState.from_dict(dev.state.get("ac"))
        st, notes = self._apply(cur, args)
        sig = ir.encode(dev.protocol, st)
        return self._phone(ctx, dev, [{"op": "ir", **sig.to_dict()}], self._ac_message(dev.name, st, notes),
                           new_state={"ac": st.to_dict()})

    def ir_test(self, ctx: Ctx, dev: Device, protocol: str) -> dict[str, Any]:
        """Onboarding: send 'on, cool 24°C' in one protocol; the user tells us if the AC beeped."""
        if protocol not in ir.PROTOCOLS:
            raise ToolError("Unknown remote type")
        sig = ir.encode(protocol, ir.AcState(True, "cool", ir.DEFAULT_TEMP_C, "auto"))
        return self._phone(ctx, dev, [{"op": "ir", **sig.to_dict()}],
                           f"Point your phone at {dev.name}. Did it beep and start at 24°C? ({ir.PROTOCOLS[protocol]['label']})")

    def _cloud_ac(self, pack: Pack, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        prov = pack.config["provider"]
        dev = self.pick(ctx, pack, "ac", args.get("device"), autosync=True)
        client = cloud_client(ctx, prov)
        live = client.status(dev.external_id, "ac")
        cur = ir.AcState(bool(live.get("power")), live.get("mode") or "cool",
                         ir.clamp_temp(live.get("temp_c") or ir.DEFAULT_TEMP_C)[0], live.get("fan") or "auto")
        st, notes = self._apply(cur, args)
        if st.power:
            client.set_ac(dev.external_id, True, st.mode, None if st.mode == "fan" else st.temp_c, st.fan)
        else:
            client.set_ac(dev.external_id, False)
        dev.state = {**dev.state, "ac": st.to_dict()}
        return {"device": dev.name, **st.to_dict(), "message": self._ac_message(dev.name, st, notes)}

    # ------------------------------------------------------------------ cloud sync + alerts
    def sync(self, ctx: Ctx, pack: Pack) -> dict[str, Any]:
        prov = pack.config["provider"]
        found = cloud_client(ctx, prov).list_devices()
        have = {d.external_id: d for d in self.devices(ctx, pack)}
        added = []
        for f in found:
            if f["kind"] not in ("ac", "fridge", "washer"):
                continue
            if f["kind"] == "ac" and not pack.config.get("ac_control"):
                continue
            d = have.get(f["id"])
            if d is None:
                d = Device(user_id=ctx.user.id, pack_id=pack.id, name=f["name"], kind=f["kind"], channel="cloud",
                           provider=prov, external_id=f["id"], brand=PROVIDERS[prov].split()[0])
                ctx.session.add(d)
                added.append(f["name"])
            else:
                d.name = f["name"]
        ctx.session.flush()
        names = [d.name for d in self.devices(ctx, pack)]
        return {"devices": names, "added": added,
                "message": f"Found {len(names)} appliance(s) in {pack.name}: {', '.join(names) or 'none'}."}


def check_alerts(ctx: Ctx, packs: dict[str, Pack]) -> list[dict[str, Any]]:
    """Run by the reminder/notification worker: fridge door open or warm, washing done. Each alert fires once."""
    ex = DeviceExecutor()
    alerts: list[dict[str, Any]] = []
    for dev in ex.devices(ctx):
        if dev.channel != "cloud" or dev.kind not in ("fridge", "washer"):
            continue
        try:
            st = cloud_client(ctx, dev.provider).status(dev.external_id, dev.kind)
        except ToolError:
            continue
        mem = dict(dev.state or {})
        if dev.kind == "fridge":
            open_now = bool(st.get("door_open"))
            if open_now and not mem.get("door_alerted"):
                alerts.append({"device": dev.name, "kind": "fridge_door", "text": f"{dev.name} door is open. Please close it."})
            mem["door_alerted"] = open_now
            warm = (st.get("fridge_c") or 0) > FRIDGE_WARM_C
            if warm and not mem.get("warm_alerted"):
                alerts.append({"device": dev.name, "kind": "fridge_warm",
                               "text": f"{dev.name} is at {st['fridge_c']}°C — food may spoil. Check the door and power."})
            mem["warm_alerted"] = warm
        else:
            prev = mem.get("washer_state")
            if st.get("state") == "finished" and prev not in (None, "finished"):
                alerts.append({"device": dev.name, "kind": "washer_done", "text": f"{dev.name}: washing is done."})
            mem["washer_state"] = st.get("state")
        dev.state = mem
    return alerts
