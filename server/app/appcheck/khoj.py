"""REA Khoj: "yeh app / program / file kaise kaam karta hai, saboot ke saath."

Investigation loop on top of REA's static MCP tools. The model drives it itself:
overview -> classes -> class -> method -> refs, exactly REA's own agent flow.

This is NOT App Jaanch (the safety verdict). It returns data about how a thing works,
with evidence lines, so the owner can learn a feature and reimplement it; it never cracks
a licence, unlocks paid features, bypasses anti-cheat, copies code, or runs the target.

The same locked-down REA client as App Jaanch is reused: stdio MCP, the static-only
allowlist (extended here), minimal env, one check at a time, killed process-group.
A per-tenant file cache keeps a downloaded/copied target stable across follow-up calls
for the duration of one investigation (the mailbox's stored file may vanish in 24 h).
"""
from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..pc.service import safe_name
from . import analyze as an
from .runner import NotConfigured, ReaError, Session, apk_ready, configured

KHOJ_KEEP_FILES = 8          # per tenant, LRU
KHOJ_TTL_S = 6 * 3600        # an investigation rarely lasts longer; bound disk


class KhojError(Exception):
    pass


# ---------------------------------------------------------------- public status
def status() -> dict[str, Any]:
    return {"enabled": configured(), "apk": apk_ready(), "max_mb": get_settings().appcheck_max_mb,
            "tools": len(getattr(Session, "ALLOWED", None) or []) or None or _allow_count(),
            "kinds": ["apk", "apks", "exe", "elf", "electron", "model", "sqlite", "beam", "pyc", "ips",
                      "devicetree", "kernel", "evm", "go", "rust", "other"]}


def _allow_count() -> int:
    from .runner import ALLOWED
    return len(ALLOWED)


# ---------------------------------------------------------------- file cache (per tenant)
def _cache_root(tenant: str) -> Path:
    base = Path(get_settings().rea_home or (Path(get_settings().pc_files_dir).parent / "rea_home")).expanduser()
    h = hashlib.sha1(tenant.encode("utf-8")).hexdigest()[:16]
    p = base / "khoj" / h
    p.mkdir(parents=True, exist_ok=True)
    return p


def _stage(tenant: str, src: dict[str, Any]) -> tuple[str, Path, str]:
    """Resolve the source file and copy it into the tenant's khoj cache by sha256.

    The mailbox's stored file_id path can vanish in 24 h; a copied copy keeps an
    investigation stable across follow-up calls. The Session still copies this into its
    own private work folder (rea only ever sees the second copy).
    """
    from .service import _resolve
    name, source_path, tmp = _resolve(tenant, src)
    try:
        if not source_path.is_file():
            raise KhojError("File server par nahi mili; dobara bhejiye.")
        size = source_path.stat().st_size
        cap = get_settings().appcheck_max_mb * 1024 * 1024
        if size > cap:
            raise KhojError(f"File {get_settings().appcheck_max_mb} MB se badi hai.")
        sha = an.sha256_file(source_path)
        root = _cache_root(tenant)
        dst_dir = root / sha
        dst = dst_dir / (safe_name(name) or "target")
        dst_dir.mkdir(parents=True, exist_ok=True)
        if not dst.is_file():
            shutil.copyfile(source_path, dst)
            (dst_dir / "touched").write_text(str(int(time.time())))
        else:
            (dst_dir / "touched").write_text(str(int(time.time())))
        _lru_sweep(root)
        return name, dst, an.sniff(dst, name)
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def _lru_sweep(root: Path) -> None:
    try:
        cut = time.time() - KHOJ_TTL_S
        dirs = []
        for d in root.iterdir():
            if not d.is_dir():
                continue
            t = d / "touched"
            ts = int(t.read_text()) if t.is_file() else 0
            if ts < cut:
                shutil.rmtree(d, ignore_errors=True)
                continue
            dirs.append((ts, d))
        dirs.sort()
        while len(dirs) > KHOJ_KEEP_FILES:
            _, d = dirs.pop(0)
            shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass


# ---------------------------------------------------------------- evidence shaping
def _nr(res: dict[str, Any]) -> dict[str, Any]:
    nr = res.get("normalized_result") or {}
    return nr.get("summary") if isinstance(nr.get("summary"), dict) and nr.get("kind") == "summary" else nr


