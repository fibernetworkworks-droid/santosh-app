"""HOOLA FRAMES (v0.471): the HyperFrames render worker.

HeyGen's open-source HyperFrames engine (github.com/heygen-com/hyperframes, Apache 2.0,
npm `hyperframes` pinned 0.9.6) turns an HTML composition into a deterministic MP4:
frame clock -> animation seek -> headless Chrome capture -> FFmpeg encode + audio mix.
The model authors the composition; this worker is the only thing that runs it.

Discipline (the REA runner's, applied to Chromium + FFmpeg):
- one render at a time on the whole box; a second caller waits frames_queue_wait_s and
  is refused honestly, so a live voice call NEVER waits behind a render
- every CLI run is a subprocess in its own process group; past frames_timeout_s the
  whole group is SIGKILLed - no zombie Chrome, no half-written MP4
- renders run `nice -n 19` (and `ionice -c2 -n7` when available): the API and the calls
  keep their CPU
- per-tenant project dirs with an LRU (frames_per_tenant) and a disk janitor
  (frames_disk_cap_gb / frames_keep_h); one tenant's project is never another's
- the model's HTML and its listed asset files are the ONLY inputs; paths are sanitised
  (no `..`, no absolute paths, project-relative); nothing from a composition ever runs
  outside the project's headless Chrome
- the determinism gate runs first (`hyperframes check --json`): a composition that
  fetches network mid-render, reads the wall clock or rolls unseeded dice is refused
  before any render
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import get_settings

_ACTIONS = ("render", "check", "timeline", "snapshot", "add", "status", "avatar_film")
_NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,120}$")


class FramesError(Exception):
    pass


class NotConfigured(FramesError):
    pass


def frames_bin() -> str:
    """Absolute path to the pinned hyperframes launcher, or '' when absent."""
    st = get_settings()
    b = (st.frames_bin or "").strip()
    if not b:
        return ""
    p = Path(b).expanduser()
    return str(p) if p.is_file() and os.access(p, os.X_OK) else ""


def configured() -> bool:
    return bool(get_settings().frames_enabled and frames_bin())


def _root() -> Path:
    st = get_settings()
    r = Path((st.frames_root or "").strip() or (Path("data") / "frames")).expanduser()
    r.mkdir(parents=True, exist_ok=True)
    return r


def _env() -> dict[str, str]:
    st = get_settings()
    node_dir = (st.frames_node_dir or "").strip()
    if node_dir:
        node_dir = str(Path(node_dir).expanduser())
    else:
        node_dir = str(Path(shutil.which("node") or "/usr/bin/node").parent)
    env = {"PATH": f"{node_dir}:/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()),
           "LANG": "C.UTF-8", "NO_COLOR": "1", "CI": "1"}
    for k in ("HYPERFRAMES_BROWSER_PATH", "PRODUCER_HEADLESS_SHELL_PATH"):   # v0.747 a browser the box already has
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _prefix() -> list[str]:
    """nice/ionice wrappers so a render never takes CPU from the API or a live call."""
    argv: list[str] = []
    if shutil.which("nice"):
        argv += ["nice", "-n", "19"]
    if shutil.which("ionice"):
        argv += ["ionice", "-c", "2", "-n", "7"]
    return argv


def _run(argv: list[str], cwd: Path, timeout: float) -> tuple[int, str]:
    """One CLI run in its own process group, killed whole past the deadline."""
    st = get_settings()
    proc = subprocess.Popen(_prefix() + argv, cwd=str(cwd), env=_env(),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=min(timeout, max(1, st.frames_timeout_s)))
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
        raise FramesError(f"timeout: {argv[0]} passed {int(timeout)}s; process group killed")
    except BaseException:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        raise
    return proc.returncode, (out or b"").decode("utf-8", "replace")[-12000:]


def _cli(*args: str, cwd: Path, timeout: float) -> str:
    binp = frames_bin()
    if not binp:
        raise NotConfigured(
            "HOOLA FRAMES is not installed on this server yet (FRAMES_BIN missing). "
            "Run install_hyperframes.sh, or ask the owner.")
    rc, out = _run([binp, *args], cwd=cwd, timeout=timeout)
    if rc != 0:
        raise FramesError(f"hyperframes {args[0]} failed (rc={rc}): {out[-1500:]}")
    return out


# ---------------------------------------------------------------- projects ---

def tenant_dir(tenant: str) -> Path:
    """Per-tenant project root: sha1-isolated, like the REA cache."""
    import hashlib
    d = _root() / hashlib.sha1(tenant.encode()).hexdigest()[:16]
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_project(tenant: str) -> Path:
    d = tenant_dir(tenant) / f"p-{uuid.uuid4().hex[:10]}"
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "compositions").mkdir(parents=True, exist_ok=True)
    _touch_tenant_lru(d)
    return d


def _touch_tenant_lru(project: Path) -> None:
    (project / ".frames_lru").write_text(str(time.time()))
    td = project.parent
    st = get_settings()
    projs = sorted([p for p in td.glob("p-*") if p.is_dir()],
                   key=lambda p: _lru_key(p), reverse=True)
    for old in projs[int(max(1, st.frames_per_tenant)):]:
        shutil.rmtree(old, ignore_errors=True)


def _lru_key(p: Path) -> float:
    try:
        return float((p / ".frames_lru").read_text().strip())
    except Exception:
        try:
            return p.stat().st_mtime
        except Exception:
            return 0.0


def _safe_rel(name: str) -> str:
    n = (name or "").strip().replace("\\", "/").lstrip("/")
    if not n or ".." in n.split("/") or not _NAME_OK.match(n):
        raise FramesError(f"wrong file name: {name!r} (project-relative only, no '..')")
    if n.startswith(("assets/", "compositions/")) or n == "index.html":
        return n
    raise FramesError(f"file {name!r} must be inside the project: index.html, assets/... or compositions/...")


def write_project(tenant: str, html: str, files: list[dict[str, Any]] | None,
                  project: Path | None = None) -> Path:
    """Materialise the model's composition. ONLY this + listed assets go on disk."""
    if not (html or "").strip():
        raise FramesError("The composition is empty - give the HTML (the content of index.html).")
    p = project or new_project(tenant)
    try:
        (p / "index.html").write_text(html, encoding="utf-8")
        for f in files or []:
            name = str(f.get("name", ""))
            rel = _safe_rel(name)
            dest = p / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if f.get("text") is not None:
                dest.write_text(str(f["text"]), encoding="utf-8")
                continue
            src = str(f.get("path", "") or "")
            if not src:
                raise FramesError(f"asset {name!r}: give either path (a file already stored) or text.")
            _copy_src_file(rel, src, dest)
        _touch_tenant_lru(p)
        return p
    except FramesError:
        if project is None:
            shutil.rmtree(p, ignore_errors=True)
        raise


