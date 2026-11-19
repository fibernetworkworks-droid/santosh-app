"""Film Desk PREVIS (shot-plan checks): the shot list as a timeline, and the problems a person would circle, all in CODE.

Register: docs/research/film_industry/00_INDEX.md  (previs / shot list / storyboard). Pure functions over `shots` and the parsed
`scenes`: no database, no network, no model. It does not draw or generate anything: the animatic stays the studio's free preview.

Honest limits: the 180-degree rule, lens choice and blocking need a floor plan and a human eye, so they are NOT checked here; the
camera 'size' comes from the studio's camera names only. Timings are estimates (speech 2.5 words a second, the parser's own rate).
"""
from __future__ import annotations

from typing import Any

SPEECH_WPS = 2.5            # words per second, the same rate the script parser uses
WIDE_CAMS = ("static", "dolly_out", "pan_left", "pan_right", "crane_up", "drone", "orbit", "tilt_up", "tilt_down")
# what a camera move asks of the unit (names are the studio's own)
GEAR = {"dolly_in": "dolly + track", "dolly_out": "dolly + track", "tracking": "gimbal / steadicam or dolly",
        "crane_up": "crane / jib", "drone": "drone (flying permission and licensed pilot needed)", "handheld": "handheld rig",
        "orbit": "dolly on a circular track or gimbal", "pan_left": "fluid head", "pan_right": "fluid head",
        "tilt_up": "fluid head", "tilt_down": "fluid head", "static": "tripod"}
RUN_LIMIT = 4               # same camera this many shots in a row = monotony flag
TOL = 0.15                  # total vs target runtime


def previs(shots: list[dict[str, Any]], scenes: list[dict[str, Any]], runtime_target_s: int | None = None) -> dict[str, Any]:
    if not shots:
        return {"shots": 0, "note": "Make the shot list first (action=shots).", "flags": []}
    by_scene = {sc["id"]: sc for sc in scenes}
    order = {sc["id"]: sc["n"] for sc in scenes}
    ordered = sorted(shots, key=lambda x: (order.get(x.get("scene"), 999), str(x.get("id"))))
    t = 0
    timeline, flags = [], []

    def flag(kind: str, text: str) -> None:
        flags.append({"kind": kind, "text": text})

    for sh in ordered:
        dur = int(sh.get("duration") or 0)
        row = {"id": sh.get("id"), "scene": sh.get("scene"), "camera": sh.get("camera") or "", "start_s": t, "end_s": t + dur,
               "duration_s": dur, "characters": list(sh.get("characters") or []), "has_dialogue": bool(sh.get("dialogue")),
               "gear": GEAR.get(sh.get("camera") or "", "")}
        t += dur
        timeline.append(row)
        sc = by_scene.get(sh.get("scene"))
        if not sh.get("camera"):
            flag("measured", f"{sh.get('id')}: the camera is not decided (how will it be filmed?).")
        if sh.get("dialogue"):
            need = len(str(sh["dialogue"]).split()) / SPEECH_WPS
            if dur + 0.5 < need:
                flag("measured", f"{sh.get('id')}: the dialogue needs ~{need:.1f} s but the shot is {dur} s: make the shot longer or the line shorter.")
            if not sh.get("speaker"):
                flag("measured", f"{sh.get('id')}: there is dialogue but the speaker is not decided.")
        if sc is not None:
            allowed = {c.lower() for c in sc.get("characters") or []}
            odd = [c for c in sh.get("characters") or [] if str(c).lower() not in allowed]
            if odd:
                flag("measured", f"{sh.get('id')}: {', '.join(odd)} are not characters of this scene.")
    # scene by scene
    per_scene = []
    for sc in scenes:
        mine = [r for r in timeline if r["scene"] == sc["id"]]
        secs = sum(r["duration_s"] for r in mine)
        cams = sorted({r["camera"] for r in mine if r["camera"]})
        per_scene.append({"scene": sc["id"], "n": sc["n"], "heading": sc.get("heading", ""), "shots": len(mine), "shot_seconds": secs,
                          "script_seconds": int(sc.get("seconds") or 0), "cameras": cams})
        if not mine:
            flag("measured", f"Scene {sc['n']} ({sc.get('heading', '')[:40]}): has no shot.")
            continue
        if len(mine) >= 2 and secs and sc.get("seconds") and abs(secs - int(sc["seconds"])) > max(6, 0.5 * int(sc["seconds"])):
            flag("measured", f"Scene {sc['n']}: the shots add up to {secs} s but the script estimate is {sc['seconds']} s: change one of the two.")
        first = ordered_first(mine)
        if len(mine) >= 3 and first and first["camera"] and first["camera"] not in WIDE_CAMS:
            flag("heuristic", f"Scene {sc['n']}: the first shot does not look wide/establishing: will the viewer know the place?")
        if len(mine) == 1 and sc.get("dialogue") and len(sc.get("dialogue") or []) >= 3:
            flag("heuristic", f"Scene {sc['n']}: {len(sc['dialogue'])} dialogue lines on only one shot: the whole scene from one angle?")
    run, prev = 0, None
    for r in timeline:
        run = run + 1 if r["camera"] and r["camera"] == prev else 1
        prev = r["camera"]
        if run == RUN_LIMIT:
            flag("heuristic", f"{r['id']}: {RUN_LIMIT} shots in a row are '{r['camera']}' up to here: try varying it.")
    if runtime_target_s and t:
        if abs(t - int(runtime_target_s)) > TOL * int(runtime_target_s):
            flag("measured", f"The shots add up to {t} s, your target {runtime_target_s} s ({t - int(runtime_target_s):+d} s).")
    mix: dict[str, int] = {}
    for r in timeline:
        if r["camera"]:
            mix[r["camera"]] = mix.get(r["camera"], 0) + 1
    gear = sorted({r["gear"] for r in timeline if r["gear"]})
    if "drone (flying permission and licensed pilot needed)" in gear:
        flag("measured", "There is a drone shot: flying permission and a licensed pilot are needed (you arrange this).")
    return {"shots": len(timeline), "total_seconds": t, "runtime_target_s": runtime_target_s or None, "timeline": timeline,
            "per_scene": per_scene, "camera_mix": mix, "gear": gear, "flags": flags,
            "note": "This is a check of the shot list. The 180 degree rule, lenses and blocking need a floor plan and a human eye; they are not checked here. "
                    "To see an animatic, use action=preview (free)."}


def ordered_first(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return min(rows, key=lambda r: r["start_s"]) if rows else None
