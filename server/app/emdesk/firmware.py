"""Firmware C / C++ (and Arduino) read for the faults that bite on a microcontroller: what an interrupt handler must not do (allocate,
print, wait, take a lock, call an RTOS function without FromISR), variables shared between an interrupt and the main code without
volatile or without a critical section, busy waits with no timeout, recursion and big arrays on a small stack, raw register addresses,
and what keeps the chip awake. Read from the text - the build, the chip and the real timing are not."""
from __future__ import annotations

import re
from typing import Any


class FirmwareError(ValueError):
    pass


ISR_NAME = re.compile(r"(?:_IRQHandler|_IRQ_Handler|_Handler|_isr|_ISR|Interrupt)$|^(?:isr_|ISR_|IRQ_)|^(?:SysTick|PendSV|HardFault|NMI)_Handler$")
CALLBACK = re.compile(r"^HAL_\w+(?:Callback)$|^(?:HAL_GPIO_EXTI_Callback|HAL_TIM_PeriodElapsedCallback)$")
DISABLE = re.compile(r"__disable_irq\s*\(|taskENTER_CRITICAL|portENTER_CRITICAL|portDISABLE_INTERRUPTS|\bcli\s*\(|noInterrupts\s*\(|__set_PRIMASK\s*\(\s*1|"
                     r"ATOMIC_BLOCK|critical_section_enter_blocking|save_and_disable_interrupts|irq_lock\s*\(|k_spin_lock|__disable_interrupt|"
                     r"osKernelLock|vTaskSuspendAll|CRITICAL_SECTION_ENTER|xSemaphoreTake|osMutexAcquire|pthread_mutex_lock|__set_BASEPRI\s*\(\s*[^0)]")
ENABLE = re.compile(r"__enable_irq\s*\(|taskEXIT_CRITICAL|portEXIT_CRITICAL|portENABLE_INTERRUPTS|\bsei\s*\(|interrupts\s*\(|__set_PRIMASK\s*\(\s*0|"
                    r"critical_section_exit|restore_interrupts|irq_unlock\s*\(|k_spin_unlock|__enable_interrupt|osKernelUnlock|xTaskResumeAll|"
                    r"CRITICAL_SECTION_LEAVE|xSemaphoreGive|osMutexRelease|pthread_mutex_unlock|__set_BASEPRI\s*\(\s*0")
RTOS_NOT_ISR = re.compile(r"\b(xQueueSend|xQueueSendToBack|xQueueSendToFront|xQueueReceive|xQueueOverwrite|xSemaphoreGive|xSemaphoreTake|xTaskNotify|"
                          r"xTaskNotifyGive|xEventGroupSetBits|xEventGroupClearBits|xTimerStart|xTimerStop|xTimerReset|xStreamBufferSend|"
                          r"xMessageBufferSend|vTaskDelay|vTaskResume|ulTaskNotifyTake)\s*\(")
TYPE_SIZE = {"char": 1, "uint8_t": 1, "int8_t": 1, "bool": 1, "_Bool": 1, "byte": 1, "unsigned char": 1, "signed char": 1,
             "uint16_t": 2, "int16_t": 2, "short": 2, "unsigned short": 2, "int": 4, "unsigned": 4, "unsigned int": 4, "uint32_t": 4,
             "int32_t": 4, "float": 4, "long": 4, "unsigned long": 4, "size_t": 4, "uint64_t": 8, "int64_t": 8, "double": 8,
             "long long": 8, "unsigned long long": 8, "uint_fast8_t": 1, "uint_least8_t": 1}
WIDE = re.compile(r"\b(?:uint64_t|int64_t|long\s+long|double)\b")
WDT = re.compile(r"HAL_IWDG_Refresh|HAL_WWDG_Refresh|IWDG_ReloadCounter|wdt_reset|esp_task_wdt_reset|WDT_Feed|watchdog_update|wdog_refresh|"
                 r"WDOG_Refresh|feed_?watchdog|wdt_feed|IWDG->KR|R_WDT_Refresh|SYSCTL_WDT|watchdog_feed|ESP\.wdtFeed|rtc_wdt_feed", re.I)
