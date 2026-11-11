"""HOOLA DESIGN D8b: the starter plugins, shipped as DATA (docs/HOOLA_DESIGN_PLAN.md section 8, D8b).

Eight small, original plugins, each a {manifest, code} pair written against the D8a plugin API (the global `hoola`
inside the sandboxed plugin frame) with the SMALLEST permissions it needs. Nothing here runs on the server: the
editor's Plugins manager shows them with "Add", and adding one goes through D8a's own review dialog (she sees the
code and the permissions and approves them - that IS the install).

Every starter passes the same check a plugin Hoola writes must pass (plugin_ai.validate: manifest schema, the static
scan, the smallest permissions) - `listing()` refuses to serve one that does not, and the test suite runs each one's
code against a fake `hoola` in node (server/tests/web/design_plugins_ai_harness.js).

Shared shape of the code: PRELUDE (small helpers) then the body. D8a runs the whole source as the BODY of an async
function in a Web Worker (globals `hoola` and `command`; no DOM): `await` and `return` work at the top level, a panel
is drawn with hoola.ui.show(html) and answers through hoola.ui.on(msg => ...) ({action, values}), and every plugin
ends with hoola.close().
"""
from __future__ import annotations

import json

from . import ai, plugin_ai

# The editor's own font list (hd-ui.js FONTS == ai.FONTS), so "swap fonts" offers exactly what the editor can load.
_FONTS_JS = json.dumps(list(ai.FONTS))

PRELUDE = r"""
const ROOT = '0:0';
const idOf = x => typeof x === 'string' ? x : ((x && x.id) || '');
const node = async id => { const n = await hoola.get(id); return n ? Object.assign({}, n, {id: n.id || id}) : null; };
const pick = async () => { const s = await hoola.selection(), out = []; for (const x of (Array.isArray(s) ? s : [])) { const n = typeof x === 'string' ? await node(x) : x; if (n && n.id) out.push(n); } return out; };
const pageId = async () => idOf(await hoola.page());
/* every layer under the given ones (them included), depth first, at most `cap` */
async function walk(ids, cap) {
  const out = [], stack = ids.slice().reverse();
  while (stack.length && out.length < cap) {
    const x = stack.pop(), n = typeof x === 'string' ? await node(x) : x;
    if (!n || !n.id) continue;
    out.push(n);
    const k = await hoola.children(n.id);
    for (let i = (Array.isArray(k) ? k.length : 0) - 1; i >= 0; i--) stack.push(k[i]);
  }
  return out;
}
const esc = s => String(s === undefined || s === null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const finish = async msg => { if (msg) await hoola.notify(msg); await hoola.close(); };
"""

UI_PRELUDE = r"""
const panel = (html, opts) => hoola.ui.show(CSS + '<div class="p">' + html + '</div>', opts || {});
const CSS = '<style>' +
  'body{margin:0;font:13px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1d1b26;background:#fff}' +
  '.p{padding:16px;display:flex;flex-direction:column;gap:12px}h1{font-size:15px;margin:0;font-weight:600}' +
  'label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:#5b5868}' +
  'input,select,textarea{font:inherit;color:inherit;border:1px solid #d9d6e3;border-radius:8px;padding:8px 10px;background:#fff}' +
  'textarea{font:12px/1.5 ui-monospace,monospace;min-height:200px;resize:vertical}' +
  '.row{display:flex;gap:8px}.row label{flex:1;min-width:0}.check{flex-direction:row;align-items:center;gap:8px;color:#1d1b26}' +
  '.hint{margin:0;font-size:12px;color:#6b6780}.acts{display:flex;justify-content:flex-end;gap:8px}' +
  'button{font:inherit;border:1px solid #d9d6e3;background:#fff;border-radius:8px;padding:8px 14px;cursor:pointer}' +
  'button.pri{background:#5b3df5;border-color:#5b3df5;color:#fff;font-weight:600}' +
  '.list{display:flex;flex-direction:column;gap:6px;max-height:260px;overflow:auto}' +
  '.item{display:flex;align-items:center;gap:8px;padding:8px;border:1px solid #ece9f3;border-radius:8px}' +
  '.sw{width:16px;height:16px;border-radius:4px;border:1px solid rgba(0,0,0,.15);flex:none}.grow{flex:1;min-width:0}' +
  '.t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bad{color:#b42318;font-weight:600}' +
  '</style>';
"""


