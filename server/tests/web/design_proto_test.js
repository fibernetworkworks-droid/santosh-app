/* HOOLA DESIGN - browser walk of phase D6 "prototype" (hd-proto.js + design-proto.css) against the REAL editor files
   and the small mock server of design_ui_test.js (REST + a one-file WebSocket room).
   Run:  node server/tests/web/design_proto_test.js        (DESIGN_SHOTS=<dir> also writes screenshots)
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium). The last line is a JSON report.

   It wires an interaction by dragging the + handle, edits it in the popover and the Prototype tab (one undo step
   each), then PLAYS: a three-screen flow by real clicks (home -> detail -> overlay -> back), smart animate stepped
   to its middle on the player's own clock (the matched layer is half way, read from the canvas pixels too), a
   scrolling frame with a fixed header, hover / press / drag / delay / key triggers, the https-only link question,
   the keys of the player, a reload on the player address, view only, and reduced motion. The document must be the
   same before and after playing: the store, the server's copy and the op log. */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const {startMock, newDoc, layoutProblems} = require('./design_ui_test.js');

const solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}];
function seed() {
  const doc = newDoc(), n = doc.nodes;
  n['0:1'].name = 'Flows';
  Object.assign(n, {
    '9:1': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Home', x: 0, y: 0, w: 390, h: 844, fills: solid('#FFFFFF'), protoStart: true, flowName: 'Shop'},
    '9:2': {type: 'TEXT', parent: '9:1', idx: 'a0', name: 'Title', x: 24, y: 60, w: 200, h: 34, chars: 'Sweet shop', fontSize: 28, fontWeight: 600, fills: solid('#1A1A1F')},
    '9:3': {type: 'RECT', parent: '9:1', idx: 'a1', name: 'Card', x: 24, y: 130, w: 342, h: 180, radius: 20, fills: solid('#6E55F0'),
      reactions: [{trigger: 'click', action: 'navigate', to: '9:10', anim: {type: 'smart', dir: 'left', dur: 400, ease: 'linear'}}]},
    '9:4': {type: 'RECT', parent: '9:1', idx: 'a2', name: 'Button', x: 24, y: 340, w: 342, h: 56, radius: 14, fills: solid('#EE8F35')},
    '9:10': {type: 'FRAME', parent: '0:1', idx: 'a1', name: 'Detail', x: 520, y: 0, w: 390, h: 844, fills: solid('#F4F1FF')},
    '9:11': {type: 'RECT', parent: '9:10', idx: 'a0', name: 'Card', x: 0, y: 0, w: 390, h: 420, radius: 0, fills: solid('#EE8F35'), reactions: [{trigger: 'click', action: 'back'}]},
    '9:13': {type: 'TEXT', parent: '9:10', idx: 'a1', name: 'Title', x: 24, y: 450, w: 290, h: 48, chars: 'Sweet shop', fontSize: 40, fontWeight: 600, fills: solid('#1A1A1F')},
    '9:12': {type: 'RECT', parent: '9:10', idx: 'a2', name: 'Buy', x: 24, y: 760, w: 342, h: 56, radius: 14, fills: solid('#1A1A1F'),
      reactions: [{trigger: 'click', action: 'overlay', to: '9:20', anim: {type: 'move', dir: 'up', dur: 300, ease: 'out'}}]},
    '9:20': {type: 'FRAME', parent: '0:1', idx: 'a2', name: 'Sheet', x: 1040, y: 0, w: 320, h: 240, radius: 18, fills: solid('#FFFFFF'), overlay: {pos: 'bc'}},
    '9:21': {type: 'RECT', parent: '9:20', idx: 'a0', name: 'Close', x: 24, y: 160, w: 272, h: 48, radius: 12, fills: solid('#6E55F0'), reactions: [{trigger: 'click', action: 'close'}]},
    '9:30': {type: 'FRAME', parent: '0:1', idx: 'a3', name: 'Feed', x: 0, y: 1000, w: 390, h: 844, fills: solid('#FFFFFF'), scroll: 'v', protoStart: true, flowName: 'Feed'},
    '9:31': {type: 'RECT', parent: '9:30', idx: 'a0', name: 'Header', x: 0, y: 0, w: 390, h: 90, fills: solid('#6E55F0'), fixed: true},
    '9:40': {type: 'FRAME', parent: '0:1', idx: 'a4', name: 'Lab', x: 520, y: 1000, w: 390, h: 844, fills: solid('#14122B'),
      reactions: [{trigger: 'after', delay: 800, action: 'navigate', to: '9:30'}, {trigger: 'key', key: 'g', action: 'navigate', to: '9:1'}]},
    '9:41': {type: 'RECT', parent: '9:40', idx: 'a0', name: 'Hover me', x: 40, y: 100, w: 310, h: 120, radius: 16, fills: solid('#3FCB98'), reactions: [{trigger: 'hover', action: 'overlay', to: '9:50'}]},
    '9:42': {type: 'RECT', parent: '9:40', idx: 'a1', name: 'Link', x: 40, y: 260, w: 310, h: 80, radius: 16, fills: solid('#F27D7D'), reactions: [{trigger: 'click', action: 'url', url: 'https://example.com/shop'}]},
    '9:43': {type: 'RECT', parent: '9:40', idx: 'a2', name: 'Bad link', x: 40, y: 360, w: 310, h: 60, radius: 16, fills: solid('#8A85AC'), reactions: [{trigger: 'click', action: 'url', url: 'javascript:alert(1)'}]},
    '9:44': {type: 'RECT', parent: '9:40', idx: 'a3', name: 'Press', x: 40, y: 440, w: 310, h: 60, radius: 16, fills: solid('#EE8F35'), reactions: [{trigger: 'press', action: 'overlay', to: '9:50'}]},
    '9:45': {type: 'RECT', parent: '9:40', idx: 'a4', name: 'Drag', x: 40, y: 520, w: 310, h: 60, radius: 16, fills: solid('#B347E6'), reactions: [{trigger: 'drag', action: 'navigate', to: '9:1'}]},
    '9:50': {type: 'FRAME', parent: '0:1', idx: 'a5', name: 'Tip', x: 1040, y: 1000, w: 220, h: 120, radius: 14, fills: solid('#FFFFFF'), overlay: {pos: 'tc', dim: false}}
  });
  for (let i = 0; i < 6; i++) n['9:' + (32 + i)] = {type: 'RECT', parent: '9:30', idx: 'b' + i, name: 'Row ' + i, x: 20, y: 110 + i * 300, w: 350, h: 280, radius: 16, fills: solid(i % 2 ? '#EE8F35' : '#B347E6')};
  return doc;
}

