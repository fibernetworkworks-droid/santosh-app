/* Prayogshala studio module: surface tension by capillary rise (NCERT Class XI, Section B).
   A glass trough of liquid stands on the bench; a fine capillary tube is held upright in the clamp of a retort stand
   with its lower end dipping in the liquid, and a pointer on a small stand has its tip just at the liquid surface.
   A travelling microscope on its own pillar reads heights on a millimetre scale with a vernier (least count 0.001 cm).
   The gloved hand lowers the tube into the liquid, slides the microscope carriage to focus on the meniscus and then on
   the pointer tip, and swaps the tube for one of another bore.
   Physics: the `capillary` kernel of the mech11 pack - h = 2 T cosθ / (r ρ g), the same numbers the server checks.
   Everything (liquid, bores, surface tension) is read from the lab's own params, so one rig serves the whole family. */
HoolaStudio.define('capillary-rise', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.capillary;
  function labParams(name) {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(name, o);
  }
  var p = labParams('capillary');
  var VAR = S.lab.variant || {}, SAMPLE = String(VAR.sample || '');
  // the liquid: its name and colour come from the variant's sample line; the base lab is clean water
  var LIQS = [[/detergent|soap/i, 'water with detergent', 0x74b4b0], [/glycer/i, 'glycerine', 0xc8bb70],
    [/kerosene/i, 'kerosene oil', 0xd6c88c], [/alcohol|ethanol/i, 'ethyl alcohol', 0xa9c3d2],
    [/salt|brine/i, 'salt solution', 0x7ab0cc], [/water/i, 'water', 0x58a3c8]];
  var LQ = { name: 'water', col: 0x58a3c8 };
  LIQS.forEach(function (q) { if (LQ.set !== 1 && q[0].test(SAMPLE)) { LQ = { name: q[1], col: q[2], set: 1 }; } });
  if (!LQ.set && /detergent/i.test(S.lab.title || '')) LQ = { name: 'water with detergent', col: 0x74b4b0 };

  // ---------- the three tubes this lab uses: its own bore first, then a narrower and a wider one
  function r3(v) { return Math.round(v * 1e5) / 1e5; }
  var R0 = p.r, BORES = [r3(R0), r3(Math.max(0.00012, R0 * 0.6)), r3(Math.min(0.0006, R0 * 1.7))];
  if (BORES[2] <= BORES[0] * 1.08) BORES[2] = r3(BORES[0] * 1.4);
  function riseFor(r) { return 2 * p.T * Math.cos(p.theta) / (r * p.rho * p.g); }
  var HMAX = riseFor(Math.min(BORES[0], BORES[1], BORES[2]));

  // ---------- geometry (metres; bench top y = 0)
  var TX = 0.0, TZ = -0.1, TR = 0.062, TH = 0.05, LIQ = 0.034;          // trough + liquid surface
  var DIP = 0.016, TUBE_L = Math.max(0.16, Math.min(0.3, 0.055 + HMAX * 1.3));
  var TUBE_R = 0.0032, BORE_DRAWN = 0.0017;                             // the bore is drawn far thicker than life
  var UP_Y = LIQ + 0.055;                                               // the tube waits this far above the liquid
  var MX = 0.19, MZ = TZ - 0.03, PIL_H = Math.max(0.3, LIQ + HMAX + 0.1);
  var SC_Y0 = 0.03, SC_LEN = PIL_H - 0.06;                              // the printed scale: zero at SC_Y0
  var CARR_Y0 = LIQ + 0.02;
  var PTX = -0.03, PTZ = TZ - 0.03, PFX = -0.085, PFZ = TZ - 0.09;      // pointer tip (at the surface) and its foot

  var sim = K.init(p);
  var st = { idx: 0, dipped: false, carr: CARR_Y0, r1: null, r2: null, swapped: 0, raised: true };

  function heq() { return riseFor(p.r); }
  function settled() { return Math.abs(sim.h - heq()) < 2e-5; }
  function menY() { return LIQ + (st.dipped ? sim.h : 0); }
  function readingAt(y) { return Math.round((y - SC_Y0) * 100 * 1000) / 1000; }   // cm, least count 0.001 cm
  function reading() { return readingAt(st.carr); }

  // ---------- the bench: trough of liquid
  function troughGeom(r, h) {
    var pts = [[0, 0], [r - 0.004, 0], [r, 0.004], [r, h], [r + 0.0016, h + 0.001], [r - 0.0014, h + 0.0004],
      [r - 0.0014, 0.005], [r - 0.005, 0.0016], [0, 0.0016]].map(function (a) { return new T.Vector2(a[0], a[1]); });
    return new T.LatheGeometry(pts, 54);
  }
  var trough = new T.Group(); S.scene.add(trough);
  var gm = M.glass.clone(); gm.side = T.DoubleSide;
  trough.add(S.mesh(troughGeom(TR, TH), gm));
  var liqM = new T.MeshStandardMaterial({ color: LQ.col, roughness: 0.22, metalness: 0.0 });
  var liquid = S.mesh(new T.CylinderGeometry(TR - 0.0016, TR - 0.0016, LIQ - 0.002, 48), liqM, false);
  liquid.position.y = 0.002 + (LIQ - 0.002) / 2; liquid.renderOrder = 2; trough.add(liquid);
  trough.position.set(TX, 0, TZ);
  S.contact(0.16, 0.16, TX, TZ, 0.5);

  // ---------- retort stand, its clamp holding the tube over the trough
  var jawY = (LIQ - DIP) + TUBE_L * 0.82;                               // the clamp grips the tube, raised or dipped
  var stand = S.stand({ x: -0.11, z: TZ, h: jawY + 0.1, armY: jawY, armLen: 0.3 });
  var jawPad = S.rounded(0.026, 0.02, 0.026, 0.004, M.rubber); jawPad.position.set(TX, jawY - 0.002, TZ); S.scene.add(jawPad);

  // ---------- the capillary tubes (one in the clamp, the others in a wooden rack)
  var RACK = new T.Vector3(0.33, 0, 0.01);
  var rack = new T.Group(); rack.position.copy(RACK); S.scene.add(rack);
  var rb = S.rounded(0.2, 0.06, 0.02, 0.004, M.darkWood); rb.rotation.x = -Math.PI / 2; rb.position.y = 0.01; rack.add(rb);
  [-0.06, 0.06].forEach(function (x) {
    var v = S.rounded(0.02, 0.03, 0.018, 0.003, M.darkWood); v.position.set(x, 0.03, 0); rack.add(v);
    var notch = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.02, 14), M.rubber); notch.rotation.z = Math.PI / 2; notch.position.set(x, 0.044, 0); rack.add(notch);
  });
  var rl = S.label('CAPILLARY TUBES', { w: 0.13, ratio: 0.14, color: '#f2e5c6' }); rl.rotation.x = -Math.PI / 2; rl.position.set(0, 0.021, 0.022); rack.add(rl);
  S.contact(0.26, 0.12, RACK.x, RACK.z, 0.5);

  var tubeGlass = new T.MeshPhysicalMaterial({ color: 0xd8ecf2, roughness: 0.08, metalness: 0, transmission: 0.62,
    thickness: 0.003, ior: 1.5, transparent: true, opacity: 0.9 });
  var tubes = BORES.map(function (r, i) {
    var g = new T.Group();
    var body = S.mesh(new T.CylinderGeometry(TUBE_R, TUBE_R, TUBE_L, 20, 1, true), tubeGlass, false);
    body.position.y = TUBE_L / 2; g.add(body);
    var rim = S.mesh(new T.TorusGeometry(TUBE_R, 0.0004, 6, 20), tubeGlass, false); rim.rotation.x = Math.PI / 2; rim.position.y = TUBE_L; g.add(rim);
    var tag = S.label((r * 1000).toFixed(2) + ' mm', { w: 0.026, ratio: 0.3, color: '#1c3a52', bg: '#f3efe2' });
    tag.position.set(0, TUBE_L - 0.022, TUBE_R + 0.0012); g.add(tag);
    g.userData.r = r;
    S.scene.add(g);
    return g;
  });
  function rackSlot(i) { return new T.Vector3(RACK.x - 0.055 + i * 0.055, 0.046, RACK.z); }
  function layFlat(g, i) { g.rotation.set(0, 0, Math.PI / 2); g.position.copy(rackSlot(i)); }
  tubes.forEach(function (g, i) { layFlat(g, i); });
  function standUp(g, y) { g.rotation.set(0, 0, 0); g.position.set(TX, y, TZ); }
  standUp(tubes[0], UP_Y);

  // the liquid column inside the tube in the clamp (drawn thicker than life so it can be seen)
  var colM = new T.MeshStandardMaterial({ color: new T.Color(LQ.col).multiplyScalar(0.55), roughness: 0.25, metalness: 0.0 });
  var column = S.mesh(new T.CylinderGeometry(BORE_DRAWN, BORE_DRAWN, 1, 16), colM, false);
  column.renderOrder = 3; S.scene.add(column);
  var meniscus = S.mesh(new T.SphereGeometry(BORE_DRAWN, 16, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), colM, false);
  meniscus.renderOrder = 3; S.scene.add(meniscus);
  column.visible = false; meniscus.visible = false;                    // nothing inside the tube until it is dipped
  column.position.set(TX, LIQ, TZ); meniscus.position.set(TX, LIQ, TZ);

  // ---------- the pointer whose tip just touches the liquid surface
  var ptr = new T.Group(); S.scene.add(ptr);
  var pfoot = S.rounded(0.05, 0.04, 0.012, 0.003, M.iron); pfoot.rotation.x = -Math.PI / 2; pfoot.position.set(PFX, 0.006, PFZ); ptr.add(pfoot);
  var ppost = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.1, 14), M.chrome); ppost.position.set(PFX, 0.062, PFZ); ptr.add(ppost);
  var parm = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, Math.abs(PTX - PFX), 12), M.chrome);
  parm.rotation.z = Math.PI / 2; parm.position.set((PTX + PFX) / 2, 0.106, PFZ); ptr.add(parm);
  var parm2 = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, Math.abs(PTZ - PFZ), 12), M.chrome);
  parm2.rotation.x = Math.PI / 2; parm2.position.set(PTX, 0.106, (PTZ + PFZ) / 2); ptr.add(parm2);
  var NL = 0.106 - LIQ;
  var needle = S.mesh(new T.ConeGeometry(0.0018, NL, 14), M.steel); needle.rotation.x = Math.PI; needle.position.set(PTX, LIQ + NL / 2, PTZ); ptr.add(needle);
  S.contact(0.08, 0.07, PFX, PFZ, 0.45);

  // ---------- travelling microscope: base, pillar with a millimetre scale, sliding carriage with a vernier
  function mmScaleTex(lenM) {
    var cm = Math.round(lenM * 100), W = 150, Hh = Math.min(8000, cm * 10 * 6 + 40);
    return S.canvasTex(W, Hh, function (x, w, h) {
      x.fillStyle = '#efe9d8'; x.fillRect(0, 0, w, h);
      var k = (h - 24) / (cm * 10);
      x.fillStyle = '#17171a'; x.font = '600 26px "Public Sans", sans-serif'; x.textBaseline = 'middle';
      for (var i = 0; i <= cm * 10; i++) {
        var y = h - 12 - i * k, big = i % 10 === 0, mid = i % 5 === 0;
        x.fillRect(0, y - (big ? 1.4 : 0.8), big ? w * 0.42 : mid ? w * 0.3 : w * 0.18, big ? 2.8 : 1.6);
        if (big) x.fillText(String(i / 10), w * 0.5, y);
      }
      x.save(); x.translate(w * 0.9, h - 20); x.rotate(-Math.PI / 2);
      x.fillStyle = '#6b4a14'; x.font = '600 20px "Public Sans", sans-serif'; x.fillText('cm', 0, 0); x.restore();
    });
  }
  var micro = new T.Group(); S.scene.add(micro);
  var mbase = S.rounded(0.12, 0.1, 0.022, 0.006, M.iron); mbase.rotation.x = -Math.PI / 2; mbase.position.set(MX, 0.011, MZ); micro.add(mbase);
  [[-0.04, -0.03], [0.04, -0.03], [0, 0.035]].forEach(function (f) {
    var lv = S.mesh(new T.CylinderGeometry(0.006, 0.007, 0.006, 16), M.iron); lv.position.set(MX + f[0], 0.002, MZ + f[1]); micro.add(lv);
  });
  var pillar = S.rounded(0.028, PIL_H, 0.022, 0.004, M.iron); pillar.position.set(MX, 0.022 + PIL_H / 2, MZ); micro.add(pillar);
  var scPlate = new T.Mesh(new T.PlaneGeometry(0.013, SC_LEN), new T.MeshStandardMaterial({ map: mmScaleTex(SC_LEN), roughness: 0.5 }));
  scPlate.position.set(MX - 0.0045, SC_Y0 + SC_LEN / 2, MZ + 0.0112); micro.add(scPlate);
  var mlbl = S.label('TRAVELLING MICROSCOPE  ·  V.C. 0.001 cm', { w: 0.1, ratio: 0.12, color: '#e8e8ea' });
  mlbl.rotation.x = -Math.PI / 2; mlbl.position.set(MX, 0.0231, MZ + 0.036); micro.add(mlbl);

  var carr = new T.Group(); S.scene.add(carr);
  var cbody = S.rounded(0.05, 0.05, 0.03, 0.005, M.brass); cbody.position.set(0, 0, -0.028); carr.add(cbody);
  var carm = S.mesh(new T.BoxGeometry(0.012, 0.016, 0.062), M.brass); carm.position.set(-0.026, 0, -0.004); carr.add(carm);
  var vTex = S.canvasTex(96, 256, function (x, w, h) {
    x.fillStyle = '#d9b154'; x.fillRect(0, 0, w, h); x.fillStyle = '#2a1e06'; x.font = '600 22px "Public Sans", sans-serif'; x.textBaseline = 'middle';
    for (var i = 0; i <= 10; i++) { var y = h - 14 - i * (h - 28) / 10; x.fillRect(0, y - 1, i % 5 === 0 ? w * 0.46 : w * 0.3, 2); if (i % 5 === 0) x.fillText(String(i), w * 0.55, y); }
  });
  var vPlate = new T.Mesh(new T.PlaneGeometry(0.009, 0.026), new T.MeshStandardMaterial({ map: vTex, roughness: 0.4 }));
  vPlate.position.set(-0.0185, 0, 0.0122); carr.add(vPlate);
  var idxLine = S.mesh(new T.BoxGeometry(0.02, 0.0012, 0.0012), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }), false);
  idxLine.position.set(-0.0205, 0, 0.0134); carr.add(idxLine);
  var mtube = S.mesh(new T.CylinderGeometry(0.0135, 0.0115, 0.1, 26), M.black); mtube.rotation.z = Math.PI / 2; mtube.position.set(-0.085, 0, 0.004); carr.add(mtube);
  var eye = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.02, 20), M.bakelite); eye.rotation.z = Math.PI / 2; eye.position.set(-0.025, 0, 0.004); carr.add(eye);
  var obj = S.mesh(new T.CylinderGeometry(0.009, 0.007, 0.016, 20), M.chrome); obj.rotation.z = Math.PI / 2; obj.position.set(-0.142, 0, 0.004); carr.add(obj);
  var fknob = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 18), M.black); fknob.rotation.x = Math.PI / 2; fknob.position.set(-0.026, -0.022, 0.03); carr.add(fknob);
  var cclamp = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.008, 12), M.chrome); cclamp.rotation.x = Math.PI / 2; cclamp.position.set(0.02, 0.018, -0.012); carr.add(cclamp);
  function placeCarr() { carr.position.set(MX, st.carr, MZ); }
  placeCarr();

  S.addApparatus('trough', trough, 'Glass trough with ' + LQ.name,
    'The liquid whose surface tension you measure. The tube dips into it and a pointer tip just touches its surface.');
  S.addApparatus('stand', stand, 'Retort stand with clamp', 'Holds the capillary tube upright, with its lower end in the liquid.');
  S.addApparatus('tube', tubes[0], 'Capillary tube', 'A fine glass tube of bore radius r. The column inside is drawn thicker than life so you can see it.');
  S.addApparatus('rack', rack, 'Tubes of other bores', 'Three clean tubes, each with its bore radius printed on it.');
  S.addApparatus('ptr', ptr, 'Pointer', 'A steel needle whose tip is set exactly at the liquid surface, so the microscope can read that level.');
  S.addApparatus('micro', micro, 'Travelling microscope', 'A microscope on a carriage that slides along a millimetre scale. Its vernier reads to 0.001 cm.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudB = S.hudCard('Bore radius r'), hudH = S.hudCard('Rise h'), hudR = S.hudCard('Microscope reads');

  // ---------- actions
  function moveCarr(targetY, ms) {
    var y0 = st.carr, y1 = Math.max(SC_Y0 + 0.004, Math.min(SC_Y0 + SC_LEN - 0.01, targetY));
    var grip = new T.Vector3(MX - 0.026, 0, MZ + 0.034);
    function at(k) { return new T.Vector3(grip.x, y0 + (y1 - y0) * k, grip.z); }
    return S.hand.pinchMove(at(0), at, function (k) { st.carr = y0 + (y1 - y0) * k; placeCarr(); }, { ms: ms || 1100, mode: 'front' })
      .then(function () { st.carr = y1; placeCarr(); });
  }
  function dipTube() {
    if (S.hand.busy) return Promise.resolve();
    if (st.dipped) { S.say('The tube is already dipping in the liquid.'); return Promise.resolve(); }
    var g = tubes[st.idx], y0 = g.position.y, y1 = LIQ - DIP;
    var grip = new T.Vector3(TX + TUBE_R + 0.004, 0, TZ);
    return S.hand.pinchMove(new T.Vector3(grip.x, y0 + TUBE_L * 0.62, grip.z),
      function (k) { return new T.Vector3(grip.x, y0 + (y1 - y0) * k + TUBE_L * 0.62, grip.z); },
      function (k) { g.position.y = y0 + (y1 - y0) * k; }, { ms: 1200 })
      .then(function () {
        g.position.y = y1; st.dipped = true; st.raised = false; sim = K.init(p); sim.h = 0;
        S.say('The tube dips ' + Math.round(DIP * 1000) + ' mm into the ' + LQ.name + '. Watch the liquid climb inside it, then wait until the meniscus stops moving.');
        S.render();
      });
  }
  function focusMeniscus() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.dipped) { S.say('Dip the tube in the liquid first.'); return Promise.resolve(); }
    if (!settled()) { S.say('The meniscus is still rising. Wait until it stands still, then focus on it.'); return Promise.resolve(); }
    return moveCarr(menY()).then(function () {
      st.r1 = reading();
      S.say('Cross-wire on the lowest point of the meniscus: the microscope reads ' + st.r1.toFixed(3) + ' cm.');
      S.render();
    });
  }
  function focusSurface() {
    if (S.hand.busy) return Promise.resolve();
    if (st.r1 === null) { S.say('Read the meniscus first.'); return Promise.resolve(); }
    return moveCarr(LIQ).then(function () {
      st.r2 = reading();
      S.say('Cross-wire on the pointer tip, which sits at the liquid surface: ' + st.r2.toFixed(3) + ' cm.');
      S.render();
    });
  }
  function recordH() {
    if (S.hand.busy) return;
    if (st.r1 === null || st.r2 === null) { S.say('Take both readings: the meniscus and the liquid surface.'); return; }
    var hcm = Math.round((st.r1 - st.r2) * 1000) / 1000;
    if (hcm <= 0) { S.say('The meniscus must read higher than the surface. Focus on both again.'); return; }
    if (S.rows.some(function (row) { return Math.abs(row.r - p.r) < 1e-9; })) { S.say('This tube is already in the table. Change the tube first.'); return; }
    S.addRow({ r: p.r, h: hcm / 100, r1: st.r1, r2: st.r2 });
    st.r1 = null; st.r2 = null;
    S.say('Written in your record book: bore ' + (p.r * 1000).toFixed(2) + ' mm, rise ' + hcm.toFixed(3) + ' cm.');
  }
  function changeTube(i) {
    if (S.hand.busy) return Promise.resolve();
    if (i === st.idx) { S.say('That tube is already in the clamp.'); return Promise.resolve(); }
    var out = tubes[st.idx], into = tubes[i], slot = rackSlot(st.idx);
    var gy = out.position.y + TUBE_L * 0.62, lift = new T.Vector3(TX + TUBE_R + 0.004, 0, TZ);
    var pr = S.hand.pinchMove(new T.Vector3(lift.x, gy, lift.z),
      function (k) { return new T.Vector3(lift.x + (slot.x - TX) * k, gy + 0.04 * Math.sin(Math.PI * k) - (gy - slot.y - 0.01) * k, lift.z + (slot.z - TZ) * k); },
      function (k) {
        out.position.set(TX + (slot.x - TX) * k, out.position.y + (slot.y - out.position.y) * k, TZ + (slot.z - TZ) * k);
        out.rotation.z = (Math.PI / 2) * k;
      }, { ms: 1300 });
    return pr.then(function () {
      layFlat(out, st.idx); st.dipped = false; st.raised = true; st.r1 = null; st.r2 = null;
      var from = rackSlot(i);
      return S.hand.pinchMove(new T.Vector3(from.x, from.y + 0.02, from.z),
        function (k) { return new T.Vector3(from.x + (TX + TUBE_R + 0.004 - from.x) * k, from.y + 0.02 + (UP_Y + TUBE_L * 0.62 - from.y - 0.02) * k, from.z + (TZ - from.z) * k); },
        function (k) {
          into.position.set(from.x + (TX - from.x) * k, from.y + (UP_Y - from.y) * k, from.z + (TZ - from.z) * k);
          into.rotation.z = (Math.PI / 2) * (1 - k);
        }, { ms: 1300 });
    }).then(function () {
      standUp(into, UP_Y); st.idx = i; st.swapped++;
      p.r = into.userData.r; sim = K.init(p); sim.h = 0;
      S.say('Tube of bore ' + (p.r * 1000).toFixed(2) + ' mm is in the clamp. Dip it and measure the rise again.');
      S.render();
    });
  }

  function fmtT(v) { return (v * 1000).toFixed(1); }
  var CALC = HK.CALCS.cap_T;

  return {
    camera: { pos: [0.4, 0.3, 0.46], look: [0.07, 0.12, -0.08] },
    views: {
      rig: [[0.34, 0.28, 0.42], [0.04, 0.12, -0.09]],
      trough: [[0.12, 0.16, 0.14], [TX, LIQ, TZ]],
      stand: [[0.2, 0.42, 0.5], [-0.06, 0.24, TZ]],
      tube: [[0.14, LIQ + 0.07, 0.2], [TX, LIQ + 0.05, TZ]],
      rack: [[0.42, 0.2, 0.34], [RACK.x, 0.03, RACK.z]],
      ptr: [[0.08, 0.16, 0.14], [PTX, LIQ + 0.02, PTZ]],
      micro: [[0.42, 0.3, 0.34], [MX - 0.03, 0.18, MZ]],
      read: [[0.22, LIQ + 0.2, 0.46], [0.09, LIQ + 0.04, TZ]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]]
    },
    theory: {
      principle: 'A liquid that wets glass climbs a fine tube. All round the circle where the liquid meets the glass, '
        + 'surface tension pulls the liquid up with a force 2πrT cosθ; the weight of the raised column, πr²hρg, pulls it '
        + 'down. The liquid stops rising when the two are equal.',
      formula: 'h = 2 T cosθ / (r ρ g)', formulaNote: 'so T = h r ρ g / 2 cosθ · for a liquid that wets glass θ ≈ 0, cosθ ≈ 1',
      more: ['A narrower bore gives a higher rise: h is inversely proportional to r, so the graph of h against 1/r is a '
        + 'straight line through the origin with slope 2T/(ρg).',
        'Every height is read with the travelling microscope: the lowest point of the meniscus first, then the pointer tip '
        + 'at the liquid surface. The rise h is the difference of the two readings.'],
      precautions: 'The tube and the trough must be clean: the smallest trace of grease changes the angle of contact. Keep '
        + 'the tube vertical, keep the pointer tip exactly at the surface, and read the lowest point of the meniscus with '
        + 'your eye in line with it.'
    },
    book: {
      title: 'Expt. — Surface Tension by Capillary Rise',
      lines: ['Aim: surface tension T of ' + LQ.name + ' by capillary rise.',
        'Density ρ = ' + p.rho.toFixed(1) + ' kg/m³,  g = ' + (+p.g.toFixed(2)) + ' m/s²',
        'Angle of contact θ = ' + Math.round(p.theta * 180 / Math.PI) + '°  (the liquid wets glass)',
        'Travelling microscope, vernier constant 0.001 cm',
        'h = meniscus reading − surface reading', 'T = h r ρ g / 2',
        'Precautions: clean tube, vertical tube, no parallax.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Bore r (mm)', get: function (r) { return (r.r * 1000).toFixed(2); } },
        { label: 'Meniscus (cm)', get: function (r) { return r.r1.toFixed(3); } },
        { label: 'Surface (cm)', get: function (r) { return r.r2.toFixed(3); } },
        { label: 'Rise h (cm)', get: function (r) { return (r.h * 100).toFixed(3); } },
        { label: 'T (mN/m)', get: function (r) { return fmtT(r.h * r.r * p.rho * p.g / 2); } }]
    },
    graph: {
      x: function (r) { return 1 / r.r; }, y: function (r) { return r.h; },
      xlabel: '1 / r (per metre)', ylabel: 'Rise h (m)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; }
    },
    result: function (rows) {
      if (!rows.length) return null;
      return { label: 'T (surface tension)', value: CALC.fn(rows, p), unit: 'N/m', digits: 4, truth: p.T,
        note: 'Mean of T = h r ρ g / 2 over the tubes measured.' };
    },
    resultNote: 'In a real lab a trace of grease, or a tube that is not quite vertical, makes the rise a little small, so '
      + 'T comes out a little low.',
    tol: 0.02,
    chips: ['Why does a narrow tube lift the liquid higher?', 'Why must the tube be clean?', 'What is the angle of contact?',
      'Check my readings', 'Why is my T different from the table value?'],
    viva: [['Why is the rise measured to the LOWEST point of the meniscus?',
      ['Because the formula uses the level of the flat liquid surface it is compared with', 'Because it is easier to see',
        'Because the top of the meniscus is dry'], 0,
      'The column whose weight is being balanced is measured from the liquid surface to the bottom of the curved meniscus.'],
      ['If the same tube is used with a liquid of lower surface tension, the rise is',
        ['Smaller', 'Larger', 'Unchanged'], 0, 'h is proportional to T.']],
    askState: function () {
      return { liquid: LQ.name, bore_radius_mm: +(p.r * 1000).toFixed(3), tube_dipped: st.dipped,
        meniscus_settled: settled(), rise_now_cm: +(sim.h * 100).toFixed(3),
        microscope_reading_cm: reading(), meniscus_reading_cm: st.r1, surface_reading_cm: st.r2,
        tubes_measured: S.rows.length, tubes_available_mm: BORES.map(function (r) { return +(r * 1000).toFixed(2); }) };
    },

    steps: [
      { id: 'dip', title: 'Dip the tube', view: 'rig', render: function (u) {
          u.h2('Dip the capillary tube in the liquid');
          u.p('The tube of bore ' + (p.r * 1000).toFixed(2) + ' mm hangs in the clamp just above the ' + LQ.name
            + '. Lower it until its end is well under the surface, then let the meniscus settle.');
          u.task('1. Lower the tube into the liquid', st.dipped, st.dipped ? 'Dipping ' + Math.round(DIP * 1000) + ' mm under the surface' : 'The end must stay under the surface')
            .add(u.button(st.dipped ? 'Dipped' : 'Lower the tube', function () { S.focus('tube'); dipTube(); }, !st.dipped, S.hand.busy || st.dipped));
          u.task('2. Wait for the meniscus to stand still', st.dipped && settled(), st.dipped ? (settled() ? 'Settled' : 'Still rising') : 'After the tube is dipped');
          u.live(function () { return 'Rise inside the tube: ' + (st.dipped ? (sim.h * 100).toFixed(3) + ' cm' : '—') + (st.dipped && settled() ? ' · settled' : ''); });
          u.note('The pointer beside the tube has its tip exactly at the liquid surface. That is the level the rise is measured from.');
          u.next('Next: read the heights', st.dipped && settled());
        },
        ok: function () { return st.dipped && settled(); },
        auto: function () { return dipTube().then(function () { S.advance(60, settled); }); } },

      { id: 'read', title: 'Measure the rise', view: 'read', render: function (u) {
          u.h2('Read the meniscus and the surface');
          u.p('Slide the microscope carriage until the cross-wire sits on the lowest point of the meniscus and read the '
            + 'scale; then bring it down to the pointer tip at the liquid surface and read again. The difference is h.');
          u.task('1. Focus on the meniscus', st.r1 !== null, st.r1 !== null ? 'Reading ' + st.r1.toFixed(3) + ' cm' : 'The lowest point of the curve')
            .add(u.button('Focus on the meniscus', function () { focusMeniscus(); }, st.r1 === null, S.hand.busy || !st.dipped));
          u.task('2. Focus on the liquid surface', st.r2 !== null, st.r2 !== null ? 'Reading ' + st.r2.toFixed(3) + ' cm' : 'On the pointer tip')
            .add(u.button('Focus on the pointer tip', function () { focusSurface(); }, st.r1 !== null && st.r2 === null, S.hand.busy || st.r1 === null));
          u.row(u.button('Record h', recordH, st.r1 !== null && st.r2 !== null, S.hand.busy || st.r1 === null || st.r2 === null));
          u.live(function () { return 'Microscope reads ' + reading().toFixed(3) + ' cm' + (st.r1 !== null && st.r2 !== null ? ' · h = ' + (st.r1 - st.r2).toFixed(3) + ' cm' : ''); });
          u.h3('Observation table'); u.table();
          u.next('Next: other bores', S.rows.length >= 1);
        },
        ok: function () { return S.rows.length >= 1; },
        auto: function () { return focusMeniscus().then(focusSurface).then(function () { recordH(); }); } },

      { id: 'tubes', title: 'Other bores', view: 'rig', render: function (u) {
          u.h2('Repeat with tubes of other bore');
          u.p('A narrower tube should lift the liquid higher. Put each of the other tubes in the clamp, dip it, and measure '
            + 'its rise the same way.');
          var rowB = u.row();
          BORES.forEach(function (r, i) {
            rowB.appendChild(u.button((i === st.idx ? '✓ ' : '') + (r * 1000).toFixed(2) + ' mm',
              function () { changeTube(i); }, false, S.hand.busy || i === st.idx));
          });
          u.row(u.button('Lower the tube', function () { dipTube(); }, !st.dipped, S.hand.busy || st.dipped),
            u.button('Focus on the meniscus', function () { focusMeniscus(); }, false, S.hand.busy || !st.dipped),
            u.button('Focus on the pointer tip', function () { focusSurface(); }, false, S.hand.busy || st.r1 === null),
            u.button('Record h', recordH, true, S.hand.busy || st.r1 === null || st.r2 === null));
          u.live(function () { return 'Tube ' + (p.r * 1000).toFixed(2) + ' mm · rise ' + (st.dipped ? (sim.h * 100).toFixed(3) + ' cm' : '—') + (st.dipped && !settled() ? ' · rising' : ''); });
          u.h3('Observation table'); u.table();
          if (S.rows.length < 3) u.p(S.rows.length + ' of 3 tubes measured.');
          u.next('Next: the graph and T', S.rows.length >= 3);
        },
        ok: function () { return S.rows.length >= 3; },
        auto: function () {
          var pr = Promise.resolve();
          [1, 2].forEach(function (i) {
            pr = pr.then(function () { return changeTube(i); })
              .then(function () { return dipTube(); })
              .then(function () { S.advance(60, settled); return focusMeniscus(); })
              .then(focusSurface).then(function () { recordH(); });
          });
          return pr;
        } }
    ],

    tick: function (dt) {
      if (st.dipped) K.step(sim, p, dt);
      var g = tubes[st.idx];
      var base = st.dipped ? LIQ : g.position.y + 0.004, top = st.dipped ? menY() : base;
      var len = Math.max(0.0008, top - (st.dipped ? g.position.y + 0.002 : base));
      column.visible = st.dipped;
      meniscus.visible = st.dipped;
      if (st.dipped) {
        column.scale.y = len; column.position.set(TX, g.position.y + 0.002 + len / 2, TZ);
        meniscus.position.set(TX, top, TZ);
      }
      hudB.set((p.r * 1000).toFixed(2) + ' mm');
      hudH.set(st.dipped ? (sim.h * 100).toFixed(3) + ' cm' : '—');
      hudR.set(reading().toFixed(3) + ' cm');
    }
  };
});
