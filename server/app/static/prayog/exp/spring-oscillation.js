/* Prayogshala studio module: Spring-mass oscillation - T against m (NCERT Class XI).
   The same rig as Hooke's law: a helical spring on a retort stand, a slotted-mass hanger with a pointer beside a metre
   scale. The gloved hand loads the hanger (lowering it gently to rest), pulls it down about 3 cm and lets go; the
   student times 10 oscillations on the stopwatch. Physics: the spring kernel from kernels.js (undamped, as in the lab). */
HoolaStudio.define('spring-oscillation', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.spring;
  function hidden(id, dflt) { var k = (S.lab.knobs || []).filter(function (q) { return q.id === id; })[0]; return k ? k.value * (k.k || 1) : dflt; }
  var p = window.HoolaKernels.paramsFor('spring', S.lab.params);
  p.k = hidden('k', 20);
  var G = p.g, HANGER = 0.05, DISC = 0.05, MAXN = 9;
  var st = { n: 0, pull: Math.round((p.x0 || 0.03) * 1000) / 10, running: false, held: false };
  p.m = HANGER;
  var sim = K.init(p); sim.y = [0, 0];
  var n = 0, halves = 0, lastSign = 0, crossings = 0, prevSign = 0;

  // ---------- geometry constants
  var JX = 0.06, JZ = -0.05;
  var YTOP = 0.95, LC0 = 0.08, TURNS = 20, CR = 0.012, WIRE = 0.0011;
  var DR = 0.02, DT = 0.0045, STEM = 0.1;
  var RX = 0.11, RZ = -0.05, RY = 0.03, RLEN = 1.0, MM = RLEN * 1000;
  function markY(cm) { return RY + (RLEN + 0.01) - (5 + cm * 10) * (MM + 20) / (MM + 10) / 1000; }
  function cmAt(y) { return ((RY + RLEN + 0.01 - y) * 1000 * (MM + 10) / (MM + 20) - 5) / 10; }
  var R0 = cmAt(YTOP - LC0 - 0.026);
  function ext() { return p.m * G / p.k + sim.y[0]; }
  function ptrY() { return markY(R0 + ext() * 100); }
  function atRest() { return Math.abs(sim.y[0]) < 0.0005 && Math.abs(sim.y[1]) < 0.005; }

  function helix(turns, R, wire, seg, rad) {
    var N = turns * seg, g = new T.BufferGeometry(), pos = new Float32Array((N + 1) * (rad + 1) * 3), nor = new Float32Array(pos.length), idx = [];
    for (var i = 0; i < N; i++) for (var j = 0; j < rad; j++) { var a = i * (rad + 1) + j, b = (i + 1) * (rad + 1) + j; idx.push(a, b, a + 1, b, b + 1, a + 1); }
    g.setIndex(idx); g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setAttribute('normal', new T.BufferAttribute(nor, 3));
    var w = 2 * Math.PI * turns, last = -1;
    g.update = function (L) { if (Math.abs(L - last) < 2e-5) return; last = L;
      for (var i = 0; i <= N; i++) { var t = i / N, a = w * t, ca = Math.cos(a), sa = Math.sin(a);
        var tx = -R * w * sa, ty = -L, tz = R * w * ca, tl = Math.hypot(tx, ty, tz); tx /= tl; ty /= tl; tz /= tl;
        var nx = -ca, nz = -sa, bx = ty * nz, by = tz * nx - tx * nz, bz = -ty * nx;
        for (var j = 0; j <= rad; j++) { var f = 2 * Math.PI * j / rad, cf = Math.cos(f), sf = Math.sin(f), ox = cf * nx + sf * bx, oy = sf * by, oz = cf * nz + sf * bz, k = (i * (rad + 1) + j) * 3;
          pos[k] = R * ca + wire * ox; pos[k + 1] = -L * t + wire * oy; pos[k + 2] = R * sa + wire * oz; nor[k] = ox; nor[k + 1] = oy; nor[k + 2] = oz; } }
      g.attributes.position.needsUpdate = true; g.attributes.normal.needsUpdate = true; };
    return g;
  }
  function slotted() {
    var w = 0.0064, a = Math.asin(w / 2 / DR), s = new T.Shape();
    s.moveTo(DR * Math.cos(a), w / 2); s.absarc(0, 0, DR, a, 2 * Math.PI - a, false); s.lineTo(0, -w / 2); s.absarc(0, 0, w / 2, -Math.PI / 2, Math.PI / 2, true); s.lineTo(DR * Math.cos(a), w / 2);
    var g = new T.ExtrudeGeometry(s, { depth: DT - 0.001, bevelEnabled: true, bevelThickness: 0.0005, bevelSize: 0.0005, bevelSegments: 2, curveSegments: 40 });
    g.translate(0, 0, -(DT - 0.001) / 2); g.rotateX(-Math.PI / 2); g.rotateY(Math.PI); return g;
  }

  // ---------- apparatus
  var stand = S.stand({ x: JX - 0.01, z: JZ, armY: 1.0, h: 1.08, armLen: 0.2 });
  var hookG = new T.Group(); S.scene.add(hookG);
  var hk = S.mesh(new T.CylinderGeometry(0.0016, 0.0016, 0.016, 12), M.steel); hk.position.set(JX, 0.984, JZ); hookG.add(hk);
  var hk2 = S.mesh(new T.TorusGeometry(0.0055, 0.0014, 10, 28), M.steel); hk2.rotation.y = Math.PI / 2; hk2.position.set(JX, 0.9705, JZ); hookG.add(hk2);
  var spring = new T.Group(); spring.position.set(JX, YTOP, JZ); S.scene.add(spring);
  var springM = new T.MeshStandardMaterial({ color: 0xb9bec4, roughness: 0.28, metalness: 1 });
  var hgeo = helix(TURNS, CR, WIRE, 26, 8); var coil = S.mesh(hgeo, springM); coil.frustumCulled = false; spring.add(coil);
  var topLoop = S.mesh(new T.TorusGeometry(0.0075, WIRE, 8, 28), springM); topLoop.position.set(0, 0.0085, 0); spring.add(topLoop);
  var topLeg = S.mesh(new T.CylinderGeometry(WIRE, WIRE, 1, 8), springM); spring.add(topLeg);
  var botLoop = S.mesh(new T.TorusGeometry(0.0075, WIRE, 8, 28), springM); spring.add(botLoop);
  var botLeg = S.mesh(new T.CylinderGeometry(WIRE, WIRE, 1, 8), springM); spring.add(botLeg);
  function leg(m, a, b) { var d = b.clone().sub(a); m.position.copy(a).add(b).multiplyScalar(0.5); m.scale.set(1, d.length(), 1); m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.normalize()); }
  leg(topLeg, new T.Vector3(CR, 0, 0), new T.Vector3(0.0, 0.0012, 0));
  var hanger = new T.Group(); S.scene.add(hanger);
  var hh = S.mesh(new T.TorusGeometry(0.0055, 0.0015, 10, 28, Math.PI * 1.6), M.chrome); hh.rotation.set(0, Math.PI / 2, Math.PI * 0.7); hh.position.y = 0.009; hanger.add(hh);
  var stem = S.mesh(new T.CylinderGeometry(0.0024, 0.0024, STEM, 16), M.chrome); stem.position.y = -STEM / 2 + 0.003; hanger.add(stem);
  var baseD = S.mesh(new T.CylinderGeometry(DR, DR, 0.004, 40), M.brass); baseD.position.y = -STEM + 0.001; hanger.add(baseD);
  var pb = S.mesh(new T.BoxGeometry(0.036, 0.0012, 0.004), M.steel); pb.position.set(0.02, 0, 0.0068); hanger.add(pb);
  var ptip = S.mesh(new T.ConeGeometry(0.002, 0.008, 4), M.steel); ptip.rotation.z = -Math.PI / 2; ptip.scale.set(1, 1, 0.3); ptip.position.set(0.042, 0, 0.0068); hanger.add(ptip);
  var collar = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.006, 16), M.steel); hanger.add(collar);
  var STACK0 = -STEM + 0.003;
  var ruler = S.ruler(RLEN, { title: 'METRE SCALE · cm · LC 1 mm', labelEvery: 10 }); ruler.position.set(RX, RY, RZ);
  var rfoot = S.rounded(0.08, 0.05, 0.03, 0.008, M.darkWood); rfoot.rotation.x = -Math.PI / 2; rfoot.position.set(RX, 0.015, RZ); S.scene.add(rfoot); S.contact(0.14, 0.1, RX, RZ, 0.5);
  var discGeo = slotted(), lblTex = S.canvasTex(128, 64, function (x) { x.fillStyle = '#5a3d0c'; x.font = '700 40px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('50 g', 64, 34); });
  var lblMat = new T.MeshStandardMaterial({ map: lblTex, transparent: true, roughness: 0.5, depthWrite: false }), lblGeo = new T.PlaneGeometry(0.014, 0.007);
  var PILE = new T.Vector3(0.36, 0, 0.0), discs = [], onHanger = [];
  for (var i = 0; i < MAXN; i++) { var d = new T.Group(); d.add(S.mesh(discGeo, M.brass));
    var lb = new T.Mesh(lblGeo, lblMat); lb.rotation.x = -Math.PI / 2; lb.rotation.z = Math.PI / 2; lb.position.set(0.0115, DT / 2 + 0.0002, 0); lb.renderOrder = 2; d.add(lb);
    d.position.set(PILE.x, DT / 2 + i * DT, PILE.z); S.scene.add(d); discs.push(d); }
  S.contact(0.08, 0.08, PILE.x, PILE.z, 0.5);
  var hangShadow = S.contact(0.07, 0.07, JX, JZ, 0.25);
  var pile = discs.slice();
  var watch = S.stopwatch([0.24, 0.035, 0.17], [-1.15, 0, 0.25]);

  S.addApparatus('stand', stand, 'Retort stand with clamp', 'A heavy iron base and a rigid rod: the top of the spring stays fixed.');
  S.addApparatus('spring', spring, 'Helical spring', 'A steel spring. The mass on it moves up and down in simple harmonic motion.');
  S.addApparatus('hanger', hanger, 'Slotted-mass hanger with pointer', 'The hanger itself is 50 g. The pointer shows the mean position on the scale.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Shows how far the hanger is pulled down. Least count 1 mm.');
  S.addApparatus('masses', discs[0], 'Slotted masses', 'Nine slotted masses of 50 g each. The oscillating mass m = hanger + slotted masses.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Least count 0.01 s. Time 10 oscillations, not one.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudM = S.hudCard('Mass m'), hudX = S.hudCard('Displacement'), hudN = S.hudCard('Oscillations');

  // ---------- hand helpers
  function along(pts) { var L = [0]; for (var i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
    return function (k) { var d = Math.max(0, Math.min(1, k)) * L[L.length - 1]; for (var i = 1; i < pts.length; i++) if (d <= L[i] || i === pts.length - 1) { var f = (d - L[i - 1]) / Math.max(1e-9, L[i] - L[i - 1]); return pts[i - 1].clone().lerp(pts[i], Math.min(1, f)); } }; }
  // pinch at startPt, move along fn(k) while onK(k) runs, let go (then `release()`), withdraw the hand
  function grab(startPt, fn, onK, ms, release) {
    if (S.fast) { onK(1); if (release) release(); return Promise.resolve(); }
    var H = S.hand; H.busy = true;
    return H.shape('relaxed', 1).then(function () { return H.reach(startPt, 'side', 800); }).then(function () { return H.shape('pinch', 280); })
      .then(function () { return H.follow(fn, 'side', ms, onK); }).then(function () { if (release) release(); return H.shape('relaxed', 240); })
      .then(function () { return H.away(); }).then(function () { H.busy = false; S.render(); }, function () { H.busy = false; });
  }
  var GRIP = new T.Vector3(DR + 0.001, 0, 0);
  function slotPos(i) { return new T.Vector3(JX, ptrY() + STACK0 + DT / 2 + i * DT, JZ); }
  function basePt() { return new T.Vector3(JX, ptrY() + STACK0 - 0.001, JZ); }

  function busyOrMoving() {
    if (S.hand.busy) return true;
    if (st.running || !atRest()) { S.say('Stop the oscillation first: steady the hanger, then change the mass.'); return true; }
    return false;
  }
  function addMass() {
    if (busyOrMoving()) return Promise.resolve();
    if (st.n >= MAXN) { S.say('That is 500 g in all. More would stretch the spring past its elastic limit.'); return Promise.resolve(); }
    var d = pile.pop(), from = d.position.clone(), nn = st.n, top = slotPos(nn), x1 = 0, on = false;
    var path = along([from, from.clone().setY(from.y + 0.07), top.clone().add(new T.Vector3(0.05, 0.05, 0)), top.clone().add(new T.Vector3(0.05, 0.001, 0)), top.clone().setY(top.y + 0.001)]);
    // the hand slides the mass on, then lowers the hanger gently to its new rest position (so it does not bounce)
    return grab(from.clone().add(GRIP), function (k) { return (k < 0.75 ? path(k / 0.75) : d.position.clone()).add(GRIP); }, function (k) {
      if (k < 0.75) { d.position.copy(path(k / 0.75)); return; }
      if (!on) { on = true; st.held = true; var e = ext(); onHanger.push(d); st.n = nn + 1; p.m = HANGER + st.n * DISC; x1 = e - p.m * G / p.k; }
      sim.y = [x1 * (1 - (k - 0.75) / 0.25), 0]; pose(); }, 2200, function () { st.held = false; sim.y = [0, 0]; S.render(); S.say('Mass m is now ' + Math.round(p.m * 1000) + ' g (hanger + ' + st.n + ' slotted masses).'); });
  }
  function removeMass() {
    if (busyOrMoving()) return Promise.resolve();
    if (!st.n) { S.say('There is no slotted mass on the hanger.'); return Promise.resolve(); }
    var d = onHanger[onHanger.length - 1], nn = st.n, taken = false, x1 = 0, path2 = null;
    return grab(slotPos(nn - 1).add(GRIP), function (k) { return (path2 && k > 0.25 ? path2((k - 0.25) / 0.75) : d.position.clone()).add(GRIP); }, function (k) {
      if (!taken) { taken = true; st.held = true; var e = ext(); onHanger.pop(); st.n = nn - 1; p.m = HANGER + st.n * DISC; x1 = e - p.m * G / p.k; }
      if (k <= 0.25) { sim.y = [x1 * (1 - k / 0.25), 0]; d.position.copy(slotPos(nn - 1)); pose(); return; }
      if (!path2) { st.held = false; sim.y = [0, 0]; var f = d.position.clone(), to = new T.Vector3(PILE.x, DT / 2 + pile.length * DT, PILE.z);
        path2 = along([f, f.clone().add(new T.Vector3(0.05, 0, 0)), f.clone().add(new T.Vector3(0.05, 0.05, 0)), to.clone().setY(to.y + 0.07), to]); }
      d.position.copy(path2((k - 0.25) / 0.75)); }, 2000, function () { st.held = false; pile.push(d); S.render(); S.say('Mass m is now ' + Math.round(p.m * 1000) + ' g.'); });
  }
  function setDiscs(target) { var pr = Promise.resolve();
    for (var i = 0; i < Math.abs(target - st.n); i++) pr = pr.then(function () { return target > st.n ? addMass() : removeMass(); });
    return pr; }
  function maxPull() { return Math.min(4, (p.m * G / p.k) * 100 - 0.5); }   // cm: the spring must stay stretched at the top of the swing
  function pullRelease(cm) {
    if (S.hand.busy) return Promise.resolve();
    if (st.running) { S.say('It is already oscillating. Steady it first if you want to start again.'); return Promise.resolve(); }
    if (p.m < 0.1 - 1e-9) { S.say('Load at least one slotted mass first (m ≥ 100 g), or the spring goes slack at the top of each swing.'); return Promise.resolve(); }
    if (cm < 1) { S.say('Pull it down at least 1 cm, so you can see and count the oscillations.'); return Promise.resolve(); }
    if (cm > maxPull() + 1e-9) { S.say('Too far: pull at most ' + maxPull().toFixed(1) + ' cm for this mass, or the coils go slack at the top.'); return Promise.resolve(); }
    var a = cm / 100, b0 = basePt(); st.held = true;
    return grab(b0.clone().add(GRIP), function (k) { return b0.clone().add(new T.Vector3(DR + 0.001, -a * k, 0)); }, function (k) { sim.y = [a * k, 0]; prevSign = 1; pose(); }, 900,
      function () { st.held = false; sim.y = [a, 0]; prevSign = 1; st.running = true; S.say('Released. Start the stopwatch as the pointer passes its mean position.'); });
  }
  function steady() {
    if (S.hand.busy) return Promise.resolve();
    if (watch.on) { watch.on = false; }
    var eq = new T.Vector3(JX, markY(R0 + p.m * G / p.k * 100) + STACK0 - 0.001, JZ).add(GRIP);
    function catchIt() { st.held = true; sim.y = [0, 0]; prevSign = 0; st.running = false; pose(); }
    if (S.fast) { catchIt(); st.held = false; return Promise.resolve(); }
    var H = S.hand; H.busy = true;
    return H.shape('open', 1).then(function () { return H.reach(eq, 'side', 700); }).then(function () { catchIt(); return H.shape('grip', 160); })
      .then(function () { return S.tween(450, function () {}); }).then(function () { st.held = false; return H.shape('relaxed', 240); })
      .then(function () { return H.away(); }).then(function () { H.busy = false; S.say('The hanger is at rest.'); S.render(); });
  }
  function pressWatch() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.running && !watch.on) { S.say('Release the mass first, then time it.'); return Promise.resolve(); }
    return S.hand.tap(watch.start).then(function () {
      S.click(2400);
      if (!watch.on) { watch.t = 0; n = 0; halves = 0; lastSign = Math.sign(sim.y[0]) || 1; watch.on = true; }
      else { watch.on = false; record(); }
      S.render(); });
  }
  function record() {
    if (n < 9 || n > 11) { S.say('You counted ' + n + ' oscillations. Stop the watch after exactly 10 for this reading.'); return; }
    var t = Math.round(watch.t * 100) / 100;
    S.addRow({ m: p.m, n: n, t: t, T: t / n });
    S.say('Written in your record book: m = ' + Math.round(p.m * 1000) + ' g, ' + n + ' oscillations in ' + t.toFixed(2) + ' s.');
    S.focus('book');
  }
  function timeOne() {   // auto: start at a mean-position crossing, stop after 10 oscillations
    var c0 = crossings; S.advance(3, function () { return crossings > c0; });
    return pressWatch().then(function () { S.advance(40, function () { return n >= 10; }); return pressWatch(); });
  }

  var EXP = {
    camera: { pos: [0.82, 0.86, 1.76], look: [0.09, 0.5, -0.05] },
    views: { stand: [[0.45, 0.85, 1.1], [-0.05, 0.6, -0.05]], spring: [[0.2, 0.9, 0.5], [0.06, 0.84, -0.05]], hanger: [[0.2, 0.8, 0.45], [0.07, 0.76, -0.05]],
      ruler: [[0.22, 0.86, 0.42], [0.1, 0.8, -0.05]], masses: [[0.5, 0.25, 0.4], [0.34, 0.03, 0.02]], sw: [[0.45, 0.62, 1.05], [0.15, 0.42, 0.0]],
      rig: [[0.7, 0.62, 1.3], [0.16, 0.44, 0.0]], swing: [[0.42, 0.78, 0.85], [0.1, 0.66, -0.04]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A mass m hanging on a spring of spring constant k, pulled down a little and released, moves up and down in simple harmonic motion about its rest position.',
      formula: 'T = 2π √(m / k)', formulaNote: 'so T² = (4π² / k) m, and k = 4π² / slope of T² against m',
      more: ['The graph of T² against m is a straight line through the origin. (The spring\'s own mass is small and is neglected here.)'],
      precautions: 'Pull the mass down only a little and release it without a sideways push, so it moves straight up and down. Start timing as the pointer passes the mean position. Time 10 oscillations.' },
    book: { title: 'Expt. — Spring-mass oscillation', lines: ['Aim: to find k from T against m.', 'm = hanger (50 g) + slotted masses', 'T = 2π √(m/k)  →  T² = (4π²/k) m', 'k = 4π² / slope of T² vs m', 'Precautions: small pull, vertical motion, time 10 osc.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'm (g)', get: function (r) { return String(Math.round(r.m * 1000)); } },
        { label: 't₁₀ (s)', get: function (r) { return r.t.toFixed(2); } }, { label: 'T (s)', get: function (r) { return r.T.toFixed(3); } }, { label: 'T² (s²)', get: function (r) { return (r.T * r.T).toFixed(3); } }] },
    graph: { x: function (r) { return r.m; }, y: function (r) { return r.T * r.T; }, xlabel: 'm (kg)', ylabel: 'T² (s²)', x0: 0, y0: 0,
      line: function (pts) { var s = S.fit.origin(pts); return function (x) { return s * x; }; } },
    result: function (rows) { if (rows.length < 2) return null; var s = S.fit.origin(rows.map(function (r) { return [r.m, r.T * r.T]; })); if (!(s > 0)) return null;
      return { label: 'k', value: 4 * Math.PI * Math.PI / s, unit: 'N/m', digits: 1, truth: p.k, note: 'From k = 4π² / slope of T² against m.' }; },
    tol: 0.02,
    chips: ['Why does a heavier mass oscillate slower?', 'Why time 10 oscillations?', 'Does the amplitude change T?', 'Check my readings', 'Why plot T² and not T?'],
    viva: [['Does the time period depend on how far you pull the mass down (for small pulls)?', ['No, T = 2π√(m/k) has no amplitude in it', 'Yes, a bigger pull gives a longer T', 'Yes, a bigger pull gives a shorter T'], 0, 'In SHM the period is independent of the amplitude.'],
      ['Why do we plot T² against m?', ['It gives a straight line through the origin', 'T is always negative', 'It makes the numbers smaller'], 0, 'T² = (4π²/k) m is a straight line; its slope gives k.']],
    askState: function () { return { mass_m_g: Math.round(p.m * 1000), slotted_masses: st.n, pull_cm: st.pull, oscillating: st.running, displacement_cm: +(sim.y[0] * 100).toFixed(2),
      stopwatch_running: watch.on, stopwatch_s: +watch.t.toFixed(2), oscillations_counted: n }; },

    steps: [
      { id: 'load', title: 'Load', view: 'rig', render: function (u) {
          u.h2('Load the hanger');
          u.p('Choose the mass m. The hand slides 50 g slotted masses onto the hanger and lowers it gently to rest. m = hanger (50 g) + slotted masses.');
          u.live(function () { return 'm = ' + Math.round(p.m * 1000) + ' g' + (st.running ? ' · oscillating' : ''); });
          u.row(u.button('Add a 50 g mass', function () { addMass(); }, true, S.hand.busy || st.n >= MAXN),
            u.button('Remove a mass', function () { removeMass(); }, false, S.hand.busy || !st.n));
          if (st.running) u.row(u.button('Steady the hanger', function () { steady(); }, false, S.hand.busy));
          if (p.m < 0.1 - 1e-9) u.note('Use at least 100 g: with only the light hanger the spring goes slack at the top of each swing.');
          u.next('Next: pull and release', p.m >= 0.1 - 1e-9);
        },
        ok: function () { return p.m >= 0.1 - 1e-9; },
        auto: function () { return setDiscs(1); } },
      { id: 'pull', title: 'Pull and release', view: 'swing', render: function (u) {
          u.h2('Pull down and release');
          u.p('The hand pulls the hanger down by the chosen distance and lets go. It then oscillates up and down about its rest position.');
          u.slider('Pull down by', 0.5, 5, 0.5, function () { return st.pull; }, function (v) { st.pull = v; }, 'cm', 1);
          u.row(u.button(st.running ? 'Oscillating…' : 'Pull and release', function () { pullRelease(st.pull); }, true, st.running || S.hand.busy),
            u.button('Steady the hanger', function () { steady(); }, false, !st.running || S.hand.busy));
          u.note('About 3 cm is right. Too big a pull lets the spring go slack at the top.');
          u.next('Next: time 10 oscillations', st.running);
        },
        ok: function () { return st.running; },
        auto: function () { st.pull = 3; return pullRelease(3); } },
      { id: 'time', title: 'Time it', view: 'sw', render: function (u) {
          u.h2('Time 10 oscillations');
          u.p('Press START as the pointer passes its mean position (the middle of its swing). Count 10 full oscillations and press STOP.');
          u.live(function () { return watch.t.toFixed(2) + ' s · ' + n + ' oscillations'; });
          u.row(u.button(watch.on ? 'STOP' : 'START', function () { pressWatch(); }, true, (!st.running && !watch.on) || S.hand.busy),
            u.button('Reset', function () { if (!watch.on) { watch.t = 0; n = 0; S.render(); } }, false, watch.on));
          u.h3('Observation table'); u.table();
          u.row(u.button('Change the mass for the next reading', function () { steady().then(function () { S.go(1); }); }, false, S.hand.busy));
          u.next('Next: plot the graph', S.rows.length >= 3);
          if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 masses recorded (5 is better).');
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          return timeOne().then(function () { return [3, 5, 7, 9].reduce(function (pr, nd) { return pr.then(function () {
            return steady().then(function () { return setDiscs(nd); }).then(function () { return pullRelease(3); }).then(timeOne); }); }, Promise.resolve()); }); } },
    ],

    tick: function (dt) {
      if (!st.held) K.step(sim, p, dt);
      var s = Math.sign(sim.y[0]);
      if (s && prevSign && s !== prevSign) { crossings++; if (watch.on) { halves++; if (halves % 2 === 0) n++; } }
      if (s) prevSign = s;
      pose();
    },
  };
  function pose() {
    var py = ptrY(), L = Math.max(0.03, YTOP - (py + 0.026));
    hgeo.update(L);
    botLoop.position.set(0, -L - 0.0085, 0); leg(botLeg, new T.Vector3(CR, -L, 0), new T.Vector3(0, -L - 0.0012, 0));
    hanger.position.set(JX, py, JZ);
    onHanger.forEach(function (d, i) { d.position.set(JX, py + STACK0 + DT / 2 + i * DT, JZ); });
    var hgt = py - STEM; hangShadow.material.opacity = Math.max(0.08, 0.32 - hgt * 0.25); hangShadow.scale.setScalar(0.8 + hgt);
    hudM.set(Math.round(p.m * 1000) + ' g'); hudX.set((sim.y[0] * 100).toFixed(1) + ' cm'); hudN.set(String(n));
  }
  pose();
  return EXP;
});