def _code(body: str, panel: bool = False) -> str:
    """The plugin's whole source: the helpers (+ the panel helpers when it shows one), then its body. D8a runs it as
    the body of an async function (so `await` and `return` work at the top level) in a Web Worker with `hoola` and
    `command`."""
    return PRELUDE.strip() + "\n" + (UI_PRELUDE.strip() + "\n" if panel else "") + "\n" + body.strip() + "\n"


# ----------------------------------------------------------------------------------------------- 1 rename layers
RENAME = _code(r"""
/* Rename the selected layers by a pattern: {n} = a number, {name} = the old name, {type} = the layer type.
   Layers are numbered in reading order (top to bottom, then left to right). */
function readingOrder(list) {
  const rows = [];
  for (const n of list.slice().sort((a, b) => (a.y || 0) - (b.y || 0))) {
    const row = rows.find(r => Math.abs(r.y - (n.y || 0)) <= Math.max(4, Math.min(r.h, n.h || 0) / 2));
    if (row) row.items.push(n); else rows.push({y: n.y || 0, h: n.h || 0, items: [n]});
  }
  return rows.reduce((out, r) => out.concat(r.items.sort((a, b) => (a.x || 0) - (b.x || 0))), []);
}
function pad(num, digits) { const s = String(Math.abs(num)); return (num < 0 ? '-' : '') + (s.length >= digits ? s : '0'.repeat(digits - s.length) + s); }
function nameFor(pattern, n, i, start, step, digits, many) {
  let p = String(pattern || '').trim() || '{name}';
  if (many && p.indexOf('{n}') < 0) p += ' {n}';
  const type = String(n.type || 'Layer').toLowerCase();
  return p.split('{n}').join(pad(start + i * step, digits)).split('{name}').join(n.name || '')
    .split('{type}').join(type.charAt(0).toUpperCase() + type.slice(1)).slice(0, 120);
}
const list = readingOrder(await pick());
if (!list.length) return finish('Select the layers to rename first.');
const v = {pat: 'Item {n}', start: '1', step: '1', digits: '1'};
const num = (x, d) => { const n = parseInt(x, 10); return isFinite(n) ? n : d; };
const names = () => list.map((n, i) => nameFor(v.pat, n, i, num(v.start, 1), num(v.step, 1), Math.max(1, Math.min(6, num(v.digits, 1))), list.length > 1));
const draw = () => { const all = names();
  return panel('<h1>Rename ' + list.length + (list.length === 1 ? ' layer' : ' layers') + '</h1>' +
    '<label>Pattern<input name="pat" data-action="preview" value="' + esc(v.pat) + '"></label><p class="hint">{n} number · {name} old name · {type} layer type</p>' +
    '<div class="row"><label>Start at<input name="start" type="number" data-action="preview" value="' + esc(v.start) + '"></label>' +
    '<label>Step<input name="step" type="number" data-action="preview" value="' + esc(v.step) + '"></label>' +
    '<label>Digits<input name="digits" type="number" min="1" max="6" data-action="preview" value="' + esc(v.digits) + '"></label></div>' +
    '<p class="hint" id="preview">Becomes: ' + esc(all.slice(0, 3).join(', ') + (all.length > 3 ? ', …' : '')) + '</p>' +
    '<div class="acts"><button data-action="cancel">Cancel</button><button class="pri" data-action="go">Rename</button></div>', {title: 'Rename layers', width: 340, height: 330}); };
hoola.ui.on(async msg => {
  try {
    Object.assign(v, (msg && msg.values) || {});
    if (msg.action === 'cancel') return finish('');
    if (msg.action === 'preview') return draw();
    if (msg.action !== 'go') return;
    const all = names();
    for (let i = 0; i < list.length; i++) if (all[i] !== list[i].name) await hoola.set(list[i].id, {name: all[i]});
    await finish('Renamed ' + list.length + (list.length === 1 ? ' layer.' : ' layers.'));
  } catch (e) { await finish('Rename stopped: ' + e.message); }
});
await draw();
""", panel=True)

