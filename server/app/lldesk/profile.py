"""A profile read for where the time goes: perf report --stdio (with or without children), folded stacks (Brendan Gregg's
stackcollapse format, the input of a flame graph), or perf stat counters. Time is grouped into what costs latency - allocation and
GC, locks and waiting, the kernel and system calls, page faults, copying, the scheduler, the network stack, logging, serialisation -
and perf stat's counters are read into IPC, cache and branch misses, context switches and CPU migrations. Pasted text is data."""
from __future__ import annotations

import re
from typing import Any


class ProfileError(ValueError):
    pass


CATS = [("alloc", "Allocation and GC", r"\b(?:malloc|free|calloc|realloc|_int_malloc|_int_free|tcache|operator new|operator delete|je_|mi_|tc_|arena_|"
                                       r"runtime\.mallocgc|runtime\.gc|runtime\.scanobject|runtime\.markroot|runtime\.sweep|gcBgMarkWorker|G1|ZGC|Shenandoah|"
                                       r"CollectedHeap|PSScavenge|GenCollect|__rust_alloc|__rust_dealloc)", 5.0),
        ("lock", "Locks and waiting", r"(?:futex|pthread_mutex|pthread_cond|__lll_lock|lll_lock|runtime\.lock|runtime\.semacquire|runtime\.park|"
                                      r"std::mutex|parking_lot|Unsafe\.park|LockSupport|ObjectMonitor|osq_lock|queued_spin_lock|native_queued_spin)", 3.0),
        ("fault", "Page faults", r"(?:page_fault|exc_page_fault|handle_mm_fault|do_anonymous_page|clear_page|__do_fault|do_page_fault)", 1.0),
        ("sched", "The scheduler", r"(?:\bschedule\b|__schedule|finish_task_switch|pick_next_task|try_to_wake_up|ttwu_|__switch_to|"
                                   r"runtime\.schedule|runtime\.findrunnable|runtime\.mcall|runtime\.gopark)", 3.0),
        ("net", "The network stack", r"(?:tcp_|udp_|ip_rcv|ip_output|ip_finish|__netif|netif_|napi_|__dev_queue|dev_hard_start|skb_|sock_|inet_|__sys_sendto|"
                                     r"__sys_recvfrom|epoll_wait|ep_poll)", 15.0),
        ("copy", "Copying memory", r"(?:memcpy|memmove|__memcpy|__memmove|copy_user|copy_to_user|copy_from_user|_copy_to_iter|_copy_from_iter|rep_movs)", 8.0),
        ("log", "Logging and formatting", r"(?:vfprintf|__vfprintf|printf|fwrite|_IO_|spdlog|log4j|Logger|fmt::|std::ostream|format_|strftime|"
                                          r"__strftime|\bsnprintf)", 3.0),
        ("ser", "Serialisation", r"(?:json|Json|JSON|protobuf|google::protobuf|serde|rapidjson|nlohmann|simdjson|Jackson|Gson|msgpack|encoding/json|"
                                 r"proto\.Marshal|proto\.Unmarshal)", 8.0),
        ("sys", "Kernel and system calls", r"(?:\[k\]|entry_SYSCALL|do_syscall|syscall_|__x64_sys|__arm64_sys|el0_svc|_raw_spin|irq_|"
                                           r"__softirq|do_softirq|asm_sysvec|\bsyscall\b|vdso)", 20.0)]
WHY = {"alloc": "allocating and freeing, or collecting garbage, on the hot path",
       "lock": "threads waiting for each other",
       "fault": "touching memory for the first time - the kernel maps a page while the request waits",
       "sched": "threads being put to sleep and woken - each wake-up costs microseconds",
       "net": "the kernel's network path",
       "copy": "copying bytes from one buffer to another",
       "log": "writing logs or formatting text",
       "ser": "encoding and decoding messages",
       "sys": "inside the kernel"}
