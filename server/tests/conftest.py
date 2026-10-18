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
