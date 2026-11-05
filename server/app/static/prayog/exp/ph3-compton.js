/* Prayogshala studio module: COMPTON SCATTERING BENCH (M.Sc. / PhD nuclear physics).
   A collimated Cs-137 source in a lead housing with a shutter, a small scatterer on a turntable, a NaI(Tl)
   detector on a graduated arm that swings about the scatterer, and a multichannel analyser with a live spectrum.
   The energy scale is calibrated on two known lines (the direct Cs-137 beam and an Am-241 disc), then the scattered
   photopeak is found at seven angles. The same bench serves the energy-against-angle experiment (electron rest
   energy) and the Klein-Nishina cross-section experiment (differential and total cross-section).
   Physics: the `ph3_compton` kernel of packs/ph3_nuc.js. Counts are Poisson numbers from the lab's own seed; the
   scatterer is treated as thin (no absorption inside it): a stated simplification. */
HoolaStudio.define('ph3-compton', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ph3_compton, assign = HK.assign;
  var p = HK.paramsFor('ph3_compton', S.lab.params);
  var V_ = S.lab.variant || {}, GATED = p.coin > 0, TASK = p.task >= 0.5 ? 1 : 0;
  var KIND = GATED ? 'plastic' : (p.ne25 < 1 ? 'copper' : 'aluminium');
  var SCN = { aluminium: 'Aluminium rod, 3 cm by 5 cm', copper: 'Copper rod, 1 cm by 3 cm', plastic: 'Plastic scintillator rod, 3 cm by 5 cm' };
  var SAMPLE = V_.sample || SCN[KIND], CAL_N = 2.0e4, NCH = Math.round(p.nch), AM = KN.CAL_AM;
  var CARD = KN.card(p), CX = -0.12, CZ = -0.15, RD = 0.19, BY = 0.075;
  var st = { shut: false, scatIn: true, am: false, th: 90, counting: false, prog: 0, counts: null, what: '', pk: null, tlive: 0, idx: 0,
    cal: null, fitted: false, recorded: true };
  // ---------------------------------------------------------------- shared bench helpers (this rig carries its own copy)
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function pad(n, w) { var s = String(n); while (s.length < w) s = '0' + s; return s; }
  var leadM = new T.MeshStandardMaterial({ color: 0x53565c, roughness: 0.72, metalness: 0.55 });
  function brick(g, x, y, z, w, h, d) { var b = S.rounded(w, d, h, 0.004, leadM); b.rotation.x = -Math.PI / 2; b.position.set(x, y + h / 2, z); g.add(b); return b; }
  function makeSource(color) {
    var g = new T.Group();
    var disc = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.004, 24), new T.MeshStandardMaterial({ color: color || 0xb8322a, roughness: 0.4, metalness: 0.3 }));
    g.add(disc);
    var rim = S.mesh(new T.TorusGeometry(0.0085, 0.0012, 8, 24), M.chrome); rim.rotation.x = Math.PI / 2; g.add(rim);
    var tref = S.canvasTex(128, 128, function (x, w, h) {
      x.fillStyle = '#f2d02a'; x.fillRect(0, 0, w, h); x.fillStyle = '#1b1b1b'; x.beginPath(); x.arc(w / 2, h / 2, 10, 0, Math.PI * 2); x.fill();
      for (var i = 0; i < 3; i++) { x.beginPath(); x.arc(w / 2, h / 2, 46, i * 2.094 - 0.45, i * 2.094 + 0.45); x.arc(w / 2, h / 2, 18, i * 2.094 + 0.45, i * 2.094 - 0.45, true); x.closePath(); x.fill(); } });
    var tm = new T.Mesh(new T.CircleGeometry(0.0082, 24), new T.MeshStandardMaterial({ map: tref, roughness: 0.6 }));
    tm.rotation.x = -Math.PI / 2; tm.position.y = 0.0021; g.add(tm);
    return g;
  }
  function makePot(x, z, text) {
    var pot = new T.Group(); S.scene.add(pot); pot.position.set(x, 0, z);
    var b = S.mesh(new T.CylinderGeometry(0.03, 0.032, 0.03, 28), leadM); b.position.y = 0.015; pot.add(b);
    var h = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.022, 24), new T.MeshStandardMaterial({ color: 0x17181b })); h.position.y = 0.021; pot.add(h);
    var lid = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.008, 28), leadM); lid.position.set(0.055, 0.004, 0.02); pot.add(lid);
    var lb = S.label(text || 'SEALED SOURCE STORE', { w: 0.06, ratio: 0.2, color: '#e8e8ea' }); lb.rotation.x = -Math.PI / 2; lb.position.set(0, 0.0012, 0.058); pot.add(lb);
    return pot;
  }
  function makeTongs(x, z) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0.004, z); g.rotation.y = 0.4;
    [-1, 1].forEach(function (sg) { var a = S.mesh(new T.BoxGeometry(0.17, 0.004, 0.005), M.chrome); a.position.set(0, 0, sg * 0.006); a.rotation.y = sg * 0.04; g.add(a); });
    var hg = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.016, 12), M.chrome); hg.rotation.x = Math.PI / 2; hg.position.set(0.06, 0, 0); g.add(hg);
    return g;
  }
  // a rack-mounted instrument: front panel drawn on a canvas, with helper to place parts on it (metres from its centre)
  function panel(W, H, D, drawFn, x, z, ry) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var caseM = S.rounded(W, D, H, 0.012, new T.MeshStandardMaterial({ color: 0xd7d3c9, roughness: 0.5, metalness: 0.12 }));
    caseM.rotation.x = -Math.PI / 2; caseM.position.y = H / 2 + 0.004; g.add(caseM);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) { var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber); ft.position.set(f[0] * (W / 2 - 0.02), 0.002, f[1] * (D / 2 - 0.02)); g.add(ft); });
    var FZ = D / 2 + 0.0062, PW = W - 0.014, PH = H - 0.014;
    var tex = S.canvasTex(Math.min(2000, Math.round(W * 2800)), Math.round(Math.min(2000, Math.round(W * 2800)) * PH / PW), function (x, w, h) {
      var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
      x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
      drawFn(x, w, h, X, Y, k);
    });
    var fac = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }), M.grey]);
    fac.position.set(0, 0.004 + H / 2, FZ - 0.002); g.add(fac);
    S.contact(W * 1.25, D * 1.35, x, z, 0.55);
    return { g: g, FZ: FZ, PW: PW, PH: PH, H: H, up: function (u, v, dz) { return new T.Vector3(u, 0.004 + H / 2 + v, FZ + (dz || 0)); } };
  }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; for (var i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  function makeKnob(pn, u, v) {
    var k = new T.Group(); k.position.copy(pn.up(u, v)); pn.g.add(k);
    var sk = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 36), M.bakelite); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; k.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; k.add(kb);
    var pt = S.mesh(new T.BoxGeometry(0.002, 0.016, 0.0012), M.white, false); pt.position.set(0, 0.009, 0.0215); k.add(pt);
    return k;
  }
  function makeButton(pn, u, v, mat) { var b = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.008, 20), mat || M.green); b.rotation.x = Math.PI / 2; b.position.copy(pn.up(u, v, 0.004)); pn.g.add(b); return b; }
  function makeLcd(pn, cx, cy, wdt, hgt, digits) {
    var tex = S.liveTex(512, 190), last = '';
    var bez = S.mesh(new T.BoxGeometry(wdt + 0.006, hgt + 0.006, 0.003), M.grey); bez.position.copy(pn.up(cx, cy, 0.001)); pn.g.add(bez);
    var scr = new T.Mesh(new T.PlaneGeometry(wdt, hgt), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.copy(pn.up(cx, cy, 0.004)); pn.g.add(scr);
    var ghost = ''; while (ghost.length < digits) ghost += '8';
    var set = function (txt) {
      if (txt === last) return; last = txt;
      tex.draw(function (x) {
        var gr = x.createLinearGradient(0, 0, 0, 190); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); x.fillStyle = gr; x.fillRect(0, 0, 512, 190);
        x.font = '700 ' + Math.round(Math.min(110, 880 / (digits + 1))) + 'px "JetBrains Mono", monospace'; x.textAlign = 'right';
        x.fillStyle = 'rgba(0,0,0,.07)'; x.fillText(ghost, 480, 130); x.fillStyle = '#1b2116'; x.fillText(txt, 480, 130);
      });
    };
    set('0'); return set;
  }
  // a flat monitor on a stand showing a live plot
  function makeScreen(x, z, ry, W, H) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = ry || 0;
    var base = S.rounded(0.14, 0.1, 0.008, 0.004, M.iron); base.rotation.x = -Math.PI / 2; base.position.set(0, 0.004, 0); g.add(base);
    var neck = S.mesh(new T.CylinderGeometry(0.012, 0.016, 0.07, 20), M.iron); neck.position.set(0, 0.04, 0); g.add(neck);
    var head = new T.Group(); head.position.set(0, 0.075 + H / 2, 0.01); head.rotation.x = -0.12; g.add(head);
    var bz = S.rounded(W + 0.03, H + 0.03, 0.02, 0.008, new T.MeshStandardMaterial({ color: 0x1a1c20, roughness: 0.5, metalness: 0.3 })); head.add(bz);
    var tex = S.liveTex(1280, Math.round(1280 * H / W));
    var scr = new T.Mesh(new T.PlaneGeometry(W, H), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); scr.position.z = 0.0125; head.add(scr);
    S.contact(0.2, 0.16, x, z, 0.5);
    return { g: g, tex: tex, W: W, H: H };
  }
  // plot helpers for the monitor
  function plotFrame(x, w, h, box, xmin, xmax, ymin, ymax, xlabel, ylabel, xt, yt, fmtx, fmty) {
    var X = function (v) { return box.l + (v - xmin) / (xmax - xmin) * (box.r - box.l); }, Y = function (v) { return box.b - (v - ymin) / (ymax - ymin) * (box.b - box.t); };
    x.strokeStyle = 'rgba(160,230,190,.16)'; x.lineWidth = 1; x.fillStyle = '#9fe0b8'; x.font = Math.round(h * 0.034) + 'px "JetBrains Mono", monospace';
    var i, v;
    x.textAlign = 'right';
    for (i = 0; i <= yt; i++) { v = ymin + (ymax - ymin) * i / yt; x.beginPath(); x.moveTo(box.l, Y(v)); x.lineTo(box.r, Y(v)); x.stroke(); x.fillText(fmty ? fmty(v) : String(Math.round(v)), box.l - 6, Y(v) + 5); }
    x.textAlign = 'center';
    for (i = 0; i <= xt; i++) { v = xmin + (xmax - xmin) * i / xt; x.beginPath(); x.moveTo(X(v), box.t); x.lineTo(X(v), box.b); x.stroke(); x.fillText(fmtx ? fmtx(v) : String(Math.round(v)), X(v), box.b + h * 0.045); }
    x.fillStyle = '#c9f5dc'; x.fillText(xlabel, (box.l + box.r) / 2, box.ly || h - 8);
    x.save(); x.translate(box.lx || 18, (box.t + box.b) / 2); x.rotate(-Math.PI / 2); x.fillText(ylabel, 0, 0); x.restore();
    x.strokeStyle = 'rgba(160,230,190,.5)'; x.strokeRect(box.l, box.t, box.r - box.l, box.b - box.t);
    return { X: X, Y: Y };
  }

  // ================================================================ source housing with shutter
  var house = new T.Group(); S.scene.add(house); house.position.set(-0.46, 0, CZ);
  brick(house, 0, 0, 0, 0.12, 0.12, 0.12); brick(house, 0.05, 0.0, 0.07, 0.04, 0.12, 0.04); brick(house, 0.05, 0.0, -0.07, 0.04, 0.12, 0.04);
  var coll = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.07, 20), new T.MeshStandardMaterial({ color: 0x17181b })); coll.rotation.z = Math.PI / 2; coll.position.set(0.04, BY, 0); house.add(coll);
  var plug = brick(house, 0.078, 0.0, 0, 0.026, 0.12, 0.05);
  var hlbl = S.label('Cs-137  ·  SEALED', { w: 0.09, ratio: 0.18, color: '#1b1b1b', bg: '#f2d02a' }); hlbl.position.set(-0.03, 0.09, 0.061); house.add(hlbl);
  var beamM = new T.MeshBasicMaterial({ color: 0xffd24a, transparent: true, opacity: 0.0, depthWrite: false });
  var beam = new T.Mesh(new T.CylinderGeometry(0.003, 0.003, 0.28, 8), beamM); beam.rotation.z = Math.PI / 2; beam.position.set(-0.46 + 0.075 + 0.14 + 0.02, BY, CZ); S.scene.add(beam);
  S.contact(0.2, 0.2, -0.46, CZ, 0.55);

  // ================================================================ turntable, protractor, scatterer
  var proto = new T.Mesh(new T.PlaneGeometry(0.62, 0.31), new T.MeshStandardMaterial({ roughness: 0.7, transparent: true, map: S.canvasTex(1240, 620, function (x, w, h) {
    var R = 0.30 / 0.62 * w, i, th, c = w / 2;
    x.fillStyle = 'rgba(236,232,222,.96)'; x.beginPath(); x.moveTo(c, 0); x.arc(c, 0, R, 0, Math.PI); x.closePath(); x.fill();
    x.strokeStyle = '#1b1b1b'; x.fillStyle = '#1b1b1b'; x.textAlign = 'center'; x.font = '600 24px "Public Sans", sans-serif';
    for (i = 0; i <= 180; i += 2) { th = i * Math.PI / 180; var big = i % 10 === 0, l = i % 20 === 0 ? 34 : (big ? 22 : 12);
      x.lineWidth = big ? 2.5 : 1.2; x.beginPath(); x.moveTo(c + Math.cos(th) * (R - 6), Math.sin(th) * (R - 6)); x.lineTo(c + Math.cos(th) * (R - 6 - l), Math.sin(th) * (R - 6 - l)); x.stroke();
      if (i % 20 === 0) x.fillText(String(i), c + Math.cos(th) * (R - 66), Math.sin(th) * (R - 66) + 8); }
    x.lineWidth = 3; x.beginPath(); x.arc(c, 0, R - 6, 0, Math.PI); x.stroke();
    x.lineWidth = 1.5; x.setLineDash([10, 8]); x.beginPath(); x.moveTo(c - R, 0); x.lineTo(c + R, 0); x.stroke(); x.setLineDash([]);
    x.font = '600 22px "Public Sans", sans-serif'; x.fillText('SCATTERING ANGLE θ (degrees)', c, R * 0.4); }) }));
  proto.rotation.x = -Math.PI / 2; proto.position.set(CX, 0.0035, CZ + 0.155); S.scene.add(proto);
  var turn = S.mesh(new T.CylinderGeometry(0.028, 0.03, 0.01, 36), M.iron); turn.position.set(CX, 0.009, CZ); S.scene.add(turn);
  var rodH = KIND === 'copper' ? 0.03 : 0.05, rodR = KIND === 'copper' ? 0.005 : 0.015;
  var rodM = KIND === 'plastic' ? new T.MeshStandardMaterial({ color: 0x8fbfe8, roughness: 0.2, transparent: true, opacity: 0.85 })
    : (KIND === 'copper' ? M.copper : new T.MeshStandardMaterial({ color: 0xc4c9ce, roughness: 0.3, metalness: 0.9 }));
  var rodG = new T.Group(); S.scene.add(rodG);
  var rod = S.mesh(new T.CylinderGeometry(rodR, rodR, rodH, 28), rodM); rod.position.y = rodH / 2; rodG.add(rod);
  var ROD_IN = new T.Vector3(CX, 0.014, CZ), ROD_OUT = new T.Vector3(CX - 0.01, 0.014, CZ + 0.255);
  rodG.position.copy(ROD_IN);
  if (GATED) {                                               // the scatterer is a scintillator: light guide and a small PMT
    var lg = S.mesh(new T.CylinderGeometry(0.012, 0.015, 0.05, 20), new T.MeshStandardMaterial({ color: 0x15171a })); lg.position.y = rodH + 0.025; rodG.add(lg);
    var spmt = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.06, 20), new T.MeshStandardMaterial({ color: 0x2c3138, metalness: 0.5, roughness: 0.5 })); spmt.position.y = rodH + 0.075; rodG.add(spmt);
  }
  S.contact(0.1, 0.1, CX, CZ, 0.45);
  // arm and detector
  var arm = new T.Group(); S.scene.add(arm); arm.position.set(CX, 0.0135, CZ);
  var bar = S.mesh(new T.BoxGeometry(RD - 0.03, 0.004, 0.012), M.alu); bar.position.set((RD - 0.03) / 2 + 0.02, 0, 0); arm.add(bar);
  var det = new T.Group(); S.scene.add(det);
  var can = S.mesh(new T.CylinderGeometry(0.0272, 0.0272, 0.055, 36), new T.MeshStandardMaterial({ color: 0xb9bec5, metalness: 0.85, roughness: 0.3 })); can.rotation.z = Math.PI / 2; can.position.set(-0.0275, 0, 0); det.add(can);
  var win = S.mesh(new T.CylinderGeometry(0.0255, 0.0255, 0.002, 36), new T.MeshStandardMaterial({ color: 0xe6e8ea, roughness: 0.15, metalness: 0.4 })); win.rotation.z = Math.PI / 2; win.position.set(0.001, 0, 0); det.add(win);
  var pmt = S.mesh(new T.CylinderGeometry(0.0285, 0.0285, 0.12, 36), new T.MeshStandardMaterial({ color: 0x2c3138, roughness: 0.5, metalness: 0.5 })); pmt.rotation.z = Math.PI / 2; pmt.position.set(-0.115, 0, 0); det.add(pmt);
  var dbase = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.04, 36), M.bakelite); dbase.rotation.z = Math.PI / 2; dbase.position.set(-0.195, 0, 0); det.add(dbase);
  var shield = S.mesh(new T.CylinderGeometry(0.036, 0.036, 0.06, 36, 1, true), leadM); shield.rotation.z = Math.PI / 2; shield.position.set(-0.03, 0, 0); shield.material = new T.MeshStandardMaterial({ color: 0x53565c, roughness: 0.72, metalness: 0.55, side: T.DoubleSide }); det.add(shield);
  var amG = makeSource(0x2a5db8); amG.scale.set(0.8, 0.8, 0.8); S.scene.add(amG);
  var potG = makePot(0.02, 0.17, 'SOURCE STORE'), tongs = makeTongs(0.16, 0.20);
  var AM_POT = new T.Vector3(0.02, 0.016, 0.17);
  var cable = null;
  function setAngle(th) {
    st.th = th; var r = th * Math.PI / 180;
    arm.rotation.y = -r; det.position.set(CX + RD * Math.cos(r), BY, CZ + RD * Math.sin(r)); det.rotation.y = Math.PI - r;
    if (st.am) amG.position.set(det.position.x - 0.014 * Math.cos(r), BY, det.position.z - 0.014 * Math.sin(r));
    if (cable) cable.set([[det.position.x - 0.235 * Math.cos(r), 0.07, det.position.z - 0.235 * Math.sin(r)], [0.0, 0.01, 0.1], [0.28, 0.05, -0.04]]);
  }
  setAngle(90);

  // ================================================================ MCA panel and monitor
  var mca = panel(0.34, 0.15, 0.2, function (x, w, h, X, Y, k) {
    x.fillStyle = '#f1efe8'; x.textAlign = 'left'; x.font = '700 ' + Math.round(0.0105 * k) + 'px "Public Sans", sans-serif'; x.fillText('MULTICHANNEL ANALYSER', X(-0.155), Y(0.055));
    x.font = '500 ' + Math.round(0.0075 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText(NCH + ' CHANNELS  ·  NaI(Tl) 2 in × 2 in' + (GATED ? '  ·  GATED' : ''), X(-0.155), Y(0.04));
    x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0085 * k) + 'px "Public Sans", sans-serif';
    x.fillText('TIME (s)', X(-0.155), Y(0.0)); x.fillText('COUNTS', X(-0.155), Y(-0.045)); x.textAlign = 'center'; x.fillText('START', X(0.12), Y(0.03)); x.fillText('ERASE', X(0.12), Y(-0.04));
  }, 0.42, -0.02, -0.2);
  var mStart = makeButton(mca, 0.12, 0.052, M.green), mErase = makeButton(mca, 0.12, -0.016, M.grey);
  var showTime = makeLcd(mca, -0.045, 0.0, 0.17, 0.03, 8), showCnt = makeLcd(mca, -0.045, -0.04, 0.17, 0.03, 8);
  var scr = makeScreen(0.36, -0.45, 0, 0.44, 0.27);
  cable = S.wire([[0, 0, 0], [0, 0, 0]], 'black'); setAngle(st.th);
  var hudA = S.hudCard('Detector angle'), hudE = S.hudCard('Peak energy'), hudN = S.hudCard('Counts');

  S.addApparatus('house', house, 'Cs-137 source in its lead housing', 'The sealed source sits behind a lead plug (the shutter). Open it with the tongs only for counting and close it afterwards. The collimator makes a narrow beam.');
  S.addApparatus('scat', rodG, SAMPLE, 'The scatterer is a small rod on the turntable: the photons it scatters through the angle θ are the ones the detector sees. It is treated as thin here (no absorption inside).');
  S.addApparatus('arm', arm, 'Graduated arm and detector table', 'The arm swings the detector about the scatterer; the angle is read on the protractor scale.');
  S.addApparatus('det', det, 'NaI(Tl) detector', 'A 2-inch scintillation crystal on a photomultiplier tube: each photon that stops in it makes a flash proportional to the energy left there. The lead collar cuts room background.');
  S.addApparatus('pot', potG, 'Lead source store', 'The Am-241 calibration disc is kept here, lid on.');
  S.addApparatus('tongs', tongs, 'Source tongs', 'Long tongs keep your hands away from the source.');
  S.addApparatus('mca', mca.g, 'Multichannel analyser', 'Sorts the pulses by height into channels: the spectrum. START counts for the preset time; ERASE clears it.');
  S.addApparatus('screen', scr.g, 'Live spectrum', 'The spectrum as it builds up. A fitted peak is marked with its width.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ================================================================ spectrum screen
  function eOf(ch) { return st.cal ? st.cal.a + st.cal.b * ch : null; }
  var lastPaint = 0;
  function paint(force) {
    var now = performance.now(); if (!force && now - lastPaint < 100) return; lastPaint = now;
    scr.tex.draw(function (x, w, h) {
      x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
      var box = { l: 90, r: w - 24, t: h * 0.1, b: h * 0.86 }, c = st.counts, n = NCH, i, ymax = 20;
      var cal = !!st.cal, xmin = 0, xmax = cal ? eOf(n) : n;
      if (c) for (i = 0; i < n; i++) { var v = Math.round(c[i] * st.prog); if (v > ymax) ymax = v; }
      ymax = ymax * 1.15;
      var fr = plotFrame(x, w, h, box, xmin, xmax, 0, ymax, cal ? 'energy (keV)' : 'channel', 'counts per channel', 5, 4);
      x.fillStyle = '#c9f5dc'; x.textAlign = 'left'; x.font = '600 ' + Math.round(h * 0.04) + 'px "JetBrains Mono", monospace';
      x.fillText(st.what || 'no spectrum', box.l + 8, box.t - 10);
      if (c) {
        x.strokeStyle = '#6dffa4'; x.lineWidth = 2; x.beginPath();
        for (i = 0; i < n; i++) { var X = fr.X(cal ? eOf(i + 0.5) : i + 0.5), Y = fr.Y(Math.round(c[i] * st.prog)); if (i) x.lineTo(X, Y); else x.moveTo(X, Y); }
        x.stroke();
        if (st.pk && st.fitted) {
          var xc = cal ? eOf(st.pk.ch) : st.pk.ch, hw = st.pk.fwhm_ch / 2 * (cal ? st.cal.b : 1);
          x.strokeStyle = 'rgba(255,210,74,.9)'; x.lineWidth = 2; x.setLineDash([5, 4]); x.beginPath(); x.moveTo(fr.X(xc), box.t); x.lineTo(fr.X(xc), box.b); x.stroke(); x.setLineDash([]);
          x.strokeStyle = 'rgba(255,210,74,.55)'; x.lineWidth = 8; x.beginPath(); x.moveTo(fr.X(xc - hw), box.b - 10); x.lineTo(fr.X(xc + hw), box.b - 10); x.stroke();
          x.fillStyle = '#ffd24a'; x.fillText('peak ch ' + st.pk.ch.toFixed(1) + (cal ? '  =  ' + xc.toFixed(1) + ' keV' : ''), box.l + 8, box.t + h * 0.06);
        }
      } else { x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.fillText('press START to count', (box.l + box.r) / 2, (box.t + box.b) / 2); }
    });
  }
  paint(true);

  // ================================================================ human actions
  function moveGroup(g, to, opts) {
    var from = g.position.clone(), lift = (opts && opts.lift) || 0.06;
    var f = function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k + lift * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k); };
    return S.hand.pinchMove(from, f, function (k) { g.position.copy(f(k)); tongs.position.set(g.position.x + 0.06, g.position.y, g.position.z + 0.05); }, { mode: 'side', ms: 900, reachMs: 600 }).then(function () { g.position.copy(to); });
  }
  function shutter(open) {
    if (busy() || st.shut === open) return Promise.resolve();
    var y0 = plug.position.y, y1 = open ? 0.17 : 0.06, pt = wpt(house, 0.078, 0.12, 0.0);
    return S.hand.pinchMove(pt, function (k) { return new T.Vector3(pt.x, pt.y + (y1 - y0) * k, pt.z); }, function (k) { plug.position.y = y0 + (y1 - y0) * k; }, { mode: 'side', ms: 700, reachMs: 600 })
      .then(function () { plug.position.y = y1; st.shut = open; beamM.opacity = open && st.scatIn !== undefined ? 0.35 : 0;
        S.say(open ? 'Shutter open: the beam runs to the scatterer. Keep out of the line of the beam.' : 'Shutter closed.'); S.render(); });
  }
  function scatterer(inn) {
    if (busy() || st.scatIn === inn) return Promise.resolve();
    if (inn && st.th < 20) { S.say('Turn the arm to 20 degrees or more before the scatterer goes back: at 0 degrees the detector looks straight at the beam.'); return Promise.resolve(); }
    return moveGroup(rodG, inn ? ROD_IN : ROD_OUT, { lift: 0.08 }).then(function () { st.scatIn = inn; S.say(inn ? 'Scatterer in the beam, on the turntable.' : 'Scatterer out of the beam, on its rest.'); S.render(); });
  }
  function amDisc(on) {
    if (busy() || st.am === on) return Promise.resolve();
    var r = st.th * Math.PI / 180, win = new T.Vector3(det.position.x - 0.014 * Math.cos(r), BY, det.position.z - 0.014 * Math.sin(r));
    if (on && st.shut) { S.say('Close the Cs-137 shutter first: the Am-241 lines must be counted alone.'); return Promise.resolve(); }
    if (on && st.scatIn) { S.say('Take the scatterer out of the way first.'); return Promise.resolve(); }
    return moveGroup(amG, on ? win : AM_POT.clone(), { lift: 0.07 }).then(function () { st.am = on;
      S.say(on ? 'Am-241 disc on the detector window, put there with the tongs.' : 'Am-241 disc back in the lead store.'); S.render(); });
  }
  function turnArm(th) {
    if (busy()) return Promise.resolve();
    if (!isFinite(th) || th < 0 || th > 150) { S.say('The arm turns between 0 and 150 degrees.'); return Promise.resolve(); }
    if (st.scatIn && th < 20) { S.say('With the scatterer in, keep the arm at 20 degrees or more: nearer the beam the detector would be flooded.'); return Promise.resolve(); }
    if (th === st.th) return Promise.resolve();
    var a0 = st.th, hp = function (k) { var a = (a0 + (th - a0) * k) * Math.PI / 180; return new T.Vector3(CX + RD * Math.cos(a), BY + 0.04, CZ + RD * Math.sin(a)); };
    return S.hand.pinchMove(hp(0), hp, function (k) { setAngle(a0 + (th - a0) * k); }, { mode: 'top', ms: 500 + 5 * Math.abs(th - a0), reachMs: 600 })
      .then(function () { setAngle(th); S.say('Detector at ' + th + ' degrees.'); S.render(); });
  }
  function expectedFor() {
    if (st.shut && st.am) { S.say('Counting a mixture: close the shutter, or take the Am-241 disc away.'); return null; }
    if (st.shut && st.scatIn) {
      if (st.th < 20) return null;
      var q = assign(p, { th: st.th }); return { ex: KN.expected(q), what: 'Cs-137 photons scattered through ' + st.th + '°' };
    }
    if (st.shut && !st.scatIn) {
      if (st.th !== 0) { S.say('With the scatterer out, the Cs-137 beam reaches the detector only at 0 degrees: swing the arm to 0 first.'); return null; }
      return { ex: KN.direct(p, p.E0, CAL_N), what: 'Cs-137 beam, direct' };
    }
    if (st.am && !st.shut) return { ex: KN.direct(p, AM, CAL_N), what: 'Am-241 59.54 keV' };
    return { ex: KN.line_spec(p, 100, 0), what: 'background only (no source in view)' };
  }
  function acquire() {
    if (busy()) return Promise.resolve(false);
    var e = expectedFor(); if (!e) { S.say(st.shut && st.th < 20 ? 'Turn the arm first.' : 'Set the bench up first.'); return Promise.resolve(false); }
    var c = KN.counts(e.ex, p.seed + 977 * st.idx); st.idx += 1;
    st.counts = c; st.what = e.what + '  ·  ' + p.t + ' s'; st.pk = null; st.fitted = false; st.recorded = false; st.counting = true; st.prog = 0; st.tlive = 0;
    return S.hand.tap(mStart, 'front').then(function () { return S.tween(1600, function (u) { st.prog = u; st.tlive = p.t * u; }); }).then(function () {
      st.prog = 1; st.tlive = p.t; st.counting = false; var tot = 0; for (var i = 0; i < c.length; i++) tot += c[i];
      S.say('Acquired ' + tot + ' counts in ' + p.t + ' s. Fit the peak to find its channel and area.'); S.render(); paint(true); return true;
    });
  }
  function fitPeak() {
    if (busy()) return false;
    if (!st.counts || st.prog < 1) { S.say('Acquire a spectrum first.'); return false; }
    st.pk = KN.find_peak(st.counts, p); st.fitted = true;
    S.say('Peak found at channel ' + st.pk.ch.toFixed(1) + ', width ' + st.pk.fwhm_ch.toFixed(1) + ' channels, net area ' + Math.round(st.pk.area) + ' counts.'); S.render(); paint(true); return true;
  }
  function recordCal(e0, name) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.fitted || st.recorded) { S.say('Fit a fresh peak first.'); return false; }
    var want = name === 'Cs' ? 'Cs-137 beam, direct' : 'Am-241 59.54 keV';
    if (st.what.indexOf(want) !== 0) { S.say('This spectrum is not the ' + (name === 'Cs' ? 'direct Cs-137 beam' : 'Am-241 line') + '.'); return false; }
    st.recorded = true;
    S.addRow({ kind: 'cal', name: name === 'Cs' ? 'Cs-137' : 'Am-241', E: e0, ch: st.pk.ch });
    var cs = S.rows.filter(function (r) { return r.kind === 'cal'; }), a = {}, i;
    cs.forEach(function (r) { a[r.name] = r; });
    if (a['Cs-137'] && a['Am-241']) { var b = (a['Cs-137'].E - a['Am-241'].E) / (a['Cs-137'].ch - a['Am-241'].ch); st.cal = { a: a['Am-241'].E - b * a['Am-241'].ch, b: b };
      S.say('Energy scale: E = ' + st.cal.a.toFixed(2) + ' + ' + st.cal.b.toFixed(4) + ' × channel (keV).'); }
    else S.say('Calibration point written down.');
    paint(true); return true;
  }
  function recordScatter() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.cal) { S.say('Calibrate the energy scale first, with the two known lines.'); return false; }
    if (!st.fitted || st.recorded) { S.say('Fit a fresh peak first.'); return false; }
    if (st.what.indexOf('Cs-137 photons scattered') !== 0) { S.say('This spectrum is not a scattered one: put the scatterer in the beam and open the shutter.'); return false; }
    if (S.rows.some(function (r) { return r.kind === 'sc' && r.th === st.th; })) { S.say('That angle is already written down.'); return false; }
    st.recorded = true; var E = eOf(st.pk.ch);
    var pref = p.t * KN.flux(p) * p.ne25 * 1e25 * KN.omega(p), ds = st.pk.area / (pref * KN.eff_card(CARD, E));
    S.addRow({ kind: 'sc', th: st.th, ch: st.pk.ch, Ep: E, area: st.pk.area, ds: ds, kn: KN.kn(p.E0, st.th) });
    S.say('Written in your record book: ' + st.th + '°, E′ = ' + E.toFixed(1) + ' keV.'); paint(true); return true;
  }
  function eraseNow() { if (busy()) return Promise.resolve(); return S.hand.tap(mErase, 'front').then(function () { st.counts = null; st.what = ''; st.pk = null; st.fitted = false; st.prog = 0; st.tlive = 0; S.say('Spectrum cleared.'); S.render(); paint(true); }); }
  function sc() { return S.rows.filter(function (r) { return r.kind === 'sc'; }); }
  function peaksOf() { return sc().map(function (r) { return [r.th, r.Ep, r.area]; }); }
  function result() {
    var rows = peaksOf(); if (rows.length < 5) return null;
    var a = KN.analyse(p, rows);
    if (TASK === 1) return { label: 'Total Compton cross-section per electron', value: a.sigma, unit: 'barn', digits: 3, truth: HK.TEXTBOOK.ph3_compton_sigma(p),
      note: 'Your d sigma/d Omega came out ' + a.ratio.toFixed(3) + ' times the Klein-Nishina value on average, which is the ratio the unmeasured ends were scaled by. Integrating 2 pi sin(theta) d sigma/d Omega over the sphere gives ' + a.sigma.toFixed(3) + ' barn (1 barn = 1e-28 m²); the Klein-Nishina formula gives 0.256 barn at 662 keV.' };
    return { label: 'Electron rest energy', value: a.mc2, unit: 'keV', digits: 1, truth: HK.TEXTBOOK.ph3_compton_mc2(p),
      note: 'The slope of 1/E′ against (1 − cos θ) is 1/(m c²): ' + a.mc2.toFixed(1) + ' keV. The intercept is 1/E0, the reciprocal of the incident photon energy.' };
  }
  var xk = function (r) { return 1 - Math.cos(r.th * Math.PI / 180); };

  return {
    camera: { pos: [0.02, 1.0, 1.42], look: [0.02, 0.03, -0.14] },
    views: { house: [[-0.5, 0.3, 0.2], [-0.46, 0.08, -0.15]], scat: [[-0.12, 0.25, 0.1], [-0.12, 0.03, -0.15]], arm: [[-0.05, 0.4, 0.4], [-0.12, 0.0, -0.05]], det: [[0.0, 0.2, 0.15], [-0.05, 0.075, -0.0]],
      pot: [[0.02, 0.2, 0.4], [0.02, 0.02, 0.17]], tongs: [[0.16, 0.2, 0.42], [0.16, 0.0, 0.2]], mca: [[0.5, 0.25, 0.5], [0.42, 0.06, 0.08]], screen: [[0.3, 0.3, 0.12], [0.36, 0.17, -0.45]],
      bench: [[0.02, 1.0, 1.42], [0.02, 0.03, -0.14]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'A photon that scatters off a free electron at rest gives some of its energy to the electron, and how much depends only on the angle through which it is scattered. The scattered photon has less energy, and its wavelength grows by the Compton wavelength h/mc times (1 − cos θ).',
      formula: "1/E′ = 1/E₀ + (1 − cos θ) / (m c²)",
      formulaNote: "E₀ = 661.657 keV (Cs-137). How many photons go through θ: dσ/dΩ = (r_e²/2)(E′/E₀)²(E′/E₀ + E₀/E′ − sin²θ)",
      more: ['A straight line of 1/E′ against (1 − cos θ) has slope 1/(m c²): the electron rest energy comes out of photon energies alone.',
        'The scatterer’s electrons are bound, but 662 keV is far above their binding energy, so they scatter as if free.',
        'The photopeak of the scattered line sits on a Compton shelf in the NaI crystal; the peak is found by its centroid above a baseline, and its net area is the count.'],
      precautions: 'Cs-137 is a sealed source behind a lead shutter. Open the shutter only while counting, keep out of the beam line, use the tongs for the Am-241 disc and return it to its locked store.' },
    book: { title: 'Expt. — Compton scattering',
      lines: ['Aim: ' + (TASK ? 'differential and total cross-section.' : 'E′ against θ; electron rest energy.'), 'Scatterer: ' + SAMPLE, 'Source: Cs-137, E₀ = 661.657 keV; calibration Am-241 59.54 keV',
        GATED ? 'Method: gated by the scatterer’s pulse (coincidence).' : 'Method: scattered photopeak against angle.', 'Counting time ' + p.t + ' s'],
      columns: [{ label: 'θ', get: function (r) { return r.kind === 'sc' ? r.th : r.name; } }, { label: 'Ch', get: function (r) { return r.ch.toFixed(1); } },
        { label: "E′ keV", get: function (r) { return r.kind === 'sc' ? r.Ep.toFixed(1) : r.E; } },
        { label: 'Area', get: function (r) { return r.kind === 'sc' ? Math.round(r.area) : ''; } },
        { label: 'dσ/dΩ ×10⁻³⁰', get: function (r) { return r.kind === 'sc' ? (r.ds * 1e30).toFixed(2) : ''; } }] },
    graph: { x: function (r) { return r.kind === 'sc' ? xk(r) : NaN; }, y: function (r) { return r.kind === 'sc' ? 1000 / r.Ep : NaN; }, xlabel: '1 − cos θ', ylabel: "1000 / E′ (MeV⁻¹)",
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: TASK ? 0.06 : 0.03,
    resultNote: 'The line is straight because the scattering is a one-to-one relation between angle and energy.',
    chips: ['Why does the photon lose energy?', 'What is the Compton shelf?', 'Why 1/E′ against 1 − cos θ?', 'Check my readings', 'Why is the scatterer treated as thin?'],
    viva: [['The scattered photon has the least energy when it is scattered through', ['180 degrees', '90 degrees', '0 degrees'], 0, 'E′ = E₀/(1 + (E₀/mc²)(1 − cos θ)) is smallest at θ = 180°.'],
      ['The slope of 1/E′ against (1 − cos θ) is', ['1/(m c²)', 'm c²', '1/E₀'], 0, 'From 1/E′ − 1/E₀ = (1 − cos θ)/(m c²).'],
      ['The Am-241 line is counted with the shutter closed so that', ['Only one line is in the spectrum', 'The detector is cooler', 'The scatterer is not hit'], 0, 'Two sources at once would put two sets of lines in one spectrum.']],
    askState: function () {
      return { experiment: TASK ? 'Compton cross-section' : 'Compton scattering energy against angle', scatterer: SAMPLE, angle_deg: st.th, shutter_open: st.shut, scatterer_in_beam: st.scatIn,
        am241_on_detector: st.am, calibrated: !!st.cal, spectrum: st.what, fitted_peak_channel: st.pk ? +st.pk.ch.toFixed(1) : null, scattering_readings: sc().length };
    },
    steps: [
      { id: 'cal', title: 'Energy calibration', view: 'bench', render: function (u) {
          u.h2('Calibrate the energy scale');
          u.p('Two known lines fix the scale E = a + b × channel: the direct Cs-137 beam (661.657 keV) and an Am-241 disc (59.54 keV).');
          u.p('Counting time ' + p.t + ' s each. Cs-137 first: the scatterer out of the way, the arm at 0 degrees, the shutter open.');
          u.task('1. Scatterer out, arm at 0°', !st.scatIn && st.th === 0, !st.scatIn && st.th === 0 ? 'Done' : 'Not yet')
            .add(u.row(u.button('Lift the scatterer out', function () { S.focus('scat'); scatterer(false); }, st.scatIn, !st.scatIn || S.hand.busy),
              u.button('Arm to 0°', function () { S.focus('arm'); turnArm(0); }, st.th !== 0, st.th === 0 || S.hand.busy)));
          u.task('2. Cs-137 beam: open the shutter, count, fit, record', S.rows.some(function (r) { return r.name === 'Cs-137'; }), st.what || 'Not counted')
            .add(u.row(u.button('Open shutter', function () { S.focus('house'); shutter(true); }, !st.shut, st.shut || S.hand.busy),
              u.button('START (' + p.t + ' s)', function () { acquire(); }, true, S.hand.busy)))
            .add(u.row(u.button('Fit the peak', function () { fitPeak(); }, false, S.hand.busy), u.button('Record as 661.657 keV', function () { recordCal(p.E0, 'Cs'); }, false, S.hand.busy)));
          u.task('3. Am-241: close the shutter, disc on the window, count, fit, record', S.rows.some(function (r) { return r.name === 'Am-241'; }), st.am ? 'Disc on the window' : 'Disc in the store')
            .add(u.row(u.button('Close shutter', function () { shutter(false); }, st.shut, !st.shut || S.hand.busy), u.button('Am-241 disc on', function () { S.focus('pot'); amDisc(true); }, !st.am && !st.shut, st.am || S.hand.busy)))
            .add(u.row(u.button('START (' + p.t + ' s)', function () { acquire(); }, true, S.hand.busy), u.button('Fit the peak', function () { fitPeak(); }, false, S.hand.busy)))
            .add(u.button('Record as 59.54 keV', function () { recordCal(AM, 'Am'); }, false, S.hand.busy));
          u.live(function () { return st.cal ? 'E = ' + st.cal.a.toFixed(2) + ' + ' + st.cal.b.toFixed(4) + ' × channel' : 'Not calibrated yet'; });
          u.next('Next: scatter at seven angles', !!st.cal);
        },
        ok: function () { return !!st.cal; },
        auto: function () {
          return scatterer(false).then(function () { return turnArm(0); }).then(function () { return shutter(true); }).then(function () { return acquire(); })
            .then(function () { fitPeak(); recordCal(p.E0, 'Cs'); }).then(function () { return shutter(false); }).then(function () { return amDisc(true); })
            .then(function () { return acquire(); }).then(function () { fitPeak(); recordCal(AM, 'Am'); }).then(function () { return amDisc(false); });
        } },
      { id: 'scatter', title: 'Scattered photons', view: 'arm', render: function (u) {
          u.h2('Count the scattered photons at seven angles');
          u.p('Put the scatterer in the beam, open the shutter, then for each angle turn the arm, count, fit the scattered photopeak and record it: 20, 40, 60, 80, 100, 120 and 140 degrees.');
          u.p('Efficiency card (photopeak efficiency of the crystal, %): ' + [100, 200, 300, 400, 500, 600, 700].map(function (e) { return e + ' keV ' + (100 * KN.eff_card(CARD, e)).toFixed(1); }).join(' · ') + '. It is needed to turn the net area into a cross-section.');
          u.p('Turn the arm to 20° first: the scatterer cannot go back while the detector is at 0°, in the beam.');
          u.row(u.button('Scatterer in', function () { S.focus('scat'); scatterer(true); }, !st.scatIn, st.scatIn || S.hand.busy),
            u.button('Open shutter', function () { shutter(true); }, !st.shut, st.shut || S.hand.busy));
          u.row.apply(u, [20, 40, 60, 80, 100, 120, 140].map(function (a) { return u.button(a + '°', function () { turnArm(a); }, st.th === a, S.hand.busy); }));
          u.row(u.button('START (' + p.t + ' s)', function () { acquire(); }, true, S.hand.busy), u.button('Fit the peak', function () { fitPeak(); }, false, S.hand.busy),
            u.button('Record', function () { recordScatter(); }, false, S.hand.busy));
          u.live(function () { return 'Arm at ' + st.th + '°  ·  ' + (st.pk && st.fitted && st.cal ? 'peak at ' + eOf(st.pk.ch).toFixed(1) + ' keV' : 'no peak fitted') + '  ·  ' + sc().length + ' of 7 recorded'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', sc().length >= 7);
        },
        ok: function () { return sc().length >= 7; },
        auto: function () {
          var ch = turnArm(20).then(function () { return scatterer(true); }).then(function () { return shutter(true); });
          [20, 40, 60, 80, 100, 120, 140].forEach(function (a) { ch = ch.then(function () { return turnArm(a); }).then(function () { return acquire(); }).then(function () { fitPeak(); recordScatter(); }); });
          return ch.then(function () { return shutter(false); });
        } }
    ],
    tick: function () {
      showTime(st.tlive.toFixed(0)); showCnt(String(st.counts ? Math.round((function () { var t = 0; for (var i = 0; i < st.counts.length; i++) t += st.counts[i]; return t; })() * st.prog) : 0));
      hudA.set(st.th + '°'); hudE.set(st.pk && st.fitted && st.cal ? eOf(st.pk.ch).toFixed(1) + ' keV' : '—'); hudN.set(st.pk && st.fitted ? String(Math.round(st.pk.area)) : '—');
      beamM.opacity = st.shut ? 0.35 : 0;
      if (st.counting) paint(false);
    }
  };
});
