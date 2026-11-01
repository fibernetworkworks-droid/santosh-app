# HOOLA PRAYOGSHALA — a real practical lab in 3D, for every field

Owner's ask (1 Nov 2026): "NOW A REAL PRACTICAL LAB --- FOR EVERY FIELD IN WORLD HOOLA WILL SHOW IN 3D HOW THINGS
ARE WORKS. --- MAKE A PLAN". This file is the plan.

**Status (1 Nov 2026):**
- **L0 + L1 BUILT** (owner: "GO L0 + L1"). Search "PRAYOGSHALA L0 + L1" in docs/HISTORY.md for the details.
- Decision 2 changed while building: L1 uses Hoola's OWN deterministic kernels, each with a Python and a JS twin, instead of
  a physics engine. Every NCERT practical needs exact numbers, not a game engine, and own code is what lets the server
  prove the phone's numbers. Rapier vs cannon-es moves to L4 (machines), where real multi-body contact is needed.
- Decision 3 (sharing) is still open. Today's catalogue is public teaching material with no user data.

## 1. What "a real practical lab" has to mean

A video of a beating heart is not a lab, and neither is a model that spins on the screen. A lab exists when the learner
can **change something and see the true result**. Every Prayogshala lab must have all six of these:

1. **3D you can hold**: rotate, zoom, cut it open (section plane), explode it into parts, and tap a part to see its name.
2. **Knobs**: sliders and switches for the real inputs (length of a pendulum, resistance, pH, gear ratio, valve timing).
3. **True behaviour**: the motion and the numbers come from **code that does the physics, chemistry or maths**, never
   from the model's imagination. A wrong lab looks exactly as confident as a right one, so the sum must live in code
   (the same rule as v0.374 TPM KE HISAAB).
4. **Instruments**: a stopwatch, ruler, protractor, voltmeter / ammeter, thermometer, pH meter and graph plotter. The
   learner reads them and fills an observation table, the same way a school practical works.
5. **Explain**: Hinglish (or her language) narration with a guided camera tour, then predict → observe → explain.
6. **Honest labels**: every number shows where it came from (a kernel, a cited source, or "illustrative only").

## 2. What Hoola already has (reused, not rebuilt)

| Already built | Used for |
|---|---|
| `appmaker/assets/scene3d.js` + vendored `three.min.js` r149: a 3D scene drawn from **DATA only** (shapes, materials, lights, animations), with no network and no model-written code | The base of the lab runtime. The same safety rule applies: Opus writes data, never JavaScript |
| Engineering desk (`engineering/`): CadQuery parts / assemblies → GLB, FEA stress / heat / modes, gears, bearings, fasteners | Machines and engineering labs: exploded assemblies, stress shown as colours, gear trains |
| `pylab` sandbox | The Python twin of every kernel for tests, plus heavy runs (e.g. a 10,000-step simulation) |
| Shiksha / Pathyakram / Guru / Daftar | The lab as a lesson step, teacher assignment, observation sheet → grading, mastery |
| Shodh + NCERT book grounding | Citations for every fact in the narration |
| Voice TTS + Gemini / OpenAI call | Narration and "ask while you watch" |
| Game desk (Godot Web export) | Only for the rare lab that needs a full game engine. The default is three.js (lighter on phones) |
| Phone `webview_flutter`, console panel | The viewer on both surfaces |

## 3. The design: ONE engine, not a million hand-made labs

"Every field in the world" cannot mean drawing each lab by hand. It needs three layers:

**A. Lab Scene Language (LSL), data only.** One JSON describes a lab:
`bodies` (primitive shapes / a GLB from the asset library / a CAD part), `joints` (hinge, slider, gear mesh, rope),
`fields` (gravity, E / B field, flow), `kernel` (which simulation drives it + its parameters), `knobs` (min / max /
step / unit, bound to kernel parameters), `instruments`, `labels`, `tour` (camera stops + narration lines),
`observation_table`, `questions`, `sources`. A strict checker validates it (units, ranges, every knob bound to
something real, every label pointing at a body that exists, and a triangle budget).

**B. Kernels: the true behaviour, in code.** Each one is a small, deterministic JavaScript module with a **Python
twin** that must give the same numbers (tested on the server, so a JS bug cannot slip through):

