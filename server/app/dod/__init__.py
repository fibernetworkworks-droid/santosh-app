"""HOOLA DOD - the coworker (owner, 28 Nov 2026: "OPENCLAW WORK WITH SEPERATE SECTON NAME HOOLA DOD ( A COWORKER )").

She meets her coworker once (a face from the 200 looks, a name, a voice), then gives it real work - order dinner,
code for hours, write documents, collect data from websites. Each user's work runs on HER OWN OpenClaw Gateway (the
official release, unchanged) in the background; she never sees OpenClaw, only her coworker. Nothing here touches the
Hoola chat, Hoola PC, Hoola Code or the main avatar.

    models.py   - her coworker profile, her tasks, her gateway record
    looks.py    - the 200 looks (served from static/dod/looks)
    gateway.py  - one OpenClaw Gateway per user: container, config, wake / sleep, the /v1/responses stream
    service.py  - a task's life: steps, her notes, her yes, files, stop
    api.py      - /api/dod/*
"""
