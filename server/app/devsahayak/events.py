"""Hoola Code Phase 6 - GITHUB EVENTS start a scheduled task (docs/HOOLA_CODE_WEB_PLAN.md; owner: "GO PHASE 6").

The official route is a REPOSITORY WEBHOOK: GitHub calls Hoola when something happens in her repo and signs every call
with a secret only GitHub and this server hold. (A full "GitHub App" would need her to register an app and keep its
private key here; a webhook gives the same events with her existing token and nothing new to trust.)

- CONNECT (her tap, per repo): Hoola makes the webhook with her token when the token may (Webhooks: write); when it may
  not, she is shown the address and the secret ONCE to paste into GitHub > Settings > Webhooks.
- A delivery is believed only when its `X-Hub-Signature-256` matches. A wrong id and a wrong signature look the same.
  A delivery seen before is not run again. A bot's event never starts anything (no loops), nor does Hoola's own branch.
- WHO may start work: by default only events caused by HER (the login the token belongs to). "Anyone in the repo" can be
  chosen on a PRIVATE repo only - on a public repo any stranger can open an issue.
- WHAT an event does is ONE of her scheduled tasks whose "starts on" is that event. Each run is an ordinary session:
  same checks, her PR tap on a public repo, her merge tap always. The event's own text (an issue title...) rides along
  as DATA, never as instructions. A new pull request from someone else gets a DRAFT review, posted only on her tap.
- At most 10 runs an hour per task."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
from datetime import datetime
from typing import Any

from sqlalchemy import select

from ..db import now, session
from .gh import GhError
from .models import DevRepo, DevSchedule

log = logging.getLogger("santosh.devsahayak.events")
EVENTS = {"issue_opened": "a new issue is opened", "issue_labeled": "an issue gets a label",
          "pr_opened": "someone opens a pull request", "ci_failed": "a CI run fails", "push": "something is pushed"}
GH_EVENTS = ["issues", "pull_request", "workflow_run", "push"]
MAX_BODY = 1_000_000
PER_HOUR = 10


def _S():
    from . import service as S
    return S


def _j(v: Any, d: Any) -> Any:
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


def when_say(event: str, flt: dict[str, Any]) -> str:
    lab, br = str(flt.get("label") or ""), str(flt.get("branch") or "")
    return {"issue_opened": "When a new issue is opened" + (f" with the label '{lab}'" if lab else ""),
            "issue_labeled": f"When an issue gets the label '{lab}'" if lab else "When an issue gets a label",
            "pr_opened": "When someone opens a pull request",
            "ci_failed": "When a CI run fails on " + (br or "the default branch"),
            "push": "When something is pushed to " + (br or "the default branch")}.get(event, "")


def clean_filter(event: str, flt: Any) -> dict[str, Any]:
    S = _S()
    f = flt if isinstance(flt, dict) else {}
    out: dict[str, Any] = {}
    lab, br, who = str(f.get("label") or "").strip()[:60], str(f.get("branch") or "").strip()[:100], str(f.get("who") or "me")
    if lab and event in ("issue_opened", "issue_labeled"):
        out["label"] = lab
    if event == "issue_labeled" and not lab:
        raise S.DevError("Name the label that should start the work (for example: hoola).")
    if br and event in ("ci_failed", "push"):
        if br.startswith("hoola/"):
            raise S.DevError("Pick one of your own branches, not one of Hoola's work branches.")
        out["branch"] = br
    if who not in ("me", "anyone"):
        raise S.DevError("who = me | anyone")
    out["who"] = who
    return out


# ---------------------------------------------------------------- connect / disconnect (her tap)
def hook_url(hook_id: str) -> str:
    S = _S()
    base = str(S._setting("public_base_url", "") or "").rstrip("/")
    if not base.startswith("https://"):
        raise S.DevError("This server has no public https address set (PUBLIC_BASE_URL), so GitHub cannot call it.")
    return f"{base}/api/devsahayak/github/{hook_id}"


def connect(tenant: str, full: str) -> dict[str, Any]:
    """Turn events on for one repo. Returns {on, by_hoola} - and, only when she has to add the webhook herself, the
    address and the secret, this ONE time."""
    from ..bazar.security import vault
    S = _S()
    with session() as s:
        r = s.scalars(select(DevRepo).where(DevRepo.tenant_id == tenant, DevRepo.full_name == (full or "").strip())).first()
        if r is None:
            raise S.DevError("That repo is not on your list.")
        rid = r.id
        if r.hook_id and r.hook_secret and r.hook_gh:
            return {"on": True, "by_hoola": True, "already": True}
    hid, secret = secrets.token_hex(16), secrets.token_urlsafe(32)
    url = hook_url(hid)
    gh_id = 0
    try:
        gh_id = int(S.gh(tenant).create_hook(full, url, secret, GH_EVENTS).get("id") or 0)
    except GhError as e:
        log.info("devsahayak webhook for %s not made by Hoola: %s", full, e)
    with session() as s:
        r = s.get(DevRepo, rid)
        r.hook_id, r.hook_secret, r.hook_gh, r.hook_seen = hid, vault().seal(secret), gh_id or None, None
    if gh_id:
        return {"on": True, "by_hoola": True}
    return {"on": True, "by_hoola": False, "url": url, "secret": secret, "events": GH_EVENTS,
            "how": ["On GitHub open the repo > Settings > Webhooks > Add webhook.", "Payload URL: the address below. Content type: application/json.",
                    "Secret: the secret below (it is shown only now).", "Events: Issues, Pull requests, Workflow runs, Pushes. Then Add webhook."]}


def disconnect(tenant: str, full: str) -> dict[str, Any]:
    S = _S()
    with session() as s:
        r = s.scalars(select(DevRepo).where(DevRepo.tenant_id == tenant, DevRepo.full_name == (full or "").strip())).first()
        if r is None:
            raise S.DevError("That repo is not on your list.")
        gh_id, rid = r.hook_gh, r.id
    left = False
    if gh_id:
        try:
            S.gh(tenant).delete_hook(full, int(gh_id))
        except GhError:
            left = True                          # the address stops answering either way; GitHub's copy may need her to remove it
    with session() as s:
        r = s.get(DevRepo, rid)
        r.hook_id, r.hook_secret, r.hook_gh, r.hook_seen = None, None, None, None
    return {"on": False, "left_on_github": left or not gh_id}


# ---------------------------------------------------------------- one delivery from GitHub
def _facts(event: str, p: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """(our event name, the few facts we keep) or None for a delivery nothing listens to."""
    act = str(p.get("action") or "")
    who = p.get("sender") or {}
    base = {"by": str(who.get("login") or ""), "bot": str(who.get("type") or "").lower() == "bot" or str(who.get("login") or "").endswith("[bot]")}
    if event == "issues" and act in ("opened", "labeled") and isinstance(p.get("issue"), dict) and "pull_request" not in p["issue"]:
        i = p["issue"]
        f = {**base, "n": int(i.get("number") or 0), "title": str(i.get("title") or "")[:200],
             "labels": [str(x.get("name") or "") for x in (i.get("labels") or []) if isinstance(x, dict)][:20]}
        if act == "labeled":
            f["label"] = str((p.get("label") or {}).get("name") or "")
        return ("issue_opened" if act == "opened" else "issue_labeled"), f
    if event == "pull_request" and act in ("opened", "ready_for_review") and isinstance(p.get("pull_request"), dict):
        pr = p["pull_request"]
        if pr.get("draft") or str((pr.get("head") or {}).get("ref") or "").startswith("hoola/"):
            return None
        return "pr_opened", {**base, "n": int(pr.get("number") or 0), "title": str(pr.get("title") or "")[:200]}
    if event == "workflow_run" and act == "completed" and isinstance(p.get("workflow_run"), dict):
        w = p["workflow_run"]
        br = str(w.get("head_branch") or "")
        if str(w.get("conclusion") or "") != "failure" or br.startswith("hoola/"):
            return None
        return "ci_failed", {**base, "branch": br, "workflow": str(w.get("name") or "")[:120], "run": int(w.get("id") or 0),
                             "sha": str(w.get("head_sha") or "")[:40], "bot": False}     # a CI run's "sender" is whoever pushed; the failure is the event
    if event == "push" and str(p.get("ref") or "").startswith("refs/heads/") and not p.get("deleted"):
        br = str(p["ref"])[11:]
        if br.startswith("hoola/"):
            return None
        return "push", {**base, "branch": br, "commits": len(p.get("commits") or []), "sha": str(p.get("after") or "")[:40]}
    return None


def _say(kind: str, f: dict[str, Any]) -> str:
    if kind in ("issue_opened", "issue_labeled"):
        return (f"GitHub event: issue #{f['n']} was " + ("opened" if kind == "issue_opened" else f"given the label '{f.get('label', '')}'")
                + f" by {f['by']}. Its title: {f['title']}")
    if kind == "ci_failed":
        return f"GitHub event: the CI run '{f['workflow']}' (run {f['run']}) FAILED on branch {f['branch']} at commit {f['sha'][:12]}."
    if kind == "push":
        return f"GitHub event: {f['commits']} commit(s) were pushed to {f['branch']} by {f['by']} (now at {f['sha'][:12]})."
    return f"GitHub event: pull request #{f['n']} was opened by {f['by']}. Its title: {f['title']}"


def receive(hook_id: str, event: str, delivery: str, signature: str, raw: bytes) -> dict[str, Any]:
    """The public door. {status: 401 | 200, ...}. Nothing about why a call was refused is told to the caller."""
    from ..bazar.security import vault
    S = _S()
    if not bool(S._setting("dev_events", True)):
        return {"status": 401}
    with session() as s:
        r = s.scalars(select(DevRepo).where(DevRepo.hook_id == (hook_id or "").strip())).first() if hook_id else None
        if r is None or not r.hook_secret:
            return {"status": 401}
        try:
            secret = vault().open(r.hook_secret)
        except ValueError:
            return {"status": 401}
        want = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, (signature or "").strip()):
            return {"status": 401}
        seen = _j(r.hook_seen or "", {}) or {}
        ids = list(seen.get("ids") or [])
        if delivery and delivery in ids:
            return {"status": 200, "ok": True, "repeat": True, "started": 0}
        ids = (ids + [delivery])[-200:] if delivery else ids
        seen["ids"] = ids
        seen["last"] = {"event": event[:40], "at": now().isoformat()}
        r.hook_seen = json.dumps(seen)
        tenant, full, private, default = r.tenant_id, r.full_name, bool(r.private), r.default_branch
    if event == "ping":
        return {"status": 200, "ok": True, "pong": True, "started": 0}
    try:
        p = json.loads(raw)
    except ValueError:
        return {"status": 200, "ok": True, "started": 0}
    if not isinstance(p, dict) or str((p.get("repository") or {}).get("full_name") or "").lower() != full.lower():
        return {"status": 200, "ok": True, "started": 0}
    got = _facts(event, p)
    if got is None:
        return {"status": 200, "ok": True, "started": 0}
    kind, f = got
    if f.get("bot"):
        return {"status": 200, "ok": True, "started": 0, "why": "bot"}
    me = str(S.settings(tenant).get("login") or "").lower()
    started = 0
    with session() as s:
        rows = [(x.id, _j(x.event_filter or "", {})) for x in s.scalars(select(DevSchedule).where(
            DevSchedule.tenant_id == tenant, DevSchedule.repo == full, DevSchedule.enabled.is_(True), DevSchedule.event == kind)).all()]
    for sid, flt in rows:
        who = str(flt.get("who") or "me")
        if kind != "ci_failed" and not (f["by"].lower() == me and me) and not (who == "anyone" and private):
            continue                              # a stranger's issue on a public repo never starts work
        lab, br = str(flt.get("label") or ""), str(flt.get("branch") or "") or default
        if kind == "issue_labeled" and f.get("label", "").lower() != lab.lower():
            continue
        if kind == "issue_opened" and lab and lab.lower() not in [x.lower() for x in f.get("labels") or []]:
            continue
        if kind in ("ci_failed", "push") and f.get("branch") != br:
            continue
        if not _take_slot(sid):
            continue
        try:
            if kind == "pr_opened":               # someone's pull request: a DRAFT review; posting it stays her tap
                threading.Thread(target=_review, args=(tenant, full, int(f["n"])), name=f"dev-ev-{sid}", daemon=True).start()
            else:
                from . import around as AR
                AR.run_schedule(tenant, sid, by="event", payload=_say(kind, f), issue=int(f.get("n") or 0) if kind.startswith("issue") else 0)
            started += 1
        except Exception as e:  # noqa: BLE001 - one task that cannot start must not fail the delivery
            log.info("devsahayak event %s for %s did not start: %s", kind, sid, e)
    return {"status": 200, "ok": True, "started": started}


def _review(tenant: str, full: str, n: int) -> None:
    try:
        _S().review(tenant, full, n)
    except Exception as e:  # noqa: BLE001
        log.info("devsahayak event review %s#%s: %s", full, n, e)


def _take_slot(sid: str) -> bool:
    """At most PER_HOUR runs an hour per task, counted with the trigger's own counter."""
    with session() as s:
        r = s.get(DevSchedule, sid)
        if r is None:
            return False
        t0 = now()
        hits = [h for h in _j(r.trigger_hits or "", []) if (t0 - datetime.fromisoformat(h)).total_seconds() < 3600]
        if len(hits) >= PER_HOUR:
            r.last_note = f"Skipped: {PER_HOUR} runs in the last hour already."
            return False
        hits.append(t0.isoformat())
        r.trigger_hits = json.dumps(hits)
        return True
