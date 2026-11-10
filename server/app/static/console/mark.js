/* v0.716 NAYA ROOP: the Hoola mark (the owner's logo, 9 Nov 2026) drawn as vector so it is sharp from a 16px tab to
   a splash, and each part can move on its own. viewBox 0..100, the core at 49.4 / 50.2 (measured on her artwork).

   HoolaMark.svg({mono})  - the still mark; glossy (core highlight, a light ridge on every arc) unless mono.
   HoolaMark.think(px)    - the THINKING mark: four layers at different depths on one tilting stage -
                            T3 the whole mark tilts in 3D, turns half way and rests; T1 the outer and inner arcs
                            orbit in opposite directions; T2 the arcs breathe outward one after the other while the
                            core floats in front and pulses. CSS in v2.css (.hm3); reduced motion = the still mark.
   HoolaMark.paths        - the raw shapes, read by tool/make_mark.js to build every logo size and the
                            Android notification silhouette, so no size can drift from this file. */
'use strict';
(() => {
const CX = 49.4, CY = 50.2;
function crescent(r, a0, a1, maxw) {
  const n = 40, out = [], inn = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, a = (a0 + (a1 - a0) * t) * Math.PI / 180;
    const w = maxw * Math.pow(Math.sin(Math.PI * t), 0.85) / 2;
    out.push([CX + (r + w) * Math.cos(a), CY + (r + w) * Math.sin(a)]);
    inn.push([CX + (r - w) * Math.cos(a), CY + (r - w) * Math.sin(a)]);
  }
  return 'M' + out.concat(inn.reverse()).map(p => p[0].toFixed(2) + ' ' + p[1].toFixed(2)).join('L') + 'Z';
}
const at = (r, a) => [CX + r * Math.cos(a * Math.PI / 180), CY + r * Math.sin(a * Math.PI / 180)];
// radius, start angle, end angle, widest stroke, gradient from -> to
const ARCS = {
  uo: [35.5, -125, 36, 4.4, '#00F0FF', '#0038D6'],
  ui: [25.5, -116, 25, 3.1, '#0A86F5', '#0730E0'],
  lo: [36, 55, 212, 3.8, '#5B10D2', '#B428F7'],
  li: [25.5, 67, 202, 3.2, '#4A00C4', '#6A10D8'],
};
const PATHS = Object.fromEntries(Object.entries(ARCS).map(([k, a]) => [k, crescent(a[0], a[1], a[2], a[3])]));
PATHS.needle = (() => {
  const p1 = [11.6, 14.8], p2 = [88.7, 87.5], dx = p2[0] - p1[0], dy = p2[1] - p1[1], L = Math.hypot(dx, dy);
  const nx = -dy / L * 1.9, ny = dx / L * 1.9;
  return `M${p1[0]} ${p1[1]}L${(CX + nx).toFixed(2)} ${(CY + ny).toFixed(2)}L${p2[0]} ${p2[1]}L${(CX - nx).toFixed(2)} ${(CY - ny).toFixed(2)}Z`;
})();
PATHS.core = {cx: CX, cy: CY, r: 11.2};
let MID = 0;
function svg(opts = {}) {
  const mono = !!opts.mono, parts = opts.parts || 'oinc', id = 'hm' + (++MID);
  const fill = k => mono ? 'currentColor' : `url(#${id}${k})`;
  let defs = '';
  if (!mono) {
    for (const [k, a] of Object.entries(ARCS)) {
      const s = at(a[0], a[1]), e = at(a[0], a[2]);
      defs += `<linearGradient id="${id}${k}" gradientUnits="userSpaceOnUse" x1="${s[0]}" y1="${s[1]}" x2="${e[0]}" y2="${e[1]}"><stop offset="0" stop-color="${a[4]}"/><stop offset="1" stop-color="${a[5]}"/></linearGradient>`;
    }
    defs += `<linearGradient id="${id}n" gradientUnits="userSpaceOnUse" x1="11.6" y1="14.8" x2="88.7" y2="87.5"><stop offset="0" stop-color="#0A46E8"/><stop offset=".42" stop-color="#00F2FF"/><stop offset=".58" stop-color="#00F2FF"/><stop offset="1" stop-color="#0A46E8"/></linearGradient>`;
    defs += `<radialGradient id="${id}c" cx="36%" cy="30%" r="78%"><stop offset="0" stop-color="#7DF6FF"/><stop offset=".28" stop-color="#16D2FF"/><stop offset=".72" stop-color="#0A6CF2"/><stop offset="1" stop-color="#0634B8"/></radialGradient>`;
    defs += `<radialGradient id="${id}r" cx="50%" cy="50%" r="50%"><stop offset=".7" stop-color="#001060" stop-opacity="0"/><stop offset="1" stop-color="#001060" stop-opacity=".35"/></radialGradient>`;
    defs += `<filter id="${id}b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation=".9"/></filter>`;
  }
  const shine = k => {
    if (mono) return '';
    const a = ARCS[k];
    return `<path d="${crescent(a[0] + a[3] * .16, a[1] + 10, a[2] - 10, a[3] * .34)}" fill="#FFFFFF" opacity=".38"/>`;
  };
  let g = '';
  if (parts.includes('o')) g += `<g class="hm-outer"><path d="${PATHS.uo}" fill="${fill('uo')}"/>${shine('uo')}<path d="${PATHS.lo}" fill="${fill('lo')}"/>${shine('lo')}</g>`;
  if (parts.includes('i')) g += `<g class="hm-inner"><path d="${PATHS.ui}" fill="${fill('ui')}"/>${shine('ui')}<path d="${PATHS.li}" fill="${fill('li')}"/>${shine('li')}</g>`;
  if (parts.includes('n')) g += `<path class="hm-needle" d="${PATHS.needle}" fill="${fill('n')}"/>` +
    (mono ? '' : `<path d="M14 17 L${CX} ${CY} L86 85" stroke="#FFFFFF" stroke-width=".45" stroke-linecap="round" opacity=".55" fill="none"/>`);
  if (parts.includes('c')) g += `<g class="hm-core"><circle cx="${CX}" cy="${CY}" r="11.2" fill="${fill('c')}"/>` +
    (mono ? '' : `<circle cx="${CX}" cy="${CY}" r="11.2" fill="url(#${id}r)"/><ellipse cx="${CX - 3.6}" cy="${CY - 4.6}" rx="4.6" ry="3" fill="#FFFFFF" opacity=".75" filter="url(#${id}b)" transform="rotate(-30 ${CX - 3.6} ${CY - 4.6})"/><circle cx="${CX - 4.6}" cy="${CY - 5.4}" r="1.1" fill="#FFFFFF" opacity=".9"/>`) + '</g>';
  return `<svg class="hm-svg" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${defs ? '<defs>' + defs + '</defs>' : ''}${g}</svg>`;
}
function think(px = 20) {
  // every class carries the hm3- prefix: the console already owns .spin, .live, .turn... (a bare .spin drew a ring)
  const ly = (cls, parts) => `<span class="hm3-ly hm3-${cls}"><span class="hm3-spin"><span class="hm3-sig">${svg({parts})}</span></span></span>`;
  return `<span class="hm3" style="--s:${px}px" aria-hidden="true"><span class="hm3-floor"></span><span class="hm3-tilt"><span class="hm3-turn">` +
    ly('o', 'o') + ly('i', 'i') + ly('n', 'n') + ly('c', 'c') + `</span></span><span class="hm3-still">${svg()}</span></span>`;
}
window.HoolaMark = {svg, think, paths: PATHS, arcs: ARCS};
})();
