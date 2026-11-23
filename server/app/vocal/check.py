"""v0.999.167 VOCAL CHECK - is every Hoola Vocal tool really wired to its engine, end to end?

Each tool is driven through the SAME server function its button uses (service.tts, dialogue, sfx_text, change, cleanup,
hear, design_preview, dub_start ...), on a throwaway account `__vocalcheck__` that is wiped at the end, with the smallest
real request the engine accepts. A tool is LIVE only when real sound (or real text) came back and was read as such; the
engine's own words are printed when it refuses. Keys are never printed - only whether each is set.

    python -m app.vocal.check            # free + tiny calls (about a cent of engine cost in all)
    python -m app.vocal.check --paid     # also voice design and both kinds of dubbing (a few cents, a few minutes)
    python -m app.vocal.check --json

Results: LIVE (worked), DEAD (the engine or the code refused: the reason follows), NOT CONNECTED (its key or program is
not on this server, so the page says so too), NOT CHECKED (needs something a check cannot give, e.g. a real person's
spoken consent), SKIPPED (a paid check without --paid).
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Any, Callable

T = "__vocalcheck__"
STEP_S = 240          # a step that takes longer is cut and reported DEAD


def _tone(seconds: float = 1.5, rate: int = 24000) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(n)))
    return b.getvalue()


def _sound_ok(data: bytes) -> str:
    """What the bytes really are: 'WAV 1.4 s', 'MP3 31 KB' ... or '' when they are not sound."""
    if not data or len(data) < 200:
        return ""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        try:
            with wave.open(io.BytesIO(data)) as w:
                s = w.getnframes() / float(w.getframerate() or 1)
            return f"WAV {s:.1f} s" if s > 0.05 else ""
        except Exception:   # noqa: BLE001
            return ""
    if data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return f"MP3 {len(data) // 1024} KB"
    if data[:4] == b"fLaC":
        return f"FLAC {len(data) // 1024} KB"
    if data[:4] == b"OggS":
        return f"OGG {len(data) // 1024} KB"
    if data[4:8] == b"ftyp":
        return f"MP4 {len(data) // 1024} KB"
    return ""


class Check:
    def __init__(self, paid: bool = False):
        from . import service as V
        self.V = V
        self.paid = paid
        self.rows: list[dict[str, Any]] = []
        self.gem_voice = ""
        self.el_voice = ""
        self.made: list[str] = []          # history ids made here (their files)

    # ------------------------------------------------------------------ helpers
    def row(self, tool: str, engine: str, result: str, detail: str, secs: float = 0.0) -> None:
        self.rows.append({"tool": tool, "engine": engine, "result": result, "detail": detail[:300], "seconds": round(secs, 1)})

    def run(self, tool: str, engine: str, fn: Callable[[], Any], need: Callable[[], str] | None = None, paid: bool = False) -> Any:
        why = need() if need else ""
        if why:
            self.row(tool, engine, "NOT CONNECTED", why)
            return None
        if paid and not self.paid:
            self.row(tool, engine, "SKIPPED", "a paid check: run with --paid")
            return None
        t0 = time.time()
        try:
            out = fn()
            if asyncio.iscoroutine(out):
                out = asyncio.run(asyncio.wait_for(out, STEP_S))
            ok, detail = out if isinstance(out, tuple) else (True, str(out))
            self.row(tool, engine, "LIVE" if ok else "DEAD", detail, time.time() - t0)
            return out
        except Exception as e:   # noqa: BLE001
            msg = str(e) or e.__class__.__name__
            self.row(tool, engine, "DEAD", f"{e.__class__.__name__}: {msg}", time.time() - t0)
            return None

    def file_of(self, hid: str) -> bytes:
        p, _ = self.V.audio_file(T, hid)
        return Path(p).read_bytes()

    def judge_row(self, r: dict[str, Any]) -> tuple[bool, str]:
        """A made row: its file read back and named by its bytes."""
        items = r.get("items") or [r]
        out = []
        for it in items:
            hid = str(it.get("id") or "")
            self.made.append(hid)
            kind = _sound_ok(self.file_of(hid))
            if not kind:
                return False, f"{hid}: the file is not sound"
            out.append(kind)
        return True, ", ".join(out) + (f" · {r.get('voice_name')}" if r.get("voice_name") else "")

    # ------------------------------------------------------------------ the checks
    def go(self) -> list[dict[str, Any]]:
        V = self.V
        from . import eleven as EL
        from . import engines as EN
        from . import gvoice as GV
        from ..audedit import ops
        from ..config import get_settings
        from ..interactive import lab
        s = get_settings()
        gem = lambda: "" if EN.gemini_ready() else "GEMINI_API_KEY is not set on this server"          # noqa: E731
        ele = lambda: "" if EL.ready() else "ELEVENLABS_API_KEY is not set on this server"             # noqa: E731
        ffm = lambda: "" if ops.ffmpeg_ok() else "ffmpeg is not installed"                              # noqa: E731

        # keys and programs (names only)
        for name, on in (("GEMINI_API_KEY", bool(s.gemini_api_key)), ("ELEVENLABS_API_KEY", bool(EL.key())),
                         ("GPU voice lab", bool(lab.configured())), ("ffmpeg", bool(ops.ffmpeg_ok()))):
            self.row(f"Setup: {name}", "-", "LIVE" if on else "NOT CONNECTED", "set" if on else "missing")

        # ---- voice lists
        def gem_catalog():
            g = GV.catalog()
            b = V.builtin()
            if b:
                self.gem_voice = next((v["id"] for v in b if v["id"].startswith("hv_")), b[0]["id"])
            return bool(b), f"{len(b)} built-in voices; Google's extended list answered {len(g)}"
        self.run("Voice library (Standard voices)", "Gemini", gem_catalog, gem)

        def el_catalog():
            e = EL.voices()
            if e:
                self.el_voice = "ev_" + e[0]["id"]
            return bool(e), f"{len(e)} premium voices on the account"
        self.run("Voice library (Premium voices)", "ElevenLabs", el_catalog, ele)

        def el_account():
            r = EL._call("GET", "/v1/user/subscription").json()
            used, cap = r.get("character_count"), r.get("character_limit")
            return True, f"plan {r.get('tier') or '?'} · {used} of {cap} characters used this period"
        self.run("ElevenLabs account", "ElevenLabs", el_account, ele)

        def shared():
            r = V.shared_library(q="calm")
            n = len(r.get("voices") or [])
            return n > 0, f"{n} shared voices for 'calm'" + (f" · {r.get('why')}" if r.get("why") else "")
        self.run("Voice library (shared, Add to my voices)", "ElevenLabs", shared, ele)

        # ---- speech
        self.run("Speech (Standard voice)", "Gemini",
                 lambda: self._tts(self.gem_voice, "Hello, this is a short check from Hoola."),
                 lambda: gem() or ("" if self.gem_voice else "no Standard voice was listed"))
        self.run("Speech (Premium voice)", "ElevenLabs",
                 lambda: self._tts(self.el_voice, "Hello, this is a short check from Hoola.", engine="eleven"),
                 lambda: ele() or ("" if self.el_voice else "no Premium voice was listed"))

        def preview():
            data = asyncio.run(V.preview(T, self.gem_voice, "en"))
            k = _sound_ok(data)
            return bool(k), k or "no sound"
        self.run("Voice preview (Play on a voice)", "Gemini", preview, lambda: gem() or ("" if self.gem_voice else "no voice"))

        # ---- dictionary
        def hear():
            V.rule_add(T, "Hoola", "Hoo-la")
            data = asyncio.run(V.hear(T, "Hoola is here.", voice=self.gem_voice))
            k = _sound_ok(data)
            return bool(k), (k + " · read with the dictionary") if k else "no sound"
        self.run("Dictionary: Hear it", "Gemini", hear, lambda: gem() or ("" if self.gem_voice else "no voice"))

        # ---- dialogue
        b = V.builtin() if EN.gemini_ready() else []
        two = [v["id"] for v in b[:2]]
        lines = [{"speaker": "Asha", "text": "Hello, welcome."}, {"speaker": "Ravi", "text": "Thank you, glad to be here."}]
        self.run("Dialogue (line by line)", "Gemini",
                 lambda: self._row(V.dialogue(T, lines, {"Asha": two[0], "Ravi": two[1]}, lang="en", mode="lines")),
                 lambda: gem() or ("" if len(two) == 2 else "fewer than two voices"))
        self.run("Dialogue (natural take, two voices)", "Gemini",
                 lambda: self._row(V.dialogue(T, lines, {"Asha": two[0], "Ravi": two[1]}, lang="en", mode="natural")),
                 lambda: gem() or ("" if len(two) == 2 else "fewer than two voices"))

        def el_two():
            e = EL.voices()
            return ["ev_" + e[0]["id"], "ev_" + e[1]["id"]] if len(e) >= 2 else []
        self.run("Dialogue (natural take, Premium voices)", "ElevenLabs",
                 lambda: self._row(V.dialogue(T, lines, dict(zip(("Asha", "Ravi"), el_two())), lang="en", mode="natural")),
                 lambda: ele() or ("" if len(el_two()) == 2 else "fewer than two premium voices"))

        def script():
            r = asyncio.run(V.podcast(T, (
                "Hoola Vocal is the voice studio inside Hoola. It reads any text aloud in about 140 languages, in a "
                "ready-made voice or in a voice the user designs from words.\n\nIt also makes conversations between two "
                "or more people, reads whole books chapter by chapter, dubs videos into other languages and makes sound "
                "effects from a short description.\n\nEvery file it makes carries an AI mark, and the price of every "
                "job is shown before anything is spent."), minutes=1))
            n = len(r.get("lines") or [])
            return n > 0, f"{n} lines written from the text"
        self.run("Dialogue: Write it from a document", "Gemini (text)", script, gem)

        # ---- studio
        def chapter():
            p = V.project_save(T, title="Check", voice=self.gem_voice, lang="en",
                               chapters=[{"title": "One", "text": "The wind came off the sea."}])
            pid = p.get("id") or (p.get("project") or {}).get("id")
            r = asyncio.run(V.chapter_make(T, pid, 0))
            return self.judge_row(r) if r.get("id") else (False, "no chapter sound")
        self.run("Studio: make a chapter", "Gemini", chapter, lambda: gem() or ("" if self.gem_voice else "no voice"))

        # ---- sound effects
        self.run("Sound effects: game sounds", "Hoola server", lambda: (bool(_sound_ok(V.sfx_sound("coin", 1)[0])), "coin #1 made by code"))

        def fx_words():
            r = V.sfx_text(T, "a single short wooden click", seconds=0.5, takes=1, follow=0.3)
            return self.judge_row(r)
        self.run("Sound effects: from words", "ElevenLabs", fx_words, ele)

        def improve():
            r = V.sfx_improve("rain on roof")
            t = str(r.get("prompt") or r.get("text") or "")
            return bool(t), f"“{t[:80]}”"
        self.run("Sound effects: Improve the words", "Gemini (text)", improve, gem)

        # ---- clean-up, voice out of music, voice changer
        src = Path(tempfile.mkdtemp(prefix="vocalcheck_")) / "check.wav"
        src.write_bytes(_tone())
        spoken = self._spoken_file(src.parent)

        def cleanup():
            r = V.cleanup(T, str(spoken or src), name="check", denoise=True, voice=True, level=True)
            return self.judge_row(r)
        self.run("Clean-up (noise, loudness)", "Hoola server", cleanup, ffm)

        def isolate():
            r = V.cleanup(T, str(spoken or src), name="check", music=True)
            return self.judge_row(r)
        self.run("Clean-up: voice out of music", "ElevenLabs", isolate, lambda: ele() or ffm())

        def changer():
            r = V.change(T, str(spoken), self.el_voice, denoise=False)
            return self.judge_row(r)
        self.run("Voice changer", "ElevenLabs", changer,
                 lambda: ele() or ("" if self.el_voice else "no premium voice") or ("" if spoken else "no spoken sample to change"))

        # ---- your voice
        def design():
            r = V.design_preview(T, "A calm, warm middle-aged narrator with a gentle voice", lang="en")
            opts = r.get("previews") or []
            heard = [o for o in opts if _sound_ok(Path(V.audio_file(T, o["pid"])[0]).read_bytes())]
            pend = V._load(T).get("pending") or []
            spoke = ""
            try:                                              # a designed voice speaking (Gemini Interactions API)
                if pend:
                    spoke = _sound_ok(GV.speak_custom("This is my new voice.", str(pend[0]["gid"]), "calm"))
            except Exception as e:   # noqa: BLE001
                spoke = f"FAILED to speak: {e}"
            for p in pend:                                    # the options are Google voices: removed again
                GV.delete(str(p.get("gid") or ""))
            ok = bool(heard) and spoke and not spoke.startswith("FAILED")
            return ok, f"{len(heard)} of {len(opts)} options with a sample; speaking in it: {spoke or 'no sound'}"
        self.run("Your voice: describe a voice", "Gemini", design, gem, paid=True)
        self.row("Your voice: copy my voice (clone)", "Gemini", "NOT CHECKED",
                 "needs a real person reading the consent statement aloud; a check cannot give that")

        # ---- dubbing
        video = self._video(src.parent)
        for mode, eng, need in (("matched", "Gemini", gem), ("own", "ElevenLabs", ele)):
            self.run(f"Dubbing ({'matched voices' if mode == 'matched' else 'their own voices'})", eng,
                     lambda m=mode: self._dub(video, m),
                     lambda n=need: n() or ffm() or ("" if video else "could not make a test video"), paid=True)

        # ---- downloads in every format
        def formats():
            hid = next((h for h in self.made if h), "")
            if not hid:
                return False, "no sound was made to convert"
            got = []
            for f in ("mp3", "ogg", "m4a"):
                p, _ = V.audio_file(T, hid, f)
                got.append(f"{f} {'ok' if _sound_ok(Path(p).read_bytes()) else 'NOT SOUND'}")
            return all("ok" in g for g in got), ", ".join(got)
        self.run("Download as MP3 / OGG / M4A", "Hoola server", formats, ffm)

        shutil.rmtree(src.parent, ignore_errors=True)
        return self.rows

    # ------------------------------------------------------------------ pieces
    def _tts(self, voice: str, text: str, engine: str = "auto") -> tuple[bool, str]:
        r = asyncio.run(self.V.tts(T, text, voice=voice, lang="en", takes=1, engine=engine, fmt="wav"))
        return self.judge_row(r)

    def _row(self, coro) -> tuple[bool, str]:
        return self.judge_row(asyncio.run(coro))

    def _spoken_file(self, folder: Path) -> Path | None:
        """A real spoken sample for the changer / isolation: the first speech this check made, else nothing."""
        for hid in self.made:
            try:
                data = self.file_of(hid)
            except Exception:   # noqa: BLE001
                continue
            if _sound_ok(data).startswith("WAV"):
                p = folder / "spoken.wav"
                p.write_bytes(data)
                return p
        return None

    def _video(self, folder: Path) -> Path | None:
        sp = self._spoken_file(folder)
        if not sp or not shutil.which("ffmpeg"):
            return None
        out = folder / "check.mp4"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x240:r=10",
                            "-i", str(sp), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)],
                           capture_output=True, timeout=60)
        return out if r.returncode == 0 and out.is_file() else None

    def _dub(self, video: Path, mode: str) -> tuple[bool, str]:
        V = self.V
        r = V.dub_start(T, str(video), ["es"], mode=mode, name="check")
        did = r.get("id") or (r.get("dub") or {}).get("id")
        if not did:
            return False, "the dub did not start"
        end = time.time() + STEP_S - 10
        while time.time() < end:
            d = V.dub_get(T, did)
            st = str(d.get("status") or "")
            if st == "ready":
                return True, f"dubbed into Spanish ({mode})"
            if st == "check":
                return True, f"the Spanish lines are made and wait for her OK ({mode})"
            if st in ("failed", "error"):
                return False, str(d.get("error") or "failed")
            time.sleep(5)
        return False, "not finished within the check's time"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--paid", action="store_true", help="also voice design and dubbing (a few cents)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    from . import service as V
    c = Check(paid=a.paid)
    try:
        rows = c.go()
    finally:
        shutil.rmtree(V._home(T), ignore_errors=True)
    if a.json:
        print(json.dumps(rows, indent=1))
    else:
        w = max(len(r["tool"]) for r in rows)
        for r in rows:
            sec = f"{r['seconds']:>5.1f}s" if r["seconds"] else "      "
            print(f"{r['result']:<13} {r['tool']:<{w}}  {r['engine']:<14} {sec}  {r['detail']}")
        n = {k: sum(1 for r in rows if r["result"] == k) for k in ("LIVE", "DEAD", "NOT CONNECTED", "NOT CHECKED", "SKIPPED")}
        print("\n" + " · ".join(f"{v} {k.lower()}" for k, v in n.items() if v))
    return 1 if any(r["result"] == "DEAD" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
