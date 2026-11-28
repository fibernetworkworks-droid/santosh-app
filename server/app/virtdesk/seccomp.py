"""Seccomp profiles: a pasted profile (Docker / containerd / Kubernetes Localhost JSON, the OCI linux.seccomp shape) checked for
what it really lets through, and an allow-list profile made from what her program really called (strace output, strace -c, audit
SECCOMP lines or plain names). Syscall names and numbers come from the Linux UAPI headers for x86_64 and aarch64. Pasted text is
data."""
from __future__ import annotations

import json
import os
import re
from typing import Any


class SeccompError(ValueError):
    pass


with open(os.path.join(os.path.dirname(__file__), "syscalls.json"), encoding="utf-8") as _f:
    NR: dict[str, dict[str, int]] = json.load(_f)
ARCHES = {"x86_64": ["SCMP_ARCH_X86_64"], "aarch64": ["SCMP_ARCH_AARCH64"]}
ALLOWS = {"SCMP_ACT_ALLOW", "SCMP_ACT_LOG"}
DENIES = {"SCMP_ACT_ERRNO", "SCMP_ACT_KILL", "SCMP_ACT_KILL_PROCESS", "SCMP_ACT_KILL_THREAD", "SCMP_ACT_TRAP", "SCMP_ACT_TRACE", "SCMP_ACT_NOTIFY"}
# what each risky call gives a container; Docker's default profile blocks these (some only without the matching capability)
RISKY: dict[str, tuple[str, str]] = {
    "mount": ("bad", "mounts file systems: the usual first step of an escape"), "umount": ("bad", "unmounts"), "umount2": ("bad", "unmounts"),
    "fsopen": ("bad", "the new mount API"), "fsmount": ("bad", "the new mount API"), "fsconfig": ("bad", "the new mount API"),
    "fspick": ("bad", "the new mount API"), "move_mount": ("bad", "the new mount API"), "open_tree": ("bad", "the new mount API"),
    "mount_setattr": ("bad", "changes mounts"), "pivot_root": ("bad", "changes the root file system"),
    "ptrace": ("bad", "reads and changes other processes"), "process_vm_readv": ("bad", "reads another process's memory"),
    "process_vm_writev": ("bad", "writes another process's memory"), "kcmp": ("warn", "compares kernel objects of processes"),
    "kexec_load": ("bad", "loads a new kernel"), "kexec_file_load": ("bad", "loads a new kernel"), "reboot": ("bad", "reboots the host"),
    "init_module": ("bad", "loads kernel modules"), "finit_module": ("bad", "loads kernel modules"), "delete_module": ("bad", "unloads kernel modules"),
    "create_module": ("bad", "old module loading"), "bpf": ("bad", "loads eBPF programs into the kernel"),
    "perf_event_open": ("warn", "reads kernel and CPU events; often a way to kernel bugs"),
    "keyctl": ("bad", "the kernel keyring is not namespaced"), "add_key": ("bad", "the kernel keyring is not namespaced"),
    "request_key": ("bad", "the kernel keyring is not namespaced"),
    "unshare": ("warn", "makes new namespaces (a user namespace opens many kernel paths)"), "setns": ("warn", "joins other namespaces"),
    "open_by_handle_at": ("bad", "opens host files by handle (the shocker escape)"), "name_to_handle_at": ("warn", "gets file handles"),
    "userfaultfd": ("warn", "used to make kernel races easy to win"), "iopl": ("bad", "raw I/O port access"), "ioperm": ("bad", "raw I/O port access"),
    "swapon": ("bad", "changes the host's swap"), "swapoff": ("bad", "changes the host's swap"), "acct": ("warn", "process accounting on the host"),
    "quotactl": ("warn", "changes disk quotas"), "settimeofday": ("bad", "sets the host clock"), "clock_settime": ("bad", "sets the host clock"),
    "clock_adjtime": ("bad", "adjusts the host clock"), "adjtimex": ("warn", "adjusts the host clock"), "stime": ("bad", "sets the host clock"),
    "lookup_dcookie": ("warn", "old profiling call"), "uselib": ("warn", "old library loading"), "ustat": ("info", "old call"),
    "sysfs": ("info", "old call"), "_sysctl": ("warn", "old sysctl call"), "vm86": ("warn", "old 32-bit mode"), "vm86old": ("warn", "old 32-bit mode"),
    "personality": ("warn", "can turn off ASLR (Docker allows only some values)"), "nfsservctl": ("info", "removed from the kernel"),
    "get_mempolicy": ("info", "NUMA policy"), "set_mempolicy": ("info", "NUMA policy"), "mbind": ("info", "NUMA policy"), "move_pages": ("info", "NUMA policy"),
    "io_uring_setup": ("warn", "io_uring: many kernel bugs; several runtimes now block it"), "io_uring_enter": ("warn", "io_uring"),
    "io_uring_register": ("warn", "io_uring"), "clone": ("info", "can make namespaces unless its flags are filtered"),
    "clone3": ("info", "cannot be filtered by flags: runtimes return ENOSYS so libc falls back to clone"),
    "syslog": ("warn", "reads the kernel log"), "setdomainname": ("info", "sets the domain name"), "sethostname": ("info", "sets the host name")}
