/* Prayogshala studio module: depression of a loaded metre scale (NCERT Class XI, Section B, Activities).
   A wooden metre scale is clamped flat in a heavy stand so that a measured length sticks out free. A pin fixed at the
   free end points at a vertical millimetre scale with a strip of mirror beside it (so the reading is taken with no
   parallax, to about 0.2 mm). The gloved hand slides 50 g slotted weights onto the hanger at the free end one at a
   time, and the beam bends into the cantilever curve.
   Physics: the `beambend` kernel of the mech11 pack - δ = m g L³ / (3 Y I) with I = b t³ / 12. */
HoolaStudio.define('metre-scale-depression', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.beambend;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('beambend');
  p.m = 0; p.mode = 0;
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '') || 'Wooden metre scale';
  var STEP_KG = 0.05, NW = 5, LC = 0.0002;                       // 50 g weights; the pin is read to 0.2 mm
  var sim = K.init(p);
  var st = { n: 0, zero: null };

  // ---------- geometry
  var CY = 0.24, CZ = -0.1, CX = -0.42;                          // the clamp jaw: where the beam leaves the clamp
  var FREE = p.L, OVER = 0.06;                                   // free length to the load, plus a little overhang
  var TOT = FREE + OVER, BW = p.b, BT = p.t;
  var SEGS = 64;

  // the stand and clamp
  var stand = new T.Group(); S.scene.add(stand);
  var base = S.rounded(0.24, 0.2, 0.024, 0.006, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(CX - 0.05, 0.012, CZ); stand.add(base);
  var post = S.mesh(new T.CylinderGeometry(0.017, 0.02, CY, 24), M.chrome); post.position.set(CX - 0.05, CY / 2, CZ); stand.add(post);
  var jawA = S.rounded(0.11, 0.035, 0.07, 0.005, M.iron); jawA.position.set(CX - 0.035, CY + 0.02 + BT / 2, CZ); stand.add(jawA);
  var jawB = S.rounded(0.11, 0.035, 0.07, 0.005, M.iron); jawB.position.set(CX - 0.035, CY - 0.02 - BT / 2, CZ); stand.add(jawB);
  [-0.02, 0.03].forEach(function (dx) {
    var sc = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.07, 14), M.chrome); sc.position.set(CX - 0.035 + dx, CY, CZ + 0.045); sc.rotation.x = Math.PI / 2; stand.add(sc);
    var wn = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 6), M.black); wn.position.set(CX - 0.035 + dx, CY, CZ + 0.082); wn.rotation.x = Math.PI / 2; stand.add(wn);
  });
  S.contact(0.3, 0.26, CX - 0.05, CZ, 0.55);

  // the beam: a box whose vertices follow the cantilever curve
  var topTex = S.canvasTex(2048, 128, function (x, w, h) {
    x.drawImage(S.woodTex.image, 0, 0, w, h);
    var cm = Math.round(TOT * 100), k = w / cm;
    x.fillStyle = '#17171a'; x.font = '600 34px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var i = 0; i <= cm; i++) {
      var px = i * k, big = i % 10 === 0, mid = i % 5 === 0;
      x.fillRect(px, 0, big ? 3 : 1.6, big ? h * 0.42 : mid ? h * 0.3 : h * 0.18);
      if (big) x.fillText(String(i), px + 2, h * 0.64);
    }
    x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillStyle = '#6b4a14';
    x.fillText('METRE SCALE · cm', 12, h - 14);
  });
  var woodM = new T.MeshStandardMaterial({ map: S.woodTex, color: 0xd8c08a, roughness: 0.62 });
  var topM = new T.MeshStandardMaterial({ map: topTex, roughness: 0.55 });
  var beamG = new T.BoxGeometry(TOT, BT, BW, SEGS, 1, 1);
  var basePos = beamG.attributes.position.array.slice();
  var beam = S.mesh(beamG, [woodM, woodM, topM, woodM, woodM, woodM]);
  beam.position.set(CX + TOT / 2, CY, CZ); S.scene.add(beam);
  function curve(xFromClamp, d) {                                 // the cantilever's own shape, free end down by d
    var L = FREE, x = Math.min(xFromClamp, L);
    var y = -d * (3 * L * x * x - x * x * x) / (2 * L * L * L);
    if (xFromClamp > L) y += -(d * 3 / (2 * L)) * (xFromClamp - L);   // beyond the load the beam runs on straight
    return y;
  }
  function bend(d) {
    var pos = beamG.attributes.position.array;
    for (var i = 0; i < pos.length; i += 3) {
      var xl = basePos[i] + TOT / 2;                              // 0 at the clamp
      pos[i + 1] = basePos[i + 1] + curve(xl, d);
    }
    beamG.attributes.position.needsUpdate = true;
    beamG.computeVertexNormals();
  }

  // hanger at the free end + the pile of slotted weights
  var hang = new T.Group(); S.scene.add(hang);
  var hhook = S.mesh(new T.TorusGeometry(0.006, 0.0015, 8, 20), M.chrome); hhook.rotation.y = Math.PI / 2; hang.add(hhook);
  var hstem = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.06, 12), M.chrome); hstem.position.y = -0.034; hang.add(hstem);
  var hdisc = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.006, 32), M.brass); hdisc.position.y = -0.066; hang.add(hdisc);
  var DT = 0.011, DR = 0.029;
  var PILE = new T.Vector3(0.3, 0, 0.1);
  var wTex = S.canvasTex(128, 64, function (x) { x.fillStyle = '#5a3d0c'; x.font = '700 36px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('50 g', 64, 34); });
  var wMat = new T.MeshStandardMaterial({ map: wTex, transparent: true, roughness: 0.5, depthWrite: false });
  var weights = [], onHanger = [];
  for (var i = 0; i < NW; i++) {
    var g = new T.Group();
    g.add(S.mesh(new T.CylinderGeometry(DR, DR, DT, 32), M.brass));
    var tag = new T.Mesh(new T.PlaneGeometry(0.02, 0.01), wMat); tag.rotation.x = -Math.PI / 2; tag.position.set(0.006, DT / 2 + 0.0003, 0); tag.renderOrder = 2; g.add(tag);
    g.position.set(PILE.x, DT / 2 + i * DT, PILE.z); S.scene.add(g); weights.push(g);
  }
  var pile = weights.slice();
  S.contact(0.1, 0.1, PILE.x, PILE.z, 0.5);

  // the pointer pin at the free end, and the vertical scale with its mirror strip
  var pin = new T.Group(); S.scene.add(pin);
  var pinR = S.mesh(new T.CylinderGeometry(0.0009, 0.0009, 0.05, 10), M.chrome); pinR.rotation.z = Math.PI / 2; pinR.position.x = 0.025; pin.add(pinR);
  var pinT = S.mesh(new T.ConeGeometry(0.0014, 0.008, 12), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }));
  pinT.rotation.z = -Math.PI / 2; pinT.position.x = 0.054; pin.add(pinT);
  var pinC = S.mesh(new T.BoxGeometry(0.008, 0.012, 0.012), M.black); pin.add(pinC);

  var VX = CX + FREE + 0.075, VZ = CZ, VY0 = CY - 0.14, VLEN = 0.2;
  var vst = new T.Group(); S.scene.add(vst);
  var vbase = S.rounded(0.1, 0.09, 0.02, 0.005, M.iron); vbase.rotation.x = -Math.PI / 2; vbase.position.set(VX, 0.01, VZ); vst.add(vbase);
  var vpost = S.mesh(new T.CylinderGeometry(0.008, 0.009, VY0 + VLEN + 0.03, 18), M.chrome); vpost.position.set(VX + 0.03, (VY0 + VLEN + 0.03) / 2, VZ); vst.add(vpost);
  var vTex = S.canvasTex(128, 1024, function (x, w, h) {
    x.fillStyle = '#f3efe2'; x.fillRect(0, 0, w, h);
    var mm = Math.round(VLEN * 1000), k = (h - 24) / mm;
    x.fillStyle = '#17171a'; x.font = '600 20px "Public Sans", sans-serif'; x.textBaseline = 'middle';
    for (var j = 0; j <= mm; j++) {
      var y = h - 12 - j * k, big = j % 10 === 0, mid = j % 5 === 0;
      x.fillRect(0, y - (big ? 1.2 : 0.7), big ? w * 0.5 : mid ? w * 0.36 : w * 0.22, big ? 2.4 : 1.4);
      if (big) x.fillText(String(j / 10), w * 0.56, y);
    }
    x.fillStyle = '#9fb6c4'; x.fillRect(w * 0.84, 0, w * 0.16, h);
  });
  var vplate = new T.Mesh(new T.PlaneGeometry(0.018, VLEN), new T.MeshStandardMaterial({ map: vTex, roughness: 0.45 }));
  vplate.position.set(VX, VY0 + VLEN / 2, VZ - 0.006); vst.add(vplate);
  var vback = S.mesh(new T.BoxGeometry(0.022, VLEN + 0.01, 0.004), M.iron); vback.position.set(VX, VY0 + VLEN / 2, VZ - 0.009); vst.add(vback);
  S.contact(0.13, 0.12, VX, VZ, 0.5);

  S.addApparatus('stand', stand, 'Clamp stand', 'Two iron jaws grip the scale flat, so that end can neither move nor turn.');
  S.addApparatus('beam', beam, SAMPLE, 'Width ' + (BW * 1000).toFixed(0) + ' mm and thickness ' + (BT * 1000).toFixed(1)
    + ' mm, with ' + (FREE * 100).toFixed(0) + ' cm free beyond the clamp.');
  S.addApparatus('hang', hang, 'Hanger at the free end', 'Slotted weights of 50 g are slid onto it one at a time.');
  S.addApparatus('weights', weights[0], 'Slotted weights', NW + ' weights of 50 g: ' + (NW * 50) + ' g in all.');
  S.addApparatus('vst', vst, 'Vertical scale with mirror strip', 'The pin is read against it; the mirror beside the scale kills parallax. Readings to 0.2 mm.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Load'), hudD = S.hudCard('Depression'), hudR = S.hudCard('Pin reads');

  // ---------- readings
  function delta() { return sim.d; }
  function settled() { return Math.abs(sim.d - p.m * p.g * Math.pow(p.L, 3) / (3 * p.Y * (p.b * Math.pow(p.t, 3) / 12))) < 2e-6; }
  function pinY() { return CY + curve(FREE, delta()); }     // the pin is fixed at the loaded end
  function readingMm() { return Math.round((pinY() - VY0) / LC) * LC * 1000; }   // on the vertical scale, to 0.2 mm

  function setLoad(n) { st.n = n; p.m = n * STEP_KG; }
  function addWeight() {
    if (S.hand.busy) return Promise.resolve();
    if (st.zero === null) { S.say('Read the pin with no load first.'); return Promise.resolve(); }
    if (st.n >= NW) { S.say('That is ' + (NW * STEP_KG * 1000) + ' g. More would bend the scale for good.'); return Promise.resolve(); }
    if (!settled()) { S.say('Let the scale come to rest before adding the next weight.'); return Promise.resolve(); }
    var d = pile.pop(), from = d.position.clone(), n = st.n;
    var to = new T.Vector3(hang.position.x, hang.position.y - 0.063 + DT / 2 + n * DT, hang.position.z);
    function path(k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.08 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }
    var grip = new T.Vector3(DR + 0.002, 0, 0);
    return S.hand.pinchMove(from.clone().add(grip), function (k) { return path(k).add(grip); },
      function (k) { d.position.copy(path(k)); }, { ms: 1400 })
      .then(function () {
        onHanger.push(d); setLoad(n + 1);
        S.say('Load at the free end: ' + (st.n * STEP_KG * 1000) + ' g. Wait for the scale to stop quivering, then read the pin.');
        S.render();
      });
  }
  function readPin() {
    if (S.hand.busy) return;
    if (!settled()) { S.say('The scale is still bending. Wait until the pin stands still.'); return; }
    var r = readingMm();
    if (st.zero === null) {
      if (st.n) { S.say('Take the no-load reading with an empty hanger.'); return; }
      st.zero = r;
      S.addRow({ n: 0, m: 0, rd: r, delta: 0 });
      S.say('No-load reading ' + r.toFixed(1) + ' mm. Every depression is measured from this.');
      S.render(); return;
    }
    if (S.rows.some(function (row) { return row.n === st.n; })) { S.say('The reading for ' + (st.n * STEP_KG * 1000) + ' g is already in the table.'); return; }
    var dmm = Math.round((st.zero - r) * 10) / 10;
    S.addRow({ n: st.n, m: st.n * STEP_KG, rd: r, delta: dmm / 1000 });
    S.say('Written in your record book: ' + (st.n * STEP_KG * 1000) + ' g, pin at ' + r.toFixed(1) + ' mm, depression ' + dmm.toFixed(1) + ' mm.');
  }

  var CALC = HK.CALCS.beam_Y;
  function pose() {
    var d = delta();
    bend(d);
    var endY = CY + curve(FREE, d);
    hang.position.set(CX + FREE, endY - BT / 2 - 0.006, CZ);
    onHanger.forEach(function (w, i) { w.position.set(hang.position.x, hang.position.y - 0.063 + DT / 2 + i * DT, hang.position.z); });
    pin.position.set(CX + FREE, pinY(), CZ + BW / 2 + 0.004);
    pin.rotation.z = -Math.atan2(delta() * 3 / (2 * FREE), 1);
    hudL.set((st.n * STEP_KG * 1000).toFixed(0) + ' g');
    hudD.set(st.zero === null ? '—' : (st.zero - readingMm()).toFixed(1) + ' mm');
    hudR.set(readingMm().toFixed(1) + ' mm');
  }
  pose();

  return {
    camera: { pos: [0.45, 0.56, 1.0], look: [0.02, 0.2, -0.08] },
    views: {
      rig: [[0.42, 0.54, 0.96], [0.02, 0.2, -0.08]],
      stand: [[-0.22, 0.4, 0.34], [CX - 0.04, 0.22, CZ]],
      beam: [[0.1, 0.46, 0.6], [0.0, 0.23, CZ]],
      hang: [[0.2, 0.3, 0.42], [CX + FREE, 0.14, CZ]],
      vst: [[VX + 0.1, 0.3, 0.3], [VX, 0.18, VZ]],
      weights: [[0.42, 0.24, 0.42], [PILE.x, 0.03, PILE.z]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A beam clamped at one end and loaded at the other bends into an arc. The layers on the outside of the '
        + 'bend are stretched and those on the inside are compressed, and it is the material\'s resistance to that '
        + 'stretching which holds the load up. The depression of the free end measures how much the beam gives.',
      formula: 'δ = m g L³ / (3 Y I),  I = b t³ / 12',
      formulaNote: 'so δ is proportional to the load, and to the cube of the free length',
      more: ['The thickness matters most of all: I goes as t³, so a scale twice as thick bends eight times less under the '
        + 'same load. The width only helps in proportion.',
        'The same scale resting on two knife edges and loaded in the middle sags only m g L³ / (48 Y I) - sixteen times '
        + 'less than the cantilever, because both ends are held.'],
      precautions: 'Clamp the scale firmly and keep it horizontal to start with. Add the weights gently and wait for the '
        + 'quivering to stop. Read the pin with your eye in line with its image in the mirror strip.'
    },
    book: {
      title: 'Expt. — Depression of a Loaded Metre Scale',
      lines: ['Aim: how the depression of a clamped metre scale changes with the load.',
        'Free length L = ' + (FREE * 100).toFixed(0) + ' cm,  breadth b = ' + (BW * 1000).toFixed(0) + ' mm,  thickness t = ' + (BT * 1000).toFixed(1) + ' mm',
        'I = b t³ / 12 = ' + (p.b * Math.pow(p.t, 3) / 12).toExponential(2) + ' m⁴',
        'δ = reading with no load − reading with the load',
        'δ = m g L³ / (3 Y I)   →   Y = m g L³ / (3 I δ)',
        'Precautions: firm clamp, gentle loading, no parallax.'],
      columns: [{ label: 'Load (g)', get: function (r) { return String(Math.round(r.m * 1000)); } },
        { label: 'Pin reads (mm)', get: function (r) { return r.rd.toFixed(1); } },
        { label: 'Depression δ (mm)', get: function (r) { return (r.delta * 1000).toFixed(1); } },
        { label: 'δ / m (mm/g)', get: function (r) { return r.m > 0 ? (r.delta * 1000 / (r.m * 1000)).toFixed(3) : '—'; } }]
    },
    graph: {
      x: function (r) { return r.m; }, y: function (r) { return r.delta * 1000; },
      xlabel: 'Load m (kg)', ylabel: 'Depression δ (mm)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      var use = rows.filter(function (r) { return r.delta > 0; });
      if (use.length < 2) return null;
      return { label: 'Y of the scale', value: CALC.fn(use, p), unit: 'Pa', digits: 0, truth: p.Y,
        note: 'From δ = m g L³ / (3 Y I). The straight line through the origin shows that δ is proportional to the load.' };
    },
    resultNote: 'Wood is not the same stiffness in every scale, so the value found here is this scale\'s own: what the '
      + 'experiment really shows is that the depression is proportional to the load.',
    tol: 0.05,
    chips: ['Why does thickness matter so much?', 'What is the mirror strip for?',
      'Why is the graph a straight line?', 'Check my readings', 'What are the main sources of error?'],
    viva: [['If the free length is halved, the depression under the same load becomes',
      ['One eighth', 'One half', 'One quarter'], 0, 'δ is proportional to L³.'],
      ['The mirror strip beside the scale is there to',
        ['Remove parallax when the pin is read', 'Light the scale', 'Hold the scale straight'], 0,
        'The eye is right when the pin and its image coincide.']],
    askState: function () {
      return { load_g: Math.round(st.n * STEP_KG * 1000), free_length_cm: +(FREE * 100).toFixed(1),
        breadth_mm: +(BW * 1000).toFixed(1), thickness_mm: +(BT * 1000).toFixed(2),
        depression_now_mm: +(delta() * 1000).toFixed(2), pin_reading_mm: readingMm(), no_load_reading_mm: st.zero,
        settled: settled(), readings_taken: S.rows.length };
    },

    steps: [
      { id: 'zero', title: 'No-load reading', view: 'vst', render: function (u) {
          u.h2('Read the pin with no load');
          u.p('The scale is clamped with ' + (FREE * 100).toFixed(0) + ' cm free. The pin at the free end points at the '
            + 'vertical scale. Read it now, before any weight goes on.');
          u.task('Read the pin', st.zero !== null, st.zero !== null ? 'No-load reading = ' + st.zero.toFixed(1) + ' mm' : 'Eye in line with the mirror image')
            .add(u.button('Read the pin', readPin, st.zero === null, S.hand.busy || st.zero !== null));
          u.live(function () { return 'Pin at ' + readingMm().toFixed(1) + ' mm'; });
          u.note('The vertical scale is read to 0.2 mm with the help of the mirror strip beside it.');
          u.next('Next: load the free end', st.zero !== null);
        },
        ok: function () { return st.zero !== null; },
        auto: function () { S.advance(20, settled); readPin(); return Promise.resolve(); } },

      { id: 'load', title: 'Load it', view: 'rig', render: function (u) {
          u.h2('Add the weights, 50 g at a time');
          u.p('Each weight bends the scale a little more. Wait for it to stop quivering and read the pin after every one.');
          u.row(u.button('Add 50 g', function () { addWeight(); }, true, S.hand.busy || st.n >= NW),
            u.button('Read the pin', readPin, false, S.hand.busy));
          u.live(function () {
            return 'Load ' + (st.n * STEP_KG * 1000) + ' g · depression ' + (delta() * 1000).toFixed(2) + ' mm · pin '
              + readingMm().toFixed(1) + ' mm' + (settled() ? '' : ' · still bending');
          });
          if (st.n >= NW) u.note('All ' + NW + ' weights are on. Take them off when you have finished so that the scale does not take a set.');
          u.h3('Observation table'); u.table();
          var have = S.rows.filter(function (r) { return r.m > 0; }).length;
          if (have < 4) u.p(have + ' of at least 4 loads recorded.');
          u.next('Next: the graph', have >= 4);
        },
        ok: function () { return S.rows.filter(function (r) { return r.m > 0; }).length >= 4; },
        auto: function () {
          var pr = Promise.resolve();
          for (var i = 0; i < NW; i++) {
            pr = pr.then(function () { return addWeight(); }).then(function () { S.advance(20, settled); readPin(); });
          }
          return pr;
        } }
    ],

    tick: function (dt) { K.step(sim, p, dt); pose(); }
  };
});
