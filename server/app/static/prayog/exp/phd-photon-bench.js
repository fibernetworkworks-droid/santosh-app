/* Prayogshala studio module: PHOTON-COUNTING BENCH (Ph.D. quantum optics and photon statistics).
   One bench, three set-ups, one kernel each of packs/phd_optics.js:
     phd_g2         a Hanbury Brown-Twiss correlator: a laser, a rotating ground-glass disc, a beam splitter, two photon
                    counters and a coincidence histogram (pseudo-thermal light and laser light);
     phd_poisson    a source, a counter with a dead time and a scaler: counts per window, their variance, the gaps;
     phd_antibunch  a heralded-photon source (SIMULATED INSTRUMENT: no student may touch a pump laser and a down-converter),
                    a beam splitter and three single-photon counters.
   The counts are drawn from the lab's own seed. The student finds g2(0), the mean-variance relation or alpha from the
   counts by their own division, fit or count; the bench never shows the quantity being measured. */
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

HoolaStudio.define('phd-photon-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, Kt = phdKit(S), r = Kt.r, si = Kt.si;
  var MODE = ({ phd_g2: 'g2', phd_poisson: 'poisson', phd_antibunch: 'anti' })[KERN];
  var RATES = [10, 30, 100, 300, 1000, 3000, 10000, 30000];
  var st = { on: false, glass: false, hist: null, cur: null, rate: 3, prog: 0, idx: 0, gaps: null, counts: null, an: null, cnt: null };
  var dirty = true;
  function mark() { dirty = true; }
  function beam(a, b, col, op) {
    var d = new T.Vector3().subVectors(b, a), len = d.length(), m = new T.Mesh(new T.CylinderGeometry(0.0011, 0.0011, len, 8), new T.MeshBasicMaterial({ color: col || 0xff3322, transparent: true, opacity: op || 0.5 }));
    m.position.copy(a).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); S.scene.add(m); return m;
  }
  function apd(x, z, ry, name, big) {                                          // a photon-counting module with a snout and a BNC
    var g = new T.Group(); g.position.set(x, 0, z); g.rotation.y = ry; S.scene.add(g);
    Kt.box(0.07, 0.06, 0.05, 0x3a3f47, 0, 0, 0, g);
    var sn = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.035, 20), M.alu); sn.rotation.z = Math.PI / 2; sn.position.set(-0.05, 0.1 - 0.06 + 0.0, 0); g.add(sn); sn.position.y = 0.04;
    var lb = S.label(name, { w: 0.05, ratio: 0.2, color: '#e8e8ea' }); lb.position.set(0, 0.033, 0.0252); g.add(lb);
    Kt.bnc(g, 0.035, 0.03, 0, Math.PI / 2); S.contact(0.1, 0.08, x, z, 0.4); return g;
  }
  var HY = 0.1;                                                              // beam height above the bench: low, never eye level

  // ================================================================ the optics
  var optics = new T.Group(); S.scene.add(optics);
  var disc = null, discG = null, discX = -0.3, bs = null, detA = null, detB = null, srcBox = null;
  if (MODE === 'g2') {
    var lz = new T.Group(); lz.position.set(-0.55, 0, -0.22); S.scene.add(lz);
    var lbod = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.2, 24), new T.MeshStandardMaterial({ color: 0x2f3a46, roughness: 0.4, metalness: 0.5 })); lbod.rotation.z = Math.PI / 2; lbod.position.set(0, HY, 0); lz.add(lbod);
    var lcap = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.012, 24), M.alu); lcap.rotation.z = Math.PI / 2; lcap.position.set(0.105, HY, 0); lz.add(lcap);
    var lst = S.mesh(new T.BoxGeometry(0.1, HY - 0.02, 0.05), M.alu); lst.position.set(0, (HY - 0.02) / 2 + 0.0, 0); lz.add(lst);
    var llb = S.label('He-Ne LASER · low power', { w: 0.1, ratio: 0.12, color: '#e8e8ea' }); llb.position.set(-0.01, HY + 0.0, 0.0205); lz.add(llb);
    S.contact(0.28, 0.12, -0.55, -0.22, 0.4);
    var lens = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.004, 24), M.glass); lens.rotation.z = Math.PI / 2; lens.position.set(-0.43, HY, -0.22); S.scene.add(lens);
    var lsp = S.mesh(new T.CylinderGeometry(0.003, 0.003, HY - 0.012, 10), M.chrome); lsp.position.set(-0.43, (HY - 0.012) / 2, -0.22); S.scene.add(lsp);
    // the ground-glass disc on its motor: it slides in and out of the beam
    discG = new T.Group(); discG.position.set(discX, 0, -0.22); S.scene.add(discG);
    var mot = Kt.box(0.05, 0.05, 0.04, 0x3a3f47, 0, 0, -0.05, discG);
    disc = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.003, 40), new T.MeshStandardMaterial({ color: 0xdfe7ea, roughness: 0.9, transparent: true, opacity: 0.8 })); disc.rotation.x = Math.PI / 2; disc.position.set(0, HY, -0.0); discG.add(disc);
    var dsp = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.05, 10), M.chrome); dsp.rotation.x = Math.PI / 2; dsp.position.set(0, HY, -0.025); discG.add(dsp);
    var dlb = S.label('ROTATING GROUND GLASS', { w: 0.08, ratio: 0.12, color: '#e8e8ea' }); dlb.rotation.x = -Math.PI / 2; dlb.position.set(0, 0.0012, 0.05); discG.add(dlb);
    discG.position.z = -0.22 + 0.16;                                           // out of the beam, in front
    bs = S.mesh(new T.BoxGeometry(0.025, 0.025, 0.025), M.glass); bs.position.set(-0.12, HY, -0.22); S.scene.add(bs);
    var bsp = S.mesh(new T.CylinderGeometry(0.003, 0.003, HY - 0.012, 10), M.chrome); bsp.position.set(-0.12, (HY - 0.012) / 2, -0.22); S.scene.add(bsp);
    S.contact(0.06, 0.06, -0.12, -0.22, 0.4);
    detA = apd(0.06, -0.22, 0, 'COUNTER 1'); detB = apd(-0.12, -0.38, Math.PI / 2, 'COUNTER 2');
    detA.children[1].position.set(-0.05, 0.04, 0); detB.children[1].position.set(-0.05, 0.04, 0);
    var bm1 = beam(new T.Vector3(-0.44, HY, -0.22), new T.Vector3(-0.12, HY, -0.22)), bm2 = beam(new T.Vector3(-0.12, HY, -0.22), new T.Vector3(0.025, HY, -0.22), 0xff3322, 0.35), bm3 = beam(new T.Vector3(-0.12, HY, -0.22), new T.Vector3(-0.12, HY, -0.35), 0xff3322, 0.35);
    var cl = S.label('beam clamped horizontal · 10 cm above the bench', { w: 0.16, ratio: 0.07, color: '#7a1f1f' }); cl.rotation.x = -Math.PI / 2; cl.position.set(-0.3, 0.0012, -0.08); S.scene.add(cl);
    optics.add(lz);
  } else if (MODE === 'poisson') {
    var srcB = Kt.box(0.1, 0.06, 0.08, 0x6f8193, -0.5, 0, -0.22);
    var srl = S.label('LED SOURCE', { w: 0.08, ratio: 0.12, color: '#f1efe8', bg: '#2b323d', px: 512 }); srl.position.set(-0.5, 0.04, -0.22 + 0.0405); S.scene.add(srl);
    var led = S.mesh(new T.SphereGeometry(0.01, 18, 18), new T.MeshStandardMaterial({ color: 0x664400, emissive: 0x000000 })); led.position.set(-0.43, 0.04, -0.22); S.scene.add(led); disc = led;
    var rail = S.mesh(new T.BoxGeometry(0.5, 0.006, 0.02), M.alu); rail.position.set(-0.22, 0.003, -0.22); S.scene.add(rail);
    var rtext = S.canvasTex(1024, 40, function (x, w, h) { x.fillStyle = '#dfe3e6'; x.fillRect(0, 0, w, h); x.fillStyle = '#222'; x.font = '600 24px "Public Sans", sans-serif'; for (var i = 0; i <= 10; i++) { x.fillRect(i * w / 10, 0, 3, 16); x.fillText(String(i * 5), i * w / 10 + 6, 36); } });
    var rs = new T.Mesh(new T.PlaneGeometry(0.5, 0.0195), new T.MeshBasicMaterial({ map: rtext })); rs.rotation.x = -Math.PI / 2; rs.position.set(-0.22, 0.0063, -0.22); S.scene.add(rs);
    var dt = apd(0.07, -0.22, 0, 'PHOTON COUNTER');
    var sh = Kt.box(0.035, 0.02, 0.05, 0x2f3a46, -0.27, 0, -0.22);
    S.contact(0.6, 0.12, -0.22, -0.22, 0.3);
    optics.add(rail);
  } else {
    srcBox = new T.Group(); srcBox.position.set(-0.5, 0, -0.24); S.scene.add(srcBox);
    Kt.box(0.17, 0.09, 0.12, 0x2b323d, 0, 0, 0, srcBox);
    var sl = S.label('HERALDED PHOTON SOURCE', { w: 0.15, ratio: 0.1, color: '#f1efe8' }); sl.position.set(0, 0.07, 0.0607); srcBox.add(sl);
    var sl2 = S.label('SIMULATED INSTRUMENT · pump laser sealed in', { w: 0.15, ratio: 0.08, color: '#f2d02a' }); sl2.position.set(0, 0.052, 0.0607); srcBox.add(sl2);
    var wl = S.label('pair source: heralds + partners', { w: 0.12, ratio: 0.08, color: '#c7ccd6' }); wl.position.set(0, 0.034, 0.0607); srcBox.add(wl);
    bs = S.mesh(new T.BoxGeometry(0.025, 0.025, 0.025), M.glass); bs.position.set(-0.28, HY - 0.04, -0.24); S.scene.add(bs);
    var bsp2 = S.mesh(new T.CylinderGeometry(0.003, 0.003, HY - 0.052, 10), M.chrome); bsp2.position.set(-0.28, (HY - 0.052) / 2, -0.24); S.scene.add(bsp2);
    detA = apd(-0.4, -0.38, 0.0, 'G (HERALD)'); detB = apd(-0.12, -0.24, 0, 'T'); var detC = apd(-0.28, -0.4, Math.PI / 2, 'R');
    S.wire([[-0.4, 0.05, -0.2], [-0.35, 0.03, -0.17], [-0.28, 0.045, -0.2]], 'black');
    var fib = S.wire([[-0.42, 0.09, -0.24 + 0.06], [-0.35, 0.03, -0.24 + 0.1], [-0.28, 0.08, -0.24 + 0.02]], 'ray');
    S.contact(0.2, 0.15, -0.5, -0.24, 0.4);
  }

  // ================================================================ the instrument
  var TIT = { g2: ['COINCIDENCE HISTOGRAMMER', 'two inputs · 6.25 µs bins · ±250 µs'], poisson: ['SCALER / TIMER', 'counts per window · dead time 10 µs'], anti: ['4-CHANNEL COINCIDENCE COUNTER', 'G · T · R · G+T+R'] };
  var ins = Kt.instrument({ x: 0.22, z: -0.24, ry: -0.12, w: 0.42, h: 0.2, d: 0.26, title: TIT[MODE][0], sub: TIT[MODE][1], screen: { u: -0.045, v: 0.0, w: 0.28, h: 0.155 },
    knobs: MODE === 'poisson' ? [[0.145, 0.03, 0.012, 'SOURCE POSITION']] : [], buttons: [[0.1, -0.06, 'POWER', M.green], [0.17, -0.06, MODE === 'poisson' ? 'COUNT' : 'START', M.grey]] });
  var pwr = ins.buttons[0], go = ins.buttons[1], led1 = S.mesh(new T.SphereGeometry(0.004, 12, 12), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 }));
  led1.position.copy(ins.at(0.1, -0.038, 0.002)); ins.g.add(led1);
  S.contact(0.5, 0.34, 0.22, -0.24, 0.5);
  if (MODE === 'g2') { S.wire([[0.06 + 0.035, 0.03, -0.22], [0.07, 0.02, -0.3], [0.01, 0.06, -0.26]], 'black'); S.wire([[-0.12, 0.03, -0.38 + 0.035], [-0.05, 0.02, -0.33], [0.01, 0.07, -0.23]], 'black'); }
  if (MODE === 'poisson') S.wire([[0.07 + 0.035, 0.03, -0.22], [0.05, 0.02, -0.3], [0.01, 0.06, -0.26]], 'black');

  S.addApparatus('optics', MODE === 'g2' ? optics : MODE === 'poisson' ? optics : srcBox, MODE === 'g2' ? 'Laser, ground glass, beam splitter and counters' : MODE === 'poisson' ? 'LED source on a rail and photon counter' : 'Heralded photon source (simulated)',
    MODE === 'g2' ? 'A low-power laser is expanded and passes through a rotating ground-glass disc, then a 50:50 beam splitter sends half to each photon counter. The beam stays 10 cm above the bench. The disc slides in and out of the beam.'
      : MODE === 'poisson' ? 'The LED shines on the photon counter. Moving it along the rail changes the light, so the rate; the counter registers one pulse per photon and is blind for 10 microseconds after each.'
        : 'A real pump laser and crystal are sealed and set up by staff, so this is a SIMULATED INSTRUMENT. Each photon of a pair that reaches G heralds the other, which goes to the beam splitter and its two counters T and R.');
  S.addApparatus('ins', ins.g, TIT[MODE][0].charAt(0) + TIT[MODE][0].slice(1).toLowerCase(), 'The counter and its screen. Everything it shows is what a real one would show: counts and histograms.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard('Power'), hudB = S.hudCard(MODE === 'g2' ? 'Source' : MODE === 'poisson' ? 'Rate set' : 'Run'), hudC = S.hudCard('Readings');

  // ================================================================ what the screen shows
  function drawScreen(x, w, h) {
    Kt.bg(x, w, h); var fs = Math.round(h * 0.05), i, ch;
    if (!st.on) { Kt.text(x, 'power off', w / 2, h / 2, '#5aa77a', fs * 1.4, 'center'); return; }
    if (MODE === 'g2') {
      var hs = st.hist, mid = hs ? (hs.length - 1) / 2 : 40, cinf = p.R1 * p.R2 * p.Ts * p.bw;
      ch = Kt.chart(x, { x: w * 0.1, y: h * 0.1, w: w * 0.86, h: h * 0.55 }, { xr: [-(mid) * p.bw * 1e6, mid * p.bw * 1e6], yr: [cinf * 0.8, cinf * 2.2], xlabel: 'delay between the two counters (µs)', ylabel: 'coincidences per bin' });
      if (hs) { for (i = 0; i < hs.length; i++) { var bx = ch.X((i - mid) * p.bw * 1e6), by = ch.Y(Math.max(hs[i], cinf * 0.8)); x.fillStyle = '#ffe45e'; x.fillRect(bx - w * 0.004, by, w * 0.0085, ch.Y(cinf * 0.8) - by); } }
      Kt.text(x, st.glass ? 'ground glass IN: pseudo-thermal light' : 'ground glass OUT: laser light', w * 0.04, h * 0.84, '#9fe0b8', fs * 0.95);
      Kt.text(x, st.an ? 'centre ' + Math.round(hs[mid]) + '   far mean ' + Math.round(st.an[2]) : (hs ? '' : 'press START to accumulate ' + p.Ts + ' s'), w * 0.04, h * 0.93, '#ffe45e', fs * 1.1);
      Kt.text(x, 'rate 1 ' + si(p.R1, 'Hz', 2) + '   rate 2 ' + si(p.R2, 'Hz', 2), w * 0.96, h * 0.93, '#9fe0b8', fs * 0.9, 'right');
    } else if (MODE === 'poisson') {
      var cs = st.counts, mx = 1, bins = [], nb = 40, lo = 0, hi = 1, m, sd;
      if (cs) { var mv = KN.stats(cs); m = mv[0]; sd = Math.sqrt(mv[1]); lo = Math.max(0, Math.floor(m - 4.5 * Math.max(sd, 1))); hi = Math.ceil(m + 4.5 * Math.max(sd, 1)); if (hi - lo < 12) hi = lo + 12;
        for (i = 0; i < nb; i++) bins.push(0); cs.forEach(function (c) { var k = Math.floor((c - lo) / (hi - lo) * nb); if (k >= 0 && k < nb) bins[k]++; }); mx = Math.max.apply(null, bins); }
      ch = Kt.chart(x, { x: w * 0.1, y: h * 0.12, w: w * 0.86, h: h * 0.55 }, { xr: [lo, hi], yr: [0, Math.max(mx * 1.15, 5)], xlabel: 'counts in one window', ylabel: 'windows' });
      if (cs) { bins.forEach(function (b, k) { var bx = ch.X(lo + (k + 0.5) * (hi - lo) / nb), by = ch.Y(b); x.fillStyle = '#ffe45e'; x.fillRect(bx - w * 0.009, by, w * 0.018, ch.Y(0) - by); }); }
      var q = st.cur;
      Kt.text(x, q ? 'window ' + si(q.tw, 's', 2) + '   ' + st.counts.length + ' windows' : 'press COUNT', w * 0.04, h * 0.78, '#9fe0b8', fs);
      Kt.text(x, q ? 'mean ' + r(q.mean, 2) + '    variance ' + r(q.v, 2) : '', w * 0.04, h * 0.88, '#ffe45e', fs * 1.3);
      Kt.text(x, 'source at ' + (RATES[st.rate] >= 1 ? '' : '') + 'position ' + (st.rate + 1) + ' of ' + RATES.length, w * 0.96, h * 0.78, '#9fe0b8', fs, 'right');
    } else {
      var c = st.cnt, lab = ['N_G', 'N_GT', 'N_GR', 'N_GTR'], col = ['#ffe45e', '#64e3ff', '#64e3ff', '#ff9f5e'];
      for (i = 0; i < 4; i++) { Kt.text(x, lab[i], w * 0.06, h * (0.2 + i * 0.17), col[i], fs * 1.5); Kt.text(x, c ? String(Math.round(c[i])).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : '—', w * 0.96, h * (0.2 + i * 0.17), col[i], fs * 2.1, 'right'); }
      Kt.text(x, c ? 'run finished' : 'press START to run the counters', w * 0.06, h * 0.9, '#9fe0b8', fs);
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
      if (MODE === 'poisson' && disc) { disc.material.emissive.setHex(on ? 0xffaa33 : 0); }
      S.say(on ? (MODE === 'g2' ? 'Instrument on. The laser is running and the counters are armed.' : MODE === 'poisson' ? 'Instrument on, LED lit.' : 'Instrument on: the source and the three counters are running.') : 'Switched off.'); mark(); S.render();
    });
  }
  function glass(on) {
    if (MODE !== 'g2' || Kt.busy() || st.glass === on) return Promise.resolve();
    var z0 = discG.position.z, z1 = on ? -0.22 : -0.22 + 0.16, pt = new T.Vector3(discX, HY + 0.03, z0);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { discG.position.z = z0 + (z1 - z0) * k; }, { mode: 'top', ms: 800, reachMs: 600 }).then(function () {
      st.glass = on; discG.position.z = z1; st.hist = null; st.an = null; S.say(on ? 'Ground glass in the beam and spinning: the light on the counters is pseudo-thermal speckle.' : 'Ground glass out of the beam: the counters see the plain laser light.'); mark(); S.render();
    });
  }
  function integrate(ms, fn) { return S.tween(ms, function (k) { st.prog = k; if (k >= 1) st.prog = 0; mark(); }).then(function () { st.prog = 0; return fn(); }); }
  function needOn() { if (!st.on) { S.say('Switch the instrument on first.'); return true; } return false; }
  function accumulate() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return S.hand.tap(go, 'front').then(function () { return integrate(1200, function () {
      var q = assign(p, { kind: st.glass ? 1 : 0, seed: p.seed + st.idx++ });
      st.hist = KN.hist(q); st.an = null; S.say('Accumulated ' + p.Ts + ' s of coincidences.'); mark(); S.render(); return st.hist;
    }); });
  }
  function analyse() {
    if (!st.hist) { S.say('Accumulate the histogram first.'); return null; }
    st.an = KN.analyse(p, st.hist); st.cur = { src: st.glass ? 'thermal' : 'laser', g2: st.an[0], tc: st.an[1], cinf: st.an[2] };
    S.say('Centre bin over the far bins: g2(0) = ' + r(st.an[0], 3) + (st.an[1] > 0 ? '. The dip fits a coherence time of ' + r(st.an[1] * 1e6, 1) + ' µs.' : '. The histogram is flat: no coherence time to fit.')); mark(); S.render(); return st.cur;
  }
  function setRate(i) {
    if (i < 0 || i >= RATES.length || Kt.busy()) return Promise.resolve();
    var kn = ins.knobs[0], a0 = kn.rotation.z, a1 = 2.3 - 4.6 * i / (RATES.length - 1), pt = Kt.wpt(ins.g, kn.position.x, kn.position.y, ins.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kn.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 450, reachMs: 450 }).then(function () { st.rate = i; kn.rotation.z = a1; st.cur = null; st.counts = null; mark(); S.render(); });
  }
  function countRun() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    var rt = RATES[st.rate], tw = Math.min(p.tw, 400 / rt);
    return S.hand.tap(go, 'front').then(function () { return integrate(900, function () {
      var q = assign(p, { rate: rt, tw: tw, seed: p.seed + 3 * st.idx++ }), s = KN.stream(q), mv = KN.stats(s.counts);
      st.counts = s.counts; st.gaps = s.gaps; st.cur = { rate: rt, tw: tw, mean: mv[0], v: mv[1], fano: mv[0] > 0 ? mv[1] / mv[0] : 0, q: q };
      S.say('Counted ' + s.counts.length + ' windows of ' + si(tw, 's', 2) + ': mean ' + r(mv[0], 2) + ', variance ' + r(mv[1], 2) + '.'); mark(); S.render(); return st.cur;
    }); });
  }
  function gapFit() {                                                        // the interval distribution: ln(number) against gap
    if (!st.cur || !st.gaps) { S.say('Take a count run first.'); return null; }
    var rt = st.cur.rate, g = st.gaps, i, bw = 1 / (rt * 4), bins = [], nb = 16, k, xs = [];
    for (i = 0; i < nb; i++) bins.push(0);
    for (i = 0; i < g.length; i++) { k = Math.floor(g[i] / bw); if (k >= 0 && k < nb) bins[k]++; }
    var pts = []; for (i = 0; i < nb; i++) if (bins[i] > 20) pts.push([(i + 0.5) * bw, Math.log(bins[i])]);
    var f = S.fit.linear(pts); if (!f || f.m >= 0) { S.say('Not enough gaps to fit.'); return null; }
    return { rate_est: -f.m, rate: rt, n: g.length };
  }
  function recordCount() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var c = st.cur; if (!c || !st.counts) { S.say('Press COUNT first.'); return false; }
    if (S.rows.some(function (q) { return q.k === 'cnt' && q.rate === c.rate; })) { S.say('That source position is already in the book.'); return false; }
    S.addRow({ k: 'cnt', rate: c.rate, tw: c.tw, mean: c.mean, v: c.v, fano: c.fano }); return true;
  }
  function recordGap() {
    var g = gapFit(); if (!g) return false; if (S.hand.busy) return false;
    if (S.rows.some(function (q) { return q.k === 'gap'; })) { S.say('The gap histogram is already in the book.'); return false; }
    S.addRow({ k: 'gap', rate: g.rate, est: g.rate_est, n: g.n }); S.say('Gap histogram: ln(number) falls with slope -' + r(g.rate_est, 1) + ' per second.'); return true;
  }
  function recordG2() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var c = st.cur; if (!c || !st.an) { S.say('Work out g2(0) first.'); return false; }
    if (S.rows.some(function (q) { return q.src === c.src; })) { S.say('This source is already in the book.'); return false; }
    S.addRow({ src: c.src, g2: c.g2, tc: c.tc, cinf: c.cinf }); return true;
  }
  function runAnti() {
    if (needOn() || Kt.busy()) return Promise.resolve(null);
    return S.hand.tap(go, 'front').then(function () { return integrate(1400, function () { st.cnt = KN.counts(p); S.say('Run finished: N_G = ' + Math.round(st.cnt[0]) + '.'); mark(); S.render(); return st.cnt; }); });
  }
  function workAlpha() {
    if (!st.cnt) { S.say('Run the counters first.'); return false; }
    if (S.hand.busy) return false; if (S.rows.length) { S.say('Alpha is already worked out.'); return false; }
    var c = st.cnt, a = c[0] * c[3] / (c[1] * c[2]); S.addRow({ NG: c[0], NGT: c[1], NGR: c[2], NGTR: c[3], alpha: a }); S.say('alpha = N_G N_GTR / (N_GT N_GR) = ' + r(a, 4) + (a < 1 ? ': below 1, which no classical field can give.' : '.')); return true;
  }

  // ================================================================ result
  function lowSlope(rows) {
    var rs = rows.filter(function (q) { return q.k === 'cnt' && q.rate * p.td < 0.02; }), sxy = 0, sxx = 0;
    if (rs.length < 4) return null; rs.forEach(function (q) { sxy += q.mean * q.v; sxx += q.mean * q.mean; }); return { m: sxy / sxx, n: rs.length };
  }
  function result(rows) {
    if (MODE === 'g2') {
      var th = rows.filter(function (q) { return q.src === 'thermal'; })[0], ls = rows.filter(function (q) { return q.src === 'laser'; })[0]; if (!th) return null;
      return { label: 'g2(0) of the pseudo-thermal light', value: th.g2, unit: '', digits: 3, truth: HK.TEXTBOOK.phd_g2_zero(assign(p, { kind: 1 })),
        note: 'Coherence time from the dip: ' + r(th.tc * 1e6, 1) + ' µs (the disc speed sets it; true ' + r(p.tc * 1e6, 1) + ' µs). ' + (ls ? 'Laser light alone: g2(0) = ' + r(ls.g2, 3) + ' (no bunching).' : 'Take out the ground glass and repeat to see g2 = 1.') };
    }
    if (MODE === 'poisson') {
      var lo = lowSlope(rows); if (!lo) return null; var hi = rows.filter(function (q) { return q.k === 'cnt' && q.rate * p.td >= 0.05; }).sort(function (a, b) { return b.rate - a.rate; })[0], gp = rows.filter(function (q) { return q.k === 'gap'; })[0];
      return { label: 'Variance ÷ mean at low rates', value: lo.m, unit: '', digits: 2, truth: 1,
        note: 'Slope of variance against mean through the origin for ' + lo.n + ' rates where the counter is hardly ever blind. ' + (hi ? 'At ' + si(hi.rate, 'Hz', 2) + ' the ratio falls to ' + r(hi.fano, 2) + ' (dead time: expect ' + r(1 / Math.pow(1 + hi.rate * p.td, 2), 2) + '). ' : '') + (gp ? 'The gaps fall off as exp(-' + r(gp.est, 0) + ' t) at a source rate of ' + si(gp.rate, 'Hz', 2) + '.' : '') };
    }
    if (!rows.length) return null; var a = rows[0];
    return { label: 'Anticorrelation parameter alpha', value: a.alpha, unit: '', digits: 4, truth: HK.TEXTBOOK.phd_antibunch_alpha(p),
      note: a.alpha < 1 ? 'alpha is well below 1: a classical field would give at least 1, so the light at the beam splitter is nonclassical. A perfect single photon gives 0; the remainder comes from heralds that held two photons.' : 'alpha is not below 1.' };
  }

  // ================================================================ text
  var TXT = {
    g2: { principle: 'The normalised intensity correlation g2(τ) compares the chance of two photons arriving τ apart with the chance for independent arrivals. Chaotic (thermal) light bunches: g2(0) = 2, falling to 1 over the coherence time. A steady laser has g2 = 1 at every delay.',
      formula: 'g2(τ) = ⟨I(t) I(t+τ)⟩ / ⟨I⟩²', note: 'thermal light: g2(0) = 2; laser light: g2 = 1',
      more: ['Each bin holds Poisson-distributed counts; with millions per bin the scatter is a few parts in ten thousand.', 'The coherence time depends on how fast the speckle changes: a faster disc gives a shorter one.', 'Hanbury Brown and Twiss used this in 1956 to measure the sizes of stars.'] },
    poisson: { principle: 'Independent random events at a steady rate follow Poisson statistics: the number in a fixed time has variance equal to its mean, and the gaps between them are exponential. A counter blind for a dead time after each count makes the counts more regular, so at a high rate the variance falls below the mean.',
      formula: 'variance = mean,   gap distribution ∝ exp(−rate · t)', note: 'with dead time td the ratio falls to 1/(1 + rate · td)² at a high rate',
      more: ['A larger mean gives a Gaussian-looking histogram; at a mean of a few counts it is lopsided.', 'Fitting ln(number in a gap bin) against the gap gives a line of slope −rate.', 'Variance equal to mean is the signature that the events are independent.'] },
    anti: { principle: 'A single photon can be detected at one output of a beam splitter or the other, never both. If a heralding detector G signals one photon, the chance of clicks at both T and R should then be zero. A classical wave would give coincidences at least as often as chance.',
      formula: 'α = N_G · N_GTR / (N_GT · N_GR)', note: 'classical light: α ≥ 1; a perfect single photon: α = 0',
      more: ['The three-fold coincidences N_GTR are the heart of it: they are rare, so the run needs hundreds of millions of heralds.', 'A source that sometimes emits two photons at once gives a small but nonzero α.', 'Grangier, Roger and Aspect first showed this in 1986.'] } };
  var BOOK = {
    g2: [{ label: 'Source', get: function (z) { return z.src; } }, { label: 'g2(0)', get: function (z) { return r(z.g2, 3); } }, { label: 'tc (µs)', get: function (z) { return z.tc > 0 ? r(z.tc * 1e6, 1) : '—'; } }, { label: 'Far mean', get: function (z) { return Math.round(z.cinf); } }],
    poisson: [{ label: 'Rate set', get: function (z) { return z.k === 'cnt' ? si(z.rate, 'Hz', 2) : 'gaps ' + si(z.rate, 'Hz', 2); } }, { label: 'Mean', get: function (z) { return z.k === 'cnt' ? r(z.mean, 2) : '—'; } }, { label: 'Variance', get: function (z) { return z.k === 'cnt' ? r(z.v, 2) : '—'; } }, { label: 'Var ÷ mean', get: function (z) { return z.k === 'cnt' ? r(z.fano, 3) : 'slope ' + r(z.est, 1); } }],
    anti: [{ label: 'N_G', get: function (z) { return Math.round(z.NG); } }, { label: 'N_GT', get: function (z) { return Math.round(z.NGT); } }, { label: 'N_GR', get: function (z) { return Math.round(z.NGR); } }, { label: 'N_GTR', get: function (z) { return Math.round(z.NGTR); } }, { label: 'α', get: function (z) { return r(z.alpha, 4); } }] };
  var VIVA = {
    g2: [['Thermal light has g2(0) equal to', ['2', '1', '0'], 0, 'Chaotic light bunches.'], ['A steady laser beam gives g2(τ)', ['1 at every delay', '2 at zero delay', '0 at zero delay'], 0, 'Photon arrivals are independent.'], ['A faster-rotating disc makes the coherence time', ['Shorter', 'Longer', 'The same'], 0, 'The speckle decorrelates sooner.']],
    poisson: [['For Poisson counts the variance equals', ['The mean', 'The mean squared', 'Zero'], 0, 'That is the Poisson law.'], ['A counter\'s dead time makes the variance at a high rate', ['Smaller than the mean', 'Larger than the mean', 'Equal to the mean'], 0, 'The counts are more regular than random.'], ['The gaps between independent random counts are distributed', ['Exponentially', 'Normally', 'Uniformly'], 0, 'The chance of waiting longer decays as exp(−rate t).']],
    anti: [['A perfect single photon at a beam splitter gives α equal to', ['0', '1', '2'], 0, 'It can click only one detector.'], ['Which α rules out any classical wave?', ['Below 1', 'Above 1', 'Exactly 1'], 0, 'A classical field gives α at least 1.'], ['Why is the measured α not exactly zero?', ['Some heralds hold two photons', 'The beam splitter is not 50:50', 'The detectors are slow'], 0, 'Multi-pair events click both detectors.']] };

  // ================================================================ steps
  var STEPS = [{ id: 'on', title: 'Switch on', view: 'ins', render: function (u) {
      u.h2('Switch the instrument on');
      u.p(MODE === 'g2' ? 'The laser is expanded and sent through the beam splitter to two photon counters. The histogrammer starts a clock when counter 1 fires and records the delay to counter 2.' : MODE === 'poisson' ? 'The LED shines on the photon counter. The scaler counts the pulses in equal windows.' : 'A simulated heralded-photon source feeds the heralding counter G and a beam splitter with counters T and R. The coincidence counter records G, G+T, G+R and G+T+R.');
      u.task('Power', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('ins'); powerOn(!st.on); }, !st.on, S.hand.busy));
      u.note(MODE === 'g2' ? 'The laser beam is clamped horizontal, 10 cm above the bench. Never look into it or at a reflection, and block it when you change anything.' : MODE === 'anti' ? 'A real source needs a pump laser and single-photon counters set up by staff. This one is simulated: nothing here is hazardous.' : 'Keep the counter out of direct room light: a photon counter can be damaged by bright light.');
      u.next('Next', st.on); }, ok: function () { return st.on; }, auto: function () { return powerOn(true); } }];
  if (MODE === 'g2') {
    var g2step = function (id, title, wantGlass, lead) { return { id: id, title: title, view: 'optics', render: function (u) {
        u.h2(title); u.p(lead);
        u.task('Ground glass', st.glass === wantGlass, st.glass ? 'In the beam' : 'Out of the beam').add(u.button(wantGlass ? 'Slide the glass into the beam' : 'Slide the glass out', function () { S.focus('optics'); glass(wantGlass); }, st.glass !== wantGlass, S.hand.busy || st.glass === wantGlass));
        u.row(u.button('START (' + p.Ts + ' s)', function () { S.focus('ins'); accumulate(); }, true, S.hand.busy || st.glass !== wantGlass), u.button('Work out g2(0)', function () { analyse(); }, false, !st.hist || S.hand.busy), u.button('Write it down', function () { recordG2(); }, false, !st.an || S.hand.busy));
        u.live(function () { return st.an ? 'g2(0) = ' + r(st.an[0], 3) + (st.an[1] > 0 ? ' · tc = ' + r(st.an[1] * 1e6, 1) + ' µs' : ' · flat') : st.hist ? 'histogram ready' : 'no histogram'; });
        panel(u); u.h3('Observation table'); u.table();
        var have = S.rows.some(function (q) { return q.src === (wantGlass ? 'thermal' : 'laser'); }); u.next(wantGlass ? 'Next: laser light' : 'Next: result', have); },
      ok: function () { return S.rows.some(function (q) { return q.src === (wantGlass ? 'thermal' : 'laser'); }); },
      auto: function () { return glass(wantGlass).then(function () { return accumulate(); }).then(function () { analyse(); recordG2(); }); } }; };
    STEPS.push(g2step('thermal', 'Pseudo-thermal light', true, 'Put the rotating ground glass in the beam. Accumulate the coincidence histogram, divide the centre bin by the mean of the far bins to get g2(0), and note how wide the central peak is.'));
    STEPS.push(g2step('laser', 'Laser light', false, 'Take the ground glass out and repeat. A steady laser has no bunching: the histogram should be flat.'));
  } else if (MODE === 'poisson') {
    STEPS.push({ id: 'counts', title: 'Counts per window', view: 'ins', render: function (u) {
        u.h2('Mean and variance at several rates');
        u.p('Move the source along the rail (the knob sets eight positions, dim to bright). At each, press COUNT: the scaler takes 1000 windows. Write down the mean and the variance of the counts per window. At least six positions, including the brightest.');
        for (var i = 0; i < RATES.length; i += 4) u.row.apply(u, RATES.slice(i, i + 4).map(function (v, j) { var k = i + j; return u.button('Position ' + (k + 1), function () { S.focus('ins'); setRate(k); }, st.rate === k, S.hand.busy); }));
        u.row(u.button('COUNT', function () { S.focus('ins'); countRun(); }, true, S.hand.busy), u.button('Write it down', function () { recordCount(); }, false, !st.counts || S.hand.busy));
        u.live(function () { return 'position ' + (st.rate + 1) + ' · ' + (st.cur ? 'mean ' + r(st.cur.mean, 2) + ' · variance ' + r(st.cur.v, 2) : 'no run'); });
        panel(u); u.h3('Observation table'); u.table();
        var nc = S.rows.filter(function (q) { return q.k === 'cnt'; }).length; if (nc < 6) u.p(nc + ' of at least 6 positions.'); u.next('Next: the gaps', nc >= 6); },
      ok: function () { return S.rows.filter(function (q) { return q.k === 'cnt'; }).length >= 6; },
      auto: function () { var c = Promise.resolve(), j; for (j = 0; j < RATES.length; j++) (function (jj) { c = c.then(function () { return setRate(jj); }).then(function () { return countRun(); }).then(function () { recordCount(); }); })(j); return c; } });
    STEPS.push({ id: 'gaps', title: 'Gaps between counts', view: 'ins', render: function (u) {
        u.h2('The interval distribution');
        u.p('Set the source to position 3 (about 100 counts a second) and take a run. The scaler also timed the gap between successive counts: press the button to histogram them and fit ln(number) against the gap.');
        u.row(u.button('Position 3', function () { setRate(2); }, st.rate === 2, S.hand.busy), u.button('COUNT', function () { S.focus('ins'); countRun(); }, true, S.hand.busy || st.rate !== 2), u.button('Histogram the gaps and write the slope down', function () { recordGap(); }, false, !st.counts || S.hand.busy));
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.some(function (q) { return q.k === 'gap'; })); },
      ok: function () { return S.rows.some(function (q) { return q.k === 'gap'; }); },
      auto: function () { return setRate(2).then(function () { return countRun(); }).then(function () { recordGap(); }); } });
  } else {
    STEPS.push({ id: 'run', title: 'Count the heralds', view: 'ins', render: function (u) {
        u.h2('Run the counters');
        u.p('Press START. The counters run for the whole run and then show four numbers: heralds N_G, heralds with a click at T, at R, and heralds with clicks at both T and R.');
        u.row(u.button('START', function () { S.focus('ins'); runAnti(); }, true, S.hand.busy), u.button('Work out α and write it down', function () { workAlpha(); }, false, !st.cnt || S.hand.busy));
        u.formula('α = N_G · N_GTR / (N_GT · N_GR)', 'below 1 means the light cannot be a classical wave');
        u.live(function () { return st.cnt ? 'N_G ' + Math.round(st.cnt[0]) + ' · N_GT ' + Math.round(st.cnt[1]) + ' · N_GR ' + Math.round(st.cnt[2]) + ' · N_GTR ' + Math.round(st.cnt[3]) : 'no run'; });
        panel(u); u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.length >= 1); },
      ok: function () { return S.rows.length >= 1; },
      auto: function () { return runAnti().then(function () { workAlpha(); }); } });
  }

  function askState() {
    var q = { experiment: S.lab.title, sample: V_.sample || '', power_on: st.on, readings: S.rows.length };
    if (MODE === 'g2') { q.ground_glass_in = st.glass; q.accumulation_s = p.Ts; q.bin_width_us = p.bw * 1e6; q.rate_per_counter_Hz = p.R1; }
    if (MODE === 'poisson') { q.source_position = st.rate + 1; q.dead_time_us = p.td * 1e6; if (st.cur) { q.last_mean = r(st.cur.mean, 2); q.last_variance = r(st.cur.v, 2); } }
    if (MODE === 'anti') { q.detector_efficiency = p.eta; if (st.cnt) q.counts = st.cnt.map(Math.round); }
    return q;
  }
  var tx = TXT[MODE];
  return {
    camera: { pos: [-0.14, 0.62, 1.2], look: [-0.14, 0.06, -0.22] },
    views: { optics: [[-0.28, 0.4, 0.28], [-0.25, 0.08, -0.24]], ins: [[0.2, 0.37, 0.48], [0.22, 0.1, -0.24]], bench: [[-0.14, 0.62, 1.2], [-0.14, 0.06, -0.22]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: tx.principle, formula: tx.formula, formulaNote: tx.note, more: tx.more,
      precautions: MODE === 'g2' ? 'Class 2 laser: beam horizontal at bench height, never look into it or at a reflection, keep the counters out of room light.' : MODE === 'anti' ? 'A simulated instrument: in a real lab the pump laser is enclosed and the detectors are interlocked. ' : 'Do not shine bright light on a photon counter.' },
    book: { title: 'Expt. - ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 74), V_.sample ? 'Sample: ' + V_.sample.slice(0, 50) : '', MODE === 'anti' ? 'Simulated heralded source.' : 'Counts from the instrument.'], columns: BOOK[MODE] },
    result: result, tol: MODE === 'g2' ? 0.03 : MODE === 'poisson' ? 0.12 : 0.03,
    resultNote: 'Counts are random, so the agreement is limited by the statistics: more counts, a closer value.',
    chips: ['What does g2 mean?', 'How many counts do I need?', 'What is dead time?', 'Check my readings', 'Why does the variance equal the mean?'],
    viva: VIVA[MODE], askState: askState, steps: STEPS,
    tick: function (dt) { if (discG && st.on && st.glass) disc.rotation.y += 5 * (dt || 0.016); hudA.set(st.on ? 'On' : 'Off'); hudB.set(MODE === 'g2' ? (st.glass ? 'Pseudo-thermal' : 'Laser') : MODE === 'poisson' ? 'Position ' + (st.rate + 1) : (st.cnt ? 'Done' : 'Not run')); hudC.set(S.rows.length + ' written');
      if (dirty) { dirty = false; paint(); paintPanel(); } },
    ready: function () { paint(); }
  };
});
