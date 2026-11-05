/* Prayogshala studio module: SIGNAL-RECOVERY AND NOISE BENCH (Ph.D. research techniques).
   One bench, five instruments, one kernel each of packs/phd_optics.js:
     phd_lockin   a chopped photodiode signal buried in noise and a lock-in amplifier (single phase, then dual phase);
     phd_johnson  a decade of metal-film resistors, a low-noise amplifier and a true-rms voltmeter, at room temperature
                  and in liquid nitrogen;
     phd_shot     a photodiode lit by an LED, a transimpedance amplifier and the same voltmeter;
     phd_psd      a resistor and an amplifier board in front of an FFT spectrum analyser;
     phd_boxcar   a pulsed light source, a photodiode and a boxcar averager.
   Every reading is a simulated measurement: the noise is drawn from the lab's own seed, the answer is found by the
   student's own average, slope or fit, and the bench never shows the quantity it is measuring. */
/* ---- shared bench kit (the same few helpers are built into every Ph.D. instrument rig) ---- */
function phdKit(S) {
  var T = S.T, M = S.M, K = {};
  K.r = function (v, d) { var k = Math.pow(10, d === undefined ? 2 : d); return Math.round(v * k) / k; };
  K.si = function (v, unit, d) {
    if (!isFinite(v)) return '—'; if (v === 0) return '0 ' + unit;
    var a = Math.abs(v), pre = [['G', 1e9], ['M', 1e6], ['k', 1e3], ['', 1], ['m', 1e-3], ['µ', 1e-6], ['n', 1e-9], ['p', 1e-12], ['f', 1e-15]], i;
    for (i = 0; i < pre.length; i++) if (a >= pre[i][1] * 0.9995) break;
    if (i === pre.length) i = pre.length - 1;
    return String(parseFloat((v / pre[i][1]).toPrecision(d || 3))) + ' ' + pre[i][0] + unit;
  };
  K.busy = function () { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; };
  K.wpt = function (o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); };
  K.knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  K.knob = function (parent, u, v, z0, rad) {
    var kg = new T.Group(); kg.position.set(u, v, z0); parent.add(kg);
    var sk = S.mesh(new T.CylinderGeometry(rad * 1.3, rad * 1.38, 0.004, 36), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; kg.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(rad, rad * 1.1, 0.016, 36), new T.MeshStandardMaterial({ map: K.knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; kg.add(kb);
    var kp = S.mesh(new T.BoxGeometry(0.002, rad * 1.1, 0.0012), M.white, false); kp.position.set(0, rad * 0.65, 0.0215); kg.add(kp);
    return kg;
  };
  K.button = function (parent, u, v, z0, color) {
    var b = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.008, 20), color || M.green); b.rotation.x = Math.PI / 2; b.position.set(u, v, z0 + 0.004); parent.add(b); return b;
  };
  // an instrument case on the bench: front panel with printed title, a screen, knobs and buttons.
  // o = { x, z, ry, w, h, d, title, sub, screen: { u, v, w, h }, knobs: [[u, v, r, label]], buttons: [[u, v, label, color]], tint }
  K.instrument = function (o) {
    var g = new T.Group(); g.position.set(o.x, 0, o.z); g.rotation.y = o.ry || 0; S.scene.add(g);
    var W = o.w, Hh = o.h, D = o.d, FZ = D / 2 + 0.0062, PW = W - 0.014, PH = Hh - 0.014;
    var cs = S.rounded(W, D, Hh, 0.01, new T.MeshStandardMaterial({ color: o.tint || 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); cs.rotation.x = -Math.PI / 2; cs.position.y = Hh / 2 + 0.004; g.add(cs);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.004, 14), M.rubber); ft.position.set(f[0] * (W / 2 - 0.02), 0.002, f[1] * (D / 2 - 0.02)); g.add(ft); });
    var tex = S.canvasTex(1400, Math.round(1400 * PH / PW), function (x, w, h) {
      var k = w / PW, X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; };
      x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
      x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0125 * k) + 'px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText(o.title, 28, 52);
      x.fillStyle = '#c7ccd6'; x.font = '500 ' + Math.round(0.0075 * k) + 'px "Public Sans", sans-serif'; x.fillText(o.sub || '', 28, 88);
      x.textAlign = 'center'; x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0068 * k) + 'px "Public Sans", sans-serif';
      (o.knobs || []).forEach(function (q) { x.fillText(q[3] || '', X(q[0]), Y(q[1] - q[2] * 1.9 - 0.004)); });
      (o.buttons || []).forEach(function (q) { x.fillText(q[2] || '', X(q[0]), Y(q[1] - 0.019)); });
      x.textAlign = 'left';
    });
    var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]); fac.position.set(0, 0.004 + Hh / 2, FZ - 0.002); g.add(fac);
    var cy = 0.004 + Hh / 2, I = { g: g, FZ: FZ, cy: cy, knobs: [], buttons: [], PH: PH, PW: PW };
    I.at = function (u, v, dz) { return new T.Vector3(u, cy + v, FZ + (dz || 0)); };
    (o.knobs || []).forEach(function (q) { var kn = K.knob(g, q[0], cy + q[1], FZ, q[2]); I.knobs.push(kn); });
    (o.buttons || []).forEach(function (q) { I.buttons.push(K.button(g, q[0], cy + q[1], FZ, q[3])); });
    if (o.screen) {
      var sc = o.screen, pxw = 1024, pxh = Math.round(1024 * sc.h / sc.w), stex = S.liveTex(pxw, pxh);
      var bez = S.mesh(new T.BoxGeometry(sc.w + 0.008, sc.h + 0.008, 0.003), M.grey); bez.position.copy(I.at(sc.u, sc.v, 0.001)); g.add(bez);
      var scr = new T.Mesh(new T.PlaneGeometry(sc.w, sc.h), new T.MeshBasicMaterial({ map: stex, toneMapped: false })); scr.position.copy(I.at(sc.u, sc.v, 0.0035)); g.add(scr);
      I.screen = { tex: stex, w: pxw, h: pxh, paint: function (fn) { stex.draw(function (x, w, h) { fn(x, w, h); }); } };
    }
    return I;
  };
  // a panel canvas in the step pane that shares the 3D screen's drawing
  K.panel = function (u, ratio) {
    var cv = document.createElement('canvas'); cv.width = 760; cv.height = Math.round(760 * ratio);
    cv.style.cssText = 'width:100%;border-radius:10px;border:1px solid var(--line);background:#06130c'; u.el(cv); return cv;
  };
  // plot helpers for the green instrument screens
  K.bg = function (x, w, h) { x.fillStyle = '#06130c'; x.fillRect(0, 0, w, h); };
  K.chart = function (x, R, o) {
    var lx = o.xlog ? Math.log(o.xr[0]) : o.xr[0], hx = o.xlog ? Math.log(o.xr[1]) : o.xr[1], ly = o.ylog ? Math.log(o.yr[0]) : o.yr[0], hy = o.ylog ? Math.log(o.yr[1]) : o.yr[1], i, fs = Math.round(R.h * 0.075);
    var X = function (v) { return R.x + R.w * ((o.xlog ? Math.log(v) : v) - lx) / (hx - lx); }, Y = function (v) { return R.y + R.h - R.h * ((o.ylog ? Math.log(v) : v) - ly) / (hy - ly); };
    x.strokeStyle = 'rgba(120,220,150,.2)'; x.lineWidth = 1;
    for (i = 0; i <= 8; i++) { x.beginPath(); x.moveTo(R.x + R.w * i / 8, R.y); x.lineTo(R.x + R.w * i / 8, R.y + R.h); x.stroke(); }
    for (i = 0; i <= 6; i++) { x.beginPath(); x.moveTo(R.x, R.y + R.h * i / 6); x.lineTo(R.x + R.w, R.y + R.h * i / 6); x.stroke(); }
    x.strokeStyle = 'rgba(120,220,150,.55)'; x.strokeRect(R.x, R.y, R.w, R.h);
    x.fillStyle = '#9fe0b8'; x.font = fs + 'px "JetBrains Mono", monospace'; x.textAlign = 'left';
    if (o.xlabel) x.fillText(o.xlabel, R.x + 4, R.y + R.h + fs * 1.3);
    if (o.ylabel) x.fillText(o.ylabel, R.x + 4, R.y - fs * 0.35);
    return { X: X, Y: Y };
  };
  K.poly = function (x, ch, pts, col, lw) {
    x.strokeStyle = col; x.lineWidth = lw || 2.2; x.beginPath();
    for (var i = 0; i < pts.length; i++) { var px = ch.X(pts[i][0]), py = ch.Y(pts[i][1]); if (i) x.lineTo(px, py); else x.moveTo(px, py); } x.stroke();
  };
  K.dots = function (x, ch, pts, col, rad) { x.fillStyle = col; pts.forEach(function (q) { x.beginPath(); x.arc(ch.X(q[0]), ch.Y(q[1]), rad || 3, 0, Math.PI * 2); x.fill(); }); };
  K.text = function (x, t, px, py, col, size, al) { x.fillStyle = col || '#9fe0b8'; x.font = size + 'px "JetBrains Mono", monospace'; x.textAlign = al || 'left'; x.fillText(t, px, py); };
  // a BNC socket on the side of a case / box
  K.bnc = function (parent, x, y, z, rotY) {
    var g = new T.Group(); g.position.set(x, y, z); g.rotation.y = rotY || 0; parent.add(g);
    var b = S.mesh(new T.CylinderGeometry(0.0065, 0.0065, 0.012, 20), M.chrome); b.rotation.x = Math.PI / 2; g.add(b);
    var pin = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.014, 8), M.brass); pin.rotation.x = Math.PI / 2; pin.position.z = 0.002; g.add(pin);
    return g;
  };
  K.box = function (w, h, d, color, x, y, z, parent) { var b = S.rounded(w, d, h, Math.min(0.004, w / 6), new T.MeshStandardMaterial({ color: color, roughness: 0.55, metalness: 0.1 })); b.rotation.x = -Math.PI / 2; b.position.set(x, y + h / 2, z); (parent || S.scene).add(b); return b; };
  // a tiny Lehmer + Box-Muller generator for decorative noise on the screens (same stream as the pack's)
  K.rnd = function (seed) {
    var s = (Math.floor(Math.abs(seed)) % 2147483646) + 1, has = false, z1 = 0, o = {};
    o.next = function () { s = (s * 16807) % 2147483647; return s / 2147483647; };
    o.gauss = function () { if (has) { has = false; return z1; } var a = o.next(), b = o.next(), q = Math.sqrt(-2 * Math.log(a)); z1 = q * Math.sin(2 * Math.PI * b); has = true; return q * Math.cos(2 * Math.PI * b); };
    return o;
  };
  return K;
}

