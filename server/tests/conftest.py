import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _pg_database(monkeypatch):
    """A fresh Postgres database for one test when HOOLA_TEST_PG is set (e.g.
    postgresql+psycopg://postgres@/?host=/var/tmp/hpg&port=55432); dropped afterwards."""
    base = os.environ.get("HOOLA_TEST_PG", "").strip()
    if not base:
        return ""
    import uuid

    import psycopg
    from sqlalchemy.engine import make_url
    u = make_url(base)
    name = "hoola_t_" + uuid.uuid4().hex[:12]
    q = dict(u.query)
    with psycopg.connect(dbname="postgres", user=u.username or "postgres", password=u.password, host=q.get("host") or u.host,
                         port=int(q.get("port") or u.port or 5432), autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{name}"')
    monkeypatch.setenv("DATABASE_URL", u.set(database=name).render_as_string(hide_password=False))
    return name


def _drop_pg(name):
    from sqlalchemy.engine import make_url

    import psycopg
    from app import db
    if db._engine is not None:
        db._engine.dispose()
    u = make_url(os.environ["HOOLA_TEST_PG"])
    q = dict(u.query)
    try:
        with psycopg.connect(dbname="postgres", user=u.username or "postgres", password=u.password, host=q.get("host") or u.host,
                             port=int(q.get("port") or u.port or 5432), autocommit=True) as c:
            c.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    except Exception:                                   # noqa: BLE001 - a leftover test database is harmless
        pass


@pytest.fixture(autouse=True)
def _full_voice_menu(monkeypatch):
    """v0.627 production declares the small call menu; the older suites (with or without `env`) pin the full one.
    test_v0627_chhota_menu switches the small one on for itself."""
    from app.config import get_settings
    monkeypatch.setenv("VOICE_LEAN_TOOLS", "false")
    monkeypatch.setenv("SITE_FULL_LOOKS", "false")    # v0.649 older site suites pin page-top looks; test_v0649 checks the whole site
    monkeypatch.setenv("VOICE_BRAIN", "false")         # v0.630 older call suites pin Gemini as the brain; test_v0630 turns it on
    monkeypatch.setenv("CLAUDE_ONE_MODEL", "")        # v0.631 older suites pin each part's own model; test_v0631 checks the lock
    monkeypatch.setenv("CHAT_SIMPLE_MODEL", "")       # v0.630 older chat suites pin the chat model; test_v0630 checks Haiku
    monkeypatch.setenv("CHAT_ALONE", "false")         # v0.714 older suites pin "the chat she is in"; test_v0714 turns it on
    monkeypatch.setenv("HOOLA_LANGUAGE", "auto")      # v0.728 older suites pin Hinglish text; test_v0728 checks English
    monkeypatch.setenv("CHAT_ANSWER_ONLY", "false")   # parity Phase 5: older suites pin the stapled notes; test_parity5 checks on
    monkeypatch.setenv("CHAT_PLAIN_LOOP", "false")    # parity Phase 5b: older suites pin the after-answer checks; test_parity5b_plain_loop checks on
    monkeypatch.setenv("CHAT_WORK_IN_TURN", "false")  # PARITY Phase 4: older suites pin background crews / research + the 900 s turn; test_parity_p4 checks in-turn
    monkeypatch.setenv("QUICK_LANE", "true")          # v0.724 older suites pin the quick lane; test_v0724 checks it is off
    monkeypatch.setenv("CHAT_CORE_TOOLS", "false")    # Parity Phase 3: older suites pin the core families + old result text; test_v0733_clean_tools checks the core set
    monkeypatch.setenv("CHAT_APPROVAL_WORDS", "true") # v0.724 older suites pin "haan" approving a card; test_v0724 checks off
    monkeypatch.setenv("CHAT_ONE_MODEL", "false")      # v0.732 older suites pin the brain fallbacks; test_v0732_ek_model checks one model
    monkeypatch.setenv("CHAT_FILES_BY_CODE", "false")  # v0.738 older suites pin pylab keeping only png / csv / xlsx files
    monkeypatch.setenv("CHAT_EVERY_MESSAGE", "false")  # v0.738 older suites pin the research-plan gate + canned stop line; test_v0738 checks every message reaches the model
    monkeypatch.setenv("ARCHITECT_OPUS", "true")       # v0.735 older suites pin the architect on Opus; test_v0735_all_glm checks GLM
    monkeypatch.setenv("CLAUDE_ALL_GLM_FALLBACK", "true")  # v0.735 older suites pin the Claude fallback at the SDK door
    monkeypatch.setenv("GLM_IMAGES", "false")          # v0.735 older suites pin pictures -> Claude (non-NVIDIA GLM)
    monkeypatch.setenv("GLM_PDF", "false")             # v0.735 older suites pin PDFs -> Claude
    monkeypatch.setenv("CHAT_CONTEXT_LIMIT_CLAUDE", "200000")   # v0.724 older gauge suites pin the 200k window
    monkeypatch.setenv("CHAT_CONTEXT_LIMIT_GLM", "200000")
    monkeypatch.setenv("CHAT_ONE_MEMORY", "false")    # parity Phase 7: older suites pin the per-turn memory blocks; test_parity_p7 checks one memory
    monkeypatch.setenv("CHAT_SMALL_PROMPT", "false")  # parity Phase 2: older suites pin the long per-turn prompt; test_parity_p2 checks the small one
    monkeypatch.setenv("CHAT_CONTEXT_MAX_TOKENS_GLM", "40000")  # v0.707 pin; test_v0724 checks the 1M / no-cap defaults
    monkeypatch.setenv("CHAT_THINKING_ADAPTIVE", "false")  # parity Phase 4: older suites pin thinking only for long / hard turns; test_parity_p4_thinking checks adaptive
    monkeypatch.setenv("CHAT_ARTIFACT_DIRECT", "false")  # parity Phase 6: older suites pin the builder-only pages line; test_parity6 turns it on
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Fresh database, test-mode WhatsApp that approves instantly, no real API keys."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    pg_db = _pg_database(monkeypatch)                  # v0.390 PAKKI NEEV: HOOLA_TEST_PG=<url> runs the suite on Postgres
    monkeypatch.setenv("WA_DRY_RUN", "true")
    monkeypatch.setenv("DRY_RUN_APPROVAL_SECONDS", "0")
    monkeypatch.setenv("SEND_RATE_PER_SEC", "1000")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("VOICEID_VAD", "false")      # voice-id tests use synthetic tones, which Silero rightly calls "not a voice"
    monkeypatch.setenv("HOOLA_ENRICH", "false")     # no background vision / suggestion calls; tests call enrich.run
    monkeypatch.setenv("SITE_LOOK_FIX", "false")    # v0.606 the canned site AI writes eyebrows; old build tests keep their rounds
    monkeypatch.setenv("VOICE_TOOL_ACK", "false")
    monkeypatch.setenv("VIDEO_EDIT_WORKER", "false")   # tests call videoedit.run_job themselves
    monkeypatch.setenv("OPERATOR_WORKER", "false")     # tests call operator.run_job themselves
    monkeypatch.setenv("GOAL_VERIFY_LINKS", "false")   # v0.443 the done=verified gate never reaches the network in tests
    monkeypatch.setenv("CHAT_HEAL_AI", "false")        # v0.158 no model judge of call cards in tests
    monkeypatch.setenv("AGENT_SELF_CHECK", "false")    # v0.78: scripted model tests don't expect the extra check call
    monkeypatch.setenv("NOTEBOOK_PAINT", "false")      # v0.155: Notebook pages are painted by Gemini; tests use the HTML renderer
    monkeypatch.setenv("NOTEBOOK_TTS_MODEL", "gemini-2.5-flash-preview-tts")   # v0.155: tests use the patched older TTS path
    monkeypatch.setenv("AGENT_FIX_SEARCH", "false")
    monkeypatch.setenv("GYAAN_GROUND", "false")      # v0.135: no extra grounding call in scripted model tests
    monkeypatch.setenv("VOICE_OPENAI_ENABLED", "true")   # v0.622 production is Gemini-only; the OpenAI suites still test that engine
    monkeypatch.setenv("VOICE_BRAIN", "false")       # v0.630 see _full_voice_menu
    monkeypatch.setenv("CHAT_SIMPLE_MODEL", "")
    monkeypatch.setenv("CLAUDE_ONE_MODEL", "")
    monkeypatch.setenv("VOICE_LEAN_TOOLS", "false")  # v0.627 production declares the small menu; older suites pin the full one (test_v0627 checks the small one)
    monkeypatch.setenv("VOICE_PARK", "false")        # v0.617 older call suites expect a live Gemini session; test_v0617 turns it on
    monkeypatch.setenv("PUSH_QUIET", "0-0")         # wave 13: no night-quiet behaviour by the wall clock in old suites (test_v0686 sets its own)
    monkeypatch.setenv("MEMORY_AUTO", "false")       # v0.108: no background fact-picking model calls in scripted tests
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    monkeypatch.setenv("CONNECT_CLEAN", "false")     # v0.303: older suites count the full catalogue; test_v0303 covers clean          # no 40 s embedding-model download attempt (the sandbox has no HF)
    monkeypatch.setenv("SITE_ART", "false")         # v0.225: no art-direction / critique Opus calls in scripted site tests
    monkeypatch.setenv("SITE_CRITIQUE", "off")
    monkeypatch.setenv("SITE_KIT", "false")         # v0.330: no design-kit Opus call in scripted site tests (its own suite turns it on)
    monkeypatch.setenv("SITE_JOURNEYS", "false")    # v0.400: visitor journeys open a browser per version; their own suite turns them on
    monkeypatch.setenv("DOC_ART", "false")          # v0.313: no Opus art direction for PDFs in tests (router picks)
    monkeypatch.setenv("DOC_REVIEW", "false")       # v0.313: no Opus page review in tests (its own tests fake it)
    monkeypatch.setenv("SOCIAL_AI", "false")        # v0.353: no Opus calendar call in tests (its own tests fake it)
    monkeypatch.setenv("SEO_AI", "false")           # v0.317: no Opus roadmap call in tests (its own tests fake it)
    monkeypatch.setenv("SITE_AI_PHOTOS", "0")       # v0.292: no image-model calls in scripted site tests
    monkeypatch.setenv("SITE_LOOK_SECTIONS", "1")   # v0.292: looks stay hero-only unless a test asks for more
    monkeypatch.setenv("KAAM_WATCH", "false")        # v0.136: job-watch notes only in its own tests
    monkeypatch.setenv("CODER_ENABLED", "false")     # v0.473: coder memory writes only in its own tests
    monkeypatch.setenv("HARD_JUDGE", "false")        # v0.272: no tiny judge model call in tests (the rules still run)
    monkeypatch.setenv("HARD_CHECK", "false")        # v0.436: no reviewer call in scripted turns (its own tests switch it on)
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
    if pg_db:
        _drop_pg(pg_db)
    set_whatsapp(None)
    from app.agent import set_client
    set_client(None)
    get_settings.cache_clear()


SAMPLE = ROOT / "samples" / "leads_sample_TEST_MODE_ONLY.csv"
