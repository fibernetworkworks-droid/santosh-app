/* Prayogshala studio module: Young's modulus of a wire by Searle's apparatus (NCERT Class XI, Section B).
   Two wires of the same material hang side by side from one rigid bracket. The left (reference) wire carries a constant
   dead load; the right (experimental) wire carries the hanger on which half-kilogram slotted weights are added. Each
   wire ends in a brass frame; a spirit level lies across the two frames, resting on a pin on the left frame and on the
   tip of a micrometer screw (pitch 0.5 mm, 50 divisions, least count 0.01 mm) on the right frame.
   When the loaded wire stretches, its frame goes down, the bubble runs off centre, and the student turns the micrometer
   until the bubble is central again. The change in the micrometer reading IS the extension.
   Physics: the `searle` kernel of the mech11 pack - e = 4 m g L / (π d² Y). Everything is read from the lab's params. */
HoolaStudio.define('searle-young-modulus', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.searle;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('searle');
  p.m = 0;
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  var METALS = [[/brass/i, 'brass', 0xd4ad55, 0.3], [/copper/i, 'copper', 0xc8764a, 0.28],
    [/alumin/i, 'aluminium', 0xcdd2d6, 0.35], [/nichrome/i, 'nichrome', 0x9aa0a6, 0.4], [/steel|iron/i, 'steel', 0xc9ced3, 0.25]];
  var WIRE = { name: 'steel', col: 0xc9ced3, rough: 0.25 };
  METALS.forEach(function (q) { if (!WIRE.set && q[0].test(SAMPLE)) WIRE = { name: q[1], col: q[2], rough: q[3], set: 1 }; });

  // ---------- geometry
  var FY = 0.24, TOP = p.L + FY, WZ = -0.42, XA = -0.035, XB = 0.035, SEP = XB - XA;
  var FRH = 0.085, WR = Math.max(0.0007, p.d * 2);         // the wire is drawn thicker than life so it can be seen
  var STEP_KG = 0.5, NW = 5, ZERO_SCR = 0.0012;            // five half-kilogram slotted weights; the screw starts at 1.20 mm
  var BUB_PER_MRAD = 0.0012;                               // the bubble runs 1.2 mm along its tube per milliradian of tilt
  var sim = K.init(p);
  var st = { n: 0, scr: ZERO_SCR, zero: null, levelled: true, turning: 0 };

  function e() { return sim.e; }
  function tiltMrad() { return (st.scr - ZERO_SCR - e()) / SEP * 1000; }
  function bubble() { return Math.max(-0.011, Math.min(0.011, -tiltMrad() * BUB_PER_MRAD)); }
  function centred() { return Math.abs(tiltMrad()) < 0.02; }
  function reading() { return Math.round(st.scr * 100000) / 100; }      // mm, least count 0.01 mm
  function settled() { return Math.abs(e() - p.m * p.g * p.L / (Math.PI * p.d * p.d / 4 * p.Y)) < 2e-7; }

  // ---------- pillar, bracket, wires
  var post = new T.Group(); S.scene.add(post);
  var base = S.rounded(0.3, 0.24, 0.03, 0.008, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(-0.26, 0.015, WZ); post.add(base);
  var pillar = S.mesh(new T.CylinderGeometry(0.019, 0.022, TOP + 0.05, 28), M.chrome); pillar.position.set(-0.26, (TOP + 0.05) / 2, WZ); post.add(pillar);
  var brk = S.rounded(0.36, 0.034, 0.05, 0.006, M.iron); brk.position.set(-0.09, TOP + 0.017, WZ); post.add(brk);
  var gus = S.mesh(new T.BoxGeometry(0.06, 0.06, 0.03), M.iron); gus.position.set(-0.23, TOP - 0.02, WZ); post.add(gus);
  [XA, XB].forEach(function (x) {
    var chk = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.016, 14), M.brass); chk.position.set(x, TOP - 0.008, WZ); post.add(chk);
  });
  S.contact(0.4, 0.32, -0.26, WZ, 0.55);
  var wireM = new T.MeshStandardMaterial({ color: WIRE.col, roughness: WIRE.rough, metalness: 1 });
  var wires = [XA, XB].map(function (x) {
    var w = S.mesh(new T.CylinderGeometry(WR, WR, p.L, 10), wireM, true, false);
    w.position.set(x, FY + p.L / 2, WZ); S.scene.add(w); return w;
  });

  // ---------- the two frames
  function frame(x) {
    var g = new T.Group(); S.scene.add(g);
    var bar = function (w, h, dp, px, py) { var m = S.mesh(new T.BoxGeometry(w, h, dp), M.brass); m.position.set(px, py, 0); g.add(m); return m; };
    bar(0.05, 0.006, 0.016, 0, 0);                                   // top bar (the wire ends here)
    bar(0.006, FRH, 0.016, -0.022, -FRH / 2);
    bar(0.006, FRH, 0.016, 0.022, -FRH / 2);
    bar(0.05, 0.008, 0.016, 0, -FRH);                                // bottom bar: the load hangs from it
    var hook = S.mesh(new T.TorusGeometry(0.005, 0.0014, 8, 18), M.brass); hook.position.set(0, -FRH - 0.007, 0); g.add(hook);
    g.position.set(x, FY, WZ);
    return g;
  }
  var frA = frame(XA), frB = frame(XB);
  var pin = S.mesh(new T.CylinderGeometry(0.0025, 0.0025, 0.012, 12), M.chrome); pin.position.set(0, 0.009, 0); frA.add(pin);

  // ---------- micrometer screw on the experimental frame
  var mic = new T.Group(); frB.add(mic); mic.position.set(0, 0.004, 0);
  var barrel = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.03, 24), M.chrome); barrel.position.y = 0.015; mic.add(barrel);
  var msTex = S.canvasTex(64, 256, function (x, w, h) {
    x.fillStyle = '#d7dadd'; x.fillRect(0, 0, w, h); x.fillStyle = '#1a1a1c';
    x.font = '600 20px "Public Sans", sans-serif';
    for (var i = 0; i <= 10; i++) { var y = h - 16 - i * (h - 32) / 10; x.fillRect(0, y - 1, i % 2 ? w * 0.28 : w * 0.46, 2); if (!(i % 2)) x.fillText(String(i / 2), w * 0.55, y + 7); }
  });
  var msPlate = new T.Mesh(new T.PlaneGeometry(0.006, 0.026), new T.MeshStandardMaterial({ map: msTex, roughness: 0.4 }));
  msPlate.position.set(0.0, 0.015, 0.0092); mic.add(msPlate);
  var thimble = new T.Group(); mic.add(thimble);
  var thTex = S.canvasTex(512, 64, function (x, w, h) {
    x.fillStyle = '#cfd4d8'; x.fillRect(0, 0, w, h); x.fillStyle = '#17181a'; x.font = '600 22px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var i = 0; i < 50; i++) { var px = i * w / 50; x.fillRect(px, 0, i % 5 ? 1.4 : 2.4, i % 5 ? h * 0.3 : h * 0.5); if (!(i % 10)) x.fillText(String(i), px + 10, h * 0.8); }
  });
  var thBody = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.026, 36), new T.MeshStandardMaterial({ map: thTex, roughness: 0.3, metalness: 0.7 }));
  thBody.position.y = 0.042; thimble.add(thBody);
  var thCap = S.mesh(new T.CylinderGeometry(0.0095, 0.0095, 0.008, 24), M.black); thCap.position.y = 0.059; thimble.add(thCap);
  var tip = S.mesh(new T.CylinderGeometry(0.0026, 0.0026, 0.012, 14), M.steel); mic.add(tip);

  // ---------- spirit level across the two frames
  var lev = new T.Group(); S.scene.add(lev);
  var levBar = S.rounded(SEP + 0.05, 0.016, 0.026, 0.003, new T.MeshStandardMaterial({ color: 0x23262a, roughness: 0.35 }));
  lev.add(levBar);
  var glassT = S.mesh(new T.CylinderGeometry(0.0042, 0.0042, 0.03, 20), M.glass, false); glassT.rotation.z = Math.PI / 2; glassT.position.set(0, 0.009, 0.0); lev.add(glassT);
  var liqT = S.mesh(new T.CylinderGeometry(0.0034, 0.0034, 0.029, 18), new T.MeshStandardMaterial({ color: 0xe8edc0, roughness: 0.1, transparent: true, opacity: 0.6 }), false);
  liqT.rotation.z = Math.PI / 2; liqT.position.set(0, 0.009, 0); lev.add(liqT);
  var bub = S.mesh(new T.CylinderGeometry(0.0033, 0.0033, 0.006, 16), new T.MeshStandardMaterial({ color: 0xf7fbff, roughness: 0.05 }), false);
  bub.rotation.z = Math.PI / 2; bub.position.set(0, 0.009, 0); bub.renderOrder = 3; lev.add(bub);
  [-0.004, 0.004].forEach(function (x) { var mk = S.mesh(new T.BoxGeometry(0.0009, 0.0012, 0.009), M.black, false); mk.position.set(x, 0.0132, 0); lev.add(mk); });
  var levLbl = S.label('SPIRIT LEVEL', { w: 0.03, ratio: 0.16, color: '#e6e6e8' }); levLbl.position.set(-0.03, 0.0, 0.0133); lev.add(levLbl);

  // ---------- dead load, hanger and the slotted weights
  function disc(r, h, mat) { return S.mesh(new T.CylinderGeometry(r, r, h, 36), mat); }
  var dead = new T.Group(); S.scene.add(dead);
  var dstem = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.06, 12), M.chrome); dstem.position.y = -0.03; dead.add(dstem);
  var ddisc = disc(0.032, 0.03, M.brass); ddisc.position.y = -0.075; dead.add(ddisc);
  var dl = S.label('2 kg', { w: 0.03, ratio: 0.4, color: '#4a3208' }); dl.position.set(0, -0.075, 0.0322); dead.add(dl);
  dead.position.set(XA, FY - FRH - 0.012, WZ);

  var hang = new T.Group(); S.scene.add(hang);
  var hstem = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.06, 12), M.chrome); hstem.position.y = -0.03; hang.add(hstem);
  var hdisc = disc(0.034, 0.008, M.brass); hdisc.position.y = -0.064; hang.add(hdisc);
  var hl = S.label('HANGER', { w: 0.034, ratio: 0.22, color: '#4a3208' }); hl.rotation.x = -Math.PI / 2; hl.position.set(0, -0.0598, 0.004); hang.add(hl);

  var DR = 0.033, DT = 0.013;
  var PILE = new T.Vector3(0.33, 0, 0.06);
  var wTex = S.canvasTex(128, 64, function (x) { x.fillStyle = '#5a3d0c'; x.font = '700 34px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('0.5 kg', 64, 34); });
  var wMat = new T.MeshStandardMaterial({ map: wTex, transparent: true, roughness: 0.5, depthWrite: false });
  var weights = [], onHanger = [];
  for (var i = 0; i < NW; i++) {
    var g = new T.Group();
    var body = disc(DR, DT, M.brass); g.add(body);
    var slot = S.mesh(new T.BoxGeometry(DR, DT + 0.001, 0.007), M.epoxy, false); slot.position.set(-DR / 2, 0, 0); slot.visible = false; g.add(slot);
    var tag = new T.Mesh(new T.PlaneGeometry(0.02, 0.01), wMat); tag.rotation.x = -Math.PI / 2; tag.position.set(0.008, DT / 2 + 0.0003, 0); tag.renderOrder = 2; g.add(tag);
    g.position.set(PILE.x, DT / 2 + i * DT, PILE.z); S.scene.add(g); weights.push(g);
  }
  var pile = weights.slice();
  S.contact(0.1, 0.1, PILE.x, PILE.z, 0.5);

  S.addApparatus('post', post, 'Rigid support and bracket', 'Both wires hang from one bracket, so both feel the same support.');
  S.addApparatus('wireB', wires[1], 'Experimental wire', 'A ' + WIRE.name + ' wire of diameter ' + (p.d * 1000).toFixed(3)
    + ' mm and length ' + p.L.toFixed(2) + ' m, drawn thicker than life so you can see it.');
  S.addApparatus('wireA', wires[0], 'Reference wire', 'The same wire beside it under a constant dead load: temperature changes affect both alike.');
  S.addApparatus('lev', lev, 'Spirit level', 'It lies across the two frames. When the bubble is between the marks, the frames are level again.');
  S.addApparatus('mic', mic, 'Micrometer screw', 'Pitch 0.5 mm, 50 divisions on the thimble: least count 0.01 mm.');
  S.addApparatus('hang', hang, 'Hanger', 'Half-kilogram slotted weights go on here, one at a time.');
  S.addApparatus('weights', weights[0], 'Slotted weights', 'Five weights of 0.5 kg each: 2.5 kg in all, well inside the elastic limit of this wire.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Load on the wire'), hudM = S.hudCard('Micrometer'), hudB = S.hudCard('Bubble');

  // ---------- actions
  function setLoad(n) { st.n = n; p.m = n * STEP_KG; }
  function addWeight() {
    if (S.hand.busy) return Promise.resolve();
    if (st.zero === null) { S.say('Take the zero reading first, with only the hanger on the wire.'); return Promise.resolve(); }
    if (st.n >= NW) { S.say('That is ' + (NW * STEP_KG) + ' kg. More would take the wire past its elastic limit.'); return Promise.resolve(); }
    var d = pile.pop(), from = d.position.clone(), n = st.n;
    var to = new T.Vector3(XB, 0, WZ);
    function path(k) {
      var mid = Math.sin(Math.PI * k) * 0.08;
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + mid + (0.02 - from.y) * k, from.z + (to.z - from.z) * k);
    }
    var grip = new T.Vector3(DR + 0.002, 0, 0);
    return S.hand.pinchMove(from.clone().add(grip), function (k) { return path(k).add(grip); },
      function (k) { d.position.copy(path(k)); }, { ms: 1500 })
      .then(function () {
        onHanger.push(d); setLoad(n + 1); st.levelled = false;
        S.say('Load on the wire: ' + (st.n * STEP_KG).toFixed(1) + ' kg. The wire stretches, the frame goes down and the bubble runs off centre.');
        S.render();
      });
  }
  function levelBubble() {
    if (S.hand.busy) return Promise.resolve();
    if (!settled()) { S.say('Let the wire finish stretching before you level the bubble.'); return Promise.resolve(); }
    if (centred()) { S.say('The bubble is already between the marks. Read the micrometer.'); return Promise.resolve(); }
    var s0 = st.scr, s1 = ZERO_SCR + e();
    var grip = new T.Vector3(XB + 0.014, FY + 0.05, WZ + 0.014);
    return S.hand.pinchMove(grip, function () { return grip; }, function (k) { st.scr = s0 + (s1 - s0) * k; st.turning = k; }, { ms: 1600, mode: 'front', pose: 'pinch' })
      .then(function () {
        st.scr = s1; st.turning = 0; st.levelled = true;
        S.say('Bubble back between the marks. The micrometer reads ' + reading().toFixed(2) + ' mm.');
        S.render();
      });
  }
  function readZero() {
    if (S.hand.busy) return;
    if (!centred()) { S.say('Bring the bubble between the marks first.'); return; }
    st.zero = reading();
    S.say('Zero reading ' + st.zero.toFixed(2) + ' mm, with only the hanger on the wire. Every extension is measured from this.');
    S.render();
  }
  function record() {
    if (S.hand.busy) return;
    if (st.zero === null) { S.say('Take the zero reading first.'); return; }
    if (!st.n) { S.say('Add a weight first.'); return; }
    if (!centred()) { S.say('The bubble is not between the marks. Turn the micrometer until it is.'); return; }
    if (S.rows.some(function (r) { return r.n === st.n; })) { S.say('The reading for ' + (st.n * STEP_KG).toFixed(1) + ' kg is already in the table.'); return; }
    var rd = reading(), ext = Math.round((rd - st.zero) * 100) / 100;
    S.addRow({ n: st.n, m: st.n * STEP_KG, rd: rd, e: ext / 1000 });
    S.say('Written in your record book: ' + (st.n * STEP_KG).toFixed(1) + ' kg, micrometer ' + rd.toFixed(2) + ' mm, extension ' + ext.toFixed(2) + ' mm.');
  }

  var CALC = HK.CALCS.searle_Y;
  function Ygpa(v) { return (v / 1e9).toFixed(0); }

  return {
    camera: { pos: [0.8, FY + p.L * 0.5, 1.3 + p.L * 0.45], look: [0.0, FY + p.L * 0.3, WZ] },
    views: {
      rig: [[0.75, FY + p.L * 0.5, 1.25 + p.L * 0.45], [0.0, FY + p.L * 0.3, WZ]],
      post: [[0.3, TOP + 0.05, 0.6], [-0.1, TOP - 0.02, WZ]],
      wireB: [[0.3, FY + p.L * 0.6, 0.5], [XB, FY + p.L * 0.55, WZ]],
      wireA: [[0.3, FY + p.L * 0.6, 0.5], [XA, FY + p.L * 0.55, WZ]],
      lev: [[0.14, FY + 0.09, 0.22], [0.0, FY + 0.02, WZ]],
      mic: [[0.12, FY + 0.1, 0.18], [XB, FY + 0.05, WZ]],
      hang: [[0.26, FY + 0.02, 0.34], [XB, FY - 0.1, WZ]],
      weights: [[0.46, 0.22, 0.4], [PILE.x, 0.03, PILE.z]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'Stress is the load carried by each square metre of the wire\'s cross-section; strain is the extension '
        + 'as a fraction of the original length. Within the elastic limit their ratio is a constant of the material, '
        + 'Young\'s modulus Y. The extension here is only a fraction of a millimetre, so it is measured with a micrometer '
        + 'screw and a spirit level between two wires hung from the same bracket.',
      formula: 'Y = (mg / πd²⁄4) ÷ (e / L) = 4 m g L / (π d² e)',
      formulaNote: 'so e is proportional to the load: the slope of the e against m graph gives Y',
      more: ['The reference wire carries a steady dead load. A change in room temperature, or a slight yielding of the '
        + 'support, moves both frames together and does not disturb the bubble, so what is left is the stretch caused by '
        + 'the load alone.',
        'Loading and unloading in the same steps checks that the wire is still elastic: the two sets of readings should agree.'],
      precautions: 'Add the weights gently, without jerks. Wait for the wire to stop stretching before levelling the bubble. '
        + 'Keep the total load inside the elastic limit. Measure the diameter with a screw gauge at several places.'
    },
    book: {
      title: 'Expt. — Young\'s Modulus (Searle\'s Apparatus)',
      lines: ['Aim: Young\'s modulus of a ' + WIRE.name + ' wire.',
        'Length of the wire L = ' + p.L.toFixed(2) + ' m',
        'Diameter d = ' + (p.d * 1000).toFixed(3) + ' mm  (screw gauge)',
        'Micrometer: pitch 0.5 mm, 50 divisions, L.C. 0.01 mm',
        'Extension e = micrometer reading − zero reading',
        'Y = 4 m g L / (π d² e)', 'Precautions: gentle loading, wait, stay elastic.'],
      columns: [{ label: 'Load (kg)', get: function (r) { return r.m.toFixed(1); } },
        { label: 'Micrometer (mm)', get: function (r) { return r.rd.toFixed(2); } },
        { label: 'Extension e (mm)', get: function (r) { return (r.e * 1000).toFixed(2); } },
        { label: 'Y (GPa)', get: function (r) { return r.e > 0 ? Ygpa(4 * r.m * p.g * p.L / (Math.PI * p.d * p.d * r.e)) : '—'; } }]
    },
    graph: {
      x: function (r) { return r.m; }, y: function (r) { return r.e * 1000; },
      xlabel: 'Load m (kg)', ylabel: 'Extension e (mm)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      var use = rows.filter(function (r) { return r.e > 0; });
      if (!use.length) return null;
      return { label: 'Y', value: CALC.fn(use, p), unit: 'Pa', digits: 0, truth: p.Y,
        note: 'Mean of Y = 4 m g L / (π d² e) over the loads, with L = ' + p.L.toFixed(2) + ' m and d = ' + (p.d * 1000).toFixed(3) + ' mm.' };
    },
    resultNote: 'The reading is only as good as the diameter: d appears squared, so a 1 % error in d is a 2 % error in Y.',
    tol: 0.03,
    chips: ['Why two wires?', 'What is the elastic limit?', 'Why does d matter so much?', 'Check my readings',
      'Why is my Y different from the table value?'],
    viva: [['What does the slope of the extension against load graph give?',
      ['4 g L / (π d² Y), so Y can be found from it', 'The mass of the wire', 'The elastic limit'], 0,
      'e = (4 g L / π d² Y) m, so the slope holds Y.'],
      ['Why must the load stay inside the elastic limit?',
        ['Beyond it the wire does not return to its length and Hooke\'s law fails', 'Beyond it the wire gets hot',
          'Beyond it the micrometer breaks'], 0, 'Past the elastic limit the extension is no longer proportional to the load.']],
    askState: function () {
      return { wire: WIRE.name, length_m: p.L, diameter_mm: +(p.d * 1000).toFixed(3),
        load_kg: +(st.n * STEP_KG).toFixed(1), weights_on_hanger: st.n,
        extension_now_mm: +(e() * 1000).toFixed(3), micrometer_mm: reading(), zero_reading_mm: st.zero,
        bubble_centred: centred(), tilt_mrad: +tiltMrad().toFixed(3), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'zero', title: 'Zero reading', view: 'lev', render: function (u) {
          u.h2('Level the bubble and take the zero reading');
          u.p('Only the hanger is on the experimental wire. Turn the micrometer screw until the bubble of the spirit level '
            + 'sits between the two marks, then read the micrometer. Every extension is measured from this reading.');
          u.task('1. Bubble between the marks', centred(), centred() ? 'Level' : 'Turn the micrometer screw')
            .add(u.button('Turn the micrometer', function () { levelBubble(); }, !centred(), S.hand.busy || centred()));
          u.task('2. Read the micrometer', st.zero !== null, st.zero !== null ? 'Zero reading = ' + st.zero.toFixed(2) + ' mm' : 'With the bubble central')
            .add(u.button('Read the micrometer', readZero, st.zero === null && centred(), S.hand.busy || st.zero !== null || !centred()));
          u.live(function () { return 'Micrometer ' + reading().toFixed(2) + ' mm · bubble ' + (centred() ? 'central' : 'off centre by ' + Math.abs(tiltMrad()).toFixed(2) + ' mrad'); });
          u.note('The wire is ' + p.L.toFixed(2) + ' m long and ' + (p.d * 1000).toFixed(3) + ' mm thick, measured with a screw gauge.');
          u.next('Next: load the wire', st.zero !== null);
        },
        ok: function () { return st.zero !== null; },
        auto: function () { readZero(); return Promise.resolve(); } },

      { id: 'load', title: 'Load the wire', view: 'rig', render: function (u) {
          u.h2('Add the weights, half a kilogram at a time');
          u.p('After each weight the wire stretches, the frame goes down and the bubble runs off centre. Wait, bring it '
            + 'back with the micrometer, and record the reading.');
          u.row(u.button('Add 0.5 kg', function () { addWeight(); }, true, S.hand.busy || st.n >= NW),
            u.button('Turn the micrometer', function () { levelBubble(); }, false, S.hand.busy || centred()),
            u.button('Record the reading', record, false, S.hand.busy || !centred() || !st.n));
          u.live(function () {
            return 'Load ' + (st.n * STEP_KG).toFixed(1) + ' kg · extension ' + (e() * 1000).toFixed(3) + ' mm · micrometer '
              + reading().toFixed(2) + ' mm · bubble ' + (centred() ? 'central' : 'off centre');
          });
          if (st.n >= NW) u.note('All five weights are on (' + (NW * STEP_KG) + ' kg). Do not load the wire any further.');
          u.h3('Observation table'); u.table();
          var have = S.rows.length;
          if (have < 4) u.p(have + ' of at least 4 loads recorded.');
          u.next('Next: the graph and Y', have >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () {
          var pr = Promise.resolve();
          for (var i = 0; i < NW; i++) {
            pr = pr.then(function () { return addWeight(); })
              .then(function () { S.advance(40, settled); return levelBubble(); })
              .then(function () { record(); });
          }
          return pr;
        } }
    ],

    tick: function (dt) {
      K.step(sim, p, dt);
      var drop = e();
      frB.position.y = FY - drop;
      wires[1].scale.y = (p.L + drop) / p.L; wires[1].position.y = FY - drop + (p.L + drop) / 2;
      hang.position.set(XB, FY - FRH - 0.012 - drop, WZ);
      onHanger.forEach(function (d, i) { d.position.set(XB, FY - FRH - 0.012 - drop - 0.06 + DT / 2 + i * DT, WZ); });
      // the level: left end on the pin of the reference frame, right end on the micrometer tip
      var yL = FY + 0.013, yR = FY - drop + 0.004 + (st.scr - ZERO_SCR) + 0.013 + ZERO_SCR;
      lev.position.set((XA + XB) / 2, (yL + yR) / 2, WZ);
      lev.rotation.z = Math.atan2(yR - yL, SEP);
      bub.position.x = bubble();
      thimble.rotation.y = -(st.scr / 0.0005) * Math.PI * 2;
      tip.position.y = 0.03 + (st.scr - ZERO_SCR) + ZERO_SCR + 0.006;
      hudL.set((st.n * STEP_KG).toFixed(1) + ' kg');
      hudM.set(reading().toFixed(2) + ' mm');
      hudB.set(centred() ? 'central' : (tiltMrad() > 0 ? 'to the left' : 'to the right'));
    }
  };
});
