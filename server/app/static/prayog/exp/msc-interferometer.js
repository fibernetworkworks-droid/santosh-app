/* Prayogshala studio module: INTERFEROMETER BENCH (M.Sc. optics).
   Two arrangements on one rig, chosen by the lab's kernel:
     msc_michelson  a Michelson interferometer with a micrometer-driven mirror and a plate holder in the fixed arm.
                    The lab's `src` param picks the task: 0 laser (count fringes -> wavelength), 1 sodium lamp
                    (contrast minima -> D-line separation), 2 white light (sharpest fringes with and without a
                    plate -> refractive index of the plate).
     msc_gascell    a Mach-Zehnder (arch 0) or Jamin (arch 1) interferometer with an evacuable gas cell in one path:
                    fringes counted while the pressure rises from vacuum -> n - 1 of the gas.
   All numbers come from the kernels of packs/msc_optics.js on the lab's own params, the code the server checks. */
HoolaStudio.define('msc-interferometer', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME], MICH = KNAME === 'msc_michelson';
  var p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {};
  var TAB = S.lab.table || {}, CALC = HK.CALCS[TAB.calc], TXT = HK.TEXTBOOK[(S.lab.check || {}).textbook];
  var SRC = Math.floor(p.src || 0);
  var GAS = V_.sample || 'Air';
  var st = { on: false, aligned: false, x: 1.0e-3, count: 0, d: 1.5e-4, P: 0, pumped: false, plate: false,
    win: [0.5e-3, 3.0e-3], marked: false, target: 1.0, tcount: 0, minsList: null };
  p.x = st.x;

  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function box(w, h, d, mat, x, y, z, parent, r) {
    var m = S.rounded(w, d, h, r === undefined ? 0.004 : r, mat); m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); (parent || S.scene).add(m); return m;
  }
  var dark = new T.MeshStandardMaterial({ color: 0x22262c, roughness: 0.6 });
  var cream = new T.MeshStandardMaterial({ color: 0xe3dfd3, roughness: 0.5, metalness: 0.1 });
  var mirrorM = new T.MeshStandardMaterial({ color: 0xf2f4f6, roughness: 0.04, metalness: 1 });
  var glassM = new T.MeshPhysicalMaterial({ color: 0xe8f4f2, roughness: 0.03, transmission: 0.9, thickness: 0.02, transparent: true, opacity: 0.5 });
  var beamCol = SRC === 0 || !MICH ? 0xff2a1a : SRC === 1 ? 0xffc030 : 0xfff3d0;
  var beamMat = new T.MeshBasicMaterial({ color: beamCol, transparent: true, opacity: 0.0 });
  var beams = [];
  function beamSeg(a, b) {
    var d = new T.Vector3().subVectors(b, a), len = d.length();
    var m = S.mesh(new T.CylinderGeometry(0.0014, 0.0014, len, 8), beamMat, false, false);
    m.position.copy(a).add(b).multiplyScalar(0.5); m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d.clone().normalize());
    S.scene.add(m); beams.push(m); return m;
  }
  var Y = 0.07;

  // ---------------------------------------------------------------- source
  var srcG = new T.Group(); S.scene.add(srcG); srcG.position.set(-0.62, 0, MICH ? -0.12 : -0.05);
  var pwrBtn;
  if (SRC === 0 || !MICH) {
    var tube = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.26, 28), M.alu); tube.rotation.z = Math.PI / 2; tube.position.set(0, Y - 0.01, 0); srcG.add(tube);
    var cap = S.mesh(new T.CylinderGeometry(0.031, 0.031, 0.02, 28), M.black); cap.rotation.z = Math.PI / 2; cap.position.set(0.135, Y - 0.01, 0); srcG.add(cap);
    var base = box(0.3, 0.04, 0.08, dark, 0, 0.022, 0, srcG);
    var lb = S.label('He-Ne LASER  632.8 nm', { w: 0.14, ratio: 0.12, bg: '#e9e6dc', color: '#2a2a2a', px: 512 }); lb.position.set(-0.02, Y + 0.0208, 0); lb.rotation.x = -Math.PI / 2; srcG.add(lb);
    if (!MICH || SRC === 0) { var lab2 = lb; }
  } else if (SRC === 1) {
    var lamp = S.mesh(new T.CylinderGeometry(0.04, 0.045, 0.16, 28), new T.MeshStandardMaterial({ color: 0x3a3e45, roughness: 0.5 })); lamp.position.set(0, 0.08, 0); srcG.add(lamp);
    var glow = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.08, 20), new T.MeshStandardMaterial({ color: 0xffb020, emissive: 0xff9800, emissiveIntensity: 0.5, roughness: 0.4 })); glow.rotation.z = Math.PI / 2; glow.position.set(0.045, 0.085, 0); srcG.add(glow);
    var dif = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.004, 28), new T.MeshStandardMaterial({ color: 0xfff1cc, transparent: true, opacity: 0.7, roughness: 0.9 })); dif.rotation.z = Math.PI / 2; dif.position.set(0.1, 0.085, 0); srcG.add(dif);
  } else {
    var wl = box(0.1, 0.1, 0.1, dark, 0, 0.055, 0, srcG);
    var wl2 = S.mesh(new T.CylinderGeometry(0.025, 0.025, 0.02, 24), new T.MeshStandardMaterial({ color: 0xfff7e0, emissive: 0xfff0c0, emissiveIntensity: 0.4 })); wl2.rotation.z = Math.PI / 2; wl2.position.set(0.058, 0.06, 0); srcG.add(wl2);
    var dif2 = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.004, 28), new T.MeshStandardMaterial({ color: 0xfff1cc, transparent: true, opacity: 0.7, roughness: 0.9 })); dif2.rotation.z = Math.PI / 2; dif2.position.set(0.1, 0.06, 0); srcG.add(dif2);
  }
  pwrBtn = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.008, 16), M.red); pwrBtn.rotation.x = Math.PI / 2; pwrBtn.position.set(-0.1, 0.02, 0.042); srcG.add(pwrBtn);
  var srcY = (SRC === 0 || !MICH) ? Y - 0.01 : (SRC === 1 ? 0.085 : 0.06);
  S.contact(0.34, 0.14, srcG.position.x, srcG.position.z, 0.5);

  // ---------------------------------------------------------------- the interferometer
  var mir2, carriage, thimble, plate, plateHolder, cellG, screenTex, readTex, chartTex, gaugeTex, pumpBtn, valveBtn, screenMesh, alignScrew, chartG, readG;
  var A = { bs: null }, X0 = -0.15;
  function bsCube(x, z, rotY) {
    var g = new T.Group(); g.position.set(x, Y, z); S.scene.add(g);
    var c = S.mesh(new T.BoxGeometry(0.036, 0.036, 0.036), glassM); g.add(c);
    var dg = S.mesh(new T.BoxGeometry(0.0008, 0.036, 0.0508), new T.MeshStandardMaterial({ color: 0xd8e6ee, transparent: true, opacity: 0.55, metalness: 0.6, roughness: 0.1 })); dg.rotation.y = Math.PI / 4; g.add(dg);
    var pl = S.mesh(new T.CylinderGeometry(0.008, 0.012, Y - 0.018, 16), M.alu); pl.position.y = -(Y - 0.018) / 2 - 0.018; g.add(pl);
    return g;
  }
  function mirrorOn(x, z, rotY, withScrews) {
    var g = new T.Group(); g.position.set(x, Y, z); g.rotation.y = rotY; S.scene.add(g);
    var m = S.mesh(new T.BoxGeometry(0.004, 0.034, 0.034), mirrorM); g.add(m);
    var fr = S.mesh(new T.BoxGeometry(0.01, 0.04, 0.04), M.black); fr.position.x = -0.007; g.add(fr);
    var pl = S.mesh(new T.CylinderGeometry(0.008, 0.012, Y - 0.02, 16), M.alu); pl.position.set(-0.007, -(Y - 0.02) / 2 - 0.02, 0); g.add(pl);
    if (withScrews) { [-1, 1].forEach(function (s) { var sc = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.02, 10), M.chrome); sc.rotation.z = Math.PI / 2; sc.position.set(-0.02, s * 0.011, s * 0.011); g.add(sc); }); }
    return g;
  }
  var apparatusList = [];
  if (MICH) {
    var bsG = bsCube(X0, -0.12), fixed = mirrorOn(X0, -0.4, -Math.PI / 2, true);
    fixed.rotation.y = Math.PI / 2;                          // face the beam splitter (normal along +z)
    carriage = new T.Group(); carriage.position.set(0.2, 0, -0.12); S.scene.add(carriage);
    var mm = mirrorOn(0, -0, 0, false); S.scene.remove(mm); mm.position.set(0, Y, 0); mm.rotation.y = Math.PI; carriage.add(mm);
    var rail = box(0.34, 0.012, 0.03, M.alu, 0.13, 0.008, 0, carriage); rail.position.set(0.13, 0.008, 0);
    var slide = box(0.06, 0.02, 0.05, M.steel, 0.0, 0.022, 0, carriage);
    var mic = new T.Group(); mic.position.set(0.5, 0.045, -0.12); S.scene.add(mic);
    var barrel = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.11, 28), M.steel); barrel.rotation.z = Math.PI / 2; barrel.position.x = -0.045; mic.add(barrel);
    thimble = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.06, 36), new T.MeshStandardMaterial({ map: S.canvasTex(512, 128, function (x, w, h) { x.fillStyle = '#c9ced2'; x.fillRect(0, 0, w, h); x.strokeStyle = '#222'; x.fillStyle = '#222'; x.lineWidth = 3; x.font = '600 34px "Public Sans", sans-serif'; for (var i = 0; i < 50; i++) { var xx = i / 50 * w; x.beginPath(); x.moveTo(xx, 0); x.lineTo(xx, i % 5 ? 30 : 56); x.stroke(); if (i % 5 === 0) x.fillText(String(i), xx + 4, 100); } }), roughness: 0.3, metalness: 0.7 }));
    thimble.rotation.z = Math.PI / 2; thimble.position.x = 0.03; mic.add(thimble);
    var knob = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.02, 24), M.black); knob.rotation.z = Math.PI / 2; knob.position.x = 0.07; mic.add(knob);
    var shaft = S.mesh(new T.CylinderGeometry(0.0035, 0.0035, 0.2, 10), M.steel); shaft.rotation.z = Math.PI / 2; shaft.position.set(-0.13, 0, 0); mic.add(shaft);
    S.contact(0.8, 0.12, 0.2, -0.12, 0.35);
    // plate holder in the fixed arm, and the plate waiting on the bench
    plateHolder = new T.Group(); plateHolder.position.set(X0, 0, -0.27); S.scene.add(plateHolder);
    var phb = box(0.04, 0.01, 0.03, M.alu, 0, 0.005, 0, plateHolder);
    var phpl = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.03, 10), M.steel); phpl.position.y = 0.025; plateHolder.add(phpl);
    plate = new T.Group(); S.scene.add(plate);
    var th = Math.max(0.003, Math.min(0.012, p.tp * 6));
    var pm = S.mesh(new T.BoxGeometry(th, 0.034, 0.03), new T.MeshPhysicalMaterial({ color: 0xdff0ee, roughness: 0.03, transmission: 0.9, thickness: 0.01, transparent: true, opacity: 0.55, ior: 1.5 })); pm.position.y = 0.02; plate.add(pm);
    var pbase = S.mesh(new T.CylinderGeometry(0.014, 0.016, 0.006, 20), M.alu); pbase.position.y = 0.003; plate.add(pbase);
    var PLATE_OUT = new T.Vector3(0.05, 0.004, -0.31), PLATE_IN = new T.Vector3(X0, 0.012, -0.27); plate.position.copy(PLATE_OUT);
    var plbl = S.label('plate  t = ' + (p.tp * 1000).toFixed(3) + ' mm', { w: 0.1, ratio: 0.14, bg: '#e9e6dc', color: '#2a2a2a', px: 512 }); plbl.position.set(0.05, 0.001, -0.25); plbl.rotation.x = -Math.PI / 2; S.scene.add(plbl);
    // beams
    var yb = srcY;
    beamSeg(new T.Vector3(-0.5, yb, -0.12), new T.Vector3(X0, Y, -0.12));
    beamSeg(new T.Vector3(X0, Y, -0.12), new T.Vector3(X0, Y, -0.4));
    var movBeam = beamSeg(new T.Vector3(X0, Y, -0.12), new T.Vector3(0.2, Y, -0.12));
    beamSeg(new T.Vector3(X0, Y, -0.12), new T.Vector3(X0, Y, 0.12));
    alignScrew = fixed.children[2] || fixed;
  } else {
    // gas cell interferometers (Mach-Zehnder or Jamin), laid out in the plane of the table
    var JAMIN = p.arch >= 0.5;
    var Lc = Math.max(0.08, Math.min(0.34, p.L));
    var zA = -0.05, zB = -0.3;
    if (!JAMIN) {
      var bs1 = bsCube(-0.3, zA), bs2 = bsCube(0.2, zB);
      var m1 = mirrorOn(0.2, zA, Math.PI * 0.75, false), m2 = mirrorOn(-0.3, zB, Math.PI * 0.75 + Math.PI, false);
      m1.rotation.y = Math.PI / 4 * 3; m2.rotation.y = -Math.PI / 4;
      beamSeg(new T.Vector3(-0.5, srcY, zA), new T.Vector3(-0.3, Y, zA)); beamSeg(new T.Vector3(-0.3, Y, zA), new T.Vector3(0.2, Y, zA));
      beamSeg(new T.Vector3(0.2, Y, zA), new T.Vector3(0.2, Y, zB)); beamSeg(new T.Vector3(-0.3, Y, zA), new T.Vector3(-0.3, Y, zB));
      beamSeg(new T.Vector3(-0.3, Y, zB), new T.Vector3(0.2, Y, zB)); beamSeg(new T.Vector3(0.2, Y, zB), new T.Vector3(0.45, Y, zB));
      cellG = new T.Group(); cellG.position.set(-0.05, Y, zA); S.scene.add(cellG);
      S.contact(0.8, 0.5, -0.05, -0.17, 0.3);
    } else {
      var zJ = -0.12;
      [-0.28, 0.12].forEach(function (xx) {
        var pl = S.mesh(new T.BoxGeometry(0.02, 0.05, 0.2), glassM); pl.position.set(xx, 0.04, zJ - 0.0); pl.rotation.y = Math.PI / 4; S.scene.add(pl);
        var pb = box(0.07, 0.014, 0.07, M.alu, xx, 0.007, zJ, null);
      });
      beamSeg(new T.Vector3(-0.5, srcY, zJ), new T.Vector3(-0.28, 0.05, zJ));
      beamSeg(new T.Vector3(-0.28, 0.05, zJ - 0.0), new T.Vector3(0.12, 0.05, zJ - 0.0));
      beamSeg(new T.Vector3(-0.28, 0.05, zJ - 0.0), new T.Vector3(0.12, 0.05, zJ));
      cellG = new T.Group(); cellG.position.set(-0.08, 0.05, zJ + 0.0); S.scene.add(cellG);
      var upper = beamSeg(new T.Vector3(-0.28, 0.05, zJ + 0.045), new T.Vector3(0.12, 0.05, zJ + 0.045));
      beamSeg(new T.Vector3(0.12, 0.05, zJ), new T.Vector3(0.45, 0.05, zJ + 0.1));
      cellG.position.set(-0.08, 0.05, zJ); S.contact(0.7, 0.3, -0.08, -0.12, 0.3);
    }
    // the evacuable cell, drawn at its real length
    var cglass = S.mesh(new T.CylinderGeometry(0.014, 0.014, Lc, 28), glassM); cglass.rotation.z = Math.PI / 2; cellG.add(cglass);
    [-1, 1].forEach(function (s) { var w = S.mesh(new T.CylinderGeometry(0.017, 0.017, 0.008, 24), M.steel); w.rotation.z = Math.PI / 2; w.position.x = s * (Lc / 2 + 0.004); cellG.add(w); });
    var port = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.04, 10), M.brass); port.position.set(0, 0.025, 0); cellG.add(port);
    // pump, gauge, valve
    var pump = new T.Group(); pump.position.set(0.45, 0, 0.05); S.scene.add(pump);
    box(0.16, 0.07, 0.1, dark, 0, 0.04, 0, pump);
    pumpBtn = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.01, 18), M.green); pumpBtn.rotation.x = Math.PI / 2; pumpBtn.position.set(-0.05, 0.03, 0.055); pump.add(pumpBtn);
    valveBtn = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.014, 20), M.red); valveBtn.rotation.x = Math.PI / 2; valveBtn.position.set(0.05, 0.03, 0.055); pump.add(valveBtn);
    var pl1 = S.label('PUMP', { w: 0.04, ratio: 0.3, bg: '#14181d', color: '#7fd1b5', px: 256 }); pl1.position.set(-0.05, 0.052, 0.0505); pump.add(pl1);
    var pl2 = S.label('AIR IN', { w: 0.04, ratio: 0.3, bg: '#14181d', color: '#f0b0a8', px: 256 }); pl2.position.set(0.05, 0.052, 0.0505); pump.add(pl2);
    gaugeTex = S.liveTex(300, 300);
    var gauge = new T.Mesh(new T.CircleGeometry(0.04, 36), new T.MeshBasicMaterial({ map: gaugeTex, toneMapped: false })); gauge.position.set(0, 0.11, 0.051); pump.add(gauge);
    var gring = S.mesh(new T.TorusGeometry(0.04, 0.003, 10, 36), M.chrome); gring.position.set(0, 0.11, 0.0505); pump.add(gring);
    S.wire([[cellG.position.x, Y + 0.045, cellG.position.z], [0.1, 0.12, -0.1], [0.42, 0.06, 0.0]], 'blue');
    S.contact(0.2, 0.14, 0.45, 0.05, 0.4);
    S.addApparatus('pump', pump, 'Pump, gauge and air valve', 'A rotary pump takes the cell down to vacuum; the valve lets air in slowly. The dial shows the pressure in atmospheres.');
  }

  // ---------------------------------------------------------------- observation screen, readout, chart
  screenTex = S.liveTex(256, 256);
  var scrG = new T.Group(); S.scene.add(scrG); scrG.position.set(MICH ? X0 : 0.2, 0, MICH ? 0.16 : -0.3 + 0.17);
  var sframe = S.rounded(0.15, 0.15, 0.012, 0.006, dark); sframe.position.set(0, 0.08, 0); scrG.add(sframe);
  screenMesh = new T.Mesh(new T.CircleGeometry(0.06, 40), new T.MeshBasicMaterial({ map: screenTex, toneMapped: false })); screenMesh.position.set(0, 0.08, 0.0075); scrG.add(screenMesh);
  var sleg = S.mesh(new T.CylinderGeometry(0.01, 0.014, 0.01, 16), M.alu); sleg.position.y = 0.005; scrG.add(sleg);
  S.contact(0.18, 0.1, scrG.position.x, scrG.position.z, 0.4);
  readTex = S.liveTex(480, 300);
  readG = new T.Group(); S.scene.add(readG); readG.position.set(MICH ? 0.18 : -0.2, 0, MICH ? 0.18 : 0.1);
  var rframe = S.rounded(0.2, 0.125, 0.014, 0.006, dark); rframe.position.set(0, 0.075, 0); readG.add(rframe);
  var rmesh = new T.Mesh(new T.PlaneGeometry(0.19, 0.119), new T.MeshBasicMaterial({ map: readTex, toneMapped: false })); rmesh.position.set(0, 0.075, 0.0075); readG.add(rmesh);
  var rleg = S.mesh(new T.CylinderGeometry(0.01, 0.014, 0.012, 16), M.alu); rleg.position.y = 0.006; readG.add(rleg);
  S.contact(0.22, 0.12, readG.position.x, readG.position.z, 0.4);
  if (MICH && SRC !== 0) {
    chartTex = S.liveTex(900, 440);
    chartG = new T.Group(); S.scene.add(chartG); chartG.position.set(0.62, 0, -0.32); chartG.rotation.y = -0.45;
    var cb = S.rounded(0.3, 0.17, 0.03, 0.008, dark); cb.position.set(0, 0.11, 0); cb.rotation.x = -0.15; chartG.add(cb);
    var cf = new T.Mesh(new T.PlaneGeometry(0.28, 0.137), new T.MeshBasicMaterial({ map: chartTex, toneMapped: false })); cf.position.set(0, 0.11, 0.0165); cf.rotation.x = -0.15; chartG.add(cf);
    var cn = S.mesh(new T.CylinderGeometry(0.009, 0.009, 0.06, 16), M.iron); cn.position.y = 0.04; chartG.add(cn);
    var cbase = S.mesh(new T.CylinderGeometry(0.035, 0.04, 0.012, 24), M.iron); cbase.position.y = 0.006; chartG.add(cbase);
    S.contact(0.3, 0.2, 0.62, -0.32, 0.4);
  }
  S.addApparatus('src', srcG, MICH ? (SRC === 0 ? 'He-Ne laser' : SRC === 1 ? 'Sodium lamp with diffuser' : 'White-light lamp with diffuser') : 'He-Ne laser', 'The light source. A He-Ne laser is a class 2/3R beam: never look into it.');
  if (MICH) {
    S.addApparatus('bs', bsG, 'Beam splitter', 'A half-silvered plate: it sends half the light each way. The two beams come back and meet again on the screen.');
    S.addApparatus('mov', carriage, 'Movable mirror', 'Carried on a slide and pushed by the micrometer screw: 0.5 mm per turn of the thimble.');
    S.addApparatus('fix', fixed, 'Fixed mirror', 'Two small screws tilt it so that the circular fringes sit in the middle of the screen.');
    S.addApparatus('mic', mic, 'Micrometer', 'The thimble reads the mirror position to 0.001 mm. Turn it the same way during a count: the screw has backlash.');
    S.addApparatus('plate', plate, 'Glass plate', 'Its thickness is printed on the label. It goes in the holder in the fixed arm, square to the beam.');
  } else {
    S.addApparatus('cell', cellG, 'Gas cell, ' + (p.L * 100).toFixed(0) + ' cm', 'A glass tube with flat windows, evacuable. The beam in this arm passes through it once.');
  }
  S.addApparatus('screen', scrG, 'Observation screen', 'The two beams meet here and make the fringes. Bright centre means the two paths differ by a whole number of wavelengths.');
  S.addApparatus('read', readG, 'Readout', 'Shows the micrometer or gauge reading and the fringe count.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudA = S.hudCard(MICH ? 'Micrometer' : 'Pressure'), hudB = S.hudCard(MICH ? 'Contrast' : 'Fringes counted'), hudC = S.hudCard('Centre brightness');

  // ---------------------------------------------------------------- drawing
  function phaseNow() { return MICH ? KN.inten_at(p, p.x) : KN.inten_at(p, st.P); }
  function drawScreen() {
    screenTex.draw(function (x, w, h) {
      var img = x.createImageData(w, h), i, j, R = w / 2, delta, V, ph0, ring, r2, cI, k;
      var K, col = [255, 40, 26];
      if (MICH) {
        delta = KN.delta(p, p.x); V = KN.vis_at(p, p.x);
        K = Math.min(8, 0.4 + Math.abs(delta) / p.lam * 0.02);
        ph0 = 2 * Math.PI * delta / p.lam;
        col = SRC === 0 ? [255, 40, 26] : SRC === 1 ? [255, 190, 40] : [255, 255, 255];
      } else { V = 1; K = 2.2; ph0 = KN.phase(p, st.P); }
      for (j = 0; j < h; j++) for (i = 0; i < w; i++) {
        var dx = (i - R) / R, dy = (j - R) / R; r2 = dx * dx + dy * dy; k = (j * w + i) * 4;
        if (r2 > 1 || !st.on) { img.data[k] = 12; img.data[k + 1] = 14; img.data[k + 2] = 18; img.data[k + 3] = 255; continue; }
        if (MICH && SRC === 2) {
          var Vw = V, lamc = [6.2e-7, 5.4e-7, 4.6e-7], ch = [];
          for (var c = 0; c < 3; c++) { var phc = 2 * Math.PI * delta / lamc[c]; ch.push(0.5 * (1 - Vw * Math.cos(phc + K * Math.PI * 2 * r2))); }
          img.data[k] = 255 * ch[0]; img.data[k + 1] = 255 * ch[1]; img.data[k + 2] = 255 * ch[2];
        } else {
          var ph = MICH ? ph0 : ph0, ring = MICH ? 0.5 * (1 - V * Math.cos(ph + K * Math.PI * 2 * r2)) : 0.5 * (1 + Math.cos(ph + K * Math.PI * 2 * r2));
          var fall = 0.35 + 0.65 * (1 - r2);
          img.data[k] = col[0] * ring * fall; img.data[k + 1] = col[1] * ring * fall; img.data[k + 2] = col[2] * ring * fall;
        }
        img.data[k + 3] = 255;
      }
      x.putImageData(img, 0, 0);
    });
  }
  function drawRead() {
    readTex.draw(function (x, w, h) {
      x.fillStyle = '#10151b'; x.fillRect(0, 0, w, h); x.textAlign = 'left';
      x.fillStyle = '#7d8795'; x.font = '600 26px "Public Sans", sans-serif';
      if (MICH) {
        x.fillText('MICROMETER', 24, 44); x.fillStyle = '#4ad1b5'; x.font = '700 62px "Public Sans", sans-serif'; x.fillText((p.x * 1000).toFixed(4) + ' mm', 24, 108);
        x.fillStyle = '#7d8795'; x.font = '600 26px "Public Sans", sans-serif'; x.fillText(SRC === 0 ? 'FRINGES COUNTED (THIS RUN)' : 'FRINGE CONTRAST', 24, 160);
        x.fillStyle = '#ffb648'; x.font = '700 62px "Public Sans", sans-serif'; x.fillText(SRC === 0 ? String(st.count) : KN.vis_at(p, p.x).toFixed(2), 24, 224);
        x.fillStyle = '#7d8795'; x.font = '500 22px "Public Sans", sans-serif'; x.fillText(SRC === 2 ? (st.plate ? 'plate IN the fixed arm' : 'plate out') : '', 24, 270);
      } else {
        x.fillText('PRESSURE', 24, 44); x.fillStyle = '#4ad1b5'; x.font = '700 62px "Public Sans", sans-serif'; x.fillText(st.P.toFixed(2) + ' atm', 24, 108);
        x.fillStyle = '#7d8795'; x.font = '600 26px "Public Sans", sans-serif'; x.fillText('FRINGES COUNTED', 24, 160);
        x.fillStyle = '#ffb648'; x.font = '700 62px "Public Sans", sans-serif'; x.fillText(st.tcount.toFixed(1), 24, 224);
        x.fillStyle = '#7d8795'; x.font = '500 22px "Public Sans", sans-serif'; x.fillText('gas: ' + GAS + (st.pumped ? '' : '  (cell not yet pumped)'), 24, 270);
      }
    });
  }
  function drawGauge() {
    if (!gaugeTex) return;
    gaugeTex.draw(function (x, w, h) {
      x.fillStyle = '#f4f2ea'; x.fillRect(0, 0, w, h); x.strokeStyle = '#222'; x.fillStyle = '#222'; x.lineWidth = 3; x.font = '600 26px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (var i = 0; i <= 10; i++) { var a = (-225 + i * 27) * Math.PI / 180, r1 = 120, r2 = i % 5 ? 132 : 144; x.beginPath(); x.moveTo(150 + r1 * Math.cos(a), 150 + r1 * Math.sin(a)); x.lineTo(150 + r2 * Math.cos(a), 150 + r2 * Math.sin(a)); x.stroke(); if (i % 5 === 0) x.fillText((i / 10).toFixed(1), 150 + 96 * Math.cos(a), 160 + 96 * Math.sin(a)); }
      x.font = '600 24px "Public Sans", sans-serif'; x.fillText('atm', 150, 205);
      var na = (-225 + st.P * 270) * Math.PI / 180; x.strokeStyle = '#b3261e'; x.lineWidth = 6; x.beginPath(); x.moveTo(150, 150); x.lineTo(150 + 112 * Math.cos(na), 150 + 112 * Math.sin(na)); x.stroke();
    });
  }
  function chartWindow() { return st.win; }
  function chartVal(x, wide) {
    if (SRC === 1) return KN.vis_at(p, x, 1, 0);
    var v = KN.vis_at(p, x, 2, st.plate ? 1 : 0);
    return v;
  }
  function drawChart() {
    if (!chartTex) return;
    var lo = st.win[0], hi = st.win[1];
    chartTex.draw(function (x, w, h) {
      x.fillStyle = '#10151b'; x.fillRect(0, 0, w, h);
      var L = 76, R = w - 20, Tp = 36, Bt = h - 60, i, v;
      x.strokeStyle = '#2b3340'; x.lineWidth = 1.5; x.fillStyle = '#7d8795'; x.font = '19px "Public Sans", sans-serif'; x.textAlign = 'center';
      for (i = 0; i <= 6; i++) { v = lo + (hi - lo) * i / 6; x.beginPath(); x.moveTo(L + (R - L) * i / 6, Tp); x.lineTo(L + (R - L) * i / 6, Bt); x.stroke(); x.fillText((v * 1000).toFixed(hi - lo > 0.5e-3 ? 2 : 4), L + (R - L) * i / 6, Bt + 24); }
      x.textAlign = 'right';
      for (i = 0; i <= 4; i++) { x.beginPath(); x.moveTo(L, Bt - (Bt - Tp) * i / 4); x.lineTo(R, Bt - (Bt - Tp) * i / 4); x.stroke(); x.fillText((i / 4).toFixed(2), L - 8, Bt - (Bt - Tp) * i / 4 + 6); }
      x.fillStyle = '#aeb6c0'; x.textAlign = 'left'; x.font = '600 21px "Public Sans", sans-serif'; x.fillText('FRINGE CONTRAST', 10, 24); x.textAlign = 'right'; x.fillText('MIRROR POSITION (mm)', R, h - 12);
      if (st.on) {
        x.strokeStyle = '#ffb648'; x.lineWidth = 2.5; x.beginPath();
        var cols = 700, sub = SRC === 2 ? 6 : 1, c, s, best;
        for (c = 0; c <= cols; c++) {
          best = 0; for (s = 0; s < sub; s++) { var xx = lo + (hi - lo) * (c + s / sub) / cols, vv = chartVal(xx); if (vv > best) best = vv; }
          var px = L + (R - L) * c / cols, py = Bt - best * (Bt - Tp);
          if (c) x.lineTo(px, py); else x.moveTo(px, py);
        }
        x.stroke();
        x.strokeStyle = '#4ad1b5'; x.lineWidth = 1.5; x.setLineDash([5, 5]); var cx = L + (R - L) * (p.x - lo) / (hi - lo);
        if (cx >= L && cx <= R) { x.beginPath(); x.moveTo(cx, Tp); x.lineTo(cx, Bt); x.stroke(); }
        x.setLineDash([]);
      }
    });
  }
  function redraw() { drawScreen(); drawRead(); drawGauge(); drawChart(); }
  function moveMirror(xm) {
    p.x = xm; st.x = xm;
    if (carriage) carriage.position.x = 0.2 + (xm - 1.0e-3) * 40;
    if (thimble) thimble.rotation.x = xm / 0.0005 * Math.PI * 2;
    if (MICH && beams[2]) { var L = Math.abs(carriage.position.x - X0); beams[2].scale.y = L / 0.35; beams[2].position.x = X0 + (carriage.position.x - X0) / 2; }
  }
  moveMirror(st.x); redraw();

  // ---------------------------------------------------------------- human actions
  function powerOn() {
    if (busy()) return Promise.resolve();
    if (st.on) return Promise.resolve();
    return S.hand.tap(pwrBtn, 'front').then(function () {
      st.on = true; S.click(700, 0.05); beamMat.opacity = 0.7; pwrBtn.material = M.green; redraw();
      S.say('The source is on. ' + (MICH && SRC === 1 ? 'Sodium lamps take a few minutes to warm up to full yellow.' : 'Keep the beam below eye level.')); S.render();
    });
  }
  function align() {
    if (busy()) return Promise.resolve();
    if (st.aligned) return Promise.resolve();
    if (!st.on) { S.say('Switch the source on first.'); return Promise.resolve(); }
    var target = MICH ? alignScrew : (pumpBtn || srcG);
    return S.hand.tap(MICH ? fixed : srcG, 'side').then(function () {
      st.aligned = true; S.click(500, 0.04); S.say('The circular fringes are centred on the screen. Do not touch the mirror screws again.'); redraw(); S.render();
    });
  }
  // ---- Michelson, laser: count fringes while the micrometer is turned by d
  function turnAndCount(d) {
    if (busy()) return Promise.resolve(false);
    if (!st.aligned) { S.say('Align the fringes first.'); return Promise.resolve(false); }
    if (!isFinite(d) || d < 0.02e-3 || d > 0.4e-3) { S.say('Turn the micrometer by between 0.02 and 0.40 mm.'); return Promise.resolve(false); }
    var x0 = p.x;
    if (x0 + d > 2.9e-3) { moveMirror(1.0e-3); x0 = p.x; S.say('Screwed back to 1.000 mm (backlash taken up) before the next count.'); }
    var N = KN.count(p, x0, d);
    st.count = 0;
    return S.hand.pinchMove(wpt(mic, 0.07, 0, 0), function (k) { return wpt(mic, 0.07, 0, 0); }, function (k) {
      moveMirror(x0 + d * k); st.count = Math.floor(N * k); drawScreen(); drawRead();
    }, { mode: 'side', ms: 2400, reachMs: 700, pose: 'grip' }).then(function () {
      moveMirror(x0 + d); st.count = N; st.lastRun = { d: d, N: N }; redraw(); S.render();
      S.say(N + ' bright fringes passed the centre while the mirror moved ' + (d * 1000).toFixed(3) + ' mm.'); return true;
    });
  }
  function recordRun() {
    if (!st.lastRun) { S.say('Make a count first.'); return false; }
    var d = st.lastRun.d, N = st.lastRun.N;
    if (S.rows.some(function (r) { return Math.abs(r.d - d) < 1e-12 && r.N === N && r._run === st.lastRun; })) { S.say('That run is already in your table.'); return false; }
    S.addRow({ d: d, N: N, _run: st.lastRun }); S.say('Written in your record book: d = ' + (d * 1000).toFixed(3) + ' mm, N = ' + N + '.'); return true;
  }
  // ---- Michelson, doublet / white light: the chart
  function setMirror(xm) {
    if (!isFinite(xm) || xm < 0.4e-3 || xm > 3.2e-3) { S.say('The micrometer travels from 0.4 to 3.2 mm.'); return false; }
    moveMirror(xm); redraw(); return true;
  }
  function setWindow(lo, hi) { st.win = [Math.max(0.4e-3, lo), Math.min(3.2e-3, hi)]; redraw(); }
  function minimaAll() { if (!st.minsList) st.minsList = KN.minima(p, 0.5e-3, 3.0e-3, 2e-6); return st.minsList; }
  function nextMinimum(dir) {
    var m = minimaAll(), x = p.x, i, best = null;
    if (dir > 0) { for (i = 0; i < m.length; i++) if (m[i] > x + 1e-7) { best = m[i]; break; } } else { for (i = m.length - 1; i >= 0; i--) if (m[i] < x - 1e-7) { best = m[i]; break; } }
    if (best === null) { S.say('No further minimum in that direction.'); return false; }
    return setMirror(best);
  }
  function markMinimum() {
    var m = minimaAll(), i, hit = -1;
    for (i = 0; i < m.length; i++) if (Math.abs(m[i] - p.x) < 2e-7) hit = i;
    if (hit < 0) { S.say('Not at a minimum of the contrast: use Next minimum or turn the micrometer until the fringes almost vanish.'); return false; }
    var k = S.rows.length + 1;
    if (S.rows.some(function (r) { return Math.abs(r.x - m[hit]) < 1e-9; })) { S.say('That minimum is already in your table.'); return false; }
    S.addRow({ k: k, x: m[hit] }); S.say('Minimum ' + k + ' written down: ' + (m[hit] * 1000).toFixed(4) + ' mm.'); return true;
  }
  function insertPlate() {
    if (busy()) return Promise.resolve();
    if (st.plate) return Promise.resolve();
    var from = plate.position.clone(), to = PLATE_IN.clone();
    return S.hand.pinchMove(from.clone().add(new T.Vector3(0, 0.025, 0)), function (k) {
      return new T.Vector3(from.x + (to.x - from.x) * k, from.y + 0.025 + 0.05 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k);
    }, function (k) { plate.position.set(from.x + (to.x - from.x) * k, from.y + 0.05 * Math.sin(Math.PI * k) + (to.y - from.y) * k, from.z + (to.z - from.z) * k); }, { mode: 'side', ms: 1000, reachMs: 700 }).then(function () {
      plate.position.copy(to); st.plate = true; p.ins = 1; S.say('The plate is in the fixed arm, square to the beam. The white-light fringes have disappeared.'); redraw(); S.render();
    });
  }
  function markSharpest() {
    var lo = st.win[0], hi = st.win[1];
    if (hi - lo > 120e-6) { S.say('Zoom in first: the window must be under 0.1 mm wide to place the mark to a fraction of a micrometer.'); return false; }
    var n = 2000, step = (hi - lo) / n, bi = 0, bv = -1, i, f = function (x) { return chartVal(x); };
    for (i = 0; i <= n; i++) { var v = f(lo + i * step); if (v > bv) { bv = v; bi = i; } }
    if (bv < 0.05) { S.say('No fringes in this window: widen it and look for the spike.'); return false; }
    var a = lo + (bi - 1) * step, b = lo + (bi + 1) * step, j;
    for (j = 0; j < 60; j++) { var a1 = a + (b - a) / 3, a2 = b - (b - a) / 3; if (f(a1) > f(a2)) b = a2; else a = a1; }
    var xm = (a + b) / 2, k = st.plate ? 1 : 0;
    moveMirror(xm); redraw();
    var prev = S.rows.filter(function (r) { return r.k === k; });
    if (prev.length) S.rows.splice(S.rows.indexOf(prev[0]), 1);
    S.addRow({ k: k, x: xm }); S.say('Sharpest fringes at ' + (xm * 1000).toFixed(4) + ' mm (' + (k ? 'plate in' : 'plate out') + ').'); return true;
  }
  function seekZpd() {
    // the student's search: wide window to find the spike, then narrower windows round it, then the mark
    var a = 0.5e-3, b = 3.0e-3, n = 2400, best = 0, bx = 0, i;
    for (i = 0; i <= n; i++) { var x = a + (b - a) * i / n; var v = chartVal(x); if (v > best) { best = v; bx = x; } }
    if (best < 0.05) {
      var s2 = 0.25e-6, m2 = 0, mx = 0; for (i = 0; i < 10000; i++) { var xx = a + s2 * i * 1; var vv = chartVal(xx); if (vv > m2) { m2 = vv; mx = xx; } }
      bx = mx;
    }
    // refine with a fine scan to be sure of the spike
    var fine = 0, fx = bx; for (i = -400; i <= 400; i++) { var xf = bx + i * 0.25e-6, vf = chartVal(xf); if (vf > fine) { fine = vf; fx = xf; } }
    moveMirror(fx); setWindow(fx - 40e-6, fx + 40e-6);
    return markSharpest();
  }
  // ---- gas cell
  function pumpDown() {
    if (busy()) return Promise.resolve();
    if (!st.on) { S.say('Switch the laser on first.'); return Promise.resolve(); }
    var P0 = st.P;
    return S.hand.tap(pumpBtn, 'front').then(function () {
      return S.tween(1400, function (k) { st.P = P0 * (1 - k); drawGauge(); drawRead(); drawScreen(); });
    }).then(function () { st.P = 0; st.pumped = true; st.tcount = 0; redraw(); S.say('The cell is at vacuum. The centre of the pattern is bright.'); S.render(); });
  }
  function admit(target) {
    if (busy()) return Promise.resolve(false);
    if (!st.pumped) { S.say('Pump the cell down first.'); return Promise.resolve(false); }
    if (!isFinite(target) || target < 0.05 || target > 1.0) { S.say('Let air in to a pressure between 0.05 and 1.0 atm.'); return Promise.resolve(false); }
    if (st.P > 1e-9) { S.say('Pump down to vacuum again before the next count.'); return Promise.resolve(false); }
    var N = KN.fringes(p, target);
    return S.hand.tap(valveBtn, 'front').then(function () {
      return S.tween(2600, function (k) { st.P = target * k; st.tcount = N * k; p.P = st.P; drawGauge(); drawRead(); drawScreen(); });
    }).then(function () { st.P = target; p.P = target; st.tcount = N; st.last = { P: target, N: rnd(N, 1) }; st.pumped = false; redraw(); S.render(); S.say(N.toFixed(1) + ' fringes passed while the pressure rose to ' + target.toFixed(2) + ' atm.'); return true; });
  }
  function recordGas() {
    if (!st.last) { S.say('Let air in and count first.'); return false; }
    if (S.rows.some(function (r) { return r.P === st.last.P; })) { S.say('There is already a reading at ' + st.last.P.toFixed(2) + ' atm.'); return false; }
    S.addRow({ P: st.last.P, N: st.last.N }); S.say('Written in your record book: ' + st.last.P.toFixed(2) + ' atm, ' + st.last.N.toFixed(1) + ' fringes.'); return true;
  }

  // ---------------------------------------------------------------- result
  function enough() {
    var v; try { v = CALC.fn(S.rows, p); } catch (e) { return false; }
    if (!isFinite(v) || v === 0) return false;
    if (MICH && SRC === 0) return S.rows.length >= 3;
    if (MICH && SRC === 1) return S.rows.length >= 3;
    if (MICH) return !!(S.rows.filter(function (r) { return r.k === 0; }).length && S.rows.filter(function (r) { return r.k === 1; }).length);
    return S.rows.length >= 3;
  }
  function result(rows) {
    if (!enough()) return null;
    var v = CALC.fn(rows, p), tr = TXT ? TXT(p) : undefined, k = MICH ? (TAB.result_k || 1) : 1e4, unit = MICH ? (TAB.result_unit || '') : '× 10⁻⁴';
    var note = '';
    if (!MICH) note = 'n − 1 at 1 atm for ' + GAS.toLowerCase() + ', from the slope of fringes against pressure. The fringe count was read to 0.1 of a fringe.';
    else if (SRC === 2) note = 'n = 1 + shift / t. White-light fringes follow the group delay, so a real plate would read a little high; this simulated glass has no dispersion.';
    return { label: CALC.label.charAt(0).toUpperCase() + CALC.label.slice(1), value: v * k, unit: unit, digits: MICH ? TAB.result_digits : 3, truth: tr === undefined ? undefined : tr * k, note: note };
  }

  var graph = null;
  if (!MICH) graph = { xlabel: 'pressure (atm)', ylabel: 'fringes counted', x: function (r) { return r.P; }, y: function (r) { return r.N; }, x0: 0, y0: 0,
    line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } };
  else if (SRC === 0) graph = { xlabel: 'mirror travel d (mm)', ylabel: 'fringes N', x: function (r) { return r.d * 1000; }, y: function (r) { return r.N; }, x0: 0, y0: 0,
    line: function (pts) { var m = S.fit.origin(pts); return function (x) { return m * x; }; } };
  else if (SRC === 1) graph = { xlabel: 'disappearance number', ylabel: 'mirror reading (mm)', x: function (r) { return r.k; }, y: function (r) { return r.x * 1000; }, x0: 0,
    line: function (pts) { var f = S.fit.linear(pts); return f ? function (x) { return f.m * x + f.c; } : null; } };

  var colsMap = MICH ? (SRC === 0 ? [{ label: 'd (mm)', get: function (r) { return (r.d * 1000).toFixed(3); } }, { label: 'N', get: function (r) { return r.N; } }, { label: '2d/N (nm)', get: function (r) { return (2 * r.d / r.N * 1e9).toFixed(1); } }]
    : SRC === 1 ? [{ label: 'Minimum', get: function (r) { return r.k; } }, { label: 'Reading (mm)', get: function (r) { return (r.x * 1000).toFixed(4); } }]
    : [{ label: 'Plate', get: function (r) { return r.k ? 'in' : 'out'; } }, { label: 'Sharpest at (mm)', get: function (r) { return (r.x * 1000).toFixed(4); } }])
    : [{ label: 'P (atm)', get: function (r) { return r.P.toFixed(2); } }, { label: 'N counted', get: function (r) { return r.N.toFixed(1); } }, { label: 'N λ / L', get: function (r) { return (r.N * p.lam / p.L / Math.max(r.P, 1e-9) * 1e4).toFixed(3) + ' e-4'; } }];

  var FORM = MICH ? (SRC === 0 ? 'λ = 2 d / N' : SRC === 1 ? 'Δx = λ̄² / (2 Δλ)   so   Δλ = λ̄² / (2 Δx)' : 'n = 1 + s / t')
    : 'N = (n − 1) L / λ   so   n − 1 = N λ / L';
  var HINT = MICH ? (SRC === 0 ? 'Turn the micrometer the same way and count the fringes that pass the centre.' : SRC === 1 ? 'Find at least three places where the fringes almost vanish.' : 'Zoom in on the spike of sharp fringes, mark it, put the plate in, find the spike again.')
    : 'Pump to vacuum, let air in to a chosen pressure while counting fringes, record the pressure and N.';

  var steps = [];
  steps.push({ id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
      u.h2('Switch on and align');
      u.p('Switch the source on, then ' + (MICH ? 'tilt the fixed mirror with its two screws until the circular fringes are centred on the screen.' : 'adjust the second beam-splitter until the fringes are broad and steady.'));
      u.task('1. Switch the source on', st.on, st.on ? 'On' : 'Press POWER')
        .add(u.button(st.on ? 'On' : 'Switch on', function () { S.focus('src'); powerOn(); }, !st.on, st.on || S.hand.busy));
      u.task('2. Align the fringes', st.aligned, st.aligned ? 'Fringes centred' : 'Adjust the screws')
        .add(u.button(st.aligned ? 'Aligned' : 'Align', function () { S.focus(MICH ? 'fix' : 'screen'); align(); }, !st.aligned, st.aligned || !st.on || S.hand.busy));
      u.note(S.lab.safety);
      u.next('Next: take readings', st.on && st.aligned);
    },
    ok: function () { return st.on && st.aligned; },
    auto: function () { return powerOn().then(function () { return align(); }); } });

  if (MICH && SRC === 0) steps.push({ id: 'count', title: 'Count fringes', view: 'mic', render: function (u) {
      u.h2('Turn the micrometer and count');
      u.p(HINT);
      var tg = { v: st.d * 1000 };
      u.slider('Distance to turn the mirror', 0.05, 0.3, 0.01, function () { return tg.v; }, function (v) { tg.v = v; st.d = v * 1e-3; }, 'mm', 2);
      u.row(u.button('Turn and count', function () { S.focus('mic'); turnAndCount(st.d); }, true, S.hand.busy), u.button('Record this run', function () { recordRun(); }, false, S.hand.busy));
      u.live(function () { return 'Micrometer ' + (p.x * 1000).toFixed(4) + ' mm  ·  counted ' + st.count; });
      u.h3('Observation table'); u.table();
      u.next('Next: the result', enough());
    },
    ok: function () { return enough(); },
    auto: function () {
      var ds = [0.10e-3, 0.15e-3, 0.20e-3], chain = Promise.resolve();
      ds.forEach(function (d) { chain = chain.then(function () { st.d = d; return turnAndCount(d); }).then(function () { recordRun(); }); });
      return chain;
    } });

  if (MICH && SRC === 1) steps.push({ id: 'minima', title: 'Find the minima', view: 'mic', render: function (u) {
      u.h2('Where do the fringes almost vanish?');
      u.p(HINT + ' The chart shows the fringe contrast against the micrometer reading; the dotted line is where the mirror is now.');
      var tg = { v: p.x * 1000 };
      u.slider('Micrometer reading', 0.6, 3.0, 0.001, function () { return p.x * 1000; }, function (v) { tg.v = v; setMirror(v * 1e-3); }, 'mm', 3);
      u.row(u.button('◀ Previous minimum', function () { nextMinimum(-1); u.live; S.render(); }), u.button('Next minimum ▶', function () { nextMinimum(1); S.render(); }));
      u.row(u.button('Write down this minimum', function () { markMinimum(); }, true, S.hand.busy));
      u.live(function () { return 'Mirror at ' + (p.x * 1000).toFixed(4) + ' mm  ·  contrast ' + KN.vis_at(p, p.x).toFixed(2); });
      u.h3('Observation table'); u.table();
      u.next('Next: the result', enough());
    },
    ok: function () { return enough(); },
    auto: function () {
      st.rows0 = S.rows.length;
      var m = minimaAll(), chain = Promise.resolve();
      m.slice(0, 5).forEach(function (x) { chain = chain.then(function () { setMirror(x); return markMinimum(); }); });
      return chain;
    } });

  if (MICH && SRC === 2) steps.push({ id: 'zpd', title: 'Find the sharpest fringes', view: 'mic', render: function (u) {
      u.h2('Plate out, then plate in');
      u.p(HINT);
      var tg = { v: p.x * 1000 };
      u.slider('Micrometer reading', 0.5, 3.0, 0.0005, function () { return p.x * 1000; }, function (v) { tg.v = v; setMirror(v * 1e-3); }, 'mm', 4);
      u.row(u.button('Show the whole travel', function () { setWindow(0.5e-3, 3.0e-3); S.render(); }), u.button('Zoom to ±50 µm here', function () { setWindow(p.x - 50e-6, p.x + 50e-6); S.render(); }),
        u.button('Zoom to ±5 µm here', function () { setWindow(p.x - 5e-6, p.x + 5e-6); S.render(); }));
      u.row(u.button('Mark the sharpest fringes', function () { markSharpest(); S.render(); }, true, S.hand.busy));
      u.task('Plate in the fixed arm', st.plate, st.plate ? 'Plate is in' : 'Plate on the bench').add(u.button(st.plate ? 'In' : 'Put the plate in', function () { S.focus('plate'); insertPlate().then(function () { setWindow(0.5e-3, 3.0e-3); }); }, false, st.plate || S.hand.busy));
      u.live(function () { return 'Mirror at ' + (p.x * 1000).toFixed(4) + ' mm  ·  contrast ' + KN.vis_at(p, p.x, 2, st.plate ? 1 : 0).toFixed(2); });
      u.h3('Observation table'); u.table();
      u.next('Next: the result', enough());
    },
    ok: function () { return enough(); },
    auto: function () {
      setWindow(0.5e-3, 3.0e-3);
      return Promise.resolve().then(function () { return seekZpd(); }).then(function () { return insertPlate(); }).then(function () { setWindow(0.5e-3, 3.0e-3); return seekZpd(); });
    } });

  if (!MICH) steps.push({ id: 'fringes', title: 'Count fringes', view: 'pump', render: function (u) {
      u.h2('Pump down, then let the gas in');
      u.p(HINT);
      u.row(u.button('Pump down to vacuum', function () { S.focus('pump'); pumpDown(); }, !st.pumped, S.hand.busy || st.pumped));
      var tg = { v: st.target };
      u.slider('Let the gas in up to', 0.1, 1.0, 0.05, function () { return tg.v; }, function (v) { tg.v = v; st.target = v; }, 'atm', 2);
      u.row(u.button('Let gas in and count', function () { S.focus('pump'); admit(st.target); }, true, S.hand.busy || !st.pumped), u.button('Record this count', function () { recordGas(); S.render(); }, false, S.hand.busy));
      u.live(function () { return 'Gauge ' + st.P.toFixed(2) + ' atm  ·  fringes counted ' + st.tcount.toFixed(1); });
      u.h3('Observation table'); u.table();
      u.next('Next: the result', enough());
    },
    ok: function () { return enough(); },
    auto: function () {
      var chain = Promise.resolve();
      [0.2, 0.4, 0.6, 0.8, 1.0].forEach(function (P) {
        chain = chain.then(function () { return pumpDown(); }).then(function () { st.target = P; return admit(P); }).then(function () { recordGas(); });
      });
      return chain;
    } });

  return {
    camera: { pos: [0.0, 0.7, 1.05], look: [-0.02, 0.05, -0.15] },
    views: { src: [[-0.62, 0.3, 0.3], [-0.62, 0.06, -0.1]], bs: [[-0.15, 0.3, 0.25], [-0.15, 0.06, -0.12]], mov: [[0.2, 0.3, 0.2], [0.2, 0.06, -0.12]], fix: [[-0.15, 0.3, 0.05], [-0.15, 0.06, -0.4]],
      mic: [[0.46, 0.3, 0.2], [0.46, 0.05, -0.12]], plate: [[-0.05, 0.3, 0.1], [-0.15, 0.03, -0.27]], screen: [[scrG.position.x, 0.3, 0.45], [scrG.position.x, 0.08, scrG.position.z]],
      read: [[readG.position.x, 0.3, 0.5], [readG.position.x, 0.08, readG.position.z]], cell: [[-0.05, 0.3, 0.2], [-0.05, 0.06, -0.12]], pump: [[0.45, 0.3, 0.35], [0.45, 0.06, 0.05]],
      bench: [[0.0, 0.7, 1.05], [-0.02, 0.05, -0.15]], book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: FORM, formulaNote: 'SI units; the fringe count is read to a tenth of a fringe where a fraction is needed', more: [HINT], precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 72) + '...', MICH ? 'Michelson interferometer, micrometer 0.001 mm' : (p.arch >= 0.5 ? 'Jamin interferometer' : 'Mach-Zehnder interferometer') + ', cell ' + (p.L * 100).toFixed(0) + ' cm', 'Gas: ' + GAS, HINT.slice(0, 70)], columns: colsMap },
    graph: graph,
    result: result,
    tol: 0.02,
    resultNote: 'Fringe counting turns a length too small to see into a number you can count. The result is only as good as the count: one fringe missed over a few hundred is still a small error.',
    chips: ['What is a fringe?', 'Why does the centre go bright and dark?', 'What if I lose count?', 'Check my readings', 'What is the unknown here?'],
    viva: [],
    askState: function () {
      return { experiment: S.lab.title, source_on: st.on, aligned: st.aligned, micrometer_mm: MICH ? +(p.x * 1000).toFixed(4) : undefined, fringes_counted: MICH ? st.count : +st.tcount.toFixed(1),
        pressure_atm: MICH ? undefined : +st.P.toFixed(2), plate_in: MICH ? st.plate : undefined, readings_taken: S.rows.length };
    },
    steps: steps,
    tick: function () {
      hudA.set(MICH ? (p.x * 1000).toFixed(3) + ' mm' : st.P.toFixed(2) + ' atm');
      hudB.set(MICH ? (SRC === 0 ? String(st.count) : KN.vis_at(p, p.x, undefined, undefined).toFixed(2)) : st.tcount.toFixed(1));
      hudC.set(st.on ? phaseNow().toFixed(2) : '—');
    }
  };
});
