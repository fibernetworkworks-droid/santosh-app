"""Speech engines for Hoola Awaaz. Every engine speaks in a voice made from a short reference recording.

An engine is picked with ENGINE=<name> in the worker's .env. Adding a model = one file here with a class that
implements Engine, plus its name in ENGINES below.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Iterator

import numpy as np


class EngineError(Exception):
    """A problem the user can be told about (bad reference audio, unsupported language...)."""


class Engine:
    name = "base"
    sample_rate = 24000          # rate of the float32 audio the engine yields
    can_design = False           # can make a brand-new voice from a text description
    watermark = False            # adds an inaudible watermark to everything it says
    languages: tuple[str, ...] = ("hi", "en")

    def load(self) -> None:
        """Load model weights (once, at worker start)."""

    def prepare(self, voice_dir: Path, ref_wav: Path, ref_text: str, lang: str) -> dict:
        """Turn the reference recording into whatever the model needs to speak in that voice, cached in voice_dir.
        Returns facts for the server (e.g. seconds used)."""
        raise NotImplementedError

    def stream(self, voice_dir: Path, text: str, lang: str) -> Iterator[np.ndarray]:
        """Speak `text` in the voice, yielding float32 mono chunks in [-1, 1] at self.sample_rate as soon as they
        are ready (first chunk fast: that is what the caller hears as reply speed)."""
        raise NotImplementedError

    def design(self, description: str, text: str, lang: str) -> np.ndarray:
        """A new voice from words ("young woman from Pune, warm, slightly husky"): a float32 sample saying `text`."""
        raise EngineError("Is engine mein nayi awaaz banane ki suvidha nahi hai.")


ENGINES = {
    "fake": "engines.fake:FakeEngine",
    "chatterbox": "engines.chatterbox:ChatterboxEngine",
}


def load_engine(name: str) -> Engine:
    if name not in ENGINES:
        raise EngineError(f"Unknown ENGINE {name!r}; choose one of {', '.join(ENGINES)}")
    mod, cls = ENGINES[name].split(":")
    return getattr(importlib.import_module(mod), cls)()
