"""v0.246 FULL CLAUDE MODE proof: the long-chat memory quiz (run it on the VPS, it uses the REAL brain).

A long chat (default 300 exchanges) is planted with 20 details far apart (file names, ids, her exact instructions).
Then Hoola is asked about each one, three times over, in a fresh copy of the same chat per mode:
  hoola   = the v0.108 40-49 exchange window          (CHAT_CONTEXT=hoola)
  full    = Phase 1, whole chat + safety net          (CHAT_CONTEXT=claude, CHAT_COMPACT=false)
  compact = Phase 1 + 2, whole chat + checkpoint      (CHAT_CONTEXT=claude, CHAT_COMPACT=true)
Score = how many answers contain the planted detail. Costs real tokens: about 3 x 20 model calls on a big chat.

    cd ~/apps/santosh-core && .venv/bin/python ~/santosh_app/server/tools/memory_quiz.py            # all modes
    cd ~/apps/santosh-core && .venv/bin/python ~/santosh_app/server/tools/memory_quiz.py --modes compact --questions 5

Needs the keys from the VPS .env (read from the current folder). Writes nothing to her database: every mode runs on a
throw-away SQLite file in /tmp.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]

PLANTS = [
    ("Sharma ji ki invoice file ka naam QZ17_Sharma_March.pdf rakhna", "Sharma ji ki invoice file ka naam kya rakha tha?", "QZ17_Sharma_March"),
    ("Mehta Traders ka order number ORD-55821 hai", "Mehta Traders ka order number kya tha?", "55821"),
    ("Report hamesha Marathi mein banana, English mein nahi", "Report kis bhasha mein banani hai?", "Marathi"),
    ("Godown ka naya pata Plot 44, Bhosari MIDC hai", "Godown ka naya pata kya hai?", "Bhosari"),
    ("Riya ka birthday 14 August ko hai", "Riya ka birthday kab hai?", "14 August"),
    ("Supplier Kapoor Steels ka GST state code 27 hai", "Kapoor Steels ka state code kya tha?", "27"),
    ("Meeting room ka wifi naam FNW-Guest-5G hai", "Meeting room ka wifi naam kya hai?", "FNW-Guest-5G"),
    ("Diwali offer ka code DIWALI-LX9 rakhna", "Diwali offer ka code kya rakha tha?", "LX9"),
    ("Truck number MH14-KQ-7781 se maal aayega", "Maal kis truck se aayega?", "7781"),
    ("Client Joshi ko quotation sirf PDF mein bhejna, Excel nahi", "Joshi ko quotation kis format mein bhejni hai?", "PDF"),
    ("Naye intern ka naam Aarav Kulkarni hai", "Naye intern ka naam kya hai?", "Aarav"),
    ("Warehouse ka CCTV password reset ticket TCK-4410 hai", "CCTV reset ka ticket number kya tha?", "4410"),
    ("Monthly rent 38,500 rupaye har 5 tarikh ko jaata hai", "Rent kis tarikh ko jaata hai?", "5"),
    ("Website ka naya domain hoola-bakery.in liya hai", "Naya domain kaunsa liya tha?", "hoola-bakery"),
    ("Pune branch ka manager Sameer Deshpande hai", "Pune branch ka manager kaun hai?", "Sameer"),
    ("Price list ki sheet ka naam PL_2026_Q4_final hai", "Price list sheet ka naam kya hai?", "PL_2026_Q4"),
    ("Accountant ko har Shukravar ko report bhejni hai", "Accountant ko report kis din bhejni hai?", "Shukravar"),
    ("Courier ke liye Blue Dart account BD-99812 use karna", "Courier account number kya hai?", "99812"),
    ("Annual maintenance contract 31 March ko khatam hota hai", "AMC kab khatam hota hai?", "31 March"),
    ("Brand ka rang hamesha teal aur saffron rakhna", "Brand ke rang kaunse hain?", "teal"),
]
FILLER = ["aaj ka mausam kaisa hai", "ek chhota email draft karo", "kal ki meeting yaad dilana", "list mein doodh daalo",
          "ek motivational line likho", "sales ka total batao", "ek WhatsApp message ka draft banao", "kaam ki list dikhao"]
MODES = {"hoola": {"CHAT_CONTEXT": "hoola"},
         "full": {"CHAT_CONTEXT": "claude", "CHAT_COMPACT": "false"},
         "compact": {"CHAT_CONTEXT": "claude", "CHAT_COMPACT": "true"}}


def _build(conv_n: int, plants: list[tuple[str, str, str]]):
    from app.db import Conversation, Message, session
    with session() as s:
        c = Conversation(tenant_id="default", title="memory quiz")
        s.add(c)
        s.flush()
        cid = c.id
    gap = max(1, conv_n // (len(plants) + 1))
    with session() as s:
        for i in range(conv_n):
            k = i // gap - 1
            her = plants[k][0] if (i % gap == 0 and 0 <= k < len(plants)) else f"{FILLER[i % len(FILLER)]} ({i})"
            s.add(Message(conversation_id=cid, role="user", content=her, display=her))
            ans = "Theek hai, yaad rakha." if her in [p[0] for p in plants] else f"Ho gaya ({i})."
            s.add(Message(conversation_id=cid, role="assistant", content=[{"type": "text", "text": ans}], display=ans))
    return cid


async def _run_mode(mode: str, conv_n: int, q: int) -> dict:
    for k, v in MODES[mode].items():
        os.environ[k] = v
    from app.config import get_settings
    get_settings.cache_clear()
    from app import db
    db.init_db(f"sqlite:///{tempfile.mkdtemp(prefix='hoola-quiz-')}/quiz.db")
    plants = PLANTS[:q]
    cid = _build(conv_n, plants)
    from app.agent import run_turn
    got = []
    for fact, ask, want in plants:
        out = await run_turn(cid, ask, tenant_id="default")
        ok = want.lower() in (out or "").lower()
        got.append({"ask": ask, "want": want, "ok": ok, "answer": (out or "")[:160]})
        print(f"  [{mode}] {'OK ' if ok else 'MISS'} {ask} -> {(out or '')[:90]!r}", flush=True)
    from app.agent import context
    return {"mode": mode, "score": sum(g["ok"] for g in got), "of": len(got),
            "last_reading": context.LAST.get(cid, {}), "answers": got}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modes", default="hoola,full,compact")
    ap.add_argument("--exchanges", type=int, default=300)
    ap.add_argument("--questions", type=int, default=20)
    a = ap.parse_args()
    sys.path.insert(0, str(HERE))
    os.environ.setdefault("MEMORY_AUTO", "false")      # the quiz measures the chat window, not the fact picker
    os.environ.setdefault("KAAM_WATCH", "false")
    os.environ["FCM_SERVICE_ACCOUNT_FILE"] = ""         # never a push to her phone from a quiz
    os.environ["WA_DRY_RUN"] = "true"                   # never a real WhatsApp message
    os.environ["CALL_RECEIPT"] = "false"
    results = []
    for m in [x.strip() for x in a.modes.split(",") if x.strip() in MODES]:
        print(f"== {m} ==", flush=True)
        results.append(asyncio.run(_run_mode(m, a.exchanges, max(1, min(a.questions, len(PLANTS))))))
    print(json.dumps([{k: r[k] for k in ("mode", "score", "of")} for r in results], indent=1))


if __name__ == "__main__":
    main()
