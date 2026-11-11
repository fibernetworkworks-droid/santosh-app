/* HOOLA DESIGN - browser walk of phase D3 "systems" (hd-components.js): components, instances + overrides, variants,
   component properties, styles, variables + modes, the Assets panel and the library, against the REAL editor with the
   mock server of design_ui_test.js (REST + a one-file WebSocket room).
   Run:  node server/tests/web/design_components_test.js      (DESIGN_SHOTS=<dir> also writes screenshots;
         DESIGN_ALL=1 loads the other second-wave feature files too, by default they are left out so this walk
         only depends on the first wave + hd-components.js)
   It works with the mouse and the keyboard where a person would, asserts on HD.store and on canvas PIXELS, and ends
   with two editors on one file that must show the same document. */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const {startMock, newDoc, layoutProblems} = require('./design_ui_test.js');

const solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}];
function seed() {
  const doc = newDoc();
  Object.assign(doc.nodes, {
    '9:1': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Button', x: 40, y: 40, w: 160, h: 48, radius: 10, fills: solid('#6E55F0')},
    '9:2': {type: 'TEXT', parent: '9:1', idx: 'a0', name: 'Label', x: 20, y: 14, w: 70, h: 20, chars: 'Buy now', fontSize: 16, fontWeight: 600, fills: solid('#FFFFFF'), autoResize: 'none'},
    '9:3': {type: 'ELLIPSE', parent: '9:1', idx: 'a1', name: 'Dot', x: 132, y: 18, w: 12, h: 12, fills: solid('#EE8F35')},
    '9:5': {type: 'RECT', parent: '0:1', idx: 'a1', name: 'Card', x: 40, y: 320, w: 120, h: 80, radius: 8, fills: solid('#D9D9D9')},
    '9:6': {type: 'RECT', parent: '0:1', idx: 'a2', name: 'Card 2', x: 200, y: 320, w: 120, h: 80, radius: 8, fills: solid('#C0C0C0')},
    '9:7': {type: 'FRAME', parent: '0:1', idx: 'a3', name: 'Panel', x: 40, y: 440, w: 280, h: 120, fills: solid('#FFFFFF')},
    '9:8': {type: 'RECT', parent: '9:7', idx: 'a0', name: 'Swatch', x: 20, y: 20, w: 80, h: 80, fills: solid('#111111')}
  });
  return doc;
}
function libDoc(color) {
  const doc = newDoc();
  Object.assign(doc.nodes, {
    '7:1': {type: 'COMPONENT', parent: '0:1', idx: 'a0', name: 'Badge', x: 0, y: 0, w: 90, h: 30, radius: 15, fills: solid(color)},
    '7:2': {type: 'TEXT', parent: '7:1', idx: 'a0', name: 'Badge text', x: 14, y: 6, w: 60, h: 18, chars: 'New', fontSize: 14, fills: solid('#FFFFFF'), autoResize: 'none'},
    '7:3': {type: 'COMPONENT', parent: '0:1', idx: 'a1', name: 'Chip', x: 0, y: 80, w: 140, h: 40, fills: solid('#FFFFFF')},
    '7:4': {type: 'INSTANCE', parent: '7:3', idx: 'a0', name: 'Badge', comp: '7:1', x: 8, y: 5, w: 90, h: 30, ov: {'7:2': {chars: 'Hot'}}}
  });
  return doc;
}

