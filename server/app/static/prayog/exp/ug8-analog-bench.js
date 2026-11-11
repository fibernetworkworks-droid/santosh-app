/* Prayogshala studio rig `ug8-analog-bench`: ONE analog electronics bench for the wave-8 B.Sc. set-ups of
   app/prayog/labs/ug_analog_w8.py. A solderless breadboard whose parts follow the lab, a bench supply / function
   generator panel (the circuit's settings as dials the hand turns, with a POWER rocker), two digital multimeters and a
   two-channel digital storage scope. The scope shows either the SAMPLED waveforms of the lab's own kernel
   (packs/ug_analog_w8.js) or, for a DC characteristic, an X-Y plot of the readings taken so far. Every number on a
   meter, on the screen and in the table comes from the kernel: bisection, scanning, a DFT, an RK4 run or a SAR loop;
   nothing is typed in. The circuit on the board changes with the lab; the bench, the hand actions and the procedure
   do not. Low voltages only. */
HoolaStudio.define('ug8-analog-bench', function (S) {
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

  // ---------- more parts for this bench
  function ledPart(x, z, color, tag) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY, z);
    var col = new T.Color(color);
    var mat = new T.MeshStandardMaterial({ color: col.clone().multiplyScalar(0.55), emissive: 0x000000, roughness: 0.25, transparent: true, opacity: 0.92 });
    var body = S.mesh(new T.CylinderGeometry(0.0025, 0.0025, 0.004, 18), mat); body.position.y = 0.004; g.add(body);
    var dome = S.mesh(new T.SphereGeometry(0.0025, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), mat); dome.position.y = 0.006; g.add(dome);
    [-1, 1].forEach(function (sg) { var pin = S.mesh(new T.CylinderGeometry(0.0003, 0.0003, 0.006, 8), M.chrome, false); pin.position.set(sg * 0.0012, 0.0, 0); g.add(pin); });
    if (tag) { var lb = L(tag, { w: 0.03, ratio: 0.3, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + 0.011); BB.add(lb); }
    var o = { g: g, last: -1 };
    o.set = function (k) { k = clamp(k, 0, 1); if (Math.abs(k - o.last) < 0.01) return; o.last = k; mat.emissive.copy(col).multiplyScalar(1.6 * k); };
    parts.push(o); return o;
  }
  function ledBar(x, z, n, color) { var out = [], i; for (i = 0; i < n; i++) out.push(ledPart(x + (i - (n - 1) / 2) * 0.009, z, color, i === 0 ? 'MSB' : i === n - 1 ? 'LSB' : '')); return { set: function (code) { for (var j = 0; j < n; j++) out[j].set((code >> (n - 1 - j)) & 1); } }; }
  function switchRow(x, z, n) {
    var g = new T.Group(); BB.add(g); g.position.set(x, PY, z);
    var body = S.rounded(0.0105 * n, 0.012, 0.005, 0.0008, new T.MeshStandardMaterial({ color: 0xb42a2a, roughness: 0.45 })); body.rotation.x = -Math.PI / 2; body.position.y = 0.0025; g.add(body);
    var levers = [], i;
    for (i = 0; i < n; i++) { var lv = S.mesh(new T.BoxGeometry(0.004, 0.0025, 0.004), M.white); lv.position.set((i - (n - 1) / 2) * 0.0105, 0.0058, 0.002); g.add(lv); levers.push(lv); }
    var lb = L('D3 D2 D1 D0', { w: 0.044, ratio: 0.2, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, BT + 0.0008, z + 0.014); BB.add(lb);
    parts.push({ g: g });
    return { set: function (code) { for (var j = 0; j < n; j++) levers[j].position.z = ((code >> (n - 1 - j)) & 1) ? -0.003 : 0.003; } };
  }
  function cable(z, color, thick, name) {
    var c = S.mesh(new T.CylinderGeometry(thick, thick, 0.3, 16), new T.MeshStandardMaterial({ color: color, roughness: 0.55 })); c.rotation.z = Math.PI / 2; c.position.set(0, PY + thick, z); BB.add(c);
    var lb = L(name, { w: 0.07, ratio: 0.16, color: '#3d3528', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(0.12, BT + 0.0008, z + thick + 0.006); BB.add(lb);
    parts.push({ g: c }); return c;
  }
  function boxPart(w, h, d, x, z, color, text) {
    var b = S.rounded(w, d, h, 0.004, new T.MeshStandardMaterial({ color: color, roughness: 0.5, metalness: 0.1 })); b.rotation.x = -Math.PI / 2; b.position.set(x, h / 2, z); S.scene.add(b); S.contact(w + 0.04, d + 0.04, x, z, 0.45);
    if (text) { var lb = L(text, { w: w * 0.9, ratio: 0.2, color: '#f2f2f2', weight: 700 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, h + 0.0006, z); S.scene.add(lb); }
    return b;
  }
  function bath(x, z) {
    var bk = S.beaker(0.05, 0.11, [x, 0, z], 0x9fd0e6, 0.7); S.contact(0.14, 0.14, x, z, 0.5);
    var th = S.thermometer({ len: 0.2, min: 0, max: 100, pos: [x + 0.022, 0.02, z + 0.012], value: p.Ta || 25 });
    var coil = S.mesh(new T.TorusGeometry(0.022, 0.003, 10, 30), M.copper); coil.rotation.x = Math.PI / 2; coil.position.set(x, 0.03, z); S.scene.add(coil);
    var stat = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.15, 14), M.chrome); stat.position.set(x - 0.022, 0.08, z - 0.01); S.scene.add(stat);
    var head = boxPart(0.05, 0.03, 0.04, x - 0.07, z - 0.02, 0x3a4f6e, 'THERMOSTAT');
    return { bk: bk, th: th, head: head };
  }
  function dmm(x, z, title) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var body = S.rounded(0.11, 0.15, 0.035, 0.008, new T.MeshStandardMaterial({ color: 0xe3b81e, roughness: 0.5 })); body.rotation.x = -Math.PI / 2 + 0.35; body.position.set(0, 0.03, 0); g.add(body);
    var face = new T.Group(); face.rotation.x = -Math.PI / 2 + 0.35; face.position.set(0, 0.03, 0); g.add(face);
    var tex = S.liveTex(512, 200), lcd = new T.Mesh(new T.PlaneGeometry(0.09, 0.035), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); lcd.position.set(0, 0.042, 0.0182); face.add(lcd);
    var tl = L(title, { w: 0.09, ratio: 0.14, color: '#1b1b1b' }); tl.position.set(0, 0.066, 0.0181); face.add(tl);
    var kb = S.mesh(new T.CylinderGeometry(0.018, 0.019, 0.008, 28), M.black); kb.rotation.x = Math.PI / 2; kb.position.set(0, -0.012, 0.0185); face.add(kb);
    [-0.03, 0, 0.03].forEach(function (dx, i) { var j = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.006, 14), i === 0 ? M.red || M.black : M.black); j.rotation.x = Math.PI / 2; j.position.set(dx, -0.055, 0.019); face.add(j); });
    S.contact(0.14, 0.18, x, z, 0.5);
    var last = '';
    return { g: g, set: function (name, text) { var k = name + '|' + text; if (k === last) return; last = k;
      tex.draw(function (cx, w, h) { cx.fillStyle = '#c9d4b8'; cx.fillRect(0, 0, w, h); cx.fillStyle = '#20261c'; cx.textAlign = 'left'; cx.font = '600 34px "Public Sans", sans-serif'; cx.fillText(name, 14, 44, w - 28);
        cx.textAlign = 'right'; cx.font = '700 86px "JetBrains Mono", monospace'; cx.fillText(text, w - 14, 160, w - 28); }); } };
  }

  // =============================================================================================== the lab's plan
  var PLANS = {};
  var YEL = '#ffe45e', CYA = '#64e3ff', GRN = '#8dff9b';
  function ln10(x) { return Math.log(x) / Math.LN10; }
  function rng(a, b, s) { var o = [], v; for (v = a; v <= b + s * 1e-6; v += s) o.push(Math.round(v * 1e6) / 1e6); return o; }
  function sig3(v) { return Number(v.toPrecision(3)); }
  function fLabel(f) { return f >= 1e6 ? sig3(f / 1e6) + ' MHz' : f >= 1e3 ? sig3(f / 1e3) + ' kHz' : sig3(f) + ' Hz'; }
  function sineTrace(f, amps, phs, cycles) { var n = NS, dt = cycles / f / n, out = amps.map(function () { return []; }), i, k, wt;
    for (i = 0; i < n; i++) { wt = 2 * Math.PI * f * i * dt; for (k = 0; k < amps.length; k++) out[k].push(amps[k] * Math.sin(wt + (phs[k] || 0))); } return { dt: dt, ys: out }; }
  var NS = 1200;
  function xyRows(fx, fy) { return S.rows.map(function (r) { return [fx(r), fy(r)]; }); }
  function interpCross(pts, level, logx) {        // first crossing of y = level along the x-sorted points
    var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; }), i, a, b, xa, xb;
    for (i = 1; i < q.length; i++) { a = q[i - 1]; b = q[i]; if ((a[1] - level) * (b[1] - level) <= 0 && a[1] !== b[1]) {
      xa = logx ? ln10(a[0]) : a[0]; xb = logx ? ln10(b[0]) : b[0]; var x = xa + (xb - xa) * (level - a[1]) / (b[1] - a[1]); return logx ? Math.pow(10, x) : x; } }
    return NaN;
  }
  function crossings(pts, level) { var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; }), out = [], i, a, b;
    for (i = 1; i < q.length; i++) { a = q[i - 1]; b = q[i]; if ((a[1] - level) * (b[1] - level) < 0) out.push(Math.pow(10, ln10(a[0]) + (ln10(b[0]) - ln10(a[0])) * (level - a[1]) / (b[1] - a[1]))); }
    return out; }
  function ohm(r) { return rLabel(r); }

  // ---------------------------------------------------------------- diodes (p-n, Boltzmann, LED)
  function diodePlan(kind) {
    var led = kind === 'led', kb = kind === 'kb', ard = Math.round(p.adc) === 1;
    var VALS = led ? [0, 0.5, 1.0, 1.5, 1.6, 1.7, 1.75, 1.8, 1.85, 1.9, 2.0, 2.1, 2.2, 2.4, 2.7, 3.0, 3.5, 4.0, 5.0, 6.0]
      : kb ? [0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0]
        : [-10, -8, -6, -4, -2, -1, 0, 0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0];
    var dev = led ? 'red LED' : kb ? 'BC547 with base and collector joined' : (SAMPLE || '1N4007 silicon diode');
    function rd(q) { return memo('rd', q, function (qq) { var r = KN.read(qq, qq.Vs); return { V: r[0], I: r[1] }; }); }
    function cut(rows) { var f = rows.filter(function (r) { return r.I > 0; }).map(function (r) { return [r.V, Math.log(r.I)]; }); return interpCross(f, Math.log(1e-3), false); }
    var pl = {
      compName: (led ? 'Red LED' : kb ? 'Diode-connected BC547' : dev) + ' in series with ' + ohm(p.Rser),
      wiring: 'Bench supply → ' + ohm(p.Rser) + ' resistor → ' + dev + ' → back to the supply. ' + (ard ? 'An Arduino Uno reads the junction voltage on A0 and the resistor\'s voltage on A1, both on its internal 1.1 V reference.' : 'Multimeter 1 across the device, multimeter 2 in series as the ammeter' + (kb ? ' (the voltage across 1 kΩ divided by 1 kΩ).' : '.')) + (kb ? ' Room temperature 300 K, ideality factor n = 1.' : ''),
      formula: led ? 'I = I_s (exp(V/(n V_T)) − 1);  turn-on: V at I = 1 mA' : kb ? 'ln I = ln I_s + (q / (n k T)) V,   k = q / (n T × slope)' : 'I = I_s (exp(V/(n V_T)) − 1),   r_d = dV/dI;  cut-in: V at I = 1 mA',
      controls: [{ param: 'Vs', label: 'Supply voltage', short: 'SUPPLY', unit: 'V', digits: 2, vals: VALS }],
      art: function () {
        resistor(-0.06, -0.02, p.Rser, 'R');
        var lp = led ? ledPart(0.02, -0.02, '#ff3020', 'LED') : null; if (!led) { if (kb) to92(0.02, -0.02, 'BC547'); else diode(0.02, -0.02, kind === 'pn' ? 'D1' : 'D'); }
        battery(-0.12, 0.03, 'SUPPLY'); jumper([-0.075, -0.02], [-0.12, 0.02], 'red'); jumper([0.04, -0.02], [0.1, 0.03], 'black');
        return function (q) { if (lp) lp.set(Math.min(1, rd(q).I / 0.01)); }; },
      trace: function (q) { var m = rd(q);
        if (kb) return { xy: { pts: xyRows(function (r) { return r.V; }, function (r) { return Math.log(Math.max(r.I, 1e-15)); }), cur: [m.V, Math.log(Math.max(m.I, 1e-15))], xl: 'V (V)', yl: 'ln (I / A)' } };
        return { xy: { pts: xyRows(function (r) { return r.V; }, function (r) { return r.I * 1000; }), cur: [m.V, m.I * 1000], xl: 'V (V)', yl: 'I (mA)' } }; },
      meas: function (q) { var m = rd(q), rev = m.I < 0;
        var it = rev ? fmt(m.I * 1e6, 3) + ' µA' : kb ? fmt(m.I * 1000, 4) + ' mA' : fmt(m.I * 1000, 3) + ' mA';
        return { lines: ['V = ' + fmt(m.V, kb ? 4 : 3) + ' V   I = ' + it, 'Supply ' + fmt(q.Vs, 2) + ' V through ' + ohm(p.Rser)],
          meters: ard ? [['ARDUINO A0 (1.1 V ref)', Math.round(m.V / (1.1 / 1024)) + ' cnt'], ['A1: I = V/1 kΩ', fmt(m.I * 1000, 4) + ' mA']] : [['V  DC', fmt(m.V, kb ? 4 : 3) + ' V'], [rev ? 'µA  DC' : 'mA  DC', rev ? fmt(m.I * 1e6, 3) : fmt(m.I * 1000, kb ? 4 : 3)]],
          row: { Vs: q.Vs, V: m.V, I: m.I } }; },
      cols: [{ label: 'Supply (V)', get: function (r) { return fmt(r.Vs, 2); } }, { label: 'V (V)', get: function (r) { return fmt(r.V, kb ? 4 : 3); } },
        { label: 'I (mA)', get: function (r) { return r.I < 0 ? fmt(r.I * 1000, 6) : fmt(r.I * 1000, 4); } }].concat(kb ? [{ label: 'ln I', get: function (r) { return r.I > 0 ? fmt(Math.log(r.I), 3) : '—'; } }] : []),
      need: kb ? 8 : led ? 10 : 12,
      runs: (kb ? [0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5] : led ? [0, 1.0, 1.5, 1.7, 1.75, 1.8, 1.85, 1.9, 2.0, 2.2, 2.4, 3.0, 4.0, 5.0]
        : [0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 1.0, 1.6, 3.0, -1, -4, -10]).map(function (v) { return { Vs: v }; }),
      okFn: kind === 'pn' ? function (rows) { var f = 0, r = 0; rows.forEach(function (x) { if (x.Vs > 0) f++; else if (x.Vs < 0) r++; }); return f >= 6 && r >= 3; } : null,
      graph: kb ? { x: function (r) { return r.V; }, y: function (r) { return r.I > 0 ? Math.log(r.I) : NaN; }, xlabel: 'V (V)', ylabel: 'ln (I / A)',
        line: function (pts) { var l = ols(pts.filter(function (q) { return isFinite(q[1]); })); return function (x) { return l.m * x + l.c; }; } }
        : { x: function (r) { return r.V; }, y: function (r) { return r.I * 1000; }, xlabel: 'V (V)', ylabel: 'I (mA)' },
      result: function (rows) {
        if (kb) { var pts = rows.filter(function (r) { return r.I > 0 && r.I < 1.2e-3; }).map(function (r) { return [r.V, Math.log(r.I)]; }), l = ols(pts);
          return { label: 'Boltzmann constant k', value: 1.602176634e-19 / (p.n * p.T * l.m) * 1e23, unit: '× 10⁻²³ J/K', digits: 4, truth: p.kB * 1e23,
            note: 'Slope of ln I against V = ' + fmt(l.m, 2) + ' per volt from ' + pts.length + ' readings below 1.2 mA; k = q / (n T × slope) with n = 1 and T = 300 K.' }; }
        var vc = cut(rows), fw = rows.filter(function (r) { return r.I > 0; }).sort(function (a, b) { return b.I - a.I; }), rdn = fw.length >= 2 ? (fw[0].V - fw[1].V) / (fw[0].I - fw[1].I) : NaN;
        var rv = rows.filter(function (r) { return r.Vs < 0; }).sort(function (a, b) { return a.Vs - b.Vs; });
        return { label: led ? 'Turn-on voltage (at 1 mA)' : 'Cut-in voltage (at 1 mA)', value: vc, unit: 'V', digits: 3, truth: KN.measure(p).Vcut,
          note: 'Interpolated on ln I between the two readings either side of 1 mA. Dynamic resistance from the two highest readings: ' + fmt(rdn, 2) + ' Ω.' + (rv.length ? ' Reverse current at ' + fmt(rv[0].Vs, 0) + ' V supply: ' + fmt(-rv[0].I * 1e6, 3) + ' µA.' : '') };
      },
      resultNote: kb ? 'The points lie on a straight line because the current is exponential in the voltage; its slope is q/(n k T). Using the room temperature and n = 1 gives the Boltzmann constant. At larger currents the series resistance bends the line, which is why only readings below about a milliamp are used.'
        : 'The current stays tiny until the voltage approaches the cut-in value and then rises steeply; above it the series resistance makes the curve almost straight and its slope is the dynamic resistance. In reverse bias only a small saturation and leakage current flows.',
      chips: ['Why does the current rise so suddenly?', kb ? 'Why is n taken as 1?' : 'What is the dynamic resistance?', 'What limits the current?', 'Check my readings'],
      viva: kb ? [['The slope of ln I against V is', ['q/(n k T)', 'n k T/q', 'I_s'], 0, 'From I = I_s exp(qV/(n k T)).']]
        : [['At 1 mA the dynamic resistance of an ideal diode at 300 K (n = 1) is about', ['26 Ω', '2.6 Ω', '260 Ω'], 0, 'r_d = V_T / I.']] };
    return pl;
  }
  PLANS['u8-pn-diode'] = function () { return diodePlan('pn'); };
  PLANS['u8-diode-boltzmann'] = function () { return diodePlan('kb'); };
  PLANS['u8-led-vi'] = function () { return diodePlan('led'); };

  // ---------------------------------------------------------------- tunnel diode
  PLANS['u8-tunnel-diode'] = function () {
    function cur(q) { return KN.i_of(q, q.V); }
    return {
      compName: 'Germanium tunnel diode on a 10 Ω divider',
      wiring: 'Bench supply → 1 kΩ → 10 Ω to ground; the tunnel diode sits across the 10 Ω through the milliammeter, so its voltage is set directly by the divider. Multimeter 1 across the diode.',
      formula: 'I = I_p (V/V_p) e^(1 − V/V_p) + I_v e^(A₂ (V − V_v)) + I_s (e^(V/V_T) − 1);   PVR = I_p / I_v',
      controls: [{ param: 'V', label: 'Diode voltage', short: 'VOLTAGE', unit: 'V', digits: 3, vals: rng(0, 0.6, 0.005) }],
      art: function () { resistor(-0.07, -0.03, 1000, 'R1'); resistor(-0.02, 0.01, 10, 'R2'); diode(0.04, -0.02, 'TD'); battery(-0.12, 0.03, 'SUPPLY');
        jumper([-0.085, -0.03], [-0.12, 0.02], 'red'); jumper([0.055, -0.02], [0.1, 0.03], 'black'); return function () {}; },
      trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.V; }, function (r) { return r.I * 1000; }), cur: [q.V, cur(q) * 1000], xl: 'V (V)', yl: 'I (mA)' } }; },
      meas: function (q) { var i = cur(q); return { lines: ['V = ' + fmt(q.V, 3) + ' V   I = ' + fmt(i * 1000, 4) + ' mA'], meters: [['V  DC', fmt(q.V, 3) + ' V'], ['mA  DC', fmt(i * 1000, 4)]], row: { V: q.V, I: i } }; },
      cols: [{ label: 'V (V)', get: function (r) { return fmt(r.V, 3); } }, { label: 'I (mA)', get: function (r) { return fmt(r.I * 1000, 4); } }],
      need: 14,
      runs: [0, 0.02, 0.04, 0.055, 0.06, 0.065, 0.07, 0.075, 0.09, 0.12, 0.16, 0.2, 0.24, 0.28, 0.3, 0.31, 0.32, 0.33, 0.34, 0.36, 0.4, 0.45, 0.5, 0.55].map(function (v) { return { V: v }; }),
      graph: { x: function (r) { return r.V; }, y: function (r) { return r.I * 1000; }, xlabel: 'V (V)', ylabel: 'I (mA)' },
      result: function (rows) {
        var q = rows.slice().sort(function (a, b) { return a.V - b.V; }), ip = 0, kp = 0, i, iv = Infinity, sm = 0, s;
        for (i = 0; i < q.length; i++) if (q[i].I > ip && q[i].V < 0.2) { ip = q[i].I; kp = i; }
        for (i = kp; i < q.length; i++) if (q[i].V < 0.45 && q[i].I < iv) iv = q[i].I;
        for (i = kp + 1; i < q.length; i++) if (q[i].V < 0.36) { s = (q[i].I - q[i - 1].I) / (q[i].V - q[i - 1].V); if (s < sm) sm = s; }
        var m = KN.measure(p);
        return { label: 'Peak-to-valley ratio I_p / I_v', value: ip / iv, unit: '', digits: 2, truth: m.pvr,
          note: 'Peak ' + fmt(ip * 1000, 4) + ' mA, valley ' + fmt(iv * 1000, 4) + ' mA from your table. Steepest falling slope gives a negative resistance of about ' + fmt(1 / sm, 0) + ' Ω (the model\'s steepest point: ' + fmt(m.Rneg, 0) + ' Ω).' };
      },
      resultNote: 'The current rises to a peak, falls through the negative-resistance region as tunnelling stops, reaches a valley of excess current, and then rises again as an ordinary forward-biased junction. The ratio of peak to valley current is the figure of merit for a tunnel diode used as an oscillator or switch.',
      chips: ['What is negative resistance?', 'Why must the source be stiff?', 'What is the excess current?', 'Check my readings'],
      viva: [['A tunnel diode can be used as an oscillator because', ['it has a negative-resistance region', 'it rectifies', 'it emits light'], 0, 'Negative resistance can cancel a tank circuit\'s losses.']] };
  };

  // ---------------------------------------------------------------- BJT h-parameters
  PLANS['u8-bjt-hparams'] = function () {
    function m(q) { return memo('bh', q, function (qq) { return { Vbe: KN.vbe(qq, qq.Ib, qq.Vce), Ic: KN.ic(qq, qq.Ib, qq.Vce) }; }); }
    function sl(rows, fx, fy) { return ols(rows.map(function (r) { return [fx(r), fy(r)]; })).m; }
    function atV(rows) { return rows.filter(function (r) { return Math.abs(r.Vce - 5) < 1e-9; }); }
    function atI(rows) { return rows.filter(function (r) { return Math.abs(r.Ib - 2e-5) < 1e-12; }); }
    return {
      compName: 'BC547 in common-emitter connection',
      wiring: 'Base supply → 100 kΩ → microammeter → base; collector supply → milliammeter → collector; emitter to common. Multimeter 1 across base-emitter, multimeter 2 is the collector milliammeter. Operating point: I_B = 20 µA, V_CE = 5 V.',
      formula: 'h_ie = ΔV_BE/ΔI_B,  h_fe = ΔI_C/ΔI_B  (V_CE fixed);   h_oe = ΔI_C/ΔV_CE,  h_re = ΔV_BE/ΔV_CE  (I_B fixed)',
      controls: [{ param: 'Ib', label: 'Base current', short: 'BASE I', unit: 'µA', digits: 0, fmtv: function (v) { return fmt(v * 1e6, 0) + ' µA'; }, vals: [5e-6, 1e-5, 1.5e-5, 2e-5, 2.5e-5, 3e-5, 3.5e-5, 4e-5] },
        { param: 'Vce', label: 'Collector-emitter voltage', short: 'V_CE', unit: 'V', digits: 1, vals: rng(1, 10, 1) }],
      art: function () { to92(0.0, -0.02, 'BC547'); resistor(-0.07, -0.02, 100000, 'RB'); battery(-0.12, 0.03, 'V_BB'); battery(0.1, 0.03, 'V_CC');
        jumper([-0.085, -0.02], [-0.12, 0.02], 'red'); jumper([0.01, -0.03], [0.09, 0.02], 'red'); return function () {}; },
      trace: function (q) { var c = m(q); return { xy: { pts: xyRows(function (r) { return r.Vce; }, function (r) { return r.Ic * 1000; }), cur: [q.Vce, c.Ic * 1000], xl: 'V_CE (V)', yl: 'I_C (mA)' } }; },
      meas: function (q) { var c = m(q); return { lines: ['I_B = ' + fmt(q.Ib * 1e6, 1) + ' µA   V_CE = ' + fmt(q.Vce, 2) + ' V', 'V_BE = ' + fmt(c.Vbe, 4) + ' V   I_C = ' + fmt(c.Ic * 1000, 4) + ' mA'],
        meters: [['V_BE  DC', fmt(c.Vbe, 4) + ' V'], ['I_C  mA', fmt(c.Ic * 1000, 4)]], row: { Ib: q.Ib, Vce: q.Vce, Vbe: c.Vbe, Ic: c.Ic } }; },
      cols: [{ label: 'I_B (µA)', get: function (r) { return fmt(r.Ib * 1e6, 1); } }, { label: 'V_CE (V)', get: function (r) { return fmt(r.Vce, 2); } },
        { label: 'V_BE (V)', get: function (r) { return fmt(r.Vbe, 4); } }, { label: 'I_C (mA)', get: function (r) { return fmt(r.Ic * 1000, 4); } }],
      need: 8,
      runs: [{ Vce: 5, Ib: 1e-5 }, { Ib: 1.5e-5 }, { Ib: 2e-5 }, { Ib: 2.5e-5 }, { Ib: 3e-5 }, { Ib: 2e-5, Vce: 3 }, { Vce: 4 }, { Vce: 6 }, { Vce: 7 }],
      okFn: function (rows) { return atV(rows).length >= 3 && atI(rows).length >= 3; },
      graph: { x: function (r) { return r.Ib * 1e6; }, y: function (r) { return r.Ic * 1000; }, xlabel: 'I_B (µA)', ylabel: 'I_C (mA)',
        line: function (pts) { var l = ols(pts); return function (x) { return l.m * x + l.c; }; } },
      result: function (rows) {
        var a = atV(rows), b = atI(rows), hfe = sl(a, function (r) { return r.Ib; }, function (r) { return r.Ic; }), hie = sl(a, function (r) { return r.Ib; }, function (r) { return r.Vbe; });
        var hoe = sl(b, function (r) { return r.Vce; }, function (r) { return r.Ic; }), hre = sl(b, function (r) { return r.Vce; }, function (r) { return r.Vbe; });
        return { label: 'Current gain h_fe', value: hfe, unit: '', digits: 1, truth: KN.measure(assign(p, { Ib: 2e-5, Vce: 5 })).hfe,
          note: 'Slopes from your table: h_ie = ' + fmt(hie / 1000, 2) + ' kΩ (straight-line slope; the curve is steeper at low current), h_oe = ' + fmt(hoe * 1e6, 1) + ' µS, h_re = ' + (hre * 1e4).toFixed(2) + ' × 10⁻⁴.' };
      },
      resultNote: 'At fixed V_CE the collector current is proportional to the base current, so h_fe is the slope of that line. The input characteristic is exponential, so h_ie is about V_T/I_B at the operating point. The output characteristic slopes gently because of the Early effect (h_oe), and V_CE barely moves V_BE (h_re of order 10⁻⁴).',
      chips: ['What does h_ie mean physically?', 'Why is h_oe small?', 'What is the Early effect?', 'Check my readings'],
      viva: [['h_ie of a transistor at I_B = 20 µA is about', ['1.3 kΩ', '13 Ω', '130 kΩ'], 0, 'V_T/I_B = 25.9 mV / 20 µA.']] };
  };

  // ---------------------------------------------------------------- BJT switch
  PLANS['u8-bjt-switch'] = function () {
    var VALS = rng(0, 5, 0.05);
    function vo(q) { return memo('vo', q, function (qq) { return KN.vout(qq, qq.Vin); }); }
    return {
      compName: 'BC547 NOT gate', wiring: 'Input → R_B = ' + ohm(p.Rb) + ' → base; collector → R_C = ' + ohm(p.Rc) + ' → +' + p.Vcc + ' V; emitter to common. An LED indicator on the output. Multimeter 1 on the input, multimeter 2 on the output.',
      formula: 'V_out = V_CC − β I_B R_C,   I_B = (V_in − V_BE)/R_B;   threshold V_in = V_BE + R_B (V_CC/2)/(β R_C)',
      controls: [{ param: 'Vin', label: 'Input voltage', short: 'INPUT', unit: 'V', digits: 2, vals: VALS }],
      art: function () { to92(0.0, -0.02, 'BC547'); resistor(-0.06, -0.02, p.Rb, 'RB'); resistor(0.03, -0.05, p.Rc, 'RC'); var lp = ledPart(0.07, 0.0, '#40ff40', 'OUT');
        battery(0.11, 0.03, '+5 V'); jumper([-0.075, -0.02], [-0.12, 0.02], 'yellow'); return function (q) { lp.set(vo(q) / p.Vcc); }; },
      trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.Vin; }, function (r) { return r.Vout; }), cur: [q.Vin, vo(q)], xl: 'V_in (V)', yl: 'V_out (V)' } }; },
      meas: function (q) { var v = vo(q); return { lines: ['V_in = ' + fmt(q.Vin, 2) + ' V   V_out = ' + fmt(v, 3) + ' V (' + (v > p.Vcc / 2 ? 'logic 1' : 'logic 0') + ')'], meters: [['V_in', fmt(q.Vin, 2) + ' V'], ['V_out', fmt(v, 3) + ' V']], row: { Vin: q.Vin, Vout: v } }; },
      cols: [{ label: 'V_in (V)', get: function (r) { return fmt(r.Vin, 2); } }, { label: 'V_out (V)', get: function (r) { return fmt(r.Vout, 3); } }, { label: 'Logic', get: function (r) { return r.Vout > p.Vcc / 2 ? '1' : '0'; } }],
      need: 10,
      runs: [0, 0.5, 0.6, 0.65, 0.7, 0.72, 0.74, 0.76, 0.78, 0.8, 0.82, 0.85, 0.9, 1.0, 1.5, 2, 3, 5].map(function (v) { return { Vin: v }; }),
      okFn: function (rows) { var lo = rows.some(function (r) { return r.Vin < 0.3; }), hi = rows.some(function (r) { return r.Vin > 4; }); return lo && hi; },
      graph: { x: function (r) { return r.Vin; }, y: function (r) { return r.Vout; }, xlabel: 'V_in (V)', ylabel: 'V_out (V)' },
      result: function (rows) { var th = interpCross(rows.map(function (r) { return [r.Vin, r.Vout]; }), p.Vcc / 2, false), lo = rows.filter(function (r) { return r.Vin > 4; });
        return { label: 'Switching threshold (V_out = V_CC/2)', value: th, unit: 'V', digits: 3, truth: KN.vth(p),
          note: 'Interpolated between the two readings either side of ' + p.Vcc / 2 + ' V. V_OH = ' + p.Vcc + ' V at a low input; V_OL = ' + (lo.length ? fmt(lo[lo.length - 1].Vout, 3) : '—') + ' V with the transistor saturated.' }; },
      resultNote: 'Below about 0.6 V the transistor is off and the output is high; then the output falls steeply as base current flows, and above about 1 V the transistor is saturated with only V_CE(sat) left. The circuit is an inverter: a NOT gate.',
      chips: ['Why is the output inverted?', 'What is saturation?', 'How would a larger R_C change it?', 'Check my readings'],
      viva: [['In saturation the collector-emitter voltage is about', ['0.1 V', '2.5 V', '5 V'], 0, 'Both junctions are forward biased.']] };
  };

  // ---------------------------------------------------------------- push-pull
  PLANS['u8-push-pull'] = function () {
    function an(q) { return memo('pp', q, function (qq) { return KN.analyse(qq); }); }
    return {
      compName: 'Complementary push-pull stage (n-p-n and p-n-p followers)', wiring: 'Generator (1 kHz sine) → both bases (through two bias diodes in class AB, shorted in class B); emitters joined → ' + p.RL + ' Ω load; ±12 V supplies. Channel 1 on the input, channel 2 on the output; the distortion analyser reads channel 2.',
      formula: 'v_out = v_in − V_g (v_in > V_g),  0,  v_in + V_g (v_in < −V_g);   V_out,peak = V_p − V_g',
      controls: [{ param: 'mode', label: 'Bias', short: 'BIAS', unit: '', digits: 0, names: ['class B', 'class AB'], vals: [0, 1] },
        { param: 'Vp', label: 'Input peak voltage', short: 'INPUT', unit: 'V', digits: 1, vals: [0.8, 1, 1.5, 2, 3, 4, 5, 6, 8] }],
      art: function () { to92(-0.01, -0.04, 'BD139'); to92(-0.01, 0.0, 'BD140'); var d1 = diode(-0.06, -0.04, 'D1'), d2 = diode(-0.06, 0.0, 'D2'); resistor(0.06, -0.02, 8, 'RL');
        battery(0.11, 0.03, '±12 V'); jumper([-0.08, -0.02], [-0.12, 0.03], 'yellow'); jumper([0.0, -0.02], [0.045, -0.02], 'blue');
        return function (q) { var ab = Math.round(q.mode) === 1; d1.g.visible = ab; d2.g.visible = ab; d1.label.visible = ab; d2.label.visible = ab; }; },
      trace: function (q) { return memo('ppt', q, function (qq) { var n = NS, dt = 2 / qq.f / n, a = [], b = [], i, v, d = KN.dz(qq);
        for (i = 0; i < n; i++) { v = qq.Vp * Math.sin(2 * Math.PI * qq.f * i * dt); a.push(v); b.push(v > d ? v - d : v < -d ? v + d : 0); }
        return { dt: dt, ch: [{ y: a, color: YEL, name: 'IN' }, { y: b, color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: maxOf(b) }, { kind: 'h', ch: 1, y: d }] }; }); },
      meas: function (q) { var a = an(q); return { lines: ['Output peak = ' + fmt(a.Vop, 3) + ' V (input ' + fmt(q.Vp, 1) + ' V peak)', 'THD = ' + fmt(a.thd * 100, 2) + ' %   output power = ' + fmt(a.Pout * 1000, 0) + ' mW'],
        meters: [['OUT PEAK', fmt(a.Vop, 3) + ' V'], ['THD', fmt(a.thd * 100, 2) + ' %']], row: { mode: Math.round(q.mode), Vp: q.Vp, vop: a.Vop, thd: a.thd } }; },
      cols: [{ label: 'Bias', get: function (r) { return r.mode ? 'AB' : 'B'; } }, { label: 'V_in,p (V)', get: function (r) { return fmt(r.Vp, 1); } }, { label: 'V_out,p (V)', get: function (r) { return fmt(r.vop, 3); } },
        { label: 'V_in − V_out (V)', get: function (r) { return fmt(r.Vp - r.vop, 3); } }, { label: 'THD (%)', get: function (r) { return fmt(r.thd * 100, 2); } }],
      need: 6,
      runs: [{ mode: 0, Vp: 1 }, { Vp: 1.5 }, { Vp: 2 }, { Vp: 3 }, { Vp: 5 }, { Vp: 8 }, { mode: 1, Vp: 2 }, { Vp: 5 }],
      okFn: function (rows) { var b = 0, ab = 0; rows.forEach(function (r) { if (r.mode) ab++; else b++; }); return b >= 4 && ab >= 1; },
      graph: { x: function (r) { return r.mode ? NaN : r.Vp; }, y: function (r) { return r.mode ? NaN : r.vop; }, xlabel: 'Input peak (V)', ylabel: 'Output peak (V), class B',
        line: function (pts) { var l = ols(pts.filter(function (q) { return isFinite(q[0]); })); return function (x) { return l.m * x + l.c; }; } },
      result: function (rows) { var b = rows.filter(function (r) { return !r.mode; }), vg = mean(b.map(function (r) { return r.Vp - r.vop; })), ab = rows.filter(function (r) { return r.mode; });
        return { label: 'Turn-on voltage V_g (crossover dead zone)', value: vg, unit: 'V', digits: 3, truth: p.Vg,
          note: 'Mean of V_in − V_out over the class B readings. THD at the lowest drive ' + fmt(b.length ? b[0].thd * 100 : NaN, 1) + ' %' + (ab.length ? '; in class AB ' + fmt(ab[0].thd * 100, 2) + ' % at ' + fmt(ab[0].Vp, 1) + ' V.' : '.') }; },
      resultNote: 'The output peak is always the input peak less V_g, so a line of slope 1 fits the class B readings with an offset of V_g. The flat step at each zero crossing is a fixed size, so its distortion is worst at low drive and fades at high drive. Biasing each base by a diode drop (class AB) almost removes it.',
      chips: ['Where does crossover distortion come from?', 'Why is it worse at low volume?', 'How does class AB fix it?', 'Check my readings'],
      viva: [['Class B efficiency can reach about', ['78.5 %', '25 %', '100 %'], 0, 'π/4 for a full sine.']] };
  };

  // ---------------------------------------------------------------- op-amp frequency response
  PLANS['u8-opamp-response'] = function () {
    var chip = /351/.test(SAMPLE) ? 'LF351' : '741';
    var FS = [100, 1000, 3000, 10000, 20000, 30000, 50000, 70000, 100000, 150000, 200000, 300000, 500000, 700000, 1000000, 1500000, 2000000, 3000000];
    function g(q) { return memo('og', q, function (qq) { var h = KN.h(qq, qq.f); return { g: Math.sqrt(h[0] * h[0] + h[1] * h[1]), ph: Math.atan2(h[1], h[0]) * 180 / Math.PI }; }); }
    return {
      compName: chip + ' op-amp amplifier, gain set by R_1 and R_f',
      wiring: 'Generator (' + fmt(p.Vin * 1000, 0) + ' mV peak) → R_1 = 1 kΩ → ' + chip + ' (inverting: input to R_1 at pin 2, pin 3 grounded; non-inverting: input to pin 3, R_1 from pin 2 to ground); R_f from output to pin 2; ±12 V. Channel 1 on the input, channel 2 on the output.',
      formula: 'f_3 = GBW / (1 + R_f/R_1),   G = G₀ / √(1 + (f/f_3)²)  ⇒  f_3 = f / √((G₀/G)² − 1)',
      controls: [{ param: 'cfg', label: 'Connection', short: 'CIRCUIT', unit: '', digits: 0, names: ['inverting', 'non-inverting'], vals: [0, 1] },
        { param: 'Rf', label: 'Feedback resistor R_f', short: 'R_f', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [10000, 47000, 100000] },
        { param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { dip8(0.0, -0.02, chip === '741' ? 'uA741' : 'LF351'); resistor(-0.06, -0.02, p.R1, 'R1'); var rf = resistor(0.0, -0.06, p.Rf, 'Rf'); battery(0.1, 0.03, '±12 V');
        jumper([-0.075, -0.02], [-0.12, 0.03], 'yellow'); jumper([0.012, -0.02], [0.06, 0.02], 'blue'); return function (q) { rf.set(q.Rf); }; },
      trace: function (q) { var m = g(q), t = sineTrace(q.f, [p.Vin, p.Vin * m.g], [0, m.ph * Math.PI / 180], 3);
        return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: p.Vin * m.g }] }; },
      meas: function (q) { var m = g(q); return { lines: ['Gain = ' + fmt(m.g, 3) + ' (' + fmt(20 * ln10(m.g), 2) + ' dB) at ' + fLabel(q.f), 'Phase ' + fmt(m.ph, 1) + '°,  output ' + fmt(p.Vin * m.g * 1000, 1) + ' mV peak'],
        meters: [['FREQ', fLabel(q.f)], ['GAIN', fmt(m.g, 3)]], row: { cfg: Math.round(q.cfg), Rf: q.Rf, f: q.f, g: m.g } }; },
      cols: [{ label: 'Circuit', get: function (r) { return r.cfg ? 'non-inv' : 'inv'; } }, { label: 'R_f (kΩ)', get: function (r) { return fmt(r.Rf / 1000, 0); } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } },
        { label: 'Gain', get: function (r) { return fmt(r.g, 3); } }, { label: 'f_3 (kHz)', get: function (r, i, rows) { var v = f3Of(r, rows); return isFinite(v) ? fmt(v / 1000, 1) : '—'; } }],
      need: 12,
      runs: [[0, 10000], [0, 47000], [1, 10000]].reduce(function (a, c) { [100, 10000, 30000, 100000, 300000, 1000000, 3000000].forEach(function (f, i) { a.push(i === 0 ? { cfg: c[0], Rf: c[1], f: f } : { f: f }); }); return a; }, []),
      okFn: function (rows) { var a = rows.some(function (r) { return r.cfg === 0; }), b = rows.some(function (r) { return r.cfg === 1; }); return a && b && rows.filter(function (r) { return isFinite(f3Of(r, rows)); }).length >= 3; },
      graph: { x: function (r) { return ln10(r.f); }, y: function (r) { return 20 * ln10(r.g); }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain (dB)' },
      result: function (rows) { var gb = rows.map(function (r) { var f3 = f3Of(r, rows); return isFinite(f3) ? f3 * (1 + r.Rf / p.R1) : NaN; }).filter(isFinite);
        return { label: 'Gain-bandwidth product', value: mean(gb) / 1e6, unit: 'MHz', digits: 3, truth: KN.measure(p).gbw / 1e6,
          note: 'For each reading between 15 % and 90 % of its set\'s low-frequency gain G₀: f_3 = f/√((G₀/G)² − 1), then GBW = f_3 (1 + R_f/R_1); average of ' + gb.length + '.' }; },
      resultNote: 'Every gain setting rolls off at a frequency inversely proportional to its noise gain 1 + R_f/R_1, so the product of the two stays the same: the op-amp\'s gain-bandwidth product. An inverting and a non-inverting amplifier with the same resistors have the same bandwidth, though their gains differ by one.',
      chips: ['What is the gain-bandwidth product?', 'Why do both connections roll off at the same frequency?', 'What would slew rate do?', 'Check my readings'],
      viva: [['A 1 MHz op-amp at a noise gain of 100 has a bandwidth of', ['10 kHz', '100 kHz', '1 MHz'], 0, 'GBW / noise gain.']] };
    function f3Of(r, rows) { var lo = rows.filter(function (x) { return x.cfg === r.cfg && x.Rf === r.Rf; }).sort(function (a, b) { return a.f - b.f; })[0];
      if (!lo || lo.f > 1000) return NaN; var k = lo.g / r.g; if (r.g > 0.9 * lo.g || r.g < 0.15 * lo.g) return NaN; return r.f / Math.sqrt(k * k - 1); }
  };

  // ---------------------------------------------------------------- difference amplifier
  PLANS['u8-diff-amp'] = function () {
    function out(q) { var a = q.A; return Math.round(q.mode) === 0 ? KN.out(q, -0.5 * a, 0.5 * a) : KN.out(q, a, a); }
    return {
      compName: 'Four-resistor difference amplifier', wiring: 'V_1 → R_1 = 10 kΩ → pin 2, R_2 = 100 kΩ from output to pin 2; V_2 → R_3 = 10 kΩ → pin 3, R_4 = 100 kΩ from pin 3 to ground (1 % resistors); ±12 V. Generator at 1 kHz; channel 1 on the input, channel 2 on the output.',
      formula: 'A_d = R_2/R_1,   A_cm = R_4′/(R_3 + R_4′)(1 + R_2/R_1) − R_2/R_1,   CMRR = A_d / A_cm',
      controls: [{ param: 'mode', label: 'Input', short: 'INPUT', unit: '', digits: 0, names: ['differential', 'common-mode'], vals: [0, 1] },
        { param: 'A', label: 'Input amplitude', short: 'AMPLITUDE', unit: 'V', digits: 2, vals: [0.05, 0.1, 0.2, 0.5, 1.0, 2.0] }],
      art: function () { dip8(0.0, -0.02, 'uA741'); resistor(-0.06, -0.04, p.R1, 'R1'); resistor(-0.06, 0.0, p.R3, 'R3'); resistor(0.0, -0.065, p.R2, 'R2'); resistor(0.05, 0.02, p.R4, 'R4');
        battery(0.1, 0.03, '±12 V'); jumper([-0.075, -0.04], [-0.12, 0.03], 'yellow'); jumper([-0.075, 0.0], [-0.12, 0.04], 'green'); return function () {}; },
      trace: function (q) { var v = out(q), t = sineTrace(1000, [q.A, v], [0, 0], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: Math.round(q.mode) ? 'V_cm' : 'V_2−V_1' }, { y: t.ys[1], color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: Math.abs(v) }] }; },
      meas: function (q) { var v = out(q), gn = v / q.A; return { lines: ['Input ' + fmt(q.A, 2) + ' V peak (' + (Math.round(q.mode) ? 'common-mode' : 'differential') + ')', 'Output ' + fmt(Math.abs(v) * 1000, 2) + ' mV peak, gain ' + (Math.abs(gn) < 0.1 ? gn.toExponential(3) : fmt(gn, 4))],
        meters: [['IN  AC peak', fmt(q.A, 2) + ' V'], ['OUT  AC peak', fmt(Math.abs(v) * 1000, 2) + ' mV']], row: { mode: Math.round(q.mode), A: q.A, vo: v, g: gn } }; },
      cols: [{ label: 'Input', get: function (r) { return r.mode ? 'common' : 'diff'; } }, { label: 'V_in (V)', get: function (r) { return fmt(r.A, 2); } }, { label: 'V_out (mV)', get: function (r) { return fmt(r.vo * 1000, 3); } },
        { label: 'Gain', get: function (r) { return Math.abs(r.g) < 0.1 ? r.g.toExponential(3) : fmt(r.g, 4); } }],
      need: 6,
      runs: [{ mode: 0, A: 0.05 }, { A: 0.1 }, { A: 0.2 }, { mode: 1, A: 0.5 }, { A: 1.0 }, { A: 2.0 }],
      okFn: function (rows) { return rows.filter(function (r) { return !r.mode; }).length >= 2 && rows.filter(function (r) { return r.mode; }).length >= 2; },
      graph: { x: function (r) { return r.mode ? r.A : NaN; }, y: function (r) { return r.mode ? r.vo * 1000 : NaN; }, xlabel: 'Common-mode input (V)', ylabel: 'Output (mV)', line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } },
      result: function (rows) { var ad = mean(rows.filter(function (r) { return !r.mode; }).map(function (r) { return r.g; })), ac = mean(rows.filter(function (r) { return r.mode; }).map(function (r) { return r.g; }));
        var c = Math.abs(ad / ac); return { label: 'CMRR', value: c, unit: '', digits: 0, truth: KN.measure(p).cmrr, note: 'A_d = ' + fmt(ad, 3) + ', A_cm = ' + ac.toExponential(3) + ', CMRR = ' + fmt(20 * ln10(c), 1) + ' dB.' }; },
      resultNote: 'The differential gain is R_2/R_1 = 10. A common-mode input should give no output, but a fraction of a per cent mismatch between R_4/R_3 and R_2/R_1 leaves a small output proportional to it, so the CMRR here is set by the resistors. Matched resistor networks are how precision difference amplifiers reach 80-100 dB.',
      chips: ['What limits the CMRR?', 'Why is CMRR given in dB?', 'How do I improve it?', 'Check my readings'],
      viva: [['With resistors matched to 0.1 %, a gain-10 difference amplifier has a CMRR of roughly', ['80 dB', '20 dB', '200 dB'], 0, 'About (1 + R_2/R_1)/(fractional mismatch).']] };
  };

  // ---------------------------------------------------------------- analog computer
  PLANS['u8-analog-computer'] = function () {
    var NAMES = ['simultaneous equations', 'first order', 'second order'];
    function rcOf(r) { return Math.sqrt(1 - p.z * p.z) / (2 * Math.PI * r.fd); }
    function sol(q) { return memo('ac', q, function (qq) { var c = Math.round(qq.cfg);
      if (c === 0) { var a = KN.simul(qq, true); return { c: 0, x: a[0], y: a[1], xs: a[2], ys: a[3], dt: a[4] }; }
      if (c === 1) { var b = KN.first(qq); return { c: 1, tau: b[2], ys: b[0], dt: b[1] }; }
      var d = KN.second(qq); return { c: 2, fd: d[2], ys: d[0], dt: d[1] }; }); }
    return {
      compName: 'Analog computer patch board: integrators, summers and inverters', wiring: 'Integrators of R (unknown) and C (the dial) with summing amplifiers. Equations: 2x + y = 5, x + 3y = 10;  RC dv/dt = −v from 5 V;  x″ + 2ζω x′ + ω² x = 0, ζ = ' + p.z + ', ω = 1/RC, from 5 V. Channel 1 shows x (or v), channel 2 shows y.',
      formula: 'τ = RC,   f_d = √(1 − ζ²) / (2π RC),   x = (c₁b₂ − b₁c₂)/(a₁b₂ − b₁a₂)',
      controls: [{ param: 'cfg', label: 'Equation patched', short: 'EQUATION', unit: '', digits: 0, names: NAMES, vals: [0, 1, 2] },
        { param: 'C', label: 'Integrator capacitor', short: 'C', unit: 'F', digits: 0, fmtv: cLabel, vals: [1e-8, 2.2e-8, 4.7e-8, 1e-7, 2.2e-7, 4.7e-7] }],
      art: function () { dip8(-0.06, -0.03, 'TL074'); dip8(0.0, -0.03, 'TL074'); var c1 = capacitor(-0.06, 0.01, 1e-7, 'C1', 'ceramic'), c2 = capacitor(0.0, 0.01, 1e-7, 'C2', 'ceramic'); resistor(0.06, -0.03, 100000, 'R');
        battery(0.11, 0.03, '±12 V'); jumper([-0.05, -0.03], [-0.01, -0.03], 'blue'); jumper([0.01, -0.03], [0.05, 0.01], 'green'); return function () {}; },
      trace: function (q) { var s = sol(q); if (s.c === 0) return { dt: s.dt, ch: [{ y: s.xs, color: YEL, name: 'x' }, { y: s.ys, color: CYA, name: 'y' }], marks: [{ kind: 'h', ch: 0, y: s.x }, { kind: 'h', ch: 1, y: s.y }] };
        return { dt: s.dt, ch: [{ y: s.ys, color: YEL, name: s.c === 1 ? 'v' : 'x' }], marks: s.c === 1 ? [{ kind: 'h', ch: 0, y: p.V0 / Math.E }, { kind: 'v', t: s.tau, color: CYA }] : [] }; },
      meas: function (q) { var s = sol(q), l;
        if (s.c === 0) l = ['x = ' + fmt(s.x, 3) + ' V   y = ' + fmt(s.y, 3) + ' V (settled)'];
        else if (s.c === 1) l = ['v falls to V₀/e = ' + fmt(p.V0 / Math.E, 3) + ' V after τ = ' + fmt(s.tau * 1000, 3) + ' ms'];
        else l = ['Period = ' + fmt(1000 / s.fd, 3) + ' ms   f_d = ' + fmt(s.fd, 3) + ' Hz'];
        return { lines: l, meters: [['CHANNEL 1', s.c === 0 ? fmt(s.x, 3) + ' V' : s.c === 1 ? fmt(s.tau * 1000, 3) + ' ms' : fmt(1000 / s.fd, 3) + ' ms'], ['CHANNEL 2', s.c === 0 ? fmt(s.y, 3) + ' V' : '—']],
          row: { cfg: s.c, C: q.C, x: s.x, y: s.y, tau: s.tau, fd: s.fd } }; },
      cols: [{ label: 'Equation', get: function (r) { return NAMES[r.cfg]; } }, { label: 'C', get: function (r) { return cLabel(r.C); } },
        { label: 'Reading', get: function (r) { return r.cfg === 0 ? 'x = ' + fmt(r.x, 3) + ', y = ' + fmt(r.y, 3) : r.cfg === 1 ? 'τ = ' + fmt(r.tau * 1000, 3) + ' ms' : 'T = ' + fmt(1000 / r.fd, 3) + ' ms'; } },
        { label: 'R (kΩ)', get: function (r) { return r.cfg === 0 ? '—' : fmt((r.cfg === 1 ? r.tau / r.C : rcOf(r) / r.C) / 1000, 2); } }],
      need: 6,
      runs: [{ cfg: 0, C: 1e-7 }, { cfg: 1, C: 2.2e-8 }, { C: 1e-7 }, { C: 4.7e-7 }, { cfg: 2, C: 2.2e-8 }, { C: 1e-7 }, { C: 4.7e-7 }],
      okFn: function (rows) { var c = [0, 0, 0]; rows.forEach(function (r) { c[r.cfg]++; }); return c[0] >= 1 && c[1] >= 1 && c[2] >= 1; },
      graph: { x: function (r) { return r.cfg ? r.C * 1e6 : NaN; }, y: function (r) { return r.cfg === 1 ? r.tau * 1000 : r.cfg === 2 ? rcOf(r) * 1000 : NaN; }, xlabel: 'C (µF)', ylabel: 'RC (ms)', line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } },
      result: function (rows) { var rs = rows.filter(function (r) { return r.cfg; }).map(function (r) { return r.cfg === 1 ? r.tau / r.C : rcOf(r) / r.C; }), s0 = rows.filter(function (r) { return r.cfg === 0; })[0];
        return { label: 'Integrator resistor R', value: mean(rs) / 1000, unit: 'kΩ', digits: 2, truth: p.R / 1000,
          note: 'R = τ/C from the first-order runs and √(1 − ζ²)/(2π f_d C) from the second-order runs, averaged over ' + rs.length + '.' + (s0 ? ' Simultaneous equations: x = ' + fmt(s0.x, 3) + ', y = ' + fmt(s0.y, 3) + ' (exact: 1, 3).' : '') }; },
      resultNote: 'The integrators turn each equation into a circuit whose voltages obey it. The pair of simultaneous equations settles where both are satisfied; the first-order circuit decays with time constant RC; the second-order loop rings at its damped natural frequency. RC is the same in both, so the integrator resistor comes out of either.',
      chips: ['How does an integrator solve an equation?', 'Why does the loop settle at the solution?', 'What does ζ do?', 'Check my readings'],
      viva: [['An inverting integrator\'s output is', ['−(1/RC) ∫ V_in dt', 'RC dV_in/dt', 'V_in R/C'], 0, 'The capacitor current equals V_in/R.']] };
  };

  // ---------------------------------------------------------------- active filters
  PLANS['u8-active-filters'] = function () {
    var kind = Math.round(p.kind), f0 = KN.f0(p), NAMES = ['low-pass', 'high-pass', 'band-pass', 'band-reject'];
    var FS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2, 1.3, 1.4, 1.6, 2, 2.5, 3, 5, 10].map(function (k) { return sig3(k * f0); });
    var ref = KN.ref(p);
    function g(q) { return memo('fg', q, function (qq) { var h = KN.h(qq, qq.f); return { g: Math.sqrt(h[0] * h[0] + h[1] * h[1]), ph: Math.atan2(h[1], h[0]) * 180 / Math.PI }; }); }
    return {
      compName: (SAMPLE || 'Sallen-Key ' + NAMES[kind] + ' filter'), wiring: NAMES[kind].charAt(0).toUpperCase() + NAMES[kind].slice(1) + ' filter, R = ' + rLabel(p.R) + ', C = ' + cLabel(p.C) + (kind <= 1 ? ', op-amp gain K = ' + p.K + ' (5.86 kΩ and 10 kΩ)' : ', Q = ' + p.Q) + '. Generator 1 V peak; channel 1 on the input, channel 2 on the output.',
      formula: 'f₀ = 1/(2π R C),   H = ' + ['K/(1 − x² + jx/Q)', '−K x²/(1 − x² + jx/Q)', '(jx/Q)/(1 − x² + jx/Q)', '(1 − x²)/(1 − x² + jx/Q)'][kind] + ',   cut-off where |H| = H_pass/√2',
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { dip8(0.0, -0.02, 'uA741'); resistor(-0.07, -0.03, p.R, 'R'); resistor(-0.04, 0.01, p.R, 'R'); capacitor(-0.02, -0.055, p.C, 'C', 'ceramic'); capacitor(0.04, 0.01, p.C, 'C', 'ceramic');
        battery(0.1, 0.03, '±12 V'); jumper([-0.085, -0.03], [-0.12, 0.03], 'yellow'); return function () {}; },
      trace: function (q) { var m = g(q), t = sineTrace(q.f, [1, m.g], [0, m.ph * Math.PI / 180], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: m.g }] }; },
      meas: function (q) { var m = g(q); return { lines: ['Gain = ' + fmt(m.g, 4) + ' (' + fmt(20 * ln10(m.g / ref), 2) + ' dB from the pass band) at ' + fLabel(q.f), 'Phase ' + fmt(m.ph, 1) + '°'],
        meters: [['FREQ', fLabel(q.f)], ['OUT  AC peak', fmt(m.g, 4) + ' V']], row: { f: q.f, g: m.g } }; },
      cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 1); } }, { label: 'V_out (V)', get: function (r) { return fmt(r.g, 4); } }, { label: 'Gain (dB)', get: function (r) { return fmt(20 * ln10(r.g / ref), 2); } }],
      need: 12,
      runs: FS.map(function (f) { return { f: f }; }),
      graph: { x: function (r) { return ln10(r.f); }, y: function (r) { return 20 * ln10(r.g / ref); }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain relative to the pass band (dB)' },
      result: function (rows) { var pts = rows.map(function (r) { return [r.f, 20 * ln10(r.g / ref)]; }), cs = crossings(pts, -3.0103), m = KN.measure(p);
        var lo = cs.length ? cs[0] : NaN, hi = cs.length > 1 ? cs[cs.length - 1] : NaN;
        return { label: kind <= 1 ? 'Cut-off frequency (−3 dB)' : 'Lower cut-off frequency (−3 dB)', value: lo, unit: 'Hz', digits: 1, truth: m.fc,
          note: 'Interpolated on dB against log f between the readings either side of −3 dB.' + (kind >= 2 ? ' Upper cut-off ' + fmt(hi, 1) + ' Hz (the model: ' + fmt(m.fc2, 1) + ' Hz); bandwidth ' + fmt(hi - lo, 1) + ' Hz.' : '') + ' Design f₀ = 1/(2πRC) = ' + fmt(f0, 1) + ' Hz.' }; },
      resultNote: ['The low-pass is flat below f₀ and falls 40 dB a decade above it; with Q = 0.707 (Butterworth) the −3 dB point is f₀ itself.', 'The high-pass is the mirror image: it rises 40 dB a decade up to f₀ and is flat above it.',
        'The band-pass peaks at f₀ and passes a band of width f₀/Q between its two −3 dB edges, placed geometrically about f₀.', 'The notch removes a band of width f₀/Q around f₀ and passes everything else.'][kind],
      chips: ['What sets the cut-off?', 'What does Q do?', 'Why is it called active?', 'Check my readings'],
      viva: [['A Butterworth response is', ['maximally flat in the pass band', 'the steepest possible', 'a band-pass'], 0, 'Q = 0.707 for second order.']] };
  };

  // ---------------------------------------------------------------- JFET CS amplifier
  PLANS['u8-jfet-cs'] = function () {
    var FS = [10, 20, 30, 50, 70, 100, 200, 500, 1000, 10000, 100000, 300000, 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000];
    function g(q) { return memo('jg', q, function (qq) { var h = KN.h(qq, qq.f); return { g: Math.sqrt(h[0] * h[0] + h[1] * h[1]), ph: Math.atan2(h[1], h[0]) * 180 / Math.PI }; }); }
    var vin = 0.02, b = KN.bias(p);
    return {
      compName: 'BFW10 common-source amplifier', wiring: 'Generator (' + vin * 1000 + ' mV peak) → 10 kΩ → 0.1 µF → gate (1 MΩ to ground); R_S = 680 Ω bypassed by 22 µF; R_D = 2.2 kΩ to +15 V; 1 µF to the 10 kΩ load. Channel 1 on the generator, channel 2 on the load.',
      formula: 'I_D = I_DSS (1 − V_GS/V_P)²,  V_GS = −I_D R_S,  g_m = (2 I_DSS/|V_P|)(1 − V_GS/V_P),  A = −g_m (R_D ∥ R_L)',
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { to92(-0.01, -0.02, 'BFW10'); resistor(-0.07, -0.02, p.Rsig, 'Rsig'); resistor(-0.04, 0.02, p.Rg, 'RG'); resistor(0.03, -0.05, p.Rd, 'RD'); resistor(0.03, 0.03, p.Rs, 'RS'); resistor(0.08, 0.0, p.RL, 'RL');
        capacitor(-0.045, -0.02, p.Cin, 'Cin', 'ceramic'); capacitor(0.06, 0.03, p.Cs, 'CS', 'el'); battery(0.115, 0.03, '15 V'); jumper([-0.085, -0.02], [-0.12, 0.03], 'yellow'); return function () {}; },
      trace: function (q) { var m = g(q), t = sineTrace(q.f, [vin, vin * m.g], [0, m.ph * Math.PI / 180], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }], marks: [{ kind: 'h', ch: 1, y: vin * m.g }] }; },
      meas: function (q) { var m = g(q); return { lines: ['Gain = ' + fmt(m.g, 3) + ' (' + fmt(20 * ln10(m.g), 2) + ' dB) at ' + fLabel(q.f), 'Output ' + fmt(vin * m.g * 1000, 1) + ' mV peak, phase ' + fmt(m.ph, 0) + '°', 'Bias: I_D = ' + fmt(b[0] * 1000, 3) + ' mA, V_GS = ' + fmt(-b[0] * p.Rs, 3) + ' V'],
        meters: [['FREQ', fLabel(q.f)], ['GAIN', fmt(m.g, 3)]], row: { f: q.f, g: m.g } }; },
      cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'Gain', get: function (r) { return fmt(r.g, 3); } }, { label: 'Gain (dB)', get: function (r) { return fmt(20 * ln10(r.g), 2); } }],
      need: 10,
      runs: FS.map(function (f) { return { f: f }; }),
      graph: { x: function (r) { return ln10(r.f); }, y: function (r) { return 20 * ln10(r.g); }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain (dB)' },
      result: function (rows) { var gm = maxOf(rows.map(function (r) { return r.g; })), top = rows.filter(function (r) { return r.g >= 0.99 * gm; }), am = mean(top.map(function (r) { return r.g; }));
        var cs = crossings(rows.map(function (r) { return [r.f, 20 * ln10(r.g / am)]; }), -3.0103), m = KN.measure(p);
        return { label: 'Mid-band voltage gain', value: am, unit: '', digits: 2, truth: m.Amid,
          note: 'Average of the flat part of your table. Half-power frequencies about ' + (cs.length ? fLabel(cs[0]) : '—') + ' and ' + (cs.length > 1 ? fLabel(cs[cs.length - 1]) : '—') + ' (model ' + fLabel(m.fL) + ' and ' + fLabel(m.fH) + '); bandwidth about ' + (cs.length > 1 ? fLabel(cs[cs.length - 1] - cs[0]) : '—') + '.' }; },
      resultNote: 'The gain is flat between a lower corner set by the coupling and source-bypass capacitors and an upper corner set by the gate capacitances, the gate-drain one enlarged by the Miller effect. In between, the stage inverts and multiplies the signal by g_m (R_D ∥ R_L).',
      chips: ['Why is the output inverted?', 'What is the Miller effect?', 'How does R_S set the bias?', 'Check my readings'],
      viva: [['A JFET is controlled by', ['the gate-source voltage', 'the gate current', 'the drain current'], 0, 'The gate junction is reverse biased and draws almost nothing.']] };
  };

  // ---------------------------------------------------------------- DAC
  PLANS['u8-dac'] = function () {
    var NAMES = []; for (var i = 0; i < 16; i++) NAMES.push(('000' + i.toString(2)).slice(-4));
    function v(q) { return KN.vout(q, Math.round(q.D)); }
    var sw = null;
    return {
      compName: '4-bit R-2R ladder DAC with a buffer', wiring: 'Four switches put 5 V or 0 V on the 2R legs (R = 10 kΩ, 2R = 20 kΩ) of the ladder; the MSB node drives a non-inverting buffer of gain 1 + 6.2 kΩ/10 kΩ. Multimeter 1 on the output.',
      formula: 'V_out = V_ref (1 + R_f/R_g) D / 2⁴,   LSB = V_ref (1 + R_f/R_g) / 16',
      controls: [{ param: 'D', label: 'Input code (D3 D2 D1 D0)', short: 'CODE', unit: '', digits: 0, names: NAMES, vals: rng(0, 15, 1) }],
      art: function () { sw = switchRow(-0.07, -0.02, 4); dip8(0.04, -0.02, 'uA741'); [-0.02, 0.0, 0.02].forEach(function (x) { resistor(x, 0.02, p.R, 'R'); }); resistor(0.08, -0.04, p.Rf, 'Rf'); resistor(0.08, 0.0, p.Rg, 'Rg');
        battery(0.11, 0.035, '+5 V'); return function (q) { sw.set(Math.round(q.D)); }; },
      trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.D; }, function (r) { return r.V; }), cur: [Math.round(q.D), v(q)], xl: 'Code D', yl: 'V_out (V)' } }; },
      meas: function (q) { var x = v(q); return { lines: ['Code ' + NAMES[Math.round(q.D)] + ' (D = ' + Math.round(q.D) + ')   V_out = ' + fmt(x, 4) + ' V'], meters: [['V  DC', fmt(x, 4) + ' V'], ['CODE', NAMES[Math.round(q.D)]]], row: { D: Math.round(q.D), V: x } }; },
      cols: [{ label: 'Code', get: function (r) { return NAMES[r.D]; } }, { label: 'D', get: function (r) { return r.D; } }, { label: 'V_out (V)', get: function (r) { return fmt(r.V, 4); } }],
      need: 8,
      runs: rng(0, 15, 1).map(function (d) { return { D: d }; }),
      graph: { x: function (r) { return r.D; }, y: function (r) { return r.V; }, xlabel: 'Code D', ylabel: 'V_out (V)', line: function (pts) { var l = ols(pts); return function (x) { return l.m * x + l.c; }; } },
      result: function (rows) { var l = ols(rows.map(function (r) { return [r.D, r.V]; })), top = rows.filter(function (r) { return r.D === 15; })[0];
        return { label: 'Step size (1 LSB)', value: l.m, unit: 'V', digits: 4, truth: KN.measure(p).lsb, note: 'Slope of the straight line through your ' + rows.length + ' readings; full scale ' + (top ? fmt(top.V, 3) + ' V' : '(code 1111 not taken)') + '. The specification asked for 0.5 V; the E24 resistors give ' + fmt(5 * (1 + p.Rf / p.Rg) / 16, 4) + ' V.' }; },
      resultNote: 'Every step of the code adds the same voltage, so the output is a straight staircase through zero: the ladder weights each bit by a power of two using only R and 2R. The buffer\'s gain sets the step size to the specification.',
      chips: ['How does the ladder weight the bits?', 'What is the resolution?', 'Why use a buffer?', 'Check my readings'],
      viva: [['The MSB of a 4-bit DAC contributes', ['half of full scale (about)', 'one LSB', 'a quarter'], 0, '8 of 15 steps.']] };
  };

  // ---------------------------------------------------------------- ADC
  PLANS['u8-adc'] = function () {
    var bar = null;
    function c(q) { return KN.code(q, q.Vin); }
    function bin(k) { return ('0000000' + k.toString(2)).slice(-8); }
    return {
      compName: 'ADC0804 8-bit converter with LED outputs', wiring: '2.5 V on the Vref/2 pin (span 0-5 V), free-running conversion; the input from a potentiometer read by multimeter 1; eight LEDs on the data outputs.',
      formula: 'code = nearest of V_in / LSB,   LSB = V_ref / 256',
      controls: [{ param: 'Vin', label: 'Input voltage', short: 'INPUT', unit: 'V', digits: 2, vals: rng(0, 5, 0.1) }],
      art: function () { dip8(-0.04, -0.02, 'ADC0804'); bar = ledBar(0.05, -0.04, 8, '#ff3020'); resistor(-0.09, 0.02, 10000, 'POT'); battery(0.11, 0.035, '+5 V');
        return function (q) { bar.set(c(q)); }; },
      trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.Vin; }, function (r) { return r.code; }), cur: [q.Vin, c(q)], xl: 'V_in (V)', yl: 'Code' } }; },
      meas: function (q) { var k = c(q); return { lines: ['V_in = ' + fmt(q.Vin, 2) + ' V   LEDs ' + bin(k) + ' = ' + k], meters: [['V_in  DC', fmt(q.Vin, 2) + ' V'], ['LEDs', bin(k)]], row: { Vin: q.Vin, code: k } }; },
      cols: [{ label: 'V_in (V)', get: function (r) { return fmt(r.Vin, 2); } }, { label: 'LEDs', get: function (r) { return bin(r.code); } }, { label: 'Code', get: function (r) { return r.code; } }],
      need: 8,
      runs: rng(0.2, 4.6, 0.4).map(function (v) { return { Vin: v }; }),
      graph: { x: function (r) { return r.Vin; }, y: function (r) { return r.code; }, xlabel: 'V_in (V)', ylabel: 'Code', line: function (pts) { var l = ols(pts); return function (x) { return l.m * x + l.c; }; } },
      result: function (rows) { var l = ols(rows.map(function (r) { return [r.Vin, r.code]; }));
        return { label: 'Step size (1 LSB)', value: 1000 / l.m, unit: 'mV', digits: 2, truth: KN.measure(p).lsb * 1000, note: 'Inverse of the slope of code against input, ' + fmt(l.m, 2) + ' codes per volt; span = 256 LSB = ' + fmt(256 / l.m, 3) + ' V.' }; },
      resultNote: 'The code climbs one step for every 19.5 mV of input, so the points sit within half a step of a straight line whose slope is 1/LSB. The converter finds each code by trying the bits one at a time from the MSB.',
      chips: ['How does successive approximation work?', 'What sets the span?', 'What is quantisation error?', 'Check my readings'],
      viva: [['The quantisation error of a converter that rounds to the nearest code is at most', ['half an LSB', 'one LSB', 'zero'], 0, 'The levels sit half a step low.']] };
  };

  // ---------------------------------------------------------------- sample and hold
  PLANS['u8-sample-hold'] = function () {
    function an(q) { return memo('sh', q, function (qq) { var t = KN.trace(qq), a = KN.analyse(qq); return { sw: t[0], vc: t[1], dt: t[2], tacq: a.tacq, droop: a.droop }; }); }
    return {
      compName: 'CD4066 switch, hold capacitor and buffer', wiring: '2 V DC level → source resistor → CD4066 switch (R_on ≈ ' + p.Ron + ' Ω) → hold capacitor C_h (unknown) → buffer. The switch closes at t = 0 for six time constants, then holds. Channel 1 on the sampling pulse, channel 2 on the capacitor.',
      formula: 'v_C = V_s (1 − e^(−t/τ)),  τ = (R_src + R_on) C_h;  t_acq(10–90 %) = τ ln 9;  droop = I_leak / C_h',
      controls: [{ param: 'Rsrc', label: 'Source resistor', short: 'R_SOURCE', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [470, 1000, 2200, 3300, 4700, 6800, 10000] }],
      art: function () { dip8(-0.02, -0.02, 'CD4066'); dip8(0.05, -0.02, 'TL071'); var rs = resistor(-0.08, -0.02, p.Rsrc, 'Rsrc'); capacitor(0.02, 0.02, p.Ch, 'Ch', 'ceramic', true); battery(0.11, 0.035, '±5 V');
        jumper([-0.095, -0.02], [-0.12, 0.03], 'yellow'); return function (q) { rs.set(q.Rsrc); }; },
      trace: function (q) { var a = an(q), t10 = NaN, t90 = NaN; var c1 = cross(a.vc, a.dt, 0.1 * p.Vs, true), c2 = cross(a.vc, a.dt, 0.9 * p.Vs, true);
        return { dt: a.dt, ch: [{ y: a.sw, color: YEL, name: 'PULSE' }, { y: a.vc, color: CYA, name: 'C_h' }], marks: (c1.length && c2.length) ? [{ kind: 'v', t: c1[0], color: CYA }, { kind: 'v', t: c2[0], color: CYA }] : [] }; },
      meas: function (q) { var a = an(q); return { lines: ['10 % → 90 % rise: ' + fmt(a.tacq * 1e6, 2) + ' µs', 'Droop while holding: ' + fmt(a.droop, 3) + ' V/s'],
        meters: [['t_acq', fmt(a.tacq * 1e6, 2) + ' µs'], ['DROOP', fmt(a.droop, 3) + ' V/s']], row: { Rsrc: q.Rsrc, tacq: a.tacq, droop: a.droop } }; },
      cols: [{ label: 'R_src (Ω)', get: function (r) { return fmt(r.Rsrc, 0); } }, { label: 't_acq (µs)', get: function (r) { return fmt(r.tacq * 1e6, 2); } },
        { label: 'C_h (nF)', get: function (r) { return fmt(r.tacq / ((r.Rsrc + p.Ron) * Math.log(9)) * 1e9, 3); } }, { label: 'Droop (V/s)', get: function (r) { return fmt(r.droop, 3); } }],
      need: 4,
      runs: [470, 1000, 2200, 4700, 10000].map(function (r) { return { Rsrc: r }; }),
      graph: { x: function (r) { return (r.Rsrc + p.Ron) / 1000; }, y: function (r) { return r.tacq * 1e6; }, xlabel: 'R_src + R_on (kΩ)', ylabel: 't_acq (µs)', line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } },
      result: function (rows) { var cs = rows.map(function (r) { return r.tacq / ((r.Rsrc + p.Ron) * Math.log(9)); });
        return { label: 'Hold capacitor C_h', value: mean(cs) * 1e9, unit: 'nF', digits: 3, truth: p.Ch * 1e9, note: 'C_h = t_acq / ((R_src + R_on) ln 9) averaged over ' + rows.length + ' readings; the leakage implied by the droop is ' + fmt(mean(rows.map(function (r) { return r.droop; })) * p.Ch * 1e9, 2) + ' nA.' }; },
      resultNote: 'The acquisition time grows in proportion to the total charging resistance, so the points lie on a line through the origin of slope C_h ln 9. While holding, the capacitor droops slowly; a bigger capacitor would droop less but acquire more slowly.',
      chips: ['Why is a buffer needed after the capacitor?', 'What causes droop?', 'How is the capacitor chosen?', 'Check my readings'],
      viva: [['Acquisition time is the time to', ['charge the hold capacitor to within the required accuracy', 'discharge it', 'open the switch'], 0, 'Here from 10 % to 90 %.']] };
  };

  // ---------------------------------------------------------------- 7805 supply
  PLANS['u8-regulated-supply'] = function () {
    function rn(q) { return memo('rg', q, function (qq) { return KN.run(qq, qq.Vsec, qq.Io, true); }); }
    function sl(rows, fx, fy) { return ols(rows.map(function (r) { return [fx(r), fy(r)]; })).m; }
    function ok(r) { return r.rout < 0.001; }
    function lineReg(rows) { var a = rows.filter(function (r) { return Math.abs(r.Io - 0.25) < 1e-9 && ok(r); }); return a.length >= 2 ? sl(a, function (r) { return r.Vin; }, function (r) { return r.Vout; }) : NaN; }
    function loadRows(rows) { return rows.filter(function (r) { return Math.abs(r.Vsec - 15) < 1e-9 && ok(r); }); }
    return {
      compName: 'Bridge rectifier, 2200 µF reservoir and 7805 regulator', wiring: 'Transformer secondary (taps 9, 12, 15, 18 V rms, 50 Hz; primary in a closed box) → bridge of four 1N4007 → 2200 µF → 7805 (0.33 µF in, 0.1 µF out) → rheostat load with an ammeter. Multimeter 1 on the regulator input (DC), multimeter 2 on the output. Channel 1 shows the input ripple, channel 2 the output.',
      formula: 'V_m = √2 V_sec − 2 V_f,  ripple ≈ I/(2 f C);   line reg = ΔV_out/ΔV_in,   load reg R_o = −ΔV_out/ΔI_o (at constant V_in)',
      controls: [{ param: 'Vsec', label: 'Transformer tap', short: 'TAP', unit: 'V', digits: 0, vals: [9, 12, 15, 18] },
        { param: 'Io', label: 'Load current', short: 'LOAD', unit: 'A', digits: 2, vals: [0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0] }],
      art: function () { boxPart(0.12, 0.08, 0.09, -0.3, 0.06, 0x4a4f57, 'TRANSFORMER'); [-0.09, -0.07].forEach(function (x) { diode(x, -0.04, 'D'); diode(x, 0.0, 'D'); });
        capacitor(-0.03, -0.02, p.Cf, '2200µ', 'el'); to92(0.02, -0.02, '7805'); var rl = resistor(0.07, -0.02, 10, 'LOAD'); return function () {}; },
      trace: function (q) { var r = rn(q); return { dt: r.dt, ch: [{ y: r.ins, color: YEL, name: 'V_in', center: r.Vin }, { y: r.outs, color: CYA, name: 'V_out', center: r.Vout }] }; },
      meas: function (q) { var r = rn(q), drop = !ok(r); return { lines: ['V_in (DC) = ' + fmt(r.Vin, 3) + ' V, ripple ' + fmt(r.rin, 3) + ' V p-p, valley ' + fmt(r.Vmin, 2) + ' V', 'V_out = ' + fmt(r.Vout, 4) + ' V' + (drop ? '  DROPOUT: output ripple ' + fmt(r.rout * 1000, 0) + ' mV' : '')],
        meters: [['V_in  DC', fmt(r.Vin, 3) + ' V'], ['V_out  DC', fmt(r.Vout, 4) + ' V']], row: { Vsec: q.Vsec, Io: q.Io, Vin: r.Vin, Vout: r.Vout, rout: r.rout } }; },
      cols: [{ label: 'Tap (V)', get: function (r) { return fmt(r.Vsec, 0); } }, { label: 'I_o (A)', get: function (r) { return fmt(r.Io, 2); } }, { label: 'V_in (V)', get: function (r) { return fmt(r.Vin, 3); } },
        { label: 'V_out (V)', get: function (r) { return fmt(r.Vout, 4); } }, { label: 'Note', get: function (r) { return ok(r) ? 'regulating' : 'dropout'; } }],
      need: 8,
      runs: [{ Vsec: 15, Io: 0.1 }, { Io: 0.25 }, { Io: 0.4 }, { Io: 0.55 }, { Io: 0.7 }, { Io: 1.0 }, { Io: 0.25, Vsec: 9 }, { Vsec: 12 }, { Vsec: 18 }, { Vsec: 9, Io: 1.0 }],
      okFn: function (rows) { return loadRows(rows).length >= 3 && isFinite(lineReg(rows)); },
      graph: { x: function (r) { return Math.abs(r.Vsec - 15) < 1e-9 && ok(r) ? r.Io : NaN; }, y: function (r) { return (r.Vout - 5) * 1000; }, xlabel: 'Load current (A), 15 V tap', ylabel: 'V_out − 5 V (mV)', line: function (pts) { var l = ols(pts.filter(function (q) { return isFinite(q[0]); })); return function (x) { return l.m * x + l.c; }; } },
      result: function (rows) { var lr = lineReg(rows), a = loadRows(rows), so = sl(a, function (r) { return r.Io; }, function (r) { return r.Vout; }), si = sl(a, function (r) { return r.Io; }, function (r) { return r.Vin; });
        var ro = -so + lr * si, dropped = rows.filter(function (r) { return !ok(r); }).length;
        return { label: 'Load regulation (output resistance)', value: ro * 1000, unit: 'mΩ', digits: 2, truth: p.Ro * 1000,
          note: 'Line regulation from the 0.25 A readings: ' + fmt(lr * 1000, 3) + ' mV per volt of input. The load slope ' + fmt(-so * 1000, 2) + ' mΩ is corrected for the input sagging with load (' + fmt(si, 2) + ' V/A times the line regulation). ' + (dropped ? dropped + ' reading(s) in dropout were left out.' : 'No reading was in dropout.') }; },
      resultNote: 'While the input\'s ripple valleys stay about 2 V above the output, the 7805 holds 5 V within a few millivolts whatever the tap or the load: the change per volt of input is the line regulation, the change per ampere of load the output resistance. On the 9 V tap at full load the valleys fall below the dropout and the output follows them down.',
      chips: ['What is dropout?', 'Why does the input fall with load?', 'What does the reservoir capacitor do?', 'Check my readings'],
      viva: [['The minimum input for a 7805 is about', ['7 V', '5 V', '12 V'], 0, '5 V plus its 2 V dropout.']] };
  };

  // ---------------------------------------------------------------- PLL
  PLANS['u8-pll'] = function () {
    var f0 = KN.f0(p), kf = 8 * f0 / p.V, NAMES = ['tracking (start locked)', 'capture (start unlocked)'];
    var VALS = rng(-1.2, 1.2, 0.01).map(function (k) { return Math.round(f0 + k * kf); });
    function lk(q) { return memo('pl', q, function (qq) { return KN.locked(qq, qq.fin - f0, Math.round(qq.mode)); }); }
    function edge(rows, mode, side) { var a = rows.filter(function (r) { return r.mode === mode && r.df * side > 0; }), inn = a.filter(function (r) { return r.lock; }), out = a.filter(function (r) { return !r.lock; });
      if (!inn.length || !out.length) return NaN; var i1 = Math.max.apply(null, inn.map(function (r) { return r.df * side; })), o1 = Math.min.apply(null, out.filter(function (r) { return r.df * side > i1; }).map(function (r) { return r.df * side; }).concat([Infinity]));
      return isFinite(o1) ? 0.5 * (i1 + o1) : NaN; }
    return {
      compName: 'NE565 phase-locked loop', wiring: 'NE565 on ±5 V (V = 10 V) with R_1 = ' + rLabel(p.R1) + ' and C_1 = ' + cLabel(p.C1) + ' (f₀ = ' + fmt(f0, 0) + ' Hz), C_2 = ' + cLabel(p.C2) + ' with the internal 3.6 kΩ as the loop filter. Generator (1 V) on pin 2; channel 1 on the input, channel 2 on the VCO output (pin 4).',
      formula: 'f₀ = 0.3/(R₁C₁),   lock range ±f_L = ±8 f₀/V,   capture ±f_C ≈ ±(1/2π)√(2π f_L / τ),  τ = 3.6 kΩ × C₂',
      controls: [{ param: 'mode', label: 'Approach', short: 'SWEEP', unit: '', digits: 0, names: NAMES, vals: [0, 1] },
        { param: 'fin', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, vals: VALS }],
      art: function () { dip8(0.0, -0.02, 'NE565'); resistor(-0.06, -0.03, p.R1, 'R1'); capacitor(-0.04, 0.01, p.C1, 'C1', 'ceramic'); capacitor(0.04, 0.01, p.C2, 'C2', 'el'); var lp = ledPart(0.08, -0.03, '#40ff40', 'LOCK');
        battery(0.11, 0.035, '±5 V'); jumper([-0.075, -0.03], [-0.12, 0.03], 'yellow'); return function (q) { lp.set(lk(q) ? 1 : 0); }; },
      trace: function (q) { var L1 = lk(q), fv = L1 ? q.fin : f0, n = NS, dt = 4 / q.fin / n, a = [], b = [], i;
        for (i = 0; i < n; i++) { a.push(Math.sin(2 * Math.PI * q.fin * i * dt)); b.push(Math.sin(2 * Math.PI * fv * i * dt + (L1 ? 0.6 : 0)) >= 0 ? 2 : -2); }
        return { dt: dt, ch: [{ y: a, color: YEL, name: 'IN' }, { y: b, color: CYA, name: 'VCO' }] }; },
      meas: function (q) { var L1 = lk(q); return { lines: ['Input ' + fmt(q.fin, 0) + ' Hz (' + (q.fin >= f0 ? '+' : '') + fmt(q.fin - f0, 0) + ' Hz from f₀): ' + (L1 ? 'LOCKED, VCO at ' + fmt(q.fin, 0) + ' Hz' : 'NOT LOCKED, VCO near its free-running ' + fmt(f0, 0) + ' Hz'), 'Approach: ' + NAMES[Math.round(q.mode)]],
        meters: [['INPUT', fmt(q.fin, 0) + ' Hz'], ['LOCK', L1 ? 'LOCKED' : 'free']], row: { mode: Math.round(q.mode), fin: q.fin, df: q.fin - f0, lock: L1 } }; },
      cols: [{ label: 'Approach', get: function (r) { return r.mode ? 'capture' : 'tracking'; } }, { label: 'f_in (Hz)', get: function (r) { return fmt(r.fin, 0); } }, { label: 'f_in − f₀ (Hz)', get: function (r) { return fmt(r.df, 0); } }, { label: 'Locked?', get: function (r) { return r.lock ? 'yes' : 'no'; } }],
      need: 12,
      runs: [0, 0.95, 0.97, 0.99, 1.01, 1.03, -0.95, -0.97, -0.99, -1.01, -1.03].map(function (k, i) { var o = { fin: Math.round(f0 + k * kf) }; if (i === 0) o.mode = 0; return o; })
        .concat([0.3, 0.26, 0.24, 0.22, 0.2, 0.18, 0.14, -0.3, -0.26, -0.24, -0.22, -0.2, -0.18, -0.14].map(function (k, i) { var o = { fin: Math.round(f0 + k * kf) }; if (i === 0) o.mode = 1; return o; })),
      okFn: function (rows) { return isFinite(edge(rows, 0, 1)) && isFinite(edge(rows, 0, -1)); },
      graph: { x: function (r) { return r.df; }, y: function (r) { return r.lock ? (r.mode ? 0.5 : 1) : 0; }, xlabel: 'f_in − f₀ (Hz)', ylabel: 'Locked (1 tracking, 0.5 capture)' },
      result: function (rows) { var up = edge(rows, 0, 1), dn = edge(rows, 0, -1), cu = edge(rows, 1, 1), cd = edge(rows, 1, -1), m = KN.measure(p);
        return { label: 'Lock range (each side of f₀)', value: 0.5 * (up + dn), unit: 'Hz', digits: 0, truth: m.lock,
          note: 'Edges from your table: +' + fmt(up, 0) + ' Hz and −' + fmt(dn, 0) + ' Hz (data sheet 8 f₀/V = ' + fmt(8 * f0 / p.V, 0) + ' Hz). Capture: +' + fmt(cu, 0) + ' / −' + fmt(cd, 0) + ' Hz (the loop model\'s ' + fmt(m.capture, 0) + ' Hz; the textbook estimate is ' + fmt(HK.TEXTBOOK.u8_pll_capture(p), 0) + ' Hz, a rough guide only).' }; },
      resultNote: 'Once locked, the loop follows the input until the VCO can be pulled no further: the lock range, set by the VCO\'s gain and the supply. Starting unlocked, the phase detector only produces a beat that the loop filter mostly removes, so the loop pulls in over a much narrower capture range. A larger C_2 narrows it further.',
      chips: ['Why is the capture range smaller?', 'What does the loop filter do?', 'What sets f₀?', 'Check my readings'],
      viva: [['The lock range of a 565 on ±6 V with f₀ = 5 kHz is about', ['±3.3 kHz', '±50 kHz', '±330 Hz'], 0, '8 × 5000 / 12.']] };
  };

  // ---------------------------------------------------------------- universal counter
  PLANS['u8-counter'] = function () {
    var NAMES = ['frequency', 'period (average)'];
    function rd(q) { var fr = Math.round(q.mode) === 0; if (fr) { var a = KN.freq(q, q.Tg); return { fr: true, val: a[0], cnt: a[1], f: a[0] }; }
      var b = KN.period(q, q.Np); return { fr: false, val: b[0], cnt: b[1], f: 1 / b[0] }; }
    return {
      compName: 'Universal counter with a 10 MHz time base', wiring: 'The oscillator under test (unknown frequency) → counter input A; channel 1 shows the signal, channel 2 the counter\'s gate. Multimeter positions show the counter\'s display and its count.',
      formula: 'frequency: f = N / T_g (± 1 count);   period: T = M / (f_clk N_p) (± 1 clock count)',
      controls: [{ param: 'mode', label: 'Function', short: 'FUNCTION', unit: '', digits: 0, names: NAMES, vals: [0, 1] },
        { param: 'Tg', label: 'Gate time', short: 'GATE', unit: 's', digits: 2, vals: [0.01, 0.1, 1, 10] },
        { param: 'Np', label: 'Periods averaged', short: 'AVERAGE', unit: '', digits: 0, vals: [1, 10, 100, 1000] }],
      art: function () { boxPart(0.16, 0.07, 0.1, -0.22, 0.09, 0x2b2f36, 'OSCILLATOR'); return function () {}; },
      trace: function (q) { var n = NS, f = p.f, dt = 6 / f / n, a = [], b = [], i, fr = Math.round(q.mode) === 0, gw = fr ? 3 / f : Math.min(5, q.Np) / f;
        for (i = 0; i < n; i++) { a.push(Math.sin(2 * Math.PI * f * i * dt) >= 0 ? 1 : -1); b.push(i * dt >= 0.5 / f && i * dt < 0.5 / f + gw ? 2 : 0); }
        return { dt: dt, ch: [{ y: a, color: YEL, name: 'INPUT' }, { y: b, color: CYA, name: 'GATE' }] }; },
      meas: function (q) { var r = rd(q); return { lines: [r.fr ? 'Display ' + fmt(r.val, 2) + ' Hz (' + r.cnt + ' counts in ' + q.Tg + ' s)' : 'Display ' + fmt(r.val * 1e6, 4) + ' µs (' + r.cnt + ' clock counts over ' + q.Np + ' period' + (q.Np > 1 ? 's' : '') + ')', 'Frequency from it: ' + fmt(r.f, 4) + ' Hz'],
        meters: [['COUNTER', r.fr ? fmt(r.val, 2) + ' Hz' : fmt(r.val * 1e6, 3) + ' µs'], ['COUNT', String(r.cnt)]], row: { mode: r.fr ? 0 : 1, set2: r.fr ? q.Tg : q.Np, val: r.val, cnt: r.cnt, f: r.f } }; },
      cols: [{ label: 'Function', get: function (r) { return NAMES[r.mode]; } }, { label: 'Gate / periods', get: function (r) { return r.mode ? fmt(r.set2, 0) + ' periods' : fmt(r.set2, 2) + ' s'; } },
        { label: 'Display', get: function (r) { return r.mode ? fmt(r.val * 1e6, 4) + ' µs' : fmt(r.val, 2) + ' Hz'; } }, { label: 'Counts', get: function (r) { return r.cnt; } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 4); } }],
      need: 6,
      runs: [{ mode: 0, Tg: 0.01 }, { Tg: 0.1 }, { Tg: 1 }, { Tg: 10 }, { mode: 1, Np: 1 }, { Np: 10 }, { Np: 100 }, { Np: 1000 }],
      okFn: function (rows) { return rows.some(function (r) { return r.mode === 0; }) && rows.some(function (r) { return r.mode === 1; }); },
      graph: { x: function (r) { return ln10(r.cnt); }, y: function (r) { return r.f; }, xlabel: 'log10 (counts)', ylabel: 'Frequency found (Hz)' },
      result: function (rows) { var best = rows.slice().sort(function (a, b) { return b.cnt - a.cnt; })[0];
        return { label: 'Oscillator frequency', value: best.f, unit: 'Hz', digits: 3, truth: p.f, note: 'From the reading with the most counts (' + best.cnt + ', ' + NAMES[best.mode] + ' mode), whose ±1-count resolution is ' + fmt(best.f / best.cnt, 4) + ' Hz.' }; },
      resultNote: 'Each reading is uncertain by one count, so its relative resolution is 1/counts. A 10 s gate counts about 12 000 cycles; averaging 1000 periods counts about 8 million clock cycles and is far finer. For a low frequency, period measurement wins; for a high one, frequency measurement does.',
      chips: ['What is the ±1 count error?', 'Why average many periods?', 'When is period mode better?', 'Check my readings'],
      viva: [['A 0.1 s gate on a 1234 Hz signal reads to about', ['10 Hz', '0.1 Hz', '1 Hz'], 0, 'One count in 0.1 s.']] };
  };

  // ---------------------------------------------------------------- distortion factor meter
  PLANS['u8-distortion-meter'] = function () {
    var f0 = p.f0, NAMES = ['SET LEVEL', 'DISTORTION'];
    var FS = [0.9, 0.95, 0.97, 0.98, 0.99, 0.995, 1.0, 1.005, 1.01, 1.02, 1.03, 1.05, 1.1].map(function (k) { return Math.round(k * f0); });
    function rd(q) { return memo('df', q, function (qq) { var tot = KN.rms(qq, qq.fn, false), res = KN.rms(qq, qq.fn, true); return { tot: tot, res: res }; }); }
    return {
      compName: 'Distortion factor meter on a signal generator', wiring: 'Generator output (' + fmt(f0 / 1000, 0) + ' kHz, 1 V) → distortion factor meter input. In SET LEVEL the meter is adjusted to read 100 %; in DISTORTION a notch of Q = ' + p.Q + ' tuned by the dial removes the fundamental. Channel 1 shows the input, channel 2 the residual after the notch (×10).',
      formula: 'D = √(V₂² + V₃² + …) / √(V₁² + V₂² + …),   notch H(x) = (1 − x²)/(1 − x² + jx/Q)',
      controls: [{ param: 'mode', label: 'Meter function', short: 'FUNCTION', unit: '', digits: 0, names: NAMES, vals: [0, 1] },
        { param: 'fn', label: 'Notch tuning', short: 'TUNE', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { boxPart(0.16, 0.07, 0.1, -0.22, 0.09, 0x3a4f6e, 'SIGNAL GENERATOR'); return function () {}; },
      trace: function (q) { var n = NS, dt = 3 / f0 / n, a = [], b = [], i, k, amp = [p.V1, p.V1 * p.h2, p.V1 * p.h3, p.V1 * p.h4, p.V1 * p.h5], mag = [], ph = [];
        for (k = 1; k < 6; k++) { var x = k * f0 / q.fn, re = 1 - x * x, im = x / p.Q, d = re * re + im * im; mag.push(Math.sqrt((re * re * re * re + re * re * im * im)) / d); ph.push(Math.atan2(-re * im, re * re) ); }
        for (i = 0; i < n; i++) { var th = 2 * Math.PI * f0 * i * dt, s = 0, r = 0; for (k = 0; k < 5; k++) { s += amp[k] * Math.sin((k + 1) * th); r += amp[k] * mag[k] * Math.sin((k + 1) * th + ph[k]); } a.push(s); b.push(10 * r); }
        return { dt: dt, ch: [{ y: a, color: YEL, name: 'IN' }, { y: b, color: CYA, name: 'RESIDUAL ×10' }] }; },
      meas: function (q) { var r = rd(q), dist = Math.round(q.mode) === 1, rdg = dist ? 100 * r.res / r.tot : 100;
        return { lines: [dist ? 'Meter: ' + fmt(rdg, 2) + ' % with the notch at ' + fLabel(q.fn) : 'Meter set to 100 % (total ' + fmt(r.tot, 4) + ' V rms)'], meters: [['TUNE', fLabel(q.fn)], ['METER', fmt(rdg, 2) + ' %']], row: { mode: dist ? 1 : 0, fn: q.fn, D: rdg } }; },
      cols: [{ label: 'Function', get: function (r) { return NAMES[r.mode]; } }, { label: 'Notch (kHz)', get: function (r) { return fmt(r.fn / 1000, 2); } }, { label: 'Reading (%)', get: function (r) { return fmt(r.D, 2); } }],
      need: 6,
      runs: [{ mode: 0, fn: Math.round(f0) }].concat([0.95, 0.98, 0.99, 0.995, 1.0, 1.005, 1.01, 1.02, 1.05].map(function (k, i) { var o = { fn: Math.round(k * f0) }; if (i === 0) o.mode = 1; return o; })),
      okFn: function (rows) { return rows.some(function (r) { return r.mode === 0; }) && rows.filter(function (r) { return r.mode === 1; }).length >= 5; },
      graph: { x: function (r) { return r.mode ? r.fn / 1000 : NaN; }, y: function (r) { return r.mode ? r.D : NaN; }, xlabel: 'Notch tuning (kHz)', ylabel: 'Meter reading (%)' },
      result: function (rows) { var d = rows.filter(function (r) { return r.mode === 1; }).sort(function (a, b) { return a.D - b.D; })[0];
        return { label: 'Distortion factor', value: d.D, unit: '%', digits: 2, truth: 100 * HK.TEXTBOOK.u8_dfm_d(p), note: 'The minimum reading, with the notch at ' + fLabel(d.fn) + '. The notch of Q = ' + p.Q + ' trims the second harmonic by about 0.2 %, so the meter reads very slightly low.' }; },
      resultNote: 'Away from the right setting the notch lets part of the 1 V fundamental through and the reading is large; at the right setting only the harmonics remain and the reading falls to its minimum, the distortion factor.',
      chips: ['Why is the reading a minimum?', 'What is total harmonic distortion?', 'Why set the level to 100 % first?', 'Check my readings'],
      viva: [['A pure sine on this meter would read', ['0 %', '100 %', '50 %'], 0, 'Nothing is left after the notch.']] };
  };

  // ---------------------------------------------------------------- thermostat
  PLANS['u8-thermostat'] = function () {
    var B = null;
    function rn(q) { return memo('ts', q, function (qq) { return KN.run(qq, true); }); }
    return {
      compName: 'Thermostat in a heated water bath', wiring: 'Water bath (1 kg) with a ' + p.P + ' W low-voltage heater switched by the thermostat\'s relay; the thermometer beside the thermostat bulb; room at ' + p.Ta + ' °C. The scope runs as a chart recorder: channel 1 is the temperature, channel 2 the heater.',
      formula: 'set point = (T_off + T_on)/2,   hysteresis = T_off − T_on,   t_heat = τ ln((T_∞ − T_on)/(T_∞ − T_off)),  τ = C/(hA)',
      controls: [{ param: 'D', label: 'Dial setting', short: 'DIAL', unit: '°C', digits: 0, vals: [30, 35, 40, 45, 50, 55, 60, 65] }],
      art: function () { B = bath(0.25, 0.12); return function (q) { var r = rn(q); B.th.set(r.Toff); }; },
      trace: function (q) { var r = rn(q), heat = r.heats.map(function (h) { return h ? 1 : 0; }), n = Math.min(r.temps.length, Math.ceil((r.ev.length >= 4 ? r.ev[3][0] + 60 : 4000) / r.dt));
        return { dt: r.dt, ch: [{ y: r.temps.slice(0, n), color: YEL, name: 'T', unit: '°C', center: (r.Ton + r.Toff) / 2 }, { y: heat.slice(0, n), color: CYA, name: 'HEATER', unit: '', center: 0.5 }],
          marks: [{ kind: 'h', ch: 0, y: r.Toff }, { kind: 'h', ch: 0, y: r.Ton }] }; },
      meas: function (q) { var r = rn(q); return { lines: ['Heater off at ' + fmt(r.Toff, 1) + ' °C, on at ' + fmt(r.Ton, 1) + ' °C', 'Heating ' + fmt(r.theat, 1) + ' s, cooling ' + fmt(r.tcool, 1) + ' s per cycle'],
        meters: [['OFF AT', fmt(r.Toff, 1) + ' °C'], ['ON AT', fmt(r.Ton, 1) + ' °C']], row: { D: q.D, ton: r.Ton, toff: r.Toff, theat: r.theat, tcool: r.tcool } }; },
      cols: [{ label: 'Dial (°C)', get: function (r) { return fmt(r.D, 0); } }, { label: 'T_off (°C)', get: function (r) { return fmt(r.toff, 1); } }, { label: 'T_on (°C)', get: function (r) { return fmt(r.ton, 1); } },
        { label: 'Set point (°C)', get: function (r) { return fmt((r.toff + r.ton) / 2, 2); } }, { label: 'Heat / cool (s)', get: function (r) { return fmt(r.theat, 0) + ' / ' + fmt(r.tcool, 0); } }],
      need: 4,
      runs: [30, 40, 50, 60].map(function (d) { return { D: d }; }),
      graph: { x: function (r) { return r.D; }, y: function (r) { return (r.toff + r.ton) / 2; }, xlabel: 'Dial setting (°C)', ylabel: 'True set point (°C)', line: function (pts) { var l = ols(pts); return function (x) { return l.m * x + l.c; }; } },
      result: function (rows) { var h = mean(rows.map(function (r) { return r.toff - r.ton; })), l = ols(rows.map(function (r) { return [r.D, (r.toff + r.ton) / 2]; }));
        return { label: 'Hysteresis (differential)', value: h, unit: '°C', digits: 2, truth: p.H, note: 'Mean of T_off − T_on. Calibration: set point = ' + fmt(l.c, 2) + ' + ' + fmt(l.m, 3) + ' × dial.' }; },
      resultNote: 'The thermostat switches the heater off a little above its set point and on a little below it; the gap is the same at every setting, and the set point follows the dial along a straight calibration line. The bath warms faster at a low setting and cools faster at a high one.',
      chips: ['Why does a thermostat need hysteresis?', 'Why do the heating and cooling times differ?', 'What is the calibration error?', 'Check my readings'],
      viva: [['A thermostat with no hysteresis would', ['switch on and off very rapidly', 'never switch', 'overheat'], 0, 'Any noise would cross the set point.']] };
  };

  // ---------------------------------------------------------------- cable noise pick-up
  PLANS['u8-cable-noise'] = function () {
    var shielded = p.k < 1, NAMES = ['floating', 'grounded'];
    var FS = [1000, 2000, 5000, 10000, 20000];
    function vn(q) { return memo('nz', q, function (qq) { var w = KN.wave(qq); return { src: w[0], vn: w[1], dt: w[2], a: 0.5 * (maxOf(w[1]) - minOf(w[1])) }; }); }
    function cOf(r) { var w = 2 * Math.PI * r.f, a = r.vn / (w * p.R * p.V1), c = a, i; for (i = 0; i < 8; i++) c = a * Math.sqrt(1 + Math.pow(w * p.R * (c + p.C2g), 2)); return c; }
    var ctl = [{ param: 'f', label: 'Aggressor frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }];
    if (shielded) ctl.unshift({ param: 'sg', label: 'Shield', short: 'SHIELD', unit: '', digits: 0, names: NAMES, vals: [0, 1] });
    return {
      compName: (SAMPLE || 'Unshielded wire') + ' beside an aggressor wire', wiring: 'Aggressor wire fed with ' + p.V1 + ' V peak from the generator; the test ' + (shielded ? 'cable' : 'wire') + ' runs alongside it, terminated in ' + rLabel(p.R) + ' (stray ' + cLabel(p.C2g) + ' to ground). ' + (shielded ? 'Its shield can be grounded at one end or left floating. ' : 'It has no shield. ') + 'Channel 1 on the aggressor, channel 2 across the termination.',
      formula: 'V_N = ωR C₁₂ V₁ / √(1 + (ωR(C₁₂ + C₂g))²)  ≈ ωR C₁₂ V₁ at low frequency',
      controls: ctl,
      art: function () { cable(-0.05, 0xb42a2a, 0.003, 'AGGRESSOR'); var c = cable(-0.025, shielded ? 0x8a8f96 : 0x3a6fb3, shielded ? 0.0045 : 0.002, shielded ? 'SHIELDED' : 'TEST WIRE'); resistor(0.12, 0.01, p.R, 'R');
        var gnd = shielded ? ledPart(-0.13, 0.01, '#40ff40', 'SHIELD GND') : null; return function (q) { if (gnd) gnd.set(Math.round(q.sg) === 1 ? 1 : 0); }; },
      trace: function (q) { var m = vn(q); return { dt: m.dt, ch: [{ y: m.src, color: YEL, name: 'AGGRESSOR' }, { y: m.vn, color: CYA, name: 'NOISE' }], marks: [{ kind: 'h', ch: 1, y: m.a }] }; },
      meas: function (q) { var m = vn(q), sh = shielded ? (Math.round(q.sg) ? 'shield grounded' : 'shield floating') : 'no shield';
        return { lines: ['Noise ' + fmt(m.a * 1000, 4) + ' mV peak at ' + fLabel(q.f) + ' (' + sh + ')'], meters: [['FREQ', fLabel(q.f)], ['NOISE', fmt(m.a * 1000, 4) + ' mV']], row: { sg: shielded ? Math.round(q.sg) : 1, f: q.f, vn: m.a } }; },
      cols: [{ label: 'Shield', get: function (r) { return shielded ? NAMES[r.sg] : 'none'; } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'Noise (mV)', get: function (r) { return fmt(r.vn * 1000, 4); } }, { label: 'C (pF)', get: function (r) { return fmt(cOf(r) * 1e12, 3); } }],
      need: shielded ? 6 : 4,
      runs: (shielded ? [{ sg: 1, f: 1000 }, { f: 2000 }, { f: 5000 }, { f: 10000 }, { sg: 0, f: 1000 }, { f: 5000 }, { f: 10000 }] : FS.map(function (f) { return { f: f }; })),
      okFn: shielded ? function (rows) { return rows.filter(function (r) { return r.sg === 1; }).length >= 3 && rows.some(function (r) { return r.sg === 0; }); } : null,
      graph: { x: function (r) { return r.f / 1000; }, y: function (r) { return r.vn * 1000; }, xlabel: 'Frequency (kHz)', ylabel: 'Noise (mV peak)' },
      result: function (rows) { var g = rows.filter(function (r) { return r.sg === 1; }), fl = rows.filter(function (r) { return r.sg === 0; }), c = mean(g.map(cOf)), cf = fl.length ? mean(fl.map(cOf)) : NaN;
        return { label: shielded ? 'Coupling capacitance with the shield grounded' : 'Coupling capacitance', value: c * 1e12, unit: 'pF', digits: 3, truth: KN.ceff(assign(p, { sg: 1 })) * 1e12,
          note: 'C = V_N/(ωR V₁) corrected for the ' + cLabel(p.C2g) + ' stray to ground, averaged over ' + g.length + ' readings.' + (shielded && isFinite(cf) ? ' With the shield floating: ' + fmt(cf * 1e12, 3) + ' pF, ' + fmt(cf / c, 0) + ' times as much: a shield only works when it is grounded.' : '') }; },
      resultNote: shielded ? 'The noise rises in proportion to frequency, as capacitive coupling should. Grounding the shield cuts it to the small fraction the shield does not cover; left floating, the shield passes the coupling on and the noise is as large as for a bare wire.'
        : 'The noise rises in proportion to frequency because the coupling is through a small capacitance. With no shield the only cures are distance, a lower receiving impedance, or a twisted, shielded cable.',
      chips: ['Why does the noise grow with frequency?', 'Why must the shield be grounded?', 'What about ground loops?', 'Check my readings'],
      viva: [['Halving the receiving resistance makes capacitive pick-up', ['about half', 'twice', 'unchanged'], 0, 'V_N ≈ ωR C V₁.']] };
  };

  var PL = (PLANS[BASE] || PLANS['u8-pn-diode'])();
  var CTRL = PL.controls;

  // =============================================================================================== control panel
  var gpTitle = L('SUPPLY · GENERATOR · CIRCUIT SETTINGS', { w: 0.24, ratio: 0.08, color: '#1b1b1b', px: 1024 }); gpTitle.position.set(0, 0.092, 0.0605); gp.add(gpTitle);
  var NCT = CTRL.length, dials = [], lcds = [];
  function dialX(i) { return (i - (NCT - 1) / 2) * 0.064 - 0.03; }
  CTRL.forEach(function (c, i) {
    var x = dialX(i);
    var lb = L(c.short, { w: 0.058, ratio: 0.16, color: '#1b1b1b' }); lb.position.set(x, 0.074, 0.0605); gp.add(lb);
    dials.push(dialKnob(gp, x, 0.05, 0.0605, 0.013));
    var tex = S.liveTex(256, 72), m = new T.Mesh(new T.PlaneGeometry(0.058, 0.0165), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); m.position.set(x, 0.02, 0.0608); gp.add(m);
    lcds.push({ tex: tex, last: '' });
  });
  var rockerBase = S.mesh(new T.BoxGeometry(0.028, 0.02, 0.006), M.black); rockerBase.position.set(0.1, 0.045, 0.0605); gp.add(rockerBase);
  var rocker = S.mesh(new T.BoxGeometry(0.02, 0.014, 0.01), new T.MeshStandardMaterial({ color: 0xd9d9d6, roughness: 0.4 })); rocker.position.set(0.1, 0.045, 0.065); gp.add(rocker);
  var pilotM = new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.0055, 14, 10), pilotM, false); pilot.position.set(0.1, 0.07, 0.0625); gp.add(pilot);
  var pwl = L('POWER', { w: 0.03, ratio: 0.26, color: '#1b1b1b' }); pwl.position.set(0.1, 0.022, 0.0605); gp.add(pwl);

  // =============================================================================================== oscilloscope
  var SCX = 0.04, SCZ = -0.43, SW = 0.5, SD = 0.24, SH = 0.3;
  var sco = new T.Group(); S.scene.add(sco); sco.position.set(SCX, 0, SCZ);
  var sBody = S.rounded(SW, SD, SH, 0.012, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); sBody.rotation.x = -Math.PI / 2; sBody.position.y = SH / 2; sco.add(sBody);
  S.contact(SW + 0.08, SD + 0.08, SCX, SCZ, 0.5);
  var bez = S.mesh(new T.BoxGeometry(0.39, 0.292, 0.006), M.grey); bez.position.set(-0.05, 0.15, SD / 2 + 0.001); sco.add(bez);
  var scrTex = S.liveTex(1024, 768), scr = new T.Mesh(new T.PlaneGeometry(0.36, 0.27), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scr.position.set(-0.05, 0.15, SD / 2 + 0.0045); sco.add(scr);
  dialKnob(sco, 0.2, 0.225, SD / 2, 0.014); dialKnob(sco, 0.2, 0.17, SD / 2, 0.014);
  var curBtn = S.mesh(new T.BoxGeometry(0.05, 0.02, 0.01), new T.MeshStandardMaterial({ color: 0x3a4f6e, roughness: 0.4 })); curBtn.position.set(0.2, 0.1, SD / 2 + 0.003); sco.add(curBtn);
  var curL = L('CURSORS', { w: 0.046, ratio: 0.28, color: '#f2f2f2' }); curL.position.set(0.2, 0.1, SD / 2 + 0.0085); sco.add(curL);
  var curLed = S.mesh(new T.SphereGeometry(0.0035, 10, 8), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }), false); curLed.position.set(0.228, 0.1, SD / 2 + 0.0095); sco.add(curLed);
  var sLbl = L('DIGITAL STORAGE OSCILLOSCOPE · 2 CH · X-Y', { w: 0.28, ratio: 0.06, color: '#1b1b1b', px: 1024 }); sLbl.position.set(-0.05, 0.296, SD / 2 + 0.0005); sco.add(sLbl);
  var chL1 = L('CH1', { w: 0.03, ratio: 0.3, color: '#6b5a00' }); chL1.position.set(0.2, 0.26, SD / 2 + 0.0008); sco.add(chL1);
  var chL2 = L('CH2', { w: 0.03, ratio: 0.3, color: '#006a80' }); chL2.position.set(0.2, 0.205, SD / 2 + 0.0008); sco.add(chL2);

  // ---------- the two multimeters
  var DM = [dmm(0.37, 0.0, 'MULTIMETER 1'), dmm(0.51, 0.0, 'MULTIMETER 2')];

  function niceStep(v) { var e = Math.pow(10, Math.floor(ln10(v))), f = v / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e; }
  var st = { power: false, checked: false, cur: false, set: CTRL.map(function (c) { return c.vals[0]; }), idx: CTRL.map(function () { return 0; }) };
  function over() { var o = {}; CTRL.forEach(function (c, i) { o[c.param] = st.set[i]; }); return o; }
  function qNow() { return assign(p, over()); }
  function drawXY(cx, w, h, xy) {
    var PL0 = 90, PT = 24, W = w - 120, H = h - 210, pts = xy.pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); }), all = pts.concat(isFinite(xy.cur[0]) && isFinite(xy.cur[1]) ? [xy.cur] : []), i;
    var x0 = Math.min.apply(null, all.map(function (q) { return q[0]; }).concat([0])), x1 = Math.max.apply(null, all.map(function (q) { return q[0]; }).concat([1e-9]));
    var y0 = Math.min.apply(null, all.map(function (q) { return q[1]; }).concat([0])), y1 = Math.max.apply(null, all.map(function (q) { return q[1]; }).concat([1e-9]));
    if (xy.yl && /ln/.test(xy.yl)) { y0 = Math.min.apply(null, all.map(function (q) { return q[1]; })); y1 = Math.max.apply(null, all.map(function (q) { return q[1]; })); }
    if (!(x1 - x0 > 1e-12)) x1 = x0 + 1; if (!(y1 - y0 > 1e-12)) y1 = y0 + 1;
    var dx = (x1 - x0) * 0.06, dy = (y1 - y0) * 0.08; x0 -= dx; x1 += dx; y0 -= dy; y1 += dy;
    function X(v) { return PL0 + (v - x0) / (x1 - x0) * W; } function Y(v) { return PT + H - (v - y0) / (y1 - y0) * H; }
    cx.strokeStyle = 'rgba(120,220,150,.22)'; cx.lineWidth = 1;
    for (i = 0; i <= 10; i++) { cx.beginPath(); cx.moveTo(PL0 + W * i / 10, PT); cx.lineTo(PL0 + W * i / 10, PT + H); cx.stroke(); }
    for (i = 0; i <= 8; i++) { cx.beginPath(); cx.moveTo(PL0, PT + H * i / 8); cx.lineTo(PL0 + W, PT + H * i / 8); cx.stroke(); }
    cx.strokeStyle = 'rgba(120,220,150,.6)'; if (x0 < 0 && x1 > 0) { cx.beginPath(); cx.moveTo(X(0), PT); cx.lineTo(X(0), PT + H); cx.stroke(); } if (y0 < 0 && y1 > 0) { cx.beginPath(); cx.moveTo(PL0, Y(0)); cx.lineTo(PL0 + W, Y(0)); cx.stroke(); }
    cx.fillStyle = '#9fe0b8'; cx.font = '600 24px "JetBrains Mono", monospace'; cx.textAlign = 'center';
    for (i = 0; i <= 5; i++) { var xv = x0 + (x1 - x0) * i / 5; cx.fillText(Math.abs(x1 - x0) < 0.5 ? xv.toFixed(3) : Math.abs(x1 - x0) < 20 ? xv.toFixed(2) : xv.toFixed(0), X(xv), PT + H + 30); }
    cx.textAlign = 'right'; for (i = 0; i <= 4; i++) { var yv = y0 + (y1 - y0) * i / 4; cx.fillText(Math.abs(y1 - y0) < 0.5 ? yv.toFixed(3) : Math.abs(y1 - y0) < 20 ? yv.toFixed(2) : yv.toFixed(0), PL0 - 8, Y(yv) + 8); }
    cx.fillStyle = GRN; pts.forEach(function (q) { cx.beginPath(); cx.arc(X(q[0]), Y(q[1]), 8, 0, Math.PI * 2); cx.fill(); });
    if (isFinite(xy.cur[0]) && isFinite(xy.cur[1])) { cx.strokeStyle = YEL; cx.lineWidth = 4; var px = X(xy.cur[0]), py = Y(xy.cur[1]); cx.beginPath(); cx.moveTo(px - 16, py); cx.lineTo(px + 16, py); cx.moveTo(px, py - 16); cx.lineTo(px, py + 16); cx.stroke(); }
    cx.textAlign = 'left'; cx.fillStyle = '#9fe0b8'; cx.font = '700 30px "JetBrains Mono", monospace'; cx.fillText('X-Y  ' + xy.xl + '  against  ' + xy.yl, PL0, h - 126, W);
  }
  function drawScope(cx, w, h) {
    cx.fillStyle = '#04100a'; cx.fillRect(0, 0, w, h);
    var PL0 = 14, PT = 14, W = w - 28, H = h - 176, i;
    cx.font = '600 34px "JetBrains Mono", monospace'; cx.textAlign = 'center';
    if (!st.power) { cx.fillStyle = '#4d8f6a'; cx.fillText('POWER OFF', w / 2, h / 2); return; }
    var q = qNow(), tr = PL.trace(q);
    if (tr.xy) drawXY(cx, w, h, tr.xy);
    else {
      cx.strokeStyle = 'rgba(120,220,150,.22)'; cx.lineWidth = 1;
      for (i = 0; i <= 10; i++) { cx.beginPath(); cx.moveTo(PL0 + W * i / 10, PT); cx.lineTo(PL0 + W * i / 10, PT + H); cx.stroke(); }
      for (i = 0; i <= 8; i++) { cx.beginPath(); cx.moveTo(PL0, PT + H * i / 8); cx.lineTo(PL0 + W, PT + H * i / 8); cx.stroke(); }
      cx.strokeStyle = 'rgba(120,220,150,.5)'; cx.beginPath(); cx.moveTo(PL0, PT + H / 2); cx.lineTo(PL0 + W, PT + H / 2); cx.stroke();
      var N = tr.ch[0].y.length, spanT = tr.dt * N, stride = Math.max(1, Math.floor(N / 1500)), vdivs = [], cen = [];
      tr.ch.forEach(function (c) { var c0 = c.center || 0, mx = Math.max(Math.abs(maxOf(c.y) - c0), Math.abs(minOf(c.y) - c0), 1e-12); cen.push(c0); vdivs.push(niceStep(mx / 3.2)); });
      var X = function (t) { return PL0 + W * t / spanT; };
      var Yc = function (v, k) { return PT + H / 2 - (v - cen[k]) / vdivs[k] * (H / 8); };
      if (tr.marks && st.cur) tr.marks.forEach(function (m) {
        cx.setLineDash([8, 6]); cx.lineWidth = 2; cx.strokeStyle = m.color || '#ffffff';
        cx.beginPath();
        if (m.kind === 'v') { cx.moveTo(X(m.t), PT); cx.lineTo(X(m.t), PT + H); } else { var yy = Yc(m.y, m.ch || 0); cx.moveTo(PL0, yy); cx.lineTo(PL0 + W, yy); }
        cx.stroke(); cx.setLineDash([]);
      });
      tr.ch.forEach(function (c, k) {
        cx.strokeStyle = c.color; cx.lineWidth = 4; cx.beginPath();
        for (var j = 0; j < N; j += stride) { var px = X(j * tr.dt), py = Yc(c.y[j], k); if (j === 0) cx.moveTo(px, py); else cx.lineTo(px, py); }
        cx.stroke();
      });
      cx.textAlign = 'left'; cx.font = '700 30px "JetBrains Mono", monospace';
      tr.ch.forEach(function (c, k) { var u = c.unit === undefined ? 'V' : c.unit; cx.fillStyle = c.color; cx.fillText(c.name + ' ' + (u ? eng(vdivs[k], u) : fmt(vdivs[k], 2)) + '/div' + (c.center ? ' @' + fmt(c.center, 1) : ''), PL0 + 6 + k * 335, h - 126, 330); });
      cx.fillStyle = '#9fe0b8'; cx.fillText(eng(spanT / 10, 's') + '/div', PL0 + 6 + tr.ch.length * 335, h - 126, 330);
    }
    cx.textAlign = 'left'; cx.font = '600 31px "JetBrains Mono", monospace';
    if (st.cur) { var ln = PL.meas(q).lines; cx.fillStyle = '#e8fff1'; cx.fillText(ln[0], PL0 + 6, h - 86, W - 12); if (ln.length > 1) cx.fillText(ln[1], PL0 + 6, h - 52, W - 12); if (ln.length > 2) cx.fillText(ln.slice(2).join('  '), PL0 + 6, h - 18, W - 12); }
    else { cx.fillStyle = '#6fa88a'; cx.fillText('CURSORS OFF  (tap CURSORS to measure)', PL0 + 6, h - 60); }
  }
  var scopeKey = '';
  function paintScope() {
    var k = JSON.stringify(over()) + st.power + st.cur + S.rows.length;
    if (k === scopeKey) return;
    scopeKey = k; scrTex.draw(drawScope);
    if (st.power) { var mm = PL.meas(qNow()).meters; DM[0].set(mm[0][0], mm[0][1]); DM[1].set(mm[1][0], mm[1][1]); }
    else { DM[0].set('OFF', '----'); DM[1].set('OFF', '----'); }
  }

  // ---------- the circuit on the board follows the dials
  var ART = PL.art(), artKey = '';
  function artSync() { var k = JSON.stringify(over()) + st.power; if (k === artKey) return; artKey = k; if (st.power) ART(qNow()); }

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
  setLook(); artSync(); paintScope();

  // ---------- wiring: supply, probes and meter leads
  S.wire([[GPX + 0.1, 0.03, GPZ + 0.065], [GPX + 0.2, 0.04, -0.1], [BBX - 0.15, 0.03, BBZ + 0.03]], 'red');
  S.wire([[SCX - 0.2, 0.035, SCZ + 0.13], [SCX - 0.25, 0.06, -0.12], [BBX + 0.1, 0.035, BBZ + 0.02]], 'yellow');
  S.wire([[SCX - 0.15, 0.035, SCZ + 0.13], [SCX - 0.2, 0.05, -0.1], [BBX + 0.13, 0.03, BBZ + 0.05]], 'blue');
  S.wire([[0.37, 0.012, 0.075], [0.3, 0.03, 0.09], [BBX + 0.16, 0.03, BBZ + 0.02]], 'red');
  S.wire([[0.51, 0.012, 0.075], [0.4, 0.03, 0.13], [BBX + 0.16, 0.03, BBZ + 0.05]], 'black');

  S.addApparatus('board', BB, PL.compName, PL.wiring);
  S.addApparatus('panel', gp, 'Supply, generator and circuit settings', 'The hand turns these dials one at a time; each dial\'s small display shows its present setting. The POWER rocker switches the bench on.');
  S.addApparatus('scope', sco, 'Two-channel digital storage oscilloscope', 'The screen is drawn from the circuit\'s own sampled waveforms, or as an X-Y plot of your readings for a DC characteristic. CURSORS switches on the markers and the readout line.');
  S.addApparatus('meters', DM[0].g, 'Two digital multimeters', 'They show the two readings of every setting; their leads go to the circuit on the board.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard('Reading'), hudS = S.hudCard('Settings');

  // =============================================================================================== human actions
  function dialFront(i) { return wpos(gp, dialX(i), 0.05, 0.072); }
  function turnTo(i, value) {
    var c = CTRL[i];
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var j = 0, best = 1e30, k;
    for (k = 0; k < c.vals.length; k++) if (Math.abs(c.vals[k] - value) < best) { best = Math.abs(c.vals[k] - value); j = k; }
    if (j === st.idx[i] && st.set[i] === c.vals[j]) return Promise.resolve();
    var i0 = st.idx[i], pt = dialFront(i);
    return S.hand.pinchMove(pt, function () { return pt; }, function (kk) {
      dials[i].rotation.z = dialAngle(i, i0 + (j - i0) * kk);
    }, { mode: 'front', ms: 360 + 180 * Math.min(3, Math.abs(j - i0)), reachMs: 500 })
      .then(function () { st.idx[i] = j; st.set[i] = c.vals[j]; setLook(); artSync(); paintScope(); S.render(); });
  }
  function togglePower(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () {
      st.power = on; if (!on) st.cur = false; setLook(); artSync(); paintScope(); S.click(900, 0.05);
      S.say(on ? 'Power on. The pilot lamp is lit, the meters read and the scope shows the circuit.' : 'Power off.');
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
    S.addRow(row); scopeKey = ''; paintScope();
    S.say('Written in your record book: ' + m.lines[0] + '.');
  }
  function enough() { return S.rows.length >= PL.need && (!PL.okFn || PL.okFn(S.rows)); }
  function liveLine() { return PL.meas(qNow()).lines[0]; }
  function ctrlLine() { return CTRL.map(function (c, i) { return c.label + ': ' + ctrlTxt(i, st.set[i]); }).join('  ·  '); }

  return {
    camera: { pos: [-0.08, 0.9, 1.3], look: [-0.06, 0.06, -0.16] },
    views: {
      board: [[0.06, 0.3, 0.3], [0.06, 0.02, -0.1]], panel: [[-0.44, 0.22, 0.2], [-0.44, 0.05, -0.24]], scope: [[0.0, 0.26, 0.4], [-0.01, 0.15, -0.4]],
      meters: [[0.44, 0.3, 0.42], [0.44, 0.03, 0.0]], bench: [[-0.08, 0.9, 1.3], [-0.06, 0.06, -0.16]], book: [[-0.55, 0.44, 0.52], [-0.62, 0.0, 0.08]],
    },
    theory: {
      principle: S.lab.theory, formula: PL.formula || '',
      formulaNote: 'Every reading on the meters and the scope is computed from the lab\'s own circuit model.' + (SAMPLE ? ' This specimen: ' + SAMPLE + '.' : ''),
      more: ['How it is wired: ' + PL.wiring],
      precautions: S.lab.safety + ' Change one dial at a time and let the reading settle.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title, at: [-0.66, 0.1, 0.12],
      lines: ['Aim: ' + S.lab.aim, PL.wiring, 'Instruments: two digital multimeters and a two-channel digital scope.', 'Precautions: power off before changing a connection; one dial changed at a time.'],
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
      if (st.power) out.reading = PL.meas(qNow()).lines.join('; ');
      return out;
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Check the circuit and switch on');
          u.p(PL.wiring);
          u.task('1. Check the circuit on the board', st.checked, st.checked ? 'Parts and connections checked' : 'Look at the board, the meters and the probes')
            .add(u.button(st.checked ? 'Checked' : 'Check the circuit', function () { st.checked = true; S.focus('board'); S.say(PL.compName + '. ' + PL.wiring); S.render(); }, !st.checked, st.checked));
          u.task('2. Switch the power on', st.power, st.power ? 'Power on; the meters and the scope read the circuit' : 'The hand presses the POWER rocker')
            .add(u.row(u.button(st.power ? 'Switch off' : 'Switch on', function () { if (!st.checked) { S.say('Check the circuit before you switch it on.'); return; } S.focus('panel'); togglePower(!st.power); }, !st.power, S.hand.busy)));
          u.note('A circuit is checked before it is powered, never after.');
          u.next('Next: take readings', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return togglePower(true); } },
      { id: 'measure', title: 'Measure', view: 'scope', render: function (u) {
          u.h2('Set the dials and take readings');
          u.p('The hand turns each dial to the setting you choose; switch the cursors on, read the meters and the screen, then record. At least ' + PL.need + ' readings are needed' + (PL.okFn ? ', covering every part of the experiment' : '') + '.');
          CTRL.forEach(function (c, i) {
            u.slider(c.label, 0, c.vals.length - 1, 1, function () { return st.idx[i]; }, function (k) { if (!st.power) { S.say('Switch the power on first.'); return; } turnTo(i, c.vals[k]); }, '', 0);
            u.note(c.label + ' is now ' + ctrlTxt(i, st.set[i]));
          });
          u.row(u.button(st.cur ? 'Cursors off' : 'Cursors on', function () { S.focus('scope'); toggleCursors(!st.cur); }, !st.cur, S.hand.busy),
            u.button('Record the readings', function () { record(); }, true, S.hand.busy));
          u.live(function () { return !st.power ? 'Power is off' : st.cur ? liveLine() : 'Cursors are off: switch them on to read the screen'; });
          u.h3('Observation table'); u.table();
          if (!enough()) u.p(S.rows.length + ' of at least ' + PL.need + ' readings recorded' + (PL.okFn ? ' (the set must also cover every part of the experiment)' : '') + '.');
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
