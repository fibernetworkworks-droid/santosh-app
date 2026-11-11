/* Kernel pack (browser twin of app/prayog/packs/ug_matter_w8.py): B.Sc. nuclear / radiation physics and solid
   state physics, wave 8. Same formulas, same order of operations, so both sides give the same numbers.
     um8_beta    N = N0 exp(-mu_m x) up to the Katz-Penfold range R = 0.412 E^(1.265 - 0.0954 ln E), mu_m = 17 E^-1.14
     um8_k40     A = m f_K N_A theta ln2 / (M_K T_half), counted with the tray efficiency
     um8_ion     Bethe-Bloch (PDG form, no shell / density corrections) with the Barkas effective charge; CSDA range
     um8_xrd     Bragg 2 d sin(theta) = lambda, Scherrer L = K lambda / (beta cos theta)
     um8_revsat  I_s = C T^3 exp(-Eg / (k T))
   Counting is Poisson from the lab's own seed: SIMULATED DATA. No randomness drawn from the system, no wall clock. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI, LN2 = Math.log(2.0), NA = 6.02214076e23, KB_EV = 8.617333262e-5, YEAR = 3.15576e7;
  var ME = 0.51099895, AMU = 931.49410242, KBB = 0.307075, MU0 = 1.25663706212e-6;

  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) { v = Number(rs[i][keys[j]]); if (rs[i][keys[j]] === null || rs[i][keys[j]] === undefined || !isFinite(v)) { ok = false; break; } vals.push(v); }
      if (ok) out.push(vals);
    }
    return out;
  }
  function linfit(pts) {
    var n = pts.length, sx = 0, sy = 0, sxx = 0, sxy = 0, i, den, m;
    if (n < 2) return null;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxx += pts[i][0] * pts[i][0]; sxy += pts[i][0] * pts[i][1]; }
    den = n * sxx - sx * sx;
    if (Math.abs(den) < 1e-300) return null;
    m = (n * sxy - sx * sy) / den;
    return [m, (sy - m * sx) / n];
  }
  function copy(p) { var q = {}, k; for (k in p) if (Object.prototype.hasOwnProperty.call(p, k)) q[k] = p[k]; return q; }
  function Rnd(seed) { var s = Math.floor(Math.abs(seed)) % 2147483646; this.s = s + 1; }
  Rnd.prototype.next = function () { this.s = (this.s * 16807) % 2147483647; return this.s / 2147483647; };
  Rnd.prototype.poisson = function (m) {
    if (m <= 0) return 0;
    if (m > 400) { var kk = Math.floor(m / 400) + 1, total = 0, j;
      for (j = 0; j < kk; j++) total += this.poisson(m / kk);
      return total; }
    var lim = Math.exp(-m), k = 0, p = 1;
    for (;;) { p *= this.next(); if (p <= lim) return k; k += 1; if (k > 100000) return k; }
  };

  // ------------------------------------------------------------------ beta absorption
  var BetaAbsorb = {
    PARAMS: { x: 0.0, E: 0.7637, N0: 400.0, brem: 0.4, bg: 0.5, tau: 2.5e-4, t: 100.0, seed: 17.0, rho: 2.699 },
    VARS: ['t', 'rate', 'net', 'x_mg'],
    rangeKP: function (E) { return 0.412 * Math.pow(E, 1.265 - 0.0954 * Math.log(E)); },
    muM: function (E) { return 17.0 * Math.pow(E, -1.14); },
    betaRate: function (p) { var x = Math.max(p.x, 0.0); if (x >= BetaAbsorb.rangeKP(p.E)) return 0.0;
      return p.N0 * Math.exp(-BetaAbsorb.muM(p.E) * x); },
    trueRate: function (p) { return p.bg + p.brem + BetaAbsorb.betaRate(p); },
    obsRate: function (p) { var r = BetaAbsorb.trueRate(p); return r / (1.0 + r * p.tau); },
    counts: function (p, k) { var rnd = new Rnd(p.seed + 977.0 * (k || 0)); return rnd.poisson(BetaAbsorb.obsRate(p) * Math.max(p.t, 0.0)); },
    endPoint: function (p) { var lo = 0.0, hi = 5.0, i, mid, q;
      for (i = 0; i < 200; i++) { mid = (lo + hi) / 2; q = copy(p); q.x = mid; if (BetaAbsorb.betaRate(q) > 0) lo = mid; else hi = mid; }
      return (lo + hi) / 2; },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, rate: BetaAbsorb.obsRate(p), net: BetaAbsorb.betaRate(p), x_mg: p.x * 1000.0 }; },
    measure: function (p) { return { R: BetaAbsorb.endPoint(p), mu: BetaAbsorb.muM(p.E), rate: BetaAbsorb.obsRate(p) }; },
  };

  // ------------------------------------------------------------------ potassium-40 in a salt
  var K40Salt = {
    PARAMS: { m: 0.1, fK: 0.52445, MK: 39.0983, ab: 1.17e-4, T12: 1.248e9, br: 0.8928, eff: 0.002, bg: 0.45, tau: 2.5e-4, t: 600.0, seed: 29.0, on: 1.0 },
    VARS: ['t', 'A', 'beta', 'net', 'rate'],
    activity: function (p) { var nk = p.m * 1000.0 * p.fK / p.MK * NA * p.ab; return nk * LN2 / (p.T12 * YEAR); },
    netRate: function (p) { return K40Salt.activity(p) * p.br * p.eff * (p.on > 0.5 ? 1.0 : 0.0); },
    obsRate: function (p) { var r = p.bg + K40Salt.netRate(p); return r / (1.0 + r * p.tau); },
    counts: function (p, k) { var rnd = new Rnd(p.seed + 977.0 * (k || 0)); return rnd.poisson(K40Salt.obsRate(p) * Math.max(p.t, 0.0)); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, A: K40Salt.activity(p), beta: K40Salt.activity(p) * p.br, net: K40Salt.netRate(p), rate: K40Salt.obsRate(p) }; },
    measure: function (p) { var q = copy(p); q.on = 1.0; var a = K40Salt.activity(q);
      return { net: K40Salt.netRate(q), A: a, specific: a / (q.m * 1000.0 * q.fK) }; },
  };

  // ------------------------------------------------------------------ stopping of ions (Bethe-Bloch)
  var IonStop = {
    PARAMS: { mode: 0.0, z: 1.0, Mu: 1.007276, E: 10.0, ZA: 0.55508, I: 75.0, rho: 1.0, n: 20.0, Ec: 1.0, nref: 4000.0 },
    VARS: ['t', 'S', 'dEdx', 'R', 'zeff', 'beta'],
    kin: function (E, Mu) { var M = Mu * AMU, g = 1.0 + E * Mu / M, b2 = 1.0 - 1.0 / (g * g); return [g, b2, M]; },
    zeff: function (z, b2) { return z * (1.0 - Math.exp(-125.0 * Math.sqrt(b2) * Math.pow(z, -2.0 / 3.0))); },
    S: function (E, p) {
      var k = IonStop.kin(E, p.Mu), g = k[0], b2 = k[1], M = k[2], r = ME / M;
      var tmax = 2.0 * ME * b2 * g * g / (1.0 + 2.0 * g * r + r * r), Imev = p.I * 1e-6;
      var L = 0.5 * Math.log(2.0 * ME * b2 * g * g * tmax / (Imev * Imev)) - b2, ze = IonStop.zeff(p.z, b2);
      return KBB * ze * ze * p.ZA / b2 * L;
    },
    rangeN: function (p, n) {
      n = Math.max(1, Math.round(n));
      var a = Math.log(p.Ec), b = Math.log(p.E), h = (b - a) / n, total = 0.0, i, e;
      for (i = 0; i < n; i++) { e = Math.exp(a + (i + 0.5) * h); total += e * h * p.Mu / IonStop.S(e, p); }
      return total;
    },
    sMin: function (p) {
      var lo = Math.log(50.0), hi = Math.log(1.0e5), gr = (Math.sqrt(5.0) - 1.0) / 2.0, i, a, b, e;
      for (i = 0; i < 200; i++) { a = hi - gr * (hi - lo); b = lo + gr * (hi - lo);
        if (IonStop.S(Math.exp(a), p) < IonStop.S(Math.exp(b), p)) hi = b; else lo = a; }
      e = Math.exp((lo + hi) / 2);
      return [e, IonStop.S(e, p)];
    },
    bragg: function (p, n) {
      n = Math.max(4, Math.round(n));
      var R = IonStop.rangeN(p, p.nref), dx = R / n, e = p.E, x = 0.0, out = [], i, s, e1, s1;
      for (i = 0; i < 4 * n; i++) {
        if (e <= p.Ec) break;
        s = IonStop.S(e, p);
        out.push([x, s]);
        e1 = e - 0.5 * dx * s / p.Mu;
        if (e1 <= p.Ec) { x += (e - p.Ec) * p.Mu / s; e = p.Ec; break; }
        s1 = IonStop.S(e1, p);
        e = e - dx * s1 / p.Mu;
        x += dx;
      }
      return out;
    },
    stopDepth: function (p, n) {
      n = Math.max(4, Math.round(n));
      var R = IonStop.rangeN(p, p.nref), dx = R / n, e = p.E, x = 0.0, i, s, e1, s1, e2;
      for (i = 0; i < 4 * n; i++) {
        if (e <= p.Ec) break;
        s = IonStop.S(e, p);
        e1 = e - 0.5 * dx * s / p.Mu;
        if (e1 <= p.Ec) { x += (e - p.Ec) * p.Mu / s; break; }
        s1 = IonStop.S(e1, p);
        e2 = e - dx * s1 / p.Mu;
        if (e2 <= p.Ec) { x += (e - p.Ec) * p.Mu / s1; break; }
        e = e2;
        x += dx;
      }
      return x;
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var k = IonStop.kin(p.E, p.Mu), S = IonStop.S(p.E, p);
      return { t: s.t || 0.0, S: S, dEdx: S * p.rho, R: IonStop.rangeN(p, p.n), zeff: IonStop.zeff(p.z, k[1]), beta: Math.sqrt(k[1]) }; },
    measure: function (p) { var k = IonStop.kin(p.E, p.Mu), sm = IonStop.sMin(p);
      return { S: IonStop.S(p.E, p), R: IonStop.rangeN(p, p.nref), Rn: IonStop.rangeN(p, p.n), zeff: IonStop.zeff(p.z, k[1]),
        Smin: sm[1], Emin: sm[0], depth: IonStop.stopDepth(p, p.n) }; },
  };

  // ------------------------------------------------------------------ X-ray powder diffraction
  function mod(a, b) { return ((a % b) + b) % b; }
  var PowderXRD = {
    PARAMS: { tth: 30.0, lam: 1.5406e-10, a: 3.6149e-10, c: 0.0, lat: 2.0, L: 4.0e-8, K: 0.9, binst: 0.08, I0: 1000.0, bg: 20.0, ph: 1.0, pk: 1.0, pl: 1.0 },
    VARS: ['t', 'I', 'tth'],
    allowed: function (h, k, l, lat) {
      if (lat === 1) return mod(h + k + l, 2) === 0;
      if (lat === 2) return mod(h, 2) === mod(k, 2) && mod(k, 2) === mod(l, 2);
      if (lat === 3) { if (!(mod(h, 2) === mod(k, 2) && mod(k, 2) === mod(l, 2))) return false;
        if (mod(h, 2) === 1) return true; return mod(h + k + l, 4) === 0; }
      if (lat === 4) return !(mod(h - k, 3) === 0 && mod(l, 2) === 1);
      if (lat === 5) {                                 // I4_1/amd (anatase)
        if (mod(h + k + l, 2) !== 0) return false;
        if (l === 0 && (mod(h, 2) !== 0 || mod(k, 2) !== 0)) return false;
        if (h === 0 && mod(k + l, 2) !== 0) return false;
        if (h === k && mod(2 * h + l, 4) !== 0) return false;
        if (h === 0 && k === 0 && mod(l, 4) !== 0) return false;
        return true;
      }
      if (lat === 6) {                                 // R-3c in hexagonal axes (hematite)
        if (mod(-h + k + l, 3) !== 0) return false;
        if ((h === 0 || k === 0) && mod(l, 2) !== 0) return false;
        if (h === 0 && k === 0 && mod(l, 6) !== 0) return false;
        return true;
      }
      return true;
    },
    dsp: function (h, k, l, p) {
      var lat = Math.round(p.lat), a = p.a, c;
      if (lat <= 3) return a / Math.sqrt(h * h + k * k + l * l);
      c = p.c;
      if (lat === 5) return 1.0 / Math.sqrt((h * h + k * k) / (a * a) + l * l / (c * c));
      return 1.0 / Math.sqrt(4.0 / 3.0 * (h * h + h * k + k * k) / (a * a) + l * l / (c * c));
    },
    lines: function (p, lo, hi) {
      if (lo === undefined) lo = 15.0;
      if (hi === undefined) hi = 100.0;
      var lat = Math.round(p.lat), seen = {}, order = [], hmax = lat <= 3 ? 6 : 4, lmax = lat <= 3 ? 6 : 16, h, k, l, d, sn, tth, key, th, lp, out, top, i;
      for (h = 0; h <= hmax; h++) for (k = 0; k <= hmax; k++) {
        if (lat <= 3 && k > h) continue;
        for (l = 0; l <= lmax; l++) {
          if (lat <= 3 && l > k) continue;
          if (h === 0 && k === 0 && l === 0) continue;
          if (!PowderXRD.allowed(h, k, l, lat)) continue;
          d = PowderXRD.dsp(h, k, l, p); sn = p.lam / (2.0 * d);
          if (sn >= 1.0) continue;
          tth = 2.0 * Math.asin(sn) * 180.0 / PI;
          if (tth < lo || tth > hi) continue;
          key = 'k' + String(Math.round(d * 1e14));
          th = tth / 2.0 * PI / 180.0;
          lp = (1.0 + Math.pow(Math.cos(2 * th), 2)) / (Math.pow(Math.sin(th), 2) * Math.cos(th));
          if (seen[key]) { seen[key][1] += lp; continue; }
          seen[key] = [tth, lp, h, k, l, h * h + k * k + l * l]; order.push(key);
        }
      }
      out = order.map(function (q) { return seen[q]; }).sort(function (x, y) { return x[0] - y[0]; });
      if (out.length) { top = -Infinity; for (i = 0; i < out.length; i++) if (out[i][1] > top) top = out[i][1];
        for (i = 0; i < out.length; i++) out[i][1] = out[i][1] / top; }
      return out;
    },
    width: function (tth, p) { var th = tth / 2.0 * PI / 180.0, bs = p.K * p.lam / (p.L * Math.cos(th)) * 180.0 / PI;
      return Math.sqrt(bs * bs + p.binst * p.binst); },
    intensity: function (tth, p) {
      var tot = p.bg, ls = PowderXRD.lines(p), i, w, sg, dx;
      for (i = 0; i < ls.length; i++) { w = PowderXRD.width(ls[i][0], p); sg = w / 2.3548200450309493; dx = tth - ls[i][0];
        if (Math.abs(dx) < 8 * w) tot += p.I0 * ls[i][1] * Math.exp(-dx * dx / (2 * sg * sg)); }
      return tot;
    },
    peak: function (p) { var d = PowderXRD.dsp(Math.round(p.ph), Math.round(p.pk), Math.round(p.pl), p);
      return 2.0 * Math.asin(p.lam / (2.0 * d)) * 180.0 / PI; },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { return { t: s.t || 0.0, I: PowderXRD.intensity(p.tth, p), tth: p.tth }; },
    measure: function (p) {
      var t2 = PowderXRD.peak(p), w = PowderXRD.width(t2, p), b = Math.sqrt(Math.max(w * w - p.binst * p.binst, 0.0)) * PI / 180.0, th = t2 / 2.0 * PI / 180.0;
      return { L: p.K * p.lam / (b * Math.cos(th)), tth: t2, fwhm: w,
        a: p.lam / (2.0 * Math.sin(th)) * Math.sqrt(Math.pow(p.ph, 2) + Math.pow(p.pk, 2) + Math.pow(p.pl, 2)) };
    },
  };

  // ------------------------------------------------------------------ reverse saturation current
  var RevSat = {
    PARAMS: { Eg: 0.66, I300: 2.0e-6, Vr: 1.0, T0: 27.0, Tset: 27.0, tau: 120.0 },
    VARS: ['t', 'T', 'I', 'I_uA'],
    iS: function (Tc, p) {
      var T = Tc + 273.15, c = p.I300 / (Math.pow(300.0, 3) * Math.exp(-p.Eg / (KB_EV * 300.0)));
      var v = 1.0 - Math.exp(-Math.max(p.Vr, 0.0) / (KB_EV * T));
      return c * T * T * T * Math.exp(-p.Eg / (KB_EV * T)) * v;
    },
    init: function (p) { return { t: 0.0, T: p.T0 }; },
    step: function (s, p, dt) { s.T = p.Tset + (s.T - p.Tset) * Math.exp(-dt / p.tau); s.t += dt; },
    view: function (s, p) { var i = RevSat.iS(s.T, p); return { t: s.t, T: s.T, I: i, I_uA: i * 1e6 }; },
    measure: function (p) {
      var pts = [], i, Tc, T, f;
      for (i = 0; i < 6; i++) { Tc = 30.0 + 10.0 * i; T = Tc + 273.15; pts.push([1.0 / T, Math.log(RevSat.iS(Tc, p) / (T * T * T))]); }
      f = linfit(pts);
      return { Eg: f ? -f[0] * KB_EV : 0.0, I: RevSat.iS(p.T0, p) };
    },
  };

  // ------------------------------------------------------------------ piezoelectric resonator (BVD circuit)
  var Piezo = {
    PARAMS: { f: 90000.0, fs: 100000.0, C0: 2.0e-9, k: 0.55, R1: 4.0, Rs: 100.0, V0: 1.0 },
    VARS: ['t', 'Vr', 'Z'],
    zabs: function (f, p) {
      var w = 2.0 * PI * f, c1 = p.k * p.k * p.C0 / (1.0 - p.k * p.k), l1 = 1.0 / (Math.pow(2.0 * PI * p.fs, 2) * c1);
      var mr = p.R1, mi = w * l1 - 1.0 / (w * c1), cr = 0.0, ci = -1.0 / (w * p.C0);
      var nr = mr * cr - mi * ci, ni = mr * ci + mi * cr, dr = mr + cr, di = mi + ci, den = dr * dr + di * di;
      var zr = (nr * dr + ni * di) / den, zi = (ni * dr - nr * di) / den, tr = zr + p.Rs, ti = zi;
      return [Math.sqrt(zr * zr + zi * zi), p.V0 * p.Rs / Math.sqrt(tr * tr + ti * ti)];
    },
    extreme: function (p, lo, hi, sign) {
      var gr = (Math.sqrt(5.0) - 1.0) / 2.0, i, a, b;
      for (i = 0; i < 200; i++) { a = hi - gr * (hi - lo); b = lo + gr * (hi - lo);
        if (sign * Piezo.zabs(a, p)[0] < sign * Piezo.zabs(b, p)[0]) hi = b; else lo = a; }
      return (lo + hi) / 2;
    },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var z = Piezo.zabs(p.f, p); return { t: s.t || 0.0, Vr: z[1], Z: z[0] }; },
    measure: function (p) {
      var fa0 = p.fs / Math.sqrt(1.0 - p.k * p.k);
      var fr = Piezo.extreme(p, 0.8 * p.fs, 0.5 * (p.fs + fa0), 1.0), fa = Piezo.extreme(p, 0.5 * (p.fs + fa0), 1.2 * fa0, -1.0);
      return { fr: fr, fa: fa, k: Math.sqrt(1.0 - Math.pow(fr / fa, 2)) };
    },
  };

  // ------------------------------------------------------------------ Gouy balance
  var Gouy = {
    PARAMS: { I: 0.0, kB: 0.25, Bs: 1.2, chim: 1460.0, rho: 1.2, M: 249.68, A: 5.0e-5, chiair: 3.7e-7, g: 9.81, m0: 0.012 },
    VARS: ['t', 'B', 'dm', 'm'],
    field: function (p) { return p.Bs * Math.tanh(p.kB * Math.max(p.I, 0.0) / p.Bs); },
    chiv: function (p) { return 4.0 * PI * p.chim * 1e-6 * p.rho / p.M; },
    dm: function (B, p) { return (Gouy.chiv(p) - p.chiair) * p.A * B * B / (2.0 * MU0 * p.g); },
    init: function () { return { t: 0.0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) { var B = Gouy.field(p), d = Gouy.dm(B, p); return { t: s.t || 0.0, B: B, dm: d, m: p.m0 + d }; },
    measure: function (p) {
      var pts = [], i, q, B, f, sl, chiv;
      for (i = 0; i < 5; i++) { q = copy(p); q.I = 0.5 + 0.5 * i; B = Gouy.field(q); pts.push([B * B, Gouy.dm(B, q)]); }
      f = linfit(pts); sl = f ? f[0] : 0.0;
      chiv = sl * 2.0 * MU0 * p.g / p.A + p.chiair;
      return { chim: chiv * p.M / (4.0 * PI * 1e-6 * p.rho), chiv: chiv };
    },
  };

  function egFit(rs) {
    var pts = rows(rs, ['T', 'I']).filter(function (x) { return x[1] > 0; })
      .map(function (x) { return [1.0 / (x[0] + 273.15), Math.log(x[1] * 1e-6 / Math.pow(x[0] + 273.15, 3))]; });
    var f = linfit(pts); return f ? -f[0] * KB_EV : 0.0;
  }
  function betaMu(rs) {
    var pts = rows(rs, ['xm', 'net']).filter(function (x) { return x[1] > 0; }).map(function (x) { return [x[0], Math.log(x[1])]; });
    var f = linfit(pts); return f ? -f[0] : 0.0;
  }
  function simpsonRange(p) {
    var n = 2000, a = Math.log(p.Ec), b = Math.log(p.E), h = (b - a) / n, tot = 0.0, i, e, f, w;
    for (i = 0; i <= n; i++) { e = Math.exp(a + i * h); f = e * p.Mu / IonStop.S(e, p);
      w = (i === 0 || i === n) ? 1.0 : (i % 2 === 1 ? 4.0 : 2.0); tot += w * f; }
    return tot * h / 3.0;
  }

  HK.register({
    K: { um8_gouy: Gouy, um8_piezo: Piezo, um8_beta: BetaAbsorb, um8_k40: K40Salt, um8_ion: IonStop, um8_xrd: PowderXRD, um8_revsat: RevSat },
    CALCS: {
      um8_eg: { label: 'Eg (band gap)', unit: 'eV', needs: ['T', 'I'], fn: function (r) { return egFit(r); } },
      um8_beta_mu: { label: 'mu_m (mass absorption coefficient)', unit: 'cm²/g', needs: ['xm', 'net'], fn: function (r) { return betaMu(r); } },
    },
    TEXTBOOK: {
      um8_beta_range: function (p) { return 0.412 * Math.pow(p.E, 1.265 - 0.0954 * Math.log(p.E)); },
      um8_k40_net: function (p) { return p.m * 1000.0 * p.fK / p.MK * NA * p.ab * LN2 / (p.T12 * YEAR) * p.br * p.eff; },
      um8_bethe_S: function (p) { return IonStop.S(p.E, p); },
      um8_zeff: function (p) { return p.z * (1.0 - Math.exp(-125.0 * Math.sqrt(IonStop.kin(p.E, p.Mu)[1]) * Math.pow(p.z, -2.0 / 3.0))); },
      um8_csda: function (p) { return simpsonRange(p); },
      um8_scherrer: function (p) { return p.L; },
      um8_eg: function (p) { return p.Eg; },
      um8_keff: function (p) { return p.k; },
      um8_chim: function (p) { return p.chim; },
    },
  });
})(typeof window !== 'undefined' ? window : this);
