"""A Linux host read for low latency: what she pastes from /proc/cmdline, sysctl -a, the CPU frequency governor, transparent huge
pages, lscpu, ethtool -c / -g, irqbalance, tuned-adm and the clock source. Each setting that adds latency is named with what it costs
and the line to change it. Trade-offs (power, throughput, security) are said with each one. Pasted text is data; nothing is run."""
from __future__ import annotations

import re
from typing import Any


class TuneError(ValueError):
    pass


def _cmdline(t: str) -> dict[str, str] | None:
    for ln in t.splitlines():
        s = ln.strip()
        if s.startswith("BOOT_IMAGE=") or (re.search(r"\broot=\S+", s) and re.search(r"\b(?:ro|rw|quiet)\b", s)) or s.lower().startswith(("cmdline:", "/proc/cmdline:")):
            s = re.sub(r"^(?:/proc/)?cmdline:\s*", "", s, flags=re.I)
            out = {}
            for tok in s.split():
                k, _, v = tok.partition("=")
                out[k] = v
            return out
    return None


def _sysctl(t: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^\s*((?:kernel|vm|net|fs)\.[\w.\-]+)\s*[=:]\s*(.*?)\s*$", t, re.M):
        out[m.group(1)] = m.group(2)
    return out


def _range(s: str) -> set[int]:
    out: set[int] = set()
    for part in str(s or "").split(","):
        part = part.strip()
        if not part or not re.match(r"^\d", part):
            continue
        a, _, b = part.partition("-")
        try:
            lo, hi = int(a), int((b.split(":")[0]) or a)
        except ValueError:
            continue
        if hi - lo > 4096:
            continue
        out |= set(range(lo, hi + 1))
    return out


RULES = [("vm.swappiness", lambda v: v > 10, "warn", "Memory", "vm.swappiness is {v:g}: the kernel swaps out memory sooner - a request that touches a swapped page waits for the disk.", "vm.swappiness = 10 (or 1)", ""),
         ("kernel.numa_balancing", lambda v: v == 1, "warn", "Memory", "Automatic NUMA balancing is on: the kernel unmaps pages now and then to see who uses them, and moves them - each causes a page fault.", "kernel.numa_balancing = 0, and place memory yourself (numactl --membind / --cpunodebind).", ""),
         ("kernel.timer_migration", lambda v: v == 1, "info", "CPU isolation", "Timers can move between CPUs (kernel.timer_migration = 1).", "kernel.timer_migration = 0", ""),
         ("net.ipv4.tcp_slow_start_after_idle", lambda v: v == 1, "warn", "Network", "TCP slow start after idle is on: a connection that was quiet starts again with a small window, so the next burst waits extra round trips.", "net.ipv4.tcp_slow_start_after_idle = 0", ""),
         ("net.core.somaxconn", lambda v: v < 1024, "warn", "Network", "net.core.somaxconn is {v:g}: under a burst of new connections the accept queue fills and connections are dropped or retried a second later.", "net.core.somaxconn = 4096 (and the listen() backlog to match).", ""),
         ("net.core.busy_read", lambda v: v == 0, "info", "Network", "Socket busy polling is off (busy_read = 0): a blocked read sleeps and is woken by the interrupt.", "net.core.busy_read = 50 and net.core.busy_poll = 50 (what tuned's network-latency profile sets) - a core spins while waiting.", "CPU time spent spinning"),
         ("kernel.sched_rt_runtime_us", lambda v: 0 < v < 1000000, "info", "Scheduler", "Real-time throttling is on ({v:g} µs of each second): a SCHED_FIFO thread that spins is stopped for the rest of each second.", "kernel.sched_rt_runtime_us = -1 only if the RT threads are pinned to isolated cores - otherwise a spinning RT thread can starve the system.", ""),
         ("vm.stat_interval", lambda v: v <= 1, "info", "CPU isolation", "vm.stat_interval is {v:g} s: memory statistics are updated on every CPU each second.", "vm.stat_interval = 10", "")]
GOOD_PROFILES = ("latency-performance", "network-latency", "realtime", "cpu-partitioning", "realtime-virtual-host")


def check(text: str) -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 5_000_000:
        raise TuneError("That is longer than 5 MB.")
    if not t.strip():
        raise TuneError("Paste the outputs first.")
    iss: list[dict[str, Any]] = []
    seen: list[str] = []
    missing: list[str] = []

    def add(sev: str, area: str, text_: str, fix: str = "", cost: str = "") -> None:
        iss.append({"sev": sev, "area": area, "text": text_, "fix": fix, "cost": cost})
    cl = _cmdline(t)
    sc = _sysctl(t)
    low = t.lower()
    cpus = None
    m = re.search(r"^\s*CPU\(s\):\s*(\d+)", t, re.M)
    if m:
        cpus = int(m.group(1))
        seen.append(f"{cpus} CPUs (lscpu)")
    tpc = re.search(r"Thread\(s\) per core:\s*(\d+)", t)
    numa = re.search(r"NUMA node\(s\):\s*(\d+)", t)
    iso: set[int] = set()
    if cl is None:
        missing.append("the kernel command line (cat /proc/cmdline)")
    else:
        seen.append("the kernel command line")
        iso_raw = re.sub(r"^(?:(?:managed_irq|domain|nohz)\s*,\s*)+", "", cl.get("isolcpus", ""))
        iso = _range(iso_raw)
        nohz = _range(cl.get("nohz_full", ""))
        sug = f"2-{cpus - 1}" if cpus and cpus > 3 else "2-7"
        if not iso and not nohz:
            add("warn", "CPU isolation", "No CPUs are set apart: the hot threads share cores with everything else (kernel threads, timers, other processes).",
                f"isolcpus=managed_irq,domain,{sug} nohz_full={sug} rcu_nocbs={sug} on the kernel command line, then pin the hot threads there (taskset / pthread_setaffinity_np).",
                "those cores run only what you pin to them")
        elif iso and not nohz:
            add("warn", "CPU isolation", f"isolcpus is set ({len(iso)} CPUs) but not nohz_full: the timer tick still interrupts those cores up to 1,000 times a second.",
                f"nohz_full={iso_raw or sug} (the kernel must be built with CONFIG_NO_HZ_FULL).")
        if nohz and "rcu_nocbs" not in cl:
            add("info", "CPU isolation", "nohz_full is set: recent kernels offload RCU callbacks from those CPUs by themselves; on an older kernel add rcu_nocbs with the same list.")
        if 0 in (iso | nohz):
            add("warn", "CPU isolation", "CPU 0 is in the isolated set: the kernel needs at least one housekeeping CPU and keeps some work on CPU 0.", "Leave CPU 0 (and its hyper-thread sibling) out of isolcpus / nohz_full.")
        if "intel_idle.max_cstate" not in cl and "processor.max_cstate" not in cl and "idle" not in cl:
            deep = re.search(r"\bC(?:3|6|7|8|10)\b", t)
            add("warn" if deep else "info", "Power states",
                f"The CPUs can sleep in deep C-states ({deep.group(0)} seen): waking from one takes tens of microseconds." if deep else
                "Deep C-states are not limited: an idle core can sleep deeply and take tens of microseconds to wake.",
                "intel_idle.max_cstate=1 processor.max_cstate=1 on the command line - or hold /dev/cpu_dma_latency open at 0 from your process (what tuned's latency-performance profile does).",
                "more power and heat")
        if cl.get("mitigations") == "off":
            add("info", "Security", "mitigations=off: system calls and context switches are faster, but the CPU vulnerability protections are off.", "Only on machines that run nothing but your own trusted code.")
        if cl.get("transparent_hugepage") == "always":
            add("warn", "Memory", "transparent_hugepage=always on the command line.", "transparent_hugepage=madvise")
        if "skew_tick" not in cl and (iso or nohz):
            add("info", "CPU isolation", "skew_tick=1 is not set: the timer ticks of all CPUs fire at the same moment and contend for the same locks.", "skew_tick=1")
        if cl.get("nmi_watchdog") != "0" and sc.get("kernel.nmi_watchdog") != "0":
            add("info", "Interrupts", "The NMI watchdog may be on: it interrupts every CPU periodically.", "nmi_watchdog=0 on the command line (you lose the hard-lockup detector).")
    gov = re.findall(r"scaling_governor\s*[:=]?\s*(\w+)|^\s*(performance|powersave|schedutil|ondemand|conservative)\s*$", t, re.M)
    govs = {a or b for a, b in gov}
    if govs:
        seen.append("the CPU frequency governor")
        slow = govs - {"performance"}
        if slow:
            add("warn", "Power states", f"The CPU frequency governor is {', '.join(sorted(slow))}: cores slow down when idle and take time to speed up when a request arrives.",
                "cpupower frequency-set -g performance (or tuned-adm profile latency-performance).", "more power")
    else:
        missing.append("the frequency governor (cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor)")
    m = re.search(r"\[(always|madvise|never)\]", t)
    if m:
        seen.append("transparent huge pages")
        if m.group(1) == "always":
            add("warn", "Memory", "Transparent huge pages are set to always: khugepaged and direct compaction can stall a thread for milliseconds while it gathers memory.",
                "echo madvise > /sys/kernel/mm/transparent_hugepage/enabled (and defrag = defer+madvise or never); use explicit huge pages for the hot data.")
    else:
        missing.append("transparent huge pages (cat /sys/kernel/mm/transparent_hugepage/enabled)")
    if sc:
        seen.append(f"{len(sc)} sysctl settings")

        def num(k: str) -> float | None:
            try:
                return float(sc[k].split()[0])
            except (KeyError, ValueError, IndexError):
                return None
        for k, bad, sev, area, txt, fix, cost in RULES:
            v = num(k)
            if v is not None and bad(v):
                add(sev, area, txt.format(v=v), fix, cost)
        rm = num("net.core.rmem_max")
        if rm is not None and rm < 4 * 1024 * 1024:
            add("info", "Network", f"net.core.rmem_max is {rm / 1024:.0f} KiB: a socket cannot ask for a larger receive buffer, and a burst that overflows it is dropped and resent.",
                "net.core.rmem_max = 16777216 and net.core.wmem_max = 16777216, then set SO_RCVBUF in the program.")
    else:
        missing.append("sysctl settings (sysctl -a)")
    m = re.search(r"Adaptive RX:\s*(on|off)", t)
    if m:
        seen.append("NIC interrupt coalescing (ethtool -c)")
        if m.group(1) == "on":
            add("warn", "Network", "Adaptive RX interrupt coalescing is on: the card holds packets back to send fewer interrupts, which adds tens of microseconds under light load.",
                "ethtool -C <nic> adaptive-rx off rx-usecs 0 (or a small fixed value)", "more interrupts and CPU at high packet rates")
        u = re.search(r"^\s*rx-usecs:\s*(\d+)", t, re.M)
        if u and int(u.group(1)) > 8:
            add("warn", "Network", f"rx-usecs is {u.group(1)}: the card waits up to {u.group(1)} µs before raising an interrupt for a packet.", "ethtool -C <nic> rx-usecs 0")
    m = re.search(r"Pre-set maximums:.*?RX:\s*(\d+).*?Current hardware settings:.*?RX:\s*(\d+)", t, re.S)
    if m:
        seen.append("NIC rings (ethtool -g)")
        mx, cur = int(m.group(1)), int(m.group(2))
        if cur < mx // 2:
            add("info", "Network", f"The RX ring is {cur} of a possible {mx}: a burst larger than the ring is dropped.", f"ethtool -G <nic> rx {mx} - a larger ring absorbs bursts (it does not add delay while the core keeps up).")
    if re.search(r"irqbalance[^\n]*\b(?:active \(running\)|: active|is running|enabled)", low):
        seen.append("irqbalance")
        add("warn" if iso else "info", "Interrupts", "irqbalance is running: it moves interrupts between CPUs - onto the hot cores unless it is told to stay off them.",
            "Set IRQBALANCE_BANNED_CPULIST to the isolated CPUs, or stop irqbalance and pin the NIC queues' interrupts yourself (/proc/irq/<n>/smp_affinity_list).")
    m = re.search(r"Current active profile:\s*([\w\-]+)", t)
    if m:
        seen.append("the tuned profile")
        if m.group(1) not in GOOD_PROFILES:
            add("info", "Profile", f"The tuned profile is {m.group(1)}.", "tuned-adm profile network-latency (or latency-performance) sets the governor, C-state limit, THP and busy polling in one step.")
    m = re.search(r"current_clocksource\s*[:=]?\s*(\w[\w\-]*)|Switched to clocksource\s+(\w[\w\-]*)", t)
    if m:
        cs = m.group(1) or m.group(2)
        seen.append(f"the clock source ({cs})")
        if cs in ("hpet", "acpi_pm"):
            add("bad", "Clocks", f"The clock source is {cs}: every clock_gettime() becomes a slow hardware read instead of a fast vDSO call - often a microsecond or more.",
                "Find why the TSC was refused: dmesg | grep -i 'tsc\\|clocksource'. On a VM use kvm-clock; on bare metal a stable TSC (tsc=reliable only if you are sure).")
    if tpc and int(tpc.group(1)) > 1:
        add("info", "CPU isolation", f"{tpc.group(1)} threads per core: two hyper-threads share one core's caches and execution units.",
            "Keep the hot thread's sibling idle (leave it out of what you pin), or turn SMT off: echo off > /sys/devices/system/cpu/smt/control.", "fewer logical CPUs")
    if numa and int(numa.group(1)) > 1:
        add("info", "Memory", f"{numa.group(1)} NUMA nodes: memory on the other socket is slower to reach.",
            "Keep each hot thread, its memory and its NIC queue on one node: numactl --cpunodebind=N --membind=N, and the NIC's node from /sys/class/net/<nic>/device/numa_node.")
    if not seen:
        raise TuneError("Nothing in that I can read: paste cat /proc/cmdline, sysctl -a, lscpu, the scaling_governor files, ethtool -c <nic> and so on.")
    order = {"bad": 0, "warn": 1, "info": 2}
    iss.sort(key=lambda i: order[i["sev"]])
    counts = {k: sum(1 for i in iss if i["sev"] == k) for k in order}
    return {"seen": seen, "missing": missing, "issues": iss, "counts": counts, "isolated": sorted(iso)[:256], "cmdline": dict(list((cl or {}).items())[:80]),
            "verdict": f"Read {len(seen)} part(s) of the host: {counts['bad'] + counts['warn']} setting(s) that add latency, {counts['info']} note(s).",
            "note": ("Only what you pasted was read; a part that was not in it is listed under 'Not seen'. Every change trades something - power, "
                     "throughput, the number of usable cores - and is worth measuring before and after on the Latency page.")}
