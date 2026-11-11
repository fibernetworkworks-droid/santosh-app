/* Prayogshala studio module: the school heat and sound bench (wave 7). One rig, eight set-ups - the lab id picks the apparatus:
     sw7-sound-through-solids    a tap timed along a wooden metre scale, a string telephone and air
     sw7-reflection-of-sound     two tubes, a wall and a sound-level meter
     sw7-black-white-tins        a black tin and a white tin of water under a lamp that stands in for the sun
     sw7-specific-heat-liquid    a hot brass bob dropped into kerosene in a calorimeter
     sw7-wax-cooling-curve       molten wax cooling in a test tube
     sw7-bimetallic-strip        a brass and iron strip over a heater
     sw7-liquid-level-heating    a flask of glycerine with a narrow tube in a water bath
     sw7-rate-of-heat-loss       calorimeters of hot water cooling under different conditions
   Physics: the school_w7 kernel pack (and the shipped mixtures kernel) - the same numbers the server checks. The shared
   workflow at the end of the file gives every set-up its steps: and each step its auto: action, and the result: of the experiment. */
HoolaStudio.define('sw7-heat-sound-bench', function (S) {
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
  var waterM = new T.MeshStandardMaterial({ color: 0x4f9fd6, roughness: 0.1, transparent: true, opacity: 0.55 });
  function hotplate(x, z) { var g = grp(x, 0, z); box(g, 0.18, 0.04, 0.16, mat(0xd9dce0, 0.4, 0.3), 0, 0.02, 0); cyl(g, 0.06, 0.06, 0.006, mat(0x2a2c30, 0.6), 0, 0.043, 0, 32); cyl(g, 0.012, 0.012, 0.01, M.black, 0.06, 0.02, 0.081, 16).rotation.x = Math.PI / 2; S.contact(0.24, 0.22, x, z, 0.45); return g; }
  function can(par, r, h, m, x, y, z) { var g = grp(x, y, z, par); add(g, new T.Mesh(new T.CylinderGeometry(r, r, h, 32, 1, true), m), 0, h / 2, 0); cyl(g, r, r, 0.003, m, 0, 0.0015, 0, 32); return g; }
  function probe(par, x, y, z, len) { return cyl(par, 0.0025, 0.0025, len, M.chrome, x, y, z, 10); }

  // ------------------------------------------------------------------------------------------ sound in solids
  LABS['sw7-sound-through-solids'] = (function () {
    var micA, micB, pulse, lc, names = ['Wooden metre scale', 'String telephone', 'Air'], ys = [0.05, 0.16, 0.26], zs = [BZ, BZ - 0.14, BZ - 0.28];
    return {
      intro: 'Three paths for a sound: a wooden metre scale resting on foam, a string telephone (two paper cups joined by a tight nylon line) and open air. Two small microphones are fixed a measured distance apart on each path, and a timer shows the time between their signals.',
      build: function () {
        var sc = grp(0, 0, zs[0]); box(sc, 1.0, 0.006, 0.03, M.wood, 0, ys[0] - 0.005, 0); [-0.4, 0.4].forEach(function (x) { box(sc, 0.06, ys[0] - 0.008, 0.05, mat(0x5a6470, 0.95), x, (ys[0] - 0.008) / 2, 0); });
        add(sc, tape(1.0, sc, { w: 0.028 }), -0.5, ys[0] - 0.0018, 0).rotation.x = -Math.PI / 2; S.contact(1.1, 0.1, 0, zs[0], 0.4);
        var tel = grp(0, 0, zs[1]); [-1, 1].forEach(function (sg) { var c = cyl(tel, 0.03, 0.022, 0.06, mat(0xf2ede0, 0.9), sg * (p.d1 / 2 + 0.03), ys[1], 0, 20); c.rotation.z = sg * Math.PI / 2; cyl(tel, 0.006, 0.006, ys[1], M.chrome, sg * (p.d1 / 2 + 0.03), ys[1] / 2, -0.03, 10); });
        var ln = cyl(tel, 0.0008, 0.0008, p.d1, mat(0xf4f4f4, 0.5), 0, ys[1], 0, 6); ln.rotation.z = Math.PI / 2;
        micA = grp(0, 0, 0); micB = grp(0, 0, 0); [micA, micB].forEach(function (m) { cyl(m, 0.008, 0.008, 0.016, M.black, 0, 0.008, 0, 16); cyl(m, 0.0015, 0.0015, 0.05, mat(0x1d1d1f), 0, 0.04, 0, 6); });
        pulse = sph(S.scene, 0.008, new T.MeshBasicMaterial({ color: 0xffb020 }), 0, 0, 0);
        lc = lcd(0.3, BZ + 0.2, 'TIME BETWEEN SIGNALS  µs', 0.2);
        S.addApparatus('scale', sc, 'Wooden metre scale', 'A solid path for the sound: one metre of wood, resting on foam so that the bench does not carry the tap.');
        S.addApparatus('telephone', tel, 'String telephone', 'Two paper cups joined by a tight nylon line ' + fx(p.d1, 1) + ' m long.');
        S.addApparatus('timer', lc.group, 'Timer', 'Shows the time between the signals of the two microphones, in millionths of a second.');
        return { handAt: function (c) { var m = c.set.medium, d = p['d' + m]; return new T.Vector3(-d / 2 - 0.03, ys[m] + 0.04, zs[m]); },
          update: function (c, r, k, done) { var m = c.set.medium, d = p['d' + m];
            micA.position.set(-d / 2, ys[m], zs[m]); micB.position.set(d / 2, ys[m], zs[m]);
            pulse.visible = k > 0 && k < 1; pulse.position.set(-d / 2 + d * k, ys[m] + 0.012, zs[m]); lc.set(done ? fx(r.dt * 1e6, 0) : '0'); } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { medium: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { dist: v.dist, dt: v.dt, v: v.dist / v.dt }; },
      runLabel: 'Tap the end', dur: 1.0, hudLabel: 'Speed of sound',
      runText: 'Fix the microphones on a path, tap one end sharply and read the time between the two signals. The speed is the distance between the microphones divided by that time.',
      live: function (r, done) { return done ? fx(r.dist, 2) + ' m in ' + fx(r.dt * 1e6, 0) + ' µs: speed ' + fx(r.v, 0) + ' m/s.' : 'Microphones ' + fx(r.dist, 2) + ' m apart; the timer is at zero.'; },
      hud: function (r) { return fx(r.v, 0) + ' m/s'; },
      cols: [['Path', function (r) { return r.label; }], ['distance (m)', function (r) { return fx(r.dist, 2); }], ['time (µs)', function (r) { return fx(r.dt * 1e6, 0); }], ['speed (m/s)', function (r) { return fx(r.v, 0); }]],
      theory: { formula: 'v = distance / time;   in a solid rod v = √(Y / ρ)' },
      result: function (rows) { var i = ix(p.medium, 3), r = rowAt(rows, i), a = rowAt(rows, 2); if (!r) return null;
        return { label: 'Speed of sound in the ' + names[i].toLowerCase(), value: r.v, unit: 'm/s', digits: 0, truth: K.view({ t: 0 }, p).v, note: a ? 'In air it was only ' + fx(a.v, 0) + ' m/s: sound travels far faster through solids.' : 'Time the sound in air too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ reflection of sound
  LABS['sw7-reflection-of-sound'] = (function () {
    var t1, t2, lc, OZ = -0.6, OY = 0.035, LT = 0.36, sweep = 10;
    function tube(colr) { var g = grp(0, OY, OZ); var c = add(g, new T.Mesh(new T.CylinderGeometry(0.022, 0.022, LT, 28, 1, true), mat(colr, 0.8, 0, { side: T.DoubleSide })), 0, 0, 0.1 + LT / 2); c.rotation.x = Math.PI / 2; return g; }
    return {
      camera: { pos: [0.05, 1.15, 0.95], look: [0, 0.02, -0.38] }, view: [[0.05, 1.0, 0.7], [0, 0.02, -0.38]],
      intro: 'A hard vertical board is the reflector. One cardboard tube points at it from a ticking clock; a second tube, with a sound-level meter at its end, can be turned about the same point. A screen along the normal stops the sound going straight across. A protractor on the table reads both angles from the normal.',
      build: function () {
        var wall = box(S.scene, 0.9, 0.3, 0.012, M.wood, 0, 0.15, OZ - 0.008); S.contact(1.0, 0.1, 0, OZ, 0.4);
        var pro = new T.Mesh(new T.CircleGeometry(0.46, 48, Math.PI, Math.PI), new T.MeshStandardMaterial({ roughness: 0.9, map: S.canvasTex(1024, 1024, function (c, w, h) { c.fillStyle = '#f4efe0'; c.fillRect(0, 0, w, h); c.strokeStyle = '#333'; c.fillStyle = '#333'; c.font = '600 26px sans-serif'; c.textAlign = 'center';
          for (var a = 0; a <= 180; a += 5) { var t = a * Math.PI / 180, big = a % 10 === 0; c.lineWidth = big ? 3 : 1.5; c.beginPath(); c.moveTo(w / 2 + Math.cos(t) * 470, h / 2 + Math.sin(t) * 470); c.lineTo(w / 2 + Math.cos(t) * (big ? 510 : 495), h / 2 + Math.sin(t) * (big ? 510 : 495)); c.stroke();
            if (big) c.fillText(String(Math.abs(90 - a)), w / 2 + Math.cos(t) * 440, h / 2 + Math.sin(t) * 440 + 9); } }) }));
        pro.rotation.x = -Math.PI / 2; pro.position.set(0, 0.002, OZ); S.scene.add(pro);
        var scr = box(S.scene, 0.006, 0.12, 0.3, mat(0x7a8794, 0.9), 0, 0.06, OZ + 0.22);
        t1 = tube(0xb58a57); t2 = tube(0xb58a57);
        var clock = cyl(t1, 0.03, 0.03, 0.015, M.white, 0, 0, 0.1 + LT + 0.03, 24); clock.rotation.x = Math.PI / 2; add(t1, S.mesh(new T.TorusGeometry(0.03, 0.004, 8, 24), M.black), 0, 0, 0.1 + LT + 0.03);
        box(t2, 0.03, 0.02, 0.05, M.black, 0, 0, 0.1 + LT + 0.03);
        lc = lcd(0.55, -0.12, 'SOUND LEVEL  %', 0.15);
        S.addApparatus('wall', wall, 'Reflecting board', 'A hard, smooth board: it reflects sound as a mirror reflects light.');
        S.addApparatus('tube1', t1, 'First tube and clock', 'Guides the ticking of the clock to the board at the angle of incidence.');
        S.addApparatus('tube2', t2, 'Listening tube', 'Turned about the same point until the sound is loudest.');
        S.addApparatus('screen', scr, 'Screen', 'Stops sound reaching the listening tube directly.');
        S.addApparatus('meter', lc.group, 'Sound-level meter', 'Shows how loud the sound in the listening tube is, as a percentage of the loudest.');
        return { handAt: function () { return new T.Vector3(0.3, 0.1, OZ + 0.4); },
          update: function (c, r, k, done) { var i = c.set.i_deg, a = done ? r.r : (k < 0.85 ? 10 + 70 * (k / 0.85) : r.r);
            t1.rotation.y = -i * Math.PI / 180; t2.rotation.y = a * Math.PI / 180; sweep = a;
            lc.set(k > 0 ? fx(100 * K.view({ t: 0 }, Q({ i_deg: i, r_deg: a })).loud, 0) : '0'); } };
      },
      conds: [30, 40, 50].map(function (a) { return { label: 'Angle of incidence ' + a + '°', set: { i_deg: a } }; }),
      read: function (q) { return { i: q.i_deg, r: K.measure(q).r_peak }; },
      runLabel: 'Turn the listening tube slowly', dur: 3.0, hudLabel: 'Loudest at',
      runText: 'Set the first tube, then turn the listening tube slowly from 10° to 80° while watching the meter. Bring it back to where the sound was loudest and read that angle.',
      live: function (r, done) { return done ? 'Incidence ' + fx(r.i, 0) + '°: the sound is loudest with the listening tube at ' + fx(r.r, 0) + '°.' : 'The listening tube is at 10°; hardly any sound reaches it.'; },
      hud: function (r) { return fx(r.r, 0) + '°'; },
      cols: [['angle of incidence (°)', function (r) { return fx(r.i, 0); }], ['angle of reflection (°)', function (r) { return fx(r.r, 0); }], ['difference (°)', function (r) { return fx(r.r - r.i, 0); }]],
      theory: { formula: 'angle of reflection = angle of incidence' },
      graph: { x: function (r) { return r.i; }, y: function (r) { return r.r; }, xlabel: 'angle of incidence (°)', ylabel: 'angle of reflection (°)', x0: 0, y0: 0, line: function () { return function (x) { return x; }; } },
      result: function (rows) { var r = null; rows.forEach(function (q) { if (Math.abs(q.i - p.i_deg) < 1e-9) r = q; }); if (!r) return null;
        return { label: 'Angle of reflection for ' + fx(p.i_deg, 0) + '° incidence', value: r.r, unit: '°', digits: 0, truth: p.i_deg, note: 'In every row the two angles are equal: sound obeys the same law of reflection as light.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ black and white tins
  LABS['sw7-black-white-tins'] = (function () {
    var l0, l1, sw;
    return {
      intro: 'Two identical tins, one painted dull black and one white, hold equal amounts of water with a digital thermometer in each. They stand side by side in the sun; on this bench a reflector lamp stands in for the sun.',
      given: function () { return ['Both tins start at ' + fx(p.Ta, 1) + ' °C, the temperature of the room.']; },
      build: function () {
        var tb = can(S.scene, 0.04, 0.11, mat(0x101112, 0.95, 0, { side: T.DoubleSide }), -0.12, 0, BZ), tw = can(S.scene, 0.04, 0.11, mat(0xf4f4f1, 0.7, 0, { side: T.DoubleSide }), 0.12, 0, BZ);
        [tb, tw].forEach(function (g) { cyl(g, 0.037, 0.037, 0.08, waterM, 0, 0.043, 0, 24); probe(g, 0.01, 0.1, 0, 0.14); S.contact(0.12, 0.12, g.position.x, BZ, 0.45); });
        var lamp = S.stand({ x: 0.2, z: BZ - 0.22, h: 0.6, armY: 0.5, armLen: 0.22 }); var hd = S.mesh(new T.ConeGeometry(0.09, 0.1, 28, 1, true), mat(0xc4c9ce, 0.3, 0.9, { side: T.DoubleSide })); add(S.scene, hd, 0.03, 0.48, BZ - 0.2); hd.rotation.x = -0.5;
        sph(S.scene, 0.03, new T.MeshBasicMaterial({ color: 0xfff0c0 }), 0.03, 0.455, BZ - 0.19);
        l0 = lcd(-0.12, BZ + 0.18, 'BLACK TIN  °C', 0.15); l1 = lcd(0.12, BZ + 0.18, 'WHITE TIN  °C', 0.15); sw = S.stopwatch([0.42, 0.035, BZ + 0.18], [-1.2, -0.3, 0]);
        S.addApparatus('black', tb, 'Black tin', 'A dull black surface absorbs most of the radiation that falls on it.');
        S.addApparatus('white', tw, 'White tin', 'A white surface reflects most of the radiation.');
        S.addApparatus('lamp', lamp, 'Lamp (the sun)', 'Stands in for sunlight falling equally on both tins.');
        S.addApparatus('sw', sw.group, 'Stopwatch', 'Times how long the tins have stood in the light.');
        return { handAt: function (c) { return new T.Vector3(c.set.tin ? 0.12 : -0.12, 0.26, BZ); },
          update: function (c, r, k, done) { var t = c.set.tm * (done ? 1 : k);
            l0.set(fx(K.view({ t: 0 }, Q({ tin: 0, tm: t })).T, 1)); l1.set(fx(K.view({ t: 0 }, Q({ tin: 1, tm: t })).T, 1)); sw.t = t; sw.on = false; } };
      },
      conds: [[0, 1200], [1, 1200], [0, 2400], [1, 2400]].map(function (s) { return { label: (s[0] ? 'White' : 'Black') + ' tin after ' + fx(s[1] / 60, 0) + ' min', set: { tin: s[0], tm: s[1] } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { tin: q.tin, tm: q.tm, T: v.T, rise: v.rise }; },
      runLabel: 'Leave the tins in the light', dur: 2.2, hudLabel: 'Thermometer',
      runText: 'Leave both tins in the light and read the thermometer of the chosen tin at the chosen time. (The stopwatch runs fast here.)',
      live: function (r, done) { return done ? (r.tin ? 'White' : 'Black') + ' tin after ' + fx(r.tm / 60, 0) + ' min: ' + fx(r.T, 1) + ' °C, a rise of ' + fx(r.rise, 1) + ' °C.' : 'Both tins are at room temperature.'; },
      hud: function (r) { return fx(r.T, 1) + ' °C'; },
      cols: [['Tin', function (r) { return r.tin ? 'white' : 'black'; }], ['time (min)', function (r) { return fx(r.tm / 60, 0); }], ['T (°C)', function (r) { return fx(r.T, 1); }], ['rise (°C)', function (r) { return fx(r.rise, 1); }]],
      theory: { formula: 'rise (black) : rise (white) = heat absorbed (black) : heat absorbed (white)' },
      result: function (rows) { var b = rowAt(rows, 2), w = rowAt(rows, 3); if (!b || !w || !w.rise) return null;
        return { label: 'Heat absorbed, black ÷ white', value: b.rise / w.rise, unit: '', digits: 2, truth: p.a0 / p.a1, note: 'From the two rises after 40 minutes. Thermometers that read to 0.1 °C fix this ratio to a few per cent.' }; },
      tol: 0.05,
    };
  })();

  // ------------------------------------------------------------------------------------------ specific heat of a liquid
  LABS['sw7-specific-heat-liquid'] = (function () {
    var bob, str, lc, lb, liq, CX = 0.18, HX = -0.25;
    return {
      view: [[0.0, 0.55, 1.1], [-0.02, 0.12, BZ]],
      intro: 'A copper calorimeter in an insulating jacket holds kerosene. A brass bob on a thread is heated in boiling water on a hot plate and then dropped into the kerosene; a thermometer shows the highest temperature reached.',
      given: function () { return ['Brass bob: ' + fx(p.m1 * 1000, 0) + ' g at ' + fx(p.T1, 0) + ' °C; specific heat of brass ' + fx(p.c1, 0) + ' J/(kg K).', 'Calorimeter and stirrer (copper): ' + fx(p.mc * 1000, 0) + ' g, ' + fx(p.cc, 0) + ' J/(kg K).', 'Kerosene starts at ' + fx(p.T2, 1) + ' °C.']; },
      build: function () {
        var hp = hotplate(HX, BZ); var bk = S.beaker(0.05, 0.11, [HX, 0.046, BZ], 0x8fc4e0, 0.7);
        var jk = grp(CX, 0, BZ); box(jk, 0.15, 0.1, 0.15, M.wood, 0, 0.05, 0); can(jk, 0.045, 0.1, mat(0xc8764a, 0.3, 1, { side: T.DoubleSide }), 0, 0.012, 0);
        liq = cyl(jk, 0.042, 0.042, 1, mat(0xe9d27a, 0.2, 0, { transparent: true, opacity: 0.8 }), 0, 0, 0, 24); probe(jk, 0.02, 0.12, 0.01, 0.16); S.contact(0.2, 0.2, CX, BZ, 0.45);
        bob = cyl(S.scene, 0.014, 0.014, 0.03, M.brass, 0, 0, 0, 20); str = thread();
        lc = lcd(0.5, BZ + 0.14, 'THERMOMETER  °C', 0.15); lb = lcd(0.5, BZ - 0.06, 'KEROSENE  g', 0.15);
        S.addApparatus('hot', hp, 'Hot plate and boiling water', 'Brings the brass bob to the temperature of boiling water.');
        S.addApparatus('cal', jk, 'Calorimeter', 'A copper can in a wooden jacket, so that very little heat is lost to the room.');
        S.addApparatus('bob', bob, 'Brass bob', 'A solid whose specific heat is known.');
        S.addApparatus('th', lc.group, 'Thermometer', 'Shows the temperature of the kerosene.');
        return { handAt: function () { return new T.Vector3(HX, 0.36, BZ); },
          update: function (c, r, k, done) { var x, y, lev = 0.04 + 0.03 * c.set.m2 / 0.12;
            liq.scale.y = lev; liq.position.y = 0.015 + lev / 2;
            if (k < 0.3) { x = HX; y = 0.09; } else if (k < 0.5) { var e = (k - 0.3) / 0.2; x = HX + (CX - HX) * e; y = 0.09 + 0.2 * Math.sin(e * Math.PI) + (0.05 - 0.09) * e; } else { x = CX; y = 0.04; }
            bob.position.set(x, y, BZ); str.set([[x, y + 0.015, BZ], [x, y + 0.2, BZ]]);
            lc.set(fx(k < 0.5 ? p.T2 : p.T2 + (r.Tf - p.T2) * (1 - Math.exp(-(k - 0.5) * 12)), 2)); if (done) lc.set(fx(r.Tf, 2)); lb.set(fx(c.set.m2 * 1000, 0)); } };
      },
      conds: [0.12, 0.15].map(function (m, i) { return { label: 'Trial ' + (i + 1) + ': ' + fx(m * 1000, 0) + ' g of kerosene', set: { m2: m } }; }),
      read: function (q) { var Tf = K.measure(q).Tf; return { m2: q.m2, Tf: Tf, c: (q.m1 * q.c1 * (q.T1 - Tf) - q.mc * q.cc * (Tf - q.T2)) / (q.m2 * (Tf - q.T2)) }; },
      runLabel: 'Transfer the hot bob and stir', dur: 3.0, hudLabel: 'Final temperature',
      runText: 'Lift the bob out of the boiling water, drop it quickly into the kerosene, stir and note the highest temperature. Repeat with a different mass of kerosene.',
      live: function (r, done) { return done ? 'With ' + fx(r.m2 * 1000, 0) + ' g of kerosene the temperature rose to ' + fx(r.Tf, 2) + ' °C.' : 'The bob is in the boiling water; the kerosene is at ' + fx(p.T2, 1) + ' °C.'; },
      hud: function (r) { return fx(r.Tf, 2) + ' °C'; },
      cols: [['kerosene (g)', function (r) { return fx(r.m2 * 1000, 0); }], ['final T (°C)', function (r) { return fx(r.Tf, 2); }], ['c of kerosene (J/kg K)', function (r) { return fx(r.c, 0); }]],
      theory: { formula: 'm₁c₁(T₁ − T) = (m₂c₂ + m_c c_c)(T − T₂)' },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.c; })); if (!isFinite(m)) return null;
        return { label: 'Specific heat capacity of kerosene', value: m, unit: 'J/(kg·K)', digits: 0, truth: p.c2, note: 'About half that of water: kerosene warms about twice as much for the same heat.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ cooling curve of wax
  LABS['sw7-wax-cooling-curve'] = (function () {
    var wax, lc, sw, mins = [0, 1, 2, 3, 6, 9, 12, 14, 16, 20], liqM = mat(0xf3e2a6, 0.2, 0, { transparent: true, opacity: 0.75 }), solM = mat(0xf4f1e6, 0.9), TX = 0.11;
    return {
      view: [[0.1, 0.55, 1.0], [0.12, 0.2, BZ]],
      intro: 'A test tube of paraffin wax has just been melted in a water bath and is now clamped in the air to cool. A thermometer stands in the wax and a stopwatch is running.',
      build: function () {
        var stand = S.stand({ x: 0.1, z: BZ, h: 0.5, armY: 0.3, armLen: 0.2 });
        var tube = grp(TX, 0.16, BZ); add(tube, new T.Mesh(new T.CylinderGeometry(0.012, 0.012, 0.16, 24, 1, true), M.glass), 0, 0.08, 0); add(tube, new T.Mesh(new T.SphereGeometry(0.012, 20, 12, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), M.glass), 0, 0, 0);
        wax = cyl(tube, 0.0105, 0.0105, 0.07, liqM, 0, 0.036, 0, 20); probe(tube, 0, 0.12, 0, 0.2);
        lc = lcd(0.48, BZ + 0.14, 'THERMOMETER  °C', 0.15); sw = S.stopwatch([0.3, 0.035, BZ + 0.18], [-1.2, -0.3, 0]);
        S.addApparatus('tube', tube, 'Test tube of wax', 'Clear while the wax is liquid; it turns cloudy and white as it sets.');
        S.addApparatus('stand', stand, 'Stand and clamp', 'Holds the tube in still air.');
        S.addApparatus('th', lc.group, 'Thermometer', 'Read every time to the nearest 0.5 °C.');
        S.addApparatus('sw', sw.group, 'Stopwatch', 'Runs from the moment the tube is taken out of the water bath.');
        return { handAt: function () { return new T.Vector3(0.3, 0.09, BZ + 0.18); },
          update: function (c, r, k, done) { var i = conds0(c), t0 = i > 0 ? mins[i - 1] * 60 : 0, t = t0 + (c.set.tm - t0) * (done ? 1 : k), T = K.view({ t: t }, p);
            lc.set(fx(T.reading, 1)); sw.t = t; sw.on = false; wax.material = T.T > p.Tm + 0.01 ? liqM : solM; } };
      },
      conds: mins.map(function (m) { return { label: 'At ' + m + ' min', set: { tm: m * 60 } }; }),
      read: function (q, c) { return { tm: c.set.tm, T: K.view({ t: c.set.tm }, p).reading }; },
      runLabel: 'Wait and read the thermometer', dur: 1.2, hudLabel: 'Thermometer',
      runText: 'Read the thermometer at each of the times in turn (the stopwatch runs fast here). Watch for the stretch where the reading does not change.',
      live: function (r, done) { return done ? 'At ' + fx(r.tm / 60, 0) + ' min the thermometer reads ' + fx(r.T, 1) + ' °C.' : 'Waiting for the time of the next reading.'; },
      hud: function (r) { return fx(r.T, 1) + ' °C'; },
      cols: [['time (min)', function (r) { return fx(r.tm / 60, 0); }], ['temperature (°C)', function (r) { return fx(r.T, 1); }]],
      theory: { formula: 'the flat part of the cooling curve is at the melting point' },
      graph: { x: function (r) { return r.tm / 60; }, y: function (r) { return r.T; }, xlabel: 'time (min)', ylabel: 'temperature (°C)', x0: 0, y0: 20 },
      result: function (rows) { var cnt = {}, best = null; rows.forEach(function (r) { var k2 = fx(r.T, 1); cnt[k2] = (cnt[k2] || 0) + 1; if (cnt[k2] >= 3 && (best === null || cnt[k2] > cnt[fx(best, 1)])) best = r.T; }); if (best === null) return null;
        return { label: 'Melting point of the wax', value: best, unit: '°C', digits: 1, truth: p.Tm, note: 'The temperature that stayed the same for several readings while the wax was setting.' }; },
    };
    function conds0(c) { return mins.indexOf(Math.round(c.set.tm / 60)); }
  })();

  // ------------------------------------------------------------------------------------------ bimetallic strip
  LABS['sw7-bimetallic-strip'] = (function () {
    var segs = [], lc, lg, N = 14, CX = -0.1, CY = 0.2, VIS = 1;
    return {
      view: [[0.02, 0.45, 0.85], [0.0, 0.16, BZ]],
      intro: 'A strip of brass riveted to a strip of iron is clamped at one end, with the brass on top, over an electric heater. A thermometer touches the strip and a millimetre scale stands behind its free end.',
      given: function () { return ['Length of the strip beyond the clamp: ' + fx(p.Ls * 100, 1) + ' cm; total thickness ' + fx(p.ts * 1000, 2) + ' mm.', 'Room temperature: ' + fx(p.T0, 0) + ' °C.']; },
      build: function () {
        var cl = grp(CX, 0, BZ); box(cl, 0.05, CY + 0.015, 0.06, M.iron, -0.03, (CY + 0.015) / 2, 0); box(cl, 0.03, 0.012, 0.04, M.alu, -0.005, CY + 0.01, 0); S.contact(0.1, 0.1, CX - 0.03, BZ, 0.45);
        for (var i = 0; i < N; i++) { var g = grp(0, 0, BZ); box(g, p.Ls / N * 1.04, 0.0015, 0.02, M.brass, 0, 0.00075, 0); box(g, p.Ls / N * 1.04, 0.0015, 0.02, M.iron, 0, -0.00075, 0); segs.push(g); }
        var ht = hotplate(CX + p.Ls / 2, BZ); 
        upright(tape(0.1, S.scene, { w: 0.02, bg: '#ffffff' }), CX + p.Ls + 0.012, CY - 0.08, BZ - 0.012);
        lc = lcd(0.42, BZ + 0.14, 'STRIP TEMPERATURE  °C', 0.16); lg = lcd(0.42, BZ - 0.06, 'TIP MOVED  mm', 0.16);
        S.addApparatus('strip', segs[0], 'Bimetallic strip', 'Brass on top, iron below, riveted so that they cannot slide over each other.');
        S.addApparatus('heater', ht, 'Heater', 'Warms the whole strip evenly.');
        S.addApparatus('clamp', cl, 'Clamp', 'Holds one end of the strip fixed.');
        S.addApparatus('th', lc.group, 'Thermometer', 'Shows the temperature of the strip.');
        return { handAt: function () { return new T.Vector3(CX + p.Ls / 2 + 0.06, 0.08, BZ + 0.09); },
          update: function (c, r, k, done) { var e = ease(k), kap = r.kap * e * VIS, ds = p.Ls / N, x = CX, y = CY, a = 0;
            segs.forEach(function (g) { var am = a - kap * ds / 2; g.position.set(x + Math.cos(am) * ds / 2, y + Math.sin(am) * ds / 2, BZ); g.rotation.z = am; x += Math.cos(am) * ds; y += Math.sin(am) * ds; a -= kap * ds; });
            lc.set(fx(p.T0 + (c.set.T - p.T0) * e, 0)); lg.set(fx(r.defl * 1000 * e, 1)); } };
      },
      conds: [75, 125, 175].map(function (t) { return { label: 'Heat to ' + t + ' °C', set: { T: t } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q), dT = q.T - q.T0; return { T: q.T, dT: dT, defl: v.defl, kap: v.kap, da: 4 * v.defl * q.ts / (3 * q.Ls * q.Ls * dT) }; },
      runLabel: 'Switch on the heater', dur: 2.2, hudLabel: 'Tip moved',
      runText: 'Heat the strip to the chosen temperature, let it settle and read on the scale how far the free end has moved down.',
      live: function (r, done) { return done ? 'At ' + fx(r.T, 0) + ' °C the tip has moved ' + fx(r.defl * 1000, 1) + ' mm towards the iron side.' : 'The strip is straight at room temperature.'; },
      hud: function (r) { return fx(r.defl * 1000, 1) + ' mm'; },
      cols: [['T (°C)', function (r) { return fx(r.T, 0); }], ['ΔT (°C)', function (r) { return fx(r.dT, 0); }], ['tip moved δ (mm)', function (r) { return fx(r.defl * 1000, 1); }], ['Δα (10⁻⁶ /K)', function (r) { return fx(r.da * 1e6, 2); }]],
      theory: { formula: 'δ = 3 Δα ΔT L² / (4 t)', note: 'Δα = α(brass) − α(iron); equal thickness and stiffness assumed' },
      graph: { x: function (r) { return r.dT; }, y: function (r) { return r.defl * 1000; }, xlabel: 'ΔT (°C)', ylabel: 'tip moved (mm)', x0: 0, y0: 0 },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.da; })); if (!isFinite(m)) return null;
        return { label: 'Difference of the two expansivities', value: m * 1e6, unit: '× 10⁻⁶ /K', digits: 2, truth: (p.a1 - p.a2) * 1e6, note: 'The strip bends towards the iron because brass expands more. The bend is proportional to the rise in temperature.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ level of a liquid on heating
  LABS['sw7-liquid-level-heating'] = (function () {
    var col, lc, lg, FX = 0.0, H0 = 0.02, TB = 0.2;
    return {
      view: [[0.05, 0.6, 1.1], [0.02, 0.2, BZ]],
      intro: 'A 100 mL flask is filled with glycerine and closed by a stopper carrying a narrow glass tube, so that the liquid stands a little way up the tube. The flask sits in a water bath on a hot plate, and a scale stands behind the tube.',
      given: function () { return ['Volume of the flask: ' + fx(p.V0 * 1e6, 0) + ' mL. Bore of the tube: ' + fx(p.a * 1e6, 2) + ' mm² (radius 1.5 mm).', 'Room temperature: ' + fx(p.T0, 0) + ' °C.']; },
      build: function () {
        var hp = hotplate(FX, BZ); var bath = S.beaker(0.07, 0.12, [FX, 0.046, BZ], 0x8fc4e0, 0.75);
        var fl = grp(FX, 0.1, BZ); sph(fl, 0.03, mat(0xd9c88a, 0.1, 0, { transparent: true, opacity: 0.7 }), 0, 0, 0); cyl(fl, 0.009, 0.011, 0.04, M.glass, 0, 0.045, 0, 16); cyl(fl, 0.011, 0.009, 0.014, M.cork, 0, 0.068, 0, 16);
        add(fl, new T.Mesh(new T.CylinderGeometry(0.003, 0.003, 0.3, 12, 1, true), M.glass), 0, 0.075 + 0.15, 0);
        col = cyl(fl, 0.0016, 0.0016, 1, mat(0xb3261e, 0.4), 0, 0, 0, 8);
        upright(tape(0.2, S.scene, { w: 0.02, bg: '#ffffff' }), FX + 0.016, TB, BZ - 0.006);
        lc = lcd(0.42, BZ + 0.14, 'WATER BATH  °C', 0.15); lg = lcd(0.42, BZ - 0.06, 'LEVEL ROSE  mm', 0.15);
        S.addApparatus('flask', fl, 'Flask and tube', 'A small expansion of the liquid shows as a long movement in the narrow tube.');
        S.addApparatus('bath', bath, 'Water bath', 'Warms the flask slowly and evenly.');
        S.addApparatus('hot', hp, 'Hot plate', 'Heats the water bath.');
        S.addApparatus('th', lc.group, 'Thermometer', 'Shows the temperature of the bath.');
        return { handAt: function () { return new T.Vector3(FX + 0.06, 0.06, BZ + 0.09); },
          update: function (c, r, k, done) { var e = ease(k), dip = k > 0 && k < 0.2 ? -0.004 * Math.sin(k / 0.2 * Math.PI) : 0, h = H0 + r.dh * e + dip;
            col.scale.y = Math.max(0.001, h); col.position.y = TB - 0.1 + h / 2; lc.set(fx(p.T0 + (c.set.T - p.T0) * e, 1)); lg.set(fx(r.dh * 1000 * e, 1)); } };
      },
      conds: [30, 35, 40, 45].map(function (t) { return { label: 'Bath at ' + t + ' °C', set: { T: t } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q), dT = q.T - q.T0; return { T: q.T, dT: dT, dh: v.dh, g: q.a * v.dh / (q.V0 * dT) }; },
      runLabel: 'Warm the bath and wait', dur: 2.4, hudLabel: 'Level rose',
      runText: 'Warm the bath to the chosen temperature and wait until the level stops moving. Watch for the small dip at the start, then read how far the level has risen.',
      live: function (r, done) { return done ? 'At ' + fx(r.T, 0) + ' °C the level has risen ' + fx(r.dh * 1000, 1) + ' mm.' : 'The level stands at its room-temperature mark.'; },
      hud: function (r) { return fx(r.dh * 1000, 1) + ' mm'; },
      cols: [['T (°C)', function (r) { return fx(r.T, 0); }], ['ΔT (°C)', function (r) { return fx(r.dT, 0); }], ['rise Δh (mm)', function (r) { return fx(r.dh * 1000, 1); }], ['a Δh / (V₀ ΔT) (10⁻⁴ /K)', function (r) { return fx(r.g * 1e4, 3); }]],
      theory: { formula: 'Δh = V₀ (γ − γ_glass) ΔT / a' },
      graph: { x: function (r) { return r.dT; }, y: function (r) { return r.dh * 1000; }, xlabel: 'ΔT (°C)', ylabel: 'rise (mm)', x0: 0, y0: 0 },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.g; })); if (!isFinite(m)) return null;
        return { label: 'Apparent expansivity of glycerine in glass', value: m * 1e4, unit: '× 10⁻⁴ /K', digits: 3, truth: (p.gam - p.gg) * 1e4, note: 'The real expansivity of the liquid is larger by the expansivity of the glass.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ rate of loss of heat
  LABS['sw7-rate-of-heat-loss'] = (function () {
    var ves = [], lc, sw, set = [['Calorimeter of hot water', {}], ['Wider vessel (twice the open area)', { A: 2 * p.A }], ['Polished calorimeter', { f: 0.6 }], ['Starting cooler, at 50 °C', { T0: 50 }], ['Twice the water', { m: 2 * p.m }]];
    return {
      view: [[0.05, 0.5, 0.95], [0.05, 0.1, BZ]],
      intro: 'Calorimeters of hot water stand on a cork mat with a thermometer and a stopwatch: a blackened one, a wider one, a polished one and a taller one that holds twice the water. Each time, the fall of 5 °C from the starting temperature is timed.',
      given: function () { return ['Room temperature: ' + fx(p.Ts, 0) + ' °C. Water: ' + fx(p.m * 1000, 0) + ' g, specific heat ' + fx(p.c, 0) + ' J/(kg K).']; },
      build: function () {
        var matb = box(S.scene, 0.3, 0.008, 0.2, M.cork, 0.02, 0.004, BZ); S.contact(0.36, 0.26, 0.02, BZ, 0.4);
        var bl = mat(0x24262a, 0.8, 0.2, { side: T.DoubleSide }), po = mat(0xe9ebed, 0.12, 1, { side: T.DoubleSide });
        [[0.04, 0.09, bl], [0.0566, 0.06, bl], [0.04, 0.09, po], [0.04, 0.09, bl], [0.04, 0.16, bl]].forEach(function (d) { var g = can(S.scene, d[0], d[1], d[2], 0.02, 0.008, BZ); cyl(g, d[0] * 0.94, d[0] * 0.94, d[1] * 0.8, waterM, 0, d[1] * 0.42, 0, 24); probe(g, 0.012, d[1], 0, 0.14); ves.push(g); });
        lc = lcd(0.42, BZ + 0.14, 'THERMOMETER  °C', 0.15); sw = S.stopwatch([0.42, 0.035, BZ - 0.08], [-1.2, -0.3, 0]);
        S.addApparatus('vessel', ves[0], 'Calorimeter', 'Hot water in an open vessel: it loses heat from its surface to the room.');
        S.addApparatus('th', lc.group, 'Thermometer', 'Shows the temperature of the water.');
        S.addApparatus('sw', sw.group, 'Stopwatch', 'Times the fall of 5 °C.');
        return { handAt: function () { return new T.Vector3(0.42, 0.09, BZ - 0.08); },
          update: function (c, r, k, done) { var i = conds1(c); ves.forEach(function (g, j) { g.visible = j === i; }); var e = done ? 1 : k;
            lc.set(fx(r.T0 - p.drop * e, 1)); sw.t = r.tdrop * e; sw.on = false; } };
      },
      conds: set.map(function (s) { return { label: s[0], set: s[1] }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { T0: q.T0, tdrop: v.tdrop, k: Math.log((q.T0 - q.Ts) / (q.T0 - q.drop - q.Ts)) / v.tdrop }; },
      runLabel: 'Time a fall of 5 °C', dur: 2.0, hudLabel: 'Time for 5 °C',
      runText: 'Start the stopwatch at the starting temperature and stop it when the water has cooled by 5 °C (the stopwatch runs fast here). Change one thing at a time and compare.',
      live: function (r, done) { return done ? 'From ' + fx(r.T0, 0) + ' °C to ' + fx(r.T0 - p.drop, 0) + ' °C took ' + fx(r.tdrop, 0) + ' s.' : 'The water is at its starting temperature.'; },
      hud: function (r) { return fx(r.tdrop, 0) + ' s'; },
      cols: [['What was changed', function (r) { return r.label; }], ['from (°C)', function (r) { return fx(r.T0, 0); }], ['time for 5 °C (s)', function (r) { return fx(r.tdrop, 0); }], ['k (10⁻⁴ /s)', function (r) { return fx(r.k * 1e4, 3); }]],
      theory: { formula: 'dT/dt = −k (T − Tₛ),   k = h A / (m c)' },
      result: function (rows) { var r = rowAt(rows, 0); if (!r) return null;
        return { label: 'Cooling constant of the first calorimeter', value: r.k * 1e4, unit: '× 10⁻⁴ /s', digits: 3, truth: p.h * p.A * p.f / (p.m * p.c) * 1e4, note: 'A larger open area cools faster; a polished surface, a smaller temperature difference and a larger mass all cool more slowly.' }; },
    };
    function conds1(c) { for (var i = 0; i < set.length; i++) if (set[i][0] === c.label) return i; return 0; }
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
