/* Prayogshala studio walk-through: opens each lab in headless Chromium (test mode = no animations, physics driven by
   the test), runs every experiment step's own `auto` action exactly as a student would (through the same buttons'
   code paths), checks each step's `ok`, then checks the final result against the lab's true value within `tol`.
   Usage: node tools/prayog_walk.js http://localhost:8791 [id ...]   (needs playwright; screenshots -> $SHOTS if set)
   With no ids it walks EVERY experiment (catalogue labs + their variants), paged from the server.
   LOAD_MS=<ms> is the page-load budget (default 300000: a busy machine renders slowly, never fail a good lab on time alone).
   BASE=<lab id> walks one family; SHARD=i/n walks every n-th experiment starting at i (CI runs n shards in parallel). */
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://localhost:8791';
const only = process.argv.slice(3);
(async () => {
  let ids = only;
  if (!ids.length) {
    for (let page = 1; ; page++) {
      const d = await (await fetch(`${base}/api/prayog/labs?limit=200&page=${page}${process.env.BASE ? '&base=' + process.env.BASE : ''}`)).json();
      ids = ids.concat(d.labs.map((l) => l.id));
      if (ids.length >= d.total || !d.labs.length) break;
    }
  }
  if (process.env.SHARD) { const [i, n] = process.env.SHARD.split('/').map(Number); ids = ids.filter((_, k) => k % n === i); }
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  let bad = 0;
  for (const id of ids) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    page.setDefaultTimeout(180000);                      // a busy machine renders slowly; never fail a good lab on time alone
    const errs = [];
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error' && !/favicon|fonts\.g/.test(m.text())) errs.push('console: ' + m.text()); });
    let out;
    try {
      await page.goto(`${base}/static/prayog/lab.html?id=${id}&test=1`);
      await page.waitForFunction(() => window.__studio && window.__studio.steps, null, { timeout: +(process.env.LOAD_MS || 300000) });
      if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${id}-0.png` });
      out = await page.evaluate(async () => {
        const S = window.__studio, log = [];
        S.next();                                            // theory -> first experiment step
        for (let guard = 0; guard < 20; guard++) {
          const st = S.steps[S.step];
          if (st.result || st.viva) break;
          if (!st.auto) { log.push(`step ${st.id}: no auto`); return { ok: false, log }; }
          await st.auto(S);
          const ok = st.ok ? !!st.ok(S) : true;
          log.push(`step ${st.id}: ${ok ? 'ok' : 'NOT ok'}`);
          if (!ok) return { ok: false, log };
          S.next();
        }
        const r = S.result();
        const tol = S.exp.tol === undefined ? 0.03 : S.exp.tol;
        if (!r || !isFinite(r.value)) return { ok: false, log: log.concat(['no result']) };
        const err = r.truth ? Math.abs(r.value - r.truth) / Math.abs(r.truth) : 0;
        log.push(`result ${r.label} = ${r.value.toFixed(4)} ${r.unit || ''} (true ${r.truth}) err ${(err * 100).toFixed(2)}% tol ${(tol * 100).toFixed(1)}%`);
        S.render();                                          // the result pane and the viva must draw too
        S.next(); S.render();
        return { ok: err <= tol, log, rows: S.rows.length };
      });
      if (process.env.SHOTS) {
        await page.evaluate(() => { const S = window.__studio; S.fast = false; S.go(1); });
        await page.waitForTimeout(1300);
        await page.screenshot({ path: `${process.env.SHOTS}/${id}-1.png` });
      }
    } catch (e) { out = { ok: false, log: ['crash: ' + e.message] }; }
    const pass = out.ok && !errs.length;
    if (!pass) bad++;
    console.log(`${pass ? 'PASS' : 'FAIL'} ${id}\n   ${out.log.join('\n   ')}${errs.length ? '\n   ' + errs.slice(0, 5).join('\n   ') : ''}`);
    await page.close();
  }
  await browser.close();
  console.log(bad ? `${bad} lab(s) failed` : `all ${ids.length} labs passed`);
  process.exit(bad ? 1 : 0);
})();
