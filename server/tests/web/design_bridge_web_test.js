/* HOOLA DESIGN - browser walk of D7 bridge B, Send to Web Studio (hd-bridge-web.js), in the REAL editor with the
   mock server of design_ui_test.js. The bridge's routes (/api/design/files/<id>/to-site, .../to-site/preview) and Web
   Studio's site list (/api/sites, /api/sites/<id>) are answered in the page by a small fake (page.route).
   Run:  node server/tests/web/design_bridge_web_test.js     (DESIGN_SHOTS=<dir> also writes screenshots)
   It selects a frame, opens the dialog from the Design panel, previews the HTML (read only, server text stays TEXT),
   sends a new site, then adds the frame to a page of a built site (an unbuilt one is not offered), and checks the
   result links to Web Studio and lists the warnings. Exit 0 = pass, 77 = no browser here. */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const {startMock, newDoc} = require('./design_ui_test.js');

function seed() {
  const doc = newDoc();
  Object.assign(doc.nodes, {
    '9:1': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Hero', x: 0, y: 0, w: 1440, h: 600, fills: [{type: 'solid', color: '#1E1B4B'}],
      layout: {mode: 'v', gap: 16, pad: [64, 64, 64, 64], alignMain: 'start', alignCross: 'start'}},
    '9:2': {type: 'TEXT', parent: '9:1', idx: 'a0', name: 'Title', chars: 'Fresh sweets', fontSize: 64, fontWeight: 700, fills: [{type: 'solid', color: '#FFFFFF'}]},
    '9:3': {type: 'RECT', parent: '0:1', idx: 'a1', name: 'Not a frame', x: 1600, y: 0, w: 100, h: 100}
  });
  return doc;
}

