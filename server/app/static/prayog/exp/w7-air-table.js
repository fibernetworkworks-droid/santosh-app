/* Prayogshala studio rig: a virtual air table for two-dimensional collisions (pack ug_mech_w7, kernel w7_coll2d).
   SIMULATED DATA, and said so. Puck B rests at the centre of a frictionless table; a spring launcher a sideways
   distance b from B's centre line sends puck A along +x. A strobe camera above flashes every 0.05 s; its photograph is
   drawn on the table's printed millimetre grid, and the student reads each dot to 1 mm and fits straight lines to get
   every velocity component. Every position comes from the kernel's own motion; the restitution e (the bumper rings)
   is hidden. Table coordinates: x to the right, y away from the student; B starts at the origin. */
HoolaStudio.define('w7-air-table', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.w7_coll2d, PI = Math.PI;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('w7_coll2d');
  var B0 = p.b, VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var TW = 1.0, TD = 0.7, TH = 0.1, OX = 0.1, ZB = -0.2, FL = 0.05, TEND = 0.85;   // table, B's start (table x), flash interval, time after impact
  var st = { dims: false, bSet: Math.round(B0 * 1000), running: false, done: false, shot: false, t: 0 };
  var sim = K.init(p);
  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 32), mat); }
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function rnd(v, lc) { return Math.round(v / lc) * lc; }
  function W(x, y, h) { return new T.Vector3(OX + x, TH + (h || 0), ZB - y); }   // table (x, y) -> world
  function tc() { return K.geo(p)[0]; }

  // ---------- the table, its grid (and the strobe photograph drawn on it)
  var legs = new T.Group(); S.scene.add(legs);
  [[-0.45, -0.3], [0.45, -0.3], [-0.45, 0.3], [0.45, 0.3]].forEach(function (q) { var l = box(0.03, TH - 0.02, 0.03, M.alu); l.position.set(q[0], (TH - 0.02) / 2, ZB + q[1]); legs.add(l); });
  var top = S.rounded(TW + 0.04, TD + 0.04, 0.02, 0.008, M.alu); top.rotation.x = -PI / 2; top.position.set(0, TH - 0.012, ZB); S.scene.add(top);
  S.contact(1.2, 0.85, 0, ZB, 0.5);
  var PX = 1600, PY = Math.round(PX * TD / TW), tex = S.liveTex(PX, PY);
  var surf = new T.Mesh(new T.PlaneGeometry(TW, TD), new T.MeshStandardMaterial({ map: tex, roughness: 0.35 })); surf.rotation.x = -PI / 2; surf.position.set(0, TH + 0.0005, ZB); S.scene.add(surf);
  function tx(x) { return (x + OX + TW / 2) / TW * PX; }   // table x (relative to B's start) -> pixel
  function ty(y) { return (TD / 2 - y) / TD * PY; }
  var dotsCache = null;
  function drawTable() {
    tex.draw(function (c) { c.fillStyle = '#eef3f6'; c.fillRect(0, 0, PX, PY); var i, mm = PX / (TW * 1000);
      for (i = 0; i <= TW * 100; i++) { var x = i * 10 * mm; c.strokeStyle = i % 10 === 0 ? 'rgba(40,70,110,.55)' : 'rgba(40,70,110,.18)'; c.lineWidth = i % 10 === 0 ? 2 : 1; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, PY); c.stroke(); }
      for (i = 0; i <= TD * 100; i++) { var y = i * 10 * mm; c.strokeStyle = i % 10 === 0 ? 'rgba(40,70,110,.55)' : 'rgba(40,70,110,.18)'; c.lineWidth = i % 10 === 0 ? 2 : 1; c.beginPath(); c.moveTo(0, y); c.lineTo(PX, y); c.stroke(); }
      c.fillStyle = 'rgba(30,50,80,.8)'; c.font = '600 22px "Public Sans", sans-serif'; c.fillText('grid: 1 cm squares, axes through B\'s starting point', 14, PY - 14);
      c.strokeStyle = 'rgba(20,20,20,.7)'; c.lineWidth = 2; c.beginPath(); c.moveTo(tx(-0.5), ty(0)); c.lineTo(tx(0.38), ty(0)); c.stroke(); c.beginPath(); c.moveTo(tx(0), ty(-0.33)); c.lineTo(tx(0), ty(0.33)); c.stroke();
      if (st.shot && dotsCache) { dotsCache.forEach(function (d) { c.fillStyle = d.w === 1 ? 'rgba(200,40,40,.85)' : 'rgba(40,80,200,.85)'; c.beginPath(); c.arc(tx(d.x), ty(d.y), 5, 0, 2 * PI); c.fill(); }); } });
  }
  // ---------- pucks, launcher, strobe camera
  var red = new T.MeshStandardMaterial({ color: 0xc23b3b, roughness: 0.4 }), blue = new T.MeshStandardMaterial({ color: 0x2f5fb8, roughness: 0.4 });
  var ringM = new T.MeshStandardMaterial({ color: p.e > 0.8 ? 0x2a2a2a : 0x8a7a5a, roughness: 0.9 });
  function puck(mat, lbl) { var g = new T.Group(); S.scene.add(g); var b = cyl(p.R - 0.004, 0.018, mat); b.position.y = 0.011; g.add(b);
    var r = S.mesh(new T.TorusGeometry(p.R - 0.003, 0.004, 10, 40), ringM); r.rotation.x = PI / 2; r.position.y = 0.011; g.add(r);
    var l = S.label(lbl, { w: 0.04, ratio: 0.5, color: '#ffffff' }); l.rotation.x = -PI / 2; l.position.y = 0.0205; g.add(l); return g; }
  var pA = puck(red, 'A ' + Math.round(p.m1 * 1000) + ' g'), pB = puck(blue, 'B ' + Math.round(p.m2 * 1000) + ' g');
  var launcher = new T.Group(); S.scene.add(launcher);
  var lb = box(0.06, 0.03, 0.05, M.iron); lb.position.y = 0.015; launcher.add(lb); var lr = cyl(0.004, 0.05, M.chrome, 10); lr.rotation.z = PI / 2; lr.position.set(0.035, 0.018, 0); launcher.add(lr);
  var trig = cyl(0.007, 0.01, M.red, 16); trig.position.set(-0.01, 0.035, 0); launcher.add(trig);
  var cam = new T.Group(); S.scene.add(cam); var cpost = cyl(0.006, 0.75, M.chrome); cpost.position.set(-0.56, 0.4, ZB - 0.3); cam.add(cpost);
  var carm = cyl(0.005, 0.5, M.chrome); carm.rotation.z = PI / 2; carm.position.set(-0.32, 0.77, ZB - 0.3); cam.add(carm);
  var cbody = S.rounded(0.08, 0.06, 0.05, 0.008, M.black); cbody.position.set(-0.08, 0.76, ZB - 0.3); cam.add(cbody);
  var flash = cyl(0.016, 0.01, M.white, 20); flash.position.set(-0.08, 0.725, ZB - 0.3); cam.add(flash);
  var cbase = S.rounded(0.12, 0.1, 0.016, 0.006, M.iron); cbase.rotation.x = -PI / 2; cbase.position.set(-0.56, 0.008, ZB - 0.3); cam.add(cbase);
  function pose() { var v = K.view(sim, p), a = W(v.x1, v.y1), b = W(v.x2, v.y2); pA.position.copy(a); pB.position.copy(b);
    var l = W(p.x0 - p.R - 0.035, p.b); launcher.position.set(l.x, TH, l.z); }
  pose(); drawTable();

  S.addApparatus('table', surf, 'Air table (simulated)', 'Air from tiny holes lifts the pucks, so they glide without friction. The surface is printed with a 1 cm grid; its axes pass through B\'s starting point.');
  S.addApparatus('pA', pA, 'Puck A (' + Math.round(p.m1 * 1000) + ' g)', 'Launched along +x at about ' + p.u.toFixed(2) + ' m/s. Its rim carries the same bumper ring as B.');
  S.addApparatus('pB', pB, 'Puck B (' + Math.round(p.m2 * 1000) + ' g)', 'Rests at the origin until it is struck. Radius ' + (p.R * 100).toFixed(1) + ' cm, like A.');
  S.addApparatus('launcher', launcher, 'Spring launcher', 'Its slide sets the sideways offset b of puck A from the line through B\'s centre.');
  S.addApparatus('cam', cam, 'Strobe camera', 'Flashes every ' + (FL * 1000).toFixed(0) + ' ms with the shutter open, so each puck leaves a row of dots.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hud1 = S.hudCard('Offset b'), hud2 = S.hudCard('Time');

  var DIMS = 'Puck A: m1 = ' + Math.round(p.m1 * 1000) + ' g. Puck B: m2 = ' + Math.round(p.m2 * 1000) + ' g (balance). Radius of each R = ' + (p.R * 100).toFixed(1) + ' cm. Strobe interval ' + (FL * 1000).toFixed(0) + ' ms.';
  function measure() { if (st.dims) return; st.dims = true; S.say(DIMS + ' Written in your record book.'); S.focus('pA'); S.book.draw(); S.render(); }
  function setB() { if (S.hand.busy || st.running) return Promise.resolve(); return S.hand.tap(lb).then(function () { p.b = st.bSet / 1000; sim.t = 0; st.done = false; st.shot = false; dotsCache = null; pose(); drawTable(); S.click(1500);
    S.say('The launcher is ' + st.bSet + ' mm to the side of B\'s centre line.'); S.render(); }); }
  function launch() { if (S.hand.busy || st.running) return Promise.resolve(); if (!st.dims) { S.say('Weigh the pucks first.'); return Promise.resolve(); }
    if (p.b >= 2 * p.R) { S.say('At this offset A misses B. Bring the launcher closer to the centre line.'); return Promise.resolve(); }
    return S.hand.tap(trig).then(function () { sim.t = 0; st.shot = false; dotsCache = null; drawTable(); st.running = true; st.done = false; S.click(900); S.say('Puck A is launched; the strobe camera is open.'); S.render(); }); }
  function dots() { var out = [], tEnd = tc() + TEND, k, t, v;
    for (k = 0; k * FL <= tEnd + 1e-9; k++) { t = k * FL; v = K.view({ t: t }, p); out.push({ k: k, t: t, w: 1, x: rnd(v.x1, 0.001), y: rnd(v.y1, 0.001) }); if (t > tc()) out.push({ k: k, t: t, w: 2, x: rnd(v.x2, 0.001), y: rnd(v.y2, 0.001) }); }
    return out; }
  function fitV(list) { var fx = S.fit.linear(list.map(function (d) { return [d.t, d.x]; })), fy = S.fit.linear(list.map(function (d) { return [d.t, d.y]; })); return [fx ? fx.m : NaN, fy ? fy.m : NaN]; }
  function readTracks() { if (!st.done) { S.say('Launch puck A and let the run finish first.'); return; }
    if (S.rows.some(function (r) { return Math.abs(r.b - p.b) < 1e-9; })) { S.say('You already have a run at this offset. Change b.'); return; }
    var D = dots(), t0 = tc(), gap = 1.5 * FL;                       // the dots within a flash or so of the impact are left out of the fits
    dotsCache = D; st.shot = true; drawTable();
    var before = D.filter(function (d) { return d.w === 1 && d.t < t0 - gap; }), a1 = D.filter(function (d) { return d.w === 1 && d.t > t0 + gap; }), b2 = D.filter(function (d) { return d.w === 2 && d.t > t0 + gap; });
    var u = fitV(before), v1 = fitV(a1), v2 = fitV(b2);
    S.addRow({ b: p.b, ux: u[0], uy: u[1], v1x: v1[0], v1y: v1[1], v2x: v2[0], v2y: v2[1] });
    S.say('Strobe photograph read: ' + before.length + ' dots of A before, ' + a1.length + ' of A and ' + b2.length + ' of B after. Velocities written in the table.'); }
  function sums(r) { var P0x = p.m1 * r.ux, P0y = p.m1 * r.uy, Px = p.m1 * r.v1x + p.m2 * r.v2x, Py = p.m1 * r.v1y + p.m2 * r.v2y;
    var K0 = p.m1 * (r.ux * r.ux + r.uy * r.uy), K1 = p.m1 * (r.v1x * r.v1x + r.v1y * r.v1y) + p.m2 * (r.v2x * r.v2x + r.v2y * r.v2y);
    return { px: Px / P0x, py: (Py - P0y) / P0x, ke: K1 / K0 }; }
  function predicted(b) { var q = {}; Object.keys(p).forEach(function (k) { q[k] = p[k]; }); q.b = b; return HK.TEXTBOOK.w7_coll2d_ke(q); }
  function f3(v) { return isFinite(v) ? v.toFixed(3) : '—'; }

  return {
    camera: { pos: [0.0, 1.15, 0.95], look: [-0.02, 0.08, ZB] },
    views: { main: [[0.0, 1.12, 0.92], [-0.02, 0.08, ZB]], table: [[-0.02, 1.25, 0.35], [-0.02, 0.1, ZB]], pA: [[-0.25, 0.35, 0.25], [-0.3, 0.1, ZB]], pB: [[0.1, 0.35, 0.25], [0.1, 0.1, ZB]],
      launcher: [[-0.35, 0.3, 0.25], [-0.4, 0.1, ZB]], cam: [[-0.2, 0.9, 0.5], [-0.3, 0.6, ZB - 0.3]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: 'm1 u = m1 v1 + m2 v2 (x and y);   KE kept = 1 − (1 − e²) m2/(m1 + m2) cos²φ', formulaNote: 'sin φ = b / 2R. e = 1 for an elastic collision, e < 1 for an inelastic one.',
      more: [S.lab.aim], precautions: 'SIMULATED DATA: the table, the pucks and the photograph are computed. Read each dot at its centre. Leave out the dots taken while the pucks were touching.' },
    book: { title: 'Expt. — Two-dimensional collisions (virtual)', lines: ['Aim: momentum and kinetic energy in an oblique collision.', 'm1 = ' + Math.round(p.m1 * 1000) + ' g,  m2 = ' + Math.round(p.m2 * 1000) + ' g,  R = ' + (p.R * 100).toFixed(1) + ' cm', 'strobe ' + (FL * 1000).toFixed(0) + ' ms; velocities from straight-line fits'],
      columns: [{ label: 'b (mm)', get: function (r) { return (r.b * 1000).toFixed(0); } }, { label: 'u (m/s)', get: function (r) { return f3(r.ux); } }, { label: 'v1x, v1y', get: function (r) { return f3(r.v1x) + ', ' + f3(r.v1y); } },
        { label: 'v2x, v2y', get: function (r) { return f3(r.v2x) + ', ' + f3(r.v2y); } }, { label: 'Px′/Px', get: function (r) { return sums(r).px.toFixed(4); } }, { label: 'Py′/Px', get: function (r) { return sums(r).py.toFixed(4); } },
        { label: 'KE′/KE', get: function (r) { return sums(r).ke.toFixed(4); } }] },
    result: function (rows) { if (rows.length < 3) return null; var r0 = rows.filter(function (r) { return Math.abs(r.b - B0) < 1e-9; })[0]; if (!r0) return null;
      var note = rows.map(function (r) { var q = sums(r); return 'b = ' + (r.b * 1000).toFixed(0) + ' mm: Px′/Px = ' + q.px.toFixed(4) + ', Py′/Px = ' + q.py.toFixed(4) + ', KE′/KE = ' + q.ke.toFixed(4) + ' (theory ' + predicted(r.b).toFixed(4) + ')'; }).join('; ');
      return { label: 'KE after ÷ KE before (b = ' + (B0 * 1000).toFixed(0) + ' mm)', value: sums(r0).ke, unit: '', digits: 4, truth: predicted(B0), note: 'Momentum is kept in both directions in every run. ' + note + '.' }; },
    tol: 0.03,
    chips: ['Why is momentum kept but not always energy?', 'What does the offset b change?', 'Check my readings', 'Why leave out the dots near the impact?'],
    viva: [['The total momentum of the two pucks after the collision is', ['the same as before, in both directions', 'larger than before', 'the same only along x'], 0, 'No outside force acts along the table during the impact.']],
    askState: function () { var v = K.view(sim, p); return { simulated: true, offset_b_mm: +(p.b * 1000).toFixed(0), running: st.running, run_done: st.done, puckA_mm: [Math.round(v.x1 * 1000), Math.round(v.y1 * 1000)], puckB_mm: [Math.round(v.x2 * 1000), Math.round(v.y2 * 1000)], runs: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'main', render: function (u) { u.h2('Weigh the pucks');
          u.p('SIMULATED DATA: this air table is a virtual one. Both momentum and kinetic energy need the masses.');
          u.task('Weigh both pucks and note the strobe interval', st.dims, st.dims ? DIMS : 'Balance and the camera\'s setting').add(u.button(st.dims ? 'Done' : 'Weigh', measure, !st.dims, st.dims));
          if (SAMPLE) u.note('Sample: ' + SAMPLE + '.');
          u.next('Next: launch the pucks', st.dims); },
        ok: function () { return st.dims; }, auto: function () { measure(); return Promise.resolve(); } },
      { id: 'runs', title: 'Runs', view: 'table', render: function (u) { u.h2('Launch, photograph, read the tracks');
          u.slider('Sideways offset of the launcher b', 0, 70, 5, function () { return st.bSet; }, function (v) { st.bSet = v; }, 'mm');
          u.row(u.button('Slide the launcher to b', function () { setB(); }, true, S.hand.busy || st.running), u.button('Launch puck A', function () { launch(); }, false, S.hand.busy || st.running),
            u.button('Read the strobe photograph', readTracks, false, !st.done));
          u.live(function () { return 'b = ' + (p.b * 1000).toFixed(0) + ' mm · ' + (st.running ? 'pucks moving' : st.done ? 'run finished' : 'ready'); });
          u.h3('Observation table'); u.table(); var ok = S.rows.length >= 3 && S.rows.some(function (r) { return Math.abs(r.b - B0) < 1e-9; });
          if (!ok) u.p('Read at least 3 runs at different offsets, one of them at b = ' + (B0 * 1000).toFixed(0) + ' mm.'); u.next('Next: test the conservation laws', ok); },
        ok: function () { return S.rows.length >= 3 && S.rows.some(function (r) { return Math.abs(r.b - B0) < 1e-9; }); },
        auto: function () { return [Math.round(B0 * 1000), 10, 50, 20].filter(function (v, i, a) { return a.indexOf(v) === i; }).slice(0, 3).reduce(function (pr, b) { return pr.then(function () { st.bSet = b; return setB(); })
          .then(function () { return launch(); }).then(function () { S.advance(5, function () { return st.done; }); readTracks(); }); }, Promise.resolve()); } },
    ],
    tick: function (dt) {
      if (st.running) { K.step(sim, p, dt); if (sim.t >= tc() + TEND) { sim.t = tc() + TEND; st.running = false; st.done = true; } }
      pose(); hud1.set((p.b * 1000).toFixed(0) + ' mm'); hud2.set(sim.t.toFixed(2) + ' s'); },
  };
});
