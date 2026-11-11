/* Prayogshala studio module: ALPHA SPECTROMETER BENCH (M.Sc. / PhD nuclear physics).
   A silicon surface-barrier detector facing a sealed alpha source on a rail, under a glass bell jar on a base
   plate, with a rotary pump, a vacuum controller (pressure gauge and air-inlet valve), a gold foil on a lever
   and a multichannel analyser with a live spectrum. The energy scale is set on two sources in vacuum, then air is
   let in step by step and the peak is followed down in energy; E^(3/2) against the air path gives the range, and a
   gold foil gives a stopping power.
   Physics: the `ph3_alpha` kernel of packs/ph3_nuc.js (Bragg-Kleeman range rule, straggling). Counts are Poisson
   numbers from the lab's own seed. */
HoolaStudio.define('ph3-alpha', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KN = HK.K.ph3_alpha, assign = HK.assign;
  var p = HK.paramsFor('ph3_alpha', S.lab.params);
  var V_ = S.lab.variant || {}, SRC = Math.round(p.src), NAMES = ['Am-241', 'Pu-239'], NOMS = [KN.LINES[0][0][0], KN.LINES[1][0][0]];
  var SAMPLE = V_.sample || NAMES[SRC] + ' sealed alpha source';
  var NCH = Math.round(p.nch), GAIN = p.gain, FOIL = 1.0, PRS = [0, 100, 200, 300, 400, 500, 600, 700];
  var CX = -0.22, CZ = -0.18, BY = 0.03;
  var st = { open: false, src: null, pr: 1013, foil: false, counting: false, prog: 0, counts: null, what: '', meta: null, pk: null, fitted: false, recorded: true, tlive: 0, idx: 0, cal: null, valve: 0 };
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

  // ================================================================ chamber
  var base = new T.Group(); S.scene.add(base); base.position.set(CX, 0, CZ);
  var plate = S.mesh(new T.CylinderGeometry(0.105, 0.11, 0.014, 48), M.steel); plate.position.y = 0.007; base.add(plate);
  var oring = S.mesh(new T.TorusGeometry(0.087, 0.0035, 8, 48), M.rubber); oring.rotation.x = Math.PI / 2; oring.position.y = 0.0145; base.add(oring);
  var floor = S.mesh(new T.CylinderGeometry(0.08, 0.08, 0.002, 40), new T.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.4, metalness: 0.8 })); floor.position.y = 0.015; base.add(floor);
  // detector on its mount at the left end, facing +x
  var det = new T.Group(); det.position.set(-0.062, 0.03, 0); base.add(det);
  var dbody = S.mesh(new T.CylinderGeometry(0.016, 0.016, 0.03, 28), M.brass); dbody.rotation.z = Math.PI / 2; dbody.position.x = -0.015; det.add(dbody);
  var dface = S.mesh(new T.CylinderGeometry(0.0125, 0.0125, 0.0015, 28), new T.MeshStandardMaterial({ color: 0xe6c25a, roughness: 0.2, metalness: 1 })); dface.rotation.z = Math.PI / 2; dface.position.x = 0.001; det.add(dface);
  var dpost = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.02, 12), M.brass); dpost.position.set(-0.02, -0.014, 0); det.add(dpost);
  // rail with its scale in centimetres from the detector face
  var rail = S.mesh(new T.BoxGeometry(0.13, 0.006, 0.014), M.alu); rail.position.set(-0.062 + 0.065, 0.0185, 0.0); base.add(rail);
  var rtex = S.canvasTex(1300, 140, function (x, w, h) { x.fillStyle = '#d8dbde'; x.fillRect(0, 0, w, h); x.fillStyle = '#16171a'; x.font = '600 56px "Public Sans", sans-serif'; x.textAlign = 'center';
    for (var cm = 0; cm <= 12; cm++) { var xx = 12 + cm / 13 * (w - 24); x.fillRect(xx, 0, 4, cm % 2 ? 40 : 60); if (cm % 2 === 0) x.fillText(String(cm), xx, 120); } });
  var rscale = new T.Mesh(new T.PlaneGeometry(0.13, 0.0135), new T.MeshStandardMaterial({ map: rtex, roughness: 0.6 })); rscale.rotation.x = -Math.PI / 2; rscale.position.set(-0.062 + 0.065, 0.0216, 0.0); base.add(rscale);
  var holderG = new T.Group(); holderG.position.set(-0.062 + p.d, 0.02, 0); base.add(holderG);
  var hpost = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.014, 12), M.chrome); hpost.position.y = 0.007; holderG.add(hpost);
  var hcup = S.mesh(new T.CylinderGeometry(0.0095, 0.0095, 0.003, 20), M.alu); hcup.position.y = 0.0155; holderG.add(hcup);
  var SRC_AT = new T.Vector3(CX - 0.062 + p.d, 0.0225 + 0.012, CZ);
  // gold foil on a swinging arm, worked from a knob outside the jar
  var foilArm = new T.Group(); foilArm.position.set(-0.062 + 0.012, 0.0, -0.032); base.add(foilArm);
  var fpost = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.03, 12), M.chrome); fpost.position.y = 0.017; foilArm.add(fpost);
  var farm = S.mesh(new T.BoxGeometry(0.003, 0.002, 0.034), M.alu); farm.position.set(0, 0.032, 0.017); foilArm.add(farm);
  var fring = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.002, 24), new T.MeshStandardMaterial({ color: 0xc9a23a, roughness: 0.3, metalness: 1 })); fring.rotation.z = Math.PI / 2; fring.position.set(0, 0.03, 0.034); foilArm.add(fring);
  var ffoil = S.mesh(new T.CircleGeometry(0.0075, 24), new T.MeshStandardMaterial({ color: 0xf2d27a, roughness: 0.1, metalness: 1, side: T.DoubleSide })); ffoil.rotation.y = Math.PI / 2; ffoil.position.set(0.0012, 0.03, 0.034); foilArm.add(ffoil);
  var flbl = S.label('Au 1.0 mg/cm²', { w: 0.05, ratio: 0.2, color: '#e8e8ea', bg: '#2b2f36' }); flbl.rotation.set(-Math.PI / 2, 0, 0); flbl.position.set(-0.062 + 0.012, 0.0165, -0.075); base.add(flbl);
  var FA_OUT = -Math.PI / 2 * 0.0, FA_IN = 0.0;
  function foilAngle(on) { return on ? 0.0 : -1.35; }
  foilArm.rotation.y = foilAngle(false);
  var lever = new T.Group(); lever.position.set(-0.062 + 0.012, 0.012, -0.105); base.add(lever);
  var lk = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.014, 20), new T.MeshStandardMaterial({ map: knurl, roughness: 0.5 })); lk.position.y = 0.007; lever.add(lk);
  var lptr = S.mesh(new T.BoxGeometry(0.003, 0.002, 0.016), M.white, false); lptr.position.set(0, 0.0145, 0.005); lever.add(lptr);
  lever.rotation.y = foilAngle(false);
  // bell jar
  var jar = new T.Group(); S.scene.add(jar); var JAR_DOWN = new T.Vector3(CX, 0.014, CZ), JAR_UP = new T.Vector3(CX + 0.16, 0.3, CZ + 0.06); jar.position.copy(JAR_DOWN);
  var jg = S.mesh(new T.CylinderGeometry(0.087, 0.087, 0.15, 48, 1, true), new T.MeshPhysicalMaterial({ color: 0xcfe6ee, roughness: 0.05, metalness: 0.0, transmission: 0.0, transparent: true, opacity: 0.2, side: T.DoubleSide, depthWrite: false })); jg.position.y = 0.075; jar.add(jg);
  var jtop = S.mesh(new T.SphereGeometry(0.087, 40, 12, 0, Math.PI * 2, 0, Math.PI / 2), new T.MeshPhysicalMaterial({ color: 0xcfe6ee, roughness: 0.05, transparent: true, opacity: 0.2, side: T.DoubleSide, depthWrite: false })); jtop.position.y = 0.15; jar.add(jtop);
  var jrim = S.mesh(new T.TorusGeometry(0.087, 0.004, 8, 48), M.steel); jrim.rotation.x = Math.PI / 2; jrim.position.y = 0.0; jar.add(jrim);
  var jknob = S.mesh(new T.CylinderGeometry(0.012, 0.014, 0.02, 20), M.bakelite); jknob.position.y = 0.245; jar.add(jknob);
  S.contact(0.3, 0.3, CX, CZ, 0.5);
  // pump and hose
  var pump = new T.Group(); S.scene.add(pump); pump.position.set(-0.6, 0, -0.34);
  var pbody = S.rounded(0.2, 0.1, 0.09, 0.01, new T.MeshStandardMaterial({ color: 0x3a5b8a, roughness: 0.5, metalness: 0.3 })); pbody.rotation.x = -Math.PI / 2; pbody.position.y = 0.045 + 0.004; pump.add(pbody);
  var pmotor = S.mesh(new T.CylinderGeometry(0.04, 0.04, 0.09, 28), new T.MeshStandardMaterial({ color: 0x24262b, roughness: 0.5, metalness: 0.5 })); pmotor.rotation.z = Math.PI / 2; pmotor.position.set(0.14, 0.05, 0); pump.add(pmotor);
  var plb = S.label('ROTARY PUMP', { w: 0.09, ratio: 0.2, color: '#f1efe8', bg: '#26334a' }); plb.position.set(0, 0.055, 0.0505); pump.add(plb);
  S.contact(0.34, 0.16, -0.54, -0.34, 0.5);
  var hosePts = [new T.Vector3(-0.58, 0.04, -0.28), new T.Vector3(-0.5, 0.012, -0.24), new T.Vector3(-0.36, 0.008, -0.22), new T.Vector3(-0.27, 0.012, -0.19)];
  var hose = S.mesh(new T.TubeGeometry(new T.CatmullRomCurve3(hosePts), 40, 0.007, 10, false), new T.MeshStandardMaterial({ color: 0x3a3d42, roughness: 0.6 })); S.scene.add(hose);
  // vacuum controller: pressure LCD, pump switch, air-inlet valve
  var vac = panel(0.32, 0.14, 0.2, function (x, w, h, X, Y, k) {
    x.fillStyle = '#f1efe8'; x.textAlign = 'left'; x.font = '700 ' + Math.round(0.0105 * k) + 'px "Public Sans", sans-serif'; x.fillText('VACUUM CONTROL', X(-0.15), Y(0.055));
    x.font = '700 ' + Math.round(0.0085 * k) + 'px "Public Sans", sans-serif'; x.fillText('PRESSURE (mbar)', X(-0.15), Y(0.02)); x.fillText('AIR INLET', X(0.045), Y(0.055)); x.textAlign = 'center'; x.fillText('PUMP', X(-0.1), Y(-0.045));
    var i, th, R = 0.034;
    for (i = 0; i <= 10; i++) { th = (225 - 270 * i / 10) * Math.PI / 180; x.strokeStyle = '#f1efe8'; x.lineWidth = i % 5 === 0 ? 4 : 2; x.beginPath();
      x.moveTo(X(0.09 + Math.cos(th) * (R + 0.004)), Y(-0.005 + Math.sin(th) * (R + 0.004))); x.lineTo(X(0.09 + Math.cos(th) * (R + 0.012)), Y(-0.005 + Math.sin(th) * (R + 0.012))); x.stroke();
      if (i % 5 === 0) { x.font = '600 ' + Math.round(0.0065 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText(String(i * 100), X(0.09 + Math.cos(th) * (R + 0.022)), Y(-0.005 + Math.sin(th) * (R + 0.022)) + 4); } }
  }, 0.26, 0.05, -0.12);
  var vacLcd = makeLcd(vac, -0.075, -0.005, 0.12, 0.034, 6), pumpB = makeButton(vac, -0.1, -0.03, M.green);
  var valveK = makeKnob(vac, 0.09, -0.005);
  function valveRot(v) { return (225 - 270 * Math.min(1000, Math.max(0, v)) / 1000) * Math.PI / 180 - Math.PI / 2; }
  valveK.rotation.z = valveRot(0);
  var mca = panel(0.3, 0.15, 0.2, function (x, w, h, X, Y, k) {
    x.fillStyle = '#f1efe8'; x.textAlign = 'left'; x.font = '700 ' + Math.round(0.0105 * k) + 'px "Public Sans", sans-serif'; x.fillText('MULTICHANNEL ANALYSER', X(-0.135), Y(0.055));
    x.font = '500 ' + Math.round(0.0075 * k) + 'px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText(NCH + ' CHANNELS  ·  Si SURFACE BARRIER', X(-0.135), Y(0.04));
    x.fillStyle = '#f1efe8'; x.font = '700 ' + Math.round(0.0085 * k) + 'px "Public Sans", sans-serif'; x.fillText('TIME (s)', X(-0.135), Y(0.0)); x.fillText('COUNTS', X(-0.135), Y(-0.045));
    x.textAlign = 'center'; x.fillText('START', X(0.105), Y(0.03)); x.fillText('ERASE', X(0.105), Y(-0.04));
  }, 0.66, -0.14, -0.22);
  var mStart = makeButton(mca, 0.105, 0.052, M.green), mErase = makeButton(mca, 0.105, -0.016, M.grey);
  var showTime = makeLcd(mca, -0.03, 0.0, 0.15, 0.03, 8), showCnt = makeLcd(mca, -0.03, -0.04, 0.15, 0.03, 8);
  var scr = makeScreen(0.3, -0.5, 0, 0.44, 0.27);
  S.wire([[CX - 0.1, 0.012, CZ - 0.05], [0.1, 0.01, -0.28], [0.26, 0.06, -0.12]], 'black');
  S.wire([[0.22, 0.05, -0.1], [0.4, 0.02, -0.02], [0.58, 0.06, -0.12]], 'blue');
  var potG = makePot(-0.02, 0.12, 'SOURCE STORE'), tongs = makeTongs(0.12, 0.16);
  var discs = [makeSource(0xb8322a), makeSource(0x2a5db8)], POT_AT = [new T.Vector3(-0.035, 0.016, 0.12), new T.Vector3(-0.005, 0.016, 0.12)];
  discs.forEach(function (d, i) { S.scene.add(d); d.position.copy(POT_AT[i]); });
  var hudP = S.hudCard('Pressure'), hudE = S.hudCard('Peak energy'), hudN = S.hudCard('Counts');

  S.addApparatus('jar', jar, 'Bell jar and base plate', 'The glass jar sits on an O-ring. Lift it straight up to reach the source; the chamber is at atmospheric pressure whenever it is open.');
  S.addApparatus('det', det, 'Silicon surface-barrier detector', 'A thin gold layer over a silicon junction: each alpha particle that stops in the silicon makes a pulse proportional to its energy. Never touch the face.');
  S.addApparatus('rail', rail, 'Source rail', 'The source sits on a rail 3.0 cm from the detector face. The distance is fixed for every reading.');
  S.addApparatus('foil', foilArm, 'Gold foil on an arm', 'A gold foil of known mass thickness (1.0 mg/cm²), swung in front of the source from the knob outside the jar.');
  S.addApparatus('pump', pump, 'Rotary pump', 'Takes the air out of the chamber so that the alpha particles lose no energy on the way.');
  S.addApparatus('vac', vac.g, 'Vacuum controller', 'The gauge reads the pressure in the chamber; the PUMP switch pumps down, and the AIR INLET valve lets air in to the pressure you set.');
  S.addApparatus('pot', potG, 'Lead source store', 'The sealed alpha sources are kept here, lid on, when not in use.');
  S.addApparatus('tongs', tongs, 'Source tongs', 'Alpha sources are sealed but fragile; the tongs keep your hands off the source.');
  S.addApparatus('mca', mca.g, 'Multichannel analyser', 'Sorts the pulses by height into channels.');
  S.addApparatus('screen', scr.g, 'Live spectrum', 'The alpha spectrum as it builds up.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  function eOf(ch) { return st.cal ? st.cal.a + st.cal.b * ch : null; }
  var lastPaint = 0;
  function paint(force) {
    var now = performance.now(); if (!force && now - lastPaint < 100) return; lastPaint = now;
    scr.tex.draw(function (x, w, h) {
      x.fillStyle = '#0d1a14'; x.fillRect(0, 0, w, h);
      var box = { l: 90, r: w - 24, t: h * 0.1, b: h * 0.86 }, c = st.counts, n = NCH, i, ymax = 20, cal = !!st.cal, xmax = cal ? eOf(n) / 1000 : n, xmin = 0;
      if (c) for (i = 0; i < n; i++) { var v = Math.round(c[i] * st.prog); if (v > ymax) ymax = v; }
      ymax *= 1.15;
      var fr = plotFrame(x, w, h, box, 0, xmax, 0, ymax, cal ? 'alpha energy (MeV)' : 'channel', 'counts per channel', 6, 4, function (v) { return cal ? v.toFixed(1) : String(Math.round(v)); });
      x.fillStyle = '#c9f5dc'; x.textAlign = 'left'; x.font = '600 ' + Math.round(h * 0.04) + 'px "JetBrains Mono", monospace'; x.fillText(st.what || 'no spectrum', box.l + 8, box.t - 10);
      if (c) {
        x.strokeStyle = '#6dffa4'; x.lineWidth = 2; x.beginPath();
        for (i = 0; i < n; i++) { var X = fr.X(cal ? eOf(i + 0.5) / 1000 : i + 0.5), Y = fr.Y(Math.round(c[i] * st.prog)); if (i) x.lineTo(X, Y); else x.moveTo(X, Y); }
        x.stroke();
        if (st.pk && st.fitted) {
          var xc = cal ? eOf(st.pk.ch) / 1000 : st.pk.ch, hw = st.pk.fwhm_ch / 2 * (cal ? st.cal.b / 1000 : 1);
          x.strokeStyle = 'rgba(255,210,74,.9)'; x.lineWidth = 2; x.setLineDash([5, 4]); x.beginPath(); x.moveTo(fr.X(xc), box.t); x.lineTo(fr.X(xc), box.b); x.stroke(); x.setLineDash([]);
          x.strokeStyle = 'rgba(255,210,74,.55)'; x.lineWidth = 8; x.beginPath(); x.moveTo(fr.X(xc - hw), box.b - 10); x.lineTo(fr.X(xc + hw), box.b - 10); x.stroke();
          x.fillStyle = '#ffd24a'; x.fillText('peak ch ' + st.pk.ch.toFixed(1) + (cal ? '  =  ' + (xc * 1000).toFixed(0) + ' keV' : ''), box.l + 8, box.t + h * 0.06);
        }
      } else { x.fillStyle = '#6aa88a'; x.textAlign = 'center'; x.fillText('press START to count', (box.l + box.r) / 2, (box.t + box.b) / 2); }
    });
  }
  paint(true);

  // ================================================================ human actions
  function moveGroup(g, to, lift) {
    var from = g.position.clone(), f = function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k + (lift || 0.06) * Math.sin(Math.PI * k), from.z + (to.z - from.z) * k); };
    return S.hand.pinchMove(from, f, function (k) { g.position.copy(f(k)); }, { mode: 'side', ms: 900, reachMs: 600 }).then(function () { g.position.copy(to); });
  }
  function jarLift(up) {
    if (busy() || st.open === up) return Promise.resolve();
    var from = jar.position.clone(), to = up ? JAR_UP : JAR_DOWN, hp = new T.Vector3(CX, 0.26, CZ);
    return S.hand.pinchMove(hp.clone().add(new T.Vector3(0, 0, 0)), function (k) { return new T.Vector3(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k + 0.26 - 0.014, from.z + (to.z - from.z) * k); },
      function (k) { jar.position.set(from.x + (to.x - from.x) * k, from.y + (to.y - from.y) * k, from.z + (to.z - from.z) * k); }, { mode: 'top', ms: 1000, reachMs: 700 })
      .then(function () { jar.position.copy(to); st.open = up; if (up) { st.pr = 1013; st.counts = null; st.what = ''; st.fitted = false; } S.say(up ? 'Bell jar lifted off: the chamber is at atmospheric pressure.' : 'Bell jar down on its O-ring. Now pump out the air.'); S.render(); });
  }
  function putSource(i) {
    if (busy()) return Promise.resolve();
    if (!st.open) { S.say('Lift the bell jar first.'); return Promise.resolve(); }
    if (st.src === i) return Promise.resolve();
    var ch = Promise.resolve();
    if (st.src !== null) ch = ch.then(function () { return moveGroup(discs[st.src], POT_AT[st.src], 0.07); });
    return ch.then(function () { return moveGroup(discs[i], SRC_AT, 0.08); }).then(function () { st.src = i; S.say(NAMES[i] + ' on the rail, 3.0 cm from the detector, put there with the tongs.'); S.render(); });
  }
  function takeSource() {
    if (busy() || st.src === null) return Promise.resolve();
    if (!st.open) { S.say('Lift the bell jar first.'); return Promise.resolve(); }
    var i = st.src; return moveGroup(discs[i], POT_AT[i], 0.08).then(function () { st.src = null; S.say(NAMES[i] + ' back in the lead store.'); S.render(); });
  }
  function setPr(target, ms) { var p0 = st.pr; return S.tween(ms, function (k) { st.pr = p0 + (target - p0) * k; }).then(function () { st.pr = target; }); }
  function pumpDown() {
    if (busy()) return Promise.resolve();
    if (st.open) { S.say('Put the bell jar down before you pump.'); return Promise.resolve(); }
    return S.hand.tap(pumpB, 'front').then(function () { return setPr(0.1, 1500); }).then(function () { S.say('Pumped down: the chamber is at about 0.1 mbar, alpha particles lose no energy on the way.'); S.render(); });
  }
  function airTo(mbar) {
    if (busy()) return Promise.resolve();
    if (st.open) { S.say('Put the bell jar down first: the chamber must be closed to hold a pressure.'); return Promise.resolve(); }
    if (!isFinite(mbar) || mbar < 0 || mbar > 800) { S.say('Set a pressure between 0 and 800 mbar.'); return Promise.resolve(); }
    if (mbar < 1) return pumpDown();
    var v0 = st.valve, pt = wpt(vac.g, 0.09, 0.004 + vac.H / 2 - 0.005, vac.FZ + 0.024);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { var v = v0 + (mbar - v0) * k; valveK.rotation.z = valveRot(v); S.hand.group.rotation.y = -(valveRot(v) - valveRot(v0)) * 0.3; }, { mode: 'front', ms: 500, reachMs: 600 })
      .then(function () { st.valve = mbar; valveK.rotation.z = valveRot(mbar); return setPr(mbar, 1200); }).then(function () { S.say('Air admitted to ' + mbar + ' mbar.'); S.render(); });
  }
  function foilTo(on) {
    if (busy() || st.foil === on) return Promise.resolve();
    var a0 = foilAngle(!on), a1 = foilAngle(on), pt = wpt(base, -0.062 + 0.012, 0.03, -0.105);
    return S.hand.pinchMove(pt, function () { return pt; }, function (k) { var a = a0 + (a1 - a0) * k; lever.rotation.y = a; foilArm.rotation.y = a; }, { mode: 'top', ms: 600, reachMs: 600 })
      .then(function () { st.foil = on; lever.rotation.y = a1; foilArm.rotation.y = a1; S.say(on ? 'Gold foil swung in front of the source.' : 'Gold foil swung out of the way.'); S.render(); });
  }
  function configNow() {
    if (st.open) { S.say('Put the bell jar down first: you cannot count with the chamber open.'); return null; }
    if (st.src === null) { S.say('There is no source on the rail.'); return null; }
    return { src: st.src, pr: st.pr < 1 ? 0 : st.pr, tf: st.foil ? FOIL : 0 };
  }
  function acquire() {
    if (busy()) return Promise.resolve(false);
    var cf = configNow(); if (!cf) return Promise.resolve(false);
    var q = assign(p, cf);
    if (KN.energy(KN.lines(q)[0][0], KN.xair(q), q.a) <= 0) { S.say('The alpha particles are stopped before they reach the detector at this pressure: lower it.'); return Promise.resolve(false); }
    var c = KN.counts(q, st.idx); st.idx += 1; st.counts = c; st.meta = cf; st.pk = null; st.fitted = false; st.recorded = false; st.counting = true; st.prog = 0; st.tlive = 0;
    st.what = NAMES[cf.src] + '  ·  ' + (cf.pr === 0 ? 'vacuum' : Math.round(cf.pr) + ' mbar') + (cf.tf ? '  ·  Au foil' : '') + '  ·  ' + p.t + ' s';
    return S.hand.tap(mStart, 'front').then(function () { return S.tween(1600, function (u) { st.prog = u; st.tlive = p.t * u; }); }).then(function () {
      st.prog = 1; st.tlive = p.t; st.counting = false; var tot = 0; for (var i = 0; i < c.length; i++) tot += c[i];
      S.say('Acquired ' + tot + ' counts in ' + p.t + ' s. Fit the peak to find its channel.'); S.render(); paint(true); return true;
    });
  }
  function fitPeak() {
    if (busy()) return false;
    if (!st.counts || st.prog < 1) { S.say('Acquire a spectrum first.'); return false; }
    st.pk = KN.find_peak(st.counts, p); st.fitted = true;
    S.say('Peak found at channel ' + st.pk.ch.toFixed(1) + ', width ' + st.pk.fwhm_ch.toFixed(1) + ' channels.'); S.render(); paint(true); return true;
  }
  function recordCal(i) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.fitted || st.recorded) { S.say('Fit a fresh peak first.'); return false; }
    if (!st.meta || st.meta.src !== i || st.meta.pr !== 0 || st.meta.tf) { S.say('Calibrate on ' + NAMES[i] + ' in vacuum, with no foil in the way.'); return false; }
    st.recorded = true; S.addRow({ kind: 'cal', name: NAMES[i], E: NOMS[i], ch: st.pk.ch });
    var cs = S.rows.filter(function (r) { return r.kind === 'cal'; }), a = {}; cs.forEach(function (r) { a[r.name] = r; });
    if (a['Am-241'] && a['Pu-239']) { var b = (a['Am-241'].E - a['Pu-239'].E) / (a['Am-241'].ch - a['Pu-239'].ch); st.cal = { a: a['Am-241'].E - b * a['Am-241'].ch, b: b };
      S.say('Energy scale: E = ' + st.cal.a.toFixed(1) + ' + ' + st.cal.b.toFixed(3) + ' × channel (keV).'); } else S.say('Calibration point written down.');
    paint(true); return true;
  }
  function air() { return S.rows.filter(function (r) { return r.kind === 'air'; }); }
  function foilRows() { return S.rows.filter(function (r) { return r.kind === 'foil'; }); }
  function recordAir() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.cal) { S.say('Calibrate the energy scale first.'); return false; }
    if (!st.fitted || st.recorded) { S.say('Fit a fresh peak first.'); return false; }
    if (!st.meta || st.meta.src !== SRC || st.meta.tf) { S.say('Use ' + NAMES[SRC] + ', with the foil swung out.'); return false; }
    var prv = Math.round(st.meta.pr); if (air().some(function (r) { return r.pr === prv; })) { S.say('That pressure is already written down.'); return false; }
    st.recorded = true; var E = eOf(st.pk.ch);
    S.addRow({ kind: 'air', pr: prv, x: p.d * 100 * st.meta.pr / 1013.25, E: E / 1000, ch: st.pk.ch, w: st.pk.fwhm_ch * st.cal.b });
    S.say('Written in your record book: ' + (prv === 0 ? 'vacuum' : prv + ' mbar') + ', E = ' + E.toFixed(0) + ' keV.'); paint(true); return true;
  }
  function recordFoil() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.cal) { S.say('Calibrate the energy scale first.'); return false; }
    if (!st.fitted || st.recorded) { S.say('Fit a fresh peak first.'); return false; }
    var v = air().filter(function (r) { return r.pr === 0; })[0];
    if (!v) { S.say('Record the vacuum peak of ' + NAMES[SRC] + ' first, in the air-loss table.'); return false; }
    if (!st.meta || st.meta.src !== SRC || !st.meta.tf || st.meta.pr !== 0) { S.say('Swing the foil in, in vacuum, with ' + NAMES[SRC] + ' on the rail.'); return false; }
    st.recorded = true; var E = eOf(st.pk.ch) / 1000, dE = v.E - E;
    S.addRow({ kind: 'foil', E: E, dE: dE, S: dE / FOIL, ch: st.pk.ch });
    S.say('Energy lost in the foil: ' + (dE * 1000).toFixed(0) + ' keV, a stopping power of about ' + (dE / FOIL).toFixed(3) + ' MeV per mg/cm².'); paint(true); return true;
  }
  function eraseNow() { if (busy()) return Promise.resolve(); return S.hand.tap(mErase, 'front').then(function () { st.counts = null; st.what = ''; st.pk = null; st.fitted = false; st.prog = 0; st.tlive = 0; S.say('Spectrum cleared.'); S.render(); paint(true); }); }
  function airPts() { return air().map(function (r) { return [r.x, r.E]; }); }
  function result() {
    var pts = airPts(); if (pts.length < 6) return null;
    var R = KN.range_fit(pts), v = air().filter(function (r) { return r.pr === 0; })[0], fo = foilRows()[0];
    return { label: 'Range of the alpha particles in air', value: R, unit: 'cm', digits: 2, truth: HK.TEXTBOOK.ph3_alpha_range(p),
      note: 'E^(3/2) falls linearly with the air path and reaches zero at the range (15 °C, 1013 mbar).' + (v ? ' Energy resolution (FWHM) of the peak in vacuum: ' + v.w.toFixed(1) + ' keV.' : '') +
        (fo ? ' Gold foil: ' + (fo.dE * 1000).toFixed(0) + ' keV lost in 1.0 mg/cm², a stopping power of about ' + fo.S.toFixed(3) + ' MeV per mg/cm² near ' + fo.E.toFixed(2) + ' MeV.' : '') };
  }

  return {
    camera: { pos: [0.02, 1.0, 1.45], look: [0.0, 0.04, -0.2] },
    views: { jar: [[-0.1, 0.3, 0.2], [-0.22, 0.06, -0.18]], det: [[-0.2, 0.22, 0.05], [-0.28, 0.03, -0.18]], rail: [[-0.2, 0.2, 0.05], [-0.22, 0.02, -0.18]], foil: [[-0.2, 0.2, 0.05], [-0.25, 0.03, -0.2]],
      pump: [[-0.5, 0.3, 0.1], [-0.58, 0.05, -0.34]], vac: [[0.2, 0.25, 0.6], [0.26, 0.07, 0.15]], pot: [[0.0, 0.2, 0.4], [-0.02, 0.02, 0.12]], tongs: [[0.12, 0.2, 0.42], [0.12, 0.0, 0.16]],
      mca: [[0.6, 0.25, 0.5], [0.66, 0.07, -0.04]], screen: [[0.28, 0.3, 0.1], [0.3, 0.17, -0.5]], bench: [[0.02, 1.0, 1.45], [0.0, 0.04, -0.2]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: {
      principle: 'An alpha particle loses energy to the gas it crosses at a rate that grows as it slows down, so it comes to rest after a definite distance, its range. For alpha particles of 4–7 MeV in air the range follows an empirical rule, R = a E^(3/2): the 3/2 power of the energy falls in a straight line with distance.',
      formula: 'E^(3/2) = E₀^(3/2) − x / a,   R = a E₀^(3/2)',
      formulaNote: 'x = air path at 15 °C and 1013 mbar; a = 0.318 cm MeV^(−3/2) (Bragg–Kleeman)',
      more: ['Pressure sets how much gas is crossed: a path of d at pressure p counts as d × p/1013 mbar of normal air, so the range is found by letting air in instead of moving the source.',
        'A foil of mass thickness t acts like an air path of t / (0.56 A^(1/3)) cm, from the Bragg–Kleeman rule R(mg/cm²) = 0.56 A^(1/3) R(cm of air).',
        'The peak broadens as the path grows because energy loss is a chance process (straggling); the detector adds its own width.'],
      precautions: 'Sealed sources only, moved with the tongs. The detector face is a thin gold layer: never touch it. Never open the chamber with the bias applied, and let air in slowly. Return the sources to the locked store.' },
    book: { title: 'Expt. — Alpha spectrometry', lines: ['Aim: energy loss in air, range, foil stopping power.', 'Source: ' + SAMPLE + '; rail distance 3.0 cm', 'Calibration: Am-241 5485.56 keV and Pu-239 5156.59 keV (main lines)', 'E^(3/2) = E₀^(3/2) − x/a'],
      columns: [{ label: 'Source / p', get: function (r) { return r.kind === 'cal' ? r.name : (r.kind === 'foil' ? 'Au foil' : (r.pr === 0 ? 'vacuum' : r.pr + ' mbar')); } },
        { label: 'Ch', get: function (r) { return r.ch.toFixed(1); } }, { label: 'E (keV)', get: function (r) { return r.kind === 'cal' ? r.E.toFixed(1) : (r.E * 1000).toFixed(0); } },
        { label: 'x (cm)', get: function (r) { return r.kind === 'air' ? r.x.toFixed(2) : ''; } }, { label: 'E^1.5', get: function (r) { return r.kind === 'air' ? Math.pow(r.E, 1.5).toFixed(3) : ''; } },
        { label: 'S (MeV/mg·cm⁻²)', get: function (r) { return r.kind === 'foil' ? r.S.toFixed(3) : ''; } }] },
    graph: { x: function (r) { return r.kind === 'air' ? r.x : NaN; }, y: function (r) { return r.kind === 'air' ? Math.pow(r.E, 1.5) : NaN; }, xlabel: 'air path x (cm)', ylabel: 'E^(3/2) (MeV^(3/2))', x0: 0, y0: 0,
      line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } },
    result: result,
    tol: 0.04,
    resultNote: 'The straight line of E^(3/2) against air path is the Bragg–Kleeman rule; where it reaches zero is the range.',
    chips: ['Why plot E to the 3/2?', 'Why use pressure instead of distance?', 'Why does the peak broaden?', 'Check my readings', 'Why calibrate on two sources?'],
    viva: [['The range of a 5.5 MeV alpha particle in air at 1 atm is about', ['4 cm', '40 cm', '4 mm'], 0, 'R = 0.318 E^(3/2) = 4.1 cm.'],
      ['Doubling the pressure in the chamber is equivalent to', ['Doubling the source–detector distance', 'Halving the distance', 'No change'], 0, 'The gas crossed is proportional to d × p.'],
      ['The peak gets wider in air because', ['Energy loss is a chance process (straggling)', 'The detector warms up', 'The source decays'], 0, 'Particles lose slightly different amounts, and more so over a longer path.']],
    askState: function () {
      return { experiment: 'alpha spectrometry, energy loss and range', source: st.src === null ? 'none on the rail' : NAMES[st.src], bell_jar_open: st.open, pressure_mbar: Math.round(st.pr),
        foil_in: st.foil, calibrated: !!st.cal, spectrum: st.what, fitted_peak_channel: st.pk ? +st.pk.ch.toFixed(1) : null, readings: air().length };
    },
    steps: [
      { id: 'cal', title: 'Energy calibration', view: 'jar', render: function (u) {
          u.h2('Calibrate the spectrometer in vacuum');
          u.p('Two sources with known main-line energies fix the scale: Am-241 (5485.56 keV) and Pu-239 (5156.59 keV). In vacuum the alpha particles lose nothing on the way.');
          u.task('1. Put a source on the rail', st.src !== null, st.src === null ? 'Bell jar on, no source' : NAMES[st.src] + ' on the rail')
            .add(u.row(u.button(st.open ? 'Bell jar down' : 'Lift the bell jar', function () { S.focus('jar'); jarLift(!st.open); }, false, S.hand.busy)))
            .add(u.row(u.button('Am-241 on', function () { S.focus('pot'); putSource(0); }, false, S.hand.busy || !st.open), u.button('Pu-239 on', function () { putSource(1); }, false, S.hand.busy || !st.open)));
          u.task('2. Pump down', !st.open && st.pr < 1, st.pr < 1 ? 'About 0.1 mbar' : Math.round(st.pr) + ' mbar')
            .add(u.button('Pump out the air', function () { S.focus('vac'); pumpDown(); }, false, S.hand.busy || st.open));
          u.task('3. Count, fit and record each source', S.rows.filter(function (r) { return r.kind === 'cal'; }).length >= 2, st.what || 'Not counted')
            .add(u.row(u.button('START (' + p.t + ' s)', function () { acquire(); }, true, S.hand.busy), u.button('Fit the peak', function () { fitPeak(); }, false, S.hand.busy)))
            .add(u.row(u.button('Record as Am-241', function () { recordCal(0); }, false, S.hand.busy), u.button('Record as Pu-239', function () { recordCal(1); }, false, S.hand.busy)));
          u.live(function () { return st.cal ? 'E = ' + st.cal.a.toFixed(1) + ' + ' + st.cal.b.toFixed(3) + ' × channel (keV)' : 'Not calibrated yet'; });
          u.next('Next: let air in', !!st.cal);
        },
        ok: function () { return !!st.cal; },
        auto: function () {
          var ch = jarLift(true);
          [0, 1].forEach(function (i) { ch = ch.then(function () { return putSource(i); }).then(function () { return jarLift(false); }).then(function () { return pumpDown(); }).then(function () { return acquire(); })
            .then(function () { fitPeak(); recordCal(i); }).then(function () { return i === 0 ? jarLift(true) : null; }); });
          return ch;
        } },
      { id: 'air', title: 'Energy loss in air', view: 'vac', render: function (u) {
          u.h2('Follow the peak as air is let in');
          u.p('Put ' + NAMES[SRC] + ' on the rail, close the jar, pump down, then for each pressure — 0, 100, 200 … 700 mbar — count, fit the peak and record it. The foil must be swung out.');
          u.task('Source and chamber', !st.open && st.src === SRC, st.src === SRC ? (st.open ? 'Jar open' : 'Ready') : 'Not set')
            .add(u.row(u.button(st.open ? 'Bell jar down' : 'Lift the bell jar', function () { jarLift(!st.open); }, false, S.hand.busy), u.button(NAMES[SRC] + ' on', function () { putSource(SRC); }, false, S.hand.busy || !st.open)));
          u.row(u.button('Pump out', function () { pumpDown(); }, false, S.hand.busy || st.open));
          u.row.apply(u, PRS.slice(1).map(function (v) { return u.button(v + '', function () { airTo(v); }, false, S.hand.busy || st.open); }));
          u.row(u.button('START (' + p.t + ' s)', function () { acquire(); }, true, S.hand.busy), u.button('Fit the peak', function () { fitPeak(); }, false, S.hand.busy), u.button('Record', function () { recordAir(); }, false, S.hand.busy));
          u.live(function () { return 'Pressure ' + (st.pr < 1 ? '0.1' : Math.round(st.pr)) + ' mbar  ·  ' + (st.pk && st.fitted && st.cal ? 'peak at ' + eOf(st.pk.ch).toFixed(0) + ' keV' : 'no peak fitted') + '  ·  ' + air().length + ' of 8 recorded'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the gold foil', air().length >= 8);
        },
        ok: function () { return air().length >= 8; },
        auto: function () {
          var ch = jarLift(true).then(function () { return putSource(SRC); }).then(function () { return jarLift(false); }).then(function () { return pumpDown(); });
          PRS.forEach(function (v) { ch = ch.then(function () { return airTo(v); }).then(function () { return acquire(); }).then(function () { fitPeak(); recordAir(); }); });
          return ch;
        } },
      { id: 'foil', title: 'Gold foil', view: 'foil', render: function (u) {
          u.h2('Stopping power of a gold foil');
          u.p('Pump back down to vacuum, swing the 1.0 mg/cm² gold foil in front of the source and count. The energy lost, divided by the foil’s mass thickness, is the mean stopping power.');
          u.row(u.button('Pump out', function () { pumpDown(); }, false, S.hand.busy || st.open), u.button(st.foil ? 'Swing foil out' : 'Swing foil in', function () { S.focus('foil'); foilTo(!st.foil); }, !st.foil, S.hand.busy));
          u.row(u.button('START (' + p.t + ' s)', function () { acquire(); }, true, S.hand.busy), u.button('Fit the peak', function () { fitPeak(); }, false, S.hand.busy), u.button('Record', function () { recordFoil(); }, false, S.hand.busy));
          u.live(function () { return foilRows().length ? 'Energy lost ' + (foilRows()[0].dE * 1000).toFixed(0) + ' keV  ·  S = ' + foilRows()[0].S.toFixed(3) + ' MeV per mg/cm²' : 'Foil ' + (st.foil ? 'in' : 'out') + '  ·  not measured yet'; });
          u.h3('Observation table'); u.table();
          u.next('Next: the result', foilRows().length >= 1);
        },
        ok: function () { return foilRows().length >= 1; },
        auto: function () { return pumpDown().then(function () { return foilTo(true); }).then(function () { return acquire(); }).then(function () { fitPeak(); recordFoil(); }).then(function () { return foilTo(false); })
          .then(function () { return jarLift(true); }).then(function () { return takeSource(); }).then(function () { return jarLift(false); }); } }
    ],
    tick: function () {
      showTime(st.tlive.toFixed(0)); showCnt(String(st.counts ? Math.round((function () { var t = 0; for (var i = 0; i < st.counts.length; i++) t += st.counts[i]; return t; })() * st.prog) : 0));
      vacLcd(st.pr < 1 ? '0.1' : String(Math.round(st.pr)));
      hudP.set((st.pr < 1 ? '0.1' : Math.round(st.pr)) + ' mbar'); hudE.set(st.pk && st.fitted && st.cal ? eOf(st.pk.ch).toFixed(0) + ' keV' : '—'); hudN.set(st.pk && st.fitted ? String(Math.round(st.pk.area)) : '—');
      if (st.counting) paint(false);
    }
  };
});
