"""HOOLA PROMPTING (docs/HOOLA_PROMPTING_PLAN.md). A prompt inside Hoola is a structured BRIEF, never loose text:
her facts are locked, a guess is labelled a guess, nothing is rewritten silently and no magic phrase is ever added.

anatomy.py  what a complete ask has, per section (web / image / script)
brief.py    her words -> a brief (code first, one small model call, code checks the model), the Prompt Score
dialect.py  a brief -> the exact wording each Hoola engine wants
context.py  what Hoola already knows about her business (brand kit, her memory page)
recipes.py  starter recipes with blanks
store.py    her saved prompts
api.py      /api/prompting/*
"""
