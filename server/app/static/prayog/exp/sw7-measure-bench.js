/* Prayogshala studio module: the school measuring bench (wave 7). One rig, nine set-ups - the lab id picks the apparatus:
     sw7-liquid-pressure-holes   a tall bottle of water with holes at three heights and a ring of holes
     sw7-pressure-cuboid-sand    an iron cuboid resting on sand on each of its faces
     sw7-bottle-upthrust         an empty bottle pushed into water with a force gauge
     sw7-cork-nail               the density of a cork and of iron nails
     sw7-beam-balance            a physical balance and a box of weights
     sw7-vernier-inside-depth    vernier callipers on a beaker and a calorimeter
     sw7-screw-gauge-sheet       a screw gauge, a metal sheet and an irregular lamina on graph paper
     sw7-paper-scale             paper scales of least count 0.5 cm and 0.2 cm
     sw7-lens-combination        two thin lenses in contact on an optical bench
   Physics: the school_w7 kernel pack - the same numbers the server checks. The shared workflow at the end of the
   file gives every set-up its steps: and each step its auto: action, and the result: of the experiment. */
HoolaStudio.define('sw7-measure-bench', function (S) {
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
  var sandM = new T.MeshStandardMaterial({ map: S.noiseTex(256, 256, '#cfb27a', 6000, 0.25, 2.0), roughness: 0.95 });
  var dropM = mat(0x9fd0ea, 0.2, 0, { transparent: true, opacity: 0.9 });

  // ------------------------------------------------------------------------------------------ water from holes
  LABS['sw7-liquid-pressure-holes'] = (function () {
    var BX = 0.05, BZ2 = -0.45, RBt = 0.045, jets = [], plugs = [], ND = 14;
    var DIRS = [[1, 0], [-1, 0], [0.7071, 0.7071], [-0.7071, 0.7071]], ys = [p.y0, p.y1, p.y2];
    return {
      camera: { pos: [0.1, 1.15, 2.1], look: [0.05, 0.3, -0.35] }, view: [[0.1, 0.95, 1.7], [0.05, 0.28, -0.4]],
      intro: 'A tall bottle of water stands on a stool with a tray below it. It has plugged holes at three heights and four more round it at one height. A tap keeps the water at the same level while a hole is open.',
      given: function () { return ['Water level above the base of the bottle: ' + fx(p.H * 100, 0) + ' cm.', 'The base of the bottle is ' + fx(p.S * 100, 0) + ' cm above the tray. g = ' + fx(p.g, 1) + ' m/s².']; },
      build: function () {
        var stool = box(S.scene, 0.16, p.S, 0.16, M.darkWood, BX, p.S / 2, BZ2); S.contact(0.22, 0.22, BX, BZ2, 0.5);
        var bot = grp(BX, p.S, BZ2);
        add(bot, new T.Mesh(new T.CylinderGeometry(RBt, RBt, p.H + 0.06, 36, 1, true), M.glass), 0, (p.H + 0.06) / 2, 0);
        cyl(bot, RBt * 0.96, RBt * 0.96, p.H, waterM, 0, p.H / 2, 0, 32); cyl(bot, RBt, RBt, 0.004, mat(0xd7dbe0, 0.4), 0, 0.002, 0, 36);
        ys.forEach(function (y) { plugs.push(cyl(bot, 0.004, 0.004, 0.012, mat(0xb3261e), RBt + 0.004, y, 0, 10)); plugs[plugs.length - 1].rotation.z = Math.PI / 2; });
        DIRS.forEach(function (d, i) { if (i === 0) return; var pg = cyl(bot, 0.004, 0.004, 0.012, mat(0x1d6fb8), d[0] * (RBt + 0.004), p.y2, d[1] * (RBt + 0.004), 10); pg.rotation.z = Math.PI / 2; pg.rotation.y = -Math.atan2(d[1], d[0]); });
        var tray = grp(0.05, 0, -0.33); box(tray, 1.2, 0.006, 0.56, mat(0xdfe5ea, 0.5), 0, 0.003, 0);
        flat(tape(0.62, S.scene), BX + RBt, 0.008, BZ2 + 0.07);
        for (var j = 0; j < 4; j++) { var arr = []; for (var i = 0; i < ND; i++) arr.push(sph(S.scene, 0.0045, dropM, 0, -1, 0)); jets.push(arr); }
        S.addApparatus('bottle', bot, 'Bottle of water', 'Red plugs close holes at three heights on one side; blue plugs close a ring of holes at one height.');
        S.addApparatus('stool', stool, 'Stool', 'Raises the bottle so that every jet has room to fall into the tray.');
        S.addApparatus('tray', tray, 'Tray and tape', 'The tape, laid from the wall of the bottle, shows where a jet lands.');
        return { handAt: function (c) { return new T.Vector3(BX + RBt + 0.03, p.S + (c.ring ? p.y2 : ys[c.set.hole]) + 0.03, BZ2); },
          update: function (c, r, k, done) {
            var y = c.ring ? p.y2 : ys[c.set.hole], tf = Math.sqrt(2 * (y + p.S) / p.g), grow = clamp01(k * 2.5);
            jets.forEach(function (arr, j) { var on = (c.ring ? true : j === 0) && k > 0, d = DIRS[j];
              arr.forEach(function (o, i) { var tt = tf * (i + 1) / ND; o.visible = on && (i + 1) / ND <= grow + 1e-9;
                o.position.set(BX + d[0] * (RBt + r.v * tt), Math.max(0.01, p.S + y - 0.5 * p.g * tt * tt), BZ2 + d[1] * (RBt + r.v * tt)); }); });
            plugs.forEach(function (pg, i) { pg.visible = !(k > 0 && !c.ring && i === c.set.hole) && !(k > 0 && c.ring && i === 2); });
          } };
      },
      conds: [0, 1, 2].map(function (i) { return { label: 'Hole ' + fx(ys[i] * 100, 0) + ' cm above the base', set: { hole: i } }; })
        .concat([{ label: 'Ring of four holes at ' + fx(p.y2 * 100, 0) + ' cm', set: { hole: 2 }, ring: true }]),
      read: function (q, c) { var v = K.view({ t: 0 }, q); return { y: v.y, depth: q.H - v.y, x: v.x, v: v.x / Math.sqrt(2 * (v.y + q.S) / q.g), ring: !!c.ring }; },
      runLabel: 'Pull out the plug', dur: 1.5, hudLabel: 'Jet lands at',
      runText: 'Open one hole at a time and read on the tape where the jet lands. Then open the ring of four holes at one height and compare the four jets.',
      live: function (r, done) { return done ? (r.ring ? 'All four jets land ' + fx(r.x * 100, 1) + ' cm out: the same in every direction.' : 'Depth ' + fx(r.depth * 100, 0) + ' cm: the jet lands ' + fx(r.x * 100, 1) + ' cm from the bottle.') : 'The hole is plugged.'; },
      hud: function (r) { return fx(r.x * 100, 1) + ' cm'; },
      cols: [['Hole', function (r) { return r.ring ? 'ring of 4' : 'single'; }], ['depth (cm)', function (r) { return fx(r.depth * 100, 0); }], ['jet lands (cm)', function (r) { return fx(r.x * 100, 1); }], ['speed (m/s)', function (r) { return fx(r.v, 2); }]],
      theory: { formula: 'P = ρ g d;   v = √(2 g d)', note: 'd is the depth of the hole below the water surface' },
      graph: { x: function (r) { return r.depth * 100; }, y: function (r) { return r.v; }, xlabel: 'depth of the hole (cm)', ylabel: 'speed of the jet (m/s)', x0: 0, y0: 0 },
      result: function (rows) { var i = ix(p.hole, 3), r = rowAt(rows, i); if (!r) return null;
        return { label: 'Speed of the jet at a depth of ' + fx(r.depth * 100, 0) + ' cm', value: r.v, unit: 'm/s', digits: 2, truth: Math.sqrt(2 * p.g * (p.H - ys[i])),
          note: 'From the range and the time of fall. The deeper the hole, the faster the jet; at one depth the jets are equal all round.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ cuboid on sand
  LABS['sw7-pressure-cuboid-sand'] = (function () {
    var cub = [], TOP = 0.06, lc, lg, fn = ['Largest face down', 'Middle face down', 'Smallest face down'], iron = mat(0x4a4f57, 0.45, 0.7);
    return {
      view: [[0.1, 0.5, 0.9], [0.05, 0.08, BZ]],
      intro: 'An iron cuboid, a tray of dry levelled sand, a spring balance and a depth gauge. The cuboid can be stood on any of its three different faces.',
      given: function () { return ['Sides of the cuboid by the scale: ' + fx(p.a * 100, 1) + ' cm × ' + fx(p.b * 100, 1) + ' cm × ' + fx(p.c * 100, 1) + ' cm.']; },
      build: function () {
        var tray = grp(0.05, 0, BZ); box(tray, 0.34, TOP, 0.26, mat(0x3e5a7a, 0.6), 0, TOP / 2, 0); box(tray, 0.32, 0.004, 0.24, sandM, 0, TOP + 0.001, 0); S.contact(0.4, 0.32, 0.05, BZ, 0.45);
        [[p.a, p.c, p.b], [p.a, p.b, p.c], [p.b, p.a, p.c]].forEach(function (d) { var m = box(S.scene, d[0], d[1], d[2], iron, 0.05, 0, BZ); m.userData.h = d[1]; cub.push(m); });
        lc = lcd(0.45, BZ + 0.16, 'SPRING BALANCE  N', 0.15); lg = lcd(0.64, BZ + 0.16, 'DEPTH GAUGE  mm', 0.15);
        S.addApparatus('cuboid', cub[2], 'Iron cuboid', 'The same weight whichever face it rests on; only the area under it changes.');
        S.addApparatus('tray', tray, 'Tray of sand', 'The dent in the sand shows how hard the cuboid presses.');
        S.addApparatus('balance', lc.group, 'Spring balance', 'Reads the weight of the cuboid in newtons.');
        S.addApparatus('gauge', lg.group, 'Depth gauge', 'Reads the depth of the dent.');
        return { handAt: function () { return new T.Vector3(0.05, TOP + 0.16, BZ); },
          update: function (c, r, k, done) { cub.forEach(function (m, i) { m.visible = i === c.set.face; m.position.y = TOP + m.userData.h / 2 + 0.06 * (1 - clamp01(k * 2)) - r.depth * clamp01(k * 2 - 1); });
            lc.set(fx(r.W, 2)); lg.set(done ? fx(r.depth * 1000, 1) : '0.0'); } };
      },
      conds: fn.map(function (n, i) { return { label: n, set: { face: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { W: v.W, l1: v.l1, l2: v.l2, A: v.A, P: v.W / v.A, depth: v.depth }; },
      runLabel: 'Lower the cuboid on to the sand', dur: 1.6, hudLabel: 'Depth of the dent',
      runText: 'Level the sand, lower the cuboid gently on the chosen face and read the depth of the dent. Work out the pressure from the weight and the area of that face.',
      live: function (r, done) { return done ? 'Face ' + fx(r.l1 * 100, 1) + ' cm × ' + fx(r.l2 * 100, 1) + ' cm: dent ' + fx(r.depth * 1000, 1) + ' mm deep.' : 'The cuboid is held above the sand; it weighs ' + fx(r.W, 2) + ' N.'; },
      hud: function (r) { return fx(r.depth * 1000, 1) + ' mm'; },
      cols: [['Face', function (r) { return fx(r.l1 * 100, 1) + ' × ' + fx(r.l2 * 100, 1) + ' cm'; }], ['A (cm²)', function (r) { return fx(r.A * 1e4, 1); }], ['W (N)', function (r) { return fx(r.W, 2); }], ['P = W/A (Pa)', function (r) { return fx(r.P, 0); }], ['dent (mm)', function (r) { return fx(r.depth * 1000, 1); }]],
      theory: { formula: 'P = W / A' },
      result: function (rows) { var i = ix(p.face, 3), r = rowAt(rows, i); if (!r) return null;
        return { label: 'Pressure with the ' + fn[i].toLowerCase().replace(' down', ''), value: r.P, unit: 'Pa', digits: 0, truth: K.view({ t: 0 }, p).P, note: 'The same weight on a smaller face gives a larger pressure and a deeper dent.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ upthrust on a bottle
  LABS['sw7-bottle-upthrust'] = (function () {
    var bot, lf, lv, wat, HB = 0.2, RBt = Math.sqrt(p.V / (Math.PI * 0.2)), WT = 0.26, jar;
    return {
      view: [[0.1, 0.6, 1.2], [0.1, 0.18, BZ]],
      intro: 'A sealed empty bottle floats in an overflow tank that is full to the spout. A force gauge pushes the bottle down; the water it displaces runs out of the spout into a measuring jar.',
      given: function () { return ['Weight of the empty bottle: ' + fx(p.mb * p.g, 2) + ' N.', 'Density of water: ' + fx(p.rho, 0) + ' kg/m³; g = ' + fx(p.g, 1) + ' m/s².']; },
      build: function () {
        var tank = grp(0, 0, BZ); add(tank, new T.Mesh(new T.BoxGeometry(0.3, WT + 0.03, 0.22), M.glass), 0, (WT + 0.03) / 2, 0);
        wat = box(tank, 0.29, WT, 0.21, waterM, 0, WT / 2, 0); var sp = cyl(tank, 0.006, 0.006, 0.06, M.glass, 0.17, WT - 0.005, 0, 12); sp.rotation.z = Math.PI / 2 - 0.4; S.contact(0.36, 0.28, 0, BZ, 0.45);
        jar = S.beaker(0.045, 0.2, [0.26, 0, BZ], 0x8fc4e0, 0.01);
        bot = grp(0, 0, BZ); cyl(bot, RBt, RBt, HB, mat(0xdfeff5, 0.2, 0, { transparent: true, opacity: 0.55 }), 0, HB / 2, 0, 28); cyl(bot, 0.014, 0.014, 0.03, mat(0x2c5fb4, 0.5), 0, HB + 0.015, 0, 16);
        cyl(bot, 0.004, 0.004, 0.2, M.chrome, 0, HB + 0.13, 0, 10);
        lf = lcd(0.55, BZ + 0.16, 'FORCE GAUGE  N', 0.15); lv = lcd(0.55, BZ - 0.02, 'WATER RUN OUT  mL', 0.15);
        S.addApparatus('tank', tank, 'Overflow tank', 'Full to the spout, so every bit of water displaced runs out.');
        S.addApparatus('bottle', bot, 'Empty bottle', 'Sealed, very light and about one litre in volume.');
        S.addApparatus('gauge', lf.group, 'Force gauge', 'Reads the push needed to hold the bottle down.');
        S.addApparatus('jar', jar, 'Measuring jar', 'Collects the displaced water so that its volume can be read.');
        return { handAt: function () { return new T.Vector3(0, WT + HB + 0.3, BZ); },
          update: function (c, r, k, done) { var f = c.set.frac * ease(k); bot.position.y = WT - HB * Math.max(0.03, f);
            jar.setLevel(Math.max(0.01, 0.78 * f)); lf.set(fx(r.F * ease(k), 2)); lv.set(fx(r.Vd * 1e6 * ease(k), 0)); } };
      },
      conds: [0.25, 0.5, 0.75, 1].map(function (f) { return { label: f === 1 ? 'Whole bottle under' : (f === 0.5 ? 'Half under' : (f === 0.25 ? 'A quarter under' : 'Three quarters under')), set: { frac: f } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { frac: q.frac, F: v.F, Wt: v.Wt, U: v.F + v.Wt, Vd: v.Vd, Wd: q.rho * q.g * v.Vd }; },
      runLabel: 'Push the bottle down', dur: 1.8, hudLabel: 'Push on the bottle',
      runText: 'Push the bottle under to the chosen mark. Read the push on the force gauge and the volume of water that has run out.',
      live: function (r, done) { return done ? 'Push ' + fx(r.F, 2) + ' N; ' + fx(r.Vd * 1e6, 0) + ' mL of water ran out.' : 'The bottle floats, hardly dipping into the water.'; },
      hud: function (r) { return fx(r.F, 2) + ' N'; },
      cols: [['Under water', function (r) { return fx(r.frac * 100, 0) + ' %'; }], ['push F (N)', function (r) { return fx(r.F, 2); }], ['upthrust F + W (N)', function (r) { return fx(r.U, 2); }], ['water out (mL)', function (r) { return fx(r.Vd * 1e6, 0); }], ['its weight (N)', function (r) { return fx(r.Wd, 2); }]],
      theory: { formula: 'U = F + W = ρ g V', note: 'upthrust = weight of the water displaced' },
      graph: { x: function (r) { return r.Vd * 1e6; }, y: function (r) { return r.U; }, xlabel: 'water displaced (mL)', ylabel: 'upthrust (N)', x0: 0, y0: 0 },
      result: function (rows) { var r = rowAt(rows, 3); if (!r) return null;
        return { label: 'Upthrust on the whole bottle', value: r.U, unit: 'N', digits: 2, truth: p.rho * p.g * p.V, note: 'In every row the upthrust equals the weight of the water that ran out: Archimedes\' principle.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ cork and nails
  LABS['sw7-cork-nail'] = (function () {
    var cork, nails, lb, lv, wcol, RC = 0.014, H0 = 0.08, CX = 0.25, names = ['Cork', 'Iron nails'];
    return {
      view: [[0.1, 0.5, 0.95], [0.1, 0.1, BZ]],
      intro: 'An electronic balance, a 100 mL measuring cylinder half full of water, a cork and five iron nails tied with thread. A pin is used to push the cork just under the water.',
      given: function () { return ['Density of water: ' + fx(p.rho_w, 0) + ' kg/m³ = ' + fx(p.rho_w / 1000, 3) + ' g/cm³.']; },
      build: function () {
        lb = lcd(-0.1, BZ, 'BALANCE  g', 0.17); var pan = cyl(S.scene, 0.05, 0.05, 0.004, M.alu, -0.1, 0.1, BZ - 0.03, 32); cyl(S.scene, 0.006, 0.006, 0.03, M.chrome, -0.1, 0.085, BZ - 0.03, 10);
        var cy = grp(CX, 0, BZ); add(cy, new T.Mesh(new T.CylinderGeometry(RC + 0.002, RC + 0.002, 0.2, 28, 1, true), M.glass), 0, 0.1, 0); cyl(cy, 0.03, 0.03, 0.006, M.glass, 0, 0.003, 0, 28);
        wcol = cyl(cy, RC, RC, 1, waterM, 0, 0, 0, 24); S.contact(0.1, 0.1, CX, BZ, 0.45);
        upright(tape(0.2, S.scene, { w: 0.012, bg: '#ffffff' }), CX + RC + 0.004, 0.006, BZ + 0.012);
        cork = cyl(S.scene, 0.012, 0.01, 0.022, mat(0xb98a55, 0.95), 0, 0, 0, 20);
        nails = grp(0, 0, 0); for (var i = 0; i < 5; i++) { cyl(nails, 0.0018, 0.0006, 0.05, mat(0x6e737a, 0.4, 0.8), (i - 2) * 0.004, 0, 0, 8); cyl(nails, 0.004, 0.004, 0.0015, mat(0x6e737a, 0.4, 0.8), (i - 2) * 0.004, 0.025, 0, 10); }
        lv = lcd(0.52, BZ + 0.12, 'WATER LEVEL  mL', 0.15);
        S.addApparatus('balance', lb.group, 'Electronic balance', 'Reads the mass in grams.');
        S.addApparatus('cylinder', cy, 'Measuring cylinder', 'The rise of the water level is the volume of the body.');
        S.addApparatus('cork', cork, 'Cork', 'Light and full of air spaces.');
        S.addApparatus('nails', nails, 'Iron nails', 'Five nails tied together, so that their volume is large enough to read.');
        return { handAt: function () { return new T.Vector3(CX, 0.26, BZ); },
          update: function (c, r, k, done) {
            var b = c.set.body, inW = k > 0.5, rise = r.V / (Math.PI * RC * RC) * clamp01(k * 2 - 1), lev = H0 + rise;
            wcol.scale.y = lev; wcol.position.y = 0.006 + lev / 2;
            var o = b === 0 ? cork : nails, other = b === 0 ? nails : cork; other.position.set(-0.3 + (b === 0 ? 0 : 0.06), 0.012, BZ + 0.14); other.rotation.z = Math.PI / 2;
            o.rotation.z = 0;
            if (!inW) o.position.set(-0.1, 0.102 + (b === 0 ? 0.011 : 0.025), BZ - 0.03);
            else o.position.set(CX, 0.006 + (b === 0 ? lev - 0.013 : 0.027), BZ);
            lb.set(fx(r.m * 1000, 2)); lv.set(fx((H0 * Math.PI * RC * RC + r.V * clamp01(k * 2 - 1)) * 1e6, 1));
          } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { body: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { m: v.m, V: v.V, rho: v.m / v.V, floats: v.floats > 0.5 }; },
      runLabel: 'Weigh it, then put it in the cylinder', dur: 2.4, hudLabel: 'Density',
      runText: 'Weigh the body on the balance, then lower it into the measuring cylinder (the cork has to be pushed just under with a pin) and read the rise of the water.',
      live: function (r, done) { return done ? 'Mass ' + fx(r.m * 1000, 2) + ' g, volume ' + fx(r.V * 1e6, 1) + ' mL: left alone it ' + (r.floats ? 'floats.' : 'sinks.') : 'The body is on the balance: ' + fx(r.m * 1000, 2) + ' g.'; },
      hud: function (r) { return fx(r.rho / 1000, 2) + ' g/cm³'; },
      cols: [['Body', function (r) { return r.label; }], ['m (g)', function (r) { return fx(r.m * 1000, 2); }], ['V (mL)', function (r) { return fx(r.V * 1e6, 1); }], ['density (g/cm³)', function (r) { return fx(r.rho / 1000, 2); }], ['in water', function (r) { return r.floats ? 'floats' : 'sinks'; }]],
      theory: { formula: 'density = mass / volume', note: 'floats if less dense than water, sinks if denser' },
      result: function (rows) { var i = ix(p.body, 2), r = rowAt(rows, i), o = rowAt(rows, 1 - i); if (!r) return null;
        return { label: 'Density of the ' + names[i].toLowerCase(), value: r.rho, unit: 'kg/m³', digits: 0, truth: p['rho' + i],
          note: o ? 'The ' + names[1 - i].toLowerCase() + ' came to ' + fx(o.rho, 0) + ' kg/m³. Water is ' + fx(p.rho_w, 0) + ' kg/m³: the lighter one floats, the denser one sinks.' : 'Measure the other body too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ beam balance
  LABS['sw7-beam-balance'] = (function () {
    var beam, panL, panR, ptr, bodies = [], wst = [], PY = 0.32, ARM = 0.16, WS = K.WEIGHTS, names = ['Body A (brass block)', 'Body B (glass stopper)'];
    function tried(m, j) { var tot = 0, i; for (i = 0; i < j && i < WS.length; i++) if (tot + WS[i] <= m + 1e-9) tot += WS[i]; return tot; }
    function kept(m) { var tot = 0, out = [], i; for (i = 0; i < WS.length; i++) if (tot + WS[i] <= m + 1e-9) { tot += WS[i]; out.push(WS[i] >= 0.001 ? fx(WS[i] * 1000, 0) + ' g' : fx(WS[i] * 1e6, 0) + ' mg'); } return out.join(' + '); }
    return {
      view: [[0.05, 0.55, 1.05], [0.02, 0.2, BZ]],
      intro: 'A physical balance in its case: a beam on a knife edge, a pan hanging from each end and a pointer over a small scale. A box holds weights from 100 g down to 10 mg.',
      build: function () {
        var g = grp(0.02, 0, BZ); box(g, 0.46, 0.02, 0.2, M.darkWood, 0, 0.01, 0); S.contact(0.52, 0.26, 0.02, BZ, 0.5);
        cyl(g, 0.008, 0.01, PY, M.brass, 0, 0.02 + PY / 2, 0, 20);
        txt(g, '|  |  |  |  |  ǀ  |  |  |  |  |', 0.07, 0, 0.06, 0.012, { bg: '#f7f4ea', ratio: 0.2 });
        beam = grp(0, 0.02 + PY, 0, g); box(beam, 2 * ARM + 0.02, 0.008, 0.008, M.brass, 0, 0, 0); ptr = box(beam, 0.002, 0.25, 0.002, mat(0x22252b), 0, -0.125, 0.008);
        panL = grp(0, 0, 0, g); panR = grp(0, 0, 0, g);
        [panL, panR].forEach(function (pn) { cyl(pn, 0.05, 0.05, 0.003, M.brass, 0, -0.2, 0, 32); [[-0.04, 0], [0.04, 0], [0, 0.04]].forEach(function (o) { var w = box(pn, 0.0012, 0.2, 0.0012, M.chrome, o[0] / 2, -0.1, o[1] / 2); w.rotation.z = o[0] * 2.4; w.rotation.x = -o[1] * 2.4; }); });
        bodies.push(box(panL, 0.03, 0.022, 0.025, M.brass, 0, -0.187, 0)); var stp = cyl(panL, 0.012, 0.016, 0.035, M.glass, 0, -0.18, 0, 20); bodies.push(stp);
        for (var i = 0; i < 8; i++) wst.push(cyl(panR, 0.011 - i * 0.0008, 0.011 - i * 0.0008, 0.007, M.brass, (i % 3 - 1) * 0.022, -0.195 + Math.floor(i / 3) * 0.0, (Math.floor(i / 3) - 1) * 0.022, 16));
        var wb = grp(0.42, 0, BZ + 0.12); box(wb, 0.14, 0.025, 0.08, M.wood, 0, 0.0125, 0); for (var j = 0; j < 6; j++) cyl(wb, 0.009 - j * 0.0008, 0.009 - j * 0.0008, 0.014, M.brass, -0.05 + j * 0.02, 0.03, 0, 14); S.contact(0.18, 0.12, 0.42, BZ + 0.12, 0.45);
        S.addApparatus('balance', g, 'Physical balance', 'With equal arms the beam is level when the masses in the two pans are equal.');
        S.addApparatus('weights', wb, 'Weight box', 'Brass weights from 100 g to 1 g and fractional weights down to 10 mg, handled with forceps.');
        return { handAt: function () { return new T.Vector3(0.02 + ARM, 0.2, BZ); },
          update: function (c, r, k, done) {
            var m = p['m' + c.set.body], j = Math.round(k * WS.length), tot = tried(m, j), diff = m - tot, tilt = Math.max(-0.12, Math.min(0.12, diff * 60));
            if (done) tilt = 0;
            beam.rotation.z = tilt; panL.position.set(-ARM * Math.cos(tilt), 0.02 + PY - ARM * Math.sin(tilt), 0); panR.position.set(ARM * Math.cos(tilt), 0.02 + PY + ARM * Math.sin(tilt), 0);
            bodies.forEach(function (b, i) { b.visible = i === c.set.body; });
            var n = 0, t2 = 0, i2; for (i2 = 0; i2 < j && i2 < WS.length; i2++) if (t2 + WS[i2] <= m + 1e-9) { t2 += WS[i2]; n++; }
            wst.forEach(function (w, i) { w.visible = i < n; });
          } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { body: i } }; }),
      read: function (q) { var m = K.measure(q).m_read; return { m: m, list: kept(q['m' + ix(q.body, 2)]) }; },
      runLabel: 'Try the weights, largest first', dur: 3.2, hudLabel: 'Weights in the pan',
      runText: 'With the body in the left pan, try each weight in the right pan from the largest down. A weight that makes its pan sink comes off; one that does not stays on. Stop when the pointer rests at the centre.',
      live: function (r, done) { return done ? 'Balanced. Weights left in the pan: ' + r.list + ' = ' + fx(r.m * 1000, 2) + ' g.' : 'The body is in the left pan and the beam is arrested.'; },
      hud: function (r) { return fx(r.m * 1000, 2) + ' g'; },
      cols: [['Body', function (r) { return r.label; }], ['Weights that stayed', function (r) { return r.list; }], ['Mass (g)', function (r) { return fx(r.m * 1000, 2); }]],
      theory: { formula: 'mass of the body = sum of the weights that balance it' },
      result: function (rows) { var i = ix(p.body, 2), r = rowAt(rows, i), o = rowAt(rows, 1 - i); if (!r) return null;
        return { label: 'Mass of ' + names[i].split(' (')[0], value: r.m * 1000, unit: 'g', digits: 2, truth: p['m' + i] * 1000, note: o ? 'The other body weighed ' + fx(o.m * 1000, 2) + ' g.' : 'Weigh the second body too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ vernier on a vessel
  LABS['sw7-vernier-inside-depth'] = (function () {
    var ves = [], cal, sl, rod, names = ['Glass beaker', 'Copper calorimeter'];
    function vs(v) { var cm = v * 100, msr = Math.floor(cm * 10 + 1e-6) / 10, vsd = Math.round((cm - msr) * 100); return 'main scale ' + fx(msr, 1) + ' cm + vernier ' + vsd + ' × 0.01 cm = ' + fx(cm, 2) + ' cm'; }
    return {
      view: [[0.05, 0.5, 0.9], [0.02, 0.1, BZ]],
      intro: 'Vernier callipers with inside jaws and a depth strip, a glass beaker and a copper calorimeter. The callipers read to 0.01 cm and have no zero error.',
      given: function () { return ['Least count of the callipers: ' + fx(p.lc * 100, 2) + ' cm. Zero error: nil.']; },
      build: function () {
        [0, 1].forEach(function (i) { var D = p['D' + i], h = p['h' + i], g = grp(0.02, 0, BZ);
          add(g, new T.Mesh(new T.CylinderGeometry(D / 2 + 0.002, D / 2 + 0.002, h + 0.003, 36, 1, true), i === 0 ? M.glass : mat(0xc8764a, 0.3, 1, { side: T.DoubleSide })), 0, (h + 0.003) / 2, 0);
          cyl(g, D / 2 + 0.002, D / 2 + 0.002, 0.003, i === 0 ? M.glass : M.copper, 0, 0.0015, 0, 36); ves.push(g); });
        S.contact(0.12, 0.12, 0.02, BZ, 0.45);
        cal = grp(0, 0, BZ); box(cal, 0.2, 0.016, 0.003, steelBar(), 0.08, 0, 0); box(cal, 0.004, 0.03, 0.003, M.steel, -0.018, -0.022, 0); 
        txt(cal, '0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15', 0.156, 0.078, 0.003, 0.0017, { ratio: 0.05, color: '#111' });
        sl = grp(0, 0, 0, cal); box(sl, 0.04, 0.022, 0.005, M.alu, 0.012, 0, 0.001); box(sl, 0.004, 0.03, 0.003, M.steel, 0.0, -0.022, 0);
        rod = box(cal, 0.2, 0.003, 0.0015, M.steel, 0, 0, -0.002);
        S.addApparatus('callipers', cal, 'Vernier callipers', 'The small upper jaws measure an inside diameter; the thin strip at the end measures a depth.');
        S.addApparatus('beaker', ves[0], 'Vessel', 'A straight-sided vessel; its internal volume is π D² h / 4.');
        return { handAt: function (c) { return new T.Vector3(0.1, p['h' + c.set.vessel] + 0.1, BZ); },
          update: function (c, r, k, done) {
            var v = c.set.vessel, D = p['D' + v], h = p['h' + v]; ves.forEach(function (g, i) { g.visible = i === v; });
            if (k < 0.5) { var o = D * clamp01(k * 4); cal.rotation.z = 0; cal.position.set(0.02 - D / 2 + 0.018, h + 0.03, BZ); sl.position.x = o - 0.018; rod.position.x = 0.08 + o; }
            else { var d2 = h * clamp01((k - 0.5) * 4); cal.rotation.z = -Math.PI / 2; cal.position.set(0.02 + D / 2 - 0.008, h + 0.18, BZ); sl.position.x = d2; rod.position.x = 0.08 + d2; }
          } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { vessel: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { D: v.D, dep: v.dep, V: v.V }; },
      runLabel: 'Measure the diameter, then the depth', dur: 3.0, hudLabel: 'Internal volume',
      runText: 'Open the inside jaws across the mouth of the vessel and read the diameter. Then stand the end of the main scale on the rim, run the depth strip to the bottom and read the depth.',
      live: function (r, done) { return done ? 'Diameter: ' + vs(r.D) + '. Depth: ' + vs(r.dep) + '.' : 'The jaws are closed: the callipers read zero.'; },
      hud: function (r) { return fx(r.V * 1e6, 1) + ' cm³'; },
      cols: [['Vessel', function (r) { return r.label; }], ['D (cm)', function (r) { return fx(r.D * 100, 2); }], ['depth h (cm)', function (r) { return fx(r.dep * 100, 2); }], ['V = πD²h/4 (cm³)', function (r) { return fx(r.V * 1e6, 1); }]],
      theory: { formula: 'reading = main scale + vernier division × least count;   V = π D² h / 4' },
      result: function (rows) { var i = ix(p.vessel, 2), r = rowAt(rows, i); if (!r) return null;
        return { label: 'Internal volume of the ' + names[i].toLowerCase(), value: r.V * 1e6, unit: 'cm³', digits: 1, truth: Math.PI * p['D' + i] * p['D' + i] * p['h' + i] / 4 * 1e6, note: 'Internal diameter ' + fx(r.D * 100, 2) + ' cm and depth ' + fx(r.dep * 100, 2) + ' cm.' }; },
    };
    function steelBar() { return M.steel; }
  })();

  // ------------------------------------------------------------------------------------------ screw gauge, sheet, lamina
  LABS['sw7-screw-gauge-sheet'] = (function () {
    var sheet, lam, paper, sg, spin, names = ['Metal sheet', 'Irregular lamina'];
    function sr(v) { var mm = v * 1000, msr = Math.floor(mm * 2 + 1e-6) / 2, cs = Math.round((mm - msr) * 100); return 'main scale ' + fx(msr, 1) + ' mm + circular scale ' + cs + ' × 0.01 mm = ' + fx(mm, 2) + ' mm'; }
    return {
      view: [[0.05, 0.42, 0.75], [0.0, 0.04, BZ]],
      intro: 'A screw gauge reading to 0.01 mm, a flat metal sheet, and an irregular lamina lying on centimetre graph paper where its outline has been traced.',
      given: function () { return ['Least count of the screw gauge: 0.01 mm. Zero error: nil.', 'The area is counted on the graph paper to the nearest half square (0.5 cm²).']; },
      build: function () {
        paper = new T.Mesh(new T.PlaneGeometry(0.2, 0.16), new T.MeshStandardMaterial({ roughness: 0.9, map: S.canvasTex(1000, 800, function (c, w, h) {
          c.fillStyle = '#f7f9f4'; c.fillRect(0, 0, w, h); for (var i = 0; i <= 200; i++) { c.strokeStyle = i % 10 === 0 ? '#5aa469' : (i % 5 === 0 ? '#9fd0a8' : '#d6ecd9'); c.lineWidth = i % 10 === 0 ? 2 : 1;
            c.beginPath(); c.moveTo(i * 5, 0); c.lineTo(i * 5, h); c.stroke(); c.beginPath(); c.moveTo(0, i * 5); c.lineTo(w, i * 5); c.stroke(); }
          c.strokeStyle = '#333'; c.lineWidth = 3; c.beginPath(); blob(c, 500, 400, 138); c.stroke(); }) }));
        flat(paper, 0.2, 0.0015, BZ + 0.04); S.scene.add(paper);
        var shp = new T.Shape(); (function () { var n = 40, i, a, r; for (i = 0; i <= n; i++) { a = i / n * Math.PI * 2; r = 0.0276 * (1 + 0.18 * Math.sin(3 * a) + 0.1 * Math.cos(5 * a)); if (i) shp.lineTo(Math.cos(a) * r, Math.sin(a) * r); else shp.moveTo(Math.cos(a) * r, Math.sin(a) * r); } })();
        lam = new T.Mesh(new T.ExtrudeGeometry(shp, { depth: 0.0012, bevelEnabled: false }), mat(0xb9bec4, 0.3, 0.9)); lam.rotation.x = -Math.PI / 2; S.scene.add(lam);
        sheet = box(S.scene, 0.09, 0.0006, 0.06, mat(0xc9ccd1, 0.3, 0.9), 0, 0, 0);
        sg = grp(-0.12, 0.05, BZ); var u = S.mesh(new T.TorusGeometry(0.03, 0.005, 10, 24, Math.PI), M.iron); u.rotation.z = Math.PI; add(sg, u, 0, 0, 0);
        cyl(sg, 0.003, 0.003, 0.012, M.steel, -0.03, 0.006, 0, 12); spin = cyl(sg, 0.003, 0.003, 0.03, M.steel, 0.03, 0.02, 0, 12); 
        var slv = cyl(sg, 0.006, 0.006, 0.04, M.alu, 0.03, 0.035, 0, 16), thm = cyl(sg, 0.009, 0.009, 0.035, M.chrome, 0.03, 0.07, 0, 24);
        sg.rotation.z = -Math.PI / 2; S.contact(0.14, 0.1, -0.12, BZ, 0.4);
        S.addApparatus('gauge', sg, 'Screw gauge', 'One turn of the thimble moves the spindle 0.5 mm; the thimble has 50 divisions.');
        S.addApparatus('sheet', sheet, 'Metal sheet', 'A thin flat sheet; its thickness is too small for a ruler.');
        S.addApparatus('lamina', lam, 'Irregular lamina', 'A flat piece with an irregular outline, traced on the graph paper.');
        return { handAt: function () { return new T.Vector3(-0.1, 0.12, BZ); },
          update: function (c, r, k, done) { var b = c.set.body, grip = k > 0.15 && k < 0.6;
            sheet.position.set(b === 0 && grip ? -0.125 : 0.0, b === 0 && grip ? 0.05 : 0.002, b === 0 && grip ? BZ : BZ + 0.1); sheet.rotation.z = b === 0 && grip ? Math.PI / 2 : 0;
            lam.position.set(b === 1 && grip ? -0.125 : 0.2, b === 1 && grip ? 0.05 : 0.003, b === 1 && grip ? BZ : BZ + 0.04); lam.rotation.y = b === 1 && grip ? Math.PI / 2 : 0;
            spin.position.y = 0.02 - 0.012 * (grip ? 1 : 0); } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { body: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { th: v.th, A: v.A, V: v.V, lam: q.body > 0.5 }; },
      runLabel: 'Grip it in the screw gauge and read', dur: 2.4, hudLabel: 'Thickness',
      runText: 'Close the screw gauge on the piece with the ratchet and read the thickness. For the lamina, also count the squares inside its outline on the graph paper.',
      live: function (r, done) { return done ? 'Thickness: ' + sr(r.th) + (r.lam ? '. Squares inside the outline: ' + fx(r.A * 1e4, 1) + ' cm².' : '.') : 'The screw gauge is open.'; },
      hud: function (r) { return fx(r.th * 1000, 2) + ' mm'; },
      cols: [['Piece', function (r) { return r.label; }], ['thickness (mm)', function (r) { return fx(r.th * 1000, 2); }], ['area (cm²)', function (r) { return r.lam ? fx(r.A * 1e4, 1) : '—'; }], ['volume (mm³)', function (r) { return r.lam ? fx(r.V * 1e9, 0) : '—'; }]],
      theory: { formula: 'reading = main scale + circular scale × least count;   V = A × t' },
      result: function (rows) { var r = rowAt(rows, 1), s = rowAt(rows, 0); if (!r) return null;
        return { label: 'Volume of the irregular lamina', value: r.V * 1e9, unit: 'mm³', digits: 0, truth: p.A1 * p.t1 * 1e9, note: (s ? 'The metal sheet is ' + fx(s.th * 1000, 2) + ' mm thick. ' : '') + 'Counting squares fixes the area only to about half a square, so the volume is good to about 1 %.' }; },
    };
    function blob(c, cx, cy, R) { var n = 60, i, a, r; for (i = 0; i <= n; i++) { a = i / n * Math.PI * 2; r = R * (1 + 0.18 * Math.sin(3 * a) + 0.1 * Math.cos(5 * a)); if (i) c.lineTo(cx + Math.cos(a) * r, cy - Math.sin(a) * r); else c.moveTo(cx + Math.cos(a) * r, cy - Math.sin(a) * r); } }
  })();

  // ------------------------------------------------------------------------------------------ paper scales
  LABS['sw7-paper-scale'] = (function () {
    var strips = [], pen, lcs = [0.005, 0.002], X0 = -0.1;
    function strip(lc) { var len = 0.2, n = Math.round(len / lc);
      var tex = S.canvasTex(2000, 160, function (c, w, h) { c.fillStyle = '#fbfaf3'; c.fillRect(0, 0, w, h); c.fillStyle = '#1a2a6c';
        for (var i = 0; i <= n; i++) { var x = i * lc / len * w, cm = Math.abs(i * lc * 100 - Math.round(i * lc * 100)) < 1e-6; c.fillRect(x - (cm ? 2 : 1), 0, cm ? 4 : 2, cm ? 70 : 42);
          if (cm) { c.font = '600 44px "Caveat", "Comic Sans MS", cursive'; c.textAlign = 'center'; c.fillText(String(Math.round(i * lc * 100)), Math.min(w - 20, Math.max(16, x)), 124); } } });
      var m = new T.Mesh(new T.PlaneGeometry(len, 0.022), new T.MeshStandardMaterial({ map: tex, roughness: 0.9 })); m.geometry.translate(len / 2, 0, 0); return m; }
    return {
      camera: { pos: [0.02, 0.5, 0.85], look: [0.0, 0.02, BZ + 0.05] }, view: [[0.0, 0.3, 0.42], [0.0, 0.0, BZ + 0.06]],
      intro: 'Two strips of paper have been ruled by hand as scales: one marked every 0.5 cm and one every 0.2 cm. A pencil is the length to be measured.',
      build: function () {
        lcs.forEach(function (lc, i) { var s = strip(lc); flat(s, X0, 0.0015, BZ + 0.05 + i * 0.07); S.scene.add(s); strips.push(s); });
        pen = grp(0, 0, 0); var b = cyl(pen, 0.0035, 0.0035, p.L - 0.012, mat(0xe8b024, 0.5), (p.L - 0.012) / 2, 0, 0, 6); b.rotation.z = Math.PI / 2;
        var t = S.mesh(new T.ConeGeometry(0.0035, 0.012, 12), M.wood); t.rotation.z = -Math.PI / 2; add(pen, t, p.L - 0.006, 0, 0);
        S.addApparatus('s1', strips[0], 'Paper scale, least count 0.5 cm', 'Marked every half centimetre.');
        S.addApparatus('s2', strips[1], 'Paper scale, least count 0.2 cm', 'Marked every two millimetres.');
        S.addApparatus('pencil', pen, 'Pencil', 'The length to be measured. Its true length is hidden.');
        return { handAt: function (c) { return new T.Vector3(X0 + 0.07, 0.03, BZ + 0.035 + (c.set.lc < 0.004 ? 0.07 : 0)); },
          update: function (c, r, k, done) { var i = c.set.lc < 0.004 ? 1 : 0, z = BZ + 0.035 + i * 0.07, e = ease(k); pen.position.set(X0, 0.004, z - 0.05 * (1 - e)); } };
      },
      conds: lcs.map(function (lc) { return { label: 'Scale of least count ' + fx(lc * 100, 1) + ' cm', set: { lc: lc } }; }),
      read: function (q) { return { lc: q.lc, reading: K.view({ t: 0 }, q).reading }; },
      runLabel: 'Lay the pencil along the scale', dur: 1.4, hudLabel: 'Length read',
      runText: 'Lay the pencil along the scale with its blunt end at zero and read the mark nearest to its tip. Do it on both scales.',
      live: function (r, done) { return done ? 'The tip is nearest the ' + fx(r.reading * 100, 1) + ' cm mark.' : 'The pencil is beside the scale.'; },
      hud: function (r) { return fx(r.reading * 100, 1) + ' cm'; },
      cols: [['Least count (cm)', function (r) { return fx(r.lc * 100, 1); }], ['Length read (cm)', function (r) { return fx(r.reading * 100, 1); }], ['Can be wrong by (cm)', function (r) { return '± ' + fx(r.lc * 50, 2); }]],
      theory: { formula: 'reading = number of divisions × least count', note: 'uncertain by half a division' },
      result: function (rows) { var r = rowAt(rows, 1), o = rowAt(rows, 0); if (!r) return null;
        return { label: 'Length of the pencil (0.2 cm scale)', value: r.reading * 100, unit: 'cm', digits: 1, truth: p.L * 100, note: (o ? 'The 0.5 cm scale gave ' + fx(o.reading * 100, 1) + ' cm. ' : '') + 'The finer scale lands closer to the true length.' }; },
      tol: 0.02,
    };
  })();

  // ------------------------------------------------------------------------------------------ lens combination
  LABS['sw7-lens-combination'] = (function () {
    var SET = [0.10, 0.15, 0.20, 0.30, 0.50], pick = [], holder, screen, img, X0 = -0.5, BY = 0.1, rack = [], target = p.f1 * p.f2 / (p.f1 + p.f2);
    function Fof() { if (pick.length !== 2) return NaN; var a = SET[pick[0]], b = SET[pick[1]]; return a * b / (a + b); }
    function toggle(i) { var k = pick.indexOf(i); if (k >= 0) pick.splice(k, 1); else { if (pick.length >= 2) pick.shift(); pick.push(i); }
      S.say(pick.length === 2 ? 'Together: 1/F = 1/' + fx(SET[pick[0]] * 100, 0) + ' + 1/' + fx(SET[pick[1]] * 100, 0) + ', so F = ' + fx(Fof() * 100, 1) + ' cm.' : 'Choose two lenses.'); S.render(); }
    return {
      intro: 'An optical bench with a lit cross-wire object, a lens holder and a screen. A rack holds five convex lenses marked 10, 15, 20, 30 and 50 cm. A combination of focal length ' + fx(target * 100, 0) + ' cm is wanted.',
      given: function () { return ['Focal length asked for: F = ' + fx(target * 100, 0) + ' cm.']; },
      setupUi: function (u) { u.h3('Choose two lenses for the holder'); var r = u.row();
        SET.forEach(function (f, i) { r.appendChild(u.button((pick.indexOf(i) >= 0 ? '✓ ' : '') + fx(f * 100, 0) + ' cm', function () { toggle(i); }, pick.indexOf(i) >= 0, false)); });
        u.live(function () { return pick.length === 2 ? 'This pair gives F = ' + fx(Fof() * 100, 1) + ' cm.' : 'Two lenses are needed.'; }); },
      setupOk: function () { return Math.abs(Fof() - target) < 1e-9; }, setupNeed: 'That pair does not give ' + fx(target * 100, 0) + ' cm. Use 1/F = 1/f1 + 1/f2 and choose again.',
      setupAuto: function () { pick = [SET.indexOf(p.f1), SET.indexOf(p.f2)]; },
      build: function () {
        var bench = box(S.scene, 1.1, 0.02, 0.06, M.iron, 0.05, 0.03, BZ); box(S.scene, 0.06, 0.03, 0.12, M.iron, -0.45, 0.015, BZ); box(S.scene, 0.06, 0.03, 0.12, M.iron, 0.55, 0.015, BZ); S.contact(1.2, 0.2, 0.05, BZ, 0.45);
        flat(tape(1.0, S.scene, { w: 0.02 }), X0, 0.0405, BZ + 0.018);
        function up(x) { var g = grp(x, 0.04, BZ); box(g, 0.03, 0.012, 0.05, M.alu, 0, 0.006, 0); cyl(g, 0.004, 0.004, BY - 0.04, M.chrome, 0, (BY - 0.04) / 2 + 0.01, 0, 12); return g; }
        var obj = up(X0); box(obj, 0.03, 0.06, 0.05, M.black, 0, BY - 0.04 + 0.03, 0); var win = add(obj, new T.Mesh(new T.PlaneGeometry(0.03, 0.03), new T.MeshBasicMaterial({ color: 0xfff1b8 })), 0.0152, BY - 0.04 + 0.03, 0); win.rotation.y = Math.PI / 2;
        holder = up(0); var ring = S.mesh(new T.TorusGeometry(0.028, 0.003, 10, 32), M.black); ring.rotation.y = Math.PI / 2; add(holder, ring, 0, BY - 0.04 + 0.035, 0);
        [-0.003, 0.003].forEach(function (dx) { var l = S.mesh(new T.SphereGeometry(0.027, 24, 16), M.glass, false); l.scale.set(0.12, 1, 1); add(holder, l, dx, BY - 0.04 + 0.035, 0); });
        screen = up(0.3); box(screen, 0.003, 0.09, 0.09, M.white, 0, BY - 0.04 + 0.035, 0);
        img = add(screen, new T.Mesh(new T.CircleGeometry(0.01, 24), new T.MeshBasicMaterial({ color: 0xffe9a0, transparent: true })), -0.0017, BY - 0.04 + 0.035, 0); img.rotation.y = -Math.PI / 2;
        var rk = grp(0.25, 0, BZ + 0.16); box(rk, 0.3, 0.012, 0.04, M.wood, 0, 0.006, 0); SET.forEach(function (f, i) { var l = S.mesh(new T.SphereGeometry(0.02, 20, 14), M.glass, false); l.scale.set(1, 1, 0.12 + 0.01 / f * 0.1); add(rk, l, -0.12 + i * 0.06, 0.034, 0); rack.push(l);
          txt(rk, fx(f * 100, 0) + ' cm', 0.045, -0.12 + i * 0.06, 0.007, 0.0205, { bg: '#f7f4ea', ratio: 0.3 }); });
        S.contact(0.34, 0.08, 0.25, BZ + 0.16, 0.4);
        S.addApparatus('bench', bench, 'Optical bench', 'A metre bench with a scale; the uprights slide along it.');
        S.addApparatus('object', obj, 'Lit object', 'A cross-wire in front of a lamp.');
        S.addApparatus('lens', holder, 'Lens holder', 'Holds the two chosen lenses in contact.');
        S.addApparatus('screen', screen, 'Screen', 'Moved until the image of the cross-wire is sharp.');
        S.addApparatus('rack', rk, 'Set of lenses', 'Convex lenses of focal length 10, 15, 20, 30 and 50 cm.');
        return { handAt: function (c) { return new T.Vector3(X0 + c.set.u + 0.2, BY + 0.12, BZ); },
          update: function (c, r, k, done) { var xs = X0 + c.set.u + r.v + (1 - ease(k)) * 0.12; holder.position.x = X0 + c.set.u; screen.position.x = xs;
            var blur = 1 + 3 * (1 - ease(k)); img.scale.setScalar(blur * (r.v / c.set.u)); img.material.opacity = 1 / blur; rack.forEach(function (l, i) { l.visible = pick.indexOf(i) < 0; }); } };
      },
      conds: [0.30, 0.40, 0.50].map(function (u) { return { label: 'Object ' + fx(u * 100, 0) + ' cm from the lenses', set: { u: u } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { u: q.u, v: v.v, F: q.u * v.v / (q.u + v.v) }; },
      runLabel: 'Move the screen until the image is sharp', dur: 1.8, hudLabel: 'Image distance',
      runText: 'Place the lens pair at the chosen distance from the object and slide the screen until the image of the cross-wire is sharp. Read u and v on the bench.',
      live: function (r, done) { return done ? 'u = ' + fx(r.u * 100, 1) + ' cm, sharp image at v = ' + fx(r.v * 100, 1) + ' cm.' : 'The image on the screen is blurred.'; },
      hud: function (r) { return fx(r.v * 100, 1) + ' cm'; },
      cols: [['u (cm)', function (r) { return fx(r.u * 100, 1); }], ['v (cm)', function (r) { return fx(r.v * 100, 1); }], ['F = uv/(u+v) (cm)', function (r) { return fx(r.F * 100, 2); }]],
      theory: { formula: '1/F = 1/f₁ + 1/f₂;   F = u v / (u + v)' },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.F; })); if (!isFinite(m)) return null;
        return { label: 'Focal length of the combination', value: m * 100, unit: 'cm', digits: 2, truth: target * 100, note: 'The ' + fx(p.f1 * 100, 0) + ' cm and ' + fx(p.f2 * 100, 0) + ' cm lenses in contact: 1/F = 1/f₁ + 1/f₂.' }; },
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
