---
name: byox-physics-engine
description: Build a 2D rigid-body physics engine: collisions, impulse, joints
---
GOAL: a 2D engine where boxes and circles stack, bounce and slide realistically.

PHASES
1. Particle: position, velocity, mass; Euler integration with gravity.
2. Circle-circle collision detection; elastic impulse response.
3. AABB vs AABB; SAT for convex polygons (find separating axis → MTV).
4. Impulse resolution: restitution (bounciness) + friction along tangent.
5. Distance joint (spring); visualise with SDL2 or raylib.

CORE CONCEPTS
- Impulse = j·normal; j = -(1+e)·vel_rel·n / (1/mA + 1/mB + cross terms).
- SAT: project all vertices onto each face normal; gap = no collision; min overlap = MTV.
- Restitution e=1 fully elastic; e=0 perfectly inelastic; real objects e=0.3–0.8.

VERIFY: stack of 5 boxes stays stable; dropped sphere bounces 3 times and settles.