def _clip(s: Any, n: int = 800) -> str:
    if not isinstance(s, str):
        s = str(s)
    return s if len(s) <= n else (s[:n] + f"  … [{len(s) - n} aur chars]")


def _compact(obj: Any, *, depth: int = 0, str_n: int = 320, list_n: int = 30, key_n: int = 40) -> Any:
    """A bounded, JSON-friendly view of whatever REA returned. Strings clipped, lists trimmed,
    dicts clipped, depth bounded. The model gets the structure + enough sample values to
    decide the next probe, without a 5 MiB wall of text."""
    if depth > 4:
        return "<…>"
    if isinstance(obj, str):
        return _clip(obj, str_n)
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (list, tuple)):
        head = [_compact(x, depth=depth + 1, str_n=str_n, list_n=list_n, key_n=key_n) for x in obj[:list_n]]
        if len(obj) > list_n:
            head.append(f"+{len(obj) - list_n} aur")
        return head
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= key_n:
                out[f"+{len(obj) - key_n} keys"] = ""
                break
            out[str(k)] = _compact(v, depth=depth + 1, str_n=str_n, list_n=list_n, key_n=key_n)
        return out
    return str(obj)[:str_n]


def _longest_text(nr: Any, n: int = 6000) -> str:
    """The decompiled body / longest string anywhere in the REA result, clipped."""
    best = ""
    stack = [nr]
    while stack:
        v = stack.pop()
        if isinstance(v, str) and len(v) > len(best):
            best = v
        elif isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, (list, tuple)):
            stack.extend(v)
    return _clip(best, n)


def _safe_call(rea: Session, tool: str, args: dict[str, Any], limits: list[str]) -> dict[str, Any]:
    try:
        return _nr(rea.call(tool, args))
    except ReaError as e:
        limits.append(f"{tool}: {str(e)[:160]}")
        return {}


# ---------------------------------------------------------------- overview (per kind)
def _ov_apk(rea: Session, staged: Path, name: str, out: dict[str, Any]) -> None:
    if not apk_ready():
        out["limits"].append("APK ke internals ke liye JADX (REA_JADX_JAR) server par set nahi hai; overview atak jaata hai.")
        return
    pkg = _safe_call(rea, "inspect_android_package", {"path": str(staged), "detail": "complete"}, out["limits"])
    man_text = ((pkg.get("manifest") or {}).get("text")) or ""
    man = an.manifest_facts(man_text)
    perms = [p if isinstance(p, str) else p.get("name", str(p)) for p in (pkg.get("permissions") or [])]
    out["facts"].update({
        "kind_label": "Android APK", "package": pkg.get("package_name") or "", "version": pkg.get("version_name") or "",
        "min_android_sdk": pkg.get("min_sdk") or "", "target_sdk": pkg.get("target_sdk") or "",
        "app_name": man.get("label") or "", "permissions": perms[:60],
        "activities": len(pkg.get("activities") or []), "services": len(pkg.get("services") or []),
        "receivers": len(pkg.get("receivers") or []), "providers": len(pkg.get("providers") or []),
        "classes": pkg.get("class_count"), "uses_internet": "android.permission.INTERNET" in perms,
        "components": [c.rsplit(".", 1)[-1] for c in (man.get("components") or [])][:40],
        "sms_receiver": man.get("sms_receiver"), "debuggable": man.get("debuggable"),
        "cleartext": man.get("cleartext"), "manifest": _clip(man_text, 1200),
    })
    sig = an.apk_signer(staged)
    cert = sig.get("cert") or {}
    out["facts"].update({"signed_by": cert.get("subject", ""), "signer_sha256": cert.get("sha256", ""),
                         "signature_schemes": sig.get("schemes")})
    sigv = _safe_call(rea, "inspect_apk_signature", {"path": str(staged), "detail": "summary"}, out["limits"])
    out["facts"]["signature"] = _compact(sigv, list_n=8)
    if _safe_call(rea, "identify_flutter_build", {"path": str(staged)}, out["limits"]).get("flutter_detected"):
        out["facts"]["built_with"] = "Flutter"
        d = _safe_call(rea, "inspect_dart_aot", {"abi": "arm64-v8a", "detail": "summary", "path": str(staged)}, out["limits"])
        out["facts"]["dart_aot"] = _compact(d, list_n=6)
    il = _safe_call(rea, "inspect_il2cpp_metadata", {"detail": "summary", "path": str(staged)}, out["limits"])
    if il:
        out["facts"]["built_with"] = "Unity (IL2CPP)"
        out["facts"]["il2cpp"] = _compact(il, list_n=6)
    out["next"].extend(["classes (query a name)", "class class_name=...", "method class_name=... method_name=...",
                         "refs class_name=...", "signature"])


