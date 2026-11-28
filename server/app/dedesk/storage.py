"""A table's files read from a listing - `aws s3 ls --recursive`, `gsutil ls -l`, `hdfs dfs -ls -R` / `du`, `az storage blob list`
output, or a CSV of path and size: total size, how many files and how big, the small-file problem (and how many files would be
left after compacting to her target size), partitions found from key=value folders and how lopsided they are, file formats and
uncompressed text, and what a full scan costs at her price per TB scanned."""
from __future__ import annotations

import re
import statistics as stx
from collections import defaultdict
from typing import Any

from .common import DeInputError, finder, finish, human, size_bytes

MB = 1024 ** 2


class StorageError(DeInputError):
    pass


_EXT = {"parquet": "parquet", "pq": "parquet", "orc": "orc", "avro": "avro", "csv": "csv", "tsv": "csv", "json": "json", "jsonl": "json", "ndjson": "json",
        "txt": "text", "gz": "gzip", "snappy": "parquet", "zst": "zstd", "bz2": "bzip2", "delta": "delta", "crc": "meta", "xlsx": "excel"}


def _line(line: str) -> tuple[str, float] | None:
    s = line.strip()
    if not s or s.startswith(("Found ", "TOTAL:", "Total ")):
        return None
    toks = s.replace("\t", " ").split()
    if "," in s and len(toks) <= 2 or (s.count(",") >= 1 and not re.search(r"\s\d", s)):
        parts = [p.strip().strip('"') for p in s.split(",")]
        if len(parts) >= 2:
            for a, b in ((parts[0], parts[1]), (parts[1], parts[0])):
                n = size_bytes(b)
                if n is not None and not re.fullmatch(r"[\d.]+\s*\w*", a):
                    return a, n
            return None
    # aws: 2026-01-01 10:00:00   12345 path   |  gsutil: 12345  2026-01-01T..Z  gs://..  |  hdfs ls: -rw-r--r-- 3 u g 12345 2026-01-01 10:00 /p
    path = toks[-1]
    nums = [t for t in toks[:-1] if re.fullmatch(r"\d+(\.\d+)?", t)]
    sized = [t for t in toks[:-1] if re.fullmatch(r"\d+(\.\d+)?\s*[KMGT]i?B?", t, re.I)]
    if len(toks) >= 2 and re.fullmatch(r"[\d.]+\s*[KMGT]?i?B?", toks[0], re.I) and size_bytes(toks[0]) is not None and len(toks) in (2, 3) and not re.fullmatch(r"\d{4}-\d\d-\d\d", toks[0]):
        n = size_bytes(toks[0] + (toks[1] if len(toks) == 3 and re.fullmatch(r"[KMGT]i?B?", toks[1], re.I) else ""))
        return path, n
    if sized:
        return path, size_bytes(sized[-1])
    if s.startswith(("-", "d")) and len(toks) >= 8:
        if s.startswith("d"):
            return None
        return path, float(toks[4])
    if nums:
        big = [float(x) for x in nums if not re.fullmatch(r"\d{4}", x)]
        if big:
            return path, max(big)
    return None


