/* Prayogshala studio module: OPTICAL TWEEZERS BENCH (Ph.D. laser spectroscopy and atomic physics; MIT Junior Lab "Optical Trapping").
   An inverted microscope with a sample chamber of beads in water on a motorised stage, an ENCLOSED infrared trapping laser,
   a quadrant photodiode that tracks one trapped bead and a trap analyser with a live screen.
   Physics: the `phd_tweezers` kernel of packs/phd_optics.js - the bead's Brownian motion in the trap, an exactly stepped
   Ornstein-Uhlenbeck process drawn from the lab's own seed. The stiffness is found three ways from the record:
   equipartition (kappa = kB T / <x^2>), the corner frequency of the power spectrum (kappa = 2 pi gamma fc) and the lag
   of the bead behind a moving stage (Stokes drag, kappa = gamma v / x_d). Nothing is read back from a formula.
   SIMULATED INSTRUMENT: the trapping laser is Class 4 infrared and sealed in its interlocked box: no student touches it. */
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

HoolaStudio.define('phd-tweezers-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, Kt = phdKit(S), r = Kt.r, si = Kt.si, KB = 1.380649e-23;
  var PS = [0.4, 0.7, 1.0, 1.4], PW = PS.map(function (f) { return r(f * p.P, 2); });          // laser powers (mW): the lab's own power is the third
  var st = { on: false, lp: 2, rec: null, sp: null, fc: null, cur: null, prog: 0, idx: 0, drag: null, moving: false };
  var dirty = true;
  function mark() { dirty = true; }
  function pNow() { return assign(p, { P: PW[st.lp] }); }
  var G = 6 * Math.PI * p.eta * p.a;

  // ================================================================ the microscope
  var mic = new T.Group(); mic.position.set(-0.1, 0, -0.2); S.scene.add(mic);
  Kt.box(0.26, 0.04, 0.2, 0x2b323d, 0, 0, 0, mic);
  Kt.box(0.07, 0.24, 0.06, 0x3a3f47, -0.08, 0.04, -0.05, mic);
  Kt.box(0.2, 0.05, 0.07, 0x3a3f47, 0.0, 0.23, -0.05, mic);
  var qpd = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.05, 24), M.alu); qpd.position.set(0.05, 0.3, -0.05); mic.add(qpd);
  var qpl = S.label('QUADRANT PHOTODIODE', { w: 0.05, ratio: 0.2, color: '#1b1b1b' }); qpl.position.set(0.05, 0.3, -0.05 + 0.0225); mic.add(qpl);
  var tur = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.03, 28), M.black); tur.position.set(0.04, 0.075, 0.03); mic.add(tur);
  var obj = S.mesh(new T.CylinderGeometry(0.012, 0.016, 0.06, 24), M.chrome); obj.position.set(0.04, 0.12, 0.03); mic.add(obj);
  var ol = S.label('100× · NA 1.25 · OIL', { w: 0.03, ratio: 0.25, color: '#1b1b1b' }); ol.position.set(0.04, 0.12, 0.03 + 0.0165); mic.add(ol);
  var stage = new T.Group(); stage.position.set(0.04, 0.155, 0.03); mic.add(stage);
  var sp0 = S.mesh(new T.BoxGeometry(0.13, 0.008, 0.1), M.alu); stage.add(sp0);
  var slide = S.mesh(new T.BoxGeometry(0.076, 0.0012, 0.026), new T.MeshPhysicalMaterial({ color: 0xdfeff2, roughness: 0.05, transmission: 0.9, transparent: true, opacity: 0.7 })); slide.position.set(0, 0.0046, 0); stage.add(slide);
  var drop = S.mesh(new T.SphereGeometry(0.006, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), new T.MeshStandardMaterial({ color: 0x9bd1e8, transparent: true, opacity: 0.6, roughness: 0.1 })); drop.position.set(0, 0.005, 0); stage.add(drop);
  var tub = Kt.box(0.05, 0.03, 0.04, 0x6f8193, 0.12, 0.0, 0.0, mic);
  var sl = S.label('NANO-STAGE DRIVE', { w: 0.045, ratio: 0.16, color: '#f1efe8', bg: '#2b323d', px: 384 }); sl.position.set(0.12, 0.022, 0.0205); mic.add(sl);
  var ml = S.label('INVERTED MICROSCOPE', { w: 0.14, ratio: 0.09, color: '#e8e8ea' }); ml.position.set(0, 0.021, 0.1005); mic.add(ml);
  S.contact(0.34, 0.28, -0.1, -0.2, 0.45);
  // the sealed trapping laser
  var las = new T.Group(); las.position.set(-0.55, 0, -0.2); S.scene.add(las);
  Kt.box(0.18, 0.1, 0.12, 0x2b323d, 0, 0, 0, las);
  var lsl = S.label('TRAPPING LASER 1064 nm · CLASS 4 · ENCLOSED', { w: 0.17, ratio: 0.1, color: '#f2d02a' }); lsl.position.set(0, 0.07, 0.0607); las.add(lsl);
  var lsl2 = S.label('SIMULATED INSTRUMENT · interlocked · no student access', { w: 0.17, ratio: 0.09, color: '#f1efe8' }); lsl2.position.set(0, 0.05, 0.0607); las.add(lsl2);
  var lled = S.mesh(new T.SphereGeometry(0.005, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); lled.position.set(-0.07, 0.025, 0.062); las.add(lled);
  var pipe = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.3, 18), M.alu); pipe.rotation.z = Math.PI / 2; pipe.position.set(0.24, 0.07, 0); las.add(pipe);
  var plb = S.label('BEAM TUBE · sealed, horizontal, 7 cm above the bench', { w: 0.22, ratio: 0.06, color: '#7a1f1f' }); plb.rotation.x = -Math.PI / 2; plb.position.set(0.12, 0.0012, 0.08); las.add(plb);
  S.contact(0.22, 0.16, -0.55, -0.2, 0.4);
  // the analyser
  var ins = Kt.instrument({ x: 0.28, z: -0.22, ry: -0.12, w: 0.42, h: 0.2, d: 0.26, title: 'TRAP ANALYSER', sub: 'bead position · record · spectrum · stage speed', screen: { u: -0.045, v: 0.0, w: 0.28, h: 0.155 },
    knobs: [[0.145, 0.035, 0.012, 'LASER POWER']], buttons: [[0.1, -0.06, 'POWER', M.green], [0.17, -0.06, 'RECORD', M.grey]] });
  var pwr = ins.buttons[0], go = ins.buttons[1], led1 = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }));
  led1.position.copy(ins.at(0.1, -0.038, 0.002)); ins.g.add(led1);
  S.contact(0.5, 0.34, 0.28, -0.22, 0.5);
  S.wire([[-0.1 + 0.05, 0.33, -0.25], [0.0, 0.2, -0.2], [0.07, 0.08, -0.22]], 'black'); S.wire([[-0.1 + 0.12, 0.015, -0.2], [0.05, 0.02, -0.12], [0.07, 0.05, -0.2]], 'red');
  S.addApparatus('mic', mic, 'Inverted microscope with a bead chamber', 'A drop of 1 micrometre silica beads in water on a slide, on a motorised stage. The trapping beam enters from below through the objective and holds one bead near its focus; a quadrant photodiode follows the bead.');
  S.addApparatus('las', las, 'Trapping laser (simulated, sealed)', 'A real trapping laser is an invisible Class 4 infrared beam, enclosed and interlocked, set up by staff. Here it is a simulated instrument: you set its power with the knob on the analyser and nothing else.');
  S.addApparatus('ins', ins.g, 'Trap analyser', 'Records the bead position, shows its histogram and power spectrum, and drives the stage.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Power'), hudB = S.hudCard('Laser power'), hudC = S.hudCard('Readings');

  // ================================================================ the screen
  function drawScreen(x, w, h) {
    Kt.bg(x, w, h); var fs = Math.round(h * 0.05), ch, i, q = pNow();
    if (!st.on) { Kt.text(x, 'power off', w / 2, h / 2, '#5aa77a', fs * 1.4, 'center'); return; }
    var xs = st.rec, k;
    ch = Kt.chart(x, { x: w * 0.1, y: h * 0.08, w: w * 0.86, h: h * 0.3 }, { xr: [0, 0.4], yr: [-250, 250], xlabel: 'time (s)', ylabel: 'bead position (nm)' });
    if (xs) { var pts = [], n = Math.min(xs.length, Math.floor(0.4 * q.fs)), stp = Math.max(1, Math.floor(n / 600)), off = st.drag ? st.drag.off : 0; for (i = 0; i < n; i += stp) pts.push([i / q.fs, (xs[i] - off) * 1e9]); Kt.poly(x, ch, pts, '#ffe45e', 1.2); }
    if (st.sp) {
      var ch2 = Kt.chart(x, { x: w * 0.1, y: h * 0.52, w: w * 0.86, h: h * 0.3 }, { xr: [st.sp[0][0], st.sp[st.sp.length - 1][0]], yr: [1e-21, 5e-18], xlog: true, ylog: true, xlabel: 'frequency (Hz, log)', ylabel: 'power (m²/Hz, log)' });
      Kt.poly(x, ch2, st.sp.map(function (z) { return [z[0], Math.max(z[1], 1e-21)]; }), '#ffe45e', 1.2);
      if (st.fc) { x.strokeStyle = 'rgba(100,227,255,.9)'; x.lineWidth = 2; x.beginPath(); x.moveTo(ch2.X(st.fc), h * 0.52); x.lineTo(ch2.X(st.fc), h * 0.82); x.stroke(); Kt.text(x, 'fc ' + r(st.fc, 1) + ' Hz', ch2.X(st.fc) + 6, h * 0.58, '#64e3ff', fs); }
    }
    Kt.text(x, 'laser ' + PW[st.lp] + ' mW' + (st.rec ? '   ' + st.rec.length + ' samples at ' + q.fs + ' Hz' : '   press RECORD'), w * 0.04, h * 0.9, '#9fe0b8', fs);
    if (st.cur) Kt.text(x, st.cur.txt, w * 0.96, h * 0.97, '#ffe45e', fs * 1.05, 'right');
    if (st.prog > 0 && st.prog < 1) { x.fillStyle = 'rgba(100,227,255,.8)'; x.fillRect(0, h - 6, w * st.prog, 6); }
  }
  function paint() { ins.screen.paint(drawScreen); }
  var panelCv = null;
  function paintPanel() { if (panelCv && panelCv.isConnected) drawScreen(panelCv.getContext('2d'), panelCv.width, panelCv.height); }
  function panel(u) { panelCv = Kt.panel(u, 0.62); paintPanel(); }

  // ================================================================ actions
  function integrate(ms, fn) { return S.tween(ms, function (k) { st.prog = k; if (k >= 1) st.prog = 0; mark(); }).then(function () { st.prog = 0; return fn(); }); }
  function needOn() { if (!st.on) { S.say('Switch the analyser on first.'); return true; } return false; }
  function powerOn(on) {
    if (Kt.busy()) return Promise.resolve(); if (st.on === on) return Promise.resolve();
    return S.hand.tap(pwr, 'front').then(function () {
      st.on = on; led1.material.emissive.setHex(on ? 0x22cc44 : 0); led1.material.color.setHex(on ? 0x33dd55 : 0x331111); lled.material.emissive.setHex(on ? 0xcc2222 : 0); lled.material.color.setHex(on ? 0xff3333 : 0x331111);
      S.say(on ? 'Analyser on. The enclosed laser is on and one bead is trapped.' : 'Switched off.'); mark(); S.render();
    });
  }
  function setPower(i) {
    if (Kt.busy() || i < 0 || i >= PS.length) return Promise.resolve();
    var kn = ins.knobs[0], a0 = kn.rotation.z, a1 = 2.0 - 4.0 * i / (PS.length - 1), pt = Kt.wpt(ins.g, kn.position.x, kn.position.y, ins.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kn.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 450, reachMs: 450 }).then(function () { st.lp = i; kn.rotation.z = a1; st.rec = null; st.sp = null; st.fc = null; st.cur = null; mark(); S.render(); });
  }
  function recordRun() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return S.hand.tap(go, 'front').then(function () { return integrate(1200, function () {
      var q = pNow(); st.rec = KN.record(q, Math.floor(q.N), 10 * st.idx++ + 0.5, 0); st.sp = null; st.fc = null; st.drag = null; st.cur = null;
      S.say('Recorded ' + r(q.N / q.fs, 0) + ' s of the bead\'s position.'); mark(); S.render(); return st.rec;
    }); });
  }
  function meanOf(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return s / xs.length; }
  function x2Of() { var xs = st.rec, m = meanOf(xs), s = 0, i; for (i = 0; i < xs.length; i++) s += (xs[i] - m) * (xs[i] - m); return s / xs.length; }
  function equip() {
    if (!st.rec) { S.say('Record the bead first.'); return null; }
    var x2 = x2Of(), k = KB * p.T / x2; st.cur = { m: 'eq', x2: x2, kappa: k, P: PW[st.lp], txt: '<x²> = ' + r(x2 * 1e18, 0) + ' nm²   κ = ' + r(k * 1e6, 2) + ' pN/µm' };
    S.say('<x²> = ' + r(x2 * 1e18, 0) + ' nm². Equipartition: κ = kB T / <x²> = ' + r(k * 1e6, 2) + ' pN/µm.'); mark(); S.render(); return st.cur;
  }
  function spectrumFit() {
    if (!st.rec) { S.say('Record the bead first.'); return null; }
    var q = pNow(); st.sp = KN.spectrum(q, st.rec, 128); st.fc = KN.corner(st.sp, q.fs); var k = 2 * Math.PI * G * st.fc;
    st.cur = { m: 'psd', fc: st.fc, kappa: k, P: PW[st.lp], x2: x2Of(), txt: 'fc = ' + r(st.fc, 1) + ' Hz   κ = ' + r(k * 1e6, 2) + ' pN/µm' };
    S.say('Corner frequency ' + r(st.fc, 1) + ' Hz; with γ = 6π η a = ' + r(G * 1e9, 2) + ' × 10⁻⁹ kg/s the stiffness is ' + r(k * 1e6, 2) + ' pN/µm.'); mark(); S.render(); return st.cur;
  }
  function dragRun() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    if (!st.rec) { S.say('Record the bead at rest first (it gives the rest position).'); return Promise.resolve(null); }
    var q = pNow(), v = p.v;
    return S.hand.tap(go, 'front').then(function () { return integrate(1000, function () {
      var nd = Math.floor(q.Td * q.fs), run = KN.record(q, nd, 10 * st.idx++ + 1.5, G * v / KN.kappa(q)), m0 = meanOf(st.rec), m1 = meanOf(run), xd = m1 - m0;
      st.drag = { off: m0, xd: xd, v: v }; st.cur = { m: 'drag', xd: xd, v: v, kappa: G * v / xd, P: PW[st.lp], x2: x2Of(), txt: 'lag ' + r(xd * 1e9, 1) + ' nm at ' + r(v * 1e6, 0) + ' µm/s   κ = ' + r(G * v / xd * 1e6, 2) + ' pN/µm' };
      st.rec = run; st.sp = null; st.fc = null; S.say('Stage moving at ' + r(v * 1e6, 0) + ' µm/s: the bead lags ' + r(xd * 1e9, 1) + ' nm. Stokes drag γ v = ' + r(G * v * 1e12, 2) + ' pN is balanced by κ x.'); mark(); S.render(); return st.cur;
    }); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var c = st.cur; if (!c) { S.say('Analyse a record first.'); return false; }
    if (S.rows.some(function (z) { return z.m === c.m && z.P === c.P; })) { S.say('That analysis at this power is already in the book.'); return false; }
    S.addRow(assign(c, { txt: undefined })); st.cur = null; mark(); return true;
  }
  // ---- analysis of the book
  function rowsOf(m, P) { return S.rows.filter(function (z) { return z.m === m && (P === undefined || z.P === P); }); }
  function result(rows) {
    var base = PW[2], eq = rows.filter(function (z) { return z.m === 'eq' && z.P === base; })[0]; if (!eq) return null;
    var ps = rows.filter(function (z) { return z.m === 'psd' && z.P === base; })[0], dr = rows.filter(function (z) { return z.m === 'drag' && z.P === base; })[0], note = '', lin = rows.filter(function (z) { return z.m === 'eq'; });
    if (ps) note += 'Corner frequency ' + r(ps.fc, 1) + ' Hz gives ' + r(ps.kappa * 1e6, 2) + ' pN/µm; with κ from equipartition the viscosity would be ' + r(eq.kappa / (2 * Math.PI * ps.fc * 6 * Math.PI * p.a) * 1e3, 3) + ' mPa s. ';
    if (dr) note += 'Stokes drag gives ' + r(dr.kappa * 1e6, 2) + ' pN/µm, and with that κ the equipartition record gives kB = ' + r(dr.kappa * eq.x2 / p.T * 1e23, 3) + ' × 10⁻²³ J/K. ';
    if (lin.length >= 3) { var f = S.fit.origin(lin.map(function (z) { return [z.P, z.kappa * 1e6]; })); note += 'Stiffness against laser power: ' + r(f, 3) + ' pN/µm per mW over ' + lin.length + ' powers (a straight line through the origin).'; }
    return { label: 'Trap stiffness at ' + base + ' mW', value: eq.kappa * 1e6, unit: 'pN/µm', digits: 2, truth: p.kp * p.P * 1e6, note: note };
  }
  var VIVA = [['Doubling the laser power makes the trap stiffness', ['Double', 'Half', 'Unchanged'], 0, 'κ is proportional to the power.'], ['Equipartition says the mean potential energy ½ κ <x²> is', ['½ kB T', 'kB T', 'Zero'], 0, 'One degree of freedom, ½ kB T.'], ['In the power spectrum, a stiffer trap has a corner frequency that is', ['Higher', 'Lower', 'The same'], 0, 'fc = κ / (2π γ).']];

  // ================================================================ steps
  var STEPS = [{ id: 'on', title: 'Switch on', view: 'ins', render: function (u) {
      u.h2('Switch the analyser on');
      u.p('A 1 micrometre silica bead (radius ' + r(p.a * 1e6, 2) + ' µm) is held in water near the focus of the trapping beam. The quadrant photodiode follows its position and the analyser records it.');
      u.task('Power', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('ins'); powerOn(!st.on); }, !st.on, S.hand.busy));
      u.note('The trapping laser is a sealed, interlocked Class 4 infrared beam: a simulated instrument here, and in a real lab set up by staff. Never open the box or the beam tube.');
      u.next('Next', st.on); }, ok: function () { return st.on; }, auto: function () { return powerOn(true); } },
    { id: 'equip', title: 'Equipartition', view: 'ins', render: function (u) {
        u.h2('Stiffness from the width of the bead\'s wander');
        u.p('Record 52 seconds of the bead\'s position at each laser power. Work out the mean square displacement <x²>; equipartition gives κ = kB T / <x²> at T = ' + p.T + ' K. Do at least three of the four powers.');
        u.row(PW.map(function (v, i) { return u.button(v + ' mW', function () { S.focus('ins'); setPower(i); }, st.lp === i, S.hand.busy); })[0], PW.map(function (v, i) { return u.button(v + ' mW', function () { setPower(i); }, st.lp === i, S.hand.busy); })[1], PW.map(function (v, i) { return u.button(v + ' mW', function () { setPower(i); }, st.lp === i, S.hand.busy); })[2], PW.map(function (v, i) { return u.button(v + ' mW', function () { setPower(i); }, st.lp === i, S.hand.busy); })[3]);
        u.row(u.button('RECORD', function () { S.focus('ins'); recordRun(); }, true, S.hand.busy), u.button('Work out <x²> and κ', function () { equip(); }, false, !st.rec || S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        u.live(function () { return PW[st.lp] + ' mW · ' + (st.cur && st.cur.m === 'eq' ? 'κ = ' + r(st.cur.kappa * 1e6, 2) + ' pN/µm' : st.rec ? 'recorded' : 'no record'); });
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: the power spectrum', rowsOf('eq').length >= 3 && rowsOf('eq', PW[2]).length >= 1); },
      ok: function () { return rowsOf('eq').length >= 3 && rowsOf('eq', PW[2]).length >= 1; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < 3; j++) (function (jj) { c = c.then(function () { return setPower(jj); }).then(function () { return recordRun(); }).then(function () { equip(); record(); }); })(j); return c; } },
    { id: 'psd', title: 'Power spectrum', view: 'ins', render: function (u) {
        u.h2('Stiffness from the corner frequency');
        u.p('Set the laser to ' + PW[2] + ' mW and record. The analyser averages the power spectrum in 128 segments and fits a Lorentzian: the corner frequency is fc = κ / (2π γ), with γ = 6π η a the Stokes drag on the bead (η = ' + r(p.eta * 1e3, 2) + ' mPa s, water).');
        u.row(u.button(PW[2] + ' mW', function () { S.focus('ins'); setPower(2); }, st.lp !== 2, S.hand.busy || st.lp === 2), u.button('RECORD', function () { S.focus('ins'); recordRun(); }, true, S.hand.busy || st.lp !== 2), u.button('Spectrum and fit', function () { spectrumFit(); }, false, !st.rec || S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: Stokes drag', rowsOf('psd').length >= 1); },
      ok: function () { return rowsOf('psd').length >= 1; }, auto: function () { return setPower(2).then(function () { return recordRun(); }).then(function () { spectrumFit(); record(); }); } },
    { id: 'drag', title: 'Stokes drag', view: 'mic', render: function (u) {
        u.h2('Stiffness from the lag behind a moving stage');
        u.p('With the bead at rest recorded at ' + PW[2] + ' mW (that gives its rest position), move the stage at ' + r(p.v * 1e6, 0) + ' µm/s. The water drags the bead back by γ v, and the trap pulls it forward with κ x_d: so κ = γ v / x_d.');
        u.row(u.button(PW[2] + ' mW', function () { setPower(2); }, st.lp !== 2, S.hand.busy || st.lp === 2), u.button('RECORD at rest', function () { S.focus('ins'); recordRun(); }, false, S.hand.busy || st.lp !== 2), u.button('Move the stage', function () { S.focus('mic'); dragRun(); }, true, S.hand.busy || !st.rec || st.drag !== null), u.button('Write it down', function () { record(); }, false, !st.cur || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: result', rowsOf('drag').length >= 1); },
      ok: function () { return rowsOf('drag').length >= 1; }, auto: function () { return setPower(2).then(function () { return recordRun(); }).then(function () { return dragRun(); }).then(function () { record(); }); } }];

  function askState() { return { experiment: S.lab.title, sample: V_.sample || '', power_on: st.on, laser_power_mW: PW[st.lp], bead_radius_um: p.a * 1e6, temperature_K: p.T, readings: S.rows.length }; }
  return {
    camera: { pos: [-0.12, 0.66, 1.2], look: [-0.12, 0.1, -0.2] },
    views: { mic: [[-0.06, 0.34, 0.26], [-0.06, 0.15, -0.17]], las: [[-0.5, 0.25, 0.2], [-0.55, 0.05, -0.2]], ins: [[0.25, 0.37, 0.48], [0.28, 0.1, -0.22]], bench: [[-0.12, 0.66, 1.2], [-0.12, 0.1, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A tightly focused laser beam pulls a small transparent bead towards the focus: near the focus it is a spring of stiffness κ. Thermal kicks from the water make the bead wander in it, and the size and speed of that wander measure κ. Three independent ways agree: the width of the wander (equipartition), its speed (the corner frequency of the spectrum) and the lag behind a moving stage (Stokes drag).',
      formula: 'κ = kB T / <x²>,   fc = κ / (2π γ),   κ = γ v / x_d,   γ = 6π η a', formulaNote: 'γ is the Stokes drag coefficient of the bead in water',
      more: ['The position of a bead in a harmonic trap is an Ornstein-Uhlenbeck process: its spectrum is a Lorentzian with corner frequency fc, flat below it and falling as 1/f² above.', 'With κ known from the drag test, equipartition gives kB; with κ from equipartition, the corner frequency gives the viscosity of the liquid.', 'Doubling the laser power doubles κ: the three methods all give a straight line against power.'],
      precautions: 'A real trapping laser is an invisible Class 4 infrared beam: it is enclosed and interlocked, set up by staff. Do not open the box or the beam tube, and do not look into any microscope port. Here it is a simulated instrument.' },
    book: { title: 'Expt. - ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 74), 'Bead radius ' + r(p.a * 1e6, 2) + ' um, water, T = ' + p.T + ' K', 'Laser powers ' + PW.join(', ') + ' mW', 'Simulated instrument (sealed IR laser).'],
      columns: [{ label: 'Method', get: function (z) { return z.m === 'eq' ? 'equipartition' : z.m === 'psd' ? 'spectrum' : 'drag'; } }, { label: 'P (mW)', get: function (z) { return z.P; } }, { label: 'Measured', get: function (z) { return z.m === 'eq' ? '<x²> ' + r(z.x2 * 1e18, 0) + ' nm²' : z.m === 'psd' ? 'fc ' + r(z.fc, 1) + ' Hz' : 'lag ' + r(z.xd * 1e9, 1) + ' nm'; } }, { label: 'κ (pN/µm)', get: function (z) { return r(z.kappa * 1e6, 2); } }] },
    graph: { x: function (z) { return z.P; }, y: function (z) { return z.kappa * 1e6; }, xlabel: 'laser power (mW)', ylabel: 'κ (pN/µm)', line: function (pts) { var m = S.fit.origin(pts); return isFinite(m) ? function (x) { return m * x; } : null; } },
    result: result, tol: 0.04, resultNote: 'The stiffness comes from the width of a 52 s record: with about 14 000 independent samples the statistical scatter is about 1 %. The other two methods agree within their own scatter, 1 to 3 %.',
    chips: ['Why does κ go up with power?', 'What is equipartition?', 'Why is the spectrum a Lorentzian?', 'Check my readings', 'What if the bead sticks to the slide?'],
    viva: VIVA, askState: askState, steps: STEPS,
    tick: function () { hudA.set(st.on ? 'On' : 'Off'); hudB.set(PW[st.lp] + ' mW'); hudC.set(S.rows.length + ' written'); if (dirty) { dirty = false; paint(); paintPanel(); } },
    ready: function () { paint(); }
  };
});
