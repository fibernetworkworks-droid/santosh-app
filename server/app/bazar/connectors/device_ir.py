"""Infrared encoders for AC remotes. The server builds the full IR pattern; the phone only transmits it
(Android ConsumerIrManager.transmit(carrierHz, patternMicros)).

IR is one-way: an AC remote always sends the *whole* state (power, mode, temperature, fan), so Santosh keeps the
last state per AC and sends the complete new state every time.

Protocols here are public, widely documented remote formats:
- ``lg_ac``     LG 28-bit AC protocol (8-bit signature 0x88, nibble-sum checksum). Older LG remotes.
- ``lg2_ac``    Same 28-bit payload with the shorter "LG2" header used by newer LG inverter remotes.
- ``coolix``    Midea-family 24-bit protocol (each byte followed by its inverse, frame sent twice). Used by Midea and
                many OEM-made ACs sold under other brands.

Every brand/model must be confirmed on a real AC during onboarding: Santosh sends a test command and asks
"Did the AC beep?" before saving the protocol.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MIN_TEMP_C = 20   # safety + BEE guidance: Santosh never sets an AC below 20 °C
MAX_TEMP_C = 28
DEFAULT_TEMP_C = 24  # BEE default for star-rated ACs
MODES = ("cool", "dry", "fan", "auto", "heat")
FANS = ("auto", "low", "medium", "high")


@dataclass
class AcState:
    power: bool = False
    mode: str = "cool"
    temp_c: int = DEFAULT_TEMP_C
    fan: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        return {"power": self.power, "mode": self.mode, "temp_c": self.temp_c, "fan": self.fan}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> AcState:
        d = d or {}
        return cls(power=bool(d.get("power", False)), mode=d.get("mode", "cool") if d.get("mode") in MODES else "cool",
                   temp_c=clamp_temp(d.get("temp_c", DEFAULT_TEMP_C))[0], fan=d.get("fan", "auto") if d.get("fan") in FANS else "auto")


def clamp_temp(t: Any) -> tuple[int, bool]:
    """Returns (temperature, was_clamped)."""
    try:
        v = int(round(float(t)))
    except (TypeError, ValueError):
        return DEFAULT_TEMP_C, True
    c = min(MAX_TEMP_C, max(MIN_TEMP_C, v))
    return c, c != v


@dataclass
class IrSignal:
    carrier_hz: int
    pattern: list[int]           # alternating mark/space durations in microseconds, starting with a mark
    code_hex: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"carrier_hz": self.carrier_hz, "pattern": self.pattern, "code": self.code_hex}


def _bits(value: int, nbits: int, mark: int, one: int, zero: int, msb_first: bool = True) -> list[int]:
    out: list[int] = []
    order = range(nbits - 1, -1, -1) if msb_first else range(nbits)
    for i in order:
        out += [mark, one if (value >> i) & 1 else zero]
    return out


# ------------------------------------------------------------------ LG (28 bit)
LG_MODE = {"cool": 0, "dry": 1, "fan": 2, "auto": 3, "heat": 4}
LG_FAN = {"low": 0, "medium": 2, "high": 4, "auto": 5}
LG_TIMING = {"lg_ac": (8500, 4250, 550, 1600, 550), "lg2_ac": (3200, 9900, 480, 1600, 550)}


def lg_checksum(code_without_sum: int) -> int:
    """Sum of the six 4-bit nibbles above the checksum nibble, low 4 bits."""
    s = 0
    v = code_without_sum >> 4
    for _ in range(6):
        s += v & 0xF
        v >>= 4
    return s & 0xF


def lg_code(state: AcState) -> int:
    if not state.power:
        return 0x88C0051  # LG "power off" command
    raw = (0x88 << 20) | (0x0 << 16) | (LG_MODE[state.mode] << 12) | ((state.temp_c - 15) << 8) | (LG_FAN[state.fan] << 4)
    return raw | lg_checksum(raw)


def encode_lg(state: AcState, variant: str = "lg_ac") -> IrSignal:
    code = lg_code(state)
    hdr_m, hdr_s, bit_m, one, zero = LG_TIMING[variant]
    pattern = [hdr_m, hdr_s] + _bits(code, 28, bit_m, one, zero) + [bit_m]
    return IrSignal(38000, pattern, f"0x{code:07X}")


# ------------------------------------------------------------------ Coolix / Midea family (24 bit)
# Temperature codes for 17..30 °C (index = temp - 17)
COOLIX_TEMP = [0b0000, 0b0001, 0b0011, 0b0010, 0b0110, 0b0111, 0b0101, 0b0100, 0b1100, 0b1101, 0b1001, 0b1000, 0b1010, 0b1011]
COOLIX_MODE = {"cool": 0b00, "dry": 0b01, "auto": 0b10, "heat": 0b11}
COOLIX_FAN = {"auto": 0b101, "low": 0b100, "medium": 0b010, "high": 0b001}
COOLIX_OFF = 0xB27BE0
COOLIX_FAN_ONLY_TEMP = 0b1110  # temperature nibble used when the AC runs in fan-only mode
COOLIX_SENSOR_IGNORE = 0b11111
COOLIX_TIMING = (4480, 4480, 560, 1680, 560, 5040)  # hdr mark, hdr space, bit mark, one space, zero space, gap


def coolix_code(state: AcState) -> int:
    if not state.power:
        return COOLIX_OFF
    if state.mode == "fan":
        fan = COOLIX_FAN.get(state.fan, 0b101)
        return (0xB2 << 16) | (((fan << 5) | COOLIX_SENSOR_IGNORE) << 8) | (COOLIX_FAN_ONLY_TEMP << 4) | (0b01 << 2)
    fan = 0b000 if state.mode in ("auto", "dry") else COOLIX_FAN[state.fan]  # auto/dry force "auto0" fan
    temp_code = COOLIX_TEMP[min(30, max(17, state.temp_c)) - 17]
    return (0xB2 << 16) | (((fan << 5) | COOLIX_SENSOR_IGNORE) << 8) | (temp_code << 4) | (COOLIX_MODE[state.mode] << 2)


def encode_coolix(state: AcState) -> IrSignal:
    code = coolix_code(state)
    hdr_m, hdr_s, bit_m, one, zero, gap = COOLIX_TIMING
    frame: list[int] = [hdr_m, hdr_s]
    for shift in (16, 8, 0):
        b = (code >> shift) & 0xFF
        frame += _bits(b, 8, bit_m, one, zero) + _bits(b ^ 0xFF, 8, bit_m, one, zero)
    frame += [bit_m, gap]
    pattern = frame + frame[:-1]  # sent twice; pattern must end on a mark
    return IrSignal(38000, pattern, f"0x{code:06X}")


# ------------------------------------------------------------------ public API
PROTOCOLS = {
    "lg_ac": {"label": "LG (classic remote)", "encode": lambda s: encode_lg(s, "lg_ac")},
    "lg2_ac": {"label": "LG (new inverter remote)", "encode": lambda s: encode_lg(s, "lg2_ac")},
    "coolix": {"label": "Midea family (Coolix)", "encode": encode_coolix},
}

# Which protocols to try first during onboarding, by the brand the user names. Confirmed per AC with a test beep.
BRAND_TRY_ORDER = {
    "lg": ["lg2_ac", "lg_ac"],
    "midea": ["coolix"],
    "carrier": ["coolix"],
    "default": ["coolix", "lg2_ac", "lg_ac"],
}


def try_order(brand: str) -> list[str]:
    return BRAND_TRY_ORDER.get((brand or "").strip().lower(), BRAND_TRY_ORDER["default"])


def encode(protocol: str, state: AcState) -> IrSignal:
    if protocol not in PROTOCOLS:
        raise ValueError(f"Unsupported IR protocol {protocol}")
    sig = PROTOCOLS[protocol]["encode"](state)
    total = sum(sig.pattern)
    if total > 2_000_000:  # Android rejects patterns longer than 2 seconds
        raise ValueError("IR pattern longer than 2 s")
    return sig


def decode_lg(code: int) -> AcState:
    """Inverse of lg_code for tests and for showing what a code means."""
    if code == 0x88C0051:
        return AcState(power=False)
    mode = {v: k for k, v in LG_MODE.items()}[(code >> 12) & 0xF]
    fan = {v: k for k, v in LG_FAN.items()}[(code >> 4) & 0xF]
    return AcState(True, mode, ((code >> 8) & 0xF) + 15, fan)
