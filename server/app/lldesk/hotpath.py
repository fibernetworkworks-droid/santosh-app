"""Hot-path code read for what costs latency: allocation, locks, logging, sleeping, syscalls per message, copies and boxing - in
C / C++, Rust, Go and Java. A rule is stronger inside a loop (found from the braces). These are patterns read in the code, not
measurements: a profile decides what really costs time. Pasted code is data."""
from __future__ import annotations

import re
from typing import Any


class CodeError(ValueError):
    pass


# (id, languages, regex, only inside a loop, severity, what it costs, what to do)
R: list[tuple[str, str, str, bool, str, str, str]] = [
    # C / C++
    ("alloc", "cpp", r"\bnew\s+[A-Za-z_][\w:<>]*\s*[\(\[{]|\b(?:malloc|calloc|realloc)\s*\(|std::make_(?:shared|unique)\s*<", True, "warn",
     "allocates on every pass: the allocator can take a lock, touch cold memory or fault a page", "Allocate once before the loop: a pool, an arena or a pre-sized buffer you reuse."),
    ("endl", "cpp", r"std::endl\b", False, "warn", "std::endl flushes the stream - a write() system call every line", "Write '\\n' and flush when you choose to."),
    ("lock", "cpp", r"\bstd::(?:mutex|shared_mutex|recursive_mutex|lock_guard|unique_lock|scoped_lock)\b|\bpthread_mutex_lock\s*\(", False, "warn",
     "a lock: under contention the thread sleeps in the kernel and wakes tens of microseconds later", "Give the data one owner thread, or pass it through a single-producer single-consumer ring; keep shared state in atomics."),
    ("shptr", "cpp", r"[(,]\s*(?:const\s+)?std::shared_ptr<[^>]+>\s+\w+\s*[,)]", False, "info",
     "a shared_ptr taken by value: an atomic reference-count increment and decrement on every call", "Take it as const std::shared_ptr<T>& or as T& when the call does not keep it."),
    ("func", "cpp", r"\bstd::function\s*<", False, "info", "std::function can allocate for a large capture and calls through a pointer", "A template parameter or a function_ref keeps the call direct."),
    ("map", "cpp", r"\bstd::(?:map|set|multimap|list)\s*<", False, "info", "node-based containers: every step to the next node is a likely cache miss", "A sorted vector or a flat / open-addressing hash map keeps the data together."),
    ("strfmt", "cpp", r"\bstd::(?:to_string|stringstream|ostringstream)\b|\bstd::format\s*\(", True, "warn", "builds a string on every pass: allocation and formatting", "Format into a fixed buffer, or off the hot path."),
    ("log", "cpp", r"\b(?:printf|fprintf|puts|syslog)\s*\(|\bstd::(?:cout|cerr)\b|\bspdlog::|\bLOG\s*\(|\bLOG_(?:INFO|DEBUG|WARN)\b", True, "warn",
     "logging in the loop: formatting and a write to a file or a pipe", "Log off the hot path: write a small record to a ring buffer and let another thread format it."),
    ("sleep", "cpp", r"\b(?:usleep|nanosleep|sleep)\s*\(|std::this_thread::sleep_for\b", False, "warn",
     "sleeping: the wake-up comes from the scheduler, tens of microseconds or more late", "Spin for short waits (with a pause instruction), or block on the event you wait for."),
    ("yield", "cpp", r"std::this_thread::yield\s*\(|\bsched_yield\s*\(", True, "info", "yield in a spin loop: a system call each time round", "_mm_pause() / std::this_thread::yield only after many spins."),
    ("gtod", "cpp", r"\bgettimeofday\s*\(|\btime\s*\(\s*(?:NULL|nullptr|0)\s*\)", False, "info", "gettimeofday: wall clock, can jump", "clock_gettime(CLOCK_MONOTONIC) (a vDSO call, no system call) or the TSC for hot timing."),
    ("volatile", "cpp", r"\bvolatile\s+(?:bool|int|long|unsigned|std::|uint)", False, "warn", "volatile is not synchronisation: no ordering between threads", "std::atomic with the memory order you need."),
    ("seqcst", "cpp", r"memory_order_seq_cst", False, "info", "seq_cst: on x86 a store becomes a locked instruction or a fence", "memory_order_release on the store and memory_order_acquire on the load are enough for a hand-off."),
    ("dyncast", "cpp", r"\bdynamic_cast\s*<", True, "info", "dynamic_cast walks type information on every pass", "Keep the type known (a variant, a tag) on the hot path."),
    ("throw", "cpp", r"\bthrow\s+\w", True, "info", "throwing on the hot path: unwinding is very slow when it happens", "Return an error value for expected failures."),
    ("vecgrow", "cpp", r"\.(?:push_back|emplace_back)\s*\(", True, "info", "push_back in a loop: the vector reallocates and copies as it grows", "Call reserve() before the loop if no reserve is done."),
    ("syscall", "cpp", r"\b(?:send|recv|sendto|recvfrom|read|write)\s*\(\s*\w+\s*,", True, "info", "one system call per message", "Batch with sendmmsg / recvmmsg, use io_uring, or kernel bypass for the busiest path."),
    ("atomicadj", "cpp", r"^\s*(?:alignas\(\d+\)\s*)?std::atomic\s*<[^>]+>\s+\w+\s*(?:[{=][^;]*)?;", False, "info",
     "an atomic member: if two threads write atomics that sit on one cache line, the line bounces between their cores (false sharing)", "Check the struct on the Layout page; put alignas(64) on members that different threads write."),
    # Rust
    ("ralloc", "rust", r"\bVec::(?:new|with_capacity)\s*\(|\bvec!\s*\[|\bBox::new\s*\(|\bString::(?:new|from)\s*\(|\.to_string\s*\(\)|\.to_owned\s*\(\)|\bformat!\s*\(|\.to_vec\s*\(\)", True, "warn",
     "allocates on every pass", "Reuse a buffer made before the loop (clear() keeps the capacity)."),
    ("rclone", "rust", r"\.clone\s*\(\)", True, "info", "clone() in the loop: a copy (or an allocation for a String / Vec)", "Borrow instead, or move the value."),
    ("rlock", "rust", r"\bMutex\s*<|\bRwLock\s*<|\.lock\s*\(\)", False, "warn", "a lock: under contention the thread parks", "One owner thread, a channel (crossbeam / a ring), or atomics."),
    ("rlog", "rust", r"\b(?:println|eprintln|print|info|debug|trace|warn)!\s*\(", True, "warn", "printing / logging in the loop", "Log off the hot path."),
    ("rsleep", "rust", r"std::thread::sleep\s*\(|thread::sleep\s*\(", False, "warn", "sleeping: woken late by the scheduler", "Spin briefly (std::hint::spin_loop) or block on the event."),
    ("rhash", "rust", r"\bHashMap\s*<|\bHashSet\s*<", False, "info", "the default hasher (SipHash) resists attacks but is slow for small keys", "FxHash or ahash for keys an attacker cannot choose."),
    ("rarc", "rust", r"\bArc::clone\s*\(", True, "info", "an atomic reference count change every pass", "Clone the Arc once outside the loop and borrow inside."),
    ("rmpsc", "rust", r"std::sync::mpsc", False, "info", "std::sync::mpsc is a general channel", "A bounded SPSC ring (or crossbeam) for a fixed producer and consumer."),
    # Go
    ("galloc", "go", r"\bmake\s*\(|\bnew\s*\(|\bappend\s*\(", True, "warn", "allocates on every pass: more garbage, more GC work and pauses", "Allocate before the loop and reuse (a sync.Pool for buffers that leave the function)."),
    ("gfmt", "go", r"\bfmt\.(?:Sprintf|Printf|Println|Sprint|Fprintf)\s*\(|\blog\.(?:Printf|Println|Print)\s*\(", True, "warn", "fmt / log in the loop: reflection, allocation, a write", "strconv into a []byte you reuse; log off the hot path."),
    ("gdefer", "go", r"^\s*defer\s+", True, "warn", "defer in a loop runs only when the function returns: they pile up", "Move the body into a small function, or release by hand."),
    ("glock", "go", r"\bsync\.(?:Mutex|RWMutex)\b|\.Lock\s*\(\)", False, "warn", "a mutex: contention parks the goroutine", "One owner goroutine, or atomics / sharded state."),
    ("gsleep", "go", r"\btime\.Sleep\s*\(", False, "warn", "sleeping: the timer fires late", "Wait on a channel or the event."),
    ("gjson", "go", r"\bjson\.(?:Marshal|Unmarshal|NewEncoder|NewDecoder)\b", True, "warn", "encoding/json uses reflection and allocates", "A code-generated encoder, or a hand-written one for the hot message."),
    ("grex", "go", r"\bregexp\.(?:MustCompile|Compile)\s*\(", True, "warn", "compiles a regular expression every pass", "Compile it once at package level."),
    ("ggc", "go", r"\bruntime\.GC\s*\(", False, "bad", "forces a full collection: a long stop", "Remove it; tune GOGC / GOMEMLIMIT instead."),
    ("gany", "go", r"\binterface\s*\{\s*\}|\bany\b", True, "info", "boxing into an interface can allocate", "Keep concrete types on the hot path."),
    # Java
    ("jalloc", "java", r"\bnew\s+[A-Z]\w*\s*(?:<[^>]*>)?\s*\(", True, "warn", "allocates on every pass (escape analysis may remove it, often does not): GC work", "Reuse objects (a pool or flyweights), or keep the data in primitive arrays."),
    ("jsync", "java", r"\bsynchronized\b|\bReentrantLock\b|\.lock\s*\(\)", False, "warn", "a lock: contention parks the thread", "One writer thread with a ring (the Disruptor pattern), or the java.util.concurrent.atomic classes."),
    ("jcat", "java", r"\w+\s*\+=\s*\"|\"\s*\+\s*\w+|String\.format\s*\(", True, "warn", "builds a String on every pass", "A StringBuilder reused, or formatting off the hot path."),
    ("jbox", "java", r"<\s*(?:Integer|Long|Double|Short|Byte|Character|Float)\s*[,>]", False, "info", "boxed numbers in a collection: an object per value", "Primitive collections (an int[] or fastutil / Agrona / Eclipse Collections)."),
    ("jlog", "java", r"\bSystem\.(?:out|err)\.print|\b(?:log|logger|LOG)\.(?:info|debug|warn|trace)\s*\(", True, "warn", "logging in the loop", "An asynchronous logger with no allocation per call, guarded by a level check."),
    ("jsleep", "java", r"\bThread\.sleep\s*\(", False, "warn", "sleeping: woken late by the scheduler", "Thread.onSpinWait() for short waits, or block on the event."),
    ("jstream", "java", r"\.stream\s*\(\)", True, "info", "a stream pipeline builds objects on every pass", "A plain loop on the hot path."),
    ("jregex", "java", r"\bPattern\.compile\s*\(|\.split\s*\(|\.replaceAll\s*\(|\.matches\s*\(", True, "warn", "compiles a regular expression every pass", "A static final Pattern compiled once."),
    ("jgc", "java", r"\bSystem\.gc\s*\(", False, "bad", "asks for a full GC", "Remove it."),
    ("jsynccoll", "java", r"\bCollections\.synchronized\w+\s*\(|\bHashtable\b|\bVector\s*<", False, "warn", "a lock on every call", "ConcurrentHashMap, or one owner thread."),
]
LANGS = {"cpp": "C / C++", "rust": "Rust", "go": "Go", "java": "Java"}


