/* Kernel pack `engine_ug`: the exact JavaScript twin of app/prayog/packs/engine_ug.py. Same formulas, same
   algorithms, same numbers (the server's tests run both and compare). Three engines:
   1. a two-element ray tracer, surface by surface with vector Snell / reflection (eng_lensmirror, eng_twolens,
      eng_liquid);
   2. an AC phasor engine: R, L, C in series / parallel as complex impedance, with a time-domain trace for the
      oscilloscope, and a current-carrying sonometer wire driven at the mains frequency (eng_acphasor, eng_acsono);
   3. gate-level clocked logic stepped in unit gate delays: flip-flops, a ripple counter and a shift register built
      from NAND gates (eng_ff, eng_count, eng_shift).
   Deterministic: fixed-count bisection, fixed steps, no randomness, no wall clock. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels || (typeof require !== 'undefined' ? require('../kernels.js') : null);
  var PI = Math.PI, TMIN = 1e-9;

  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; if (b) for (k in b) o[k] = b[k]; return o; }
  function sqrt(x) { return Math.sqrt(x); }

  // ================================================================================== the surface tracer
  function unit(v) { var L = sqrt(v[0] * v[0] + v[1] * v[1]); return L > 0 ? [v[0] / L, v[1] / L] : [0, 0]; }
  function refract(d, nrm, n1, n2) {
    var cosi = -(d[0] * nrm[0] + d[1] * nrm[1]), r = n1 / n2, k = 1 - r * r * (1 - cosi * cosi), ct;
    if (k < 0) return null;
    ct = sqrt(k);
    return [r * d[0] + (r * cosi - ct) * nrm[0], r * d[1] + (r * cosi - ct) * nrm[1]];
  }
  function meet(p1, d1, p2, d2) {
    var den = d1[0] * d2[1] - d1[1] * d2[0], t;
    if (Math.abs(den) < 1e-18) return null;
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den;
    return [p1[0] + t * d1[0], p1[1] + t * d1[1]];
  }
  function surf(vx, R, nl, nr, mirror) { return { vx: vx, R: R, nl: nl, nr: nr, m: !!mirror }; }
  function lens(cx, R1, R2, n, d) { return [surf(cx - d / 2, R1, 1.0, n, false), surf(cx + d / 2, R2, n, 1.0, false)]; }
  function hit(o, d, s) {
    var vx = s.vx, R = s.R, cx, ox, oy, bq, cq, disc, sq, best = null, bx = 0, ts, i, t, x;
    if (R === 0) {
      if (Math.abs(d[0]) < 1e-15) return null;
      t = (vx - o[0]) / d[0];
      return t > TMIN ? t : null;
    }
    cx = vx + R; ox = o[0] - cx; oy = o[1];
    bq = ox * d[0] + oy * d[1]; cq = ox * ox + oy * oy - R * R; disc = bq * bq - cq;
    if (disc < 0) return null;
    sq = sqrt(disc); ts = [-bq - sq, -bq + sq];
    for (i = 0; i < 2; i++) {
      t = ts[i];
      if (t > TMIN) {
        x = o[0] + t * d[0];
        if (best === null || Math.abs(x - vx) < Math.abs(bx - vx)) { best = t; bx = x; }
      }
    }
    return best;
  }
  function trace(surfs, o, d) {
    var pts = [[o[0], o[1]]], i = -1, step = 1, n = surfs.length, it, s, t, nrm, dot, n1, n2;
    for (it = 0; it < 40; it++) {
      i += step;
      if (i < 0 || i >= n) break;
      s = surfs[i];
      t = hit(o, d, s);
      if (t === null) return null;
      o = [o[0] + t * d[0], o[1] + t * d[1]];
      pts.push([o[0], o[1]]);
      if (s.R === 0) nrm = [d[0] > 0 ? -1.0 : 1.0, 0.0];
      else {
        nrm = unit([o[0] - (s.vx + s.R), o[1]]);
        if (nrm[0] * d[0] + nrm[1] * d[1] > 0) nrm = [-nrm[0], -nrm[1]];
      }
      if (s.m) {
        dot = d[0] * nrm[0] + d[1] * nrm[1];
        d = [d[0] - 2 * dot * nrm[0], d[1] - 2 * dot * nrm[1]];
        step = -step;
      } else {
        if (step > 0) { n1 = s.nl; n2 = s.nr; } else { n1 = s.nr; n2 = s.nl; }
        d = refract(d, nrm, n1, n2);
        if (d === null) return null;
      }
    }
    return [pts, d];
  }
  function image(surfs, xo, h, aim) {
    var x0 = surfs[0].vx, ra, rb;
    if (aim === undefined) aim = 1e-4;
    ra = trace(surfs, [xo, h], unit([x0 - xo, aim - h]));
    rb = trace(surfs, [xo, h], unit([x0 - xo, -aim - h]));
    if (ra === null || rb === null) return null;
    return meet(ra[0][ra[0].length - 1], ra[1], rb[0][rb[0].length - 1], rb[1]);
  }
  function sharpOf(scr, imgx, ok) {
    if (!ok) return 0.0;
    var q = (scr - imgx) / 0.004;
    return 1 / (1 + q * q);
  }
  function draw(surfs, xo, h, aims, L) {
    var out = [], x0 = surfs[0].vx, i, r, pts, d, end, k, q;
    for (i = 0; i < aims.length; i++) {
      r = trace(surfs, [xo, h], unit([x0 - xo, aims[i] - h]));
      if (r === null) continue;
      pts = r[0]; d = r[1];
      end = [pts[pts.length - 1][0] + L * d[0], pts[pts.length - 1][1] + L * d[1]];
      q = [];
      for (k = 0; k < pts.length; k++) q.push([pts[k][0], pts[k][1]]);
      q.push(end);
      out.push({ p: q, v: 0 });
    }
    return out;
  }
  function bisect(f, lo, hi, n) {
    var flo = f(lo), mid, fm, i;
    if (n === undefined) n = 70;
    for (i = 0; i < n; i++) {
      mid = (lo + hi) / 2; fm = f(mid);
      if ((fm > 0) === (flo > 0)) { lo = mid; flo = fm; } else hi = mid;
    }
    return (lo + hi) / 2;
  }
  function rimOf(p) { return sqrt(Math.max(p.R * p.d - p.d * p.d / 4, 0.0)) * 0.8; }

  // ================================================================================== lens + mirror
  var LensMirror = {
    PARAMS: { R: 0.15, n: 1.5168, d: 0.003, u: 0.30, h: 0.003, a: 0.08, Rm: 0.20, convex: 1.0, mir: 0.0, scr: 0.28 },
    VARS: ['rays', 'img_x', 'img_y', 'coin', 'v_lens', 'real', 'sharp'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    surfs: function (p, withMirror) {
      var sf = lens(0.0, p.R, -p.R, p.n, p.d), Rs;
      if (withMirror) { Rs = p.convex >= 0.5 ? p.Rm : -p.Rm; sf.push(surf(p.a, Rs, 1.0, 1.0, true)); }
      return sf;
    },
    view: function (s, p) {
      var withM = p.mir >= 0.5, sf = LensMirror.surfs(p, withM), im = image(sf, -p.u, p.h);
      var im0 = image(LensMirror.surfs(p, false), -p.u, p.h), ok = im !== null, rim = rimOf(p);
      var rays = draw(sf, -p.u, p.h, [rim, 0.0, -rim], 1.2);
      var vLens = im0 ? im0[0] : 0.0, real0 = !!(im0 && im0[0] > 0), ix, iy, coin, real, sharp;
      if (withM) {
        ix = ok ? im[0] : 0.0; iy = ok ? im[1] : 0.0;
        coin = ok ? ix - (-p.u) : 9.0;
        real = (ok && ix < 0) ? 1.0 : 0.0;
        sharp = ok ? 1 / (1 + (coin / 0.004) * (coin / 0.004)) : 0.0;
      } else {
        ix = im0 ? im0[0] : 0.0; iy = im0 ? im0[1] : 0.0;
        coin = 9.0; real = real0 ? 1.0 : 0.0; sharp = sharpOf(p.scr, ix, real0);
      }
      return { rays: rays, img_x: ix, img_y: iy, coin: coin, v_lens: vLens, real: real, sharp: sharp };
    },
    measure: function (p) {
      var q = assign(p, { h: 0.002, mir: 1.0 }), im0 = image(LensMirror.surfs(q, false), -q.u, q.h), v, a0 = null, aPrev, gPrev, k, aNow, gNow;
      if (im0 === null || im0[0] <= 0.03) return { v: 0.0, a: 0.0, R_est: 0.0, f_est: 0.0 };
      v = im0[0];
      function g(a) {
        var qq = assign(q, { a: a }), im = image(LensMirror.surfs(qq, true), -qq.u, qq.h);
        return im ? (im[0] + qq.u) : 9.0;
      }
      aPrev = 0.02; gPrev = g(0.02); k = 1;
      while (0.02 + k * 0.002 < v - 0.004) {
        aNow = 0.02 + k * 0.002; gNow = g(aNow);
        if (gPrev !== 9.0 && gNow !== 9.0 && (gPrev > 0) !== (gNow > 0)) { a0 = bisect(g, aPrev, aNow); break; }
        aPrev = aNow; gPrev = gNow; k++;
      }
      if (a0 === null) return { v: v, a: 0.0, R_est: 0.0, f_est: 0.0 };
      return { v: v, a: a0, R_est: v - a0, f_est: (v - a0) / 2 };
    }
  };

  // ================================================================================== two lenses
  var TwoLens = {
    PARAMS: { R: 0.15, n: 1.5168, d: 0.002, u: 0.30, h: 0.003, a: 0.13, R2: 0.30, d2: 0.0006, n2: 1.5168, mir: 0.0, scr: 0.45 },
    VARS: ['rays', 'img_x', 'img_y', 'real', 'v1', 'sharp'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    surfs: function (p, withL2) {
      var sf = lens(0.0, p.R, -p.R, p.n, p.d);
      if (withL2) sf = sf.concat(lens(p.a, -p.R2, p.R2, p.n2, p.d2));
      return sf;
    },
    view: function (s, p) {
      var withL2 = p.mir >= 0.5, sf = TwoLens.surfs(p, withL2), im = image(sf, -p.u, p.h);
      var im0 = image(TwoLens.surfs(p, false), -p.u, p.h), rim = rimOf(p);
      var rays = draw(sf, -p.u, p.h, [rim, 0.0, -rim], 1.0);
      var v1 = im0 ? im0[0] : 0.0, ix = im ? im[0] : 0.0, iy = im ? im[1] : 0.0;
      var real = !!(im && ix > (withL2 ? p.a : 0.0));
      return { rays: rays, img_x: ix, img_y: iy, real: real ? 1.0 : 0.0, v1: v1, sharp: sharpOf(p.scr, ix, real) };
    },
    measure: function (p) {
      var q = assign(p, { h: 0.002, mir: 1.0 }), im0 = image(TwoLens.surfs(q, false), -q.u, q.h), im = image(TwoLens.surfs(q, true), -q.u, q.h), u2, v2, den;
      if (im0 === null || im === null) return { v1: 0.0, v2: 0.0, f2: 0.0 };
      u2 = im0[0] - q.a; v2 = im[0] - q.a; den = u2 - v2;
      return { v1: im0[0], v2: v2, f2: Math.abs(den) > 1e-12 ? u2 * v2 / den : 0.0 };
    }
  };

  // ================================================================================== a liquid layer
  var Liquid = {
    PARAMS: { mode: 0.0, R: 0.15, n: 1.5168, d: 0.003, nl: 1.333, liq: 0.0, H: 0.15, h: 0.003, t: 0.003 },
    VARS: ['rays', 'img_x', 'img_y', 'coin', 'real'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    surfs: function (p, liq) {
      var on = liq === undefined || liq === null ? p.liq >= 0.5 : liq, nl = on ? p.nl : 1.0, sf;
      if (p.mode < 0.5) {
        sf = lens(0.0, p.R, -p.R, p.n, p.d);
        sf[1].nr = nl;
        sf.push(surf(p.d / 2, 0.0, nl, nl, true));
        return sf;
      }
      return [surf(0.0, 0.0, 1.0, nl, false), surf(p.t, -p.R, nl, nl, true)];
    },
    view: function (s, p) {
      var sf = Liquid.surfs(p), im = image(sf, -p.H, p.h);
      var rays = draw(sf, -p.H, p.h, p.mode < 0.5 ? [0.01, 0.0, -0.01] : [0.012, 0.0, -0.012], 0.6);
      var ok = im !== null, ix = ok ? im[0] : 0.0, iy = ok ? im[1] : 0.0;
      return { rays: rays, img_x: ix, img_y: iy, coin: ok ? (ix + p.H) : 9.0, real: (ok && ix < 0) ? 1.0 : 0.0 };
    },
    coincide: function (p, liq, lo, hi) {
      var q = assign(p, { h: 0.002 });
      function g(Hh) { var im = image(Liquid.surfs(q, liq), -Hh, q.h); return im ? (im[0] + Hh) : 9.0; }
      return bisect(g, lo, hi);
    },
    measure: function (p) {
      var Fg, Hd, Hl, nl;
      if (p.mode < 0.5) {
        Fg = p.R / (2 * (p.n - 1));
        Hd = Liquid.coincide(p, false, 0.75 * Fg, 1.5 * Fg);
        Hl = Liquid.coincide(p, true, Hd, 3.0 * Hd);
        nl = 1 + 2 * (p.n - 1) * (1 - Hd / Hl);
      } else {
        Hd = Liquid.coincide(p, false, 0.58 * p.R, 1.15 * p.R);
        Hl = Liquid.coincide(p, true, 0.58 * p.R, 1.15 * p.R);
        nl = Hd / Hl;
      }
      return { H_dry: Hd, H_liq: Hl, nl: nl };
    }
  };

  // ================================================================================== AC phasor engine
  function cmul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function cdiv(a, b) { var den = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / den, (a[1] * b[0] - a[0] * b[1]) / den]; }
  function cabs(a) { return sqrt(a[0] * a[0] + a[1] * a[1]); }
  function lc(p) { return p.L * (p.core >= 0.5 ? p.kfe : 1.0); }

  var AcPhasor = {
    PARAMS: { topo: 0.0, V: 6.0, f: 50.0, R: 0.0, L: 0.1, C: 1e-6, r: 5.0, Rin: 0.0, core: 0.0, kfe: 1.0 },
    VARS: ['Zmag', 'phi', 'I', 'Vcoil', 'Vx', 'VR', 'pf', 'tt', 'vs', 'ic', 'vx'],
    NS: 200,
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    solve: function (p, f) {
      var w = 2 * PI * f, V = [p.V, 0.0], Lc = lc(p), zc = [p.r, w * Lc], topo = Math.round(p.topo), zC, Z, I, zp, vp;
      if (topo === 0) {
        zC = p.C > 0 ? [0.0, -1.0 / (w * p.C)] : [0.0, 0.0];
        Z = [p.R + p.r + zC[0], w * Lc + zC[1]];
        I = cdiv(V, Z);
        return [Z, I, cmul(I, zc), cmul(I, zC), [p.R * I[0], p.R * I[1]]];
      }
      if (topo === 1) {
        zC = [0.0, -1.0 / (w * p.C)];
        zp = cdiv(cmul(zc, zC), [zc[0] + zC[0], zc[1] + zC[1]]);
        Z = [p.Rin + zp[0], zp[1]];
        I = cdiv(V, Z);
        vp = cmul(I, zp);
        return [Z, I, vp, vp, [p.Rin * I[0], p.Rin * I[1]]];
      }
      Z = [p.r, w * Lc];
      I = cdiv(V, Z);
      return [Z, I, cmul(I, zc), cmul(I, zc), [0.0, 0.0]];
    },
    view: function (s, p) {
      var sol = AcPhasor.solve(p, p.f), Z = sol[0], I = sol[1], vcoil = sol[2], vx = sol[3], vr = sol[4];
      var w = 2 * PI * p.f, n = AcPhasor.NS, T = 1.0 / p.f, tt = [], vs = [], ii = [], vxx = [], k, t, c, sn, Zm;
      for (k = 0; k < n; k++) {
        t = 2 * T * k / n; c = Math.cos(w * t); sn = Math.sin(w * t);
        tt.push(t); vs.push(p.V * c); ii.push(I[0] * c - I[1] * sn); vxx.push(vx[0] * c - vx[1] * sn);
      }
      Zm = cabs(Z);
      return { Zmag: Zm, phi: Math.atan2(Z[1], Z[0]), I: cabs(I), Vcoil: cabs(vcoil), Vx: cabs(vx), VR: cabs(vr),
        pf: Zm > 0 ? Z[0] / Zm : 0.0, tt: tt, vs: vs, ic: ii, vx: vxx };
    },
    peak: function (ph) {
      var m = 0.0, n = 2000, k, th, y;
      for (k = 0; k < n; k++) {
        th = 2 * PI * k / n; y = Math.abs(ph[0] * Math.cos(th) - ph[1] * Math.sin(th));
        if (y > m) m = y;
      }
      return m;
    },
    measure: function (p) {
      var topo = Math.round(p.topo), sol, Zs, w, Lest, fg, f0, half, fl, fh, bw;
      if (topo === 2) {
        sol = AcPhasor.solve(p, p.f);
        Zs = AcPhasor.peak([p.V, 0.0]) / AcPhasor.peak(sol[1]);
        w = 2 * PI * p.f;
        Lest = sqrt(Math.max(Zs * Zs - p.r * p.r, 0.0)) / w;
        return { Z: Zs, L_est: Lest, f0: 0.0, Q: 0.0, bw: 0.0 };
      }
      fg = 1.0 / (2 * PI * sqrt(lc(p) * p.C));
      function zim(f) { return AcPhasor.solve(p, f)[0][1]; }
      function resp(f) { var s2 = AcPhasor.solve(p, f); return topo === 1 ? cabs(s2[0]) : cabs(s2[1]); }
      f0 = bisect(zim, fg * 0.2, fg * 5.0, 90);
      half = resp(f0) / sqrt(2.0);
      fl = bisect(function (f) { return resp(f) - half; }, f0 / 3.0, f0);
      fh = bisect(function (f) { return resp(f) - half; }, f0, f0 * 3.0);
      bw = fh - fl;
      return { Z: 0.0, L_est: 0.0, f0: f0, Q: bw > 0 ? f0 / bw : 0.0, bw: bw };
    }
  };

  var AcSono = {
    PARAMS: { mu: 0.00147, M: 0.5, l: 0.5, fm: 49.93, V: 6.0, Rh: 5.0, Rw: 0.1, B: 0.05, w: 0.03, Q: 40.0, g: 9.80665 },
    VARS: ['amp', 'I', 'fn', 'T'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    amp: function (p, l) {
      var T = p.M * p.g, v = sqrt(T / p.mu), Z = [p.Rh + p.Rw, 0.0], I = cabs(cdiv([p.V * sqrt(2.0), 0.0], Z));
      var F0 = p.B * I * p.w, meff = p.mu * l / 2, w = 2 * PI * p.fm, re = 0.0, im = 0.0, ks = [1, 3], i, k, wn, a, b, den;
      for (i = 0; i < 2; i++) {
        k = ks[i]; wn = k * PI * v / l; a = wn * wn - w * w; b = w * wn / p.Q; den = a * a + b * b;
        re += a / den; im += -b / den;
      }
      return [(F0 / meff) * sqrt(re * re + im * im), I, v / (2 * l), T];
    },
    view: function (s, p) { var r = AcSono.amp(p, p.l); return { amp: r[0], I: r[1], fn: r[2], T: r[3] }; },
    measure: function (p) {
      var lo = 0.15, hi = 0.95, bestL = lo, bestA = -1.0, k, l, a, h = 1e-5, T;
      for (k = 0; k <= 800; k++) { l = lo + (hi - lo) * k / 800.0; a = AcSono.amp(p, l)[0]; if (a > bestA) { bestA = a; bestL = l; } }
      function slope(x) { return AcSono.amp(p, x + h)[0] - AcSono.amp(p, x - h)[0]; }
      l = bisect(slope, bestL - 0.002, bestL + 0.002, 60);
      T = p.M * p.g;
      return { l_res: l, f_est: sqrt(T / p.mu) / (2 * l) };
    }
  };

  // ================================================================================== gate-level logic
  function nand(ins, sig) { var i; for (i = 0; i < ins.length; i++) if (!sig[ins[i]]) return 1; return 0; }
  function settle(gates, sig, maxt) {
    var t, k, nw, changed;
    if (maxt === undefined) maxt = 80;
    for (t = 0; t < maxt; t++) {
      nw = []; changed = false;
      for (k = 0; k < gates.length; k++) nw.push(nand(gates[k][1], sig));
      for (k = 0; k < gates.length; k++) if (sig[gates[k][0]] !== nw[k]) changed = true;
      if (!changed) return [t, true];
      for (k = 0; k < gates.length; k++) sig[gates[k][0]] = nw[k];
    }
    return [maxt, false];
  }
  function ticks(gates, sig, n, watch, log, t0) {
    var last = watch ? watch(sig) : null, t, k, nw, w;
    for (t = 0; t < n; t++) {
      nw = [];
      for (k = 0; k < gates.length; k++) nw.push(nand(gates[k][1], sig));
      for (k = 0; k < gates.length; k++) sig[gates[k][0]] = nw[k];
      if (watch) { w = watch(sig); if (w !== last) { log.push([t0 + t + 1, w]); last = w; } }
    }
  }
  function ffGates(kind) {
    if (kind === 0) return [['Q', ['Sb', 'Qb']], ['Qb', ['Rb', 'Q']]];
    if (kind === 1) return [['a', ['S', 'CK']], ['b', ['R', 'CK']], ['Q', ['a', 'Qb']], ['Qb', ['b', 'Q']]];
    if (kind === 2) return [['nd', ['D', 'D']], ['a', ['D', 'CK']], ['b', ['nd', 'CK']], ['Q', ['a', 'Qb']], ['Qb', ['b', 'Q']]];
    if (kind === 3) return [['a', ['J', 'CK', 'Qb']], ['b', ['K', 'CK', 'Q']], ['Q', ['a', 'Qb']], ['Qb', ['b', 'Q']]];
    return [['nck', ['CK', 'CK']],
      ['ma', ['J', 'CK', 'Qb']], ['mb', ['K', 'CK', 'Q']], ['M', ['ma', 'Mb']], ['Mb', ['mb', 'M']],
      ['sa', ['M', 'nck']], ['sb', ['Mb', 'nck']], ['Q', ['sa', 'Qb']], ['Qb', ['sb', 'Q']]];
  }
  function ffInputs(kind, a, b) {
    if (kind === 0) return { Sb: a, Rb: b };
    if (kind === 1) return { S: a, R: b };
    if (kind === 2) return { D: a };
    return { J: a, K: b };
  }
  function ffSignals(kind, q, a, b, ck) {
    var sig = { CK: ck, Q: q, Qb: 1 - q }, ins = ffInputs(kind, a, b), k, g = ffGates(kind);
    for (k in ins) sig[k] = ins[k];
    for (k = 0; k < g.length; k++) if (sig[g[k][0]] === undefined) sig[g[k][0]] = 1;
    if (kind === 4) { sig.M = q; sig.Mb = 1 - q; }
    return sig;
  }
  function upd(sig, o) { var k; for (k in o) sig[k] = o[k]; }

  var FlipFlop = {
    PARAMS: { kind: 1.0, a: 0.0, b: 0.0, q0: 0.0, tw: 24.0 },
    VARS: ['Q', 'Qb', 'osc', 'toggles', 'a_n', 'b_n', 'M', 'ck'],
    init: function (p) {
      var kind = Math.round(p.kind), a = kind === 0 ? 1 : Math.round(p.a), b = kind === 0 ? 1 : Math.round(p.b);
      var sig = ffSignals(kind, Math.round(p.q0), a, b, 0);
      settle(ffGates(kind), sig);
      return { t: 0, sig: sig, toggles: 0, osc: 0 };
    },
    step: function (s, p, dt) { s.t += dt; },
    force: function (s, p, q) {
      var kind = Math.round(p.kind), sg = s.sig;
      sg.Q = q; sg.Qb = 1 - q;
      if (kind === 4) { sg.M = q; sg.Mb = 1 - q; }
      settle(ffGates(kind), sg);
    },
    drive: function (s, p, a, b) {
      var kind = Math.round(p.kind), r;
      upd(s.sig, ffInputs(kind, Math.round(a), Math.round(b)));
      r = settle(ffGates(kind), s.sig);
      s.osc = r[1] ? 0 : 1;
      return r[1];
    },
    clock: function (s, p) {
      var kind = Math.round(p.kind), g = ffGates(kind), sg = s.sig, tw = Math.round(p.tw), log = [], r;
      sg.CK = 1;
      ticks(g, sg, tw, function (x) { return x.Q; }, log, 0);
      sg.CK = 0;
      r = settle(g, sg);
      s.osc = r[1] ? 0 : 1;
      s.toggles = log.length;
      return { toggles: log.length, settled: r[1] ? 1.0 : 0.0 };
    },
    view: function (s, p) {
      var sg = s.sig, kind = Math.round(p.kind);
      var a = ['Sb', 'S', 'D', 'J', 'J'][kind], b = ['Rb', 'R', 'D', 'K', 'K'][kind];
      return { Q: +sg.Q, Qb: +sg.Qb, osc: +(s.osc || 0), toggles: +(s.toggles || 0), a_n: +sg[a], b_n: +sg[b],
        M: sg.M === undefined ? +sg.Q : +sg.M, ck: +sg.CK };
    },
    valid: function (kind, a, b) {
      if (kind === 0) return !(a === 0 && b === 0);
      if (kind === 1 || kind === 3) return !(a === 1 && b === 1);
      return true;
    },
    measure: function (p) {
      var kind = Math.round(p.kind), sig = 0, idx = 0, a, b, q0, q, st;
      for (a = 0; a < 2; a++) for (b = 0; b < 2; b++) for (q0 = 0; q0 < 2; q0++) {
        if (!(kind === 2 && b === 1) && FlipFlop.valid(kind, a, b)) {
          q = assign(p, { a: a, b: b, q0: q0 });
          st = FlipFlop.init(q);
          FlipFlop.drive(st, q, a, b);
          if (kind !== 0) FlipFlop.clock(st, q);
          sig += st.sig.Q * Math.pow(2, idx);
        }
        idx++;
      }
      return { sig: +sig };
    }
  };

  function countGates(nst, down) {
    var gates = [], k, c, P;
    for (k = 0; k < nst; k++) {
      c = k === 0 ? 'CK' : (!down ? 'Q' + (k - 1) : 'Qb' + (k - 1));
      P = '' + k;
      gates.push(['nck' + P, [c, c]], ['ma' + P, ['J', c, 'Qb' + P]], ['mb' + P, ['J', c, 'Q' + P]],
        ['M' + P, ['ma' + P, 'Mb' + P]], ['Mb' + P, ['mb' + P, 'M' + P]],
        ['sa' + P, ['M' + P, 'nck' + P]], ['sb' + P, ['Mb' + P, 'nck' + P]],
        ['Q' + P, ['sa' + P, 'Qb' + P]], ['Qb' + P, ['sb' + P, 'Q' + P]]);
    }
    return gates;
  }
  function countWord(sig, nst) { var s = 0, k; for (k = 0; k < nst; k++) s += sig['Q' + k] * (1 << k); return s; }

  var Counter = {
    PARAMS: { down: 0.0, tw: 40.0, tl: 60.0 },
    VARS: ['word', 'Q0', 'Q1', 'Q2', 'Q3', 'ripple', 'glitch', 'ck'],
    NST: 4,
    resetSig: function (p) {
      var sig = { CK: 0, J: 1 }, k, P, nm, names = ['nck', 'ma', 'mb', 'sa', 'sb'], i;
      for (k = 0; k < Counter.NST; k++) {
        P = '' + k;
        sig['Q' + P] = 0; sig['Qb' + P] = 1; sig['M' + P] = 0; sig['Mb' + P] = 1;
        for (i = 0; i < names.length; i++) { nm = names[i]; sig[nm + P] = 1; }
      }
      settle(countGates(Counter.NST, Math.round(p.down)), sig);
      return sig;
    },
    init: function (p) { return { t: 0, sig: Counter.resetSig(p), events: [], n: 0, start: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    reset: function (s, p) { s.sig = Counter.resetSig(p); s.events = []; s.n = 0; s.start = 0; },
    clock: function (s, p) {
      var n = Counter.NST, g = countGates(n, Math.round(p.down)), sg = s.sig, log = [];
      function wd(x) { return countWord(x, n); }
      s.start = countWord(sg, n);
      sg.CK = 1;
      ticks(g, sg, Math.round(p.tw), wd, log, 0);
      sg.CK = 0;
      ticks(g, sg, Math.round(p.tl), wd, log, Math.round(p.tw));
      s.events = log; s.n += 1;
      return { events: log, word: +countWord(sg, n) };
    },
    view: function (s, p) {
      var sg = s.sig, ev = s.events || [], word = countWord(sg, Counter.NST), out, k, first, c = 0;
      out = { word: +word, ripple: +ev.length, glitch: 0.0, ck: +sg.CK };
      for (k = 0; k < Counter.NST; k++) out['Q' + k] = +sg['Q' + k];
      if (ev.length) {
        first = s.start || 0;
        for (k = 0; k < ev.length - 1; k++) if (ev[k][1] !== first && ev[k][1] !== word) c++;
        out.glitch = +c;
      }
      return out;
    },
    measure: function (p) {
      var st = Counter.init(p), tot = 0, k;
      for (k = 0; k < 16; k++) { Counter.clock(st, p); tot += (k + 1) * countWord(st.sig, Counter.NST); }
      return { sum: +tot };
    }
  };

  function dffGates(P, d, ck) {
    return [['n1' + P, ['n4' + P, 'n2' + P]], ['n2' + P, ['n1' + P, ck]],
      ['n3' + P, ['n2' + P, ck, 'n4' + P]], ['n4' + P, ['n3' + P, d]],
      ['Q' + P, ['n2' + P, 'Qb' + P]], ['Qb' + P, ['Q' + P, 'n3' + P]]];
  }
  function shiftGates(nst) {
    var gates = [], k;
    for (k = 0; k < nst; k++) gates = gates.concat(dffGates('' + k, k === 0 ? 'SI' : 'Q' + (k - 1), 'CK'));
    return gates;
  }
  var Shift = {
    PARAMS: { si: 0.0, word: 11.0, tw: 30.0 },
    VARS: ['word_out', 'Q0', 'Q1', 'Q2', 'Q3', 'ck', 'si'],
    NST: 4,
    init: function (p) {
      var sig = { CK: 0, SI: Math.round(p.si) }, k, P;
      for (k = 0; k < Shift.NST; k++) {
        P = '' + k;
        sig['Q' + P] = 0; sig['Qb' + P] = 1; sig['n1' + P] = 1; sig['n2' + P] = 1; sig['n3' + P] = 1; sig['n4' + P] = 1;
      }
      settle(shiftGates(Shift.NST), sig);
      return { t: 0, sig: sig };
    },
    step: function (s, p, dt) { s.t += dt; },
    drive: function (s, p, si) { s.sig.SI = Math.round(si); settle(shiftGates(Shift.NST), s.sig); },
    clock: function (s, p) {
      var g = shiftGates(Shift.NST), sg = s.sig;
      sg.CK = 1;
      ticks(g, sg, Math.round(p.tw), null, null, 0);
      sg.CK = 0;
      settle(g, sg);
      return { word: +Shift.word(sg) };
    },
    word: function (sg) { var s = 0, k; for (k = 0; k < Shift.NST; k++) s += sg['Q' + k] * (1 << k); return s; },
    view: function (s, p) {
      var sg = s.sig, out = { word_out: +Shift.word(sg), ck: +sg.CK, si: +sg.SI }, k;
      for (k = 0; k < Shift.NST; k++) out['Q' + k] = +sg['Q' + k];
      return out;
    },
    measure: function (p) {
      var st = Shift.init(p), w = Math.round(p.word) & 15, k;
      for (k = 0; k < Shift.NST; k++) { Shift.drive(st, p, (w >> (Shift.NST - 1 - k)) & 1); Shift.clock(st, p); }
      return { word: +Shift.word(st.sig) };
    }
  };

  // ================================================================================== textbook formulas
  function ffNext(kind, a, b, q) {
    if (kind === 0) return (a && b) ? q : (!a ? 1 : 0);
    if (kind === 1) return a ? 1 : (!b ? q : 0);
    if (kind === 2) return a;
    return (a && (1 - q)) || ((1 - b) && q);
  }
  function ffSig(p) {
    var kind = Math.round(p.kind), tot = 0, idx = 0, a, b, q0;
    for (a = 0; a < 2; a++) for (b = 0; b < 2; b++) for (q0 = 0; q0 < 2; q0++) {
      if (!(kind === 2 && b === 1) && FlipFlop.valid(kind, a, b)) tot += (ffNext(kind, a, b, q0) ? 1 : 0) * Math.pow(2, idx);
      idx++;
    }
    return +tot;
  }
  function countSum(p) {
    var down = Math.round(p.down), tot = 0, k, w;
    for (k = 0; k < 16; k++) { w = !down ? (k + 1) % 16 : (((-(k + 1)) % 16) + 16) % 16; tot += (k + 1) * w; }
    return +tot;
  }
  var TEXTBOOK = {
    eng_lensmirror_f: function (p) { return p.Rm / 2; },
    eng_twolens_f2: function (p) { return -p.R2 / (2 * (p.n2 - 1)); },
    eng_liquid_nl: function (p) { return p.nl; },
    eng_coil_L: lc,
    eng_series_f0: function (p) { return 1.0 / (2 * PI * sqrt(lc(p) * p.C)); },
    eng_series_Q: function (p) { return sqrt(lc(p) / p.C) / (p.R + p.r); },
    eng_sono_f: function (p) { return p.fm; },
    eng_ff_sig: ffSig,
    eng_count_sum: countSum,
    eng_shift_word: function (p) { return +(Math.round(p.word) & 15); }
  };

  // ================================================================================== results from a table
  function rowsOf(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rs[i][keys[j]];
        if (v === undefined || v === null || v === '' || !isFinite(+v)) { ok = false; break; }
        vals.push(+v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mean(xs) { var s = 0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0; }
  function coilL(r, p) {
    var vals = [];
    rowsOf(r, ['V', 'I', 'r']).forEach(function (x) {
      var Z;
      if (x[1] > 0 && p.f > 0) { Z = x[0] / x[1]; vals.push(sqrt(Math.max(Z * Z - x[2] * x[2], 0.0)) / (2 * PI * p.f)); }
    });
    return mean(vals);
  }
  function sonoF(r, p) {
    var vals = [];
    rowsOf(r, ['l', 'M']).forEach(function (x) { if (x[0] > 0 && x[1] > 0) vals.push(sqrt(x[1] * p.g / p.mu) / (2 * x[0])); });
    return mean(vals);
  }
  function lmF(r) { return mean(rowsOf(r, ['v', 'a']).map(function (x) { return (x[0] - x[1]) / 2; })); }
  function tlF(r) {
    var vals = [];
    rowsOf(r, ['v1', 'a', 'xi']).forEach(function (x) { var u2 = x[0] - x[1], v2 = x[2] - x[1]; if (Math.abs(u2 - v2) > 1e-9) vals.push(u2 * v2 / (u2 - v2)); });
    return mean(vals);
  }
  function liqN(r, p) {
    var vals = [];
    rowsOf(r, ['Hd', 'Hl']).forEach(function (x) { if (x[1] > 0) vals.push(p.mode < 0.5 ? 1 + 2 * (p.n - 1) * (1 - x[0] / x[1]) : x[0] / x[1]); });
    return mean(vals);
  }
  var CALCS = {
    eng_coil_L: { label: 'L', unit: 'H', needs: ['V', 'I', 'r'], fn: coilL },
    eng_sono_f: { label: 'f of the mains', unit: 'Hz', needs: ['l', 'M'], fn: sonoF },
    eng_lm_f: { label: 'f of the mirror', unit: 'm', needs: ['v', 'a'], fn: lmF },
    eng_tl_f: { label: 'f of the concave lens', unit: 'm', needs: ['v1', 'a', 'xi'], fn: tlF },
    eng_liq_n: { label: 'n of the liquid', unit: '', needs: ['Hd', 'Hl'], fn: liqN }
  };

  H.register({
    K: { eng_lensmirror: LensMirror, eng_twolens: TwoLens, eng_liquid: Liquid, eng_acphasor: AcPhasor, eng_acsono: AcSono,
      eng_ff: FlipFlop, eng_count: Counter, eng_shift: Shift },
    CALCS: CALCS, TEXTBOOK: TEXTBOOK
  });
})(typeof window !== 'undefined' ? window : this);
