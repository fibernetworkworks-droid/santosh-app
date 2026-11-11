/* Prayogshala studio rig `em-ug-instruments`: THE B.Sc. ELECTRICITY AND MAGNETISM INSTRUMENT BENCH.
   One bench, one procedure (connect, switch on, set, read, record), and the apparatus of whichever set-up of
   app/prayog/labs/ug_em_w7.py is open. The lab's kernel picks the apparatus:
     w7_carey      Carey Foster's bridge             w7_potlow    low resistance on a ten-wire potentiometer
     w7_anderson   Anderson's bridge                 w7_unibridge universal R / L / C bridge
     w7_qmeter     Q-meter                           w7_tau       RC / RL time constant on an oscilloscope
     w7_xfmr       transformer under load            w7_motor     DC motor and tachometer
     w7_gen        AC / DC generator                 w7_fallmag   magnet falling through a coil (Arduino)
     w7_gconv      galvanometer into a meter         w7_srcreg    constant-voltage / constant-current source
     w7_magneto    deflection and vibration magnetometers         msc_loop   B-H loop of a ring specimen
   Every reading comes from that kernel (packs/ug_em_w7.js, or packs/msc_solid.js for the loop) on the lab's own
   params: the same code the server checks against the textbook formula. Readings are rounded to the least count
   of the instrument that shows them, and nothing else is done to them. Low-voltage supplies only. */
