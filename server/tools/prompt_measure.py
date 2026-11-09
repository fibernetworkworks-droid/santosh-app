"""Parity Phase 2: measure what a chat turn sends as its system prompt, block by block (no model call, no network).

Seeds a throw-away SQLite tenant (profile, 15 facts, a memory page), runs two real chat turns through
santosh.run_turn with the model call faked, and prints the system prompt's size per turn, whether it was
byte-identical, the size of her newest message (where the per-turn notes ride) and the old blocks one by one.

    cd server && python tools/prompt_measure.py            # small prompt (chat_small_prompt default)
    cd server && python tools/prompt_measure.py --old      # the long per-turn prompt (chat_small_prompt=false)
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    d = tempfile.mkdtemp(prefix="hoola-prompt-")
    os.environ.update(DATABASE_URL=f"sqlite:///{d}/t.db", WA_DRY_RUN="true", ANTHROPIC_API_KEY="test", SEMANTIC_OFF="1",
                      MEMORY_AUTO="false", HOOLA_ENRICH="false", KAAM_WATCH="false", HARD_JUDGE="false",
                      HARD_CHECK="false", AGENT_SELF_CHECK="false", GYAAN_GROUND="false", AGENT_FIX_SEARCH="false",
                      LOGO_WARM="false", TV_REFRESH="false", IFSC_REFRESH="false",
                      CHAT_SMALL_PROMPT="false" if "--old" in sys.argv else "true")
    os.chdir(d)
    sys.path.insert(0, HERE)
    from app import aboutme, db, life
    db.init_db()
    from app.db import Conversation, MemoryFact, Profile, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    with session() as s:
        s.merge(Profile(tenant_id="default", name="Meghana", city="Akola", language="hinglish"))
        for i in range(15):
            s.add(MemoryFact(tenant_id="default", text=f"Fact {i}: her godown in Chakan stocks {i * 10} boxes",
                             source=None if i % 2 else "auto"))
    aboutme.set_text("default", "Meghana runs Newtika Pvt Ltd from Akola. " * 30)
    from app.agent import santosh
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        sysx = system if isinstance(system, str) else "".join(b.get("text", "") for b in system)
        last = history[-1]["content"]
        lt = last if isinstance(last, str) else " ".join(b.get("text", "") for b in last if isinstance(b, dict))
        seen.append((sysx, len(lt), len(tools or [])))
        return ([{"type": "text", "text": "Done."}], "end_turn", brain)

    santosh._think = fake_think
    asks = ("hi kaise ho", "mera gst return file karna hai aur ek email bhejo")
    for msg in asks:
        asyncio.run(santosh.run_turn(conv, msg))
    for (sysx, lt, nt), msg in zip(seen, asks):
        print(f"turn {msg!r}: system {len(sysx):,} chars | her newest message {lt:,} chars | tools {nt}")
    print("system byte-identical across the two turns:", seen[0][0] == seen[1][0])
    print("\nthe old blocks (what the long prompt is built from):")
    from app.agent import admit, prompts
    from app.agent import mcp_live
    from app.config import get_settings
    fams = frozenset(admit.plan_for(asks[0], get_settings()).families)
    rows = [("work guide, full", len(prompts.SYSTEM)),
            ("work guide, cut for a 'hi' turn", len(prompts.system_text(fams)) - len(prompts._kaam_tips())),
            ("  of it: reply rules (replystyle.CHAT)", len(prompts._REPLY_RULES)),
            ("kaam tips", len(prompts._kaam_tips())),
            ("context_block (memory page + profile + facts + routines)", len(life.context_block("default", conv))),
            ("mcp_live.prompt_block", len(mcp_live.prompt_block(mcp_live.snapshot("default"), {})))]
    for mod in ("net.learning", "net.dosti", "employee.service", "mshop.service", "chai.service", "darzi.service",
                "office.service", "lekhak.service", "telecall.service", "kalam.service", "site.service",
                "appmaker.service", "aftersales.service", "wapsi.service", "brand.service", "ads.service"):
        try:
            rows.append((f"{mod}.prompt_block", len(importlib.import_module("app." + mod).prompt_block("default") or "")))
        except Exception as e:   # noqa: BLE001
            rows.append((f"{mod}.prompt_block (failed: {e})", 0))
    for name, n in rows:
        print(f"{n:9,}  {name}")


if __name__ == "__main__":
    main()
