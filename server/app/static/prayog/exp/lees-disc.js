/* Prayogshala studio module: Lee and Charlton's disc - thermal conductivity of a bad conductor (B.Sc. Thermal Physics).
   Physics: the hw_lees kernel (packs/heat_wave_ug) - the same numbers the server checks. The sample sits between a heated
   chest and a brass disc B; disc B settles at th2 (mode 0). With the sample off, the bare disc is heated (mode 2) and
   timed as it cools (mode 1). The hidden knob k (the sample) is what the student measures. */
HoolaStudio.define('lees-disc', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.hw_lees;
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('hw_lees');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || ''), METHOD = String(VAR.method || '');
  var ELEC = /electric/i.test(METHOD);
  var SMAT = /ebonite|rubber/i.test(SAMPLE) ? { name: 'Ebonite', mat: M.black, tag: 'EBONITE' } : { name: 'Glass', mat: new T.MeshPhysicalMaterial({ color: 0xcfe6e2, roughness: 0.05, transmission: 0.7, thickness: 0.01, ior: 1.5, transparent: true, opacity: 0.9 }), tag: 'GLASS' };
  function r1(v) { return Math.round(v * 10) / 10; }
  var mB = K.mass(p);
  var sim = K.init(p);
  var st = { dims: false, heat: false, speed: 30, read: null, bare: false, hot: false, chestOff: false, timing: false, armed: false, ta: 0, Ta: 0, tb: 0, Tb: 0, dtdt: null, sampleOut: false, cool: false };
  var CX = 0.0, CZ = -0.22, YB = 0.2;                                // centre of the stack, height of disc B's middle
  var R = p.r, HB = p.h, D = p.d, CH = 0.06;

  function carry(startPt, legs, pose) {
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, 'side', 800); }).then(function () { return S.hand.shape(pose || 'grip', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, 'side', l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  function tube(pts, r, mat) {
    var curve = new T.CatmullRomCurve3(pts.map(function (a) { return new T.Vector3(a[0], a[1], a[2]); }));
    var m = S.mesh(new T.TubeGeometry(curve, 40, r, 10, false), mat, true, false); S.scene.add(m); return m;
  }
  function cord(a, b, r) { var A = new T.Vector3().fromArray(a), Bv = new T.Vector3().fromArray(b), len = A.distanceTo(Bv);
    var m = S.mesh(new T.CylinderGeometry(r, r, len, 6), M.thread, false, false); m.position.copy(A.clone().add(Bv).multiplyScalar(0.5));
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), Bv.clone().sub(A).normalize()); S.scene.add(m); return m; }
  var rubber = new T.MeshStandardMaterial({ color: 0x2b2d30, roughness: 0.6 });

  // ---------- retort stand, ring and the three cords that hang disc B
  var stand = new T.Group(); S.scene.add(stand);
  var base = S.rounded(0.16, 0.12, 0.025, 0.006, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(CX - 0.16, 0.0125, CZ); stand.add(base);
  var rod = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.55, 16), M.chrome); rod.position.set(CX - 0.16, 0.275, CZ); stand.add(rod);
  var arm = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.17, 12), M.chrome); arm.rotation.z = Math.PI / 2; arm.position.set(CX - 0.08, 0.5, CZ); stand.add(arm);
  var boss = S.mesh(new T.BoxGeometry(0.026, 0.02, 0.02), M.iron); boss.position.set(CX - 0.16, 0.5, CZ); stand.add(boss);
  var ring = S.mesh(new T.TorusGeometry(0.03, 0.002, 8, 32), M.chrome); ring.rotation.x = Math.PI / 2; ring.position.set(CX, 0.5, CZ); stand.add(ring);
  S.contact(0.22, 0.18, CX - 0.16, CZ, 0.5);
  var ang = [Math.PI / 2, Math.PI / 2 + 2.094, Math.PI / 2 + 4.189];
  var cords = ang.map(function (a) { return cord([CX + Math.cos(a) * 0.03, 0.5, CZ + Math.sin(a) * 0.03], [CX + Math.cos(a) * (R - 0.002), YB, CZ + Math.sin(a) * (R - 0.002)], 0.0006); });

  // ---------- disc B, sample, steam chest / heater block
  var discB = S.mesh(new T.CylinderGeometry(R, R, HB, 64), M.brass); discB.position.set(CX, YB, CZ); S.scene.add(discB);
  var bl = S.label('B', { w: 0.012, ratio: 1, color: '#4a3510' }); bl.rotation.y = 0; bl.position.set(CX, YB, CZ + R + 0.0006); S.scene.add(bl);
  var SY = YB + HB / 2 + D / 2;
  var sample = new T.Group(); S.scene.add(sample);
  var sdisc = S.mesh(new T.CylinderGeometry(R, R, D, 64), SMAT.mat); sample.add(sdisc); sample.position.set(CX, SY, CZ);
  var CY0 = YB + HB / 2 + D + CH / 2, CY1 = YB + HB / 2 + CH / 2;      // chest height on the sample, and directly on disc B
  var chest = new T.Group(); S.scene.add(chest); chest.position.set(CX, CY0, CZ);
  var cbody = S.mesh(new T.CylinderGeometry(R + 0.004, R + 0.004, CH, 48), M.brass); chest.add(cbody);
  var ctop = S.mesh(new T.CylinderGeometry(R * 0.35, R * 0.35, 0.012, 24), M.brass); ctop.position.y = CH / 2 + 0.006; chest.add(ctop);
  var cl = S.label(ELEC ? 'HEATER BLOCK' : 'STEAM CHEST', { w: 0.04, ratio: 0.2, color: '#4a3510' }); cl.position.set(0, 0.0, R + 0.0046); chest.add(cl);
  var th1 = S.thermometer({ len: 0.3, min: 20, max: 110, value: p.Ts }); th1.rotation.z = -Math.PI / 2; th1.position.set(0.012, 0, 0.012); chest.add(th1);
  var th2 = S.thermometer({ len: 0.3, min: 20, max: 110, value: p.Ts, pos: [CX + 0.012, YB, CZ + 0.012] }); th2.rotation.z = -Math.PI / 2;
  // cork mat where the sample waits
  var mat = S.mesh(new T.CylinderGeometry(0.05, 0.05, 0.004, 40), M.cork); mat.position.set(0.5, 0.002, -0.1); S.scene.add(mat); S.contact(0.12, 0.12, 0.5, -0.1, 0.4);
  var PARK_S = new T.Vector3(0.5, 0.004 + D / 2, -0.1), PARK_C = new T.Vector3(0.5, 0.004 + CH / 2 + 0.02, -0.12);
  // ---------- heat source: boiler + steam pipe, or a mains heater supply
  var BX = -0.62, BZ = -0.28, srcSwitch, boiler;
  var pipeMesh = null, wireMesh = null;
  function pipePts(c) { return [[BX, 0.2, BZ], [BX, 0.26, BZ], [BX + 0.2, 0.3, CZ - 0.02], [Math.min(c.x, 0.3) - 0.1, c.y + CH / 2 + 0.12, c.z - 0.02], [c.x - 0.03, c.y + CH / 2 + 0.05, c.z - 0.01], [c.x, c.y + CH / 2 + 0.014, c.z]]; }
  function wirePts(c) { return [[BX + 0.1, 0.03, BZ + 0.0], [c.x - 0.12, 0.05, c.z - 0.04], [c.x - 0.03, c.y, c.z - 0.03]]; }
  function setSource(c) {
    if (!ELEC) { if (pipeMesh) { pipeMesh.geometry.dispose(); pipeMesh.geometry = new T.TubeGeometry(new T.CatmullRomCurve3(pipePts(c).map(function (a) { return new T.Vector3(a[0], a[1], a[2]); })), 40, 0.005, 10, false); }
      else pipeMesh = tube(pipePts(c), 0.005, rubber); }
    else { if (wireMesh) wireMesh.set(wirePts(c)); else wireMesh = S.wire(wirePts(c), 'red'); }
  }
  if (!ELEC) {
    var plate = S.rounded(0.16, 0.16, 0.04, 0.01, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); plate.rotation.x = -Math.PI / 2; plate.position.set(BX, 0.02, BZ); S.scene.add(plate);
    srcSwitch = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), M.red); srcSwitch.rotation.x = Math.PI / 2; srcSwitch.position.set(BX + 0.05, 0.02, BZ + 0.083); S.scene.add(srcSwitch);
    boiler = S.mesh(new T.SphereGeometry(0.065, 32, 24), M.copper); boiler.position.set(BX, 0.1, BZ); boiler.scale.y = 0.9; S.scene.add(boiler);
    var bneck = S.mesh(new T.CylinderGeometry(0.018, 0.026, 0.05, 20), M.copper); bneck.position.set(BX, 0.16, BZ); S.scene.add(bneck);
    S.contact(0.22, 0.22, BX, BZ, 0.5);
  } else {
    boiler = S.powerBox([BX, 0, BZ], 'HEATER SUPPLY');
    srcSwitch = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.012, 24), M.red); srcSwitch.rotation.x = Math.PI / 2; srcSwitch.position.set(BX + 0.05, 0.05, BZ + 0.1); S.scene.add(srcSwitch);
  }
  setSource(chest.position);
  var watch = S.stopwatch([0.3, 0.035, 0.17], [-1.15, 0, -0.2]);
  var steamTex = S.canvasTex(128, 128, function (x) { var g = x.createRadialGradient(64, 64, 2, 64, 64, 62); g.addColorStop(0, 'rgba(255,255,255,.75)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });
  var wisps = []; for (var wi = 0; wi < 5; wi++) { var w = new T.Mesh(new T.PlaneGeometry(0.045, 0.045), new T.MeshBasicMaterial({ map: steamTex, transparent: true, opacity: 0, depthWrite: false }));
    w.userData.ph = wi / 5; S.scene.add(w); wisps.push(w); }

  S.addApparatus('stand', stand, 'Retort stand and ring', 'Three cords from the ring hang disc B, so nothing touches it but the sample and the heated block.');
  S.addApparatus('discB', discB, 'Brass disc B', 'Brass disc of radius ' + (R * 1000).toFixed(0) + ' mm and thickness ' + (HB * 1000).toFixed(0) + ' mm. Its mass, from the balance, is ' + (mB * 1000).toFixed(1) + ' g; brass has s = ' + p.s + ' J/(kg K).');
  S.addApparatus('sample', sample, SMAT.name + ' disc (the bad conductor)', 'A thin ' + SMAT.name.toLowerCase() + ' disc of the same radius as B, ' + (D * 1000).toFixed(1) + ' mm thick.');
  S.addApparatus('chest', chest, ELEC ? 'Electrically heated block' : 'Steam chamber', ELEC ? 'A brass block with a heater coil; the supply is set so it settles near ' + p.Th.toFixed(0) + ' °C.' : 'Steam from the boiler keeps this block at ' + p.Th.toFixed(0) + ' °C.');
  S.addApparatus('th1', th1, 'Thermometer θ1', 'In a hole in the heated block. Reads the temperature of the top face of the sample. Least count 0.1 °C.');
  S.addApparatus('th2', th2, 'Thermometer θ2', 'In a hole in disc B. Reads the temperature of the lower face of the sample. Least count 0.1 °C.');
  S.addApparatus('boiler', boiler, ELEC ? 'Heater supply' : 'Boiler', ELEC ? 'Mains supply for the heater, with a switch.' : 'Electric boiler that makes steam. Switch it on at the plate.');
  S.addApparatus('mat', mat, 'Cork mat', 'Where the sample and the heated block wait while the bare disc is heated and cooled.');
  S.addApparatus('sw', watch.group, 'Digital stopwatch', 'Times the fall of disc B through 8 K.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here.');

  var bookLines = ['Aim: to find k of ' + SMAT.name.toLowerCase() + ' by Lee and Charlton\'s method.', 'Sample d = ' + (D * 1000).toFixed(1) + ' mm.  Disc B: r = ' + (R * 1000).toFixed(1) + ' mm, h = ' + (HB * 1000).toFixed(1) + ' mm,', 'm = ' + (mB * 1000).toFixed(1) + ' g,  s = ' + p.s + ' J/(kg K)', 'k = m s (dθ/dt)(r + 2h)/(2r + 2h) · d / (π r² (θ1 − θ2))'];
  var hudA = S.hudCard('θ1 (block)'), hudB = S.hudCard('θ2 (disc B)'), hudC = S.hudCard('Stopwatch');

  function th1Now() { return p.mode > 1.5 || st.chestOff ? p.Ts : p.Ts + (p.Th - p.Ts) * (1 - Math.exp(-Math.max(0, sim.t) / 90)); }
  // ---------- actions
  function measureAll() { if (st.dims) return; st.dims = true; S.focus('discB');
    S.say('Sample ' + (D * 1000).toFixed(1) + ' mm (screw gauge). Disc B: radius ' + (R * 1000).toFixed(1) + ' mm, thickness ' + (HB * 1000).toFixed(1) + ' mm, mass ' + (mB * 1000).toFixed(1) + ' g (balance). Written in your record book.'); S.book.draw(); S.render(); }
  function heatOn() { if (S.hand.busy || st.heat) return Promise.resolve(); return S.hand.tap(srcSwitch).then(function () { S.click(2000); st.heat = true; sim = K.init(p); p.mode = 0; S.say((ELEC ? 'Heater on.' : 'Boiler on: steam is on its way.') + ' Disc B will warm up slowly.'); S.render(); }); }
  function drift() { var C = mB * p.s, G = (p.k * Math.PI * R * R / D) + p.hc * Math.PI * (R * R + 2 * R * HB), tau = C / G, Tss = K.th2(p), a = sim.T, b = Tss + (p.T0 - Tss) * Math.exp(-Math.max(0, sim.t - 300) / tau);
    return { d: a - b, ok: p.mode < 0.5 && sim.t >= 300 && Math.abs(a - b) < 0.05 }; }
  function jump(sec) { if (!st.heat) { S.say('Switch the heater on first.'); return; } if (p.mode > 0.5) { S.say('The sample is off; this is no longer the steady state.'); return; } K.step(sim, p, sec); S.render(); }
  function readAll() { if (!st.heat) { S.say('Switch the heater on first.'); return; } if (p.mode > 0.5) { S.say('Read θ1 and θ2 while the sample is on.'); return; }
    st.read = { th1: r1(th1Now()), th2: r1(sim.T) }; S.say('θ1 = ' + st.read.th1.toFixed(1) + ' °C, θ2 = ' + st.read.th2.toFixed(1) + ' °C.'); S.focus('th2'); S.render(); }
  function moveGroup(g, a, b, lift) {
    return carry(new T.Vector3(a.x + R + 0.006, a.y, a.z), [{ ms: 1400, fn: function (k) { var q = a.clone().lerp(b, k); q.y += Math.sin(k * Math.PI) * lift; return new T.Vector3(q.x + R + 0.006, q.y, q.z); },
      onK: function (k) { var q = a.clone().lerp(b, k); q.y += Math.sin(k * Math.PI) * lift; g.position.copy(q); if (g === chest) setSource(q); } }], 'grip').then(function () { g.position.copy(b); if (g === chest) setSource(b); });
  }
  function bareHeat() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.read) { S.say('Read θ1 and θ2 first, with the sample in place.'); return Promise.resolve(); }
    if (st.timing || st.armed) { S.say('Finish the timing first.'); return Promise.resolve(); }
    var chain = Promise.resolve();
    if (!st.sampleOut) chain = chain.then(function () { return moveGroup(chest, chest.position.clone(), PARK_C.clone().setX(0.38), 0.1); })
      .then(function () { return moveGroup(sample, sample.position.clone(), PARK_S.clone(), 0.1); }).then(function () { st.sampleOut = true; return moveGroup(chest, chest.position.clone(), new T.Vector3(CX, CY1, CZ), 0.0); });
    else chain = chain.then(function () { return moveGroup(chest, chest.position.clone(), new T.Vector3(CX, CY1, CZ), 0.1); });
    return chain.then(function () {
      p.mode = 2; var tgt = st.read.th2 + 4.6, n = 0; while (r1(sim.T) < tgt && n++ < 20000) K.step(sim, p, 0.5);
      st.hot = true; S.say('Disc B is heated directly to ' + r1(sim.T).toFixed(1) + ' °C. Lift the block away and time the cooling.'); return moveGroup(chest, chest.position.clone(), PARK_C.clone(), 0.1); })
      .then(function () { p.mode = 1; st.chestOff = true; S.render(); });
  }
  function armTiming() {
    if (S.hand.busy) return;
    if (!st.hot || p.mode !== 1) { S.say('Heat the bare disc and lift the block away first.'); return; }
    st.armed = true; st.timing = false; st.dtdt = null; S.say('Ready: the stopwatch starts when the thermometer reads θ2 + 4 K and stops at θ2 − 4 K.'); S.render();
  }
  function track() {   // the student's hand on the stopwatch, following the mercury
    if (!st.armed && !st.timing) return;
    var rd = r1(sim.T), hi = st.read.th2 + 4.0, lo = st.read.th2 - 4.0;
    if (st.armed && rd <= hi + 1e-9) { st.armed = false; st.timing = true; st.ta = sim.t; st.Ta = rd; watch.t = 0; watch.on = true; S.click(2400); S.render(); }
    else if (st.timing && rd <= lo + 1e-9) { st.timing = false; watch.on = false; st.tb = sim.t; st.Tb = rd; var tt = Math.round(st.tb - st.ta);
      st.dtdt = (st.Ta - st.Tb) / tt; st.tt = tt; S.say('Fell from ' + st.Ta.toFixed(1) + ' to ' + st.Tb.toFixed(1) + ' °C in ' + tt + ' s: ' + st.dtdt.toFixed(4) + ' K/s.'); S.render(); }
  }
  function record() {
    if (st.dtdt === null || !st.read) { S.say('Time a cooling run first.'); return; }
    S.addRow({ th1: st.read.th1, th2: st.read.th2, dtdt: st.dtdt, t: st.tt, Ta: st.Ta, Tb: st.Tb }); st.dtdt = null; st.hot = false; S.say('Row written.'); S.render();
  }
  function kOne(r) { return mB * p.s * r.dtdt * (R + 2 * HB) / (2 * R + 2 * HB) * D / (Math.PI * R * R * (r.th1 - r.th2)); }
  function setSpeed(v) { st.speed = v; S.render(); }

  return {
    camera: { pos: [0.05, 0.45, 1.35], look: [-0.02, 0.17, -0.22] },
    views: { stand: [[0.1, 0.4, 0.55], [CX - 0.1, 0.3, CZ]], discB: [[0.1, 0.28, 0.2], [CX, YB, CZ]], sample: [[0.12, 0.3, 0.2], [CX, SY, CZ]], chest: [[0.12, 0.35, 0.22], [CX, CY0, CZ]],
      th1: [[0.3, 0.35, 0.3], [CX + 0.15, CY0, CZ]], th2: [[0.3, 0.3, 0.3], [CX + 0.15, YB, CZ]], boiler: [[-0.4, 0.3, 0.3], [BX, 0.1, BZ]], mat: [[0.55, 0.25, 0.25], [0.5, 0.03, -0.1]],
      sw: [[-0.5, 0.4, 0.5], [-1.1, 0.05, -0.2]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'With the sample between the heated block and disc B, heat flows through it at the same rate as disc B loses it to the air. The loss is found from how fast the bare disc cools at the same temperature.',
      formula: 'k π r² (θ1 − θ2) / d = m s (dθ/dt) (r + 2h) / (2r + 2h)', formulaNote: 'so k = m s (dθ/dt) (r + 2h) / (2r + 2h) · d / (π r² (θ1 − θ2))',
      more: ['With the sample on, the top face of disc B is covered: only its lower face and edge lose heat, which is the fraction (r + 2h)/(2r + 2h) of the loss from the whole bare disc.'],
      precautions: 'Wait for steady θ1 and θ2. Handle the hot block and sample with tongs. Keep the disc away from draughts while it cools. Read the thermometers with your eye level with the mercury.' },
    book: { title: 'Expt. — Lee and Charlton\'s disc', lines: bookLines,
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'θ1 (°C)', get: function (r) { return r.th1.toFixed(1); } }, { label: 'θ2 (°C)', get: function (r) { return r.th2.toFixed(1); } },
        { label: 'Fall (°C)', get: function (r) { return r.Ta.toFixed(1) + '→' + r.Tb.toFixed(1); } }, { label: 't (s)', get: function (r) { return String(r.t); } },
        { label: 'dθ/dt (K/s)', get: function (r) { return r.dtdt.toFixed(4); } }, { label: 'k', get: function (r) { return kOne(r).toFixed(3); } }] },
    result: function (rows) { if (!rows.length) return null; var s = 0; rows.forEach(function (r) { s += kOne(r); });
      return { label: 'k (' + SMAT.name.toLowerCase() + ')', value: s / rows.length, unit: 'W/(m·K)', digits: 3, truth: p.k, note: 'Mean of ' + rows.length + ' cooling runs.' }; },
    tol: 0.05,
    chips: ['Why is disc B hung by cords?', 'Why measure the cooling with the sample off?', 'Why is (r + 2h)/(2r + 2h) used?', 'Check my readings', 'Why is my k different?'],
    viva: [['Why is the sample made thin and wide?', ['So the heat flows straight through it and the temperature drop is measurable', 'To make it heavy', 'To make it cool faster'], 0, 'A thin, wide disc passes the heat along its thickness and loses little from its edge.'],
      ['Which face of disc B is covered while the sample is on?', ['The top face', 'The lower face', 'The edge'], 0, 'The sample sits on the top face, so only the lower face and the edge lose heat.']],
    askState: function () { return { heater_on: st.heat, sample_in_place: !st.sampleOut, lab_time_s: Math.round(sim.t), theta2_C: r1(sim.T), theta1_C: r1(th1Now()), steady: st.heat ? drift().ok : false, cooling_runs: S.rows.length, sample: SMAT.name }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'discB', render: function (u) {
          u.h2('Measure the disc, then switch the heat on');
          u.task('1. Measure the sample and disc B', st.dims, st.dims ? 'd = ' + (D * 1000).toFixed(1) + ' mm; r = ' + (R * 1000).toFixed(1) + ' mm; m = ' + (mB * 1000).toFixed(1) + ' g' : 'Screw gauge, vernier callipers and a balance')
            .add(u.button(st.dims ? 'Measured' : 'Measure', measureAll, !st.dims, st.dims));
          u.task('2. Switch the ' + (ELEC ? 'heater' : 'boiler') + ' on', st.heat, st.heat ? 'On' : 'The hand presses the switch')
            .add(u.button(st.heat ? 'On' : 'Switch on', function () { heatOn(); }, st.dims && !st.heat, st.heat || S.hand.busy));
          u.note('The sample is ' + SMAT.name.toLowerCase() + ', ' + (D * 1000).toFixed(1) + ' mm thick. It will take a while for disc B to settle.');
          u.next('Next: wait for the steady state', st.dims && st.heat);
        },
        ok: function () { return st.dims && st.heat; },
        auto: function () { measureAll(); return heatOn(); } },
      { id: 'steady', title: 'Steady state', view: 'th2', render: function (u) {
          u.h2('Wait for θ2 to settle');
          u.p('Disc B warms up until the heat that enters it equals the heat it loses. Run the clock faster, then check that θ2 changed by less than 0.05 °C in five minutes.');
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 30, 120].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.row(u.button('Jump 10 minutes', function () { jump(600); }, false, false));
          u.live(function () { var d = drift(); return 'Lab time ' + Math.floor(sim.t / 60) + ' min · θ1 ' + r1(th1Now()).toFixed(1) + ' · θ2 ' + r1(sim.T).toFixed(1) + ' °C · ' + (sim.t < 300 ? 'too early to judge' : d.ok ? 'STEADY' : 'still changing'); });
          u.next('Next: the cooling rate', drift().ok);
        },
        ok: function () { return drift().ok; },
        auto: function () { for (var i = 0; i < 200 && !drift().ok; i++) K.step(sim, p, 300); return Promise.resolve(); } },
      { id: 'cool', title: 'Cooling rate', view: 'chest', render: function (u) {
          u.h2('Find the cooling rate of the bare disc');
          u.task('1. Read θ1 and θ2 (sample in place)', !!st.read, st.read ? 'θ1 ' + st.read.th1.toFixed(1) + ' °C, θ2 ' + st.read.th2.toFixed(1) + ' °C' : 'Both thermometers are steady now')
            .add(u.button(st.read ? 'Read again' : 'Read the thermometers', readAll, !st.read, !!st.sampleOut || S.hand.busy));
          u.task('2. Remove the sample and heat disc B directly', st.hot || st.chestOff, st.chestOff ? 'The bare disc is hot and the block is lifted away' : 'The hand lifts the block and the sample away, then lowers the block on B')
            .add(u.button('Heat the bare disc', function () { bareHeat(); }, !!st.read && !st.hot, !st.read || st.hot || S.hand.busy));
          u.task('3. Time the fall through 8 K', st.dtdt !== null, st.dtdt !== null ? st.dtdt.toFixed(4) + ' K/s' : (st.armed ? 'Waiting for θ2 + 4 K…' : st.timing ? 'Timing…' : 'Starts at θ2 + 4 K, stops at θ2 − 4 K'))
            .add(u.button(st.armed || st.timing ? 'Timing…' : 'Start timing', armTiming, st.hot && st.dtdt === null, !st.hot || st.armed || st.timing || st.dtdt !== null));
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 30, 120].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.live(function () { return 'θ2 ' + r1(sim.T).toFixed(1) + ' °C · stopwatch ' + watch.t.toFixed(0) + ' s'; });
          u.row(u.button('Write in the table', record, st.dtdt !== null, st.dtdt === null));
          u.h3('Observation table'); u.table();
          u.next('Next: work out k', S.rows.length >= 2);
          if (S.rows.length < 2) u.p(S.rows.length + ' run(s) so far. Heat the bare disc again and take at least 2 runs.');
        },
        ok: function () { return S.rows.length >= 2; },
        auto: function () {
          function runUntil(cond, maxS) { var n = 0; while (!cond() && n++ < maxS * 2) { K.step(sim, p, 0.5); if (st.timing) watch.t = sim.t - st.ta; track(); } }
          function one() { return bareHeat().then(function () { armTiming(); runUntil(function () { return st.dtdt !== null; }, 4000); record(); }); }
          readAll(); return one().then(one); } },
    ],

    tick: function (dt) {
      if (st.heat) { var d = dt * st.speed; K.step(sim, p, d); if (st.timing) watch.t = sim.t - st.ta; track(); }
      th1.set(st.heat ? th1Now() : p.Ts); th2.set(st.heat ? sim.T : p.Ts);
      var steam = (!ELEC && st.heat && !st.chestOff) ? 1 : 0, now = (S._steamT = (S._steamT || 0) + dt);
      wisps.forEach(function (w) { var ph = (now * 0.3 + w.userData.ph) % 1; w.position.set(BX + Math.sin(ph * 6 + w.userData.ph * 9) * 0.01, 0.23 + ph * 0.12, BZ);
        w.quaternion.copy(S.camera.quaternion); w.scale.setScalar(0.6 + ph * 1.4); w.material.opacity = steam * 0.3 * Math.sin(ph * Math.PI); });
      hudA.set(r1(st.heat ? th1Now() : p.Ts).toFixed(1) + ' °C'); hudB.set(r1(st.heat ? sim.T : p.Ts).toFixed(1) + ' °C'); hudC.set(watch.t.toFixed(0) + ' s');
    },
  };
});