# ----------------------------------------------------------------------------------------------- 2 tidy into a grid
TIDY = _code(r"""
/* Tidy the selected layers into a neat grid: reading order kept, about as many columns as rows, 24 px apart,
   starting where the selection starts. Only layers that share one parent move together. */
const GAP = 24;
const all = await pick();
if (all.length < 2) return finish('Select two or more layers to tidy.');
const home = all[0].parent, list = all.filter(n => n.parent === home), skipped = all.length - list.length;
const rows = [];
for (const n of list.slice().sort((a, b) => (a.y || 0) - (b.y || 0))) {
  const row = rows.find(r => Math.abs(r.y - (n.y || 0)) <= Math.max(4, Math.min(r.h, n.h || 0) / 2));
  if (row) row.items.push(n); else rows.push({y: n.y || 0, h: n.h || 0, items: [n]});
}
const order = rows.reduce((out, r) => out.concat(r.items.sort((a, b) => (a.x || 0) - (b.x || 0))), []);
const cols = Math.ceil(Math.sqrt(order.length)), lines = Math.ceil(order.length / cols);
const colW = new Array(cols).fill(0), rowH = new Array(lines).fill(0);
order.forEach((n, i) => { const c = i % cols, r = Math.floor(i / cols); colW[c] = Math.max(colW[c], n.w || 0); rowH[r] = Math.max(rowH[r], n.h || 0); });
const x0 = Math.min.apply(null, order.map(n => n.x || 0)), y0 = Math.min.apply(null, order.map(n => n.y || 0));
for (let i = 0; i < order.length; i++) {
  const c = i % cols, r = Math.floor(i / cols);
  let x = x0, y = y0;
  for (let k = 0; k < c; k++) x += colW[k] + GAP;
  for (let k = 0; k < r; k++) y += rowH[k] + GAP;
  x = Math.round(x); y = Math.round(y);
  if (x !== (order[i].x || 0) || y !== (order[i].y || 0)) await hoola.set(order[i].id, {x: x, y: y});
}
await finish('Tidied ' + order.length + ' layers into ' + cols + (cols === 1 ? ' column' : ' columns') +
  (skipped ? ' (' + skipped + ' in another frame were left alone)' : '') + '.');
""")