| Kernel | Covers |
|---|---|
| `mech` rigid bodies + constraints (vendored **Rapier** wasm, Apache-2.0, or cannon-es, MIT) | levers, pulleys, inclined planes, collisions, pendulums, projectiles, cranes, vehicles |
| `osc_wave` | SHM, springs, resonance, sound, standing waves, Doppler |
| `optics` ray tracer | lenses, mirrors, prisms, refraction, TIR, the eye, microscope, telescope, fibre optics |
| `em` | field lines, charges, a magnet + coil, motor, generator, transformer |
| `circuit` (MNA solver) | Ohm's law, series / parallel, Wheatstone / meter bridge, RC charging, diode, transistor, house wiring (ITI) |
| `thermo` particles | gas laws, kinetic theory, heat engine cycles (Otto / Diesel / Carnot), refrigerator, AC |
| `chem` | molecules in 3D (PubChem's own 3D conformers, official PUG-REST), bonds / orbitals as shapes, titration (true pH curve from Ka / Kb), stoichiometry, electrolysis, equilibrium |
| `flow` | pipes, pumps, Bernoulli, a heart chamber, blood flow, irrigation, (reusing `fea.flow` for 3D) |
| `orbit` | solar system from NASA JPL Horizons ephemeris (official API), eclipses, seasons, satellites |
| `bio_process` keyframes + rates | cell division, DNA → protein, nerve impulse, photosynthesis, digestion (timed processes with real rates where known, "schematic" badge where not) |
| `math3d` | surfaces z = f(x, y), vectors, solids of revolution, probability (dice / Galton board), linear algebra |
| `flow_graph` | non-physical fields drawn as 3D systems: money in an economy, a packet across the internet, a CPU executing an instruction, a supply chain, how a bill becomes a law |

**C. The author: "Mujhe dikhao X kaise kaam karta hai".** Each request goes through these steps:
1. Opus picks the kernel(s) and writes the LSL.
2. The checker validates it.
3. Chromium headless renders 4 stills plus a 10-second run of the kernel.
4. A vision review checks the stills against the brief and fixes what is wrong (the same pattern as CAD's vision review).
5. Only then does the learner see it.

**A finished lab is cached by topic + level, so it is built once and every later user gets it free.** That one rule is
what makes "every field" affordable.

**Asset library**: only permissive, attributed sources, recorded in THIRD_PARTY_NOTICES.md:
- PubChem 3D (public domain data)
- NASA 3D Resources (public domain)
- BodyParts3D / Z-Anatomy (CC BY-SA, attribution shown in the lab)
- NIH 3D (licence checked per model)
- Hoola's own CAD parts

Every model is decimated to fit the phone budget.

## 4. Fields covered (catalogue targets)

- **School science (CBSE / State boards 6-12):** every experiment in the NCERT lab manuals: Physics, Chemistry, Biology.
  This is the first proof set because it has a fixed list and known right answers.
- **Engineering:** mechanical (engines, gearboxes, pumps, turbines), civil (truss loads, beams, foundations, water
  supply), electrical (motors, transformers, grid), electronics, chemical (distillation column, reactor).
- **ITI / vocational trades:** electrician wiring, fitter, welder (heat zones only, no hazard instructions), motor
  mechanic, plumber, AC technician.
- **Medicine / nursing / pharmacy (education only, never advice):** anatomy with sections, the heart cycle, lungs,
  kidney filtration, drug action at a receptor (schematic), injection sites for nursing.
- **Agriculture:** soil layers, drip irrigation flow, the plant life cycle, a tractor's PTO, greenhouse heat.
- **Earth and space:** plate tectonics, the water cycle, monsoon, earthquakes (waves), the solar system, satellites.
- **Maths, computer science, economics, civics:** through `math3d` + `flow_graph`.

## 5. Phases

| Phase | What gets built | Proof before moving on |
|---|---|---|
| **L0 LAB RUNTIME** | `prayog/` module: LSL schema + checker, `lab3d.js` (extends scene3d: orbit / zoom, section plane, explode, tap-to-name, knobs, instruments, observation table, tour with narration), console Lab page + phone `lab_screen.dart` (WebView, offline after the first load), private share link | 10 hand-written labs open on her phone at ≥ 30 fps, every knob moves something true |
| **L1 PHYSICS KERNELS** | `mech`, `osc_wave`, `optics`, `em`, `circuit`, `thermo`, each with a Python twin + a same-numbers test | NCERT physics manual (~20 experiments) built; each reading within 1 % of the textbook value |
| **L2 CHEMISTRY** | `chem` kernel, PubChem 3D molecules, titration / electrolysis / equilibrium labs, a safety rule list (school-level reactions only) | NCERT chemistry manual set; the titration pH curve matches the computed curve |
| **L3 BIOLOGY + BODY** | anatomy library (sections, layers), `bio_process`, the heart / lungs / kidney through `flow` | NCERT biology set + 10 anatomy labs, every label checked against its source |
| **L4 MACHINES + TRADES** | CAD → lab bridge (any engineering-desk assembly becomes a lab: explode, animate the joints, FEA colours), engine / pump / motor library, ITI wiring with `circuit` | 25 machines run with the correct motion (gear ratio, valve timing read from the kernel) |
| **L5 EARTH, SPACE, AGRI** | `orbit` (JPL Horizons), earth processes, agriculture labs | the eclipse dates the lab shows match NASA's list |
| **L6 ABSTRACT FIELDS** | `math3d`, `flow_graph` | 30 labs across maths, CS, economics, civics |
| **L7 AI AUTHOR** | Opus → LSL → checker → stills + run → vision review → cache; agent tool `prayog` + `prayog_dekho`; the voice call hands it to `santosh_kaam` | 100 asks from 20 fields via the real path: ≥ 90 % pass the checker on the first or second try, with the cost per new lab measured |
| **L8 CLASSROOM** | lab as a Guru lesson step, teacher assigns it in Shiksha, observation sheet → Daftar grading (unsigned until the teacher signs), a **virtual practical exam** (CBSE practical format: aim, procedure, readings, result, viva) | one full class runs a practical end to end |
| **L9 SHARE, AR, VIDEO** | narrated MP4 of the tour (headless render + TTS), AR on the phone (Android Scene Viewer intent with the GLB, iPhone Quick Look USDZ), optional WebXR | the AR opens on her Android phone, and the MP4 plays in WhatsApp |
| **L10 PROOF CARD** | `python -m app.quality lab`: 500 labs × 20 fields, checker pass, kernel vs textbook numbers, fps on a ₹10k Android, size, cost per lab | the card shown to the owner |

**Suggested start: L0 + L1** (the runtime plus physics). Physics has the clearest right answers, so it proves the
engine honestly before any other field rides on it.

## 6. Costs and limits (to confirm with real runs)

- **Viewing a lab:** free, because it runs on the learner's phone.
- **A NEW lab from the AI author:** one Opus authoring call plus one vision review. I expect roughly ₹15-40 for each
  new topic, but this is an estimate until L7 measures it. The price card is shown first, as with everything else.
  A cached lab costs nothing.
- **Phone budget:** ≤ 80k triangles, ≤ 8 MB per lab, 30 fps on a mid-range phone (all to be measured in L0).
- **Server:** it only authors and caches labs, so no GPU is needed. Headless Chromium is already on the VPS (website desk).

## 7. Never

- **Opus never writes JavaScript for a lab.** It writes data only, and the runtime refuses anything else (the same rule
  as scene3d).
- **No number is invented.** Every number comes from a kernel or a cited source. A schematic process wears an
  "illustrative" badge.
- **No dangerous labs**, whatever field is claimed: explosives, weapons, drug synthesis, pathogen handling and harmful
  chemistry beyond school-level reactions are refused. Medical labs are education and never advice.
- **No unlicensed models:** every asset's licence and attribution is recorded, and anything without a clear licence
  is not used.
- **No children's data leaves Shiksha's consent rules** (DPDP s.9, as in Phase 0).
- **No frozen PC / desktop files are touched.**

## 8. Decisions for the owner

1. Start with **L0 + L1** (runtime + physics)? Or with another field first?
2. Physics engine: **Rapier** (faster, Apache-2.0 wasm, ~1.5 MB) or **cannon-es** (smaller, MIT, pure JS)? My
   recommendation is Rapier, with cannon-es as the fallback on very old phones.
3. Should cached labs be shared across all users (cheapest, and a public library grows) or kept private per school
   unless it publishes them?

## 9. Not verified yet (checked during each phase)

- three.js r149 performance on her phone with knobs moving (L0).
- Rapier wasm loading inside the Android WebView (L1).
- PubChem 3D conformer coverage for school chemicals (L2).
- The exact licence of each anatomy model file (L3).
- Whether JPL Horizons rate limits are fine for caching (L5).
- The real Opus cost per authored lab (L7).
- Scene Viewer intent behaviour on her phone (L9).
