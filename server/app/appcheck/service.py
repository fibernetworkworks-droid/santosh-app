"""App Jaanch: "is this APK / EXE safe to install?" Static checks only, through REA; the file is never run."""
from __future__ import annotations

import datetime as dt
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import session
from ..events import bus
from . import analyze as an
from .models import AppCheck
from .runner import ReaError, Session, apk_ready, configured

ORDER = {"high": 0, "medium": 1, "low": 2}


class CheckError(Exception):
    pass


def status() -> dict[str, Any]:
    return {"enabled": configured(), "apk": apk_ready(), "max_mb": get_settings().appcheck_max_mb}


# ---------------------------------------------------------------- where the file comes from
def _resolve(tenant: str, src: dict[str, Any]) -> tuple[str, Path, Path | None]:
    """-> (name, path, temp_dir_to_clean)"""
    from ..mailbox import service as ms
    if src.get("file_id"):
        try:
            f = ms._file_row(tenant, str(src["file_id"]))
        except ms.MailError as e:
            raise CheckError(str(e))
        p = Path(f.stored_path)
        if not p.is_file():
            raise CheckError("Yeh file ab server par nahi hai (24 ghante baad hat jaati hai); dobara bhejiye.")
        return f.name, p, None
    tmp = Path(tempfile.mkdtemp(prefix="chk_src_"))
    try:
        if src.get("email_id"):
            if src.get("attachment_id") in (None, ""):
                raise CheckError("Email ka kaunsa attachment jaanchna hai? (attachment_id)")
            try:
                name, _mt, data = ms.attachment(tenant, str(src["email_id"]), str(src["attachment_id"]))
            except ms.MailError as e:
                raise CheckError(str(e))
        elif src.get("drive"):
            from ..drive import service as dsv
            try:
                c, f = dsv.resolve(tenant, str(src["drive"]))
                name, _mt, data, _c, _f = dsv.fetch(tenant, dsv.make_ref(c, f["id"]))
            except Exception as e:
                raise CheckError(f"Drive se file nahi mili: {str(e)[:150]}")
        else:
            raise CheckError("Kaunsi file? file_id (phone / PC se aayi file), email attachment ya Drive file dijiye.")
        if len(data) > get_settings().appcheck_max_mb * 1024 * 1024:
            raise CheckError(f"File {get_settings().appcheck_max_mb} MB se badi hai.")
        from ..pc.service import safe_name
        p = tmp / safe_name(name)
        p.write_bytes(data)
        return name, p, tmp
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


# ---------------------------------------------------------------- per kind
def _nr(res: dict[str, Any]) -> dict[str, Any]:
    nr = res.get("normalized_result") or {}
    return nr.get("summary") if isinstance(nr.get("summary"), dict) and nr.get("kind") == "summary" else nr


def _check_apk(rea: Session, path: Path, name: str, out: dict[str, Any]) -> list[dict[str, str]]:
    res = rea.call("inspect_android_package", {"path": str(path), "detail": "complete"})
    pkg = _nr(res)
    man_text = ((pkg.get("manifest") or {}).get("text")) or ""
    man = an.manifest_facts(man_text)
    signer = an.apk_signer(path)
    cert = signer.get("cert") or {}
    out["facts"].update({
        "package": pkg.get("package_name") or "", "version": pkg.get("version_name") or "",
        "min_android_sdk": pkg.get("min_sdk") or "", "target_sdk": pkg.get("target_sdk") or "",
        "app_name": man.get("label") or "", "permissions": pkg.get("permissions") or [],
        "has_app_icon": man.get("launcher"), "special_powers": [c.rsplit(".", 1)[-1] for c in man.get("components") or []],
        "signed_by": cert.get("subject", ""), "signer_sha256": cert.get("sha256", ""), "signature_schemes": signer.get("schemes"),
        "classes": pkg.get("class_count"),
    })
    try:
        fl = _nr(rea.call("identify_flutter_build", {"path": str(path)}))
        if fl.get("flutter_detected"):
            out["facts"]["built_with"] = "Flutter"
    except ReaError:
        pass
    out["limits"].append("Signature kisne kiya yeh file mein likha hua dikhaya hai; asli jaanch Android install ke waqt karta hai.")
    return an.apk_flags(pkg, man, signer, name)