def _ov_exe(rea: Session, staged: Path, out: dict[str, Any]) -> None:
    basics = an.pe_basics(staged)
    out["facts"].update({"kind_label": "Windows PE (EXE / DLL)", "architecture": basics.get("arch", ""),
                          "is_dll": basics.get("dll"), "has_signature": basics.get("signed")})
    out["facts"]["resources"] = _compact(_safe_call(rea, "inspect_pe_resources", {"path": str(staged)}, out["limits"]),
                                          list_n=10)
    out["facts"]["imports"] = _compact(_safe_call(rea, "inspect_pe_imports",
        {"path": str(staged), "max_dlls": 40, "max_functions": 200}, out["limits"]), list_n=20)
    out["facts"]["load_config"] = _compact(_safe_call(rea, "inspect_pe_load_config",
        {"path": str(staged), "max_callbacks": 20}, out["limits"]), list_n=10)
    if basics.get("signed"):
        out["facts"]["certificate"] = _compact(_safe_call(rea, "inspect_pe_certificates",
            {"path": str(staged), "max_entries": 8}, out["limits"]), list_n=6)
    m = _safe_call(rea, "inspect_managed_artifact", {"path": str(staged), "detail": "summary"}, out["limits"])
    cls = m.get("classification") or {}
    if cls.get("status") and cls.get("status") != "not-managed":
        out["facts"]["built_with"] = ".NET"
        out["facts"]["assembly"] = (m.get("assembly") or {}).get("name", "")
        mm = _safe_call(rea, "inspect_managed_members", {"path": str(staged), "detail": "summary"}, out["limits"])
        out["facts"]["managed_types"] = mm.get("type_count") or len(mm.get("types") or [])
    _deps(rea, staged, out)
    out["facts"]["exports"] = _compact(_safe_call(rea, "inspect_native_exports",
        {"path": str(staged), "detail": "summary"}, out["limits"]), list_n=20)
    out["next"].extend(["byte entropy tells if the body is packed/encrypted (read-only)"])


def _deps(rea: Session, staged: Path, out: dict[str, Any]) -> None:
    g = _safe_call(rea, "inspect_go_binary", {"path": str(staged)}, out["limits"])
    if g.get("build_info"):
        out["facts"]["built_with"] = "Go " + str((g.get("build_info") or {}).get("go_version") or
                                                  (g.get("build_info") or {}).get("version") or "").strip()
    r = _safe_call(rea, "inspect_rust_binary", {"path": str(staged)}, out["limits"])
    if r.get("packages"):
        out["facts"]["built_with"] = "Rust"
        out["facts"]["rust_crates"] = len(r.get("packages") or [])


def _ov_elf(rea: Session, staged: Path, out: dict[str, Any]) -> None:
    out["facts"]["kind_label"] = "Linux ELF (.so / executable / module)"
    out["facts"]["exports"] = _compact(_safe_call(rea, "inspect_native_exports",
        {"path": str(staged), "detail": "summary"}, out["limits"]), list_n=30)
    out["facts"]["notes"] = _compact(_safe_call(rea, "inspect_elf_notes",
        {"path": str(staged), "max_entries": 30}, out["limits"]), list_n=12)
    _deps(rea, staged, out)
    if staged.suffix.lower() == ".ko":
        km = _safe_call(rea, "inspect_kernel_module", {"path": str(staged), "max_entries": 30}, out["limits"])
        if km:
            out["facts"]["kernel_module"] = _compact(km, list_n=10)