FIX = {"alloc": "Pool or pre-allocate what the hot path uses; for GC languages allocate less per request (and size the young generation / GOGC for it).",
       "lock": "Fewer shared locks: one owner thread, sharded state or a lock-free ring.",
       "fault": "Touch the memory at start-up (MAP_POPULATE, pre-faulting, mlockall(MCL_CURRENT | MCL_FUTURE)) and turn transparent huge page compaction off for the process.",
       "sched": "Pin the hot threads to their own cores and keep them busy (spin or busy-poll) instead of sleeping.",
       "net": "Busy polling (SO_BUSY_POLL), fewer system calls per message (recvmmsg / sendmmsg, io_uring), or kernel bypass for the busiest path.",
       "copy": "Pass buffers by reference (zero-copy): reuse the receive buffer, use sendfile / splice / MSG_ZEROCOPY for large sends.",
       "log": "Move logging off the hot path (a ring buffer another thread drains).",
       "ser": "A faster or schema-based format for the hot message, or decode only the fields you read.",
       "sys": "Fewer system calls on the hot path: batch them, read time from the vDSO, keep the work in user space."}


def _cat(sym: str) -> str | None:
    for k, _, rx, _ in CATS:
        if re.search(rx, sym):
            return k
    return None


def _perf_report(t: str) -> list[dict[str, Any]] | None:
    rows = []
    children = bool(re.search(r"^#\s*Children\s+Self", t, re.M))
    for m in re.finditer(r"^\s*(\d+(?:\.\d+)?)%\s+(?:(\d+(?:\.\d+)?)%\s+)?(\S+)\s+(\S+)\s+\[([.kgu])\]\s+(.+?)\s*$", t, re.M):
        a, b = float(m.group(1)), m.group(2)
        self_ = float(b) if (b is not None and children) else a
        total = a if (b is not None and children) else None
        sym = m.group(6)
        if m.group(5) == "k":
            sym = "[k] " + sym
        rows.append({"sym": sym, "self": self_, "total": total, "dso": m.group(4), "comm": m.group(3)})
    return rows or None


