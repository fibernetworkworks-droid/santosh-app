"""Moving envelopes between avatars: on this server directly; to other servers over signed HTTPS (federation)."""
from __future__ import annotations

from typing import Any

from . import identity as idn


class TransportError(Exception):
    pass


def deliver(env: dict[str, Any]) -> dict[str, Any]:
    if idn.is_local(env["to"]):
        from .service import receive
        return receive(env)
    from . import federation
    return federation.send(env)


def lookup_remote(handle: str, dom: str) -> str:
    from . import federation
    return federation.lookup(handle, dom)
