/* Kernel pack (browser twin of app/prayog/packs/pg_optics_w9.py): the M.Sc. optics, lasers and spectroscopy bench.
   Same formulas, same order of operations, so both sides give the same numbers. Every kernel is a "set the control,
   read the instrument" set-up with read(p), plan(p) and calc(rows, p); measure(p) = plan -> read -> calc.
     po9_fp       Fabry-Perot rings              po9_zeeman   Zeeman pattern (etalon or Lummer-Gehrcke plate)
     po9_biref    a retarding plate              po9_ellipse  elliptically polarised light
     po9_photoel  photoelastic disc / beam       po9_eo       Kerr and Pockels cells, modulation
     po9_faraday  Faraday rotation               po9_fraun    Fraunhofer diffraction
     po9_cdev     constant deviation drum        po9_rowland  concave grating, Rowland mounting
     po9_band     band heads (Deslandres)        po9_spec     a scanned spectrum
     po9_film     film step (Fizeau, FECO)       po9_stoney   Stoney's equation with Newton's rings
     po9_photom   photometry                     po9_ao       acousto-optics
   Deterministic: no randomness, no wall clock. */
(function (root) {
  'use strict';
  var HK = (root && root.HoolaKernels) ||
    (typeof module !== 'undefined' && module.exports && module.exports.register ? module.exports : null);
  if (!HK) throw new Error('HoolaKernels is not loaded');
  var PI = Math.PI;
  var C_LIGHT = 299792458.0, H_PLANCK = 6.62607015e-34;
  var J1_ZEROS = [3.8317059702075125, 7.015586669815619, 10.173468135062722, 13.323691936314223];
  var SINC2_HALF = 1.3915573144528073;
  var NA_REF = 5.893e-7;
  var HG_CAL = [4.046565e-7, 4.358335e-7, 5.460750e-7];

  function fin(v) { v = Number(v); return isFinite(v) ? v : 0.0; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function rnd(v) { return Math.floor(v + 0.5); }
  function rows(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = rs[i] ? rs[i][keys[j]] : undefined;
        if (v === undefined || v === null || v === '' || typeof v === 'boolean') { ok = false; break; }
        v = Number(v); if (!isFinite(v)) { ok = false; break; } vals.push(v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function mean(xs) { var s = 0.0, i; for (i = 0; i < xs.length; i++) s += xs[i]; return xs.length ? s / xs.length : 0.0; }
  function line(xs, ys) {
    var n = xs.length, sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0, i, den, m;
    if (n < 2) return [0.0, 0.0];
    for (i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; }
    den = n * sxx - sx * sx;
    if (den === 0.0) return [0.0, 0.0];
    m = (n * sxy - sx * sy) / den;
    return [m, (sy - m * sx) / n];
  }
  function sqrt(v) { return v > 0.0 ? Math.sqrt(v) : 0.0; }
  function asin(v) { return Math.asin(clamp(v, -1.0, 1.0)); }
  function ln(v) { return v > 0.0 ? Math.log(v) : 0.0; }
  function sinc2(u) { if (Math.abs(u) < 1e-9) return 1.0; var q = Math.sin(u) / u; return q * q; }
  function jn(n, u) {
    var h = u / 2.0, term = 1.0, tot, k;
    for (k = 1; k <= n; k++) term = term * h / k;
    tot = term;
    for (k = 1; k < 40; k++) { term = -term * h * h / (k * (k + n)); tot += term; }
    return tot;
  }
  function sortedBy(r, i) {
    var out = r.map(function (q) { return q.slice(); }), a, b, q;
    for (a = 1; a < out.length; a++) {
      q = out[a]; b = a - 1;
      while (b >= 0 && out[b][i] > q[i]) { out[b + 1] = out[b]; b -= 1; }
      out[b + 1] = q;
    }
    return out;
  }
  function airy(F, ph) { var s = Math.sin(PI * ph); return 1.0 / (1.0 + F * s * s); }
  function coef(R) { return R < 1.0 ? 4.0 * R / ((1.0 - R) * (1.0 - R)) : 1e9; }
  function col(r, i) { var out = [], k; for (k = 0; k < r.length; k++) out.push(r[k][i]); return out; }
  function merge(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
  function scan(K) {
    K.init = function () { return { t: 0.0 }; };
    K.step = function (s, p, dt) { s.t += dt; };
    K.view = function (s, p) { return K.read(p); };
    K.table = function (p) {
      var pl = K.plan(p), out = [], i;
      for (i = 0; i < pl.length; i++) out.push(merge(pl[i], K.read(merge(p, pl[i]))));
      return out;
    };
    K.measure = function (p) { var r = K.table(p); return { result: fin(K.calc(r, p)), rows: r.length }; };
    return K;
  }

  // ---------------------------------------------------------------------- Fabry-Perot etalon rings
  var Fp = scan({
    PARAMS: { lam: 5.460750e-7, ds: 10.0, w2: 0.6, t: 0.01, f: 0.3, R: 0.9, mode: 0.0, x: 0.004 },
    VARS: ['x', 'I', 'c', 'n'],
    read: function (p) {
      var x = Math.abs(p.x), u = p.f / Math.sqrt(p.f * p.f + x * x), s1 = 1.0 / p.lam, s2 = s1 + p.ds, F = coef(p.R);
      var p1 = 2.0 * p.t * s1 * u, p2 = 2.0 * p.t * s2 * u;
      var I = (airy(F, p1) + p.w2 * airy(F, p2)) / (1.0 + p.w2);
      var d1 = Math.abs(p1 - rnd(p1)), d2 = Math.abs(p2 - rnd(p2));
      var c = (p.w2 > 0.0 && d2 < d1) ? 1.0 : 0.0, ph = c > 0.5 ? p2 : p1;
      var M = Math.floor(2.0 * p.t * s1);
      return { x: p.x, I: I, c: c, n: M - rnd(ph) + 1.0 };
    },
    xr: function (p, s, m) {
      var cs = m / (2.0 * p.t * s);
      if (cs >= 1.0 || cs <= 0.0) return 0.0;
      return p.f * Math.tan(Math.acos(cs));
    },
    plan: function (p) {
      var s1 = 1.0 / p.lam, s2 = s1 + p.ds, M = Math.floor(2.0 * p.t * s1), out, h;
      if (p.mode > 1.5) {
        h = asin(1.0 / sqrt(coef(p.R))) / PI;
        return [{ x: Fp.xr(p, s1, M - 1.0) }, { x: Fp.xr(p, s1, M - 1.0 + h) }, { x: Fp.xr(p, s1, M - 1.0 - h) },
          { x: Fp.xr(p, s1, M - 2.0) }];
      }
      out = [{ x: Fp.xr(p, s1, M) }, { x: Fp.xr(p, s1, M - 1.0) }, { x: Fp.xr(p, s1, M - 2.0) }];
      if (p.mode < 0.5) out = out.concat([{ x: Fp.xr(p, s2, M) }, { x: Fp.xr(p, s2, M - 1.0) }]);
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'c', 'n']), f = p.f, s1 = 1.0 / p.lam, us = [], i, j, q, ring1, ring2, du, w, main, l, ds;
      for (i = 0; i < r.length; i++) { q = r[i]; us.push([f / Math.sqrt(f * f + q[0] * q[0]), q[1], q[2]]); }
      if (p.mode > 1.5) {
        ring1 = us.filter(function (q) { return q[1] < 0.5 && Math.abs(q[2] - 2.0) < 0.5; }).map(function (q) { return q[0]; });
        ring2 = us.filter(function (q) { return q[1] < 0.5 && Math.abs(q[2] - 3.0) < 0.5; }).map(function (q) { return q[0]; });
        if (ring1.length < 3 || !ring2.length) return 0.0;
        ring1 = sortedBy(ring1.map(function (v) { return [v]; }), 0).map(function (q) { return q[0]; });
        du = ring1[1] - mean(ring2);
        w = ring1[ring1.length - 1] - ring1[0];
        return w > 0.0 ? du / w : 0.0;
      }
      main = us.filter(function (q) { return q[1] < 0.5; });
      if (p.mode > 0.5) {
        l = line(col(main, 2), col(main, 0));
        return l[0] < 0.0 ? -1.0 / (2.0 * s1 * l[0]) : 0.0;
      }
      ds = [];
      for (i = 0; i < us.length; i++) {
        q = us[i];
        if (q[1] > 0.5) {
          for (j = 0; j < main.length; j++) {
            if (Math.abs(main[j][2] - q[2]) < 0.5) { ds.push(s1 * (main[j][0] / q[0] - 1.0)); break; }
          }
        }
      }
      return mean(ds);
    },
  });

  // ---------------------------------------------------------------------- Zeeman effect
  function zcomps(p) {
    var out = [], ju = rnd(p.ju), jl = rnd(p.jl), a, b, k, seen, i;
    for (a = -ju; a <= ju; a++) {
      for (b = -jl; b <= jl; b++) {
        if (Math.abs(a - b) > 1) continue;
        if (p.view > 0.5 && a === b) continue;
        k = a * p.gu - b * p.gl;
        k = rnd(k * 1e6) / 1e6;
        seen = false;
        for (i = 0; i < out.length; i++) if (Math.abs(out[i] - k) < 1e-9) seen = true;
        if (!seen) out.push(k);
      }
    }
    return sortedBy(out.map(function (v) { return [v]; }), 0).map(function (q) { return q[0]; });
  }
  var ZALO = 0.02;
  var Zeeman = scan({
    PARAMS: { lam: 5.460750e-7, B: 0.5, em: 1.75882001076e11, gu: 2.0, gl: 1.5, ju: 1.0, jl: 2.0, meth: 0.0, view: 0.0,
      t: 0.003, f: 0.3, R: 0.9, nlg: 1.5168, tl: 0.003, mode: 0.0, x: 0.004 },
    VARS: ['x', 'I', 'c', 'n'],
    dl: function (p) { return p.em * p.B / (4.0 * PI * C_LIGHT); },
    q: function (p, x) {
      if (p.meth > 0.5) { var a = Math.atan(Math.abs(x) / p.f), cs = Math.cos(a); return sqrt(p.nlg * p.nlg - cs * cs); }
      return p.f / Math.sqrt(p.f * p.f + x * x);
    },
    thick: function (p) { return p.meth > 0.5 ? p.tl : p.t; },
    base: function (p, smin) {
      if (p.meth > 0.5) { var cs = Math.cos(ZALO); return Math.ceil(2.0 * p.tl * smin * sqrt(p.nlg * p.nlg - cs * cs)); }
      return Math.floor(2.0 * p.t * smin);
    },
    read: function (p) {
      var ks = zcomps(p), s0 = 1.0 / p.lam, dl = Zeeman.dl(p), qv = Zeeman.q(p, p.x), th = Zeeman.thick(p), F = coef(p.R);
      var I = 0.0, best = 9.0, c = 0.0, phc = 0.0, i, ph, d, M, n;
      for (i = 0; i < ks.length; i++) {
        ph = 2.0 * th * (s0 + ks[i] * dl) * qv;
        I += airy(F, ph);
        d = Math.abs(ph - rnd(ph));
        if (d < best) { best = d; c = i + 1.0; phc = ph; }
      }
      M = ks.length ? Zeeman.base(p, s0 + ks[0] * dl) : 0.0;
      n = p.meth > 0.5 ? (rnd(phc) - M + 1.0) : (M - rnd(phc) + 1.0);
      return { x: p.x, I: I / Math.max(1, ks.length), c: c, n: n };
    },
    xof: function (p, s, m) {
      var g, cc, cs;
      if (p.meth > 0.5) {
        g = m / (2.0 * p.tl * s); cc = p.nlg * p.nlg - g * g;
        if (cc <= 0.0 || cc >= 1.0) return 0.0;
        return p.f * Math.tan(Math.acos(Math.sqrt(cc)));
      }
      cs = m / (2.0 * p.t * s);
      if (cs >= 1.0 || cs <= 0.0) return 0.0;
      return p.f * Math.tan(Math.acos(cs));
    },
    plan: function (p) {
      var ks = zcomps(p), s0, dl, lo, hi, M, st, out = [], j, m;
      if (!ks.length) return [];
      s0 = 1.0 / p.lam; dl = Zeeman.dl(p); lo = s0 + ks[0] * dl; hi = s0 + ks[ks.length - 1] * dl;
      M = Zeeman.base(p, lo); st = p.meth > 0.5 ? 1.0 : -1.0;
      for (j = 0; j < 2; j++) { m = M + st * j; out.push({ x: Zeeman.xof(p, lo, m) }); out.push({ x: Zeeman.xof(p, hi, m) }); }
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'c', 'n']), ks, cmin, cmax, s0, sp = [], i, j, a, b, tot, span, dl;
      if (r.length < 2) return 0.0;
      ks = zcomps(p);
      if (ks.length < 2) return 0.0;
      cmin = r[0][1]; cmax = r[0][1];
      for (i = 0; i < r.length; i++) { cmin = Math.min(cmin, r[i][1]); cmax = Math.max(cmax, r[i][1]); }
      s0 = 1.0 / p.lam;
      for (i = 0; i < r.length; i++) {
        a = r[i];
        if (Math.abs(a[1] - cmin) > 0.5) continue;
        for (j = 0; j < r.length; j++) {
          b = r[j];
          if (Math.abs(b[1] - cmax) < 0.5 && Math.abs(b[2] - a[2]) < 0.5) { sp.push(s0 * (Zeeman.q(p, a[0]) / Zeeman.q(p, b[0]) - 1.0)); break; }
        }
      }
      tot = mean(sp);
      if (tot <= 0.0) return 0.0;
      span = ks[ks.length - 1] - ks[0];
      if (p.mode > 1.5) { dl = p.em * p.B / (4.0 * PI * C_LIGHT); return dl > 0.0 ? tot / dl / 2.0 : 0.0; }
      if (span <= 0.0 || p.B <= 0.0) return 0.0;
      dl = tot / span;
      if (p.mode > 0.5) return H_PLANCK * C_LIGHT * dl / p.B;
      return 4.0 * PI * C_LIGHT * dl / p.B;
    },
  });

  // ---------------------------------------------------------------------- birefringence of a plate
  var Biref = scan({
    PARAMS: { dn: 0.0091, t: 3.0e-5, lam: 5.893e-7, beta: 0.004, x0: 0.005, mode: 0.0, stage: 0.0, A: 0.0, x: 0.005 },
    VARS: ['x', 'A', 'I'],
    delta: function (p) { return 2.0 * PI * p.dn * p.t / p.lam; },
    babinet: function (p) { var m = rnd(p.mode); return m === 0 || m === 2; },
    read: function (p) {
      var d = p.stage > 0.5 ? Biref.delta(p) : 0.0, ph, s, c;
      if (Biref.babinet(p)) { ph = 2.0 * PI * (p.x - p.x0) / p.beta - d; s = Math.sin(ph / 2.0); return { x: p.x, I: s * s }; }
      s = Math.sin(d / 2.0); c = Math.cos(p.A);
      return { x: p.x, I: c * c - Math.cos(2.0 * p.A) * s * s };
    },
    plan: function (p) {
      if (Biref.babinet(p)) return [{ stage: 0.0, x: p.x0 }, { stage: 0.0, x: p.x0 + p.beta }, { stage: 1.0, x: p.x0 + p.beta * Biref.delta(p) / (2.0 * PI) }];
      return [{ stage: 1.0, A: 0.0 }, { stage: 1.0, A: PI / 4.0 }, { stage: 1.0, A: PI / 2.0 }];
    },
    calc: function (rs, p) {
      var r, z, s, beta, d, i0, i9, i, q, tot;
      if (Biref.babinet(p)) {
        r = rows(rs, ['stage', 'x']);
        z = sortedBy(r.filter(function (q) { return q[0] < 0.5; }), 1);
        s = r.filter(function (q) { return q[0] > 0.5; }).map(function (q) { return q[1]; });
        if (z.length < 2 || !s.length) return 0.0;
        beta = z[1][1] - z[0][1];
        if (beta <= 0.0) return 0.0;
        d = 2.0 * PI * (s[0] - z[0][1]) / beta;
      } else {
        r = rows(rs, ['A', 'I']);
        if (r.length < 2) return 0.0;
        i0 = r[0]; i9 = r[0];
        for (i = 0; i < r.length; i++) {
          q = r[i];
          if (Math.abs(q[0]) < Math.abs(i0[0])) i0 = q;
          if (Math.abs(q[0] - PI / 2.0) < Math.abs(i9[0] - PI / 2.0)) i9 = q;
        }
        tot = i0[1] + i9[1];
        if (tot <= 0.0) return 0.0;
        d = 2.0 * asin(sqrt(i9[1] / tot));
      }
      if (rnd(p.mode) >= 2) return d * p.lam / (2.0 * PI);
      return d * p.lam / (2.0 * PI * p.t);
    },
  });

  // ---------------------------------------------------------------------- elliptically polarised light
  function cm(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function ca(a, b) { return [a[0] + b[0], a[1] + b[1]]; }
  function cs(a, k) { return [a[0] * k, a[1] * k]; }
  var Ellipse = scan({
    PARAMS: { del: 1.2, phi: 0.5235987755982988, lam: 5.893e-7, beta: 0.004, x0: 0.005, mode: 0.0, stage: 0.0, A: 0.0, x: 0.0 },
    VARS: ['x', 'I'],
    field: function (p) {
      var c = Math.cos(p.phi), s = Math.sin(p.phi), e = [Math.cos(p.del), Math.sin(p.del)];
      return [[c * c + s * s * e[0], s * s * e[1]], [c * s * (1.0 - e[0]), -c * s * e[1]]];
    },
    stokes: function (ex, ey) {
      var s0 = ex[0] * ex[0] + ex[1] * ex[1] + ey[0] * ey[0] + ey[1] * ey[1];
      var s1 = ex[0] * ex[0] + ex[1] * ex[1] - ey[0] * ey[0] - ey[1] * ey[1];
      var s2 = 2.0 * (ex[0] * ey[0] + ex[1] * ey[1]);
      var s3 = 2.0 * (ex[0] * ey[1] - ex[1] * ey[0]);
      return [s0, s1, s2, s3];
    },
    qwp: function (ex, ey, a) {
      var c = Math.cos(a), s = Math.sin(a);
      var ea = ca(cs(ex, c), cs(ey, s)), eb = ca(cs(ex, -s), cs(ey, c));
      eb = cm(eb, [0.0, 1.0]);
      return [ca(cs(ea, c), cs(eb, -s)), ca(cs(ea, s), cs(eb, c))];
    },
    ana: function (ex, ey, th) { var a = ca(cs(ex, Math.cos(th)), cs(ey, Math.sin(th))); return a[0] * a[0] + a[1] * a[1]; },
    babinet: function (p) { return rnd(p.mode) >= 2; },
    read: function (p) {
      var d, g, c, s, ar, e2, amp, f, ex, ey, o;
      if (Ellipse.babinet(p)) {
        d = p.stage > 0.5 ? p.del : 0.0; g = 2.0 * PI * (p.x - p.x0) / p.beta;
        c = Math.cos(p.phi); s = Math.sin(p.phi); ar = p.A - p.phi;
        e2 = [-s * Math.cos(d - g), -s * Math.sin(d - g)];
        amp = ca([c * Math.cos(ar), 0.0], cs(e2, Math.sin(ar)));
        return { x: p.x, I: amp[0] * amp[0] + amp[1] * amp[1] };
      }
      f = Ellipse.field(p); ex = f[0]; ey = f[1];
      if (p.stage > 0.5) { o = Ellipse.qwp(ex, ey, Ellipse.truth(p)[0]); ex = o[0]; ey = o[1]; }
      return { x: p.x, I: Ellipse.ana(ex, ey, p.A) };
    },
    truth: function (p) {
      var f = Ellipse.field(p), S = Ellipse.stokes(f[0], f[1]);
      return [0.5 * Math.atan2(S[2], S[1]), 0.5 * asin(S[3] / S[0])];
    },
    plan: function (p) {
      var al, f, o, S, nul;
      if (Ellipse.babinet(p)) return [{ stage: 0.0, A: PI / 2.0, x: p.x0 }, { stage: 0.0, A: PI / 2.0, x: p.x0 + p.beta },
        { stage: 1.0, A: PI / 2.0, x: p.x0 + p.beta * p.del / (2.0 * PI) }];
      al = Ellipse.truth(p)[0]; f = Ellipse.field(p); o = Ellipse.qwp(f[0], f[1], al); S = Ellipse.stokes(o[0], o[1]);
      nul = 0.5 * Math.atan2(S[2], S[1]) + PI / 2.0;
      return [{ stage: 0.0, A: 0.0 }, { stage: 0.0, A: PI / 4.0 }, { stage: 0.0, A: PI / 2.0 },
        { stage: 0.0, A: 3.0 * PI / 4.0 }, { stage: 1.0, A: nul }];
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'A', 'x']), m = rnd(p.mode), z, s, beta, d, psi, chi, ri;
      if (Ellipse.babinet(p)) {
        z = sortedBy(r.filter(function (q) { return q[0] < 0.5; }), 2);
        s = r.filter(function (q) { return q[0] > 0.5; });
        if (z.length < 2 || !s.length) return 0.0;
        beta = z[1][2] - z[0][2];
        if (beta <= 0.0) return 0.0;
        d = 2.0 * PI * (s[0][2] - z[0][2]) / beta;
        if (m === 2) return d;
        psi = Math.abs(s[0][1] - PI / 2.0 - p.phi);
        chi = 0.5 * asin(Math.sin(2.0 * psi) * Math.sin(d));
        return Math.abs(Math.tan(chi));
      }
      ri = rows(rs, ['stage', 'A', 'I']);
      z = ri.filter(function (q) { return q[0] < 0.5; });
      if (z.length < 4) return 0.0;
      var at = function (a) { var best = z[0], k; for (k = 0; k < z.length; k++) if (Math.abs(z[k][1] - a) < Math.abs(best[1] - a)) best = z[k]; return best[2]; };
      var al = 0.5 * Math.atan2(at(PI / 4.0) - at(3.0 * PI / 4.0), at(0.0) - at(PI / 2.0));
      if (m === 1) return al;
      s = ri.filter(function (q) { return q[0] > 0.5; });
      if (!s.length) return 0.0;
      chi = s[0][1] - PI / 2.0 - al;
      while (chi > PI / 2.0) chi -= PI;
      while (chi < -PI / 2.0) chi += PI;
      return Math.abs(Math.tan(chi));
    },
  });

  // ---------------------------------------------------------------------- photoelasticity
  var Photoel = scan({
    PARAMS: { C: 5.5e-11, D: 0.05, hb: 0.012, a: 0.03, lam: 5.461e-7, shape: 0.0, pol: 1.0, mode: 0.0, x: 0.0 },
    VARS: ['x', 'I', 'n'],
    k: function (p) {
      if (p.shape > 0.5) return 3.0 * p.C * p.a / (p.hb * p.hb * p.lam);
      return 8.0 * p.C / (PI * p.D * p.lam);
    },
    read: function (p) { var N = Photoel.k(p) * Math.max(0.0, p.x), s = Math.sin(PI * N); return { x: p.x, I: s * s, n: rnd(N) }; },
    plan: function (p) { var k = Photoel.k(p), out = [{ x: 0.0 }], i; for (i = 1; i < 5; i++) out.push({ x: i / k }); return out; },
    calc: function (rs, p) {
      var r = rows(rs, ['x', 'n']), l, k;
      if (r.length < 3) return 0.0;
      l = line(col(r, 1), col(r, 0));
      if (l[0] <= 0.0) return 0.0;
      k = 1.0 / l[0];
      if (p.mode > 0.5) return k;
      if (p.shape > 0.5) return k * p.hb * p.hb * p.lam / (3.0 * p.a);
      return k * PI * p.D * p.lam / 8.0;
    },
  });

  // ---------------------------------------------------------------------- Kerr and Pockels cells
  var Eo = scan({
    PARAMS: { kind: 0.0, K: 2.4e-12, l: 0.05, d: 0.005, r: 1.06e-11, n: 1.51, L: 0.02, lam: 6.328e-7, fc: 2.0e4, f0: 1.0e3,
      P0: 1.0e-3, mode: 0.0, A: 0.0, x: 0.0 },
    VARS: ['x', 'A', 'P', 'm'],
    vpi: function (p) {
      var k = rnd(p.kind), n3 = p.n * p.n * p.n;
      if (k === 0) return p.d / sqrt(2.0 * p.K * p.l);
      if (k === 1) return p.lam / (2.0 * n3 * p.r);
      return p.lam * p.d / (2.0 * n3 * p.r * p.L);
    },
    gam: function (p, v) { var vp = Eo.vpi(p); if (rnd(p.kind) === 0) return PI * (v / vp) * (v / vp); return PI * v / vp; },
    read: function (p) {
      var m = rnd(p.mode), vm, f, hh, s;
      if (m >= 2) {
        if (m === 2) { vm = p.x; f = p.f0; } else { vm = 0.05 * Eo.vpi(p); f = p.A; }
        hh = 1.0 / Math.sqrt(1.0 + (f / p.fc) * (f / p.fc));
        return { x: p.x, A: p.A, P: 0.5 * p.P0, m: Math.abs(Math.sin(PI * vm * hh / Eo.vpi(p))) };
      }
      s = Math.sin(Eo.gam(p, p.x) / 2.0);
      return { x: p.x, A: p.A, P: p.P0 * s * s, m: 0.0 };
    },
    plan: function (p) {
      var m = rnd(p.mode), vp = Eo.vpi(p), ks;
      if (m === 2) return [0.01, 0.02, 0.03, 0.04, 0.05].map(function (k) { return { x: vp * k }; });
      if (m === 3) return [0.02, 0.25, 0.5, 1.0, 1.5, 2.5].map(function (k) { return { A: p.fc * k }; });
      ks = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2];
      return ks.map(function (k) { return { x: vp * k }; });
    },
    calc: function (rs, p) {
      var m = rnd(p.mode), k = rnd(p.kind), r, l, a0, fs, i, q, h, top, vs, g, vp, n3;
      if (m === 2) {
        r = rows(rs, ['x', 'm']);
        if (r.length < 2) return 0.0;
        l = line(col(r, 0), r.map(function (q) { return asin(q[1]); }));
        return l[0] > 0.0 ? PI / l[0] : 0.0;
      }
      if (m === 3) {
        r = sortedBy(rows(rs, ['A', 'm']), 0);
        if (r.length < 2 || r[0][1] <= 0.0) return 0.0;
        a0 = asin(r[0][1]); fs = [];
        for (i = 0; i < r.length; i++) { q = r[i]; h = asin(q[1]) / a0; if (h > 0.0 && h < 0.99) fs.push(q[0] / Math.sqrt(1.0 / (h * h) - 1.0)); }
        return mean(fs);
      }
      r = rows(rs, ['x', 'P']);
      if (r.length < 2) return 0.0;
      top = r[0];
      for (i = 0; i < r.length; i++) if (r[i][1] > top[1]) top = r[i];
      if (top[1] <= 0.0) return 0.0;
      vs = [];
      for (i = 0; i < r.length; i++) {
        q = r[i];
        if (q[0] > 0.0 && q[0] <= top[0] && q[1] > 0.0) {
          g = 2.0 * asin(sqrt(q[1] / top[1]));
          if (g <= 0.0) continue;
          vs.push(k === 0 ? q[0] * Math.sqrt(PI / g) : q[0] * PI / g);
        }
      }
      vp = mean(vs);
      if (vp <= 0.0) return 0.0;
      if (m === 1) return vp;
      n3 = p.n * p.n * p.n;
      if (k === 0) return p.d * p.d / (2.0 * p.l * vp * vp);
      if (k === 1) return p.lam / (2.0 * n3 * vp);
      return p.lam * p.d / (2.0 * n3 * p.L * vp);
    },
  });

  // ---------------------------------------------------------------------- Faraday rotation
  var Faraday = scan({
    PARAMS: { V: 9.22, l: 0.1, kB: 0.05, lam: 5.893e-7, l0: 4.5e-7, l1: 5.5e-7, l2: 6.5e-7, mode: 0.0, stage: 0.0, A: 0.0,
      x: 1.5707963267948966 },
    VARS: ['x', 'A', 'B', 'P', 'm'],
    lam: function (p) {
      if (rnd(p.mode) === 1) { var s = rnd(p.stage); return s <= 0 ? p.l0 : (s === 1 ? p.l1 : p.l2); }
      return p.lam;
    },
    vl: function (p, lam) { return p.V * (NA_REF / lam) * (NA_REF / lam); },
    read: function (p) {
      var B = p.kB * p.A, rho = Faraday.vl(p, Faraday.lam(p)) * B * p.l, c;
      if (rnd(p.mode) === 2) return { x: p.x, A: p.A, B: B, P: 0.0, m: Math.abs(Math.sin(2.0 * rho)) };
      c = Math.cos(p.x - rho);
      return { x: p.x, A: p.A, B: B, P: c * c, m: 0.0 };
    },
    null: function (p, A, lam) { return PI / 2.0 + Faraday.vl(p, lam) * p.kB * A * p.l; },
    plan: function (p) {
      var m = rnd(p.mode), out = [], s, lam;
      if (m === 2) return [0.5, 1.0, 1.5, 2.0].map(function (a) { return { A: a }; });
      if (m === 1) {
        for (s = 0; s < 3; s++) {
          lam = s === 0 ? p.l0 : (s === 1 ? p.l1 : p.l2);
          out.push({ stage: s, A: 0.0, x: Faraday.null(p, 0.0, lam) });
          out.push({ stage: s, A: 4.0, x: Faraday.null(p, 4.0, lam) });
        }
        return out;
      }
      return [0.0, 1.0, 2.0, 3.0, 4.0].map(function (a) { return { A: a, x: Faraday.null(p, a, p.lam) }; });
    },
    calc: function (rs, p) {
      var m = rnd(p.mode), r, l, xs, ys, s, g, lo, hi, i, q, v, lam;
      if (m === 2) {
        r = rows(rs, ['B', 'm']);
        if (r.length < 2) return 0.0;
        l = line(col(r, 0), r.map(function (q) { return asin(q[1]) / 2.0; }));
        return l[0] / p.l;
      }
      if (m === 1) {
        r = rows(rs, ['stage', 'B', 'x']); xs = []; ys = [];
        for (s = 0; s < 3; s++) {
          g = r.filter(function (q) { return Math.abs(q[0] - s) < 0.5; });
          if (g.length < 2) continue;
          lo = g[0]; hi = g[0];
          for (i = 0; i < g.length; i++) { q = g[i]; if (q[1] < lo[1]) lo = q; if (q[1] > hi[1]) hi = q; }
          if (hi[1] - lo[1] <= 0.0) continue;
          v = (hi[2] - lo[2]) / ((hi[1] - lo[1]) * p.l);
          lam = s === 0 ? p.l0 : (s === 1 ? p.l1 : p.l2);
          if (v > 0.0) { xs.push(Math.log(lam)); ys.push(Math.log(v)); }
        }
        if (xs.length < 2) return 0.0;
        return -line(xs, ys)[0];
      }
      r = rows(rs, ['B', 'x']);
      if (r.length < 2) return 0.0;
      return line(col(r, 0), col(r, 1))[0] / p.l;
    },
  });

  // ---------------------------------------------------------------------- Fraunhofer diffraction
  var Fraun = scan({
    PARAMS: { lam: 6.328e-7, L: 1.0, a: 1.0e-4, d: 2.5e-4, N: 20.0, mode: 0.0, x: 0.0 },
    VARS: ['x', 'I', 'm'],
    s: function (p, x) { return Math.sin(Math.atan(x / p.L)); },
    comb: function (N, u) { var sn = Math.sin(u), q; if (Math.abs(sn) < 1e-9) return 1.0; q = Math.sin(N * u) / (N * sn); return q * q; },
    read: function (p) {
      var m = rnd(p.mode), s = Fraun.s(p, p.x), lam = p.lam, ua = PI * p.a * s / lam, ud = PI * p.d * s / lam, I, k, j, best, i, c;
      if (m === 1) {
        j = Math.abs(ua) < 1e-9 ? 1.0 : 2.0 * jn(1, ua) / ua;
        I = j * j; best = 0;
        for (i = 0; i < J1_ZEROS.length; i++) if (Math.abs(Math.abs(ua) - J1_ZEROS[i]) < Math.abs(Math.abs(ua) - J1_ZEROS[best])) best = i;
        k = Math.abs(ua) < 0.5 * J1_ZEROS[0] ? 0.0 : best + 1.0;
      } else if (m === 2 || m === 3) {
        I = sinc2(ua); k = rnd(Math.abs(p.a * s / lam));
      } else if (m === 4) {
        c = Math.cos(ud); I = c * c * sinc2(ua); k = rnd(Math.abs(p.d * s / lam));
      } else {
        I = sinc2(ua) * Fraun.comb(p.N, ud); k = rnd(Math.abs(p.d * s / lam));
      }
      return { x: p.x, I: I, m: k };
    },
    xs: function (p, s) { if (s >= 1.0) return 0.0; return p.L * Math.tan(Math.asin(s)); },
    plan: function (p) {
      var m = rnd(p.mode), lam = p.lam;
      if (m === 1) return [0, 1].map(function (i) { return { x: Fraun.xs(p, J1_ZEROS[i] * lam / (PI * p.a)) }; });
      if (m === 2 || m === 3) return [1.0, 2.0, 3.0].map(function (k) { return { x: Fraun.xs(p, k * lam / p.a) }; });
      if (m === 5) return [1.0, 2.0].map(function (k) { return { x: Fraun.xs(p, k * lam / p.d) }; });
      return [1.0, 2.0, 3.0].map(function (k) { return { x: Fraun.xs(p, k * lam / p.d) }; });
    },
    calc: function (rs, p) {
      var m = rnd(p.mode), out = [], r = rows(rs, ['x', 'm']), i, q, s, k, j;
      for (i = 0; i < r.length; i++) {
        q = r[i]; s = Math.abs(Fraun.s(p, q[0])); k = q[1];
        if (s <= 0.0 || k < 0.5) continue;
        if (m === 1) { j = rnd(k) - 1; if (j >= 0 && j < J1_ZEROS.length) out.push(J1_ZEROS[j] * p.lam / (PI * s)); }
        else if (m === 2 || m === 3) out.push(k * p.lam / s);
        else if (m === 5) out.push(p.d * s / k);
        else out.push(k * p.lam / s);
      }
      return mean(out);
    },
  });

  // ---------------------------------------------------------------------- constant deviation spectrometer
  var Cdev = scan({
    PARAMS: { l1: 5.769610e-7, l2: 5.790670e-7, e0: 8.0e-10, e1: 0.004, e2: 1.0e4, w: 1.5e-10, mode: 0.0, stage: 0.0, x: 5.5e-7 },
    VARS: ['x', 'I'],
    drum: function (p, lam) { var q = lam - 5.5e-7; return lam + p.e0 + p.e1 * q + p.e2 * q * q; },
    read: function (p) {
      var lines = p.stage < 0.5 ? HG_CAL : [p.l1, p.l2], I = 0.0, i, z;
      for (i = 0; i < lines.length; i++) { z = (p.x - Cdev.drum(p, lines[i])) / p.w; I += Math.exp(-z * z); }
      return { x: p.x, I: I };
    },
    plan: function (p) {
      var out = HG_CAL.map(function (lam) { return { stage: 0.0, x: Cdev.drum(p, lam) }; });
      return out.concat([{ stage: 1.0, x: Cdev.drum(p, p.l1) }, { stage: 1.0, x: Cdev.drum(p, p.l2) }]);
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x']), z, u, xs;
      z = sortedBy(r.filter(function (q) { return q[0] < 0.5; }), 1);
      u = sortedBy(r.filter(function (q) { return q[0] > 0.5; }), 1);
      if (z.length < 3 || !u.length) return 0.0;
      xs = [z[0][1], z[1][1], z[2][1]];
      function lam(x) {
        var tot = 0.0, i, j, w, den;
        for (i = 0; i < 3; i++) {
          w = 1.0;
          for (j = 0; j < 3; j++) {
            if (j !== i) { den = xs[i] - xs[j]; if (den === 0.0) return 0.0; w *= (x - xs[j]) / den; }
          }
          tot += w * HG_CAL[i];
        }
        return tot;
      }
      if (p.mode > 0.5) return lam(u[0][1]);
      if (u.length < 2) return 0.0;
      return lam(u[u.length - 1][1]) - lam(u[0][1]);
    },
  });

  // ---------------------------------------------------------------------- concave grating, Rowland mounting
  var Rowland = scan({
    PARAMS: { R: 1.0, d: 1.6666666666666667e-6, al: 0.17453292519943295, m: 1.0, N: 5000.0, la: 5.460750e-7, lb: 5.769610e-7,
      lu: 5.790670e-7, mode: 0.0, x: 0.15 },
    VARS: ['x', 'I'],
    lam: function (p, x) { return p.d * (Math.sin(p.al) + Math.sin(x / p.R)) / p.m; },
    pos: function (p, lam) { return p.R * asin(p.m * lam / p.d - Math.sin(p.al)); },
    read: function (p) {
      var lam = Rowland.lam(p, p.x), I = 0.0, ls = [p.la, p.lb, p.lu], i, dl;
      for (i = 0; i < 3; i++) { dl = ls[i] / (p.m * p.N); I += sinc2(PI * (lam - ls[i]) / dl); }
      return { x: p.x, I: I };
    },
    plan: function (p) {
      var m = rnd(p.mode), dl, h, out;
      if (m === 2) {
        dl = p.la / (p.m * p.N); h = SINC2_HALF * dl / PI;
        return [{ x: Rowland.pos(p, p.la - h) }, { x: Rowland.pos(p, p.la) }, { x: Rowland.pos(p, p.la + h) }];
      }
      out = [{ x: Rowland.pos(p, p.la) }, { x: Rowland.pos(p, p.lb) }];
      if (m === 1) out.push({ x: Rowland.pos(p, p.lu) });
      return out;
    },
    calc: function (rs, p) {
      var m = rnd(p.mode), r = sortedBy(rows(rs, ['x']), 0), fw, dx, pf;
      if (r.length < 2) return 0.0;
      if (m === 2) {
        if (r.length < 3) return 0.0;
        fw = Rowland.lam(p, r[r.length - 1][0]) - Rowland.lam(p, r[0][0]);
        return fw > 0.0 ? p.la * (2.0 * SINC2_HALF / PI) / fw : 0.0;
      }
      dx = r[1][0] - r[0][0];
      if (dx <= 0.0) return 0.0;
      pf = (p.lb - p.la) / dx;
      if (m === 1) { if (r.length < 3) return 0.0; return p.la + (r[2][0] - r[0][0]) * pf; }
      return pf;
    },
  });

  // ---------------------------------------------------------------------- band heads, Deslandres table
  var BANDS = [[2.0, 0.0], [1.0, 0.0], [0.0, 0.0], [0.0, 1.0], [0.0, 2.0], [1.0, 1.0]];
  var Band = scan({
    PARAMS: { Te: 2068895.0, we1: 87005.0, wx1: 352.0, we0: 97923.0, wx0: 697.0, w: 2.0e-11, W: 4.0e-10, mode: 0.0, x: 4.84e-7 },
    VARS: ['x', 'I'],
    nu: function (p, v1, v0) {
      var g1 = p.we1 * (v1 + 0.5) - p.wx1 * (v1 + 0.5) * (v1 + 0.5), g0 = p.we0 * (v0 + 0.5) - p.wx0 * (v0 + 0.5) * (v0 + 0.5);
      return p.Te + g1 - g0;
    },
    read: function (p) {
      var I = 0.0, i, b, h, a, dx, z;
      for (i = 0; i < BANDS.length; i++) {
        b = BANDS[i]; h = 1.0 / Band.nu(p, b[0], b[1]); a = Math.pow(0.7, b[0] + b[1]); dx = p.x - h;
        if (dx >= 0.0) I += a * Math.exp(-dx / p.W); else { z = dx / p.w; I += a * Math.exp(-z * z); }
      }
      return { x: p.x, I: I };
    },
    plan: function (p) { return BANDS.slice(0, 5).map(function (b) { return { x: 1.0 / Band.nu(p, b[0], b[1]) }; }); },
    calc: function (rs, p) {
      var r = sortedBy(rows(rs, ['x']), 0), n, m, a, b, wx;
      if (r.length < 5 || r[0][0] <= 0.0) return 0.0;
      n = r.slice(0, 5).map(function (q) { return 1.0 / q[0]; });
      m = rnd(p.mode);
      if (m <= 1) { a = n[2] - n[3]; b = n[3] - n[4]; wx = (a - b) / 2.0; return m === 0 ? wx : a + 2.0 * wx; }
      a = n[1] - n[2]; b = n[0] - n[1]; wx = (a - b) / 2.0;
      return m === 2 ? a + 2.0 * wx : wx;
    },
  });

  // ---------------------------------------------------------------------- a scanned spectrum
  var Spec = scan({
    PARAMS: { kind: 0.0, c1: 5.07e-7, c2: 5.26e-7, c3: 5.46e-7, c4: 5.66e-7, c5: 0.0, w: 6.0e-9, a: 1.0, tb: 2.0, gs: 1.0e-9,
      Ts: 5778.0, mode: 0.0, x: 5.3e-7 },
    VARS: ['x', 'S'],
    cs: function (p) { return [p.c1, p.c2, p.c3, p.c4, p.c5].filter(function (c) { return c > 0.0; }); },
    read: function (p) {
      var k = rnd(p.kind), tot = 0.0, c = Spec.cs(p), i, z, lam, ref, b, cont;
      for (i = 0; i < c.length; i++) { z = (p.x - c[i]) / p.w; tot += Math.exp(-z * z); }
      if (k === 1) return { x: p.x, S: tot };
      if (k === 2) {
        lam = p.x; if (lam <= 1e-8) return { x: p.x, S: 0.0 }; ref = 5.0e-7; b = 0.014387768775039337 / p.Ts;
        cont = Math.pow(ref / lam, 5) * (Math.exp(b / ref) - 1.0) / (Math.exp(b / lam) - 1.0);
        return { x: p.x, S: cont * (1.0 - p.a * tot) };
      }
      return { x: p.x, S: Math.exp(-p.a * tot) };
    },
    targets: function (p) {
      var c = Spec.cs(p), i;
      if (rnd(p.mode) === 1) return c;
      i = rnd(p.tb) - 1;
      return (i >= 0 && i < c.length) ? [c[i]] : [];
    },
    plan: function (p) {
      var out = [], h = p.w / 2.0, t = Spec.targets(p), i, g;
      for (i = 0; i < t.length; i++) { g = rnd(t[i] / p.gs) * p.gs; out.push({ x: g - h }, { x: g }, { x: g + h }); }
      return out;
    },
    vertex: function (p, a, b, c) {
      var k = rnd(p.kind), x1 = a[0], x2 = b[0], x3 = c[0], y1, y2, y3, den, A, Bq;
      function y(v) { if (k === 1) return ln(v); if (k === 2) return v; return (v > 0.0 && v < 1.0) ? ln(-ln(v)) : 0.0; }
      y1 = y(a[1]); y2 = y(b[1]); y3 = y(c[1]);
      den = (x1 - x2) * (x1 - x3) * (x2 - x3);
      if (den === 0.0) return 0.0;
      A = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / den;
      Bq = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / den;
      if (A === 0.0) return 0.0;
      return -Bq / (2.0 * A);
    },
    calc: function (rs, p) {
      var r = sortedBy(rows(rs, ['x', 'S']), 0), groups = [], cur, i, vs = [], g, mid, v;
      if (r.length < 3) return 0.0;
      cur = [r[0]];
      for (i = 1; i < r.length; i++) { if (r[i][0] - r[i - 1][0] > 1.5 * p.w) { groups.push(cur); cur = []; } cur.push(r[i]); }
      groups.push(cur);
      for (i = 0; i < groups.length; i++) {
        g = groups[i];
        if (g.length >= 3) { mid = Math.floor(g.length / 2); v = Spec.vertex(p, g[mid - 1], g[mid], g[mid + 1]); if (v > 0.0) vs.push(v); }
      }
      if (!vs.length) return 0.0;
      if (rnd(p.mode) === 1) { if (vs.length < 2) return 0.0; return (1.0 / vs[0] - 1.0 / vs[vs.length - 1]) / (vs.length - 1); }
      return vs[0];
    },
  });

  // ---------------------------------------------------------------------- thickness of a film at a step
  var Film = scan({
    PARAMS: { t: 1.2e-7, lam: 5.461e-7, s: 4.0e-4, F: 60.0, T0: 2.0e-6, mode: 0.0, stage: 0.0, A: 5.0e-7, x: 4.0e-4 },
    VARS: ['x', 'A', 'I'],
    read: function (p) {
      var tt = p.stage > 0.5 ? p.t : 0.0, G, gap;
      if (p.mode > 0.5) { G = p.T0 - tt; if (p.A <= 0.0) return { x: p.x, A: p.A, I: 0.0 }; return { x: p.x, A: p.A, I: airy(p.F, 2.0 * G / p.A) }; }
      gap = (p.lam / 2.0) * (p.x / p.s) - tt;
      return { x: p.x, A: p.A, I: airy(p.F, 2.0 * gap / p.lam) };
    },
    order: function (p) { return Math.ceil(2.0 * p.T0 / 6.5e-7); },
    plan: function (p) {
      var m;
      if (p.mode > 0.5) {
        m = Film.order(p);
        return [{ stage: 0.0, A: 2.0 * p.T0 / m }, { stage: 0.0, A: 2.0 * p.T0 / (m + 1.0) }, { stage: 1.0, A: 2.0 * (p.T0 - p.t) / m }];
      }
      return [{ stage: 0.0, x: p.s }, { stage: 0.0, x: 2.0 * p.s }, { stage: 1.0, x: p.s * (1.0 + 2.0 * p.t / p.lam) }];
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', p.mode > 0.5 ? 'A' : 'x']), z, f, hi, lo, m, s;
      z = sortedBy(r.filter(function (q) { return q[0] < 0.5; }), 1);
      f = r.filter(function (q) { return q[0] > 0.5; });
      if (z.length < 2 || !f.length) return 0.0;
      if (p.mode > 0.5) {
        hi = z[z.length - 1][1]; lo = z[0][1];
        if (hi - lo <= 0.0) return 0.0;
        m = rnd(lo / (hi - lo));
        return m * (hi - f[0][1]) / 2.0;
      }
      s = z[1][1] - z[0][1];
      if (s <= 0.0) return 0.0;
      return (p.lam / 2.0) * (f[0][1] - z[0][1]) / s;
    },
  });

  // ---------------------------------------------------------------------- Stoney: stress from curvature
  var Stoney = scan({
    PARAMS: { sig: 2.0e8, hf: 5.0e-7, hs: 1.0e-3, Ms: 9.35e10, R0: 100.0, lam: 5.893e-7, mode: 0.0, stage: 0.0, x: 0.01 },
    VARS: ['x', 'I', 'm'],
    kap: function (p) { return 6.0 * p.sig * p.hf / (p.Ms * p.hs * p.hs); },
    radius: function (p, stage) { if (stage < 0.5) return p.R0; return 1.0 / (1.0 / p.R0 + Stoney.kap(p)); },
    read: function (p) {
      var R = Stoney.radius(p, p.stage), q = p.x * p.x / (R * p.lam), s = Math.sin(PI * q);
      return { x: p.x, I: s * s, m: rnd(q) };
    },
    plan: function (p) {
      var out = [], sts = [0.0, 1.0], ms = [2.0, 4.0, 6.0], i, j, R;
      for (i = 0; i < 2; i++) { R = Stoney.radius(p, sts[i]); for (j = 0; j < 3; j++) out.push({ stage: sts[i], x: Math.sqrt(ms[j] * R * p.lam) }); }
      return out;
    },
    calc: function (rs, p) {
      var r = rows(rs, ['stage', 'x', 'm']), Rs = [], sts = [0.0, 1.0], i, g, l, k;
      for (i = 0; i < 2; i++) {
        g = r.filter(function (q) { return Math.abs(q[0] - sts[i]) < 0.5; });
        if (g.length < 2) return 0.0;
        l = line(col(g, 2), g.map(function (q) { return q[1] * q[1]; }));
        if (l[0] <= 0.0) return 0.0;
        Rs.push(l[0] / p.lam);
      }
      k = 1.0 / Rs[1] - 1.0 / Rs[0];
      if (p.mode > 0.5) return p.Ms * p.hs * p.hs * k / (6.0 * p.hf);
      return k;
    },
  });

  // ---------------------------------------------------------------------- photometry
  var Photom = scan({
    PARAMS: { Iv: 65.0, K: 15.0, mode: 0.0, x: 0.5 },
    VARS: ['x', 'E', 'Ee'],
    read: function (p) { var d = Math.max(p.x, 0.05), E = p.Iv / (d * d); return { x: p.x, E: E, Ee: E / p.K }; },
    plan: function () { return [0.3, 0.4, 0.5, 0.6, 0.8, 1.0].map(function (d) { return { x: d }; }); },
    calc: function (rs, p) {
      var m = rnd(p.mode), r, key;
      if (m === 1) {
        r = rows(rs, ['x', 'E']).filter(function (q) { return q[0] > 0.0 && q[1] > 0.0; });
        if (r.length < 2) return 0.0;
        return -line(r.map(function (q) { return Math.log(q[0]); }), r.map(function (q) { return Math.log(q[1]); }))[0];
      }
      key = m === 2 ? 'Ee' : 'E';
      r = rows(rs, ['x', key]).filter(function (q) { return q[0] > 0.0; });
      if (r.length < 2) return 0.0;
      return line(r.map(function (q) { return 1.0 / (q[0] * q[0]); }), col(r, 1))[0];
    },
  });

  // ---------------------------------------------------------------------- acousto-optics
  var Ao = scan({
    PARAMS: { v: 1497.0, f: 1.0e7, lam: 6.328e-7, L: 1.0, nu: 1.5, P100: 1.0, ws: 3.0e-4, mode: 0.0, A: 0.0, x: 0.0 },
    VARS: ['x', 'A', 'I', 'm', 'eta'],
    xb: function (p) { var sb = p.lam * p.f / (2.0 * p.v); return p.L * Math.tan(2.0 * asin(sb)); },
    eta: function (p, A) { var s = Math.sin(PI / 2.0 * sqrt(A / p.P100)); return s * s; },
    read: function (p) {
      var m = rnd(p.mode), x = p.x, e, z0, z1, I, best, bd, k, sk, xk, z, jk;
      if (m === 2) return { x: p.x, A: p.A, I: 0.0, m: 0.0, eta: Ao.eta(p, p.A) };
      if (m === 1) {
        e = Ao.eta(p, p.A > 0.0 ? p.A : 0.5 * p.P100);
        z0 = x / p.ws; z1 = (x - Ao.xb(p)) / p.ws;
        I = (1.0 - e) * Math.exp(-z0 * z0) + e * Math.exp(-z1 * z1);
        return { x: x, A: p.A, I: I, m: Math.abs(z1) < Math.abs(z0) ? 1.0 : 0.0, eta: e };
      }
      I = 0.0; best = 0.0; bd = 1e30;
      for (k = -3; k < 4; k++) {
        sk = k * p.lam * p.f / p.v;
        xk = Math.abs(sk) < 1.0 ? p.L * Math.tan(Math.asin(sk)) : 1e9;
        z = (x - xk) / p.ws; jk = jn(Math.abs(k), p.nu);
        I += jk * jk * Math.exp(-z * z);
        if (Math.abs(x - xk) < bd) { bd = Math.abs(x - xk); best = Math.abs(k); }
      }
      return { x: x, A: p.A, I: I, m: best, eta: 0.0 };
    },
    plan: function (p) {
      var m = rnd(p.mode);
      if (m === 2) return [0.1, 0.2, 0.3, 0.4, 0.5].map(function (k) { return { A: p.P100 * k }; });
      if (m === 1) return [{ x: 0.0 }, { x: Ao.xb(p) }];
      return [1.0, 2.0, 3.0].map(function (k) { var sk = k * p.lam * p.f / p.v; return { x: p.L * Math.tan(asin(sk)) }; });
    },
    calc: function (rs, p) {
      var m = rnd(p.mode), out = [], r, i, q, a, th;
      if (m === 2) {
        r = rows(rs, ['A', 'eta']);
        for (i = 0; i < r.length; i++) { q = r[i]; a = asin(sqrt(q[1])); if (q[0] > 0.0 && a > 0.0) out.push(PI * PI * q[0] / (4.0 * a * a)); }
        return mean(out);
      }
      r = rows(rs, ['x', 'm']);
      for (i = 0; i < r.length; i++) {
        q = r[i];
        if (q[1] < 0.5 || q[0] <= 0.0) continue;
        th = Math.atan(q[0] / p.L);
        if (m === 1) out.push(p.lam * p.f / (2.0 * Math.sin(th / 2.0)));
        else out.push(q[1] * p.lam * p.f / Math.sin(th));
      }
      return mean(out);
    },
  });

  // ---------------------------------------------------------------------- ellipsometry
  function cc(a, b) { return [a, b === undefined ? 0.0 : b]; }
  function cadd(a, b) { return [a[0] + b[0], a[1] + b[1]]; }
  function csub(a, b) { return [a[0] - b[0], a[1] - b[1]]; }
  function cmul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function cdiv(a, b) { var d = b[0] * b[0] + b[1] * b[1]; if (d === 0.0) return [0.0, 0.0]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; }
  function cabs2(a) { return a[0] * a[0] + a[1] * a[1]; }
  function csqrt(a) { var r = Math.sqrt(a[0] * a[0] + a[1] * a[1]), re = sqrt((r + a[0]) / 2.0), im = sqrt((r - a[0]) / 2.0); return [re, a[1] >= 0.0 ? im : -im]; }
  function cexpi(t) { return [Math.cos(t), Math.sin(t)]; }
  function acos(v) { return Math.acos(clamp(v, -1.0, 1.0)); }
  var Ellips = scan({
    PARAMS: { phi0: 1.0471975511965976, phi1: 1.2217304763960306, phi2: 1.1344640137963142, n1: 1.457, d: 1.0e-7, n2: 3.882, k2: 0.019,
      lam: 6.328e-7, sample: 0.0, meth: 0.0, mode: 0.0, stage: 0.0, A: 0.0, x: 0.0 },
    VARS: ['x', 'A', 'I'],
    phi: function (p, st) { var s = rnd(st); return s <= 0 ? p.phi0 : (s === 1 ? p.phi1 : p.phi2); },
    rho: function (p, ph, d) {
      var n0 = cc(1.0), n2 = cc(p.n2, p.k2), s0 = Math.sin(ph), c0 = cc(Math.cos(ph)), c2, n1, c1, b, e, out = [], fs, i, a, g, ge;
      function cosin(N) { var q = cdiv(cc(s0), N); return csqrt(csub(cc(1.0), cmul(q, q))); }
      function rp(Na, ca, Nb, cb) { return cdiv(csub(cmul(Nb, ca), cmul(Na, cb)), cadd(cmul(Nb, ca), cmul(Na, cb))); }
      function rs(Na, ca, Nb, cb) { return cdiv(csub(cmul(Na, ca), cmul(Nb, cb)), cadd(cmul(Na, ca), cmul(Nb, cb))); }
      c2 = cosin(n2);
      if (p.sample > 0.5) return [rp(n0, c0, n2, c2), rs(n0, c0, n2, c2)];
      n1 = cc(p.n1); c1 = cosin(n1);
      b = cmul(cc(2.0 * PI * d / p.lam), cmul(n1, c1));
      e = cmul(cexpi(-2.0 * b[0]), cc(Math.exp(2.0 * b[1])));
      fs = [rp, rs];
      for (i = 0; i < 2; i++) { a = fs[i](n0, c0, n1, c1); g = fs[i](n1, c1, n2, c2); ge = cmul(g, e); out.push(cdiv(cadd(a, ge), cadd(cc(1.0), cmul(a, ge)))); }
      return out;
    },
    psidel: function (p, st) { var r = Ellips.rho(p, Ellips.phi(p, st), p.d), q = cdiv(r[0], r[1]); return [Math.atan(Math.sqrt(cabs2(q))), Math.atan2(q[1], q[0])]; },
    read: function (p) {
      var r = Ellips.rho(p, Ellips.phi(p, p.stage), p.d), rp = r[0], rs = r[1], A = p.A, amp, P, c, a, b, ex, ey;
      if (p.meth > 0.5) { amp = cadd(cmul(cc(Math.cos(A)), rp), cmul(cc(Math.sin(A)), rs)); return { x: p.x, A: A, I: 2.0 * cabs2(amp) / (cabs2(rp) + cabs2(rs)) }; }
      P = p.x; c = Math.cos(PI / 4.0);
      a = cc(c * Math.cos(P) + c * Math.sin(P));
      b = cmul(cc(-c * Math.cos(P) + c * Math.sin(P)), cc(0.0, -1.0));
      ex = csub(cmul(cc(c), a), cmul(cc(c), b)); ey = cadd(cmul(cc(c), a), cmul(cc(c), b));
      amp = cadd(cmul(cc(Math.cos(A)), cmul(rp, ex)), cmul(cc(Math.sin(A)), cmul(rs, ey)));
      return { x: P, A: A, I: 2.0 * cabs2(amp) / (cabs2(rp) + cabs2(rs)) };
    },
    plan: function (p) {
      var out = [], sts = [0.0, 1.0, 2.0], i, j, pd, P, as = [0.0, PI / 4.0, PI / 2.0, 3.0 * PI / 4.0];
      for (i = 0; i < 3; i++) {
        if (p.meth > 0.5) { for (j = 0; j < 4; j++) out.push({ stage: sts[i], A: as[j] }); }
        else {
          pd = Ellips.psidel(p, sts[i]); P = (1.5 * PI - pd[1]) / 2.0;
          while (P < 0.0) P += PI;
          while (P >= PI) P -= PI;
          out.push({ stage: sts[i], x: P, A: pd[0] });
        }
      }
      return out;
    },
    measured: function (rs, p) {
      var out = [], r = p.meth > 0.5 ? rows(rs, ['stage', 'A', 'I']) : rows(rs, ['stage', 'x', 'A']), sts = [0.0, 1.0, 2.0], i, g, ph, i0, i9, cd, A, psi;
      for (i = 0; i < 3; i++) {
        g = r.filter(function (q) { return Math.abs(q[0] - sts[i]) < 0.5; });
        if (!g.length) continue;
        ph = Ellips.phi(p, sts[i]);
        if (p.meth > 0.5) {
          if (g.length < 4) continue;
          var at = function (a) { var best = g[0], k; for (k = 0; k < g.length; k++) if (Math.abs(g[k][1] - a) < Math.abs(best[1] - a)) best = g[k]; return best[2]; };
          i0 = at(0.0); i9 = at(PI / 2.0);
          if (i0 <= 0.0 || i9 <= 0.0) continue;
          cd = (at(PI / 4.0) - at(3.0 * PI / 4.0)) / (2.0 * Math.sqrt(i0 * i9));
          out.push([ph, Math.sqrt(i0 / i9), acos(cd), 1.0]);
        } else {
          A = g[0][2]; psi = A;
          while (psi < 0.0) psi += PI;
          while (psi >= PI) psi -= PI;
          if (psi > PI / 2.0) psi = PI - psi;
          out.push([ph, Math.tan(psi), 1.5 * PI - 2.0 * g[0][1], 0.0]);
        }
      }
      return out;
    },
    miss: function (p, ph, d, m) {
      var r = Ellips.rho(p, ph, d), q = cdiv(r[0], r[1]), tp = Math.sqrt(cabs2(q)), cd, z;
      if (m[3] > 0.5) { cd = tp > 0.0 ? q[0] / tp : 0.0; return (tp - m[1]) * (tp - m[1]) + (cd - Math.cos(m[2])) * (cd - Math.cos(m[2])); }
      z = csub(q, cmul(cc(m[1]), cexpi(m[2])));
      return cabs2(z);
    },
    thick: function (p, m) {
      var ph = m[0], s = Math.sin(ph), per = p.lam / (2.0 * sqrt(p.n1 * p.n1 - s * s)), best = 0.0, bv = 1e30, i, d, v, lo, hi, g = 0.6180339887498949, a, b;
      if (per <= 0.0) return 0.0;
      for (i = 0; i < 400; i++) { d = per * i / 400.0; v = Ellips.miss(p, ph, d, m); if (v < bv) { bv = v; best = d; } }
      lo = best - per / 400.0; hi = best + per / 400.0;
      for (i = 0; i < 60; i++) { a = hi - g * (hi - lo); b = lo + g * (hi - lo); if (Ellips.miss(p, ph, a, m) < Ellips.miss(p, ph, b, m)) hi = b; else lo = a; }
      return (lo + hi) / 2.0;
    },
    metal: function (m) {
      var ph = m[0], rho = cmul(cc(m[1]), cexpi(m[2])), f, t, s, eps;
      if (m[3] > 0.5) rho = cmul(cc(m[1]), [Math.cos(m[2]), -Math.sin(m[2])]);
      f = cdiv(csub(cc(1.0), rho), cadd(cc(1.0), rho)); t = Math.tan(ph); s = Math.sin(ph);
      eps = cmul(cc(s * s), cadd(cc(1.0), cmul(cc(t * t), cmul(f, f))));
      return csqrt(eps);
    },
    calc: function (rs, p) {
      var ms = Ellips.measured(rs, p), m = rnd(p.mode), vals = [], i, N;
      if (!ms.length) return 0.0;
      for (i = 0; i < ms.length; i++) { if (m === 0) vals.push(Ellips.thick(p, ms[i])); else { N = Ellips.metal(ms[i]); vals.push(m === 1 ? N[0] : N[1]); } }
      return mean(vals);
    },
  });

  // ---------------------------------------------------------------------- optical particle counter (SIMULATED DATA)
  var OPC_EDGES = [3.0e-7, 5.0e-7, 7.0e-7, 1.0e-6, 2.0e-6, 3.0e-6, 5.0e-6, 1.0e-5];
  function erf(x) {
    var sg = x >= 0.0 ? 1.0 : -1.0, t, y;
    x = Math.abs(x); t = 1.0 / (1.0 + 0.3275911 * x);
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
    return sg * y;
  }
  var Aerosol = scan({
    PARAMS: { N: 1.5e8, cmd: 6.0e-7, sg: 2.0, Q: 4.717e-5, t: 60.0, mode: 0.0, x: 1.0 },
    VARS: ['x', 'C'],
    F: function (p, d) { if (d <= 0.0) return 0.0; return 0.5 * (1.0 + erf(Math.log(d / p.cmd) / (Math.sqrt(2.0) * Math.log(p.sg)))); },
    read: function (p) {
      var k = rnd(p.x), lo, hi;
      if (k < 1 || k > OPC_EDGES.length) return { x: p.x, C: 0.0 };
      lo = Aerosol.F(p, OPC_EDGES[k - 1]); hi = k < OPC_EDGES.length ? Aerosol.F(p, OPC_EDGES[k]) : 1.0;
      return { x: p.x, C: p.N * p.Q * p.t * (hi - lo) };
    },
    plan: function () { var out = [], k; for (k = 1; k <= OPC_EDGES.length; k++) out.push({ x: k }); return out; },
    calc: function (rs, p) {
      var r = sortedBy(rows(rs, ['x', 'C']), 0), tot = 0.0, i, half, c, q, k, lo, hi, f;
      if (r.length < 2) return 0.0;
      for (i = 0; i < r.length; i++) tot += r[i][1];
      if (p.mode < 0.5) return tot / (p.Q * p.t);
      half = tot / 2.0; c = 0.0;
      for (i = 0; i < r.length; i++) {
        q = r[i]; k = rnd(q[0]);
        if (k < 1 || k > OPC_EDGES.length) continue;
        if (c + q[1] >= half && q[1] > 0.0) {
          lo = OPC_EDGES[k - 1]; hi = k < OPC_EDGES.length ? OPC_EDGES[k] : 2.0 * lo; f = (half - c) / q[1];
          return Math.exp(Math.log(lo) + f * (Math.log(hi) - Math.log(lo)));
        }
        c += q[1];
      }
      return 0.0;
    },
    truth: function (p) {
      var f0, target, a, b, i, m;
      if (p.mode < 0.5) return p.N * (1.0 - Aerosol.F(p, OPC_EDGES[0]));
      f0 = Aerosol.F(p, OPC_EDGES[0]); target = f0 + (1.0 - f0) / 2.0; a = OPC_EDGES[0]; b = 1.0e-4;
      for (i = 0; i < 80; i++) { m = Math.sqrt(a * b); if (Aerosol.F(p, m) < target) a = m; else b = m; }
      return a;
    },
  });

  function calc(K) { return function (r, p) { return fin(K.calc(r, p)); }; }
  function m_(p) { return rnd(p.mode); }

  HK.register({
    K: { po9_fp: Fp, po9_zeeman: Zeeman, po9_biref: Biref, po9_ellipse: Ellipse, po9_photoel: Photoel, po9_eo: Eo,
      po9_faraday: Faraday, po9_fraun: Fraun, po9_cdev: Cdev, po9_rowland: Rowland, po9_band: Band, po9_spec: Spec,
      po9_film: Film, po9_stoney: Stoney, po9_photom: Photom, po9_ao: Ao, po9_ellipso: Ellips, po9_aerosol: Aerosol },
    CALCS: {
      po9_fp: { label: 'from the ring readings', unit: '', needs: ['x', 'c', 'n'], fn: calc(Fp) },
      po9_zeeman: { label: 'from the Zeeman pattern', unit: '', needs: ['x', 'c', 'n'], fn: calc(Zeeman) },
      po9_biref: { label: 'birefringence / retardation', unit: '', needs: ['stage', 'I'], fn: calc(Biref) },
      po9_ellipse: { label: 'the polarisation ellipse', unit: '', needs: ['stage', 'A', 'I'], fn: calc(Ellipse) },
      po9_photoel: { label: 'stress-optic coefficient', unit: '', needs: ['x', 'n'], fn: calc(Photoel) },
      po9_eo: { label: 'electro-optic constant / half-wave voltage', unit: '', needs: ['x'], fn: calc(Eo) },
      po9_faraday: { label: 'Verdet constant', unit: '', needs: ['B'], fn: calc(Faraday) },
      po9_fraun: { label: 'from the diffraction pattern', unit: 'm', needs: ['x', 'm'], fn: calc(Fraun) },
      po9_cdev: { label: 'corrected wavelength', unit: 'm', needs: ['stage', 'x'], fn: calc(Cdev) },
      po9_rowland: { label: 'from the plate', unit: '', needs: ['x'], fn: calc(Rowland) },
      po9_band: { label: 'vibrational constant', unit: '1/m', needs: ['x'], fn: calc(Band) },
      po9_spec: { label: 'band position', unit: '', needs: ['x', 'S'], fn: calc(Spec) },
      po9_film: { label: 'film thickness', unit: 'm', needs: ['stage'], fn: calc(Film) },
      po9_stoney: { label: 'curvature / film stress', unit: '', needs: ['stage', 'x', 'm'], fn: calc(Stoney) },
      po9_photom: { label: 'luminous intensity', unit: '', needs: ['x', 'E', 'Ee'], fn: calc(Photom) },
      po9_ao: { label: 'speed of sound / P100', unit: '', needs: ['m'], fn: calc(Ao) },
      po9_ellipso: { label: 'film thickness / optical constants', unit: '', needs: ['stage', 'A', 'I'], fn: calc(Ellips) },
      po9_aerosol: { label: 'number concentration / median diameter', unit: '', needs: ['x', 'C'], fn: calc(Aerosol) },
    },
    TEXTBOOK: {
      po9_fp: function (p) { return [p.ds, p.t, PI * Math.sqrt(p.R) / (1.0 - p.R)][m_(p)]; },
      po9_zeeman: function (p) {
        var ks = zcomps(p), m = m_(p);
        if (m === 2) return ks.length ? (ks[ks.length - 1] - ks[0]) / 2.0 : 0.0;
        return m === 1 ? p.em * H_PLANCK / (4.0 * PI) : p.em;
      },
      po9_biref: function (p) { return m_(p) >= 2 ? p.dn * p.t : p.dn; },
      po9_ellipse: function (p) { var m = m_(p); return m === 1 ? Ellipse.truth(p)[0] : (m === 2 ? p.del : Math.abs(Math.tan(Ellipse.truth(p)[1]))); },
      po9_photoel: function (p) { return p.mode > 0.5 ? Photoel.k(p) : p.C; },
      po9_eo: function (p) { var m = m_(p), k = rnd(p.kind); if (m === 3) return p.fc; if (m >= 1) return Eo.vpi(p); return k === 0 ? p.K : p.r; },
      po9_faraday: function (p) { return m_(p) === 1 ? 2.0 : Faraday.vl(p, p.lam); },
      po9_fraun: function (p) { var m = m_(p); return m === 5 ? p.lam : ((m === 0 || m === 4) ? p.d : p.a); },
      po9_cdev: function (p) { return p.mode > 0.5 ? p.l1 : p.l2 - p.l1; },
      po9_rowland: function (p) {
        var m = m_(p), lam, beta;
        if (m === 2) return p.m * p.N;
        if (m === 1) return p.lu;
        lam = (p.la + p.lb) / 2.0; beta = Math.asin(p.m * lam / p.d - Math.sin(p.al));
        return p.d * Math.cos(beta) / (p.m * p.R);
      },
      po9_band: function (p) { var m = m_(p); return (m >= 0 && m <= 3) ? [p.wx0, p.we0, p.we1, p.wx1][m] : 0.0; },
      po9_spec: function (p) {
        var c = Spec.cs(p), i;
        if (m_(p) === 1) return c.length > 1 ? (1.0 / c[0] - 1.0 / c[c.length - 1]) / (c.length - 1) : 0.0;
        i = rnd(p.tb) - 1;
        return (i >= 0 && i < c.length) ? c[i] : 0.0;
      },
      po9_film: function (p) { return p.t; },
      po9_stoney: function (p) { return p.mode > 0.5 ? p.sig : Stoney.kap(p); },
      po9_photom: function (p) { return [p.Iv, 2.0, p.Iv / p.K][m_(p)]; },
      po9_ao: function (p) { return m_(p) === 2 ? p.P100 : p.v; },
      po9_ellipso: function (p) { return [p.d, p.n2, p.k2][m_(p)]; },
      po9_aerosol: function (p) { return Aerosol.truth(p); },
    },
  });
})(typeof window !== 'undefined' ? window : this);
