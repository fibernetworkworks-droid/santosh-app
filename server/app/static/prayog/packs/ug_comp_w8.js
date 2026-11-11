/* Kernel pack (browser twin of app/prayog/packs/ug_comp_w8.py): B.Sc. "Computational physics" practicals, wave 8.
   Same formulas, same order of operations, so both sides give the same numbers. Deterministic throughout: anything
   random is a seeded Lehmer generator (16807, mod 2^31 - 1), never the clock; the molecular dynamics uses arithmetic
   and square roots only, so both twins follow the same chaotic trajectory.
     cw8_fact cw8_frame cw8_vfield cw8_group cw8_gfx cw8_anharm cw8_ljmd cw8_levels cw8_maxwell cw8_heatcap
     cw8_qdist cw8_fractal cw8_flow cw8_game cw8_conv cw8_lti cw8_fir cw8_geod cw8_constr
   Every kernel reports val (numerical), exact (the reference), err, nused and the curves the monitor draws. */
(function (root) {
  'use strict';
  var PI = Math.PI, M31 = 2147483647;
  var KB = 1.380649e-23, NA = 6.02214076e23, QE = 1.602176634e-19;

  function I(v) { return Math.floor(v + 0.5); }
  function errOf(val, exact) { return Math.abs(val - exact) / Math.max(Math.abs(exact), 1e-30); }
  function grid(a, b, m) { var out = [], i; for (i = 0; i <= m; i++) out.push(a + (b - a) * i / m); return out; }
  function mod(a, b) { var r = a % b; return r < 0 ? r + b : r; }
  function lcg(seed) { var s = mod(I(seed), M31); return [s > 0 ? s : 1]; }
  function u(st) { st[0] = (st[0] * 16807) % M31; return st[0] / M31; }
  function rowsOf(rs, keys) {
    var out = [], i, j, vals, v, ok;
    for (i = 0; i < (rs || []).length; i++) {
      vals = []; ok = true;
      for (j = 0; j < keys.length; j++) {
        v = Number(rs[i][keys[j]]);
        if (rs[i][keys[j]] === '' || rs[i][keys[j]] === null || rs[i][keys[j]] === undefined || !isFinite(v)) { ok = false; break; }
        vals.push(v);
      }
      if (ok) out.push(vals);
    }
    return out;
  }
  function thin(xs, m) {
    var n = xs.length, out = [], i;
    if (n <= m + 1) return xs.slice();
    for (i = 0; i <= m; i++) out.push(xs[I(i * (n - 1) / m)]);
    return out;
  }
  function uniqSorted(a) {
    var s = a.slice().sort(function (x, y) { return x - y; }), out = [], i;
    for (i = 0; i < s.length; i++) if (!out.length || s[i] !== out[out.length - 1]) out.push(s[i]);
    return out;
  }
  function simpson(f, a, b, n) {
    n = Math.max(2, n - (n % 2));
    var h = (b - a) / n, s = f(a) + f(b), i;
    for (i = 1; i < n; i++) s += (i % 2 === 1 ? 4.0 : 2.0) * f(a + h * i);
    return s * h / 3.0;
  }
  function base(val, exact, nused, cx, ce, cy, px, py, extra) {
    var s = { t: 0.0, val: val, exact: exact, err: errOf(val, exact), nused: nused, cx: cx, ce: ce, cy: cy, px: px, py: py }, k;
    if (extra) for (k in extra) s[k] = extra[k];
    return s;
  }
  function copy(s) { var o = {}, k; for (k in s) o[k] = s[k]; return o; }
  function kernel(params, init) {
    var K = {
      PARAMS: params, VARS: ['t', 'val', 'exact', 'err', 'nused', 'cx', 'ce', 'cy', 'px', 'py'],
      init: init,
      step: function (s, p, dt) { s.t += dt; },
      view: function (s) { return copy(s); },
      measure: function (p) { var s = init(p); return { val: s.val, exact: s.exact, err: s.err, nused: s.nused }; }
    };
    return K;
  }
  function sumArr(a) { var s = 0, i; for (i = 0; i < a.length; i++) s += a[i]; return s; }

  // ====================================================================================== factorials
  function lnfact(N) { var s = 0.0, k; for (k = 2; k <= N; k++) s += Math.log(k); return s; }
  function stirling(N, meth) {
    if (N < 1) return 0.0;
    var v = N * Math.log(N) - N;
    if (meth >= 1) v += 0.5 * Math.log(2 * PI * N);
    if (meth >= 2) v += 1.0 / (12.0 * N);
    return v;
  }
  function factK(p, N) { return Math.max(0, Math.min(N, I(p.frac * N))); }
  function factExact(p) {
    var N = Math.max(1, I(p.n));
    if (I(p.cas) === 1) { var K = factK(p, N); return lnfact(N) - lnfact(K) - lnfact(N - K); }
    return lnfact(N);
  }
  var CwFact = kernel({ cas: 0.0, method: 1.0, n: 20.0, frac: 0.5 }, function (p) {
    var cas = I(p.cas), meth = I(p.method), N = Math.max(1, I(p.n)), K = factK(p, N), i;
    function approx(m) { return cas === 1 ? stirling(m, meth) - stirling(factK(p, m), meth) - stirling(m - factK(p, m), meth) : stirling(m, meth); }
    function exact(m) { if (cas === 1) { var k2 = factK(p, m); return lnfact(m) - lnfact(k2) - lnfact(m - k2); } return lnfact(m); }
    var val = approx(N), ex = factExact(p), ms = [];
    for (i = 0; i <= 40; i++) ms.push(Math.max(1, I(1 + (N - 1) * i / 40.0)));
    ms = uniqSorted(ms);
    return base(val, ex, N, ms.map(function (m) { return m; }), ms.map(exact), ms.map(approx), [N], [val], { K: K });
  });

  // ====================================================================================== frame transformations
  function frameAt(p, f) {
    var cas = I(p.cas);
    if (cas === 1) return Math.tanh(Math.atanh(p.u) - f * Math.atanh(p.v));
    if (cas === 2) { var th = f * p.th; return p.x * Math.cos(th) + p.y * Math.sin(th); }
    return p.u - f * p.v;
  }
  function frameExact(p) { return frameAt(p, 1.0); }
  var CwFrame = kernel({ cas: 0.0, method: 0.0, n: 16.0, u: 0.6, v: 0.5, x: 1.0, y: 0.5, th: 0.8 }, function (p) {
    var cas = I(p.cas), n = Math.max(1, I(p.n)), a, b, d, k, obs = [], t2;
    if (cas === 2) { a = p.x; b = p.y; d = p.th / n; }
    else if (cas === 1) { var uu = p.u, g = 1.0 / Math.sqrt(1.0 - uu * uu); a = g; b = g * uu; d = Math.atanh(p.v) / n; }
    else { a = 1.0; b = p.u; d = p.v / n; }
    for (k = 0; k <= n; k++) {
      obs.push(cas === 2 ? a : b / a);
      if (k === n) break;
      if (cas === 2) { t2 = a + d * b; b = b - d * a; a = t2; }
      else if (cas === 1) { t2 = a - d * b; b = b - d * a; a = t2; }
      else { b = b - d * a; }
    }
    var val = obs[obs.length - 1], ex = frameExact(p), idx = [];
    for (k = 0; k <= 40; k++) idx.push(I(n * k / 40.0));
    idx = uniqSorted(idx);
    var inv = cas === 1 ? a * a - b * b : (cas === 2 ? a * a + b * b : a);
    return base(val, ex, n, idx.map(function (q) { return q / n; }), idx.map(function (q) { return frameAt(p, q / n); }),
      idx.map(function (q) { return obs[q]; }), [], [], { inv: inv });
  });

  // ====================================================================================== vector fields
  function vfPhi(x, y, z) { return Math.sin(x) * Math.cos(y) * Math.exp(z); }
  function vfF(x, y, z) { return [Math.sin(x * y), Math.cos(y * z), Math.exp(x * z)]; }
  function vfG(x, y, z) { return [-Math.exp(x) * Math.sin(y), y * Math.sin(x), z * z]; }
  function vfExactAt(cas, x, y, z) {
    if (cas === 1) return y * Math.cos(x * y) - z * Math.sin(y * z) + x * Math.exp(x * z);
    if (cas === 2) return y * Math.cos(x) + Math.exp(x) * Math.cos(y);
    var gx = Math.cos(x) * Math.cos(y) * Math.exp(z), gy = -Math.sin(x) * Math.sin(y) * Math.exp(z), gz = Math.sin(x) * Math.cos(y) * Math.exp(z);
    return Math.sqrt(gx * gx + gy * gy + gz * gz);
  }
  function vfNumAt(cas, meth, h, x, y, z) {
    function d(fn, comp, axis) {
      var e = [0.0, 0.0, 0.0]; e[axis] = h;
      var fp = fn(x + e[0], y + e[1], z + e[2]);
      if (meth === 1) {
        var f0 = fn(x, y, z);
        return ((comp >= 0 ? fp[comp] : fp) - (comp >= 0 ? f0[comp] : f0)) / h;
      }
      var fm = fn(x - e[0], y - e[1], z - e[2]);
      return ((comp >= 0 ? fp[comp] : fp) - (comp >= 0 ? fm[comp] : fm)) / (2 * h);
    }
    if (cas === 1) return d(vfF, 0, 0) + d(vfF, 1, 1) + d(vfF, 2, 2);
    if (cas === 2) return d(vfG, 1, 0) - d(vfG, 0, 1);
    var gx = d(vfPhi, -1, 0), gy = d(vfPhi, -1, 1), gz = d(vfPhi, -1, 2);
    return Math.sqrt(gx * gx + gy * gy + gz * gz);
  }
  function vfExact(p) { return vfExactAt(I(p.cas), p.x0, p.y0, p.z0); }
  var CwVfield = kernel({ cas: 0.0, method: 0.0, n: 16.0, x0: 0.7, y0: 0.4, z0: 0.3 }, function (p) {
    var cas = I(p.cas), meth = I(p.method), n = Math.max(1, I(p.n)), h = 1.0 / n, x0 = p.x0, y0 = p.y0, z0 = p.z0, i, j;
    var val = vfNumAt(cas, meth, h, x0, y0, z0), ex = vfExact(p);
    var cx = grid(x0 - 1.0, x0 + 1.0, 40);
    var ce = cx.map(function (x) { return vfExactAt(cas, x, y0, z0); });
    var cy = cx.map(function (x) { return vfNumAt(cas, meth, h, x, y0, z0); });
    var px = meth === 0 ? [x0 - h, x0, x0 + h] : [x0, x0 + h];
    var py = px.map(function (x) { return vfNumAt(cas, meth, h, x, y0, z0); });
    var arr = [];
    for (j = 0; j < 9; j++) for (i = 0; i < 9; i++) {
      var xx = x0 - 1.0 + i * 0.25, yy = y0 - 1.0 + j * 0.25, F;
      if (cas === 1) { F = vfF(xx, yy, z0); arr.push(xx, yy, F[0], F[1]); }
      else if (cas === 2) { F = vfG(xx, yy, z0); arr.push(xx, yy, F[0], F[1]); }
      else arr.push(xx, yy, Math.cos(xx) * Math.cos(yy) * Math.exp(z0), -Math.sin(xx) * Math.sin(yy) * Math.exp(z0));
    }
    return base(val, ex, n, cx, ce, cy, px, py, { arrows: arr, h: h });
  });

  // ====================================================================================== wave groups
  function gwOmega(cas, k, p) { return cas === 1 ? Math.sqrt(p.s * k * k * k) : Math.sqrt(p.g * k); }
  function gwExact(p) { var cas = I(p.cas), k = p.k0; return cas === 1 ? 1.5 * Math.sqrt(p.s * k) : 0.5 * Math.sqrt(p.g / k); }
  var CwGroup = kernel({ cas: 0.0, method: 0.0, n: 4.0, k0: 1.0, w: 0.8, T: 4.0, g: 1.0, s: 1.0 }, function (p) {
    var cas = I(p.cas), n = Math.max(1, I(p.n)), k0 = p.k0, T = p.T, dk = p.w * k0 / n;
    var k1 = k0 - 0.5 * dk, k2 = k0 + 0.5 * dk, w1 = gwOmega(cas, k1, p), w2 = gwOmega(cas, k2, p);
    var Lw = 2 * PI / dk, M = 2000, best = -1.0, bi = 0, vals = [], i, x, a1, a2, re, im, v;
    for (i = 0; i < M; i++) {
      x = Lw * i / M; a1 = k1 * x - w1 * T; a2 = k2 * x - w2 * T;
      re = Math.cos(a1) + Math.cos(a2); im = Math.sin(a1) + Math.sin(a2); v = re * re + im * im;
      vals.push(v);
      if (v > best) { best = v; bi = i; }
    }
    var ym = vals[mod(bi - 1, M)], y0 = vals[bi], yp = vals[mod(bi + 1, M)], den = ym - 2 * y0 + yp;
    var off = Math.abs(den) > 1e-300 ? 0.5 * (ym - yp) / den : 0.0;
    var xpk = Lw * (bi + off) / M, val = xpk / T, ex = gwExact(p), vp = gwOmega(cas, k0, p) / k0;
    var cx = grid(0.0, 2.0 * Lw, 300), cy = [], ce = [];
    for (i = 0; i < cx.length; i++) {
      x = cx[i]; a1 = k1 * x - w1 * T; a2 = k2 * x - w2 * T;
      cy.push(Math.cos(a1) + Math.cos(a2));
      ce.push(2.0 * Math.abs(Math.cos(0.5 * (dk * x - (w2 - w1) * T))));
    }
    return base(val, ex, n, cx, ce, cy, [xpk], [2.0], { vp: vp, dk: dk, Lw: Lw });
  });

  // ====================================================================================== graphics transformations
  function gfxMap(cas, p, x, y) {
    var c, s;
    if (cas === 1) { c = Math.cos(2 * p.al); s = Math.sin(2 * p.al); return [c * x + s * y, s * x - c * y]; }
    if (cas === 2) return [x + p.sh * y, y];
    if (cas === 3) { c = Math.cos(p.th); s = Math.sin(p.th); return [c * x - s * y, s * x + c * y]; }
    return [x + p.tx, y + p.ty];
  }
  function gfxExact(p) {
    var cas = I(p.cas);
    if (I(p.what) === 1) return gfxMap(cas, p, p.cx0, p.cy0)[0];
    return (cas === 1 ? -1.0 : 1.0) * PI * p.r * p.r;
  }
  var CwGfx = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 24.0, r: 1.0, cx0: 1.5, cy0: 0.5, tx: 2.0, ty: 1.0, al: 0.5, sh: 0.6, th: 0.7 }, function (p) {
    var cas = I(p.cas), what = I(p.what), n = Math.max(3, I(p.n)), xs = [], ys = [], ox = [], oy = [], k, j;
    for (k = 0; k < n; k++) {
      var a = 2 * PI * k / n, x = p.cx0 + p.r * Math.cos(a), y = p.cy0 + p.r * Math.sin(a), q = gfxMap(cas, p, x, y);
      ox.push(x); oy.push(y); xs.push(q[0]); ys.push(q[1]);
    }
    var A2 = 0.0, Cx = 0.0, cr;
    for (k = 0; k < n; k++) { j = (k + 1) % n; cr = xs[k] * ys[j] - xs[j] * ys[k]; A2 += cr; Cx += (xs[k] + xs[j]) * cr; }
    var area = 0.5 * A2, cxm = Math.abs(A2) > 1e-300 ? Cx / (3.0 * A2) : 0.0;
    var val = what === 1 ? cxm : area;
    return base(val, gfxExact(p), n, ox.concat([ox[0]]), oy.concat([oy[0]]), [], xs.concat([xs[0]]), ys.concat([ys[0]]), { area: area, cxm: cxm });
  });

  // ====================================================================================== anharmonic radial Schrodinger
  function ahUnits(p) {
    var hw = p.hbarc * Math.sqrt(p.kk / p.mc2), a = Math.sqrt(Math.sqrt(p.hbarc * p.hbarc / (p.mc2 * p.kk)));
    return [hw, a, p.bb * a * a * a / hw];
  }
  function ahV(r, bm) { return 0.5 * r * r + bm * r * r * r / 3.0; }
  function ahShoot(E, bm, h, N, keep) {
    function q(r) { return 2.0 * (E - ahV(r, bm)); }
    var c = h * h / 12.0, u0 = 0.0, u1 = h, us = keep ? [u0, u1] : null, f0 = 1.0 + c * q(0.0), f1 = 1.0 + c * q(h), i, r2, f2, u2;
    for (i = 1; i < N; i++) {
      r2 = (i + 1) * h; f2 = 1.0 + c * q(r2);
      u2 = ((12.0 - 10.0 * f1) * u1 - f0 * u0) / f2;
      u0 = u1; u1 = u2; f0 = f1; f1 = f2;
      if (keep) us.push(u2);
      if (Math.abs(u1) > 1e250) break;
    }
    return [u1, us];
  }
  function ahNumerov(p, n) {
    var U = ahUnits(p), bm = U[2], h = p.rmax / n, lo = p.Elo, hi = p.Ehi, it, mid;
    var slo = ahShoot(lo, bm, h, n, false)[0] > 0;
    for (it = 0; it < 64; it++) {
      mid = 0.5 * (lo + hi);
      if ((ahShoot(mid, bm, h, n, false)[0] > 0) === slo) lo = mid; else hi = mid;
    }
    var E = 0.5 * (lo + hi), us = ahShoot(E, bm, h, n, true)[1], cut = us.length - 1, pk = 0.0, i, half = Math.floor(us.length / 2);
    for (i = 0; i < half; i++) pk = Math.max(pk, Math.abs(us[i]));
    for (i = half; i < us.length - 1; i++) {
      if (Math.abs(us[i + 1]) > Math.abs(us[i]) && Math.abs(us[i]) < 1e-6 * pk) { cut = i; break; }
    }
    var s0 = 0.0, s2 = 0.0, w, r;
    for (i = 0; i <= cut; i++) {
      w = (i === 0 || i === cut) ? 0.5 : 1.0; r = i * h;
      s0 += w * us[i] * us[i]; s2 += w * us[i] * us[i] * r * r;
    }
    return [E, s0 > 0 ? s2 / s0 : 0.0, us, h, cut];
  }
  function jacobi(A) {
    var n = A.length, a = A.map(function (r) { return r.slice(); }), V = [], i, j, sw, pi, qi, k;
    for (i = 0; i < n; i++) { V.push([]); for (j = 0; j < n; j++) V[i].push(i === j ? 1.0 : 0.0); }
    for (sw = 0; sw < 60; sw++) {
      var off = 0.0;
      for (i = 0; i < n; i++) for (j = i + 1; j < n; j++) off += a[i][j] * a[i][j];
      if (off < 1e-30) break;
      for (pi = 0; pi < n - 1; pi++) for (qi = pi + 1; qi < n; qi++) {
        var apq = a[pi][qi];
        if (Math.abs(apq) < 1e-300) continue;
        var th = (a[qi][qi] - a[pi][pi]) / (2.0 * apq);
        var t = (th >= 0 ? 1.0 : -1.0) / (Math.abs(th) + Math.sqrt(th * th + 1.0));
        var c = 1.0 / Math.sqrt(t * t + 1.0), s = t * c, x1, x2;
        for (k = 0; k < n; k++) { x1 = a[k][pi]; x2 = a[k][qi]; a[k][pi] = c * x1 - s * x2; a[k][qi] = s * x1 + c * x2; }
        for (k = 0; k < n; k++) { x1 = a[pi][k]; x2 = a[qi][k]; a[pi][k] = c * x1 - s * x2; a[qi][k] = s * x1 + c * x2; }
        for (k = 0; k < n; k++) { x1 = V[k][pi]; x2 = V[k][qi]; V[k][pi] = c * x1 - s * x2; V[k][qi] = s * x1 + c * x2; }
      }
    }
    var ev = []; for (i = 0; i < n; i++) ev.push(a[i][i]);
    return [ev, V];
  }
  function ahRitz(p) {
    var U = ahUnits(p), bm = U[2], NB = 18, G = 1600, R = 9.0, h = R / G, rs = [], B = [], i, k, l;
    for (i = 0; i <= G; i++) rs.push(i * h);
    for (k = 0; k < NB; k++) { var row = []; for (i = 0; i <= G; i++) row.push(0.0); B.push(row); }
    for (i = 0; i <= G; i++) {
      var r = rs[i], t = r * r, L0 = 1.0, L1 = 1.5 - t, g = r * Math.exp(-0.5 * t), L2;
      B[0][i] = g * L0;
      if (NB > 1) B[1][i] = g * L1;
      for (k = 1; k < NB - 1; k++) { L2 = ((2 * k + 1.5 - t) * L1 - (k + 0.5) * L0) / (k + 1); L0 = L1; L1 = L2; B[k + 1][i] = g * L1; }
    }
    for (k = 0; k < NB; k++) {
      var s = 0.0;
      for (i = 0; i <= G; i++) s += B[k][i] * B[k][i];
      var nk = 1.0 / Math.sqrt(s * h);
      for (i = 0; i <= G; i++) B[k][i] *= nk;
    }
    var H = [], X2 = [];
    for (k = 0; k < NB; k++) { H.push([]); X2.push([]); for (l = 0; l < NB; l++) { H[k].push(0.0); X2[k].push(0.0); } }
    var r3 = rs.map(function (q) { return q * q * q; }), r2 = rs.map(function (q) { return q * q; });
    for (k = 0; k < NB; k++) for (l = k; l < NB; l++) {
      var s3 = 0.0, s2 = 0.0, w;
      for (i = 0; i <= G; i++) { w = B[k][i] * B[l][i]; s3 += w * r3[i]; s2 += w * r2[i]; }
      s3 *= h; s2 *= h;
      H[k][l] = H[l][k] = bm * s3 / 3.0 + (k === l ? (2 * k + 1.5) : 0.0);
      X2[k][l] = X2[l][k] = s2;
    }
    var J = jacobi(H), ev = J[0], V = J[1], j0 = 0, j;
    for (j = 0; j < NB; j++) if (ev[j] < ev[j0]) j0 = j;
    var c = []; for (k = 0; k < NB; k++) c.push(V[k][j0]);
    var r2m = 0.0;
    for (k = 0; k < NB; k++) for (l = 0; l < NB; l++) r2m += c[k] * X2[k][l] * c[l];
    return [ev[j0], r2m];
  }
  function ahExact(p) {
    var U = ahUnits(p), hw = U[0], a = U[1], bm = U[2], what = I(p.what);
    if (Math.abs(bm) < 1e-15) return what === 0 ? 1.5 * hw : 1.5 * a * a;
    var R = ahRitz(p);
    return what === 0 ? R[0] * hw : R[1] * a * a;
  }
  var CwAnharm = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 200.0, hbarc: 197.3269804, mc2: 940.0, kk: 100.0, bb: 0.0, rmax: 7.0, Elo: 0.5, Ehi: 3.0 }, function (p) {
    var what = I(p.what), n = Math.max(8, I(p.n)), U = ahUnits(p), hw = U[0], a = U[1], bm = U[2];
    var R = ahNumerov(p, n), E = R[0], r2 = R[1], us = R[2], h = R[3], cut = R[4], i;
    var val = what === 0 ? E * hw : r2 * a * a, ex = ahExact(p), idx = [];
    for (i = 0; i <= 60; i++) idx.push(I(cut * i / 60.0));
    idx = uniqSorted(idx);
    var mx = 0; for (i = 0; i <= cut; i++) mx = Math.max(mx, Math.abs(us[i]));
    if (!mx) mx = 1.0;
    return base(val, ex, n, idx.map(function (q) { return q * h * a; }), [], idx.map(function (q) { return us[q] / mx; }), [], [],
      { Vr: idx.map(function (q) { return ahV(q * h, bm); }), E: E, hw: hw, a: a, bm: bm });
  });

  // ====================================================================================== Lennard-Jones molecular dynamics
  function ljForces(X, Y, L, rc2, FX, FY) {
    var N = X.length, i, j;
    for (i = 0; i < N; i++) { FX[i] = 0.0; FY[i] = 0.0; }
    var ic2 = 1.0 / rc2, ic6 = ic2 * ic2 * ic2, shift = 4.0 * (ic6 * ic6 - ic6), hL = 0.5 * L, pe = 0.0;
    for (i = 0; i < N - 1; i++) {
      var xi = X[i], yi = Y[i];
      for (j = i + 1; j < N; j++) {
        var dx = xi - X[j], dy = yi - Y[j];
        if (dx > hL) dx -= L; else if (dx < -hL) dx += L;
        if (dy > hL) dy -= L; else if (dy < -hL) dy += L;
        var r2 = dx * dx + dy * dy;
        if (r2 < rc2) {
          var i2 = 1.0 / r2, i6 = i2 * i2 * i2, f = 24.0 * i2 * i6 * (2.0 * i6 - 1.0);
          FX[i] += f * dx; FY[i] += f * dy; FX[j] -= f * dx; FY[j] -= f * dy;
          pe += 4.0 * (i6 * i6 - i6) - shift;
        }
      }
    }
    return pe;
  }
  function ljRun(p, n) {
    var side = Math.max(2, I(p.side)), N = side * side, L = Math.sqrt(N / p.rho), dt = p.dt, rc2 = p.rc * p.rc, what = I(p.what);
    var st = lcg(p.seed), X = [], Y = [], VX = [], VY = [], a = L / side, i, j;
    for (j = 0; j < side; j++) for (i = 0; i < side; i++) {
      X.push((i + 0.5) * a); Y.push((j + 0.5) * a);
      VX.push(2.0 * u(st) - 1.0);
      var vy = 2.0 * u(st) - 1.0;
      VY.push(what === 1 ? 0.0 : vy);
    }
    var mx = sumArr(VX) / N, my = sumArr(VY) / N, ke = 0.0;
    for (i = 0; i < N; i++) { VX[i] -= mx; VY[i] -= my; ke += VX[i] * VX[i] + VY[i] * VY[i]; }
    var sc = Math.sqrt(2.0 * (N - 1) * p.T0 / ke);
    for (i = 0; i < N; i++) { VX[i] *= sc; VY[i] *= sc; }
    var FX = [], FY = [];
    for (i = 0; i < N; i++) { FX.push(0.0); FY.push(0.0); }
    ljForces(X, Y, L, rc2, FX, FY);
    var neq = Math.max(0, I(p.neq)), total = neq + n;
    var sv = 0.0, sv2 = 0.0, sx2 = 0.0, sy2 = 0.0, cnt = 0.0, cnt2 = 0.0, ns = 0.0, hl = 0.5 * L;
    var tt = [], ty = [], e0 = 0.0, e1 = 0.0, every = Math.max(1, Math.floor(total / 60)), step;
    for (step = 0; step < total; step++) {
      var hdt = 0.5 * dt;
      for (i = 0; i < N; i++) {
        VX[i] += hdt * FX[i]; VY[i] += hdt * FY[i];
        X[i] += dt * VX[i]; Y[i] += dt * VY[i];
        if (X[i] >= L) X[i] -= L; else if (X[i] < 0.0) X[i] += L;
        if (Y[i] >= L) Y[i] -= L; else if (Y[i] < 0.0) Y[i] += L;
      }
      var pe = ljForces(X, Y, L, rc2, FX, FY), kx = 0.0, ky = 0.0;
      for (i = 0; i < N; i++) { VX[i] += hdt * FX[i]; VY[i] += hdt * FY[i]; kx += VX[i] * VX[i]; ky += VY[i] * VY[i]; }
      if (step === 0) e0 = 0.5 * (kx + ky) + pe;
      e1 = 0.5 * (kx + ky) + pe;
      if (step >= neq) {
        ns += 1.0; sx2 += kx; sy2 += ky;
        var c = 0.0;
        for (i = 0; i < N; i++) {
          var v2 = VX[i] * VX[i] + VY[i] * VY[i];
          sv += Math.sqrt(v2); sv2 += v2;
          if (X[i] < hl) c += 1.0;
        }
        cnt += c; cnt2 += c * c;
      }
      if (step % every === 0) {
        tt.push((step + 1) * dt);
        if (what === 1) ty.push(kx > 0 ? ky / kx : 0.0);
        else if (what === 2) ty.push(ns > 0 ? cnt / Math.max(ns, 1.0) / (hl * L) : 0.0);
        else ty.push(ns > 0 ? (sv / (ns * N)) / Math.sqrt(sv2 / (ns * N)) : 0.0);
      }
    }
    var out = { N: N, L: L, ns: ns, e0: e0, e1: e1, tt: tt, ty: ty, X: X.slice(), Y: Y.slice() };
    if (what === 1) out.val = sx2 > 0 ? sy2 / sx2 : 0.0;
    else if (what === 2) { var m = cnt / ns; out.val = m / (hl * L); out.fano = m > 0 ? (cnt2 / ns - m * m) / m : 0.0; }
    else out.val = (sv / (ns * N)) / Math.sqrt(sv2 / (ns * N));
    out.Tk = ns > 0 ? (sx2 + sy2) / (ns * (2.0 * N - 2.0)) : 0.0;
    return out;
  }
  function ljExact(p) { var w = I(p.what); return w === 1 ? 1.0 : (w === 2 ? p.rho : 0.5 * Math.sqrt(PI)); }
  var CwLjmd = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 400.0, side: 6.0, rho: 0.25, T0: 1.0, dt: 0.005, rc: 2.5, neq: 200.0, seed: 2024.0 }, function (p) {
    var n = Math.max(1, I(p.n)), o = ljRun(p, n), ex = ljExact(p), pts = [], i;
    for (i = 0; i < o.X.length; i++) pts.push(o.X[i] / o.L, o.Y[i] / o.L);
    return base(o.val, ex, n, o.tt, o.tt.map(function () { return ex; }), o.ty, [], [],
      { pts: pts, Tk: o.Tk, drift: (o.e1 - o.e0) / Math.max(Math.abs(o.e0), 1e-12), fano: o.fano !== undefined ? o.fano : 0.0, Np: o.N, Lbox: o.L });
  });

  // ====================================================================================== few-level partition functions
  function lvStates(p) {
    var L = Math.max(2, I(p.L)), st = I(p.cas), out = [], j, k;
    for (j = 0; j < L; j++) for (k = 0; k < L; k++) {
      if (st === 1 && k <= j) continue;
      if (st === 2 && k < j) continue;
      out.push([(j + k) * p.eps, 1.0]);
    }
    return out;
  }
  function lvThermo(p, T) {
    var ss = lvStates(p), e0 = Infinity, i, Z = 0.0, S1 = 0.0, S2 = 0.0;
    for (i = 0; i < ss.length; i++) e0 = Math.min(e0, ss[i][0]);
    for (i = 0; i < ss.length; i++) { var e = ss[i][0], w = ss[i][1] * Math.exp(-(e - e0) / T); Z += w; S1 += w * e; S2 += w * e * e; }
    var U = S1 / Z;
    return [Z, U, S2 / Z, e0 - T * Math.log(Z)];
  }
  function lvExact(p) {
    var T = p.T, th = lvThermo(p, T), U = th[1];
    if (I(p.what) === 1) return (U - th[3]) / T;
    return (th[2] - U * U) / (T * T);
  }
  var CwLevels = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 8.0, L: 3.0, eps: 1.0, T: 0.8 }, function (p) {
    var meth = I(p.method), what = I(p.what), n = Math.max(1, I(p.n)), T = p.T;
    function q(t) { var th = lvThermo(p, t); return what === 0 ? th[1] : -th[3]; }
    function deriv(t, h) { return meth === 1 ? (q(t + h) - q(t)) / h : (q(t + h) - q(t - h)) / (2 * h); }
    var h = T / n, val = deriv(T, h), ex = lvExact(p), cx = grid(0.1 * T, 3.0 * T, 50), ce = [], cy = [], i;
    for (i = 0; i < cx.length; i++) {
      var t = cx[i], th = lvThermo(p, t);
      ce.push(what === 1 ? (th[1] - th[3]) / t : (th[2] - th[1] * th[1]) / (t * t));
      cy.push(deriv(t, t / n));
    }
    return base(val, ex, n, cx, ce, cy, [T], [val], { Z: lvThermo(p, T)[0], nstates: lvStates(p).length });
  });

  // ====================================================================================== Maxwell speed distribution
  function mxM(p) { return p.M * 1e-3 / NA; }
  function mxF(v, p) { var a = mxM(p) / (2 * KB * p.T); return 4 * PI * Math.pow(a / PI, 1.5) * v * v * Math.exp(-a * v * v); }
  function mxExact(p) {
    var m = mxM(p), T = p.T, w = I(p.what);
    if (w === 1) return Math.sqrt(3 * KB * T / m);
    if (w === 2) return Math.sqrt(2 * KB * T / m);
    return Math.sqrt(8 * KB * T / (PI * m));
  }
  var CwMaxwell = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 16.0, M: 28.0134, T: 300.0 }, function (p) {
    var w = I(p.what), n = Math.max(2, I(p.n)), vp = Math.sqrt(2 * KB * p.T / mxM(p)), vmax = 6.0 * vp, val, px = [], py, i;
    if (w === 2) {
      var h = vmax / n, fs = [], bi = 0;
      for (i = 0; i <= n; i++) fs.push(mxF(h * i, p));
      for (i = 0; i <= n; i++) if (fs[i] > fs[bi]) bi = i;
      bi = Math.max(1, Math.min(n - 1, bi));
      var den = fs[bi - 1] - 2 * fs[bi] + fs[bi + 1], off = Math.abs(den) > 1e-300 ? 0.5 * (fs[bi - 1] - fs[bi + 1]) / den : 0.0;
      val = h * (bi + off);
      for (i = 0; i <= n; i++) px.push(h * i);
      py = fs;
    } else {
      var k = w === 1 ? 2 : 1;
      var Iv = simpson(function (v) { return Math.pow(v, k) * mxF(v, p); }, 0.0, vmax, n);
      val = w === 1 ? Math.sqrt(Iv) : Iv;
      var nn = Math.max(2, n - (n % 2));
      for (i = 0; i <= nn; i++) px.push(vmax * i / nn);
      py = px.map(function (v) { return mxF(v, p); });
    }
    var ex = mxExact(p), cx = grid(0.0, vmax, 80);
    return base(val, ex, n, cx, cx.map(function (v) { return mxF(v, p); }), [], thin(px, 80), thin(py, 80), { vline: ex, vfound: val });
  });

  // ====================================================================================== specific heat of solids
  var R_GAS = NA * KB;
  function debyeJ4(x) {
    var s = 0.0, k = 1, P4 = Math.pow(PI, 4) / 15.0;
    while (k < 20000) {
      var e = Math.exp(-k * x), term = e * (x * x * x / k + 3 * x * x / (k * k) + 6 * x / (k * k * k) + 6.0 / (k * k * k * k));
      s += term;
      if (term < 1e-18 * P4 && k > 3) break;
      k += 1;
    }
    return -Math.pow(x, 4) / Math.expm1(x) + 4 * (P4 - s);
  }
  function hcEinsteinU(T, th) { return 3 * R_GAS * th / Math.expm1(th / T); }
  function hcExact(p) {
    var meth = I(p.method), T = p.T, x;
    if (meth === 1) { x = p.thE / T; return 3 * R_GAS * x * x * Math.exp(x) / (Math.expm1(x) * Math.expm1(x)); }
    if (meth === 2) { x = p.thD / T; return 9 * R_GAS * debyeJ4(x) / (x * x * x); }
    return 3 * R_GAS;
  }
  function debyeIntegrand(t) { if (t === 0.0) return 0.0; var em = Math.expm1(t); return Math.pow(t, 4) * Math.exp(t) / (em * em); }
  var CwHeatcap = kernel({ cas: 0.0, method: 2.0, n: 8.0, T: 100.0, thD: 343.0, thE: 265.7 }, function (p) {
    var meth = I(p.method), n = Math.max(2, I(p.n));
    function Cnum(T) {
      var h = T / n;
      if (meth === 0) return (3 * R_GAS * (T + h) - 3 * R_GAS * (T - h)) / (2 * h);
      if (meth === 1) return (hcEinsteinU(T + h, p.thE) - hcEinsteinU(T - h, p.thE)) / (2 * h);
      var x = p.thD / T;
      return 9 * R_GAS * simpson(debyeIntegrand, 0.0, x, n) / (x * x * x);
    }
    function Cex(T) { var q = copy(p); q.T = T; return hcExact(q); }
    var T = p.T, val = Cnum(T), ex = hcExact(p), top = Math.max(p.thD, p.thE) * 1.5, cx = grid(0.04 * top, top, 50);
    return base(val, ex, n, cx, cx.map(Cex), cx.map(Cnum), [T], [val], { R: R_GAS });
  });

  // ====================================================================================== quantum distributions
  function zeta(s) {
    var N = 20, tot = 0.0, k, j;
    for (k = 1; k < N; k++) tot += Math.pow(k, -s);
    tot += Math.pow(N, 1 - s) / (s - 1) + 0.5 * Math.pow(N, -s);
    var B = [1.0 / 6, -1.0 / 30, 1.0 / 42, -1.0 / 30], fac = 1.0, poch = s;
    for (j = 0; j < 4; j++) {
      var k2 = 2 * (j + 1);
      fac *= (k2 - 1) * k2;
      tot += B[j] / fac * poch * Math.pow(N, -s - k2 + 1);
      poch *= (s + k2 - 1) * (s + k2);
    }
    return tot;
  }
  function qdA(p) { return I(p.cas) === 1 ? 2.0 : 0.5; }
  function qdRatio(meth, a) {
    if (meth === 0) return a + 1.0;
    function X(s) { var z = zeta(s); return meth === 1 ? (1.0 - Math.pow(2.0, 1.0 - s)) * z : z; }
    return (a + 1.0) * X(a + 2.0) / X(a + 1.0);
  }
  function qdKT(p) { return KB * p.T / QE; }
  function qdExact(p) { return qdRatio(I(p.method), qdA(p)) * qdKT(p); }
  function qdOcc(meth, x) {
    if (meth === 1) return 1.0 / (Math.exp(x) + 1.0);
    if (meth === 2) return x > 0 ? 1.0 / Math.expm1(x) : 0.0;
    return Math.exp(-x);
  }
  function qdInt(meth, a, n) {
    function g(t) {
      if (t === 0.0) { if (meth === 2 && Math.abs(2 * a - 1) < 1e-12) return 2.0; return 0.0; }
      return 2.0 * Math.pow(t, 2 * a + 1) * qdOcc(meth, t * t);
    }
    return simpson(g, 0.0, 7.0, n);
  }
  var CwQdist = kernel({ cas: 0.0, method: 0.0, n: 16.0, T: 300.0 }, function (p) {
    var meth = I(p.method), n = Math.max(2, I(p.n)), a = qdA(p), kT = qdKT(p);
    var val = qdInt(meth, a + 1.0, n) / qdInt(meth, a, n) * kT, ex = qdExact(p), cx = grid(0.0, 8.0, 80);
    return base(val, ex, n, cx, cx.map(function (x) { return (x > 0 || meth !== 2) ? qdOcc(meth, x) : 0.0; }),
      cx.map(function (x) { return qdOcc(0, x); }), [], [], { cy2: cx.map(function (x) { return qdOcc(1, x); }), kT: kT, ratio: val / kT });
  });

  // ====================================================================================== fractals
  var FRV = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]];
  function frSlope(xs, ys) {
    var n = xs.length, sx = sumArr(xs), sy = sumArr(ys), sxx = 0.0, sxy = 0.0, i;
    for (i = 0; i < n; i++) { sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; }
    var den = n * sxx - sx * sx;
    return Math.abs(den) > 1e-300 ? (n * sxy - sx * sy) / den : 0.0;
  }
  function frBoxes(X, Y, k) {
    var e = Math.pow(2, k), seen = {}, c = 0, i, key;
    for (i = 0; i < X.length; i++) {
      key = Math.floor(X[i] * e) * 4096 + Math.floor(Y[i] * e);
      if (!seen[key]) { seen[key] = 1; c++; }
    }
    return c;
  }
  function frExact(p) { return I(p.cas) === 2 ? 1.5 : Math.log(3.0) / Math.log(2.0); }
  var CwFractal = kernel({ cas: 0.0, method: 0.0, n: 6.0, kmax: 6.0, seed: 4242.0 }, function (p) {
    var cas = I(p.cas), n = Math.max(1, I(p.n)), kmax = Math.max(2, I(p.kmax)), X = [], Y = [], st, i, k, lx = [], ly = [];
    if (cas === 2) {
      st = lcg(p.seed);
      var S = 0.0, ys = [0.0], lags = [1, 2, 4, 8, 16, 32], li;
      for (i = 0; i < n; i++) { S += u(st) < 0.5 ? 1.0 : -1.0; ys.push(S); }
      for (li = 0; li < lags.length; li++) {
        var t = lags[li], s = 0.0, c = 0;
        for (i = 0; i < n - t + 1; i++) { var d = ys[i + t] - ys[i]; s += d * d; c += 1; }
        lx.push(Math.log(t));
        ly.push(c > 0 && s > 0 ? Math.log(Math.sqrt(s / c)) : 0.0);
      }
      var H = frSlope(lx, ly), prof = thin(ys, 400), pxs = [];
      for (i = 0; i < prof.length; i++) pxs.push(i / Math.max(1, prof.length - 1));
      return base(2.0 - H, frExact(p), n, lx, lx.map(function (x) { return ly[0] + 0.5 * (x - lx[0]); }), ly, lx, ly,
        { H: H, path_x: pxs, path_y: prof });
    }
    if (cas === 1) {
      st = lcg(p.seed);
      var x = 1.0 / 3.0, y = 1.0 / 3.0;
      for (i = 0; i < n + 20; i++) {
        var r = u(st), j = r < 1.0 / 3.0 ? 0 : (r < 2.0 / 3.0 ? 1 : 2);
        x = 0.5 * (x + FRV[j][0]); y = 0.5 * (y + FRV[j][1]);
        if (i >= 20) { X.push(x); Y.push(y); }
      }
    } else {
      X = [1.0 / 3.0]; Y = [1.0 / 3.0];
      var lev, v;
      for (lev = 0; lev < Math.min(n, 9); lev++) {
        var X2 = [], Y2 = [];
        for (i = 0; i < X.length; i++) for (v = 0; v < 3; v++) { X2.push(0.5 * (X[i] + FRV[v][0])); Y2.push(0.5 * (Y[i] + FRV[v][1])); }
        X = X2; Y = Y2;
      }
    }
    for (k = 1; k <= kmax; k++) { lx.push(k * Math.log(2.0)); ly.push(Math.log(frBoxes(X, Y, k))); }
    var val = frSlope(lx, ly), ex = frExact(p), pts = [], step = Math.max(1, Math.floor(X.length / 1500));
    for (i = 0; i < X.length; i += step) pts.push(X[i], Y[i]);
    return base(val, ex, n, lx, lx.map(function (q) { return ly[0] + ex * (q - lx[0]); }), ly, lx, ly, { pts: pts });
  });

  // ====================================================================================== flow visualisation
  function flVel(p, x, y, t) { return [p.a * x, -p.a * y + p.b * Math.cos(p.w * t)]; }
  function flYp(p, t) { var a = p.a, b = p.b, w = p.w; return b / (a * a + w * w) * (a * Math.cos(w * t) + w * Math.sin(w * t)); }
  function flPathExact(p, t0, t1) {
    var a = p.a;
    return [p.x0 * Math.exp(a * (t1 - t0)), flYp(p, t1) + (p.y0 - flYp(p, t0)) * Math.exp(-a * (t1 - t0))];
  }
  function flStreamExact(p, s) {
    var a = p.a, c = p.b * Math.cos(p.w * p.T) / a;
    return [p.x0 * Math.exp(a * s), c + (p.y0 - c) * Math.exp(-a * s)];
  }
  function flRk4(p, x, y, t, h, steps, frozen) {
    var tr = [[x, y]], tf = p.T, k;
    function f(xx, yy, tt) { return flVel(p, xx, yy, frozen ? tf : tt); }
    for (k = 0; k < steps; k++) {
      var k1 = f(x, y, t), k2 = f(x + 0.5 * h * k1[0], y + 0.5 * h * k1[1], t + 0.5 * h);
      var k3 = f(x + 0.5 * h * k2[0], y + 0.5 * h * k2[1], t + 0.5 * h), k4 = f(x + h * k3[0], y + h * k3[1], t + h);
      x += h * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6.0;
      y += h * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6.0;
      t += h;
      tr.push([x, y]);
    }
    return tr;
  }
  function flExact(p) {
    var cas = I(p.cas);
    if (cas === 2) return flStreamExact(p, p.S)[1];
    if (cas === 1) return flPathExact(p, p.tau, p.T)[1];
    return flPathExact(p, 0.0, p.T)[1];
  }
  var CwFlow = kernel({ cas: 0.0, method: 0.0, n: 8.0, a: 0.3, b: 1.0, w: 2.0, x0: 0.5, y0: 0.0, T: 3.0, tau: 1.0, S: 3.0 }, function (p) {
    var cas = I(p.cas), n = Math.max(1, I(p.n)), tr, ex_tr = [], k;
    if (cas === 2) { tr = flRk4(p, p.x0, p.y0, 0.0, p.S / n, n, true); for (k = 0; k <= 60; k++) ex_tr.push(flStreamExact(p, p.S * k / 60.0)); }
    else if (cas === 1) { tr = flRk4(p, p.x0, p.y0, p.tau, (p.T - p.tau) / n, n, false); for (k = 0; k <= 60; k++) ex_tr.push(flPathExact(p, p.T * k / 60.0, p.T)); }
    else { tr = flRk4(p, p.x0, p.y0, 0.0, p.T / n, n, false); for (k = 0; k <= 60; k++) ex_tr.push(flPathExact(p, 0.0, p.T * k / 60.0)); }
    var val = tr[tr.length - 1][1];
    return base(val, flExact(p), n, ex_tr.map(function (q) { return q[0]; }), ex_tr.map(function (q) { return q[1]; }), [],
      tr.map(function (q) { return q[0]; }), tr.map(function (q) { return q[1]; }), { xend: tr[tr.length - 1][0] });
  });

  // ====================================================================================== game theory
  function gmExact(p) {
    if (I(p.cas) === 1) return (p.d - p.c) / (p.a + p.d - p.b - p.c);
    return p.V / p.C;
  }
  var CwGame = kernel({ cas: 0.0, method: 0.0, n: 40.0, V: 2.0, C: 5.0, p0: 0.1, tend: 60.0, a: 2.0, b: -1.0, c: -1.0, d: 1.0 }, function (p) {
    var cas = I(p.cas), n = Math.max(1, I(p.n)), ex = gmExact(p), k, tr = [], val;
    if (cas === 1) {
      var a = p.a, b = p.b, c = p.c, d = p.d, r1 = 1.0, r2 = 0.0, c1 = 1.0, c2 = 0.0, every = Math.max(1, Math.floor(n / 60));
      for (k = 1; k < n; k++) {
        var ur1 = a * c1 + b * c2, ur2 = c * c1 + d * c2, uc1 = a * r1 + c * r2, uc2 = b * r1 + d * r2;
        if (ur1 >= ur2) r1 += 1.0; else r2 += 1.0;
        if (uc1 <= uc2) c1 += 1.0; else c2 += 1.0;
        if (k % every === 0) tr.push([k + 1, r1 / (r1 + r2)]);
      }
      val = r1 / (r1 + r2);
      return base(val, ex, n, tr.map(function (q) { return q[0]; }), tr.map(function () { return ex; }), tr.map(function (q) { return q[1]; }), [], [],
        { colfreq: c1 / (c1 + c2) });
    }
    var V = p.V, C = p.C, h = p.tend / n, x = p.p0;
    tr.push([0.0, x]);
    for (k = 0; k < n; k++) { x = x + h * x * (1.0 - x) * (V - C * x) / 2.0; tr.push([(k + 1) * h, x]); }
    var th = thin(tr, 60);
    return base(x, ex, n, th.map(function (q) { return q[0]; }), th.map(function () { return ex; }), th.map(function (q) { return q[1]; }), [], []);
  });

  // ====================================================================================== discrete convolution
  function cvX(p, k) { return (k >= 0 && k < I(p.Lx)) ? Math.pow(p.al, k) : 0.0; }
  function cvH(p, k) { return (k >= 0 && k < I(p.Lh)) ? Math.pow(p.be, k) : 0.0; }
  function cvExactAt(p, m) {
    var al = p.al, be = p.be, lo = Math.max(0, m - I(p.Lh) + 1), hi = Math.min(m, I(p.Lx) - 1);
    if (hi < lo) return 0.0;
    var q = al / be;
    if (Math.abs(1.0 - q) < 1e-12) return Math.pow(be, m) * (hi - lo + 1);
    return Math.pow(be, m) * (Math.pow(q, lo) - Math.pow(q, hi + 1)) / (1.0 - q);
  }
  function cvExact(p) { return cvExactAt(p, I(p.m)); }
  var CwConv = kernel({ cas: 0.0, method: 0.0, n: 16.0, al: 0.8, be: 0.5, Lx: 12.0, Lh: 10.0, m: 3.0 }, function (p) {
    var meth = I(p.method), Lx = I(p.Lx), Lh = I(p.Lh), Ly = Lx + Lh - 1, n = Math.max(1, I(p.n)), m = I(p.m), y = [], k, j, f, s;
    if (meth === 1) {
      for (k = 0; k < Ly; k++) { s = 0.0; for (j = 0; j < Lx; j++) s += cvX(p, j) * cvH(p, k - j); y.push(s); }
    } else {
      var N = n, xr = [], hr = [];
      for (k = 0; k < N; k++) { xr.push(k < N ? cvX(p, k) : 0.0); hr.push(k < N ? cvH(p, k) : 0.0); }
      for (k = N; k < Lx; k++) xr[k % N] += cvX(p, k);
      for (k = N; k < Lh; k++) hr[k % N] += cvH(p, k);
      var Xr = [], Xi = [];
      for (f = 0; f < N; f++) {
        var a1 = 0.0, a2 = 0.0, b1 = 0.0, b2 = 0.0;
        for (k = 0; k < N; k++) {
          var ang = 2 * PI * f * k / N, c = Math.cos(ang), sn = Math.sin(ang);
          a1 += xr[k] * c; a2 -= xr[k] * sn; b1 += hr[k] * c; b2 -= hr[k] * sn;
        }
        Xr.push(a1 * b1 - a2 * b2); Xi.push(a1 * b2 + a2 * b1);
      }
      for (k = 0; k < N; k++) {
        s = 0.0;
        for (f = 0; f < N; f++) { var an = 2 * PI * f * k / N; s += Xr[f] * Math.cos(an) - Xi[f] * Math.sin(an); }
        y.push(s / N);
      }
    }
    var val = m < y.length ? y[m] : 0.0, ex = cvExact(p), K = Math.max(Ly, y.length), cx = [], ce = [], cy = [];
    for (k = 0; k < K; k++) { cx.push(k); ce.push(cvExactAt(p, k)); cy.push(k < y.length ? y[k] : 0.0); }
    return base(val, ex, n, cx, ce, cy, [m], [val], { Ly: Ly });
  });

  // ====================================================================================== LTI difference equation
  function ltiCoef(p) { var r = p.r, th = p.th; return [2.0 * r * Math.cos(th), -r * r, p.b0, p.b1]; }
  function ltiH(p, w) {
    var c = ltiCoef(p), a1 = c[0], a2 = c[1], b0 = c[2], b1 = c[3];
    var nr = b0 + b1 * Math.cos(w), ni = -b1 * Math.sin(w), dr = 1.0 - a1 * Math.cos(w) - a2 * Math.cos(2 * w), di = a1 * Math.sin(w) + a2 * Math.sin(2 * w);
    return Math.sqrt((nr * nr + ni * ni) / (dr * dr + di * di));
  }
  function ltiExact(p) {
    if (I(p.what) === 1) { var c = ltiCoef(p); return (c[2] + c[3]) / (1.0 - c[0] - c[1]); }
    return ltiH(p, p.w0);
  }
  function ltiRun(p, xin, n) {
    var c = ltiCoef(p), a1 = c[0], a2 = c[1], b0 = c[2], b1 = c[3], y = [], y1 = 0.0, y2 = 0.0, x1 = 0.0, k;
    for (k = 0; k < n; k++) { var x0 = xin(k), v = a1 * y1 + a2 * y2 + b0 * x0 + b1 * x1; y.push(v); y2 = y1; y1 = v; x1 = x0; }
    return y;
  }
  var CwLti = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 32.0, r: 0.8, th: 0.6, b0: 1.0, b1: 0.5, w0: 0.6 }, function (p) {
    var what = I(p.what), n = Math.max(1, I(p.n)), y, val, k;
    if (what === 1) { y = ltiRun(p, function () { return 1.0; }, n); val = y[y.length - 1]; }
    else {
      y = ltiRun(p, function (q) { return q === 0 ? 1.0 : 0.0; }, n);
      var re = 0.0, im = 0.0;
      for (k = 0; k < n; k++) { re += y[k] * Math.cos(p.w0 * k); im -= y[k] * Math.sin(p.w0 * k); }
      val = Math.sqrt(re * re + im * im);
    }
    var ex = ltiExact(p), cx = [];
    for (k = 0; k < y.length; k++) cx.push(k);
    var c = ltiCoef(p), r = p.r, th = p.th, tcx = thin(cx, 80);
    return base(val, ex, n, tcx, what === 1 ? tcx.map(function () { return ex; }) : [], thin(y, 80), tcx, thin(y, 80),
      { poles: [r * Math.cos(th), r * Math.sin(th), r * Math.cos(th), -r * Math.sin(th)], zeros: [Math.abs(c[2]) > 1e-300 ? -c[3] / c[2] : 0.0, 0.0] });
  });

  // ====================================================================================== FIR filter design
  function firTaps(p, N) {
    var meth = I(p.method), wc = p.wc, M = N - 1, h = [], k;
    for (k = 0; k < N; k++) {
      var t = k - 0.5 * M, hd = Math.abs(t) < 1e-12 ? wc / PI : Math.sin(wc * t) / (PI * t), wn;
      if (meth === 1) wn = 0.5 - 0.5 * Math.cos(2 * PI * k / M);
      else if (meth === 2) wn = 0.54 - 0.46 * Math.cos(2 * PI * k / M);
      else wn = 1.0;
      h.push(hd * wn);
    }
    return h;
  }
  function firA(h, w) { var M = h.length - 1, s = 0.0, k; for (k = 0; k < h.length; k++) s += h[k] * Math.cos(w * (k - 0.5 * M)); return s; }
  var CwFir = kernel({ cas: 0.0, method: 0.0, n: 31.0, wc: 1.0 }, function (p) {
    var N = Math.max(5, I(p.n)); if (N % 2 === 0) N += 1;
    var h = firTaps(p, N), wc = p.wc, span = 6 * PI / N, lo = Math.max(1e-6, wc - span), hi = Math.min(PI - 1e-6, wc + span), m = 120, i, it;
    var a = lo, fa = firA(h, a) - 0.5, b = hi;
    for (i = 1; i <= m; i++) {
      var x = lo + (hi - lo) * i / m, fx = firA(h, x) - 0.5;
      if (fa > 0 && 0 >= fx) { b = x; break; }
      a = x; fa = fx;
    }
    for (it = 0; it < 60; it++) { var mid = 0.5 * (a + b); if (firA(h, mid) - 0.5 > 0) a = mid; else b = mid; }
    var val = 0.5 * (a + b), cx = grid(0.0, PI, 120);
    return base(val, wc, N, cx, cx.map(function (w) { return w <= wc ? 1.0 : 0.0; }), cx.map(function (w) { return firA(h, w); }), [val], [0.5],
      { taps: h, dB: cx.map(function (w) { var v = Math.abs(firA(h, w)); return v > 1e-12 ? 20 * Math.log10(v) : -240.0; }) });
  });

  // ====================================================================================== geodesics
  function gdEnds(p) {
    if (I(p.cas) === 1) {
      return [[p.la1, p.lo1], [p.la2, p.lo2]].map(function (q) {
        var a = q[0] * PI / 180.0, b = q[1] * PI / 180.0;
        return [p.R * Math.cos(a) * Math.cos(b), p.R * Math.cos(a) * Math.sin(b), p.R * Math.sin(a)];
      });
    }
    return [[p.xa, p.ya, 0.0], [p.xb, p.yb, 0.0]];
  }
  function gdExact(p) {
    var E = gdEnds(p), A = E[0], B = E[1];
    if (I(p.cas) === 1) {
      var cx = A[1] * B[2] - A[2] * B[1], cy = A[2] * B[0] - A[0] * B[2], cz = A[0] * B[1] - A[1] * B[0], dot = A[0] * B[0] + A[1] * B[1] + A[2] * B[2];
      return p.R * Math.atan2(Math.sqrt(cx * cx + cy * cy + cz * cz), dot);
    }
    return Math.sqrt(Math.pow(B[0] - A[0], 2) + Math.pow(B[1] - A[1], 2));
  }
  var CwGeod = kernel({ cas: 0.0, method: 0.0, n: 8.0, xa: 0.0, ya: 0.0, xb: 3.0, yb: 1.0, bump: 1.0, R: 1.0, la1: 10.0, lo1: 0.0, la2: 50.0, lo2: 100.0 }, function (p) {
    var cas = I(p.cas), n = Math.max(2, I(p.n)), E = gdEnds(p), A = E[0], B = E[1], P = [], k, sw;
    for (k = 0; k <= n; k++) {
      var s = k / n;
      if (cas === 1) {
        var la = (p.la1 + (p.la2 - p.la1) * s) * PI / 180.0, lo = (p.lo1 + (p.lo2 - p.lo1) * s) * PI / 180.0;
        P.push([p.R * Math.cos(la) * Math.cos(lo), p.R * Math.cos(la) * Math.sin(lo), p.R * Math.sin(la)]);
      } else {
        P.push([A[0] + (B[0] - A[0]) * s, A[1] + (B[1] - A[1]) * s + p.bump * Math.sin(PI * s), 0.0]);
      }
    }
    var start = P.map(function (q) { return q.slice(); }), sweeps = 6 * n * n + 50;
    for (sw = 0; sw < sweeps; sw++) {
      for (k = 1; k < n; k++) {
        var x = 0.5 * (P[k - 1][0] + P[k + 1][0]), y = 0.5 * (P[k - 1][1] + P[k + 1][1]), z = 0.5 * (P[k - 1][2] + P[k + 1][2]);
        if (cas === 1) { var rr = Math.sqrt(x * x + y * y + z * z); x = p.R * x / rr; y = p.R * y / rr; z = p.R * z / rr; }
        P[k] = [x, y, z];
      }
    }
    function length(Q) {
      var s2 = 0.0, j;
      for (j = 0; j < n; j++) { var dx = Q[j + 1][0] - Q[j][0], dy = Q[j + 1][1] - Q[j][1], dz = Q[j + 1][2] - Q[j][2]; s2 += Math.sqrt(dx * dx + dy * dy + dz * dz); }
      return s2;
    }
    var val = length(P), ex = gdExact(p), c0, c1;
    if (cas === 1) {
      var ll = function (q) { return [Math.atan2(q[1], q[0]) * 180.0 / PI, Math.asin(Math.max(-1.0, Math.min(1.0, q[2] / p.R))) * 180.0 / PI]; };
      c0 = start.map(ll); c1 = P.map(ll);
    } else { c0 = start.map(function (q) { return [q[0], q[1]]; }); c1 = P.map(function (q) { return [q[0], q[1]]; }); }
    return base(val, ex, n, c0.map(function (q) { return q[0]; }), c0.map(function (q) { return q[1]; }), [],
      c1.map(function (q) { return q[0]; }), c1.map(function (q) { return q[1]; }), { L0: length(start), sweeps: sweeps });
  });

  // ====================================================================================== constrained Lagrangian mechanics
  function agmK(k) {
    var a = 1.0, b = Math.sqrt(1.0 - k * k), i, t;
    for (i = 0; i < 40; i++) { t = 0.5 * (a + b); b = Math.sqrt(a * b); a = t; if (Math.abs(a - b) < 1e-16 * a) break; }
    return PI / (2.0 * a);
  }
  function csExact(p) {
    var cas = I(p.cas), g = p.g;
    if (cas === 1) { var m1 = p.m1, m2 = p.m2; return I(p.what) === 1 ? 2.0 * m1 * m2 * g / (m1 + m2) : (m1 - m2) * g / (m1 + m2); }
    if (cas === 2) { var w = p.w, c0 = g / (w * w * p.R); return 2 * PI / (w * Math.sqrt(1.0 - c0 * c0)); }
    var th0 = p.th0 * PI / 180.0;
    return 4.0 * Math.sqrt(p.L / g) * agmK(Math.sin(0.5 * th0));
  }
  function csRk4(f, y, h) {
    var n = y.length, i, t = [], k1 = f(y), k2, k3, k4;
    for (i = 0; i < n; i++) t.push(y[i] + 0.5 * h * k1[i]); k2 = f(t); t = [];
    for (i = 0; i < n; i++) t.push(y[i] + 0.5 * h * k2[i]); k3 = f(t); t = [];
    for (i = 0; i < n; i++) t.push(y[i] + h * k3[i]); k4 = f(t);
    var out = [];
    for (i = 0; i < n; i++) out.push(y[i] + h * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0);
    return out;
  }
  var CwConstr = kernel({ cas: 0.0, method: 0.0, what: 0.0, n: 32.0, g: 9.80665, L: 1.0, th0: 30.0, m1: 0.3, m2: 0.2, R: 0.2, w: 10.0, amp: 0.0001, periods: 3.0 }, function (p) {
    var cas = I(p.cas), what = I(p.what), n = Math.max(4, I(p.n)), g = p.g, ex = csExact(p), cx = [], cy = [], k, s, s2, h, val, cross = [], t = 0.0, nsteps;
    if (cas === 1) {
      var m1 = p.m1, m2 = p.m2, T1 = 1.0;
      h = T1 / n;
      var fA = function (q) { var lam = 2.0 * m1 * m2 * g / (m1 + m2); return [q[1], (m1 * g - lam) / m1]; };
      s = [0.0, 0.0];
      for (k = 0; k < n; k++) { s = csRk4(fA, s, h); cx.push((k + 1) * h); cy.push(s[0]); }
      var acc = 2.0 * s[0] / (T1 * T1);
      val = what === 1 ? m1 * (g - acc) : acc;
      return base(val, ex, n, cx, what === 0 ? cx.map(function (q) { return 0.5 * ex * q * q; }) : [], cy, [], []);
    }
    if (cas === 2) {
      var w = p.w, R = p.R, c0 = g / (w * w * R), th0 = Math.acos(c0), Tg = 2 * PI / (w * Math.sqrt(1.0 - c0 * c0));
      h = Tg / n;
      var fH = function (q) { return [q[1], Math.sin(q[0]) * (w * w * Math.cos(q[0]) - g / R)]; };
      s = [th0 + p.amp, 0.0];
      nsteps = I(p.periods * n) + 2;
      var prev = s[0] - th0;
      for (k = 0; k < nsteps; k++) {
        s2 = csRk4(fH, s, h);
        var d2 = s2[0] - th0;
        if ((prev > 0 && 0 >= d2) || (prev < 0 && 0 <= d2)) cross.push(t + h * prev / (prev - d2));
        s = s2; prev = d2; t = t + h;
        cx.push(t); cy.push(d2);
      }
      val = cross.length >= 2 ? 2.0 * (cross[cross.length - 1] - cross[0]) / (cross.length - 1) : 0.0;
      return base(val, ex, n, thin(cx, 120), [], thin(cy, 120), [], [], { th0: th0 });
    }
    var L = p.L, a0 = p.th0 * PI / 180.0;
    h = ex / n;
    var fP = function (q) {
      var x = q[0], y = q[1], vx = q[2], vy = q[3], r2 = x * x + y * y, lam = (vx * vx + vy * vy - g * y) / r2;
      return [vx, vy, -lam * x, -lam * y - g];
    };
    s = [L * Math.sin(a0), -L * Math.cos(a0), 0.0, 0.0];
    nsteps = I(p.periods * n) + 2;
    for (k = 0; k < nsteps; k++) {
      s2 = csRk4(fP, s, h);
      if ((s[0] > 0 && 0 >= s2[0]) || (s[0] < 0 && 0 <= s2[0])) {
        var lo = 0.0, hi = h, it;
        for (it = 0; it < 60; it++) {
          var mt = 0.5 * (lo + hi), u2 = mt / h;
          var h00 = 2 * Math.pow(u2, 3) - 3 * Math.pow(u2, 2) + 1, h10 = Math.pow(u2, 3) - 2 * Math.pow(u2, 2) + u2;
          var h01 = -2 * Math.pow(u2, 3) + 3 * Math.pow(u2, 2), h11 = Math.pow(u2, 3) - Math.pow(u2, 2);
          var xm = h00 * s[0] + h10 * h * s[2] + h01 * s2[0] + h11 * h * s2[2];
          if ((xm > 0) === (s[0] > 0)) lo = mt; else hi = mt;
        }
        cross.push(t + 0.5 * (lo + hi));
      }
      s = s2; t = t + h;
      cx.push(s[0]); cy.push(s[1]);
    }
    val = cross.length >= 2 ? 2.0 * (cross[cross.length - 1] - cross[0]) / (cross.length - 1) : 0.0;
    var drift = Math.abs(Math.sqrt(s[0] * s[0] + s[1] * s[1]) - L) / L;
    return base(val, ex, n, thin(cx, 120), [], thin(cy, 120), [], [], { drift: drift });
  });

  // ====================================================================================== calcs
  function best(r) {
    var rs = rowsOf(r, ['n', 'val', 'err']), i, b;
    if (!rs.length) return 0;
    b = rs[0];
    for (i = 0; i < rs.length; i++) if (rs[i][2] < b[2] || (rs[i][2] === b[2] && rs[i][0] > b[0])) b = rs[i];
    return b[1];
  }
  function order(r) {
    var rs = rowsOf(r, ['n', 'err']), pts = [], i, sx = 0, sy = 0, sxx = 0, sxy = 0, den;
    for (i = 0; i < rs.length; i++) if (rs[i][0] > 0 && rs[i][1] > 0) pts.push([Math.log(rs[i][0]), Math.log(rs[i][1])]);
    if (pts.length < 2) return 0;
    for (i = 0; i < pts.length; i++) { sx += pts[i][0]; sy += pts[i][1]; sxx += pts[i][0] * pts[i][0]; sxy += pts[i][0] * pts[i][1]; }
    den = pts.length * sxx - sx * sx;
    if (Math.abs(den) < 1e-30) return 0;
    return -(pts.length * sxy - sx * sy) / den;
  }

  root.HoolaKernels.register({
    K: { cw8_fact: CwFact, cw8_frame: CwFrame, cw8_vfield: CwVfield, cw8_group: CwGroup, cw8_gfx: CwGfx, cw8_anharm: CwAnharm,
      cw8_ljmd: CwLjmd, cw8_levels: CwLevels, cw8_maxwell: CwMaxwell, cw8_heatcap: CwHeatcap, cw8_qdist: CwQdist,
      cw8_fractal: CwFractal, cw8_flow: CwFlow, cw8_game: CwGame, cw8_conv: CwConv, cw8_lti: CwLti, cw8_fir: CwFir,
      cw8_geod: CwGeod, cw8_constr: CwConstr },
    TEXTBOOK: {
      cw8_fact_v: factExact, cw8_frame_v: frameExact, cw8_vfield_v: vfExact, cw8_group_v: gwExact, cw8_gfx_v: gfxExact,
      cw8_anharm_v: ahExact, cw8_ljmd_v: ljExact, cw8_levels_v: lvExact, cw8_maxwell_v: mxExact, cw8_heatcap_v: hcExact,
      cw8_qdist_v: qdExact, cw8_fractal_v: frExact, cw8_flow_v: flExact, cw8_game_v: gmExact, cw8_conv_v: cvExact,
      cw8_lti_v: ltiExact, cw8_fir_v: function (p) { return p.wc; }, cw8_geod_v: gdExact, cw8_constr_v: csExact
    },
    CALCS: {
      cw8_best: { label: 'best value', unit: '', needs: ['n', 'val', 'err'], fn: best },
      cw8_order: { label: 'order of the method', unit: '', needs: ['n', 'err'], fn: order }
    }
  });
})(typeof window !== 'undefined' ? window : this);