def _check_exe(rea: Session, path: Path, name: str, out: dict[str, Any]) -> list[dict[str, str]]:
    basics = an.pe_basics(path)
    vinfo: dict[str, str] = {}
    level = ""
    try:
        pe = _nr(rea.call("inspect_pe_resources", {"path": str(path)}))
        vinfo, level = an.pe_version_info(path, pe.get("resources") or [])
    except ReaError as e:
        out["limits"].append(f"Resources nahi padh paaye: {str(e)[:120]}")
    out["facts"].update({"company": vinfo.get("CompanyName", ""), "product": vinfo.get("ProductName", ""),
                         "description": vinfo.get("FileDescription", ""), "original_name": vinfo.get("OriginalFilename", ""),
                         "version": vinfo.get("FileVersion", "") or vinfo.get("ProductVersion", ""),
                         "architecture": basics.get("arch", ""), "is_dll": basics.get("dll"),
                         "has_signature": basics.get("signed"), "asks_admin": level == "requireAdministrator"})
    try:
        m = _nr(rea.call("inspect_managed_artifact", {"path": str(path), "detail": "summary"}))
        cls = m.get("classification") or {}
        if cls.get("status") and cls.get("status") != "not-managed":
            out["facts"]["built_with"] = ".NET"
            asm = m.get("assembly") or {}
            if isinstance(asm, dict) and asm.get("name"):
                out["facts"]["assembly"] = asm.get("name")
    except ReaError:
        pass
    _deps(rea, path, out)
    if basics.get("signed"):
        out["limits"].append("Digital signature maujood hai; Windows khud jaanchega ki woh sahi company ka hai ya nahi.")
    return an.exe_flags(name, basics, vinfo, level)


def _deps(rea: Session, path: Path, out: dict[str, Any]) -> None:
    try:
        go = _nr(rea.call("inspect_go_binary", {"path": str(path)}))
        bi = go.get("build_info") or {}
        if bi:
            out["facts"]["built_with"] = "Go " + str(bi.get("go_version") or bi.get("version") or "").strip()
    except ReaError:
        pass
    try:
        rs = _nr(rea.call("inspect_rust_binary", {"path": str(path)}))
        pk = rs.get("packages") or []
        if pk:
            out["facts"]["built_with"] = "Rust"
            out["facts"]["rust_crates"] = len(pk)
    except ReaError:
        pass


def _check_electron(rea: Session, path: Path, out: dict[str, Any]) -> list[dict[str, str]]:
    res = _nr(rea.call("analyze_javascript_application", {"input_path": str(path), "format": "auto", "detail": "summary",
                                                         "integrity_policy": "record-and-continue"}))
    counts = {k: v for k, v in res.items() if isinstance(v, int) and not isinstance(v, bool)}
    out["facts"].update({"built_with": "Electron / JavaScript", **{k: counts[k] for k in list(counts)[:8]}})
    out["limits"].append("JavaScript app ka structure dekha; is tarah ke apps ke liye koi pakka khatra-niyam nahi lagaya.")
    return []


