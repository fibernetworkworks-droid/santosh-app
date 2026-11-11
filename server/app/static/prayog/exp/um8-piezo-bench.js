/* Prayogshala studio RIG: the PIEZO RESONANCE BENCH of wave 8 (B.Sc. solid state physics).
   A function generator drives a PZT ceramic disc (in a spring holder) in series with a 100 ohm sense resistor; an AC
   millivoltmeter reads the voltage across the resistor, i.e. the current through the disc. The student sweeps the
   frequency through the radial resonance and reads the maximum (resonance fr) and the minimum (antiresonance fa).
   Physics: the um8_piezo kernel (packs/ug_matter_w8.js), the Butterworth-Van Dyke circuit - the same code the server
   checks. k_eff^2 = 1 - (fr / fa)^2. SIMULATED DATA. */
HoolaStudio.define('um8-piezo-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.um8_piezo, assign = HK.assign;
  var p = HK.paramsFor('um8_piezo', S.lab.params);
  var V_ = S.lab.variant || {};
  var DISC = V_.sample || 'PZT-5A type ceramic disc, 20 mm, silvered faces';
  var FA0 = p.fs / Math.sqrt(1 - p.k * p.k);            // where to look: set from this disc's own numbers
  var FLO = Math.floor(0.7 * p.fs / 1000), FHI = Math.ceil(1.25 * FA0 / 1000);
  var st = { on: false, f: FLO * 1000, last: null, sweep: null, from: FLO, to: FHI, step: 1 };

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function fmt(v, d) { return isFinite(v) ? v.toFixed(d) : '—'; }
  function vr(f) { return KN.zabs(f, p)[1]; }
  function readV(f) { return Math.round(vr(f) * 1e4) / 10; }      // mV to 0.1 mV

  // ================================================================ generator, disc, resistor, voltmeter
  function box(w, h, d, col, pos) { var g = new T.Group(); S.scene.add(g); g.position.set(pos[0], 0, pos[1]);
    var b = S.rounded(w, h, d, 0.01, new T.MeshStandardMaterial({ color: col, roughness: 0.5 })); b.position.y = h / 2; g.add(b); return g; }
  var gen = box(0.26, 0.1, 0.2, 0x2b2f36, [-0.24, -0.2]);
  var gTex = S.liveTex(512, 160), gLast = '';
  var gScr = new T.Mesh(new T.PlaneGeometry(0.12, 0.036), new T.MeshBasicMaterial({ map: gTex, toneMapped: false })); gScr.position.set(-0.05, 0.065, 0.1005); gen.add(gScr);
  var gKnob = new T.Group(); gKnob.position.set(0.075, 0.05, 0.1); gen.add(gKnob);
  var gk = S.mesh(new T.CylinderGeometry(0.018, 0.019, 0.016, 32), M.bakelite); gk.rotation.x = Math.PI / 2; gk.position.z = 0.008; gKnob.add(gk);
  var gptr = S.mesh(new T.BoxGeometry(0.002, 0.014, 0.0012), M.white, false); gptr.position.set(0, 0.008, 0.0165); gKnob.add(gptr);
  var gPwr = S.mesh(new T.BoxGeometry(0.018, 0.012, 0.006), M.red); gPwr.position.set(-0.1, 0.025, 0.101); gen.add(gPwr);
  var gL = S.label('FUNCTION GENERATOR   1 Hz – 2 MHz', { w: 0.14, ratio: 0.1, color: '#e8e8ea' }); gL.position.set(-0.03, 0.088, 0.1005); gen.add(gL);
  S.contact(0.32, 0.26, -0.24, -0.2, 0.5);
  var holder = new T.Group(); S.scene.add(holder); holder.position.set(0.0, 0, -0.1);
  var hb = S.rounded(0.1, 0.07, 0.02, 0.008, M.wood); hb.rotation.x = -Math.PI / 2; hb.position.y = 0.01; holder.add(hb);
  var post = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.06, 12), M.brass); post.position.set(-0.03, 0.05, 0); holder.add(post);
  var post2 = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.06, 12), M.brass); post2.position.set(0.03, 0.05, 0); holder.add(post2);
  var disc = new T.Group(); disc.position.set(0, 0.06, 0); holder.add(disc);
  var cer = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.002, 40), new T.MeshStandardMaterial({ color: 0xe9e3d3, roughness: 0.7 })); cer.rotation.x = Math.PI / 2; disc.add(cer);
  var ag = S.mesh(new T.CylinderGeometry(0.018, 0.018, 0.0022, 40), M.chrome); ag.rotation.x = Math.PI / 2; disc.add(ag);
  var clip1 = S.mesh(new T.BoxGeometry(0.012, 0.004, 0.006), M.brass); clip1.position.set(-0.022, 0, 0); disc.add(clip1);
  var clip2 = S.mesh(new T.BoxGeometry(0.012, 0.004, 0.006), M.brass); clip2.position.set(0.022, 0, 0); disc.add(clip2);
  var res = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.014, 12), new T.MeshStandardMaterial({ color: 0xc8b28a })); res.rotation.z = Math.PI / 2; res.position.set(0.08, 0.012, 0.0); S.scene.add(res);
  var rl = S.label('100 Ω', { w: 0.03, ratio: 0.3, color: '#2b2f36' }); rl.rotation.x = -Math.PI / 2; rl.position.set(0.08, 0.001, 0.02); S.scene.add(rl);
  S.contact(0.12, 0.09, 0.0, -0.1, 0.45);
  var mv = box(0.18, 0.1, 0.16, 0x3a4f6e, [0.28, -0.1]);
  var mTex = S.liveTex(512, 160), mLast = '';
  var mScr = new T.Mesh(new T.PlaneGeometry(0.12, 0.036), new T.MeshBasicMaterial({ map: mTex, toneMapped: false })); mScr.position.set(0, 0.06, 0.0805); mv.add(mScr);
  var mL = S.label('AC MILLIVOLTMETER', { w: 0.1, ratio: 0.12, color: '#e8e8ea' }); mL.position.set(0, 0.025, 0.0805); mv.add(mL);
  S.contact(0.24, 0.22, 0.28, -0.1, 0.5);
  S.wire([[-0.16, 0.05, -0.1], [-0.03, 0.08, -0.1]], 'red');
  S.wire([[0.03, 0.08, -0.1], [0.073, 0.012, 0.0]], 'black');
  S.wire([[0.087, 0.012, 0.0], [0.22, 0.05, -0.02]], 'black');
  S.wire([[-0.16, 0.04, -0.1], [0.0, 0.01, 0.06], [0.24, 0.04, -0.02]], 'black');
  function lcd(tex, txt, which) {
    if ((which ? mLast : gLast) === txt) return; if (which) mLast = txt; else gLast = txt;
    tex.draw(function (x) { x.fillStyle = which ? '#a9b79a' : '#0b1f12'; x.fillRect(0, 0, 512, 160); x.font = '700 76px "JetBrains Mono", monospace';
      x.textAlign = 'right'; x.fillStyle = which ? '#1b2116' : '#5cff8a'; x.fillText(txt, 490, 112); });
  }
  lcd(gTex, '-----', 0); lcd(mTex, '0.0', 1);

  S.addApparatus('gen', gen, 'Function generator', 'Sets the frequency; its display reads it to 10 Hz.');
  S.addApparatus('disc', holder, DISC, 'The disc between two spring contacts on its silvered faces, so it is free to vibrate in its plane.');
  S.addApparatus('mv', mv, 'AC millivoltmeter', 'Reads the voltage across the 100 Ω sense resistor: the current through the disc times 100 Ω.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every sweep is written here.');
  var hudF = S.hudCard('Frequency'), hudV = S.hudCard('Sense voltage');

  // ================================================================ actions
  function power() {
    if (busy() || st.on) return Promise.resolve();
    return S.hand.tap(gPwr, 'front').then(function () { st.on = true; S.say('Generator on, 1 V amplitude.'); S.render(); });
  }
  function turnTo(fk) {
    if (busy()) return Promise.resolve();
    if (!isFinite(fk) || fk < 50 || fk > 200) { S.say('Sweep between 50 and 200 kHz: the radial resonance of this disc lies in that range.'); return Promise.resolve(); }
    var pt = gKnob.getWorldPosition(new T.Vector3()), f0 = st.f;
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { st.f = f0 + (fk * 1000 - f0) * k; gKnob.rotation.z = -st.f / 20000; },
      { mode: 'front', ms: 500, reachMs: 450 }).then(function () { st.f = Math.round(fk * 100) * 10; S.render(); });
  }
  function sweep(fromK, toK, stepK) {
    if (busy()) return Promise.resolve(false);
    if (!st.on) { S.say('Switch the generator on first.'); return Promise.resolve(false); }
    if (!(toK > fromK) || stepK <= 0 || (toK - fromK) / stepK > 400) { S.say('Choose a range and a step that give at most 400 readings.'); return Promise.resolve(false); }
    var xs = [], ys = [], f;
    for (f = fromK; f <= toK + 1e-9; f += stepK) { xs.push(Math.round(f * 100) / 100); ys.push(readV(Math.round(f * 100) * 10)); }
    return turnTo(fromK).then(function () {
      return S.tween(1600, function (k) { var i = Math.min(xs.length - 1, Math.floor(k * xs.length)); st.f = xs[i] * 1000; gKnob.rotation.z = -st.f / 20000; });
    }).then(function () {
      var imax = 0, imin = 0, i;
      for (i = 1; i < ys.length; i++) { if (ys[i] > ys[imax]) imax = i; if (ys[i] < ys[imin]) imin = i; }
      st.sweep = { x: xs, y: ys };
      var row = { from: fromK, to: toK, step: stepK, fmax: xs[imax], vmax: ys[imax], fmin: xs[imin], vmin: ys[imin] };
      S.addRow(row); st.last = row; st.f = xs[xs.length - 1] * 1000;
      S.say('Swept ' + fromK + ' to ' + toK + ' kHz in steps of ' + stepK + ' kHz: largest ' + fmt(row.vmax, 1) + ' mV at ' + fmt(row.fmax, 2) + ' kHz, smallest ' + fmt(row.vmin, 1) + ' mV at ' + fmt(row.fmin, 2) + ' kHz.');
      S.render(); return true;
    });
  }
  function best(rows, key) {           // the finest sweep that contains the extreme
    var r = rows.filter(function (q) { return q[key] > q.from && q[key] < q.to; });
    if (!r.length) return null;
    return r.reduce(function (a, b) { return b.step < a.step ? b : a; });
  }
  function result(rows) {
    var a = best(rows, 'fmax'), b = best(rows, 'fmin');
    if (!a || !b || a.step > 0.1 || b.step > 0.1) return null;
    var fr = a.fmax, fa = b.fmin;
    if (!(fa > fr)) return null;
    return { label: 'Coupling coefficient k_eff', value: Math.sqrt(1 - Math.pow(fr / fa, 2)), unit: '', digits: 3, truth: p.k,
      note: 'Resonance fr = ' + fmt(fr, 2) + ' kHz (current maximum), antiresonance fa = ' + fmt(fa, 2) + ' kHz (current minimum): k_eff² = 1 − (fr/fa)². SIMULATED DATA.' };
  }

  return {
    camera: { pos: [0.0, 0.6, 0.85], look: [0, 0.08, -0.08] },
    views: { gen: [[-0.16, 0.3, 0.22], [-0.24, 0.06, -0.2]], disc: [[0.04, 0.22, 0.16], [0.0, 0.06, -0.1]], mv: [[0.3, 0.3, 0.3], [0.28, 0.06, -0.1]],
      bench: [[0.0, 0.6, 0.85], [0, 0.08, -0.08]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'Near a mechanical resonance a piezoelectric disc behaves like a series R-L-C branch in parallel with its own capacitance C0 (the Butterworth-Van Dyke circuit). The current is largest at the resonance fr and nearly vanishes at the antiresonance fa just above it.',
      formula: 'k_eff² = 1 − (fr / fa)² = C1 / (C0 + C1)',
      formulaNote: 'fr: series resonance (current maximum);  fa: parallel resonance (current minimum)',
      more: ['The further apart fr and fa, the more strongly the electrical and mechanical energies are coupled.',
        'Both extremes are sharp: sweep coarsely to find them, then slowly in small steps through each.',
        'The small sense resistor loads the disc a little; with 100 Ω the error in fr is far below the reading step.'],
      precautions: 'Hold the brittle disc only by its edge, keep the contacts at the centre of the faces, and change the frequency slowly near the extremes.' },
    book: { title: 'Expt. — Coupling coefficient of a piezoelectric disc',
      lines: ['Disc: ' + DISC, 'Sense resistor 100 Ω, generator 1 V.', 'k_eff² = 1 − (fr/fa)²'],
      columns: [{ label: 'range (kHz)', get: function (r) { return r.from + '–' + r.to; } }, { label: 'step', get: function (r) { return r.step; } },
        { label: 'f max (kHz)', get: function (r) { return fmt(r.fmax, 2); } }, { label: 'f min (kHz)', get: function (r) { return fmt(r.fmin, 2); } }] },
    graph: { x: function (r) { return r.step; }, y: function (r) { return r.fmin - r.fmax; }, xlabel: 'sweep step (kHz)', ylabel: 'fa − fr (kHz)', x0: 0 },
    result: result,
    tol: 0.02,
    resultNote: 'The two sharp extremes of the current are the whole measurement: their ratio gives how much of the drive becomes vibration. PZT ceramics couple far more strongly than quartz.',
    chips: ['What is the antiresonance?', 'Why a sense resistor?', 'What does k_eff mean physically?', 'Check my sweeps'],
    viva: [['At the antiresonance the current through the disc is', ['A minimum', 'A maximum', 'Unchanged'], 0, 'The motional branch and C0 form a parallel resonance.'],
      ['k_eff² = 1 − (fr/fa)² equals', ['C1 / (C0 + C1)', 'C0 / C1', 'R1 / Rs'], 0, 'From the BVD circuit.']],
    askState: function () {
      return { experiment: 'coupling coefficient of a PZT disc from its resonance and antiresonance', disc: DISC, generator_on: st.on,
        frequency_kHz: st.f / 1000, sense_mV: readV(st.f), sweeps: S.rows.length, last_sweep: st.last };
    },
    steps: [
      { id: 'coarse', title: 'Coarse sweep', view: 'gen', render: function (u) {
          u.h2('Find the resonance and the antiresonance');
          u.p('Switch the generator on and sweep from ' + FLO + ' to ' + FHI + ' kHz in steps of 1 kHz, watching the millivoltmeter: a sharp maximum, then a sharp minimum.');
          u.task('Generator', st.on, st.on ? 'On' : 'Off').add(u.button('Switch it on', function () { power(); }, true, st.on || S.hand.busy));
          u.button('Sweep ' + FLO + '–' + FHI + ' kHz, 1 kHz steps', function () { sweep(FLO, FHI, 1); }, false, S.hand.busy || !st.on);
          u.table();
          u.next('Next: slow sweeps', S.rows.length >= 1);
        },
        ok: function () { return S.rows.length >= 1; },
        auto: function () { return power().then(function () { return sweep(FLO, FHI, 1); }); } },
      { id: 'fine', title: 'Slow sweeps', view: 'mv', render: function (u) {
          u.h2('Sweep slowly through each extreme');
          var c = st.last || { fmax: p.fs / 1000, fmin: FA0 / 1000 };
          u.p('Sweep 2 kHz around each extreme in steps of 0.05 kHz (50 Hz).');
          u.slider('Step', 0.01, 1, 0.01, function () { return st.step; }, function (v) { st.step = Math.round(v * 100) / 100; }, 'kHz', 2);
          var a = S.rows[0] || c;
          u.row(u.button('Sweep round the maximum', function () { sweep(Math.round(a.fmax) - 1, Math.round(a.fmax) + 1, st.step); }, true, S.hand.busy || !st.on),
            u.button('Sweep round the minimum', function () { sweep(Math.round(a.fmin) - 1, Math.round(a.fmin) + 1, st.step); }, false, S.hand.busy || !st.on));
          u.live(function () { return fmt(st.f / 1000, 2) + ' kHz  ·  ' + fmt(readV(st.f), 1) + ' mV'; });
          u.table();
          u.next('Next: the result', result(S.rows) !== null);
        },
        ok: function () { return result(S.rows) !== null; },
        auto: function () {
          var a = S.rows[0]; st.step = 0.05;
          return sweep(Math.round(a.fmax) - 1, Math.round(a.fmax) + 1, 0.05).then(function () { return sweep(Math.round(a.fmin) - 1, Math.round(a.fmin) + 1, 0.05); });
        } },
    ],
    tick: function () {
      lcd(gTex, st.on ? (st.f / 1000).toFixed(2) + 'k' : '-----', 0);
      lcd(mTex, st.on ? readV(st.f).toFixed(1) : '0.0', 1);
      hudF.set(st.on ? (st.f / 1000).toFixed(2) + ' kHz' : 'off');
      hudV.set(st.on ? readV(st.f).toFixed(1) + ' mV' : '—');
      cer.rotation.y += 0;
    },
  };
});
