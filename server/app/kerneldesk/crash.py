"""Read a Linux kernel crash log (Oops, BUG, panic, WARNING, KASAN, UBSAN, lockdep, hung task, soft / hard lockup, RCU stall,
OOM, general protection fault; x86_64, arm64, riscv64) into its parts - in code, no model: the kind, the kernel, taint flags,
the CPU / task, the faulting address, where it stopped, the cleaned call trace, the modules, KASAN's allocate / free stacks,
lockdep's locks - plus what the evidence points at and the exact commands to find the source line in HER tree.

A crash log is DATA: nothing in it is followed as an instruction."""
from __future__ import annotations

import hashlib
import re
from typing import Any

MAX = 400_000
_TS = re.compile(r"^\s*(?:<\d>)?(?:\[\s*\d+\.\d+\]\s*|\[\s*T\d+\]\s*|\[\s*C\d+\]\s*)*")
_SYSLOG = re.compile(r"^[A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \S+ kernel: ")
_ISO = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.+\-Z]+ \S+ kernel: ")

TAINT = {"P": "a proprietary module was loaded", "F": "a module was force-loaded", "S": "running on hardware out of spec",
         "R": "a module was force-unloaded", "M": "a machine check exception happened", "B": "a bad page was found",
         "U": "taint requested by userspace", "D": "the kernel died recently (an earlier Oops)", "A": "an ACPI table was overridden",
         "W": "a WARNING happened earlier", "C": "a staging driver was loaded", "I": "a firmware bug workaround is active",
         "O": "an out-of-tree module was loaded", "E": "an unsigned module was loaded", "L": "a soft lockup happened earlier",
         "K": "the kernel was live-patched", "X": "an auxiliary taint (distribution-defined)", "T": "built with struct randomization",
         "N": "an in-kernel test was run"}
POISON = {"dead000000000100": "LIST_POISON1 - a list entry used after list_del()",
          "dead000000000122": "LIST_POISON2 - a list entry used after list_del()",
          "6b6b6b6b6b6b6b6b": "slab POISON_FREE (0x6b) - memory used after it was freed",
          "5a5a5a5a5a5a5a5a": "slab POISON_INUSE (0x5a) - memory read before it was set",
          "a5a5a5a5a5a5a5a5": "slab POISON_END (0xa5) - past the end of an object",
          "cccccccccccccccc": "0xcc fill - uninitialized stack memory (stack init pattern)"}

