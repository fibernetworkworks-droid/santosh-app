"""v0.586 SAHI KHARCHA: the long card's --check line prices THE RUN that starts (its asks, k, model),
not the whole 75-run set on Sonnet - her 5-job Haiku try printed 'Rs 4,500-16,500'."""
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]


def test_estimate_scales_by_model():
    from app.quality import longcard as LC
    assert LC.estimate(75, "claude-sonnet-5-5") == (4500, 16500)
    lo, hi = LC.estimate(5, "claude-haiku-5-5")
    assert (lo, hi) == (15, 55)
    assert LC.estimate(1, "claude-opus-5-5") == (120, 440)
    assert LC.estimate(0, "claude-haiku-5-5") == (0, 0)


def _check(*args, model=""):
    env = {"PATH": "/usr/bin:/bin", "QUALITY_MODEL": model} if model else {"PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, "-m", "app.quality", "longcard", "--check", *args], cwd=SERVER,
                       capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_check_prices_the_try_not_the_set():
    out = _check("--k", "1", "--limit", "5", "--label", "try", model="haiku")
    assert "5 of 25 asks, 5 runs at k=1 on claude-haiku-5-5" in out
    assert "Rs 15-55" in out and "4,500" not in out


def test_vps_ops_passes_the_run_args_to_check():
    wf = (SERVER.parent / ".github/workflows/vps-ops.yml").read_text()
    assert "longcard --check $LC_ARGS" in wf


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.686.0"