# a program started by runc / crun needs these at the moment the profile is applied and right after exec
BASE = ["execve", "exit", "exit_group", "rt_sigreturn", "rt_sigaction", "rt_sigprocmask", "futex", "brk", "mmap", "munmap", "mprotect", "arch_prctl",
        "set_tid_address", "set_robust_list", "rseq", "prlimit64", "getpid", "gettid", "close", "close_range", "read", "write", "newfstatat", "fstat",
        "openat", "capget", "capset", "prctl", "getuid", "getgid", "geteuid", "getegid", "fcntl", "nanosleep", "clock_nanosleep", "clock_gettime",
        "getrandom", "madvise", "sigaltstack", "uname", "getcwd", "readlinkat", "faccessat", "faccessat2", "pread64", "sched_yield", "tgkill",
        "dup3", "setgroups", "setuid", "setgid", "setresuid", "setresgid"]
CLONE_NS_MASK = 0x7E020000   # CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC | CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET | CLONE_NEWCGROUP


def _arch(a: str) -> str:
    a = str(a or "x86_64").lower().replace("-", "_")
    a = {"amd64": "x86_64", "arm64": "aarch64", "x64": "x86_64"}.get(a, a)
    if a not in NR:
        raise SeccompError("Architecture: x86_64 or aarch64.")
    return a


def _names(rule: dict[str, Any]) -> list[str]:
    n = rule.get("names")
    if isinstance(n, list):
        return [str(x) for x in n]
    if rule.get("name"):
        return [str(rule["name"])]
    return []