# (kind, label, regex on a line)
HEADS = [
    ("kasan", "KASAN memory error", re.compile(r"BUG: KASAN: ([\w-]+) in (\S+)")),
    ("kfence", "KFENCE memory error", re.compile(r"BUG: KFENCE: ([\w -]+) in (\S+)")),
    ("ubsan", "Undefined behaviour (UBSAN)", re.compile(r"UBSAN: ([\w-]+) in (\S+)")),
    ("null", "NULL pointer dereference", re.compile(r"(?:BUG: kernel NULL pointer dereference, address: (\w+)|Unable to handle kernel NULL pointer dereference at virtual address (\w+))")),
    ("pagefault", "Page fault in the kernel", re.compile(r"(?:BUG: unable to handle page fault for address: (\w+)|Unable to handle kernel paging request at virtual address (\w+))")),
    ("gpf", "General protection fault", re.compile(r"general protection fault(?:, probably for non-canonical address (0x\w+))?")),
    ("lockdep", "Locking problem (lockdep)", re.compile(r"WARNING: (possible circular locking dependency detected|possible recursive locking detected|inconsistent lock state|suspicious RCU usage|bad unlock balance detected!|held lock freed!|possible irq lock inversion dependency detected)")),
    ("softlockup", "Soft lockup", re.compile(r"(?:BUG|watchdog): soft lockup - CPU#(\d+) stuck for (\d+)s! \[(.+?):(\d+)\]")),
    ("hardlockup", "Hard lockup", re.compile(r"(?:Watchdog detected hard LOCKUP on cpu (\d+)|NMI watchdog: Watchdog detected hard LOCKUP)")),
    ("rcu", "RCU stall", re.compile(r"rcu: INFO: rcu_\w+ (?:self-)?detected stall")),
    ("hung", "Hung task", re.compile(r"INFO: task (.+?):(\d+) blocked for more than (\d+) seconds")),
    ("oom", "Out of memory", re.compile(r"(?:(\S+) invoked oom-killer|Out of memory: Killed process (\d+) \((.+?)\))")),
    ("bug", "Kernel BUG()", re.compile(r"(?:kernel BUG at (\S+)!|------------\[ cut here \]------------\s*$)")),
    ("warning", "WARNING", re.compile(r"WARNING: CPU: (\d+) PID: (\d+) at (\S+) (\S+)")),
    ("panic", "Kernel panic", re.compile(r"Kernel panic - not syncing: (.*)")),
    ("oops", "Oops", re.compile(r"(?:Internal error: )?Oops(?: - BUG)?: (\w+) \[#(\d+)\]")),
]
WHY = {
    "kasan": "KASAN caught a bad memory access. The kind in the first line says which (use-after-free, slab-out-of-bounds, "
             "global-out-of-bounds, double-free ...). Read the 'Allocated by' and 'Freed by' stacks: the object was freed in the "
             "second and used after in the first line's function.",
    "kfence": "KFENCE (the low-cost sampling memory checker) caught a bad access in production. Same meaning as KASAN, fewer details.",
    "ubsan": "Undefined behaviour in C: an index past an array, a shift too big, a signed overflow or a misaligned access. "
             "The file:line in the first line is the exact place.",
    "null": "The kernel followed a NULL pointer. A small faulting address (under 0x1000) is the OFFSET of a field inside a "
            "structure reached through that NULL pointer - find which pointer in the stopped function can be NULL here.",
    "pagefault": "The kernel touched an address that is not mapped. A random-looking address usually means a stale or "
                 "corrupted pointer (use-after-free, a missing init) rather than NULL.",
    "gpf": "A general protection fault on x86: usually a non-canonical (corrupted or poisoned) pointer. If the address matches "
           "a poison value the meaning is below.",
    "lockdep": "lockdep found a lock order problem that CAN deadlock, even if it did not this time. The chain lists which "
               "locks are taken in opposite orders on two paths; make both paths take them in the same order.",
    "softlockup": "A CPU ran kernel code for too long without scheduling (the watchdog default is about 20 s): a tight loop, "
                  "spinning on a lock or waiting on hardware without a timeout in the stopped function.",
    "hardlockup": "A CPU stopped taking interrupts: usually a loop with interrupts disabled or a deadlock on a spinlock held "
                  "with interrupts off.",
    "rcu": "An RCU grace period could not finish: a CPU stayed in an RCU read-side section, or with preemption / interrupts "
           "off, for too long. Look at the stacks of the CPUs named in the stall.",
    "hung": "A task waited in uninterruptible sleep for longer than hung_task_timeout_secs: usually a lock never released, "
            "I/O that never completed, or a missed wake-up. The top of its stack says what it waits for.",
    "oom": "The system ran out of memory and the OOM killer picked a process. Check the memory summary and who used it; a "
           "steadily growing slab or a kernel memory leak shows in the slab lines.",
    "bug": "Code hit BUG() / BUG_ON() on purpose because a condition that must never happen did. The file:line is the check; "
           "the real cause is earlier.",
    "warning": "A WARN_ON() fired: the kernel kept running but something unexpected happened at that file:line.",
    "panic": "The kernel stopped for good. The reason text says why; often a fatal Oops in interrupt context, a missing root "
             "file system, or panic_on_oops / panic_on_warn being set.",
    "oops": "The kernel hit a fault in its own code. The stopped function (RIP / pc) and the call trace show where.",
}


