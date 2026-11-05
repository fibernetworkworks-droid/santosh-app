/* Prayogshala studio rig: the magnetic effect of a current (NCERT Science VII / X).
   One bench - low-voltage supply, plug key, rheostat and ammeter in series - feeds whichever conductor the lab asks
   for: a long straight wire over a plotting compass (Oersted), a circular coil, a 30 cm solenoid, or a coil wound on
   an iron nail. Small fields are read as the deflection of the compass (tan(theta) = B / B_H), larger ones with a
   Hall teslameter. Every number comes from the `coilfield` kernel of packs/em_school.js - the Biot-Savart sum the
   server checks against the textbook formula. */
HoolaStudio.define('current-magnetism', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.coilfield;
  var p = HK.paramsFor('coilfield', S.lab.params);
  var V_ = S.lab.variant || {}, BASE = V_.base || S.lab.id, SAMPLE = V_.sample || '';
  var KIND = p.kind < 0.5 ? 'wire' : p.kind < 1.5 ? 'coil' : 'sol';
  var CORE = BASE === 'electromagnet-nail';                      // the lab that measures what the iron does
  var COMPASS = KIND === 'wire';                                 // small fields: read the compass
  var D0 = p.d, RS0 = p.Rs, MUR0 = p.mur, BH = p.BH;
  var RS_MIN = 1.0, RS_MAX = Math.max(12, RS0 * 4);
  var st = { key: false, rs: RS0, d: D0, rev: p.rev >= 0 ? 1 : -1, core: true, traced: false, zero: false,
    filings: false, probeIn: !COMPASS, target: RS0 };
  var sim = KC.init(p), B = 0, Ical = 0, needle = 0;

  function solve() {
    p.key = st.key ? 1 : 0; p.Rs = st.rs; p.d = st.d; p.rev = st.rev;
    p.mur = CORE ? (st.core ? MUR0 : 1.0) : MUR0;
    var v = KC.view(sim, p);
    Ical = Math.abs(v.I); B = v.B;
    needle = v.theta;                                    // the compass is always on the card; only the Hall probe can be out
  }
  var I0 = Math.abs(p.Eb) / RS0;                         // the current the set-up is designed for
  function pick(list, need) { for (var i = 0; i < list.length; i++) if (list[i] >= need - 1e-9) return list[i]; return list[list.length - 1]; }
  var AMAX = pick([0.5, 1, 1.5, 2, 3, 5], I0 * 1.25), ARES = AMAX / 100;
  function fI(v) { return (Math.round(v / ARES) * ARES).toFixed(2); }
  function fmtN(v, d) { return String(+v.toFixed(d === undefined ? 2 : d)); }
  // what the instruments can really resolve
  function degRead() { return Math.round(Math.abs(needle) * 180 / Math.PI / 0.5) * 0.5; }
  function teslaRes() { return Math.abs(B) < 0.002 ? 1e-6 : 1e-4; }
  function teslaRead() { var r = teslaRes(); return Math.round(Math.abs(B) / r) * r; }
  function teslaTxt() { var r = teslaRes(); return r < 1e-5 ? (teslaRead() * 1000).toFixed(3) + ' mT' : (teslaRead() * 1000).toFixed(1) + ' mT'; }
  // the textbook field per ampere at this geometry: the pack's own formula, not the kernel's sum
  function perAmp(dist, mur) {
    var q = HK.assign(p, { Eb: 1, Rs: 1, key: 1, d: dist === undefined ? D0 : dist, mur: mur === undefined ? p.mur : mur });
    return HK.TEXTBOOK.cfield_B(q);
  }

  // ---------- helpers
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }

  // ---------- supply, key, rheostat, ammeter (the same series circuit for every lab)
  var PB = [-0.56, -0.22];
  var pb = S.powerBox([PB[0], 0, PB[1]], 'DC SUPPLY');
  var pbV = S.label(fmtN(p.Eb, 1) + ' V DC', { w: 0.05, ratio: 0.3, color: '#f2f2f2' });
  pbV.position.set(PB[0] + 0.045, 0.034, PB[1] + 0.0405); S.scene.add(pbV);
  var pbPlus = { at: new T.Vector3(PB[0] + 0.04, 0.109, PB[1]) }, pbMinus = { at: new T.Vector3(PB[0] - 0.04, 0.109, PB[1]) };

  var KP = [-0.42, -0.04];
  var key = S.plugKey([KP[0], 0, KP[1]]), plug = key.userData.plug;
  var kLbl = S.label('K', { w: 0.013, ratio: 1, color: '#f0e6c8' }); kLbl.rotation.x = -Math.PI / 2; kLbl.position.set(KP[0], 0.0175, KP[1] + 0.016); S.scene.add(kLbl);
  var kL = post(KP[0] - 0.042, 0.0, KP[1] - 0.04, 'red'), kR = post(KP[0] + 0.042, 0.0, KP[1] - 0.04, 'black');
  var ZAX = new T.Vector3(0, 0, 1);
  function plugPose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
  function plugApply(k) { var q = plugPose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
  function plugHead(k) { var q = plugPose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
  plugApply(0);
  function setKey(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.key) return Promise.resolve();
    var a = st.key ? 1 : 0, b = on ? 1 : 0;
    if (!on) { st.key = false; solve(); }
    return S.hand.pinchMove(plugHead(a), function (k) { return plugHead(a + (b - a) * k); }, function (k) { plugApply(a + (b - a) * k); },
      { ms: 850, mode: 'top' }).then(function () {
        plugApply(b); st.key = !!on; solve(); S.click(1500, 0.04, 0.09);
        S.say(on ? 'Key closed: ' + fI(Ical) + ' A flows, and the ' + (COMPASS ? 'compass needle swings off north' : 'teslameter reads the field') + '.'
          : 'Key open: no current, so the field goes with it.');
        S.render();
      });
  }

  var RHP = [-0.14, 0.02], RH_LEN = 0.26;
  var rh = S.rheostat([RHP[0], 0, RHP[1]], RH_LEN);
  var rhA = post(RHP[0] - RH_LEN / 2 - 0.01, 0.05, RHP[1], 'red'), rhC = post(RHP[0] + RH_LEN / 2 - 0.006, 0.065, RHP[1], 'black');
  var rhPlate = S.label('RHEOSTAT', { w: 0.06, ratio: 0.17, color: '#f3ead2', bg: '#2b2b2b' });
  rhPlate.position.set(RHP[0] + RH_LEN / 2 - 0.03, 0.025, RHP[1] + 0.0105); S.scene.add(rhPlate);
  function rsToF(r) { return (RS_MAX - r) / (RS_MAX - RS_MIN); }                 // contact near A = less resistance
  function sliderTop(f) { return rh.localToWorld(new T.Vector3(-RH_LEN / 2 + 0.02 + f * (RH_LEN - 0.04), 0.074, 0)); }
  function setRs(r) { st.rs = Math.max(RS_MIN, Math.min(RS_MAX, r)); rh.setFraction(rsToF(st.rs)); solve(); }
  setRs(RS0);
  function slide(target) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    target = Math.max(RS_MIN, Math.min(RS_MAX, target)); st.target = target;
    var r0 = st.rs; if (Math.abs(target - r0) < 1e-9) return Promise.resolve();
    return S.hand.pinchMove(sliderTop(rsToF(r0)), function (k) { return sliderTop(rsToF(r0 + (target - r0) * k)); },
      function (k) { setRs(r0 + (target - r0) * k); }, { ms: 600 + Math.abs(rsToF(target) - rsToF(r0)) * 1200, mode: 'top' })
      .then(function () { setRs(target); S.render(); });
  }

  var am = S.meter({ min: 0, max: AMAX, ticks: AMAX === 0.5 ? 5 : AMAX === 1 ? 10 : AMAX === 1.5 ? 6 : 5, unit: 'A', symbol: 'A',
    caption: 'DC AMMETER 0–' + fmtN(AMAX) + ' A', pos: [-0.4, 0, -0.44] });
  var amP = { at: wpt(am, 0.035, 0.07, -0.03) }, amM = { at: wpt(am, -0.035, 0.07, -0.03) };

  // ---------- the working table: a card on a wooden stage, with the conductor over it
  var WX = 0.36, WZ = -0.26;
  var stage = S.rounded(0.44, 0.34, 0.014, 0.006, M.darkWood); stage.rotation.x = -Math.PI / 2; stage.position.set(WX, 0.007, WZ); S.scene.add(stage);
  S.contact(0.5, 0.4, WX, WZ, 0.45);
  var cardTex = S.canvasTex(1024, 768, function (x, w, h) {
    x.fillStyle = '#f7f3e6'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(60,70,90,.25)'; x.lineWidth = 2;
    for (var i = 1; i < 10; i++) { x.beginPath(); x.moveTo(i * w / 10, 0); x.lineTo(i * w / 10, h); x.stroke(); }
    for (var j = 1; j < 8; j++) { x.beginPath(); x.moveTo(0, j * h / 8); x.lineTo(w, j * h / 8); x.stroke(); }
    x.fillStyle = '#2b3a55'; x.font = '700 40px "Public Sans", sans-serif'; x.textAlign = 'center';
    x.fillText('N', w / 2, 52); x.fillText('S', w / 2, h - 18);
    x.textAlign = 'left'; x.fillText('W', 16, h / 2 + 14); x.textAlign = 'right'; x.fillText('E', w - 16, h / 2 + 14);
  });
  var card = new T.Mesh(new T.PlaneGeometry(0.4, 0.3), new T.MeshStandardMaterial({ map: cardTex, roughness: 0.8 }));
  card.rotation.x = -Math.PI / 2; card.position.set(WX, 0.0145, WZ); S.scene.add(card);

  // iron filings (hidden until they are sprinkled): rings round a wire, a bar-magnet pattern for the solenoid
  var filG = new T.Group(); filG.visible = false; S.scene.add(filG); filG.position.set(WX, 0.0152, WZ);
  (function () {
    var fm = new T.MeshStandardMaterial({ color: 0x3a3c40, roughness: 0.6, metalness: 0.7 });
    var n = 0;
    for (var ring = 1; ring <= 5 && n < 260; ring++) {
      var rr = 0.014 * ring, cnt = 10 + ring * 5;
      for (var k = 0; k < cnt && n < 260; k++) {
        var a = (k / cnt) * Math.PI * 2 + ring * 0.2;
        var fx = Math.cos(a) * rr, fz = Math.sin(a) * rr;
        if (KIND !== 'wire') { fx *= 1.9; }                                   // stretched along the solenoid's axis
        if (Math.abs(fx) > 0.19 || Math.abs(fz) > 0.14) continue;
        var fl = S.mesh(new T.BoxGeometry(0.0055, 0.0006, 0.0011), fm, false);
        fl.position.set(fx, 0, fz); fl.rotation.y = -a + Math.PI / 2; filG.add(fl); n++;
      }
    }
  })();

  // ---------- the conductor itself
  var src = new T.Group(); S.scene.add(src);
  var cu = new T.MeshStandardMaterial({ color: 0xc8703a, roughness: 0.25, metalness: 0.9 });
  var srcP, srcM;
  if (KIND === 'wire') {
    var WL = Math.min(0.42, p.wireL);                                        // the part of the wire over the card
    var bar = S.mesh(new T.CylinderGeometry(0.0013, 0.0013, WL, 14), cu); bar.rotation.x = Math.PI / 2; bar.position.set(WX, 0.0145 + D0, WZ); src.add(bar);
    [-1, 1].forEach(function (s) {
      var h = 0.0145 + D0, pst = S.mesh(new T.CylinderGeometry(0.004, 0.005, h, 16), M.bakelite);
      pst.position.set(WX, h / 2 + 0.0075, WZ + s * (WL / 2 - 0.012)); src.add(pst);
      var cl = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.006, 16), M.brass); cl.position.set(WX, 0.0145 + D0, WZ + s * (WL / 2 - 0.012)); src.add(cl);
    });
    srcP = post(WX + 0.035, 0.0145, WZ - WL / 2 + 0.004, 'red'); srcM = post(WX - 0.035, 0.0145, WZ + WL / 2 - 0.004, 'black');
    src.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new T.Vector3(WX, 0.0145 + D0, WZ - WL / 2),
      new T.Vector3(WX + 0.02, 0.0145 + D0 * 0.6, WZ - WL / 2 - 0.01), new T.Vector3(srcP.at.x, 0.016, srcP.at.z)]), 20, 0.0013, 6, false), cu));
    src.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new T.Vector3(WX, 0.0145 + D0, WZ + WL / 2),
      new T.Vector3(WX - 0.02, 0.0145 + D0 * 0.6, WZ + WL / 2 + 0.01), new T.Vector3(srcM.at.x, 0.016, srcM.at.z)]), 20, 0.0013, 6, false), cu));
  } else if (KIND === 'coil') {
    var A = p.a, NT = Math.max(1, Math.round(p.N));
    var fmr = new T.MeshStandardMaterial({ color: 0xf1e7cc, roughness: 0.45, side: T.DoubleSide });
    var ring = S.mesh(new T.TorusGeometry(A, 0.006, 10, 60), fmr); ring.position.set(WX, 0.0145 + A + 0.012, WZ); src.add(ring);
    var stalk = S.mesh(new T.CylinderGeometry(0.006, 0.008, A + 0.012, 14), M.bakelite); stalk.position.set(WX, 0.0145 + (A + 0.012) / 2, WZ); src.add(stalk);
    // the turns wind round the coil's axis, which points along z (the probe comes in along it)
    var hel = new T.Curve(); hel.getPoint = function (t, tgt) {
      var a = t * NT * Math.PI * 2, off = (t - 0.5) * 0.0035 * NT;
      return (tgt || new T.Vector3()).set(Math.cos(a) * (A + 0.0068), Math.sin(a) * (A + 0.0068), off);
    };
    var wind = S.mesh(new T.TubeGeometry(hel, NT * 28, 0.0011, 6, false), cu); wind.position.set(WX, 0.0145 + A + 0.012, WZ); src.add(wind);
    srcP = post(WX + 0.08, 0.0145, WZ + 0.05, 'red'); srcM = post(WX - 0.08, 0.0145, WZ + 0.05, 'black');
    [[-1, srcM], [1, srcP]].forEach(function (q) {
      src.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new T.Vector3(WX, 0.0145 + 0.012 - 0.0068, WZ + q[0] * 0.0035 * NT / 2),
        new T.Vector3(WX + q[0] * 0.04, 0.03, WZ + 0.02), new T.Vector3(q[1].at.x, 0.016, q[1].at.z)]), 20, 0.0011, 6, false), cu));
    });
  } else {
    var LS = CORE ? p.Lsol : Math.min(0.34, p.Lsol), AS = Math.max(0.006, p.a);
    var tube = S.mesh(new T.CylinderGeometry(AS + 0.001, AS + 0.001, LS, 28, 1, true), new T.MeshStandardMaterial({ color: 0xf1e7cc, roughness: 0.5, side: T.DoubleSide }));
    tube.rotation.z = Math.PI / 2; tube.position.set(WX, 0.0145 + AS + 0.03, WZ); src.add(tube);
    if (CORE) {
      var nail = S.mesh(new T.CylinderGeometry(AS * 0.8, AS * 0.8, LS + 0.03, 20), new T.MeshStandardMaterial({ color: 0x6e7276, roughness: 0.4, metalness: 0.85 }));
      nail.rotation.z = Math.PI / 2; nail.position.set(WX, 0.0145 + AS + 0.03, WZ); src.add(nail); src.userData.nail = nail;
      var tip = S.mesh(new T.ConeGeometry(AS * 0.8, 0.014, 18), new T.MeshStandardMaterial({ color: 0x6e7276, roughness: 0.4, metalness: 0.85 }));
      tip.rotation.z = -Math.PI / 2; tip.position.set(WX + LS / 2 + 0.022, 0.0145 + AS + 0.03, WZ); src.add(tip); src.userData.tip = tip;
    }
    var turns = Math.max(8, Math.min(90, Math.round(p.nsol * LS)));
    var hel2 = new T.Curve(); hel2.getPoint = function (t, tgt) {
      var a = t * turns * Math.PI * 2;
      return (tgt || new T.Vector3()).set(-LS / 2 + t * LS, Math.cos(a) * (AS + 0.0026), Math.sin(a) * (AS + 0.0026));
    };
    var w2 = S.mesh(new T.TubeGeometry(hel2, turns * 16, 0.0012, 6, false), cu); w2.position.set(WX, 0.0145 + AS + 0.03, WZ); src.add(w2);
    [-1, 1].forEach(function (s) {
      var stp = S.mesh(new T.CylinderGeometry(0.005, 0.007, AS + 0.03, 14), M.bakelite); stp.position.set(WX + s * (LS / 2 - 0.01), 0.0145 + (AS + 0.03) / 2, WZ); src.add(stp);
    });
    srcP = post(WX + LS / 2 + 0.03, 0.0145, WZ + 0.08, 'red'); srcM = post(WX - LS / 2 - 0.03, 0.0145, WZ + 0.08, 'black');
    [[-1, srcM], [1, srcP]].forEach(function (q) {
      src.add(S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3([new T.Vector3(WX + q[0] * LS / 2, 0.0145 + AS + 0.03, WZ),
        new T.Vector3(WX + q[0] * (LS / 2 + 0.02), 0.03, WZ + 0.04), new T.Vector3(q[1].at.x, 0.016, q[1].at.z)]), 20, 0.0012, 6, false), cu));
    });
  }

  // ---------- plotting compass (small fields) and Hall teslameter (larger ones)
  var comp = new T.Group(); S.scene.add(comp);
  var cbody = S.mesh(new T.CylinderGeometry(0.026, 0.028, 0.012, 36), M.brass); cbody.position.y = 0.006; comp.add(cbody);
  var dialTex = S.canvasTex(512, 512, function (x, w, h) {
    x.fillStyle = '#f8f5ec'; x.fillRect(0, 0, w, h);
    var cx = w / 2, cy = h / 2, R = w * 0.44;
    x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b';
    for (var i = 0; i < 360; i += 2) {
      var a = i * Math.PI / 180, big = i % 10 === 0, len = big ? 26 : 12;
      x.lineWidth = big ? 2.6 : 1.2; x.beginPath();
      x.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); x.lineTo(cx + Math.cos(a) * (R - len), cy + Math.sin(a) * (R - len)); x.stroke();
    }
    x.font = '700 30px "Public Sans", sans-serif'; x.textAlign = 'center';
    [[0, 'E'], [90, 'S'], [180, 'W'], [270, 'N']].forEach(function (q) {
      var a = q[0] * Math.PI / 180; x.fillText(q[1], cx + Math.cos(a) * (R - 54), cy + Math.sin(a) * (R - 54) + 10);
    });
    x.font = '600 22px "Public Sans", sans-serif';
    for (var g = 10; g <= 80; g += 10) [[-1, 1], [1, 1], [-1, -1], [1, -1]].forEach(function (sg) {
      var a = (270 + sg[0] * g) * Math.PI / 180;
      x.fillText(String(g), cx + Math.cos(a) * (R - 38) * sg[1] * (sg[1] > 0 ? 1 : -1), cy + Math.sin(a) * (R - 38) * (sg[1] > 0 ? 1 : -1) + 8);
    });
  });
  var dial = new T.Mesh(new T.CircleGeometry(0.0245, 48), new T.MeshStandardMaterial({ map: dialTex, roughness: 0.7 }));
  dial.rotation.x = -Math.PI / 2; dial.position.y = 0.0122; comp.add(dial);
  var ndl = new T.Group(); ndl.position.y = 0.0135; comp.add(ndl);
  var nN = S.mesh(new T.BoxGeometry(0.0016, 0.0008, 0.019), new T.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.4 }), false); nN.position.z = -0.0095; ndl.add(nN);
  var nS = S.mesh(new T.BoxGeometry(0.0016, 0.0008, 0.019), new T.MeshStandardMaterial({ color: 0xe8e8ea, roughness: 0.4 }), false); nS.position.z = 0.0095; ndl.add(nS);
  var hub = S.mesh(new T.CylinderGeometry(0.0015, 0.0015, 0.002, 12), M.chrome, false); ndl.add(hub);
  var cglass = new T.Mesh(new T.CircleGeometry(0.0265, 36), M.glass); cglass.rotation.x = -Math.PI / 2; cglass.position.y = 0.0145; comp.add(cglass);
  comp.position.set(WX, 0.0145, WZ);
  if (!COMPASS) comp.position.set(WX - 0.15, 0.0145, WZ + 0.11);               // parked beside the stage

  var tm = new T.Group(); S.scene.add(tm); tm.position.set(0.66, 0, -0.52); tm.rotation.y = -0.35;
  var tface = new T.Group(); tface.rotation.x = -Math.PI / 2; tface.position.y = 0.018; tm.add(tface);
  tface.add(S.rounded(0.1, 0.15, 0.034, 0.01, new T.MeshStandardMaterial({ color: 0x2f3338, roughness: 0.6 })));
  var tTex = S.canvasTex(560, 840, function (x, w, h) {
    x.fillStyle = '#2b2e34'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#f2f2f2'; x.textAlign = 'center'; x.font = '700 38px "Public Sans", sans-serif';
    x.fillText('HALL TESLAMETER', w / 2, 56);
    x.font = '600 26px "Public Sans", sans-serif'; x.fillStyle = '#9aa3ad'; x.fillText('DC  ·  AUTO RANGE', w / 2, 92);
    x.fillStyle = '#1b1d21'; x.fillRect(40, 120, w - 80, 220);
    x.fillStyle = '#f0b928'; x.font = '700 28px "Public Sans", sans-serif'; x.fillText('ZERO', w * 0.28, 420); x.fillStyle = '#f2f2f2'; x.fillText('HOLD', w * 0.72, 420);
    x.fillStyle = '#9aa3ad'; x.font = '600 24px "Public Sans", sans-serif'; x.fillText('PROBE', w / 2, 760);
  });
  tface.add((function () { var m = new T.Mesh(new T.PlaneGeometry(0.094, 0.141), new T.MeshStandardMaterial({ map: tTex, roughness: 0.5 })); m.position.z = 0.0172; return m; })());
  var tlcd = S.liveTex(512, 224), lastLcd = '';
  var lcdM = new T.Mesh(new T.PlaneGeometry(0.076, 0.033), new T.MeshBasicMaterial({ map: tlcd, toneMapped: false }));
  lcdM.position.set(0, 0.0345, 0.0176); tface.add(lcdM);
  function drawLcd() {
    var txt = (st.key ? teslaTxt() : '0.000 mT') + '|' + fI(Ical);
    if (txt === lastLcd) return; lastLcd = txt;
    tlcd.draw(function (x, w, h) {
      var g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#b9c4a7'); g.addColorStop(1, '#9eab8b');
      x.fillStyle = g; x.fillRect(0, 0, w, h);
      x.fillStyle = '#1b2116'; x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'left'; x.fillText('B  DC', 18, 36);
      x.textAlign = 'right'; x.font = '700 86px "JetBrains Mono", monospace';
      x.fillText(st.key ? teslaTxt().replace(' mT', '') : '0.000', w - 110, 140);
      x.font = '600 34px "Public Sans", sans-serif'; x.fillText('mT', w - 20, 140);
    });
  }
  var zeroBtn = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.003, 20), new T.MeshStandardMaterial({ color: 0xf0b928, roughness: 0.5 }));
  zeroBtn.rotation.x = Math.PI / 2; zeroBtn.position.set(-0.024, 0.0105, 0.0185); tface.add(zeroBtn);
  var holdBtn = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.003, 20), M.grey); holdBtn.rotation.x = Math.PI / 2; holdBtn.position.set(0.024, 0.0105, 0.0185); tface.add(holdBtn);
  S.contact(0.16, 0.2, 0.66, -0.52, 0.5);
  // the Hall probe: a thin wand on a lead, slid into the coil / solenoid
  var probe = new T.Group(); S.scene.add(probe);
  var wand = S.mesh(new T.BoxGeometry(0.004, 0.0022, 0.1), new T.MeshStandardMaterial({ color: 0x1f2227, roughness: 0.5 })); wand.position.z = -0.05; probe.add(wand);
  var ptip = S.mesh(new T.BoxGeometry(0.0055, 0.0012, 0.008), new T.MeshStandardMaterial({ color: 0xd9d9dd, roughness: 0.3, metalness: 0.5 })); ptip.position.z = -0.101; probe.add(ptip);
  var grip2 = S.mesh(new T.CylinderGeometry(0.0062, 0.0062, 0.05, 16), M.blackPlastic); grip2.rotation.x = Math.PI / 2; grip2.position.z = 0.03; probe.add(grip2);
  function probeHome() { return new T.Vector3(WX + 0.08, 0.03, WZ + 0.2); }
  function probeIn() { return new T.Vector3(WX, 0.0145 + (KIND === 'coil' ? p.a + 0.012 : Math.max(0.006, p.a) + 0.03), WZ + 0.1); }
  probe.position.copy(COMPASS ? probeHome() : probeIn());
  probe.visible = !COMPASS;
  function movedProbe(on) {
    if (COMPASS) return Promise.resolve();
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.probeIn) return Promise.resolve();
    var from = probe.position.clone(), to = on ? probeIn() : probeHome();
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.006, 0.03)),
      function (k) { return from.clone().lerp(to, k).add(new T.Vector3(0, 0.006, 0.03)); },
      function (k) { probe.position.copy(from.clone().lerp(to, k)); }, { ms: 850, mode: 'top' })
      .then(function () {
        probe.position.copy(to); st.probeIn = !!on; solve();
        S.say(on ? 'The Hall probe sits at the centre, its face across the field.' : 'The probe is drawn out of the ' + (KIND === 'coil' ? 'coil' : 'solenoid') + '.');
        S.render();
      });
  }
  S.wire([[0.63, 0.03, -0.45], [0.54, 0.02, -0.38], [WX + 0.12, 0.02, WZ + 0.22], [probe.position.x + 0.004, 0.028, probe.position.z + 0.055]], 'black');

  // ---------- the leads
  lead(pbPlus.at, kL.at, 'red', [[-0.5, -0.26], [-0.46, -0.12]]);
  lead(kR.at, rhA.at, 'red', [[-0.34, -0.1], [-0.3, 0.0]]);
  lead(rhC.at, srcP.at, 'yellow', [[0.04, 0.04], [0.2, 0.06]]);
  lead(srcM.at, amP.at, 'yellow', [[0.08, -0.3], [-0.26, -0.36]]);
  lead(amM.at, pbMinus.at, 'black', [[-0.54, -0.46], [-0.62, -0.34]]);

  S.addApparatus('pb', pb, 'DC supply (' + fmtN(p.Eb, 1) + ' V)', 'A low-voltage supply. Everything here runs on cells or this box: never on the mains.');
  S.addApparatus('key', key, 'Plug key K', 'Closes the circuit. Keep it open between readings so the wire stays cool.');
  S.addApparatus('rh', rh, 'Rheostat', 'Changes the resistance of the circuit, and so the current. Start with it at maximum.');
  S.addApparatus('am', am, 'Ammeter (0–' + fmtN(AMAX) + ' A)', 'In series with the conductor. Read to ' + fmtN(ARES) + ' A.');
  S.addApparatus('src', src, KIND === 'wire' ? 'Straight conductor' : KIND === 'coil' ? 'Circular coil (' + Math.round(p.N) + ' turns, radius ' + fmtN(p.a * 100, 1) + ' cm)'
    : CORE ? 'Coil on an iron nail' : 'Solenoid (' + fmtN(p.Lsol * 100, 0) + ' cm, ' + Math.round(p.nsol) + ' turns/m)',
    KIND === 'wire' ? 'A thick copper wire held ' + fmtN(D0 * 100, 1) + ' cm above the card, along the magnetic meridian.'
      : KIND === 'coil' ? 'Turns of insulated copper on a vertical former. Every turn adds its own field at the centre.'
        : CORE ? 'About ' + Math.round(p.nsol * p.Lsol) + ' turns wound along a 6 cm iron nail. The nail can be slid out.'
          : 'A long coil. Inside it the field is almost uniform and parallel to the axis.');
  S.addApparatus('comp', comp, 'Plotting compass', 'Its needle points along the resultant of the earth’s horizontal field and the field of the current, so tan(deflection) = B / B_H.');
  if (!COMPASS) S.addApparatus('tm', tm, 'Hall teslameter', 'Reads the field directly in millitesla. Press ZERO with the key open before each set of readings.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudI = S.hudCard('Ammeter'), hudB = S.hudCard('Field B'), hudD = S.hudCard(COMPASS ? 'Deflection' : CORE ? 'Core' : 'Probe');
  solve();

  // ---------- actions
  function trace() {
    st.traced = true; S.focus('circuit');
    S.say('Supply + → key → rheostat → ' + (KIND === 'wire' ? 'the straight wire' : KIND === 'coil' ? 'the coil' : CORE ? 'the coil on the nail' : 'the solenoid')
      + ' → ammeter → supply −: one series circuit, so the ammeter reads the current in the conductor itself.');
    S.render();
  }
  function zeroCheck() {
    if (st.key) { S.say('Take the key out first: the zero is checked with no current.'); return; }
    st.zero = true; S.focus(COMPASS ? 'comp' : 'tm');
    S.say(COMPASS ? 'With no current the needle rests along north-south, on the zero of the dial: the card is lined up with the magnetic meridian.'
      : 'With no current the teslameter reads zero after ZERO is pressed: the earth’s field is taken out.');
    S.render();
  }
  function sprinkle() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    st.filings = !st.filings; filG.visible = st.filings && st.key;
    S.say(st.filings ? (st.key ? 'The filings set themselves in ' + (KIND === 'wire' ? 'circles round the wire' : 'a pattern like a bar magnet’s') + '.'
      : 'The filings are sprinkled. Close the key and tap the card to see the pattern.') : 'The filings are brushed off the card.');
    S.render(); return Promise.resolve();
  }
  function setCore(on) {
    if (!CORE) return Promise.resolve();
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (!!on === st.core) return Promise.resolve();
    var g = src.userData.nail, tp = src.userData.tip, x0 = g.position.x, x1 = WX + (on ? 0 : 0.17);
    function tipAt(x) { return new T.Vector3(x + p.Lsol / 2 + 0.03, g.position.y + 0.012, g.position.z); }
    return S.hand.pinchMove(tipAt(x0),
      function (k) { return tipAt(x0 + (x1 - x0) * k); },
      function (k) { g.position.x = x0 + (x1 - x0) * k; tp.position.x = g.position.x + p.Lsol / 2 + 0.022; },
      { ms: 800, mode: 'top' }).then(function () {
        g.position.x = x1; tp.position.x = g.position.x + p.Lsol / 2 + 0.022;
        st.core = !!on; solve();
        S.say(on ? 'The iron nail is pushed back into the coil: the field jumps up.' : 'The nail is drawn out: only the coil’s own field is left.');
        S.render();
      });
  }
  function reverse() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var was = st.key;
    return (was ? setKey(false) : Promise.resolve()).then(function () {
      st.rev = -st.rev; solve();
      S.say('The two leads at the supply have been changed over: the current now flows the other way.');
      return was ? setKey(true) : Promise.resolve();
    }).then(function () { S.render(); });
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('The key is open, so there is no current. Close it first.'); return false; }
    if (!COMPASS && !st.probeIn) { S.say('Slide the Hall probe in to the centre first.'); return false; }
    if (COMPASS && Math.abs(st.d - D0) > 1e-9) { S.say('Take the whole set of readings at one distance: put the wire back to ' + fmtN(D0 * 100, 1) + ' cm.'); return false; }
    var i = +fI(Ical);
    if (i <= 0) { S.say('The ammeter reads zero. Check the circuit.'); return false; }
    if (S.rows.length >= 12) { S.say('Twelve readings are plenty. Go on to the graph.'); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.I - i) < ARES / 2; })) { S.say('There is already a reading at I = ' + i.toFixed(2) + ' A. Move the rheostat for a new current.'); return false; }
    if (COMPASS) {
      var th = degRead();
      if (th < 2) { S.say('The deflection is too small to read. Let more current through.'); return false; }
      if (th > 80) { S.say('The needle is nearly across the dial: at more than 80° the reading is useless. Cut the current down.'); return false; }
      S.addRow({ I: i, th: th, B: BH * Math.tan(th * Math.PI / 180) });
      S.say('Written in your record book: I = ' + i.toFixed(2) + ' A, deflection = ' + th.toFixed(1) + '°.');
      return true;
    }
    if (CORE) {
      var wasCore = st.core;
      if (!wasCore) { S.say('Read the field with the nail in first; the pair of readings is taken at one current.'); return false; }
      S.addRow({ I: i, B: teslaRead(), B0: null });
      S.say('Field with the core: ' + teslaTxt() + '. Now draw the nail out and record the empty coil at the same current.');
      return true;
    }
    S.addRow({ I: i, B: teslaRead() });
    S.say('Written in your record book: I = ' + i.toFixed(2) + ' A, B = ' + teslaTxt() + '.');
    return true;
  }
  function recordEmpty() {
    if (!CORE) return false;
    if (st.core) { S.say('Draw the nail out first.'); return false; }
    var open = null;
    for (var i = S.rows.length - 1; i >= 0; i--) if (S.rows[i].B0 === null) { open = S.rows[i]; break; }
    if (!open) { S.say('Record the field with the core first.'); return false; }
    if (Math.abs(+fI(Ical) - open.I) > ARES) { S.say('Set the current back to ' + open.I.toFixed(2) + ' A: the pair must be taken at the same current.'); return false; }
    open.B0 = teslaRead(); S.book.draw(); S.render();
    S.say('Empty coil at the same current: ' + teslaTxt() + '. The ratio of the two is what the iron does.');
    return true;
  }
  function pending() { return CORE && S.rows.some(function (r) { return r.B0 === null; }); }
  var NEED = CORE ? 3 : 4;
  function done() { return S.rows.length >= NEED && !pending(); }

  // the currents the walk-through uses: spread over the rheostat, never above the meter's range
  function plan() {                                       // the rheostat only ever cuts the current down from I0
    var out = [], k;
    for (k = 0; k < NEED; k++) out.push(Math.min(RS_MAX, RS0 / (1 - 0.15 * k)));
    return out;
  }

  var steps = [
    { id: 'check', title: 'Check the circuit', view: 'circuit', render: function (u) {
        u.h2('Set the circuit up');
        u.p('The conductor is in series with the key, the rheostat and the ammeter, so the ammeter reads exactly the current in it.');
        u.task('1. Trace the circuit', st.traced, st.traced ? 'Supply, key, rheostat, conductor, ammeter: one loop' : 'Follow the leads from the supply’s + terminal')
          .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
        u.task('2. ' + (COMPASS ? 'Line the card up and check the zero' : 'Zero the teslameter'), st.zero,
          st.zero ? (COMPASS ? 'Needle along north-south, on zero' : 'Teslameter reads 0.000 mT') : 'With the key open')
          .add(u.button(st.zero ? 'Checked' : (COMPASS ? 'Check the zero' : 'Press ZERO'), zeroCheck, !st.zero, st.zero));
        u.note(COMPASS ? 'The dial’s north-south line must lie along the needle before the current is switched on, or the deflection cannot be read.'
          : 'The teslameter measures the earth’s field as well, so it is zeroed with the key open.');
        u.next('Next: switch the current on', st.traced && st.zero);
      },
      ok: function () { return st.traced && st.zero; },
      auto: function () { trace(); zeroCheck(); return Promise.resolve(); } }];

  if (!COMPASS) {
    steps.push({ id: 'probe', title: 'Put the probe in', view: 'src', render: function (u) {
        u.h2('Slide the Hall probe to the centre');
        u.p('The probe must sit where the field is being measured, with its flat face across the field.');
        u.task('Probe at the centre', st.probeIn, st.probeIn ? 'In place' : 'Lying beside the stage')
          .add(u.row(u.button(st.probeIn ? 'In place' : 'Slide the probe in', function () { movedProbe(true); }, true, S.hand.busy || st.probeIn),
            u.button('Draw it out', function () { movedProbe(false); }, false, S.hand.busy || !st.probeIn)));
        u.live(function () { return 'Teslameter ' + (st.key ? teslaTxt() : '0.000 mT'); });
        u.next('Next: switch the current on', st.probeIn);
      },
      ok: function () { return st.probeIn; },
      auto: function () { return movedProbe(true); } });
  }

  steps.push({ id: 'on', title: 'Switch on', view: COMPASS ? 'comp' : 'src', render: function (u) {
      u.h2('Close the key and watch');
      u.p(COMPASS ? 'The hand pushes the plug in. The moment the current flows the needle swings off north: a current makes a magnetic field. This was Oersted’s discovery.'
        : 'The hand pushes the plug in. The teslameter reads the field the current has made.');
      u.task('Key closed', st.key, st.key ? 'Current ' + fI(Ical) + ' A' : 'Open: no current')
        .add(u.row(u.button(st.key ? 'Key is in' : 'Insert the plug', function () { setKey(true); }, true, st.key || S.hand.busy),
          u.button('Take the plug out', function () { setKey(false); }, false, !st.key || S.hand.busy)));
      u.row(u.button('Reverse the current', function () { reverse(); }, false, S.hand.busy),
        u.button(st.filings ? 'Brush the filings off' : 'Sprinkle iron filings', function () { sprinkle(); }, false, S.hand.busy));
      if (CORE) u.row(u.button(st.core ? 'Draw the nail out' : 'Push the nail in', function () { setCore(!st.core); }, false, S.hand.busy));
      u.live(function () {
        return 'Ammeter ' + fI(Ical) + ' A  ·  ' + (COMPASS ? 'deflection ' + degRead().toFixed(1) + '°' : 'B ' + (st.key ? teslaTxt() : '0.000 mT'));
      });
      u.note(COMPASS ? 'Reverse the current and the needle swings the same amount the other way: the field has reversed with it.'
        : 'The filings on the card show the shape of the field; the teslameter gives its size.');
      u.next('Next: take the readings', st.key);
    },
    ok: function () { return st.key; },
    auto: function () { return setKey(true).then(sprinkle).then(reverse).then(reverse); } });

  steps.push({ id: 'read', title: 'Take the readings', view: 'work', render: function (u) {
      u.h2(CORE ? 'The field with the core and without it' : COMPASS ? 'Deflection at several currents' : 'Field at several currents');
      u.p(CORE ? 'At each current read the field with the nail in, then draw the nail out and read it again. Three pairs are enough.'
        : 'Move the rheostat contact to change the current and take ' + NEED + ' readings at different currents.');
      u.slider('Rheostat resistance', RS_MIN, RS_MAX, 0.5, function () { return st.target; }, function (v) { st.target = v; }, 'Ω', 1);
      u.row(u.button('Slide the contact', function () { slide(st.target); }, true, S.hand.busy),
        u.button(st.key ? 'Take the plug out' : 'Insert the plug', function () { setKey(!st.key); }, false, S.hand.busy));
      if (COMPASS) {
        u.slider('Height of the wire above the needle', 0.01, 0.1, 0.005, function () { return st.d; }, function (v) { st.d = v; solve(); }, 'm', 3);
        u.note('Raise the wire and the deflection falls: the field goes as 1/d. Put it back to ' + fmtN(D0 * 100, 1) + ' cm for the table.');
      }
      if (CORE) u.row(u.button(st.core ? 'Draw the nail out' : 'Push the nail in', function () { setCore(!st.core); }, false, S.hand.busy),
        u.button('Record the empty coil', function () { recordEmpty(); }, false, S.hand.busy || st.core || !pending()));
      u.row(u.button(CORE ? 'Record with the core' : 'Record this reading', function () { record(); }, true, !st.key || S.hand.busy));
      u.live(function () {
        return 'I ' + fI(Ical) + ' A  ·  ' + (COMPASS ? 'deflection ' + degRead().toFixed(1) + '°  ·  B = B_H tan θ = ' + (BH * Math.tan(degRead() * Math.PI / 180) * 1e6).toFixed(2) + ' µT'
          : 'B ' + (st.key ? teslaTxt() : '0.000 mT')) + (CORE ? '  ·  nail ' + (st.core ? 'in' : 'out') : '');
      });
      u.h3('Observation table'); u.table();
      if (!done()) u.p(S.rows.length + ' of at least ' + NEED + (CORE ? ' pairs' : ' readings') + ' recorded' + (pending() ? '; one pair still needs the empty-coil reading.' : '.'));
      u.next('Next: the graph and the result', done());
    },
    ok: done,
    auto: function () {
      var rs = plan();
      return rs.reduce(function (pr, r) {
        return pr.then(function () {
          return slide(r).then(function () {
            S.advance(0.2);
            if (!CORE) { record(); return null; }
            if (!st.core) return setCore(true).then(function () { S.advance(0.1); record(); return setCore(false).then(function () { S.advance(0.1); recordEmpty(); }); });
            record();
            return setCore(false).then(function () { S.advance(0.1); recordEmpty(); return setCore(true); });
          });
        });
      }, st.key ? Promise.resolve() : setKey(true));
    } });

  var TRUTH = CORE ? MUR0 : perAmp(D0, CORE ? MUR0 : p.mur);
  return {
    camera: { pos: [0.02, 1.46, 0.58], look: [0.02, 0.0, -0.24] },
    views: { pb: [[-0.46, 0.34, -0.04], [-0.56, 0.04, -0.22]], key: [[-0.38, 0.26, 0.14], [-0.42, 0.02, -0.05]],
      rh: [[-0.12, 0.3, 0.2], [-0.14, 0.04, 0.0]], am: [[-0.4, 0.3, -0.16], [-0.4, 0.04, -0.45]],
      src: [[0.36, 0.3, 0.04], [0.36, 0.04, -0.26]], comp: [[WX + 0.02, 0.17, WZ + 0.14], [WX, 0.015, WZ]],
      tm: [[0.62, 0.3, -0.22], [0.66, 0.02, -0.52]],
      circuit: [[0.02, 1.46, 0.58], [0.02, 0.0, -0.24]], work: [[0.22, 0.8, 0.3], [0.22, 0.02, -0.28]],
      book: [[-0.5, 0.45, 0.6], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: KIND === 'wire'
        ? 'A current makes a magnetic field round itself. Round a long straight wire the lines are circles, and their direction is given by the right-hand thumb rule. '
          + 'A compass needle under the wire sets itself along the resultant of this field and the earth’s horizontal field B_H.'
        : KIND === 'coil'
          ? 'Every small part of a current-carrying loop adds its own field, and on the axis all these contributions point the same way, so they simply add. '
            + 'The field is strongest at the centre and falls away along the axis.'
          : CORE ? 'A coil carrying a current behaves as a magnet. Put soft iron inside and the iron is magnetised too, so its own magnetisation adds to the coil’s field '
            + 'and multiplies it many times over. Switch the current off and almost all of it goes.'
            : 'A solenoid is a stack of circular loops. Inside a long one the fields of the turns add to a nearly uniform field along the axis; outside, the lines '
              + 'spread and return, exactly like a bar magnet’s.',
      formula: KIND === 'wire' ? 'B = μ₀I / (2πd),   tan θ = B / B_H'
        : KIND === 'coil' ? 'B = μ₀ N I a² / (2 (a² + z²)^{3/2})'
          : CORE ? 'B = μ₀ μ_r n I' : 'B = μ₀ n I',
      formulaNote: KIND === 'wire' ? 'so the deflection grows with the current and falls as the wire is raised'
        : CORE ? 'μ_r for this nail is what the two readings give' : 'proportional to the current, so the graph is a straight line through the origin',
      more: [KIND === 'wire'
        ? 'Because the wire has ends, the field close to its middle is a little less than the ideal μ₀I/2πd: the exact value for a wire of length L is '
          + 'μ₀I/(2πd) × (L/2)/√(d² + L²/4), and that is what this set-up is measured against.'
        : KIND === 'coil' ? 'Twenty turns give twenty times the field of one turn at the same current, which is why a few turns of wire can deflect a compass that a single wire hardly moves.'
          : CORE ? 'The textbook permeability of iron is in the thousands, but a short nail cannot reach it: the poles at its two ends set up a field inside that opposes the '
            + 'magnetisation. What this experiment measures is the effective multiplier of this particular nail in this particular coil.'
            : 'Inside a long solenoid the field does not depend on the radius or on how many turns there are in all, only on how many turns there are per metre.'],
      precautions: 'Low-voltage supply only, never the mains. Start with the rheostat at its maximum so the first current is small, keep the key open between readings so '
        + 'nothing heats up, and keep magnets, phones and iron away from the compass.' },
    book: { title: 'Expt. — ' + (KIND === 'wire' ? 'Magnetic field of a straight current' : KIND === 'coil' ? 'Magnetic field of a circular coil'
      : CORE ? 'An electromagnet on an iron nail' : 'Magnetic field of a solenoid'),
      lines: ['Aim: ' + S.lab.aim].concat(SAMPLE ? ['Set-up: ' + SAMPLE] : []).concat(
        KIND === 'wire' ? ['Wire ' + fmtN(D0 * 100, 1) + ' cm above the needle', 'B_H = ' + fmtN(BH * 1e6, 1) + ' µT (given)',
          'B = B_H tan θ', 'B / I compared with μ₀I/2πd × end correction']
          : KIND === 'coil' ? ['Coil: ' + Math.round(p.N) + ' turns, radius ' + fmtN(p.a * 100, 1) + ' cm',
            'Hall probe at the centre', 'B / I compared with μ₀N/2a']
            : CORE ? ['Nail: 6 cm soft iron, ' + Math.round(p.nsol * p.Lsol) + ' turns', 'B with the core ÷ B without = μ_r (effective)']
              : ['Solenoid: ' + fmtN(p.Lsol * 100, 0) + ' cm, ' + Math.round(p.nsol) + ' turns/m', 'Hall probe at the centre', 'B / I compared with μ₀n']),
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'I (A)', get: function (r) { return r.I.toFixed(2); } }]
        .concat(COMPASS ? [{ label: 'θ (°)', get: function (r) { return r.th.toFixed(1); } },
          { label: 'B = B_H tan θ (µT)', get: function (r) { return (r.B * 1e6).toFixed(2); } }]
          : CORE ? [{ label: 'B core (mT)', get: function (r) { return (r.B * 1000).toFixed(1); } },
            { label: 'B empty (mT)', get: function (r) { return r.B0 === null ? '—' : (r.B0 * 1000).toFixed(3); } },
            { label: 'μ_r', get: function (r) { return r.B0 ? (r.B / r.B0).toFixed(0) : '—'; } }]
            : [{ label: 'B (mT)', get: function (r) { return (r.B * 1000).toFixed(3); } },
              { label: 'B/I (mT/A)', get: function (r) { return r.I ? (r.B * 1000 / r.I).toFixed(3) : '—'; } }]) },
    graph: CORE ? null : { x: function (r) { return r.I; }, y: function (r) { return r.B * (COMPASS ? 1e6 : 1000); },
      xlabel: 'I (A)', ylabel: COMPASS ? 'B (µT)' : 'B (mT)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: function (rows) {
      if (rows.length < NEED) return null;
      if (CORE) {
        var rs = rows.filter(function (r) { return r.B0; });
        if (rs.length < NEED) return null;
        return { label: 'Effective μ_r of the nail', value: S.fit.mean(rs.map(function (r) { return r.B / r.B0; })), unit: '', digits: 0,
          truth: TRUTH, note: 'Mean of (field with the core) ÷ (field without it) at the same current.' };
      }
      var k = S.fit.origin(rows.map(function (r) { return [r.I, r.B]; }));
      return { label: 'Field per ampere', value: k * (COMPASS ? 1e6 : 1000), unit: COMPASS ? 'µT/A' : 'mT/A', digits: 3,
        truth: TRUTH * (COMPASS ? 1e6 : 1000), note: 'Slope of the B against I graph, a straight line through the origin.' };
    },
    tol: 0.05,
    resultNote: COMPASS ? 'The field is proportional to the current and nothing else changed, so the graph had to be a straight line through the origin.'
      : CORE ? 'The same coil, the same current, and the field jumped by that factor: all of it is the iron’s doing.' : '',
    chips: ['Why does the needle deflect at all?', 'What is the right-hand thumb rule?',
      COMPASS ? 'Why must the card be lined up with north?' : 'Why is the field uniform inside?',
      'Check my readings', CORE ? 'Why soft iron and not steel?' : 'What happens if the current is reversed?'],
    viva: [[KIND === 'wire' ? 'The current is doubled and the compass left where it is. tan(deflection)' : 'The current is doubled. The field becomes',
      ['Doubles', 'Halves', 'Stays the same'], 0, 'The field of a current is proportional to the current.'],
    [COMPASS ? 'Why is a deflection of more than 80° useless?' : 'Why is the teslameter zeroed with the key open?',
      COMPASS ? ['tan θ changes too fast there to be read accurately', 'The needle breaks', 'The field reverses']
        : ['To take the earth’s own field out of the reading', 'To charge the probe', 'To cool the coil'], 0,
      COMPASS ? 'Near 90° a tiny error in the angle is a huge error in tan θ.' : 'Otherwise every reading carries the earth’s field with it.']],
    askState: function () {
      return { set_up: KIND === 'wire' ? 'straight wire over a plotting compass' : KIND === 'coil' ? 'circular coil with a Hall probe'
        : CORE ? 'coil on an iron nail' : 'solenoid with a Hall probe',
        key_closed: st.key, ammeter_A: +fI(Ical), rheostat_ohm: +fmtN(st.rs, 1),
        field_uT: +(Math.abs(B) * 1e6).toFixed(2), compass_deflection_deg: COMPASS ? degRead() : null,
        current_direction: st.rev > 0 ? 'as drawn' : 'reversed', iron_core_in: CORE ? st.core : null,
        probe_at_centre: COMPASS ? null : st.probeIn, distance_cm: KIND === 'wire' ? +fmtN(st.d * 100, 1) : null,
        earth_field_uT: +fmtN(BH * 1e6, 1), readings_taken: S.rows.length };
    },
    steps: steps,
    tick: function () {
      solve();
      am.set(Ical);
      ndl.rotation.y += (needle - ndl.rotation.y) * 0.18;
      filG.visible = st.filings && st.key;
      drawLcd();
      hudI.set(fI(Ical) + ' A');
      hudB.set(st.key ? (Math.abs(B) * 1e6 >= 1000 ? (Math.abs(B) * 1000).toFixed(2) + ' mT' : (Math.abs(B) * 1e6).toFixed(2) + ' µT') : '0 µT');
      hudD.set(COMPASS ? degRead().toFixed(1) + '°' : CORE ? (st.core ? 'In' : 'Out') : (st.probeIn ? 'At centre' : 'Out'));
    },
  };
});
