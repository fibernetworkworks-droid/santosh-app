---
type: "AEP evidence"
title: "P8 HOOLA AEP 1.0 - the parity audit"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/audit.py
  - repo://server/tests/test_v0600_hoola_aep1.py
---

The 100% parity audit: the matrix verified live (every symbol imports, every test needle greps), the phase checklist with living numbers, and these evidence pages - generated from the tree, never asserted.

Files: `server/app/aep/audit.py` (602 lines)
Suite: `server/tests/test_v0600_hoola_aep1.py` (10 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| the parity matrix verified live | `app.aep.audit.audit_parity` | `test_audit_parity_all_rows_verified` |
| the phase checklist sign-off | `app.aep.audit.phase_checklist` | `test_phase_checklist_signoff` |
| the openwiki analog generated | `app.aep.audit.generate_wiki` | `test_wiki_generation_deterministic` |
| the CLI lanes | `app.aep.audit.main` | `test_audit_cli_lanes` |