HoolaStudio.define('phd-noise-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, Kt = phdKit(S), r = Kt.r, si = Kt.si;
  var MODE = ({ phd_lockin: 'lockin', phd_johnson: 'johnson', phd_shot: 'shot', phd_psd: 'psd', phd_boxcar: 'boxcar' })[KERN];
  var TCOLD = 77, TCS = [0.1, 0.3, 1, 3], NS = [1, 4, 16, 64, 256], SEGS = [4, 16, 64, 256];
  var st = { on: false, idx: 0, cur: null, tc: 1, phr: 0, sel: 0, cold: false, nseg: 16, sp: null, ab: null, N: 1, gdel: 0, prog: 0, rep: 0 };
  var dirty = true;
  function mark() { dirty = true; }
  function Rs() { return KN.RS || []; }
  var RSEL = MODE === 'johnson' ? KN.RS : MODE === 'shot' ? KN.IS.map(function (v) { return v * (p.Iscale || 1); }) : [];
  function ohm(v) { return v === 0 ? 'SHORT' : si(v, 'Ω', 2); }

  // ================================================================ the bench: device under test
  var dut = new T.Group(); S.scene.add(dut); dut.position.set(-0.55, 0, -0.26);
  var spin = null, dewarCan = null, canY0 = 0, selKnob = null, lampMat = null;
  if (MODE === 'lockin') {
    var motor = Kt.box(0.07, 0.07, 0.06, 0x3a3f47, 0, 0, 0, dut);
    var disc = S.mesh(new T.CylinderGeometry(0.06, 0.06, 0.003, 48), new T.MeshStandardMaterial({ color: 0x1b1d20, roughness: 0.5, metalness: 0.5 }));
    disc.rotation.x = Math.PI / 2; disc.position.set(0, 0.09, 0.034); dut.add(disc); spin = disc;
    for (var sl = 0; sl < 6; sl++) { var a = sl * Math.PI / 3, slot = S.mesh(new T.BoxGeometry(0.018, 0.012, 0.0036), new T.MeshStandardMaterial({ color: 0x9aa2ab, roughness: 0.4, metalness: 0.6 }), false); slot.position.set(Math.cos(a) * 0.043, Math.sin(a) * 0.043, 0); slot.rotation.z = a + Math.PI / 2; disc.add(slot); }
    var hub = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.01, 20), M.chrome); hub.rotation.x = Math.PI / 2; hub.position.set(0, 0.09, 0.036); dut.add(hub);
    lampMat = new T.MeshStandardMaterial({ color: 0x553300, emissive: 0x000000, roughness: 0.4 });
    var lamp = S.mesh(new T.CylinderGeometry(0.012, 0.015, 0.04, 18), lampMat); lamp.rotation.x = Math.PI / 2; lamp.position.set(0, 0.09, 0.075); dut.add(lamp);
    var lstand = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.09, 10), M.chrome); lstand.position.set(0, 0.045, 0.09); dut.add(lstand);
    var pdcan = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.03, 18), M.chrome); pdcan.rotation.x = Math.PI / 2; pdcan.position.set(0, 0.09, -0.012); dut.add(pdcan);
    var pst = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.09, 10), M.chrome); pst.position.set(0, 0.045, -0.012); dut.add(pst);
    var lb = S.label('OPTICAL CHOPPER', { w: 0.07, ratio: 0.18, color: '#e8e8ea' }); lb.rotation.x = -Math.PI / 2; lb.position.set(0, 0.0012 + 0.06, 0.0); lb.position.y = 0.0014; lb.position.z = 0.1; dut.add(lb);
  } else if (MODE === 'johnson') {
    var rb = Kt.box(0.14, 0.07, 0.1, 0x6f8193, 0, 0, 0, dut);
    var rl = S.label('RESISTOR DECADE · metal film · 0.1 %', { w: 0.13, ratio: 0.1, color: '#f1efe8', bg: '#2b323d', px: 768 }); rl.position.set(0, 0.053, 0.0507); dut.add(rl);
    selKnob = Kt.knob(dut, 0, 0.032, 0.05, 0.014);
    var dial = S.canvasTex(512, 512, function (x, w, h) { x.fillStyle = 'rgba(0,0,0,0)'; x.clearRect(0, 0, w, h); x.fillStyle = '#f1efe8'; x.font = '600 34px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (var i = 0; i < 8; i++) { var ang = 2.35 - i * 0.67; x.fillText(i === 0 ? 'S' : ['1k', '2k', '5k', '10k', '20k', '50k', '100k'][i - 1], w / 2 + Math.cos(ang) * 210, h / 2 - Math.sin(ang) * 210 + 12); } });
    var dm = new T.Mesh(new T.PlaneGeometry(0.1, 0.1), new T.MeshBasicMaterial({ map: dial, transparent: true })); dm.position.set(0, 0.032, 0.0512); dut.add(dm);
    var dew = new T.Group(); dew.position.set(0.19, 0, -0.01); dut.add(dew);
    var dwb = S.mesh(new T.CylinderGeometry(0.055, 0.05, 0.16, 36, 1, true), M.alu); dwb.position.y = 0.08; dew.add(dwb);
    var dwf = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.004, 36), M.alu); dwf.position.y = 0.002; dew.add(dwf);
    var dwl = S.mesh(new T.CylinderGeometry(0.048, 0.048, 0.002, 36), new T.MeshStandardMaterial({ color: 0xb8d6e6, roughness: 0.2, metalness: 0.2, transparent: true, opacity: 0.85 })); dwl.position.y = 0.1; dew.add(dwl);
    var dlb = S.label('LIQUID NITROGEN · gloves and goggles', { w: 0.07, ratio: 0.2, color: '#1b1b1b', bg: '#f2d02a', px: 768 }); dlb.position.set(0, 0.07, 0.0565); dew.add(dlb);
    dewarCan = new T.Group(); dewarCan.position.set(0.19, 0.24, -0.01); dut.add(dewarCan); canY0 = 0.24;
    var can = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.06, 20), M.steel); can.position.y = -0.03; dewarCan.add(can);
    var rod = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.2, 10), M.steel); rod.position.y = 0.1; dewarCan.add(rod);
    var cl = S.label('RESISTORS', { w: 0.03, ratio: 0.25, color: '#1b1b1b' }); cl.position.set(0, -0.03, 0.0205); dewarCan.add(cl);
    S.wire([[-0.55 + 0.0, 0.05, -0.26 + 0.05], [-0.55 + 0.1, 0.02, -0.26 + 0.08], [-0.55 + 0.19 - 0.02, 0.2, -0.26 - 0.01]], 'black');
  } else if (MODE === 'shot') {
    var drv = Kt.box(0.13, 0.06, 0.1, 0x6f8193, -0.02, 0, 0.0, dut);
    var dl = S.label('LED DRIVER · constant current', { w: 0.12, ratio: 0.1, color: '#f1efe8', bg: '#2b323d', px: 768 }); dl.position.set(-0.02, 0.046, 0.0507); dut.add(dl);
    selKnob = Kt.knob(dut, -0.02, 0.028, 0.05, 0.013);
    var tube = S.mesh(new T.CylinderGeometry(0.026, 0.026, 0.17, 30), new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.6 })); tube.rotation.z = Math.PI / 2; tube.position.set(0.2, 0.04, 0.0); dut.add(tube);
    [-1, 1].forEach(function (sg) { var cp = S.mesh(new T.CylinderGeometry(0.0285, 0.0285, 0.012, 30), M.alu); cp.rotation.z = Math.PI / 2; cp.position.set(0.2 + sg * 0.087, 0.04, 0); dut.add(cp); });
    var tl = S.label('LIGHT-TIGHT TUBE · LED → PHOTODIODE', { w: 0.15, ratio: 0.1, color: '#e8e8ea' }); tl.position.set(0.2, 0.04, 0.0265); dut.add(tl);
    var ts = S.mesh(new T.BoxGeometry(0.04, 0.012, 0.05), M.alu); ts.position.set(0.2, 0.006, 0); dut.add(ts);
    S.wire([[-0.55 + 0.1, 0.03, -0.26 + 0.0], [-0.55 + 0.1, 0.015, -0.26 + 0.06], [-0.55 + 0.2, 0.012, -0.26 + 0.06]], 'red');
  } else if (MODE === 'psd') {
    var pcb = S.mesh(new T.BoxGeometry(0.2, 0.004, 0.13), new T.MeshStandardMaterial({ color: 0x1f6b3a, roughness: 0.5 })); pcb.position.set(0.04, 0.012, 0); dut.add(pcb);
    for (var fi = 0; fi < 4; fi++) { var ft = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.01, 10), M.brass); ft.position.set(-0.04 + fi * 0.08, 0.005, -0.05); dut.add(ft); }
    var res = new T.Group(); res.position.set(-0.02, 0.026, 0.02); dut.add(res);
    var rbd = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.03, 14), new T.MeshStandardMaterial({ color: 0xcdb98a, roughness: 0.6 })); rbd.rotation.z = Math.PI / 2; res.add(rbd);
    [0xb8641a, 0x1b1b1b, 0xe0a010, 0xc8c8c8].forEach(function (c, i) { var bd = S.mesh(new T.CylinderGeometry(0.0057, 0.0057, 0.0028, 14), new T.MeshStandardMaterial({ color: c })); bd.rotation.z = Math.PI / 2; bd.position.x = -0.011 + i * 0.0068; res.add(bd); });
    var ic = S.mesh(new T.BoxGeometry(0.03, 0.007, 0.018), new T.MeshStandardMaterial({ color: 0x151515, roughness: 0.4 })); ic.position.set(0.06, 0.0185, 0.0); dut.add(ic);
    for (var pi = 0; pi < 4; pi++) [-1, 1].forEach(function (sg) { var pn = S.mesh(new T.BoxGeometry(0.0022, 0.003, 0.0016), M.chrome); pn.position.set(0.0495 + pi * 0.007, 0.0145, sg * 0.0098); dut.add(pn); });
    var il = S.label(V_.sample ? V_.sample.slice(0, 22) : 'RESISTOR + AMP', { w: 0.06, ratio: 0.2, color: '#d8d8d8' }); il.rotation.x = -Math.PI / 2; il.position.set(0.06, 0.0225, 0.0); dut.add(il);
    var bl = S.label('TEST BOARD · screened can removed', { w: 0.14, ratio: 0.1, color: '#e8e8ea' }); bl.rotation.x = -Math.PI / 2; bl.position.set(0.04, 0.0145, 0.052); dut.add(bl);
    S.wire([[-0.55 + 0.12, 0.02, -0.26 + 0.0], [-0.55 + 0.24, 0.015, -0.26 + 0.06], [-0.55 + 0.3, 0.02, -0.26 + 0.05]], 'black');
  } else {
    var pg = Kt.box(0.13, 0.06, 0.1, 0x6f8193, -0.02, 0, 0.0, dut);
    var pgl = S.label('PULSE GENERATOR · 1 µs · 1 kHz', { w: 0.12, ratio: 0.1, color: '#f1efe8', bg: '#2b323d', px: 768 }); pgl.position.set(-0.02, 0.046, 0.0507); dut.add(pgl);
    var led = S.mesh(new T.SphereGeometry(0.009, 16, 16), new T.MeshStandardMaterial({ color: 0x334400, emissive: 0x000000 })); led.position.set(0.14, 0.04, 0.0); dut.add(led); lampMat = led.material;
    var lstd = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.04, 10), M.chrome); lstd.position.set(0.14, 0.02, 0); dut.add(lstd);
    var ph = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.03, 18), M.chrome); ph.rotation.z = Math.PI / 2; ph.position.set(0.2, 0.04, 0); dut.add(ph);
    var phs = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.04, 10), M.chrome); phs.position.set(0.2, 0.02, 0); dut.add(phs);
    var phl = S.label('PHOTODIODE', { w: 0.04, ratio: 0.2, color: '#e8e8ea' }); phl.position.set(0.2, 0.04, 0.0145); dut.add(phl);
    S.wire([[-0.55 - 0.02, 0.04, -0.26 + 0.0], [-0.55 + 0.06, 0.03, -0.26 + 0.07], [-0.55 + 0.14, 0.04, -0.26]], 'red');
  }
  S.contact(0.5, 0.3, -0.47, -0.26, 0.45);

  // the low-noise amplifier between the device and the instrument
  var amp = new T.Group(); S.scene.add(amp); amp.position.set(-0.1, 0, -0.27);
  var abox = Kt.box(0.11, 0.06, 0.09, 0xb8bcc2, 0, 0, 0, amp);
  var alb = S.label(MODE === 'shot' ? 'TRANSIMPEDANCE AMP' : 'LOW-NOISE AMP', { w: 0.1, ratio: 0.12, color: '#1b1b1b' }); alb.position.set(0, 0.04, 0.0455); amp.add(alb);
  var alb2 = S.label(MODE === 'shot' ? 'Rf = ' + si(p.Rf, 'Ω', 2) : MODE === 'lockin' ? 'pre-amp' : MODE === 'boxcar' ? 'fast pre-amp' : '× ' + (p.G || 1) + ' voltage gain', { w: 0.08, ratio: 0.12, color: '#3a3f47' }); alb2.position.set(0, 0.022, 0.0455); amp.add(alb2);
  Kt.bnc(amp, -0.055, 0.03, 0.0, -Math.PI / 2); Kt.bnc(amp, 0.055, 0.03, 0.0, Math.PI / 2);
  S.wire([[-0.55 + 0.33, 0.04, -0.26 + 0.0], [-0.32, 0.02, -0.25], [-0.2, 0.03, -0.27]], 'black');
  S.contact(0.18, 0.15, -0.1, -0.27, 0.45);

  // ================================================================ the instrument
  var TITLES = { lockin: ['LOCK-IN AMPLIFIER', 'dual phase · X Y R θ · 0.1 s – 3 s'], johnson: ['TRUE-RMS VOLTMETER', 'band-limited · mean-square output'],
    shot: ['TRUE-RMS VOLTMETER', 'band-limited · mean-square output'], psd: ['FFT SPECTRUM ANALYSER', 'Hann window · averaged · 0 – 4 kHz'], boxcar: ['BOXCAR AVERAGER', 'gate delay · gate width · averages'] };
  var KNOBS = { lockin: [[0.1, 0.04, 0.012, 'TIME CONSTANT'], [0.1, -0.026, 0.012, 'REF PHASE']], johnson: [], shot: [], psd: [[0.12, 0.03, 0.013, 'AVERAGES']], boxcar: [[0.12, 0.03, 0.013, 'AVERAGES']] };
  var ins = Kt.instrument({ x: 0.22, z: -0.24, ry: -0.12, w: 0.42, h: 0.2, d: 0.26, title: TITLES[MODE][0], sub: TITLES[MODE][1],
    screen: { u: -0.06, v: 0.0, w: 0.25, h: 0.155 }, knobs: KNOBS[MODE], buttons: [[0.1, -0.058, 'POWER', M.green], [0.17, -0.058, MODE === 'psd' ? 'ACQUIRE' : 'READ', M.grey]] });
  var pwr = ins.buttons[0], go = ins.buttons[1], led1 = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }));
  led1.position.copy(ins.at(0.1, -0.035, 0.002)); ins.g.add(led1);
  S.wire([[-0.1 + 0.055, 0.03, -0.27], [0.0, 0.02, -0.24], [0.22 - 0.17, 0.045, -0.24 + 0.13]], 'black');
  S.contact(0.5, 0.34, 0.22, -0.24, 0.5);

  S.addApparatus('dut', dut, ({ lockin: 'Optical chopper, lamp and photodiode', johnson: 'Resistor decade and liquid-nitrogen dewar', shot: 'LED driver and light-tight photodiode tube',
    psd: 'Resistor and amplifier test board', boxcar: 'Pulsed light source and photodiode' })[MODE],
    ({ lockin: 'A lamp shines through a chopper wheel onto a photodiode, so the light reaches it as a square-ish wave at the chopper frequency. That frequency is the reference the lock-in locks on to.',
      johnson: 'Eight metal-film resistors on a rotary switch (the first position is a short). The small can on the rod holds the resistors and can be lowered into liquid nitrogen, which is about 77 K.',
      shot: 'A constant-current LED shines on a photodiode inside a light-tight tube. The LED current sets the photocurrent; nothing else changes.',
      psd: 'The resistor and the amplifier input stage on an open test board. The board is the source of all the noise the analyser sees.',
      boxcar: 'A pulse generator flashes an LED once every millisecond; a fast photodiode sees each flash decay. The same pulse arrives again and again, which is what boxcar averaging needs.' })[MODE]);
  S.addApparatus('amp', amp, 'Low-noise amplifier', 'It brings the tiny signal up to a level the instrument can use. Its own noise is in every reading and has to be allowed for.');
  S.addApparatus('ins', ins.g, TITLES[MODE][0].charAt(0) + TITLES[MODE][0].slice(1).toLowerCase(), 'The instrument that turns the noisy signal into a number. Read its screen the way you would a real one.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Power'), hudB = S.hudCard(MODE === 'lockin' ? 'Time constant' : MODE === 'johnson' ? 'Resistor' : MODE === 'shot' ? 'Photocurrent' : MODE === 'psd' ? 'Averages' : 'Averages'), hudC = S.hudCard('Readings');

  // ================================================================ what the screen shows
  var DEC = (function () { var g = Kt.rnd(77), o = [], i; for (i = 0; i < 600; i++) o.push(g.gauss()); return o; })();
  function lockinInput(n) {                                                // a short stretch of the noisy input, for show
    var pts = [], i, srms = p.en * Math.sqrt(10 * p.f / 2), ph = p.phi * Math.PI / 180;
    for (i = 0; i < n; i++) pts.push([i / (n - 1), (p.A * Math.cos(2 * Math.PI * 3 * i / (n - 1) + ph) + srms * DEC[i % 600]) * 1e6]);
    return pts;
  }
  function drawScreen(x, w, h) {
    Kt.bg(x, w, h); var fs = Math.round(h * 0.052), c = st.cur, i, ch, pts;
    if (!st.on) { Kt.text(x, 'power off', w / 2, h / 2, '#5aa77a', fs * 1.4, 'center'); return; }
    if (MODE === 'lockin') {
      ch = Kt.chart(x, { x: w * 0.04, y: h * 0.1, w: w * 0.92, h: h * 0.32 }, { xr: [0, 1], yr: [-60, 60], ylabel: 'INPUT  (µV)' });
      Kt.poly(x, ch, lockinInput(400), '#ffe45e', 1.6);
      Kt.text(x, 'time constant ' + st.tc + ' s    reference phase ' + st.phr + '°', w * 0.04, h * 0.5, '#9fe0b8', fs);
      var X = c && c.X !== undefined ? c.X * 1e6 : null, Y = c && c.Y !== undefined ? c.Y * 1e6 : null;
      Kt.text(x, 'X ' + (X === null ? '—' : r(X, 2) + ' µV'), w * 0.04, h * 0.64, '#ffe45e', fs * 1.7);
      Kt.text(x, 'Y ' + (c && c.k === 'XY' && Y !== null ? r(Y, 2) + ' µV' : '—'), w * 0.04, h * 0.77, '#64e3ff', fs * 1.7);
      Kt.text(x, c && c.k === 'XY' ? 'R ' + r(c.R * 1e6, 2) + ' µV   θ ' + r(c.th, 1) + '°' : 'R —   θ —', w * 0.04, h * 0.9, '#9fe0b8', fs * 1.7);
      Kt.text(x, c && c.k === 'XY' ? 'SNR ' + r(c.snr, 1) : '', w * 0.82, h * 0.9, '#9fe0b8', fs * 1.2, 'right');
    } else if (MODE === 'johnson' || MODE === 'shot') {
      var J = MODE === 'johnson', rows = S.rows.filter(function (q) { return !q.cold; });
      var vmax = 1.0e-9; for (i = 0; i < RSEL.length; i++) vmax = Math.max(vmax, KN.v2True(p, RSEL[i])); vmax *= 1.15;
      ch = Kt.chart(x, { x: w * 0.1, y: h * 0.4, w: w * 0.86, h: h * 0.48 }, { xr: [0, RSEL[RSEL.length - 1] * 1.05], yr: [0, vmax * 1e6], xlabel: J ? 'resistance R' : 'photocurrent I', ylabel: 'mean-square output  (mV²)' });
      Kt.dots(x, ch, rows.map(function (q) { return [J ? q.R : q.I, q.v2 * 1e6]; }), '#ffe45e', 4);
      Kt.text(x, J ? 'T = ' + (st.cold ? TCOLD : p.T) + ' K   R = ' + ohm(RSEL[st.sel]) : 'LED current ' + (RSEL[st.sel] * 1e6 < 1 ? r(RSEL[st.sel] * 1e9, 0) + ' nA' : r(RSEL[st.sel] * 1e6, 1) + ' µA') + (RSEL[st.sel] === 0 ? '  (dark)' : ''), w * 0.04, h * 0.1, '#9fe0b8', fs * 1.1);
      Kt.text(x, c ? 'v² = ' + r(c.v2 * 1e6, 3) + ' mV²' : 'v² = —', w * 0.04, h * 0.27, '#ffe45e', fs * 1.9);
      Kt.text(x, c ? 'rms ' + r(Math.sqrt(c.v2) * 1e3, 2) + ' mV' : '', w * 0.96, h * 0.27, '#9fe0b8', fs * 1.2, 'right');
    } else if (MODE === 'psd') {
      ch = Kt.chart(x, { x: w * 0.1, y: h * 0.12, w: w * 0.86, h: h * 0.6 }, { xr: [p.fs / p.N, p.fs / 2], yr: [Math.sqrt(KN.sw(p)) * 1e9 * 0.4, Math.sqrt(KN.spec(p, p.fs / p.N)) * 1e9 * 2.2], xlog: true, ylog: true, xlabel: 'frequency (Hz, log)', ylabel: 'voltage noise (nV/√Hz, log)' });
      if (st.sp) {
        Kt.poly(x, ch, st.sp.map(function (q) { return [q[0], Math.sqrt(Math.max(q[1], 1e-30)) * 1e9]; }), '#ffe45e', 1.4);
        if (st.ab) Kt.poly(x, ch, st.sp.map(function (q) { return [q[0], Math.sqrt(Math.max(st.ab[0] + st.ab[1] / q[0], 1e-30)) * 1e9]; }), '#64e3ff', 2.4);
      }
      Kt.text(x, st.sp ? st.nseg + ' averages' + (st.ab ? '   floor ' + r(Math.sqrt(st.ab[0]) * 1e9, 2) + ' nV/√Hz   corner ' + r(st.ab[1] / st.ab[0], 0) + ' Hz' : '') : 'press ACQUIRE', w * 0.1, h * 0.93, '#9fe0b8', fs);
    } else {
      var tmax = 8 * p.tau;
      ch = Kt.chart(x, { x: w * 0.08, y: h * 0.1, w: w * 0.88, h: h * 0.52 }, { xr: [0, tmax * 1e6], yr: [-0.8, 1.4], xlabel: 'time after the trigger (µs)', ylabel: 'photodiode (V)' });
      var one = [], avg = [], nn = 160, tt, sg = KN.sigma1(p) * 0.35;
      for (i = 0; i < nn; i++) { tt = tmax * i / (nn - 1); var sv = p.A * Math.exp(-tt / p.tau); one.push([tt * 1e6, sv + sg * DEC[(i * 3) % 600]]); avg.push([tt * 1e6, sv]); }
      Kt.poly(x, ch, one, '#7a8a2e', 1.2); Kt.poly(x, ch, avg, '#ffe45e', 2.2);
      var g0 = st.gdel * 1e6, g1 = (st.gdel + p.w) * 1e6; x.fillStyle = 'rgba(100,227,255,.28)'; x.fillRect(ch.X(g0), h * 0.1, Math.max(2, ch.X(g1) - ch.X(g0)), h * 0.52);
      Kt.text(x, 'gate ' + r(st.gdel * 1e6, 2) + ' µs  width ' + r(p.w * 1e6, 2) + ' µs   averages ' + st.N, w * 0.04, h * 0.74, '#9fe0b8', fs);
      Kt.text(x, c ? 'OUTPUT ' + r(c.v, 4) + ' V' + (c.sd !== undefined ? '   scatter ' + r(c.sd, 4) + ' V   SNR ' + r(c.snr, 1) : '') : 'OUTPUT —', w * 0.04, h * 0.9, '#ffe45e', fs * 1.4);
    }
    if (st.prog > 0 && st.prog < 1) { x.fillStyle = 'rgba(100,227,255,.8)'; x.fillRect(0, h - 6, w * st.prog, 6); }
  }
  function paint() { ins.screen.paint(drawScreen); }
  var panelCv = null;
  function paintPanel() { if (panelCv && panelCv.isConnected) drawScreen(panelCv.getContext('2d'), panelCv.width, panelCv.height); }
  function panel(u) { panelCv = Kt.panel(u, 0.62); paintPanel(); }

  // ================================================================ human actions
  function powerOn(on) {
    if (Kt.busy()) return Promise.resolve(); if (st.on === on) return Promise.resolve();
    return S.hand.tap(pwr, 'front').then(function () {
      st.on = on; led1.material.emissive.setHex(on ? 0x22cc44 : 0); led1.material.color.setHex(on ? 0x33dd55 : 0x331111);
      if (lampMat) { lampMat.emissive.setHex(on ? (MODE === 'boxcar' ? 0x88aa22 : 0xffaa33) : 0); }
      if (!on) st.cur = null;
      S.say(on ? 'Instrument on' + (MODE === 'lockin' ? ', chopper running at ' + p.f + ' Hz.' : '.') : 'Switched off.'); mark(); S.render();
    });
  }
  function turnKnob(kn, a0, a1, apply, ms) {
    var pt = Kt.wpt(ins.g, kn.position.x, kn.position.y, ins.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kn.rotation.z = a0 + (a1 - a0) * k; apply(k); }, { mode: 'front', ms: ms || 450, reachMs: 450 });
  }
  function setTc(v) {
    if (Kt.busy()) return Promise.resolve(); var a0 = ins.knobs[0].rotation.z, a1 = 2.2 - 1.1 * TCS.indexOf(v);
    return turnKnob(ins.knobs[0], a0, a1, function () {}).then(function () { st.tc = v; ins.knobs[0].rotation.z = a1; st.cur = null; mark(); S.render(); });
  }
  function setPhase(v) {
    if (!isFinite(v) || v < 0 || v > 360) { S.say('The reference phase goes from 0 to 360 degrees.'); return Promise.resolve(); }
    if (Kt.busy()) return Promise.resolve(); var a0 = ins.knobs[1].rotation.z, a1 = 2.2 - 4.4 * v / 360;
    return turnKnob(ins.knobs[1], a0, a1, function () {}).then(function () { st.phr = v; ins.knobs[1].rotation.z = a1; st.cur = null; mark(); S.render(); });
  }
  function setNseg(v) {
    var list = MODE === 'psd' ? SEGS : NS; if (list.indexOf(v) < 0) return Promise.resolve();
    if (Kt.busy()) return Promise.resolve(); var a0 = ins.knobs[0].rotation.z, a1 = 2.2 - 4.4 * list.indexOf(v) / (list.length - 1);
    return turnKnob(ins.knobs[0], a0, a1, function () {}).then(function () { if (MODE === 'psd') st.nseg = v; else st.N = v; ins.knobs[0].rotation.z = a1; mark(); S.render(); });
  }
  function selectR(i) {
    if (!selKnob || i < 0 || i >= RSEL.length) return Promise.resolve(); if (Kt.busy()) return Promise.resolve();
    var a0 = selKnob.rotation.z, ang = -(i * (MODE === 'johnson' ? 0.67 : 0.7)), pt = Kt.wpt(dut, selKnob.position.x, selKnob.position.y, 0.074);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { selKnob.rotation.z = a0 + (ang - a0) * k; }, { mode: 'front', ms: 450, reachMs: 450 }).then(function () { st.sel = i; selKnob.rotation.z = ang; st.cur = null; mark(); S.render(); });
  }
  function lower(on) {                                                       // the resistor can into / out of the liquid nitrogen
    if (!dewarCan || Kt.busy() || st.cold === on) return Promise.resolve();
    var y0 = dewarCan.position.y, y1 = on ? 0.115 : canY0, pt = Kt.wpt(dut, 0.19, 0.3, -0.01);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { dewarCan.position.y = y0 + (y1 - y0) * k; }, { mode: 'top', ms: 900, reachMs: 600 }).then(function () {
      st.cold = on; dewarCan.position.y = y1; st.cur = null;
      S.say(on ? 'The resistor can is in the liquid nitrogen: about ' + TCOLD + ' K. Wait for it to cool before reading (the noise follows the resistor, not the room).' : 'Resistors back at room temperature.'); mark(); S.render();
    });
  }
  function integrate(ms, fn) { return S.tween(ms, function (k) { st.prog = k; if (k >= 1) st.prog = 0; mark(); }).then(function () { st.prog = 0; return fn(); }); }
  function needOn() { if (!st.on) { S.say('Switch the instrument on first.'); return true; } return false; }
  // ---- one reading per kind
  function readLockinX() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return integrate(700, function () { var xy = KN.read(p, st.tc, st.phr, st.idx++); st.cur = { k: 'X', X: xy[0], tc: st.tc, phr: st.phr }; S.say('X = ' + r(xy[0] * 1e6, 2) + ' µV at reference phase ' + st.phr + '°.'); mark(); S.render(); return st.cur; });
  }
  function readLockinXY() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return integrate(900, function () {
      var n = 5, Rs_ = [], Xs = [], Ys = [], j, xy;
      for (j = 0; j < n; j++) { xy = KN.read(p, st.tc, st.phr, st.idx++); Xs.push(xy[0]); Ys.push(xy[1]); Rs_.push(Math.sqrt(xy[0] * xy[0] + xy[1] * xy[1])); }
      var mx = S.fit.mean(Xs), my = S.fit.mean(Ys), mr = S.fit.mean(Rs_), sd = 0;
      for (j = 0; j < n; j++) sd += (Rs_[j] - mr) * (Rs_[j] - mr); sd = Math.sqrt(sd / (n - 1));
      st.cur = { k: 'XY', tc: st.tc, phr: st.phr, X: mx, Y: my, R: mr, th: Math.atan2(my, mx) * 180 / Math.PI + st.phr, sd: sd, snr: sd > 0 ? mr / sd : 0 };
      S.say('R = ' + r(mr * 1e6, 2) + ' µV, θ = ' + r(st.cur.th, 1) + '° (mean of 5 readings, scatter ' + r(sd * 1e6, 2) + ' µV).'); mark(); S.render(); return st.cur;
    });
  }
  function readMeter() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    var q = MODE === 'johnson' ? assign(p, { T: st.cold ? TCOLD : p.T }) : p, v = RSEL[st.sel];
    return integrate(800, function () {
      var v2 = MODE === 'johnson' ? KN.msq(q, v, st.idx++) : KN.msq(q, v, st.idx++);
      st.cur = MODE === 'johnson' ? { T: q.T, R: v, v2: v2, cold: st.cold } : { I: v, v2: v2 };
      S.say('Mean-square output ' + r(v2 * 1e6, 3) + ' mV² (rms ' + r(Math.sqrt(v2) * 1e3, 2) + ' mV).'); mark(); S.render(); return st.cur;
    });
  }
  function acquire() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return integrate(900 + st.nseg * 4, function () { st.sp = KN.spectrum(p, st.nseg); st.ab = null; st.cur = { nseg: st.nseg }; S.say(st.nseg + ' spectra averaged.'); mark(); S.render(); return st.cur; });
  }
  function fitNow() {
    if (!st.sp) { S.say('Acquire a spectrum first.'); return null; } st.ab = KN.fit(st.sp);
    st.cur = { nseg: st.nseg, floor: st.ab[0], fc: st.ab[0] > 0 ? st.ab[1] / st.ab[0] : 0 };
    S.say('Fit P = a + b/f: floor ' + r(Math.sqrt(st.ab[0]) * 1e9, 2) + ' nV/√Hz, corner ' + r(st.cur.fc, 0) + ' Hz.'); mark(); S.render(); return st.cur;
  }
  function boxSnr() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return integrate(800, function () {
      var g = Kt.rnd(p.seed + 1000 * st.N + 7 * st.idx++), vals = [], j, m, sd = 0, n = 40;
      for (j = 0; j < n; j++) vals.push(KN.output(p, 0, st.N, g));
      m = S.fit.mean(vals); for (j = 0; j < n; j++) sd += (vals[j] - m) * (vals[j] - m); sd = Math.sqrt(sd / (n - 1));
      st.cur = { k: 'snr', N: st.N, v: m, sd: sd, snr: m / sd }; S.say('Averaging ' + st.N + ' shots: output ' + r(m, 4) + ' V, scatter ' + r(sd, 4) + ' V, SNR ' + r(m / sd, 1) + '.'); mark(); S.render(); return st.cur;
    });
  }
  function setGate(td) {
    if (!isFinite(td) || td < 0 || td > 3 * p.tau) { S.say('Set the gate delay between 0 and ' + r(3 * p.tau * 1e6, 1) + ' µs.'); return; } st.gdel = td; st.cur = null; mark();
  }
  function boxDelay() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return integrate(700, function () {
      var g = Kt.rnd(p.seed + 5 * st.idx++ + 31), v = KN.output(p, st.gdel, Math.floor(p.nav), g);
      st.cur = { k: 'td', td: st.gdel, v: v }; S.say('Gate at ' + r(st.gdel * 1e6, 2) + ' µs: output ' + r(v, 4) + ' V.'); mark(); S.render(); return st.cur;
    });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var c = st.cur; if (!c) { S.say('Take a reading first.'); return false; }
    var row = assign(c, {});
    if (MODE === 'lockin' && c.k === 'X' && S.rows.some(function (q) { return q.k === 'X' && q.phr === c.phr && q.tc === c.tc; })) { S.say('A reading at this phase is already in the book. Turn the reference to another phase.'); return false; }
    if (MODE === 'lockin' && c.k === 'XY' && S.rows.some(function (q) { return q.k === 'XY' && q.tc === c.tc; })) { S.say('A reading at this time constant is already in the book.'); return false; }
    if (MODE === 'johnson' && S.rows.some(function (q) { return q.R === c.R && q.cold === c.cold; })) { S.say('That resistor is already in the book at this temperature.'); return false; }
    if (MODE === 'shot' && S.rows.some(function (q) { return q.I === c.I; })) { S.say('That current is already in the book.'); return false; }
    if (MODE === 'psd') { if (!c.floor) { S.say('Fit the spectrum first.'); return false; } if (S.rows.some(function (q) { return q.nseg === c.nseg; })) { S.say('A fit with ' + c.nseg + ' averages is already in the book.'); return false; } }
    if (MODE === 'boxcar' && c.k === 'snr' && S.rows.some(function (q) { return q.k === 'snr' && q.N === c.N; })) { S.say('That number of averages is already in the book.'); return false; }
    if (MODE === 'boxcar' && c.k === 'td' && S.rows.some(function (q) { return q.k === 'td' && Math.abs(q.td - c.td) < 1e-12; })) { S.say('That delay is already in the book.'); return false; }
    S.addRow(row); st.cur = null; mark(); S.render(); return true;
  }

  // ================================================================ analysis of the book
  function singleAmp(rows) {
    var xr = rows.filter(function (q) { return q.k === 'X'; }), sc = 0, ss = 0, cc = 0, a = 0, b = 0, i, d, ph;
    if (xr.length < 4) return null;
    for (i = 0; i < xr.length; i++) { ph = xr[i].phr * Math.PI / 180; cc += Math.cos(ph) * Math.cos(ph); sc += Math.cos(ph) * Math.sin(ph); ss += Math.sin(ph) * Math.sin(ph); a += xr[i].X * Math.cos(ph); b += xr[i].X * Math.sin(ph); }
    d = cc * ss - sc * sc; if (Math.abs(d) < 1e-9) return null;
    var A = (a * ss - b * sc) / d, B = (b * cc - a * sc) / d; return { R: Math.sqrt(A * A + B * B), th: -Math.atan2(B, A) * 180 / Math.PI };
  }
  function slopeOf(rows, xk, sel) {
    var rs = rows.filter(sel), xs = rs.map(function (q) { return q[xk]; }), ys = rs.map(function (q) { return q.v2; }), f = S.fit.linear(xs.map(function (x, i) { return [x, ys[i]]; }));
    return f; }
  function result(rows) {
    var i;
    if (MODE === 'lockin') {
      var xy = rows.filter(function (q) { return q.k === 'XY'; }).sort(function (a, b) { return a.tc - b.tc; }); if (!xy.length) return null;
      var best = xy[xy.length - 1], sa = singleAmp(rows);
      return { label: 'Signal amplitude (peak)', value: best.R * 1e6, unit: 'µV', digits: 2, truth: p.A * 1e6,
        note: 'Dual phase at ' + best.tc + ' s: R = ' + r(best.R * 1e6, 2) + ' µV, phase ' + r(best.th, 1) + '° (true phase ' + p.phi + '°). ' + (sa ? 'The single-phase scan gives ' + r(sa.R * 1e6, 2) + ' µV at ' + r(sa.th, 1) + '°. ' : '')
          + 'Longer time constants give a smaller scatter: SNR ' + xy.map(function (q) { return q.tc + ' s → ' + r(q.snr, 0); }).join(', ') + '.' };
    }
    if (MODE === 'johnson') {
      var warm = rows.filter(function (q) { return !q.cold; }); if (warm.length < 6) return null;
      var f = slopeOf(rows, 'R', function (q) { return !q.cold; }); if (!f) return null;
      var kb = f.m / (4 * p.T * p.df * p.G * p.G), cold = rows.filter(function (q) { return q.cold; }), note = 'Slope of v² against R at ' + p.T + ' K gives 4 kB T Δf G²; the intercept is the amplifier\'s own noise (' + r(Math.sqrt(Math.max(f.c, 0) / (p.G * p.G * p.df)) * 1e9, 2) + ' nV/√Hz).';
      if (cold.length >= 2) { var sh = cold.filter(function (q) { return q.R === 0; })[0], hi = cold.filter(function (q) { return q.R > 0; })[0], w0 = warm.filter(function (q) { return q.R === 0; })[0], w1 = warm.filter(function (q) { return hi && q.R === hi.R; })[0];
        if (sh && hi && w0 && w1) note += ' At ' + TCOLD + ' K the resistor\'s noise is ' + r((hi.v2 - sh.v2) / (w1.v2 - w0.v2), 3) + ' of its room-temperature value (T ratio ' + r(TCOLD / p.T, 3) + ').'; }
      return { label: 'Boltzmann constant', value: kb * 1e23, unit: '× 10⁻²³ J/K', digits: 3, truth: 1.380649, note: note };
    }
    if (MODE === 'shot') {
      if (rows.length < 6) return null; var g = slopeOf(rows, 'I', function () { return true; }); if (!g) return null;
      var qq = g.m / (2 * p.Rf * p.Rf * p.df);
      return { label: 'Electron charge', value: qq * 1e19, unit: '× 10⁻¹⁹ C', digits: 3, truth: 1.602176634,
        note: 'Slope of v² against the photocurrent gives 2 q Rf² Δf. The intercept is the feedback resistor\'s own Johnson noise (4 kB T Rf Δf = ' + r(g.c * 1e6, 3) + ' mV² here).' };
    }
    if (MODE === 'psd') {
      if (!rows.length) return null; var bst = rows.slice().sort(function (a, b) { return a.nseg - b.nseg; })[rows.length - 1];
      return { label: 'White noise floor', value: Math.sqrt(bst.floor) * 1e9, unit: 'nV/√Hz', digits: 2, truth: Math.sqrt(KN.sw(p)) * 1e9,
        note: 'From the fit with ' + bst.nseg + ' averages: the 1/f corner is at ' + r(bst.fc, 0) + ' Hz (true ' + p.fc + ' Hz). With more averages the spectrum is smoother and both numbers settle.' };
    }
    var tds = rows.filter(function (q) { return q.k === 'td'; }); if (tds.length < 6) return null;
    var fl = S.fit.linear(tds.filter(function (q) { return q.v > 0; }).map(function (q) { return [q.td, Math.log(q.v)]; })); if (!fl || fl.m >= 0) return null;
    var sn = rows.filter(function (q) { return q.k === 'snr'; }), nt = '';
    if (sn.length >= 3) { var fs_ = S.fit.linear(sn.map(function (q) { return [Math.log(q.N), Math.log(q.snr)]; })); nt = ' SNR grows as N^' + r(fs_.m, 2) + ' (the square-root law says 0.5).'; }
    return { label: 'Decay time', value: -1 / fl.m * 1e6, unit: 'µs', digits: 3, truth: p.tau * 1e6, note: 'ln(output) against gate delay is a straight line of slope −1/τ, whatever the gate width.' + nt };
  }

  // ================================================================ text
  var TXT = {
    lockin: { principle: 'A lock-in amplifier multiplies the input by a reference at the signal\'s own frequency and averages the product. A signal at that frequency gives a steady output; noise at every other frequency averages away. Only the frequencies within about 1/(4 τ) of the reference survive, so a longer time constant τ means a narrower band and less noise.',
      formula: 'X = A cos(φ − φᵣ),  Y = A sin(φ − φᵣ),  R = √(X² + Y²) = A', note: 'the amplitude comes out whatever the signal phase; the noise on a reading falls as 1/√τ',
      more: ['Single phase: the instrument shows only X. Turn the reference phase and X follows a cosine of the reference phase; the peak of that cosine is the amplitude.', 'Dual phase: two mixers 90° apart give X and Y together, so R and the phase θ are read at once, with no turning.', 'Each reading is the display averaged over the last four time constants after eight time constants of settling.'] },
    johnson: { principle: 'Charge carriers in a resistor jiggle with thermal energy, so a resistor at temperature T has a fluctuating voltage across it even with no current. Its mean square, in a bandwidth Δf, is 4 kB T R Δf. Measure it for several R and the slope of v² against R gives kB.',
      formula: 'v² = 4 kB T R Δf', note: 'the amplifier adds noise of its own: the intercept of the line, which you measure with the input shorted',
      more: ['The amplifier gain G multiplies the voltage, so the meter reads G² times the noise voltage squared.', 'Noise power is proportional to T: dipping the resistors in liquid nitrogen (77 K) cuts the resistor\'s part to about a quarter.', 'Noise readings carry their own statistical scatter: averaging more samples narrows it.'] },
    shot: { principle: 'A current is a stream of separate charges q arriving at random, so it fluctuates. In a bandwidth Δf the mean-square current fluctuation is 2 q I Δf. Measuring this for several currents gives the charge of the carrier.',
      formula: 'i² = 2 q I Δf', note: 'the feedback resistor also makes Johnson noise: it is the intercept at zero current',
      more: ['The transimpedance amplifier turns the current into a voltage Rf I, so the meter reads Rf² times the current noise.', 'Shot noise needs a DC current: at I = 0 only the resistor\'s noise is left.', 'The result is the charge of the carrier that carries the current, here the electron.'] },
    psd: { principle: 'A spectrum analyser splits a noise signal into frequencies and shows the power in each hertz. A resistor and an amplifier give a flat (white) floor, 4 kB T R + eₙ², with an extra 1/f rise at low frequency that meets the floor at the corner frequency fc.',
      formula: 'S(f) = S_w (1 + f_c / f)', note: 'S_w is the white floor; at f = f_c the 1/f part equals the floor',
      more: ['One spectrum of a random signal scatters wildly; averaging N of them narrows the scatter by √N.', 'The fit uses weights because the scatter of each point is proportional to the point itself.', 'A Hann window is applied to each record so the strong low frequencies do not leak into the high ones.'] },
    boxcar: { principle: 'A boxcar averager opens a short gate at a chosen delay after each trigger, averages the signal inside it, and averages that over many shots. The pulse repeats exactly, the noise does not, so the signal adds up N times and the noise only √N times: the signal-to-noise ratio grows as √N.',
      formula: 'SNR ∝ √N,   output ∝ exp(−t_d / τ)', note: 'stepping the gate along the pulse maps out its decay; the slope of ln(output) is −1/τ',
      more: ['The gate width does not change the decay time, only the size of the output and its noise.', 'Averaging N shots at the same gate gives N-fold the signal and √N-fold the noise.'] } };
  var BOOK = {
    lockin: { cols: [{ label: 'Mode', get: function (z) { return z.k === 'X' ? 'single' : 'dual'; } }, { label: 'τ (s)', get: function (z) { return z.tc; } }, { label: 'φref', get: function (z) { return z.phr + '°'; } },
      { label: 'X (µV)', get: function (z) { return r(z.X * 1e6, 2); } }, { label: 'Y (µV)', get: function (z) { return z.k === 'XY' ? r(z.Y * 1e6, 2) : '—'; } }, { label: 'R (µV)', get: function (z) { return z.k === 'XY' ? r(z.R * 1e6, 2) : '—'; } }] },
    johnson: { cols: [{ label: 'T (K)', get: function (z) { return z.T; } }, { label: 'R', get: function (z) { return z.R === 0 ? 'short' : si(z.R, 'Ω', 2); } }, { label: 'v² (mV²)', get: function (z) { return r(z.v2 * 1e6, 3); } }, { label: 'rms (mV)', get: function (z) { return r(Math.sqrt(z.v2) * 1e3, 2); } }] },
    shot: { cols: [{ label: 'I', get: function (z) { return si(z.I, 'A', 2); } }, { label: 'v² (mV²)', get: function (z) { return r(z.v2 * 1e6, 3); } }, { label: 'rms (mV)', get: function (z) { return r(Math.sqrt(z.v2) * 1e3, 2); } }] },
    psd: { cols: [{ label: 'Averages', get: function (z) { return z.nseg; } }, { label: 'Floor (nV/√Hz)', get: function (z) { return r(Math.sqrt(z.floor) * 1e9, 2); } }, { label: 'Corner (Hz)', get: function (z) { return r(z.fc, 0); } }] },
    boxcar: { cols: [{ label: 'Set', get: function (z) { return z.k === 'snr' ? 'N = ' + z.N : 'td ' + r(z.td * 1e6, 2) + ' µs'; } }, { label: 'Output (V)', get: function (z) { return r(z.v, 4); } }, { label: 'Scatter (V)', get: function (z) { return z.k === 'snr' ? r(z.sd, 4) : '—'; } }, { label: 'SNR', get: function (z) { return z.k === 'snr' ? r(z.snr, 1) : '—'; } }] } };
  var VIVA = {
    lockin: [['Why does a longer time constant give a cleaner reading?', ['It narrows the band of noise that gets through', 'It makes the signal larger', 'It raises the chopper frequency'], 0, 'The detection band is about 1/(4τ).'], ['The lock-in shows X = 0 and Y = A. The signal phase relative to the reference is', ['90°', '0°', '180°'], 0, 'X = A cos Δ and Y = A sin Δ.'], ['What does R = √(X² + Y²) not depend on?', ['The phase of the signal', 'The amplitude', 'The noise'], 0, 'Rotating X and Y into each other leaves R unchanged.']],
    johnson: [['Cooling the resistor from 300 K to 77 K changes its noise power by a factor of about', ['0.26', '4', '0.5'], 0, 'v² is proportional to T: 77/300.'], ['What does the intercept of the line v² against R measure?', ['The noise of the amplifier', 'The temperature', 'The bandwidth'], 0, 'With the input shorted only the amplifier\'s noise is left.'], ['Why is the noise measured in a stated bandwidth?', ['Noise power is proportional to the bandwidth', 'The meter is slow', 'The resistor changes with frequency'], 0, 'v² = 4 kB T R Δf.']],
    shot: [['Doubling the current makes the shot-noise power', ['Double', 'Four times', 'Unchanged'], 0, 'i² = 2 q I Δf is proportional to I.'], ['Why is the noise at zero current not zero?', ['The feedback resistor still makes Johnson noise', 'The LED leaks', 'The meter is faulty'], 0, 'It is the intercept of the line.'], ['What does the slope of v² against I give?', ['The charge of the carrier', 'The resistance', 'The temperature'], 0, 'slope = 2 q Rf² Δf.']],
    psd: [['What is the corner frequency?', ['Where the 1/f part equals the white floor', 'Where the noise stops', 'The sampling frequency'], 0, 'S(f_c) = 2 S_w.'], ['Averaging 64 spectra instead of 4 makes the scatter of each point', ['Four times smaller', 'Sixteen times smaller', 'The same'], 0, 'It falls as 1/√N.'], ['The white floor of a resistor in front of an amplifier is', ['4 kB T R + eₙ²', '4 kB T / R', 'kB T'], 0, 'The resistor\'s Johnson noise plus the amplifier\'s own.']],
    boxcar: [['Averaging 100 pulses instead of 1 improves the signal-to-noise ratio by', ['10', '100', '1'], 0, 'SNR grows as √N.'], ['Why does the gate width not change the measured decay time?', ['The log of the output stays a line of the same slope', 'The gate is too short', 'The pulse is always the same'], 0, 'ln(output) = const − t_d/τ.'], ['What must the pulse do for boxcar averaging to work?', ['Repeat identically while the noise does not', 'Be very large', 'Be a sine wave'], 0, 'Only a repeating signal adds coherently.']] };
  var MINR = { lockin: 'Read X at six or more reference phases, then take a dual-phase reading at each time constant.', johnson: 'Read all eight positions of the switch at room temperature, then two at 77 K.', shot: 'Read at least six currents, including the dark one.', psd: 'Acquire with 4, 16, 64 and 256 averages and fit each.', boxcar: 'Take the SNR at five numbers of averages, then step the gate along the pulse.' };

  // ================================================================ steps
  var STEPS = [{ id: 'on', title: 'Switch on', view: 'ins', render: function (u) {
      u.h2('Switch the instrument on');
      u.p(({ lockin: 'The lamp shines through the chopper onto the photodiode. The pre-amp feeds the lock-in.', johnson: 'The resistor decade is wired to the low-noise amplifier and the true-rms voltmeter. Everything is screened.', shot: 'The LED lights the photodiode through a light-tight tube; the transimpedance amplifier turns its current into a voltage.',
        psd: 'The test board is connected to the amplifier and the spectrum analyser.', boxcar: 'The pulse generator flashes the LED; the photodiode and pre-amp feed the boxcar averager.' })[MODE]);
      u.task('Power', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('ins'); powerOn(!st.on); }, !st.on, S.hand.busy));
      u.note(MODE === 'johnson' ? 'Liquid nitrogen is very cold: the lab uses gloves and goggles, and the can is lowered on its rod, never held in the hand.' : 'Mains-powered instruments: keep leads away from the power cable and leave the screened box closed.');
      u.next('Next', st.on); }, ok: function () { return st.on; }, auto: function () { return powerOn(true); } }];
  function phaseOf(i) { return 60 * i; }
  function btns(u, vals, label, act, sel, per) { for (var i = 0; i < vals.length; i += per) u.row.apply(u, vals.slice(i, i + per).map(function (v, j) { return u.button(label(v, i + j), function () { S.focus(MODE === 'johnson' || MODE === 'shot' ? 'dut' : 'ins'); act(v, i + j); }, sel(v, i + j), S.hand.busy); })); }
  if (MODE === 'lockin') {
    STEPS.push({ id: 'single', title: 'Single phase', view: 'ins', render: function (u) {
        u.h2('Single-phase detection: turn the reference');
        u.p('With one mixer the lock-in shows only X. Set the time constant to 1 s, turn the reference phase in steps, and write X down at six or more different phases. X follows A cos(φ − φᵣ): its peak is the amplitude.');
        u.slider('Reference phase', 0, 360, 15, function () { return st.phr; }, function (v) { setPhase(v); }, '°', 0);
        u.row(u.button('Time constant 1 s', function () { S.focus('ins'); setTc(1); }, false, S.hand.busy || st.tc === 1), u.button('Read X', function () { S.focus('ins'); readLockinX(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        u.live(function () { return 'τ = ' + st.tc + ' s · φ = ' + st.phr + '° · ' + (st.cur && st.cur.k === 'X' ? 'X = ' + r(st.cur.X * 1e6, 2) + ' µV' : 'no reading'); });
        panel(u); u.h3('Observation table'); u.table();
        var nx = S.rows.filter(function (q) { return q.k === 'X'; }).length; if (nx < 6) u.p(nx + ' of at least 6 readings.');
        u.next('Next: dual phase', nx >= 6); },
      ok: function () { return S.rows.filter(function (q) { return q.k === 'X'; }).length >= 6; },
      auto: function () { var c = setTc(1), j; for (j = 0; j < 6; j++) (function (jj) { c = c.then(function () { return setPhase(phaseOf(jj)); }).then(function () { return readLockinX(); }).then(function () { record(); }); })(j); return c; } });
    STEPS.push({ id: 'dual', title: 'Dual phase', view: 'ins', render: function (u) {
        u.h2('Dual-phase detection: X, Y, R and θ together');
        u.p('Set the reference phase back to 0°. A dual-phase reading takes five displays and gives X, Y, R and the signal phase. Do it at each of the four time constants and see how the scatter falls.');
        btns(u, TCS, function (v) { return 'τ = ' + v + ' s'; }, function (v) { setTc(v); }, function (v) { return st.tc === v; }, 2);
        u.row(u.button('Phase to 0°', function () { setPhase(0); }, false, S.hand.busy || st.phr === 0), u.button('Read X, Y, R, θ', function () { S.focus('ins'); readLockinXY(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        u.live(function () { return 'τ = ' + st.tc + ' s · φ = ' + st.phr + '° · ' + (st.cur && st.cur.k === 'XY' ? 'R = ' + r(st.cur.R * 1e6, 2) + ' µV, θ = ' + r(st.cur.th, 1) + '°' : 'no reading'); });
        panel(u); u.h3('Observation table'); u.table();
        var nd = S.rows.filter(function (q) { return q.k === 'XY'; }).length; u.next('Next: result', nd >= 4); },
      ok: function () { return S.rows.filter(function (q) { return q.k === 'XY'; }).length >= 4; },
      auto: function () { var c = setPhase(0), j; for (j = 0; j < TCS.length; j++) (function (jj) { c = c.then(function () { return setTc(TCS[jj]); }).then(function () { return readLockinXY(); }).then(function () { record(); }); })(j); return c; } });
  } else if (MODE === 'johnson') {
    STEPS.push({ id: 'warm', title: 'Room temperature', view: 'dut', render: function (u) {
        u.h2('Noise of each resistor at ' + p.T + ' K');
        u.p('Turn the switch to each position (the first is a short), press MEASURE and write the mean-square output down. At least eight readings.');
        btns(u, RSEL, function (v) { return v === 0 ? 'short' : si(v, 'Ω', 1); }, function (v, i) { selectR(i); }, function (v, i) { return st.sel === i; }, 4);
        u.row(u.button('MEASURE', function () { S.focus('ins'); readMeter(); }, true, S.hand.busy || st.cold), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        u.live(function () { return 'T = ' + (st.cold ? TCOLD : p.T) + ' K · ' + ohm(RSEL[st.sel]) + ' · ' + (st.cur ? 'v² = ' + r(st.cur.v2 * 1e6, 3) + ' mV²' : 'no reading'); });
        panel(u); u.h3('Observation table'); u.table();
        var nw = S.rows.filter(function (q) { return !q.cold; }).length; if (nw < 8) u.p(nw + ' of 8 readings.');
        u.next('Next: cool the resistors', nw >= 8); },
      ok: function () { return S.rows.filter(function (q) { return !q.cold; }).length >= 8; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < RSEL.length; j++) (function (jj) { c = c.then(function () { return selectR(jj); }).then(function () { return readMeter(); }).then(function () { record(); }); })(j); return c; } });
    STEPS.push({ id: 'cold', title: 'Liquid nitrogen', view: 'dut', render: function (u) {
        u.h2('The same resistors at 77 K');
        u.p('Lower the can of resistors into the liquid nitrogen on its rod. Read the short and the largest resistor again. The resistor\'s part of the noise should fall in proportion to the temperature.');
        u.task('Can in the nitrogen', st.cold, st.cold ? 'About ' + TCOLD + ' K' : 'At room temperature').add(u.button(st.cold ? 'Lift it out' : 'Lower the can', function () { S.focus('dut'); lower(!st.cold); }, !st.cold, S.hand.busy));
        u.row(u.button('Short', function () { selectR(0); }, st.sel === 0, S.hand.busy), u.button(si(RSEL[7], 'Ω', 1), function () { selectR(7); }, st.sel === 7, S.hand.busy), u.button('MEASURE', function () { S.focus('ins'); readMeter(); }, true, S.hand.busy || !st.cold), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table();
        var nc = S.rows.filter(function (q) { return q.cold; }).length; u.next('Next: result', nc >= 2); },
      ok: function () { return S.rows.filter(function (q) { return q.cold; }).length >= 2; },
      auto: function () { return lower(true).then(function () { return selectR(0); }).then(function () { return readMeter(); }).then(function () { record(); }).then(function () { return selectR(7); }).then(function () { return readMeter(); }).then(function () { record(); }); } });
  } else if (MODE === 'shot') {
    STEPS.push({ id: 'cur', title: 'Noise against current', view: 'dut', render: function (u) {
        u.h2('Noise against photocurrent');
        u.p('Set the LED current with the knob (the first position is dark), press MEASURE and write the mean-square output down. At least six currents.');
        btns(u, RSEL, function (v) { return v === 0 ? 'dark' : si(v, 'A', 1); }, function (v, i) { selectR(i); }, function (v, i) { return st.sel === i; }, 4);
        u.row(u.button('MEASURE', function () { S.focus('ins'); readMeter(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        u.live(function () { return (RSEL[st.sel] === 0 ? 'dark' : si(RSEL[st.sel], 'A', 2)) + ' · ' + (st.cur ? 'v² = ' + r(st.cur.v2 * 1e6, 3) + ' mV²' : 'no reading'); });
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.length >= 6); },
      ok: function () { return S.rows.length >= 6; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < RSEL.length; j++) (function (jj) { c = c.then(function () { return selectR(jj); }).then(function () { return readMeter(); }).then(function () { record(); }); })(j); return c; } });
  } else if (MODE === 'psd') {
    STEPS.push({ id: 'spec', title: 'Acquire and fit', view: 'ins', render: function (u) {
        u.h2('Spectrum with 4, 16, 64 and 256 averages');
        u.p('Choose the number of averages, press ACQUIRE, then fit the spectrum with the white floor plus 1/f. Write the floor and the corner down. Do it for all four numbers and watch the scatter fall.');
        btns(u, SEGS, function (v) { return v + ' averages'; }, function (v) { setNseg(v); }, function (v) { return st.nseg === v; }, 4);
        u.row(u.button('ACQUIRE', function () { S.focus('ins'); acquire(); }, true, S.hand.busy), u.button('Fit floor + 1/f', function () { fitNow(); }, false, !st.sp || S.hand.busy), u.button('Write it down', function () { record(); }, false, !(st.cur && st.cur.floor) || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.length >= 4); },
      ok: function () { return S.rows.length >= 4; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < SEGS.length; j++) (function (jj) { c = c.then(function () { return setNseg(SEGS[jj]); }).then(function () { return acquire(); }).then(function () { fitNow(); record(); }); })(j); return c; } });
  } else {
    STEPS.push({ id: 'snr', title: 'SNR against averages', view: 'ins', render: function (u) {
        u.h2('Signal-to-noise ratio against the number of shots averaged');
        u.p('Put the gate at the start of the pulse (delay 0). For each number of averages the instrument repeats the measurement 40 times; the mean over the scatter is the SNR. Write down five values of N.');
        btns(u, NS, function (v) { return 'N = ' + v; }, function (v) { setNseg(v); }, function (v) { return st.N === v; }, 3);
        u.row(u.button('Measure', function () { S.focus('ins'); setGate(0); boxSnr(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table();
        var ns_ = S.rows.filter(function (q) { return q.k === 'snr'; }).length; u.next('Next: map the pulse', ns_ >= 5); },
      ok: function () { return S.rows.filter(function (q) { return q.k === 'snr'; }).length >= 5; },
      auto: function () { var c = Promise.resolve(), j; setGate(0); for (j = 0; j < NS.length; j++) (function (jj) { c = c.then(function () { return setNseg(NS[jj]); }).then(function () { return boxSnr(); }).then(function () { record(); }); })(j); return c; } });
    STEPS.push({ id: 'decay', title: 'Map the decay', view: 'ins', render: function (u) {
        u.h2('Step the gate along the pulse');
        u.p('Use ' + Math.floor(p.nav) + ' shots per point. Move the gate in steps of ' + r(0.3 * p.tau * 1e6, 2) + ' µs from the trigger, measure and write the output down. Eight points.');
        u.slider('Gate delay', 0, 3 * p.tau * 1e6, 0.1 * p.tau * 1e6, function () { return st.gdel * 1e6; }, function (v) { setGate(v * 1e-6); }, 'µs', 2);
        u.row(u.button('Measure', function () { S.focus('ins'); boxDelay(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table();
        var nt_ = S.rows.filter(function (q) { return q.k === 'td'; }).length; u.next('Next: result', nt_ >= 8); },
      ok: function () { return S.rows.filter(function (q) { return q.k === 'td'; }).length >= 8; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < 8; j++) (function (jj) { c = c.then(function () { setGate(0.3 * p.tau * jj); return boxDelay(); }).then(function () { record(); }); })(j); return c; } });
  }

  function askState() {
    var q = { experiment: S.lab.title, sample: V_.sample || '', method: V_.method || '', power_on: st.on, readings: S.rows.length };
    if (MODE === 'lockin') { q.time_constant_s = st.tc; q.reference_phase_deg = st.phr; q.chopper_frequency_Hz = p.f; }
    if (MODE === 'johnson') { q.temperature_K = st.cold ? TCOLD : p.T; q.resistor = ohm(RSEL[st.sel]); q.bandwidth_Hz = p.df; q.gain = p.G; }
    if (MODE === 'shot') { q.photocurrent = RSEL[st.sel]; q.bandwidth_Hz = p.df; q.feedback_resistor = p.Rf; }
    if (MODE === 'psd') { q.averages = st.nseg; q.sample_rate_Hz = p.fs; q.temperature_K = p.T; q.resistor_ohm = p.R; }
    if (MODE === 'boxcar') { q.gate_width_us = p.w * 1e6; q.gate_delay_us = r(st.gdel * 1e6, 2); q.averages = st.N; }
    return q;
  }
  var th = TXT[MODE];
  return {
    camera: { pos: [-0.1, 0.68, 1.22], look: [-0.1, 0.06, -0.2] },
    views: { dut: [[-0.47, 0.28, 0.2], [-0.5, 0.05, -0.26]], amp: [[-0.1, 0.2, 0.0], [-0.1, 0.03, -0.27]], ins: [[0.2, 0.37, 0.48], [0.22, 0.1, -0.24]], bench: [[-0.1, 0.68, 1.22], [-0.1, 0.06, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: th.principle, formula: th.formula, formulaNote: th.note, more: th.more, precautions: 'Keep leads short and the screened box closed; a noise measurement picks up everything near it. ' + (MODE === 'johnson' ? 'Liquid nitrogen: gloves, goggles, and a vented container.' : 'No lasers or high voltages are used in this experiment.') },
    book: { title: 'Expt. - ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 74), V_.sample ? 'Sample: ' + V_.sample.slice(0, 50) : '', MINR[MODE].slice(0, 74), 'Readings come from the instrument, not a formula.'], columns: BOOK[MODE].cols },
    graph: MODE === 'johnson' || MODE === 'shot' ? { x: function (z) { return MODE === 'johnson' ? z.R : z.I; }, y: function (z) { return z.v2 * 1e6; }, xlabel: MODE === 'johnson' ? 'R (Ω)' : 'I (A)', ylabel: 'mean-square output (mV²)',
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } } : undefined,
    result: result, tol: MODE === 'lockin' ? 0.03 : MODE === 'psd' ? 0.04 : 0.03,
    resultNote: 'The reading is a measurement on noisy data: repeat it with a longer average and it settles. The agreement is as good as the statistics allow, no better.',
    chips: ['What is the noise bandwidth?', 'How do I know my reading is good?', 'Why average more?', 'Check my readings', 'What limits this measurement?'],
    viva: VIVA[MODE], askState: askState, steps: STEPS,
    tick: function (dt) { if (spin && st.on) { spin.rotation.z += 6 * (dt || 0.016); } hudA.set(st.on ? 'On' : 'Off'); hudB.set(MODE === 'lockin' ? st.tc + ' s' : MODE === 'johnson' ? ohm(RSEL[st.sel]) + (st.cold ? ' · 77 K' : '') : MODE === 'shot' ? (RSEL[st.sel] === 0 ? 'dark' : si(RSEL[st.sel], 'A', 2)) : MODE === 'psd' ? st.nseg : st.N); hudC.set(S.rows.length + ' written');
      if (dirty) { dirty = false; paint(); paintPanel(); } },
    ready: function () { paint(); }
  };
});
