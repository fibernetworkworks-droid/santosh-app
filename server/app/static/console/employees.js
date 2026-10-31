/* v0.317 HIRE AN EMPLOYEE: the Employee Hub (hire / pause / let go) and the SEO Desk of a hired SEO Specialist
   (onboarding, KPIs against the baseline, the 90-day plan board, alerts, schedule, run-now buttons).
   Talks to /api/employees* and /api/seo/{onboard,desk,roadmap,run,gsc/link}. Every value from the server goes on the
   page through esc() - site names, issue texts and plan items are data. */
window.HoolaEmployees = function ({api, esc, toast, changed}) {
  let HUB = null, DESK = null, TIMER = null;
  const TRUST = {seekh: ['Seekh', 'asks you before every change outside Hoola'],
                 saathi: ['Saathi', 'does small, undoable changes and tells you the same day'],
                 bharosa: ['Bharosa', 'works on its own inside your limits; weekly summary']};
  const WS = {technical: 'Technical', content: 'Content', local: 'Local', authority: 'Authority', ai_search: 'AI search', reporting: 'Reporting'};
  const COLS = [['planned', 'Planned'], ['doing', 'Doing'], ['waiting_her', 'Waiting for you'], ['done', 'Done']];
  const STATE = {first_run: ['v', 'First check running'], ready: ['ok', 'Working'], error: ['bad', 'Stopped'], new: ['warn', 'Starting']};
  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const tag = (c, n) => `<span class="tag ${c}">${esc(n)}</span>`;
  const when = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? '–' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const num = v => (v === null || v === undefined || v === '') ? '–' : (typeof v === 'number' ? v.toLocaleString('en-IN', {maximumFractionDigits: 1}) : esc(String(v)));
  const visible = el => el && el.isConnected && !el.closest('.view')?.hidden;

  // ------------------------------------------------------------ the hub
  async function hub(el) {
    HUB = el;
    if (!el.firstChild) el.innerHTML = '<div class="vh"><h2>Employees</h2></div><div class="empty">Loading…</div>';
    let d;
    try { d = await api('GET', '/api/employees'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>Employees</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    changed(d.hired || {});
    el.innerHTML = `<div class="vh"><h2>Employees</h2><span class="muted em-sub">Hire an AI employee for one job. It gets its own desk and works 24/7; you stay in charge.</span></div>
      <div class="em-grid">${(d.employees || []).map(card).join('')}</div>`;
    el.querySelectorAll('[data-em]').forEach(b => b.addEventListener('click', () => act(b.dataset.em, b.dataset.key)));
  }

  function card(e) {
    const hired = e.status === 'hired' || e.status === 'paused';
    const st = e.status === 'hired' ? tag('ok', 'Working') : e.status === 'paused' ? tag('warn', 'Paused') : !e.live ? tag('', 'Coming soon') : '';
    const list = (t, xs) => xs && xs.length ? `<h4>${esc(t)}</h4><ul>${xs.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
    let btns = '';
    if (!e.live) btns = '<button class="btn soft" type="button" disabled>Coming soon</button>';
    else if (!hired) btns = `<button class="btn go" type="button" data-em="hire" data-key="${esc(e.key)}">Hire ${esc(e.name)}</button>`;
    else btns = `<button class="btn go" type="button" data-em="open" data-key="${esc(e.key)}">Open desk</button>
      <button class="btn soft" type="button" data-em="${e.status === 'paused' ? 'resume' : 'pause'}" data-key="${esc(e.key)}">${e.status === 'paused' ? 'Resume' : 'Pause'}</button>
      <button class="btn soft em-leave" type="button" data-em="leave" data-key="${esc(e.key)}">Let go</button>`;
    return `<article class="tile gl em-card${e.live ? '' : ' em-soon'}"><div class="em-h"><h3>${esc(e.name)}</h3>${st}</div>
      <p class="em-pitch">${esc(e.pitch || '')}</p>${list('What it does', e.does)}${list('What it needs', e.needs)}${list('What it will never do', e.never)}
      <div class="acts">${btns}</div></article>`;
  }

  async function act(what, key) {
    if (what === 'open') { location.hash = ''; document.querySelector(`[data-v="${key}desk"]`)?.click(); return; }
    if (what === 'leave' && !confirm('Let go of this employee? Its jobs stop at once. Its history stays, read-only.')) return;
    try {
      await api('POST', `/api/employees/${encodeURIComponent(key)}/${what}`, what === 'hire' ? {trust: 'seekh'} : undefined);
      toast(what === 'hire' ? 'Hired. Open the desk to set it up.' : what === 'leave' ? 'Let go. Its jobs have stopped.' : what === 'pause' ? 'Paused. No jobs run until you resume.' : 'Back at work.');
    } catch (e) { toast(e.message, true); }
    await hub(HUB);
    if (what === 'hire') document.querySelector(`[data-v="${key}desk"]`)?.click();
  }

  // ------------------------------------------------------------ the SEO desk
  async function desk(el) {
    DESK = el; clearTimeout(TIMER);
    if (!el.firstChild) el.innerHTML = '<div class="vh"><h2>SEO Desk</h2></div><div class="empty">Loading…</div>';
    let d;
    try { d = await api('GET', '/api/seo/desk'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>SEO Desk</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    if (!d.hired) { el.innerHTML = `<div class="vh"><h2>SEO Desk</h2></div><div class="empty">The SEO Specialist is not hired. <button class="btn go" type="button" data-v="hire">Go to Employees</button></div>`; return; }
    if (!d.onboarded) { el.innerHTML = onboardForm(d); wireOnboard(el); return; }
    const [sc, sn] = STATE[d.state] || ['warn', d.state];
    const g = d.google || {};
    el.innerHTML = `<div class="vh"><h2>SEO Desk</h2><span class="muted em-sub">${esc(d.site.name || '')} · <a href="${esc(d.site.url)}" target="_blank" rel="noopener">${esc(d.site.url)}</a></span>
        ${tag(sc, sn)} ${d.status === 'paused' ? tag('warn', 'Paused') : ''} <span class="tag">${esc((TRUST[d.trust] || [d.trust])[0])}</span></div>
      ${g.connected ? '' : `<div class="tile gl em-note"><b>Connect Google</b><span>Search Console (and Analytics, if you use it) give the real numbers: clicks, searches, leads from Google. Read-only.</span>
        <button class="btn go" type="button" id="emGoogle">Connect Google</button></div>`}
      ${d.roadmap_status === 'draft' ? `<div class="tile gl em-note"><b>Your 90-day plan is ready</b><span>${esc(String(d.roadmap_count))} steps from the real audit. Read it below and approve it to start the weekly work.</span>
        <button class="btn go" type="button" id="emApprove">Approve plan</button></div>` : ''}
      <div class="kpis em-kpis">${(d.kpis || []).map(kpi).join('') || '<div class="empty">Numbers appear after the first check.</div>'}</div>
      <p class="muted em-small">Baseline from ${esc(d.baseline?.date || '–')}. Google's own data runs three days behind.</p>
      ${proBlock(d)}
      <div class="tile gl"><div class="em-h"><h3>90-day plan</h3><span class="muted">${d.roadmap_status === 'approved' ? 'Approved' : 'Draft'}</span></div>
        <div class="em-board">${COLS.map(([k, n]) => col(k, n, d.board?.[k] || [])).join('')}</div></div>
      <div class="grid2">
        <div class="tile gl"><h3>Activity and alerts</h3>${feed(d.events || [])}</div>
        <div class="tile gl"><h3>Runs 24/7</h3>${sched(d.schedule || [])}
          <div class="acts em-run"><button class="btn soft" type="button" data-run="weekly">Full check now</button>
            <button class="btn soft" type="button" data-run="daily">Refresh numbers</button>
            <button class="btn soft" type="button" data-run="monthly">Monthly report now</button>
            <button class="btn soft" type="button" data-run="roadmap">Rewrite plan draft</button>
            <button class="btn soft" type="button" data-run="index">Check Google index</button></div></div>
      </div>
      <div class="tile gl"><h3>Open fixes on the website</h3>${fixes(d.open_tasks || [])}</div>
      ${indexNow(d)}`;
    wireDesk(el, d);
    if (d.state === 'first_run') TIMER = setTimeout(() => { if (visible(el)) desk(el); }, 10000);
  }

  function kpi(k) {
    const ch = k.change_pct === null || k.change_pct === undefined ? '' :
      `<i class="${k.good ? 'okc' : 'badc'}">${k.change_pct >= 0 ? '+' : ''}${esc(String(k.change_pct))}%</i>`;
    return `<div class="kpi gl"><b>${num(k.now)}</b><span>${esc(k.name)}</span><small>from ${num(k.baseline)} ${ch}</small></div>`;
  }

  function col(k, n, items) {
    return `<div class="em-col"><h4>${esc(n)} <span class="muted">${items.length}</span></h4>${items.map(it => `
      <div class="em-item"><div class="em-meta"><span class="tag">${esc(WS[it.workstream] || it.workstream)}</span><span class="muted">Week ${esc(String(it.week))}${it.owner === 'her' ? ' · needs you' : ''}</span></div>
        <b>${esc(it.title)}</b>${it.why ? `<p class="muted">${esc(it.why)}</p>` : ''}
        ${it.signal ? `<details class="em-env"><summary>How we'll know</summary><p><b>Early sign:</b> ${esc(it.signal)}</p><p><b>Not working if:</b> ${esc(it.fail_check || '')}</p></details>` : ''}
        <select data-item="${esc(it.id)}" aria-label="Status">${[...COLS, ['skipped', 'Skipped']].map(([v, l]) => `<option value="${v}"${v === it.status ? ' selected' : ''}>${l}</option>`).join('')}</select></div>`).join('') || '<p class="muted em-small">Nothing here.</p>'}</div>`;
  }

  function feed(ev) {
    if (!ev.length) return '<div class="empty">Nothing yet.</div>';
    const c = {bad: 'bad', warn: 'warn', ok: 'ok', info: ''};
    return `<ul class="em-feed">${ev.map(e => `<li><span class="tag ${c[e.level] || ''}">${esc(e.kind)}</span><span>${esc(e.text)}</span><time class="muted">${esc(when(e.at))}</time></li>`).join('')}</ul>`;
  }

  function sched(s) {
    return `<table class="em-tbl"><thead><tr><th>Job</th><th>When</th><th>Last run</th></tr></thead><tbody>${s.map(x =>
      `<tr><td>${esc(x.job)}</td><td>${esc(x.every)}</td><td class="muted">${esc(when(x.last))}</td></tr>`).join('')}</tbody></table>`;
  }

  function fixes(t) {
    if (!t.length) return '<div class="empty">No open fixes.</div>';
    const c = {bad: 'bad', warn: 'warn', info: ''};
    const pc = {critical: 'bad', high: 'bad', medium: 'warn', low: ''};
    return `<table class="em-tbl"><thead><tr><th>Priority</th><th>Page</th><th>Problem</th><th>Fix</th></tr></thead><tbody>${t.slice(0, 20).map(x =>
      `<tr><td><span class="tag ${x.priority ? (pc[x.priority] || '') : (c[x.level] || '')}">${esc(x.priority || x.level)}</span></td><td class="em-url">${esc(x.url.replace(/^https?:\/\/[^/]+/, '') || '/')}</td><td>${esc(x.text)}</td><td class="muted">${esc(x.fix)}</td></tr>`).join('')}</tbody></table>`;
  }

  function onboardForm(d) {
    return `<div class="vh"><h2>SEO Desk</h2><span class="muted em-sub">Five questions, then your SEO Specialist starts: full website check, Google numbers, a baseline and a 90-day plan.</span></div>
      <form class="tile gl ar-form em-form" id="emOn" autocomplete="off">
        <div class="ar-fields em-fields">
          <label><span>Website address</span><input id="emUrl" required placeholder="yourbusiness.in"></label>
          <label><span>Business name</span><input id="emName" placeholder="Sharma Dental Clinic"></label>
          <label><span>City</span><input id="emCity" placeholder="Nagpur"></label>
          <label><span>What you sell (comma separated)</span><input id="emSvc" placeholder="Root canal, implants, braces"></label>
          <label class="em-wide"><span>What do you want from Google?</span><input id="emGoal" placeholder="More calls for implants in Nagpur"></label>
          <label class="em-wide"><span>Who are your customers?</span><input id="emCust" placeholder="Families and office workers in Dharampeth and Sadar"></label>
          <label class="em-wide"><span>Competitors' websites (optional, comma separated)</span><input id="emComp" placeholder="smiledental.in, citydentist.in"></label>
          <label><span>Weekly note on</span><select id="emDay">${DAYS.map((n, i) => `<option value="${i}">${n}</option>`).join('')}</select></label>
          <label><span>At</span><input id="emTime" type="time" value="09:30"></label>
        </div>
        <fieldset class="em-trust"><legend>How much may it do on its own?</legend>${['seekh', 'saathi'].map(k => `
          <label><input type="radio" name="emTrust" value="${k}"${k === (d.trust || 'seekh') ? ' checked' : ''}> <b>${TRUST[k][0]}</b> <span class="muted">${TRUST[k][1]}</span></label>`).join('')}
          <p class="muted em-small">In this version it only reads and reports; changes to your site come in the next phase, always within this setting.</p></fieldset>
        <div class="acts"><button class="btn go" type="submit">Start work</button></div>
      </form>`;
  }

  function wireOnboard(el) {
    el.querySelector('#emOn').addEventListener('submit', async ev => {
      ev.preventDefault();
      const v = id => el.querySelector(id).value.trim();
      const btn = el.querySelector('#emOn button[type=submit]'); btn.disabled = true;
      try {
        const r = await api('POST', '/api/seo/onboard', {url: v('#emUrl'), name: v('#emName'), city: v('#emCity'), services: v('#emSvc'),
          goal: v('#emGoal'), customers: v('#emCust'), competitors: v('#emComp'), weekday: Number(v('#emDay')), morning_time: v('#emTime'),
          trust: el.querySelector('input[name=emTrust]:checked')?.value || 'seekh'});
        toast(r.say || 'Started.');
        el.innerHTML = ''; desk(el);
      } catch (e) { toast(e.message, true); btn.disabled = false; }
    });
  }

  // v0.319 SEO PRO: health in 7 parts, Google index, AI search bots, trust (E-E-A-T), local score, speed, screenshots
  function proBlock(d) {
    const p = d.pro || {}, h = p.health;
    if (!h) return '';
    const bar = (lbl, sc, mx, unit) => `<div class="em-bar"><span>${esc(lbl)}</span><i><b style="width:${Math.max(0, Math.min(100, Math.round(100 * sc / (mx || 100))))}%"></b></i><em>${sc === null || sc === undefined ? '–' : esc(String(sc))}${unit ? ' ' + unit : (mx && mx !== 100 ? '/' + mx : '')}</em></div>`;
    const ix = d.index || {}, bots = p.ai_bots || [], e = p.eeat || {}, lo = p.local || {}, c = (d.latest || {}).cwv || {};
    const kinds = {google: 'Google', search: 'AI search', user: 'On request', training: 'Training only'};
    const train = bots.filter(b => b.kind === 'training');
    const botRow = b => `<tr><td>${esc(b.bot)}</td><td class="muted">${esc(kinds[b.kind] || b.kind)}</td><td><span class="tag ${b.allowed ? 'ok' : (b.kind === 'training' ? '' : 'bad')}">${b.allowed ? 'Allowed' : 'Blocked'}</span></td></tr>`;
    const shots = d.shots || {};
    const weeks = (d.crux || {}).weeks || [];
    const spark = weeks.length > 1 ? (() => {
      const v = weeks.map(w => w.lcp_ms || 0), mx = Math.max(...v, 2500), W = 220, H = 40;
      const pts = v.map((x, i) => `${Math.round(i * W / (v.length - 1))},${Math.round(H - x * H / mx)}`).join(' ');
      return `<svg class="em-spark" viewBox="0 0 ${W} ${H}" role="img" aria-label="Loading time over ${weeks.length} weeks"><line x1="0" x2="${W}" y1="${Math.round(H - 2500 * H / mx)}" y2="${Math.round(H - 2500 * H / mx)}" class="em-good"/><polyline points="${pts}"/></svg>`;
    })() : '';
    return `<div class="grid2 em-pro">
      <div class="tile gl em-health"><div class="em-h"><h3>Website health</h3><b class="em-big">${esc(String(h.total))}<small>/100</small></b></div>
        <p class="muted em-small">${['critical', 'high', 'medium', 'low'].map(k => `${h.counts?.[k] || 0} ${k}`).join(' · ')}</p>
        ${(h.parts || []).map(x => bar(`${x.label} (${x.weight})`, x.score, 100)).join('')}
        ${ix.checked ? `<p class="em-small"><b>${esc(String(ix.indexed))} of ${esc(String(ix.checked))}</b> key pages are in Google's index (Google's own answer).</p>` : ''}</div>
      <div class="tile gl"><h3>AI search</h3><p class="muted em-small">Search bots decide if ChatGPT, Claude or Perplexity can show you. Blocking training bots is your choice and costs nothing in search.</p>
        <table class="em-tbl em-bots"><tbody>${bots.filter(b => b.kind !== 'training').map(botRow).join('')}</tbody></table>
        ${train.length ? `<details class="em-env"><summary>Training-only bots: ${train.filter(b => b.allowed).length} allowed, ${train.filter(b => !b.allowed).length} blocked</summary>
          <table class="em-tbl em-bots"><tbody>${train.map(botRow).join('')}</tbody></table></details>` : ''}</div>
      <div class="tile gl"><div class="em-h"><h3>Trust signals (E-E-A-T)</h3><b class="em-big">${esc(String(e.total ?? '–'))}<small>/100</small></b></div>
        ${(e.parts || []).map(x => `<details class="em-env"><summary>${bar(x.key[0].toUpperCase() + x.key.slice(1), x.score, x.max)}</summary><ul>${x.signals.map(s => `<li class="${s.ok ? 'okc' : 'muted'}">${s.ok ? '✓' : '–'} ${esc(s.text)}</li>`).join('')}</ul></details>`).join('')}</div>
      <div class="tile gl"><div class="em-h"><h3>Local search</h3><b class="em-big">${esc(String(lo.total ?? '–'))}<small>/100</small></b></div>
        ${(lo.parts || []).map(x => bar(x.label, x.score, x.max)).join('')}<p class="muted em-small">${esc(lo.note || '')}</p></div>
      <div class="tile gl"><h3>Speed on phones</h3>
        ${c.lcp_ms ? `<p class="em-small">Main content shows in <b>${(c.lcp_ms / 1000).toFixed(1)} s</b> (good is 2.5 s or less).</p>` : '<p class="muted em-small">Speed appears after the weekly check.</p>'}
        ${(c.lcp_parts || []).map(x => bar(x.label, x.ms, Math.max(...c.lcp_parts.map(y => y.ms)), 'ms')).join('')}
        ${spark ? `<p class="muted em-small">Real visitors, last ${weeks.length} weeks (Chrome). The line under the curve is the 2.5 s mark.</p>${spark}` : ''}</div>
      ${shots.mobile || shots.desktop ? `<div class="tile gl"><h3>How Google sees it</h3><div class="em-shots">${['mobile', 'desktop'].filter(k => shots[k]).map(k =>
        `<figure class="em-shot em-shot-${k}"><img src="${esc(shots[k].img)}" alt="${k} screenshot of your home page" loading="lazy"><figcaption class="muted">${k === 'mobile' ? 'Phone' : 'Computer'} · ${esc(when(shots[k].at))}</figcaption></figure>`).join('')}</div></div>` : ''}
    </div>`;
  }

  function indexNow(d) {
    const key = (d.indexnow || {}).key;
    return `<div class="tile gl em-note"><b>IndexNow</b><span>${key ? `Put a file named <code>${esc(key)}.txt</code> containing only <code>${esc(key)}</code> at the top of your website. Then changed pages go to Bing and other engines every week.` :
      'Tell Bing and other IndexNow engines about changed pages every week. Google does not use it; your Search Console covers Google.'}</span>
      <button class="btn soft" type="button" id="emIndexNow">${key ? 'Check the file' : 'Turn on'}</button></div>`;
  }

  function wireDesk(el, d) {
    el.querySelector('#emIndexNow')?.addEventListener('click', async () => {
      try { const r = await api('POST', '/api/seo/run/indexnow', {}); toast(r.say, !r.live); desk(el); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelector('#emGoogle')?.addEventListener('click', async () => {
      try { const r = await api('GET', '/api/seo/gsc/link'); window.open(r.url, '_blank', 'noopener'); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelector('#emApprove')?.addEventListener('click', async () => {
      try { await api('POST', '/api/seo/roadmap/approve', {}); toast('Plan approved. Work starts this week.'); desk(el); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelectorAll('select[data-item]').forEach(s => s.addEventListener('change', async () => {
      try { await api('POST', `/api/seo/roadmap/item/${encodeURIComponent(s.dataset.item)}`, {status: s.value}); desk(el); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-run]').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true;
      try {
        await api('POST', `/api/seo/run/${b.dataset.run}`, {});
        toast({weekly: 'Full check started. Results land here in a few minutes.', daily: 'Refreshing the Google numbers.',
               monthly: 'Making the report. The PDF arrives in your chat.', roadmap: 'Plan draft rewritten.',
               index: 'Asking Google about your key pages. Results land here in a minute.'}[b.dataset.run]);
        if (b.dataset.run === 'roadmap') desk(el);
      } catch (e) { toast(e.message, true); }
      b.disabled = false;
    }));
  }

  return {hub, desk};
};
