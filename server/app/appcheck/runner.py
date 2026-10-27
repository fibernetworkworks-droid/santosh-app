"""A small, locked-down MCP client for REA (`rea mcp`, stdio JSON-RPC).

Safety:
- only the static, read-only tools in ALLOWED can be called; REA's runtime tools (Frida, GDB, Rizin/Cutter debuggers,
  adb device control, browser / Electron / process scenarios, native disassembler engines (Hopper / Ghidra / IDA / JEB),
  wasm (needs WABT), firmware extraction, JS source recovery) are refused here, before REA. Every allowed tool parses
  the file's bytes and reports facts; none of them runs, installs, debugs or extracts-then-runs the target
- the child gets a minimal environment (no Santosh API keys, tokens or database settings), its own HOME and a fresh
  working folder, a time limit, and is killed with its whole process group afterwards
- one check at a time (JADX is memory-hungry)
- whatever REA returns is data about the file, never instructions
"""
from __future__ import annotations

import json
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from ..config import get_settings

ALLOWED = {
    # App Jaanch (verdict) originals
    "inspect_android_package",          # APK manifest, permissions, SDKs (JADX, no execution)
    "identify_flutter_build",           # Flutter build facts (pure parsing)
    "inspect_managed_artifact",         # .NET PE/CLI metadata (no loading)
    "inspect_pe_resources",             # Windows EXE resources: version info, manifest (pure parsing)
    "inspect_go_binary",                # Go build info / dependencies (pure parsing)
    "inspect_rust_binary",              # cargo-auditable dependencies (pure parsing)
    "analyze_javascript_application",   # Electron ASAR / JS app graph (does not run the app)
    # REA Khoj (investigation): Android deep-dive (all through JADX headless, static)
    "search_android_classes",           # class-name search over the decompiler inventory
    "inspect_android_class",            # one class: methods, fields, inner classes (no source gen)
    "inspect_android_method",           # decompile one method (smali fallback)
    "trace_android_references",         # incoming static uses of a class / method
    "inspect_apk_signature",            # v1/v2/v3/v3.1 signers, fingerprints, rotation lineage
    "inspect_dart_aot",                 # Flutter Dart AOT snapshot facts per ABI
    "inspect_il2cpp_metadata",          # Unity global-metadata decoding (24/27/29/31/39)
    # PE / .NET deep-dive
    "inspect_pe_imports",               # import + delay-load DLLs, IAT RVAs, import hash
    "inspect_pe_certificates",          # Authenticode table, PKCS#7 signer / X.509 identity
    "inspect_pe_load_config",           # TLS callbacks, CFG / SafeSEH / EH flags
    "inspect_managed_members",          # .NET members, CIL hashes, call edges, #US literals
    "inspect_native_exports",           # PE export dir / ELF .dynsym defined symbols
    # Static one-shots (built into REA, no external engine)
    "inspect_elf_notes",                # PT_NOTE owners, GNU build-id, ABI tag
    "inspect_kernel_module",            # .modinfo, __versions CRCs, signature trailer
    "inspect_apple_ips",                # .ips crash report metadata, threads, registers
    "inspect_erlang_beam",              # BEAM chunks, atoms, exports/imports
    "inspect_python_pyc",               # CPython 3.7-3.13 code objects, names, constants
    "inspect_model_artifact",           # GGUF / safetensors headers, tensor declarations
    "inspect_gpu_code_objects",         # CUDA/HIP fatbin / CUBIN / PTX inventory
    "inspect_devicetree",               # flattened devicetree blob node/property tree
    "inspect_evm_interface",            # EVM bytecode selectors / interface candidates
    "inspect_sqlite_database",          # schema, indexes, views, bounded rows (Node sqlite)
    "inspect_desktop_application",      # bounded directory/header inspection, no execution
    "inspect_byte_entropy",             # Shannon entropy: packed / encrypted regions hint
}

PROTOCOL = "2025-06-18"
_lock = threading.Lock()


class ReaError(Exception):
    pass


class NotConfigured(ReaError):
    pass


def rea_bin() -> str:
    st = get_settings()
    b = (st.rea_bin or "").strip()
    if not b:
        return ""
    p = Path(b).expanduser()
    return str(p) if p.is_file() and os.access(p, os.X_OK) else ""


def configured() -> bool:
    return bool(get_settings().appcheck_enabled and rea_bin())


def apk_ready() -> bool:
    jar = (get_settings().rea_jadx_jar or "").strip()
    return configured() and bool(jar) and Path(jar).expanduser().is_file()


