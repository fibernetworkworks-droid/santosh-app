/* Prayogshala studio module: Specific heat of a solid by the method of mixtures (NCERT Class XI).
   Physics: the mixtures kernel from kernels.js (metal and water + calorimeter exchange heat, RK4) - the same numbers the
   server checks. The hidden knob c1 (the metal's specific heat) is what the student measures. */
HoolaStudio.define('specific-heat-mixtures', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, K = HK.K.mixtures;
  var up = new T.Vector3(0, 1, 0);
  function labParams(name) { var o = {}; (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {}; Object.keys(lp).forEach(function (key) { o[key] = lp[key]; }); return HK.paramsFor(name, o); }
  var p = labParams('mixtures');
  function r1(v) { return Math.round(v * 10) / 10; }     // water thermometer: read to 0.1 °C
  function r5(v) { return Math.round(v * 2) / 2; }       // boiling-water thermometer: 0.5 °C
  var sim = K.init(p);
  var st = { heater: false, Tboil: 32, boiled: 0, T1: null, T2: null, moved: false, dropped: false, stirred: 0, speed: 5, fallV: 0, shownW: p.T2, blockT: 32 };

  function carry(startPt, legs, pose, mode) {
    mode = mode || 'side';
    if (S.fast) { legs.forEach(function (l) { if (l.onK) l.onK(1); }); return Promise.resolve(); }
    S.hand.busy = true;
    var pr = S.hand.shape('relaxed', 1).then(function () { return S.hand.reach(startPt, mode, 800); }).then(function () { return S.hand.shape(pose || 'grip', 320); });
    legs.forEach(function (l) { pr = pr.then(function () { return S.hand.follow(l.fn, mode, l.ms || 1000, l.onK); }); });
    return pr.then(function () { return S.hand.shape('relaxed', 260); }).then(function () { return S.hand.away(); })
      .then(function () { S.hand.busy = false; }, function () { S.hand.busy = false; });
  }
  function clampStand(jx, jz, armY, armLen, h) {
    var g = S.stand({ x: 0, z: 0, armY: armY, armLen: armLen, h: h });
    var blob = S.scene.children[S.scene.children.length - 1], rotY = -Math.PI / 2;
    g.rotation.y = rotY; var j = new T.Vector3(-0.19 + armLen, 0, 0).applyAxisAngle(up, rotY);
    g.position.set(jx - j.x, 0, jz - j.z);
    var bc = new T.Vector3(-0.12, 0, 0).applyAxisAngle(up, rotY); blob.position.set(g.position.x + bc.x, blob.position.y, g.position.z + bc.z); blob.rotation.z = rotY;
    return g;
  }
  function vessel(r, h, mat) {
    var pts = [[0, 0.0005], [r - 0.005, 0.0005], [r, 0.005], [r, h], [r + 0.0018, h + 0.0012], [r - 0.0012, h + 0.0004], [r - 0.0012, 0.006], [r - 0.006, 0.0018], [0, 0.0018]]
      .map(function (a) { return new T.Vector2(a[0], a[1]); });
    var m = mat.clone(); m.side = T.DoubleSide; return S.mesh(new T.LatheGeometry(pts, 48), m);
  }
  var waterM = new T.MeshStandardMaterial({ color: 0x9cc6d6, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.9 });
  var copperM = new T.MeshStandardMaterial({ color: 0xe39a68, roughness: 0.28, metalness: 0.6 });

  // ---------- heater + beaker of boiling water with the metal in it
  var HX = -0.13, HZ = -0.12, PLATE = 0.052;
  var heater = new T.Group(); S.scene.add(heater);
  var hb = S.rounded(0.17, 0.17, 0.045, 0.012, new T.MeshStandardMaterial({ color: 0xe7e4dc, roughness: 0.5 })); hb.rotation.x = -Math.PI / 2; hb.position.set(HX, 0.0225, HZ); heater.add(hb);
  var hplate = S.mesh(new T.CylinderGeometry(0.066, 0.066, 0.007, 48), new T.MeshStandardMaterial({ color: 0x1d1d1f, roughness: 0.6, metalness: 0.3, emissive: 0x000000 })); hplate.position.set(HX, 0.0485, HZ); heater.add(hplate);
  var coil = S.mesh(new T.TorusGeometry(0.04, 0.0025, 8, 48), new T.MeshStandardMaterial({ color: 0x3a3a3c, roughness: 0.5, metalness: 0.5, emissive: 0x000000 })); coil.rotation.x = Math.PI / 2; coil.position.set(HX, PLATE + 0.0005, HZ); heater.add(coil);
  var knob = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.012, 24), M.black); knob.rotation.x = Math.PI / 2; knob.position.set(HX + 0.045, 0.022, HZ + 0.091); heater.add(knob);
  var lamp = S.mesh(new T.SphereGeometry(0.004, 12, 10), new T.MeshStandardMaterial({ color: 0x5a1010, roughness: 0.3, emissive: 0x000000 })); lamp.position.set(HX - 0.045, 0.024, HZ + 0.087); heater.add(lamp);
  var hl = S.label('HOT PLATE  ·  1 kW', { w: 0.07, ratio: 0.14, color: '#3b3b3b' }); hl.position.set(HX - 0.005, 0.034, HZ + 0.0855); heater.add(hl);
  S.contact(0.24, 0.24, HX, HZ, 0.55);
  var BR = 0.046, BH = 0.115;
  var beaker = S.beaker(BR, BH, [HX, PLATE, HZ]);
  var bw = S.mesh(new T.CylinderGeometry(BR * 0.95, BR * 0.95, BH * 0.62, 36), new T.MeshStandardMaterial({ color: 0x6aaccc, roughness: 0.05, metalness: 0.08 }), false);   // opaque, so it shows through the transmissive beaker glass
  bw.position.y = 0.002 + BH * 0.31; bw.renderOrder = 2; beaker.add(bw);
  var bubbles = []; for (var i = 0; i < 16; i++) { var b = S.mesh(new T.SphereGeometry(0.0022 + (i % 3) * 0.0008, 8, 6), new T.MeshStandardMaterial({ color: 0xffffff, roughness: 0.1, transparent: true, opacity: 0.8 }), false); b.renderOrder = 3;
    b.userData = { ph: i / 16, x: (((i * 37) % 17) / 17 - 0.5) * 0.06, z: (((i * 53) % 13) / 13 - 0.5) * 0.06 }; b.visible = false; S.scene.add(b); bubbles.push(b); }
  // the metal: a cylinder on a wire gauze platform in the boiling water
  var BLOCK_R = 0.017, BLOCK_H = 0.032;
  var block = new T.Group(); S.scene.add(block);
  var bm = S.mesh(new T.CylinderGeometry(BLOCK_R, BLOCK_R, BLOCK_H, 40), new T.MeshStandardMaterial({ color: 0xc9cdd2, roughness: 0.32, metalness: 0.9 })); bm.position.y = BLOCK_H / 2; block.add(bm);
  var bhook = S.mesh(new T.TorusGeometry(0.004, 0.001, 8, 16), M.steel); bhook.position.y = BLOCK_H + 0.004; block.add(bhook);
  var gauze = S.mesh(new T.CylinderGeometry(0.03, 0.03, 0.002, 24), new T.MeshStandardMaterial({ color: 0x8b8f93, roughness: 0.5, metalness: 0.8, wireframe: true })); gauze.position.set(HX, PLATE + 0.012, HZ); S.scene.add(gauze);
  var BLOCK_HOME = new T.Vector3(HX + 0.006, PLATE + 0.013, HZ);
  block.position.copy(BLOCK_HOME);
  var thermoB = S.thermometer({ len: 0.3, min: -10, max: 110, value: 32, pos: [HX - 0.012, PLATE + 0.03, HZ - 0.028] });
  var standB = clampStand(HX - 0.012, HZ - 0.028, 0.29, 0.3, 0.44);

  // ---------- calorimeter in its wooden jacket, with stirrer and thermometer
  var CX = 0.17, CZ = -0.08, JR = 0.064, JH = 0.1, CAL_R = 0.036, CAL_H = 0.085, CY = 0.012;
  var jacket = new T.Group(); S.scene.add(jacket);
  var jprof = [[0, 0], [JR, 0], [JR, JH], [JR - 0.004, JH + 0.003], [JR - 0.012, JH + 0.003], [JR - 0.014, JH], [JR - 0.014, 0.01], [0, 0.01]].map(function (a) { return new T.Vector2(a[0], a[1]); });
  var jm = M.darkWood.clone(); jm.side = T.DoubleSide;
  var jw = S.mesh(new T.LatheGeometry(jprof, 56), jm); jw.position.set(CX, 0, CZ); jacket.add(jw);
  var felt = S.mesh(new T.CylinderGeometry(JR - 0.0145, JR - 0.0145, 0.002, 40), new T.MeshStandardMaterial({ color: 0x2f2f2c, roughness: 1 })); felt.position.set(CX, 0.011, CZ); jacket.add(felt);
  var jl = S.label('INSULATING JACKET', { w: 0.06, ratio: 0.14, color: '#f1e4c9' }); jl.position.set(CX, 0.05, CZ + JR + 0.0008); jacket.add(jl);
  S.contact(0.18, 0.18, CX, CZ, 0.55);
  var cal = new T.Group(); cal.position.set(CX, CY, CZ); S.scene.add(cal);
  cal.add(vessel(CAL_R, CAL_H, copperM));
  var water = S.mesh(new T.CylinderGeometry(CAL_R - 0.0014, CAL_R - 0.0014, 1, 40), waterM, false); cal.add(water);
  var WAREA = Math.PI * Math.pow(CAL_R - 0.0014, 2), WH0 = p.m2 / 1000 / WAREA, WBLOCK = Math.PI * BLOCK_R * BLOCK_R * BLOCK_H / WAREA;
  function setWater(h) { water.scale.y = h; water.position.y = 0.002 + h / 2; }
  setWater(WH0);
  var stir = new T.Group(); cal.add(stir);
  var srod = S.mesh(new T.CylinderGeometry(0.0013, 0.0013, 0.13, 10), copperM); srod.position.y = 0.065; stir.add(srod);
  var sring = S.mesh(new T.TorusGeometry(0.007, 0.0013, 8, 24), copperM); sring.rotation.x = Math.PI / 2; stir.add(sring);
  var STIR0 = new T.Vector3(-0.014, 0.006, 0.022); stir.position.copy(STIR0);
  var TWX = CX - 0.017, TWZ = CZ - 0.018;
  var thermoW = S.thermometer({ len: 0.3, min: 0, max: 50, value: p.T2, pos: [TWX, CY + 0.012, TWZ] });
  var standW = clampStand(TWX, TWZ, 0.28, 0.3, 0.44);
  var BLOCK_IN = new T.Vector3(CX + 0.012, CY + 0.0025, CZ);
  // tongs lying in front, jaws pointing left
  var TONG_L = 0.2, tongs = new T.Group(); S.scene.add(tongs);
  var armA = new T.Group(), armB = new T.Group(); tongs.add(armA); tongs.add(armB);
  [armA, armB].forEach(function (a, i) { var s = i ? 1 : -1; var bar = S.mesh(new T.BoxGeometry(0.006, TONG_L, 0.003), M.steel); bar.position.y = -TONG_L / 2; a.add(bar);
    var cup = S.mesh(new T.SphereGeometry(0.008, 14, 10, 0, Math.PI), M.steel); cup.rotation.y = s > 0 ? -Math.PI / 2 : Math.PI / 2; cup.position.set(-s * 0.002, -TONG_L + 0.004, 0); a.add(cup);
    var grip = S.mesh(new T.BoxGeometry(0.009, 0.05, 0.005), M.rubber); grip.position.y = -0.03; a.add(grip); });
  var pin = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.009, 14), M.brass); pin.rotation.x = Math.PI / 2; tongs.add(pin);
  function tongOpen(a) { armA.rotation.z = a; armB.rotation.z = -a; }
  var TONG_HOME = new T.Vector3(0.25, 0.009, 0.12), TONG_ROT = -Math.PI / 2;
  function placeTongs(pos, rot, open) { tongs.position.copy(pos); tongs.rotation.z = rot; tongOpen(open); tongShadow.position.set(pos.x - (rot ? 0.1 : 0), 0.0008, pos.z); tongShadow.material.opacity = Math.max(0.08, 0.4 - pos.y * 2); }
  var tongShadow = S.contact(0.24, 0.05, 0.14, 0.12, 0.4);
  placeTongs(TONG_HOME, TONG_ROT, 0.03);
  // a weighed-masses card
  var card = S.label('m₁ ' + Math.round(p.m1 * 1000) + ' g · water ' + Math.round(p.m2 * 1000) + ' g · cal.+stirrer ' + Math.round(p.mc * 1000) + ' g', { w: 0.2, ratio: 0.09, color: '#2a2a2a', bg: '#f5f1e6' });
  card.rotation.x = -Math.PI / 2; card.position.set(0.05, 0.001, 0.15); S.scene.add(card);
  var steamTex = S.canvasTex(128, 128, function (x) { var g = x.createRadialGradient(64, 64, 2, 64, 64, 62); g.addColorStop(0, 'rgba(255,255,255,.75)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });
  var wisps = []; for (i = 0; i < 6; i++) { var w = new T.Mesh(new T.PlaneGeometry(0.05, 0.05), new T.MeshBasicMaterial({ map: steamTex, transparent: true, opacity: 0, depthWrite: false })); w.userData.ph = i / 6; S.scene.add(w); wisps.push(w); }

  S.addApparatus('heater', heater, 'Hot plate', 'Keeps the water in the beaker boiling, so the metal is at 100 °C.');
  S.addApparatus('beaker', beaker, 'Beaker of boiling water', 'The metal sits on a wire gauze in it, never touching the hot bottom.');
  S.addApparatus('block', block, 'Metal cylinder', 'The solid whose specific heat you find. Mass m₁ = ' + Math.round(p.m1 * 1000) + ' g.');
  S.addApparatus('thermoB', thermoB, 'Thermometer (boiling water)', 'Range −10 to 110 °C, least count 0.5 °C. Gives T₁, the metal\'s temperature.');
  S.addApparatus('cal', cal, 'Copper calorimeter with stirrer', 'Holds ' + Math.round(p.m2 * 1000) + ' g of water. Calorimeter + stirrer = ' + Math.round(p.mc * 1000) + ' g of copper (c = 385 J/kg K).');
  S.addApparatus('jacket', jacket, 'Wooden insulating jacket', 'Wood and the air gap keep heat from leaking out of the calorimeter.');
  S.addApparatus('thermoW', thermoW, 'Thermometer (water)', 'Range 0 to 50 °C, read to 0.1 °C with a lens. Gives T₂ and the final temperature.');
  S.addApparatus('tongs', tongs, 'Tongs', 'Carry the hot metal quickly, so it loses little heat on the way.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hudB = S.hudCard('Boiling water'), hudW = S.hudCard('Water in calorimeter'), hudN = S.hudCard('Readings');

  // ---------- actions
  function Tw() { return st.dropped ? sim.y[1] : p.T2; }
  function switchHeater() {
    if (S.hand.busy) return Promise.resolve();
    return S.hand.tap(knob, 'tap').then(function () { st.heater = !st.heater; S.click(700, 0.05);
      S.say(st.heater ? 'Hot plate on. Let the water boil for a minute so the metal reaches 100 °C.' : 'Hot plate off.'); S.render(); });
  }
  function readT2() { if (st.dropped) { S.say('Too late: T₂ is read before the metal goes in.'); return; }
    st.T2 = r1(p.T2); bookLines[1] = 'Water + calorimeter, initial T₂ = ' + st.T2.toFixed(1) + ' °C'; S.book.draw(); S.focus('thermoW');
    S.say('Initial water temperature T₂ = ' + st.T2.toFixed(1) + ' °C.'); S.render(); }
  function readT1() { if (st.boiled < 60) { S.say('Not yet: let the water boil for at least a minute so the whole metal is at the boiling point.'); return; }
    st.T1 = r5(st.Tboil); bookLines[2] = 'Metal in boiling water, T₁ = ' + st.T1.toFixed(1) + ' °C'; S.book.draw(); S.focus('thermoB');
    S.say('Temperature of the hot metal T₁ = ' + st.T1.toFixed(1) + ' °C.'); S.render(); }
  function transfer() {
    if (S.hand.busy) return Promise.resolve();
    if (st.T1 === null || st.T2 === null) { S.say('Read T₂ (water) and T₁ (boiling water) first.'); return Promise.resolve(); }
    if (st.moved) { S.say('The metal is already in the calorimeter.'); return Promise.resolve(); }
    var down = new T.Vector3(0, TONG_L, 0), hang = new T.Vector3(0, -TONG_L + 0.004, 0);
    var g0 = TONG_HOME.clone().add(new T.Vector3(0, 0.004, 0)), g1 = new T.Vector3(HX + 0.02, PLATE + BH + TONG_L + 0.06, HZ + 0.03),
      g2 = BLOCK_HOME.clone().add(new T.Vector3(0, BLOCK_H / 2, 0)).sub(hang), g3 = new T.Vector3(BLOCK_IN.x, CY + CAL_H + TONG_L + 0.05, BLOCK_IN.z), g4 = g3.clone().add(new T.Vector3(0, -0.035, 0));
    var lerp = function (a, b, k) { return a.clone().lerp(b, k); };
    var arc = function (a, b, k, hgt) { return lerp(a, b, k).add(new T.Vector3(0, Math.sin(Math.PI * k) * hgt, 0)); };
    var blockOn = function (g) { block.position.copy(g).add(hang).add(new T.Vector3(0, -BLOCK_H / 2, 0)); };
    var legs = [
      { ms: 900, fn: function (k) { return arc(g0, g1, k, 0.05); }, onK: function (k) { placeTongs(arc(g0, g1, k, 0.05), TONG_ROT * (1 - k), 0.03 + 0.13 * k); } },
      { ms: 800, fn: function (k) { return lerp(g1, g2, k); }, onK: function (k) { placeTongs(lerp(g1, g2, k), 0, 0.16 - (k > 0.85 ? (k - 0.85) / 0.15 * 0.07 : 0)); } },
      { ms: 1300, fn: function (k) { return arc(g2, g3, k, 0.06); }, onK: function (k) { placeTongs(arc(g2, g3, k, 0.06), 0, 0.09); blockOn(arc(g2, g3, k, 0.06)); } },
      { ms: 450, fn: function (k) { return lerp(g3, g4, k); }, onK: function (k) { placeTongs(lerp(g3, g4, k), 0, k > 0.7 ? 0.16 : 0.09); if (k < 0.7) blockOn(lerp(g3, g4, k)); else drop(); } },
      { ms: 1000, fn: function (k) { return arc(g4, g0, k, 0.04); }, onK: function (k) { placeTongs(arc(g4, g0, k, 0.04), TONG_ROT * k, 0.16 - 0.13 * k); } },
    ];
    return carry(g0, legs, 'grip').then(function () { placeTongs(TONG_HOME, TONG_ROT, 0.03); drop(); if (S.fast) landBlock();
      S.say('The hot metal is in. Stir gently and watch the water thermometer climb.'); S.render(); });
  }
  function drop() { if (st.dropped) return; st.dropped = true; st.moved = true; st.fallV = 0; sim = K.init(p); }
  function landBlock() { block.position.copy(BLOCK_IN); setWater(WH0 + WBLOCK); }
  function stirIt() {
    if (S.hand.busy) return Promise.resolve();
    if (!st.dropped) { S.say('Stir after the metal is in.'); return Promise.resolve(); }
    var top = function (k) { return cal.position.clone().add(STIR0).add(new T.Vector3(0, 0.128 + 0.018 * Math.abs(Math.sin(3 * Math.PI * k)), 0)); };
    return S.hand.pinchMove(top(0), top, function (k) { stir.position.y = STIR0.y + 0.018 * Math.abs(Math.sin(3 * Math.PI * k)); }, { mode: 'top', ms: 1800 })
      .then(function () { stir.position.copy(STIR0); st.stirred++; S.render(); });
  }
  function recordTf() {
    if (!st.dropped) { S.say('Put the hot metal in first.'); return; }
    var rate = Math.abs(sim.y[0] - sim.y[1]);
    if (rate > 0.15) { S.say('The water is still warming (' + r1(Tw()).toFixed(1) + ' °C). Stir and wait until the reading stops rising.'); return; }
    if (S.rows.length) { S.say('Final temperature already written: ' + S.rows[0].Tf.toFixed(1) + ' °C.'); return; }
    S.addRow({ Tf: r1(Tw()), T1: st.T1, T2: st.T2 });
    S.say('Final (highest steady) temperature θ = ' + S.rows[0].Tf.toFixed(1) + ' °C. Written in your record book.');
  }
  var bookLines = ['Aim: specific heat of a solid by mixtures.', 'Water + calorimeter, initial T₂ = ……', 'Metal in boiling water, T₁ = ……',
    'm₁ = ' + Math.round(p.m1 * 1000) + ' g, m_w = ' + Math.round(p.m2 * 1000) + ' g, m_c = ' + Math.round(p.mc * 1000) + ' g', 'Heat lost by metal = heat gained by water + cal.',
    'c = (m_w c_w + m_c c_c)(θ − T₂) / m₁(T₁ − θ)'];
  function cOf(r) { var C = p.m2 * p.c2 + p.mc * p.cc; return C * (r.Tf - r.T2) / (p.m1 * (r.T1 - r.Tf)); }
  function setSpeed(v) { st.speed = v; S.render(); }

  return {
    camera: { pos: [0.36, 0.56, 1.08], look: [0.02, 0.12, -0.08] },
    views: { heater: [[0.0, 0.32, 0.42], [HX, 0.1, HZ]], beaker: [[-0.04, 0.3, 0.32], [HX, 0.1, HZ]], block: [[-0.06, 0.28, 0.22], [HX, 0.08, HZ]],
      thermoB: [[-0.08, 0.3, 0.2], [HX - 0.02, 0.22, HZ]], cal: [[0.28, 0.3, 0.3], [CX, 0.08, CZ]], jacket: [[0.32, 0.22, 0.32], [CX, 0.05, CZ]],
      thermoW: [[0.24, 0.28, 0.18], [TWX + 0.005, 0.2, CZ]], tongs: [[0.3, 0.25, 0.42], [0.15, 0.02, 0.1]], transfer: [[0.12, 0.48, 0.68], [0.02, 0.15, -0.08]],
      stand: [[0.4, 0.5, 0.7], [0, 0.25, -0.3]], book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]] },
    theory: { principle: 'When a hot solid is dropped into cold water in a calorimeter, heat flows until all of them reach one final temperature θ. If no heat leaks out, the heat lost by the solid equals the heat gained by the water and the calorimeter.',
      formula: 'm₁c (T₁ − θ) = (m_w c_w + m_c c_c)(θ − T₂)', formulaNote: 'so c = (m_w c_w + m_c c_c)(θ − T₂) / m₁(T₁ − θ) · c_w = 4186, c_c = 385 J/(kg·K)',
      more: ['T₁ is the solid\'s temperature (boiling water), T₂ the starting temperature of the water and calorimeter, θ the highest steady temperature after mixing.'],
      precautions: 'Let the solid stay in boiling water long enough to reach 100 °C. Transfer it quickly with tongs, without splashing. Stir gently. Read θ as the highest steady reading. Keep the calorimeter in its jacket.' },
    book: { title: 'Expt. — Specific Heat (Mixtures)', lines: bookLines,
      columns: [{ label: 'T₁ (°C)', get: function (r) { return r.T1.toFixed(1); } }, { label: 'T₂ (°C)', get: function (r) { return r.T2.toFixed(1); } },
        { label: 'θ (°C)', get: function (r) { return r.Tf.toFixed(1); } }, { label: 'c (J/kg K)', get: function (r) { return Math.round(cOf(r)); } }] },
    result: function (rows) { if (!rows.length) return null; var c = S.fit.mean(rows.map(cOf));
      return { label: 'c (solid)', value: c, unit: 'J/(kg·K)', digits: 0, truth: p.c1, note: 'From the heat balance with θ = ' + rows[0].Tf.toFixed(1) + ' °C.' }; },
    resultNote: 'Heat lost to the air during the transfer and while mixing makes θ a little low, so c comes out a little low in a real lab.',
    tol: 0.02,
    chips: ['Why use tongs and move quickly?', 'Why a wooden jacket?', 'Why stir?', 'Check my readings', 'Why is my c different from the table value?'],
    viva: [['Why should the metal be transferred quickly?', ['So that it loses little heat to the air on the way', 'So that the water does not boil', 'So that the stirrer does not move'], 0, 'Any heat lost on the way is not counted in the balance, so c comes out low.'],
      ['What does θ mean in this experiment?', ['The highest steady temperature of the mixture', 'The temperature of the boiling water', 'The room temperature'], 0, 'Read θ when the thermometer stops rising.']],
    askState: function () { return { heater_on: st.heater, boiling_water_C: r5(st.Tboil), boiled_for_s: Math.round(st.boiled), T1_C: st.T1, T2_C: st.T2, metal_in_calorimeter: st.dropped,
      water_thermometer_C: r1(st.shownW), times_stirred: st.stirred, time_runs_faster_by: st.speed, final_recorded: S.rows.length ? S.rows[0].Tf : null }; },

    steps: [
      { id: 'heat', title: 'Heat the metal', view: 'heater', render: function (u) {
          u.h2('Heat the metal, read T₁ and T₂');
          u.task('1. Switch on the hot plate', st.heater, st.heater ? 'On: ' + (st.boiled > 0 ? 'boiling for ' + Math.round(st.boiled) + ' s' : 'heating the water') : 'Off')
            .add(u.button(st.heater ? 'Switch off' : 'Switch on the hot plate', function () { switchHeater(); }, !st.heater, S.hand.busy || st.moved));
          u.task('2. Read the water in the calorimeter (T₂)', st.T2 !== null, st.T2 !== null ? 'T₂ = ' + st.T2.toFixed(1) + ' °C' : 'Before the metal goes in')
            .add(u.button('Read T₂', readT2, false, st.T2 !== null));
          u.task('3. Read the boiling water (T₁)', st.T1 !== null, st.T1 !== null ? 'T₁ = ' + st.T1.toFixed(1) + ' °C' : 'After at least one minute of boiling')
            .add(u.button('Read T₁', readT1, false, st.T1 !== null || !st.heater));
          u.live(function () { return 'Boiling-water thermometer: ' + r5(st.Tboil).toFixed(1) + ' °C' + (st.boiled > 0 ? ' · boiling ' + Math.round(st.boiled) + ' s' : ''); });
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 5, 20].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.next('Next: drop in the hot metal', st.T1 !== null && st.T2 !== null);
        },
        ok: function () { return st.T1 !== null && st.T2 !== null; },
        auto: function () { readT2(); return (st.heater ? Promise.resolve() : switchHeater()).then(function () { S.advance(120, function () { return st.boiled >= 61; }); readT1(); }); } },
      { id: 'mix', title: 'Mix', view: 'transfer', render: function (u) {
          u.h2('Transfer the metal and stir');
          u.task('1. Move the hot metal into the calorimeter with the tongs', st.moved, st.moved ? 'In the water' : 'Quickly, without splashing')
            .add(u.button(st.moved ? 'Done' : 'Transfer with the tongs', function () { transfer(); S.render(); }, !st.moved, st.moved || S.hand.busy));
          u.task('2. Stir gently', st.stirred > 0, st.stirred ? 'Stirred ' + st.stirred + ' time' + (st.stirred > 1 ? 's' : '') : 'Up and down, slowly')
            .add(u.button('Stir', function () { stirIt(); }, st.moved && !st.stirred, !st.moved || S.hand.busy));
          u.live(function () { return 'Water thermometer: ' + r1(st.shownW).toFixed(1) + ' °C'; });
          u.next('Next: read the final temperature', st.moved && st.stirred > 0);
        },
        ok: function () { return st.moved && st.stirred > 0; },
        auto: function () { return transfer().then(stirIt); } },
      { id: 'final', title: 'Final temperature', view: 'thermoW', render: function (u) {
          u.h2('Read the highest steady temperature θ');
          u.p('Keep stirring now and then. The reading climbs, then stops. Write θ when it no longer rises.');
          u.live(function () { return 'Water thermometer: ' + r1(st.shownW).toFixed(1) + ' °C'; });
          u.row(u.button('Stir again', function () { stirIt(); }, false, S.hand.busy), u.button('Record θ', recordTf, true, S.rows.length > 0));
          var sp = u.row(); sp.appendChild(document.createTextNode('Time runs: '));
          [1, 5, 20].forEach(function (v) { sp.appendChild(u.button((st.speed === v ? '✓ ' : '') + v + '×', function () { setSpeed(v); }, false, false)); });
          u.h3('Observation table'); u.table();
          if (S.rows.length) u.note('Removed the reading by mistake? Delete it with × and record again.');
          u.next('Next: work out c', S.rows.length >= 1);
        },
        ok: function () { return S.rows.length >= 1; },
        auto: function () { S.advance(600, function () { return Math.abs(sim.y[0] - sim.y[1]) < 0.01; }); recordTf(); return Promise.resolve(); } },
    ],

    tick: function (dt) {
      var ldt = dt * st.speed;
      // the boiling beaker: heats towards 100 °C while the plate is on, cools slowly when off
      var boilPt = 100;
      if (st.heater) st.Tboil = Math.min(boilPt, st.Tboil + ldt * 0.9 * (1 + (boilPt - st.Tboil) / 30)); else st.Tboil += (32 - st.Tboil) * Math.min(1, ldt * 0.004);
      if (st.heater && st.Tboil >= boilPt - 0.01) st.boiled += ldt; else if (!st.heater) st.boiled = 0;
      thermoB.set(st.Tboil);
      if (!st.moved) st.blockT = st.Tboil;
      if (st.dropped) K.step(sim, p, ldt);
      // falling block, water rise
      if (st.dropped && block.position.y > BLOCK_IN.y + 1e-4) { st.fallV += 9.8 * dt * (block.position.y < CY + 0.002 + WH0 ? 0.15 : 1); block.position.y = Math.max(BLOCK_IN.y, block.position.y - st.fallV * dt);
        block.position.x += (BLOCK_IN.x - block.position.x) * Math.min(1, dt * 8); block.position.z += (BLOCK_IN.z - block.position.z) * Math.min(1, dt * 8); }
      if (st.dropped) { var sub = Math.max(0, Math.min(1, (CY + 0.002 + WH0 + BLOCK_H - block.position.y) / BLOCK_H)); setWater(WH0 + WBLOCK * sub); }
      st.shownW += (Tw() - st.shownW) * Math.min(1, dt * 4); thermoW.set(st.shownW);
      // heater glow + lamp
      var on = st.heater ? 1 : 0; lamp.material.emissive.setRGB(on * 1.4, on * 0.1, 0); coil.material.emissive.setRGB(on * 0.35, on * 0.06, 0);
      // bubbles + steam over the boiling beaker
      var boil = st.heater ? Math.max(0, Math.min(1, (st.Tboil - 85) / 15)) : 0, now = (st.clock = (st.clock || 0) + dt);
      bubbles.forEach(function (b) { var u2 = b.userData, ph = (now * 1.6 + u2.ph) % 1; b.visible = boil > 0.05 && ph < boil;
        b.position.set(HX + u2.x * (1 - ph * 0.3), PLATE + 0.006 + ph * 0.066, HZ + u2.z); });
      wisps.forEach(function (w) { var ph = (now * 0.25 + w.userData.ph) % 1; w.position.set(HX + Math.sin(ph * 6 + w.userData.ph * 9) * 0.015, PLATE + BH + 0.01 + ph * 0.13, HZ);
        w.quaternion.copy(S.camera.quaternion); w.scale.setScalar(0.6 + ph * 1.4); w.material.opacity = boil * 0.35 * Math.sin(ph * Math.PI); });
      hudB.set(r5(st.Tboil).toFixed(1) + ' °C'); hudW.set(r1(st.shownW).toFixed(1) + ' °C'); hudN.set(String(S.rows.length));
    },
  };
});
