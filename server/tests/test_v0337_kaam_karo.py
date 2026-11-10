"""v0.337 KAAM KARO (owner: "GO 1" after the first live tool card: 23/26 right first picks).
1. The one real miss: "ABC Traders ke liye 3 items ka quotation PDF bana do: Chair 2500 x 10, Table 6000 x 2" got words,
   no tool. A file whose content she gave is a clear ask - make it now, small missing details blank + one line after.
2. A fair card: her ID details before a form (id_locker) is a right first step, and ONE real question is right where
   the ask truly has no subject ("customer ki complaint register karo")."""
import asyncio


def test_a_file_with_its_content_is_made_now():
    from app.agent import replystyle
    from app.agent.tools import TOOLS
    assert "make it NOW" in replystyle.CHAT and "Never ask before the first draft" in replystyle.CHAT
    d = {t["name"]: t["description"] for t in TOOLS}
    assert d["doc_studio"].startswith("LANE: ") and "never ask before the first draft" in d["doc_studio"]


def _card(monkeypatch, blocks):
    from app.agent import santosh
    from app.quality import toolchoice as T

    async def think(*a, **k):
        return blocks, "end_turn", "claude"
    monkeypatch.setattr(santosh, "_think", think)
    asks = {a["id"]: a for a in T.fresh_asks()}
    return T, asks


def test_her_details_first_counts_for_a_form(monkeypatch):
    from app.config import get_settings
    T, asks = _card(monkeypatch, [{"type": "tool_use", "id": "t1", "name": "id_locker", "input": {}}])
    form = next(a for a in asks.values() if a["text"].startswith("passport renewal"))
    r = asyncio.run(T._first_pick(form, "claude", get_settings()))
    assert r["right"] and r["pick"] == "id_locker"


def test_one_real_question_counts_only_where_the_ask_has_no_subject(monkeypatch):
    from app.config import get_settings
    T, asks = _card(monkeypatch, [{"type": "text", "text": "Kis customer ki complaint hai, aur kya shikayat hai?"}])
    complaint = next(a for a in asks.values() if a["text"].startswith("customer ki complaint"))
    r = asyncio.run(T._first_pick(complaint, "claude", get_settings()))
    assert r["right"] and r["asked"]
    quote = next(a for a in asks.values() if "quotation PDF" in a["text"])
    r = asyncio.run(T._first_pick(quote, "claude", get_settings()))
    assert not r["right"] and not r["asked"]            # the quotation had its content: words are a miss


def test_the_card_line_shows_fair_questions():
    from app.quality import toolchoice as T
    card = {"kind": "live", "brain": "claude", "set": 1, "asks": 2, "answered": 2, "right": 2, "via_search": 0,
            "no_tool": 1, "asked": 1, "errors": 0, "rows": []}
    assert "a fair question 1" in T.lines(card)[0]
