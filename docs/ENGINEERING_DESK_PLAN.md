# Hoola Engineering Desk — plan for "Research, CAD, Hardware & Industrial Tech" employees

Owner asks (1 Nov 2026): *"NOW LETS WORK ON EMPLOYEE SECTION READ FIRST THEN WE WORK ON Research, CAD, Hardware &
Industrial Tech"* (her list IX, 10 roles) → *"GO PLAN"*.

Ten hireable AI employees on the frame SEO and Social built (`employee/hire.py`: hire → onboard → desk → jobs → trust →
report). They share one new base, the **Engineering Desk**: Hoola writes engineering code, runs a free open-source solver
in a locked box on the server, and puts the model, numbers, plots and a report on her desk. Each role then adds its own
**pack** (solver + checks + report template + standards checklist).

---

## 1. What a good engineer in each role actually delivers

| # | Role | A real deliverable | What "good" means |
|---|------|--------------------|-------------------|
| 1 | CFD Programmer | Flow / heat case: geometry → mesh → solver setup → run → pressure / velocity / drag / temperature plots + report | Mesh study (3 sizes), residuals converged, y+ checked, result compared with a hand estimate |
| 2 | CAD / CAM Software Engineer | A part from words / a sketch / a photo with numbers: parametric 3D model, STEP + STL + drawing PDF, CNC toolpath (G-code) | Every dimension from her numbers, units stated, wall thickness / draft / tolerances checked, toolpath simulated |
| 3 | Industrial IoT System Architect | Plant network + SCADA design: device list, protocol map (Modbus / OPC-UA / MQTT), zones & conduits (IEC 62443), bill of materials, config templates | Each tag has an owner, OT and IT split, no device reachable from the internet, data flow drawn |
| 4 | Automotive ECU (AUTOSAR) Programmer | C modules + configs, unit tests, MISRA C report, requirement → code → test trace | Zero required-rule MISRA findings or each one justified, tests cover the requirement list |
| 5 | Spacecraft Flight Software Engineer | Flight code review / modules, fault handling, tests, coding-standard report (NASA "Power of 10", JPL C) | No dynamic memory after init, bounded loops, every return value checked, tests per requirement |
| 6 | Medical Device Embedded Engineer | Software files in the IEC 62304 structure: plan, requirements, architecture, risk (ISO 14971), unit tests, trace | Safety class stated, every hazard has a control and a test, traceability complete |
| 7 | Acoustic Simulation Engineer | Room / hall / enclosure sound: RT60, impulse response, SPL map, treatment suggestions, audio preview | Method stated (image source / ray), absorption values sourced, compared with Sabine estimate |
| 8 | Structural Analysis (FEA) Developer | Part / beam / bracket: mesh → loads / supports → stress, deflection, safety factor plots + report | Units, material from a cited table, mesh convergence, hand calc cross-check, max stress vs yield |
| 9 | Semiconductor Lithography Software Engineer | Chip layout (GDS / OASIS) scripts: DRC rule checks, layer maths, density / fill reports, layout generators | Rule deck stated, every violation located with coordinates, scripts reproducible |
| 10 | Optical Systems Simulation Engineer | Lens / laser path: ray trace, spot diagram, focal length, beam propagation, tolerance table | Wavelength and glass data stated, paraxial check, aberration numbers, diffraction limit compared |

Never, for every role: claim a certification or approval (DO-178C, IEC 62304, ISO 26262, CE, FDA, CDSCO, AIS), sign
drawings, connect to a live plant / vehicle / device, use cracked commercial software, or hide that the work is
AI-made. Safety-critical outputs (roles 4, 5, 6, and any structure carrying people) always end with **"Draft for a
qualified engineer's review — not certified."**

---

## 2. What Hoola already has

- **Hire frame:** `employee/hire.py` (hire / pause / let go, trust seekh / saathi / bharosa), Employee Hub (console
  `employees.js`, phone `employees_screen.dart`), desk pattern from SEO (`seo/desk.py`) and Social.
- **Locked code runner pattern:** `blender3d/` = `guard.py` (AST check: allowed imports only, no files / network /
  internals), `runner.py` (cut-down builtins + import gate), `sandbox.py` (`unshare -rn` no network, tiny env with no
  secrets, own folder, RLIMIT memory / file size, nice 10, wall-clock kill), price + limits per tenant, signed file URLs,
  progress events. The Engineering sandbox is the same design with engineering libraries instead of `bpy`.
