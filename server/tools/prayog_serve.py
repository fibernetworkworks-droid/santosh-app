"""Serve only Prayogshala (catalogue + static lab pages) for the headless walk-through, locally and on CI.
Run from server/:  python -m uvicorn tools.prayog_serve:app --port 8791"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.prayog.api import make_router  # noqa: E402

app = FastAPI()
app.include_router(make_router())
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "app" / "static")), name="static")
