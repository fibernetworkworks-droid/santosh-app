"""v0.150 Voice call check: connect to Gemini Live exactly the way a real call does and say which part it refuses.

    cd ~/apps/santosh-core && .venv/bin/python -m app.voicecheck            # the main tenant
    cd ~/apps/santosh-core && .venv/bin/python -m app.voicecheck <tenant>

Also GET /api/voice/check (owner). It tries: the full call setup -> each step of voice.SETUP_STEPS (one extra less
each time) until Gemini answers, and when it is the tool list, which single tool Gemini refuses. Then it also checks
a quiet note sent mid-call as client_content (Gemini 3.x closes the session for it). Nothing is saved or said to anyone;
each try is one short Gemini Live session (~ a few paise).
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import time

from . import life, voice
from .config import get_settings


async def _try(cfg, note: bool = False, timeout: float = 15) -> tuple[bool, str]:
    """One short session: does Gemini answer a test line? (note=True: also send a mid-call client_content note)"""
    from google.genai import types
    t0 = time.monotonic()
    try:
        async with contextlib.AsyncExitStack() as stack:
            s = await asyncio.wait_for(stack.enter_async_context(voice.connector(cfg)), timeout=20)
            await s.send_realtime_input(text="(Yeh ek test hai: bas 'haan' bolo.)")

            async def answer() -> bool:
                sent_note = False
                async for m in s.receive():
                    if getattr(m, "tool_call", None) is not None:
                        return True
                    sc = getattr(m, "server_content", None)
                    if sc is None:
                        continue
                    if sc.model_turn is not None or sc.turn_complete:
                        if not note:
                            return True
                        if not sent_note:
                            sent_note = True
                            await s.send_client_content(
                                turns=types.Content(role="user", parts=[types.Part(text="(Test note, do not reply.)")]),
                                turn_complete=False)
                            await s.send_realtime_input(text="(Ek aur test: bas 'theek' bolo.)")
                            continue
                        if sc.turn_complete:
                            return True
                return False

            ok = await asyncio.wait_for(answer(), timeout=timeout)
            return ok, "" if ok else "Gemini ne jawab nahi diya (session band)"
    except asyncio.TimeoutError:
        return False, f"timeout after {round(time.monotonic() - t0)} s"
    except Exception as e:      # noqa: BLE001 - the whole point is to report what Gemini said
        return False, str(e)[:400]


async def _setup(tenant: str):
    from . import voicelang, voicestyle
    from .agent import mcp_live
    from .avatar import service as av
    st = get_settings()
    a = av.get(tenant)
    pool = av.FEMALE_VOICES if a["gender"] == "f" else av.MALE_VOICES
    vname = a["voice"] if a.get("voice") in pool else (st.voice_default if a["gender"] == "m" else av.DEFAULT_VOICE["f"])
    context = life.context_block(tenant)
    try:
        from . import yaad
        context += "\n\n" + (yaad.voice_block(tenant, "") or "")
    except Exception:
        pass
    try:
        snap = await asyncio.to_thread(mcp_live.snapshot, tenant)
        mcp_defs, _ = mcp_live.tool_defs(snap, min(25, st.mcp_native_tools))
    except Exception:
        mcp_defs = []
    try:
        style = voicestyle.for_call(tenant)
    except Exception:
        style = {}
    langst = voicelang.start_state(tenant, "hi-IN")

    def cfg(safe: int = 0, tools: list[str] | None = None, mcp: list[dict] | None = None):
        c = voice.live_config(vname, "hi-IN", context, None, a["name"], a["gender"],
                              mcp_defs if mcp is None else mcp, langst=langst, style=style, safe=safe)
        if tools is not None:
            from google.genai import types
            c.tools = [types.Tool(function_declarations=[d for d in c.tools[0].function_declarations if d.name in tools])]
        return c
    return cfg, mcp_defs, style


async def _bisect(make, names: list[str], keep: list[str]) -> str | None:
    """The one tool (from `names`) that makes Gemini refuse; `keep` is always declared."""
    while len(names) > 1:
        half = names[: len(names) // 2]
        ok, _, _ = await _attempt(lambda: make(keep + half))
        names = names[len(names) // 2:] if ok else half
    if names:
        ok, _, _ = await _attempt(lambda: make(keep + names))
        return None if ok else names[0]
    return None


async def _attempt(build, note: bool = False, timeout: float = 15) -> tuple[bool, str, bool]:
    """v0.185.2 one attempt that mirrors the REAL call loop's affective heal: a generic setup refusal while
    enable_affective_dialog is on drops it (process-wide, like voice.py) and retries the SAME config once.
    Returns (ok, error, healed_without_affective). Without this the instrument tested every rung WITH the
    field on and reported 'nothing works' even when only the field was refused (the VPS answer, 26 Oct)."""
    from . import voice
    cfg = build()
    affective_on = bool(getattr(cfg, "enable_affective_dialog", None))
    ok, why = await _try(cfg, note=note, timeout=timeout)
    if ok or not affective_on or not voice.setup_refused(RuntimeError(why or "")):
        return ok, why, False
    voice._AFFECTIVE["ok"] = False
    ok, why = await _try(build(), note=note, timeout=timeout)
    return ok, why, True


async def run(tenant: str | None = None) -> dict:
    st = get_settings()
    tenant = tenant or st.tenant_id
    out: dict = {"model": st.gemini_live_model, "tenant": tenant, "steps": [], "say": ""}
    if not st.gemini_api_key:
        out["say"] = "GEMINI_API_KEY .env mein nahi hai: voice call chal hi nahi sakti."
        return out
    make, mcp_defs, style = await _setup(tenant)
    out["mcp_tools"] = len(mcp_defs)
    out["vocab"] = len(voice.clean_vocab(style.get("vocab")) or [])
    full = make(0)
    out["tools"] = len(full.tools[0].function_declarations) if full.tools else 0
    out["prompt_chars"] = len(full.system_instruction.parts[0].text)
    out["schema_problems"] = [f"{d.name}: {p}" for d in (full.tools[0].function_declarations if full.tools else [])
                              for p in voice.schema_problems(d.parameters_json_schema or {})]
    affective = {"refused": False}
    ok, why, healed = await _attempt(lambda: make(0))
    step = {"try": "full", "ok": ok, "error": why}
    if healed:
        step["without_affective"] = True
        affective["refused"] = True
    out["steps"].append(step)
    works_at = 0 if ok else None
    if not ok:
        for i in range(1, len(voice.SETUP_STEPS) + 1):
            ok, why2, healed2 = await _attempt(lambda i=i: make(i))
            step = {"try": "without " + ", ".join(voice.SETUP_STEPS[:i]), "ok": ok, "error": why2}
            if healed2:
                step["without_affective"] = True
                affective["refused"] = True
            out["steps"].append(step)
            if ok:
                works_at = i
                break
    out["works_at"] = works_at
    out["affective"] = affective
    culprit = None
    if works_at:
        step = voice.SETUP_STEPS[works_at - 1]
        out["refused_part"] = step
        if step == "mcp" and mcp_defs:
            bad = await _bisect(lambda extra: make(0, mcp=[m for m in mcp_defs if m["name"] in extra]),
                                [m["name"] for m in mcp_defs], [])
            culprit = bad and f"MCP tool {bad}"
        elif step in ("core_tools", "no_tools"):
            base = make(works_at - 1)
            names = [d.name for d in base.tools[0].function_declarations]
            keep = [n for n in names if n in voice.CORE_TOOLS or n in ("santosh_kaam", "side_talk")] if step == "core_tools" \
                else ["santosh_kaam"]
            rest = [n for n in names if n not in keep]
            bad = await _bisect(lambda extra: make(works_at - 1, tools=extra), rest, keep)
            culprit = bad and f"tool {bad}"
        out["culprit"] = culprit
    # Gemini 3.x and mid-call client_content (how quiet notes used to travel)
    if works_at is not None:
        ok_cc, why_cc, _ = await _attempt(lambda: make(works_at), note=True, timeout=25)
        out["mid_call_client_content"] = {"ok": ok_cc, "error": why_cc}
    # what the server now does on its own
    out["server_now"] = voice.setup_view()
    affective_note = ("Gemini enable_affective_dialog mana karta hai (generic 1007) - real calls ye khud "
                      "heal kar leti hain (bina affective ke chalti hain). ") if affective["refused"] else ""
    if works_at == 0:
        out["say"] = (affective_note + "Gemini poori call setup le raha hai. " +
                      ("Beech call mein client_content bhi chalta hai." if out.get("mid_call_client_content", {}).get("ok")
                       else "Beech call mein client_content NAHI chalta (isliye notes ab tool jawab / text ke saath jaate hain)."))
    elif works_at:
        out["say"] = (affective_note + f"Gemini '{voice.SETUP_STEPS[works_at - 1]}' ke saath call mana karta hai" +
                      (f" ({culprit})" if culprit else "") + ". Calls ab apne aap iske bina chalti hain.")
        voice.remember_setup(works_at)
    else:
        out["say"] = (affective_note + "Gemini bina affective ke BHI kisi setup ko jawab nahi de raha: " + (why or "") +
                     " (key / model naam / Google ki taraf ki dikkat; GEMINI_LIVE_MODEL check karein - "
                     "dusre model se aise test karein: GEMINI_LIVE_MODEL=<model-naam> .venv/bin/python -m app.voicecheck)")
    return out


def main() -> None:
    from .db import init_db
    init_db()
    res = asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else None))
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
