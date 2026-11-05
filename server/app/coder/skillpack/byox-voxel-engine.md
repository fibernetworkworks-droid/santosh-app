---
name: byox-voxel-engine
description: Build a voxel engine: chunks, greedy meshing, Perlin terrain
---
GOAL: an infinite procedural voxel world with greedy meshing and block placement.

PHASES
1. Allocate 16×16×16 voxel chunk; render each visible face as two triangles.
2. Greedy meshing: merge co-planar same-type faces into quads; count faces before/after.
3. Frustum culling: skip chunks entirely outside the camera frustum (6-plane test).
4. Perlin noise terrain: 2D octave noise → heightmap; cave carving with 3D noise.
5. Block placement / destruction via DDA ray-pick; update and re-mesh affected chunk.

CORE CONCEPTS
- Chunk coordinate: world_pos / 16 (integer divide); local_pos = world_pos % 16.
- Greedy mesh: extend quad in x until type changes; then in z — O(n²) per slice.
- DDA ray march: step to next voxel boundary; track which face was hit.

LANGUAGE: C++ or Rust with OpenGL; Python + moderngl for learning.

VERIFY: 16-chunk render distance at 60 fps; placing a block is reflected immediately.