# frames of the reporting / allocating / waiting machinery: the first frame that is NOT one of these is the code to look at
NOISE = re.compile(r"^(?:dump_stack\w*|show_stack|print_report|print_address_description\w*|kasan_\w+|__kasan_\w+|__asan_\w+|"
                   r"check_memory_region|kasan|report_bug|__warn\w*|warn_slowpath\w*|__die\w*|die|oops_\w+|page_fault_oops|"
                   r"do_user_addr_fault|do_kern_addr_fault|exc_page_fault|asm_exc_\w+|handle_page_fault|do_page_fault|do_mem_abort|"
                   r"el1_\w+|el1h_\w+|__do_kernel_fault|die_kernel_fault|panic|kfree\w*|kvfree\w*|k[mz]alloc\w*|__k[mz]alloc\w*|"
                   r"kmem_cache_\w+|__kmem_cache_\w+|slab_\w+|__slab_\w+|___slab_\w+|kmalloc_trace\w*|__kmalloc\w*|"
                   r"stack_trace_save|save_stack\w*|set_track\w*|debug_check_no\w*|"
                   r"__schedule|schedule|schedule_\w+|io_schedule\w*|preempt_schedule\w*|__mutex_lock\w*|mutex_lock\w*|"
                   r"__down\w*|down\w*|rwsem_\w+|__rwsem_\w+|wait_for_completion\w*|__wait_for_common|wait_for_common\w*|"
                   r"__wait_\w+|wait_\w+_event\w*|__flush_work|flush_work|__cond_resched|_raw_spin_\w+|queued_spin_\w+|"
                   r"native_queued_spin\w*|lock_acquire|lock_release|__lock_acquire|rcu_\w+)$")
WAITS = re.compile(r"^(?:__mutex_lock\w*|mutex_lock\w*|__down\w*|down\w*|rwsem_\w+|wait_for_completion\w*|io_schedule\w*|"
                   r"__flush_work|flush_work|__wait_\w+|_raw_spin_\w+|queued_spin_\w+|native_queued_spin\w*)")


def base(fn: str) -> str:
    """The function name without the compiler's clone suffixes (.constprop.0, .isra.0, .part.0, .cold)."""
    return re.sub(r"\.(?:constprop|isra|part|cold|llvm|lto_priv)(?:\.\d+)*.*$", "", fn or "")


def noise(fn: str) -> bool:
    return bool(NOISE.match(base(fn)))


