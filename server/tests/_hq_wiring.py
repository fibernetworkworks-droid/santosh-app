"""v0.999.30 WIRED: one check every studio's browser test runs - the chat's quality tier + her credits are drawn UNDER that
studio's typing box, from the server's REAL routes (GET / PUT /api/model/tier, GET /api/credits), and a pick reaches the
tier the server uses for her work. Only two things are faked: tiers are 'offered' (no OpenRouter key in tests) and her
wallet has paid credits (a real top-up granted through the wallet)."""
from __future__ import annotations

import tempfile

_JS_UNDER = """(box) => {
  const b = document.querySelector(box); if (!b || !b.offsetParent) return null;
  const r = b.getBoundingClientRect();
  const btns = [...document.querySelectorAll('.hq-btn')].filter(x => x.offsetParent);
  let best = null, gap = 1e9;
  for (const x of btns) { const q = x.getBoundingClientRect(); const d = q.top - r.bottom;
    if (d >= -4 && d < gap && q.left < r.right + 4 && q.right > r.left - 4) { gap = d; best = x; } }
  if (!best) return null;
  const row = best.closest('[data-hoola-quality]');
  return {tier: best.textContent.trim(), credits: row?.querySelector('.hq-cr')?.textContent.trim() || '', gap: Math.round(gap)};
}"""


def real_tiers(monkeypatch, tier: str = "high") -> str:
    """Turn tiers on for the test server's account with paid credits; returns the account."""
    monkeypatch.setenv("CREDITS_ON", "true")
    monkeypatch.setenv("MODEL_TIER_DIR", tempfile.mkdtemp(prefix="hq-tier-"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app import tiers
    monkeypatch.setattr(tiers, "offered", lambda: (True, ""))
    from app.credits import plans as P, wallet as W
    t = get_settings().tenant_id
    W.ensure_table()
    W.grant(t, "topup", next(iter(P.TOPUPS)), "IN", "wiring-test")
    tiers.set_tier(t, tier)
    return t


def quality_under(pg, box: str, want: str = "High", timeout: int = 15000) -> dict:
    """The quality button + credits sit right under `box` (the typing box), showing her tier and her credits."""
    try:
        pg.wait_for_function(f"() => ({_JS_UNDER})({box!r})", timeout=timeout)
    except Exception:   # say what IS there, so a failure names the gap
        seen = pg.evaluate("""(box) => { const b = document.querySelector(box); const r = b && b.getBoundingClientRect();
          return {box: r ? [r.left, r.top, r.right, r.bottom].map(Math.round) : null,
                  hosts: document.querySelectorAll('[data-hoola-quality]').length, mounted: document.querySelectorAll('[data-hq]').length,
                  btns: [...document.querySelectorAll('.hq-btn')].map(x => { const q = x.getBoundingClientRect(); return [x.textContent, !!x.offsetParent, Math.round(q.left), Math.round(q.top)]; })}; }""", box)
        raise AssertionError(f"no quality button under {box}: {seen}")
    got = pg.evaluate(_JS_UNDER, box)
    assert got and got["tier"] == want, (box, got)
    assert got["credits"].endswith("credits") and got["gap"] < 120, (box, got)
    return got


def pick_low(pg, box: str, tenant: str) -> None:
    """Pick Low from the button under `box`: the real PUT lands and the server's tier for her work is now low."""
    from app import tiers
    pg.evaluate("""(box) => { const r = document.querySelector(box).getBoundingClientRect();
      const b = [...document.querySelectorAll('.hq-btn')].filter(x => x.offsetParent)
        .sort((a, c) => Math.abs(a.getBoundingClientRect().top - r.bottom) - Math.abs(c.getBoundingClientRect().top - r.bottom))[0];
      b.click(); }""", box)
    pg.wait_for_selector(".hq-menu.on")
    pg.locator(".hq-menu .hq-mi", has_text="Low").click()
    pg.wait_for_function("() => [...document.querySelectorAll('.hq-btn')].some(b => b.textContent.trim() === 'Low')")
    assert tiers.chosen(tenant) == "low"
