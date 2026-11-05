/* Prayogshala studio module: the GALVANOMETER BENCH (NCERT Class XII, Section A). One apparatus, three set-ups:
     galvanometer-half-deflection  - the resistance G of the galvanometer and its figure of merit,
     galvanometer-to-voltmeter     - a high resistance in series makes a voltmeter of a chosen range,
     galvanometer-to-ammeter       - a shunt wire in parallel makes an ammeter of a chosen range.
   A centre-zero moving-coil galvanometer, plug-type decade resistance boxes whose dials the hand turns, plug keys,
   a 2 V accumulator or a DC supply, a rheostat, a manganin shunt wire with a sliding contact, and the standard
   meters the converted ones are checked against. Every current comes from the circuit kernel (kernels.js, modified
   nodal analysis) on the lab's own net and params - the same numbers the server checks. */
HoolaStudio.define('galvanometer-board', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, KC = HK.K.circuit, CFG = S.lab.cfg;
  var p = HK.paramsFor('circuit', S.lab.params);
  var ID = S.lab.id || '';
  var MODE = /half/.test(ID) ? 'half' : /voltmeter/.test(ID) ? 'volt' : 'amm';
  var FOM = p.FOM, FS = 30, IG = FOM * FS;            // figure of merit, full scale, full-scale current
  var LAM = p.lam || 1.209;                            // shunt wire: ohms per metre
  var RANGE = MODE === 'volt' ? p.Vrange : p.Irange;
  var st = { traced: false, key: false, k2: false, R: 0, Sh: 0, th1: 0, E: 0, power: false, Rl: p.Rl || 20, ls: 1.0 };

  // ---------------------------------------------------------------- small helpers (kept inside this module)
  function wpt(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function post(x, y, z, color) { var t = S.terminal([x, y, z], color); return { g: t, at: new T.Vector3(x, y + 0.009, z) }; }
  function lead(a, b, color, via, lift) {
    var up = lift || 0.014, pts = [[a.x, a.y, a.z], [a.x, a.y + up, a.z]];
    (via || []).forEach(function (v) { pts.push(v.length === 2 ? [v[0], 0.0035, v[1]] : v); });
    pts.push([b.x, b.y + up, b.z], [b.x, b.y, b.z]);
    var w = S.wire(pts, color); if (color === 'black') { w.material.color.setHex(0x111113); w.material.roughness = 0.8; } return w;
  }
  function busy() { if (S.hand.busy) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function r1(v) { return Math.round(v * 10) / 10; }
  function fnum(v, d) { return v.toFixed(d === undefined ? 1 : d); }

  // ---------------------------------------------------------------- decade resistance box (the hand turns its dials)
  function decadeBox(x, z, muls, title) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var n = muls.length, W = 0.06 + n * 0.055, D = 0.13, H = 0.052;
    var body = S.rounded(W, D, H, 0.006, M.darkWood); body.rotation.x = -Math.PI / 2; body.position.y = H / 2; g.add(body);
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
      var ft = S.mesh(new T.CylinderGeometry(0.008, 0.009, 0.003, 14), M.rubber); ft.position.set(f[0] * (W / 2 - 0.016), 0.0015, f[1] * (D / 2 - 0.016)); g.add(ft); });
    var dx = muls.map(function (m, i) { return -(n - 1) * 0.055 / 2 + i * 0.055; });
    var PW = W - 0.008, PD = D - 0.008;
    var tex = S.canvasTex(Math.round(1400), Math.round(1400 * PD / PW), function (c, w, h) {
      var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (v / PD + 0.5) * h; }, k = w / PW;
      c.fillStyle = '#171a1f'; c.fillRect(0, 0, w, h);
      c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 3; c.strokeRect(10, 10, w - 20, h - 20);
      c.fillStyle = '#eceadf'; c.font = '700 ' + Math.round(k * 0.009) + 'px "Public Sans", sans-serif'; c.textAlign = 'left';
      c.fillText(title, 26, Math.round(k * 0.014));
      muls.forEach(function (m, i) {
        var cx = X(dx[i]), cy = Y(0.006), R = 0.027 * k;
        c.strokeStyle = '#8b9099'; c.lineWidth = 2; c.beginPath(); c.arc(cx, cy, R * 0.72, 0, Math.PI * 2); c.stroke();
        c.textAlign = 'center'; c.fillStyle = '#eceadf'; c.font = '600 ' + Math.round(k * 0.0075) + 'px "Public Sans", sans-serif';
        for (var d = 0; d < 10; d++) { var a = d * Math.PI / 5; c.fillText(String(d), cx + Math.sin(a) * R, cy + Math.cos(a) * R + k * 0.0026); }
        c.fillStyle = '#f0c36b'; c.font = '700 ' + Math.round(k * 0.007) + 'px "Public Sans", sans-serif';
        c.fillText('x ' + m, cx, Y(-0.05));
      });
      c.textAlign = 'right'; c.fillStyle = '#9aa1ab'; c.font = '500 ' + Math.round(k * 0.0055) + 'px "Public Sans", sans-serif';
      c.fillText('OHMS  +/- 0.5 %', w - 26, h - 22); c.textAlign = 'left';
    });
    var panel = new T.Mesh(new T.PlaneGeometry(PW, PD), new T.MeshStandardMaterial({ map: tex, roughness: 0.45 }));
    panel.rotation.x = -Math.PI / 2; panel.position.y = H + 0.0006; g.add(panel);
    var knurl = S.canvasTex(256, 32, function (c, w, h) { c.fillStyle = '#15161a'; c.fillRect(0, 0, w, h); c.fillStyle = '#3b3e45'; for (var i = 0; i < w; i += 9) c.fillRect(i, 0, 3, h); });
    var dials = muls.map(function (m, i) {
      var d = new T.Group(); d.position.set(dx[i], H + 0.001, 0.006); g.add(d);
      var kb = S.mesh(new T.CylinderGeometry(0.0165, 0.018, 0.013, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.42 })); kb.position.y = 0.0065; d.add(kb);
      var cap = S.mesh(new T.CylinderGeometry(0.0125, 0.0125, 0.0015, 36), M.chrome); cap.position.y = 0.0138; d.add(cap);
      var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.0012, 0.015), M.white, false); ptr.position.set(0, 0.0146, 0.0085); d.add(ptr);
      return { g: d, mul: m, digit: 0, top: new T.Vector3(x + dx[i], H + 0.016, z + 0.006) };
    });
    var tL = post(x - W / 2 + 0.014, H, z - D / 2 + 0.012), tR = post(x + W / 2 - 0.014, H, z - D / 2 + 0.012);
    S.contact(W + 0.06, D + 0.06, x, z, 0.5);
    return { group: g, dials: dials, tL: tL, tR: tR, muls: muls,
      value: function () { var v = 0; dials.forEach(function (d) { v += d.digit * d.mul; }); return v; },
      max: function () { var v = 0; dials.forEach(function (d) { v += 9 * d.mul; }); return v; },
      look: function () { dials.forEach(function (d) { d.g.rotation.y = d.digit * Math.PI / 5; }); } };
  }
  function digitsFor(box, value) {
    var left = Math.round(value), out = [];
    box.muls.forEach(function (m) { var d = Math.max(0, Math.min(9, Math.floor(left / m + 1e-9))); out.push(d); left -= d * m; });
    return out;
  }
  function setBox(box, value, onDone) {
    if (busy()) return Promise.resolve(false);
    if (!(value >= 0 && value <= box.max())) { S.say('This box goes from 0 to ' + box.max() + ' ohms only.'); return Promise.resolve(false); }
    var want = digitsFor(box, value), jobs = [];
    want.forEach(function (d, i) { if (box.dials[i].digit !== d) jobs.push([i, d]); });
    return jobs.reduce(function (pr, j) {
      return pr.then(function () {
        var dl = box.dials[j[0]], a = dl.digit, b = j[1];
        return S.hand.pinchMove(dl.top, function () { return dl.top; }, function (k) {
          dl.digit = a + (b - a) * k; box.look(); S.hand.group.rotation.y = -(dl.digit - a) * 0.12;
        }, { mode: 'top', ms: 420 + 60 * Math.abs(b - a), reachMs: 520 })
          .then(function () { dl.digit = b; box.look(); S.hand.group.rotation.y = 0; S.click(1200, 0.02, 0.05); });
      });
    }, Promise.resolve()).then(function () { if (onDone) onDone(box.value()); S.render(); return true; });
  }

  // ---------------------------------------------------------------- plug key (the hand pulls the plug out / pushes it in)
  function plugKey(x, z, name) {
    var key = S.plugKey([x, 0, z]), plug = key.userData.plug;
    var tl = post(x - 0.02, 0.022, z - 0.008), tr = post(x + 0.02, 0.022, z - 0.008);
    var lb = S.label(name, { w: 0.022, ratio: 0.5, color: '#e9e4d6' }); lb.rotation.x = -Math.PI / 2; lb.position.set(x, 0.0165, z + 0.016); S.scene.add(lb);
    var ZAX = new T.Vector3(0, 0, 1);
    function pose(k) { return { x: 0.062 * (1 - k), y: 0.008 + 0.016 * k + 0.04 * Math.sin(Math.PI * k), z: 0.012 * (1 - k), rz: Math.PI / 2 * (1 - k) }; }
    function apply(k) { var q = pose(k); plug.position.set(q.x, q.y, q.z); plug.rotation.set(0, 0, q.rz); }
    function head(k) { var q = pose(k); return key.localToWorld(new T.Vector3(0, 0.013, 0).applyAxisAngle(ZAX, q.rz).add(new T.Vector3(q.x, q.y, q.z))); }
    apply(0);
    return { group: key, tl: tl, tr: tr, apply: apply, head: head };
  }
  function toggleKey(k, on, label) {
    if (busy()) return Promise.resolve();
    var a = k.closed ? 1 : 0, b = on ? 1 : 0;
    if (a === b) return Promise.resolve();
    return S.hand.pinchMove(k.head(a), function (q) { return k.head(a + (b - a) * q); }, function (q) { k.apply(a + (b - a) * q); }, { ms: 850, mode: 'top' })
      .then(function () { k.apply(b); k.closed = !!on; S.click(1400, 0.04, 0.1);
        S.say(on ? label + ' closed.' : label + ' open: no current flows now.'); S.render(); });
  }

  // ---------------------------------------------------------------- the galvanometer (centre zero, 30-0-30)
  var gal = S.meter({ min: -FS, max: FS, zeroCentre: true, ticks: 6, unit: 'div', symbol: 'G',
    caption: 'GALVANOMETER  30–0–30 div', pos: [-0.02, 0, -0.68] });
  var gP = { at: wpt(gal, 0.035, 0.07, -0.03) }, gM = { at: wpt(gal, -0.035, 0.07, -0.03) };
  var gTag = S.label(MODE === 'half' ? 'G = ?' : 'G = ' + fnum(p.Rg, 0) + ' ohm,  k = ' + (FOM * 1e6).toFixed(1) + ' uA/div',
    { w: MODE === 'half' ? 0.05 : 0.16, ratio: MODE === 'half' ? 0.3 : 0.085, px: 1024, color: '#2b2f36' });
  gTag.rotation.x = -Math.PI / 2; gTag.position.set(-0.02, 0.0012, -0.56); S.scene.add(gTag);

  // ---------------------------------------------------------------- source: a 2 V accumulator, or a DC supply for the voltmeter
  var src, srcP, srcM, supplyKnob = null;
  if (MODE === 'volt') {
    src = S.powerBox([-0.66, 0, -0.42], 'DC SUPPLY 0 – 3 V');
    srcP = { at: wpt(src.userData.plus, 0, 0.012, 0) }; srcM = { at: wpt(src.userData.minus, 0, 0.012, 0) };
    supplyKnob = src.userData.knob;
    var sLab = S.label('0        1        2        3  V', { w: 0.1, ratio: 0.1, px: 1024, color: '#e8e8e8' });
    sLab.position.set(-0.66, 0.058, -0.368); src.add(sLab);
  } else {
    src = new T.Group(); S.scene.add(src); src.position.set(-0.66, 0, -0.42);
    var acc = S.rounded(0.08, 0.1, 0.07, 0.006, M.bakelite); acc.position.y = 0.055; src.add(acc);
    var lid = S.rounded(0.086, 0.012, 0.076, 0.004, M.blackPlastic); src.add(lid); lid.position.y = 0.112;
    [-0.022, 0.022].forEach(function (vx) { var v = S.mesh(new T.CylinderGeometry(0.007, 0.007, 0.008, 16), new T.MeshStandardMaterial({ color: 0xd8862a, roughness: 0.5 })); v.position.set(vx, 0.122, 0); src.add(v); });
    var aL = S.label(MODE === 'amm' ? '6 V' : '2 V', { w: 0.04, ratio: 0.45, color: '#f2f2f2' }); aL.position.set(0, 0.066, 0.0356); src.add(aL);
    var aL2 = S.label('ACCUMULATOR', { w: 0.055, ratio: 0.16, color: '#c9ccd1' }); aL2.position.set(0, 0.04, 0.0356); src.add(aL2);
    S.contact(0.14, 0.13, -0.66, -0.42, 0.55);
    srcP = post(-0.638, 0.118, -0.42, 'red'); srcM = post(-0.682, 0.118, -0.42, 'black');
  }

  // ---------------------------------------------------------------- mode-specific apparatus
  var key1 = plugKey(-0.52, -0.12, 'K1'); key1.closed = false;
  var rBox = MODE === 'amm' ? null : decadeBox(-0.26, -0.5, [1000, 100, 10, 1], MODE === 'half' ? 'HIGH RESISTANCE BOX  R' : 'RESISTANCE BOX  R');
  var shBox = null, key2 = null, stdMeter = null, rheo = null, shunt = null;
  function boxR() { return rBox ? rBox.value() : 0; }

  if (MODE === 'half') {
    shBox = decadeBox(0.3, -0.5, [100, 10, 1], 'SHUNT BOX  S');
    key2 = plugKey(0.34, -0.16, 'K2'); key2.closed = false;
  } else if (MODE === 'volt') {
    stdMeter = S.meter({ min: 0, max: 3, ticks: 6, unit: 'V', symbol: 'V', caption: 'STANDARD VOLTMETER 0–3 V', pos: [0.36, 0, -0.66], rotY: 0.2 });
  } else {
    stdMeter = S.meter({ min: 0, max: 0.5, ticks: 5, unit: 'A', symbol: 'A', caption: 'STANDARD AMMETER 0–0.5 A', pos: [0.36, 0, -0.66], rotY: 0.2 });
    rheo = S.rheostat([-0.06, 0, -0.26], 0.24);
    var rhL = post(-0.18, 0.062, -0.26), rhR = post(0.06, 0.062, -0.26);
    // the shunt: a thick manganin wire on a small board, with a sliding brass bridge that sets its length
    shunt = (function () {
      var g = new T.Group(); S.scene.add(g); g.position.set(0.2, 0, -0.06);
      var bd = S.rounded(0.16, 0.05, 0.014, 0.004, M.wood); bd.rotation.x = -Math.PI / 2; bd.position.y = 0.007; g.add(bd);
      var scl = S.canvasTex(1024, 128, function (c, w, h) { c.drawImage(S.woodTex.image, 0, 0, w, h);
        c.fillStyle = 'rgba(255,248,230,.5)'; c.fillRect(0, 0, w, h); c.fillStyle = '#171717';
        var k = (w - 40) / 100;
        for (var i = 0; i <= 100; i++) { var xx = 20 + i * k; c.fillRect(xx - 0.7, 0, i % 10 ? 1.4 : 2.4, i % 10 === 0 ? 44 : i % 5 === 0 ? 32 : 18);
          if (i % 10 === 0) { c.font = '600 26px "Public Sans", sans-serif'; c.textAlign = 'center'; c.fillText(String(i / 10), xx, 76); } }
        c.font = '600 22px "Public Sans", sans-serif'; c.textAlign = 'left'; c.fillStyle = '#6b4a14'; c.fillText('MANGANIN SHUNT  cm', 24, 112); });
      var sp = new T.Mesh(new T.PlaneGeometry(0.13, 0.016), new T.MeshStandardMaterial({ map: scl, roughness: 0.6 }));
      sp.rotation.x = -Math.PI / 2; sp.position.set(0, 0.0146, 0.014); g.add(sp);
      var wire = S.mesh(new T.CylinderGeometry(0.0008, 0.0008, 0.12, 12), new T.MeshStandardMaterial({ color: 0xc8b9a0, roughness: 0.25, metalness: 1 }));
      wire.rotation.z = Math.PI / 2; wire.position.set(0, 0.0202, -0.008); g.add(wire);
      [-0.06, 0.06].forEach(function (ex) { var pl = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.01, 16), M.brass); pl.position.set(ex, 0.019, -0.008); g.add(pl); });
      var br = new T.Group(); g.add(br);
      var blk = S.rounded(0.014, 0.014, 0.02, 0.002, M.brass); blk.position.y = 0.0245; br.add(blk);
      var jaw = S.mesh(new T.BoxGeometry(0.004, 0.006, 0.016), M.chrome); jaw.position.set(0, 0.019, -0.008); br.add(jaw);
      var kn = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.008, 16), M.blackPlastic); kn.position.y = 0.0355; br.add(kn);
      S.contact(0.21, 0.1, 0.2, -0.06, 0.45);
      return { group: g, bridge: br, tL: post(0.14, 0.015, -0.062), tR: post(0.26, 0.015, -0.062),
        place: function (l) { br.position.set(-0.06 + 0.12 * (l / 10), 0, -0.008); },
        head: function (l) { return new T.Vector3(0.2 - 0.06 + 0.12 * (l / 10), 0.042, -0.068); } };
    })();
    shunt.place(st.ls);
  }

  // ---------------------------------------------------------------- the leads, terminal to terminal
  if (MODE === 'half') {
    lead(srcP.at, key1.tl.at, 'red', [[-0.72, -0.3], [-0.62, -0.2]]);
    lead(key1.tr.at, rBox.tL.at, 'red', [[-0.48, -0.14], [-0.42, -0.4]]);
    lead(rBox.tR.at, gP.at, 'red', [[-0.2, -0.42], [-0.06, -0.52]]);
    lead(gM.at, srcM.at, 'black', [[-0.2, -0.72], [-0.6, -0.68], [-0.78, -0.58]]);
    lead(gP.at, shBox.tL.at, '#d9a520', [[0.08, -0.56], [0.2, -0.44]]);
    lead(shBox.tR.at, key2.tr.at, '#d9a520', [[0.4, -0.42], [0.4, -0.2]]);
    lead(key2.tl.at, gM.at, 'blue', [[0.22, -0.2], [0.04, -0.66]]);
  } else if (MODE === 'volt') {
    lead(srcP.at, key1.tl.at, 'red', [[-0.72, -0.3], [-0.62, -0.2]]);
    lead(key1.tr.at, rBox.tL.at, 'red', [[-0.48, -0.14], [-0.42, -0.4]]);
    lead(rBox.tR.at, gP.at, 'red', [[-0.2, -0.42], [-0.06, -0.52]]);
    lead(gM.at, srcM.at, 'black', [[-0.2, -0.72], [-0.6, -0.7], [-0.8, -0.56]]);
    lead(key1.tr.at, { x: 0.396, y: 0.082, z: -0.69 }, '#d9a520', [[-0.3, -0.06], [0.1, -0.3], [0.34, -0.5]]);
    lead({ x: 0.324, y: 0.082, z: -0.69 }, gM.at, 'blue', [[0.2, -0.74], [0.0, -0.76]]);
  } else {
    lead(srcP.at, key1.tl.at, 'red', [[-0.72, -0.3], [-0.62, -0.2]]);
    lead(key1.tr.at, rhL.at, 'red', [[-0.44, -0.12], [-0.26, -0.2]]);
    lead(rhR.at, { x: 0.324, y: 0.082, z: -0.69 }, 'red', [[0.16, -0.3], [0.3, -0.56]]);
    lead({ x: 0.396, y: 0.082, z: -0.69 }, gP.at, '#d9a520', [[0.24, -0.76], [0.06, -0.74]]);
    lead(gM.at, srcM.at, 'black', [[-0.22, -0.74], [-0.62, -0.7], [-0.8, -0.56]]);
    lead(gP.at, shunt.tL.at, 'blue', [[0.04, -0.5], [0.12, -0.2]]);
    lead(shunt.tR.at, gM.at, 'blue', [[0.3, -0.2], [0.08, -0.62]]);
  }

  S.addApparatus('gal', gal, 'Moving-coil galvanometer (30–0–30)',
    'A centre-zero galvanometer. The deflection is proportional to the current through its coil; ' + (MODE === 'half' ? 'its own resistance G is what we find.' : 'it needs ' + (IG * 1000).toFixed(2) + ' mA for full-scale deflection.'));
  if (rBox) S.addApparatus('rb', rBox.group, MODE === 'half' ? 'High resistance box R (1–9999 Ω)' : 'Resistance box R (1–9999 Ω)',
    'Four dials: thousands, hundreds, tens and units. Turn them to set the resistance in the circuit.');
  S.addApparatus('key', key1.group, 'Plug key K₁', 'Insert the plug only while taking a reading, so nothing heats up.');
  S.addApparatus('src', src, MODE === 'volt' ? 'Variable DC supply (0–3 V)' : MODE === 'amm' ? 'Accumulator (6 V)' : 'Accumulator (2 V)',
    MODE === 'volt' ? 'Turn the knob to apply a known voltage to both meters.' : 'Drives a steady current through the circuit.');
  if (MODE === 'half') {
    S.addApparatus('sb', shBox.group, 'Shunt resistance box S (1–999 Ω)', 'Goes across the galvanometer through key K₂, and takes part of the current.');
    S.addApparatus('key2', key2.group, 'Plug key K₂', 'Closing it puts the shunt S across the galvanometer.');
  } else {
    S.addApparatus('std', stdMeter, MODE === 'volt' ? 'Standard voltmeter (0–3 V)' : 'Standard ammeter (0–0.5 A)',
      'The laboratory meter the converted galvanometer is checked against.');
  }
  if (MODE === 'amm') {
    S.addApparatus('rheo', rheo, 'Rheostat', 'Changes the current in the circuit so that several readings can be taken.');
    S.addApparatus('shunt', shunt.group, 'Manganin shunt wire', 'A thick manganin wire of ' + LAM.toFixed(3) + ' ohm per metre. The sliding bridge sets the length that is in the circuit.');
  }
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  // ---------------------------------------------------------------- physics: the circuit kernel on the lab's net
  function live() {
    var o = { k1: st.key ? 1 : 0 };
    if (MODE === 'half') { o.k2 = st.k2 ? 1 : 0; o.Rh = Math.max(boxR(), 1e-3); o.Sh = Math.max(shBox.value(), 1e-3); }
    else if (MODE === 'volt') { o.Eb = st.power ? st.E : 0; o.Rser = Math.max(boxR(), 1e-3); }
    else { o.Rl = st.Rl; o.Sht = LAM * st.ls / 100; }
    return o;
  }
  function solve(over) {
    var q = HK.assign(p, live()); if (over) q = HK.assign(q, over);
    return KC.view(KC.init(q, CFG), q, CFG);
  }
  function defl(over) { if (!st.key) return 0; return r1(solve(over).I_G / FOM); }
  function stdRead() {
    if (!st.key) return 0;
    var v = solve();
    return MODE === 'volt' ? Math.round(v.V_VM / 0.02) * 0.02 : Math.round(v.I_AM / 0.005) * 0.005;
  }
  function shuntOhm() { return LAM * st.ls / 100; }
  function needR() { return RANGE / IG - p.Rg; }                        // series resistance for the chosen range
  function needS() { return p.Rg * IG / (RANGE - IG); }                 // shunt for the chosen range
  function needL() { return r1(needS() / LAM * 100); }                  // that shunt as a length of the wire, in cm
  function trueRange() {
    if (MODE === 'volt') return (boxR() + p.Rg) * IG;
    var s = shuntOhm(); return IG * (p.Rg + s) / s;
  }
  var hudA = S.hudCard(MODE === 'half' ? 'Resistance box R' : MODE === 'volt' ? 'Series R' : 'Shunt length'),
    hudB = S.hudCard('Galvanometer'), hudC = S.hudCard(MODE === 'half' ? 'Shunt box S' : MODE === 'volt' ? 'Standard voltmeter' : 'Standard ammeter');

  // ---------------------------------------------------------------- human actions
  function trace() {
    st.traced = true; S.focus('bench');
    S.say(MODE === 'half' ? 'Accumulator, key K1, the high resistance box R and the galvanometer are in series. The shunt box S with key K2 is across the galvanometer.'
      : MODE === 'volt' ? 'The resistance box R is in series with the galvanometer: that pair is the converted voltmeter. The standard voltmeter is across the same two points.'
      : 'The shunt wire is across the galvanometer: that pair is the converted ammeter. The standard ammeter, the rheostat and the key are in series with it.');
    S.render();
  }
  function setR(v) { return setBox(rBox, v, function (got) { st.R = got; S.say('Resistance box set to ' + got + ' ohm.'); }); }
  function setS(v) { return setBox(shBox, v, function (got) { st.Sh = got; }); }
  function setKey1(on) { return toggleKey(key1, on, 'Key K1').then(function () { st.key = key1.closed; S.render(); }); }
  function setKey2(on) { return toggleKey(key2, on, 'Key K2').then(function () { st.k2 = key2.closed; S.render(); }); }
  function setSupply(E) {
    if (busy()) return Promise.resolve();
    if (!(E >= 0 && E <= 3.0001)) { S.say('The supply goes from 0 to 3 V only.'); return Promise.resolve(); }
    var E0 = st.E, a0 = supplyKnob.rotation.z, at = wpt(supplyKnob, 0, 0, 0.006);
    return S.hand.pinchMove(at, function () { return at; }, function (k) {
      st.E = E0 + (E - E0) * k; supplyKnob.rotation.z = a0 - (st.E - E0) * 1.6; }, { mode: 'front', ms: 450 + 300 * Math.abs(E - E0), reachMs: 600 })
      .then(function () { st.E = Math.round(E * 100) / 100; S.render(); });
  }
  function setPower(on) {
    if (busy()) return Promise.resolve();
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(supplyKnob, 'front').then(function () { st.power = on; S.say(on ? 'Supply switched on.' : 'Supply switched off.'); S.render(); });
  }
  function setRheo(R) {
    if (busy()) return Promise.resolve();
    if (!(R >= 12 && R <= 60)) { S.say('The rheostat goes from 12 to 60 ohm.'); return Promise.resolve(); }
    var R0 = st.Rl, sl = rheo.userData.slider, at = wpt(sl, 0, 0.016, 0);
    return S.hand.pinchMove(at, function (k) { var f = (R0 + (R - R0) * k - 12) / 48; return new T.Vector3(-0.06 - 0.1 + 0.2 * f, 0.078, -0.26); },
      function (k) { st.Rl = R0 + (R - R0) * k; rheo.setFraction((st.Rl - 12) / 48); }, { mode: 'side', ms: 600 + 400 * Math.abs(R - R0) / 48, reachMs: 650 })
      .then(function () { st.Rl = Math.round(R * 2) / 2; rheo.setFraction((st.Rl - 12) / 48); S.render(); });
  }
  function setContact(l) {
    if (busy()) return Promise.resolve(false);
    if (!(l >= 0.5 && l <= 10)) { S.say('The shunt wire is 10 cm long: choose a length between 0.5 and 10 cm.'); return Promise.resolve(false); }
    var l0 = st.ls;
    return S.hand.pinchMove(shunt.head(l0), function (k) { return shunt.head(l0 + (l - l0) * k); },
      function (k) { st.ls = l0 + (l - l0) * k; shunt.place(st.ls); }, { mode: 'top', ms: 700, reachMs: 650 })
      .then(function () { st.ls = r1(l); shunt.place(st.ls); S.click(900, 0.02, 0.05);
        S.say('Shunt length set to ' + fnum(st.ls) + ' cm, that is ' + shuntOhm().toFixed(4) + ' ohm.'); S.render(); return true; });
  }

  // ---------------------------------------------------------------- readings
  function noteTh1() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('Insert the plug key K1 first.'); return false; }
    if (st.k2) { S.say('Take the plug out of K2 first: the first deflection is taken with the shunt out of the circuit.'); return false; }
    if (!(boxR() > 0)) { S.say('Set the resistance box first: with R = 0 the galvanometer would be destroyed.'); return false; }
    var d = defl();
    if (Math.abs(d) >= FS) { S.say('The deflection is off scale. Raise R.'); return false; }
    if (Math.abs(d) < 10) { S.say('Only ' + fnum(d) + ' division: lower R so the deflection is at least 10 divisions.'); return false; }
    st.th1 = d; S.say('First deflection with the shunt out: ' + fnum(d) + ' division.'); S.render(); return true;
  }
  function recordHalf() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!(st.th1 > 0)) { S.say('Note the first deflection with K2 open first.'); return false; }
    if (!st.k2) { S.say('Close key K2 so the shunt is in the circuit.'); return false; }
    var d = defl(), half = st.th1 / 2;
    if (Math.abs(d - half) > 0.25) { S.say('The deflection is ' + fnum(d) + ' division, not ' + fnum(half) + '. Change the shunt box S.'); return false; }
    var R = boxR(), Sv = shBox.value();
    if (!(Sv > 0 && Sv < R)) { S.say('The shunt must be smaller than R for this method.'); return false; }
    if (S.rows.some(function (r) { return r.R === R; })) { S.say('You already have a reading with R = ' + R + ' ohm. Change R.'); return false; }
    S.addRow({ R: R, th1: st.th1, S: Sv, th2: d });
    S.say('Written in your record book: R = ' + R + ' ohm, S = ' + Sv + ' ohm, so G = ' + (R * Sv / (R - Sv)).toFixed(1) + ' ohm.');
    return true;
  }
  function recordVerify() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return false; }
    if (!st.key) { S.say('Insert the plug key K1 first.'); return false; }
    if (MODE === 'volt' && !st.power) { S.say('Switch the supply on first.'); return false; }
    var d = defl(), v = stdRead();
    if (d < 4) { S.say('Only ' + fnum(d) + ' division: ' + (MODE === 'volt' ? 'raise the supply voltage.' : 'lower the rheostat.')); return false; }
    if (d > FS) { S.say('The galvanometer is off scale: ' + (MODE === 'volt' ? 'lower the supply voltage.' : 'raise the rheostat.')); return false; }
    if (S.rows.some(function (r) { return Math.abs(r.d - d) < 0.5; })) { S.say('You already have a reading at about ' + fnum(d) + ' division. Change the setting.'); return false; }
    S.addRow({ d: d, v: v });
    S.say('Written in your record book: ' + fnum(d) + ' division, standard meter ' + (MODE === 'volt' ? v.toFixed(2) + ' V' : v.toFixed(3) + ' A') + '.');
    return true;
  }
  // what a student does with a dial box: try a value, see whether the deflection is too much or too little, halve the gap
  function findHalf() {
    var lo = 1, hi = shBox.max(), target = st.th1 / 2;
    function probe(v) { return setS(v).then(function () { return defl(); }); }
    function step(n) {
      if (n > 12) return Promise.resolve();
      var mid = Math.round((lo + hi) / 2);
      return probe(mid).then(function (d) {
        if (Math.abs(d - target) <= 0.05) return;
        if (d > target) hi = mid; else lo = mid;
        if (hi - lo <= 1) { return probe(Math.abs(defl() - target) < 1e-9 ? mid : (Math.abs(d - target) <= 0.25 ? mid : hi)); }
        return step(n + 1);
      });
    }
    return step(0).then(function () {
      var best = shBox.value(), bd = Math.abs(defl() - target);
      return [best - 1, best + 1].reduce(function (pr, v) {
        return pr.then(function () { if (v < 1 || v > shBox.max()) return; return probe(v).then(function (d) {
          if (Math.abs(d - target) < bd - 1e-12) { bd = Math.abs(d - target); best = v; } }); });
      }, Promise.resolve()).then(function () { return setS(best); });
    });
  }

  // ---------------------------------------------------------------- the result
  function gValues(rows) { return rows.map(function (r) { return r.R * r.S / (r.R - r.S); }).filter(isFinite); }
  function result(rows) {
    if (MODE === 'half') {
      if (rows.length < 2) return null;
      var v = S.fit.mean(gValues(rows));
      return { label: 'G', value: v, unit: 'Ω', digits: 1, truth: p.Rg,
        note: 'Mean of G = RS/(R − S) over your readings. Figure of merit k = E/((R + G)θ₁) = ' + (FOM * 1e6).toFixed(2) + ' µA per division.' };
    }
    var pts = rows.map(function (r) { return [r.d, r.v]; }).filter(function (q) { return isFinite(q[0]) && isFinite(q[1]); });
    if (pts.length < 3) return null;
    var slope = S.fit.origin(pts);
    return { label: MODE === 'volt' ? 'Range of the converted voltmeter' : 'Range of the converted ammeter',
      value: slope * FS, unit: MODE === 'volt' ? 'V' : 'A', digits: MODE === 'volt' ? 2 : 3, truth: trueRange(),
      note: 'Slope of the standard meter\'s reading against the deflection, times ' + FS + ' divisions (full scale).' };
  }

  // ---------------------------------------------------------------- steps
  var stepsHalf = [
    { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
        u.h2('Set up the circuit');
        u.p('The galvanometer, the high resistance box R, key K₁ and the accumulator are in series. The shunt box S sits across the galvanometer behind key K₂.');
        u.task('1. Trace the circuit', st.traced, st.traced ? 'Series circuit traced; shunt across the galvanometer' : 'Follow the leads from the accumulator')
          .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
        var t2 = u.task('2. Set the resistance box R', boxR() > 0, boxR() > 0 ? 'R = ' + boxR() + ' Ω' : 'Every dial is at 0: R = 0 Ω');
        var row = document.createElement('div'); row.className = 'row';
        [4500, 5000, 6000, 8000].forEach(function (v) { row.appendChild(u.button(v + ' Ω', function () { setR(v); }, boxR() === v, S.hand.busy)); });
        t2.add(row);
        u.task('3. Keep K₂ open and insert K₁', st.key && !st.k2, st.key ? (st.k2 ? 'K₂ is still closed' : 'K₁ closed, K₂ open') : 'K₁ is open')
          .add(u.row(u.button(st.key ? 'K₁ is in' : 'Insert the plug in K₁', function () {
            if (!(boxR() > 0)) { S.say('Set the resistance box first: a galvanometer straight across a cell is destroyed.'); return; }
            setKey1(true); }, !st.key, st.key || S.hand.busy),
            u.button('Take K₂ out', function () { setKey2(false); }, false, !st.k2 || S.hand.busy)));
        u.note('Always set a few thousand ohms on R before closing K₁.');
        u.next('Next: take the readings', st.traced && boxR() > 0 && st.key && !st.k2);
      },
      ok: function () { return st.traced && boxR() > 0 && st.key && !st.k2; },
      auto: function () { trace(); return setR(5000).then(function () { return setKey1(true); }); } },
    { id: 'read', title: 'Half deflection', view: 'gal', render: function (u) {
        u.h2('Halve the deflection with the shunt');
        u.p('Note the deflection θ with K₂ open. Then close K₂ and change the shunt box S until the deflection is exactly θ/2. Then G = RS/(R − S).');
        u.task('1. Note θ with the shunt out', st.th1 > 0, st.th1 > 0 ? 'θ = ' + fnum(st.th1) + ' division at R = ' + boxR() + ' Ω' : 'K₂ open, K₁ closed')
          .add(u.button('Note the deflection', function () { noteTh1(); }, st.th1 === 0, S.hand.busy));
        u.task('2. Close K₂ and adjust S', st.k2, st.k2 ? 'S = ' + shBox.value() + ' Ω, deflection ' + fnum(defl()) + ' division' : 'K₂ is open')
          .add(u.row(u.button(st.k2 ? 'K₂ is in' : 'Insert the plug in K₂', function () { setKey2(true); }, !st.k2, st.k2 || S.hand.busy),
            u.button('Find the half deflection', function () {
              if (!(st.th1 > 0)) { S.say('Note the first deflection first.'); return; }
              if (!st.k2) { S.say('Close key K2 first.'); return; }
              findHalf(); }, false, S.hand.busy)));
        var set = { v: shBox.value() };
        u.slider('Shunt box S by hand', 1, 999, 1, function () { return set.v; }, function (v) { set.v = v; }, 'Ω', 0);
        u.row(u.button('Set the shunt box', function () { setS(set.v); }, false, S.hand.busy),
          u.button('Record this reading', function () { recordHalf(); }, true, S.hand.busy));
        u.live(function () { return 'Deflection ' + fnum(defl()) + ' division  ·  half of θ is ' + fnum(st.th1 / 2) + '  ·  R = ' + boxR() + ' Ω, S = ' + shBox.value() + ' Ω'; });
        u.h3('Change R and repeat');
        var row2 = u.row(); [4500, 5000, 6000, 8000].forEach(function (v) {
          row2.appendChild(u.button(v + ' Ω', function () { setKey2(false).then(function () { return setR(v); }).then(function () { st.th1 = 0; S.render(); }); }, boxR() === v, S.hand.busy)); });
        u.h3('Observation table'); u.table();
        if (S.rows.length < 3) u.p(S.rows.length + ' of at least 3 readings recorded.');
        u.next('Next: result', S.rows.length >= 3);
      },
      ok: function () { return S.rows.length >= 3; },
      auto: function () {
        function one(R) {
          return setKey2(false).then(function () { return setR(R); })
            .then(function () { st.th1 = 0; noteTh1(); return setKey2(true); })
            .then(findHalf).then(function () { recordHalf(); });
        }
        return [5000, 4500, 6000, 8000].reduce(function (pr, R) { return pr.then(function () { return one(R); }); }, Promise.resolve());
      } },
  ];

  var designRender = function (u) {
    u.h2(MODE === 'volt' ? 'Design the voltmeter' : 'Design the ammeter');
    u.p('The galvanometer needs ' + (IG * 1000).toFixed(2) + ' mA (k × 30 divisions) for full-scale deflection, and its own resistance is G = ' + fnum(p.Rg, 0) + ' Ω.');
    u.formula(MODE === 'volt' ? 'R = V / Iɢ − G' : 'S = G Iɢ / (I − Iɢ)',
      MODE === 'volt' ? 'for a range of ' + RANGE + ' V: R = ' + needR().toFixed(0) + ' Ω' : 'for a range of ' + RANGE + ' A: S = ' + needS().toFixed(4) + ' Ω = ' + needL().toFixed(1) + ' cm of the shunt wire');
    u.task('1. Trace the circuit', st.traced, st.traced ? 'Circuit traced' : 'Follow the leads from the supply')
      .add(u.button(st.traced ? 'Traced' : 'Trace the circuit', trace, !st.traced, st.traced));
    if (MODE === 'volt') {
      var ok1 = Math.abs(boxR() - needR()) < 1;
      u.task('2. Set R on the resistance box', ok1, ok1 ? 'R = ' + boxR() + ' Ω' : 'R is ' + boxR() + ' Ω, it should be ' + needR().toFixed(0) + ' Ω')
        .add(u.row(u.button('Set ' + needR().toFixed(0) + ' Ω', function () { setR(Math.round(needR())); }, !ok1, S.hand.busy),
          u.button('Set 0 Ω', function () { setR(0); }, false, S.hand.busy)));
      u.task('3. Insert K₁ and switch the supply on', st.key && st.power, st.key && st.power ? 'Ready' : 'K₁ ' + (st.key ? 'closed' : 'open'))
        .add(u.row(u.button(st.key ? 'K₁ is in' : 'Insert the plug in K₁', function () { setKey1(true); }, !st.key, st.key || S.hand.busy),
          u.button(st.power ? 'Supply is on' : 'Switch the supply on', function () { setPower(true); }, !st.power, st.power || S.hand.busy)));
      u.next('Next: verify the range', st.traced && ok1 && st.key && st.power);
    } else {
      var ok2 = Math.abs(st.ls - needL()) < 0.06;
      u.task('2. Set the shunt length', ok2, ok2 ? 'l = ' + fnum(st.ls) + ' cm = ' + shuntOhm().toFixed(4) + ' Ω' : 'l is ' + fnum(st.ls) + ' cm, it should be ' + needL().toFixed(1) + ' cm')
        .add(u.row(u.button('Slide the bridge to ' + needL().toFixed(1) + ' cm', function () { setContact(needL()); }, !ok2, S.hand.busy),
          u.button('Slide to 10 cm', function () { setContact(10); }, false, S.hand.busy)));
      u.task('3. Rheostat at its highest, then insert K₁', st.key, st.key ? 'K₁ closed, rheostat ' + fnum(st.Rl) + ' Ω' : 'K₁ is open')
        .add(u.row(u.button('Rheostat to 60 Ω', function () { setRheo(60); }, false, S.hand.busy),
          u.button(st.key ? 'K₁ is in' : 'Insert the plug in K₁', function () { setKey1(true); }, !st.key, st.key || S.hand.busy)));
      u.next('Next: verify the range', st.traced && ok2 && st.key);
    }
  };

  var verifyRender = function (u) {
    u.h2('Verify it against the standard meter');
    u.p(MODE === 'volt' ? 'Apply several voltages. Each time read the standard voltmeter and the deflection of the converted meter, and record both.'
      : 'Change the rheostat. Each time read the standard ammeter and the deflection of the converted meter, and record both.');
    if (MODE === 'volt') {
      var sv = { v: Math.min(3, Math.round((st.E + 0.5) * 20) / 20) };
      u.slider('Set the supply to', 0, 3, 0.05, function () { return sv.v; }, function (v) { sv.v = v; }, 'V', 2);
      u.row(u.button('Turn the supply knob', function () { setSupply(sv.v); }, true, S.hand.busy),
        u.button('Record this reading', function () { recordVerify(); }, false, S.hand.busy));
    } else {
      var sr = { v: Math.max(12, Math.round(st.Rl) - 4) };
      u.slider('Set the rheostat to', 12, 60, 0.5, function () { return sr.v; }, function (v) { sr.v = v; }, 'Ω', 1);
      u.row(u.button('Move the rheostat', function () { setRheo(sr.v); }, true, S.hand.busy),
        u.button('Record this reading', function () { recordVerify(); }, false, S.hand.busy));
    }
    u.live(function () { return 'Deflection ' + fnum(defl()) + ' division  ·  standard meter ' + (MODE === 'volt' ? stdRead().toFixed(2) + ' V' : stdRead().toFixed(3) + ' A'); });
    u.h3('Observation table'); u.table();
    if (S.rows.length < 5) u.p(S.rows.length + ' of at least 5 readings recorded.');
    u.next('Next: result', S.rows.length >= 5);
  };

  var stepsConvert = [
    { id: 'design', title: 'Design', view: 'bench', render: designRender,
      ok: function () { return MODE === 'volt' ? (st.traced && Math.abs(boxR() - needR()) < 1 && st.key && st.power)
        : (st.traced && Math.abs(st.ls - needL()) < 0.06 && st.key); },
      auto: function () {
        trace();
        if (MODE === 'volt') return setR(Math.round(needR())).then(function () { return setKey1(true); }).then(function () { return setPower(true); });
        return setContact(needL()).then(function () { return setRheo(60); }).then(function () { return setKey1(true); });
      } },
    { id: 'verify', title: 'Verify', view: 'std', render: verifyRender,
      ok: function () { return S.rows.length >= 5; },
      auto: function () {
        if (MODE === 'volt') {
          return [1.0, 1.5, 2.0, 2.5, 3.0].reduce(function (pr, E) {
            return pr.then(function () { return setSupply(E); }).then(function () { recordVerify(); }); }, Promise.resolve());
        }
        return [60, 40, 30, 22, 16, 13].reduce(function (pr, R) {
          return pr.then(function () { return setRheo(R); }).then(function () { recordVerify(); }); }, Promise.resolve());
      } },
  ];

  var bookHalf = { title: 'Expt. — Galvanometer by half deflection', at: [0.66, 0.12, -0.12],
    lines: ['Aim: to find the resistance G of a galvanometer', 'by the half-deflection method.',
      'E = ' + fnum(p.Eb, 1) + ' V,  galvanometer 30–0–30 div',
      'G = R S / (R − S)', 'k = E / ((R + G) θ) ampere per division',
      'Precautions: R large before K1 is closed;', 'K2 open while θ is noted.'],
    columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }, { label: 'R (Ω)', get: function (r) { return r.R; } },
      { label: 'θ (div)', get: function (r) { return fnum(r.th1); } }, { label: 'S (Ω)', get: function (r) { return r.S; } },
      { label: 'θ/2 (div)', get: function (r) { return fnum(r.th2); } },
      { label: 'G (Ω)', get: function (r) { return (r.R * r.S / (r.R - r.S)).toFixed(1); } }] };
  var bookConv = { title: MODE === 'volt' ? 'Expt. — Galvanometer into a voltmeter' : 'Expt. — Galvanometer into an ammeter', at: [0.66, 0.12, -0.12],
    lines: ['Aim: to convert a galvanometer into a', (MODE === 'volt' ? 'voltmeter of range ' + RANGE + ' V and verify it.' : 'ammeter of range ' + RANGE + ' A and verify it.'),
      'G = ' + fnum(p.Rg, 0) + ' Ω,  k = ' + (FOM * 1e6).toFixed(2) + ' µA/div',
      'Iɢ = k × 30 = ' + (IG * 1000).toFixed(2) + ' mA',
      MODE === 'volt' ? 'R = V/Iɢ − G = ' + needR().toFixed(0) + ' Ω' : 'S = G Iɢ/(I − Iɢ) = ' + needS().toFixed(4) + ' Ω',
      'Range = 30 × (slope of the graph)'],
    columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
      { label: 'Deflection (div)', get: function (r) { return fnum(r.d); } },
      { label: MODE === 'volt' ? 'Standard V (V)' : 'Standard I (A)', get: function (r) { return MODE === 'volt' ? r.v.toFixed(2) : r.v.toFixed(3); } },
      { label: MODE === 'volt' ? 'V per div' : 'A per div', get: function (r) { return r.d ? (r.v / r.d).toFixed(4) : '—'; } }] };

  return {
    camera: { pos: [-0.1, 1.2, 1.02], look: [-0.1, 0.02, -0.38] },
    views: { bench: [[-0.1, 1.14, 0.96], [-0.1, 0.02, -0.38]], gal: [[-0.02, 0.3, -0.34], [-0.02, 0.06, -0.68]],
      rb: [[-0.26, 0.28, -0.24], [-0.26, 0.03, -0.5]], key: [[-0.46, 0.24, 0.1], [-0.52, 0.02, -0.12]],
      src: [[-0.56, 0.3, -0.14], [-0.66, 0.06, -0.44]],
      sb: [[0.3, 0.28, -0.24], [0.3, 0.03, -0.5]], key2: [[0.4, 0.24, 0.08], [0.34, 0.02, -0.16]],
      std: [[0.34, 0.32, -0.3], [0.36, 0.06, -0.66]], rheo: [[-0.06, 0.26, -0.02], [-0.06, 0.04, -0.26]],
      shunt: [[0.2, 0.18, 0.1], [0.2, 0.02, -0.06]],
      book: [[0.66, 0.46, 0.44], [0.66, 0.0, -0.1] ] },
    theory: MODE === 'half' ? {
      principle: 'With key K₂ open the whole current from the cell passes through the galvanometer, so the deflection θ is proportional to E/(R + G). Closing K₂ puts the shunt S across the galvanometer, which then takes only a part of the current.',
      formula: 'G = R S / (R − S)',
      formulaNote: 'when the deflection has fallen to exactly half · k = E / ((R + G) θ) is the figure of merit',
      more: ['The deflection halves when the shunt carries half the current, that is when S equals the parallel combination of R and G. The formula assumes the current drawn from the cell hardly changes when the shunt is put in, which is why R must be a few thousand ohms while G is only tens of ohms.',
        'The figure of merit k is the current needed for one division of deflection; a galvanometer with a small k is a sensitive one.'],
      precautions: 'Set a few thousand ohms on R before closing K₁, keep K₂ open while the first deflection is noted, and take the plugs out between readings.' } : {
      principle: MODE === 'volt' ? 'A galvanometer is a voltmeter of a very small range: at full-scale deflection the voltage across it is only Iɢ G. A high resistance R in series means the same full-scale current flows at a much larger applied voltage.'
        : 'A galvanometer can take only its small full-scale current Iɢ. A low resistance S in parallel (a shunt) carries the rest of the line current, so a much larger current gives full-scale deflection.',
      formula: MODE === 'volt' ? 'R = V / Iɢ − G' : 'S = G Iɢ / (I − Iɢ)',
      formulaNote: 'Iɢ = k × 30 divisions = ' + (IG * 1000).toFixed(2) + ' mA, G = ' + fnum(p.Rg, 0) + ' Ω',
      more: [MODE === 'volt' ? 'The converted meter is verified against a standard voltmeter joined across the same two points: the graph of the standard reading against the deflection is a straight line through the origin, and its slope times 30 divisions is the real range.'
        : 'Shunting also lowers the meter\'s own resistance to GS/(G + S), which is exactly what an ammeter needs: it must not disturb the current it measures. The converted meter is verified against a standard ammeter in series with it.',
        'A converted meter is only as good as the resistance you add: a 1 % error in R or S is a 1 % error in every reading.'],
      precautions: MODE === 'volt' ? 'Set the series resistance before switching the supply on, and never apply more than the designed range.'
        : 'Keep the rheostat at its highest resistance when the key is closed, and open the key between readings.' },
    book: MODE === 'half' ? bookHalf : bookConv,
    graph: MODE === 'half' ? { x: function (r) { return 1000 / r.R; }, y: function (r) { return r.th1; },
      xlabel: '1000 / R  (1/Ω)', ylabel: 'θ (div)', x0: 0, y0: 0,
      line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } }
      : { x: function (r) { return r.d; }, y: function (r) { return r.v; }, xlabel: 'Deflection (div)',
        ylabel: MODE === 'volt' ? 'Standard voltmeter (V)' : 'Standard ammeter (A)', x0: 0, y0: 0,
        line: function (pts) { var k = S.fit.origin(pts); return function (x) { return k * x; }; } },
    result: result,
    tol: 0.02,
    resultNote: MODE === 'half' ? 'The same G should come out of every row; if one row is far off, its shunt was not exactly at the half deflection.'
      : 'A straight line through the origin means the converted meter is linear, and its slope fixes what one division is worth.',
    chips: MODE === 'half' ? ['Why must R be large?', 'What is the figure of merit?', 'Check my readings', 'Why is the deflection halved?']
      : ['Why this value of ' + (MODE === 'volt' ? 'R' : 'the shunt') + '?', 'Check my readings', 'Why verify against a standard meter?', 'What if the resistance is 10 % wrong?'],
    viva: MODE === 'half' ? [
      ['Why is a high resistance box used and not a low one?', ['So the current stays small and G = RS/(R − S) holds', 'To make the deflection larger', 'To protect the shunt'], 0,
        'The formula assumes the cell\'s current is unchanged when the shunt is inserted, which needs R ≫ G.'],
      ['The figure of merit of a galvanometer is', ['The current for one division of deflection', 'Its resistance', 'Its full-scale deflection'], 0, 'k = I/θ, in ampere per division.']]
      : MODE === 'volt' ? [
        ['Why is the resistance added in series and not in parallel?', ['A voltmeter must take almost no current', 'To make the meter more sensitive', 'To lower its resistance'], 0,
          'In series it raises the meter\'s resistance, so it hardly loads the circuit.'],
        ['If R is made twice as large, the range becomes', ['Nearly twice as large', 'Half', 'Unchanged'], 0, 'V = Iɢ(G + R), and R is much larger than G.']]
        : [['Why is the shunt resistance so small?', ['It must carry almost all the current', 'To heat up less', 'To raise the meter\'s resistance'], 0,
          'S = G Iɢ/(I − Iɢ), and Iɢ is only a fraction of a milliampere.'],
          ['An ammeter must have', ['A very low resistance', 'A very high resistance', 'No resistance at all'], 0, 'Otherwise it changes the current it is measuring.']],
    askState: function () {
      var o = { experiment: MODE === 'half' ? 'resistance of a galvanometer by half deflection'
        : MODE === 'volt' ? 'galvanometer converted into a voltmeter of range ' + RANGE + ' V'
          : 'galvanometer converted into an ammeter of range ' + RANGE + ' A',
      key_K1_closed: st.key, resistance_box_R_ohm: boxR(), deflection_div: defl(),
      galvanometer_figure_of_merit_uA_per_div: +(FOM * 1e6).toFixed(2), readings_taken: S.rows.length };
      if (MODE === 'half') { o.key_K2_closed = st.k2; o.shunt_box_S_ohm = shBox.value(); o.first_deflection_div = st.th1; }
      else if (MODE === 'volt') { o.supply_on = st.power; o.supply_setting_V = +st.E.toFixed(2); o.standard_voltmeter_V = stdRead(); o.series_resistance_needed_ohm = +needR().toFixed(0); }
      else { o.rheostat_ohm = st.Rl; o.shunt_length_cm = st.ls; o.shunt_ohm = +shuntOhm().toFixed(4); o.standard_ammeter_A = stdRead(); o.shunt_needed_ohm = +needS().toFixed(4); }
      return o;
    },
    steps: MODE === 'half' ? stepsHalf : stepsConvert,
    tick: function () {
      var d = defl();
      gal.set(Math.max(-FS - 1, Math.min(FS + 1, d)));
      if (stdMeter) stdMeter.set(st.key ? (MODE === 'volt' ? solve().V_VM : solve().I_AM) : 0);
      hudA.set(MODE === 'half' ? boxR() + ' Ω' : MODE === 'volt' ? boxR() + ' Ω' : fnum(st.ls) + ' cm');
      hudB.set(st.key ? fnum(d) + ' div' : '—');
      hudC.set(MODE === 'half' ? shBox.value() + ' Ω' : st.key ? (MODE === 'volt' ? stdRead().toFixed(2) + ' V' : stdRead().toFixed(3) + ' A') : '—');
    },
  };
});
