"""The F7 card: a firm with 50 test clients (FINANCE_GLOBAL_PLAN phase F7).

The firm: 2 partners, 1 manager, 4 preparers (each assigned 12-13 clients), 2 reviewers (each assigned half), and one person for each
of the 50 clients. For every client: papers are asked for, the client sends one, a preparer makes a draft naming a signer, a reviewer
approves it, the signer signs it, a partner shares it. A seed picks which clients get an edit after approval, a send-back, a stale
read, a wrong signer.

ISOLATION. Every client person, on every action they can take (switcher, portal, send papers), sees their own book only: their
client list is exactly theirs, their portal carries no other client's name, draft id, draft text or request; asking for another
client's portal, request or draft gets the same refusal as a client that does not exist; a client cannot draft, review, sign, share,
see the queue, the dashboard or an audit trail. A preparer cannot touch a client they are not assigned to.

REVIEW GATE. A draft is never signed before approval; the preparer cannot review their own draft; a client cannot review; a send-back
needs notes; an approval made on text that has since changed does not hold (the draft goes back to review and cannot be signed);
an approval sent with a stale hash is refused.

SIGNED BY THE NAMED PERSON. Only the signer named on the draft can sign; the other partner cannot; the signature carries that person's
name and the hash of the approved text; a signed draft cannot be edited.

    python -m app.fin.card_f7        builds a scratch database, prints the card; exit 1 if anything fails
"""
from __future__ import annotations

import json
import random
import sys
from typing import Any

from . import evidence as EV
from . import profile as PR
from .desks import firm as F

N_CLIENTS = 50


def _expect_refused(bad: list[str], what: str, fn) -> None:
    try:
        fn()
        bad.append(f"{what}: was allowed")
    except (F.FirmError, PermissionError):
        pass


def run(n_clients: int = N_CLIENTS, seed: int = 7) -> dict[str, Any]:
    try:
        return _run(n_clients, seed)
    except Exception as e:     # a crash is a failed card, not a stopped one
        return {"clients": n_clients, "ok": False, "problems": [f"{type(e).__name__}: {e}"], "problem_count": 1, "leaks": 0, "events": 0}