def _folded(t: str) -> list[dict[str, Any]] | None:
    lines = [ln for ln in t.splitlines() if ln.strip()]
    stacks = []
    for ln in lines:
        m = re.match(r"^(.*\S)\s+(\d+)\s*$", ln)
        if not m or ";" not in m.group(1) and len(lines) > 3 and not re.search(r"\w", m.group(1)):
            continue
        if m:
            stacks.append((m.group(1).split(";"), int(m.group(2))))
    if len(stacks) < max(2, len(lines) // 2):
        return None
    tot = sum(c for _, c in stacks) or 1
    self_: dict[str, int] = {}
    total: dict[str, int] = {}
    for fr, c in stacks:
        self_[fr[-1]] = self_.get(fr[-1], 0) + c
        for f in set(fr):
            total[f] = total.get(f, 0) + c
    return [{"sym": s, "self": self_.get(s, 0) * 100 / tot, "total": total[s] * 100 / tot, "dso": "", "comm": ""} for s in total] + [{"_samples": tot}]


def _stat(t: str) -> dict[str, float]:
    c: dict[str, float] = {}
    for m in re.finditer(r"^\s*([\d,.]+)\s+(?:msec\s+)?([\w\-./:]+)(?:\s|$)", t, re.M):
        try:
            c[m.group(2).split(":")[0]] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    m = re.search(r"([\d.]+)\s+seconds time elapsed", t)
    if m:
        c["elapsed_s"] = float(m.group(1))
    return c


def analyse(text: str) -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 20_000_000:
        raise ProfileError("That is longer than 20 MB.")
    issues: list[dict[str, Any]] = []
    kind = ""
    rows = _perf_report(t)
    samples = None
    if rows:
        kind = "perf report"
    else:
        rows = _folded(t)
        if rows:
            kind = "folded stacks"
            samples = rows.pop()["_samples"]
    counters = _stat(t) if re.search(r"Performance counter stats|instructions|cycles|cache-misses|context-switches", t) else {}
    if not rows and not counters:
        raise ProfileError("Not a profile I can read: paste perf report --stdio, folded stacks (stackcollapse-perf.pl output), or perf stat output.")
    cats: dict[str, float] = {}
    top = []
    if rows:
        for r in rows:
            r["cat"] = _cat(r["sym"])
        for r in rows:
            if r["cat"]:
                cats[r["cat"]] = cats.get(r["cat"], 0.0) + r["self"]
        top = sorted(rows, key=lambda r: -r["self"])[:25]
        for k, label, _, lim in CATS:
            v = cats.get(k, 0)
            if v >= lim:
                who = [r["sym"] for r in top if r["cat"] == k][:4]
                issues.append({"sev": "warn" if v >= 2 * lim else "info", "area": label,
                               "text": f"{v:.1f}% of the samples are {WHY[k]}" + (f" ({', '.join(w[:50] for w in who)})" if who else "") + ".", "fix": FIX[k]})
        if top and top[0]["self"] >= 25:
            issues.append({"sev": "info", "text": f"One function takes {top[0]['self']:.0f}% on its own: {top[0]['sym'][:80]} - the first place to look."})
    stat: dict[str, Any] = {}
    if counters:
        g = counters.get
        if g("cycles") and g("instructions"):
            stat["ipc"] = g("instructions") / g("cycles")
            if stat["ipc"] < 1:
                issues.append({"sev": "warn", "text": f"{stat['ipc']:.2f} instructions per cycle: the CPU is mostly waiting - usually on memory (cache misses) or branch mispredictions.",
                               "fix": "Look at cache-misses and the data layout (the Layout page): keep what one request touches together and in order."})
        if g("cache-references") and g("cache-misses") is not None:
            stat["cache_miss"] = g("cache-misses") / g("cache-references")
            if stat["cache_miss"] > 0.1:
                issues.append({"sev": "info", "text": f"{stat['cache_miss'] * 100:.0f}% of cache references miss the last-level cache."})
        if g("branches") and g("branch-misses") is not None:
            stat["branch_miss"] = g("branch-misses") / g("branches")
            if stat["branch_miss"] > 0.02:
                issues.append({"sev": "info", "text": f"{stat['branch_miss'] * 100:.1f}% of branches are mispredicted (each costs around 15-20 cycles)."})
        el = g("elapsed_s") or (g("task-clock") or 0) / 1000 or None
        for key, what, lim, fix in (("context-switches", "context switches", 1000, "Pin the hot threads and stop them sleeping (spin or busy-poll), or give them fewer reasons to block."),
                                    ("cpu-migrations", "moves between CPUs", 10, "Pin the hot threads to fixed cores (taskset, pthread_setaffinity_np, isolcpus)."),
                                    ("page-faults", "page faults", 1000, FIX["fault"])):
            v = g(key)
            if v is None:
                continue
            rate = v / el if el else None
            stat[key.replace("-", "_")] = v
            if rate is not None:
                stat[key.replace("-", "_") + "_per_s"] = rate
            if (rate or 0) > lim or (key == "cpu-migrations" and v > 0 and el is None):
                issues.append({"sev": "warn" if key != "page-faults" else "info", "text": f"{v:,.0f} {what}" + (f" ({rate:,.0f} a second)" if rate is not None else "") + ".", "fix": fix})
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    bigs = sorted(((v, k) for k, v in cats.items()), reverse=True)
    label = dict((k, l) for k, l, _, _ in CATS)
    verdict = (f"{kind or 'perf stat'}: " + ("; ".join(f"{label[k]} {v:.0f}%" for v, k in bigs[:3]) if bigs else
               (f"IPC {stat['ipc']:.2f}" if stat.get("ipc") else "counters read")) + (f"; the top function is {top[0]['sym'][:60]} ({top[0]['self']:.0f}%)." if top else "."))
    return {"kind": kind or "perf stat", "samples": samples, "top": [{k: r.get(k) for k in ("sym", "self", "total", "dso", "cat")} for r in top],
            "cats": [{"key": k, "label": label[k], "share": v} for v, k in bigs], "stat": stat, "counters": dict(list(counters.items())[:40]),
            "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order}, "verdict": verdict,
            "note": ("Grouped by function name, so a function is counted by what it is called, not what it does inside. Self time is where the CPU was; "
                     "a profile of a whole run mixes the hot path with start-up - record during steady load, and use off-CPU profiling for time spent waiting.")}
