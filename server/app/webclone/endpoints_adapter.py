"""WEB CLONE stage 3 - endpoints: the functional map of what was captured.

The bundle is zipped once and handed to appcheck.endpoints.extract (the same static scanner the
App Jaanch lane uses - it reads bytes, never runs them), then its summary() shapes the answer:
{counts, top_hosts, urls, api_paths, ips}. On python.org this surfaces the /api/event path and
the 8 hosts the page's JS + CSS talk to, which is exactly the map a rebuild needs to wire its
own fetches against.
"""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any

from ..appcheck import endpoints


def scan(bundle_dir: Path, name: str = "") -> dict[str, Any]:
    """Zip the capture bundle, run the static scanner, return the summary shape."""
    bundle_dir = Path(bundle_dir)
    name = name or bundle_dir.name or "webclone-bundle"
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        zip_path = Path(tf.name)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(bundle_dir.rglob("*")):
                if p.is_file():
                    z.write(p, p.relative_to(bundle_dir).as_posix())
        res = endpoints.extract(zip_path, zip_path.name, kind="zip")
        out = endpoints.summary(name, res, None)
        out["kind"] = "webclone-capture"
        return out
    finally:
        zip_path.unlink(missing_ok=True)
