"""Self-check on the VPS: makes one real sample of each new Notebook Studio piece with the real models and saves them so
the owner can look at them (and we can compare models).

    cd ~/apps/santosh-core && .venv/bin/python -m app.notebook.paintcheck [out_dir]

Writes slide-hinglish.jpg, slide-hindi.jpg, infographic.jpg, frame.jpg and dialogue.mp3 (or .wav) and prints, for each,
the model that answered, the seconds it took and the text read-back score (1.0 = every planned word is on the page)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from . import media, paint, render

SLIDE = {"layout": "stats", "kicker": "FNW Q3 2026", "title": "Q3 ke mukhya aankde",
         "stats": [{"value": "₹42L", "label": "Revenue (18% upar)"}, {"value": "22", "label": "Syrotech OLTs chal rahe"},
                   {"value": "4", "label": "SSAs: Akola, Pune, Nashik, Goa"}],
         "visual": "fiber optic network map of Maharashtra and Goa with glowing connections"}
SLIDE_HI = {"layout": "bullets", "title": "अकोला में FTTH का विस्तार",
            "bullets": ["फॉल्ट ठीक होने का समय 6 से घटकर 4 घंटे", "नए कनेक्शन में 31% बढ़त", "गोवा लॉन्च समय पर हुआ"],
            "visual": "a field engineer connecting fiber to a village home"}
INFO = {"title": "FNW Q3 ek nazar mein", "subtitle": "Akola, Pune, Nashik, Goa", "hero": {"value": "₹42 lakh", "label": "Q3 revenue"},
        "stats": [{"value": "18%", "label": "growth"}, {"value": "22", "label": "OLTs"}],
        "sections": [{"heading": "Tez service", "text": "MTTR 6 se 4 ghante", "points": ["WhatsApp se 80% tickets band"]},
                     {"heading": "Naya ilaaka", "text": "Goa SSA shuru", "points": ["September 2026"]}],
        "steps": ["Lead", "Survey", "Connection", "Billing"], "takeaway": "Har ghar tak fiber, har gaon tak internet."}
SCENE = {"headline": "Goa mein FNW ki shuruaat", "points": ["September 2026"],
         "visual": "fiber cables reaching a Goan coastal village at sunset",
         "narration": "September 2026 mein FNW ne Goa SSA mein kaam shuru kiya, aur pehle mahine mein hi sau se zyada ghar jude."}
DIALOGUE = ["Ravi [warm, upbeat]: Namaste dosto! <short pause> Aaj baat karenge FNW ke Q3 ki.",
            "Priya [curious]: Haan Ravi, sabse badi khabar kya hai? |haan|",
            "Ravi [impressed]: Revenue 42 lakh pahunch gaya, 18 percent zyada! <laugh>",
            "Priya [thoughtful]: Aur Goa mein bhi kaam shuru ho gaya, wo bhi samay par."]


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
    _one("slide (Hinglish)", out, slide(SLIDE, "hinglish", "slide-hinglish.jpg"))
    _one("slide (Hindi)", out, slide(SLIDE_HI, "hi", "slide-hindi.jpg"))

    def info():
        r = paint.paint_checked(lambda fix: paint.info_brief(INFO, "portrait", st["img"], "", "hinglish", fix), "9:16", "page", None)
        (out / "infographic.jpg").write_bytes(paint.finish(r["img"], 1152, 2048, quality=92))
        return f"model={r['model']} tries={r['tries']} text={r['check']['score']}"
    _one("infographic", out, info)

    def frame():
        r = paint.paint_checked(lambda fix: paint.frame_brief(SCENE, 3, 9, "FNW ki kahani", render.style_of("watercolor")["img"],
                                                              "", "hinglish", False, fix), "16:9", "frame", None)
        (out / "frame.jpg").write_bytes(paint.finish(r["img"], 1600, 900))
        return f"model={r['model']} tries={r['tries']} text={r['check']['score']}"
    _one("video frame", out, frame)

    def voice():
        pcm = media.speak_dialogue(DIALOGUE, "Hinglish (Hindi + English, Indian accent)")
        data, ext = media.encode_mp3(pcm)
        (out / f"dialogue{ext}").write_bytes(data)
        used = "older TTS (fallback)" if media._NEW_TTS_OFF["until"] > time.time() else "gemini-3.8-flash-tts"
        return f"{media.seconds_of(pcm):.1f}s of audio via {used}"
    _one("two-host audio", out, voice)
    print(f"\nFiles in {out.resolve()}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/notebook/_check"))
