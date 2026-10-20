# Hoola Moves (parked on branch `moves-preview`, 20 Oct 2026)

The owner saw the preview page and said: save this for future work. Not in the app yet.

## What exists
- `assets/santosh3d/avatar.js`: `HoolaAvatar.build(look, { rig: true })` gives the avatar real joints
  (`parts.rig.shoulder/elbow/hand/hip/knee/foot[s]`, s = -1 / +1). Without `rig` every avatar is built exactly as on main.
  Rest pose with rig = arms hanging, legs straight.
- `assets/santosh3d/moves.js`: `HoolaMoves.attach(parts)` -> `play(id)`, `update(dt, t)`. 13 moves: idle (Aaram), phone,
  wave (Hello), namaste, bhangra, groove (Disco), jump (Kudo), spin (Ghoomo), clap (Taali), walk (Chalo), cheer (Jeet gaye!),
  think (Socho, head scratch), yoga (tree pose). Each move = function of time -> pose; the mover eases toward it
  (rate 13, 22 for jump/spin), squash & stretch, feet kept near flat, phone shown only in `phone`.
  Angle rules are in the file header. Works on all 200 looks (long skirts/saree: legs move under the cone).
- `tool/moves/demo_template.html` + `build_demo.py`: the preview page (move pad, Auto tour, WebAudio dhol beat,
  look picker for all 200, drag to turn).

## Next (when the owner says go)
1. `santosh3d/index.html`: build with `{ rig: true }`, attach mover, `santosh.dance(id)` from Dart; the existing
   mood/talk/listen behaviour should drive `idle`/`phone`; keep the old non-rig look as fallback.
2. Show the live 3D avatar on Today + call screens (today they show PNGs via LiveSantosh).
3. Avatar picks moves itself: namaste on app open / greeting, jump or cheer when a task finishes, bhangra on
   birthdays / good news, think while working; owner can say "naacho" / "jump karo" (server event `avatar_move`).
4. Work Theatre (theatre.js) could use the rig for its own avatar.
5. Check on a real phone: WebView frame rate with shadows on low-end Android.
