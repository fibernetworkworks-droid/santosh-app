/* HOOLA DESIGN - phase D9c branches + merge (hd-branches.js) against a REAL server.
   Two signed-in browsers: A makes a branch of a file from the Branches dialog and edits there (the hero's fill,
   a new badge), B edits main differently (the same fill, another colour). A opens "Review & merge": the conflict
   shows both values in plain words with a picture of each, the changed layers show before / after pictures, the
   Merge button waits for the choice; A keeps the branch's fill and merges. B, on main, sees the result land live;
   A's branch turns read only with a link to main; the file browser tags the branch "Merged into ...", and the
   pre-merge version is in main's history.

   Run:  HD_BASE=http://127.0.0.1:<port> HD_KEY=<api key> node server/tests/web/design_branches_test.js
         (server/tests/test_v0825_design_branches.py starts the server on a free port with a fresh database)
         DESIGN_SHOTS=<dir> also writes screenshots, light and dark.
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium / no server). Last line = JSON. */
'use strict';
const assert = require('node:assert/strict'), fs = require('fs'), path = require('path');
const BASE = (process.env.HD_BASE || '').replace(/\/+$/, ''), KEY = process.env.HD_KEY || 'itest-key';
const SHOTS = process.env.DESIGN_SHOTS || '';
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
  if (!BASE) { console.log('SKIP: HD_BASE is not set (run it through test_v0825_design_branches.py)'); process.exit(77); }
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  try { const r = await fetch(BASE + '/console/design'); if (r.status !== 200) throw new Error('status ' + r.status); } catch (e) { console.log('SKIP: no Hoola Design server at ' + BASE + ' (' + e.message + ')'); process.exit(77); }
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  if (SHOTS) fs.mkdirSync(SHOTS, {recursive: true});
  const errors = [];

  async function newPage(name) {
    const ctx = await browser.newContext({viewport: {width: 1440, height: 900}, colorScheme: 'light'});
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(name + ': ' + e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR|WebSocket/.test(m.text())) errors.push(name + ' console: ' + m.text()); });
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(key => { localStorage.setItem('hoola.console.token', key); }, KEY);
    return page;
  }
  const live = page => page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0 && HD.branches && HD.branches.info, null, {timeout: 25000});
  const saved = page => page.waitForFunction(() => HD.net.status === 'live' && HD.net.pending() === 0 && !HD.net.held);
  const shot = async (page, name) => { if (SHOTS) { await page.waitForTimeout(250); await page.screenshot({path: path.join(SHOTS, name + '.png')}); } };
  const fill = (page, id) => page.evaluate(i => { const f = HD.store.has(i) ? HD.store.prop(i, 'fills') : null; return f && f[0] ? f[0].color : null; }, id);
  const toast = (page, re) => page.waitForFunction(src => new RegExp(src).test((document.querySelector('.hd-toast.on') || {}).textContent || ''), re.source);

  try {
    const file = (await rest('POST', '/files', {name: 'Diwali poster'})).data;
    ok(file && file.id, 'a file was made');
    const A = await newPage('A'), Bp = await newPage('B');
    await A.goto(BASE + '/console/design#/f/' + file.id); await live(A);
    const ids = await A.evaluate(() => { const S = HD.store, solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}]; const out = {};
      S.tx('seed', () => { out.frame = S.create('FRAME', '0:1', {name: 'Phone', x: 0, y: 0, w: 390, h: 700, fills: solid('#FFFFFF')});
        out.hero = S.create('RECT', out.frame, {name: 'Hero', x: 24, y: 60, w: 342, h: 200, radius: 20, fills: solid('#FF8800')});
        out.card = S.create('RECT', out.frame, {name: 'Card', x: 24, y: 300, w: 160, h: 120, fills: solid('#EEEEEE')}); });
      return out; });
    await saved(A);
    /* ------------------------------------------------------------ main: the Branches button and dialog */
    const btn = A.locator('.hd-top-l .hd-br-btn');
    await btn.waitFor({timeout: 10000});
    ok(await btn.isVisible(), 'a main file shows a Branches button');
    await btn.click();
    await A.locator('.hd-br-dialog').waitFor();
    ok(/No branches yet/.test(await A.locator('.hd-br-list').textContent()), 'the empty list says what a branch is');
    await shot(A, 'branches-dialog-light');
    await A.fill('.hd-br-make input', 'Try blue');
    await A.click('.hd-br-make .hd-btn.pri');
    await A.waitForFunction(id => location.hash.indexOf('#/f/') === 0 && location.hash.indexOf(id) < 0, file.id);
    const branchId = await A.evaluate(() => decodeURIComponent(location.hash.slice(4)));
    await live(A);
    await A.waitForFunction(() => HD.branches.info && HD.branches.info.is_branch);
    const badge = A.locator('.hd-top-l .hd-br-badge');
    await badge.waitFor();
    eq((await badge.textContent()).trim(), 'Branch of Diwali poster', 'the branch shows whose branch it is');
    ok(await A.evaluate(() => HD.net.cid > 1000000), 'the branch hands out its own range of layer ids');
    /* ------------------------------------------------------------ edits on both sides */
    const badgeId = await A.evaluate(([hero, frame]) => { const S = HD.store, solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}]; let b;
      S.tx('branch edits', () => { S.set(hero, {fills: solid('#2266FF'), y: 80}); b = S.create('RECT', frame, {name: 'Badge', x: 280, y: 20, w: 80, h: 32, radius: 16, fills: solid('#E0457B')}); });
      return b; }, [ids.hero, ids.frame]);
    await saved(A);
    await Bp.goto(BASE + '/console/design#/f/' + file.id); await live(Bp);
    eq(await fill(Bp, ids.hero), '#FF8800', 'main still has its own fill');
    ok(!(await Bp.evaluate(id => HD.store.has(id), badgeId)), 'the branch badge is not on main yet');
    await Bp.evaluate(([hero, card]) => { const S = HD.store; S.tx('main edits', () => { S.set(hero, {fills: [{type: 'solid', color: '#00AA00', opacity: 1, visible: true}]}); S.set(card, {name: 'Card (main)'}); }); }, [ids.hero, ids.card]);
    await saved(Bp);
    /* ------------------------------------------------------------ review */
    await badge.click();
    await A.locator('.hd-menu .hd-mi', {hasText: 'Review & merge'}).click();
    await A.locator('.hd-br-review .hd-br-conf').waitFor({timeout: 20000});
    await A.waitForFunction(() => HD.branches.review && HD.branches.review.pics && !HD.net.held, null, {timeout: 20000});
    const conf = A.locator('.hd-br-conf');
    eq(await conf.count(), 1, 'one conflict: the fill changed on both sides');
    eq((await conf.locator('.hd-br-ctext').textContent()).trim(), 'Fill: #2266FF here, #00AA00 on main', 'the conflict says both values in plain words');
    eq(await conf.locator('img.hd-br-pic').count(), 2, 'a picture of each side of the conflict');
    const rows = await A.evaluate(() => Array.from(document.querySelectorAll('.hd-br-chg')).map(r => ({name: r.querySelector('.hd-br-cname').textContent, kind: r.dataset.kind, pics: r.querySelectorAll('img.hd-br-pic').length, what: r.querySelector('.hd-br-ckind').textContent})));
    const hero = rows.find(r => r.name === 'Hero'), added = rows.find(r => r.name === 'Badge');
    ok(hero && hero.pics === 2 && /Fill/.test(hero.what) && /Y/.test(hero.what), 'the changed hero has a before and an after picture');
    ok(added && added.kind === 'added' && added.pics === 1, 'the new badge has its after picture');
    ok(/On main since you branched \(2\)/.test(await A.locator('.hd-br-other summary').textContent()), 'main\'s own changes are listed as staying');
    ok(/Card \(main\)/.test(await A.locator('.hd-br-other').textContent()), 'with their names');
    ok(await A.locator('.hd-br-sec h4.hd-br-page').first().textContent() === 'Page 1', 'changes are grouped by page');
    const merge = A.locator('.hd-br-rfoot .hd-btn.pri');
    ok(await merge.isDisabled(), 'Merge waits until the conflict is decided');
    ok(/1 conflict still needs a choice/.test(await A.locator('.hd-br-fnote').textContent()), 'the footer says what is missing');
    eq(await fill(A, ids.hero), '#2266FF', 'after the pictures the branch is back to its own document');
    eq(await A.evaluate(() => HD.net.role), 'edit', 'and it is still editable');
    await shot(A, 'review-light');
    await A.evaluate(() => window.HoolaTheme && HoolaTheme.setTheme('dark'));
    await shot(A, 'review-dark');
    await A.evaluate(() => window.HoolaTheme && HoolaTheme.setTheme('light'));
    await conf.locator('.hd-br-opt[data-side="ours"]').click();
    ok(await conf.locator('.hd-br-opt[data-side="ours"]').getAttribute('aria-checked') === 'true', 'the choice is marked');
    ok(!(await merge.isDisabled()), 'Merge wakes up once every conflict is decided');
    await shot(A, 'review-decided-light');
    await merge.click();
    await toast(A, /Merged into/);
    /* ------------------------------------------------------------ after the merge */
    await Bp.waitForFunction(([hero, b]) => HD.store.has(b) && HD.store.prop(hero, 'fills')[0].color === '#2266FF', [ids.hero, badgeId], {timeout: 15000});
    ok(true, 'main shows the merged fill and the new badge live');
    eq(await Bp.evaluate(id => HD.store.prop(id, 'name'), ids.card), 'Card (main)', 'main\'s own change stayed');
    eq(await Bp.evaluate(id => HD.store.prop(id, 'y'), ids.hero), 80, 'the branch\'s other change landed too');
    await A.waitForFunction(() => HD.net.role === 'view' && HD.store.readOnly, null, {timeout: 15000});
    ok(true, 'the merged branch is read only now');
    await A.locator('.hd-br-done a.hd-btn').waitFor();
    eq(await A.locator('.hd-br-done a.hd-btn').getAttribute('href'), '#/f/' + file.id, 'the bar links to main');
    await A.waitForFunction(() => /Merged into/.test((document.querySelector('.hd-br-badge') || {}).textContent || ''));
    ok(true, 'the badge says merged');
    await shot(A, 'merged-light');
    await Bp.evaluate(() => window.HoolaTheme && HoolaTheme.setTheme('dark'));
    await shot(Bp, 'main-after-merge-dark');
    const versions = (await rest('GET', '/files/' + file.id + '/versions')).data.versions;
    ok(versions.some(v => v.label === 'Before merging Try blue'), 'main has a version from before the merge');
    /* ------------------------------------------------------------ the file browser */
    await A.click('.hd-br-done a.hd-btn');
    await A.waitForFunction(id => HD.app.file && HD.app.file.id === id && HD.net.status === 'live' && HD.branches.info && HD.branches.info.file === id, file.id, {timeout: 20000});
    ok(!(await A.evaluate(() => HD.branches.info.is_branch)), 'the link opened main');
    await A.goto(BASE + '/console/design#/');
    await A.locator('.hd-card[data-file="' + branchId + '"] .hd-br-tag').waitFor({timeout: 15000});
    eq((await A.locator('.hd-card[data-file="' + branchId + '"] .hd-br-tag').textContent()).trim(), 'Merged into Diwali poster', 'the file browser tags the branch');
    eq(await A.locator('.hd-card[data-file="' + file.id + '"] .hd-br-tag').count(), 0, 'and not the main file');
    await shot(A, 'files-light');
    eq(errors, [], 'no page errors');
    console.log(JSON.stringify({ok: true, checks}));
  } catch (e) {
    console.log('FAIL: ' + (e && e.stack || e) + (errors.length ? '\nerrors: ' + errors.join('\n') : ''));
    console.log(JSON.stringify({ok: false, checks, error: String(e && e.message || e)}));
    await browser.close();
    process.exit(1);
  }
  await browser.close();
}
main();
