/* v0.874 EK RANG (owner, 13 Nov 2026: "looks stale and AI made - do perfect logo work with a good background and the
   icon properly filled with perfect one colour"): the Hoola mark redrawn as ONE solid colour. No gradients, no gloss
   ridges, no core highlight, no blur. Same idea as her artwork (a core, a needle through it, two pairs of orbit arcs),
   now geometric: the core sits at the exact centre (50 / 50), the needle is a true 45 degree diagonal, every arc pair is
   the 180 degree turn of the other, and the arcs are full-bodied crescents instead of hairlines. viewBox 0..100.

   Colour: Hoola violet, the redesign's one accent (lib/ui/hoola_theme.dart accent #5B45E0, dark #9C88FF). In the
   console it follows the theme through --acc-rgb; the app icon draws it WHITE on a violet tile (tool/make_mark.js).

   HoolaMark.svg({mono, color, parts}) - the still mark. mono = currentColor; color = any CSS colour.
   HoolaMark.think(px)    - the THINKING mark: four layers at different depths on one tilting stage -
                            T3 the whole mark tilts in 3D, turns half way and rests; T1 the outer and inner arcs
                            orbit in opposite directions; T2 the arcs breathe outward one after the other while the
                            core floats in front and pulses. CSS in v2.css (.hm3); reduced motion = the still mark.
   HoolaMark.paths        - the raw shapes, read by tool/make_mark.js to build every logo size and the
                            Android notification silhouette, so no size can drift from this file. */
'use strict';
(() => {
const CX = 50, CY = 50;
const VIOLET = '#5B45E0';
// a full-bodied arc: widest in the middle, easing down to a rounded tip at both ends (a semicircle cap of the tip's
// width), so the ends are clean at a 16 px favicon and at a 1024 px splash alike
function crescent(r, a0, a1, maxw) {
  const n = 72, out = [], inn = [], tip = maxw * 0.34;
  const w = t => (tip + (maxw - tip) * Math.pow(Math.sin(Math.PI * t), 0.9)) / 2;
  for (let i = 0; i <= n; i++) {
    const t = i / n, a = (a0 + (a1 - a0) * t) * Math.PI / 180, h = w(t);
    out.push([CX + (r + h) * Math.cos(a), CY + (r + h) * Math.sin(a)]);
    inn.push([CX + (r - h) * Math.cos(a), CY + (r - h) * Math.sin(a)]);
  }
  const f = p => p[0].toFixed(2) + ' ' + p[1].toFixed(2), c = (tip / 2).toFixed(2), last = inn[n], first = out[0];
  return 'M' + out.map(f).join('L') + `A${c} ${c} 0 0 1 ${f(last)}` + 'L' + inn.reverse().map(f).join('L') + `A${c} ${c} 0 0 1 ${f(first)}Z`;
}
// radius, start angle, end angle, widest body. The needle runs along 45 / 225 degrees; every gap is centred on it,
// and the lower pair is the upper pair turned 180 degrees.
const ARCS = {
  uo: [35.5, -124, 34, 7.0],
  ui: [24.5, -114, 24, 5.6],
  lo: [35.5, 56, 214, 7.0],
  li: [24.5, 66, 204, 5.6],
};
const PATHS = Object.fromEntries(Object.entries(ARCS).map(([k, a]) => [k, crescent(a[0], a[1], a[2], a[3])]));
PATHS.needle = (() => {
  const p1 = [12.5, 12.5], p2 = [87.5, 87.5], h = 3 / Math.SQRT2;     // 3 wide each side at the core
  return `M${p1[0]} ${p1[1]}L${(CX + h).toFixed(2)} ${(CY - h).toFixed(2)}L${p2[0]} ${p2[1]}L${(CX - h).toFixed(2)} ${(CY + h).toFixed(2)}Z`;
})();
PATHS.core = {cx: CX, cy: CY, r: 12.6};
function svg(opts = {}) {
  const parts = opts.parts || 'oinc';
  const fill = opts.mono ? 'currentColor' : (opts.color || `rgb(var(--acc-rgb, 91 69 224))`);
  let g = '';
  if (parts.includes('o')) g += `<g class="hm-outer"><path d="${PATHS.uo}"/><path d="${PATHS.lo}"/></g>`;
  if (parts.includes('i')) g += `<g class="hm-inner"><path d="${PATHS.ui}"/><path d="${PATHS.li}"/></g>`;
  if (parts.includes('n')) g += `<path class="hm-needle" d="${PATHS.needle}"/>`;
  if (parts.includes('c')) g += `<g class="hm-core"><circle cx="${CX}" cy="${CY}" r="${PATHS.core.r}"/></g>`;
  return `<svg class="hm-svg" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><g fill="${fill}">${g}</g></svg>`;
}
function think(px = 20) {
  // every class carries the hm3- prefix: the console already owns .spin, .live, .turn... (a bare .spin drew a ring)
  const ly = (cls, parts) => `<span class="hm3-ly hm3-${cls}"><span class="hm3-spin"><span class="hm3-sig">${svg({parts})}</span></span></span>`;
  return `<span class="hm3" style="--s:${px}px" aria-hidden="true"><span class="hm3-floor"></span><span class="hm3-tilt"><span class="hm3-turn">` +
    ly('o', 'o') + ly('i', 'i') + ly('n', 'n') + ly('c', 'c') + `</span></span><span class="hm3-still">${svg()}</span></span>`;
}
window.HoolaMark = {svg, think, paths: PATHS, arcs: ARCS, violet: VIOLET};
})();
