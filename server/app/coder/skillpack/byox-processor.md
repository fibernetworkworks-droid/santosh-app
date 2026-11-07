---
name: byox-processor
description: Build a RISC-V CPU in Verilog or simulate RV32I in C
---
GOAL: execute a Fibonacci program on a RISC-V soft-core; correct register output.

PHASES
1. Single-cycle RV32I: register file (x0 always 0), ALU, immediate decode.
2. R-type (add/sub/and/or/slt) + I-type (addi/slti/lw) working.
3. Load/store (lw, sw) + branch (beq, bne, blt) + JAL/JALR.
4. 5-stage pipeline: IF/ID/EX/MEM/WB; hazard detection + forwarding.
5. Control hazard: flush on branch taken; run Fibonacci; check x10 register.

CORE CONCEPTS
- RV32I: 32 registers × 32 bits; instruction = 32 bits fixed width; RISC.
- Data hazard: EX/MEM → EX forwarding covers most; load-use needs 1 stall.
- CSR instructions for machine-mode traps (optional for Phase 5).

LANGUAGE: Verilog / SystemVerilog for FPGA; C for a software simulator first.

VERIFY: fib(10) = 55 in register x10 after the program halts.
