/* Kernel pack `elec_ug`: the exact JavaScript twin of app/prayog/packs/elec_ug.py. Same formulas, same algorithms,
   same numbers (the server's tests run both and compare). The undergraduate analog and digital electronics physics
   the shared `circuit` kernel cannot do: a JFET / MOSFET channel, an op-amp with a finite gain and saturation, a
   Zener shunt regulator with a load, a solar cell as the single-diode model, a rectifier with a capacitor filter,
   and logic gates / adders / subtractors built out of 2-input NAND gates. Deterministic: fixed-count bisection,
   fixed time steps, no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, VT = 0.025852, NS = 2000, CYC = 40;

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function bit(v) { return (+v) >= 0.5 ? 1 : 0; }
  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; if (b) for (k in b) o[k] = b[k]; return o; }

  // ================================================================================== FET (JFET / MOSFET)
  var fet = {
    PARAMS: { kind: 0.0, Idss: 0.008, Vp: -3.0, kn: 0.02, Vth: 2.1, lam: 0.02, Vgs: 0.0, Vdd: 12.0, Rd: 1000.0 },
    VARS: ['t', 'I_d', 'V_ds', 'V_gs', 'V_rd', 'gm'],
    id_at: function (vds, p) {
      if (vds < 0) vds = 0;
      var vov, a, core;
      if (p.kind < 0.5) {
        vov = p.Vgs - p.Vp;
        if (vov <= 0) return 0;
        a = p.Idss / (p.Vp * p.Vp);
        core = vds < vov ? a * (2 * vov * vds - vds * vds) : a * vov * vov;
      } else {
        vov = p.Vgs - p.Vth;
        if (vov <= 0) return 0;
        core = vds < vov ? p.kn * (vov * vds - 0.5 * vds * vds) : 0.5 * p.kn * vov * vov;
      }
      return core * (1 + p.lam * vds);
    },
    solve: function (p) {
      var lo = 0, hi = Math.max(p.Vdd, 0), i, mid, vds;
      for (i = 0; i < 80; i++) { mid = (lo + hi) / 2; if (mid + fet.id_at(mid, p) * p.Rd > p.Vdd) hi = mid; else lo = mid; }
      vds = (lo + hi) / 2;
      return [fet.id_at(vds, p), vds];
    },
    gm: function (p) {
      var d = 0.001, hi = fet.solve(assign(p, { Vgs: p.Vgs + d }))[0], lo = fet.solve(assign(p, { Vgs: p.Vgs - d }))[0];
      return (hi - lo) / (2 * d);
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = fet.solve(p); return { t: s.t || 0, I_d: q[0], V_ds: q[1], V_gs: p.Vgs, V_rd: q[0] * p.Rd, gm: fet.gm(p) }; },
    measure: function (p) { var q = fet.solve(p); return { I_d: q[0], V_ds: q[1], gm: fet.gm(p) }; }
  };
  function fet_id(p) {
    var vov, a;
    if (p.kind < 0.5) { vov = p.Vgs - p.Vp; a = vov <= 0 ? 0 : p.Idss * vov * vov / (p.Vp * p.Vp); }
    else { vov = p.Vgs - p.Vth; a = vov <= 0 ? 0 : 0.5 * p.kn * vov * vov; }
    return a * (1 + p.lam * p.Vdd) / (1 + a * p.lam * p.Rd);
  }

  // ================================================================================== operational amplifier
  var opamp = {
    PARAMS: { A0: 200000.0, Vsat: 13.5, R1: 1000.0, R2: 1e9, R3: 1e9, Rf: 10000.0, Ra: 0.0, Rb: 1e9,
      V1: 0.0, V2: 0.0, V3: 0.0, V4: 0.0, open: 0.0 },
    VARS: ['t', 'V_o', 'V_n', 'V_p', 'V_1', 'V_2', 'V_3', 'V_4', 'sat'],
    solve: function (p) {
      var vp = p.V4 * p.Rb / Math.max(p.Ra + p.Rb, 1e-12), raw, gi, g, s, vo;
      if (p.open >= 0.5) { raw = p.A0 * (vp - p.V1); return [clamp(raw, -p.Vsat, p.Vsat), p.V1, vp]; }
      gi = 1 / p.R1 + 1 / p.R2 + 1 / p.R3;
      g = gi + 1 / p.Rf;
      s = p.V1 / p.R1 + p.V2 / p.R2 + p.V3 / p.R3;
      vo = (vp * g - s) / (1 / p.Rf + g / p.A0);
      if (Math.abs(vo) > p.Vsat) { vo = vo > 0 ? p.Vsat : -p.Vsat; return [vo, (s + vo / p.Rf) / g, vp]; }
      return [vo, vp - vo / p.A0, vp];
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var q = opamp.solve(p);
      return { t: s.t || 0, V_o: q[0], V_n: q[1], V_p: q[2], V_1: p.V1, V_2: p.V2, V_3: p.V3, V_4: p.V4,
        sat: Math.abs(q[0]) >= p.Vsat - 1e-9 ? 1 : 0 }; },
    measure: function (p) { var q = opamp.solve(p); return { V_o: q[0], V_n: q[1], V_p: q[2] }; }
  };
  function opamp_vo(p) {
    var vp = p.V4 * p.Rb / Math.max(p.Ra + p.Rb, 1e-12), gi, s;
    if (p.open >= 0.5) return clamp(p.A0 * (vp - p.V1), -p.Vsat, p.Vsat);
    gi = 1 / p.R1 + 1 / p.R2 + 1 / p.R3;
    s = p.V1 / p.R1 + p.V2 / p.R2 + p.V3 / p.R3;
    return clamp(vp * (1 + p.Rf * gi) - p.Rf * s, -p.Vsat, p.Vsat);
  }

  // ================================================================================== Zener shunt regulator
  var zenreg = {
    PARAMS: { Vin: 12.0, Rs: 470.0, Vz: 5.1, Rz: 7.0, RL: 1000.0, Is: 5e-9, knee: 0.02 },
    VARS: ['t', 'V_o', 'I_z', 'I_s', 'I_L', 'V_Rs', 'P_z'],
    iz: function (v, p) { var u = v - p.Vz; return (u + Math.sqrt(u * u + p.knee * p.knee)) / (2 * p.Rz) + p.Is; },
    solve: function (p) {
      var lo = 0, hi = Math.max(p.Vin, 0), i, mid;
      for (i = 0; i < 100; i++) { mid = (lo + hi) / 2;
        if ((mid - p.Vin) / p.Rs + zenreg.iz(mid, p) + mid / p.RL > 0) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var vo = zenreg.solve(p), iz = zenreg.iz(vo, p), il = vo / p.RL;
      return { t: s.t || 0, V_o: vo, I_z: iz, I_L: il, I_s: iz + il, V_Rs: p.Vin - vo, P_z: vo * iz }; },
    measure: function (p) { var vo = zenreg.solve(p); return { V_o: vo, I_z: zenreg.iz(vo, p), I_L: vo / p.RL }; }
  };
  function zenreg_vo(p) { return (p.Vin / p.Rs + p.Vz / p.Rz) / (1 / p.Rs + 1 / p.Rz + 1 / p.RL); }

  // ================================================================================== solar cell
  var solar = {
    PARAMS: { Iph: 0.12, Is: 1e-9, nD: 1.3, ns: 1.0, Rser: 0.3, Rsh: 10000.0, RL: 10.0 },
    VARS: ['t', 'V_o', 'I_o', 'P_o', 'R_L'],
    diode: function (vj, p) { return p.Is * (Math.exp(Math.min(vj / (p.ns * p.nD * VT), 80)) - 1); },
    i_at: function (v, p) {
      var lo = -(p.Iph + 1), hi = p.Iph + 1, i, mid, vj;
      for (i = 0; i < 70; i++) { mid = (lo + hi) / 2; vj = v + mid * p.Rser;
        if (mid + solar.diode(vj, p) + vj / p.Rsh - p.Iph > 0) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    },
    on_load: function (p) {
      var lo = 0, hi = p.Iph + 1, i, mid, vj;
      for (i = 0; i < 70; i++) { mid = (lo + hi) / 2; vj = mid * (p.RL + p.Rser);
        if (mid + solar.diode(vj, p) + vj / p.Rsh - p.Iph > 0) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    },
    voc: function (p) {
      var lo = 0, hi = 5 * Math.max(p.ns, 1), i, mid;
      for (i = 0; i < 100; i++) { mid = (lo + hi) / 2; if (solar.i_at(mid, p) < 0) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var i = solar.on_load(p), v = i * p.RL;
      return { t: s.t || 0, V_o: v, I_o: i, P_o: v * i, R_L: p.RL }; },
    measure: function (p) {
      var isc = solar.i_at(0, p), voc = solar.voc(p), lo = 0, hi = voc, i, a1, a2, vm, im, pm;
      for (i = 0; i < 100; i++) { a1 = lo + (hi - lo) / 3; a2 = hi - (hi - lo) / 3;
        if (a1 * solar.i_at(a1, p) < a2 * solar.i_at(a2, p)) lo = a1; else hi = a2; }
      vm = (lo + hi) / 2; im = solar.i_at(vm, p); pm = vm * im;
      return { I_sc: isc, V_oc: voc, V_m: vm, I_m: im, P_m: pm, FF: isc * voc > 0 ? pm / (isc * voc) : 0 };
    }
  };
  function solar_voc(p) { return p.ns * p.nD * VT * Math.log(p.Iph / p.Is + 1); }

  // ================================================================================== rectifier + filter
  var rect = {
    PARAMS: { Vp: 12.0, f: 50.0, kind: 2.0, C: 0.0, RL: 1000.0, Vd: 0.7, Rs: 1.0 },
    VARS: ['t', 'V_in', 'V_rect', 'V_o', 'I_L'],
    drops: function (p) { return p.kind >= 2.5 ? 2 : 1; },
    vrect: function (t, p) {
      var v = p.Vp * Math.sin(2 * PI * p.f * t);
      if (p.kind < 1.5) return v - p.Vd;
      return Math.abs(v) - rect.drops(p) * p.Vd;
    },
    h: function (p) { return 1 / (Math.max(p.f, 1e-6) * NS); },
    out: function (t, vo, p) {
      if (p.C > 0) return vo;
      var vr = rect.vrect(t, p);
      return vr > 0 ? vr * p.RL / (p.RL + p.Rs) : 0;
    },
    init: function () { return { t: 0, vo: 0 }; },
    step: function (s, p, dt) {
      var h = rect.h(p), n = Math.max(1, Math.ceil(dt / h - 1e-9)), hh = dt / n, i, vr, idio;
      for (i = 0; i < n; i++) {
        if (p.C > 0) {
          vr = rect.vrect(s.t, p);
          idio = Math.max(0, (vr - s.vo) / p.Rs);
          s.vo = Math.max(0, s.vo + hh * (idio - s.vo / p.RL) / p.C);
        }
        s.t += hh;
      }
    },
    view: function (s, p) { var vo = rect.out(s.t, s.vo || 0, p);
      return { t: s.t, V_in: p.Vp * Math.sin(2 * PI * p.f * s.t), V_rect: rect.vrect(s.t, p), V_o: vo, I_L: vo / p.RL }; },
    measure: function (p) {
      var h = rect.h(p), s = rect.init(), i, su = 0, sq = 0, mx = -1e30, mn = 1e30, v, vdc, vrms, vac;
      for (i = 0; i < CYC * NS; i++) rect.step(s, p, h);
      for (i = 0; i < NS; i++) {
        v = rect.out(s.t, s.vo, p);
        su += v; sq += v * v;
        if (v > mx) mx = v;
        if (v < mn) mn = v;
        rect.step(s, p, h);
      }
      vdc = su / NS; vrms = Math.sqrt(sq / NS); vac = Math.sqrt(Math.max(0, vrms * vrms - vdc * vdc));
      return { V_dc: vdc, V_rms: vrms, V_ac: vac, V_pp: mx - mn, ripple: vdc > 0 ? vac / vdc : 0 };
    }
  };
  function rect_vdc(p) { return p.kind < 1.5 ? p.Vp / PI : 2 * p.Vp / PI; }

  // ================================================================================== digital logic
  function nand(a, b) { return 1 - a * b; }
  function gnot(a) { return nand(a, a); }
  function gand(a, b) { var n = nand(a, b); return nand(n, n); }
  function gor(a, b) { return nand(gnot(a), gnot(b)); }
  function gxor(a, b) { var n1 = nand(a, b); return nand(nand(a, n1), nand(b, n1)); }

  var logic_gate = {
    PARAMS: { A: 0.0, B: 0.0, fn: 4.0, Vcc: 5.0 },
    VARS: ['t', 'Y', 'n1', 'n2', 'n3', 'n4', 'A_in', 'B_in'],
    nodes: function (p) {
      var a = bit(p.A), b = bit(p.B), fn = Math.round(p.fn), n1 = 0, n2 = 0, n3 = 0, n4 = 0, y;
      if (fn === 1) { n1 = nand(a, a); y = n1; }
      else if (fn === 2) { n1 = nand(a, b); n2 = nand(n1, n1); y = n2; }
      else if (fn === 3) { n1 = nand(a, a); n2 = nand(b, b); n3 = nand(n1, n2); y = n3; }
      else if (fn === 5) { n1 = nand(a, b); y = n1; }
      else if (fn === 6) { n1 = nand(a, a); n2 = nand(b, b); n3 = nand(n1, n2); n4 = nand(n3, n3); y = n4; }
      else if (fn === 7) { n1 = nand(a, b); n2 = nand(a, n1); n3 = nand(b, n1); n4 = nand(n2, n3); y = nand(n4, n4); }
      else { n1 = nand(a, b); n2 = nand(a, n1); n3 = nand(b, n1); n4 = nand(n2, n3); y = n4; }
      return { Y: y, n1: n1, n2: n2, n3: n3, n4: n4, A_in: a, B_in: b };
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var o = logic_gate.nodes(p); o.t = s.t || 0; return o; },
    measure: function (p) { var n = logic_gate.nodes(p); return { Y: n.Y, n1: n.n1, n4: n.n4 }; }
  };
  function logic_y(p) {
    var a = bit(p.A), b = bit(p.B), fn = Math.round(p.fn);
    if (fn === 1) return 1 - a;
    if (fn === 2) return a * b;
    if (fn === 3) return (a || b) ? 1 : 0;
    if (fn === 5) return 1 - a * b;
    if (fn === 6) return (a || b) ? 0 : 1;
    if (fn === 7) return a === b ? 1 : 0;
    return a !== b ? 1 : 0;
  }

  var logic_arith = {
    PARAMS: { A: 0.0, B: 0.0, Cin: 0.0, fn: 1.0, An: 0.0, Bn: 0.0 },
    VARS: ['t', 'S', 'Cout', 'D', 'Bout', 'SUM', 'value', 'A_in', 'B_in', 'Cin_in'],
    nodes: function (p) {
      var a = bit(p.A), b = bit(p.B), c = bit(p.Cin), fn = Math.round(p.fn);
      var s = 0, co = 0, d = 0, bo = 0, sm = 0, value, s1, c1, x, an, bn, carry, i, ai, bi, si;
      if (fn === 1) { s = gxor(a, b); co = gand(a, b); value = s + 2 * co; }
      else if (fn === 2) { s1 = gxor(a, b); c1 = gand(a, b); s = gxor(s1, c); co = gor(c1, gand(s1, c)); value = s + 2 * co; }
      else if (fn === 3) { d = gxor(a, b); bo = gand(gnot(a), b); value = d - 2 * bo; }
      else if (fn === 4) { x = gxor(a, b); d = gxor(x, c); bo = gor(gand(gnot(x), c), gand(gnot(a), b)); value = d - 2 * bo; }
      else {
        an = Math.round(p.An); bn = Math.round(p.Bn); carry = c;
        for (i = 0; i < 4; i++) {
          ai = (an >> i) & 1; bi = (bn >> i) & 1;
          s1 = gxor(ai, bi); c1 = gand(ai, bi);
          si = gxor(s1, carry);
          carry = gor(c1, gand(s1, carry));
          sm += si << i;
        }
        co = carry; s = sm & 1; value = sm + 16 * co;
      }
      return { S: s, Cout: co, D: d, Bout: bo, SUM: sm, value: value, A_in: a, B_in: b, Cin_in: c };
    },
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var o = logic_arith.nodes(p); o.t = s.t || 0; return o; },
    measure: function (p) { return logic_arith.nodes(p); }
  };
  function arith_value(p) {
    var a = bit(p.A), b = bit(p.B), c = bit(p.Cin), fn = Math.round(p.fn);
    if (fn === 1 || fn === 2) return a + b + (fn === 2 ? c : 0);
    if (fn === 3 || fn === 4) return a - b - (fn === 4 ? c : 0);
    return Math.round(p.An) + Math.round(p.Bn) + c;
  }

  // ================================================================================== learner's tables
  function rowsOf(rs, keys) {
    var out = [], i, j, v, vals, ok;
    for (i = 0; i < rs.length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rs[i][keys[j]];
        if (typeof v !== 'number' || !isFinite(v)) { ok = false; break; }
        vals.push(+v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function slope(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, den;
    if (n < 2) return 0;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    den = n * sxx - sx * sx;
    return den === 0 ? 0 : (n * sxy - sx * sy) / den;
  }
  function calc_fet_vp(rs) {
    var raw = rowsOf(rs, ['Vgs', 'Id']), pts = [], i, m, n, mx = 0, my = 0;
    for (i = 0; i < raw.length; i++) pts.push([raw[i][0], Math.sqrt(Math.max(raw[i][1], 0))]);
    m = slope(pts);
    if (m === 0 || pts.length < 2) return 0;
    n = pts.length;
    for (i = 0; i < n; i++) { mx += pts[i][0]; my += pts[i][1]; }
    mx /= n; my /= n;
    return mx - my / m;
  }
  function calc_opamp_gain(rs) { return slope(rowsOf(rs, ['Vin', 'Vout'])); }
  function calc_line_reg(rs) { return 1000 * slope(rowsOf(rs, ['Vin', 'Vo'])); }
  function calc_solar_ff(rs) {
    var pts = rowsOf(rs, ['V', 'I']), i, isc = 0, voc = 0, pm = 0;
    if (!pts.length) return 0;
    for (i = 0; i < pts.length; i++) { if (pts[i][1] > isc) isc = pts[i][1]; if (pts[i][0] > voc) voc = pts[i][0]; }
    for (i = 0; i < pts.length; i++) pm = Math.max(pm, pts[i][0] * pts[i][1]);
    return isc * voc > 0 ? pm / (isc * voc) : 0;
  }
  function calc_ripple(rs) {
    var pts = rowsOf(rs, ['Vdc', 'Vac']), i, vals = [], tot = 0;
    for (i = 0; i < pts.length; i++) if (pts[i][0] !== 0) vals.push(pts[i][1] / pts[i][0]);
    if (!vals.length) return 0;
    for (i = 0; i < vals.length; i++) tot += vals[i];
    return tot / vals.length;
  }
  function calc_truth_sig(rs) {
    var pts = rowsOf(rs, ['Y']), i, tot = 0;
    for (i = 0; i < pts.length; i++) tot += (pts[i][0] >= 0.5 ? 1 : 0) * Math.pow(2, i);
    return tot;
  }

  H.register({
    K: { fet: fet, opamp: opamp, zenreg: zenreg, solar: solar, rectifier: rect,
      logic_gate: logic_gate, logic_arith: logic_arith },
    TEXTBOOK: { fet_id: fet_id, opamp_vo: opamp_vo, zenreg_vo: zenreg_vo, solar_voc: solar_voc,
      rect_vdc: rect_vdc, logic_y: logic_y, arith_value: arith_value },
    CALCS: {
      fet_vp: { label: 'V_P', unit: 'V', needs: ['Vgs', 'Id'], fn: calc_fet_vp },
      opamp_gain: { label: 'gain', unit: '', needs: ['Vin', 'Vout'], fn: calc_opamp_gain },
      zen_line_reg: { label: 'line regulation', unit: 'mV/V', needs: ['Vin', 'Vo'], fn: calc_line_reg },
      solar_ff: { label: 'fill factor', unit: '', needs: ['V', 'I'], fn: calc_solar_ff },
      rect_ripple: { label: 'ripple factor', unit: '', needs: ['Vdc', 'Vac'], fn: calc_ripple },
      truth_sig: { label: 'truth-table signature', unit: '', needs: ['Y'], fn: calc_truth_sig }
    }
  });
})(typeof window !== 'undefined' ? window : this);
