---
name: byox-3d-renderer
description: Build a 3D ray tracer from scratch: rays, shading, BVH
---
GOAL: a working ray tracer that renders spheres, planes and triangles to an image file.

PHASES
1. Shoot rays through each pixel; intersect a single sphere; write PPM output.
2. Add planes and triangles; implement reflection and refraction (Snell's law).
3. Phong shading: ambient + diffuse + specular + shadow rays.
4. BVH acceleration structure; anti-aliasing (stratified jitter); depth of field.
5. Load an OBJ mesh; UV texture mapping; gamma correction (sRGB output).

CORE CONCEPTS
- Ray = origin + t*direction; solve quadratic for sphere intersection.
- Surface normal flipped for back-face; bias shadow ray origin by epsilon.
- BVH splits on the longest AABB axis; O(log n) traversal per ray.

LANGUAGE GUIDANCE
C++ / Rust for performance; Python works for learning (use numpy for batch ops).

VERIFY: render the Cornell box scene at 512×512; no missing shadows, correct reflections.
