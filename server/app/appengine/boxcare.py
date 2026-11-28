"""ONE ENGINE (owner: "GO ONE ENGINE"): the new engine's builder box looked after the way Lovable and Emergent look
after their build machines - checked before every build and repaired by itself, so building does not depend on someone
running a VPS job.

What breaks a new-engine build on this server, and what happens now:
- the box image is missing or older than the code needs (a server rebuild, a pruned image, a new image revision):
  rebuilt here, once at a time (every build that needs it waits for the same rebuild), the owner told in her
  'Hoola updates' chat; a rebuild that failed is not tried again for 30 minutes (so a broken build never loops);
- Docker is missing or not answering, or the disk is nearly full: this cannot be fixed by code safely, so the owner is
  told plainly (at most once every 6 hours per problem) and the build says why.

A check before every build is cheap (two `docker` calls); the worker also checks every 10 minutes while the new engine
builds new websites, so a problem is usually repaired before a person asks for a website. Switching the default to the
new engine is refused while the box cannot build and cannot be repaired (enginedefault.decide).

Switch: `app_engine_box_care` (default on; the test suite turns it off so no test starts a real image build)."""
from __future__ import annotations

import logging
import shutil
import threading
import time
from typing import Any

log = logging.getLogger("santosh.appengine")

FAIL_WAIT_S = 1800            # a failed automatic rebuild waits this long before it is tried again
TELL_EVERY_S = 6 * 3600       # the same problem is told to the owner at most this often
CHECK_EVERY_S = 600           # the worker's own look, while the new engine builds new websites
DISK_MIN_GB = 3.0             # less free space than this on Docker's disk = a build can fail half-way

_REPAIR = threading.Lock()    # one rebuild at a time; builds that need it wait for the same one
STATE: dict[str, Any] = {"checked_at": 0.0, "last": {}, "repairing": False, "repaired_at": 0.0, "failed_at": 0.0,
                         "fail_why": "", "repairs": 0, "told": {}}


def _settings():
    from ..config import get_settings
    return get_settings()


def on() -> bool:
    st = _settings()
    return bool(getattr(st, "app_engine", True)) and bool(getattr(st, "app_engine_box_care", True))


def in_use() -> bool:
    """Is the new engine building NEW websites on this server (her decision or the server switch)?"""
    try:
        from ..site import enginedefault as ED
        return ED.view().get("new_sites_on") == "new"
    except Exception:                                   # noqa: BLE001 - no decision readable: the old engine
        return False


def _docker_root() -> str:
    from ..devlab import box
    d = box.docker()
    if d:
        rc, out, _ = box._run([d, "info", "--format", "{{.DockerRootDir}}"], 25)
        t = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
        if rc == 0 and t.startswith("/"):
            return t
    return "/"


def disk_free_gb(path: str = "") -> float | None:
    """Free space on the disk Docker keeps its images on (None when it cannot be read)."""
    import os
    p = path or _docker_root()
    while p and not os.path.exists(p):
        p = os.path.dirname(p.rstrip("/")) or "/"
    try:
        return round(shutil.disk_usage(p or "/").free / 1e9, 1)
    except OSError:
        return None


def check(disk: bool = True) -> dict[str, Any]:
    """Can the box build right now? ok, why, fixable (the image can be rebuilt by code), disk_free_gb. Never raises."""
    from . import runner as R
    try:
        av = dict(R.available())
    except Exception as e:                              # noqa: BLE001
        av = {"ok": False, "runner": "box", "why": f"the box could not be checked: {type(e).__name__}"}
    out = {"ok": bool(av.get("ok")), "runner": av.get("runner"), "why": str(av.get("why") or ""),
           "fixable": av.get("fix") == "image", "rev": av.get("rev", ""), "at": time.time()}
    if disk and out["runner"] == "box" and av.get("fix") != "docker":
        g = disk_free_gb()
        out["disk_free_gb"] = g
        if g is not None and g < DISK_MIN_GB:
            out["disk_low"] = True
            if out["ok"]:
                out["why"] = (f"only {g} GB free on the disk the builder uses (needs at least {DISK_MIN_GB:g} GB); "
                              "a website build can fail half-way")
    STATE["checked_at"], STATE["last"] = out["at"], out
    return out


