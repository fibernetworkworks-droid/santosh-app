/* Prayogshala studio module: Kundt's tube - the speed of sound in a rod (B.Sc. Waves and Acoustics).
   Physics: the hw_kundt kernel (packs/heat_wave_ug) - the same numbers the server checks. A rod clamped at its middle sings
   f = v_rod / 2 L; the air column resonates when the piston stands a whole number of half wavelengths d = v_air / 2f from
   the rod's disc, and the dust heaps at the nodes d apart. v_rod = v_air L / d. The hidden knob vr is what the student finds. */
HoolaStudio.define('kundt-tube', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_kundt;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_kundt');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var ROD = /steel/i.test(SAMPLE) ? { name: 'Steel', mat: M.steel, tag: 'STEEL ROD' } : /glass/i.test(SAMPLE) ? { name: 'Glass', mat: new T.MeshPhysicalMaterial({ color: 0xe3f1ee, roughness: 0.05, transmission: 0.6, thickness: 0.01, ior: 1.5, transparent: true, opacity: 0.85 }), tag: 'GLASS ROD' } : { name: 'Brass', mat: M.brass, tag: 'BRASS ROD' };
  function r1(v) { return Math.round(v * 10) / 10; }
  var d = K.spacing(p), VA = K.vair(p), L = p.Lr, LT = p.Lt;
  var st = { temp: false, len: false, clamp: false, dust: false, Lp: 0.5, sing: 0, shownC: 0, clock: 0, heaps: null, dd: null };
  function view() { p.Lp = st.Lp; return K.view({ t: 0 }, p); }

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'pinch', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  // ---------- geometry along x at height YT: rod (left) then tube (right)
  var ZT = -0.2, YT = 0.1, XR0 = -1.04, XT0 = -0.04, XCL = XR0 + L / 2;
  var rod = S.mesh(new T.CylinderGeometry(0.008, 0.008, L, 32), ROD.mat); rod.rotation.z = Math.PI / 2; rod.position.set(XR0 + L / 2, YT, ZT); S.scene.add(rod);
  var disc = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.003, 36), M.cork); disc.rotation.z = Math.PI / 2; disc.position.set(XT0 + 0.012, YT, ZT); S.scene.add(disc);
  var rl = S.label(ROD.tag, { w: 0.07, ratio: 0.12, color: '#4a3510' }); rl.position.set(XR0 + 0.2, YT + 0.0085, ZT + 0.0); rl.rotation.x = -Math.PI / 2; S.scene.add(rl);
  // stand and clamp at the middle
  var stand = new T.Group(); S.scene.add(stand);
  var sb = S.rounded(0.16, 0.12, 0.025, 0.006, M.iron); sb.rotation.x = -Math.PI / 2; sb.position.set(XCL, 0.0125, ZT); stand.add(sb);
  var srod = S.mesh(new T.CylinderGeometry(0.007, 0.007, YT + 0.05, 16), M.chrome); srod.position.set(XCL, (YT + 0.05) / 2, ZT - 0.05); stand.add(srod);
  var clampB = S.rounded(0.04, 0.03, 0.03, 0.004, M.iron); clampB.position.set(XCL, YT, ZT - 0.02); stand.add(clampB);
  var cscrew = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.03, 16), M.chrome); cscrew.position.set(XCL, YT + 0.03, ZT - 0.005); stand.add(cscrew);
  var cknob = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.008, 20), M.black); cknob.position.set(XCL, YT + 0.049, ZT - 0.005); stand.add(cknob);
  S.contact(0.22, 0.18, XCL, ZT, 0.5);
  // glass tube on two wooden blocks, with a piston at the right
  var tube = S.mesh(new T.CylinderGeometry(0.026, 0.026, LT, 40, 1, true), M.glass, false); tube.rotation.z = Math.PI / 2; tube.position.set(XT0 + LT / 2, YT, ZT); tube.material = M.glass; S.scene.add(tube);
  [XT0 + 0.2, XT0 + LT - 0.2].forEach(function (x) { var bl = S.rounded(0.05, 0.075, 0.07, 0.006, M.wood); bl.position.set(x, 0.0375, ZT); S.scene.add(bl); S.contact(0.1, 0.1, x, ZT, 0.5); });
  var powder = S.mesh(new T.BoxGeometry(LT - 0.03, 0.0008, 0.012), new T.MeshStandardMaterial({ color: 0xe8d36a, roughness: 1 }), false); powder.position.set(XT0 + LT / 2, YT - 0.0248, ZT); S.scene.add(powder); powder.visible = false;
  var heapMat = new T.MeshStandardMaterial({ color: 0xe8d36a, roughness: 1 });
  var heaps = []; for (var hi = 0; hi < 22; hi++) { var hm = S.mesh(new T.SphereGeometry(0.0125, 14, 10), heapMat, false); hm.visible = false; hm.userData.i = hi; S.scene.add(hm); heaps.push(hm); }
  var piston = new T.Group(); S.scene.add(piston);
  var pface = S.mesh(new T.CylinderGeometry(0.0245, 0.0245, 0.012, 36), M.rubber); pface.rotation.z = Math.PI / 2; piston.add(pface);
  var prod = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.5, 12), M.chrome); prod.rotation.z = Math.PI / 2; prod.position.set(0.25, 0, 0); piston.add(prod);
  var pknob = S.mesh(new T.SphereGeometry(0.012, 18, 14), M.black); pknob.position.set(0.5, 0, 0); piston.add(pknob);
  function pistonX() { return XT0 + 0.012 + st.Lp; }
  piston.position.set(pistonX(), YT, ZT);
  // a scale along the tube (mm), a thermometer and a cloth
  var scTex = S.canvasTex(4096, 64, function (x, w, h) { x.fillStyle = '#fbfaf3'; x.fillRect(0, 0, w, h); x.fillStyle = '#222'; x.font = '600 26px sans-serif';
    for (var c = 0; c <= 1000; c += 1) { var xx = c / 1000 * (w - 4) + 2, big = c % 100 === 0, mid = c % 10 === 0; x.fillRect(xx, 0, big ? 3 : 1.2, big ? 34 : (mid ? 22 : (c % 5 === 0 ? 14 : 8))); if (big && c < 1000) x.fillText(String(c / 10), xx - 10, 58); } });
  var scale = new T.Mesh(new T.PlaneGeometry(LT, 0.03), new T.MeshStandardMaterial({ map: scTex, roughness: 0.6 })); scale.position.set(XT0 + 0.012 + LT / 2, 0.052, ZT + 0.06); scale.rotation.x = -0.35; S.scene.add(scale);
  var thermo = S.thermometer({ len: 0.25, min: 0, max: 50, value: p.Tc, pos: [-0.35, 0.0, -0.05] });
  var cloth = new T.Group(); S.scene.add(cloth); var clb = S.rounded(0.05, 0.02, 0.03, 0.006, new T.MeshStandardMaterial({ color: 0xc9b18a, roughness: 1 })); clb.position.set(0, 0, 0); cloth.add(clb);
  var CLOTH_HOME = new T.Vector3(XR0 + 0.35, 0.015, ZT + 0.12); cloth.position.copy(CLOTH_HOME);
  var jar = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.05, 24), new T.MeshStandardMaterial({ color: 0xe8d36a, roughness: 0.9 })); jar.position.set(-0.16, 0.025, ZT + 0.16); S.scene.add(jar);
  var jl = S.label('LYCOPODIUM', { w: 0.03, ratio: 0.2, color: '#4a3510' }); jl.position.set(-0.16, 0.03, ZT + 0.1805); S.scene.add(jl);
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);
  var hudC = S.hudCard('Dust figure'), hudL = S.hudCard('Piston'), hudN = S.hudCard('Readings');

  S.addApparatus('rod', rod, ROD.name + ' rod', 'Length ' + (L * 100).toFixed(1) + ' cm, clamped exactly at its middle. Stroke the half outside the tube with a rosined cloth and it sings longitudinally.');
  S.addApparatus('clamp', stand, 'Clamp stand', 'The clamp grips the rod at its middle, where it must be a node.');
  S.addApparatus('tube', tube, 'Glass tube with dust', 'A dry glass tube with a little lycopodium powder. At resonance the powder heaps at the nodes of the standing wave.');
  S.addApparatus('piston', piston, 'Piston', 'Slides in the tube to change the length of the air column. Resonance needs a whole number of half wavelengths.');
  S.addApparatus('thermo', thermo, 'Thermometer', 'Room temperature: the speed of sound in air depends on it.');
  S.addApparatus('scale', scale, 'Scale along the tube', 'Millimetre scale to read the position of each heap from the piston.');
  S.addApparatus('cloth', cloth, 'Rosined cloth', 'Stroke the rod along its length with it.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Not needed here.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var bookLines = ['Aim: to find the speed of sound in a ' + ROD.name.toLowerCase() + ' rod.', 'L = ' + (L * 100).toFixed(1) + ' cm,   ρ = ' + Math.round(p.rho) + ' kg/m³ (tables)', 'v(air) = 331.3 √(1 + t/273.15)', 'v(rod) = v(air) L / d,   Y = ρ v²'];

  // ---------- actions
  function readTemp() { if (st.temp) return; st.temp = true; S.focus('thermo'); S.say('Room temperature ' + r1(p.Tc).toFixed(1) + ' °C, so v(air) = 331.3 √(1 + ' + r1(p.Tc).toFixed(1) + '/273.15) = ' + K.vair(HK.assign(p, { Tc: r1(p.Tc) })).toFixed(1) + ' m/s. Written in your record book.'); S.book.draw(); S.render(); }
  function measureLen() { if (st.len) return; st.len = true; S.focus('rod'); S.say('Length of the rod L = ' + (L * 100).toFixed(1) + ' cm.'); S.book.draw(); S.render(); }
  function clampRod() { if (S.hand.busy || st.clamp) return Promise.resolve(); return S.hand.tap(cknob).then(function () { S.click(1500); cknob.rotation.y = 1.5; st.clamp = true; S.say('The rod is clamped at its middle.'); S.render(); }); }
  function sprinkle() { if (st.dust) return; st.dust = true; powder.visible = true; S.say('A thin line of powder lies along the tube.'); S.render(); }
  function stroke() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.clamp || !st.dust) { S.say('Clamp the rod at its middle and put the powder in first.'); return Promise.resolve(); }
    var a = new T.Vector3(XR0 + 0.2, YT + 0.012, ZT + 0.02), b = new T.Vector3(XR0 + 0.45, YT + 0.012, ZT + 0.02);
    return carry(a, [{ ms: 900, fn: function (k) { return a.clone().lerp(b, k); }, onK: function (k) { cloth.position.copy(a.clone().lerp(b, k)); } },
      { ms: 900, fn: function (k) { return b.clone().lerp(a, k); }, onK: function (k) { cloth.position.copy(b.clone().lerp(a, k)); } }], 'pinch').then(function () { cloth.position.copy(CLOTH_HOME); st.sing = 1; S.click(2600, 0.6); S.say('The rod sings. Watch the powder.'); S.render(); });
  }
  function movePiston(l) {
    l = Math.max(0.1, Math.min(LT - 0.02, Math.round(l * 1000) / 1000));
    if (S.hand.busy) return Promise.resolve();
    var a = piston.position.clone(), b = new T.Vector3(XT0 + 0.012 + l, YT, ZT), big = Math.abs(l - st.Lp) > 0.02;
    if (!big || S.fast) { st.Lp = l; piston.position.copy(b); S.render(); return Promise.resolve(); }
    return carry(new T.Vector3(a.x + 0.5, YT, ZT + 0.005), [{ ms: 1000, fn: function (k) { return a.clone().lerp(b, k).add(new T.Vector3(0.5, 0, 0.005)); }, onK: function (k) { st.Lp = a.x + (b.x - a.x) * k - XT0 - 0.012; piston.position.copy(a.clone().lerp(b, k)); } }], 'grip')
      .then(function () { st.Lp = l; piston.position.copy(b); S.render(); });
  }
  function nudge(dl) { if (S.hand.busy) return; st.Lp = Math.max(0.1, Math.min(LT - 0.02, Math.round((st.Lp + dl) * 1000) / 1000)); piston.position.x = pistonX(); S.render(); }
  function heapPositions() {                                // the powder piles up at the nodes: from the piston, every d
    var n = Math.min(22, Math.floor(st.Lp / d + 0.02) + 1), out = [], j;
    for (j = 0; j < n; j++) out.push(j * d); return out;
  }
  function readHeaps() {
    var v = view();
    if (st.sing < 0.3) { S.say('Stroke the rod so it sings, then read the heaps.'); return false; }
    if (v.clarity < 0.6) { S.say('The heaps are not sharp yet (sharpness ' + v.clarity.toFixed(2) + '). Move the piston a millimetre at a time until the dust is sharpest.'); return false; }
    var pos = heapPositions(); if (pos.length < 8) { S.say('Only ' + pos.length + ' heaps: move the piston further out to get at least 8.'); return false; }
    var x1 = Math.round(pos[0] * 1000) / 1000, x8 = Math.round(pos[7] * 1000) / 1000, dd = (x8 - x1) / 7;
    st.heaps = { x1: x1, x8: x8, n: pos.length, Lp: st.Lp }; st.dd = dd; S.focus('scale');
    S.say('Heap 1 at ' + (x1 * 100).toFixed(1) + ' cm, heap 8 at ' + (x8 * 100).toFixed(1) + ' cm from the piston: d = ' + (dd * 100).toFixed(3) + ' cm.'); S.render(); return true;
  }
  function record() {
    if (st.dd === null) { S.say('Read the heap positions first.'); return; }
    if (S.rows.some(function (r) { return Math.abs(r.Lp - st.heaps.Lp) < 0.01; })) { S.say('Move the piston to a different resonance and measure again.'); return; }
    S.addRow({ Lrod: L, dd: st.dd, Lp: st.heaps.Lp, n: st.heaps.n }); S.say('Written: d = ' + (st.dd * 100).toFixed(3) + ' cm over ' + st.heaps.n + ' heaps.'); st.dd = null; st.heaps = null;
  }
  function vOne(r) { return K.vair(HK.assign(p, { Tc: r1(p.Tc) })) * r.Lrod / r.dd; }
  function bestFor(n) { return n * d; }

  return {
    camera: { pos: [-0.05, 0.6, 2.7], look: [-0.05, 0.08, -0.2] },
    views: { rod: [[-0.7, 0.3, 0.55], [-0.7, 0.1, ZT]], clamp: [[-0.45, 0.3, 0.45], [XCL, 0.07, ZT]], tube: [[0.2, 0.3, 0.6], [0.3, 0.1, ZT]], piston: [[0.75, 0.25, 0.4], [0.5, 0.1, ZT]], thermo: [[-0.35, 0.3, 0.4], [-0.35, 0.1, -0.05]],
      scale: [[0.15, 0.2, 0.4], [0.15, 0.06, ZT + 0.06]], cloth: [[-0.8, 0.25, 0.35], [XR0 + 0.35, 0.05, ZT + 0.1]], sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A rod clamped at its middle sings with a node there and antinodes at both ends, so its wavelength is twice its length. Its disc drives the air in the tube at the same frequency; at resonance the dust heaps at the nodes of the standing wave in the air.',
      formula: 'v(rod) / v(air) = L / d', formulaNote: 'because f = v(rod) / 2L and f = v(air) / 2d, with d the distance between neighbouring heaps (half a wavelength in air). Then Y = ρ v².',
      more: ['v(air) = 331.3 √(1 + t/273.15) m/s with t in °C, the speed of sound in dry air at the room temperature.', 'Measuring across many heaps (eight, so seven gaps) and dividing makes the spacing more exact than measuring one gap.'],
      precautions: 'Clamp the rod exactly at its middle. Keep the tube dry and the powder fine. Stroke along the rod with a rosined cloth, steadily. Move the piston by small steps from both sides to find the sharpest heaps. Read the scale from straight above.' },
    book: { title: 'Expt. — Kundt\'s tube', lines: bookLines,
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Heaps', get: function (r) { return String(r.n); } }, { label: 'd (cm)', get: function (r) { return (r.dd * 100).toFixed(3); } },
        { label: 'L / d', get: function (r) { return (r.Lrod / r.dd).toFixed(2); } }, { label: 'v rod (m/s)', get: function (r) { return vOne(r).toFixed(0); } }] },
    result: function (rows) { if (!rows.length) return null; var s = 0; rows.forEach(function (r) { s += vOne(r); }); var v = s / rows.length;
      return { label: 'v (' + ROD.name.toLowerCase() + ' rod)', value: v, unit: 'm/s', digits: 0, truth: p.vr, note: 'Mean of ' + rows.length + ' readings. Young\'s modulus Y = ρ v² = ' + (p.rho * v * v / 1e9).toFixed(0) + ' GPa (ρ = ' + Math.round(p.rho) + ' kg/m³ from tables).' }; },
    tol: 0.02,
    chips: ['Why is the rod clamped in the middle?', 'Why do the dust heaps form?', 'Why measure eight heaps?', 'Check my readings', 'Why is my v different?'],
    viva: [['Why must the rod be clamped exactly at its middle?', ['The middle is a node and the ends are antinodes', 'So it does not fall', 'To make it sing louder'], 0, 'The fundamental of a rod clamped at its middle has a node there.'],
      ['The distance between neighbouring dust heaps is', ['half a wavelength in air', 'a whole wavelength', 'half a wavelength in the rod'], 0, 'Neighbouring nodes of a standing wave are λ/2 apart.']],
    askState: function () { var v = view(); return { temperature_read: st.temp, rod_length_cm: st.len ? +(L * 100).toFixed(1) : null, clamped: st.clamp, powder: st.dust, rod_singing: st.sing > 0.3, piston_cm: +(st.Lp * 100).toFixed(1), dust_sharpness: st.sing > 0.3 ? +v.clarity.toFixed(2) : null, heaps: st.sing > 0.3 && v.clarity > 0.3 ? heapPositions().length : 0, readings: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'clamp', render: function (u) {
          u.h2('Measure, clamp and sprinkle');
          u.task('1. Read the room temperature', st.temp, st.temp ? 'v(air) = ' + K.vair(HK.assign(p, { Tc: r1(p.Tc) })).toFixed(1) + ' m/s' : 'From the thermometer')
            .add(u.button(st.temp ? 'Read' : 'Read the thermometer', readTemp, !st.temp, st.temp));
          u.task('2. Measure the length of the rod', st.len, st.len ? 'L = ' + (L * 100).toFixed(1) + ' cm' : 'Metre scale')
            .add(u.button(st.len ? 'Measured' : 'Measure L', measureLen, !st.len, st.len));
          u.task('3. Clamp the rod at its middle', st.clamp, st.clamp ? 'Clamped' : 'The hand tightens the clamp')
            .add(u.button(st.clamp ? 'Clamped' : 'Tighten the clamp', function () { clampRod(); }, st.len && !st.clamp, st.clamp || S.hand.busy));
          u.task('4. Sprinkle lycopodium in the tube', st.dust, st.dust ? 'A thin line along the tube' : 'A thin, even line')
            .add(u.button(st.dust ? 'Done' : 'Sprinkle the powder', sprinkle, !st.dust, st.dust));
          u.next('Next: make the dust heap', st.temp && st.len && st.clamp && st.dust);
        },
        ok: function () { return st.temp && st.len && st.clamp && st.dust; },
        auto: function () { readTemp(); measureLen(); sprinkle(); return clampRod(); } },
      { id: 'tune', title: 'Resonance', view: 'piston', render: function (u) {
          u.h2('Stroke the rod and tune the piston');
          u.p('Stroke the rod, then move the piston a little at a time. At resonance the powder gathers in sharp heaps at equal spacings. Take readings at two resonances.');
          u.row(u.button('Stroke the rod', function () { stroke().then(function () { S.render(); }); }, st.sing < 0.3, S.hand.busy));
          u.slider('Piston position', 10, LT * 100 - 2, 0.1, function () { return st.Lp * 100; }, function (v) { st.Lp = v / 100; piston.position.x = pistonX(); }, 'cm', 1);
          u.row(u.button('−1 cm', function () { nudge(-0.01); }, false, false), u.button('−1 mm', function () { nudge(-0.001); }, false, false), u.button('+1 mm', function () { nudge(0.001); }, false, false), u.button('+1 cm', function () { nudge(0.01); }, false, false));
          u.live(function () { var v = view(); return 'Piston ' + (st.Lp * 100).toFixed(1) + ' cm · ' + (st.sing < 0.3 ? 'the rod is quiet: stroke it' : 'dust sharpness ' + v.clarity.toFixed(2) + (v.clarity >= 0.6 ? ' (sharp heaps)' : '')); });
          u.row(u.button('Read the heap positions', function () { readHeaps(); }, true, false), u.button('Write in the table', record, st.dd !== null, st.dd === null));
          u.live(function () { return st.dd === null ? 'No reading in hand' : 'd = ' + (st.dd * 100).toFixed(3) + ' cm (heap 8 − heap 1) / 7'; });
          u.h3('Observation table'); u.table();
          u.next('Next: work out v', S.rows.length >= 2);
          if (S.rows.length < 2) u.p(S.rows.length + ' reading(s) so far. Take 2, at two different resonances (piston positions).');
        },
        ok: function () { return S.rows.length >= 2; },
        auto: function () {
          function one(n) { return stroke().then(function () { return movePiston(Math.round(bestFor(n) * 1000) / 1000); }).then(function () {
            // trim by a millimetre on each side for the sharpest dust, as a student does
            var best = st.Lp, bc = view().clarity, i; for (i = -4; i <= 4; i++) { var l = Math.round((st.Lp + i * 0.001) * 1000) / 1000; st.Lp = l; var c = view().clarity; if (c > bc) { bc = c; best = l; } } st.Lp = best; piston.position.x = pistonX();
            readHeaps(); record(); }); }
          return one(8).then(function () { return one(9); }); } },
    ],

    tick: function (dt) {
      st.clock += dt; if (st.sing > 0) st.sing = Math.max(0, st.sing - dt / 40);
      var v = view(), target = (st.sing > 0.3 && st.dust) ? v.clarity : 0; st.shownC += (target - st.shownC) * Math.min(1, dt * 4);
      var pos = heapPositions(), px = pistonX(), i;
      for (i = 0; i < heaps.length; i++) { var h = heaps[i]; if (i < pos.length && st.shownC > 0.03 && st.dust) { h.visible = true; h.position.set(px - 0.006 - pos[i], YT - 0.0248 + 0.0008, ZT);
          h.scale.set(0.35, 0.1 + 0.9 * st.shownC, 0.45 + 0.5 * st.shownC); } else h.visible = false; }
      piston.position.x = pistonX(); rod.position.y = YT + (st.sing > 0.3 ? Math.sin(st.clock * 90) * 0.0001 : 0);
      hudC.set(st.sing > 0.3 && st.dust ? v.clarity.toFixed(2) : '—'); hudL.set((st.Lp * 100).toFixed(1) + ' cm'); hudN.set(String(S.rows.length));
    },
  };
});