SLEEP = re.compile(r"__WFI\s*\(|__WFE\s*\(|\bwfi\b|HAL_PWR_Enter|sleep_cpu\s*\(|sleep_mode\s*\(|esp_light_sleep_start|esp_deep_sleep|"
                   r"LowPower\.|vTaskDelay|osDelay|k_sleep|k_msleep|__low_power_mode|LPM\d|_BIS_SR|asm\s*\(\s*\"wfi|tickless|"
                   r"pm_state_force|sleep_ms|vTaskDelayUntil|xTaskDelayUntil", re.I)


def _strip(src: str) -> tuple[str, str]:
    """(code without comments, the same with string and char contents blanked) - both keep every newline so lines still count."""
    out, nost = [], []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            nost.append(" " * (j - i))
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            seg = re.sub(r"[^\n]", " ", src[i:j])
            out.append(seg)
            nost.append(seg)
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(src[i:j])
            nost.append(c + " " * max(0, j - i - 2) + (c if j - i >= 2 else ""))
            i = j
        else:
            out.append(c)
            nost.append(c)
            i += 1
    return "".join(out), "".join(nost)


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _funcs(ns: str) -> list[dict[str, Any]]:
    fns, depth, last = [], 0, 0
    i = 0
    while i < len(ns):
        c = ns[i]
        if c == "{":
            if depth == 0:
                sig = ns[last:i]
                sig_c = re.sub(r"^\s*#.*$", "", sig, flags=re.M).strip()
                m = re.search(r"([A-Za-z_]\w*(?:::\w+)?)\s*\(((?:[^()]|\([^()]*\))*)\)\s*(?:const|override|noexcept|IRAM_ATTR|__attribute__\s*\(\(.*?\)\))*\s*$", sig_c, re.S)
                kw = re.match(r"^(?:typedef\s+)?(?:struct|union|enum|class|namespace|extern\s+\"C\")\b", sig_c)
                if m and not kw and "=" not in sig_c.split("(")[0] and m.group(1) not in ("if", "for", "while", "switch", "do", "sizeof", "return"):
                    j, d = i, 0
                    while j < len(ns):
                        if ns[j] == "{":
                            d += 1
                        elif ns[j] == "}":
                            d -= 1
                            if d == 0:
                                break
                        j += 1
                    name = m.group(1)
                    args = m.group(2)
                    if name == "ISR" or name in ("SIGNAL", "INTERRUPT_HANDLER"):
                        name = f"ISR({args.split(',')[0].strip()})"
                    fns.append({"name": name, "sig": sig_c[-300:], "start": i, "end": j, "line": _line(ns, i), "end_line": _line(ns, j),
                                "args": args})
                    i = j + 1
                    last = i
                    continue
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
            if depth == 0:
                last = i + 1
        elif c == ";" and depth == 0:
            last = i + 1
        i += 1
    return fns


def _globals(ns: str, fns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    outside, prev = [], 0
    for f in fns:
        outside.append((prev, ns[prev:f["start"]]))
        prev = f["end"] + 1
    outside.append((prev, ns[prev:]))
    g: dict[str, dict[str, Any]] = {}
    for off, chunk in outside:
        depth = 0
        buf_start = 0
        k = 0
        while k < len(chunk):
            ch = chunk[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == ";" and depth == 0:
                stmt = chunk[buf_start:k]
                st = re.sub(r"^\s*#.*$", "", stmt, flags=re.M).strip()
                st = re.sub(r"\s+", " ", st)
                if st and not re.match(r"^(?:typedef|using|return|struct\s+\w+\s*$|enum|union|class)\b", st) and "(" not in st.split("=")[0]:
                    decl = st.split("=")[0]
                    for part in decl.split(","):
                        m = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])*\s*$", part)
                        if m and m.group(1) not in TYPE_SIZE and not re.fullmatch(r"(?:static|volatile|const|extern|unsigned|signed|register|inline)", m.group(1)):
                            typ = decl.split(",")[0][: decl.split(",")[0].rfind(m.group(1))] if part is decl.split(",")[0] else decl.split(",")[0]
                            if not re.search(r"[A-Za-z_]", typ.replace("static", "").replace("volatile", "").replace("const", "").replace("extern", "")):
                                continue
                            g[m.group(1)] = {"name": m.group(1), "volatile": "volatile" in decl or "_Atomic" in decl or "atomic" in decl,
                                             "atomic": bool(re.search(r"_Atomic|std::atomic|atomic_", decl)), "const": bool(re.search(r"\bconst\b", typ)),
                                             "wide": bool(WIDE.search(typ)), "type": re.sub(r"\b(?:static|extern)\b", "", typ).strip(),
                                             "line": _line(ns, off + buf_start + max(0, stmt.rfind(m.group(1))))}
                buf_start = k + 1
            k += 1
    return g


