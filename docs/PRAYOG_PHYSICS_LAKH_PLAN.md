# PRAYOGSHALA PHYSICS — 1 lakh experiments, every chapter, school to PhD

Owner, 2 Nov 2026: "NOW LETS WORK ON PHYSICS REMAINING EXPERIMENTS --- COVER 1 LAKH EXPERIMENT FROM ALL CHAPTERS TILL PHD".

Starting point: v0.441 has 22 labs in the realistic studio (`static/prayog/studio/studio.js` + one hand-written
`exp/<id>.js` per lab, about 400 lines each, all 22 verified by `tools/prayog_walk.js`).

## 1. What "1 lakh" can honestly mean

There are not 1 lakh *different apparatus set-ups* in physics. Counted from the syllabi below, there are about
**2,000–2,500 distinct set-ups** from Class 6 to research labs. Real lab manuals multiply each set-up in five
ways, and each way is a genuinely different practical a student does:

| Multiplier | Example (Young's modulus) | Typical count |
|---|---|---|
| **Method** | Searle's apparatus · bending of a beam · Ewing's extensometer · cantilever oscillation | 2–5 |
| **Sample / material** | steel · copper · brass · aluminium · nichrome wire | 3–10 |
| **The unknown** | find Y · find the load for a given strain · find the wire radius from Y | 2–4 |
| **Level** | Class 11 reading only · B.Sc error analysis · M.Sc least-squares fit with uncertainty | 1–4 |
| **Conditions** | room temperature · heated wire · different lengths | 1–5 |

So 1 lakh = about 2,200 set-ups × about 45 meaningful variants. **A variant is counted only if:**
1. its numbers come from a tested kernel;
2. the walk-through runs it through its real buttons;
3. the result lands within tolerance of the true value.

A variant that fails is never shown and never counted. The proof card (Phase P8) states the real number.

## 2. Why the 22-lab method cannot reach it

A hand-written module per lab took about 400 lines and one sub-agent run each. 1 lakh that way is impossible, and
2,200 hand-written modules would be unmaintainable. So the studio moves from **"one module per lab"** to
**"rig + spec"**:

- **Part** (~400): a real piece of apparatus, built once and reused everywhere. Examples: travelling microscope,
  spectrometer, Searle's apparatus, Lee's disc, CRO, function generator, GM counter, lock-in amplifier, cryostat,
  laser, photodiode, electromagnet, Hall probe, X-ray diffractometer.
- **Kernel** (~80): the true physics in Python, with a JS twin and a same-numbers test. Today there are 16.
- **Rig** (~250): a procedure template that places parts, joins them to a kernel, and defines the hand actions and
  steps. One rig covers a whole family. For example, `rig.resonance_column` serves both the resonance tube and
  Kundt's tube with different parts.
- **Spec** (1 lakh): small JSON with `rig + kernel params + hidden unknown + sample + level + theory text + viva`.
  Most specs are produced by a generator from a family table; none are hand-drawn.

The studio engine, record book, graph, viva and Ask Hoola stay as they are. The 22 existing labs become the first
22 specs and must still pass byte-for-byte on the walk.

## 3. The catalogue (sources = official syllabi only)

| Level | Source (official) | Distinct set-ups (estimate, P0 counts them) |
|---|---|---|
| Class 6–10 | NCERT Science textbooks + Lab Manual activities, NCERT Exemplar | ~350 |
| Class 11–12 | NCERT Physics Lab Manual (practicals + activities), CBSE practical syllabus, state boards | ~250 |
| UG (B.Sc / B.Tech) | UGC LOCF B.Sc Physics practicals, AICTE model curriculum (Engineering Physics), university lab manuals | ~650 |
| PG (M.Sc) | UGC model M.Sc Physics curriculum, IIT / IISER / university M.Sc lab manuals | ~550 |
| PhD / research techniques | Standard advanced-lab texts (e.g. Melissinos *Experiments in Modern Physics*) and published methods | ~450 |

**Chapters, every level:**
- units and measurement;
- mechanics;
- elasticity, fluids, surface tension and viscosity;
- heat and thermodynamics;
- oscillations, waves and acoustics;
- optics, both ray and wave, plus polarisation;
- electrostatics, current electricity and magnetism;
- electromagnetic induction and AC;
- electronics: diode, transistor, op-amp, digital, communication;
- modern and atomic physics;
- nuclear physics;
- solid state and materials;
- spectroscopy (UV-Vis, Raman, ESR, NMR, Mössbauer);
- laser and quantum optics;
- low temperature and superconductivity;
- plasma;
- astrophysics data labs;
- computational physics.

## 4. Kernels to add (~64 new, each with a Python twin + a same-numbers test)

| Area | Kernels |
|---|---|
| Mechanics and properties of matter | rigid-body rotation (moment of inertia, flywheel, torsion pendulum), compound and Kater's pendulum, Searle's / bending / cantilever (Young's modulus), modulus of rigidity, Poiseuille flow, capillary rise / Jaeger, gyroscope, collisions, projectile |
| Heat | Lee's disc / Searle's conductivity, Stefan's law, thermocouple, thermistor, Callendar's, J by electrical method, adiabatic γ (Clément–Desormes / Rüchardt) |
| Waves | Melde's, Kundt's, Doppler, beats, ultrasonic interferometer |
| Optics | Newton's rings, Fresnel biprism, Michelson, Fabry–Pérot, diffraction grating, single / double slit, Malus / Brewster, optical activity (polarimeter), Rydberg spectrum, dispersive power, resolving power, fibre NA, laser beam profile |
| Electricity and magnetism | LCR resonance (series / parallel, Q), tangent galvanometer + earth's field, Helmholtz coil, B-H hysteresis, ballistic galvanometer, Anderson / Maxwell / Schering bridges, Carey-Foster, transformer, induction motor slip |
| Electronics | BJT / FET characteristics + amplifiers, Zener regulator, rectifier + filters, op-amp (inverting, integrator, oscillators), logic gates / flip-flops, modulation / demodulation, 555 timer |
| Modern physics | photoelectric (h), LED Planck's constant, e/m (Thomson), Millikan oil drop, Franck–Hertz, Hall effect, four-probe bandgap, solar-cell I–V, GM counter statistics + absorption, half-life, Compton, X-ray diffraction (Bragg), Zeeman |
| PG / PhD | ESR (g-factor), NMR (Larmor), Mössbauer, Raman, superconducting Tc (R–T), Josephson I–V, quantum Hall (simulated), laser rate equations, optical tweezers (trap stiffness), Hanbury Brown–Twiss / g², BEC (simulated), Monte Carlo Ising, lock-in detection, cryogenic thermometry |

Research-level labs whose real apparatus no student can touch carry a **"simulated instrument"** badge: SQUID,
Mössbauer, dilution fridge and BEC. Their numbers still come from published models, cited in the lab.

## 5. Phases

| Phase | What gets built | Proof before moving on |
|---|---|---|
| **P0 CATALOGUE** | `prayog/catalog/physics/*.json`: the full set-up tree (level → chapter → set-up → methods → samples → unknowns), every row citing its syllabus line; a counter that prints the real totals | the counted set-ups per level and the variant total, shown to the owner |
| **P1 RIG ENGINE** | `studio/rigs/` + `studio/parts/` + spec loader; the 22 labs re-expressed as specs; a generator `prayog/gen.py` (family table → specs); server catalogue moves to a paged index (1 lakh cannot be one JSON) | all 22 pass the walk with the same numbers as v0.441; 1 spec → page in under 1 s |
| **P2 SCHOOL** | Class 6–12 complete: ~600 set-ups, new parts + kernels as needed | every school set-up passes the walk; NCERT values within 1 % |
| **P3 UG** | B.Sc / B.Tech labs: ~650 set-ups, about 30 kernels | walk pass + textbook values |
| **P4 PG** | M.Sc labs: ~550 set-ups (spectroscopy, solid state, nuclear, electronics) | walk pass + cited values |
| **P5 PhD** | research techniques: ~450 set-ups, simulated-instrument badge where needed | walk pass + values from the cited papers |
| **P6 VARIANTS → 1 LAKH** | generator expands every set-up by method × sample × unknown × level × condition; each variant is walked headless on CI in shards (≈ 1 lakh × ~2 s ≈ 55 CPU-hours, so 20 parallel jobs ≈ 3 hours) | only passing variants are published; the real count is printed |
| **P7 FIND IT** | browse by level / chapter / topic, search, "experiments like this", syllabus mapping (CBSE / state / university), Ask Hoola across a chapter | any experiment reachable in 3 taps; search under 300 ms on the VPS |
| **P8 PROOF CARD** | `python -m app.quality prayog`: counts per level / chapter, walk pass %, error vs truth, page size, fps on a ₹10k Android | the card shown to the owner |

## 6. Limits said plainly

- **1 lakh walk-throughs are CI work, not sandbox work.** They run sharded on GitHub Actions (a `prayog-walk.yml`
  workflow), not in this session.
- **Look and feel.** Generated variants share the rig's look. A copper wire and a steel wire on Searle's apparatus
  differ in colour, numbers and theory notes, not in hand-made scenery. The set-ups themselves (~2,200) each get a
  real rig.
- **Facts and numbers.** Every syllabus line and textbook value is cited. Nothing is invented to make up the count.
  If the honest total after P0 is below 1 lakh, the card says so and names the gap. The total is never padded with
  near-duplicates.
- **Phone budget.** Each lab page loads only its rig + parts (≤ 3 MB), never the whole catalogue.

## 7. Suggested start

**P0 + P1.** The real count comes first, so the owner sees where 1 lakh comes from. Then the rig engine, because
every later phase rides on it and the 22 existing labs prove it changes nothing that already works.

## Build-out log and hand-off notes (live)

The meter is `cd server && python3 -m app.prayog.count --cover`. A set-up counts only when its `built` lab really
opens; a claim that does not open is reported as BROKEN, never counted.

**Engine work that made the build-out possible**
- Kernel packs (`prayog/packs/<area>.py` + the JS twin in `static/prayog/packs/`) and lab packs
  (`prayog/labs/<area>.py`): new physics and new set-ups go in their OWN files, so many people build at once.
- `/api/prayog/kernels.js` serves kernels.js plus every pack as one script.
- `tools/prayog_claim.py` applies build agents' claims centrally.
- The twin test now covers PACK kernels numerically (it did not: a drifting JS twin passed silently).
- The LSL checker no longer refuses real physics: a parameter may carry 6e23 or 1.6e-19 (`PHYS = 1e30`). Ten
  modern / nuclear labs were being silently dropped by the old 1e12 cap.
- The catalogue route pages at 100 by design; its test asks for the full page.

**Cheap next wins named by the build agents**
- `specific-heat-liquid-mixtures` (XI-XII): reuses the shipped `mixtures` kernel; `mix_Tf` is already its check and
  `mix_c_liquid` is already a CALC in packs/mech11.py. Only a calorimeter rig is missing.
- `pendulum-energy-dissipation` (XI-XII): rides the shipped `pendulum` kernel, which already has damping `b`.
- `sound-through-solids` (VI-X): v = sqrt(Y / rho) with two sensors on a rod; Y and rho are CRC constants.
- `reflection-of-sound-tubes` (VI-X): measures the peak angle against i = r.
- `radiation-black-white-tins` (VI-X): steady dT = alpha G / h, solar absorptance from published tables.
- The 7 Class XII ray-optics set-ups (convex mirror by lens, concave lens by convex, liquid lens, liquid mirror,
  lateral deviation, image nature, lens combination) need ONE new two-element ray-trace kernel; the shipped
  Lens / Mirror kernels trace a single element only.
- The 2 Alternating Current set-ups need an AC source and an inductor element in the circuit kernel.

**Known honest gaps (not to be faked)**
- Qualitative school activities with no measurable unknown (push-pull effects, transparent vs opaque, inertia of a
  coin, balloon rocket, convection): a `check` within 1 % of a textbook formula cannot be written for them without
  turning the activity into a different experiment.
- Assembly / diagnosis activities (identify the components, find the open circuit, household wiring): there is no
  measured quantity for the walk to check. These need a build-a-circuit interaction the studio does not have.
- Dispersion and colour set-ups need n(lambda) (Cauchy / Sellmeier) and a colour-matching kernel.
- Jaltarang: a struck glass is a shell mode and a blown one is a Helmholtz resonator; the quarter-wave pipe formula
  would be invented physics. An agent built that kernel and then deleted it rather than ship it.

**Load note**: each walk drives a real headless browser. Six build agents saturate a 4-core box (load 35, one
OOM kill). Run at most 4 - 6 agents at a time, and never edit a rig's .js while its walk is loading it.
