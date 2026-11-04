"""HOOLA CODER prompts - the observer's instructions (v0.480.0).

The claude-mem prompt architecture, ported: one cacheable system prefix (identity, role, focus,
skip rules), one per-event user turn (<observed_from_santosh_session> blocks with capped fields),
and one summary checkpoint. Fields are truncated head-60/tail-30 with an elision marker so the
observer knows what it did NOT see and never invents the middle.
"""
from __future__ import annotations

import json

from .modes import load_mode

OBS_FIELD_MAX_CHARS = 16_000             # per field (about 4k tokens)
MAX_OUTPUT_TOKENS = 1500

_ELLIPSIS = "\n<elided chars=%d />\n"


def _cap_field(text: str, limit: int = OBS_FIELD_MAX_CHARS) -> str:
    """Head 60% / tail 30% / elision marker 10% - the observer sees both ends, never a fake middle."""
    t = text or ""
    if len(t) <= limit:
        return t
    keep = max(200, limit - 200)
    head = int(keep * 0.667)
    tail = keep - head
    return t[:head] + _ELLIPSIS % (len(t) - keep) + (t[-tail:] if tail else "")


def observer_system(mode: dict | None = None) -> str:
    m = mode or load_mode()
    p = m["prompts"]
    types = "\n".join(f"- {t['id']}" for t in m["observation_types"])
    concepts = ", ".join(m["observation_concepts"])
    return "\n\n".join([
        p["system_identity"], p["observer_role"], p["recording_focus"], p["skip_guidance"],
        "OBSERVATION TYPES - type MUST be exactly one of:\n" + types,
        "CONCEPTS - 2-5 per observation, bare keywords only: " + concepts,
        p["field_guidance"],
        _skeleton(m),
        p["footer"],
    ])


def _skeleton(m: dict) -> str:
    return (
        "Reply with one or more <observation> blocks in EXACTLY this shape:\n"
        "<observation>\n  <type>bugfix|feature|refactor|change|discovery|decision|security_alert|"
        "security_note|sensitive</type>\n  <title>max 120 chars, the durable fact</title>\n"
        "  <subtitle>max 24 words</subtitle>\n  <facts><fact>one fact</fact><fact>another</fact></facts>\n"
        "  <narrative>full context: what was done, how it works, why it matters</narrative>\n"
        "  <concepts><concept>how-it-works</concept></concepts>\n"
        "  <files_read><file>path</file></files_read>\n  <files_modified><file>path</file></files_modified>\n"
        "</observation>\n"
        "or <skip_summary reason=\"noise\" /> when this tool use taught nothing.")


def event_block(ev: dict) -> str:
    """One tool call as the observer sees it: what happened, the (redacted) parameters, the outcome."""
    args = ev.get("args") if isinstance(ev.get("args"), (dict, list)) else {"raw": str(ev.get("args", ""))}
    try:
        args_s = json.dumps(args, ensure_ascii=False, default=str)[:OBS_FIELD_MAX_CHARS]
    except Exception:
        args_s = str(args)[:OBS_FIELD_MAX_CHARS]
    out = str(ev.get("result", ""))[:OBS_FIELD_MAX_CHARS]
    return (
        "<observed_from_santosh_session>\n"
        f"  <what_happened>{ev.get('tool', '')}</what_happened>\n"
        f"  <occurred_at>{ev.get('at', '')}</occurred_at>\n"
        f"  <conversation>{ev.get('conv', '')}</conversation>\n"
        f"  <actor>{ev.get('actor', '')}</actor>\n"
        f"  <parameters>{_cap_field(args_s)}</parameters>\n"
        f"  <outcome>{_cap_field(out)}</outcome>\n"
        "</observed_from_santosh_session>")


def observation_prompt(events: list[dict], mode: dict | None = None) -> tuple[str, str]:
    """(system, user) for a batch of tool events. The elision + redaction hints ride along."""
    m = mode or load_mode()
    body = "\n".join(event_block(e) for e in events)
    user = body + (
        "\n\nIf a <parameters> or <outcome> block above contains an <elided chars=... /> marker, that "
        "field was truncated to fit your window: describe only what you can see, never infer the elided "
        "range. Values shown as ***redacted*** were secrets BEFORE you saw them - refer to them only as "
        "'a redacted credential', never guess.\n"
        "Return one or more <observation> blocks, or a single <skip_summary reason=\"noise\" /> if every "
        "event above was routine. Never reply with an empty response or prose.")
    return observer_system(m), user


