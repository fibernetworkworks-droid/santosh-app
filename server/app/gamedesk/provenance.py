"""v0.455 PROVENANCE (docs/GAME_MOAT_PLAN.md §5.1 item 3): where every piece of a shipped game came from, as a fact
she can read off - and the human record that is the only part of it she may actually own.

WHY THIS AND NOT A NICER FEATURE. The moat research found two things that both land on the same missing record:

1. THE STORES ASK, AND SHE SIGNS. Steam's Content Survey asks the publisher to declare "any kind of content that
   ships with your game and is consumed by players" made with AI tools, and separately whether the game generates
   content WHILE RUNNING (that second one carries an extra guardrails obligation). Unity's Asset Store requires the
   same disclosure; Fab requires a `CreatedWithAI` tag. Completing Steam's survey is a promise to Valve, checked in
   pre-release review. Hoola cannot make that promise - SHE does - but she could not make it honestly either,
   because nothing wrote down which model made which file.

2. AI OUTPUT MAY NOT BE HERS AT ALL. The US Copyright Office (Jan 2025, Part 2) holds that prompt-only output is
   not copyrightable; India's Copyright Act s.2(d)(vi) asks for the human who "causes the work to be created" and
   the Copyright Office rejected an AI as author in 2026. So a game made mostly of generated assets may have
   little or nothing enforceable in it - no claim against someone who lifts its art. What IS protectable is human
   creative selection, arrangement and modification. Hoola already records every one of those acts (her approvals,
   her rejections, her own uploads, the decisions log with `by="her"`) - it had just never been collected and shown
   to her as what it is.

HOW IT STAYS HONEST:
- It is READ-ONLY and derived. Nothing here is a new claim: the model names come from `ai.used()` written onto each
  build, the asset sources from `assets.KINDS[kind]["source"]` as declared in code, her acts from the decisions log
  and the approvals that already exist.
- GENERATIVE and CODE-MADE are not the same thing and are never merged. A sound effect built by `sfx.py` from a
  preset and a seed is arithmetic, not a generative model; declaring it as AI-generated art would be a FALSE
  statement on her survey. So is a Blender-scripted mesh. They are listed separately and named as procedural.
- HER OWN UPLOADS are neither: they are her files, her copyright, and the strongest thing in the record.
- ONLY WHAT SHIPS counts. An asset that was made, priced and never approved is not in the game, so it is not on the
  survey. The record follows `approved`, not `created`.
- WHERE IT IS A JUDGEMENT CALL IT SAYS SO rather than deciding for her. The game's GDScript is the clearest one:
  Valve's January 2026 rewrite exempted AI dev tools such as code assistants, and code is not "consumed by
  players" the way art is - but a game whose code was written by a model start to finish is not obviously the same
  case as a human using an assistant. That tension is printed, with both readings, and left to her.
- IT NEVER SAYS THE DECLARATION IS CORRECT. The last line of every answer is that she signs it, not Hoola.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from ..db import session
from . import service as G

log = logging.getLogger("santosh.gamedesk")

# How each asset kind is actually made. Read from assets.KINDS["source"] at run time; this maps that source to what a
# store survey needs to know about it. Keeping the mapping HERE and not in a prompt is the point.
GENERATIVE = {"photogen": "a generative image model", "lyria": "a generative music model",
              "tts": "a generative text-to-speech voice"}
PROCEDURAL = {"synth": "built by code from a preset and a seed (no model: arithmetic)",
              "blender": "built by a Blender script (no model: geometry from code)"}
HER_OWN = {"upload": "her own file, uploaded by her", "her upload": "her own file, uploaded by her"}
# v0.810 the free library: made by people, published CC0, never AI. Named with its library and licence.
LIBRARY = {"library:kenney": "from the free library: Kenney, CC0 (made by a person, not by AI)",
           "library:polyhaven": "from the free library: Poly Haven, CC0 (made by people, not by AI)",
           "library:ambientcg": "from the free library: ambientCG, CC0 (made by a person, not by AI)"}


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _live(tenant: str, gid: str) -> tuple[Any, dict]:
    g = G._get(tenant, gid)
    good = G._good(g)
    return g, (good[-1] if good else {})


# ---------------------------------------------------------------- 1. the code
def code_record(tenant: str, gid: str) -> dict[str, Any]:
    """Which model wrote the live build, from what the build itself recorded. Older builds have no record and say so
    rather than guessing a model name."""
    g, live = _live(tenant, gid)
    vers = [v for v in (g.versions or []) if v.get("ok")]
    models: list[str] = []
    for v in vers:
        for m in v.get("models") or []:
            if m not in models:
                models.append(m)
    live_models = list(live.get("models") or [])
    return {"live_version": live.get("n"), "at": live.get("at"), "source_hash": live.get("src"),
            "files": len(live.get("files") or []), "models_live_build": live_models,
            "models_ever": models,
            "unrecorded": bool(vers and not models),
            "note": ("This build recorded no model name: it was made before v0.455 started writing it down, or no new "
                     "code was asked for (a data-only rebuild writes none)." if not live_models else
                     "GDScript written by the model(s) named, from the approved design document."),
            "runtime_generation": False,
            "runtime_note": ("The game calls no model while it runs. HoolaRuntime talks only to its own play-link host, "
                             "for the live config and opt-in telemetry, and the play page's CSP allows nothing else. So "
                             "Steam's LIVE-generated question is a plain No, and its guardrails obligation does not apply.")}


# ---------------------------------------------------------------- 2. the assets that actually ship
def assets_record(tenant: str, ref: str) -> dict[str, Any]:
    from . import assets as A
    st = _studio(tenant, ref)
    A.ensure_table()
    with session() as s:
        rows = s.scalars(select(A.GameAsset).where(A.GameAsset.studio_id == st.id)).all()
        for r in rows:
            s.expunge(r)
    shipped: list[dict] = []
    made_not_shipped = 0
    for a in rows:
        if not a.approved:
            made_not_shipped += 1
            continue
        hist = [h for h in (a.history or []) if int(h.get("v") or 0) == int(a.approved)]
        h = hist[-1] if hist else {}
        src = str(h.get("source") or (A.KINDS.get(a.kind) or {}).get("source") or "")
        spec = dict(a.spec or {})
        shipped.append({"key": a.key, "kind": a.kind, "version": a.approved, "at": h.get("at"),
                        "source": src,
                        "how": GENERATIVE.get(src) or PROCEDURAL.get(src) or HER_OWN.get(src) or LIBRARY.get(src) or f"source '{src}'",
                        "kind_of_making": ("generative" if src in GENERATIVE else
                                           "procedural" if src in PROCEDURAL else
                                           "hers" if src in HER_OWN else
                                           "library" if src in LIBRARY else "unknown"),
                        "licence": (h.get("meta") or {}).get("licence"), "credit": (h.get("meta") or {}).get("credit"),
                        "model": (h.get("meta") or {}).get("model"),
                        "prompt": (a.words or "")[:300] or None,
                        "seed": spec.get("seed"), "preset": spec.get("preset"),
                        "cost_inr": round(float(h.get("cost_inr") or 0), 2),
                        "versions_made": a.version, "she_picked_version": a.approved})
    gen = [x for x in shipped if x["kind_of_making"] == "generative"]
    proc = [x for x in shipped if x["kind_of_making"] == "procedural"]
    hers = [x for x in shipped if x["kind_of_making"] == "hers"]
    unknown = [x for x in shipped if x["kind_of_making"] == "unknown"]
    lib = [x for x in shipped if x["kind_of_making"] == "library"]
    return {"shipped": shipped, "generative": gen, "procedural": proc, "hers": hers, "unknown": unknown, "library": lib,
            "counts": {"in_the_game": len(shipped), "generative": len(gen), "procedural": len(proc),
                       "hers": len(hers), "unknown": len(unknown), "made_but_never_approved": made_not_shipped},
            "note": ("Only APPROVED assets are in the game, so only those are on a store survey. "
                     f"{made_not_shipped} asset(s) were made and never approved - they ship with nothing."),
            "procedural_warning": ("A sound effect from a preset and a seed, and a Blender-scripted mesh, are made by "
                                   "code, not by a generative model. Declaring them as AI-generated content would be a "
                                   "false statement, so they are listed apart.")}


# ---------------------------------------------------------------- 3. the human record (the only part she may own)
def human_record(tenant: str, ref: str) -> dict[str, Any]:
    """What SHE chose, changed, rejected and made. Under both the US and the Indian position this - creative
    selection, arrangement and modification - is what can be protected; the generated layer may be nobody's."""
    from . import assets as A
    from . import studio as S
    st = _studio(tenant, ref)
    full = S.get(tenant, st.id)
    tasks = full.get("tasks") or []
    decisions = [d for d in (full.get("decisions") or []) if str(d.get("by") or "") == "her"]
    A.ensure_table()
    with session() as s:
        rows = s.scalars(select(A.GameAsset).where(A.GameAsset.studio_id == st.id)).all()
        picked = [{"key": r.key, "kind": r.kind, "chose_version": r.approved, "of_versions_made": r.version}
                  for r in rows if r.approved and (r.version or 0) > 1]
        rejected = [{"key": r.key, "kind": r.kind} for r in rows if r.status == "rejected"]
        uploaded = [{"key": r.key, "kind": r.kind} for r in rows
                    if any(str(h.get("source") or "") in ("upload", "her upload") for h in (r.history or []))]
    her_tasks = [t for t in tasks if str(t.get("source") or "") == "her"]
    sent_back = [t for t in tasks if str(t.get("status") or "") in ("dropped",) or t.get("review")]
    acts = (len(decisions) + len(picked) + len(rejected) + len(uploaded) + len(her_tasks))
    return {"decisions_she_made": [{"text": d.get("text"), "why": d.get("why"), "at": d.get("at")} for d in decisions[:40]],
            "asset_versions_she_chose": picked, "assets_she_rejected": rejected, "files_she_uploaded": uploaded,
            "tasks_she_asked_for": len(her_tasks), "tasks_sent_back_or_reviewed": len(sent_back),
            "counts": {"decisions": len(decisions), "versions_chosen": len(picked), "rejected": len(rejected),
                       "uploaded": len(uploaded), "her_tasks": len(her_tasks), "total_acts": acts},
            "why_it_matters": ("The US Copyright Office (Jan 2025) holds that prompt-only output is not copyrightable, "
                               "and India's Copyright Act asks for the human who caused the work to be created - the "
                               "Copyright Office rejected an AI as author in 2026. What is protectable is human "
                               "creative selection, arrangement and modification. This list is that record, kept as it "
                               "happened; it is not legal advice and a lawyer should see it before you rely on it."),
            "thin_warning": ("Very few human acts are recorded for this game, so there may be little in it that is "
                             "protectable. Choosing between versions, editing what comes back and writing your own "
                             "decisions is what builds that record." if acts < 5 else "")}


