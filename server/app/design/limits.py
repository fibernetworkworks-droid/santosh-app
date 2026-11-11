"""Small in-memory rate limits of HOOLA DESIGN (phase D5): comments a person writes and the reads of a share
link. One process, a sliding window per key; it is a seat belt against a runaway script, not an account system.
Called on the event loop only (the routes are async), so it needs no lock.
"""
from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException, Request


class Window:
    """At most `limit` hits per `per_s` seconds for one key."""

    def __init__(self, limit: int, per_s: float = 60.0, what: str = "requests"):
        self.limit, self.per_s, self.what = int(limit), float(per_s), what
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) > 20000:                  # never grows without end: forget the keys gone quiet
                edge = now - self.per_s
                for k in [k for k, q in self._hits.items() if not q or q[-1] <= edge]:
                    del self._hits[k]
            hits = self._hits[key] = deque()
        edge = now - self.per_s
        while hits and hits[0] <= edge:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def check(self, key: str) -> None:
        if not self.allow(key):
            raise HTTPException(429, f"Too many {self.what} in a short time. Please wait a minute and try again.",
                                headers={"Retry-After": str(int(self.per_s))})

    def reset(self) -> None:
        self._hits.clear()


def caller(request: Request) -> str:
    """Who is reading a share link: the proxy's X-Real-IP, else the socket's peer. Never a client-sent
    X-Forwarded-For (anyone can write that)."""
    real = request.headers.get("x-real-ip", "").strip()
    return real or (request.client.host if request.client else "") or "?"


COMMENTS = Window(30, 60.0, "comments")                 # written by one person
SHARED_READS = Window(120, 60.0, "requests")            # document + comments of one link from one address
SHARED_IMAGES = Window(1200, 60.0, "requests")          # the images that document draws