def summary_prompt(last_assistant: str, history_tail: str) -> tuple[str, str]:
    """(system, user) for the end-of-session checkpoint."""
    system = (
        "MODE SWITCH: PROGRESS SUMMARY. You are the HOOLA CODER observer writing the session's closing "
        "summary for future sessions. You have no tools and no contact with anyone.\n\n"
        "You MUST wrap your ENTIRE response in <summary>...</summary> tags with exactly these fields: "
        "<request>, <investigated>, <learned>, <completed>, <next_steps>, <notes>.\n\n"
        + load_mode()["prompts"]["summary_instruction"] +
        "\n\nIf there is genuinely nothing to summarize, reply with exactly "
        "<skip_summary reason=\"nothing durable\" />.")
    user = ("Her ask this session:\n" + (last_assistant or "(not recorded)") +
            "\n\nWhat the observer saw (oldest first):\n" + _cap_field(history_tail, 24_000) +
            "\n\nWrite the <summary> block now.")
    return system, user


# ---------------------------------------------------------------- v0.477 HOOLA NUDGE

REFLECTION_MAX_OUTPUT_TOKENS = 1200

_REFLECTION_SYSTEM = (
    "You are the quiet self-teaching memory inside Santosh, a Hindi/Hinglish voice+chat assistant. "
    "You run BETWEEN her turns, invisible: the user never reads you and can never reply to you. "
    "You have no tools and no contact with anyone - your entire output is parsed into memory writes. "
    "You never write in Hindi: memory is English so any Hoola surface can search it.\n\n"
    "YOUR JOB: look at the recent stretch of one conversation and decide what is worth KEEPING. "
    "Write durable observations (the same XML the session observer uses) and, only when the stretch "
    "reveals a reusable CLASS of task, propose a skill. Rules:\n"
    "- Observations: durable facts only (decisions, discoveries, how-things-work, credentials NEVER). "
    "Routine chatter, one-off errors and anything already obvious from the digest are noise: skip them.\n"
    "- Skills: only for a repeatable CLASS of task ('deploy-a-flask-app'), never for one incident "
    "(a name must never contain a specific date, error string, or one-off detail). Propose a skill "
    "ONLY when the stretch shows a procedure that would be done again. Use action=update to improve "
    "a skill from the CURRENT SKILLS list (its name + description are given); action=create for a new one.\n"
    "- Write at most 4 blocks total (observations + skills together). Fewer is better. If nothing is "
    "durable, reply with exactly <skip_summary reason=\"nothing durable\" />.\n\n"
    "OUTPUT SHAPES (exactly these; no prose outside them):\n"
    "<observation>\n  <type>bugfix|feature|refactor|change|discovery|decision|security_alert|"
    "security_note|sensitive</type>\n  <title>max 120 chars, the durable fact</title>\n"
    "  <subtitle>max 24 words</subtitle>\n  <facts><fact>one fact</fact></facts>\n"
    "  <narrative>full context</narrative>\n  <concepts><concept>how-it-works</concept></concepts>\n"
    "</observation>\n"
    "<skill action=\"create\" name=\"lowercase-hyphenated\" description=\"<= 60 chars, one sentence\">"
    "the instructions, markdown</skill>\n"
    "<skill action=\"update\" name=\"an-existing-skill\" description=\"<= 60 chars\">"
    "the FULL new instructions (an update replaces the body)</skill>")


def reflection_system() -> str:
    """The STABLE prefix: this prompt never changes between runs (the cheap-brain cache shape)."""
    return _REFLECTION_SYSTEM


# ---------------------------------------------------------------- v0.480 HOOLA CURATOR

CURATOR_MAX_OUTPUT_TOKENS = 1200

