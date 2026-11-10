---
name: byox-memory-allocator
description: Build malloc/free: free-list, coalescing, segregated fits
when_to_use: malloc, implement malloc, memory allocator, free list, heap allocator
---
GOAL: a malloc/free that passes a correctness test suite with <10% fragmentation.

PHASES
1. sbrk wrapper: return 16-byte aligned pointers; implicit free list with header/footer.
2. free(): mark block free; immediate coalescing with adjacent free blocks.
3. Explicit free list: doubly-linked list of free blocks; O(1) free.
4. Segregated fits: size classes; search smallest fitting class first.
5. Benchmark vs glibc malloc; measure heap utilisation and throughput.

CORE CONCEPTS
- Boundary tags: header = (size | alloc_bit); footer mirrors header for O(1) coalescing.
- Coalesce: check prev alloc bit in header; check next block header; merge.
- Segregated fits: 8 size classes (1-8, 9-16, … bytes); best-fit within class.

LANGUAGE: C only — this requires direct pointer arithmetic and sbrk.

VERIFY: `mdriver` test suite reports 0 errors; utilisation ≥ 70%.
