/* HOOLA DESIGN - browser walk of D7 bridge A, Import from Figma (hd-bridge-figma.js), against the REAL editor with the
   mock server of design_ui_test.js. The bridge's own routes (/api/design/figma, /api/design/import/...) are answered
   in the page by a small fake (page.route), so no Figma and no Hoola server is needed.
   Run:  node server/tests/web/design_figma_test.js      (DESIGN_SHOTS=<dir> also writes screenshots)
   It clicks "Import from Figma" in the file browser, saves a token through a password field (never shown again),
   imports a link, follows the job's steps, reads the warnings AS TEXT (a warning carrying HTML must stay text),
   opens the new file, finds the item in the editor's main menu, and opens a job from its #/import/<job> address. */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const {startMock, newDoc} = require('./design_ui_test.js');
const TOKEN = 'figd_' + 'Q'.repeat(30) + 'zz9w';

async function walk() {
  const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  const mock = await startMock(newDoc());
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { await mock.close(); console.log('no browser here: ' + String(e.message || e).split('\n')[0]); process.exit(77); }
  const errors = [], seen = {puts: [], posts: [], polls: 0};
  const fake = {linked: false, polls: 0, job: null};
  const page = await browser.newPage({viewport: {width: 1440, height: 900}});
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
  await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
  await page.addInitScript(() => localStorage.setItem('hoola.console.token', 'fixture-only'));
  const json = (r, o, code) => r.fulfill({status: code || 200, contentType: 'application/json', body: JSON.stringify(o)});
  await page.route(/\/api\/design\/figma$/, (r, req) => {
    const m = req.method();
    if (m === 'GET') return json(r, {linked: fake.linked, hint: fake.linked ? '...zz9w' : ''});
    if (m === 'PUT') { const b = JSON.parse(req.postData() || '{}'); seen.puts.push(b.token); if (!/^figd_/.test(b.token)) return json(r, {detail: 'That does not look like a Figma personal access token.'}, 400); fake.linked = true; return json(r, {ok: true, linked: true, hint: '...zz9w'}); }
    if (m === 'DELETE') { fake.linked = false; return json(r, {ok: true, linked: false, hint: ''}); }
    return json(r, {detail: 'no'}, 405);
  });
  await page.route(/\/api\/design\/import\//, (r, req) => {
    const u = new URL(req.url());
    if (req.method() === 'POST' && u.pathname.endsWith('/import/figma')) { seen.posts.push(JSON.parse(req.postData() || '{}'));
      fake.polls = 0; fake.job = {id: 'fi_test1', state: 'queued', step: 'Waiting to start', done: 0, total: 0, file: null, name: '', warnings: [], error: null, watch: '/console/design#/import/fi_test1'};
      return json(r, {job: fake.job}); }
    const id = u.pathname.split('/').pop();
    if (id !== 'fi_test1' || !fake.job) return json(r, {detail: 'No such import (an import is remembered for a day).'}, 404);
    seen.polls++; fake.polls++;
    const j = fake.job;
    if (fake.polls === 1) Object.assign(j, {state: 'reading', step: 'Reading the file from Figma', name: 'My App'});
    else if (fake.polls === 2) Object.assign(j, {state: 'images', step: 'Picture 1 of 2', done: 1, total: 2, file: 'f1'});
    else if (fake.polls === 3) Object.assign(j, {state: 'writing', step: 'Writing layers 1,500 of 3,000', done: 1500, total: 3000});
    else Object.assign(j, {state: 'done', step: 'Imported', done: 3000, total: 3000, layers: 2998, pages: 2, images: 2,
      warnings: [{text: 'Smooth corners (drawn as plain round corners)', count: 3}, {text: '<img src=x onerror="window.__pwned=1">', count: 1}]});
    return json(r, j);
  });
  const base = 'http://127.0.0.1:' + mock.port + '/console/design';
  const shot = async name => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };

  /* 1. the file browser has the button; no token yet -> a password field */
  await page.goto(base + '#/');
  await page.waitForSelector('.hd-hhead .hd-fig-open', {timeout: 20000});
  await page.click('.hd-fig-open');
  await page.waitForSelector('.hd-fig input[type=password]');
  const inp = page.locator('.hd-fig input[type=password]');
  assert.equal(await inp.getAttribute('autocomplete'), 'off');
  assert.ok(await page.locator('.hd-fig a[href="https://www.figma.com/settings"]').count() === 1, 'a link to Figma\'s own settings');
  const note = await page.locator('.hd-fig-note').first().textContent();
  assert.match(note, /sealed/); assert.match(note, /never shown again/); assert.match(note, /Web Studio/);
  await shot('figma-token');
  await inp.fill('wrong');
  await page.click('.hd-fig button[type=submit]');
  await page.waitForSelector('.hd-fig .hd-fig-err');
  assert.match(await page.locator('.hd-fig .hd-fig-err').textContent(), /personal access token/);
  assert.equal(await page.locator('.hd-fig input[type=password]').inputValue(), '', 'a refused token is not left in the field');
  await page.fill('.hd-fig input[type=password]', TOKEN);
  await page.click('.hd-fig button[type=submit]');
  await page.waitForSelector('.hd-fig input[type=url]');
  assert.deepEqual(seen.puts, ['wrong', TOKEN]);
  const body = await page.locator('.hd-fig').textContent();
  assert.ok(!body.includes(TOKEN), 'the token is not shown again');
  assert.match(body, /\.\.\.zz9w/);
  assert.equal(await page.evaluate(() => document.querySelectorAll('input[type=password]').length), 0);

  /* 2. import: the job's steps, then the result with the warnings as text */
  await page.fill('.hd-fig input[type=url]', 'https://www.figma.com/design/AbCdEfGhIjKlMnOp/My-App');
  await page.click('.hd-fig button[type=submit]');
  await page.waitForSelector('.hd-fig-run');
  await page.waitForSelector('.hd-fig-res', {timeout: 15000});
  assert.equal(seen.posts.length, 1); assert.equal(seen.posts[0].url, 'https://www.figma.com/design/AbCdEfGhIjKlMnOp/My-App');
  assert.ok(seen.polls >= 4);
  const res = await page.locator('.hd-fig-res').textContent();
  assert.match(res, /My App/); assert.match(res, /2,998 layers/); assert.match(res, /Smooth corners/); assert.match(res, /× 3/);
  assert.match(res, /<img src=x onerror/, 'a warning is shown as text');
  assert.equal(await page.evaluate(() => document.querySelectorAll('.hd-fig img').length), 0, 'no HTML from the server becomes an element');
  assert.equal(await page.evaluate(() => window.__pwned), undefined);
  await shot('figma-done');

  /* 3. Open file -> the editor; its main menu has the import too */
  await page.click('.hd-fig-res .hd-btn.pri');
  await page.waitForFunction(() => location.hash === '#/f/f1' && window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live', null, {timeout: 20000});
  assert.equal(await page.locator('.hd-fig').count(), 0);
  await page.click('button[aria-label="Main menu"]');
  const item = page.locator('.hd-menu .hd-mi', {hasText: 'Import from Figma'});
  assert.equal(await item.count(), 1);
  await item.click();
  await page.waitForSelector('.hd-fig input[type=url]');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('.hd-fig'));

  /* 4. the address the chat tool gives opens the job */
  await page.goto(base + '#/import/fi_test1');
  await page.waitForSelector('.hd-fig-res', {timeout: 15000});
  assert.match(await page.locator('.hd-fig-res').textContent(), /My App/);
  await page.goto(base + '#/import/fi_nope');
  await page.waitForSelector('.hd-fig .hd-fig-err', {timeout: 15000});
  assert.match(await page.locator('.hd-fig .hd-fig-err').textContent(), /No such import/);

  assert.deepEqual(errors, []);
  await browser.close(); await mock.close();
  console.log('design_figma_test: ok');
}
if (require.main === module) walk().catch(e => { console.error(e); process.exit(1); });
