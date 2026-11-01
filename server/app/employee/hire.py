"""v0.317 HIRE AN EMPLOYEE: the owner picks an AI employee in the Employee Hub (web console or app); only then does its
desk appear on her surfaces and its 24/7 jobs run. SEO Specialist is the first one; the rest of the catalogue shows as
"coming" so she sees where Hoola is going.

States: hired -> paused -> hired (resume) ; hired / paused -> left. Letting go stops every job at once and keeps the
history read-only (nothing is deleted). One row per (tenant, employee key)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session


class HireError(Exception):
    pass


class HiredEmployee(Base):
    __tablename__ = "hired_employees"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("he"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(10), default="hired")          # hired | paused | left
    trust: Mapped[str] = mapped_column(String(10), default="seekh")           # seekh | saathi | bharosa
    settings: Mapped[str] = mapped_column(Text, default="{}")
    hired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_table() -> None:
    """Self-heal (the table is also created by db.init_db): once per database engine."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        HiredEmployee.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


TRUST = ("seekh", "saathi", "bharosa")

GAME_GROUP = "Game Development, Simulation & VR"   # v0.379 the Game Desk employees' heading in the Hub
SW_GROUP = "Software Architecture, Engineering & Core Systems"   # v0.410 the Architecture Desk employees' heading