def analyse(text: str, small_mb: float = 32, target_mb: float = 256, price_tb: float | None = None) -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise StorageError("Paste a file listing: aws s3 ls --recursive, gsutil ls -l, hdfs dfs -ls -R or a CSV of path,size.")
    files = []
    skipped = 0
    for i, line in enumerate(t.splitlines()):
        if i == 0 and re.match(r"(?i)^\s*(path|key|name|file)\s*,\s*(size|bytes)", line):
            continue
        r = _line(line)
        if r is None:
            if line.strip():
                skipped += 1
            continue
        p, n = r
        if p.endswith("/") or n is None:
            continue
        name = p.rsplit("/", 1)[-1]
        if name.startswith(("_", ".")) and not name.startswith("_delta_log"):
            continue
        files.append((p, n))
    if not files:
        raise StorageError("No files with a size found in that listing.")
    issues, add = finder()
    sizes = [n for _, n in files]
    total = sum(sizes)
    small = [n for n in sizes if n < small_mb * MB]
    fmts: dict[str, list[float]] = defaultdict(list)
    for p, n in files:
        name = p.rsplit("/", 1)[-1].lower()
        parts = name.split(".")
        ext = parts[-1] if len(parts) > 1 else ""
        f = _EXT.get(ext, ext or "none")
        if f in ("gzip", "zstd", "bzip2") and len(parts) > 2:
            f = _EXT.get(parts[-2], parts[-2]) + "+" + f
        if f == "parquet" and "snappy" in parts:
            f = "parquet"
        fmts[f].append(n)
    parts_: dict[str, list[float]] = defaultdict(list)
    keys: list[str] = []
    for p, n in files:
        segs = [s for s in p.split("/")[:-1] if re.fullmatch(r"[\w\-]+=[^/]*", s)]
        if segs:
            if not keys:
                keys = [s.split("=")[0] for s in segs]
            parts_["/".join(segs)].append(n)
    res: dict[str, Any] = {"files": len(files), "total": total, "total_h": human(total), "median": stx.median(sizes), "mean": total / len(files),
                           "max": max(sizes), "min": min(sizes), "small": len(small), "small_mb": small_mb, "target_mb": target_mb,
                           "after": max(1, round(total / (target_mb * MB) + 0.4999)), "formats": {k: {"files": len(v), "bytes": sum(v)} for k, v in sorted(fmts.items(), key=lambda x: -sum(x[1]))},
                           "skipped": skipped}
    edges = [0, 1 * MB, 8 * MB, 32 * MB, 128 * MB, 512 * MB, 2048 * MB, float("inf")]
    labels = ["< 1 MB", "1-8 MB", "8-32 MB", "32-128 MB", "128-512 MB", "512 MB-2 GB", "> 2 GB"]
    res["hist"] = [[labels[i], sum(1 for n in sizes if edges[i] <= n < edges[i + 1])] for i in range(len(labels))]
    if parts_:
        ps = sorted(((k, sum(v), len(v)) for k, v in parts_.items()), key=lambda x: -x[1])
        pb = [x[1] for x in ps]
        res["partitions"] = {"keys": keys, "count": len(ps), "median": stx.median(pb), "max": pb[0], "files_median": stx.median([x[2] for x in ps]),
                             "top": [{"partition": k, "bytes": b, "files": c} for k, b, c in ps[:15]], "small": sum(1 for b in pb if b < small_mb * MB)}
        med = stx.median(pb)
        if med and pb[0] > 10 * med and len(ps) >= 5:
            add("warn", "Skew", f"The largest partition ({ps[0][0]}) is {pb[0] / med:.0f}x the median - one task does most of the work.",
                "Split it further (another key, or bucketing) or salt the hot key.", ps[0][0])
        if len(ps) > 10000:
            add("warn", "Partitions", f"{len(ps):,} partitions - planning and listing them gets slow.", "Partition on fewer, coarser columns (e.g. day, not hour).")
        if res["partitions"]["small"] > 0.5 * len(ps) and len(ps) >= 10:
            add("warn", "Partitions", f"{res['partitions']['small']:,} of {len(ps):,} partitions hold under {small_mb:g} MB in all - the table is cut too finely.",
                "Use a coarser partition key.")
    share = len(small) / len(files)
    if share > 0.5 and len(files) >= 20:
        add("bad" if share > 0.8 else "warn", "Small files", f"{len(small):,} of {len(files):,} files ({share * 100:.0f}%) are under {small_mb:g} MB (median {human(res['median'])}).",
            f"Compact to ~{target_mb:g} MB files: about {res['after']:,} files instead of {len(files):,} (OPTIMIZE / rewrite_data_files / coalesce before writing).")
    big = [n for n in sizes if n > 2048 * MB]
    if big:
        add("info", "Big files", f"{len(big)} file(s) over 2 GB - fewer readers can work on the table in parallel.", "Aim for 128 MB - 1 GB files.")
    text_bytes = sum(v["bytes"] for k, v in res["formats"].items() if k in ("csv", "json", "text"))
    if text_bytes > 0.2 * total:
        add("warn", "Format", f"{human(text_bytes)} ({text_bytes / total * 100:.0f}%) is uncompressed CSV / JSON - scans read all of it.",
            "Store it as Parquet (or ORC) with compression: typically several times smaller and only the columns asked for are read.")
    if price_tb:
        res["scan_cost"] = total / 1024 ** 4 * price_tb
        res["price_tb"] = price_tb
    res["verdict"] = f"{len(files):,} files, {human(total)}, median {human(res['median'])}" + (f", {res['partitions']['count']:,} partitions" if parts_ else "")
    res["note"] = "Read from the listing only - sizes are on storage (compressed); the warehouse may bill a different number of bytes."
    return finish(res, issues)
