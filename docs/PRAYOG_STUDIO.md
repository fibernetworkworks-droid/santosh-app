# Prayogshala studio: how to build a realistic experiment

Owner's bar: "EXPERIMENT SHOULD FEEL REALISTIC LIKE HUMAN LAB" and "MAKE EVERY EXPERIMENT PERFECT AND ROBUST".

The approved look is the Simple pendulum. Its module, `server/app/static/prayog/exp/simple-pendulum.js`, is the
**reference**. Read it before writing anything.

## Files

- `server/app/static/prayog/studio/studio.js` is the shared engine: room, bench, lights, devices, hand, workflow,
  record book, graph, viva and Ask Hoola. **Do not edit it.** If an experiment truly needs an engine change, say so in
  your report. Helpers you need go inside your own module.
- `server/app/static/prayog/kernels.js` holds the trusted physics: the JS twins of `server/app/prayog/kernels.py`.
  **Do not edit it.**
- `server/app/prayog/catalog.py` holds each lab's LSL data. The page reads it from `/api/prayog/labs/<id>` as `S.lab`.
  It gives the title, aim, theory, params, cfg (circuit nets), check, steps, safety, questions and sources.
- Your module goes in `server/app/static/prayog/exp/<lab-id>.js`. Exactly one `HoolaStudio.define('<lab-id>', function (S) { ... return {...}; })`.

## The module

```js
HoolaStudio.define('<id>', function (S) {
  var T = S.T, M = S.M;                          // three.js r149, shared materials
  var p = window.HoolaKernels.paramsFor('<kernel>', S.lab.params);   // physics params (SI)
  // build the apparatus (S.scene.add / S.devices), register each piece with S.addApparatus(key, group, name, info)
  // HUD cards: var h = S.hudCard('Label'); h.set('text') each tick
  return {
    camera: { pos: [...], look: [...] },         // the opening view: the whole set-up on the bench
    views: { key: [[camPos], [lookAt]], ... },   // S.focus(key) flies there; step.view picks one; 'book' must exist
    theory: { principle, formula, formulaNote, more: [..], precautions },
    book: { title, lines: [...], columns: [{ label, get(row, i) }], at: [x, z, rotY] (optional) },
    graph: { x(row), y(row), xlabel, ylabel, x0, y0, line(pts) -> fn(x) },   // optional
    result(rows) -> { label, value, unit, digits, truth, note } | null,       // truth = the lab's real value
    tol: 0.02,                                   // the walk-through's allowed error vs truth
    chips: [...], viva: [[q, [options], answerIndex, why], ...],             // LSL questions are added after yours
    askState(S) -> {...},                        // what Ask Hoola sees: the live readings, plainly named
    steps: [ { id, title, view, render(u, S), ok(S) -> bool, auto(S) -> Promise }, ... ],
    tick(dt) { ... },                            // advance physics + update the 3D every frame
  };
});
```

The engine adds a **Theory** step first, and **Result** (with the graph) and **Viva** steps last. You write only the
experiment steps in between.

## Rules

1. **Numbers come from code.** Use the lab's kernel from `HoolaKernels.K.<kernel>` (`init`, `step`, `view`,
   `measure`) with the lab's params and cfg, exactly as the server checks them. A hidden "unknown" (the lab's hidden
   knob, e.g. `k`, `mu`, `eta`, `Sx`, `n`, `r_int`, `c1`, `L`) is what the student measures. Never show it outside
   the result line's "true value in this lab". Small readability helpers are fine, such as rounding to the
   instrument's least count. Inventing physics is not.
