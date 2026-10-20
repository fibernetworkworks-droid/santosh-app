"""A stand-in engine for tests and for trying the plumbing without a GPU: a soft hum whose pitch comes from the
voice and whose length comes from the text. It never sounds like anyone."""
from __future__ import annotations

import hashlib
import json
import time
import wave
from pathlib import Path
from typing import Iterator

import numpy as np

from . import Engine, EngineError


class FakeEngine(Engine):
    name = "fake"
    sample_rate = 24000
    can_design = True
    chunk_s = 0.1
    delay_s = 0.0          # tests can slow it down to check cancelling

    def prepare(self, voice_dir: Path, ref_wav: Path, ref_text: str, lang: str) -> dict:
        with wave.open(str(ref_wav), "rb") as w:
            seconds = w.getnframes() / float(w.getframerate())
        if seconds < 3:
            raise EngineError("Recording bahut chhoti hai.")
        pitch = 90 + int(hashlib.sha256(ref_wav.read_bytes()).hexdigest()[:4], 16) % 160
        (voice_dir / "fake.json").write_text(json.dumps({"pitch": pitch}))
        return {"seconds": round(seconds, 1)}

    def _tone(self, pitch: float, seconds: float) -> np.ndarray:
        t = np.arange(int(seconds * self.sample_rate)) / self.sample_rate
        return (0.2 * np.sin(2 * np.pi * pitch * t)).astype(np.float32)

    def stream(self, voice_dir: Path, text: str, lang: str) -> Iterator[np.ndarray]:
        meta = voice_dir / "fake.json"
        if not meta.exists():
            raise EngineError("Yeh awaaz taiyaar nahi hai.")
        pitch = json.loads(meta.read_text())["pitch"]
        total = max(0.2, 0.06 * len(text.split()) + 0.1)
        n = max(1, int(round(total / self.chunk_s)))
        for _ in range(n):
            if self.delay_s:
                time.sleep(self.delay_s)
            yield self._tone(pitch, self.chunk_s)

    def design(self, description: str, text: str, lang: str) -> np.ndarray:
        pitch = 90 + int(hashlib.sha256(description.encode()).hexdigest()[:4], 16) % 160
        return self._tone(pitch, max(4.0, 0.3 * len(text.split())))
