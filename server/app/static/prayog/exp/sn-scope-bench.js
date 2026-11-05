/* Prayogshala studio rig `sn-scope-bench`: ONE electronics bench with a solderless breadboard, a control panel
   (a function generator and the circuit's settings as dials the hand turns, with a POWER rocker) and a two-channel
   oscilloscope whose screen is DRAWN FROM THE SAMPLED WAVEFORMS of the lab's own kernel (packs/sn_elec.js), with
   cursors the student switches on. It serves the instrument, analog and communication set-ups of
   app/prayog/labs/sn_elec.py: oscilloscope measurements, pulse timing, diode clippers and clampers, the 555 timer,
   the UJT oscillator, the common-emitter amplifier and AM / FM modulation. The circuit on the board changes with the
   lab; the bench, the hand actions and the procedure do not. Every number on the screen and in the table is found on
   the sampled waveform by the kernel (crossings, peaks, intervals); nothing is read back from a formula. Low
   voltages only: a bench generator and a battery bias, never mains. */
HoolaStudio.define('sn-scope-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KN = HK.K[S.lab.kernel], p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function fmt(v, d) { return isFinite(v) ? v.toFixed(d) : '----'; }
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }
  function maxOf(a) { var m = a[0], i; for (i = 1; i < a.length; i++) if (a[i] > m) m = a[i]; return m; }
  function minOf(a) { var m = a[0], i; for (i = 1; i < a.length; i++) if (a[i] < m) m = a[i]; return m; }
  function mean(a) { var s = 0, i; for (i = 0; i < a.length; i++) s += a[i]; return a.length ? s / a.length : NaN; }
  function ols(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d, m;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    if (n < 2 || d === 0) return { m: NaN, c: NaN };
    m = (n * sxy - sx * sy) / d;
    return { m: m, c: (sy - m * sx) / n };
  }
  function origin(pts) { var a = 0, b = 0, i; for (i = 0; i < pts.length; i++) { a += pts[i][0] * pts[i][1]; b += pts[i][0] * pts[i][0]; } return b ? a / b : NaN; }
  function cross(y, dt, level, rising) {
    var out = [], i, a, b;
    for (i = 1; i < y.length; i++) {
      a = y[i - 1] - level; b = y[i] - level;
      if (rising && a < 0 && b >= 0 && b !== a) out.push((i - 1 + (0 - a) / (b - a)) * dt);
      else if (!rising && a >= 0 && b < 0) out.push((i - 1 + (0 - a) / (b - a)) * dt);
    }
    return out;
  }
  function eng(v, unit) {                       // 1.50 µs, 2.20 kΩ ...
    var a = Math.abs(v), pre = '', k = 1;
    if (a === 0 || !isFinite(a)) return '0 ' + unit;
    if (a >= 1e6) { pre = 'M'; k = 1e-6; } else if (a >= 1e3) { pre = 'k'; k = 1e-3; } else if (a >= 1) { pre = ''; k = 1; } else if (a >= 1e-3) { pre = 'm'; k = 1e3; } else if (a >= 1e-6) { pre = 'µ'; k = 1e6; } else if (a >= 1e-9) { pre = 'n'; k = 1e9; } else { pre = 'p'; k = 1e12; }
    return (v * k).toPrecision(3).replace(/\.?0+$/, function (m) { return m.indexOf('.') >= 0 ? '' : m; }) + ' ' + pre + unit;
  }
  function L(text, o) {
    o = o || {};
    var w = o.w || 0.05, ratio = o.ratio || 0.25, px = o.px || 512, h = Math.round(px * ratio);
    var tex = S.canvasTex(px, h, function (x) {
      if (o.bg) { x.fillStyle = o.bg; x.fillRect(0, 0, px, h); }
      x.fillStyle = o.color || '#1b1b1b'; x.textAlign = 'center'; x.textBaseline = 'middle';
      var fs = Math.round(h * 0.62), wt = o.weight || 600;
      x.font = wt + ' ' + fs + 'px "Public Sans", sans-serif';
      var mw = x.measureText(text).width;
      if (mw > px * 0.94) { fs = Math.floor(fs * px * 0.94 / mw); x.font = wt + ' ' + fs + 'px "Public Sans", sans-serif'; }
      x.fillText(text, px / 2, h / 2);
    });
    return new T.Mesh(new T.PlaneGeometry(w, w * ratio), new T.MeshStandardMaterial({ map: tex, transparent: !o.bg, roughness: 0.6 }));
  }
  var MEMO = {};
  function memo(tag, q, fn) {
    var k = tag + JSON.stringify(q), v = MEMO[k];
    if (v) return v;
    if (Object.keys(MEMO).length > 40) MEMO = {};
    v = MEMO[k] = fn(q); return v;
  }

  // =============================================================================================== the bench
  var WOODW = 1.2;
  function cabinet(w, h, d, x, z, color) {
    var b = S.rounded(w, h, d, 0.008, new T.MeshStandardMaterial({ color: color, roughness: 0.5, metalness: 0.1 }));
    b.rotation.x = -Math.PI / 2; b.position.set(x, d / 2, z); S.scene.add(b); S.contact(w + 0.06, h + 0.06, x, z, 0.5); return b;
  }
  function dialKnob(parent, x, y, z, r) {
    var k = new T.Group(); k.position.set(x, y, z); parent.add(k);
    var sk = S.mesh(new T.CylinderGeometry(r * 1.25, r * 1.3, 0.004, 32), M.black); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; k.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(r, r * 1.08, 0.016, 32), new T.MeshStandardMaterial({ color: 0x24252a, roughness: 0.4, metalness: 0.3 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; k.add(kb);
    var pt = S.mesh(new T.BoxGeometry(0.003, r * 0.9, 0.0016), M.white, false); pt.position.set(0, r * 0.45, 0.0215); k.add(pt);
    return k;
  }

  // ---------- breadboard and its parts
  var BBX = 0.06, BBZ = -0.1, BW = 0.34, BD = 0.13, BT = 0.012;
  var BB = new T.Group(); S.scene.add(BB); BB.position.set(BBX, 0, BBZ);
  var bbTex = S.canvasTex(1400, 540, function (x, w, h) {
    x.fillStyle = '#efece2'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(0,0,0,.12)'; x.lineWidth = 2; x.strokeRect(6, 6, w - 12, h - 12);
    [[30, '#b8322a'], [h - 30, '#2c5fb4']].forEach(function (rail) { x.strokeStyle = rail[1]; x.lineWidth = 3; x.beginPath(); x.moveTo(60, rail[0]); x.lineTo(w - 60, rail[0]); x.stroke(); });
    x.fillStyle = '#7d7668'; var i, j;
    for (i = 0; i < 56; i++) for (j = 0; j < 10; j++) x.fillRect(66 + i * 21, 76 + j * 30 + (j >= 5 ? 56 : 0), 7, 7);
    x.fillStyle = '#d7d2c4'; x.fillRect(50, 76 + 5 * 30 + 6, w - 100, 40);
  });
  var bbBody = S.rounded(BW, BD, BT, 0.004, new T.MeshStandardMaterial({ color: 0xefece2, roughness: 0.6 })); bbBody.rotation.x = -Math.PI / 2; bbBody.position.y = BT / 2; BB.add(bbBody);
  var bbTop = new T.Mesh(new T.PlaneGeometry(BW - 0.004, BD - 0.004), new T.MeshStandardMaterial({ map: bbTex, roughness: 0.65 })); bbTop.rotation.x = -Math.PI / 2; bbTop.position.y = BT + 0.0004; BB.add(bbTop);
  S.contact(BW + 0.08, BD + 0.08, BBX, BBZ, 0.5);
  var PY = BT + 0.006;
  var BAND = ['#111111', '#6b3a1e', '#c4231c', '#e8761e', '#e9c81a', '#2c8a3a', '#2747a8', '#7a3aa8', '#8a8a8a', '#f2f2f2'];
  function bandsOf(r) { var e = Math.floor(Math.log(r) / Math.LN10 + 1e-9) - 1, d = Math.round(r / Math.pow(10, e)); if (d >= 100) { d = Math.round(d / 10); e += 1; } return [Math.floor(d / 10), d % 10, Math.max(0, Math.min(9, e))]; }
  function rLabel(r) { return r >= 1e6 ? (r / 1e6) + ' MΩ' : r >= 1e3 ? (r / 1e3) + ' kΩ' : r + ' Ω'; }
  function cLabel(c) { return c >= 1e-6 ? (c * 1e6) + ' µF' : c >= 1e-9 ? (c * 1e9) + ' nF' : (c * 1e12) + ' pF'; }
  var parts = [];
  function resistor(x, z, val, tag, vert) {
    var tex = S.liveTex(64, 400), g = new T.Group(); BB.add(g); g.position.set(x, PY + 0.003, z); if (vert) g.rotation.y = Math.PI / 2;
    var body = S.mesh(new T.CylinderGeometry(0.0019, 0.0019, 0.015, 20), new T.MeshStandardMaterial({ map: tex, roughness: 0.55 })); body.rotation.z = Math.PI / 2; g.add(body);
    [-1, 1].forEach(function (sg) { var ld = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.007, 8), M.chrome, false); ld.rotation.z = Math.PI / 2; ld.position.x = sg * 0.011; g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.006, 8), M.chrome, false); dn.position.set(sg * 0.0145, -0.003, 0); g.add(dn); });
    var lb = L(tag + ' ' + rLabel(val), { w: 0.04, ratio: 0.26, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + (vert ? 0 : 0.014)); BB.add(lb);
    var o = { g: g, label: lb, tag: tag, val: 0 };
    o.set = function (v) { if (v === o.val) return; o.val = v; var bd = bandsOf(v);
      tex.draw(function (c, w, h) { c.fillStyle = '#d9bf8c'; c.fillRect(0, 0, w, h); [[0.24, BAND[bd[0]]], [0.37, BAND[bd[1]]], [0.5, BAND[bd[2]]], [0.78, '#c9a23a']].forEach(function (b) { c.fillStyle = b[1]; c.fillRect(0, h * (1 - b[0]) - 16, w, 32); }); });
      var nt = L(o.tag + ' ' + rLabel(v), { w: 0.04, ratio: 0.26, color: '#3d3528', weight: 700 }); lb.material.map = nt.material.map; lb.material.needsUpdate = true; };
    o.set(val); parts.push(o); return o;
  }
  function capacitor(x, z, val, tag, kind, unknown) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY, z);
    var body;
    if (kind === 'el') { body = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.012, 22), new T.MeshStandardMaterial({ color: 0x1f3a7a, roughness: 0.4, metalness: 0.2 })); body.position.y = 0.006; }
    else { body = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.0025, 24), new T.MeshStandardMaterial({ color: 0xc9792e, roughness: 0.5 })); body.rotation.x = Math.PI / 2; body.position.y = 0.007; }
    g.add(body);
    [-1, 1].forEach(function (sg) { var pin = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.012, 8), M.chrome, false); pin.position.set(sg * 0.0022, -0.001, 0); g.add(pin); });
    var lb = L(tag + (unknown ? ' = ?' : ' ' + cLabel(val)), { w: 0.04, ratio: 0.26, color: unknown ? '#7a1f1f' : '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + 0.014); BB.add(lb);
    var o = { g: g }; parts.push(o); return o;
  }
  function diode(x, z, tag) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY + 0.003, z);
    var body = S.mesh(new T.CylinderGeometry(0.0019, 0.0019, 0.0085, 20), new T.MeshStandardMaterial({ color: 0xc9824a, roughness: 0.2, transparent: true, opacity: 0.85 })); body.rotation.z = Math.PI / 2; g.add(body);
    var band = S.mesh(new T.CylinderGeometry(0.00205, 0.00205, 0.0014, 20), M.black); band.rotation.z = Math.PI / 2; band.position.x = -0.0028; g.add(band);
    [-1, 1].forEach(function (sg) { var ld = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.008, 8), M.chrome, false); ld.rotation.z = Math.PI / 2; ld.position.x = sg * 0.0085; g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.006, 8), M.chrome, false); dn.position.set(sg * 0.0125, -0.003, 0); g.add(dn); });
    var lb = L(tag || 'D1', { w: 0.03, ratio: 0.3, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + 0.012); BB.add(lb);
    var o = { g: g, label: lb }; parts.push(o); return o;
  }
  function dip8(x, z, name) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY, z);
    var dipM = new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.4 });
    var d = S.rounded(0.0098, 0.0064, 0.0035, 0.0006, dipM); d.rotation.x = -Math.PI / 2; d.position.y = 0.00175 + 0.002; g.add(d);
    var lb = L(name, { w: 0.0085, ratio: 0.34, color: '#cfcfcf', px: 256 }); lb.rotation.x = -Math.PI / 2; lb.position.set(0.001, 0.0058, 0); g.add(lb);
    var notch = S.mesh(new T.CylinderGeometry(0.0011, 0.0011, 0.0012, 14, 1, false, 0, Math.PI), new T.MeshStandardMaterial({ color: 0x2a2c32, roughness: 0.5 }), false); notch.position.set(-0.0049, 0.0057, 0); g.add(notch);
    var i, sg; for (i = 0; i < 4; i++) for (sg = -1; sg <= 1; sg += 2) { var pin = S.mesh(new T.BoxGeometry(0.0006, 0.005, 0.0003), M.chrome, false); pin.position.set(-0.0038 + i * 0.00254, -0.0005, sg * 0.0036); g.add(pin); }
    var o = { g: g }; parts.push(o); return o;
  }
  function to92(x, z, name) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY, z);
    var caseM = new T.MeshStandardMaterial({ color: 0x14151a, roughness: 0.42 });
    var body = S.mesh(new T.CylinderGeometry(0.0023, 0.0023, 0.0048, 24, 1, false, -0.7, Math.PI * 2 - 1.4), caseM); body.position.y = 0.0024; g.add(body);
    var flat = S.mesh(new T.BoxGeometry(0.0038, 0.0048, 0.0004), caseM); flat.position.set(0, 0.0024, 0.00185); g.add(flat);
    var cap = S.mesh(new T.SphereGeometry(0.0023, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), caseM); cap.scale.y = 0.5; cap.position.y = 0.0048; g.add(cap);
    [-0.0013, 0, 0.0013].forEach(function (dx) { var lg = S.mesh(new T.CylinderGeometry(0.00035, 0.00035, 0.007, 8), M.chrome, false); lg.position.set(dx, -0.0005, 0); g.add(lg); });
    var lb = L(name, { w: 0.03, ratio: 0.3, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + 0.013); BB.add(lb);
    var o = { g: g }; parts.push(o); return o;
  }
  function battery(x, z, txt) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY, z);
    var b = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.028, 24), new T.MeshStandardMaterial({ color: 0x1f6f4a, roughness: 0.35, metalness: 0.2 })); b.rotation.z = Math.PI / 2; b.position.y = 0.0085; g.add(b);
    var lb = L(txt, { w: 0.024, ratio: 0.3, color: '#f4f4f4' }); lb.position.set(0, 0.0185, 0); lb.rotation.x = -Math.PI / 2; g.add(lb);
    var o = { g: g }; parts.push(o); return o;
  }
  function coil(x, z, txt) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY + 0.006, z);
    var core = S.mesh(new T.TorusGeometry(0.008, 0.004, 12, 24), new T.MeshStandardMaterial({ color: 0x2f6fb3, roughness: 0.45 })); core.rotation.x = Math.PI / 2; g.add(core);
    var lb = L(txt, { w: 0.04, ratio: 0.26, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + 0.016); BB.add(lb);
    parts.push({ g: g }); return g;
  }
  function jumper(a, b, color) {
    var pa = [BBX + a[0], BT + 0.003, BBZ + a[1]], pbb = [BBX + b[0], BT + 0.003, BBZ + b[1]];
    S.wire([pa, [(pa[0] + pbb[0]) / 2, BT + 0.016, (pa[2] + pbb[2]) / 2], pbb], color);
  }

  // ---------- control panel (generator and circuit settings) with a POWER rocker
  var GPX = -0.44, GPZ = -0.24;
  var gp = new T.Group(); S.scene.add(gp); gp.position.set(GPX, 0, GPZ);
  var gpBody = S.rounded(0.26, 0.12, 0.1, 0.01, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); gpBody.rotation.x = -Math.PI / 2; gpBody.position.y = 0.05; gp.add(gpBody);
  S.contact(0.34, 0.2, GPX, GPZ, 0.5);

  // =============================================================================================== the lab's plan
  var PLANS = {};
  var YEL = '#ffe45e', CYA = '#64e3ff', GRN = '#8dff9b';
  function ln10(x) { return Math.log(x) / Math.LN10; }
  function crossMarks(t, ca, cb, col) {
    var m = [];
    if (ca.length >= 2) { m.push({ kind: 'v', t: ca[0], color: YEL }); m.push({ kind: 'v', t: ca[1], color: YEL }); }
    if (cb && ca.length) { var i; for (i = 0; i < cb.length; i++) if (cb[i] >= ca[0] - 1e-12) { m.push({ kind: 'v', t: cb[i], color: CYA }); break; } }
    return m;
  }

  PLANS['sn-cro-measure'] = function () { return {
    compName: 'RC low-pass network with a generator and the scope',
    wiring: 'Generator (2 V peak on a 0.5 V DC level) → R = ' + rLabel(p.R) + ' → capacitor C (unknown) to ground. Channel 1 is on the generator, channel 2 across the capacitor.',
    controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, vals: [300, 500, 800, 1000, 1500, 2000, 3000, 5000, 8000] }],
    art: function () { resistor(-0.07, -0.01, p.R, 'R'); capacitor(0.0, -0.01, 0, 'C', 'ceramic', true); battery(0.09, -0.02, 'GEN');
      jumper([-0.085, -0.01], [-0.12, 0.03], 'yellow'); jumper([0.0, 0.01], [0.09, 0.03], 'black'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), a = t[1], b = t[2], dt = t[0], ca = cross(a, dt, mean(a), true), cb = cross(b, dt, mean(b), true);
      return { dt: dt, ch: [{ y: a, color: YEL, name: 'CH1' }, { y: b, color: CYA, name: 'CH2' }], marks: crossMarks(dt, ca, cb) }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['T = ' + eng(m.T, 's') + '   f = 1/T = ' + eng(m.f, 'Hz'), 'CH1 p-p = ' + fmt(m.Vpp1, 3) + ' V   mean = ' + fmt(m.Vdc1, 3) + ' V', 'CH2 p-p = ' + fmt(m.Vpp2, 3) + ' V', 'CH2 lags CH1 by ' + fmt(m.phase, 2) + '°'],
        row: { f: m.f, T: m.T, vpp1: m.Vpp1, vdc: m.Vdc1, vpp2: m.Vpp2, phase: m.phase } }; },
    cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'T (ms)', get: function (r) { return fmt(r.T * 1000, 3); } }, { label: 'Vpp1 (V)', get: function (r) { return fmt(r.vpp1, 3); } },
      { label: 'Mean (V)', get: function (r) { return fmt(r.vdc, 3); } }, { label: 'Vpp2 (V)', get: function (r) { return fmt(r.vpp2, 3); } }, { label: 'φ (°)', get: function (r) { return fmt(r.phase, 2); } },
      { label: 'tan φ', get: function (r) { return fmt(Math.tan(r.phase * Math.PI / 180), 4); } }],
    need: 6,
    runs: [300, 500, 800, 1000, 1500, 2000, 3000, 5000, 8000].map(function (f) { return { f: f }; }),
    graph: { x: function (r) { return r.f / 1000; }, y: function (r) { return Math.tan(r.phase * Math.PI / 180); }, xlabel: 'Frequency (kHz)', ylabel: 'tan φ',
      line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      var cs = rows.map(function (r) { return Math.tan(r.phase * Math.PI / 180) / (2 * Math.PI * r.f * p.R); });
      return { label: 'Capacitor C', value: mean(cs) * 1e9, unit: 'nF', digits: 2, truth: p.C * 1e9,
        note: 'tan φ = 2π f R C, so C = tan φ / (2π f R) at each frequency; average of ' + rows.length + ' readings.' };
    },
    resultNote: 'tan φ grows in proportion to the frequency, so the points lie on a straight line through the origin with slope 2π R C. The same recording also gave the period and frequency, the peak-to-peak voltage and the DC level of the signal.',
    chips: ['How is the phase read from the screen?', 'Why does tan φ rise with frequency?', 'What is the DC level?', 'Check my readings'],
    viva: [['The frequency of a signal is found from the screen as', ['1 divided by the period', 'the volts per division', 'the peak-to-peak voltage'], 0, 'f = 1/T.']] }; };

  PLANS['sn-cro-pulse'] = function () { return {
    compName: 'Pulse generator, decade resistor and capacitor',
    wiring: 'Pulse generator (0 to 5 V, edges 5 ns) → resistor box → capacitor C (unknown) to ground. Channel 1 is on the generator, channel 2 across the capacitor. Scope bandwidth 100 MHz.',
    controls: [{ param: 'R', label: 'Resistor box', short: 'RESISTOR', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [1000, 2200, 3300, 4700, 6800, 10000, 15000, 22000] }],
    art: function () { var r = resistor(-0.07, -0.01, p.R, 'R'); capacitor(0.0, -0.01, 0, 'C', 'ceramic', true); battery(0.09, -0.02, 'PULSE');
      jumper([-0.085, -0.01], [-0.12, 0.03], 'yellow'); jumper([0.0, 0.01], [0.09, 0.03], 'black'); return function (q) { r.set(q.R); }; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), a = t[1], b = t[2], dt = t[0], top = maxOf(b), m = KN.measure(qq);
      var r10 = cross(b, dt, 0.1 * top, true), r90 = cross(b, dt, 0.9 * top, true);
      return { dt: dt, ch: [{ y: a, color: YEL, name: 'CH1' }, { y: b, color: CYA, name: 'CH2' }], marks: [{ kind: 'h', ch: 1, y: 0.1 * top }, { kind: 'h', ch: 1, y: 0.9 * top }, { kind: 'v', t: r10[0], color: CYA }, { kind: 'v', t: r90[0], color: CYA }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Rise time (10 to 90 %) = ' + eng(m.tr, 's'), 'Fall time (90 to 10 %) = ' + eng(m.tf, 's'), 'Delay (50 % to 50 %) = ' + eng(m.td, 's'), 'Final level = ' + fmt(m.top, 3) + ' V'],
        row: { tr: m.tr, tf: m.tf, td: m.td } }; },
    cols: [{ label: 'R', get: function (r) { return rLabel(r.set.R); } }, { label: 'Rise (µs)', get: function (r) { return fmt(r.tr * 1e6, 3); } }, { label: 'Fall (µs)', get: function (r) { return fmt(r.tf * 1e6, 3); } },
      { label: 'Delay (µs)', get: function (r) { return fmt(r.td * 1e6, 3); } }, { label: 'C = tr / (2.197 R) (nF)', get: function (r) { return fmt(r.tr / (Math.log(9) * r.set.R) * 1e9, 3); } }],
    need: 6,
    runs: [1000, 2200, 3300, 4700, 6800, 10000, 15000, 22000].map(function (v) { return { R: v }; }),
    graph: { x: function (r) { return r.set.R / 1000; }, y: function (r) { return r.tr * 1e6; }, xlabel: 'R (kΩ)', ylabel: 'Rise time (µs)',
      line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      var cs = rows.map(function (r) { return r.tr / (Math.log(9) * r.set.R); });
      return { label: 'Capacitor C', value: mean(cs) * 1e9, unit: 'nF', digits: 3, truth: p.C * 1e9,
        note: 'For each resistance C = t_r / (2.197 R); the delay is ' + fmt(mean(rows.map(function (r) { return r.td / r.tr; })), 3) + ' of the rise time (ln 2 / ln 9 = 0.315).' };
    },
    resultNote: 'The rise time is proportional to R, so t_r against R is a straight line through the origin with slope 2.197 C. The scope\'s own rise time (3.5 ns for 100 MHz) is far below the shortest edge here, so it adds almost nothing in quadrature.',
    chips: ['Why is the rise time 2.197 RC?', 'What limits the fastest edge I can see?', 'Why is the delay shorter than the rise?', 'Check my readings'],
    viva: [['The 10 to 90 % rise time of an RC circuit is', ['2.197 R C', 'R C', '0.693 R C'], 0, 'ln 9 = 2.197.']] }; };

  var SHAPE_NAMES = ['positive clipper', 'negative clipper', 'positive clamper', 'negative clamper'];
  PLANS['sn-waveshaper'] = function () { return {
    compName: SAMPLE || 'Diode wave-shaping board',
    wiring: 'A 5 V peak, 1 kHz sine from the generator goes to the board. In the clippers a series resistor R = 10 kΩ and the diode go to the bias battery; in the clampers a capacitor C = 1 µF is in series with the signal, with the diode across the output and the load R_L = 1 MΩ.',
    controls: [{ param: 'mode', label: 'Circuit', short: 'CIRCUIT', unit: '', digits: 0, names: SHAPE_NAMES, vals: [0, 1, 2, 3] },
      { param: 'Vb', label: 'Bias voltage', short: 'BIAS', unit: 'V', digits: 1, vals: [-1, 0, 1] }],
    art: function () {
      var rs = resistor(-0.08, -0.03, p.R, 'R'), rl = resistor(0.08, -0.03, p.RL, 'RL'), cp = capacitor(-0.02, -0.03, p.C, 'C', 'ceramic'), dd = diode(0.03, 0.0, 'D1'), bt = battery(0.1, 0.02, 'Vb');
      jumper([-0.095, -0.03], [-0.13, 0.03], 'yellow'); jumper([0.04, 0.0], [0.09, 0.04], 'blue');
      return function (q) { var m = Math.round(q.mode); cp.g.visible = m >= 2; rs.g.visible = m < 2; rs.label.visible = m < 2; rl.g.visible = m >= 2; rl.label.visible = m >= 2; dd.g.rotation.y = (m === 0 || m === 3) ? 0 : Math.PI; }; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), vi = t[1], vo = t[2], m = KN.measure(qq);
      return { dt: t[0], ch: [{ y: vi, color: YEL, name: 'IN' }, { y: vo, color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: m.Vmax }, { kind: 'h', ch: 1, y: m.Vmin }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Output maximum = ' + fmt(m.Vmax, 3) + ' V', 'Output minimum = ' + fmt(m.Vmin, 3) + ' V', 'Output peak-to-peak = ' + fmt(m.Vpp, 3) + ' V (input 10 V)', 'Output mean = ' + fmt(m.Vdc, 3) + ' V'],
        row: { vmax: m.Vmax, vmin: m.Vmin, vpp: m.Vpp } }; },
    cols: [{ label: 'Circuit', get: function (r) { return SHAPE_NAMES[Math.round(r.set.mode)]; } }, { label: 'Bias (V)', get: function (r) { return fmt(r.set.Vb, 1); } }, { label: 'Vmax (V)', get: function (r) { return fmt(r.vmax, 3); } },
      { label: 'Vmin (V)', get: function (r) { return fmt(r.vmin, 3); } }, { label: 'Vpp (V)', get: function (r) { return fmt(r.vpp, 3); } }, { label: 'V_f found (V)', get: function (r) { return fmt(vfOf(r), 3); } }],
    need: 6,
    runs: [{ mode: 0, Vb: 0 }, { mode: 1, Vb: 0 }, { mode: 2, Vb: 0 }, { mode: 3, Vb: 0 }, { mode: 0, Vb: 1 }, { mode: 2, Vb: -1 }],
    okFn: function (rows) { var c = [0, 0, 0, 0]; rows.forEach(function (r) { c[Math.round(r.set.mode)]++; }); return rows.length >= 6 && (c[0] + c[1]) >= 2 && (c[2] + c[3]) >= 2; },
    graph: { x: function (r) { return r.set.Vb; }, y: function (r) { return Math.round(r.set.mode) === 0 || Math.round(r.set.mode) === 3 ? r.vmax : r.vmin; }, xlabel: 'Bias voltage (V)', ylabel: 'Clipping / clamping level (V)' },
    result: function (rows) {
      return { label: 'Diode forward drop V_f', value: mean(rows.map(vfOf)), unit: 'V', digits: 3, truth: p.Vf,
        note: 'The level at which the wave stops, less the bias: V_max - V_b for the positive clipper and the negative clamper, V_b - V_min for the others.' };
    },
    resultNote: 'Every clipping or clamping level sits one forward drop beyond the bias, on the side the diode points to; that is why the clippers and the clampers give the same V_f. The output peak-to-peak of a clamper equals the input\'s: it only shifts the wave. The few millivolts above V_f are the diode\'s slope resistance times its current.',
    chips: ['What is the difference between a clipper and a clamper?', 'Why does the clamping level follow the bias?', 'Why is V_f a little higher than 0.65 V?', 'Check my readings'],
    viva: [['A clamper changes a wave\'s', ['DC level', 'shape', 'frequency'], 0, 'It adds a DC level and keeps the shape.']] }; };
  function vfOf(r) { var m = Math.round(r.set.mode), vb = r.set.Vb; return (m === 0 || m === 3) ? r.vmax - vb : vb - r.vmin; }

  PLANS['sn-timer-555'] = function () { return {
    compName: 'NE555 timer board',
    wiring: 'NE555 on the breadboard with R1, R2 and the timing capacitor C (unknown) on a 9 V supply. As an astable, pin 2 is tied to pin 6; as a monostable R2 is not used and a trigger pulse goes to pin 2.',
    controls: [{ param: 'kind', label: 'Mode', short: 'MODE', unit: '', digits: 0, names: ['astable', 'monostable'], vals: [0, 1] },
      { param: 'R1', label: 'Resistor R1', short: 'R1', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [1000, 2200, 4700, 10000] },
      { param: 'R2', label: 'Resistor R2', short: 'R2', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [1000, 4700, 10000, 22000, 47000] }],
    art: function () {
      dip8(-0.02, -0.01, 'NE555'); var a = resistor(-0.1, -0.03, p.R1, 'R1'), b = resistor(-0.1, 0.02, p.R2, 'R2'); capacitor(0.05, -0.03, 0, 'C', 'el', true); battery(0.11, 0.02, '9 V');
      jumper([-0.02, -0.02], [-0.1, -0.03], 'yellow'); jumper([0.0, 0.0], [0.05, 0.0], 'blue');
      return function (q) { a.set(q.R1); b.set(q.R2); var mono = Math.round(q.kind) === 1; b.g.visible = !mono; b.label.visible = !mono; }; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), dt = t[0], k = Math.round(qq.kind), m = KN.measure(qq), marks = [];
      var lvl = 0.5 * qq.Vcc, r = cross(t[2], dt, lvl, true), f = cross(t[2], dt, lvl, false), i;
      if (k === 0) { for (i = 0; i < Math.min(2, r.length); i++) marks.push({ kind: 'v', t: r[i], color: YEL }); } else { if (r.length) marks.push({ kind: 'v', t: r[0], color: CYA }); if (f.length) marks.push({ kind: 'v', t: f[0], color: CYA }); }
      return k === 0 ? { dt: dt, ch: [{ y: t[2], color: YEL, name: 'OUT' }, { y: t[1], color: CYA, name: 'CAP' }], marks: marks }
        : { dt: dt, ch: [{ y: t[3], color: YEL, name: 'TRIG' }, { y: t[2], color: CYA, name: 'OUT' }], marks: marks }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); }), k = Math.round(q.kind);
      return k === 0 ? { lines: ['Period T = ' + eng(m.T, 's') + '   f = ' + eng(m.f, 'Hz'), 'High time = ' + eng(m.Thigh, 's'), 'Low time = ' + eng(m.Tlow, 's'), 'Duty cycle = ' + fmt(m.duty * 100, 1) + ' %'], row: { f: m.f, thigh: m.Thigh, tlow: m.Tlow, duty: m.duty, width: 0 } }
        : { lines: ['Output pulse width = ' + eng(m.width, 's'), 'Trigger: falling edge at pin 2'], row: { f: 0, thigh: 0, tlow: 0, duty: 0, width: m.width } }; },
    cols: [{ label: 'Mode', get: function (r) { return Math.round(r.set.kind) === 0 ? 'astable' : 'monostable'; } }, { label: 'R1', get: function (r) { return rLabel(r.set.R1); } },
      { label: 'R2', get: function (r) { return Math.round(r.set.kind) === 0 ? rLabel(r.set.R2) : '—'; } }, { label: 'f (Hz)', get: function (r) { return Math.round(r.set.kind) === 0 ? fmt(r.f, 1) : '—'; } },
      { label: 'Duty (%)', get: function (r) { return Math.round(r.set.kind) === 0 ? fmt(r.duty * 100, 1) : '—'; } }, { label: 'Width (ms)', get: function (r) { return Math.round(r.set.kind) === 1 ? fmt(r.width * 1000, 3) : '—'; } },
      { label: 'C found (µF)', get: function (r) { return fmt(cOf(r) * 1e6, 4); } }],
    need: 5,
    runs: [{ kind: 0, R1: 1000, R2: 10000 }, { kind: 0, R1: 4700, R2: 10000 }, { kind: 0, R1: 1000, R2: 22000 }, { kind: 0, R1: 2200, R2: 4700 }, { kind: 1, R1: 1000 }, { kind: 1, R1: 4700 }, { kind: 1, R1: 10000 }],
    okFn: function (rows) { var a = 0, m = 0; rows.forEach(function (r) { if (Math.round(r.set.kind) === 0) a++; else m++; }); return a >= 2 && m >= 2; },
    graph: { x: function (r) { return r.set.R1 / 1000; }, y: function (r) { return cOf(r) * 1e6; }, xlabel: 'R1 (kΩ)', ylabel: 'C found (µF)' },
    result: function (rows) {
      return { label: 'Timing capacitor C', value: mean(rows.map(cOf)) * 1e6, unit: 'µF', digits: 4, truth: p.C * 1e6,
        note: 'From the astable frequency C = 1.44/((R1 + 2 R2) f) and from the monostable width C = T/(1.1 R1); average of all ' + rows.length + ' readings.' };
    },
    resultNote: 'Both ways of using the 555 give the same capacitor, to within the scope\'s reading error: the astable from its frequency and the monostable from its pulse width. The 555 is therefore also a simple way to measure a capacitor.',
    chips: ['Why is the astable duty cycle above 50 %?', 'What does the trigger do in the monostable?', 'How is C found from each mode?', 'Check my readings'],
    viva: [['In the monostable the output pulse width is', ['1.1 R1 C', '0.693 R2 C', '1.44 / (R1 C)'], 0, 'The capacitor charges from 0 to 2/3 of the supply through R1.']] }; };
  function cOf(r) { return Math.round(r.set.kind) === 0 ? 1.44 / ((r.set.R1 + 2 * r.set.R2) * r.f) : r.width / (1.1 * r.set.R1); }

  PLANS['sn-ujt-oscillator'] = function () { return {
    compName: SAMPLE || 'UJT relaxation oscillator board',
    wiring: 'Capacitor C = 47 nF charges through the resistor R from the 9 V supply to the UJT emitter; base 2 goes to the supply through 330 ohm and base 1 to ground through 100 ohm. Channel 1 is on the capacitor.',
    controls: [{ param: 'R1', label: 'Charging resistor R', short: 'RESISTOR R', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [15000, 22000, 33000, 47000, 68000] }],
    art: function () { to92(-0.02, -0.01, 'UJT'); var a = resistor(-0.1, -0.03, p.R1, 'R'); capacitor(0.05, -0.03, p.C, 'C', 'ceramic'); resistor(0.0, 0.03, 330, 'RB2'); resistor(0.06, 0.03, 100, 'RB1'); battery(0.12, 0.02, '9 V');
      jumper([-0.02, -0.02], [-0.1, -0.03], 'yellow'); jumper([0.0, 0.0], [0.05, 0.0], 'blue'); return function (q) { a.set(q.R1); }; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), vc = t[1], hi = maxOf(vc), i0 = vc.indexOf(hi), lo = minOf(vc.slice(i0)), dt = t[0];
      return { dt: dt, ch: [{ y: vc, color: CYA, name: 'CAP' }], marks: [{ kind: 'h', ch: 0, y: hi }, { kind: 'h', ch: 0, y: lo }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); }), tr = PLANS_TRACE(q), vc = tr.ch[0].y, hi = maxOf(vc), lo = minOf(vc.slice(vc.indexOf(hi)));
      return { lines: ['Period T = ' + eng(m.T, 's') + '   f = ' + eng(m.f, 'Hz'), 'Peak V_p = ' + fmt(hi, 3) + ' V', 'Valley V_v = ' + fmt(lo, 3) + ' V', 'V_D taken as ' + fmt(p.Vd, 1) + ' V'],
        row: { T: m.T, f: m.f, vp: hi, vv: lo } }; },
    cols: [{ label: 'R', get: function (r) { return rLabel(r.set.R1); } }, { label: 'T (ms)', get: function (r) { return fmt(r.T * 1000, 3); } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 1); } },
      { label: 'V_p (V)', get: function (r) { return fmt(r.vp, 3); } }, { label: 'V_v (V)', get: function (r) { return fmt(r.vv, 3); } }, { label: 'η = (V_p - V_D)/V_bb', get: function (r) { return fmt((r.vp - p.Vd) / p.Vcc, 3); } }],
    need: 4,
    runs: [15000, 22000, 33000, 47000, 68000].map(function (v) { return { R1: v }; }),
    graph: { x: function (r) { return r.set.R1 / 1000; }, y: function (r) { return r.T * 1000; }, xlabel: 'R (kΩ)', ylabel: 'Period (ms)', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Intrinsic stand-off ratio η', value: mean(rows.map(function (r) { return (r.vp - p.Vd) / p.Vcc; })), unit: '', digits: 3, truth: p.eta,
        note: 'η = (V_p - V_D)/V_bb from the sawtooth peak on each reading; the period is proportional to R as T = R C ln((V_bb - V_v)/(V_bb - V_p)).' };
    },
    resultNote: 'The peak of the sawtooth is where the UJT fires, V_p = η V_bb + V_D, so the peak gives η directly. The period then follows from how long the capacitor takes to climb from the valley to that peak: it is proportional to R, and its logarithm is fixed by η and the supply.',
    chips: ['What does the UJT do at the peak?', 'Why is the period proportional to R?', 'How is η found from the peak?', 'Check my readings'],
    viva: [['A UJT fires when its emitter voltage reaches', ['η V_bb + V_D', 'V_bb / 2', 'zero'], 0, 'That is the peak point voltage.']] }; };
  function PLANS_TRACE(q) { return PL.trace(q); }

  var CE_FS = [10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000, 300000, 1000000, 3000000, 10000000];
  function ceVin() { return Math.round(p.stages) === 2 ? 0.0002 : 0.010; }
  PLANS['sn-ce-amplifier'] = function () {
    var two = Math.round(p.stages) === 2;
    return {
    compName: SAMPLE || (two ? 'Two-stage RC-coupled CE amplifier board' : 'Common-emitter amplifier board'),
    wiring: (two ? 'Two identical stages, the first coupled to the second through a 1 µF capacitor. ' : '') + 'BC547 with R1 = 47 kΩ, R2 = 10 kΩ, R_C = 2.2 kΩ, R_E = 680 Ω bypassed by 220 µF, 1 µF coupling capacitors, load R_L = ' + rLabel(p.RL) + ', V_CC = 12 V. Input ' + (two ? '0.2 mV (generator through a 1000:1 attenuator)' : '10 mV') + ' peak from a 50 ohm generator.',
    controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: function (f) { return f >= 1e6 ? (f / 1e6) + ' MHz' : f >= 1e3 ? (f / 1e3) + ' kHz' : f + ' Hz'; }, vals: CE_FS }],
    art: function () {
      var ql = to92(-0.06, -0.01, 'BC547'); resistor(-0.12, -0.04, p.R1, 'R1', true); resistor(-0.12, 0.03, p.R2, 'R2', true); resistor(-0.03, -0.045, p.Rc, 'RC'); resistor(-0.03, 0.035, p.Re, 'RE'); resistor(0.04, 0.0, p.RL, 'RL');
      capacitor(-0.09, -0.01, p.Cin, 'Cin', 'ceramic'); capacitor(0.0, 0.0, p.Cout, 'Cout', 'ceramic'); capacitor(0.01, 0.035, p.CE, 'CE', 'el'); battery(0.115, 0.03, '12 V');
      if (two) { to92(0.065, -0.04, 'BC547'); resistor(0.095, -0.015, p.Rc, 'RC2'); }
      jumper([-0.12, 0.0], [-0.09, -0.01], 'yellow'); jumper([-0.05, -0.01], [-0.03, -0.045], 'blue'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var n = 2400, f = qq.f, vin = ceVin(), A = KN.gain(qq, f), ph = KN.phase(qq, f) * Math.PI / 180, dt = 4 / f / n, a = [], b = [], i, wt;
      for (i = 0; i < n; i++) { wt = 2 * Math.PI * f * i * dt; a.push(vin * Math.sin(wt)); b.push(vin * A * Math.sin(wt + ph)); }
      return { dt: dt, ch: [{ y: a, color: YEL, name: 'IN' }, { y: b, color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 0, y: maxOf(a) }, { kind: 'h', ch: 1, y: maxOf(b) }, { kind: 'h', ch: 1, y: minOf(b) }] }; }); },
    meas: function (q) { var t = PLANS_TRACE(q), a = t.ch[0].y, b = t.ch[1].y, vi = maxOf(a) - minOf(a), vo = maxOf(b) - minOf(b), g = vo / vi, ph = KN.phase(q, q.f);
      return { lines: ['Input p-p = ' + eng(vi, 'V'), 'Output p-p = ' + eng(vo, 'V'), 'Gain = ' + fmt(g, 2) + '  (' + fmt(20 * ln10(g), 1) + ' dB)', 'Output ' + (Math.abs(ph) > 90 ? 'inverted' : 'in phase') + ', phase ' + fmt(ph, 1) + '°'],
        row: { f: q.f, vin: vi, vout: vo, gain: g, phase: ph } }; },
    cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'Vin p-p', get: function (r) { return eng(r.vin, 'V'); } }, { label: 'Vout p-p', get: function (r) { return eng(r.vout, 'V'); } },
      { label: 'Gain', get: function (r) { return fmt(r.gain, 2); } }, { label: 'Gain (dB)', get: function (r) { return fmt(20 * ln10(r.gain), 1); } }],
    need: 10,
    runs: CE_FS.map(function (f) { return { f: f }; }),
    graph: { x: function (r) { return ln10(r.f); }, y: function (r) { return 20 * ln10(r.gain); }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain (dB)' },
    result: function (rows) {
      var g = rows.map(function (r) { return r.gain; }), gm = maxOf(g), top = rows.filter(function (r) { return r.gain >= 0.99 * gm; }), amid = mean(top.map(function (r) { return r.gain; })), half = amid / Math.sqrt(2);
      var q = rows.slice().sort(function (a, b) { return a.f - b.f; }), fl = NaN, fh = NaN, i;
      for (i = 1; i < q.length; i++) { if (isNaN(fl) && q[i - 1].gain < half && q[i].gain >= half) fl = Math.pow(10, ln10(q[i - 1].f) + (ln10(q[i].f) - ln10(q[i - 1].f)) * (half - q[i - 1].gain) / (q[i].gain - q[i - 1].gain));
        if (!isNaN(fl) && isNaN(fh) && q[i - 1].gain >= half && q[i].gain < half) fh = Math.pow(10, ln10(q[i - 1].f) + (ln10(q[i].f) - ln10(q[i - 1].f)) * (q[i - 1].gain - half) / (q[i - 1].gain - q[i].gain)); }
      return { label: 'Mid-band voltage gain', value: amid, unit: '', digits: 1, truth: KN.measure(p).Amid,
        note: 'Average of the flat part of your table (' + fmt(20 * ln10(amid), 1) + ' dB); half-power frequencies about ' + eng(fl, 'Hz') + ' and ' + eng(fh, 'Hz') + ' by interpolation.' };
    },
    resultNote: 'The gain is flat between a lower corner set by the coupling and bypass capacitors and an upper corner set by the transistor\'s capacitances, enlarged by the Miller effect. In between, the amplifier inverts the signal and multiplies it by about g_m R_L\'. Reading the gain at ten or more frequencies on a log scale is what locates both corners.',
    chips: ['Why is the output inverted?', 'What sets the upper corner?', 'What is g_m here?', 'Check my readings'],
    viva: [['The mid-band gain of a common-emitter stage is about', ['- g_m times the collector load', 'the supply voltage', 'beta'], 0, 'A_v = - g_m (R_C || R_L) times the input divider.']] }; };

  PLANS['sn-am-modulation'] = function () { return {
    compName: 'Transistor amplitude modulator board',
    wiring: 'A 20 kHz, 2 V peak carrier and a 500 Hz message go to the modulator (a transistor stage with its collector tuned to the carrier). Channel 1 shows the message, channel 2 the modulated output.',
    controls: [{ param: 'Vm', label: 'Message amplitude', short: 'MESSAGE (V pk)', unit: 'V', digits: 1, vals: [0.4, 0.8, 1.2, 1.6, 2.0, 2.4] }],
    art: function () { to92(-0.04, -0.01, '2N2222'); coil(0.04, -0.03, 'L'); capacitor(0.04, 0.02, 0, 'C', 'ceramic'); resistor(-0.11, -0.03, 10000, 'RB'); resistor(-0.11, 0.03, 1000, 'RE'); capacitor(-0.07, 0.03, 1e-6, 'Cc', 'ceramic'); battery(0.11, 0.02, '12 V');
      jumper([-0.04, -0.02], [0.04, -0.03], 'yellow'); jumper([-0.12, 0.03], [-0.11, 0.0], 'blue'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), m = KN.measure(qq);
      return { dt: t[0], ch: [{ y: t[1], color: YEL, name: 'MSG' }, { y: t[2], color: CYA, name: 'AM' }], marks: [{ kind: 'h', ch: 1, y: m.Vmax }, { kind: 'h', ch: 1, y: m.Vmin }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Envelope maximum V_max = ' + fmt(m.Vmax, 3) + ' V', 'Envelope minimum V_min = ' + fmt(m.Vmin, 3) + ' V', 'm = (V_max - V_min)/(V_max + V_min) = ' + fmt(m.m, 3), 'Carrier V_c = (V_max + V_min)/2 = ' + fmt(m.Vc_est, 3) + ' V'],
        row: { vm: q.Vm, vmax: m.Vmax, vmin: m.Vmin, m: m.m } }; },
    cols: [{ label: 'Message (V)', get: function (r) { return fmt(r.vm, 1); } }, { label: 'V_max (V)', get: function (r) { return fmt(r.vmax, 3); } }, { label: 'V_min (V)', get: function (r) { return fmt(r.vmin, 3); } }, { label: 'm', get: function (r) { return fmt(r.m, 3); } }],
    need: 5,
    runs: [0.4, 0.8, 1.2, 1.6, 2.0, 2.4].map(function (v) { return { Vm: v }; }),
    graph: { x: function (r) { return r.vm; }, y: function (r) { return r.m; }, xlabel: 'Message amplitude (V)', ylabel: 'Modulation index m', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Modulator sensitivity k_a', value: origin(rows.map(function (r) { return [r.vm, r.m]; })), unit: '1/V', digits: 3, truth: p.ka,
        note: 'Slope of the modulation index against the message amplitude; the largest index here is ' + fmt(maxOf(rows.map(function (r) { return r.m; })), 2) + '.' };
    },
    resultNote: 'The modulation index grows in proportion to the message, so m against V_m is a straight line through the origin whose slope is the modulator\'s sensitivity. Beyond m = 1 the envelope would fold over and a simple detector could no longer recover the message.',
    chips: ['How is m read from the screen?', 'What happens above m = 1?', 'What does k_a mean?', 'Check my readings'],
    viva: [['If V_max = 3 V and V_min = 1 V, the modulation index is', ['0.5', '2', '0.33'], 0, '(3 - 1)/(3 + 1) = 0.5.']] }; };

  PLANS['sn-fm-modulation'] = function () { return {
    compName: 'Voltage-controlled oscillator FM generator board',
    wiring: 'The message (250 Hz) drives a varicap diode in the tank of a 20 kHz oscillator. Channel 1 shows the message, channel 2 the FM output. A zero-crossing frequency counter followed by a filter acts as the discriminator.',
    controls: [{ param: 'Vm', label: 'Message amplitude', short: 'MESSAGE (V pk)', unit: 'V', digits: 1, vals: [0.4, 0.8, 1.2, 1.6, 2.0, 2.4] }],
    art: function () { dip8(-0.04, -0.01, 'VCO'); diode(0.04, -0.03, 'VC'); coil(0.04, 0.02, 'L'); capacitor(0.1, -0.03, 0, 'C', 'ceramic'); resistor(-0.11, -0.03, 10000, 'R'); capacitor(-0.09, 0.03, 1e-6, 'Cc', 'ceramic'); battery(0.11, 0.03, '9 V');
      jumper([-0.04, -0.02], [0.04, -0.03], 'yellow'); jumper([-0.1, 0.03], [-0.11, 0.0], 'blue'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq);
      return { dt: t[0], ch: [{ y: t[1], color: YEL, name: 'MSG' }, { y: t[2], color: CYA, name: 'FM' }], marks: [] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Deviation = ' + eng(m.df, 'Hz') + '   beta = ' + fmt(m.beta, 2), 'Mean frequency = ' + eng(m.fc_est, 'Hz'), 'Carson bandwidth = ' + eng(m.bw, 'Hz'), 'Discriminator output = ' + fmt(m.Vrec, 3) + ' V peak'],
        row: { vm: q.Vm, df: m.df, beta: m.beta, vrec: m.Vrec } }; },
    cols: [{ label: 'Message (V)', get: function (r) { return fmt(r.vm, 1); } }, { label: 'Deviation (Hz)', get: function (r) { return fmt(r.df, 0); } }, { label: 'β', get: function (r) { return fmt(r.beta, 2); } }, { label: 'Discriminator (V)', get: function (r) { return fmt(r.vrec, 3); } }],
    need: 5,
    runs: [0.4, 0.8, 1.2, 1.6, 2.0, 2.4].map(function (v) { return { Vm: v }; }),
    graph: { x: function (r) { return r.vm; }, y: function (r) { return r.df; }, xlabel: 'Message amplitude (V)', ylabel: 'Deviation (Hz)', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Modulator sensitivity k_f', value: origin(rows.map(function (r) { return [r.vm, r.df]; })), unit: 'Hz/V', digits: 0, truth: p.kf,
        note: 'Slope of the deviation against the message amplitude.' };
    },
    resultNote: 'The frequency deviation is proportional to the message amplitude whatever the message frequency, so the points lie on a straight line through the origin; its slope is the modulator\'s sensitivity. The discriminator turns the frequency swing back into a voltage proportional to the message.',
    chips: ['How is the deviation read from the screen?', 'What is beta?', 'What does Carson\'s rule say?', 'Check my readings'],
    viva: [['In FM the deviation depends on', ['the message amplitude', 'the message frequency', 'the carrier amplitude'], 0, 'delta f = k_f V_m.']] }; };


  function opaDep(a, dt) {                       // where the slewing edge, extended back along its straight line, leaves the rail
    var out = a, lo = minOf(out), j = 0, sl;
    while (out[j] < lo + 1.0) j++;
    sl = (out[j + 1] - out[j]) / dt;
    return j * dt - (out[j] - lo) / sl;
  }
  PLANS['sn-opamp-comparator'] = function () { return {
    compName: 'Op-amp comparator board (LM741)',
    wiring: 'An LM741 on ±15 V with no feedback: the sine goes to the inverting input (pin 2) and the reference from a trimmer to the non-inverting input (pin 3). Channel 1 is the input, channel 2 the output.',
    controls: [{ param: 'Vref', label: 'Reference voltage', short: 'V REF', unit: 'V', digits: 1, vals: [-1, 0, 0.5, 1, 1.5, 2] },
      { param: 'Vp', label: 'Input amplitude (peak)', short: 'INPUT (V pk)', unit: 'V', digits: 1, vals: [2, 3] }],
    art: function () { dip8(-0.02, -0.01, 'LM741'); resistor(-0.11, -0.03, 10000, 'R'); resistor(-0.11, 0.03, 10000, 'RP'); battery(0.07, -0.03, '+15 V'); battery(0.07, 0.03, '-15 V'); battery(0.12, 0.0, 'VREF');
      jumper([-0.02, -0.02], [-0.11, -0.03], 'yellow'); jumper([0.0, 0.0], [0.07, 0.0], 'blue'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), a = t[1], o = t[2], dt = t[0], lo = minOf(o), hi = maxOf(o), sw = hi - lo, td = opaDep(o, dt);
      return { dt: dt, ch: [{ y: a, color: YEL, name: 'IN' }, { y: o, color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 0, y: qq.Vref, color: GRN }, { kind: 'v', t: td, color: CYA }, { kind: 'h', ch: 1, y: lo + 0.1 * sw }, { kind: 'h', ch: 1, y: lo + 0.9 * sw }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Edge leaves the rail when V_in = ' + fmt(m.trip, 3) + ' V (reference ' + fmt(q.Vref, 2) + ' V)', 'Output levels ' + fmt(m.vlo, 2) + ' V and ' + fmt(m.vhi, 2) + ' V', 'Slew rate (10-90 %) = ' + fmt(m.SR / 1e6, 3) + ' V/µs'],
        row: { trip: m.trip, sr: m.SR, vlo: m.vlo, vhi: m.vhi } }; },
    cols: [{ label: 'V_ref (V)', get: function (r) { return fmt(r.set.Vref, 1); } }, { label: 'Input pk (V)', get: function (r) { return fmt(r.set.Vp, 1); } }, { label: 'Trip point (V)', get: function (r) { return fmt(r.trip, 3); } },
      { label: 'Trip - V_ref (mV)', get: function (r) { return fmt((r.trip - r.set.Vref) * 1000, 1); } }, { label: 'Low / high (V)', get: function (r) { return fmt(r.vlo, 1) + ' / ' + fmt(r.vhi, 1); } }, { label: 'Slew (V/µs)', get: function (r) { return fmt(r.sr / 1e6, 3); } }],
    need: 5,
    runs: [{ Vref: -1, Vp: 2 }, { Vref: 0, Vp: 2 }, { Vref: 0.5, Vp: 2 }, { Vref: 1, Vp: 2 }, { Vref: 2, Vp: 3 }],
    graph: { x: function (r) { return r.set.Vref; }, y: function (r) { return r.trip; }, xlabel: 'Reference voltage (V)', ylabel: 'Trip point (V)', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Slew rate of the op-amp', value: mean(rows.map(function (r) { return r.sr / 1e6; })), unit: 'V/µs', digits: 3, truth: p.SR / 1e6,
        note: 'The 10 to 90 % swing of the output divided by the time between those two points; the trip point matched the reference to within ' + fmt(maxOf(rows.map(function (r) { return Math.abs(r.trip - r.set.Vref) * 1000; })), 1) + ' mV.' };
    },
    resultNote: 'With no feedback the op-amp is a comparator: the output sits at one rail or the other and swings across when the input passes the reference. With the reference at zero it is a zero-crossing detector. The trip point follows the reference (a gain of 200 000 means only microvolts of input are needed) but the swing is not instantaneous: the output can only slew at about half a volt per microsecond.',
    chips: ['What is a zero-crossing detector?', 'Why does the output sit at the rails?', 'What limits how fast the output switches?', 'Check my readings'],
    viva: [['A comparator\'s output is at', ['one of two rail voltages', 'the average of the inputs', 'zero'], 0, 'The huge gain saturates the output on either side of the threshold.']] }; };

  PLANS['sn-opamp-integrator'] = function () { return {
    compName: 'Op-amp integrator board (LM741)',
    wiring: 'Square wave through R = ' + rLabel(p.R) + ' to the inverting input of an LM741; feedback capacitor C (unknown) in parallel with a leakage resistor R_f = ' + rLabel(p.Rf) + '. Channel 1 is the input, channel 2 the output.',
    controls: [{ param: 'f', label: 'Square-wave frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, vals: [200, 500, 1000, 2000] }, { param: 'Vp', label: 'Square-wave amplitude', short: 'AMPLITUDE (V)', unit: 'V', digits: 2, vals: [0.1, 0.25, 0.5] }],
    art: function () { dip8(-0.02, -0.01, 'LM741'); resistor(-0.11, -0.03, p.R, 'R'); capacitor(0.05, -0.03, 0, 'C', 'ceramic', true); resistor(0.05, 0.03, p.Rf, 'Rf'); battery(0.12, 0.0, '±15 V');
      jumper([-0.02, -0.02], [-0.11, -0.03], 'yellow'); jumper([0.0, 0.0], [0.05, 0.0], 'blue'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), o = t[2];
      return { dt: t[0], ch: [{ y: t[1], color: YEL, name: 'IN' }, { y: o, color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: maxOf(o) }, { kind: 'h', ch: 1, y: minOf(o) }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Ramp slope = ' + fmt(m.slope / 1000, 3) + ' V/ms (first half-cycle)', 'Output p-p = ' + fmt(m.vpp, 3) + ' V', 'Input amplitude = ' + fmt(q.Vp, 2) + ' V'], row: { slope: m.slope, vpp: m.vpp } }; },
    cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.set.f, 0); } }, { label: 'V_in (V)', get: function (r) { return fmt(r.set.Vp, 2); } }, { label: 'Slope (V/ms)', get: function (r) { return fmt(r.slope / 1000, 3); } },
      { label: 'Output p-p (V)', get: function (r) { return fmt(r.vpp, 3); } }, { label: 'C = V/(R |slope|) (nF)', get: function (r) { return fmt(r.set.Vp / (p.R * Math.abs(r.slope)) * 1e9, 3); } }],
    need: 5,
    runs: [{ f: 200, Vp: 0.25 }, { f: 500, Vp: 0.5 }, { f: 1000, Vp: 0.5 }, { f: 2000, Vp: 0.5 }, { f: 1000, Vp: 0.25 }, { f: 500, Vp: 0.1 }],
    graph: { x: function (r) { return r.set.Vp; }, y: function (r) { return Math.abs(r.slope) / 1000; }, xlabel: 'Input amplitude (V)', ylabel: '|slope| (V/ms)', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Feedback capacitor C', value: mean(rows.map(function (r) { return r.set.Vp / (p.R * Math.abs(r.slope)); })) * 1e9, unit: 'nF', digits: 2, truth: p.C * 1e9,
        note: 'The output ramps at V_in/(R C), so C = V_in/(R |slope|); average over ' + rows.length + ' readings. The leakage resistor makes the slope a fraction of a percent low.' };
    },
    resultNote: 'A square wave through an integrator becomes a triangle: the output ramps down while the input is high and up while it is low, with slope V_in/(R C) and a peak-to-peak size V_in/(2 f R C). The leakage resistor keeps the output from drifting to a rail, at the price of a slight droop.',
    chips: ['Why does a square wave become a triangle?', 'What does the leakage resistor do?', 'How is C found from the slope?', 'Check my readings'],
    viva: [['The output of an ideal op-amp integrator is proportional to', ['the time integral of the input', 'the input', 'the derivative of the input'], 0, 'V_out = -(1/RC) times the integral of V_in.']] }; };

  PLANS['sn-opamp-differentiator'] = function () { return {
    compName: 'Op-amp differentiator board (LM741)',
    wiring: 'Triangle wave through the capacitor C (unknown) and a series resistor R_s = ' + rLabel(p.Rs) + ' to the inverting input of an LM741; feedback resistor R = ' + rLabel(p.R) + '. Channel 1 is the input, channel 2 the output.',
    controls: [{ param: 'f', label: 'Triangle-wave frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, vals: [200, 500, 1000, 2000] }, { param: 'Vp', label: 'Triangle-wave peak', short: 'PEAK (V)', unit: 'V', digits: 1, vals: [0.5, 1, 2] }],
    art: function () { dip8(-0.02, -0.01, 'LM741'); capacitor(-0.11, -0.03, 0, 'C', 'ceramic', true); resistor(-0.07, 0.03, p.Rs, 'Rs'); resistor(0.05, -0.03, p.R, 'R'); battery(0.12, 0.0, '±15 V');
      jumper([-0.02, -0.02], [-0.11, -0.03], 'yellow'); jumper([0.0, 0.0], [0.05, 0.0], 'blue'); return function () {}; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), o = t[2];
      return { dt: t[0], ch: [{ y: t[1], color: YEL, name: 'IN' }, { y: o, color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: maxOf(o) }, { kind: 'h', ch: 1, y: minOf(o) }] }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Output amplitude = ' + fmt(m.amp, 3) + ' V (flat top)', 'Input peak = ' + fmt(q.Vp, 1) + ' V at ' + eng(q.f, 'Hz')], row: { amp: m.amp } }; },
    cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.set.f, 0); } }, { label: 'V_in peak (V)', get: function (r) { return fmt(r.set.Vp, 1); } }, { label: 'Output amp (V)', get: function (r) { return fmt(r.amp, 3); } },
      { label: 'C = A/(4 V f R) (nF)', get: function (r) { return fmt(r.amp / (4 * r.set.Vp * r.set.f * p.R) * 1e9, 3); } }],
    need: 5,
    runs: [{ f: 500, Vp: 1 }, { f: 1000, Vp: 0.5 }, { f: 1000, Vp: 1 }, { f: 1000, Vp: 2 }, { f: 2000, Vp: 1 }, { f: 200, Vp: 2 }],
    graph: { x: function (r) { return 4 * r.set.Vp * r.set.f / 1000; }, y: function (r) { return r.amp; }, xlabel: '4 V f (kV/s)', ylabel: 'Output amplitude (V)', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Capacitor C', value: mean(rows.map(function (r) { return r.amp / (4 * r.set.Vp * r.set.f * p.R); })) * 1e9, unit: 'nF', digits: 2, truth: p.C * 1e9,
        note: 'A triangle of peak V and frequency f has slope 4 V f, so the output amplitude is R C · 4 V f; average over ' + rows.length + ' readings.' };
    },
    resultNote: 'A triangle through a differentiator becomes a square wave: the slope of a triangle is constant, so the output is constant, flipping sign with the slope. Its size is R C times the slope, 4 V f. The small series resistor keeps the high-frequency gain finite so the corners do not run into the rails or oscillate.',
    chips: ['Why does a triangle become a square wave?', 'What does the series resistor do?', 'How is C found from the amplitude?', 'Check my readings'],
    viva: [['The output of a differentiator is proportional to', ['the rate of change of the input', 'the input itself', 'the area under the input'], 0, 'V_out = -R C dV_in/dt.']] }; };


  PLANS['sn-transistor-astable'] = function () { return {
    compName: 'Transistor astable multivibrator board',
    wiring: 'Two BC547 transistors, each with a 1 kΩ collector resistor, cross-coupled through two equal capacitors C (unknown) and biased through R1 and R2 from 9 V. Channel 1 is on the collector of the first transistor, channel 2 on the base of the one that is charging.',
    controls: [{ param: 'R1', label: 'Resistor R1', short: 'R1', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [4700, 10000, 22000, 47000] }, { param: 'R2', label: 'Resistor R2', short: 'R2', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [4700, 10000, 22000, 47000] }],
    art: function () { to92(-0.07, -0.02, 'BC547'); to92(0.04, -0.02, 'BC547'); var a = resistor(-0.12, 0.03, p.R1, 'R1'), b = resistor(0.09, 0.03, p.R2, 'R2'); resistor(-0.06, 0.04, 1000, 'RC1'); resistor(0.03, 0.04, 1000, 'RC2');
      capacitor(-0.02, -0.04, 0, 'C1', 'ceramic', true); capacitor(0.0, 0.0, 0, 'C2', 'ceramic', true); battery(0.13, -0.02, '9 V');
      jumper([-0.07, -0.03], [0.04, -0.03], 'yellow'); jumper([-0.02, -0.01], [0.0, 0.01], 'blue'); return function (q) { a.set(q.R1); b.set(q.R2); }; },
    trace: function (q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), dt = t[0], lvl = 0.5 * qq.Vcc, r = cross(t[2], dt, lvl, true), fl = cross(t[2], dt, lvl, false), marks = [], i;
      for (i = 0; i < Math.min(2, r.length); i++) marks.push({ kind: 'v', t: r[i], color: YEL }); if (fl.length > 1) marks.push({ kind: 'v', t: fl[1], color: YEL });
      return { dt: dt, ch: [{ y: t[2], color: YEL, name: 'COLL' }, { y: t[1], color: CYA, name: 'BASE' }], marks: marks }; }); },
    meas: function (q) { var m = memo('ms', q, function (qq) { return KN.measure(qq); });
      return { lines: ['Period T = ' + eng(m.T, 's') + '   f = ' + eng(m.f, 'Hz'), 'High time = ' + eng(m.Thigh, 's') + '   low time = ' + eng(m.Tlow, 's'), 'Duty cycle = ' + fmt(m.duty * 100, 1) + ' %'],
        row: { f: m.f, thigh: m.Thigh, tlow: m.Tlow, duty: m.duty } }; },
    cols: [{ label: 'R1', get: function (r) { return rLabel(r.set.R1); } }, { label: 'R2', get: function (r) { return rLabel(r.set.R2); } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 1); } },
      { label: 'High (ms)', get: function (r) { return fmt(r.thigh * 1000, 3); } }, { label: 'Low (ms)', get: function (r) { return fmt(r.tlow * 1000, 3); } }, { label: 'Duty (%)', get: function (r) { return fmt(r.duty * 100, 1); } },
      { label: 'C = 1/(0.693 (R1 + R2) f) (nF)', get: function (r) { return fmt(1 / (0.693 * (r.set.R1 + r.set.R2) * r.f) * 1e9, 2); } }],
    need: 5,
    runs: [{ R1: 10000, R2: 10000 }, { R1: 10000, R2: 22000 }, { R1: 22000, R2: 10000 }, { R1: 47000, R2: 22000 }, { R1: 4700, R2: 47000 }, { R1: 22000, R2: 22000 }],
    graph: { x: function (r) { return (r.set.R1 + r.set.R2) / 1000; }, y: function (r) { return 1 / r.f * 1000; }, xlabel: 'R1 + R2 (kΩ)', ylabel: 'Period (ms)', line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      return { label: 'Capacitors C', value: mean(rows.map(function (r) { return 1 / (0.693 * (r.set.R1 + r.set.R2) * r.f); })) * 1e9, unit: 'nF', digits: 2, truth: p.C * 1e9,
        note: 'From f = 1/(0.693 (R1 + R2) C) at each setting; the duty cycle came out as R1/(R1 + R2) within ' + fmt(maxOf(rows.map(function (r) { return Math.abs(r.duty - r.set.R1 / (r.set.R1 + r.set.R2)) * 100; })), 1) + ' percentage points.' };
    },
    resultNote: 'Each transistor stays off for 0.693 times the resistor-capacitor product on its base, so the high time is 0.693 R1 C and the low time 0.693 R2 C. The period is their sum and the duty cycle R1/(R1 + R2). The model takes V_BE and V_CE(sat) as zero, which is a good approximation when the supply is much larger than 0.7 V.',
    chips: ['Why is each half-period 0.693 R C?', 'How is the duty cycle set?', 'How is C found?', 'Check my readings'],
    viva: [['The period of the astable multivibrator is', ['0.693 (R1 + R2) C', '1.1 R C', '2 π R C'], 0, 'Each half is 0.693 times its own R C.']] }; };

  var PL = (PLANS[BASE] || PLANS['sn-cro-measure'])();
  var CTRL = PL.controls;

  // =============================================================================================== control panel
  var gpTitle = L('FUNCTION GENERATOR + CIRCUIT SETTINGS', { w: 0.24, ratio: 0.08, color: '#1b1b1b', px: 1024 }); gpTitle.position.set(0, 0.092, 0.0605); gp.add(gpTitle);
  var NCT = CTRL.length, dials = [], lcds = [];
  CTRL.forEach(function (c, i) {
    var x = (i - (NCT - 1) / 2) * 0.072 - 0.02;
    var lb = L(c.short, { w: 0.064, ratio: 0.16, color: '#1b1b1b' }); lb.position.set(x, 0.074, 0.0605); gp.add(lb);
    dials.push(dialKnob(gp, x, 0.05, 0.0605, 0.014));
    var tex = S.liveTex(256, 72), m = new T.Mesh(new T.PlaneGeometry(0.062, 0.0174), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); m.position.set(x, 0.02, 0.0608); gp.add(m);
    lcds.push({ tex: tex, last: '' });
  });
  var rockerBase = S.mesh(new T.BoxGeometry(0.028, 0.02, 0.006), M.black); rockerBase.position.set(0.1, 0.045, 0.0605); gp.add(rockerBase);
  var rocker = S.mesh(new T.BoxGeometry(0.02, 0.014, 0.01), new T.MeshStandardMaterial({ color: 0xd9d9d6, roughness: 0.4 })); rocker.position.set(0.1, 0.045, 0.065); gp.add(rocker);
  var pilotM = new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.0055, 14, 10), pilotM, false); pilot.position.set(0.1, 0.07, 0.0625); gp.add(pilot);
  var pwl = L('POWER', { w: 0.03, ratio: 0.26, color: '#1b1b1b' }); pwl.position.set(0.1, 0.022, 0.0605); gp.add(pwl);

  // =============================================================================================== oscilloscope
  var SCX = 0.06, SCZ = -0.42, SW = 0.5, SD = 0.26, SH = 0.3;
  var sco = new T.Group(); S.scene.add(sco); sco.position.set(SCX, 0, SCZ);
  var sBody = S.rounded(SW, SD, SH, 0.012, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); sBody.rotation.x = -Math.PI / 2; sBody.position.y = SH / 2; sco.add(sBody);
  S.contact(SW + 0.08, SD + 0.08, SCX, SCZ, 0.5);
  var bez = S.mesh(new T.BoxGeometry(0.39, 0.292, 0.006), M.grey); bez.position.set(-0.05, 0.15, SD / 2 + 0.001); sco.add(bez);
  var scrTex = S.liveTex(1024, 768), scr = new T.Mesh(new T.PlaneGeometry(0.36, 0.27), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scr.position.set(-0.05, 0.15, SD / 2 + 0.0045); sco.add(scr);
  var sk1 = dialKnob(sco, 0.2, 0.225, SD / 2, 0.014), sk2 = dialKnob(sco, 0.2, 0.17, SD / 2, 0.014);
  var curBtn = S.mesh(new T.BoxGeometry(0.05, 0.02, 0.01), new T.MeshStandardMaterial({ color: 0x3a4f6e, roughness: 0.4 })); curBtn.position.set(0.2, 0.1, SD / 2 + 0.003); sco.add(curBtn);
  var curL = L('CURSORS', { w: 0.046, ratio: 0.28, color: '#f2f2f2' }); curL.position.set(0.2, 0.1, SD / 2 + 0.0085); sco.add(curL);
  var curLed = S.mesh(new T.SphereGeometry(0.0035, 10, 8), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }), false); curLed.position.set(0.228, 0.1, SD / 2 + 0.0095); sco.add(curLed);
  var sLbl = L('OSCILLOSCOPE · 2 CHANNEL · 100 MHz', { w: 0.26, ratio: 0.06, color: '#1b1b1b', px: 1024 }); sLbl.position.set(-0.05, 0.296, SD / 2 + 0.0005); sco.add(sLbl);
  var chL1 = L('CH1', { w: 0.03, ratio: 0.3, color: '#6b5a00' }); chL1.position.set(0.2, 0.26, SD / 2 + 0.0008); sco.add(chL1);
  var chL2 = L('CH2', { w: 0.03, ratio: 0.3, color: '#006a80' }); chL2.position.set(0.2, 0.205, SD / 2 + 0.0008); sco.add(chL2);

  function niceStep(v) { var e = Math.pow(10, Math.floor(ln10(v))), f = v / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e; }
  var st = { power: false, checked: false, cur: false, set: CTRL.map(function (c) { return c.vals[0]; }), idx: CTRL.map(function () { return 0; }) };
  function over() { var o = {}; CTRL.forEach(function (c, i) { o[c.param] = st.set[i]; }); return o; }
  function qNow() { return assign(p, over()); }
  function drawScope(cx, w, h) {
    cx.fillStyle = '#04100a'; cx.fillRect(0, 0, w, h);
    var PL0 = 14, PT = 14, W = w - 28, H = h - 150, i;
    cx.strokeStyle = 'rgba(120,220,150,.22)'; cx.lineWidth = 1;
    for (i = 0; i <= 10; i++) { cx.beginPath(); cx.moveTo(PL0 + W * i / 10, PT); cx.lineTo(PL0 + W * i / 10, PT + H); cx.stroke(); }
    for (i = 0; i <= 8; i++) { cx.beginPath(); cx.moveTo(PL0, PT + H * i / 8); cx.lineTo(PL0 + W, PT + H * i / 8); cx.stroke(); }
    cx.strokeStyle = 'rgba(120,220,150,.5)'; cx.beginPath(); cx.moveTo(PL0, PT + H / 2); cx.lineTo(PL0 + W, PT + H / 2); cx.stroke();
    cx.font = '600 34px "JetBrains Mono", monospace'; cx.textAlign = 'center';
    if (!st.power) { cx.fillStyle = '#4d8f6a'; cx.fillText('POWER OFF', w / 2, h / 2); return; }
    var q = qNow(), tr = PL.trace(q), N = tr.ch[0].y.length, spanT = tr.dt * N, stride = Math.max(1, Math.floor(N / 1500)), vdivs = [];
    tr.ch.forEach(function (c) { var mx = Math.max(Math.abs(maxOf(c.y)), Math.abs(minOf(c.y)), 1e-12); vdivs.push(niceStep(mx / 3.2)); });
    function X(t) { return PL0 + W * t / spanT; }
    function Yc(v, k) { return PT + H / 2 - v / vdivs[k] * (H / 8); }
    tr.marks && st.cur && tr.marks.forEach(function (m) {
      cx.setLineDash([8, 6]); cx.lineWidth = 2; cx.strokeStyle = m.color || '#ffffff';
      cx.beginPath();
      if (m.kind === 'v') { cx.moveTo(X(m.t), PT); cx.lineTo(X(m.t), PT + H); } else { var yy = Yc(m.y, m.ch || 0); cx.moveTo(PL0, yy); cx.lineTo(PL0 + W, yy); }
      cx.stroke(); cx.setLineDash([]);
    });
    tr.ch.forEach(function (c, k) {
      cx.strokeStyle = c.color; cx.lineWidth = 4; cx.beginPath();
      for (var j = 0; j < N; j += stride) { var px = X(j * tr.dt), py = Yc(c.y[j], k); if (j === 0) cx.moveTo(px, py); else cx.lineTo(px, py); }
      cx.stroke();
      cx.fillStyle = c.color; cx.beginPath(); var gy = PT + H / 2; cx.moveTo(PL0, gy - 9); cx.lineTo(PL0 + 14, gy); cx.lineTo(PL0, gy + 9); cx.fill();
    });
    cx.textAlign = 'left'; cx.font = '700 30px "JetBrains Mono", monospace';
    tr.ch.forEach(function (c, k) { cx.fillStyle = c.color; cx.fillText(c.name + ' ' + eng(vdivs[k], 'V') + '/div', PL0 + 6 + k * 330, h - 100); });
    cx.fillStyle = '#9fe0b8'; cx.fillText(eng(spanT / 10, 's') + '/div', PL0 + 6 + tr.ch.length * 330, h - 100);
    cx.font = '600 26px "JetBrains Mono", monospace';
    if (st.cur) { var ln = PL.meas(q).lines; cx.fillStyle = '#e8fff1'; cx.fillText(ln[0], PL0 + 6, h - 62); if (ln.length > 1) cx.fillText(ln[1], PL0 + 6, h - 34); if (ln.length > 2) cx.fillText(ln.slice(2).join('  '), PL0 + 6, h - 8); }
    else { cx.fillStyle = '#6fa88a'; cx.fillText('CURSORS OFF  (tap CURSORS to measure)', PL0 + 6, h - 50); }
  }
  var scopeKey = '';
  function paintScope() {
    var k = JSON.stringify(over()) + st.power + st.cur;
    if (k === scopeKey) return;
    scopeKey = k; scrTex.draw(drawScope);
  }

  // ---------- the circuit on the board follows the dials
  var ART = PL.art(), artKey = '';
  function artSync() { var k = JSON.stringify(over()); if (k === artKey) return; artKey = k; ART(qNow()); }

  // ---------- readouts on the control panel
  function ctrlTxt(i, v) { var c = CTRL[i]; if (c.names) return c.names[Math.round(v)]; if (c.fmtv) return c.fmtv(v); return fmt(v, c.digits) + (c.unit ? ' ' + c.unit : ''); }
  function dialAngle(i, idx) { return 2.3 - 4.6 * idx / Math.max(1, CTRL[i].vals.length - 1); }
  function setLook() {
    CTRL.forEach(function (c, i) {
      dials[i].rotation.z = dialAngle(i, st.idx[i]);
      var txt = ctrlTxt(i, st.set[i]);
      if (lcds[i].last !== txt) { lcds[i].last = txt; lcds[i].tex.draw(function (cx, w, h) { cx.fillStyle = '#10181a'; cx.fillRect(0, 0, w, h); cx.fillStyle = '#9ff0d2'; cx.font = '700 38px "JetBrains Mono", monospace'; cx.textAlign = 'center'; cx.fillText(txt, w / 2, 50, w - 10); }); }
    });
    pilotM.emissive.setHex(st.power ? 0x22ff55 : 0x000000); pilotM.color.setHex(st.power ? 0x38c25e : 0x331111);
    rocker.rotation.x = st.power ? -0.3 : 0.3;
    curLed.material.emissive.setHex(st.cur ? 0xffcc33 : 0x000000); curLed.material.color.setHex(st.cur ? 0xffcc33 : 0x331111);
  }
  setLook(); artSync();

  // ---------- wiring: generator and probes
  S.wire([[GPX + 0.1, 0.03, GPZ + 0.065], [GPX + 0.2, 0.04, -0.1], [BBX - 0.15, 0.03, BBZ + 0.03]], 'red');
  S.wire([[SCX - 0.2, 0.035, SCZ + 0.14], [SCX - 0.25, 0.06, -0.12], [BBX + 0.12, 0.035, BBZ + 0.02]], 'yellow');
  S.wire([[SCX - 0.15, 0.035, SCZ + 0.14], [SCX - 0.2, 0.05, -0.1], [BBX + 0.15, 0.03, BBZ + 0.05]], 'blue');

  S.addApparatus('board', BB, PL.compName, PL.wiring);
  S.addApparatus('panel', gp, 'Generator and circuit settings', 'The hand turns these dials one at a time; each dial\'s small display shows its present setting. The POWER rocker switches the bench supply on.');
  S.addApparatus('scope', sco, 'Two-channel oscilloscope', 'The screen is drawn from the circuit\'s own sampled waveforms. CURSORS switches on the markers and the readout line at the foot of the screen.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard('Scope reading'), hudS = S.hudCard('Settings');

  // =============================================================================================== human actions
  function dialFront(i) { return wpos(gp, (i - (NCT - 1) / 2) * 0.072 - 0.02, 0.05, 0.072); }
  function turnTo(i, value) {
    var c = CTRL[i];
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var j = 0, best = 1e30, k;
    for (k = 0; k < c.vals.length; k++) if (Math.abs(c.vals[k] - value) < best) { best = Math.abs(c.vals[k] - value); j = k; }
    if (j === st.idx[i] && st.set[i] === c.vals[j]) return Promise.resolve();
    var i0 = st.idx[i], pt = dialFront(i);
    return S.hand.pinchMove(pt, function () { return pt; }, function (kk) {
      st.set[i] = kk >= 1 ? c.vals[j] : c.vals[i0] + (c.vals[j] - c.vals[i0]) * kk; dials[i].rotation.z = dialAngle(i, i0 + (j - i0) * kk); artSync();
    }, { mode: 'front', ms: 360 + 180 * Math.min(3, Math.abs(j - i0)), reachMs: 500 })
      .then(function () { st.idx[i] = j; st.set[i] = c.vals[j]; setLook(); artSync(); paintScope(); S.render(); });
  }
  function togglePower(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () {
      st.power = on; setLook(); paintScope(); S.click(900, 0.05);
      S.say(on ? 'Power on. The pilot lamp is lit and the trace appears on the scope.' : 'Power off.');
      S.render();
    });
  }
  function toggleCursors(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!st.power) { S.say('Switch the power on first.'); return Promise.resolve(); }
    if (on === st.cur) return Promise.resolve();
    return S.hand.tap(curBtn, 'front').then(function () {
      st.cur = on; setLook(); paintScope(); S.click(700, 0.05);
      S.say(on ? 'Cursors on: the markers show where the readings are taken and the readout is at the foot of the screen.' : 'Cursors off.');
      S.render();
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return; }
    if (!st.power) { S.say('Switch the power on first.'); return; }
    if (!st.cur) { S.say('Switch the cursors on first: they place the markers the readings are taken from.'); return; }
    var key = JSON.stringify(over()), i;
    for (i = 0; i < S.rows.length; i++) if (JSON.stringify(S.rows[i].set) === key) { S.say('You already have a reading at these settings. Turn a dial to new ones.'); return; }
    var m = PL.meas(qNow()), row = assign({ set: over() }, m.row);
    S.addRow(row);
    S.say('Written in your record book: ' + m.lines[0] + '.');
  }
  function enough() { return S.rows.length >= PL.need && (!PL.okFn || PL.okFn(S.rows)); }
  var FORMULA = { 'sn-cro-measure': 'tan φ = 2π f R C', 'sn-cro-pulse': 't_r = 2.197 R C,   t_d = 0.693 R C', 'sn-waveshaper': 'clip level = V_b ± V_f',
    'sn-timer-555': 'f = 1.44 / ((R1 + 2 R2) C),   T = 1.1 R1 C', 'sn-ujt-oscillator': 'V_p = η V_bb + V_D,   T = R C ln((V_bb − V_v)/(V_bb − V_p))',
    'sn-ce-amplifier': 'A_v = − g_m (R_C ∥ R_L) · R_in/(R_s + R_in)', 'sn-transistor-astable': 'f = 1 / (0.693 (R1 + R2) C),   duty = R1/(R1 + R2)', 'sn-opamp-comparator': 'trip when V_in = V_ref,   SR = ΔV / Δt', 'sn-opamp-integrator': 'V_out = −(1/RC) ∫ V_in dt', 'sn-opamp-differentiator': 'V_out = −R C dV_in/dt = −4 R C V f (triangle)', 'sn-am-modulation': 'm = (V_max − V_min)/(V_max + V_min) = k_a V_m', 'sn-fm-modulation': 'Δf = k_f V_m,   β = Δf / f_m' };
  function liveLine() { return PL.meas(qNow()).lines[0]; }
  function ctrlLine() { return CTRL.map(function (c, i) { return c.label + ': ' + ctrlTxt(i, st.set[i]); }).join('  ·  '); }

  return {
    camera: { pos: [-0.06, 0.6, 0.98], look: [-0.06, 0.1, -0.2] },
    views: {
      board: [[0.06, 0.3, 0.3], [0.06, 0.02, -0.1]], panel: [[-0.44, 0.22, 0.2], [-0.44, 0.05, -0.24]], scope: [[0.0, 0.26, 0.4], [0.0, 0.15, -0.4]],
      bench: [[-0.06, 0.6, 0.98], [-0.06, 0.1, -0.2]], book: [[-0.55, 0.44, 0.52], [-0.62, 0.0, 0.08]],
    },
    theory: {
      principle: S.lab.theory, formula: FORMULA[BASE] || '',
      formulaNote: 'The scope screen is drawn from the lab\'s own kernel; every reading is taken on the sampled waveform.' + (SAMPLE ? ' This specimen: ' + SAMPLE + '.' : ''),
      more: ['How it is wired: ' + PL.wiring],
      precautions: S.lab.safety + ' Switch the power off before changing a connection.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title, at: [-0.66, 0.1, 0.12],
      lines: ['Aim: ' + S.lab.aim, PL.wiring, 'Instrument: two-channel oscilloscope with cursors.', 'Precautions: power off before changing a connection; one dial changed at a time.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }].concat(PL.cols.map(function (c) { return { label: c.label, get: function (r, i) { return c.get(r, i, S.rows); } }; })),
    },
    graph: PL.graph,
    result: function (rows) { return rows.length < 2 ? null : PL.result(rows); },
    tol: 0.03,
    resultNote: PL.resultNote,
    chips: PL.chips,
    viva: PL.viva,
    askState: function () {
      var out = { power_on: st.power, cursors_on: st.cur, readings_taken: S.rows.length, set_up: PL.wiring, specimen: SAMPLE || PL.compName };
      CTRL.forEach(function (c, i) { out[c.label] = ctrlTxt(i, st.set[i]); });
      if (st.power) out.scope_reading = PL.meas(qNow()).lines.join('; ');
      return out;
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Check the circuit and switch on');
          u.p(PL.wiring);
          u.task('1. Check the circuit on the board', st.checked, st.checked ? 'Parts and connections checked' : 'Look at the board and the probes')
            .add(u.button(st.checked ? 'Checked' : 'Check the circuit', function () { st.checked = true; S.focus('board'); S.say(PL.compName + '. ' + PL.wiring); S.render(); }, !st.checked, st.checked));
          u.task('2. Switch the power on', st.power, st.power ? 'Power on; the trace is on the screen' : 'The hand presses the POWER rocker')
            .add(u.row(u.button(st.power ? 'Switch off' : 'Switch on', function () { S.focus('panel'); togglePower(!st.power); }, !st.power, S.hand.busy)));
          u.note('A circuit is checked before it is powered, never after. Keep the probe ground clips on the circuit\'s common point.');
          u.next('Next: take readings', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return togglePower(true); } },
      { id: 'measure', title: 'Measure', view: 'scope', render: function (u) {
          u.h2('Set the dials and measure on the scope');
          u.p('The hand turns each dial to the setting you choose; switch the cursors on, read the screen, then record. At least ' + PL.need + ' readings are needed.');
          CTRL.forEach(function (c, i) {
            u.slider(c.label, 0, c.vals.length - 1, 1, function () { return st.idx[i]; }, function (k) { turnTo(i, c.vals[k]); }, '', 0);
            u.note(c.label + ' is now ' + ctrlTxt(i, st.set[i]));
          });
          u.row(u.button(st.cur ? 'Cursors off' : 'Cursors on', function () { S.focus('scope'); toggleCursors(!st.cur); }, !st.cur, S.hand.busy),
            u.button('Record the readings', function () { record(); }, true, S.hand.busy));
          u.live(function () { return st.cur ? liveLine() : 'Cursors are off: switch them on to read the screen'; });
          u.h3('Observation table'); u.table();
          if (!enough()) u.p(S.rows.length + ' of at least ' + PL.need + ' readings recorded' + (PL.okFn ? ' (the set must also cover every mode of the experiment)' : '') + '.');
          u.next('Next: plot and work out the result', enough());
        },
        ok: function () { return enough(); },
        auto: function () {
          return toggleCursors(true).then(function () {
            return PL.runs.reduce(function (pr, run) {
              return pr.then(function () {
                var chain = Promise.resolve();
                CTRL.forEach(function (c, i) { if (run[c.param] !== undefined) chain = chain.then(function () { return turnTo(i, run[c.param]); }); });
                return chain.then(function () { record(); });
              });
            }, Promise.resolve());
          });
        } },
    ],

    tick: function () {
      artSync(); paintScope();
      hudR.set(st.power && st.cur ? liveLine() : st.power ? 'cursors off' : 'off');
      hudS.set(ctrlLine());
    },
  };
});
