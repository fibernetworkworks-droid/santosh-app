/* HOOLA DESIGN - D8b (hd-plugins-ai.js + design/gallery.py + design/plugin_starters.py + design/plugin_ai.py) against a
   REAL server, in a real Chromium, through D8a's real plugin runtime:
   - the file browser's Templates tab: every template with its picture, categories, search, Use = a NEW file opened in
     the editor (the text is laid out once with the real fonts, the mark comes off);
   - the Plugins dialog shows "Starter plugins by Hoola": Add -> D8a's review dialog -> Install -> it runs (Tidy into a
     grid puts three messy rectangles on a 24 px grid, in one undo step);
   - Ask Hoola to make a plugin: the draft (the route is answered in the page with a draft the server's check made) opens
     in D8a's review; Cancel brings her back to her idea and the draft; Review and install -> installed;
   - Save as a template: her file appears under My templates, only for her.
   Run:  HD_BASE=http://127.0.0.1:<port> HD_KEY=<api key> HD_DRAFT=<json> node server/tests/web/design_plugins_ai_test.js
         (server/tests/test_v0825_design_plugin_ai.py starts the server). DESIGN_SHOTS=<dir> also writes a screenshot of
         the gallery and of every template open in the editor.
   Exit 0 = pass, 1 = fail, 77 = could not run here. Last line = JSON. */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const BASE = (process.env.HD_BASE || '').replace(/\/+$/, ''), KEY = process.env.HD_KEY || 'itest-key';
let checks = 0;
const ok = (cond, what) => { assert.ok(cond, what); checks++; };
const eq = (a, b, what) => { assert.deepEqual(a, b, what); checks++; };

