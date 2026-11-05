/* Prayogshala studio module: the travelling microscope bench (B.Sc. measurement and error analysis).
   A heavy levelled base carries a horizontal rail with a millimetre main scale and a fifty-division vernier, a vertical
   pillar with its own scale, and a low-power microscope with cross-wires in the eyepiece. The object lies on the glass
   stage, lit from the side by a small lamp. A fine screw slides the carriage.
   The gloved hand turns the fine screw to set the cross-wire first on one edge of the object and then on the other; the
   difference of the two vernier readings is one measurement, and the whole thing is done over and over.
   Physics: the `travmicro` kernel of the mech_ug pack - the least count is pitch / vernier divisions, and the readings
   scatter about the true size with a fixed, reproducible spread. One rig serves both the least-count lab and the
   random-error lab; every number comes from the lab's params. */
HoolaStudio.define('travelling-microscope', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.travmicro;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('travmicro');
  var SAMPLE = String((S.lab.variant || {}).sample || '');
  var OBJ = /wire/i.test(SAMPLE) ? { name: 'wire', kind: 'wire' } : /plate|glass/i.test(SAMPLE) ? { name: 'glass plate', kind: 'plate' }
    : /sphere|ball/i.test(SAMPLE) ? { name: 'steel sphere', kind: 'sphere' } : { name: 'steel disc', kind: 'disc' };
  var NREP = Math.max(3, Math.round(p.nrep));
  var LC = p.pitch / p.ndiv;                       // the least count, in metres
  var BASE = Math.round(0.012 / LC) * LC;          // the first cross-wire setting: a round number on the scale
  var st = { i: 0, lcDone: false, side: 0, A: null, B: null };
  var ready = false;

  function split(r) {                              // a vernier reading: main-scale part + the coinciding vernier division
    var nd = Math.floor(r / LC + 0.5), whole = Math.floor(nd / p.ndiv);
    return { msr: whole * p.pitch, vsd: nd - whole * p.ndiv, total: nd * LC };
  }
  function reading(i) { var q = HK.assign(p, { idx: i }); return K.view(K.init(q), q).x; }

  // ---------- geometry: the rail runs along x at z = ZR; the stage is in front of it
  var ZR = -0.2, RAILY = 0.035, CARY = 0.14, STZ = -0.055;
  var base = S.rounded(0.52, 0.32, 0.026, 0.008, new T.MeshStandardMaterial({ color: 0x343a41, roughness: 0.55, metalness: 0.4 }));
  base.rotation.x = -Math.PI / 2; base.position.set(0, 0.013, -0.1); S.scene.add(base);
  S.contact(0.58, 0.38, 0, -0.1, 0.55);
  [[-0.22, -0.2], [0.22, -0.2], [-0.22, 0.0], [0.22, 0.0]].forEach(function (f) {
    var lv = S.mesh(new T.CylinderGeometry(0.009, 0.011, 0.018, 16), M.chrome); lv.position.set(f[0], 0.009, f[1] - 0.0); S.scene.add(lv);
  });
  var rail = S.rounded(0.46, 0.07, 0.03, 0.004, new T.MeshStandardMaterial({ color: 0x4a5058, roughness: 0.4, metalness: 0.6 }));
  rail.position.set(0, RAILY, ZR); S.scene.add(rail);
  var hscale = S.ruler(0.4, { title: 'MAIN SCALE · mm', labelEvery: 10, width: 0.03, thick: 0.004, pxPerMm: 2 });
  hscale.rotation.z = Math.PI / 2; hscale.position.set(0.2, RAILY + 0.016, ZR + 0.034); S.scene.add(hscale);

  var carriage = new T.Group(); S.scene.add(carriage);
  var cbody = S.rounded(0.075, 0.07, 0.07, 0.006, new T.MeshStandardMaterial({ color: 0x3d434a, roughness: 0.45, metalness: 0.55 }));
  cbody.position.y = RAILY + 0.035; carriage.add(cbody);
  var vplate = S.rounded(0.05, 0.022, 0.004, 0.002, M.brass); vplate.position.set(0, RAILY + 0.016, ZR * 0 + 0.038); carriage.add(vplate);
  var vTex = S.canvasTex(512, 64, function (x, w, h) {
    x.fillStyle = '#d9b24c'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#1b1b1d'; x.font = '600 20px "Public Sans", sans-serif';
    for (var i = 0; i <= 10; i++) { var px = 6 + i * (w - 14) / 10; x.fillRect(px, 0, 2, i % 5 === 0 ? h * 0.6 : h * 0.4); if (i % 5 === 0) x.fillText(String(i * 5), px + 3, h - 6); }
  });
  var vFace = new T.Mesh(new T.PlaneGeometry(0.05, 0.012), new T.MeshStandardMaterial({ map: vTex, roughness: 0.5 }));
  vFace.position.set(0, RAILY + 0.018, 0.0405); carriage.add(vFace);
  var pillar = S.rounded(0.045, 0.045, 0.26, 0.005, new T.MeshStandardMaterial({ color: 0x343a41, roughness: 0.5, metalness: 0.45 }));
  pillar.position.set(-0.05, RAILY + 0.16, 0); carriage.add(pillar);
  var vscale = S.ruler(0.2, { title: 'VERTICAL · mm', labelEvery: 10, width: 0.022, thick: 0.003, pxPerMm: 2 });
  vscale.position.set(-0.05, RAILY + 0.04, 0.024); carriage.add(vscale);
  var tube = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.15, 24), M.black); tube.rotation.x = Math.PI / 2; tube.position.set(0.0, CARY, 0.035); carriage.add(tube);
  var eye = S.mesh(new T.CylinderGeometry(0.012, 0.013, 0.035, 20), new T.MeshStandardMaterial({ color: 0x17181a, roughness: 0.4 }));
  eye.rotation.x = Math.PI / 2; eye.position.set(0, CARY, 0.125); carriage.add(eye);
  var obj = S.mesh(new T.CylinderGeometry(0.0095, 0.0095, 0.022, 16), M.chrome); obj.rotation.x = Math.PI / 2; obj.position.set(0, CARY, -0.048); carriage.add(obj);
  var holder = S.mesh(new T.BoxGeometry(0.014, 0.075, 0.014), new T.MeshStandardMaterial({ color: 0x3d434a, roughness: 0.5 }));
  holder.position.set(0, CARY - 0.045, 0.01); carriage.add(holder);
  var screw = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.012, 24), M.brass); screw.rotation.z = Math.PI / 2; screw.position.set(-0.052, RAILY + 0.012, 0.012); carriage.add(screw);
  carriage.position.set(0, 0, ZR);

  // the glass stage with the object on it, and a lamp
  var stage = new T.Group(); S.scene.add(stage);
  var sglass = new T.Mesh(new T.BoxGeometry(0.16, 0.005, 0.11), new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.04, transparent: true, opacity: 0.25, transmission: 0.6, depthWrite: false }));
  sglass.position.y = 0.032; stage.add(sglass);
  [-1, 1].forEach(function (s) { var sp = S.mesh(new T.BoxGeometry(0.012, 0.03, 0.09), M.alu); sp.position.set(s * 0.07, 0.016, 0); stage.add(sp); });
  var specM = new T.MeshStandardMaterial({ color: OBJ.kind === 'plate' ? 0xcfe3e6 : 0xd3d8dd, roughness: OBJ.kind === 'plate' ? 0.05 : 0.2, metalness: OBJ.kind === 'plate' ? 0.0 : 0.95,
    transparent: OBJ.kind === 'plate', opacity: OBJ.kind === 'plate' ? 0.55 : 1 });
  var SIZE = Math.max(0.004, Math.min(0.06, p.L));
  var spec = OBJ.kind === 'wire' ? S.mesh(new T.CylinderGeometry(Math.max(0.0006, SIZE / 2), Math.max(0.0006, SIZE / 2), 0.09, 14), specM)
    : OBJ.kind === 'plate' ? S.mesh(new T.BoxGeometry(SIZE, 0.004, 0.05), specM)
      : OBJ.kind === 'sphere' ? S.mesh(new T.SphereGeometry(SIZE / 2, 18, 12), specM)
        : S.mesh(new T.CylinderGeometry(SIZE / 2, SIZE / 2, 0.006, 28), specM);
  if (OBJ.kind === 'wire') spec.rotation.x = Math.PI / 2;
  spec.position.set(0, 0.0355 + (OBJ.kind === 'sphere' ? SIZE / 2 : OBJ.kind === 'wire' ? SIZE / 2 : 0.004), 0);
  stage.add(spec);
  stage.position.set(0, 0, STZ); S.contact(0.19, 0.14, 0, STZ, 0.35);

  var lamp = new T.Group(); S.scene.add(lamp);
  var lhead = S.mesh(new T.CylinderGeometry(0.022, 0.026, 0.04, 20), new T.MeshStandardMaterial({ color: 0x3a4149, roughness: 0.5 }));
  lhead.rotation.z = 1.25; lhead.position.y = 0.075; lamp.add(lhead);
  var lstem = S.mesh(new T.CylinderGeometry(0.005, 0.006, 0.08, 14), M.chrome); lstem.position.y = 0.04; lamp.add(lstem);
  var lbase = S.rounded(0.07, 0.06, 0.016, 0.005, M.iron); lbase.rotation.x = -Math.PI / 2; lbase.position.y = 0.008; lamp.add(lbase);
  lamp.position.set(-0.19, 0, STZ + 0.01); S.contact(0.1, 0.09, -0.19, STZ + 0.01, 0.4);
  var plate2 = S.label('TRAVELLING  MICROSCOPE  ·  L.C.  0.001 cm', { w: 0.2, ratio: 0.09, color: '#d7dbe0', weight: 600 });
  plate2.rotation.x = -Math.PI / 2; plate2.position.set(0, 0.027, 0.035); S.scene.add(plate2);

  S.addApparatus('micro', carriage, 'Travelling microscope', 'A low-power microscope on a carriage. Its vernier reads how far the carriage has moved, to '
    + (LC * 1000).toFixed(3) + ' mm.');
  S.addApparatus('stage', stage, 'Glass stage with the ' + OBJ.name, 'The object being measured. The cross-wire is set on one edge, then on the other.');
  S.addApparatus('lamp', lamp, 'Lamp', 'Lights the object from the side, so each edge is sharp against the background.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudR = S.hudCard('Vernier reading'), hudN = S.hudCard('Readings taken'), hudM = S.hudCard('Mean so far');

  // ---------- actions
  function moveTo(xm) {                            // the carriage position on the bench for a scale reading of xm metres
    carriage.position.x = -0.1 + (xm - BASE) * 3.0;
  }
  function setLc() {
    st.lcDone = true;
    S.say('Main scale pitch ' + (p.pitch * 1000).toFixed(1) + ' mm, ' + p.ndiv.toFixed(0) + ' vernier divisions, so the least count is '
      + (LC * 1000).toFixed(3) + ' mm = ' + (LC * 100).toFixed(4) + ' cm.');
    if (ready) S.render();
  }
  function setOn(side) {                           // 0 = first edge, 1 = second edge
    if (S.hand.busy) return Promise.resolve();
    var x = reading(st.i), target = side === 0 ? BASE : BASE + x;
    var from = new T.Vector3(carriage.position.x - 0.06, RAILY + 0.05, ZR + 0.03);
    var to = new T.Vector3(-0.1 + (target - BASE) * 3.0 - 0.06, RAILY + 0.05, ZR + 0.03);
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); }, function (k) {
      var cur = BASE + (target - BASE) * k; moveTo(cur);
    }, { ms: 700, hold: 150, mode: 'side' }).then(function () {
      moveTo(target);
      if (side === 0) { st.A = BASE; st.B = null; S.say('Cross-wire set on the first edge: ' + fmtRead(BASE) + '.'); }
      else { st.B = target; S.say('Cross-wire set on the other edge: ' + fmtRead(target) + '.'); }
      st.side = side;
      S.render();
    });
  }
  function fmtRead(r) {
    var q = split(r);
    return 'M.S.R. ' + (q.msr * 100).toFixed(2) + ' cm + ' + q.vsd + ' × ' + (LC * 100).toFixed(4)
      + ' cm = ' + (q.total * 100).toFixed(4) + ' cm';
  }
  function recordReading() {
    if (st.A === null || st.B === null) { S.say('Set the cross-wire on both edges first.'); return; }
    var x = Math.round((st.B - st.A) / LC) * LC;
    S.addRow({ n: st.i + 1, A: st.A, B: st.B, x: x });
    st.i = st.i + 1; st.A = null; st.B = null;
    S.say('Reading ' + st.i + ' written in your record book: ' + (x * 1000).toFixed(3) + ' mm.');
    if (ready) S.render();
  }
  function oneReading() { return setOn(0).then(function () { return setOn(1); }).then(function () { recordReading(); }); }
  function meanSoFar() {
    if (!S.rows.length) return null;
    var s = 0; S.rows.forEach(function (r) { s += r.x; });
    return s / S.rows.length;
  }
  function sdSoFar() {
    var n = S.rows.length; if (n < 2) return null;
    var m = meanSoFar(), v = 0;
    S.rows.forEach(function (r) { v += (r.x - m) * (r.x - m); });
    return Math.sqrt(v / (n - 1));
  }

  moveTo(BASE);

  var EXP = {
    camera: { pos: [0.34, 0.33, 0.46], look: [0.0, 0.1, -0.12] },
    views: {
      setup: [[0.33, 0.32, 0.45], [0.0, 0.1, -0.12]],
      micro: [[0.2, 0.24, 0.3], [-0.04, 0.11, -0.14]],
      scale: [[0.1, 0.17, 0.2], [-0.05, 0.065, -0.15]],
      stage: [[0.12, 0.17, 0.2], [0.0, 0.05, -0.06]],
      book: [[-0.34, 0.5, 0.56], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'The least count of a vernier instrument is one main-scale division divided by the number of vernier '
        + 'divisions. Setting a cross-wire on an edge is a judgement, so repeated measurements of the same object scatter; '
        + 'their mean is the best estimate and the standard error of the mean says how well it is known.',
      formula: 'L.C. = pitch / N,   x̄ = Σx/n,   s = √(Σ(x − x̄)²/(n − 1)),   S.E. = s/√n',
      formulaNote: 'Here pitch = ' + (p.pitch * 1000).toFixed(1) + ' mm and N = ' + p.ndiv.toFixed(0)
        + ', so L.C. = ' + (LC * 1000).toFixed(3) + ' mm = ' + (LC * 100).toFixed(4) + ' cm.',
      more: ['A random error is as likely to be above the true value as below it, so it shrinks as 1/√n when readings are repeated. A systematic error does not.',
        'The answer is written as mean ± standard error, and to no more decimal places than the least count justifies.',
        'A vernier reading is the main-scale mark just before the index, plus the number of the vernier division that lines up, times the least count.'],
      precautions: 'Always turn the fine screw the same way when setting the cross-wire, so backlash in the screw does not '
        + 'creep into the readings. Keep your eye square to the eyepiece. Do not lean on the bench while a reading is being taken.'
    },
    book: {
      title: 'Expt. — Travelling microscope',
      lines: ['Aim: to measure a small dimension and report it with its uncertainty.',
        'Pitch = ' + (p.pitch * 1000).toFixed(1) + ' mm, vernier divisions = ' + p.ndiv.toFixed(0),
        'L.C. = ' + (LC * 100).toFixed(4) + ' cm', 'Reading = M.S.R. + V.S.D. × L.C.',
        'x = (second edge) − (first edge)', 'Report x̄ ± s/√n'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Edge 1 (cm)', get: function (r) { return (r.A * 100).toFixed(4); } },
        { label: 'Edge 2 (cm)', get: function (r) { return (r.B * 100).toFixed(4); } },
        { label: 'x (cm)', get: function (r) { return (r.x * 100).toFixed(4); } }]
    },
    graph: {
      x: function (r, i) { return r.n; }, y: function (r) { return r.x * 1000; },
      xlabel: 'reading number', ylabel: 'x (mm)', line: null
    },
    result: function (rows) {
      if (rows.length < 3) return null;
      var v = HK.CALCS.tm_mean.fn(rows, p);
      if (!isFinite(v) || v <= 0) return null;
      var sd = sdSoFar(), se = sd === null ? 0 : sd / Math.sqrt(rows.length);
      return { label: 'Mean size of the ' + OBJ.name, value: v, unit: 'm', digits: 6, truth: p.L,
        note: 'Standard deviation ' + ((sd || 0) * 1000).toFixed(3) + ' mm, standard error ' + (se * 1000).toFixed(3)
          + ' mm over ' + rows.length + ' readings.' };
    },
    tol: 0.02,
    chips: ['How is the least count worked out?', 'Why repeat the measurement?', 'Check my readings',
      'What is the difference between a random and a systematic error?', 'Why always turn the screw the same way?'],
    viva: [['The least count of this instrument is', [(LC * 100).toFixed(4) + ' cm', (p.pitch * 100).toFixed(3) + ' cm', '0.1 cm'], 0,
      'Pitch divided by the number of vernier divisions.'],
      ['Taking four times as many readings changes the standard error of the mean to', ['half', 'a quarter', 'the same'], 0,
        'The standard error goes as 1/√n.']],
    askState: function () {
      return {
        least_count_cm: +(LC * 100).toFixed(4), readings_taken: S.rows.length, readings_wanted: NREP,
        first_edge_cm: st.A === null ? null : +(st.A * 100).toFixed(4),
        second_edge_cm: st.B === null ? null : +(st.B * 100).toFixed(4),
        mean_so_far_mm: meanSoFar() === null ? null : +(meanSoFar() * 1000).toFixed(3),
        sd_so_far_mm: sdSoFar() === null ? null : +(sdSoFar() * 1000).toFixed(3),
        object: OBJ.name
      };
    },

    steps: [
      { id: 'lc', title: 'Least count', view: 'scale',
        render: function (u) {
          u.h2('Work out the least count');
          u.p('Count how far one main-scale division is and how many divisions the vernier carries. The least count is '
            + 'the first divided by the second.');
          u.task('Read the scales', st.lcDone, st.lcDone ? 'L.C. = ' + (LC * 100).toFixed(4) + ' cm' : 'Not read yet')
            .add(u.button('Read them', function () { S.focus('scale'); setLc(); }, !st.lcDone, st.lcDone));
          if (st.lcDone) u.formula('L.C. = ' + (p.pitch * 1000).toFixed(1) + ' mm ÷ ' + p.ndiv.toFixed(0)
            + ' = ' + (LC * 1000).toFixed(3) + ' mm = ' + (LC * 100).toFixed(4) + ' cm');
          u.note('No reading may be written to more decimal places than the least count allows.');
          u.next('Next: measure the ' + OBJ.name, st.lcDone);
        },
        ok: function () { return st.lcDone; },
        auto: function () { setLc(); return Promise.resolve(); } },

      { id: 'read', title: 'Repeat the measurement', view: 'micro',
        render: function (u) {
          u.h2('Measure the ' + OBJ.name + ', ' + NREP + ' times over');
          u.p('Set the cross-wire on one edge and read the vernier; move the carriage to the other edge and read again. '
            + 'The difference is one measurement. Then start afresh and do it again.');
          u.task('1. Cross-wire on the first edge', st.A !== null, st.A !== null ? fmtRead(st.A) : 'Not set')
            .add(u.button('Set and read', function () { setOn(0); }, st.A === null, S.hand.busy || st.A !== null));
          u.task('2. Cross-wire on the other edge', st.B !== null, st.B !== null ? fmtRead(st.B) : 'Not set')
            .add(u.button('Set and read', function () { setOn(1); }, st.B === null, S.hand.busy || st.A === null || st.B !== null));
          u.row(u.button('Write this reading down', function () { recordReading(); }, true, S.hand.busy || st.A === null || st.B === null));
          u.live(function () {
            var m = meanSoFar(), sd = sdSoFar();
            return S.rows.length + ' of ' + NREP + ' readings'
              + (m === null ? '' : ' · mean ' + (m * 1000).toFixed(3) + ' mm')
              + (sd === null ? '' : ' · s = ' + (sd * 1000).toFixed(3) + ' mm');
          });
          u.h3('Observation table'); u.table();
          u.next('Next: the mean and its error', S.rows.length >= NREP);
          if (S.rows.length < NREP) u.p('Take ' + (NREP - S.rows.length) + ' more. Each one must be an independent setting of the cross-wire.');
        },
        ok: function () { return S.rows.length >= NREP; },
        auto: function () {
          var seq = Promise.resolve();
          for (var i = 0; i < NREP; i++) seq = seq.then(oneReading);
          return seq;
        } }
    ],

    tick: function () { pose(); },
    ready: function () { ready = true; }
  };
  function pose() {
    var cur = BASE + (carriage.position.x + 0.1) / 3.0;
    hudR.set((split(cur).total * 100).toFixed(4) + ' cm');
    hudN.set(S.rows.length + ' / ' + NREP);
    var m = meanSoFar();
    hudM.set(m === null ? '—' : (m * 1000).toFixed(3) + ' mm');
  }
  pose();
  return EXP;
});
