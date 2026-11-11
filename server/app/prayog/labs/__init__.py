"""Lab packs: a new set-up's catalogue entry lives in its OWN file, never in the shared catalog.py.

A pack is `app/prayog/labs/<area>.py` exporting `BUILDERS = (fn, ...)`, each returning one LSL lab dict exactly
like the builders in catalog.py (import its helpers: `from ..catalog import B, knob, inst, col, lab, ...`).
Every pack's labs are checked and served with the rest; a broken pack is logged and skipped, never fatal.
"""