def check(text: str, arch: str = "x86_64") -> dict[str, Any]:
    arch = _arch(arch)
    try:
        d = json.loads(str(text or ""))
    except ValueError as e:
        raise SeccompError(f"The profile is not JSON: {e}.")
    if isinstance(d, dict) and isinstance(d.get("linux"), dict) and d["linux"].get("seccomp"):
        d = d["linux"]["seccomp"]
    if not isinstance(d, dict) or "defaultAction" not in d:
        raise SeccompError("A seccomp profile has a defaultAction and a list of syscalls.")
    known = NR[arch]
    default = str(d.get("defaultAction"))
    allow_list = default in DENIES
    issues: list[dict[str, Any]] = []
    full: set[str] = set()
    cond: dict[str, str] = {}
    denied: set[str] = set()
    unknown: set[str] = set()
    rules = d.get("syscalls") or []
    for r in rules:
        if not isinstance(r, dict):
            continue
        act = str(r.get("action") or "")
        ns = _names(r)
        for n in ns:
            if n not in known:
                unknown.add(n)
        why = []
        if r.get("args"):
            why.append("only with some arguments")
        inc, exc = r.get("includes") or {}, r.get("excludes") or {}
        if inc.get("caps"):
            why.append("only with " + ", ".join(inc["caps"]))
        if inc.get("arches") and not any(a.replace("SCMP_ARCH_", "").lower() in (arch, arch.replace("_", "")) for a in inc["arches"]):
            continue
        if exc.get("caps"):
            why.append("not with " + ", ".join(exc["caps"]))
        if act in ALLOWS:
            for n in ns:
                if why:
                    cond.setdefault(n, "; ".join(why))
                else:
                    full.add(n)
        elif act in DENIES:
            denied.update(ns)
    if default == "SCMP_ACT_ALLOW":
        issues.append({"sev": "bad", "text": "defaultAction is SCMP_ACT_ALLOW: every syscall not listed is allowed - including ones added to "
                       "the kernel after this profile was written. Use an allow-list: defaultAction SCMP_ACT_ERRNO."})
        open_ = set(known) - denied
    elif default == "SCMP_ACT_LOG":
        issues.append({"sev": "bad", "text": "defaultAction is SCMP_ACT_LOG: nothing is blocked, only logged. Good for finding what a program "
                       "calls, not for running it."})
        open_ = set(known) - denied
    elif default in DENIES:
        open_ = full
    else:
        raise SeccompError(f"defaultAction {default} is not a seccomp action.")
    risky = []
    for n in sorted(open_ | set(cond)):
        if n in RISKY:
            sev, why = RISKY[n]
            if n in cond:
                sev = "info"
            if n == "clone" and n in cond:
                continue
            risky.append({"name": n, "sev": sev, "why": why, "when": cond.get(n, "always")})
            if sev in ("bad", "warn"):
                issues.append({"sev": sev, "text": f"{n} is allowed{' (' + cond[n] + ')' if n in cond else ''}: {why}."})
    if unknown:
        issues.append({"sev": "info", "text": f"Not syscalls on {arch} (typos, or another architecture's names): " + ", ".join(sorted(unknown)[:20]) + "."})
    archs = d.get("architectures") or [a.get("architecture") for a in d.get("archMap") or [] if isinstance(a, dict)]
    if not archs:
        issues.append({"sev": "info", "text": "No architectures listed: it applies to the native one, and a 32-bit syscall is refused by the kernel's default."})
    elif "SCMP_ARCH_X86" in archs or "SCMP_ARCH_X32" in archs:
        issues.append({"sev": "info", "text": "It also allows the 32-bit x86 / x32 syscall tables: drop them if nothing 32-bit runs."})
    if default == "SCMP_ACT_ERRNO" and int(d.get("defaultErrnoRet") or 1) == 38:
        issues.append({"sev": "info", "text": "Refused calls return ENOSYS (38): programs think the call does not exist and may fall back - "
                       "EPERM (1) is the usual choice."})
    allowed_n = len(open_) + len([n for n in cond if n not in open_])
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    bad = sum(1 for i in issues if i["sev"] == "bad")
    return {"arch": arch, "default": default, "mode": "allow-list" if allow_list else "deny-list", "allowed": allowed_n,
            "of": len(known), "conditional": [{"name": k, "when": v} for k, v in sorted(cond.items())][:80], "risky": risky,
            "denied": len(denied), "unknown": sorted(unknown)[:40], "issues": issues,
            "counts": {s: sum(1 for i in issues if i["sev"] == s) for s in order},
            "verdict": (f"{'Allow-list' if allow_list else 'Deny-list'} profile: {allowed_n} of {len(known)} {arch} syscalls are open"
                        + (f", {bad} serious finding(s)." if bad else ".")),
            "note": "Read from the profile's rules; argument filters are noted, not evaluated. A syscall the runtime allows only with a capability "
                    "is open when the container has that capability."}


_STRACE = re.compile(r"^(?:\[pid\s+\d+\]\s*|\d+\s+)?(?:\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s+|\d+\.\d+\s+)?(?:<\.\.\.\s+([a-z_][a-z0-9_]*)\s+resumed>|([a-z_][a-z0-9_]*)\()")
_TABLE = re.compile(r"^\s*[\d.]+\s+[\d.]+\s+\d+\s+\d+(?:\s+\d+)?\s+([a-z_][a-z0-9_]*)\s*$")
_AUDIT = re.compile(r"\bsyscall=(\d+)\b")