# The catalogue. `live` employees can be hired today; the others show as "coming".
CATALOG: dict[str, dict[str, Any]] = {
    "seo": {
        "name": "SEO Specialist", "live": True, "icon": "search",
        "pitch": "Gets your business found on Google and in AI answers. Works 24/7 on your website and Google profile.",
        "does": ["Full audit of your website every week (up to 500 pages) with a fix list",
                 "Watches your site every hour: down, blocked from Google, pages dropped",
                 "Reads your Search Console and Google Analytics: clicks, searches, leads from Google",
                 "Core Web Vitals (speed) on mobile",
                 "A 90-day plan you approve, worked as a weekly board",
                 "Weekly note and a monthly PDF report with charts"],
        "needs": ["Your website address", "Google sign-in for Search Console (and Analytics, if you use it)"],
        "never": ["Buy links or fake reviews", "Publish anything on your site or Google profile without your OK",
                  "Make mass AI pages or doorway pages", "Promise a ranking"],
    },
    "social": {"name": "Social Media Manager", "live": True, "icon": "share",
               "pitch": "Runs your Instagram and Facebook Page like a good agency: plans the month, writes the posts, learns what works.",
               "does": ["Reads your last 50 posts and their numbers: what works, when your people are online",
                        "A strategy: content themes, posting rhythm, hashtags, the one number the month is judged on",
                        "A 30-day calendar of ready posts (hook, caption in your language, hashtags, picture brief) for your OK",
                        "Indian festivals and local moments planned in",
                        "Checks your connections every hour and fresh numbers every day"],
               "needs": ["Instagram Business or Creator account and / or your Facebook Page",
                         "One login on Instagram / Facebook's own page (Hoola never sees your password)"],
               "never": ["Buy followers or likes, or use engagement pods", "Post anything without your OK",
                         "Invent prices, offers or claims", "Read or touch any account you did not connect"]},
    "accounts": {"name": "Accounts Assistant", "live": False, "icon": "receipt",
                 "pitch": "Bills, GST returns, payments due and the monthly books."},
    "telecaller": {"name": "Telecaller", "live": False, "icon": "phone",
                   "pitch": "Calls your leads and customers with a script, notes every answer."},
    "support": {"name": "Customer Support", "live": False, "icon": "chat",
                "pitch": "Answers customer questions on WhatsApp and email from your own FAQ."},
    # v0.357 ENGINEERING DESK (docs/ENGINEERING_DESK_PLAN.md): one shared locked runner, a pack per role
    "cad": {"name": "CAD Engineer", "live": True, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "Turns your words and sizes into a real 3D part: STEP and STL files plus a dimensioned drawing.",
            "does": ["Designs the part from your words (and your sizes in mm) as clean, parametric CadQuery code",
                     "Builds it in a locked box on Hoola's server and checks it: valid solid, one body, the size you asked",
                     "Gives you STEP (for any CAD / CNC shop), STL (for 3D printing), 4 views and a drawing PDF",
                     "Changes it on your words: 'holes 10 mm karo', 'wall 3 mm moti'",
                     "Keeps every version on the CAD Desk"],
            "needs": ["What the part is and its main sizes in mm (a photo of a sketch with numbers helps)"],
            "never": ["Call a design certified, approved or safe to use without a qualified engineer",
                      "Sign or stamp drawings", "Use cracked or unlicensed CAD software",
                      "Design weapons or export-controlled parts"]},
    "fea": {"name": "Structural Analysis (FEA)", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "Will the part break? Stress, deflection and safety factor with plots (CalculiX)."},
    "cfd": {"name": "CFD Engineer", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "Air and heat flow around or through your design, with plots (OpenFOAM)."},
    "acoustic": {"name": "Acoustic Simulation", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
                 "pitch": "How a room or hall sounds: echo time, sound level map, what to treat."},
    "optics": {"name": "Optical Systems Simulation", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
               "pitch": "Lens and laser paths: ray trace, spot size, focal length, tolerances."},
    "ecu": {"name": "Automotive ECU (AUTOSAR) Programmer", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "C code, MISRA checks, unit tests and requirement tracing for vehicle ECUs (draft, not certified)."},
    "flight_sw": {"name": "Spacecraft Flight Software", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
                  "pitch": "Flight code review, fault handling and tests to NASA / ESA style rules (draft, not certified)."},
    "med_sw": {"name": "Medical Device Software", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
               "pitch": "Embedded code and IEC 62304 / ISO 14971 files and tests (draft for your engineers)."},
    "litho": {"name": "Chip Layout (Lithography) Software", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
              "pitch": "Layout scripts and design-rule checks on GDS files (KLayout)."},
    "iiot": {"name": "Industrial IoT Architect", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
             "pitch": "SCADA and factory network design: device list, protocols, security zones, BOM (paper only)."},
    # v0.379 GAME DESK (docs/GAME_DESK_PLAN.md): one shared desk, a pack per role; Phase 1 = the Game Developer
    "game_dev": {"name": "Game Developer", "live": True, "icon": "game", "group": GAME_GROUP,
                 "pitch": "Makes original games from your words with Godot 4, tests them itself and gives you a link to play on any phone.",
                 "does": ["Writes a short design doc first: you OK it or change it",
                          "Builds the game in Godot 4 (free, open source) for the phone browser",
                          "Plays it itself before you see it: frame rate, taps and keys, screenshots, script errors",
                          "Fixes its own mistakes from the real errors (up to four rounds)",
                          "A private play link and QR, plus the whole Godot project as a zip",
                          "Changes in your words make a new version; the last good one keeps working"],
                 "needs": ["Your idea in two or three lines (what you do, how you win, who it is for)"],
                 "never": ["Copy a specific existing game, its characters, levels or art",
                           "Real-money, betting or gambling games", "Cheats, bots for other people's games, weapon targeting",
                           "Share your game anywhere: the link is private until you share it"]},
    "xr_dev": {"name": "AR / VR Interaction Engineer", "live": False, "icon": "game", "group": GAME_GROUP,
               "pitch": "WebXR scenes with hand tracking and gestures that open in a phone or headset browser."},
    "netcode_dev": {"name": "Multiplayer Network Programmer", "live": False, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Netcode for your game: server, prediction, lag compensation, tested with bots on bad networks."},
    # v0.417 Phase 7 batch 1 (docs/GAME_DESK_PLAN.md phase 2): each role is a PACK on the shared Game Desk
    "physics_dev": {"name": "Physics Engine Developer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Sets up your game's physics and proves it in the real engine: falling, jumping, bouncing and "
                             "fast bullets checked against textbook answers.",
                    "does": ["Takes your numbers (fastest thing, thinnest wall, gravity) from your words or your Game Bible",
                             "Works out tick rate and continuous collision in code so nothing passes through walls",
                             "Runs a physics lab in Godot itself: free fall, jumps, bounces, a box stack, 3D, run twice",
                             "Every case compared with the formula; failures are named, never hidden",
                             "Your OK puts the proven settings and jump helpers into your game"],
                    "needs": ["A game on the Game Desk (or just your numbers)"],
                    "never": ["Claim a number the lab did not measure", "Change your game before your OK",
                              "Fluid simulation (not built yet - said plainly)"]},
    "sim_dev": {"name": "Simulation Software Engineer", "live": False, "icon": "game", "group": GAME_GROUP,
                "pitch": "Flight, space and driving training simulators with cited data and repeatable scenarios."},
    "procgen_dev": {"name": "Procedural World Generation Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Islands, dungeons, cities and platform levels from rules and a seed - checked playable, "
                             "previewed, and walkable in your browser.",
                    "does": ["Makes terrain (biomes, rivers, villages), dungeons, cities or side-view levels from your words",
                             "Same seed = same world, proved by making it twice",
                             "Checks every village, room, exit and goal can be reached; a level is walked with your jump",
                             "A preview picture, a walk-it link, world.json, heightmap and a 3D .glb mesh",
                             "Your OK puts the world into your game (HoolaWorld) without new code"],
                    "needs": ["Two lines: what kind of world, how big, anything special"],
                    "never": ["Copy a real game's map or levels", "Put a world in your game before your OK"]},
    "vfx_td": {"name": "VFX Pipeline Technical Director", "live": False, "icon": "game", "group": GAME_GROUP,
               "pitch": "CG pipeline for film and TV: shot tracking, ACES colour, EXR, render queue (Blender / OpenUSD)."},
    "audio_dev": {"name": "Spatial Audio Systems Programmer", "live": False, "icon": "game", "group": GAME_GROUP,
                  "pitch": "3D positional sound: HRTF, distance, occlusion and reverb zones for games and VR."},
    "twin_arch": {"name": "Digital Twin Architect", "live": False, "icon": "game", "group": GAME_GROUP,
                  "pitch": "A live 3D twin of your factory or building with what-if simulation; reads data, never controls."},
    "haptics_dev": {"name": "Haptic Feedback Systems Engineer", "live": False, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Vibration patterns and driver code for phones, controllers and your own device."},
    # v0.410 SOFTWARE ARCHITECTURE, ENGINEERING & CORE SYSTEMS (docs/SOFTWARE_DESK_PLAN.md). Code they write goes to HER
    # GitHub through the Developer Sahayak's draft PR + CI path; heavy builds run in HER CI, never on her PC.
    "architect": {"name": "Principal Software Architect", "live": True, "icon": "code", "group": SW_GROUP,
                  "pitch": "Designs your system the way a principal architect would: decisions, diagrams, capacity and risks - "
                           "then checks every pull request against it.",
                  "does": ["Reads your GitHub repo first (read only) or starts from your idea for a new system",
                           "Writes the architecture: context, quality targets, components, data, main flows, security",
                           "Draws the diagrams: system context, containers, the main flow, deployment",
                           "Decision records (ADRs) with the options it did not pick and why",
                           "Capacity worked out in code from your numbers: requests per second, storage, servers",
                           "Risks, failure modes, a phased roadmap and the questions it needs answered",
                           "A PDF you can hand to your team; changes in your words make the next version",
                           "Reads your pull requests against the approved design (on its own if you switch it on)"],
                  "needs": ["What the system must do, who uses it and roughly how many people a day",
                            "Optional: your GitHub repo (connected once in the Developer Sahayak)"],
                  "never": ["Push, merge or deploy anything - its PR notes go out only on your tap",
                            "Run your code on its server or touch your PC",
                            "Make up scale numbers: no users-a-day number, no capacity sheet",
                            "Call a design approved by a certified authority"]},
    "compiler_eng": {"name": "Compiler Construction Engineer", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Domain-specific languages: grammar, parser, interpreter or compiler with golden tests."},
    "kernel_dev": {"name": "Kernel / OS Developer", "live": False, "icon": "code", "group": SW_GROUP,
                   "pitch": "Kernel patches, drivers and crash-log diagnosis; boot-tested in QEMU in your own CI."},
    "graphics_eng": {"name": "Graphics Engine Programmer", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Renderers and shaders (Vulkan, ray tracing): shader validation and CPU-rendered checks."},
    "dbengine_dev": {"name": "Database Engine Developer", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Query plans and indexes from your real database, storage and query-engine code, benchmarks."},
    "distsys_eng": {"name": "Distributed Systems Engineer", "live": False, "icon": "code", "group": SW_GROUP,
                    "pitch": "Consensus, retries, idempotency and failover - with failure-injection tests and formal specs."},
    "hypervisor_eng": {"name": "Virtualization / Hypervisor Engineer", "live": False, "icon": "code", "group": SW_GROUP,
                       "pitch": "Container runtimes and VMs: configs, security profiles and hardening, tested in your CI."},
    "lowlatency_eng": {"name": "Backend Systems Engineer (Low Latency)", "live": False, "icon": "code", "group": SW_GROUP,
                       "pitch": "Lock-free, zero-copy hot paths with microbenchmarks and p99 analysis of your latency data."},
    "mainframe_arch": {"name": "Mainframe Modernization Architect", "live": False, "icon": "code", "group": SW_GROUP,
                       "pitch": "COBOL inventory, dependency map and migration plan; translations proved side by side."},
    "refactor_eng": {"name": "Legacy Code Refactoring Specialist", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Maps the worst code, writes tests first, then many small safe refactor PRs, each green on CI."},
}


def _row(s, tenant: str, key: str) -> HiredEmployee | None:
    return s.scalars(select(HiredEmployee).where(HiredEmployee.tenant_id == tenant, HiredEmployee.key == key)
                     .order_by(HiredEmployee.hired_at.desc())).first()


def _view(r: HiredEmployee | None) -> dict[str, Any]:
    if r is None:
        return {"status": "none"}
    try:
        st = json.loads(r.settings or "{}")
    except ValueError:
        st = {}
    return {"status": r.status, "trust": r.trust, "hired_at": r.hired_at.isoformat() if r.hired_at else "",
            "left_at": r.left_at.isoformat() if r.left_at else "", "settings": st}


def status(tenant: str, key: str) -> str:
    """'none' | 'hired' | 'paused' | 'left'."""
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        return r.status if r else "none"


def is_hired(tenant: str, key: str) -> bool:
    """Hired and working (paused counts as hired for the desk, not for the 24/7 jobs: see is_working)."""
    return status(tenant, key) in ("hired", "paused")


def is_working(tenant: str, key: str) -> bool:
    return status(tenant, key) == "hired"


def hired_keys(tenant: str) -> dict[str, str]:
    """{key: status} for every employee she has hired and not let go (the surfaces use this to show desks)."""
    ensure_table()
    out: dict[str, str] = {}
    with session() as s:
        for r in s.scalars(select(HiredEmployee).where(HiredEmployee.tenant_id == tenant)
                           .order_by(HiredEmployee.hired_at)).all():
            if r.status in ("hired", "paused"):
                out[r.key] = r.status
            else:
                out.pop(r.key, None)
    return out


def working_tenants(key: str) -> list[str]:
    """Every tenant whose `key` employee is hired and not paused (the 24/7 scheduler walks these)."""
    ensure_table()
    with session() as s:
        return sorted({r.tenant_id for r in s.scalars(select(HiredEmployee).where(HiredEmployee.key == key,
                                                                                  HiredEmployee.status == "hired")).all()})


def catalog(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    out = []
    with session() as s:
        for key, c in CATALOG.items():
            out.append({"key": key, "group": "Business", **c, **_view(_row(s, tenant, key))})
    return out


def hire(tenant: str, key: str, trust: str = "seekh") -> dict[str, Any]:
    c = CATALOG.get(key)
    if c is None:
        raise HireError("Aisa koi employee nahi.")
    if not c.get("live"):
        raise HireError(f"{c['name']} abhi taiyaar ho raha hai; jald aayega.")
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is not None and r.status in ("hired", "paused"):
            r.status = "hired"
            return {"key": key, **_view(r), "already": True}
        r = HiredEmployee(tenant_id=tenant, key=key, status="hired",
                          trust=trust if trust in TRUST else "seekh", settings="{}")
        s.add(r)
        s.flush()
        return {"key": key, **_view(r)}


def _set(tenant: str, key: str, status_: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is None or r.status == "left":
            raise HireError("Yeh employee abhi hired nahi hai.")
        r.status = status_
        if status_ == "left":
            r.left_at = now()
        return {"key": key, **_view(r)}


def pause(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "paused")


def resume(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "hired")


def leave(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "left")


def settings(tenant: str, key: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        return _view(_row(s, tenant, key)).get("settings", {})


def save_settings(tenant: str, key: str, **kw: Any) -> dict[str, Any]:
    """Merge keys into the employee's settings (trust is its own column)."""
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is None or r.status == "left":
            raise HireError("Yeh employee abhi hired nahi hai.")
        st = _view(r)["settings"]
        trust = kw.pop("trust", None)
        if trust in TRUST:
            r.trust = trust
        st.update({k: v for k, v in kw.items() if v is not None})
        r.settings = json.dumps(st, ensure_ascii=False)
        return _view(r)
