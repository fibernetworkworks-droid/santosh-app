/* Prayogshala studio module: SIGNAL BENCH (M.Sc. electronics): feedback oscillators and filters.
   A dual +-12 V supply, a function generator, a solderless breadboard carrying the real parts (resistors with colour
   bands, capacitors, inductors, the op-amp or transistor) and an oscilloscope with two channels.
   Physics: the lab's own kernel - `msc_osc` (RC phase-shift, Wien-bridge, Colpitts and Hartley oscillators: the
   oscillation frequency and the minimum gain are found by scanning the feedback network's phase) or `msc_filt`
   (Sallen-Key low and high pass, band pass, all-pass, passive RC) of packs/msc_elec.js. The scope traces are sampled
   from the kernel's response; the period, the peak-to-peak voltages and the phase are measured on those traces, the
   way the scope's own cursors do - nothing is read back from a formula. Low voltages only. */
HoolaStudio.define('msc-signal-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, KIND = Math.round(p.kind), IS_OSC = KERN === 'msc_osc';
  var st = { on: false, gen: false, A: 1.0, f: 1000, vin: 1.0, trace: null, meas: null, dirty: true };
  var dirty = true;
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function r(v, d) { var k = Math.pow(10, d === undefined ? 2 : d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function fmtR(v) { return v >= 1e6 ? r(v / 1e6, 2) + ' MΩ' : v >= 1e3 ? r(v / 1e3, 2) + ' kΩ' : r(v, 1) + ' Ω'; }
  function fmtC(v) { return v >= 1e-6 ? r(v * 1e6, 2) + ' µF' : v >= 1e-9 ? r(v * 1e9, 2) + ' nF' : r(v * 1e12, 1) + ' pF'; }
  function fmtL(v) { return v >= 1 ? r(v, 2) + ' H' : v >= 1e-3 ? r(v * 1e3, 2) + ' mH' : r(v * 1e6, 1) + ' µH'; }
  function fmtF(f) { return f >= 1e6 ? r(f / 1e6, 3) + ' MHz' : f >= 1e3 ? r(f / 1e3, 3) + ' kHz' : r(f, 1) + ' Hz'; }
  var OSCNAME = ['RC phase-shift oscillator', 'Wien-bridge oscillator', 'Colpitts oscillator', 'Hartley oscillator'];
  var FILTNAME = ['Sallen-Key low-pass filter', 'Sallen-Key high-pass filter', 'Band-pass filter (high-pass then low-pass)', 'All-pass phase shifter', 'Passive RC low-pass filter', 'Passive RC high-pass filter'];

  // ---------------------------------------------------------------- what the scope shows
  function qNow() { return IS_OSC ? assign(p, { A: st.A }) : assign(p, { f: st.f }); }
  function osc() { return KN.solve(qNow()); }                          // [w0, amin]
  function makeTrace() {
    var q = qNow(), n = 2400, i, a = [], b = [], t, per, span;
    if (IS_OSC) {
      var s = KN.solve(q); per = 2 * Math.PI / s[0]; span = per * 4; var amp = KN.amplitude(q);
      for (i = 0; i < n; i++) { t = span * i / (n - 1); a.push(amp * Math.sin(s[0] * t)); }
      return { t0: 0, span: span, a: a, b: null, amp: amp, per: per };
    }
    per = 1 / st.f; span = per * 4; var h = KN.h(q, st.f), ph = h[1] * Math.PI / 180;
    for (i = 0; i < n; i++) { t = span * i / (n - 1); a.push(st.vin / 2 * Math.sin(2 * Math.PI * st.f * t)); b.push(st.vin / 2 * h[0] * Math.sin(2 * Math.PI * st.f * t + ph)); }
    return { t0: 0, span: span, a: a, b: b, per: per };
  }
  function crossings(y, span) {                                           // rising zero crossings, interpolated
    var n = y.length, out = [], i; for (i = 1; i < n; i++) if (y[i - 1] < 0 && y[i] >= 0) out.push((i - 1 + (0 - y[i - 1]) / (y[i] - y[i - 1])) * span / (n - 1)); return out;
  }
  function measureTrace(tr) {
    var cr = crossings(tr.a, tr.span), res = {}, i; if (cr.length >= 2) res.T = (cr[cr.length - 1] - cr[0]) / (cr.length - 1);
    res.vppA = Math.max.apply(null, tr.a) - Math.min.apply(null, tr.a);
    if (tr.b) { res.vppB = Math.max.apply(null, tr.b) - Math.min.apply(null, tr.b); var cb = crossings(tr.b, tr.span); if (cr.length && cb.length && res.T) { var d = cb[0] - cr[0]; if (cb[0] < cr[0] && cb.length > 1) d = cb[1] - cr[0]; var ph = -(d / res.T) * 360; while (ph > 180) ph -= 360; while (ph < -180) ph += 360; res.phase = ph; } }
    return res;
  }

  // ---------------------------------------------------------------- the bench
  var wood = S.rounded(1.5, 0.7, 0.01, 0.004, M.darkWood);
  var gen = new T.Group(); S.scene.add(gen); gen.position.set(-0.46, 0, -0.26);
  var GW = 0.26, GH = 0.1, GD = 0.22;
  var gcase = S.rounded(GW, GD, GH, 0.01, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); gcase.rotation.x = -Math.PI / 2; gcase.position.y = GH / 2 + 0.004; gen.add(gcase);
  var GFZ = GD / 2 + 0.0062, gTex = S.canvasTex(900, 360, function (x, w, h) { x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.textAlign = 'center'; x.font = '700 40px "Public Sans", sans-serif'; x.fillText(IS_OSC ? 'DC SUPPLY  ± 12 V' : 'FUNCTION GENERATOR', w / 2, 62);
    x.font = '500 26px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText(IS_OSC ? 'dual regulated · 100 mA' : 'SINE · 1 Hz - 1 MHz · OUTPUT 50 Ω', w / 2, 100); x.font = '700 28px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8';
    x.fillText(IS_OSC ? 'ON / OFF' : 'FREQUENCY', w * 0.3, h - 30); x.fillText(IS_OSC ? '' : 'OUTPUT', w * 0.75, h - 30); });
  var gfac = S.mesh(new T.BoxGeometry(GW - 0.014, GH - 0.014, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: gTex, roughness: 0.45 }), M.grey]); gfac.position.set(0, 0.004 + GH / 2, GFZ - 0.002); gen.add(gfac);
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  function makeKnob(parent, u, v, z0, rad) { var kg = new T.Group(); kg.position.set(u, v, z0); parent.add(kg);
    var sk = S.mesh(new T.CylinderGeometry(rad * 1.3, rad * 1.38, 0.004, 36), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; kg.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(rad, rad * 1.1, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; kg.add(kb);
    var kp = S.mesh(new T.BoxGeometry(0.002, rad * 1.1, 0.0012), M.white, false); kp.position.set(0, rad * 0.65, 0.0215); kg.add(kp); return kg; }
  var gKnob = makeKnob(gen, -0.05, 0.004 + GH / 2 - 0.012, GFZ, 0.014), gSw = makeKnob(gen, IS_OSC ? -0.05 : 0.06, 0.004 + GH / 2 - 0.012, GFZ, 0.009);
  function fAngle(f) { return 3 * Math.PI / 4 - 1.5 * Math.PI * (Math.log(f / 1) / Math.log(1e6)); }
  gKnob.rotation.z = IS_OSC ? 2.0 : fAngle(st.f); gSw.rotation.z = 2.3;
  var gLed = S.mesh(new T.SphereGeometry(0.005, 14, 14), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); gLed.position.set(IS_OSC ? 0.05 : 0.06, 0.004 + GH / 2 + 0.03, GFZ + 0.002); gen.add(gLed);
  S.contact(0.34, 0.3, -0.46, -0.26, 0.5);
  // breadboard and parts
  var bb = new T.Group(); S.scene.add(bb); bb.position.set(-0.02, 0, -0.16);
  var bbase = S.rounded(0.42, 0.26, 0.018, 0.004, new T.MeshStandardMaterial({ color: 0xf2f0ea, roughness: 0.6 })); bbase.rotation.x = -Math.PI / 2; bbase.position.y = 0.009; bb.add(bbase);
  var holes = S.canvasTex(1024, 640, function (x, w, h) { x.fillStyle = '#f2f0ea'; x.fillRect(0, 0, w, h); x.fillStyle = '#b8b6ae';
    for (var i = 0; i < 64; i++) for (var j = 0; j < 40; j++) { if (j > 15 && j < 24) continue; x.fillRect(10 + i * 15.6, 10 + j * 15.2, 5, 5); }
    x.fillStyle = '#d9d7cf'; x.fillRect(0, 15 * 15.2 + 22, w, 8 * 15.2 - 8); x.fillStyle = '#c33'; x.fillRect(0, 4, w, 3); x.fillStyle = '#26c'; x.fillRect(0, h - 8, w, 3); });
  var btop = new T.Mesh(new T.PlaneGeometry(0.4, 0.25), new T.MeshStandardMaterial({ map: holes, roughness: 0.6 })); btop.rotation.x = -Math.PI / 2; btop.position.y = 0.0185; bb.add(btop);
  var bands = [0x000000, 0x6b3a1a, 0xc0392b, 0xe67e22, 0xf1c40f, 0x27ae60, 0x2980b9, 0x8e44ad, 0x888888, 0xffffff];
  function resistor(x, z, ang, val) {
    var g = new T.Group(); g.position.set(x, 0.027, z); g.rotation.y = ang; bb.add(g);
    var body = S.mesh(new T.CylinderGeometry(0.0034, 0.0034, 0.022, 14), new T.MeshStandardMaterial({ color: 0xd9c08c, roughness: 0.6 })); body.rotation.z = Math.PI / 2; g.add(body);
    var mant = val, ex = 0; while (mant >= 100) { mant /= 10; ex++; } while (mant < 10) { mant *= 10; ex--; }
    var d1 = Math.floor(mant / 10) % 10, d2 = Math.round(mant) % 10; [d1, d2, Math.max(0, Math.min(9, ex + 0))].forEach(function (d, i) { var rg = S.mesh(new T.CylinderGeometry(0.00355, 0.00355, 0.0018, 14), new T.MeshStandardMaterial({ color: bands[d] })); rg.rotation.z = Math.PI / 2; rg.position.x = -0.007 + i * 0.0045; g.add(rg); });
    [-1, 1].forEach(function (sg) { var lead = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.013, 8), M.chrome); lead.rotation.z = Math.PI / 2; lead.position.set(sg * 0.0165, -0.0, 0); g.add(lead); var pin = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.014, 8), M.chrome); pin.position.set(sg * 0.0225, -0.007, 0); g.add(pin); });
    return g;
  }
  function capacitor(x, z, big) {
    var g = new T.Group(); g.position.set(x, 0.0, z); bb.add(g);
    var body = big ? S.mesh(new T.BoxGeometry(0.014, 0.014, 0.006), new T.MeshStandardMaterial({ color: 0xd9822b, roughness: 0.5 })) : S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.003, 20), new T.MeshStandardMaterial({ color: 0xc9792e, roughness: 0.5 }));
    body.position.set(0, 0.029, 0); if (!big) body.rotation.x = Math.PI / 2; g.add(body);
    [-1, 1].forEach(function (sg) { var pin = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.014, 8), M.chrome); pin.position.set(sg * 0.0025, 0.021, 0); g.add(pin); });
    return g;
  }
  function inductor(x, z) {
    var g = new T.Group(); g.position.set(x, 0.03, z); bb.add(g);
    var core = S.mesh(new T.TorusGeometry(0.009, 0.0045, 12, 24), new T.MeshStandardMaterial({ color: 0x2f6fb3, roughness: 0.45 })); core.rotation.x = Math.PI / 2; g.add(core);
    [-1, 1].forEach(function (sg) { var pin = S.mesh(new T.CylinderGeometry(0.0006, 0.0006, 0.02, 8), M.chrome); pin.position.set(sg * 0.007, -0.01, 0.007); g.add(pin); }); return g;
  }
  function dip(x, z, name) {
    var g = new T.Group(); g.position.set(x, 0.025, z); bb.add(g);
    var body = S.mesh(new T.BoxGeometry(0.019, 0.0045, 0.0095), new T.MeshStandardMaterial({ color: 0x151515, roughness: 0.4 })); g.add(body);
    var lb = S.label(name, { w: 0.017, ratio: 0.3, color: '#cfcfcf', px: 256 }); lb.rotation.x = -Math.PI / 2; lb.position.y = 0.0025; g.add(lb);
    for (var i = 0; i < 4; i++) [-1, 1].forEach(function (sg) { var pn = S.mesh(new T.BoxGeometry(0.0012, 0.003, 0.0012), M.chrome); pn.position.set(-0.0075 + i * 0.005, -0.002, sg * 0.0055); g.add(pn); });
    return g;
  }
  function label(txt, x, z) { var lb = S.label(txt, { w: 0.05, ratio: 0.22, color: '#1b1b1b', px: 256 }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, 0.0193, z); bb.add(lb); }
  var partsG = [];
  if (IS_OSC && KIND === 0) { [-0.14, -0.08, -0.02].forEach(function (x) { resistor(x, -0.065, 0, p.R); capacitor(x + 0.03, -0.02, false); }); label(fmtR(p.R) + ' ×3', -0.08, -0.095); label(fmtC(p.C) + ' ×3', -0.05, 0.0); dip(0.09, -0.06, 'TL082'); }
  else if (IS_OSC && KIND === 1) { resistor(-0.12, -0.065, 0, p.R); resistor(-0.12, 0.0, 0, p.R); capacitor(-0.06, -0.065, false); capacitor(-0.06, 0.0, false); label(fmtR(p.R) + ' ×2', -0.12, -0.095); label(fmtC(p.C) + ' ×2', -0.06, -0.095); dip(0.09, -0.06, 'LM741'); }
  else if (IS_OSC && KIND === 2) { inductor(-0.13, -0.05); capacitor(-0.06, -0.05, true); capacitor(-0.02, -0.05, true); label(fmtL(p.L), -0.13, -0.085); label('C1 ' + fmtC(p.C), -0.06, -0.085); label('C2 ' + fmtC(p.C2), -0.02, -0.085); dip(0.09, -0.06, '2N3904'); }
  else if (IS_OSC) { inductor(-0.13, -0.05); inductor(-0.09, -0.05); capacitor(-0.04, -0.05, true); label('L1 ' + fmtL(p.L), -0.13, -0.085); label('L2 ' + fmtL(p.L2), -0.09, -0.012); label(fmtC(p.C), -0.04, -0.085); dip(0.09, -0.06, '2N3904'); }
  else { resistor(-0.13, -0.065, 0, p.R); capacitor(-0.08, -0.05, false); label(fmtR(p.R), -0.13, -0.095); label(fmtC(p.C), -0.08, -0.095);
    if (KIND === 2) { resistor(-0.02, -0.065, 0, p.R2); capacitor(0.03, -0.05, false); label(fmtR(p.R2), -0.02, -0.095); label(fmtC(p.C2), 0.03, -0.095); }
    if (KIND <= 3) { resistor(-0.13, 0.0, 0, p.R); capacitor(-0.08, 0.0, false); dip(0.1, -0.06, 'LM741'); } }
  // the gain pot
  var potG = new T.Group(); bb.add(potG); potG.position.set(0.14, 0.03, 0.05); potG.visible = IS_OSC;
  var potB = S.mesh(new T.BoxGeometry(0.02, 0.02, 0.02), new T.MeshStandardMaterial({ color: 0x2f6fb3, roughness: 0.5 })); potG.add(potB);
  var potK = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.01, 20), new T.MeshStandardMaterial({ map: knurl })); potK.position.y = 0.014; potG.add(potK);
  var potI = S.mesh(new T.BoxGeometry(0.0018, 0.002, 0.007), M.white, false); potI.position.set(0, 0.02, 0.0035); potG.add(potI);
  function potAngle(A) { return -2.4 + 4.8 * Math.min(1, Math.max(0, (Math.log(A) / Math.log(60)))); }
  potG.rotation.y = potAngle(st.A);
  // two binding posts on the front of the supply / generator, and leads to the breadboard
  [[0.09, 'red'], [0.115, 'black']].forEach(function (pq) {
    var bp = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.012, 16), new T.MeshStandardMaterial({ color: pq[1] === 'red' ? 0xc0392b : 0x1b1b1b, roughness: 0.4 })); bp.rotation.x = Math.PI / 2; bp.position.set(pq[0], 0.004 + GH / 2 - 0.02, GFZ + 0.006); gen.add(bp);
    var tp = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.004, 14), M.chrome); tp.rotation.x = Math.PI / 2; tp.position.set(pq[0], 0.004 + GH / 2 - 0.02, GFZ + 0.013); gen.add(tp);
  });
  S.wire([[-0.46 + 0.09, 0.034, -0.26 + GFZ + 0.013], [-0.3, 0.012, -0.08], [-0.2, 0.012, -0.05], [-0.14, 0.03, -0.12]], 'red');
  S.wire([[-0.46 + 0.115, 0.034, -0.26 + GFZ + 0.013], [-0.3, 0.012, -0.03], [-0.19, 0.012, 0.0], [-0.13, 0.03, -0.07]], 'black');
  S.contact(0.5, 0.32, -0.02, -0.16, 0.4);
  // oscilloscope
  var sco = new T.Group(); S.scene.add(sco); sco.position.set(0.3, 0, -0.26); sco.rotation.y = -0.18;
  var scase = S.rounded(0.32, 0.26, 0.22, 0.012, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); scase.rotation.x = -Math.PI / 2; scase.position.y = 0.114; sco.add(scase);
  var bez = S.mesh(new T.BoxGeometry(0.22, 0.17, 0.006), M.grey); bez.position.set(-0.03, 0.14, 0.131); sco.add(bez);
  var scrTex = S.liveTex(1024, 760), scr = new T.Mesh(new T.PlaneGeometry(0.2, 0.2 * 760 / 1024), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scr.position.set(-0.03, 0.14, 0.1345); sco.add(scr);
  var sk1 = makeKnob(sco, 0.115, 0.17, 0.1315, 0.013), sk2 = makeKnob(sco, 0.115, 0.1, 0.1315, 0.013);
  var sLbl = S.label('OSCILLOSCOPE · 2 CH', { w: 0.1, ratio: 0.1, color: '#1b1b1b' }); sLbl.position.set(-0.03, 0.235, 0.1315); sco.add(sLbl);
  S.contact(0.4, 0.34, 0.3, -0.26, 0.5);
  var CHAN = IS_OSC ? 1 : 2;
  function drawScope(x, w, h) {
    x.fillStyle = '#06130c'; x.fillRect(0, 0, w, h); var PL = 10, PT = 10, W = w - 20, H = h - 20, i;
    x.strokeStyle = 'rgba(120,220,150,.2)'; x.lineWidth = 1;
    for (i = 0; i <= 10; i++) { x.beginPath(); x.moveTo(PL + W * i / 10, PT); x.lineTo(PL + W * i / 10, PT + H); x.stroke(); } for (i = 0; i <= 8; i++) { x.beginPath(); x.moveTo(PL, PT + H * i / 8); x.lineTo(PL + W, PT + H * i / 8); x.stroke(); }
    x.strokeStyle = 'rgba(120,220,150,.45)'; x.beginPath(); x.moveTo(PL, PT + H / 2); x.lineTo(PL + W, PT + H / 2); x.stroke();
    var tr = st.trace; if (!tr) { x.fillStyle = '#5aa77a'; x.font = '26px "JetBrains Mono", monospace'; x.textAlign = 'center'; x.fillText(st.on ? 'no signal' : 'power off', w / 2, h / 2); return; }
    var peak = IS_OSC ? Math.max(1, Math.max.apply(null, tr.a.map(Math.abs))) : Math.max(0.5, st.vin * 0.55, tr.b ? Math.max.apply(null, tr.b.map(Math.abs)) : 0), vdiv = peak / 3, n = tr.a.length;
    function plot(y, col) { x.strokeStyle = col; x.lineWidth = 2.4; x.beginPath(); for (var k = 0; k < n; k++) { var px = PL + W * k / (n - 1), py = PT + H / 2 - (y[k] / vdiv) * (H / 8); if (k) x.lineTo(px, py); else x.moveTo(px, py); } x.stroke(); }
    plot(tr.a, '#ffe45e'); if (tr.b) plot(tr.b, '#64e3ff');
    x.fillStyle = '#9fe0b8'; x.font = '22px "JetBrains Mono", monospace'; x.textAlign = 'left';
    x.fillText('time ' + fmtT(tr.span / 10) + '/div    ' + (IS_OSC ? 'CH1 ' : 'CH1 ') + r(vdiv, 2) + ' V/div', PL + 6, h - 14);
  }
  function fmtT(s) { return s >= 1e-3 ? r(s * 1e3, 3) + ' ms' : s >= 1e-6 ? r(s * 1e6, 2) + ' µs' : r(s * 1e9, 1) + ' ns'; }
  function paintScope() { scrTex.draw(function (x, w, h) { drawScope(x, w, h); }); }
  var scopeCv = null;
  function paintPanel() { if (scopeCv && scopeCv.isConnected) drawScope(scopeCv.getContext('2d'), scopeCv.width, scopeCv.height); }
  S.addApparatus('gen', gen, IS_OSC ? 'Dual ±12 V supply' : 'Function generator', IS_OSC ? 'Powers the amplifier. The op-amp or transistor needs both rails; a wrong connection destroys it.' : 'Gives a sine wave of the frequency set on its dial, at a fixed amplitude.');
  S.addApparatus('bb', bb, 'Breadboard with the circuit', 'The parts are on a solderless breadboard: resistors with their colour bands, capacitors, ' + (IS_OSC && KIND >= 2 ? 'inductors and a transistor' : 'and an op-amp') + '. The values are printed beside them.');
  S.addApparatus('scope', sco, 'Oscilloscope', 'Shows the signals against time. The period is read from successive crossings of the zero line, the amplitude from the peak-to-peak height.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard(IS_OSC ? 'Gain A' : 'Frequency'), hudB = S.hudCard(IS_OSC ? 'Amplitude' : 'Output'), hudC = S.hudCard('Readings');

  // ---------------------------------------------------------------- actions
  function powerOn(on) {
    if (busy()) return Promise.resolve(); if (st.on === on) return Promise.resolve();
    var pt = wpt(gen, IS_OSC ? -0.05 : 0.06, 0.004 + GH / 2 - 0.012, GFZ + 0.024), a0 = on ? 2.3 : -0.9, a1 = on ? -0.9 : 2.3;
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { gSw.rotation.z = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 650, reachMs: 600 }).then(function () {
      st.on = on; gSw.rotation.z = a1; gLed.material.emissive.setHex(on ? 0x22cc44 : 0); gLed.material.color.setHex(on ? 0x33dd55 : 0x331111);
      if (!on) { st.trace = null; st.meas = null; } else refresh(); dirty = true; S.say(on ? (IS_OSC ? 'Supply on: ±12 V to the amplifier. The gain pot is at its lowest setting.' : 'Generator on, ' + fmtF(st.f) + ', ' + st.vin + ' V peak to peak.') : 'Switched off.'); S.render(); });
  }
  function refresh() { st.trace = st.on ? makeTrace() : null; st.meas = null; dirty = true; }
  function setGain(A, animate) {
    if (!isFinite(A) || A < 1 || A > 60) { S.say('The gain pot goes from 1 to 60.'); return Promise.resolve(); }
    var a0 = st.A;
    function apply(v) { st.A = v; potG.rotation.y = potAngle(v); refresh(); }
    if (animate === false || S.hand.busy) { apply(A); return Promise.resolve(); }
    var pt = wpt(potG, 0, 0.026, 0); return S.hand.pinchMove(pt, function () { return pt; }, function (k) { apply(a0 + (A - a0) * k); }, { mode: 'top', ms: 600, reachMs: 600 }).then(function () { apply(A); });
  }
  function setFreq(f, animate) {
    if (!isFinite(f) || f < 1 || f > 1e6) { S.say('The generator goes from 1 Hz to 1 MHz.'); return Promise.resolve(); }
    var f0 = st.f;
    function apply(v) { st.f = v; gKnob.rotation.z = fAngle(v); refresh(); }
    if (animate === false || S.hand.busy) { apply(f); return Promise.resolve(); }
    var pt = wpt(gen, -0.05, 0.004 + GH / 2 - 0.012, GFZ + 0.024); return S.hand.pinchMove(pt, function () { return pt; }, function (k) { apply(Math.exp(Math.log(f0) + (Math.log(f) - Math.log(f0)) * k)); }, { mode: 'front', ms: 500, reachMs: 500 }).then(function () { apply(f); });
  }
  function raiseGain() {                                              // turn the pot up until the output just starts
    if (!st.on) { S.say('Switch the supply on first.'); return Promise.resolve(null); }
    var A = 1, am = KN.solve(assign(p, { A: 1 }))[1], found = null, q = 1;
    for (A = 1; A <= 60; A += 0.05) { if (KN.amplitude(assign(p, { A: A })) > 0.02) { found = A; break; } }
    if (found === null) { S.say('Even at full gain the circuit does not oscillate.'); return Promise.resolve(null); }
    return setGain(found).then(function () { S.say('Oscillation just starts at a gain of about ' + r(found, 2) + '.'); S.render(); return found; });
  }
  function measureNow() {
    if (!st.on || !st.trace) { S.say('Switch on first.'); return null; }
    var m = measureTrace(st.trace); if (IS_OSC && !(m.T > 0)) { S.say('No oscillation to measure: raise the gain.'); return null; }
    st.meas = m; S.say(IS_OSC ? 'Scope: period ' + fmtT(m.T) + ', amplitude ' + r(m.vppA / 2, 2) + ' V.' : 'Scope: input ' + r(m.vppA, 3) + ' V pp, output ' + r(m.vppB, 3) + ' V pp, phase ' + (m.phase !== undefined ? r(m.phase, 1) : '?') + '°.');
    S.render(); return m;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    var m = st.meas; if (!m) { S.say('Measure on the scope first.'); return false; }
    if (IS_OSC) { if (S.rows.some(function (rw) { return Math.abs(rw.A - st.A) < 0.05; })) { S.say('A reading at this gain is already in the book.'); return false; }
      S.addRow({ A: r(st.A, 2), T: m.T, f: 1 / m.T, vo: m.vppA / 2 }); return true; }
    if (S.rows.some(function (rw) { return Math.abs(Math.log(rw.f / st.f)) < 1e-4; })) { S.say('A reading at ' + fmtF(st.f) + ' is already in the book.'); return false; }
    S.addRow({ f: st.f, vin: m.vppA, vout: m.vppB, g: m.vppB / m.vppA, db: 20 * Math.log(m.vppB / m.vppA) / Math.LN10, ph: m.phase === undefined ? 0 : m.phase }); return true;
  }
  function corner(rows) {                                             // the -3 dB (or -90 degree) frequency, interpolated on the readings
    var rs = rows.slice().sort(function (a, b) { return a.f - b.f; }), i, n = rs.length; if (n < 6) return null;
    function interp(y0, y1, x0, x1, y) { return Math.exp(Math.log(x0) + (Math.log(x1) - Math.log(x0)) * (y - y0) / (y1 - y0)); }
    if (KIND === 3) { for (i = 1; i < n; i++) if (rs[i - 1].ph > -90 && rs[i].ph <= -90) return interp(rs[i - 1].ph, rs[i].ph, rs[i - 1].f, rs[i].f, -90); return null; }
    var h0, lowSide = KIND === 1 || KIND === 5 || KIND === 2;
    if (KIND === 0 || KIND === 4) h0 = Math.max(rs[0].g, rs[1].g); else if (KIND === 1 || KIND === 5) h0 = Math.max(rs[n - 1].g, rs[n - 2].g); else h0 = Math.max.apply(null, rs.map(function (z) { return z.g; }));
    var tgt = h0 / Math.sqrt(2);
    if (lowSide) { for (i = 1; i < n; i++) if (rs[i - 1].g < tgt && rs[i].g >= tgt) return interp(rs[i - 1].g, rs[i].g, rs[i - 1].f, rs[i].f, tgt); }
    else { for (i = 1; i < n; i++) if (rs[i - 1].g > tgt && rs[i].g <= tgt) return interp(rs[i - 1].g, rs[i].g, rs[i - 1].f, rs[i].f, tgt); }
    return null;
  }
  function truthF() { return HK.TEXTBOOK[IS_OSC ? 'msc_osc_f' : 'msc_filt_fc'](p); }
  function result(rows) {
    if (IS_OSC) { if (!rows.length) return null; var fs = rows.map(function (z) { return z.f; }); var am = KN.solve(assign(p, { A: 1 }))[1];
      return { label: 'Frequency of oscillation', value: S.fit.mean(fs), unit: 'Hz', digits: 1, truth: truthF(), note: 'Oscillation starts at a gain of about ' + (rows.length ? r(Math.min.apply(null, rows.map(function (z) { return z.A; })), 1) : '') + ' (the circuit needs a gain of at least ' + r(am, 2) + '); the frequency does not depend on the gain.' }; }
    var fc = corner(rows); if (fc === null) return null;
    return { label: KIND === 3 ? 'Frequency of the -90° phase shift' : KIND === 2 ? 'Lower -3 dB frequency' : '-3 dB cut-off frequency', value: fc, unit: 'Hz', digits: 1, truth: truthF(), note: 'Interpolated between the two readings that bracket ' + (KIND === 3 ? '-90°' : '-3 dB') + ' on a ' + rows.length + '-point sweep.' };
  }
  var NAME = IS_OSC ? OSCNAME[KIND] : FILTNAME[KIND];
  var OPRIN = 'A feedback oscillator is an amplifier whose output is fed back through a frequency-selective network. It oscillates at the frequency where the loop phase is zero, provided the amplifier gain is at least the loss of the network at that frequency (the Barkhausen criterion).';
  var FPRIN = 'A filter passes some frequencies and rejects others. The cut-off is where the gain has fallen to 1/\u221a2 (-3 dB) of its passband value; beyond it the gain falls by 20 dB per decade for each order of the filter.';
  var OF = [['f = 1 / (2\u03c0\u221a6 RC),  A \u2265 29', 'three RC sections give 60\u00b0 each at one frequency; the inverting amplifier supplies the other 180\u00b0'], ['f = 1 / (2\u03c0 RC),  A \u2265 3', 'a Wien bridge with equal R and C: zero phase at \u03c9RC = 1'],
    ['f = 1 / (2\u03c0 \u221a(L C\u2081C\u2082 / (C\u2081 + C\u2082))),  A \u2265 C\u2082/C\u2081', 'the tank is L with C\u2081 and C\u2082 in series'], ['f = 1 / (2\u03c0 \u221a((L\u2081 + L\u2082 + 2M) C)),  A \u2265 L\u2082/L\u2081', 'the tank is C across L\u2081 and L\u2082 in series']];
  var FF = [['f\u2080 = 1 / (2\u03c0 RC)', 'second-order Butterworth stage (gain 1.586): falls at 40 dB/decade'], ['f\u2080 = 1 / (2\u03c0 RC)', 'second-order high-pass: rises at 40 dB/decade'], ['f_L = 1 / (2\u03c0 R\u2081C\u2081),  f_H = 1 / (2\u03c0 R\u2082C\u2082)', 'the pass band lies between the two corners'],
    ['f = 1 / (2\u03c0 RC) at 90\u00b0 of lag', 'the gain is 1 at every frequency; only the phase changes'], ['f_c = 1 / (2\u03c0 RC)', 'first-order low-pass: 20 dB/decade'], ['f_c = 1 / (2\u03c0 RC)', 'first-order high-pass: 20 dB/decade']];
  var TH = { principle: IS_OSC ? OPRIN : FPRIN, formula: (IS_OSC ? OF : FF)[KIND][0], note: (IS_OSC ? OF : FF)[KIND][1] };
  var TT = TH;
  function askState() { var q = { experiment: S.lab.title, circuit: NAME, power_on: st.on, readings: S.rows.length };
    if (IS_OSC) { q.gain_A = r(st.A, 2); q.R = fmtR(p.R); q.C = fmtC(p.C); } else { q.frequency = fmtF(st.f); q.R = fmtR(p.R); q.C = fmtC(p.C); if (st.meas) { q.last_gain = r(st.meas.vppB / st.meas.vppA, 3); } }
    return q; }
  var VIVA = IS_OSC ? [['What two conditions must a feedback oscillator meet?', ['Loop phase zero and loop gain at least one', 'Loop phase 90° and gain below one', 'Any phase and gain exactly 29'], 0, 'The Barkhausen criterion.'], ['Does the oscillation frequency change when the gain is raised above the minimum?', ['No, the network sets it', 'Yes, it rises', 'Yes, it falls'], 0, 'Only the amplitude and the distortion grow.']]
    : [['At the cut-off frequency the gain has fallen to', ['0.707 of its passband value', '0.5', 'zero'], 0, '-3 dB is a factor 1/√2 in voltage.'], ['A second-order filter rolls off at', ['40 dB per decade', '20 dB per decade', '6 dB per decade'], 0, 'Each order adds 20 dB per decade.']];

  // ---------------------------------------------------------------- steps
  function scopeBlock(u) { var cv = document.createElement('canvas'); cv.width = 760; cv.height = 450; cv.style.cssText = 'width:100%;border-radius:10px;border:1px solid var(--line);background:#06130c'; u.el(cv); scopeCv = cv; paintPanel(); }
  var STEPS = [{ id: 'on', title: 'Switch on', view: 'gen', render: function (u) {
      u.h2('Switch the ' + (IS_OSC ? 'supply' : 'generator') + ' on');
      u.p(IS_OSC ? 'The ' + NAME + ' is built on the breadboard with ' + (KIND === 0 ? 'three equal resistors and capacitors' : KIND === 1 ? 'two equal resistors and capacitors' : 'an inductor and capacitors') + '. Switch the ±12 V supply on.' : 'The ' + NAME.toLowerCase() + ' is on the breadboard. Switch the function generator on: it gives a sine wave of ' + st.vin + ' V peak to peak.');
      u.task('Power', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('gen'); powerOn(!st.on); }, !st.on, S.hand.busy));
      u.note('Low voltages only. Check the supply polarity before switching on: a reversed op-amp supply destroys it.');
      u.next('Next', st.on); }, ok: function () { return st.on; }, auto: function () { return powerOn(true); } }];
  if (IS_OSC) {
    STEPS.push({ id: 'gain', title: 'Gain and period', view: 'scope', render: function (u) {
        u.h2('Raise the gain and measure the period');
        u.p('Turn the gain pot up slowly from 1 until a steady sine wave appears on the scope: that is the minimum gain. Then raise it a little more and measure the period on the scope.');
        u.slider('Gain A', 1, 60, 0.05, function () { return st.A; }, function (v) { setGain(v, false); paintPanel(); }, '', 2);
        u.row(u.button('Turn up until it oscillates', function () { S.focus('bb'); raiseGain(); }, false, S.hand.busy), u.button('Measure the period', function () { S.focus('scope'); measureNow(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.meas || S.hand.busy));
        u.live(function () { var am = osc()[1]; return 'Gain ' + r(st.A, 2) + ' · ' + (KN.amplitude(qNow()) > 0 ? 'oscillating, amplitude ' + r(KN.amplitude(qNow()), 2) + ' V' : 'no oscillation') + (st.meas ? ' · period ' + fmtT(st.meas.T) : ''); });
        scopeBlock(u); u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.length >= 2); }, ok: function () { return S.rows.length >= 2; },
      auto: function () { return raiseGain().then(function (A0) { var A = (A0 || 3) * 1.4; return setGain(Math.min(60, A)); }).then(function () { measureNow(); record(); return setGain(Math.min(60, (osc()[1] || 3) * 1.8)); }).then(function () { measureNow(); record(); }); } });
  } else {
    STEPS.push({ id: 'sweep', title: 'Frequency sweep', view: 'scope', render: function (u) {
        u.h2('Gain and phase against frequency');
        u.p('Set the generator frequency, measure the input and output on the scope, and write the readings down. Use a spread of frequencies on both sides of the expected corner and closer spacing near it. At least eight readings.');
        u.slider('Frequency (log scale)', 0, 600, 1, function () { return Math.round(Math.log(st.f) / Math.log(1e6) * 600); }, function (v) { setFreq(Math.round(Math.exp(v / 600 * Math.log(1e6)) * 10) / 10, false); paintPanel(); }, '', 0);
        u.row(u.button('Measure', function () { S.focus('scope'); measureNow(); }, true, S.hand.busy), u.button('Write it down', function () { record(); }, false, !st.meas || S.hand.busy));
        u.live(function () { var h = KN.h(qNow(), st.f); return fmtF(st.f) + (st.meas ? ' · gain ' + r(st.meas.vppB / st.meas.vppA, 3) + (st.meas.phase !== undefined ? ' · phase ' + r(st.meas.phase, 1) + '°' : '') : ''); });
        scopeBlock(u); u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.length >= 8); }, ok: function () { return S.rows.length >= 8; },
      auto: function () { var f0 = 1 / (2 * Math.PI * p.R * p.C), chain = Promise.resolve(), k;       // the student reads R and C off the parts: the nominal corner
        if (KIND === 2) f0 = 1 / (2 * Math.PI * p.R * p.C);
        for (k = -9; k <= 9; k++) (function (kk) { chain = chain.then(function () { return setFreq(Math.min(1e6, Math.max(1, Math.round(f0 * Math.pow(2, kk / 3) * 10) / 10)), false); }).then(function () { measureNow(); record(); }); })(k);
        return chain; } });
  }
  var cols = IS_OSC ? [{ label: 'Gain A', get: function (z) { return z.A; } }, { label: 'T (ms)', get: function (z) { return r(z.T * 1e3, 4); } }, { label: 'f (Hz)', get: function (z) { return r(z.f, 1); } }, { label: 'Amplitude (V)', get: function (z) { return r(z.vo, 2); } }]
    : [{ label: 'f (Hz)', get: function (z) { return z.f; } }, { label: 'Vin (V pp)', get: function (z) { return r(z.vin, 3); } }, { label: 'Vout (V pp)', get: function (z) { return r(z.vout, 3); } }, { label: 'Gain', get: function (z) { return r(z.g, 3); } }, { label: 'dB', get: function (z) { return r(z.db, 2); } }, { label: 'Phase (°)', get: function (z) { return r(z.ph, 1); } }];
  return {
    camera: { pos: [-0.08, 0.62, 1.22], look: [-0.08, 0.05, -0.2] },
    views: { gen: [[-0.38, 0.25, 0.2], [-0.46, 0.06, -0.26]], bb: [[-0.05, 0.3, 0.12], [-0.02, 0.02, -0.16]], scope: [[0.26, 0.3, 0.2], [0.3, 0.13, -0.26]], bench: [[-0.08, 0.62, 1.22], [-0.08, 0.05, -0.2]], book: [[0.1, 0.45, 0.55], [0.2, 0.0, 0.1]] },
    theory: { principle: TT.principle, formula: TT.formula, formulaNote: TT.note,
      more: ['The scope shows the signal against time: the period is the time between successive rising zero crossings; the peak-to-peak height gives the amplitude; the phase is the delay of the output crossing over the period.', 'Component values are printed beside the parts and carry a tolerance of a few per cent; the measured frequency is the one the actual values give.'],
      precautions: 'Low voltages only. Check supply polarity and never exceed the rated supply of the op-amp.' },
    book: { title: 'Expt. - ' + S.lab.title, at: [0.2, 0.1, 0.1], lines: ['Aim: ' + S.lab.aim.slice(0, 76), NAME, 'R = ' + fmtR(p.R) + ', C = ' + fmtC(p.C), 'Safety: low voltage, correct supply polarity.'], columns: cols },
    result: result, tol: 0.015,
    resultNote: 'The numbers come from measuring the simulated waveforms on the scope; component tolerance is not modelled, so the agreement is limited only by the reading.',
    chips: ['What is the Barkhausen criterion?', 'What is the cut-off frequency?', 'Why -3 dB?', 'Check my reading', 'Why does the gain matter?'],
    viva: VIVA, askState: askState, steps: STEPS,
    tick: function () { if (dirty) { dirty = false; paintScope(); paintPanel(); } hudA.set(IS_OSC ? r(st.A, 2) : fmtF(st.f)); hudB.set(IS_OSC ? r(KN.amplitude(qNow()), 2) + ' V' : (st.meas ? r(st.meas.vppB, 3) + ' V pp' : '—')); hudC.set(S.rows.length + ' written'); },
    ready: function () { paintScope(); }
  };
});