def mine(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """The first reliable frame outside the reporting / allocator / scheduler machinery."""
    for f in frames or []:
        if f and not f.get("unsure") and not noise(f.get("fn") or ""):
            return f
    return next((f for f in frames or [] if f and not f.get("unsure")), {})


def _clean(line: str) -> str:
    line = _SYSLOG.sub("", line)
    line = _ISO.sub("", line)
    return _TS.sub("", line).rstrip()


def _frame(s: str) -> dict[str, Any] | None:
    s = s.strip()
    if not s or s in ("<TASK>", "</TASK>", "<IRQ>", "</IRQ>", "<NMI>", "</NMI>", "<EOI>"):
        return None
    unsure = s.startswith("? ")
    s = s[2:] if unsure else s
    s = re.sub(r"^\[<[0-9a-f]+>\]\s*", "", s)                       # old style [<ffff...>] addresses
    m = re.match(r"([A-Za-z_.$][\w.$]*)\+(0x[0-9a-f]+)/(0x[0-9a-f]+)(?:\s+\[(\w+)(?:\])?)?", s)
    if not m:
        m2 = re.match(r"([A-Za-z_][\w.]*)\s*\((.*)\)", s)              # arm64 'func (mod)' rarely
        if not m2:
            return None
        return {"fn": m2.group(1), "off": "", "size": "", "mod": "", "unsure": unsure, "raw": s[:200]}
    mod = m.group(4) or ""
    return {"fn": m.group(1), "off": m.group(2), "size": m.group(3), "mod": mod, "unsure": unsure, "raw": s[:200]}


def parse(text: str) -> dict[str, Any]:
    text = str(text or "")[:MAX]
    lines = [_clean(x) for x in text.replace("\r\n", "\n").split("\n")]
    out: dict[str, Any] = {"kind": "", "label": "", "detail": "", "address": "", "kernel": "", "taint": [], "taint_raw": "",
                           "cpu": "", "pid": "", "comm": "", "hardware": "", "stopped": {}, "lr": {}, "trace": [], "modules": [],
                           "out_of_tree": [], "kasan": {}, "lockdep": [], "oom": {}, "poison": "", "file_line": "",
                           "count": 0, "arch": ""}
    found = []
    for i, ln in enumerate(lines):
        for kind, label, rx in HEADS:
            m = rx.search(ln)
            if m:
                found.append((i, kind, label, m))
                break
    if not found:
        out["label"] = "No crash found"
        return out
    # the most specific head wins: the order of HEADS; among equals the first in the log
    rank = {k: n for n, (k, _l, _r) in enumerate(HEADS)}
    i0, kind, label, m = min(found, key=lambda f: (rank[f[1]], f[0]))
    nums = [int(x) for x in re.findall(r"\[#(\d+)\]", "\n".join(lines))]
    heads = sum(1 for ln in lines if re.search(r"(?:BUG: |Unable to handle kernel |general protection fault|Kernel panic - not syncing)", ln)
                and not re.search(r"Kernel panic - not syncing: Fatal exception", ln))
    out.update(kind=kind, label=label, count=max(nums) if nums else max(1, heads if kind in ("kasan", "kfence", "ubsan", "lockdep") else 1))
    g = [x for x in m.groups() if x] if m.groups() else []
    if kind in ("null", "pagefault"):
        out["address"] = g[0] if g else ""
    elif kind == "gpf":
        out["address"] = g[0] if g else ""
    elif kind in ("kasan", "kfence", "ubsan"):
        out["detail"] = g[0] if g else ""
        loc = g[1] if len(g) > 1 else ""
        if re.search(r"\.(?:[chS]|rs):\d+", loc):                      # UBSAN names file:line; KASAN names the function
            out["file_line"] = loc
    elif kind == "warning":
        out["cpu"], out["pid"], out["file_line"] = g[0], g[1], g[2]
    elif kind == "softlockup":
        out["cpu"], out["detail"], out["comm"], out["pid"] = g[0], g[1] + " s", g[2], g[3]
    elif kind == "hung":
        out["comm"], out["pid"], out["detail"] = g[0], g[1], g[2] + " s"
    elif kind in ("lockdep", "panic"):
        out["detail"] = g[0] if g else ""
    elif kind == "bug":
        out["file_line"] = g[0] if g else ""
    # a BUG() header 'kernel BUG at x' can be on the cut-here block: find it
    for ln in lines:
        mb = re.search(r"kernel BUG at (\S+)!", ln)
        if mb and not out["file_line"]:
            out["file_line"] = mb.group(1)
        mp = re.search(r"Kernel panic - not syncing: (.*)", ln)
        if mp and kind != "panic":
            out["panic"] = mp.group(1)[:200]
    for ln in lines:
        mc = re.search(r"CPU: (\d+) (?:UID: \d+ )?PID: (\d+) Comm: (\S+)\s+(Not tainted|Tainted: ([A-Z ]+))\s+(\d\S*)", ln)
        if mc:
            out["cpu"] = out["cpu"] or mc.group(1)
            out["pid"] = out["pid"] or mc.group(2)
            out["comm"] = out["comm"] or mc.group(3)
            out["taint_raw"] = (mc.group(5) or "").strip()
            out["kernel"] = mc.group(6)
            break
    if not out["kernel"]:
        mv = next((re.search(r"Linux version (\S+)", ln) for ln in lines if "Linux version" in ln), None)
        out["kernel"] = mv.group(1) if mv else ""
    out["taint"] = [{"flag": c, "means": TAINT.get(c, "unknown flag")} for c in out["taint_raw"] if c.strip() and c != "G"]
    for ln in lines:
        mh = re.search(r"Hardware name: (.+)", ln)
        if mh:
            out["hardware"] = mh.group(1)[:160]
            break
    for ln in lines:
        mr = re.search(r"(?:RIP: \w{4}:|^\s*pc : |^epc : |PC is at )(.+)", ln)
        if mr:
            f = _frame(mr.group(1).strip())
            if f:
                out["stopped"] = f
                out["arch"] = "x86_64" if "RIP:" in ln else "arm64" if "pc :" in ln else "riscv64" if "epc :" in ln else ""
                break
    for ln in lines:
        ml = re.search(r"(?:^\s*lr : |^\s*ra : |LR is at )(.+)", ln)
        if ml:
            out["lr"] = _frame(ml.group(1).strip()) or {}
            break
    # the call trace after the chosen head (else the first one)
    start = next((k for k in range(i0, len(lines)) if re.match(r"\s*Call [Tt]race:", lines[k])), None)
    if start is None:
        start = next((k for k, ln in enumerate(lines) if re.match(r"\s*Call [Tt]race:", ln)), None)
    if start is not None:
        for ln in lines[start + 1:start + 120]:
            if re.match(r"\s*(?:---\[ end|Modules linked in|RIP:|Code:|CR2:|\S+: \S+ \S+ PID)", ln) or (not ln.strip() and out["trace"]):
                break
            f = _frame(ln)
            if f:
                out["trace"].append(f)
    for ln in lines:
        mm = re.search(r"Modules linked in:(.*)", ln)
        if mm:
            mods = [x for x in mm.group(1).split() if x and not x.startswith("[")]
            out["modules"] = [re.sub(r"\(.*\)$", "", x) for x in mods][:200]
            out["out_of_tree"] = [re.sub(r"\(.*\)$", "", x) for x in mods if re.search(r"\([^)]*O[^)]*\)", x)]
            break
    if kind in ("kasan", "kfence"):
        k: dict[str, Any] = {}
        for ln in lines:
            mw = re.search(r"(Read|Write) of size (\d+) at addr (\w+) by task (\S+)", ln)
            if mw:
                k.update(access=mw.group(1).lower(), size=int(mw.group(2)), addr=mw.group(3), task=mw.group(4))
                break
        for name in ("Allocated by task", "Freed by task", "Last potentially related work creation"):
            idx = next((j for j, ln in enumerate(lines) if ln.strip().startswith(name)), None)
            if idx is not None:
                st = []
                for ln in lines[idx + 1:idx + 30]:
                    if not ln.strip():
                        if st:
                            break
                        continue
                    f = _frame(ln)
                    if f:
                        st.append(f)
                k[name.split(" by")[0].split(" potentially")[0].lower().replace(" ", "_")] = st[:12]
        mo = next((re.search(r"The buggy address belongs to the object at (\w+)\s+which belongs to the cache (\S+) of size (\d+)", " ".join(lines[j:j + 2]))
                   for j, ln in enumerate(lines) if "belongs to the object at" in ln), None)
        if mo:
            k.update(object=mo.group(1), cache=mo.group(2), object_size=int(mo.group(3)))
        out["kasan"] = k
    if kind == "lockdep":
        out["lockdep"] = [re.sub(r"\s+", " ", ln.strip())[:160] for ln in lines if re.match(r"\s*-> #\d+ \(", ln)
                          or re.match(r"\s*\(.+?\)\{.+?\}", ln) or re.search(r"is trying to acquire lock:|but task is already holding lock:", ln)][:20]
    if kind == "oom":
        for ln in lines:
            mk = re.search(r"Out of memory: Killed process (\d+) \((.+?)\) total-vm:(\d+)kB, anon-rss:(\d+)kB", ln)
            if mk:
                out["oom"] = {"pid": mk.group(1), "name": mk.group(2), "total_vm_kb": int(mk.group(3)), "rss_kb": int(mk.group(4))}
            mg = re.search(r"gfp_mask=(0x\w+)\((.*?)\), order=(\d+)", ln)
            if mg:
                out["oom"].update(gfp=mg.group(2), order=int(mg.group(3)))
    addr = (out["address"] or "").lower().replace("0x", "")
    blob = " ".join(lines).lower()
    for p, means in POISON.items():
        if p in addr or p in blob:
            out["poison"] = f"0x{p}: {means}"
            break
    if not out["poison"] and re.match(r"^dead0000000001[0-9a-f]{2}$", addr):
        out["poison"] = f"0x{addr} (LIST_POISON plus an offset): a list entry used after list_del()"
    return out


def _small(addr: str) -> int | None:
    try:
        v = int(addr, 16)
    except (TypeError, ValueError):
        return None
    return v if v < 0x1000 else None


def explain(p: dict[str, Any], tree: str = "") -> dict[str, Any]:
    """What the evidence points at, by rules, + the commands to run in HER tree. Never a guess presented as a fact."""
    if not p.get("kind"):
        return {"summary": "No kernel crash was found in this text. Paste the whole log from the first '[ cut here ]' or 'BUG:' "
                           "line to the '---[ end trace' line.", "points": [], "commands": []}
    st = p.get("stopped") or {}
    where = st if st and not noise(st.get("fn") or "") else mine(p.get("trace") or []) or st
    fn = where.get("fn") or (p.get("file_line") or "?")
    mod = where.get("mod") or ""
    points = [WHY.get(p["kind"], "")]
    if p["kind"] == "null":
        off = _small(p.get("address") or "")
        if off is not None:
            points.append(f"The address 0x{off:x} means the code read a field {off} bytes into a structure, through a NULL "
                          f"pointer, inside {fn}(). The pointer at that offset's structure is the one to check for NULL.")
    if p.get("poison"):
        points.append("The address is a poison value: " + p["poison"] + ".")
    if p["kind"] in ("kasan", "kfence") and p.get("kasan", {}).get("freed"):
        fr = mine(p["kasan"]["freed"])
        al = mine(p["kasan"].get("allocated") or [])
        if fr:
            points.append(f"Freed in {fr['fn']}(), used again in {fn}(): something keeps a pointer after {fr['fn']}() frees it"
                          + (f"; allocated in {al['fn']}()." if al else "."))
    if p["kind"] == "hung":
        w = next((f for f in p.get("trace") or [] if WAITS.match(base(f.get("fn") or ""))), None)
        if w:
            points.append(f"It waits in {base(w['fn'])}() called from {fn}(): find who holds that lock or never completes, and check "
                          "the stacks of the other blocked tasks (echo w > /proc/sysrq-trigger prints them).")
    lr = p.get("lr") or {}
    if lr.get("mod") and not where.get("mod"):
        points.append(f"It was called from {lr['fn']}() in the module '{lr['mod']}' (the link register): start there.")
    if mod:
        oot = mod in (p.get("out_of_tree") or [])
        points.append(f"It stopped inside the module '{mod}'" + (" - an out-of-tree module (taint O), most likely your own "
                                                                  "driver." if oot else "."))
    flags = {t["flag"] for t in p.get("taint") or []}
    if "P" in flags or "O" in flags or "E" in flags:
        points.append("The kernel is tainted (" + ", ".join(sorted(flags)) + "): upstream maintainers usually ask to "
                      "reproduce it without proprietary / out-of-tree modules before they look.")
    if "D" in flags or "W" in flags:
        points.append("An earlier Oops or WARNING happened first (taint D / W): the FIRST report in the log is the one to fix.")
    if p.get("count", 1) > 1:
        points.append(f"This log has {p['count']} crash reports; fix the first one - later ones are often a result of it.")
    cmds = []
    if where.get("fn") and where.get("off"):
        obj = f"{mod}.ko" if mod else "vmlinux"
        cmds.append(f"./scripts/faddr2line {obj} {where['fn']}{'+' + where['off']}/{where['size']}")
    cmds.append("./scripts/decode_stacktrace.sh vmlinux < crash.txt   # every frame with its file:line (needs CONFIG_DEBUG_INFO)")
    if p.get("file_line"):
        cmds.append(f"git log -L :{p['file_line'].split(':')[0]}  # or: git blame {p['file_line'].split(':')[0]}")
    if p["kind"] == "lockdep":
        cmds.append("cat /proc/lockdep_chains | less   # on the test machine, with CONFIG_PROVE_LOCKING")
    if p["kind"] in ("null", "pagefault", "gpf", "oops"):
        cmds.append("Rebuild with CONFIG_KASAN=y and reproduce: a use-after-free shows its free site.")
    summary = (f"{p['label']}" + (f" ({p['detail']})" if p.get("detail") else "") + f" in {fn}()" +
               (f" [{mod}]" if mod else "") + (f" on {p['kernel']}" if p.get("kernel") else "") +
               (f", task {p['comm']} (PID {p['pid']})" if p.get("comm") else "") + ".")
    return {"summary": summary, "points": [x for x in points if x], "commands": cmds, "where": where}


def signature(p: dict[str, Any]) -> str:
    fr = [f["fn"] for f in ([p.get("stopped")] if p.get("stopped") else []) + (p.get("trace") or [])
          if f and not f.get("unsure") and not noise(f.get("fn") or "")]
    seen: list[str] = []
    for f in fr:
        if f not in seen:
            seen.append(f)
        if len(seen) == 3:
            break
    key = "|".join([p.get("kind") or "", p.get("detail") or "", p.get("file_line") or ""] + seen)
    return hashlib.sha1(key.encode()).hexdigest()[:12]