def _run(n_clients: int, seed: int) -> dict[str, Any]:
    rnd = random.Random(seed)
    t = f"card7-{seed}"
    pv = PR.preview({"size": "firm", "countries": ["GB"], "wants": [], "people": []})
    ans = {**pv["answers"], "currency": "GBP", "name": "Card & Co"}
    firm = PR.apply(t, ans, PR.preview(ans)["hash"])["id"]
    go = lambda action, **a: F.run(t, action, {"firm": firm, **a})   # noqa: E731
    bad: list[str] = []
    go("person_add", name="Pia Partner", role="partner")
    go("person_add", person="pia-partner", name="Raj Partner", role="partner")
    go("person_add", person="pia-partner", name="Meg Manager", role="manager")
    cl = [go("client_add", person="pia-partner", name=f"Client {k:02d} Ltd", size=rnd.choice(["solo", "business", "personal"]))["client"]["id"]
          for k in range(n_clients)]
    names = {c: f"Client {k:02d} Ltd" for k, c in enumerate(cl)}
    preps = []
    for j in range(4):
        mine = cl[j::4]
        preps.append((go("person_add", person="pia-partner", name=f"Prep {j}", role="preparer", clients=mine)["person"]["id"], mine))
    revs = [(go("person_add", person="pia-partner", name=f"Rev {j}", role="reviewer", clients=cl[j::2])["person"]["id"], cl[j::2])
            for j in range(2)]
    persons = {c: go("person_add", person="pia-partner", name=f"Person of {names[c]}", role="client", clients=[c])["person"]["id"] for c in cl}
    signer_of = {c: rnd.choice(["pia-partner", "raj-partner"]) for c in cl}
    prep_of = {c: p for p, mine in preps for c in mine}
    for c in cl[::5]:                     # some drafts are prepared by the manager, who may review - but never their own
        prep_of[c] = "meg-manager"
    rev_of = {c: r for r, mine in revs for c in mine}
    drafts: dict[str, str] = {}
    texts: dict[str, str] = {}
    for c in cl:
        rq = go("request", person=prep_of[c], client=c, items=["bank statements", "receipts"], due="2026-10-31")["request"]
        go("provide", person=persons[c], request=rq, item="bank statements")
        body = f"Accounts for {names[c]}: profit {rnd.randint(1000, 99999)}. Secret note {rnd.randint(10**8, 10**9)}."
        texts[c] = body
        d = go("draft", person=prep_of[c], client=c, kind="accounts", title=f"Accounts {names[c]}", body=body, signer=signer_of[c])["draft"]
        drafts[c] = d["id"]
        _expect_refused(bad, f"{names[c]}: signed before approval", lambda: go("sign", person=signer_of[c], draft=d["id"]))
        _expect_refused(bad, f"{names[c]}: the preparer reviewed their own draft",
                        lambda: go("review", person=prep_of[c], draft=d["id"], verdict="approve"))
        if prep_of[c] == "meg-manager":
            _expect_refused(bad, f"{names[c]}: the manager reviewed the draft she prepared",
                            lambda: go("review", person="meg-manager", draft=d["id"], verdict="approve"))
        _expect_refused(bad, f"{names[c]}: a client reviewed", lambda: go("review", person=persons[c], draft=d["id"], verdict="approve"))
        roll = rnd.random()
        if roll < 0.2:
            _expect_refused(bad, f"{names[c]}: sent back without notes",
                            lambda: go("review", person=rev_of[c], draft=d["id"], verdict="send_back"))
            go("review", person=rev_of[c], draft=d["id"], verdict="send_back", notes="Add the depreciation note.")
            texts[c] = body + " Depreciation note added."
            go("edit", person=prep_of[c], draft=d["id"], body=texts[c])
        if 0.2 <= roll < 0.35:
            _expect_refused(bad, f"{names[c]}: an approval on a stale hash",
                            lambda: go("review", person=rev_of[c], draft=d["id"], verdict="approve", hash="0" * 64))
        go("review", person=rev_of[c], draft=d["id"], verdict="approve", hash=F._hash(texts[c]))
        if 0.35 <= roll < 0.5:                       # changed after approval: back to review, cannot be signed on the old approval
            texts[c] = texts[c] + " Late change."
            r = go("edit", person=prep_of[c], draft=d["id"], body=texts[c])
            if r["draft"]["state"] != "waiting":
                bad.append(f"{names[c]}: an edit after approval did not send it back to review")
            _expect_refused(bad, f"{names[c]}: signed on an approval of other text", lambda: go("sign", person=signer_of[c], draft=d["id"]))
            go("review", person=rev_of[c], draft=d["id"], verdict="approve")
        other = "raj-partner" if signer_of[c] == "pia-partner" else "pia-partner"
        _expect_refused(bad, f"{names[c]}: signed by the partner who is not named", lambda: go("sign", person=other, draft=d["id"]))
        _expect_refused(bad, f"{names[c]}: signed by the manager", lambda: go("sign", person="meg-manager", draft=d["id"]))
        sgd = go("sign", person=signer_of[c], draft=d["id"])["draft"]["signed"]
        want_name = "Pia Partner" if signer_of[c] == "pia-partner" else "Raj Partner"
        if sgd["name"] != want_name or sgd["hash"] != F._hash(texts[c]):
            bad.append(f"{names[c]}: signature {sgd} not by {want_name} on the approved text")
        _expect_refused(bad, f"{names[c]}: a signed draft was edited", lambda: go("edit", person=prep_of[c], draft=d["id"], body="x"))
        go("share", person="pia-partner", draft=d["id"])
    # isolation, every client
    leaks = 0
    for k, c in enumerate(cl):
        p = persons[c]
        mine = go("clients", person=p)
        if [x["id"] for x in mine["clients"]] != [c]:
            bad.append(f"{names[c]}: the switcher shows {len(mine['clients'])} clients")
        po = go("portal", person=p, client=cl[(k + 1) % len(cl)])     # asking for another client still gives only their own
        blob = json.dumps(po)
        for o in cl:
            if o != c and (names[o] in blob or drafts[o] in blob or texts[o][:40] in blob):
                leaks += 1
        if po["client"] != names[c] or len(po["shared_with_you"]) != 1 or po["shared_with_you"][0]["body"] != texts[c]:
            bad.append(f"{names[c]}: the portal does not show their own signed draft")
        other = cl[(k + 7) % len(cl)]
        for action, extra in (("draft", {"client": other, "kind": "letter", "body": "x", "signer": "pia-partner"}),
                              ("review", {"draft": drafts[other], "verdict": "approve"}), ("sign", {"draft": drafts[other]}),
                              ("share", {"draft": drafts[other]}), ("queue", {}), ("dashboard", {}), ("audit", {"client": c}),
                              ("request", {"client": c, "items": ["x"]})):
            _expect_refused(bad, f"{names[c]}: a client did {action}", lambda: go(action, person=p, **extra))
        try:
            go("provide", person=p, request="rq%d" % ((k + 7) % len(cl) + 1), item="receipts")
            bad.append(f"{names[c]}: sent papers on another client's request")
        except F.FirmError as e:
            if str(e) != "No such request for this person.":
                bad.append(f"{names[c]}: another client's request was refused in words that tell it exists: {e}")
    # preparers stay in their lane
    for pid, mine in preps:
        stranger = next(c for c in cl if c not in mine)
        _expect_refused(bad, f"{pid}: drafted for a client not assigned", lambda: go("draft", person=pid, client=stranger, kind="memo",
                                                                                   body="x", signer="pia-partner"))
        _expect_refused(bad, f"{pid}: opened another preparer's draft", lambda: go("edit", person=pid, draft=drafts[stranger], body="x"))
        q = go("queue", person=pid)
        if any(x["client"] not in {names[c] for c in mine} for x in q["to_review"] + q["to_sign"] + q["sent_back_to_me"]):
            bad.append(f"{pid}: the queue shows a client not assigned")
    # the audit trail of one client holds only that client
    c0 = cl[0]
    au = go("audit", person="pia-partner", client=c0)
    if any(e["workspace_id"] != c0 for e in au["events"]) or not au["chain"]["ok"]:
        bad.append("the audit trail mixes clients or the chain is broken")
    if not any("signed by" in e["what"] for e in au["events"]):
        bad.append("the audit trail does not show the signature")
    dash = go("dashboard", person="pia-partner")
    if dash["clients"] != n_clients or dash["drafts"]["signed"] != n_clients:
        bad.append(f"dashboard {dash['clients']} clients / {dash['drafts']} drafts")
    if leaks:
        bad.append(f"{leaks} pieces of another client seen in a portal")
    return {"clients": n_clients, "ok": not bad, "problems": bad[:20], "problem_count": len(bad), "leaks": leaks,
            "events": len(EV.events(t, limit=2000))}


def _scratch_db() -> None:
    import os
    import tempfile
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="card7_"), "card.db")
    os.environ["HOOLA_FIN_REVIEW_DIR"] = tempfile.mkdtemp(prefix="card7_review_")
    from ..config import get_settings
    get_settings.cache_clear()
    from .. import db
    db.init_db()


if __name__ == "__main__":
    _scratch_db()
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else N_CLIENTS)
    for p in r["problems"]:
        print("FAIL", p)
    print(f"F7 card: {'PASS' if r['ok'] else 'FAIL'} - {r['clients']} clients, {r['problem_count']} problems, {r['leaks']} leaks, "
          f"{r['events']} audit events")
    sys.exit(0 if r["ok"] else 1)
