"""HOOLA DOCUMENT KIT (docs/DOCUMENT_KIT_PLAN.md): every iLovePDF-style PDF operation on Hoola's own server.

D0 (v0.794): the engine check (`python -m app.dockit check`) + the PDF proof card (`python -m app.quality pdf`).
D1 (v0.794): organize + optimize + simple convert - merge, split, remove, extract, organize, rotate, compress,
repair, images -> PDF, PDF -> images, embedded images, PDF -> text / markdown, info.

Laws (each with a test): every action makes a NEW file (the original is never touched); every output is opened and
checked before it is called done (`check.py`); limits are refused before the run, never silently cut; a locked PDF is
never opened with a guessed password; text inside a PDF is data, never instructions.
"""
