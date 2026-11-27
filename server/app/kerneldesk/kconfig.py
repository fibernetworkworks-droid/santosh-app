"""Read a kernel .config and check it against named profiles (hardening, QEMU boot test, debugging, container host), or compare
two configs. The profiles are DATA with their source; they were written from the public recommendations as of late 2026 and are
shown as 'check this' against her kernel version - an option missing from her file may simply not exist in that version."""
from __future__ import annotations

import re
from typing import Any

MAX = 2_000_000
SRC_KSPP = "Kernel Self Protection Project recommended settings (kspp.github.io) - check this against your kernel version"
SRC_DOCKER = "the container runtimes' own check-config scripts (moby/contrib/check-config.sh) - check this"
SRC_DEV = "Documentation/dev-tools and Documentation/admin-guide - check this"

# name -> (want, arch or "", why). want: "y" (y), "m|y", "n" (not set), or a value
PROFILES: dict[str, dict[str, Any]] = {
    "hardening": {"name": "Hardening", "source": SRC_KSPP, "items": [
        ("STACKPROTECTOR_STRONG", "y", "", "canaries on stack buffers"),
        ("STRICT_KERNEL_RWX", "y", "", "kernel code read-only, data not executable"),
        ("STRICT_MODULE_RWX", "y", "", "the same for modules"),
        ("RANDOMIZE_BASE", "y", "", "KASLR"),
        ("RANDOMIZE_MEMORY", "y", "x86_64", "randomize the kernel's memory regions"),
        ("VMAP_STACK", "y", "", "guard pages around kernel stacks"),
        ("HARDENED_USERCOPY", "y", "", "bounds checks on copies to / from user space"),
        ("FORTIFY_SOURCE", "y", "", "compile-time and run-time buffer size checks"),
        ("INIT_ON_ALLOC_DEFAULT_ON", "y", "", "zero memory on allocation"),
        ("INIT_STACK_ALL_ZERO", "y", "", "zero stack variables"),
        ("SLAB_FREELIST_HARDENED", "y", "", "harden the slab freelist"),
        ("SLAB_FREELIST_RANDOM", "y", "", "randomize the slab freelist"),
        ("SHUFFLE_PAGE_ALLOCATOR", "y", "", "randomize the page allocator"),
        ("BUG_ON_DATA_CORRUPTION", "y", "", "stop on detected list / data corruption"),
        ("LIST_HARDENED", "y", "", "cheap list integrity checks (6.6 and later)"),
        ("SCHED_STACK_END_CHECK", "y", "", "detect stack overruns at schedule()"),
        ("DEBUG_WX", "y", "", "warn on writable and executable mappings"),
        ("UBSAN_BOUNDS", "y", "", "array bounds checks"),
        ("SECURITY_YAMA", "y", "", "ptrace restrictions"),
        ("SECCOMP", "y", "", "system call filtering"),
        ("SECCOMP_FILTER", "y", "", "BPF filters for seccomp"),
        ("MODULE_SIG", "y", "", "signed modules"),
        ("STRICT_DEVMEM", "y", "", "restrict /dev/mem"),
        ("IO_STRICT_DEVMEM", "y", "", "restrict /dev/mem for busy I/O ranges too"),
        ("DEVMEM", "n", "", "no /dev/mem at all unless you need it"),
        ("PROC_KCORE", "n", "", "no /proc/kcore"),
        ("LEGACY_PTYS", "n", "", "no legacy BSD PTYs"),
        ("COMPAT_BRK", "n", "", "keep heap randomization"),
        ("PAGE_TABLE_ISOLATION", "y", "x86_64", "Meltdown mitigation (MITIGATION_PAGE_TABLE_ISOLATION on 6.9 and later)"),
        ("ARM64_SW_TTBR0_PAN", "y", "arm64", "privileged access never, emulated"),
        ("UNMAP_KERNEL_AT_EL0", "y", "arm64", "Meltdown mitigation on arm64"),
    ]},
    "qemu": {"name": "QEMU boot test", "source": SRC_DEV, "items": [
        ("PRINTK", "y", "", "kernel messages"),
        ("TTY", "y", "", "a console"),
        ("SERIAL_8250", "y", "x86_64", "the PC serial port"),
        ("SERIAL_8250_CONSOLE", "y", "x86_64", "console on ttyS0"),
        ("SERIAL_AMBA_PL011", "y", "arm64", "the virt board's serial port"),
        ("SERIAL_AMBA_PL011_CONSOLE", "y", "arm64", "console on ttyAMA0"),
        ("SERIAL_OF_PLATFORM", "y", "riscv64", "the virt board's serial port"),
        ("BLK_DEV_INITRD", "y", "", "boot an initramfs"),
        ("RD_GZIP", "y", "", "a gzip initramfs"),
        ("DEVTMPFS", "y", "", "/dev filled by the kernel"),
        ("DEVTMPFS_MOUNT", "y", "", "mounted at boot"),
        ("BINFMT_ELF", "y", "", "run ELF programs (init)"),
        ("BINFMT_SCRIPT", "y", "", "run #! scripts (init)"),
        ("PROC_FS", "y", "", "/proc"),
        ("SYSFS", "y", "", "/sys"),
        ("VIRTIO_PCI", "m|y", "", "virtio devices"),
        ("VIRTIO_BLK", "m|y", "", "virtio disks"),
        ("VIRTIO_NET", "m|y", "", "virtio network"),
        ("PCI", "y", "x86_64", "PCI bus"),
    ]},
    "debug": {"name": "Debugging", "source": SRC_DEV, "items": [
        ("DEBUG_KERNEL", "y", "", "the debugging menu"),
        ("DEBUG_INFO_DWARF5", "y", "", "debug info so crash frames map to file:line (or DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT)"),
        ("KALLSYMS", "y", "", "function names in crash logs"),
        ("KALLSYMS_ALL", "y", "", "data symbols too"),
        ("FRAME_POINTER", "y", "arm64", "reliable stack traces"),
        ("UNWINDER_ORC", "y", "x86_64", "reliable stack traces"),
        ("MAGIC_SYSRQ", "y", "", "SysRq keys"),
        ("DETECT_HUNG_TASK", "y", "", "hung task reports"),
        ("SOFTLOCKUP_DETECTOR", "y", "", "soft lockup reports"),
        ("HARDLOCKUP_DETECTOR", "y", "", "hard lockup reports"),
        ("PROVE_LOCKING", "y", "", "lockdep (slow: test kernels only)"),
        ("KASAN", "y", "", "memory errors (slow: test kernels only)"),
        ("UBSAN", "y", "", "undefined behaviour"),
        ("DEBUG_LIST", "y", "", "list corruption checks"),
        ("PANIC_ON_OOPS", "n", "", "keep running after an Oops to collect more"),
    ]},
    "containers": {"name": "Container host", "source": SRC_DOCKER, "items": [
        ("NAMESPACES", "y", "", ""), ("NET_NS", "y", "", ""), ("PID_NS", "y", "", ""), ("IPC_NS", "y", "", ""),
        ("UTS_NS", "y", "", ""), ("USER_NS", "y", "", "rootless containers"), ("CGROUPS", "y", "", ""),
        ("CGROUP_CPUACCT", "y", "", ""), ("CGROUP_DEVICE", "y", "", ""), ("CGROUP_FREEZER", "y", "", ""),
        ("CGROUP_SCHED", "y", "", ""), ("CGROUP_PIDS", "y", "", ""), ("CPUSETS", "y", "", ""), ("MEMCG", "y", "", ""),
        ("KEYS", "y", "", ""), ("VETH", "m|y", "", ""), ("BRIDGE", "m|y", "", ""), ("BRIDGE_NETFILTER", "m|y", "", ""),
        ("IP_NF_FILTER", "m|y", "", ""), ("IP_NF_TARGET_MASQUERADE", "m|y", "", ""), ("NETFILTER_XT_MATCH_ADDRTYPE", "m|y", "", ""),
        ("NETFILTER_XT_MATCH_CONNTRACK", "m|y", "", ""), ("NF_NAT", "m|y", "", ""), ("POSIX_MQUEUE", "y", "", ""),
        ("OVERLAY_FS", "m|y", "", "the usual storage driver"), ("SECCOMP", "y", "", ""),
    ]},
}


def parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for ln in str(text or "")[:MAX].splitlines():
        ln = ln.strip()
        m = re.match(r"^CONFIG_(\w+)=(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^# CONFIG_(\w+) is not set$", ln)
        if m:
            out[m.group(1)] = "n"
    return out


def arch_of(cfg: dict[str, str]) -> str:
    if cfg.get("X86_64") == "y":
        return "x86_64"
    if cfg.get("ARM64") == "y":
        return "arm64"
    if cfg.get("RISCV") == "y":
        return "riscv64"
    return ""


def version_of(text: str) -> str:
    m = re.search(r"# Linux/\S+ ([\d.]+\S*) Kernel Configuration", str(text or "")[:2000])
    return m.group(1) if m else ""


def check(text: str, profiles: list[str] | None = None, arch: str = "") -> dict[str, Any]:
    cfg = parse(text)
    if not cfg:
        return {"ok": False, "error": "No CONFIG_ lines found - paste the whole .config file.", "results": []}
    a = arch or arch_of(cfg)
    results = []
    for key in profiles or list(PROFILES):
        pr = PROFILES.get(key)
        if not pr:
            continue
        rows = []
        for name, want, only, why in pr["items"]:
            if only and a and only != a:
                continue
            have = cfg.get(name)
            if have is None:
                status = "absent" if want != "n" else "ok"
            elif want == "n":
                status = "ok" if have == "n" else "wrong"
            elif want == "m|y":
                status = "ok" if have in ("y", "m") else "wrong"
            else:
                status = "ok" if have == want else "wrong"
            rows.append({"name": "CONFIG_" + name, "want": {"n": "not set", "m|y": "y or m"}.get(want, want), "have":
                         {"n": "not set", None: "not in the file"}.get(have, have) if have in ("n", None) else have,
                         "status": status, "why": why})
        results.append({"profile": key, "name": pr["name"], "source": pr["source"], "rows": rows,
                        "ok": sum(r["status"] == "ok" for r in rows), "wrong": sum(r["status"] == "wrong" for r in rows),
                        "absent": sum(r["status"] == "absent" for r in rows)})
    fragment = "\n".join(f"CONFIG_{r['name'][7:]}=y" if r["want"] in ("y", "y or m") else f"# CONFIG_{r['name'][7:]} is not set"
                         for res in results for r in res["rows"] if r["status"] != "ok")
    return {"ok": True, "arch": a, "version": version_of(text), "options": len(cfg), "results": results, "fragment": fragment,
            "note": "An option 'not in the file' may not exist in your kernel version, or may depend on another option. Merge the "
                    "fragment with scripts/kconfig/merge_config.sh and run make olddefconfig - Kconfig says which ones it dropped."}


def diff(a_text: str, b_text: str) -> dict[str, Any]:
    a, b = parse(a_text), parse(b_text)
    if not a or not b:
        return {"ok": False, "error": "Paste two .config files."}
    added = sorted(k for k in b if k not in a and b[k] != "n")
    removed = sorted(k for k in a if k not in b and a[k] != "n")
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    return {"ok": True, "a_version": version_of(a_text), "b_version": version_of(b_text),
            "added": [{"name": "CONFIG_" + k, "value": b[k]} for k in added][:800],
            "removed": [{"name": "CONFIG_" + k, "value": a[k]} for k in removed][:800],
            "changed": [{"name": "CONFIG_" + k, "from": a[k], "to": b[k]} for k in changed][:800],
            "counts": {"added": len(added), "removed": len(removed), "changed": len(changed)}}