WRITE = r"(?:\[[^\]\n]*\])*(?:\.\w+|->\w+)*\s*(?:[+\-*/%&|^]|<<|>>)?=(?!=)"


def _defines(code: str) -> dict[str, int]:
    out = {}
    for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+\(?\s*(\d+)[uUlL]*\s*\)?\s*$", code, re.M):
        out[m.group(1)] = int(m.group(2))
    return out


def check(text: str) -> dict[str, Any]:
    src = str(text or "").replace("\r\n", "\n")
    if not src.strip():
        raise FirmwareError("Paste the firmware source first (C, C++ or an Arduino sketch).")
    code, ns = _strip(src)
    fns = _funcs(ns)
    if not fns:
        raise FirmwareError("No functions found - paste C / C++ source with function bodies.")
    defs = _defines(code)
    g = _globals(ns, fns)
    names = {f["name"] for f in fns}
    issues: list[dict[str, Any]] = []

    def add(sev: str, rule: str, f: dict[str, Any] | None, pos: int | None, text_: str, fix: str = "") -> None:
        issues.append({"sev": sev, "rule": rule, "fn": f["name"] if f else "", "line": _line(ns, pos) if pos is not None else (f["line"] if f else 0),
                       "text": text_, "fix": fix})
    attach = set(re.findall(r"attachInterrupt\s*\([^,]+,\s*&?(\w+)", ns)) | set(re.findall(r"gpio_isr_handler_add\s*\([^,]+,\s*&?(\w+)", ns)) \
        | set(re.findall(r"(?:NVIC_SetVector|IntRegister|irq_set_exclusive_handler|gpio_set_irq_enabled_with_callback|timer_isr_register|"
                         r"esp_timer_create|add_repeating_timer_ms|ticker\.attach|Timer\d?\.attachInterrupt|IRQ_CONNECT)\s*\([^)]*?&?(\w+)\s*[,)]", ns))
    for f in fns:
        body = ns[f["start"]:f["end"] + 1]
        f["body"] = body
        why = ""
        base = f["name"].split("::")[-1]
        if f["name"].startswith("ISR("):
            why = "AVR ISR() vector"
        elif re.search(r"__attribute__\s*\(\(\s*(?:interrupt|signal|isr)", f["sig"]) or re.search(r"\b__interrupt\b|\binterrupt\s+void\b|#pragma\s+vector", f["sig"]):
            why = "marked as an interrupt"
        elif ISR_NAME.search(base) and base not in ("Default_Handler",):
            why = "interrupt handler name"
        elif CALLBACK.match(base):
            why = "HAL callback - runs inside the interrupt"
        elif base in attach:
            why = "registered as an interrupt handler"
        elif "IRAM_ATTR" in f["sig"] and re.search(r"isr|irq|intr|interrupt", base, re.I):
            why = "IRAM_ATTR interrupt handler"
        f["isr"] = why
        f["calls"] = sorted({c for c in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body) if c in names and c != f["name"]})
    by = {f["name"]: f for f in fns}
    # functions called from an interrupt run in its context too (three levels)
    frontier = [f for f in fns if f["isr"]]
    for _ in range(3):
        nxt = []
        for f in frontier:
            for c in f["calls"]:
                t = by.get(c)
                if t and not t["isr"]:
                    t["isr"] = f"called from {f['name']}"
                    nxt.append(t)
        frontier = nxt
    isrs = [f for f in fns if f["isr"]]
    for f in isrs:
        b, s0 = f["body"], f["start"]
        direct = not f["isr"].startswith("called from")
        for m in re.finditer(r"\b(malloc|calloc|realloc|free|pvPortMalloc|vPortFree|new\b|delete\b)\s*[(\s\[]", b):
            add("bad", "Memory in an interrupt", f, s0 + m.start(), f"{f['name']} ({f['isr']}) calls {m.group(1)} - the heap is not safe to touch from an interrupt and can take a long, varying time.",
                "Allocate before the interrupt is enabled; in the handler use a fixed buffer or a pool.")
        for m in re.finditer(r"\b(printf|sprintf|snprintf|puts|fprintf|Serial\.print\w*|Serial\.write|cout|ESP_LOG\w|HAL_UART_Transmit|HAL_SPI_Transmit(?:Receive)?|HAL_I2C_Master_Transmit|NRF_LOG\w*)\b", b):
            add("warn", "Printing in an interrupt", f, s0 + m.start(), f"{f['name']} ({f['isr']}) calls {m.group(1)} - slow and often blocking; it stretches the interrupt and can deadlock on a busy port.",
                "Set a flag or put the bytes in a ring buffer; print from the main loop or a task.")
        for m in re.finditer(r"\b(HAL_Delay|delay|delayMicroseconds|_delay_ms|_delay_us|delay_ms|delay_us|vTaskDelay|osDelay|k_sleep|k_msleep|sleep|usleep|nrf_delay_ms|ets_delay_us)\s*\(", b):
            add("bad", "Waiting in an interrupt", f, s0 + m.start(), f"{f['name']} ({f['isr']}) waits with {m.group(1)}() - " +
                ("HAL_Delay counts SysTick, which cannot run inside a same-or-higher priority interrupt: it can hang for ever." if m.group(1) == "HAL_Delay"
                 else "every other interrupt of the same or lower priority waits too."), "Start a timer and finish the work in its own interrupt or in the main code.")
        for m in RTOS_NOT_ISR.finditer(b):
            add("bad", "RTOS call without FromISR", f, s0 + m.start(), f"{f['name']} ({f['isr']}) calls {m.group(1)}() - FreeRTOS functions without FromISR must not be called from an interrupt.",
                f"Use {m.group(1).replace('xQueueSendToBack', 'xQueueSendToBack').rstrip()}FromISR() with a BaseType_t woken flag and portYIELD_FROM_ISR()." if not m.group(1).startswith("vTaskDelay") else "Give a semaphore / notify a task from the interrupt and wait there.")
        for m in re.finditer(r"\b(pthread_mutex_lock|osMutexAcquire|k_mutex_lock|std::lock_guard|mtx\.lock)\b", b):
            add("bad", "Lock in an interrupt", f, s0 + m.start(), f"{f['name']} ({f['isr']}) takes a lock ({m.group(1)}) - if the interrupted code holds it, the system deadlocks.",
                "Disable the interrupt briefly in the main code instead, or hand the work to a task.")
        if direct:
            if re.search(r"\b(?:float|double)\b|\d\.\d*(?:[eE][+-]?\d+)?[fF]?\b(?![\w.])", b):
                add("warn", "Floating point in an interrupt", f, s0, f"{f['name']} uses floating point - on an FPU core the handler must stack the FPU registers (lazy stacking helps); without an FPU it calls the soft-float library.",
                    "Use integers / fixed point in the handler, or make sure the FPU context is saved for this interrupt.")
            for m in re.finditer(r"\bwhile\s*\(([^;{}]*)\)\s*;", b):
                add("warn", "Busy wait in an interrupt", f, s0 + m.start(), f"{f['name']} waits in a loop: while ({m.group(1).strip()[:60]}); - the interrupt holds the CPU until the hardware answers.",
                    "Use the peripheral's own interrupt for the next step, or a bounded loop with a timeout.")
            n = f["end_line"] - f["line"]
            if n > 40:
                add("info", "Long interrupt handler", f, None, f"{f['name']} is {n} lines long - long handlers raise the latency of everything at the same or lower priority.",
                    "Clear the flag, take the data, and defer the rest (a flag, a queue, a task notification).")
    # shared variables
    shared = []
    for v in g.values():
        if v["const"]:
            continue
        pat_w = re.compile(r"(?<![\w.>])" + re.escape(v["name"]) + WRITE + r"|(?:\+\+|--)\s*" + re.escape(v["name"]) + r"\b|\b" + re.escape(v["name"]) + r"(?:\[[^\]\n]*\])*\s*(?:\+\+|--)")
        pat_u = re.compile(r"(?<![\w.>])" + re.escape(v["name"]) + r"\b")
        w_isr = [f["name"] for f in isrs if pat_w.search(f["body"])]
        used = [f for f in fns if not f["isr"] and pat_u.search(f["body"])]
        u_isr = [f["name"] for f in isrs if pat_u.search(f["body"])]
        w_main = [f for f in fns if not f["isr"] and pat_w.search(f["body"])]
        if not (u_isr and used) or not (w_isr or w_main):
            continue
        row = {"name": v["name"], "type": v["type"], "volatile": v["volatile"], "atomic": v["atomic"], "line": v["line"], "isr": u_isr, "isr_writes": w_isr,
               "main": [f["name"] for f in used], "unprotected": []}
        if w_isr and not v["volatile"]:
            add("bad", "Shared without volatile", None, None, f"{v['name']} is written in {', '.join(w_isr)} and read in {', '.join(row['main'][:3])} but is not volatile - "
                "the compiler may keep it in a register and never see the change (a loop waiting on it can spin for ever).",
                f"Declare it volatile ({v['type']} volatile {v['name']}) - or use an atomic / a queue.")
            issues[-1]["line"] = v["line"]
        for f in used:
            b = f["body"]
            for m in re.finditer(r"(?:\+\+|--)\s*" + re.escape(v["name"]) + r"\b|(?<![\w.>])" + re.escape(v["name"]) + r"(?:\[[^\]\n]*\])*\s*(?:\+\+|--|[+\-|&^]=|<<=|>>=)", b):
                before = b[:m.start()]
                d = [x.end() for x in DISABLE.finditer(before)]
                e = [x.end() for x in ENABLE.finditer(before)]
                if not (d and (not e or max(d) > max(e))) and not v["atomic"]:
                    row["unprotected"].append(f["name"])
                    if w_isr:
                        add("warn", "Read-modify-write not protected", f, f["start"] + m.start(), f"{f['name']} changes {v['name']} with a read-modify-write while {', '.join(u_isr)} also "
                            f"{'writes' if w_isr else 'reads'} it - if the interrupt lands between the read and the write, one update is lost.",
                            "Wrap it in a critical section (__disable_irq() / taskENTER_CRITICAL(), then enable again) or use an atomic.")
                    break
        if v["wide"]:
            def _guarded(b: str, at: int) -> bool:
                d = [x.end() for x in DISABLE.finditer(b[:at])]
                e = [x.end() for x in ENABLE.finditer(b[:at])]
                return bool(d) and (not e or max(d) > max(e))
            prot = all(_guarded(f["body"], m.start()) for f in used for m in pat_u.finditer(f["body"]))
            if not prot and not v["atomic"]:
                add("warn", "Wide value shared with an interrupt", None, None, f"{v['name']} ({v['type']}) is shared with {', '.join(u_isr)} - on a 32-bit (or smaller) core it is read in two or more steps, "
                    "so the main code can see half an old value and half a new one.", "Read it with interrupts off, or read twice until both reads agree.")
                issues[-1]["line"] = v["line"]
        shared.append(row)
    for f in fns:
        b, s0 = f["body"], f["start"]
        if re.search(r"\b" + re.escape(f["name"].split("::")[-1]) + r"\s*\(", b[b.find("{") + 1:]) and not f["name"].startswith("ISR("):
            add("warn", "Recursion", f, None, f"{f['name']} calls itself - its stack use has no fixed bound, so the stack size cannot be proved.",
                "Rewrite it as a loop with an explicit, bounded stack.")
        for m in re.finditer(r"\b((?:unsigned\s+|signed\s+)?(?:long\s+long|long|short|char|int|float|double|bool|_Bool|byte|u?int(?:8|16|32|64)_t|size_t|uint_fast8_t|uint_least8_t))\s+([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*|\d+)\s*\](?:\s*\[\s*(\d+|[A-Za-z_]\w*)\s*\])?\s*[;=]", b):
            if re.search(r"\bstatic\s+(?:const\s+)?" + re.escape(m.group(1)) + r"\s+" + re.escape(m.group(2)), b):
                continue
            def val(x: str | None) -> int | None:
                if x is None:
                    return 1
                return int(x) if x.isdigit() else defs.get(x)
            a, c = val(m.group(3)), val(m.group(4))
            if a is None or c is None:
                continue
            size = TYPE_SIZE.get(re.sub(r"\s+", " ", m.group(1)), 4) * a * c
            if size >= 512:
                add("warn" if size >= 1024 else "info", "Big array on the stack", f, s0 + m.start(), f"{f['name']} puts {m.group(2)}[{a * c}] ({size:,} bytes) on the stack"
                    + (" inside an interrupt" if f["isr"] else "") + " - a task or main stack on a microcontroller is often 1-8 KB.",
                    "Make it static (or global) if the function is not re-entered, or give the task a measured, larger stack.")
        for m in re.finditer(r"\bwhile\s*\(([^;{}]*(?:\([^;{}]*\)[^;{}]*)*)\)\s*(?:;|\{\s*\})", b):
            cond = m.group(1)
            if f["isr"] or re.search(r"timeout|tmo|retries|tries|millis\s*\(|HAL_GetTick|xTaskGetTickCount|--|\bcount|deadline|elapsed|time", cond, re.I):
                continue
            if re.search(r"->|\bREG|[A-Z]{2,}\w*\s*&|&\s*[A-Z_]{3,}|\bflag|ready|busy|done|status|\bSR\b|ISR\b|IFG|_FLAG|__HAL_\w+_GET_FLAG|digitalRead", cond):
                add("warn", "Busy wait with no timeout", f, s0 + m.start(), f"{f['name']} waits for the hardware: while ({cond.strip()[:70]}); - if the bit never changes (a disconnected sensor, a "
                    "peripheral left in error), the firmware hangs here.", "Add a timeout (a tick count or a loop limit) and an error path.")
        for m in re.finditer(r"\*\s*\(\s*(volatile\s+)?(?:const\s+)?(?:u?int(?:8|16|32)_t|unsigned\s+(?:int|long|char)|uint32|u32)\s*\*\s*\)\s*\(?\s*(0x[0-9A-Fa-f]{6,})", b):
            if m.group(1):
                add("info", "Register by address", f, s0 + m.start(), f"{f['name']} writes the register at {m.group(2)} by number - correct only for this chip.",
                    "Use the vendor header's name (e.g. GPIOA->ODR), so a chip change or a typo shows at compile time.")
            else:
                add("bad", "Register access without volatile", f, s0 + m.start(), f"{f['name']} reads or writes {m.group(2)} through a pointer that is not volatile - the compiler may drop or reorder the access.",
                    "Cast to a volatile pointer (*(volatile uint32_t *)), or use the vendor header's register names.")
        for m in re.finditer(r"\b(malloc|calloc|realloc|pvPortMalloc|new\s+\w)", b):
            if not re.search(r"init|setup|begin|create|start|main\b", f["name"], re.I) and not f["isr"]:
                add("info", "Heap after start-up", f, s0 + m.start(), f"{f['name']} allocates with {m.group(1).split()[0]} while running - over hours the heap fragments and an allocation can fail.",
                    "Allocate once at start-up, or use fixed-size pools; check every result for NULL.")
                break
        for m in re.finditer(r"\bsprintf\s*\(", b):
            add("warn", "sprintf without a size", f, s0 + m.start(), f"{f['name']} uses sprintf - nothing stops it writing past the buffer.", "Use snprintf with sizeof(buffer).")
        for m in re.finditer(r"\bgets\s*\(", b):
            add("bad", "gets", f, s0 + m.start(), f"{f['name']} uses gets() - it cannot be told the buffer size.", "Use fgets with the buffer size.")
    for m in re.finditer(r"\b(?:s?n?printf|Serial\.printf|ESP_LOG\w)\s*\([^;]*?%[-+ #0]*\d*(?:\.\d+)?[lL]?[fFeEgG]", code):
        f = next((x for x in fns if x["start"] <= m.start() <= x["end"]), None)
        add("info", "printf with %f", f, m.start(), "printf with %f / %e / %g needs the float formatter - with newlib-nano it prints nothing unless linked with -u _printf_float (several KB).",
            "Print fixed point (value / 100 and value % 100), or accept the size and link the float formatter on purpose.")
        break
    for m in re.finditer(r"\bfloat\s+[A-Za-z_]\w*\s*=\s*[-+]?\d+\.\d*(?:[eE][-+]?\d+)?(?![fF\w])", ns):
        f = next((x for x in fns if x["start"] <= m.start() <= x["end"]), None)
        add("info", "Double constant for a float", f, m.start(), "A float is set from a constant without an f suffix (1.5 instead of 1.5f) - the maths is done in double, which on a single-precision FPU "
            "runs in the software library.", "Write float constants with an f suffix, and build with -Wdouble-promotion.")
        break
    loops = [m for m in re.finditer(r"\b(?:while\s*\(\s*(?:1|true|TRUE)\s*\)|for\s*\(\s*;\s*;\s*\))", ns)]
    main_like = [f for f in fns if re.fullmatch(r"main|loop|app_main|setup", f["name"])]
    if (loops or any(f["name"] == "loop" for f in fns)) and main_like:
        rtos = bool(re.search(r"vTaskStartScheduler|osKernelStart|xTaskCreate|k_thread_create|app_main", ns))
        if not SLEEP.search(ns) and not rtos:
            f0 = next((f for f in main_like), None)
            add("info", "Never sleeps", f0, None, "The main loop never puts the CPU to sleep (no __WFI / sleep mode / delay) - it runs at full current all the time.",
                "On battery: sleep until the next interrupt (__WFI(), the HAL's low-power modes) and wake on the events you need.")
        if not WDT.search(ns):
            f0 = next((f for f in main_like), None)
            add("info", "No watchdog", f0, None, "No watchdog refresh was found - if the firmware hangs (a busy wait, a deadlock) nothing restarts it.",
                "Start the independent watchdog at boot and refresh it from the main loop only when every task has shown it is alive.")
    issues.sort(key=lambda x: ({"bad": 0, "warn": 1, "info": 2}[x["sev"]], x["line"]))
    seen, uniq = set(), []
    for i in issues:
        k = (i["rule"], i["fn"], i["line"])
        if k not in seen:
            seen.add(k)
            uniq.append(i)
    issues = uniq[:300]
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in ("bad", "warn", "info")}
    loc = sum(1 for ln in code.splitlines() if ln.strip())
    lang = "C++" if re.search(r"\bclass\b|::|\bnamespace\b|\btemplate\s*<|std::", ns) else "C"
    if re.search(r"\bvoid\s+setup\s*\(\s*\)|\bvoid\s+loop\s*\(\s*\)", ns):
        lang = "Arduino"
    rtos = "FreeRTOS" if re.search(r"xTaskCreate|vTaskStartScheduler|xQueue|osKernelStart", ns) else ("Zephyr" if re.search(r"k_thread|K_THREAD_DEFINE|k_sem", ns) else "")
    hal = "STM32 HAL" if "HAL_" in ns else ("ESP-IDF" if re.search(r"esp_|ESP_", ns) else ("AVR" if re.search(r"\bISR\(|_vect\b|PORT[A-D]\b", ns) else ("Arduino" if lang == "Arduino" else "")))
    verdict = (f"{len(fns)} function(s), {len(isrs)} running in interrupt context, {len(shared)} variable(s) shared with an interrupt: "
               f"{counts['bad']} serious, {counts['warn']} to fix.")
    return {"lang": lang, "rtos": rtos, "platform": hal, "loc": loc, "functions": [{"name": f["name"], "line": f["line"], "lines": f["end_line"] - f["line"] + 1,
            "isr": f["isr"], "calls": f["calls"][:12]} for f in fns][:300], "isrs": [{"name": f["name"], "why": f["isr"], "line": f["line"]} for f in isrs],
            "shared": shared, "globals": len(g), "issues": issues, "counts": counts, "verdict": verdict,
            "note": ("Read from the source text: macros are not expanded, priorities and the chip are not known, and a function counts as running in an interrupt by its name, "
                     "a marker, a HAL callback, a registration call or a call from one. A clean read is not a test on the board.")}
