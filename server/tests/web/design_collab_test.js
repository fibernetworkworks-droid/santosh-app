/* HOOLA DESIGN - phase D5 "together" (hd-collab.js + the share mode of hd-app.js / hd-net.js) against a REAL server.
   Three browsers in ONE file: two signed-in editors (A, B) and one signed-out visitor (G) who came in through the
   view-only link. Checked: a comment appears live for all three, reply, resolve, unread dots, plain text only, the
   pin follows its layer; the visitor can not edit (its forged ops are refused by the server) and sees images
   through the public route; save a version -> edit -> preview the old one (nothing is sent, the live document
   stays whole, even while the other editor keeps working) -> back -> restore (both editors reload to it, the view
   stays where it was); duplicate a version as a new file; follow a person, spotlight, cursor chat; a link to one
   layer; a switched-off link and a made-up link show a friendly page, never a blank screen or the sign-in wall.

   Run:  HD_BASE=http://127.0.0.1:<port> HD_KEY=<api key> node server/tests/web/design_collab_test.js
         (server/tests/test_v0777_design_collab.py starts the server on a free port with a fresh database)
         DESIGN_SHOTS=<dir> also writes screenshots, light and dark.
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium / no server). Last line = JSON. */
'use strict';
const assert = require('node:assert/strict'), fs = require('fs'), path = require('path');
const BASE = (process.env.HD_BASE || '').replace(/\/+$/, ''), KEY = process.env.HD_KEY || 'itest-key';
const SHOTS = process.env.DESIGN_SHOTS || '';
/* a real 1x1 PNG (the server checks uploads by content) */
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
let checks = 0;
const ok = (cond, what) => { assert.ok(cond, what); checks++; };
const eq = (a, b, what) => { assert.deepEqual(a, b, what); checks++; };

async function rest(method, p, body, raw) {
  const headers = {Authorization: 'Bearer ' + KEY};
  if (body !== undefined && !raw) headers['Content-Type'] = 'application/json';
  if (raw) headers['Content-Type'] = 'image/png';
  const r = await fetch(BASE + '/api/design' + p, {method, headers, body: body === undefined ? undefined : raw ? body : JSON.stringify(body)});
  const text = await r.text();
  let data = null; try { data = JSON.parse(text); } catch (e) { data = text; }
  return {status: r.status, data};
}

