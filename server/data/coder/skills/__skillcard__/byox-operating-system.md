---
name: byox-operating-system
description: Build an OS: bootloader, VGA, interrupts, paging, scheduler
---
GOAL: a kernel that boots in QEMU, handles keyboard IRQs and runs two processes.

PHASES
1. NASM bootloader: load kernel sectors; enter 32-bit protected mode (GDT).
2. VGA text buffer: print "Hello"; set up IDT; handle divide-by-zero exception.
3. PIC init; IRQ0 (timer) and IRQ1 (keyboard) handlers; working keyboard input.
4. Physical memory manager (bitmap); virtual memory (page directory + tables).
5. Round-robin scheduler; context switch (save/restore registers); two tasks.

CORE CONCEPTS
- GDT: null, code (DPL 0, exec+read), data (DPL 0, read+write) descriptors.
- IDT gate: offset lo/hi, selector, type (interrupt gate = 0x8E).
- Page table: 1024 entries × 4 KB = 4 MB per table; PD maps 1024 tables = 4 GB.

LANGUAGE: C + x86 Assembly (NASM).

VERIFY: QEMU boots; keyboard echoes characters; two tasks alternate in QEMU console.
