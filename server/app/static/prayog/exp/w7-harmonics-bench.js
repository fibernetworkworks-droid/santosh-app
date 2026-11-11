/* Prayogshala studio rig: harmonics of a complex wave on a CRO (pack ug_mech_w7, kernel w7_fourier).
   A function generator gives a square, triangular or clipped sine wave at f0. A narrow tunable band-pass filter is
   tuned to n f0 and the CRO shows the sine wave it passes: the n-th harmonic. The student reads its peak-to-peak
   height with the cursors for n = 1, 2, 3 ... and compares the relative amplitudes with Fourier's theorem.
   Every amplitude is the kernel's own Fourier integral of the wave; nothing is typed in. */
HoolaStudio.define('w7-harmonics-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.w7_fourier, PI = Math.PI;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('w7_fourier');
  var SHAPE = p.shape < 0.5 ? { name: 'square wave', tag: 'SQUARE', law: '1/n (odd n only)' } : p.shape < 1.5 ? { name: 'triangular wave', tag: 'TRIANGLE', law: '1/n² (odd n only)' } : { name: 'clipped sine wave', tag: 'CLIPPED SINE', law: 'the Fourier integral (odd n only)' };
  var st = { dims: false, on: false, tuned: false, nSet: 1, an: 0, t: 0 };
  var ZB = -0.36;
  function box(w, h, d, mat) { return S.mesh(new T.BoxGeometry(w, h, d), mat); }
  function cyl(r, h, mat, seg) { return S.mesh(new T.CylinderGeometry(r, r, h, seg || 24), mat); }
  function rnd(v, lc) { return Math.round(v / lc) * lc; }
  function peak() { return p.shape > 1.5 ? p.A * p.clip : p.A; }
  function exact(n) { var q = {}; Object.keys(p).forEach(function (k) { q[k] = p[k]; }); q.n = n; return HK.TEXTBOOK.w7_fourier_ratio(q); }

  // ---------- function generator
  var gen = new T.Group(); S.scene.add(gen); gen.position.set(-0.28, 0, ZB);
  var gb = S.rounded(0.26, 0.11, 0.2, 0.01, new T.MeshStandardMaterial({ color: 0x33414f, roughness: 0.5 })); gb.position.y = 0.055; gen.add(gb);
  var gtex = S.liveTex(384, 128), gscr = new T.Mesh(new T.PlaneGeometry(0.11, 0.037), new T.MeshBasicMaterial({ map: gtex, toneMapped: false })); gscr.position.set(-0.06, 0.075, 0.1005); gen.add(gscr);
  var gl = S.label('FUNCTION GENERATOR', { w: 0.16, ratio: 0.12, color: '#e9edf2' }); gl.position.set(0, 0.022, 0.1006); gen.add(gl);
  var gpow = cyl(0.009, 0.008, M.green); gpow.rotation.x = PI / 2; gpow.position.set(0.1, 0.08, 0.102); gen.add(gpow);
  [0.03, 0.065].forEach(function (x) { var k = cyl(0.011, 0.012, M.black); k.rotation.x = PI / 2; k.position.set(x, 0.07, 0.104); gen.add(k); });
  S.contact(0.34, 0.28, -0.28, ZB, 0.55);
  function drawGen() { gtex.draw(function (x) { x.fillStyle = st.on ? '#9fe6b0' : '#32403a'; x.fillRect(0, 0, 384, 128); if (!st.on) return; x.fillStyle = '#0d2a14'; x.font = '700 46px "JetBrains Mono", monospace'; x.textAlign = 'left';
    x.fillText((p.f0 / 1000).toFixed(3) + ' kHz', 12, 52); x.font = '700 34px "JetBrains Mono", monospace'; x.fillText(SHAPE.tag, 12, 104); }); }
  // ---------- tunable filter
  var fil = new T.Group(); S.scene.add(fil); fil.position.set(0.06, 0, ZB + 0.02);
  var fb = S.rounded(0.2, 0.09, 0.16, 0.01, new T.MeshStandardMaterial({ color: 0x6b6f58, roughness: 0.55 })); fb.position.y = 0.045; fil.add(fb);
  var dial = cyl(0.026, 0.014, M.black, 40); dial.rotation.x = PI / 2; dial.position.set(0.045, 0.05, 0.087); fil.add(dial);
  var dmark = box(0.003, 0.02, 0.002, M.white); dmark.position.set(0, 0.012, 0); var dg = new T.Group(); dg.position.set(0.045, 0.05, 0.0945); dg.add(dmark); fil.add(dg);
  var ftex = S.liveTex(256, 96), fscr = new T.Mesh(new T.PlaneGeometry(0.075, 0.028), new T.MeshBasicMaterial({ map: ftex, toneMapped: false })); fscr.position.set(-0.045, 0.058, 0.0805); fil.add(fscr);
  var fl = S.label('TUNABLE BAND-PASS FILTER', { w: 0.16, ratio: 0.11, color: '#f0efe2' }); fl.position.set(0, 0.016, 0.0806); fil.add(fl);
  S.contact(0.27, 0.23, 0.06, ZB + 0.02, 0.55);
  function drawFil() { ftex.draw(function (x) { x.fillStyle = st.on ? '#e9c46a' : '#4a4530'; x.fillRect(0, 0, 256, 96); if (!st.on) return; x.fillStyle = '#2a1e00'; x.font = '700 44px "JetBrains Mono", monospace'; x.textAlign = 'center';
    x.fillText(st.tuned ? (p.n * p.f0 / 1000).toFixed(2) + ' kHz' : '-- kHz', 128, 62); }); }
  // ---------- CRO
  var cro = new T.Group(); S.scene.add(cro); cro.position.set(0.48, 0, ZB - 0.02);
  var cb = S.rounded(0.34, 0.24, 0.3, 0.012, new T.MeshStandardMaterial({ color: 0xd8d4c8, roughness: 0.6 })); cb.position.y = 0.12; cro.add(cb);
  var bez = S.rounded(0.2, 0.16, 0.006, 0.006, M.black); bez.position.set(-0.05, 0.13, 0.151); cro.add(bez);
  var ctex = S.liveTex(640, 512), cscr = new T.Mesh(new T.PlaneGeometry(0.185, 0.148), new T.MeshBasicMaterial({ map: ctex, toneMapped: false })); cscr.position.set(-0.05, 0.13, 0.1545); cro.add(cscr);
  [[0.09, 0.19], [0.135, 0.19], [0.09, 0.13], [0.135, 0.13], [0.09, 0.07], [0.135, 0.07]].forEach(function (q) { var k = cyl(0.012, 0.012, M.grey); k.rotation.x = PI / 2; k.position.set(q[0], q[1], 0.156); cro.add(k); });
  var cl = S.label('DIGITAL STORAGE OSCILLOSCOPE', { w: 0.2, ratio: 0.1, color: '#2a2a2a' }); cl.position.set(-0.05, 0.03, 0.1506); cro.add(cl);
  S.contact(0.42, 0.38, 0.48, ZB - 0.02, 0.55);
  S.wire([[-0.2, 0.05, ZB + 0.1], [-0.1, 0.01, ZB + 0.2], [0.0, 0.04, ZB + 0.1]], 'black'); S.wire([[0.12, 0.04, ZB + 0.1], [0.25, 0.01, ZB + 0.22], [0.4, 0.05, ZB + 0.13]], 'black');
  S.wire([[-0.24, 0.05, ZB + 0.1], [0.05, 0.005, ZB + 0.26], [0.36, 0.05, ZB + 0.13]], 'yellow');
  var frames = 0, lastKey = '';
  function vdiv(a) { var opts = [2, 1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01], i; for (i = opts.length - 1; i >= 0; i--) if (a <= 3.2 * opts[i]) return opts[i]; return 2; }
  function drawCro(force) {
    var key = st.on + '|' + st.tuned + '|' + p.n; if (!force && key === lastKey && (S.fast || frames++ % 6)) return; lastKey = key;
    ctex.draw(function (x) { x.fillStyle = '#06140c'; x.fillRect(0, 0, 640, 512); x.strokeStyle = 'rgba(110,190,140,.3)'; x.lineWidth = 1; var i;
      for (i = 0; i <= 10; i++) { x.beginPath(); x.moveTo(i * 64, 0); x.lineTo(i * 64, 512); x.stroke(); } for (i = 0; i <= 8; i++) { x.beginPath(); x.moveTo(0, i * 64); x.lineTo(640, i * 64); x.stroke(); }
      if (!st.on) return;
      var v1 = vdiv(peak()), ph0 = S.fast ? 0 : (st.t * 0.15) % 1, px;
      x.strokeStyle = '#f2c94c'; x.lineWidth = 2.5; x.beginPath(); for (px = 0; px <= 640; px += 2) { var y = p.A * K.wave(p, px / 640 * 2 + ph0); var py = 150 - y / v1 * 40; if (px) x.lineTo(px, py); else x.moveTo(px, py); } x.stroke();
      x.fillStyle = '#f2c94c'; x.font = '600 20px "JetBrains Mono", monospace'; x.textAlign = 'left'; x.fillText('CH1 ' + v1 + ' V/div  wave', 8, 22);
      if (st.tuned) { var a = Math.abs(st.an), v2 = vdiv(Math.max(a, 0.004)); x.strokeStyle = '#5fd0ff'; x.lineWidth = 2.5; x.beginPath();
        for (px = 0; px <= 640; px += 2) { var yy = a * Math.sin(2 * PI * p.n * (px / 640 * 2 + ph0)); var p2 = 380 - yy / v2 * 40; if (px) x.lineTo(px, p2); else x.moveTo(px, p2); } x.stroke();
        x.fillStyle = '#5fd0ff'; x.fillText('CH2 ' + v2 + ' V/div  filter out   Vpp ' + (2 * a).toFixed(3) + ' V', 8, 500); } });
  }
  drawGen(); drawFil(); drawCro(true);
  S.addApparatus('gen', gen, 'Function generator', 'Gives the ' + SHAPE.name + ' at ' + (p.f0 / 1000).toFixed(3) + ' kHz.');
  S.addApparatus('fil', fil, 'Tunable band-pass filter', 'A narrow filter of unit gain at its centre frequency. Tuned to n times the fundamental it passes only the n-th harmonic.');
  S.addApparatus('cro', cro, 'Digital storage oscilloscope', 'Channel 1 shows the wave itself, channel 2 the filter output. The cursors read a peak-to-peak height to 1 mV.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hud1 = S.hudCard('Filter tuned to'), hud2 = S.hudCard('CH2 peak to peak');

  function switchOn() { if (st.dims || S.hand.busy) return Promise.resolve(); return S.hand.tap(gpow).then(function () { st.on = true; st.dims = true; S.click(1800); drawGen(); drawFil(); drawCro(true);
    S.say('The wave on channel 1 is a ' + SHAPE.name + ' of ±' + peak().toFixed(2) + ' V at ' + (p.f0 / 1000).toFixed(3) + ' kHz. Written in your record book.'); S.book.draw(); S.render(); }); }
  function tune() { if (!st.on) { S.say('Switch the generator on first.'); return Promise.resolve(); } if (S.hand.busy) return Promise.resolve();
    return S.hand.tap(dial).then(function () { p.n = st.nSet; st.an = K.measure(p).an; st.tuned = true; dg.rotation.z = -(p.n - 1) * 0.6; S.click(2000); drawFil(); drawCro(true); S.render(); }); }
  function read() { if (!st.tuned) { S.say('Tune the filter first.'); return; } if (S.rows.some(function (r) { return r.n === p.n; })) { S.say('Harmonic ' + p.n + ' is already in the table. Tune to another.'); return; }
    var r = { n: p.n, f: p.n * p.f0, Vpp: rnd(2 * Math.abs(st.an), 0.001) }; S.addRow(r); S.say('Harmonic ' + r.n + ' at ' + (r.f / 1000).toFixed(2) + ' kHz: ' + r.Vpp.toFixed(3) + ' V peak to peak.'); }
  function rowN(rows, n) { return rows.filter(function (r) { return r.n === n; })[0]; }
  function need(rows) { return rowN(rows, 1) && rowN(rows, 3) && rows.length >= 4 ? '' : 'Read the fundamental, the third harmonic and at least two more.'; }

  return {
    camera: { pos: [0.12, 0.52, 1.1], look: [0.12, 0.08, ZB] },
    views: { main: [[0.12, 0.5, 1.05], [0.12, 0.08, ZB]], gen: [[-0.25, 0.25, 0.1], [-0.28, 0.06, ZB]], fil: [[0.08, 0.22, 0.05], [0.06, 0.05, ZB]], cro: [[0.3, 0.3, 0.45], [0.36, 0.11, ZB]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: 'y(t) = Σ bₙ sin(2π n f0 t)', formulaNote: 'For this ' + SHAPE.name + ' the harmonics fall as ' + SHAPE.law + '.', more: [S.lab.aim], precautions: S.lab.safety + ' Tune the filter for the largest output before reading it.' },
    book: { title: 'Expt. — Harmonics of a ' + SHAPE.name, lines: ['Aim: relative amplitudes of the harmonics of a ' + SHAPE.name + '.', 'f0 = ' + (p.f0 / 1000).toFixed(3) + ' kHz,  wave ±' + peak().toFixed(2) + ' V', 'relative amplitude = Vpp(n) / Vpp(1)'],
      columns: [{ label: 'n', get: function (r) { return String(r.n); } }, { label: 'f (kHz)', get: function (r) { return (r.f / 1000).toFixed(2); } }, { label: 'Vpp (V)', get: function (r) { return r.Vpp.toFixed(3); } },
        { label: 'Vpp(n)/Vpp(1)', get: function (r) { var a = rowN(S.rows, 1); return a ? (r.Vpp / a.Vpp).toFixed(4) : '—'; } }] },
    result: function (rows) { var a = rowN(rows, 1), b = rowN(rows, 3); if (!a || !b || !a.Vpp) return null;
      var others = rows.filter(function (r) { return r.n !== 1 && r.n !== 3; }).map(function (r) { return 'n = ' + r.n + ': ' + (r.Vpp / a.Vpp).toFixed(4) + (r.n % 2 ? ' (Fourier ' + exact(r.n).toFixed(4) + ')' : ' (Fourier 0)'); }).join('; ');
      return { label: 'b₃ / b₁ (third harmonic ÷ fundamental)', value: b.Vpp / a.Vpp, unit: '', digits: 4, truth: exact(3), note: 'Fundamental amplitude ' + (a.Vpp / 2).toFixed(3) + ' V. ' + others + '.' }; },
    tol: 0.03,
    chips: ['What is a harmonic?', 'Why are the even harmonics missing?', 'Check my readings', 'What does the filter do?'],
    viva: [['Which harmonics does a symmetrical ' + SHAPE.name + ' contain?', ['Only the odd ones', 'Only the even ones', 'All of them'], 0, 'Its second half cycle is the first one turned upside down, which removes every even harmonic.']],
    askState: function () { return { wave: SHAPE.name, generator_on: st.on, filter_tuned_to_harmonic: st.tuned ? p.n : 'not tuned', ch2_peak_to_peak_V: st.tuned ? +(2 * Math.abs(st.an)).toFixed(3) : 0, harmonics_read: S.rows.map(function (r) { return r.n; }).join(', ') || 'none' }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'main', render: function (u) { u.h2('Switch on and look at the wave');
          u.p('The generator feeds channel 1 of the oscilloscope directly, and channel 2 through the filter.');
          u.task('Switch the generator on and note the wave', st.dims, st.dims ? SHAPE.name + ', ±' + peak().toFixed(2) + ' V, ' + (p.f0 / 1000).toFixed(3) + ' kHz' : 'The hand presses the power button')
            .add(u.button(st.dims ? 'On' : 'Switch on', function () { switchOn(); }, !st.dims, st.dims || S.hand.busy));
          u.next('Next: pick out the harmonics', st.dims); },
        ok: function () { return st.dims; }, auto: function () { return switchOn(); } },
      { id: 'read', title: 'Harmonics', view: 'cro', render: function (u) { u.h2('Tune the filter, read the harmonic');
          u.slider('Tune the filter to harmonic n', 1, 9, 1, function () { return st.nSet; }, function (v) { st.nSet = v; }, '× f0');
          u.row(u.button('Turn the dial to n f0', function () { tune(); }, true, S.hand.busy), u.button('Read Vpp with the cursors', read, false, !st.tuned));
          u.live(function () { return st.tuned ? 'Filter at ' + (p.n * p.f0 / 1000).toFixed(2) + ' kHz · CH2 ' + (2 * Math.abs(st.an)).toFixed(3) + ' V peak to peak' : 'Filter not tuned'; });
          u.h3('Observation table'); u.table(); var nd = need(S.rows); if (nd) u.p(nd); u.next('Next: compare with Fourier', !nd); },
        ok: function () { return !need(S.rows); },
        auto: function () { return [1, 2, 3, 4, 5, 7, 9].reduce(function (pr, n) { return pr.then(function () { st.nSet = n; return tune(); }).then(function () { read(); }); }, Promise.resolve()); } },
    ],
    tick: function (dt) { st.t += dt; drawCro(false); hud1.set(st.tuned ? p.n + ' × f0' : '—'); hud2.set(st.tuned ? (2 * Math.abs(st.an)).toFixed(3) + ' V' : '—'); },
  };
});
