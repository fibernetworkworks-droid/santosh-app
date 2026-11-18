"""v0.997 KHULA PITARA (owner, her BSNL Goa job: a RAR of 8 invoices that Hoola could not open, so it wrote the email
from other mails and guessed the months, the totals and her GST number). An archive she attaches - ZIP, RAR, 7z, TAR -
is opened on the SERVER the moment it arrives: every file inside becomes a file of her own (its own file_id, readable
with file_read like any PDF she sent, attachable to an email), and the archive's own read lists them.

Readers, in order: the standard library for ZIP and TAR (always there), libarchive (RAR4 / RAR5 / 7z / ISO / CAB...;
the `libarchive-c` package over the system libarchive), then `rarfile` when an unrar / bsdtar / 7z program exists.
None of them = the archive is reported as NOT OPENED, with the reason - never an empty "nothing inside".

Walls: no path ever leaves the archive (names are flattened, `..` and absolute paths dropped), at most MAX_MEMBERS
files, MAX_MEMBER bytes each and MAX_TOTAL bytes in all (a zip bomb stops at the wall, said), a password-protected
archive is said as such (her password is never asked for in chat), a program inside is listed but never extracted.
"""
from __future__ import annotations

import io
import logging
import tarfile
import zipfile
from pathlib import PurePosixPath
from typing import Any

log = logging.getLogger("santosh.archive")