- **Code work:** Developer Sahayak (`devsahayak/`, PRs, rules-first v0.356), QA (`qa/`), Docs writer (`docwriter/`),
  App reviewer / REA static analysis (`appcheck/`, 7-tool allowlist), DevOps.
- **Reports:** Hoola Print (`docstudio/htmlpdf.py`, v0.313): designed PDFs with charts, captions, bookmarks.
- **Pictures:** Blender 3D renders, photogen; the workspace reader shows PDFs / images in the console.
- **Missing:** no CAD kernel, mesher, FEA / CFD / acoustic / optics / layout solver, no engineering units handling, no
  standards packs, no engineering desk.

---

## 3. The engines (all free, open-source, run as separate programs on the server)

| Use | Engine | Licence | Install |
|-----|--------|---------|---------|
| CAD (B-rep, STEP / STL) | CadQuery on OpenCASCADE | Apache-2.0 / LGPL-2.1 | `pip install cadquery` |
| Meshing | Gmsh | GPL-2.0+ | `pip install gmsh` |
| FEA (production) | CalculiX `ccx` | GPL-2.0 | `apt install calculix-ccx` |
| FEA (light, pure Python) | scikit-fem | BSD-3 | `pip install scikit-fem` |
| CFD | OpenFOAM (openfoam.org) | GPL-3.0 | OpenFOAM apt repo; Phase 3 only, heavy |
| CAM toolpaths | OpenCAMLib + own G-code post | LGPL-2.1 | pip / build; Phase 2b |
| Room acoustics | pyroomacoustics | MIT | `pip install pyroomacoustics` |
| Chip layout / DRC | KLayout Python module | GPL-3.0 | `pip install klayout` |
| Optics (rays) | RayOptics | BSD-3 | `pip install rayoptics` |
| Optics (beams / FDTD) | LightPipes; Meep later (conda only) | check at build | Phase 4 |
| C checks | cppcheck (+ MISRA addon), clang-tidy, gcc, Unity / CMocka tests | GPL-3.0 / Apache / MIT | apt |
| Plots / numbers | numpy, scipy, matplotlib, pint (units) | BSD | pip |

GPL engines are run as separate programs on Newtika's server and their output is returned to her; nothing GPL is linked
into Hoola or shipped in the APK. MISRA rule texts are copyrighted: the MISRA check uses rule numbers only unless she
uploads her own licensed rule file. Every licence is re-checked before its phase ships (`THIRD_PARTY_NOTICES.md`).

---

## 4. The Engineering Desk (shared base, Phase 1)

**4.1 Hire and onboarding (same frame as SEO / Social).** One catalogue entry per role in `hire.CATALOG`, grouped
under "Research, CAD, Hardware & Industrial Tech". Onboarding asks: what she makes / designs, units (mm-N-MPa default),
materials she uses, standards her customers need, and her review rule ("who signs off").

**4.2 Projects.** `engineering/` module: a Project = brief + inputs (her numbers, sketches, CAD files, datasheets) +
runs + results + report. Table `eng_projects` / `eng_runs` (self-healing tables, registered in `db.init_db`).

