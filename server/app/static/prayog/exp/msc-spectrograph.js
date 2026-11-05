/* Prayogshala studio module: SPECTROGRAPH BENCH (M.Sc. spectroscopy).
   A scanning monochromator with a source, a sample compartment, a detector and a readout screen. One rig serves every
   spectroscopy set-up of the pack packs/msc_optics.js: the kernel named by the lab supplies the signal at every
   position (profile), the range (axis) and the lines the instrument's peak-pick would find (lines); the student
   scans, puts the cursor on a line and records it. The constants in each spectrum come from the lab's own params. */
HoolaStudio.define('msc-spectrograph', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME];
  var p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {};
  var TAB = S.lab.table || {}, CALC = HK.CALCS[TAB.calc], TXT = HK.TEXTBOOK[(S.lab.check || {}).textbook];
  var CTRL = KN.CONTROL || null, NMODE = (KN.MODES || []).length;

  var INFO = {
    msc_iodine: { sample: 'Iodine vapour in a sealed quartz cell', kind: 'gas', col: 0xb773c4, src: 'Halogen lamp', det: 'Photomultiplier', need: 8, xd: 2, cur: 'Wavelength', hint: 'Number the bands from the red end (1, 2, 3 ...) and record each band head.' },
    msc_rovib: { sample: 'Gas cell with KBr windows', kind: 'gas', col: 0xdfe9ee, src: 'Globar (hot ceramic rod)', det: 'DTGS detector', need: 3, xd: 2, cur: 'Wavenumber', hint: 'Number the lines from the gap: R(0), R(1) ... on the high side (+1, +2 ...) and P(1), P(2) ... on the low side (-1, -2 ...).' },
    msc_raman: { sample: 'Liquid in a 10 mm cuvette', kind: 'cuvette', col: 0xe8eef0, src: '532 nm laser (interlocked)', det: 'CCD behind the spectrometer', need: 1, xd: 1, cur: 'Raman shift', hint: 'Strongest Stokes line is 1; its anti-Stokes partner is -1.' },
    msc_fluor: { sample: 'Fluorophore solution in a quartz cuvette', kind: 'cuvette', col: 0xc9e6ee, src: 'Xenon lamp', det: 'Photomultiplier', need: 2, xd: 1, cur: 'Wavelength', hint: 'Absorption peak is band 1 and emission peak is band 2.' },
    msc_tauc: { sample: 'Thin film on a glass slide', kind: 'film', col: 0xd9c35a, src: 'Deuterium and halogen lamps', det: 'Photodiode', need: 6, xd: 1, cur: 'Wavelength', hint: 'Record about eight points on the steep part of the edge.' },
    msc_varshni: { sample: 'GaAs wafer on the cryostat cold finger', kind: 'cryo', col: 0x5a5f66, src: '532 nm laser (interlocked)', det: 'Photodiode behind the monochromator', need: 2, xd: 1, cur: 'Wavelength', hint: 'Record the peak at 300 K, cool with liquid nitrogen, then record the peak at 77 K.' },
    msc_decay: { sample: 'Ruby crystal in front of the photodiode', kind: 'crystal', col: 0xc4283c, src: 'Xenon flash lamp', det: 'Photodiode and oscilloscope', need: 6, xd: 2, cur: 'Time', hint: 'Record time and voltage at about eight points along the decay.' },
    msc_glow: { sample: 'Irradiated chip on the heater plate', kind: 'heater', col: 0xe6dfcf, src: 'No lamp: the crystal itself glows', det: 'Photomultiplier', need: 3, xd: 1, cur: 'Temperature', hint: 'Choose a heating rate, heat, record the peak. Use four different rates.' },
    msc_beer: { sample: 'Rhodamine 6G in ethanol, 10 mm cell', kind: 'cuvette', col: 0xe0457b, src: 'Deuterium and halogen lamps', det: 'Photodiode', need: 4, xd: 1, cur: 'Wavelength', hint: 'Record the absorbance at the peak for each concentration.' }
  };
  var I = INFO[KNAME] || INFO.msc_fluor;
  var SAMPLE = V_.sample || I.sample;
  var hasLines = !!KN.lines;
  var st = { on: false, loaded: false, mode: 0, ci: 0, cursor: null, trace: {}, scanned: {}, upto: 1, sel: -1, cooled: false };
  if (CTRL) p[CTRL.param] = CTRL.values[0];

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function key() { return st.mode + '|' + (CTRL ? st.ci : 0); }
  function AX() { return KN.axis(p); }
  function lineList() {
    if (!hasLines) return [];
    if (!st.linesCache) st.linesCache = {};
    var k = key();
    if (!st.linesCache[k]) {
      var ls = KN.lines(p, st.mode) || [];
      st.linesCache[k] = ls.slice().sort(function (a, b) { return a.x - b.x; });
    }
    return st.linesCache[k];
  }
  function applyCtrl(i) {
    st.ci = i; if (CTRL) p[CTRL.param] = CTRL.values[i];
    var ax = AX(); if (st.cursor === null || st.cursor < ax.lo || st.cursor > ax.hi) st.cursor = (ax.lo + ax.hi) / 2;
  }
  function ctrlRaw() { return CTRL ? CTRL.values[st.ci] : undefined; }
  function ctrlShow() { return CTRL ? rnd(CTRL.values[st.ci] * CTRL.scale, CTRL.digits) + ' ' + CTRL.unit : ''; }
  var ax0 = AX(); st.cursor = ax0.lo + (ax0.hi - ax0.lo) * 0.5;

  // ================================================================ the bench
  function box(w, h, d, mat, x, y, z, parent, r) {
    var m = S.rounded(w, h, d, r === undefined ? 0.006 : r, mat); m.rotation.x = -Math.PI / 2;
    m.position.set(x, y, z); (parent || S.scene).add(m); return m;
  }
  var cream = new T.MeshStandardMaterial({ color: 0xe3dfd3, roughness: 0.5, metalness: 0.1 });
  var dark = new T.MeshStandardMaterial({ color: 0x22262c, roughness: 0.6 });

  // source
  var srcG = new T.Group(); S.scene.add(srcG); srcG.position.set(-0.7, 0, -0.17);
  box(0.14, 0.11, 0.12, dark, 0, 0.055 + 0.003, 0, srcG);
  var srcLens = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.03, 20), M.chrome); srcLens.rotation.z = Math.PI / 2; srcLens.position.set(0.085, 0.06, 0); srcG.add(srcLens);
  var srcLab = S.label(I.src.length > 26 ? I.src.slice(0, 26) : I.src, { w: 0.12, ratio: 0.14, bg: '#2f343b', color: '#e9e6dc', px: 512 }); srcLab.position.set(0, 0.075, 0.0613); srcG.add(srcLab);
  var pwr = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.008, 16), M.red); pwr.rotation.x = Math.PI / 2; pwr.position.set(-0.04, 0.035, 0.063); srcG.add(pwr);
  S.contact(0.2, 0.18, -0.7, -0.17, 0.5);

  // sample compartment (a lidded dark box on the beam line)
  var comp = new T.Group(); S.scene.add(comp); comp.position.set(-0.42, 0, -0.17);
  box(0.16, 0.08, 0.13, dark, 0, 0.043, 0, comp);
  var lid = box(0.15, 0.01, 0.12, new T.MeshStandardMaterial({ color: 0x2c3036, roughness: 0.5 }), 0, 0.088, 0, comp);
  var holder = new T.Group(); holder.position.set(0, 0.083, 0); comp.add(holder);
  S.contact(0.22, 0.2, -0.42, -0.17, 0.5);

  // monochromator
  var mono = new T.Group(); S.scene.add(mono); mono.position.set(-0.04, 0, -0.17);
  var MW = 0.3, MD = 0.2, MH = 0.13;
  box(MW, MH, MD, cream, 0, MH / 2 + 0.004, 0, mono, 0.01);
  var FZ = MD / 2 + 0.0035;
  var panelTex = S.canvasTex(1200, 460, function (x, w, h) {
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
    x.fillStyle = '#f1efe8'; x.font = '700 50px "Public Sans", sans-serif'; x.fillText('SCANNING MONOCHROMATOR', 36, 78);
    x.font = '500 30px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('GRATING  ·  PRE-ALIGNED  ·  SLITS 1 mm', 36, 122);
    x.fillStyle = '#f1efe8'; x.font = '700 30px "Public Sans", sans-serif'; x.fillText('POWER', 86, 400); x.fillText('SCAN', 820, 400);
  });
  var fp = S.mesh(new T.BoxGeometry(MW - 0.016, MH - 0.016, 0.003), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: panelTex, roughness: 0.45 }), M.grey]);
  fp.position.set(0, MH / 2 + 0.004, FZ - 0.0015); mono.add(fp);
  function pp(u, v) { return new T.Vector3(u, 0.004 + MH / 2 + v, FZ + 0.004); }
  var onB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.01, 20), M.red); onB.rotation.x = Math.PI / 2; onB.position.copy(pp(-0.1, -0.038)); mono.add(onB);
  var scanB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.01, 20), M.green); scanB.rotation.x = Math.PI / 2; scanB.position.copy(pp(0.08, -0.038)); mono.add(scanB);
  var dialTex = S.liveTex(360, 150);
  var dial = new T.Mesh(new T.PlaneGeometry(0.09, 0.0375), new T.MeshBasicMaterial({ map: dialTex, toneMapped: false })); dial.position.copy(pp(-0.03, 0.008)); mono.add(dial);
  var drum = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.012, 28), M.brass); drum.rotation.x = Math.PI / 2; drum.position.copy(pp(0.085, 0.012)); mono.add(drum);
  var tick = S.mesh(new T.BoxGeometry(0.003, 0.014, 0.003), M.black); tick.position.copy(pp(0.085, 0.024)); tick.position.z += 0.007; mono.add(tick);
  [-1, 1].forEach(function (sgn) { var t = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.05, 20), M.chrome); t.rotation.z = Math.PI / 2; t.position.set(sgn * (MW / 2 + 0.025), 0.06, 0); mono.add(t); });
  S.contact(0.42, 0.28, -0.04, -0.17, 0.5);

  // detector
  var det = new T.Group(); S.scene.add(det); det.position.set(0.26, 0, -0.17);
  var dt = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.13, 28), M.alu); dt.rotation.z = Math.PI / 2; dt.position.y = 0.065; det.add(dt);
  var dcap = S.mesh(new T.CylinderGeometry(0.032, 0.032, 0.012, 28), M.black); dcap.rotation.z = Math.PI / 2; dcap.position.set(0.07, 0.065, 0); det.add(dcap);
  var dlab = S.label(I.det.length > 22 ? I.det.slice(0, 22) : I.det, { w: 0.08, ratio: 0.14, bg: '#d6dade', color: '#222', px: 512 }); dlab.position.set(0, 0.098, 0.0); dlab.rotation.x = -Math.PI / 2; det.add(dlab);
  S.contact(0.18, 0.1, 0.26, -0.17, 0.45);
  var cab = S.wire([new T.Vector3(0.3, 0.06, -0.17), new T.Vector3(0.36, 0.02, -0.12), new T.Vector3(0.44, 0.012, -0.12)], 0x222222); if (cab) S.scene.add(cab);

  // readout screen
  var scrTex = S.liveTex(900, 520);
  var scrG = new T.Group(); S.scene.add(scrG); scrG.position.set(0.55, 0, -0.2); scrG.rotation.y = -0.4;
  var scrBody = S.rounded(0.3, 0.04, 0.2, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.6 })); scrBody.position.set(0, 0.11, 0); scrBody.rotation.x = -0.15; scrG.add(scrBody);
  var scrFace = new T.Mesh(new T.PlaneGeometry(0.28, 0.162), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scrFace.position.set(0, 0.11, 0.0215); scrFace.rotation.x = -0.15; scrG.add(scrFace);
  var scrNeck = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.06, 16), M.iron); scrNeck.position.y = 0.04; scrG.add(scrNeck);
  var scrBase = S.mesh(new T.CylinderGeometry(0.035, 0.04, 0.012, 24), M.iron); scrBase.position.y = 0.006; scrG.add(scrBase);
  S.contact(0.28, 0.2, 0.55, -0.2, 0.45);

  // the sample piece, and the accessory for the kind of experiment
  var samp = new T.Group(); S.scene.add(samp);
  var BENCHPOS = new T.Vector3(-0.34, 0.004, 0.06); samp.position.copy(BENCHPOS);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xdfe6ea, roughness: 0.03, transmission: 0.85, thickness: 0.002, transparent: true, opacity: 0.45 });
  function liqMat() { return new T.MeshPhysicalMaterial({ color: I.col, transmission: 0.4, roughness: 0.08, thickness: 0.01, transparent: true, opacity: 0.88 }); }
  if (I.kind === 'gas') {
    var gc = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.1, 24), glassM); gc.rotation.z = Math.PI / 2; gc.position.y = 0.02; samp.add(gc);
    var gf = S.mesh(new T.CylinderGeometry(0.0125, 0.0125, 0.096, 24), liqMat()); gf.material.opacity = 0.35; gf.rotation.z = Math.PI / 2; gf.position.y = 0.02; samp.add(gf);
    [-1, 1].forEach(function (s) { var w = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.008, 24), M.steel); w.rotation.z = Math.PI / 2; w.position.set(s * 0.054, 0.02, 0); samp.add(w); });
    var vv = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.02, 12), M.brass); vv.position.set(0, 0.04, 0); samp.add(vv);
  } else if (I.kind === 'cuvette') {
    var cg = S.mesh(new T.BoxGeometry(0.012, 0.045, 0.012), glassM); cg.position.y = 0.0225; samp.add(cg);
    var cl = S.mesh(new T.BoxGeometry(0.0095, 0.03, 0.0095), liqMat()); cl.position.y = 0.017; samp.add(cl);
  } else if (I.kind === 'film') {
    var sl = S.mesh(new T.BoxGeometry(0.026, 0.002, 0.076), glassM); sl.position.y = 0.0045; samp.add(sl);
    var fl = S.mesh(new T.BoxGeometry(0.024, 0.0004, 0.05), new T.MeshStandardMaterial({ color: I.col, roughness: 0.3, transparent: true, opacity: 0.8 })); fl.position.set(0, 0.0058, 0.012); samp.add(fl);
    var fh = S.mesh(new T.BoxGeometry(0.03, 0.02, 0.01), M.alu); fh.position.set(0, 0.014, -0.03); samp.add(fh);
  } else if (I.kind === 'cryo') {
    var dw = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.09, 32), M.alu); dw.position.y = 0.045; samp.add(dw);
    var dwin = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.004, 24), glassM); dwin.rotation.x = Math.PI / 2; dwin.position.set(0, 0.05, 0.03); samp.add(dwin);
    var dtop = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.03, 20), M.steel); dtop.position.y = 0.105; samp.add(dtop);
  } else if (I.kind === 'crystal') {
    var rc = S.mesh(new T.BoxGeometry(0.012, 0.012, 0.045), new T.MeshPhysicalMaterial({ color: I.col, transmission: 0.35, roughness: 0.1, thickness: 0.02, transparent: true, opacity: 0.9 })); rc.position.y = 0.018; samp.add(rc);
    var rb = S.mesh(new T.CylinderGeometry(0.018, 0.02, 0.012, 20), M.alu); rb.position.y = 0.006; samp.add(rb);
  } else {
    var hp = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.01, 30), M.alu); hp.position.y = 0.005; samp.add(hp);
    var hc = S.mesh(new T.BoxGeometry(0.014, 0.004, 0.014), new T.MeshStandardMaterial({ color: I.col, roughness: 0.8 })); hc.position.y = 0.012; samp.add(hc);
  }
  var accG = new T.Group(); S.scene.add(accG); accG.position.set(0.12, 0, 0.1);
  var accName = 'Bench accessory', accInfo = '';
  if (KNAME === 'msc_varshni') {
    var df = S.mesh(new T.CylinderGeometry(0.04, 0.036, 0.12, 28), M.alu); df.position.y = 0.06; accG.add(df);
    var dn = S.mesh(new T.CylinderGeometry(0.015, 0.02, 0.04, 20), M.steel); dn.position.y = 0.14; accG.add(dn);
    accName = 'Liquid-nitrogen dewar'; accInfo = 'Holds liquid nitrogen at 77 K. The technician pours it into the cryostat; you only watch the temperature.';
  } else if (KNAME === 'msc_glow') {
    var hb = box(0.12, 0.05, 0.08, dark, 0, 0.028, 0, accG);
    var hd = S.label('HEATER 0.5 - 4 K/s', { w: 0.1, ratio: 0.14, bg: '#14181d', color: '#7fd1b5', px: 512 }); hd.position.set(0, 0.03, 0.0413); accG.add(hd);
    accName = 'Heater controller'; accInfo = 'Raises the plate temperature at a steady rate you set, from room temperature.';
  } else if (KNAME === 'msc_beer') {
    var rk = box(0.14, 0.014, 0.05, M.wood, 0, 0.007, 0, accG, 0.003);
    for (var vi = 0; vi < 6; vi++) { var vl = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.045, 18), liqMat()); vl.material.opacity = 0.5 + 0.08 * vi; vl.position.set(-0.055 + vi * 0.022, 0.036, 0); accG.add(vl); }
    accName = 'Dilution series'; accInfo = 'Six volumetric dilutions of the stock dye, from 1 to 6 micromolar.';
  } else {
    var bk = box(0.1, 0.05, 0.06, M.grey, 0, 0.028, 0, accG);
    accName = 'Instrument electronics'; accInfo = 'Power supply and control electronics; nothing here to adjust.';
  }
  S.contact(0.16, 0.12, 0.12, 0.1, 0.4);
  var beam = S.mesh(new T.CylinderGeometry(0.002, 0.002, 0.64, 8), new T.MeshBasicMaterial({ color: 0xffd48a, transparent: true, opacity: 0.0 }), false, false);
  beam.rotation.z = Math.PI / 2; beam.position.set(-0.4, 0.075, -0.17); S.scene.add(beam);

  S.addApparatus('mono', mono, 'Scanning monochromator', 'A grating that sends one narrow band of wavelengths to the detector at a time. Pre-aligned: a student does not open it.');
  S.addApparatus('src', srcG, I.src, 'The light source for this measurement.');
  S.addApparatus('comp', comp, 'Sample compartment', 'A dark box with a lid on the beam line. The sample sits in its holder.');
  S.addApparatus('samp', samp, SAMPLE, 'The sample for this experiment. Handle it by the edges.');
  S.addApparatus('det', det, I.det, 'Turns the light that gets through the monochromator into a signal.');
  S.addApparatus('screen', scrG, 'Readout screen', 'Draws the signal against ' + (AX().xlabel || '').toLowerCase() + ' as the instrument scans. A cursor reads any point.');
  S.addApparatus('acc', accG, accName, accInfo);
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard(I.cur + ' at cursor'), hudB = S.hudCard('Signal'), hudC = S.hudCard(CTRL ? CTRL.label : 'Lines found');

  // ================================================================ drawing the trace and the dial
  function fmtX(v) { return rnd(v, I.xd).toFixed(I.xd); }
  function drawDial() {
    dialTex.draw(function (x, w, h) {
      x.fillStyle = '#10151b'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#4ad1b5'; x.font = '700 64px "Public Sans", sans-serif'; x.textAlign = 'center';
      x.fillText(st.on ? fmtX(st.cursor) : '---', w / 2, 82);
      x.font = '500 28px "Public Sans", sans-serif'; x.fillStyle = '#7d8795'; x.fillText(AX().unit, w / 2, 128);
    });
  }
  function ymaxOf(tr) { var m = 0; for (var i = 0; i < tr.length; i++) if (tr[i][1] > m) m = tr[i][1]; return Math.max(m * 1.15, 1e-9); }
  function drawScreen() {
    var ax = AX(), tr = st.trace[key()], ls = lineList();
    scrTex.draw(function (x, w, h) {
      x.fillStyle = '#10151b'; x.fillRect(0, 0, w, h);
      var L = 84, R = w - 24, Tp = 40, Bt = h - 62;
      var ym = tr ? ymaxOf(tr) : (ax.ymax || 1);
      var X = function (v) { return L + (v - ax.lo) / (ax.hi - ax.lo) * (R - L); }, Y = function (v) { return Bt - v / ym * (Bt - Tp); };
      x.strokeStyle = '#2b3340'; x.lineWidth = 1.5; x.fillStyle = '#7d8795'; x.font = '19px "Public Sans", sans-serif'; x.textAlign = 'center';
      var i, v;
      for (i = 0; i <= 6; i++) { v = ax.lo + (ax.hi - ax.lo) * i / 6; x.beginPath(); x.moveTo(X(v), Tp); x.lineTo(X(v), Bt); x.stroke(); x.fillText(String(Math.round(v * 10) / 10), X(v), Bt + 24); }
      x.textAlign = 'right';
      for (i = 0; i <= 4; i++) { v = ym * i / 4; x.beginPath(); x.moveTo(L, Y(v)); x.lineTo(R, Y(v)); x.stroke(); x.fillText(ym < 0.01 ? v.toExponential(1) : v.toFixed(ym < 3 ? 2 : 1), L - 8, Y(v) + 6); }
      x.fillStyle = '#aeb6c0'; x.textAlign = 'left'; x.font = '600 21px "Public Sans", sans-serif'; x.fillText((ax.ylabel || '').toUpperCase(), 12, 24);
      x.textAlign = 'right'; x.fillText((ax.xlabel || '').toUpperCase(), R, h - 12);
      if (NMODE) { x.textAlign = 'left'; x.fillStyle = '#ffb648'; x.fillText(KN.MODES[st.mode], L + 6, Tp + 24); }
      if (CTRL) { x.textAlign = 'right'; x.fillStyle = '#ffb648'; x.fillText(ctrlShow(), R - 6, Tp + 24); }
      if (!st.loaded) { x.fillStyle = '#7d8795'; x.textAlign = 'center'; x.font = '600 26px "Public Sans", sans-serif'; x.fillText('load the sample', (L + R) / 2, (Tp + Bt) / 2); return; }
      if (tr) {
        var n = Math.max(2, Math.floor(tr.length * st.upto));
        x.strokeStyle = '#ffb648'; x.lineWidth = 2.5; x.beginPath();
        for (i = 0; i < n; i++) { if (i) x.lineTo(X(tr[i][0]), Y(tr[i][1])); else x.moveTo(X(tr[i][0]), Y(tr[i][1])); }
        x.stroke();
        if (st.upto >= 1) {
          x.fillStyle = '#4ad1b5';
          ls.forEach(function (l) { x.beginPath(); x.moveTo(X(l.x), Y(l.y) - 8); x.lineTo(X(l.x) - 5, Y(l.y) - 16); x.lineTo(X(l.x) + 5, Y(l.y) - 16); x.closePath(); x.fill(); });
        }
      }
      x.strokeStyle = '#4ad1b5'; x.lineWidth = 1.5; x.setLineDash([5, 5]); x.beginPath(); x.moveTo(X(st.cursor), Tp); x.lineTo(X(st.cursor), Bt); x.stroke(); x.setLineDash([]);
      x.fillStyle = '#4ad1b5'; x.textAlign = 'left'; x.font = '600 22px "Public Sans", sans-serif';
      if (tr) x.fillText(fmtX(st.cursor) + ' ' + ax.unit + '   y = ' + sigAt(st.cursor).toPrecision(3), L + 8, Bt - 12);
    });
  }
  function sigAt(x) { return KN.profile(x, p, st.mode); }
  function redraw() { drawDial(); drawScreen(); }
  redraw();

  // ================================================================ human actions
  function powerOn() {
    if (busy()) return Promise.resolve();
    if (st.on) return Promise.resolve();
    return S.hand.tap(onB, 'front').then(function () {
      st.on = true; S.click(700, 0.05); beam.material.opacity = 0.55; pwr.material = M.green;
      S.say(I.src + ' and the electronics are on. Give them a minute to settle before a real measurement.'); redraw(); S.render();
    });
  }
  function loadSample() {
    if (busy()) return Promise.resolve();
    if (st.loaded) return Promise.resolve();
    if (!st.on) { S.say('Switch the instrument on first.'); return Promise.resolve(); }
    var from = samp.position.clone(), to = wpt(holder, 0, 0, 0);
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.02, 0)), function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.02 + 0.07 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, function (k) {
      samp.position.set(from.x + (to.x - from.x) * k, from.y + 0.07 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, { mode: 'side', ms: 1000, reachMs: 700 }).then(function () {
      samp.position.copy(to); st.loaded = true;
      S.say('Sample in the holder and the lid closed. ' + (I.kind === 'cuvette' ? 'Clear faces towards the light.' : ''));
      redraw(); S.render();
    });
  }
  function computeTrace() {
    var ax = AX(), n = ax.n, out = [], i;
    for (i = 0; i <= n; i++) { var x = ax.lo + (ax.hi - ax.lo) * i / n; out.push([x, KN.profile(x, p, st.mode)]); }
    return out;
  }
  function scan() {
    if (busy()) return Promise.resolve(false);
    if (!st.loaded) { S.say('Load the sample first.'); return Promise.resolve(false); }
    st.trace[key()] = computeTrace(); st.upto = 0;
    return S.hand.tap(scanB, 'front').then(function () {
      return S.tween(1700, function (k) { st.upto = k; drawScreen(); });
    }).then(function () {
      st.upto = 1; st.scanned[key()] = true;
      if (!st.sel || st.sel < 0) st.sel = -1;
      redraw(); S.say('Scan finished.' + (hasLines ? ' The instrument has marked ' + lineList().length + ' lines with green arrows.' : '')); S.render(); return true;
    });
  }
  function setCursor(v) {
    var ax = AX(); if (!isFinite(v)) return false;
    st.cursor = Math.max(ax.lo, Math.min(ax.hi, v)); redraw(); return true;
  }
  function stepLine(dir) {
    var ls = lineList(); if (!ls.length) { S.say('This spectrum has no marked lines: place the cursor by hand.'); return; }
    var i = 0, best = 1e99;
    ls.forEach(function (l, j) { var d = Math.abs(l.x - st.cursor); if (d < best) { best = d; i = j; } });
    if (best > 1e-6) { if (dir > 0 && ls[i].x < st.cursor) i += 1; else if (dir < 0 && ls[i].x > st.cursor) i -= 1; else i += dir; } else i += dir;
    i = Math.max(0, Math.min(ls.length - 1, i)); setCursor(ls[i].x);
  }
  function snapped() {
    var ls = lineList(), ax = AX(), tol = 0.0005 * (ax.hi - ax.lo), r = null;
    ls.forEach(function (l) { if (Math.abs(l.x - st.cursor) <= tol) r = l; });
    return r;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.loaded) { S.say('Load the sample first.'); return false; }
    if (!st.scanned[key()]) { S.say('Run the scan first.'); return false; }
    var c = ctrlRaw(), row;
    if (hasLines) {
      var l = snapped();
      if (!l) { S.say('Put the cursor on a marked line first (use Next line).'); return false; }
      var dup = S.rows.some(function (r) { return r.k === l.k && r.c === c; });
      if (dup) { S.say('Line ' + l.k + ' is already in your table.'); return false; }
      row = { k: l.k, x: l.x, y: l.y }; if (c !== undefined) row.c = c;
    } else {
      var x = st.cursor;
      if (S.rows.some(function (r) { return Math.abs(r.x - x) < 1e-9 * Math.max(1, Math.abs(x)); })) { S.say('You already have a reading there.'); return false; }
      row = { x: x, y: sigAt(x) };
    }
    S.addRow(row);
    S.say('Written in your record book: ' + (row.k !== undefined ? 'line ' + row.k + ', ' : '') + fmtX(row.x) + ' ' + AX().unit + '.');
    return true;
  }
  function setMode(i) {
    if (busy()) return; st.mode = i; applyCtrl(st.ci); redraw(); S.render();
  }
  function setCtrl(i) {
    if (busy()) return;
    if (KNAME === 'msc_varshni' && i === 1 && !st.cooled) { st.cooled = true; S.say('The technician pours liquid nitrogen into the cryostat. The wafer is at 77 K when the thermometer stops falling.'); }
    applyCtrl(i); redraw(); S.render();
  }

  // ================================================================ result, graph, columns
  function enough() {
    var calcOk = (function () { try { var v = CALC.fn(S.rows, p); return isFinite(v) && v !== 0; } catch (e) { return false; } })();
    var need = KNAME === 'msc_rovib' ? (S.lab.id.indexOf('hcl') >= 0 ? 8 : 2) : I.need;
    return calcOk && S.rows.length >= need;
  }
  function result(rows) {
    if (!enough()) return null;
    var k = TAB.result_k || 1, v = CALC.fn(rows, p), tr = TXT ? TXT(p) : undefined;
    var note = noteFor(rows, v);
    return { label: CALC.label.charAt(0).toUpperCase() + CALC.label.slice(1), value: v * k, unit: TAB.result_unit || CALC.unit,
      digits: TAB.result_digits, truth: tr === undefined ? undefined : tr * k, note: note };
  }
  function noteFor(rows, v) {
    var mu, r;
    if (KNAME === 'msc_rovib' && S.lab.id.indexOf('hcl') >= 0) {
      mu = p.m1 * p.m2 / (p.m1 + p.m2) * 1.66053906660e-27;
      r = Math.sqrt(6.62607015e-34 / (8 * Math.PI * Math.PI * 2.99792458e8 * mu * v * 100));
      return 'Bond length r = ' + (r * 1e10).toFixed(3) + ' angstrom (literature 1.275). The weaker lines in each doublet are H37Cl.';
    }
    if (KNAME === 'msc_rovib') return 'Band centre ' + ((function () { var a = rows.filter(function (q) { return q.k === 1; })[0], b = rows.filter(function (q) { return q.k === -1; })[0]; return a && b ? (a.x + b.x) / 2 : NaN; })()).toFixed(2) + ' cm-1 (midpoint of R(0) and P(1)).';
    if (KNAME === 'msc_raman') {
      var a = rows.filter(function (q) { return q.k === 1; })[0], b = rows.filter(function (q) { return q.k === -1; })[0];
      if (a && b && b.y > 0) {
        var nuL = 1e7 / p.lamL, ratio = Math.pow((nuL + a.x) / (nuL - a.x), 4) * a.y / b.y;
        if (ratio > 1) return 'From the anti-Stokes / Stokes ratio the sample is at about ' + (1.438777 * a.x / Math.log(ratio)).toFixed(0) + ' K.';
      }
      return 'Record the anti-Stokes line of the strongest line (k = -1) to get the temperature.';
    }
    if (KNAME === 'msc_iodine') return 'A Birge-Sponer extrapolation of the straight line to zero spacing would overestimate the dissociation energy; the real curve bends.';
    return '';
  }
  function numRows() { return S.rows; }
  function byK(k) { var f = S.rows.filter(function (r) { return r.k === k; }); return f.length ? f[f.length - 1] : null; }
  var graph = null;
  if (KNAME === 'msc_iodine') graph = { xlabel: 'band number + 1/2', ylabel: 'spacing (cm-1)', y0: 0,
    x: function (r) { return r.k + 0.5; }, y: function (r) { var q = byK(r.k + 1); return q ? 1e7 / q.x - 1e7 / r.x : NaN; },
    line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } };
  else if (KNAME === 'msc_rovib' && S.lab.id.indexOf('hcl') >= 0) graph = { xlabel: 'J + 1/2', ylabel: 'R(J-1) - P(J+1) (cm-1)', y0: 0,
    x: function (r) { return r.k > 0 ? r.k + 0.5 : NaN; }, y: function (r) { var q = byK(-(r.k + 1)); return r.k > 0 && q ? r.x - q.x : NaN; },
    line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } };
  else if (KNAME === 'msc_tauc') graph = { xlabel: 'photon energy (eV)', ylabel: '(alpha h nu)^2', y0: 0,
    x: function (r) { return 1239.84198 / r.x; }, y: function (r) { return (r.y > 0.005 && r.y < 0.995) ? Math.pow(-Math.log(r.y) / p.t * 1239.84198 / r.x, 2) : NaN; },
    line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } };
  else if (KNAME === 'msc_decay') graph = { xlabel: 'time (ms)', ylabel: 'ln V', x: function (r) { return r.x; }, y: function (r) { return Math.log(r.y); }, y0: -6,
    line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } };
  else if (KNAME === 'msc_glow') graph = { xlabel: '1000 / Tm (1/K)', ylabel: 'ln(Tm^2 / beta)', x: function (r) { return 1000 / r.x; }, y: function (r) { return Math.log(r.x * r.x / r.c); },
    line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } };
  else if (KNAME === 'msc_beer') graph = { xlabel: 'concentration (uM)', ylabel: 'absorbance', x: function (r) { return r.c * 1e6; }, y: function (r) { return r.y; }, y0: 0, x0: 0,
    line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } };

  var colsMap = {
    msc_iodine: [{ label: 'Band', get: function (r) { return r.k; } }, { label: 'λ (nm)', get: function (r) { return r.x.toFixed(2); } }, { label: 'ν (cm⁻¹)', get: function (r) { return (1e7 / r.x).toFixed(1); } }],
    msc_rovib: [{ label: 'Line', get: function (r) { return r.k > 0 ? 'R(' + (r.k - 1) + ')' : 'P(' + (-r.k) + ')'; } }, { label: 'ν (cm⁻¹)', get: function (r) { return r.x.toFixed(2); } }, { label: 'Height', get: function (r) { return r.y.toFixed(3); } }],
    msc_raman: [{ label: 'Line', get: function (r) { return r.k; } }, { label: 'Shift (cm⁻¹)', get: function (r) { return r.x.toFixed(1); } }, { label: 'Height', get: function (r) { return r.y.toFixed(4); } }],
    msc_fluor: [{ label: 'Band', get: function (r) { return r.k === 1 ? 'absorption' : 'emission'; } }, { label: 'λ (nm)', get: function (r) { return r.x.toFixed(1); } }, { label: 'ν (cm⁻¹)', get: function (r) { return (1e7 / r.x).toFixed(0); } }],
    msc_tauc: [{ label: 'λ (nm)', get: function (r) { return r.x.toFixed(1); } }, { label: 'T', get: function (r) { return r.y.toFixed(3); } }, { label: 'hν (eV)', get: function (r) { return (1239.84198 / r.x).toFixed(3); } }],
    msc_varshni: [{ label: 'T (K)', get: function (r) { return r.c; } }, { label: 'λ peak (nm)', get: function (r) { return r.x.toFixed(1); } }, { label: 'E (eV)', get: function (r) { return (1239.84198 / r.x).toFixed(4); } }],
    msc_decay: [{ label: 't (ms)', get: function (r) { return r.x.toFixed(2); } }, { label: 'V (V)', get: function (r) { return r.y.toFixed(3); } }, { label: 'ln V', get: function (r) { return Math.log(r.y).toFixed(3); } }],
    msc_glow: [{ label: 'β (K/s)', get: function (r) { return r.c; } }, { label: 'Tm (K)', get: function (r) { return r.x.toFixed(1); } }, { label: 'ln(Tm²/β)', get: function (r) { return Math.log(r.x * r.x / r.c).toFixed(3); } }],
    msc_beer: [{ label: 'c (µM)', get: function (r) { return (r.c * 1e6).toFixed(0); } }, { label: 'λ (nm)', get: function (r) { return r.x.toFixed(1); } }, { label: 'A', get: function (r) { return r.y.toFixed(3); } }]
  };
  function tracePoints(lo, hi, n) { var o = [], i; for (i = 0; i <= n; i++) o.push(lo + (hi - lo) * i / n); return o; }

  // ================================================================ the auto path (the same functions the buttons call)
  function autoPoints() {
    var ls = lineList(), out = [];
    if (hasLines) {
      if (KNAME === 'msc_iodine') return ls.slice().sort(function (a, b) { return a.k - b.k; }).slice(0, 14).map(function (l) { return l.x; });
      if (KNAME === 'msc_rovib') return ls.filter(function (l) { return (l.k >= 1 && l.k <= 5) || (l.k <= -1 && l.k >= -6); }).map(function (l) { return l.x; });
      if (KNAME === 'msc_raman') return ls.filter(function (l) { return l.k === 1 || l.k === -1; }).map(function (l) { return l.x; });
      return ls.map(function (l) { return l.x; });
    }
    var ax = AX(), i, f;
    if (KNAME === 'msc_decay') { for (i = 1; i <= 8; i++) out.push(ax.hi * i / 12); return out; }
    if (KNAME === 'msc_tauc') {
      var lo = ax.lo, hi = ax.hi;
      var bis = function (lvl) { var a = lo, b = hi, m, j; for (j = 0; j < 60; j++) { m = (a + b) / 2; if ((KN.profile(a, p) - lvl) * (KN.profile(m, p) - lvl) <= 0) b = m; else a = m; } return (a + b) / 2; };
      var x90 = bis(0.9), x05 = bis(0.05), e1 = 1239.84198 / x90, e2 = 1239.84198 / x05;
      for (i = 0; i < 8; i++) { f = e1 + (e2 - e1) * i / 7; out.push(Math.round(1239.84198 / f * 10) / 10); }
      return out;
    }
    return out;
  }
  function recordAt(x) { setCursor(x); return record(); }
  function autoRun() {
    var chain = Promise.resolve();
    chain = chain.then(function () { return powerOn(); }).then(function () { return loadSample(); });
    var combos = [], mi, ci;
    for (mi = 0; mi < Math.max(1, NMODE); mi++) {
      if (CTRL) { var cn = KNAME === 'msc_beer' ? 5 : CTRL.values.length; for (ci = 0; ci < cn; ci++) combos.push([mi, ci]); } else combos.push([mi, 0]);
    }
    combos.forEach(function (cb) {
      chain = chain.then(function () { st.mode = cb[0]; applyCtrl(cb[1]); redraw(); return scan(); }).then(function () {
        autoPoints().forEach(function (x) { recordAt(x); });
      });
    });
    return chain;
  }

  return {
    camera: { pos: [0.0, 0.62, 1.0], look: [-0.02, 0.07, -0.1] },
    views: { mono: [[-0.04, 0.34, 0.5], [-0.04, 0.08, -0.17]], src: [[-0.7, 0.28, 0.3], [-0.7, 0.06, -0.17]], comp: [[-0.42, 0.3, 0.3], [-0.42, 0.07, -0.17]],
      samp: [[-0.34, 0.2, 0.35], [-0.34, 0.03, 0.06]], det: [[0.26, 0.26, 0.28], [0.26, 0.06, -0.17]], screen: [[0.52, 0.3, 0.2], [0.55, 0.1, -0.2]],
      acc: [[0.12, 0.3, 0.42], [0.12, 0.05, 0.1]], bench: [[0.0, 0.62, 1.0], [-0.02, 0.07, -0.1]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: ({
      msc_iodine: 'G(v) = ωe(v + ½) − ωexe(v + ½)²,   Δν(v) = ωe − 2ωexe (v + 1)',
      msc_rovib: 'R(J−1) − P(J+1) = 4B₀(J + ½),   r = √(h / 8π²cμB),   k = 4π²c²ν²μ',
      msc_raman: 'I(anti-Stokes) / I(Stokes) = ((ν₀+s)/(ν₀−s))⁴ exp(−hcs/kT)',
      msc_fluor: 'Stokes shift = 1/λ(abs) − 1/λ(em)',
      msc_tauc: '(αhν)² = B(hν − Eg),   α = −ln T / t',
      msc_varshni: 'Eg(T) = Eg(0) − αT² / (T + β)',
      msc_decay: 'V = V₀ exp(−t/τ),   ln V = ln V₀ − t/τ',
      msc_glow: 'ln(Tm²/β) = E/(kTm) + constant',
      msc_beer: 'A = ε c l' })[KNAME], formulaNote: 'SI-derived units as printed in the instrument; constants from CODATA 2018',
      more: [I.hint], precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 70) + '...', 'Sample: ' + SAMPLE, 'Source: ' + I.src, 'Detector: ' + I.det, I.hint.slice(0, 70)],
      columns: colsMap[KNAME] || colsMap.msc_fluor },
    graph: graph,
    result: result,
    tol: 0.02,
    resultNote: 'Every value came from the cursor reading of a line or a point on the scan. A real instrument adds noise and a slit width; here the lines are noise-free so the answer shows the method, not the luck.',
    chips: ['What does this scan show?', 'How do I read the cursor?', 'Why is this line broad?', 'Check my readings', 'What is the sample?'],
    viva: [],
    askState: function () {
      return { experiment: S.lab.title, sample: SAMPLE, instrument_on: st.on, sample_loaded: st.loaded, scanned: !!st.scanned[key()], mode: NMODE ? KN.MODES[st.mode] : undefined,
        control: CTRL ? ctrlShow() : undefined, cursor: fmtX(st.cursor) + ' ' + AX().unit, readings_taken: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Switch on and load the sample');
          u.p(I.src + ' and the ' + I.det.toLowerCase() + ' need to be on before a scan. The sample is ' + SAMPLE.toLowerCase() + '.');
          u.task('1. Switch the instrument on', st.on, st.on ? 'Lamp and detector are on' : 'Press POWER')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { S.focus('mono'); powerOn(); }, !st.on, st.on || S.hand.busy));
          u.task('2. Load the sample', st.loaded, st.loaded ? 'In the holder' : 'On the bench')
            .add(u.button(st.loaded ? 'Loaded' : 'Load the sample', function () { S.focus('samp'); loadSample(); }, !st.loaded, st.loaded || !st.on || S.hand.busy));
          u.note(S.lab.safety || 'Handle the sample by its edges.');
          u.next('Next: scan and read', st.on && st.loaded);
        },
        ok: function () { return st.on && st.loaded; },
        auto: function () { return powerOn().then(function () { return loadSample(); }); } },
      { id: 'scan', title: 'Scan and read', view: 'screen', render: function (u) {
          var ax = AX();
          u.h2('Scan, then put the cursor on the lines');
          u.p(I.hint);
          if (NMODE) u.row.apply(u, KN.MODES.map(function (m, i) { return u.button(m, function () { setMode(i); }, st.mode === i, S.hand.busy); }));
          if (CTRL) u.row.apply(u, CTRL.values.map(function (v, i) { return u.button(rnd(v * CTRL.scale, CTRL.digits) + ' ' + CTRL.unit, function () { setCtrl(i); }, st.ci === i, S.hand.busy); }));
          u.row(u.button(st.scanned[key()] ? 'Scan again' : 'Run the scan', function () { S.focus('mono'); scan(); }, !st.scanned[key()], S.hand.busy));
          if (hasLines) u.row(u.button('◀ Previous line', function () { stepLine(-1); }, false, !st.scanned[key()]), u.button('Next line ▶', function () { stepLine(1); }, false, !st.scanned[key()]));
          var tg = { v: st.cursor };
          u.slider('Cursor (' + ax.unit + ')', ax.lo, ax.hi, (ax.hi - ax.lo) / 4000, function () { return st.cursor; }, function (v) { tg.v = v; setCursor(v); }, ax.unit, I.xd);
          u.row(u.button('Record this reading', function () { record(); }, true, S.hand.busy));
          u.live(function () { return fmtX(st.cursor) + ' ' + ax.unit + (st.scanned[key()] ? '  ·  signal ' + sigAt(st.cursor).toPrecision(3) : ''); });
          u.h3('Observation table'); u.table();
          u.p(S.rows.length + ' readings recorded' + (hasLines ? '' : '; about ' + I.need + ' needed') + '.');
          u.next('Next: the result', enough());
        },
        ok: function () { return enough(); },
        auto: function () { return autoRun(); } },
    ],
    tick: function () {
      hudA.set(fmtX(st.cursor) + ' ' + AX().unit);
      hudB.set(st.loaded && st.scanned[key()] ? sigAt(st.cursor).toPrecision(3) : '—');
      hudC.set(CTRL ? ctrlShow() : (st.scanned[key()] ? String(lineList().length) : '—'));
    }
  };
});
