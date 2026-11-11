/* Prayogshala kernel pack: SCHOOL OPTICS (NCERT Class 6-10 light) - the JavaScript twin of
   server/app/prayog/packs/optics_school.py, step for step. Four kernels: shadowbox (lamp, object, screen, the pipe
   test), pinhole (pinhole camera), planemirror (law of reflection, the virtual image, inclined mirrors) and slabray
   (a rectangular glass slab: Snell at both faces, the lateral displacement). SI, deterministic. */
(function (root) {
  'use strict';
  var H = root.HoolaKernels;
  if (!H) throw new Error('kernels.js must load before its packs');
  var R2D = 180 / Math.PI;

  function unit(v) { var L = Math.sqrt(v[0] * v[0] + v[1] * v[1]); return L > 0 ? [v[0] / L, v[1] / L] : [0, 0]; }
  function refract(d, nrm, n1, n2) {
    var cosi = -(d[0] * nrm[0] + d[1] * nrm[1]), r = n1 / n2, k = 1 - r * r * (1 - cosi * cosi), ct;
    if (k < 0) return null;
    ct = Math.sqrt(k);
    return [r * d[0] + (r * cosi - ct) * nrm[0], r * d[1] + (r * cosi - ct) * nrm[1]];
  }
  function meet(p1, d1, p2, d2) {
    var den = d1[0] * d2[1] - d1[1] * d2[0], t;
    if (Math.abs(den) < 1e-18) return null;
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den;
    return [p1[0] + t * d1[0], p1[1] + t * d1[1]];
  }
  function ang(d) { return Math.atan2(Math.abs(d[0]), Math.abs(d[1])); }
  function q6(x) { return Math.floor(x * 1e6 + 0.5); }

  // ------------------------------------------------------------------ shadows
  function edge(p, y0) {
    var d = unit([p.a - 0.0, p.h - y0]);
    return y0 + d[1] / d[0] * p.D;
  }
  function canSee(p) {
    var half = 2 * p.bore / Math.max(p.plen, 1e-9);
    return (Math.abs(p.bend) <= 2 * p.bore / Math.max(p.plen / 2, 1e-9) && Math.abs(p.tilt) <= half) ? 1 : 0;
  }
  var ShadowBox = {
    PARAMS: { h: 0.06, a: 0.30, D: 0.90, s: 0.004, bend: 0.0, tilt: 0.0, plen: 0.30, bore: 0.009 },
    VARS: ['rays', 'shadow', 'umbra', 'pen', 'mag', 'see'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var sharp = edge(p, 0.0), inner = edge(p, p.s / 2), outer = edge(p, -p.s / 2);
      var rays = [{ p: [[0.0, 0.0], [p.a, p.h], [p.D, sharp]], v: 0 }, { p: [[0.0, 0.0], [p.D, 0.0]], v: 0 }];
      return { rays: rays, shadow: sharp, umbra: inner, pen: outer - inner, mag: p.D / p.a, see: canSee(p) };
    },
    measure: function (p) { var v = ShadowBox.view(null, p); return { shadow: v.shadow, umbra: v.umbra, pen: v.pen, see: v.see }; }
  };

  // ------------------------------------------------------------------ pinhole camera
  function pinTop(p) {
    var o = [-p.u, p.h], d = unit([0.0 - o[0], 0.0 - o[1]]);
    return [p.v, d[1] / d[0] * p.v];
  }
  var Pinhole = {
    PARAMS: { h: 0.09, u: 0.60, v: 0.15, dp: 0.0015 },
    VARS: ['rays', 'img_h', 'img_y', 'blur', 'mag', 'crisp'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var top = pinTop(p), blur = p.dp * (p.u + p.v) / p.u, img = Math.abs(top[1]);
      var rays = [{ p: [[-p.u, p.h], [0.0, 0.0], top], v: 0 }, { p: [[-p.u, 0.0], [0.0, 0.0], [p.v, 0.0]], v: 0 }];
      return { rays: rays, img_h: img, img_y: top[1], blur: blur, mag: p.v / p.u, crisp: img + blur > 0 ? img / (img + blur) : 0 };
    },
    measure: function (p) { var v = Pinhole.view(null, p); return { img_h: v.img_h, blur: v.blur, mag: v.mag }; }
  };

  // ------------------------------------------------------------------ plane mirrors
  function reflect(d, nrm) { var dot = d[0] * nrm[0] + d[1] * nrm[1]; return [d[0] - 2 * dot * nrm[0], d[1] - 2 * dot * nrm[1]]; }
  function pmRay(p, L) {
    L = L === undefined ? 0.14 : L;
    var d = unit([Math.sin(p.i), -Math.cos(p.i)]), rd = reflect(d, [0.0, 1.0]);
    return { legs: [[-L * d[0], -L * d[1]], [0.0, 0.0], [L * rd[0], L * rd[1]]], rd: rd };
  }
  function pmImage(p) {
    var o = [0.0, p.d], out = [], i, sx, hit, d, xs = [-p.sep, p.sep];
    for (i = 0; i < 2; i++) {
      sx = xs[i]; hit = [sx, 0.0]; d = unit([hit[0] - o[0], hit[1] - o[1]]);
      out.push([hit, reflect(d, [0.0, 1.0])]);
    }
    return meet(out[0][0], out[0][1], out[1][0], out[1][1]);
  }
  function pmImages(p) {
    var th = p.theta, c2 = Math.cos(2 * th), s2 = Math.sin(2 * th);
    var start = [p.d * Math.cos(th / 2), p.d * Math.sin(th / 2)];
    var pts = [start], seen = {}, i = 0, j, q, nx, k, cand;
    seen[q6(start[0]) + ',' + q6(start[1])] = 1;
    while (i < pts.length && pts.length < 200) {
      q = pts[i]; i++;
      cand = [[q[0], -q[1]], [c2 * q[0] + s2 * q[1], s2 * q[0] - c2 * q[1]]];
      for (j = 0; j < 2; j++) {
        nx = cand[j]; k = q6(nx[0]) + ',' + q6(nx[1]);
        if (!seen[k]) { seen[k] = 1; pts.push(nx); }
      }
    }
    return pts.length - 1;
  }
  var PlaneMirror = {
    PARAMS: { i: 0.5236, d: 0.09, theta: 1.0472, sep: 0.02 },
    VARS: ['rays', 'r', 'img_y', 'img', 'N'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var one = pmRay(p), img = pmImage(p) || [0.0, 0.0];
      var rays = [{ p: one.legs, v: 0 }, { p: [[0.0, 0.0], [0.0, 0.06]], v: 1 }, { p: [[0.0, p.d], [img[0], img[1]]], v: 1 }];
      return { rays: rays, r: ang(one.rd), img_y: img[1], img: Math.abs(img[1]), N: pmImages(p) };
    },
    measure: function (p) { var v = PlaneMirror.view(null, p); return { r: v.r, img: v.img, N: v.N }; }
  };

  // ------------------------------------------------------------------ rectangular glass slab
  function slabTrace(p) {
    var d0 = unit([Math.sin(p.i), -Math.cos(p.i)]), d1 = refract(d0, [0.0, 1.0], 1.0, p.n), hit, d2;
    if (!d1 || d1[1] >= 0) return null;
    hit = [d1[0] / -d1[1] * p.t, -p.t];
    d2 = refract(d1, [0.0, -1.0], p.n, 1.0);
    if (!d2) return null;
    return { d0: d0, d1: d1, hit: hit, d2: d2 };
  }
  var SlabRay = {
    PARAMS: { t: 0.05, n: 1.5168, i: 0.5236, w: 0.09 },
    VARS: ['rays', 'r', 'e', 'shift', 'tir'],
    init: function () { return { t: 0 }; },
    step: function (s, p, dt) { s.t += dt; },
    view: function (s, p) {
      var tr = slabTrace(p), L = 0.07, rays, shift;
      if (!tr) return { rays: [], r: 0, e: 0, shift: 0, tir: 1 };
      rays = [{ p: [[-L * tr.d0[0], -L * tr.d0[1]], [0.0, 0.0], tr.hit, [tr.hit[0] + L * tr.d2[0], tr.hit[1] + L * tr.d2[1]]], v: 0 },
        { p: [[0.0, 0.0], [L * tr.d0[0], L * tr.d0[1]]], v: 1 }];
      shift = Math.abs(tr.d0[0] * tr.hit[1] - tr.d0[1] * tr.hit[0]);
      return { rays: rays, r: ang(tr.d1), e: ang(tr.d2), shift: shift, tir: 0 };
    },
    measure: function (p) { var v = SlabRay.view(null, p); return { r: v.r, e: v.e, shift: v.shift }; }
  };

  // ------------------------------------------------------------------ results from the learner's table
  function rows(rs, keys) {
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
  function mapMean(rs, keys, fn, keep) { return mean(rows(rs, keys).filter(keep || function () { return true; }).map(fn)); }

  H.register({
    K: { shadowbox: ShadowBox, pinhole: Pinhole, planemirror: PlaneMirror, slabray: SlabRay },
    TEXTBOOK: {
      shadow_h: function (p) { return p.h * p.D / p.a; },
      shadow_pen: function (p) { return p.s * (p.D - p.a) / p.a; },
      pinhole_h: function (p) { return p.h * p.v / p.u; },
      planemirror_r: function (p) { return p.i; },
      planemirror_img: function (p) { return p.d; },
      incl_N: function (p) { return 360.0 / (p.theta * R2D) - 1.0; },
      slabray_r: function (p) { return Math.asin(Math.sin(p.i) / p.n); },
      slabray_shift: function (p) { var r = Math.asin(Math.sin(p.i) / p.n); return p.t * Math.sin(p.i - r) / Math.cos(r); }
    },
    CALCS: {
      shadow_h0: { label: 'height of the object', unit: 'm', needs: ['a', 'D', 'sh'],
        fn: function (r) { return mapMean(r, ['a', 'D', 'sh'], function (x) { return x[2] * x[0] / x[1]; }, function (x) { return x[1] > 0; }); } },
      pinhole_h0: { label: 'height of the object', unit: 'm', needs: ['u', 'v', 'hi'],
        fn: function (r) { return mapMean(r, ['u', 'v', 'hi'], function (x) { return x[2] * x[0] / x[1]; }, function (x) { return x[1] > 0; }); } },
      mirror_law_r: { label: 'r / i', unit: '', needs: ['ai', 'ar'],
        fn: function (r) { return mapMean(r, ['ai', 'ar'], function (x) { return x[1] / x[0]; }, function (x) { return x[0] > 0; }); } },
      incl_360: { label: 'theta x (N + 1)', unit: '°', needs: ['th', 'nim'],
        fn: function (r) { return mapMean(r, ['th', 'nim'], function (x) { return x[0] * (x[1] + 1); }); } },
      slabray_n: { label: 'n', unit: '', needs: ['ai', 'ar'],
        fn: function (r) { return mapMean(r, ['ai', 'ar'], function (x) { return Math.sin(x[0]) / Math.sin(x[1]); }, function (x) { return Math.sin(x[1]) > 0; }); } }
    }
  });
})(typeof window !== 'undefined' ? window : this);
