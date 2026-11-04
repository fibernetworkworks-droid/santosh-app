"""v0.487.0 BYOX guide functions — list, fetch, plan.

Three pure functions called by the byox agent tools; no I/O, no side effects.
"""
from __future__ import annotations
import difflib

from . import CATEGORIES, SLUGS, TUTORIALS


def list_categories(q: str = "") -> list[dict]:
    """Return all categories, optionally filtered by a query string."""
    q = (q or "").strip().lower()
    out = []
    for cat in CATEGORIES.values():
        if q and q not in cat["slug"] and q not in cat["display_name"].lower() and q not in cat["description"].lower():
            continue
        out.append({
            "slug": cat["slug"],
            "display_name": cat["display_name"],
            "description": cat["description"],
            "best_languages": cat["best_languages"],
            "tutorial_count": cat.get("tutorial_count", 0),
        })
    return out


def get_guide(slug_or_name: str, level: str = "standard", language: str = "") -> dict:
    """Return a full guide dict for a category.

    slug_or_name: exact slug, display_name substring, or fuzzy match.
    level: 'quick' (phases + reference only) | 'standard' (all fields) | 'deep' (all + tips).
    language: optional filter — only return tutorials in this language (case-insensitive).
    """
    key = _resolve(slug_or_name)
    if key is None:
        close = difflib.get_close_matches(slug_or_name.lower(), SLUGS, n=3, cutoff=0.4)
        return {"error": f"Category {slug_or_name!r} not found.",
                "suggestions": close}
    cat = CATEGORIES[key]
    all_tutorials = TUTORIALS.get(key, [])
    lang_filter = (language or "").strip().lower()
    if lang_filter:
        filtered = [t for t in all_tutorials if t["lang"].lower() == lang_filter]
        tutorials_out = filtered if filtered else all_tutorials
        lang_note = None if filtered else f"No tutorials found for language {language!r}; showing all languages."
    else:
        tutorials_out = all_tutorials
        lang_note = None

    base: dict = {
        "slug": cat["slug"],
        "display_name": cat["display_name"],
        "description": cat["description"],
        "core_concepts": cat["core_concepts"],
        "best_languages": cat["best_languages"],
        "phases": cat["phases"],
        "reference_url": cat["reference_url"],
        "tutorial_count": cat.get("tutorial_count", len(all_tutorials)),
        "tutorials": tutorials_out,
    }
    if lang_note:
        base["language_note"] = lang_note
    if level == "quick":
        return {
            "slug": cat["slug"],
            "display_name": cat["display_name"],
            "phases": cat["phases"],
            "reference_url": cat["reference_url"],
            "tutorial_count": base["tutorial_count"],
            "tutorials": tutorials_out,
        }
    if level == "deep":
        base["deep_tips"] = _deep_tips(cat)
    return base


def plan_learning(want: str, background: str = "", time_weeks: int = 4) -> dict:
    """Return a personalised BYOX learning plan.

    want:        a free-text description of what the learner wants to build
    background:  languages / experience the learner already has
    time_weeks:  total calendar weeks available
    """
    want_lower = want.lower()
    ranked: list[tuple[int, str]] = []
    for slug, cat in CATEGORIES.items():
        score = 0
        for word in want_lower.split():
            if word in cat["slug"] or word in cat["display_name"].lower() or word in cat["description"].lower():
                score += 2
            if any(word in c.lower() for c in cat["core_concepts"]):
                score += 1
        if score > 0:
            ranked.append((score, slug))
    ranked.sort(key=lambda x: -x[0])

    # pick top-3 matches; fall back to reasonable starter categories
    picks = [slug for _, slug in ranked[:3]]
    if not picks:
        picks = ["byox-web-server", "byox-shell", "byox-database"]

    # language fit
    bg_langs = [t.strip() for t in background.split(",") if t.strip()] if background else []
    for slug in picks:
        cat = CATEGORIES[slug]
        if bg_langs and not any(l in cat["best_languages"] for l in bg_langs):
            cat_copy = dict(cat)
            cat_copy["language_note"] = (
                f"You listed {bg_langs} but this project is usually done in "
                f"{cat['best_languages']}. That's a great pairing — pick the language "
                f"you want to learn alongside the systems concept."
            )

    weeks_per_project = max(1, time_weeks // max(1, len(picks)))
    plan_steps = []
    for i, slug in enumerate(picks):
        cat = CATEGORIES[slug]
        plan_steps.append({
            "week": i * weeks_per_project + 1,
            "project": cat["display_name"],
            "slug": slug,
            "goal": cat["phases"][0],
            "milestone": cat["phases"][-1],
            "reference_url": cat["reference_url"],
            "tutorial_count": cat.get("tutorial_count", len(TUTORIALS.get(slug, []))),
        })

    return {
        "want": want,
        "background": background or "not specified",
        "time_weeks": time_weeks,
        "weeks_per_project": weeks_per_project,
        "projects": plan_steps,
        "note": (
            "Start with Phase 1 of each project before moving to the next. "
            "A working Phase 1 teaches more than a half-finished Phase 5."
        ),
    }


# ---------------------------------------------------------------- helpers

def _resolve(slug_or_name: str) -> str | None:
    s = slug_or_name.strip().lower()
    # exact slug
    if s in CATEGORIES:
        return s
    # byox- prefix missing
    with_prefix = "byox-" + s
    if with_prefix in CATEGORIES:
        return with_prefix
    # display_name substring
    for slug, cat in CATEGORIES.items():
        if s in cat["display_name"].lower():
            return slug
    # fuzzy slug match
    close = difflib.get_close_matches(s, SLUGS, n=1, cutoff=0.5)
    return close[0] if close else None


def _deep_tips(cat: dict) -> list[str]:
    tips = [
        f"Work through Phase 1 completely before reading about Phase 2 — "
        f"building intuition for {cat['display_name']} requires the friction of doing.",
        f"Use {cat['best_languages'][0]} for your first attempt even if you know "
        f"another language better; language-idiomatic solutions reveal the design.",
        "Write a test for the simplest case first; it makes the loop concrete.",
        f"Read the reference ({cat['reference_url']}) AFTER your Phase 1 attempt, "
        f"not before — the gap between your design and theirs is the lesson.",
    ]
    return tips
