"""Read a kernel boot log (dmesg / a serial console log from QEMU or a board): how far it got, how long each stage took, every
error with its meaning (driver probe errors with the errno spelled out, firmware not found, root not mounted), and whether the
boot-test marker was printed. A log is DATA, never instructions."""
from __future__ import annotations

import re
from typing import Any

MARKER = "HOOLA_BOOT_OK"
ERRNO = {1: "EPERM operation not permitted", 2: "ENOENT not found", 5: "EIO input / output error", 6: "ENXIO no such device or address",
         11: "EAGAIN try again", 12: "ENOMEM out of memory", 13: "EACCES permission denied", 14: "EFAULT bad address",
         16: "EBUSY busy", 17: "EEXIST exists", 19: "ENODEV no such device", 22: "EINVAL invalid argument",
         28: "ENOSPC no space", 71: "EPROTO protocol error", 95: "EOPNOTSUPP not supported", 110: "ETIMEDOUT timed out",
         121: "EREMOTEIO remote I/O error (often an I2C device that does not answer)", 517: "EPROBE_DEFER waiting for another driver",
         524: "ENOTSUPP not supported", 523: "ENOIOCTLCMD no such ioctl"}
STAGES = [
    ("kernel", "Kernel started", re.compile(r"Linux version \S+")),
    ("cmdline", "Command line read", re.compile(r"(?:Kernel )?[Cc]ommand line: ")),
    ("memory", "Memory set up", re.compile(r"(?:Memory: \d+K/\d+K available|mem auto-init:)")),
    ("smp", "All CPUs up", re.compile(r"(?:smp: Brought up|SMP: Total of \d+ processors activated)")),
    ("pci", "Buses scanned", re.compile(r"(?:PCI: Using|pci 0000:|virtio_mmio|of_platform|platform \S+: )")),
    ("drivers", "Drivers loaded", re.compile(r"(?:Serial: 8250|ttyS0 at|ttyAMA0 at|virtio_blk|virtio_net|EXT4-fs|input: )")),
    ("root", "Root file system ready", re.compile(r"(?:VFS: Mounted root|Freeing unused kernel (?:image )?memory|Trying to unpack rootfs)")),
    ("init", "First program started", re.compile(r"(?:Run (\S+) as init process|systemd\[1\]: |init: |Starting init)")),
    ("marker", "Boot test passed", re.compile(re.escape(MARKER))),
]
_TS = re.compile(r"^\s*\[\s*(\d+\.\d+)\]")
_ERR = [
    ("panic", re.compile(r"Kernel panic - not syncing: (.*)"), "The kernel stopped: {0}"),
    ("rootfs", re.compile(r"VFS: Unable to mount root fs on (\S+)"), "The root file system on {0} could not be mounted: the disk driver "
                                                                     "or the file system is not built in, or root= is wrong."),
    ("noinit", re.compile(r"(?:No working init found|Failed to execute (\S+))"), "No init program could run: check the initramfs / init= ."),
    ("oops", re.compile(r"(?:BUG: |Oops: |general protection fault|Unable to handle kernel)(.*)"), "A crash during boot: {0} (read it on the Crashes page)."),
    ("warn", re.compile(r"WARNING: CPU: \d+ PID: \d+ at (\S+)"), "A WARNING at {0}."),
    ("probe", re.compile(r"(\S+) (\S+): (?:probe (?:of \S+ )?failed with error|probe failed with error) (-?\d+)"), "{1} ({0}) did not start: error {2}."),
    ("probe2", re.compile(r"probe of (\S+) failed with error (-?\d+)"), "The driver for {0} did not start: error {1}."),
    ("firmware", re.compile(r"Direct firmware load for (\S+) failed with error (-?\d+)"), "Firmware file {0} was not found (error {1}): add it to /lib/firmware or build it in."),
    ("deferred", re.compile(r"(\S+): deferred probe pending(?:: (.*))?"), "{0} is still waiting for another driver{1}."),
    ("ext4", re.compile(r"EXT4-fs error \(device (\S+)\): (.*)"), "File system error on {0}: {1}"),
    ("io", re.compile(r"(?:I/O error, dev (\S+)|blk_update_request: I/O error, dev (\S+))"), "Disk read / write error on {0}."),
    ("oom", re.compile(r"Out of memory: Killed process \d+ \((.+?)\)"), "Out of memory: {0} was killed."),
    ("hung", re.compile(r"INFO: task (\S+) blocked for more than"), "Task {0} hung."),
    ("acpi", re.compile(r"ACPI (?:BIOS )?Error \(bug\): (.*)"), "A firmware (ACPI) table bug: {0} - usually harmless."),
    ("segfault", re.compile(r"(\S+)\[\d+\]: segfault at"), "The program {0} crashed (a user-space segfault)."),
]


