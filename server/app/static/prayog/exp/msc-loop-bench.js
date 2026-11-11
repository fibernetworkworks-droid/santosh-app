/* Prayogshala studio module: M.Sc. HYSTERESIS-LOOP BENCH (B-H, P-E and M-H loops).
   A function generator drives the sample, an integrator turns the response into a voltage, and an oscilloscope in X-Y
   mode draws the loop. The loop is the `msc_loop` kernel (packs/msc_solid.js): the rising branch M = Ms tanh((H - Hc)/a),
   the falling branch the mirror image, and a loop that is not driven to saturation is narrower. The student drives the
   sample harder and harder, captures the loop each time, and reads the coercive field where the loop cuts the field
   axis, the remanence where it cuts the other axis, the saturation from its flat top, and the energy lost per cycle from
   its area - all found by searching the traced points, never read back from the formula. */
HoolaStudio.define('msc-loop-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.msc_loop, assign = HK.assign;
  var p = HK.paramsFor('msc_loop', S.lab.params);
  var V_ = S.lab.variant || {};
  var KIND = Math.round(p.kind);
  var U = {
    1: { name: 'B-H', sample: 'Transformer steel ring with two windings', hs: 1, hu: 'A/m', hn: 'H', ys: 1, yu: 'T', yn: 'B', hcn: 'coercive field Hc', mrn: 'remanent flux density Br', msn: 'saturation flux density Bs',
      hd: 0, yd: 3, hasArea: true, au: 'J/m³', as: 1, fixture: 'toroid', fixName: 'Ring with primary and secondary windings', gen: 'POWER OSCILLATOR 50 Hz' },
    2: { name: 'P-E', sample: V_.sample || 'Barium titanate ceramic disc with silver electrodes', hs: 1e-5, hu: 'kV/cm', hn: 'E', ys: 100, yu: 'µC/cm²', yn: 'P', hcn: 'coercive field Ec', mrn: 'remanent polarisation Pr', msn: 'saturation polarisation Ps',
      hd: 2, yd: 2, hasArea: true, au: 'J/m³', as: 1, fixture: 'disc', fixName: 'Ceramic disc in a guarded holder', gen: 'HIGH-VOLTAGE AMPLIFIER 50 Hz' },
    3: { name: 'M-H', sample: V_.sample || 'Magnetite nanoparticle powder', hs: 1e-3, hu: 'kA/m', hn: 'H', ys: 1, yu: 'A m²/kg', yn: 'M', hcn: 'coercive field Hc', mrn: 'remanent magnetisation Mr', msn: 'saturation magnetisation Ms',
      hd: 1, yd: 1, hasArea: false, fixture: 'vsm', fixName: 'Powder holder on the vibrating rod', gen: 'MAGNET POWER SUPPLY · SWEEP' }
  }[KIND];
  var HC = p.Hc, H0LO = HC * 0.3, H0HI = HC * 8;
  var st = { mounted: false, on: false, H0: HC * 4, cap: null, shown: p.H0 };
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }

  // ---------- the loop, found by searching the traced points
  function trace(h0) {
    var q = assign(p, { H0: h0 }), n = 400, hs = [], up = [], dn = [], i;
    for (i = 0; i <= n; i++) { var h = -h0 + 2 * h0 * i / n; hs.push(h); up.push(KN.m(h, 1, q)); dn.push(KN.m(h, -1, q)); }
    return { h0: h0, hs: hs, up: up, dn: dn };
  }
  function analyse(tr) {
    var n = tr.hs.length - 1, i, hc = 0, area = 0, mid = Math.round(n / 2), hcA = 0;
    for (i = 0; i < n; i++) if (tr.dn[i] < 0 && tr.dn[i + 1] >= 0) { hc = -(tr.hs[i] + (tr.hs[i + 1] - tr.hs[i]) * tr.dn[i] / (tr.dn[i] - tr.dn[i + 1])); break; }
    for (i = 0; i < n; i++) if (tr.up[i] < 0 && tr.up[i + 1] >= 0) { hcA = tr.hs[i] + (tr.hs[i + 1] - tr.hs[i]) * (0 - tr.up[i]) / (tr.up[i + 1] - tr.up[i]); break; }
    for (i = 0; i < n; i++) area += 0.5 * ((tr.dn[i] - tr.up[i]) + (tr.dn[i + 1] - tr.up[i + 1])) * (tr.hs[i + 1] - tr.hs[i]);
    return { Hc: (hc + hcA) / 2, Mr: tr.dn[mid], Ms: tr.up[n], area: area };
  }

  // ================================================================ the oscilloscope
  var scopeG = new T.Group(); S.scene.add(scopeG); scopeG.position.set(0.3, 0, -0.1); scopeG.rotation.y = -0.28;
  var cs = S.rounded(0.26, 0.2, 0.2, 0.01, new T.MeshStandardMaterial({ color: 0xcfcbbf, roughness: 0.5 })); cs.rotation.x = -Math.PI / 2; cs.position.y = 0.103; scopeG.add(cs);
  var scrTex = S.liveTex(640, 480), scrBez = mk(scopeG, box(0.2, 0.15, 0.004), M.grey, -0.012, 0.12, 0.1005);
  var scr = new T.Mesh(new T.PlaneGeometry(0.19, 0.14), new T.MeshBasicMaterial({ map: scrTex, toneMapped: false })); scr.position.set(-0.012, 0.12, 0.1035); scopeG.add(scr);
  var scopeKnob = new T.Group(); scopeKnob.position.set(0.1, 0.17, 0.1035); scopeG.add(scopeKnob);
  var skm = mk(scopeKnob, cyl(0.011, 0.012, 0.012, 24), M.bakelite); skm.rotation.x = Math.PI / 2;
  var skp = mk(scopeKnob, box(0.0018, 0.011, 0.001), M.white, 0, 0.006, 0.007);
  for (var kb = 0; kb < 3; kb++) { var kk = mk(scopeG, cyl(0.007, 0.008, 0.01, 18), M.bakelite, 0.1, 0.12 - kb * 0.03, 0.1035); kk.rotation.x = Math.PI / 2; }
  var scl = S.label('OSCILLOSCOPE · X-Y', { w: 0.1, ratio: 0.14, color: '#20252b' }); scl.position.set(-0.012, 0.035, 0.1035); scopeG.add(scl);
  S.contact(0.32, 0.26, 0.3, -0.1, 0.5);
  var lastKey = '';
  function drawScope(tr, an, live) {
    var key = (tr ? tr.h0 : 0) + '|' + (an ? 1 : 0) + '|' + st.on + '|' + live; if (key === lastKey) return; lastKey = key;
    scrTex.draw(function (x, w, h) {
      x.fillStyle = '#06130a'; x.fillRect(0, 0, w, h);
      x.strokeStyle = 'rgba(80,220,120,.22)'; x.lineWidth = 1;
      for (var i = 1; i < 10; i++) { x.beginPath(); x.moveTo(i * w / 10, 0); x.lineTo(i * w / 10, h); x.stroke(); }
      for (var j = 1; j < 8; j++) { x.beginPath(); x.moveTo(0, j * h / 8); x.lineTo(w, j * h / 8); x.stroke(); }
      x.strokeStyle = 'rgba(80,220,120,.55)'; x.lineWidth = 2; x.beginPath(); x.moveTo(0, h / 2); x.lineTo(w, h / 2); x.moveTo(w / 2, 0); x.lineTo(w / 2, h); x.stroke();
      if (!st.on || !tr) { x.fillStyle = 'rgba(80,220,120,.5)'; x.font = '600 26px "JetBrains Mono", monospace'; x.fillText(st.on ? 'no signal' : 'scope off', 24, 44); return; }
      var hx = Math.max(tr.h0, HC * 1.2) * 1.15, my = Math.max(p.Ms, 1e-12) * 1.2;
      function X(v) { return w / 2 + v / hx * (w / 2 - 20); }
      function Y(v) { return h / 2 - v / my * (h / 2 - 20); }
      x.strokeStyle = '#6dff9a'; x.lineWidth = 3; x.shadowColor = '#6dff9a'; x.shadowBlur = 8;
      x.beginPath(); tr.hs.forEach(function (hh, k) { if (k) x.lineTo(X(hh), Y(tr.up[k])); else x.moveTo(X(hh), Y(tr.up[k])); }); x.stroke();
      x.beginPath(); tr.hs.forEach(function (hh, k) { if (k) x.lineTo(X(hh), Y(tr.dn[k])); else x.moveTo(X(hh), Y(tr.dn[k])); }); x.stroke();
      x.shadowBlur = 0;
      if (an && !live) { x.fillStyle = '#ffd24a'; x.strokeStyle = '#ffd24a'; x.lineWidth = 2;
        [[an.Hc, 0], [-an.Hc, 0], [0, an.Mr], [0, -an.Mr]].forEach(function (c) { x.beginPath(); x.arc(X(c[0]), Y(c[1]), 7, 0, Math.PI * 2); x.stroke(); });
        x.font = '600 22px "JetBrains Mono", monospace'; x.fillText('cursors on the axis crossings', 18, h - 16); }
      x.fillStyle = 'rgba(160,255,190,.85)'; x.font = '600 20px "JetBrains Mono", monospace';
      x.fillText('X: ' + (hx / (w / 2 - 20) * (w / 10) * U.hs).toPrecision(2) + ' ' + U.hu + '/div', w - 280, 28);
      x.fillText('Y: ' + (my / (h / 2 - 20) * (h / 8) * U.ys).toPrecision(2) + ' ' + U.yu + '/div', w - 280, 52);
    });
  }

  // ================================================================ the generator box and the fixture
  var genG = new T.Group(); S.scene.add(genG); genG.position.set(0.02, 0, 0.1); genG.rotation.y = -0.1;
  var gc = S.rounded(0.22, 0.15, 0.08, 0.008, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5 })); gc.rotation.x = -Math.PI / 2; gc.position.y = 0.043; genG.add(gc);
  var gtex = S.canvasTex(900, 330, function (xx, w, h) { xx.fillStyle = '#2b323d'; xx.fillRect(0, 0, w, h); xx.strokeStyle = 'rgba(255,255,255,.12)'; xx.lineWidth = 3; xx.strokeRect(8, 8, w - 16, h - 16);
    xx.fillStyle = '#f1efe8'; xx.font = '700 32px "Public Sans", sans-serif'; xx.fillText(U.gen, 24, 50); xx.font = '500 22px "Public Sans", sans-serif'; xx.fillStyle = '#c7ccd6'; xx.fillText('drive amplitude sets the peak field', 24, 86); });
  var gf = S.mesh(box(0.208, 0.068, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: gtex, roughness: 0.45 }), M.grey]); gf.position.set(0, 0.043, 0.0775); genG.add(gf);
  var genLcd = S.liveTex(512, 180), genLast = '';
  var gbz = mk(genG, box(0.1, 0.03, 0.003), M.grey, 0.04, 0.032, 0.08); var gsc = new T.Mesh(new T.PlaneGeometry(0.095, 0.026), new T.MeshBasicMaterial({ map: genLcd, toneMapped: false })); gsc.position.set(0.04, 0.032, 0.0825); genG.add(gsc);
  var genKnob = new T.Group(); genKnob.position.set(-0.07, 0.032, 0.0825); genG.add(genKnob);
  var gk = mk(genKnob, cyl(0.012, 0.013, 0.012, 28), M.bakelite); gk.rotation.x = Math.PI / 2; mk(genKnob, box(0.0018, 0.012, 0.001), M.white, 0, 0.007, 0.007);
  S.contact(0.28, 0.2, 0.02, 0.1, 0.5);
  function genShow(txt, u2) {
    if (txt + u2 === genLast) return; genLast = txt + u2;
    genLcd.draw(function (xx) { var gr = xx.createLinearGradient(0, 0, 0, 180); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); xx.fillStyle = gr; xx.fillRect(0, 0, 512, 180);
      xx.font = '700 80px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 112); xx.font = '600 32px "Public Sans", sans-serif'; xx.fillText(u2, 498, 150); });
  }

  var fixG = new T.Group(); S.scene.add(fixG); fixG.position.set(-0.32, 0, -0.12);
  var sampleG = new T.Group(); S.scene.add(sampleG);
  var PARK = new T.Vector3(-0.06, 0.012, 0.17), MOUNT;
  mk(S.scene, cyl(0.03, 0.03, 0.004, 28), M.alu, PARK.x, 0.002, PARK.z); S.contact(0.08, 0.08, PARK.x, PARK.z, 0.5);
  if (U.fixture === 'toroid') {
    mk(fixG, box(0.18, 0.012, 0.12), M.bakelite, 0, 0.006, 0);
    mk(fixG, cyl(0.004, 0.004, 0.05, 10), M.steel, 0.07, 0.035, -0.03);
    var rb = mk(fixG, box(0.04, 0.02, 0.016), new T.MeshStandardMaterial({ color: 0xe2c25f, roughness: 0.5 }), -0.06, 0.022, 0.04);
    var rl = S.label('R 10 Ω', { w: 0.03, ratio: 0.3, color: '#20252b' }); rl.rotation.x = -Math.PI / 2; rl.position.set(-0.06, 0.0325, 0.04); fixG.add(rl);
    var cap = mk(fixG, cyl(0.01, 0.01, 0.03, 20), new T.MeshStandardMaterial({ color: 0x2a4f9c, roughness: 0.4 }), 0.06, 0.027, 0.04);
    MOUNT = new T.Vector3(-0.32, 0.03, -0.12);
    var tor = S.mesh(new T.TorusGeometry(0.03, 0.011, 14, 36), new T.MeshStandardMaterial({ color: 0x4b4d52, roughness: 0.3, metalness: 0.5 })); tor.rotation.x = Math.PI / 2; sampleG.add(tor);
    for (var a = 0; a < 26; a++) { var th = a / 26 * Math.PI * 2, wc = S.mesh(new T.TorusGeometry(0.0115, 0.0008, 6, 14), a % 2 ? M.copper : new T.MeshStandardMaterial({ color: 0xb04030, roughness: 0.4 }));
      wc.position.set(Math.cos(th) * 0.03, 0, Math.sin(th) * 0.03); wc.rotation.set(0, -th, 0); sampleG.add(wc); }
  } else if (U.fixture === 'disc') {
    mk(fixG, box(0.18, 0.012, 0.12), M.bakelite, 0, 0.006, 0);
    mk(fixG, box(0.08, 0.05, 0.07), new T.MeshStandardMaterial({ color: 0x8a1f1a, roughness: 0.4 }), 0.0, 0.037, 0);
    mk(fixG, box(0.06, 0.004, 0.05), M.black, 0.0, 0.064, 0);
    mk(fixG, cyl(0.012, 0.012, 0.035, 20), new T.MeshStandardMaterial({ color: 0x2a4f9c, roughness: 0.4 }), -0.07, 0.03, 0.03);
    mk(fixG, cyl(0.004, 0.004, 0.012, 10), M.chrome, 0.07, 0.018, -0.03);
    var wl = S.label('DANGER · HIGH VOLTAGE', { w: 0.07, ratio: 0.14, color: '#fff', bg: '#a8201a' }); wl.position.set(0, 0.038, 0.0355); fixG.add(wl);
    MOUNT = new T.Vector3(-0.32, 0.0715, -0.12);
    var dsc = S.mesh(cyl(0.012, 0.012, 0.0015, 28), new T.MeshStandardMaterial({ color: 0xcfc9bb, roughness: 0.5 })); sampleG.add(dsc);
    var ag = S.mesh(cyl(0.0105, 0.0105, 0.0017, 28), new T.MeshStandardMaterial({ color: 0xd9dce0, roughness: 0.2, metalness: 1 })); ag.position.y = 0.0001; sampleG.add(ag);
  } else {
    mk(fixG, box(0.34, 0.03, 0.06), new T.MeshStandardMaterial({ color: 0x3a4249, roughness: 0.5, metalness: 0.6 }), 0, 0.2, 0);
    mk(fixG, box(0.34, 0.03, 0.06), new T.MeshStandardMaterial({ color: 0x3a4249, roughness: 0.5, metalness: 0.6 }), 0, 0.015, 0);
    mk(fixG, box(0.03, 0.2, 0.06), new T.MeshStandardMaterial({ color: 0x3a4249, roughness: 0.5, metalness: 0.6 }), -0.155, 0.11, 0);
    mk(fixG, box(0.03, 0.2, 0.06), new T.MeshStandardMaterial({ color: 0x3a4249, roughness: 0.5, metalness: 0.6 }), 0.155, 0.11, 0);
    var cl = mk(fixG, cyl(0.045, 0.045, 0.045, 28), M.copper, 0, 0.165, 0), cl2 = mk(fixG, cyl(0.045, 0.045, 0.045, 28), M.copper, 0, 0.055, 0);
    mk(fixG, cyl(0.032, 0.026, 0.03, 28), M.iron, 0, 0.13, 0); mk(fixG, cyl(0.026, 0.032, 0.03, 28), M.iron, 0, 0.09, 0);
    mk(fixG, cyl(0.003, 0.003, 0.17, 10), M.steel, 0, 0.19, 0);
    mk(fixG, cyl(0.03, 0.03, 0.03, 24), M.black, 0, 0.26, 0);
    var vl = S.label('VIBRATING SAMPLE MAGNETOMETER', { w: 0.14, ratio: 0.1, color: '#e8eaec' }); vl.position.set(0, 0.2, 0.0305); fixG.add(vl);
    MOUNT = new T.Vector3(-0.32, 0.11, -0.12);
    var vial = S.mesh(cyl(0.004, 0.004, 0.01, 12), new T.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.2, transparent: true, opacity: 0.7 })); sampleG.add(vial);
    var pw = S.mesh(cyl(0.0035, 0.0035, 0.005, 12), new T.MeshStandardMaterial({ color: 0x1c1410, roughness: 0.8 })); pw.position.y = -0.002; sampleG.add(pw);
  }
  S.contact(0.22, 0.16, -0.32, -0.12, 0.5);
  sampleG.position.copy(PARK);
  S.addApparatus('fixture', fixG, U.fixName, 'The sample and its circuit: the drive current sets the field, an integrating circuit turns the response into a voltage for the scope.');
  S.addApparatus('sample', sampleG, U.sample, 'The sample under test. Its coercive field is the hidden number you are measuring.');
  S.addApparatus('scope', scopeG, 'Oscilloscope in X-Y mode', 'Horizontal: the field. Vertical: the response (flux density, polarisation or magnetisation). The trace is the hysteresis loop.');
  S.addApparatus('gen', genG, U.gen.charAt(0) + U.gen.slice(1).toLowerCase(), 'Sets the amplitude of the drive. A weak drive gives a small loop; the true coercive field shows only once the loop is driven to saturation.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every capture you take is written here, as in a real practical file.');
  var hudH = S.hudCard('Drive amplitude'), hudL = S.hudCard('Loop');
  genShow('0', U.hu); drawScope(null, null, true);

  // ================================================================ human actions
  function mountSample() {
    if (busy() || st.mounted) return Promise.resolve();
    var a = sampleG.position.clone(), b = MOUNT.clone();
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.01, 0)), function (k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.07 * Math.sin(Math.PI * k) + (b.y - a.y) * k + 0.01, a.z + (b.z - a.z) * k); },
      function (k) { sampleG.position.set(a.x + (b.x - a.x) * k, a.y + 0.07 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); }, { mode: 'top', ms: 1300, reachMs: 650 })
      .then(function () { sampleG.position.copy(b); st.mounted = true; S.say(KIND === 1 ? 'The ring is wired into the circuit.' : KIND === 2 ? 'The disc is clamped between the electrodes in its guarded holder.' : 'The powder holder is fixed to the vibrating rod, in the gap.'); S.render(); });
  }
  function switchOn() {
    if (busy() || st.on) return Promise.resolve();
    if (!st.mounted) { S.say('Mount the sample first.'); return Promise.resolve(); }
    return S.hand.tap(scopeKnob, 'front').then(function () { st.on = true; S.say('Scope and generator are on. The loop is traced continuously at the set amplitude.'); S.click(880, 0.05); S.render(); });
  }
  function setAmp(h0) {
    if (busy()) return Promise.resolve();
    if (!(h0 >= H0LO - 1e-9 && h0 <= H0HI + 1e-9)) { S.say('The drive amplitude runs from ' + rnd(H0LO * U.hs, 2) + ' to ' + rnd(H0HI * U.hs, 1) + ' ' + U.hu + '.'); return Promise.resolve(); }
    if (!st.on) { S.say('Switch the scope on first.'); return Promise.resolve(); }
    var a = st.H0;
    return S.hand.tap(genKnob, 'front').then(function () { return S.tween(600, function (k) { st.H0 = a + (h0 - a) * k; }); })
      .then(function () { st.H0 = h0; S.say('Drive amplitude ' + rnd(h0 * U.hs, U.hd) + ' ' + U.hu + '. Watch how the loop changes.'); S.render(); });
  }
  function capture() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (!st.on) { S.say('Switch the scope on first.'); return null; }
    for (var i = 0; i < S.rows.length; i++) if (Math.abs(S.rows[i].h0 - st.H0) < 1e-9 * Math.max(1, st.H0)) { S.say('You already captured this amplitude. Change the drive first.'); return null; }
    var tr = trace(st.H0), an = analyse(tr), row = { h0: st.H0, Hc: an.Hc, Mr: an.Mr, Ms: an.Ms, area: an.area };
    st.cap = { tr: tr, an: an }; drawScope(tr, an, false); lastKey = '';
    S.addRow(row);
    S.say('Captured: ' + rnd(an.Hc * U.hs, U.hd + 1) + ' ' + U.hu + ' where the loop cuts the field axis, ' + rnd(an.Mr * U.ys, U.yd) + ' ' + U.yu + ' where it cuts the vertical axis.');
    return row;
  }

  function result(rows) {
    if (rows.length < 4) return null;
    var r = rows.slice().sort(function (a, b) { return a.h0 - b.h0; }), top = r[r.length - 1], prev = r[r.length - 2];
    if (Math.abs(top.Hc - prev.Hc) > 0.03 * top.Hc) return null;                  // the two largest loops must agree: the loop has stopped growing
    return { label: U.hcn.charAt(0).toUpperCase() + U.hcn.slice(1), value: top.Hc * U.hs, unit: U.hu, digits: U.hd + 1, truth: p.Hc * U.hs,
      note: 'Taken from the saturated loop (drive ' + rnd(top.h0 * U.hs, U.hd) + ' ' + U.hu + '): the loop cuts the field axis at ±' + rnd(top.Hc * U.hs, U.hd + 1) + ' ' + U.hu + '. ' + U.mrn.charAt(0).toUpperCase() + U.mrn.slice(1) + ' ' + rnd(top.Mr * U.ys, U.yd) + ' ' + U.yu + ', ' + U.msn + ' ' + rnd(top.Ms * U.ys, U.yd) + ' ' + U.yu + (U.hasArea ? ', and the loop area is ' + rnd(top.area, 1) + ' ' + U.au + ' per cycle.' : '.') +
        ' Smaller drives gave narrower loops whose crossing is not the material\'s own.' };
  }

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { fixture: [[-0.3, 0.3, 0.38], [-0.32, 0.1, -0.12]], sample: [[-0.12, 0.22, 0.34], [-0.1, 0.03, 0.12]], scope: [[0.34, 0.24, 0.3], [0.3, 0.12, -0.1]],
      gen: [[0.02, 0.2, 0.36], [0.02, 0.04, 0.1]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: 'loop area = ∮ ' + U.yn + ' d' + U.hn + ',   ' + U.hn + 'c: ' + U.yn + ' = 0',
      formulaNote: 'the area is the energy lost per cycle per unit volume' + (U.hasArea ? '' : ' (a magnetometer reports magnetisation per kilogram, so here it is only a measure of the loss)'),
      more: ['The loop is traced at the drive frequency. The coercive field is where it cuts the field axis, the remanence where it cuts the vertical axis.',
        'A loop that has not reached saturation is narrower. The value to quote is from a loop driven well past the point where it stops growing.',
        'This bench simulates a loop with the ' + (V_.source ? 'sample "' + (V_.sample || U.sample) + '"' : 'lab\'s own illustrative sample') + '; the hidden coercive field is the lab\'s own value.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Sample: ' + U.sample, U.hn + ' on the X axis, ' + U.yn + ' on the Y axis.'],
      columns: [{ label: 'drive (' + U.hu + ')', get: function (r) { return (r.h0 * U.hs).toFixed(U.hd); } }, { label: U.hn + 'c (' + U.hu + ')', get: function (r) { return (r.Hc * U.hs).toFixed(U.hd + 1); } },
        { label: U.yn + 'r (' + U.yu + ')', get: function (r) { return (r.Mr * U.ys).toFixed(U.yd); } }, { label: U.yn + 's (' + U.yu + ')', get: function (r) { return (r.Ms * U.ys).toFixed(U.yd); } }]
        .concat(U.hasArea ? [{ label: 'area (' + U.au + ')', get: function (r) { return r.area.toFixed(1); } }] : []) },
    graph: { x: function (r) { return r.h0 * U.hs; }, y: function (r) { return r.Hc * U.hs; }, xlabel: 'drive amplitude (' + U.hu + ')', ylabel: U.hn + 'c read (' + U.hu + ')', line: function () { return null; } },
    result: result,
    tol: 0.02,
    resultNote: 'The coercive field is a property of the material only once the loop is saturated; the smaller loops show how an under-driven sample would have misled you.',
    chips: ['Why does a weak drive give a smaller coercive field?', 'What does the area of the loop mean?', 'Check my readings', 'Soft and hard magnets: what is the difference?'],
    viva: [],
    askState: function () {
      var cur = trace(st.H0), an = analyse(cur);
      return { experiment: S.lab.title, sample: U.sample, mounted: st.mounted, scope_on: st.on, drive_amplitude: rnd(st.H0 * U.hs, U.hd) + ' ' + U.hu,
        loop_cuts_field_axis_at: rnd(an.Hc * U.hs, U.hd + 1) + ' ' + U.hu, captures_taken: S.rows.length };
    },
    steps: [
      { id: 'setup', title: 'Set up', view: 'fixture', render: function (u) {
          u.h2('Mount the sample, switch the scope on');
          u.p('The sample is on its tray: ' + U.sample.toLowerCase() + '. Mount it, then switch the scope and generator on.');
          u.task('1. Mount the sample', st.mounted, st.mounted ? 'In place' : 'Still on the tray').add(u.button(st.mounted ? 'Mounted' : 'Mount the sample', function () { S.focus('fixture'); mountSample(); }, !st.mounted, st.mounted || S.hand.busy));
          u.task('2. Switch on', st.on, st.on ? 'Tracing' : 'Off').add(u.button(st.on ? 'Switched on' : 'Switch the scope on', function () { S.focus('scope'); switchOn(); }, !st.on && st.mounted, st.on || !st.mounted || S.hand.busy));
          u.next('Next: trace the loops', st.mounted && st.on);
        },
        ok: function () { return st.mounted && st.on; }, auto: function () { return mountSample().then(switchOn); } },
      { id: 'loops', title: 'Drive and capture', view: 'scope', render: function (u) {
          u.h2('Drive harder and harder, capture each loop');
          u.p('Raise the drive amplitude in steps and capture the loop at each. The loop grows and then stops growing: that is saturation. The cursors sit where it cuts the axes.');
          var tg = { v: Math.max(H0LO, Math.min(H0HI, st.H0)) };
          u.slider('Drive amplitude', H0LO * U.hs, H0HI * U.hs, (H0HI - H0LO) * U.hs / 120, function () { return tg.v * U.hs; }, function (v) { tg.v = v / U.hs; }, U.hu, U.hd + 1);
          u.row(u.button('Set the amplitude', function () { S.focus('gen'); setAmp(tg.v); }, true, S.hand.busy), u.button('Capture the loop', function () { capture(); }, false, S.hand.busy));
          u.live(function () { var an = analyse(trace(st.H0)); return 'Drive ' + rnd(st.H0 * U.hs, U.hd) + ' ' + U.hu + '  ·  cuts the field axis at ±' + rnd(an.Hc * U.hs, U.hd + 1) + ' ' + U.hu; });
          u.h3('Captures'); u.table();
          if (S.rows.length < 4) u.p(S.rows.length + ' of at least 4 captures taken (include a drive above three times the coercive field).');
          u.next('Next: the result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () { return [0.5, 1, 2, 6].reduce(function (pr, m) { return pr.then(function () { return setAmp(HC * m); }).then(function () { capture(); }); }, Promise.resolve()); } }
    ],
    tick: function () {
      genShow(st.on ? rnd(st.H0 * U.hs, U.hd).toFixed(U.hd) : '0', U.hu);
      if (st.on && st.mounted) { var tr = (st.cap && Math.abs(st.cap.tr.h0 - st.H0) < 1e-9 * st.H0) ? st.cap.tr : trace(st.H0); drawScope(tr, st.cap && st.cap.tr === tr ? st.cap.an : null, !(st.cap && st.cap.tr === tr)); }
      else drawScope(null, null, true);
      hudH.set(st.on ? rnd(st.H0 * U.hs, U.hd) + ' ' + U.hu : '—'); hudL.set(st.on ? U.hn + 'c ' + rnd(analyse(trace(st.H0)).Hc * U.hs, U.hd + 1) + ' ' + U.hu : '—');
    },
  };
});
