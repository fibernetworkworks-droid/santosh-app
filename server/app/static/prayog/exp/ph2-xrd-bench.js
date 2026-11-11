/* Prayogshala studio module: X-RAY DIFFRACTOMETER BENCH for two labs (SIMULATED facility instrument).
   ph2-xrd-refine (+ variants): a cubic powder pattern (Bragg-Brentano, Cu K-alpha1). The student scans 2-theta, the program
   finds every line (position, width, area), the student picks the structure model(s) from the data card, the lines are
   indexed with the allowed reflections, the lattice parameter is refined by least squares on sin^2(theta) and, for a
   two-phase mixture, the scale factor of each phase gives the weight fractions (Hill-Howard). Atomic positions stay
   FIXED: this is a Rietveld-style scale-factor and lattice refinement, not a full Rietveld refinement.
   ph2-xrr-film (+ variants): the specular reflectivity of a film or multilayer on silicon (exact Parratt recursion).
   The student scans 2-theta, marks the fringe maxima, numbers them and fits sin^2(theta) against order^2.
   Physics: kernels ph2_xrd and ph2_xrr in packs/ph2_films.js. */
HoolaStudio.define('ph2-xrd-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var XRR = String(S.lab.id).indexOf('ph2-xrr') === 0;
  var KN = XRR ? HK.K.ph2_xrr : HK.K.ph2_xrd;
  var p = HK.paramsFor(XRR ? 'ph2_xrr' : 'ph2_xrd', S.lab.params);
  var V_ = S.lab.variant || {};
  var MIX = !XRR && Math.round(p.t2) > 0, ML = XRR && Math.round(p.kind) === 2;
  var SAMPLE = V_.sample || (XRR ? 'Gold film, 40 nm, on a silicon wafer' : 'Silicon powder (standard)');
  var STRUCT = { 1: 'Diamond cubic (silicon)', 2: 'Perovskite ABO3 (Pm-3m)', 3: 'Spinel (Fd-3m)' };
  var st = { mounted: false, open: false, tth: p.tmin, scanned: false, scanning: false, lines: null, fr: null, c1: 0, c2: 0, fit: null };
  var XS = [], YS = [], PROG = 0, PK = null;
  var D2R = Math.PI / 180;
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }

  // ================================================================ the goniometer
  var CX = -0.3, CZ = -0.16, RA = 0.115;
  var gon = new T.Group(); S.scene.add(gon);
  mk(gon, cyl(0.15, 0.155, 0.02, 48), new T.MeshStandardMaterial({ color: 0xaeb4ba, roughness: 0.35, metalness: 0.85 }), CX, 0.01, CZ);
  mk(gon, new T.TorusGeometry(RA, 0.002, 6, 96), M.chrome, CX, 0.0215, CZ).rotation.x = Math.PI / 2;
  for (var tk = 0; tk <= 12; tk++) { var ta = tk * 10 * D2R; var mm = mk(gon, box(0.0015, 0.001, 0.008), M.black, CX + (RA + 0.014) * Math.cos(ta), 0.0215, CZ - (RA + 0.014) * Math.sin(ta)); mm.rotation.y = ta; }
  var sampleStage = new T.Group(); sampleStage.position.set(CX, 0.02, CZ); gon.add(sampleStage);
  mk(sampleStage, cyl(0.02, 0.022, 0.012, 28), M.iron, 0, 0.006, 0);
  mk(sampleStage, box(0.034, 0.003, 0.034), M.alu, 0, 0.0135, 0);
  mk(sampleStage, box(0.024, 0.0012, 0.024), new T.MeshStandardMaterial({ color: 0x1f2124, roughness: 0.2 }), 0, 0.0155, 0);
  var sampM = new T.MeshStandardMaterial({ color: XRR ? 0x6c7480 : 0xb7bcc2, roughness: XRR ? 0.12 : 0.7, metalness: XRR ? 0.95 : 0.4 });
  var sampleOn = mk(sampleStage, box(0.024, XRR ? 0.0012 : 0.0016, 0.024), sampM, 0, 0.0158, 0); sampleOn.visible = false;
  var tube = new T.Group(); tube.position.set(CX - RA - 0.06, 0.045, CZ); gon.add(tube);
  mk(tube, box(0.12, 0.07, 0.09), new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.4, metalness: 0.5 }), 0, 0, 0);
  mk(tube, box(0.02, 0.05, 0.05), new T.MeshStandardMaterial({ color: 0xd8b42a, roughness: 0.4 }), 0.062, 0, 0);
  var tlb = S.label('X-RAY TUBE · Cu Kα1', { w: 0.1, ratio: 0.14, color: '#20252b', bg: '#d8b42a' }); tlb.position.set(0, 0.0, 0.0455); tube.add(tlb);
  var wlb = S.label('RADIATION', { w: 0.05, ratio: 0.2, color: '#fff', bg: '#a8201a' }); wlb.position.set(0, 0.026, 0.0455); tube.add(wlb);
  var beam = mk(gon, cyl(0.0012, 0.0012, RA + 0.03, 8), new T.MeshBasicMaterial({ color: 0x8f6bff, transparent: true, opacity: 0.0 }), CX - (RA + 0.03) / 2, 0.0345, CZ); beam.rotation.z = Math.PI / 2;
  var arm = new T.Group(); arm.position.set(CX, 0.0345, CZ); gon.add(arm);
  mk(arm, box(RA + 0.03, 0.006, 0.012), M.alu, (RA + 0.03) / 2 - 0.02, 0, 0);
  mk(arm, box(0.03, 0.036, 0.03), new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.4, metalness: 0.5 }), RA + 0.02, 0, 0);
  var dlb = S.label('DETECTOR', { w: 0.028, ratio: 0.2, color: '#e8eaec', bg: '#2f3338' }); dlb.rotation.y = -Math.PI / 2; dlb.position.set(RA + 0.0355, 0, 0); arm.add(dlb);
  var scat = mk(arm, cyl(0.0012, 0.0012, RA, 8), new T.MeshBasicMaterial({ color: 0x8f6bff, transparent: true, opacity: 0.0 }), RA / 2, 0, 0); scat.rotation.z = Math.PI / 2;
  S.contact(0.34, 0.34, CX, CZ, 0.5);
  mk(S.scene, cyl(0.03, 0.03, 0.004, 28), M.alu, -0.06, 0.002, 0.17); S.contact(0.08, 0.08, -0.06, 0.17, 0.5);
  var cap = new T.Group(); S.scene.add(cap); cap.position.set(-0.06, 0.012, 0.17);
  mk(cap, box(0.034, 0.003, 0.034), M.alu, 0, 0, 0); mk(cap, box(0.024, XRR ? 0.0012 : 0.0016, 0.024), sampM, 0, 0.0015, 0);

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
  var ang = instBox(0.0, -0.1, 0.05, 'GONIOMETER', XRR ? 'detector angle 2θ, reflectivity' : 'detector angle 2θ and counts', 0.22);
  genB.show('OFF', ''); ang.show(p.tmin.toFixed(2), '2θ °');
  var monG = new T.Group(); S.scene.add(monG); monG.position.set(0.34, 0, -0.1); monG.rotation.y = -0.3;
  var mb = S.rounded(0.3, 0.2, 0.03, 0.008, new T.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4 })); mb.position.set(0, 0.115, 0); monG.add(mb);
  mk(monG, cyl(0.012, 0.016, 0.07, 14), M.alu, 0, 0.035, -0.01); mk(monG, box(0.12, 0.008, 0.08), M.alu, 0, 0.004, 0);
  var plotTex = S.liveTex(768, 480), plot = new T.Mesh(new T.PlaneGeometry(0.28, 0.175), new T.MeshBasicMaterial({ map: plotTex, toneMapped: false })); plot.position.set(0, 0.115, 0.017); monG.add(plot);
  S.contact(0.34, 0.2, 0.34, -0.1, 0.5);

  var plotKey = '';
  function drawPlot() {
    var nfound = (st.lines ? st.lines.length : 0) + (st.fr ? st.fr.length : 0);
    var key = PROG + '|' + st.scanned + '|' + nfound + '|' + st.c1 + '|' + st.c2; if (key === plotKey) return; plotKey = key;
    plotTex.draw(function (x, w, h) {
      x.fillStyle = '#10161d'; x.fillRect(0, 0, w, h);
      var L = 74, R = 18, Tp = 30, B = 52, x0 = p.tmin, x1 = p.tmax;
      var X = function (t) { return L + (t - x0) / (x1 - x0) * (w - L - R); };
      var ymax = 1, ymin = 0, Y;
      if (XRR) { ymin = -9; ymax = 0.3; Y = function (v) { return h - B - (Math.log(Math.max(v, 1e-12)) / Math.LN10 - ymin) / (ymax - ymin) * (h - B - Tp); }; }
      else { if (YS.length) for (var i = 0; i < YS.length; i += 4) if (YS[i] > ymax) ymax = YS[i]; ymax *= 1.08; Y = function (v) { return h - B - v / ymax * (h - B - Tp); }; }
      x.strokeStyle = 'rgba(255,255,255,.14)'; x.fillStyle = '#9aa7b6'; x.font = '600 18px "JetBrains Mono", monospace'; x.lineWidth = 1;
      var xstep = XRR ? 1 : 20;
      for (var a = Math.ceil(x0 / xstep) * xstep; a <= x1; a += xstep) { x.beginPath(); x.moveTo(X(a), Tp); x.lineTo(X(a), h - B); x.stroke(); x.fillText(a + '°', X(a) - 10, h - B + 22); }
      if (XRR) { for (var e = -8; e <= 0; e += 2) { var yy = h - B - (e - ymin) / (ymax - ymin) * (h - B - Tp); x.beginPath(); x.moveTo(L, yy); x.lineTo(w - R, yy); x.stroke(); x.fillText('1e' + e, 6, yy + 5); } }
      else for (var c = 0; c <= 4; c++) { var yv = ymax * c / 4; x.beginPath(); x.moveTo(L, Y(yv)); x.lineTo(w - R, Y(yv)); x.stroke(); x.fillText(Math.round(yv), 6, Y(yv) + 5); }
      x.fillStyle = '#e8eaec'; x.font = '600 20px "Public Sans", sans-serif'; x.fillText('2θ (degrees)', w / 2 - 50, h - 12); x.fillText(XRR ? 'reflectivity (log scale)' : 'counts', 8, 22);
      if (YS.length) { x.strokeStyle = '#5ee0a0'; x.lineWidth = 2; x.beginPath(); var n = Math.min(XS.length, Math.floor(PROG * XS.length)), first = true, step = XRR ? 1 : 2;
        for (var j = 0; j < n; j += step) { if (first) { x.moveTo(X(XS[j]), Y(YS[j])); first = false; } else x.lineTo(X(XS[j]), Y(YS[j])); } x.stroke(); }
      x.fillStyle = '#ffd24a'; x.font = '600 15px "JetBrains Mono", monospace';
      if (st.lines) st.lines.forEach(function (q) { var yb = Y(q.height + p.bg); x.beginPath(); x.moveTo(X(q.tth), yb - 4); x.lineTo(X(q.tth) - 5, yb - 14); x.lineTo(X(q.tth) + 5, yb - 14); x.fill(); x.fillText(q.tth.toFixed(1), X(q.tth) - 16, yb - 18); });
      if (st.fr) st.fr.forEach(function (q) { var k = Math.round((q.tth - p.tmin) / 0.01), yb = Y(YS[Math.max(0, Math.min(YS.length - 1, k))] || 1e-6); x.beginPath(); x.moveTo(X(q.tth), yb - 4); x.lineTo(X(q.tth) - 5, yb - 14); x.lineTo(X(q.tth) + 5, yb - 14); x.fill(); });
    });
  }
  S.addApparatus('gonio', gon, XRR ? 'Reflectometer' : 'Powder diffractometer', XRR ? 'The sample at the centre of the goniometer, the tube at a grazing angle and the detector on an arm that turns through 2θ.' : 'A Bragg-Brentano goniometer: the sample at the centre, the tube on one side and the detector on an arm that turns through 2θ.');
  S.addApparatus('sample', cap, SAMPLE, XRR ? 'A flat film on a polished silicon wafer. The beam grazes it at a fraction of a degree.' : 'A fine powder pressed flat in a holder. Many tiny crystals point every way, so some are always at the Bragg angle.');
  S.addApparatus('gen', genB.group, 'X-ray generator', 'Supplies the tube. The shutter is opened only from outside the interlocked cabinet.');
  S.addApparatus('ang', ang.group, 'Goniometer control', 'Shows the detector angle 2θ and drives the scan.');
  S.addApparatus('mon', monG, 'Scan display', XRR ? 'The reflectivity against 2θ on a log scale.' : 'The counts the detector records, against 2θ.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every line you find is written here, as in a real practical file.');
  var hudA = S.hudCard('Detector angle 2θ'), hudI = S.hudCard(XRR ? 'Reflectivity' : 'Counts');
  drawPlot();

  // ================================================================ human actions
  function mountSample() {
    if (busy() || st.mounted) return Promise.resolve();
    var a = cap.position.clone(), b = new T.Vector3(CX, 0.0345, CZ);
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.01, 0)), function (k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.08 * Math.sin(Math.PI * k) + (b.y - a.y) * k + 0.01, a.z + (b.z - a.z) * k); },
      function (k) { cap.position.set(a.x + (b.x - a.x) * k, a.y + 0.08 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); }, { mode: 'top', ms: 1300, reachMs: 650 })
      .then(function () { cap.visible = false; sampleOn.visible = true; st.mounted = true; S.say(XRR ? 'The film is on the sample stage, its surface level with the goniometer axis.' : 'The powder holder is on the sample stage, its surface level with the goniometer axis.'); S.render(); });
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
    st.scanning = true;
    var sc = KN.scan(p); XS = sc[0]; YS = sc[1]; PK = XRR ? null : KN.peaks(p);
    S.say('Scanning 2θ from ' + p.tmin + '° to ' + p.tmax + '°.');
    return S.tween(5200, function (k) { PROG = k; st.tth = p.tmin + (p.tmax - p.tmin) * k; }).then(function () { PROG = 1; st.tth = p.tmax; st.scanned = true; st.scanning = false; S.say('The scan is complete.'); S.render(); });
  }
  function findLines() {
    if (st.lines) { S.say('The lines are already found.'); return false; }
    if (!st.scanned) { S.say('Run the scan first.'); return false; }
    var ls = KN.findLines(XS, YS); if (ls.length < 3) { S.say('Fewer than three lines: the pattern cannot be indexed.'); return false; }
    st.lines = ls;
    ls.forEach(function (q) { S.addRow({ tth: q.tth, fwhm: q.fwhm, area: q.area, ph: '—', N: 0, s2: Math.pow(Math.sin(q.tth * D2R / 2), 2), a: 0 }); });
    S.say(ls.length + ' lines found. Each has a position, a width and an area.'); return true;
  }
  function pickStruct(slot, t) { if (busy()) return; if (slot === 1) st.c1 = t; else st.c2 = t; S.render(); }
  function refine() {
    if (busy()) return false;
    if (!st.lines) { S.say('Find the lines first.'); return false; }
    if (!st.c1 || (MIX && !st.c2)) { S.say(MIX ? 'Choose a structure model for both phases.' : 'Choose the structure model of this sample.'); return false; }
    var lam = p.lam * 1e10, used = st.lines.map(function () { return false; }), phs = MIX ? [st.c1, st.c2] : [st.c1], res = [], sw = [], bad = null;
    S.rows.forEach(function (r) { r.ph = '—'; r.N = 0; r.a = 0; });
    phs.forEach(function (t, idx) {
      var r = KN.indexPhase(st.lines, lam, t, used);
      if (!r) { bad = STRUCT[t]; return; }
      r.pairs.forEach(function (pr) { used[pr[0]] = true; S.rows[pr[0]].ph = 'Phase ' + (idx + 1); S.rows[pr[0]].N = pr[1]; S.rows[pr[0]].a = lam * Math.sqrt(pr[1]) / (2 * Math.sqrt(S.rows[pr[0]].s2)); });
      var rl = KN.refl(t, r.a, lam, p.tmin - 2, p.tmax + 2), map = {}, sg = 0, sgg = 0, zm = KN.ZMV[t];
      rl.forEach(function (q) { map[q.N] = q; });
      r.pairs.forEach(function (pr) { var q = map[pr[1]]; if (!q) return; var g = q.sf * q.lp / Math.pow(r.a, 6); sg += st.lines[pr[0]].area * g; sgg += g * g; });
      var sp = sgg > 0 ? sg / (p.I0 * sgg) : 0;
      res.push({ t: t, a: r.a, n: r.n }); sw.push(sp * zm[0] * zm[1] * Math.pow(r.a, 3));
    });
    if (bad) { S.say('With the ' + bad + ' model fewer than three lines fit one lattice: this structure does not match. Try another.'); S.rows.forEach(function (r) { r.ph = '—'; r.N = 0; r.a = 0; }); st.fit = null; S.book.draw(); S.render(); return false; }
    var tot = 0; sw.forEach(function (x) { tot += x; });
    st.fit = { res: res, w: sw.map(function (x) { return x / tot; }) };
    S.book.draw();
    S.say(MIX ? 'Both phases indexed. Refined a = ' + res.map(function (q) { return (q.a).toFixed(4) + ' Å'; }).join(' and ') + '; weight fractions ' + st.fit.w.map(function (x) { return (100 * x).toFixed(1) + ' %'; }).join(' and ') + '.' : 'Indexed ' + res[0].n + ' lines. Refined a = ' + res[0].a.toFixed(4) + ' Å by least squares on sin²θ.');
    S.render(); return true;
  }
  function findFringes() {
    if (st.fr) { S.say('The fringes are already marked.'); return false; }
    if (!st.scanned) { S.say('Run the scan first.'); return false; }
    var f = KN.fit(p);
    if (!f.tths || f.tths.length < 3 || !f.d) { S.say('Fewer than three usable maxima above the critical angle: scan a wider range.'); return false; }
    st.fr = f.tths.map(function (t, i) { return { tth: t, m: f.m0 + i }; });
    st.fr.forEach(function (q) { S.addRow({ m: q.m, tth: q.tth, s2: Math.pow(Math.sin(q.tth * D2R / 2), 2), m2: q.m * q.m }); });
    S.say(st.fr.length + ' maxima marked above the critical angle (2θc about ' + f.tthc.toFixed(2) + '°). The orders start at m = ' + f.m0 + ' because that numbering gives the straightest line.');
    return true;
  }
  function wlin() {
    var pts = S.rows.filter(function (r) { return r.m2 !== undefined; }).map(function (r) { return [r.m2, r.s2]; });
    return pts.length >= 3 ? S.fit.linear(pts) : null;
  }

  function result(rows) {
    if (XRR) {
      var f = wlin(); if (!f || f.m <= 0) return null;
      var d = p.lam / (2 * Math.sqrt(f.m));
      var rho = f.c > 0 ? (f.c / 2) * 2 * Math.PI / (2.8179403262e-15 * p.lam * p.lam * 6.02214076e23 * 1000 * p.ze_f) / 1000 : 0;
      return { label: ML ? 'Bilayer period' : 'Film thickness', value: d * 1e9, unit: 'nm', digits: 2, truth: p.d1 * 1e9,
        note: 'Fit of sin²θ against order² over ' + rows.length + ' maxima: slope (λ/2d)² = ' + f.m.toExponential(3) + ', so d = λ / (2 √slope).' + (ML ? '' : ' The intercept ' + f.c.toExponential(2) + ' is 2δ of the film: its density comes out near ' + rho.toFixed(1) + ' g/cm³ (an estimate, since the intercept is sensitive to the first fringes).') + ' Roughness is in the model but not measured here.' };
    }
    if (!st.fit) return null;
    if (MIX) {
      var iSi = -1; st.fit.res.forEach(function (q, i) { if (q.t === 1) iSi = i; });
      if (iSi < 0) return null;
      return { label: 'Weight fraction of silicon', value: st.fit.w[iSi], unit: '', digits: 3, truth: p.w1,
        note: 'Refined lattice parameters ' + st.fit.res.map(function (q) { return (q.a).toFixed(4) + ' Å (' + STRUCT[q.t] + ')'; }).join(' and ') + '. W = S(ZMV)/Σ S(ZMV) with S fitted to the line areas; no absorption correction.' };
    }
    return { label: 'Lattice parameter a', value: st.fit.res[0].a, unit: 'Å', digits: 4, truth: p.a1 * 1e10,
      note: 'Least squares of sin²θ = (λ²/4a²) N over ' + st.fit.res[0].n + ' indexed lines. Atomic positions were held fixed, so this is a lattice and scale-factor refinement, not a full Rietveld refinement.' };
  }

  var cols = XRR
    ? [{ label: 'order m', get: function (r) { return r.m; } }, { label: '2θ (°)', get: function (r) { return r.tth.toFixed(3); } }, { label: 'sin²θ (10⁻⁴)', get: function (r) { return (r.s2 * 1e4).toFixed(3); } }, { label: 'm²', get: function (r) { return r.m2; } }]
    : [{ label: '2θ (°)', get: function (r) { return r.tth.toFixed(3); } }, { label: 'FWHM (°)', get: function (r) { return r.fwhm.toFixed(3); } }, { label: 'area', get: function (r) { return Math.round(r.area); } },
      { label: 'phase', get: function (r) { return r.ph; } }, { label: 'N', get: function (r) { return r.N || '—'; } }, { label: 'a (Å)', get: function (r) { return r.a ? r.a.toFixed(4) : '—'; } }];

  var theoryXRD = {
    principle: S.lab.theory,
    formula: '2 d sinθ = λ,   sin²θ = (λ² / 4a²) N',
    formulaNote: 'N = h²+k²+l²;  W = S(ZMV) / Σ S(ZMV) for a mixture',
    more: ['The structure factor of the cell decides which N appear: silicon (diamond) 3, 8, 11, 16, 19...; the perovskite every N; the spinel 3, 8, 11, 12, 16, 19...', 'Least squares over all lines averages the small angle errors of each line.', 'This bench keeps the atomic positions fixed. A full Rietveld refinement would also refine them, the widths and the background.'],
    precautions: S.lab.safety };
  var theoryXRR = {
    principle: S.lab.theory,
    formula: 'sin²θm = (m λ / 2d)² + 2δ',
    formulaNote: 'd the film thickness (or the bilayer period), δ the refraction decrement',
    more: ['For small angles far above θc the spacing of the fringes gives d = λ / (2 Δθ), with Δθ in radians.', 'The critical angle is θc = √(2δ); below it the beam is totally reflected.', 'Roughness lowers the fringe contrast and makes the curve fall faster; this bench does not measure it.'],
    precautions: S.lab.safety };

  var scanInfo = XRR ? 'The detector turns from ' + p.tmin + '° to ' + p.tmax + '°, twice as fast as the sample. The reflectivity is drawn as it arrives.' : 'The detector turns from ' + p.tmin + '° to ' + p.tmax + '° while the sample turns half as fast. The counts are drawn as they arrive.';
  function structRow(u, slot) {
    var cur = slot === 1 ? st.c1 : st.c2;
    u.p(slot === 1 ? (MIX ? 'Phase 1 structure model (from the data card):' : 'Structure model from the sample\'s data card:') : 'Phase 2 structure model:');
    u.row(u.button('Diamond', function () { pickStruct(slot, 1); }, cur === 1, S.hand.busy), u.button('Perovskite', function () { pickStruct(slot, 2); }, cur === 2, S.hand.busy), u.button('Spinel', function () { pickStruct(slot, 3); }, cur === 3, S.hand.busy));
  }

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { gonio: [[-0.3, 0.3, 0.2], [-0.3, 0.03, -0.16]], sample: [[-0.1, 0.2, 0.33], [-0.06, 0.02, 0.17]], gen: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]], ang: [[0.0, 0.22, 0.08], [0.0, 0.05, -0.1]],
      mon: [[0.38, 0.24, 0.18], [0.34, 0.11, -0.1]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: XRR ? theoryXRR : theoryXRD,
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Sample: ' + SAMPLE, 'Cu Kα1, λ = ' + (p.lam * 1e10).toFixed(4) + ' Å. Simulated bench.'], columns: cols },
    graph: XRR ? { x: function (r) { return r.m2 === undefined ? NaN : r.m2; }, y: function (r) { return r.s2 === undefined ? NaN : r.s2 * 1e4; }, xlabel: 'm²', ylabel: 'sin²θ (10⁻⁴)',
        line: function (pts) { var f = S.fit.linear(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return f ? function (x) { return f.m * x + f.c; } : null; } }
      : { x: function (r) { return r.N && r.ph === 'Phase 1' ? r.N : NaN; }, y: function (r) { return r.N && r.ph === 'Phase 1' ? r.s2 : NaN; }, xlabel: 'N = h²+k²+l² (phase 1)', ylabel: 'sin²θ',
        line: function (pts) { var k = S.fit.origin(pts.filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); })); return isFinite(k) ? function (x) { return k * x; } : null; } },
    result: result,
    tol: XRR ? 0.01 : (MIX ? 0.03 : 0.002),
    resultNote: XRR ? 'The thickness is the slope of your own fringe line, with the lab\'s true value alongside.' : 'The refined value is shown with the lab\'s true value alongside.',
    chips: XRR ? ['Why do the fringes appear?', 'What is the critical angle?', 'Check my readings', 'Why use sin²θ against m²?'] : ['Why are some lines missing?', 'How do I tell the structures apart?', 'Check my readings', 'What is a scale factor?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, sample: SAMPLE, mounted: st.mounted, shutter_open: st.open, scanned: st.scanned, lines_found: st.lines ? st.lines.length : (st.fr ? st.fr.length : 0), structure_models: [st.c1 ? STRUCT[st.c1] : 'none yet', st.c2 ? STRUCT[st.c2] : 'none yet'] }; },
    steps: [
      { id: 'setup', title: 'Load and expose', view: 'gonio', render: function (u) {
          u.h2(XRR ? 'Load the film, open the shutter' : 'Load the powder, open the shutter');
          u.p(XRR ? 'The film on its silicon wafer waits on the tray. Put it on the sample stage, close the cabinet door and open the shutter.' : 'The powder is pressed flat in its holder on the tray. Put it on the sample stage, close the cabinet door and open the shutter from the generator.');
          u.task('1. Load the sample', st.mounted, st.mounted ? 'On the stage' : 'On the tray').add(u.button(st.mounted ? 'Loaded' : 'Load the sample', function () { S.focus('gonio'); mountSample(); }, !st.mounted, st.mounted || S.hand.busy));
          u.task('2. Open the shutter', st.open, st.open ? 'X-rays on' : 'Shutter closed').add(u.button(st.open ? 'Shutter open' : 'Open the shutter', function () { S.focus('gen'); openShutter(); }, !st.open && st.mounted, st.open || !st.mounted || S.hand.busy));
          u.note('The tube is interlocked: the shutter cannot open with the cabinet door open. This is a simulated bench of a facility instrument.');
          u.next('Next: scan', st.mounted && st.open);
        },
        ok: function () { return st.mounted && st.open; }, auto: function () { return mountSample().then(openShutter); } },
      { id: 'scan', title: 'Scan 2θ', view: 'mon', render: function (u) {
          u.h2('Scan the detector through 2θ');
          u.p(scanInfo);
          u.task('Run the scan', st.scanned, st.scanned ? 'Scan recorded' : st.scanning ? 'Scanning…' : 'Ready').add(u.button(st.scanned ? 'Recorded' : 'Start the scan', function () { S.focus('mon'); runScan(); }, !st.scanned, st.scanned || st.scanning || S.hand.busy));
          u.live(function () { return 'Detector at ' + st.tth.toFixed(2) + '°'; });
          u.next('Next: analyse', st.scanned);
        },
        ok: function () { return st.scanned; }, auto: function () { return runScan(); } },
      { id: 'analyse', title: XRR ? 'Fringes and the fit' : 'Index and refine', view: 'mon', render: function (u) {
          if (XRR) {
            u.h2('Mark the fringe maxima');
            u.p('Mark the maxima above the critical angle, number them with consecutive orders and plot sin²θ against order². The slope gives the thickness.');
            u.task('Find and number the maxima', !!st.fr, st.fr ? st.fr.length + ' maxima' : 'Not done').add(u.button(st.fr ? 'Marked' : 'Mark the maxima', function () { S.focus('mon'); findFringes(); }, !st.fr, !!st.fr || S.hand.busy));
          } else {
            u.h2('Find the lines, index them, refine');
            u.p(MIX ? 'Find the lines, choose a structure model for each phase from the data card and refine. The program fits the lattice parameter of each phase and its scale factor.' : 'Find the lines, choose the structure model from the data card and refine the lattice parameter.');
            u.task('1. Find the lines', !!st.lines, st.lines ? st.lines.length + ' lines' : 'Not done').add(u.button(st.lines ? 'Found' : 'Find the lines', function () { S.focus('mon'); findLines(); }, !st.lines, !!st.lines || S.hand.busy));
            structRow(u, 1); if (MIX) structRow(u, 2);
            u.task('2. Refine', !!st.fit, st.fit ? 'Done' : 'Not done').add(u.button(st.fit ? 'Refined' : 'Index and refine', function () { refine(); }, !st.fit && !!st.lines, !!st.fit || !st.lines || S.hand.busy));
          }
          u.h3('Table'); u.table();
          u.next('Next: the result', XRR ? !!st.fr : !!st.fit);
        },
        ok: function () { return XRR ? !!st.fr : !!st.fit; },
        auto: function () {
          if (XRR) { findFringes(); return Promise.resolve(); }
          findLines(); st.c1 = Math.round(p.t1); if (MIX) st.c2 = Math.round(p.t2); refine(); return Promise.resolve();
        } }
    ],
    tick: function () {
      genB.show(st.open ? '40·20' : 'OFF', st.open ? 'kV·mA' : ''); ang.show(st.tth.toFixed(2), '2θ °');
      arm.rotation.y = st.tth * D2R; sampleStage.rotation.y = st.tth * D2R / 2;
      beam.material.opacity = st.open ? 0.5 : 0; scat.material.opacity = st.open ? 0.5 : 0;
      var v = 0;
      if (st.scanned || st.scanning) { var k = Math.max(0, Math.min(XS.length - 1, Math.round((st.tth - p.tmin) / (XRR ? 0.01 : 0.02)))); v = YS.length ? YS[k] : 0; }
      hudA.set(st.tth.toFixed(2) + '°'); hudI.set(st.open ? (XRR ? v.toExponential(2) : Math.round(v) + '') : '—');
      drawPlot();
    },
  };
});
