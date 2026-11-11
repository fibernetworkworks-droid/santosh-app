/* Prayogshala studio rig: sliding and rolling friction of a trolley on an inclined plane (pack ug_mech_w7, kernel
   w7_trolley). A plank is hinged at its lower end and rests on a lab jack a distance l up the slope; a vernier height
   gauge reads the height h of that support, so sin θ = h / l. An electromagnet at the top holds the trolley over the
   first photo-gate; switching it off releases the trolley from rest and starts the timer, and the second photo-gate a
   distance d down the slope stops it. A lever on the trolley locks or frees its wheels. Every time comes from the
   kernel's own motion (stepped in the tick); the hidden friction coefficients are what the student measures. */
HoolaStudio.define('w7-trolley-incline', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.w7_trolley, PI = Math.PI;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('w7_trolley');
  var LOCK0 = p.lock > 0.5 ? 1 : 0;                       // the state of the wheels this lab is about
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var LSUP = 1.2, XS = 1.15, HX = -0.55, BT = 0.025, PL = 1.3, PT = 0.02, PW = 0.18, ZB = -0.2;   // hinge to jack l, start of the run, geometry
  var RANGE = { 1: { min: 300, max: 650, step: 10, auto: [400, 450, 500, 550, 600] }, 0: { min: 20, max: 100, step: 2, auto: [30, 40, 50, 60, 70] } };
  var st = { dims: false, hSet: RANGE[LOCK0].auto[0], h: 0, running: false, done: false, t: 0, tg: 0, held: true, prevS: 0, prevT: 0 };
  p.lock = LOCK0;
  var sim = K.init(p);
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 24), mat); }
  function rnd(v, lc) { return Math.round(v / lc) * lc; }
  function setAngleFromH(hmm) { st.h = hmm; p.angle = Math.asin(hmm / 1000 / LSUP); }

  // ---------- base board, hinge, plank
  var base = S.rounded(1.5, 0.3, BT, 0.01, M.darkWood); base.rotation.x = -PI / 2; base.position.set(HX + 0.7, BT / 2, ZB); S.scene.add(base);
  S.contact(1.6, 0.4, HX + 0.7, ZB, 0.55);
  var hinge = cyl(0.007, PW * 0.8, M.brass); hinge.rotation.x = PI / 2; hinge.position.set(HX, BT + 0.004, ZB); S.scene.add(hinge);
  var plank = new T.Group(); plank.position.set(HX, BT, ZB); S.scene.add(plank);
  var pm = S.rounded(PL, PT, PW, 0.004, M.wood); pm.position.set(PL / 2, PT / 2, 0); plank.add(pm);
  var stop = S.rounded(0.03, 0.04, PW - 0.02, 0.004, M.darkWood); stop.position.set(0.03, PT + 0.02, 0); plank.add(stop);
  var foam = box(0.012, 0.035, PW - 0.04, M.rubber); foam.position.set(0.051, PT + 0.02, 0); plank.add(foam);
  [-1, 1].forEach(function (sg) { var rail = box(PL - 0.08, 0.008, 0.006, M.alu); rail.position.set(PL / 2, PT + 0.004, sg * 0.05); plank.add(rail); });
  // ---------- the trolley: body, four wheels, lock lever, iron plate for the magnet
  var trol = new T.Group(); plank.add(trol);
  var tb = S.rounded(0.12, 0.035, 0.085, 0.006, new T.MeshStandardMaterial({ color: 0x2f6db5, roughness: 0.45, metalness: 0.3 })); tb.position.y = 0.032; trol.add(tb);
  var wheels = [];
  [[-0.04, -0.05], [-0.04, 0.05], [0.04, -0.05], [0.04, 0.05]].forEach(function (q) { var w = cyl(0.0125, 0.008, M.black, 28); w.rotation.x = PI / 2; w.position.set(q[0], PT + 0.0045, q[1]); trol.add(w); wheels.push(w);
    var hub = cyl(0.004, 0.009, M.chrome, 12); hub.rotation.x = PI / 2; hub.position.copy(w.position); trol.add(hub); });
  var lever = new T.Group(); lever.position.set(-0.03, 0.052, 0.03); trol.add(lever);
  var lv = box(0.004, 0.03, 0.004, M.red); lv.position.y = 0.015; lever.add(lv); var lk = S.mesh(new T.SphereGeometry(0.005, 12, 10), M.red); lk.position.y = 0.031; lever.add(lk);
  var plate = box(0.004, 0.025, 0.04, M.iron); plate.position.set(0.062, 0.032, 0); trol.add(plate);
  var flag = box(0.02, 0.03, 0.002, M.black); flag.position.set(0, 0.065, -0.045); trol.add(flag);
  // ---------- electromagnet at the top and the two photo-gates
  var mag = new T.Group(); mag.position.set(XS + 0.075, PT, 0); plank.add(mag);
  var mb = box(0.02, 0.05, 0.05, M.iron); mb.position.set(0.0, 0.03, 0); mag.add(mb); var coil = cyl(0.014, 0.025, M.copper, 20); coil.rotation.z = PI / 2; coil.position.set(-0.012, 0.032, 0); mag.add(coil);
  function gate(x) { var g = new T.Group(); g.position.set(x, PT, 0); plank.add(g);
    [-0.065, 0.065].forEach(function (z) { var pr = box(0.014, 0.1, 0.014, M.black); pr.position.set(0, 0.05, z); g.add(pr); });
    var top = box(0.014, 0.012, 0.144, M.black); top.position.set(0, 0.104, 0); g.add(top);
    var led = cyl(0.003, 0.004, M.red, 12); led.rotation.x = PI / 2; led.position.set(0, 0.08, -0.057); g.add(led); return g; }
  var g1 = gate(XS), g2 = gate(XS - p.d);
  // ---------- the lab jack under the plank and the vernier height gauge beside it
  var jack = new T.Group(); S.scene.add(jack);
  var jb = S.rounded(0.16, 0.16, 0.016, 0.006, M.alu); jb.rotation.x = -PI / 2; jb.position.y = 0.008; jack.add(jb);
  var jtop = box(0.15, 0.012, 0.15, M.alu); jack.add(jtop);
  var jcol = box(0.03, 1, 0.03, M.chrome); jack.add(jcol);
  var gaugeG = new T.Group(); S.scene.add(gaugeG);
  var gb = S.rounded(0.1, 0.07, 0.016, 0.005, M.iron); gb.rotation.x = -PI / 2; gb.position.y = 0.008; gaugeG.add(gb);
  var gpost = S.ruler(0.7, { title: 'mm · vernier 0.1 mm', labelEvery: 100, unitDiv: 1, width: 0.026 }); gaugeG.add(gpost); gpost.position.set(0, BT - 0.7 + 0.7, 0);
  var slider = box(0.05, 0.012, 0.03, M.chrome); gaugeG.add(slider);
  // ---------- timer box
  var tim = new T.Group(); tim.position.set(0.45, 0, 0.18); S.scene.add(tim);
  var tbx = S.rounded(0.16, 0.07, 0.1, 0.008, new T.MeshStandardMaterial({ color: 0x2b3440, roughness: 0.5 })); tbx.position.y = 0.035; tim.add(tbx);
  var ttex = S.liveTex(512, 160), tscr = new T.Mesh(new T.PlaneGeometry(0.12, 0.036), new T.MeshBasicMaterial({ map: ttex, toneMapped: false })); tscr.position.set(0, 0.045, 0.0505); tim.add(tscr);
  var tl = S.label('GATE TIMER  1 ms', { w: 0.1, ratio: 0.15, color: '#e8ecf0' }); tl.position.set(0, 0.016, 0.0506); tim.add(tl);
  var relBtn = cyl(0.008, 0.008, M.green); relBtn.rotation.x = PI / 2; relBtn.position.set(0.065, 0.05, 0.052); tim.add(relBtn);
  S.contact(0.22, 0.16, 0.45, 0.18, 0.5);
  S.wire([[0.4, 0.04, 0.14], [0.2, 0.01, 0.0], [HX + (XS - p.d) * 0.95, 0.03, ZB + 0.1]], 'black');
  S.wire([[0.45, 0.04, 0.14], [0.4, 0.01, 0.0], [HX + XS * 0.92, 0.05, ZB + 0.1]], 'black');
  var lastTxt = '';
  function drawTimer() { var txt = (st.running ? st.t : st.tg).toFixed(3) + ' s'; if (txt === lastTxt) return; lastTxt = txt;
    ttex.draw(function (x) { x.fillStyle = '#0c1a10'; x.fillRect(0, 0, 512, 160); x.fillStyle = '#7dff9b'; x.font = '700 92px "JetBrains Mono", monospace'; x.textAlign = 'center'; x.fillText(txt, 256, 112); }); }

  function pose() {
    plank.rotation.z = p.angle;
    trol.position.set(XS - sim.s, 0, 0);
    lever.rotation.z = p.lock > 0.5 ? 0.6 : -0.6;
    var c = Math.cos(p.angle), sn = Math.sin(p.angle), jx = HX + LSUP * c, jy = BT + LSUP * sn - PT * c * 0 ;
    jack.position.set(jx, 0, ZB); jtop.position.set(0, jy - 0.006, 0); jcol.scale.y = Math.max(0.01, jy - 0.02); jcol.position.set(0, (jy - 0.012) / 2 + 0.004, 0);
    gaugeG.position.set(jx + 0.13, 0, ZB + 0.02); slider.position.set(-0.03, jy, 0);
    var rot = sim.s / 0.0125; if (p.lock < 0.5) wheels.forEach(function (w) { w.rotation.y = rot; });
  }
  setAngleFromH(st.hSet); pose(); drawTimer();

  S.addApparatus('plank', plank, 'Inclined plane', 'A 1.3 m plank hinged at its lower end. It rests on the lab jack ' + (LSUP * 100).toFixed(0) + ' cm up the slope from the hinge (l), so sin θ = h / l.');
  S.addApparatus('trol', trol, 'Trolley', 'A four-wheeled trolley. The red lever locks the wheels (they then slide) or frees them (they roll).');
  S.addApparatus('jack', jack, 'Lab jack', 'Raise or lower it to set the height h of the plank at the support.');
  S.addApparatus('gauge', gaugeG, 'Vernier height gauge', 'Reads the height of the plank\'s underside at the support above the base board. Least count 0.1 mm.');
  S.addApparatus('gates', g2, 'Photo-gates', 'The first gate is under the electromagnet, the second ' + (p.d * 100).toFixed(1) + ' cm down the slope (d). The trolley\'s black flag cuts each beam.');
  S.addApparatus('mag', mag, 'Electromagnet release', 'Holds the trolley at rest over the first gate. Switching it off releases the trolley and starts the timer.');
  S.addApparatus('tim', tim, 'Gate timer', 'Starts when the magnet releases the trolley and stops when the flag cuts the second gate. Reads to 1 ms.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hud1 = S.hudCard('Height h'), hud2 = S.hudCard('Timer'), hud3 = S.hudCard('Wheels');

  var DIMS = 'Hinge to support l = ' + (LSUP * 100).toFixed(1) + ' cm (metre scale). Gate to gate d = ' + (p.d * 100).toFixed(1) + ' cm. g = ' + p.g.toFixed(2) + ' m/s².';
  function measure() { if (st.dims) return; st.dims = true; S.say(DIMS + ' Written in your record book.'); S.focus('plank'); S.book.draw(); S.render(); }
  function moves() { return K.acc(p) > 0; }
  function setLock(v) { if (S.hand.busy || st.running) return Promise.resolve(); return S.hand.tap(lk).then(function () { p.lock = v; S.click(1500); pose(); S.say(v ? 'Wheels locked: the trolley will slide.' : 'Wheels free: the trolley will roll.'); S.render(); }); }
  function setHeight() { if (S.hand.busy || st.running) return Promise.resolve(); if (!st.dims) { S.say('Measure l and d first.'); return Promise.resolve(); }
    var r = RANGE[p.lock > 0.5 ? 1 : 0], v = Math.max(r.min, Math.min(r.max, st.hSet));
    return S.hand.tap(jtop).then(function () { sim.s = 0; sim.v = 0; sim.t = 0; st.done = false; st.tg = 0; setAngleFromH(v); pose(); drawTimer(); S.click(1500);
      S.say('The gauge reads h = ' + v.toFixed(1) + ' mm: θ = ' + (p.angle * 180 / PI).toFixed(2) + '°.'); S.render(); }); }
  function release() { if (S.hand.busy || st.running) return Promise.resolve(); if (!st.dims) { S.say('Measure l and d first.'); return Promise.resolve(); }
    if (st.h <= 0) { S.say('Set the height of the plane first.'); return Promise.resolve(); }
    return S.hand.tap(relBtn).then(function () {
      sim.s = 0; sim.v = 0; sim.t = 0; st.t = 0; st.tg = 0; st.prevS = 0; st.prevT = 0; st.done = false;
      if (!moves()) { S.say('The magnet lets go, but the trolley stays where it is: friction holds it at this angle. Raise the plane.'); S.render(); return; }
      st.running = true; S.click(1200); S.say('Released. The timer is running.'); S.render(); }); }
  function finished() { return st.done; }
  function record() { if (!st.done) { S.say('Release the trolley and let it pass the second gate first.'); return; }
    var lock = p.lock > 0.5 ? 1 : 0;
    if (S.rows.some(function (r) { return r.lock === lock && Math.abs(r.h - st.h) < 1e-9; })) { S.say('You already have this height with the wheels ' + (lock ? 'locked' : 'free') + '. Change the height.'); return; }
    S.addRow({ lock: lock, h: rnd(st.h, 0.1), t: rnd(st.tg, 0.001) }); S.say('h = ' + st.h.toFixed(1) + ' mm, t = ' + st.tg.toFixed(3) + ' s, wheels ' + (lock ? 'locked' : 'free') + '. Written in the table.'); }
  function calc(r) { var th = Math.asin(r.h / 1000 / LSUP), a = 2 * p.d / (r.t * r.t); return { th: th, a: a, mu: Math.tan(th) - a / (p.g * Math.cos(th)) }; }
  function rowsOf(rows, lock) { return rows.filter(function (r) { return r.lock === lock; }); }
  function meanMu(rows) { var m = rows.map(function (r) { return calc(r).mu; }); return m.length ? m.reduce(function (a, b) { return a + b; }, 0) / m.length : NaN; }
  function truthOf(lock) { var q = {}; Object.keys(p).forEach(function (k) { q[k] = p[k]; }); q.lock = lock; return HK.TEXTBOOK.w7_trolley_mu(q); }
  var NAME = { 1: 'sliding (wheels locked)', 0: 'rolling (wheels free)' };

  return {
    camera: { pos: [0.1, 0.75, 1.75], look: [0.05, 0.22, ZB] },
    views: { main: [[0.1, 0.72, 1.7], [0.05, 0.22, ZB]], plank: [[0.2, 0.6, 1.2], [0.05, 0.25, ZB]], trol: [[0.6, 0.7, 0.4], [0.4, 0.4, ZB]], jack: [[0.95, 0.4, 0.5], [0.5, 0.2, ZB]],
      gauge: [[0.95, 0.4, 0.4], [0.65, 0.25, ZB]], gates: [[0.0, 0.3, 0.5], [-0.05, 0.1, ZB]], mag: [[0.8, 0.8, 0.4], [0.5, 0.5, ZB]], tim: [[0.45, 0.25, 0.55], [0.45, 0.04, 0.18]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: 'μ = tan θ − 2d / (g t² cos θ)', formulaNote: 'sin θ = h / l. From rest over a distance d, a = 2d / t² = g (sin θ − μ cos θ).',
      more: [S.lab.aim], precautions: S.lab.safety + ' Check that the trolley runs straight between the rails. Read the height gauge at the support, not elsewhere along the plank.' },
    book: { title: 'Expt. — Friction of a trolley on an inclined plane', lines: ['Aim: coefficients of sliding and rolling friction.', 'l = ' + (LSUP * 100).toFixed(1) + ' cm,  d = ' + (p.d * 100).toFixed(1) + ' cm,  g = ' + p.g.toFixed(2) + ' m/s²', 'sin θ = h / l,  μ = tan θ − 2d / (g t² cos θ)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Wheels', get: function (r) { return r.lock ? 'locked' : 'free'; } }, { label: 'h (mm)', get: function (r) { return r.h.toFixed(1); } },
        { label: 'θ (°)', get: function (r) { return (calc(r).th * 180 / PI).toFixed(2); } }, { label: 't (s)', get: function (r) { return r.t.toFixed(3); } }, { label: 'a (m/s²)', get: function (r) { return calc(r).a.toFixed(4); } },
        { label: 'μ', get: function (r) { return calc(r).mu.toFixed(4); } }] },
    graph: { x: function (r) { return Math.tan(calc(r).th); }, y: function (r) { return calc(r).a / (p.g * Math.cos(calc(r).th)); }, xlabel: 'tan θ', ylabel: 'a / (g cos θ)', line: function (pts) { var f = S.fit.linear(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) { var mine = rowsOf(rows, LOCK0); if (mine.length < 3) return null; var mu = meanMu(mine), other = rowsOf(rows, 1 - LOCK0);
      var f = S.fit.linear(mine.map(function (r) { var c = calc(r); return [Math.tan(c.th), c.a / (p.g * Math.cos(c.th))]; }));
      var note = 'Mean of ' + mine.length + ' runs. On the graph of a / (g cos θ) against tan θ the slope is ' + (f ? f.m.toFixed(3) : '—') + ' (theory 1) and the intercept is ' + (f ? (-f.c).toFixed(4) : '—') + ' = −μ.';
      if (other.length) note += ' With the wheels ' + (LOCK0 ? 'free' : 'locked') + ': μ = ' + meanMu(other).toFixed(4) + ' from ' + other.length + ' run' + (other.length > 1 ? 's' : '') + '.';
      return { label: 'μ ' + NAME[LOCK0], value: mu, unit: '', digits: 4, truth: truthOf(LOCK0), note: note }; },
    tol: 0.03,
    chips: ['Why is rolling friction so small?', 'How is θ found from h?', 'Check my readings', 'Why does the trolley not move?'],
    viva: [['Sliding friction is found here from', ['the time to roll a known distance from rest', 'the mass of the trolley', 'the area of the wheels'], 0, 'a = 2d / t² and a = g (sin θ − μ cos θ) give μ.']],
    askState: function () { return { wheels: p.lock > 0.5 ? 'locked' : 'free', height_mm: +st.h.toFixed(1), angle_deg: +(p.angle * 180 / PI).toFixed(2), timer_s: +(st.running ? st.t : st.tg).toFixed(3), running: st.running, readings: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'main', render: function (u) { u.h2('Measure the plane');
          u.p('The angle will come from the height of the support, so its distance l from the hinge is needed, and the distance d between the gates.');
          u.task('Measure l and d', st.dims, st.dims ? DIMS : 'Metre scale along the plank').add(u.button(st.dims ? 'Measured' : 'Measure', measure, !st.dims, st.dims));
          if (SAMPLE) u.note('Sample: ' + SAMPLE + '.');
          u.next('Next: time the trolley', st.dims); },
        ok: function () { return st.dims; }, auto: function () { measure(); return Promise.resolve(); } },
      { id: 'runs', title: 'Runs', view: 'main', render: function (u) { u.h2('Release the trolley at several heights');
          u.row(u.button('Lock the wheels', function () { setLock(1); }, p.lock > 0.5, S.hand.busy || st.running), u.button('Free the wheels', function () { setLock(0); }, p.lock < 0.5, S.hand.busy || st.running));
          var r = RANGE[p.lock > 0.5 ? 1 : 0];
          u.slider('Height of the support h', r.min, r.max, r.step, function () { return st.hSet; }, function (v) { st.hSet = v; }, 'mm');
          u.row(u.button('Set the jack to this height', function () { setHeight(); }, true, S.hand.busy || st.running), u.button('Release the trolley', function () { release(); }, false, S.hand.busy || st.running),
            u.button('Write t in the table', record, false, !st.done));
          u.live(function () { return 'h = ' + st.h.toFixed(1) + ' mm · θ = ' + (p.angle * 180 / PI).toFixed(2) + '° · wheels ' + (p.lock > 0.5 ? 'locked' : 'free') + ' · timer ' + (st.running ? st.t : st.tg).toFixed(3) + ' s'; });
          u.h3('Observation table'); u.table(); var n = rowsOf(S.rows, LOCK0).length; if (n < 5) u.p(n + ' of at least 5 heights timed with the wheels ' + (LOCK0 ? 'locked' : 'free') + '.');
          u.next('Next: work out μ', n >= 5); },
        ok: function () { return rowsOf(S.rows, LOCK0).length >= 5; },
        auto: function () { return RANGE[LOCK0].auto.reduce(function (pr, h) { return pr.then(function () { return p.lock === LOCK0 ? null : setLock(LOCK0); }).then(function () { st.hSet = h; return setHeight(); })
          .then(function () { return release(); }).then(function () { S.advance(20, finished); record(); }); }, Promise.resolve()); } },
    ],
    tick: function (dt) {
      if (st.running) { st.prevS = sim.s; st.prevT = sim.t; K.step(sim, p, dt);
        if (sim.s >= p.d) { st.tg = st.prevT + (p.d - st.prevS) / (sim.s - st.prevS) * (sim.t - st.prevT); st.running = false; st.done = true; sim.s = Math.min(sim.s, XS - 0.12); sim.v = 0; S.click(800); }
        st.t = sim.t; }
      pose(); drawTimer();
      hud1.set(st.h.toFixed(1) + ' mm'); hud2.set((st.running ? st.t : st.tg).toFixed(3) + ' s'); hud3.set(p.lock > 0.5 ? 'locked' : 'free'); },
  };
});
