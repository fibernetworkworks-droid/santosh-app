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
EDU_GROUP = "Education, Research & Lab"   # v0.453 the Shiksha suite + Prayogshala in the Hub (one Education Desk)
ENT_GROUP = "Enterprise Systems & ERP"   # v0.453 the ten enterprise jobs (v0.358) in the Hub; their desk is Systems
# v0.453 these employees' tools were open to every user before they joined the Hub, so hiring one only adds its desk;
# a tool must never start checking is_hired() for them (tested), or users would silently lose what they had.
EDU_OPEN = True

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
    # v0.422 Phase 7 batch 3 (docs/GAME_DESK_PLAN.md phase 4)
    "xr_dev": {"name": "AR / VR Interaction Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
               "pitch": "A WebXR room that opens in a phone or headset browser, with hand gestures and comfort rules checked.",
               "does": ["Sets up VR or AR with teleport, snap turning and a seated mode",
                        "Checks comfort in code: panel distance, text size, no forced camera motion",
                        "Hand gestures (pinch, grab, point) scored on a test set and checked in Godot itself",
                        "A walk-in demo room you open in your headset or phone browser",
                        "Your OK puts it into your game (HoolaXR)"],
               "needs": ["VR or AR, and the device (a headset or a phone)"],
               "never": ["Claim frame rates on your headset it has not measured", "Use smooth turning (a sickness cause)"]},
    "netcode_dev": {"name": "Multiplayer Network Programmer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Netcode for your game - server, prediction, lag compensation - proved by bots on bad networks; "
                             "the server runs on your own cloud.",
                    "does": ["Designs tick rate, send rate and interest range from your numbers",
                             "Bots play over good, 150 ms / 2 % loss and bad mobile networks",
                             "Measures rubber-banding, desync (must be 0), bandwidth and lag-compensation hits",
                             "Runs the Godot netcode itself with a server and three clients",
                             "A kit: a game server for your cloud (Docker) and the client code"],
                    "needs": ["How many players, how fast they move, and your own cloud for the server"],
                    "never": ["Host your game server on Hoola", "Claim the network part works before it runs on your server"]},
    # v0.420 Phase 7 batch 1 (docs/GAME_DESK_PLAN.md phase 2): each role is a PACK on the shared Game Desk
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
    # v0.423 Phase 7 batch 4 (docs/GAME_DESK_PLAN.md phase 5)
    "sim_dev": {"name": "Simulation Software Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
                "pitch": "Flight, space and driving training models, each validated against a textbook case, with cited data "
                         "and repeatable scenarios.",
                "does": ["Orbits (two-body + J2), a light-aircraft glide model or a car's handling model",
                         "Checks each against its textbook answer: orbit period, node drift, glide angle, phugoid, yaw rate",
                         "States the data source, the time step and the integrator; every scenario runs twice the same",
                         "A log (CSV) and a plot; an orbit model can go into your game (HoolaSim)"],
                "needs": ["What should be simulated, and the numbers you have"],
                "never": ["Weapon targeting, missile or combat simulators", "Call itself a certified flight training device"]},
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
    "vfx_td": {"name": "VFX Pipeline Technical Director", "live": True, "icon": "game", "group": GAME_GROUP,
               "pitch": "A CG pipeline for your shots: naming and versions, ACES colour end to end, EXR frames, a render queue "
                        "with cost per shot.",
               "does": ["Shot and file naming with versions that only go up",
                        "Colour from camera / texture to ACEScg to your screen, converted and measured",
                        "Writes a real ACEScg EXR test frame and reads it back",
                        "Plans the render queue: failed frames re-queued, cost per shot, every frame traced to its scene",
                        "A kit with the manifest and a Blender render script for your machines"],
               "needs": ["Your shots (frame ranges), your sources and your farm's size and rate"],
               "never": ["Claim Blender / OpenColorIO ran here (they are not installed on the server)"]},
    # v0.421 Phase 7 batch 2 (docs/GAME_DESK_PLAN.md phase 3)
    "audio_dev": {"name": "Spatial Audio Systems Programmer", "live": True, "icon": "game", "group": GAME_GROUP,
                  "pitch": "3D sound for your game - direction, distance, walls and room echo - measured, with headphone "
                           "demos you can hear.",
                  "does": ["Designs reverb zones (room, hall, cave...) and distance / wall settings from your words",
                           "Renders binaural headphone demos: a sound walking round your head, distance, each zone",
                           "Measures everything: ear-to-ear timing per direction, 6 dB per doubling, each zone's echo time",
                           "Demos at a measured -16 LUFS, never clipping",
                           "Your OK puts the zones, wall and distance settings into your game (HoolaAudio)"],
                  "needs": ["The places in your game (a cave, a hall, outdoors...)"],
                  "never": ["Claim front / back or height cues a round-head model cannot give (said plainly)",
                            "Change your game before your OK"]},
    "twin_arch": {"name": "Digital Twin Architect", "live": True, "icon": "game", "group": GAME_GROUP,
                  "pitch": "A twin of your line or shop floor with what-if simulation - every number traced to your data or "
                           "a stated assumption; it reads, never controls.",
                  "does": ["Your stations, machines, cycle times, breakdowns and shifts as a model",
                           "Simulates throughput, utilisation, work in progress, lead time and the bottleneck",
                           "What-ifs: one more machine, a faster station, a second shift - with the same random numbers",
                           "Checks its own engine against exact answers and queueing theory, and against your real week",
                           "A layout picture with each station's load"],
                  "needs": ["Your stations and their numbers (or your data tags), and one real week's output"],
                  "never": ["Write, command or control anything in your plant", "Call a twin validated without your real week",
                            "A 3D twin view (not built yet)"]},
    "haptics_dev": {"name": "Haptic Feedback Systems Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "One vibration pattern per meaning for your game, phone apps and your own device - checked, "
                             "with an off switch for every player.",
                    "does": ["Picks a pattern for each moment you name (jump, coin, hit, game over...)",
                             "Checks pulse length for the motor, gaps you can feel, and that no two patterns feel the same",
                             "States battery cost per play",
                             "Exports iPhone Core Haptics files, Android code and a DRV2605 driver (compiled here)",
                             "Your OK puts them into your game (HoolaHaptics) with an off switch and intensity"],
                    "needs": ["The moments that should buzz, and the device (phone, controller or your own board)"],
                    "never": ["Buzz for everything", "Ship patterns without an off switch",
                              "Promise vibration in iPhone browsers (they have none)"]},
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
    # v0.453 EDUCATION, RESEARCH & LAB: the Shiksha suite (v0.381 / v0.387 / v0.403) and Prayogshala (v0.415 / v0.441) were
    # live on the server and the phone but never in the Hub. Hiring one adds the Education Desk to the console sidebar; it
    # does NOT gate the tools - every user had them before this version and keeps them (see EDU_OPEN).
    "tutor": {"name": "Personal Tutor (Guru Sahayak)", "live": True, "icon": "book", "group": EDU_GROUP,
              "pitch": "Teaches one learner at a time: a hint first, then a step, the full answer last - and practice that comes back before it is forgotten.",
              "does": ["Explains a doubt with a hint ladder, one rung each time the learner asks",
                       "Checks an answer with code or the answer key before calling it right",
                       "Practice and revision on a spaced schedule, with an exam-mode window",
                       "An NCERT mastery path with gates: the next chapter opens once this one is learnt",
                       "Practice in the learner's own language",
                       "A weekly progress report for the guardian, sent only on your tap"],
              "needs": ["The learner's class, subjects and the language to teach in",
                        "For a child under 18: the guardian's consent and a daily time limit"],
              "never": ["Write the answer to graded homework, a test or an exam (hints and explanations only)",
                        "Work with a child without the guardian's consent, or past the daily time you set",
                        "Share a child's details or report with anyone but the guardian, and that only on your tap",
                        "Call an answer certain when no code or answer key checked it"]},
    "school_office": {"name": "School Office Assistant (Daftar)", "live": True, "icon": "book", "group": EDU_GROUP,
                      "pitch": "Runs the school office: attendance, grading, timetable and report cards - with every mark signed off by the teacher.",
                      "does": ["Daily attendance and an absence alert card for each guardian, sent on your tap",
                               "Grades answer sheets, OMR sheets, Google Forms quizzes, code and rubric work",
                               "Its marks are suggestions until the teacher signs them off",
                               "Builds the timetable from periods, teachers and subjects",
                               "Report cards made only from signed-off marks"],
                      "needs": ["Classes and sections, periods per day", "Teachers and their subjects, term names and your grade scale"],
                      "never": ["Make a mark final without the teacher's sign-off",
                                "Handle a child's marks or attendance without the guardian's consent",
                                "Send a guardian a message, alert or report card without your tap, or to any other child's guardian",
                                "Send bulk WhatsApp messages by itself"]},
    "curriculum": {"name": "Curriculum & Exam Designer (Pathyakram)", "live": True, "icon": "book", "group": EDU_GROUP,
                   "pitch": "Question banks, board-pattern papers with answer keys, year and lesson plans, and rubrics - every item approved by a teacher.",
                   "does": ["A question bank where every AI question is a draft until a teacher approves it",
                            "Papers in your board's pattern with an answer key and blueprint",
                            "Year plans, lesson plans and marking rubrics",
                            "Swaps a question in a paper without rebuilding it",
                            "Shares a paper or plan only when the teacher taps"],
                   "needs": ["Your board (CBSE / ICSE / state), classes, subjects, medium and session"],
                   "never": ["Copy copyrighted syllabus or textbook text (chapter names, codes and official links only)",
                             "State a board pattern or marks as certain without a source - it says 'estimate'",
                             "Send a paper, quiz or plan out without the teacher's or your tap",
                             "Touch a leaked or 'leaked' exam paper"]},
    "research": {"name": "Research Assistant (Shodh)", "live": True, "icon": "book", "group": EDU_GROUP,
                 "pitch": "Finds and reads the literature through official scholarly APIs, maps the gaps and keeps your references exact.",
                 "does": ["Searches OpenAlex, Crossref, arXiv and PubMed; every DOI is checked on Crossref",
                          "Screens papers against your question and summarises the ones that pass",
                          "A review matrix and the research gaps across the papers",
                          "References in BibTeX or RIS in your university's style",
                          "Data analysis as code in a locked sandbox, so every number can be traced",
                          "Section drafts that carry an AI-assistance note"],
                 "needs": ["Your topic, field and citation style", "Optionally an email address for polite use of the scholarly APIs"],
                 "never": ["Cite a paper or reference no official API returned",
                           "Write a thesis, assignment or paper for you to submit as your own",
                           "Put a number in the results that the analysis did not produce",
                           "Get past a paywall (only legal open-access copies)"]},
    "school_register": {"name": "School Register (Shiksha)", "live": True, "icon": "book", "group": EDU_GROUP,
                        "pitch": "The school's register: classes, learners, guardian consent and the gradebook every other education employee works from.",
                        "does": ["Classes, sections and learners in one register",
                                 "Guardian consent recorded per learner before any child's data is used",
                                 "A shared question bank across classes",
                                 "The gradebook, where only teacher-signed marks are final"],
                        "needs": ["Your institution, board, medium and academic year"],
                        "never": ["Use a child's details without the guardian's consent",
                                  "Show marks to anyone but the learner's own guardian",
                                  "Treat an AI mark as final"]},
    "lab": {"name": "Virtual Science Lab (Prayogshala)", "live": True, "icon": "book", "group": EDU_GROUP,
            "pitch": "22 NCERT physics practicals in a realistic 3D lab: real equipment, the steps, the record book, the graph and the viva.",
            "does": ["Theory, steps, record book, graph and viva for each practical",
                     "Readings computed by the same physics code that checks them, within 1 %",
                     "Ask Hoola inside any lab when a step is unclear",
                     "Works on a phone or a computer, no install"],
            "needs": ["Nothing: open a lab and start"],
            "never": ["Show a reading its own physics code did not compute",
                      "Stand in for a practical your board requires to be done in a real lab"]},
    "erp": {"name": 'ERP Architect (SAP / Oracle)', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Reads your SAP or NetSuite modules and fields and turns them into integration specs, field mappings and migration sheets.',
        "does": ['Integration specs, field mappings and migration sheets from your real system', 'The whole ERP lifecycle as one desk: blueprint, data, security, testing, cutover, support', 'Reads run at once; every write goes plan, dry run, your tap, then verified'],
        "needs": ['Your own SAP or NetSuite connection, joined on the Systems page (the key is sealed)'],
        "never": ['Make an ERP entry without your tap', 'Delete records, at any size', 'Work without saying whether it is the production or the test system']},
    "crm_arch": {"name": 'CRM Architect (Salesforce)', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Reads your Salesforce objects, flows and permissions and plans the customisation, with a test list.',
        "does": ['Describes your org and runs read-only SOQL', 'Customisation plans, security matrices and test lists', 'Configuration changes go through a validated deploy that you approve'],
        "needs": ['Your Salesforce org, joined with your own login'],
        "never": ['Change your live org without your tap', 'Delete records, at any size', 'Guess whether a change is data or configuration']},
    "tpm": {"name": 'Technical Product Manager', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'The engineering side of delivery: dependencies, architecture decisions, NFRs, tech debt, capacity, release train and risks.',
        "does": ['Critical path, capacity and delivery metrics worked out in code, never guessed', 'RAID log, release readiness and who has gone quiet', 'Status built only from what each owner actually said'],
        "needs": ['Your tracker (Jira / Linear / Asana) or a sheet of the work'],
        "never": ['Promise a date to anyone on your behalf', 'Write a status the team did not give', 'Change your tracker without your tap']},
    "bpa": {"name": 'Process Automation Architect', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Connects the work between two systems as a step-by-step flow and runs it.',
        "does": ['Designs the flow between your apps (Composio, SAP, Oracle, Salesforce)', 'Runs it on one test record first, then on all', 'Every writing step passes the trust gate'],
        "needs": ['The apps you want joined, connected with your own accounts'],
        "never": ['Run a flow on all records before a test record passed and you said yes', 'Write to another system without its trust gate']},
    "ecom_arch": {"name": 'E-Commerce Systems Architect', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Checks your catalogue, stock, prices and checkout - what breaks under a rush - and fixes listings.',
        "does": ['Catalogue, stock, price and checkout checks on your own store', 'Load-risk notes: what fails when traffic spikes', 'Listing fixes drafted for your OK'],
        "needs": ['Your Shopify store or a sheet of your catalogue'],
        "never": ['Change a price or the catalogue without your tap', 'Use a stock number that was not read from your store']},
    "health_int": {"name": 'Healthcare Integration (HL7 / FHIR)', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'The ABDM paperwork end to end: FHIR R4 record structure, the ABHA flow, the M1 / M2 / M3 checklist and audit papers.',
        "does": ['FHIR R4 structures and sample data', 'ABHA flow and milestone checklists', 'Audit-ready documents'],
        "needs": ["Your hospital or clinic's systems described in a sheet"],
        "never": ["Read or send any real patient's data", "Take the ABDM production route on your behalf - that stays in your organisation's name"]},
    "bank_int": {"name": 'Core Banking Integrator', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Statement reconciliation, ledger matching, reporting formats and the Account Aggregator readiness checklist.',
        "does": ['Reconciliation by reference, then amount and date together', 'Ledger matching where each line is used once', 'Account Aggregator readiness checklist'],
        "needs": ['Statements and your Tally or ledger export'],
        "never": ['Move money or connect to a bank directly (RBI rules: only a regulated entity can be an FIU)', 'Write a full account number - last 4 digits only']},
    "supply_opt": {"name": 'Supply Chain Optimisation', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'The cheapest plan across routes, warehouses and orders, reorder points and stock levels - savings shown in rupees.',
        "does": ['Reorder points from real demand and lead time', 'Dead stock and stockout dates', 'Every saving shown with its working'],
        "needs": ['At least 14 days of sales and stock history'],
        "never": ['Place an order - you place it', 'Show a saving without the calculation behind it']},
    "plm": {"name": 'PLM Specialist', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Reads Windchill parts, BOMs and change orders and drafts the change with its impact.',
        "does": ['BOM explosion with costs rolled up from the parts', 'Where-used for any part', 'Change drafts with their impact'],
        "needs": ['Your Windchill server (Teamcenter is read-only)'],
        "never": ['Write to a BOM without your tap', 'Leave your object checked out after a half-finished run']},
    "regtech": {"name": 'RegTech / Compliance Automation', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'A compliance calendar that watches every date, prepares the filing papers and warns when a rule is about to break.',
        "does": ['Due-date calendar with the source of every date', 'Filing papers prepared', 'Exposure worked out only from penalty figures you gave'],
        "needs": ['The returns and registrations your business has'],
        "never": ['File on a government portal for you - you file', 'Give legal advice: it cites the rule, not an opinion']},
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