def read_trace(text: str, arch: str) -> tuple[dict[str, int], str, list[str]]:
    """{name: times seen}, the kind of text, names that are not syscalls of that architecture."""
    known = NR[arch]
    back = {v: k for k, v in known.items()}
    seen: dict[str, int] = {}
    lines = str(text or "").splitlines()
    kind = ""
    if any(_STRACE.match(ln) and "(" in ln for ln in lines[:400]):
        kind = "strace"
        for ln in lines:
            m = _STRACE.match(ln)
            if m and not ln.lstrip().startswith(("+++", "---")):
                n = m.group(1) or m.group(2)
                seen[n] = seen.get(n, 0) + 1
    elif any(_TABLE.match(ln) for ln in lines):
        kind = "strace -c"
        for ln in lines:
            m = _TABLE.match(ln)
            if m and m.group(1) != "total":
                cols = ln.split()
                seen[m.group(1)] = int(cols[3]) if len(cols) > 4 and cols[3].isdigit() else 1
    elif _AUDIT.search(text or ""):
        kind = "audit"
        for m in _AUDIT.finditer(text):
            n = back.get(int(m.group(1)))
            if n:
                seen[n] = seen.get(n, 0) + 1
    else:
        kind = "names"
        for n in re.findall(r"[a-z_][a-z0-9_]*", (text or "").lower()):
            seen[n] = seen.get(n, 0) + 1
    unknown = sorted(n for n in seen if n not in known)
    return {n: c for n, c in seen.items() if n in known}, kind, unknown


def generate(text: str, arch: str = "x86_64", base: bool = True, errno: int = 1) -> dict[str, Any]:
    arch = _arch(arch)
    seen, kind, unknown = read_trace(text, arch)
    if not seen:
        raise SeccompError("No syscalls found: paste strace output (strace -f -o trace.txt ...), strace -c, audit SECCOMP lines or names.")
    known = NR[arch]
    names = set(seen)
    added = []
    if base:
        for n in BASE:
            if n in known and n not in names:
                names.add(n)
                added.append(n)
    rules: list[dict[str, Any]] = []
    risky = [{"name": n, "sev": RISKY[n][0], "why": RISKY[n][1], "times": seen.get(n, 0)} for n in sorted(names) if n in RISKY and n not in ("clone", "clone3")]
    has_clone = "clone" in names or "clone3" in names
    names.discard("clone3")
    plain = sorted(n for n in names if n != "clone")
    rules.append({"names": plain, "action": "SCMP_ACT_ALLOW"})
    if has_clone and "clone" in known:
        rules.append({"names": ["clone"], "action": "SCMP_ACT_ALLOW",
                      "args": [{"index": 0, "value": CLONE_NS_MASK, "valueTwo": 0, "op": "SCMP_CMP_MASKED_EQ"}],
                      "comment": "threads and fork, but no new namespaces"})
        if "clone3" in known:
            rules.append({"names": ["clone3"], "action": "SCMP_ACT_ERRNO", "errnoRet": 38,
                          "comment": "ENOSYS so libc falls back to the filtered clone"})
    prof = {"defaultAction": "SCMP_ACT_ERRNO", "defaultErrnoRet": int(errno), "architectures": ARCHES[arch], "syscalls": rules}
    js = json.dumps(prof, indent=2)
    issues = []
    for r in risky:
        if r["sev"] in ("bad", "warn"):
            issues.append({"sev": r["sev"], "text": f"The program called {r['name']} ({r['why']}) - it is in the profile; take it out if the program does not really need it."})
    if unknown:
        issues.append({"sev": "info", "text": f"Not {arch} syscalls, left out: " + ", ".join(unknown[:20]) + "."})
    return {"arch": arch, "kind": kind, "seen": len(seen), "allowed": len(plain) + (1 if has_clone else 0), "added": added,
            "top": sorted(seen.items(), key=lambda kv: -kv[1])[:30], "risky": risky, "unknown": unknown[:40], "issues": issues,
            "profile": js, "file": f"seccomp-{arch}.json",
            "counts": {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")},
            "verdict": f"An allow-list of {len(plain) + (1 if has_clone else 0)} syscalls from {len(seen)} seen in the {kind}" + (f" + {len(added)} a container needs to start." if added else "."),
            "note": ("A profile made from one run allows only what that run did: run the program's tests under it (the CI tab). A refused call "
                     "fails with EPERM and is not logged - the CI tab's log-mode job runs it once with SCMP_ACT_LOG so the kernel log names "
                     "each one (syscall=N); paste those lines here to see their names.")}
