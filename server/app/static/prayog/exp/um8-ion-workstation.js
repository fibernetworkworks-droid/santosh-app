/* Prayogshala studio RIG: the STOPPING-POWER WORKSTATION of wave 8 (B.Sc. radiation physics, the syllabus's SRIM / TRIM
   exercises done with the Bethe-Bloch formula). Desk, monitor, keyboard with a live Enter key, tower and a printed card.
   One rig serves four set-ups by the lab's `mode`:
     0  um8-ion-energy-loss   S(E) of protons from 1 MeV to 50 GeV and its minimum (minimum ionising)
     1  um8-ion-proton-range  the CSDA range R = integral dE / S(E), converged in the number of energy steps
     2  um8-ion-projectile-z  S for ions z = 1 to 92 at one speed; the effective charge sqrt(S / S_proton)
     3  um8-ion-bragg         the ion marched through the target in depth steps: the Bragg curve and the stopping depth
   Every number comes from the um8_ion kernel (packs/ug_matter_w8.js) - the same code the server checks. The program is
   NOT SRIM: no nuclear stopping, no shell / density corrections, no Monte Carlo; the card says so. */
HoolaStudio.define('um8-ion-workstation', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.um8_ion, assign = HK.assign;
  var p = HK.paramsFor('um8_ion', S.lab.params);
  var MODE = Math.round(p.mode);
  var V_ = S.lab.variant || {};
  var MED = V_.sample || ['Liquid water', 'Graphite (carbon)', 'Mylar (polyethylene terephthalate)', 'Gold'][MODE];
  var IONS = [[1, 'H', 1.007276], [2, 'He', 4.0026], [3, 'Li', 6.94], [6, 'C', 12.011], [8, 'O', 15.999], [10, 'Ne', 20.180],
    [18, 'Ar', 39.95], [36, 'Kr', 83.798], [54, 'Xe', 131.29], [79, 'Au', 196.97], [92, 'U', 238.03]];
  var ION = ({ 1: 'proton', 2: 'helium', 8: 'oxygen', 18: 'argon', 36: 'krypton', 54: 'xenon', 92: 'uranium' })[Math.round(p.z)] || ('z = ' + p.z);
  var st = { on: false, n: MODE === 3 ? 20 : MODE === 1 ? 5 : 2, ion: 0, last: null, runs: 0, curve: null };

  function fmt(v, d) { if (!isFinite(v)) return '—'; return v.toFixed(d); }
  function sci(v) { if (!isFinite(v)) return '—'; var a = Math.abs(v); return (a >= 0.01 && a < 1e5) ? v.toPrecision(5) : v.toExponential(3); }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }

  // ================================================================ the desk
  var desk = new T.Group(); S.scene.add(desk);
  var mat = S.rounded(0.9, 0.45, 0.004, 0.01, new T.MeshStandardMaterial({ color: 0x1d1f24, roughness: 0.9 }));
  mat.rotation.x = -Math.PI / 2; mat.position.set(0.05, 0.002, -0.12); desk.add(mat);
  var mon = new T.Group(); S.scene.add(mon); mon.position.set(0.08, 0, -0.42);
  var foot = S.rounded(0.22, 0.14, 0.012, 0.01, M.grey); foot.rotation.x = -Math.PI / 2; foot.position.y = 0.008; mon.add(foot);
  var neck = S.mesh(new T.CylinderGeometry(0.016, 0.02, 0.11, 20), M.grey); neck.position.y = 0.065; mon.add(neck);
  var bez = S.rounded(0.42, 0.27, 0.016, 0.01, new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.4 }));
  bez.position.set(0, 0.245, 0.02); mon.add(bez);
  var scrTex = S.liveTex(1280, 780);
  var scr = new T.Mesh(new T.PlaneGeometry(0.39, 0.238), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false }));
  scr.position.set(0, 0.245, 0.0285); mon.add(scr);
  var logo = S.label('HOOLA', { w: 0.03, ratio: 0.25, color: '#9aa0a8' }); logo.position.set(0, 0.118, 0.0285); mon.add(logo);
  S.contact(0.3, 0.2, 0.08, -0.42, 0.5);
  var kbd = new T.Group(); S.scene.add(kbd); kbd.position.set(0.08, 0, -0.1);
  var kb = S.rounded(0.34, 0.12, 0.014, 0.006, new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.6 }));
  kb.rotation.x = -Math.PI / 2; kb.position.y = 0.007; kbd.add(kb);
  var keyM = new T.MeshStandardMaterial({ color: 0x2c2d31, roughness: 0.55 });
  for (var r = 0; r < 4; r++) for (var c = 0; c < 13; c++) {
    if (r === 1 && c >= 11) continue;
    var k = S.mesh(new T.BoxGeometry(0.0205, 0.006, 0.0205), keyM); k.position.set(-0.145 + c * 0.0225, 0.016, -0.04 + r * 0.025); kbd.add(k);
  }
  var enter = S.mesh(new T.BoxGeometry(0.044, 0.007, 0.046), new T.MeshStandardMaterial({ color: 0x3f6fd8, roughness: 0.5 }));
  enter.position.set(0.1375, 0.0165, -0.0275); kbd.add(enter);
  var eLbl = S.label('Enter', { w: 0.026, ratio: 0.35, color: '#ffffff' }); eLbl.rotation.x = -Math.PI / 2; eLbl.position.set(0.1375, 0.0205, -0.0275); kbd.add(eLbl);
  var mouse = S.rounded(0.058, 0.095, 0.022, 0.02, new T.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.5 }));
  mouse.rotation.x = -Math.PI / 2; mouse.position.set(0.31, 0.011, -0.1); S.scene.add(mouse);
  S.contact(0.36, 0.14, 0.08, -0.1, 0.5);
  var tower = new T.Group(); S.scene.add(tower); tower.position.set(-0.56, 0, -0.45);
  var tw = S.rounded(0.17, 0.36, 0.34, 0.01, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5, metalness: 0.3 }));
  tw.position.y = 0.17; tower.add(tw);
  var pwr = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.004, 20), M.chrome); pwr.rotation.x = Math.PI / 2; pwr.position.set(0, 0.29, 0.182); tower.add(pwr);
  var led = S.mesh(new T.SphereGeometry(0.003, 10, 8), new T.MeshBasicMaterial({ color: 0x333333 })); led.position.set(0.03, 0.29, 0.182); tower.add(led);
  S.contact(0.2, 0.38, -0.56, -0.45, 0.5);
  // the printed method card
  var CARD = ['Bethe-Bloch: −dE/dx = K z² (Z/A)(1/β²)[½ ln(2mc²β²γ²Tmax/I²) − β²]', 'K = 0.307075 MeV cm²/mol,  mc² = 0.51099895 MeV',
    'Medium: ' + MED, 'Z/A = ' + p.ZA + ' mol/g,  I = ' + p.I + ' eV,  ρ = ' + p.rho + ' g/cm³',
    MODE === 0 ? 'Task: S(E) of protons, 1 MeV - 50 GeV; find the minimum' : MODE === 1 ? 'Task: CSDA range of ' + p.E + ' MeV protons, R = ∫dE/S'
      : MODE === 2 ? 'Task: S of ions z = 1 - 92 at ' + p.E + ' MeV/u; z_eff = √(S/S_p)' : 'Task: ' + ION + ' at ' + p.E + ' MeV/u, depth steps: Bragg curve',
    'Effective charge (Barkas): z_eff = z(1 − e^(−125 β z^(−2/3)))', 'NOT SRIM: no nuclear stopping, no shell or density corrections.'];
  var cardTex = S.canvasTex(620, 820, function (x, w, h) {
    x.fillStyle = '#fbfaf5'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b2a4a'; x.font = '700 34px "Public Sans", sans-serif';
    x.fillText('STOPPING POWER', 30, 60); x.font = '500 22px "Public Sans", sans-serif'; x.fillStyle = '#2b2f36';
    var y = 110; CARD.forEach(function (ln) {
      var words = ln.split(' '), line = '';
      words.forEach(function (wd) { if (x.measureText(line + wd).width > w - 60) { x.fillText(line, 30, y); y += 30; line = ''; } line += wd + ' '; });
      x.fillText(line, 30, y); y += 46; });
  });
  var card = new T.Mesh(new T.PlaneGeometry(0.15, 0.2), new T.MeshStandardMaterial({ map: cardTex, roughness: 0.8 }));
  card.rotation.x = -Math.PI / 2; card.rotation.z = -0.12; card.position.set(0.48, 0.0045, -0.05); S.scene.add(card);

  S.addApparatus('mon', mon, 'Monitor', 'The program draws its curve here and prints every run.');
  S.addApparatus('kbd', kbd, 'Keyboard', 'Enter runs the program at the settings you chose.');
  S.addApparatus('tower', tower, 'Workstation', 'The computer running the stopping-power program.');
  S.addApparatus('card', card, 'Method card', 'The formula, the medium\'s constants and the task. ' + CARD[6]);
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every run is written here.');
  var hud1 = S.hudCard(MODE === 0 ? 'Points per decade' : MODE === 2 ? 'Ion' : 'Steps'), hud2 = S.hudCard('Last run');

  // ================================================================ the computations (all from the kernel)
  function sOf(E, z, Mu) { return KN.S(E, assign(p, { z: z, Mu: Mu })); }
  function runCurve() {                       // mode 0: S on a grid of ppd points per decade, 1 MeV .. 50 GeV
    var ppd = st.n, pts = [], i, E, nmax = Math.floor(Math.log(5e4) / Math.LN10 * ppd + 1e-9);
    for (i = 0; i <= nmax; i++) { E = Math.pow(10, i / ppd); pts.push([E, KN.S(E, p)]); }
    var mi = 0; for (i = 1; i < pts.length; i++) if (pts[i][1] < pts[mi][1]) mi = i;
    return { pts: pts, Smin: pts[mi][1], Emin: pts[mi][0] };
  }
  function runRange() { return { R: KN.rangeN(p, st.n) }; }
  function runIon() { var io = IONS[st.ion]; return { z: io[0], sym: io[1], Mu: io[2], S: sOf(p.E, io[0], io[2]) }; }
  function runBragg() {
    var pts = KN.bragg(p, st.n), depth = KN.stopDepth(p, st.n), mi = 0, i;
    for (i = 1; i < pts.length; i++) if (pts[i][1] > pts[mi][1]) mi = i;
    return { pts: pts, depth: depth, peak: pts.length ? pts[mi][0] : 0 };
  }
  function um(g) { return g / p.rho * 1e4; }

  // ================================================================ the screen
  function drawScreen() {
    scrTex.draw(function (x) {
      var W = 1280, H = 780;
      x.fillStyle = '#0d1b2a'; x.fillRect(0, 0, W, H);
      if (!st.on) { x.fillStyle = '#05070a'; x.fillRect(0, 0, W, H); return; }
      x.fillStyle = '#e8eef7'; x.font = '600 34px "JetBrains Mono", monospace';
      x.fillText(['stopping.py  S(E) of protons', 'range.py  CSDA range', 'zscan.py  S against projectile z', 'bragg.py  Bragg curve'][MODE] + '  -  ' + MED.split(' (')[0], 30, 50);
      var px = 30, py = 80, pw = 800, ph = 640;
      x.strokeStyle = '#3b5274'; x.lineWidth = 2; x.strokeRect(px, py, pw, ph);
      var pts = [];
      if (MODE === 0 && st.curve) pts = st.curve.pts.map(function (q) { return [Math.log(q[0]) / Math.LN10, Math.log(q[1]) / Math.LN10]; });
      if (MODE === 3 && st.curve) pts = st.curve.pts.map(function (q) { return [um(q[0]), q[1] * p.rho / 1e4]; });
      if (MODE === 2) pts = S.rows.map(function (r) { return [Math.log(r.z) / Math.LN10, Math.log(r.S) / Math.LN10]; });
      if (MODE === 1) pts = S.rows.map(function (r) { return [Math.log(r.n) / Math.LN10, r.R]; });
      if (pts.length) {
        var xs = pts.map(function (q) { return q[0]; }), ys = pts.map(function (q) { return q[1]; });
        var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
        if (MODE === 3) { y0 = 0; x0 = 0; }
        if (x1 - x0 < 1e-9) { x0 -= 1; x1 += 1; }
        if (y1 - y0 < 1e-12) { y0 -= Math.abs(y0) * 0.01 + 1e-6; y1 += Math.abs(y1) * 0.01 + 1e-6; }
        var X = function (v) { return px + 40 + (v - x0) / (x1 - x0) * (pw - 80); }, Y = function (v) { return py + ph - 40 - (v - y0) / (y1 - y0) * (ph - 80); };
        x.strokeStyle = '#7fb2ff'; x.lineWidth = 4; x.beginPath();
        pts.forEach(function (q, i) { if (i) x.lineTo(X(q[0]), Y(q[1])); else x.moveTo(X(q[0]), Y(q[1])); }); x.stroke();
        x.fillStyle = '#ffd36b'; pts.forEach(function (q) { x.beginPath(); x.arc(X(q[0]), Y(q[1]), 6, 0, Math.PI * 2); x.fill(); });
        x.fillStyle = '#9fb3cc'; x.font = '500 24px "JetBrains Mono", monospace';
        x.fillText(['log10 E (MeV)', 'log10 n (steps)', 'log10 z', 'depth (µm)'][MODE], px + pw - 260, py + ph - 8);
        x.fillText(['log10 S (MeV cm²/g)', 'R (g/cm²)', 'log10 S', 'dE/dx (MeV/µm)'][MODE], px + 10, py + 28);
      } else { x.fillStyle = '#6f86a6'; x.font = '500 28px "JetBrains Mono", monospace'; x.fillText('No run yet: choose the setting and press Enter.', px + 30, py + 60); }
      x.fillStyle = '#e8eef7'; x.font = '600 26px "JetBrains Mono", monospace'; x.fillText('RUN LOG', 870, 110);
      x.font = '500 22px "JetBrains Mono", monospace'; x.fillStyle = '#b7c6dc';
      S.rows.slice(-14).forEach(function (r, i) {
        var t = MODE === 0 ? 'ppd ' + r.ppd + ': Smin ' + fmt(r.Smin, 4) + ' @ ' + fmt(r.Emin, 0) + ' MeV'
          : MODE === 1 ? 'n ' + r.n + ':  R ' + fmt(r.R, 5) + ' g/cm²'
            : MODE === 2 ? r.sym + ' z=' + r.z + ':  S ' + sci(r.S) + '  zeff ' + fmt(r.ze, 2)
              : 'n ' + r.n + ':  stops ' + fmt(r.depth, 2) + ' µm';
        x.fillText(t, 870, 150 + i * 40);
      });
    });
  }
  drawScreen();

  // ================================================================ actions
  function powerOn() {
    if (busy() || st.on) return Promise.resolve();
    return S.hand.tap(pwr, 'front').then(function () {
      st.on = true; led.material.color.setHex(0x37d67a); drawScreen();
      S.say('The workstation is on and the program is loaded with the medium on the card.'); S.render();
    });
  }
  function setN(v) {
    var lim = MODE === 0 ? [1, 20] : MODE === 1 ? [2, 1000] : [10, 1000];
    if (!isFinite(v) || v < lim[0] || v > lim[1]) { S.say('Choose a setting from ' + lim[0] + ' to ' + lim[1] + '.'); return false; }
    st.n = Math.round(v); return true;
  }
  function run() {
    if (busy()) return Promise.resolve(false);
    if (!st.on) { S.say('Switch the workstation on first.'); return Promise.resolve(false); }
    return S.hand.tap(enter, 'top').then(function () {
      var row;
      if (MODE === 0) {
        if (S.rows.some(function (r) { return r.ppd === st.n; })) { S.say('You already ran ' + st.n + ' points per decade. Change it.'); return false; }
        st.curve = runCurve(); row = { ppd: st.n, npts: st.curve.pts.length, Smin: st.curve.Smin, Emin: st.curve.Emin };
        S.say('S computed at ' + row.npts + ' energies. The smallest is ' + fmt(row.Smin, 4) + ' MeV cm²/g at ' + fmt(row.Emin, 0) + ' MeV.');
      } else if (MODE === 1) {
        if (S.rows.some(function (r) { return r.n === st.n; })) { S.say('You already ran ' + st.n + ' steps. Change it.'); return false; }
        var rr = runRange(); row = { n: st.n, R: rr.R, Rcm: rr.R / p.rho };
        S.say('With ' + st.n + ' energy steps the range is ' + fmt(rr.R, 5) + ' g/cm², that is ' + fmt(rr.R / p.rho, 4) + ' cm.');
      } else if (MODE === 2) {
        var io = runIon();
        if (S.rows.some(function (r) { return r.z === io.z; })) { S.say(io.sym + ' is already in the log. Choose another ion.'); return false; }
        var sp = sOf(p.E, 1, IONS[0][2]);
        row = { z: io.z, sym: io.sym, S: io.S, ratio: io.S / sp, ze: Math.sqrt(io.S / sp) };
        S.say(io.sym + ' at ' + p.E + ' MeV per nucleon: S = ' + sci(io.S) + ' MeV cm²/g, ' + fmt(row.ratio, 1) + ' times the proton\'s: z_eff = ' + fmt(row.ze, 2) + '.');
      } else {
        if (S.rows.some(function (r) { return r.n === st.n; })) { S.say('You already ran ' + st.n + ' steps. Change it.'); return false; }
        st.curve = runBragg(); row = { n: st.n, depth: um(st.curve.depth), peak: um(st.curve.peak) };
        S.say('With ' + st.n + ' depth steps the ' + ION + ' ions stop at ' + fmt(row.depth, 2) + ' µm; the Bragg peak is at ' + fmt(row.peak, 2) + ' µm.');
      }
      S.addRow(row); st.runs += 1; st.last = row; drawScreen(); S.render(); return true;
    });
  }

  function result(rows) {
    if (MODE === 0) {
      if (rows.length < 3) return null;
      var best = rows.reduce(function (a, b) { return b.ppd > a.ppd ? b : a; });
      var sm = KN.sMin(p);
      return { label: 'Minimum mass stopping power (minimum ionising)', value: best.Smin, unit: 'MeV cm²/g', digits: 4, truth: sm[1],
        note: 'At ' + fmt(best.Emin, 0) + ' MeV on your finest grid; the formula\'s own minimum is at ' + fmt(sm[0], 0) + ' MeV. The PDG quotes about 1.99 MeV cm²/g for water with the density effect included, which this program leaves out.' };
    }
    if (MODE === 1) {
      if (rows.length < 4) return null;
      var b1 = rows.reduce(function (a, b) { return b.n > a.n ? b : a; });
      return { label: 'CSDA range of ' + p.E + ' MeV protons', value: b1.R, unit: 'g/cm²', digits: 4, truth: KN.rangeN(p, p.nref),
        note: 'That is ' + fmt(b1.R / p.rho, 3) + ' cm of ' + MED.split(' (')[0].toLowerCase() + '. The midpoint sum settles as the steps shrink; the uncorrected Bethe formula is good to a few per cent at these energies.' };
    }
    if (MODE === 2) {
      var u = rows.filter(function (r) { return r.z === 92; })[0], hp = rows.filter(function (r) { return r.z === 1; })[0];
      if (!u || !hp || rows.length < 5) return null;
      return { label: 'Effective charge of uranium at ' + p.E + ' MeV/u', value: u.ze, unit: '', digits: 2,
        truth: KN.zeff(92, KN.kin(p.E, 238.03)[1]), note: 'S(U) is ' + fmt(u.ratio, 0) + ' times S(p), not 92² = 8464 times: the ion carries some of its electrons.' };
    }
    if (rows.length < 3) return null;
    var b3 = rows.reduce(function (a, b) { return b.n > a.n ? b : a; });
    return { label: 'Stopping depth of ' + ION + ' ions', value: b3.depth, unit: 'µm', digits: 2, truth: um(KN.rangeN(p, p.nref)),
      note: 'The Bragg peak lies at ' + fmt(b3.peak, 2) + ' µm, just before the end. Below 0.5 MeV per nucleon the march stops: the uncorrected formula is not valid there.' };
  }

  var LIST = MODE === 0 ? [2, 5, 10] : MODE === 1 ? [5, 10, 20, 50, 200] : MODE === 3 ? [20, 50, 100, 400] : null;
  var ZLIST = [0, 1, 3, 4, 6, 7, 8, 10];
  return {
    camera: { pos: [0.45, 0.42, 0.78], look: [0.08, 0.17, -0.3] },
    views: { mon: [[0.12, 0.32, 0.12], [0.08, 0.24, -0.42]], kbd: [[0.12, 0.25, 0.2], [0.08, 0.02, -0.1]],
      tower: [[-0.05, 0.5, 0.55], [-0.4, 0.17, -0.42]], card: [[0.5, 0.3, 0.15], [0.48, 0.0, -0.05]],
      bench: [[0.45, 0.42, 0.78], [0.08, 0.17, -0.3]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A fast ion loses energy mainly by knocking electrons of the medium. The Bethe-Bloch formula gives the loss per unit mass thickness from the ion\'s charge and speed and two numbers of the medium: its electrons per gram (Z/A) and its mean excitation energy I.',
      formula: '−dE/dx = K z² (Z/A) (1/β²) [½ ln(2mₑc²β²γ²T_max / I²) − β²]',
      formulaNote: 'K = 0.307075 MeV cm²/mol; at the same speed every ion loses z_eff² times a proton\'s loss',
      more: ['The loss falls as 1/β² while the ion is slow, has a broad minimum near βγ ≈ 3, and then rises slowly.',
        'The range is the integral R = ∫ dE / S(E): the program adds it up in steps, and the steps must be made small enough that the answer stops changing.',
        'SRIM, the program the syllabus names, adds shell and density-effect corrections, nuclear stopping and fitted data, and runs a Monte Carlo of the path (TRIM). This program is the bare Bethe-Bloch formula and says so.'],
      precautions: 'Write down the setting of every run before you change it, and report only a number you have seen settle.' },
    book: { title: 'Expt. — ' + S.lab.title,
      lines: ['Medium: ' + MED, 'Z/A = ' + p.ZA + ',  I = ' + p.I + ' eV,  ρ = ' + p.rho + ' g/cm³', 'Bethe-Bloch, no shell or density corrections.'],
      columns: MODE === 0 ? [{ label: 'ppd', get: function (r) { return r.ppd; } }, { label: 'points', get: function (r) { return r.npts; } },
        { label: 'S min', get: function (r) { return fmt(r.Smin, 4); } }, { label: 'E (MeV)', get: function (r) { return fmt(r.Emin, 0); } }]
        : MODE === 1 ? [{ label: 'n', get: function (r) { return r.n; } }, { label: 'R (g/cm²)', get: function (r) { return fmt(r.R, 5); } },
          { label: 'R (cm)', get: function (r) { return fmt(r.Rcm, 4); } }]
          : MODE === 2 ? [{ label: 'Ion', get: function (r) { return r.sym; } }, { label: 'z', get: function (r) { return r.z; } },
            { label: 'S', get: function (r) { return sci(r.S); } }, { label: 'z_eff', get: function (r) { return fmt(r.ze, 2); } }]
            : [{ label: 'n', get: function (r) { return r.n; } }, { label: 'stops (µm)', get: function (r) { return fmt(r.depth, 2); } },
              { label: 'peak (µm)', get: function (r) { return fmt(r.peak, 2); } }] },
    graph: MODE === 2 ? { x: function (r) { return r.z; }, y: function (r) { return r.ze; }, xlabel: 'z', ylabel: 'z_eff', x0: 0, y0: 0 }
      : MODE === 0 ? { x: function (r) { return r.ppd; }, y: function (r) { return r.Smin; }, xlabel: 'points per decade', ylabel: 'S min (MeV cm²/g)' }
        : MODE === 1 ? { x: function (r) { return r.n; }, y: function (r) { return r.R; }, xlabel: 'energy steps n', ylabel: 'R (g/cm²)' }
          : { x: function (r) { return r.n; }, y: function (r) { return r.depth; }, xlabel: 'depth steps n', ylabel: 'stopping depth (µm)' },
    result: result,
    tol: 0.01,
    resultNote: 'A computed curve is only as good as the formula: compare it with the measured tables (NIST PSTAR / ASTAR, SRIM) and see where the corrections this program leaves out begin to matter.',
    chips: ['Why does S fall as 1/β²?', 'What is the mean excitation energy?', 'How is this different from SRIM?', 'Check my runs'],
    viva: [['The stopping power depends on the medium through', ['Z/A and I', 'its colour', 'its temperature only'], 0, 'Electrons per gram and how tightly they are bound.'],
      ['A heavy ion at modest speed has', ['An effective charge below z', 'A charge above z', 'No charge'], 0, 'It carries some electrons.']],
    askState: function () {
      return { experiment: S.lab.title, medium: MED, workstation_on: st.on, setting: MODE === 2 ? IONS[st.ion][1] : st.n,
        runs: S.rows.length, last_run: st.last };
    },
    steps: [
      { id: 'on', title: 'Switch on', view: 'tower', render: function (u) {
          u.h2('Switch the workstation on');
          u.p('Read the method card first: the formula, the medium (' + MED + ') and the task.');
          u.task('Workstation', st.on, st.on ? 'On, program loaded' : 'Off').add(u.button('Press the power button', function () { powerOn(); }, true, st.on || S.hand.busy));
          u.next('Next: run the program', st.on);
        },
        ok: function () { return st.on; }, auto: function () { return powerOn(); } },
      { id: 'run', title: 'Run', view: 'mon', render: function (u) {
          if (MODE === 2) {
            u.h2('Stopping power of each ion at ' + p.E + ' MeV per nucleon');
            u.p('Choose an ion and press Enter. Start with the proton: every other ion is compared with it.');
            u.slider('Ion', 0, IONS.length - 1, 1, function () { return st.ion; }, function (v) { st.ion = Math.round(v); S.render(); }, '', 0);
            u.p('Chosen: ' + IONS[st.ion][1] + ' (z = ' + IONS[st.ion][0] + ')');
          } else {
            u.h2(['Compute S(E) and find its minimum', 'Integrate the range', '', 'March the ion through the target'][MODE]);
            u.p(MODE === 0 ? 'Choose how many energies per decade to compute, from 1 MeV to 50 GeV, and press Enter. Run a coarse grid and finer ones.'
              : MODE === 1 ? 'Choose the number of energy steps and press Enter. Run with few steps and with many: watch the range settle.'
                : 'Choose the number of depth steps and press Enter. Run several times with more steps until the stopping depth settles.');
            u.slider(MODE === 0 ? 'Points per decade' : 'Steps', MODE === 0 ? 1 : MODE === 1 ? 2 : 10, MODE === 0 ? 20 : 1000, 1,
              function () { return st.n; }, function (v) { setN(v); }, '', 0);
          }
          u.button('Press Enter', function () { S.focus('kbd'); run(); }, true, S.hand.busy || !st.on);
          u.live(function () { return st.last ? JSON.stringify(st.last).replace(/[{}"]/g, ' ').slice(0, 120) : 'No run yet'; });
          u.h3('Run log'); u.table();
          u.next('Next: the result', result(S.rows) !== null);
        },
        ok: function () { return result(S.rows) !== null; },
        auto: function () {
          var seq = MODE === 2 ? ZLIST : LIST;
          return seq.reduce(function (pr, v) {
            return pr.then(function () { if (MODE === 2) st.ion = v; else setN(v); return run(); });
          }, Promise.resolve());
        } },
    ],
    tick: function () {
      hud1.set(MODE === 2 ? IONS[st.ion][1] : String(st.n));
      hud2.set(st.last ? (MODE === 0 ? fmt(st.last.Smin, 3) : MODE === 1 ? fmt(st.last.R, 4) : MODE === 2 ? fmt(st.last.ze, 2) : fmt(st.last.depth, 1) + ' µm') : '—');
    },
  };
});