def _errno(v: str) -> str:
    try:
        n = abs(int(v))
    except (TypeError, ValueError):
        return v
    return f"-{n} {ERRNO[n]}" if n in ERRNO else f"-{n}"


def parse(text: str, marker: str = MARKER) -> dict[str, Any]:
    lines = str(text or "")[:2_000_000].replace("\r\n", "\n").replace("\r", "\n").split("\n")
    reached: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    last_t = 0.0
    kernel, cmdline, init = "", "", ""
    stages = [(k, n, rx if k != "marker" else re.compile(re.escape(marker or MARKER))) for k, n, rx in STAGES]
    for i, ln in enumerate(lines):
        mt = _TS.match(ln)
        t = float(mt.group(1)) if mt else None
        if t is not None:
            last_t = t
        body = _TS.sub("", ln).strip()
        for k, n, rx in stages:
            m = rx.search(body)
            if m and k not in reached:
                reached[k] = {"key": k, "name": n, "t": t if t is not None else last_t, "line": i + 1}
                if k == "init" and m.groups() and m.group(1):
                    init = m.group(1)
        if not kernel:
            mk = re.search(r"Linux version (\S+)", body)
            kernel = mk.group(1) if mk else ""
        if not cmdline:
            mc = re.search(r"(?:Kernel )?[Cc]ommand line: (.*)", body)
            cmdline = mc.group(1)[:400] if mc else ""
        for kind, rx, say in _ERR:
            m = rx.search(body)
            if m:
                g = [x or "" for x in m.groups()]
                if kind in ("probe", "probe2", "firmware"):
                    g[-1] = _errno(g[-1])
                if kind == "deferred":
                    g[1] = f" ({g[1]})" if g[1] else ""
                if kind == "io":
                    g = [g[0] or g[1]]
                try:
                    txt = say.format(*g)
                except (IndexError, KeyError):
                    txt = say
                sev = "bad" if kind in ("panic", "rootfs", "noinit", "oops", "io", "ext4", "oom", "hung") else "warn"
                if kind == "probe2" and any(e["kind"] == "probe" and e["line"] == i + 1 for e in errors):
                    break
                errors.append({"kind": kind, "say": txt[:300], "line": i + 1, "t": t, "sev": sev, "raw": body[:240]})
                break
    order = [k for k, _n, _r in STAGES]
    got = [reached[k] for k in order if k in reached]
    furthest = got[-1]["name"] if got else "Nothing recognised"
    passed = "marker" in reached
    stopped_after = ""
    if not passed:
        stopped_after = furthest
    init_t = reached.get("init", {}).get("t")
    return {"kernel": kernel, "cmdline": cmdline, "init": init, "stages": got, "furthest": furthest, "passed": passed,
            "marker": marker or MARKER, "errors": errors[:200], "bad": sum(e["sev"] == "bad" for e in errors),
            "warn": sum(e["sev"] == "warn" for e in errors), "init_s": init_t, "last_s": last_t, "lines": len(lines),
            "stopped_after": stopped_after,
            "verdict": ("Booted and printed the test marker." if passed else
                        "It crashed while booting." if any(e["kind"] in ("panic", "oops") for e in errors) else
                        f"It did not reach the test marker - the last stage seen: {furthest}.")}