# ----------------------------------------------------------------------------------------------- 3 contrast checker
CONTRAST = _code(r"""
/* Every text below 4.5 : 1 against what is behind it (WCAG AA for body text). The background is the nearest layer
   ABOVE the text in the tree with a visible fill (a gradient counts its worst end), else the page colour. Shapes lying
   under a text without being its parent are not seen: check those by eye. Fix = the nearest darker or lighter shade
   of the text's own colour that reads. */
const NEED = 4.5;
function hexOk(c) { return typeof c === 'string' && /^#[0-9a-fA-F]{6}$/.test(c); }
function rgb(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
function hex(v) { return '#' + v.map(x => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0')).join('').toUpperCase(); }
function lum(c) { const v = rgb(c).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; }
function ratio(a, b) { const la = lum(a), lb = lum(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); }
function mix(a, b, t) { const x = rgb(a), y = rgb(b); return hex([0, 1, 2].map(i => x[i] + (y[i] - x[i]) * t)); }
function worst(c, bgs) { return Math.min.apply(null, bgs.map(b => ratio(c, b))); }
function paintCols(fills) {
  const list = Array.isArray(fills) ? fills : [];
  for (let i = list.length - 1; i >= 0; i--) {
    const p = list[i];
    if (!p || p.visible === false || (p.opacity !== undefined && p.opacity < 0.5)) continue;
    if (p.type === 'solid' && hexOk(p.color)) return [p.color.toUpperCase()];
    if (p.stops && p.stops.length) { const s = p.stops.filter(x => hexOk(x.color)); if (s.length) return [s[0].color.toUpperCase(), s[s.length - 1].color.toUpperCase()]; }
    if (p.type === 'image') return [];
  }
  return null;
}
function readable(fg, bgs) {
  if (worst(fg, bgs) >= NEED) return fg;
  const to = bgs.reduce((s, b) => s + lum(b), 0) / bgs.length < 0.18 ? '#FFFFFF' : '#000000';
  for (let k = 1; k <= 12; k++) { const c = mix(fg, to, k / 12); if (worst(c, bgs) >= NEED) return c; }
  return worst('#000000', bgs) >= worst('#FFFFFF', bgs) ? '#000000' : '#FFFFFF';
}
async function backgroundOf(n, cache) {
  let id = n.parent, guard = 0;
  while (id && guard++ < 200) {
    if (!cache.has(id)) cache.set(id, await node(id));
    const a = cache.get(id);
    if (!a) break;
    if (a.type === 'PAGE') return [hexOk(a.bg) ? a.bg.toUpperCase() : '#F5F5F5'];
    if (a.visible !== false && (a.opacity === undefined || a.opacity >= 0.5)) { const c = paintCols(a.fills); if (c) return c; }
    id = a.parent;
  }
  return ['#FFFFFF'];
}
const picked = await pick(), scope = picked.length ? picked : [await pageId()];
const texts = (await walk(scope, 6000)).filter(n => n.type === 'TEXT' && n.visible !== false), cache = new Map(), low = [];
for (const t of texts) {
  const own = paintCols(t.fills);
  if (!own || own.length !== 1) continue;
  const bgs = await backgroundOf(t, cache);
  if (!bgs.length) continue;
  const last = t.fills.filter(p => p && p.type === 'solid' && p.visible !== false).pop();
  const alpha = (last && last.opacity !== undefined ? last.opacity : 1) * (t.opacity === undefined ? 1 : t.opacity);
  const r = Math.min.apply(null, bgs.map(b => ratio(alpha >= 1 ? own[0] : mix(b, own[0], alpha), b)));
  if (r < NEED) low.push({id: t.id, name: t.name || 'Text', chars: String(t.chars || ''), fg: own[0], bg: bgs[0], ratio: r, fix: readable(own[0], bgs)});
}
const where = picked.length ? 'the selection' : 'this page';
async function fixAll() { for (const r of low) await hoola.set(r.id, {fills: [{type: 'solid', color: r.fix, opacity: 1, visible: true}]}); return low.length; }
if (command === 'fix') return finish(low.length ? 'Fixed ' + (await fixAll()) + ' texts so they read at 4.5 : 1.' : 'Every text in ' + where + ' already reads at 4.5 : 1.');
const rows = low.map(r => '<div class="item"><span class="sw" style="background:' + r.fg + '"></span><span class="sw" style="background:' + r.bg + '"></span>' +
  '<span class="grow t">' + esc(r.chars.slice(0, 60) || r.name) + '</span><span class="bad">' + r.ratio.toFixed(2) + '</span></div>').join('');
hoola.ui.on(async msg => {
  try {
    if (msg.action === 'close') return finish('');
    if (msg.action === 'fix') await finish('Fixed ' + (await fixAll()) + ' texts so they read at 4.5 : 1.');
  } catch (e) { await finish('Fix stopped: ' + e.message); }
});
await panel('<h1>Contrast check</h1><p class="hint" id="sum">' + (low.length ? low.length + ' of ' + texts.length + ' texts in ' + where + ' are below 4.5 : 1.' : 'All ' + texts.length + ' texts in ' + where + ' read at 4.5 : 1 or better.') + '</p>' +
  '<div class="list">' + rows + '</div><p class="hint">Only the layers a text sits inside count as its background.</p>' +
  '<div class="acts"><button data-action="close">Close</button>' + (low.length ? '<button class="pri" data-action="fix">Fix all</button>' : '') + '</div>',
  {title: 'Contrast check', width: 360, height: 420});
""", panel=True)