def _ov_electron(rea: Session, staged: Path, out: dict[str, Any]) -> None:
    res = _nr(rea.call("analyze_javascript_application",
                        {"input_path": str(staged), "format": "auto", "detail": "summary",
                         "integrity_policy": "record-and-continue"}))
    counts = {k: v for k, v in res.items() if isinstance(v, int) and not isinstance(v, bool)}
    out["facts"].update({"kind_label": "Electron / JavaScript app", "built_with": "Electron / JS"})
    out["facts"].update({k: counts[k] for k in list(counts)[:12]})
    out["facts"]["graph"] = _compact(res, list_n=10)
    out["next"].append("trace_application_feature (a JS seed) is one of the deeper REA probes; not exposed here")


def _ov_one_shot(rea: Session, staged: Path, kind: str, out: dict[str, Any]) -> bool:
    """Return True if a kind matched. Static one-shots keyed by file extension / magic."""
    n, s = staged.name.lower(), staged.suffix.lower()
    p = {"path": str(staged)}
    try:
        if kind == "other" and s in (".db", ".sqlite", ".sqlite3"):
            r = rea.call("inspect_sqlite_database", {**p, "schema_scope": "all", "row_limit": 0,
                                                      "worker_timeout_ms": 60000})
            out["facts"].update({"kind_label": "SQLite database", "tables": _compact(_nr(r), list_n=30)}); return True
        if s in (".gguf", ".safetensors") or n.endswith(".gguf"):
            r = rea.call("inspect_model_artifact", {**p, "detail": "summary", "hash": "header"})
            out["facts"].update({"kind_label": "ML model artifact", "model": _compact(_nr(r))}); return True
        if s == ".beam":
            r = rea.call("inspect_erlang_beam", {**p, "detail": "summary"})
            out["facts"].update({"kind_label": "Erlang BEAM", "beam": _compact(_nr(r))}); return True
        if s == ".pyc":
            r = rea.call("inspect_python_pyc", {**p, "detail": "summary"})
            out["facts"].update({"kind_label": "CPython .pyc", "pyc": _compact(_nr(r))}); return True
        if n.endswith(".ips"):
            r = rea.call("inspect_apple_ips", {**p, "max_threads": 10, "max_frames": 20})
            out["facts"].update({"kind_label": "Apple .ips crash", "ips": _compact(_nr(r))}); return True
        if s == ".dtb":
            r = rea.call("inspect_devicetree", {**p, "detail": "summary", "max_nodes": 200})
            out["facts"].update({"kind_label": "devicetree blob", "fdt": _compact(_nr(r))}); return True
        if s == ".evm":
            r = rea.call("inspect_evm_interface", {**p, "encoding": "hex", "detail": "summary"})
            out["facts"].update({"kind_label": "EVM bytecode", "evm": _compact(_nr(r))}); return True
    except ReaError as e:
        out["limits"].append(str(e)[:200])
        return True
    return False


def overview(tenant: str, src: dict[str, Any]) -> dict[str, Any]:
    if not configured():
        raise KhojError("REA abhi server par chalu nahi hai (REA_BIN set karna hai).")
    name, path, kind = _stage(tenant, src)
    out: dict[str, Any] = {"name": name, "kind": kind, "size": path.stat().st_size,
                          "sha256": an.sha256_file(path), "facts": {}, "limits": [], "next": [], "engine": ""}
    if kind == "script":
        out["limits"].append("Yeh script file hai; bytes + entropy padh sakte hain, lekin RUN nahi karna safe hai.")
        with Session() as rea:
            out["engine"] = f"REA {rea.server_info.get('version', '')}".strip()
            staged = rea.stage(path, name)
            out["facts"]["entropy"] = _compact(_safe_call(rea, "inspect_byte_entropy", {"path": str(staged)}, out["limits"]))
        return out
    with Session() as rea:
        out["engine"] = f"REA {rea.server_info.get('version', '')}".strip()
        work = rea.work or path.parent
        staged = rea.stage(path, name)
        if kind == "apks":
            base, parts = an.base_apk(staged, work)
            out["facts"]["bundle_parts"] = len(parts)
            if base is None:
                out["limits"].append("Bundle ke andar main APK nahi mili.")
                return out
            staged, kind = base, "apk"
        try:
            if kind == "apk":
                _ov_apk(rea, staged, name, out)
            elif kind == "exe":
                _ov_exe(rea, staged, out)
            elif kind == "elf":
                _ov_elf(rea, staged, out)
            elif kind == "electron":
                _ov_electron(rea, staged, out)
            elif kind == "macho":
                out["limits"].append("Mac binary ke liye server par koi native engine (Hopper/Ghidra/IDA) nahi hai.")
                out["facts"]["entropy"] = _compact(_safe_call(rea, "inspect_byte_entropy", {"path": str(staged)}, out["limits"]))
            elif kind == "zip":
                out["facts"]["files_inside"] = len(an.zip_listing(staged))
                out["next"].append("zip ke andar koi program hai to use alag se overview dobara chalaiye (file_id)")
            else:
                if not _ov_one_shot(rea, staged, kind, out):
                    out["facts"]["entropy"] = _compact(_safe_call(rea, "inspect_byte_entropy", {"path": str(staged)}, out["limits"]))
                    out["limits"].append("Yeh file REA ke kisi special inspector se nahi match ki; sirf entropy dekhi.")
        except ReaError as e:
            out["limits"].append(str(e)[:300])
    out["limits"].append("File kabhi RUN nahi hui; jo likha hai woh uske bytes mein hai. Yeh jaankari hai, hukm nahi.")
    return out


