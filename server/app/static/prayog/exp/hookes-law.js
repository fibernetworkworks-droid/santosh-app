/* Prayogshala studio module: Hooke's law - spring constant (NCERT Class XI).
   A helical spring hangs from the clamp of a retort stand; a slotted-mass hanger hangs from it and a steel pointer on
   the hanger reads a vertical metre scale. The gloved hand slides 50 g slotted masses onto the hanger one by one.
   Physics: the spring kernel from kernels.js (damped, c from the lab) - the pointer settles by itself after each load. */
HoolaStudio.define('hookes-law', function (S) {
  var T = S.T, M = S.M, K = window.HoolaKernels.K.spring;
  function hidden(id, dflt) { var k = (S.lab.knobs || []).filter(function (q) { return q.id === id; })[0]; return k ? k.value * (k.k || 1) : dflt; }
  var p = window.HoolaKernels.paramsFor('spring', S.lab.params);
  p.k = hidden('k', 20); p.x0 = 0;
  var G = p.g, HANGER = 0.05, DISC = 0.05, MAXN = 9;        // hanger 50 g, slotted masses 50 g, 9 masses = 500 g in all
  var st = { n: 0, zero: null };
  p.m = HANGER;
  var sim = K.init(p); sim.y = [0, 0];

  // ---------- geometry constants
  var JX = 0.06, JZ = -0.05;                     // the clamp jaw: the spring hangs below it
  var YTOP = 0.95, LC0 = 0.08, TURNS = 20, CR = 0.012, WIRE = 0.0011;
  var DR = 0.02, DT = 0.0045, STEM = 0.1;        // slotted mass radius / thickness, hanger stem length
  var RX = 0.11, RZ = -0.05, RY = 0.03, RLEN = 1.0;   // metre scale (standing in a foot)
  var MM = RLEN * 1000;
  function markY(cm) { return RY + RLEN - cm / 100; }   // true-scale ruler: zero at RY + RLEN   // where the printed mark sits
  function cmAt(y) { return (RY + RLEN - y) * 100; }
  var PTR0 = YTOP - LC0 - 0.026;                 // pointer height with the spring unstretched
  var R0 = cmAt(PTR0);                           // scale reading with zero extension (not shown: the student reads it)
  function ext() { return p.m * G / p.k + sim.y[0]; }
  function readingExact() { return R0 + ext() * 100; }
  function reading() { return Math.round(readingExact() * 10) / 10; }   // least count 1 mm
  function settled() { return Math.abs(sim.y[1]) < 0.002 && Math.abs(sim.y[0]) < 0.0003; }

  // ---------- helical spring (rebuilt in place as it stretches)
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
  function slotted() {   // a slotted mass: a disc with a radial slot to the centre hole
    var w = 0.0064, a = Math.asin(w / 2 / DR), s = new T.Shape();
    s.moveTo(DR * Math.cos(a), w / 2); s.absarc(0, 0, DR, a, 2 * Math.PI - a, false); s.lineTo(0, -w / 2); s.absarc(0, 0, w / 2, -Math.PI / 2, Math.PI / 2, true); s.lineTo(DR * Math.cos(a), w / 2);
    var g = new T.ExtrudeGeometry(s, { depth: DT - 0.001, bevelEnabled: true, bevelThickness: 0.0005, bevelSize: 0.0005, bevelSegments: 2, curveSegments: 40 });
    g.translate(0, 0, -(DT - 0.001) / 2); g.rotateX(-Math.PI / 2); g.rotateY(Math.PI); return g;   // flat, slot opening towards -x
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
  // hanger: hook, stem, base disc; the slotted masses sit on the base
  var hanger = new T.Group(); S.scene.add(hanger);
  var hh = S.mesh(new T.TorusGeometry(0.0055, 0.0015, 10, 28, Math.PI * 1.6), M.chrome); hh.rotation.set(0, Math.PI / 2, Math.PI * 0.7); hh.position.y = 0.009; hanger.add(hh);
  var stem = S.mesh(new T.CylinderGeometry(0.0024, 0.0024, STEM, 16), M.chrome); stem.position.y = -STEM / 2 + 0.003; hanger.add(stem);
  var baseD = S.mesh(new T.CylinderGeometry(DR, DR, 0.004, 40), M.brass); baseD.position.y = -STEM + 0.001; hanger.add(baseD);
  var ptr = new T.Group(); hanger.add(ptr);
  var pb = S.mesh(new T.BoxGeometry(0.036, 0.0012, 0.004), M.steel); pb.position.set(0.02, 0, 0.0068); ptr.add(pb);
  var ptip = S.mesh(new T.ConeGeometry(0.002, 0.008, 4), M.steel); ptip.rotation.z = -Math.PI / 2; ptip.scale.set(1, 1, 0.3); ptip.position.set(0.042, 0, 0.0068); ptr.add(ptip);
  var collar = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.006, 16), M.steel); ptr.add(collar);
  ptr.position.set(0, 0, 0); var STACK0 = -STEM + 0.003;   // top of the base disc, in hanger space
  // the metre scale, standing in a wooden foot beside the spring
  var ruler = S.ruler(RLEN, { title: 'METRE SCALE · cm · LC 1 mm', labelEvery: 10 }); ruler.position.set(RX, RY, RZ);
  var rfoot = S.rounded(0.08, 0.05, 0.03, 0.008, M.darkWood); rfoot.rotation.x = -Math.PI / 2; rfoot.position.set(RX, 0.015, RZ); S.scene.add(rfoot); S.contact(0.14, 0.1, RX, RZ, 0.5);
  // slotted masses: a pile on the bench, the hand takes the top one
  var discGeo = slotted(), lblTex = S.canvasTex(128, 64, function (x) { x.fillStyle = '#5a3d0c'; x.font = '700 40px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('50 g', 64, 34); });
  var lblMat = new T.MeshStandardMaterial({ map: lblTex, transparent: true, roughness: 0.5, depthWrite: false }), lblGeo = new T.PlaneGeometry(0.014, 0.007);
  var PILE = new T.Vector3(0.27, 0, 0.08), discs = [], onHanger = [];
  for (var i = 0; i < MAXN; i++) { var d = new T.Group(), dm = S.mesh(discGeo, M.brass); d.add(dm);
    var lb = new T.Mesh(lblGeo, lblMat); lb.rotation.x = -Math.PI / 2; lb.position.set(0.0115, DT / 2 + 0.0002, 0); lb.rotation.z = Math.PI / 2; lb.renderOrder = 2; d.add(lb);
    d.position.set(PILE.x, DT / 2 + i * DT, PILE.z); S.scene.add(d); discs.push(d); }
  S.contact(0.08, 0.08, PILE.x, PILE.z, 0.5);
  var hangShadow = S.contact(0.07, 0.07, JX, JZ, 0.25);
  var pile = discs.slice();   // discs still on the bench, bottom first

  S.addApparatus('stand', stand, 'Retort stand with clamp', 'A heavy iron base and a rigid rod: the top of the spring stays fixed.');
  S.addApparatus('spring', spring, 'Helical spring', 'A steel spring. Within its elastic limit the extension is proportional to the load.');
  S.addApparatus('hanger', hanger, 'Slotted-mass hanger with pointer', 'The hanger itself is 50 g. Its steel pointer moves along the metre scale.');
  S.addApparatus('ruler', ruler, 'Metre scale', 'Fixed upright beside the spring. Read the pointer on it with your eye level with the pointer. Least count 1 mm.');
  S.addApparatus('masses', discs[0], 'Slotted masses', 'Nine slotted masses of 50 g each. The slot lets each one slide onto the hanger stem.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudL = S.hudCard('Load on hanger'), hudR = S.hudCard('Pointer reading'), hudX = S.hudCard('Extension');

  // ---------- positions
  function ptrY() { var r = readingExact(); return markY(r); }
  function stackTopWorld(nn) { return ptrY() + STACK0 + nn * DT; }
  function along(pts) { var L = [0]; for (var i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
    return function (k) { var d = Math.max(0, Math.min(1, k)) * L[L.length - 1]; for (var i = 1; i < pts.length; i++) if (d <= L[i] || i === pts.length - 1) { var f = (d - L[i - 1]) / Math.max(1e-9, L[i] - L[i - 1]); return pts[i - 1].clone().lerp(pts[i], Math.min(1, f)); } }; }
  var GRIP = new T.Vector3(DR + 0.001, 0, 0);   // the fingers hold a disc by its right rim

  function setLoad(nn) { var e = ext(); st.n = nn; p.m = HANGER + nn * DISC; sim.y[0] = e - p.m * G / p.k; }
  function addMass() {
    if (S.hand.busy) return Promise.resolve();
    if (st.n >= MAXN) { S.say('That is 500 g in all. More load would stretch the spring past its elastic limit.'); return Promise.resolve(); }
    if (st.zero === null) { S.say('Take the zero reading first, with only the hanger on the spring.'); return Promise.resolve(); }
    if (Math.abs(sim.y[1]) > 0.02) { S.say('Let the hanger come to rest before adding the next mass.'); return Promise.resolve(); }
    var d = pile.pop(), from = d.position.clone(), nn = st.n;
    var top = stackTopWorld(nn) + DT / 2 + 0.0008, path = along([from, from.clone().setY(from.y + 0.07), new T.Vector3(JX + 0.05, top + 0.05, JZ), new T.Vector3(JX + 0.05, top, JZ), new T.Vector3(JX, top, JZ)]);
    return S.hand.pinchMove(from.clone().add(GRIP), function (k) { return path(k).add(GRIP); }, function (k) { d.position.copy(path(k)); d.rotation.y = 0; }, { ms: 1700 })
      .then(function () { onHanger.push(d); setLoad(nn + 1); S.render(); S.say('Mass added: the load on the hanger is now ' + (st.n * 50) + ' g. Wait for the pointer to settle, then read it.'); });
  }
  function removeMass() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.n) { S.say('There is no slotted mass on the hanger.'); return Promise.resolve(); }
    if (Math.abs(sim.y[1]) > 0.02) { S.say('Let the hanger come to rest first.'); return Promise.resolve(); }
    var d = onHanger[onHanger.length - 1], from = d.position.clone(), to = new T.Vector3(PILE.x, DT / 2 + pile.length * DT, PILE.z);
    var path = along([from, new T.Vector3(JX + 0.05, from.y, JZ), new T.Vector3(JX + 0.05, from.y + 0.05, JZ), to.clone().setY(to.y + 0.07), to]);
    var taken = false, nn = st.n;
    return S.hand.pinchMove(from.clone().add(GRIP), function (k) { return path(k).add(GRIP); }, function (k) { if (!taken) { taken = true; onHanger.pop(); setLoad(nn - 1); } d.position.copy(path(k)); }, { ms: 1600 })
      .then(function () { pile.push(d); S.render(); S.say('Mass removed. The load on the hanger is now ' + (st.n * 50) + ' g.'); });
  }
  function readPointer() {
    if (S.hand.busy) return;
    if (!settled()) { S.say('The pointer is still moving. Wait until it comes to rest, then read it.'); return; }
    var r = reading();
    if (st.zero === null) {
      if (st.n) { S.say('Take the zero reading with only the hanger on: remove the slotted masses first.'); return; }
      st.zero = r; S.addRow({ n: 0, m: 0, F: 0, R: r, x: 0 });
      S.say('Zero reading ' + r.toFixed(1) + ' cm written in your record book. Now add the first 50 g mass.'); S.render(); return; }
    if (S.rows.some(function (row) { return row.n === st.n; })) { S.say('You already recorded the reading for ' + (st.n * 50) + ' g. Add another mass.'); return; }
    var x = Math.round((r - st.zero) * 10) / 10, m = st.n * DISC;
    S.addRow({ n: st.n, m: m, F: m * G, R: r, x: x / 100 });
    S.say('Written in your record book: load ' + (st.n * 50) + ' g, reading ' + r.toFixed(1) + ' cm, extension ' + x.toFixed(1) + ' cm.');
  }

  var EXP = {
    camera: { pos: [0.82, 0.86, 1.76], look: [0.09, 0.5, -0.05] },
    views: { stand: [[0.45, 0.85, 1.1], [-0.05, 0.6, -0.05]], spring: [[0.2, 0.9, 0.5], [0.06, 0.84, -0.05]], hanger: [[0.2, 0.8, 0.45], [0.07, 0.76, -0.05]],
      ruler: [[0.22, 0.86, 0.42], [0.1, 0.8, -0.05]], masses: [[0.45, 0.25, 0.42], [0.27, 0.03, 0.08]],
      rig: [[0.8, 0.66, 1.55], [0.17, 0.45, 0.0]], read: [[0.17, 0.82, 0.36], [0.09, 0.78, -0.05]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'A spring stretches when a load hangs from it. Within the elastic limit the restoring force is proportional to the extension: F = k x (Hooke\'s law), where k is the spring constant.',
      formula: 'F = mg = k x', formulaNote: 'so k = slope of the graph of load F against extension x',
      more: ['The pointer reading with only the hanger is the zero reading. Each extension is the pointer reading minus the zero reading. A graph of F against x is a straight line through the origin; its slope is k.'],
      precautions: 'Add the masses gently and wait for the pointer to come to rest before reading. Keep your eye level with the pointer to avoid parallax. Do not load beyond the elastic limit.' },
    book: { title: 'Expt. — Hooke\'s Law', lines: ['Aim: to find the spring constant k of a spring.', 'Each slotted mass = 50 g, hanger = 50 g', 'g = 9.8 m/s²', 'Extension x = reading − zero reading', 'F = mg = k x   →   k = slope of F vs x', 'Precautions: wait for the pointer to rest, no parallax.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'Load (g)', get: function (r) { return String(Math.round(r.m * 1000)); } },
        { label: 'F = mg (N)', get: function (r) { return r.F.toFixed(2); } }, { label: 'Reading (cm)', get: function (r) { return r.R.toFixed(1); } },
        { label: 'Ext. x (cm)', get: function (r) { return (r.x * 100).toFixed(1); } }] },
    graph: { x: function (r) { return r.x; }, y: function (r) { return r.F; }, xlabel: 'Extension x (m)', ylabel: 'Load F (N)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) { var pts = rows.filter(function (r) { return r.x > 0; }).map(function (r) { return [r.x, r.F]; }); if (pts.length < 2) return null;
      return { label: 'k', value: S.fit.origin(pts), unit: 'N/m', digits: 1, truth: p.k, note: 'From the slope of load F against extension x.' }; },
    tol: 0.02,
    chips: ['What is the elastic limit?', 'Why take a zero reading?', 'Why wait for the pointer to settle?', 'Check my readings', 'Why is the graph a straight line?'],
    viva: [['Why do we wait before reading the pointer after adding a mass?', ['The spring oscillates for a while before it comes to rest', 'The spring gets heavier', 'The scale expands'], 0, 'A reading taken while the hanger still bobs is too high or too low.'],
      ['What does the slope of the load–extension graph give?', ['The spring constant k', 'The mass of the spring', 'g'], 0, 'F = k x, so F/x = k.']],
    askState: function () { return { slotted_masses_on_hanger: st.n, load_on_hanger_g: st.n * 50, hanger_mass_g: 50, pointer_reading_cm: +reading().toFixed(1),
      zero_reading_cm: st.zero, extension_cm: st.zero === null ? null : +(reading() - st.zero).toFixed(1), pointer_settled: settled() }; },

    steps: [
      { id: 'zero', title: 'Zero reading', view: 'rig', render: function (u) {
          u.h2('Set up and take the zero reading');
          u.p('The spring hangs from the clamp of the retort stand. The hanger (50 g) hangs from its lower end, and the pointer on the hanger lies along the metre scale.');
          u.task('1. Check the spring hangs freely', true, 'It does not touch the scale or the stand rod.');
          u.task('2. Read the pointer with only the hanger', st.zero !== null, st.zero !== null ? 'Zero reading = ' + st.zero.toFixed(1) + ' cm' : 'Keep your eye level with the pointer')
            .add(u.button(st.zero !== null ? 'Recorded' : 'Read the pointer', function () { S.focus('read'); readPointer(); }, st.zero === null, st.zero !== null));
          u.live(function () { return 'Pointer: ' + reading().toFixed(1) + ' cm' + (settled() ? ' · at rest' : ' · moving'); });
          u.note('Every extension is measured from this zero reading.');
          u.next('Next: add the masses', st.zero !== null);
        },
        ok: function () { return st.zero !== null; },
        auto: function () { S.advance(20, settled); readPointer(); return Promise.resolve(); } },
      { id: 'load', title: 'Add masses', view: 'rig', render: function (u) {
          u.h2('Add masses one by one');
          u.p('Let the hand slide a 50 g slotted mass onto the hanger. Wait until the pointer comes to rest, then read it. Repeat for each mass.');
          u.live(function () { return 'Load ' + (st.n * 50) + ' g · reading ' + reading().toFixed(1) + ' cm' + (settled() ? ' · at rest' : ' · settling…'); });
          u.row(u.button('Add a 50 g mass', function () { addMass(); }, true, S.hand.busy || st.n >= MAXN),
            u.button('Read the pointer', function () { S.focus('read'); readPointer(); }, false, S.hand.busy),
            u.button('Remove a mass', function () { removeMass(); }, false, S.hand.busy || !st.n));
          if (st.n >= MAXN) u.note('All nine masses are on (500 g). Do not load the spring any further.');
          u.h3('Observation table'); u.table();
          var have = S.rows.filter(function (r) { return r.x > 0; }).length;
          u.next('Next: plot the graph', have >= 4);
          if (have < 4) u.p(have + ' of at least 4 loads recorded (6 or more is better).');
        },
        ok: function () { return S.rows.filter(function (r) { return r.x > 0; }).length >= 4; },
        auto: function () { var pr = Promise.resolve();
          for (var i = 0; i < 7; i++) pr = pr.then(function () { return addMass(); }).then(function () { S.advance(40, settled); readPointer(); });
          return pr; } },
    ],

    tick: function (dt) { K.step(sim, p, dt); pose(); },
  };
  function pose() {
      var py = ptrY(), cb = py + 0.026, L = Math.max(0.03, YTOP - cb);
      hgeo.update(L);
      botLoop.position.set(0, -L - 0.0085, 0); leg(botLeg, new T.Vector3(CR, -L, 0), new T.Vector3(0, -L - 0.0012, 0));
      hanger.position.set(JX, py, JZ);
      onHanger.forEach(function (d, i) { d.position.set(JX, py + STACK0 + DT / 2 + i * DT, JZ); });
      var hgt = py - STEM; hangShadow.material.opacity = Math.max(0.08, 0.32 - hgt * 0.25); hangShadow.scale.setScalar(0.8 + hgt);
      hudL.set((st.n * 50) + ' g'); hudR.set(reading().toFixed(1) + ' cm'); hudX.set(st.zero === null ? '—' : (reading() - st.zero).toFixed(1) + ' cm');
  }
  pose();
  return EXP;
});