def _run(name: str, path: Path, kind: str, out: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    if an.double_extension(name):
        flags.append(an._flag("high", "naam document / photo jaisa hai par asal mein program hai (do extension wali chaal)", "double_ext"))
    if kind == "script":
        lvl = an.SCRIPT_EXT.get(Path(name.lower()).suffix, "medium")
        flags.append(an._flag(lvl, f"'{Path(name).suffix}' file kholte hi commands chalati hai", "script"))
        b, lu = an.name_lures(name)
        if b or lu:
            flags.append(an._flag("high", f"naam mein '{', '.join(b + lu)}' hai: aisi files aam fraud tareeka hain", "lure_name"))
        return flags
    if kind == "other":
        out["limits"].append("Yeh APK / EXE / app file nahi lagti; App Jaanch sirf apps aur programs padhta hai.")
        return flags
    if kind == "macho":
        out["limits"].append("Mac app ki gehri jaanch abhi server par nahi hoti.")
        return flags
    with Session() as rea:
        out["engine"] = f"REA {rea.server_info.get('version', '')}".strip()
        work = rea.work or path.parent
        if kind == "zip":
            items = an.zip_listing(path)
            out["facts"]["files_inside"] = len(items)
            inner = [i for i in items if Path(i["name"].lower()).suffix in (".apk", ".exe", ".scr", ".msi", ".js", ".vbs",
                                                                              ".bat", ".cmd", ".ps1", ".hta", ".lnk", ".jar")]
            if inner:
                out["facts"]["programs_inside"] = [i["name"] for i in inner[:10]]
                flags.append(an._flag("medium", f"zip ke andar program hai: {', '.join(Path(i['name']).name for i in inner[:3])}",
                                      "zip_program"))
                for i in inner[:3]:
                    if an.double_extension(Path(i["name"]).name):
                        flags.append(an._flag("high", f"andar '{Path(i['name']).name}' document jaisa naam wala program hai", "double_ext"))
            return flags
        staged = rea.stage(path, name)
        if kind == "apks":
            base, parts = an.base_apk(staged, work)
            out["facts"]["bundle_parts"] = len(parts)
            if base is None:
                out["limits"].append("Bundle ke andar main APK nahi mila.")
                return flags
            staged, kind = base, "apk"
        if kind == "apk":
            if not apk_ready():
                out["limits"].append("APK ki jaanch ke liye server par JADX (REA_JADX_JAR) set nahi hai.")
                return flags
            return flags + _check_apk(rea, staged, name, out)
        if kind == "exe":
            return flags + _check_exe(rea, staged, name, out)
        if kind == "elf":
            _deps(rea, staged, out)
            return flags
        if kind == "electron":
            return flags + _check_electron(rea, staged, out)
    return flags


# ---------------------------------------------------------------- public
def check(tenant: str, conversation_id: str, src: dict[str, Any]) -> dict[str, Any]:
    if not configured():
        raise CheckError("App Jaanch abhi server par chalu nahi hai (REA install karke REA_BIN set karna hai).")
    name, path, tmp = _resolve(tenant, src)
    try:
        size = path.stat().st_size
        if size > get_settings().appcheck_max_mb * 1024 * 1024:
            raise CheckError(f"File {get_settings().appcheck_max_mb} MB se badi hai.")
        sha = an.sha256_file(path)
        since = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=30)
        with session() as s:
            old = s.scalars(select(AppCheck).where(AppCheck.tenant_id == tenant, AppCheck.sha256 == sha,
                                                   AppCheck.created_at >= since, AppCheck.verdict != "unknown")
                            .order_by(AppCheck.created_at.desc())).first()
            cached = dict(old.result) | {"id": old.id, "name": name, "cached": True} if old is not None else None
        if cached is not None:
            _publish(conversation_id, cached)
            return cached
        kind = an.sniff(path, name)
        out: dict[str, Any] = {"name": name, "kind": kind, "size": size, "sha256": sha, "facts": {}, "limits": [], "engine": ""}
        try:
            flags = _run(name, path, kind, out)
            v = an.verdict(flags) if (flags or out["facts"]) else "unknown"
        except ReaError as e:
            flags, v = [], "unknown"
            out["limits"].append(str(e)[:300])
        flags.sort(key=lambda f: ORDER.get(f["level"], 3))
        if kind == "zip" and v == "clear":
            v = "caution" if out["facts"].get("programs_inside") else "clear"
        out.update({"verdict": v, "verdict_text": an.VERDICT_TEXT[v], "flags": flags,
                    "advice": an.ADVICE.get("apk" if kind in ("apk", "apks") else "exe" if kind in ("exe", "zip") else
                                            "script" if kind == "script" else "", "")})
        with session() as s:
            row = AppCheck(tenant_id=tenant, name=name[:300], sha256=sha, kind=kind, verdict=v, result=out)
            s.add(row)
            s.flush()
            out["id"] = row.id
        _publish(conversation_id, out)
        return out
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def _publish(conv: str, out: dict[str, Any]) -> None:
    if not conv:
        return
    f = out.get("facts") or {}
    keep = ("package", "version", "app_name", "signed_by", "company", "product", "description", "built_with", "architecture",
            "files_inside")
    bus.publish(conv, "app_check", {"id": out.get("id"), "name": out.get("name"), "kind": out.get("kind"),
                                    "verdict": out.get("verdict"), "verdict_text": out.get("verdict_text"),
                                    "flags": [{"level": x["level"], "text": x["text"]} for x in (out.get("flags") or [])[:10]],
                                    "facts": {k: f[k] for k in keep if f.get(k) not in (None, "", [])},
                                    "permissions": len(f.get("permissions") or []), "advice": out.get("advice", ""),
                                    "limits": (out.get("limits") or [])[:3], "sha256": out.get("sha256", "")})


def history(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(AppCheck).where(AppCheck.tenant_id == tenant).order_by(AppCheck.created_at.desc()).limit(limit)).all()
        return [{"id": r.id, "name": r.name, "kind": r.kind, "verdict": r.verdict, "when": r.created_at.isoformat(),
                 "flags": len((r.result or {}).get("flags") or [])} for r in rows]


def get(tenant: str, cid: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(AppCheck, cid)
        if r is None or r.tenant_id != tenant:
            raise CheckError("Yeh jaanch nahi mili.")
        return dict(r.result) | {"id": r.id}
