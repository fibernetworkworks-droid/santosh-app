---
name: byox-game
description: Build a 2D game: fixed game loop, physics, sprites, audio
---
GOAL: a playable 2D platformer with sprites, collisions, enemies and sound.

PHASES
1. Window + renderer (SDL2/raylib/pygame); fixed-timestep loop at 60 fps.
2. Player sprite, keyboard input, gravity + jump; floor collision.
3. Tilemap: load from CSV/JSON; draw only tiles in the visible viewport.
4. AABB tile collision; enemy AI (patrol + reverse on wall/edge).
5. Score HUD, sound effects (WAV), game-over screen, restart.

CORE CONCEPTS
- Fixed timestep: accumulator += deltaTime; while acc >= step { update(); acc -= step; }
- AABB: two rectangles overlap when x-ranges AND y-ranges both overlap.
- ECS: separates data (components) from behaviour (systems) for scalability.

VERIFY: player lands correctly on platforms; enemy bounces at walls; score increments.
