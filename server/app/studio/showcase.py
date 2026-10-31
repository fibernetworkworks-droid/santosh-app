"""v0.328 SHOWCASE (Phase 5 of the Create Studio design audit): real Hoola-made pictures and clips instead of the drawn placeholders.

The owner asked for "REAL HOOLA CREATED VIDEOS AND IMAGES HERE FOR PRESENTATION". Nothing new spends money here: the showcase is ONE
hidden Director film in the owner's own studio ("Hoola showcase"), one shot per slot on the studio pages. Its pictures are made by
the film's normal "opening pictures" price card and its four clips by the normal "make the shots" card - both go through
`service.keyframes` / `service.generate` -> `_ask` -> her Haan (+ phone fingerprint at /api/studio/approvals). This module only
  - sets the film up (owner only),
  - asks for those two cards (owner only),
  - says which slots are ready and serves their files to every signed-in user (the studio pages of every account show them).

    setup() / ask_pictures() / ask_clips() / manifest() / file_for(slot, kind)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import get_settings

NAME = "Hoola showcase"
STYLE = "No words, letters, numbers, logos or watermarks anywhere in the picture. Warm natural light, rich colour, Indian setting, premium photography."

# slot id -> what the picture shows. Slot ids are the studio page's own cards: film<i> = QUICK (Director film types), tpl<i> = STARTERS
# (templates), tool<i> = ALLTOOLS, sty<i> = STYLES (the Image page's style tiles). Guides reuse their tool's picture.
SLOTS: list[tuple[str, str]] = [
    ("film0", "A young shop owner in Jaipur hands a beautifully packed product to a smiling customer across a wooden counter, shallow depth of field"),
    ("film1", "A boy on a rooftop in old Delhi flying a kite at golden hour, the city of terraces behind him, cinematic wide frame"),
    ("film2", "A singer with a guitar on a Mumbai rooftop at night, string lights and the skyline glowing behind, cinematic"),
    ("film3", "An Indian bride and groom laughing during a haldi ceremony, marigold flowers and yellow drapes, candid wedding photography"),
    ("film4", "A bright modern apartment living room with a balcony view of a green Pune hillside, morning sun, real estate photography"),
    ("film5", "A sleek new pair of wireless earbuds on a polished stone plinth, soft studio light, product launch hero shot"),
    ("film6", "Two friends at a roadside chai stall in the rain, one looking surprised at a phone, moody cinematic street light"),
    ("film7", "A family lighting diyas together on a doorstep rangoli during Diwali, warm glow on their faces"),
    ("tpl0", "A small Indian sweet shop decorated with diyas and fairy lights for a Diwali sale, glowing shelves of mithai"),
    ("tpl1", "A clay kulhad of masala chai on a wooden table, steam rising, warm morning light, empty space at the top"),
    ("tpl2", "A car on a wet ghat road in the monsoon, mist over green hills, aerial drone view"),
    ("tpl3", "A confident woman founder speaking into a podcast microphone in a sunlit Bengaluru office"),
    ("tpl4", "A woman in a deep red Banarasi silk saree in a heritage haveli courtyard, soft daylight, fashion lookbook"),
    ("tpl5", "A cosy study desk by a rainy window at night, open notebooks, a cup of tea and warm lamp light"),
    ("tpl6", "A South Indian temple gopuram at dawn, mist, golden rim light, birds in the sky"),
    ("tpl7", "Pav bhaji sizzling on a big tawa at a Mumbai street stall at night, melting butter, bokeh lights"),
    ("tpl8", "A shehnai and a dhol on a festive marigold-decorated stage, warm celebratory light"),
    ("tpl9", "Two hosts laughing at a podcast table with headphones, cosy studio with plants"),
    ("tool0", "A film camera on a slider filming a chai stall at sunset, behind-the-scenes look"),
    ("tool1", "A product photography setup with a perfume bottle on silk under soft boxes"),
    ("tool2", "A music producer's desk with a keyboard and studio monitors, purple evening light"),
    ("tool3", "A professional studio microphone with a pop filter, warm bokeh background"),
    ("tool4", "A woman speaking happily to the camera in a bright home studio, ring light behind the camera"),
    ("tool5", "A video editing desk with two monitors showing a colourful timeline, night city outside the window"),
    ("tool6", "A director's chair and clapperboard on an Indian film set with lights and crew in soft focus"),
    ("tool7", "A writer's desk with a fountain pen, a notebook of handwritten notes and a cup of chai"),
    ("tool8", "Three portrait photos of the same young Indian man pinned on a casting board, studio light"),
    ("sty0", "A cup of masala chai with cardamom and cinnamon beside it, beautiful balanced composition"),
    ("sty1", "A photorealistic portrait of an elderly Rajasthani man with a bright turban, natural window light"),
    ("sty2", "A cinematic wide frame of a lone cyclist on a Kolkata street at dusk, film grain, anamorphic look"),
    ("sty3", "Diyas and marigolds glowing at night, festive warm glow, sparkles of light"),
    ("sty4", "A premium skincare jar on a soft pastel background, product studio lighting, clean shadows"),
    ("sty5", "A watercolour painting of a houseboat on the Kerala backwaters, soft washes of colour"),
    ("sty6", "An anime-style illustration of a girl on a Mumbai local train at sunset, vibrant colours"),
    ("sty7", "A cute 3D clay-style scene of a tiny chai stall with a smiling chaiwala, soft studio light"),
    ("sty8", "Madhubani folk-art style painting of a peacock and lotus flowers, bold lines, natural colours"),
]
CLIPS = ["film0", "film2", "film3", "film7"]          # the four moving previews (each starts from its picture)
SLOT_IDS = {s for s, _ in SLOTS}


class ShowcaseError(Exception):
    pass


def owner() -> str:
    return get_settings().tenant_id


async def setup() -> dict[str, Any]:
    """Create the hidden showcase film in the owner's studio (one 5 s shot per slot). Free: no picture or clip is made here."""
    from . import service as ss
    st = await ss.studio(owner())
    if not st.pdir(NAME).joinpath("project.json").exists():
        st.create(NAME, aspect="3:4", style="cinematic", language="Hindi", budget_usd=12.0,
                  brief="Hoola Create showcase: real pictures and clips for the studio pages")
        st.storyboard_set(NAME, [{"id": sid, "prompt": f"{text}. {STYLE}", "duration": 5, "kind": "scene"} for sid, text in SLOTS])
        p = st.load(NAME)
        p["hidden"] = True                  # never in her film lists, so "Make the shots" can't be tapped for all 36 by mistake
        p.setdefault("prefs", {})["cast_skip"] = True
        st.save(p)
    return status()


