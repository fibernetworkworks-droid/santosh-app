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
    const groups = {};                                    // v0.357 cards grouped (Business / Research, CAD, Hardware & Industrial Tech)
    for (const e of d.employees || []) (groups[e.group || 'Business'] ||= []).push(e);
    el.innerHTML = `<div class="vh"><h2>Employees</h2><span class="muted em-sub">Hire an AI employee for one job. It gets its own desk and works 24/7; you stay in charge.</span></div>
      ${Object.entries(groups).map(([g, xs]) => `<h3 class="em-group">${esc(g)}</h3><div class="em-grid">${xs.map(card).join('')}</div>`).join('')}`;
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
    if (what === 'open') { location.hash = ''; document.querySelector(`[data-v="${key}desk"]`)?.click(); return; }   // seodesk / socialdesk
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

  // ------------------------------------------------------------ v0.353 the Social Desk (Social Media Manager, Phase 1)
  let SOC = null, SOCTRUST = 'seekh';
  const PLAT = {instagram: 'Instagram', facebook: 'Facebook Page'};
  const PST = {draft: ['warn', 'Draft'], approved: ['ok', 'Approved'], skipped: ['', 'Skipped']};
  const DONE = {publishing: ['v', 'Posting…'], published: ['ok', 'Posted'], failed: ['bad', 'Not posted'], missed: ['', 'Missed']};   // v0.355
  async function social(el) {
    SOC = el; clearTimeout(TIMER);
    if (!el.firstChild) el.innerHTML = '<div class="vh"><h2>Social Desk</h2></div><div class="empty">Loading…</div>';
    let d;
    try { d = await api('GET', '/api/social/desk'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>Social Desk</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    if (!d.hired) { el.innerHTML = `<div class="vh"><h2>Social Desk</h2></div><div class="empty">The Social Media Manager is not hired. <button class="btn go" type="button" data-v="hire">Go to Employees</button></div>`; return; }
    if (!d.onboarded) { el.innerHTML = socialForm(d); wireSocialForm(el); return; }
    const [sc, sn] = STATE[d.state] || ['warn', d.state];
    const accs = d.accounts || [], b = d.baseline || {}, stg = d.strategy || {}, cal = d.calendar || [];
    const pl = d.pulse || {}, pst = pl.settings || {};
    SOCTRUST = d.trust || 'seekh';
    el.innerHTML = `<div class="vh"><h2>Social Desk</h2><span class="muted em-sub">${esc(d.profile.business || '')}${d.profile.city ? ' · ' + esc(d.profile.city) : ''}</span>
        ${accs.length ? tag(sc, sn) : tag('warn', 'Connect an account')} ${d.status === 'paused' ? tag('warn', 'Paused') : ''} <span class="tag">${esc((TRUST[d.trust] || [d.trust])[0])}</span></div>
      <div class="tile gl"><div class="em-h"><h3>Accounts</h3><span class="muted em-small">You log in on Instagram / Facebook's own page. Hoola never sees your password.</span></div>
        <div class="sc-accs">${accs.map(a => `<div class="sc-acc">${a.picture ? `<img src="${esc(a.picture)}" alt="" loading="lazy">` : '<span class="sc-pic"></span>'}
          <div><b>${esc(a.handle || a.name)}</b><span class="muted">${esc(PLAT[a.platform] || a.platform)} · ${num(a.followers)} followers</span>
          ${a.status !== 'ok' ? `<span class="badc em-small">${esc(a.status === 'expired' ? 'Connection ended: connect again' : a.error || a.status)}</span>` : ''}
          ${a.status === 'ok' && (a.can_post === false || a.can_reply === false) ? '<span class="warnc em-small">Reconnect to allow posting and replies</span>' : ''}</div>
          <button class="btn soft" type="button" data-scoff="${esc(a.id)}">Disconnect</button></div>`).join('')}
        <div class="sc-connect">${['instagram', 'facebook'].map(p => d.connect[p]
          ? `<button class="btn ${accs.some(a => a.platform === p) ? 'soft' : 'go'}" type="button" data-scon="${p}">${accs.some(a => a.platform === p) ? 'Reconnect' : 'Connect'} ${PLAT[p]}</button>`
          : `<button class="btn soft" type="button" disabled title="The server needs Hoola's Meta app keys">${PLAT[p]}: not set up on the server yet</button>`).join('')}</div>
        <p class="muted em-small">Instagram must be a Business or Creator account (free switch in Instagram settings). A post goes out only when you approve it or tap Publish now: exactly what you approved, at its time.</p></div>
      ${d.calendar_status === 'draft' && cal.length ? `<div class="tile gl em-note"><b>Your 30-day calendar is ready</b><span>${cal.length} posts planned from your real numbers. Read them below, edit any, then approve.</span>
        <button class="btn go" type="button" id="scApprove">Approve calendar</button></div>` : ''}
      ${accs.length && pst.paused ? `<div class="tile gl em-note sc-paused"><b>Posting is paused</b><span>${esc(pst.pause_reason || 'Nothing goes out and no reply is sent on its own until you resume.')}</span>
        <button class="btn go" type="button" data-scpause="0">Resume</button></div>` : ''}
      ${accs.length && (pl.waiting_ok || []).length ? `<div class="tile gl em-note"><b>${pl.waiting_ok.length} planned post(s) wait for your OK today</b><span>Read each below and tap OK to post (Seekh). Saathi lets approved plan posts go on their own.</span></div>` : ''}
      ${accs.length ? `<div class="tile gl sc-inbox" id="scInbox"><div class="em-h"><h3>Inbox: comments + DMs</h3>
          <span class="muted em-small">Sorted for you; every reply is drafted from your facts. ${d.trust === 'seekh' ? 'Nothing goes without your tap.' : 'Simple replies go on their own (your trust setting); complaints always wait for you.'}</span></div>
        <div class="sc-tabs" role="tablist">${Object.entries(BOX).map(([k, l]) => `<button class="btn ${k === BOXNOW ? 'go' : 'soft'}" type="button" role="tab" aria-selected="${k === BOXNOW}" data-scbox="${k}">${l}${k === 'done' ? '' : ` <span class="sc-n">${num((d.inbox || {})[k] || 0)}</span>`}</button>`).join('')}
          <button class="btn soft" type="button" data-scrun="inbox">Check now</button></div>
        <div class="sc-items" id="scItems"><div class="empty">Loading…</div></div></div>` : ''}
      ${accs.length ? `<div class="kpis em-kpis">${(d.kpis || []).map(kpi).join('') || '<div class="empty">Numbers appear after the first read.</div>'}</div>
      <p class="muted em-small">Baseline from ${esc(b.date || '–')}${b.posts_read ? ` · ${num(b.posts_read)} posts read` : ''}.</p>` : ''}
      ${stg.pillars ? `<div class="grid2">
        <div class="tile gl"><h3>Strategy</h3>${stg.goal_metric ? `<p class="em-small"><b>Judged on:</b> ${esc(stg.goal_metric)}</p>` : ''}
          <div class="sc-pills">${(stg.pillars || []).map(p => `<span class="tag" title="${esc(p.why || '')}">${esc(p.name)}</span>`).join('')}</div>
          <p class="em-small">${num((stg.rhythm || {}).feed_per_week)} feed posts + ${num((stg.rhythm || {}).stories_per_week)} Stories a week · best hours ${(stg.best_hours || b.best_hours || []).map(h => esc(String(h).padStart(2, '0') + ':00')).join(', ')}</p>
          <p class="muted em-small">${(stg.hashtags || []).map(esc).join(' ')}</p></div>
        <div class="tile gl"><h3>What works for you</h3>${(b.formats || []).length ? `<table class="em-tbl"><tbody>${b.formats.map(f => `<tr><td>${esc(f.fmt)}</td><td class="muted">${num(f.posts)} posts</td><td>${num(f.avg_eng)} interactions</td></tr>`).join('')}</tbody></table>` : '<div class="empty">After the first read.</div>'}
          ${(b.top_posts || []).slice(0, 3).map(t => `<p class="em-small"><a href="${esc(t.permalink)}" target="_blank" rel="noopener">${esc(t.fmt)} · ${num(t.eng)} interactions</a> <span class="muted">${esc((t.caption || '').slice(0, 80))}</span></p>`).join('')}</div>
      </div>` : ''}
      ${accs.length ? `<div class="grid2">
        <div class="tile gl"><h3>Posting controls</h3>
          <p class="em-small">${pst.paused ? tag('warn', 'Paused') : tag('ok', 'Posting on')} ${SOCTRUST === 'seekh' ? 'Every plan post waits for your OK.' : `Plan posts go on their own: ${num(pl.auto_today || 0)} of ${num(pl.post_cap || 0)} today.`}</p>
          <div class="sc-quiet"><label>No posts on their own from <input type="number" min="0" max="23" id="scQ0" value="${esc(String((pst.quiet || [23, 7])[0]))}"></label>
            <label>to <input type="number" min="0" max="23" id="scQ1" value="${esc(String((pst.quiet || [23, 7])[1]))}"></label>
            <button class="btn soft" type="button" id="scQSave">Save</button></div>
          <div class="acts em-run">${pst.paused ? '<button class="btn go" type="button" data-scpause="0">Resume posting</button>' : '<button class="btn soft" type="button" data-scpause="1">Pause all posting</button>'}
            <button class="btn soft sc-stop" type="button" id="scStop">Emergency stop</button></div>
          <p class="muted em-small">Pause also stops automatic replies. Emergency stop sends every queued post back to draft.</p></div>
        <div class="tile gl"><h3>Best times for you</h3>${(pl.best_times || {}).slots && pl.best_times.slots.length
          ? `<table class="em-tbl"><tbody>${pl.best_times.slots.map(x => `<tr><td>${esc(x.day)} ${esc(x.band)}</td><td>${esc(String(x.lift))}x your normal</td><td class="muted">${num(x.posts)} posts</td></tr>`).join('')}</tbody></table>
            <p class="muted em-small">Certainty: ${esc(pl.best_times.sure)}. New calendars use these times.</p>`
          : `<div class="empty">${esc((pl.best_times || {}).note || 'After a few more posts.')}</div>`}
          ${(pl.boosts || []).length ? `<h3 class="sc-h">Worth a boost</h3>${pl.boosts.map(x => `<p class="em-small"><a href="${esc(x.permalink)}" target="_blank" rel="noopener">${esc(x.fmt)} · ${esc(x.date)}</a> <b>${esc(String(x.times))}x</b> your normal. <span class="muted">${esc(x.plan)}</span></p>`).join('')}` : ''}</div>
      </div>` : ''}
      ${accs.length ? growthTile(d.growth || {}) : ''}
      ${cal.length ? `<div class="tile gl"><div class="em-h"><h3>Calendar</h3><span class="muted">${esc(d.calendar_status === 'approved' ? 'Approved' : 'Draft')}</span></div>
        <div class="sc-cal">${cal.map(post).join('')}</div></div>` : ''}
      <div class="grid2">
        <div class="tile gl"><h3>Activity</h3>${feed(d.events || [])}</div>
        <div class="tile gl"><h3>Runs 24/7</h3>${sched(d.schedule || [])}
          <div class="acts em-run"><button class="btn soft" type="button" data-scrun="daily">Refresh numbers</button>
            <button class="btn soft" type="button" data-scrun="plan">Rewrite calendar draft</button>
            <button class="btn soft" type="button" data-scrun="monthly">Make this month's PDF</button></div></div>
      </div>`;
    wireSocial(el, d);
    wireGrowth(el);
    if (accs.length) inbox(el);
    if (d.state === 'first_run') TIMER = setTimeout(() => { if (visible(el)) social(el); }, 8000);
  }

  function post(p) {
    const [c, n] = PST[p.status] || DONE[p.status] || ['', p.status];
    const done = ['published', 'publishing'].includes(p.status);
    const res = p.result || {};
    const dt = new Date(p.slot);
    const day = isNaN(dt) ? p.slot : dt.toLocaleString('en-IN', {weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'});
    const needOk = p.plan_only && SOCTRUST === 'seekh';   // v0.369 Seekh: a plan post waits for her OK on its day
    return `<div class="em-item sc-post" data-pid="${esc(p.id)}"><div class="em-meta"><b>${esc(day)}</b>${tag(c, n)}${needOk ? tag('warn', 'Needs your OK') : ''}<span class="tag">${esc(p.format)}</span>
        <span class="muted">${(p.platforms || []).map(x => esc(PLAT[x] || x)).join(' + ')}${p.pillar ? ' · ' + esc(p.pillar) : ''}${p.occasion ? ' · ' + esc(p.occasion) : ''}</span></div>
      <b>${esc(p.hook)}</b>
      <details class="em-env"><summary>Caption, hashtags and picture brief</summary><p class="sc-cap">${esc(p.caption)}</p>
        <p class="muted">${(p.hashtags || []).map(esc).join(' ')}</p>${p.visual ? `<p><b>Picture / video:</b> ${esc(p.visual)}</p>` : ''}${p.cta ? `<p><b>Ask:</b> ${esc(p.cta)}</p>` : ''}
        <textarea class="sc-edit" rows="5" aria-label="Edit caption" hidden>${esc(p.caption)}</textarea></details>
      ${(p.media || []).length ? `<div class="sc-media">${p.media.map(m => m.kind === 'video'
          ? `<span class="sc-vid" title="Video">▶</span>` : `<img src="${esc(m.url)}" alt="Picture for this post" loading="lazy">`).join('')}</div>` : ''}
      ${Object.entries(res).map(([pl, r]) => r.link ? `<p class="em-small okc">Posted on <a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(PLAT[pl] || pl)}</a></p>`
          : r.error ? `<p class="em-small badc">${esc(PLAT[pl] || pl)}: ${esc(r.error)}</p>` : '').join('')}
      ${!done && (p.problems || []).length ? `<p class="em-small warnc">${(p.problems || []).map(esc).join(' ')}</p>` : ''}
      ${done ? '' : `<div class="acts"><select data-scst="${esc(p.id)}" aria-label="Status">${Object.entries(PST).map(([v, [, l]]) => `<option value="${v}"${v === p.status ? ' selected' : ''}>${l}</option>`).join('')}${DONE[p.status] ? `<option selected disabled>${esc(DONE[p.status][1])}</option>` : ''}</select>
        <button class="btn soft" type="button" data-sccopy="${esc(p.id)}">Copy caption</button><button class="btn soft" type="button" data-scedit="${esc(p.id)}">Edit</button>
        <label class="btn soft sc-up">Add photo / video<input type="file" accept="image/*,video/mp4,video/quicktime" data-scup="${esc(p.id)}" hidden></label>
        <button class="btn soft" type="button" data-scposter="${esc(p.id)}">Make poster</button>
        ${needOk ? `<button class="btn go" type="button" data-scok="${esc(p.id)}">OK to post</button>` : ''}
        <button class="btn ${needOk ? 'soft' : 'go'}" type="button" data-scpub="${esc(p.id)}"${(p.problems || []).length ? ' disabled' : ''}>Publish now</button></div>`}</div>`;
  }

  // ------------------------------------------------------------ v0.370 growth (Phase 5)
  const UGS = {new: ['warn', 'New'], asked: ['v', 'Asked'], granted: ['ok', 'They said yes'], refused: ['', 'They said no'],
               reposted: ['ok', 'Draft made'], ignored: ['', 'Ignored']};
  function growthTile(g) {
    const w = g.watch || {hashtags: [], competitors: []}, ab = g.ab || {}, lk = g.link || {};
    const comp = c => { const l = c.last || {}, p = c.prev || {};
      const df = l.followers != null && p.followers != null ? l.followers - p.followers : null;
      return `<tr><td>@${esc(l.username || c.name)}</td><td>${l.followers != null ? num(l.followers) + (df ? ` <span class="muted">(${df > 0 ? '+' : ''}${num(df)})</span>` : '') : '–'}</td>
        <td>${l.posts_7d != null ? num(l.posts_7d) : '–'}</td><td>${l.avg_eng != null ? num(l.avg_eng) : '–'}</td><td>${esc(((l.formats || [])[0] || {}).fmt || '–')}</td></tr>
        ${c.error ? `<tr><td colspan="5" class="badc em-small">${esc(c.error)}</td></tr>` : ''}`; };
    const htag = h => { const l = h.last || {};
      return `<div class="em-item"><b>#${esc(h.name)}</b> <span class="muted">${l.posts ? `${num(l.avg_eng)} interactions a top post · best ${esc(((l.formats || [])[0] || {}).fmt || '–')}` : esc(h.error || 'Read on Monday')}</span>
        ${(l.ideas || []).map(i => `<p class="em-small"><a href="${esc(i.permalink)}" target="_blank" rel="noopener">${esc(i.fmt)} · ${num(i.eng)}</a> <span class="muted">${esc(i.line)}</span></p>`).join('')}</div>`; };
    const ug = u => { const [c, n] = UGS[u.status] || ['', u.status];
      return `<div class="em-item sc-ugc" data-uid="${esc(u.id)}"><div class="em-meta"><b>@${esc(u.username)}</b>${tag(c, n)}<a class="muted" href="${esc(u.permalink)}" target="_blank" rel="noopener">open post</a></div>
        <p class="em-small">${esc((u.caption || '').slice(0, 160))}</p>${u.proof ? `<p class="em-small okc">Their yes: ${esc(u.proof)}</p>` : ''}${u.error ? `<p class="em-small badc">${esc(u.error)}</p>` : ''}
        <div class="acts">${['new', 'asked', 'refused'].includes(u.status) ? `<button class="btn soft" type="button" data-ugask="${esc(u.id)}">${u.status === 'new' ? 'Ask to repost' : 'Ask again'}</button>` : ''}
          ${['new', 'asked'].includes(u.status) ? `<button class="btn soft" type="button" data-ugyes="${esc(u.id)}">They said yes</button>` : ''}
          ${u.status === 'granted' ? `<button class="btn go" type="button" data-ugrepost="${esc(u.id)}">Make a credited draft</button>` : ''}
          ${!['reposted', 'ignored'].includes(u.status) ? `<button class="btn soft" type="button" data-ugignore="${esc(u.id)}">Ignore</button>` : ''}</div></div>`; };
    return `<div class="tile gl sc-growth"><div class="em-h"><h3>Growth</h3><span class="muted em-small">${lk.ok ? `Listening through your Page's Instagram @${esc(lk.username)}.` : esc(lk.reason || '')} Public business data only, never scraping.</span></div>
      <div class="grid2"><div>
        <h3 class="sc-h">Competitors</h3>${w.competitors.length ? `<table class="em-tbl"><thead><tr><th>Account</th><th>Followers</th><th>Posts this week</th><th>Interactions a post</th><th>Best format</th></tr></thead><tbody>${w.competitors.map(comp).join('')}</tbody></table>` : '<div class="empty">Add up to 5 Instagram business accounts you compete with.</div>'}
        <h3 class="sc-h">Hashtags of your niche</h3>${w.hashtags.map(htag).join('') || '<div class="empty">Add up to 5 hashtags.</div>'}
        <form class="ar-form em-form sc-watch" id="scWatch"><label><span>Competitors (usernames, comma separated)</span><input id="scComp" value="${esc(w.competitors.map(c => c.name).join(', '))}" placeholder="smiledentalakola, citydental"></label>
          <label><span>Hashtags (comma separated)</span><input id="scTags" value="${esc(w.hashtags.map(h => h.name).join(', '))}" placeholder="akoladentist, dentalcare"></label>
          <div class="acts"><button class="btn soft" type="submit">Save</button><button class="btn soft" type="button" data-scrun="growth">Check now</button></div></form>
        <h3 class="sc-h">Hook styles (A/B)</h3>${(ab.styles || []).length ? `<table class="em-tbl"><tbody>${ab.styles.map(r => `<tr><td>${esc(r.style)}</td><td>${num(r.posts)} posts</td><td>${num(r.avg_eng)} interactions a post</td></tr>`).join('')}</tbody></table>` : ''}
        <p class="muted em-small">${esc(ab.note || '')}</p>
      </div><div>
        <h3 class="sc-h">Customers tagging you</h3>${(g.ugc || []).map(ug).join('') || '<div class="empty">When customers tag you, their posts appear here. Ask before you repost.</div>'}
        <h3 class="sc-h">Check a creator before a collab</h3>
        <form class="ar-form em-form" id="scCreator"><label><span>Instagram username</span><input id="scCrUser" placeholder="foodie_akola"></label>
          <label><span>Collab caption (optional, checked for #ad)</span><input id="scCrCap"></label><div class="acts"><button class="btn soft" type="submit">Check</button></div></form>
        <div id="scCrOut"></div>
      </div></div></div>`;
  }

  function wireGrowth(el) {
    el.querySelector('#scWatch')?.addEventListener('submit', async ev => {
      ev.preventDefault();
      const list = id => el.querySelector(id).value.split(',').map(x => x.trim()).filter(Boolean);
      try { await api('POST', '/api/social/growth/watch', {competitors: list('#scComp'), hashtags: list('#scTags')}); toast('Saved. Tap Check now or wait for Monday.'); social(el); }
      catch (e) { toast(e.message, true); }
    });
    const act = (sel, key, action, body, done) => el.querySelectorAll(sel).forEach(b => b.addEventListener('click', async () => {
      const bd = typeof body === 'function' ? body() : body; if (bd === null) return;
      b.disabled = true;
      try { await api('POST', `/api/social/ugc/${encodeURIComponent(b.dataset[key])}/${action}`, bd); toast(done); social(el); }
      catch (e) { toast(e.message, true); b.disabled = false; }
    }));
    act('[data-ugask]', 'ugask', 'ask', () => confirm('Post a polite comment from your account asking to repost it with credit?') ? {} : null, 'Asked. When they reply YES, tap They said yes.');
    act('[data-ugyes]', 'ugyes', 'permission', () => { const p = prompt('What did they say, and where? (kept as proof)'); return p ? {granted: true, proof: p} : null; }, 'Saved their yes.');
    act('[data-ugrepost]', 'ugrepost', 'repost', {}, 'A credited draft is in your calendar - approve it like any post.');
    act('[data-ugignore]', 'ugignore', 'ignore', {}, 'Ignored.');
    el.querySelector('#scCreator')?.addEventListener('submit', async ev => {
      ev.preventDefault();
      const out = el.querySelector('#scCrOut'); out.innerHTML = '<div class="empty">Checking…</div>';
      try {
        const r = await api('POST', '/api/social/creator/check', {username: el.querySelector('#scCrUser').value, caption: el.querySelector('#scCrCap').value});
        out.innerHTML = `<div class="em-item"><b>@${esc(r.username)}</b> <span class="muted">${esc(r.name || '')}</span>
          <p class="em-small">${num(r.followers)} followers · ${r.avg_likes != null ? num(r.avg_likes) : '–'} likes + ${r.avg_comments != null ? num(r.avg_comments) : '–'} comments a post${r.eng_rate != null ? ` · ${esc(String(r.eng_rate))}%` : ''}</p>
          ${(r.signals || []).map(x => `<p class="em-small warnc">${esc(x)}</p>`).join('') || '<p class="em-small okc">No warning signals in the public numbers.</p>'}
          ${r.disclosure ? `<p class="em-small">${esc(JSON.stringify(r.disclosure.problems || r.disclosure.issues || r.disclosure).slice(0, 400))}</p>` : ''}
          <p class="muted em-small">${esc(r.note)}</p></div>`;
      } catch (e) { out.innerHTML = `<p class="badc">${esc(e.message)}</p>`; }
    });
  }

  // ------------------------------------------------------------ v0.368 the inbox (Phase 3)
  const BOX = {needs: 'Needs you', leads: 'Leads', complaints: 'Complaints', done: 'Done'};
  const CLS = {lead: ['ok', 'Lead'], question: ['v', 'Question'], praise: ['v', 'Praise'], complaint: ['warn', 'Complaint'],
               spam: ['bad', 'Spam'], abuse: ['bad', 'Abuse'], other: ['', 'Other']};
  let BOXNOW = 'needs';
  async function inbox(el) {
    const box = el.querySelector('#scItems'); if (!box) return;
    let r;
    try { r = await api('GET', `/api/social/inbox?box=${BOXNOW}`); }
    catch (e) { box.innerHTML = `<p class="badc">${esc(e.message)}</p>`; return; }
    box.innerHTML = (r.items || []).map(msg).join('') || `<div class="empty">${BOXNOW === 'needs' ? 'Nothing waiting for you.' : 'Nothing here yet.'}</div>`;
    wireInbox(el, box);
  }

  function msg(m) {
    const [c, n] = CLS[m.cls] || ['', m.cls];
    const open = ['new', 'drafted', 'failed'].includes(m.status);
    const where = `${m.platform === 'instagram' ? 'Instagram' : 'Facebook'} ${m.kind === 'dm' ? 'DM' : 'comment'}`;
    const at = m.at ? new Date(m.at).toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : '';
    const doneLine = m.status === 'replied' ? `<p class="em-small okc">${m.auto ? 'Hoola replied' : 'You replied'}: ${esc(m.reply)}</p>`
      : m.status === 'hidden' ? `<p class="em-small muted">${m.auto ? 'Hidden by Hoola' : 'Hidden'} (not deleted) <button class="btn soft" type="button" data-scunhide="${esc(m.id)}">Unhide</button></p>`
      : `<p class="em-small muted">No reply needed <button class="btn soft" type="button" data-scback="${esc(m.id)}">Bring back</button></p>`;
    return `<div class="em-item sc-msg" data-mid="${esc(m.id)}"><div class="em-meta"><b>${esc(m.author || 'Someone')}</b>${tag(c, n)}
        <span class="muted">${esc(where)}${at ? ' · ' + esc(at) : ''}${m.permalink ? ` · <a href="${esc(m.permalink)}" target="_blank" rel="noopener">post</a>` : ''}</span></div>
      ${m.post ? `<p class="muted em-small sc-on">On: ${esc(m.post)}</p>` : ''}
      <p class="sc-text">${esc(m.text)}</p>
      ${m.note ? `<p class="muted em-small">${esc(m.note)}</p>` : ''}
      ${m.error ? `<p class="badc em-small">${esc(m.error)}</p>` : ''}
      ${open ? (m.dm_closed ? '<p class="warnc em-small">Meta lets a business answer a DM only within 24 hours. Reply from the Instagram / Facebook app yourself.</p>'
          : `<textarea class="sc-reply" rows="2" aria-label="Reply to ${esc(m.author || 'them')}">${esc(m.draft)}</textarea>
        ${m.needs_her ? '<p class="warnc em-small">Check this one: it may need a fact only you know.</p>' : ''}`) +
        `<div class="acts">${m.dm_closed ? '' : `<button class="btn go" type="button" data-scsend="${esc(m.id)}">Send reply</button>`}
          ${m.kind === 'comment' ? `<button class="btn soft" type="button" data-schide="${esc(m.id)}">Hide</button>` : ''}
          <button class="btn soft" type="button" data-scignore="${esc(m.id)}">No reply needed</button></div>` : doneLine}</div>`;
  }

  function wireInbox(el, box) {
    const call = async (b, method, path, body, done) => {
      b.disabled = true;
      try { await api(method, path, body); toast(done); social(el); }
      catch (e) { toast(e.message, true); b.disabled = false; }
    };
    const id = v => encodeURIComponent(v);
    box.querySelectorAll('[data-scsend]').forEach(b => b.addEventListener('click', () => {
      const text = b.closest('.sc-msg').querySelector('.sc-reply').value.trim();
      if (!text) { toast('Write a reply first.', true); return; }
      call(b, 'POST', `/api/social/inbox/${id(b.dataset.scsend)}/reply`, {text}, 'Reply sent.');
    }));
    box.querySelectorAll('[data-schide]').forEach(b => b.addEventListener('click', () =>
      call(b, 'POST', `/api/social/inbox/${id(b.dataset.schide)}/hide`, {hidden: true}, 'Hidden. Nothing deleted.')));
    box.querySelectorAll('[data-scunhide]').forEach(b => b.addEventListener('click', () =>
      call(b, 'POST', `/api/social/inbox/${id(b.dataset.scunhide)}/hide`, {hidden: false}, 'Shown again.')));
    box.querySelectorAll('[data-scignore]').forEach(b => b.addEventListener('click', () =>
      call(b, 'POST', `/api/social/inbox/${id(b.dataset.scignore)}`, {status: 'ignored'}, 'Moved to Done.')));
    box.querySelectorAll('[data-scback]').forEach(b => b.addEventListener('click', () =>
      call(b, 'POST', `/api/social/inbox/${id(b.dataset.scback)}`, {status: 'drafted'}, 'Back in Needs you.')));
  }

  function socialForm(d) {
    const p = d.profile || {};
    return `<div class="vh"><h2>Social Desk</h2><span class="muted em-sub">A few questions, then connect Instagram or your Facebook Page. Your Social Media Manager reads your posts, finds what works and plans the month.</span></div>
      <form class="tile gl ar-form em-form" id="scOn" autocomplete="off">
        <div class="ar-fields em-fields">
          <label><span>Business name</span><input id="scBiz" required value="${esc(p.business || '')}" placeholder="Sharma Dental Clinic"></label>
          <label><span>City</span><input id="scCity" value="${esc(p.city || '')}" placeholder="Nagpur"></label>
          <label class="em-wide"><span>What you sell</span><input id="scSells" value="${esc(p.sells || '')}" placeholder="Root canal, implants, braces"></label>
          <label class="em-wide"><span>Who are your customers?</span><input id="scCust" placeholder="Families and office workers in Dharampeth"></label>
          <label class="em-wide"><span>What do you want from social media?</span><input id="scGoal" placeholder="More WhatsApp enquiries for implants"></label>
          <label class="em-wide"><span>Languages for posts (comma separated)</span><input id="scLang" value="${esc((p.languages || ['Hinglish']).join(', '))}"></label>
          <label class="em-wide"><span>Facts for replies: prices, timings, address, WhatsApp (only these are ever quoted)</span><textarea id="scFacts" rows="3" placeholder="Cleaning Rs 800. Open 10 am - 8 pm, Sunday closed. WhatsApp 98xxxxxx10">${esc(p.facts || '')}</textarea></label>
        </div>
        <fieldset class="em-trust"><legend>How much may it do on its own?</legend>${['seekh', 'saathi'].map(k => `
          <label><input type="radio" name="scTrust" value="${k}"${k === (d.trust || 'seekh') ? ' checked' : ''}> <b>${TRUST[k][0]}</b> <span class="muted">${TRUST[k][1]}</span></label>`).join('')}
          <p class="muted em-small">Posts go out only after your OK. Seekh: every plan post and every reply waits for your tap. Saathi: approved plan posts go on their own (up to 6 a day, never at night) and you are told the same day. Saathi: replies to simple questions, leads and praise from your facts and hides spam (never deletes); complaints always wait for you.</p></fieldset>
        <div class="acts"><button class="btn go" type="submit">Save and continue</button></div>
      </form>`;
  }

  function wireSocialForm(el) {
    el.querySelector('#scOn').addEventListener('submit', async ev => {
      ev.preventDefault();
      const v = id => el.querySelector(id).value.trim();
      const btn = el.querySelector('#scOn button[type=submit]'); btn.disabled = true;
      try {
        await api('POST', '/api/social/onboard', {business: v('#scBiz'), city: v('#scCity'), sells: v('#scSells'), customers: v('#scCust'),
          goal: v('#scGoal'), languages: v('#scLang'), facts: v('#scFacts'), trust: el.querySelector('input[name=scTrust]:checked')?.value || 'seekh'});
        toast('Saved. Now connect Instagram or your Facebook Page.');
        el.innerHTML = ''; social(el);
      } catch (e) { toast(e.message, true); btn.disabled = false; }
    });
  }

  function wireSocial(el, d) {
    el.querySelectorAll('[data-scon]').forEach(b => b.addEventListener('click', async () => {
      try { const r = await api('GET', `/api/social/connect/${b.dataset.scon}`); window.open(r.url, '_blank', 'noopener'); toast('Log in on the page that opened, then come back here.'); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-scoff]').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Disconnect this account? Hoola deletes its token and the posts it read.')) return;
      try { await api('POST', `/api/social/accounts/${encodeURIComponent(b.dataset.scoff)}/disconnect`, {}); social(el); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelector('#scApprove')?.addEventListener('click', async () => {
      try { const r = await api('POST', '/api/social/calendar/approve', {}); toast(`Approved ${r.approved} posts.`); social(el); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelectorAll('[data-scst]').forEach(s => s.addEventListener('change', async () => {
      try { await api('POST', `/api/social/posts/${encodeURIComponent(s.dataset.scst)}`, {status: s.value}); social(el); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-sccopy]').forEach(b => b.addEventListener('click', async () => {
      const p = (d.calendar || []).find(x => x.id === b.dataset.sccopy);
      try { await navigator.clipboard.writeText(`${p.caption}\n\n${(p.hashtags || []).join(' ')}`); toast('Caption copied.'); }
      catch (e) { toast('Could not copy: select the text instead.', true); }
    }));
    el.querySelectorAll('[data-scedit]').forEach(b => b.addEventListener('click', async () => {
      const card = b.closest('.sc-post'), det = card.querySelector('details'), ta = card.querySelector('.sc-edit');
      if (ta.hidden) { det.open = true; ta.hidden = false; ta.focus(); b.textContent = 'Save'; return; }
      try { await api('POST', `/api/social/posts/${encodeURIComponent(b.dataset.scedit)}`, {caption: ta.value}); toast('Saved. An edited post needs your OK again.'); social(el); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-scup]').forEach(inp => inp.addEventListener('change', async () => {
      const f = inp.files && inp.files[0]; if (!f) return;
      const fd = new FormData(); fd.append('file', f);
      try {
        const a = await api('POST', '/api/social/media', undefined, {form: fd});
        await api('POST', `/api/social/posts/${encodeURIComponent(inp.dataset.scup)}/media`, {assets: [a.id]});
        toast('Added. Approve the post again when it looks right.'); social(el);
      } catch (e) { toast(e.message, true); }
    }));
    el.querySelectorAll('[data-scposter]').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true; b.textContent = 'Making…';
      try { await api('POST', `/api/social/posts/${encodeURIComponent(b.dataset.scposter)}/poster`, {}); toast('Poster made from your Brand kit.'); social(el); }
      catch (e) { toast(e.message, true); b.disabled = false; b.textContent = 'Make poster'; }
    }));
    el.querySelectorAll('[data-scpub]').forEach(b => b.addEventListener('click', async () => {
      const p = (d.calendar || []).find(x => x.id === b.dataset.scpub);
      const where = (p.platforms || []).map(x => PLAT[x] || x).join(' and ');
      if (!confirm(`Post this now on ${where}? It goes out exactly as shown, to everyone who follows you.`)) return;
      b.disabled = true;
      try { await api('POST', `/api/social/posts/${encodeURIComponent(p.id)}/publish`, {}); toast('Posting… the link appears here in a minute.'); setTimeout(() => social(el), 5000); }
      catch (e) { toast(e.message, true); b.disabled = false; }
    }));
    el.querySelectorAll('[data-scok]').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true;
      try { await api('POST', `/api/social/posts/${encodeURIComponent(b.dataset.scok)}`, {status: 'approved'}); toast('OK. It goes out at its time.'); social(el); }
      catch (e) { toast(e.message, true); b.disabled = false; }
    }));
    el.querySelectorAll('[data-scpause]').forEach(b => b.addEventListener('click', async () => {
      const on = b.dataset.scpause === '1';
      try { await api('POST', '/api/social/settings', {paused: on}); toast(on ? 'Paused. Nothing goes out until you resume.' : 'Resumed.'); social(el); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelector('#scStop')?.addEventListener('click', async () => {
      if (!confirm('Emergency stop? All posting and automatic replies stop, and every queued post goes back to draft.')) return;
      try { const r = await api('POST', '/api/social/settings', {stop: true}); toast(`Stopped. ${r.back_to_draft} post(s) back to draft.`); social(el); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelector('#scQSave')?.addEventListener('click', async () => {
      try { await api('POST', '/api/social/settings', {quiet: [Number(el.querySelector('#scQ0').value), Number(el.querySelector('#scQ1').value)]}); toast('Quiet hours saved.'); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelectorAll('[data-scbox]').forEach(b => b.addEventListener('click', () => {
      BOXNOW = b.dataset.scbox;
      el.querySelectorAll('[data-scbox]').forEach(x => { const on = x === b; x.className = `btn ${on ? 'go' : 'soft'}`; x.setAttribute('aria-selected', on); });
      inbox(el);
    }));
    el.querySelectorAll('[data-scrun]').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true;
      try { await api('POST', `/api/social/run/${b.dataset.scrun}`, {}); toast({plan: 'Rewriting the draft. Approved posts stay.', inbox: 'Checking comments and DMs now.', monthly: 'Making the PDF - it arrives in your chat.', growth: 'Reading tags, hashtags and competitors now.'}[b.dataset.scrun] || 'Reading your latest numbers.'); setTimeout(() => social(el), 4000); }
      catch (e) { toast(e.message, true); }
      b.disabled = false;
    }));
  }

  // ------------------------------------------------------------ v0.357 the CAD Desk (Engineering Desk, Phase 1)
  let CTIMER = null;
  const CSTATE = {queued: ['warn', 'Queued'], designing: ['v', 'Designing'], building: ['v', 'Building'], drawing: ['v', 'Drawing'],
                  done: ['ok', 'Ready'], failed: ['bad', 'Failed']};
  const FILEN = [['part.step', 'STEP (CAD / CNC)'], ['part.stl', 'STL (3D print)'], ['part.3mf', '3MF (3D print)'], ['part.glb', 'GLB (3D viewer / AR)'],
                 ['section.dxf', 'DXF section (laser / CNC)'], ['drawing.pdf', 'Drawing PDF'], ['part.py', 'CadQuery code']];
  const b64 = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1] || ''); r.onerror = no; r.readAsDataURL(f); });
  async function cad(el) {
    clearTimeout(CTIMER);
    let d;
    try { d = await api('GET', '/api/eng/projects'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>CAD Desk</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    const ps = d.projects || [];
    el.innerHTML = `<div class="vh"><h2>CAD Desk</h2><span class="muted em-sub">Describe a part with its sizes in mm. Hoola designs it, checks it and gives you STEP, STL and a drawing. Drafts for your engineer's review, not certified.</span></div>
      <article class="tile gl cad-new"><textarea id="cadBrief" rows="4" placeholder="A single part or a whole assembly. e.g. gearbox: 2 spur gears module 2 (20 and 40 teeth) on 15 mm shafts with 6202 bearings in an aluminium housing 4 mm walls, M5 lid screws"></textarea>
      <div class="cad-in"><label>Sketch / photo (up to 3) <input type="file" id="cadImg" accept="image/png,image/jpeg,image/webp" multiple></label>
      <label>Your STEP / STL to modify or fit (up to 2) <input type="file" id="cadFile" accept=".step,.stp,.stl" multiple></label></div>
      <div class="acts"><button class="btn go" type="button" id="cadGo">Design it</button><span class="muted">${esc(String(d.today || 0))} today</span></div></article>
      ${ps.length ? ps.map(cadCard).join('') : '<div class="empty">No parts yet.</div>'}`;
    el.querySelector('#cadGo').addEventListener('click', async ev => {
      const brief = el.querySelector('#cadBrief').value.trim();
      if (!brief) return;
      ev.target.disabled = true;
      try {
        const images = await Promise.all([...el.querySelector('#cadImg').files].slice(0, 3).map(b64));
        const files = await Promise.all([...el.querySelector('#cadFile').files].slice(0, 2).map(async f => ({name: f.name, data: await b64(f)})));
        await api('POST', '/api/eng/projects', {brief, images, files});
        toast('Designing. A simple part takes about a minute, a big assembly a few.');
      }
      catch (e) { toast(e.message, true); }
      cad(el);
    });
    el.querySelectorAll('[data-cadch]').forEach(b => b.addEventListener('click', async () => {
      const inp = el.querySelector(`[data-cadin="${b.dataset.cadch}"]`), words = inp.value.trim();
      if (!words) return;
      b.disabled = true;
      try { await api('POST', `/api/eng/projects/${encodeURIComponent(b.dataset.cadch)}/change`, {words}); toast('Making the next version.'); }
      catch (e) { toast(e.message, true); }
      cad(el);
    }));
    el.querySelectorAll('[data-caddel]').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Delete this part and all its versions?')) return;
      try { await api('DELETE', `/api/eng/projects/${encodeURIComponent(b.dataset.caddel)}`); } catch (e) { toast(e.message, true); }
      cad(el);
    }));
    if (ps.some(p => !['done', 'failed'].includes(p.status))) CTIMER = setTimeout(() => { if (visible(el)) cad(el); }, 4000);
  }
  function cadMore(v) {                                   // v0.362 material, mass, parts list, printing, review, plan
    const bits = [];
    if (v.material) bits.push(`Material: ${esc(v.material)}${v.mass_g ? ` · about ${num(v.mass_g)} g` : ''}`);
    if (v.print && v.print.overhang_pct !== undefined)
      bits.push(`3D print: ${num(v.print.overhang_pct)}% overhang${v.print.fits_220_bed ? ' · fits a 220 mm bed' : ' · bigger than a 220 mm bed'}`);
    if (v.review && v.review.problems && v.review.problems.length) bits.push(`Review notes: ${v.review.problems.map(esc).join('; ')}`);
    else if (v.review && v.review.ok) bits.push('Opus review: matches the ask');
    const bom = (v.parts || []).length ? `<table class="cad-bom"><thead><tr><th>Part</th><th>Volume (mm³)</th><th>Mass (g)</th></tr></thead><tbody>${
      v.parts.map(x => `<tr><td>${esc(x.name)}</td><td>${num(x.volume_mm3)}</td><td>${x.mass_g == null ? '–' : num(x.mass_g)}</td></tr>`).join('')}</tbody></table>` : '';
    const plan = v.plan ? `<details><summary>Design plan</summary><p class="muted">${esc(v.plan)}</p></details>` : '';
    return `${bits.length ? `<p class="muted">${bits.join('<br>')}</p>` : ''}${bom}${plan}`;
  }
  function cadCard(p) {
    const st = CSTATE[p.status] || ['', p.status], v = p.latest;
    const views = v ? ['iso', 'front', 'top', 'right'].filter(k => v.files[k + '.png'])
      .map(k => `<a href="${esc(v.files[k + '.png'])}" target="_blank" rel="noopener"><img src="${esc(v.files[k + '.png'])}" alt="${esc(k)} view" loading="lazy"></a>`).join('') : '';
    const bb = v && v.bbox ? `${num(v.bbox.x)} x ${num(v.bbox.y)} x ${num(v.bbox.z)} mm` : '';
    const checks = v ? (v.checks || []).map(c => tag(c.ok ? 'ok' : 'bad', `${c.ok ? '✓' : '✗'} ${c.name}${c.note ? ': ' + c.note : ''}`)).join(' ') : '';
    const files = v ? FILEN.filter(([f]) => v.files[f]).map(([f, n]) => `<a class="btn soft" href="${esc(v.files[f])}" target="_blank" rel="noopener">${esc(n)}</a>`).join(' ') : '';
    const busy = !['done', 'failed'].includes(p.status);
    return `<article class="tile gl cad-card"><div class="em-h"><h3>${esc(p.title)}${v ? ` <small class="muted">v${esc(String(v.n))}</small>` : ''}</h3>${tag(st[0], busy ? p.stage || st[1] : st[1])}</div>
      ${p.error ? `<p class="badc">${esc(p.error)}</p>` : ''}
      ${views ? `<div class="cad-views">${views}</div>` : ''}
      ${bb ? `<p class="muted">${esc(bb)}${v.volume_mm3 ? ' · ' + num(v.volume_mm3) + ' mm³' : ''}${v.assumed && v.assumed.toLowerCase() !== 'none' ? ' · Assumed: ' + esc(v.assumed) : ''}</p>` : ''}
      ${checks ? `<div class="cad-checks">${checks}</div>` : ''}
      ${v ? cadMore(v) : ''}
      ${files ? `<div class="acts">${files}</div>` : ''}
      ${v && !busy ? `<div class="cad-change"><input data-cadin="${esc(p.id)}" placeholder="Change it, e.g. holes 10 mm, wall 3 mm thicker"><button class="btn soft" type="button" data-cadch="${esc(p.id)}">Make next version</button></div>` : ''}
      <div class="acts"><button class="btn soft em-leave" type="button" data-caddel="${esc(p.id)}">Delete</button></div></article>`;
  }

  return {hub, desk, social, cad};
};
