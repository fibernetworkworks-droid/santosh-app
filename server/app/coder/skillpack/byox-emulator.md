---
name: byox-emulator
description: Build a CHIP-8 or bytecode VM: fetch-decode-execute, timers, display
---
GOAL: run real CHIP-8 ROMs correctly; pass the official test ROM.

PHASES
1. Load 4 KB ROM; initialise registers (V0-VF), stack, PC=0x200, memory.
2. Fetch 2-byte opcode; decode high nibble; dispatch 10 instructions.
3. Full CHIP-8 opcode set: arithmetic, jumps, subroutine calls (CALL/RET).
4. Display (64×32 XOR sprite rendering); delay/sound timers at 60 Hz.
5. Keyboard input; run Space Invaders; pass chip8-test-suite ROM.

CORE CONCEPTS
- Opcode fetch: high_byte << 8 | low_byte; PC += 2 after every fetch.
- XOR sprite: flip screen pixels; set VF=1 if any pixel was erased (collision).
- Timer: decrement delay/sound register at 60 Hz in a separate thread/tick.

VERIFY: `chip8-test-suite.ch8` passes all tests; Space Invaders is playable.
