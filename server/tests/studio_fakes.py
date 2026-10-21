"""From the owner's hoola-studio tests (v0.68 in Hoola).
Fake OpenRouter / fal / BytePlus / Google video APIs that follow the documented request and response shapes.
They record every request so tests can check what the studio sends, and they return real MP4 files.
Prompt words trigger behaviour: BLOCKED -> 422 rejection, FLAKY -> first submit fails with 500, SLOW -> takes ~6 s."""
from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

LOG: list[dict] = []
JOBS: dict[str, dict] = {}
FLAKY_SEEN: set[str] = set()
FILES = Path(tempfile.mkdtemp(prefix="fake_api_"))


def make_mp4(jid: str, duration: int, aspect: str) -> Path:
    aw, ah = (int(x) for x in (aspect if aspect and ":" in aspect else "16:9").split(":"))
    h = 480
    w = round(h * aw / ah) // 2 * 2
    if aw < ah:
        w, h = 480, round(480 * ah / aw) // 2 * 2
    p = FILES / f"{jid}.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:r=24:d={duration}",
                    "-f", "lavfi", "-i", f"sine=f=500:d={duration}", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                    "-shortest", str(p)], check=True)
    return p


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, status=200):
        b = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def base(self):
        return f"http://{self.headers['Host']}"

    def _state(self, j):
        el = time.time() - j["t0"]
        need = 6 if j["slow"] else 0.8
        return "queued" if el < need * 0.3 else "running" if el < need else "done"

    def do_POST(self):
        u = urlparse(self.path)
        body = self._body()
        rec = {"path": u.path, "query": parse_qs(u.query), "auth": self.headers.get("Authorization"), "body": body}
        LOG.append(rec)
        prompt = json.dumps(body)
        if "BLOCKED" in prompt:
            return self._json({"detail": "content policy: request rejected"}, 422)
        if "FLAKY" in prompt and prompt not in FLAKY_SEEN:
            FLAKY_SEEN.add(prompt)
            return self._json({"detail": "upstream error"}, 500)
        jid = uuid.uuid4().hex[:12]
        if u.path.startswith("/fal/"):
            if rec["auth"] != "Key test-fal":
                return self._json({"detail": "bad key"}, 401)
            dur = int(body.get("duration", 5)) if str(body.get("duration", "5")).isdigit() else 5
            JOBS[jid] = {"t0": time.time(), "slow": "SLOW" in prompt, "dur": dur, "aspect": body.get("aspect_ratio")}
            owner = "/".join(u.path.split("/")[2:4])
            b = f"{self.base()}/fal/{owner}/requests/{jid}"
            return self._json({"request_id": jid, "status_url": b + "/status", "response_url": b, "cancel_url": b + "/cancel",
                               "queue_position": 0})
        if u.path == "/ark/api/v3/contents/generations/tasks":
            if rec["auth"] != "Bearer test-ark":
                return self._json({"error": {"message": "bad key"}}, 401)
            JOBS[jid] = {"t0": time.time(), "slow": "SLOW" in prompt, "dur": int(body.get("duration", 5)), "aspect": body.get("ratio")}
            return self._json({"id": jid})
        if u.path == "/openrouter/api/v1/videos":
            if rec["auth"] != "Bearer test-or":
                return self._json({"error": {"code": 401, "message": "No auth credentials found"}}, 401)
            refs = [x["image_url"]["url"] for x in body.get("input_references", [])] + \
                   [x["image_url"]["url"] for x in body.get("frame_images", [])]
            fetched = []
            for url in refs:  # like the real provider: images must be reachable
                if url.startswith("data:image/"):
                    fetched.append("data")
                    continue
                try:
                    import urllib.request
                    with urllib.request.urlopen(url, timeout=10) as r:
                        b = r.read()
                    fetched.append("url-ok" if len(b) > 100 else "url-empty")
                except Exception as e:
                    return self._json({"error": {"code": 400, "message": f"could not fetch image: {e}"}}, 400)
            rec["fetched"] = fetched
            JOBS[jid] = {"t0": time.time(), "slow": "SLOW" in prompt, "dur": int(body.get("duration", 5)),
                         "aspect": body.get("aspect_ratio"), "fail": "ORFAIL" in prompt, "nourl": int(body.get("duration", 5)) % 2 == 1}
            return self._json({"id": jid, "polling_url": f"/openrouter/api/v1/videos/{jid}", "status": "pending"}, 202)
        if u.path == "/google/v1beta/interactions":
            if rec["query"].get("key") != ["test-gemini"]:
                return self._json({"error": {"message": "API key not valid"}}, 400)
            time.sleep(1.0)  # the create call returns when the video is ready
            make_mp4(jid, 8, body.get("response_format", {}).get("aspect_ratio", "16:9"))
            return self._json({"id": "int_" + jid, "steps": [{"type": "model_output", "content": [
                {"type": "video", "mime_type": "video/mp4", "uri": f"{self.base()}/google/v1beta/files/{jid}"}]}]})
        self._json({"detail": "not found"}, 404)

    def do_PUT(self):
        self._json({"status": "CANCELLATION_REQUESTED"}, 202)

    def do_DELETE(self):
        self._json({}, 200)

    def do_GET(self):
        u = urlparse(self.path)
        parts = u.path.strip("/").split("/")
        if u.path.startswith("/fal/") and "requests" in parts:
            jid = parts[parts.index("requests") + 1]
            j = JOBS.get(jid)
            if not j:
                return self._json({"detail": "not found"}, 404)
            st = self._state(j)
            if u.path.endswith("/status"):
                return self._json({"status": {"queued": "IN_QUEUE", "running": "IN_PROGRESS", "done": "COMPLETED"}[st],
                                   "queue_position": 0})
            if st != "done":
                return self._json({"detail": "still in progress"}, 400)
            if not (FILES / f"{jid}.mp4").exists():
                make_mp4(jid, j["dur"], j["aspect"])
            return self._json({"video": {"url": f"{self.base()}/files/{jid}.mp4", "content_type": "video/mp4"}, "seed": 42})
        if u.path == "/openrouter/api/v1/videos/models":
            return self._json({"data": [
                {"id": "bytedance/seedance-2.0-fast", "name": "Seedance 2.0 Fast", "supported_durations": [4, 5, 6, 8, 10, 12, 15],
                 "supported_resolutions": ["480p", "720p", "1080p"], "supported_aspect_ratios": ["16:9", "9:16", "1:1"],
                 "supported_frame_images": ["first_frame", "last_frame"], "pricing_skus": [{"sku": "video_480p", "price": "0.04"}]},
                {"id": "google/veo-3.1-fast", "name": "Veo 3.1 Fast", "supported_durations": [4, 6, 8],
                 "supported_resolutions": ["720p", "1080p"], "supported_aspect_ratios": ["16:9", "9:16"]},
                {"id": "x-ai/grok-imagine-video-1.5-lite", "name": "Grok Imagine Video 1.5 Lite", "supported_durations": [6, 10],
                 "supported_resolutions": ["480p", "720p"], "supported_aspect_ratios": ["16:9", "9:16"]}]})
        if u.path.startswith("/openrouter/api/v1/videos/"):
            LOG.append({"path": u.path, "query": parse_qs(u.query), "auth": self.headers.get("Authorization"), "method": "GET"})
            if self.headers.get("Authorization") != "Bearer test-or":
                return self._json({"error": {"code": 401, "message": "auth"}}, 401)
            jid = parts[4]
            j = JOBS.get(jid)
            if not j:
                return self._json({"error": {"code": 404, "message": "not found"}}, 404)
            if u.path.endswith("/content"):
                if not (FILES / f"{jid}.mp4").exists():
                    make_mp4(jid, j["dur"], j["aspect"])
                return self._file(FILES / f"{jid}.mp4")
            st = self._state(j)
            if st != "done":
                return self._json({"id": jid, "status": "pending" if st == "queued" else "in_progress",
                                   "polling_url": f"/openrouter/api/v1/videos/{jid}"})
            if j["fail"]:
                return self._json({"id": jid, "status": "failed", "error": "provider rejected the content"})
            out = {"id": jid, "status": "completed", "generation_id": "gen-" + jid,
                   "usage": {"cost": round(0.0123 * j["dur"], 4), "is_byok": False}}
            if not j["nourl"]:
                if not (FILES / f"{jid}.mp4").exists():
                    make_mp4(jid, j["dur"], j["aspect"])
                out["unsigned_urls"] = [f"/openrouter/api/v1/videos/{jid}/content?index=0"]
            return self._json(out)
        if u.path.startswith("/ark/api/v3/contents/generations/tasks/"):
            jid = parts[-1]
            j = JOBS.get(jid)
            st = self._state(j)
            if st != "done":
                return self._json({"id": jid, "status": st})
            if not (FILES / f"{jid}.mp4").exists():
                make_mp4(jid, j["dur"], j["aspect"])
            return self._json({"id": jid, "status": "succeeded", "content": {"video_url": f"{self.base()}/files/{jid}.mp4"}, "seed": 7})
        if u.path.startswith("/google/v1beta/files/"):
            fid = parts[-1]
            if fid.endswith(":download"):
                return self._file(FILES / f"{fid.split(':')[0]}.mp4")
            return self._json({"name": f"files/{fid}", "state": "ACTIVE"})
        if u.path.startswith("/files/"):
            return self._file(FILES / parts[-1])
        self._json({"detail": "not found"}, 404)

    def _file(self, p: Path):
        if not p.exists():
            return self._json({"detail": "no file"}, 404)
        b = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def serve(port: int = 8960) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
