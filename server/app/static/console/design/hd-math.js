/* HOOLA DESIGN - hd-math.js
 *
 * HD.math: 2x3 affine matrices and rectangle helpers. Pure functions, no state, no DOM.
 *
 * MATRIX  m = [a, b, c, d, e, f]  (the Canvas2D order, so ctx.setTransform.apply(ctx, m) works):
 *     x' = a*x + c*y + e          y' = b*x + d*y + f
 * mul(m, n) = m x n : n is applied FIRST, then m (world = mul(parentWorld, local)).
 * Angles: rotate() takes RADIANS like the canvas; rotateDeg() takes degrees. On a y-down
 * canvas a positive angle turns CLOCKWISE, which is how a node's `rot` is defined.
 * translate / rotate / scale each work two ways:
 *     translate(tx, ty)        -> a new matrix
 *     translate(m, tx, ty)     -> m x translate(tx, ty)   (like ctx.translate on m)
 * RECT    r = {x, y, w, h}. Functions never change their arguments.
 */
(function () {
  'use strict';
  var HD = window.HD = window.HD || {};
  var PI = Math.PI, D2R = PI / 180, R2D = 180 / PI;
  var isArr = Array.isArray;

  function identity() { return [1, 0, 0, 1, 0, 0]; }

  function mul(m, n) {
    return [
      m[0] * n[0] + m[2] * n[1],
      m[1] * n[0] + m[3] * n[1],
      m[0] * n[2] + m[2] * n[3],
      m[1] * n[2] + m[3] * n[3],
      m[0] * n[4] + m[2] * n[5] + m[4],
      m[1] * n[4] + m[3] * n[5] + m[5]
    ];
  }

  function inv(m) {
    var det = m[0] * m[3] - m[1] * m[2];
    if (!det || !isFinite(det)) return identity();
    var a = m[3] / det, b = -m[1] / det, c = -m[2] / det, d = m[0] / det;
    return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])];
  }

  function apply(m, x, y) {
    if (isArr(x)) { y = x[1]; x = x[0]; }
    return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  }

  /* exact sin / cos at the quarter turns, so a 90 degree node has no 6e-17 noise */
  function trig(rad) {
    var q = rad / (PI / 2), r = Math.round(q);
    if (Math.abs(q - r) < 1e-12) {
      r = ((r % 4) + 4) % 4;
      return r === 0 ? [1, 0] : r === 1 ? [0, 1] : r === 2 ? [-1, 0] : [0, -1];
    }
    return [Math.cos(rad), Math.sin(rad)];
  }

  function translate(m, tx, ty) {
    if (isArr(m)) return [m[0], m[1], m[2], m[3], m[0] * tx + m[2] * ty + m[4], m[1] * tx + m[3] * ty + m[5]];
    return [1, 0, 0, 1, m || 0, tx || 0];
  }

  function rotMat(rad, cx, cy) {
    var t = trig(rad), c = t[0], s = t[1];
    if (cx === undefined) return [c, s, -s, c, 0, 0];
    cy = cy || 0;
    return [c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy];
  }
  /* rotate(rad [,cx,cy]) -> matrix      rotate(m, rad [,cx,cy]) -> m x R */
  function rotate(m, rad, cx, cy) {
    if (isArr(m)) return mul(m, rotMat(rad || 0, cx, cy));
    return rotMat(m || 0, rad, cx);
  }
  function rotateDeg(m, deg, cx, cy) {
    if (isArr(m)) return mul(m, rotMat((deg || 0) * D2R, cx, cy));
    return rotMat((m || 0) * D2R, deg, cx);
  }

  /* scale(sx [,sy]) -> matrix           scale(m, sx [,sy]) -> m x S */
  function scale(m, sx, sy) {
    if (isArr(m)) {
      if (sy === undefined) sy = sx;
      return [m[0] * sx, m[1] * sx, m[2] * sy, m[3] * sy, m[4], m[5]];
    }
    if (sx === undefined) sx = m;
    return [m, 0, 0, sx, 0, 0];
  }

  /* The local matrix of a node: translate(x, y) x rotate about the box centre (degrees clockwise) x flips
     about the centre. (0,0)..(w,h) is the node's own box; the result maps it into the parent's space. */
  function nodeMatrix(x, y, w, h, rotDeg, flipH, flipV) {
    if (!rotDeg && !flipH && !flipV) return [1, 0, 0, 1, x, y];
    var t = trig((rotDeg || 0) * D2R), c = t[0], s = t[1];
    var fx = flipH ? -1 : 1, fy = flipV ? -1 : 1;
    var a = c * fx, b = s * fx, cc = -s * fy, d = c * fy;
    var cx = w / 2, cy = h / 2;
    return [a, b, cc, d, x + cx - (a * cx + cc * cy), y + cy - (b * cx + d * cy)];
  }

  /* {x, y, rot (degrees), sx, sy} of a matrix; a mirror shows as sx < 0 */
  function decompose(m) {
    var det = m[0] * m[3] - m[1] * m[2];
    var sx = Math.sqrt(m[0] * m[0] + m[1] * m[1]), sy = Math.sqrt(m[2] * m[2] + m[3] * m[3]);
    if (det < 0) sx = -sx;
    var rot = sx ? Math.atan2(m[1] / sx, m[0] / sx) * R2D : 0;
    return {x: m[4], y: m[5], rot: rot, sx: sx, sy: sy};
  }

  function eq(m, n, eps) {
    eps = eps === undefined ? 1e-9 : eps;
    for (var i = 0; i < 6; i++) if (Math.abs(m[i] - n[i]) > eps) return false;
    return true;
  }
  function isIdentity(m) { return m[0] === 1 && m[1] === 0 && m[2] === 0 && m[3] === 1 && m[4] === 0 && m[5] === 0; }

  /* ---------- numbers ---------- */
  function deg(rad) { return rad * R2D; }
  function rad(d) { return d * D2R; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function dist(x1, y1, x2, y2) {
    if (isArr(x1)) { y2 = y1[1]; x2 = y1[0]; y1 = x1[1]; x1 = x1[0]; }
    var dx = x2 - x1, dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
  }
  /* degrees into (-180, 180] */
  function normDeg(d) {
    d = d % 360;
    if (d > 180) d -= 360; else if (d <= -180) d += 360;
    return d === 0 ? 0 : d;
  }
  function round(v, places) {
    var k = Math.pow(10, places === undefined ? 6 : places), r = Math.round(v * k) / k;
    return r === 0 ? 0 : r;
  }

  /* ---------- rectangles ---------- */
  function rect(x, y, w, h) { return {x: x, y: y, w: w, h: h}; }

  function rectUnion(a, b) {
    if (!a) return b ? {x: b.x, y: b.y, w: b.w, h: b.h} : null;
    if (!b) return {x: a.x, y: a.y, w: a.w, h: a.h};
    var x = a.x < b.x ? a.x : b.x, y = a.y < b.y ? a.y : b.y;
    var r = a.x + a.w > b.x + b.w ? a.x + a.w : b.x + b.w, t = a.y + a.h > b.y + b.h ? a.y + a.h : b.y + b.h;
    return {x: x, y: y, w: r - x, h: t - y};
  }
  /* do the two rects touch or overlap (edges count, so a zero-height line can be hit) */
  function rectHit(a, b) {
    return a.x <= b.x + b.w && b.x <= a.x + a.w && a.y <= b.y + b.h && b.y <= a.y + a.h;
  }
  /* a fully contains b */
  function rectContains(a, b) {
    return b.x >= a.x && b.y >= a.y && b.x + b.w <= a.x + a.w && b.y + b.h <= a.y + a.h;
  }
  /* ptInRect(r, x, y) | ptInRect(x, y, r) | ptInRect(r, [x,y]) | ptInRect([x,y], r) */
  function ptInRect(a, b, c) {
    var r, x, y;
    if (typeof a === 'number') { x = a; y = b; r = c; }
    else if (isArr(a)) { x = a[0]; y = a[1]; r = b; }
    else if (isArr(b)) { r = a; x = b[0]; y = b[1]; }
    else { r = a; x = b; y = c; }
    return !!r && x >= r.x && y >= r.y && x <= r.x + r.w && y <= r.y + r.h;
  }
  function rectIntersect(a, b) {
    var x = a.x > b.x ? a.x : b.x, y = a.y > b.y ? a.y : b.y;
    var r = a.x + a.w < b.x + b.w ? a.x + a.w : b.x + b.w, t = a.y + a.h < b.y + b.h ? a.y + a.h : b.y + b.h;
    return r < x || t < y ? null : {x: x, y: y, w: r - x, h: t - y};
  }
  function rectExpand(r, dx, dy) {
    if (dy === undefined) dy = dx;
    return {x: r.x - dx, y: r.y - dy, w: r.w + 2 * dx, h: r.h + 2 * dy};
  }
  function rectCenter(r) { return [r.x + r.w / 2, r.y + r.h / 2]; }
  function rectFromPoints(pts) {
    if (!pts || !pts.length) return null;
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      if (p[0] < x0) x0 = p[0];
      if (p[0] > x1) x1 = p[0];
      if (p[1] < y0) y0 = p[1];
      if (p[1] > y1) y1 = p[1];
    }
    return {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
  }
  /* rect from two corner points in any order */
  function rectFromCorners(x1, y1, x2, y2) {
    return {x: x1 < x2 ? x1 : x2, y: y1 < y2 ? y1 : y2, w: Math.abs(x2 - x1), h: Math.abs(y2 - y1)};
  }
  function rectEq(a, b, eps) {
    eps = eps === undefined ? 1e-9 : eps;
    return !!a && !!b && Math.abs(a.x - b.x) <= eps && Math.abs(a.y - b.y) <= eps &&
      Math.abs(a.w - b.w) <= eps && Math.abs(a.h - b.h) <= eps;
  }

  /* the 4 corners [tl, tr, br, bl] of the box (0,0)..(w,h) under m */
  function corners(m, w, h) {
    return [
      [m[4], m[5]],
      [m[0] * w + m[4], m[1] * w + m[5]],
      [m[0] * w + m[2] * h + m[4], m[1] * w + m[3] * h + m[5]],
      [m[2] * h + m[4], m[3] * h + m[5]]
    ];
  }
  /* corners [tl, tr, br, bl] of a rect turned `rotDeg` clockwise about its own centre */
  function rectCorners(r, rotDeg) {
    return corners(nodeMatrix(r.x, r.y, r.w, r.h, rotDeg || 0, false, false), r.w, r.h);
  }
  /* axis-aligned bounds of the box (0,0)..(w,h) under m */
  function boundsOf(m, w, h) {
    if (m[1] === 0 && m[2] === 0 && m[0] === 1 && m[3] === 1) return {x: m[4], y: m[5], w: w, h: h};
    var ax = m[0] * w, ay = m[1] * w, bx = m[2] * h, by = m[3] * h;
    var x0 = Math.min(0, ax, bx, ax + bx), x1 = Math.max(0, ax, bx, ax + bx);
    var y0 = Math.min(0, ay, by, ay + by), y1 = Math.max(0, ay, by, ay + by);
    return {x: m[4] + x0, y: m[5] + y0, w: x1 - x0, h: y1 - y0};
  }
  /* axis-aligned bounds of a rect under m */
  function transformRect(m, r) {
    var b = boundsOf(m, r.w, r.h), ox = m[0] * r.x + m[2] * r.y, oy = m[1] * r.x + m[3] * r.y;
    b.x += ox; b.y += oy;
    return b;
  }
  /* is the world point inside the box (0,0)..(w,h) placed by m (exact for rotated boxes); pad grows the box */
  function ptInBox(m, w, h, x, y, pad) {
    var p = apply(inv(m), x, y);
    pad = pad || 0;
    return p[0] >= -pad && p[1] >= -pad && p[0] <= w + pad && p[1] <= h + pad;
  }

  HD.math = {
    identity: identity, mul: mul, inv: inv, apply: apply,
    translate: translate, rotate: rotate, rotateDeg: rotateDeg, scale: scale,
    nodeMatrix: nodeMatrix, decompose: decompose, eq: eq, isIdentity: isIdentity,
    deg: deg, rad: rad, clamp: clamp, lerp: lerp, dist: dist, normDeg: normDeg, round: round,
    rect: rect, rectUnion: rectUnion, rectHit: rectHit, rectContains: rectContains, ptInRect: ptInRect,
    rectIntersect: rectIntersect, rectExpand: rectExpand, rectCenter: rectCenter,
    rectFromPoints: rectFromPoints, rectFromCorners: rectFromCorners, rectEq: rectEq,
    corners: corners, rectCorners: rectCorners, boundsOf: boundsOf, transformRect: transformRect, ptInBox: ptInBox
  };
})();
