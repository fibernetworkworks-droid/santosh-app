/* Prayogshala studio module: UV-VISIBLE BENCH (B.Sc. nanomaterials).
   A double-beam UV-visible spectrophotometer with its sample compartment, a quartz cuvette of gold colloid, a
   matching blank of water, and the instrument screen that draws the spectrum as it scans.
   Physics: the `colloid` kernel of packs/modern_ug.js on the lab's own params - the same code the server checks.
   The size comes from Haiss et al. (2007), an empirical relation for spherical citrate-capped gold, and the lab
   says plainly what that method can and cannot do. */
HoolaStudio.define('uv-vis-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.colloid, assign = HK.assign;
  var p = HK.paramsFor('colloid', S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || 'Gold colloid in water, citrate-capped';
  var LAM0 = 400, LAM1 = 750, ALC = 0.001;
  var st = { blanked: false, loaded: false, lam: 450, scanned: false, scan: [], done: {} };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function absAt(nm) { return st.loaded ? KN.absorbance(nm, p) : 0; }
  function readA(nm) { return rnd(absAt(nm === undefined ? st.lam : nm), 3); }
  function peakNm() { return KN.peakNm(p); }
  function colloidColour() {                       // the colour the eye sees: what is left after the band absorbs
    var d = p.d;
    return d < 30 ? 0xb2353a : d < 55 ? 0xa33a52 : d < 80 ? 0x8d3a6b : 0x6d3f7a;
  }

  // ================================================================ the spectrophotometer
  var spec = new T.Group(); S.scene.add(spec); spec.position.set(-0.16, 0, -0.14); spec.rotation.y = 0.12;
  var SW = 0.46, SD = 0.3, SH = 0.15;
  var caseM = new T.MeshStandardMaterial({ color: 0xe6e2d8, roughness: 0.5, metalness: 0.1 });
  var cse = S.rounded(SW, SD, SH, 0.012, caseM); cse.rotation.x = -Math.PI / 2; cse.position.y = SH / 2 + 0.005;
  spec.add(cse);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.01, 0.011, 0.005, 16), M.rubber);
    ft.position.set(f[0] * (SW / 2 - 0.025), 0.0025, f[1] * (SD / 2 - 0.025)); spec.add(ft);
  });
  var FZ = SD / 2 + 0.0062, PW = SW - 0.016, PH = SH - 0.016;
  var faceTex = S.canvasTex(1400, Math.round(1400 * PH / PW), function (x, w, h) {
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 40px "Public Sans", sans-serif';
    x.fillText('UV – VISIBLE SPECTROPHOTOMETER', 34, 60);
    x.font = '500 24px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6';
    x.fillText('DOUBLE BEAM  ·  190 – 900 nm  ·  10 mm CELLS', 34, 96);
    x.font = '700 24px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8';
    x.fillText('BASELINE', w * 0.52, h * 0.78); x.fillText('SCAN', w * 0.68, h * 0.78);
  });
  var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004),
    [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: faceTex, roughness: 0.45 }), M.grey]);
  fac.position.set(0, 0.005 + SH / 2, FZ - 0.002); spec.add(fac);
  function sp(u, v, dz) { return new T.Vector3(u, 0.005 + SH / 2 + v, FZ + (dz || 0)); }
  var baseB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), M.grey); baseB.rotation.x = Math.PI / 2;
  baseB.position.copy(sp(0.018, -0.044, 0.004)); spec.add(baseB);
  var scanB = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), M.green); scanB.rotation.x = Math.PI / 2;
  scanB.position.copy(sp(0.082, -0.044, 0.004)); spec.add(scanB);
  // the sample compartment, with its lid
  var comp = S.mesh(new T.BoxGeometry(0.14, 0.012, 0.11), new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.7 }));
  comp.position.set(-0.1, SH + 0.006, 0.0); spec.add(comp);
  var lid = new T.Group(); spec.add(lid); lid.position.set(-0.1, SH + 0.012, -0.055);
  var lidP = S.mesh(new T.BoxGeometry(0.14, 0.006, 0.11), new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.6 }));
  lidP.position.z = 0.055; lid.add(lidP);
  var lidH = S.mesh(new T.BoxGeometry(0.04, 0.008, 0.01), M.bakelite); lidH.position.set(0, 0.006, 0.105); lid.add(lidH);
  // two cuvette holders
  function holder(dx) {
    var g = new T.Group(); spec.add(g); g.position.set(-0.1 + dx, SH + 0.012, 0);
    var blk = S.mesh(new T.BoxGeometry(0.018, 0.012, 0.018), new T.MeshStandardMaterial({ color: 0x15171a, roughness: 0.8 }));
    g.add(blk); return g;
  }
  var holdS = holder(-0.03), holdR = holder(0.03);
  function cuvette(colour, filled) {
    var g = new T.Group();
    var glassM = new T.MeshPhysicalMaterial({ color: 0xdfe6ea, roughness: 0.03, transmission: 0.85, thickness: 0.002,
      transparent: true, opacity: 0.4 });
    var wallsG = S.mesh(new T.BoxGeometry(0.012, 0.045, 0.012), glassM); wallsG.position.y = 0.0225; g.add(wallsG);
    var liq = S.mesh(new T.CylinderGeometry(0.0048, 0.0048, 0.03, 4),
      new T.MeshPhysicalMaterial({ color: colour, transmission: 0.45, roughness: 0.08, thickness: 0.01,
        transparent: true, opacity: 0.9 }));
    liq.rotation.y = Math.PI / 4; liq.position.y = 0.016; g.add(liq);
    liq.visible = !!filled;
    g.userData.liq = liq;
    return g;
  }
  var blankC = cuvette(0xdfe9f2, true); blankC.position.copy(wpt(holdR, 0, 0.006, 0)); S.scene.add(blankC);
  var sampC = cuvette(colloidColour(), true); S.scene.add(sampC);
  var BENCHPOS = new T.Vector3(0.18, 0.004, 0.18);
  sampC.position.copy(BENCHPOS);
  // the instrument screen: the spectrum is drawn here as it scans
  var scrTex = S.liveTex(760, 440);
  var scrG = new T.Group(); S.scene.add(scrG); scrG.position.set(0.28, 0, -0.2); scrG.rotation.y = -0.45;
  var scrBody = S.rounded(0.26, 0.03, 0.17, 0.008, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.6 }));
  scrBody.position.set(0, 0.095, 0); scrBody.rotation.x = -0.18; scrG.add(scrBody);
  var scrFace = new T.Mesh(new T.PlaneGeometry(0.24, 0.15), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false }));
  scrFace.position.set(0, 0.095, 0.017); scrFace.rotation.x = -0.18; scrG.add(scrFace);
  var scrStand = S.mesh(new T.CylinderGeometry(0.01, 0.03, 0.02, 20), M.iron); scrStand.position.y = 0.01;
  scrG.add(scrStand);
  var scrNeck = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.06, 16), M.iron); scrNeck.position.y = 0.04;
  scrG.add(scrNeck);
  // vials of colloid of other sizes, and a pipette
  var rack = new T.Group(); S.scene.add(rack); rack.position.set(0.34, 0, 0.16);
  var rackB = S.rounded(0.12, 0.06, 0.014, 0.004, M.wood); rackB.rotation.x = -Math.PI / 2; rackB.position.y = 0.007;
  rack.add(rackB);
  [0, 1, 2].forEach(function (i) {
    var v = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.045, 20),
      new T.MeshPhysicalMaterial({ color: [0xb2353a, 0x9c3a5e, 0x6d3f7a][i], transmission: 0.4, roughness: 0.1,
        thickness: 0.01, transparent: true, opacity: 0.9 }));
    v.position.set(-0.035 + i * 0.035, 0.034, 0); rack.add(v);
  });
  var pip = S.mesh(new T.CylinderGeometry(0.003, 0.0015, 0.12, 14), M.glass); pip.rotation.z = Math.PI / 2 - 0.2;
  pip.position.set(0.2, 0.006, 0.26); S.scene.add(pip);
  S.contact(0.54, 0.38, -0.16, -0.14, 0.55);
  S.contact(0.3, 0.22, 0.28, -0.2, 0.5);
  S.contact(0.16, 0.1, 0.34, 0.16, 0.45);

  function drawScreen() {
    scrTex.draw(function (x, w, h) {
      x.fillStyle = '#10151b'; x.fillRect(0, 0, w, h);
      var L = 70, R = w - 20, Tp = 28, Bt = h - 46;
      var amax = Math.max(0.6, KN.absorbance(peakNm(), p) * 1.25);
      var X = function (nm) { return L + (nm - LAM0) / (LAM1 - LAM0) * (R - L); };
      var Y = function (a) { return Bt - a / amax * (Bt - Tp); };
      x.strokeStyle = '#2b3340'; x.lineWidth = 1.5; x.fillStyle = '#7d8795';
      x.font = '18px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (var nm = LAM0; nm <= LAM1; nm += 50) {
        x.beginPath(); x.moveTo(X(nm), Tp); x.lineTo(X(nm), Bt); x.stroke();
        x.fillText(String(nm), X(nm), Bt + 24);
      }
      x.textAlign = 'right';
      for (var a = 0; a <= amax; a += amax / 4) {
        x.beginPath(); x.moveTo(L, Y(a)); x.lineTo(R, Y(a)); x.stroke();
        x.fillText(a.toFixed(2), L - 8, Y(a) + 6);
      }
      x.fillStyle = '#aeb6c0'; x.textAlign = 'left'; x.font = '600 20px "Public Sans", sans-serif';
      x.fillText('ABSORBANCE', 12, 20); x.textAlign = 'right';
      x.fillText('WAVELENGTH (nm)', R, h - 12);
      if (st.scan.length > 1) {
        x.strokeStyle = '#ffb648'; x.lineWidth = 3; x.beginPath();
        for (var i = 0; i < st.scan.length; i++) {
          var q = st.scan[i];
          if (i) x.lineTo(X(q[0]), Y(q[1])); else x.moveTo(X(q[0]), Y(q[1]));
        }
        x.stroke();
      }
      if (st.loaded) {
        x.strokeStyle = '#4ad1b5'; x.lineWidth = 1.5; x.setLineDash([5, 5]);
        x.beginPath(); x.moveTo(X(st.lam), Tp); x.lineTo(X(st.lam), Bt); x.stroke(); x.setLineDash([]);
        x.fillStyle = '#4ad1b5'; x.textAlign = 'left'; x.font = '600 22px "Public Sans", sans-serif';
        x.fillText(st.lam.toFixed(0) + ' nm   A = ' + readA().toFixed(3), L + 10, Tp + 24);
      } else {
        x.fillStyle = '#7d8795'; x.textAlign = 'center'; x.font = '600 22px "Public Sans", sans-serif';
        x.fillText('load the sample cell', (L + R) / 2, (Tp + Bt) / 2);
      }
    });
  }
  drawScreen();

  S.addApparatus('spec', spec, 'UV-visible spectrophotometer', 'A double-beam instrument: the blank sits in the reference beam and the sample in the other, so the glass and the water are taken out of the answer.');
  S.addApparatus('samp', sampC, SAMPLE, 'A 10 mm quartz cuvette of gold colloid. Its red colour IS the plasmon band: the green light is absorbed, so what comes through looks red.');
  S.addApparatus('blank', blankC, 'Blank cuvette (water)', 'A matching cuvette of the same water, used to set the baseline before the sample is scanned.');
  S.addApparatus('screen', scrG, 'Instrument screen', 'Draws the absorbance against wavelength as the instrument scans, and reads the absorbance at any wavelength you choose.');
  S.addApparatus('rack', rack, 'Vials of colloid', 'Colloids made with different amounts of citrate, which set the particle size. Their colour changes with size, from red to purple.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Wavelength'), hudA = S.hudCard('Absorbance'), hudP = S.hudCard('Plasmon peak');

  // ================================================================ human actions
  function baseline() {
    if (busy()) return Promise.resolve();
    return S.hand.tap(baseB, 'front').then(function () {
      st.blanked = true; S.click(900, 0.05);
      S.say('Baseline taken with water in both beams: the glass, the water and the lamp\'s own shape are now zeroed out.');
      S.render();
    });
  }
  function loadSample() {
    if (busy()) return Promise.resolve();
    if (st.loaded) return Promise.resolve();
    if (!st.blanked) { S.say('Take the baseline with the blank first.'); return Promise.resolve(); }
    var from = sampC.position.clone(), to = wpt(holdS, 0, 0.006, 0);
    return S.hand.pinchMove(from, function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k,
        from.z + (to.z - from.z) * k);
    }, function (k) {
      sampC.position.set(from.x + (to.x - from.x) * k,
        from.y + 0.06 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, { mode: 'side', ms: 1000, reachMs: 700 }).then(function () {
      sampC.position.copy(to); st.loaded = true;
      S.say('Colloid in the sample beam, clear faces towards the light, lid closed. Fingerprints on the clear faces would show up as absorbance.');
      S.render();
    });
  }
  function scan() {
    if (busy()) return Promise.resolve(false);
    if (!st.loaded) { S.say('Load the sample cell first.'); return Promise.resolve(false); }
    st.scan = [];
    return S.hand.tap(scanB, 'front').then(function () {
      return S.tween(1800, function (k) {
        var upto = LAM0 + (LAM1 - LAM0) * k;
        st.scan = [];
        for (var nm = LAM0; nm <= upto; nm += 2) st.scan.push([nm, absAt(nm)]);
        st.lam = Math.round(upto); drawScreen();
      });
    }).then(function () {
      st.scan = [];
      for (var nm = LAM0; nm <= LAM1; nm += 2) st.scan.push([nm, absAt(nm)]);
      st.scanned = true; st.lam = Math.round(peakNm()); drawScreen();
      S.say('Scan finished. One broad band with its maximum near ' + peakNm().toFixed(0) + ' nm: that is the surface plasmon resonance of the gold spheres.');
      S.render(); return true;
    });
  }
  function goTo(nm) {
    if (!isFinite(nm) || nm < LAM0 || nm > LAM1) { S.say('The scan runs from ' + LAM0 + ' to ' + LAM1 + ' nm.'); return false; }
    st.lam = Math.round(nm); drawScreen(); return true;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.loaded) { S.say('Load the sample cell first.'); return false; }
    if (!st.scanned) { S.say('Run the scan first, so you can see where the band is.'); return false; }
    if (st.done[st.lam]) { S.say('You already have a reading at ' + st.lam + ' nm.'); return false; }
    st.done[st.lam] = true;
    S.addRow({ nm: st.lam, A: readA() });
    S.say('Written in your record book: ' + st.lam + ' nm, absorbance ' + readA().toFixed(3) + '.');
    return true;
  }

  function result(rows) {
    if (rows.length < 6) return null;
    var a450 = null, best = null, i;
    for (i = 0; i < rows.length; i++) {
      if (Math.abs(rows[i].nm - 450) <= 2) a450 = rows[i].A;
      if (!best || rows[i].A > best.A) best = rows[i];
    }
    if (a450 === null || !best || !(a450 > 0)) return null;
    var d = Math.exp(3.00 * (best.A / a450) - 2.20);
    return { label: 'Particle diameter', value: d, unit: 'nm', digits: 1, truth: p.d,
      note: 'From A(peak)/A(450) = ' + (best.A / a450).toFixed(3) + ' in Haiss\'s relation d = exp(3.00 r − 2.20). The peak itself, at ' + best.nm + ' nm, gives a size of about ' + (Math.log((best.nm - 512) / 6.53) / 0.0216).toFixed(0) + ' nm by the other relation - a useful cross-check.' };
  }

  return {
    camera: { pos: [0.0, 0.94, 1.14], look: [-0.02, 0.08, -0.06] },
    views: { spec: [[-0.1, 0.56, 0.52], [-0.16, 0.08, -0.1]], samp: [[-0.12, 0.34, 0.22], [-0.14, 0.14, -0.13]],
      blank: [[-0.06, 0.32, 0.2], [-0.1, 0.14, -0.13]], screen: [[0.3, 0.34, 0.16], [0.28, 0.1, -0.2]],
      rack: [[0.34, 0.24, 0.34], [0.34, 0.03, 0.16]],
      bench: [[0.0, 0.94, 1.14], [-0.02, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'The free electrons of a gold sphere much smaller than the wavelength of light can be driven back and forth by the light\'s own field, and at one frequency they resonate. That surface plasmon resonance absorbs green light, which is why a gold colloid looks red, and both the position of the band and its height above the 450 nm absorbance grow with the size of the spheres.',
      formula: 'λ_spr = 512 + 6.53 e^(0.0216 d),   d = e^(3.00 A_spr/A₄₅₀ − 2.20)',
      formulaNote: 'd in nanometres; both relations are Haiss et al., Anal. Chem. 79 (2007) 4215',
      more: ['The ratio of the two absorbances is used rather than one of them, because both grow with how much colloid is in the cuvette and their ratio does not.',
        'Said plainly: this is an empirical relation fitted to spherical citrate-capped gold between about 5 and 100 nm. It gives one average size, says nothing about the spread, and must not be used for silver, for rods or for coated particles. An electron microscope is what settles a size argument.',
        'The baseline with water in both beams takes the cuvette, the solvent and the lamp\'s own spectrum out of the measurement.'],
      precautions: 'Handle the cuvette by its frosted faces only. Wipe the clear faces with lens tissue. Keep the lid closed while the lamp is on, and never pipette by mouth.' },
    book: { title: 'Expt. — Gold nanoparticles by UV-visible spectrophotometry',
      lines: ['Aim: plasmon peak and particle size of a gold colloid.', 'Sample: ' + SAMPLE,
        '10 mm quartz cells, water as the blank.', 'Baseline taken with water in both beams.',
        'd = exp(3.00 A_spr/A₄₅₀ − 2.20)  (Haiss 2007)', 'λ_spr = 512 + 6.53 exp(0.0216 d)'],
      columns: [{ label: 'λ (nm)', get: function (r) { return r.nm; } },
        { label: 'Absorbance', get: function (r) { return r.A.toFixed(3); } },
        { label: 'A / A₄₅₀', get: function (r) {
          var a450 = null, i; for (i = 0; i < S.rows.length; i++) if (Math.abs(S.rows[i].nm - 450) <= 2) a450 = S.rows[i].A;
          return a450 ? (r.A / a450).toFixed(3) : ''; } }] },
    graph: { x: function (r) { return r.nm; }, y: function (r) { return r.A; }, xlabel: 'λ (nm)',
      ylabel: 'absorbance', y0: 0,
      line: function (pts) {
        var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; });
        return function (x) {
          if (x <= q[0][0]) return q[0][1];
          for (var i = 0; i < q.length - 1; i++) {
            if (x <= q[i + 1][0]) { var a = q[i], b = q[i + 1];
              return b[0] === a[0] ? b[1] : a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]); }
          }
          return q[q.length - 1][1];
        };
      } },
    result: result,
    tol: 0.05,
    resultNote: 'One broad band in the green, and its height against the 450 nm absorbance, give an average diameter in a minute - which is why UV-visible spectrophotometry is the first thing done to a new colloid. It is a quick, honest estimate, not a microscope.',
    chips: ['Why does a gold colloid look red?', 'Why use the ratio of two absorbances?',
      'What can this method NOT tell us?', 'Check my readings', 'What sets the particle size?'],
    viva: [['A gold colloid looks red because', ['Its plasmon band absorbs green light', 'Gold is red', 'The cuvette is tinted'], 0,
      'What is left after the green is absorbed looks red.'],
      ['The ratio A_spr/A₄₅₀ is used because', ['It does not depend on the concentration', 'A₄₅₀ is the peak', 'It is easier to read'], 0,
        'Both absorbances scale with concentration; their ratio does not.'],
      ['This method gives', ['An average size only', 'The size of every particle', 'The shape of the particles'], 0,
        'It is an empirical relation for spheres, and says nothing about the spread or the shape.']],
    askState: function () {
      return { experiment: 'UV-visible spectrum of a gold colloid: plasmon peak and particle size',
        sample: SAMPLE, baseline_taken: st.blanked, sample_loaded: st.loaded, scanned: st.scanned,
        wavelength_nm: st.lam, absorbance: readA(), plasmon_peak_nm: +peakNm().toFixed(1),
        readings_taken: S.rows.length };
    },

    steps: [
      { id: 'blank', title: 'Baseline', view: 'spec', render: function (u) {
          u.h2('Take the baseline, then load the colloid');
          u.p('Water goes in both beams first and the instrument is told to remember what it sees: that takes the cuvette, the water and the lamp\'s own spectrum out of every later reading.');
          u.task('1. Baseline with water in both beams', st.blanked, st.blanked ? 'Baseline stored' : 'Press BASELINE')
            .add(u.button(st.blanked ? 'Baseline taken' : 'Take the baseline', function () { S.focus('spec'); baseline(); }, !st.blanked, st.blanked || S.hand.busy));
          u.task('2. Colloid into the sample beam', st.loaded, st.loaded ? 'Cuvette in the sample holder' : 'On the bench')
            .add(u.button(st.loaded ? 'Loaded' : 'Load the cuvette', function () { S.focus('samp'); loadSample(); }, !st.loaded, st.loaded || S.hand.busy));
          u.live(function () { return st.loaded ? 'Absorbance at ' + st.lam + ' nm: ' + readA().toFixed(3) : 'Sample beam empty'; });
          u.note('Hold the cuvette by its frosted faces. A fingerprint on a clear face reads as absorbance.');
          u.next('Next: scan the spectrum', st.blanked && st.loaded);
        },
        ok: function () { return st.blanked && st.loaded; },
        auto: function () { return baseline().then(function () { return loadSample(); }); } },

      { id: 'scan', title: 'Scan and read', view: 'screen', render: function (u) {
          u.h2('Scan from ' + LAM0 + ' to ' + LAM1 + ' nm, then read the band');
          u.p('Run the scan and watch the band appear. Then read the absorbance at 450 nm and at the peak, and at a few wavelengths on either side so that the shape of the band is in your table too.');
          u.row(u.button(st.scanned ? 'Scan again' : 'Run the scan', function () { scan(); }, !st.scanned, S.hand.busy),
            u.button('Go to the peak', function () { goTo(peakNm()); }, false, !st.scanned),
            u.button('Go to 450 nm', function () { goTo(450); }, false, !st.scanned));
          var tg = { v: st.lam };
          u.slider('Read the absorbance at', LAM0, LAM1, 5, function () { return tg.v; },
            function (v) { tg.v = v; goTo(v); }, 'nm', 0);
          u.row(u.button('Record λ and A', function () { record(); }, true, S.hand.busy));
          u.live(function () { return st.lam + ' nm  ·  A = ' + readA().toFixed(3)
            + (st.scanned ? '  ·  peak at ' + peakNm().toFixed(0) + ' nm' : ''); });
          u.h3('Observation table'); u.table();
          var has450 = S.rows.some(function (r) { return Math.abs(r.nm - 450) <= 2; });
          if (!has450) u.note('The reading at 450 nm is the one the size relation needs: do not leave it out.');
          if (S.rows.length < 6) u.p(S.rows.length + ' of at least 6 wavelengths recorded.');
          u.next('Next: the particle size', S.rows.length >= 6 && has450);
        },
        ok: function () { return S.rows.length >= 6 && S.rows.some(function (r) { return Math.abs(r.nm - 450) <= 2; }); },
        auto: function () {
          return scan().then(function () {
            var pk = Math.round(peakNm());
            var list = [450, pk - 40, pk - 20, pk, pk + 20, pk + 40, pk + 80, 700];
            list.forEach(function (nm) { if (goTo(nm)) record(); });
          });
        } },
    ],

    tick: function () {
      hudL.set(st.lam + ' nm');
      hudA.set(st.loaded ? readA().toFixed(3) : '—');
      hudP.set(st.scanned ? peakNm().toFixed(0) + ' nm' : '—');
    },
  };
});