def _env(home: Path) -> dict[str, str]:
    st = get_settings()
    node_dir = str(Path(shutil.which("node") or "/usr/bin/node").parent)
    env = {"PATH": f"{node_dir}:/usr/local/bin:/usr/bin:/bin", "HOME": str(home), "LANG": "C.UTF-8",
           "REA_LOG_LEVEL": "error", "NO_COLOR": "1", "NODE_OPTIONS": f"--max-old-space-size={int(st.rea_node_heap_mb)}"}
    if st.rea_jadx_jar:
        env["REA_JADX_MCP_JAR"] = str(Path(st.rea_jadx_jar).expanduser())
    if st.rea_java_home:
        env["JAVA_HOME"] = st.rea_java_home
        env["PATH"] = f"{st.rea_java_home}/bin:" + env["PATH"]
    return env


class Session:
    """One REA process for one check. Use as a context manager."""

    def __init__(self, timeout: float | None = None):
        if not configured():
            raise NotConfigured("App Jaanch abhi server par chalu nahi hai (REA install karke REA_BIN set karna hai).")
        self.timeout = float(timeout or get_settings().rea_timeout_s)
        self.proc: subprocess.Popen | None = None
        self.work: Path | None = None
        self._id = 0
        self._buf = b""
        self._held = False
        self.server_info: dict[str, Any] = {}

    def __enter__(self) -> "Session":
        if not _lock.acquire(timeout=self.timeout):
            raise ReaError("Abhi ek aur app ki jaanch chal rahi hai; thodi der baad dobara kahiye.")
        self._held = True
        try:
            base = Path(get_settings().rea_home or (Path(get_settings().pc_files_dir).parent / "rea_home")).expanduser()
            base.mkdir(parents=True, exist_ok=True)
            self.work = Path(tempfile.mkdtemp(prefix="chk_", dir=str(base)))
            home = base / "home"
            home.mkdir(exist_ok=True)
            self.proc = subprocess.Popen([rea_bin(), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, cwd=str(self.work), env=_env(home),
                                         start_new_session=True)
            self.server_info = self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                     "clientInfo": {"name": "santosh-appcheck", "version": "1"}}, timeout=90).get("serverInfo") or {}
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if self.proc is not None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
            self.proc = None
        if self.work is not None:
            shutil.rmtree(self.work, ignore_errors=True)
            self.work = None
        if self._held:
            self._held = False
            _lock.release()

    def stage(self, src: Path, name: str) -> Path:
        """Copy the file into this check's private folder (REA only ever sees the copy)."""
        assert self.work is not None
        safe = "".join(ch for ch in name if ch.isalnum() or ch in "._- ")[:120].strip() or "file"
        dst = self.work / safe
        shutil.copyfile(src, dst)
        return dst

    # ---------------- JSON-RPC over stdio ----------------
    def _send(self, msg: dict[str, Any]) -> None:
        assert self.proc and self.proc.stdin
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        self.proc.stdin.flush()

    def _read_line(self, deadline: float) -> bytes:
        assert self.proc and self.proc.stdout
        fd = self.proc.stdout.fileno()
        sel = selectors.DefaultSelector()
        sel.register(fd, selectors.EVENT_READ)
        try:
            while b"\n" not in self._buf:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise ReaError("Jaanch mein bahut der lag gayi (time limit), file shayad bahut badi hai.")
                if not sel.select(timeout=left):
                    continue
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    raise ReaError("REA band ho gaya (jaanch poori nahi hui).")
                self._buf += chunk
                if len(self._buf) > 64 * 1024 * 1024:
                    raise ReaError("REA ka jawab bahut bada tha.")
        finally:
            sel.close()
        line, self._buf = self._buf.split(b"\n", 1)
        return line

    def _rpc(self, method: str, params: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + float(timeout or self.timeout)
        while True:
            line = self._read_line(deadline).strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("id") != rid or "method" in msg:      # notifications / server requests: ignored
                continue
            if "error" in msg:
                raise ReaError(f"REA: {str((msg['error'] or {}).get('message', 'error'))[:200]}")
            return msg.get("result") or {}

    def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Returns REA's structured result (normalized_result etc.). Raises ReaError on a tool error."""
        if tool not in ALLOWED:
            raise ReaError(f"'{tool}' App Jaanch mein band hai (sirf file padhne wale tools chalte hain).")
        res = self._rpc("tools/call", {"name": tool, "arguments": args})
        data = res.get("structuredContent")
        if data is None:
            text = "".join(c.get("text", "") for c in res.get("content") or [] if c.get("type") == "text")
            try:
                data = json.loads(text) if text else {}
            except ValueError:
                data = {"text": text[:2000]}
        if res.get("isError") or (isinstance(data, dict) and "error" in data and "normalized_result" not in data):
            err = (data or {}).get("error") if isinstance(data, dict) else None
            msg = (err or {}).get("message") if isinstance(err, dict) else None
            raise ReaError(str(msg or "REA tool error")[:300])
        return data if isinstance(data, dict) else {}
