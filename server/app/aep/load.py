"""HOOLA AEP load - the from-dict loader, the langchain-core `load/` idea
hand-built for the house (upstream reference read at github.com/langchain-ai/langchain
@ aa2528fb, libs/core/langchain_core/load/{dump.py 120 lines, load.py 828, mapping.py
1103}) - ZERO upstream code (the port law).

v0.581.0 HOOLA HUB (P7 of the AEP plan): P1's serializable.py shipped the
`to_json()` seed and reserved the loader for P7; this is that loader.

THE DUMP LANE
- `dumpd(obj)`  - the dict form; `dumps(obj, pretty=False)` - the JSON string form.
- Every `Serializable` becomes its langchain-shaped constructor dict
  ({"lc": 1, "type": "constructor", "id": [...], "kwargs": {...}}); anything else
  that is not plain JSON becomes the honest `not_implemented` marker with the
  object's module+class named (never a silent loss).
- ESCAPE LAW (the injection guard): a plain dict that carries an `lc` key is user
  data, not a serialized object - it is wrapped as {"__lc_escaped__": {...}} on
  dump and unwrapped (back to a plain dict, never instantiated) on load. Only
  dicts produced by `Serializable.to_json()` are treated as loadable objects.
- SECRETS: a class may declare `lc_secrets` ({attr: name}); dumpd replaces those
  kwarg values with `$name` placeholders, so secrets never ride the wire. The
  redaction-before-egress law, upstream serializable.py's lc_secrets shape.

THE LOAD LANE
- `load(obj)` / `loads(text)` rebuild objects through `Reviver` against the
  ALLOWLIST (`SERIALIZABLE_MAPPING`, scanned from the live app.aep package and
  cached). Anything not in the allowlist refuses with the upstream-style wording -
  deserialization instantiates constructors, so the allowlist IS the security
  boundary (the threat model is upstream load.py's own docstring: a payload can
  configure base_url / api_key / model - treat it as executable configuration).
- `allowed_objects` gates further: "all" (the full house mapping), "core"
  (default - every aep class), "messages" (only message classes - the safe
  choice for untrusted input), or an explicit list of classes.
- STRONGER THAN UPSTREAM, ON PURPOSE: the house loader resolves classes from the
  in-memory mapping only - it NEVER imports a module at load time, and it NEVER
  reads the environment itself: `secrets_from_env=True` demands the caller hand
  the env mapping over explicitly - the loader stays env-blind (the P1 law: no
  environment reads inside aep sources).
- `secrets_map` substitutes `$name` placeholders (default secrets_from_env=False
  - the same warning as upstream: only for payloads you fully trust).

Inert library: nothing here executes, touches the network or reads config until
called - the P1 kill-switch note holds for P7 too.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from pydantic import BaseModel

from .serializable import Serializable

_ESCAPE_KEY = "__lc_escaped__"
_SECRET_PREFIX = "$"
_HOUSE_NAMESPACES = ("aep", "hoola")

# ---------------------------------------------------------------------------
# the not-implemented marker
# ---------------------------------------------------------------------------


class SerializedNotImplemented(BaseModel):
    """The honest marker for an object that does not serialize (upstream shape).

    `repr` and `name` carry the object's own identity so the loss is visible in
    the payload instead of silent.
    """

    repr: str
    name: str

    def to_json(self) -> dict[str, Any]:
        return {
            "lc": 1,
            "type": "not_implemented",
            "id": [type(self).__module__, self.name],
            "kwargs": {},
        }


def _to_json_not_implemented(obj: Any) -> dict[str, Any]:
    m = SerializedNotImplemented(repr=repr(obj), name=type(obj).__name__)
    return m.to_json()


def _default(obj: Any) -> Any:
    """Serializable -> its to_json(); anything else -> the not_implemented marker."""
    if isinstance(obj, Serializable):
        return _apply_secrets(obj, obj.to_json())
    return _to_json_not_implemented(obj)


def _apply_secrets(obj: Any, data: dict[str, Any]) -> dict[str, Any]:
    """Mask the class's lc_secrets kwarg values as $name placeholders (both
    serializable lanes - the Serializable family and the house-duck models)."""
    secrets = getattr(type(obj), "lc_secrets", None) or {}
    if not secrets:
        return data
    kwargs = dict(data.get("kwargs") or {})
    for attr, name in secrets.items():
        if attr in kwargs and kwargs[attr] is not None:
            kwargs[attr] = f"{_SECRET_PREFIX}{name}"
    data["kwargs"] = kwargs
    return data


def _house_id(cls: type) -> tuple[str, ...]:
    """The house id convention for the pydantic-based serializables
    (models.py's BaseChatModel/BaseLLM family - P1 built them on
    _SerializableBase, not on serializable.Serializable)."""
    return ("aep", cls.__module__.rsplit(".", 1)[-1], cls.__name__)


def _house_serialize(obj: Any) -> dict[str, Any]:
    """The constructor dict for a house-duck serializable (a BaseModel in the
    aep package that carries no to_json of its own)."""
    cls = type(obj)
    try:
        kwargs = obj.model_dump() if isinstance(obj, BaseModel) else {}
    except Exception:  # noqa: BLE001 - the honest marker, never a crash
        return _to_json_not_implemented(obj)
    data = {"lc": 1, "type": "constructor", "id": list(_house_id(cls)),
            "kwargs": _serialize_value(kwargs)}
    return _apply_secrets(obj, data)


def _is_house_serializable(obj: Any) -> bool:
    cls = type(obj)
    return cls.__module__.startswith("app.aep") and isinstance(obj, BaseModel)


def _serialize_value(value: Any) -> Any:
    """The deep walk: lists/tuples stay sequences, dicts escape, models dump."""
    if isinstance(value, Serializable):
        return _default(value)
    if _is_house_serializable(value):
        return _house_serialize(value)
    if isinstance(value, dict):
        if "lc" in value:
            return {_ESCAPE_KEY: {k: _serialize_value(v) for k, v in value.items()}}
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if isinstance(value, BaseModel):
        # A non-Serializable pydantic model rides as its plain dict (it dumps
        # honestly) unless it is simply not JSON-able - then the marker.
        try:
            return {k: _serialize_value(v) for k, v in value.model_dump().items()}
        except Exception:  # noqa: BLE001 - the honest marker, never a crash
            return _to_json_not_implemented(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return _default(value)


def dumpd(obj: Any) -> Any:
    """The dict form of the dump lane (upstream dump.py:105)."""
    return _serialize_value(obj)


def dumps(obj: Any, *, pretty: bool = False, **kwargs: Any) -> str:
    """The JSON string form (upstream dump.py:70). `default` is refused - the
    serialization policy lives here, not with the caller."""
    if "default" in kwargs:
        raise ValueError("`default` should not be passed to dumps")
    serialized = _serialize_value(obj)
    if pretty:
        indent = kwargs.pop("indent", 2)
        return json.dumps(serialized, indent=indent, **kwargs)
    return json.dumps(serialized, **kwargs)


# ---------------------------------------------------------------------------
# the allowlist mapping
# ---------------------------------------------------------------------------

_MAPPING_LOCK = threading.Lock()
_MAPPING: dict[tuple[str, ...], type] | None = None


def _scan_mapping() -> dict[tuple[str, ...], type[Serializable]]:
    """Every Serializable subclass on the app.aep package, keyed by its id.

    Built once and cached; the scan imports app.aep (the package is inert, so
    the scan costs nothing but the walk). Loader-time resolution is then pure
    dict lookup - no import ever happens on the load path.
    """
    global _MAPPING
    with _MAPPING_LOCK:
        if _MAPPING is not None:
            return _MAPPING
        import app.aep as aep_pkg  # local import: the scan runs on first use only

        mapping: dict[tuple[str, ...], type] = {}
        seen: set[int] = set()

        def _consider(cls: Any) -> None:
            if not isinstance(cls, type) or id(cls) in seen:
                return
            seen.add(id(cls))
            if issubclass(cls, Serializable) and cls is not Serializable:
                mapping[tuple(cls.lc_id())] = cls
            elif issubclass(cls, BaseModel) and cls.__module__.startswith("app.aep"):
                mapping[_house_id(cls)] = cls

        def _walk(mod: Any) -> None:
            for name in sorted(dir(mod)):
                _consider(getattr(mod, name, None))

        _walk(aep_pkg)
        for attr in dir(aep_pkg):
            mod = getattr(aep_pkg, attr, None)
            if getattr(mod, "__package__", "").startswith("app.aep"):
                _walk(mod)
        _MAPPING = mapping
        return _MAPPING


def serializable_mapping() -> dict[tuple[str, ...], type]:
    """The live allowlist (a copy - the registry itself stays house-internal)."""
    return dict(_scan_mapping())


# ---------------------------------------------------------------------------
# the loader
# ---------------------------------------------------------------------------

_ALLOWED_MODES = ("all", "core", "messages")


def _classes_for_allowed(allowed: str | list[type] | tuple[type, ...]) \
        -> set[type]:
    mapping = _scan_mapping()
    if isinstance(allowed, str):
        if allowed not in _ALLOWED_MODES:
            raise ValueError(
                f"allowed_objects must be one of {_ALLOWED_MODES} or a list of "
                f"classes, got {allowed!r}")
        if allowed == "all":
            return set(mapping.values())
        if allowed == "core":
            return {c for i, c in mapping.items() if i[0] == "aep"}
        # "messages" - the safe choice: only message classes.
        return {c for i, c in mapping.items() if len(i) >= 2 and i[1] == "messages"}
    classes: set[type] = set()
    for cls in allowed:
        if not (isinstance(cls, type) and (issubclass(cls, Serializable)
                                           or cls.__module__.startswith("app.aep"))):
            raise ValueError(f"allowed_objects entries must be aep classes, got {cls!r}")
        classes.add(cls)
    return classes


class Reviver:
    """Rebuilds one constructor dict against the allowlist (upstream load.py:336).

    The id path matches the mapping exactly or by suffix (the last two or three
    segments) so payloads survive house id drift without loosening the class
    gate: the CLASS is still the allowlist entry, never the path text.
    """

    def __init__(
        self,
        *,
        secrets_map: dict[str, str] | None = None,
        allowed_objects: str | list[type] | tuple[type, ...] = "core",
        valid_namespaces: tuple[str, ...] | list[str] = _HOUSE_NAMESPACES,
        secrets_from_env: bool = False,
        env: dict[str, str] | None = None,
    ) -> None:
        self.secrets_map = secrets_map or {}
        self.allowed_objects = allowed_objects
        self.valid_namespaces = tuple(valid_namespaces) or _HOUSE_NAMESPACES
        self.secrets_from_env = secrets_from_env
        self.env = env
        self._classes = _classes_for_allowed(allowed_objects)

    def _resolve(self, id_path: list[str]) -> type | None:
        if not id_path or id_path[0] not in self.valid_namespaces:
            return None
        full = tuple(id_path)
        mapping = _scan_mapping()
        if full in mapping:
            cls = mapping[full]
            return cls if cls in self._classes else None
        for tail in (full[-1:], full[-2:], full[-3:]):
            cls = mapping.get(tail)
            if cls is not None:
                return cls if cls in self._classes else None
        return None

    def _substitute_secrets(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in kwargs.items():
            if isinstance(v, str) and v.startswith(_SECRET_PREFIX) and len(v) > 1:
                name = v[1:]
                if name in self.secrets_map:
                    out[k] = self.secrets_map[name]
                    continue
                if self.secrets_from_env:
                    if self.env is None:
                        raise ValueError(
                            f"Secret placeholder {v!r} for kwarg {k!r}: "
                            "secrets_from_env=True demands the caller hand the "
                            "env mapping over explicitly - the loader never "
                            "reads the environment itself")
                    env_val = self.env.get(name)
                    if env_val is not None:
                        out[k] = env_val
                        continue
                raise ValueError(
                    f"Secret placeholder {v!r} for kwarg {k!r} has no value in "
                    "secrets_map and secrets_from_env is False")
            out[k] = v
        return out

    def __call__(self, value: dict[str, Any]) -> Any:
        if not all(k in value for k in ("lc", "id", "type", "kwargs")):
            return value
        if value.get("type") == "not_implemented":
            return SerializedNotImplemented(repr="(loaded)", name=(value.get("id") or ["", "?"])[-1])
        if value.get("type") != "constructor":
            return value
        cls = self._resolve(list(value.get("id") or []))
        if cls is None:
            path = ".".join(str(p) for p in (value.get("id") or []))
            raise ValueError(
                f"Trying to load an object that doesn't exist: {path}. Only "
                "classes in the allowlist can be loaded - pass allowed_objects "
                "explicitly for untrusted input.")
        kwargs = self._substitute_secrets(dict(value.get("kwargs") or {}))
        return cls(**kwargs)


def _load_value(value: Any, reviver: Reviver) -> Any:
    if isinstance(value, dict):
        if _ESCAPE_KEY in value and len(value) == 1:
            inner = value[_ESCAPE_KEY]
            # Escaped user data unwraps to a PLAIN dict - never instantiated.
            return {k: _load_value(v, reviver) for k, v in inner.items()}
        if value.get("lc") == 1 and "id" in value:
            # A serialized object marker: the reviver is the ONLY door back to
            # a live object, and its allowlist is the security boundary.
            return reviver(value)
        return {k: _load_value(v, reviver) for k, v in value.items()}
    if isinstance(value, list):
        return [_load_value(v, reviver) for v in value]
    return value


def load(
    obj: Any,
    *,
    secrets_map: dict[str, str] | None = None,
    allowed_objects: str | list[type] | tuple[type, ...] = "core",
    secrets_from_env: bool = False,
    env: dict[str, str] | None = None,
) -> Any:
    """Rebuild aep objects from the dump-dict form (upstream load.py:683).

    Threat model (upstream load.py's own, honored here): a payload can carry
    constructor configuration - base_url, api_key, model names. `load()`
    instantiates allowed classes with the kwargs it carries, so only feed it
    payloads you trust; for untrusted input use `allowed_objects="messages"`
    (or an explicit class list) and keep `secrets_from_env=False`. The loader
    itself never reads the environment: `secrets_from_env=True` requires the
    caller to pass `env=<mapping>`.
    """
    reviver = Reviver(
        secrets_map=secrets_map,
        allowed_objects=allowed_objects,
        secrets_from_env=secrets_from_env,
        env=env,
    )
    return _load_value(obj, reviver)


def loads(
    text: str,
    *,
    secrets_map: dict[str, str] | None = None,
    allowed_objects: str | list[type] | tuple[type, ...] = "core",
    secrets_from_env: bool = False,
    env: dict[str, str] | None = None,
) -> Any:
    """`load()` over a JSON string (upstream load.py:572)."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to loads: not valid JSON - {e}") from e
    return load(obj, secrets_map=secrets_map, allowed_objects=allowed_objects,
                secrets_from_env=secrets_from_env, env=env)
