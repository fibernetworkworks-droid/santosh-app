/* Prayogshala studio rig `pe9-elec-bench`: ONE electronics bench for the wave-9 M.Sc. set-ups of
   app/prayog/labs/pg_elec_w9.py (built on the pattern of the B.Sc. ug8-analog-bench, as its own file). A solderless
   breadboard whose parts follow the lab, a supply / generator / settings panel (the circuit's settings as dials the
   hand turns, with a POWER rocker), two digital multimeters and a two-channel digital storage scope. The scope shows
   either the SAMPLED waveforms of the lab's own kernel (packs/pg_elec_w9.js) or an X-Y plot of the readings taken so
   far. Every number on a meter, on the screen and in the table comes from the kernel; nothing is typed in. Each lab's
   variants (its methods) share the plan of their base lab and read every value from S.lab.params. Low voltages only. */
HoolaStudio.define('pe9-elec-bench', function (S) {
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
  // =============================================================================================== the lab's plan
  var K_ = Math.round(p.kind === undefined ? 0 : p.kind);
  function linCross(pts, level) {               // all crossings of y = level along the x-sorted points, linear in x
    var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; }), out = [], i, a, b;
    for (i = 1; i < q.length; i++) { a = q[i - 1]; b = q[i]; if ((a[1] - level) * (b[1] - level) < 0) out.push(a[0] + (b[0] - a[0]) * (level - a[1]) / (b[1] - a[1])); }
    return out;
  }
  function decades(ms, d0, d1) { var o = [], d, i; for (d = d0; d <= d1; d *= 10) for (i = 0; i < ms.length; i++) o.push(Math.round(ms[i] * d * 1000) / 1000); return o; }
  var E6 = [1, 1.5, 2.2, 3.3, 4.7, 6.8];
  function binStr(v, n) { var s = '', i; for (i = n - 1; i >= 0; i--) s += (v >> i) & 1; return s; }
  function lineFit(pts) { var l = ols(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return function (x) { return l.m * x + l.c; }; }
  function originFit(pts) { var m = origin(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return function (x) { return m * x; }; }

  // ---------------------------------------------------------------- regulated supplies
  PLANS['pe9-regulator'] = function () {
    var NAMES = ['zener shunt regulator', 'series transistor regulator', 'IC regulator (7805 type)'];
    var VIN = K_ === 2 ? [8, 9, 10, 11, 12, 13, 14, 15, 16, 18] : [10, 11, 12, 13, 14, 15, 16, 17, 18];
    var IL = K_ === 0 ? [0.005, 0.01, 0.015, 0.02, 0.025, 0.03] : K_ === 1 ? [0.05, 0.1, 0.15, 0.2, 0.25, 0.3] : [0.1, 0.25, 0.5, 0.75, 1.0];
    var ILF = p.IL, VF = K_ === 2 ? 12 : 15;
    function rn(q) { return memo('rg', q, function (qq) { var r = KN.run(qq, qq.Vin, qq.IL), w = KN.ripple(qq, qq.Vin, qq.IL); r.a = w[0]; r.b = w[1]; r.dt = w[2]; return r; }); }
    function lineRows(rows) { return rows.filter(function (r) { return Math.abs(r.IL - ILF) < 1e-9; }); }
    function loadRows(rows) { return rows.filter(function (r) { return Math.abs(r.Vin - VF) < 1e-9; }); }
    return {
      compName: NAMES[K_] + (K_ === 0 ? ': ' + rLabel(p.Rs) + ' and a ' + p.Vz + ' V zener' : K_ === 1 ? ': zener on ' + rLabel(p.Rs) + ' driving an emitter follower' : ''),
      wiring: 'Variable DC supply carrying a 1 V peak-to-peak 100 Hz ripple → ' + NAMES[K_] + ' → rheostat load with an ammeter. Multimeter 1 reads the output (5½ digits), multimeter 2 the output ripple. Channel 1 shows the input ripple, channel 2 the output (AC coupled).',
      formula: K_ === 0 ? 'line = ΔV_o/ΔV_in = r_z/(R_s + r_z),   R_o = −ΔV_o/ΔI_L = R_s ∥ r_z' : K_ === 1 ? 'line ≈ r_z/(R_s + r_z),   R_o ≈ V_T/I_L + (R_s ∥ r_z)/(β + 1)' : 'line = ΔV_o/ΔV_in,   R_o = −ΔV_o/ΔI_L,   ripple rejection = 20 log(ΔV_in/ΔV_o)',
      controls: [{ param: 'Vin', label: 'Input voltage', short: 'V_IN', unit: 'V', digits: 1, vals: VIN },
        { param: 'IL', label: 'Load current', short: 'LOAD', unit: 'A', digits: 3, fmtv: function (v) { return fmt(v * 1000, 0) + ' mA'; }, vals: IL }],
      art: function () { var rs = resistor(-0.07, -0.03, K_ === 2 ? 330 : p.Rs, K_ === 2 ? 'Cin' : 'Rs'); diode(-0.02, -0.03, K_ === 2 ? 'D' : 'ZENER'); if (K_ === 1) to92(0.03, -0.03, 'SL100'); if (K_ === 2) to92(0.03, -0.03, '7805');
        capacitor(0.06, 0.0, 1e-4, 'Co', 'el'); resistor(0.08, -0.04, 100, 'LOAD'); battery(-0.12, 0.03, 'DC IN'); jumper([-0.085, -0.03], [-0.12, 0.02], 'red'); jumper([0.09, -0.04], [0.11, 0.03], 'black'); return function () {}; },
      trace: function (q) { var r = rn(q); return { dt: r.dt, ch: [{ y: r.a, color: YEL, name: 'V_in', center: q.Vin }, { y: r.b, color: CYA, name: 'V_out', center: r.Vout }] }; },
      meas: function (q) { var r = rn(q); return { lines: ['V_in ' + fmt(q.Vin, 1) + ' V, load ' + fmt(q.IL * 1000, 0) + ' mA: V_out = ' + fmt(r.Vout, 5) + ' V', 'Output ripple ' + fmt(r.rout * 1000, 2) + ' mV p-p for 1 V p-p in'],
        meters: [['V_out  DC', fmt(r.Vout, 5) + ' V'], ['RIPPLE p-p', fmt(r.rout * 1000, 2) + ' mV']], row: { Vin: q.Vin, IL: q.IL, Vout: r.Vout, rout: r.rout } }; },
      cols: [{ label: 'V_in (V)', get: function (r) { return fmt(r.Vin, 1); } }, { label: 'I_L (mA)', get: function (r) { return fmt(r.IL * 1000, 0); } },
        { label: 'V_out (V)', get: function (r) { return fmt(r.Vout, 5); } }, { label: 'Ripple (mV)', get: function (r) { return fmt(r.rout * 1000, 2); } }],
      need: 9,
      runs: VIN.filter(function (v) { return v >= (K_ === 2 ? 9 : 11) && v <= (K_ === 2 ? 16 : 17); }).map(function (v, i) { return i === 0 ? { Vin: v, IL: ILF } : { Vin: v }; })
        .concat(IL.filter(function (x) { return Math.abs(x - ILF) > 1e-9; }).map(function (x, i) { return i === 0 ? { Vin: VF, IL: x } : { IL: x }; })),
      okFn: function (rows) { return lineRows(rows).length >= 3 && loadRows(rows).length >= 3; },
      graph: { x: function (r) { return Math.abs(r.IL - ILF) < 1e-9 ? r.Vin : NaN; }, y: function (r) { return r.Vout; }, xlabel: 'V_in (V), at the fixed load', ylabel: 'V_out (V)', line: lineFit },
      result: function (rows) { var a = lineRows(rows), b = loadRows(rows), lr = ols(a.map(function (r) { return [r.Vin, r.Vout]; })).m, ro = -ols(b.map(function (r) { return [r.IL, r.Vout]; })).m;
        var rr = mean(rows.map(function (r) { return r.rout; }));
        return { label: 'Line regulation ΔV_out/ΔV_in', value: lr * 1000, unit: 'mV/V', digits: 3, truth: HK.TEXTBOOK.pe9_reg_line(p) * 1000,
          note: 'Slope of V_out against V_in at ' + fmt(ILF * 1000, 0) + ' mA (' + a.length + ' readings). Load regulation from the ' + fmt(VF, 0) + ' V readings: R_o = ' + (ro < 1 ? fmt(ro * 1000, 2) + ' mΩ' : fmt(ro, 3) + ' Ω') + '. Mean output ripple ' + fmt(rr * 1000, 2) + ' mV p-p for 1 V p-p in: a ripple rejection of ' + fmt(20 * ln10(1 / rr), 1) + ' dB.' }; },
      resultNote: K_ === 0 ? 'The zener holds the output because its slope resistance is small next to R_s: a volt more at the input changes the output by only r_z/(R_s + r_z). Load current is taken from the zener\'s share, so the output falls by R_s ∥ r_z per ampere until the zener current runs out.'
        : K_ === 1 ? 'The emitter follower copies the zener voltage less one V_BE while supplying the load itself; the zener sees only the base current, so the output resistance is about V_T/I_L plus the zener\'s source resistance divided by the current gain, far below the shunt regulator\'s.'
          : 'The IC regulator\'s error amplifier compares the output with an internal reference and corrects it, so both line and load regulation are a fraction of a millivolt; ripple on the input is rejected by the same factor as a slow change of input.',
      chips: ['What is line regulation?', 'Why does the series regulator do better?', 'What is ripple rejection?', 'Check my readings'],
      viva: [['A regulator\'s load regulation is best described by its', ['output resistance', 'input resistance', 'ripple frequency'], 0, 'The output falls by R_o per ampere of load.']] };
  };

  // ---------------------------------------------------------------- converters
  PLANS['pe9-converters'] = function () {
    var adc = K_ === 2, NAMES = ['R-2R ladder DAC', 'binary-weighted DAC', 'successive-approximation ADC'];
    if (adc) return {
      compName: '8-bit successive-approximation ADC on a 5 V reference', wiring: 'Generator\'s DC output (the input voltage) → ADC input; reference 5 V; the eight output bits drive the LED bar (MSB on the left). Multimeter 1 reads the input voltage, multimeter 2 shows the code.',
      formula: 'code = round((V_in − V_off)/LSB),   LSB = V_ref / 2⁸;   SAR: try each bit from the MSB, keep it if V_in ≥ the trial code',
      controls: [{ param: 'Vin', label: 'Input voltage', short: 'V_IN', unit: 'V', digits: 2, vals: rng(0, 5, 0.05) }],
      art: function () { dip8(-0.03, -0.03, 'ADC0804'); var bar = ledBar(0.05, 0.0, 8, '#ff4030'); battery(-0.12, 0.03, '5 V'); jumper([-0.045, -0.03], [-0.12, 0.02], 'red'); return function (q) { bar.set(KN.adc(q, q.Vin)); }; },
      trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.Vin; }, function (r) { return r.code; }), cur: [q.Vin, KN.adc(q, q.Vin)], xl: 'V_in (V)', yl: 'code' } }; },
      meas: function (q) { var c = KN.adc(q, q.Vin); return { lines: ['V_in = ' + fmt(q.Vin, 2) + ' V → code ' + c + ' (' + binStr(c, 8) + ')'], meters: [['V_in  DC', fmt(q.Vin, 3) + ' V'], ['CODE', String(c)]], row: { Vin: q.Vin, code: c } }; },
      cols: [{ label: 'V_in (V)', get: function (r) { return fmt(r.Vin, 2); } }, { label: 'Code', get: function (r) { return r.code; } }, { label: 'Binary', get: function (r) { return binStr(r.code, 8); } }],
      need: 8,
      runs: [0.3, 0.8, 1.2, 1.7, 2.0, 2.45, 3.1, 3.6, 4.2, 4.75].map(function (v) { return { Vin: v }; }),
      graph: { x: function (r) { return r.Vin; }, y: function (r) { return r.code; }, xlabel: 'V_in (V)', ylabel: 'Output code', line: lineFit },
      result: function (rows) { var l = ols(rows.map(function (r) { return [r.Vin, r.code]; }));
        return { label: 'Resolution (step size, 1 LSB)', value: 1000 / l.m, unit: 'mV', digits: 2, truth: p.Vref / 256 * 1000, note: 'From the slope of code against V_in (' + fmt(l.m, 2) + ' codes per volt); the line crosses code 0 at ' + fmt(-l.c / l.m * 1000, 1) + ' mV, the converter\'s offset with its half-LSB step. 8 bits on ' + fmt(p.Vref, 1) + ' V.' }; },
      resultNote: 'Each code covers one step of V_ref/256; the transfer characteristic is a staircase whose average slope gives the step size. The SAR loop needs only eight comparisons, one per bit.',
      chips: ['How does successive approximation work?', 'What limits the resolution?', 'Why the half-LSB offset?', 'Check my readings'],
      viva: [['The resolution of an 8-bit ADC on 5 V is about', ['19.5 mV', '5 mV', '0.6 V'], 0, '5/256 V.']] };
    return {
      compName: '4-bit ' + NAMES[K_] + ' with a summing op-amp', wiring: 'Four switches D3 (MSB) ... D0 route the ' + (K_ === 0 ? '2R legs of an R-2R ladder (R = ' + rLabel(p.R) + ')' : 'binary-weighted resistors R, 2R, 4R, 8R (R = ' + rLabel(p.R) + ')') + ' to the op-amp\'s virtual earth; feedback R_f = ' + rLabel(p.Rf) + '; reference ' + p.Vref + ' V. Multimeter 1 reads the output.',
      formula: K_ === 0 ? 'V_o = (V_ref R_f / R) · D / 2⁴,   step = V_ref R_f /(16 R)' : 'V_o = V_ref R_f Σ bᵢ / (2^(3−i) R),   step = V_ref R_f /(8 R)',
      controls: [{ param: 'D', label: 'Input code', short: 'CODE', unit: '', digits: 0, fmtv: function (v) { return v + ' (' + binStr(v, 4) + ')'; }, vals: rng(0, 15, 1) }],
      art: function () { var sw = switchRow(-0.06, -0.03, 4); dip8(0.05, -0.03, 'uA741'); resistor(0.0, -0.05, p.R, 'R'); resistor(0.0, -0.01, 2 * p.R, '2R'); resistor(0.05, -0.065, p.Rf, 'Rf'); battery(0.11, 0.03, '±12 V');
        jumper([-0.04, -0.03], [0.035, -0.03], 'yellow'); return function (q) { sw.set(Math.round(q.D)); }; },
      trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.D; }, function (r) { return r.V; }), cur: [q.D, KN.dac(q, Math.round(q.D))], xl: 'code D', yl: 'V_out (V)' } }; },
      meas: function (q) { var v = KN.dac(q, Math.round(q.D)); return { lines: ['Code ' + Math.round(q.D) + ' (' + binStr(Math.round(q.D), 4) + '): V_out = ' + fmt(v, 4) + ' V'], meters: [['V_out  DC', fmt(v, 4) + ' V'], ['CODE', binStr(Math.round(q.D), 4)]], row: { D: Math.round(q.D), V: v } }; },
      cols: [{ label: 'Code', get: function (r) { return r.D; } }, { label: 'D3D2D1D0', get: function (r) { return binStr(r.D, 4); } }, { label: 'V_out (V)', get: function (r) { return fmt(r.V, 4); } }],
      need: 12,
      runs: rng(0, 15, 1).map(function (d) { return { D: d }; }),
      graph: { x: function (r) { return r.D; }, y: function (r) { return r.V; }, xlabel: 'Input code D', ylabel: 'V_out (V)', line: lineFit },
      result: function (rows) { var l = ols(rows.map(function (r) { return [r.D, r.V]; })), inl = 0;
        rows.forEach(function (r) { inl = Math.max(inl, Math.abs(r.V - (l.m * r.D + l.c)) / l.m); });
        return { label: 'Step size (resolution)', value: l.m * 1000, unit: 'mV', digits: 2, truth: KN.dac_fit(p).lsb * 1000,
          note: 'Least-squares slope of V_out against the code over ' + rows.length + ' codes; design value ' + fmt(HK.TEXTBOOK.pe9_conv_main(p) * 1000, 2) + ' mV. Largest deviation from the line (integral non-linearity) ' + fmt(inl, 3) + ' LSB, from the 1 % resistors.' }; },
      resultNote: K_ === 0 ? 'An R-2R ladder needs only two resistor values, and every leg sees the same load, so its accuracy depends on matching, not on a wide spread of values. Its errors show as small departures from the straight line, largest at the MSB transition.'
        : 'A binary-weighted DAC needs resistors spanning 2ⁿ⁻¹ : 1; their tolerances weigh most on the MSB, so the largest deviation from the line comes at the code where the MSB switches on.',
      chips: ['Why is the R-2R ladder preferred?', 'What is non-linearity?', 'Where is the biggest error?', 'Check my readings'],
      viva: [['A 4-bit DAC has how many output levels?', ['16', '4', '15'], 0, '2⁴ codes.']] };
  };

  // ---------------------------------------------------------------- passive filters
  PLANS['pe9-passive-filters'] = function () {
    var NAMES = ['low-pass', 'high-pass', 'band-pass'], FS = decades(E6, 10, 100000).concat([1000000]);
    function g(q) { return memo('pf', q, function (qq) { return { db: KN.db(qq, qq.f), ph: KN.phase(qq, qq.f) }; }); }
    function corner(rows) { var pts = rows.map(function (r) { return [r.f, r.db]; });
      if (K_ < 2) return { fc: interpCross(pts, -3.0103, true) };
      var mx = Math.max.apply(null, rows.map(function (r) { return r.db; })), c = crossings(pts, mx - 3.0103); return { fL: c[0], fH: c[c.length - 1], fc: c.length >= 2 ? Math.sqrt(c[0] * c[c.length - 1]) : NaN }; }
    return {
      compName: 'Passive RC ' + NAMES[K_] + (K_ < 2 ? ', R = ' + rLabel(p.R) + ', C = ' + cLabel(p.C) : ': C1 = ' + cLabel(p.C) + ', R1 = ' + rLabel(p.R) + ' then R2 = ' + rLabel(p.R2) + ', C2 = ' + cLabel(p.C2)),
      wiring: 'Generator (1 V) → ' + (K_ === 0 ? 'R → output across C' : K_ === 1 ? 'C → output across R' : 'C1 → node across R1 → R2 → output across C2') + '. Channel 1 on the input, channel 2 on the output; the scope reads the gain in dB and the phase.',
      formula: K_ < 2 ? 'f_c = 1/(2π R C),   |H| = 1/√(1 + (f/f_c)^±2),   −3 dB and ∓45° at f_c' : 'H = jωR₁C₁ / (1 − ω²R₁C₁R₂C₂ + jω(R₁C₁ + R₂C₂ + R₁C₂)),   f₀ = 1/(2π√(R₁C₁R₂C₂)) = √(f_L f_H)',
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { resistor(-0.05, -0.03, p.R, K_ === 2 ? 'R1' : 'R', K_ === 1); capacitor(0.0, -0.03, p.C, K_ === 2 ? 'C1' : 'C', 'ceramic'); if (K_ === 2) { resistor(0.05, -0.03, p.R2, 'R2'); capacitor(0.09, -0.01, p.C2, 'C2', 'ceramic'); }
        jumper([-0.065, -0.03], [-0.12, 0.03], 'yellow'); jumper([0.0, -0.01], [0.1, 0.03], 'blue'); return function () {}; },
      trace: function (q) { var m = g(q), t = sineTrace(q.f, [1, Math.pow(10, m.db / 20)], [0, m.ph * Math.PI / 180], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var m = g(q); return { lines: [fLabel(q.f) + ': gain ' + fmt(m.db, 2) + ' dB (' + fmt(Math.pow(10, m.db / 20), 4) + ' V out), phase ' + fmt(m.ph, 1) + '°'],
        meters: [['FREQ', fLabel(q.f)], ['GAIN dB', fmt(m.db, 2)]], row: { f: q.f, db: m.db, ph: m.ph } }; },
      cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'V_out/V_in', get: function (r) { return fmt(Math.pow(10, r.db / 20), 4); } }, { label: 'Gain (dB)', get: function (r) { return fmt(r.db, 2); } }, { label: 'Phase (°)', get: function (r) { return fmt(r.ph, 1); } }],
      need: 10,
      runs: (K_ < 2 ? [100, 220, 470, 1000, 1500, 2200, 3300, 4700, 10000, 22000, 47000, 100000] : [10, 22, 47, 68, 100, 150, 220, 330, 470, 680, 1000, 1500, 2200, 3300, 4700, 10000, 22000]).map(function (f) { return { f: f }; }),
      okFn: function (rows) { return isFinite(corner(rows).fc); },
      graph: { x: function (r) { return ln10(r.f); }, y: function (r) { return r.db; }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain (dB)' },
      result: function (rows) { var c = corner(rows), s = rows.slice().sort(function (a, b) { return a.f - b.f; }), lo = s[0], hi = s[s.length - 1], sl = K_ === 1 ? (s[1].db - lo.db) / (ln10(s[1].f) - ln10(lo.f)) : (hi.db - s[s.length - 2].db) / (ln10(hi.f) - ln10(s[s.length - 2].f));
        return { label: K_ < 2 ? 'Cut-off frequency f_c' : 'Centre frequency f₀ = √(f_L f_H)', value: c.fc, unit: 'Hz', digits: 1, truth: HK.TEXTBOOK.pe9_filt_fc(p),
          note: (K_ < 2 ? 'Where the gain crosses −3.01 dB, interpolated on log f.' : '−3 dB frequencies ' + fmt(c.fL, 1) + ' Hz and ' + fmt(c.fH, 1) + ' Hz (bandwidth ' + fmt(c.fH - c.fL, 0) + ' Hz).') + ' Roll-off far from the corner: ' + fmt(Math.abs(sl), 1) + ' dB per decade.' }; },
      resultNote: 'The gain is flat in the pass band and falls 20 dB per decade beyond each corner, where the phase has moved by 45°. A band-pass made of two passive sections loads itself, so its peak is below 0 dB and its pass band wider than the two corners alone would give.',
      chips: ['Why −3 dB?', 'What is the phase at f_c?', 'Why does the band-pass peak below 0 dB?', 'Check my readings'],
      viva: [['A first-order RC filter\'s gain one decade past its corner is about', ['−20 dB', '−3 dB', '−40 dB'], 0, '20 dB per decade.']] };
  };

  // ---------------------------------------------------------------- resonance
  PLANS['pe9-resonance'] = function () {
    var par = Math.round(p.mode) === 1, f0n = 1 / (2 * Math.PI * Math.sqrt(p.L * p.C)), FS = [], k;
    for (k = -60; k <= 60; k++) FS.push(Math.round(f0n * (1 + k * 0.0025)));
    function I(q) { return memo('lc', q, function (qq) { return KN.cur(qq, qq.f); }); }
    function an(rows) { var s = rows.slice().sort(function (a, b) { return a.f - b.f; }), ex = s.reduce(function (m, r) { return par ? (r.I < m.I ? r : m) : (r.I > m.I ? r : m); }, s[0]);
      var c = linCross(s.map(function (r) { return [r.f, r.I]; }), par ? ex.I * Math.SQRT2 : ex.I / Math.SQRT2);
      if (c.length < 2) return null; var f1 = c[0], f2 = c[c.length - 1]; return { f1: f1, f2: f2, fr: Math.sqrt(f1 * f2), Q: Math.sqrt(f1 * f2) / (f2 - f1), ex: ex }; }
    var runs = []; for (k = (par ? -16 : -24); k <= (par ? 16 : 24); k += (par ? 1 : 2)) runs.push({ f: Math.round(f0n * (1 + k * 0.0025)) });
    return {
      compName: par ? 'Parallel tank: ' + (p.L * 1000) + ' mH coil ∥ ' + cLabel(p.C) : 'Series LCR: ' + (p.L * 1000) + ' mH coil, ' + cLabel(p.C) + ' and the circuit\'s resistance',
      wiring: 'Generator (' + p.V + ' V rms) → milliammeter → ' + (par ? 'the coil and the capacitor in parallel' : 'coil → capacitor (in series)') + ' → back. Multimeter 1 reads the frequency, multimeter 2 the current.',
      formula: par ? 'f_a = (1/2π)√(1/LC − R²/L²),  current least;   Q = 2π f_a L / R,   bandwidth where I = √2 I_min' : 'f_r = 1/(2π√(LC)),   I_max = V/R;   Q = f_r/(f₂ − f₁) = (1/R)√(L/C)',
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, vals: FS }],
      art: function () { coil(-0.05, -0.03, (p.L * 1000) + ' mH'); capacitor(0.02, -0.03, p.C, 'C', 'ceramic'); if (!par) resistor(0.07, -0.03, 10, 'r');
        jumper([-0.065, -0.03], [-0.12, 0.03], 'yellow'); jumper([0.03, -0.03], [0.1, 0.03], 'blue'); return function () {}; },
      trace: function (q) { var i = I(q), t = sineTrace(q.f, [p.V * Math.SQRT2, i * 1000 * Math.SQRT2], [0, 0], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'V' }, { y: t.ys[1], color: CYA, name: 'I', unit: 'mA' }] }; },
      meas: function (q) { var i = I(q); return { lines: ['f = ' + fmt(q.f, 0) + ' Hz: I = ' + fmt(i * 1000, 4) + ' mA rms'], meters: [['FREQ', fmt(q.f, 0) + ' Hz'], ['I  rms', fmt(i * 1000, 4) + ' mA']], row: { f: q.f, I: i } }; },
      cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'I (mA)', get: function (r) { return fmt(r.I * 1000, 4); } }],
      need: 15,
      runs: runs,
      okFn: function (rows) { return !!an(rows); },
      graph: { x: function (r) { return r.f; }, y: function (r) { return r.I * 1000; }, xlabel: 'f (Hz)', ylabel: 'I (mA)' },
      result: function (rows) { var a = an(rows); if (!a) return null;
        return { label: 'Quality factor Q', value: a.Q, unit: '', digits: 2, truth: HK.TEXTBOOK.pe9_lcr_q(p),
          note: 'Half-power frequencies ' + fmt(a.f1, 1) + ' and ' + fmt(a.f2, 1) + ' Hz (where I = ' + (par ? '√2 I_min' : 'I_max/√2') + '), so the ' + (par ? 'anti-' : '') + 'resonant frequency √(f₁f₂) = ' + fmt(a.fr, 1) + ' Hz (textbook ' + fmt(HK.TEXTBOOK.pe9_lcr_fr(p), 1) + ' Hz) and Q = f_r/(f₂ − f₁).' }; },
      resultNote: par ? 'At anti-resonance the coil\'s and the capacitor\'s currents nearly cancel, so the generator supplies only the small in-phase current through the dynamic resistance L/(CR): the current dips. A smaller coil resistance gives a deeper, narrower dip and a higher Q.'
        : 'At resonance the inductive and capacitive reactances cancel and only the resistance limits the current; the sharper the peak, the higher the Q. The half-power frequencies lie symmetrically on a log scale about f_r.',
      chips: ['Why does the current peak?', 'What does Q tell me?', 'Why does a parallel circuit draw less current?', 'Check my readings'],
      viva: [['Doubling R in a series LCR circuit makes Q', ['half', 'double', 'unchanged'], 0, 'Q = (1/R)√(L/C).']] };
  };

  // ---------------------------------------------------------------- op-amp linear circuits
  PLANS['pe9-opamp-linear'] = function () {
    var NAMES = ['inverting', 'non-inverting', 'summing', 'difference', 'voltage follower', 'averaging'];
    var FS = [10, 100, 1000, 3000, 10000, 20000, 30000, 50000, 70000, 100000, 150000, 200000, 300000, 500000, 700000, 1000000, 1500000, 2000000, 3000000, 5000000];
    var GN = KN.gng(p), G = GN[0], NG = GN[1];
    function g(q) { return memo('ol', q, function (qq) { return KN.gain(qq, qq.f); }); }
    function f3Of(r, rows) { var lo = rows.slice().sort(function (a, b) { return a.f - b.f; })[0]; if (!lo || lo.f > 1000 || r.g > 0.9 * lo.g || r.g < 0.15 * lo.g) return NaN; var k = lo.g / r.g; return r.f / Math.sqrt(k * k - 1); }
    return {
      compName: '741 ' + NAMES[K_] + ' amplifier', wiring: K_ === 4 ? 'Generator (50 mV) → pin 3; output tied to pin 2; ±12 V. Channel 1 on the input, channel 2 on the output.'
        : 'Generator (50 mV) → ' + (K_ === 1 ? 'pin 3, R_1 = ' + rLabel(p.R1) + ' from pin 2 to earth' : 'R_1 = ' + rLabel(p.R1) + ' into pin 2' + (K_ === 2 || K_ === 5 ? ', a second input V_2 through another R_1' : '') + (K_ === 3 ? ', V_2 through R_1 to pin 3 with R_f to earth' : '')) + '; R_f = ' + rLabel(p.Rf) + ' from the output to pin 2; ±12 V. Channel 1 on the input, channel 2 on the output.',
      formula: 'G = ' + (K_ === 0 ? '−R_f/R_1' : K_ === 1 ? '1 + R_f/R_1' : K_ === 2 ? '−R_f/R_1 per input (V_o = −R_f(V₁+V₂)/R_1)' : K_ === 3 ? 'R_f/R_1 on (V₂ − V₁)' : K_ === 4 ? '1' : '−(V₁ + V₂)/2  (R_f = R_1/2)') + ' = ' + fmt(G, 3) + ';   noise gain NG = ' + fmt(NG, 2) + ';   f_3dB = f_a(1 + A₀/NG),  GBW = f_3dB · NG',
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { dip8(0.0, -0.02, 'uA741'); if (K_ !== 4) { resistor(-0.06, -0.02, p.R1, 'R1'); resistor(0.0, -0.06, p.Rf, 'Rf'); } if (K_ === 2 || K_ === 3 || K_ === 5) resistor(-0.06, 0.02, p.R1, 'R1\''); battery(0.1, 0.03, '±12 V');
        jumper([-0.075, -0.02], [-0.12, 0.03], 'yellow'); jumper([0.012, -0.02], [0.06, 0.02], 'blue'); return function () {}; },
      trace: function (q) { var m = g(q), t = sineTrace(q.f, [p.V1, p.V1 * m], [0, G < 0 ? Math.PI : 0], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var m = g(q); return { lines: [fLabel(q.f) + ': gain ' + fmt(m, 4) + ' (' + fmt(20 * ln10(m), 2) + ' dB), output ' + fmt(p.V1 * m * 1000, 2) + ' mV peak',
        K_ === 2 || K_ === 3 || K_ === 5 ? 'DC check: V₁ = ' + fmt(p.V1 * 1000, 0) + ' mV, V₂ = ' + fmt(p.V2 * 1000, 0) + ' mV → V_o = ' + fmt(KN.dc_out(q) * 1000, 2) + ' mV' : 'DC gain ' + fmt(KN.dc_out(q) / p.V1, 4)],
        meters: [['FREQ', fLabel(q.f)], ['GAIN', fmt(m, 4)]], row: { f: q.f, g: m } }; },
      cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'V_out (mV)', get: function (r) { return fmt(p.V1 * r.g * 1000, 2); } }, { label: 'Gain', get: function (r) { return fmt(r.g, 4); } },
        { label: 'f_3dB (kHz)', get: function (r, i, rows) { var v = f3Of(r, rows); return isFinite(v) ? fmt(v / 1000, 2) : '—'; } }],
      need: 10,
      runs: [10, 100, 1000, 10000, 30000, 50000, 70000, 100000, 150000, 200000, 300000, 500000, 1000000, 1500000, 2000000, 3000000].map(function (f) { return { f: f }; }),
      okFn: function (rows) { return rows.filter(function (r) { return isFinite(f3Of(r, rows)); }).length >= 3; },
      graph: { x: function (r) { return ln10(r.f); }, y: function (r) { return 20 * ln10(r.g); }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain (dB)' },
      result: function (rows) { var gb = rows.map(function (r) { var f3 = f3Of(r, rows); return isFinite(f3) ? f3 * NG : NaN; }).filter(isFinite), lo = rows.slice().sort(function (a, b) { return a.f - b.f; })[0];
        return { label: 'Gain-bandwidth product', value: mean(gb) / 1e6, unit: 'MHz', digits: 3, truth: p.A0 * p.fa / 1e6,
          note: 'Low-frequency gain ' + fmt(lo.g, 4) + ' (ideal |G| = ' + fmt(Math.abs(G), 3) + '). For each reading between 15 % and 90 % of it: f_3 = f/√((G₀/G)² − 1), then GBW = f_3 × NG with NG = ' + fmt(NG, 2) + '; average of ' + gb.length + '.' }; },
      resultNote: 'The gain is set by the resistors alone until the op-amp\'s own gain, falling 20 dB per decade, is no longer large compared with the noise gain; then the amplifier rolls off. The -3 dB frequency times the noise gain is the same for every circuit: the gain-bandwidth product.',
      chips: ['What is the noise gain?', 'Why does the follower have the widest bandwidth?', 'How does the summing amplifier add?', 'Check my readings'],
      viva: [['A summing amplifier with two 10 kΩ inputs and R_f = 100 kΩ has a noise gain of', ['21', '11', '10'], 0, '1 + R_f/(R_1 ∥ R_1).']] };
  };

  // ---------------------------------------------------------------- integrator / differentiator
  PLANS['pe9-integ-diff'] = function () {
    var dif = K_ === 1, W = Math.round(p.wave), WN = ['square', 'sine', 'triangle'][W], FS = dif ? [200, 500, 1000, 2000] : [1000, 2000, 5000, 10000];
    function an(q) { return memo('id', q, function (qq) { var t = KN.trace(qq), a = KN.analyse(qq); return { x: t[0], y: t[1], dt: t[2], vpp: a.Vpp, rc: a.tau, dec: a.decay }; }); }
    return {
      compName: (dif ? 'Op-amp differentiator: unknown C in series with R_s = ' + rLabel(p.Rs) + ', feedback R = ' + rLabel(p.R) : 'Op-amp integrator: input R = ' + rLabel(p.R) + ', unknown feedback C shunted by ' + rLabel(p.Rf)) + ', ' + WN + ' input',
      wiring: 'Generator (' + WN + ', ' + p.Vp + ' V peak) → ' + (dif ? 'R_s → C → pin 2; R from the output to pin 2' : 'R → pin 2; C and R_f from the output to pin 2') + '; pin 3 earthed; ±12 V. Channel 1 on the input, channel 2 on the output.',
      formula: dif ? (W === 0 ? 'spikes decay as e^(−t/R_sC):  RC = R · τ_decay / R_s' : W === 1 ? 'V_pp = 2ωRC V_p  ⇒  RC = V_pp/(2ω V_p)' : 'square of amplitude RC · 4V_p f  ⇒  RC = V_pp/(8 V_p f)')
        : (W === 0 ? 'triangle of V_pp = V_p T/(2RC)  ⇒  RC = V_p T/(2 V_pp)' : W === 1 ? 'V_pp = 2V_p/(ωRC)  ⇒  RC = 2V_p/(ω V_pp)' : 'parabolic arcs of V_pp = V_p T/(4RC)  ⇒  RC = V_p T/(4 V_pp)'),
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { dip8(0.0, -0.02, 'uA741'); resistor(-0.06, -0.02, dif ? p.Rs : p.R, dif ? 'Rs' : 'R'); capacitor(dif ? -0.03 : 0.0, dif ? 0.01 : -0.06, p.C, 'C', 'ceramic', true); resistor(0.0, -0.06, dif ? p.R : p.Rf, dif ? 'R' : 'Rf');
        battery(0.1, 0.03, '±12 V'); jumper([-0.075, -0.02], [-0.12, 0.03], 'yellow'); jumper([0.012, -0.02], [0.06, 0.02], 'blue'); return function () {}; },
      trace: function (q) { var a = an(q); return { dt: a.dt, ch: [{ y: a.x, color: YEL, name: 'IN' }, { y: a.y, color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var a = an(q), sq = dif && W === 0;
        return { lines: [sq ? 'Spike height ' + fmt(a.vpp / 2, 3) + ' V; falls to 1/e in ' + fmt(a.dec * 1e6, 3) + ' µs' : fLabel(q.f) + ': output ' + fmt(a.vpp, 4) + ' V peak to peak', 'Time constant RC from it: ' + fmt(a.rc * 1e6, 2) + ' µs'],
          meters: [[sq ? 'DECAY 1/e' : 'OUT p-p', sq ? fmt(a.dec * 1e6, 3) + ' µs' : fmt(a.vpp, 4) + ' V'], ['FREQ', fLabel(q.f)]], row: { f: q.f, vpp: a.vpp, dec: a.dec, rc: a.rc } }; },
      cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: dif && W === 0 ? 'τ_decay (µs)' : 'V_pp (V)', get: function (r) { return dif && W === 0 ? fmt(r.dec * 1e6, 3) : fmt(r.vpp, 4); } }, { label: 'RC (µs)', get: function (r) { return fmt(r.rc * 1e6, 2); } }, { label: 'C (nF)', get: function (r) { return fmt(r.rc / p.R * 1e9, 3); } }],
      need: 3,
      runs: FS.map(function (f) { return { f: f }; }),
      graph: { x: function (r) { return 1000 / r.f; }, y: function (r) { return dif && W === 0 ? r.dec * 1e6 : r.vpp; }, xlabel: 'Period T (ms)', ylabel: dif && W === 0 ? 'τ_decay (µs)' : 'V_pp (V)' },
      result: function (rows) { var c = mean(rows.map(function (r) { return r.rc / p.R; }));
        return { label: 'Unknown capacitor C', value: c * 1e9, unit: 'nF', digits: 3, truth: p.C * 1e9, note: 'C = RC / R with R = ' + rLabel(p.R) + ', averaged over ' + rows.length + ' frequencies; RC = ' + fmt(c * p.R * 1e6, 2) + ' µs.' }; },
      resultNote: dif ? 'The differentiator\'s output follows the slope of its input: a triangle gives a square, a sine a cosine of amplitude growing with frequency, and a square wave gives spikes whose decay is set by R_s and C.'
        : 'The integrator\'s output is the running area under its input: a square wave gives a triangle, a sine a cosine of amplitude falling with frequency, a triangle parabolic arcs. R_f keeps the output from drifting but barely changes it at these frequencies.',
      chips: ['Why does the output fall with frequency?', 'What does R_f do?', 'Why R_s in a differentiator?', 'Check my readings'],
      viva: [['An integrator\'s output for a sine input', ['lags by 90° and falls as 1/f', 'leads by 90° and rises with f', 'is a square wave'], 0, 'The integral of sin is −cos.']] };
  };

  // ---------------------------------------------------------------- comparators, peak detector, instrumentation amplifier
  PLANS['pe9-comparators'] = function () {
    if (K_ === 0) {
      var VALS = rng(-3, 3, 0.1).map(function (v) { return Math.round(v * 10) / 10000; });
      return {
        compName: '741 with no feedback as a zero-crossing detector', wiring: 'Generator\'s DC offset (fine control, 0.1 mV steps) → pin 3; pin 2 earthed; ±15 V. Multimeter 1 reads the input (a 6½-digit meter), multimeter 2 the output. The scope plots the output against the input.',
        formula: 'V_o = clip(A₀ (V_in − V_os), ±V_sat);   switches where V_in = V_os',
        controls: [{ param: 'Vin', label: 'DC input', short: 'V_IN', unit: 'V', digits: 4, fmtv: function (v) { return fmt(v * 1000, 1) + ' mV'; }, vals: VALS }],
        art: function () { dip8(0.0, -0.02, 'uA741'); battery(0.1, 0.03, '±15 V'); var lp = ledPart(0.06, -0.03, '#40ff40', 'OUT+'); jumper([-0.012, -0.02], [-0.12, 0.03], 'yellow'); return function (q) { lp.set(KN.zcd(q, q.Vin) > 0 ? 1 : 0); }; },
        trace: function (q) { return { xy: { pts: xyRows(function (r) { return r.Vin * 1000; }, function (r) { return r.Vo; }), cur: [q.Vin * 1000, KN.zcd(q, q.Vin)], xl: 'V_in (mV)', yl: 'V_out (V)' } }; },
        meas: function (q) { var v = KN.zcd(q, q.Vin); return { lines: ['V_in = ' + fmt(q.Vin * 1000, 2) + ' mV: V_out = ' + fmt(v, 3) + ' V'], meters: [['V_in', fmt(q.Vin * 1000, 2) + ' mV'], ['V_out', fmt(v, 3) + ' V']], row: { Vin: q.Vin, Vo: v } }; },
        cols: [{ label: 'V_in (mV)', get: function (r) { return fmt(r.Vin * 1000, 2); } }, { label: 'V_out (V)', get: function (r) { return fmt(r.Vo, 3); } }],
        need: 8,
        runs: [-3, -2, -1, 0, 1, 1.5, 1.7, 1.8, 1.9, 2.0, 2.5, 3].map(function (v) { return { Vin: v / 1000 }; }),
        okFn: function (rows) { return linCross(rows.map(function (r) { return [r.Vin, r.Vo]; }), 0).length >= 1; },
        graph: { x: function (r) { return r.Vin * 1000; }, y: function (r) { return r.Vo; }, xlabel: 'V_in (mV)', ylabel: 'V_out (V)' },
        result: function (rows) { var c = linCross(rows.map(function (r) { return [r.Vin, r.Vo]; }), 0);
          return { label: 'Switching point (input offset voltage)', value: c[0] * 1000, unit: 'mV', digits: 3, truth: p.Vos * 1000, note: 'Where the output passes through zero, interpolated between the readings either side. The output swings between ±' + p.Vsat + ' V; the steep part is only about ' + fmt(2 * p.Vsat / p.A0 * 1e6, 0) + ' µV wide.' }; },
        resultNote: 'With no feedback the op-amp\'s whole gain acts on the input, so its output jumps from one rail to the other within microvolts. It does so not at zero but at the input offset voltage, which is why a zero-crossing detector is trimmed or followed by hysteresis.',
        chips: ['Why does it switch at a few millivolts?', 'What is the transfer characteristic?', 'Why add hysteresis?', 'Check my readings'],
        viva: [['A comparator\'s output switches when', ['V_in − V_os changes sign', 'V_in reaches V_sat', 'the slew rate is reached'], 0, 'Open loop.']] };
    }
    if (K_ === 1) {
      function pk(q) { return memo('pk', q, function (qq) { var r = KN.peak(qq), hi = maxOf(r[1]), lo = minOf(r[1]); return { x: r[0], y: r[1], dt: r[2], vpk: hi, rip: hi - lo }; }); }
      return {
        compName: 'Precision peak detector: 741, diode, hold capacitor (unknown) and a ' + rLabel(p.RL) + ' load', wiring: 'Generator (sine, ' + p.Vp + ' V peak) → pin 3; diode from the output to the hold capacitor; the capacitor\'s voltage fed back to pin 2; ' + rLabel(p.RL) + ' load across the capacitor. Channel 1 on the input, channel 2 on the capacitor.',
        formula: 'V_out ≈ V_p;   droop between peaks ΔV ≈ V_p T/(R_L C)  ⇒  C ≈ V_p /(f R_L ΔV)',
        controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: [200, 500, 1000, 2000, 5000] }],
        art: function () { dip8(0.0, -0.02, 'uA741'); diode(0.05, -0.02, 'D'); capacitor(0.08, 0.01, p.Ch, 'Ch', 'el', true); resistor(0.08, -0.05, p.RL, 'RL'); battery(0.11, 0.035, '±12 V'); jumper([-0.012, -0.02], [-0.12, 0.03], 'yellow'); return function () {}; },
        trace: function (q) { var a = pk(q); return { dt: a.dt, ch: [{ y: a.x, color: YEL, name: 'IN' }, { y: a.y, color: CYA, name: 'HOLD' }] }; },
        meas: function (q) { var a = pk(q); return { lines: ['Held peak ' + fmt(a.vpk, 4) + ' V, droop between peaks ' + fmt(a.rip * 1000, 3) + ' mV at ' + fLabel(q.f)], meters: [['HOLD  DC', fmt(a.vpk, 4) + ' V'], ['DROOP p-p', fmt(a.rip * 1000, 3) + ' mV']], row: { f: q.f, vpk: a.vpk, rip: a.rip } }; },
        cols: [{ label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'Held (V)', get: function (r) { return fmt(r.vpk, 4); } }, { label: 'Droop (mV)', get: function (r) { return fmt(r.rip * 1000, 3); } }, { label: 'C (µF)', get: function (r) { return fmt(r.vpk / (r.f * p.RL * r.rip) * 1e6, 3); } }],
        need: 4,
        runs: [200, 500, 1000, 2000, 5000].map(function (f) { return { f: f }; }),
        graph: { x: function (r) { return 1000 / r.f; }, y: function (r) { return r.rip * 1000; }, xlabel: 'Period T (ms)', ylabel: 'Droop (mV)', line: originFit },
        result: function (rows) { var c = mean(rows.map(function (r) { return r.vpk / (r.f * p.RL * r.rip); }));
          return { label: 'Hold capacitor C', value: c * 1e6, unit: 'µF', digits: 3, truth: p.Ch * 1e6, note: 'C = V_p T/(R_L ΔV) averaged over ' + rows.length + ' frequencies; the held level equals the input peak ' + fmt(rows[0].vpk, 4) + ' V, with no diode drop because the op-amp is inside the loop.' }; },
        resultNote: 'The op-amp drives the diode until the capacitor reaches the input\'s peak, so the diode\'s 0.6 V is not lost. Between peaks the capacitor discharges through the load, drooping in proportion to the period: a larger capacitor or a lighter load holds better.',
        chips: ['Why is there no diode drop?', 'What sets the droop?', 'Why does the droop grow at low frequency?', 'Check my readings'],
        viva: [['Doubling the hold capacitor makes the droop', ['half', 'double', 'unchanged'], 0, 'ΔV ≈ V_p T/(R_L C).']] };
    }
    var MN = ['differential 10 mV', 'common mode 1 V'];
    function ia(q) { return memo('ia', q, function (qq) { var r = KN.ina(qq, qq.Rg); return { ad: r[0], acm: r[1] }; }); }
    return {
      compName: 'Three-op-amp instrumentation amplifier: R = ' + rLabel(p.R) + ', R_g from the box, difference stage ' + rLabel(p.Ra) + ' / ' + rLabel(p.Rb), wiring: 'Two input followers with gain set by R_g, then a difference amplifier. The generator feeds either a differential 10 mV or the same 1 V to both inputs. Multimeter 1 reads the output, multimeter 2 the gain.',
      formula: 'A_d = (1 + 2R/R_g) R_b/R_a,   A_cm from the mismatch of the difference stage,   CMRR = A_d/|A_cm|',
      controls: [{ param: 'mode', label: 'Input', short: 'INPUT', unit: '', digits: 0, names: MN, vals: [0, 1] }, { param: 'Rg', label: 'Gain resistor R_g', short: 'R_g', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [100, 220, 470, 1000, 2200, 4700, 10000] }],
      art: function () { dip8(-0.04, -0.02, 'TL074'); var rg = resistor(-0.09, -0.02, p.Rg, 'Rg'); resistor(0.02, -0.04, p.Ra, 'Ra'); resistor(0.02, 0.0, p.Rb, 'Rb'); resistor(0.07, -0.04, p.Ra, 'Ra'); resistor(0.07, 0.0, p.Rb, 'Rb');
        battery(0.11, 0.035, '±12 V'); jumper([-0.105, -0.02], [-0.12, 0.03], 'yellow'); return function (q) { rg.set(q.Rg); }; },
      trace: function (q) { var a = ia(q), cm = Math.round(q.mode) === 1, vin = cm ? 1 : 0.01, t = sineTrace(1000, [vin, vin * (cm ? a.acm : a.ad)], [0, 0], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var a = ia(q), cm = Math.round(q.mode) === 1, out = cm ? a.acm * 1 : a.ad * 0.01;
        return { lines: [MN[Math.round(q.mode)] + ', R_g = ' + rLabel(q.Rg) + ': V_out = ' + fmt(out * 1000, 4) + ' mV peak', 'Gain ' + (cm ? 'A_cm = ' + fmt(a.acm, 6) : 'A_d = ' + fmt(a.ad, 3))],
          meters: [['V_out', fmt(out * 1000, 4) + ' mV'], ['GAIN', cm ? fmt(a.acm, 6) : fmt(a.ad, 3)]], row: { mode: Math.round(q.mode), Rg: q.Rg, gain: cm ? a.acm : a.ad } }; },
      cols: [{ label: 'Input', get: function (r) { return r.mode ? 'common' : 'diff'; } }, { label: 'R_g (Ω)', get: function (r) { return fmt(r.Rg, 0); } }, { label: 'Gain', get: function (r) { return r.mode ? fmt(r.gain, 6) : fmt(r.gain, 3); } },
        { label: 'CMRR (dB)', get: function (r, i, rows) { var c = rows.filter(function (x) { return x.mode === 1; }); return !r.mode && c.length ? fmt(20 * ln10(r.gain / Math.abs(mean(c.map(function (x) { return x.gain; })))), 1) : '—'; } }],
      need: 7,
      runs: [{ mode: 0, Rg: 100 }, { Rg: 470 }, { Rg: 1000 }, { Rg: 4700 }, { Rg: 10000 }, { mode: 1, Rg: 100 }, { Rg: 1000 }, { Rg: 10000 }],
      okFn: function (rows) { return rows.some(function (r) { return r.mode === 1; }) && rows.filter(function (r) { return r.mode === 0; }).length >= 3; },
      graph: { x: function (r) { return r.mode ? NaN : 1 + 2 * p.R / r.Rg; }, y: function (r) { return r.mode ? NaN : r.gain; }, xlabel: '1 + 2R/R_g', ylabel: 'Differential gain A_d', line: originFit },
      result: function (rows) { var c = mean(rows.filter(function (r) { return r.mode === 1; }).map(function (r) { return r.gain; })), d = rows.filter(function (r) { return r.mode === 0; }).sort(function (a, b) { return b.gain - a.gain; })[0];
        return { label: 'Common-mode gain A_cm', value: c, unit: '', digits: 6, truth: HK.TEXTBOOK.pe9_cmp_main(p), note: 'The same for every R_g: the input stage passes a common-mode signal with gain 1. At the highest gain (A_d = ' + fmt(d.gain, 1) + ') the CMRR is ' + fmt(20 * ln10(d.gain / Math.abs(c)), 1) + ' dB.' }; },
      resultNote: 'R_g sets the differential gain without touching the common-mode gain, which comes only from the difference stage\'s resistor mismatch. So the CMRR rises with the gain: the reason instrumentation amplifiers take their gain in the first stage.',
      chips: ['Why doesn\'t R_g change A_cm?', 'What limits the CMRR?', 'Why three op-amps?', 'Check my readings'],
      viva: [['An instrumentation amplifier\'s CMRR improves when', ['its differential gain is raised with R_g', 'R_g is removed', 'the supply is raised'], 0, 'A_cm stays the same.']] };
  };

  // ---------------------------------------------------------------- triangle-wave generator
  PLANS['pe9-triangle-gen'] = function () {
    function an(q) { return memo('tr', q, function (qq) { var t = KN.trace(qq), a = KN.analyse(qq); return { y: t[0], s: t[1], dt: t[2], f: a.f, amp: a.amp }; }); }
    return {
      compName: 'Schmitt comparator (R1 = ' + rLabel(p.R1) + ', R2 = ' + rLabel(p.R2) + ') and integrator (R from the box, unknown C)', wiring: 'Op-amp 1: Schmitt comparator with positive feedback R2 and input R1 from the triangle output. Op-amp 2: inverting integrator of R and C driven by the comparator\'s square wave. Channel 1 on the triangle, channel 2 on the square wave.',
      formula: 'f = R2 / (4 R1 R C),   amplitude = V_sat R1/R2',
      controls: [{ param: 'R', label: 'Integrator resistor', short: 'R', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [4700, 6800, 10000, 15000, 22000, 33000, 47000] }],
      art: function () { dip8(-0.04, -0.02, 'TL072'); resistor(-0.09, -0.02, p.R1, 'R1'); resistor(-0.04, -0.06, p.R2, 'R2'); var r = resistor(0.03, -0.02, p.R, 'R'); capacitor(0.07, -0.02, p.C, 'C', 'ceramic', true); battery(0.11, 0.035, '±15 V'); return function (q) { r.set(q.R); }; },
      trace: function (q) { var a = an(q); return { dt: a.dt, ch: [{ y: a.y, color: YEL, name: 'TRI' }, { y: a.s, color: CYA, name: 'SQ' }] }; },
      meas: function (q) { var a = an(q); return { lines: ['R = ' + rLabel(q.R) + ': f = ' + fmt(a.f, 1) + ' Hz, triangle amplitude ' + fmt(a.amp, 3) + ' V'], meters: [['FREQ', fmt(a.f, 1) + ' Hz'], ['AMPL', fmt(a.amp, 3) + ' V']], row: { R: q.R, f: a.f, amp: a.amp } }; },
      cols: [{ label: 'R (kΩ)', get: function (r) { return fmt(r.R / 1000, 1); } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 1); } }, { label: 'Amplitude (V)', get: function (r) { return fmt(r.amp, 3); } }],
      need: 5,
      runs: [4700, 10000, 15000, 22000, 33000, 47000].map(function (r) { return { R: r }; }),
      graph: { x: function (r) { return 1000 / r.R; }, y: function (r) { return r.f; }, xlabel: '1/R (per kΩ)', ylabel: 'f (Hz)', line: originFit },
      result: function (rows) { var m = origin(rows.map(function (r) { return [1 / r.R, r.f]; }));
        return { label: 'Integrator capacitor C', value: p.R2 / (4 * p.R1 * m) * 1e9, unit: 'nF', digits: 3, truth: p.C * 1e9, note: 'Slope of f against 1/R = ' + fmt(m, 1) + ' Hz·Ω = R2/(4 R1 C). The amplitude stays at V_sat R1/R2 = ' + fmt(mean(rows.map(function (r) { return r.amp; })), 3) + ' V whatever R is.' }; },
      resultNote: 'The integrator\'s ramp rate is V_sat/(RC); the comparator reverses it each time the ramp reaches ±V_sat R1/R2. So R and C set only the frequency, and R1/R2 only the amplitude.',
      chips: ['Why is the amplitude independent of R?', 'What sets the frequency?', 'Why positive feedback?', 'Check my readings'],
      viva: [['Halving the integrator resistor makes the frequency', ['double', 'half', 'unchanged'], 0, 'f ∝ 1/(RC).']] };
  };

  // ---------------------------------------------------------------- sweep generators
  PLANS['pe9-sweep'] = function () {
    var NAMES = ['RC sweep (gated)', 'UJT with a constant-current charger', 'UJT relaxation sawtooth', 'zener-triggered sawtooth', 'bootstrap sweep'];
    var Vp = p.eta * p.V + p.Vd;
    function cOf(r) { var T = r.T, R = r.R;
      if (K_ === 0) return T / (R * Math.log(p.V / (p.V - p.Vs)));
      if (K_ === 1) { var I = (p.Vz - p.Vbe) / R; return T / (p.ro * Math.log((I * p.ro - p.Vv) / (I * p.ro - Vp))); }
      if (K_ === 2) return T / (R * Math.log((p.V - p.Vv) / (p.V - Vp)));
      if (K_ === 3) return T / (R * Math.log((p.V - p.Vce) / (p.V - p.Vz - p.Vbe)));
      return T * (1 - p.A) / (R * Math.log(1 / (1 - (1 - p.A) * p.Vs / p.V))); }
    function an(q) { return memo('sw', q, function (qq) { var t = KN.trace(qq), a = KN.analyse(qq); return { y: t[0], dt: t[1], T: a.T, es: a.es, lo: a.lo, hi: a.hi }; }); }
    return {
      compName: NAMES[K_] + ', charging resistor R from the box, unknown C, supply ' + p.V + ' V', wiring: K_ === 0 ? 'R from the supply charges C; a transistor switch, gated by the generator, discharges C each time the sweep reaches ' + p.Vs + ' V.' : K_ === 1 ? 'A PNP current source (base held by a ' + p.Vz + ' V zener, emitter resistor R) charges C; a 2N2646 UJT discharges it at its peak voltage.' : K_ === 2 ? 'R charges C from ' + p.V + ' V; a 2N2646 UJT fires at η V + V_D and discharges C to its valley voltage.' : K_ === 3 ? 'R charges C from ' + p.V + ' V; a transistor triggered through a ' + p.Vz + ' V zener discharges C at V_z + V_BE.' : 'R charges C; an emitter follower of gain ' + p.A + ' lifts the top of R with the capacitor, so the charging current stays nearly constant; the gate discharges C at ' + p.Vs + ' V.',
      formula: 'T = τ ln((V_∞ − V_lo)/(V_∞ − V_hi)),   e_s = (V_hi − V_lo)/(V_∞ − V_lo)' + (K_ === 1 ? ';  constant current I = (V_z − V_BE)/R into r_o: V_∞ = I r_o, τ = r_o C  (≈ C (V_p − V_v)/I while I r_o ≫ V_p)' : ''),
      controls: [{ param: 'R', label: 'Charging resistor', short: 'R', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [4700, 10000, 22000, 47000, 100000] }],
      art: function () { var r = resistor(-0.07, -0.02, p.R, 'R'); capacitor(-0.02, 0.01, p.C, 'C', 'ceramic', true); to92(0.03, -0.02, K_ === 1 || K_ === 2 ? '2N2646' : 'BC547'); if (K_ === 1 || K_ === 3) diode(0.07, -0.02, 'ZENER'); if (K_ === 1) to92(0.07, 0.02, 'BC557');
        battery(0.11, 0.035, p.V + ' V'); jumper([-0.085, -0.02], [-0.12, 0.03], 'red'); return function (q) { r.set(q.R); }; },
      trace: function (q) { var a = an(q); return { dt: a.dt, ch: [{ y: a.y, color: YEL, name: 'SWEEP' }], marks: [{ kind: 'h', ch: 0, y: a.hi }, { kind: 'h', ch: 0, y: a.lo }] }; },
      meas: function (q) { var a = an(q); return { lines: ['R = ' + rLabel(q.R) + ': sweep period ' + eng(a.T, 's') + ', from ' + fmt(a.lo, 2) + ' V to ' + fmt(a.hi, 2) + ' V', 'Slope error (1 − end slope/start slope) ' + fmt(a.es * 100, 2) + ' %'],
        meters: [['PERIOD', eng(a.T, 's')], ['SLOPE ERR', fmt(a.es * 100, 2) + ' %']], row: { R: q.R, T: a.T, es: a.es } }; },
      cols: [{ label: 'R (kΩ)', get: function (r) { return fmt(r.R / 1000, 1); } }, { label: 'T (µs)', get: function (r) { return fmt(r.T * 1e6, 2); } }, { label: 'e_s (%)', get: function (r) { return fmt(r.es * 100, 2); } }, { label: 'C (nF)', get: function (r) { return fmt(cOf(r) * 1e9, 2); } }],
      need: 4,
      runs: [4700, 10000, 22000, 47000, 100000].map(function (r) { return { R: r }; }),
      graph: { x: function (r) { return r.R / 1000; }, y: function (r) { return r.T * 1000; }, xlabel: 'R (kΩ)', ylabel: 'Sweep period (ms)', line: originFit },
      result: function (rows) { var c = mean(rows.map(cOf));
        return { label: 'Timing capacitor C', value: c * 1e9, unit: 'nF', digits: 2, truth: p.C * 1e9, note: 'From each period with the circuit\'s own formula' + (K_ === 1 ? ' (the current source\'s 1 MΩ output resistance included: at small currents the sweep is no longer linear)' : '') + ', averaged over ' + rows.length + '. Slope error ' + fmt(rows[0].es * 100, 2) + ' % (' + NAMES[K_] + ').' }; },
      resultNote: 'Every sweep is a capacitor charging towards an asymptote and reset before it gets far: the period scales with RC, and the linearity depends only on how small a fraction of the asymptote the sweep uses. The constant-current and bootstrap circuits raise the asymptote so far that the sweep is nearly a straight line.',
      chips: ['What is slope error?', 'Why is the bootstrap sweep so linear?', 'What sets a UJT\'s firing voltage?', 'Check my readings'],
      viva: [['A sweep\'s slope error is reduced by', ['raising the voltage it charges towards', 'a bigger C', 'a smaller R'], 0, 'e_s = (V_hi − V_lo)/(V_∞ − V_lo).']] };
  };

  // ---------------------------------------------------------------- tuned amplifiers
  PLANS['pe9-tuned-amp'] = function () {
    var dbl = K_ === 1, f0n = 1 / (2 * Math.PI * Math.sqrt(p.L * p.C)), FS = [], k, runs = [];
    for (k = -40; k <= 40; k++) FS.push(Math.round(f0n * (1 + k * 0.0025) / 10) * 10);
    for (k = (dbl ? -16 : -12); k <= (dbl ? 16 : 12); k++) runs.push({ f: Math.round(f0n * (1 + k * 0.0025) / 10) * 10 });
    function G(q) { return memo('tu', q, function (qq) { return KN.gain(qq, qq.f); }); }
    function an(rows) { var mx = Math.max.apply(null, rows.map(function (r) { return r.g; })), c = linCross(rows.map(function (r) { return [r.f, r.g]; }), mx / Math.SQRT2);
      return c.length >= 2 ? { f1: c[0], f2: c[c.length - 1], f0: Math.sqrt(c[0] * c[c.length - 1]), mx: mx } : null; }
    return {
      compName: (dbl ? 'Double-tuned' : 'Single-tuned') + ' RF amplifier: ' + (p.L * 1e6) + ' µH and ' + cLabel(p.C) + ' tank' + (dbl ? 's, critically coupled' : ''), wiring: 'RF generator (10 mV) → base of the BF-type transistor; collector load the tuned tank' + (dbl ? ', coupled to an identical secondary tank feeding the output' : '') + '. Channel 1 on the input, channel 2 on the output.',
      formula: dbl ? 'G = A₀ 2kQ / √((1 + k²Q² − x²)² + 4x²),  x = Q(f/f₀ − f₀/f);  critical (kQ = 1): bandwidth = √2 f₀/Q' : 'G = A₀ / √(1 + x²),  x = Q(f/f₀ − f₀/f);  f₀ = 1/(2π√(LC)),  bandwidth = f₀/Q',
      controls: [{ param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: function (v) { return fmt(v / 1000, 2) + ' kHz'; }, vals: FS }],
      art: function () { to92(-0.03, -0.02, 'BF194'); coil(0.03, -0.03, (p.L * 1e6) + ' µH'); capacitor(0.03, 0.02, p.C, 'C', 'ceramic'); if (dbl) { coil(0.08, -0.03, (p.L * 1e6) + ' µH'); capacitor(0.08, 0.02, p.C, 'C', 'ceramic'); }
        battery(-0.1, 0.03, '12 V'); jumper([-0.045, -0.02], [-0.12, 0.03], 'yellow'); return function () {}; },
      trace: function (q) { var g = G(q), t = sineTrace(q.f, [0.01, 0.01 * g], [0, 0], 4); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'IN' }, { y: t.ys[1], color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var g = G(q); return { lines: [fmt(q.f / 1000, 2) + ' kHz: gain ' + fmt(g, 3) + ' (' + fmt(20 * ln10(g), 2) + ' dB)'], meters: [['FREQ', fmt(q.f / 1000, 2) + ' kHz'], ['GAIN', fmt(g, 3)]], row: { f: q.f, g: g } }; },
      cols: [{ label: 'f (kHz)', get: function (r) { return fmt(r.f / 1000, 2); } }, { label: 'Gain', get: function (r) { return fmt(r.g, 3); } }, { label: 'dB', get: function (r) { return fmt(20 * ln10(r.g), 2); } }],
      need: 15,
      runs: runs,
      okFn: function (rows) { return !!an(rows); },
      graph: { x: function (r) { return r.f / 1000; }, y: function (r) { return r.g; }, xlabel: 'f (kHz)', ylabel: 'Gain' },
      result: function (rows) { var a = an(rows); if (!a) return null; var bw = a.f2 - a.f1;
        return { label: 'Q of the tank' + (dbl ? 's' : ''), value: (dbl ? Math.SQRT2 : 1) * a.f0 / bw, unit: '', digits: 2, truth: p.Q,
          note: 'Half-power frequencies ' + fmt(a.f1 / 1000, 3) + ' and ' + fmt(a.f2 / 1000, 3) + ' kHz: centre f₀ = ' + fmt(a.f0 / 1000, 3) + ' kHz (textbook ' + fmt(HK.TEXTBOOK.pe9_tuned_f0(p) / 1000, 3) + ' kHz), bandwidth ' + fmt(bw / 1000, 3) + ' kHz; Q = ' + (dbl ? '√2 ' : '') + 'f₀/bandwidth.' }; },
      resultNote: dbl ? 'Two coupled tanks at critical coupling give a flat top and a bandwidth √2 times that of one tank of the same Q, with steeper skirts: the pass band an IF amplifier wants.'
        : 'The tank\'s impedance, and so the gain, peaks at f₀ and falls away on either side; the higher the Q, the narrower the band. The half-power frequencies sit symmetrically about f₀ on a log scale.',
      chips: ['Why does gain peak at f₀?', 'What does coupling do?', 'Why use double-tuned stages?', 'Check my readings'],
      viva: [['A single-tuned stage with Q = 40 at 500 kHz has a bandwidth of', ['12.5 kHz', '40 kHz', '500 Hz'], 0, 'f₀/Q.']] };
  };

  // ---------------------------------------------------------------- counters
  PLANS['pe9-counters'] = function () {
    var syn = K_ === 1;
    function rn(q) { return memo('cn', q, function (qq) { var r = KN.run(qq); r.nb = KN.bits(qq); return r; }); }
    return {
      compName: (syn ? 'Synchronous' : 'Asynchronous (ripple)') + ' mod-N counter of JK flip-flops, decoded clear', wiring: 'Clock ' + fmt(p.fclk / 1000, 0) + ' kHz → ' + (syn ? 'every flip-flop\'s clock; the next-state logic sets J and K' : 'the first flip-flop; each Q drives the next one\'s clock (J = K = 1)') + '; a NAND decode resets the count at N. The universal counter reads the MSB\'s frequency; channel 1 on the clock, channel 2 on the MSB.',
      formula: 'modulus = f_clk / f_MSB;   ' + (syn ? 'delay of every output = t_pd' : 'MSB delay = n t_pd (the change ripples through n stages)'),
      controls: [{ param: 'N', label: 'Modulus wired', short: 'MOD N', unit: '', digits: 0, vals: [6, 8, 10, 12, 16] }],
      art: function () { dip8(-0.05, -0.02, '74LS76'); dip8(0.0, -0.02, '74LS76'); dip8(0.05, -0.02, '74LS00'); var bar = ledBar(0.0, 0.03, 4, '#ff4030'); battery(0.11, 0.035, '5 V'); return function (q) { bar.set(Math.round(q.N) - 1); }; },
      trace: function (q) { var r = rn(q), n = Math.round(q.N), msb = 1 << (r.nb - 1), N2 = 3 * n, per = 1 / p.fclk, dt = N2 * per / NS, a = [], b = [], i, t, cy, c;
        for (i = 0; i < NS; i++) { t = i * dt; cy = Math.floor(t / per); a.push((t - cy * per) < per / 2 ? 5 : 0); c = r.seq[(cy + n - 1) % n]; b.push((c & msb) ? 5 : 0); }
        return { dt: dt, ch: [{ y: a, color: YEL, name: 'CLK' }, { y: b, color: CYA, name: 'MSB' }] }; },
      meas: function (q) { var r = rn(q), fo = p.fclk / r.mod; return { lines: ['MSB frequency ' + fmt(fo, 2) + ' Hz: modulus ' + fmt(p.fclk / fo, 3), 'MSB changes ' + fmt(r.delay * 1e9, 1) + ' ns after the clock edge (' + r.nb + ' flip-flops)'],
        meters: [['f_MSB', fmt(fo, 2) + ' Hz'], ['DELAY', fmt(r.delay * 1e9, 1) + ' ns']], row: { N: Math.round(q.N), fo: fo, mod: p.fclk / fo, delay: r.delay, nb: r.nb } }; },
      cols: [{ label: 'N wired', get: function (r) { return r.N; } }, { label: 'f_MSB (Hz)', get: function (r) { return fmt(r.fo, 2); } }, { label: 'Modulus', get: function (r) { return fmt(r.mod, 3); } }, { label: 'Stages', get: function (r) { return r.nb; } }, { label: 'Delay (ns)', get: function (r) { return fmt(r.delay * 1e9, 1); } }],
      need: 4,
      runs: [6, 8, 10, 12, 16].map(function (n) { return { N: n }; }),
      graph: { x: function (r) { return r.nb; }, y: function (r) { return r.delay * 1e9; }, xlabel: 'Number of flip-flops', ylabel: 'MSB delay (ns)', line: syn ? lineFit : originFit },
      result: function (rows) { var t = mean(rows.map(function (r) { return syn ? r.delay : r.delay / r.nb; }));
        return { label: 'Flip-flop propagation delay t_pd', value: t * 1e9, unit: 'ns', digits: 2, truth: p.tpd * 1e9, note: 'Every measured modulus equals N (' + rows.map(function (r) { return fmt(r.mod, 0); }).join(', ') + '). ' + (syn ? 'The delay does not grow with the number of stages: t_pd itself.' : 'The MSB delay grows by one t_pd per stage: t_pd = delay / stages.') }; },
      resultNote: syn ? 'All flip-flops share the clock, so every output changes one propagation delay after the edge however long the counter: synchronous counters can run fast.'
        : 'Each stage waits for the one before it to change, so the delays add: an n-stage ripple counter is n t_pd late at its MSB, which limits how fast it can be clocked and causes decoding glitches.',
      chips: ['Why does the delay grow with stages?', 'How is a mod-10 counter made?', 'What is a decoding glitch?', 'Check my readings'],
      viva: [['A 4-stage ripple counter with t_pd = 25 ns has an MSB delay of', ['100 ns', '25 ns', '400 ns'], 0, 'n t_pd.']] };
  };

  // ---------------------------------------------------------------- AM / FM
  PLANS['pe9-am-fm'] = function () {
    var fm = K_ === 1, J0Z = 2.404826;
    function an(q) { return memo('af', q, function (qq) { var s = KN.signal(qq), m = KN.measure(qq); return { y: s[0], dt: s[1], m: m }; }); }
    return {
      compName: (fm ? 'FM' : 'AM') + ' modulator: ' + fmt(p.fc / 1000, 0) + ' kHz carrier of ' + p.Vc + ' V, ' + fmt(p.fm, 0) + ' Hz message', wiring: 'Carrier generator and message generator → ' + (fm ? 'the VCO-type FM modulator' : 'the transistor AM modulator') + '; channel 1 on the modulated wave; the scope\'s FFT reads the carrier and side-band lines. A ' + (fm ? 'discriminator' : 'diode envelope detector') + ' recovers the message.',
      formula: fm ? 'β = k_f V_m / f_m;  lines V_c J_n(β) at f_c + n f_m;  carrier null J₀(β) = 0 at β = 2.4048  ⇒  k_f = 2.4048 f_m / V_m(null)' : 'm = k_a V_m = (V_max − V_min)/(V_max + V_min);  side-bands m V_c/2 at f_c ± f_m;  detector output m V_c',
      controls: [{ param: 'Vm', label: 'Message amplitude', short: 'V_m', unit: 'V', digits: 2, vals: fm ? rng(0.2, 1.2, 0.02) : [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0] }],
      art: function () { to92(-0.04, -0.02, fm ? 'MC1648' : 'BF194'); coil(0.02, -0.03, 'TANK'); diode(0.07, -0.02, 'OA79'); capacitor(0.07, 0.02, 1e-8, 'C', 'ceramic'); battery(-0.1, 0.03, '12 V'); return function () {}; },
      trace: function (q) { var a = an(q); return { dt: a.dt, ch: [{ y: a.y, color: YEL, name: fm ? 'FM' : 'AM' }] }; },
      meas: function (q) { var a = an(q), m = a.m;
        if (fm) return { lines: ['V_m = ' + fmt(q.Vm, 2) + ' V: carrier line ' + fmt(m.car, 4) + ' V (signed), first side-bands ' + fmt(Math.abs(m.s1), 4) + ' V', 'Discriminator output ' + fmt(m.demod, 3) + ' V'],
          meters: [['CARRIER', fmt(m.car, 4) + ' V'], ['1st SB', fmt(Math.abs(m.s1), 4) + ' V']], row: { Vm: q.Vm, car: m.car, s1: m.s1 } };
        var hi = p.Vc * (1 + m.m), lo = p.Vc * (1 - m.m);
        return { lines: ['V_m = ' + fmt(q.Vm, 2) + ' V: envelope V_max ' + fmt(hi, 3) + ' V, V_min ' + fmt(lo, 3) + ' V → m = ' + fmt(m.m, 4), 'Side-bands ' + fmt(m.usb, 4) + ' / ' + fmt(m.lsb, 4) + ' V; detector output ' + fmt(m.demod, 3) + ' V'],
          meters: [['m', fmt(m.m, 4)], ['SIDE-BAND', fmt(m.usb, 4) + ' V']], row: { Vm: q.Vm, m: m.m, sb: m.usb } }; },
      cols: fm ? [{ label: 'V_m (V)', get: function (r) { return fmt(r.Vm, 2); } }, { label: 'Carrier (V)', get: function (r) { return fmt(r.car, 4); } }, { label: '1st side-band (V)', get: function (r) { return fmt(Math.abs(r.s1), 4); } }]
        : [{ label: 'V_m (V)', get: function (r) { return fmt(r.Vm, 2); } }, { label: 'm', get: function (r) { return fmt(r.m, 4); } }, { label: 'Side-band (V)', get: function (r) { return fmt(r.sb, 4); } }, { label: '2 SB/V_c', get: function (r) { return fmt(2 * r.sb / p.Vc, 4); } }],
      need: fm ? 8 : 5,
      runs: (fm ? [0.2, 0.4, 0.6, 0.7, 0.76, 0.78, 0.8, 0.82, 0.84, 0.9, 1.0] : [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]).map(function (v) { return { Vm: v }; }),
      okFn: fm ? function (rows) { return linCross(rows.map(function (r) { return [r.Vm, r.car]; }), 0).length >= 1; } : null,
      graph: fm ? { x: function (r) { return r.Vm; }, y: function (r) { return r.car; }, xlabel: 'V_m (V)', ylabel: 'Carrier line (V)' } : { x: function (r) { return r.Vm; }, y: function (r) { return r.m; }, xlabel: 'V_m (V)', ylabel: 'Modulation index m', line: originFit },
      result: function (rows) {
        if (fm) { var z = linCross(rows.map(function (r) { return [r.Vm, r.car]; }), 0)[0];
          return { label: 'Frequency deviation constant k_f', value: J0Z * p.fm / z, unit: 'Hz/V', digits: 1, truth: p.kf, note: 'The carrier line changes sign (passes through zero) at V_m = ' + fmt(z, 4) + ' V, where β = 2.4048: k_f = 2.4048 f_m / V_m. The deviation there is ' + fmt(J0Z * p.fm, 0) + ' Hz; Carson\'s bandwidth 2(Δf + f_m) = ' + fmt(2 * (J0Z * p.fm + p.fm), 0) + ' Hz.' }; }
        var m = origin(rows.map(function (r) { return [r.Vm, r.m]; }));
        return { label: 'Modulator sensitivity k_a', value: m, unit: '1/V', digits: 4, truth: p.ka, note: 'Slope of m against V_m through the origin, ' + rows.length + ' readings; each side-band is m V_c/2, as the FFT shows.' }; },
      resultNote: fm ? 'As the deviation grows, power moves from the carrier into more and more side-bands; at β = 2.405 the carrier line vanishes altogether, a precise marker for calibrating a modulator.'
        : 'The envelope swings by m V_c above and below the carrier; the same m sets the two side-bands at m V_c/2 each, and the detector recovers m V_c. m grows in proportion to the message until over-modulation at m = 1.',
      chips: ['Where does the AM power go?', 'Why does the FM carrier vanish?', 'What is Carson\'s rule?', 'Check my readings'],
      viva: [['An AM wave with m = 1 has total side-band power equal to', ['half the carrier power', 'the carrier power', 'zero'], 0, 'm²/2 of the carrier.']] };
  };

  // ---------------------------------------------------------------- analog computer
  PLANS['pe9-analog-comp'] = function () {
    var NAMES = ['falling body', 'simultaneous equations', 'second-order equation'];
    function an(q) { return memo('ac', q, function (qq) { var r = KN.run(qq), a = KN.analyse(qq); return { a: r[0], b: r[1], dt: r[2], m: a }; }); }
    function rcOf(r) { return K_ === 0 ? r.v / Math.sqrt(2 * p.V0 / p.Vg) : Math.sqrt(1 - p.z * p.z) / (2 * Math.PI * r.v); }
    return {
      compName: 'Analog computer patch board: ' + NAMES[K_], wiring: K_ === 0 ? 'V_g = ' + p.Vg + ' V → integrator 1 (velocity) → integrator 2 (height, starting at V₀ = ' + p.V0 + ' V). Channel 1 the velocity, channel 2 the height.' : K_ === 1 ? 'Two integrators and summers patched for 2x + y = 5, x + 3y = 10; channel 1 on x, channel 2 on y.' : 'Two integrators and a summer patched for x″ + 2ζω x′ + ω² x = 0 (ζ = ' + p.z + ', ω = 1/RC), started at x = ' + p.V0 + ' V. Channel 1 on x.',
      formula: K_ === 0 ? 'v = V_g t/RC,  y = V₀ − V_g t²/(2(RC)²),  landing at T₀ = RC√(2V₀/V_g)' : K_ === 1 ? 'RC dx/dt = c₁ − a₁x − b₁y,  RC dy/dt = c₂ − a₂x − b₂y  → settles at the solution' : 'f_d = √(1 − ζ²)/(2π RC)',
      controls: [{ param: 'C', label: 'Integrator capacitors', short: 'C', unit: 'F', digits: 0, fmtv: cLabel, vals: [2.2e-8, 4.7e-8, 1e-7, 2.2e-7, 4.7e-7] }],
      art: function () { dip8(-0.04, -0.02, 'TL074'); dip8(0.02, -0.02, 'TL074'); capacitor(-0.04, 0.02, 1e-7, 'C1', 'ceramic'); capacitor(0.02, 0.02, 1e-7, 'C2', 'ceramic'); resistor(0.07, -0.03, p.R, 'R', false); battery(0.11, 0.035, '±12 V'); return function () {}; },
      trace: function (q) { var a = an(q); return { dt: a.dt, ch: K_ === 2 ? [{ y: a.a, color: YEL, name: 'x' }] : [{ y: a.a, color: YEL, name: K_ === 0 ? 'v' : 'x' }, { y: a.b, color: CYA, name: K_ === 0 ? 'y' : 'y' }] }; },
      meas: function (q) { var a = an(q), m = a.m;
        if (K_ === 0) return { lines: ['Height reaches 0 at T₀ = ' + fmt(m.T0 * 1000, 3) + ' ms; velocity then ' + fmt(m.vland, 3) + ' V'], meters: [['T₀', fmt(m.T0 * 1000, 3) + ' ms'], ['v(T₀)', fmt(m.vland, 3) + ' V']], row: { C: q.C, v: m.T0, w: m.vland } };
        if (K_ === 1) return { lines: ['Settled: x = ' + fmt(m.x, 4) + ' V, y = ' + fmt(m.y, 4) + ' V'], meters: [['x', fmt(m.x, 4) + ' V'], ['y', fmt(m.y, 4) + ' V']], row: { C: q.C, v: m.x, w: m.y } };
        return { lines: ['Damped oscillation: period ' + fmt(1000 / m.fd, 3) + ' ms, f_d = ' + fmt(m.fd, 3) + ' Hz'], meters: [['PERIOD', fmt(1000 / m.fd, 3) + ' ms'], ['f_d', fmt(m.fd, 3) + ' Hz']], row: { C: q.C, v: m.fd, w: 0 } }; },
      cols: [{ label: 'C', get: function (r) { return cLabel(r.C); } }, { label: K_ === 0 ? 'T₀ (ms)' : K_ === 1 ? 'x (V)' : 'f_d (Hz)', get: function (r) { return K_ === 0 ? fmt(r.v * 1000, 3) : fmt(r.v, 4); } },
        { label: K_ === 0 ? 'v(T₀) (V)' : K_ === 1 ? 'y (V)' : 'RC (ms)', get: function (r) { return K_ === 2 ? fmt(rcOf(r) * 1000, 3) : fmt(r.w, 4); } }, { label: K_ === 1 ? '—' : 'R (kΩ)', get: function (r) { return K_ === 1 ? '—' : fmt(rcOf(r) / r.C / 1000, 2); } }],
      need: 3,
      runs: [2.2e-8, 4.7e-8, 1e-7, 2.2e-7, 4.7e-7].map(function (c) { return { C: c }; }),
      graph: { x: function (r) { return r.C * 1e6; }, y: function (r) { return K_ === 1 ? r.v : rcOf(r) * 1000; }, xlabel: 'C (µF)', ylabel: K_ === 1 ? 'x (V)' : 'RC (ms)', line: K_ === 1 ? lineFit : originFit },
      result: function (rows) {
        if (K_ === 1) return { label: 'Solution x', value: mean(rows.map(function (r) { return r.v; })), unit: 'V', digits: 4, truth: HK.TEXTBOOK.pe9_acomp_main(p), note: 'Settled values x = ' + fmt(rows[0].v, 4) + ', y = ' + fmt(rows[0].w, 4) + ' (exact 1 and 3), the same for every C: the capacitors set only how fast it settles.' };
        var rs = rows.map(function (r) { return rcOf(r) / r.C; });
        return { label: 'Integrator resistor R', value: mean(rs) / 1000, unit: 'kΩ', digits: 2, truth: p.R / 1000, note: (K_ === 0 ? 'RC = T₀/√(2V₀/V_g)' : 'RC = √(1 − ζ²)/(2π f_d)') + ' from each run, then R = RC/C, averaged over ' + rs.length + '.' }; },
      resultNote: K_ === 0 ? 'The first integrator turns the constant "g" into a velocity growing linearly with time, the second turns that into a height falling as t²: the scope draws the straight line and the parabola. RC sets the machine\'s time scale.'
        : K_ === 1 ? 'Each integrator keeps changing its variable until its equation\'s error is zero, so the circuit settles where both equations hold: the solution.' : 'A loop of two integrators with damping feedback rings at its damped natural frequency, set by RC and ζ.',
      chips: ['How does an integrator compute?', 'What is the time scale?', 'Why does the circuit settle at the solution?', 'Check my readings'],
      viva: [['In the falling-body circuit the height trace is', ['a parabola', 'a straight line', 'an exponential'], 0, 'y = V₀ − V_g t²/(2(RC)²).']] };
  };

  // ---------------------------------------------------------------- power amplifiers
  PLANS['pe9-power-amp'] = function () {
    var cb = K_ === 1, VALS = cb ? [2, 4, 6, 8, 10, 11, 12, 13, 14] : [1, 2, 3, 4, 5, 5.5, 6, 7, 8];
    function an(q) { return memo('pa', q, function (qq) { var w = KN.wave(qq), a = KN.analyse(qq); a.vo = w[0]; return a; }); }
    function okRow(r) { return cb ? r.Vo <= p.Vcc * 0.999 && r.Vd - p.Vg < p.Vcc : r.thd < 0.005; }
    function xOf(r) { return cb ? r.Vo / p.Vcc : (r.Vo / p.Vcc) * (r.Vo / p.Vcc); }
    return {
      compName: cb ? 'Class B complementary push-pull pair on ±' + p.Vcc + ' V into ' + p.RL + ' Ω' : 'Series-fed class A stage on ' + p.Vcc + ' V with an ' + p.RL + ' Ω collector load, biased at V_cc/(2R_L)', wiring: 'Generator → driver → output stage → ' + p.RL + ' Ω load. Multimeter 1 in the supply lead (average current), multimeter 2 reads the distortion factor; channel 1 the drive, channel 2 the load voltage.',
      formula: cb ? 'P_o = V_o²/(2R_L),  P_dc = 2V_cc V_o/(π R_L),  η = π V_o/(4V_cc) ≤ 78.5 %' : 'P_o = V_o²/(2R_L),  P_dc = V_cc²/(2R_L),  η = (V_o/V_cc)² ≤ 25 %',
      controls: [{ param: 'Vd', label: 'Drive amplitude', short: 'DRIVE', unit: 'V', digits: 1, vals: VALS }],
      art: function () { to92(-0.04, -0.02, cb ? 'SL100' : '2N3055'); if (cb) to92(0.0, -0.02, 'SK100'); resistor(0.05, -0.02, p.RL, 'RL'); battery(0.1, 0.03, cb ? '±' + p.Vcc + ' V' : p.Vcc + ' V'); jumper([-0.055, -0.02], [-0.12, 0.03], 'yellow'); return function () {}; },
      trace: function (q) { var a = an(q), n = a.vo.length, d = [], i; for (i = 0; i < n; i++) d.push(q.Vd * Math.sin(2 * Math.PI * i / n));
        return { dt: 1e-3 / n, ch: [{ y: d, color: YEL, name: 'DRIVE' }, { y: a.vo, color: CYA, name: 'LOAD' }] }; },
      meas: function (q) { var a = an(q); return { lines: ['Drive ' + fmt(q.Vd, 1) + ' V: output ' + fmt(a.Vo, 3) + ' V peak, P_o = ' + fmt(a.Po, 3) + ' W, P_dc = ' + fmt(a.Pdc, 3) + ' W, η = ' + fmt(a.eta * 100, 2) + ' %', 'Total harmonic distortion ' + fmt(a.thd * 100, 2) + ' %'],
        meters: [['SUPPLY  DC', fmt(a.Pdc / p.Vcc, 4) + ' A'], ['THD', fmt(a.thd * 100, 2) + ' %']], row: { Vd: q.Vd, Vo: a.Vo, Po: a.Po, Pdc: a.Pdc, eta: a.eta, thd: a.thd } }; },
      cols: [{ label: 'Drive (V)', get: function (r) { return fmt(r.Vd, 1); } }, { label: 'V_o (V)', get: function (r) { return fmt(r.Vo, 3); } }, { label: 'P_o (W)', get: function (r) { return fmt(r.Po, 3); } }, { label: 'P_dc (W)', get: function (r) { return fmt(r.Pdc, 3); } }, { label: 'η (%)', get: function (r) { return fmt(r.eta * 100, 2); } }, { label: 'THD (%)', get: function (r) { return fmt(r.thd * 100, 2); } }],
      need: 6,
      runs: VALS.map(function (v) { return { Vd: v }; }),
      okFn: function (rows) { return rows.filter(okRow).length >= 3; },
      graph: { x: function (r) { return okRow(r) ? xOf(r) : NaN; }, y: function (r) { return r.eta * 100; }, xlabel: cb ? 'V_o/V_cc' : '(V_o/V_cc)²', ylabel: 'η (%)', line: originFit },
      result: function (rows) { var ok = rows.filter(okRow), m = origin(ok.map(function (r) { return [xOf(r), r.eta * 100]; })), mx = rows.reduce(function (a, r) { return r.eta > a.eta ? r : a; }, rows[0]);
        return { label: 'Largest efficiency (at the full undistorted swing)', value: cb ? m : m * 0.25, unit: '%', digits: 2, truth: cb ? Math.PI / 4 * 100 : 25,
          note: 'Straight line through the origin fitted to the ' + ok.length + ' unclipped readings, extrapolated to V_o = ' + (cb ? 'V_cc' : 'V_cc/2') + '. Largest measured: η = ' + fmt(mx.eta * 100, 2) + ' % at drive ' + fmt(mx.Vd, 1) + ' V (THD ' + fmt(mx.thd * 100, 2) + ' %).' + (cb ? ' At small drive the crossover dead zone of ' + p.Vg + ' V raises the distortion.' : ' Beyond V_cc/2 the wave clips and the distortion rises.') }; },
      resultNote: cb ? 'Each transistor conducts only while its half of the wave needs it, so the supply current follows the signal and the efficiency rises in proportion to the swing, up to π/4. The price is crossover distortion where neither transistor conducts.'
        : 'The class A stage draws the same supply current whatever the signal, so most of the power heats the transistor and the load\'s resistance; the efficiency grows as the square of the swing, to 25 % at most.',
      chips: ['Why is class A so inefficient?', 'Where does crossover distortion come from?', 'How is class AB better?', 'Check my readings'],
      viva: [['The largest efficiency of an ideal class B stage is', ['78.5 %', '50 %', '25 %'], 0, 'π/4.']] };
  };

  // ---------------------------------------------------------------- op-amp parameters
  PLANS['pe9-opamp-params'] = function () {
    var TN = ['offset: gain 1001, inputs earthed', 'bias: follower, 1 MΩ shorted', 'bias: follower, 1 MΩ in the + input', 'CMRR: gain 100, ΔV_cm = 10 V', 'slew rate: follower, 10 V step', 'gain 100 against frequency'];
    var chip = SAMPLE ? SAMPLE.split(' ')[0] : '741';
    function rd(q) { return memo('op', q, function (qq) { return KN.readings(qq); }); }
    function val(q) { var r = rd(q), t = Math.round(q.test); return t === 0 ? r.vo_off : t === 1 ? r.vo_b0 : t === 2 ? r.vo_b1 : t === 3 ? r.dvo_cm : t === 4 ? r.rise : r.g_f; }
    function f3Of(r, rows) { var g = rows.filter(function (x) { return x.test === 5; }).sort(function (a, b) { return a.f - b.f; }), lo = g[0]; if (r.test !== 5 || !lo || lo.f > 1000 || r.v > 0.9 * lo.v || r.v < 0.15 * lo.v) return NaN; var k = lo.v / r.v; return r.f / Math.sqrt(k * k - 1); }
    function one(rows, t) { var x = rows.filter(function (r) { return r.test === t; })[0]; return x ? x.v : NaN; }
    return {
      compName: chip + ' op-amp in its standard test circuits', wiring: 'One test circuit at a time on the board, chosen with the TEST dial; ±15 V. Multimeter 1 reads the output, the scope the edges and the frequency response.',
      formula: 'V_os = V_o/1001;  I_b = ΔV_o/1 MΩ;  CMRR = 20 log(100 ΔV_cm/ΔV_o);  SR = 8 V / t(10→90 %);  GBW = f_3dB × 101',
      controls: [{ param: 'test', label: 'Test circuit', short: 'TEST', unit: '', digits: 0, names: TN, vals: [0, 1, 2, 3, 4, 5] }, { param: 'f', label: 'Generator frequency (gain test)', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: [10, 100, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000] }],
      art: function () { dip8(0.0, -0.02, chip); resistor(-0.06, -0.02, 100, 'R1'); resistor(0.0, -0.06, 100000, 'Rf'); resistor(0.06, -0.02, 1000000, 'Rb'); battery(0.1, 0.03, '±15 V'); return function () {}; },
      trace: function (q) { var r = rd(q), t = Math.round(q.test), n = NS, i, a = [], b = [], dt;
        if (t === 4) { dt = 4 * r.rise / n; for (i = 0; i < n; i++) { var tt = i * dt, inp = tt < 0.5 * r.rise ? -5 : 5; a.push(inp); b.push(tt < 0.5 * r.rise ? -5 : Math.min(5, -5 + p.SR * (tt - 0.5 * r.rise))); } return { dt: dt, ch: [{ y: a, color: YEL, name: 'IN' }, { y: b, color: CYA, name: 'OUT' }] }; }
        var s = sineTrace(t === 5 ? q.f : 1000, [0.05, t === 5 ? 0.05 * r.g_f : val(q)], [0, Math.PI], 3); return { dt: s.dt, ch: [{ y: s.ys[0], color: YEL, name: 'IN' }, { y: s.ys[1], color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var t = Math.round(q.test), v = val(q), txt = t === 4 ? 'Output rises 10 → 90 % (8 V) in ' + fmt(v * 1e6, 3) + ' µs' : t === 5 ? fLabel(q.f) + ': gain ' + fmt(v, 3) : t === 3 ? 'Output changes by ' + fmt(v * 1000, 4) + ' mV for ΔV_cm = 10 V' : 'V_o = ' + fmt(v * 1000, 4) + ' mV';
        return { lines: [TN[t] + ': ' + txt], meters: [['TEST', String(t + 1)], ['READING', t === 4 ? fmt(v * 1e6, 3) + ' µs' : t === 5 ? fmt(v, 3) : fmt(v * 1000, 4) + ' mV']], row: { test: t, f: t === 5 ? q.f : 0, v: v } }; },
      cols: [{ label: 'Test', get: function (r) { return r.test + 1; } }, { label: 'Setting', get: function (r) { return r.test === 5 ? fLabel(r.f) : '—'; } }, { label: 'Reading', get: function (r) { return r.test === 4 ? fmt(r.v * 1e6, 3) + ' µs' : r.test === 5 ? fmt(r.v, 3) : fmt(r.v * 1000, 4) + ' mV'; } },
        { label: 'Result', get: function (r, i, rows) { if (r.test === 0) return 'V_os ' + fmt(r.v / 1001 * 1e6, 1) + ' µV'; if (r.test === 2) return 'I_b ' + eng((one(rows, 1) - r.v) / 1e6, 'A'); if (r.test === 3) return 'CMRR ' + fmt(20 * ln10(1000 / r.v), 1) + ' dB'; if (r.test === 4) return 'SR ' + fmt(8 / r.v / 1e6, 3) + ' V/µs'; var f3 = f3Of(r, rows); return isFinite(f3) ? 'f_3 ' + fmt(f3 / 1000, 2) + ' kHz' : '—'; } }],
      need: 9,
      runs: [{ test: 0 }, { test: 1 }, { test: 2 }, { test: 3 }, { test: 4 }, { test: 5, f: 10 }, { f: 1000 }, { f: 5000 }, { f: 10000 }, { f: 20000 }, { f: 50000 }, { f: 100000 }, { f: 200000 }],
      okFn: function (rows) { var have = [0, 1, 2, 3, 4].every(function (t) { return rows.some(function (r) { return r.test === t; }); }); return have && rows.filter(function (r) { return isFinite(f3Of(r, rows)); }).length >= 2; },
      graph: { x: function (r) { return r.test === 5 ? ln10(r.f) : NaN; }, y: function (r) { return r.test === 5 ? 20 * ln10(r.v) : NaN; }, xlabel: 'log10 (f / Hz)', ylabel: 'Gain (dB), gain-100 test' },
      result: function (rows) { var gb = rows.map(function (r) { var f3 = f3Of(r, rows); return isFinite(f3) ? f3 * 101 : NaN; }).filter(isFinite);
        return { label: 'Gain-bandwidth product', value: mean(gb) / 1e6, unit: 'MHz', digits: 3, truth: p.A0 * p.fa / 1e6,
          note: 'From ' + gb.length + ' readings of the gain-100 test. The other tests give V_os = ' + fmt(one(rows, 0) / 1001 * 1e6, 1) + ' µV, I_b = ' + eng((one(rows, 1) - one(rows, 2)) / 1e6, 'A') + ', CMRR = ' + fmt(20 * ln10(1000 / one(rows, 3)), 1) + ' dB, slew rate = ' + fmt(8 / one(rows, 4) / 1e6, 3) + ' V/µs.' }; },
      resultNote: 'Each parameter needs its own circuit: a high gain to make a tiny offset readable, a large resistor to turn a tiny bias current into a voltage, a large common-mode swing for the CMRR, a large step for the slew rate and a sweep for the bandwidth.',
      chips: ['Why use a gain of 1001 for the offset?', 'How does 1 MΩ reveal the bias current?', 'What limits the slew rate?', 'Check my readings'],
      viva: [['The offset test uses a large gain so that', ['the tiny offset becomes a readable output', 'the op-amp saturates', 'the bias current cancels'], 0, 'V_o = 1001 V_os.']] };
  };

  // ---------------------------------------------------------------- crystal oscillator
  PLANS['pe9-crystal-osc'] = function () {
    var CLS = [1e-11, 1.5e-11, 2e-11, 2.7e-11, 3.3e-11, 4.7e-11];
    function fq(q) { return memo('xt', q, function (qq) { return Math.round(KN.freq(qq, qq.CL, qq.T)); }); }
    function cl(rows) { return rows.filter(function (r) { return Math.abs(r.T - p.Ti) < 1e-9; }); }
    return {
      compName: '10 MHz AT-cut quartz crystal in a Pierce oscillator, holder capacitance C0 = ' + fmt(p.C0 * 1e12, 1) + ' pF (bridge)', wiring: 'Crystal between the inverter\'s input and output with the load trimmer C_L; the crystal sits in a small oven. The universal counter (10 MHz reference, 1 Hz resolution) reads the frequency; channel 1 on the output.',
      formula: 'f_L = f_s (1 + C1/(2(C0 + C_L)));  f against 1/(C0 + C_L) is a line of slope f_s C1/2;  AT-cut: Δf/f = a₃(T − T_i)³ + a₁(T − T_i)',
      controls: [{ param: 'CL', label: 'Load capacitance', short: 'C_L', unit: 'F', digits: 0, fmtv: function (v) { return fmt(v * 1e12, 0) + ' pF'; }, vals: CLS }, { param: 'T', label: 'Oven temperature', short: 'OVEN', unit: '°C', digits: 0, vals: [-20, 0, 10, 25, 40, 50, 70] }],
      art: function () { boxPart(0.02, 0.012, 0.012, BBX - 0.02, BBZ - 0.02, 0x9aa3ad, 'XTAL'); dip8(0.04, -0.02, '74HC04'); capacitor(-0.06, -0.02, 2e-11, 'CL', 'ceramic'); battery(0.1, 0.03, '5 V'); return function () {}; },
      trace: function (q) { var f = fq(q), t = sineTrace(f, [2.5], [0], 4); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'OUT' }] }; },
      meas: function (q) { var f = fq(q); return { lines: ['C_L ' + fmt(q.CL * 1e12, 0) + ' pF at ' + fmt(q.T, 0) + ' °C: f = ' + f + ' Hz'], meters: [['COUNTER', f + ' Hz'], ['OVEN', fmt(q.T, 0) + ' °C']], row: { CL: q.CL, T: q.T, f: f } }; },
      cols: [{ label: 'C_L (pF)', get: function (r) { return fmt(r.CL * 1e12, 0); } }, { label: 'T (°C)', get: function (r) { return fmt(r.T, 0); } }, { label: 'f (Hz)', get: function (r) { return String(r.f); } },
        { label: 'Δf/f (ppm)', get: function (r, i, rows) { var b = rows.filter(function (x) { return Math.abs(x.T - p.Ti) < 1e-9 && x.CL === r.CL; })[0]; return b ? fmt((r.f / b.f - 1) * 1e6, 2) : '—'; } }],
      need: 8,
      runs: CLS.map(function (c, i) { return i === 0 ? { CL: c, T: p.Ti } : { CL: c }; }).concat([-20, 0, 10, 40, 50, 70].map(function (t, i) { return i === 0 ? { CL: 2e-11, T: t } : { T: t }; })),
      okFn: function (rows) { return cl(rows).length >= 3; },
      graph: { x: function (r) { return Math.abs(r.T - p.Ti) < 1e-9 ? 1e-12 / (p.C0 + r.CL) : NaN; }, y: function (r) { return r.f; }, xlabel: '1 pF/(C0 + C_L)', ylabel: 'f (Hz)', line: lineFit },
      result: function (rows) { var a = cl(rows), l = ols(a.map(function (r) { return [1 / (p.C0 + r.CL), r.f]; })), tr = rows.filter(function (r) { return Math.abs(r.CL - 2e-11) < 1e-15; }).map(function (r) { return r.f; });
        return { label: 'Motional capacitance C1', value: 2 * l.m / l.c * 1e15, unit: 'fF', digits: 3, truth: p.C1 * 1e15,
          note: 'From the line f = f_s + (f_s C1/2)·1/(C0 + C_L): series resonance f_s = ' + fmt(l.c, 0) + ' Hz. Over the oven run the frequency moved by ' + (tr.length > 1 ? fmt((Math.max.apply(null, tr) - Math.min.apply(null, tr)) / Math.min.apply(null, tr) * 1e6, 2) + ' ppm' : '—') + ', the crystal\'s stability.' }; },
      resultNote: 'Because C1 is a few femtofarads, a change of tens of picofarads in the load moves the frequency by only a few hundred ppm: the circuit hardly matters, the crystal decides. Temperature does more, along the AT-cut\'s cubic curve.',
      chips: ['Why is a crystal so stable?', 'What is pulling?', 'Why an AT cut?', 'Check my readings'],
      viva: [['Raising the load capacitance of a crystal oscillator', ['lowers its frequency slightly', 'raises it', 'stops it'], 0, 'f_L = f_s(1 + C1/(2(C0 + C_L))).']] };
  };

  // ---------------------------------------------------------------- multivibrators
  PLANS['pe9-multivibrators'] = function () {
    var tech = Math.round(p.tech), mode = Math.round(p.mode), TEC = ['transistor', '555', 'op-amp'][tech], MOD = ['astable', 'monostable', 'bistable'][mode];
    var lg = Math.log((2 * p.Vcc - p.Vce - p.Vbe) / (p.Vcc - p.Vbe)), bb = p.R1 / (p.R1 + p.R2);
    var RV = [4700, 10000, 15000, 22000, 33000, 47000], ctl, cOf, rlabel;
    if (mode === 2 && tech === 0) ctl = { param: 'ftrig', label: 'Trigger frequency', short: 'TRIGGER', unit: 'Hz', digits: 0, fmtv: fLabel, vals: [100, 200, 500, 1000, 2000, 5000] };
    else if (mode === 2 && tech === 1) ctl = { param: 'Vcc', label: 'Supply voltage', short: 'V_cc', unit: 'V', digits: 0, vals: [5, 6, 9, 12, 15] };
    else if (mode === 2) ctl = { param: 'R1', label: 'Feedback resistor R1', short: 'R1', unit: 'Ω', digits: 0, fmtv: rLabel, vals: [2200, 4700, 10000, 15000, 22000] };
    else ctl = { param: tech === 0 && mode === 0 ? 'R2' : tech === 1 && mode === 0 ? 'R2' : 'R', label: 'Timing resistor', short: 'R', unit: 'Ω', digits: 0, fmtv: rLabel, vals: RV };
    function tm(q) { return memo('mv', q, function (qq) { var t = KN.times(qq), tr = KN.trace(qq); t.x = tr[0]; t.y = tr[1]; t.dt = tr[2]; return t; }); }
    cOf = function (r) { var R = r.s;
      if (mode === 0) return tech === 0 ? r.m / ((p.R1 + R) * lg) : tech === 1 ? r.m / ((p.R1 + 2 * R) * Math.log(2)) : r.m / (2 * R * Math.log((1 + bb) / (1 - bb)));
      return tech === 0 ? r.m / (R * lg) : tech === 1 ? r.m / (R * Math.log(3)) : r.m / (R * Math.log((1 + p.Vd / p.Vsat) / (1 - bb))); };
    rlabel = mode < 2 ? 'Timing capacitor C' : tech === 0 ? 'Division ratio T_out/T_trigger' : tech === 1 ? 'Upper threshold / V_cc' : 'Saturation voltage V_sat';
    function resOf(r) { if (mode < 2) return cOf(r) * 1e9; if (tech === 0) return r.m * r.s; if (tech === 1) return r.m / r.s; return r.m / (r.s / (r.s + p.R2)); }
    var truth = mode < 2 ? p.C * 1e9 : tech === 0 ? 2 : tech === 1 ? 2 / 3 : p.Vsat;
    return {
      compName: TEC + ' ' + MOD + ' multivibrator', wiring: (tech === 0 ? 'Two BC547 transistors cross-coupled' + (mode === 0 ? ' by two capacitors C (unknown), base resistors R1 = ' + rLabel(p.R1) + ' and R2 from the box' : mode === 1 ? ' — one by the timing capacitor C (unknown) and resistor R, one by a resistor — triggered from the generator' : ' by resistors, with steering diodes taking the trigger pulses') : tech === 1 ? 'NE555 ' + (mode === 0 ? 'with R1 = ' + rLabel(p.R1) + ', R2 from the box and C (unknown)' : mode === 1 ? 'with R from the box and C (unknown), triggered on pin 2' : 'with trigger and threshold joined, fed by a triangle from the generator') : '741 ' + (mode === 2 ? 'Schmitt trigger: R1 from the box, R2 = ' + rLabel(p.R2) + ', triangle input' : 'with feedback divider R1 = ' + rLabel(p.R1) + ', R2 = ' + rLabel(p.R2) + ', timing R from the box and C (unknown)' + (mode === 1 ? ', clamp diode, triggered' : ''))) + '. Supply ' + (tech === 2 ? '±15 V' : p.Vcc + ' V') + '; channel 1 on the timing node or input, channel 2 on the output.',
      formula: mode === 0 ? (tech === 0 ? 'T = (R1 + R2) C ln((2V_cc − V_CE − V_BE)/(V_cc − V_BE))' : tech === 1 ? 'T = 0.693 (R1 + 2R2) C,  duty = (R1 + R2)/(R1 + 2R2)' : 'T = 2RC ln((1 + β)/(1 − β)),  β = R1/(R1 + R2)')
        : mode === 1 ? (tech === 0 ? 'W = R C ln((2V_cc − V_CE − V_BE)/(V_cc − V_BE)) ≈ 0.69 RC' : tech === 1 ? 'W = 1.1 R C' : 'W = R C ln((1 + V_D/V_sat)/(1 − β))') : (tech === 0 ? 'f_out = f_trigger / 2' : tech === 1 ? 'switches at V_cc/3 and 2V_cc/3' : 'switches at ±β V_sat'),
      controls: [ctl],
      art: function () { if (tech === 0) { to92(-0.04, -0.02, 'BC547'); to92(0.03, -0.02, 'BC547'); } else dip8(0.0, -0.02, tech === 1 ? 'NE555' : 'uA741'); resistor(-0.07, -0.02, p.R1, 'R1'); resistor(0.07, -0.02, mode === 0 ? p.R2 : p.R, mode === 0 ? 'R2' : 'R');
        if (!(mode === 2)) capacitor(0.0, 0.02, p.C, 'C', 'ceramic', true); var lp = ledPart(0.06, 0.03, '#ff4030', 'OUT'); battery(0.11, 0.035, tech === 2 ? '±15 V' : p.Vcc + ' V'); return function () { lp.set(0.8); }; },
      trace: function (q) { var t = tm(q), ch = [{ y: t.y, color: CYA, name: 'OUT' }]; if (mode === 2 && tech > 0) ch.unshift({ y: t.x, color: YEL, name: 'IN' }); else if (mode === 1) ch.unshift({ y: t.x, color: YEL, name: 'TRIG' });
        return { dt: t.dt, ch: ch, marks: mode === 2 && tech > 0 ? [{ kind: 'h', ch: 0, y: t.thi }, { kind: 'h', ch: 0, y: t.tlo }] : [] }; },
      meas: function (q) { var t = tm(q), s = q[ctl.param], txt;
        if (mode === 0) txt = 'Period ' + eng(t.main, 's') + ' (f = ' + fmt(1 / t.main, 1) + ' Hz), duty cycle ' + fmt(t.duty * 100, 1) + ' %';
        else if (mode === 1) txt = 'Pulse width ' + eng(t.main, 's');
        else if (tech === 0) txt = 'Output period ' + eng(t.main, 's') + ' for a trigger every ' + eng(1 / q.ftrig, 's');
        else txt = 'Switches at ' + fmt(t.thi, 3) + ' V (rising) and ' + fmt(t.tlo, 3) + ' V (falling)';
        return { lines: [ctl.label + ' ' + (ctl.fmtv ? ctl.fmtv(s) : fmt(s, 0) + ' ' + ctl.unit) + ': ' + txt], meters: [[mode === 2 && tech > 0 ? 'UPPER' : mode === 1 ? 'WIDTH' : 'PERIOD', mode === 2 && tech > 0 ? fmt(t.thi, 3) + ' V' : eng(t.main, 's')], [mode === 0 ? 'DUTY' : mode === 2 && tech > 0 ? 'LOWER' : 'SET', mode === 0 ? fmt(t.duty * 100, 1) + ' %' : mode === 2 && tech > 0 ? fmt(t.tlo, 3) + ' V' : (ctl.fmtv ? ctl.fmtv(s) : fmt(s, 0))]],
          row: { s: s, m: t.main, duty: t.duty, lo: t.tlo } }; },
      cols: [{ label: ctl.label, get: function (r) { return ctl.fmtv ? ctl.fmtv(r.s) : fmt(r.s, 0) + ' ' + ctl.unit; } }, { label: mode === 0 ? 'T (ms)' : mode === 1 ? 'W (ms)' : tech === 0 ? 'T_out (ms)' : 'Upper (V)', get: function (r) { return mode === 2 && tech > 0 ? fmt(r.m, 3) : fmt(r.m * 1000, 4); } },
        { label: mode === 0 ? 'Duty (%)' : mode === 2 && tech > 0 ? 'Lower (V)' : '—', get: function (r) { return mode === 0 ? fmt(r.duty * 100, 1) : mode === 2 && tech > 0 ? fmt(r.lo, 3) : '—'; } }, { label: rlabel, get: function (r) { return fmt(resOf(r), mode < 2 ? 2 : 3); } }],
      need: 4,
      runs: ctl.vals.map(function (v) { var o = {}; o[ctl.param] = v; return o; }),
      graph: { x: function (r) { return mode < 2 ? r.s / 1000 : r.s; }, y: function (r) { return mode < 2 || tech === 0 ? r.m * 1000 : r.m; }, xlabel: ctl.label + (mode < 2 ? ' (kΩ)' : ''), ylabel: mode === 0 ? 'T (ms)' : mode === 1 ? 'W (ms)' : tech === 0 ? 'T_out (ms)' : 'Upper threshold (V)' },
      result: function (rows) { var v = mean(rows.map(resOf));
        return { label: rlabel, value: v, unit: mode < 2 ? 'nF' : tech === 2 ? 'V' : '', digits: mode < 2 ? 2 : 3, truth: truth, note: 'From each reading with the circuit\'s own formula, averaged over ' + rows.length + '.' + (mode === 0 ? ' Duty cycle ' + fmt(rows[0].duty * 100, 1) + ' %.' : '') }; },
      resultNote: mode === 0 ? 'The circuit has no stable state, so the timing capacitor alternately charges and is reset: the period is set by RC and the switching thresholds.' : mode === 1 ? 'One trigger gives one pulse whose width is set by RC, after which the circuit returns to its stable state and waits.' : tech === 0 ? 'A bistable stays in either state until triggered; triggered on every pulse it toggles, so its output repeats every two triggers: a divide-by-two.' : 'With positive feedback the circuit switches at two different input levels, its hysteresis; between them it remembers its last state.',
      chips: ['What makes it astable?', 'What sets the pulse width?', 'What is hysteresis?', 'Check my readings'],
      viva: [['A 555 monostable\'s pulse width is', ['1.1 RC', '0.693 RC', 'RC'], 0, 'C charges from 0 to 2V_cc/3: ln 3 = 1.1.']] };
  };

  // ---------------------------------------------------------------- CE amplifier designed for a gain
  PLANS['pe9-ce-design'] = function () {
    var FS = decades([1, 2.2, 4.7], 1, 1000000).concat([10000000]), B = KN.bias(p), rp = p.Rc * p.RL / (p.Rc + p.RL);
    FS = FS.concat([1500, 3300, 6800, 15, 33, 68, 150, 1500000, 3300000, 6800000]).sort(function (a, b) { return a - b; }).filter(function (v, i, a) { return i === 0 || v !== a[i - 1]; });
    function g(q) { return memo('ce', q, function (qq) { return KN.gain(qq, qq.f, qq.Rx); }); }
    function mid(rows) { var a = rows.filter(function (r) { return r.Rx === 0 && r.f === 10000; })[0]; return a ? a.g : NaN; }
    function band(rows) { var a = rows.filter(function (r) { return r.Rx === 0; }), m = mid(rows), c = crossings(a.map(function (r) { return [r.f, r.g]; }), m / Math.SQRT2); return c.length >= 2 ? [c[0], c[c.length - 1]] : null; }
    function zin(rows) { var m = mid(rows), z = rows.filter(function (r) { return r.Rx > 0 && r.f === 10000; }).map(function (r) { return r.Rx * r.g / (m - r.g); }); return z.length ? mean(z) : NaN; }
    return {
      compName: 'BC547B common-emitter stage: R1 = 47 kΩ, R2 = 10 kΩ, R_c = 2.2 kΩ, R_L = 10 kΩ, Re1 = ' + fmt(p.Re1, 0) + ' Ω unbypassed + ' + fmt(p.Re2, 0) + ' Ω bypassed',
      wiring: 'Generator (10 mV) → test resistor R_x → 10 µF → base; collector to 12 V through R_c; emitter through Re1 and Re2 (Re2 bypassed by 100 µF); output through 10 µF to R_L. Channel 1 on the generator, channel 2 on the output. Bias: I_E = ' + fmt(B[0] * 1000, 3) + ' mA, r_e = ' + fmt(B[1], 1) + ' Ω.',
      formula: 'A_v = α (R_c ∥ R_L)/(r_e + Re1) = α × ' + fmt(rp, 0) + ' Ω/(' + fmt(B[1], 1) + ' + ' + fmt(p.Re1, 0) + ') Ω;   Z_in = R_x v/(v₀ − v)',
      controls: [{ param: 'Rx', label: 'Series test resistor R_x', short: 'R_x', unit: 'Ω', digits: 0, fmtv: function (v) { return v ? rLabel(v) : 'shorted'; }, vals: [0, 1000, 2200, 4700, 10000] },
        { param: 'f', label: 'Generator frequency', short: 'FREQUENCY', unit: 'Hz', digits: 0, fmtv: fLabel, vals: FS }],
      art: function () { to92(0.0, -0.02, 'BC547B'); resistor(-0.06, -0.05, p.R1, 'R1'); resistor(-0.06, 0.0, p.R2, 'R2'); resistor(0.05, -0.05, p.Rc, 'Rc'); resistor(0.05, 0.0, Math.max(p.Re1, 1), 'Re1'); capacitor(0.09, 0.02, p.CE, 'CE', 'el'); var rx = resistor(-0.1, -0.03, 1000, 'Rx');
        battery(0.11, 0.035, '12 V'); jumper([-0.115, -0.03], [-0.13, 0.03], 'yellow'); return function (q) { if (q.Rx) rx.set(q.Rx); }; },
      trace: function (q) { var m = g(q), t = sineTrace(q.f, [0.01, 0.01 * m], [0, Math.PI], 3); return { dt: t.dt, ch: [{ y: t.ys[0], color: YEL, name: 'GEN' }, { y: t.ys[1], color: CYA, name: 'OUT' }] }; },
      meas: function (q) { var m = g(q); return { lines: [fLabel(q.f) + (q.Rx ? ', R_x = ' + rLabel(q.Rx) : '') + ': gain ' + fmt(m, 3) + ' (output ' + fmt(m * 10, 2) + ' mV peak)'], meters: [['FREQ', fLabel(q.f)], ['GAIN', fmt(m, 3)]], row: { Rx: q.Rx, f: q.f, g: m } }; },
      cols: [{ label: 'R_x (Ω)', get: function (r) { return fmt(r.Rx, 0); } }, { label: 'f (Hz)', get: function (r) { return fmt(r.f, 0); } }, { label: 'Gain', get: function (r) { return fmt(r.g, 3); } }, { label: 'Z_in (kΩ)', get: function (r, i, rows) { var m = mid(rows); return r.Rx > 0 && r.f === 10000 && isFinite(m) ? fmt(r.Rx * r.g / (m - r.g) / 1000, 3) : '—'; } }],
      need: 14,
      runs: [1, 2.2, 4.7, 10, 15, 22, 33, 47, 68, 100, 150, 220, 470, 1000, 10000, 100000, 1000000, 1500000, 2200000, 3300000, 4700000, 6800000, 10000000].map(function (f, i) { return i === 0 ? { Rx: 0, f: f } : { f: f }; })
        .concat([1000, 2200, 4700, 10000].map(function (r, i) { return i === 0 ? { Rx: r, f: 10000 } : { Rx: r }; })),
      okFn: function (rows) { return isFinite(mid(rows)) && !!band(rows) && isFinite(zin(rows)); },
      graph: { x: function (r) { return r.Rx === 0 ? ln10(r.f) : NaN; }, y: function (r) { return r.g; }, xlabel: 'log10 (f / Hz), R_x shorted', ylabel: 'Gain' },
      result: function (rows) { var m = mid(rows), b = band(rows) || [NaN, NaN];
        return { label: 'Mid-band voltage gain', value: m, unit: '', digits: 2, truth: HK.TEXTBOOK.pe9_ce_amid(p),
          note: 'Design value α(R_c ∥ R_L)/(r_e + Re1) = ' + fmt(HK.TEXTBOOK.pe9_ce_amid(p), 2) + '. Half-power frequencies ' + fmt(b[0], 1) + ' Hz and ' + fmt(b[1] / 1e6, 3) + ' MHz (bandwidth ' + fmt((b[1] - b[0]) / 1e6, 3) + ' MHz). Input impedance from the R_x readings: ' + fmt(zin(rows) / 1000, 3) + ' kΩ (model (β + 1)(r_e + Re1) ∥ R_th).' }; },
      resultNote: 'The unbypassed resistor Re1 trades gain for predictability: with it, the gain is set mostly by resistors and the input impedance rises; with none, the gain depends on r_e and so on the bias current and temperature. The bypass and coupling capacitors decide where the low-frequency response falls off.',
      chips: ['How do I choose Re1?', 'Why does the input impedance change?', 'What sets the lower cut-off?', 'Check my readings'],
      viva: [['With Re1 = 0 and I_E = 1 mA, the gain of a stage with R_c ∥ R_L = 2 kΩ is about', ['77', '20', '2'], 0, '2000/26.']] };
  };

  var PL = (PLANS[BASE] || PLANS['pe9-regulator'])();
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