**4.3 The engineering sandbox** (`engineering/guard.py`, `runner.py`, `sandbox.py`, cloned from `blender3d/`):
- Allowed imports per role pack (e.g. CAD: `cadquery`, `math`, `numpy`; FEA: `gmsh`, `numpy`, `skfem`), nothing else.
- Hoola's helpers `E.*` do the file I/O: `E.save_step()`, `E.save_stl()`, `E.plot()`, `E.table()`, `E.run_solver("ccx",
  deck)`: the script never opens files, sockets or processes itself.
- No network (`unshare -rn`), no secrets, own folder, memory cap (default 4 GB), CPU time and wall-clock caps (default
  10 min), file-size cap, one job per user at a time, global queue.

**4.4 Price before every heavy run.** A run is priced from mesh size × solver × minutes (CPU rupees) + the model calls
that plan and check it. The price card is shown before the run; she taps Approve. Light runs (a CAD part, a ray trace)
stay under a small free daily allowance. Monthly cap per user, like Composio and Video Studio.

**4.5 Checks before results reach her.** Every pack has an automatic checker: units present, geometry valid / watertight,
mesh quality, solver converged, result within an order of magnitude of a hand formula, numbers in the report match the
run files. A failed check means Hoola fixes and re-runs (max 2) or tells her plainly which input is missing.

**4.6 The desk (console + phone).** Projects list; per project: 3D viewer (STL / glTF in the console with three.js;
image turntable on the phone), plots, numbers table, files (STEP / STL / G-code / GDS / C / PDF, signed links), run
history with prices, checks with pass / fail, and the report. Chat: "bracket ka stress check karo" starts the same flow.

**4.7 Report.** Hoola Print PDF per project: brief, assumptions, inputs, method, mesh / setup, results with plots,
checks, limits, and the review line for safety-critical work.

**4.8 Agent tool.** `eng_desk` (family `engineering`, admitted on engineering words): `new_project`, `add_input`,
`plan`, `run` (returns a price card for heavy runs), `result`, `report`, `export`.

---

## 5. Role packs and phases

| Phase | Roles | Why this order |
|-------|-------|----------------|
| **1** | Engineering Desk base + **CAD/CAM (CAD part)** | Most demand (fabricators, product makers, students), cheap runs, very visible result (3D model + STEP + drawing) |
| **2** | **FEA** (+ CAM toolpaths) | Reuses the CAD model and Gmsh; "will my part break?" is the next question after a part |
| **3** | **CFD** | Reuses CAD + meshing; heaviest compute, so it comes after pricing / caps are proven |
| **4** | **Acoustic** + **Optical** | Light Python engines (pyroomacoustics, RayOptics), quick wins |
| **5** | **ECU / AUTOSAR**, **Spacecraft flight SW**, **Medical device SW** | Mostly Developer Sahayak + a standards pack: MISRA / Power-of-10 / IEC 62304 templates, cppcheck + tests, traceability matrix |
| **6** | **Lithography / layout** (KLayout DRC) + **Industrial IoT architect** (design docs, protocol maps, IEC 62443 zones) | Niche users; mostly scripting + documents |

Each phase ships like every Hoola version: server + tests + console + phone + CI green + HISTORY section.

**Phase 1 detail (first build after her GO):**
1. `engineering/` base: projects, runs, sandbox (clone of `blender3d` safety), price card, caps, desk API
   (`/api/eng/*`), self-check `python -m app.engineering check` (engines installed, sandbox has no network).
2. CAD pack: words / sketch photo / her numbers → CadQuery script → solid → checks (valid solid, volume, bounding box
   vs her dimensions, min wall) → STEP + STL + PNG views + a 2D drawing PDF with dimensions.
3. Hire card "CAD Engineer" live; the other 9 shown under the new group as "Coming soon".
4. Console desk with a 3D viewer; phone desk with images and files.
5. VPS: `pip install cadquery gmsh` (tested in the sandbox first; CadQuery wheels are ~100 MB).

---

## 6. Costs and limits (to confirm with real runs)

- CAD part: seconds of CPU + 1-2 model calls → near zero; in the free daily allowance.
- FEA small part (~50k elements): 1-3 min CPU.
- CFD case (~1M cells): 20-60 min on several cores → needs a price card and probably a bigger server or a separate
  compute box; Phase 3 decides.
- Server sizing: today's VPS shares CPU with the chat; heavy solvers get a separate queue with 1 concurrent job and
  `nice`. If CFD demand grows, a dedicated compute machine (no Hoola secrets on it) is the clean answer.

---

## 7. Never

Claim a design is certified, approved or safe to build without a qualified engineer; sign or stamp drawings; connect to
a live plant, PLC, vehicle CAN bus or medical device; run anything that reaches the network from the sandbox; use
cracked or unlicensed commercial software; reproduce copyrighted standards text; hide AI involvement in a report;
export controlled technology on request (space / defence items under SCOMET / ITAR are refused with a plain note).

---

## 8. Not verified yet (checked during each phase)

CadQuery / OCP wheel install on the VPS Python version; CalculiX and Gmsh versions in Ubuntu's repo; OpenFOAM install
size and run times on the VPS; RayOptics / LightPipes licences at the version used; real CPU cost per run on her server.