async function rest(method, p, body) {
  const headers = {Authorization: 'Bearer ' + KEY};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const r = await fetch(BASE + '/api/design' + p, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  const text = await r.text();
  let data = null; try { data = JSON.parse(text); } catch (e) { data = text; }
  return {status: r.status, data};
}

async function main() {
  if (!BASE) { console.log('SKIP: HD_BASE is not set (run it through test_v0825_design_plugin_ai.py)'); process.exit(77); }
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  const shot = async (page, name) => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };
  const errors = [];
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 900}});
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
    await page.addInitScript(key => { if (window.top === window) localStorage.setItem('hoola.console.token', key); }, KEY);
    const draft = process.env.HD_DRAFT ? JSON.parse(process.env.HD_DRAFT) : null;
    const asked = [];
    await page.route(/\/api\/design\/plugins\/draft$/, (r, req) => { asked.push(JSON.parse(req.postData() || '{}'));
      return r.fulfill({status: draft ? 200 : 503, contentType: 'application/json', body: JSON.stringify(draft || {detail: 'No AI model is configured on this server.'})}); });
    const toast = re => page.waitForFunction(src => new RegExp(src).test((document.querySelector('.hd-toast.on') || {}).textContent || ''), re.source, {timeout: 15000});
    const total = (await rest('GET', '/templates')).data.templates.length;
    ok(total >= 16, 'the server lists the built-in templates');

    /* ------------------------------------------------------------ the Templates tab */
    await page.goto(BASE + '/console/design#/');
    await page.locator('.hd-hbar .hd-segb[data-v="templates"]').click();
    await page.waitForFunction(n => document.querySelectorAll('.hdg-card').length === n, total, {timeout: 20000});
    eq(await page.locator('.hd-hbar h1').textContent(), 'Templates', 'the page says where she is');
    ok(await page.locator('.hd-hbar .hd-segb[data-v="templates"]').getAttribute('aria-selected') === 'true', 'the tab is on');
    ok(!(await page.locator('.hd-newcard').isVisible().catch(() => false)), 'her files are hidden while templates show');
    await page.waitForFunction(n => Array.from(document.querySelectorAll('.hdg-thumb img')).filter(i => i.complete && i.naturalWidth > 0).length === n, total, {timeout: 30000});
    ok(true, 'every template has its picture');
    await shot(page, 'gallery');
    await page.locator('.hdg-cat', {hasText: 'Festivals'}).click();
    await page.waitForFunction(() => document.querySelectorAll('.hdg-card').length === 4);
    eq(await page.locator('.hdg-card .hdg-name').allTextContents(), ['Diwali greetings poster', 'Eid Mubarak poster', 'Christmas poster', 'Holi Instagram post'], 'the Festivals category');
    await page.locator('.hdg-cat', {hasText: 'All'}).click();
    await page.locator('.hd-hsearch input').fill('wedding');
    await page.waitForFunction(() => document.querySelectorAll('.hdg-card').length === 1);
    eq(await page.locator('.hdg-card .hdg-name').textContent(), 'Wedding invitation (Hindi + English)', 'search finds a template by its words');
    await page.locator('.hd-hsearch input').fill('');
    await page.waitForFunction(n => document.querySelectorAll('.hdg-card').length === n, total);
    const filesBefore = (await rest('GET', '/files')).data.files.length;
    await page.locator('.hdg-card[data-template="diwali-poster"] .hdg-use').click();
    await page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0, null, {timeout: 25000});
    eq((await rest('GET', '/files')).data.files.length, filesBefore + 1, 'Use made one NEW file');
    ok(/^#\/f\//.test(await page.evaluate(() => location.hash)), 'and opened it');
    eq(await page.evaluate(() => HD.app.file.name), 'Diwali greetings poster', 'named after the template');
    await page.waitForFunction(() => { const p = HD.sel.page, k = HD.store.children(p)[0]; return k && HD.store.get(k).aiSettle === undefined; }, null, {timeout: 20000});
    ok(true, 'the editor laid the text out with the real fonts once and took the mark off');
    const texts = await page.evaluate(() => { const out = []; HD.store.walk(HD.sel.page, (id, n) => { if (n.type === 'TEXT') out.push(n.chars); }); return out; });
    ok(texts.indexOf('शुभ दीपावली') >= 0 && texts.some(t => /\[phone number\]/.test(t)), 'her words in Hindi and the marked blanks');
    await page.evaluate(() => HD.render.zoomToFit(undefined, false));
    await shot(page, 'editor-diwali');

    /* ------------------------------------------------------------ a starter plugin: Add -> review -> Install -> run */
    await page.evaluate(() => HD.plugins.open());
    await page.waitForFunction(() => document.querySelectorAll('.hdp-manager .hdpa-starter').length === 8, null, {timeout: 15000});
    const names = await page.locator('.hdpa-starter strong').allTextContents();
    eq(names.length, 8, 'eight starter plugins in the Plugins dialog');
    ok(names.indexOf('Contrast checker') >= 0 && names.indexOf('Indian numbers and ₹') >= 0, 'the starters by name');
    await shot(page, 'plugins-manager');
    await page.locator('.hdpa-starter[data-starter="hoola.tidy-grid"] .hd-btn').click();
    await page.locator('.hdp-review').waitFor();
    const review = await page.locator('.hdp-review').innerText();
    ok(/Tidy into a grid/.test(review) && /Read your design/.test(review) && /Change your design/.test(review), 'D8a review: name and permissions in plain words');
    ok(review.indexOf('GAP = 24') >= 0, 'and the code itself');
    await shot(page, 'review-starter');
    await page.locator('.hdp-review .hd-btn.pri', {hasText: 'Install'}).click();
    await page.waitForFunction(() => document.querySelector('.hdp-manager .hdpa-starter[data-starter="hoola.tidy-grid"] .hd-btn') &&
      document.querySelector('.hdp-manager .hdpa-starter[data-starter="hoola.tidy-grid"] .hd-btn').textContent === 'Added', null, {timeout: 15000});
    ok(true, 'after Install the starter says Added');
    await page.evaluate(() => HD.ui.closeModal());
    const ids = await page.evaluate(() => {
      const pg = HD.sel.page, out = [];
      HD.store.tx('three boxes', () => { [[1500, 40, 100, 60], [1650, 75, 80, 80], [1530, 210, 120, 40]].forEach((b, i) => out.push(HD.store.create('RECT', pg, {name: 'Box ' + i, x: b[0], y: b[1], w: b[2], h: b[3]}))); });
      HD.sel.set(out); return out;
    });
    await page.waitForFunction(() => HD.net.pending() === 0);
    const res = await page.evaluate(() => HD.plugins.run('hoola.tidy-grid', 'run'));
    ok(res && res.ok, 'the starter ran: ' + JSON.stringify(res));
    const pos = await page.evaluate(list => list.map(id => [HD.store.prop(id, 'x'), HD.store.prop(id, 'y')]), ids);
    eq(pos, [[1500, 40], [1500 + 100 + 24, 40], [1500, 40 + 80 + 24]], 'a 2-column grid, 24 apart, from the top-left of the selection');
    await page.evaluate(() => HD.store.undo());
    eq(await page.evaluate(list => list.map(id => [HD.store.prop(id, 'x'), HD.store.prop(id, 'y')]), ids), [[1500, 40], [1650, 75], [1530, 210]], 'ONE undo puts them back');

    /* ------------------------------------------------------------ Ask Hoola to make a plugin */
    await page.evaluate(() => HD.pluginsAI.ask());
    await page.locator('.hdpa-dialog textarea').fill('Number the selected layers as Step 1, Step 2');
    await shot(page, 'ask-hoola');
    await page.locator('.hdpa-dialog .hd-btn.pri').click();
    await page.locator('.hdp-review').waitFor({timeout: 15000});
    eq(asked, [{prompt: 'Number the selected layers as Step 1, Step 2'}], 'her sentence went to the draft route');
    const rv = await page.locator('.hdp-review').innerText();
    ok(/Step numbers/.test(rv) && /Change your design/.test(rv) && !/Keep a little data/.test(rv), 'the review shows the SMALLEST permissions (storage was taken out)');
    ok((await rest('GET', '/plugins/step-numbers')).status === 404, 'nothing installed by asking');
    await page.locator('.hdp-review .hd-btn', {hasText: 'Cancel'}).click();
    await page.locator('.hdpa-dialog .hdpa-draft').waitFor({timeout: 10000});
    eq(await page.locator('.hdpa-dialog textarea').inputValue(), 'Number the selected layers as Step 1, Step 2', 'Cancel brings her back to her idea');
    await page.locator('.hdpa-draft .hd-btn', {hasText: 'Review and install'}).click();
    await page.locator('.hdp-review .hd-btn.pri', {hasText: 'Install'}).click();
    await toast(/is installed/);
    const got = await rest('GET', '/plugins/step-numbers');
    ok(got.status === 200 && got.data.plugin.approved, 'installed only after HER Install');
    eq(got.data.plugin.manifest.permissions, ['read', 'edit'], 'with the smallest permissions');

    /* ------------------------------------------------------------ Save as a template -> My templates */
    await page.evaluate(() => HD.pluginsAI.saveAsTemplate());
    await page.locator('.hdpa-dialog input').fill('Our Diwali poster');
    await page.locator('.hdpa-dialog .hd-btn.pri').click();
    await toast(/Only you can see it/);
    const mine = (await rest('GET', '/templates')).data.mine;
    eq([mine.length, mine[0] && mine[0].name, mine[0] && mine[0].reviewed], [1, 'Our Diwali poster', false], 'kept as HER template, not reviewed, private');
    await page.goto(BASE + '/console/design#/');
    await page.locator('.hd-hbar .hd-segb[data-v="templates"]').click();
    await page.waitForFunction(() => document.querySelector('.hdg-h2') && document.querySelector('.hdg-h2').textContent === 'My templates', null, {timeout: 15000});
    ok(await page.locator('.hdg-card[data-template^="mine_"]').count() === 1, 'My templates shows it');
    await page.locator('.hd-hbar .hd-segb[data-v="recent"]').click();
    await page.waitForFunction(() => !document.querySelector('.hdg-gallery') && document.querySelector('.hd-card'));
    ok(true, 'back to Recent: the gallery goes, her files come back');

    /* ------------------------------------------------------------ every template open in the real editor (pictures) */
    if (shots) {
      for (const t of (await rest('GET', '/templates')).data.templates) {
        const f = (await rest('POST', '/templates/' + t.id + '/use', {})).data;
        await page.goto(BASE + '/console/design#/f/' + f.id);
        await page.waitForFunction(id => window.HD && HD.app.file && HD.app.file.id === id && HD.ui.mounted && HD.net.status === 'live', f.id, {timeout: 25000});
        await page.waitForFunction(() => { const k = HD.store.children(HD.sel.page)[0]; return k && HD.store.get(k).aiSettle === undefined; }, null, {timeout: 20000}).catch(() => {});
        await page.evaluate(() => { HD.sel.clear(); HD.render.zoomToFit(undefined, false); });
        await page.waitForTimeout(400);
        await shot(page, 'template-' + t.id);
      }
    }
    eq(errors, [], 'no errors on the page');
    console.log(JSON.stringify({ok: true, checks: checks}));
  } finally {
    await browser.close();
  }
}
main().catch(e => { console.error(e && e.stack || e); console.log(JSON.stringify({ok: false, checks: checks, error: String(e && e.message || e)})); process.exit(1); });