def _copy_src_file(rel: str, src: str, dest: Path) -> None:
    """src is an absolute path the AGENT layer resolved against the tenant (ctx) —
    this worker never sees a file_id, so no cross-tenant read can happen here."""
    st = get_settings()
    s = Path(src).expanduser()
    if not s.is_file():
        raise FramesError(f"asset {rel!r}: file not found.")
    if s.stat().st_size > st.frames_max_mb * 1024 * 1024:
        raise FramesError(f"asset {rel!r} is larger than {st.frames_max_mb} MB.")
    shutil.copyfile(s, dest)


# ---------------------------------------------------------------- the gate ---

def _check_json(project: Path) -> dict[str, Any]:
    out = _cli("check", "--json", cwd=project,
               timeout=min(300.0, max(60.0, get_settings().frames_timeout_s / 2)))
    i = out.find("{")
    if i < 0:
        return {"ok": True, "unparsed": out[-400:]}
    try:
        return json.loads(out[i:])
    except json.JSONDecodeError:
        return {"ok": True, "unparsed": out[-400:]}


def _compact_errors(rep: dict[str, Any], cap: int = 1400) -> list[str]:
    errs: list[str] = []
    for section in ("lint", "runtime", "layout", "motion", "contrast", "craft"):
        s = rep.get(section) or {}
        items = s.get("errors") if isinstance(s, dict) else None
        for it in items or []:
            if isinstance(it, dict):
                errs.append(f"[{section}] {it.get('rule') or it.get('code') or it.get('id') or 'error'}: "
                            f"{str(it.get('message') or it)[:220]}")
            else:
                errs.append(f"[{section}] {str(it)[:220]}")
    if rep.get("unparsed"):
        errs.append(f"[raw] {str(rep['unparsed'])[:300]}")
    out, size = [], 0
    for e in errs:
        size += len(e)
        out.append(e)
        if size >= cap:
            out.append("... (more errors; fix these first)")
            break
    return out