async function walk() {
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  const mock = await startMock(seed());
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { await mock.close(); console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const errors = []; let checks = 0;
  const eq = (a, b, msg) => { checks++; assert.deepEqual(a, b, msg); }, yes = (v, msg) => { checks++; assert.ok(v, msg); };
  const near = (a, b, tol, msg) => { checks++; assert.ok(Math.abs(a - b) <= tol, msg + ': ' + a + ' is not near ' + b); };
  const isColor = (got, want, msg) => { checks++; assert.ok(got && want.every((v, i) => Math.abs(got[i] - v) <= 8), msg + ': ' + JSON.stringify(got) + ' is not ' + JSON.stringify(want)); };
  async function newPage(viewport, opts) {
    const page = await browser.newPage(Object.assign({viewport: viewport, colorScheme: 'light'}, opts || {}));
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(() => localStorage.setItem('hoola.console.token', 'fixture-only'));
    return page;
  }
  const base = 'http://127.0.0.1:' + mock.port + '/console/design';
  const mounted = page => page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0 && HD.proto, null, {timeout: 20000});
  const settle = page => page.evaluate(() => new Promise(done => { let last = '', same = 0, n = 0; const tick = () => { const v = [HD.render.view.x, HD.render.view.y, HD.render.view.zoom].join(); same = v === last ? same + 1 : 0; last = v; if (same >= 3 || ++n > 90) setTimeout(done, 30); else requestAnimationFrame(tick); }; requestAnimationFrame(tick); }));
  const frames = (page, n) => page.evaluate(k => new Promise(done => { const t = () => { if (--k <= 0) done(); else requestAnimationFrame(t); }; requestAnimationFrame(t); }), n || 2);
  const shot = async (page, name) => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };
  const serverDoc = () => JSON.stringify(mock.files.get('f1').doc);
  const until = async (fn, msg) => { for (let i = 0; i < 100; i++) { if (fn()) return; await new Promise(r => setTimeout(r, 30)); } assert.fail('waited in vain: ' + msg); };
  try {
    /* ================================================================ the editor: wiring + the Prototype tab */
    const page = await newPage({width: 1440, height: 900});
    const st = () => page.evaluate(() => HD.proto.state());
    const prop = (id, name) => page.evaluate(([i, k]) => { const v = HD.store.get(i)[k]; return v === undefined ? null : v; }, [id, name]);
    const select = async ids => { await page.evaluate(l => HD.sel.set(l), ids); await frames(page, 3); };
    const toClient = (sx, sy) => page.evaluate(([x, y]) => { const r = HD.tools.canvas.getBoundingClientRect(); return [r.left + x, r.top + y]; }, [sx, sy]);
    const centre = id => page.evaluate(i => { const b = HD.store.worldBounds(i), s = HD.render.worldToScreen(b.x + b.w / 2, b.y + b.h / 2), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; }, id);
    const stopClocks = () => page.evaluate(() => HD.proto.clock.freeze()), stepClock = ms => page.evaluate(m => HD.proto.clock.step(m), ms);
    const at = id => page.evaluate(i => HD.proto.pointOf(i), id);
    const click = async id => { const p = await at(id); assert.ok(p, 'the layer ' + id + ' is on the screen of the player'); await page.mouse.click(p[0], p[1]); };
    /* the colour of one pixel of the player, at a point given in frame units of the window */
    const px = (fx, fy) => page.evaluate(([x, y]) => { const L = HD.proto.state().layout, cv = document.querySelector('.hdp-canvas'), d = cv.width / cv.getBoundingClientRect().width; const p = cv.getContext('2d').getImageData(Math.round((L.x + x * L.k) * d), Math.round((L.y + y * L.k) * d), 1, 1).data; return [p[0], p[1], p[2]]; }, [fx, fy]);

    await page.goto(base + '#/f/f1'); await mounted(page); await settle(page);
    await page.locator('.hd-right .hd-tab', {hasText: 'Prototype'}).click(); await frames(page, 3);
    eq(await page.locator('.hd-right .hd-tab').allTextContents(), ['Design', 'Prototype'], 'one Prototype tab beside Design');
    yes(await page.locator('.hdp-panel').isVisible(), 'the Prototype tab shows');
    eq(await page.locator('.hdp-flowrow').count(), 2, 'both flows are listed');
    eq(await page.evaluate(layoutProblems), [], 'layout, Prototype tab with nothing selected'); await shot(page, 'proto-tab-page-light');

    /* ---- drag the + handle of the button onto the Detail frame ---- */
    await select(['9:4']);
    const opsBefore = mock.log.ops.length;
    const hd = await page.evaluate(() => HD.proto.handle()); yes(hd && hd.node === '9:4', 'a + handle beside the selected layer');
    const from = await toClient(hd.x, hd.y), to = await centre('9:10');
    await page.mouse.move(from[0], from[1]); await page.mouse.down(); await page.mouse.move((from[0] + to[0]) / 2, to[1] - 40, {steps: 4}); await shot(page, 'proto-wire-dragging');
    await page.mouse.move(to[0], to[1], {steps: 4}); await page.mouse.up(); await frames(page, 3);
    const wired = {trigger: 'click', action: 'navigate', to: '9:10', anim: {type: 'dissolve', dir: 'left', dur: 300, ease: 'out'}};
    eq(await prop('9:4', 'reactions'), [wired], 'the drag made a navigate reaction to the frame under the pointer');
    eq(await prop('9:4', 'x'), 24, 'and the layer did not move');
    await until(() => mock.log.ops.length > opsBefore, 'the op reaches the server');
    eq(mock.log.ops.length, opsBefore + 1, 'one op batch'); eq(mock.files.get('f1').doc.nodes['9:4'].reactions, [wired], 'which reached the server');
    eq(await page.evaluate(() => HD.store.undoLabel()), 'Add interaction');
    await page.evaluate(() => HD.store.undo()); eq(await prop('9:4', 'reactions'), null, 'one undo takes the whole wire back');
    await page.evaluate(() => HD.store.redo()); eq(await prop('9:4', 'reactions'), [wired], 'redo'); await frames(page, 3);
    const wires = await page.evaluate(() => HD.proto.wires().map(w => ({node: w.node, to: w.to, pts: w.pts})));
    const mine = wires.find(w => w.node === '9:4'); yes(mine && mine.to === '9:10' && mine.pts, 'the arrow is drawn');
    yes(wires.some(w => w.node === '9:3' && w.to === '9:10') && wires.some(w => w.node === '9:12' && w.to === '9:20'), 'with the arrows that were there');
    eq(await page.locator('.hdp-ix').count(), 1, 'the interaction is in the list'); eq((await page.locator('.hdp-ixb').first().textContent()).replace(/\s+/g, ' ').trim(), 'On clickDetail');
    eq(await page.evaluate(layoutProblems), [], 'layout, a wired layer'); await shot(page, 'proto-wired-light');

    /* ---- click the arrow: the popover edits it, one undo step per change ---- */
    const bez = (b, t) => { const u = 1 - t; return [u * u * u * b[0][0] + 3 * u * u * t * b[1][0] + 3 * u * t * t * b[2][0] + t * t * t * b[3][0], u * u * u * b[0][1] + 3 * u * u * t * b[1][1] + 3 * u * t * t * b[2][1] + t * t * t * b[3][1]]; };
    const wireClick = async () => { const w = (await page.evaluate(() => HD.proto.wires().map(x => ({node: x.node, pts: x.pts})))).find(x => x.node === '9:4'), m = bez(w.pts, 0.5), c = await toClient(m[0], m[1]); await page.mouse.click(c[0], c[1]); await frames(page, 3); };
    await wireClick();
    yes(await page.locator('.hdp-pop').isVisible(), 'a click on the arrow opens the interaction');
    eq(await page.evaluate(() => HD.sel.ids.slice()), ['9:4'], 'the layer stays selected');
    const ed = page.locator('.hdp-pop'), r0 = async () => (await prop('9:4', 'reactions'))[0];
    await ed.locator('select[aria-label="Animation"]').selectOption('push'); eq((await r0()).anim.type, 'push'); eq(await page.evaluate(() => HD.store.undoLabel()), 'Change animation');
    await ed.locator('.hdp-dir button[aria-label="Upwards"]').click(); eq((await r0()).anim.dir, 'up');
    await ed.locator('select[aria-label="Easing"]').selectOption('spring'); eq((await r0()).anim.ease, 'spring');
    const dur = ed.locator('input[aria-label="Duration in milliseconds"]'); await dur.fill('450'); await dur.press('Enter'); eq((await r0()).anim.dur, 450);
    eq(await page.evaluate(layoutProblems), [], 'layout, the interaction popover'); await shot(page, 'proto-popover-light');
    await ed.locator('select[aria-label="Trigger"]').selectOption('after'); eq((await r0()).trigger, 'after'); eq((await r0()).delay, 800); yes(await ed.locator('input[aria-label="Delay in milliseconds"]').isVisible(), 'a delay field');
    await ed.locator('select[aria-label="Trigger"]').selectOption('key'); await ed.locator('.hdp-key').click(); await page.keyboard.press('k'); eq((await r0()).key, 'k', 'the pressed key is kept'); eq(await page.evaluate(() => HD.tools.current), 'move', 'and it did not reach the editor');
    await ed.locator('select[aria-label="Trigger"]').selectOption('click'); eq((await r0()).delay, undefined); eq((await r0()).key, undefined);
    await ed.locator('select[aria-label="Action"]').selectOption('overlay'); await ed.locator('.hdp-di', {hasText: 'Sheet'}).click(); eq([(await r0()).action, (await r0()).to], ['overlay', '9:20']);
    await ed.locator('select[aria-label="Action"]').selectOption('url'); const url = ed.locator('input[aria-label="Link address"]');
    await url.fill('javascript:alert(1)'); await url.press('Enter'); eq((await r0()).url, undefined, 'a link that is not https is not kept');
    await url.fill('example.com/a'); await url.press('Enter'); eq((await r0()).url, 'https://example.com/a'); eq((await r0()).to, undefined);
    await ed.locator('select[aria-label="Action"]').selectOption('navigate'); await ed.locator('.hdp-di', {hasText: 'Detail'}).click(); eq((await r0()).to, '9:10');
    await ed.locator('select[aria-label="Animation"]').selectOption('dissolve');
    await page.keyboard.press('Escape'); await frames(page, 2); eq(await page.locator('.hdp-pop').count(), 0);
    const layers = await page.evaluate(() => HD.store.count());
    await wireClick(); await page.keyboard.press('Escape'); await frames(page, 2);
    await wireClick(); await page.locator('.hd-canvas').focus(); await page.keyboard.press('Delete'); await frames(page, 3);
    eq(await prop('9:4', 'reactions'), null, 'Delete removes the selected arrow'); eq(await page.evaluate(() => HD.store.count()), layers, 'not the layer');
    await page.evaluate(() => HD.store.undo()); eq((await r0()).to, '9:10', 'and undo brings it back');

    /* ---- the Prototype tab: flow start, scrolling, fixed, overlay, device, the + button ---- */
    await select(['9:1']); eq(await page.locator('.hdp-panel input[aria-label="Flow name"]').inputValue(), 'Shop');
    await select(['9:10']); await page.locator('.hdp-panel button[title="Start a flow at this frame"]').click(); await frames(page, 3);
    eq([await prop('9:10', 'protoStart'), await prop('9:10', 'flowName')], [true, 'Flow 1']); eq(await page.evaluate(() => HD.proto.flows(HD.sel.page).length), 3);
    await page.locator('.hdp-panel button[title="Remove the starting point"]').click(); await frames(page, 3); eq([await prop('9:10', 'protoStart'), await prop('9:10', 'flowName')], [null, null]);
    await page.locator('.hdp-panel select[aria-label="Scroll behaviour"]').selectOption('both'); eq(await prop('9:10', 'scroll'), 'both'); await page.evaluate(() => HD.store.undo()); eq(await prop('9:10', 'scroll'), null);
    await frames(page, 3); await page.locator('.hdp-panel select[aria-label="Overlay position"]').selectOption('manual'); await frames(page, 3);
    const ox = page.locator('.hdp-panel input[aria-label="Overlay X"]'); await ox.fill('12'); await ox.press('Enter'); await frames(page, 3); eq(await prop('9:10', 'overlay'), {pos: 'manual', x: 12});
    await page.locator('.hdp-panel .hd-check', {hasText: 'Dim the background'}).locator('input').uncheck(); eq((await prop('9:10', 'overlay')).dim, false);
    eq(await page.evaluate(layoutProblems), [], 'layout, a screen in the Prototype tab');
    await page.evaluate(() => { HD.store.undo(); HD.store.undo(); HD.store.undo(); }); eq(await prop('9:10', 'overlay'), null, 'three steps, three undos');
    await select(['9:11']); const fix = page.locator('.hdp-panel .hd-check', {hasText: 'Fix position when scrolling'}).locator('input');
    await fix.check(); eq(await prop('9:11', 'fixed'), true); await frames(page, 3); await page.locator('.hdp-panel .hd-check', {hasText: 'Fix position when scrolling'}).locator('input').uncheck(); eq(await prop('9:11', 'fixed'), null);
    await select(['9:2']); await page.locator('.hdp-panel button[title="Add an interaction"]').click(); await frames(page, 3);
    eq(await prop('9:2', 'reactions'), [wired], 'the + button adds a navigate to the next frame'); yes(await page.locator('.hdp-pop').isVisible(), 'and opens it');
    await page.locator('.hdp-pop .hdp-del').click(); await frames(page, 3); eq(await prop('9:2', 'reactions'), null, 'Remove');
    await select([]); await page.locator('.hdp-panel select[aria-label="Device"]').selectOption('phone'); eq(await prop('0:1', 'device'), 'phone'); await frames(page, 3);

    /* ================================================================ the player */
    /* a phone around the frame, in the dark */
    await page.emulateMedia({colorScheme: 'dark'}); await select(['9:1']);
    await page.evaluate(() => HD.proto.open('9:1')); await frames(page, 3);
    let s = await st(); eq([s.open, s.frame, s.device], [true, '9:1', 'phone']); near(s.layout.w / s.layout.h, 390 / 844, 0.002, 'the screen of the phone');
    isColor(await px(195, 500), [255, 255, 255], 'the frame is drawn inside the phone'); await shot(page, 'proto-player-phone-dark');
    await page.keyboard.press('Escape'); await frames(page, 3); eq(await page.evaluate(() => HD.proto.isOpen), false);
    eq(await page.evaluate(layoutProblems), [], 'layout, dark'); await shot(page, 'proto-tab-dark');
    await page.emulateMedia({colorScheme: 'light'});
    await select([]); await page.locator('.hdp-panel select[aria-label="Device"]').selectOption('none'); eq(await prop('0:1', 'device'), null); await until(() => mock.files.get('f1').doc.nodes['0:1'].device === undefined, 'the last edit reaches the server');

    /* ---- from here on nothing may change the document ---- */
    const docBefore = await page.evaluate(() => JSON.stringify(HD.store.toDoc())), serverBefore = serverDoc(), opsPlay = mock.log.ops.length, undoBefore = await page.evaluate(() => HD.store.undoLabel());
    await select(['9:1']);
    await page.locator('.hd-top button[title="Present"]').click(); await page.locator('.hdp').waitFor(); await frames(page, 3);
    s = await st(); eq([s.frame, s.start, s.history, s.overlays], ['9:1', '9:1', [], []]); eq(await page.evaluate(() => location.hash), '#/f/f1/p/9%3A1', 'the address of the player');
    near(s.layout.w / s.layout.h, 390 / 844, 0.002, 'the frame fits the window'); isColor(await px(195, 220), [110, 85, 240], 'the real renderer drew the card');
    eq((await page.locator('.hdp-count').textContent()).trim(), '1 / 6'); eq(await page.locator('.hdp-name').textContent(), 'Home');
    const bar = await page.evaluate(() => { const bad = [], vw = innerWidth; for (const g of document.querySelectorAll('.hdp-l, .hdp-c, .hdp-r')) { const list = Array.from(g.children).filter(e => e.getBoundingClientRect().width > 0).map(e => e.getBoundingClientRect()); for (let i = 0; i < list.length; i++) { if (list[i].left < 0 || list[i].right > vw) bad.push('outside'); for (let j = i + 1; j < list.length; j++) if (Math.min(list[i].right, list[j].right) - Math.max(list[i].left, list[j].left) > 1) bad.push('overlap'); } }
      const l = document.querySelector('.hdp-l').getBoundingClientRect(), c = document.querySelector('.hdp-c').getBoundingClientRect(), r = document.querySelector('.hdp-r').getBoundingClientRect(); if (l.right > c.left + 1 || c.right > r.left + 1) bad.push('groups overlap'); return bad; });
    eq(bar, [], 'the toolbar of the player'); await shot(page, 'proto-player-light');

    /* ---- home -> detail by smart animate, stopped in the middle ---- */
    await stopClocks(); await click('9:3');
    s = await st(); eq([s.frame, s.history, s.anim.kind], ['9:10', ['9:1'], 'smart']);
    await stepClock(200); s = await st(); near(s.anim.p, 0.5, 0.001, 'half way');
    const card = s.smart.find(x => x.name === 'Card'), title = s.smart.find(x => x.name === 'Title');
    eq([card.a, card.b, card.x, card.y, card.w, card.h], ['9:3', '9:11', 12, 65, 366, 300], 'the matched card is half way between its two boxes');
    eq([title.x, title.y], [24, 255], 'so is the matched title');
    isColor(await px(195, 215), [174, 114, 147], 'its colour is half way too'); isColor(await px(16, 70), [174, 114, 147], 'it has grown to the left and up');
    isColor(await px(6, 215), [250, 248, 255], 'but not yet to the edge (the frame colour is half way as well)'); isColor(await px(195, 400), [250, 248, 255], 'nor to its full height'); await shot(page, 'proto-smart-middle');
    const mid = await px(195, 790); yes(mid[0] > 100 && mid[0] < 200, 'the unmatched Buy button is fading in: ' + mid);
    await stepClock(250); s = await st(); eq([s.anim, s.frame, s.history], [null, '9:10', ['9:1']]);
    isColor(await px(195, 215), [238, 143, 53], 'the detail frame'); isColor(await px(195, 790), [26, 26, 31], 'with its button');
    eq(await page.evaluate(() => location.hash), '#/f/f1/p/9%3A10', 'the address follows');

    /* ---- detail -> the overlay (moves in from below), a click on nothing, close ---- */
    await click('9:12'); s = await st(); eq([s.anim.kind, s.overlays.map(o => o.id)], ['ovin', ['9:20']]);
    await stepClock(150); const dim = await px(195, 600); yes(dim[0] > 150 && dim[0] < 240, 'the background is dimming: ' + dim); await stepClock(200);
    s = await st(); eq([s.anim, s.overlays], [null, [{id: '9:20', x: 35, y: 604, scroll: {x: 0, y: 0}}]], 'the sheet sits at the bottom centre');
    isColor(await px(195, 650), [255, 255, 255], 'the sheet'); isColor(await px(195, 300), [143, 86, 32], 'over the dimmed frame'); await shot(page, 'proto-overlay');
    await page.mouse.click(...(await at('9:20')).map((v, i) => v - (i ? 60 * s.layout.k : 0))); s = await st(); eq([s.hints, s.overlays.length], [1, 1], 'a click on nothing shows where to click'); await stepClock(100); await shot(page, 'proto-hints');
    await stepClock(800); eq((await st()).hints, 0);
    await click('9:21'); eq((await st()).anim.kind, 'ovout'); await stepClock(400); s = await st(); eq([s.anim, s.overlays, s.frame], [null, [], '9:10'], 'Close closes the overlay');
    await click('9:12'); await stepClock(400); eq((await st()).overlays.length, 1);
    const out = await at('9:11'); await page.mouse.click(out[0], out[1]); await stepClock(400); s = await st(); eq([s.overlays, s.frame], [[], '9:10'], 'a click outside closes it and reaches nothing under it');

    /* ---- back ---- */
    await click('9:11'); s = await st(); eq([s.frame, s.history, s.anim.kind], ['9:1', [], 'smart'], 'Back plays the way it came, the other way round');
    await stepClock(200); eq((await st()).smart.find(x => x.name === 'Card').y, 65); await stepClock(300); eq((await st()).anim, null); isColor(await px(195, 220), [110, 85, 240], 'home again');

    /* ---- the same click on the real clock ---- */
    await page.evaluate(() => HD.proto.clock.release()); await click('9:3');
    await page.waitForFunction(() => { const x = HD.proto.state(); return x.frame === '9:10' && !x.anim; }, null, {timeout: 5000}); checks++;

    /* ---- keys: next / previous frame, restart ---- */
    await stopClocks();
    await page.keyboard.press('ArrowRight'); eq((await st()).frame, '9:20'); await page.keyboard.press('ArrowLeft'); eq((await st()).frame, '9:10');
    eq(await page.evaluate(() => HD.tools.current), 'move'); await page.keyboard.press('r'); s = await st(); eq([s.frame, s.history], ['9:1', []], 'R starts again'); eq(await page.evaluate(() => HD.tools.current), 'move', 'and the key never reached the editor');

    /* ---- another flow: a frame that scrolls under a fixed header ---- */
    await page.locator('.hdp-flow').click(); await page.locator('.hd-pop .hd-mi', {hasText: 'Feed'}).click(); await frames(page, 2); await stepClock(0);
    s = await st(); eq([s.frame, s.start, s.scroll], ['9:30', '9:30', {x: 0, y: 0, maxX: 0, maxY: 1046}], 'the content is as tall as its layers');
    isColor(await px(195, 45), [110, 85, 240], 'header'); isColor(await px(195, 250), [179, 71, 230], 'row 0');
    const h0 = await at('9:31'), r0p = await at('9:32'), cv = await page.locator('.hdp-canvas').boundingBox();
    await page.mouse.move(cv.x + cv.width / 2, cv.y + cv.height / 2); await page.mouse.wheel(0, 240); await stepClock(0);
    s = await st(); near(s.scroll.y, 240 / s.layout.k, 0.01, 'the wheel scrolls the frame');
    const h1 = await at('9:31'), r1p = await at('9:32'); eq(h1, h0, 'the fixed header stays'); near(r0p[1] - r1p[1], 240, 0.01, 'the rows move');
    isColor(await px(195, 45), [110, 85, 240], 'the header is still on top'); isColor(await px(195, 300), [238, 143, 53], 'row 1 has come up'); await shot(page, 'proto-scroll-fixed');
    await page.mouse.wheel(0, 99999); await stepClock(0); eq((await st()).scroll.y, 1046, 'it stops at the end'); await page.mouse.wheel(0, -99999); await stepClock(0); eq((await st()).scroll.y, 0);
    /* a finger drags it and it keeps gliding */
    await page.evaluate(([x, y]) => { const cvs = document.querySelector('.hdp-canvas'), ev = (t, yy) => cvs.dispatchEvent(new PointerEvent(t, {pointerId: 7, pointerType: 'touch', isPrimary: true, clientX: x, clientY: yy, button: 0, buttons: t === 'pointerup' ? 0 : 1, bubbles: true, cancelable: true}));
      ev('pointerdown', y); for (let i = 1; i <= 6; i++) { HD.proto.clock.step(16); ev('pointermove', y - i * 25); } HD.proto.clock.step(16); ev('pointerup', y - 150); }, [cv.x + cv.width / 2, cv.y + cv.height / 2]);
    const y1 = (await st()).scroll.y; near(y1, 150 / s.layout.k, 0.5, 'a touch drag scrolls'); await stepClock(100); const y2 = (await st()).scroll.y; yes(y2 > y1 + 20, 'and glides on: ' + y1 + ' -> ' + y2);
    await page.evaluate(() => { for (let i = 0; i < 300; i++) HD.proto.clock.step(32); }); const y3 = (await st()).scroll.y; await stepClock(500); eq((await st()).scroll.y, y3, 'until it rests'); yes(y3 > y2 && y3 < 1046, 'somewhere before the end: ' + y3);

    /* ---- delay, hover, press, drag, link, key ---- */
    await page.mouse.move(cv.x + 5, cv.y + 5);
    await page.evaluate(() => HD.proto.open('9:40')); s = await st(); eq([s.frame, s.timers], ['9:40', 1], 'a timer waits');
    await stepClock(700); eq((await st()).frame, '9:40'); await stepClock(150); eq((await st()).frame, '9:30', 'after the delay it moves on'); eq((await st()).timers, 0);
    await page.evaluate(() => HD.proto.open('9:40'));
    const hv = await at('9:41'); await page.mouse.move(hv[0], hv[1]); eq((await st()).overlays.map(o => [o.id, o.x, o.y]), [['9:50', 85, 0]], 'hovering opens the tip at the top centre'); await stepClock(0); isColor(await px(195, 60), [255, 255, 255], 'the tip'); await shot(page, 'proto-hover');
    await page.mouse.move(hv[0], hv[1] + 10); eq((await st()).overlays.length, 1, 'while the pointer stays on the layer');
    await page.mouse.move(cv.x + 5, cv.y + 5); eq((await st()).overlays, [], 'and leaving takes it away');
    const pr = await at('9:44'); await page.mouse.move(pr[0], pr[1]); await page.mouse.down(); eq((await st()).overlays.map(o => o.id), ['9:50'], 'while pressing'); await page.mouse.up(); eq((await st()).overlays, [], 'released');
    const dg = await at('9:45'); await page.mouse.move(dg[0], dg[1]); await page.mouse.down(); eq((await st()).frame, '9:40'); await page.mouse.move(dg[0] + 40, dg[1], {steps: 3}); eq((await st()).frame, '9:1', 'a drag'); await page.mouse.up(); eq((await st()).frame, '9:1');
    await page.evaluate(() => HD.proto.open('9:40'));
    await click('9:42'); yes(await page.locator('.hdp-ask').isVisible(), 'a link asks first'); eq(await page.locator('.hdp-url').textContent(), 'https://example.com/shop'); eq((await st()).ask, true); await shot(page, 'proto-link-ask');
    const pagesBefore = page.context().pages().length; await page.locator('.hdp-ask button', {hasText: 'Stay here'}).click(); eq(await page.locator('.hdp-ask').count(), 0); eq(page.context().pages().length, pagesBefore, 'nothing opened');
    await click('9:43'); eq(await page.locator('.hdp-ask').count(), 0, 'a link that is not https is never offered'); yes(/not a secure https/.test(await page.locator('.hd-toast').textContent()), 'and she is told');
    await page.keyboard.press('g'); eq((await st()).frame, '9:1', 'the key of the frame');
    /* the size options */
    await page.locator('.hdp-r .hd-segb', {hasText: 'Fill'}).click(); s = await st(); eq(s.zoom, 'fill'); yes(s.layout.w > 1300 && s.scroll.maxY > 0, 'Fill: as wide as the window, the rest scrolls');
    await page.locator('.hdp-r .hd-segb', {hasText: '100%'}).click(); s = await st(); near(s.layout.k, 1, 0.0001, '100%'); await page.locator('.hdp-r .hd-segb', {hasText: 'Fit'}).click(); eq((await st()).zoom, 'fit');
    /* copy the link */
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
    await page.locator('.hdp-r .hd-btn', {hasText: 'Copy link'}).click(); await page.waitForFunction(() => /Prototype link copied/.test((document.querySelector('.hd-toast') || {}).textContent || '')); checks++;
    eq(await page.evaluate(() => HD.proto.link('9:10')), base + '#/f/f1/p/9%3A10');

    /* ---- Esc: back in the editor, and nothing was written ---- */
    await page.evaluate(() => HD.proto.clock.release()); await page.keyboard.press('Escape'); await frames(page, 4);
    eq([await page.evaluate(() => HD.proto.isOpen), await page.locator('.hdp').count()], [false, 0]); await page.waitForFunction(() => location.hash === '#/f/f1'); checks++;
    yes(await page.evaluate(() => HD.ui.mounted && HD.store.readOnly === false && typeof HD.store.tx === 'function' && !Object.prototype.hasOwnProperty.call(HD.store, '__real')), 'the editor is there, on the real store');
    eq(await page.evaluate(() => JSON.stringify(HD.store.toDoc())), docBefore, 'playing did not change one byte of the document');
    eq(serverDoc(), serverBefore, 'nor of the server copy'); eq(mock.log.ops.length, opsPlay, 'no op was sent'); eq(await page.evaluate(() => HD.store.undoLabel()), undoBefore, 'no undo step was made');
    eq(await page.evaluate(() => Object.keys(HD.store.toDoc().nodes).filter(k => k.charAt(0) === '~')), [], 'no scratch node is in the store');

    /* ---- a reload on the player address brings the player back ---- */
    await page.goto(base + '#/f/f1/p/9%3A10'); await page.reload(); await page.waitForFunction(() => window.HD && HD.proto && HD.proto.isOpen, null, {timeout: 20000}); await frames(page, 3);
    s = await st(); eq([s.frame, await page.evaluate(() => location.hash)], ['9:10', '#/f/f1/p/9%3A10'], 'restored on the frame of the address');
    await page.evaluate(() => HD.proto.clock.step(0)); isColor(await px(195, 215), [238, 143, 53], 'and drawn');
    await page.evaluate(() => HD.proto.clock.release()); await page.keyboard.press('Escape'); await page.waitForFunction(() => location.hash === '#/f/f1' && !HD.proto.isOpen && HD.ui.mounted); checks++;
    await page.goto(base + '#/f/f1/p/nope'); await page.reload(); await page.waitForFunction(() => window.HD && HD.proto && HD.proto.isOpen, null, {timeout: 20000}); eq((await st()).frame, '9:1', 'a frame that is gone: the first flow');
    await page.goBack().catch(() => {}); await page.close();

    /* ================================================================ view only: it plays, it can not be edited */
    mock.server.viewOnly = true;
    const v = await newPage({width: 1280, height: 800}); await v.goto(base + '#/f/f1/p/9%3A1'); await v.waitForFunction(() => window.HD && HD.proto && HD.proto.isOpen, null, {timeout: 20000});
    eq(await v.evaluate(() => HD.app.file.role), 'view'); await v.evaluate(() => HD.proto.clock.freeze());
    const vp = await v.evaluate(() => HD.proto.pointOf('9:3')); await v.mouse.click(vp[0], vp[1]); await v.evaluate(() => HD.proto.clock.step(500)); eq(await v.evaluate(() => HD.proto.state().frame), '9:10', 'a view-only file plays');
    await v.evaluate(() => HD.proto.clock.release()); await v.keyboard.press('Escape'); await v.waitForFunction(() => !HD.proto.isOpen && HD.ui.mounted);
    await v.locator('.hd-right .hd-tab', {hasText: 'Prototype'}).click(); await v.evaluate(() => HD.sel.set(['9:3'])); await v.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    eq(await v.evaluate(() => HD.proto.handle()), null, 'no + handle'); eq(await v.locator('.hdp-panel button[title="Add an interaction"]').count(), 0, 'no + button'); yes(await v.locator('.hdp-ix .hd-ib').first().isDisabled(), 'Remove is off');
    await v.locator('.hdp-ixb').first().click(); yes(await v.locator('.hdp-pop select[aria-label="Animation"]').isDisabled(), 'the popover is read only'); eq(await v.locator('.hdp-pop .hdp-del').count(), 0);
    eq(await v.evaluate(layoutProblems), [], 'layout, view only'); await shot(v, 'proto-view-only');
    eq(serverDoc(), serverBefore, 'still the same document'); await v.close(); mock.server.viewOnly = false;

    /* ================================================================ reduced motion: a dissolve instead */
    const q = await newPage({width: 1280, height: 800}, {reducedMotion: 'reduce'}); await q.goto(base + '#/f/f1/p/9%3A1'); await q.waitForFunction(() => window.HD && HD.proto && HD.proto.isOpen, null, {timeout: 20000});
    await q.evaluate(() => HD.proto.clock.freeze()); const qp = await q.evaluate(() => HD.proto.pointOf('9:3')); await q.mouse.click(qp[0], qp[1]);
    eq(await q.evaluate(() => { const a = HD.proto.state().anim; return [a.kind, a.type]; }), ['screen', 'dissolve'], 'smart animate becomes a dissolve');
    await q.evaluate(() => HD.proto.clock.step(500)); eq(await q.evaluate(() => [HD.proto.state().frame, HD.proto.state().anim]), ['9:10', null]); await q.close();

    eq(errors, [], 'no script errors');
    console.log('design_proto_test: ok');
    console.log(JSON.stringify({checks: checks, shots: shots || null}));
  } catch (e) { if (shots && browser.contexts().length) { for (const c of browser.contexts()) for (const pg of c.pages()) { try { await pg.screenshot({path: path.join(shots, 'FAILED.png')}); } catch (e2) { /* closed */ } } } throw e;
  } finally { await browser.close().catch(() => {}); await mock.close(); }
}
if (require.main === module) walk().catch(e => { console.error(e); process.exit(1); });
module.exports = {seed};
