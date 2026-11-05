/* Prayogshala studio module: X-BAND MICROWAVE BENCH (M.Sc. physics, WR-90 waveguide, 22.86 mm x 10.16 mm).
   A solid-state (Gunn) or reflex-klystron source with its power supply, an isolator, a variable attenuator, a
   cavity wavemeter, a slotted line with a travelling probe and a crystal detector, a load at the end (short, horn,
   slide-screw mismatch, dielectric slab on a short) and a detector indicator with an analogue dial.
   Physics: the lab's own kernel - `msc_mwline` (slotted line: guide wavelength, VSWR, double-minimum method, load
   impedance by the shift method, dielectric constant by the slab shift), `msc_klys` (reflex-klystron modes and
   electronic tuning) or `msc_gunn` (Gunn I-V, threshold and power) of packs/msc_elec.js. Positions are searched
   numerically on the detector response; nothing is read back from a formula. Microwave power is a few milliwatts
   and the open horn is never aimed at a person. */
HoolaStudio.define('msc-microwave-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign, KERN = S.lab.kernel, KN = HK.K[KERN];
  var p = HK.paramsFor(KERN, S.lab.params), V_ = S.lab.variant || {}, TASK = Math.round(p.task);
  var IS_LINE = KERN === 'msc_mwline', IS_KLYS = KERN === 'msc_klys', IS_GUNN = KERN === 'msc_gunn';
  var st = { on: false, warm: false, x: 0.05, vr: 150, vb: 0, load: 'short', slab: false, hist: [], trace: [], knobA: 0, found: null, sweeping: false };
  var dirty = true, SAMPLE = V_.sample || '';
  var X0 = -0.12;                                                  // scene x of the 0 mm mark of the slotted-line scale
  var ZL = -0.22;                                                  // the waveguide run

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function r(v, d) { var k = Math.pow(10, d === undefined ? 1 : d); return Math.round(v * k) / k; }
  function q10(v) { return Math.round(v * 1e5) / 1e5; }            // positions are read on a 0.01 mm vernier
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function lamG() { return IS_LINE ? KN.lamG(p) : 0; }

  // ---- the detector response the probe sees
  function pw(x) {
    if (TASK === 4) return st.slab ? KN.power(assign(p, { sam: 1 }), x) : KN.power(assign(p, { sam: 0 }), x, true);
    if (TASK === 0) return KN.power(assign(p, { sam: 0 }), x, true);
    if (TASK === 3) return st.load === 'short' ? KN.power(assign(p, { sam: 0 }), x, true) : KN.power(assign(p, { sam: 0 }), x);
    return KN.power(assign(p, { sam: 0 }), x);
  }
  function extrema(sign, f) {
    var n = 2000, xs = [], ys = [], out = [], i, lo, hi, c, d, fc, fd, k, gr = 0.6180339887498949;
    for (i = 0; i <= n; i++) { xs.push(0.1 * i / n); ys.push(sign * f(xs[i])); }
    for (i = 1; i < n; i++) {
      if (ys[i] < ys[i - 1] && ys[i] <= ys[i + 1]) {
        lo = xs[i - 1]; hi = xs[i + 1]; c = hi - gr * (hi - lo); d = lo + gr * (hi - lo); fc = sign * f(c); fd = sign * f(d);
        for (k = 0; k < 50; k++) { if (fc < fd) { hi = d; d = c; fd = fc; c = hi - gr * (hi - lo); fc = sign * f(c); } else { lo = c; c = d; fc = fd; d = lo + gr * (hi - lo); fd = sign * f(d); } }
        out.push(q10((lo + hi) / 2));
      }
    }
    return out;
  }
  function nearest(list, x, minDist) { var b = null, bd = 1e9, i; for (i = 0; i < list.length; i++) { var d = Math.abs(list[i] - x); if (d >= (minDist || 0) && d < bd) { bd = d; b = list[i]; } } return b; }

  // ================================================================ the bench
  var steel = new T.MeshStandardMaterial({ color: 0xb4bac2, roughness: 0.35, metalness: 0.85 });
  var brassM = M.brass;
  function guide(x0, x1, y, mat) {
    var g = new T.Group(); S.scene.add(g); g.position.set((x0 + x1) / 2, y, ZL);
    var len = Math.abs(x1 - x0), b = S.mesh(new T.BoxGeometry(len, 0.0112, 0.0239), mat || brassM); g.add(b);
    [-1, 1].forEach(function (sg) { var fl = S.mesh(new T.BoxGeometry(0.004, 0.034, 0.034), mat || brassM); fl.position.set(sg * (len / 2 + 0.002), 0, 0); g.add(fl); });
    return g;
  }
  var GY = 0.085;
  function post(x, h) { var s = S.mesh(new T.CylinderGeometry(0.006, 0.008, h, 16), M.chrome); s.position.set(x, h / 2, ZL); S.scene.add(s);
    var b = S.mesh(new T.CylinderGeometry(0.022, 0.024, 0.008, 24), M.iron); b.position.set(x, 0.004, ZL); S.scene.add(b); }
  // power supply
  var sup = new T.Group(); S.scene.add(sup); sup.position.set(-0.76, 0, ZL - 0.04);
  var SW = 0.2, SH = 0.13, SD = 0.2;
  var scase = S.rounded(SW, SD, SH, 0.01, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); scase.rotation.x = -Math.PI / 2; scase.position.y = SH / 2 + 0.004; sup.add(scase);
  var SFZ = SD / 2 + 0.0062, SPW = SW - 0.014, SPH = SH - 0.014;
  var supName = IS_KLYS ? 'KLYSTRON POWER SUPPLY' : 'GUNN POWER SUPPLY', supNote = IS_KLYS ? 'BEAM 300 V · REFLECTOR 0 - 500 V' : 'BIAS 0 - 12 V · 0 - 250 mA';
  var sTex = S.canvasTex(1000, Math.round(1000 * SPH / SPW), function (x, w, h) {
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.textAlign = 'center'; x.font = '700 40px "Public Sans", sans-serif'; x.fillText(supName, w / 2, 62);
    x.font = '500 26px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText(supNote, w / 2, 100);
    x.font = '700 28px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText(IS_KLYS ? 'REFLECTOR' : 'BIAS', w * 0.3, h - 26); x.fillText('POWER', w * 0.75, h - 26);
    var kx = (-0.04 / SPW + 0.5) * w, ky = (0.5 + 0.012 / SPH) * h, kr = 0.028 * w / SPW, vmin = IS_KLYS ? 20 : 0, vmax = IS_KLYS ? 500 : 12, nt = IS_KLYS ? 24 : 12, q;
    x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8'; x.font = '600 20px "Public Sans", sans-serif';
    for (q = 0; q <= nt; q++) { var th = (225 - 270 * q / nt) * Math.PI / 180, big = q % (IS_KLYS ? 4 : 2) === 0; x.lineWidth = big ? 3 : 2; x.beginPath();
      x.moveTo(kx + Math.cos(th) * kr, ky - Math.sin(th) * kr); x.lineTo(kx + Math.cos(th) * (kr + (big ? 22 : 12)), ky - Math.sin(th) * (kr + (big ? 22 : 12))); x.stroke();
      if (big) { x.textAlign = 'center'; x.fillText(String(Math.round(vmin + (vmax - vmin) * q / nt)), kx + Math.cos(th) * (kr + 42), ky - Math.sin(th) * (kr + 42) + 7); } } });
  var sfac = S.mesh(new T.BoxGeometry(SPW, SPH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: sTex, roughness: 0.45 }), M.grey]);
  sfac.position.set(0, 0.004 + SH / 2, SFZ - 0.002); sup.add(sfac);
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  function knobAt(parent, u, v, z0, rad) {
    var kg = new T.Group(); kg.position.set(u, v, z0); parent.add(kg);
    var sk = S.mesh(new T.CylinderGeometry(rad * 1.3, rad * 1.38, 0.004, 36), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; kg.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(rad, rad * 1.1, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; kg.add(kb);
    var kp = S.mesh(new T.BoxGeometry(0.002, rad * 1.1, 0.0012), M.white, false); kp.position.set(0, rad * 0.65, 0.0215); kg.add(kp); return kg;
  }
  var supKnob = knobAt(sup, -0.04, 0.004 + SH / 2 - 0.012, SFZ, 0.0145);
  var pwrKnob = knobAt(sup, 0.05, 0.004 + SH / 2 - 0.012, SFZ, 0.0105);
  var led = S.mesh(new T.SphereGeometry(0.005, 14, 14), new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000 })); led.position.set(0.05, 0.004 + SH / 2 + 0.03, SFZ + 0.002); sup.add(led);
  function knobA(v) { return IS_KLYS ? 3 * Math.PI / 4 - 1.5 * Math.PI * (v - 20) / 480 : 3 * Math.PI / 4 - 1.5 * Math.PI * v / 12; }
  supKnob.rotation.z = knobA(IS_KLYS ? st.vr : st.vb); pwrKnob.rotation.z = 2.3;
  // source on its mount, isolator, attenuator, wavemeter
  var yG = GY;
  var src = new T.Group(); S.scene.add(src); src.position.set(-0.6, yG, ZL);
  var sbody = S.mesh(new T.BoxGeometry(0.06, 0.03, 0.04), brassM); src.add(sbody);
  var scyl = IS_KLYS ? S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.11, 28), new T.MeshStandardMaterial({ color: 0xaab0b8, roughness: 0.3, metalness: 0.8 })) : S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.05, 20), steel);
  scyl.position.y = IS_KLYS ? 0.08 : 0.04; src.add(scyl);
  var sl = S.label(IS_KLYS ? 'REFLEX KLYSTRON' : 'GUNN OSCILLATOR', { w: 0.052, ratio: 0.16, color: '#1b1b1b', bg: '#e6e1cf' }); sl.position.set(0, 0.0, 0.0205); src.add(sl);
  var fl0 = S.mesh(new T.BoxGeometry(0.004, 0.034, 0.034), brassM); fl0.position.set(0.032, 0, 0); src.add(fl0);
  var iso = guide(-0.55, -0.47, yG, brassM), isoL = S.label('ISOLATOR', { w: 0.05, ratio: 0.2, color: '#1b1b1b', bg: '#e6e1cf' }); isoL.position.set(0, 0.0, 0.0125); iso.add(isoL);
  var att = guide(-0.46, -0.38, yG, brassM);
  var attK = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.016, 24), new T.MeshStandardMaterial({ map: knurl })); attK.position.set(0, 0.014, 0); att.add(attK);
  var attL = S.label('VARIABLE ATTENUATOR', { w: 0.07, ratio: 0.14, color: '#1b1b1b', bg: '#e6e1cf' }); attL.position.set(0, 0.0, 0.0125); att.add(attL);
  var wav = guide(-0.37, -0.29, yG, brassM);
  var wcav = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.03, 36), steel); wcav.position.set(0, 0.026, 0); wav.add(wcav);
  var wdial = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), new T.MeshStandardMaterial({ map: knurl })); wdial.position.set(0, 0.052, 0); wav.add(wdial);
  var wl = S.label('FREQUENCY METER', { w: 0.07, ratio: 0.14, color: '#1b1b1b', bg: '#e6e1cf' }); wl.position.set(0, 0.0, 0.0125); wav.add(wl);
  [-0.57, -0.42, -0.33].forEach(function (x) { post(x, yG - 0.0056); });
  // slotted line
  var line = guide(-0.17, 0.0, yG, brassM), SLX0 = -0.17;
  line.position.set(-0.085, yG, ZL);
  var lineTop = S.mesh(new T.BoxGeometry(0.17, 0.004, 0.0239), new T.MeshStandardMaterial({ color: 0xb5a054, roughness: 0.4, metalness: 0.8 })); lineTop.position.set(0, 0.0078, 0); line.add(lineTop);
  var slot = S.mesh(new T.BoxGeometry(0.1, 0.0045, 0.0018), new T.MeshStandardMaterial({ color: 0x0d0d0d })); slot.position.set(X0 + 0.05 + 0.085, 0.0083, 0); line.add(slot);
  var scaleTex = S.canvasTex(1700, 120, function (x, w, h) { x.fillStyle = '#f1efe8'; x.fillRect(0, 0, w, h); x.fillStyle = '#16171a'; x.font = '600 34px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var mm = 0; mm <= 100; mm++) { var xx = 12 + mm * (w - 24) / 100; x.fillRect(xx, 0, mm % 10 === 0 ? 4 : 2, mm % 10 === 0 ? 56 : mm % 5 === 0 ? 40 : 26); if (mm % 10 === 0) x.fillText(String(mm), xx, 98); } });
  var sc = new T.Mesh(new T.PlaneGeometry(0.1 * 1700 / 1676, 0.0072), new T.MeshStandardMaterial({ map: scaleTex, roughness: 0.6 })); sc.rotation.x = -Math.PI / 2; sc.position.set(X0 + 0.05 + 0.085, 0.0112, 0.0225); line.add(sc);
  var scaleTitle = S.label('SLOTTED LINE · mm', { w: 0.05, ratio: 0.14, color: '#1b1b1b', bg: '#e6e1cf' }); scaleTitle.position.set(X0 + 0.05 + 0.085, 0.0, 0.0125); line.add(scaleTitle);
  var carriage = new T.Group(); line.add(carriage); carriage.position.set(X0 + st.x + 0.085, 0.0, 0.0);
  var cb = S.rounded(0.026, 0.034, 0.012, 0.003, M.iron); cb.rotation.x = -Math.PI / 2; cb.position.set(0, 0.016, 0); carriage.add(cb);
  var probe = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.02, 10), steel); probe.position.set(0, 0.0062, 0); carriage.add(probe);
  var dmount = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.026, 20), M.chrome); dmount.position.set(0, 0.032, 0); carriage.add(dmount);
  var indPos = new T.Vector3(0.22, 0, -0.02);
  S.wire([[X0 + st.x + 0.0, 0.125, ZL], [-0.03, 0.15, -0.15], [0.08, 0.06, -0.09], [indPos.x - 0.06, 0.05, indPos.z + 0.07]], 'black');
  [-0.14, 0.02].forEach(function (x) { post(x, yG - 0.0056); });
  // load at the end
  var load = new T.Group(); S.scene.add(load); load.position.set(0.0, yG, ZL);
  var shortP = S.mesh(new T.BoxGeometry(0.004, 0.034, 0.034), M.chrome); shortP.position.set(0.004, 0, 0); load.add(shortP);
  var slab = S.mesh(new T.BoxGeometry(p.ls || 0.004, 0.0098, 0.0224), new T.MeshStandardMaterial({ color: /ptfe/i.test(SAMPLE) ? 0xf2f2ee : /glass|silica|quartz/i.test(SAMPLE) ? 0xcfe5ea : 0xe9ddc2, roughness: 0.5, transparent: true, opacity: 0.92 })); slab.position.set(-(p.ls || 0.004) / 2 - 0.0, 0, 0); slab.visible = false; load.add(slab);
  var hornG = new T.Group(); load.add(hornG); hornG.visible = false;
  var horn = S.mesh(new T.CylinderGeometry(0.056, 0.018, 0.12, 4, 1, true), new T.MeshStandardMaterial({ color: 0xc3a45c, roughness: 0.35, metalness: 0.85, side: T.DoubleSide })); horn.rotation.z = -Math.PI / 2; horn.rotation.x = Math.PI / 4; horn.position.set(0.06, 0, 0); hornG.add(horn);
  var tuner = S.mesh(new T.BoxGeometry(0.06, 0.03, 0.04), brassM); tuner.position.set(0.04, 0.0, 0); tuner.visible = false; load.add(tuner);
  var tscrew = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.04, 14), steel); tscrew.position.set(0.04, 0.032, 0); tscrew.visible = false; load.add(tscrew);
  var lload = S.label('', { w: 0.05, ratio: 0.2 });
  var loadLabel = S.label(IS_LINE ? (TASK === 1 ? 'HORN - OPEN ROOM' : TASK === 2 || TASK === 3 ? 'SLIDE-SCREW TUNER' : TASK === 4 ? 'SHORT + SLAB' : 'SHORT CIRCUIT') : 'MATCHED LOAD', { w: 0.08, ratio: 0.14, color: '#1b1b1b', bg: '#e6e1cf' });
  loadLabel.position.set(0.045, -0.04, 0.0); loadLabel.rotation.x = 0; loadLabel.position.set(0.05, 0.0, 0.0205); load.add(loadLabel);
  S.contact(1.55, 0.3, -0.18, ZL, 0.35);
  // the indicator (analogue dial + display)
  var ind = new T.Group(); S.scene.add(ind); ind.position.copy(indPos); ind.rotation.y = -0.3;
  var IW = 0.24, IH = 0.17, ID = 0.16;
  var icase = S.rounded(IW, ID, IH, 0.01, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); icase.rotation.x = -Math.PI / 2; icase.position.y = IH / 2 + 0.004; ind.add(icase);
  var dialTex = S.liveTex(1024, 720), dialMat = new T.MeshBasicMaterial({ map: dialTex, toneMapped: false });
  var dialP = new T.Mesh(new T.PlaneGeometry(IW - 0.014, (IW - 0.014) * 720 / 1024), dialMat); dialP.position.set(0, 0.004 + IH / 2, ID / 2 + 0.0035); ind.add(dialP);
  S.addApparatus('source', src, IS_KLYS ? 'Reflex klystron' : IS_GUNN ? 'Gunn oscillator' : 'Gunn oscillator (X band)', IS_KLYS ? 'A reflex klystron: the beam is turned back by the reflector and bunches; it oscillates in modes, each a window of reflector voltage.' : 'A Gunn diode in a waveguide cavity. Above its threshold voltage it oscillates at a frequency set by the transit length and the cavity.');
  S.addApparatus('supply', sup, supName.charAt(0) + supName.slice(1).toLowerCase(), 'Supplies the bias (or beam and reflector) voltage; the knob on the left sets it and the lamp shows that the source is on.');
  S.addApparatus('iso', iso, 'Isolator', 'Passes power one way only, so reflections from the load never pull the source frequency.');
  S.addApparatus('att', att, 'Variable attenuator', 'Sets the power so that the detector stays on its square-law part.');
  S.addApparatus('wav', wav, 'Cavity wavemeter', 'Tune the cavity until the detector reading dips: the dial then reads the frequency.');
  S.addApparatus('line', line, IS_LINE ? 'Slotted line' : 'Waveguide', 'A slot along the middle of the broad wall lets a small probe sample the electric field without disturbing it. The scale reads the probe position in millimetres.');
  S.addApparatus('carriage', carriage, 'Probe carriage and crystal detector', 'The carriage slides along the slot; the crystal detector gives a current proportional to the power of the field at the probe.');
  S.addApparatus('load', load, IS_LINE ? (TASK === 1 ? 'Pyramidal horn' : TASK === 2 || TASK === 3 ? 'Slide-screw tuner' : TASK === 4 ? 'Short circuit with dielectric slab' : 'Short circuit') : 'Matched load', 'The termination of the guide. It decides the standing wave: a short gives total reflection, a matched load none.');
  S.addApparatus('ind', ind, 'Detector indicator', 'The analogue dial reads the crystal current, the display the other readings.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard(IS_LINE ? 'Probe position' : IS_KLYS ? 'Reflector voltage' : 'Bias voltage'), hudB = S.hudCard(IS_LINE ? 'Detector current' : IS_KLYS ? 'Power' : 'Current'), hudC = S.hudCard('Readings');

  // ================================================================ readings
  function reading() {                                  // primary dial value, its unit and full scale
    if (IS_LINE) { return { v: st.on ? pw(st.x) : 0, max: p.p0, unit: 'µA' }; }
    if (IS_KLYS) { return { v: st.on && st.warm ? KN.power(assign(p, { vr: st.vr }), st.vr) : 0, max: p.P0, unit: 'mW' }; }
    return { v: st.on ? KN.cur(p, st.vb) * 1000 : 0, max: 200, unit: 'mA' };
  }
  function freqNow() {
    if (IS_KLYS) return st.on && st.warm && KN.power(p, st.vr) > 0 ? Math.round(KN.freq(p, st.vr) / 1e5) / 10 : 0;
    if (IS_GUNN) return st.on && st.vb > KN.vth(p) ? Math.round(p.vd / p.Lg / 1e8) / 10 : 0;
    return Math.round(p.f / 1e5) / 10;
  }
  function drawDial(x, w, h) {
    var rd = reading(), cx = w / 2, cy = h * 0.82, R = h * 0.6;
    x.fillStyle = '#efe9d6'; x.fillRect(0, 0, w, h);
    x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b'; x.lineWidth = 3; x.textAlign = 'center'; x.font = '600 34px "Public Sans", sans-serif';
    for (var i = 0; i <= 50; i++) { var f = i / 50, th = (Math.PI * 0.8) - f * Math.PI * 0.6 * 2 + Math.PI * 0.0 - Math.PI * 0.0; th = Math.PI * 0.82 - f * Math.PI * 0.64;
      var big = i % 10 === 0, r1 = R, r2 = R - (big ? 34 : 18); x.lineWidth = big ? 4 : 2; x.beginPath(); x.moveTo(cx + Math.cos(th) * r1, cy - Math.sin(th) * r1); x.lineTo(cx + Math.cos(th) * r2, cy - Math.sin(th) * r2); x.stroke();
      if (big) x.fillText(String(Math.round(rd.max * f)), cx + Math.cos(th) * (R - 66), cy - Math.sin(th) * (R - 66) + 10); }
    var fr = Math.max(0, Math.min(1, rd.v / rd.max)), ta = Math.PI * 0.82 - fr * Math.PI * 0.64;
    x.strokeStyle = '#b3261e'; x.lineWidth = 5; x.beginPath(); x.moveTo(cx, cy); x.lineTo(cx + Math.cos(ta) * (R - 10), cy - Math.sin(ta) * (R - 10)); x.stroke();
    x.fillStyle = '#1b1b1b'; x.beginPath(); x.arc(cx, cy, 12, 0, 6.3); x.fill();
    x.font = '700 40px "Public Sans", sans-serif'; x.fillText(rd.unit, cx, h * 0.5);
    x.font = '600 32px "JetBrains Mono", monospace'; x.textAlign = 'left';
    x.fillText(IS_LINE ? 'probe ' + r(st.x * 1000, 2) + ' mm' : IS_KLYS ? 'Vr ' + r(st.vr, 1) + ' V' : 'V ' + r(st.vb, 2) + ' V', 28, 52);
    x.textAlign = 'right'; var fq = freqNow();
    if (IS_KLYS) x.fillText('f ' + (fq > 0 ? r(KN.freq(p, st.vr) / 1e9, 4) + ' GHz' : '—'), w - 28, 52);
    else if (IS_GUNN) x.fillText('f ' + (fq > 0 ? fq + ' GHz' : '—'), w - 28, 52);
    else x.fillText('f ' + r(p.f / 1e9, 3) + ' GHz', w - 28, 52);
  }
  function paintDial() { dialTex.draw(function (x, w, h) { x.save(); drawDial(x, w, h); x.restore(); }); }
  // a plot beside the bench for the klystron / Gunn traces
  var plotCv = null;
  function drawPlot(x, w, h) {
    x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h); var PL = 52, PB = 34, PT = 14, PR = 14, i, pts = IS_KLYS ? st.trace : st.hist2();
    var xmin = IS_KLYS ? 0 : 0, xmax = IS_KLYS ? 500 : 12, ymax = IS_KLYS ? p.P0 * 1.15 : 220;
    var X = function (v) { return PL + (v - xmin) / (xmax - xmin) * (w - PL - PR); }, Y = function (v) { return h - PB - v / ymax * (h - PB - PT); };
    x.strokeStyle = 'rgba(160,230,190,.16)'; x.fillStyle = '#9fe0b8'; x.font = '15px "JetBrains Mono", monospace'; x.textAlign = 'center';
    for (i = 0; i <= 5; i++) { var xv = xmin + (xmax - xmin) * i / 5; x.beginPath(); x.moveTo(X(xv), PT); x.lineTo(X(xv), h - PB); x.stroke(); x.fillText(String(Math.round(xv * 10) / 10), X(xv), h - PB + 17); }
    x.textAlign = 'right'; for (i = 0; i <= 4; i++) { var yv = ymax * i / 4; x.beginPath(); x.moveTo(PL, Y(yv)); x.lineTo(w - PR, Y(yv)); x.stroke(); x.fillText(String(Math.round(yv)), PL - 6, Y(yv) + 5); }
    x.textAlign = 'center'; x.fillText(IS_KLYS ? 'reflector voltage (V)     power (mW)' : 'bias voltage (V)     current (mA)', PL + (w - PL - PR) / 2, h - 4);
    x.strokeStyle = '#6dffa4'; x.fillStyle = '#6dffa4'; x.lineWidth = 2;
    if (IS_KLYS) { x.beginPath(); pts.forEach(function (q, k) { if (k) x.lineTo(X(q[0]), Y(q[1])); else x.moveTo(X(q[0]), Y(q[1])); }); x.stroke(); }
    else pts.forEach(function (q) { x.beginPath(); x.arc(X(q[0]), Y(q[1]), 4, 0, 6.3); x.fill(); });
    x.strokeStyle = '#ffd24a'; x.setLineDash([5, 4]); var cv = IS_KLYS ? st.vr : st.vb; x.beginPath(); x.moveTo(X(cv), PT); x.lineTo(X(cv), h - PB); x.stroke(); x.setLineDash([]);
  }
  st.hist2 = function () { var o = []; S.rows.forEach(function (rw) { if (rw.V !== undefined) o.push([rw.V, rw.I]); }); return o; };
  var mon = null, monTex = null;
  if (!IS_LINE) {
    mon = new T.Group(); S.scene.add(mon); mon.position.set(0.4, 0, -0.4); mon.rotation.y = -0.4;
    var mb = S.rounded(0.3, 0.2, 0.03, 0.008, new T.MeshStandardMaterial({ color: 0x1b1d21, roughness: 0.45, metalness: 0.3 })); mb.position.set(0, 0.18, 0); mon.add(mb);
    var ms = S.mesh(new T.BoxGeometry(0.04, 0.09, 0.03), M.iron); ms.position.set(0, 0.06, -0.01); mon.add(ms);
    var mbs = S.rounded(0.18, 0.12, 0.012, 0.006, M.iron); mbs.rotation.x = -Math.PI / 2; mbs.position.set(0, 0.006, 0); mon.add(mbs);
    monTex = S.liveTex(1024, 620);
    var mscr = new T.Mesh(new T.PlaneGeometry(0.28, 0.28 * 620 / 1024), new T.MeshBasicMaterial({ map: monTex, toneMapped: false })); mscr.position.set(0, 0.18, 0.017); mon.add(mscr);
    S.addApparatus('plot', mon, 'Chart display', 'The trace of power (or current) against the control voltage, drawn as you sweep.');
    S.contact(0.4, 0.3, 0.4, -0.4, 0.45);
  }
  function paintMon() { if (monTex) monTex.draw(function (x, w, h) { drawPlot(x, w, h); }); if (plotCv && plotCv.isConnected) drawPlot(plotCv.getContext('2d'), plotCv.width, plotCv.height); }
  S.contact(0.34, 0.26, -0.76, ZL - 0.04, 0.5); S.contact(0.3, 0.22, indPos.x, indPos.z, 0.45);
  // set the load for the task
  function showLoad() {
    shortP.visible = IS_LINE ? !(TASK === 1 || ((TASK === 2 || TASK === 3) && st.load === 'unknown')) : false; hornG.visible = IS_LINE && TASK === 1;
    var tun = IS_LINE && (TASK === 2 || (TASK === 3 && st.load === 'unknown')); tuner.visible = tun; tscrew.visible = tun;
    slab.visible = IS_LINE && TASK === 4 && st.slab; if (!IS_LINE) shortP.visible = false;
    loadLabel.visible = IS_LINE;
  }
  showLoad();

  // ================================================================ human actions
  function turnKnob(kg, from, to, ptLocal) {
    var pt = wpt(sup, ptLocal[0], ptLocal[1], ptLocal[2]);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { kg.rotation.z = from + (to - from) * k; }, { mode: 'front', ms: 700, reachMs: 600 });
  }
  function switchOn(on) {
    if (busy()) return Promise.resolve();
    if (st.on === on) return Promise.resolve();
    return turnKnob(pwrKnob, on ? 2.3 : -0.9, on ? -0.9 : 2.3, [0.05, 0.004 + SH / 2 - 0.012, SFZ + 0.024]).then(function () {
      st.on = on; pwrKnob.rotation.z = on ? -0.9 : 2.3; led.material.emissive.setHex(on ? 0x22cc44 : 0); led.material.color.setHex(on ? 0x33dd55 : 0x331111);
      if (!on) st.warm = false; dirty = true;
      S.say(on ? (IS_KLYS ? 'Supply on. The klystron heater must warm up before the beam is switched on.' : 'Supply on. The Gunn diode is biased from 0 V upward.') : 'Supply off.'); S.render(); });
  }
  function warmUp() { if (!st.on) { S.say('Switch the supply on first.'); return Promise.resolve(); } return S.tween(900, function () {}).then(function () { st.warm = true; dirty = true; S.say('Warm-up done: the beam is on at 300 V.'); S.render(); }); }
  function setControl(v, animate) {                                    // reflector voltage (klystron) or bias (Gunn)
    var lo = IS_KLYS ? 20 : 0, hi = IS_KLYS ? 500 : 12;
    if (!isFinite(v) || v < lo - 1e-9 || v > hi + 1e-9) { S.say('That is outside the supply\'s range of ' + lo + ' to ' + hi + ' V.'); return Promise.resolve(); }
    var v0 = IS_KLYS ? st.vr : st.vb;
    function apply(val) { if (IS_KLYS) st.vr = val; else st.vb = val; supKnob.rotation.z = knobA(val); dirty = true; }
    if (animate === false || S.hand.busy) { apply(v); return Promise.resolve(); }
    return turnKnob(supKnob, knobA(v0), knobA(v), [-0.04, 0.004 + SH / 2 - 0.012, SFZ + 0.024]).then(function () { apply(v); });
  }
  function moveProbe(x, animate) {
    if (!isFinite(x) || x < -1e-9 || x > 0.1 + 1e-9) { S.say('The slot is 0 to 100 mm long.'); return Promise.resolve(); }
    x = q10(Math.max(0, Math.min(0.1, x)));
    function apply(v) { st.x = v; carriage.position.x = X0 + v + 0.085; dirty = true; if (st.on) { st.hist.push([v, pw(v)]); if (st.hist.length > 400) st.hist.shift(); } }
    if (animate === false || S.hand.busy || Math.abs(x - st.x) < 1e-6) { apply(x); return Promise.resolve(); }
    var x0 = st.x, pt = wpt(carriage, 0, 0.032, 0);
    return S.hand.pinchMove(pt, function (k) { return wpt(line, X0 + (x0 + (x - x0) * k) + 0.085, 0.036, 0); }, function (k) { apply(x0 + (x - x0) * k); }, { mode: 'top', ms: 500 + 4000 * Math.abs(x - x0), reachMs: 500 }).then(function () { apply(x); });
  }
  function fitLoad(which) {
    if (busy()) return Promise.resolve();
    if (st.load === which) return Promise.resolve();
    return S.tween(700, function () {}).then(function () { st.load = which; showLoad(); dirty = true; S.say(which === 'unknown' ? 'The unknown load is on the end of the line.' : 'The short circuit is on the end of the line.'); S.render(); });
  }
  function fitSlab(on) {
    if (busy()) return Promise.resolve();
    if (st.slab === on) return Promise.resolve();
    return S.tween(700, function () {}).then(function () { st.slab = on; showLoad(); dirty = true; S.say(on ? 'The dielectric slab is in the guide, against the short.' : 'The slab is out: only the short circuit.'); S.render(); });
  }
  function goMin(dir) { return goExtreme(1, dir); }
  function goMax() { return goExtreme(-1, 0); }
  function goExtreme(sign, dir) {                                      // slide the probe to the nearest minimum (sign 1) or maximum
    if (!st.on) { S.say('Switch the source on first.'); return Promise.resolve(null); }
    var list = extrema(sign, pw), tgt = null, i;
    if (dir === 0) tgt = nearest(list, st.x, 0);
    else { for (i = 0; i < list.length; i++) { if (dir > 0 && list[i] > st.x + lamG() * 0.25 && (tgt === null || list[i] < tgt)) tgt = list[i]; if (dir < 0 && list[i] < st.x - lamG() * 0.25 && (tgt === null || list[i] > tgt)) tgt = list[i]; } if (tgt === null) tgt = nearest(list, st.x, 0); }
    if (tgt === null) { S.say('No ' + (sign > 0 ? 'minimum' : 'maximum') + ' in the slot.'); return Promise.resolve(null); }
    return moveProbe(tgt).then(function () { S.say((sign > 0 ? 'Minimum' : 'Maximum') + ' of the detector reading at ' + r(tgt * 1000, 2) + ' mm.'); S.render(); return tgt; });
  }
  function goTwice() {                                                 // the two points either side of the minimum where the reading is twice the minimum
    var mn = extrema(1, pw), xm = nearest(mn, st.x, 0); if (xm === null) return Promise.resolve(null);
    var pm = pw(xm), out = [], side;
    for (side = -1; side <= 1; side += 2) { var lo = 0, hi = 0.012, k; for (k = 0; k < 50; k++) { var mid = (lo + hi) / 2; if (pw(xm + side * mid) < 2 * pm) lo = mid; else hi = mid; } out.push(q10(xm + side * (lo + hi) / 2)); }
    return moveProbe(xm).then(function () { return moveProbe(out[0]); }).then(function () { return { a: out[0], b: out[1], xm: xm }; });
  }
  function readTrace() { return S.tween(600, function () {}); }
  function sweep() {
    if (busy()) return Promise.resolve();
    if (!(st.on && st.warm)) { S.say('Switch on the supply and let it warm up first.'); return Promise.resolve(); }
    st.trace = []; st.sweeping = true;
    var n = 0;
    return S.tween(1600, function (k) { var v = 20 + 480 * k; st.vr = v; supKnob.rotation.z = knobA(v); var target = Math.floor(k * 96); while (n <= target) { var vv = 20 + n * 5; st.trace.push([vv, KN.power(assign(p, { vr: vv }), vv)]); n++; } dirty = true; }).then(function () {
      st.trace = []; for (var i = 0; i <= 96; i++) { var vv = 20 + i * 5; st.trace.push([vv, KN.power(assign(p, { vr: vv }), vv)]); }
      st.sweeping = false; dirty = true; S.say('Reflector swept from 20 to 500 V: the power shows separate modes, each a window of reflector voltage.'); S.render(); });
  }
  function nearestCentre() {
    if (!(st.on && st.warm)) { S.say('Switch on the supply and let it warm up first.'); return Promise.resolve(null); }
    var best = -1, vc = null, i, v, pwr, loV = Math.max(20, st.vr - 110), hiV = Math.min(500, st.vr + 110), peaks = [];
    for (i = Math.round(loV * 10); i <= Math.round(hiV * 10); i++) { v = i / 10; pwr = KN.power(assign(p, { vr: v }), v); var pl = KN.power(assign(p, { vr: v - 0.1 }), v - 0.1), pr = KN.power(assign(p, { vr: v + 0.1 }), v + 0.1); if (pwr > 0 && pwr >= pl && pwr > pr) peaks.push(v); }
    vc = nearest(peaks, st.vr, 0); if (vc === null) { S.say('No mode in reach: move the reflector voltage nearer to a power maximum first.'); return Promise.resolve(null); }
    return setControl(vc).then(function () { S.say('Tuned to the centre of a mode: Vr = ' + r(vc, 1) + ' V, power ' + r(KN.power(assign(p, { vr: vc }), vc), 2) + ' mW.'); S.render(); return vc; });
  }
  function halfPoint(vc, dir) {
    var pc = KN.power(assign(p, { vr: vc }), vc), v = vc, k = 0;
    while (k++ < 4000) { v = r(v + dir * 0.1, 1); if (v < 20 || v > 500) break; if (KN.power(assign(p, { vr: v }), v) <= pc / 2) break; }
    return v;
  }
  function klysRecord() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
    var vc = st.vr, pc = KN.power(assign(p, { vr: vc }), vc);
    if (pc <= 0) { S.say('The tube is not oscillating here. Tune to a mode first.'); return Promise.resolve(false); }
    var n = KN.locate(p, vc)[0];
    if (S.rows.some(function (rw) { return rw.n === n; })) { S.say('Mode ' + n + ' is already in the book.'); return Promise.resolve(false); }
    var vlo = halfPoint(vc, -1), vhi = halfPoint(vc, 1);
    return setControl(Math.max(20, vlo), true).then(function () { return setControl(Math.min(500, vhi), true); }).then(function () { return setControl(vc, true); }).then(function () {
      var flo = Math.round(KN.freq(p, Math.max(20, vlo)) / 1e5) / 10, fhi = Math.round(KN.freq(p, Math.min(500, vhi)) / 1e5) / 10, fc = Math.round(KN.freq(p, vc) / 1e5) / 10;
      S.addRow({ n: n, vr: vc, P: pc, fc: fc, vlo: vlo, vhi: vhi, flo: flo, fhi: fhi, et: Math.abs(flo - fhi) });
      S.say('Mode ' + n + ': centre ' + r(vc, 1) + ' V, half-power points ' + r(vlo, 1) + ' and ' + r(vhi, 1) + ' V; the frequency moves ' + r(Math.abs(flo - fhi), 1) + ' MHz between them.'); return true; });
  }
  function gunnRead() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.on) { S.say('Switch the supply on first.'); return false; }
    var V = r(st.vb, 2);
    if (S.rows.some(function (rw) { return Math.abs(rw.V - V) < 1e-9; })) { S.say('A reading at ' + V + ' V is already in the book.'); return false; }
    S.addRow({ V: V, I: r(KN.cur(p, V) * 1000, 1), P: r(KN.power(p, V), 2), f: freqNow() }); return true;
  }
  function lineRecord(kind) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.on) { S.say('Switch the source on first.'); return false; }
    var row = { kind: kind, x: st.x, I: pw(st.x) };
    if (S.rows.some(function (rw) { return rw.kind === kind && Math.abs(rw.x - row.x) < 2e-5; })) { S.say('That reading is already in the book.'); return false; }
    S.addRow(row); return true;
  }
  function rowsOf(k) { return S.rows.filter(function (rw) { return rw.kind === k; }).sort(function (a, b) { return a.x - b.x; }); }

  // ================================================================ result
  function lamCalc() { return KN.lamG(p); }
  function result(rows) {
    var i, a;
    if (IS_KLYS) {
      var rr = rows.filter(function (rw) { return rw.n === Math.round(p.mode); })[0]; if (!rr) return null;
      return { label: 'Electronic tuning range of mode ' + rr.n, value: rr.et, unit: 'MHz', digits: 1, truth: p.f0 / (2 * p.Q) / 1e6, note: 'Mode centre ' + r(rr.vr, 1) + ' V; frequency measured at the two half-power voltages with the wavemeter.' };
    }
    if (IS_GUNN) {
      if (rows.length < 8) return null; var best = rows[0]; for (i = 1; i < rows.length; i++) if (rows[i].I > best.I) best = rows[i];
      return { label: 'Threshold voltage (current maximum)', value: best.V, unit: 'V', digits: 2, truth: KN.vth(p), note: 'The current peaks at ' + r(best.I, 1) + ' mA and then falls; oscillation starts there at about ' + r(p.vd / p.Lg / 1e9, 2) + ' GHz.' };
    }
    var mins = rowsOf('m'), maxs = rowsOf('M'), shorts = rowsOf('S');
    if (TASK === 0) { if (mins.length < 2) return null; var sum = 0; for (i = 1; i < mins.length; i++) sum += mins[i].x - mins[i - 1].x; return { label: 'Guide wavelength', value: 2 * sum / (mins.length - 1) * 1000, unit: 'mm', digits: 2, truth: lamCalc() * 1000, note: 'Twice the distance between successive minima of the standing wave.' }; }
    if (TASK === 1) { if (!mins.length || !maxs.length) return null; var mn = Math.min.apply(null, mins.map(function (z) { return z.I; })), mx = Math.max.apply(null, maxs.map(function (z) { return z.I; })); return { label: 'VSWR', value: Math.sqrt(mx / mn), unit: '', digits: 3, truth: (1 + p.g) / (1 - p.g), note: 'S = √(I_max / I_min): the crystal is a square-law detector, so the currents go as power.' }; }
    if (TASK === 2) { var tw = rows.filter(function (z) { return z.kind === 'a'; })[0], tb = rows.filter(function (z) { return z.kind === 'b'; })[0]; if (!tw || !tb) return null; var dx = Math.abs(tb.x - tw.x), lg = lamCalc(); return { label: 'VSWR by the double-minimum method', value: Math.sqrt(1 + 1 / Math.pow(Math.sin(Math.PI * dx / lg), 2)), unit: '', digits: 2, truth: (1 + p.g) / (1 - p.g), note: 'Width of the minimum at twice its power: ' + r(dx * 1000, 2) + ' mm, with λg = ' + r(lg * 1000, 2) + ' mm.' }; }
    if (TASK === 3) { if (!shorts.length || !mins.length || !maxs.length) return null; var im = Math.min.apply(null, mins.map(function (z) { return z.I; })), iM = Math.max.apply(null, maxs.map(function (z) { return z.I; })), S_ = Math.sqrt(iM / im), lg3 = lamCalc(), half = lg3 / 2, xm = mins[0].x, xs = shorts[0].x, delta = ((xm - xs) % half + half) % half, dmin = ((half - delta) % half + half) % half, z = KN.zload(S_, dmin, lg3);
      return { label: 'Normalised load resistance r', value: z[0], unit: '', digits: 3, truth: (1 - p.g * p.g) / (1 + p.g * p.g - 2 * p.g * Math.cos(p.phi)), note: 'VSWR ' + r(S_, 2) + ', the first minimum is ' + r(dmin * 1000, 2) + ' mm from the load; z = ' + r(z[0], 3) + ' ' + (z[1] < 0 ? '−' : '+') + ' j' + r(Math.abs(z[1]), 3) + '.' }; }
    var sh0 = shorts[0], wm = rows.filter(function (z) { return z.kind === 'W'; })[0]; if (!sh0 || !wm) return null;
    var half4 = lamCalc() / 2, sh = (((sh0.x - wm.x) % half4) + half4) % half4; if (sh > half4 / 2) sh -= half4;
    return { label: 'Dielectric constant of the slab', value: KN.erFromShift(sh, p), unit: '', digits: 3, truth: p.er, note: 'The minimum moved ' + r(sh * 1000, 2) + ' mm (toward the generator is positive) when the ' + r(p.ls * 1000, 1) + ' mm slab was put against the short.' };
  }

  // ================================================================ text
  var TX = {
    0: ['Standing waves in a waveguide: the guide wavelength', 'Against a short circuit the wave is totally reflected, and the incident and reflected waves make a standing wave whose minima are half a guide wavelength apart: λg = 2 (x₂ − x₁). It is longer than the free-space wavelength because of the waveguide cut-off.', 'λg = λ₀ / √(1 − (λ₀ / 2a)²)', 'a = 22.86 mm for WR-90; cut-off wavelength 2a'],
    1: ['VSWR of a mismatched load', 'The probe measures the standing wave: the ratio of its largest to smallest field is the voltage standing-wave ratio S = (1 + |Γ|)/(1 − |Γ|). The crystal detector is square-law, so its current goes as the power of the field and S = √(I_max / I_min).', 'S = √(I_max / I_min)', 'valid while the crystal follows a square law'],
    2: ['The double-minimum method for a high VSWR', 'When S is large the minimum is so sharp that I_max/I_min cannot be read. Instead the width Δx of the minimum, between the two points where the power is twice its minimum, gives S = √(1 + 1/sin²(πΔx/λg)).', 'S = √(1 + 1/sin²(π Δx / λg))', 'Δx is measured at twice the minimum power'],
    3: ['Load impedance on the slotted line', 'A short circuit in place of the load gives reference minima. The shift of the first minimum when the unknown load is fitted, together with the VSWR, gives the load: z = (1 − jS tan βd)/(S − j tan βd), where d is the distance of the first minimum from the load and β = 2π/λg.', 'z = (1 − jS tan βd) / (S − j tan βd)', 'd = λg/2 − (shift of the minimum toward the load)'],
    4: ['Dielectric constant by the slab shift method', 'A slab of length l against the short changes the load seen by the line, so every minimum moves by Δ. The slab-filled guide has phase constant βd = √(εr k₀² − (π/a)²), and tan(β(l − Δ)) = (β/βd) tan(βd l) gives εr.', 'tan β(l − Δ) = (β / β_d) tan(β_d l)', 'β_d = √(εr k₀² − (π/a)²)']
  };
  var KTX = ['The reflex klystron: modes and electronic tuning', 'Electrons are turned back by the reflector and return to the cavity after a transit time. The tube oscillates only if they return at the right phase, N = n + 3/4 transit cycles. Each n is a mode: a window of reflector voltage in which the power rises and falls, and the frequency is pulled either side of the cavity frequency (electronic tuning).', 'N = 2 L f √(2 m V₀ / e) / (V₀ + Vr) = n + 3/4', 'the reflector voltage at the centre of mode n'];
  var GTX = ['The Gunn oscillator: I-V characteristic and threshold', 'In gallium arsenide the electrons are scattered to a heavier, slower valley when the field exceeds about 3.2 kV/cm. The current then falls and a domain of high field crosses the diode, giving microwave oscillation at a frequency vd/L. The current maximum is the threshold voltage V_th = E_th L.', 'V_th = E_th · L', 'oscillation frequency f = v_d / L'];
  var TT = IS_KLYS ? KTX : IS_GUNN ? GTX : TX[TASK] || TX[0];
  var VIVA = IS_KLYS ? [['Why are there several separate reflector-voltage windows?', ['The electrons must return at N = n + 3/4 cycles; each n is a mode', 'The tube has several cavities', 'The supply is noisy'], 0, 'Only certain reflector voltages bring the bunch back at the right phase.'], ['Which mode has the highest reflector voltage?', ['The one with the smallest n', 'The one with the largest n', 'They all have the same'], 0, 'V_r + V₀ falls as 1/(n + 3/4).']]
    : IS_GUNN ? [['Why does the current of a Gunn diode fall above the threshold?', ['Electrons move to a slower, heavier valley', 'The diode overheats', 'The supply limits it'], 0, 'The negative differential mobility is what makes the oscillation possible.'], ['What sets the oscillation frequency of a transit-time Gunn diode?', ['v_d / L', 'The bias only', 'The supply ripple'], 0, 'A domain crosses the active length L at the drift velocity v_d.']]
    : [['The guide wavelength is longer than the free-space wavelength because', ['of the cut-off of the guide', 'the wave slows down', 'of the probe'], 0, 'λg = λ₀/√(1 − (λ₀/2a)²).'], ['The crystal detector reads', ['power, so I_max/I_min = S²', 'voltage, so I_max/I_min = S', 'frequency'], 0, 'A square-law detector gives a current proportional to power.']];

  function askState() {
    var q = { experiment: S.lab.title, source_on: st.on };
    if (IS_LINE) { q.probe_mm = r(st.x * 1000, 2); q.detector_current = r(reading().v, 2); q.frequency_GHz = r(p.f / 1e9, 3); } else if (IS_KLYS) { q.reflector_V = r(st.vr, 1); q.power_mW = r(reading().v, 2); } else { q.bias_V = r(st.vb, 2); q.current_mA = r(reading().v, 1); }
    q.readings = S.rows.length; return q;
  }

  // ================================================================ steps
  var STEPS = [];
  function stepOn() {
    return { id: 'on', title: 'Switch on', view: 'supply', render: function (u) {
        u.h2('Switch on the source');
        u.p(IS_KLYS ? 'Switch the supply on, wait for the klystron heater to warm up, and check that the beam is on at 300 V.' : IS_GUNN ? 'Switch the supply on. The bias starts at zero.' : 'Switch the Gunn supply on and set the attenuator so that the detector current stays below the top of its scale.');
        u.task('1. Supply', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switch off' : 'Switch on', function () { S.focus('supply'); switchOn(!st.on); }, !st.on, S.hand.busy));
        if (IS_KLYS) u.task('2. Warm-up', st.warm, st.warm ? 'Beam on' : 'Heater warming').add(u.button('Wait for warm-up', function () { warmUp(); }, false, !st.on || st.warm || S.hand.busy));
        if (IS_LINE && TASK === 3) u.note('First the short circuit is on the end of the line; it gives the reference minima.');
        u.note('The microwave power is a few milliwatts. Never look into an open waveguide or horn, and never aim a horn at anyone.');
        u.next('Next', IS_KLYS ? st.on && st.warm : st.on);
      }, ok: function () { return IS_KLYS ? st.on && st.warm : st.on; },
      auto: function () { return switchOn(true).then(function () { return IS_KLYS ? warmUp() : null; }); } };
  }
  function probeBlock(u) {
    u.slider('Probe position', 0, 100, 0.05, function () { return r(st.x * 1000, 2); }, function (v) { moveProbe(v / 1000, false); paintDial(); }, 'mm', 2);
    u.live(function () { return 'Detector current ' + r(reading().v, 2) + ' µA at ' + r(st.x * 1000, 2) + ' mm'; });
  }
  function nav(u) { return u; }
  if (IS_LINE) {
    STEPS.push(stepOn());
    if (TASK === 0) STEPS.push({ id: 'min', title: 'Minima', view: 'carriage', render: function (u) {
        u.h2('Find successive minima');
        u.p('Slide the probe along the slot and find the positions where the detector current dips to its smallest value. Find at least two successive minima.');
        probeBlock(u); u.row(u.button('Nearest minimum', function () { S.focus('carriage'); goMin(0); }, false, S.hand.busy), u.button('Next minimum →', function () { goMin(1); }, false, S.hand.busy), u.button('Write it down', function () { lineRecord('m'); }, true, S.hand.busy));
        u.h3('Observation table'); u.table(); u.next('Next: result', rowsOf('m').length >= 2);
      }, ok: function () { return rowsOf('m').length >= 2; },
      auto: function () { return moveProbe(0.003).then(function () { return goMin(0); }).then(function () { lineRecord('m'); return goMin(1); }).then(function () { lineRecord('m'); return goMin(1); }).then(function () { lineRecord('m'); }); } });
    if (TASK === 1) STEPS.push({ id: 'swr', title: 'Maximum and minimum', view: 'carriage', render: function (u) {
        u.h2('Maximum and minimum of the standing wave');
        u.p('Find a maximum and a minimum of the detector current; write both down. The horn is radiating into an empty room: nothing is aimed at anyone.');
        probeBlock(u); u.row(u.button('Nearest maximum', function () { S.focus('carriage'); goMax(); }, false, S.hand.busy), u.button('Nearest minimum', function () { goMin(0); }, false, S.hand.busy));
        u.row(u.button('Write down the maximum', function () { lineRecord('M'); }, true, S.hand.busy), u.button('Write down the minimum', function () { lineRecord('m'); }, true, S.hand.busy));
        u.h3('Observation table'); u.table(); u.next('Next: result', rowsOf('m').length >= 1 && rowsOf('M').length >= 1);
      }, ok: function () { return rowsOf('m').length >= 1 && rowsOf('M').length >= 1; },
      auto: function () { return moveProbe(0.02).then(function () { return goMax(); }).then(function () { lineRecord('M'); return goMin(0); }).then(function () { lineRecord('m'); }); } });
    if (TASK === 2) STEPS.push({ id: 'dm', title: 'Double minimum', view: 'carriage', render: function (u) {
        u.h2('Width of the minimum at twice the power');
        u.p('Find a minimum and note its current. Then move the probe to each side until the current is twice the minimum; the distance between those two positions is Δx. λg is calculated from the frequency ' + r(p.f / 1e9, 2) + ' GHz and a = 22.86 mm: ' + r(lamCalc() * 1000, 2) + ' mm.');
        probeBlock(u); u.row(u.button('Nearest minimum', function () { goMin(0); }, false, S.hand.busy), u.button('Go to the twice-minimum points', function () { goTwice(); }, false, S.hand.busy));
        u.row(u.button('Write down the minimum', function () { lineRecord('m'); }, false, S.hand.busy), u.button('Write down this point (a)', function () { lineRecord('a'); }, false, S.hand.busy), u.button('Write down this point (b)', function () { lineRecord('b'); }, false, S.hand.busy));
        u.h3('Observation table'); u.table(); u.next('Next: result', rowsOf('a').length >= 1 && rowsOf('b').length >= 1);
      }, ok: function () { return rowsOf('a').length >= 1 && rowsOf('b').length >= 1; },
      auto: function () { return moveProbe(0.02).then(function () { return goMin(0); }).then(function () { lineRecord('m'); return goTwice(); }).then(function (o) { return moveProbe(o.a).then(function () { lineRecord('a'); return moveProbe(o.b); }).then(function () { lineRecord('b'); }); }); } });
    if (TASK === 3) {
      STEPS.push({ id: 'ref', title: 'Short-circuit reference', view: 'carriage', render: function (u) {
          u.h2('Reference minimum with the short circuit');
          u.p('With the short circuit on the end of the line, find a minimum and write it down. It marks a plane that is a whole number of half-wavelengths from the load.');
          probeBlock(u); u.row(u.button('Nearest minimum', function () { goMin(0); }, false, S.hand.busy), u.button('Write it down', function () { lineRecord('S'); }, true, S.hand.busy));
          u.h3('Observation table'); u.table(); u.next('Next: the unknown load', rowsOf('S').length >= 1);
        }, ok: function () { return rowsOf('S').length >= 1; },
        auto: function () { return moveProbe(0.06).then(function () { return goMin(0); }).then(function () { lineRecord('S'); }); } });
      STEPS.push({ id: 'unk', title: 'Unknown load', view: 'load', render: function (u) {
          u.h2('The unknown load');
          u.task('Fit the load', st.load === 'unknown', st.load === 'unknown' ? 'Slide-screw tuner on the line' : 'Short circuit still on').add(u.button('Fit the unknown load', function () { S.focus('load'); fitLoad('unknown'); }, st.load !== 'unknown', S.hand.busy || st.load === 'unknown'));
          u.p('Find the first minimum nearest to the one you recorded and write it down, then the maximum nearest it: the ratio gives the VSWR.');
          probeBlock(u); u.row(u.button('Nearest minimum', function () { goMin(0); }, false, S.hand.busy), u.button('Nearest maximum', function () { goMax(); }, false, S.hand.busy));
          u.row(u.button('Write down the minimum', function () { lineRecord('m'); }, true, S.hand.busy), u.button('Write down the maximum', function () { lineRecord('M'); }, true, S.hand.busy));
          u.h3('Observation table'); u.table(); u.next('Next: result', rowsOf('m').length >= 1 && rowsOf('M').length >= 1);
        }, ok: function () { return rowsOf('m').length >= 1 && rowsOf('M').length >= 1; },
        auto: function () { var sx = rowsOf('S')[0].x; return fitLoad('unknown').then(function () { return moveProbe(sx); }).then(function () { return goMin(0); }).then(function () { lineRecord('m'); return goMax(); }).then(function () { lineRecord('M'); }); } });
    }
    if (TASK === 4) {
      STEPS.push({ id: 'ref', title: 'Short only', view: 'carriage', render: function (u) {
          u.h2('Reference minimum with the short circuit alone');
          u.p('With no slab in the guide, find a minimum near the middle of the slot and write it down.');
          probeBlock(u); u.row(u.button('Nearest minimum', function () { goMin(0); }, false, S.hand.busy), u.button('Write it down', function () { lineRecord('S'); }, true, S.hand.busy));
          u.h3('Observation table'); u.table(); u.next('Next: with the slab', rowsOf('S').length >= 1);
        }, ok: function () { return rowsOf('S').length >= 1; }, auto: function () { return moveProbe(0.05).then(function () { return goMin(0); }).then(function () { lineRecord('S'); }); } });
      STEPS.push({ id: 'slab', title: 'With the slab', view: 'load', render: function (u) {
          u.h2('Put the slab against the short');
          u.task('Slab in the guide', st.slab, st.slab ? 'Slab, ' + r(p.ls * 1000, 1) + ' mm' : 'No slab').add(u.button('Put the slab in', function () { S.focus('load'); fitSlab(true); }, !st.slab, S.hand.busy || st.slab));
          u.p('The standing wave shifts. Find the minimum nearest to your reference and write it down; the shift gives εr.');
          probeBlock(u); u.row(u.button('Nearest minimum', function () { goMin(0); }, false, S.hand.busy), u.button('Write it down', function () { lineRecord('W'); }, true, S.hand.busy));
          u.h3('Observation table'); u.table(); u.next('Next: result', rowsOf('W').length >= 1);
        }, ok: function () { return rowsOf('W').length >= 1; },
        auto: function () { var sx = rowsOf('S')[0].x; return fitSlab(true).then(function () { return moveProbe(sx); }).then(function () { return goMin(0); }).then(function () { lineRecord('W'); }); } });
    }
  } else if (IS_KLYS) {
    STEPS.push(stepOn());
    STEPS.push({ id: 'modes', title: 'Mode chart', view: 'plot', render: function (u) {
        u.h2('Sweep the reflector voltage');
        u.p('Turn the reflector voltage from 20 to 500 V and watch the power: it rises and falls in separate windows, the modes.');
        u.row(u.button('Sweep 20 → 500 V', function () { S.focus('supply'); sweep(); }, true, S.hand.busy || !st.warm));
        var cv = document.createElement('canvas'); cv.width = 760; cv.height = 330; cv.style.cssText = 'width:100%;border-radius:10px;border:1px solid var(--line);background:#0d1a14'; u.el(cv); plotCv = cv; drawPlot(cv.getContext('2d'), 760, 330);
        u.next('Next: measure a mode', st.trace.length > 0);
      }, ok: function () { return st.trace.length > 0; }, auto: function () { return sweep(); } });
    STEPS.push({ id: 'centre', title: 'Mode centres', view: 'supply', render: function (u) {
        u.h2('Centre and tuning range of a mode');
        u.p('Set the reflector voltage near a mode, press "Tune to the mode centre", then "Write it down": the book finds the two half-power voltages and reads the frequency with the wavemeter at each. Do the modes near 180 V and, if you like, the others.');
        u.slider('Reflector voltage', 20, 500, 1, function () { return Math.round(st.vr); }, function (v) { setControl(v, false); paintDial(); paintMon(); }, 'V', 0);
        u.row(u.button('Tune to the mode centre', function () { S.focus('supply'); nearestCentre(); }, false, S.hand.busy || !st.warm), u.button('Write it down', function () { klysRecord(); }, true, S.hand.busy));
        u.live(function () { return 'Vr ' + r(st.vr, 1) + ' V · power ' + r(reading().v, 2) + ' mW · ' + (freqNow() > 0 ? 'f = ' + r(KN.freq(p, st.vr) / 1e9, 4) + ' GHz' : 'not oscillating'); });
        u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.some(function (rw) { return rw.n === Math.round(p.mode); }));
      }, ok: function () { return S.rows.some(function (rw) { return rw.n === Math.round(p.mode); }); },
      auto: function () { return setControl(Math.round(KN.K(p) / (Math.round(p.mode) + 0.75) - p.V0 + 6)).then(function () { return nearestCentre(); }).then(function () { return klysRecord(); }); } });
  } else {
    STEPS.push(stepOn());
    STEPS.push({ id: 'iv', title: 'I-V characteristic', view: 'supply', render: function (u) {
        u.h2('Current against bias');
        u.p('Raise the bias in steps (0.5 V, and 0.1 V near the maximum of the current) and write down the current and the power. The current rises, peaks and falls; the peak is the threshold. At least eight readings.');
        u.slider('Bias voltage', 0, 12, 0.1, function () { return st.vb; }, function (v) { setControl(v, false); paintDial(); paintMon(); }, 'V', 1);
        u.row(u.button('Write it down', function () { gunnRead(); paintMon(); }, true, S.hand.busy));
        u.live(function () { return 'V ' + r(st.vb, 1) + ' · ' + r(reading().v, 1) + ' mA · power ' + r(KN.power(p, st.vb), 2) + ' mW' + (freqNow() > 0 ? ' · ' + freqNow() + ' GHz' : ''); });
        var cv = document.createElement('canvas'); cv.width = 760; cv.height = 300; cv.style.cssText = 'width:100%;border-radius:10px;border:1px solid var(--line);background:#0d1a14'; u.el(cv); plotCv = cv; drawPlot(cv.getContext('2d'), 760, 300);
        u.h3('Observation table'); u.table(); u.next('Next: result', S.rows.length >= 8);
      }, ok: function () { return S.rows.length >= 8; },
      auto: function () { var chain = Promise.resolve(), vs = [], i; for (i = 0; i <= 24; i++) vs.push(i * 0.5); for (i = 0; i <= 10; i++) vs.push(3.0 + i * 0.1);
        vs.forEach(function (v) { chain = chain.then(function () { return setControl(Math.round(v * 10) / 10, false); }).then(function () { gunnRead(); }); }); return chain.then(function () { paintMon(); return setControl(0, true); }); } });
  }

  var cols = IS_KLYS ? [{ label: 'Mode n', get: function (rw) { return rw.n; } }, { label: 'Vr centre (V)', get: function (rw) { return r(rw.vr, 1); } }, { label: 'P (mW)', get: function (rw) { return r(rw.P, 2); } },
      { label: 'Vr half-power (V)', get: function (rw) { return r(rw.vlo, 1) + ' / ' + r(rw.vhi, 1); } }, { label: 'f at half-power (MHz)', get: function (rw) { return rw.flo + ' / ' + rw.fhi; } }, { label: 'Range (MHz)', get: function (rw) { return r(rw.et, 1); } }]
    : IS_GUNN ? [{ label: 'V (V)', get: function (rw) { return rw.V; } }, { label: 'I (mA)', get: function (rw) { return rw.I; } }, { label: 'P (mW)', get: function (rw) { return rw.P; } }, { label: 'f (GHz)', get: function (rw) { return rw.f || '—'; } }]
    : [{ label: 'Reading', get: function (rw) { return { m: 'minimum', M: 'maximum', S: 'short min', a: 'point a', b: 'point b', W: 'min with slab' }[rw.kind]; } }, { label: 'x (mm)', get: function (rw) { return r(rw.x * 1000, 2); } }, { label: 'I (µA)', get: function (rw) { return r(rw.I, 2); } }];

  return {
    camera: { pos: [-0.2, 0.62, 1.3], look: [-0.2, 0.06, -0.2] },
    views: { supply: [[-0.62, 0.3, 0.14], [-0.76, 0.08, -0.26]], source: [[-0.52, 0.22, 0.12], [-0.6, 0.09, -0.22]], iso: [[-0.5, 0.22, 0.12], [-0.51, 0.09, -0.22]], att: [[-0.4, 0.22, 0.12], [-0.42, 0.09, -0.22]],
      wav: [[-0.32, 0.22, 0.12], [-0.33, 0.09, -0.22]], line: [[-0.08, 0.3, 0.16], [-0.08, 0.09, -0.22]], carriage: [[-0.06, 0.24, 0.0], [-0.06, 0.09, -0.22]],
      load: [[0.04, 0.2, 0.1], [0.04, 0.09, -0.22]], ind: [[0.2, 0.26, 0.26], [0.22, 0.1, -0.02]], plot: [[0.36, 0.3, 0.1], [0.4, 0.18, -0.4]], bench: [[-0.2, 0.62, 1.3], [-0.2, 0.06, -0.2]], book: [[-0.3, 0.42, 0.55], [-0.2, 0.0, 0.0]] },
    theory: { principle: TT[1], formula: TT[2], formulaNote: TT[3],
      more: ['Waveguide WR-90 (22.86 mm × 10.16 mm) carries the TE10 mode between 6.56 and 13.1 GHz; below the cut-off frequency c/2a = 6.56 GHz nothing propagates.', 'The source here is a Gunn or klystron oscillator of a few milliwatts, kept steady by an isolator so that reflections cannot pull its frequency.'],
      precautions: 'Microwave power here is only a few milliwatts, but never look into an open waveguide or horn and never aim a horn at a person. Keep the supply voltages within their ranges.' },
    book: { title: 'Expt. - ' + S.lab.title, at: [-0.28, 0.1, 0.1], lines: ['Aim: ' + S.lab.aim.slice(0, 76), SAMPLE || 'X-band bench, WR-90 waveguide', IS_LINE ? 'f = ' + r(p.f / 1e9, 2) + ' GHz,  a = 22.86 mm' : 'Supply voltages within their ranges', 'Safety: no horn aimed at anyone.'], columns: cols },
    result: result, tol: IS_GUNN ? 0.03 : IS_KLYS ? 0.03 : (TASK === 2 ? 0.03 : 0.02),
    resultNote: 'The positions come from searching the detector response of the simulated bench; a real slotted line is read to about 0.01 mm, which is what sets the last digit here.',
    chips: ['What is the guide wavelength?', 'Why a square-law detector?', 'What is a mode?', 'Check my reading', 'Why an isolator?'],
    viva: VIVA, askState: askState, steps: STEPS,
    tick: function () {
      if (dirty) { dirty = false; paintDial(); paintMon(); }
      hudA.set(IS_LINE ? r(st.x * 1000, 2) + ' mm' : IS_KLYS ? r(st.vr, 1) + ' V' : r(st.vb, 2) + ' V'); hudB.set(r(reading().v, 2) + ' ' + reading().unit); hudC.set(S.rows.length + ' written');
    },
    ready: function () { paintDial(); paintMon(); }
  };
});