# ---------------------------------------------------------------- APK deep-dive
def _stage_apk(tenant: str, src: dict[str, Any]) -> tuple[str, str, str]:
    name, path, kind = _stage(tenant, src)
    if kind == "apks":
        with Session() as rea:
            work = rea.work or path.parent
            staged = rea.stage(path, name)
            base, _ = an.base_apk(staged, work)
            if base is None:
                raise KhojError("Bundle ke andar main APK nahi mili.")
            return name, str(base), "apk"
    if kind != "apk":
        raise KhojError(f"Yeh action sirf APK par chalti hai; file kind = {kind}.")
    return name, str(path), kind


def classes(tenant: str, src: dict[str, Any], query: str) -> dict[str, Any]:
    if not configured():
        raise KhojError("REA abhi server par chalu nahi hai.")
    if not apk_ready():
        raise KhojError("APK deep-dive ke liye JADX (REA_JADX_JAR) set nahi hai.")
    name, p, kind = _stage_apk(tenant, src)
    with Session() as rea:
        nr = _nr(rea.call("search_android_classes", {"path": p, "query": query or ""}))
        rows = nr.get("classes") or nr.get("rows") or nr.get("results") or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        names = [r if isinstance(r, str) else (r.get("name") or r.get("class_name") or str(r)) for r in rows][:120]
        return {"name": name, "sha256": an.sha256_file(Path(p)), "kind": kind, "query": query or "",
                "count": len(names), "classes": names,
                "next": ["class class_name=<se ek> -> methods", "method class_name=... method_name=... -> decompiled body"]}


def klass(tenant: str, src: dict[str, Any], class_name: str) -> dict[str, Any]:
    if not configured() or not apk_ready():
        raise KhojError("REA / JADX abhi server par set nahi hai.")
    if not class_name:
        raise KhojError("Kaunsi class? class_name dijiye (overview ya classes se milta hai).")
    name, p, kind = _stage_apk(tenant, src)
    with Session() as rea:
        nr = _nr(rea.call("inspect_android_class", {"class_name": class_name, "path": p}))
        methods = nr.get("methods") or []
        fields = nr.get("fields") or []
        return {"name": name, "kind": kind, "class": class_name,
                "methods": [{"name": (m.get("name") if isinstance(m, dict) else m),
                              "signature": (m.get("signature") or m.get("display_signature") or "") if isinstance(m, dict) else "",
                              "overloads": (m.get("overload_count") or len(m.get("overloads") or [])) if isinstance(m, dict) else 1}
                             for m in methods][:60],
                "fields": [f if isinstance(f, str) else (f.get("name") or f.get("display_signature") or str(f))
                           for f in fields][:40],
                "inner": nr.get("inner_classes") or nr.get("inners") or [],
                "raw": _compact(nr, list_n=8),
                "next": ["method class_name=... method_name=<se ek> (overload_index agar same naam ke 2+ hain)"]}