def _one_card(p: dict) -> None:
    if any(a.get("status") == "pending" for a in (p.get("approvals") or {}).values()):
        raise ShowcaseError("A price card is already waiting for your Haan below.")


async def ask_pictures() -> dict[str, Any]:
    """The normal opening-pictures price card for every slot still without a picture."""
    from . import service as ss
    st = await ss.studio(owner())
    p = st.load(NAME)
    _one_card(p)
    miss = [s["id"] for s in p["shots"] if not s.get("keyframe")]
    if not miss:
        raise ShowcaseError("Every showcase picture is already made.")
    return await ss.keyframes(owner(), NAME, miss)


async def ask_clips() -> dict[str, Any]:
    """The normal make-the-shots price card for the four clip slots (final quality, 5 s each)."""
    from . import service as ss
    st = await ss.studio(owner())
    p = st.load(NAME)
    _one_card(p)
    made = {sid for sid, vs in p.get("variants", {}).items() if any(Path(v["file"]).is_file() for v in vs)}
    want = [c for c in CLIPS if c not in made]
    if not want:
        raise ShowcaseError("All four showcase clips are already made.")
    shots = {s["id"]: s for s in p["shots"]}
    if any(not shots.get(c, {}).get("keyframe") for c in want):   # else the clip card would paint (and charge) those pictures again
        raise ShowcaseError("Make the pictures first: each clip starts from its picture.")
    return await ss.generate(owner(), NAME, "final", want)


def _project() -> dict | None:
    from . import service as ss
    st = ss.studio_sync(owner())
    if not st.pdir(NAME).joinpath("project.json").exists():
        return None
    return st.load(NAME)


def _clip_file(p: dict, sid: str) -> Path | None:
    vs = [v for v in p.get("variants", {}).get(sid, []) if Path(v["file"]).is_file()]
    if not vs:
        return None
    picked = p.get("picked", {}).get(sid)
    v = next((x for x in vs if x["n"] == picked), vs[-1])
    return Path(v["file"])


def manifest() -> dict[str, dict[str, bool]]:
    """Which slots have a real picture / clip. Every signed-in account's studio reads this."""
    p = _project()
    if not p:
        return {}
    out = {}
    for s in p["shots"]:
        if s["id"] not in SLOT_IDS:
            continue
        pic = bool(s.get("keyframe")) and Path(s["keyframe"]).is_file()
        clip = _clip_file(p, s["id"]) is not None
        if pic or clip:
            out[s["id"]] = {"pic": pic, "clip": clip}
    return out


def status() -> dict[str, Any]:
    """The owner's panel: counts, what is being made, and any price card waiting for her Haan."""
    from . import service as ss
    p = _project()
    if not p:
        return {"set_up": False, "slots": len(SLOTS), "clips": len(CLIPS)}
    v = ss.view(owner(), p)
    m = manifest()
    return {"set_up": True, "slots": len(SLOTS), "clips": len(CLIPS), "pictures_made": sum(1 for x in m.values() if x["pic"]),
            "clips_made": sum(1 for c in CLIPS if m.get(c, {}).get("clip")), "painting": v.get("painting") or [],
            "working": bool(v.get("working")), "pics_error": v.get("pics_error") or "", "error": v.get("error") or "",
            "approvals": [a for a in (v.get("approvals") or []) if a.get("status") == "pending"],
            "picture_inr": ss._inr(ss.KEYFRAME_USD), "spent_inr": ss._inr(p.get("spent_usd") or 0)}


def file_for(slot: str, kind: str) -> Path:
    if slot not in SLOT_IDS or kind not in ("pic", "clip"):
        raise ShowcaseError("Unknown showcase item")
    p = _project()
    if not p:
        raise ShowcaseError("The showcase is not made yet")
    if kind == "clip":
        f = _clip_file(p, slot)
    else:
        s = next((x for x in p["shots"] if x["id"] == slot), None)
        f = Path(s["keyframe"]) if s and s.get("keyframe") else None
    if not f or not f.is_file():
        raise ShowcaseError("Not made yet")
    return f