# ----------------------------------------------------------------------------------------------- 4 find and replace
REPLACE = _code(r"""
/* Find and replace words in every text on this page (or in the selection). A text with mixed styles is only
   changed when its length stays the same, so its styled ranges never shift onto the wrong letters. */
function pattern(find, caseOn, whole) {
  const safe = find.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(whole ? '(^|[^\\p{L}\\p{N}_])(' + safe + ')(?=$|[^\\p{L}\\p{N}_])' : '()(' + safe + ')', caseOn ? 'gu' : 'giu');
}
const picked = await pick();
const v = {find: '', to: '', caseOn: false, whole: false, insel: picked.length > 0};
async function plan() {
  if (!v.find) return {changes: [], skipped: 0, hits: 0};
  const rx = pattern(v.find, v.caseOn, v.whole), scope = v.insel && picked.length ? picked : [await pageId()];
  const changes = []; let skipped = 0, hits = 0;
  for (const t of (await walk(scope, 8000)).filter(n => n.type === 'TEXT')) {
    const chars = String(t.chars || ''); let n = 0;
    const out = chars.replace(rx, (m, lead) => { n++; return lead + v.to; });
    if (!n) continue;
    hits += n;
    if (Array.isArray(t.runs) && t.runs.length && out.length !== chars.length) { skipped++; continue; }
    changes.push({id: t.id, chars: out});
  }
  return {changes: changes, skipped: skipped, hits: hits};
}
const plural = (n, one, many) => n + ' ' + (n === 1 ? one : many);
const draw = async () => { const p = await plan();
  const count = !v.find ? 'Type what to find, then press Enter or Tab to count.' : plural(p.hits, 'match', 'matches') + ' in ' + plural(p.changes.length + p.skipped, 'text', 'texts') +
    (p.skipped ? ' (' + p.skipped + ' with mixed styles will be left alone)' : '') + '.';
  const box = (name, on, label) => '<label class="check"><input type="checkbox" name="' + name + '" data-action="preview"' + (on ? ' checked' : '') + '> ' + label + '</label>';
  return panel('<h1>Find and replace</h1><label>Find<input name="find" data-action="preview" placeholder="Words to find" value="' + esc(v.find) + '"></label>' +
    '<label>Replace with<input name="to" data-action="preview" placeholder="New words (empty = remove)" value="' + esc(v.to) + '"></label>' +
    box('caseOn', v.caseOn, 'Match capital letters') + box('whole', v.whole, 'Whole words only') + (picked.length ? box('insel', v.insel, 'Only in the selection') : '') +
    '<p class="hint" id="count">' + esc(count) + '</p><div class="acts"><button data-action="cancel">Cancel</button><button class="pri" data-action="go">Replace all</button></div>',
    {title: 'Find and replace', width: 340, height: 400}); };
hoola.ui.on(async msg => {
  try {
    const got = (msg && msg.values) || {};
    for (const k of ['find', 'to']) if (typeof got[k] === 'string') v[k] = got[k];
    for (const k of ['caseOn', 'whole', 'insel']) if (typeof got[k] === 'boolean') v[k] = got[k];
    if (msg.action === 'cancel') return finish('');
    if (msg.action === 'preview') return draw();
    if (msg.action !== 'go') return;
    if (!v.find) return draw();
    const p = await plan();
    for (const c of p.changes) await hoola.set(c.id, {chars: c.chars});
    await finish(p.changes.length ? 'Replaced in ' + plural(p.changes.length, 'text', 'texts') + (p.skipped ? '; ' + p.skipped + ' with mixed styles left alone' : '') + '.'
      : 'Nothing to replace' + (p.skipped ? ' (' + p.skipped + ' texts with mixed styles were left alone)' : '') + '.');
  } catch (e) { await finish('Replace stopped: ' + e.message); }
});
await draw();
""", panel=True)

# ----------------------------------------------------------------------------------------------- 5 palette -> fill styles
PALETTE = _code(r"""
/* The colours of the selection (fills and strokes of every layer inside it), near-duplicates merged, the most used
   first, become up to 8 fill styles named "Palette / #RRGGBB". A colour that already has a fill style is skipped. */
const MAX = 8, NEAR = 18;
function hexOk(c) { return typeof c === 'string' && /^#[0-9a-fA-F]{6}$/.test(c); }
function rgb(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
function dist(a, b) { const x = rgb(a), y = rgb(b); return Math.sqrt((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2 + (x[2] - y[2]) ** 2); }
function solidOf(value) { const p = Array.isArray(value) ? value.filter(v => v && v.type === 'solid' && hexOk(v.color)) : []; return p.length ? p[p.length - 1].color.toUpperCase() : ''; }
const picked = await pick();
if (!picked.length) return finish('Select the layers whose colours you want as styles.');
const counts = [];
for (const n of await walk(picked, 6000)) {
  if (n.visible === false) continue;
  for (const list of [n.fills, n.strokes]) for (const p of (Array.isArray(list) ? list : [])) {
    if (!p || p.visible === false || p.type !== 'solid' || !hexOk(p.color)) continue;
    const c = p.color.toUpperCase(), hit = counts.find(e => dist(e.color, c) <= NEAR);
    if (hit) hit.n++; else counts.push({color: c, n: 1});
  }
}
if (!counts.length) return finish('No solid colours in the selection.');
const root = await node(ROOT), styles = Object.assign({}, (root && root.styles) || {});
const have = Object.keys(styles).filter(k => styles[k] && styles[k].kind === 'fill').map(k => solidOf(styles[k].value)).filter(Boolean);
const fresh = counts.sort((a, b) => b.n - a.n).filter(e => !have.some(c => dist(c, e.color) <= NEAR)).slice(0, MAX);
if (!fresh.length) return finish('Every colour of the selection already has a fill style.');
const stamp = Date.now().toString(36);
fresh.forEach((e, i) => { styles['spal_' + stamp + '_' + i] = {kind: 'fill', name: 'Palette / ' + e.color, value: [{type: 'solid', color: e.color, opacity: 1, visible: true}]}; });
await hoola.set(ROOT, {styles: styles});
await finish('Added ' + fresh.length + (fresh.length === 1 ? ' colour style' : ' colour styles') + ' (Palette / …).');
""")