# ---------------------------------------------------------------- 4. the store answers (drafted, she signs)
def steam_survey(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    a = assets_record(tenant, ref)
    c = code_record(tenant, st.game_id)
    gen_kinds = sorted({x["kind"] for x in a["generative"]})
    models = sorted({x["model"] for x in a["generative"] if x.get("model")} | set(c["models_live_build"]))
    pre: list[str] = []
    if a["generative"]:
        human = "art" if any(k in gen_kinds for k in ("sprite", "icon", "ui", "background")) else ""
        parts = [p for p in (human, "music" if "music" in gen_kinds else "", "voice lines" if "voice" in gen_kinds else "") if p]
        pre.append(f"This game ships {len(a['generative'])} generated asset(s) consumed by players"
                   + (f" ({', '.join(parts)})" if parts else "") + ". Made with: "
                   + (", ".join(sorted({x['model'] or x['how'] for x in a['generative']})) or "a generative model")
                   + ". Every one was reviewed and approved by the developer before it entered the build.")
    if a["procedural"]:
        pre.append(f"NOT declared as AI, and here is why: {len(a['procedural'])} sound/geometry asset(s) are produced by "
                   "code from a preset and a seed (no model is involved), which is procedural generation, not "
                   "generative AI.")
    if a["hers"]:
        pre.append(f"{len(a['hers'])} asset(s) are the developer's own files.")
    if a.get("library"):
        pre.append(f"{len(a['library'])} asset(s) come from free CC0 libraries (Kenney / Poly Haven / ambientCG): made by "
                   "people and released to the public domain, so they are not AI content and need no credit.")
    return {"game": st.title, "studio": st.number,
            "pre_generated": {"answer": "Yes" if a["generative"] else "No",
                              "draft": " ".join(pre) or "No generated content ships with this game.",
                              "models": models},
            "live_generated": {"answer": "No", "draft": c["runtime_note"],
                               "guardrails_needed": False},
            "judgement_calls": ([{"item": "the game's own GDScript",
                                  "fact": f"written by {', '.join(c['models_live_build'])}" if c["models_live_build"]
                                          else "written by a model; this build did not record which",
                                  "one_reading": "Valve's January 2026 rewrite exempts AI development tools such as code "
                                                 "assistants, and code is not content 'consumed by players' the way art is "
                                                 "- on that reading it is not declared.",
                                  "other_reading": "A game whose code a model wrote start to finish is not plainly the same "
                                                   "case as a person using an assistant - on that reading you declare it.",
                                  "who_decides": "You do. Hoola will not answer this one for you."}]
                                if (c["models_live_build"] or c["models_ever"]) else []),
            "unknowns": ([f"{len(a['unknown'])} shipped asset(s) have a source Hoola cannot classify - open them before "
                          "you answer."] if a["unknown"] else [])
                        + (["This build recorded no model name (made before v0.455)."] if c["unrecorded"] else []),
            "you_sign_it": ("Completing Steam's Content Survey is YOUR promise to Valve, checked in pre-release review, "
                            "that the game holds no illegal or infringing content. Hoola drafts the answer from what it "
                            "wrote down; it cannot make that promise for you, and this is not legal advice.")}


def disclosure_line(tenant: str, ref: str) -> dict[str, Any]:
    """One line for a store page, a Unity Asset Store listing or Fab's CreatedWithAI tag."""
    a = assets_record(tenant, ref)
    n = len(a["generative"])
    if not n:
        return {"needs_tag": False,
                "line": "No generative-AI content ships in this game.",
                "note": "Procedural sound and geometry are made by code, not by a model." if a["procedural"] else ""}
    kinds = sorted({x["kind"] for x in a["generative"]})
    return {"needs_tag": True,
            "line": (f"This game contains AI-generated content: {', '.join(kinds)} "
                     f"({n} asset{'s' if n != 1 else ''}), each reviewed and approved by the developer."),
            "fab_tag": "CreatedWithAI",
            "note": "Fab requires the CreatedWithAI tag where a material portion is generated; Unity's Asset Store "
                    "requires the same disclosure in the listing. Mistagging breaks their terms."}


# ---------------------------------------------------------------- 5. one sheet
def sheet(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    a = assets_record(tenant, ref)
    return {"studio": st.number, "title": st.title, "game_id": st.game_id,
            "code": code_record(tenant, st.game_id), "assets": a,
            "human": human_record(tenant, ref), "steam": steam_survey(tenant, ref),
            "disclosure": disclosure_line(tenant, ref),
            "how_to_read_it": ("Every line here was recorded when the thing happened - no part of it is worked out "
                               "afterwards by a model. Generated, code-made and your own files are kept apart because "
                               "a store survey asks about only the first.")}
