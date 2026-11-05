/* Prayogshala studio module: NETWORK THEOREMS TRAINER PANEL (B.Sc. electricity laboratory).
   One laminate panel with the network silk-screened on it, real carbon-film resistors soldered along the printed
   branches, a brass test point at every node and a removable brass link in every branch so that the ammeter can
   be put into it. Two bench supplies feed the panel, a three-dial decade box is the load, and a digital
   multimeter on its own leads reads volts or amperes. Four experiments run on this one board - Kirchhoff's laws,
   Thevenin and Norton, superposition and maximum power transfer - and every reading comes from the shared
   `circuit` kernel (kernels.js, modified nodal analysis) on the lab's own netlist, which is the same code the
   server checks against the textbook formulas in packs/em_ug.py. */
HoolaStudio.define('network-board', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.circuit, CFG = S.lab.cfg;
  var p = HK.paramsFor('circuit', S.lab.params);
  var MODE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var OPEN = 1e9, SHORT = 1e-6;

  var st = { traced: false, E1: p.E1, E2: p.E2, RL: p.RL, load: 'in', link: null, probe: null, dmm: 'V',
    probeI: null };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }

  /* ---------------------------------------------------------------- the panel and its printed network */
  var PZ = -0.30, PW = 0.80, PD = 0.33, PY = 0.018;
  function W(u, v) { return new T.Vector3(u, PY, PZ - v); }          // printed (u, v) -> world
  var RAIL = 0.100, EARTH = -0.112;
  var LAY = {                                                         // where every printed part sits
    v1: [-0.33, 0], v2: [0.33, 0],
    r1: [-0.235, RAIL], r2: [0.235, RAIL], r3: [-0.095, 0.01], r4: [0.095, 0.035],
    k1: [-0.135, RAIL], k2: [0.135, RAIL], k3: [-0.095, 0.072], k4: [0.095, 0.078],
    tp1: [-0.33, RAIL], tp2: [0.0, RAIL], tp3: [0.33, RAIL], tp4: [0.095, -0.035], tp0: [-0.01, EARTH]
  };
  var VALS = { R1: p.R1, R2: p.R2, R3: p.R3, R4: p.R4 };

  var panelTex = S.canvasTex(2048, Math.round(2048 * PD / PW), function (c, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PD) * h; }, k = w / PW;
    c.fillStyle = '#17352f'; c.fillRect(0, 0, w, h);
    for (var i = 0; i < 2600; i++) { c.fillStyle = 'rgba(255,255,255,' + (0.012 + (i % 7) * 0.004) + ')'; c.fillRect((i * 97) % w, (i * 61) % h, 2, 2); }
    c.strokeStyle = '#e9efe6'; c.lineCap = 'round'; c.lineJoin = 'round';
    function line() { c.lineWidth = 0.0045 * k; c.beginPath(); c.moveTo(X(arguments[0][0]), Y(arguments[0][1]));
      for (var j = 1; j < arguments.length; j++) c.lineTo(X(arguments[j][0]), Y(arguments[j][1])); c.stroke(); }
    function gapH(u, v, half) { line([u - half - 0.055, v], [u - half, v]); line([u + half, v], [u + half + 0.055, v]); }
    // rails
    line([-0.33, RAIL], [-0.29, RAIL]); line([-0.18, RAIL], [0.18, RAIL]); line([0.29, RAIL], [0.33, RAIL]);
    line([-0.345, EARTH], [0.345, EARTH]);
    // supply branches (battery symbols)
    line([-0.33, RAIL], [-0.33, 0.045]); line([-0.33, -0.045], [-0.33, EARTH]);
    line([0.33, RAIL], [0.33, 0.045]); line([0.33, -0.045], [0.33, EARTH]);
    [-0.33, 0.33].forEach(function (u) {
      [[0.022, 0.030], [-0.004, 0.016], [-0.030, 0.030], [-0.056 + 0.0, 0.016]].forEach(function (b, bi) {
        c.lineWidth = (bi % 2 ? 0.010 : 0.004) * k; c.beginPath();
        c.moveTo(X(u - b[1]), Y(b[0])); c.lineTo(X(u + b[1]), Y(b[0])); c.stroke(); });
    });
    // resistor outlines on the four branches
    gapH(LAY.r1[0], RAIL, 0.030); gapH(LAY.r2[0], RAIL, 0.030);
    line([LAY.r3[0], RAIL], [LAY.r3[0], LAY.r3[1] + 0.030]); line([LAY.r3[0], LAY.r3[1] - 0.030], [LAY.r3[0], EARTH]);
    line([LAY.r4[0], RAIL], [LAY.r4[0], LAY.r4[1] + 0.028]); line([LAY.r4[0], LAY.r4[1] - 0.028], [LAY.r4[0], -0.035]);
    line([LAY.tp4[0], -0.035], [0.175, -0.035]); line([0.175, -0.035], [0.175, -0.075]);
    line([0.245, -0.075], [0.245, EARTH]);
    c.lineWidth = 0.0035 * k; c.strokeStyle = '#9fd3c2';
    c.setLineDash([0.012 * k, 0.010 * k]); c.beginPath();
    c.rect(X(0.145), Y(-0.050), X(0.275) - X(0.145), Y(-0.100) - Y(-0.050)); c.stroke(); c.setLineDash([]);
    c.strokeStyle = '#e9efe6';
    // lettering
    c.fillStyle = '#e9efe6'; c.textAlign = 'center';
    function text(t, u, v, px, col) { c.fillStyle = col || '#e9efe6'; c.font = '700 ' + Math.round(px * k) + 'px "Public Sans", sans-serif';
      c.fillText(t, X(u), Y(v)); }
    text('NETWORK THEOREMS TRAINER', 0, 0.145, 0.0145, '#8fd0bb');
    text('E1', -0.33, 0.062, 0.016); text('E2', 0.33, 0.062, 0.016);
    text('R1', LAY.r1[0], RAIL + 0.030, 0.015); text('R2', LAY.r2[0], RAIL + 0.030, 0.015);
    text('R3', LAY.r3[0] - 0.035, LAY.r3[1] + 0.006, 0.015); text('R4', LAY.r4[0] + 0.036, LAY.r4[1] + 0.004, 0.015);
    text('RL  LOAD', 0.210, -0.062, 0.013, '#9fd3c2');
    text('A', LAY.k1[0], RAIL + 0.028, 0.012, '#9fd3c2'); text('B', LAY.k2[0], RAIL + 0.028, 0.012, '#9fd3c2');
    text('C', LAY.k3[0] + 0.030, LAY.k3[1], 0.012, '#9fd3c2'); text('D', LAY.k4[0] + 0.030, LAY.k4[1], 0.012, '#9fd3c2');
    text('1', LAY.tp1[0] - 0.026, RAIL - 0.008, 0.013, '#9fd3c2');
    text('2', LAY.tp2[0] + 0.024, RAIL - 0.008, 0.013, '#9fd3c2');
    text('3', LAY.tp3[0] + 0.026, RAIL - 0.008, 0.013, '#9fd3c2');
    text('4', LAY.tp4[0] - 0.026, LAY.tp4[1] - 0.004, 0.013, '#9fd3c2');
    text('EARTH  0', -0.145, EARTH + 0.016, 0.012, '#9fd3c2');
    text('LINKS A-D: TAKE ONE OUT AND PLUG THE AMMETER IN', 0, -0.142, 0.0105, '#7fb6a4');
  });
  var panel = new T.Group(); S.scene.add(panel);
  var slab = S.rounded(PW, PD, 0.016, 0.004, M.bakelite); slab.rotation.x = -Math.PI / 2; slab.position.set(0, 0.008, PZ); panel.add(slab);
  var face = new T.Mesh(new T.PlaneGeometry(PW - 0.004, PD - 0.004), new T.MeshStandardMaterial({ map: panelTex, roughness: 0.42 }));
  face.rotation.x = -Math.PI / 2; face.position.set(0, 0.0165, PZ); panel.add(face);
  [[-0.37, -0.44], [0.37, -0.44], [-0.37, -0.16], [0.37, -0.16]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 14), M.rubber); ft.position.set(f[0], 0.002, f[1]); panel.add(ft); });
  S.contact(PW + 0.12, PD + 0.12, 0, PZ, 0.55);

  /* ---------------------------------------------------------------- real resistors with colour bands */
  var BAND = ['#121214', '#6b3a10', '#c0392b', '#e07820', '#e8c34a', '#2e9b5a', '#2c5fb4', '#8e5aa8', '#9aa0a6', '#f4f4f0'];
  function bands(ohms) {
    var v = Math.max(1, Math.round(ohms)), e = 0;
    while (v >= 100) { v = Math.round(v / 10); e++; }
    if (v < 10) { v = v * 10; e--; }
    return [BAND[Math.floor(v / 10)], BAND[v % 10], BAND[Math.max(0, e)]];
  }
  function resistor(u, v, vertical, ohms, name) {
    var g = new T.Group(); S.scene.add(g);
    var at = W(u, v); g.position.copy(at);
    if (!vertical) g.rotation.y = Math.PI / 2;
    var body = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, 0.030, 20), new T.MeshStandardMaterial({ color: 0xd8c6a0, roughness: 0.55 }));
    body.rotation.x = Math.PI / 2; body.position.y = 0.010; g.add(body);
    [-1, 1].forEach(function (s) {
      var sh = S.mesh(new T.CylinderGeometry(0.0046, 0.0062, 0.005, 18), new T.MeshStandardMaterial({ color: 0xcdb891, roughness: 0.6 }));
      sh.rotation.x = Math.PI / 2; sh.position.set(0, 0.010, s * 0.0175); g.add(sh);
      var ld = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.020, 8), M.chrome);
      ld.rotation.x = Math.PI / 2; ld.position.set(0, 0.010, s * 0.028); g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.010, 8), M.chrome);
      dn.position.set(0, 0.005, s * 0.0375); g.add(dn);
    });
    bands(ohms).concat(['#c9a227']).forEach(function (col, i) {
      var b = S.mesh(new T.CylinderGeometry(0.0064, 0.0064, 0.0026, 18), new T.MeshStandardMaterial({ color: new T.Color(col), roughness: 0.5 }));
      b.rotation.x = Math.PI / 2; b.position.set(0, 0.010, -0.011 + i * 0.0062 + (i === 3 ? 0.004 : 0)); g.add(b);
    });
    S.addApparatus(name, g, 'Resistor ' + name.toUpperCase(), 'A carbon-film resistor soldered on the printed branch. Its colour bands give its value, which is what the experiment is to find.');
    return g;
  }
  var res = {
    R1: resistor(LAY.r1[0], LAY.r1[1], false, VALS.R1, 'r1'),
    R2: resistor(LAY.r2[0], LAY.r2[1], false, VALS.R2, 'r2'),
    R3: resistor(LAY.r3[0], LAY.r3[1], true, VALS.R3, 'r3'),
    R4: resistor(LAY.r4[0], LAY.r4[1], true, VALS.R4, 'r4')
  };

  /* ---------------------------------------------------------------- test points and branch links */
  function socket(u, v) {
    var g = new T.Group(); S.scene.add(g); g.position.copy(W(u, v));
    var ring = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, 0.004, 18), M.brass); ring.position.y = 0.002; g.add(ring);
    var hole = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.005, 14), M.black, false); hole.position.y = 0.0032; g.add(hole);
    return { g: g, at: W(u, v).add(new T.Vector3(0, 0.006, 0)) };
  }
  var TP = {};
  ['tp1', 'tp2', 'tp3', 'tp4', 'tp0'].forEach(function (k) { TP[k] = socket(LAY[k][0], LAY[k][1]); });
  var LINK = {};
  [['R1', 'k1', false], ['R2', 'k2', false], ['R3', 'k3', true], ['R4', 'k4', true]].forEach(function (q) {
    var u = LAY[q[1]][0], v = LAY[q[1]][1], d = 0.014;
    var a = socket(q[2] ? u : u - d, q[2] ? v + d : v), b = socket(q[2] ? u : u + d, q[2] ? v - d : v);
    var bar = new T.Group(); S.scene.add(bar);
    var bb = S.mesh(new T.BoxGeometry(q[2] ? 0.005 : 0.030, 0.0035, q[2] ? 0.030 : 0.005), M.brass);
    bb.position.y = 0.0075; bar.add(bb);
    var kn = S.mesh(new T.CylinderGeometry(0.0038, 0.0038, 0.006, 14), M.blackPlastic); kn.position.y = 0.0115; bar.add(kn);
    bar.position.copy(W(u, v));
    LINK[q[0]] = { a: a, b: b, bar: bar, home: bar.position.clone(), on: true,
      head: W(u, v).add(new T.Vector3(0, 0.015, 0)) };
  });
  function setLink(name, on) {
    var L = LINK[name];
    L.on = on;
    L.bar.position.copy(on ? L.home : L.home.clone().add(new T.Vector3(0, 0.055, 0.075)));
    L.bar.rotation.x = on ? 0 : 0.9;
  }

  /* ---------------------------------------------------------------- the two bench supplies */
  function supply(x, text) {
    var box = S.powerBox([x, 0, -0.60], text);
    var lcd = S.liveTex(400, 160), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(0.058, 0.023), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.position.set(0, 0.092, -0.56); scr.rotation.x = -Math.PI / 2 - 0.0; S.scene.add(scr);
    scr.position.x = x;
    var bez = S.mesh(new T.BoxGeometry(0.066, 0.003, 0.03), M.grey); bez.position.set(x, 0.0905, -0.56); S.scene.add(bez);
    return { group: box, knob: box.userData.knob, plus: box.userData.plus, minus: box.userData.minus,
      show: function (v) { var t = v.toFixed(1); if (t === last) return; last = t;
        lcd.draw(function (c, w, h) { c.fillStyle = '#0c1410'; c.fillRect(0, 0, w, h);
          c.fillStyle = '#5ef0a8'; c.font = '700 96px "JetBrains Mono", monospace'; c.textAlign = 'right';
          c.fillText(t, w - 90, 112); c.font = '600 44px "Public Sans", sans-serif'; c.fillText('V', w - 16, 112); }); } };
  }
  var sup1 = supply(-0.52, 'BENCH SUPPLY  E1'), sup2 = supply(0.52, 'BENCH SUPPLY  E2');

  /* ---------------------------------------------------------------- the decade load box */
  function decade(x, z, muls, title) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var n = muls.length, BW = 0.05 + n * 0.052, BD = 0.11, BH = 0.046;
    var body = S.rounded(BW, BD, BH, 0.005, M.darkWood); body.rotation.x = -Math.PI / 2; body.position.y = BH / 2; g.add(body);
    var dx = muls.map(function (m, i) { return -(n - 1) * 0.052 / 2 + i * 0.052; });
    var PWn = BW - 0.007, PDn = BD - 0.007;
    var tex = S.canvasTex(1200, Math.round(1200 * PDn / PWn), function (c, w, h) {
      var X = function (u) { return (u / PWn + 0.5) * w; }, Y = function (v) { return (v / PDn + 0.5) * h; }, k = w / PWn;
      c.fillStyle = '#191c21'; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 3; c.strokeRect(9, 9, w - 18, h - 18);
      c.fillStyle = '#eceadf'; c.font = '700 ' + Math.round(k * 0.0085) + 'px "Public Sans", sans-serif'; c.textAlign = 'left';
      c.fillText(title, 22, Math.round(k * 0.013));
      muls.forEach(function (m, i) {
        var cx = X(dx[i]), cy = Y(0.004), R = 0.024 * k;
        c.strokeStyle = '#8b9099'; c.lineWidth = 2; c.beginPath(); c.arc(cx, cy, R * 0.72, 0, Math.PI * 2); c.stroke();
        c.textAlign = 'center'; c.fillStyle = '#eceadf'; c.font = '600 ' + Math.round(k * 0.0068) + 'px "Public Sans", sans-serif';
        for (var d = 0; d < 10; d++) { var a = d * Math.PI / 5; c.fillText(String(d), cx + Math.sin(a) * R, cy + Math.cos(a) * R + k * 0.0024); }
        c.fillStyle = '#f0c36b'; c.font = '700 ' + Math.round(k * 0.0066) + 'px "Public Sans", sans-serif';
        c.fillText('x ' + m, cx, Y(-0.042));
      });
    });
    var pan = new T.Mesh(new T.PlaneGeometry(PWn, PDn), new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }));
    pan.rotation.x = -Math.PI / 2; pan.position.y = BH + 0.0006; g.add(pan);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#15161a'; c.fillRect(0, 0, w, h); c.fillStyle = '#3b3e45'; for (var i = 0; i < w; i += 9) c.fillRect(i, 0, 3, h); });
    var dials = muls.map(function (m, i) {
      var d = new T.Group(); d.position.set(dx[i], BH + 0.001, 0.004); g.add(d);
      var kb = S.mesh(new T.CylinderGeometry(0.0155, 0.017, 0.012, 32), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 })); kb.position.y = 0.006; d.add(kb);
      var cap = S.mesh(new T.CylinderGeometry(0.0118, 0.0118, 0.0015, 32), M.chrome); cap.position.y = 0.0128; d.add(cap);
      var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.0012, 0.014), M.white, false); ptr.position.set(0, 0.0136, 0.008); d.add(ptr);
      return { g: d, mul: m, digit: 0, top: new T.Vector3(x + dx[i], BH + 0.015, z + 0.004) };
    });
    var tA = socket(0, 0), tB = socket(0, 0);
    tA.g.position.set(x - BW / 2 + 0.013, 0, z - BD / 2 + 0.011); tA.at = tA.g.position.clone().add(new T.Vector3(0, 0.006, 0));
    tB.g.position.set(x + BW / 2 - 0.013, 0, z - BD / 2 + 0.011); tB.at = tB.g.position.clone().add(new T.Vector3(0, 0.006, 0));
    S.contact(BW + 0.06, BD + 0.06, x, z, 0.5);
    return { group: g, dials: dials, tA: tA, tB: tB, muls: muls,
      value: function () { var v = 0; dials.forEach(function (d) { v += d.digit * d.mul; }); return v; },
      max: function () { var v = 0; dials.forEach(function (d) { v += 9 * d.mul; }); return v; },
      look: function () { dials.forEach(function (d) { d.g.rotation.y = d.digit * Math.PI / 5; }); } };
  }
  var loadBox = decade(0.34, 0.06, [100, 10, 1], 'DECADE LOAD BOX  RL');
  (function () { var want = [], left = Math.round(st.RL);
    loadBox.muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); want.push(d); left -= d * m; });
    loadBox.dials.forEach(function (d, i) { d.digit = want[i]; }); loadBox.look(); })();

  /* ---------------------------------------------------------------- the digital multimeter */
  var dmm = (function () {
    var g = new T.Group(); S.scene.add(g); g.position.set(-0.22, 0, 0.06); g.rotation.y = 0.16;
    var MW = 0.115, MD = 0.155, MH = 0.034;
    var body = S.rounded(MW, MD, MH, 0.008, new T.MeshStandardMaterial({ color: 0xe0a93c, roughness: 0.55 }));
    body.rotation.x = -Math.PI / 2; body.position.y = MH / 2; g.add(body);
    var fp = S.mesh(new T.BoxGeometry(MW - 0.01, 0.002, MD - 0.01), M.bakelite); fp.position.y = MH + 0.001; g.add(fp);
    var lcd = S.liveTex(560, 240), last = '';
    var scr = new T.Mesh(new T.PlaneGeometry(MW - 0.026, 0.036), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.rotation.x = -Math.PI / 2; scr.position.set(0, MH + 0.0026, -MD / 2 + 0.032); g.add(scr);
    var bez = S.mesh(new T.BoxGeometry(MW - 0.02, 0.003, 0.042), M.grey); bez.position.set(0, MH + 0.0015, -MD / 2 + 0.032); g.add(bez);
    var sel = new T.Group(); sel.position.set(0, MH + 0.004, 0.012); g.add(sel);
    sel.add(S.mesh(new T.CylinderGeometry(0.0165, 0.0175, 0.008, 28), M.blackPlastic));
    var sp = S.mesh(new T.BoxGeometry(0.003, 0.002, 0.015), M.white, false); sp.position.set(0, 0.005, -0.009); sel.add(sp);
    var jacks = [-0.026, 0.026].map(function (sx) {
      var j = S.mesh(new T.CylinderGeometry(0.0048, 0.0048, 0.004, 16), sx < 0 ? M.blackPlastic : M.red);
      j.position.set(sx, MH + 0.001, MD / 2 - 0.016); g.add(j); return j; });
    S.contact(MW + 0.07, MD + 0.07, -0.22, 0.06, 0.5);
    return { group: g, sel: sel, redJack: wpt(g, 0.026, MH + 0.006, MD / 2 - 0.016), blackJack: wpt(g, -0.026, MH + 0.006, MD / 2 - 0.016),
      show: function (txt, sub, unit) { var key = txt + '|' + sub + '|' + unit; if (key === last) return; last = key;
        lcd.draw(function (c, w, h) { var gr = c.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#bcc4a7'); gr.addColorStop(1, '#9fab8c');
          c.fillStyle = gr; c.fillRect(0, 0, w, h);
          c.font = '700 110px "JetBrains Mono", monospace'; c.textAlign = 'right';
          c.fillStyle = 'rgba(0,0,0,.07)'; c.fillText('8.8.8.8', 452, 138);
          c.fillStyle = '#1b2116'; c.fillText(txt, 452, 138);
          c.font = '600 42px "Public Sans", sans-serif'; c.fillText(unit, 540, 138);
          c.textAlign = 'left'; c.font = '600 36px "Public Sans", sans-serif'; c.fillText(sub, 20, 214); }); } };
  })();

  /* ---------------------------------------------------------------- leads */
  function lead(a, b, color, via, lift) {
    var up = lift === undefined ? 0.018 : lift, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.004, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color);
    if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; }
    return w;
  }
  lead(sup1.plus.position.clone().add(new T.Vector3(0, 0.012, 0)), TP.tp1.at, 'red', [[-0.46, -0.52]]);
  lead(sup1.minus.position.clone().add(new T.Vector3(0, 0.012, 0)), W(-0.345, EARTH).add(new T.Vector3(0, 0.006, 0)), 'black', [[-0.58, -0.46], [-0.42, -0.2]]);
  lead(sup2.plus.position.clone().add(new T.Vector3(0, 0.012, 0)), TP.tp3.at, 'red', [[0.46, -0.52]]);
  lead(sup2.minus.position.clone().add(new T.Vector3(0, 0.012, 0)), W(0.345, EARTH).add(new T.Vector3(0, 0.006, 0)), 'black', [[0.58, -0.46], [0.42, -0.2]]);
  var loadLeadA = lead(W(0.175, -0.075).add(new T.Vector3(0, 0.006, 0)), loadBox.tA.at, '#d9a520', [[0.22, -0.26]]);
  var loadLeadB = lead(W(0.245, -0.075).add(new T.Vector3(0, 0.006, 0)), loadBox.tB.at, 'black', [[0.33, -0.24]]);
  socket(0.175, -0.075); socket(0.245, -0.075);

  /* the two probe leads: their tips are moved by the hand */
  var redTip = TP.tp0.at.clone(), blackTip = TP.tp0.at.clone();
  var redLead = null, blackLead = null;
  function probeMesh(color) {
    var g = new T.Group(); S.scene.add(g);
    var body = S.mesh(new T.CylinderGeometry(0.0045, 0.0055, 0.055, 16), color === 'red' ? M.red : M.blackPlastic);
    body.position.y = 0.038; g.add(body);
    var tip = S.mesh(new T.CylinderGeometry(0.0007, 0.0022, 0.022, 12), M.chrome); tip.position.y = 0.0105; g.add(tip);
    return g;
  }
  var redProbe = probeMesh('red'), blackProbe = probeMesh('black');
  function placeProbes() {
    redProbe.position.copy(redTip); blackProbe.position.copy(blackTip);
    var rp = [[redTip.x, redTip.y + 0.09, redTip.z], [redTip.x - 0.02, 0.14, redTip.z + 0.14],
      [dmm.redJack.x + 0.02, 0.09, dmm.redJack.z - 0.05], [dmm.redJack.x, dmm.redJack.y, dmm.redJack.z]];
    var bp = [[blackTip.x, blackTip.y + 0.09, blackTip.z], [blackTip.x - 0.03, 0.13, blackTip.z + 0.16],
      [dmm.blackJack.x - 0.02, 0.09, dmm.blackJack.z - 0.05], [dmm.blackJack.x, dmm.blackJack.y, dmm.blackJack.z]];
    if (!redLead) { redLead = S.wire(rp, 'red'); blackLead = S.wire(bp, 'black'); blackLead.material.color.setHex(0x111113); }
    else { redLead.set(rp); blackLead.set(bp); }
  }
  placeProbes();

  S.addApparatus('panel', panel, 'Network theorems trainer panel',
    'The network is printed on the panel: two supplies feed the junction through R₁ and R₂, R₃ goes to the earth rail and R₄ feeds the load terminals. Brass test points 1, 2, 3, 4 and 0 are the nodes; links A to D sit in the four branches.');
  S.addApparatus('dmm', dmm.group, 'Digital multimeter',
    'On its own probe leads. In the volts setting it is put across two test points; in the amperes setting it goes into a branch in place of its link.');
  S.addApparatus('load', loadBox.group, 'Decade load box R_L', 'Three dials: hundreds, tens and units of ohms. It is the load on the network.');
  S.addApparatus('sup1', sup1.group, 'Bench supply E₁', 'A regulated direct-voltage supply. Its own resistance is a few milliohms, so turning it down to zero is the same as replacing it by a link.');
  S.addApparatus('sup2', sup2.group, 'Bench supply E₂', 'The second source in the network, set independently of the first.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  /* ---------------------------------------------------------------- physics: every number from the kernel */
  function rlNow() { return st.load === 'out' ? OPEN : st.load === 'short' ? SHORT : Math.max(loadBox.value(), 1e-6); }
  function solve(over) {
    var q = HK.assign(p, { E1: st.E1, E2: st.E2, RL: rlNow() });
    if (over) q = HK.assign(q, over);
    return KC.view(KC.init(q, CFG), q, CFG);
  }
  function nodeV(key) { return solve()[{ tp1: 'N_1', tp2: 'N_2', tp3: 'N_3', tp4: 'N_4', tp0: 'N_0' }[key]]; }
  function branchI(name) { return solve()['I_' + name]; }
  function trueRth() { return p.R4 + 1 / (1 / p.R1 + 1 / p.R2 + 1 / p.R3); }
  function trueVoc() {
    var q = HK.assign(p, { E1: st.E1, E2: st.E2, RL: OPEN });
    return KC.view(KC.init(q, CFG), q, CFG).V_RL;
  }
  function trueIL(rl, e1, e2) {
    var q = HK.assign(p, { E1: e1 === undefined ? st.E1 : e1, E2: e2 === undefined ? st.E2 : e2, RL: rl });
    return KC.view(KC.init(q, CFG), q, CFG).I_RL;
  }
  function reading() {
    if (st.dmm === 'A') { return st.probeI ? branchI(st.probeI) : (st.load === 'short' ? solve().I_RL : null); }
    return st.probe ? nodeV(st.probe) - nodeV('tp0') : null;
  }
  function readText() {
    var v = reading();
    if (v === null) return ['- - - -', 'probes not on the circuit', ''];
    if (st.dmm === 'A') return [(v * 1000).toFixed(1), st.probeI ? 'branch ' + st.probeI : 'load terminals', 'mA'];
    return [v.toFixed(3), 'test point ' + st.probe.slice(2) + ' to earth', 'V'];
  }
  var hudA = S.hudCard('Multimeter'), hudB = S.hudCard('Load box'), hudC = S.hudCard('Supplies');

  /* ---------------------------------------------------------------- human actions */
  function trace() {
    st.traced = true; S.focus('panel');
    S.say('Follow the printed network: E₁ through R₁ and E₂ through R₂ both reach test point 2, the junction. R₃ goes from there to the earth rail, and R₄ carries on to the load terminals where the decade box is plugged in.');
    S.render();
  }
  function setSupply(which, volts) {
    if (busy()) return Promise.resolve(false);
    if (!(volts >= 0 && volts <= 15)) { S.say('The bench supplies are used between 0 and 15 V only.'); return Promise.resolve(false); }
    var s = which === 1 ? sup1 : sup2;
    var from = which === 1 ? st.E1 : st.E2, to = Math.round(volts * 2) / 2;
    return S.hand.pinchMove(s.knob.getWorldPosition(new T.Vector3()), function () { return s.knob.getWorldPosition(new T.Vector3()); },
      function (k) { var v = from + (to - from) * k; if (which === 1) st.E1 = v; else st.E2 = v; }, { mode: 'front', ms: 620, reachMs: 640 })
      .then(function () { if (which === 1) st.E1 = to; else st.E2 = to;
        S.say('Supply E' + which + ' set to ' + to.toFixed(1) + ' V.'); S.render(); return true; });
  }
  function setLoad(ohms) {
    if (busy()) return Promise.resolve(false);
    if (!(ohms >= 1 && ohms <= loadBox.max())) { S.say('The load box goes from 1 to ' + loadBox.max() + ' ohms.'); return Promise.resolve(false); }
    var left = Math.round(ohms), want = [];
    loadBox.muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); want.push(d); left -= d * m; });
    var jobs = [];
    want.forEach(function (d, i) { if (loadBox.dials[i].digit !== d) jobs.push([i, d]); });
    return jobs.reduce(function (pr, j) {
      return pr.then(function () {
        var dl = loadBox.dials[j[0]], a = dl.digit, b = j[1];
        return S.hand.pinchMove(dl.top, function () { return dl.top; }, function (k) { dl.digit = a + (b - a) * k; loadBox.look(); },
          { mode: 'top', ms: 380 + 50 * Math.abs(b - a), reachMs: 480 })
          .then(function () { dl.digit = b; loadBox.look(); S.click(1200, 0.02, 0.05); });
      });
    }, Promise.resolve()).then(function () { st.RL = loadBox.value(); st.load = 'in';
      S.say('Load box set to ' + loadBox.value() + ' ohm.'); S.render(); return true; });
  }
  function moveProbe(which, to) {
    var tip = which === 'red' ? redTip : blackTip, from = tip.clone();
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.045, 0)),
      function (k) { return from.clone().lerp(to, k).add(new T.Vector3(0, 0.045 + 0.04 * Math.sin(Math.PI * k), 0)); },
      function (k) { tip.copy(from.clone().lerp(to, k)); tip.y = from.y + (to.y - from.y) * k + 0.03 * Math.sin(Math.PI * k); placeProbes(); },
      { mode: 'side', ms: 760, reachMs: 560 })
      .then(function () { tip.copy(to); placeProbes(); });
  }
  function putLinksBack() {
    if (!st.probeI) return Promise.resolve();
    var name = st.probeI;
    return moveProbe('red', TP.tp0.at.clone().add(new T.Vector3(0.03, 0.02, 0.05)))
      .then(function () { return S.hand.pinchMove(LINK[name].home.clone().add(new T.Vector3(0, 0.06, 0.08)),
        function () { return LINK[name].home.clone().add(new T.Vector3(0, 0.015, 0)); }, function () {}, { mode: 'top', ms: 520 }); })
      .then(function () { setLink(name, true); st.probeI = null; st.dmm = 'V'; S.click(1500, 0.03, 0.08); S.render(); });
  }
  function probeVolts(key) {
    if (busy()) return Promise.resolve(false);
    return putLinksBack().then(function () {
      st.dmm = 'V';
      return moveProbe('black', TP.tp0.at).then(function () { return moveProbe('red', TP[key].at); });
    }).then(function () { st.probe = key; blackTip.copy(TP.tp0.at); placeProbes();
      S.say('Red probe on test point ' + key.slice(2) + ', black on earth: the meter reads ' + nodeV(key).toFixed(3) + ' V.');
      S.render(); return true; });
  }
  function probeAmps(name) {
    if (busy()) return Promise.resolve(false);
    return putLinksBack().then(function () {
      return S.hand.pinchMove(LINK[name].head, function (k) { return LINK[name].head.clone().add(new T.Vector3(0, 0.05 * k, 0.07 * k)); },
        function (k) { LINK[name].bar.position.copy(LINK[name].home.clone().add(new T.Vector3(0, 0.055 * k, 0.075 * k))); LINK[name].bar.rotation.x = 0.9 * k; },
        { mode: 'top', ms: 620 });
    }).then(function () { setLink(name, false); st.dmm = 'A';
      return moveProbe('black', LINK[name].a.at);
    }).then(function () { return moveProbe('red', LINK[name].b.at); })
      .then(function () { st.probeI = name; st.probe = null;
        S.say('The link is out of branch ' + name + ' and the ammeter is in its place: ' + (branchI(name) * 1000).toFixed(1) + ' mA.');
        S.render(); return true; });
  }
  function setLoadState(mode) {
    if (busy()) return Promise.resolve(false);
    return putLinksBack().then(function () {
      var lift = mode === 'in' ? 0 : 1;
      return S.hand.pinchMove(loadBox.tA.at.clone().add(new T.Vector3(0, 0.03, 0)),
        function (k) { return loadBox.tA.at.clone().add(new T.Vector3(0, 0.03 + 0.05 * k * lift, 0)); }, function () {}, { mode: 'top', ms: 540 });
    }).then(function () {
      st.load = mode;
      loadLeadA.visible = mode !== 'out'; loadLeadB.visible = mode !== 'out';
      S.say(mode === 'in' ? 'The load box is connected across the load terminals.'
        : mode === 'out' ? 'The load lead is off: the load terminals are open, so the meter reads the open-circuit voltage.'
          : 'The ammeter is now straight across the load terminals: this reading is the short-circuit current.');
      if (mode === 'out') { st.dmm = 'V'; st.probe = 'tp4'; redTip.copy(TP.tp4.at); blackTip.copy(TP.tp0.at); placeProbes(); }
      if (mode === 'short') { st.dmm = 'A'; st.probe = null; st.probeI = null; redTip.copy(TP.tp4.at); blackTip.copy(TP.tp0.at); placeProbes(); }
      S.render(); return true;
    });
  }

  /* ---------------------------------------------------------------- recording, per experiment */
  function have(f) { return S.rows.filter(f).length; }
  function rowsOf(f) { return S.rows.filter(f); }
  function mean(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }

  function recordCurrent() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.probeI) { S.say('Put the ammeter into one of the branches first.'); return false; }
    if (S.rows.some(function (r) { return r.what === 'I' + st.probeI.slice(1); })) { S.say('That branch current is already in the table.'); return false; }
    var i = branchI(st.probeI);
    S.addRow({ what: 'I' + st.probeI.slice(1), value: i, unit: 'mA', shown: (i * 1000).toFixed(1) });
    S.say('Written in your record book: the current in branch ' + st.probeI + ' is ' + (i * 1000).toFixed(1) + ' mA.');
    return true;
  }
  function recordVolts(label) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.probe) { S.say('Put the voltmeter probes on two test points first.'); return false; }
    if (S.rows.some(function (r) { return r.what === label; })) { S.say('That reading is already in the table.'); return false; }
    var v = nodeV(st.probe) - nodeV('tp0');
    S.addRow({ what: label, value: v, unit: 'V', shown: v.toFixed(3) });
    S.say('Written in your record book: ' + label + ' = ' + v.toFixed(3) + ' V.');
    return true;
  }
  function recordLoad(kind) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (kind === 'voc') {
      if (st.load !== 'out') { S.say('Take the load lead off first: the open-circuit voltage needs open terminals.'); return false; }
      if (have(function (r) { return r.kind === 'voc'; })) { S.say('The open-circuit voltage is already recorded.'); return false; }
      S.addRow({ kind: 'voc', V: trueVoc(), shown: trueVoc().toFixed(3) + ' V' });
      S.say('Open-circuit voltage recorded: ' + trueVoc().toFixed(3) + ' V.');
      return true;
    }
    if (kind === 'isc') {
      if (st.load !== 'short') { S.say('Put the ammeter straight across the load terminals first.'); return false; }
      if (have(function (r) { return r.kind === 'isc'; })) { S.say('The short-circuit current is already recorded.'); return false; }
      var i = solve().I_RL;
      S.addRow({ kind: 'isc', I: i, shown: (i * 1000).toFixed(2) + ' mA' });
      S.say('Short-circuit current recorded: ' + (i * 1000).toFixed(2) + ' mA.');
      return true;
    }
    if (st.load !== 'in') { S.say('Connect the load box across the terminals first.'); return false; }
    var rl = loadBox.value();
    if (S.rows.some(function (r) { return r.kind === 'load' && r.RL === rl; })) { S.say('There is already a reading at ' + rl + ' ohm.'); return false; }
    var v = solve().V_RL, cur = solve().I_RL;
    S.addRow({ kind: 'load', RL: rl, V: v, I: cur, shown: v.toFixed(3) + ' V' });
    S.say('At ' + rl + ' ohm the load takes ' + v.toFixed(3) + ' V and ' + (cur * 1000).toFixed(2) + ' mA.');
    return true;
  }
  function recordCase(which) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.load !== 'in') { S.say('Connect the load box first.'); return false; }
    var want = { both: [p.E1, p.E2], e1: [p.E1, 0], e2: [0, p.E2] }[which];
    if (Math.abs(st.E1 - want[0]) > 0.01 || Math.abs(st.E2 - want[1]) > 0.01) {
      S.say('Set the supplies for this case first: E₁ = ' + want[0].toFixed(1) + ' V and E₂ = ' + want[1].toFixed(1) + ' V.');
      return false;
    }
    if (S.rows.some(function (r) { return r.caseOf === which; })) { S.say('That case is already recorded.'); return false; }
    var i = solve().I_RL;
    S.addRow({ caseOf: which, I: i, E1: st.E1, E2: st.E2, shown: (i * 1000).toFixed(2) + ' mA' });
    S.say('Load current recorded: ' + (i * 1000).toFixed(2) + ' mA.');
    return true;
  }

  /* ---------------------------------------------------------------- results, per experiment */
  function kirchResult() {
    var i1 = rowsOf(function (r) { return r.what === 'I1'; })[0], i3 = rowsOf(function (r) { return r.what === 'I3'; })[0];
    var v3 = rowsOf(function (r) { return r.what === 'V across R3'; })[0];
    if (!i1 || !i3) return null;
    var i2 = rowsOf(function (r) { return r.what === 'I2'; })[0], i4 = rowsOf(function (r) { return r.what === 'I4'; })[0];
    var r3 = (st.E1 - i1.value * p.R1) / i3.value;
    var note = '';
    if (i2 && i4) {
      var sumIn = i1.value + i2.value, sumOut = i3.value + i4.value;
      note = 'Junction rule: ' + (sumIn * 1000).toFixed(2) + ' mA in against ' + (sumOut * 1000).toFixed(2) +
        ' mA out, a difference of ' + Math.abs(sumIn - sumOut).toExponential(1) + ' A. ';
    }
    if (v3) note += 'Loop rule: E₁ = ' + st.E1.toFixed(1) + ' V against I₁R₁ + V₃ = ' +
      (i1.value * p.R1 + v3.value).toFixed(3) + ' V.';
    return { label: 'Resistor R₃ from the loop rule', value: r3, unit: 'Ω', digits: 2, truth: p.R3, note: note };
  }
  function thevResult() {
    var voc = rowsOf(function (r) { return r.kind === 'voc'; })[0], isc = rowsOf(function (r) { return r.kind === 'isc'; })[0];
    if (!voc || !isc || !isc.I) return null;
    var rth = voc.V / isc.I, note = 'Thevenin source: ' + voc.V.toFixed(3) + ' V in series with ' + rth.toFixed(2) +
      ' Ω. Norton source: ' + (isc.I * 1000).toFixed(2) + ' mA in parallel with the same resistance. ';
    var ld = rowsOf(function (r) { return r.kind === 'load'; });
    if (ld.length) {
      var worst = 0;
      ld.forEach(function (r) { var pred = voc.V / (rth + r.RL); worst = Math.max(worst, Math.abs(pred - r.I) / Math.abs(r.I)); });
      note += 'The equivalent predicts every measured load current to within ' + (worst * 100).toFixed(1) + ' %.';
    }
    return { label: 'Thevenin / Norton resistance', value: rth, unit: 'Ω', digits: 2, truth: trueRth(), note: note };
  }
  function superResult() {
    var b = rowsOf(function (r) { return r.caseOf === 'both'; })[0], a1 = rowsOf(function (r) { return r.caseOf === 'e1'; })[0],
      a2 = rowsOf(function (r) { return r.caseOf === 'e2'; })[0];
    if (!a1 || !a2) return null;
    var sum = a1.I + a2.I;
    return { label: 'Sum of the two separate load currents', value: sum * 1000, unit: 'mA', digits: 2,
      truth: trueIL(loadBox.value(), p.E1, p.E2) * 1000,
      note: 'E₁ alone gave ' + (a1.I * 1000).toFixed(2) + ' mA and E₂ alone ' + (a2.I * 1000).toFixed(2) +
        ' mA, so together they should give ' + (sum * 1000).toFixed(2) + ' mA' +
        (b ? ', and both supplies together measured ' + (b.I * 1000).toFixed(2) + ' mA.' : '.') };
  }
  function powerRows() { return rowsOf(function (r) { return r.kind === 'load'; }); }
  function maxPowerResult() {
    var voc = rowsOf(function (r) { return r.kind === 'voc'; })[0], ld = powerRows();
    if (!voc || ld.length < 4) return null;
    var rs = ld.filter(function (r) { return r.V > 0; }).map(function (r) { return r.RL * (voc.V / r.V - 1); });
    var best = ld[0];
    ld.forEach(function (r) { if (r.V * r.V / r.RL > best.V * best.V / best.RL) best = r; });
    return { label: 'Load at which the power is greatest', value: mean(rs), unit: 'Ω', digits: 2, truth: trueRth(),
      note: 'Of the settings tried, the greatest power, ' + (best.V * best.V / best.RL * 1000).toFixed(1) +
        ' mW, came at ' + best.RL + ' Ω. Every reading also gives the network\'s own resistance exactly, from ' +
        'R = R_L(V_oc/V − 1), and those agree to ' + ((Math.max.apply(null, rs) - Math.min.apply(null, rs)) / mean(rs) * 100).toFixed(1) + ' %.' };
  }

  /* ---------------------------------------------------------------- the four procedures */
  var EXP = {
    'kirchhoff-laws': {
      resultFn: kirchResult, tol: 0.02,
      bookTitle: 'Expt. — Verification of Kirchhoff\'s laws',
      bookLines: ['Aim: to verify the junction rule and the loop rule', 'on the network trainer panel, and to find R3.',
        'Junction 2: I1 + I2 = I3 + I4', 'Left loop: E1 = I1 R1 + I3 R3', 'so R3 = (E1 - I1 R1) / I3'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Reading', get: function (r) { return r.what; } },
        { label: 'Value', get: function (r) { return r.shown; } },
        { label: 'Unit', get: function (r) { return r.unit; } }],
      graph: null,
      resultNote: 'The junction rule and the loop rule together are enough to find any one unknown in the network from the measured currents alone.',
      chips: ['Why does the junction rule hold?', 'Check my readings', 'What does the loop rule say here?', 'Why take the link out to read a current?'],
      viva: [['The junction rule is a statement of', ['Conservation of charge', 'Conservation of energy', 'Ohm\'s law'], 0,
        'Charge cannot collect at a junction.'],
        ['An ammeter must be put', ['In series, in place of the branch link', 'Across the branch', 'Across the supply'], 0,
          'It has to carry the whole branch current.'],
        ['Round a closed loop the potential differences add to', ['Zero', 'The largest emf', 'The sum of the emfs'], 0,
          'The potential at a point has one value.']]
    },
    'thevenin-norton': {
      resultFn: thevResult, tol: 0.02,
      bookTitle: 'Expt. — Thevenin\'s and Norton\'s theorems',
      bookLines: ['Aim: to find the Thevenin and Norton equivalents', 'of the panel at the load terminals, and to check',
        'that they predict the load current.', 'V_Th = open-circuit voltage,  I_N = short-circuit current',
        'R_Th = R_N = V_Th / I_N,  I_L = V_Th / (R_Th + R_L)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Reading', get: function (r) { return r.kind === 'voc' ? 'Open-circuit voltage' : r.kind === 'isc' ? 'Short-circuit current' : 'Load ' + r.RL + ' Ω'; } },
        { label: 'Meter', get: function (r) { return r.shown; } },
        { label: 'I_L (mA)', get: function (r) { return r.I === undefined ? '—' : (r.I * 1000).toFixed(2); } }],
      graph: { x: function (r) { return r.kind === 'load' ? r.RL : NaN; }, y: function (r) { return r.kind === 'load' ? r.I * 1000 : NaN; },
        xlabel: 'R_L (Ω)', ylabel: 'I_L (mA)', x0: 0, y0: 0 },
      resultNote: 'A network of any size behaves at two terminals exactly like one source and one resistance: that is the whole content of the two theorems.',
      chips: ['Why is R_Th found from V and I?', 'Check my readings', 'What is the Norton equivalent here?', 'Why replace a supply by a link?'],
      viva: [['The Thevenin voltage is measured with the load', ['Disconnected', 'Connected', 'Short-circuited'], 0,
        'It is the open-circuit terminal voltage.'],
        ['The Norton current is measured with the terminals', ['Short-circuited', 'Open', 'At the matched load'], 0,
          'It is the current the terminals pass when joined by a link.'],
        ['R_N compared with R_Th is', ['The same', 'Its reciprocal', 'Twice as large'], 0,
          'The two equivalents are source transformations of each other.']]
    },
    'superposition-theorem': {
      resultFn: superResult, tol: 0.02,
      bookTitle: 'Expt. — Verification of the superposition theorem',
      bookLines: ['Aim: to show that the load current with both supplies', 'on is the sum of the currents each would drive alone.',
        'Turning a supply down to zero leaves its branch', 'as a link, which is its own internal resistance.',
        'I(both) = I(E1 alone) + I(E2 alone)'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Case', get: function (r) { return r.caseOf === 'both' ? 'Both supplies' : r.caseOf === 'e1' ? 'E₁ alone' : 'E₂ alone'; } },
        { label: 'E₁ (V)', get: function (r) { return r.E1.toFixed(1); } },
        { label: 'E₂ (V)', get: function (r) { return r.E2.toFixed(1); } },
        { label: 'I_L (mA)', get: function (r) { return (r.I * 1000).toFixed(2); } }],
      graph: null,
      resultNote: 'The two separate currents add up to the current with both supplies on, which is what a linear network must do.',
      chips: ['Why may powers not be added?', 'Check my readings', 'Why is a supply turned down, not taken out?', 'What makes the network linear?'],
      viva: [['Superposition may be used for', ['Currents and voltages', 'Powers', 'Everything in the circuit'], 0,
        'Power goes as the square of the current, which is not linear.'],
        ['While one supply acts, the other is', ['Replaced by a link', 'Left switched on', 'Taken out, leaving a gap'], 0,
          'An ideal voltage source has no internal resistance.'],
        ['Superposition fails if the network contains', ['A diode', 'A second supply', 'A long lead'], 0,
          'A diode is not a linear element.']]
    },
    'max-power-transfer': {
      resultFn: maxPowerResult, tol: 0.03,
      bookTitle: 'Expt. — Maximum power transfer',
      bookLines: ['Aim: to show that the power in the load is greatest', 'when the load equals the network\'s own resistance.',
        'P = V² / R_L,  and R = R_L (V_oc / V − 1)', 'The peak sits at R_L = R_Th, where V = V_oc / 2.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'R_L (Ω)', get: function (r) { return r.kind === 'load' ? r.RL : 'open'; } },
        { label: 'V (V)', get: function (r) { return r.V.toFixed(3); } },
        { label: 'P (mW)', get: function (r) { return r.kind === 'load' ? (r.V * r.V / r.RL * 1000).toFixed(2) : '—'; } }],
      graph: { x: function (r) { return r.kind === 'load' ? r.RL : NaN; }, y: function (r) { return r.kind === 'load' ? r.V * r.V / r.RL * 1000 : NaN; },
        xlabel: 'R_L (Ω)', ylabel: 'P (mW)', x0: 0, y0: 0 },
      resultNote: 'The power curve is flat at its top, which is why a matched load is read off the half-voltage condition rather than by hunting for the peak.',
      chips: ['Why is the power curve so flat?', 'Check my readings', 'What is the efficiency at the match?', 'Why is a power line not matched?'],
      viva: [['Maximum power reaches the load when', ['R_L = R_Th', 'R_L is as small as possible', 'R_L is as large as possible'], 0,
        'That is where dP/dR_L is zero.'],
        ['At the match the load voltage is', ['Half the open-circuit voltage', 'The open-circuit voltage', 'A quarter of it'], 0,
          'The two equal resistances divide the voltage equally.'],
        ['A power transmission line is not matched because', ['Half the power would be wasted', 'The load would burn out', 'The voltage would be too high'], 0,
          'At the match the efficiency is only 50 per cent.']]
    }
  };
  var X = EXP[MODE] || EXP['kirchhoff-laws'];

  /* ---------------------------------------------------------------- steps */
  function setupStep() {
    return { id: 'setup', title: 'Set up', view: 'panel', render: function (u) {
        u.h2('Set up the panel');
        u.p('Two bench supplies feed the printed network. The decade box is the load. The multimeter is on its own probe leads.');
        u.task('1. Trace the printed network', st.traced, st.traced ? 'E₁–R₁–junction–R₂–E₂, R₃ to earth, R₄ to the load' : 'Follow the leads from the supplies')
          .add(u.button(st.traced ? 'Traced' : 'Trace the network', trace, !st.traced, st.traced));
        var okE = Math.abs(st.E1 - p.E1) < 0.01 && Math.abs(st.E2 - p.E2) < 0.01;
        u.task('2. Set the two supplies', okE, 'E₁ = ' + st.E1.toFixed(1) + ' V, E₂ = ' + st.E2.toFixed(1) + ' V')
          .add(u.row(u.button('E₁ to ' + p.E1.toFixed(1) + ' V', function () { S.focus('sup1'); setSupply(1, p.E1); }, Math.abs(st.E1 - p.E1) > 0.01, S.hand.busy),
            u.button('E₂ to ' + p.E2.toFixed(1) + ' V', function () { S.focus('sup2'); setSupply(2, p.E2); }, Math.abs(st.E2 - p.E2) > 0.01, S.hand.busy)));
        var okL = loadBox.value() === Math.round(p.RL) && st.load === 'in';
        u.task('3. Set the load box', okL, st.load === 'in' ? 'R_L = ' + loadBox.value() + ' Ω, connected' : 'The load lead is off')
          .add(u.row(u.button('Load box to ' + Math.round(p.RL) + ' Ω', function () { S.focus('load'); setLoad(Math.round(p.RL)); }, !okL, S.hand.busy),
            u.button('Connect the load', function () { setLoadState('in'); }, false, st.load === 'in' || S.hand.busy)));
        u.live(function () { return 'Supplies ' + st.E1.toFixed(1) + ' V and ' + st.E2.toFixed(1) + ' V  ·  load ' +
          (st.load === 'in' ? loadBox.value() + ' Ω' : st.load === 'out' ? 'open' : 'shorted'); });
        u.note('Switch a supply off before changing any lead, and never put the meter across a supply while it is set to read current.');
        u.next('Next: take the readings', st.traced && okE && okL);
      },
      ok: function () { return st.traced && Math.abs(st.E1 - p.E1) < 0.01 && Math.abs(st.E2 - p.E2) < 0.01 && loadBox.value() === Math.round(p.RL); },
      auto: function () { trace(); return setSupply(1, p.E1).then(function () { return setSupply(2, p.E2); })
        .then(function () { return setLoad(Math.round(p.RL)); }).then(function () { return setLoadState('in'); }); } };
  }

  function kirchSteps() {
    var NEED = ['I1', 'I2', 'I3', 'I4'];
    function doneI() { return NEED.filter(function (n) { return S.rows.some(function (r) { return r.what === n; }); }).length; }
    function doneV() { return S.rows.some(function (r) { return r.what === 'V across R3'; }); }
    return [
      { id: 'currents', title: 'Branch currents', view: 'panel', render: function (u) {
          u.h2('The four branch currents');
          u.p('Take the link out of a branch, plug the ammeter into its place, read the current and record it. Put the link back before moving on.');
          var row = u.row();
          ['R1', 'R2', 'R3', 'R4'].forEach(function (n) {
            var done = S.rows.some(function (r) { return r.what === 'I' + n.slice(1); });
            row.appendChild(u.button('Branch ' + n + (done ? ' ✓' : ''), function () { probeAmps(n); }, st.probeI === n, S.hand.busy));
          });
          u.row(u.button('Record this current', function () { recordCurrent(); }, true, !st.probeI || S.hand.busy),
            u.button('Put the link back', function () { putLinksBack(); }, false, !st.probeI || S.hand.busy));
          u.live(function () { return st.probeI ? 'Ammeter in branch ' + st.probeI + ': ' + (branchI(st.probeI) * 1000).toFixed(2) + ' mA'
            : 'The ammeter is not in any branch'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the loop rule', doneI() === 4);
        },
        ok: function () { return doneI() === 4; },
        auto: function () {
          return ['R1', 'R2', 'R3', 'R4'].reduce(function (pr, n) {
            return pr.then(function () { return probeAmps(n); }).then(function () { recordCurrent(); });
          }, Promise.resolve()).then(putLinksBack);
        } },
      { id: 'loop', title: 'The loop rule', view: 'panel', render: function (u) {
          u.h2('Voltages round the left loop');
          u.p('Put the voltmeter from the junction (test point 2) to earth: that is the voltage across R₃. Test point 1 to earth is the supply E₁ itself.');
          u.row(u.button('Probe test point 2', function () { probeVolts('tp2'); }, st.probe !== 'tp2', S.hand.busy),
            u.button('Probe test point 1', function () { probeVolts('tp1'); }, false, S.hand.busy),
            u.button('Probe test point 4', function () { probeVolts('tp4'); }, false, S.hand.busy));
          u.row(u.button('Record as V across R₃', function () { if (st.probe !== 'tp2') { S.say('Put the red probe on test point 2 first.'); return; } recordVolts('V across R3'); }, true, !st.probe || S.hand.busy));
          u.live(function () { return st.probe ? 'Voltmeter on test point ' + st.probe.slice(2) + ': ' + (nodeV(st.probe) - nodeV('tp0')).toFixed(3) + ' V'
            : 'The probes are off the circuit'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', doneV());
        },
        ok: function () { return doneV(); },
        auto: function () { return probeVolts('tp2').then(function () { recordVolts('V across R3'); }); } }
    ];
  }

  function thevSteps() {
    var LOADS = [5, 10, 20, 40, 80];
    return [
      { id: 'equiv', title: 'The equivalent source', view: 'panel', render: function (u) {
          u.h2('Open-circuit voltage and short-circuit current');
          u.p('Take the load lead off and read the voltage at the open terminals. Then put the ammeter straight across them and read the current.');
          u.task('1. Open-circuit voltage', have(function (r) { return r.kind === 'voc'; }) > 0, st.load === 'out' ? 'Terminals open' : 'The load is still connected')
            .add(u.row(u.button('Take the load lead off', function () { setLoadState('out'); }, st.load !== 'out', S.hand.busy),
              u.button('Record V_oc', function () { recordLoad('voc'); }, false, st.load !== 'out' || S.hand.busy)));
          u.task('2. Short-circuit current', have(function (r) { return r.kind === 'isc'; }) > 0, st.load === 'short' ? 'Ammeter across the terminals' : 'Not yet')
            .add(u.row(u.button('Ammeter across the terminals', function () { setLoadState('short'); }, st.load !== 'short', S.hand.busy),
              u.button('Record I_sc', function () { recordLoad('isc'); }, false, st.load !== 'short' || S.hand.busy)));
          u.live(function () { return st.load === 'out' ? 'Open terminals: ' + trueVoc().toFixed(3) + ' V'
            : st.load === 'short' ? 'Shorted terminals: ' + (solve().I_RL * 1000).toFixed(2) + ' mA'
              : 'Load box connected at ' + loadBox.value() + ' Ω'; });
          u.h3('Observation table'); u.table();
          u.next('Next: test the equivalent', have(function (r) { return r.kind === 'voc'; }) > 0 && have(function (r) { return r.kind === 'isc'; }) > 0);
        },
        ok: function () { return have(function (r) { return r.kind === 'voc'; }) > 0 && have(function (r) { return r.kind === 'isc'; }) > 0; },
        auto: function () { return setLoadState('out').then(function () { recordLoad('voc'); })
          .then(function () { return setLoadState('short'); }).then(function () { recordLoad('isc'); }); } },
      { id: 'test', title: 'Test it', view: 'load', render: function (u) {
          u.h2('Does the equivalent predict the load current?');
          u.p('Put the load box back and measure the load current at several settings. Compare each with V_Th / (R_Th + R_L).');
          var row = u.row();
          LOADS.forEach(function (rl) {
            var done = S.rows.some(function (r) { return r.kind === 'load' && r.RL === rl; });
            row.appendChild(u.button(rl + ' Ω' + (done ? ' ✓' : ''), function () {
              setLoad(rl).then(function (ok) { if (ok) return setLoadState('in'); }); }, loadBox.value() === rl && st.load === 'in', S.hand.busy));
          });
          u.row(u.button('Record this load reading', function () { recordLoad('load'); }, true, st.load !== 'in' || S.hand.busy));
          u.live(function () { return st.load === 'in' ? 'Load ' + loadBox.value() + ' Ω  ·  ' + solve().V_RL.toFixed(3) + ' V  ·  ' +
            (solve().I_RL * 1000).toFixed(2) + ' mA' : 'The load box is not connected'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', have(function (r) { return r.kind === 'load'; }) >= 3);
        },
        ok: function () { return have(function (r) { return r.kind === 'load'; }) >= 3; },
        auto: function () {
          return LOADS.reduce(function (pr, rl) {
            return pr.then(function () { return setLoad(rl); }).then(function () { return setLoadState('in'); })
              .then(function () { recordLoad('load'); });
          }, Promise.resolve());
        } }
    ];
  }

  function superSteps() {
    var CASES = [['both', 'Both supplies on'], ['e1', 'E₁ alone (E₂ turned to zero)'], ['e2', 'E₂ alone (E₁ turned to zero)']];
    function setCase(which) {
      var want = { both: [p.E1, p.E2], e1: [p.E1, 0], e2: [0, p.E2] }[which];
      return setSupply(1, want[0]).then(function () { return setSupply(2, want[1]); });
    }
    return [
      { id: 'cases', title: 'Three readings', view: 'panel', render: function (u) {
          u.h2('The load current in three cases');
          u.p('Read the load current with both supplies on, then with each one alone. A supply turned down to zero leaves its branch as a plain link.');
          var row = u.row();
          CASES.forEach(function (cq) {
            var done = S.rows.some(function (r) { return r.caseOf === cq[0]; });
            row.appendChild(u.button(cq[1] + (done ? ' ✓' : ''), function () { setCase(cq[0]); }, false, S.hand.busy));
          });
          u.row(u.button('Record the load current', function () {
            var which = Math.abs(st.E2) < 0.01 ? 'e1' : Math.abs(st.E1) < 0.01 ? 'e2' : 'both';
            recordCase(which); }, true, S.hand.busy || st.load !== 'in'));
          u.live(function () { return 'E₁ = ' + st.E1.toFixed(1) + ' V, E₂ = ' + st.E2.toFixed(1) + ' V  ·  load current ' +
            (solve().I_RL * 1000).toFixed(2) + ' mA'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return CASES.reduce(function (pr, cq) {
            return pr.then(function () { return setCase(cq[0]); }).then(function () { recordCase(cq[0]); });
          }, Promise.resolve());
        } }
    ];
  }

  function powerSteps() {
    var LOADS = [2, 5, 10, 15, 20, 30, 50, 100];
    return [
      { id: 'voc', title: 'Open-circuit voltage', view: 'panel', render: function (u) {
          u.h2('First, the open-circuit voltage');
          u.p('Take the load lead off and read the voltage at the open terminals. Every later reading is compared with it.');
          u.row(u.button('Take the load lead off', function () { setLoadState('out'); }, st.load !== 'out', S.hand.busy),
            u.button('Record V_oc', function () { recordLoad('voc'); }, true, st.load !== 'out' || S.hand.busy));
          u.live(function () { return st.load === 'out' ? 'Open terminals: ' + trueVoc().toFixed(3) + ' V' : 'The load box is still connected'; });
          u.h3('Observation table'); u.table();
          u.next('Next: change the load', have(function (r) { return r.kind === 'voc'; }) > 0);
        },
        ok: function () { return have(function (r) { return r.kind === 'voc'; }) > 0; },
        auto: function () { return setLoadState('out').then(function () { recordLoad('voc'); }); } },
      { id: 'sweep', title: 'Power against load', view: 'load', render: function (u) {
          u.h2('The load voltage at each setting');
          u.p('Set the decade box to each value in turn and record the load voltage. The power follows from V²/R_L.');
          var row = u.row();
          LOADS.forEach(function (rl) {
            var done = S.rows.some(function (r) { return r.kind === 'load' && r.RL === rl; });
            row.appendChild(u.button(rl + ' Ω' + (done ? ' ✓' : ''), function () {
              setLoad(rl).then(function (ok) { if (ok) return setLoadState('in'); }); }, loadBox.value() === rl && st.load === 'in', S.hand.busy));
          });
          u.row(u.button('Record this reading', function () { recordLoad('load'); }, true, st.load !== 'in' || S.hand.busy));
          u.live(function () { return st.load === 'in' ? 'Load ' + loadBox.value() + ' Ω  ·  ' + solve().V_RL.toFixed(3) + ' V  ·  ' +
            (solve().V_RL * solve().I_RL * 1000).toFixed(2) + ' mW' : 'The load box is not connected'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', powerRows().length >= 6);
        },
        ok: function () { return powerRows().length >= 6; },
        auto: function () {
          return LOADS.reduce(function (pr, rl) {
            return pr.then(function () { return setLoad(rl); }).then(function () { return setLoadState('in'); })
              .then(function () { recordLoad('load'); });
          }, Promise.resolve());
        } }
    ];
  }

  var STEPS = { 'kirchhoff-laws': kirchSteps, 'thevenin-norton': thevSteps,
    'superposition-theorem': superSteps, 'max-power-transfer': powerSteps };

  return {
    camera: { pos: [0.0, 1.0, 0.92], look: [0, 0.02, -0.2] },
    views: { bench: [[0.0, 1.0, 0.92], [0, 0.02, -0.2]], panel: [[0.0, 0.70, 0.40], [0, 0.02, -0.30]],
      dmm: [[-0.22, 0.3, 0.32], [-0.22, 0.03, 0.06]], load: [[0.34, 0.3, 0.34], [0.34, 0.03, 0.06]],
      sup1: [[-0.52, 0.34, -0.26], [-0.52, 0.06, -0.6]], sup2: [[0.52, 0.34, -0.26], [0.52, 0.06, -0.6]],
      book: [[-0.6, 0.46, 0.5], [-0.6, 0.0, 0.06]] },
    theory: {
      principle: S.lab.theory,
      formula: MODE === 'kirchhoff-laws' ? 'ΣI at a junction = 0,   ΣV round a loop = 0'
        : MODE === 'thevenin-norton' ? 'R_Th = V_oc / I_sc,   I_L = V_oc / (R_Th + R_L)'
          : MODE === 'superposition-theorem' ? 'I(both) = I(E₁ alone) + I(E₂ alone)'
            : 'P = V_oc² R_L / (R_Th + R_L)²,   greatest at R_L = R_Th',
      formulaNote: 'every reading on this panel comes from the circuit solver, the same code the server checks',
      more: [
        'The panel is one network read in four ways. R₁ and R₂ carry the two supplies to the junction, R₃ hangs from the junction to the earth rail, and R₄ carries on to the load terminals where the decade box is plugged in.',
        'A branch current is measured by taking that branch\'s brass link out and plugging the ammeter into the two sockets it leaves. A voltage is measured by putting the probes on two test points; the meter draws about a microampere, so it changes nothing.',
        'Turning a bench supply down to zero is not the same as taking it out: its branch stays in the circuit as a link of a few milliohms, which is exactly what the theorems ask for when a source is "replaced by its internal resistance".'],
      precautions: S.lab.safety },
    book: { title: X.bookTitle, at: [-0.6, 0.06, 0.1], lines: X.bookLines, columns: X.columns },
    graph: X.graph,
    result: X.resultFn,
    tol: X.tol,
    resultNote: X.resultNote,
    chips: X.chips,
    viva: X.viva,
    askState: function () {
      return { experiment: S.lab.title, supply_E1_volts: st.E1, supply_E2_volts: st.E2,
        load_box_ohms: loadBox.value(), load_terminals: st.load === 'in' ? 'load box connected'
          : st.load === 'out' ? 'open' : 'ammeter across them',
        multimeter: st.dmm === 'A' ? 'amperes' : 'volts',
        probes_on: st.probeI ? 'branch ' + st.probeI : st.probe ? 'test point ' + st.probe.slice(2) : 'nothing',
        meter_reading: readText()[0] + ' ' + readText()[2], readings_taken: S.rows.length };
    },
    steps: [setupStep()].concat((STEPS[MODE] || kirchSteps)()),
    tick: function () {
      var r = readText();
      dmm.show(r[0], r[1], r[2]);
      sup1.show(st.E1); sup2.show(st.E2);
      hudA.set(r[0] + (r[2] ? ' ' + r[2] : ''));
      hudB.set(st.load === 'in' ? loadBox.value() + ' Ω' : st.load === 'out' ? 'open' : 'shorted');
      hudC.set(st.E1.toFixed(1) + ' V / ' + st.E2.toFixed(1) + ' V');
    }
  };
});
