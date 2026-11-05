"""Film Desk SCRIPT COVERAGE (facts layer): what the script itself measures to, all in CODE.

Register: docs/research/film_industry/00_INDEX.md  (script coverage / reader report). Pure functions over the parsed scenes
(`rules.parse_script`) and the script text: no database, no network, no model.

What it is NOT: a reader's verdict. "Pass / consider / recommend" is a person's judgement and nothing here says it. Every line below
is either a COUNT (scenes, lines, words, seconds) or a HEURISTIC FLAG, and each flag carries `kind: "heuristic"` so nobody mistakes a
word-list hit for a fact about the story. Seconds are the parser's estimate (dialogue words / 2.5 + action words / 3), not a stopwatch.
Rating words are keyword hits to prepare the CBFC conversation; they never set a rating.
"""
from __future__ import annotations

import re
from typing import Any

# Words that describe a thought, not a picture: a camera cannot film them (action lines only). English + Hinglish, hers to ignore.
UNFILMABLE = ("thinks", "thought", "feels", "felt", "realizes", "realises", "remembers", "wonders", "knows", "decides", "wishes",
              "hopes", "sochta", "sochti", "mehsoos", "yaad karta", "yaad karti", "samajh jata", "samajh jati", "ehsaas")
# keyword hits only, by theme (counts help her prepare for the board; the rating itself is hers and the board's)
THEMES = {
    "violence": ("kill", "murder", "blood", "gun", "knife", "stab", "shoot", "beat", "maar", "khoon", "goli", "talwar"),
    "sexual": ("sex", "kiss", "nude", "naked", "bed", "romance", "chumban", "nanga"),
    "substance": ("liquor", "alcohol", "cigarette", "smoke", "drugs", "ganja", "sharab", "daaru", "nasha", "beedi"),
    "abuse": ("abuse", "gaali", "slap", "thappad", "bastard", "harami"),
}
LONG_SPEECH_WORDS = 40
ONE_SCENE_SHARE = 0.25


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9ऀ-ॿ]", "", name.lower())


def _close(a: str, b: str) -> bool:
    """Same character spelled twice? equal after stripping, or one is a prefix of the other (>=3 chars), or edit distance 1."""
    if not a or not b or a == b:
        return a == b and bool(a)
    if min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)):
        return True
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 4:
        return False
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        diff += 1
        if diff > 1:
            return False
        if len(a) == len(b):
            i += 1
            j += 1
        elif len(a) > len(b):
            i += 1
        else:
            j += 1
    return True


def _words(text: str) -> int:
    return len(re.findall(r"[\wऀ-ॿ']+", text or ""))


def _hits(text: str, words: tuple[str, ...]) -> int:
    low = text.lower()
    return sum(len(re.findall(rf"(?<![\wऀ-ॿ]){re.escape(w)}", low)) for w in words)