# ----------------------------------------------------------------------------------------------- 6 Indian numbers / rupees
RUPEE = _code(r"""
/* Indian digit grouping (1,00,000 and 1,25,50,000) in the selected texts.
   "Format as Indian numbers": amounts with a currency sign, numbers already written with commas, and plain numbers
   of 4 to 9 digits - except 4-digit years (1900-2099) and 6-digit numbers (they may be a PIN code).
   "Format as rupees": every amount gets the ₹ sign (Rs / INR become ₹) - for texts that are prices.
   Never touched: numbers of 10 or more digits (phone numbers), numbers that start with 0, numbers inside words. */
function indian(digits) {
  if (digits.length <= 3) return digits;
  let head = digits.slice(0, -3); const parts = [];
  while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
  if (head) parts.unshift(head);
  return parts.join(',') + ',' + digits.slice(-3);
}
function formatText(text, rupee) {
  const rx = /(?:(₹|\bRs\.?|\bINR)(\s?))?(\d{1,3}(?:,\d{2,3})+|\d+)(\.\d+)?(?![\d\p{L}])/gu;
  return String(text).replace(rx, (m, cur, sp, num, dec, at, all) => {
    const before = at > 0 ? all.charAt(at - 1) : '';
    if (before && /[\p{L}\p{N}_.\/#-]/u.test(before)) return m;
    const digits = num.replace(/,/g, ''), commas = num.indexOf(',') >= 0, year = digits.length === 4 && +digits >= 1900 && +digits <= 2099;
    if (digits.length >= 10 || (digits.length > 1 && digits.charAt(0) === '0')) return m;
    if (!cur && !commas && (rupee ? year : (digits.length < 4 || digits.length === 6 || year))) return m;
    const grouped = indian(digits) + (dec || '');
    return cur || rupee ? '₹' + grouped : grouped;
  });
}
const picked = await pick();
if (!picked.length) return finish('Select the texts (or the frames that hold them) to format.');
const rupee = command === 'rupee';
let changed = 0, skipped = 0;
for (const t of (await walk(picked, 6000)).filter(n => n.type === 'TEXT')) {
  const was = String(t.chars || ''), now = formatText(was, rupee);
  if (now === was) continue;
  if (Array.isArray(t.runs) && t.runs.length && now.length !== was.length) { skipped++; continue; }
  await hoola.set(t.id, {chars: now}); changed++;
}
await finish(changed ? 'Formatted ' + changed + (changed === 1 ? ' text' : ' texts') + (skipped ? '; ' + skipped + ' with mixed styles left alone' : '') + '.'
  : 'No numbers to format in the selection' + (skipped ? ' (' + skipped + ' texts with mixed styles were left alone)' : '') + '.');
""")

