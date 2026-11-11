/* Prayogshala studio module: M.Sc. X-RAY POWDER DIFFRACTOMETER (Bragg-Brentano, Cu K-alpha).
   A sealed X-ray tube, a powder on the goniometer and a detector arm that turns through 2-theta. The pattern is the
   `msc_xrd` kernel (packs/msc_solid.js): Bragg's law positions, the structure-factor selection rules of the lattice
   (BCC, FCC, diamond, rock salt), and Gaussian lines whose width follows Scherrer size broadening plus micro-strain
   and the instrument's own width. The student scans, finds the lines, indexes them and gets the lattice parameter
   (xrd-powder-photograph), or corrects the widths and draws a Williamson-Hall plot for the crystallite size
   (xrd-size-strain). Line heights are a model; positions and widths are the physics. */
HoolaStudio.define('msc-xrd-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.msc_xrd;
  var p = HK.paramsFor('msc_xrd', S.lab.params);
  var V_ = S.lab.variant || {};
  var SIZE = String(S.lab.id).indexOf('xrd-size-strain') === 0;
  var LATT = { 2: 'body-centred cubic (BCC)', 3: 'face-centred cubic (FCC)', 4: 'diamond cubic', 5: 'rock-salt (FCC lattice, two atoms)' };
  var SAMPLE = V_.sample || (SIZE ? 'Nanocrystalline copper powder' : 'Aluminium powder');
  var st = { mounted: false, open: false, tth: 20, scanned: false, scanning: false, lines: null, chosen: 0, done: false };
  var PEAKS = null, XS = [], YS = [], PROG = 0;
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  var D2R = Math.PI / 180;

  // ================================================================ the goniometer
  var CX = -0.3, CZ = -0.16, RA = 0.115;
  var gon = new T.Group(); S.scene.add(gon);
  mk(gon, cyl(0.15, 0.155, 0.02, 48), new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.35, metalness: 0.85 }), CX, 0.01, CZ);
  mk(gon, new T.TorusGeometry(RA, 0.002, 6, 96), M.chrome, CX, 0.0215, CZ).rotation.x = Math.PI / 2;
  for (var tk = 0; tk <= 12; tk++) { var ta = (tk * 10 - 0) * D2R; var mm = mk(gon, box(0.0015, 0.001, 0.008), M.black, CX + (RA + 0.014) * Math.cos(ta), 0.0215, CZ - (RA + 0.014) * Math.sin(ta)); mm.rotation.y = ta; }
  var sampleStage = new T.Group(); sampleStage.position.set(CX, 0.02, CZ); gon.add(sampleStage);
  mk(sampleStage, cyl(0.02, 0.022, 0.012, 28), M.iron, 0, 0.006, 0);
  var holder = mk(sampleStage, box(0.034, 0.003, 0.034), M.alu, 0, 0.0135, 0);
  var well = mk(sampleStage, box(0.024, 0.0012, 0.024), new T.MeshStandardMaterial({ color: 0x1f2124, roughness: 0.2 }), 0, 0.0155, 0);
  var powderM = new T.MeshStandardMaterial({ color: 0xb7bcc2, roughness: 0.7, metalness: 0.4 });
  var powder = mk(sampleStage, box(0.024, 0.0016, 0.024), powderM, 0, 0.0158, 0); powder.visible = false;
  var tube = new T.Group(); tube.position.set(CX - RA - 0.06, 0.045, CZ); gon.add(tube);
  mk(tube, box(0.12, 0.07, 0.09), new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.4, metalness: 0.5 }), 0, 0, 0);
  mk(tube, box(0.02, 0.05, 0.05), new T.MeshStandardMaterial({ color: 0xd8b42a, roughness: 0.4 }), 0.062, 0, 0);
  var tlb = S.label('X-RAY TUBE · Cu Kα', { w: 0.1, ratio: 0.14, color: '#20252b', bg: '#d8b42a' }); tlb.position.set(0, 0.0, 0.0455); tube.add(tlb);
  var wlb = S.label('RADIATION', { w: 0.05, ratio: 0.2, color: '#fff', bg: '#a8201a' }); wlb.position.set(0, 0.026, 0.0455); tube.add(wlb);
  var beam = mk(gon, cyl(0.0012, 0.0012, RA + 0.03, 8), new T.MeshBasicMaterial({ color: 0x8f6bff, transparent: true, opacity: 0.0 }), CX - (RA + 0.03) / 2 + 0.0, 0.0345, CZ); beam.rotation.z = Math.PI / 2;
  var arm = new T.Group(); arm.position.set(CX, 0.0345, CZ); gon.add(arm);
  var armBar = mk(arm, box(RA + 0.03, 0.006, 0.012), M.alu, (RA + 0.03) / 2 - 0.02, 0, 0);
  var det = mk(arm, box(0.03, 0.036, 0.03), new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.4, metalness: 0.5 }), RA + 0.02, 0, 0);
  var dlb = S.label('DETECTOR', { w: 0.028, ratio: 0.2, color: '#e8eaec', bg: '#2f3338' }); dlb.rotation.y = -Math.PI / 2; dlb.position.set(RA + 0.0355, 0, 0); arm.add(dlb);
  var scat = mk(arm, cyl(0.0012, 0.0012, RA, 8), new T.MeshBasicMaterial({ color: 0x8f6bff, transparent: true, opacity: 0.0 }), RA / 2, 0, 0); scat.rotation.z = Math.PI / 2;
  S.contact(0.34, 0.34, CX, CZ, 0.5);
  var tray = mk(S.scene, cyl(0.03, 0.03, 0.004, 28), M.alu, -0.06, 0.002, 0.17); S.contact(0.08, 0.08, -0.06, 0.17, 0.5);
  var cap = new T.Group(); S.scene.add(cap); cap.position.set(-0.06, 0.012, 0.17);                    // the powder in its little holder, waiting
  var pk = mk(cap, box(0.034, 0.003, 0.034), M.alu, 0, 0, 0); mk(cap, box(0.024, 0.0016, 0.024), powderM, 0, 0.0015, 0);

  // ================================================================ generator box and display
  function instBox(x, z, rotY, title, sub, wdt) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = wdt || 0.2, Dd = 0.15, Hh = 0.08;
    var cse = S.rounded(W, Dd, Hh, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); cse.rotation.x = -Math.PI / 2; cse.position.y = Hh / 2 + 0.003; g.add(cse);
    var FZ = Dd / 2 + 0.005, PW = W - 0.012, PH = Hh - 0.012;
    var tex = S.canvasTex(900, Math.round(900 * PH / PW), function (xx, w, h) { xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h); xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
      xx.fillStyle = '#f1efe8'; xx.font = '700 34px "Public Sans", sans-serif'; xx.fillText(title, 26, 52); xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText(sub, 26, 88); });
    var fac = S.mesh(box(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]); fac.position.set(0, 0.003 + Hh / 2, FZ - 0.002); g.add(fac);
    var lcdT = S.liveTex(512, 180), last = '';
    var bez = S.mesh(box(PW * 0.52, PH * 0.42, 0.003), M.grey); bez.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.001); g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(PW * 0.48, PH * 0.38), new T.MeshBasicMaterial({ map: lcdT, toneMapped: false })); scr.position.set(PW * 0.2, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(scr);
    var knobG = new T.Group(); knobG.position.set(-PW * 0.28, 0.003 + Hh / 2 - PH * 0.16, FZ + 0.004); g.add(knobG);
    var kk = S.mesh(cyl(0.012, 0.013, 0.012, 28), M.bakelite); kk.rotation.x = Math.PI / 2; knobG.add(kk);
    var kp = S.mesh(box(0.0018, 0.012, 0.001), M.white, false); kp.position.set(0, 0.007, 0.007); knobG.add(kp);
    S.contact(W + 0.06, Dd + 0.06, x, z, 0.5);
    return { group: g, knob: knobG, show: function (txt, u2) { if (txt + u2 === last) return; last = txt + u2;
      lcdT.draw(function (xx) { var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
        xx.font = '700 ' + (txt.length > 7 ? 64 : 88) + 'px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118); xx.font = '600 32px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150); }); } };
  }
  var genB = instBox(0.0, 0.1, -0.1, 'X-RAY GENERATOR', '40 kV · 20 mA · shutter', 0.22);
  var ang = instBox(0.0, -0.1, 0.05, 'GONIOMETER', 'detector angle 2θ and counts', 0.22);
  genB.show('OFF', ''); ang.show('20.00', '2θ °');
  var monG = new T.Group(); S.scene.add(monG); monG.position.set(0.34, 0, -0.1); monG.rotation.y = -0.3;
  var mb = S.rounded(0.3, 0.2, 0.03, 0.008, new T.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4 })); mb.rotation.x = 0; mb.position.set(0, 0.115, 0); monG.add(mb);
  mk(monG, cyl(0.012, 0.016, 0.07, 14), M.alu, 0, 0.035, -0.01); mk(monG, box(0.12, 0.008, 0.08), M.alu, 0, 0.004, 0);
  var plotTex = S.liveTex(768, 480), plot = new T.Mesh(new T.PlaneGeometry(0.28, 0.175), new T.MeshBasicMaterial({ map: plotTex, toneMapped: false })); plot.position.set(0, 0.115, 0.017); monG.add(plot);
  S.contact(0.34, 0.2, 0.34, -0.1, 0.5);
  var plotKey = '';
  function drawPlot() {
    var key = PROG + '|' + st.scanned + '|' + (st.lines ? st.lines.length : 0); if (key === plotKey) return; plotKey = key;
    plotTex.draw(function (x, w, h) {
      x.fillStyle = '#10161d'; x.fillRect(0, 0, w, h);
      var L = 70, R = 18, Tp = 30, B = 52, X = function (t) { return L + (t - 20) / 100 * (w - L - R); };
      var ymax = 1; if (YS.length) for (var i = 0; i < YS.length; i += 4) if (YS[i] > ymax) ymax = YS[i];
      ymax *= 1.08; var Y = function (v) { return h - B - v / ymax * (h - B - Tp); };
      x.strokeStyle = 'rgba(255,255,255,.14)'; x.fillStyle = '#9aa7b6'; x.font = '600 18px "JetBrains Mono", monospace'; x.lineWidth = 1;
      for (var a = 20; a <= 120; a += 20) { x.beginPath(); x.moveTo(X(a), Tp); x.lineTo(X(a), h - B); x.stroke(); x.fillText(a + '°', X(a) - 14, h - B + 22); }
      for (var c = 0; c <= 4; c++) { var yv = ymax * c / 4; x.beginPath(); x.moveTo(L, Y(yv)); x.lineTo(w - R, Y(yv)); x.stroke(); x.fillText(Math.round(yv), 6, Y(yv) + 5); }
      x.fillStyle = '#e8eaec'; x.font = '600 20px "Public Sans", sans-serif'; x.fillText('2θ (degrees)', w / 2 - 50, h - 12); x.fillText('counts', 8, 22);
      if (YS.length) { x.strokeStyle = '#5ee0a0'; x.lineWidth = 2; x.beginPath(); var n = Math.min(XS.length, Math.floor(PROG * XS.length)), first = true;
        for (var j = 0; j < n; j += 2) { if (first) { x.moveTo(X(XS[j]), Y(YS[j])); first = false; } else x.lineTo(X(XS[j]), Y(YS[j])); } x.stroke(); }
      if (st.lines) { x.fillStyle = '#ffd24a'; x.font = '600 16px "JetBrains Mono", monospace'; st.lines.forEach(function (q, k) { x.beginPath(); x.moveTo(X(q.tth), Y(q.height) - 4); x.lineTo(X(q.tth) - 5, Y(q.height) - 14); x.lineTo(X(q.tth) + 5, Y(q.height) - 14); x.fill(); x.fillText(q.tth.toFixed(1), X(q.tth) - 16, Y(q.height) - 18); }); }
    });
  }

  S.addApparatus('gonio', gon, 'Powder diffractometer', 'A Bragg-Brentano goniometer: the sample at the centre, the tube on one side and the detector on an arm that turns through 2θ.');
  S.addApparatus('sample', cap, SAMPLE, 'A fine powder pressed flat in a holder. Many tiny crystals point every way, so some are always at the Bragg angle.');
  S.addApparatus('gen', genB.group, 'X-ray generator', 'Supplies the tube. The shutter is opened only from outside the interlocked cabinet.');
  S.addApparatus('ang', ang.group, 'Goniometer control', 'Shows the detector angle 2θ and drives the scan.');
  S.addApparatus('mon', monG, 'Scan display', 'The counts the detector records, against 2θ.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every line you find is written here, as in a real practical file.');
  var hudA = S.hudCard('Detector angle 2θ'), hudI = S.hudCard('Counts');
  drawPlot();

  // ================================================================ human actions
  function mountSample() {
    if (busy() || st.mounted) return Promise.resolve();
    var a = cap.position.clone(), b = new T.Vector3(CX, 0.0345, CZ);
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.01, 0)), function (k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.08 * Math.sin(Math.PI * k) + (b.y - a.y) * k + 0.01, a.z + (b.z - a.z) * k); },
      function (k) { cap.position.set(a.x + (b.x - a.x) * k, a.y + 0.08 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); }, { mode: 'top', ms: 1300, reachMs: 650 })
      .then(function () { cap.visible = false; powder.visible = true; st.mounted = true; S.say('The powder holder is on the sample stage, its surface level with the goniometer axis.'); S.render(); });
  }
  function openShutter() {
    if (busy() || st.open) return Promise.resolve();
    if (!st.mounted) { S.say('Load the sample first.'); return Promise.resolve(); }
    return S.hand.tap(genB.knob, 'front').then(function () { st.open = true; S.say('Cabinet door closed and interlock made. Shutter open: 40 kV, 20 mA.'); S.click(880, 0.05); S.render(); });
  }
  function runScan() {
    if (busy() || st.scanning) return Promise.resolve();
    if (!st.open) { S.say('Open the shutter first.'); return Promise.resolve(); }
    if (st.scanned) { S.say('The scan is already recorded.'); return Promise.resolve(); }
    st.scanning = true; PEAKS = KN.peaks(p); XS = []; YS = [];
    for (var i = 0; i <= 5000; i++) { var xx = 20 + 0.02 * i; XS.push(xx); YS.push(KN.counts(xx, p, PEAKS)); }
    S.say('Scanning 2θ from 20° to 120° in steps of 0.02°.');
    return S.tween(5200, function (k) { PROG = k; st.tth = 20 + 100 * k; }).then(function () { PROG = 1; st.tth = 120; st.scanned = true; st.scanning = false; S.say('The scan is complete. The peaks are the Bragg reflections.'); S.render(); });
  }
  function findLines() {
    if (st.lines) { S.say('The lines are already found.'); return false; }
    if (!st.scanned) { S.say('Run the scan first.'); return false; }
    var pks = KN.scanPeaks(p); if (pks.length < 3) { S.say('Fewer than three lines: the pattern cannot be indexed.'); return false; }
    st.lines = pks;
    var bi = p.binst * D2R;
    pks.forEach(function (q, i) {
      var th = q.tth * D2R / 2, s2 = Math.pow(Math.sin(th), 2), row = { tth: q.tth, th: th, fwhm: q.fwhm, s2: s2, ratio: s2 / Math.pow(Math.sin(pks[0].tth * D2R / 2), 2), N: 0, a: 0, d: p.lam / (2 * Math.sin(th)) };
      if (SIZE) { var bo = q.fwhm * D2R; if (bo > bi) { var bs = Math.sqrt(bo * bo - bi * bi); row.x = 4 * Math.sin(th); row.y = bs * Math.cos(th); row.bs = bs / D2R; } }
      S.addRow(row);
    });
    S.say(pks.length + ' lines found. ' + (SIZE ? 'Each has a full width at half maximum.' : 'The ratios of sin²θ to the first line are in the table.'));
    return true;
  }
  function assignN(lt) {
    var sq = KN.seq(lt), r = S.rows, i, k, tg, bd, nn, bad = 0;
    for (i = 0; i < r.length; i++) { tg = r[i].s2 / r[0].s2 * sq[0]; nn = sq[0]; bd = Math.abs(sq[0] - tg); for (k = 1; k < sq.length; k++) if (Math.abs(sq[k] - tg) < bd) { bd = Math.abs(sq[k] - tg); nn = sq[k]; } r[i].N = nn; bad += Math.abs(nn - tg) / Math.max(nn, 1); }
    var seen = {}, dup = 0; r.forEach(function (q) { if (seen[q.N]) dup++; seen[q.N] = 1; });
    return { bad: bad, dup: dup };
  }
  function chooseLattice(lt) {
    if (busy()) return Promise.resolve();
    if (!st.lines) { S.say('Find the lines first.'); return Promise.resolve(); }
    st.chosen = lt; var q = assignN(lt);
    S.rows.forEach(function (r) { r.a = p.lam * Math.sqrt(r.N) / (2 * Math.sqrt(r.s2)); });
    S.book.draw();
    S.say(q.dup ? 'With ' + LATT[lt] + ' two lines get the same N: this lattice does not fit.' : 'With ' + LATT[lt] + ' the lines get N = ' + S.rows.map(function (r) { return r.N; }).join(', ') + '.');
    S.render(); return Promise.resolve();
  }
  function doWH() { if (!st.lines) { S.say('Find the lines first.'); return false; } st.done = true; S.say('The instrument width is subtracted in quadrature and β cosθ is plotted against 4 sinθ.'); S.render(); return true; }

  function result(rows) {
    if (SIZE) {
      var pts = rows.filter(function (r) { return r.x !== undefined; }).map(function (r) { return [r.x, r.y]; });
      if (!st.done || pts.length < 4) return null; var f = S.fit.linear(pts); if (!f || f.m === undefined || f.c <= 0) return null;
      return { label: 'Crystallite size', value: p.K * p.lam / f.c * 1e9, unit: 'nm', digits: 1, truth: p.Lx * 1e9,
        note: 'Williamson-Hall fit of ' + pts.length + ' lines: intercept K λ / L = ' + (f.c * 1e3).toFixed(3) + ' × 10⁻³ rad, so L = 0.9 × 0.15406 nm ÷ intercept. The slope ' + f.m.toExponential(2) + ' is the micro-strain (4ε = slope).' };
    }
    if (!st.chosen || rows.length < 3 || !rows[0].N) return null;
    var last = rows[rows.length - 1], q = assignN(st.chosen); if (q.dup) return null;
    return { label: 'Lattice parameter a', value: p.lam * Math.sqrt(last.N) / (2 * Math.sqrt(last.s2)) * 1e10, unit: 'Å', digits: 4, truth: p.a * 1e10,
      note: 'The lattice is ' + LATT[st.chosen] + '. From the line at 2θ = ' + last.tth.toFixed(2) + '° (N = ' + last.N + '): a = λ √N / (2 sinθ). The highest-angle line gives the most accurate value.' };
  }

  var cols = SIZE
    ? [{ label: '2θ (°)', get: function (r) { return r.tth.toFixed(2); } }, { label: 'FWHM (°)', get: function (r) { return r.fwhm.toFixed(3); } }, { label: 'β sample (°)', get: function (r) { return r.bs === undefined ? '—' : r.bs.toFixed(3); } },
      { label: '4 sinθ', get: function (r) { return r.x === undefined ? '—' : r.x.toFixed(4); } }, { label: 'β cosθ (10⁻³)', get: function (r) { return r.y === undefined ? '—' : (r.y * 1e3).toFixed(3); } }]
    : [{ label: '2θ (°)', get: function (r) { return r.tth.toFixed(2); } }, { label: 'sin²θ', get: function (r) { return r.s2.toFixed(4); } }, { label: 'ratio', get: function (r) { return r.ratio.toFixed(3); } },
      { label: 'N = h²+k²+l²', get: function (r) { return r.N || '—'; } }, { label: 'a (Å)', get: function (r) { return r.a ? (r.a * 1e10).toFixed(4) : '—'; } }];

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { gonio: [[-0.3, 0.3, 0.2], [-0.3, 0.03, -0.16]], sample: [[-0.1, 0.2, 0.33], [-0.06, 0.02, 0.17]], gen: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]], ang: [[0.0, 0.22, 0.08], [0.0, 0.05, -0.1]],
      mon: [[0.38, 0.24, 0.18], [0.34, 0.11, -0.1]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: SIZE ? 'β cosθ = K λ / L + 4 ε sinθ' : '2 d sinθ = λ,   d = a / √(h²+k²+l²)',
      formulaNote: SIZE ? 'β is the sample width in radians after the instrument width is removed in quadrature' : 'only the reflections the structure factor allows appear',
      more: SIZE ? ['K = 0.9 for roughly spherical crystallites. The intercept of the plot gives the size, the slope the micro-strain.', 'A line is broadened by the instrument too; the instrument width is measured on a coarse-grained standard and subtracted in quadrature.', 'Electron microscopy sees the grains directly; X-ray line broadening averages over the whole sample. This bench simulates the X-ray measurement only.']
        : ['Body-centred lattices show only h+k+l even; face-centred only unmixed h, k, l; the diamond structure also loses h+k+l = 4n+2.', 'The ratios of sin²θ to the first line are the ratios of N, so they name the lattice.', 'Relative heights of the lines in this simulation come from a simple model; positions are exact Bragg angles.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Sample: ' + SAMPLE, 'Cu Kα, λ = 0.15406 nm; instrument width ' + p.binst.toFixed(2) + '°.'], columns: cols },
    graph: SIZE ? { x: function (r) { return r.x === undefined ? NaN : r.x; }, y: function (r) { return r.y === undefined ? NaN : r.y * 1e3; }, xlabel: '4 sinθ', ylabel: 'β cosθ (10⁻³ rad)',
      line: function (pts) { var f = S.fit.linear(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return f ? function (x) { return f.m * x + f.c; } : null; } }
      : { x: function (r) { return r.N || NaN; }, y: function (r) { return r.s2; }, xlabel: 'N = h²+k²+l²', ylabel: 'sin²θ',
        line: function (pts) { var k = S.fit.origin(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return isFinite(k) ? function (x) { return k * x; } : null; } },
    result: result,
    tol: SIZE ? 0.05 : 0.005,
    resultNote: SIZE ? 'The size is the intercept of the Williamson-Hall line, with the lab\'s true value alongside for comparison.' : 'The lattice parameter is the textbook value for this material within the accuracy of the angle measurement.',
    chips: ['Why are some lines missing?', 'How do I tell BCC from FCC?', 'Check my readings', 'Why use the highest-angle line?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, sample: SAMPLE, mounted: st.mounted, shutter_open: st.open, scanned: st.scanned, lines_found: st.lines ? st.lines.length : 0, lattice_chosen: st.chosen ? LATT[st.chosen] : 'none yet' }; },
    steps: [
      { id: 'setup', title: 'Load and expose', view: 'gonio', render: function (u) {
          u.h2('Load the powder, open the shutter');
          u.p('The powder is pressed flat in its holder on the tray. Put it on the sample stage, close the cabinet door and open the shutter from the generator.');
          u.task('1. Load the sample', st.mounted, st.mounted ? 'On the stage' : 'On the tray').add(u.button(st.mounted ? 'Loaded' : 'Load the sample', function () { S.focus('gonio'); mountSample(); }, !st.mounted, st.mounted || S.hand.busy));
          u.task('2. Open the shutter', st.open, st.open ? 'X-rays on' : 'Shutter closed').add(u.button(st.open ? 'Shutter open' : 'Open the shutter', function () { S.focus('gen'); openShutter(); }, !st.open && st.mounted, st.open || !st.mounted || S.hand.busy));
          u.note('The tube is interlocked: the shutter cannot open with the cabinet door open. Wear your radiation badge.');
          u.next('Next: scan', st.mounted && st.open);
        },
        ok: function () { return st.mounted && st.open; }, auto: function () { return mountSample().then(openShutter); } },
      { id: 'scan', title: 'Scan 2θ', view: 'mon', render: function (u) {
          u.h2('Scan the detector through 2θ');
          u.p('The detector turns from 20° to 120° while the sample turns half as fast. The counts are drawn as they arrive.');
          u.task('Run the scan', st.scanned, st.scanned ? 'Scan recorded' : st.scanning ? 'Scanning…' : 'Ready').add(u.button(st.scanned ? 'Recorded' : 'Start the scan', function () { S.focus('mon'); runScan(); }, !st.scanned, st.scanned || st.scanning || S.hand.busy));
          u.live(function () { return 'Detector at ' + st.tth.toFixed(2) + '°'; });
          u.next('Next: find the lines', st.scanned);
        },
        ok: function () { return st.scanned; }, auto: function () { return runScan(); } },
      { id: 'lines', title: SIZE ? 'Widths and the plot' : 'Index the lines', view: 'mon', render: function (u) {
          u.h2(SIZE ? 'Find the line widths' : 'Find the lines and index them');
          if (SIZE) {
            u.p('Mark the lines and read the full width at half maximum of each. Then take the instrument width (' + p.binst.toFixed(2) + '°) out in quadrature and plot β cosθ against 4 sinθ.');
            u.task('1. Find the lines and widths', !!st.lines, st.lines ? st.lines.length + ' lines' : 'Not done').add(u.button(st.lines ? 'Found' : 'Find the lines', function () { S.focus('mon'); findLines(); }, !st.lines, !!st.lines || S.hand.busy));
            u.task('2. Williamson-Hall plot', st.done, st.done ? 'Plotted' : 'Not done').add(u.button(st.done ? 'Plotted' : 'Correct and plot', function () { doWH(); }, !st.done && !!st.lines, st.done || !st.lines || S.hand.busy));
          } else {
            u.p('Mark the lines, then compare the ratios of sin²θ to the first line with the allowed sequences of BCC (2:4:6:8…), FCC (3:4:8:11:12…) and diamond (3:8:11:16…) lattices.');
            u.task('1. Find the lines', !!st.lines, st.lines ? st.lines.length + ' lines' : 'Not done').add(u.button(st.lines ? 'Found' : 'Find the lines', function () { S.focus('mon'); findLines(); }, !st.lines, !!st.lines || S.hand.busy));
            u.task('2. Choose the lattice', !!st.chosen, st.chosen ? LATT[st.chosen] : 'Which sequence fits?');
            u.row(u.button('BCC', function () { chooseLattice(2); }, st.chosen === 2, !st.lines || S.hand.busy), u.button('FCC', function () { chooseLattice(3); }, st.chosen === 3, !st.lines || S.hand.busy), u.button('Diamond', function () { chooseLattice(4); }, st.chosen === 4, !st.lines || S.hand.busy));
          }
          u.h3('Lines'); u.table();
          u.next('Next: the result', SIZE ? st.done : !!st.chosen);
        },
        ok: function () { return SIZE ? st.done : (!!st.chosen && !!S.rows.length && !!S.rows[0].N); },
        auto: function () { findLines(); if (SIZE) { doWH(); return Promise.resolve(); } var lt = KN.index(st.lines, p.lam).ltype; return chooseLattice(lt || 3); } }
    ],
    tick: function () {
      genB.show(st.open ? '40·20' : 'OFF', st.open ? 'kV·mA' : ''); ang.show(st.tth.toFixed(2), '2θ °');
      arm.rotation.y = st.tth * D2R; sampleStage.rotation.y = st.tth * D2R / 2;
      beam.material.opacity = st.open ? 0.5 : 0;
      scat.material.opacity = st.open ? 0.5 : 0;
      var counts = YS.length && st.scanned || (st.scanning) ? KN.counts(st.tth, p, PEAKS || KN.peaks(p)) : 0;
      hudA.set(st.tth.toFixed(2) + '°'); hudI.set(st.open ? Math.round(counts) + '' : '—');
      drawPlot();
    },
  };
});
