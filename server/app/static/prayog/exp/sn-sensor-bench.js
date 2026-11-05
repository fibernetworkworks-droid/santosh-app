/* Prayogshala studio rig `sn-sensor-bench`: ONE sensor bench - the sensor under test with its stimulus, a sensor supply
   with a power rocker, a control box whose dial the hand turns (and a SAMPLE switch for the unknown), and two digital
   multimeters - serving the sensor and instrument set-ups of app/prayog/labs/sn_elec.py (LVDT, strain gauge,
   capacitive level, ultrasonic ranging, temperature sensors, meter loading, meter bandwidth, photodiode, rotary pump).
   The sensor on the bench changes with the lab; the supply, the control box, the meters, the hand actions and the
   procedure do not. Physics: the lab's own kernel from packs/sn_elec.js on the lab's own params - the same numbers the
   server checks. Nothing here invents a reading; each result is worked out from the record book. Low voltages only. */
HoolaStudio.define('sn-sensor-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KK = HK.K[S.lab.kernel], p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var SAMPLE = (S.lab.variant && S.lab.variant.sample) || '';

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function fmt(v, d) { return isFinite(v) ? v.toFixed(d) : '----'; }
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }
  function span(lo, hi, st) { var out = [], v; for (v = lo; v <= hi + 1e-9; v += st) out.push(round(v, 6)); return out; }
  function ols(pts) {                         // y = m x + c through points
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, d;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    d = n * sxx - sx * sx;
    if (n < 2 || d === 0) return { m: NaN, c: NaN };
    return { m: (n * sxy - sx * sy) / d, c: (sy - (n * sxy - sx * sy) / d * sx) / n };
  }
  function origin(pts) { var a = 0, b = 0, i; for (i = 0; i < pts.length; i++) { a += pts[i][0] * pts[i][1]; b += pts[i][0] * pts[i][0]; } return b ? a / b : NaN; }
  function known(rows) { return rows.filter(function (r) { return !r.unk; }); }
  function unkRow(rows) { var i; for (i = rows.length - 1; i >= 0; i--) if (rows[i].unk) return rows[i]; return null; }
  var MEMO = {};
  function readAt(over) { var k = JSON.stringify(over || {}), q; if (MEMO[k]) return MEMO[k]; q = assign(p, over || {}); if (Object.keys(MEMO).length > 60) MEMO = {}; MEMO[k] = KK.view(KK.init(q, null), q, null); return MEMO[k]; }
  function sig3(v) { var a = Math.abs(v); if (a === 0) return 0.001; return Math.pow(10, Math.floor(Math.log(a) / Math.LN10) - 2); }   // a 3-digit gauge
  function L(text, o) {                       // printed text on a plane, shrunk to fit its width
    o = o || {};
    var w = o.w || 0.05, ratio = o.ratio || 0.25, px = o.px || 512, h = Math.round(px * ratio);
    var tex = S.canvasTex(px, h, function (x) {
      if (o.bg) { x.fillStyle = o.bg; x.fillRect(0, 0, px, h); }
      x.fillStyle = o.color || '#1b1b1b'; x.textAlign = 'center'; x.textBaseline = 'middle';
      var fs = Math.round(h * 0.62), wt = o.weight || 600;
      x.font = wt + ' ' + fs + 'px "Public Sans", sans-serif';
      var mw = x.measureText(text).width;
      if (mw > px * 0.94) { fs = Math.floor(fs * px * 0.94 / mw); x.font = wt + ' ' + fs + 'px "Public Sans", sans-serif'; }
      x.fillText(text, px / 2, h / 2);
    });
    return new T.Mesh(new T.PlaneGeometry(w, w * ratio), new T.MeshStandardMaterial({ map: tex, transparent: !o.bg, roughness: 0.6 }));
  }
  function rfmt(r) { return r >= 1e6 ? (r / 1e6) + ' MΩ' : r >= 1e3 ? (r / 1e3) + ' kΩ' : r + ' Ω'; }

  // =============================================================================================== instrument builders
  var dmmTexCache = {};
  function dmm(x, z, title, spec) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z);
    var body = S.rounded(0.15, 0.25, 0.05, 0.012, new T.MeshStandardMaterial({ color: 0xd9a21b, roughness: 0.5 }));
    body.position.y = 0.125; g.add(body);
    var lcd = S.liveTex(512, 180);
    var scr = new T.Mesh(new T.PlaneGeometry(0.118, 0.0415), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.position.set(0, 0.195, 0.0275); g.add(scr);
    var ttl = L(title, { w: 0.12, ratio: 0.12, color: '#1b1b1b' }); ttl.position.set(0, 0.235, 0.0262); g.add(ttl);
    var dial = S.mesh(new T.CylinderGeometry(0.03, 0.032, 0.012, 32), M.black); dial.rotation.x = Math.PI / 2; dial.position.set(0, 0.12, 0.031); g.add(dial);
    var mark = S.mesh(new T.BoxGeometry(0.003, 0.02, 0.002), M.white, false); mark.position.set(0, 0.138, 0.0375); g.add(mark);
    var fnl = L(spec.fn, { w: 0.07, ratio: 0.16, color: '#1b1b1b' }); fnl.position.set(0, 0.07, 0.0262); g.add(fnl);
    var red = null, blk = null;
    [[-0.035, 'black'], [0.035, 'red']].forEach(function (q) {
      var jk = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.01, 16), q[1] === 'red' ? M.red : M.black); jk.rotation.x = Math.PI / 2; jk.position.set(q[0], 0.03, 0.03); g.add(jk);
      if (q[1] === 'red') red = jk; else blk = jk;
    });
    g.userData.red = red; g.userData.black = blk;
    S.contact(0.2, 0.12, x, z + 0.02, 0.5);
    var o = { group: g, spec: spec, last: '' };
    o.draw = function (txt, unit, on) {
      var key = txt + '|' + unit + '|' + on;
      if (o.last === key) return;
      o.last = key;
      lcd.draw(function (cx, w, h) {
        var gr = cx.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#c7d0b4'); gr.addColorStop(1, '#a6b395');
        cx.fillStyle = gr; cx.fillRect(0, 0, w, h);
        if (!on) { cx.fillStyle = '#6e7a62'; cx.font = '600 40px "Public Sans", sans-serif'; cx.textAlign = 'center'; cx.fillText('OFF', w / 2, h / 2 + 14); return; }
        cx.font = '700 84px "JetBrains Mono", monospace'; cx.textAlign = 'right';
        cx.fillStyle = 'rgba(0,0,0,.07)'; cx.fillText('-88888', w - 128, 118);
        cx.fillStyle = '#171d13'; cx.fillText(txt, w - 128, 118);
        cx.textAlign = 'left'; cx.font = '700 38px "Public Sans", sans-serif'; cx.fillText(unit, w - 120, 118);
        cx.font = '600 24px "Public Sans", sans-serif'; cx.fillStyle = '#2c3526'; cx.fillText('AUTO', 16, 36);
      });
    };
    o.draw('0.000', spec.unit, false);
    return o;
  }

  // =============================================================================================== the sensors on the bench
  // Each art builder puts the real-looking sensor on the bench and returns update(vals, unknown).
  var G = new T.Group(); S.scene.add(G); G.position.set(0.05, 0, -0.2);
  function add(o) { G.add(o); return o; }
  function steelM() { return new T.MeshStandardMaterial({ color: 0xc8ccd0, roughness: 0.28, metalness: 0.9 }); }
  function tag(txt, w, x, y, z, rx) { var l = L(txt, { w: w, ratio: 0.16, color: '#1b1b1b', bg: '#f2efe6' }); l.position.set(x, y, z); if (rx) l.rotation.x = rx; add(l); return l; }
  function disc(r, h, mat, x, y, z) { var m = S.mesh(new T.CylinderGeometry(r, r, h, 28), mat); m.position.set(x, y, z); add(m); return m; }
  function boxM(w, h, d, mat, x, y, z) { var m = S.mesh(new T.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); add(m); return m; }

  function artLvdt() {
    boxM(0.36, 0.012, 0.11, M.alu, 0, 0.006, 0);
    var tube = disc(0.024, 0.2, steelM(), -0.03, 0.045, 0); tube.rotation.z = Math.PI / 2;
    [-0.07, -0.03, 0.01].forEach(function (cx) { var r = S.mesh(new T.TorusGeometry(0.0245, 0.003, 10, 28), M.copper); r.rotation.y = Math.PI / 2; r.position.set(cx - 0.0, 0.045, 0); add(r); });
    [-0.131, 0.071].forEach(function (cx) { disc(0.027, 0.006, M.black, cx, 0.045, 0).rotation.z = Math.PI / 2; });
    [-0.06, 0.0].forEach(function (cx) { boxM(0.012, 0.03, 0.05, M.alu, cx, 0.027, 0); });
    var core = new T.Group(); add(core); core.position.set(0, 0.045, 0);
    var rod = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.30, 20), M.chrome); rod.rotation.z = Math.PI / 2; rod.position.x = 0.03; core.add(rod);
    var slug = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.07, 24), new T.MeshStandardMaterial({ color: 0x3a3d44, roughness: 0.4, metalness: 0.6 })); slug.rotation.z = Math.PI / 2; slug.position.x = -0.045; core.add(slug);
    var mic = new T.Group(); add(mic); mic.position.set(0.19, 0.045, 0);
    var sc = S.canvasTex(256, 64, function (c, w, h) { c.fillStyle = '#e8e8e4'; c.fillRect(0, 0, w, h); c.fillStyle = '#222'; for (var i = 0; i < 50; i++) c.fillRect(i * 5, 0, 1.4, i % 5 ? 18 : 30); });
    var thim = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.05, 28), new T.MeshStandardMaterial({ map: sc, roughness: 0.4, metalness: 0.4 })); thim.rotation.z = Math.PI / 2; thim.position.x = 0.02; mic.add(thim);
    var barrel = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.06, 24), M.steel); barrel.rotation.z = Math.PI / 2; barrel.position.x = -0.03; mic.add(barrel);
    tag('LVDT + MICROMETER', 0.14, -0.03, 0.082, 0.04, -0.5);
    return function (v) { core.position.x = (v.x || 0) * 8; thim.rotation.x = (v.x || 0) * 1000 * 6.28; };
  }

  function artStrain() {
    boxM(0.34, 0.016, 0.1, M.darkWood, 0, 0.008, 0);
    boxM(0.05, 0.075, 0.06, M.iron, -0.14, 0.0535, 0);
    boxM(0.014, 0.012, 0.06, M.iron, -0.11, 0.1, 0).rotation.z = 0;
    var beam = new T.Group(); add(beam); beam.position.set(-0.115, 0.075, 0);
    var strip = S.mesh(new T.BoxGeometry(0.30, 0.0022, 0.025), steelM()); strip.position.x = 0.15; beam.add(strip);
    var gauge = S.mesh(new T.BoxGeometry(0.014, 0.0006, 0.008), new T.MeshStandardMaterial({ color: 0xc9a227, roughness: 0.3, metalness: 0.8 })); gauge.position.set(0.04, 0.0014, 0); beam.add(gauge);
    var gtex = S.canvasTex(128, 64, function (c, w, h) { c.fillStyle = '#c9a227'; c.fillRect(0, 0, w, h); c.strokeStyle = '#5a4510'; c.lineWidth = 2; for (var i = 0; i < 9; i++) { c.beginPath(); c.moveTo(14, 8 + i * 6); c.lineTo(w - 14, 8 + i * 6); c.stroke(); } });
    gauge.material = new T.MeshStandardMaterial({ map: gtex, roughness: 0.3, metalness: 0.5 });
    var hook = new T.Group(); hook.position.set(0.285, -0.0011, 0); beam.add(hook);
    var cord = S.mesh(new T.CylinderGeometry(0.0008, 0.0008, 0.05, 6), M.thread); cord.position.y = -0.025; hook.add(cord);
    var bar = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.05, 10), M.steel); bar.position.y = -0.05; hook.add(bar);
    var discs = [], i;
    for (i = 0; i < 12; i++) { var d = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.006, 28), M.brass); d.position.y = -0.04 - i * 0.0065; hook.add(d); discs.push(d); }
    var br = boxM(0.12, 0.04, 0.07, new T.MeshStandardMaterial({ color: 0x4a5866, roughness: 0.5 }), 0.1, 0.036, 0.03);
    var bl = L('BRIDGE + AMP (G = 100)', { w: 0.11, ratio: 0.15, color: '#f1f1f1' }); bl.position.set(0.1, 0.057, 0.0655); bl.rotation.x = -1.5708; add(bl);
    S.wire([[-0.075 + G.position.x, 0.078, G.position.z], [0.0 + G.position.x, 0.06, 0.04 + G.position.z], [0.07 + G.position.x, 0.05, 0.03 + G.position.z]], 'yellow');
    tag('STEEL CANTILEVER, 25 x 2 mm', 0.13, -0.02, 0.0165, 0.045, -1.5708);
    return function (v) { var m = v.m || 0; beam.rotation.z = -m * 0.045; discs.forEach(function (d, k) { d.visible = k < Math.round(m / 0.1); }); hook.visible = true; };
  }

  function artCapl() {
    boxM(0.2, 0.012, 0.16, M.darkWood, 0, 0.006, 0);
    var tank = new T.Group(); add(tank);
    var gl = S.mesh(new T.BoxGeometry(0.12, 0.3, 0.12), M.glass, false); gl.position.y = 0.162; tank.add(gl);
    var water = S.mesh(new T.BoxGeometry(0.114, 1, 0.114), new T.MeshPhysicalMaterial({ color: 0x8fc8e8, transmission: 0.5, roughness: 0.1, transparent: true, opacity: 0.85 }), false); tank.add(water);
    var can = S.mesh(new T.CylinderGeometry(0.07, 0.07, 0.3, 36), new T.MeshStandardMaterial({ color: 0x4a5058, roughness: 0.35, metalness: 0.85 })); can.position.y = 0.162; tank.add(can);
    var canL = L('UNKNOWN TANK (steel, opaque)', { w: 0.12, ratio: 0.15, color: '#f2efe6' }); canL.position.set(0, 0.2, 0.0705); tank.add(canL);
    var tubeM = S.mesh(new T.CylinderGeometry(0.012, 0.012, 0.31, 28, 1, true), new T.MeshStandardMaterial({ color: 0xd2d6d9, roughness: 0.2, metalness: 1, side: T.DoubleSide })); tubeM.position.y = 0.17; tank.add(tubeM);
    var rodM = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.33, 12), new T.MeshStandardMaterial({ color: 0xf4f4f0, roughness: 0.5 })); rodM.position.y = 0.175; tank.add(rodM);
    boxM(0.05, 0.03, 0.04, M.bakelite, 0, 0.335, 0);
    S.wire([[0.1 + G.position.x, 0.335, G.position.z], [0.0 + G.position.x, 0.4, 0.02 + G.position.z], [-0.28 + G.position.x, 0.2, 0.04 + G.position.z]], 'blue');
    tag('COAXIAL PROBE: inner rod 6 mm, tube 20 mm', 0.16, 0, 0.012, 0.09, -1.5708);
    var ruler = S.mesh(new T.BoxGeometry(0.006, 0.28, 0.002), new T.MeshStandardMaterial({ map: S.canvasTex(32, 512, function (c, w, h) { c.fillStyle = '#f0ead8'; c.fillRect(0, 0, w, h); c.fillStyle = '#222'; for (var k = 0; k <= 28; k++) c.fillRect(0, h - 8 - k * (h - 16) / 28, k % 5 ? 12 : 24, 2); }), roughness: 0.6 }));
    ruler.position.set(0.064, 0.15, 0.061); tank.add(ruler);
    return function (v, unk) {
      var h = v.h || 0;
      gl.visible = !unk; water.visible = !unk; ruler.visible = !unk; can.visible = !!unk; canL.visible = !!unk;
      water.scale.y = Math.max(0.0005, h); water.position.y = 0.012 + Math.max(0.0005, h) / 2;
    };
  }

  function artUltra() {
    var rail = boxM(0.84, 0.014, 0.05, M.alu, 0, 0.007, 0);
    var tex = S.canvasTex(2048, 64, function (c, w, h) { c.fillStyle = '#f0ead8'; c.fillRect(0, 0, w, h); c.fillStyle = '#1a1a1a'; c.font = '600 22px sans-serif';
      for (var k = 0; k <= 30; k++) { var xx = 40 + k * (w - 80) / 30; c.fillRect(xx, 0, k % 5 ? 2 : 4, k % 5 ? 18 : 30); if (k % 5 === 0) c.fillText((k / 10).toFixed(1) + ' m', xx + 4, 56); } });
    var sc = new T.Mesh(new T.PlaneGeometry(0.84, 0.026), new T.MeshStandardMaterial({ map: tex, roughness: 0.6 })); sc.rotation.x = -Math.PI / 2; sc.position.set(0, 0.0145, 0.012); add(sc);
    var unit = new T.Group(); add(unit); unit.position.set(-0.39, 0.0, 0);
    var pcb = S.mesh(new T.BoxGeometry(0.014, 0.036, 0.05), new T.MeshStandardMaterial({ color: 0x1f6f4a, roughness: 0.5 })); pcb.position.set(0, 0.04, 0); unit.add(pcb);
    [-0.014, 0.014].forEach(function (zz) { var cn = S.mesh(new T.CylinderGeometry(0.0085, 0.0085, 0.013, 24), steelM()); cn.rotation.z = Math.PI / 2; cn.position.set(0.012, 0.045, zz); unit.add(cn);
      var hole = S.mesh(new T.CylinderGeometry(0.006, 0.006, 0.002, 20), M.black, false); hole.rotation.z = Math.PI / 2; hole.position.set(0.0187, 0.045, zz); unit.add(hole); });
    tag('40 kHz TRANSMITTER (T) + RECEIVER (R)', 0.14, -0.35, 0.082, 0.02, -0.6);
    var target = new T.Group(); add(target);
    var plate = S.mesh(new T.BoxGeometry(0.008, 0.11, 0.12), new T.MeshStandardMaterial({ color: 0xe9e6dc, roughness: 0.7 })); plate.position.y = 0.075; target.add(plate);
    var foot = S.mesh(new T.BoxGeometry(0.04, 0.012, 0.07), M.iron); foot.position.y = 0.02; target.add(foot);
    var cover = S.mesh(new T.BoxGeometry(0.78, 0.2, 0.15), new T.MeshStandardMaterial({ color: 0x2a2d33, roughness: 0.6 })); cover.position.set(0.04, 0.1, 0); add(cover);
    var cl = L('UNKNOWN TARGET BEHIND THIS SCREEN', { w: 0.4, ratio: 0.1, color: '#f2efe6' }); cl.position.set(0.04, 0.14, 0.0755); add(cl);
    var thm = S.thermometer({ len: 0.2, min: 0, max: 50, value: p.T, pos: [0.46 + G.position.x, 0.0, 0.1 + G.position.z] }); thm.rotation.z = 0;
    return function (v, unk) {
      var xx = -0.375 + clamp(v.d || 0, 0, 3.2) * 0.26;
      target.position.x = xx; cover.visible = !!unk; cl.visible = !!unk; target.visible = !unk;
    };
  }

  function artTsens() {
    boxM(0.22, 0.012, 0.18, M.darkWood, 0, 0.006, 0);
    var hp = disc(0.075, 0.03, new T.MeshStandardMaterial({ color: 0x35383d, roughness: 0.4, metalness: 0.5 }), -0.02, 0.027, 0);
    var plate = disc(0.07, 0.004, M.steel, -0.02, 0.044, 0);
    var knob = S.mesh(new T.CylinderGeometry(0.011, 0.011, 0.012, 20), M.black); knob.rotation.x = Math.PI / 2; knob.position.set(0.1, 0.03, 0.04); add(knob);
    var ring = S.mesh(new T.TorusGeometry(0.075, 0.003, 8, 36), new T.MeshStandardMaterial({ color: 0xc23b30, emissive: 0x501008, roughness: 0.4 })); ring.rotation.x = Math.PI / 2; ring.position.set(-0.02, 0.043, 0); add(ring);
    var bk = S.beaker(0.052, 0.14, [G.position.x - 0.02, 0.046, G.position.z], 0xa8d5ec, 0.7); S.addApparatus('beaker', bk, 'Water bath on a hot plate', 'A stirred water bath; the hot plate sets its temperature.');
    var thm = S.thermometer({ len: 0.3, min: 0, max: 110, value: p.T, pos: [G.position.x - 0.045, 0.062, G.position.z + 0.012] });
    var sensor = new T.Group(); add(sensor); sensor.position.set(0.015, 0.0, -0.01);
    var sp = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.14, 14), steelM()); sp.position.set(-0.02, 0.12, 0); sensor.add(sp);
    var cb = S.mesh(new T.CylinderGeometry(0.0022, 0.0022, 0.06, 8), M.black); cb.position.set(-0.02, 0.22, 0); sensor.add(cb);
    var bar = S.mesh(new T.CylinderGeometry(0.003, 0.003, 0.03, 8), M.white); bar.rotation.z = Math.PI / 2; bar.position.set(-0.02, 0.07, -0.012); sensor.add(bar);
    S.wire([[G.position.x - 0.005, 0.25, G.position.z - 0.01], [G.position.x - 0.14, 0.3, G.position.z - 0.05], [G.position.x - 0.4, 0.12, G.position.z - 0.12]], 'red');
    var unkL = L('UNKNOWN BATH', { w: 0.1, ratio: 0.16, color: '#f2efe6', bg: '#2a2d33' }); unkL.position.set(-0.02, 0.18, 0.056); add(unkL); unkL.visible = false;
    tag('BATH: STIRRED WATER, SENSOR + THERMOMETER', 0.18, -0.02, 0.0125, 0.085, -1.5708);
    return function (v, unk) { thm.set(v.T === undefined ? 25 : v.T); thm.visible = !unk; unkL.visible = !!unk; bk.setLevel(0.7); knob.rotation.z = ((v.T || 20) - 20) / 60 * 4.2 - 2.1; };
  }

  function artMload() {
    boxM(0.34, 0.012, 0.16, M.cabinet, 0, 0.006, 0);
    var bb = boxM(0.3, 0.012, 0.09, new T.MeshStandardMaterial({ color: 0xefece2, roughness: 0.6 }), 0, 0.018, -0.02);
    var tex1 = S.liveTex(256, 64), tex2 = S.liveTex(256, 64);
    function mkRes(x, tex) {
      var g = new T.Group(); g.position.set(x, 0.034, -0.02); add(g);
      var body = S.mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.03, 20), new T.MeshStandardMaterial({ map: tex, roughness: 0.55 })); body.rotation.z = Math.PI / 2; g.add(body);
      [-1, 1].forEach(function (sg) { var ld = S.mesh(new T.CylinderGeometry(0.0007, 0.0007, 0.014, 8), M.chrome, false); ld.rotation.z = Math.PI / 2; ld.position.x = sg * 0.022; g.add(ld); });
      return g;
    }
    mkRes(-0.05, tex1); mkRes(0.07, tex2);
    var BAND = ['#111111', '#6b3a1e', '#c4231c', '#e8761e', '#e9c81a', '#2c8a3a', '#2747a8', '#7a3aa8', '#8a8a8a', '#f2f2f2'];
    function paint(tex, r) { var e = Math.floor(Math.log(r) / Math.LN10 + 1e-9) - 1, d = Math.round(r / Math.pow(10, e)); if (d >= 100) { d = Math.round(d / 10); e += 1; }
      var digs = [Math.floor(d / 10), d % 10, Math.max(0, Math.min(9, e))]; tex.draw(function (c, w, h) { c.fillStyle = '#d9bf8c'; c.fillRect(0, 0, w, h);
        [0.22, 0.34, 0.46, 0.8].forEach(function (f, k) { c.fillStyle = k < 3 ? BAND[digs[k]] : '#c9a23a'; c.fillRect(w * f, 0, w * 0.07, h); }); }); }
    var lab1 = L('R1', { w: 0.03, ratio: 0.5, color: '#3d3528' }), lab2 = L('R2', { w: 0.03, ratio: 0.5, color: '#3d3528' });
    lab1.rotation.x = lab2.rotation.x = -1.5708; lab1.position.set(-0.05, 0.026, -0.05); lab2.position.set(0.07, 0.026, -0.05); add(lab1); add(lab2);
    var rl = L('R1 = R2 = 1 kΩ', { w: 0.12, ratio: 0.16, color: '#1b1b1b', bg: '#f2efe6' }); rl.position.set(0, 0.0125, 0.065); rl.rotation.x = -1.5708; add(rl);
    var dl = S.liveTex(256, 40), dlm = new T.Mesh(new T.PlaneGeometry(0.12, 0.019), new T.MeshBasicMaterial({ map: dl, toneMapped: false })); dlm.rotation.x = -1.5708; dlm.position.set(0, 0.013, 0.065); add(dlm); rl.visible = false;
    return function (v) { paint(tex1, v.R1 || 1000); paint(tex2, v.R2 || 1000);
      dl.draw(function (c, w, h) { c.fillStyle = '#f2efe6'; c.fillRect(0, 0, w, h); c.fillStyle = '#1b1b1b'; c.font = '700 24px "Public Sans", sans-serif'; c.textAlign = 'center'; c.fillText('R1 = R2 = ' + rfmt(v.R1 || 1000), w / 2, 29); }); };
  }

  function artMbw() {
    var gen = S.rounded(0.3, 0.12, 0.2, 0.012, new T.MeshStandardMaterial({ color: 0xcdc9bf, roughness: 0.5, metalness: 0.15 })); gen.rotation.x = -Math.PI / 2; gen.position.set(0, 0.06, 0); add(gen);
    var lcd = S.liveTex(512, 128), scr = new T.Mesh(new T.PlaneGeometry(0.15, 0.0375), new T.MeshBasicMaterial({ map: lcd, toneMapped: false })); scr.position.set(-0.05, 0.085, 0.1015); add(scr);
    var knob = S.mesh(new T.CylinderGeometry(0.022, 0.024, 0.016, 32), M.bakelite); knob.rotation.x = Math.PI / 2; knob.position.set(0.09, 0.075, 0.105); add(knob);
    var kp = S.mesh(new T.BoxGeometry(0.003, 0.001, 0.02), M.white, false); kp.position.set(0, 0.0085, 0.009); knob.add(kp);
    var t1 = L('FUNCTION GENERATOR  ·  SINE  ·  1 V rms CONSTANT', { w: 0.24, ratio: 0.07, color: '#1b1b1b' }); t1.position.set(0, 0.112, 0.1015); add(t1);
    var bnc = S.mesh(new T.CylinderGeometry(0.008, 0.008, 0.014, 20), M.steel); bnc.rotation.x = Math.PI / 2; bnc.position.set(-0.1, 0.035, 0.105); add(bnc);
    S.wire([[G.position.x - 0.1, 0.035, G.position.z + 0.11], [G.position.x - 0.24, 0.05, G.position.z + 0.16], [G.position.x - 0.3, 0.1, G.position.z + 0.06]], 'blue');
    return function (v) { var f = v.f || 1000;
      lcd.draw(function (c, w, h) { c.fillStyle = '#10181a'; c.fillRect(0, 0, w, h); c.fillStyle = '#9ff0d2'; c.font = '700 72px "JetBrains Mono", monospace'; c.textAlign = 'right';
        c.fillText(f >= 1000 ? (f / 1000).toFixed(f >= 1e5 ? 0 : 1) + ' kHz' : f.toFixed(0) + ' Hz', w - 24, 92); });
      knob.rotation.y = -2.4 + 4.8 * (Math.log(f / 100) / Math.log(1e4)); };
  }

  function artPhoto() {
    var rail = S.mesh(new T.BoxGeometry(0.62, 0.02, 0.05), M.iron); rail.position.set(0, 0.03, 0); add(rail);
    var tex = S.canvasTex(2048, 64, function (c, w, h) { c.fillStyle = '#f0ead8'; c.fillRect(0, 0, w, h); c.fillStyle = '#1a1a1a'; c.font = '600 24px sans-serif';
      for (var k = 0; k <= 30; k++) { var xx = 30 + k * (w - 60) / 30; c.fillRect(xx, 0, k % 5 ? 2 : 4, k % 5 ? 18 : 32); if (k % 5 === 0) c.fillText(String(k), xx + 4, 58); } });
    var sc = new T.Mesh(new T.PlaneGeometry(0.62, 0.022), new T.MeshStandardMaterial({ map: tex, roughness: 0.6 })); sc.rotation.x = -Math.PI / 2; sc.position.set(0, 0.0405, 0.012); add(sc);
    var pd = new T.Group(); add(pd); pd.position.set(-0.29, 0.04, 0);
    var tubeP = S.mesh(new T.CylinderGeometry(0.02, 0.02, 0.07, 28, 1, true), new T.MeshStandardMaterial({ color: 0x121214, roughness: 0.8, side: T.DoubleSide })); tubeP.rotation.z = Math.PI / 2; tubeP.position.set(0.035, 0.03, 0); pd.add(tubeP);
    var chip = S.mesh(new T.BoxGeometry(0.003, 0.008, 0.008), new T.MeshStandardMaterial({ color: 0x1a2a4a, roughness: 0.2, metalness: 0.6 })); chip.position.set(0.0, 0.03, 0); pd.add(chip);
    boxM(0.03, 0.04, 0.04, M.iron, -0.31, 0.05, 0);
    var lamp = new T.Group(); add(lamp); lamp.position.set(0.0, 0.04, 0);
    var hb = S.mesh(new T.BoxGeometry(0.03, 0.012, 0.05), M.alu); lamp.add(hb);
    var cyl = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.05, 24), new T.MeshStandardMaterial({ color: 0x24262b, roughness: 0.4, metalness: 0.5 })); cyl.rotation.z = Math.PI / 2; cyl.position.set(0.0, 0.03, 0); lamp.add(cyl);
    var led = S.mesh(new T.SphereGeometry(0.0055, 16, 12), new T.MeshStandardMaterial({ color: 0xff3a2a, emissive: 0xff1a0a, emissiveIntensity: 2.2, roughness: 0.2 }), false); led.position.set(-0.026, 0.03, 0); lamp.add(led);
    tag('PHOTODIODE (chip 7.5 mm²) IN A BLACK TUBE', 0.14, -0.2, 0.012, 0.06, -1.5708);
    tag('RED LED 660 nm · 130 mW/sr', 0.1, 0.18, 0.012, 0.06, -1.5708);
    return function (v) { lamp.position.x = -0.29 + (v.d || 0.1) * 1.6; };
  }

  function artVac() {
    boxM(0.5, 0.014, 0.2, M.darkWood, 0, 0.007, 0);
    var plateV = disc(0.08, 0.012, steelM(), -0.12, 0.02, 0);
    var jar = S.mesh(new T.CylinderGeometry(0.06, 0.06, 0.14, 40, 1, true), M.glass, false); jar.position.set(-0.12, 0.096, 0); add(jar);
    var dome = S.mesh(new T.SphereGeometry(0.06, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2), M.glass, false); dome.position.set(-0.12, 0.166, 0); add(dome);
    var knobJ = S.mesh(new T.SphereGeometry(0.008, 12, 10), M.steel); knobJ.position.set(-0.12, 0.226, 0); add(knobJ);
    var pump = S.rounded(0.16, 0.08, 0.1, 0.01, new T.MeshStandardMaterial({ color: 0x3a6f58, roughness: 0.45, metalness: 0.2 })); pump.rotation.x = -Math.PI / 2; pump.position.set(0.17, 0.05, 0); add(pump);
    var motor = S.mesh(new T.CylinderGeometry(0.035, 0.035, 0.07, 28), new T.MeshStandardMaterial({ color: 0x24262b, roughness: 0.4, metalness: 0.5 })); motor.rotation.z = Math.PI / 2; motor.position.set(0.25, 0.07, 0); add(motor);
    var sight = S.mesh(new T.CylinderGeometry(0.014, 0.014, 0.004, 20), new T.MeshStandardMaterial({ color: 0xd9a21b, roughness: 0.2, transparent: true, opacity: 0.8 }), false); sight.position.set(0.15, 0.07, 0.051); sight.rotation.x = Math.PI / 2; add(sight);
    var hose = S.wire([[G.position.x - 0.07, 0.04, G.position.z], [G.position.x + 0.02, 0.025, G.position.z + 0.02], [G.position.x + 0.12, 0.07, G.position.z]], 'black');
    var gauge = disc(0.011, 0.04, steelM(), -0.04, 0.034, 0.07); gauge.userData.id = 'gauge';
    var gcap = disc(0.012, 0.01, M.red, -0.04, 0.058, 0.07);
    S.wire([[G.position.x - 0.04, 0.06, G.position.z + 0.07], [G.position.x - 0.2, 0.2, G.position.z + 0.1], [G.position.x - 0.44, 0.12, G.position.z + 0.0]], 'blue');
    tag('BELL JAR AND PIPEWORK: 20 L IN ALL', 0.12, -0.12, 0.0145, 0.1, -1.5708);
    tag('ROTARY PUMP · PIRANI GAUGE', 0.12, 0.13, 0.0145, 0.1, -1.5708);
    return function () {};
  }

  // =============================================================================================== the lab's plan
  var PLANS = {};
  function msg(a) { return a; }

  PLANS['sn-lvdt'] = function () { return {
    compName: 'LVDT with a micrometer drive', art: artLvdt,
    wiring: 'The primary is driven at 3 V rms, 2.5 kHz. The two secondaries, wound in opposition, go to the phase-sensitive detector; its output goes to meter 1 and the raw secondary to meter 2.',
    ctrlLabel: 'CORE POSITION',
    controls: [{ params: ['x'], label: 'Core displacement x', unit: 'mm', scale: 1000, digits: 1, vals: [-4, -3, -2, -1, 0, 1, 2, 3, 4].map(function (v) { return v * 1e-3; }) }],
    m1: { fn: 'DC mV', title: 'DETECTOR OUT', label: 'Detector output', unit: 'mV', digits: 2, lc: 0.01, get: function (v) { return v.Vout_mV; } },
    m2: { fn: 'AC mV p-p', title: 'SECONDARY', label: 'Secondary peak-to-peak', unit: 'mV', digits: 1, lc: 0.1, get: function (v) { return v.Vpp_mV; } },
    unknown: { set: { x: p.xu }, label: 'Unknown displacement' },
    cols: [{ label: 'x (mm)', get: function (r) { return r.unk ? 'unknown' : fmt(r.c0 * 1000, 1); } }, { label: 'Detector (mV)', get: function (r) { return fmt(r.m1, 2); } },
      { label: 'Secondary p-p (mV)', get: function (r) { return fmt(r.m2, 1); } }, { label: 'mV per mm', get: function (r) { return r.unk || r.c0 === 0 ? '—' : fmt(r.m1 / (r.c0 * 1000), 2); } }],
    need: 7,
    graph: { x: function (r) { return r.unk ? NaN : r.c0 * 1000; }, y: function (r) { return r.unk ? NaN : r.m1; }, xlabel: 'x (mm)', ylabel: 'Detector output (mV)',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var f = ols(known(rows).map(function (r) { return [r.c0 * 1000, r.m1]; })), u = unkRow(rows);
      if (!u || !isFinite(f.m) || f.m === 0) return null;
      return { label: 'Unknown displacement', value: (u.m1 - f.c) / f.m, unit: 'mm', digits: 2, truth: p.xu * 1000,
        note: 'Sensitivity ' + fmt(f.m, 2) + ' mV per mm from your line; null residual ' + fmt(f.c, 2) + ' mV.' };
    },
    resultNote: 'The detector output is a straight line through (almost) zero: the small intercept is the residual at the null that no LVDT quite loses. Its sign flips with the side of the centre because the secondaries oppose, which is why the detector, not a rectifier, is used.',
    chips: ['Why does the output change sign?', 'What is the sensitivity of this LVDT?', 'What is the null voltage?', 'Check my readings'],
    viva: [['Where is the LVDT output zero?', ['With the core at the centre', 'With the core out of the tube', 'With the primary off'], 0, 'The two secondary voltages then cancel.']] }; };

  PLANS['sn-strain-gauge'] = function () {
    var nb = Math.round(p.nb);
    return { compName: 'Steel cantilever with a strain gauge', art: artStrain,
    wiring: 'Gauge GF = 2.0, 350 ohm, bonded near the clamp, in a ' + (nb === 1 ? 'quarter' : nb === 2 ? 'half' : 'full') + ' bridge on a 5 V supply; the instrumentation amplifier (gain 100) feeds meter 1.',
    ctrlLabel: 'SLOTTED MASSES',
    controls: [{ params: ['m'], label: 'Load on the cantilever', unit: 'kg', scale: 1, digits: 1, vals: span(0, 1.2, 0.2) }],
    m1: { fn: 'DC mV', title: 'AMP OUTPUT', label: 'Amplifier output', unit: 'mV', digits: 2, lc: 0.01, get: function (v) { return v.Vout_V * 1000; } },
    m2: { fn: 'DC V', title: 'BRIDGE SUPPLY', label: 'Bridge supply', unit: 'V', digits: 3, lc: 0.001, get: function (v, q) { return q.Vs; } },
    unknown: { set: { m: p.mu }, label: 'Unknown mass' },
    cols: [{ label: 'm (kg)', get: function (r) { return r.unk ? 'unknown' : fmt(r.c0, 1); } }, { label: 'Output (mV)', get: function (r) { return fmt(r.m1, 2); } },
      { label: 'Net (mV)', get: function (r, i, rows) { var z = known(rows).filter(function (q) { return q.c0 === 0; })[0]; return z ? fmt(r.m1 - z.m1, 2) : '—'; } },
      { label: 'Strain (µε)', get: function (r, i, rows) { var z = known(rows).filter(function (q) { return q.c0 === 0; })[0]; return z ? fmt(4 * ((r.m1 - z.m1) / 1000 / p.G) / (nb * p.GF * r.m2) * 1e6, 0) : '—'; } }],
    need: 6,
    graph: { x: function (r) { return r.unk ? NaN : r.c0; }, y: function (r) { return r.unk ? NaN : r.m1; }, xlabel: 'Load (kg)', ylabel: 'Amplifier output (mV)',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var f = ols(known(rows).map(function (r) { return [r.c0, r.m1]; })), u = unkRow(rows);
      if (!u || !isFinite(f.m) || f.m === 0) return null;
      var eps = 4 * ((u.m1 - f.c) / 1000 / p.G) / (nb * p.GF * u.m2) * 1e6;
      return { label: 'Unknown mass', value: (u.m1 - f.c) / f.m, unit: 'kg', digits: 3, truth: p.mu,
        note: 'Slope ' + fmt(f.m, 2) + ' mV per kg; the strain at that load is about ' + fmt(eps, 0) + ' microstrain.' };
    },
    resultNote: 'The strain is only a few hundred parts per million, so the bridge gives a few millivolts and the amplifier lifts them. The intercept of the line is the amplifier offset, which has to come off every reading before the strain is worked out.',
    chips: ['How is strain found from the bridge output?', 'Why a bridge and not one gauge alone?', 'What does the intercept mean?', 'Check my readings'],
    viva: [['What does a strain gauge measure directly?', ['A change of resistance', 'A change of voltage', 'A change of length'], 0, 'The bridge turns that resistance change into a voltage.']] }; };

  PLANS['sn-capacitive-level'] = function () { return {
    compName: 'Coaxial capacitive level probe in a tank', art: artCapl,
    wiring: 'The probe (inner rod 6 mm, tube 20 mm, 30 cm long) goes to the LCR meter through a short screened lead. The tank is ' + (SAMPLE || 'water') + '; relative permittivity ' + p.er + '.',
    ctrlLabel: 'TANK LEVEL (pump valve)',
    controls: [{ params: ['h'], label: 'Liquid level h', unit: 'cm', scale: 100, digits: 0, vals: span(0, 0.28, 0.04) }],
    m1: { fn: 'C pF', title: 'LCR METER', label: 'Probe capacitance', unit: 'pF', digits: 1, lc: 0.1, get: function (v) { return v.C_pF; } },
    m2: null,
    unknown: { set: { h: p.hu }, label: 'Unknown tank' },
    cols: [{ label: 'h (cm)', get: function (r) { return r.unk ? 'unknown' : fmt(r.c0 * 100, 0); } }, { label: 'C (pF)', get: function (r) { return fmt(r.m1, 1); } },
      { label: 'ΔC from empty (pF)', get: function (r, i, rows) { var z = known(rows).filter(function (q) { return q.c0 === 0; })[0]; return z ? fmt(r.m1 - z.m1, 1) : '—'; } }],
    need: 6,
    graph: { x: function (r) { return r.unk ? NaN : r.c0 * 100; }, y: function (r) { return r.unk ? NaN : r.m1; }, xlabel: 'Level (cm)', ylabel: 'Capacitance (pF)',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var f = ols(known(rows).map(function (r) { return [r.c0 * 100, r.m1]; })), u = unkRow(rows);
      if (!u || !isFinite(f.m) || f.m === 0) return null;
      return { label: 'Level in the unknown tank', value: (u.m1 - f.c) / f.m, unit: 'cm', digits: 1, truth: p.hu * 100,
        note: 'Sensitivity ' + fmt(f.m, 2) + ' pF per cm; the empty probe plus cable reads ' + fmt(f.c, 1) + ' pF.' };
    },
    resultNote: 'The reading rises in a straight line with level because the wet and dry parts of the probe are capacitors in parallel. The intercept is the empty probe plus the cable, which is why the calibration is done on the same cable that is used afterwards.',
    chips: ['Why is capacitance linear in level?', 'What is the sensitivity of this probe?', 'What does the stray capacitance do?', 'Check my readings'],
    viva: [['If the cable is changed after calibration, the calibration line', ['shifts up or down', 'changes slope', 'stays exactly the same'], 0, 'A different cable has a different stray capacitance.']] }; };

  PLANS['sn-ultrasonic-ranging'] = function () { return {
    compName: 'Ultrasonic transmitter and receiver on a rail', art: artUltra,
    wiring: 'The transmitter sends an 8-cycle burst at 40 kHz when triggered; the receiver\'s comparator stops a timer that meter 1 shows. Meter 2 reads the room air temperature.',
    ctrlLabel: 'TARGET SLIDE (rail)',
    controls: [{ params: ['d'], label: 'Target distance d', unit: 'm', scale: 1, digits: 2, vals: [0.3, 0.5, 0.8, 1.1, 1.5, 2.0, 2.5] }],
    m1: { fn: 'ms', title: 'ECHO TIMER', label: 'Echo time', unit: 'ms', digits: 3, lc: 0.001, get: function (v) { return v.te_ms; } },
    m2: { fn: 'DC °C', title: 'AIR TEMP', label: 'Air temperature', unit: '°C', digits: 1, lc: 0.1, get: function (v, q) { return q.T; } },
    unknown: { set: { d: p.dx }, label: 'Unknown target' },
    cols: [{ label: 'd (m)', get: function (r) { return r.unk ? 'unknown' : fmt(r.c0, 2); } }, { label: 'Echo time (ms)', get: function (r) { return fmt(r.m1, 3); } },
      { label: '2d / te (m/s)', get: function (r) { return r.unk ? '—' : fmt(2 * r.c0 / (r.m1 / 1000), 0); } }],
    need: 6,
    graph: { x: function (r) { return r.unk ? NaN : r.c0; }, y: function (r) { return r.unk ? NaN : r.m1; }, xlabel: 'Distance (m)', ylabel: 'Echo time (ms)',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var f = ols(known(rows).map(function (r) { return [r.c0, r.m1]; })), u = unkRow(rows);
      if (!u || !isFinite(f.m) || f.m === 0) return null;
      return { label: 'Distance of the unknown target', value: (u.m1 - f.c) / f.m * 100, unit: 'cm', digits: 1, truth: p.dx * 100,
        note: 'Slope ' + fmt(f.m, 3) + ' ms per m gives the speed of sound ' + fmt(2000 / f.m, 1) + ' m/s; the intercept is the electronics delay ' + fmt(f.c, 3) + ' ms.' };
    },
    resultNote: 'The slope of the line is 2/c and the intercept is the fixed delay inside the electronics, so one straight line calibrates the ranger for the temperature of the day and for its own latency. Using 2d/te directly on a single reading would put the whole delay into the speed.',
    chips: ['Why is the slope 2/c?', 'What is the intercept?', 'How does temperature change the reading?', 'Check my readings'],
    viva: [['The factor 2 in the echo time comes from', ['the sound going to the target and back', 'two transducers', 'the burst having two halves'], 0, 'te = 2 d / c + t0.']] }; };

  PLANS['sn-temp-sensor'] = function () {
    var dev = Math.round(p.dev);
    var U = [{ unit: 'µA', fn: 'DC µA', lc: 0.01, d: 2, name: 'AD590 current', sens: 'µA per K' }, { unit: 'mV', fn: 'DC mV', lc: 0.1, d: 1, name: 'LM35 output', sens: 'mV per °C' },
      { unit: '°C', fn: 'I²C code', lc: 0.125, d: 3, name: 'LM75 reading', sens: '°C per °C' }, { unit: 'Ω', fn: 'Ω 4-wire', lc: 0.001, d: 3, name: 'Pt100 resistance', sens: 'Ω per °C' }][dev];
    return { compName: SAMPLE || 'Temperature sensor in a stirred water bath', art: artTsens,
    wiring: 'The sensor (' + (SAMPLE || U.name) + ') sits in the bath beside a mercury reference thermometer; the hot plate sets the temperature and a bead stirs. Meter 1 reads the sensor, meter 2 the reference.',
    ctrlLabel: 'HOT PLATE SETTING',
    controls: [{ params: ['T'], label: 'Bath temperature (reference)', unit: '°C', scale: 1, digits: 0, vals: span(20, 80, 10) }],
    m1: { fn: U.fn, title: 'SENSOR', label: U.name, unit: U.unit, digits: U.d, lc: U.lc, get: function (v) { return v.reading; } },
    m2: { fn: 'DC °C', title: 'REFERENCE', label: 'Reference thermometer', unit: '°C', digits: 1, lc: 0.1, get: function (v, q, unk) { return unk ? NaN : q.T; } },
    unknown: { set: { T: p.Tu }, label: 'Unknown bath' },
    cols: [{ label: 'Reference (°C)', get: function (r) { return r.unk ? 'unknown' : fmt(r.c0, 1); } }, { label: 'Sensor (' + U.unit + ')', get: function (r) { return fmt(r.m1, U.d); } }],
    need: 6,
    graph: { x: function (r) { return r.unk ? NaN : r.c0; }, y: function (r) { return r.unk ? NaN : r.m1; }, xlabel: 'Reference temperature (°C)', ylabel: 'Sensor reading (' + U.unit + ')',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var f = ols(known(rows).map(function (r) { return [r.c0, r.m1]; })), u = unkRow(rows);
      if (!u || !isFinite(f.m) || f.m === 0) return null;
      return { label: 'Temperature of the unknown bath', value: (u.m1 - f.c) / f.m, unit: '°C', digits: 1, truth: p.Tu,
        note: 'Sensitivity ' + fmt(f.m, dev === 3 ? 4 : 3) + ' ' + U.sens + ' and intercept ' + fmt(f.c, 2) + ' ' + U.unit + ' from your line.' };
    },
    resultNote: dev === 0 ? 'The AD590 passes one microampere per kelvin; your slope shows how close this specimen is to that, and the intercept to 273.15 microamperes at 0 degC plus its own offset.'
      : dev === 1 ? 'The LM35 gives ten millivolts per degree Celsius with its zero at 0 degC; the slope and intercept show this specimen\'s small differences.'
      : dev === 2 ? 'The LM75 reports temperature in steps of 0.125 degC, so its calibration line is a staircase on a straight trend and the slope is about one.'
      : 'The platinum resistance rises by about 0.39 ohm per degree, slightly less at higher temperature, which is why a straight line through a wide range is only approximate.',
    chips: ['What is the sensitivity of this sensor?', 'Why stir the bath?', 'What does the intercept mean?', 'Check my readings'],
    viva: [['What does a calibration line give you?', ['The sensor\'s slope and offset', 'Only its name', 'Its price'], 0, 'With it a reading becomes a temperature.']] }; };

  PLANS['sn-meter-loading'] = function () { return {
    compName: 'Voltage divider loaded by a meter', art: artMload,
    wiring: 'A 5 V supply feeds R1 in series with R2 to ground; the meter is connected across R2. The decade box sets R1 = R2 = R. The meter\'s input resistance is the unknown.',
    ctrlLabel: 'RESISTANCE DECADE (R1 = R2)',
    controls: [{ params: ['R1', 'R2'], label: 'Resistance R1 = R2', unit: '', scale: 1, digits: 0, fmtv: rfmt, vals: [1e3, 1e4, 1e5, 1e6, 1e7] }],
    m1: { fn: 'DC V', title: 'METER UNDER TEST', label: 'Meter reading', unit: 'V', digits: 4, lc: 1e-4, get: function (v) { return v.Vm; } },
    m2: { fn: 'DC V', title: 'SUPPLY', label: 'Supply voltage', unit: 'V', digits: 3, lc: 1e-3, get: function (v, q) { return q.Vs; } },
    cols: [{ label: 'R1 = R2', get: function (r) { return rfmt(r.c0); } }, { label: 'Meter (V)', get: function (r) { return fmt(r.m1, 4); } },
      { label: 'True (V)', get: function (r) { return fmt(r.m2 / 2, 4); } }, { label: 'Error (%)', get: function (r) { return fmt(100 * (r.m1 - r.m2 / 2) / (r.m2 / 2), 2); } },
      { label: 'Vt/Vm - 1', get: function (r) { return fmt(r.m2 / 2 / r.m1 - 1, 5); } }],
    need: 5,
    graph: { x: function (r) { return r.c0 / 2 / 1e6; }, y: function (r) { return r.m2 / 2 / r.m1 - 1; }, xlabel: 'Thevenin resistance R/2 (MΩ)', ylabel: 'Vtrue / Vmeter - 1',
      line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      var m = origin(rows.map(function (r) { return [r.c0 / 2, r.m2 / 2 / r.m1 - 1]; }));
      if (!isFinite(m) || m <= 0) return null;
      return { label: 'Input resistance of the meter', value: 1 / m / 1e6, unit: 'MΩ', digits: 2, truth: p.Rm / 1e6,
        note: 'From the slope of V_true/V_meter - 1 against the Thevenin resistance R/2: slope = 1/R_m.' };
    },
    resultNote: 'Across 1 kilohm the meter reads the true value to a few parts in ten thousand; across 10 megohm it reads far too low. The loading error is R_th/(R_th + R_m): a measurement is trustworthy only when the source resistance is much smaller than the meter\'s.',
    chips: ['Why does the meter read low across a high resistance?', 'What is R_th here?', 'How is R_m found from the graph?', 'Check my readings'],
    viva: [['A good voltmeter has', ['a very high input resistance', 'a very low input resistance', 'no input resistance'], 0, 'It then takes almost no current.']] }; };

  PLANS['sn-meter-bandwidth'] = function () { return {
    compName: 'AC meter and function generator', art: artMbw,
    wiring: 'The generator feeds the AC volts input of the meter at a constant 1 V rms (checked on meter 2 at every frequency).',
    ctrlLabel: 'FREQUENCY (generator dial)',
    controls: [{ params: ['f'], label: 'Generator frequency', unit: 'Hz', scale: 1, digits: 0, vals: [100, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000] }],
    m1: { fn: 'AC V', title: 'METER UNDER TEST', label: 'Meter reading', unit: 'V', digits: 4, lc: 1e-4, get: function (v) { return v.reading; } },
    m2: { fn: 'AC V', title: 'GENERATOR CHECK', label: 'Generator output', unit: 'V', digits: 3, lc: 1e-3, get: function (v, q) { return q.V; } },
    cols: [{ label: 'f (kHz)', get: function (r) { return fmt(r.c0 / 1000, 1); } }, { label: 'Reading (V)', get: function (r) { return fmt(r.m1, 4); } },
      { label: 'Error (%)', get: function (r) { return fmt(100 * (r.m1 - r.m2) / r.m2, 1); } }, { label: '(V/r)² - 1', get: function (r) { return fmt(Math.pow(r.m2 / r.m1, 2) - 1, 4); } }],
    need: 10,
    graph: { x: function (r) { return r.c0 * r.c0 / 1e10; }, y: function (r) { return Math.pow(r.m2 / r.m1, 2) - 1; }, xlabel: 'f² (10¹⁰ Hz²)', ylabel: '(V/reading)² - 1',
      line: function (pts) { var m = origin(pts); return function (x) { return m * x; }; } },
    result: function (rows) {
      var m = origin(rows.map(function (r) { return [r.c0 * r.c0, Math.pow(r.m2 / r.m1, 2) - 1]; }));
      if (!isFinite(m) || m <= 0) return null;
      return { label: 'Frequency at which the reading is down 3 dB', value: 1 / Math.sqrt(m) / 1000, unit: 'kHz', digits: 2, truth: p.fc / 1000,
        note: 'For a single-pole roll-off (V/reading)² - 1 = (f/f_c)², a straight line through the origin against f².' };
    },
    resultNote: 'Well below the cut-off the meter is accurate; at f_c it reads 70.7 % of the truth, and above it falls 20 dB per decade. A meter used beyond its bandwidth gives numbers that look plausible and are simply wrong.',
    chips: ['What does 3 dB down mean?', 'Why check the generator amplitude?', 'What is the meter\'s useful range?', 'Check my readings'],
    viva: [['Above its bandwidth an AC meter reads', ['too low', 'too high', 'exactly right'], 0, 'Its input stage no longer follows the signal.']] }; };

  PLANS['sn-photodiode'] = function () {
    var R = KK.measure(p).R;
    return { compName: 'Photodiode behind a black tube and an LED on a rail', art: artPhoto,
    wiring: 'The photodiode is reverse biased and its current read by meter 1. The LED (' + (p.lam * 1e9) + ' nm, radiant intensity ' + (p.Ie * 1000) + ' mW/sr) slides on the rail; meter 2 is a caliper reading its distance.',
    ctrlLabel: 'LED SLIDE (rail)',
    controls: [{ params: ['d'], label: 'LED distance d', unit: 'cm', scale: 100, digits: 1, vals: [0.05, 0.06, 0.08, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30] }],
    m1: { fn: 'DC µA', title: 'PHOTOCURRENT', label: 'Photocurrent', unit: 'µA', digits: 3, lc: 0.001, get: function (v) { return v.I_uA; } },
    m2: { fn: 'cm', title: 'CALIPER', label: 'LED distance', unit: 'cm', digits: 1, lc: 0.1, get: function (v) { return v.d_cm; } },
    cols: [{ label: 'd (cm)', get: function (r) { return fmt(r.m2, 1); } }, { label: 'I (µA)', get: function (r) { return fmt(r.m1, 3); } },
      { label: 'E (W/m²)', get: function (r) { return fmt(p.Ie / Math.pow(r.m2 / 100, 2), 2); } }, { label: 'P = E A (µW)', get: function (r) { return fmt(p.Ie / Math.pow(r.m2 / 100, 2) * p.A * 1e6, 2); } }],
    need: 7,
    graph: { x: function (r) { return p.Ie / Math.pow(r.m2 / 100, 2) * p.A * 1e6; }, y: function (r) { return r.m1; }, xlabel: 'Optical power on the chip (µW)', ylabel: 'Photocurrent (µA)',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var f = ols(rows.map(function (r) { return [p.Ie / Math.pow(r.m2 / 100, 2) * p.A * 1e6, r.m1]; }));
      if (!isFinite(f.m)) return null;
      return { label: 'Responsivity', value: f.m, unit: 'A/W', digits: 3, truth: R,
        note: 'Slope of photocurrent (µA) against optical power (µW); the intercept ' + fmt(f.c * 1000, 1) + ' nA is the dark current.' };
    },
    resultNote: 'The photocurrent is proportional to the light power, so the points fall on a straight line whose slope is the responsivity; the small intercept is the dark current. An ideal diode would give about ' + fmt(p.lam * 1e6 * 0.8065, 2) + ' A/W at this wavelength for unit quantum efficiency.',
    chips: ['Why does the current fall as 1/d²?', 'What is the responsivity?', 'What is the dark current?', 'Check my readings'],
    viva: [['The photocurrent is proportional to', ['the optical power on the chip', 'the square of the power', 'the diode voltage'], 0, 'Each photon frees at most one electron-hole pair.']] }; };

  PLANS['sn-rotary-vacuum'] = function () { return {
    compName: 'Rotary pump, bell jar and Pirani gauge', art: artVac,
    wiring: 'A single-stage rotary pump evacuates the chamber (20 litres in all) through a hose; the Pirani gauge reads the pressure in millibar (meter 1) and a stopwatch the time (meter 2).',
    ctrlLabel: 'STOPWATCH TIME (start the pump at 0)',
    controls: [{ params: ['t'], label: 'Time since pump start', unit: 's', scale: 1, digits: 0, vals: [0, 5, 10, 15, 20, 25, 30, 40, 50, 300] }],
    m1: { fn: 'mbar', title: 'PIRANI GAUGE', label: 'Gauge pressure', unit: 'mbar', digits: 3, lc: sig3, get: function (v) { return v.P; },
      disp: function (val) { var a = Math.abs(val); return a >= 100 ? val.toFixed(0) : a >= 10 ? val.toFixed(1) : a >= 1 ? val.toFixed(2) : a >= 0.1 ? val.toFixed(3) : val.toFixed(4); } },
    m2: { fn: 's', title: 'STOPWATCH', label: 'Time', unit: 's', digits: 0, lc: 1, get: function (v, q) { return q.t; } },
    cols: [{ label: 't (s)', get: function (r) { return fmt(r.c0, 0); } }, { label: 'P (mbar)', get: function (r) { return fmt(r.m1, r.m1 >= 100 ? 0 : r.m1 >= 10 ? 1 : r.m1 >= 1 ? 2 : 4); } },
      { label: 'P - P_u (mbar)', get: function (r, i, rows) { var pu = ult(rows); return pu === null ? '—' : fmt(r.m1 - pu, r.m1 - pu >= 10 ? 1 : 3); } },
      { label: 'ln(P - P_u)', get: function (r, i, rows) { var pu = ult(rows); return pu === null || r.m1 - pu <= 0 ? '—' : fmt(Math.log(r.m1 - pu), 3); } }],
    need: 9,
    graph: { x: function (r) { return r.c0; }, y: function (r) { var pu = ult(S.rows); return pu === null || r.m1 - pu <= 0.2 ? NaN : Math.log(r.m1 - pu); }, xlabel: 'Time (s)', ylabel: 'ln(P - P_u)',
      line: function (pts) { var f = ols(pts); return function (x) { return f.m * x + f.c; }; } },
    result: function (rows) {
      var pu = ult(rows);
      if (pu === null) return null;
      var pts = rows.filter(function (r) { return r.m1 - pu > 0.2; }).map(function (r) { return [r.c0, Math.log(r.m1 - pu)]; });
      var f = ols(pts);
      if (!isFinite(f.m) || f.m >= 0) return null;
      return { label: 'Pumping speed', value: -f.m * p.Vch * 1000, unit: 'L/s', digits: 2, truth: p.S * 1000,
        note: 'Slope ' + fmt(f.m, 4) + ' per second times the 20 litre volume; ultimate pressure ' + fmt(pu, 3) + ' mbar from the last reading.' };
    },
    resultNote: 'The pressure falls by the same fraction in each equal interval, an exponential, until the pump reaches its ultimate pressure. A straight line of ln(P - P_u) against time has slope -S/V, so a bigger chamber or a slower pump gives a longer time constant.',
    chips: ['Why does ln(P - P_u) give a straight line?', 'What is the ultimate pressure?', 'What limits the lowest pressure?', 'Check my readings'],
    viva: [['If the chamber volume is doubled the pump-down time', ['doubles', 'halves', 'stays the same'], 0, 'The time constant is V/S.']] }; };
  function ult(rows) { var best = null, i; for (i = 0; i < rows.length; i++) if (rows[i].c0 >= 200 && (best === null || rows[i].c0 > best.c0)) best = rows[i]; return best ? best.m1 : null; }

  var PL = (PLANS[BASE] || PLANS['sn-lvdt'])();
  var CTRL = PL.controls;
  var ART = PL.art();

  // =============================================================================================== the bench furniture
  function cabinet(w, h, d, x, z, color) {      // a bench box: footprint w x h, height d, front face at +z
    var b = S.rounded(w, h, d, 0.008, new T.MeshStandardMaterial({ color: color, roughness: 0.5, metalness: 0.1 }));
    b.rotation.x = -Math.PI / 2; b.position.set(x, d / 2, z); S.scene.add(b); S.contact(w + 0.06, h + 0.06, x, z, 0.5); return b;
  }
  function dialKnob(parent, x, y, z, r) {
    var k = new T.Group(); k.position.set(x, y, z); parent.add(k);
    var sk = S.mesh(new T.CylinderGeometry(r * 1.25, r * 1.3, 0.004, 32), M.black); sk.rotation.x = Math.PI / 2; sk.position.z = 0.002; k.add(sk);
    var kb = S.mesh(new T.CylinderGeometry(r, r * 1.08, 0.016, 32), new T.MeshStandardMaterial({ color: 0x24252a, roughness: 0.4, metalness: 0.3 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; k.add(kb);
    var pt = S.mesh(new T.BoxGeometry(0.003, r * 0.9, 0.0016), M.white, false); pt.position.set(0, r * 0.45, 0.0215); k.add(pt);
    return k;
  }
  var CBX = 0.42, CBZ = -0.02, PBX = 0.42, PBZ = -0.36;
  var cb = new T.Group(); S.scene.add(cb); cb.position.set(CBX, 0, CBZ);
  var cbBody = S.rounded(0.2, 0.1, 0.09, 0.008, new T.MeshStandardMaterial({ color: 0x4a5866, roughness: 0.5 })); cbBody.rotation.x = -Math.PI / 2; cbBody.position.y = 0.045; cb.add(cbBody);
  S.contact(0.26, 0.16, CBX, CBZ, 0.5);
  var cbL = L(PL.ctrlLabel, { w: 0.18, ratio: 0.09, color: '#f2f2f2', px: 1024 }); cbL.position.set(0, 0.078, 0.0505); cb.add(cbL);
  var dial = dialKnob(cb, -0.05, 0.036, 0.0505, 0.017);
  var dispTex = S.liveTex(256, 80), disp = new T.Mesh(new T.PlaneGeometry(0.075, 0.0234), new T.MeshBasicMaterial({ map: dispTex, toneMapped: false })); disp.position.set(0.04, 0.047, 0.0508); cb.add(disp);
  var swKnob = null;
  if (PL.unknown) {
    var swBase = S.mesh(new T.BoxGeometry(0.05, 0.016, 0.006), M.black); swBase.position.set(0.055, 0.016, 0.0505); cb.add(swBase);
    swKnob = new T.Group(); swKnob.position.set(0.055, 0.016, 0.0535); cb.add(swKnob);
    var lev = S.mesh(new T.BoxGeometry(0.01, 0.012, 0.008), M.chrome); lev.position.set(0, 0, 0.003); swKnob.add(lev);
    var sl1 = L('KNOWN', { w: 0.026, ratio: 0.28, color: '#f2f2f2' }); sl1.position.set(0.02, 0.0305, 0.0508); cb.add(sl1);
    var sl2 = L('UNKNOWN', { w: 0.03, ratio: 0.26, color: '#f2f2f2' }); sl2.position.set(0.09, 0.0305, 0.0508); cb.add(sl2);
    var sl3 = L('SAMPLE', { w: 0.03, ratio: 0.26, color: '#d9e2ee' }); sl3.position.set(0.055, 0.0, 0.0508); cb.add(sl3);
  }
  var pb = new T.Group(); S.scene.add(pb); pb.position.set(PBX, 0, PBZ);
  var pbBody = S.rounded(0.16, 0.09, 0.07, 0.008, new T.MeshStandardMaterial({ color: 0x3a4f6e, roughness: 0.5 })); pbBody.rotation.x = -Math.PI / 2; pbBody.position.y = 0.035; pb.add(pbBody);
  S.contact(0.22, 0.15, PBX, PBZ, 0.5);
  var pbL = L('SENSOR SUPPLY  ± 5 V', { w: 0.14, ratio: 0.1, color: '#f2f2f2', px: 1024 }); pbL.position.set(0, 0.058, 0.0455); pb.add(pbL);
  var rockerBase = S.mesh(new T.BoxGeometry(0.03, 0.02, 0.006), M.black); rockerBase.position.set(-0.04, 0.03, 0.0455); pb.add(rockerBase);
  var rocker = S.mesh(new T.BoxGeometry(0.022, 0.014, 0.01), new T.MeshStandardMaterial({ color: 0xd9d9d6, roughness: 0.4 })); rocker.position.set(-0.04, 0.03, 0.05); pb.add(rocker);
  var pilotM = new T.MeshStandardMaterial({ color: 0x331111, emissive: 0x000000, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.0055, 14, 10), pilotM, false); pilot.position.set(0.04, 0.03, 0.0475); pb.add(pilot);
  var pw = L('POWER', { w: 0.03, ratio: 0.26, color: '#d9e2ee' }); pw.position.set(-0.04, 0.012, 0.0455); pb.add(pw);

  var dm1 = dmm(-0.34, -0.4, PL.m1.title, PL.m1), dm2 = PL.m2 ? dmm(-0.16, -0.4, PL.m2.title, PL.m2) : null;
  function jackPos(o, which) { var w = new T.Vector3(); o.group.updateMatrixWorld(true); o.group.userData[which].getWorldPosition(w); return w; }
  [[dm1, 0.0, 'blue'], [dm2, 0.03, 'yellow']].forEach(function (q) {
    if (!q[0]) return;
    var r = jackPos(q[0], 'red'), b = jackPos(q[0], 'black');
    S.wire([arr(r), [r.x + 0.02, 0.05, r.z + 0.1], [-0.05 + q[1], 0.03, -0.2 + 0.06]], q[2]);
    S.wire([arr(b), [b.x - 0.01, 0.04, b.z + 0.12], [-0.03 + q[1], 0.03, -0.2 + 0.08]], 'black');
  });
  S.wire([[PBX - 0.08, 0.04, PBZ + 0.03], [0.3, 0.03, -0.3], [0.2, 0.03, -0.22]], 'red');

  S.addApparatus('art', G, PL.compName, PL.wiring);
  S.addApparatus('supply', pb, 'Sensor supply with a POWER rocker', 'The rocker switches the sensor, its electronics and the meters on; the pilot lamp shows that it is live.');
  S.addApparatus('ctrl', cb, 'Control box: ' + PL.ctrlLabel.toLowerCase(), 'The hand turns this dial to set the stimulus to each of the values in turn. The small display shows its present value' + (PL.unknown ? '; the SAMPLE switch swaps in the unknown.' : '.'));
  S.addApparatus('dm1', dm1.group, 'Meter 1: ' + PL.m1.label, 'Range ' + PL.m1.fn + '. Its leads are already on the right two points of the circuit.');
  if (dm2) S.addApparatus('dm2', dm2.group, 'Meter 2: ' + PL.m2.label, 'Range ' + PL.m2.fn + '.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');
  var hud1 = S.hudCard(PL.m1.label), hud2 = dm2 ? S.hudCard(PL.m2.label) : null, hudS = S.hudCard('Setting');

  // =============================================================================================== state and readings
  var st = { power: false, checked: false, unk: false, set: CTRL[0].vals[0], idx: 0, unkSeen: false };
  function over() { var o = {}; CTRL[0].params.forEach(function (pr) { o[pr] = st.set; }); return st.unk && PL.unknown ? assign(o, PL.unknown.set) : o; }
  function live() { return readAt(over()); }
  function liveQ() { return assign(p, over()); }
  function mval(m) {
    var v = live(), val = m.get(v, liveQ(), st.unk), lc;
    if (!isFinite(val)) return NaN;
    lc = typeof m.lc === 'function' ? m.lc(val) : m.lc;
    return Math.round(val / lc) * lc;
  }
  function mtxt(m) { var v = mval(m); return !isFinite(v) ? '----' : (m.disp ? m.disp(v) : fmt(v, m.digits)); }
  function ctrlTxt(v) { var c = CTRL[0]; return c.fmtv ? c.fmtv(v) : fmt(v * c.scale, c.digits) + (c.unit ? ' ' + c.unit : ''); }
  function dialAngle(i) { return 2.3 - 4.6 * i / Math.max(1, CTRL[0].vals.length - 1); }
  function setLook() {
    dial.rotation.z = dialAngle(st.idx);
    if (swKnob) swKnob.rotation.z = st.unk ? -0.5 : 0.5;
    var on = st.power;
    pilotM.emissive.setHex(on ? 0x22ff55 : 0x000000); pilotM.color.setHex(on ? 0x38c25e : 0x331111);
    rocker.rotation.x = on ? -0.3 : 0.3;
    var txt = st.unk ? 'UNKNOWN' : ctrlTxt(st.set);
    dispTex.draw(function (c, w, h) { c.fillStyle = '#10181a'; c.fillRect(0, 0, w, h); c.fillStyle = '#9ff0d2'; c.font = '700 40px "JetBrains Mono", monospace'; c.textAlign = 'center'; c.fillText(txt, w / 2, 54, w - 16); });
  }
  var artKey = '';
  function artSync() {
    var o = over(), k = JSON.stringify(o) + st.unk;
    if (k === artKey) return;
    artKey = k; ART(assign(p, o), st.unk);
  }
  setLook(); artSync();

  // =============================================================================================== human actions
  function dialFront() { return wpos(cb, -0.05, 0.036, 0.062); }
  function turnTo(value) {
    var c = CTRL[0];
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var j = 0, best = 1e30, k;
    for (k = 0; k < c.vals.length; k++) if (Math.abs(c.vals[k] - value) < best) { best = Math.abs(c.vals[k] - value); j = k; }
    if (j === st.idx && st.set === c.vals[j]) return Promise.resolve();
    var i0 = st.idx, pt = dialFront();
    return S.hand.pinchMove(pt, function () { return pt; }, function (kk) {
      st.set = kk >= 1 ? c.vals[j] : c.vals[i0] + (c.vals[j] - c.vals[i0]) * kk; dial.rotation.z = dialAngle(i0 + (j - i0) * kk); artSync();
    }, { mode: 'front', ms: 380 + 200 * Math.min(3, Math.abs(j - i0)), reachMs: 520 })
      .then(function () { st.idx = j; st.set = c.vals[j]; setLook(); artSync(); S.render(); });
  }
  function togglePower(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () {
      st.power = on; setLook(); S.click(900, 0.05);
      S.say(on ? 'Supply on. The pilot lamp is lit and the meters have woken up.' : 'Supply off.');
      S.render();
    });
  }
  function toggleSample(unk) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (unk === st.unk) return Promise.resolve();
    return S.hand.tap(swKnob, 'front').then(function () {
      st.unk = unk; setLook(); artSync(); S.click(700, 0.05);
      S.say(unk ? 'The unknown sample is now connected.' : 'The known sample is connected again.');
      S.render();
    });
  }
  function rowNow() {
    var row = { unk: st.unk ? 1 : 0, c0: st.unk ? NaN : st.set, m1: mval(PL.m1), m2: PL.m2 ? mval(PL.m2) : 0 };
    return row;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return; }
    if (!st.power) { S.say('Switch the supply on first.'); return; }
    var i;
    if (st.unk) {
      if (unkRow(S.rows)) { S.say('You already have a reading for the unknown. Delete it to take it again.'); return; }
    } else {
      for (i = 0; i < S.rows.length; i++) if (!S.rows[i].unk && Math.abs(S.rows[i].c0 - st.set) < 1e-12) { S.say('You already have a reading at this setting. Turn the dial to a new one.'); return; }
    }
    var row = rowNow();
    S.addRow(row);
    S.say('Written in your record book: ' + mtxt(PL.m1) + ' ' + PL.m1.unit + (PL.m2 ? ' and ' + mtxt(PL.m2) + ' ' + PL.m2.unit : '') + '.');
  }
  function enough() { return known(S.rows).length >= PL.need; }

  var FORMULA = {
    'sn-lvdt': 'V = V_p S x', 'sn-strain-gauge': 'V = V_s n GF ε / 4,   ε = 6 m g L / (E b h²)', 'sn-capacitive-level': 'C = 2π ε₀ (H + (ε_r − 1) h) / ln(b/a) + C_stray',
    'sn-ultrasonic-ranging': 'te = 2 d / c + t₀,   c = 331.3 √(1 + T/273.15)', 'sn-temp-sensor': 'reading = m × T + c',
    'sn-meter-loading': 'V_meter / V_true = R_m / (R_m + R_th)', 'sn-meter-bandwidth': 'reading = V / √(1 + (f/f_c)²)', 'sn-photodiode': 'I = R P + I_dark,   R = η λ q / (h c)',
    'sn-rotary-vacuum': 'P − P_u = (P₀ − P_u) exp(−S t / V)' };

  return {
    camera: { pos: [0.02, 0.74, 1.14], look: [0.02, 0.04, -0.2] },
    views: {
      art: [[0.05, 0.34, 0.42], [0.05, 0.06, -0.2]], supply: [[0.4, 0.2, 0.0], [0.42, 0.04, -0.36]], ctrl: [[0.4, 0.2, 0.34], [0.42, 0.05, -0.02]],
      dm1: [[-0.34, 0.25, 0.0], [-0.34, 0.12, -0.4]], dm2: [[-0.16, 0.25, 0.0], [-0.16, 0.12, -0.4]],
      bench: [[0.02, 0.74, 1.14], [0.02, 0.04, -0.2]], book: [[-0.55, 0.44, 0.52], [-0.62, 0.0, 0.08]],
      beaker: [[0.1, 0.3, 0.3], [0.08, 0.1, -0.2]],
    },
    theory: {
      principle: S.lab.theory, formula: FORMULA[BASE] || '',
      formulaNote: 'All the numbers on this bench come from the lab\'s own kernel; the apparatus is the shared sensor bench.' + (SAMPLE ? ' This specimen: ' + SAMPLE + '.' : ''),
      more: ['How it is wired: ' + PL.wiring],
      precautions: S.lab.safety + ' Switch the supply off before touching a connection.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title, at: [-0.66, 0.1, 0.12],
      lines: ['Aim: ' + S.lab.aim, PL.wiring, 'Meter 1: ' + PL.m1.fn + ' — ' + PL.m1.label + (typeof PL.m1.lc === 'number' ? ', least count ' + PL.m1.lc + ' ' + PL.m1.unit : ''),
        PL.m2 ? 'Meter 2: ' + PL.m2.fn + ' — ' + PL.m2.label : 'One meter only.', 'Precautions: supply off before changing a connection; one setting changed at a time.'],
      columns: [{ label: 'S.No', get: function (r, i) { return r.unk ? 'U' : i + 1; } }].concat(PL.cols.map(function (c) {
        return { label: c.label, get: function (r, i) { return c.get(r, i, S.rows); } };
      })),
    },
    graph: PL.graph,
    result: function (rows) { return known(rows).length < 2 ? null : PL.result(rows); },
    tol: 0.03,
    resultNote: PL.resultNote,
    chips: PL.chips,
    viva: PL.viva,
    askState: function () {
      var out = { supply_on: st.power, readings_taken: S.rows.length, set_up: PL.wiring, specimen: SAMPLE || PL.compName, sample_connected: st.unk ? 'unknown' : 'known' };
      out[PL.m1.label] = mtxt(PL.m1) + ' ' + PL.m1.unit;
      if (PL.m2) out[PL.m2.label] = mtxt(PL.m2) + ' ' + PL.m2.unit;
      out[CTRL[0].label] = st.unk ? 'unknown' : ctrlTxt(st.set);
      return out;
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Check the set-up and switch on');
          u.p(PL.wiring);
          u.task('1. Check the apparatus', st.checked, st.checked ? 'Sensor, meters and control box checked' : 'Look at the sensor and its leads')
            .add(u.button(st.checked ? 'Checked' : 'Check the set-up', function () { st.checked = true; S.focus('art'); S.say(PL.compName + '. ' + PL.wiring); S.render(); }, !st.checked, st.checked));
          u.task('2. Control at its first value, then switch the supply on', st.power, st.power ? 'Supply on; the meters are reading' : 'The hand presses the POWER rocker')
            .add(u.row(u.button(st.power ? 'Switch off' : 'Switch on the supply', function () { S.focus('supply'); togglePower(!st.power); }, !st.power, S.hand.busy)));
          u.note('A circuit is checked before it is powered, never after. Change one setting at a time once it is live.');
          u.next('Next: take readings', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return togglePower(true); } },
      { id: 'read', title: 'Readings', view: 'ctrl', render: function (u) {
          var c = CTRL[0];
          u.h2('Set the control and record the meters');
          u.p('Let the hand turn the dial to each value in turn, then read the meter' + (PL.m2 ? 's' : '') + ' and write the reading into the record book. At least ' + PL.need + ' readings are needed.');
          u.slider(c.label, 0, c.vals.length - 1, 1, function () { return st.idx; }, function (k) { turnTo(c.vals[k]); }, '', 0);
          u.note(c.label + ' is now ' + ctrlTxt(st.set) + '  ·  ' + c.vals.length + ' settings on this dial');
          u.row(u.button('Record the meter' + (PL.m2 ? 's' : ''), function () { record(); }, true, S.hand.busy));
          u.live(function () { return PL.m1.label + ': ' + mtxt(PL.m1) + ' ' + PL.m1.unit + (PL.m2 ? '  ·  ' + PL.m2.label + ': ' + mtxt(PL.m2) + ' ' + PL.m2.unit : ''); });
          u.h3('Observation table'); u.table();
          if (!enough()) u.p(known(S.rows).length + ' of at least ' + PL.need + ' readings recorded.');
          u.next(PL.unknown ? 'Next: the unknown sample' : 'Next: plot and work out the result', enough());
        },
        ok: function () { return enough(); },
        auto: function () {
          return CTRL[0].vals.reduce(function (pr, v) {
            return pr.then(function () { return turnTo(v); }).then(function () { record(); });
          }, Promise.resolve());
        } },
    ].concat(PL.unknown ? [
      { id: 'unknown', title: 'Unknown sample', view: 'ctrl', render: function (u) {
          u.h2('Measure the unknown');
          u.p('Swing the SAMPLE switch to UNKNOWN. The control box now connects the ' + PL.unknown.label.toLowerCase() + ' to the sensor. Read the meters and record the reading, then use your line to find it.');
          u.task('1. Connect the unknown', st.unk, st.unk ? 'The unknown sample is connected' : 'The hand flips the SAMPLE switch')
            .add(u.button(st.unk ? 'Connected' : 'Connect the unknown', function () { S.focus('ctrl'); toggleSample(true); }, !st.unk, st.unk || S.hand.busy));
          u.task('2. Record the reading', !!unkRow(S.rows), unkRow(S.rows) ? 'Written in the record book' : 'Read the meter' + (PL.m2 ? 's' : ''))
            .add(u.button('Record the unknown', function () { record(); }, st.unk && !unkRow(S.rows), !st.unk || S.hand.busy || !!unkRow(S.rows)));
          u.live(function () { return PL.m1.label + ': ' + mtxt(PL.m1) + ' ' + PL.m1.unit; });
          u.h3('Observation table'); u.table();
          u.next('Next: plot and work out the result', !!unkRow(S.rows));
        },
        ok: function () { return !!unkRow(S.rows); },
        auto: function () { return toggleSample(true).then(function () { record(); }); } },
    ] : []),

    tick: function () {
      var on = st.power, vtxt = mtxt(PL.m1);
      artSync();
      dm1.draw(on ? vtxt : '0.000', PL.m1.unit, on);
      hud1.set(on ? vtxt + ' ' + PL.m1.unit : 'off');
      if (dm2) { var t2 = mtxt(PL.m2); dm2.draw(on ? t2 : '0.000', PL.m2.unit, on); hud2.set(on ? t2 + ' ' + PL.m2.unit : 'off'); }
      hudS.set(st.unk ? 'unknown sample' : ctrlTxt(st.set));
    },
  };
});
