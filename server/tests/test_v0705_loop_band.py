"""v0.705 LOOP BAND: her 'saare promotion mail archive kar do' looped ~40 rounds for 7 minutes - an archived Gmail mail
keeps its category label, so folder=promotions (label:promotions) kept returning the mails just archived; every round
had new inputs, so the same-call breaker never fired."""
import json

from app.agent import breaker as B
from app.mailbox import gmail


def test_inbox_tabs_mean_still_in_inbox():
    for tab in ("promotions", "social", "updates", "forums"):
        assert gmail.FOLDER_Q[tab] == f"category:{tab} in:inbox"
    assert "in:inbox" in gmail.FOLDER_Q["primary"]


def test_list_query_for_promotions():
    seen = {}

    class Box(gmail.GmailBox):
        def _req(self, method, path, **kw):
            seen["q"] = (kw.get("params") or {}).get("q")
            return {"messages": []}
    b = Box("k", "a@b.c", lambda f: "t")
    b.list("promotions", limit=5)
    assert seen["q"] == "category:promotions in:inbox"


def test_same_tool_many_times_is_paused_then_stopped():
    br = B.Breaker()
    for i in range(B.NAME_STEER):
        assert br.before("email_check", {"limit": i}) is None
    note = br.before("email_check", {"limit": 99})
    assert note and "loop" in note
    assert br.before("email_check", {"limit": 100}) is None      # genuinely new work may go on
    out = None
    for i in range(B.NAME_STOP):
        out = br.before("email_check", {"limit": 200 + i})
        if out:
            break
    assert br.stopped and "email_check" in br.stopped


def test_threads_description_names_in_inbox():
    from app.agent import email_tools as et
    d = next(t for t in et.EMAIL_TOOLS if t["name"] == "email_threads")["description"]
    assert "in:inbox" in d and json.dumps(d)
