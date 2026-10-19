"""Santosh Browser self-test (run on the VPS):  cd ~/apps/santosh-core && .venv/bin/python -m app.browser_check

Checks every link in the chain and prints where it breaks: settings -> worker reachable -> key accepted ->
Chromium starts -> the model drives a real page -> the chat tool is registered for text and voice."""
from __future__ import annotations

import json
import sys
import time


def main() -> int:
    from .config import get_settings
    from . import browser
    st = get_settings()
    ok = True

    def line(good: bool, what: str, detail: str = "") -> None:
        nonlocal ok
        ok &= good
        print(("OK   " if good else "FAIL ") + what + (f"  ->  {detail}" if detail else ""))

    line(bool(st.browser_worker_url), "BROWSER_WORKER_URL set", st.browser_worker_url or "missing in .env")
    line(bool(st.browser_worker_key), "BROWSER_WORKER_KEY set", "" if st.browser_worker_key else "missing in .env")
    try:
        cfg = browser.llm_config()
        line(True, "model for the browser", f"{cfg['provider']} {cfg.get('model')}")
    except Exception as e:
        line(False, "model for the browser", str(e))
    import httpx
    try:
        r = httpx.get(st.browser_worker_url.rstrip("/") + "/healthz", timeout=10)
        line(r.status_code == 200, "worker reachable", r.text[:200])
    except Exception as e:
        line(False, "worker reachable", f"{type(e).__name__}: {e}  (is pm2 'santosh-browser' online?)")
        return 1
    from .agent.tools import HANDLERS, TOOLS
    line("browse_web" in HANDLERS and any(t["name"] == "browse_web" for t in TOOLS), "browse_web tool in chat")
    try:
        from .voice import VOICE_TOOL_NAMES
        line("browse_web" in VOICE_TOOL_NAMES, "browse_web tool in voice calls")
    except Exception as e:
        line(False, "voice tools", str(e))
    print("\nRunning a real task (open example.com, read the heading)... up to 2 minutes")
    t0 = time.time()
    try:
        res = browser.start("selftest", "Open the page and tell me its main heading text exactly.", "https://example.com", 110)
        sid = res.get("session_id", "")
        while res.get("status") in ("running", "starting") and time.time() - t0 < 170:
            res = browser.get("selftest", sid, wait=30)
        res.pop("screenshot_jpeg_b64", None)
        good = res.get("status") == "done" and "example" in (res.get("summary") or "").lower()
        line(good, f"real browser task ({int(time.time() - t0)} s)", json.dumps(res, ensure_ascii=False)[:600])
    except Exception as e:
        line(False, "real browser task", f"{type(e).__name__}: {e}")
    print("\nOpening real sites (no AI) to see what each one shows this server...")
    sites = ["https://duckduckgo.com/?q=birth+certificate+fees+akola", "https://www.bing.com/search?q=akola+municipal+corporation",
             "https://www.india.gov.in/", "https://www.irctc.co.in/"]
    extra = [a for a in sys.argv[1:] if a.startswith("http")]
    try:
        r = httpx.post(st.browser_worker_url.rstrip("/") + "/probe", json={"urls": (extra or sites)[:6]},
                       headers={"x-worker-key": st.browser_worker_key}, timeout=300).json()
        for it in r.get("results", []):
            if it.get("error"):
                print(f"FAIL {it['url']}  ->  {it['error']}")
            elif it.get("site_blocks_bots"):
                print(f"BLOCKED BY SITE {it['url']}  ->  {it.get('title')!r}: {it.get('text', '')[:160]}")
            else:
                print(f"OK   {it['url']}  ->  {it.get('title')!r} ({it.get('seconds')} s)")
            if it.get("guard_refused"):
                print(f"     Santosh filter refused: {it['guard_refused']}")
        print("browser identity:", (r.get("results") or [{}])[0].get("browser_seen_as"))
    except Exception as e:
        print(f"FAIL site probe  ->  {type(e).__name__}: {e}")
    print("\nALL GOOD" if ok else "\nSee FAIL lines above (and: pm2 logs santosh-browser --lines 60 --nostream)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