EXTS = (".zip", ".rar", ".7z", ".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".gz", ".cab", ".iso")
MAX_MEMBERS = 40
MAX_MEMBER = 30 * 1024 * 1024
MAX_TOTAL = 120 * 1024 * 1024


class ArchiveError(Exception):
    pass


def is_archive(name: str, data: bytes = b"") -> bool:
    low = (name or "").lower()
    if low.endswith((".docx", ".xlsx", ".pptx", ".xlsm", ".odt", ".ods", ".odp", ".epub", ".apk", ".jar", ".aab",
                     ".ipa", ".whl")):
        return False                      # zip-shaped documents / programs are not "an archive she sent"
    if low.endswith(EXTS):
        return True
    head = data[:8]
    return head.startswith((b"Rar!\x1a\x07", b"7z\xbc\xaf\x27\x1c"))


def _clean(name: str) -> str:
    parts = [p for p in PurePosixPath(str(name).replace("\\", "/")).parts if p not in ("", ".", "..", "/")]
    return "/".join(parts)[-180:]


_PROGRAM_EXT = (".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".scr", ".msi", ".com", ".pif", ".sh", ".js",
                ".jse", ".wsf", ".hta", ".lnk", ".jar", ".apk", ".elf", ".bin", ".run")


def _program(name: str, data: bytes) -> bool:
    """A program inside her archive is listed, never opened or handed on: by its name, by its first bytes (MZ = a
    Windows program, ELF = a Linux one, a #! script) and by filecheck's own verdict."""
    if name.lower().endswith(_PROGRAM_EXT) or data[:2] == b"MZ" or data[:4] == b"\x7fELF" or data[:2] == b"#!":
        return True
    try:
        from . import filecheck
        rt = filecheck.real_type(name, data)
        return bool(rt.get("danger")) or rt.get("group") == "program"
    except Exception:
        return False


class _Sink:
    """Collects members inside the walls; says what the walls stopped."""

    def __init__(self) -> None:
        self.files: list[tuple[str, bytes]] = []
        self.skipped: list[dict[str, str]] = []
        self.total = 0
        self.full = False

    def add(self, name: str, size: int, read) -> None:
        clean = _clean(name)
        if not clean or clean.endswith("/"):
            return
        if len(self.files) >= MAX_MEMBERS:
            self.full = True
            self.skipped.append({"name": clean, "why": f"more than {MAX_MEMBERS} files in the archive"})
            return
        if size and size > MAX_MEMBER:
            self.skipped.append({"name": clean, "why": f"over {MAX_MEMBER // 1024 // 1024} MB"})
            return
        if self.total + (size or 0) > MAX_TOTAL:
            self.full = True
            self.skipped.append({"name": clean, "why": f"the archive opens to over {MAX_TOTAL // 1024 // 1024} MB"})
            return
        data = read()
        if len(data) > MAX_MEMBER:
            self.skipped.append({"name": clean, "why": f"over {MAX_MEMBER // 1024 // 1024} MB"})
            return
        if _program(clean, data):
            self.skipped.append({"name": clean, "why": "a program - listed, never opened"})
            return
        self.total += len(data)
        self.files.append((clean, data))


def _zip(data: bytes, sink: _Sink) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for i in z.infolist():
            if i.is_dir():
                continue
            if i.flag_bits & 0x1:
                raise ArchiveError("password")
            sink.add(i.filename, i.file_size, lambda i=i: z.read(i))


def _tar(data: bytes, sink: _Sink) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
        for m in t.getmembers():
            if not m.isfile():
                continue                   # links, devices and folders are never followed
            sink.add(m.name, m.size, lambda m=m: t.extractfile(m).read())


def _libarchive(data: bytes, sink: _Sink) -> None:
    import libarchive                      # libarchive-c over the system libarchive (RAR4 / RAR5 / 7z / ISO / CAB)
    with libarchive.memory_reader(data) as arc:
        for e in arc:
            if not e.isfile:
                continue
            blocks: list[bytes] = []
            size = int(e.size or 0)

            def read(e=e, blocks=blocks):
                n = 0
                for b in e.get_blocks():
                    n += len(b)
                    if n > MAX_MEMBER:
                        break
                    blocks.append(bytes(b))
                return b"".join(blocks)
            sink.add(e.pathname, size, read)


def _rarfile(data: bytes, sink: _Sink) -> None:
    import rarfile                         # needs an unrar / unar / bsdtar / 7z program on the server
    with rarfile.RarFile(io.BytesIO(data)) as r:
        if r.needs_password():
            raise ArchiveError("password")
        for i in r.infolist():
            if i.is_dir():
                continue
            sink.add(i.filename, i.file_size, lambda i=i: r.read(i))


_LOCKED = ("The archive is locked with a password, so nothing inside was read. Ask her to send the files without the "
           "password (or unzip them and send the PDFs) - never ask for the password in chat.")


def open_archive(name: str, data: bytes) -> dict[str, Any]:
    """{ok, files: [(name, bytes)], skipped: [{name, why}], reader, note} - or ok False with the plain reason."""
    low = (name or "").lower()
    readers = []
    if zipfile.is_zipfile(io.BytesIO(data)):
        readers.append(("zip", _zip))
    elif low.endswith((".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        readers.append(("tar", _tar))
    readers += [("libarchive", _libarchive), ("rarfile", _rarfile)]
    tried: list[str] = []
    for label, fn in readers:
        sink = _Sink()
        try:
            fn(data, sink)
        except ArchiveError as e:
            if str(e) == "password":
                return {"ok": False, "files": [], "skipped": [], "reader": label, "note": _LOCKED}
            tried.append(f"{label}: {e}")
            continue
        except ImportError as e:
            tried.append(f"{label}: not installed ({e.name or e})")
            continue
        except OSError as e:                    # libarchive-c present but the system libarchive is missing
            tried.append(f"{label}: {str(e)[:120]}")
            continue
        except Exception as e:
            if any(w in str(e).lower() for w in ("encrypt", "passphrase", "password")):
                return {"ok": False, "files": [], "skipped": [], "reader": label, "note": _LOCKED}
            tried.append(f"{label}: {type(e).__name__}: {str(e)[:160]}")
            continue
        if not sink.files and not sink.skipped:
            tried.append(f"{label}: nothing inside")
            continue
        note = ""
        if sink.full:
            note = f"Only the first {len(sink.files)} files were opened (the archive is bigger than Hoola opens at once)."
        return {"ok": True, "files": sink.files, "skipped": sink.skipped, "reader": label, "note": note}
    log.warning("archive %s not opened: %s", name, "; ".join(tried))
    return {"ok": False, "files": [], "skipped": [], "reader": "",
            "note": "Hoola could not open this archive on the server (" + "; ".join(tried)[:400] + "). Tell her "
                    "plainly that the files inside were NOT read, and ask her to send them unzipped (or as a ZIP). "
                    "Never fill in its contents from anywhere else."}


def unpack(tenant: str, name: str, data: bytes) -> dict[str, Any]:
    """Open the archive and store every file inside as her own file. -> {ok, inside: [{name, file_id, size}],
    skipped, note}. Never raises."""
    try:
        res = open_archive(name, data)
    except Exception as e:                          # pragma: no cover - open_archive already catches
        res = {"ok": False, "files": [], "skipped": [], "note": f"could not open: {e}"}
    out: dict[str, Any] = {"ok": res["ok"], "inside": [], "skipped": res.get("skipped") or [], "note": res.get("note", "")}
    if not res["ok"]:
        return out
    from .mailbox import service as ms
    import hashlib
    seen: dict[str, int] = {}
    hashes: dict[str, str] = {}
    for member, blob in res["files"]:
        base = member.rsplit("/", 1)[-1] or "file"
        if base in seen:                                # two files of one name in different folders: keep both
            seen[base] += 1
            stem, dot, ext = base.rpartition(".")
            base = f"{stem or ext} ({seen[base]}){dot + ext if stem else ''}"
        else:
            seen[base] = 1
        try:
            row = ms.store_bytes(tenant, base, blob, "mail")
        except Exception as e:
            out["skipped"].append({"name": member, "why": f"could not be kept: {e}"})
            continue
        item = {"name": base, "path": member, "file_id": row.id, "size": len(blob)}
        h = hashlib.sha256(blob).hexdigest()
        if h in hashes:                                 # the same file twice (her BSNL RAR had 2 copies): said once
            item["same_as"] = hashes[h]
        else:
            hashes[h] = base
        out["inside"].append(item)
    return out