async function main() {
  if (!BASE) { console.log('SKIP: HD_BASE is not set (run it through test_v0777_design_collab.py)'); process.exit(77); }
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  try { const r = await fetch(BASE + '/console/design'); if (r.status !== 200) throw new Error('status ' + r.status); } catch (e) { console.log('SKIP: no Hoola Design server at ' + BASE + ' (' + e.message + ')'); process.exit(77); }
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  if (SHOTS) fs.mkdirSync(SHOTS, {recursive: true});
  const errors = [];

  async function newPage(name, signedIn, viewport, scheme) {
    const ctx = await browser.newContext({viewport: viewport || {width: 1440, height: 900}, colorScheme: scheme || 'light'});
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(name + ': ' + e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR|WebSocket/.test(m.text())) errors.push(name + ' console: ' + m.text()); });
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(([key, on]) => {
      if (on) localStorage.setItem('hoola.console.token', key);
      /* every op frame this page ever puts on a socket */
      window.__ops = 0; const send = WebSocket.prototype.send;
      WebSocket.prototype.send = function (d) { if (typeof d === 'string' && (d.indexOf('"t":"ops"') >= 0 || d.slice(0, 3) === '[1,')) window.__ops++; return send.apply(this, arguments); };
    }, [KEY, !!signedIn]);
    return page;
  }
  const live = page => page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0 && HD.collab, null, {timeout: 25000});
  const saved = page => page.waitForFunction(() => HD.net.status === 'live' && HD.net.pending() === 0);
  const settle = page => page.evaluate(() => new Promise(done => { let last = '', same = 0, n = 0; const tick = () => { const v = [HD.render.view.x, HD.render.view.y, HD.render.view.zoom].join(); same = v === last ? same + 1 : 0; last = v; if (same >= 4 || ++n > 120) setTimeout(done, 60); else requestAnimationFrame(tick); }; tick(); }));
  const shot = async (page, name) => { if (SHOTS) { await settle(page); await page.screenshot({path: path.join(SHOTS, name + '.png')}); } };
  const client = (page, wx, wy) => page.evaluate(([x, y]) => { const s = HD.render.worldToScreen(x, y), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; }, [wx, wy]);
  const threads = page => page.evaluate(() => HD.collab.comments.list().map(t => ({id: t.id, text: t.head.text, node: t.head.node, resolved: t.head.resolved, replies: t.replies.map(r => r.text), unread: HD.collab.comments.unread(t.id)})));
  const worldCentre = page => page.evaluate(() => { const c = HD.tools.canvas, w = HD.render.screenToWorld(c.clientWidth / 2, c.clientHeight / 2); return [w[0], w[1], HD.render.view.zoom]; });
  const prop = (page, id, name) => page.evaluate(([i, n]) => HD.store.has(i) ? HD.store.prop(i, n) : '(gone)', [id, name]);
  const toast = (page, re) => page.waitForFunction(src => new RegExp(src).test((document.querySelector('.hd-toast.on') || {}).textContent || ''), re.source);

  try {
    /* ------------------------------------------------------------ a file, two editors */
    const file = (await rest('POST', '/files', {name: 'Diwali poster'})).data;
    ok(file && file.id, 'a file was made');
    const hash = (await rest('POST', '/files/' + file.id + '/assets', PNG, true)).data.hash;
    ok(/^[0-9a-f]{64}$/.test(hash), 'an image was uploaded');
    const A = await newPage('A', true), B = await newPage('B', true);
    await A.goto(BASE + '/console/design#/f/' + file.id); await live(A);
    const ids = await A.evaluate(h => { const S = HD.store, solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}]; let out = {};
      S.tx('seed', () => { out.frame = S.create('FRAME', '0:1', {name: 'Phone', x: 0, y: 0, w: 390, h: 700, fills: solid('#FFFFFF')});
        out.hero = S.create('RECT', out.frame, {name: 'Hero', x: 24, y: 60, w: 342, h: 200, radius: 20, fills: solid('#6E55F0')});
        out.photo = S.create('RECT', out.frame, {name: 'Photo', x: 24, y: 300, w: 160, h: 120, fills: [{type: 'image', hash: h, mode: 'fill', opacity: 1, visible: true}]});
        out.card = S.create('RECT', '0:1', {name: 'Card', x: 480, y: 80, w: 220, h: 140, radius: 12, fills: solid('#D9D9D9')}); });
      HD.render.zoomToFit(undefined, false); return out; }, hash);
    await saved(A);
    await B.goto(BASE + '/console/design#/f/' + file.id); await live(B);
    eq(await prop(B, ids.hero, 'name'), 'Hero', 'the second editor sees the document');

    /* ------------------------------------------------------------ share: the link from the dialog */
    await A.locator('.hd-top .hd-btn', {hasText: 'Share'}).click();
    await A.locator('.hd-co-share').waitFor();
    await A.locator('.hd-co-share .hd-btn.pri', {hasText: 'Create a view-only link'}).click();
    await A.locator('#hd-co-sharelink').waitFor();
    const link = await A.locator('#hd-co-sharelink').inputValue();
    ok(/\/console\/design#\/s\/[A-Za-z0-9_-]{24,}$/.test(link), 'the dialog shows the view-only link: ' + link);
    await shot(A, 'collab-share-light');
    await A.keyboard.press('Escape'); await A.locator('.hd-co-share').waitFor({state: 'detached'});
    const token = link.split('#/s/')[1];

    /* ------------------------------------------------------------ the signed-out visitor */
    const G = await newPage('G', false, {width: 1280, height: 800}, 'dark');
    await G.goto(link); await live(G);
    const g0 = await G.evaluate(h => ({token: localStorage.getItem('hoola.console.token'), role: HD.net.role, share: !!HD.net.share, ro: HD.store.readOnly, at: location.href, name: HD.app.file.name,
      chip: !!Array.from(document.querySelectorAll('.hd-top .hd-chip')).find(e => !e.hidden && /View only/.test(e.textContent)), signin: (document.querySelector('.hd-co-signin') || {}).textContent,
      rectTool: (document.querySelector('.hd-tool[data-tool="rect"]') || {}).disabled, asset: HD.render.assetURL ? HD.render.assetURL(h) : ''}), hash);
    eq([g0.token, g0.role, g0.share, g0.ro, g0.name], [null, 'view', true, true, 'Diwali poster'], 'a visitor with no sign-in gets a live, view-only editor');
    ok(g0.at.indexOf('#/s/' + token) > 0 && g0.chip && g0.signin === 'Sign in to edit' && g0.rectTool === true, 'the visitor sees "View only", a way to sign in, and no drawing tools');
    ok(g0.asset.indexOf('/api/design/shared/' + token + '/assets/' + hash) === 0, 'images are asked from the public route of the link');
    await G.waitForFunction(h => { const im = HD.render.image(h); return !!im && (im.naturalWidth || im.width) > 0; }, hash, {timeout: 10000}); checks++;
    await A.waitForFunction(() => HD.net.users.size === 2); await B.waitForFunction(() => HD.net.users.size === 2);
    eq(await A.evaluate(() => Array.from(HD.net.users.values()).map(u => u.name).sort()), ['Guest', await A.evaluate(() => HD.net.me.name)].sort(), 'the editors see the visitor as Guest');
    const overlap = await G.evaluate(() => { const cut = (a, b) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
      const tb = document.querySelector('.hd-toolbar').getBoundingClientRect(), bad = []; for (const el of document.querySelectorAll('.hd-top-r > *')) { const r = el.getBoundingClientRect(); if (r.width && (cut(r, tb) || r.right > innerWidth + 0.5)) bad.push(el.className); } return bad; });
    eq(overlap, [], 'nothing in the visitor’s top bar overlaps the tools at 1280');

    /* ------------------------------------------------------------ comments: live for all three */
    const evil = 'Make the hero taller <img src=x onerror="window.__xss=1"> please';
    await A.locator('.hd-canvas').focus(); await A.keyboard.press('c');
    let p = await client(A, 124, 160); await A.mouse.click(p[0], p[1]);
    await A.waitForFunction(() => document.activeElement && document.activeElement.classList.contains('hd-co-ta'));
    await A.keyboard.type(evil); await A.keyboard.press('Control+Enter');
    for (const page of [A, B, G]) await page.waitForFunction(() => HD.collab.comments.list().length === 1);
    const t1 = (await threads(A))[0];
    eq([t1.text, t1.node, t1.resolved, t1.unread], [evil, ids.hero, false, false], 'the comment is anchored to the layer it was dropped on, and is not "new" to its writer');
    eq((await threads(B))[0].unread, true, 'the other editor sees it as new'); eq((await threads(G))[0].unread, true, 'so does the visitor');
    await A.keyboard.press('Escape');

    /* the pin follows its layer */
    const pinB0 = await B.evaluate(id => HD.collab.comments.pin(id), t1.id);
    await A.evaluate(id => HD.store.set(id, {x: 74}), ids.hero); await saved(A);
    await B.waitForFunction(id => HD.store.prop(id, 'x') === 74, ids.hero);
    const pinB1 = await B.evaluate(id => { HD.render.flush(); return HD.collab.comments.pin(id); }, t1.id), zB = await B.evaluate(() => HD.render.view.zoom);
    ok(Math.abs((pinB1.x - pinB0.x) - 50 * zB) < 1.5 && Math.abs(pinB1.y - pinB0.y) < 1.5, 'the pin moved with its layer: ' + JSON.stringify([pinB0, pinB1, zB]));

    /* B opens the thread by its pin and replies */
    await B.locator('.hd-tab', {hasText: 'Comments'}).click();
    await B.locator('.hd-co-row.unread').waitFor(); checks++;
    await B.mouse.click(pinB1.x, pinB1.y);
    await B.locator('.hd-co-thread .hd-co-msg').first().waitFor();
    eq(await B.evaluate(() => ({text: document.querySelector('.hd-co-thread .hd-co-text').textContent, img: document.querySelectorAll('.hd-co-thread img, .hd-co-list img').length, xss: window.__xss || 0})), {text: evil, img: 0, xss: 0}, 'a comment is shown as plain text, never as HTML');
    eq((await threads(B))[0].unread, false, 'opening the thread marks it read');
    await B.waitForFunction(() => document.activeElement && document.activeElement.classList.contains('hd-co-ta'));
    await B.keyboard.type('On it @'); await B.locator('.hd-co-ats .hd-co-atb').first().waitFor();
    await B.keyboard.press('Enter'); await B.keyboard.type('thanks'); await B.keyboard.press('Control+Enter');
    for (const page of [A, B, G]) await page.waitForFunction(() => HD.collab.comments.list()[0].replies.length === 1);
    const reply = (await threads(A))[0].replies[0];
    ok(/^On it @\S.* thanks$/.test(reply), 'the reply carries the picked @mention as plain text: ' + reply);
    await B.waitForFunction(() => document.querySelectorAll('.hd-co-thread .hd-co-msg').length === 2 && !!document.querySelector('.hd-co-thread .hd-co-at')); checks++;
    await shot(B, 'collab-thread-light');

    /* the visitor reads it, and can write nothing */
    await G.locator('.hd-tab', {hasText: 'Comments'}).click(); await G.locator('.hd-co-row').first().click();
    await G.locator('.hd-co-thread .hd-co-msg').nth(1).waitFor();
    eq(await G.evaluate(() => ({ta: document.querySelectorAll('.hd-co-thread textarea').length, more: document.querySelectorAll('.hd-co-thread .hd-co-more').length, note: /Sign in to reply/.test(document.querySelector('.hd-co-ro').textContent), mineTab: Array.from(document.querySelectorAll('.hd-co-filter .hd-segb')).map(b => b.textContent.replace(/ \d+$/, ''))})),
      {ta: 0, more: 0, note: true, mineTab: ['Open', 'Resolved']}, 'the visitor reads the thread; no reply box, no edit, no resolve');
    await shot(G, 'collab-guest-dark');
    await G.keyboard.press('Escape');
    await G.locator('.hd-canvas').focus(); await G.keyboard.press('c'); p = await client(G, 600, 150); await G.mouse.click(p[0], p[1]); await toast(G, /read only on a shared link/); checks++;
    eq(await G.evaluate(async id => { const r = await fetch('/api/design/files/' + id + '/comments', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: 'x', x: 1, y: 1})}); return [r.status, location.hash.slice(0, 4)]; }, file.id), [403, '#/s/'], 'a write from the visitor’s page is answered 403 in the page and never sends them to the sign-in wall');
    eq((await fetch(BASE + '/api/design/files/' + file.id + '/comments', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: 'x', x: 1, y: 1})})).status, 401, 'and the server itself refuses a comment with no sign-in');
    eq((await (await fetch(BASE + '/api/design/shared/' + token + '/comments')).json()).comments.length, 2, 'the link reads the comments');

    /* forged ops from the visitor: refused by the server */
    const forged = await G.evaluate(([tk, hero]) => new Promise(done => { const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/api/design/ws?share=' + encodeURIComponent(tk), ['hoola']); const out = {};
      ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.t === 'init') { out.role = m.file.role; ws.send(JSON.stringify({t: 'ops', n: 1, ops: [{id: hero, p: {name: 'Hacked'}}, {id: hero, del: 1}]})); } if (m.t === 'ack') { out.rejected = m.rejected; ws.close(); done(out); } };
      ws.onerror = () => done({error: true}); setTimeout(() => done(out), 5000); }), [token, ids.hero]);
    eq(forged, {role: 'view', rejected: [0, 1]}, 'ops forged on a share socket are all refused');
    eq((await rest('GET', '/files/' + file.id + '/doc')).data.doc.nodes[ids.hero].name, 'Hero', 'and the document is untouched');
    eq(await G.evaluate(id => { HD.store.set(id, {name: 'Nope'}); return HD.store.prop(id, 'name'); }, ids.hero), 'Hero', 'the visitor’s own store is locked too');

    /* resolve -> everyone; edit; reopen */
    await B.locator('.hd-co-thead .hd-ib[aria-label="Mark as resolved"]').click();
    for (const page of [A, B, G]) await page.waitForFunction(() => HD.collab.comments.list()[0].head.resolved === true); checks++;
    await G.locator('.hd-co-filter .hd-segb', {hasText: 'Resolved'}).click(); await G.locator('.hd-co-row').waitFor(); checks++;
    await B.keyboard.press('Escape'); await B.locator('.hd-co-filter .hd-segb', {hasText: 'Resolved'}).click(); await B.locator('.hd-co-row').click();
    await B.locator('.hd-co-thead .hd-ib[aria-label="Reopen this thread"]').click();
    for (const page of [A, G]) await page.waitForFunction(() => HD.collab.comments.list()[0].head.resolved === false); checks++;
    await B.keyboard.press('Escape'); await B.locator('.hd-co-filter .hd-segb', {hasText: 'Open'}).click();
    /* pins: hidden with Shift+C, back again */
    await A.locator('.hd-canvas').focus(); await A.keyboard.press('Escape');
    ok(await A.evaluate(() => { HD.render.flush(); return HD.collab.comments.hits().length === 1; }), 'one pin is drawn');
    await A.keyboard.press('Shift+C'); ok(await A.evaluate(() => { HD.render.flush(); return HD.collab.comments.hidden && HD.collab.comments.hits().length === 0; }), 'Shift+C hides the pins');
    await A.keyboard.press('Shift+C'); ok(await A.evaluate(() => { HD.render.flush(); return !HD.collab.comments.hidden && HD.collab.comments.hits().length === 1; }), 'and shows them again');
    /* two pins that touch become one counted pin when zoomed out */
    const second = (await rest('POST', '/files/' + file.id + '/comments', {text: 'Second', x: 130, y: 166, page: '0:1'})).data;
    await A.waitForFunction(() => HD.collab.comments.list().length === 2);
    eq(await A.evaluate(() => { HD.render.setView(HD.tools.view.at(0.2, 200, 300, 400, 300), false); HD.render.flush(); return HD.collab.comments.hits().map(q => q.ids.length); }), [2], 'pins that touch are drawn as one pin with a count');
    eq(await A.evaluate(() => { HD.render.setView(HD.tools.view.at(4, 130, 166, 400, 300), false); HD.render.flush(); return HD.collab.comments.hits().map(q => q.ids.length).sort(); }), [1, 1], 'and apart again when zoomed in');
    eq((await rest('DELETE', '/comments/' + second.id)).status, 200, 'delete'); await A.waitForFunction(() => HD.collab.comments.list().length === 1);
    await A.evaluate(() => HD.render.zoomToFit(undefined, false));

    /* ------------------------------------------------------------ versions: save -> edit -> preview -> back -> restore */
    await A.locator('.hd-canvas').focus(); await A.keyboard.press('Control+Alt+h');
    await A.locator('.hd-co-vact .hd-btn').click();
    await A.locator('.hd-co-vform input').fill('Before the client call'); await A.locator('.hd-co-vform textarea').fill('Hero in violet');
    await A.locator('.hd-co-vform .hd-btn.pri').click();
    await A.waitForFunction(() => HD.collab.versions.list().length === 1);
    const v1 = (await rest('GET', '/files/' + file.id + '/versions')).data.versions[0];
    eq([v1.label, v1.note, v1.auto, !!v1.by], ['Before the client call', 'Hero in violet', false, true], 'a named version with a note and who made it');
    await A.evaluate(id => HD.store.set(id, {name: 'Hero v2', w: 300}), ids.hero); await saved(A);
    await B.waitForFunction(id => HD.store.prop(id, 'name') === 'Hero v2', ids.hero);

    const opsA = await A.evaluate(() => window.__ops), seqBefore = (await rest('GET', '/files/' + file.id + '/doc')).data.seq;
    await A.locator('.hd-co-vrow[data-id="' + v1.id + '"]').click();
    await A.waitForFunction(() => HD.collab.versions.current && HD.net.held);
    eq(await A.evaluate(id => [HD.store.prop(id, 'name'), HD.store.prop(id, 'w'), HD.store.readOnly, !!document.querySelector('.hd-co-vbar'), /Before the client call/.test(document.querySelector('.hd-co-vbar').textContent)], ids.hero), ['Hero', 342, true, true, true], 'the old version is on screen, read only, under a banner that names it');
    await shot(A, 'collab-preview-light');
    /* trying to edit the preview changes nothing and sends nothing */
    await A.evaluate(id => { HD.store.set(id, {name: 'Edited in preview'}); try { HD.store.tx('x', () => HD.store.create('RECT', '0:1', {name: 'Ghost'})); } catch (e) { /* locked */ } }, ids.hero);
    p = await client(A, 590, 150); await A.mouse.move(p[0], p[1]); await A.mouse.down(); await A.mouse.move(p[0] + 60, p[1] + 40, {steps: 4}); await A.mouse.up();
    await A.locator('.hd-canvas').focus(); await A.keyboard.press('Delete');
    /* meanwhile the other editor keeps working on the live file */
    await B.evaluate(id => HD.store.set(id, {name: 'Hero v3'}), ids.hero); await saved(B);
    await A.waitForTimeout(250);
    eq(await A.evaluate(id => [HD.store.prop(id, 'name'), window.__ops, HD.store.has(id)], ids.hero), ['Hero', opsA, true], 'in the preview: nothing changed, NO op was sent, and the live edits of others do not leak in');
    const liveDoc = (await rest('GET', '/files/' + file.id + '/doc')).data;
    eq([liveDoc.doc.nodes[ids.hero].name, liveDoc.doc.nodes[ids.hero].w, liveDoc.seq, Object.values(liveDoc.doc.nodes).some(n => n.name === 'Ghost'), liveDoc.doc.nodes[ids.card].x], ['Hero v3', 300, seqBefore + 1, false, 480], 'the live document is whole: only the other editor’s change is in it');
    eq(await prop(B, ids.hero, 'name'), 'Hero v3', 'the other editor never saw the preview');
    await A.locator('.hd-co-vbar .hd-btn', {hasText: 'Back to current'}).click();
    await A.waitForFunction(id => !HD.net.held && HD.net.status === 'live' && !HD.store.readOnly && HD.store.prop(id, 'name') === 'Hero v3' && !document.querySelector('.hd-co-vbar'), ids.hero); checks++;
    eq(await A.evaluate(() => window.__ops), opsA, 'coming back sent nothing either');
    await A.evaluate(id => HD.store.set(id, {h: 210}), ids.hero); await saved(A); await B.waitForFunction(id => HD.store.prop(id, 'h') === 210, ids.hero); checks++;

    /* duplicate the version as a new file */
    await A.locator('.hd-co-vrow[data-id="' + v1.id + '"]').click(); await A.waitForFunction(() => HD.collab.versions.current && HD.net.held);
    await A.locator('.hd-co-vbar .hd-btn', {hasText: 'Duplicate as new file'}).click();
    await A.locator('.hd-co-dialog a.hd-btn').waitFor(); await A.keyboard.press('Escape');
    const all = (await rest('GET', '/files')).data.files, copy = all.find(f => f.id !== file.id && /Before the client call/.test(f.name));
    ok(copy, 'a new file was made from the version: ' + all.map(f => f.name).join(' | '));
    const copyDoc = (await rest('GET', '/files/' + copy.id + '/doc')).data.doc.nodes;
    eq([copyDoc[ids.hero].name, copyDoc[ids.hero].w], ['Hero', 342], 'the new file holds the version, not the live document');
    eq((await rest('GET', '/files/' + file.id + '/doc')).data.doc.nodes[ids.hero].name, 'Hero v3', 'and the original file was not touched');

    /* restore: both editors (and the visitor) reload to it; the view stays where it was */
    await B.evaluate(() => { HD.tools.view.zoomTo(1.7, false); HD.tools.view.panBy(-120, 60); }); await settle(B);
    const viewB = await B.evaluate(() => [HD.render.view.x, HD.render.view.y, HD.render.view.zoom]);
    await A.locator('.hd-co-vbar .hd-btn', {hasText: 'Restore'}).click();
    await A.locator('.hd-co-dialog .hd-btn.pri', {hasText: 'Restore'}).click();
    for (const page of [A, B, G]) await page.waitForFunction(id => HD.net.status === 'live' && !HD.net.held && HD.store.prop(id, 'name') === 'Hero' && HD.store.prop(id, 'w') === 342, ids.hero, {timeout: 15000});
    checks++;
    eq(await B.evaluate(() => [HD.render.view.x, HD.render.view.y, HD.render.view.zoom]), viewB, 'the other editor’s view did not jump');
    await toast(B, /restored to an earlier version/); checks++;
    eq(await A.evaluate(() => [HD.store.readOnly, !!document.querySelector('.hd-co-vbar')]), [false, false], 'the editor who restored is editing the live file again');
    await A.waitForFunction(() => HD.collab.versions.list().some(v => v.label === 'Before restore')); checks++;
    await A.evaluate(id => HD.store.set(id, {name: 'After restore'}), ids.hero); await saved(A);
    await B.waitForFunction(id => HD.store.prop(id, 'name') === 'After restore', ids.hero); await G.waitForFunction(id => HD.store.prop(id, 'name') === 'After restore', ids.hero); checks++;
    eq(await threads(B).then(t => t.length), 1, 'the comments are still there after the reload');
    await A.locator('.hd-co-phead .hd-ib[aria-label="Close the history"]').click();
    await A.waitForFunction(() => HD.ui.state.leftTab !== 'versions'); checks++;

    /* ------------------------------------------------------------ follow, spotlight, cursor chat */
    for (const page of [A, B]) await page.waitForFunction(() => HD.net.users.size === 2);
    await A.evaluate(() => HD.render.zoomToFit(undefined, false)); await B.evaluate(() => HD.render.zoomToFit(undefined, false));
    const cidA = await A.evaluate(() => HD.net.cid);
    await A.mouse.move(700, 420); await A.mouse.move(705, 424);
    await B.waitForFunction(c => { const u = HD.net.users.get(c), x = HD.net.extra.get(c); return u && Array.isArray(u.vp) && x && Array.isArray(x.vs); }, cidA);
    const mine = await B.evaluate(c => Array.from(document.querySelectorAll('.hd-people button.hd-person')).map(b => b.dataset.cid).indexOf(String(c)), cidA);
    ok(mine >= 0, 'the other editor is in the avatar stack');
    await B.locator('.hd-people button.hd-person').nth(mine).click();
    await B.locator('.hd-co-follow').waitFor();
    eq(await B.evaluate(() => [HD.collab.following !== null, /^Following /.test(document.querySelector('.hd-co-fname').textContent)]), [true, true], 'clicking a person follows them, and says so');
    await A.evaluate(() => { HD.tools.view.zoomTo(2.4, false); HD.tools.view.panBy(-260, -140); }); await A.mouse.move(640, 400); await A.mouse.move(644, 404);
    const wantC = await worldCentre(A);
    await B.waitForFunction(w => { const c = HD.tools.canvas, p = HD.render.screenToWorld(c.clientWidth / 2, c.clientHeight / 2); return Math.abs(p[0] - w[0]) < 2 && Math.abs(p[1] - w[1]) < 2; }, wantC, {timeout: 8000});
    const gotC = await worldCentre(B);
    ok(Math.abs(gotC[2] - wantC[2]) < 0.05, 'the follower shows the same place at the same zoom: ' + JSON.stringify([wantC, gotC]));
    await shot(B, 'collab-follow-light');
    /* cursor chat, seen by the follower */
    await A.locator('.hd-canvas').focus(); await A.keyboard.press('/'); await A.locator('.hd-co-chatin').waitFor(); await A.keyboard.type('Look at this corner');
    await B.waitForFunction(c => (HD.net.extra.get(c) || {}).chat === 'Look at this corner', cidA); checks++;
    await A.keyboard.press('Enter');
    /* any pan of one's own stops following */
    p = await client(B, wantC[0], wantC[1]); await B.mouse.move(p[0], p[1]); await B.mouse.wheel(0, 120);
    await B.waitForFunction(() => HD.collab.following === null && !document.querySelector('.hd-co-follow')); checks++;
    /* spotlight: the others are asked, one tap follows */
    await A.evaluate(() => HD.collab.spotlight());
    await B.locator('.hd-co-spot').waitFor(); await G.locator('.hd-co-spot').waitFor();
    await G.locator('.hd-co-spot .hd-btn.pri').click();
    await G.waitForFunction(() => HD.collab.following !== null && !!document.querySelector('.hd-co-follow') && !document.querySelector('.hd-co-spot')); checks++;
    await A.evaluate(() => { HD.tools.view.panBy(90, 30); }); await A.mouse.move(600, 380); const wantG = await worldCentre(A);
    await G.waitForFunction(w => { const c = HD.tools.canvas, p = HD.render.screenToWorld(c.clientWidth / 2, c.clientHeight / 2); return Math.abs(p[0] - w[0]) < 2 && Math.abs(p[1] - w[1]) < 2; }, wantG, {timeout: 8000}); checks++;
    await shot(G, 'collab-guest-follow-dark');
    await G.locator('.hd-co-fchip').click(); await G.waitForFunction(() => HD.collab.following === null); checks++;
    await A.waitForFunction(() => !document.querySelector('.hd-co-chat'), null, {timeout: 9000}); checks++;       /* the chat bubble goes after 5 s */
    await B.waitForFunction(c => !(HD.net.extra.get(c) || {}).chat, cidA); checks++;

    /* someone quiet for a minute is dimmed in the avatar stack, and comes back with their next move */
    await B.evaluate(c => { HD.net.extra.get(c).at = Date.now() - 61000; }, cidA);
    await B.waitForFunction(c => { const b = document.querySelector('.hd-people button.hd-person[data-cid="' + c + '"]'); return b && b.classList.contains('hd-co-idle') && /away/.test(b.title); }, cidA, {timeout: 13000}); checks++;
    await A.mouse.move(610, 390); await A.mouse.move(620, 396);
    await B.waitForFunction(c => { const b = document.querySelector('.hd-people button.hd-person[data-cid="' + c + '"]'); return b && !b.classList.contains('hd-co-idle'); }, cidA); checks++;

    /* ------------------------------------------------------------ a link to one layer */
    const C = await newPage('C', true);
    await C.goto(BASE + '/console/design#/f/' + file.id + '?node=' + encodeURIComponent(ids.card)); await live(C);
    await C.waitForFunction(id => HD.sel.ids.length === 1 && HD.sel.ids[0] === id, ids.card); await settle(C);
    const cb = await C.evaluate(id => { const b = HD.store.worldBounds(id), c = HD.tools.canvas, a = HD.render.worldToScreen(b.x, b.y), z = HD.render.worldToScreen(b.x + b.w, b.y + b.h); return a[0] >= 0 && a[1] >= 0 && z[0] <= c.clientWidth && z[1] <= c.clientHeight; }, ids.card);
    ok(cb, '"?node=" selects that layer and brings it into view');
    eq(await C.evaluate(id => HD.app.link(id), ids.card), BASE + '/console/design#/f/' + file.id + '?node=' + encodeURIComponent(ids.card), 'the link the Share dialog copies for a layer');
    await C.context().close();
    /* the same through the view-only link, signed out */
    const H = await newPage('H', false, {width: 1280, height: 800});
    await H.goto(link + '?node=' + encodeURIComponent(ids.card)); await live(H);
    await H.waitForFunction(id => HD.sel.ids.length === 1 && HD.sel.ids[0] === id, ids.card); checks++;
    await shot(H, 'collab-guest-light');

    /* ------------------------------------------------------------ dark editor shots, then the link is switched off */
    if (SHOTS) { await A.emulateMedia({colorScheme: 'dark'}); await A.evaluate(() => window.HoolaTheme && window.HoolaTheme.setTheme('dark')); await A.locator('.hd-tab', {hasText: 'Comments'}).click();
      await A.evaluate(() => { HD.render.zoomToFit(undefined, false); HD.collab.comments.jump(HD.collab.comments.list()[0].id); }); await A.locator('.hd-co-thread').waitFor(); await shot(A, 'collab-thread-dark');
      await A.keyboard.press('Escape'); await A.locator('.hd-canvas').focus(); await A.keyboard.press('Control+Alt+h'); await A.locator('.hd-co-vrow[data-id="' + v1.id + '"]').click(); await A.waitForFunction(() => HD.collab.versions.current); await shot(A, 'collab-preview-dark');
      await A.locator('.hd-co-vbar .hd-btn', {hasText: 'Back to current'}).click(); await A.waitForFunction(() => !HD.net.held && !HD.store.readOnly); }
    await A.locator('.hd-top .hd-btn', {hasText: 'Share'}).click(); await A.locator('#hd-co-sharelink').waitFor();
    if (SHOTS) await shot(A, 'collab-share-dark');
    await A.locator('.hd-co-share .hd-btn.danger').click();
    await A.locator('.hd-co-share .hd-btn.pri', {hasText: 'Create a view-only link'}).waitFor(); await A.keyboard.press('Escape');
    for (const page of [G, H]) { await page.locator('.hd-co-gone').waitFor({timeout: 10000}); ok(/switched off/.test(await page.locator('.hd-co-gone h2').textContent()) && /#\/s\//.test(page.url()), 'the visitor is told the link was switched off, on the same page'); }
    await shot(G, 'collab-link-off-dark');
    await A.waitForFunction(() => HD.net.users.size === 1 && HD.net.status === 'live'); checks++;                   /* the editors stay */
    eq((await fetch(BASE + '/api/design/shared/' + token + '/doc')).status, 404, 'the old link opens nothing');
    eq((await fetch(BASE + '/api/design/shared/' + token + '/comments')).status, 404, 'nor its comments');
    for (const bad of [link, BASE + '/console/design#/s/not-a-real-link']) {
      const X = await newPage('X', false, {width: 1280, height: 800});
      await X.goto(bad); await X.locator('.hd-co-gone').waitFor({timeout: 10000});
      const x = await X.evaluate(() => ({h: document.querySelector('.hd-co-gone h2').textContent, p: document.querySelector('.hd-co-gone p').textContent.length > 20, a: document.querySelector('.hd-co-gone a.hd-btn').getAttribute('href'), at: location.pathname + location.hash.slice(0, 4)}));
      eq(x, {h: 'This link is not active', p: true, a: '/console/', at: '/console/design#/s/'}, 'a dead link shows a friendly page, not a blank screen and not the sign-in wall');
      if (bad !== link) await shot(X, 'collab-link-bad-light');
      await X.context().close();
    }
    eq(errors, [], 'no script error in any of the browsers');
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ok: true, checks: checks}));
}

main().catch(e => { console.error(e && e.stack ? e.stack : e); process.exit(1); });
