# Software Architecture, Engineering & Core Systems - plan (owner: "Principal Software Architect ---- START THE WORK", 1 Nov 2026)

Ten AI employees in ONE Hub group (`employee/hire.py` `SW_GROUP`). Code they write goes to HER GitHub through the
Developer Sahayak's draft PR + CI path; merging, deploying and posting are always her tap; heavy builds run in HER CI,
never on her PC and never as her code on Hoola's server.

## Where work runs (honest limits)
| Where | Good for |
|---|---|
| Hoola's server (today) | reading repos, designs, diagrams, documents, reviews, query plans from her DB |
| Small locked boxes on the VPS (per tool, like the CAD box) | GnuCOBOL, clang, a parser generator, shader check, TLA+ checker - small, no network, missing tool = skipped |
| Her own GitHub CI (works today) | kernel builds, QEMU, Docker, benchmarks |
| Never | her PC unless she says so; real GPU / DirectX / mainframe / trading-grade timing |

## The ten roles
| # | Role (key) | Delivers | Runs on | Status |
|---|---|---|---|---|
| 1 | Principal Software Architect (`architect`) | design doc, C4 / sequence / deployment diagrams, ADRs, capacity in code, risks, roadmap, PDF; PRs vs the design | server | **LIVE v0.410** |
| 10 | Legacy Code Refactoring Specialist (`refactor_eng`) | hotspot map, tests first, small refactor PRs green on CI | server + CI | Phase 2 |
| 5 | Database Engine Developer (`dbengine_dev`) | plans + indexes from her DB (read only), engine code, CI benchmarks | server + DB + CI | Phase 3 |
| 6 | Distributed Systems Engineer (`distsys_eng`) | consensus / retries / failover design, failure tests, TLA+ | box + CI | Phase 3 |
| 9 | Mainframe Modernization Architect (`mainframe_arch`) | COBOL inventory, dependency map, migration, side-by-side tests | GnuCOBOL box | Phase 4 |
| 2 | Compiler Construction Engineer (`compiler_eng`) | grammar, parser, interpreter / compiler, golden tests | box + CI | Phase 4 |
| 8 | Backend Systems Engineer, Low Latency (`lowlatency_eng`) | lock-free code, microbenchmarks ("relative only"), p99 analysis | CI | Phase 5 |
| 4 | Graphics Engine Programmer (`graphics_eng`) | renderer + shader code, SPIR-V validation, CPU renders | box + CI | Phase 5 |
| 7 | Virtualization / Hypervisor Engineer (`hypervisor_eng`) | container / VM configs, security profiles, runtime tests | CI | Phase 5 |
| 3 | Kernel / OS Developer (`kernel_dev`) | patches, drivers, crash-log diagnosis, QEMU boot tests | CI | Phase 5 |

## Phase 1 (v0.410) - the Principal Software Architect
1. Brief (+ her repo, read only through her own token: README, ADRs, manifests, compose / k8s / Terraform, OpenAPI,
   workflows, entry points - capped 24 files / 60k chars) -> Opus writes one structured design.
2. Capacity is arithmetic in `archdesk/capacity.py`. No users-a-day = no sheet. A number is HERS only when she typed it
   or it is in her brief; everything else is shown "assumed - please confirm".
3. Diagrams: vendored Mermaid 11.4.1 in the server Chromium, strict mode, every non-local request aborted, click / links /
   HTML / init refused before drawing; a broken diagram goes back to the model ONCE with Mermaid's error.
4. Markdown + printed PDF; her approve or "next version" (her change words + the previous design).
5. PR review against the APPROVED design: verdict fits / drifts / breaks + findings citing ADRs; a DRAFT until her tap
   posts ONE comment (never approve / merge). 24/7 watch of new PRs (per design, her switch): draft notes only.
6. Caps: 6 designs a day, 10 PR reviews a day. Gate: new work while hired and not paused; old designs readable while paused.

## Next
- Phase 2: Legacy Refactoring (reuse devsahayak loop + tests-first + small PRs).
- Shared: one desk list instead of three hand-written ones (v2.js / employees.js / employees_screen.dart).