def _tell(kind: str, text: str, force: bool = False) -> None:
    """Into the owner's 'Hoola updates' chat, at most once every 6 hours per kind of problem."""
    now = time.time()
    if not force and now - float(STATE["told"].get(kind) or 0.0) < TELL_EVERY_S:
        return
    STATE["told"][kind] = now
    try:
        from ..aiapps.ops import _note
        _note(_settings().tenant_id, text)
    except Exception:                                   # noqa: BLE001 - the log still has it
        log.info("box care note not sent: %s", text)


def repair(reason: str = "") -> dict[str, Any]:
    """Rebuild the box image (only when the check says the image is the problem). One at a time; a build that needs
    the box waits for the rebuild already running instead of starting a second."""
    from . import image as IMG
    with _REPAIR:
        c = check(disk=False)
        if c["ok"] or not c["fixable"]:
            return c
        if time.time() - float(STATE["failed_at"] or 0.0) < FAIL_WAIT_S:
            return {**c, "why": c["why"] + f"; the automatic repair failed a little while ago ({STATE['fail_why']}) and "
                                           "is tried again later"}
        STATE["repairing"] = True
        t0 = time.time()
        log.warning("box care: rebuilding the App Engine image (%s) because: %s", reason or "check", c["why"])
        try:
            res = IMG.build()
        except Exception as e:                          # noqa: BLE001
            res = {"ok": False, "why": f"{type(e).__name__}: {e}"[:200]}
        finally:
            STATE["repairing"] = False
        secs = round(time.time() - t0, 1)
        after = check(disk=False)
        if res.get("ok") and after["ok"]:
            STATE["repaired_at"], STATE["repairs"] = time.time(), STATE["repairs"] + 1
            STATE["failed_at"], STATE["fail_why"] = 0.0, ""
            log.warning("box care: the App Engine image is ready again (%s s)", secs)
            _tell("repaired", f"The website builder was not ready ({c['why'].split(':')[0]}), so Hoola rebuilt it by "
                              f"itself in {secs:g} seconds. New websites build normally again.", force=True)
            return {**after, "repaired": True, "seconds": secs}
        STATE["failed_at"], STATE["fail_why"] = time.time(), str(res.get("why") or after["why"])[:200]
        log.error("box care: the App Engine image did not rebuild: %s", STATE["fail_why"])
        _tell("repair_failed", "The website builder is not ready and Hoola could not rebuild it by itself "
                               f"({STATE['fail_why']}). New websites cannot be built on the new engine until it is fixed: "
                               "run VPS ops > appengine_setup, or tap Back to the old engine on /console/proofcard.")
        return {**after, "repaired": False, "seconds": secs, "why": after["why"] or STATE["fail_why"]}


def ensure(reason: str = "a build") -> dict[str, Any]:
    """Before a build: ready -> go; the image missing / old -> rebuilt here first; anything else -> the plain reason
    (and the owner told). Never raises."""
    if not on():
        return check(disk=False)
    c = check(disk=False)
    if c["ok"]:
        return c
    if c["fixable"]:
        return repair(reason)
    _tell("down", f"The website builder cannot build right now: {c['why']}. New websites on the new engine will fail "
                  "until it is fixed; to build on the old engine meanwhile, tap Back to the old engine on /console/proofcard.")
    return c


def status() -> dict[str, Any]:
    """For the owner page: the last check (re-checked when older than a minute)."""
    last = STATE.get("last") or {}
    if not last or time.time() - float(STATE.get("checked_at") or 0.0) > 60:
        last = check()
    return {**{k: last.get(k) for k in ("ok", "why", "rev", "disk_free_gb", "disk_low", "fixable", "runner")},
            "repairing": bool(STATE["repairing"]), "repairs": STATE["repairs"],
            "repaired_at": STATE["repaired_at"] or None, "repair_failed": STATE["fail_why"] or "", "care": on()}


_tick_at = 0.0


def tick() -> dict[str, Any] | None:
    """The worker's look every 10 minutes while the new engine builds new websites: repair what code can, tell the
    owner what it cannot (a full disk included)."""
    global _tick_at
    if not on() or not in_use() or time.time() - _tick_at < CHECK_EVERY_S:
        return None
    _tick_at = time.time()
    c = check()
    if not c["ok"]:
        return ensure("the 10-minute check")
    if c.get("disk_low"):
        _tell("disk", f"The website builder's disk is nearly full ({c.get('disk_free_gb')} GB free). "
                      "Free some space on the server before a website build fails half-way.")
    return c
