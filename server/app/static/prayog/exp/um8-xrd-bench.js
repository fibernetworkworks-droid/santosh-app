/* Prayogshala studio RIG: the POWDER DIFFRACTOMETER of wave 8 (B.Sc. solid state physics and nanomaterials).
   A theta-2theta goniometer in a lead-glass enclosure: the Cu K-alpha tube on one arm, the detector on the other, the
   powder slide at the centre, and the control computer that draws the diffractogram. One rig, two set-ups:
     um8-xrd-analysis  survey scan -> line angles -> sin^2 theta ratios -> lattice type and a; slow scan -> Scherrer size
     um8-nano-xrd      survey scan -> slow scan of the card's line -> width -> instrument width off -> Scherrer size
   Every intensity comes from the um8_xrd kernel (packs/ug_matter_w8.js): exact Bragg positions, Gaussian lines of
   width sqrt(beta_size^2 + beta_inst^2), heights from a simple model (said on the screen). SIMULATED DATA. */
HoolaStudio.define('um8-xrd-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.um8_xrd, assign = HK.assign;
  var p = HK.paramsFor('um8_xrd', S.lab.params);
  var NANO = S.lab.id.indexOf('um8-nano-xrd') === 0;
  var V_ = S.lab.variant || {};
  var SAMPLE = V_.sample || (NANO ? 'CdS nanopowder (zinc blende)' : 'Nanocrystalline copper powder');
  var HKL = Math.round(p.ph) + '' + Math.round(p.pk) + '' + Math.round(p.pl);
  var LINE = KN.peak(p);                                    // the card's line
  var HI = NANO ? 70 : 100, LO = NANO ? 15 : 20, STEP = 0.05;
  var NHKL = { 3: '111', 4: '200', 8: '220', 11: '311', 12: '222', 16: '400', 19: '331', 20: '420', 24: '422', 27: '511/333' };
  var st = { loaded: false, door: false, survey: null, peaks: null, indexed: false, fine: null, fstep: 0.02, arm: 15, scanning: false };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function fmt(v, d) { return isFinite(v) ? v.toFixed(d) : '—'; }
  var D2R = Math.PI / 180;

  // ================================================================ the diffractometer
  var dif = new T.Group(); S.scene.add(dif); dif.position.set(-0.18, 0, -0.18);
  var baseP = S.rounded(0.46, 0.3, 0.03, 0.01, new T.MeshStandardMaterial({ color: 0xd9dbe0, roughness: 0.5 }));
  baseP.rotation.x = -Math.PI / 2; baseP.position.y = 0.015; dif.add(baseP);
  var CEN = new T.Vector3(0, 0.17, 0);
  var circ = S.mesh(new T.CylinderGeometry(0.13, 0.13, 0.03, 64), new T.MeshStandardMaterial({ color: 0xc4c8cf, roughness: 0.35, metalness: 0.6 }));
  circ.rotation.x = Math.PI / 2; circ.position.set(0, CEN.y, -0.03); dif.add(circ);
  var circTex = S.canvasTex(512, 512, function (x, w, h) {
    x.fillStyle = '#c4c8cf'; x.fillRect(0, 0, w, h); x.strokeStyle = '#2b2f36'; x.fillStyle = '#2b2f36'; x.font = '600 18px "Public Sans", sans-serif';
    for (var a = 0; a <= 180; a += 5) { var t = (180 + a) * D2R, r1 = 240, r2 = a % 10 ? 228 : 216;
      x.lineWidth = a % 10 ? 2 : 3; x.beginPath(); x.moveTo(256 + Math.cos(t) * r1, 256 - Math.sin(t) * r1); x.lineTo(256 + Math.cos(t) * r2, 256 - Math.sin(t) * r2); x.stroke(); }
    x.textAlign = 'center'; x.fillText('2θ', 256, 300);
  });
  var face = new T.Mesh(new T.CircleGeometry(0.13, 64), new T.MeshStandardMaterial({ map: circTex, roughness: 0.4 }));
  face.position.set(0, CEN.y, -0.0145); dif.add(face);
  var pillar = S.mesh(new T.BoxGeometry(0.06, CEN.y - 0.03, 0.05), M.grey); pillar.position.set(0, (CEN.y - 0.03) / 2 + 0.03, -0.05); dif.add(pillar);
  // tube arm (fixed at -theta) and detector arm (at +theta about the vertical through the sample: Bragg-Brentano)
  function arm(len, w, col) { var g = new T.Group(); g.position.copy(CEN); dif.add(g);
    var bar = S.mesh(new T.BoxGeometry(len, 0.012, 0.02), M.chrome); bar.position.x = len / 2; g.add(bar); return g; }
  var tArm = arm(0.16), dArm = arm(0.16);
  var tube = S.mesh(new T.CylinderGeometry(0.022, 0.022, 0.09, 24), new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.4, metalness: 0.4 }));
  tube.rotation.z = Math.PI / 2; tube.position.set(0.17, 0, 0); tArm.add(tube);
  var tLbl = S.label('Cu Kα  40 kV', { w: 0.05, ratio: 0.25, color: '#f0f0f0' }); tLbl.position.set(0.17, 0, 0.023); tLbl.rotation.z = Math.PI; tArm.add(tLbl);
  var det = S.mesh(new T.BoxGeometry(0.07, 0.036, 0.036), new T.MeshStandardMaterial({ color: 0x3a4f6e, roughness: 0.4 }));
  det.position.set(0.16, 0, 0); dArm.add(det);
  var dLbl = S.label('DETECTOR', { w: 0.045, ratio: 0.25, color: '#f0f0f0' }); dLbl.position.set(0.16, 0, 0.0185); dArm.add(dLbl);
  var holder = S.mesh(new T.BoxGeometry(0.04, 0.004, 0.03), M.alu); holder.position.copy(CEN); dif.add(holder);
  function setArms(tth) {                  // the tube on the left, the detector on the right, each theta above the sample plane
    var th = tth / 2 * D2R;
    tArm.rotation.z = Math.PI - th; dArm.rotation.z = th; st.arm = tth;
  }
  setArms(30);
  // the enclosure: lead glass on a frame, a hinged front door
  var glassM = new T.MeshStandardMaterial({ color: 0xcfe0d8, transparent: true, opacity: 0.18, roughness: 0.05 });
  var encl = new T.Group(); dif.add(encl);
  [[0, 0.17, -0.15, 0.46, 0.3, 0.004], [-0.23, 0.17, 0, 0.004, 0.3, 0.3], [0.23, 0.17, 0, 0.004, 0.3, 0.3], [0, 0.32, 0, 0.46, 0.004, 0.3]].forEach(function (b) {
    var g = S.mesh(new T.BoxGeometry(b[3], b[4], b[5]), glassM, false); g.position.set(b[0], b[1], b[2]); encl.add(g); });
  var doorG = new T.Group(); doorG.position.set(-0.23, 0, 0.15); dif.add(doorG);
  var door = S.mesh(new T.BoxGeometry(0.46, 0.3, 0.004), glassM, false); door.position.set(0.23, 0.17, 0); doorG.add(door);
  var handle = S.mesh(new T.BoxGeometry(0.008, 0.06, 0.012), M.chrome); handle.position.set(0.42, 0.17, 0.008); doorG.add(handle);
  var warn = S.label('X-RAY INTERLOCK', { w: 0.1, ratio: 0.18, color: '#c0392b' }); warn.position.set(0.23, 0.29, 0.003); doorG.add(warn);
  doorG.rotation.y = -1.2;
  S.contact(0.5, 0.34, -0.18, -0.18, 0.5);
  // the sample box with the slide
  var slideG = new T.Group(); S.scene.add(slideG);
  var SLIDE_HOME = new T.Vector3(0.1, 0.012, 0.14); slideG.position.copy(SLIDE_HOME);
  var slide = S.mesh(new T.BoxGeometry(0.035, 0.003, 0.025), M.glass); slideG.add(slide);
  var powder = S.mesh(new T.BoxGeometry(0.022, 0.0012, 0.016), new T.MeshStandardMaterial({ color: /Fe2O3|hemat/i.test(SAMPLE) ? 0x8b2e1c : /CdS/i.test(SAMPLE) ? 0xd9a520 : /copper/i.test(SAMPLE) ? 0xa8603a : /silicon/i.test(SAMPLE) ? 0x6d7480 : 0xf2f0ea, roughness: 0.95 }));
  powder.position.y = 0.002; slideG.add(powder);
  var sbox = S.rounded(0.08, 0.06, 0.012, 0.005, M.wood); sbox.rotation.x = -Math.PI / 2; sbox.position.set(0.1, 0.006, 0.14); S.scene.add(sbox);
  // the control computer
  var mon = new T.Group(); S.scene.add(mon); mon.position.set(0.32, 0, -0.22); mon.rotation.y = -0.35;
  var mfoot = S.rounded(0.16, 0.1, 0.01, 0.008, M.grey); mfoot.rotation.x = -Math.PI / 2; mfoot.position.y = 0.006; mon.add(mfoot);
  var mneck = S.mesh(new T.CylinderGeometry(0.012, 0.015, 0.08, 16), M.grey); mneck.position.y = 0.05; mon.add(mneck);
  var mbez = S.rounded(0.32, 0.2, 0.014, 0.008, new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.4 })); mbez.position.set(0, 0.19, 0.012); mon.add(mbez);
  var scrTex = S.liveTex(1280, 800);
  var scr = new T.Mesh(new T.PlaneGeometry(0.3, 0.1875), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scr.position.set(0, 0.19, 0.0195); mon.add(scr);
  var ctl = new T.Group(); S.scene.add(ctl); ctl.position.set(0.3, 0, 0.1); ctl.rotation.y = -0.3;
  var cbox = S.rounded(0.2, 0.12, 0.06, 0.01, new T.MeshStandardMaterial({ color: 0xe3e1da, roughness: 0.5 })); cbox.rotation.x = -Math.PI / 2; cbox.position.y = 0.03; ctl.add(cbox);
  var scanB = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.008, 20), M.green); scanB.position.set(-0.04, 0.062, 0.02); ctl.add(scanB);
  var shut = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.008, 20), new T.MeshStandardMaterial({ color: 0xd9a520 })); shut.position.set(0.04, 0.062, 0.02); ctl.add(shut);
  var cLbl = S.label('SCAN      SHUTTER', { w: 0.12, ratio: 0.12, color: '#2b2f36' }); cLbl.rotation.x = -Math.PI / 2; cLbl.position.set(0, 0.0605, 0.045); ctl.add(cLbl);
  S.contact(0.24, 0.16, 0.3, 0.1, 0.45);

  S.addApparatus('dif', dif, 'Theta-2theta goniometer', 'The X-ray tube and the detector swing together about the powder, each at θ to its surface, so the detector sees reflections from planes parallel to the surface at 2θ.');
  S.addApparatus('slide', slideG, SAMPLE, 'The dried powder pressed flat in a glass slide, its surface level with the goniometer axis.');
  S.addApparatus('mon', mon, 'Control computer', 'Draws the diffractogram: counts per second against 2θ.');
  S.addApparatus('ctl', ctl, 'Control unit', 'SCAN starts a scan; the shutter opens only with the door closed.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every line you read is written here.');
  var hudA = S.hudCard('Detector 2θ'), hudI = S.hudCard('Counts per second');

  // ================================================================ data from the kernel
  function I(t) { return KN.intensity(t, p); }
  function survey() { var xs = [], ys = [], t; for (t = LO; t <= HI + 1e-9; t += STEP) { xs.push(t); ys.push(I(t)); } return { x: xs, y: ys, bg: Math.min.apply(null, ys) }; }
  function findPeaks(sv) {
    var top = Math.max.apply(null, sv.y), out = [], i, a, b, c, off;
    for (i = 1; i < sv.y.length - 1; i++) {
      if (sv.y[i] > sv.y[i - 1] && sv.y[i] >= sv.y[i + 1] && sv.y[i] - sv.bg > 0.08 * (top - sv.bg)) {
        a = Math.log(Math.max(sv.y[i - 1] - sv.bg, 1e-6)); b = Math.log(sv.y[i] - sv.bg); c = Math.log(Math.max(sv.y[i + 1] - sv.bg, 1e-6));
        off = (a - 2 * b + c) !== 0 ? 0.5 * (a - c) / (a - 2 * b + c) : 0;
        out.push({ tth: sv.x[i] + off * STEP, h: sv.y[i] - sv.bg });
      }
    }
    return out;
  }
  function index(peaks) {
    var s2 = peaks.map(function (q) { var s = Math.sin(q.tth / 2 * D2R); return s * s; }), n1, ok, Ns, i, v;
    for (n1 = 1; n1 <= 4; n1++) {
      ok = true; Ns = [];
      for (i = 0; i < s2.length; i++) { v = s2[i] / s2[0] * n1; if (Math.abs(v - Math.round(v)) > 0.08 || [7, 15, 23, 28].indexOf(Math.round(v)) >= 0) { ok = false; break; } Ns.push(Math.round(v)); }
      if (ok) return Ns;
    }
    return null;
  }
  function lattice(Ns) {
    if (!Ns) return 'not indexed';
    if (Ns.indexOf(4) >= 0 && Ns.every(function (n) { return [3, 4, 8, 11, 12, 16, 19, 20, 24, 27].indexOf(n) >= 0; })) return 'face-centred cubic';
    if (Ns.every(function (n) { return [3, 8, 11, 16, 19, 24, 27].indexOf(n) >= 0; })) return 'diamond cubic';
    if (Ns.every(function (n) { return n % 2 === 0; })) return 'body-centred cubic';
    return 'simple cubic';
  }
  function fineScan(center, step, bg) {
    var w0 = KN.width(center, p), xs = [], ys = [], t, im = 0, i, j, half, xl, xr;
    for (t = center - 3 * w0; t <= center + 3 * w0 + 1e-9; t += step) { xs.push(t); ys.push(I(t)); }
    for (i = 1; i < ys.length; i++) if (ys[i] > ys[im]) im = i;
    half = (ys[im] - bg) / 2 + bg; i = im; while (i > 0 && ys[i] > half) i--;
    j = im; while (j < ys.length - 1 && ys[j] > half) j++;
    if (i === im || j === im || ys[i + 1] === ys[i] || ys[j] === ys[j - 1]) return null;
    xl = xs[i] + (half - ys[i]) / (ys[i + 1] - ys[i]) * step; xr = xs[j - 1] + (half - ys[j - 1]) / (ys[j] - ys[j - 1]) * step;
    var fw = xr - xl, b = Math.sqrt(Math.max(fw * fw - p.binst * p.binst, 0)) * D2R, th = xs[im] / 2 * D2R;
    return { x: xs, y: ys, peak: xs[im], fwhm: fw, beta: b / D2R, L: p.K * p.lam / (b * Math.cos(th)) * 1e9 };
  }

  // ================================================================ the screen
  function drawScreen() {
    scrTex.draw(function (x) {
      var W = 1280, H = 800, px = 70, py = 90, pw = 1150, ph = 640;
      x.fillStyle = '#0d1b2a'; x.fillRect(0, 0, W, H);
      x.fillStyle = '#e8eef7'; x.font = '600 34px "JetBrains Mono", monospace'; x.fillText('XRD  ' + SAMPLE.split(' (')[0] + '   Cu Kα1 λ = 1.5406 Å', 30, 52);
      x.strokeStyle = '#3b5274'; x.lineWidth = 2; x.strokeRect(px, py, pw, ph);
      var sv = st.fine || st.survey;
      if (!sv) { x.fillStyle = '#6f86a6'; x.font = '500 30px "JetBrains Mono", monospace'; x.fillText(st.scanning ? 'Scanning ...' : 'No scan yet.', px + 30, py + 60); return; }
      var x0 = sv.x[0], x1 = sv.x[sv.x.length - 1], y1 = Math.max.apply(null, sv.y) * 1.08;
      var X = function (v) { return px + (v - x0) / (x1 - x0) * pw; }, Y = function (v) { return py + ph - v / y1 * ph; };
      x.strokeStyle = '#7fb2ff'; x.lineWidth = 3; x.beginPath();
      sv.x.forEach(function (t, i) { if (i) x.lineTo(X(t), Y(sv.y[i])); else x.moveTo(X(t), Y(sv.y[i])); }); x.stroke();
      x.fillStyle = '#9fb3cc'; x.font = '500 22px "JetBrains Mono", monospace';
      for (var g = Math.ceil(x0 / 10) * 10; g <= x1; g += (x1 - x0 > 20 ? 10 : 1)) x.fillText(String(g), X(g) - 12, py + ph + 28);
      x.fillText(st.fine ? 'slow scan, step ' + st.fstep + '°' : 'survey, step ' + STEP + '°   (line heights: a simple model)', px + 10, py + 28);
      if (!st.fine && st.peaks) { x.fillStyle = '#ffd36b'; st.peaks.forEach(function (q, i) { x.fillText(fmt(q.tth, 2), X(q.tth) - 30, Y(q.h + st.survey.bg) - 12); }); }
      if (st.fine) { x.fillStyle = '#ffd36b'; x.fillText('FWHM ' + fmt(st.fine.fwhm, 4) + '°', px + pw - 280, py + 28); }
    });
  }
  drawScreen();

  // ================================================================ actions
  function loadSample() {
    if (busy() || st.loaded) return Promise.resolve();
    var from = slideG.position.clone(); var to = dif.localToWorld(CEN.clone().add(new T.Vector3(0, 0.0035, 0)));
    return openDoor(true).then(function () {
      return S.hand.pinchMove(from, function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k); },
        function (k) { slideG.position.set(from.x + (to.x - from.x) * k, Math.max(from.y, to.y) + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k); },
        { mode: 'side', ms: 1200, reachMs: 650 });
    }).then(function () { slideG.position.copy(to); st.loaded = true; return openDoor(false); })
      .then(function () { S.say('The slide is in the holder, its powder surface on the goniometer axis, and the door is closed: the interlock lets the shutter open.'); S.render(); });
  }
  function openDoor(open) {
    if ((open && st.door) || (!open && !st.door)) return Promise.resolve();
    var pt = doorG.localToWorld(handle.position.clone()), a0 = doorG.rotation.y, a1 = open ? -1.2 : 0;
    return S.hand.pinchMove(pt, function (k) { var a = a0 + (a1 - a0) * k; return doorG.localToWorld(new T.Vector3(0.42 * Math.cos(a) * 0 + 0.42, 0.17, 0.008)); },
      function (k) { doorG.rotation.y = a0 + (a1 - a0) * k; }, { mode: 'front', ms: 700, reachMs: 500 })
      .then(function () { doorG.rotation.y = a1; st.door = open; });
  }
  doorG.rotation.y = 0;
  function sweep(t0, t1, ms) { return S.tween(ms, function (k) { setArms(t0 + (t1 - t0) * k); }).then(function () { setArms(t1); }); }
  function runSurvey() {
    if (busy()) return Promise.resolve(false);
    if (!st.loaded) { S.say('Load the sample first.'); return Promise.resolve(false); }
    st.scanning = true; st.fine = null; drawScreen();
    return S.hand.tap(scanB, 'top').then(function () { return sweep(LO, HI, 2200); }).then(function () {
      st.scanning = false; st.survey = survey(); st.peaks = findPeaks(st.survey); drawScreen();
      S.say('Survey from ' + LO + '° to ' + HI + '° in steps of ' + STEP + '°: ' + st.peaks.length + ' lines, at ' + st.peaks.map(function (q) { return fmt(q.tth, 2) + '°'; }).join(', ') + '.');
      S.render(); return true;
    });
  }
  function doIndex() {
    if (!st.peaks || st.indexed) return false;
    var Ns = index(st.peaks);
    if (!Ns) { S.say('These ratios do not fit a cubic lattice.'); return false; }
    st.peaks.forEach(function (q, i) {
      var s = Math.sin(q.tth / 2 * D2R), aa = p.lam * Math.sqrt(Ns[i]) / (2 * s) * 1e10;
      S.addRow({ kind: 'line', tth: q.tth, s2: s * s, ratio: s * s / Math.pow(Math.sin(st.peaks[0].tth / 2 * D2R), 2), N: Ns[i], hkl: NHKL[Ns[i]] || '?', a: aa });
    });
    st.indexed = true; st.lat = lattice(Ns);
    S.say('The ratios of sin²θ times ' + Ns[0] + ' are ' + Ns.join(', ') + ': the lattice is ' + st.lat + '.');
    S.render(); return true;
  }
  function runFine() {
    if (busy()) return Promise.resolve(false);
    if (!st.survey) { S.say('Run the survey scan first.'); return Promise.resolve(false); }
    var c = NANO ? LINE : (st.peaks && st.peaks[0] ? st.peaks[0].tth : LINE);
    st.scanning = true;
    return S.hand.tap(scanB, 'top').then(function () { var w = KN.width(c, p); return sweep(c - 3 * w, c + 3 * w, 1600); }).then(function () {
      st.scanning = false; var f = fineScan(c, st.fstep, st.survey.bg);
      if (!f) { S.say('The step is too coarse to read the width. Use a smaller step.'); return false; }
      st.fine = f; drawScreen();
      S.addRow({ kind: 'fine', step: st.fstep, peak: f.peak, fwhm: f.fwhm, beta: f.beta, L: f.L });
      S.say('Slow scan in steps of ' + st.fstep + '°: the line peaks at ' + fmt(f.peak, 3) + '° and is ' + fmt(f.fwhm, 4) + '° wide at half height. With the instrument\'s ' + p.binst + '° taken off, β = ' + fmt(f.beta, 4) + '° and L = ' + fmt(f.L, 1) + ' nm.');
      S.render(); return true;
    });
  }

  function result(rows) {
    var fines = rows.filter(function (r) { return r.kind === 'fine'; });
    var last = fines.length ? fines.reduce(function (a, b) { return b.step <= a.step ? b : a; }) : null;
    if (NANO) {
      if (!last) return null;
      return { label: 'Crystallite size (Scherrer)', value: last.L, unit: 'nm', digits: 1, truth: p.L * 1e9,
        note: 'From the (' + HKL + ') line at ' + fmt(last.peak, 2) + '°: L = 0.9 λ / (β cos θ) with β = √(β_m² − β_i²). This is the size of the coherent crystal domains, which can be smaller than the particle seen in a microscope. SIMULATED DATA.' };
    }
    var lines = rows.filter(function (r) { return r.kind === 'line'; });
    if (lines.length < 3 || !last) return null;
    var aa = S.fit.mean(lines.map(function (r) { return r.a; }));
    return { label: 'Lattice parameter a', value: aa, unit: 'Å', digits: 4, truth: p.a * 1e10,
      note: 'Lattice: ' + (st.lat || 'face-centred cubic') + '. From the first line\'s width, the Scherrer crystallite size is ' + fmt(last.L, 1) + ' nm (the lab\'s true size is ' + fmt(p.L * 1e9, 1) + ' nm). SIMULATED DATA.' };
  }

  var steps = [
    { id: 'load', title: 'Load the sample', view: 'dif', render: function (u) {
        u.h2('Load the powder');
        u.p('Open the enclosure, put the slide of ' + SAMPLE + ' in the holder with its surface level with the axis, and close the door: the shutter will not open with the door open.');
        u.task('Sample in the holder, door closed', st.loaded, st.loaded ? 'Loaded' : 'In its box').add(u.button('Load the slide', function () { S.focus('dif'); loadSample(); }, true, st.loaded || S.hand.busy));
        u.next('Next: the survey scan', st.loaded);
      },
      ok: function () { return st.loaded; }, auto: function () { return loadSample(); } },
    { id: 'survey', title: 'Survey scan', view: 'mon', render: function (u) {
        u.h2('Scan 2θ from ' + LO + '° to ' + HI + '°');
        u.p(NANO ? 'A quick scan shows where the lines are. The card names the line to measure: (' + HKL + '), near ' + fmt(LINE, 1) + '°.'
          : 'A quick scan in steps of ' + STEP + '° shows every line. Read their angles, then index them from the ratios of sin²θ.');
        u.button('Press SCAN', function () { S.focus('ctl'); runSurvey(); }, true, S.hand.busy || !st.loaded);
        if (!NANO) { u.button('Index the lines', function () { doIndex(); }, false, !st.peaks || st.indexed); u.table(); }
        u.next('Next: the slow scan', NANO ? !!st.survey : st.indexed);
      },
      ok: function () { return NANO ? !!st.survey : st.indexed; },
      auto: function () { return runSurvey().then(function () { if (!NANO) doIndex(); }); } },
    { id: 'fine', title: 'Line width', view: 'mon', render: function (u) {
        u.h2('Scan the line slowly and read its width');
        u.p('Scan the (' + (NANO ? HKL : '111') + ') line in small steps of 2θ and read its full width at half maximum. Take off the instrument\'s own width, ' + p.binst + '° (measured on a coarse-grained silicon standard): β² = β_m² − β_i².');
        u.slider('Step of the slow scan', 0.005, 0.05, 0.005, function () { return st.fstep; }, function (v) { st.fstep = Math.round(v * 1000) / 1000; }, '°', 3);
        u.button('Press SCAN', function () { runFine(); }, true, S.hand.busy || !st.survey);
        u.table();
        u.next('Next: the result', result(S.rows) !== null);
      },
      ok: function () { return result(S.rows) !== null; },
      auto: function () { st.fstep = 0.02; return runFine().then(function () { st.fstep = 0.005; return runFine(); }); } },
  ];

  return {
    camera: { pos: [0.1, 0.62, 0.85], look: [0.0, 0.12, -0.12] },
    views: { dif: [[-0.1, 0.36, 0.42], [-0.18, 0.17, -0.18]], mon: [[0.16, 0.3, 0.12], [0.32, 0.19, -0.22]],
      ctl: [[0.3, 0.3, 0.38], [0.3, 0.04, 0.1]], slide: [[0.12, 0.2, 0.32], [0.1, 0.01, 0.14]],
      bench: [[0.1, 0.62, 0.85], [0.0, 0.12, -0.12]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'X-rays reflect strongly from a set of lattice planes only at the Bragg angle. A powder shows a line for every allowed set of planes; the line positions give the lattice, and the line widths give the size of the crystallites.',
      formula: '2d sin θ = λ,   L = 0.9 λ / (β cos θ)',
      formulaNote: NANO ? 'β = √(β_m² − β_i²) in radians of 2θ; L is the crystallite size' : 'cubic: sin²θ = (λ²/4a²)(h² + k² + l²), so the sin²θ ratios name the lattice',
      more: ['Face-centred cubic keeps only unmixed h, k, l (N = 3, 4, 8, 11, 12, ...); diamond also loses h + k + l = 4n + 2 (3, 8, 11, 16, ...).',
        'Small crystallites broaden every line; strain broadens it too (that needs several lines and a Williamson-Hall plot, which this lab does not do).',
        'Line heights in this simulation come from a simple model; positions and widths are the physics.'],
      precautions: 'Never open the enclosure with the shutter open. Press the powder flat and level with the axis, or every line shifts.' },
    book: { title: 'Expt. — ' + S.lab.title,
      lines: ['Sample: ' + SAMPLE, 'Cu Kα1, λ = 1.5406 Å;  instrument width ' + p.binst + '°', NANO ? 'Line (' + HKL + ')' : 'Survey 20°–100°, then (111) slowly'],
      columns: [{ label: NANO ? 'step (°)' : '2θ (°)', get: function (r) { return r.kind === 'line' ? fmt(r.tth, 3) : String(r.step); } },
        { label: NANO ? 'FWHM (°)' : 'N / FWHM', get: function (r) { return r.kind === 'line' ? r.N + ' (' + r.hkl + ')' : fmt(r.fwhm, 4); } },
        { label: NANO ? 'β (°)' : 'a (Å) / β', get: function (r) { return r.kind === 'line' ? fmt(r.a, 4) : fmt(r.beta, 4); } },
        { label: 'L (nm)', get: function (r) { return r.kind === 'fine' ? fmt(r.L, 1) : ''; } }] },
    graph: NANO ? { x: function (r) { return r.step; }, y: function (r) { return r.L; }, xlabel: 'scan step (°)', ylabel: 'L (nm)', x0: 0 }
      : { x: function (r) { return r.kind === 'line' ? r.N : 0; }, y: function (r) { return r.kind === 'line' ? r.s2 : 0; }, xlabel: 'N = h² + k² + l²', ylabel: 'sin²θ', x0: 0, y0: 0,
        line: function (pts) { var q = pts.filter(function (a) { return a[0] > 0; }); if (q.length < 2) return null; var m = S.fit.origin(q); return function (x) { return m * x; }; } },
    result: result,
    tol: 0.02,
    resultNote: NANO ? 'The narrower the line, the bigger the crystals: below about 100 nm the broadening is easy to see, which is why X-ray diffraction is the everyday size check for nanopowders.'
      : 'The straight line of sin²θ against N through the origin has slope λ²/4a²: every line of the pattern gives the same lattice parameter.',
    chips: ['Why do some lines not appear?', 'Why take off the instrument width?', 'What is the Scherrer constant K?', 'Check my readings'],
    viva: [['The Scherrer equation gives', ['The crystallite size', 'The lattice parameter', 'The wavelength'], 0, 'L = Kλ/(β cos θ).'],
      ['In a face-centred cubic powder the first two lines have N =', ['3 and 4', '1 and 2', '2 and 4'], 0, 'Only unmixed h, k, l: (111) and (200).']],
    askState: function () {
      return { experiment: S.lab.title, sample: SAMPLE, loaded: st.loaded, detector_2theta_deg: st.arm,
        lines_found: st.peaks ? st.peaks.map(function (q) { return +q.tth.toFixed(3); }) : null, lattice: st.lat || null,
        slow_scan_step_deg: st.fstep, last_fwhm_deg: st.fine ? st.fine.fwhm : null, instrument_width_deg: p.binst };
    },
    steps: steps,
    tick: function () { hudA.set(fmt(st.arm, 2) + '°'); hudI.set(st.loaded ? fmt(I(st.arm), 0) : '—'); },
  };
});
