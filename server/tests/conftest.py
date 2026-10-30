import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Fresh database, test-mode WhatsApp that approves instantly, no real API keys."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("WA_DRY_RUN", "true")
    monkeypatch.setenv("DRY_RUN_APPROVAL_SECONDS", "0")
    monkeypatch.setenv("SEND_RATE_PER_SEC", "1000")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("VOICEID_VAD", "false")      # voice-id tests use synthetic tones, which Silero rightly calls "not a voice"
    monkeypatch.setenv("HOOLA_ENRICH", "false")     # no background vision / suggestion calls; tests call enrich.run
    monkeypatch.setenv("VOICE_TOOL_ACK", "false")
    monkeypatch.setenv("VIDEO_EDIT_WORKER", "false")   # tests call videoedit.run_job themselves
    monkeypatch.setenv("OPERATOR_WORKER", "false")     # tests call operator.run_job themselves
    monkeypatch.setenv("CHAT_HEAL_AI", "false")        # v0.158 no model judge of call cards in tests
    monkeypatch.setenv("AGENT_SELF_CHECK", "false")    # v0.78: scripted model tests don't expect the extra check call
    monkeypatch.setenv("NOTEBOOK_PAINT", "false")      # v0.155: Notebook pages are painted by Gemini; tests use the HTML renderer
    monkeypatch.setenv("NOTEBOOK_TTS_MODEL", "gemini-2.5-flash-preview-tts")   # v0.155: tests use the patched older TTS path
    monkeypatch.setenv("AGENT_FIX_SEARCH", "false")
    monkeypatch.setenv("GYAAN_GROUND", "false")      # v0.135: no extra grounding call in scripted model tests
    monkeypatch.setenv("MEMORY_AUTO", "false")       # v0.108: no background fact-picking model calls in scripted tests
    monkeypatch.setenv("SEMANTIC_OFF", "1")          # no 40 s embedding-model download attempt (the sandbox has no HF)
    monkeypatch.setenv("SITE_ART", "false")         # v0.225: no art-direction / critique Opus calls in scripted site tests
    monkeypatch.setenv("SITE_CRITIQUE", "off")
    monkeypatch.setenv("SITE_AI_PHOTOS", "0")       # v0.290: no image-model calls in scripted site tests
    monkeypatch.setenv("SITE_LOOK_SECTIONS", "1")   # v0.290: looks stay hero-only unless a test asks for more
    monkeypatch.setenv("KAAM_WATCH", "false")        # v0.136: job-watch notes only in its own tests
    monkeypatch.setenv("HARD_JUDGE", "false")        # v0.272: no tiny judge model call in tests (the rules still run)
    monkeypatch.setenv("CALL_RECEIPT", "false")      # v0.91: scripted calls don't expect the extra receipt message
    monkeypatch.setenv("BLENDER3D_WORKER", "false")   # v0.141: tests run 3D jobs themselves
    monkeypatch.setenv("BLENDER_LOOK", "false")
    monkeypatch.setenv("MEDIA_FIND", "false")       # v0.136.1: no web look-ups for the exact song / video in tests
    monkeypatch.setenv("PARALLEL_SEARCH", "false")   # v0.91: no real Parallel searches in tests
    monkeypatch.setenv("OPERATOR_PREFLIGHT", "false")  # v0.92: no live site checks (the sandbox has no DNS)
    monkeypatch.setenv("OPERATOR_REACH_FILE", str(tmp_path / "reach.json"))
    monkeypatch.setenv("IFSC_REFRESH", "false")    # no IFSC downloads / online lookups in tests
    monkeypatch.setenv("CYBER_SLEEP_BETWEEN_S", "0")  # v0.137: no politeness sleeps between fake API calls
    monkeypatch.setenv("LOGO_WARM", "false")       # no logo downloads in tests
    monkeypatch.setenv("TV_REFRESH", "false")   # no real TTS calls; tests that need the clips turn it on
    monkeypatch.chdir(tmp_path)   # ignore any local .env
    from app.config import get_settings
    get_settings.cache_clear()
    from app import db
    db.init_db()
    from app.whatsapp import DryRunWhatsApp, set_whatsapp
    wa = DryRunWhatsApp(approval_seconds=0, read_ratio=0.5, reply_ratio=0.1, seed=7)
    set_whatsapp(wa)
    yield {"wa": wa, "settings": get_settings()}
    set_whatsapp(None)
    from app.agent import set_client
    set_client(None)
    get_settings.cache_clear()


SAMPLE = ROOT / "samples" / "leads_sample_TEST_MODE_ONLY.csv"