def detect(text: str, hint: str = "") -> str:
    h = (hint or "").lower().strip()
    for k, ext in (("cpp", (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", "c++", "cpp", "c")), ("rust", (".rs", "rust")), ("go", (".go", "go", "golang")),
                   ("java", (".java", "java", "kotlin"))):
        if h and (h in ext or any(h.endswith(e) for e in ext if e.startswith("."))):
            return k
    t = text
    score = {"cpp": len(re.findall(r"#include|#define|std::|::\w+\(|->|template\s*<|\b(?:malloc|calloc|free|printf|memcpy|sizeof)\s*\(|"
                                   r"\b(?:void|int|char|unsigned|size_t|uint\d+_t)\s+\*?\w+\s*\(", t)),
             "rust": len(re.findall(r"\bfn\s+\w+|\blet\s+(?:mut\s+)?\w+|\bimpl\b|::new\(|&mut\b|\bpub\s+fn\b", t)),
             "go": len(re.findall(r"\bfunc\s+|:=|\bpackage\s+\w+|\bgo\s+func\b|\bchan\b", t)),
             "java": 3 * len(re.findall(r"\b(?:public|private|protected)\s+(?:abstract\s+|final\s+)*(?:class|interface|enum|record)\b|\bimport\s+java", t))
                     + len(re.findall(r"\bpublic\s+(?:static|final|void)|\bprivate\s+\w+|System\.|@Override|\bsynchronized\b|\bnew\s+[A-Z]\w*\s*\(", t))}
    best = max(score, key=lambda k: score[k])
    if score[best] == 0:
        raise CodeError("Could not tell the language: name it (C++, Rust, Go or Java).")
    return best


def _strip(line: str, lang: str) -> str:
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    if lang != "rust":
        line = re.sub(r"'(?:\\.|[^'\\])'", "''", line)
    return line.split("//")[0]


def check(text: str, lang_hint: str = "") -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 2_000_000:
        raise CodeError("That is longer than 2 MB.")
    lang = detect(t, lang_hint)
    rules = [r for r in R if r[1] == lang]
    loop_re = {"cpp": r"\b(?:for|while)\s*\(|\bdo\s*\{", "java": r"\b(?:for|while)\s*\(|\bdo\s*\{", "rust": r"\b(?:for\s+.+\s+in\b|while\b|loop\s*\{)", "go": r"\bfor\b"}[lang]
    stack: list[bool] = []
    pend = False
    in_block = False
    found: list[dict[str, Any]] = []
    lines = t.splitlines()
    reserved = set(re.findall(r"(\w+)\.reserve\s*\(", t))
    loops = 0
    for no, raw in enumerate(lines, 1):
        line = raw
        if in_block:
            if "*/" in line:
                line, in_block = line.split("*/", 1)[1], False
            else:
                continue
        if "/*" in line and "*/" not in line.split("/*", 1)[1]:
            line, in_block = line.split("/*", 1)[0], True
        code = _strip(re.sub(r"/\*.*?\*/", "", line), lang)
        if lang == "go" and code.strip().startswith("//"):
            continue
        is_loop = bool(re.search(loop_re, code))
        if is_loop:
            loops += 1
        inside = any(stack) or (pend and "{" not in code)
        for rid, _, rx, only_loop, sev, why, fix in rules:
            if not re.search(rx, code):
                continue
            here = inside or (is_loop and code.find("{") >= 0 and re.search(rx, code[code.find("{"):]) is not None)
            if only_loop and not here:
                continue
            if rid == "vecgrow":
                m = re.search(r"(\w+)\.(?:push_back|emplace_back)", code)
                if m and m.group(1) in reserved:
                    continue
            if rid == "syscall" and not re.search(r"\b(?:send|recv|sendto|recvfrom)\b", code) and lang == "cpp" and "fd" not in code and "sock" not in code:
                continue
            found.append({"id": rid, "line": no, "code": raw.strip()[:200], "sev": sev, "loop": bool(here), "why": why, "fix": fix})
        for ch in code:
            if ch == "{":
                stack.append(pend or is_loop)
                pend = False
                is_loop = False
            elif ch == "}" and stack:
                stack.pop()
        if is_loop and "{" not in code:
            pend = True          # the body's brace is on the next line (or a one-line body)
        elif pend and code.strip() and "{" not in code:
            pend = False
    # several atomics in one struct -> one finding, not one per line
    ats = [f for f in found if f["id"] == "atomicadj"]
    if len(ats) < 2:
        found = [f for f in found if f["id"] != "atomicadj"]
    else:
        keep = ats[0]
        keep["why"] = f"{len(ats)} atomic members (lines " + ", ".join(str(a["line"]) for a in ats[:8]) + ") - " + keep["why"]
        keep["sev"] = "warn"
        found = [f for f in found if f["id"] != "atomicadj" or f is keep]
    found.sort(key=lambda f: ({"bad": 0, "warn": 1, "info": 2}[f["sev"]], f["line"]))
    by: dict[str, int] = {}
    for f in found:
        by[f["id"]] = by.get(f["id"], 0) + 1
    counts = {k: sum(1 for f in found if f["sev"] == k) for k in ("bad", "warn", "info")}
    issues = [{"sev": f["sev"], "text": f"Line {f['line']}{' (in a loop)' if f['loop'] else ''}: {f['why']}.", "fix": f["fix"], "line": f["line"], "code": f["code"]} for f in found[:300]]
    return {"lang": lang, "lang_name": LANGS[lang], "lines": len(lines), "loops": loops, "findings": found[:300], "issues": issues, "by": by, "counts": counts,
            "verdict": (f"{LANGS[lang]}, {len(lines):,} lines: " + (f"{counts['bad'] + counts['warn']} thing(s) that cost latency on a hot path, {counts['info']} note(s)." if found else "nothing these checks look for.")),
            "note": ("Patterns read in the code, not measured. A finding matters only on the path that runs per request or per message - "
                     "profile first (perf, async-profiler, pprof) and fix what the profile shows. Code inside strings and comments is skipped.")}
