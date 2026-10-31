/* v0.312 DESIGN ARENA screen (owner only): start a scored run, watch it build, read each website's score card,
   compare two versions, and run blind duels against another builder's public site.
   Talks only to /api/arena/* (the server refuses anyone but the owner). Every value from the server goes on the
   page through esc() - business names, judge lines and rival URLs are data. */
window.HoolaArena = function ({api, esc, toast}) {
  const CRIT = [['first_impression', 'First impression'], ['typography', 'Typography'], ['layout_originality', 'Originality'],
                ['imagery', 'Imagery'], ['clear_action', 'Clear action'], ['trust', 'Trust']];
  const LABEL = {judge: 'Judge (of 10)', no_blocking_pct: 'No blocking issues %', performance: 'Performance', accessibility: 'Accessibility',
                 seo: 'SEO', lcp_ms: 'LCP (ms)', cls: 'CLS', kb: 'First load (KB)', inr: '₹ per site', minutes: 'Minutes per site',
                 sameness: 'Sameness (lower = more original)', photos: 'Photos', ...Object.fromEntries(CRIT)};
  const RIVALS = [['lovable', 'Lovable'], ['v0', 'v0'], ['bolt', 'Bolt'], ['emergent', 'Emergent'], ['chatgpt', 'ChatGPT'], ['other', 'Other']];
  const RIVAL_NAME = Object.fromEntries(RIVALS);
  let EL = null, OPEN = null, TIMER = null, SHOTS = {}, DUELING = false;

  const num = (v, d = 1) => (v === null || v === undefined || v === '') ? '–' : (typeof v === 'number' ? String(parseFloat(v.toFixed(d))) : esc(String(v)));
  const rupees = v => (v === null || v === undefined) ? '–' : '₹' + Math.round(Number(v)).toLocaleString('en-IN');
  const when = iso => { if (!iso) return ''; const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const STATUS = {running: ['v', 'Running'], done: ['ok', 'Done'], stopped: ['warn', 'Stopped'], failed: ['bad', 'Failed'], interrupted: ['bad', 'Interrupted']};
  const tag = s => { const [c, n] = STATUS[s] || ['warn', s || '–']; return `<span class="tag ${c}">${esc(n)}</span>`; };
  const visible = () => EL && EL.isConnected && !EL.closest('.view')?.hidden;

  function schedule(on) {
    clearTimeout(TIMER); TIMER = null;
    if (on) TIMER = setTimeout(() => { if (visible()) (OPEN ? openRun(OPEN, true) : draw(EL)); }, 12000);
  }

  async function draw(el) {
    EL = el; OPEN = null;
    if (!el.firstChild) el.innerHTML = '<div class="vh"><h2>Design Arena</h2></div><div class="empty">Loading…</div>';
    let d;
    try { d = await api('GET', '/api/arena/runs'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>Design Arena</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    const runs = d.runs || [], live = runs.find(r => r.status === 'running'), last = runs.find(r => r.status === 'done' && r.summary && r.summary.sites);
    const s = last?.summary || {}, duels = d.duels || {}, maxInr = Number(d.max_inr) || 3000;
    const totals = Object.values(duels).reduce((a, v) => ({n: a.n + (v.duels || 0), w: a.w + (v.hoola || 0)}), {n: 0, w: 0});
    el.innerHTML = `<div class="vh"><h2>Design Arena</h2><span class="muted ar-sub">Hoola builds real websites from fixed briefs and scores them. Your own sites are never touched.</span></div>
      <div class="kpis">
        <div class="kpi gl"><b>${num(s.judge)}</b><span>judge score, latest run</span></div>
        <div class="kpi gl"><b>${s.no_blocking_pct === undefined || s.no_blocking_pct === null ? '–' : num(s.no_blocking_pct, 0) + '%'}</b><span>sites with no blocking issue</span></div>
        <div class="kpi gl"><b>${s.lcp_ms ? num(s.lcp_ms / 1000, 1) + ' s' : '–'}</b><span>median load (LCP)</span></div>
        <div class="kpi gl"><b>${totals.n ? Math.round(100 * totals.w / totals.n) + '%' : '–'}</b><span>blind duels won${totals.n ? ` (${totals.n})` : ''}</span></div>
      </div>
      <div class="grid2 ar-top">
        ${live ? liveTile(live) : startTile(maxInr)}
        ${duelTile(runs)}
      </div>
      <div class="tile gl ar-runs"><h3>Runs</h3>${runs.length ? runsTable(runs) : '<div class="empty">No runs yet. Start one above: 6 websites is a good first run.</div>'}
        ${runs.filter(r => r.summary && r.summary.sites).length > 1 ? compareForm(runs) : ''}<div id="arCmp"></div></div>
      <div class="tile gl"><h3>Blind duels by builder</h3>${duelTable(duels)}${recentDuels(d.recent_duels || [])}</div>`;
    wire(el, runs, maxInr);
    schedule(!!live);
  }

  function startTile(maxInr) {
    const budget = Math.min(2000, maxInr);
    return `<form class="tile gl ar-form" id="arStart" autocomplete="off"><h3>New run</h3>
      <p class="muted ar-help">Each website is built end to end (plan, looks, build, checks), then an independent Opus judge scores the home page.</p>
      <div class="ar-fields">
        <label><span>Websites</span><input type="number" id="arN" min="1" max="50" value="6" required></label>
        <label><span>Brief set seed</span><input type="number" id="arSeed" min="1" value="1" required></label>
        <label><span>Budget (₹)</span><input type="number" id="arBudget" min="50" max="${maxInr}" step="50" value="${budget}" required></label>
      </div>
      <label class="ar-note"><span>Note (optional)</span><input type="text" id="arNote" maxlength="300" placeholder="For example: after the new hero layouts"></label>
      <p class="muted ar-est" id="arEst"></p>
      <div class="acts"><button class="btn go" type="submit">Start run</button></div>
      <p class="muted ar-help">Same seed = the same businesses, so two versions can be compared fairly. The run stops between websites when it reaches the budget (most ₹${Math.round(maxInr).toLocaleString('en-IN')}).</p>
    </form>`;
  }

  function liveTile(r) {
    const pct = r.budget_inr ? Math.min(100, Math.round(100 * (r.spent_inr || 0) / r.budget_inr)) : 0;
    return `<div class="tile gl ar-live"><h3>Run in progress ${tag('running')}</h3>
      <p class="ar-big">${esc(String(r.n))} websites · v${esc(r.version || '')}${r.note ? ` · <span class="muted">${esc(r.note)}</span>` : ''}</p>
      <div class="ar-meter" role="meter" aria-label="Budget used" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${pct}%"></i></div>
      <p class="muted ar-help">${rupees(r.spent_inr)} of ${rupees(r.budget_inr)} spent. Started ${esc(when(r.started))}. This page refreshes on its own.</p>
      <div class="acts"><button class="btn soft" type="button" data-ar-open="${esc(r.run)}">See websites so far</button>
        <button class="btn soft ar-stop" type="button" data-ar-stop="${esc(r.run)}">Stop after this website</button></div>
    </div>`;
  }

  function duelTile(runs) {
    return `<form class="tile gl ar-form" id="arDuel" autocomplete="off"><h3>Blind duel</h3>
      <p class="muted ar-help">Build the same business on another builder, publish it, and paste its public address. The judge sees the two sites only as A and B, in random order.</p>
      <label><span>Business (from a run)</span><select id="arBrief" required><option value="">Loading…</option></select></label>
      <div class="ar-fields ar-two">
        <label><span>Builder</span><select id="arRival">${RIVALS.map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select></label>
        <label><span>Public address</span><input type="url" id="arUrl" placeholder="https://…" required></label>
      </div>
      <div class="acts"><button class="btn go" type="submit" ${DUELING ? 'disabled' : ''}>${DUELING ? 'Judging…' : 'Run duel'}</button></div>
      <div id="arDuelOut" aria-live="polite"></div>
    </form>`;
  }

  function runsTable(runs) {
    return `<div class="sttbl"><table><thead><tr><th>Started</th><th>Version</th><th>Sites</th><th>Judge</th><th>No blocking</th><th>LCP</th><th>₹ / site</th><th>Spent</th><th>Status</th><th></th></tr></thead><tbody>
      ${runs.map(r => { const s = r.summary || {};
        return `<tr><td>${esc(when(r.started))}${r.note ? `<div class="muted ar-small">${esc(r.note)}</div>` : ''}</td><td>v${esc(r.version || '')}</td>
          <td>${s.sites ? `${num(s.ready)} / ${num(s.sites)}` : `– / ${esc(String(r.n))}`}</td><td><b>${num(s.judge)}</b></td>
          <td>${s.no_blocking_pct === undefined || s.no_blocking_pct === null ? '–' : num(s.no_blocking_pct, 0) + '%'}</td>
          <td>${s.lcp_ms ? num(s.lcp_ms / 1000, 1) + ' s' : '–'}</td><td>${rupees(s.inr)}</td><td>${rupees(r.spent_inr)}</td><td>${tag(r.status)}</td>
          <td><button class="btn soft ar-sm" type="button" data-ar-open="${esc(r.run)}">Open</button></td></tr>`; }).join('')}
      </tbody></table></div>`;
  }

  function compareForm(runs) {
    const done = runs.filter(r => r.summary && r.summary.sites);
    const opt = (r, sel) => `<option value="${esc(r.run)}" ${sel ? 'selected' : ''}>v${esc(r.version || '')} · ${esc(when(r.started))}${r.note ? ' · ' + esc(r.note.slice(0, 30)) : ''}</option>`;
    return `<form class="ar-cmpf" id="arCmpF"><b>Compare two runs</b>
      <label><span>Before</span><select id="arA">${done.map((r, i) => opt(r, i === 1)).join('')}</select></label>
      <label><span>After</span><select id="arB">${done.map((r, i) => opt(r, i === 0)).join('')}</select></label>
      <button class="btn soft" type="submit">Compare</button></form>`;
  }

  function duelTable(duels) {
    const rows = Object.entries(duels);
    if (!rows.length) return '<div class="empty">No duels yet.</div>';
    return `<div class="sttbl"><table><thead><tr><th>Builder</th><th>Duels</th><th>Hoola won</th><th>They won</th><th>Tie</th><th>Hoola win rate</th></tr></thead><tbody>
      ${rows.map(([k, v]) => `<tr><td>${esc(RIVAL_NAME[k] || k)}</td><td>${num(v.duels)}</td><td>${num(v.hoola)}</td><td>${num(v.rival)}</td><td>${num(v.tie)}</td>
        <td><b>${v.win_pct === null || v.win_pct === undefined ? '–' : num(v.win_pct, 0) + '%'}</b></td></tr>`).join('')}</tbody></table></div>`;
  }

  // r = a duel result: {winner: hoola|rival|tie, hoola: {overall}, rival: {overall}, why}; builder = 'lovable', 'v0'...
  function verdictLine(r, builder) {
    const them = RIVAL_NAME[builder] || builder || 'They';
    const w = r.winner === 'hoola' ? '<span class="tag ok">Hoola won</span>' : r.winner === 'rival' ? `<span class="tag bad">${esc(them)} won</span>` : '<span class="tag warn">Tie</span>';
    const sc = x => (x && x.overall !== undefined && x.overall !== null) ? num(x.overall) : '–';
    return `${w} <span class="muted">Hoola ${sc(r.hoola)} · ${esc(them)} ${sc(r.rival)}</span>`;
  }

  function recentDuels(list) {
    if (!list.length) return '';
    return `<h4 class="ar-h4">Latest duels</h4><div class="ar-duels">${list.map(r => `<div class="ar-duel">
      <div><b>${esc(r.name || r.brief)}</b> <span class="muted">vs ${esc(RIVAL_NAME[r.builder] || r.builder)} · ${esc(when(r.at))}</span></div>
      <div>${verdictLine(r, r.builder)}</div>
      ${r.why ? `<p class="muted ar-why">${esc(r.why)}</p>` : ''}</div>`).join('')}</div>`;
  }

  function wire(el, runs, maxInr) {
    const est = () => { const n = Number(el.querySelector('#arN')?.value) || 0, b = Number(el.querySelector('#arBudget')?.value) || 0, o = el.querySelector('#arEst');
      if (o) o.textContent = n ? `Expected cost about ₹${(n * 100).toLocaleString('en-IN')}–₹${(n * 300).toLocaleString('en-IN')} (₹100–300 a website). ${n * 100 > b ? 'The budget will stop it early.' : ''}` : ''; };
    el.querySelector('#arN')?.addEventListener('input', est); el.querySelector('#arBudget')?.addEventListener('input', est); est();
    el.querySelector('#arStart')?.addEventListener('submit', async e => {
      e.preventDefault(); const btn = e.target.querySelector('button[type=submit]'); btn.disabled = true;
      try {
        const r = await api('POST', '/api/arena/start', {n: Number(el.querySelector('#arN').value), seed: Number(el.querySelector('#arSeed').value),
          budget_inr: Math.min(maxInr, Number(el.querySelector('#arBudget').value)), note: el.querySelector('#arNote').value.trim()});
        toast(r.say || 'Run started.'); draw(el);
      } catch (err) { toast(err.message, true); btn.disabled = false; }
    });
    el.querySelectorAll('[data-ar-open]').forEach(b => b.addEventListener('click', () => openRun(b.dataset.arOpen)));
    el.querySelectorAll('[data-ar-stop]').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true; try { const r = await api('POST', `/api/arena/runs/${encodeURIComponent(b.dataset.arStop)}/stop`); toast(r.say || 'Stopping.'); } catch (err) { toast(err.message, true); b.disabled = false; }
    }));
    el.querySelector('#arCmpF')?.addEventListener('submit', async e => {
      e.preventDefault(); const a = el.querySelector('#arA').value, b = el.querySelector('#arB').value, out = el.querySelector('#arCmp');
      if (a === b) { out.innerHTML = '<p class="muted">Pick two different runs.</p>'; return; }
      try { out.innerHTML = compareTable(await api('GET', `/api/arena/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`)); }
      catch (err) { out.innerHTML = `<p class="badc">${esc(err.message)}</p>`; }
    });
    fillBriefs(el, runs);
    el.querySelector('#arDuel')?.addEventListener('submit', async e => {
      e.preventDefault(); const out = el.querySelector('#arDuelOut'), btn = e.target.querySelector('button[type=submit]');
      const [brief, site] = (el.querySelector('#arBrief').value || '').split('|');
      if (!brief) { out.innerHTML = '<p class="muted">Pick a business that a run has built.</p>'; return; }
      DUELING = true; btn.disabled = true; btn.textContent = 'Judging…'; out.innerHTML = '<p class="muted">Taking screenshots of both sites and asking the judge. This takes about a minute.</p>';
      try {
        const r = await api('POST', '/api/arena/duel', {brief_id: brief, site, rival: el.querySelector('#arRival').value, url: el.querySelector('#arUrl').value.trim()});
        out.innerHTML = `<div class="ar-duel ar-result">${verdictLine(r, el.querySelector('#arRival').value)}${r.why ? `<p class="muted ar-why">${esc(r.why)}</p>` : ''}</div>`;
      } catch (err) { out.innerHTML = `<p class="badc">${esc(err.message)}</p>`; }
      DUELING = false; btn.disabled = false; btn.textContent = 'Run duel';
    });
  }

  async function fillBriefs(el, runs) {
    const sel = el.querySelector('#arBrief'); if (!sel) return;
    const seen = new Map();
    for (const r of runs.filter(x => x.summary && x.summary.sites || x.status === 'running').slice(0, 4)) {
      try { const d = await api('GET', `/api/arena/runs/${encodeURIComponent(r.run)}`);
        (d.items || []).filter(c => c.site && c.status === 'ready').forEach(c => { if (!seen.has(c.brief)) seen.set(c.brief, {site: c.site, name: c.name, ind: c.industry, v: d.version}); });
      } catch {}
    }
    if (!sel.isConnected) return;
    sel.innerHTML = seen.size ? '<option value="">Choose a business…</option>' + [...seen].map(([b, x]) => `<option value="${esc(b)}|${esc(x.site)}">${esc(x.name)}${x.ind ? ' · ' + esc(x.ind) : ''} (v${esc(x.v || '')})</option>`).join('')
      : '<option value="">No finished websites yet. Run the Arena first.</option>';
  }

  function compareTable(c) {
    const rows = Object.entries(c.metrics || {}).sort(([a], [b]) => (a === 'judge' ? -1 : b === 'judge' ? 1 : 0));
    const V = {behtar: ['ok', 'Better'], bura: ['bad', 'Worse'], same: ['warn', 'Same']};
    return `<p class="ar-cmpsum"><span class="tag ok">${num(c.better)} better</span> <span class="tag bad">${num(c.worse)} worse</span></p>
      <div class="sttbl"><table><thead><tr><th>Measure</th><th>Before</th><th>After</th><th>Change</th><th></th></tr></thead><tbody>
      ${rows.map(([k, m]) => { const [cl, n] = V[m.verdict] || ['warn', m.verdict];
        return `<tr><td>${esc(LABEL[k] || k)}</td><td>${num(m.was, 2)}</td><td>${num(m.now, 2)}</td><td>${m.change > 0 ? '+' : ''}${num(m.change, 2)}</td><td><span class="tag ${cl}">${n}</span></td></tr>`; }).join('')}
      </tbody></table></div>`;
  }

  async function openRun(id, quiet) {
    OPEN = id; const el = EL;
    if (!quiet) el.innerHTML = '<div class="vh"><h2>Design Arena</h2></div><div class="empty">Loading…</div>';
    let d;
    try { d = await api('GET', `/api/arena/runs/${encodeURIComponent(id)}`); }
    catch (e) { el.innerHTML = `<div class="vh"><button class="btn soft ar-sm" type="button" id="arBack">← All runs</button></div><p class="badc">${esc(e.message)}</p>`; el.querySelector('#arBack').onclick = () => draw(el); return; }
    if (OPEN !== id) return;
    const items = d.items || [], s = d.summary || {};
    el.innerHTML = `<div class="vh ar-vh"><button class="btn soft ar-sm" type="button" id="arBack">← All runs</button><h2>Run · v${esc(d.version || '')}</h2>${tag(d.status)}</div>
      <p class="muted ar-say">${s.sites ? esc(sayLine(s)) : 'Still building. This page refreshes on its own.'}${d.note ? ` · ${esc(d.note)}` : ''}</p>
      ${s.sites ? `<div class="ar-crit">${CRIT.map(([k, n]) => bar(n, s[k])).join('')}</div>` : ''}
      <div class="ar-grid">${items.length ? items.map(siteCard).join('') : `<div class="empty">No website finished yet. The first one takes a few minutes.</div>`}</div>`;
    el.querySelector('#arBack').onclick = () => draw(el);
    el.querySelectorAll('img[data-ar-shot]').forEach(loadShot);
    el.querySelectorAll('[data-ar-more]').forEach(b => b.addEventListener('click', () => { const c = b.closest('.ar-card'); c.classList.toggle('more'); b.setAttribute('aria-expanded', String(c.classList.contains('more'))); }));
    schedule(d.status === 'running');
  }

  function sayLine(s) {   // the run in one readable line (the server's report_text is for logs)
    const p = [`${s.sites} websites`, `judge ${num(s.judge)} of 10`];
    if (s.no_blocking_pct !== null && s.no_blocking_pct !== undefined) p.push(`${num(s.no_blocking_pct, 0)}% with no blocking issue`);
    if (s.lcp_ms) p.push(`loads in ${num(s.lcp_ms / 1000)} s`);
    if (s.inr !== null && s.inr !== undefined) p.push(`${rupees(s.inr)} a website`);
    if (s.minutes) p.push(`${num(s.minutes)} min a website`);
    if (s.sameness !== null && s.sameness !== undefined) p.push(`sameness ${num(s.sameness)}`);
    return p.join(' · ');
  }

  function bar(name, v) {
    const p = typeof v === 'number' ? Math.max(0, Math.min(100, v * 10)) : 0;
    return `<div class="ar-bar"><span>${esc(name)}</span><i><b style="width:${p}%"></b></i><em>${num(v)}</em></div>`;
  }

  function siteCard(c) {
    if (c.status === 'failed' || !c.site) return `<div class="ar-card gl ar-failed"><div class="ar-shot ar-noshot">Not built</div><div class="ar-body">
      <b>${esc(c.name || c.brief)}</b><span class="muted ar-small">${esc([c.industry, c.city].filter(Boolean).join(' · '))}</span>
      <p class="badc ar-small">${esc(c.error || 'The build did not finish.')}</p></div></div>`;
    const j = c.judge || {}, sc = j.scores || {};
    return `<div class="ar-card gl"><div class="ar-shot"><img alt="Home page of ${esc(c.name || '')} on a phone" data-ar-shot="${esc(c.site)}"></div>
      <div class="ar-body">
        <div class="ar-head"><div><b>${esc(c.name || c.brief)}</b><span class="muted ar-small">${esc([c.industry, c.city].filter(Boolean).join(' · '))}</span></div>
          <div class="ar-score" title="Judge score of 10">${num(j.overall)}</div></div>
        <div class="ar-chips"><span class="chip ${c.blocking ? 'ar-bad' : ''}">${c.blocking ? num(c.blocking) + ' blocking' : 'No blocking'}</span>
          <span class="chip">Perf ${num(c.performance, 0)}</span><span class="chip">LCP ${c.lcp_ms ? num(c.lcp_ms / 1000, 1) + ' s' : '–'}</span>
          <span class="chip">${rupees(c.inr)}</span><span class="chip">${num(c.minutes)} min</span>${typeof c.sameness === 'number' ? `<span class="chip">Sameness ${num(c.sameness)}</span>` : ''}</div>
        ${j.best ? `<p class="ar-line"><b>Best</b> ${esc(j.best)}</p>` : ''}${j.worst ? `<p class="ar-line"><b>Weakest</b> ${esc(j.worst)}</p>` : ''}
        <div class="acts"><button class="btn soft ar-sm" type="button" data-ar-more aria-expanded="false">Scores</button>
          <button class="btn soft ar-sm" type="button" data-ar-desk>Desktop view</button></div>
      </div>
      <div class="ar-extra">${CRIT.map(([k, n]) => bar(n, sc[k])).join('')}
        <p class="muted ar-small">Accessibility ${num(c.accessibility, 0)} · SEO ${num(c.seo, 0)} · ${num(c.sections, 0)} sections · ${num(c.photos, 0)} photos${c.ai_photos ? ` (${num(c.ai_photos, 0)} AI)` : ''}</p></div>
    </div>`;
  }

  async function loadShot(img, w) {
    const id = img.dataset.arShot, key = id + '@' + (w || '390');
    try {
      SHOTS[key] ||= api('GET', `/api/arena/shot/${encodeURIComponent(id)}?w=${w || 390}`, undefined, {raw: true}).then(r => r.blob()).then(b => URL.createObjectURL(b));
      img.src = await SHOTS[key];
    } catch { delete SHOTS[key]; img.closest('.ar-shot')?.classList.add('ar-noshot'); img.replaceWith(Object.assign(document.createElement('span'), {textContent: 'No screenshot'})); }
  }

  document.addEventListener('click', e => {   // Desktop view swaps the card's phone picture for the 1440px one (and back)
    const b = e.target.closest('[data-ar-desk]'); if (!b) return;
    const card = b.closest('.ar-card'), img = card?.querySelector('img[data-ar-shot]'); if (!img) return;
    const desk = card.classList.toggle('desk');
    b.textContent = desk ? 'Phone view' : 'Desktop view';
    loadShot(img, desk ? 1440 : 390);
  });

  return {draw, openRun};
};
