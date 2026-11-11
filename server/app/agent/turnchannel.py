"""G6 of docs/LANGGRAPH_TURN_PLAN.md - voice is a CHANNEL of the same turn graph, not a second engine (only when
`chat_graph` is on; the old loop never imports this module).

Bug class 10: a call and a chat were two engines and every feature was wired twice (v0.442 every tool on a call,
v0.624 a job never turned into a reminder, v0.630-633 the call brain, v0.660 the call reads the chat, v0.692 a call
reaches the chat's long job). On the graph path a call's brain ask (voice.Call._delegate -> turn_inbox.run_owned ->
santosh.run_turn) already runs through the SAME graph as a chat turn - the same prepare / model / tools / check /
finish / deliver nodes, the G1 tool ledger, the G2 ticket + Stop, the G3 facts, the G5 delivery record. What makes it
a call is only:

  * the CHANNEL - "call" when the run was asked by a live call (the ticket `turndeliver.CALL` that
    voice.Call._delegate sets around the job's task) or runs as the call brain (`santosh.VOICE_BRAIN_NOW`), else
    "chat". The prepare node writes it into the checkpointed state, so a call ask resumed after a restart keeps its
    channel (and its profile) instead of turning into a chat turn of the full brain;
  * the PROFILE - the call brain's speed choices, as data of the prepare node (`profile()`): Haiku
    (`voice_brain_model`), the short history (`voice_brain_history` exchanges, earlier tool results cut to
    `voice_brain_result_chars`), the memory read capped at `voice_brain_memory_s`, and no compaction / thinking / hint
    lookup / MCP wait / hard-ask judge / long-job segment. The shared step functions in agent/santosh.py read these
    from the same switch they always did (`VOICE_BRAIN_NOW`, which the graph restores from the profile on resume) -
    there is ONE engine, the channel only changes its settings;
  * the DELIVERY - the deliver node tells a live call through the call's own path (the tool answer, or
    Call._late_result -> push_news -> _tell_quietly at a pause), once, from the delivery record (`call` channel), and
    never pushes to the phone what she heard on the call; a call that has ended gets the result in the chat (the reply
    row + its push) and the next call does not tell it again.

Gemini-only things stay in voice.py: the audio, the live session, parking, billing, the persona, the declared tool
menu (VOICE_TOOL_NAMES) and the spoken-claim check's audio side."""
from __future__ import annotations

CALL, CHAT = "call", "chat"


def current(conversation_id: str = "") -> tuple[str, bool]:
    """(channel, brain) of the run starting now: the call's ticket for this conversation / the call brain flag."""
    from . import santosh as S
    from . import turndeliver as D
    brain = bool(S.VOICE_BRAIN_NOW.get())
    t = D.CALL.get()
    asked = isinstance(t, dict) and (not conversation_id or t.get("conv") == conversation_id)
    return (CALL if (asked or brain) else CHAT), brain


def profile(settings, channel: str, brain: bool) -> dict:
    """The prepare node's per-channel settings (checkpointed with the run). A chat run has the chat's own settings
    (nothing to override); a call brain run has the speed choices of v0.630-v0.645."""
    if channel != CALL or not brain:
        return {"channel": channel, "brain": False}
    return {"channel": CALL, "brain": True,
            "model": str(getattr(settings, "voice_brain_model", "") or ""),
            "history_exchanges": int(getattr(settings, "voice_brain_history", 0) or 0),
            "result_chars": int(getattr(settings, "voice_brain_result_chars", 0) or 0),
            "memory_s": float(getattr(settings, "voice_brain_memory_s", 2.5) or 2.5),
            "compaction": False, "thinking": False, "hint_lookup": False, "mcp_wait": False, "hard_judge": False,
            "job_segment": False}
