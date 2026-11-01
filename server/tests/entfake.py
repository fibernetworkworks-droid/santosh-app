"""A fake enterprise endpoint, shared by the ERP / CRM suites.

v0.388 moved WRITES off `run._odata_call` and onto `dialect.Call`, because a SAP CSRF token is bound to the
security session and a per-call client can never hold one. These suites test run.py's ORCHESTRATION (plan ->
dry run -> tap -> batches -> resume), so they drive the new seam while keeping the same
`(method, path, body)` record they always asserted on. The dialect's own rules - If-Match, CSRF, the
Windchill reservation - are proved separately in test_v0388_real_rails.py against recorded HTTP.
"""
from __future__ import annotations

from typing import Any, Callable


def fake_call(calls: list, answer: Callable[[str, str, Any], tuple[int, Any]]):
    """Build a drop-in replacement for `dialect.Call`. `answer(method, path, body) -> (code, data)`."""

    class FakeCall:
        def __init__(self, ep: Any, timeout: int = 60):
            self.ep = ep
            self.system = getattr(ep, "system", "")

        # -------- plumbing the engine uses
        def close(self) -> None:
            pass

        def __enter__(self) -> "FakeCall":
            return self

        def __exit__(self, *_: Any) -> None:
            pass

        def raw(self, method: str, path: str, body: Any = None, params: dict | None = None,
                headers: dict | None = None):
            code, data = self._go(method, path, body)
            return code, data, _Res(code)

        def get(self, path: str, params: dict | None = None, page: int = 0):
            return self._go("GET", path, None)

        def etag(self, item_path: str):
            return 'W/"fake-etag"'

        # -------- the writes
        def create(self, collection: str, body: dict, idem_key: str = "", root: str = ""):
            code, data = self._go("POST", collection, body)
            return code, data, {}

        def update(self, item_path: str, body: dict, root: str = ""):
            code, data = self._go("PATCH", item_path, body)
            return code, data, {}

        def reserve(self, item_path: str, root: str = "") -> bool:
            return False

        def unreserve(self, item_path: str, root: str = "") -> None:
            return None

        def writing(self, item_path: str, root: str = ""):
            return self

        def support(self) -> dict:
            return {"system": self.system, "idempotent_create": "unknown"}

        def _go(self, method: str, path: str, body: Any):
            calls.append((method, path, body))
            return answer(method, path, body)

    return FakeCall


class _Res:
    def __init__(self, code: int):
        self.status_code, self.headers, self.text = code, {}, ""

    def json(self):
        return {}
