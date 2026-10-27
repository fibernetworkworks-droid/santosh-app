"""v0.53 Silero VAD v5 (MIT, github.com/snakers4/silero-vad) on the server: is this 40 ms of call audio a human voice?

Used by Awaaz Pehchaan so only real speech goes into the voice fingerprint guess (not TV hum, fans, clatter or
music that happens to be loud), and for call quality numbers. The phone runs the same model to gate barge-in.
One `Stream` per call (the model is recurrent). onnxruntime is optional: without it `Stream.prob` returns None.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

log = logging.getLogger("santosh.vad")
MODEL = Path(__file__).with_name("vadmodel") / "silero_vad.onnx"
WIN, CTX, SR = 512, 64, 16000
_SESS = None
_LOCK = threading.Lock()


def _session():
    global _SESS
    if _SESS is None:
        with _LOCK:
            if _SESS is None:
                try:
                    import onnxruntime as ort
                    o = ort.SessionOptions()
                    o.intra_op_num_threads = 1
                    o.inter_op_num_threads = 1
                    _SESS = ort.InferenceSession(str(MODEL), sess_options=o, providers=["CPUExecutionProvider"])
                except Exception as e:
                    log.info("silero vad unavailable: %s", e)
                    _SESS = False
    return _SESS or None


def available() -> bool:
    return _session() is not None


class Stream:
    """Feed 16 kHz 16-bit mono PCM in any chunk size; `prob` = highest speech probability of the windows completed."""

    def __init__(self):
        import numpy as np
        self.np = np
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.ctx = np.zeros(CTX, dtype=np.float32)
        self.pending = np.zeros(0, dtype=np.float32)
        self.sr = np.array(SR, dtype=np.int64)

    def prob(self, pcm: bytes) -> float | None:
        s = _session()
        if s is None:
            return None
        np = self.np
        x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
        buf = np.concatenate([self.pending, x])
        best = -1.0
        n = len(buf) // WIN
        for i in range(n):
            w = buf[i * WIN:(i + 1) * WIN]
            inp = np.concatenate([self.ctx, w])[None, :]
            out, self.state = s.run(None, {"input": inp, "state": self.state, "sr": self.sr})
            self.ctx = inp[0, -CTX:]
            best = max(best, float(out[0][0]))
        self.pending = buf[n * WIN:]
        return None if best < 0 else best
