/* Prayogshala studio module: THE FIBRE NUMERICAL-APERTURE JIG. A fibre-optic source launches light into one end of a
   step-index multimode fibre; the far end is clamped in a jig, pointing straight down at a screen ruled in
   millimetres, with a screw that sets the height. The gloved hand switches the source on, clamps the fibre end,
   raises it and reads the diameter of the lit patch across the grid. The cone of light and the patch both come from
   the `fibrecone` kernel, which traces the extreme ray out of the end face, so the numerical aperture is got from
   the readings and never read back from sqrt(n1^2 - n2^2). */
HoolaStudio.define('fibre-bench', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.fibrecone;
  var p = window.HoolaKernels.paramsFor('fibrecone', S.lab.params);
  (S.lab.knobs || []).forEach(function (k) {
    if (k.hidden && isFinite(k.value) && p[k.param] !== undefined) p[k.param] = +k.value * (+k.k || 1);
  });
  var LC = 5e-4;                                        // the grid is read to half a millimetre
  var CX = 0.18, CZ = -0.18;                            // centre of the jig and of the screen
  var SAMPLE = (S.lab.variant || {}).sample || '';
  var PLASTIC = !/glass|silica|telecom/i.test(SAMPLE);
  var st = { on: false, clamped: false, z: 0.005, zSet: 0.005, W: null };

  function fmt(v, d) { return (Math.round(v * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }
  function spotW() { return K.spot(Object.assign({}, p, { dz: st.z })); }
  function readW() { return Math.round(spotW() / LC) * LC; }
  function naOf(z, W) { return Math.sin(Math.atan2(W - p.dcore, 2 * z)); }

  // ---------------------------------------------------------------- the apparatus
  var src = new T.Group(); src.position.set(CX - 0.42, 0, CZ + 0.02); S.scene.add(src);
  var sBox = S.rounded(0.14, 0.085, 0.11, 0.008, M.iron); sBox.position.y = 0.0425; src.add(sBox);
  var sFace = S.mesh(new T.BoxGeometry(0.002, 0.07, 0.1), M.blackPlastic); sFace.position.set(0.071, 0.045, 0); src.add(sFace);
  var sPort = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.016, 18), M.alu); sPort.rotation.z = Math.PI / 2;
  sPort.position.set(0.078, 0.05, 0.02); src.add(sPort);
  var sSw = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.006, 14), M.red); sSw.rotation.z = Math.PI / 2;
  sSw.position.set(0.073, 0.022, -0.03); src.add(sSw);
  var sLab = S.label('FIBRE OPTIC SOURCE', { w: 0.08, ratio: 0.17, color: '#e8e2cf', weight: 700 });
  sLab.position.set(0, 0.078, 0.0551); sLab.rotation.x = -Math.PI / 2; src.add(sLab);
  S.contact(0.18, 0.15, CX - 0.42, CZ + 0.02, 0.5);

  // the jig: a base, a vertical pillar with a screw and a clamp that holds the fibre end straight down
  var jig = new T.Group(); jig.position.set(CX, 0, CZ); S.scene.add(jig);
  var jBase = S.rounded(0.2, 0.17, 0.016, 0.006, M.iron); jBase.rotation.x = -Math.PI / 2; jBase.position.set(0, 0.008, -0.03); jig.add(jBase);
  var jPost = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.22, 24), M.chrome); jPost.position.set(0, 0.12, -0.08); jig.add(jPost);
  var jScaleTex = S.canvasTex(128, 1024, function (x, w, h) {
    var i, mm = 60, k = h / mm;
    x.fillStyle = '#f0ead8'; x.fillRect(0, 0, w, h); x.fillStyle = '#17181a';
    for (i = 0; i <= mm; i++) {
      var big = i % 10 === 0;
      x.fillRect(0, h - i * k, big ? 52 : (i % 5 === 0 ? 36 : 22), big ? 5 : 3);
      if (big) { x.font = '600 34px sans-serif'; x.fillText(String(i), 58, h - i * k + 12); }
    }
  });
  var jScale = new T.Mesh(new T.PlaneGeometry(0.014, 0.112), new T.MeshStandardMaterial({ map: jScaleTex, roughness: 0.6 }));
  jScale.position.set(0.012, 0.088, -0.072); jig.add(jScale);
  var slider = new T.Group(); jig.add(slider);
  var sBody = S.rounded(0.034, 0.03, 0.026, 0.004, M.alu); sBody.position.set(0, 0, -0.08); slider.add(sBody);
  var sScrew = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.01, 18), M.bakelite); sScrew.rotation.z = Math.PI / 2;
  sScrew.position.set(-0.022, 0, -0.08); slider.add(sScrew);
  var sArm = S.mesh(new T.BoxGeometry(0.014, 0.012, 0.08), M.alu); sArm.position.set(0, 0, -0.04); slider.add(sArm);
  var chuck = S.mesh(new T.CylinderGeometry(0.009, 0.007, 0.018, 18), M.brass); chuck.position.set(0, -0.004, 0); slider.add(chuck);

  // the fibre: a coil on the bench and the end in the chuck
  var fibM = new T.MeshStandardMaterial({ color: PLASTIC ? 0xf2ecd8 : 0xdfe6ee, roughness: 0.35 });
  var curve = new T.CatmullRomCurve3([
    new T.Vector3(CX - 0.34, 0.052, CZ + 0.04), new T.Vector3(CX - 0.26, 0.012, CZ + 0.16),
    new T.Vector3(CX - 0.12, 0.012, CZ + 0.2), new T.Vector3(CX - 0.02, 0.012, CZ + 0.12),
    new T.Vector3(CX - 0.06, 0.012, CZ + 0.02), new T.Vector3(CX - 0.02, 0.05, CZ - 0.02)]);
  var fibre = S.mesh(new T.TubeGeometry(curve, 48, 0.0012, 8), fibM); S.scene.add(fibre);
  var endPiece = new T.Group(); S.scene.add(endPiece);
  var endTube = S.mesh(new T.CylinderGeometry(0.0012, 0.0012, 0.06, 10), fibM); endPiece.add(endTube);
  var ferrule = S.mesh(new T.CylinderGeometry(0.0025, 0.0025, 0.012, 14), M.chrome); ferrule.position.y = 0.024; endPiece.add(ferrule);

  // the screen with its millimetre grid
  var gridTex = S.canvasTex(1024, 1024, function (x, w, h) {
    var i, mm = 80, k = w / mm;
    x.fillStyle = '#f4f1e6'; x.fillRect(0, 0, w, h);
    for (i = 0; i <= mm; i++) {
      x.strokeStyle = i % 10 === 0 ? 'rgba(25,28,32,.85)' : (i % 5 === 0 ? 'rgba(25,28,32,.45)' : 'rgba(25,28,32,.2)');
      x.lineWidth = i % 10 === 0 ? 3 : 1.5;
      x.beginPath(); x.moveTo(i * k, 0); x.lineTo(i * k, h); x.stroke();
      x.beginPath(); x.moveTo(0, i * k); x.lineTo(w, i * k); x.stroke();
    }
    x.fillStyle = '#17181a'; x.font = '600 26px sans-serif';
    for (i = 10; i < mm; i += 10) { x.fillText(String(i - 40), i * k + 4, h / 2 - 6); }
  });
  var screen = S.mesh(new T.BoxGeometry(0.08, 0.004, 0.08), new T.MeshStandardMaterial({ map: gridTex, roughness: 0.9 }));
  screen.position.set(CX, 0.019, CZ); S.scene.add(screen);
  var patchTex = S.liveTex(256, 256);
  var patch = new T.Mesh(new T.PlaneGeometry(0.08, 0.08), new T.MeshBasicMaterial({ map: patchTex, transparent: true, depthWrite: false, toneMapped: false, blending: T.AdditiveBlending }));
  patch.rotation.x = -Math.PI / 2; patch.position.set(CX, 0.0215, CZ); patch.renderOrder = 5; S.scene.add(patch);
  var cone = new T.Mesh(new T.ConeGeometry(0.01, 0.02, 28, 1, true),
    new T.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: 0.14, depthWrite: false, side: T.DoubleSide, toneMapped: false }));
  cone.visible = false; S.scene.add(cone);
  S.contact(0.24, 0.22, CX, CZ - 0.02, 0.5);

  S.addApparatus('src', src, 'Fibre-optic source',
    'A lamp behind a port that launches light into the near end of the fibre. Nothing bright enough to hurt the eye leaves the far end, but never look straight into it.');
  S.addApparatus('fibre', fibre, PLASTIC ? 'Step-index plastic fibre' : 'Multimode glass fibre',
    (SAMPLE ? SAMPLE + '. ' : '') + 'Light stays in the core only if it meets the cladding beyond the critical angle; that is what fixes the cone it will accept.');
  S.addApparatus('jig', jig, 'Numerical aperture jig',
    'Holds the fibre end straight down above the screen. The screw raises it, and the height is read on the scale beside the pillar.');
  S.addApparatus('screen', screen, 'Screen ruled in millimetres',
    'The patch of light falls on it; its diameter is read across the grid to half a millimetre.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- the patch as the eye sees it (HUD)
  var eyeCard = document.createElement('div'); eyeCard.className = 'card';
  eyeCard.appendChild(document.createTextNode('The patch on the grid'));
  var eyeCan = document.createElement('canvas'); eyeCan.width = 230; eyeCan.height = 230;
  eyeCan.style.cssText = 'width:185px;height:185px;display:block;margin-top:4px;border-radius:8px';
  eyeCard.appendChild(eyeCan); S.hud.appendChild(eyeCard);
  var ectx = eyeCan.getContext('2d'), eyeKey = '';
  var hudZ = S.hudCard('Fibre end above the screen'), hudW = S.hudCard('Diameter of the patch');
  var VIEW_MM = 40;
  function drawEye() {
    var key = [st.on, st.clamped, fmt(st.z, 5)].join('|');
    if (key === eyeKey) return; eyeKey = key;
    var w = eyeCan.width, h = eyeCan.height, k = w / VIEW_MM, i;
    ectx.fillStyle = '#efece1'; ectx.fillRect(0, 0, w, h);
    for (i = 0; i <= VIEW_MM; i++) {
      ectx.strokeStyle = i % 10 === 0 ? 'rgba(25,28,32,.7)' : (i % 5 === 0 ? 'rgba(25,28,32,.35)' : 'rgba(25,28,32,.16)');
      ectx.lineWidth = i % 10 === 0 ? 1.6 : 1;
      ectx.beginPath(); ectx.moveTo(i * k, 0); ectx.lineTo(i * k, h); ectx.stroke();
      ectx.beginPath(); ectx.moveTo(0, i * k); ectx.lineTo(w, i * k); ectx.stroke();
    }
    if (st.on && st.clamped) {
      var r = spotW() * 1000 / 2 * k, g = ectx.createRadialGradient(w / 2, h / 2, r * 0.2, w / 2, h / 2, r);
      g.addColorStop(0, 'rgba(255,228,150,.95)'); g.addColorStop(0.75, 'rgba(255,205,95,.8)');
      g.addColorStop(0.97, 'rgba(255,185,70,.55)'); g.addColorStop(1, 'rgba(255,180,60,0)');
      ectx.fillStyle = g; ectx.beginPath(); ectx.arc(w / 2, h / 2, r, 0, Math.PI * 2); ectx.fill();
    }
    ectx.strokeStyle = 'rgba(70,76,84,.9)'; ectx.lineWidth = 3; ectx.strokeRect(1.5, 1.5, w - 3, h - 3);
    ectx.fillStyle = '#5d636b'; ectx.font = '500 13px "Public Sans", sans-serif';
    ectx.fillText(VIEW_MM + ' mm across', 7, h - 8);
  }
  var patKey = '';
  function drawPatch() {
    var key = [st.on, st.clamped, fmt(st.z, 5)].join('|');
    if (key === patKey) return; patKey = key;
    patchTex.draw(function (x, w, h) {
      x.clearRect(0, 0, w, h);
      if (!(st.on && st.clamped)) return;
      var r = spotW() / 0.08 * w / 2;
      var g = x.createRadialGradient(w / 2, h / 2, r * 0.2, w / 2, h / 2, r);
      g.addColorStop(0, 'rgba(255,225,140,.85)'); g.addColorStop(0.8, 'rgba(255,200,90,.6)');
      g.addColorStop(1, 'rgba(255,180,60,0)');
      x.fillStyle = g; x.beginPath(); x.arc(w / 2, h / 2, r, 0, Math.PI * 2); x.fill();
    });
  }

  function update() {
    slider.position.y = 0.0235 + st.z + 0.03;
    endPiece.visible = st.clamped;
    endPiece.position.set(CX, 0.0235 + st.z + 0.03, CZ - 0.0);
    cone.visible = st.on && st.clamped;
    if (cone.visible) {
      var W = spotW();
      cone.geometry.dispose();
      cone.geometry = new T.ConeGeometry(W / 2, st.z, 28, 1, true);
      cone.position.set(CX, 0.0215 + st.z / 2, CZ);    // apex at the fibre end, mouth on the screen
    }
    drawPatch(); drawEye();
    hudZ.set(fmt(st.z * 1000, 1) + ' mm');
    hudW.set(st.on && st.clamped ? fmt(readW() * 1000, 1) + ' mm' : '—');
  }

  // ---------------------------------------------------------------- the human actions
  function wait() { S.say('Wait for the hand to finish.'); return Promise.resolve(false); }
  function switchOn() {
    if (st.on) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    return S.hand.tap(sSw, 'front').then(function () {
      st.on = true; update(); S.say('The source is on and the light is in the fibre.'); S.render(); return true; });
  }
  function clampEnd() {
    if (st.clamped) return Promise.resolve(true);
    if (S.hand.busy) return wait();
    var to = new T.Vector3(CX, 0.0235 + st.z + 0.03, CZ), from = new T.Vector3(CX - 0.06, 0.12, CZ + 0.1);
    endPiece.visible = true;
    return S.hand.pinchMove(from, function (k) { return from.clone().lerp(to, k); },
      function (k) { endPiece.position.copy(from.clone().lerp(to, k)); },
      { ms: 1300, reachMs: 700, hold: 220, mode: 'top' }).then(function () {
      st.clamped = true; update();
      S.say('The end is in the chuck, pointing straight down at the middle of the grid.'); S.render(); return true; });
  }
  function setHeight(z) {
    if (S.hand.busy) return wait();
    z = Math.max(0.003, Math.min(0.03, Math.round(z * 2000) / 2000));
    var from = st.z;
    if (Math.abs(z - from) < 1e-9) { st.z = z; update(); return Promise.resolve(true); }
    function at(k) { return from + (z - from) * k; }
    return S.hand.pinchMove(new T.Vector3(CX - 0.026, 0.0235 + from + 0.03, CZ - 0.08),
      function (k) { return new T.Vector3(CX - 0.026, 0.0235 + at(k) + 0.03, CZ - 0.08); },
      function (k) { st.z = at(k); update(); }, { ms: 1100, reachMs: 600, hold: 160 })
      .then(function () { st.z = z; update(); S.render(); return true; });
  }
  function measureW() {
    if (S.hand.busy) return wait();
    if (!(st.on && st.clamped)) { S.say('Switch the source on and clamp the fibre end first.'); return Promise.resolve(false); }
    return S.hand.reach(new T.Vector3(CX, 0.03, CZ + 0.02), 'top', 600).then(function () { return S.hand.shape('point', 200); })
      .then(function () { return S.hand.away(500); }).then(function () {
        st.W = readW(); update();
        S.say('The patch measures ' + fmt(st.W * 1000, 1) + ' mm across the grid.'); S.render(); return true; });
  }
  function record() {
    if (st.W === null) { S.say('Measure the patch on the grid first.'); return false; }
    if (Math.abs(st.W - readW()) > 1e-9) { S.say('The height has changed since you measured. Measure the patch again.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.z - st.z) < 1e-6; })) { S.say('There is already a reading at this height. Raise the fibre end.'); return false; }
    S.addRow({ z: st.z, W: st.W, na: naOf(st.z, st.W) });
    S.say('Written down: height ' + fmt(st.z * 1000, 1) + ' mm, patch ' + fmt(st.W * 1000, 1) + ' mm.');
    return true;
  }
  function meanOf(xs) { return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : NaN; }

  var VIEWS = {
    src: [[CX - 0.34, 0.26, CZ + 0.3], [CX - 0.42, 0.05, CZ]],
    fibre: [[CX - 0.1, 0.3, CZ + 0.36], [CX - 0.14, 0.02, CZ + 0.12]],
    jig: [[CX + 0.2, 0.2, CZ + 0.26], [CX, 0.06, CZ]],
    screen: [[CX + 0.1, 0.22, CZ + 0.16], [CX, 0.02, CZ]],
    wide: [[CX + 0.22, 0.66, CZ + 0.88], [CX - 0.17, 0.05, CZ + 0.02]],
    book: [[-0.4, 0.46, 0.6], [-0.45, 0.0, 0.14]]
  };
  update();

  return {
    camera: { pos: [CX + 0.22, 0.66, CZ + 0.88], look: [CX - 0.17, 0.05, CZ + 0.02] },
    views: VIEWS,
    theory: {
      principle: 'Light stays inside the core of a fibre only if it strikes the boundary with the cladding beyond the '
        + 'critical angle. Tracing that condition back to the end face gives a cone: any ray entering inside the cone '
        + 'is carried along, and any ray outside it leaks away. The sine of the half angle of that cone is the '
        + 'numerical aperture, and the same cone comes out of the far end.',
      formula: 'NA = sin(θ_a) = √(n₁² − n₂²)',
      formulaNote: 'θ_a = acceptance angle; measured here from the patch: NA = sin(arctan((W − core) / 2z))',
      more: ['So on a screen a distance z below the end the lit patch has a diameter W = core + 2 z tan(θ_a): a '
        + 'straight line in z whose slope gives the numerical aperture.',
        PLASTIC ? 'A step-index plastic fibre has a large numerical aperture, about 0.5, which is why it is easy to '
          + 'launch light into and why it is used for short runs and for lighting.'
          : 'A glass telecom fibre has a much smaller numerical aperture, so it accepts a narrow cone only - that is '
          + 'exactly why it can carry a signal for kilometres without smearing it.'],
      precautions: 'Keep the end face clean and square to the screen. Never look straight into the end of a lit '
        + 'fibre, and never launch laser light into it for this measurement.'
    },
    book: { title: 'Expt. — Numerical aperture of a fibre',
      lines: ['Grid read to 0.5 mm; height read on the jig scale.',
        'W = core + 2 z tan(theta)', 'NA = sin(theta)',
        'Keep the end face square to the screen.'],
      columns: [{ label: 'Height z (mm)', get: function (r) { return fmt(r.z * 1000, 1); } },
        { label: 'Patch W (mm)', get: function (r) { return fmt(r.W * 1000, 1); } },
        { label: 'NA', get: function (r) { return fmt(r.na, 4); } },
        { label: 'Acceptance angle (°)', get: function (r) { return fmt(Math.asin(r.na) * 180 / Math.PI, 2); } }],
      at: [-0.45, 0.1, 0.12] },
    graph: { x: function (r) { return r.z * 1000; }, y: function (r) { return r.W * 1000; },
      xlabel: 'height z (mm)', ylabel: 'patch W (mm)', x0: 0, y0: 0,
      line: function (pts) { var L = S.fit.linear(pts); return L ? function (x) { return L.m * x + L.c; } : null; } },
    result: function (rows) {
      if (rows.length < 3) return null;
      return { label: 'NA', value: meanOf(rows.map(function (r) { return r.na; })), unit: '', digits: 4,
        truth: Math.sqrt(Math.max(p.n1 * p.n1 - p.n2 * p.n2, 0)) / p.nout,
        note: 'Mean of sin(arctan((W − core) / 2z)) over your heights; the acceptance angle is its arcsine.' };
    },
    tol: 0.03,
    chips: ['Why does the patch grow with height?', 'What does a large NA mean?', 'Why subtract the core diameter?',
      'Check my readings', 'How is NA related to the two indices?'],
    viva: [['The numerical aperture of a fibre depends on',
      ['the core and cladding indices', 'the length of the fibre', 'the brightness of the source'], 0,
      'NA = sqrt(n1 squared - n2 squared): a property of the two materials.'],
      ['A fibre with a larger NA', ['accepts light from a wider cone', 'carries light further', 'has a smaller core'], 0,
        'The acceptance angle is the arcsine of the numerical aperture.']],
    askState: function () {
      return { source_on: st.on, fibre_end_clamped: st.clamped, height_mm: +(st.z * 1000).toFixed(2),
        patch_on_the_grid_mm: st.on && st.clamped ? +(readW() * 1000).toFixed(1) : null,
        last_measured_patch_mm: st.W === null ? null : +(st.W * 1000).toFixed(1),
        core_diameter_mm: +(p.dcore * 1000).toFixed(2), readings_taken: S.rows.length, grid_least_count_mm: 0.5 };
    },
    steps: [
      { id: 'setup', title: 'Set up the jig', view: 'jig', render: function (u) {
        u.h2('Launch the light and clamp the far end');
        u.p('The near end of the fibre is already in the source. Switch the source on, then clamp the far end in the '
          + 'jig so that it points straight down at the middle of the ruled screen.');
        u.task('1. Switch the source on', st.on, st.on ? 'Light is in the fibre' : 'Press the switch on the source')
          .add(u.button(st.on ? 'Source on' : 'Switch the source on', function () { switchOn(); }, !st.on, st.on || S.hand.busy));
        u.task('2. Clamp the fibre end', st.clamped, st.clamped ? 'Square to the screen' : 'Put the ferrule into the chuck')
          .add(u.button(st.clamped ? 'Clamped' : 'Clamp the end in the jig', function () { clampEnd(); }, !st.clamped, st.clamped || S.hand.busy));
        u.note('Never look straight into the end of a lit fibre, and do not launch laser light into it for this '
          + 'measurement: the cone that comes out is bright.');
        u.next('Next: measure the patch', st.on && st.clamped);
      },
      ok: function () { return st.on && st.clamped; },
      auto: function () { return switchOn().then(clampEnd); } },

      { id: 'measure', title: 'Measure the patch', view: 'screen', render: function (u) {
        u.h2('Measure the lit patch at several heights');
        u.p('Set the height of the fibre end on the jig scale, then measure the diameter of the lit patch across the '
          + 'millimetre grid. Do this at four heights: the patch grows along a straight line, and the slope gives the '
          + 'numerical aperture.');
        u.slider('Raise the fibre end to', 3, 30, 0.5, function () { return st.zSet * 1000; },
          function (x) { st.zSet = x / 1000; }, 'mm', 1);
        u.row(u.button('Turn the screw', function () { setHeight(st.zSet); S.render(); }, true, S.hand.busy),
          u.button('Measure the patch', function () { measureW(); }, false, S.hand.busy));
        u.live(function () { return 'Height ' + fmt(st.z * 1000, 1) + ' mm · patch on the grid '
          + (st.on && st.clamped ? fmt(readW() * 1000, 1) + ' mm' : '—'); });
        u.row(u.button('Record this reading', function () { record(); S.render(); }, true, S.hand.busy));
        u.h3('Observation table'); u.table();
        u.next('Next: graph and result', S.rows.length >= 3);
        if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 heights recorded.');
      },
      ok: function () { return S.rows.length >= 3; },
      auto: function () {
        var seq = Promise.resolve();
        [0.006, 0.012, 0.018, 0.024].forEach(function (z) {
          seq = seq.then(function () { return setHeight(z); }).then(function () { return measureW(); })
            .then(function () { record(); });
        });
        return seq;
      } }
    ],
    tick: function () { update(); }
  };
});
