"""Kernel packs: new physics for Prayogshala lives in its OWN file, never in the shared kernels.py.

A pack is `app/prayog/packs/<name>.py` exporting any of:
    KERNELS  = {"<kernel name>": <class with PARAMS / init / step / view / measure>}
    FAMILY   = {"<kernel name>": "mech" | "osc_wave" | "optics" | "em" | "circuit" | "thermo" | ...}
    TEXTBOOK = {"<check name>": lambda p: <the textbook value>}
    CALCS    = {"<calc name>": {"label", "unit", "needs", "fn"}}
Its JavaScript twin is `app/static/prayog/packs/<name>.js`, which calls HoolaKernels.register({K, CALCS, TEXTBOOK}).
Both are merged at import / load time, so two people can add physics at once without touching one shared file.
"""