async function walk() {
  const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  const mock = await startMock(seed());
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { await mock.close(); console.log('no browser here: ' + String(e.message || e).split('\n')[0]); process.exit(77); }
  const errors = [];
  async function newPage(viewport, scheme) {
    const page = await browser.newPage({viewport: viewport || {width: 1440, height: 900}, colorScheme: scheme || 'light'});
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
    if (!process.env.DESIGN_ALL) await page.route(/hd-(vector|export|collab|proto|ai)\.js/, r => r.fulfill({contentType: 'application/javascript', body: ''}));
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(() => localStorage.setItem('hoola.console.token', 'fixture-only'));
    return page;
  }
  const base = 'http://127.0.0.1:' + mock.port + '/console/design';
  const mounted = page => page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0 && HD.comp, null, {timeout: 20000});
  const settle = page => page.evaluate(() => new Promise(done => { let last = '', same = 0, n = 0; const tick = () => { const v = window.HD && HD.render && HD.render.view ? [HD.render.view.x, HD.render.view.y, HD.render.view.zoom].join() : ''; same = v === last ? same + 1 : 0; last = v; if (same >= 3 || ++n > 90) setTimeout(done, 40); else requestAnimationFrame(tick); }; requestAnimationFrame(tick); }));
  const shot = async (page, name) => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };
  /* the picture of one node as a string (size + a hash of every pixel) */
  const pix = (page, id) => page.evaluate(i => { const cv = HD.render.toCanvas(i, 2, {bg: '#FFFFFF'}), d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let x = 0x811c9dc5; for (let k = 0; k < d.length; k++) { x ^= d[k]; x = Math.imul(x, 0x01000193); } return cv.width + 'x' + cv.height + ':' + (x >>> 0); }, id);
  /* the colour in the middle of a node as it is drawn */
  const mid = (page, id) => page.evaluate(i => { const cv = HD.render.toCanvas(i, 1, {bg: '#FFFFFF'}), d = cv.getContext('2d').getImageData(cv.width >> 1, cv.height >> 1, 1, 1).data; return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase(); }, id);
  try {
    const page = await newPage();
    await page.goto(base + '#/f/f1'); await mounted(page); await settle(page);
    const ev = (fn, arg) => page.evaluate(fn, arg);
    const pt = (wx, wy) => page.evaluate(([x, y]) => { const s = HD.render.worldToScreen(x, y), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; }, [wx, wy]);
    const node = id => ev(i => { const n = HD.store.get(i); return n ? JSON.parse(JSON.stringify(n)) : null; }, id);
    const clickW = async (wx, wy, o) => { const p = await pt(wx, wy); await page.mouse.click(p[0], p[1], o); await settle(page); };
    const dblW = async (wx, wy) => { const p = await pt(wx, wy); await page.mouse.dblclick(p[0], p[1]); await settle(page); };
    const idle = () => page.waitForFunction(() => HD.net.pending() === 0, null, {timeout: 15000});

    /* ---- create a component with the keyboard; alt-drag makes an instance without child nodes ---- */
    await page.locator('.hd-canvas').focus(); await clickW(50, 44);
    assert.deepEqual(await ev(() => HD.sel.ids.slice()), ['9:1'], 'the button frame is selected');
    await page.keyboard.press('Control+Alt+k'); await settle(page);
    assert.equal((await node('9:1')).type, 'COMPONENT', 'Ctrl+Alt+K turned the frame into a component');
    assert.equal(await page.locator('.hd-right section[aria-label="Component"]').count(), 1, 'the Component section shows');
    const a0 = await pt(100, 80), a1 = await pt(360, 80);
    await page.keyboard.down('Alt'); await page.mouse.move(a0[0], a0[1]); await page.mouse.down(); await page.mouse.move(a0[0] + 40, a0[1], {steps: 3}); await page.mouse.move(a1[0], a1[1], {steps: 6}); await page.mouse.up(); await page.keyboard.up('Alt'); await settle(page);
    const i1 = await ev(() => HD.sel.ids[0]); let n1 = await node(i1);
    assert.equal(n1.type, 'INSTANCE'); assert.equal(n1.comp, '9:1'); assert.equal(await ev(i => HD.store.children(i).length, i1), 0, 'an instance has no child nodes');
    assert.ok(Math.abs(n1.x - 300) < 2 && n1.w === 160 && n1.h === 48, 'the instance sits where it was dropped, at the component size: ' + JSON.stringify(n1));
    assert.equal((await node('9:1')).x, 40, 'the main component did not move');
    assert.equal(await pix(page, i1), await pix(page, '9:1'), 'the instance is drawn pixel for pixel like its component');
    /* copy + paste of the main component makes an instance too; a second one comes from the API */
    await clickW(50, 44); await ev(() => HD.tools.act.copy()); const pasted = await ev(() => HD.tools.act.paste([700, 64]));
    assert.equal((await node(pasted[0])).type, 'INSTANCE', 'pasting a main component pastes an instance'); await ev(i => { HD.sel.set([i]); HD.tools.act.remove(); }, pasted[0]);
    const i2 = await ev(() => HD.comp.insertAt('9:1', 600, 64)); await settle(page);
    assert.equal(await pix(page, i2), await pix(page, '9:1'));
    assert.equal(await ev(i => HD.store.prop(i, 'fills')[0].color, i2), '#6E55F0', 'the Design panel reads the component look for an instance'); assert.equal((await node(i2)).fills, undefined);

    /* ---- deep select: double-click inside the instance, then edit text and fill = overrides in `ov` ---- */
    await clickW(310, 50); assert.deepEqual(await ev(() => HD.sel.ids.slice()), [i1]);
    assert.equal(await page.locator('.hd-right section[aria-label="Instance"]').count(), 1); assert.match(await page.locator('.hdc-main-t').first().textContent(), /Button/);
    await shot(page, 'instance-panel');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with an instance selected');
    await dblW(340, 62);
    assert.deepEqual(await ev(() => [HD.comp.sub.inst, HD.comp.sub.path]), [i1, '9:2'], 'double-click selects the text layer inside the instance');
    assert.equal(await page.locator('.hdc-sub').count(), 1); assert.equal(await page.locator('.hdc-sub .hd-selname').textContent(), 'Label');
    const before = await ev(() => HD.store.canUndo() && HD.store.undoLabel());
    await page.locator('.hdc-sub textarea').fill('Pay later'); await page.locator('.hdc-sub textarea').blur(); await settle(page);
    n1 = await node(i1); assert.deepEqual(n1.ov, {'9:2': {chars: 'Pay later'}}, 'the text edit is an override on the instance');
    assert.equal((await node('9:2')).chars, 'Buy now', 'the main component keeps its text'); void before;
    assert.ok(await page.locator('.hdc-sub section[aria-label="Text"] .hdc-dot').count(), 'the overridden section is marked');
    await shot(page, 'sub-selected');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with a layer selected inside an instance');
    /* the dot: click it (same depth), give it another fill through the hex box */
    await clickW(438, 64); assert.equal(await ev(() => HD.comp.sub.path), '9:3', 'a click inside moves the deep selection');
    const hex = page.locator('.hdc-sub section[aria-label="Fill"] .hd-hex'); await hex.click(); await hex.fill('00AA55'); await hex.press('Enter'); await settle(page);
    n1 = await node(i1); assert.equal(n1.ov['9:3'].fills[0].color, '#00AA55'); assert.equal(n1.ov['9:2'].chars, 'Pay later');
    assert.equal((await node('9:3')).fills[0].color, '#EE8F35', 'the component keeps its fill');
    assert.notEqual(await pix(page, i1), await pix(page, '9:1'), 'only this instance looks different');
    assert.equal(await pix(page, i2), await pix(page, '9:1'), 'the other instance did not change');
    await page.keyboard.press('Escape'); await settle(page); assert.equal(await ev(() => HD.comp.sub.inst), null, 'Escape leaves the instance');
    assert.equal(await page.locator('.hdc-chip').count(), 2, 'both changes are listed on the instance');

    /* ---- edit the main: instances follow, the overridden property stays ---- */
    await ev(() => HD.store.tx('edit main', () => { HD.store.set('9:2', {chars: 'Add to cart', fontSize: 18}); HD.store.set('9:3', {fills: [{type: 'solid', color: '#FF0000', opacity: 1, visible: true}]}); HD.store.set('9:1', {fills: [{type: 'solid', color: '#1A1A1F', opacity: 1, visible: true}]}); })); await settle(page);
    assert.equal(await pix(page, i2), await pix(page, '9:1'), 'an untouched instance follows the main component');
    const t1 = await ev(i => { const t = HD.comp.vtree(i); return {chars: t.kids[0].n.chars, size: t.kids[0].n.fontSize, dot: t.kids[1].n.fills[0].color, bg: t.n.fills[0].color}; }, i1);
    assert.deepEqual(t1, {chars: 'Pay later', size: 18, dot: '#00AA55', bg: '#1A1A1F'}, 'overridden text and fill stay, everything else follows');

    /* ---- reset one override with its chip, then all ---- */
    await page.locator('.hdc-chip[data-prop="fills"]').click(); await settle(page);
    n1 = await node(i1); assert.deepEqual(n1.ov, {'9:2': {chars: 'Pay later'}}, 'the fill override is gone');
    await page.locator('.hdc-resetall').click(); await settle(page);
    n1 = await node(i1); assert.equal(n1.ov, undefined, 'Reset all changes'); assert.equal(await pix(page, i1), await pix(page, '9:1'));
    await page.keyboard.press('Control+z'); await settle(page); assert.deepEqual((await node(i1)).ov, {'9:2': {chars: 'Pay later'}}, 'one undo brings the override back');

    /* ---- component property: a text property on the main shows as a field on the instance ---- */
    const pid = await ev(() => HD.comp.addProp('9:1', 'text', '9:2', 'Label')); assert.ok(pid); await settle(page);
    await clickW(610, 50); assert.deepEqual(await ev(() => HD.sel.ids.slice()), [i2]);
    const field = page.locator('.hd-right .hdc-prow[data-cprop="' + pid + '"] input'); assert.equal(await field.inputValue(), 'Add to cart');
    await field.fill('Subscribe'); await field.press('Enter'); await settle(page);
    assert.deepEqual((await node(i2)).ov, {'9:2': {chars: 'Subscribe'}}, 'the property field writes the override');
    const bid = await ev(() => HD.comp.addProp('9:1', 'bool', '9:3', 'Show dot')); await settle(page);
    await page.locator('.hd-right .hdc-prow[data-cprop="' + bid + '"] .hdc-switch').click(); await settle(page);
    assert.equal((await node(i2)).ov['9:3'].visible, false, 'a show / hide property hides the layer in this instance');

    /* ---- detach: real layers with the overrides applied, fresh ids ---- */
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+Alt+b'); await settle(page);
    const d2 = await node(i2); assert.equal(d2.type, 'FRAME'); assert.equal(d2.comp, undefined); assert.equal(d2.ov, undefined);
    const kids2 = await ev(i => HD.store.children(i).map(k => Object.assign({id: k}, JSON.parse(JSON.stringify(HD.store.get(k))))), i2);
    assert.equal(kids2.length, 2); assert.ok(kids2.every(k => k.id !== '9:2' && k.id !== '9:3'), 'fresh ids');
    assert.equal(kids2[0].chars, 'Subscribe'); assert.equal(kids2[1].visible, false); assert.equal(d2.fills[0].color, '#1A1A1F', 'the look of the component is now its own');
    await page.keyboard.press('Control+z'); await settle(page); assert.equal((await node(i2)).type, 'INSTANCE', 'one undo makes it an instance again'); assert.equal(await ev(i => HD.store.children(i).length, i2), 0);

    /* ---- variants: combine two components, swap with the dropdown, a boolean value is a switch ---- */
    const made = await ev(() => { const S = HD.store, ids = []; S.tx('two more', () => {
      for (const [name, color, y] of [['Tag/Plain', '#2255CC', 620], ['Tag/Loud', '#CC2255', 680]]) { const c = S.create('COMPONENT', HD.sel.page, {name: name, x: 40, y: y, w: 120, h: 40, fills: [{type: 'solid', color: color, opacity: 1, visible: true}]});
        S.create('TEXT', c, {name: 'Caption', x: 10, y: 10, w: 80, h: 20, chars: name, fills: [{type: 'solid', color: '#FFFFFF', opacity: 1, visible: true}], autoResize: 'none'}); ids.push(c); } });
      HD.sel.set(ids); return ids; }); await settle(page);
    await page.locator('.hd-right section[aria-label="Variants"] .hd-btn', {hasText: 'Combine as variants'}).click(); await settle(page);
    const setId = await ev(() => HD.sel.ids[0]); assert.equal((await node(setId)).type, 'COMPONENT_SET'); assert.equal((await node(setId)).name, 'Tag');
    assert.deepEqual(await ev(s => HD.store.children(s).map(k => HD.store.get(k).name), setId), ['Property 1=Plain', 'Property 1=Loud']);
    assert.equal((await node(made[0])).parent, setId); assert.ok(Math.abs((await ev(i => HD.store.worldBounds(i), made[0])).y - 620) < 0.01, 'a variant stays where it was on the canvas');
    await shot(page, 'variant-set');
    const iv = await ev(c => HD.comp.insertAt(c, 420, 640), made[0]); await settle(page);
    await ev(([i, p]) => HD.comp.setOverride(i, p, {chars: 'Mine'}), [iv, await ev(c => HD.store.children(c)[0], made[0])]); await settle(page);
    const vsel = page.locator('.hd-right .hdc-prow[data-prop="Property 1"] select'); assert.equal(await vsel.inputValue(), 'Plain');
    await vsel.selectOption('Loud'); await settle(page);
    let nv = await node(iv); assert.equal(nv.comp, made[1], 'the dropdown swapped the instance to the other variant');
    assert.deepEqual(Object.values(nv.ov), [{chars: 'Mine'}], 'the text override moved to the layer with the same name'); assert.equal(Object.keys(nv.ov)[0], await ev(c => HD.store.children(c)[0], made[1]));
    /* a second property with true / false values shows as a switch */
    await ev(([a, b]) => HD.store.tx('bool', () => { HD.store.set(a, {name: 'Property 1=Plain, Dimmed=false'}); HD.store.set(b, {name: 'Property 1=Plain, Dimmed=true'}); }), made); await settle(page);
    const sw = page.locator('.hd-right .hdc-prow[data-prop="Dimmed"] .hdc-switch'); assert.equal(await sw.getAttribute('aria-checked'), 'true');
    await sw.click(); await settle(page); assert.equal((await node(iv)).comp, made[0], 'the switch picks the variant with Dimmed=false');
    await ev(s => HD.comp.renameVariantProp(s, 'Dimmed', 'Muted'), setId); assert.equal((await node(made[1])).name, 'Property 1=Plain, Muted=true', 'renaming a property renames it in every variant');
    await ev(s => HD.comp.addVariantProp(s, 'Size', 'M'), setId); assert.equal((await node(made[0])).name, 'Property 1=Plain, Muted=false, Size=M');

    /* ---- styles: create from a layer, apply, edit = every user changes in ONE undo step ---- */
    await ev(() => HD.sel.set(['9:5'])); await settle(page);
    await page.locator('.hd-right section[aria-label="Fill"] .hdc-stylebtn').click(); await page.locator('.hdc-stylepop button[aria-label="New style from this layer"]').click();
    await page.locator('.hdc-styleedit input').first().waitFor(); await page.locator('.hdc-styleedit input').first().fill('Brand grey'); await page.locator('.hdc-styleedit input').first().press('Enter'); await settle(page);
    const sid = await ev(() => HD.comp.styles('fill')[0].id); assert.equal((await node('9:5')).fillStyle, sid); assert.equal(await ev(() => HD.comp.styles('fill')[0].name), 'Brand grey');
    await shot(page, 'style-editor'); await page.keyboard.press('Escape');
    await ev(s => HD.comp.applyStyle(s, ['9:6']), sid); assert.equal((await node('9:6')).fills[0].color, '#D9D9D9'); assert.equal((await node('9:6')).fillStyle, sid);
    await ev(s => HD.comp.updateStyle(s, {value: [{type: 'solid', color: '#0077FF', opacity: 1, visible: true}]}), sid); await settle(page);
    assert.equal((await node('9:5')).fills[0].color, '#0077FF'); assert.equal((await node('9:6')).fills[0].color, '#0077FF'); assert.equal(await mid(page, '9:6'), '#0077FF', 'the linked layers are drawn with the new style');
    assert.equal(await page.locator('.hd-right section[aria-label="Fill"] .hdc-stylename').textContent(), 'Brand grey', 'the Fill section names the style');
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+z'); await settle(page);
    assert.equal((await node('9:5')).fills[0].color, '#D9D9D9'); assert.equal((await node('9:6')).fills[0].color, '#D9D9D9'); assert.equal(await ev(s => HD.store.get('0:0').styles[s].value[0].color, sid), '#D9D9D9', 'one undo took the style and both layers back');
    await page.keyboard.press('Control+Shift+z'); await settle(page); assert.equal((await node('9:6')).fills[0].color, '#0077FF');
    /* changing a linked fill by hand lets go of the style, in the same step */
    await ev(() => HD.store.tx('by hand', () => HD.store.set('9:6', {fills: [{type: 'solid', color: '#123456', opacity: 1, visible: true}]}))); await settle(page);
    assert.equal((await node('9:6')).fillStyle, undefined, 'a hand-made fill is not linked any more'); assert.equal(await mid(page, '9:6'), '#123456');
    await ev(() => HD.sel.clear()); await settle(page); assert.equal(await page.locator('.hd-right .hdc-srow').count(), 1, 'the style is listed when nothing is selected');
    await shot(page, 'empty-styles'); assert.deepEqual(await ev(layoutProblems), [], 'layout of the empty panel with styles');

    /* ---- variables + modes: bind, a frame switches the mode, a new value reaches every bound layer ---- */
    const vid = await ev(() => { const C = HD.comp, v = C.addVar('color', 'colour/surface'); C.setVarValue(v, C.modes()[0], '#FFCC00'); C.renameMode(C.modes()[0], 'Light'); C.addMode('Dark'); C.setVarValue(v, 'Dark', '#221133'); C.bind(['9:8'], 'fill', v); return v; }); await settle(page);
    assert.deepEqual((await node('9:8')).bind, {'$fill': vid}); assert.equal((await node('9:8')).fills[0].color, '#FFCC00', 'binding writes the resolved value');
    assert.equal(await mid(page, '9:8'), '#FFCC00');
    await ev(() => HD.sel.set(['9:7'])); await settle(page);
    const msel = page.locator('.hd-right .hdc-prow[data-bind="mode"] select'); await msel.selectOption('Dark'); await settle(page);
    assert.equal((await node('9:7')).mode, 'Dark'); assert.equal((await node('9:8')).fills[0].color, '#221133', 'the frame mode changed the bound value below it'); assert.equal(await mid(page, '9:8'), '#221133', 'and that is what is drawn');
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+z'); await settle(page); assert.equal((await node('9:8')).fills[0].color, '#FFCC00', 'one undo: mode and value together'); assert.equal((await node('9:7')).mode, undefined);
    await page.keyboard.press('Control+Shift+z'); await settle(page);
    await ev(v => HD.comp.setVarValue(v, 'Dark', '#330055'), vid); await settle(page); assert.equal((await node('9:8')).fills[0].color, '#330055', 'a new value for the mode reaches the bound layer');
    await ev(v => HD.comp.setVarValue(v, 'Light', '#FFFFFF'), vid); assert.equal((await node('9:8')).fills[0].color, '#330055', 'the other mode does not touch it');
    /* the dialog: a table with a column per mode */
    await ev(() => HD.comp.openVariables()); await page.locator('.hdc-vars .hdc-vname input').first().waitFor();
    assert.deepEqual(await page.locator('.hdc-vars .hdc-vmode input').evaluateAll(els => els.map(e => e.value)), ['Light', 'Dark']); assert.equal(await page.locator('.hdc-vars .hdc-vgroup').textContent(), 'colour');
    const cell = page.locator('.hdc-vars .hdc-vcell[data-mode="Dark"] .hd-hex'); await cell.fill('445566'); await cell.press('Enter'); await settle(page);
    assert.equal((await node('9:8')).fills[0].color, '#445566', 'typing a value in the table changes the bound layer');
    await page.locator('.hdc-vars .hd-btn', {hasText: 'Variable'}).click(); await page.locator('.hd-mi', {hasText: 'Number'}).click(); await settle(page);
    assert.equal(await ev(() => HD.comp.vars('number').length), 1); await shot(page, 'variables'); await page.locator('.hdc-vars button[aria-label="Close"]').click();
    /* a bound value changed by hand lets go of the variable */
    await ev(() => HD.store.tx('by hand', () => HD.store.set('9:8', {fills: [{type: 'solid', color: '#ABCDEF', opacity: 1, visible: true}]}))); assert.equal((await node('9:8')).bind, undefined, 'a hand-made fill is not bound any more');
    await page.keyboard.press('Control+z'); await settle(page); assert.deepEqual((await node('9:8')).bind, {'$fill': vid});

    /* ---- the Assets panel: previews, search, drag onto the canvas ---- */
    await page.locator('.hd-left .hd-tab', {hasText: 'Assets'}).click(); await page.locator('.hdc-card').first().waitFor();
    assert.deepEqual(await page.locator('.hdc-cardname').allTextContents(), ['Button', 'Tag']); assert.ok(await page.locator('.hdc-card canvas').first().evaluate(c => c.width > 4 && c.height > 4), 'a live preview');
    assert.match(await page.locator('.hdc-cardsub').textContent(), /2 variants/);
    await page.locator('.hdc-assets input[type="search"]').fill('but'); await page.waitForFunction(() => document.querySelectorAll('.hdc-card').length === 1);
    const before2 = await ev(() => HD.comp.instancesOf('9:1').length), cb = await page.locator('.hdc-card').first().boundingBox(), drop = await ev(() => { const r = HD.tools.canvas.getBoundingClientRect(); return [Math.round(r.left + r.width * 0.7), Math.round(r.top + r.height * 0.3)]; }), dw = await ev(([x, y]) => { const r = HD.tools.canvas.getBoundingClientRect(); return HD.render.screenToWorld(x - r.left, y - r.top); }, drop);
    await page.mouse.move(cb.x + cb.width / 2, cb.y + 30); await page.mouse.down(); await page.mouse.move(cb.x + cb.width / 2 + 30, cb.y + 50, {steps: 3}); await page.mouse.move(drop[0], drop[1], {steps: 8}); await page.mouse.up(); await settle(page);
    assert.equal(await ev(() => HD.comp.instancesOf('9:1').length), before2 + 1, 'dragging a card onto the canvas places an instance');
    const i3 = await ev(() => HD.sel.ids[0]), n3 = await node(i3); assert.equal(n3.type, 'INSTANCE'); assert.ok(Math.abs(n3.x + n3.w / 2 - dw[0]) < 2 && Math.abs(n3.y + n3.h / 2 - dw[1]) < 2, 'centred on the drop point');
    await page.locator('.hdc-assets input[type="search"]').fill(''); await shot(page, 'assets');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with the Assets panel');

    /* ---- the library: a component of another file is copied in, and brought up to date later ---- */
    const lib = await ev(async () => (await HD.ui.api('POST', '/files', {name: 'Brand kit'})).id); mock.files.get(lib).doc = libDoc('#008866');
    await page.locator('.hdc-lib .hd-btn', {hasText: 'Browse your files'}).click(); await page.locator('.hdc-libfile', {hasText: 'Brand kit'}).click(); await page.locator('.hdc-librow').first().waitFor();
    assert.deepEqual(await page.locator('.hdc-librow .hd-lname').allTextContents(), ['Badge', 'Chip']);
    await page.locator('.hdc-librow[data-src="7:3"] .hd-btn').click(); await settle(page);
    const chip = await ev(() => HD.sel.ids[0]), nc = await node(chip); assert.equal(nc.type, 'COMPONENT'); assert.equal(nc.name, 'Chip'); assert.deepEqual([nc.libSrc.file, nc.libSrc.id], [lib, '7:3']);
    const got = await ev(c => { const S = HD.store, k = S.children(c)[0], n = S.get(k), b = n.comp, bn = S.get(b); return {inst: n.type, badge: bn && bn.type, badgeSrc: bn && bn.libSrc && bn.libSrc.id, text: S.children(b)[0], ov: n.ov, color: bn.fills[0].color}; }, chip);
    assert.equal(got.inst, 'INSTANCE'); assert.equal(got.badge, 'COMPONENT'); assert.equal(got.badgeSrc, '7:1', 'the component its nested instance needs came along');
    assert.deepEqual(got.ov, {[got.text]: {chars: 'Hot'}}, 'overrides inside the copy point at the copied layers'); assert.equal(got.color, '#008866');
    assert.equal(await ev(() => HD.comp.listComponents().length), 4);
    mock.files.get(lib).doc = libDoc('#AA0044');                                          /* the library file changes */
    const upd = await ev(() => HD.comp.checkLibrary().then(m => Array.from(m.values()))); assert.deepEqual(upd, ['changed'], 'only the changed component is reported');
    const badgeLocal = await ev(c => HD.store.get(HD.store.children(c)[0]).comp, chip);
    assert.equal(await ev(b => HD.comp.updateFromLibrary([b]), badgeLocal), 1); await settle(page);
    assert.equal((await node(badgeLocal)).fills[0].color, '#AA0044', 'Update from library brought the new colour'); assert.equal(await ev(c => HD.store.get(HD.store.children(c)[0]).comp, chip), badgeLocal, 'the ids stayed, so instances still point at it');
    await page.locator('.hd-left .hd-tab', {hasText: 'Layers'}).click(); await settle(page);

    /* ---- an instance inside an instance: the path goes through the nested instance, a swap keeps what still fits ---- */
    const ic = await ev(c => HD.comp.insertAt(c, 2000, 2000), chip); await settle(page);
    const nest = await ev(([c, b]) => ({ni: HD.store.children(c)[0], text: HD.store.children(b)[0]}), [chip, badgeLocal]), deep = nest.ni + '/' + nest.text;
    assert.equal(await ev(([i, p]) => HD.comp.vnode(i, p).n.chars, [ic, deep]), 'Hot', 'the nested instance shows the override its component gave it');
    await ev(([i, p]) => HD.comp.setOverride(i, p, {chars: 'Sale'}), [ic, deep]); assert.deepEqual((await node(ic)).ov, {[deep]: {chars: 'Sale'}});
    assert.equal(await ev(([i, p]) => HD.comp.vnode(i, p).n.chars, [ic, deep]), 'Sale'); assert.equal(await ev(([i, n]) => HD.comp.vnode(i, n).isRoot, [ic, nest.ni]), true);
    await ev(i => HD.comp.select(i[0], i[1]), [ic, deep]); await settle(page); assert.equal(await page.locator('.hdc-sub .hd-selname').textContent(), 'Badge text'); await ev(() => HD.comp.deselect());
    await ev(i => HD.comp.detach([i]), ic); await settle(page);
    const dk = await ev(i => { const k = HD.store.children(i)[0], n = HD.store.get(k); return {type: n.type, comp: n.comp, ov: n.ov, fresh: k}; }, ic);
    assert.equal(dk.type, 'INSTANCE', 'detaching keeps a nested instance an instance'); assert.equal(dk.comp, badgeLocal); assert.deepEqual(dk.ov, {[nest.text]: {chars: 'Sale'}}, 'with the change that was made inside it'); assert.notEqual(dk.fresh, nest.ni);
    await ev(i => { HD.sel.set([i]); HD.tools.act.remove(); }, ic); await settle(page);

    /* ---- deleting a main component detaches its instances first, in the same undo step ---- */
    const users = await ev(() => HD.comp.instancesOf('9:1')); assert.ok(users.length >= 3);
    await ev(() => { HD.sel.set(['9:1']); HD.tools.act.remove(); }); await settle(page);
    assert.equal(await node('9:1'), null); for (const u of users) { const n = await node(u); assert.equal(n.type, 'FRAME', 'an instance of the deleted component became a frame'); assert.equal(await ev(i => HD.store.children(i).length, u), 2); }
    assert.equal(await ev(i => HD.store.get(HD.store.children(i)[0]).chars, i1), 'Pay later', 'with its overrides');
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+z'); await settle(page);
    assert.equal((await node('9:1')).type, 'COMPONENT'); assert.equal((await node(i1)).type, 'INSTANCE'); assert.equal(await ev(i => HD.store.children(i).length, i1), 0, 'one undo: the component and its instances are back');

    /* ---- dark theme ---- */
    await ev(i => HD.sel.set([i]), i1); await ev(() => window.HoolaTheme.setTheme('dark')); await settle(page); await shot(page, 'instance-dark');
    assert.deepEqual(await ev(layoutProblems), [], 'layout in dark'); await ev(() => window.HoolaTheme.setTheme('light'));

    /* ---- two editors on the file see the same document and the same picture ---- */
    await idle();
    const two = await newPage({width: 1280, height: 800}); await two.goto(base + '#/f/f1'); await mounted(two); await settle(two);
    const docOf = p => p.evaluate(() => { const d = HD.store.toDoc().nodes, out = {}; for (const k of Object.keys(d).sort()) { const o = {}; for (const p2 of Object.keys(d[k]).sort()) o[p2] = d[k][p2]; out[k] = o; } return JSON.stringify(out); });
    assert.equal(await docOf(two), await docOf(page), 'the second editor loaded the same document');
    /* an override made in one editor, a style edit in the other: both arrive, nobody fights */
    await ev(i => HD.comp.setOverride(i, '9:3', {fills: [{type: 'solid', color: '#00FFAA', opacity: 1, visible: true}]}), i1);
    await two.evaluate(s => HD.comp.updateStyle(s, {value: [{type: 'solid', color: '#FF8800', opacity: 1, visible: true}]}), sid);
    await two.evaluate(v => HD.comp.setVarValue(v, 'Dark', '#101010'), vid);
    await page.waitForFunction(() => HD.net.pending() === 0); await two.waitForFunction(() => HD.net.pending() === 0);
    await page.waitForFunction(v => HD.store.get('9:8').fills[0].color === '#101010' && HD.store.get('9:5').fills[0].color === '#FF8800', vid, {timeout: 10000});
    await two.waitForFunction(i => { const n = HD.store.get(i); return n && n.ov && n.ov['9:3'] && n.ov['9:3'].fills[0].color === '#00FFAA'; }, i1, {timeout: 10000});
    await settle(page); await settle(two);
    assert.equal(await docOf(two), await docOf(page), 'both editors hold the same document after editing on both sides');
    assert.equal(await pix(two, i1), await pix(page, i1), 'and draw the instance the same'); assert.equal(await mid(two, '9:8'), '#101010'); assert.equal(await mid(page, '9:5'), '#FF8800');
    const server = mock.files.get('f1').doc.nodes; assert.equal(server[i1].ov['9:3'].fills[0].color, '#00FFAA', 'the server has the override'); assert.equal(server['0:0'].styles[sid].value[0].color, '#FF8800'); assert.equal(server['9:8'].fills[0].color, '#101010');
    await shot(two, 'second-editor'); await two.close(); await page.close();
    assert.deepEqual(errors, [], 'no script errors');
    console.log('design_components_test: ok');
  } catch (e) { if (shots && browser.contexts().length) { let i = 0; for (const c of browser.contexts()) for (const pg of c.pages()) { try { await pg.screenshot({path: path.join(shots, 'FAILED-' + (i++) + '.png')}); } catch (e2) { /* closed */ } } } throw e;
  } finally { await browser.close().catch(() => {}); await mock.close(); }
}
module.exports = {seed, libDoc};
if (require.main === module) walk().catch(e => { console.error(e); process.exit(1); });
