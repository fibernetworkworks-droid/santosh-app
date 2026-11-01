"""v0.419 ROLE PACKS (Hoola Game Engine plan Phase 7, docs/GAME_DESK_PLAN.md section 5): each Game Desk role adds a pack
that writes its OWN autoload into every build of her game - the same rule as the Game Bible and the assets: Hoola
writes it from data she approved, the model only reads it (ai.GUIDE) and never edits or re-outputs it.

A pack module exposes:
  FILE = "hoola_<x>.gd"                       (also listed in template.HOOLA_OWN with its autoload name)
  for_game(tenant, game_id) -> (gd_text, {res path: file on disk}) | None
  demo_build(token) -> Path | None            (optional: a Hoola-made demo build served at /play/<token>/)
A pack that fails never breaks a build: the game builds without it and the error is logged."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path

log = logging.getLogger("santosh.gamedesk")

PACKS = ("world", "physics")                     # gamedesk/<name>.py, in build order


def _mods():
    for name in PACKS:
        try:
            yield importlib.import_module(f"{__package__}.{name}")
        except Exception:                               # noqa: BLE001
            log.exception("game pack %s", name)


def files() -> list[str]:
    return [m.FILE for m in _mods()]


def for_game(tenant: str, game_id: str) -> dict[str, tuple[str, dict[str, Path]]]:
    """{hoola_<x>.gd: (text, {res path: disk file})} for every pack with approved data for this game."""
    out: dict[str, tuple[str, dict[str, Path]]] = {}
    for m in _mods():
        try:
            got = m.for_game(tenant, game_id)
        except Exception:                               # noqa: BLE001 - the game builds without this pack
            log.exception("pack %s for game %s", m.__name__, game_id)
            continue
        if got:
            out[m.FILE] = got
    return out


def demo_build(token: str) -> Path | None:
    for m in _mods():
        fn = getattr(m, "demo_build", None)
        if fn is None:
            continue
        try:
            d = fn(token)
        except Exception:                               # noqa: BLE001
            log.exception("pack demo %s", m.__name__)
            continue
        if d is not None:
            return d
    return None