# ---------------------------------------------------------------- janitor ---

def _dir_size(p: Path) -> int:
    total = 0
    for walk in p.rglob("*"):
        try:
            if walk.is_file():
                total += walk.stat().st_size
        except OSError:
            pass
    return total


def sweep() -> dict[str, int]:
    """Age out old projects, then honour the disk cap (oldest finished first)."""
    st = get_settings()
    root = _root()
    now = time.time()
    removed = 0
    for td in [d for d in root.iterdir() if d.is_dir()] if root.is_dir() else []:
        for p in list(td.glob("p-*")):
            age_h = (now - _lru_key(p)) / 3600.0
            if age_h > max(1, st.frames_keep_h):
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
    cap = max(0.5, st.frames_disk_cap_gb) * 1024 ** 3
    sizes = {p: _dir_size(p) for p in root.glob("*/*/p-*") if p.is_dir()}
    total = sum(sizes.values())
    if total > cap:
        for p, _s in sorted(sizes.items(), key=lambda kv: _lru_key(kv[0])):
            if total <= cap:
                break
            total -= sizes.get(p, 0)
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    return {"removed": removed, "bytes": int(total)}


# ---------------------------------------------------------------- actions ---

_render_lock = threading.Lock()


def _probe_mp4(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"size_bytes": path.stat().st_size}
    if shutil.which("ffprobe"):
        try:
            rc, out = _run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "json", str(path)],
                           cwd=path.parent, timeout=60)
            if rc == 0 and out.strip():
                info["duration_s"] = round(float(json.loads(out)["format"]["duration"]), 2)
        except Exception:
            pass
    return info


def do_render(tenant: str, html: str, files: list[dict[str, Any]] | None,
              out_name: str = "film") -> dict[str, Any]:
    """check -> render -> probe. The ONE lock: the box renders one film at a time."""
    st = get_settings()
    if not _render_lock.acquire(timeout=max(1, st.frames_queue_wait_s)):
        raise FramesError(
            "A render is running right now (only one at a time). Try again in a little while.")
    try:
        sweep()
        project = write_project(tenant, html, files)
        rep = _check_json(project)
        if not rep.get("ok"):
            return {"ok": False, "stage": "check", "errors": _compact_errors(rep)}
        _cli("render", "-o", "out.mp4", cwd=project, timeout=float(st.frames_timeout_s))
        mp4 = project / "out.mp4"
        if not mp4.is_file() or mp4.stat().st_size == 0:
            raise FramesError("the render said complete but no MP4 was found; try again.")
        facts = _probe_mp4(mp4)
        return {"ok": True, "mp4_path": str(mp4), "project": str(project), **facts}
    finally:
        _render_lock.release()


def do_check(tenant: str, html: str, files: list[dict[str, Any]] | None) -> dict[str, Any]:
    project = write_project(tenant, html, files)
    rep = _check_json(project)
    if rep.get("ok"):
        return {"ok": True, "note": "check passed - ready to render."}
    return {"ok": False, "errors": _compact_errors(rep)}


def do_timeline(tenant: str, html: str, files: list[dict[str, Any]] | None) -> dict[str, Any]:
    project = write_project(tenant, html, files)
    out = _cli("timeline", cwd=project, timeout=120.0)
    return {"ok": True, "timeline": out[-2000:]}


def do_snapshot(tenant: str, html: str, files: list[dict[str, Any]] | None,
                times: list[float] | None) -> dict[str, Any]:
    project = write_project(tenant, html, files)
    argv = ["snapshot", "--json"]
    if times:
        argv.append("--at=" + ",".join(f"{float(t):.2f}" for t in times[:6]))
    out = _cli(*argv, cwd=project, timeout=240.0)
    shots = sorted((project / ".hyperframes" / "artifacts" / "snapshots").rglob("*.png"))
    return {"ok": True, "pngs": [str(s) for s in shots[:6]], "raw": out[-600:]}


def do_add(tenant: str, block: str) -> dict[str, Any]:
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,60}$", (block or "")):
        raise FramesError("the block name looks wrong.")
    project = new_project(tenant)
    out = _cli("add", block, cwd=project, timeout=180.0)
    added = [str(f.relative_to(project)) for f in project.rglob("*.html")]
    return {"ok": True, "files": added[:12], "note": out[-400:]}


