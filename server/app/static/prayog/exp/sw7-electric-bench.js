/* Prayogshala studio module: the school electric bench (wave 7). One rig, five set-ups - the lab id picks the apparatus:
     sw7-electroplating-copper   copper plates in copper sulphate solution, a supply, a rheostat, an ammeter and a balance
     sw7-liquid-conductivity     an LED tester with a milliammeter and five liquids
     sw7-force-on-conductor      an aluminium rod hanging between the poles of a horseshoe magnet
     sw7-multimeter              a digital multimeter, a resistor, a battery, a transformer and a wire
     sw7-diode-led-multimeter    a diode and an LED on the diode test of a multimeter
   Physics: the school_w7 kernel pack - the same numbers the server checks. The shared workflow at the end of the
   file gives every set-up its steps: and each step its auto: action, and the result: of the experiment. */
HoolaStudio.define('sw7-electric-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var K = HK.K[S.lab.kernel], p = HK.paramsFor(S.lab.kernel, S.lab.params || {});
  var BZ = -0.34, LABS = {};
  function Q(over) { return HK.assign(p, over || {}); }
  function ix(v, n) { var i = Math.floor(v + 0.5); return i < 0 ? 0 : (i > n - 1 ? n - 1 : i); }
  function fx(v, d) { return Number(v).toFixed(d); }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : NaN; }
  function rowAt(rows, ci) { for (var i = rows.length - 1; i >= 0; i--) if (rows[i].ci === ci) return rows[i]; return null; }
  function mat(c, r, m, extra) { var o = { color: c, roughness: r === undefined ? 0.6 : r, metalness: m || 0 }; if (extra) Object.keys(extra).forEach(function (k) { o[k] = extra[k]; }); return new T.MeshStandardMaterial(o); }
  function add(par, o, x, y, z) { o.position.set(x || 0, y || 0, z || 0); par.add(o); return o; }
  function box(par, w, h, d, m, x, y, z) { return add(par, S.mesh(new T.BoxGeometry(w, h, d), m), x, y, z); }
  function cyl(par, r1, r2, h, m, x, y, z, seg) { return add(par, S.mesh(new T.CylinderGeometry(r1, r2, h, seg || 28), m), x, y, z); }
  function sph(par, r, m, x, y, z) { return add(par, S.mesh(new T.SphereGeometry(r, 28, 20), m), x, y, z); }
  function grp(x, y, z, par) { var g = new T.Group(); g.position.set(x || 0, y || 0, z || 0); (par || S.scene).add(g); return g; }
  function txt(par, text, w, x, y, z, opts) { opts = opts || {}; opts.w = w; return add(par, S.label(text, opts), x, y, z); }
  function ease(k) { return k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; }
  function clamp01(k) { return k < 0 ? 0 : (k > 1 ? 1 : k); }
  // a bench instrument with a liquid-crystal display: { group, set(text) }
  function lcd(x, z, title, w, rotY) {
    w = w || 0.16; var g = grp(x, 0, z), tex = S.liveTex(512, 160), last = null;
    var body = S.rounded(w, 0.08, 0.05, 0.008, M.bakelite); body.rotation.x = -0.9; body.position.y = 0.047; g.add(body);
    var scr = new T.Mesh(new T.PlaneGeometry(w * 0.84, w * 0.84 * 160 / 512), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
    scr.position.set(0, 0.008, 0.0258); body.add(scr);
    var lb = S.label(title, { w: w * 0.84, ratio: 0.12, color: '#d8dade' }); lb.position.set(0, -0.028, 0.0258); body.add(lb);
    if (rotY) g.rotation.y = rotY;
    S.contact(w + 0.05, 0.12, x, z, 0.5);
    function set(s) { if (s === last) return; last = s; tex.draw(function (c, W, H) {
      c.fillStyle = '#b3c0a0'; c.fillRect(0, 0, W, H); c.fillStyle = '#18200f'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.font = '700 ' + (s.length > 9 ? 70 : 96) + 'px "JetBrains Mono", monospace'; c.fillText(s, W / 2, H / 2 + 4); }); }
    set('---');
    return { group: g, set: set };
  }
  // a printed tape (centimetres) in the XY plane, its zero at local x = 0; lay it flat or stand it up yourself
  function tape(len, par, opts) {
    opts = opts || {}; var cm = Math.round(len * 100), W = 4096, H = 128;
    var tex = S.canvasTex(W, H, function (c, w, h) { c.fillStyle = opts.bg || '#f6e8b8'; c.fillRect(0, 0, w, h); c.fillStyle = '#17171a';
      var k = w / cm, st = cm > 60 ? 10 : (cm > 20 ? 5 : 1), i, xx, big;
      for (i = 0; i <= cm; i++) { xx = i * k; big = i % 10 === 0; c.fillRect(xx - (big ? 2 : 1), 0, big ? 4 : 2, big ? 52 : (i % 5 === 0 ? 38 : 22));
        if (i % st === 0 && i > 0 && i < cm) { c.font = '600 ' + (cm > 60 ? 44 : 60) + 'px "Public Sans", sans-serif'; c.textAlign = 'center'; c.fillText(String(i), xx, 108); } } });
    var m = new T.Mesh(new T.PlaneGeometry(len, opts.w || 0.03), new T.MeshStandardMaterial({ map: tex, roughness: 0.7, side: T.DoubleSide }));
    m.geometry.translate(len / 2, 0, 0); par.add(m); return m;
  }
  function flat(m, x, y, z) { m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); return m; }
  function upright(m, x, y, z) { m.rotation.z = Math.PI / 2; m.position.set(x, y, z); return m; }
  // a thin thread / string between points that move
  function thread(color) {
    var g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(36), 3));
    var l = new T.Line(g, new T.LineBasicMaterial({ color: color === undefined ? 0x2a2a2a : color })); l.frustumCulled = false; S.scene.add(l);
    l.set = function (pts) { var a = g.attributes.position.array, i, q; for (i = 0; i < 12; i++) { q = pts[Math.min(i, pts.length - 1)]; a[i * 3] = q[0]; a[i * 3 + 1] = q[1]; a[i * 3 + 2] = q[2]; }
      g.attributes.position.needsUpdate = true; };
    return l;
  }
  // a wooden plank of length L hinged at (x, y) and tilted by `deg` (positive = rising to the right)
  function plank(L, x, y, z, deg, m, wdt) {
    var g = grp(x, y, z); box(g, L, 0.012, wdt || 0.09, m || M.wood, L / 2, -0.006, 0); g.rotation.z = deg * Math.PI / 180; return g;
  }
  function onPlank(g, s, up) { var a = g.rotation.z; return [g.position.x + s * Math.cos(a) - (up || 0) * Math.sin(a), g.position.y + s * Math.sin(a) + (up || 0) * Math.cos(a), g.position.z]; }
  function liquidM(c, o) { return new T.MeshPhysicalMaterial({ color: c, transmission: 0.4, roughness: 0.1, thickness: 0.02, transparent: true, opacity: o || 0.8 }); }
  // a hand-held digital multimeter lying tilted on the bench: { group, set(text), dial(i) }
  function dmm(x, z) {
    var g = grp(x, 0, z), tex = S.liveTex(512, 200), last = null;
    var body = S.rounded(0.085, 0.16, 0.035, 0.012, mat(0xe2a21a, 0.6)); body.rotation.x = -1.15; body.position.y = 0.05; g.add(body);
    var face = S.rounded(0.072, 0.146, 0.004, 0.008, mat(0x1a1b1e, 0.6)); face.position.z = 0.0176; body.add(face);
    var scr = new T.Mesh(new T.PlaneGeometry(0.06, 0.06 * 200 / 512), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.set(0, 0.048, 0.0202); body.add(scr);
    var knob = cyl(body, 0.017, 0.017, 0.008, mat(0x2c2e33, 0.5), 0, -0.006, 0.0235, 28); knob.rotation.x = Math.PI / 2; var tick = box(knob, 0.003, 0.0085, 0.014, M.white, 0, 0, -0.008);
    ['Ω', 'V⎓', 'V~', 'mA', '•)))', '▶|'].forEach(function (s, i) { var a = (-150 + i * 60) * Math.PI / 180, l = S.label(s, { w: 0.014, ratio: 0.6, color: '#f0f0f0' }); l.position.set(Math.sin(a) * 0.027, -0.006 + Math.cos(a) * 0.027, 0.0202); body.add(l); });
    [[-0.018, 0xb3261e], [0.018, 0x111214]].forEach(function (j) { var s = cyl(body, 0.004, 0.004, 0.004, mat(j[1]), j[0], -0.058, 0.021, 14); s.rotation.x = Math.PI / 2; });
    S.contact(0.14, 0.2, x, z, 0.5);
    function set(s) { if (s === last) return; last = s; tex.draw(function (c, W, H) { c.fillStyle = '#b3c0a0'; c.fillRect(0, 0, W, H); c.fillStyle = '#18200f'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.font = '700 ' + (s.length > 8 ? 84 : 110) + 'px "JetBrains Mono", monospace'; c.fillText(s, W / 2, H / 2 + 6); }); }
    set('0.00');
    return { group: g, set: set, dial: function (i) { knob.rotation.y = -(-150 + i * 60) * Math.PI / 180; } };
  }
  function probes() { var a = grp(0, 0, 0), b = grp(0, 0, 0); cyl(a, 0.004, 0.0015, 0.09, mat(0xb3261e, 0.5), 0, 0.05, 0, 12); cyl(a, 0.0008, 0.0008, 0.012, M.steel, 0, 0.002, 0, 6);
    cyl(b, 0.004, 0.0015, 0.09, mat(0x111214, 0.5), 0, 0.05, 0, 12); cyl(b, 0.0008, 0.0008, 0.012, M.steel, 0, 0.002, 0, 6); a.rotation.z = 0.35; b.rotation.z = -0.35; return [a, b]; }

  // ------------------------------------------------------------------------------------------ copper plating
  LABS['sw7-electroplating-copper'] = (function () {
    var la, lb, sw, rh, sol, cath;
    return {
      intro: 'Two copper plates dip into copper sulphate solution. A DC supply, a rheostat and an ammeter are joined in series with them. The plate on the negative side (the cathode) is weighed on a milligram balance before and after.',
      build: function () {
        var bk = S.beaker(0.06, 0.13, [0, 0, BZ], 0x2f7fd0, 0.7);
        var an = box(S.scene, 0.004, 0.14, 0.05, M.copper, -0.03, 0.09, BZ); cath = box(S.scene, 0.004, 0.14, 0.05, M.copper, 0.03, 0.09, BZ);
        box(S.scene, 0.12, 0.008, 0.02, M.wood, 0, 0.134, BZ);
        var ps = S.powerBox([-0.42, 0, BZ - 0.05], 'DC SUPPLY 6 V'); rh = S.rheostat([-0.38, 0, BZ + 0.16], 0.22);
        la = lcd(0.3, BZ + 0.16, 'AMMETER  A', 0.14); lb = lcd(0.52, BZ + 0.16, 'CATHODE GAINED  mg', 0.16); sw = S.stopwatch([0.3, 0.035, BZ - 0.06], [-1.2, -0.3, 0]);
        S.wire([[-0.38, 0.105, BZ - 0.05], [-0.2, 0.2, BZ], [-0.03, 0.165, BZ]], 'red'); S.wire([[0.03, 0.165, BZ], [0.2, 0.15, BZ + 0.08], [0.3, 0.07, BZ + 0.13]], 'black');
        S.wire([[0.26, 0.06, BZ + 0.13], [-0.1, 0.04, BZ + 0.22], [-0.27, 0.06, BZ + 0.16]], 'black'); S.wire([[-0.49, 0.06, BZ + 0.16], [-0.56, 0.08, BZ + 0.05], [-0.46, 0.105, BZ - 0.05]], 'black');
        S.addApparatus('cell', bk, 'Plating cell', 'Copper sulphate solution with two copper plates. Copper leaves the anode and is laid down on the cathode.');
        S.addApparatus('cathode', cath, 'Cathode plate', 'Joined to the negative terminal: this is the plate that gains copper and is weighed.');
        S.addApparatus('supply', ps, 'DC supply', 'Drives the current through the solution.');
        S.addApparatus('rheostat', rh, 'Rheostat', 'Adjusted to keep the current steady at the chosen value.');
        S.addApparatus('ammeter', la.group, 'Ammeter', 'Shows the current through the cell.');
        S.addApparatus('balance', lb.group, 'Milligram balance', 'Shows how much mass the cathode has gained.');
        return { handAt: function () { return new T.Vector3(-0.38, 0.12, BZ + 0.16); },
          update: function (c, r, k, done) { var e = done ? 1 : k; rh.setFraction(c.set.I > 0.75 ? 0.25 : 0.6); la.set(fx(k > 0 ? c.set.I : 0, 2)); sw.t = c.set.tm * e; sw.on = false;
            lb.set(fx(K.view({ t: 0 }, Q({ I: c.set.I, tm: Math.max(1e-6, c.set.tm * e) })).dm * 1e6, 0)); } };
      },
      conds: [[0.5, 600], [0.5, 1200], [1.0, 1200]].map(function (s) { return { label: fx(s[0], 1) + ' A for ' + fx(s[1] / 60, 0) + ' min', set: { I: s[0], tm: s[1] } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { I: q.I, tm: q.tm, dm: v.dm, Q: v.Q, Z: v.dm / v.Q }; },
      runLabel: 'Close the circuit and plate', dur: 2.4, hudLabel: 'Copper deposited',
      runText: 'Weigh the clean dry cathode, pass the chosen current for the chosen time, then rinse, dry and weigh it again (the stopwatch runs fast here).',
      live: function (r, done) { return done ? fx(r.I, 1) + ' A for ' + fx(r.tm, 0) + ' s: the cathode gained ' + fx(r.dm * 1e6, 0) + ' mg.' : 'The key is open; the cathode has been weighed.'; },
      hud: function (r) { return fx(r.dm * 1e6, 0) + ' mg'; },
      cols: [['I (A)', function (r) { return fx(r.I, 1); }], ['t (s)', function (r) { return fx(r.tm, 0); }], ['charge I t (C)', function (r) { return fx(r.Q, 0); }], ['gain m (mg)', function (r) { return fx(r.dm * 1e6, 0); }], ['m / (I t) (mg/C)', function (r) { return fx(r.Z * 1e6, 4); }]],
      theory: { formula: 'm = Z I t', note: 'for copper Z = M / (2 F)' },
      graph: { x: function (r) { return r.Q; }, y: function (r) { return r.dm * 1e6; }, xlabel: 'charge passed (C)', ylabel: 'copper deposited (mg)', x0: 0, y0: 0 },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.Z; })); if (!isFinite(m)) return null;
        return { label: 'Mass of copper deposited per coulomb', value: m * 1e6, unit: 'mg/C', digits: 4, truth: p.M / (p.n * p.F) * 1e6, note: 'The mass deposited is proportional to the charge passed: Faraday\'s first law of electrolysis.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ which liquids conduct
  LABS['sw7-liquid-conductivity'] = (function () {
    var liq, led, la, names = ['Tap water', 'Distilled water', 'Lemon juice', 'Vinegar', 'Salt solution'], cols = [0xa9d3e8, 0xdcecf4, 0xe9e2a0, 0xe8d6b0, 0xc4dbe6], mats, ledOn = new T.MeshBasicMaterial({ color: 0xff3020 }), ledOff = mat(0x7a1f1f, 0.4);
    return {
      view: [[0.05, 0.5, 0.95], [0.02, 0.1, BZ]],
      intro: 'A tester made of four cells, a red LED with its resistor, a milliammeter and two metal plates held a fixed distance apart. Five beakers hold tap water, distilled water, lemon juice, vinegar and salt solution.',
      given: function () { return ['Tester: ' + fx(p.V, 0) + ' V of cells, LED drop ' + fx(p.Vf, 1) + ' V, series resistor ' + fx(p.Rs, 0) + ' Ω.', 'Plates: cell constant (gap ÷ area) ' + fx(p.cellk, 0) + ' per metre.']; },
      build: function () {
        mats = cols.map(function (c) { return liquidM(c, 0.75); });
        var bk = grp(0.05, 0, BZ); add(bk, new T.Mesh(new T.CylinderGeometry(0.05, 0.05, 0.1, 32, 1, true), M.glass), 0, 0.05, 0); cyl(bk, 0.05, 0.05, 0.003, M.glass, 0, 0.0015, 0, 32); liq = cyl(bk, 0.047, 0.047, 0.06, mats[0], 0, 0.033, 0, 28); S.contact(0.14, 0.14, 0.05, BZ, 0.45);
        var pr = grp(0.05, 0, BZ); box(pr, 0.003, 0.09, 0.02, M.steel, -0.012, 0.075, 0); box(pr, 0.003, 0.09, 0.02, M.steel, 0.012, 0.075, 0); box(pr, 0.05, 0.012, 0.03, mat(0x2c2e33, 0.6), 0, 0.126, 0);
        var tb = grp(-0.3, 0, BZ + 0.02); box(tb, 0.16, 0.012, 0.1, M.wood, 0, 0.006, 0); for (var i = 0; i < 4; i++) { var cl = cyl(tb, 0.0085, 0.0085, 0.032, mat(0x1f3b82, 0.4, 0.2), -0.05 + i * 0.033, 0.021, 0.02, 16); cl.rotation.z = Math.PI / 2; }
        led = sph(tb, 0.006, ledOff, 0.04, 0.03, -0.02); cyl(tb, 0.003, 0.003, 0.02, mat(0xd9b38c, 0.6), -0.02, 0.016, -0.02, 10).rotation.z = Math.PI / 2; S.contact(0.2, 0.14, -0.3, BZ + 0.02, 0.45);
        la = lcd(0.38, BZ + 0.14, 'MILLIAMMETER  mA', 0.15);
        S.wire([[-0.22, 0.03, BZ + 0.02], [-0.08, 0.14, BZ], [0.038, 0.132, BZ]], 'red'); S.wire([[0.062, 0.132, BZ], [0.2, 0.12, BZ + 0.08], [0.34, 0.07, BZ + 0.11]], 'black');
        for (var j = 0; j < 5; j++) { var sb = S.beaker(0.022, 0.05, [-0.2 + j * 0.07, 0, BZ - 0.2], cols[j], 0.6); }
        S.addApparatus('tester', tb, 'Tester', 'Cells, a red LED and its resistor in series with the two plates.');
        S.addApparatus('plates', pr, 'Plates', 'Two metal plates held a fixed distance apart; the liquid between them completes the circuit.');
        S.addApparatus('beaker', bk, 'Liquid under test', 'Changed for each trial; the plates are rinsed in between.');
        S.addApparatus('meter', la.group, 'Milliammeter', 'Shows the current through the liquid.');
        return { handAt: function () { return new T.Vector3(0.05, 0.2, BZ); },
          update: function (c, r, k, done) { liq.material = mats[c.set.liq]; var on = k > 0.1; led.material = on && r.glow ? ledOn : ledOff; la.set(on ? fx(r.I * 1000, 3) : '0.000'); } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { liq: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q), R = (q.V - q.Vf) / v.I - q.Rs; return { I: v.I, R: R, s: q.cellk / R, glow: v.glow > 0.5 }; },
      runLabel: 'Dip the plates in', dur: 1.2, hudLabel: 'Current',
      runText: 'Dip the plates into the liquid, see whether the LED glows and read the milliammeter. Rinse the plates before the next liquid.',
      live: function (r, done) { return done ? 'Current ' + fx(r.I * 1000, 3) + ' mA: the LED ' + (r.glow ? 'glows.' : 'does not glow.') : 'The plates are out of the liquid; no current flows.'; },
      hud: function (r) { return fx(r.I * 1000, 3) + ' mA'; },
      cols: [['Liquid', function (r) { return r.label; }], ['LED', function (r) { return r.glow ? 'glows' : 'dark'; }], ['I (mA)', function (r) { return fx(r.I * 1000, 3); }], ['R of liquid (Ω)', function (r) { return r.R >= 1e4 ? r.R.toExponential(1) : fx(r.R, 0); }], ['conductivity (S/m)', function (r) { return r.s < 0.01 ? r.s.toExponential(1) : fx(r.s, 2); }]],
      theory: { formula: 'I = (V − V_LED) / (Rₛ + R);   conductivity = cell constant / R' },
      result: function (rows) { var i = ix(p.liq, 5), r = rowAt(rows, i), d = rowAt(rows, 1); if (!r) return null;
        return { label: 'Conductivity of ' + names[i].toLowerCase(), value: r.s, unit: 'S/m', digits: 3, truth: p['s' + i], note: d ? 'Distilled water passed only ' + fx(d.I * 1e6, 1) + ' µA and the LED stayed dark: with almost no ions it hardly conducts.' : 'Try distilled water too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ force on a conductor
  LABS['sw7-force-on-conductor'] = (function () {
    var rod, w1, w2, nB, sB, lc, la, PY = 0.34, LW = 0.2, PX = 0.0, RL = 0.12, arrow;
    var set = [['Current forward, N pole on top', { sI: 1, sB: 1 }], ['Current reversed', { sI: -1, sB: 1 }], ['Magnet reversed', { sI: 1, sB: -1 }], ['Both reversed', { sI: -1, sB: -1 }], ['Half the current', { I: p.I / 2 }]];
    return {
      view: [[0.05, 0.5, 0.95], [0.0, 0.17, BZ]],
      intro: 'A light aluminium rod hangs level from two thin flexible wires, between the poles of a strong horseshoe magnet. A supply and a key send a current along the rod, and a protractor reads the angle it swings to.',
      given: function () { return ['Mass of the rod: ' + fx(p.m * 1000, 1) + ' g. Length of the rod inside the field: ' + fx(p.Lr * 100, 1) + ' cm.', 'g = ' + fx(p.g, 1) + ' m/s².']; },
      build: function () {
        var fr = grp(PX, 0, BZ); box(fr, 0.02, PY, 0.02, M.wood, 0, PY / 2, -0.09); box(fr, 0.02, PY, 0.02, M.wood, 0, PY / 2, 0.09); box(fr, 0.02, 0.02, 0.2, M.wood, 0, PY, 0); box(fr, 0.12, 0.012, 0.24, M.darkWood, 0, 0.006, 0); S.contact(0.2, 0.3, PX, BZ, 0.45);
        var mg = grp(PX, 0, BZ); nB = box(mg, 0.07, 0.03, 0.05, mat(0xb3261e, 0.5), 0, PY - LW + 0.055, 0); sB = box(mg, 0.07, 0.03, 0.05, mat(0x1d4fa0, 0.5), 0, PY - LW - 0.055, 0); box(mg, 0.03, 0.14, 0.05, mat(0x555b63, 0.5, 0.5), -0.05, PY - LW, 0);
        rod = cyl(S.scene, 0.003, 0.003, RL, M.alu, 0, 0, 0, 14); rod.rotation.x = Math.PI / 2; w1 = thread(0xb87333); w2 = thread(0xb87333);
        arrow = box(S.scene, 0.03, 0.004, 0.004, mat(0x18a058), 0, 0, 0);
        var ps = S.powerBox([-0.42, 0, BZ], 'DC SUPPLY'); la = lcd(0.36, BZ + 0.14, 'AMMETER  A', 0.14); lc = lcd(0.36, BZ - 0.06, 'SWING  degrees', 0.14);
        S.wire([[-0.38, 0.105, BZ], [-0.2, 0.3, BZ - 0.09], [PX, PY + 0.01, BZ - 0.06]], 'red'); S.wire([[PX, PY + 0.01, BZ + 0.06], [-0.2, 0.3, BZ + 0.09], [-0.46, 0.105, BZ]], 'black');
        S.addApparatus('rod', rod, 'Aluminium rod', 'Carries the current across the field. Aluminium is not attracted by the magnet.');
        S.addApparatus('magnet', mg, 'Horseshoe magnet', 'Red is the north pole, blue the south: the field between them is vertical.');
        S.addApparatus('frame', fr, 'Wooden frame', 'Holds the two thin wires that carry the current to the rod.');
        S.addApparatus('supply', ps, 'DC supply', 'Sends a steady current through the rod.');
        return { handAt: function () { return new T.Vector3(-0.42, 0.16, BZ); },
          update: function (c, r, k, done) { var a = r.ang * Math.PI / 180 * ease(k) * (done ? 1 : (1 + 0.25 * Math.sin(k * 18) * (1 - k))), x = PX + LW * Math.sin(a), y = PY - LW * Math.cos(a);
            rod.position.set(x, y, BZ); w1.set([[PX, PY, BZ - 0.05], [x, y, BZ - 0.05]]); w2.set([[PX, PY, BZ + 0.05], [x, y, BZ + 0.05]]);
            var up = (c.set.sB === undefined ? 1 : c.set.sB) > 0; nB.position.y = PY - LW + (up ? 0.055 : -0.055); sB.position.y = PY - LW + (up ? -0.055 : 0.055);
            arrow.visible = k > 0.5; arrow.position.set(x + (r.ang > 0 ? 0.03 : -0.03), y, BZ + 0.07); la.set(fx(k > 0 ? r.I : 0, 2)); lc.set(fx(r.ang * ease(k), 1)); } };
      },
      conds: set.map(function (s) { return { label: s[0], set: s[1] }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { I: q.I, ang: v.ang, B: q.m * q.g * Math.tan(Math.abs(v.ang) * Math.PI / 180) / (q.I * q.Lr) }; },
      runLabel: 'Close the key', dur: 2.0, hudLabel: 'Swing',
      runText: 'Close the key and read the angle the rod settles at, and which way it went. Reverse the current, then the magnet, then both, and finally halve the current.',
      live: function (r, done) { return done ? 'With ' + fx(r.I, 1) + ' A the rod swings ' + fx(Math.abs(r.ang), 1) + '° to the ' + (r.ang > 0 ? 'right.' : 'left.') : 'No current: the rod hangs straight down.'; },
      hud: function (r) { return fx(r.ang, 1) + '°'; },
      cols: [['Arrangement', function (r) { return r.label; }], ['I (A)', function (r) { return fx(r.I, 1); }], ['swing (°)', function (r) { return fx(Math.abs(r.ang), 1); }], ['to the', function (r) { return r.ang > 0 ? 'right' : 'left'; }], ['B (T)', function (r) { return fx(r.B, 3); }]],
      theory: { formula: 'F = B I L;   tan θ = B I L / (m g)' },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.B; })); if (!isFinite(m)) return null;
        return { label: 'Magnetic field between the poles', value: m, unit: 'T', digits: 3, truth: p.B, note: 'Reversing the current or the magnet reversed the swing; reversing both brought it back. The force follows Fleming\'s left-hand rule.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ multimeter
  LABS['sw7-multimeter'] = (function () {
    var mm, pr, items = [], names = ['Resistance of the resistor', 'DC voltage of the battery', 'AC voltage of the transformer', 'Current in the circuit', 'Continuity of the wire'], XS = [-0.36, -0.2, -0.02, 0.16, 0.32];
    function shown(r) { var m = r.mode; return m === 0 ? fx(r.reading / 1000, 2) + ' kΩ' : m === 1 ? fx(r.reading, 2) + ' V' : m === 2 ? fx(r.reading, 1) + ' V~' : m === 3 ? fx(r.reading * 1000, 2) + ' mA' : fx(r.reading, 1) + ' Ω'; }
    return {
      view: [[0.0, 0.5, 0.95], [0.0, 0.05, BZ + 0.04]],
      intro: 'A digital multimeter with its red and black probes, and on a board: a carbon resistor, a 9 V battery, a small mains transformer with a low-voltage output, the battery and resistor joined as a circuit, and a length of wire.',
      build: function () {
        var bd = box(S.scene, 0.9, 0.012, 0.16, M.wood, 0, 0.006, BZ - 0.04); S.contact(1.0, 0.22, 0, BZ - 0.04, 0.4);
        var rz = grp(XS[0], 0.03, BZ - 0.04); var rb = cyl(rz, 0.006, 0.006, 0.03, mat(0xd9b38c, 0.6), 0, 0, 0, 14); rb.rotation.z = Math.PI / 2; [0xd9a520, 0x7a3fb0, 0xb3261e, 0xc9a227].forEach(function (c, i) { var b = cyl(rz, 0.0063, 0.0063, 0.003, mat(c), -0.009 + i * 0.006, 0, 0, 14); b.rotation.z = Math.PI / 2; }); cyl(rz, 0.0008, 0.0008, 0.08, M.steel, 0, 0, 0, 6).rotation.z = Math.PI / 2;
        var bt = grp(XS[1], 0.012, BZ - 0.04); box(bt, 0.026, 0.048, 0.017, mat(0x1f3b82, 0.4, 0.3), 0, 0.024, 0); cyl(bt, 0.003, 0.003, 0.004, M.steel, -0.006, 0.05, 0, 10); cyl(bt, 0.004, 0.004, 0.004, M.steel, 0.006, 0.05, 0, 6); txt(bt, '9 V', 0.022, 0, 0.024, 0.009, { color: '#f4f4f4', ratio: 0.4 });
        var tr = grp(XS[2], 0.012, BZ - 0.04); box(tr, 0.06, 0.05, 0.05, mat(0x30343a, 0.6), 0, 0.025, 0); box(tr, 0.066, 0.02, 0.03, M.copper, 0, 0.025, 0); txt(tr, '12 V AC', 0.05, 0, 0.042, 0.0255, { color: '#f4f4f4', ratio: 0.25 });
        var ck = grp(XS[3], 0.012, BZ - 0.04); box(ck, 0.026, 0.048, 0.017, mat(0x1f3b82, 0.4, 0.3), -0.025, 0.024, 0); var r2 = cyl(ck, 0.006, 0.006, 0.03, mat(0xd9b38c, 0.6), 0.03, 0.02, 0, 14); r2.rotation.z = Math.PI / 2;
        var wr = grp(XS[4], 0.014, BZ - 0.04); var wt = S.mesh(new T.TorusGeometry(0.025, 0.0015, 8, 30, Math.PI * 1.6), mat(0xb8322a, 0.5)); wt.rotation.x = Math.PI / 2; wr.add(wt);
        items = [rz, bt, tr, ck, wr]; mm = dmm(0.0, BZ + 0.22); pr = probes(); S.scene.add(pr[0]); S.scene.add(pr[1]);
        S.addApparatus('dmm', mm.group, 'Digital multimeter', 'The dial chooses what is measured: ohms, DC volts, AC volts, milliamperes or continuity.');
        S.addApparatus('resistor', rz, 'Carbon resistor', 'Its resistance is the unknown here.');
        S.addApparatus('battery', bt, 'Battery', 'A 9 V battery: a DC source.');
        S.addApparatus('transformer', tr, 'Transformer', 'Its low-voltage output is AC; the mains side is sealed.');
        S.addApparatus('circuit', ck, 'Battery and resistor in series', 'The meter is put in series here to read the current.');
        S.addApparatus('wire', wr, 'Wire', 'Tested for continuity: an unbroken wire makes the meter beep.');
        return { handAt: function (c) { return new T.Vector3(XS[c.set.mode], 0.14, BZ - 0.04); },
          update: function (c, r, k, done) { var m = c.set.mode, on = k > 0.25, y = on ? 0.03 : 0.07; mm.dial(m);
            pr[0].position.set(XS[m] - 0.045, y, BZ - 0.02); pr[1].position.set(XS[m] + 0.045, y, BZ - 0.02); mm.set(on ? shown(r) : (m === 0 || m === 4 ? 'OL' : '0.00')); } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { mode: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { mode: ix(q.mode, 5), reading: v.reading, beep: v.beep > 0.5 }; },
      runLabel: 'Set the dial and touch the probes', dur: 1.4, hudLabel: 'Display',
      runText: 'Turn the dial to the right setting first, then touch the probes: across the component for resistance and voltage, in series for current. Take all five measurements.',
      live: function (r, done) { return done ? 'The display reads ' + shown(r) + (r.mode === 4 ? (r.beep ? ' and the meter beeps: the wire is unbroken.' : ': no beep.') : '.') : 'The probes are lifted off.'; },
      hud: function (r) { return shown(r); },
      cols: [['Measurement', function (r) { return r.label; }], ['Dial', function (r) { return ['Ω', 'DC V', 'AC V', 'mA', 'continuity'][r.mode]; }], ['Display', function (r) { return shown(r); }]],
      theory: { formula: 'voltmeter across, ammeter in series;   I = V / R' },
      result: function (rows) { var r = rowAt(rows, 0), v = rowAt(rows, 1), i = rowAt(rows, 3); if (!r) return null;
        return { label: 'Resistance of the resistor', value: r.reading, unit: 'Ω', digits: 0, truth: p.R, note: (v && i) ? 'Check with Ohm\'s law: ' + fx(v.reading, 2) + ' V ÷ ' + fx(i.reading * 1000, 2) + ' mA = ' + fx(v.reading / i.reading, 0) + ' Ω.' : 'Take the voltage and the current too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ diode and LED
  LABS['sw7-diode-led-multimeter'] = (function () {
    var mm, pr, dio, led, dome, glowM = new T.MeshBasicMaterial({ color: 0xff4030 }), dimM = mat(0xb02a2a, 0.3, 0, { transparent: true, opacity: 0.8 });
    var set = [['Diode, red probe on the anode', { dev: 0, dir: 1 }], ['Diode, probes reversed', { dev: 0, dir: -1 }], ['LED, red probe on the anode', { dev: 1, dir: 1 }], ['LED, probes reversed', { dev: 1, dir: -1 }]];
    function shown(r) { return r.ol ? 'OL' : fx(r.reading, 3) + ' V'; }
    return {
      view: [[0.02, 0.45, 0.85], [0.0, 0.06, BZ]],
      intro: 'A digital multimeter set to the diode test, a silicon rectifier diode (the band marks its cathode) and a red LED (the longer lead is its anode), held in clips on a small board.',
      given: function () { return ['On the diode test the meter passes about ' + fx(p.It * 1000, 0) + ' mA and shows the voltage across the component.']; },
      build: function () {
        var bd = box(S.scene, 0.4, 0.012, 0.12, M.wood, 0, 0.006, BZ - 0.04); S.contact(0.46, 0.18, 0, BZ - 0.04, 0.4);
        dio = grp(-0.1, 0.035, BZ - 0.04); var db = cyl(dio, 0.006, 0.006, 0.022, mat(0x16171a, 0.5), 0, 0, 0, 16); db.rotation.z = Math.PI / 2; var bd2 = cyl(dio, 0.0062, 0.0062, 0.004, mat(0xd7dbe0, 0.4), 0.007, 0, 0, 16); bd2.rotation.z = Math.PI / 2; cyl(dio, 0.0008, 0.0008, 0.09, M.steel, 0, 0, 0, 6).rotation.z = Math.PI / 2;
        led = grp(0.1, 0.02, BZ - 0.04); dome = cyl(led, 0.006, 0.006, 0.012, dimM, 0, 0.03, 0, 16); var cap = sph(led, 0.006, dimM, 0, 0.036, 0); cyl(led, 0.0007, 0.0007, 0.03, M.steel, -0.003, 0.012, 0, 6); cyl(led, 0.0007, 0.0007, 0.024, M.steel, 0.003, 0.014, 0, 6); led.userData.cap = cap;
        [-0.145, -0.055, 0.055, 0.145].forEach(function (x) { box(S.scene, 0.012, 0.03, 0.012, M.brass, x, 0.027, BZ - 0.04); });
        mm = dmm(0.0, BZ + 0.22); mm.dial(5); pr = probes(); S.scene.add(pr[0]); S.scene.add(pr[1]);
        S.addApparatus('dmm', mm.group, 'Digital multimeter', 'On the diode test it shows the forward voltage, or OL when no current can pass.');
        S.addApparatus('diode', dio, 'Silicon diode', 'A rectifier diode; the silver band marks the cathode.');
        S.addApparatus('led', led, 'Red LED', 'A light-emitting diode; the longer lead is the anode.');
        return { handAt: function (c) { return new T.Vector3(c.set.dev ? 0.1 : -0.1, 0.14, BZ - 0.04); },
          update: function (c, r, k, done) { var x = c.set.dev ? 0.1 : -0.1, on = k > 0.25, y = on ? 0.045 : 0.085, f = c.set.dir > 0 ? 1 : -1;
            pr[0].position.set(x - 0.045 * f, y, BZ - 0.035); pr[1].position.set(x + 0.045 * f, y, BZ - 0.035); pr[0].rotation.z = 0.35 * f; pr[1].rotation.z = -0.35 * f;
            var lit = on && c.set.dev === 1 && c.set.dir > 0; dome.material = lit ? glowM : dimM; led.userData.cap.material = lit ? glowM : dimM; mm.set(on ? shown(r) : 'OL'); } };
      },
      conds: set.map(function (s) { return { label: s[0], set: s[1] }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { dev: ix(q.dev, 2), dir: q.dir, reading: v.reading, ol: v.ol > 0.5 }; },
      runLabel: 'Touch the probes to the leads', dur: 1.4, hudLabel: 'Display',
      runText: 'Touch the probes to the two leads, read the display, then swap the probes and read again. Do this for the diode and for the LED.',
      live: function (r, done) { return done ? (r.ol ? 'The display shows OL: no current passes this way.' : 'The display shows ' + fx(r.reading, 3) + ' V: current passes' + (r.dev ? ' and the LED glows faintly.' : '.')) : 'The probes are lifted off.'; },
      hud: function (r) { return shown(r); },
      cols: [['Connection', function (r) { return r.label; }], ['Display', function (r) { return shown(r); }], ['Current', function (r) { return r.ol ? 'does not pass' : 'passes'; }]],
      theory: { formula: 'forward bias: conducts, V ≈ forward voltage;   reverse bias: OL' },
      result: function (rows) { var r = rowAt(rows, 0), l = rowAt(rows, 2); if (!r) return null;
        return { label: 'Forward voltage of the diode', value: r.reading, unit: 'V', digits: 3, truth: p.n0 * p.Vt * Math.log(p.It / p.Is0 + 1), note: (l ? 'The LED showed ' + fx(l.reading, 3) + ' V. ' : '') + 'Both gave OL with the probes reversed: a junction conducts one way only.' }; },
    };
  })();
  // ================================================================================================ the shared workflow
  var DEF = LABS[BASE];
  if (!DEF) throw new Error('this rig has no set-up for ' + BASE);
  var conds = DEF.conds, st = { ci: 0, k: 0, running: false, done: false, checked: false };
  var sc = DEF.build();
  function cur() { return conds[st.ci]; }
  var rcache = {};
  function reading() { if (!rcache[st.ci]) rcache[st.ci] = DEF.read(Q(cur().set), cur()); return rcache[st.ci]; }
  function durOf() { return typeof DEF.dur === 'function' ? DEF.dur(cur(), reading()) : (DEF.dur || 1.6); }
  function has(i) { return !!rowAt(S.rows, i); }
  function allDone() { for (var i = 0; i < conds.length; i++) if (!has(i)) return false; return true; }
  function draw() { try { sc.update(cur(), reading(), st.k, st.done); } catch (e) { if (!draw.bad) { draw.bad = true; console.error('sw7 draw: ' + e.message); } } }
  function checkApparatus() {
    if (S.hand.busy) return Promise.resolve();
    if (DEF.setupOk && !DEF.setupOk()) { S.say(DEF.setupNeed || 'Finish setting up first.'); return Promise.resolve(); }
    var at = sc.handAt ? sc.handAt(cur()) : new T.Vector3(0, 0.1, BZ);
    return S.hand.reach(at, 'top', 600).then(function () { return S.hand.away(400); })
      .then(function () { st.checked = true; S.say(DEF.checked || 'The apparatus is ready.'); S.render(); });
  }
  function select(i) {
    if (st.running || S.hand.busy) { S.say('Wait until this run is finished.'); return; }
    st.ci = i; st.k = 0; st.done = false; draw(); S.say('Set: ' + cur().label + '.'); S.render();
  }
  function run() {
    if (S.hand.busy || st.running) return Promise.resolve();
    if (!st.checked) { S.say('Check the apparatus first.'); return Promise.resolve(); }
    st.k = 0; st.done = false; draw();
    var at = sc.handAt ? sc.handAt(cur()) : new T.Vector3(0, 0.1, BZ);
    return S.hand.reach(at, 'top', 520).then(function () { return S.hand.away(320); })
      .then(function () { st.running = true; S.click(600, 0.04, 0.04); S.render(); });
  }
  function record() {
    if (st.running) { S.say('Wait until this run is finished.'); return; }
    if (!st.done) { S.say('Nothing to record yet: ' + DEF.runLabel.toLowerCase() + ' first.'); return; }
    if (has(st.ci)) { S.say('This reading is already in the table. Choose another setting.'); return; }
    var r = Object.assign({}, reading()); r.ci = st.ci; r.label = cur().label; S.addRow(r);
    S.say('Recorded: ' + DEF.live(r, true));
  }
  var hudR = S.hudCard(DEF.hudLabel || 'Reading'), hudN = S.hudCard('Readings');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var stepSetup = { id: 'setup', title: 'The set-up', view: 'app', render: function (u) {
      u.h2('Look over the apparatus');
      u.p(DEF.intro);
      (DEF.given ? DEF.given() : []).forEach(function (g) { u.note(g); });
      if (DEF.setupUi) DEF.setupUi(u);
      u.row(u.button(st.checked ? 'Apparatus checked' : 'Check the apparatus', function () { checkApparatus(); S.render(); }, !st.checked, st.checked || S.hand.busy));
      u.note(S.lab.safety || 'Work carefully.');
      u.next('Next: take the readings', st.checked);
    },
    ok: function () { return st.checked; },
    auto: function () { if (DEF.setupAuto) DEF.setupAuto(); return checkApparatus(); } };
  var stepRead = { id: 'readings', title: 'Readings', view: 'app', render: function (u) {
      u.h2(DEF.runTitle || 'Take the readings');
      u.p(DEF.runText);
      var r = u.row(); conds.forEach(function (c, i) {
        r.appendChild(u.button((has(i) ? '✓ ' : '') + c.label, function () { select(i); }, i === st.ci, st.running)); });
      u.row(u.button(DEF.runLabel, function () { run(); S.render(); }, true, st.running || S.hand.busy),
        u.button('Record this reading', function () { record(); }, false, st.running || !st.done));
      u.live(function () { return st.running ? 'Running…' : DEF.live(reading(), st.done); });
      u.h3('Observation table'); u.table();
      u.next('Next: the result', allDone());
      if (!allDone()) u.p('Take one reading for every setting above.');
    },
    ok: function () { return allDone(); },
    auto: function () {
      var chain = Promise.resolve();
      conds.forEach(function (c, i) { chain = chain.then(function () { select(i); return run(); })
        .then(function () { for (var n = 0; n < 60 && !st.done; n++) S.advance(1, function () { return st.done; }); record(); }); });
      return chain; } };
  var th = DEF.theory || {};
  draw();
  return {
    camera: DEF.camera || { pos: [0.1, 0.95, 2.0], look: [0.05, 0.12, BZ] },
    views: Object.assign({ app: DEF.view || [[0.1, 0.75, 1.65], [0.05, 0.1, BZ]], book: [[-0.4, 0.52, 0.56], [-0.5, 0.0, 0.08]] }, DEF.views || {}),
    theory: { principle: S.lab.theory || '', formula: th.formula || '', formulaNote: th.note || '', more: th.more || [],
      precautions: S.lab.safety || '' },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim].concat(th.formula ? [th.formula] : []).concat(DEF.given ? DEF.given() : []),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }].concat(DEF.cols.map(function (c) { return { label: c[0], get: c[1] }; })) },
    graph: DEF.graph,
    result: function (rows) { return DEF.result(rows); },
    tol: DEF.tol === undefined ? 0.02 : DEF.tol,
    chips: ['What am I measuring here?', 'Check my readings', 'Why does the result come out this way?'],
    viva: DEF.viva || [],
    askState: function () { return { experiment: S.lab.title, setting: cur().label, run_in_progress: st.running, run_finished: st.done,
      now: DEF.live(reading(), st.done), readings_taken: S.rows.length, settings_still_to_do: conds.filter(function (c, i) { return !has(i); }).map(function (c) { return c.label; }) }; },
    steps: [stepSetup, stepRead],
    tick: function (dt) {
      if (st.running) { st.k += dt / durOf(); if (st.k >= 1) { st.k = 1; st.running = false; st.done = true; S.say(DEF.live(reading(), true)); S.render(); } }
      draw();
      hudR.set(st.done ? DEF.hud(reading()) : (st.running ? '…' : '—')); hudN.set(S.rows.length + ' / ' + conds.length);
    },
  };
});