def method(tenant: str, src: dict[str, Any], class_name: str, method_name: str,
          overload_index: int = 0) -> dict[str, Any]:
    if not configured() or not apk_ready():
        raise KhojError("REA / JADX abhi server par set nahi hai.")
    if not (class_name and method_name):
        raise KhojError("class_name aur method_name dono chahiye.")
    name, p, kind = _stage_apk(tenant, src)
    with Session() as rea:
        args = {"class_name": class_name, "method_name": method_name, "overload_index": overload_index, "path": p}
        nr = _nr(rea.call("inspect_android_method", args))
        src_text = _longest_text(nr, 6000)
        return {"name": name, "kind": kind, "class": class_name, "method": method_name,
                "overload_index": overload_index,
                "representation": nr.get("representation") or "",
                "fallback": nr.get("fallback") or nr.get("fallback_markers") or [],
                "source": src_text or "(no decompiled body returned; class_name/method_name/overload_index check karo)",
                "prototype": nr.get("prototype") or nr.get("dex_prototype") or "",
                "next": ["refs class_name=... [method_name=...] -> kaun use karta hai"]}


def refs(tenant: str, src: dict[str, Any], class_name: str, method_name: str = "",
         overload_index: int = 0) -> dict[str, Any]:
    if not configured() or not apk_ready():
        raise KhojError("REA / JADX abhi server par set nahi hai.")
    if not class_name:
        raise KhojError("class_name chahiye.")
    name, p, kind = _stage_apk(tenant, src)
    with Session() as rea:
        args: dict[str, Any] = {"class_name": class_name, "path": p}
        if method_name:
            args["method_name"] = method_name
            args["overload_index"] = overload_index
        nr = _nr(rea.call("trace_android_references", args))
        nodes = nr.get("incoming") or nr.get("nodes") or nr.get("references") or []
        if isinstance(nodes, dict):
            nodes = list(nodes.values())
        out = [n if isinstance(n, str) else (n.get("class_name") or n.get("name") or str(n)) for n in nodes][:60]
        return {"name": name, "kind": kind, "class": class_name, "method": method_name or None,
                "overload_index": overload_index if method_name else None,
                "count": len(out), "used_by": out,
                "raw": _compact(nr, list_n=6)}


def signature(tenant: str, src: dict[str, Any]) -> dict[str, Any]:
    if not configured():
        raise KhojError("REA abhi server par chalu nahi hai.")
    name, path, kind = _stage(tenant, src)
    if kind not in ("apk", "apks"):
        raise KhojError(f"Signature action APK par chalti hai; file kind = {kind}.")
    if kind == "apks":
        with Session() as rea:
            work = rea.work or path.parent
            staged = rea.stage(path, name)
            base, _ = an.base_apk(staged, work)
            if base is None:
                raise KhojError("Bundle ke andar main APK nahi mili.")
            path = base
    sig = an.apk_signer(path)
    cert = sig.get("cert") or {}
    out: dict[str, Any] = {"name": name, "kind": "apk", "sha256": an.sha256_file(path),
                           "signed_by": cert.get("subject", ""), "signer_sha256": cert.get("sha256", ""),
                           "schemes": sig.get("schemes"), "certificate": _compact(cert, list_n=8)}
    with Session() as rea:
        out["engine"] = f"REA {rea.server_info.get('version', '')}".strip()
        staged = rea.stage(path, name)
        out["rea_signature"] = _compact(_safe_call(rea, "inspect_apk_signature",
                                                    {"path": str(staged), "detail": "summary"}, out_limits := []), list_n=10)
    out["limits"] = ["Signature file mein likha hai; Android install ke waqt khud verify karta hai."]
    return out


KHOJ_ACTIONS = {"overview", "classes", "class", "method", "refs", "signature", "status"}


def run(tenant: str, src: dict[str, Any], action: str, **kw: Any) -> dict[str, Any]:
    if action not in KHOJ_ACTIONS:
        raise KhojError(f"Anknown action '{action}'. Use: {', '.join(sorted(KHOJ_ACTIONS))}.")
    if action == "overview":
        return overview(tenant, src)
    if action == "classes":
        return classes(tenant, src, kw.get("query") or "")
    if action == "class":
        return klass(tenant, src, kw.get("class_name") or "")
    if action == "method":
        return method(tenant, src, kw.get("class_name") or "", kw.get("method_name") or "",
                      int(kw.get("overload_index") or 0))
    if action == "refs":
        return refs(tenant, src, kw.get("class_name") or "", kw.get("method_name") or "",
                    int(kw.get("overload_index") or 0))
    if action == "signature":
        return signature(tenant, src)
    return status()