def coverage(scenes: list[dict[str, Any]], script_text: str = "", runtime_target_s: int | None = None) -> dict[str, Any]:
    n = len(scenes)
    if not n:
        return {"scenes": 0, "note": "Pehle script (scenes) chahiye.", "flags": [], "kind_note": NOTE}
    total_s = sum(int(s.get("seconds") or 0) for s in scenes)
    rows, chars = [], {}
    for sc in scenes:
        dl = sc.get("dialogue") or []
        dw = sum(_words(d.get("line", "")) for d in dl)
        aw = sum(_words(a) for a in sc.get("action") or [])
        rows.append({"n": sc["n"], "id": sc["id"], "heading": sc.get("heading", ""), "place": sc.get("place", ""),
                     "int_ext": sc.get("int_ext", ""), "time": sc.get("time", ""), "seconds": int(sc.get("seconds") or 0),
                     "dialogue_lines": len(dl), "dialogue_words": dw, "action_words": aw,
                     "dialogue_share": round(dw / (dw + aw), 2) if (dw + aw) else 0.0})
        for c in sc.get("characters") or []:
            chars.setdefault(c, {"name": c, "scenes": [], "lines": 0, "words": 0, "longest_words": 0})["scenes"].append(sc["n"])
        for d in dl:
            who = d.get("who", "")
            if not who:
                continue
            e = chars.setdefault(who, {"name": who, "scenes": [sc["n"]], "lines": 0, "words": 0, "longest_words": 0})
            w = _words(d.get("line", ""))
            e["lines"] += 1
            e["words"] += w
            e["longest_words"] = max(e["longest_words"], w)
    all_dw = sum(c["words"] for c in chars.values()) or 0
    cast = []
    for c in sorted(chars.values(), key=lambda x: (-x["words"], x["name"])):
        cast.append({"name": c["name"], "scenes_n": len(set(c["scenes"])), "first_scene": min(c["scenes"]) if c["scenes"] else None,
                     "last_scene": max(c["scenes"]) if c["scenes"] else None, "lines": c["lines"], "dialogue_words": c["words"],
                     "dialogue_pct": round(100.0 * c["words"] / all_dw, 1) if all_dw else 0.0,
                     "longest_speech_words": c["longest_words"]})
    flags: list[dict[str, str]] = []

    def flag(kind: str, text: str) -> None:
        flags.append({"kind": kind, "text": text})

    # measured facts first
    places = [s.get("place") or "" for s in scenes]
    moves = sum(1 for a, b in zip(places, places[1:]) if a and b and a != b)
    uniq_places = len({p for p in places if p})
    night = sum(1 for s in scenes if s.get("time") == "night")
    longest = max(rows, key=lambda r: r["seconds"])
    if total_s and longest["seconds"] / total_s > ONE_SCENE_SHARE and n > 3:
        flag("measured", f"Scene {longest['n']} akeli film ka {round(100 * longest['seconds'] / total_s)}% hai ({longest['seconds']} s): "
                         "kya yeh ek hi baithak mein shoot hoga?")
    missing_head = [r["n"] for r in rows if not r["time"] or not r["int_ext"]]
    if missing_head:
        flag("measured", f"Scene {', '.join(map(str, missing_head[:12]))}: heading mein INT/EXT ya din/raat nahi likha: "
                         "schedule ke liye yeh chahiye.")
    if runtime_target_s and total_s:
        diff = total_s - int(runtime_target_s)
        if abs(diff) > 0.15 * int(runtime_target_s):
            flag("measured", f"Anumaanit samay {total_s} s hai, aapka target {runtime_target_s} s ({diff:+d} s).")
    for c in cast:
        if c["lines"] == 1 and c["scenes_n"] <= 1:
            flag("measured", f"{c['name']}: sirf ek line, ek scene: kya yeh kirdaar kisi aur ke saath mil sakta hai?")
        if c["lines"] == 0 and c["scenes_n"] >= 1:
            flag("measured", f"{c['name']}: scene mein hai par bolta kuch nahi: jaan-boojh kar hai?")
        if c["longest_speech_words"] > LONG_SPEECH_WORDS:
            flag("measured", f"{c['name']}: ek speech {c['longest_speech_words']} shabdon ki hai (>{LONG_SPEECH_WORDS}): "
                             "kaat sakte hain ya tod sakte hain?")
    names = [c["name"] for c in cast]
    seen: set[tuple[str, str]] = set()
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _close(_norm(a), _norm(b)) and (a, b) not in seen:
                seen.add((a, b))
                flag("heuristic", f"'{a}' aur '{b}' ek hi kirdaar ho sakte hain (spelling alag): ek naam rakhiye warna cast do ginega.")
    talky = 0
    for r in rows:
        talky = talky + 1 if r["dialogue_share"] >= 0.9 and r["dialogue_lines"] >= 3 else 0
        if talky == 3:
            flag("heuristic", f"Scene {r['n'] - 2}-{r['n']}: teen scene lagataar sirf baatein: kya beech mein koi action / drishya chahiye?")
    unf = []
    for sc in scenes:
        for a in sc.get("action") or []:
            low = a.lower()
            if any(re.search(rf"(?<![\wऀ-ॿ]){re.escape(w)}", low) for w in UNFILMABLE):
                unf.append(f"scene {sc['n']}")
                break
    if unf:
        flag("heuristic", f"{', '.join(unf[:8])}: action line mein soch / ehsaas jaisa shabd hai jo camera nahi dikha sakta: "
                          "use kiya jaa sakne wale drishya mein badliye.")
    pos, acc = {}, 0
    for r in rows:
        acc += r["seconds"]
        for pct in (25, 50, 75):
            if pct not in pos and total_s and acc >= total_s * pct / 100.0:
                pos[pct] = r["n"]
    full = script_text or ""
    dev = len(re.findall(r"[ऀ-ॿ]", full))
    lat = len(re.findall(r"[A-Za-z]", full))
    theme_hits = {k: _hits(full, v) for k, v in THEMES.items()}
    lead = cast[0]["name"] if cast and cast[0]["dialogue_words"] else ""
    return {
        "scenes": n, "estimated_seconds": total_s, "estimated_minutes": round(total_s / 60.0, 1),
        "runtime_target_s": runtime_target_s or None,
        "words": sum(r["dialogue_words"] + r["action_words"] for r in rows),
        "dialogue_words": all_dw, "dialogue_pct": round(100.0 * all_dw / max(1, sum(r["dialogue_words"] + r["action_words"] for r in rows)), 1),
        "characters_n": len(cast), "places_n": uniq_places, "company_moves": moves, "night_scenes": night,
        "night_pct": round(100.0 * night / n, 1), "avg_scene_s": round(total_s / n, 1),
        "most_dialogue": lead, "most_dialogue_note": "sabse zyada bolne wala (shabdon se), zaroori nahi ki hero ho." if lead else "",
        "quarter_marks": {f"{p}%": f"scene {s}" for p, s in pos.items()},
        "script_marks_note": "Yeh sirf samay ke hisaab se ginti hai: aapke apne mod (act breaks) kahani se tay hote hain.",
        "script_language": {"devanagari_letters": dev, "latin_letters": lat,
                            "note": "Subtitle / dub plan ke liye; mishrit (Hinglish) script ho sakti hai."},
        "theme_hits": theme_hits,
        "theme_note": "Yeh sirf shabd-ginti hai, rating nahi. Rating aap aur board tay karte hain (action=rating).",
        "scene_table": rows, "cast_table": cast, "flags": flags, "kind_note": NOTE,
    }


NOTE = ("Yeh coverage ginti aur shabd-suchi se bani hai. 'Pass / consider / recommend' jaisa faisla kisi padhne wale insaan ka hai: "
        "yahan kuch bhi woh nahi kehta. 'heuristic' wali line sirf ek ishara hai.")