# ----------------------------------------------------------------------------------------------- 7 CSS variables
CSSVARS = _code(r"""
/* This file's styles and variables as CSS custom properties, ready to paste into a stylesheet. Read only. */
function slug(s) { return String(s || 'style').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'style'; }
function rgba(c, a) { const v = [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)); return a === undefined || a >= 1 ? c.toUpperCase() : 'rgba(' + v.join(', ') + ', ' + Math.round(a * 100) / 100 + ')'; }
function paintCss(list) {
  const p = (Array.isArray(list) ? list : []).filter(x => x && x.visible !== false).pop();
  if (!p) return '';
  if (p.type === 'solid' && p.color) return rgba(p.color, p.opacity);
  if (p.stops && p.stops.length) {
    const stops = p.stops.slice().sort((a, b) => a.pos - b.pos).map(s => rgba(s.color, s.opacity) + ' ' + Math.round(s.pos * 100) + '%').join(', ');
    if (p.type === 'radial') return 'radial-gradient(circle, ' + stops + ')';
    let deg = 180;
    if (p.from && p.to) deg = Math.round(Math.atan2(p.to[1] - p.from[1], p.to[0] - p.from[0]) * 180 / Math.PI + 90);
    return 'linear-gradient(' + deg + 'deg, ' + stops + ')';
  }
  return '';
}
function shadowCss(list) {
  return (Array.isArray(list) ? list : []).filter(e => e && e.visible !== false && (e.type === 'drop' || e.type === 'inner'))
    .map(e => (e.type === 'inner' ? 'inset ' : '') + (e.x || 0) + 'px ' + (e.y || 0) + 'px ' + (e.blur || 0) + 'px ' + (e.spread || 0) + 'px ' + rgba(e.color || '#000000', e.opacity === undefined ? 1 : e.opacity)).join(', ');
}
function cssOf(root) {
  const lines = [], used = new Set();
  const put = (name, value) => { if (value === '' || value === undefined || value === null) return; let n = name, k = 2; while (used.has(n)) n = name + '-' + k++; used.add(n); lines.push('  --' + n + ': ' + value + ';'); };
  const styles = (root && root.styles) || {}, sorted = Object.keys(styles).map(k => styles[k]).filter(Boolean).sort((a, b) => String(a.name) < String(b.name) ? -1 : 1);
  for (const s of sorted) {
    const base = slug(s.name);
    if (s.kind === 'fill') put('color-' + base, paintCss(s.value));
    else if (s.kind === 'effect') put('shadow-' + base, shadowCss(s.value));
    else if (s.kind === 'text' && s.value) {
      const v = s.value;
      if (v.font) put('font-' + base + '-family', "'" + String(v.font).replace(/'/g, '') + "'");
      if (v.fontSize) put('font-' + base + '-size', v.fontSize + 'px');
      if (v.fontWeight) put('font-' + base + '-weight', v.fontWeight);
      if (typeof v.lineHeight === 'number') put('font-' + base + '-line-height', v.lineHeight + 'px');
      if (v.letterSpacing) put('font-' + base + '-letter-spacing', v.letterSpacing + 'px');
    }
  }
  const vars = (root && root.vars) || {}, modes = (root && root.modes) || [];
  for (const k of Object.keys(vars)) {
    const v = vars[k]; if (!v || !v.modes) continue;
    const first = modes.length && v.modes[modes[0]] !== undefined ? v.modes[modes[0]] : v.modes[Object.keys(v.modes)[0]];
    if (v.type === 'color' && typeof first === 'string') put(slug(v.name), first.toUpperCase());
    else if (v.type === 'number' && typeof first === 'number') put(slug(v.name), first);
    else if (v.type === 'string' && typeof first === 'string') put(slug(v.name), JSON.stringify(first));
  }
  return lines.length ? ':root {\n' + lines.join('\n') + '\n}\n' : '';
}
const css = cssOf(await node(ROOT));
if (!css) return finish('This file has no colour, text or effect styles (or variables) yet.');
hoola.ui.on(async msg => { if (msg.action === 'close') await finish(''); });
await panel('<h1>CSS variables</h1><p class="hint">Click in the box, select all (Ctrl+A or ⌘A), copy, and paste into your stylesheet.</p>' +
  '<textarea name="out" readonly>' + esc(css) + '</textarea><div class="acts"><button class="pri" data-action="close">Done</button></div>',
  {title: 'CSS variables', width: 420, height: 420});
""", panel=True)

# ----------------------------------------------------------------------------------------------- 8 swap fonts
SWAPFONT = _code(r"""
/* Swap one font for another in every text of the selection (styled ranges too). Sizes and weights stay. */
const FONTS = __FONTS__;
const picked = await pick();
if (!picked.length) return finish('Select the texts (or the frames that hold them) first.');
const texts = (await walk(picked, 8000)).filter(n => n.type === 'TEXT'), used = {};
for (const t of texts) {
  const f = t.font || 'Inter'; used[f] = (used[f] || 0) + 1;
  for (const r of (Array.isArray(t.runs) ? t.runs : [])) if (r && r.font && r.font !== f) used[r.font] = (used[r.font] || 0) + 1;
}
const names = Object.keys(used).sort((a, b) => used[b] - used[a]);
if (!names.length) return finish('No text in the selection.');
const fromOpts = names.map(f => '<option value="' + esc(f) + '">' + esc(f) + ' (' + used[f] + ')</option>').join('');
const toOpts = FONTS.filter(f => f !== names[0]).map(f => '<option value="' + esc(f) + '">' + esc(f) + '</option>').join('');
hoola.ui.on(async msg => {
  try {
    if (msg.action === 'cancel') return finish('');
    if (msg.action !== 'go') return;
    const a = (msg.values || {}).from, b = (msg.values || {}).to;
    if (!a || !b || a === b) return hoola.notify('Pick two different fonts.');
    let n = 0;
    for (const t of texts) {
      const patch = {};
      if ((t.font || 'Inter') === a) patch.font = b;
      if (Array.isArray(t.runs) && t.runs.some(r => r && r.font === a)) patch.runs = t.runs.map(r => r && r.font === a ? Object.assign({}, r, {font: b}) : r);
      if (Object.keys(patch).length) { await hoola.set(t.id, patch); n++; }
    }
    await finish(n ? a + ' is now ' + b + ' in ' + n + (n === 1 ? ' text.' : ' texts.') : 'No text uses ' + a + '.');
  } catch (e) { await finish('Font swap stopped: ' + e.message); }
});
await panel('<h1>Swap fonts</h1><label>Replace<select name="from">' + fromOpts + '</select></label>' +
  '<label>With<select name="to">' + toOpts + '</select></label><p class="hint">' + texts.length + (texts.length === 1 ? ' text' : ' texts') +
  ' in the selection. Sizes and weights stay as they are.</p><div class="acts"><button data-action="cancel">Cancel</button><button class="pri" data-action="go">Swap</button></div>',
  {title: 'Swap fonts', width: 340, height: 300});
""", panel=True).replace("__FONTS__", _FONTS_JS)