2. **Real equipment.** Every piece must look like the real lab apparatus: shape, material, printed scales and labels,
   terminals, knobs, plugs, clamps. Use the shared devices where they fit:
   - `S.stand`, `S.cork`, `S.ruler`, `S.scaleTex`, `S.stopwatch`, `S.meter` (ammeter / voltmeter / galvanometer /
     milliammeter, zero-centre for galvanometers), `S.thermometer`;
   - `S.wire` (insulated, sagging), `S.terminal`, `S.cell`, `S.powerBox`, `S.plugKey`, `S.rheostat`,
     `S.resistanceBox`;
   - `S.opticalBench`, `S.upright`, `S.tuningFork`, `S.beaker`, `S.label`, `S.rounded`, `S.contact` (a soft shadow
     under everything that sits on the bench), `S.canvasTex` / `S.liveTex` (printed / changing surfaces).

   Build anything else from three.js primitives with care: rounded edges (`S.rounded`), bevels, and correct materials
   (`M.glass`, `M.brass`, `M.chrome`, `M.wood`, `M.darkWood`, `M.iron`, `M.copper`, `M.bakelite`...).
3. **Human actions.** Every manipulation a student does by hand is shown by the gloved hand:
   - press a button: `S.hand.tap(mesh)`;
   - pull or move a part along a path: `S.hand.pinchMove(startPoint, k => point, k => applyState(k), {ms})`;
   - low-level moves: `S.hand.reach(point, 'side'|'top'|'tap'|'front')`, `S.hand.shape('pinch'|'grip'|'point'|'open'|'relaxed')`,
     `S.hand.follow`, `S.hand.away`.

   Examples: slide a jockey, insert a plug key, move the screen on an optical bench, turn a rheostat, pour water, drop
   a ball, lower the water level. While `S.hand.busy` is true, refuse a second action. In test mode (`S.fast`) all
   hand moves resolve at once.
4. **Placement.** The bench top is y = 0 and its front edge is z = `S.BENCH_FRONT` (0.29). Keep everything between
   x -1.1..1.1 and z -0.8..0.25, and nothing hanging over the edge. The record book sits at about x -0.5, z 0.08
   unless you move it with `book.at`. Do not put apparatus on top of it.
5. **Workflow.** Each step's `render(u)` uses only the UI kit:
   - text and layout: `u.h2`, `u.h3`, `u.p`, `u.note`, `u.formula`, `u.row(...)`, `u.el(node)`;
   - controls: `u.button(text, fn, primary, disabled)`, `u.slider(label, min, max, step, get, set, unit, digits)`;
   - tasks and live values: `u.task(title, done, status).add(node)`, `u.live(fn)` (a text updated every frame);
   - the table and moving on: `u.table()`, `u.next(label, enabled)`.

   Messages to the student go through `S.say(text)`: it shows on the bench and in Ask Hoola. Re-render with
   `S.render()` after a state change. A reading is recorded with `S.addRow(row)`, which also writes it into the
   handwritten record book.
6. **Robust.** Guard every action:
   - refuse out-of-range or unsafe settings with a clear `S.say`, never silently;
   - "Next" stays disabled until `ok()` is true;
   - stopping, resetting and going back must never break the state;
   - nothing may throw. Every step needs `auto(S)`: a Promise that does the step through the **same functions** the
     buttons call, choosing sensible settings, so the walk-through proves the real path. Drive time with
     `S.advance(seconds, untilFn)`. After the last experiment step's `auto`, `result(S.rows)` must be within `tol`
     of `truth`.
7. **English only**, plain and short, the way a good lab manual reads. The engine handles theme, layout and phone
   width. Never Hinglish.

## Verify (every module, before you report)

From `server/`:

```
python3 -m uvicorn --app-dir /tmp/claude-0/-home-user-santosh-app/db912f85-eff5-5316-89c0-a99aa1513a64/scratchpad/pl mini:app --port <your port> &
SHOTS=<dir> node tools/prayog_walk.js http://localhost:<port> <id> [<id> ...]
```

Use a port of your own, 8801 or above. Every lab must print **PASS**. Then **look at** `<id>-0.png` (the opening
view) and `<id>-1.png` (the first step) with the Read tool. Fix anything that looks wrong: floating parts, objects
inside each other, parts off-screen, a camera view that misses the action, a fake-looking device. Run the walk once
more. Also run `node --check exp/<id>.js`.
