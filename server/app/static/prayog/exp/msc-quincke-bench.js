/* Prayogshala studio module: QUINCKE SUSCEPTIBILITY BENCH.
   A U-tube of liquid with its narrow limb between the pole pieces of an electromagnet and a travelling microscope
   focused on the meniscus. The `msc_quincke` kernel (packs/msc_solid.js) gives the rise h = chi B^2 / (2 mu0 rho g) of a
   liquid of volume susceptibility chi, with chi = chi(water) + 4 pi chim c / 1000 for a salt of molar susceptibility chim
   at molarity c. The student raises the field, reads the meniscus with the microscope and the field with a gaussmeter,
   plots h against B^2 and finds chi - and, for a salt, the molar susceptibility. Water alone gives its diamagnetism. */
HoolaStudio.define('msc-quincke-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.msc_quincke, assign = HK.assign;
  var p = HK.paramsFor('msc_quincke', S.lab.params);
  var V_ = S.lab.variant || {};
  var SAMPLE = V_.sample || '1.0 M manganese(II) sulphate solution';
  var SALT = p.c > 0, MU0 = 1.25663706212e-6, G = 9.80665, Z0 = 34.56, IMAX = 2.0;
  var st = { mounted: false, on: false, I: 0, settling: false };
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 24); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function q(I) { return assign(p, { I: I }); }
  function Bof(I) { return rnd(KN.view({}, q(I)).B, 3); }               // the gaussmeter, 1 mT
  function hmm(I) { return KN.view({}, q(I)).h_mm; }
  function zread(I) { return rnd(Z0 + hmm(I), 2); }                     // the microscope's vertical scale, 0.01 mm

  var CX = -0.3, CZ = -0.14;
  var mag = new T.Group(); S.scene.add(mag); mag.position.set(CX, 0, CZ);
  var yoke = new T.MeshStandardMaterial({ color: 0x3a4249, roughness: 0.5, metalness: 0.6 });
  mk(mag, box(0.3, 0.03, 0.07), yoke, 0, 0.215, 0); mk(mag, box(0.3, 0.03, 0.07), yoke, 0, 0.015, 0);
  mk(mag, box(0.03, 0.2, 0.07), yoke, -0.135, 0.115, 0); mk(mag, box(0.03, 0.2, 0.07), yoke, 0.135, 0.115, 0);
  var gapY = 0.115;
  mk(mag, cyl(0.036, 0.03, 0.04, 36), M.iron, 0, 0.18, 0); mk(mag, cyl(0.03, 0.036, 0.04, 36), M.iron, 0, 0.05, 0);
  var coilM = new T.MeshStandardMaterial({ color: 0xc8764a, roughness: 0.35, metalness: 0.9 });
  mk(mag, cyl(0.052, 0.052, 0.05, 36), coilM, 0, 0.19, 0); mk(mag, cyl(0.052, 0.052, 0.05, 36), coilM, 0, 0.04, 0);
  var ml = S.label('ELECTROMAGNET', { w: 0.1, ratio: 0.14, color: '#e8eaec' }); ml.position.set(0, 0.215, 0.0355); mag.add(ml);
  S.contact(0.34, 0.14, CX, CZ, 0.55);

  // the U-tube: a narrow limb in the gap and a wide reservoir limb beside the magnet
  var tube = new T.Group(); S.scene.add(tube);
  var glassM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, transmission: 0.6, thickness: 0.002, transparent: true, opacity: 0.55 });
  var liqCol = !SALT ? 0xbfe3ee : (/iron|FeCl|ferric/i.test(SAMPLE) ? 0xc98a2a : 0xe8b4c2);
  var liqM = new T.MeshStandardMaterial({ color: liqCol, roughness: 0.15, transparent: true, opacity: 0.95, emissive: liqCol, emissiveIntensity: 0.18 });
  mk(tube, cyl(0.0045, 0.0045, 0.19, 18), glassM, 0, 0.095, 0); mk(tube, cyl(0.017, 0.017, 0.12, 24), glassM, 0.1, 0.06, 0);
  var link = mk(tube, cyl(0.0045, 0.0045, 0.1, 14), glassM, 0.05, 0.003, 0); link.rotation.z = Math.PI / 2;
  mk(tube, box(0.14, 0.006, 0.05), M.wood, 0.05, -0.003, 0);
  var limbL = mk(tube, cyl(0.0036, 0.0036, 1, 16), liqM, 0, 0.05, 0), res = mk(tube, cyl(0.0155, 0.0155, 1, 24), liqM, 0.1, 0.03, 0);
  var base = mk(tube, cyl(0.0036, 0.0036, 0.006, 16), liqM, 0, 0.003, 0); link.material = glassM;
  var LEVEL0 = 0.115;                                                       // meniscus midway between the pole faces, magnet off
  var PARK = new T.Vector3(-0.24, 0.006, 0.15), MOUNT = new T.Vector3(CX, 0.0, CZ);
  tube.position.copy(PARK); S.contact(0.18, 0.08, PARK.x + 0.05, PARK.z, 0.45);
  function setLevels(hm) {
    var lv = LEVEL0 + hm / 1000 * 3;                                           // the rise is drawn three times larger so it can be seen
    limbL.scale.y = Math.max(lv, 0.01); limbL.position.y = lv / 2 + 0.006; res.scale.y = 0.06; res.position.y = 0.036;
  }
  setLevels(0);

  // the travelling microscope: a stand, a vertical slide with a scale, and the horizontal telescope
  var scopeG = new T.Group(); S.scene.add(scopeG); scopeG.position.set(CX, 0, CZ + 0.17);
  mk(scopeG, box(0.12, 0.012, 0.08), M.iron, 0, 0.006, 0); mk(scopeG, cyl(0.007, 0.007, 0.26, 16), M.chrome, -0.04, 0.14, 0);
  var slide = new T.Group(); scopeG.add(slide);
  mk(slide, box(0.03, 0.03, 0.03), M.alu, -0.04, 0, 0);
  var tel = mk(slide, cyl(0.011, 0.011, 0.12, 22), new T.MeshStandardMaterial({ color: 0x20262e, roughness: 0.4, metalness: 0.5 }), -0.0, 0, -0.04); tel.rotation.x = Math.PI / 2;
  var eye = mk(slide, cyl(0.008, 0.008, 0.03, 18), M.black, 0, 0, 0.03); eye.rotation.x = Math.PI / 2;
  var obj = mk(slide, cyl(0.0125, 0.0125, 0.014, 22), M.chrome, 0, 0, -0.11); obj.rotation.x = Math.PI / 2;
  var scaleTex = S.liveTex(256, 96), sbez = mk(scopeG, box(0.07, 0.03, 0.004), M.grey, 0.02, 0.05, 0.036);
  var sscr = new T.Mesh(new T.PlaneGeometry(0.064, 0.024), new T.MeshBasicMaterial({ map: scaleTex, toneMapped: false })); sscr.position.set(0.02, 0.05, 0.0385); scopeG.add(sscr);
  S.contact(0.16, 0.12, CX, CZ + 0.17, 0.5);
  var lastZ = '';
  function showZ(txt) { if (txt === lastZ) return; lastZ = txt;
    scaleTex.draw(function (x, w, h) { var gr = x.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); x.fillStyle = gr; x.fillRect(0, 0, w, h);
      x.font = '700 52px "JetBrains Mono", monospace'; x.textAlign = 'right'; x.fillStyle = '#1b2116'; x.fillText(txt, w - 56, 62); x.font = '600 24px "Public Sans", sans-serif'; x.fillText('mm', w - 10, 84); }); }
  showZ('----');

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
        xx.font = '700 92px "JetBrains Mono", monospace'; xx.textAlign = 'right'; xx.fillStyle = '#1b2116'; xx.fillText(txt, 400, 118); xx.font = '600 34px "Public Sans", sans-serif'; xx.fillText(u2, 496, 150); }); } };
  }
  var supply = instBox(0.0, 0.1, -0.1, 'MAGNET POWER SUPPLY', '0 – 2 A  ·  sets the coil current', 0.22);
  var gauss = instBox(0.3, -0.06, -0.35, 'DIGITAL GAUSSMETER', 'field in the gap, in tesla', 0.2);
  supply.show('0.00', 'A'); gauss.show('0.000', 'T');
  S.wire([[-0.3, 0.2, -0.1], [-0.14, 0.03, 0.0], [-0.04, 0.03, 0.06]], 'red');
  S.wire([[-0.26, 0.2, -0.1], [-0.1, 0.028, 0.02], [0.04, 0.03, 0.06]], 'black');
  S.addApparatus('mag', mag, 'Electromagnet', 'An iron yoke with two coils and flat pole pieces about 20 mm apart. The field in the gap follows the coil current and is measured by the gaussmeter.');
  S.addApparatus('tube', tube, 'U-tube with ' + SAMPLE, 'A narrow limb goes between the pole pieces; the wide limb outside acts as a reservoir whose level does not change. Only the narrow limb\'s meniscus moves.');
  S.addApparatus('scope', scopeG, 'Travelling microscope', 'Focused on the meniscus in the narrow limb. Its vertical scale reads to 0.01 mm.');
  S.addApparatus('supply', supply.group, 'Magnet power supply', 'Sets the coil current and so the field. The coils warm up: do not leave it at full current.');
  S.addApparatus('gauss', gauss.group, 'Digital gaussmeter', 'Reads the field where the liquid is, in tesla; the field is calibrated against the current, never assumed.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudB = S.hudCard('Field in the gap'), hudZ = S.hudCard('Meniscus reading');

  function mountTube() {
    if (busy() || st.mounted) return Promise.resolve();
    var a = tube.position.clone(), b = MOUNT.clone();
    return S.hand.pinchMove(a.clone().add(new T.Vector3(0, 0.1, 0)), function (k) { return new T.Vector3(a.x + (b.x - a.x) * k, a.y + 0.06 * Math.sin(Math.PI * k) + (b.y - a.y) * k + 0.1, a.z + (b.z - a.z) * k); },
      function (k) { tube.position.set(a.x + (b.x - a.x) * k, a.y + 0.06 * Math.sin(Math.PI * k) + (b.y - a.y) * k, a.z + (b.z - a.z) * k); }, { mode: 'top', ms: 1400, reachMs: 650 })
      .then(function () { tube.position.copy(b); st.mounted = true; S.say('The narrow limb is between the pole pieces, with its meniscus midway between the faces. The microscope is focused on it.'); S.render(); });
  }
  function switchOn() {
    if (busy() || st.on) return Promise.resolve();
    if (!st.mounted) { S.say('Mount the U-tube first.'); return Promise.resolve(); }
    return S.hand.tap(supply.knob, 'front').then(function () { st.on = true; S.say('The magnet supply is on, at zero current. Read the meniscus with no field first.'); S.click(880, 0.05); S.render(); });
  }
  function setCurrent(I) {
    if (busy()) return Promise.resolve();
    if (!(I >= -1e-9 && I <= IMAX + 1e-9)) { S.say('The supply runs from 0 to ' + IMAX + ' A.'); return Promise.resolve(); }
    if (!st.on) { S.say('Switch the magnet supply on first.'); return Promise.resolve(); }
    var a = st.I; st.settling = true;
    return S.hand.tap(supply.knob, 'front').then(function () { return S.tween(500 + 800 * Math.abs(I - a) / IMAX, function (k) { st.I = a + (I - a) * k; }); })
      .then(function () { st.I = I; st.settling = false; S.say('Current ' + I.toFixed(2) + ' A, field ' + Bof(I).toFixed(3) + ' T. Wait for the meniscus to stop moving, then read.'); S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return null; }
    if (!st.on) { S.say('Switch the magnet supply on first.'); return null; }
    if (st.settling) { S.say('Wait for the meniscus to settle.'); return null; }
    for (var i = 0; i < S.rows.length; i++) if (Math.abs(S.rows[i].I - st.I) < 1e-6) { S.say('You already have a reading at this current.'); return null; }
    var B = Bof(st.I), z = zread(st.I), z0 = S.rows.length && S.rows[0].I === 0 ? S.rows[0].z : (st.I === 0 ? z : null);
    var row = { I: rnd(st.I, 2), B: B, B2: B * B, z: z, h: z0 === null ? 0 : rnd(z - z0, 2) };
    if (st.I !== 0 && z0 === null) { S.say('Read the meniscus with the current at zero first: that is the zero of the rise.'); return null; }
    S.addRow(row);
    S.say('Written in your record book: ' + row.I.toFixed(2) + ' A, ' + B.toFixed(3) + ' T, meniscus ' + z.toFixed(2) + ' mm, rise ' + row.h.toFixed(2) + ' mm.');
    return row;
  }
  function result(rows) {
    var pts = rows.filter(function (r) { return r.B2 > 0; }).map(function (r) { return [r.B2, r.h / 1000]; });
    if (rows.length < 6 || pts.length < 5) return null;
    var f = S.fit.linear(pts); if (!f) return null;
    var chi = 2 * MU0 * p.rho * G * f.m;
    if (SALT) {
      return { label: 'Molar susceptibility of the salt', value: (chi - p.chiw) * 1000 / (4 * Math.PI * p.c) * 1e6, unit: '× 10⁻⁶ cm³/mol', digits: 0, truth: p.chim,
        note: 'Slope of h against B² is ' + f.m.toFixed(5) + ' m/T², so χ(solution) = 2 μ₀ ρ g × slope = ' + chi.toExponential(3) + '. Subtracting the water\'s χ = ' + p.chiw.toExponential(2) + ' and dividing by 4π c / 1000 gives the molar susceptibility in cgs units.' };
    }
    return { label: 'Volume susceptibility of water', value: chi * 1e6, unit: '× 10⁻⁶ (SI)', digits: 2, truth: p.chiw * 1e6,
      note: 'The slope of h against B² is negative (' + f.m.toFixed(6) + ' m/T²): the water is pushed out of the field. χ = 2 μ₀ ρ g × slope.' };
  }

  return {
    camera: { pos: [-0.04, 0.92, 1.1], look: [-0.06, 0.08, -0.06] },
    views: { mag: [[-0.3, 0.3, 0.25], [-0.3, 0.11, -0.14]], tube: [[-0.1, 0.22, 0.3], [-0.03, 0.06, 0.12]], scope: [[-0.2, 0.2, 0.34], [-0.3, 0.1, 0.03]], supply: [[0.0, 0.26, 0.32], [0.0, 0.05, 0.1]],
      gauss: [[0.3, 0.24, 0.16], [0.3, 0.05, -0.06]], bench: [[-0.04, 0.92, 1.1], [-0.06, 0.08, -0.06]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: S.lab.theory,
      formula: 'h = χ B² / (2 μ₀ ρ g),   χ = χ(water) + 4π χm c / 1000',
      formulaNote: 'h in metres, B in tesla, ρ the density of the liquid; χm in cm³/mol (cgs) and c in mol/L',
      more: ['The meniscus is read with the field off first; every rise is measured from that zero.', 'Plot h against B²: a straight line through the origin. A paramagnetic liquid rises (positive slope), a diamagnetic one falls.',
        'The field is read by a gaussmeter in the same gap, not worked out from the current.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 110) + (S.lab.aim.length > 110 ? '…' : ''), 'Liquid: ' + SAMPLE + ', density ' + p.rho.toFixed(0) + ' kg/m³' + (SALT ? ', ' + p.c.toFixed(1) + ' mol/L.' : '.'), 'Water: χ = −9.05 × 10⁻⁶ (SI).'],
      columns: [{ label: 'I (A)', get: function (r) { return r.I.toFixed(2); } }, { label: 'B (T)', get: function (r) { return r.B.toFixed(3); } }, { label: 'B² (T²)', get: function (r) { return r.B2.toFixed(4); } },
        { label: 'z (mm)', get: function (r) { return r.z.toFixed(2); } }, { label: 'h (mm)', get: function (r) { return r.h.toFixed(2); } }] },
    graph: { x: function (r) { return r.B2; }, y: function (r) { return r.h; }, xlabel: 'B² (T²)', ylabel: 'rise h (mm)', line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.03,
    resultNote: 'The susceptibility came from the slope of your own graph; the lab\'s true value is shown for comparison.',
    chips: ['Why does a paramagnetic liquid rise?', 'Why plot h against B squared?', 'Check my readings', 'What are the sources of error?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, liquid: SAMPLE, mounted: st.mounted, supply_on: st.on, current_A: rnd(st.I, 2), field_T: st.on ? Bof(st.I) : 0, readings_taken: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Mount the tube', view: 'tube', render: function (u) {
          u.h2('Mount the U-tube in the gap');
          u.p('The U-tube holds ' + SAMPLE + '. Put the narrow limb between the pole pieces so its meniscus is midway between the faces, then switch the magnet supply on.');
          u.task('1. Mount the tube', st.mounted, st.mounted ? 'In the gap' : 'On the bench').add(u.button(st.mounted ? 'Mounted' : 'Mount the tube', function () { S.focus('tube'); mountTube(); }, !st.mounted, st.mounted || S.hand.busy));
          u.task('2. Switch the supply on', st.on, st.on ? 'On, 0 A' : 'Off').add(u.button(st.on ? 'On' : 'Switch it on', function () { S.focus('supply'); switchOn(); }, !st.on && st.mounted, st.on || !st.mounted || S.hand.busy));
          u.next('Next: raise the field', st.mounted && st.on);
        },
        ok: function () { return st.mounted && st.on; }, auto: function () { return mountTube().then(switchOn); } },
      { id: 'rise', title: 'Field and meniscus', view: 'scope', render: function (u) {
          u.h2('Raise the field, read the meniscus');
          u.p('First read the meniscus with the current at zero. Then raise the current in steps of 0.25 A; at each, read the gaussmeter and the microscope once the meniscus is still. The rise is the change from the zero reading.');
          var tg = { v: st.I };
          u.slider('Magnet current', 0, IMAX, 0.05, function () { return tg.v; }, function (v) { tg.v = v; }, 'A', 2);
          u.row(u.button('Set the current', function () { S.focus('supply'); setCurrent(tg.v); }, true, S.hand.busy), u.button('Record', function () { S.focus('scope'); record(); }, false, S.hand.busy));
          u.live(function () { return st.on ? st.I.toFixed(2) + ' A  ·  ' + Bof(st.I).toFixed(3) + ' T  ·  meniscus ' + zread(st.I).toFixed(2) + ' mm' : 'Supply off'; });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 6) u.p(S.rows.length + ' of at least 6 readings taken (the first at zero current).');
          u.next('Next: the result', S.rows.length >= 6);
        },
        ok: function () { return S.rows.length >= 6; },
        auto: function () { return [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0].reduce(function (pr, I) { return pr.then(function () { return setCurrent(I); }).then(function () { record(); }); }, Promise.resolve()); } }
    ],
    tick: function () {
      var h = st.on && st.mounted ? hmm(st.I) : 0; setLevels(h);
      supply.show(st.on ? st.I.toFixed(2) : '0.00', 'A'); gauss.show(st.on ? Bof(st.I).toFixed(3) : '0.000', 'T');
      showZ(st.on && st.mounted ? zread(st.I).toFixed(2) : '----');
      slide.position.y = LEVEL0 + h / 1000 * 3 + 0.0; hudB.set(st.on ? Bof(st.I).toFixed(3) + ' T' : '—'); hudZ.set(st.on && st.mounted ? zread(st.I).toFixed(2) + ' mm' : '—');
    },
  };
});