# ---------------------------------------------------------------- avatar films ---

def _audio_duration(path: Path) -> float:
    try:
        rc, out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", str(path)], cwd=path.parent, timeout=60)
        return float(json.loads(out)["format"]["duration"])
    except Exception as e:
        raise FramesError(f"voice file {path.name}: could not measure its length: {type(e).__name__}") from None


def _pad_wav(src: Path, dest: Path, seconds: float) -> None:
    """Exact-length mono 48k WAV: the scene spans and the voice track stay frame-aligned."""
    rc, out = _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", "apad",
                    "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", "-t", f"{seconds:.3f}",
                    str(dest)], cwd=src.parent, timeout=120)
    if rc != 0 or not dest.is_file():
        raise FramesError(f"voice {src.name}: could not fit it to the scene length: {out[-300:]}")


def _concat_wavs(padded: list[Path], dest: Path) -> None:
    lst = dest.parent / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in padded), encoding="utf-8")
    rc, out = _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "pcm_s16le", str(dest)], cwd=dest.parent, timeout=300)
    lst.unlink(missing_ok=True)
    if rc != 0 or not dest.is_file():
        raise FramesError(f"could not join the voice track: {out[-300:]}")


def do_avatar_film(tenant: str, spec: dict, files: list[dict[str, Any]] | None = None,
                   out_name: str = "film", on_stage: Any = None, cancel: Any = None) -> dict[str, Any]:
    """AVATAR FILMS: spec -> lab voice -> word-timed composition -> the normal check->render gate.

    The slow parts (TTS, alignment) run BEFORE the render lock, so a busy queue never
    blocks them and a voice call is never stuck behind a render that is still scripting.
    `files` come from the tool layer owner-checked (name = the spec's asset name, e.g.
    assets/avatar.jpg; path = the stored file); the worker adds the voice track it made.
    """
    from . import avatar as av
    from ..videoedit import captions as cap
    parts = av.validate_spec(spec)
    sentences = parts["sentences"]
    if not sentences:
        raise FramesError("the script is empty - a film cannot be made without sentences.")

    provided = list(files or [])
    for f in provided:
        if not Path(str(f.get("path", ""))).is_file():
            raise FramesError(f"asset {f.get('name')!r}: file not found.")
    referenced = {parts["avatar"], parts["cta_image"]} | {it["photo"] for it in parts["items"]}
    missing = {r for r in referenced if r and r not in {f["name"] for f in provided}}
    if missing:
        raise FramesError(
            f"asset {', '.join(sorted(missing))} is in the spec but did not arrive by file_id - send it again.")

    def stage(k: str, detail: str = "") -> None:      # v0.747 HOOLA INTERACTIVE: the page shows each real step
        if on_stage:
            try:
                on_stage(k, detail)
            except Exception:
                pass

    def stopped() -> None:                              # v0.747 Stop: checked at every step boundary
        if cancel is not None and cancel.is_set():
            raise FramesError("Stopped. Nothing was kept.")

    tmp = _root() / f"_voice-{uuid.uuid4().hex[:10]}"
    tmp.mkdir(parents=True)
    try:
        stage("voice", "no voice - timed at reading speed" if parts["silent"] else f"0 of {len(sentences)} lines")
        if parts["silent"]:
            # honest silent mode: no voice engine needed; scenes timed at reading speed
            has_cta = bool(parts["cta_text"] or parts["cta_image"])
            spans = [av.scene_span(len(s) / av.ESTIMATE_CPS, is_last=(i == len(sentences) - 1),
                                   has_cta=has_cta) for i, s in enumerate(sentences)]
            # v0.747 the reading time, not the whole span: with speech == span the closing card started after the end
            speech = [min(sp, len(s) / av.ESTIMATE_CPS) for sp, s in zip(spans, sentences)]
            words, voice_asset = None, None
        else:
            from ..interactive import lab
            if not lab.configured():
                raise NotConfigured(
                    "An AVATAR FILM needs a voice: the Model Lab is not set up on this server "
                    "(AVATAR_ENGINE_URL / AVATAR_ENGINE_KEY). If you like, send silent:true in the spec "
                    "- the same film, without voice.")
            raw: list[Path] = []
            for i, s in enumerate(sentences):
                stopped()
                stage("voice", f"{i + 1} of {len(sentences)} lines")
                try:
                    data = lab.voice(s, lang=parts["lang"], model=parts["voice_model"])
                except Exception as e:
                    raise FramesError(f"the voice could not be made (sentence {i + 1}): {e}") from None
                p = tmp / f"raw-{i:02d}.wav"
                p.write_bytes(data)
                raw.append(p)
            speech = [_audio_duration(p) for p in raw]
            has_cta = bool(parts["cta_text"] or parts["cta_image"])
            spans = [av.scene_span(d, is_last=(i == len(sentences) - 1), has_cta=has_cta)
                     for i, d in enumerate(speech)]
            padded = []
            for i, (p, span) in enumerate(zip(raw, spans)):
                q = tmp / f"pad-{i:02d}.wav"
                _pad_wav(p, q, span)
                padded.append(q)
            voice = tmp / "voice.wav"
            _concat_wavs(padded, voice)
            stopped()
            stage("align", f"{sum(speech):.0f} s of speech")
            words = cap.whisper_words(str(voice), parts["lang"] if parts["lang"] not in ("hi", "en") else "hi")
            voice_asset = str(voice)

        plan = av.timing_plan(sentences, spans, speech, words)
        all_files = ([{"name": "assets/voice.wav", "path": voice_asset}] if voice_asset else []) + provided
        html = av.build_html(parts, plan)
        stopped()
        stage("draw", f"{len(plan['scenes'])} scenes, {plan['total']:.0f} s")
        res = do_render(tenant, html, all_files, out_name=out_name)
        if res.get("ok"):
            res |= {"avatar": True, "shape": parts["shape"], "scenes": len(plan["scenes"]),
                    "cues": len(plan["cues"]), "total_s": plan["total"],
                    "words_estimated": plan["estimated"], "silent": parts["silent"]}
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def status() -> dict[str, Any]:
    st = get_settings()
    binp = frames_bin()
    base: dict[str, Any] = {
        "enabled": bool(st.frames_enabled and binp),
        "bin": binp or "",
        "pin": "hyperframes@0.9.6",
        "actions": list(_ACTIONS),
        "timeout_s": st.frames_timeout_s,
        "disk_cap_gb": st.frames_disk_cap_gb,
        "per_tenant": st.frames_per_tenant,
        "busy": _render_lock.locked(),
    }
    if not binp:
        base["note"] = "FRAMES_BIN not set; install_hyperframes.sh installs it."
        return base
    try:
        rc, out = _run([binp, "--version"], cwd=Path(tempfile.gettempdir()), timeout=60)
        base["version"] = out.strip().splitlines()[0][-40:] if out.strip() else f"rc={rc}"
    except Exception as e:
        base["version_error"] = str(e)[:120]
    try:
        base["disk"] = sweep()
    except Exception:
        pass
    try:
        from . import avatar as _av
        from ..interactive import lab as _lab
        import importlib.util
        base["avatar"] = {"shapes": list(_av.SHAPES), "lab": bool(_lab.configured()),
                          "voices": list(_lab.VOICE_MODELS),
                          "whisper": importlib.util.find_spec("faster_whisper") is not None}
    except Exception:
        pass
    return base


def run(tenant: str, action: str, html: str = "", files: list[dict[str, Any]] | None = None,
        out_name: str = "film", block: str = "", times: list[float] | None = None,
        spec: dict | None = None) -> dict[str, Any]:
    if action not in _ACTIONS:
        raise FramesError(f"wrong action: {action!r}. One of: {', '.join(_ACTIONS)}")
    if action == "status":
        return status()
    if not configured():
        raise NotConfigured("HOOLA FRAMES is not configured on this server (FRAMES_BIN).")
    if action == "add":
        return do_add(tenant, block)
    if action == "avatar_film":
        return do_avatar_film(tenant, spec or {}, files=files, out_name=out_name)
    if action == "render":
        return do_render(tenant, html, files, out_name=out_name)
    if not (html or "").strip():
        raise FramesError("Give a composition: html (the content of index.html) is required.")
    if action == "check":
        return do_check(tenant, html, files)
    if action == "timeline":
        return do_timeline(tenant, html, files)
    return do_snapshot(tenant, html, files, times)