_CURATOR_SYSTEM = (
    "You are the memory curator inside Santosh, a Hindi/Hinglish voice+chat assistant. You run "
    "about once a week, invisible: the user never reads you and can never reply to you. You have "
    "no tools and no contact with anyone - your entire output is parsed into curation decisions. "
    "You never write in Hindi: memory is English so any Hoola surface can search it.\n\n"
    "YOU HAVE TWO JOBS on the memory vault you are shown:\n"
    "1. ARBITRATE near-duplicate pairs. The dedup ladder flagged each pair as 'maybe the same "
    "memory' (high similarity, no rare-token veto). For every pair decide:\n"
    '   - verdict="merge"   ONLY when both rows state the SAME fact about the SAME specific '
    "subject - same target, same outcome, interchangeable. Keep the older row's wording in mind; "
    "the newer row will be absorbed into it. When in doubt, do NOT merge.\n"
    '   - verdict="distinct"  the rows look alike but carry different facts (a different file, '
    "version, person, outcome, or one failed where the other succeeded).\n"
    '   - verdict="dismiss"  the NEWER row is pure noise (routine chatter, a re-run of the same '
    "command, nothing durable) and is not even worth keeping as its own memory.\n"
    "   Rules: a rare distinctive token in one title (a function name, an error code, a version) "
    "is identity, not noise - that is a distinct. Failed vs succeeded is distinct. Never merge "
    "rows from different subjects merely because they share generic words.\n"
    "2. PROMOTE recurring memories into skills. A skill names a CLASS of task ('deploy-a-flask-app'), "
    "never one incident - a name must not contain a date, an error string, or a one-off detail. "
    "Propose a skill ONLY when several memories show the same procedure that will be done again. "
    "action=update may target ONLY the skills in the CURRENT SKILLS list (its names are given).\n\n"
    "OUTPUT SHAPES (exactly these; no prose outside them):\n"
    '<pair id="7" verdict="merge" />\n'
    "<skill action=\"create\" name=\"lowercase-hyphenated\" description=\"<= 60 chars, one sentence\">"
    "the instructions, markdown</skill>\n"
    "<skill action=\"update\" name=\"an-existing-skill\" description=\"<= 60 chars\">"
    "the FULL new instructions (an update replaces the body)</skill>\n"
    "If nothing needs deciding and nothing is worth promoting, reply with exactly "
    "<skip_summary reason=\"nothing to curate\" />.")


def curator_system() -> str:
    """The STABLE prefix: this prompt never changes between runs (the cheap-brain cache shape)."""
    return _CURATOR_SYSTEM


def curator_user(pairs: list[dict], skills: list[dict], max_merges: int) -> str:
    """The one user turn: the candidate pairs (both rows, already-redacted vault content) and the
    current skill list (the read-before-write input). All text below passed the vault's privacy
    gate at capture time."""
    sk = "\n".join(f"- {s['name']}: {s['description']}" for s in skills) or "(no skills yet)"
    blocks = []
    for p in pairs:
        a, b = p["newer"], p["older"]
        blocks.append(
            f'<pair id="{p["id"]}" score="{p["score"]:.2f}">\n'
            f'  <row side="older" id="{a["id"]}" conv="{a["conv"]}" date="{str(a["created_at"])[:10]}" '
            f'seen="{a["occurrence_count"]}x">\n'
            f'    <title>{str(a["title"])[:160]}</title>\n'
            f'    <body>{str(a["narrative"])[:500]}</body>\n  </row>\n'
            f'  <row side="newer" id="{b["id"]}" conv="{b["conv"]}" date="{str(b["created_at"])[:10]}" '
            f'seen="{b["occurrence_count"]}x">\n'
            f'    <title>{str(b["title"])[:160]}</title>\n'
            f'    <body>{str(b["narrative"])[:500]}</body>\n  </row>\n'
            "</pair>")
    body = "\n".join(blocks) or "(no pending pairs this week)"
    return ("MERGE BUDGET THIS RUN: at most " + str(max_merges) + " merges.\n\n"
            "PENDING PAIRS (oldest row first - a merge absorbs the NEWER row into the OLDER):\n" +
            body +
            "\n\nCURRENT SKILLS (update only these names):\n" + sk +
            "\n\nGive one verdict per pair, then any skill blocks. Nothing to do -> "
            "<skip_summary reason=\"nothing to curate\" />.")


def reflection_user(digest: str, skills: list[dict], last_ask: str) -> str:
    """The one user turn: the redacted digest, her ask, and the current skill list (the
    read-before-write input - an update is only legal for a skill listed here)."""
    sk = "\n".join(f"- {s['name']}: {s['description']}" for s in skills) or "(no skills yet)"
    return ("HER LAST ASK:\n" + (last_ask or "(not recorded)") +
            "\n\nCURRENT SKILLS (update only these names):\n" + sk +
            "\n\nTHE RECENT STRETCH (redacted, oldest first):\n" + _cap_field(digest, 20_000) +
            "\n\nWrite the keep-worthy blocks now. At most 4. Nothing durable -> "
            "<skip_summary reason=\"nothing durable\" />.")
