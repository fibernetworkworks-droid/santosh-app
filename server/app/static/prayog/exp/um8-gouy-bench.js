/* Prayogshala studio RIG: the GOUY BALANCE of wave 8 (B.Sc. solid state physics).
   An analytical balance on a shelf over an electromagnet; a long glass tube of the powdered salt hangs from the
   balance's lower hook with its bottom end between the pole pieces. A gaussmeter reads the field in the gap and the
   magnet supply sets the coil current. Physics: the um8_gouy kernel (packs/ug_matter_w8.js) - the same code the
   server checks: dm = (chi_v - chi_air) A B^2 / (2 mu0 g). SIMULATED DATA. */
HoolaStudio.define('um8-gouy-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.um8_gouy, assign = HK.assign;
  var p = HK.paramsFor('um8_gouy', S.lab.params);
  var V_ = S.lab.variant || {};
  var SALT = V_.sample || 'Copper(II) sulphate pentahydrate (CuSO4.5H2O) powder';
  var COL = /Mn/.test(SALT) ? 0xf1d9de : /Fe/.test(SALT) ? 0xc9e2b8 : 0x3d7ed8;
  var st = { hung: false, I: 0, m0: null, last: null };
  var MU0 = 1.25663706212e-6;

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function q() { return assign(p, { I: st.I }); }
  function readB() { return Math.round(KN.field(q()) * 1000) / 1000; }
  function readM() { var v = st.hung ? KN.view({}, q()).m * 1000 : 0; return Math.round(v * 1e4) / 1e4; }   // g to 0.1 mg
  function fmt(v, d) { return isFinite(v) ? v.toFixed(d) : '—'; }

  // ================================================================ electromagnet
  var mag = new T.Group(); S.scene.add(mag); mag.position.set(-0.1, 0, -0.14);
  var iron = new T.MeshStandardMaterial({ color: 0x3b4048, roughness: 0.55, metalness: 0.6 });
  var base = S.rounded(0.34, 0.03, 0.14, 0.006, iron); base.position.y = 0.015; mag.add(base);
  [-1, 1].forEach(function (sg) {
    var arm = S.rounded(0.04, 0.16, 0.12, 0.006, iron); arm.position.set(sg * 0.15, 0.11, 0); mag.add(arm);
    var coil = S.mesh(new T.CylinderGeometry(0.045, 0.045, 0.07, 32), M.copper); coil.rotation.z = Math.PI / 2; coil.position.set(sg * 0.095, 0.13, 0); mag.add(coil);
    var core = S.mesh(new T.CylinderGeometry(0.025, 0.025, 0.1, 24), iron); core.rotation.z = Math.PI / 2; core.position.set(sg * 0.085, 0.13, 0); mag.add(core);
    var pole = S.mesh(new T.CylinderGeometry(0.03, 0.022, 0.025, 28), iron); pole.rotation.z = sg * Math.PI / 2; pole.position.set(sg * 0.027, 0.13, 0); mag.add(pole);
  });
  S.contact(0.4, 0.2, -0.1, -0.14, 0.55);
  // the stand and shelf carrying the balance
  var shelfY = 0.36;
  [-0.27, 0.07].forEach(function (x) { var leg = S.mesh(new T.CylinderGeometry(0.008, 0.008, shelfY, 12), M.chrome); leg.position.set(x, shelfY / 2, -0.14); S.scene.add(leg); });
  var shelf = S.rounded(0.4, 0.016, 0.22, 0.006, M.wood); shelf.position.set(-0.1, shelfY + 0.008, -0.14); S.scene.add(shelf);
  var hole = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.018, 16), new T.MeshStandardMaterial({ color: 0x111111 })); hole.position.set(-0.1, shelfY + 0.008, -0.14); S.scene.add(hole);
  var bal = new T.Group(); S.scene.add(bal); bal.position.set(-0.1, shelfY + 0.016, -0.14);
  var bb = S.rounded(0.22, 0.05, 0.2, 0.01, new T.MeshStandardMaterial({ color: 0xe8e5dd, roughness: 0.5 })); bb.position.y = 0.025; bal.add(bb);
  var cab = S.mesh(new T.BoxGeometry(0.2, 0.14, 0.16), M.glass, false); cab.position.set(0, 0.12, -0.015); bal.add(cab);
  var pan = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.003, 28), M.chrome); pan.position.set(0, 0.06, -0.015); bal.add(pan);
  var bTex = S.liveTex(512, 150), bLast = '';
  var bScr = new T.Mesh(new T.PlaneGeometry(0.1, 0.028), new T.MeshBasicMaterial({ map: bTex, toneMapped: false })); bScr.position.set(0, 0.026, 0.1005); bal.add(bScr);
  var bLbl = S.label('ANALYTICAL BALANCE  0.1 mg', { w: 0.1, ratio: 0.12, color: '#2b2f36' }); bLbl.position.set(0, 0.008, 0.1005); bal.add(bLbl);
  // the Gouy tube on its thread
  var tube = new T.Group(); S.scene.add(tube);
  var RACK = new T.Vector3(0.2, 0.0, 0.12), HANG = new T.Vector3(-0.1, 0.12, -0.14);
  var tg = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.2, 20, 1, true), M.glass, false); tg.position.y = 0.1; tube.add(tg);
  var pw = S.mesh(new T.CylinderGeometry(0.0048, 0.0048, 0.17, 20), new T.MeshStandardMaterial({ color: COL, roughness: 0.9 })); pw.position.y = 0.088; tube.add(pw);
  var tcap = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, 0.01, 16), M.blackPlastic); tcap.position.y = 0.2; tube.add(tcap);
  var thread = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 1, 6), new T.MeshStandardMaterial({ color: 0xf0f0f0 }), false); S.scene.add(thread);
  var rack = S.rounded(0.06, 0.03, 0.04, 0.005, M.wood); rack.position.set(0.2, 0.015, 0.12); S.scene.add(rack);
  function place(v) { tube.position.copy(v); var top = shelfY, y0 = v.y + 0.205; thread.visible = st.hung; thread.scale.y = Math.max(0.001, top - y0); thread.position.set(-0.1, (top + y0) / 2, -0.14); }
  tube.rotation.z = 0; place(new T.Vector3(RACK.x, RACK.y + 0.03, RACK.z)); tube.rotation.x = 0;
  // gaussmeter and magnet supply
  function unitBox(w, h, d, col, pos) { var g = new T.Group(); S.scene.add(g); g.position.set(pos[0], 0, pos[1]);
    var b = S.rounded(w, h, d, 0.01, new T.MeshStandardMaterial({ color: col, roughness: 0.5 })); b.position.y = h / 2; g.add(b); return g; }
  var gm = unitBox(0.16, 0.08, 0.12, 0x2b2f36, [0.26, -0.12]);
  var gTex = S.liveTex(512, 150), gLast = '';
  var gScr = new T.Mesh(new T.PlaneGeometry(0.1, 0.028), new T.MeshBasicMaterial({ map: gTex, toneMapped: false })); gScr.position.set(0, 0.05, 0.0605); gm.add(gScr);
  var gL = S.label('GAUSSMETER  T', { w: 0.08, ratio: 0.14, color: '#e8e8ea' }); gL.position.set(0, 0.018, 0.0605); gm.add(gL);
  S.wire([[0.2, 0.04, -0.12], [0.05, 0.1, -0.08], [-0.1, 0.13, -0.09]], 'black');
  var sup = unitBox(0.2, 0.09, 0.14, 0x3a4f6e, [0.2, 0.12]);
  var sKnob = new T.Group(); sKnob.position.set(0.05, 0.045, 0.071); sup.add(sKnob);
  var sk = S.mesh(new T.CylinderGeometry(0.016, 0.017, 0.014, 28), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.007; sKnob.add(sk);
  var skp = S.mesh(new T.BoxGeometry(0.002, 0.012, 0.0012), M.white, false); skp.position.set(0, 0.007, 0.0145); sKnob.add(skp);
  var aTex = S.liveTex(512, 150), aLast = '';
  var aScr = new T.Mesh(new T.PlaneGeometry(0.08, 0.024), new T.MeshBasicMaterial({ map: aTex, toneMapped: false })); aScr.position.set(-0.04, 0.055, 0.0705); sup.add(aScr);
  var sL = S.label('MAGNET SUPPLY 0–5 A', { w: 0.1, ratio: 0.14, color: '#e8e8ea' }); sL.position.set(-0.03, 0.02, 0.0705); sup.add(sL);
  S.wire([[0.12, 0.04, 0.12], [-0.1, 0.02, 0.0], [-0.2, 0.1, -0.1]], 'red');
  function lcd(tex, txt, which) {
    if (which === 0 && bLast === txt) return; if (which === 1 && gLast === txt) return; if (which === 2 && aLast === txt) return;
    if (which === 0) bLast = txt; else if (which === 1) gLast = txt; else aLast = txt;
    tex.draw(function (x) { x.fillStyle = '#a9b79a'; x.fillRect(0, 0, 512, 150); x.font = '700 82px "JetBrains Mono", monospace';
      x.textAlign = 'right'; x.fillStyle = '#1b2116'; x.fillText(txt, 490, 108); });
  }

  S.addApparatus('mag', mag, 'Electromagnet', 'Two coils on an iron yoke; the field between the flat pole pieces is set by the coil current.');
  S.addApparatus('bal', bal, 'Analytical balance', 'Reads to 0.1 mg. The tube hangs from the hook under the pan, through a hole in the shelf.');
  S.addApparatus('tube', tube, 'Gouy tube of ' + SALT, 'A long glass tube packed evenly with the powder; its lower end sits at the centre of the gap and its upper end far out of the field.');
  S.addApparatus('gm', gm, 'Gaussmeter', 'Its Hall probe sits in the gap beside the tube and reads B in tesla.');
  S.addApparatus('sup', sup, 'Magnet supply', 'Sets the coil current, 0–5 A.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');
  var hudB = S.hudCard('Field'), hudM = S.hudCard('Balance');

  // ================================================================ actions
  function hang() {
    if (busy() || st.hung) return Promise.resolve();
    var from = tube.position.clone(), to = HANG.clone();
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.2, 0)), function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.2 + 0.08 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k); },
      function (k) { place(new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.08 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k)); },
      { mode: 'side', ms: 1300, reachMs: 600 }).then(function () {
      st.hung = true; place(to); S.say('The tube hangs from the balance hook, its lower end at the centre of the pole gap and its upper end far above the field.'); S.render(); });
  }
  function setI(a) {
    if (busy()) return Promise.resolve(false);
    if (!isFinite(a) || a < 0 || a > 5) { S.say('The magnet supply gives 0 to 5 A.'); return Promise.resolve(false); }
    var pt = sKnob.getWorldPosition(new T.Vector3()), a0 = st.I;
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { st.I = a0 + (a - a0) * k; sKnob.rotation.z = -st.I * 0.9; },
      { mode: 'front', ms: 500 + 120 * Math.abs(a - a0), reachMs: 450 }).then(function () { st.I = Math.round(a * 10) / 10; S.render(); return true; });
  }
  function weighZero() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.hung) { S.say('Hang the tube first.'); return false; }
    if (st.I > 0) { S.say('Weigh with the magnet OFF first.'); return false; }
    st.m0 = readM(); S.say('With no field the tube reads ' + st.m0.toFixed(4) + ' g.'); S.render(); return true;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (st.m0 === null) { S.say('Weigh the tube with the magnet off first.'); return false; }
    if (st.I <= 0) { S.say('Turn the magnet current up first.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.I - st.I) < 0.05; })) { S.say('You already have a reading at ' + st.I.toFixed(1) + ' A.'); return false; }
    var B = readB(), m = readM(), dm = (m - st.m0) * 1000;
    var row = { I: st.I, B: B, B2: B * B, m: m, dm: dm };
    S.addRow(row); st.last = row;
    S.say('Written: ' + st.I.toFixed(1) + ' A, ' + B.toFixed(3) + ' T, balance ' + m.toFixed(4) + ' g, a gain of ' + dm.toFixed(1) + ' mg.');
    return true;
  }
  function result(rows) {
    if (rows.length < 4) return null;
    var f = S.fit.linear(rows.map(function (r) { return [r.B2, r.dm * 1e-6]; }));
    if (!f || f.m <= 0) return null;
    var chiv = f.m * 2 * MU0 * p.g / p.A + p.chiair;
    return { label: 'Molar susceptibility (cgs)', value: chiv * p.M / (4 * Math.PI * 1e-6 * p.rho), unit: '× 10⁻⁶ cm³/mol', digits: 0, truth: p.chim,
      note: 'Slope of dm against B²: ' + (f.m * 1e6).toFixed(1) + ' mg/T², so χ_v = ' + chiv.toExponential(3) + ' (SI) for the packed powder (ρ = ' + p.rho + ' g/cm³). SIMULATED DATA.' };
  }

  return {
    camera: { pos: [0.0, 0.7, 0.9], look: [-0.02, 0.18, -0.1] },
    views: { mag: [[-0.05, 0.3, 0.25], [-0.1, 0.13, -0.14]], bal: [[-0.05, 0.55, 0.3], [-0.1, 0.4, -0.14]], tube: [[0.0, 0.25, 0.2], [-0.1, 0.15, -0.14]],
      gm: [[0.28, 0.25, 0.25], [0.26, 0.05, -0.12]], sup: [[0.22, 0.25, 0.4], [0.2, 0.05, 0.12]], rack: [[0.22, 0.2, 0.36], [0.2, 0.05, 0.12]],
      bench: [[0.0, 0.7, 0.9], [-0.02, 0.18, -0.1]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A paramagnetic sample is pulled into a strong field. A long uniform column with one end in the field and the other end out of it feels a force that depends only on the field at the lower end.',
      formula: 'dm · g = (χ_v − χ_air) A B² / (2 μ₀),   χ_m(cgs) = χ_v M / (4π ρ)',
      formulaNote: 'A: cross-section of the tube; ρ: packed density of the powder; M: molar mass',
      more: ['Weigh with the field off first; every later reading is a change from that.',
        'The gain in mass grows as B², so plot dm against B² and use the slope: one bad reading then shows up at once.',
        'The air the column displaces is paramagnetic too (oxygen); its small susceptibility is added back.'],
      precautions: 'Pack the powder evenly with no gaps, keep the tube from touching the pole pieces, and turn the current up and down slowly.' },
    book: { title: 'Expt. — Susceptibility by the Gouy balance',
      lines: ['Sample: ' + SALT, 'Tube cross-section ' + (p.A * 1e4).toFixed(2) + ' cm², packed ρ = ' + p.rho + ' g/cm³', 'dm g = χ A B² / (2 μ₀)'],
      columns: [{ label: 'I (A)', get: function (r) { return r.I.toFixed(1); } }, { label: 'B (T)', get: function (r) { return r.B.toFixed(3); } },
        { label: 'B² (T²)', get: function (r) { return r.B2.toFixed(4); } }, { label: 'dm (mg)', get: function (r) { return r.dm.toFixed(1); } }] },
    graph: { x: function (r) { return r.B2; }, y: function (r) { return r.dm; }, xlabel: 'B² (T²)', ylabel: 'dm (mg)', x0: 0, y0: 0,
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.02,
    resultNote: 'A straight line through the origin on a B² axis is the signature of an induced moment. From the molar susceptibility the Curie law gives the number of unpaired electrons per ion.',
    chips: ['Why does the sample get heavier?', 'Why plot against B²?', 'Why must the top be out of the field?', 'Check my readings'],
    viva: [['A paramagnetic sample in the Gouy balance appears', ['Heavier', 'Lighter', 'Unchanged'], 0, 'It is pulled down into the field.'],
      ['The force depends on', ['B² at the lower end', 'B at the top', 'the field gradient only'], 0, 'For a long uniform column the gradient integrates out.']],
    askState: function () {
      return { experiment: 'magnetic susceptibility by the Gouy balance', sample: SALT, tube_hung: st.hung, current_A: st.I,
        field_T: readB(), balance_g: readM(), zero_field_g: st.m0, readings: S.rows.length };
    },
    steps: [
      { id: 'hang', title: 'Hang and weigh', view: 'bal', render: function (u) {
          u.h2('Hang the tube and weigh it with no field');
          u.task('Tube on the balance hook', st.hung, st.hung ? 'Hanging in the gap' : 'In its rack').add(u.button('Hang the tube', function () { S.focus('tube'); hang(); }, true, st.hung || S.hand.busy));
          u.task('Weight with the magnet off', st.m0 !== null, st.m0 === null ? 'Not taken' : st.m0.toFixed(4) + ' g').add(u.button('Read the balance', function () { weighZero(); }, false, !st.hung || S.hand.busy));
          u.live(function () { return 'Balance ' + readM().toFixed(4) + ' g'; });
          u.next('Next: switch the field on', st.m0 !== null);
        },
        ok: function () { return st.m0 !== null; },
        auto: function () { return hang().then(function () { weighZero(); }); } },
      { id: 'field', title: 'Field and pull', view: 'mag', render: function (u) {
          u.h2('Raise the field and read the pull');
          u.p('Set the magnet current, read the gaussmeter and the balance, and write them down. Take at least five currents.');
          var sel = { a: Math.min(5, Math.round((st.I + 1) * 10) / 10) };
          u.slider('Magnet current', 0, 5, 0.1, function () { return sel.a; }, function (v) { sel.a = Math.round(v * 10) / 10; }, 'A', 1);
          u.row(u.button('Turn the supply to ' + sel.a.toFixed(1) + ' A', function () { S.focus('sup'); setI(sel.a); }, true, S.hand.busy),
            u.button('Record B and the balance', function () { record(); }, false, S.hand.busy));
          u.live(function () { return st.I.toFixed(1) + ' A  ·  ' + readB().toFixed(3) + ' T  ·  ' + readM().toFixed(4) + ' g'; });
          u.table();
          u.next('Next: the result', S.rows.length >= 5);
        },
        ok: function () { return S.rows.length >= 5; },
        auto: function () {
          return [1, 2, 3, 4, 5].reduce(function (pr, a) { return pr.then(function () { return setI(a); }).then(function () { record(); }); }, Promise.resolve())
            .then(function () { return setI(0); });
        } },
    ],
    tick: function () {
      lcd(bTex, readM().toFixed(4), 0);
      lcd(gTex, readB().toFixed(3), 1);
      lcd(aTex, st.I.toFixed(1), 2);
      hudB.set(readB().toFixed(3) + ' T');
      hudM.set(readM().toFixed(4) + ' g');
    },
  };
});
