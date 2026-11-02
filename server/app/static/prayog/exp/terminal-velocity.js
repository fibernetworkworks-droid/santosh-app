/* Prayogshala studio module: Stokes' law - terminal velocity and viscosity (NCERT Class XI).
   A tall glass jar of glycerine with two rubber bands round it, a metre scale beside it, steel balls of five sizes in
   petri dishes. The gloved hand drops one ball at the centre of the surface; the student starts the stopwatch as it
   passes the upper band and stops it at the lower band. Physics: the stokes kernel from kernels.js (RK4). */
HoolaStudio.define('terminal-velocity', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.stokes;
  function hidden(id, dflt) { var k = (S.lab.knobs || []).filter(function (q) { return q.id === id; })[0]; return k ? k.value * (k.k || 1) : dflt; }
  var p = window.HoolaKernels.paramsFor('stokes', S.lab.params);
  p.eta = hidden('eta', 1.49);
  var DIAS = [2, 3, 4, 5, 6];   // mm, measured with a screw gauge (given)
  var st = { pick: 3, dist: null, b1: null, b2: null, phase: 'none', air: 0, airV: 0, t1: null, y1: null, left: [4, 4, 4, 4, 4], drops: 0 };
  p.r = DIAS[st.pick] / 2000;
  var sim = K.init(p);

  // ---------- geometry: the jar, the glycerine, the bands and the scale share one "reading" frame (cm on the scale)
  var JX = 0, JZ = -0.05, RO = 0.032, RI = 0.029, FOOT = 0.012, JH = 0.62, TB = 0.006;
  var FLOOR = FOOT + TB, SURF = FLOOR + 0.58, RIM = FOOT + JH;
  var RX = 0.062, RZ = -0.05, RLEN = 0.6, MM = RLEN * 1000, ZERO = 0.66;
  var RY = ZERO - (RLEN + 0.01) + 5 * (MM + 20) / (MM + 10) / 1000;
  function markY(cm) { return RY + (RLEN + 0.01) - (5 + cm * 10) * (MM + 20) / (MM + 10) / 1000; }
  function cmAt(y) { return ((RY + RLEN + 0.01 - y) * 1000 * (MM + 10) / (MM + 20) - 5) / 10; }
  var RS = cmAt(SURF), BAND1 = 16.0, BAND2 = 46.0, RF = cmAt(FLOOR);
  var D1 = (BAND1 - RS) / 100, D2 = (BAND2 - RS) / 100;        // true depths of the bands below the surface (m)
  function depthMax() { return (RF - RS) / 100 - p.r; }
  function yOf(depth) { return markY(RS + depth * 100); }

  var glassM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, metalness: 0, transparent: true, opacity: 0.2, clearcoat: 1, clearcoatRoughness: 0.05, depthWrite: false, side: T.DoubleSide });
  var glyM = new T.MeshStandardMaterial({ color: 0xdcb95c, roughness: 0.05, metalness: 0, transparent: true, opacity: 0.4, depthWrite: false, side: T.DoubleSide });
  var jar = new T.Group(); S.scene.add(jar);
  var prof = [[0, FOOT], [RO, FOOT], [RO, RIM - 0.002], [RO + 0.0025, RIM], [RI, RIM], [RI, FLOOR], [0, FLOOR]].map(function (q) { return new T.Vector2(q[0], q[1]); });
  var wall = new T.Mesh(new T.LatheGeometry(prof, 64), glassM); wall.renderOrder = 4; jar.add(wall);
  var foot = S.rounded(0.1, 0.1, FOOT, 0.02, new T.MeshPhysicalMaterial({ color: 0xdfe8ea, roughness: 0.08, transparent: true, opacity: 0.55 })); foot.rotation.x = -Math.PI / 2; foot.position.y = FOOT / 2; jar.add(foot);
  var gly = new T.Mesh(new T.CylinderGeometry(RI - 0.0003, RI - 0.0003, SURF - FLOOR, 48, 1, true), glyM); gly.position.y = (SURF + FLOOR) / 2; gly.renderOrder = 2; jar.add(gly);
  var top = new T.Mesh(new T.CircleGeometry(RI - 0.0003, 48), new T.MeshStandardMaterial({ color: 0xf3dc98, roughness: 0.02, metalness: 0.1, transparent: true, opacity: 0.6, depthWrite: false }));
  top.rotation.x = -Math.PI / 2; top.position.y = SURF; top.renderOrder = 3; jar.add(top);
  var bottomG = new T.Mesh(new T.CircleGeometry(RI - 0.0003, 48), glyM); bottomG.rotation.x = -Math.PI / 2; bottomG.position.y = FLOOR + 0.0004; jar.add(bottomG);
  var men = S.mesh(new T.TorusGeometry(RI - 0.0012, 0.0012, 8, 48), new T.MeshStandardMaterial({ color: 0xf2dc9c, roughness: 0.05, transparent: true, opacity: 0.5 }), false); men.rotation.x = Math.PI / 2; men.position.y = SURF + 0.0004; jar.add(men);
  var bandM = new T.MeshStandardMaterial({ color: 0x8a2a1e, roughness: 0.7 });
  var bands = [BAND1, BAND2].map(function (cm) { var b = S.mesh(new T.TorusGeometry(RO + 0.0016, 0.0017, 10, 56), bandM); b.rotation.x = Math.PI / 2; b.position.y = markY(cm); jar.add(b); return b; });
  var jl = S.label('GLYCERINE', { w: 0.05, ratio: 0.22, color: '#3b2a10', bg: '#f3ecd6' }); jl.position.set(0, FOOT + 0.07, RO + 0.0012); jar.add(jl);
  jar.position.set(JX, 0, JZ); S.contact(0.16, 0.16, JX, JZ, 0.5);
  var ruler = S.ruler(RLEN, { title: 'METRE SCALE · cm · LC 1 mm', labelEvery: 10 }); ruler.position.set(RX, RY, RZ);
  var rfoot = S.rounded(0.08, 0.06, 0.05, 0.008, M.darkWood); rfoot.rotation.x = -Math.PI / 2; rfoot.position.set(RX + 0.012, 0.025, RZ); S.scene.add(rfoot); S.contact(0.14, 0.11, RX + 0.012, RZ, 0.5);
  // steel balls in five small petri dishes, each with its size written on a paper slip
  var steel = new T.MeshStandardMaterial({ color: 0xe6e9ec, roughness: 0.08, metalness: 1 });
  var dishGeo = new T.LatheGeometry([[0, 0], [0.019, 0], [0.0205, 0.001], [0.0205, 0.009], [0.0192, 0.009], [0.0192, 0.0012], [0, 0.0012]].map(function (q) { return new T.Vector2(q[0], q[1]); }), 40);
  var tray = new T.Group(); S.scene.add(tray);
  var sheet = new T.Mesh(new T.PlaneGeometry(0.25, 0.085), M.paper); sheet.rotation.x = -Math.PI / 2; sheet.position.set(0, 0.0006, 0); sheet.receiveShadow = true; tray.add(sheet);
  var dishX = [-0.096, -0.048, 0, 0.048, 0.096], ballsIn = [];
  DIAS.forEach(function (d, i) { var dish = new T.Mesh(dishGeo, glassM); dish.position.set(dishX[i], 0.0008, -0.008); dish.renderOrder = 4; tray.add(dish);
    var lb = S.label(d + ' mm', { w: 0.03, ratio: 0.35, color: '#22305a', weight: 600 }); lb.rotation.x = -Math.PI / 2; lb.position.set(dishX[i], 0.0012, 0.026); tray.add(lb);
    var list = [];
    for (var j = 0; j < 4; j++) { var r = d / 2000, a = j * 1.7 + i, rr = 0.004 + (j % 2) * 0.004, b = S.mesh(new T.SphereGeometry(r, 20, 14), steel);
      b.position.set(dishX[i] + Math.cos(a) * rr, 0.002 + r, -0.008 + Math.sin(a) * rr); tray.add(b); list.push(b); }
    ballsIn.push(list); });
  var TRAY = new T.Vector3(0.24, 0, 0.1); tray.position.copy(TRAY); S.contact(0.3, 0.12, TRAY.x, TRAY.z, 0.3);
  var watch = S.stopwatch([-0.14, 0.035, 0.18], [-1.15, 0, -0.15]);
  // the falling ball (moved out of its dish when the hand picks it), and the ones already at the bottom
  var ball = null, landed = [];
  var OFFS = [[0.004, 0.002], [-0.005, 0.003], [0.002, -0.006], [-0.003, -0.004], [0.007, -0.001], [-0.007, 0.0], [0.0, 0.007], [0.005, 0.006]];

  S.addApparatus('jar', jar, 'Tall jar of glycerine', 'A tall, wide glass jar full of glycerine (density 1260 kg/m³). Its walls have little effect on a small ball at the centre.');
  S.addApparatus('bands', bands[0], 'Rubber bands', 'Two bands round the jar 30 cm apart. The upper one is well below the surface, so the ball is already at terminal velocity when it passes it.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Measures the distance between the two bands. Least count 1 mm.');
  S.addApparatus('balls', tray, 'Steel balls', 'Steel (density 7800 kg/m³), diameters 2–6 mm, measured with a screw gauge.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Start it at the upper band, stop it at the lower band.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudB = S.hudCard('Ball diameter'), hudD = S.hudCard('Depth below surface'), hudT = S.hudCard('Stopwatch');

  // ---------- actions
  function along(pts) { var L = [0]; for (var i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
    return function (k) { var d = Math.max(0, Math.min(1, k)) * L[L.length - 1]; for (var i = 1; i < pts.length; i++) if (d <= L[i] || i === pts.length - 1) { var f = (d - L[i - 1]) / Math.max(1e-9, L[i] - L[i - 1]); return pts[i - 1].clone().lerp(pts[i], Math.min(1, f)); } }; }
  function falling() { return st.phase === 'air' || st.phase === 'liquid'; }
  function readBand(i) {
    var r = i === 1 ? BAND1 : BAND2; if (i === 1) st.b1 = r; else st.b2 = r;
    if (st.b1 !== null && st.b2 !== null) st.dist = Math.round((st.b2 - st.b1) * 10) / 10;
    S.say((i === 1 ? 'Upper' : 'Lower') + ' band at ' + r.toFixed(1) + ' cm on the scale.' + (st.dist !== null ? ' Distance between the bands = ' + st.dist.toFixed(1) + ' cm.' : ''));
    S.render();
  }
  function choose(i) { if (falling()) { S.say('Wait until this ball reaches the bottom.'); return; } st.pick = i; p.r = DIAS[i] / 2000; S.render(); }
  function drop() {
    if (S.hand.busy) return Promise.resolve();
    if (st.dist === null) { S.say('First measure the distance between the two bands on the metre scale.'); return Promise.resolve(); }
    if (falling()) { S.say('A ball is still falling. Wait until it reaches the bottom.'); return Promise.resolve(); }
    var list = ballsIn[st.pick];
    if (!list.length) { S.say('No ' + DIAS[st.pick] + ' mm balls are left in this dish. Choose another size.'); return Promise.resolve(); }
    if (watch.on) { watch.on = false; }
    var b = list.pop(); b.updateMatrixWorld(true); var from = new T.Vector3(); b.getWorldPosition(from);
    tray.remove(b); S.scene.add(b); b.position.copy(from); ball = b; p.r = DIAS[st.pick] / 2000; st.left[st.pick] = list.length;
    var off = OFFS[st.drops % OFFS.length], over = new T.Vector3(JX + off[0], RIM + 0.012, JZ + off[1]);
    var path = along([from, from.clone().setY(0.12), new T.Vector3(over.x + 0.03, RIM + 0.06, over.z), over.clone().setY(RIM + 0.03), over]);
    st.phase = 'held'; st.drops++;
    return S.hand.pinchMove(from, function (k) { return path(k); }, function (k) { b.position.copy(path(k)); }, { ms: 1800, hold: 200 })
      .then(function () { st.phase = 'air'; st.air = b.position.y; st.airV = 0; st.t1 = null; S.render(); });
  }
  // the ball leaves the fingers just above the mouth; it falls through air onto the surface, then the kernel takes over
  function airStep(dt) { st.airV += p.g * dt; st.air -= st.airV * dt;
    if (st.air <= SURF + p.r * 0.2) { st.phase = 'liquid'; sim = K.init(p); sim.y = [0, st.airV]; } }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!falling() && !watch.on) { S.say('Drop a ball first, then time it between the two bands.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; watch.on = true; st.t1 = st.phase === 'liquid' ? sim.y[0] : -1; }
      else { watch.on = false; record(st.t1, st.phase === 'liquid' || st.phase === 'rest' ? sim.y[0] : -1); }
      S.render(); });
  }
  function record(y1, y2) {
    var t = Math.round(watch.t * 100) / 100;
    if (Math.abs(y1 - D1) > 0.015) { S.say('Start the watch exactly as the ball passes the upper band, not ' + (y1 < D1 ? 'before' : 'after') + ' it. Drop another ball.'); return; }
    if (Math.abs(y2 - D2) > 0.015) { S.say('Stop the watch exactly as the ball passes the lower band, not ' + (y2 < D2 ? 'before' : 'after') + ' it. Drop another ball.'); return; }
    var D = st.dist / 100, v = D / t;
    S.addRow({ d: DIAS[st.pick], r: DIAS[st.pick] / 2000, D: D, t: t, v: v });
    S.say('Written in your record book: ' + DIAS[st.pick] + ' mm ball, ' + st.dist.toFixed(1) + ' cm in ' + t.toFixed(2) + ' s, v = ' + (v * 100).toFixed(2) + ' cm/s.');
  }
  function timeOne() {   // auto: start at the upper band, stop at the lower band
    S.advance(120, function () { return st.phase === 'liquid' && sim.y[0] >= D1; });
    return pressWatch().then(function () { S.advance(120, function () { return sim.y[0] >= D2; }); return pressWatch(); })
      .then(function () { S.advance(60, function () { return st.phase === 'rest'; }); });
  }

  var EXP = {
    camera: { pos: [0.62, 0.62, 1.42], look: [0.03, 0.3, -0.04] },
    views: { jar: [[0.38, 0.5, 0.78], [0.0, 0.33, -0.05]], bands: [[0.26, 0.4, 0.55], [0.04, 0.35, -0.05]], ruler: [[0.26, 0.4, 0.55], [0.05, 0.35, -0.05]],
      setup: [[0.42, 0.48, 0.92], [0.06, 0.32, -0.04]], drop: [[0.46, 0.62, 0.86], [0.08, 0.36, -0.02]], fall: [[0.42, 0.42, 0.95], [0.02, 0.33, -0.04]],
      balls: [[0.38, 0.22, 0.38], [0.24, 0.0, 0.1]], sw: [[0.1, 0.5, 0.95], [-0.08, 0.3, 0.02]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A small sphere falling through a viscous liquid soon stops accelerating: its weight is balanced by the upthrust and the viscous drag 6πηrv. It then falls at a steady terminal velocity.',
      formula: 'v = 2 r² (ρ − σ) g / 9η', formulaNote: 'so η = 2 r² (ρ − σ) g / 9v · ρ = 7800 kg/m³ (steel), σ = 1260 kg/m³ (glycerine)',
      more: ['v is proportional to r². A graph of v against r² is a straight line through the origin, and η = 2 (ρ − σ) g / (9 × slope).'],
      precautions: 'Drop each ball gently at the centre of the surface, away from the walls. Start timing only below the upper band, when the speed is steady. Keep your eye level with each band as the ball passes it.' },
    book: { title: 'Expt. — Stokes\' Law', lines: ['Aim: to find η of glycerine from terminal velocity.', 'ρ (steel) = 7800 kg/m³, σ (glycerine) = 1260 kg/m³', 'Distance between bands D = ' + (BAND2 - BAND1).toFixed(1) + ' cm', 'v = D / t', 'η = 2 r² (ρ − σ) g / 9v', 'Precautions: drop at centre, time below upper band.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'd (mm)', get: function (r) { return r.d.toFixed(1); } },
        { label: 'r² (mm²)', get: function (r) { return (r.d * r.d / 4).toFixed(2); } }, { label: 't (s)', get: function (r) { return r.t.toFixed(2); } }, { label: 'v (cm/s)', get: function (r) { return (r.v * 100).toFixed(2); } }] },
    graph: { x: function (r) { return r.r * r.r * 1e6; }, y: function (r) { return r.v * 100; }, xlabel: 'r² (mm²)', ylabel: 'v (cm/s)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; } },
    result: function (rows) { if (rows.length < 2) return null; var s = S.fit.origin(rows.map(function (r) { return [r.r * r.r, r.v]; })); if (!(s > 0)) return null;
      return { label: 'η', value: 2 * (p.rho - p.sigma) * p.g / (9 * s), unit: 'Pa·s', digits: 2, truth: p.eta, note: 'From the slope of v against r².' }; },
    tol: 0.02,
    chips: ['Why does the ball stop speeding up?', 'Why must the upper band be well below the surface?', 'Why drop the ball at the centre?', 'Check my readings', 'How does temperature change η?'],
    viva: [['Why is the upper band placed well below the surface?', ['So the ball has reached terminal velocity before timing starts', 'So the band does not get wet', 'To make the time longer'], 0, 'Near the surface the ball is still speeding up.'],
      ['If the radius of the ball is doubled, its terminal velocity becomes', ['4 times', '2 times', 'half'], 0, 'v ∝ r².']],
    askState: function () { return { ball_diameter_mm: DIAS[st.pick], ball_state: st.phase, depth_below_surface_cm: st.phase === 'liquid' || st.phase === 'rest' ? +(sim.y[0] * 100).toFixed(1) : null,
      speed_cm_s: st.phase === 'liquid' ? +(sim.y[1] * 100).toFixed(3) : null, upper_band_cm: st.b1, lower_band_cm: st.b2, band_distance_cm: st.dist, stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2) }; },

    steps: [
      { id: 'setup', title: 'Measure', view: 'setup', render: function (u) {
          u.h2('Measure the distance between the bands');
          u.p('Two rubber bands are tied round the jar. Read each band on the metre scale with your eye level with it.');
          u.task('1. Read the upper band', st.b1 !== null, st.b1 !== null ? 'Upper band at ' + st.b1.toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button(st.b1 !== null ? 'Read' : 'Read the upper band', function () { S.focus('bands'); readBand(1); }, st.b1 === null, st.b1 !== null));
          u.task('2. Read the lower band', st.b2 !== null, st.b2 !== null ? 'Lower band at ' + st.b2.toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button(st.b2 !== null ? 'Read' : 'Read the lower band', function () { S.focus('bands'); readBand(2); }, st.b2 === null, st.b2 !== null));
          if (st.dist !== null) u.formula('D = ' + st.b2.toFixed(1) + ' − ' + st.b1.toFixed(1) + ' = ' + st.dist.toFixed(1) + ' cm');
          u.note('The upper band is about 10 cm below the surface, so the ball reaches its terminal velocity before you start timing.');
          u.next('Next: drop the balls', st.dist !== null);
        },
        ok: function () { return st.dist !== null; },
        auto: function () { readBand(1); readBand(2); return Promise.resolve(); } },
      { id: 'drop', title: 'Drop and time', view: 'drop', render: function (u) {
          u.h2('Drop a ball and time it');
          u.p('Choose a ball. The hand drops it gently at the centre of the surface. Press START as it passes the upper band and STOP as it passes the lower band.');
          var r = u.row(); DIAS.forEach(function (d, i) { r.appendChild(u.button(d + ' mm' + (st.pick === i ? ' ✓' : ''), function () { choose(i); }, st.pick === i, falling() || S.hand.busy || !ballsIn[i].length)); });
          u.row(u.button(falling() ? 'Falling…' : 'Drop the ball', function () { drop().then(function () { S.focus('fall'); }); }, true, falling() || S.hand.busy),
            u.button(watch.on ? 'STOP' : 'START', function () { pressWatch(); }, false, (!falling() && !watch.on) || S.hand.busy));
          u.live(function () { return DIAS[st.pick] + ' mm ball · ' + (st.phase === 'liquid' ? 'depth ' + (sim.y[0] * 100).toFixed(1) + ' cm' : st.phase === 'rest' ? 'at the bottom' : st.phase === 'held' ? 'in the hand' : st.phase === 'air' ? 'dropping' : 'in the dish') + ' · ' + watch.t.toFixed(2) + ' s'; });
          u.h3('Observation table'); u.table();
          var sizes = {}; S.rows.forEach(function (q) { sizes[q.d] = 1; }); var ns = Object.keys(sizes).length;
          u.next('Next: plot the graph', ns >= 3);
          if (ns < 3) u.p(ns + ' of at least 3 ball sizes timed (4 or 5 is better). Small balls fall slowly: be patient.');
        },
        ok: function () { var sz = {}; S.rows.forEach(function (q) { sz[q.d] = 1; }); return Object.keys(sz).length >= 3; },
        auto: function () { return [1, 2, 3, 4].reduce(function (pr, i) { return pr.then(function () { choose(i); return drop(); }).then(timeOne); }, Promise.resolve()); } },
    ],

    tick: function (dt) {
      if (st.phase === 'air') airStep(dt);
      else if (st.phase === 'liquid') { p.depth = depthMax(); K.step(sim, p, dt); if (sim.y[0] >= p.depth - 1e-9) { st.phase = 'rest'; landed.push(ball); S.render(); } }
      pose();
    },
  };
  function pose() {
    if (ball && st.phase !== 'held') { var x = ball.position.x, z = ball.position.z;
      ball.position.set(x, st.phase === 'air' ? Math.max(SURF, st.air) : st.phase === 'liquid' || st.phase === 'rest' ? yOf(sim.y[0]) : ball.position.y, z); }
    hudB.set(DIAS[st.pick] + ' mm'); hudD.set(st.phase === 'liquid' || st.phase === 'rest' ? (sim.y[0] * 100).toFixed(1) + ' cm' : '—'); hudT.set(watch.t.toFixed(2) + ' s');
  }
  pose();
  return EXP;
});
