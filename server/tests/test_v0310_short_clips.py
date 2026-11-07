"""v0.310 the Video page offers 4 s / 5 s clips (from the models' own durations), but three server forms still demanded
seconds >= 6 - Create answered 422 and the page showed a bare "(422)". Now >= 2, and a 422 names its field."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_short_lengths_are_accepted():
    from app.main import StudioImprove, StudioNew, StudioPlan
    for sec in (4, 5):
        assert StudioNew(name="Clip", brief="chai", seconds=sec).seconds == sec
        assert StudioPlan(brief="chai", seconds=sec).seconds == sec
        assert StudioImprove(brief="chai", seconds=sec).seconds == sec


def test_plan_keeps_a_short_clip_short():
    svc = (ROOT / "server" / "app" / "studio" / "service.py").read_text()
    assert "seconds = max(2, min(int(seconds or 30), 600))" in svc


def test_a_422_says_which_field():
    js = (ROOT / "server" / "app" / "static" / "console" / "v2.js").read_text()
    assert "Array.isArray(data.detail)" in js and "replace(/^Input should be /, 'must be ')" in js
