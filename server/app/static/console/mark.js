/* v0.887 ORBIT (owner, 13 Nov 2026: "SHOW THIS DESIGN IN MAN MADE PERFECT LOGO" -> "INCREASE THE CENTERLINE TILL END"
   -> option 2 "To the edge, bolder" on Espresso: "CHOOSE THIS"): the Hoola Orbit mark drawn on a construction grid.

   One centre (50 / 50). Two rings, each split by the 45 degree needle line into two halves; every cut is the SAME
   channel (CH wide, parallel to the needle), so no ring end is rounded off. Each half tapers by one rule: its inner
   edge is a circle shifted toward the opposite side, so a half is thickest where it faces away from the needle cut.
   The needle is a bold sharp diamond that runs to the corners of the app tile; the core sits on top at the centre.

   Coordinates are TILE coordinates: 0..100 is the whole app icon. The rings sit inside 12..88; the needle tips stop
   just inside the tile's own edge - for the rounded square (corner radius 22) at 8.94 on the diagonal, for a round
   launcher at 17.14. All shapes are plain SVG paths (arcs + lines), so tool/make_mark.js can hand the very same data
   to Android's status-bar vector.

   Colour: the app icon is the mark in WHITE on an Espresso tile (TILE #2A1C15, tool/make_mark.js). Inside the app the
   mark keeps Hoola violet (#5B45E0, the redesign's accent; the console follows --acc-rgb).

   HoolaMark.svg({mono, color, parts, shape, full}) - the still mark. mono = currentColor; color = any CSS colour;
                            shape 'circle' = the needle stops inside a round launcher; full = the whole tile box
                            (0..100) instead of the tight box around the mark.
   HoolaMark.think(px)    - the THINKING mark: four layers at different depths on one tilting stage (CSS in v2.css,
                            .hm3); reduced motion = the still mark.
   HoolaMark.paths        - the raw shapes, read by tool/make_mark.js to build every logo size and the
                            Android notification silhouette, so no size can drift from this file. */
'use strict';
(() => {
const CX = 50, CY = 50, R2 = Math.SQRT2;
const VIOLET = '#5B45E0';
const TILE = '#2A1C15';                 // Espresso: the app icon's background
const K = 0.76;                         // the mark's grid (0..100) placed inside the tile at 12..88
const CH = 5.2;                         // the needle channel through the rings, one width everywhere
const NEEDLE = 5.0;                     // the needle's width at the core; it tapers to a point at both tips
const CORE = 12.6 * K;
// [radius, ring width, taper shift] on the mark's grid
const RINGS = {o: [38, 7.2, 3.6], i: [25.5, 5.6, 2.6]};
const TIP = {square: (22 - 22 / R2) + 2.5, circle: (50 - 50 / R2) + 2.5};   // just inside the tile's edge
const BOX = '7 7 86 86';                // the tight box: needle tips included, symmetric about the centre

const f = n => n.toFixed(2);
// one half of a ring: outer circle (centre) minus the inner circle shifted away from this half, kept on one side of
// the needle channel. side +1 = the upper-right half, -1 = the lower-left half.
function half(R, w, sh, side) {
  R *= K; w *= K; sh *= K;
  const r = R - w, ix = CX - side * sh / R2, iy = CY + side * sh / R2;
  const k = side * CH / R2;                         // the channel edge: (x - 50) - (y - 50) = k
  const span = (rad, ox, oy) => Math.acos((k - (ox - CX) + (oy - CY)) / (rad * R2));
  const bo = span(R, CX, CY), bi = span(r, ix, iy);
  const at = (rad, ox, oy, th) => `${f(ox + rad * Math.cos(th))} ${f(oy + rad * Math.sin(th))}`;
  const q = -Math.PI / 4;
  // upper half runs from q - b to q + b; the lower half from q + b to q + 2 pi - b (always clockwise on screen)
  const [o1, o2] = side > 0 ? [q - bo, q + bo] : [q + bo, q + 2 * Math.PI - bo];
  const [i1, i2] = side > 0 ? [q - bi, q + bi] : [q + bi, q + 2 * Math.PI - bi];
  const big = (a, b) => (b - a > Math.PI ? 1 : 0);
  return `M${at(R, CX, CY, o1)}A${f(R)} ${f(R)} 0 ${big(o1, o2)} 1 ${at(R, CX, CY, o2)}` +
    `L${at(r, ix, iy, i2)}A${f(r)} ${f(r)} 0 ${big(i1, i2)} 0 ${at(r, ix, iy, i1)}Z`;
}
function needle(t) {
  const h = NEEDLE / 2 / R2;
  return `M${f(t)} ${f(t)}L${f(CX + h)} ${f(CY - h)}L${f(100 - t)} ${f(100 - t)}L${f(CX - h)} ${f(CY + h)}Z`;
}
const PATHS = {
  uo: half(...RINGS.o, 1), lo: half(...RINGS.o, -1),
  ui: half(...RINGS.i, 1), li: half(...RINGS.i, -1),
  needle: needle(TIP.square), needleRound: needle(TIP.circle),
  core: {cx: CX, cy: CY, r: +f(CORE)},
};
function svg(opts = {}) {
  const parts = opts.parts || 'oinc';
  const fill = opts.mono ? 'currentColor' : (opts.color || `rgb(var(--acc-rgb, 91 69 224))`);
  const nd = opts.shape === 'circle' ? PATHS.needleRound : PATHS.needle;
  let g = '';
  if (parts.includes('o')) g += `<g class="hm-outer"><path d="${PATHS.uo}"/><path d="${PATHS.lo}"/></g>`;
  if (parts.includes('i')) g += `<g class="hm-inner"><path d="${PATHS.ui}"/><path d="${PATHS.li}"/></g>`;
  if (parts.includes('n')) g += `<path class="hm-needle" d="${nd}"/>`;
  if (parts.includes('c')) g += `<g class="hm-core"><circle cx="${CX}" cy="${CY}" r="${PATHS.core.r}"/></g>`;
  const vb = opts.full ? '0 0 100 100' : BOX;
  return `<svg class="hm-svg" viewBox="${vb}" aria-hidden="true" focusable="false"><g fill="${fill}">${g}</g></svg>`;
}
function think(px = 20) {
  // every class carries the hm3- prefix: the console already owns .spin, .live, .turn... (a bare .spin drew a ring)
  const ly = (cls, parts) => `<span class="hm3-ly hm3-${cls}"><span class="hm3-spin"><span class="hm3-sig">${svg({parts})}</span></span></span>`;
  return `<span class="hm3" style="--s:${px}px" aria-hidden="true"><span class="hm3-floor"></span><span class="hm3-tilt"><span class="hm3-turn">` +
    ly('o', 'o') + ly('i', 'i') + ly('n', 'n') + ly('c', 'c') + `</span></span><span class="hm3-still">${svg()}</span></span>`;
}
window.HoolaMark = {svg, think, paths: PATHS, violet: VIOLET, tile: TILE, box: BOX};
})();
