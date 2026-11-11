/* Prayogshala studio module: the school motion bench (wave 7). One rig, ten set-ups - the lab id picks the apparatus:
     sw7-rolling-surfaces      a ball rolls off a ramp on to table, newspaper, cloth and sand
     sw7-rolling-vs-sliding    a book pulled with a spring balance, sliding and on pencil rollers
     sw7-trolley-block         a trolley from a ramp, a light gate and a wooden block
     sw7-incline-roller        a roller held on an inclined plane by a pan over a pulley
     sw7-double-incline        a ball on a double inclined plane
     sw7-projectile-range      a spring launcher and a landing strip
     sw7-free-fall-paper       a stone, a flat sheet and a crumpled sheet dropped past a timer
     sw7-ball-in-sand          a ball dropped into a tray of wet sand
     sw7-stairs-power          a model staircase with a (simulated) runner
     sw7-pendulum-dissipation  a pendulum whose amplitude dies away
   Physics: the school_w7 kernel pack - the same numbers the server checks. The shared workflow at the end of the
   file gives every set-up its steps: and each step its auto: action, and the result: of the experiment. */
HoolaStudio.define('sw7-motion-bench', function (S) {
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
  var steelM = M.steel, ballM = mat(0xb9bec4, 0.18, 1);
  function runway(x0, len, m, h) { var g = grp(x0, 0, BZ); box(g, len, h || 0.012, 0.12, m, len / 2, (h || 0.012) / 2, 0); S.contact(len + 0.05, 0.2, x0 + len / 2, BZ, 0.4); return g; }
  function clothTex(base, line) { var t = S.canvasTex(256, 256, function (c, w, h) { c.fillStyle = base; c.fillRect(0, 0, w, h); c.strokeStyle = line; c.lineWidth = 1;
    for (var i = 0; i < w; i += 6) { c.beginPath(); c.moveTo(i, 0); c.lineTo(i, h); c.stroke(); c.beginPath(); c.moveTo(0, i); c.lineTo(w, i); c.stroke(); } });
    t.wrapS = t.wrapT = T.RepeatWrapping; t.repeat.set(8, 1); return t; }
  function paperTex() { var t = S.canvasTex(512, 128, function (c, w, h) { c.fillStyle = '#e9e6dc'; c.fillRect(0, 0, w, h); c.fillStyle = '#6a6a6a';
    for (var y = 10; y < h; y += 9) for (var x = 6; x < w; x += 64) c.fillRect(x, y, 40 + (x * y) % 17, 2); c.fillStyle = '#222'; c.fillRect(8, 6, 150, 7); });
    t.wrapS = T.RepeatWrapping; t.repeat.set(3, 1); return t; }
  var sandM = new T.MeshStandardMaterial({ map: S.noiseTex(256, 256, '#cfb27a', 6000, 0.25, 2.0), roughness: 0.95 });

  // ------------------------------------------------------------------------------------------ a ball on four surfaces
  LABS['sw7-rolling-surfaces'] = (function () {
    var X0 = -0.62, SL = 15, ball, surf = [], RB = 0.012, rampG;
    var names = ['Bare table', 'Newspaper', 'Cloth', 'Sand'];
    return {
      intro: 'A grooved wooden ramp ends on a long runway. A steel ball is let go from a mark on the ramp, rolls on to the runway and stops. The runway can be covered with newspaper, cloth or a layer of sand.',
      given: function () { return ['Height of the release mark above the runway: h = ' + fx(p.h * 100, 1) + ' cm.']; },
      build: function () {
        var top = 0.3 * Math.sin(SL * Math.PI / 180);
        rampG = plank(0.3, X0 - 0.3 * Math.cos(SL * Math.PI / 180), 0.012 + top, BZ, -SL, M.wood);
        box(S.scene, 0.05, top, 0.09, M.darkWood, X0 - 0.3 * Math.cos(SL * Math.PI / 180) + 0.03, top / 2, BZ);
        var mk = box(rampG, 0.004, 0.002, 0.09, mat(0xb3261e), 0.3 - p.h / Math.sin(SL * Math.PI / 180), 0.001, 0);
        var mats = [M.wood, new T.MeshStandardMaterial({ map: paperTex(), roughness: 0.9 }), new T.MeshStandardMaterial({ map: clothTex('#3d6fa8', '#2c5486'), roughness: 1 }), sandM];
        var base = runway(X0, 1.12, M.wood);
        mats.forEach(function (m, i) { var s = box(S.scene, 1.1, i === 3 ? 0.006 : 0.002, 0.1, m, X0 + 0.56, 0.012 + (i === 3 ? 0.003 : 0.001), BZ); s.visible = false; surf.push(s); });
        flat(tape(1.1, S.scene), X0, 0.002, BZ + 0.09);
        ball = sph(S.scene, RB, ballM, 0, 0, 0);
        S.addApparatus('ramp', rampG, 'Ramp', 'A wooden ramp with a red release mark. The ball always starts from the mark.');
        S.addApparatus('runway', base, 'Runway', 'The flat surface the ball rolls on. It is covered in turn with newspaper, cloth and sand.');
        S.addApparatus('ball', ball, 'Steel ball', 'It rolls without slipping, so only the surface slows it.');
        return { handAt: function () { var q = onPlank(rampG, 0.3 - p.h / Math.sin(SL * Math.PI / 180), 0.03); return new T.Vector3(q[0], q[1], q[2]); },
          update: function (c, r, k) {
            surf.forEach(function (s, i) { s.visible = i === c.set.surf && i > 0; });
            var s0 = 0.3 - p.h / Math.sin(SL * Math.PI / 180), up = RB + (c.set.surf === 3 ? 0.004 : 0.002), q, e;
            if (k < 0.25) { e = (k / 0.25); q = onPlank(rampG, s0 + (0.3 - s0) * e * e, RB); ball.position.set(q[0], q[1], q[2]); }
            else { e = (k - 0.25) / 0.75; ball.position.set(X0 + r.d * (1 - (1 - e) * (1 - e)), 0.012 + up, BZ); }
          } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { surf: i } }; }),
      read: function (q) { var m = K.measure(q); return { d: m.d, h: q.h, c: q.h / m.d }; },
      runLabel: 'Release the ball', dur: 2.2, hudLabel: 'Distance rolled',
      runText: 'Choose a surface, let the ball go from the red mark and read on the tape how far it rolls before it stops.',
      live: function (r, done) { return done ? 'The ball stopped ' + fx(r.d * 100, 1) + ' cm from the foot of the ramp.' : 'The ball is at the release mark.'; },
      hud: function (r) { return fx(r.d * 100, 1) + ' cm'; },
      cols: [['Surface', function (r) { return r.label; }], ['h (cm)', function (r) { return fx(r.h * 100, 1); }], ['d (cm)', function (r) { return fx(r.d * 100, 1); }], ['c = h/d', function (r) { return fx(r.c, 3); }]],
      theory: { formula: 'm g h = c m g d,  so  c = h / d' },
      result: function (rows) { var i = ix(p.surf, 4), r = rowAt(rows, i); if (!r) return null;
        return { label: 'Rolling resistance on ' + names[i].toLowerCase(), value: r.c, unit: '', digits: 3, truth: p['c' + i], note: 'From c = h / d. Compare the four surfaces in the table: the softer the surface, the larger c.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ sliding against rolling
  LABS['sw7-rolling-vs-sliding'] = (function () {
    var book, bal, ptr, pencils = [], X0 = -0.45, Fmax = 5;
    return {
      intro: 'A heavy book lies on a wooden table top with a spring balance hooked to it. Three round pencils are kept ready to be used as rollers.',
      build: function () {
        var top = runway(-0.7, 1.4, M.wood);
        book = grp(X0, 0.012, BZ); box(book, 0.2, 0.035, 0.15, mat(0x7a1f2b, 0.7), 0, 0.0175, 0); box(book, 0.196, 0.029, 0.151, mat(0xf2ede0, 0.9), 0.003, 0.0175, 0);
        txt(book, 'PHYSICS', 0.12, 0, 0.0355, 0, { color: '#f0d9a0' }).rotation.x = -Math.PI / 2;
        bal = grp(X0 + 0.2, 0.03, BZ); var tube = cyl(bal, 0.011, 0.011, 0.16, M.brass, 0.12, 0, 0, 20); tube.rotation.z = Math.PI / 2;
        var face = txt(bal, '0   1   2   3   4   5 N', 0.14, 0.12, 0.0115, 0, { bg: '#f7f4ea', ratio: 0.12 }); face.rotation.x = -Math.PI / 2;
        ptr = box(bal, 0.003, 0.004, 0.02, mat(0xb3261e), 0.055, 0.0125, 0);
        var hook = cyl(bal, 0.0012, 0.0012, 0.05, M.chrome, 0.015, 0, 0, 8); hook.rotation.z = Math.PI / 2;
        var ring = S.mesh(new T.TorusGeometry(0.009, 0.0015, 8, 20), M.chrome); add(bal, ring, 0.21, 0, 0); ring.rotation.x = Math.PI / 2;
        for (var i = 0; i < 3; i++) { var pc = cyl(S.scene, 0.005, 0.005, 0.18, mat(0xe8b024, 0.5), 0, 0, 0, 6); pc.rotation.x = Math.PI / 2; pencils.push(pc); }
        S.addApparatus('book', book, 'Book', 'The body being pulled. Its weight is read first by hanging it from the balance.');
        S.addApparatus('balance', bal, 'Spring balance', 'Reads the pull in newtons. At a steady speed the pull equals the friction.');
        S.addApparatus('table', top, 'Table top', 'A plain wooden surface.');
        return { handAt: function () { return new T.Vector3(book.position.x + 0.42, 0.06, BZ); },
          update: function (c, r, k, done) {
            var roll = c.set.mode > 0.5, x = X0 + 0.45 * ease(k), y = 0.012 + (roll ? 0.01 : 0);
            book.position.set(x, y, BZ); bal.position.set(x + 0.1, y + 0.018, BZ);
            pencils.forEach(function (pc, i) { pc.position.set(roll ? X0 + 0.225 * ease(k) + (i - 1) * 0.07 : 0.55 + i * 0.03, 0.012 + 0.005, roll ? BZ : BZ + 0.0); pc.rotation.z = roll ? 0 : 0; pc.rotation.y = roll ? 0 : 0.2;
              if (!roll) pc.position.z = BZ + 0.02 * i; });
            var F = (k > 0.03) ? r.F : 0; ptr.position.x = 0.055 + 0.13 * Math.min(1, F / Fmax);
          } };
      },
      given: function () { return ['Weight of the book on the spring balance: W = ' + fx(p.m * p.g, 2) + ' N.']; },
      conds: [{ label: 'Sliding on the table', set: { mode: 0 } }, { label: 'On pencil rollers', set: { mode: 1 } }],
      read: function (q) { var m = K.measure(q); return { F: m.F, W: m.W, mu: m.F / m.W }; },
      runLabel: 'Pull at a steady speed', dur: 2.4, hudLabel: 'Spring balance',
      runText: 'Pull the book along at a steady speed and read the spring balance while it moves. Then put the pencils under it and pull again.',
      live: function (r, done) { return done ? 'Steady pull: ' + fx(r.F, 2) + ' N for a book weighing ' + fx(r.W, 2) + ' N.' : 'The book is at rest; the balance reads zero.'; },
      hud: function (r) { return fx(r.F, 2) + ' N'; },
      cols: [['How it moves', function (r) { return r.label; }], ['W (N)', function (r) { return fx(r.W, 2); }], ['F (N)', function (r) { return fx(r.F, 2); }], ['F / W', function (r) { return fx(r.mu, 3); }]],
      theory: { formula: 'F = μ W   (steady pull = friction)' },
      result: function (rows) { var a = rowAt(rows, 0), b = rowAt(rows, 1); if (!a) return null;
        return { label: 'Coefficient of sliding friction', value: a.mu, unit: '', digits: 2, truth: p.mu_s,
          note: b ? 'On rollers the pull was only ' + fx(b.F, 2) + ' N: about ' + fx(a.F / b.F, 0) + ' times smaller than when sliding.' : 'Take the reading on rollers too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ trolley and block
  LABS['sw7-trolley-block'] = (function () {
    var X0 = -0.45, SL = 12, rampG, tr, blk, gate;
    return {
      intro: 'A trolley runs down a smooth ramp, passes a light gate that shows its speed, and pushes a wooden block along the runway. The ramp has three release marks.',
      given: function () { return ['Mass of the trolley: M = ' + fx(p.M * 1000, 0) + ' g.', 'g = ' + fx(p.g, 1) + ' m/s².']; },
      build: function () {
        var LR = 0.45, cx = Math.cos(SL * Math.PI / 180), top = LR * Math.sin(SL * Math.PI / 180);
        rampG = plank(LR, X0 - LR * cx, 0.012 + top, BZ, -SL, M.wood, 0.1);
        box(S.scene, 0.05, top, 0.1, M.darkWood, X0 - LR * cx + 0.03, top / 2, BZ);
        [0.02, 0.04, 0.08].forEach(function (h) { box(rampG, 0.004, 0.002, 0.1, mat(0xb3261e), LR - h / Math.sin(SL * Math.PI / 180), 0.001, 0); });
        var base = runway(X0, 1.0, M.wood);
        flat(tape(0.9, S.scene), X0 + 0.08, 0.002, BZ + 0.09);
        tr = grp(0, 0, BZ); box(tr, 0.09, 0.022, 0.055, mat(0x2c5fb4, 0.5), 0, 0.022, 0);
        [[-0.03, 0.03], [0.03, 0.03], [-0.03, -0.03], [0.03, -0.03]].forEach(function (w) { var wh = cyl(tr, 0.011, 0.011, 0.008, M.rubber, w[0], 0.011, w[1], 20); wh.rotation.x = Math.PI / 2; });
        blk = box(S.scene, 0.06, 0.05, 0.06, M.darkWood, 0, 0, 0);
        var gp = grp(X0 + 0.02, 0.012, BZ); box(gp, 0.012, 0.09, 0.012, M.black, 0, 0.045, 0.07); box(gp, 0.012, 0.09, 0.012, M.black, 0, 0.045, -0.07); box(gp, 0.012, 0.012, 0.152, M.black, 0, 0.09, 0);
        gate = lcd(X0 - 0.05, BZ + 0.2, 'LIGHT GATE  m/s', 0.15);
        S.addApparatus('ramp', rampG, 'Ramp', 'A smooth ramp with release marks 2 cm, 4 cm and 8 cm above the runway.');
        S.addApparatus('trolley', tr, 'Trolley', 'It gains kinetic energy as it runs down.');
        S.addApparatus('block', blk, 'Wooden block', 'It is pushed along against friction; the distance shows the work done on it.');
        S.addApparatus('gate', gate.group, 'Light gate', 'Shows the speed of the trolley at the foot of the ramp.');
        return { handAt: function (c) { var q = onPlank(rampG, 0.45 - c.set.h / Math.sin(SL * Math.PI / 180), 0.06); return new T.Vector3(q[0], q[1], q[2]); },
          update: function (c, r, k, done) {
            var LR2 = 0.45, s0 = LR2 - c.set.h / Math.sin(SL * Math.PI / 180), e, q, xb = X0 + 0.08 + 0.03;
            if (k < 0.3) { e = k / 0.3; q = onPlank(rampG, s0 + (LR2 - s0 - 0.045) * e * e, 0); tr.position.set(q[0], q[1], BZ); tr.rotation.z = rampG.rotation.z; blk.position.set(xb, 0.012 + 0.025, BZ); }
            else { e = (k - 0.3) / 0.7; var s = r.s * (1 - (1 - e) * (1 - e)), ap = Math.min(1, e * 10); tr.rotation.z = 0;
              tr.position.set(X0 - 0.04 + 0.075 * ap + s, 0.012, BZ); blk.position.set(xb + s, 0.012 + 0.025, BZ); }
            gate.set(k >= 0.3 ? fx(r.v, 3) : '0.000');
          } };
      },
      conds: [0.02, 0.04, 0.08].map(function (h) { return { label: 'Release at ' + fx(h * 100, 0) + ' cm', set: { h: h } }; }),
      read: function (q) { var m = K.measure(q); return { h: q.h, v: m.v, s: m.s, KE: 0.5 * q.M * m.v * m.v, PE: q.M * q.g * q.h }; },
      runLabel: 'Release the trolley', dur: 2.2, hudLabel: 'Block pushed',
      runText: 'Release the trolley from a mark. Read its speed on the light gate and, when everything has stopped, how far the block was pushed.',
      live: function (r, done) { return done ? 'Speed ' + fx(r.v, 3) + ' m/s; the block was pushed ' + fx(r.s * 100, 1) + ' cm.' : 'The trolley is held at the release mark.'; },
      hud: function (r) { return fx(r.s * 100, 1) + ' cm'; },
      cols: [['h (cm)', function (r) { return fx(r.h * 100, 0); }], ['v (m/s)', function (r) { return fx(r.v, 3); }], ['block moved (cm)', function (r) { return fx(r.s * 100, 1); }],
        ['½Mv² (J)', function (r) { return fx(r.KE, 3); }], ['Mgh (J)', function (r) { return fx(r.PE, 3); }]],
      theory: { formula: 'Eₖ = ½ M v²  =  M g h' },
      graph: { x: function (r) { return r.v * r.v; }, y: function (r) { return r.s * 100; }, xlabel: 'v² (m²/s²)', ylabel: 'block moved (cm)', x0: 0, y0: 0 },
      result: function (rows) { var r = rowAt(rows, 2); if (!r) return null;
        return { label: 'Kinetic energy from the 8 cm mark', value: r.KE, unit: 'J', digits: 3, truth: p.M * p.g * 0.08, note: 'Worked out as ½ M v² from the light gate; the true value is the potential energy lost, M g h. The block moves in proportion to v².' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ roller on an inclined plane
  LABS['sw7-incline-roller'] = (function () {
    var pl, rol, pan, str, LP = 0.6, HX = -0.35, wts = [], lc;
    return {
      intro: 'A hinged plane can be set at any angle. A brass roller on it is tied to a string that passes over a pulley at the top and carries a pan; weights are added to the pan until the roller just stays at rest.',
      build: function () {
        var base = runway(HX - 0.05, 0.75, M.darkWood);
        pl = plank(LP, HX, 0.014, BZ, 30, M.wood, 0.1);
        var pul = cyl(pl, 0.02, 0.02, 0.008, M.alu, LP + 0.012, 0.018, 0, 24); pul.rotation.x = Math.PI / 2;
        var pro = S.mesh(new T.CircleGeometry(0.09, 32, 0, Math.PI / 2), new T.MeshStandardMaterial({ map: S.canvasTex(256, 256, function (c, w, h) { c.fillStyle = '#f4efe0'; c.fillRect(0, 0, w, h); c.strokeStyle = '#222'; c.fillStyle = '#222'; c.font = '600 22px sans-serif';
          for (var a = 0; a <= 90; a += 10) { var t = a * Math.PI / 180; c.beginPath(); c.moveTo(w / 2 + Math.cos(t) * 100, h / 2 - Math.sin(t) * 100); c.lineTo(w / 2 + Math.cos(t) * 124, h / 2 - Math.sin(t) * 124); c.stroke(); } }), side: T.DoubleSide, roughness: 0.8 }));
        add(S.scene, pro, HX, 0.014, BZ + 0.052);
        rol = cyl(S.scene, 0.025, 0.025, 0.07, M.brass, 0, 0, 0, 32); rol.rotation.x = Math.PI / 2;
        pan = grp(0, 0, BZ); cyl(pan, 0.03, 0.03, 0.003, M.alu, 0, 0, 0, 24);
        for (var i = 0; i < 5; i++) { var w = cyl(pan, 0.014, 0.014, 0.008, M.brass, 0, 0.006 + i * 0.0085, 0, 20); wts.push(w); }
        str = thread(); lc = lcd(0.55, BZ + 0.15, 'ANGLE OF THE PLANE', 0.15);
        S.addApparatus('plane', pl, 'Inclined plane', 'Hinged at the lower end, with a protractor to read the angle and a pulley at the top.');
        S.addApparatus('roller', rol, 'Roller', 'A brass roller. Its weight is what the graph will give.');
        S.addApparatus('pan', pan, 'Pan and weights', 'The pan and the weights in it pull up the plane through the string.');
        return { handAt: function () { return new T.Vector3(pan.position.x, pan.position.y + 0.08, BZ); },
          update: function (c, r, k, done) {
            pl.rotation.z = c.set.ang * Math.PI / 180;
            var q = onPlank(pl, LP * 0.55, 0.025), top = onPlank(pl, LP + 0.012, 0.038), e = ease(k);
            rol.position.set(q[0], q[1], BZ);
            var py = Math.max(0.03, top[1] - 0.12 - 0.02 * e); pan.position.set(top[0] + 0.02, py, BZ);
            var n = Math.max(1, Math.round(5 * e * r.F / 2.0)); wts.forEach(function (w, i) { w.visible = i < n; });
            str.set([[q[0], q[1], BZ], [top[0], top[1], BZ], [top[0] + 0.02, top[1] - 0.005, BZ], [top[0] + 0.02, py, BZ]]);
            lc.set(fx(c.set.ang, 0) + ' deg');
          } };
      },
      conds: [20, 30, 40, 50].map(function (a) { return { label: 'θ = ' + a + '°', set: { ang: a } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { ang: q.ang, sin: v.sin, F: v.F, mass: v.F / q.g }; },
      runLabel: 'Add weights until it balances', dur: 1.8, hudLabel: 'Pull of the pan',
      runText: 'Set the angle, then add weights to the pan until the roller neither runs down nor is pulled up. The total weight of the pan is the force F along the plane.',
      live: function (r, done) { return done ? 'Balanced with ' + fx(r.mass * 1000, 1) + ' g in all on the string: F = ' + fx(r.F, 3) + ' N at θ = ' + fx(r.ang, 0) + '°.' : 'The pan is too light: the roller would run down.'; },
      hud: function (r) { return fx(r.F, 3) + ' N'; },
      cols: [['θ (°)', function (r) { return fx(r.ang, 0); }], ['sin θ', function (r) { return fx(r.sin, 3); }], ['pan + weights (g)', function (r) { return fx(r.mass * 1000, 1); }], ['F (N)', function (r) { return fx(r.F, 3); }]],
      theory: { formula: 'F = W sin θ', note: 'the slope of F against sin θ is the weight W' },
      graph: { x: function (r) { return r.sin; }, y: function (r) { return r.F; }, xlabel: 'sin θ', ylabel: 'F (N)', x0: 0, y0: 0,
        line: function (pts) { var a = 0, b = 0; pts.forEach(function (q) { a += q[0] * q[1]; b += q[0] * q[0]; }); var m = b ? a / b : 0; return function (x) { return m * x; }; } },
      result: function (rows) { var a = 0, b = 0; rows.forEach(function (r) { a += r.F * r.sin; b += r.sin * r.sin; }); if (!b) return null;
        return { label: 'Weight of the roller (slope)', value: a / b, unit: 'N', digits: 3, truth: p.m * p.g, note: 'Slope of the straight line of F against sin θ through the origin.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ double inclined plane
  LABS['sw7-double-incline'] = (function () {
    var pA, pB, ball, RB = 0.012, LA = 0.5, LB = 0.6, mark;
    return {
      intro: 'Two grooved planks meet at the bottom to make a shallow V. A steel ball released on one side rolls down and climbs the other. A vertical scale on each side reads the height.',
      build: function () {
        var a1 = p.a1, a2 = p.a2;
        pA = plank(LA, 0, 0.02, BZ, 180 - a1, M.wood, 0.08); pB = plank(LB, 0, 0.02, BZ, a2, M.wood, 0.08);
        var ta = onPlank(pA, LA, 0), tb = onPlank(pB, LB, 0);
        box(S.scene, 0.03, ta[1], 0.08, M.darkWood, ta[0] + 0.02, ta[1] / 2, BZ); box(S.scene, 0.03, tb[1], 0.08, M.darkWood, tb[0] - 0.02, tb[1] / 2, BZ);
        upright(tape(0.2, S.scene, { w: 0.025 }), ta[0] - 0.03, 0.02, BZ + 0.05); upright(tape(0.2, S.scene, { w: 0.025 }), tb[0] + 0.03, 0.02, BZ + 0.05);
        ball = sph(S.scene, RB, ballM, 0, 0, 0); mark = box(S.scene, 0.004, 0.02, 0.085, mat(0xb3261e), 0, 0, 0);
        S.contact(1.2, 0.2, 0.05, BZ, 0.4);
        S.addApparatus('left', pA, 'First incline', 'The ball is released here from a measured height h1.');
        S.addApparatus('right', pB, 'Second incline', 'The ball climbs this side; the highest point it reaches gives h2.');
        S.addApparatus('ball', ball, 'Steel ball', 'It rolls without slipping, so very little energy is lost.');
        return { handAt: function (c) { var q = onPlank(pA, c.set.h1 / Math.sin(p.a1 * Math.PI / 180), -0.05); return new T.Vector3(q[0], q[1], BZ); },
          update: function (c, r, k, done) {
            var s1 = c.set.h1 / Math.sin(p.a1 * Math.PI / 180), s2 = r.h2 / Math.sin(p.a2 * Math.PI / 180), q, e;
            if (k < 0.5) { e = k / 0.5; q = onPlank(pA, s1 * (1 - e * e), -RB); } else { e = (k - 0.5) / 0.5; q = onPlank(pB, s2 * (1 - (1 - e) * (1 - e)), RB); }
            ball.position.set(q[0], q[1], BZ);
            var mq = onPlank(pB, s2, 0.012); mark.position.set(mq[0], mq[1], BZ); mark.visible = !!done;
          } };
      },
      conds: [0.06, 0.09, 0.12].map(function (h) { return { label: 'h1 = ' + fx(h * 100, 0) + ' cm', set: { h1: h } }; }),
      read: function (q) { var m = K.measure(q); return { h1: q.h1, h2: m.h2, ratio: m.h2 / q.h1 }; },
      runLabel: 'Release the ball', dur: 2.0, hudLabel: 'Height reached',
      runText: 'Release the ball from the chosen height on the first incline and mark the highest point it reaches on the second. Read that height on the scale.',
      live: function (r, done) { return done ? 'Released at ' + fx(r.h1 * 100, 1) + ' cm, it climbed to ' + fx(r.h2 * 100, 2) + ' cm.' : 'The ball is held at h1 = ' + fx(r.h1 * 100, 1) + ' cm.'; },
      hud: function (r) { return fx(r.h2 * 100, 2) + ' cm'; },
      cols: [['h1 (cm)', function (r) { return fx(r.h1 * 100, 1); }], ['h2 (cm)', function (r) { return fx(r.h2 * 100, 2); }], ['h2 / h1', function (r) { return fx(r.ratio, 3); }]],
      theory: { formula: 'm g h1  ≈  m g h2', note: 'energy kept = h2 / h1' },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.ratio; })); if (!isFinite(m)) return null;
        return { label: 'Fraction of the energy kept, h2 / h1', value: m, unit: '', digits: 3, truth: K.measure(p).ratio, note: 'Very nearly 1: mechanical energy is conserved apart from the small loss to rolling friction.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ projectile
  LABS['sw7-projectile-range'] = (function () {
    var X0 = -0.62, Y0 = 0.07, gun, ball, spot, lc, path = [];
    return {
      intro: 'A spring launcher fires a steel ball at the same speed every time. Its barrel can be set to any angle on a protractor. The ball lands on a strip at the same level as the muzzle, where carbon paper marks the spot.',
      build: function () {
        var strip = grp(X0, 0, BZ); box(strip, 1.2, Y0, 0.14, M.wood, 0.56, Y0 / 2, 0); S.contact(1.3, 0.22, X0 + 0.56, BZ, 0.4);
        box(strip, 1.02, 0.001, 0.1, mat(0x23262b, 0.9), 0.56, Y0 + 0.0006, -0.01);
        flat(tape(1.0, S.scene), X0, Y0 + 0.002, BZ + 0.055);
        gun = grp(X0, Y0, BZ); var bar = cyl(gun, 0.014, 0.014, 0.12, M.alu, -0.06, 0, 0, 24); bar.rotation.z = Math.PI / 2; cyl(gun, 0.016, 0.016, 0.02, M.black, -0.125, 0, 0, 24).rotation.z = Math.PI / 2;
        var yoke = box(S.scene, 0.03, 0.05, 0.05, M.iron, X0 - 0.06, Y0 - 0.02, BZ - 0.045);
        ball = sph(S.scene, 0.008, ballM, 0, 0, 0); spot = cyl(S.scene, 0.008, 0.008, 0.0012, mat(0xf2f2ef), 0, Y0 + 0.0015, BZ, 16);
        for (var i = 0; i < 14; i++) path.push(sph(S.scene, 0.003, mat(0xd9a520), 0, 0, 0));
        lc = lcd(X0 + 0.05, BZ + 0.2, 'ANGLE OF PROJECTION', 0.15);
        S.addApparatus('launcher', gun, 'Spring launcher', 'Fires the ball at the same speed each time; only the angle is changed.');
        S.addApparatus('strip', strip, 'Landing strip', 'Carbon paper on the strip marks where the ball lands; the tape gives the range.');
        return { handAt: function () { return new T.Vector3(X0 - 0.12, Y0 + 0.06, BZ); },
          update: function (c, r, k, done) {
            var a = c.set.ang * Math.PI / 180, x = r.R * k, y = x * Math.tan(a) - p.g * x * x / (2 * p.v0 * p.v0 * Math.cos(a) * Math.cos(a));
            gun.rotation.z = a; ball.position.set(X0 + x, Y0 + Math.max(0, y) + 0.008, BZ);
            path.forEach(function (d, i) { var f = (i + 1) / 15, xx = r.R * f; d.visible = f <= k + 1e-9 && k > 0;
              d.position.set(X0 + xx, Y0 + xx * Math.tan(a) - p.g * xx * xx / (2 * p.v0 * p.v0 * Math.cos(a) * Math.cos(a)) + 0.008, BZ); });
            spot.visible = !!done; spot.position.x = X0 + r.R; lc.set(fx(c.set.ang, 0) + ' deg');
          } };
      },
      conds: [15, 30, 45, 60, 75].map(function (a) { return { label: a + '°', set: { ang: a } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { ang: q.ang, R: v.R }; },
      runLabel: 'Fire the ball', dur: 1.2, hudLabel: 'Range',
      runText: 'Set the angle, fire, and read on the tape where the ball marked the carbon paper. Do all five angles.',
      live: function (r, done) { return done ? 'At ' + fx(r.ang, 0) + '° the ball landed ' + fx(r.R * 100, 1) + ' cm away.' : 'The launcher is loaded and set to ' + fx(r.ang, 0) + '°.'; },
      hud: function (r) { return fx(r.R * 100, 1) + ' cm'; },
      cols: [['Angle (°)', function (r) { return fx(r.ang, 0); }], ['Range (cm)', function (r) { return fx(r.R * 100, 1); }]],
      theory: { formula: 'R = v₀² sin 2θ / g', note: 'greatest when 2θ = 90°' },
      graph: { x: function (r) { return r.ang; }, y: function (r) { return r.R * 100; }, xlabel: 'angle of projection (°)', ylabel: 'range (cm)', x0: 0, y0: 0 },
      result: function (rows) { var b = null; rows.forEach(function (r) { if (!b || r.R > b.R + 1e-9) b = r; }); if (!b || rows.length < 3) return null;
        return { label: 'Angle of the greatest range', value: b.ang, unit: '°', digits: 0, truth: 45, note: 'The largest range in the table, ' + fx(b.R * 100, 1) + ' cm. Angles that add up to 90° gave equal ranges.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ stone and paper
  LABS['sw7-free-fall-paper'] = (function () {
    var bodies = [], lc, PAD = 0.02, names = ['Stone', 'Flat sheet of paper', 'The same sheet crumpled'];
    return {
      intro: 'A release clamp on a tall stand holds a body above a landing pad. A timer starts when the body is let go and stops when it hits the pad. The bodies are a stone, a flat sheet of A4 paper and the same sheet crumpled into a ball.',
      given: function () { return ['Height of fall: h = ' + fx(p.h * 100, 0) + ' cm.']; },
      build: function () {
        var stand = S.stand({ x: 0.1, z: BZ, h: p.h + 0.2, armY: p.h + PAD + 0.03, armLen: 0.3 });
        var pad = box(S.scene, 0.34, PAD, 0.36, mat(0x30343a, 0.8), 0.21, PAD / 2, BZ + 0.03); S.contact(0.4, 0.4, 0.21, BZ + 0.03, 0.4);
        upright(tape(p.h, S.scene, { w: 0.03 }), -0.02, PAD, BZ - 0.02);
        var stone = S.mesh(new T.DodecahedronGeometry(0.022, 0), mat(0x6f6a62, 0.9)); S.scene.add(stone);
        var sheet = S.mesh(new T.BoxGeometry(0.21, 0.0008, 0.297), mat(0xf4f3ee, 0.9)); S.scene.add(sheet);
        var crum = S.mesh(new T.IcosahedronGeometry(0.03, 0), mat(0xf4f3ee, 0.95, 0, { flatShading: true })); S.scene.add(crum);
        bodies = [stone, sheet, crum]; lc = lcd(0.62, BZ + 0.12, 'TIMER  seconds', 0.15);
        S.addApparatus('stand', stand, 'Stand and release clamp', 'Holds each body at the same height and lets it go from rest.');
        S.addApparatus('pad', pad, 'Landing pad', 'Stops the timer when the body lands.');
        S.addApparatus('timer', lc.group, 'Timer', 'Reads the time of fall to a thousandth of a second.');
        return { handAt: function () { return new T.Vector3(0.21, p.h + PAD + 0.06, BZ); },
          update: function (c, r, k, done) {
            var b = c.set.body, f = b === 1 ? Math.pow(k, 1.15) : k * k, y = PAD + p.h * (1 - f) + (b === 1 ? 0.001 : 0.022);
            bodies.forEach(function (o, i) { o.visible = i === b; o.position.set(0.21 + (b === 1 ? 0.03 * Math.sin(k * 14) * (1 - k) : 0), y, BZ + 0.03); o.rotation.z = b === 1 ? 0.2 * Math.sin(k * 14) * (k < 1 ? 1 : 0) : 0; });
            lc.set(fx(r.tf * (done ? 1 : k), 3));
          } };
      },
      conds: names.map(function (n, i) { return { label: n, set: { body: i } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { tf: v.tf, h: q.h, g: 2 * q.h / (v.tf * v.tf) }; },
      runLabel: 'Let it fall', dur: function (c, r) { return Math.max(0.8, r.tf * 1.6); }, hudLabel: 'Time of fall',
      runText: 'Clamp a body at the top, let it go and read the timer. Drop all three from the same height.',
      live: function (r, done) { return done ? 'Time of fall: ' + fx(r.tf, 3) + ' s.' : 'The body is held at ' + fx(r.h * 100, 0) + ' cm.'; },
      hud: function (r) { return fx(r.tf, 3) + ' s'; },
      cols: [['Body', function (r) { return r.label; }], ['h (cm)', function (r) { return fx(r.h * 100, 0); }], ['t (s)', function (r) { return fx(r.tf, 3); }], ['2h / t² (m/s²)', function (r) { return fx(r.g, 2); }]],
      theory: { formula: 'h = ½ g t²,  so  g = 2h / t²', note: 'true only when air resistance does not matter' },
      result: function (rows) { var r = rowAt(rows, 0); if (!r) return null; var f = rowAt(rows, 1), cb = rowAt(rows, 2);
        return { label: 'g from the falling stone', value: r.g, unit: 'm/s²', digits: 2, truth: p.g,
          note: (f && cb) ? 'The flat sheet took ' + fx(f.tf, 2) + ' s and the crumpled one ' + fx(cb.tf, 2) + ' s: the same paper, only the air resistance changed.' : 'Drop the paper both ways too.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ ball in sand
  LABS['sw7-ball-in-sand'] = (function () {
    var ball, dent, lc, TOP = 0.09, set = [[0.2, 0.25], [0.2, 0.5], [0.2, 1.0], [0.5, 0.5]];
    function rad(m) { return Math.pow(3 * m / (4 * Math.PI * 7850), 1 / 3); }
    return {
      intro: 'A deep tray of levelled wet sand stands under a tall stand with a release clamp. Steel balls of 200 g and 500 g are dropped from marked heights, and a depth gauge reads how deep the dent is.',
      build: function () {
        var stand = S.stand({ x: 0.0, z: BZ, h: 1.2, armY: 1.12, armLen: 0.24 });
        var tray = grp(0.05, 0, BZ + 0.02); box(tray, 0.3, TOP, 0.26, mat(0x3e5a7a, 0.6), 0, TOP / 2, 0); box(tray, 0.28, 0.004, 0.24, sandM, 0, TOP + 0.001, 0); S.contact(0.36, 0.32, 0.05, BZ + 0.02, 0.45);
        upright(tape(1.0, S.scene, { w: 0.03 }), -0.13, TOP, BZ - 0.03);
        ball = sph(S.scene, 1, ballM, 0, 0, 0); dent = cyl(S.scene, 1, 1, 0.002, mat(0x8a744c, 1), 0.05, TOP + 0.004, BZ + 0.02, 24);
        lc = lcd(0.5, BZ + 0.14, 'DEPTH GAUGE  mm', 0.15);
        S.addApparatus('stand', stand, 'Stand with release clamp', 'The clamp is set to the height marked on the scale, measured from the sand.');
        S.addApparatus('tray', tray, 'Tray of wet sand', 'The sand stops the ball; the dent shows how much work it did.');
        S.addApparatus('gauge', lc.group, 'Depth gauge', 'Reads the depth of the dent in millimetres.');
        return { handAt: function (c) { return new T.Vector3(0.05, TOP + c.set.h + 0.08, BZ + 0.02); },
          update: function (c, r, k, done) {
            var R = rad(c.set.m), f = Math.min(1, k / 0.8), y = TOP + R + c.set.h * (1 - f * f), sink = k > 0.8 ? (k - 0.8) / 0.2 : 0;
            ball.scale.setScalar(R); ball.position.set(0.05, y - sink * Math.min(r.d, R * 1.6), BZ + 0.02);
            dent.scale.set(R * 1.25, 1, R * 1.25); dent.visible = k >= 0.8; lc.set(done ? fx(r.d * 1000, 1) : '0.0');
          } };
      },
      conds: set.map(function (s) { return { label: fx(s[0] * 1000, 0) + ' g from ' + fx(s[1] * 100, 0) + ' cm', set: { m: s[0], h: s[1] } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { m: q.m, h: q.h, d: v.d, PE: v.PE, F: q.m * q.g * (q.h + v.d) / v.d }; },
      runLabel: 'Drop the ball', dur: 1.4, hudLabel: 'Depth of the dent',
      runText: 'Set the mass and the height, drop the ball and read the depth of the dent. Level the sand between drops.',
      live: function (r, done) { return done ? 'The ' + fx(r.m * 1000, 0) + ' g ball from ' + fx(r.h * 100, 0) + ' cm made a dent ' + fx(r.d * 1000, 1) + ' mm deep.' : 'The ball is held ' + fx(r.h * 100, 0) + ' cm above the sand.'; },
      hud: function (r) { return fx(r.d * 1000, 1) + ' mm'; },
      cols: [['m (g)', function (r) { return fx(r.m * 1000, 0); }], ['h (cm)', function (r) { return fx(r.h * 100, 0); }], ['m g h (J)', function (r) { return fx(r.PE, 2); }], ['dent (mm)', function (r) { return fx(r.d * 1000, 1); }], ['F (N)', function (r) { return fx(r.F, 1); }]],
      theory: { formula: 'Eₚ = m g h;   F d = m g (h + d)' },
      graph: { x: function (r) { return r.PE; }, y: function (r) { return r.d * 1000; }, xlabel: 'm g h (J)', ylabel: 'dent (mm)', x0: 0, y0: 0 },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.F; })); if (!isFinite(m)) return null;
        return { label: 'Resisting force of the sand', value: m, unit: 'N', digits: 1, truth: p.F, note: 'From F d = m g (h + d). More potential energy, from a greater height or a heavier ball, makes a deeper dent.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ power on the stairs
  LABS['sw7-stairs-power'] = (function () {
    var man, sw, lc, N = 20, SX = -0.55, RUN = 0.045, RISE = 0.03;
    return {
      intro: 'A scale model of a staircase with 20 steps. SIMULATED DATA: the small figure climbs with a fixed power that is hidden from you; a weighing machine shows the mass and a stopwatch times the climb.',
      given: function () { return ['Mass of the runner on the weighing machine: m = ' + fx(p.m, 1) + ' kg.', 'Height of one real step: ' + fx(p.hs * 100, 0) + ' cm.', 'g = ' + fx(p.g, 1) + ' m/s².']; },
      build: function () {
        var st2 = grp(SX, 0, BZ), cm = mat(0xb9b2a4, 0.9);
        for (var i = 0; i < N; i++) box(st2, RUN, RISE * (i + 1), 0.16, cm, RUN * (i + 0.5), RISE * (i + 1) / 2, 0);
        S.contact(1.0, 0.24, SX + 0.45, BZ, 0.45);
        man = grp(0, 0, BZ); var bm = mat(0x2c5fb4, 0.7); add(man, S.mesh(new T.CapsuleGeometry(0.012, 0.03, 6, 12), bm), 0, 0.04, 0); sph(man, 0.011, mat(0xd9a36b, 0.8), 0, 0.075, 0);
        cyl(man, 0.005, 0.005, 0.025, mat(0x22252b), -0.006, 0.0125, 0, 8); cyl(man, 0.005, 0.005, 0.025, mat(0x22252b), 0.006, 0.0125, 0, 8);
        sw = S.stopwatch([0.62, 0.035, BZ + 0.2], [-1.2, -0.3, 0]); lc = lcd(0.38, BZ + 0.2, 'WEIGHING MACHINE  kg', 0.15); lc.set(fx(p.m, 1));
        S.addApparatus('stairs', st2, 'Model staircase', 'Twenty steps. In the real activity each step is about 17 cm high.');
        S.addApparatus('runner', man, 'Runner (simulated)', 'A simulated runner with a fixed, hidden power.');
        S.addApparatus('sw', sw.group, 'Stopwatch', 'Times the climb from the first step to the last.');
        S.addApparatus('scale', lc.group, 'Weighing machine', 'Shows the mass of the runner.');
        return { handAt: function () { return new T.Vector3(0.62, 0.08, BZ + 0.2); },
          update: function (c, r, k, done) { var s = Math.floor(k * c.set.n + 1e-6), i = Math.min(c.set.n, s);
            man.position.set(SX + RUN * (i === 0 ? -0.5 : i - 0.5), i * RISE, BZ); sw.t = r.t * k; sw.on = false; } };
      },
      conds: [10, 20].map(function (n) { return { label: 'Climb ' + n + ' steps', set: { n: n } }; }),
      read: function (q) { var v = K.view({ t: 0 }, q); return { n: q.n, H: v.H, t: Math.round(v.tclimb * 100) / 100, W: v.work, P: v.work / (Math.round(v.tclimb * 100) / 100) }; },
      runLabel: 'Start the climb and the stopwatch', dur: 2.6, hudLabel: 'Time of the climb',
      runText: 'Start the stopwatch as the runner leaves the ground and stop it on the last step. Time a climb of 10 steps and one of 20.',
      live: function (r, done) { return done ? fx(r.n, 0) + ' steps (' + fx(r.H, 2) + ' m) climbed in ' + fx(r.t, 2) + ' s.' : 'The runner is waiting at the foot of the stairs.'; },
      hud: function (r) { return fx(r.t, 2) + ' s'; },
      cols: [['Steps', function (r) { return fx(r.n, 0); }], ['H (m)', function (r) { return fx(r.H, 2); }], ['m g H (J)', function (r) { return fx(r.W, 0); }], ['t (s)', function (r) { return fx(r.t, 2); }], ['P (W)', function (r) { return fx(r.P, 0); }]],
      theory: { formula: 'P = m g H / t' },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.P; })); if (!isFinite(m)) return null;
        return { label: 'Power of the runner', value: m, unit: 'W', digits: 0, truth: p.P, note: 'Simulated runner. One horsepower is 746 W: a person can manage a fraction of that for a few seconds.' }; },
    };
  })();

  // ------------------------------------------------------------------------------------------ a pendulum dying away
  LABS['sw7-pendulum-dissipation'] = (function () {
    var bob, str, PX = 0.11, PY, sw, th0 = p.th0 * 180 / Math.PI, pro;
    return {
      intro: 'A brass bob hangs on a thread 1 m long from a split cork in a clamp. A protractor behind the thread reads the amplitude of the swing, and a stopwatch runs from the moment of release.',
      given: function () { return ['Starting amplitude: ' + fx(th0, 1) + '°.']; },
      build: function () {
        PY = p.L + 0.12; var stand = S.stand({ x: 0.1, z: BZ, h: PY + 0.1, armY: PY, armLen: 0.2 });
        S.cork(new T.Vector3(PX, PY, BZ));
        pro = S.mesh(new T.CircleGeometry(0.16, 40, Math.PI * 1.25, Math.PI * 0.5), new T.MeshStandardMaterial({ side: T.DoubleSide, roughness: 0.8, map: S.canvasTex(512, 512, function (c, w, h) {
          c.fillStyle = '#f4efe0'; c.fillRect(0, 0, w, h); c.strokeStyle = '#222'; c.fillStyle = '#222'; c.font = '600 20px sans-serif'; c.textAlign = 'center';
          for (var a = -40; a <= 40; a += 5) { var t = (a - 90) * Math.PI / 180, big = a % 10 === 0; c.lineWidth = big ? 3 : 1.5; c.beginPath(); c.moveTo(w / 2 + Math.cos(t) * 200, h / 2 - Math.sin(t) * 200); c.lineTo(w / 2 + Math.cos(t) * (big ? 232 : 220), h / 2 - Math.sin(t) * (big ? 232 : 220)); c.stroke();
            if (big) c.fillText(String(Math.abs(a)), w / 2 + Math.cos(t) * 180, h / 2 - Math.sin(t) * 180 + 7); } }) }));
        add(S.scene, pro, PX, PY, BZ - 0.012);
        bob = sph(S.scene, 0.02, M.brass, 0, 0, 0); str = thread();
        sw = S.stopwatch([0.6, 0.035, BZ + 0.2], [-1.2, -0.3, 0]);
        S.addApparatus('stand', stand, 'Stand, clamp and cork', 'The thread is gripped in a split cork so that the point of suspension does not move.');
        S.addApparatus('bob', bob, 'Pendulum bob', 'A brass bob. Air resistance on it and on the thread slowly takes its energy.');
        S.addApparatus('pro', pro, 'Protractor', 'Reads the angle of the thread at the end of a swing.');
        S.addApparatus('sw', sw.group, 'Stopwatch', 'Runs from the moment the bob is released.');
        return { handAt: function () { return new T.Vector3(PX + p.L * Math.sin(p.th0), PY - p.L * Math.cos(p.th0) + 0.05, BZ); },
          update: function (c, r, k, done) {
            var A = (th0 + (r.A - th0) * k) * Math.PI / 180, th = done ? r.A * Math.PI / 180 : A * Math.cos(k * Math.PI * 2 * Math.min(8, c.set.n / 5));
            bob.position.set(PX + p.L * Math.sin(th), PY - p.L * Math.cos(th), BZ); str.set([[PX, PY, BZ], [bob.position.x, bob.position.y, BZ]]); sw.t = r.t * k; sw.on = false;
          } };
      },
      conds: [10, 20, 30, 40].map(function (n) { return { label: 'After ' + n + ' swings', set: { n: n } }; }),
      read: function (q, c) { var a = K.ampAfter(p, c.set.n), A = a[0] * 180 / Math.PI; return { n: c.set.n, A: A, t: a[1], gam: Math.log(th0 / A) / a[1] }; },
      runLabel: 'Release from 15° and let it swing', dur: 3.0, hudLabel: 'Amplitude now',
      runText: 'Release the bob from 15° and count the swings. At the chosen count, read the amplitude on the protractor and the time on the stopwatch.',
      live: function (r, done) { return done ? 'After ' + r.n + ' swings (' + fx(r.t, 1) + ' s) the amplitude is ' + fx(r.A, 2) + '°.' : 'The bob is held at ' + fx(th0, 1) + '°.'; },
      hud: function (r) { return fx(r.A, 2) + '°'; },
      cols: [['Swings', function (r) { return String(r.n); }], ['t (s)', function (r) { return fx(r.t, 1); }], ['Amplitude (°)', function (r) { return fx(r.A, 2); }], ['ln(A₀/A) / t (1/s)', function (r) { return fx(r.gam, 4); }]],
      theory: { formula: 'A = A₀ e^(−γ t)', note: 'γ = ln(A₀ / A) / t' },
      graph: { x: function (r) { return r.t; }, y: function (r) { return r.A; }, xlabel: 't (s)', ylabel: 'amplitude (°)', x0: 0, y0: 0,
        line: function (pts) { var g = mean(pts.map(function (q) { return Math.log(th0 / q[1]) / q[0]; })); return function (t) { return th0 * Math.exp(-g * t); }; } },
      result: function (rows) { var m = mean(rows.map(function (r) { return r.gam; })); if (!isFinite(m)) return null;
        return { label: 'Decay constant γ', value: m, unit: '1/s', digits: 4, truth: p.b / 2, note: 'The amplitude falls by the same fraction in equal times; the energy, which goes as A², falls twice as fast.' }; },
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
