/* Prayogshala studio module: surface tension by Jaeger's bubble method (B.Sc. properties of matter).
   Water dripping out of an aspirator bottle pushes air slowly into a closed system. One branch goes to a water
   manometer carrying a millimetre scale and a vernier; the other ends in a capillary jet drawn to a fine orifice and
   dipping a measured depth below the surface of the liquid under test. A bubble grows at the orifice until its radius
   of curvature equals the orifice's, when the pressure inside it is greatest and it breaks away; the manometer reads a
   maximum at that instant.
   The gloved hand lowers the jet to a measured depth, opens the stopcock and reads the manometer.
   Physics: the `jaeger` kernel of the mech_ug pack - H ρ_m g = h ρ_l g + 2T/r. All numbers come from the lab's params. */
HoolaStudio.define('jaeger-bubble', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.jaeger;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('jaeger');
  var SAMPLE = String((S.lab.variant || {}).sample || '');
  var tcm = /(\d+(?:\.\d+)?)\s*°c/i.exec(SAMPLE), TC = tcm ? +tcm[1] : null;
  var LIQ = /soap|detergent/i.test(SAMPLE) ? { name: 'soap solution', c: 0x8fc2bd }
    : /alcohol|ethanol/i.test(SAMPLE) ? { name: 'ethyl alcohol', c: 0xa9c3d2 }
      : { name: 'water', c: 0x58a3c8 };
  var kd = (S.lab.knobs || []).filter(function (q) { return q.param === 'hd'; })[0] || { min: 2, max: 8, k: 0.01 };
  var DMIN = kd.min * (kd.k || 1), DMAX = kd.max * (kd.k || 1);
  var DEPTHS = [0, 1, 2, 3].map(function (i) { return Math.round((DMIN + (DMAX - DMIN) * i / 3) * 1000) / 1000; });
  var MLC = 1e-4;                                       // the manometer is read with a vernier to 0.1 mm
  var st = { di: 1, rDone: false, read: [null, null], open: false, settled: false, H: null };
  p.hd = DEPTHS[st.di];
  var sim = K.init(p), ready = false;

  var glassM = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, metalness: 0, transparent: true, opacity: 0.2, clearcoat: 1, depthWrite: false, side: T.DoubleSide });
  var liqM = new T.MeshStandardMaterial({ color: LIQ.c, roughness: 0.06, transparent: true, opacity: 0.55, depthWrite: false, side: T.DoubleSide });
  var manoM = new T.MeshStandardMaterial({ color: 0x58a3c8, roughness: 0.06, transparent: true, opacity: 0.6, depthWrite: false });

  // ---------- the aspirator bottle
  var AX = -0.46, ZA = -0.14;
  var asp = new T.Group(); S.scene.add(asp);
  var aprof = [[0, 0], [0.055, 0], [0.055, 0.18], [0.03, 0.22], [0.03, 0.24], [0.027, 0.24], [0.027, 0.218], [0.052, 0.178], [0.052, 0.003], [0, 0.003]].map(function (q) { return new T.Vector2(q[0], q[1]); });
  var abody = new T.Mesh(new T.LatheGeometry(aprof, 40), glassM); abody.renderOrder = 4; asp.add(abody);
  var awater = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.12, 32), manoM, false); awater.position.y = 0.062; asp.add(awater);
  var atap = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.05, 14), glassM, false); atap.rotation.x = Math.PI / 2; atap.position.set(0, 0.012, 0.07); asp.add(atap);
  var aknob = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.016, 6), new T.MeshStandardMaterial({ color: 0xc0392b, roughness: 0.4 }));
  aknob.position.set(0, 0.012, 0.055); asp.add(aknob);
  var aLab = S.label('ASPIRATOR', { w: 0.055, ratio: 0.2, color: '#3b2a10', bg: '#f3ecd6' });
  aLab.position.set(0, 0.09, 0.056); asp.add(aLab);
  asp.position.set(AX, 0, ZA); S.contact(0.14, 0.14, AX, ZA, 0.45);

  // ---------- the water manometer: two limbs joined at the bottom, with a scale between them
  var MX = -0.16, MBOT = 0.05, MLEN = 0.3, MSEP = 0.05, ZM = -0.16;
  var mano = new T.Group(); S.scene.add(mano);
  [-1, 1].forEach(function (s) {
    var lim = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, MLEN, 16, 1, true), glassM, false);
    lim.position.set(s * MSEP / 2, MBOT + MLEN / 2, 0); mano.add(lim);
  });
  var mbend = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, MSEP, 14, 1, true), glassM, false);
  mbend.rotation.z = Math.PI / 2; mbend.position.set(0, MBOT, 0); mano.add(mbend);
  var mcol = [-1, 1].map(function (s) {
    var c = S.mesh(new T.CylinderGeometry(0.0052, 0.0052, 1, 14), manoM, false);
    c.position.x = s * MSEP / 2; mano.add(c); return c;
  });
  var mbase = S.mesh(new T.CylinderGeometry(0.0052, 0.0052, MSEP, 12), manoM, false);
  mbase.rotation.z = Math.PI / 2; mbase.position.set(0, MBOT, 0); mano.add(mbase);
  mano.position.set(MX, 0, ZM);
  var mscale = S.ruler(0.3, { title: 'MANOMETER · cm · vernier 0.01 cm', labelEvery: 10, width: 0.024 });
  mscale.position.set(MX, MBOT - 0.02, ZM - 0.012); S.scene.add(mscale);
  var mfoot = S.rounded(0.12, 0.08, 0.03, 0.008, M.darkWood); mfoot.rotation.x = -Math.PI / 2;
  mfoot.position.set(MX, 0.015, ZM); S.scene.add(mfoot); S.contact(0.16, 0.12, MX, ZM, 0.5);
  function manoCm(y) { return (MBOT - 0.02 + 0.3 - y) * 100; }

  // ---------- the beaker of liquid and the capillary jet on a sliding clamp
  var BX = 0.3, ZBk = -0.12, BR = 0.06, BH = 0.14, SURF = 0.115;
  var beaker = new T.Group(); S.scene.add(beaker);
  var bprof = [[0, 0], [BR, 0], [BR, BH], [BR - 0.0022, BH], [BR - 0.0022, 0.003], [0, 0.003]].map(function (q) { return new T.Vector2(q[0], q[1]); });
  var bw = new T.Mesh(new T.LatheGeometry(bprof, 40), glassM); bw.renderOrder = 4; beaker.add(bw);
  var bliq = S.mesh(new T.CylinderGeometry(BR - 0.004, BR - 0.004, SURF - 0.004, 36), liqM, false);
  bliq.position.y = (SURF + 0.004) / 2; beaker.add(bliq);
  var bsurf = new T.Mesh(new T.CircleGeometry(BR - 0.004, 36), new T.MeshStandardMaterial({ color: LIQ.c, roughness: 0.03, transparent: true, opacity: 0.7, depthWrite: false }));
  bsurf.rotation.x = -Math.PI / 2; bsurf.position.y = SURF; beaker.add(bsurf);
  beaker.position.set(BX, 0, ZBk); S.contact(0.15, 0.15, BX, ZBk, 0.45);

  var jetStand = new T.Group(); S.scene.add(jetStand);
  var jbase = S.rounded(0.16, 0.12, 0.022, 0.006, M.iron); jbase.rotation.x = -Math.PI / 2; jbase.position.y = 0.011; jetStand.add(jbase);
  var jrod = S.mesh(new T.CylinderGeometry(0.0075, 0.0085, 0.42, 18), M.chrome); jrod.position.y = 0.23; jetStand.add(jrod);
  jetStand.position.set(BX + 0.12, 0, ZBk - 0.06); S.contact(0.2, 0.16, BX + 0.12, ZBk - 0.06, 0.45);
  var jetClamp = new T.Group(); S.scene.add(jetClamp);
  var jc = S.rounded(0.04, 0.036, 0.036, 0.005, M.alu); jetClamp.add(jc);
  var jarm = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.12, 14), M.chrome); jarm.rotation.z = Math.PI / 2; jarm.position.x = -0.06; jetClamp.add(jarm);
  var jthumb = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.007, 6), M.black); jthumb.rotation.x = Math.PI / 2; jthumb.position.z = 0.022; jetClamp.add(jthumb);

  var jet = new T.Group(); S.scene.add(jet);
  var jtube = S.mesh(new T.CylinderGeometry(0.0038, 0.0038, 0.2, 18), glassM, false); jtube.position.y = 0.1; jet.add(jtube);
  var jtip = S.mesh(new T.ConeGeometry(0.0038, 0.016, 16), glassM, false); jtip.rotation.x = Math.PI; jtip.position.y = -0.008; jet.add(jtip);
  var bubble = S.mesh(new T.SphereGeometry(0.0055, 18, 12), new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.02, transmission: 0.75, transparent: true, opacity: 0.4, depthWrite: false }), false);
  jet.add(bubble);

  var tubeM = new T.MeshStandardMaterial({ color: 0x3f4248, roughness: 0.85 });
  function tubeBetween(a, b, r) {                       // a straight length of rubber tubing from a to b
    var va = new T.Vector3(a[0], a[1], a[2]), vb = new T.Vector3(b[0], b[1], b[2]);
    var d = vb.clone().sub(va), len = d.length();
    var m = S.mesh(new T.CylinderGeometry(r || 0.0035, r || 0.0035, len, 12), tubeM, false);
    m.position.copy(va).add(vb).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize());
    S.scene.add(m); return m;
  }
  var JOINT = [MX, MBOT + MLEN + 0.05, ZM - 0.01];      // the T-piece above the manometer
  var line1 = tubeBetween([AX, 0.03, ZA + 0.055], [AX, 0.3, ZA + 0.055]);
  var line1b = tubeBetween([AX, 0.3, ZA + 0.055], JOINT);
  var line2 = tubeBetween(JOINT, [MX - MSEP / 2, MBOT + MLEN - 0.02, ZM]);
  var line3 = tubeBetween(JOINT, [BX, 0.33, ZBk]);
  var line4 = tubeBetween([BX, 0.33, ZBk], [BX, 0.26, ZBk], 0.004);
  var tee = S.mesh(new T.SphereGeometry(0.0055, 12, 10), tubeM, false);
  tee.position.set(JOINT[0], JOINT[1], JOINT[2]); S.scene.add(tee);

  // ---------- the depth scale beside the beaker
  var DLEN = 0.22, DTOP = 0.3;
  var dscale = S.ruler(DLEN, { title: 'DEPTH · cm', labelEvery: 10, width: 0.022 });
  dscale.position.set(BX - 0.085, DTOP - DLEN, ZBk + 0.02); S.scene.add(dscale);
  var dfoot = S.rounded(0.07, 0.06, 0.028, 0.006, M.darkWood); dfoot.rotation.x = -Math.PI / 2;
  dfoot.position.set(BX - 0.085, DTOP - DLEN + 0.012, ZBk + 0.02); S.scene.add(dfoot);
  S.contact(0.1, 0.09, BX - 0.085, ZBk + 0.02, 0.45);
  function depthCm(y) { return (DTOP - y) * 100; }

  var therm = TC === null ? null : S.thermometer({ len: 0.2, min: 0, max: 100, value: TC, pos: [BX - 0.035, 0.01, ZBk + 0.045] });

  S.addApparatus('asp', asp, 'Aspirator bottle', 'Water running out of it pushes air slowly into the apparatus: one bubble every few seconds is the right rate.');
  S.addApparatus('mano', mano, 'Water manometer', 'Its difference of level is the pressure inside the bubble. Read with a vernier to ' + (MLC * 100).toFixed(2) + ' cm.');
  S.addApparatus('jet', jet, 'Capillary jet', 'Drawn to an orifice of radius ' + (p.r * 1000).toFixed(2) + ' mm, measured with a travelling microscope before it is dipped.');
  S.addApparatus('beaker', beaker, 'Beaker of ' + LIQ.name, 'The liquid under test' + (TC === null ? '' : ', at ' + TC + ' °C') + '. A fresh surface is made for every bubble, so grease on the old surface does not matter.');
  S.addApparatus('dscale', dscale, 'Depth scale', 'Reads the liquid surface and the orifice: h is their difference.');
  if (therm) S.addApparatus('therm', therm, 'Thermometer', 'Surface tension falls steadily as a liquid is warmed, so the temperature is part of the answer.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudD = S.hudCard('Depth of the orifice'), hudH = S.hudCard('Manometer H'), hudB = S.hudCard('Bubbles');

  // ---------- state
  function orificeY() { return SURF - p.hd; }
  function placeJet() {
    var y = orificeY();
    jet.position.set(BX, y, ZBk);
    jetClamp.position.set(BX + 0.06, y + 0.17, ZBk - 0.03);
  }
  function setDepth(i) {
    if (S.hand.busy) return Promise.resolve();
    if (st.open) { S.say('Close the stopcock before moving the jet.'); return Promise.resolve(); }
    var y0 = orificeY();
    st.di = i;
    var y1 = SURF - DEPTHS[i];
    st.read = [null, null]; st.H = null; st.settled = false;
    return S.hand.pinchMove(new T.Vector3(BX + 0.06, y0 + 0.17, ZBk - 0.03), function (k) {
      return new T.Vector3(BX + 0.06, y0 + 0.17 + (y1 - y0) * k, ZBk - 0.03);
    }, function (k) { p.hd = Math.max(0.005, SURF - (y0 + (y1 - y0) * k)); placeJet(); }, { ms: 900, hold: 180, mode: 'side' })
      .then(function () {
        p.hd = DEPTHS[i]; placeJet(); sim = K.init(p);
        S.say('Jet lowered to about ' + (p.hd * 100).toFixed(1) + ' cm below the surface. Read the depth scale.');
        S.render();
      });
  }
  function measureOrifice() {
    st.rDone = true;
    S.say('Orifice radius ' + (p.r * 1000).toFixed(2) + ' mm, measured with a travelling microscope.');
    if (ready) S.render();
  }
  function readDepth(which) {                           // 0 = the liquid surface, 1 = the orifice
    var y = which === 0 ? SURF : orificeY();
    st.read[which] = Math.round(depthCm(y) * 10) / 10;
    if (bothRead()) S.say('Surface at ' + st.read[0].toFixed(1) + ' cm, orifice at ' + st.read[1].toFixed(1) + ' cm, so h = ' + hCm().toFixed(1) + ' cm.');
    else S.say((which === 0 ? 'The liquid surface' : 'The orifice') + ' reads ' + st.read[which].toFixed(1) + ' cm.');
    if (ready) S.render();
  }
  function bothRead() { return st.read[0] !== null && st.read[1] !== null; }
  function hCm() { return bothRead() ? Math.round((st.read[1] - st.read[0]) * 10) / 10 : 0; }

  function openTap() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.rDone) { S.say('Measure the orifice with the travelling microscope first.'); return Promise.resolve(); }
    if (!bothRead()) { S.say('Measure the depth on the scale first.'); return Promise.resolve(); }
    return S.hand.tap(aknob).then(function () {
      S.click(1200); st.open = !st.open;
      if (st.open) { sim = K.init(p); st.settled = false; S.say('Stopcock just open: bubbles are forming at the orifice.'); }
      else S.say('Stopcock closed.');
      S.render();
    });
  }
  function readMano() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.settled) { S.say('Wait until the bubbles are coming at a steady rate and the maximum reading repeats.'); return Promise.resolve(); }
    st.H = Math.floor(sim.H / MLC + 0.5) * MLC;
    S.say('Greatest manometer difference H = ' + (st.H * 100).toFixed(2) + ' cm.');
    S.render();
    return Promise.resolve();
  }
  function recordRow() {
    if (st.H === null) { S.say('Read the manometer first.'); return; }
    S.addRow({ hd: hCm() / 100, hcm: hCm(), H: st.H, Hcm: st.H * 100 });
    S.say('Written in your record book: h = ' + hCm().toFixed(1) + ' cm, H = ' + (st.H * 100).toFixed(2) + ' cm.');
    st.H = null; S.render();
  }
  function oneDepth() {
    return openTap().then(function () {
      S.advance(40, function () { return st.settled; });
      return readMano();
    }).then(function () { recordRow(); return openTap(); });
  }
  function depthsDone() { var o = {}; S.rows.forEach(function (r) { o[r.hcm.toFixed(1)] = 1; }); return Object.keys(o).length; }

  placeJet();

  var EXP = {
    camera: { pos: [0.72, 0.72, 1.35], look: [-0.02, 0.2, -0.13] },
    views: {
      setup: [[0.7, 0.7, 1.3], [-0.02, 0.2, -0.13]],
      asp: [[-0.22, 0.4, 0.4], [AX + 0.02, 0.14, -0.14]],
      mano: [[0.06, 0.44, 0.58], [MX, 0.2, -0.16]],
      jet: [[0.5, 0.26, 0.4], [BX, 0.1, -0.12]],
      beaker: [[0.48, 0.3, 0.44], [BX, 0.09, -0.12]],
      dscale: [[0.38, 0.28, 0.42], [BX - 0.06, 0.14, -0.1]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A bubble forced out of a fine orifice grows, and its radius of curvature falls until it equals the '
        + 'radius of the orifice. At that instant the excess pressure inside it is greatest and the bubble breaks away, '
        + 'so the manometer reads a maximum.',
      formula: 'H ρₘ g = h ρₗ g + 2T / r',
      formulaNote: 'so T = r g (H ρₘ − h ρₗ) / 2, with r = ' + (p.r * 1000).toFixed(2)
        + ' mm, ρₗ = ' + p.rhol.toFixed(1) + ' kg/m³ and ρₘ = ' + p.rhom.toFixed(1) + ' kg/m³',
      more: ['A graph of H against h is a straight line of slope ρₗ/ρₘ whose intercept is 2T/(r g ρₘ).',
        'Because a fresh surface is made for every bubble, the method gives the surface tension of a clean surface even when the old one is contaminated.',
        'Warming the liquid lowers T, and the method follows that change easily: it is the usual way of measuring how surface tension varies with temperature.'],
      precautions: 'Open the stopcock only a little: a fast stream of air throws liquid about and the maximum reading means '
        + 'nothing. Take the reading only when the same maximum repeats over several bubbles. Keep the jet vertical and the '
        + 'orifice well away from the walls of the beaker.'
    },
    book: {
      title: 'Expt. — Jaeger’s bubble method',
      lines: ['Aim: to find the surface tension of ' + LIQ.name + (TC === null ? '' : ' at ' + TC + ' °C') + '.',
        'Orifice radius r = ' + (p.r * 1000).toFixed(2) + ' mm (travelling microscope)',
        'ρ of the liquid = ' + p.rhol.toFixed(1) + ' kg/m³, manometer liquid = ' + p.rhom.toFixed(1) + ' kg/m³',
        'h = (orifice reading) − (surface reading)', 'H = greatest manometer difference',
        'T = r g (H ρₘ − h ρₗ) / 2'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'h (cm)', get: function (r) { return r.hcm.toFixed(1); } },
        { label: 'H (cm)', get: function (r) { return r.Hcm.toFixed(2); } },
        { label: 'H − h (cm)', get: function (r) { return (r.Hcm - r.hcm).toFixed(2); } }]
    },
    graph: {
      x: function (r) { return r.hcm; }, y: function (r) { return r.Hcm; },
      xlabel: 'h (cm)', ylabel: 'H (cm)', x0: 0, y0: 0,
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; }
    },
    result: function (rows) {
      if (rows.length < 2) return null;
      var v = HK.CALCS.jaeger_T.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      return { label: 'T of ' + LIQ.name, value: v, unit: 'N/m', digits: 5, truth: p.Tst,
        note: 'Mean of r g (H ρₘ − h ρₗ)/2 over the depths used.' };
    },
    tol: 0.02,
    chips: ['Why is the manometer reading a maximum as the bubble breaks away?',
      'Why does a fresh surface matter?', 'Check my readings', 'What does the intercept of the graph give?',
      'How does temperature change the surface tension?'],
    viva: [['The manometer reads a maximum just as the bubble breaks away because',
      ['the bubble’s radius of curvature is then least', 'the air runs out', 'the liquid cools'], 0,
      'Excess pressure is 2T/R, and R is least when it equals the orifice radius.'],
      ['A wider orifice gives, for the same liquid,', ['a smaller manometer reading', 'a larger reading', 'the same reading'], 0,
        'The excess pressure 2T/r falls as r rises.']],
    askState: function () {
      return {
        depth_set_cm: +(p.hd * 100).toFixed(1), measured_depth_cm: bothRead() ? hCm() : null,
        surface_reading_cm: st.read[0], orifice_reading_cm: st.read[1],
        orifice_radius_mm: st.rDone ? +(p.r * 1000).toFixed(2) : null,
        stopcock_open: st.open, manometer_now_cm: +(sim.H * 100).toFixed(2), steady: st.settled,
        recorded_H_cm: st.H === null ? null : +(st.H * 100).toFixed(2), liquid: LIQ.name, temperature_C: TC
      };
    },

    steps: [
      { id: 'set', title: 'Set the depth', view: 'jet',
        render: function (u) {
          u.h2('Measure the orifice and set the depth');
          u.p('The orifice radius comes straight into the answer, so it is measured first with a travelling microscope. '
            + 'Then lower the jet to a measured depth below the surface.');
          u.task('Measure the orifice radius', st.rDone, st.rDone ? (p.r * 1000).toFixed(2) + ' mm' : 'Not measured yet')
            .add(u.button('Measure it', function () { S.focus('jet'); measureOrifice(); }, !st.rDone, st.rDone));
          var r = u.row();
          DEPTHS.forEach(function (d, i) {
            r.appendChild(u.button((d * 100).toFixed(1) + ' cm' + (st.di === i ? ' ✓' : ''), function () { setDepth(i).then(function () { S.focus('dscale'); }); }, st.di === i, S.hand.busy || st.open));
          });
          u.task('1. Read the liquid surface', st.read[0] !== null, st.read[0] !== null ? st.read[0].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('beaker'); readDepth(0); }, st.read[0] === null, st.read[0] !== null));
          u.task('2. Read the orifice', st.read[1] !== null, st.read[1] !== null ? st.read[1].toFixed(1) + ' cm' : 'Not read yet')
            .add(u.button('Read', function () { S.focus('dscale'); readDepth(1); }, st.read[1] === null, st.read[1] !== null));
          if (bothRead()) u.formula('h = ' + st.read[1].toFixed(1) + ' − ' + st.read[0].toFixed(1) + ' = ' + hCm().toFixed(1) + ' cm');
          u.next('Next: blow the bubbles', st.rDone && bothRead());
        },
        ok: function () { return st.rDone && bothRead(); },
        auto: function () { measureOrifice(); readDepth(0); readDepth(1); return Promise.resolve(); } },

      { id: 'bub', title: 'Bubble and read', view: 'mano',
        render: function (u) {
          u.h2('Open the stopcock and read the greatest manometer difference');
          u.p('One bubble every few seconds is the right rate. Watch the manometer through several bubbles and take the '
            + 'maximum it reaches, which should repeat.');
          var r = u.row();
          DEPTHS.forEach(function (d, i) {
            r.appendChild(u.button((d * 100).toFixed(1) + ' cm' + (st.di === i ? ' ✓' : ''), function () { setDepth(i).then(function () { S.focus('mano'); }); }, st.di === i, S.hand.busy || st.open));
          });
          u.task('Measure the depth for this setting', bothRead(), bothRead() ? 'h = ' + hCm().toFixed(1) + ' cm' : 'Not measured yet')
            .add(u.button('Measure it', function () { readDepth(0); readDepth(1); }, !bothRead(), bothRead()));
          u.row(u.button(st.open ? 'Close the stopcock' : 'Open the stopcock', function () { openTap(); }, !st.open, S.hand.busy || !bothRead()),
            u.button('Read the manometer', function () { readMano(); }, st.H === null, S.hand.busy || !st.settled),
            u.button('Write this reading down', function () { recordRow(); }, false, S.hand.busy || st.H === null));
          u.live(function () {
            return 'h = ' + (p.hd * 100).toFixed(1) + ' cm · manometer ' + (sim.H * 100).toFixed(2) + ' cm · '
              + (st.open ? (st.settled ? 'steady' : 'rising') : 'stopcock closed');
          });
          u.h3('Observation table'); u.table();
          var n = depthsDone();
          u.next('Next: work out T', n >= 3);
          if (n < 3) u.p(n + ' of at least 3 depths done. Move the jet, measure h again and read the manometer.');
        },
        ok: function () { return depthsDone() >= 3; },
        auto: function () {
          return [3, 1, 0].reduce(function (pr, i) {
            return pr.then(function () { return setDepth(i); })
              .then(function () { readDepth(0); readDepth(1); return oneDepth(); });
          }, Promise.resolve());
        } }
    ],

    tick: function (dt) {
      if (st.open) {
        K.step(sim, p, dt);
        var v = K.view(sim, p);
        if (v.steady >= 1) st.settled = true;
      }
      pose();
    },
    ready: function () { ready = true; }
  };
  function pose() {
    var H = sim.H, half = H / 2;
    var lTop = MBOT + 0.06 - half, rTop = MBOT + 0.06 + half;
    mcol[0].scale.y = Math.max(0.002, lTop - MBOT); mcol[0].position.y = (lTop + MBOT) / 2;
    mcol[1].scale.y = Math.max(0.002, rTop - MBOT); mcol[1].position.y = (rTop + MBOT) / 2;
    var ph = st.open ? ((sim.t * 0.8) % 1) : 0;
    bubble.visible = st.open;
    var br = 0.0012 + ph * (Math.max(0.0035, p.r * 12) - 0.0012);
    bubble.scale.set(br / 0.0055, br / 0.0055, br / 0.0055);
    bubble.position.set(0, -0.016 - br * 0.6, 0);
    hudD.set((p.hd * 100).toFixed(1) + ' cm');
    hudH.set((H * 100).toFixed(2) + ' cm');
    hudB.set(st.open ? (st.settled ? 'steady' : 'starting') : 'off');
  }
  pose();
  return EXP;
});
