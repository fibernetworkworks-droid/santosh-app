"""WEB CLONE - point at a website, get a clean Next.js rebuild with its endpoints documented.

Three stages: capture (headless Chromium + guarded asset fetches) -> endpoints (the appcheck
static scanner over the bundle) -> assemble (the Next.js app-router project). The tool surface
lives in agent/webclone_tools.py.
"""