HoolaStudio.define('em-ug-instruments', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KNAME = S.lab.kernel, KN = HK.K[KNAME], p = HK.paramsFor(KNAME, S.lab.params);
  var V_ = S.lab.variant || {}, SAMPLE = V_.sample || '';
  var st = { wired: false, on: false, vals: {}, part: 0, busyRead: false };
  var PI = Math.PI;

  /* ---------------------------------------------------------------- small helpers */
  function rnd(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function sig(v, n) { if (!v) return 0; var k = Math.pow(10, n - 1 - Math.floor(Math.log(Math.abs(v)) / Math.LN10)); return Math.round(v * k) / k; }
  function mean(a) { var s = 0, i; for (i = 0; i < a.length; i++) s += a[i]; return a.length ? s / a.length : 0; }
  function slope(pts) { var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, den; if (n < 2) return 0;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    den = n * sxx - sx * sx; return den === 0 ? 0 : (n * sxy - sx * sy) / den; }
  function busy() { if (S.hand.busy || st.busyRead) { S.say('Wait for the hand to finish.'); return true; } return false; }
  function mk(g, geo, mat, x, y, z) { var m = S.mesh(geo, mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m; }
  function cyl(r1, r2, h, seg) { return new T.CylinderGeometry(r1, r2, h, seg || 28); }
  function box(w, h, d) { return new T.BoxGeometry(w, h, d); }
  function col(hex, rough, metal) { return new T.MeshStandardMaterial({ color: hex, roughness: rough === undefined ? 0.5 : rough, metalness: metal || 0 }); }
  function grp(x, z, ry) { var g = new T.Group(); g.position.set(x, 0, z); if (ry) g.rotation.y = ry; S.scene.add(g); return g; }
  // printed text that always fits its plate (long names are condensed, never cut off)
  function tag(text, w, ratio, fg, bg) { var hh = Math.round(512 * ratio);
    var tex = S.canvasTex(512, hh, function (c) { if (bg) { c.fillStyle = bg; c.fillRect(0, 0, 512, hh); } c.fillStyle = fg; c.font = '600 ' + Math.round(hh * 0.56) + 'px "Public Sans", sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(text, 256, hh / 2, 488); });
    return new T.Mesh(new T.PlaneGeometry(w, w * ratio), new T.MeshStandardMaterial({ map: tex, transparent: !bg, roughness: 0.6 })); }
  function plate(g, text, w, x, y, z, bg, fg, ratio) { var l = tag(text, w, ratio || 0.2, fg || '#f1efe8', bg); l.position.set(x, y, z); g.add(l); return l; }
  function flat(g, text, w, x, y, z, fg) { var l = tag(text, w, 0.2, fg || '#f0e6c8'); l.rotation.x = -PI / 2; l.position.set(x, y, z); g.add(l); return l; }
  var COPPER = new T.MeshStandardMaterial({ color: 0xb5622f, roughness: 0.35, metalness: 0.6 });
  var GREENW = col(0x1f6b4a, 0.4, 0.3), CASE = col(0xd7d3c9, 0.5), DARK = col(0x2b323d, 0.5);

  // an instrument case: w wide, h high, d deep, standing on the bench with its front panel towards the student
  function caseBox(x, z, w, h, d, mat, title, ry) { var g = grp(x, z, ry);
    var b = S.rounded(w, d, h, 0.008, mat || CASE); b.rotation.x = -PI / 2; b.position.y = h / 2; g.add(b);
    g.userData.front = d / 2 + 0.0032;
    if (title) plate(g, title, Math.min(w * 0.86, 0.2), 0, 0.018, g.userData.front, '#2b323d'); g.userData.h = h; S.contact(w + 0.06, d + 0.06, x, z, 0.5); return g; }
  // a liquid-crystal display on the front of a case
  function lcd(g, x, y, w, hgt) { var tex = S.liveTex(512, 160), last = null;
    mk(g, box(w + 0.008, (hgt || w * 0.32) + 0.008, 0.002), M.grey, x, y, g.userData.front);
    var m = new T.Mesh(new T.PlaneGeometry(w, hgt || w * 0.32), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); m.position.set(x, y, g.userData.front + 0.0014); g.add(m);
    function set(txt, unit) { var key = txt + '|' + unit; if (key === last) return; last = key;
      tex.draw(function (c) { var gr = c.createLinearGradient(0, 0, 0, 160); gr.addColorStop(0, '#b9c4a7'); gr.addColorStop(1, '#9eab8b'); c.fillStyle = gr; c.fillRect(0, 0, 512, 160);
        c.fillStyle = '#1b2116'; c.textAlign = 'right'; c.font = '700 84px "JetBrains Mono", monospace'; c.fillText(txt, 392, 108); c.font = '600 34px "Public Sans", sans-serif'; c.fillText(unit || '', 500, 138); }); }
    set('----', ''); return { set: set }; }
  function knob(g, x, y, r) { var k = new T.Group(); k.position.set(x, y, g.userData.front + 0.006); g.add(k);
    var c = mk(k, cyl(r || 0.012, (r || 0.012) * 1.08, 0.012, 28), M.bakelite); c.rotation.x = PI / 2; mk(k, box(0.002, (r || 0.012) * 0.9, 0.001), M.white, 0, (r || 0.012) * 0.5, 0.0066); return k; }
  function toggle(g, x, y) { var k = mk(g, cyl(0.004, 0.004, 0.014, 12), M.chrome, x, y, g.userData.front + 0.006); k.rotation.x = PI / 2 - 0.5; return k; }
  // a digital meter: a small case with one display
  function dmm(x, z, title, ry) { var g = caseBox(x, z, 0.15, 0.08, 0.09, col(0xe0a93c, 0.55), title, ry); var d = lcd(g, 0, 0.05, 0.115, 0.036); d.g = g; return d; }
  // an oscilloscope with a live screen
  function scope(x, z, title, ry) { var g = caseBox(x, z, 0.28, 0.2, 0.2, CASE, title || 'OSCILLOSCOPE', ry);
    var tex = S.liveTex(640, 480); mk(g, box(0.2, 0.15, 0.003), M.grey, -0.03, 0.115, g.userData.front);
    var m = new T.Mesh(new T.PlaneGeometry(0.19, 0.14), new T.MeshBasicMaterial({ map: tex, toneMapped: false })); m.position.set(-0.03, 0.115, g.userData.front + 0.002); g.add(m);
    var ks = [0.17, 0.13, 0.09].map(function (y) { return knob(g, 0.105, y, 0.009); });
    function grid(c, w, h, text) { c.fillStyle = '#06130a'; c.fillRect(0, 0, w, h); c.strokeStyle = 'rgba(80,220,120,.22)'; c.lineWidth = 1; var i;
      for (i = 1; i < 10; i++) { c.beginPath(); c.moveTo(i * w / 10, 0); c.lineTo(i * w / 10, h); c.stroke(); }
      for (i = 1; i < 8; i++) { c.beginPath(); c.moveTo(0, i * h / 8); c.lineTo(w, i * h / 8); c.stroke(); }
      if (text) { c.fillStyle = 'rgba(160,255,190,.85)'; c.font = '600 22px "JetBrains Mono", monospace'; c.textAlign = 'left'; c.fillText(text, 16, 30); } }
    return { g: g, knob: ks[0], draw: function (fn) { tex.draw(function (c, w, h) { fn(c, w, h, grid); }); } }; }
  function trace(c, pts, colr) { c.strokeStyle = colr || '#6dff9a'; c.lineWidth = 3; c.shadowColor = colr || '#6dff9a'; c.shadowBlur = 8; c.beginPath();
    pts.forEach(function (q, i) { if (i) c.lineTo(q[0], q[1]); else c.moveTo(q[0], q[1]); }); c.stroke(); c.shadowBlur = 0; }
  function coilOn(g, r, len, x, y, z, mat, axis) { var c = mk(g, cyl(r, r, len, 32), mat || COPPER, x, y, z); if (axis === 'x') c.rotation.z = PI / 2; else if (axis === 'z') c.rotation.x = PI / 2; return c; }
  function post(g, x, y, z, red) { mk(g, cyl(0.005, 0.006, 0.012, 12), M.brass, x, y + 0.006, z); mk(g, cyl(0.0055, 0.0055, 0.006, 16), red ? M.red : M.blackPlastic, x, y + 0.015, z); }
  var wires = [];
  function lead(pts, colr) { var w = S.wire(pts, colr); w.visible = false; wires.push(w); return w; }

  var MX = 0.02, MZ = -0.46;                               // where the main apparatus stands
  var A = { knob: null, key: null, sw: null, name: 'Apparatus', info: '', view: [[MX, 0.55, 0.45], [MX, 0.06, MZ]], tick: null };
  var PLAN = null;

  /* ================================================================ wire boards: Carey Foster and the potentiometer */
  function wireBoard(nw, title) {
    var g = grp(MX, MZ), L = 1.0, D = nw > 1 ? 0.24 : 0.16;
    mk(g, box(L + 0.1, 0.02, D), M.darkWood, 0, 0.01, 0);
    var sc = S.ruler(L, { width: 0.022 }); sc.rotation.set(-PI / 2, 0, -PI / 2); sc.position.set(MX - L / 2, 0.0215, MZ + D / 2 - 0.02);
    var i, zs = [];
    for (i = 0; i < nw; i++) { var z = nw > 1 ? -D / 2 + 0.03 + i * (D - 0.085) / (nw - 1) : 0.01; zs.push(z);
      var w = mk(g, cyl(0.0007, 0.0007, L, 8), col(0xc9b48a, 0.25, 0.9), 0, 0.0225, z); w.rotation.z = PI / 2; }
    [-L / 2 - 0.02, L / 2 + 0.02].forEach(function (x) { mk(g, box(0.03, 0.006, D - 0.03), M.copper, x, 0.023, 0); });
    flat(g, title, 0.12, 0, 0.0205, nw > 1 ? -D / 2 + 0.014 : 0.034);
    var jock = new T.Group(); g.add(jock);
    mk(jock, cyl(0.004, 0.004, 0.07, 14), M.blackPlastic, 0, 0.065, 0); mk(jock, cyl(0.0012, 0.004, 0.03, 12), M.brass, 0, 0.037, 0); mk(jock, cyl(0.007, 0.007, 0.01, 16), M.red, 0, 0.1, 0);
    S.contact(L + 0.16, D + 0.06, MX, MZ, 0.5);
    return { g: g, L: L, D: D, zs: zs, jock: jock, place: function (f, wi) { jock.position.set(-L / 2 + f * L, 0, zs[wi || 0]); } };
  }
  function galvo(x, z, cap) { return S.meter({ pos: [x, 0, z], min: -30, max: 30, zeroCentre: true, unit: 'G', symbol: 'G', caption: cap || 'galvanometer', ticks: 6 }); }

  if (KNAME === 'w7_carey') (function () {
    var B = wireBoard(1, 'CAREY FOSTER BRIDGE'), g = B.g, zb = -0.055, s = { l: 0.5, swap: false };
    // the four gaps along the far edge: outer-left, P, Q, outer-right
    var gx = [-0.36, -0.12, 0.12, 0.36];
    mk(g, box(1.06, 0.006, 0.014), M.copper, 0, 0.023, zb - 0.02).visible = false;
    [-0.5, -0.24, 0, 0.24, 0.5].forEach(function (x, i) { var wdt = (i === 0 || i === 4) ? 0.1 : 0.1; mk(g, box(wdt, 0.005, 0.016), M.copper, i === 0 ? -0.47 : i === 4 ? 0.47 : x, 0.0225, zb); });
    function gapItem(kind) { var q = new T.Group(); g.add(q);
      if (kind === 'coil') { coilOn(q, 0.012, 0.03, 0, 0.045, 0, GREENW, 'y'); mk(q, cyl(0.014, 0.014, 0.004, 20), M.bakelite, 0, 0.062, 0); mk(q, box(0.1, 0.004, 0.006), M.copper, 0, 0.027, 0); }
      else if (kind === 'strip') { mk(q, box(0.13, 0.005, 0.02), M.copper, 0, 0.028, 0); }
      else { var b = S.rounded(0.1, 0.05, 0.03, 0.004, M.darkWood); b.rotation.x = -PI / 2; b.position.y = 0.043; q.add(b); mk(q, box(0.09, 0.003, 0.04), M.bakelite, 0, 0.0595, 0);
        [-0.03, -0.01, 0.01, 0.03].forEach(function (x) { mk(q, cyl(0.004, 0.004, 0.01, 12), M.brass, x, 0.065, 0); }); flat(q, kind, 0.08, 0, 0.0615, 0.014); }
      return q; }
    var P = gapItem('coil'), Q = gapItem('coil'), boxR = gapItem('FRACTIONAL BOX'), strip = gapItem('strip'), unk = gapItem('UNKNOWN X');
    P.position.set(gx[1], 0, zb); Q.position.set(gx[2], 0, zb);
    function seat() { var left = st.part ? unk : boxR, other = st.part ? boxR : unk; other.visible = false; left.visible = true;
      left.position.set(gx[s.swap ? 3 : 0], 0, zb); strip.position.set(gx[s.swap ? 0 : 3], 0, zb); }
    seat(); B.place(0.5);
    var gm = galvo(MX + 0.2, MZ + 0.27), cell = S.cell([MX - 0.62, 0, MZ - 0.16], { text: '2 V' }), key = S.plugKey([MX - 0.4, 0, MZ - 0.17]);
    lead([[MX, 0.05, MZ + zb], [MX + 0.1, 0.02, MZ + 0.1], [MX + 0.165, 0.07, MZ + 0.24]], 'black');
    lead([[MX + 0.235, 0.07, MZ + 0.24], [MX + 0.3, 0.02, MZ + 0.14], [MX + 0.34, 0.024, MZ + 0.075]], 'red');
    lead([[MX - 0.6, 0.03, MZ - 0.16], [MX - 0.3, 0.03, MZ - 0.1], [MX - 0.24, 0.03, MZ + zb]], 'red');
    lead([[MX - 0.37, 0.025, MZ - 0.17], [MX, 0.03, MZ - 0.12], [MX + 0.24, 0.03, MZ + zb]], 'black');
    A.name = 'Carey Foster bridge'; A.info = 'A metre of uniform wire with four gaps: equal coils P and Q in the inner two, the resistances being compared in the outer two.';
    A.knob = boxR; A.key = key.userData.plug; A.sw = key.userData.plug; A.onSwitch = function () { key.set(true); };
    function xl() { return st.part ? p.Xu : st.vals.std; }
    function slideTo(l) { var a = s.l, b = l, y = 0.11; if (S.fast) { s.l = b; B.place(b); return Promise.resolve(); }
      return S.hand.pinchMove(new T.Vector3(MX - 0.5 + a, y, MZ + 0.01), function (k) { return new T.Vector3(MX - 0.5 + a + (b - a) * k, y, MZ + 0.01); }, function (k) { s.l = a + (b - a) * k; B.place(s.l); }, { mode: 'top', ms: 1200 }); }
    function swap() { s.swap = !s.swap; if (S.fast) { seat(); return Promise.resolve(); } return S.tween(500, function (k) { if (k > 0.5) seat(); }); }
    A.tick = function () { var x = xl(), i = st.on ? KN.ig(p, s.l, s.swap ? 0 : x, s.swap ? x : 0) * 1e6 : 0; gm.set(Math.max(-30, Math.min(30, i * 0.6))); seat(); };
    PLAN = {
      parts: ['Known resistance (find ρ)', 'Unknown resistance X'],
      controls: [[{ key: 'std', label: 'Fractional resistance box', min: 0.2, max: 1.0, step: 0.1, unit: 'Ω', digits: 1, def: 0.5 }], []],
      act: ['Find both null points', 'Find both null points'],
      take: function (part, v) { var x = part ? p.Xu : v.std, m = KN.measure(assign(p, { XL: x, YR: 0 }));
        if (m.l1 < 0 || m.l2 < 0) return { err: 'No null point on the wire: the difference between the two gaps is more than the whole wire. Use a smaller resistance.' };
        var row = { part: part, r: part ? null : v.std, l1: rnd(m.l1 * 100, 1), l2: rnd(m.l2 * 100, 1) };
        return { row: row, say: 'Null points at ' + row.l1.toFixed(1) + ' cm and, with the gaps interchanged, ' + row.l2.toFixed(1) + ' cm.',
          anim: function () { s.swap = false; seat(); return slideTo(m.l1).then(swap).then(function () { return slideTo(m.l2); }).then(function () { s.swap = false; seat(); }); } }; },
      cols: [{ label: 'left gap', get: function (r) { return r.part ? 'X' : r.r.toFixed(1) + ' Ω'; } }, { label: 'l₁ (cm)', get: function (r) { return r.l1.toFixed(1); } },
        { label: 'l₂ (cm)', get: function (r) { return r.l2.toFixed(1); } }, { label: 'l₂ − l₁ (cm)', get: function (r) { return (r.l2 - r.l1).toFixed(1); } }],
      ok: function (rows) { var a = rows.filter(function (r) { return r.part === 0; }); return a.length >= 2 && rows.some(function (r) { return r.part === 1; }); },
      needText: 'Find ρ with two known resistances, then take the unknown.',
      auto: [[0, { std: 0.5 }], [0, { std: 0.8 }], [1, {}]],
      result: function (rows) { if (!this.ok(rows)) return null;
        var rho = mean(rows.filter(function (r) { return r.part === 0; }).map(function (r) { return r.r / ((r.l2 - r.l1) / 100); }));
        return { label: 'Unknown low resistance X', value: mean(rows.filter(function (r) { return r.part === 1; }).map(function (r) { return rho * (r.l2 - r.l1) / 100; })), unit: 'Ω', digits: 3, truth: p.Xu,
          note: 'The known resistances give ρ = ' + rnd(rho, 3) + ' Ω per metre of the bridge wire, and X = ρ (l₂ − l₁).' }; },
      tol: 0.02, formula: 'X − Y = ρ (l₂ − l₁)', formulaNote: 'Y is the thick copper strip (zero); ρ is the resistance of one metre of the wire',
      live: function () { return 'Jockey at ' + (s.l * 100).toFixed(1) + ' cm'; }
    };
  })();

  if (KNAME === 'w7_potlow') (function () {
    var B = wireBoard(10, 'TEN-WIRE POTENTIOMETER'), s = { l: 5.0 };
    function place(l) { var wi = Math.min(9, Math.floor(l)), f = l - wi; B.place(wi % 2 ? 1 - f : f, wi); }
    place(s.l);
    var gm = galvo(MX + 0.3, MZ + 0.29), rh = S.rheostat([MX - 0.2, 0, MZ + 0.27], 0.22);
    var lr = grp(MX - 0.55, MZ + 0.27); mk(lr, box(0.2, 0.012, 0.08), M.bakelite, 0, 0.006, 0);
    mk(lr, box(0.07, 0.008, 0.02), col(0xb9a06a, 0.3, 0.8), -0.05, 0.02, 0); mk(lr, box(0.07, 0.012, 0.03), M.copper, 0.05, 0.022, 0);
    [-0.08, -0.02, 0.02, 0.08].forEach(function (x) { post(lr, x, 0.012, 0.025, x < 0); });
    flat(lr, 'UNKNOWN R      STD S 0.1 Ω', 0.18, 0, 0.0125, -0.028); S.contact(0.26, 0.14, MX - 0.55, MZ + 0.27, 0.45);
    var am = dmm(0.7, MZ + 0.3, 'TEST CURRENT', -0.3);
    var cell = S.cell([MX - 0.6, 0, MZ - 0.2], { text: '2 V' }), key = S.plugKey([MX - 0.42, 0, MZ - 0.2]);
    lead([[MX - 0.5, 0.03, MZ], [MX - 0.56, 0.03, MZ - 0.14], [MX - 0.6, 0.03, MZ - 0.2]], 'red');
    lead([[MX - 0.5, 0.03, MZ + 0.05], [MX - 0.6, 0.02, MZ + 0.2], [MX - 0.63, 0.03, MZ + 0.295]], 'red');
    lead([[MX - 0.53, 0.03, MZ + 0.295], [MX + 0.1, 0.02, MZ + 0.2], [MX + 0.265, 0.07, MZ + 0.26]], 'black');
    lead([[MX + 0.335, 0.07, MZ + 0.26], [MX + 0.38, 0.02, MZ + 0.2], [MX + 0.42, 0.024, MZ + 0.125]], 'black');
    A.name = 'Ten-wire potentiometer'; A.info = 'Ten metres of uniform wire in ten one-metre lengths. The unknown and the 0.1 Ω standard carry the same current from the second cell.';
    A.knob = rh.userData.slider; A.key = key.userData.plug; A.sw = key.userData.plug; A.onSwitch = function () { key.set(true); };
    function slideTo(l) { var a = s.l; if (S.fast) { s.l = l; place(l); return Promise.resolve(); }
      return S.hand.pinchMove(new T.Vector3(MX, 0.11, MZ), function (k) { var q = a + (l - a) * k, wi = Math.min(9, Math.floor(q)), f = q - wi; return new T.Vector3(MX - 0.5 + (wi % 2 ? 1 - f : f), 0.11, MZ + B.zs[wi]); },
        function (k) { s.l = a + (l - a) * k; place(s.l); }, { mode: 'top', ms: 1400 }); }
    A.tick = function () { rh.setFraction((st.vals.R2 - 4) / 8); am.set(st.on ? (p.E2 / (st.vals.R2 + p.Rx + p.Sd)).toFixed(3) : '----', 'A');
      gm.set(st.on ? Math.max(-30, Math.min(30, KN.ig(assign(p, { R2: st.vals.R2 }), s.l, 0) * 1e6 * 0.4)) : 0); };
    PLAN = {
      parts: null, controls: [[{ key: 'R2', label: 'Rheostat in the test circuit', min: 4, max: 12, step: 0.5, unit: 'Ω', digits: 1, def: 6 }]],
      act: ['Balance across R, then across S'],
      take: function (part, v) { var m = KN.measure(assign(p, { R2: v.R2 }));
        if (m.l1 <= 0 || m.l2 <= 0) return { err: 'No balance on the wire: the potential difference is more than the whole wire carries. Put more rheostat in the test circuit.' };
        var row = { I: rnd(p.E2 / (v.R2 + p.Rx + p.Sd), 3), l1: rnd(m.l1 * 100, 1), l2: rnd(m.l2 * 100, 1) };
        return { row: row, say: 'Balance at ' + row.l1.toFixed(1) + ' cm across R and ' + row.l2.toFixed(1) + ' cm across the standard.', anim: function () { return slideTo(m.l1).then(function () { return slideTo(m.l2); }); } }; },
      cols: [{ label: 'I (A)', get: function (r) { return r.I.toFixed(3); } }, { label: 'l₁ for R (cm)', get: function (r) { return r.l1.toFixed(1); } },
        { label: 'l₂ for S (cm)', get: function (r) { return r.l2.toFixed(1); } }, { label: 'R = S l₁/l₂ (Ω)', get: function (r) { return (p.Sd * r.l1 / r.l2).toFixed(4); } }],
      ok: function (rows) { return rows.length >= 3; }, needText: 'Take at least three currents.',
      auto: [[0, { R2: 5 }], [0, { R2: 7 }], [0, { R2: 9 }]],
      result: function (rows) { if (rows.length < 3) return null;
        return { label: 'Unknown low resistance R', value: mean(rows.map(function (r) { return p.Sd * r.l1 / r.l2; })), unit: 'Ω', digits: 4, truth: p.Rx,
          note: 'The mean of ' + rows.length + ' currents. The ratio l₁ / l₂ stays the same when the current changes, which shows the potential leads carry no current at balance.' }; },
      tol: 0.02, formula: 'R / S = l₁ / l₂', formulaNote: 'S = ' + p.Sd + ' Ω is the standard low resistance; both carry the same current',
      live: function () { return 'Jockey at ' + (s.l * 100).toFixed(1) + ' cm'; }
    };
  })();

  /* ================================================================ bridges and the Q-meter: panel instruments */
  function panelBoard(title, draw) { var g = grp(MX - 0.08, MZ + 0.02);
    var b = S.rounded(0.5, 0.34, 0.05, 0.008, M.darkWood); b.rotation.x = -PI / 2; b.position.y = 0.025; g.add(b);
    var tex = S.canvasTex(1500, 1020, function (c, w, h) { c.fillStyle = '#17181b'; c.fillRect(0, 0, w, h); c.strokeStyle = '#e8e0c4'; c.fillStyle = '#e8e0c4'; c.lineWidth = 7; c.lineCap = 'round';
      c.font = '700 46px "Public Sans", sans-serif'; c.textAlign = 'center'; draw(c, w, h); c.font = '600 40px "Public Sans", sans-serif'; c.fillText(title, w / 2, h - 34); });
    var top = S.mesh(box(0.49, 0.003, 0.33), [M.bakelite, M.bakelite, new T.MeshStandardMaterial({ map: tex, roughness: 0.5 }), M.bakelite, M.bakelite, M.bakelite]); top.position.y = 0.052; g.add(top);
    S.contact(0.58, 0.42, MX - 0.08, MZ + 0.02, 0.5);
    g.dial = function (u, v, text) { var k = new T.Group(); k.position.set(u, 0.054, v); g.add(k); mk(k, cyl(0.016, 0.018, 0.014, 28), M.bakelite, 0, 0.007, 0); mk(k, box(0.002, 0.002, 0.014), M.white, 0, 0.0145, -0.006); if (text) flat(g, text, 0.07, u, 0.0545, v + 0.032); return k; };
    return g; }

  if (KNAME === 'w7_anderson') (function () {
    var g = panelBoard('ANDERSON BRIDGE', function (c) {
      function seg(a, b) { c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.stroke(); }
      var a = [300, 480], b = [750, 180], cc = [1200, 480], d = [750, 780], e = [750, 560];
      seg(a, b); seg(b, cc); seg(a, d); seg(d, cc); seg(d, e); seg(e, [980, 520]); seg(b, e);
      [a, b, cc, d, e].forEach(function (q) { c.beginPath(); c.arc(q[0], q[1], 13, 0, 7); c.fill(); });
      c.fillText('L, r₁', 470, 290); c.fillText('R₃', 1020, 290); c.fillText('R₂', 470, 690); c.fillText('R₄', 1020, 690); c.fillText('r', 700, 680); c.fillText('C', 900, 590); c.fillText('D', 790, 380); });
    var k1 = g.dial(-0.17, -0.1, 'r₁'), k2 = g.dial(-0.17, 0.08, 'r');
    var coil = grp(MX - 0.46, MZ - 0.08); mk(coil, cyl(0.05, 0.05, 0.006, 32), M.bakelite, 0, 0.003, 0); coilOn(coil, 0.04, 0.06, 0, 0.036, 0, COPPER, 'y'); mk(coil, cyl(0.05, 0.05, 0.006, 32), M.bakelite, 0, 0.069, 0);
    flat(coil, SAMPLE ? 'COIL' : 'COIL L', 0.06, 0, 0.0725, 0); S.contact(0.14, 0.14, MX - 0.46, MZ - 0.08, 0.5);
    var d1 = dmm(0.5, MZ - 0.12, 'DIAL r₁ (Ω)'), d2 = dmm(0.5, MZ + 0.02, 'DIAL r (Ω)'), dc = dmm(0.5, MZ + 0.16, 'CAPACITOR (µF)');
    var osc = caseBox(0.78, MZ - 0.1, 0.2, 0.09, 0.12, DARK, 'OSCILLATOR 1 kHz', -0.25), sw = toggle(osc, 0.06, 0.06);
    var det = S.meter({ pos: [0.8, 0, MZ + 0.14], min: 0, max: 100, unit: 'µA', symbol: 'µA', caption: 'detector', rotY: -0.25 });
    lead([[MX - 0.42, 0.07, MZ - 0.06], [MX - 0.36, 0.06, MZ - 0.04], [MX - 0.3, 0.056, MZ - 0.02]], 'red');
    lead([[0.7, 0.06, MZ - 0.05], [0.4, 0.03, MZ - 0.25], [MX + 0.1, 0.056, MZ - 0.1]], 'black');
    A.name = 'Anderson\'s bridge'; A.info = 'Three 1000 Ω arms, the coil with r₁ in the fourth, a standard capacitor and the resistance r. The detector is quietest at balance.';
    A.knob = k2; A.key = k1; A.sw = sw; var cur = { r1: p.r1, r: p.r };
    A.tick = function () { d1.set(st.on ? String(Math.round(cur.r1)) : '----', 'Ω'); d2.set(st.on ? String(Math.round(cur.r)) : '----', 'Ω'); dc.set(rnd(st.vals.C, 2).toFixed(2), 'µF');
      det.set(st.on ? Math.min(100, KN.ig(assign(p, { C: st.vals.C * 1e-6 }), cur.r1, cur.r) * 1e6) : 0); k1.rotation.y = -cur.r1 / 800; k2.rotation.y = -cur.r / 800; };
    PLAN = {
      parts: null, controls: [[{ key: 'C', label: 'Standard capacitor', min: 0.02, max: 0.12, step: 0.01, unit: 'µF', digits: 2, def: 0.1 }]],
      act: ['Balance with r₁ and r'],
      take: function (part, v) { var q = assign(p, { C: v.C * 1e-6 }), m = KN.measure(q), r1 = Math.round(m.r1), r = Math.round(m.r);
        if (m.I_G > 2e-7 || r < 1) return { err: 'The detector will not go quiet: with this capacitor the balance needs a negative r. Use a smaller capacitor.' };
        var a1 = cur.r1, a2 = cur.r;
        return { row: { C: v.C, r1: r1, r: r }, say: 'Balanced: r₁ = ' + r1 + ' Ω, r = ' + r + ' Ω.', anim: function () { return S.tween(900, function (k) { cur.r1 = a1 + (r1 - a1) * k; cur.r = a2 + (r - a2) * k; }).then(function () { cur.r1 = r1; cur.r = r; }); } }; },
      cols: [{ label: 'C (µF)', get: function (r) { return r.C.toFixed(2); } }, { label: 'r₁ (Ω)', get: function (r) { return r.r1; } }, { label: 'r (Ω)', get: function (r) { return r.r; } },
        { label: 'L (mH)', get: function (r) { return (Lof(r) * 1000).toFixed(1); } }],
      ok: function (rows) { return rows.length >= 3; }, needText: 'Balance the bridge with at least three capacitors.',
      auto: [[0, { C: 0.1 }], [0, { C: 0.05 }], [0, { C: 0.02 }]],
      result: function (rows) { if (rows.length < 3) return null;
        return { label: 'Self-inductance of the coil', value: mean(rows.map(Lof)) * 1000, unit: 'mH', digits: 1, truth: p.Lx * 1000,
          note: 'L = C (R₃/R₄)[r (R₄ + R₂) + R₂ R₄] with R₂ = R₃ = R₄ = ' + p.R2 + ' Ω. The steady balance gives the coil\'s own resistance R₂R₃/R₄ − r₁ = ' + rnd(p.R2 * p.R3 / p.R4 - mean(rows.map(function (r) { return r.r1; })), 0) + ' Ω.' }; },
      tol: 0.02, formula: 'L = C (R₃ / R₄) [ r (R₄ + R₂) + R₂ R₄ ]', formulaNote: 'steady balance first: r₁ + r_coil = R₂ R₃ / R₄',
      live: function () { return 'r₁ = ' + Math.round(cur.r1) + ' Ω, r = ' + Math.round(cur.r) + ' Ω'; }
    };
    function Lof(r) { return r.C * 1e-6 * p.R3 / p.R4 * (r.r * (p.R4 + p.R2) + p.R2 * p.R4); }
  })();

  if (KNAME === 'w7_unibridge') (function () {
    var FN = Math.round(p.fn), g = caseBox(MX - 0.05, MZ, 0.5, 0.2, 0.22, CASE, 'UNIVERSAL LCR BRIDGE');
    var dMain = lcd(g, -0.12, 0.15, 0.13, 0.04), dLoss = lcd(g, 0.1, 0.15, 0.1, 0.04);
    plate(g, 'MAIN DIAL', 0.07, -0.12, 0.118, g.userData.front, '#2b323d'); plate(g, FN ? 'LOSS DIAL' : 'LOSS (not used)', 0.08, 0.1, 0.118, g.userData.front, '#2b323d');
    var kMain = knob(g, -0.12, 0.075, 0.022), kLoss = knob(g, 0.1, 0.075, 0.014), kFn = knob(g, 0.2, 0.15, 0.011), kRange = knob(g, 0.2, 0.08, 0.011), sw = toggle(g, -0.215, 0.15);
    plate(g, ['R', 'L', 'C'][FN] + ' FUNCTION', 0.06, 0.2, 0.118, g.userData.front, '#2b323d'); plate(g, 'RANGE', 0.04, 0.2, 0.05, g.userData.front, '#2b323d');
    var det = S.meter({ pos: [MX + 0.38, 0, MZ + 0.05], min: 0, max: 100, unit: 'µA', symbol: 'NULL', caption: 'detector', rotY: -0.3 });
    // the unknown on the top terminals
    var u = grp(MX - 0.05, MZ); post(u, -0.05, 0.2, -0.04, true); post(u, 0.05, 0.2, -0.04, false);
    if (FN === 1) { coilOn(u, 0.032, 0.05, 0, 0.245, -0.04, COPPER, 'x'); }
    else if (FN === 0) { coilOn(u, 0.008, 0.06, 0, 0.225, -0.04, col(0xc9b07a, 0.5), 'x'); [-0.012, 0, 0.012].forEach(function (x, i) { mk(u, cyl(0.0084, 0.0084, 0.005, 16), col([0xd8b020, 0x7a1fa2, 0x7a4a1c][i]), x, 0.225, -0.04).rotation.z = PI / 2; }); }
    else { mk(u, box(0.05, 0.035, 0.016), col(0x9a2b22, 0.35), 0, 0.235, -0.04); }
    flat(g, 'UNKNOWN', 0.07, 0, 0.2005, 0.02, '#2b323d');
    lead([[MX + 0.18, 0.1, MZ + 0.1], [MX + 0.28, 0.03, MZ + 0.14], [MX + 0.345, 0.07, MZ + 0.03]], 'black');
    var UN = [{ u: 'Ω', k: 1, d: 1, nm: 'Resistance' }, { u: 'mH', k: 1000, d: 2, nm: 'Inductance' }, { u: 'nF', k: 1e9, d: 2, nm: 'Capacitance' }][FN];
    A.name = 'Universal LCR bridge'; A.info = 'One bridge frame: the function switch puts the right standards in the arms, the range switch sets the multiplier, and the two dials bring the detector to a null.' + (SAMPLE ? ' On the terminals: ' + SAMPLE + '.' : '');
    A.knob = kRange; A.key = kMain; A.sw = sw; var cur = { dm: p.Dm, dl: p.Dl };
    A.tick = function () { dMain.set(st.on ? cur.dm.toFixed(1) : '----', 'Ω'); dLoss.set(st.on && FN ? cur.dl.toFixed(FN === 1 ? 0 : 1) : '----', 'Ω');
      det.set(st.on ? Math.min(100, KN.ig(assign(p, { Rr: st.vals.Rr }), cur.dm, cur.dl) * 1e6) : 0); kMain.rotation.z = -cur.dm / 1500; kRange.rotation.z = -Math.log(st.vals.Rr) / Math.LN10; };
    PLAN = {
      parts: null, controls: [[{ key: 'Rr', label: 'Range resistor', opts: [100, 1000, 10000], unit: 'Ω', digits: 0, def: 1000 }]],
      act: [FN ? 'Balance with the main dial and the loss dial' : 'Balance with the main dial'],
      take: function (part, v) { var q = assign(p, { Rr: v.Rr }), m = KN.measure(q), dm = rnd(m.Dm, 1), dl = rnd(m.Dl, FN === 1 ? 0 : 1);
        if (m.Dm > 11100 || m.Dm < 5 || m.I_G > 2e-7) return { err: 'The main dial runs out before the detector goes quiet on this range. Try the next range.' };
        var a1 = cur.dm, a2 = cur.dl;
        return { row: { Rr: v.Rr, dm: dm, dl: dl, val: KN.value(q, dm, dl) }, say: 'Null with the main dial at ' + dm.toFixed(1) + ' Ω' + (FN ? ' and the loss dial at ' + dl + ' Ω.' : '.'),
          anim: function () { return S.tween(900, function (k) { cur.dm = a1 + (dm - a1) * k; cur.dl = a2 + (dl - a2) * k; }).then(function () { cur.dm = dm; cur.dl = dl; }); } }; },
      cols: [{ label: 'range (Ω)', get: function (r) { return r.Rr; } }, { label: 'main dial (Ω)', get: function (r) { return r.dm.toFixed(1); } },
        { label: 'loss dial (Ω)', get: function (r) { return FN ? r.dl : '—'; } }, { label: UN.nm + ' (' + UN.u + ')', get: function (r) { return (r.val * UN.k).toFixed(UN.d); } }],
      ok: function (rows) { return rows.length >= 2; }, needText: 'Balance on at least two ranges.',
      auto: [[0, { Rr: 100 }], [0, { Rr: 1000 }], [0, { Rr: 10000 }]],
      result: function (rows) { if (rows.length < 2) return null; var last = rows[rows.length - 1];
        return { label: UN.nm + ' of the unknown', value: mean(rows.map(function (r) { return r.val; })) * UN.k, unit: UN.u, digits: UN.d, truth: HK.TEXTBOOK.w7_uni_val(p) * UN.k,
          note: 'The mean over ' + rows.length + ' ranges. ' + (FN === 1 ? 'Lx = Rr · Dm · Cs with Cs = ' + rnd(p.Cs * 1e6, 2) + ' µF; the loss dial gives the coil\'s series resistance Rr Dm / Dl = ' + rnd(last.Rr * last.dm / last.dl, 1) + ' Ω.'
            : FN === 2 ? 'Cx = Cs · Dm / Rr with Cs = ' + rnd(p.Cs * 1e6, 2) + ' µF; the loss dial gives the capacitor\'s series resistance Dl Rr / Dm = ' + rnd(last.dl * last.Rr / last.dm, 1) + ' Ω.' : 'Rx = Rr · Dm / Ra with Ra = ' + p.Ra + ' Ω.') }; },
      tol: 0.02, formula: ['Rx = Rr · Dm / Ra', 'Lx = Rr · Dm · Cs', 'Cx = Cs · Dm / Rr'][FN], formulaNote: 'Dm is the main dial reading at the null, Rr the range resistor',
      live: function () { return 'Main dial ' + cur.dm.toFixed(1) + ' Ω on the ' + st.vals.Rr + ' Ω range'; }
    };
  })();

  if (KNAME === 'w7_qmeter') (function () {
    var g = caseBox(MX - 0.05, MZ, 0.5, 0.2, 0.22, CASE, 'Q-METER');
    var dF = lcd(g, -0.14, 0.15, 0.12, 0.038), dC = lcd(g, 0.05, 0.15, 0.12, 0.038);
    plate(g, 'FREQUENCY', 0.07, -0.14, 0.12, g.userData.front, '#2b323d'); plate(g, 'TUNING CAPACITOR', 0.1, 0.05, 0.12, g.userData.front, '#2b323d');
    var kF = knob(g, -0.14, 0.075, 0.016), kC = knob(g, 0.05, 0.075, 0.022), sw = toggle(g, 0.215, 0.15);
    var qm = S.meter({ pos: [MX + 0.38, 0, MZ + 0.05], min: 0, max: 250, unit: 'Q', symbol: 'Q', caption: 'circuit Q', rotY: -0.3 });
    var u = grp(MX - 0.05, MZ); post(u, -0.06, 0.2, -0.03, true); post(u, 0.06, 0.2, -0.03, false);
    mk(u, cyl(0.02, 0.02, 0.09, 24), col(0xe9e2cf, 0.6), 0, 0.235, -0.03).rotation.z = PI / 2; coilOn(u, 0.0215, 0.06, 0, 0.235, -0.03, COPPER, 'x');
    flat(g, 'COIL', 0.05, 0, 0.2005, 0.03, '#2b323d');
    lead([[MX + 0.18, 0.1, MZ + 0.1], [MX + 0.28, 0.03, MZ + 0.14], [MX + 0.345, 0.07, MZ + 0.03]], 'black');
    A.name = 'Q-meter'; A.info = 'An oscillator injects a small known voltage in series with the coil and the tuning capacitor; the voltmeter across the capacitor is marked in Q.';
    A.knob = kF; A.key = kC; A.sw = sw; var cur = { c: p.C };
    A.tick = function () { var f = st.vals.f * 1e6; dF.set(st.on ? st.vals.f.toFixed(2) : '----', 'MHz'); dC.set(st.on ? (cur.c * 1e12).toFixed(1) : '----', 'pF');
      qm.set(st.on ? Math.min(250, KN.vc(p, f, cur.c) / p.e) : 0); kC.rotation.z = -cur.c * 1e10; kF.rotation.z = -st.vals.f * 2; };
    function pairs(rows) { var out = [], i, j; for (i = 0; i < rows.length; i++) for (j = 0; j < rows.length; j++) if (Math.abs(rows[j].f - 2 * rows[i].f) < 1e-6) out.push([rows[i], rows[j]]); return out; }
    PLAN = {
      parts: null, controls: [[{ key: 'f', label: 'Oscillator frequency', min: 0.4, max: 1.7, step: 0.05, unit: 'MHz', digits: 2, def: 1.0 }]],
      act: ['Tune the capacitor for maximum Q'],
      take: function (part, v) { var f = v.f * 1e6, c = KN.tune(p, f), q = KN.vc(p, f, c) / p.e, a = cur.c;
        if (c < 1.2e-11 || c > 5.9e-10) return { err: 'The coil does not resonate within the range of the tuning capacitor at this frequency.' };
        var row = { f: rnd(v.f, 2), C: rnd(c * 1e12, 1), Q: Math.round(q) };
        return { row: row, say: 'Resonance at C = ' + row.C.toFixed(1) + ' pF; the meter reads Q = ' + row.Q + '.', anim: function () { return S.tween(900, function (k) { cur.c = a + (c - a) * k; }).then(function () { cur.c = c; }); } }; },
      cols: [{ label: 'f (MHz)', get: function (r) { return r.f.toFixed(2); } }, { label: 'C (pF)', get: function (r) { return r.C.toFixed(1); } }, { label: 'Q', get: function (r) { return r.Q; } }],
      ok: function (rows) { return rows.length >= 5 && pairs(rows).length >= 1; }, needText: 'Take at least five frequencies, with one pair an octave apart (f and 2f).',
      auto: [0.5, 0.6, 0.8, 1.0, 1.2, 1.6].map(function (f) { return [0, { f: f }]; }),
      result: function (rows) { var pr = pairs(rows); if (rows.length < 5 || !pr.length) return null;
        var cd = mean(pr.map(function (q) { return (q[0].C - 4 * q[1].C) / 3; })), best = rows[0];
        rows.forEach(function (r) { if (r.Q > best.Q) best = r; });
        return { label: 'Inductance of the coil', value: mean(pr.map(function (q) { var w = 2 * PI * q[0].f * 1e6; return 1 / (w * w * (q[0].C + (q[0].C - 4 * q[1].C) / 3) * 1e-12); })) * 1e6, unit: 'µH', digits: 1, truth: p.L * 1e6,
          note: 'From ' + pr.length + ' octave pair(s): self-capacitance Cd = (C₁ − 4C₂)/3 = ' + rnd(cd, 1) + ' pF. The indicated Q is greatest (' + best.Q + ') near ' + best.f.toFixed(2) + ' MHz; the coil\'s own Q there is Q (1 + Cd/C) = ' + Math.round(best.Q * (1 + cd / best.C)) + '.' }; },
      graph: { x: function (r) { return r.f; }, y: function (r) { return r.Q; }, xlabel: 'frequency (MHz)', ylabel: 'indicated Q' },
      tol: 0.02, formula: 'Q = V_C / e,   L = 1 / (ω² (C₁ + Cd)),   Cd = (C₁ − 4C₂) / 3', formulaNote: 'C₁ tunes the coil at f and C₂ at 2f',
      live: function () { return 'Tuning capacitor ' + (cur.c * 1e12).toFixed(1) + ' pF'; }
    };
  })();

  /* ================================================================ RC / RL time constant */
  if (KNAME === 'w7_tau') (function () {
    var RL = p.mode >= 0.5, bd = grp(MX - 0.25, MZ + 0.05);
    mk(bd, box(0.3, 0.012, 0.18), col(0x1d5b3a, 0.6), 0, 0.006, 0);
    var rb = S.resistanceBox([MX - 0.32, 0.012, MZ + 0.05]);
    if (RL) { var cg = new T.Group(); cg.position.set(0.09, 0.012, 0); bd.add(cg); mk(cg, cyl(0.03, 0.03, 0.005, 24), M.bakelite, 0, 0.0025, 0); coilOn(cg, 0.024, 0.04, 0, 0.025, 0, COPPER, 'y'); mk(cg, cyl(0.03, 0.03, 0.005, 24), M.bakelite, 0, 0.0475, 0); }
    else { mk(bd, cyl(0.013, 0.013, 0.03, 20), col(0x2a4f9c, 0.4), 0.09, 0.027, 0); }
    flat(bd, RL ? 'R  —  COIL L' : 'R  —  C', 0.12, 0, 0.0125, 0.07); S.contact(0.36, 0.24, MX - 0.25, MZ + 0.05, 0.5);
    var fg = caseBox(MX - 0.25, MZ - 0.22, 0.24, 0.09, 0.12, DARK, 'FUNCTION GENERATOR · SQUARE'), sw = toggle(fg, 0.09, 0.06), dfg = lcd(fg, -0.03, 0.058, 0.1, 0.032);
    var sc = scope(MX + 0.3, MZ, 'OSCILLOSCOPE');
    lead([[MX - 0.2, 0.07, MZ - 0.16], [MX - 0.12, 0.03, MZ - 0.06], [MX - 0.16, 0.03, MZ + 0.05]], 'red');
    lead([[MX - 0.16, 0.04, MZ + 0.05], [MX + 0.05, 0.03, MZ + 0.15], [MX + 0.2, 0.06, MZ + 0.1]], 'yellow');
    A.name = RL ? 'RL board, function generator and oscilloscope' : 'RC board, function generator and oscilloscope';
    A.info = 'A square wave switches the voltage on and off; the oscilloscope shows the ' + (RL ? 'voltage across R, which follows the current.' : 'voltage across the capacitor.') + (SAMPLE ? ' ' + SAMPLE + '.' : '');
    A.knob = rb; A.key = sc.knob; A.sw = sw; A.view = [[MX + 0.2, 0.5, 0.5], [MX + 0.15, 0.08, MZ]];
    var lastKey = '';
    A.tick = function () { rb.show(Math.round(st.vals.R / (RL ? 20 : 200))); var q = assign(p, { R: st.vals.R }), tau = 1 / KN.rate(q), key = st.on + '|' + st.vals.R + '|' + S.rows.length;
      dfg.set(st.on ? sig(1 / (20 * tau), 2).toString() : '----', 'Hz'); if (key === lastKey) return; lastKey = key;
      sc.draw(function (c, w, h, grid) { grid(c, w, h, st.on ? 'time/div ' + sig(tau * 1000, 2) + ' ms' : 'off'); if (!st.on) return;
        var pts = [], i, x, v; for (i = 0; i <= 300; i++) { x = i / 300 * 10; v = x < 0.5 ? 0 : 1 - Math.exp(-(x - 0.5)); pts.push([x / 10 * w, h * 0.85 - v * h * 0.7]); } trace(c, pts);
        c.strokeStyle = '#ffd24a'; c.lineWidth = 2; c.setLineDash([8, 8]); c.beginPath(); c.moveTo(0, h * 0.85 - 0.632 * h * 0.7); c.lineTo(w, h * 0.85 - 0.632 * h * 0.7); c.moveTo(1.5 / 10 * w, 0); c.lineTo(1.5 / 10 * w, h); c.stroke(); c.setLineDash([]);
        c.fillStyle = '#ffd24a'; c.font = '600 22px "JetBrains Mono", monospace'; c.fillText('63.2 %   Δt = ' + sig(tau * 1000, 4) + ' ms', w * 0.3, h * 0.85 - 0.632 * h * 0.7 - 10); }); };
    PLAN = {
      parts: null, controls: [[RL ? { key: 'R', label: 'Resistance box', min: 200, max: 2000, step: 100, unit: 'Ω', digits: 0, def: 1000 } : { key: 'R', label: 'Resistance box', min: 2000, max: 20000, step: 1000, unit: 'Ω', digits: 0, def: 10000 }]],
      act: ['Read the time to 63.2 % with the cursors'],
      take: function (part, v) { var m = KN.measure(assign(p, { R: v.R })), t = sig(m.tau, 4);
        return { row: { R: v.R, tau: t }, say: 'The trace reaches 63.2 % of its final height ' + sig(t * 1000, 4) + ' ms after the edge.' }; },
      cols: [{ label: 'R (Ω)', get: function (r) { return r.R; } }, { label: 'τ (ms)', get: function (r) { return (r.tau * 1000).toFixed(4); } },
        RL ? { label: '1/τ (1/ms)', get: function (r) { return (1e-3 / r.tau).toFixed(3); } } : { label: 'τ / R (µF)', get: function (r) { return (r.tau / r.R * 1e6).toFixed(4); } }],
      ok: function (rows) { return rows.length >= 4; }, needText: 'Take at least four resistances.',
      auto: (RL ? [400, 800, 1200, 1600, 2000] : [4000, 8000, 12000, 16000, 20000]).map(function (r) { return [0, { R: r }]; }),
      result: function (rows) { if (rows.length < 4) return null; var s, ic;
        if (RL) { s = slope(rows.map(function (r) { return [r.R, 1 / r.tau]; })); ic = mean(rows.map(function (r) { return 1 / r.tau - s * r.R; })) / s;
          return { label: 'Inductance of the coil, from τ = L / R', value: 1000 / s, unit: 'mH', digits: 1, truth: p.L * 1000,
            note: 'The graph of 1/τ against R is a straight line of slope 1/L. Its intercept shows ' + rnd(ic, 0) + ' Ω of extra resistance: the coil\'s own winding and the generator. Time constants ran from ' + sig(rows[0].tau * 1e6, 3) + ' µs to ' + sig(rows[rows.length - 1].tau * 1e6, 3) + ' µs.' }; }
        s = slope(rows.map(function (r) { return [r.R, r.tau]; })); ic = mean(rows.map(function (r) { return r.tau - s * r.R; })) / s;
        return { label: 'Capacitance, from τ = R C', value: s * 1e6, unit: 'µF', digits: 4, truth: p.C * 1e6,
          note: 'The graph of τ against R is a straight line of slope C. Its intercept shows ' + rnd(ic, 0) + ' Ω of extra resistance: the generator\'s own output resistance. Time constants ran from ' + sig(rows[0].tau * 1000, 3) + ' ms to ' + sig(rows[rows.length - 1].tau * 1000, 3) + ' ms.' }; },
      graph: RL ? { x: function (r) { return r.R; }, y: function (r) { return 1e-3 / r.tau; }, xlabel: 'R (Ω)', ylabel: '1/τ (1/ms)' } : { x: function (r) { return r.R / 1000; }, y: function (r) { return r.tau * 1000; }, xlabel: 'R (kΩ)', ylabel: 'τ (ms)' },
      tol: 0.02, formula: RL ? 'i = I₀ (1 − e^(−t/τ)),   τ = L / R' : 'v = V₀ (1 − e^(−t/τ)),   τ = R C', formulaNote: 'τ is the time to reach 63.2 % of the final value',
      live: function () { return 'R = ' + st.vals.R + ' Ω'; }
    };
  })();

  /* ================================================================ transformer */
  if (KNAME === 'w7_xfmr') (function () {
    var UP = p.nr > 1, g = grp(MX - 0.1, MZ), lam = col(0x4b4d52, 0.35, 0.6);
    mk(g, box(0.3, 0.014, 0.16), M.bakelite, 0, 0.007, 0);
    mk(g, box(0.2, 0.03, 0.05), lam, 0, 0.03, 0); mk(g, box(0.2, 0.03, 0.05), lam, 0, 0.17, 0); mk(g, box(0.03, 0.14, 0.05), lam, -0.085, 0.1, 0); mk(g, box(0.03, 0.14, 0.05), lam, 0.085, 0.1, 0);
    coilOn(g, UP ? 0.03 : 0.04, 0.1, -0.085, 0.1, 0, COPPER, 'y'); coilOn(g, UP ? 0.04 : 0.03, 0.1, 0.085, 0.1, 0, GREENW, 'y');
    [-0.12, -0.05, 0.05, 0.12].forEach(function (x, i) { post(g, x, 0.014, 0.065, i % 2 === 0); });
    flat(g, 'PRIMARY            SECONDARY', 0.24, 0, 0.0145, 0.045); S.contact(0.36, 0.22, MX - 0.1, MZ, 0.55);
    var sup = caseBox(MX - 0.48, MZ, 0.18, 0.1, 0.12, DARK, 'AC SUPPLY 12 V · 50 Hz'), sw = toggle(sup, 0.05, 0.065);
    var wm = caseBox(MX - 0.36, MZ + 0.24, 0.26, 0.09, 0.1, col(0xe0a93c, 0.55), 'PRIMARY  V · A · W'), dv1 = lcd(wm, -0.085, 0.055, 0.07, 0.03), di1 = lcd(wm, 0, 0.055, 0.07, 0.03), dp1 = lcd(wm, 0.085, 0.055, 0.07, 0.03);
    var m2 = caseBox(MX + 0.1, MZ + 0.24, 0.2, 0.09, 0.1, col(0xe0a93c, 0.55), 'SECONDARY  V · A'), dv2 = lcd(m2, -0.045, 0.055, 0.08, 0.03), di2 = lcd(m2, 0.045, 0.055, 0.08, 0.03);
    var rh = S.rheostat([MX + 0.3, 0, MZ - 0.02], 0.24); var rl = S.label('LOAD RHEOSTAT', { w: 0.1, ratio: 0.2, color: '#e9dfc2' }); rl.rotation.x = -PI / 2; rl.position.set(MX + 0.3, 0.002, MZ + 0.05); S.scene.add(rl);
    var lk = S.plugKey([MX + 0.3, 0, MZ - 0.14]);
    lead([[MX - 0.4, 0.06, MZ + 0.05], [MX - 0.3, 0.03, MZ + 0.1], [MX - 0.22, 0.03, MZ + 0.065]], 'red');
    lead([[MX - 0.05, 0.03, MZ + 0.065], [MX + 0.1, 0.03, MZ + 0.1], [MX + 0.2, 0.05, MZ - 0.02]], 'black');
    A.name = (UP ? 'Step-up' : 'Step-down') + ' transformer'; A.info = 'Two windings on a laminated iron core, fed from a 12 V laboratory AC supply. Meters read the primary voltage, current and power and the secondary voltage and current.';
    A.knob = rh.userData.slider; A.key = lk.userData.plug; A.sw = sw; var C0 = PLAN_CTRL();
    function PLAN_CTRL() { return UP ? { key: 'RL', label: 'Load rheostat', min: 50, max: 1000, step: 50, unit: 'Ω', digits: 0, def: 200 } : { key: 'RL', label: 'Load rheostat', min: 5, max: 100, step: 5, unit: 'Ω', digits: 0, def: 20 }; }
    function read(part, RLv) { var r = KN.solve(p, part ? RLv : 0); return { V1: rnd(p.V1, 2), I1: rnd(r.I1, 3), P1: rnd(r.Pin, 2), V2: rnd(r.V2, 2), I2: rnd(r.I2, 3) }; }
    A.tick = function () { var r = read(st.part, st.vals.RL), on = st.on; rh.setFraction((st.vals.RL - C0.min) / (C0.max - C0.min)); lk.set(st.part === 1);
      dv1.set(on ? r.V1.toFixed(2) : '----', 'V'); di1.set(on ? r.I1.toFixed(3) : '----', 'A'); dp1.set(on ? r.P1.toFixed(2) : '----', 'W'); dv2.set(on ? r.V2.toFixed(2) : '----', 'V'); di2.set(on ? r.I2.toFixed(3) : '----', 'A'); };
    function eta(r) { return r.P1 > 0 ? r.V2 * r.I2 / r.P1 : 0; }
    PLAN = {
      parts: ['Secondary open (turns ratio)', 'Secondary on load (efficiency)'], controls: [[], [C0]], act: ['Read the meters', 'Read the meters'],
      take: function (part, v) { var r = read(part, v.RL); r.part = part; r.RL = part ? v.RL : null;
        return { row: r, say: part ? 'On ' + v.RL + ' Ω: ' + r.V2.toFixed(2) + ' V and ' + r.I2.toFixed(3) + ' A out, ' + r.P1.toFixed(2) + ' W in.' : 'Open circuit: ' + r.V1.toFixed(2) + ' V on the primary, ' + r.V2.toFixed(2) + ' V on the secondary.' }; },
      cols: [{ label: 'load (Ω)', get: function (r) { return r.part ? r.RL : 'open'; } }, { label: 'V₁ (V)', get: function (r) { return r.V1.toFixed(2); } }, { label: 'I₁ (A)', get: function (r) { return r.I1.toFixed(3); } },
        { label: 'P₁ (W)', get: function (r) { return r.P1.toFixed(2); } }, { label: 'V₂ (V)', get: function (r) { return r.V2.toFixed(2); } }, { label: 'I₂ (A)', get: function (r) { return r.I2.toFixed(3); } },
        { label: 'η (%)', get: function (r) { return r.part ? (eta(r) * 100).toFixed(1) : '—'; } }],
      ok: function (rows) { return rows.some(function (r) { return r.part === 0; }) && rows.filter(function (r) { return r.part === 1; }).length >= 4; },
      needText: 'Take the open-circuit reading and at least four loads.',
      auto: [[0, {}]].concat((UP ? [100, 200, 400, 800] : [10, 20, 40, 80]).map(function (r) { return [1, { RL: r }]; })),
      result: function (rows) { if (!this.ok(rows)) return null; var o = rows.filter(function (r) { return r.part === 0; })[0], ld = rows.filter(function (r) { return r.part === 1; }), best = ld[0];
        ld.forEach(function (r) { if (eta(r) > eta(best)) best = r; });
        return { label: 'Turns ratio Ns / Np', value: o.V2 / o.V1, unit: '', digits: 3, truth: p.nr,
          note: 'From the open-circuit voltages. The open-circuit input, ' + o.P1.toFixed(2) + ' W, is the iron loss. On load the efficiency V₂I₂/P₁ was highest at ' + (eta(best) * 100).toFixed(1) + ' % with ' + best.RL + ' Ω (' + best.I2.toFixed(3) + ' A).' }; },
      graph: { x: function (r) { return r.I2; }, y: function (r) { return r.part ? eta(r) * 100 : 0; }, xlabel: 'secondary current I₂ (A)', ylabel: 'efficiency (%)' },
      tol: 0.015, formula: 'Vs / Vp = Ns / Np,   η = Vs Is / P_in', formulaNote: 'the turns ratio from the open-circuit voltages; the efficiency on load',
      live: function () { return st.part ? 'Load ' + st.vals.RL + ' Ω' : 'Secondary open'; }
    };
  })();

  /* ================================================================ DC motor */
  if (KNAME === 'w7_motor') (function () {
    var g = grp(MX - 0.12, MZ);
    mk(g, box(0.26, 0.014, 0.16), M.darkWood, 0, 0.007, 0); mk(g, box(0.012, 0.09, 0.09), M.alu, -0.04, 0.059, 0);
    var body = coilOn(g, 0.035, 0.09, -0.09, 0.07, 0, col(0x3a3f47, 0.35, 0.7), 'x'); mk(g, cyl(0.036, 0.036, 0.012, 28), M.blackPlastic, -0.14, 0.07, 0).rotation.z = PI / 2;
    var shaft = mk(g, cyl(0.003, 0.003, 0.09, 12), M.steel, 0.0, 0.07, 0); shaft.rotation.z = PI / 2;
    var disc = new T.Group(); disc.position.set(0.05, 0.07, 0); g.add(disc);
    var dtex = S.canvasTex(256, 256, function (c) { c.fillStyle = '#16181b'; c.beginPath(); c.arc(128, 128, 126, 0, 7); c.fill(); c.fillStyle = '#f2f2ef'; c.beginPath(); c.moveTo(128, 128); c.arc(128, 128, 122, -0.35, 0.35); c.fill(); });
    var dm_ = S.mesh(cyl(0.045, 0.045, 0.004, 40), [M.black, new T.MeshStandardMaterial({ map: dtex, roughness: 0.5 }), new T.MeshStandardMaterial({ map: dtex, roughness: 0.5 })]); dm_.rotation.z = PI / 2; disc.add(dm_);
    post(g, -0.1, 0.014, 0.06, true); post(g, -0.07, 0.014, 0.06, false);
    flat(g, 'DC MOTOR   Ra = ' + p.Ra + ' Ω', 0.16, 0.02, 0.0145, 0.06); S.contact(0.32, 0.22, MX - 0.12, MZ, 0.55);
    var sup = caseBox(MX - 0.48, MZ, 0.2, 0.1, 0.12, DARK, 'VARIABLE DC SUPPLY'), dV = lcd(sup, -0.03, 0.062, 0.1, 0.034), kV = knob(sup, 0.065, 0.062, 0.012), sw = toggle(sup, 0.065, 0.03);
    var am = dmm(MX - 0.3, MZ + 0.26, 'ARMATURE CURRENT'), tach = caseBox(MX + 0.2, MZ + 0.05, 0.1, 0.07, 0.16, col(0x23272d, 0.5), 'TACHOMETER', -0.9), dT = lcd(tach, 0, 0.045, 0.085, 0.03);
    lead([[MX - 0.4, 0.07, MZ + 0.05], [MX - 0.3, 0.03, MZ + 0.1], [MX - 0.22, 0.035, MZ + 0.06]], 'red');
    A.name = 'DC motor with a marked disc'; A.info = 'A small permanent-magnet motor running light. The optical tachometer counts the white mark on the disc; the armature resistance is printed on the board.';
    A.knob = kV; A.key = tach; A.sw = sw; var live = { w: 0 };
    A.tick = function (dt) { var q = assign(p, { V: st.on ? st.vals.V : 0 }), s = { t: 0, w: live.w }; KN.step(s, q, Math.min(dt, 0.05)); live.w = s.w; disc.rotation.x -= Math.min(live.w, 40) * dt;
      dV.set(st.on ? st.vals.V.toFixed(1) : '----', 'V'); am.set(st.on ? ((st.vals.V - p.k * live.w) / p.Ra).toFixed(3) : '----', 'A'); dT.set(st.on ? String(Math.round(live.w * 60 / (2 * PI))) : '----', 'rpm'); };
    PLAN = {
      parts: null, controls: [[{ key: 'V', label: 'Supply voltage', min: 1, max: 12, step: 0.5, unit: 'V', digits: 1, def: 6 }]], act: ['Read the tachometer and the ammeter'],
      take: function (part, v) { var m = KN.measure(assign(p, { V: v.V })); if (m.w <= 0) return { err: 'The motor does not start at this voltage: friction holds it. Raise the voltage.' };
        live.w = m.w; var row = { V: v.V, I: rnd(m.I, 3), rpm: Math.round(m.rpm) };
        return { row: row, say: 'At ' + v.V.toFixed(1) + ' V the motor settles at ' + row.rpm + ' rev/min and draws ' + row.I.toFixed(3) + ' A.' }; },
      cols: [{ label: 'V (V)', get: function (r) { return r.V.toFixed(1); } }, { label: 'I (A)', get: function (r) { return r.I.toFixed(3); } }, { label: 'N (rev/min)', get: function (r) { return r.rpm; } },
        { label: 'k = (V − I Ra)/ω', get: function (r) { return kof(r).toFixed(5); } }],
      ok: function (rows) { return rows.length >= 5; }, needText: 'Take at least five voltages.',
      auto: [2, 4, 6, 8, 10, 12].map(function (v) { return [0, { V: v }]; }),
      result: function (rows) { if (rows.length < 5) return null; var sl = slope(rows.map(function (r) { return [r.V, r.rpm]; }));
        return { label: 'Back-emf constant k', value: mean(rows.map(kof)), unit: 'V s/rad', digits: 4, truth: p.k,
          note: 'k = (V − I Ra) / ω with Ra = ' + p.Ra + ' Ω. The speed rises by ' + rnd(sl, 0) + ' rev/min for every volt, a straight line that does not pass through the origin because friction needs a small voltage before the motor turns.' }; },
      graph: { x: function (r) { return r.V; }, y: function (r) { return r.rpm; }, xlabel: 'supply voltage (V)', ylabel: 'speed (rev/min)' },
      tol: 0.02, formula: 'V = I Ra + k ω,   ω = 2π N / 60', formulaNote: 'k is the back emf per unit angular speed (and the torque per ampere)',
      live: function () { return Math.round(live.w * 60 / (2 * PI)) + ' rev/min'; }
    };
    function kof(r) { return (r.V - r.I * p.Ra) / (r.rpm * 2 * PI / 60); }
  })();

  /* ================================================================ generator */
  if (KNAME === 'w7_gen') (function () {
    var DC = p.mode >= 0.5, g = grp(MX - 0.14, MZ);
    mk(g, box(0.34, 0.014, 0.2), M.darkWood, 0, 0.007, 0);
    mk(g, box(0.05, 0.11, 0.1), col(0xb3261e, 0.4), -0.02, 0.085, -0.075); mk(g, box(0.05, 0.11, 0.1), col(0x2c5fb4, 0.4), -0.02, 0.085, 0.075);
    plate(g, 'N', 0.03, -0.02, 0.1, -0.0245, undefined, '#ffffff', 0.9).rotation.y = 0; plate(g, 'S', 0.03, 0.006, 0.1, 0.075, undefined, '#ffffff', 0.9).rotation.y = PI / 2;
    var rot = new T.Group(); rot.position.set(0, 0.085, 0); g.add(rot);
    mk(rot, cyl(0.003, 0.003, 0.3, 12), M.steel, 0.02, 0, 0).rotation.z = PI / 2;
    [[0, 0.03, 0.06, 0.004], [0, -0.03, 0.06, 0.004]].forEach(function (q) { mk(rot, box(0.06, 0.004, 0.004), COPPER, -0.02, q[1], 0); });
    [-0.05, 0.01].forEach(function (x) { mk(rot, box(0.004, 0.064, 0.004), COPPER, x, 0, 0); });
    if (DC) { var h1 = mk(rot, new T.CylinderGeometry(0.014, 0.014, 0.02, 24, 1, false, 0.08, PI - 0.16), M.brass, 0.09, 0, 0); h1.rotation.z = PI / 2; var h2 = mk(rot, new T.CylinderGeometry(0.014, 0.014, 0.02, 24, 1, false, PI + 0.08, PI - 0.16), M.copper, 0.09, 0, 0); h2.rotation.z = PI / 2; }
    else { [0.08, 0.105].forEach(function (x) { mk(rot, cyl(0.014, 0.014, 0.012, 28), M.brass, x, 0, 0).rotation.z = PI / 2; }); }
    [-0.02, 0.02].forEach(function (z, i) { mk(g, box(0.008, 0.07, 0.006), col(0x26282c, 0.6), DC ? 0.09 : 0.08 + i * 0.025, 0.045, DC ? z * 0.9 : 0.016); });
    mk(g, box(0.02, 0.085, 0.06), M.alu, 0.135, 0.05, 0); mk(g, box(0.02, 0.085, 0.06), M.alu, -0.12, 0.05, 0);
    var pul = mk(rot, cyl(0.022, 0.022, 0.01, 28), M.blackPlastic, -0.14, 0, 0); pul.rotation.z = PI / 2;
    flat(g, DC ? 'DC GENERATOR · SPLIT RING' : 'AC GENERATOR · SLIP RINGS', 0.2, 0.0, 0.0145, 0.088); S.contact(0.4, 0.26, MX - 0.14, MZ, 0.55);
    var drv = caseBox(MX - 0.5, MZ, 0.18, 0.1, 0.12, DARK, 'DRIVE MOTOR SPEED'), dS = lcd(drv, -0.03, 0.062, 0.09, 0.034), kS = knob(drv, 0.06, 0.062, 0.012), sw = toggle(drv, 0.06, 0.03);
    var sc = scope(MX + 0.34, MZ, 'OSCILLOSCOPE');
    lead([[MX - 0.03, 0.02, MZ + 0.02], [MX + 0.08, 0.03, MZ + 0.14], [MX + 0.22, 0.06, MZ + 0.1]], 'yellow');
    A.name = DC ? 'DC generator (split-ring commutator)' : 'AC generator (slip rings)'; A.info = 'A coil of ' + Math.round(p.N) + ' turns and area ' + rnd(p.A * 1e4, 1) + ' cm² turned between the poles of a magnet by a small drive motor. ' + (DC ? 'A split ring reverses the connections every half turn.' : 'Each end of the coil stays on its own slip ring.');
    A.knob = kS; A.key = sc.knob; A.sw = sw; A.view = [[MX + 0.1, 0.5, 0.5], [MX + 0.08, 0.08, MZ]];
    var lastKey = '', ang = 0;
    A.tick = function (dt) { if (st.on) { ang += Math.min(st.vals.f, 6) * 2 * PI * dt * 0.25; rot.rotation.x = ang; } dS.set(st.on ? st.vals.f.toFixed(0) : '----', 'rev/s');
      var key = st.on + '|' + st.vals.f; if (key === lastKey) return; lastKey = key; var q = assign(p, { f: st.vals.f }), full = p.N * p.B * p.A * 2 * PI * 25;
      sc.draw(function (c, w, h, grid) { grid(c, w, h, st.on ? 'time/div ' + sig(200 / st.vals.f, 2) + ' ms' : 'off'); if (!st.on) return; var pts = [], i;
        for (i = 0; i <= 400; i++) pts.push([i / 400 * w, h / 2 - KN.emf(q, i / 400 * 2 / st.vals.f) / full * h * 0.42]); trace(c, pts);
        c.strokeStyle = 'rgba(80,220,120,.5)'; c.lineWidth = 2; c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.stroke(); }); };
    PLAN = {
      parts: null, controls: [[{ key: 'f', label: 'Speed of the coil', min: 2, max: 25, step: 1, unit: 'rev/s', digits: 0, def: 10 }]], act: ['Read the peak emf from the trace'],
      take: function (part, v) { var m = KN.measure(assign(p, { f: v.f })), row = { f: v.f, pk: rnd(m.peak, 3), mean: rnd(m.mean, 3) + 0 };
        return { row: row, say: 'At ' + v.f + ' rev/s the peak emf is ' + row.pk.toFixed(3) + ' V' + (DC ? ' and the mean ' + row.mean.toFixed(3) + ' V: always the same sign.' : ', alternating about zero.') }; },
      cols: [{ label: 'f (rev/s)', get: function (r) { return r.f; } }, { label: 'ω (rad/s)', get: function (r) { return (2 * PI * r.f).toFixed(1); } }, { label: 'peak emf (V)', get: function (r) { return r.pk.toFixed(3); } },
        { label: 'mean emf (V)', get: function (r) { return r.mean.toFixed(3); } }],
      ok: function (rows) { return rows.length >= 5; }, needText: 'Take at least five speeds.',
      auto: [5, 10, 15, 20, 25].map(function (f) { return [0, { f: f }]; }),
      result: function (rows) { if (rows.length < 5) return null; var a = 0, b = 0; rows.forEach(function (r) { var w = 2 * PI * r.f; a += r.pk * w; b += w * w; });
        return { label: 'Flux linkage N B A', value: a / b * 1000, unit: 'mWb', digits: 2, truth: p.N * p.B * p.A * 1000,
          note: 'The slope of peak emf against ω. With N = ' + Math.round(p.N) + ' and A = ' + rnd(p.A * 1e4, 1) + ' cm² the field of the magnet is ' + rnd(a / b / (p.N * p.A) * 1000, 1) + ' mT. ' +
            (DC ? 'The mean of the one-way output is 2/π of its peak (' + rnd(mean(rows.map(function (r) { return r.mean / r.pk; })), 3) + ' measured).' : 'The mean of the alternating output is zero.') }; },
      graph: { x: function (r) { return 2 * PI * r.f; }, y: function (r) { return r.pk; }, xlabel: 'ω (rad/s)', ylabel: 'peak emf (V)' },
      tol: 0.02, formula: DC ? 'ε = | N B A ω sin ωt |' : 'ε = N B A ω sin ωt', formulaNote: 'the peak emf N B A ω is proportional to the speed',
      live: function () { return st.vals.f + ' rev/s'; }
    };
  })();

  /* ================================================================ falling magnet */
  if (KNAME === 'w7_fallmag') (function () {
    var g = grp(MX - 0.25, MZ), CY = 0.1, TOP = 0.78;
    mk(g, box(0.2, 0.016, 0.16), M.iron, 0, 0.008, 0); mk(g, cyl(0.006, 0.006, 0.82, 14), M.chrome, -0.07, 0.42, -0.04);
    [0.2, 0.6].forEach(function (y) { mk(g, box(0.08, 0.012, 0.014), M.blackPlastic, -0.035, y, -0.02); });
    var tube = mk(g, new T.CylinderGeometry(0.012, 0.012, TOP - 0.03, 24, 1, true), M.glass, 0, (TOP + 0.03) / 2, 0);
    var rl = S.ruler(0.7, { width: 0.018 }); rl.position.set(MX - 0.25 + 0.022, CY, MZ - 0.012);
    mk(g, cyl(0.022, 0.022, 0.014, 32), M.bakelite, 0, CY, 0); mk(g, new T.TorusGeometry(0.021, 0.006, 12, 36), COPPER, 0, CY, 0).rotation.x = PI / 2;
    mk(g, box(0.07, 0.02, 0.07), col(0x4f5a66, 0.9), 0, 0.026, 0);                                  // foam pad
    var mag = new T.Group(); g.add(mag); mk(mag, cyl(0.005, 0.005, 0.005, 16), M.red, 0, 0.0025, 0); mk(mag, cyl(0.005, 0.005, 0.005, 16), M.chrome, 0, -0.0025, 0);
    S.contact(0.26, 0.22, MX - 0.25, MZ, 0.55);
    var ard = grp(MX + 0.02, MZ + 0.12); mk(ard, box(0.07, 0.003, 0.055), col(0x0f6b6b, 0.5), 0, 0.006, 0); mk(ard, box(0.012, 0.011, 0.016), M.alu, -0.03, 0.013, 0.012); mk(ard, box(0.01, 0.008, 0.035), M.black, 0.022, 0.011, 0);
    mk(ard, box(0.016, 0.004, 0.008), M.black, 0, 0.0095, -0.01); flat(ard, 'ARDUINO UNO', 0.045, 0, 0.0078, 0.02, '#e8fffb'); S.contact(0.1, 0.08, MX + 0.02, MZ + 0.12, 0.45);
    var sc = scope(MX + 0.34, MZ - 0.04, 'SERIAL PLOTTER · 5 kHz'); var btn = mk(ard, cyl(0.003, 0.003, 0.004, 12), M.red, 0.022, 0.011, -0.022);
    lead([[MX - 0.23, CY, MZ + 0.01], [MX - 0.1, 0.02, MZ + 0.1], [MX, 0.012, MZ + 0.12]], 'red'); lead([[MX + 0.05, 0.012, MZ + 0.12], [MX + 0.14, 0.02, MZ + 0.1], [MX + 0.24, 0.05, MZ + 0.06]], 'black');
    A.name = 'Guide tube, pick-up coil and Arduino'; A.info = 'A coil of ' + Math.round(p.N) + ' turns, mean radius ' + rnd(p.a * 100, 1) + ' cm, round a clear tube. The Arduino samples its emf (biased to mid-scale) 5000 times a second.';
    A.knob = mag; A.key = btn; A.sw = btn; A.view = [[MX + 0.05, 0.62, 0.62], [MX + 0.02, 0.22, MZ]];
    var shown = null, lastKey = '';
    function hold(h) { mag.position.set(0, CY + h, 0); } hold(p.h);
    function plot(q) { sc.draw(function (c, w, h, grid) { grid(c, w, h, st.on ? (q ? 'emf, 0.5 V/div' : 'waiting for a drop') : 'off'); c.strokeStyle = 'rgba(80,220,120,.5)'; c.lineWidth = 2; c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.stroke();
      if (!q || !st.on) return; var tc = Math.sqrt(2 * q.h / q.g), span = 8 * q.a / Math.sqrt(2 * q.g * q.h), pts = [], i, t;
      for (i = 0; i <= 500; i++) { t = tc - span + 2 * span * i / 500; pts.push([i / 500 * w, h / 2 - KN.emf(q, t) / 2.0 * h * 0.5]); } trace(c, pts); }); }
    A.tick = function () { if (!st.busyRead) hold(st.vals.h); var key = st.on + '|' + (shown ? shown.h : 0); if (key !== lastKey) { lastKey = key; plot(shown); } };
    PLAN = {
      setupTitle: 'Connect the coil and start the plotter', connect: 'Connect the coil to the Arduino',
      parts: null, controls: [[{ key: 'h', label: 'Drop height above the coil', min: 0.15, max: 0.6, step: 0.05, unit: 'm', digits: 2, def: 0.4 }]], act: ['Release the magnet'],
      take: function (part, v) { var q = assign(p, { h: v.h }), m = KN.measure(q), lsb = 5 / 1024, row = { h: rnd(v.h, 2), pk1: Math.round(m.pk1 / lsb) * lsb, pk2: Math.round(m.pk2 / lsb) * lsb };
        if (Math.abs(row.pk2) > 2.45) return { err: 'The pulse would clip the ADC (2.5 V either side of mid-scale). Drop from a lower height.' };
        return { row: row, say: 'First pulse ' + row.pk1.toFixed(3) + ' V, second pulse ' + row.pk2.toFixed(3) + ' V: opposite signs, the second one taller.',
          anim: function () { return S.tween(450, function (k) { hold(v.h - (v.h + 0.07) * k * k); }).then(function () { shown = q; hold(-0.07); return S.wait(500); }); }, after: function () { shown = q; } }; },
      cols: [{ label: 'h (cm)', get: function (r) { return (r.h * 100).toFixed(0); } }, { label: 'first peak (V)', get: function (r) { return r.pk1.toFixed(3); } }, { label: 'second peak (V)', get: function (r) { return r.pk2.toFixed(3); } },
        { label: 'v = √(2gh) (m/s)', get: function (r) { return Math.sqrt(2 * p.g * r.h).toFixed(3); } }, { label: 'mean |peak| (V)', get: function (r) { return pk(r).toFixed(3); } }],
      ok: function (rows) { return rows.length >= 4; }, needText: 'Drop the magnet from at least four heights.',
      auto: [0.2, 0.3, 0.4, 0.5, 0.6].map(function (h) { return [0, { h: h }]; }),
      result: function (rows) { if (rows.length < 4) return null;
        return { label: 'Dipole moment of the magnet', value: mean(rows.map(function (r) { return pk(r) * p.a * p.a * 25 * Math.sqrt(5) / (24 * p.N * 4e-7 * PI * Math.sqrt(2 * p.g * r.h)); })), unit: 'A m²', digits: 3, truth: p.m,
          note: 'm = ε_peak a² / (0.4293 μ₀ N v). The two pulses of every drop have opposite signs (Lenz\'s law), and the peak grows in proportion to the speed v (Faraday\'s law): ' +
            rnd(pk(rows[0]) / Math.sqrt(2 * p.g * rows[0].h), 3) + ' V per m/s at the first height and ' + rnd(pk(rows[rows.length - 1]) / Math.sqrt(2 * p.g * rows[rows.length - 1].h), 3) + ' at the last.' }; },
      graph: { x: function (r) { return Math.sqrt(2 * p.g * r.h); }, y: pk, xlabel: 'speed at the coil v (m/s)', ylabel: 'mean peak emf (V)' },
      tol: 0.03, formula: 'ε_peak = 0.4293 μ₀ N m v / a²,   v = √(2 g h)', formulaNote: 'the peak comes when the magnet is a/2 from the plane of the coil',
      live: function () { return 'Magnet held ' + (st.vals.h * 100).toFixed(0) + ' cm above the coil'; }
    };
    function pk(r) { return (Math.abs(r.pk1) + Math.abs(r.pk2)) / 2; }
  })();

  /* ================================================================ galvanometer into a meter */
  if (KNAME === 'w7_gconv') (function () {
    var AM = p.mode >= 0.5, N = Math.round(p.n), RANGE = AM ? p.Ir : p.Vr;
    var gm = S.meter({ pos: [MX - 0.05, 0, MZ], min: -N, max: N, zeroCentre: true, unit: 'G', symbol: 'G', caption: N + ' - 0 - ' + N + ' divisions', ticks: 6 });
    var rb = S.resistanceBox([MX - 0.32, 0, MZ - 0.05]), sb = S.resistanceBox([MX - 0.32, 0, MZ + 0.12]);
    var l1 = S.label('HIGH BOX R', { w: 0.07, ratio: 0.2, color: '#f0e6c8' }); l1.rotation.x = -PI / 2; l1.position.set(MX - 0.32, 0.054, MZ - 0.08); S.scene.add(l1);
    var l2 = S.label('SHUNT BOX S′', { w: 0.07, ratio: 0.2, color: '#f0e6c8' }); l2.rotation.x = -PI / 2; l2.position.set(MX - 0.32, 0.054, MZ + 0.09); S.scene.add(l2);
    var dR = dmm(MX - 0.58, MZ - 0.05, 'R (Ω)', 0.3), dS = dmm(MX - 0.58, MZ + 0.12, 'S′ (Ω)', 0.3);
    var cell = S.cell([MX - 0.1, 0, MZ - 0.2], { text: '2 V' }), key = S.plugKey([MX + 0.08, 0, MZ - 0.2]);
    var std = S.meter({ pos: [MX + 0.25, 0, MZ], min: 0, max: RANGE, unit: AM ? 'A' : 'V', symbol: AM ? 'A' : 'V', caption: 'standard meter', ticks: 6 });
    var conv = grp(MX + 0.1, MZ + 0.17); mk(conv, box(0.12, 0.012, 0.06), M.bakelite, 0, 0.006, 0);
    if (AM) mk(conv, box(0.08, 0.004, 0.012), col(0xb9a06a, 0.3, 0.8), 0, 0.02, 0); else coilOn(conv, 0.012, 0.05, 0, 0.026, 0, GREENW, 'x');
    post(conv, -0.05, 0.012, 0, true); post(conv, 0.05, 0.012, 0, false); flat(conv, AM ? 'SHUNT' : 'SERIES RESISTANCE', 0.1, 0, 0.0125, 0.022); S.contact(0.16, 0.1, MX + 0.1, MZ + 0.17, 0.45);
    var src = caseBox(MX + 0.5, MZ, 0.18, 0.1, 0.12, DARK, AM ? 'CURRENT SOURCE' : 'VOLTAGE SOURCE', -0.3), dX = lcd(src, -0.03, 0.062, 0.09, 0.034), kX = knob(src, 0.06, 0.062, 0.012);
    lead([[MX - 0.09, 0.03, MZ - 0.2], [MX - 0.2, 0.03, MZ - 0.12], [MX - 0.27, 0.06, MZ - 0.05]], 'red');
    lead([[MX - 0.085, 0.07, MZ - 0.03], [MX - 0.15, 0.04, MZ + 0.02], [MX - 0.25, 0.06, MZ - 0.03]], 'black');
    A.name = 'Galvanometer, resistance boxes and a standard meter'; A.info = 'A ' + N + '-0-' + N + ' moving-coil galvanometer. The high box and the shunt box find its resistance; the ' + (AM ? 'shunt' : 'series resistance') + ' on the small board converts it.';
    A.knob = rb; A.key = key.userData.plug; A.sw = key.userData.plug; A.onSwitch = function () { key.set(true); };
    var cur = { th: 0, S: 0, x: 0 };
    function est(rows) { var a = rows.filter(function (r) { return r.part === 0; }); if (!a.length) return null;
      var G = mean(a.map(function (r) { return r.R * r.S / (r.R - r.S); })), k = mean(a.map(function (r) { return p.E / ((r.R + G) * r.th); })), igf = N * k;
      return { G: G, k: k, igf: igf, need: AM ? igf * G / (RANGE - igf) : RANGE / igf - G }; }
    A.tick = function () { gm.set(st.on ? cur.th : 0); std.set(st.on && st.part === 1 ? cur.x : 0); rb.show(Math.round(st.vals.R / 100)); sb.show(Math.round(cur.S));
      dR.set(String(st.vals.R), 'Ω'); dS.set(cur.S ? cur.S.toFixed(1) : '----', 'Ω'); dX.set(st.part === 1 && st.on ? st.vals.x.toFixed(2) : '----', AM ? 'A' : 'V'); conv.visible = st.part === 1; };
    PLAN = {
      parts: ['Half deflection (find G and k)', 'Convert and calibrate'],
      controls: [[{ key: 'R', label: 'High resistance box R', min: 3500, max: 8000, step: 500, unit: 'Ω', digits: 0, def: 4000 }],
        [AM ? { key: 'x', label: 'Test current', min: 0.05, max: 0.3, step: 0.05, unit: 'A', digits: 2, def: 0.2 } : { key: 'x', label: 'Test voltage', min: 0.5, max: 3.0, step: 0.5, unit: 'V', digits: 1, def: 2.0 }]],
      act: ['Read the deflection, then halve it with the shunt', 'Compare with the standard meter'],
      take: function (part, v) { var m, e, q, th, a = cur.th;
        if (part === 0) { m = KN.measure(assign(p, { R: v.R })); if (m.th0 > N) return { err: 'The deflection goes off the scale. Put more resistance in the high box.' };
          var row = { part: 0, R: v.R, th: rnd(m.th0, 1), S: rnd(m.Shalf, 1) };
          return { row: row, say: 'Deflection ' + row.th.toFixed(1) + ' divisions; a shunt of ' + row.S.toFixed(1) + ' Ω halves it.',
            anim: function () { return S.tween(500, function (k) { cur.th = a + (m.th0 - a) * k; }).then(function () { return S.hand.tap(sb); }).then(function () { cur.S = row.S; return S.tween(500, function (k) { cur.th = m.th0 * (1 - k / 2); }); }); },
            after: function () { cur.S = row.S; cur.th = m.th0 / 2; } }; }
        e = est(S.rows); if (!e) return { err: 'Find the galvanometer\'s resistance and figure of merit first (part 1).' };
        q = assign(p, { stage: 2, Rs: e.need, Sh: e.need, Vt: v.x, It: v.x }); th = KN.theta(q);
        return { row: { part: 1, x: v.x, th: rnd(th, 1), read: RANGE * rnd(th, 1) / N }, say: 'Standard meter ' + v.x + (AM ? ' A' : ' V') + ': the converted meter shows ' + rnd(th, 1).toFixed(1) + ' divisions = ' + (RANGE * rnd(th, 1) / N).toFixed(AM ? 3 : 2) + (AM ? ' A.' : ' V.'),
          anim: function () { return S.tween(600, function (k) { cur.th = a + (th - a) * k; cur.x = v.x * k; }); }, after: function () { cur.th = th; cur.x = v.x; } }; },
      cols: [{ label: 'part', get: function (r) { return r.part ? 'calibrate' : 'half defl.'; } }, { label: 'R (Ω) / test', get: function (r) { return r.part ? r.x : r.R; } },
        { label: 'θ (div)', get: function (r) { return r.th.toFixed(1); } }, { label: 'S′ (Ω) / reads', get: function (r) { return r.part ? r.read.toFixed(AM ? 3 : 2) : r.S.toFixed(1); } }],
      ok: function (rows) { return rows.filter(function (r) { return r.part === 0; }).length >= 2 && rows.filter(function (r) { return r.part === 1; }).length >= 3; },
      needText: 'Take two half-deflection readings, then three calibration points.',
      auto: [[0, { R: 4000 }], [0, { R: 6000 }]].concat((AM ? [0.1, 0.2, 0.3] : [1.0, 2.0, 3.0]).map(function (x) { return [1, { x: x }]; })),
      result: function (rows) { var e = est(rows); if (!this.ok(rows) || !e) return null; var worst = 0;
        rows.forEach(function (r) { if (r.part === 1) worst = Math.max(worst, Math.abs(r.read - r.x)); });
        return { label: AM ? 'Shunt for a 0 – ' + RANGE + ' A ammeter' : 'Series resistance for a 0 – ' + RANGE + ' V voltmeter', value: e.need, unit: 'Ω', digits: AM ? 4 : 0, truth: HK.TEXTBOOK.w7_gconv_need(p),
          note: 'Half deflection gives G = ' + rnd(e.G, 1) + ' Ω and a figure of merit of ' + rnd(e.k * 1e6, 2) + ' µA per division, so full scale needs ' + rnd(e.igf * 1e6, 0) + ' µA. Against the standard meter the converted one is never more than ' +
            worst.toFixed(AM ? 3 : 2) + (AM ? ' A' : ' V') + ' out.' }; },
      tol: 0.02, formula: AM ? 'S = Ig G / (I − Ig),   G = R S′ / (R − S′)' : 'Rs = V / Ig − G,   G = R S′ / (R − S′)', formulaNote: 'Ig = n k, the full-scale current; k = E / ((R + G) θ)',
      live: function () { return 'Galvanometer at ' + rnd(cur.th, 1).toFixed(1) + ' divisions'; }
    };
  })();

  /* ================================================================ regulated source */
  if (KNAME === 'w7_srcreg') (function () {
    var CC = p.mode >= 0.5;
    var src = caseBox(MX - 0.3, MZ, 0.26, 0.13, 0.16, DARK, CC ? 'CONSTANT-CURRENT SOURCE' : 'CONSTANT-VOLTAGE SOURCE'), dS = lcd(src, -0.04, 0.085, 0.12, 0.04), sw = toggle(src, 0.09, 0.09);
    post(src, 0.06, 0.0, 0.1, true); post(src, 0.095, 0.0, 0.1, false);
    var dec = caseBox(MX + 0.08, MZ, 0.22, 0.09, 0.14, col(0x5b4630, 0.6), 'DECADE LOAD BOX'), dL = lcd(dec, -0.03, 0.058, 0.1, 0.034), kL = knob(dec, 0.07, 0.058, 0.014);
    var mv = dmm(MX - 0.12, MZ + 0.25, 'VOLTMETER'), mi = dmm(MX + 0.1, MZ + 0.25, 'AMMETER');
    lead([[MX - 0.24, 0.02, MZ + 0.1], [MX - 0.1, 0.02, MZ + 0.14], [MX + 0.02, 0.03, MZ + 0.08]], 'red'); lead([[MX - 0.2, 0.02, MZ + 0.1], [MX - 0.16, 0.02, MZ + 0.18], [MX - 0.12, 0.04, MZ + 0.22]], 'black');
    A.name = (CC ? 'Constant-current' : 'Constant-voltage') + ' source with a decade load'; A.info = 'The source under test, a decade resistance box as its load, and two digital meters: volts across the load and amperes through it.' + (SAMPLE ? ' ' + SAMPLE + '.' : '');
    A.knob = kL; A.key = mv.g; A.sw = sw;
    function rd(RLv) { var q = KN.point(p, RLv); return CC ? { V: rnd(q[0], 3), I: rnd(q[1] * 1000, 3) } : { V: rnd(q[0], 3), I: rnd(q[1], 3) }; }
    A.tick = function () { var r = rd(st.vals.RL); dS.set(st.on ? (CC ? (p.I0 * 1000).toFixed(1) : p.V0.toFixed(1)) : '----', CC ? 'mA set' : 'V set'); dL.set(String(st.vals.RL), 'Ω');
      mv.set(st.on ? r.V.toFixed(3) : '----', 'V'); mi.set(st.on ? r.I.toFixed(3) : '----', CC ? 'mA' : 'A'); kL.rotation.z = -st.vals.RL / (CC ? 300 : 15); };
    function reg(rows) { var top = 0; rows.forEach(function (r) { top = Math.max(top, CC ? r.V : r.I); }); return rows.filter(function (r) { return (CC ? r.V : r.I) <= 0.9 * top; }); }
    PLAN = {
      parts: null, controls: [[CC ? { key: 'RL', label: 'Decade load box', min: 100, max: 2000, step: 100, unit: 'Ω', digits: 0, def: 400 } : { key: 'RL', label: 'Decade load box', min: 3, max: 90, step: 1, unit: 'Ω', digits: 0, def: 30 }]],
      act: ['Read the voltmeter and the ammeter'],
      take: function (part, v) { var r = rd(v.RL); r.RL = v.RL; return { row: r, say: 'With ' + v.RL + ' Ω: ' + r.V.toFixed(3) + ' V and ' + r.I.toFixed(3) + (CC ? ' mA.' : ' A.') }; },
      cols: [{ label: 'load (Ω)', get: function (r) { return r.RL; } }, { label: 'V (V)', get: function (r) { return r.V.toFixed(3); } }, { label: CC ? 'I (mA)' : 'I (A)', get: function (r) { return r.I.toFixed(3); } }],
      ok: function (rows) { return rows.length >= 6 && reg(rows).length >= 4; }, needText: 'Take at least six loads, going on until the source stops regulating.',
      auto: (CC ? [100, 200, 400, 600, 800, 1000, 1500, 2000] : [90, 45, 30, 18, 12, 10, 6, 3]).map(function (r) { return [0, { RL: r }]; }),
      result: function (rows) { var g = reg(rows); if (!this.ok(rows)) return null; var s, v0, lim;
        if (CC) { s = slope(g.map(function (r) { return [r.V, r.I / 1000]; })); lim = 0; rows.forEach(function (r) { lim = Math.max(lim, r.V); });
          return { label: 'Output resistance of the source', value: -1 / s / 1000, unit: 'kΩ', digits: 1, truth: p.Ro / 1000,
            note: 'From the slope of I against V in the regulating region, Ro = −ΔV/ΔI. The current changes by ' + rnd(-s * 1e6, 1) + ' µA for every volt across the load. Regulation ends at the compliance voltage, about ' + rnd(lim, 1) + ' V, where the current collapses.' }; }
        s = slope(g.map(function (r) { return [r.I, r.V]; })); v0 = mean(g.map(function (r) { return r.V - s * r.I; })); lim = 0; rows.forEach(function (r) { lim = Math.max(lim, r.I); });
        return { label: 'Output resistance of the source', value: -s, unit: 'Ω', digits: 3, truth: p.ro,
          note: 'From the slope of V against I in the regulating region, ro = −ΔV/ΔI. The no-load voltage is ' + rnd(v0, 3) + ' V and the load regulation up to ' + rnd(g[g.length - 1].I, 2) + ' A is ' + rnd(-s * g[g.length - 1].I / v0 * 100, 2) + ' %. The current limit acts at about ' + rnd(lim, 2) + ' A, where the voltage collapses.' }; },
      graph: CC ? { x: function (r) { return r.V; }, y: function (r) { return r.I; }, xlabel: 'voltage across the load (V)', ylabel: 'current (mA)' } : { x: function (r) { return r.I; }, y: function (r) { return r.V; }, xlabel: 'load current (A)', ylabel: 'terminal voltage (V)' },
      tol: 0.03, formula: CC ? 'I = I₀ − V / Ro' : 'V = V₀ − I ro', formulaNote: 'the output resistance is minus the slope of the characteristic in the regulating region',
      live: function () { return 'Load ' + st.vals.RL + ' Ω'; }
    };
  })();

  /* ================================================================ magnetometers */
  if (KNAME === 'w7_magneto') (function () {
    var g = grp(MX - 0.15, MZ + 0.02), arm = new T.Group(); g.add(arm);
    mk(arm, box(0.74, 0.014, 0.05), M.wood, 0, 0.007, 0);
    var sc1 = S.ruler(0.3, { width: 0.02 }); S.scene.remove(sc1); sc1.rotation.set(-PI / 2, 0, -PI / 2); sc1.position.set(0.06, 0.0142, 0.012); arm.add(sc1);
    var sc2 = S.ruler(0.3, { width: 0.02 }); S.scene.remove(sc2); sc2.rotation.set(-PI / 2, 0, PI / 2); sc2.position.set(-0.06, 0.0142, -0.012); arm.add(sc2);
    mk(g, cyl(0.055, 0.055, 0.03, 40), M.brass, 0, 0.029, 0);
    var dialTex = S.canvasTex(512, 512, function (c) { c.fillStyle = '#f4f1e6'; c.beginPath(); c.arc(256, 256, 250, 0, 7); c.fill(); c.strokeStyle = '#1b1b1b'; c.fillStyle = '#1b1b1b'; c.textAlign = 'center'; c.font = '600 26px "Public Sans", sans-serif';
      for (var i = 0; i < 360; i += 2) { var a = i * PI / 180, big = i % 10 === 0; c.lineWidth = big ? 3 : 1.2; c.beginPath(); c.moveTo(256 + Math.cos(a) * 246, 256 + Math.sin(a) * 246); c.lineTo(256 + Math.cos(a) * (big ? 218 : 232), 256 + Math.sin(a) * (big ? 218 : 232)); c.stroke();
        if (i % 30 === 0) { var q = i % 180; c.fillText(String(q > 90 ? 180 - q : q), 256 + Math.cos(a) * 196, 256 + Math.sin(a) * 196 + 9); } } });
    var dial = S.mesh(cyl(0.052, 0.052, 0.002, 40), [M.brass, new T.MeshStandardMaterial({ map: dialTex, roughness: 0.6 }), M.brass]); dial.position.y = 0.045; g.add(dial);
    var ndl = new T.Group(); ndl.position.y = 0.049; g.add(ndl); mk(ndl, box(0.016, 0.002, 0.004), col(0x2c5fb4, 0.4), 0, 0, 0); mk(ndl, box(0.0012, 0.001, 0.096), M.alu, 0, 0.001, 0);
    mk(g, cyl(0.054, 0.054, 0.002, 40), M.glass, 0, 0.056, 0); S.contact(0.8, 0.2, MX - 0.15, MZ + 0.02, 0.5);
    var mag = new T.Group(); g.add(mag); mk(mag, box(0.05, 0.012, 0.014), M.red, 0.025, 0, 0); mk(mag, box(0.05, 0.012, 0.014), col(0x2c5fb4, 0.4), -0.025, 0, 0);
    var vb = grp(0.62, MZ + 0.05); mk(vb, box(0.22, 0.012, 0.16), M.darkWood, 0, 0.006, 0); [[-0.105, 0], [0.105, 0], [0, -0.075]].forEach(function (q, i) { mk(vb, box(i < 2 ? 0.006 : 0.21, 0.13, i < 2 ? 0.15 : 0.006), M.wood, q[0], 0.077, q[1]); });
    mk(vb, box(0.22, 0.008, 0.16), M.wood, 0, 0.146, 0); mk(vb, cyl(0.008, 0.008, 0.12, 14), M.glass, 0, 0.21, 0); mk(vb, box(0.21, 0.13, 0.003), M.glass, 0, 0.077, 0.077);
    mk(vb, cyl(0.0006, 0.0006, 0.2, 6), M.thread, 0, 0.16, 0);
    var vmag = new T.Group(); vmag.position.y = 0.06; vb.add(vmag); mk(vmag, box(0.05, 0.012, 0.014), M.red, 0.025, 0, 0); mk(vmag, box(0.05, 0.012, 0.014), col(0x2c5fb4, 0.4), -0.025, 0, 0);
    plate(vb, 'VIBRATION MAGNETOMETER', 0.14, 0, 0.02, 0.0815, '#2b323d'); S.contact(0.28, 0.22, 0.62, MZ + 0.05, 0.5);
    var sw_ = S.stopwatch([0.62, 0.011, MZ + 0.24], [-PI / 2, 0, 0]);
    A.name = 'Deflection and vibration magnetometers'; A.info = 'The compass box sits at the centre of a graduated arm; the bar magnet is placed on the arm at a measured distance. The same magnet then swings in the vibration magnetometer. Moment of inertia of the magnet: ' + (p.Im * 1e5).toFixed(2) + ' × 10⁻⁵ kg m²; magnetic length 2l = ' + rnd(p.l * 200, 1) + ' cm.';
    A.knob = mag; A.key = sw_.start; A.sw = null; A.view = [[MX + 0.1, 0.55, 0.5], [MX + 0.1, 0.05, MZ]];
    var cur = { th: 0, sw: 0 }, clock = 0;
    function seat() { var b = st.part === 1, d = b ? st.vals.dB : st.vals.dA; arm.rotation.y = b ? PI / 2 : 0; mag.visible = st.part < 2; vmag.visible = st.part === 2;
      if (b) { mag.position.set(0, 0.02, -d); mag.rotation.y = 0; } else { mag.position.set(d, 0.02, 0); mag.rotation.y = 0; } }
    function defl(part, d) { return KN.view({ t: 0 }, assign(p, { pos: part, d: d })).theta; }
    A.tick = function (dt) { seat(); clock += dt; var tgt = st.part < 2 ? defl(st.part, st.part ? st.vals.dB : st.vals.dA) : 0; cur.th += (tgt - cur.th) * Math.min(1, dt * 5); ndl.rotation.y = -cur.th * PI / 180;
      vmag.rotation.y = st.part === 2 ? cur.sw * Math.sin(clock * 3) : 0; };
    PLAN = {
      parts: ['Tan A (magnet end-on)', 'Tan B (magnet broadside-on)', 'Vibration magnetometer'], noSwitch: true,
      setupTitle: 'Set the magnetometer', connect: 'Set the arms east-west and the pointer to 0 – 0', connectSay: 'The arms lie east-west and the pointer reads 0 – 0 with no magnet near.',
      controls: [[{ key: 'dA', label: 'Distance d of the magnet', min: 0.14, max: 0.22, step: 0.01, unit: 'm', digits: 2, def: 0.18 }], [{ key: 'dB', label: 'Distance d of the magnet', min: 0.10, max: 0.16, step: 0.01, unit: 'm', digits: 2, def: 0.13 }], []],
      act: ['Read the deflection', 'Read the deflection', 'Time ten swings'],
      take: function (part, v) { var th, t;
        if (part < 2) { th = rnd(defl(part, part ? v.dB : v.dA), 1); return { row: { part: part, d: rnd(part ? v.dB : v.dA, 2), th: th }, say: 'Mean deflection ' + th.toFixed(1) + '° (both ends of the pointer, magnet reversed and on both arms).' }; }
        t = rnd(10 * KN.period(p), 2);
        return { row: { part: 2, t10: t }, say: 'Ten swings take ' + t.toFixed(2) + ' s.', anim: function () { cur.sw = 0.09; return S.wait(1200).then(function () { cur.sw = 0; }); } }; },
      cols: [{ label: 'part', get: function (r) { return ['Tan A', 'Tan B', 'vibration'][r.part]; } }, { label: 'd (cm)', get: function (r) { return r.part < 2 ? (r.d * 100).toFixed(0) : '—'; } },
        { label: 'θ (°) / 10T (s)', get: function (r) { return r.part < 2 ? r.th.toFixed(1) : r.t10.toFixed(2); } }, { label: 'M/H or MH (SI)', get: function (r) { return r.part < 2 ? mh(r).toFixed(0) : (MH(r) * 1e5).toFixed(3) + 'e-5'; } }],
      ok: function (rows) { return rows.some(function (r) { return r.part === 0; }) && rows.some(function (r) { return r.part === 1; }) && rows.filter(function (r) { return r.part < 2; }).length >= 4 && rows.some(function (r) { return r.part === 2; }); },
      needText: 'Take two distances in Tan A, two in Tan B, and time the swings once.',
      auto: [[0, { dA: 0.15 }], [0, { dA: 0.18 }], [1, { dB: 0.11 }], [1, { dB: 0.14 }], [2, {}]],
      result: function (rows) { if (!this.ok(rows)) return null;
        var ratio = mean(rows.filter(function (r) { return r.part < 2; }).map(mh)), prod = mean(rows.filter(function (r) { return r.part === 2; }).map(MH));
        return { label: 'Earth\'s horizontal field H', value: Math.sqrt(prod / ratio) * 1e6, unit: 'µT', digits: 1, truth: p.H * 1e6,
          note: 'M/H = ' + rnd(ratio, 0) + ' A m²/T from the deflections and M H = ' + (prod * 1e5).toFixed(3) + ' × 10⁻⁵ N m from the swings, so the magnetic moment of the magnet is M = ' + rnd(Math.sqrt(prod * ratio), 3) + ' A m².' }; },
      tol: 0.02, formula: 'tan θ = B / H,   T = 2π √(I / (M H))', formulaNote: 'Tan A: B = (μ₀/4π) 2Md/(d² − l²)²;  Tan B: B = (μ₀/4π) M/(d² + l²)^(3/2)',
      live: function () { return st.part < 2 ? 'Needle at ' + rnd(cur.th, 1).toFixed(1) + '°' : 'Magnet in the vibration box'; }
    };
    function mh(r) { var d = r.d, l = p.l, t = Math.tan(r.th * PI / 180); return r.part ? 1e7 * Math.pow(d * d + l * l, 1.5) * t : 1e7 * Math.pow(d * d - l * l, 2) / (2 * d) * t; }
    function MH(r) { var tt = r.t10 / 10; return 4 * PI * PI * p.Im / (tt * tt); }
  })();

  /* ================================================================ B-H loop of a ring */
  if (KNAME === 'msc_loop') (function () {
    var HC = p.Hc, LO = HC * 0.3, HI = HC * 8, KA = HC >= 1000, HS = KA ? 1e-3 : 1, HU = KA ? 'kA/m' : 'A/m', HD = KA ? 2 : 0;
    var NAME = SAMPLE || 'Soft-iron ring';
    var g = grp(MX - 0.2, MZ + 0.02); mk(g, box(0.26, 0.012, 0.18), M.bakelite, 0, 0.006, 0);
    var ring = S.mesh(new T.TorusGeometry(0.045, 0.014, 16, 48), col(KA ? 0x5a5d63 : 0x7b7f86, 0.3, 0.7)); ring.rotation.x = PI / 2; ring.position.set(-0.04, 0.03, 0); g.add(ring);
    for (var i = 0; i < 30; i++) { var th = i / 30 * PI * 2, w = S.mesh(new T.TorusGeometry(0.0148, 0.0009, 6, 14), i % 5 === 0 ? GREENW : COPPER); w.position.set(-0.04 + Math.cos(th) * 0.045, 0.03, Math.sin(th) * 0.045); w.rotation.set(0, -th, 0); g.add(w); }
    mk(g, box(0.04, 0.016, 0.014), col(0xe2c25f, 0.5), 0.07, 0.02, -0.05); mk(g, cyl(0.01, 0.01, 0.028, 20), col(0x2a4f9c, 0.4), 0.08, 0.026, 0.03); mk(g, box(0.03, 0.012, 0.012), col(0xe2c25f, 0.5), 0.07, 0.018, 0.06);
    flat(g, 'R     INTEGRATOR  R C', 0.12, 0.07, 0.0125, 0.0); flat(g, NAME.toUpperCase().slice(0, 22), 0.11, -0.04, 0.0125, 0.075); S.contact(0.32, 0.24, MX - 0.2, MZ + 0.02, 0.5);
    var sup = caseBox(MX - 0.5, MZ, 0.2, 0.1, 0.12, DARK, 'AC SUPPLY · 50 Hz'), dH = lcd(sup, -0.03, 0.062, 0.1, 0.034), kH = knob(sup, 0.065, 0.062, 0.013), sw = toggle(sup, 0.065, 0.03);
    var sc = scope(MX + 0.28, MZ, 'OSCILLOSCOPE · X-Y');
    lead([[MX - 0.42, 0.06, MZ + 0.06], [MX - 0.34, 0.03, MZ + 0.12], [MX - 0.27, 0.03, MZ + 0.06]], 'red'); lead([[MX - 0.12, 0.03, MZ + 0.08], [MX + 0.02, 0.03, MZ + 0.14], [MX + 0.16, 0.06, MZ + 0.1]], 'yellow');
    A.name = NAME + ' with two windings'; A.info = 'The magnetising winding carries the 50 Hz current through a sensing resistor (X axis: H); the search winding feeds an R-C integrator (Y axis: B).';
    A.knob = kH; A.key = sc.knob; A.sw = sw; A.view = [[MX + 0.15, 0.5, 0.5], [MX + 0.12, 0.08, MZ]];
    function tr(h0) { var q = assign(p, { H0: h0 }), n = 400, hs = [], up = [], dn = [], j, h; for (j = 0; j <= n; j++) { h = -h0 + 2 * h0 * j / n; hs.push(h); up.push(KN.m(h, 1, q)); dn.push(KN.m(h, -1, q)); } return { h0: h0, hs: hs, up: up, dn: dn }; }
    function an(t) { var n = t.hs.length - 1, j, hc = 0, hcA = 0, area = 0;
      for (j = 0; j < n; j++) if (t.dn[j] < 0 && t.dn[j + 1] >= 0) { hc = -(t.hs[j] + (t.hs[j + 1] - t.hs[j]) * t.dn[j] / (t.dn[j] - t.dn[j + 1])); break; }
      for (j = 0; j < n; j++) if (t.up[j] < 0 && t.up[j + 1] >= 0) { hcA = t.hs[j] + (t.hs[j + 1] - t.hs[j]) * (0 - t.up[j]) / (t.up[j + 1] - t.up[j]); break; }
      for (j = 0; j < n; j++) area += 0.5 * ((t.dn[j] - t.up[j]) + (t.dn[j + 1] - t.up[j + 1])) * (t.hs[j + 1] - t.hs[j]);
      return { Hc: (hc + hcA) / 2, Br: t.dn[Math.round(n / 2)], Bs: t.up[n], area: area }; }
    var lastKey = '';
    A.tick = function () { dH.set(st.on ? (st.vals.H0 * HS).toFixed(HD) : '----', HU); kH.rotation.z = -st.vals.H0 / HI * 4; var key = st.on + '|' + st.vals.H0; if (key === lastKey) return; lastKey = key; var t = tr(st.vals.H0);
      sc.draw(function (c, w, h, grid) { grid(c, w, h, st.on ? 'X: H   Y: B' : 'off'); c.strokeStyle = 'rgba(80,220,120,.5)'; c.lineWidth = 2; c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.moveTo(w / 2, 0); c.lineTo(w / 2, h); c.stroke(); if (!st.on) return;
        var hx = Math.max(t.h0, HC * 1.2) * 1.15, my = p.Ms * 1.2; trace(c, t.hs.map(function (hh, j) { return [w / 2 + hh / hx * (w / 2 - 20), h / 2 - t.up[j] / my * (h / 2 - 20)]; })); trace(c, t.hs.map(function (hh, j) { return [w / 2 + hh / hx * (w / 2 - 20), h / 2 - t.dn[j] / my * (h / 2 - 20)]; })); }); };
    PLAN = {
      parts: null, controls: [[{ key: 'H0', label: 'Peak magnetising field', min: rnd(LO * HS, HD + 1), max: rnd(HI * HS, HD + 1), step: rnd((HI - LO) * HS / 80, HD + 2), unit: HU, digits: HD + 1, def: rnd(HC * 4 * HS, HD + 1), k: 1 / HS }]],
      act: ['Capture the loop'],
      take: function (part, v) { var a = an(tr(v.H0)); return { row: { h0: v.H0, Hc: a.Hc, Br: a.Br, Bs: a.Bs, area: a.area }, say: 'The loop cuts the H axis at ±' + (a.Hc * HS).toFixed(HD + 1) + ' ' + HU + ' and the B axis at ±' + a.Br.toFixed(3) + ' T.' }; },
      cols: [{ label: 'drive (' + HU + ')', get: function (r) { return (r.h0 * HS).toFixed(HD); } }, { label: 'Hc (' + HU + ')', get: function (r) { return (r.Hc * HS).toFixed(HD + 1); } }, { label: 'Br (T)', get: function (r) { return r.Br.toFixed(3); } },
        { label: 'B max (T)', get: function (r) { return r.Bs.toFixed(3); } }, { label: 'area (J/m³)', get: function (r) { return r.area.toFixed(0); } }],
      ok: function (rows) { return rows.length >= 4; }, needText: 'Capture at least four loops, the largest well past the point where the loop stops growing.',
      auto: [0.5, 1, 2, 5, 7].map(function (k) { return [0, { H0: HC * k }]; }),
      result: function (rows) { if (rows.length < 4) return null; var r = rows.slice().sort(function (a, b) { return a.h0 - b.h0; }), top = r[r.length - 1], prev = r[r.length - 2];
        if (Math.abs(top.Hc - prev.Hc) > 0.03 * top.Hc) return null;
        return { label: 'Coercivity of the ring', value: top.Hc * HS, unit: HU, digits: HD + 1, truth: p.Hc * HS,
          note: 'Read from the saturated loop (drive ' + (top.h0 * HS).toFixed(HD) + ' ' + HU + '). Retentivity ' + top.Br.toFixed(2) + ' T, saturation ' + top.Bs.toFixed(2) + ' T, and the area of the loop, the hysteresis loss, is ' + sig(top.area, 3) + ' J/m³ in every cycle (' + sig(top.area * 50, 3) + ' W/m³ at 50 Hz). The smaller drives gave narrower loops that are not the material\'s own.' }; },
      graph: { x: function (r) { return r.h0 * HS; }, y: function (r) { return r.Hc * HS; }, xlabel: 'drive (' + HU + ')', ylabel: 'Hc read (' + HU + ')' },
      tol: 0.02, formula: 'loss per cycle = ∮ H dB  (the area of the loop)', formulaNote: 'coercivity: where the loop cuts the H axis; retentivity: where it cuts the B axis',
      live: function () { return 'Drive ' + (st.vals.H0 * HS).toFixed(HD) + ' ' + HU; }, sameOk: function (a, b) { return Math.abs(a.h0 - b.h0) < 1e-9 * Math.max(1, a.h0); }
    };
  })();

  if (!PLAN) throw new Error('em-ug-instruments has no plan for kernel ' + KNAME);
  (PLAN.controls || []).forEach(function (cs) { cs.forEach(function (c) { st.vals[c.key] = c.k ? c.def * c.k : c.def; }); });
  if (PLAN.noSwitch) st.on = true;

  S.addApparatus('app', (function () { var g = new T.Group(); g.position.set(A.view[1][0], 0, MZ); S.scene.add(g); return g; })(), A.name, A.info);
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading is written here, as in a real practical file.');
  var hud1 = S.hudCard('Now'), hud2 = S.hudCard('Readings');

  /* ================================================================ human actions (the same for every set-up) */
  function connect() { if (busy() || st.wired) return Promise.resolve();
    return S.hand.tap(A.knob || A.key).then(function () { st.wired = true; wires.forEach(function (w) { w.visible = true; }); S.say(PLAN.connectSay || 'The circuit is connected as in the diagram. Check every joint before switching on.'); S.render(); }); }
  function switchOn() { if (busy() || st.on) return Promise.resolve();
    if (!st.wired) { S.say('Connect the circuit first.'); return Promise.resolve(); }
    return (A.sw ? S.hand.tap(A.sw) : Promise.resolve()).then(function () { st.on = true; if (A.onSwitch) A.onSwitch(); S.click(880, 0.05); S.say('Switched on.'); S.render(); }); }
  function setVal(c, v) { var k = c.k || 1;
    if (busy()) return Promise.resolve();
    if (c.opts ? c.opts.indexOf(v) < 0 : !(v >= c.min - 1e-9 && v <= c.max + 1e-9)) { S.say(c.label + ' runs from ' + c.min + ' to ' + c.max + ' ' + c.unit + '.'); return Promise.resolve(); }
    var a = st.vals[c.key], b = v * k;
    return (A.knob ? S.hand.tap(A.knob) : Promise.resolve()).then(function () { return c.opts ? null : S.tween(450, function (q) { st.vals[c.key] = a + (b - a) * q; }); }).then(function () { st.vals[c.key] = b; S.render(); });
  }
  function take() {
    if (busy()) return Promise.resolve(null);
    if (!st.wired || !st.on) { S.say('Finish the set-up step first.'); return Promise.resolve(null); }
    var r = PLAN.take(st.part, assign(st.vals)), i;
    if (r.err) { S.say(r.err); return Promise.resolve(null); }
    for (i = 0; i < S.rows.length; i++) if (PLAN.sameOk ? PLAN.sameOk(S.rows[i], r.row) : JSON.stringify(S.rows[i]) === JSON.stringify(r.row)) { S.say('You already have this reading. Change the setting first.'); return Promise.resolve(null); }
    st.busyRead = true;
    var seq = A.key ? S.hand.tap(A.key) : Promise.resolve();
    if (r.anim) seq = seq.then(function () { return r.anim(); });
    return seq.then(function () { if (r.after) r.after(); st.busyRead = false; S.addRow(r.row); S.say(r.say); return r.row; }, function () { st.busyRead = false; return null; });
  }
  function setPart(i) { if (busy()) return; st.part = i; S.render(); }

  return {
    camera: { pos: [0.1, 1.08, 1.42], look: [0.08, 0.05, -0.3] },
    views: { bench: [[0.1, 1.08, 1.42], [0.08, 0.05, -0.3]], app: A.view, book: [[-0.46, 0.46, 0.5], [-0.5, 0.0, 0.08]] },
    theory: { principle: S.lab.theory, formula: PLAN.formula, formulaNote: PLAN.formulaNote,
      more: ['Each reading is rounded to the least count of the instrument that shows it, as on a real bench.',
        'The component values of this bench are the lab\'s own illustrative ones; the hidden value is what you measure.' + (V_.note ? ' ' + V_.note : ''),
        SAMPLE ? 'On the bench: ' + SAMPLE + '.' : 'Take more readings than the minimum: a mean of several is better than any one.'],
      precautions: S.lab.safety },
    book: { title: 'Expt. — ' + S.lab.title, lines: ['Aim: ' + S.lab.aim.slice(0, 120) + (S.lab.aim.length > 120 ? '…' : ''), PLAN.formula, PLAN.formulaNote], columns: PLAN.cols },
    graph: PLAN.graph ? { x: PLAN.graph.x, y: PLAN.graph.y, xlabel: PLAN.graph.xlabel, ylabel: PLAN.graph.ylabel, line: function () { return null; } } : undefined,
    result: function (rows) { return PLAN.result(rows); },
    tol: PLAN.tol,
    chips: ['What am I measuring here?', 'Why this formula?', 'Check my readings', 'What are the main sources of error?'],
    viva: [],
    askState: function () { return { experiment: S.lab.title, apparatus: A.name, connected: st.wired, switched_on: st.on, part: PLAN.parts ? PLAN.parts[st.part] : 'single part', settings: assign(st.vals), now: PLAN.live ? PLAN.live() : '', readings_taken: S.rows.length }; },
    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2(PLAN.setupTitle || 'Connect and switch on');
          u.p(A.info);
          u.task('1. ' + (PLAN.connect || 'Connect the circuit'), st.wired, st.wired ? 'Done' : 'Not yet done').add(u.button(st.wired ? 'Done' : (PLAN.connect || 'Connect the circuit'), function () { S.focus('app'); connect(); }, !st.wired, st.wired || S.hand.busy));
          if (!PLAN.noSwitch) u.task('2. Switch on', st.on, st.on ? 'On' : 'Off').add(u.button(st.on ? 'Switched on' : 'Switch on', function () { S.focus('app'); switchOn(); }, st.wired && !st.on, st.on || !st.wired || S.hand.busy));
          u.next('Next: take the readings', st.wired && st.on);
        }, ok: function () { return st.wired && st.on; }, auto: function () { return connect().then(switchOn); } },
      { id: 'read', title: 'Readings', view: 'app', render: function (u) {
          u.h2('Take the readings');
          if (PLAN.parts) { u.p('This experiment has ' + PLAN.parts.length + ' parts. Choose the part, then take its readings.');
            u.row.apply(u, PLAN.parts.map(function (t, i) { return u.button((i + 1) + '. ' + t, function () { setPart(i); }, st.part === i, S.hand.busy || st.busyRead); })); }
          (PLAN.controls[st.part] || []).forEach(function (c) { var k = c.k || 1, tg = { v: st.vals[c.key] / k };
            if (c.opts) { u.p(c.label + ': ' + st.vals[c.key] + ' ' + c.unit); u.row.apply(u, c.opts.map(function (o) { return u.button(o + ' ' + c.unit, function () { setVal(c, o); }, st.vals[c.key] === o, S.hand.busy || st.busyRead); })); return; }
            u.slider(c.label, c.min, c.max, c.step, function () { return tg.v; }, function (v) { tg.v = v; }, c.unit, c.digits);
            u.row(u.button('Set it', function () { setVal(c, tg.v); }, false, S.hand.busy || st.busyRead)); });
          u.row(u.button(PLAN.act[st.part], function () { take(); }, true, S.hand.busy || st.busyRead));
          if (PLAN.live) u.live(PLAN.live);
          u.h3('Observations'); u.table();
          if (!PLAN.ok(S.rows)) u.p(PLAN.needText);
          u.next('Next: the result', PLAN.ok(S.rows));
        }, ok: function () { return PLAN.ok(S.rows); },
        auto: function () { return PLAN.auto.reduce(function (pr, a) { return pr.then(function () { st.part = a[0]; var cs = PLAN.controls[a[0]] || [];
          return cs.reduce(function (q, c) { return q.then(function () { return a[1][c.key] === undefined ? null : setVal(c, a[1][c.key] / (c.k || 1)); }); }, Promise.resolve()).then(take); }); }, Promise.resolve()); } }
    ],
    tick: function (dt) { if (A.tick) A.tick(dt || 0); hud1.set(PLAN.live ? PLAN.live() : '—'); hud2.set(String(S.rows.length)); }
  };
});
