"""Self-check on the VPS: makes one real sample of each new Notebook Studio piece with the real models and saves them so
the owner can look at them (and we can compare models).

    cd ~/apps/santosh-core && .venv/bin/python -m app.notebook.paintcheck [out_dir]

Writes slide-english.jpg, slide-hindi.jpg, infographic.jpg, frame.jpg and dialogue.mp3 (or .wav) and prints, for each,
the model that answered, the seconds it took and the text read-back score (1.0 = every planned word is on the page)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from . import media, paint, render

SLIDE = {"layout": "stats", "kicker": "FNW Q3 2026", "title": "Q3 key numbers",
         "stats": [{"value": "₹42L", "label": "Revenue (up 18%)"}, {"value": "22", "label": "Syrotech OLTs running"},
                   {"value": "4", "label": "SSAs: Akola, Pune, Nashik, Goa"}],
         "visual": "fiber optic network map of Maharashtra and Goa with glowing connections"}
SLIDE_HI = {"layout": "bullets", "title": "अकोला में FTTH का विस्तार",
            "bullets": ["फॉल्ट ठीक होने का समय 6 से घटकर 4 घंटे", "नए कनेक्शन में 31% बढ़त", "गोवा लॉन्च समय पर हुआ"],
            "visual": "a field engineer connecting fiber to a village home"}
INFO = {"title": "FNW Q3 at a glance", "subtitle": "Akola, Pune, Nashik, Goa", "hero": {"value": "₹42 lakh", "label": "Q3 revenue"},
        "stats": [{"value": "18%", "label": "growth"}, {"value": "22", "label": "OLTs"}],
        "sections": [{"heading": "Faster service", "text": "MTTR down from 6 to 4 hours", "points": ["80% of tickets closed on WhatsApp"]},
                     {"heading": "New region", "text": "Goa SSA launched", "points": ["September 2026"]}],
        "steps": ["Lead", "Survey", "Connection", "Billing"], "takeaway": "Fiber to every home, internet to every village."}
SCENE = {"headline": "FNW starts in Goa", "points": ["September 2026"],
         "visual": "fiber cables reaching a Goan coastal village at sunset",
         "narration": "In September 2026 FNW started work in the Goa SSA, and more than a hundred homes joined in the first month."}
DIALOGUE = ["Ravi [warm, upbeat]: Hello everyone! <short pause> Today we are talking about FNW's Q3.",
            "Priya [curious]: Right, Ravi, what is the biggest news? |right|",
            "Ravi [impressed]: Revenue reached 42 lakh, up 18 percent. <laugh>",
            "Priya [thoughtful]: And work in Goa started too, right on time."]


def _one(name: str, out: Path, fn) -> None:
    t = time.time()
    try:
        r = fn()
        print(f"{name:18} ok   {time.time() - t:5.1f}s  {r}")
    except Exception as e:
        print(f"{name:18} FAIL {time.time() - t:5.1f}s  {str(e)[:200]}")


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if not paint.enabled():
        print("Painting is off (no GEMINI_API_KEY or NOTEBOOK_PAINT=false).")
        return
    st = render.style_of("classic")
    refs: list[bytes] = []

    def slide(sl, lang, fname):
        def run():
            r = paint.paint_checked(lambda fix: paint.slide_brief(sl, 2, 10, "FNW Q3 review", st["img"], "", lang, "BSNL officers",
                                                                  bool(refs), fix), "16:9", "page", refs)
            img = paint.finish(r["img"], 1920, 1080)
            (out / fname).write_bytes(img)
            if not refs:
                refs.append(img)
            return f"model={r['model']} tries={r['tries']} text={r['check']['score']}"
        return run
    _one("slide (English)", out, slide(SLIDE, "en", "slide-english.jpg"))
    _one("slide (Hindi)", out, slide(SLIDE_HI, "hi", "slide-hindi.jpg"))

    def info():
        r = paint.paint_checked(lambda fix: paint.info_brief(INFO, "portrait", st["img"], "", "en", fix), "9:16", "page", None)
        (out / "infographic.jpg").write_bytes(paint.finish(r["img"], 1152, 2048, quality=92))
        return f"model={r['model']} tries={r['tries']} text={r['check']['score']}"
    _one("infographic", out, info)

    def frame():
        r = paint.paint_checked(lambda fix: paint.frame_brief(SCENE, 3, 9, "The FNW story", render.style_of("watercolor")["img"],
                                                              "", "en", False, fix), "16:9", "frame", None)
        (out / "frame.jpg").write_bytes(paint.finish(r["img"], 1600, 900))
        return f"model={r['model']} tries={r['tries']} text={r['check']['score']}"
    _one("video frame", out, frame)

    def voice():
        pcm = media.speak_dialogue(DIALOGUE, "English (clear, simple English)")
        data, ext = media.encode_mp3(pcm)
        (out / f"dialogue{ext}").write_bytes(data)
        used = "older TTS (fallback)" if media._NEW_TTS_OFF["until"] > time.time() else "gemini-3.8-flash-tts"
        return f"{media.seconds_of(pcm):.1f}s of audio via {used}"
    _one("two-host audio", out, voice)
    print(f"\nFiles in {out.resolve()}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/notebook/_check"))