async function walk() {
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  const mock = await startMock(seed());
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { await mock.close(); console.log('SKIP: Chromium can not start here: ' + String(e.message || e).split('\n')[0]); process.exit(77); }
  const errors = [], seen = {sends: [], previews: []};
  const page = await browser.newPage({viewport: {width: 1440, height: 900}});
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
  await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
  await page.addInitScript(() => localStorage.setItem('hoola.console.token', 'fixture-only'));
  const json = (r, o, code) => r.fulfill({status: code || 200, contentType: 'application/json', body: JSON.stringify(o)});
  await page.route(/\/api\/design\/files\/f1\/to-site\/preview$/, (r, req) => { seen.previews.push(JSON.parse(req.postData() || '{}'));
    return json(r, {html: '<section class="d-hero">\n<div class="d-hero-box">\n<h1 class="d-title">Fresh sweets</h1>\n</div>\n</section>\n', css: '.d-title {\n  font-size:64px;\n}\n',
      fonts: [{family: 'Inter', shipped: true}], images: [], warnings: ['<img src=x onerror="window.__pwned=1"> blend is not reproduced.']}); });
  await page.route(/\/api\/design\/files\/f1\/to-site$/, (r, req) => { const b = JSON.parse(req.postData() || '{}'); seen.sends.push(b);
    if (b.mode === 'section' && b.site !== 'site_built') return json(r, {detail: 'This website is not built yet.'}, 409);
    return json(r, {ok: true, site: b.mode === 'new' ? 'site_new' : 'site_built', number: b.mode === 'new' ? 'S-0002' : 'S-0001', name: b.name || 'Sharma Sweets',
      page: b.page || 'home', url: '/console/web#/site/' + (b.mode === 'new' ? 'site_new' : 'site_built'), images: 0, removed: [],
      warnings: ['Blend modes are not reproduced on the website: Glow.'], say: 'Sent. Nothing is published until you go live there.'}); });
  await page.route(/\/api\/sites$/, r => json(r, {sites: [{id: 'site_plan', number: 'S-0003', name: 'Gym plan', status: 'planned'}, {id: 'site_built', number: 'S-0001', name: 'Sharma Sweets', status: 'ready'}]}));
  await page.route(/\/api\/sites\/site_built$/, r => json(r, {id: 'site_built', plan: {pages: [{slug: 'home', title: 'Home', sections: []}, {slug: 'contact', title: 'Contact', sections: []}, {slug: 'privacy', title: 'Privacy', sections: []}]}}));
  const base = 'http://127.0.0.1:' + mock.port + '/console/design';
  const shot = async name => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };

  await page.goto(base + '#/f/f1');
  await page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.has('9:1') && HD.bridgeWeb, null, {timeout: 20000});
  /* a non-frame selection offers nothing; a frame shows the button in the Design panel and in the palette */
  await page.evaluate(() => HD.sel.set(['9:3'])); await page.waitForTimeout(150);
  assert.equal(await page.locator('.hdw-sec').count(), 0);
  await page.evaluate(() => HD.sel.set(['9:1']));
  await page.waitForSelector('.hdw-sec .hdw-wide', {timeout: 5000});
  await page.click('.hdw-sec .hdw-wide');
  await page.waitForSelector('.hdw-dialog');
  assert.equal(await page.locator('.hdw-dialog input[aria-label="Website name"]').inputValue(), 'Hero');
  /* Preview HTML: read only, the server's words are text */
  await page.click('.hdw-tog');
  await page.waitForSelector('.hdw-pre');
  const pre = await page.locator('.hdw-pre').first().textContent();
  assert.match(pre, /<h1 class="d-title">Fresh sweets<\/h1>/);
  assert.match(await page.locator('.hdw-warn').textContent(), /<img src=x onerror/);
  assert.equal(await page.evaluate(() => document.querySelectorAll('.hdw-dialog img').length), 0);
  assert.equal(await page.evaluate(() => window.__pwned), undefined);
  assert.deepEqual(seen.previews[0], {node: '9:1', mode: 'new'});
  await shot('toweb-preview');
  /* a new website */
  await page.fill('.hdw-dialog input[aria-label="Website name"]', 'Sharma Sweets');
  await page.fill('.hdw-dialog input[aria-label="What the website is for"]', 'a sweet shop');
  await page.click('.hdw-send');
  await page.waitForSelector('.hdw-dialog a.hd-btn.pri');
  assert.deepEqual(seen.sends[0], {node: '9:1', mode: 'new', name: 'Sharma Sweets', brief: 'a sweet shop'});
  assert.equal(await page.locator('.hdw-dialog a.hd-btn.pri').getAttribute('href'), '/console/web#/site/site_new');
  assert.match(await page.locator('.hdw-dialog').textContent(), /Blend modes are not reproduced/);
  await shot('toweb-sent');
  await page.click('.hdw-dialog .hd-btn:not(.pri)');
  /* add to a built site: the planned one is not offered, the legal page is not offered */
  await page.evaluate(() => HD.ui.run('sendToWeb'));
  await page.waitForSelector('.hdw-dialog');
  await page.click('.hdw-seg .hd-segb:nth-child(2)');
  await page.waitForSelector('.hdw-dialog select[aria-label="Page"] option[value="contact"]', {state: 'attached'});
  const sites = await page.locator('.hdw-dialog select[aria-label="Website"] option').allTextContents();
  assert.deepEqual(sites, ['S-0001 · Sharma Sweets']);
  const pages = await page.locator('.hdw-dialog select[aria-label="Page"] option').evaluateAll(o => o.map(x => x.value));
  assert.deepEqual(pages, ['home', 'contact']);
  await page.selectOption('.hdw-dialog select[aria-label="Page"]', 'contact');
  await page.click('.hdw-send');
  await page.waitForSelector('.hdw-dialog a.hd-btn.pri');
  assert.deepEqual(seen.sends[1], {node: '9:1', mode: 'section', site: 'site_built', page: 'contact'});
  assert.equal(await page.locator('.hdw-dialog a.hd-btn.pri').getAttribute('href'), '/console/web#/site/site_built');
  await shot('toweb-section');
  assert.deepEqual(errors, []);
  await browser.close(); await mock.close();
  console.log('design_bridge_web_test: ok');
}
if (require.main === module) walk().catch(e => { console.error(e); process.exit(1); });