def _m(pid: str, name: str, desc: str, perms: list[str], ui: bool, menu: list[tuple[str, str]]) -> dict:
    return {"id": "hoola." + pid, "name": name, "version": "1.0.0", "description": desc, "permissions": perms, "ui": ui,
            "menu": [{"label": label, "command": cmd} for label, cmd in menu]}


STARTERS: list[dict] = [
    {"manifest": _m("rename-layers", "Rename layers", "Rename the selected layers by a pattern with numbering: Card 01, Card 02 …",
                    ["read", "edit"], True, [("Rename selected layers…", "run")]), "code": RENAME, "icon": "text"},
    {"manifest": _m("tidy-grid", "Tidy into a grid", "Arrange the selected layers into an even grid, 24 px apart, in reading order.",
                    ["read", "edit"], False, [("Tidy into a grid", "run")]), "code": TIDY, "icon": "tidy"},
    {"manifest": _m("contrast-check", "Contrast checker", "List every text below 4.5 : 1 against its background, and fix them in one go.",
                    ["read", "edit"], True, [("Check contrast…", "check"), ("Fix all low contrast", "fix")]), "code": CONTRAST, "icon": "sun"},
    {"manifest": _m("find-replace", "Find and replace", "Find words in every text on the page (or the selection) and replace them.",
                    ["read", "edit"], True, [("Find and replace…", "run")]), "code": REPLACE, "icon": "search"},
    {"manifest": _m("palette-styles", "Palette to styles", "Turn the colours of the selection into up to 8 fill styles.",
                    ["read", "edit"], False, [("Make styles from the selection", "run")]), "code": PALETTE, "icon": "dropper"},
    {"manifest": _m("indian-numbers", "Indian numbers and ₹", "Group numbers the Indian way (1,00,000) and add the rupee sign to prices.",
                    ["read", "edit"], False, [("Format as Indian numbers", "indian"), ("Format as rupees (₹)", "rupee")]), "code": RUPEE, "icon": "check"},
    {"manifest": _m("css-variables", "Export CSS variables", "This file's colour, text and effect styles and variables as CSS custom properties.",
                    ["read"], True, [("Export CSS variables…", "run")]), "code": CSSVARS, "icon": "copy"},
    {"manifest": _m("swap-fonts", "Swap fonts", "Replace one font with another in every text of the selection.",
                    ["read", "edit"], True, [("Swap fonts…", "run")]), "code": SWAPFONT, "icon": "text"},
]


def checked() -> list[dict]:
    """Every starter through plugin_ai.validate (the very check a plugin Hoola writes must pass)."""
    out = []
    for s in STARTERS:
        v = plugin_ai.validate(s["manifest"], s["code"])
        out.append({"manifest": v["manifest"], "code": v["code"], "permissions": v["permissions"], "icon": s.get("icon", "")})
    return out


_CACHE: list[dict] | None = None


def listing() -> list[dict]:
    """GET /api/design/plugins/starters: each starter validated once per process (a starter that fails is never served)."""
    global _CACHE
    if _CACHE is None:
        good = []
        for s in STARTERS:
            try:
                v = plugin_ai.validate(s["manifest"], s["code"])
            except plugin_ai.PluginError:
                continue
            good.append({"manifest": v["manifest"], "code": v["code"], "permissions": v["permissions"], "icon": s.get("icon", ""),
                         "starter": True, "by": "Hoola"})
        _CACHE = good
    return _CACHE
