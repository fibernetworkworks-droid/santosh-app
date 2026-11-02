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
  const DESKS = {game_dev: 'gamedesk', procgen_dev: 'gamedesk', physics_dev: 'gamedesk', audio_dev: 'gamedesk', haptics_dev: 'gamedesk', netcode_dev: 'gamedesk', xr_dev: 'gamedesk', sim_dev: 'gamedesk', twin_arch: 'gamedesk', vfx_td: 'gamedesk', architect: 'archdesk'};   // v0.420 the Game Desk roles share it
    // v0.410 + the Architecture Desk    // v0.370 employee key -> its desk view when the names differ

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
    if (what === 'open') { location.hash = ''; document.querySelector(`[data-v="${DESKS[key] || key + 'desk'}"]`)?.click(); return; }   // seodesk / socialdesk / caddesk / gamedesk
    if (what === 'leave' && !confirm('Let go of this employee? Its jobs stop at once. Its history stays, read-only.')) return;
    try {
      await api('POST', `/api/employees/${encodeURIComponent(key)}/${what}`, what === 'hire' ? {trust: 'seekh'} : undefined);
      toast(what === 'hire' ? 'Hired. Open the desk to set it up.' : what === 'leave' ? 'Let go. Its jobs have stopped.' : what === 'pause' ? 'Paused. No jobs run until you resume.' : 'Back at work.');
    } catch (e) { toast(e.message, true); }
    await hub(HUB);
    if (what === 'hire') document.querySelector(`[data-v="${DESKS[key] || key + 'desk'}"]`)?.click();
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
  let SOC = null, SOCTRUST = 'seekh', HAS_LI = false, HAS_YT = false;
  const PLAT = {instagram: 'Instagram', facebook: 'Facebook Page', linkedin: 'LinkedIn', whatsapp: 'WhatsApp Business', youtube: 'YouTube'};   // v0.384
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
    HAS_LI = (d.accounts || []).some(a => a.platform === 'linkedin' && a.status === 'ok');
    HAS_YT = (d.accounts || []).some(a => a.platform === 'youtube' && a.status === 'ok');
    el.innerHTML = `<div class="vh"><h2>Social Desk</h2><span class="muted em-sub">${esc(d.profile.business || '')}${d.profile.city ? ' · ' + esc(d.profile.city) : ''}</span>
        ${accs.length ? tag(sc, sn) : tag('warn', 'Connect an account')} ${d.status === 'paused' ? tag('warn', 'Paused') : ''} <span class="tag">${esc((TRUST[d.trust] || [d.trust])[0])}</span></div>
      <div class="tile gl"><div class="em-h"><h3>Accounts</h3><span class="muted em-small">You log in on Instagram / Facebook's own page. Hoola never sees your password.</span></div>
        <div class="sc-accs">${accs.map(a => `<div class="sc-acc">${a.picture ? `<img src="${esc(a.picture)}" alt="" loading="lazy">` : '<span class="sc-pic"></span>'}
          <div><b>${esc(a.handle || a.name)}</b><span class="muted">${esc(PLAT[a.platform] || a.platform)}${a.platform === 'whatsapp' ? ' · ' + esc(a.name || '') + ' · messages reach your Business inbox' : a.platform === 'linkedin' ? ' · your profile' : a.platform === 'youtube' ? ' · ' + num(a.followers) + ' subscribers' : ' · ' + num(a.followers) + ' followers'}</span>
          ${a.platform === 'whatsapp' && a.error ? `<span class="warnc em-small">${esc(a.error)}</span>` : ''}
          ${a.status !== 'ok' ? `<span class="badc em-small">${esc(a.status === 'expired' ? 'Connection ended: connect again' : a.error || a.status)}</span>` : ''}
          ${a.status === 'ok' && (a.can_post === false || a.can_reply === false) ? '<span class="warnc em-small">Reconnect to allow posting and replies</span>' : ''}</div>
          <button class="btn soft" type="button" data-scoff="${esc(a.id)}">Disconnect</button></div>`).join('')}
        <div class="sc-connect">${['instagram', 'facebook', 'linkedin', 'whatsapp', 'youtube'].map(p => d.connect[p]
          ? `<button class="btn ${accs.some(a => a.platform === p) ? 'soft' : 'go'}" type="button" data-scon="${p}">${accs.some(a => a.platform === p) ? 'Reconnect' : 'Connect'} ${PLAT[p]}</button>`
          : `<button class="btn soft" type="button" disabled title="The server needs Hoola's ${p === 'linkedin' ? 'LinkedIn' : p === 'youtube' ? 'Google sign-in' : 'Meta'} app keys">${PLAT[p]}: not set up on the server yet</button>`).join('')}</div>
        <p class="muted em-small">WhatsApp Business: Meta's own window connects your number; customers' messages then reach your Business inbox. LinkedIn: posts go to your own profile (a Company Page needs LinkedIn's approval first).</p>
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
          <p class="muted em-small">Pause also stops automatic replies. Emergency stop sends every queued post back to draft.</p>
          ${HAS_YT ? `<div class="sc-quiet"><label>YouTube: are your videos made for kids? <select id="scKids" aria-label="Made for kids">
              <option value="" ${pst.yt_kids == null ? 'selected' : ''} disabled>Choose (YouTube requires it)</option>
              <option value="no" ${pst.yt_kids === false ? 'selected' : ''}>No</option><option value="yes" ${pst.yt_kids === true ? 'selected' : ''}>Yes</option></select></label></div>
            <div class="sc-quiet"><label>YouTube playlist ID (optional) <input id="scPl" class="sc-pl" value="${esc(pst.yt_playlist || '')}" placeholder="PL..."></label>
              <button class="btn soft" type="button" id="scPlSave">Save</button></div>
            <p class="muted em-small">Until Google finishes Hoola's YouTube API audit, uploads may stay private - the post tells you, and you make it public in YouTube Studio.</p>` : ''}</div>
        <div class="tile gl"><h3>Best times for you</h3>${(pl.best_times || {}).slots && pl.best_times.slots.length
          ? `<table class="em-tbl"><tbody>${pl.best_times.slots.map(x => `<tr><td>${esc(x.day)} ${esc(x.band)}</td><td>${esc(String(x.lift))}x your normal</td><td class="muted">${num(x.posts)} posts</td></tr>`).join('')}</tbody></table>
            <p class="muted em-small">Certainty: ${esc(pl.best_times.sure)}. New calendars use these times.</p>`
          : `<div class="empty">${esc((pl.best_times || {}).note || 'After a few more posts.')}</div>`}
          ${(pl.boosts || []).length ? `<h3 class="sc-h">Worth a boost</h3>${pl.boosts.map(x => `<p class="em-small"><a href="${esc(x.permalink)}" target="_blank" rel="noopener">${esc(x.fmt)} · ${esc(x.date)}</a> <b>${esc(String(x.times))}x</b> your normal. <span class="muted">${esc(x.plan)}</span></p>`).join('')}` : ''}</div>
      </div>` : ''}
      ${accs.length ? growthTile(d.growth || {}) : ''}
      ${accs.length ? '<div class="tile gl sc-ytads" id="scYtAds"><div class="em-h"><h3>YouTube ads</h3></div><div class="empty">Loading…</div></div>' : ''}
      ${accs.length ? '<div class="tile gl sc-ytads" id="scMetaAds"><div class="em-h"><h3>Facebook &amp; Instagram ads</h3></div><div class="empty">Loading…</div></div>' : ''}
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
    if (accs.length) ytAds(el);
    if (accs.length) metaAds(el);
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
      ${Object.entries(res).map(([pl, r]) => r.link ? `<p class="em-small okc">Posted on <a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(PLAT[pl] || pl)}</a></p>${r.note ? `<p class="em-small warnc">${esc(r.note)}</p>` : ''}`
          : r.error ? `<p class="em-small badc">${esc(PLAT[pl] || pl)}: ${esc(r.error)}</p>` : '').join('')}
      ${!done && (p.problems || []).length ? `<p class="em-small warnc">${(p.problems || []).map(esc).join(' ')}</p>` : ''}
      ${done ? '' : `<div class="acts"><select data-scst="${esc(p.id)}" aria-label="Status">${Object.entries(PST).map(([v, [, l]]) => `<option value="${v}"${v === p.status ? ' selected' : ''}>${l}</option>`).join('')}${DONE[p.status] ? `<option selected disabled>${esc(DONE[p.status][1])}</option>` : ''}</select>
        <button class="btn soft" type="button" data-sccopy="${esc(p.id)}">Copy caption</button><button class="btn soft" type="button" data-scedit="${esc(p.id)}">Edit</button>
        <label class="btn soft sc-up">Add photo / video<input type="file" accept="image/*,video/mp4,video/quicktime" data-scup="${esc(p.id)}" hidden></label>
        <button class="btn soft" type="button" data-scposter="${esc(p.id)}">Make poster</button>
        ${HAS_YT && ['reel', 'video'].includes(p.format) ? `<button class="btn soft" type="button" data-scyt="${esc(p.id)}" aria-pressed="${(p.platforms || []).includes('youtube')}">${(p.platforms || []).includes('youtube') ? 'Remove YouTube' : (p.format === 'reel' ? 'Also as YouTube Short' : 'Also on YouTube')}</button>` : ''}
        ${HAS_LI ? `<button class="btn soft" type="button" data-scli="${esc(p.id)}" aria-pressed="${(p.platforms || []).includes('linkedin')}">${(p.platforms || []).includes('linkedin') ? 'Remove LinkedIn' : 'Also on LinkedIn'}</button>` : ''}
        ${needOk ? `<button class="btn go" type="button" data-scok="${esc(p.id)}">OK to post</button>` : ''}
        <button class="btn ${needOk ? 'soft' : 'go'}" type="button" data-scpub="${esc(p.id)}"${(p.problems || []).length ? ' disabled' : ''}>Publish now</button></div>`}</div>`;
  }

  // ------------------------------------------------------------ v0.383 growth (Phase 5)
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

  // ------------------------------------------------------------ v0.401 YouTube ads (plan Y2): Google Ads API, her taps only
  const YTS = {draft: ['warn', 'Draft'], checked: ['ok', 'Google checked'], created: ['v', 'In Google, paused'],
               running: ['ok', 'Running'], paused: ['', 'Paused'], ended: ['', 'Finished'], failed: ['bad', 'Needs a fix']};
  async function ytAds(el) {
    const box = el.querySelector('#scYtAds'); if (!box) return;
    let v;
    try { v = await api('GET', '/api/social/ytads'); }
    catch (e) { box.innerHTML = `<div class="em-h"><h3>YouTube ads</h3></div><p class="badc">${esc(e.message)}</p>`; return; }
    const head = `<div class="em-h"><h3>YouTube ads</h3><span class="muted em-small">Your own Google Ads account. An ad is made paused; money is spent only after you tap Start.</span></div>`;
    if (!v.configured) { box.innerHTML = head + '<div class="empty">Not set up on the server yet (Google sign-in).</div>'; return; }
    const a = v.account;
    if (!a) { box.innerHTML = head + '<button class="btn go" type="button" id="ytConn">Connect Google Ads</button>'; wireYt(el, box, v); return; }
    const pick = !a.customer_id ? `<p class="em-small">Which ad account runs your YouTube ads?</p><div class="acts">${(a.customers || []).filter(c => !c.manager).map(c =>
      `<button class="btn soft" type="button" data-ytcust="${esc(c.id)}">${esc(c.name || c.id)} (${esc(c.currency || '')})${c.test ? ' - test' : ''}</button>`).join('') || '<span class="muted">No ad account found in this Google login.</span>'}</div>` : '';
    const card = d => { const [c, n] = YTS[d.status] || ['', d.status]; const ro = !['draft', 'checked', 'failed'].includes(d.status);
      return `<div class="em-item sc-ytd" data-did="${esc(d.id)}"><div class="em-meta"><b>${esc(d.video_title || d.video_id || 'New ad')}</b>${tag(c, n)}
          <span class="muted">${num(d.daily)} ${esc(a.currency || '')} a day x ${num(d.days)} days = ${num(d.total)}${d.stop_on ? ' · until ' + esc(d.stop_on) : ''}</span></div>
        ${ro ? `<p class="em-small">${d.headlines.map(esc).join(' · ')}</p>` : `<div class="ar-form em-form sc-ytform">
          <label><span>Video</span><select data-f="video_id">${(v.videos || []).map(x => `<option value="${esc(x.id)}"${x.id === d.video_id ? ' selected' : ''}>${esc(x.title || x.id)} (${num(x.views)} views)</option>`).join('')}<option value="${esc(d.video_id)}"${(v.videos || []).some(x => x.id === d.video_id) ? '' : ' selected'}>${esc(d.video_id || 'Choose')}</option></select></label>
          <label><span>Headlines (one per line, up to 5, 40 letters each)</span><textarea data-f="headlines" rows="3">${esc(d.headlines.join('\n'))}</textarea></label>
          <label><span>Long headline (90)</span><input data-f="long_headline" value="${esc(d.long_headline)}"></label>
          <label><span>Descriptions (one per line, up to 5, 90 each)</span><textarea data-f="descriptions" rows="2">${esc(d.descriptions.join('\n'))}</textarea></label>
          <label><span>Business name (25)</span><input data-f="business" value="${esc(d.business)}"></label>
          <label><span>Where the ad leads (https://...)</span><input data-f="final_url" value="${esc(d.final_url)}"></label>
          <label><span>Daily budget (${esc(a.currency || '')}, up to ${num(v.cap)})</span><input data-f="daily" type="number" min="1" max="${esc(String(v.cap))}" value="${esc(String(d.daily))}"></label>
          <label><span>Days (1-30)</span><input data-f="days" type="number" min="1" max="30" value="${esc(String(d.days))}"></label>
          <label class="btn soft sc-up">${d.logo_asset ? 'Change logo' : 'Add logo (square)'}<input type="file" accept="image/*" data-ytlogo="${esc(d.id)}" hidden></label></div>`}
        ${(d.problems || []).length ? `<p class="em-small warnc">${d.problems.map(esc).join(' ')}</p>` : ''}${d.error ? `<p class="em-small badc">${esc(d.error)}</p>` : ''}
        <div class="acts">${ro ? '' : `<button class="btn soft" type="button" data-ytsave="${esc(d.id)}">Save</button>
          <button class="btn soft" type="button" data-ytact="check" data-id="${esc(d.id)}">Check with Google (free)</button>
          <button class="btn go" type="button" data-ytact="create" data-id="${esc(d.id)}"${(d.problems || []).length ? ' disabled' : ''}>Create in Google (paused)</button>`}
          ${['created', 'paused'].includes(d.status) ? `<button class="btn go" type="button" data-ytact="start" data-id="${esc(d.id)}" data-total="${esc(String(d.total))}">Start</button>` : ''}
          ${d.status === 'running' ? `<button class="btn soft" type="button" data-ytact="pause" data-id="${esc(d.id)}">Pause</button>` : ''}</div></div>`; };
    box.innerHTML = head + `<p class="muted em-small">Google account ${esc(a.email)}${a.customer_id ? ' · ad account ' + esc(a.customer_id) : ''}${a.error ? ' · ' + esc(a.error) : ''}</p>` + pick +
      (a.customer_id ? `<div class="acts em-run"><button class="btn soft" type="button" id="ytRead">Read my YouTube ads</button>
        <button class="btn soft" type="button" id="ytNew"${(v.videos || []).length ? '' : ' disabled title="Connect YouTube first"'}>New YouTube ad</button></div>
        <div id="ytCamps"></div><div class="sc-items">${(v.drafts || []).map(card).join('')}</div>
        <p class="muted em-small">Runs on YouTube only (in-stream, in-feed, Shorts) as a Demand Gen campaign, India, your languages. Older in-stream "Video" campaigns cannot be made through Google's API - make those in Google Ads.</p>` : '');
    wireYt(el, box, v);
  }

  function wireYt(el, box, v) {
    const go = async (fn, done) => { try { await fn(); if (done) toast(done); ytAds(el); } catch (e) { toast(e.message, true); } };
    box.querySelector('#ytConn')?.addEventListener('click', async () => {
      try { const r = await api('GET', '/api/social/ytads/connect'); window.open(r.url, '_blank', 'noopener'); toast('Sign in on Google, then come back here.'); }
      catch (e) { toast(e.message, true); }
    });
    box.querySelectorAll('[data-ytcust]').forEach(b => b.addEventListener('click', () => go(() => api('POST', '/api/social/ytads/account', {customer_id: b.dataset.ytcust}), 'Ad account chosen.')));
    box.querySelector('#ytNew')?.addEventListener('click', () => go(() => api('POST', '/api/social/ytads/drafts', {video_id: (v.videos[0] || {}).id || ''}), 'Draft made - change anything, then Check with Google.'));
    box.querySelector('#ytRead')?.addEventListener('click', async () => {
      const out = box.querySelector('#ytCamps'); out.innerHTML = '<div class="empty">Reading…</div>';
      try {
        const r = await api('POST', '/api/social/ytads/read');
        out.innerHTML = (r.campaigns || []).length ? `<table class="em-tbl"><thead><tr><th>Campaign</th><th>Status</th><th>Spent (${esc(r.currency || '')})</th><th>Views</th><th>Cost a view</th><th>Clicks</th><th>Results</th></tr></thead><tbody>${r.campaigns.map(c =>
          `<tr><td>${esc(c.name)}</td><td>${esc(c.status)}</td><td>${num(c.spend)}</td><td>${num(c.views)}</td><td>${c.cpv == null ? '–' : num(c.cpv)}</td><td>${num(c.clicks)}</td><td>${num(c.conversions)}</td></tr>`).join('')}</tbody></table>
          ${r.ads_desk ? `<p class="muted em-small">Ads desk: ${esc(r.ads_desk)}</p>` : ''}` : '<div class="empty">No YouTube campaigns in the last 30 days.</div>';
      } catch (e) { out.innerHTML = `<p class="badc">${esc(e.message)}</p>`; }
    });
    const body = card => { const o = {}; card.querySelectorAll('[data-f]').forEach(i => { const f = i.dataset.f;
      o[f] = ['headlines', 'descriptions'].includes(f) ? i.value.split('\n').map(x => x.trim()).filter(Boolean) : (['daily', 'days'].includes(f) ? Number(i.value) : i.value); }); return o; };
    box.querySelectorAll('[data-ytsave]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/social/ytads/drafts/${encodeURIComponent(b.dataset.ytsave)}`, body(b.closest('.sc-ytd'))), 'Saved.')));
    box.querySelectorAll('[data-ytlogo]').forEach(inp => inp.addEventListener('change', async () => {
      const f = inp.files && inp.files[0]; if (!f) return;
      const fd = new FormData(); fd.append('file', f);
      go(async () => { const a = await api('POST', '/api/social/media', undefined, {form: fd});
        await api('POST', `/api/social/ytads/drafts/${encodeURIComponent(inp.dataset.ytlogo)}`, {...body(inp.closest('.sc-ytd')), logo_asset: a.id}); }, 'Logo added.');
    }));
    box.querySelectorAll('[data-ytact]').forEach(b => b.addEventListener('click', async () => {
      const act = b.dataset.ytact, id = encodeURIComponent(b.dataset.id);
      if (act === 'create' && !confirm('Create this ad in your Google Ads account? It is made PAUSED - nothing is spent until you tap Start.')) return;
      if (act === 'start' && !confirm(`Start this YouTube ad? Google can spend up to its daily budget every day, about ${b.dataset.total} in total. You can Pause any time.`)) return;
      b.disabled = true;
      go(() => api('POST', `/api/social/ytads/drafts/${id}/${act}`, act === 'start' ? {confirm: true} : {}),
         {check: 'Google checked it - no problems.', create: 'Made in Google Ads, paused.', start: 'Started.', pause: 'Paused.'}[act]);
    }));
  }

  // ------------------------------------------------------------ v0.417 META ADS (A1): her Meta ad account by Facebook Login, her taps only
  const MAS = {draft: ['warn', 'Draft'], checked: ['ok', 'Meta checked'], created: ['v', 'In Meta, paused'],
               running: ['ok', 'Running'], paused: ['', 'Paused'], ended: ['', 'Finished'], failed: ['bad', 'Needs a fix']};
  async function metaAds(el) {
    const box = el.querySelector('#scMetaAds'); if (!box) return;
    let v;
    try { v = await api('GET', '/api/ads/metaads'); }
    catch (e) { box.innerHTML = `<div class="em-h"><h3>Facebook &amp; Instagram ads</h3></div><p class="badc">${esc(e.message)}</p>`; return; }
    const head = `<div class="em-h"><h3>Facebook &amp; Instagram ads</h3><span class="muted em-small">Your own Meta ad account. An ad is made paused; money is spent only after you tap Start.</span></div>`;
    if (!v.configured) { box.innerHTML = head + '<div class="empty">Not set up on the server yet (Meta app keys).</div>'; return; }
    const a = v.account;
    if (!a) { box.innerHTML = head + '<button class="btn go" type="button" id="maConn">Connect with Facebook</button>'; wireMa(el, box, v); return; }
    const login = a.via === 'login';
    const warn = a.renew ? '<p class="em-small warnc">Your Facebook login ends soon. <button class="btn soft" type="button" id="maConn">Connect again</button></p>'
      : (!login ? '<p class="em-small warnc">Joined with a pasted token - connect with Facebook to make ads here. <button class="btn soft" type="button" id="maConn">Connect with Facebook</button></p>' : '');
    const pick = login && !a.account ? `<p class="em-small">Which ad account pays for your ads?</p><div class="acts">${(a.accounts || []).map(c =>
      `<button class="btn soft" type="button" data-maacct="${esc(c.id)}"${c.active ? '' : ' disabled'}>${esc(c.name || c.id)} (${esc(c.currency || '')})${c.active ? '' : ' - closed'}</button>`).join('') || '<span class="muted">No ad account found in this Facebook login.</span>'}</div>` : '';
    const pages = login && a.account ? `<div class="acts"><span class="muted em-small">Ads run as</span>${(a.pages || []).map(p =>
      `<button class="btn ${p.id === a.page ? 'go' : 'soft'}" type="button" data-mapage="${esc(p.id)}">${esc(p.name)}${p.ig ? ' + @' + esc(p.ig) : ''}</button>`).join('') || '<span class="muted">No Page in this login.</span>'}</div>` : '';
    const cur = a.currency || '';
    const card = d => { const [c, n] = MAS[d.status] || ['', d.status]; const ro = !['draft', 'checked', 'failed'].includes(d.status); const boost = d.goal === 'boost';
      return `<div class="em-item sc-ytd" data-mid="${esc(d.id)}"><div class="em-meta"><b>${esc(d.goal_label)}</b>${tag(c, n)}
          <span class="muted">${num(d.daily)} ${esc(cur)} a day x ${num(d.days)} days = ${num(d.total)} · ${esc((d.cities || []).join(', ') || 'all India')}${d.stop_on ? ' · until ' + esc(d.stop_on) : ''}</span></div>
        ${ro ? `<p class="em-small">${esc(boost ? 'Post ' + d.post_id : d.text)}</p>` : `<div class="ar-form em-form sc-ytform">
          ${boost ? `<p class="em-small">Boosting post ${esc(d.post_id)}</p>` : `<label><span>Ad text</span><textarea data-f="text" rows="3">${esc(d.text)}</textarea></label>
          <label><span>Headline (40)</span><input data-f="headline" value="${esc(d.headline)}"></label>
          <label><span>Description (30, optional)</span><input data-f="description" value="${esc(d.description)}"></label>`}
          ${d.goal === 'website' ? `<label><span>Website (https://...)</span><input data-f="link" value="${esc(d.link)}"></label>` : ''}
          <label><span>Show on</span><select data-f="platforms">${[['both', 'Facebook + Instagram'], ['facebook', 'Facebook only'], ['instagram', 'Instagram only']].map(([k, t]) => `<option value="${k}"${d.platforms === k ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
          <label><span>Cities (comma separated, empty = all India)</span><input data-f="cities" value="${esc((d.cities || []).join(', '))}"></label>
          <label><span>Around each city (km)</span><input data-f="radius_km" type="number" min="1" max="80" value="${esc(String(d.radius_km))}"></label>
          <label><span>Ages</span><span class="acts"><input data-f="age_min" type="number" min="18" max="65" value="${esc(String(d.age_min))}"> to <input data-f="age_max" type="number" min="18" max="65" value="${esc(String(d.age_max))}"></span></label>
          <label><span>Who</span><select data-f="gender">${[['all', 'Everyone'], ['women', 'Women'], ['men', 'Men']].map(([k, t]) => `<option value="${k}"${d.gender === k ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
          <label><span>Daily budget (${esc(cur)}, up to ${num(v.cap)})</span><input data-f="daily" type="number" min="1" max="${esc(String(v.cap))}" value="${esc(String(d.daily))}"></label>
          <label><span>Days (1-30)</span><input data-f="days" type="number" min="1" max="30" value="${esc(String(d.days))}"></label>
          ${boost ? '' : `<label class="btn soft sc-up">${d.image_asset ? 'Change photo' : 'Add photo (square or 4:5)'}<input type="file" accept="image/*" data-maimg="${esc(d.id)}" hidden></label>`}</div>`}
        ${(d.problems || []).length ? `<p class="em-small warnc">${d.problems.map(esc).join(' ')}</p>` : ''}${d.error ? `<p class="em-small badc">${esc(d.error)}</p>` : ''}
        <div class="acts">${ro ? '' : `<button class="btn soft" type="button" data-masave="${esc(d.id)}">Save</button>
          <button class="btn soft" type="button" data-maact="check" data-id="${esc(d.id)}">Check with Meta (free)</button>
          <button class="btn go" type="button" data-maact="create" data-id="${esc(d.id)}"${(d.problems || []).length ? ' disabled' : ''}>Create in Meta (paused)</button>`}
          ${['created', 'paused'].includes(d.status) ? `<button class="btn go" type="button" data-maact="start" data-id="${esc(d.id)}" data-total="${esc(String(d.total))} ${esc(cur)}" data-days="${esc(String(d.days))}">Start</button>` : ''}
          ${d.status === 'running' ? `<button class="btn soft" type="button" data-maact="pause" data-id="${esc(d.id)}">Pause</button>` : ''}</div></div>`; };
    box.innerHTML = head + `<p class="muted em-small">${esc(a.name || 'No ad account chosen')}${a.account ? ' · ' + esc(a.account) : ''}</p>` + warn + pick + pages +
      (login && a.account ? `<div class="acts em-run">${Object.entries(v.goals || {}).map(([k, t]) => `<button class="btn soft" type="button" data-manew="${esc(k)}">${esc(t)}</button>`).join('')}</div>
        <div id="maPosts"></div><div class="sc-items">${(v.drafts || []).map(card).join('')}</div>
        <p class="muted em-small">Chat ads open a WhatsApp / Messenger / Instagram chat with you. Meta stops the ad by itself after its days; Hoola also marks it finished and tells you.</p>` : '');
    wireMa(el, box, v);
  }

  function wireMa(el, box, v) {
    const go = async (fn, done) => { try { await fn(); if (done) toast(done); metaAds(el); } catch (e) { toast(e.message, true); } };
    box.querySelector('#maConn')?.addEventListener('click', async () => {
      try { const r = await api('GET', '/api/ads/meta/connect'); window.open(r.url, '_blank', 'noopener'); toast('Sign in on Facebook, then come back here.'); }
      catch (e) { toast(e.message, true); }
    });
    box.querySelectorAll('[data-maacct]').forEach(b => b.addEventListener('click', () => go(() => api('POST', '/api/ads/metaads/account', {account: b.dataset.maacct}), 'Ad account chosen.')));
    box.querySelectorAll('[data-mapage]').forEach(b => b.addEventListener('click', () => go(() => api('POST', '/api/ads/metaads/account', {page: b.dataset.mapage}), 'Page chosen.')));
    box.querySelectorAll('[data-manew]').forEach(b => b.addEventListener('click', async () => {
      const goal = b.dataset.manew;
      if (goal !== 'boost') return go(() => api('POST', '/api/ads/metaads/drafts', {goal}), 'Draft made from your business facts - add a photo, then Check with Meta.');
      const out = box.querySelector('#maPosts'); out.innerHTML = '<div class="empty">Reading your Page posts…</div>';
      try {
        const r = await api('GET', '/api/ads/metaads/posts');
        out.innerHTML = (r.posts || []).length ? `<p class="em-small">Which post?</p>${r.posts.map(p => `<p class="em-small"><button class="btn soft" type="button" data-mapost="${esc(p.id)}">Boost</button> ${esc(p.date)} · ${esc(p.text || '(photo / video)')} ${p.link ? `<a href="${esc(p.link)}" target="_blank" rel="noopener">open</a>` : ''}</p>`).join('')}` : '<div class="empty">No posts on your Page.</div>';
        out.querySelectorAll('[data-mapost]').forEach(x => x.addEventListener('click', () => go(() => api('POST', '/api/ads/metaads/drafts', {goal: 'boost', post_id: x.dataset.mapost}), 'Draft made - check the budget and days.')));
      } catch (e) { out.innerHTML = `<p class="badc">${esc(e.message)}</p>`; }
    }));
    const body = card => { const o = {}; card.querySelectorAll('[data-f]').forEach(i => { const f = i.dataset.f;
      o[f] = f === 'cities' ? i.value.split(',').map(x => x.trim()).filter(Boolean) : (['daily', 'days', 'radius_km', 'age_min', 'age_max'].includes(f) ? Number(i.value) : i.value); }); return o; };
    box.querySelectorAll('[data-masave]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/ads/metaads/drafts/${encodeURIComponent(b.dataset.masave)}`, body(b.closest('.sc-ytd'))), 'Saved.')));
    box.querySelectorAll('[data-maimg]').forEach(inp => inp.addEventListener('change', async () => {
      const f = inp.files && inp.files[0]; if (!f) return;
      const fd = new FormData(); fd.append('file', f);
      go(async () => { const a = await api('POST', '/api/social/media', undefined, {form: fd});
        await api('POST', `/api/ads/metaads/drafts/${encodeURIComponent(inp.dataset.maimg)}`, {...body(inp.closest('.sc-ytd')), image_asset: a.id}); }, 'Photo added.');
    }));
    box.querySelectorAll('[data-maact]').forEach(b => b.addEventListener('click', async () => {
      const act = b.dataset.maact, id = encodeURIComponent(b.dataset.id);
      if (act === 'create' && !confirm('Create this ad in your Meta ad account? It is made PAUSED - nothing is spent until you tap Start.')) return;
      if (act === 'start' && !confirm(`Start this ad? Meta can spend up to its daily budget every day, about ${b.dataset.total} in total, and stops it after ${b.dataset.days} days. You can Pause any time.`)) return;
      b.disabled = true;
      go(() => api('POST', `/api/ads/metaads/drafts/${id}/${act}`, act === 'start' ? {confirm: true} : {}),
         {check: 'Meta checked it - no problems.', create: 'Made in Meta, paused.', start: 'Started.', pause: 'Paused.'}[act]);
    }));
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
    el.querySelectorAll('[data-scyt]').forEach(b => b.addEventListener('click', async () => {
      const p = (d.calendar || []).find(x => x.id === b.dataset.scyt);
      const on = (p.platforms || []).includes('youtube');
      const pl = on ? p.platforms.filter(x => x !== 'youtube') : [...(p.platforms || []), 'youtube'];
      try { await api('POST', `/api/social/posts/${encodeURIComponent(p.id)}`, {platforms: pl}); toast(on ? 'YouTube removed. Approve the post again.' : 'Added to YouTube. Approve the post again.'); social(el); }
      catch (e) { toast(e.message, true); }
    }));
    el.querySelector('#scKids')?.addEventListener('change', async ev => {
      try { await api('POST', '/api/social/settings', {yt_kids: ev.target.value === 'yes'}); toast('Saved for YouTube.'); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelector('#scPlSave')?.addEventListener('click', async () => {
      try { await api('POST', '/api/social/settings', {yt_playlist: el.querySelector('#scPl').value.trim()}); toast('Playlist saved.'); }
      catch (e) { toast(e.message, true); }
    });
    el.querySelectorAll('[data-scli]').forEach(b => b.addEventListener('click', async () => {
      const p = (d.calendar || []).find(x => x.id === b.dataset.scli);
      const on = (p.platforms || []).includes('linkedin');
      const pl = on ? p.platforms.filter(x => x !== 'linkedin') : [...(p.platforms || []), 'linkedin'];
      try { await api('POST', `/api/social/posts/${encodeURIComponent(p.id)}`, {platforms: pl}); toast(on ? 'LinkedIn removed. Approve the post again.' : 'Added to LinkedIn. Approve the post again.'); social(el); }
      catch (e) { toast(e.message, true); }
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
                  checking: ['v', 'Checking'], analysing: ['v', 'Analysing'],
                  done: ['ok', 'Ready'], failed: ['bad', 'Failed']};
  const FILEN = [['part.step', 'STEP (CAD / CNC)'], ['part.stl', 'STL (3D print)'], ['part.3mf', '3MF (3D print)'], ['part.glb', 'GLB (3D viewer / AR)'],
                 ['section.dxf', 'DXF section (laser / CNC)'], ['drawing.pdf', 'Drawing PDF'], ['part.py', 'CadQuery code'],
                 ['analysis.pdf', 'Analysis report PDF'], ['part.nc', 'CNC G-code'], ['flat.dxf', 'Flat pattern DXF'],
                 ['robot_urdf.zip', 'Robot package (URDF / SRDF / SDF / MJCF)']];
  const b64 = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1] || ''); r.onerror = no; r.readAsDataURL(f); });
  async function cad(el) {
    clearTimeout(CTIMER);
    let d;
    try { d = await api('GET', '/api/eng/projects'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>CAD Desk</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    const ps = d.projects || [];
    el.innerHTML = `<div class="vh"><h2>CAD Desk</h2><span class="muted em-sub">Describe a part with its sizes in mm. Hoola designs it, checks it and gives you STEP, STL and a drawing. Drafts for your engineer's review, not certified.</span></div>
      <article class="tile gl cad-new"><textarea id="cadBrief" rows="4" placeholder="A part, a sheet-metal piece or a whole assembly, with its sizes. Add a load (kg), heat (watts), motor rpm or 'CNC' and Hoola also checks strength, heat, vibration or makes G-code. e.g. aluminium wall bracket 120 x 40, holds 25 kg at the tip, 2x M6 to the wall, safety factor 2"></textarea>
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
    // v0.365 analysis (FEA), CNC and sheet metal
    const ana = (v.analysis || []).map(a => `<div class="cad-ana"><b>${esc((a.lines || [])[0] || a.kind)}</b>${
      (a.lines || []).slice(1).map(l => `<div class="${l.startsWith('!') ? 'badc' : 'muted'}">${esc(l.replace(/^! /, ''))}</div>`).join('')}</div>`).join('');
    const pics = ['fea_0.png', 'fea_1.png', 'fea_2.png', 'cam.png', 'flat.png', 'motion.gif', 'explode.png', 'camcurve.png', 'dynamics.png'].filter(k => v.files[k])
      .map(k => `<a href="${esc(v.files[k])}" target="_blank" rel="noopener"><img src="${esc(v.files[k])}" alt="${esc(k)}" loading="lazy"></a>`).join('');
    const cam = v.cam ? `<p class="muted">${v.cam.ok ? `CNC: ${esc((v.cam.ops || []).join(', '))} · tool Ø${num(v.cam.tool_d)} mm · about ${num(v.cam.minutes)} min · simulate before cutting`
      : `CNC G-code did not run: ${esc(v.cam.error || '')}`}</p>` : '';
    const sheet = v.sheet ? `<p class="muted">Sheet ${num(v.sheet.t)} mm · flat ${num(v.sheet.length)} x ${num(v.sheet.width)} mm · R ${num(v.sheet.r)} · K ${num(v.sheet.k)}</p>` : '';
    // v0.403 measured manufacturability (DFM) rows
    const dfm = v.dfm && (v.dfm.rows || []).length ? `<div class="cad-ana"><b>Manufacturability (${esc(v.dfm.process)}): ${num(v.dfm.fails)} fail, ${num(v.dfm.reviews)} to review</b>${
      v.dfm.rows.map(r => `<div class="${r.status === 'fail' ? 'badc' : 'muted'}">${esc({pass: '✓', fail: '✗', review: '!', unverified: '?'}[r.status] || '')} ${esc(r.check)}: ${esc(r.measured)} (limit ${esc(r.limit)})${r.fix && r.status !== 'pass' ? ' - ' + esc(r.fix) : ''}</div>`).join('')}</div>` : '';
    return `${bits.length ? `<p class="muted">${bits.join('<br>')}</p>` : ''}${ana}${dfm}${cam}${sheet}${pics ? `<div class="cad-views">${pics}</div>` : ''}${bom}${plan}`;
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

  // ------------------------------------------------------------ v0.370 the Game Desk (Game Developer)
  let GTIMER = null;
  const GST = {designing: ['v', 'Writing the design'], design_ready: ['warn', 'Waiting for your OK'], queued: ['v', 'Queued'],
               writing: ['v', 'Writing code'], building: ['v', 'Building'], testing: ['v', 'Playing it'], done: ['ok', 'Ready to play'],
               failed: ['bad', 'Did not work'], cancelled: ['', 'Stopped']};
  const BUSYG = ['designing', 'queued', 'writing', 'building', 'testing'];
  let GS_BIBLE = false;        // v0.395 the Game Bible page of the open project
  let GS_ASSETS = false;       // v0.416 the Assets page of the open project
  let GS_REL = false;          // v0.416 the Release page (platforms + store kit) of the open project
  let GS_QA = false;           // v0.416 the QA farm + bugs page of the open project
  let GS_SIM = null;
  let GS_OPEN = '';            // v0.386 the Studio Project board open in the Game Desk ('' = the desk home)
  let GS_ROLE = '';            // v0.420 a role page open: 'world' | 'physics' ('' = none)
  let GS_ROLE_SID = '';        // ... for this Studio project ('' = her own, no project)
  async function game(el) {
    clearTimeout(GTIMER);
    if (GS_ROLE) return ({world: gsWorld, physics: gsPhysics, audio: gsAudio, haptics: gsHaptics, net: gsNet, xr: gsXr, sim: gsSim, twin: gsTwin, vfx: gsVfx}[GS_ROLE] || gsWorld)(el);
    if (GS_OPEN) return gsBoard(el, GS_OPEN);
    if (!el.firstChild) el.innerHTML = '<div class="vh"><h2>Game Desk</h2></div><div class="empty">Loading…</div>';
    let d, sp = {projects: []};
    try { [d, sp] = await Promise.all([api('GET', '/api/game'), api('GET', '/api/gamestudio').catch(() => ({projects: []}))]); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>Game Desk</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    const h = d.health || {};
    el.innerHTML = `<div class="vh"><h2>Game Desk</h2><span class="muted em-sub">Original games from your words, built in Godot 4 and played by Hoola before you see them.</span>
        ${h.ready ? tag('ok', 'Godot ' + (h.version || '')) : tag('bad', 'Godot not installed on the server')}</div>
      <div class="tile gl gd-new"><h3>New game</h3>
        <textarea id="gdBrief" rows="3" maxlength="2000" placeholder="Your idea in 2-3 lines: what the player does, how they win, who it is for" aria-label="Game idea"></textarea>
        <div class="acts"><select id="gdOr" aria-label="Screen">${(d.orientations || ['portrait']).map(o => `<option value="${esc(o)}">${esc(o[0].toUpperCase() + o.slice(1))}</option>`).join('')}</select>
          <button class="btn go" type="button" id="gdNew"${h.ready ? '' : ' disabled'}>Write the design</button></div>
        <p class="muted em-small">A short design doc comes first; nothing is built until you say OK. The play link stays private until you share it.</p></div>
      <div class="tile gl gd-team"><h3>Game Desk team</h3><p class="muted em-small">Each role is its own employee (hire it in Employees). Open a project's board to work on that game, or try them here on their own.</p>
        <div class="acts"><button class="btn soft" type="button" data-gs-role="world">Worlds (Procedural World Engineer)</button>
          <button class="btn soft" type="button" data-gs-role="physics">Physics (Physics Engine Developer)</button>
          <button class="btn soft" type="button" data-gs-role="audio">Audio (Spatial Audio Programmer)</button>
          <button class="btn soft" type="button" data-gs-role="haptics">Haptics (Haptic Feedback Engineer)</button>
          <button class="btn soft" type="button" data-gs-role="net">Multiplayer (Network Programmer)</button>
          <button class="btn soft" type="button" data-gs-role="xr">VR / AR (Interaction Engineer)</button>
          <button class="btn soft" type="button" data-gs-role="sim">Simulators (Simulation Engineer)</button>
          <button class="btn soft" type="button" data-gs-role="twin">Digital twin (Twin Architect)</button>
          <button class="btn soft" type="button" data-gs-role="vfx">VFX pipeline (Pipeline TD)</button></div></div>
      ${gsHome(sp.projects || [], d.games || [])}
      ${(d.games || []).map(gcard).join('') || '<div class="empty">No games yet.</div>'}`;
    el.querySelectorAll('[data-gs-role]').forEach(b => b.addEventListener('click', () => { GS_ROLE = b.dataset.gsRole; GS_ROLE_SID = ''; game(el); }));
    el.querySelectorAll('[data-gs-open]').forEach(b => b.addEventListener('click', () => { GS_OPEN = b.dataset.gsOpen; game(el); }));
    el.querySelector('#gsNew')?.addEventListener('click', async e => {
      const game_ = el.querySelector('#gsGame').value, goal = el.querySelector('#gsGoal').value.trim();
      if (!game_) { toast('Pick a game that already plays.', true); return; }
      e.target.disabled = true;
      try { const p = await api('POST', '/api/gamestudio', {game: game_, goal}); GS_OPEN = p.id; toast('Project started. Add tasks or let Hoola plan them.'); }
      catch (err) { toast(err.message, true); }
      game(el);
    });
    el.querySelector('#gdNew')?.addEventListener('click', async e => {
      const brief = el.querySelector('#gdBrief').value.trim();
      if (brief.length < 8) { toast('Write your idea in 2-3 lines first.', true); return; }
      e.target.disabled = true;
      try { await api('POST', '/api/game', {brief, orientation: el.querySelector('#gdOr').value}); toast('Writing the design doc…'); }
      catch (err) { toast(err.message, true); }
      game(el);
    });
    el.querySelectorAll('[data-gd]').forEach(b => b.addEventListener('click', () => gact(el, b.dataset.gd, b.dataset.id, b)));
    el.querySelectorAll('img[data-qr]').forEach(img => { try { const q = window.qrcode(0, 'M'); q.addData(img.dataset.qr); q.make(); img.src = q.createDataURL(4, 2); } catch { img.remove(); } });
    if ((d.games || []).some(g => BUSYG.includes(g.status))) GTIMER = setTimeout(() => { if (visible(el)) game(el); }, 4000);
  }

  // ---------------------------------------------------------------- v0.386 Studio Project (long game projects)
  const GS_COLS = [['todo', 'To do'], ['working', 'Hoola working'], ['review', 'Waiting for your OK'], ['blocked', 'Stuck'], ['done', 'Done']];
  function gsBars(ms, gates) {
    const last = {}; (gates || []).forEach(g => { if (!last[g.milestone]) last[g.milestone] = g; });
    const VC = {PASS: 'ok', CONCERNS: 'warn', FAIL: 'bad', 'NOT ASSESSED': ''};
    return `<div class="gs-ms">${(ms || []).map(m => `<div class="gs-m"><div class="gs-mh"><b>${esc(m.name)}</b><span class="muted">${num(m.done)}/${num(m.total)}${m.target ? ' · ' + esc(m.target) : ''}</span></div>
      <div class="pbar"><i style="width:${Math.max(0, Math.min(100, m.pct || 0))}%"></i></div>
      ${gates ? `<div class="gs-gate">${last[m.key] ? tag(VC[last[m.key].verdict] || '', last[m.key].verdict) : ''}<button class="btn soft gs-mini" type="button" data-gs-gate="${esc(m.key)}">Gate check</button></div>` : ''}</div>`).join('')}</div>`;
  }
  let GS_CREW = null;
  let GS_CREW_OPEN = false;
  function gsCrew(p) {
    if (!GS_CREW) return '<p class="muted em-small">Loading the crew…</p>';
    const busy = new Set((p.crew || {}).busy || []);
    return `<p class="muted em-small">${esc(GS_CREW.note)}</p>${GS_CREW.tiers.map(t => `<h4>${esc(t.label)}</h4><div class="gs-roster">${t.roles.map(r =>
      `<div class="gs-rcard${busy.has(r.key) ? ' gs-busy' : ''}"><b>${esc(r.name)}</b><span class="gs-role${r.mode === 'writes' ? ' gs-writes' : ''}">${r.mode === 'writes' ? 'writes' : 'builds'}</span><p>${esc(r.does)}</p></div>`).join('')}</div>`).join('')}`;
  }
  function gsHome(projects, games) {
    const free = games.filter(g => g.version > 0 && !projects.some(p => p.game && p.game.id === g.id));
    return `<section class="tile gl gs-home"><h3>Studio projects</h3>
      <p class="muted em-small">A long project around one game: a task board, milestones, a log of decisions, a nightly build and a morning report. Each task is one small change that waits for your OK.</p>
      ${projects.map(p => `<article class="gs-pcard"><div class="em-h"><h4>${esc(p.number)} · ${esc(p.title)}</h4>
          ${p.counts && p.counts.review ? tag('warn', p.counts.review + ' waiting for your OK') : p.counts && p.counts.working ? tag('v', 'Hoola working') : tag('', (p.counts?.todo || 0) + ' to do')}</div>
        ${gsBars(p.milestones)}<div class="acts"><button class="btn go" type="button" data-gs-open="${esc(p.id)}">Open board</button></div></article>`).join('')}
      ${free.length ? `<div class="acts gs-start"><select id="gsGame" aria-label="Game">${free.map(g => `<option value="${esc(g.id)}">${esc(g.number)} · ${esc(g.title)}</option>`).join('')}</select>
        <input id="gsGoal" maxlength="1500" placeholder="Goal, e.g. release on the Play Store in 6 months" aria-label="Project goal">
        <button class="btn soft" type="button" id="gsNew">Start a long project</button></div>` : (projects.length ? '' : '<p class="muted em-small">Make a game first; once it plays you can turn it into a long project.</p>')}
    </section>`;
  }
  function gsTask(t, p) {
    const ms = (p.milestones || []).find(m => m.key === t.milestone);
    const b = (a, label, cls = 'soft') => `<button class="btn ${cls}" type="button" data-gst="${a}" data-id="${esc(t.number)}">${label}</button>`;
    const VC = {'COMPLETE': 'ok', 'COMPLETE WITH NOTES': 'warn', 'BLOCKED': 'bad', 'NOT ASSESSED': ''};
    const IC = {covered: '✓', failed: '✕', untested: '○'};
    const rv = t.review || {};
    const writes = t.role_mode === 'writes';
    return `<div class="gs-task gs-p${num(t.priority)}"><div class="gs-th"><b>${esc(t.number)}</b> ${esc(t.title)}</div>
      <div class="gs-meta"><span class="gs-role${writes ? ' gs-writes' : ''}" title="${writes ? 'Writes a result for your OK' : 'Changes the game'}">${esc(t.role_name || '')}</span>
        ${esc(ms ? ms.name : t.milestone)}${t.source !== 'her' ? ' · by Hoola' : ''}${t.version ? ' · v' + num(t.version) : ''}</div>
      ${t.detail ? `<div class="gs-detail">${esc(t.detail)}</div>` : ''}
      ${t.notes && t.status === 'review' ? (writes ? `<details class="gs-writeup" open><summary>${esc(t.role_name)}'s result</summary><pre>${esc(t.notes)}</pre></details>` : `<div class="gs-detail">${esc(t.notes)}</div>`) : ''}
      ${t.error ? `<div class="badc em-small">${esc(t.error)}</div>` : ''}
      ${(t.criteria || []).length ? `<ul class="gs-crit">${t.criteria.map(c => `<li class="gs-c-${esc(c.status)}" title="${esc(c.by === 'her' ? 'Only you can judge this' : c.by === 'test' ? "Hoola's automatic play run" : 'Seen in a screenshot')}"><span>${IC[c.status] || '○'}</span>${esc(c.text)}${(c.evidence || {}).why ? ` <span class="muted">- ${esc(c.evidence.why)}</span>` : ''}</li>`).join('')}</ul>
        ${['review', 'done'].includes(t.status) ? `<div class="gs-verdict">${tag(VC[t.verdict] || '', t.verdict)}${t.evidence_old ? ' ' + tag('warn', 'Evidence older than the code') : ''}</div>` : ''}` : ''}
      ${rv.by ? `<div class="gs-review"><b>${esc(rv.by_name || 'Lead')}</b> (saw ${num(rv.shots_seen)} screenshot${rv.shots_seen === 1 ? '' : 's'}): ${esc(rv.summary || '')}${(rv.findings || []).length ? `<ul>${rv.findings.map(f => `<li>${esc(f)}</li>`).join('')}</ul>` : ''}</div>` : ''}
      <div class="acts">${t.status === 'todo' ? b('start', writes ? 'Write it now' : 'Build now', 'go') + b('drop', 'Drop') : ''}
        ${t.status === 'review' ? b('ok', 'OK', 'go') + b('back', 'Send back') + (!writes ? b('review', rv.by ? 'Review again' : 'Ask ' + (t.reviewer || 'the lead').replace(/_/g, ' ') + ' to review') : '') : ''}
        ${t.status === 'blocked' ? b('start', 'Try again', 'go') + b('drop', 'Drop') : ''}
        ${t.status === 'done' ? b('back', 'Undo') : ''}</div></div>`;
  }
  // ---------------------------------------------------------------- v0.395 Game Bible (specs as data)
  const BIB_COLS = {character: ['role', 'age'], enemy: ['tier', 'hp', 'damage', 'speed', 'behaviour'], item: ['tier', 'effect', 'value', 'price'],
                    level: ['order', 'duration_s', 'reward_coins'], quest: ['goal', 'target', 'count'], screen: ['purpose']};
  function bibChip(c) { return `<span class="gb-chip" style="background:${/^#[0-9A-Fa-f]{6}$/.test(c) ? c : 'transparent'}" title="${esc(c)}"></span>`; }
  async function gsBible(el, id) {
    clearTimeout(GTIMER);
    let v;
    try { v = await api('GET', `/api/gamestudio/${encodeURIComponent(id)}/bible`); }
    catch (e) { toast(e.message, true); GS_BIBLE = false; return gsBoard(el, id); }
    const d = v.data || {}, ck = v.check || {}, dr = v.draft || {}, st = d.style || {}, pl = d.player || {};
    const q = encodeURIComponent(id);
    const kinds = Object.keys(v.templates || {});
    const tbl = k => {
      const rows = (d.entities || {})[k] || [], cols = BIB_COLS[k] || [];
      return `<section class="tile gl gb-kind"><div class="em-h"><h3>${esc(v.templates[k].label)}s <span class="muted">${num(rows.length)}</span></h3>
        <div class="acts"><button class="btn soft" type="button" data-gb-add="${esc(k)}">Add</button>
          <input data-gb-words="${esc(k)}" maxlength="300" placeholder="Generate: e.g. 3 night enemies" aria-label="What to generate">
          <button class="btn soft" type="button" data-gb-gen="${esc(k)}">Generate</button></div></div>
        ${rows.length ? `<div class="gb-scroll"><table class="gb-t"><thead><tr><th>id</th><th>Name</th>${cols.map(c => `<th>${esc(c)}</th>`).join('')}<th></th></tr></thead><tbody>
          ${rows.map(e => `<tr><td><code>${esc(e.id)}</code></td><td>${e.color ? bibChip(e.color) : ''}${esc(e.name || '')}</td>${cols.map(c => `<td>${esc(String(e[c] ?? ''))}</td>`).join('')}
            <td class="gb-rowacts"><button class="btn soft gs-mini" type="button" data-gb-edit="${esc(k)}" data-id="${esc(e.id)}">Edit</button>
            <button class="btn soft gs-mini em-leave" type="button" data-gb-del="${esc(k)}" data-id="${esc(e.id)}">Remove</button></td></tr>`).join('')}</tbody></table></div>`
          : '<p class="muted em-small">None yet.</p>'}
        <div class="gb-editor" data-gb-ed="${esc(k)}" hidden><textarea rows="10" spellcheck="false" aria-label="Entry as JSON"></textarea>
          <div class="acts"><button class="btn go" type="button" data-gb-save="${esc(k)}">Save</button><button class="btn soft" type="button" data-gb-cancel="${esc(k)}">Cancel</button></div></div></section>`;
    };
    const sim = GS_SIM && GS_SIM.id === id ? GS_SIM.r : null;
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="gbBack">← Board</button><h2>Game Bible</h2>
        <span class="muted em-sub">v${num(v.version)} · in the game: v${num(v.applied)}</span>
        ${v.version > v.applied ? '<button class="btn go" type="button" id="gbApply">Put it in the game</button>' : ''}
        <button class="btn soft" type="button" id="gbSim">Simulate balance</button></div>
      <p class="muted em-sub">The game's names and numbers as data. Every change is checked; the game reads it, so a balance change rebuilds with no new code.</p>
      ${(ck.errors || []).length ? `<div class="tile gl badc"><b>Fix first</b><ul>${ck.errors.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}
      ${(ck.warnings || []).length ? `<div class="tile gl"><b>Worth a look</b><ul class="gs-log">${ck.warnings.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}
      ${dr.kind ? `<div class="tile gl gb-draft"><h3>Draft from Hoola, waiting for your OK</h3>
        ${dr.kind === 'seed' ? '<p class="em-small">A first Bible from the design doc.</p>' : `<ul class="gs-log">${(dr.add || []).map(e => `<li>${e.color ? bibChip(e.color) : ''}<b>${esc(e.name)}</b> <code>${esc(e.id)}</code>
          ${(BIB_COLS[dr.kind] || []).map(c => `<span class="muted">${esc(c)} ${esc(String(e[c] ?? ''))}</span>`).join(' · ')}</li>`).join('')}</ul>`}
        ${((dr.check || {}).errors || []).length ? `<p class="badc em-small">${esc(dr.check.errors.slice(0, 3).join('; '))}</p>` : ''}
        <div class="acts"><button class="btn go" type="button" id="gbOk">OK, add to the Bible</button><button class="btn soft" type="button" id="gbNo">No</button></div></div>` : ''}
      ${!v.version && !dr.kind ? '<div class="tile gl"><p>The Bible is empty.</p><div class="acts"><button class="btn go" type="button" id="gbSeed">Make the first Bible from the design doc</button></div></div>' : ''}
      ${sim ? `<section class="tile gl"><h3>Balance (${num(sim.runs)} plays a level, same Bible = same numbers)</h3>
        ${sim.ok ? `<div class="gb-sim">${sim.levels.map(r => `<div class="gb-lv"><span>${esc(r.name)}</span><div class="pbar"><i style="width:${Math.round(r.win_rate * 100)}%"></i></div><b>${Math.round(r.win_rate * 100)}% win</b>
          <span class="muted">${num(r.avg_coins)} coins</span></div>`).join('') || '<p class="muted">No levels yet.</p>'}</div>
          ${sim.flags.length ? `<ul class="gs-log">${sim.flags.map(f => `<li>${esc(f)}</li>`).join('')}</ul>` : '<p class="em-small">No balance problems found.</p>'}
          ${(sim.economy.items || []).length ? `<p class="em-small">${sim.economy.items.map(i => `${esc(i.name)} (${num(i.price)}): ${i.levels_to_afford ? 'after level ' + num(i.levels_to_afford) : 'never affordable'}`).join(' · ')}</p>` : ''}`
          : `<p class="badc em-small">${esc((sim.errors || []).join('; '))}</p>`}</section>` : ''}
      <div class="gs-grid">
        <section class="tile gl"><h3>Style</h3><div class="gb-pal">${(st.palette || []).map(bibChip).join('')}</div>
          <div class="acts"><input id="gbPal" value="${esc((st.palette || []).join(', '))}" placeholder="#101820, #FFB000, ..." aria-label="Palette"><button class="btn soft" type="button" id="gbPalSave">Save palette</button></div>
          <p class="muted em-small">Every colour in the Bible must come from this palette.</p></section>
        <section class="tile gl"><h3>Player</h3><div class="gb-pl">${['hp', 'damage', 'fire_rate', 'hit_chance', 'speed'].map(k => `<label>${esc(k)} <input type="number" step="any" data-gb-pl="${k}" value="${esc(String(pl[k] ?? ''))}"></label>`).join('')}</div>
          <div class="acts"><button class="btn soft" type="button" id="gbPlSave">Save player</button></div></section>
        <section class="tile gl"><h3>Curves</h3><p class="muted em-small">How numbers grow by tier: [base, growth]. Enemies, items and levels take their numbers from here.</p>
          <textarea id="gbCurves" rows="7" spellcheck="false" aria-label="Curves">${esc(JSON.stringify(d.curves || {}, null, 1))}</textarea>
          <div class="acts"><button class="btn soft" type="button" id="gbCurSave">Save curves</button>${['enemy', 'item', 'level'].map(k => `<button class="btn soft gs-mini" type="button" data-gb-recurve="${k}">Re-make ${k} numbers</button>`).join('')}</div></section>
      </div>
      ${kinds.map(tbl).join('')}
      <section class="tile gl"><h3>Changes</h3><ul class="gs-log">${(v.history || []).map(h => `<li><b>v${num(h.v)}</b> ${esc(h.what)} <span class="muted">${esc((h.at || '').slice(0, 16).replace('T', ' '))} · ${esc(h.by)}</span></li>`).join('')}</ul></section>`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsBible(el, id); };
    el.querySelector('#gbBack').addEventListener('click', () => { GS_BIBLE = false; gsBoard(el, id); });
    el.querySelector('#gbApply')?.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/bible/apply`), 'Rebuilding the game with the Bible (no new code).'));
    el.querySelector('#gbSim').addEventListener('click', async e => {
      e.target.disabled = true; e.target.textContent = 'Simulating…';
      try { GS_SIM = {id, r: await api('POST', `/api/gamestudio/${q}/bible/simulate`, {})}; } catch (err) { toast(err.message, true); }
      gsBible(el, id);
    });
    el.querySelector('#gbOk')?.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/bible/accept`, {}), 'Added to the Bible.'));
    el.querySelector('#gbNo')?.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/bible/reject`, {})));
    el.querySelector('#gbSeed')?.addEventListener('click', e => { e.target.disabled = true; e.target.textContent = 'Reading the design…';
      go(() => api('POST', `/api/gamestudio/${q}/bible/seed`, {}), 'A draft Bible is ready for your OK.'); });
    el.querySelector('#gbPalSave').addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/bible/section`,
      {section: 'style', value: {palette: el.querySelector('#gbPal').value.split(/[\s,]+/).filter(Boolean)}}), 'Saved.'));
    el.querySelector('#gbPlSave').addEventListener('click', () => {
      const value = {}; el.querySelectorAll('[data-gb-pl]').forEach(i => { if (i.value !== '') value[i.dataset.gbPl] = Number(i.value); });
      go(() => api('POST', `/api/gamestudio/${q}/bible/section`, {section: 'player', value}), 'Saved.');
    });
    el.querySelector('#gbCurSave').addEventListener('click', () => {
      let value; try { value = JSON.parse(el.querySelector('#gbCurves').value); } catch { toast('Curves must be JSON.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/bible/section`, {section: 'curves', value}), 'Saved.');
    });
    el.querySelectorAll('[data-gb-recurve]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/bible/recurve`, {kind: b.dataset.gbRecurve}), 'Numbers re-made from the curves.')));
    const editor = (k, obj) => {
      const box = el.querySelector(`[data-gb-ed="${CSS.escape(k)}"]`); box.hidden = false;
      box.querySelector('textarea').value = JSON.stringify(obj, null, 1); box.querySelector('textarea').focus();
    };
    el.querySelectorAll('[data-gb-add]').forEach(b => b.addEventListener('click', () => {
      const t = v.templates[b.dataset.gbAdd].fields, obj = {id: ''};
      Object.entries(t).forEach(([f, o]) => { obj[f] = o.default; });
      editor(b.dataset.gbAdd, obj);
    }));
    el.querySelectorAll('[data-gb-edit]').forEach(b => b.addEventListener('click', () => {
      const e = ((d.entities || {})[b.dataset.gbEdit] || []).find(x => x.id === b.dataset.id); if (e) editor(b.dataset.gbEdit, e);
    }));
    el.querySelectorAll('[data-gb-cancel]').forEach(b => b.addEventListener('click', () => { el.querySelector(`[data-gb-ed="${CSS.escape(b.dataset.gbCancel)}"]`).hidden = true; }));
    el.querySelectorAll('[data-gb-save]').forEach(b => b.addEventListener('click', () => {
      const k = b.dataset.gbSave; let entity;
      try { entity = JSON.parse(el.querySelector(`[data-gb-ed="${CSS.escape(k)}"] textarea`).value); } catch { toast('The entry must be JSON.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/bible/entity`, {kind: k, entity}), 'Saved.');
    }));
    el.querySelectorAll('[data-gb-del]').forEach(b => b.addEventListener('click', () => {
      if (confirm(`Remove ${b.dataset.id} from the Bible?`)) go(() => api('DELETE', `/api/gamestudio/${q}/bible/entity/${encodeURIComponent(b.dataset.gbDel)}/${encodeURIComponent(b.dataset.id)}`));
    }));
    el.querySelectorAll('[data-gb-gen]').forEach(b => b.addEventListener('click', () => {
      const k = b.dataset.gbGen, words = el.querySelector(`[data-gb-words="${CSS.escape(k)}"]`).value.trim();
      const m = words.match(/\b(\d{1,2})\b/); b.disabled = true; b.textContent = 'Writing…';
      go(() => api('POST', `/api/gamestudio/${q}/bible/generate`, {kind: k, n: m ? Number(m[1]) : 3, words}), 'A draft is ready for your OK.');
    }));
  }

  // ---------------------------------------------------------------- v0.416 asset pipeline
  const AST_ST = {priced: ['warn', 'Waiting for your tap'], making: ['v', 'Being made'], draft: ['warn', 'Waiting for your OK'],
                  approved: ['ok', 'In the game'], rejected: ['', 'Not used'], failed: ['bad', 'Failed its checks']};
  function astPreview(a) {
    if (!a.url) return '<div class="ga-empty">—</div>';
    const u = esc(a.url);
    if (['sprite', 'icon', 'ui', 'background'].includes(a.kind)) return `<img src="${u}" alt="${esc(a.key)}" class="ga-img ga-${esc(a.kind)}" loading="lazy">`;
    if (['sfx', 'music', 'voice'].includes(a.kind)) return `<audio controls preload="none" src="${u}"></audio>`;
    return `<a class="btn soft gs-mini" href="${u}" download="${esc(a.key)}.glb">Download GLB</a>`;
  }
  async function gsAssets(el, id) {
    clearTimeout(GTIMER);
    let v;
    const q = encodeURIComponent(id);
    try { v = await api('GET', `/api/gamestudio/${q}/assets`); }
    catch (e) { toast(e.message, true); GS_ASSETS = false; return gsBoard(el, id); }
    const kinds = v.kinds || {}, card = v.card || {items: [], total_inr: 0};
    const byKind = {};
    (v.assets || []).forEach(a => { (byKind[a.kind] = byKind[a.kind] || []).push(a); });
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="gaBack">← Board</button><h2>Assets</h2>
        <span class="muted em-sub">${num(v.in_game)} in the game · ₹${num(v.spent_inr)} spent</span>
        <button class="btn go" type="button" id="gaApply">Put approved assets in the game</button>
        <button class="btn soft" type="button" id="gaSug">What does the game still need?</button></div>
      <p class="muted em-sub">Art follows the Game Bible palette. Sounds are made in code (free). Pictures, music and voice cost money: they wait on a price card until you tap it. Nothing enters the game before your OK.</p>
      ${card.items.length ? `<div class="tile gl ga-card"><b>Price card: ₹${num(card.total_inr)}</b> for ${num(card.items.length)} asset${card.items.length === 1 ? '' : 's'}
        <ul class="gs-log">${card.items.map(i => `<li><label><input type="checkbox" data-ga-pick="${esc(i.id)}" checked> ${esc(i.key)} <span class="muted">${esc(i.kind)} · ₹${num(i.cost_inr)}</span></label></li>`).join('')}</ul>
        <div class="acts"><button class="btn go" type="button" id="gaSpend">Make the ticked ones</button></div></div>` : ''}
      <div id="gaSugBox"></div>
      <div class="tile gl ga-new"><h3>New asset</h3>
        <div class="acts"><select id="gaKind" aria-label="Kind">${Object.entries(kinds).map(([k, x]) => `<option value="${esc(k)}">${esc(x.label)}${x.cost_inr ? ' (about ₹' + num(x.cost_inr) + ')' : ' (free)'}</option>`).join('')}</select>
          <input id="gaKey" maxlength="40" placeholder="key, e.g. red_bat (Bible id)" aria-label="Key">
          <input id="gaWords" maxlength="600" placeholder="What it is, e.g. a red bat with big ears, side view" aria-label="Description"></div>
        <div class="acts"><select id="gaPreset" aria-label="Sound preset">${(v.presets || []).map(p => `<option>${esc(p)}</option>`).join('')}</select>
          <input id="gaSeed" type="number" min="1" value="1" aria-label="Sound seed" title="Seed: the same seed makes the same sound">
          <input id="gaText" maxlength="400" placeholder="Voice line text" aria-label="Voice text">
          <select id="gaLock" aria-label="Palette lock"><option value="check">Palette: check</option><option value="strict">Palette: snap every pixel</option><option value="off">Palette: off</option></select>
          <select id="gaQ" aria-label="Quality"><option value="fast">Fast (₹3)</option><option value="best">Best (₹12)</option></select>
          <button class="btn go" type="button" id="gaMake">Make / price it</button>
          <label class="btn soft ga-up">Upload my file<input type="file" id="gaFile" accept=".png,.jpg,.jpeg,.wav,.ogg,.mp3,.glb" hidden></label></div></div>
      ${Object.keys(kinds).filter(k => byKind[k]).map(k => `<section class="tile gl"><h3>${esc(kinds[k].label)}s <span class="muted">${num(byKind[k].length)}</span></h3>
        <div class="ga-grid">${byKind[k].map(a => { const [c, n] = AST_ST[a.status] || ['', a.status]; const ck = a.checks || {};
          return `<div class="ga-item"><div class="ga-prev">${astPreview(a)}</div><div class="ga-h"><b>${esc(a.key)}</b> ${tag(c, n)}</div>
            <div class="gs-meta">v${num(a.version)}${a.approved ? ' · in game: v' + num(a.approved) : ''}${a.meta && a.meta.w ? ' · ' + num(a.meta.w) + '×' + num(a.meta.h) : ''}${a.meta && a.meta.seconds ? ' · ' + num(a.meta.seconds) + ' s' : ''}${a.meta && a.meta.palette_share != null ? ' · palette ' + Math.round(a.meta.palette_share * 100) + '%' : ''}${a.source ? ' · ' + esc(a.source) : ''}</div>
            ${a.words ? `<div class="gs-detail">${esc(a.words)}</div>` : ''}
            ${(ck.errors || []).map(x => `<div class="badc em-small">${esc(x)}</div>`).join('')}${(ck.warnings || []).map(x => `<div class="muted em-small">${esc(x)}</div>`).join('')}
            ${a.error && !(ck.errors || []).length ? `<div class="badc em-small">${esc(a.error)}</div>` : ''}
            <div class="acts">${a.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-ga="approve" data-key="${esc(a.key)}">OK, use it</button><button class="btn soft gs-mini" type="button" data-ga="reject" data-key="${esc(a.key)}">No</button>` : ''}
              ${a.kind === 'sfx' && a.status !== 'making' ? `<button class="btn soft gs-mini" type="button" data-ga-again="${esc(a.key)}" data-preset="${esc((a.spec || {}).preset || '')}" data-seed="${num(((a.spec || {}).seed || 1) + 1)}">Another one</button>` : ''}
              ${a.status !== 'making' ? `<button class="btn soft gs-mini em-leave" type="button" data-ga="remove" data-key="${esc(a.key)}">Remove</button>` : ''}</div></div>`; }).join('')}</div></section>`).join('') || '<div class="empty">No assets yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsAssets(el, id); };
    el.querySelector('#gaBack').addEventListener('click', () => { GS_ASSETS = false; gsBoard(el, id); });
    el.querySelector('#gaApply').addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/assets-apply`), 'Rebuilding the game with the approved assets (no new code).'));
    el.querySelector('#gaSpend')?.addEventListener('click', () => {
      const ids = [...el.querySelectorAll('[data-ga-pick]:checked')].map(x => x.dataset.gaPick);
      if (!ids.length) { toast('Tick at least one.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/assets/spend`, {ids}), 'Making them. Each one waits for your OK.');
    });
    el.querySelector('#gaSug').addEventListener('click', async () => {
      try { const r = await api('GET', `/api/gamestudio/${q}/assets/suggest`);
        el.querySelector('#gaSugBox').innerHTML = r.suggest.length ? `<div class="tile gl"><b>The game still needs</b><ul class="gs-log">${r.suggest.map(x => `<li>${esc(x.key)} <span class="muted">${esc(x.kind)} · ${x.cost_inr ? '₹' + num(x.cost_inr) : 'free'}</span> ${esc(x.words || '')}
          <button class="btn soft gs-mini" type="button" data-ga-sug='${esc(JSON.stringify(x))}'>${x.cost_inr ? 'Price it' : 'Make it'}</button></li>`).join('')}</ul></div>` : '<p class="muted em-small">Nothing missing for the Bible\'s entries.</p>';
        el.querySelectorAll('[data-ga-sug]').forEach(b => b.addEventListener('click', () => { const x = JSON.parse(b.dataset.gaSug);
          go(() => api('POST', `/api/gamestudio/${q}/assets`, {kind: x.kind, key: x.key, words: x.words, preset: x.preset}), x.cost_inr ? 'Added to the price card.' : 'Making it.'); }));
      } catch (e) { toast(e.message, true); }
    });
    el.querySelector('#gaMake').addEventListener('click', () => {
      const kind = el.querySelector('#gaKind').value, key = el.querySelector('#gaKey').value.trim(), words = el.querySelector('#gaWords').value.trim();
      if (!key && !words) { toast('Give it a key or a description.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/assets`, {kind, key, words, preset: el.querySelector('#gaPreset').value, seed: Number(el.querySelector('#gaSeed').value) || 1,
        text: el.querySelector('#gaText').value.trim(), palette_lock: el.querySelector('#gaLock').value, quality: el.querySelector('#gaQ').value}),
        (kinds[kind] || {}).cost_inr ? 'On the price card: tap it to make.' : 'Making it.');
    });
    el.querySelector('#gaFile').addEventListener('change', e => {
      const f = e.target.files[0]; if (!f) return;
      if (f.size > 12 * 1024 * 1024) { toast('12 MB at most.', true); return; }
      const key = el.querySelector('#gaKey').value.trim() || f.name.replace(/\.[^.]+$/, '');
      const fr = new FileReader();
      fr.onload = () => go(() => api('POST', `/api/gamestudio/${q}/assets/upload`, {kind: el.querySelector('#gaKind').value, key, words: el.querySelector('#gaWords').value.trim(),
        data: String(fr.result).split(',')[1] || ''}), 'Checked. It waits for your OK.');
      fr.readAsDataURL(f);
    });
    el.querySelectorAll('[data-ga]').forEach(b => b.addEventListener('click', () => {
      if (b.dataset.ga === 'remove' && !confirm(`Remove ${b.dataset.key} and all its versions?`)) return;
      go(() => api('POST', `/api/gamestudio/${q}/assets/${encodeURIComponent(b.dataset.key)}/${b.dataset.ga}`, {}));
    }));
    el.querySelectorAll('[data-ga-again]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/assets`,
      {kind: 'sfx', key: b.dataset.gaAgain, preset: b.dataset.preset, seed: Number(b.dataset.seed)}), 'A new version is being made.')));
    if ((v.assets || []).some(a => a.status === 'making')) GTIMER = setTimeout(() => { if (visible(el) && GS_ASSETS) gsAssets(el, id); }, 5000);
  }

  // ---------------------------------------------------------------- v0.416 QA farm + bug tracker
  const QV = {PASS: 'ok', CONCERNS: 'warn', FAIL: 'bad', 'NOT ASSESSED': ''};
  const BUG_ST = {open: ['bad', 'Open'], fixing: ['warn', 'Being fixed'], fixed: ['ok', 'Fixed (bot checked)'], wontfix: ['', "Won't fix"], duplicate: ['', 'Duplicate']};
  async function gsQa(el, id) {
    clearTimeout(GTIMER);
    const q = encodeURIComponent(id);
    let d;
    try { d = await api('GET', `/api/gamestudio/${q}/qa`); }
    catch (e) { toast(e.message, true); GS_QA = false; return gsBoard(el, id); }
    const L = d.last || {}, gl = L.golden || {}, pf = L.perf || {};
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="qaBack">← Board</button><h2>QA</h2>
        ${L.verdict ? tag(QV[L.verdict] || '', L.verdict) : ''}<span class="muted em-sub">${L.at ? 'v' + num(L.version) + ' · ' + esc((L.at || '').slice(0, 16).replace('T', ' ')) : 'Not run yet'}</span>
        <button class="btn go" type="button" id="qaRun"${d.running ? ' disabled' : ''}>${d.running ? 'Bots are playing…' : 'Run the QA bots now'}</button></div>
      <p class="muted em-sub">Hoola's bots play a debug build of the game on desktop, mid-range phone and low-end phone speeds every night, the same way each time. A bug the bots find is fixed only when the same bot can no longer find it.</p>
      ${L.verdict ? `<div class="tile gl qa-sum">${(L.blockers || []).map(x => `<div class="em-small">${tag('bad', 'Blocker')} ${esc(x)}</div>`).join('')}
        ${(L.concerns || []).map(x => `<div class="em-small">${tag('warn', 'Concern')} ${esc(x)}</div>`).join('')}
        ${(L.missing || []).map(x => `<div class="em-small">${tag('', 'Not assessed')} ${esc(x)}</div>`).join('')}
        <div class="gd-nums">${pf.fps_avg ? `<span><b>${num(pf.fps_avg)}</b> fps average</span>` : ''}${pf.mid_phone_fps ? `<span><b>${num(pf.mid_phone_fps)}</b> fps on a mid phone</span>` : ''}${pf.load_s ? `<span><b>${num(pf.load_s)}</b> s to start</span>` : ''}</div>
        ${(L.fixed || []).length ? `<p class="em-small">Fixed and checked by the bots: ${esc(L.fixed.join(', '))}</p>` : ''}</div>` : ''}
      ${gl.candidate_url ? `<section class="tile gl"><h3>Start screen</h3><div class="qa-gold">
          ${gl.golden_url ? `<figure><img src="${esc(gl.golden_url)}" alt="Golden start screen"><figcaption>Golden (approved)</figcaption></figure>` : ''}
          <figure><img src="${esc(gl.candidate_url)}" alt="This run's start screen"><figcaption>This run${gl.diff != null ? ' · ' + (Math.round(gl.diff * 1000) / 10) + '% different' : ''}</figcaption></figure></div>
        ${gl.verdict !== 'same' ? '<div class="acts"><button class="btn soft" type="button" id="qaGold">This is how it should look</button></div>' : ''}</section>` : ''}
      ${(L.runs || []).length ? `<section class="tile gl"><h3>Bot runs</h3><div class="gb-scroll"><table class="gb-t"><thead><tr><th>Bot</th><th>Speed</th><th>Result</th><th>fps</th><th>Score / state</th><th>Game overs</th><th>Shots</th></tr></thead><tbody>
        ${L.runs.map(x => `<tr><td>${esc(x.bot)} <span class="muted">#${num(x.seed)}</span></td><td>${esc(x.profile.replace('_', ' '))}</td>
          <td>${x.ok ? tag('ok', 'OK') : tag('bad', 'Error')}${(x.errors || []).length ? `<div class="badc em-small">${esc(x.errors[0])}</div>` : ''}${(x.warnings || []).map(w => `<div class="muted em-small">${esc(w)}</div>`).join('')}</td>
          <td>${x.fps != null ? num(x.fps) : '—'}</td><td>${esc(Object.entries(x.state || {}).map(([k, v]) => k + ' ' + v).join(', ') || '—')}</td><td>${num(x.game_overs || 0)}</td>
          <td class="qa-shots">${(x.shot_urls || []).map(u => `<img src="${esc(u)}" alt="Bot screenshot" loading="lazy">`).join('')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="tile gl"><h3>Bugs <span class="muted">${num(d.open)} open</span></h3>
        <div class="acts"><input id="qaBugT" maxlength="200" placeholder="Report a bug, e.g. the jump button does nothing on my phone" aria-label="Bug">
          <select id="qaBugS" aria-label="Severity"><option value="major">Major</option><option value="crash">Crash</option><option value="blocker">Blocker</option><option value="minor">Minor</option><option value="visual">Looks wrong</option><option value="perf">Slow</option></select>
          <button class="btn soft" type="button" id="qaBugAdd">Report</button></div>
        ${(d.bugs || []).map(b => { const [c, n] = BUG_ST[b.status] || ['', b.status]; return `<div class="qa-bug"><div class="ga-h"><b>${esc(b.number)}</b> ${esc(b.title)} ${tag(c, n)} ${tag(b.severity === 'crash' || b.severity === 'blocker' ? 'bad' : '', b.severity)}${b.regression ? ' ' + tag('bad', 'Came back ×' + num(b.regression)) : ''}</div>
          <div class="gs-meta">${b.source === 'her' ? 'Reported by you' : `Found by bot ${esc(b.repro.bot || '')} #${num(b.repro.seed || 1)} on ${esc((b.repro.profile || '').replace('_', ' '))}`} · seen ${num(b.seen)}× · v${num(b.first_version)}${b.last_version !== b.first_version ? '–' + num(b.last_version) : ''}${b.task ? ' · task ' + esc(b.task) : ''}</div>
          ${((b.evidence || {}).errors || []).slice(0, 2).map(e => `<div class="badc em-small">${esc(e)}</div>`).join('')}
          <div class="acts">${['open', 'fixing'].includes(b.status) && !b.task ? `<button class="btn go gs-mini" type="button" data-qb="fix" data-n="${esc(b.number)}">Fix it (make a task)</button>` : ''}
            ${['open', 'fixing'].includes(b.status) ? `<button class="btn soft gs-mini" type="button" data-qb="wontfix" data-n="${esc(b.number)}">Won't fix</button><button class="btn soft gs-mini" type="button" data-qb="duplicate" data-n="${esc(b.number)}">Duplicate</button>` : `<button class="btn soft gs-mini" type="button" data-qb="open" data-n="${esc(b.number)}">Reopen</button>`}</div></div>`; }).join('') || '<p class="muted em-small">No bugs.</p>'}</section>`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsQa(el, id); };
    el.querySelector('#qaBack').addEventListener('click', () => { GS_QA = false; gsBoard(el, id); });
    el.querySelector('#qaRun').addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/qa/run`), 'The bots are playing (2-4 minutes).'));
    el.querySelector('#qaGold')?.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/qa/golden`, {}), 'Saved as the golden start screen.'));
    el.querySelector('#qaBugAdd').addEventListener('click', () => { const title = el.querySelector('#qaBugT').value.trim();
      if (title.length < 4) { toast('Write the bug in one line.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/bugs`, {title, severity: el.querySelector('#qaBugS').value}), 'Bug saved.'); });
    el.querySelectorAll('[data-qb]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/bugs/${encodeURIComponent(b.dataset.n)}/${b.dataset.qb}`),
      b.dataset.qb === 'fix' ? 'A fix task is on the board. The bug closes when the same bot cannot find it again.' : '')));
    if (d.running) GTIMER = setTimeout(() => { if (visible(el) && GS_QA) gsQa(el, id); }, 8000);
  }

  // ---------------------------------------------------------------- v0.416 platforms: downloads, store kit, itch.io
  const PL = {linux: 'Linux', windows: 'Windows', macos: 'macOS', android: 'Android'};
  const RST = {done: ['ok', 'Ready'], building: ['v', 'Building'], queued: ['v', 'Queued'], failed: ['bad', 'Failed'], 'not assessed': ['', 'Not built here']};
  let GS_KIT = null;
  async function gsRelease(el, id) {
    clearTimeout(GTIMER);
    const q = encodeURIComponent(id);
    let d;
    try { d = await api('GET', `/api/gamestudio/${q}/releases`); }
    catch (e) { toast(e.message, true); GS_REL = false; return gsBoard(el, id); }
    const tg = d.targets || {}, kit = GS_KIT && GS_KIT.id === id ? GS_KIT.k : null;
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="relBack">← Board</button><h2>Release</h2>
        <span class="muted em-sub">${esc((d.identity || {}).package || '')}</span></div>
      <p class="muted em-sub">Real downloads of the live game. Linux, Windows and macOS are built on Hoola's server; Android (APK to install, AAB for Google Play) in your private builds repo, signed with this game's own upload key. Nothing is published unless you tap.</p>
      <div class="tile gl rel-new"><h3>New release</h3><div class="acts">${Object.keys(PL).map(p => `<label class="gs-sw"><input type="checkbox" data-rel-p="${p}"${tg[p] && tg[p].ready ? ' checked' : ''}> ${PL[p]}${tg[p] && !tg[p].ready ? ` <span class="muted em-small">(${esc(tg[p].note)})</span>` : ''}</label>`).join('')}</div>
        <div class="acts"><select id="relFmt" aria-label="Android format"><option value="apk">Android: APK (install on a phone)</option><option value="aab">Android: AAB (Google Play)</option></select>
          <button class="btn go" type="button" id="relGo">Build the release</button></div></div>
      ${(d.releases || []).map(r => `<section class="tile gl"><div class="em-h"><h3>${esc(r.number)} · ${esc(r.version_name)} <span class="muted">game v${num(r.version)}</span></h3>${tag(r.status === 'done' ? 'ok' : r.status === 'failed' ? 'bad' : r.status === 'building' ? 'v' : 'warn', r.status)}</div>
        <div class="rel-grid">${Object.entries(r.platforms || {}).map(([p, x]) => { const [c, n] = RST[x.status] || ['', x.status]; return `<div class="rel-item"><b>${esc(PL[p] || p)}</b> ${tag(c, n)}
          ${x.mb ? `<span class="muted em-small">${num(x.mb)} MB${x.format ? ' · ' + esc(x.format.toUpperCase()) : ''}</span>` : ''}
          ${x.url ? `<a class="btn go gs-mini" href="${esc(x.url)}">Download</a>` : ''}${x.note ? `<div class="muted em-small">${esc(x.note)}</div>` : ''}
          ${((x.checks || {}).errors || []).map(e => `<div class="badc em-small">${esc(e)}</div>`).join('')}${((x.checks || {}).warnings || []).map(w => `<div class="muted em-small">${esc(w)}</div>`).join('')}</div>`; }).join('')}</div>
        ${['done', 'partial'].includes(r.status) ? `<div class="acts rel-itch">${(r.itch || {}).card && r.itch.card.hash ? `<b>itch.io card:</b> ${esc(r.itch.card.target)} (${esc(Object.keys(r.itch.card.files || {}).join(', '))})
            <button class="btn go gs-mini" type="button" data-itch-push="${esc(r.id)}" data-hash="${esc(r.itch.card.hash)}">Yes, upload to itch.io</button>` :
          `<input data-itch-t="${esc(r.id)}" maxlength="140" placeholder="itch.io page: your-name/game-name" aria-label="itch.io page"><button class="btn soft gs-mini" type="button" data-itch-card="${esc(r.id)}">Prepare itch.io upload</button>`}
          ${((r.itch || {}).pushed || []).slice(-1).map(p => `<span class="muted em-small">Last upload ${esc((p.at || '').slice(0, 16).replace('T', ' '))}: ${esc(p.results.map(x => x.platform + (x.ok ? ' ok' : ' failed')).join(', '))}</span>`).join('')}</div>` : ''}
      </section>`).join('') || '<div class="empty">No releases yet.</div>'}
      <section class="tile gl"><h3>itch.io key</h3><p class="muted em-small">${d.itch_key ? 'Your itch.io key is saved (sealed). Paste a new one to replace it.' : 'From itch.io > Settings > API keys. Only typed here, never in chat.'}</p>
        <div class="acts"><input id="relKey" type="password" autocomplete="off" maxlength="80" placeholder="itch.io API key" aria-label="itch.io API key"><button class="btn soft" type="button" id="relKeySave">Save key</button></div></section>
      <section class="tile gl"><h3>Store kit</h3><p class="muted em-small">Store texts for itch.io, Steam and Google Play within their limits, store images in the exact sizes, the AI disclosure, an age-rating draft and the Steam upload scripts. Nothing is published.</p>
        <div class="acts"><button class="btn soft" type="button" id="relKit">${kit ? 'Write it again' : 'Make the store kit'}</button>${kit ? `<a class="btn go" href="${esc(kit.zip)}">Download the kit (ZIP)</a>` : ''}</div>
        ${kit ? `<div class="rel-kit">${['itch', 'steam', 'play'].map(st => `<div><h4>${{itch: 'itch.io', steam: 'Steam', play: 'Google Play'}[st]}</h4>${Object.entries(kit[st] || {}).map(([k, v]) => `<p class="em-small"><b>${esc(k)}:</b> ${esc(Array.isArray(v) ? v.join(', ') : String(v))}</p>`).join('')}</div>`).join('')}</div>
          <p class="em-small"><b>AI disclosure:</b> ${esc(kit.ai_disclosure)}</p>
          <p class="em-small"><b>Age rating draft:</b> ${esc(Object.entries(kit.rating.expected).map(([k, v]) => k + ' ' + v).join(' · '))} - ${esc(kit.rating.note)}</p>
          ${(kit.notes || []).map(n => `<p class="muted em-small">${esc(n)}</p>`).join('')}` : ''}</section>`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsRelease(el, id); };
    el.querySelector('#relBack').addEventListener('click', () => { GS_REL = false; gsBoard(el, id); });
    el.querySelector('#relGo').addEventListener('click', () => {
      const platforms = [...el.querySelectorAll('[data-rel-p]:checked')].map(x => x.dataset.relP);
      if (!platforms.length) { toast('Pick at least one platform.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/releases`, {platforms, android_format: el.querySelector('#relFmt').value}), 'Building the release.');
    });
    el.querySelector('#relKeySave').addEventListener('click', () => { const key = el.querySelector('#relKey').value.trim(); if (!key) return;
      go(() => api('POST', '/api/gamestudio/itch-key', {key}), 'Saved and sealed.'); });
    el.querySelector('#relKit').addEventListener('click', async e => { e.target.disabled = true; e.target.textContent = 'Writing…';
      try { GS_KIT = {id, k: await api('GET', `/api/gamestudio/${q}/store-kit${GS_KIT && GS_KIT.id === id ? '?regen=true' : ''}`)}; } catch (err) { toast(err.message, true); }
      gsRelease(el, id); });
    el.querySelectorAll('[data-itch-card]').forEach(b => b.addEventListener('click', () => {
      const target = el.querySelector(`[data-itch-t="${CSS.escape(b.dataset.itchCard)}"]`).value.trim();
      go(() => api('POST', `/api/gamestudio/${q}/releases/${encodeURIComponent(b.dataset.itchCard)}/itch`, {target}), 'The upload card is ready: check it, then tap Yes.');
    }));
    el.querySelectorAll('[data-itch-push]').forEach(b => b.addEventListener('click', () => {
      if (!confirm('Upload these files to your itch.io page now?')) return;
      b.disabled = true; b.textContent = 'Uploading…';
      go(() => api('POST', `/api/gamestudio/${q}/releases/${encodeURIComponent(b.dataset.itchPush)}/itch/push`, {hash: b.dataset.hash}), 'Uploaded to itch.io.');
    }));
    if ((d.releases || []).some(r => r.status === 'building')) GTIMER = setTimeout(() => { if (visible(el) && GS_REL) gsRelease(el, id); }, 6000);
  }

  // ---------------------------------------------------------------- v0.420 Game Desk roles: Worlds + Physics
  const WST = {draft: ['warn', 'Waiting for your OK'], approved: ['ok', 'In the game'], rejected: ['', 'Not used'], failed: ['bad', 'Failed its checks'],
               testing: ['v', 'Lab running']};
  function roleBack(el) { GS_ROLE = ''; if (GS_ROLE_SID) { GS_OPEN = GS_ROLE_SID; gsBoard(el, GS_ROLE_SID); } else game(el); }
  function checkList(ch) {
    return `${(ch.errors || []).map(e => `<div class="badc em-small">✕ ${esc(e)}</div>`).join('')}${(ch.warnings || []).map(w => `<div class="muted em-small">! ${esc(w)}</div>`).join('')}
      ${(ch.passed || []).map(x => `<div class="em-small">✓ ${esc(x)}</div>`).join('')}`;
  }
  async function gsWorld(el) {
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', '/api/gamedesk/worlds' + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="wdBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>Worlds</h2>
        ${d.hired ? tag('ok', 'Procedural World Engineer hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">Worlds made from rules and a seed by code (no AI picture, free). Each one is made twice to prove the same seed gives the same world, and every village, room, exit and goal is checked reachable. Nothing goes into your game before your OK.</p>
      <div class="tile gl wd-new"><h3>New world</h3>
        <textarea id="wdWords" rows="2" maxlength="600" placeholder="e.g. a big island with two rivers and a snowy mountain · a dungeon with 15 rooms · a short platformer level, my player jumps 3 tiles up" aria-label="Your world"></textarea>
        <div class="acts"><select id="wdKind" aria-label="Kind"><option value="">Kind: from my words</option>${(d.kinds || []).map(k => `<option value="${esc(k)}">${esc(k)}</option>`).join('')}</select>
          <input id="wdSeed" type="number" min="0" placeholder="Seed (optional)" aria-label="Seed">
          <button class="btn go" type="button" id="wdGo"${d.hired ? '' : ' disabled'}>Make the world</button>
          ${sid ? '<button class="btn soft" type="button" id="wdApply">Put approved worlds in the game</button>' : ''}</div>
        ${d.hired ? '' : '<p class="muted em-small">Hire the Procedural World Generation Engineer in Employees to make worlds.</p>'}</div>
      ${(d.worlds || []).map(w => { const [c, n] = WST[w.status] || ['', w.status]; const f = w.files || {}, st = w.stats || {}, dm = w.demo || {};
        return `<section class="tile gl wd-card"><div class="em-h"><h3>${esc(w.number)} · ${esc(w.key)} <span class="muted">${esc(w.kind)} · seed ${num(w.seed)} · v${num(w.version)}</span></h3>${tag(c, n)}</div>
          <div class="wd-body">${f['preview.png'] ? `<img class="wd-prev" src="${esc(f['preview.png'])}" alt="Preview of world ${esc(w.number)}" loading="lazy">` : ''}
          <div class="wd-info"><p class="muted em-small">${num(st.w)} × ${num(st.h)} cells · made in ${num(st.ms)} ms${st.reachable_share != null ? ' · ' + Math.round(st.reachable_share * 100) + '% reachable' : ''}${st.glb ? ' · 3D mesh ' + num(st.glb.triangles) + ' triangles' : ''}</p>
            ${checkList(w.checks || {})}
            <div class="acts">${['world.json', 'heightmap.png', 'world.glb'].filter(k => f[k]).map(k => `<a class="btn soft gs-mini" href="${esc(f[k])}">${esc(k)}</a>`).join('')}</div>
            <div class="acts">${w.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-wd="approve" data-id="${esc(w.id)}">OK, use it</button><button class="btn soft gs-mini" type="button" data-wd="reject" data-id="${esc(w.id)}">No</button>` : ''}
              ${w.status !== 'failed' ? `<button class="btn soft gs-mini" type="button" data-wd="demo" data-id="${esc(w.id)}"${dm.status === 'building' ? ' disabled' : ''}>${dm.status === 'building' ? 'Building the walk-it link…' : dm.play_url ? 'Build the walk-it link again' : 'Walk it in the browser'}</button>` : ''}
              <button class="btn soft gs-mini" type="button" data-wd-again="${esc(w.id)}">Same settings, new seed</button>
              ${dm.play_url ? `<a class="btn go gs-mini" href="${esc(dm.play_url)}" target="_blank" rel="noopener">Walk it</a>` : ''}</div>
            ${dm.status === 'failed' ? `<div class="badc em-small">Walk-it link did not build: ${esc((dm.errors || []).join('; '))}</div>` : ''}
            ${dm.numbers && dm.numbers.fps_server ? `<p class="muted em-small">Played by Hoola: ${num(dm.numbers.fps_server)} fps on the server, loads in ${num(dm.numbers.load_s)} s, ${num(dm.numbers.download_mb)} MB</p>` : ''}</div></div></section>`; }).join('') || '<div class="empty">No worlds yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsWorld(el); };
    el.querySelector('#wdBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#wdGo').addEventListener('click', e => {
      const words = el.querySelector('#wdWords').value.trim(), kind = el.querySelector('#wdKind').value, seed = el.querySelector('#wdSeed').value;
      if (!words && !kind) { toast('Write your world in a line, or pick a kind.', true); return; }
      e.target.disabled = true; e.target.textContent = 'Making…';
      go(() => api('POST', '/api/gamedesk/worlds', {words, kind, seed: seed === '' ? null : Number(seed), studio: sid}), 'Made and checked.');
    });
    el.querySelector('#wdApply')?.addEventListener('click', () => go(() => api('POST', '/api/gamedesk/worlds/apply', {studio: sid}), 'Rebuilding the game with the approved worlds.'));
    el.querySelectorAll('[data-wd]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/world/${encodeURIComponent(b.dataset.id)}/${b.dataset.wd}`),
      {approve: 'Approved. Put it in the game when you are ready.', reject: '', demo: 'Building the walk-it link (under a minute).'}[b.dataset.wd])));
    el.querySelectorAll('[data-wd-again]').forEach(b => b.addEventListener('click', () => { const w = (d.worlds || []).find(x => x.id === b.dataset.wdAgain); if (!w) return;
      go(() => api('POST', '/api/gamedesk/worlds', {kind: w.kind, params: w.params, key: w.key, studio: sid}), 'A new seed, same rules.'); }));
    if ((d.worlds || []).some(w => (w.demo || {}).status === 'building')) GTIMER = setTimeout(() => { if (visible(el) && GS_ROLE === 'world') gsWorld(el); }, 5000);
  }

  async function gsPhysics(el) {
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', '/api/gamedesk/physics' + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    const df = d.defaults || {};
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="phBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>Physics</h2>
        ${d.hired ? tag('ok', 'Physics Engine Developer hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">Hoola works out the settings from your numbers, then proves them in Godot itself: free fall, a jump's range, a bounce, your fastest body against your thinnest wall (with and without continuous collision), a box stack, a 3D drop, and the whole lab twice. Every case is compared with its formula. Fluids are not part of this yet.</p>
      <div class="tile gl ph-new"><h3>New physics setup</h3>
        <div class="ph-grid"><label>Fastest body (px/s)<input id="phSpeed" type="number" min="1" value="${num(df.speed)}"></label>
          <label>Thinnest wall (px)<input id="phWall" type="number" min="1" value="${num(df.wall)}"></label>
          <label>Physics ticks / s<input id="phTicks" type="number" min="30" max="240" value="${num(df.ticks)}"></label>
          <label>Gravity (px/s²)<input id="phG" type="number" min="0" value="${num(df.gravity)}"></label></div>
        <div class="acts"><button class="btn go" type="button" id="phGo"${d.hired ? '' : ' disabled'}>Run the physics lab</button>
          ${sid ? '<button class="btn soft" type="button" id="phApply">Put approved physics in the game</button>' : ''}</div>
        ${sid ? '<p class="muted em-small">With a project, the fastest speed in your Game Bible is used when you leave the speed as it is.</p>' : ''}
        ${d.hired ? '' : '<p class="muted em-small">Hire the Physics Engine Developer in Employees to run the lab.</p>'}</div>
      ${(d.setups || []).map(x => { const [c, n] = WST[x.status] || ['', x.status]; const lab = x.lab || {}, st = x.settings || {}, i = x.inputs || {};
        return `<section class="tile gl ph-card"><div class="em-h"><h3>${esc(x.number)} <span class="muted">${num(i.speed)} px/s · ${num(i.wall)} px wall · ${num(i.ticks)} ticks · g ${num(i.gravity)}</span></h3>${tag(c, n)}${lab.verdict ? tag(lab.verdict === 'PASS' ? 'ok' : 'bad', lab.verdict + ' ' + num(lab.passed) + '/' + num(lab.total)) : ''}</div>
          <p class="em-small"><b>Settings:</b> ${num(st.ticks)} ticks · gravity ${num(st.gravity)}${st.ccd ? ' · continuous collision (cast-ray) above ' + num(st.ccd_min_speed) + ' px/s' : ''} - ${esc(st.why || '')}</p>
          ${(lab.before || {}).say ? `<p class="em-small"><b>Why:</b> ${esc(lab.before.say)}</p>` : ''}
          ${(lab.cases || []).length ? `<table class="ph-tbl"><thead><tr><th>Case</th><th>Measured</th><th>Formula</th><th></th></tr></thead><tbody>${lab.cases.map(k => `<tr><td>${esc(k.case)}<div class="muted em-small">${esc(k.note)}</div></td>
            <td>${esc(typeof k.measured === 'object' ? Object.entries(k.measured).map(([a, b]) => a + ': ' + b).join(' · ') : String(k.measured))}</td><td>${esc(String(typeof k.expected === 'object' ? Object.entries(k.expected).map(([a, b]) => a + ': ' + b).join(' · ') : k.expected))}</td>
            <td>${tag(k.ok ? 'ok' : 'bad', k.ok ? 'pass' : 'fail')}</td></tr>`).join('')}</tbody></table>` : (x.status === 'testing' ? '<p class="muted em-small">The lab is running in Godot…</p>' : '')}
          ${x.error ? `<div class="badc em-small">${esc(x.error)}</div>` : ''}
          <div class="acts">${x.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-ph="approve" data-id="${esc(x.id)}">OK, use these settings</button><button class="btn soft gs-mini" type="button" data-ph="reject" data-id="${esc(x.id)}">No</button>` : ''}</div></section>`; }).join('') || '<div class="empty">No physics setups yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsPhysics(el); };
    el.querySelector('#phBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#phGo').addEventListener('click', e => {
      const v = id => Number(el.querySelector(id).value);
      const inputs = {wall: v('#phWall'), ticks: v('#phTicks'), gravity: v('#phG')};
      if (!(sid && v('#phSpeed') === Number(df.speed))) inputs.speed = v('#phSpeed');
      e.target.disabled = true; e.target.textContent = 'Starting…';
      go(() => api('POST', '/api/gamedesk/physics', {inputs, studio: sid}), 'The lab is running in Godot.');
    });
    el.querySelector('#phApply')?.addEventListener('click', () => go(() => api('POST', '/api/gamedesk/physics/apply', {studio: sid}), 'Rebuilding the game with the approved physics.'));
    el.querySelectorAll('[data-ph]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/physics/${encodeURIComponent(b.dataset.id)}/${b.dataset.ph}`),
      b.dataset.ph === 'approve' ? 'Approved. Put it in the game when you are ready.' : '')));
    if ((d.setups || []).some(x => x.status === 'testing')) GTIMER = setTimeout(() => { if (visible(el) && GS_ROLE === 'physics') gsPhysics(el); }, 4000);
  }

  // ---------------------------------------------------------------- v0.421 Game Desk roles: Audio + Haptics
  function checksTable(rows) {
    return `<table class="ph-tbl"><tbody>${(rows || []).map(c => `<tr><td>${esc(c.check)}<div class="muted em-small">${esc(c.note)}</div></td><td>${tag(c.ok ? 'ok' : 'bad', c.ok ? 'pass' : 'fail')}</td></tr>`).join('')}</tbody></table>`;
  }
  async function gsAudio(el) {
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', '/api/gamedesk/audio' + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    const zp = d.zone_presets || {};
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="auBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>Audio</h2>
        ${d.hired ? tag('ok', 'Spatial Audio Programmer hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">Reverb zones, distance and walls for your game, with headphone demos. Every number is measured: ear-to-ear timing for 13 directions, 6 dB per doubling of distance, each zone's echo time, demo loudness. A round-head model gives no front / back or height cue; in the game, Godot's own panning, distance and zones play it.</p>
      <div class="tile gl"><h3>New audio setup</h3><div class="acts">${Object.keys(zp).map(k => `<label class="gs-sw"><input type="checkbox" data-au-z="${esc(k)}"${['room', 'hall'].includes(k) ? ' checked' : ''}> ${esc(k.replace('_', ' '))} <span class="muted em-small">${num(zp[k])} s</span></label>`).join('')}</div>
        <div class="ph-grid"><label>Full volume up to (m)<input id="auMin" type="number" min="0.1" step="0.1" value="1"></label><label>Silent beyond (m)<input id="auMax" type="number" min="1" value="40"></label></div>
        <div class="acts"><button class="btn go" type="button" id="auGo"${d.hired ? '' : ' disabled'}>Render and measure</button>${sid ? '<button class="btn soft" type="button" id="auApply">Put approved audio in the game</button>' : ''}</div>
        ${d.hired ? '' : '<p class="muted em-small">Hire the Spatial Audio Systems Programmer in Employees first.</p>'}</div>
      ${(d.setups || []).map(x => { const [c, n] = WST[x.status] || ['', x.status]; const rp = x.report || {}, f = x.files || {}, nb = rp.numbers || {};
        return `<section class="tile gl"><div class="em-h"><h3>${esc(x.number)} <span class="muted">${esc(((x.plan || {}).zones || []).map(z => z.key + ' ' + z.rt60 + ' s').join(' · '))}</span></h3>${tag(c, n)}${rp.verdict ? tag(rp.verdict === 'PASS' ? 'ok' : 'bad', rp.verdict + ' ' + num(rp.passed) + '/' + num(rp.total)) : ''}</div>
          ${Object.keys(f).length ? `<div class="au-demos">${Object.entries(f).map(([k, u]) => `<div><b class="em-small">${esc(k.replace('.wav', ''))}</b><audio controls preload="none" src="${esc(u)}"></audio></div>`).join('')}</div><p class="muted em-small">Use headphones. Render ${num(nb.render_s)} s · ${num(nb.cpu_per_voice_s_per_s)} s CPU per voice per second · latency ${num(nb.latency_ms)} ms</p>` : (x.status === 'testing' ? '<p class="muted em-small">Rendering and measuring…</p>' : '')}
          ${checksTable(rp.checks)}${rp.limits ? `<p class="muted em-small">${esc(rp.limits)}</p>` : ''}${x.error ? `<div class="badc em-small">${esc(x.error)}</div>` : ''}
          <div class="acts">${x.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-au="approve" data-id="${esc(x.id)}">OK, use it</button><button class="btn soft gs-mini" type="button" data-au="reject" data-id="${esc(x.id)}">No</button>` : ''}</div></section>`; }).join('') || '<div class="empty">No audio setups yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsAudio(el); };
    el.querySelector('#auBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#auGo').addEventListener('click', e => {
      const zones = [...el.querySelectorAll('[data-au-z]:checked')].map(x => ({key: x.dataset.auZ, rt60: zp[x.dataset.auZ]}));
      if (!zones.length) { toast('Pick at least one place.', true); return; }
      e.target.disabled = true;
      go(() => api('POST', '/api/gamedesk/audio', {plan: {zones, min_d: Number(el.querySelector('#auMin').value), max_d: Number(el.querySelector('#auMax').value)}, studio: sid}), 'Rendering and measuring.');
    });
    el.querySelector('#auApply')?.addEventListener('click', () => go(() => api('POST', '/api/gamedesk/audio/apply', {studio: sid}), 'Rebuilding the game with the approved audio.'));
    el.querySelectorAll('[data-au]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/audio/${encodeURIComponent(b.dataset.id)}/${b.dataset.au}`), b.dataset.au === 'approve' ? 'Approved.' : '')));
    if ((d.setups || []).some(x => x.status === 'testing')) GTIMER = setTimeout(() => { if (visible(el) && GS_ROLE === 'audio') gsAudio(el); }, 3000);
  }

  async function gsHaptics(el) {
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', '/api/gamedesk/haptics' + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    const acts = d.actuators || {};
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="hpBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>Haptics</h2>
        ${d.hired ? tag('ok', 'Haptic Feedback Engineer hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">One vibration pattern per moment, checked for the motor (pulse length, gaps you can feel, no two that feel the same) with battery per play. Every player gets an off switch and intensity. The kit has iPhone Core Haptics files, Android code and a DRV2605 driver compiled here. iPhone browsers have no vibration.</p>
      <div class="tile gl"><h3>New pattern set</h3>
        <textarea id="hpWords" rows="2" maxlength="600" placeholder="The moments that should buzz, e.g. jump, coin, hit, game over, level up" aria-label="Moments"></textarea>
        <div class="acts"><select id="hpAct" aria-label="Device">${Object.entries(acts).map(([k, a]) => `<option value="${esc(k)}">${esc(a.name)}</option>`).join('')}</select>
          <button class="btn go" type="button" id="hpGo"${d.hired ? '' : ' disabled'}>Make and check</button>${sid ? '<button class="btn soft" type="button" id="hpApply">Put approved haptics in the game</button>' : ''}</div>
        ${d.hired ? '' : '<p class="muted em-small">Hire the Haptic Feedback Systems Engineer in Employees first.</p>'}</div>
      ${(d.sets || []).map(x => { const [c, n] = WST[x.status] || ['', x.status]; const rp = x.report || {}, f = x.files || {}, comp = ((rp.kit || {}).drv2605_compile || {});
        return `<section class="tile gl"><div class="em-h"><h3>${esc(x.number)} <span class="muted">${esc(x.actuator_name)} · ${esc(Object.keys(x.patterns || {}).join(', '))}</span></h3>${tag(c, n)}</div>
          ${f['patterns.png'] ? `<img class="wd-prev hp-img" src="${esc(f['patterns.png'])}" alt="Pattern shapes" loading="lazy">` : ''}
          ${checkList(rp)}
          <table class="ph-tbl"><thead><tr><th>Pattern</th><th>Length</th><th>Pulses</th><th>Energy / play</th><th>Per 1,000 plays</th></tr></thead><tbody>${Object.entries(rp.rows || {}).map(([k, r]) => `<tr><td>${esc(k)}</td><td>${num(r.ms)} ms</td><td>${num(r.pulses)}</td><td>${num(r.energy_mj)} mJ</td><td>${num(r.per_1000_plays_mwh)} mWh</td></tr>`).join('')}</tbody></table>
          <p class="muted em-small">${esc(rp.battery_note || '')} · DRV2605 driver: ${esc(comp.status || '')}${comp.compiler ? ' (' + esc(comp.compiler) + ')' : ''}</p>
          <div class="acts">${f['kit.zip'] ? `<a class="btn soft gs-mini" href="${esc(f['kit.zip'])}">Download the kit (ZIP)</a>` : ''}
            <button class="btn soft gs-mini" type="button" data-hp-try="${esc(x.id)}">Feel it on this phone</button>
            ${x.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-hp="approve" data-id="${esc(x.id)}">OK, use it</button><button class="btn soft gs-mini" type="button" data-hp="reject" data-id="${esc(x.id)}">No</button>` : ''}</div></section>`; }).join('') || '<div class="empty">No pattern sets yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsHaptics(el); };
    el.querySelector('#hpBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#hpGo').addEventListener('click', e => { e.target.disabled = true;
      go(() => api('POST', '/api/gamedesk/haptics', {words: el.querySelector('#hpWords').value.trim(), actuator: el.querySelector('#hpAct').value, studio: sid}), 'Made and checked.'); });
    el.querySelector('#hpApply')?.addEventListener('click', () => go(() => api('POST', '/api/gamedesk/haptics/apply', {studio: sid}), 'Rebuilding the game with the approved haptics.'));
    el.querySelectorAll('[data-hp]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/haptics/${encodeURIComponent(b.dataset.id)}/${b.dataset.hp}`), b.dataset.hp === 'approve' ? 'Approved.' : '')));
    el.querySelectorAll('[data-hp-try]').forEach(b => b.addEventListener('click', async () => {
      const x = (d.sets || []).find(s => s.id === b.dataset.hpTry); if (!x) return;
      if (!navigator.vibrate) { toast('This browser cannot vibrate (iPhone browsers and most computers cannot).', true); return; }
      for (const [name, ev] of Object.entries(x.patterns || {})) {   // each pattern in turn, 600 ms apart: off/on timings for navigator.vibrate
        const seq = []; let t = 0; ev.forEach(e => { seq.push(Math.max(0, e.t - t), e.d); t = e.t + e.d; }); seq.shift();
        toast(name); navigator.vibrate(seq); await new Promise(r => setTimeout(r, t + 600));
      }
    }));
  }

  // ---------------------------------------------------------------- v0.422 Game Desk roles: Multiplayer + VR / AR
  async function gsNet(el) {
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', '/api/gamedesk/net' + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    const df = d.defaults || {};
    const F = [['players', 'Players'], ['tick', 'Server ticks / s'], ['send', 'Snapshots / s'], ['speed', 'Player speed (px/s)'], ['size', 'Player size (px)'], ['interest', 'Sees players within (px)']];
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="ncBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>Multiplayer</h2>
        ${d.hired ? tag('ok', 'Network Programmer hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">Bots play your game's movement over a good network, the plan's 150 ms / 2 % loss network and a bad mobile one, through an authoritative server with prediction, reconciliation, interpolation and lag compensation. Measured: rubber-banding, desync (must be 0), bandwidth, hits the server agrees with. Then the Godot netcode itself runs with a server and three clients. The game server runs on your own cloud - Hoola hosts none - and the netcode is not inside the game build yet.</p>
      <div class="tile gl"><h3>New netcode setup</h3><div class="ph-grid">${F.map(([k, l]) => `<label>${l}<input data-nc="${k}" type="number" value="${num(df[k])}"></label>`).join('')}</div>
        <div class="acts"><button class="btn go" type="button" id="ncGo"${d.hired ? '' : ' disabled'}>Run the bots</button></div>
        ${d.hired ? '' : '<p class="muted em-small">Hire the Multiplayer Network Programmer in Employees first.</p>'}</div>
      ${(d.setups || []).map(x => { const [c, n] = WST[x.status] || ['', x.status]; const rp = x.report || {}, i = x.inputs || {}, runs = rp.runs || {};
        return `<section class="tile gl"><div class="em-h"><h3>${esc(x.number)} <span class="muted">${num(i.players)} players · ${num(i.tick)} Hz · ${num(i.send)} snapshots/s</span></h3>${tag(c, n)}${rp.verdict ? tag(rp.verdict === 'PASS' ? 'ok' : 'bad', rp.verdict + ' ' + num(rp.passed) + '/' + num(rp.total)) : ''}</div>
          ${Object.keys(runs).length ? `<table class="ph-tbl"><thead><tr><th>Network</th><th>Correction p95 / max</th><th>Desync</th><th>Down / up per player</th><th>Lag-comp hits</th></tr></thead><tbody>${Object.values(runs).map(r => `<tr><td>${esc(r.net)}</td><td>${num(r.corr_p95_px)} / ${num(r.corr_max_px)} px</td><td>${num(r.desync_px_max)} px</td><td>${num(r.down_bps_per_player)} / ${num(r.up_bps_per_player)} B/s</td><td>${Math.round((r.lagcomp_agree || 0) * 100)}% (without: ${Math.round((r.no_lagcomp_agree || 0) * 100)}%)</td></tr>`).join('')}</tbody></table>` : (x.status === 'testing' ? '<p class="muted em-small">Bots are playing…</p>' : '')}
          ${checksTable(rp.checks)}${x.error ? `<div class="badc em-small">${esc(x.error)}</div>` : ''}
          <div class="acts">${(x.files || {})['kit.zip'] ? `<a class="btn soft gs-mini" href="${esc(x.files['kit.zip'])}">Download the kit (server for your cloud + client)</a>` : ''}
            ${x.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-nc-do="approve" data-id="${esc(x.id)}">OK</button><button class="btn soft gs-mini" type="button" data-nc-do="reject" data-id="${esc(x.id)}">No</button>` : ''}</div></section>`; }).join('') || '<div class="empty">No netcode setups yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsNet(el); };
    el.querySelector('#ncBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#ncGo').addEventListener('click', e => { e.target.disabled = true;
      const inputs = {}; el.querySelectorAll('[data-nc]').forEach(x => { inputs[x.dataset.nc] = Number(x.value); });
      go(() => api('POST', '/api/gamedesk/net', {inputs, studio: sid}), 'The bots are playing.'); });
    el.querySelectorAll('[data-nc-do]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/net/${encodeURIComponent(b.dataset.id)}/${b.dataset.ncDo}`), b.dataset.ncDo === 'approve' ? 'Approved.' : '')));
    if ((d.setups || []).some(x => x.status === 'testing')) GTIMER = setTimeout(() => { if (visible(el) && GS_ROLE === 'net') gsNet(el); }, 4000);
  }

  async function gsXr(el) {
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', '/api/gamedesk/xr' + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="xrBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>VR / AR</h2>
        ${d.hired ? tag('ok', 'AR / VR Engineer hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">A WebXR setup that opens in a headset or phone browser: teleport, snap turning, a seated mode, readable panels - the comfort rules are checked in code. Hand gestures are scored on a test set of synthetic hands and checked in Godot itself. Frame rate on your headset is not measured here.</p>
      <div class="tile gl"><h3>New VR / AR setup</h3><div class="acts">
          <select id="xrMode" aria-label="Mode"><option value="vr">VR (headset)</option><option value="ar">AR (phone or headset camera view)</option></select>
          <select id="xrSnap" aria-label="Snap turn"><option value="30">Snap turn 30°</option><option value="45">Snap turn 45°</option></select>
          <select id="xrFps" aria-label="Device"><option value="72">Quest-class (72 fps)</option><option value="90">90 fps headset</option></select>
          <label class="gs-sw"><input type="checkbox" id="xrSeat" checked> Seated mode</label>
          <button class="btn go" type="button" id="xrGo"${d.hired ? '' : ' disabled'}>Check and build the demo room</button>${sid ? '<button class="btn soft" type="button" id="xrApply">Put approved VR / AR in the game</button>' : ''}</div>
        ${d.hired ? '' : '<p class="muted em-small">Hire the AR / VR Interaction Engineer in Employees first.</p>'}</div>
      ${(d.setups || []).map(x => { const [c, n] = WST[x.status] || ['', x.status]; const rp = x.report || {}, st = x.settings || {}, dm = x.demo || {}, gs = rp.gestures || {};
        return `<section class="tile gl"><div class="em-h"><h3>${esc(x.number)} <span class="muted">${esc((st.mode || '').toUpperCase())} · snap ${num(st.snap_deg)}° · ${num(st.fps)} fps</span></h3>${tag(c, n)}${rp.verdict ? tag(rp.verdict === 'PASS' ? 'ok' : 'bad', rp.verdict + ' ' + num(rp.passed) + '/' + num(rp.total)) : ''}</div>
          ${x.status === 'testing' ? '<p class="muted em-small">Checking and building…</p>' : ''}
          ${checkList(rp.comfort || {})}${checksTable(rp.checks)}
          ${gs.confusion ? `<table class="ph-tbl"><thead><tr><th>Shown → read as</th>${Object.keys(gs.confusion).map(g => `<th>${esc(g)}</th>`).join('')}</tr></thead><tbody>${Object.entries(gs.confusion).map(([g, row]) => `<tr><td>${esc(g)}</td>${Object.values(row).map(v => `<td>${num(v)}</td>`).join('')}</tr>`).join('')}</tbody></table>` : ''}
          <div class="acts">${dm.play_url ? `<a class="btn go gs-mini" href="${esc(dm.play_url)}" target="_blank" rel="noopener">Open the demo room</a><span class="muted em-small">On a headset or phone browser tap to enter XR</span>` : ''}
            ${x.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-xr-do="approve" data-id="${esc(x.id)}">OK, use it</button><button class="btn soft gs-mini" type="button" data-xr-do="reject" data-id="${esc(x.id)}">No</button>` : ''}</div>
          ${dm.status === 'failed' ? `<div class="badc em-small">Demo did not build: ${esc((dm.errors || []).join('; '))}</div>` : ''}</section>`; }).join('') || '<div class="empty">No VR / AR setups yet.</div>'}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsXr(el); };
    el.querySelector('#xrBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#xrGo').addEventListener('click', e => { e.target.disabled = true;
      go(() => api('POST', '/api/gamedesk/xr', {studio: sid, settings: {mode: el.querySelector('#xrMode').value, snap_deg: Number(el.querySelector('#xrSnap').value),
        fps: Number(el.querySelector('#xrFps').value), seated: el.querySelector('#xrSeat').checked}}), 'Checking and building the demo room.'); });
    el.querySelector('#xrApply')?.addEventListener('click', () => go(() => api('POST', '/api/gamedesk/xr/apply', {studio: sid}), 'Rebuilding the game with VR / AR.'));
    el.querySelectorAll('[data-xr-do]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/xr/${encodeURIComponent(b.dataset.id)}/${b.dataset.xrDo}`), b.dataset.xrDo === 'approve' ? 'Approved.' : '')));
    if ((d.setups || []).some(x => x.status === 'testing')) GTIMER = setTimeout(() => { if (visible(el) && GS_ROLE === 'xr') gsXr(el); }, 5000);
  }

  // ---------------------------------------------------------------- v0.423 Game Desk roles: Simulators, Digital Twin, VFX
  async function gsReportPage(el, cfg) {
    // one page shape for the three report-style roles: a form, then each setup's checks + numbers + files
    clearTimeout(GTIMER);
    const sid = GS_ROLE_SID, qs = sid ? `?studio=${encodeURIComponent(sid)}` : '';
    let d;
    try { d = await api('GET', `/api/gamedesk/${cfg.base}` + qs); }
    catch (e) { toast(e.message, true); GS_ROLE = ''; return game(el); }
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="rpBack">← ${sid ? 'Board' : 'Game Desk'}</button><h2>${esc(cfg.title)}</h2>
        ${d.hired ? tag('ok', cfg.who + ' hired') : tag('warn', 'Not hired yet')}</div>
      <p class="muted em-sub">${esc(cfg.intro)}</p>
      <div class="tile gl"><h3>${esc(cfg.formTitle)}</h3>${cfg.form(d)}
        <div class="acts"><button class="btn go" type="button" id="rpGo"${d.hired ? '' : ' disabled'}>${esc(cfg.go)}</button>
          ${sid && cfg.apply ? '<button class="btn soft" type="button" id="rpApply">Put the approved one in the game</button>' : ''}</div>
        ${d.hired ? '' : `<p class="muted em-small">Hire the ${esc(cfg.who)} in Employees first.</p>`}</div>
      ${(d.setups || []).map(x => { const [c, n] = WST[x.status] || ['', x.status]; const rp = x.report || {}, f = x.files || {};
        return `<section class="tile gl"><div class="em-h"><h3>${esc(x.number)} <span class="muted">${esc(cfg.sub(x))}</span></h3>${tag(c, n)}${rp.verdict ? tag(rp.verdict === 'PASS' ? 'ok' : 'bad', rp.verdict + ' ' + num(rp.passed) + '/' + num(rp.total)) : ''}</div>
          ${(rp.cases || []).length ? `<table class="ph-tbl"><thead><tr><th>Reference case</th><th>Measured</th><th>Expected</th><th></th></tr></thead><tbody>${rp.cases.map(k => `<tr><td>${esc(k.case)}<div class="muted em-small">${esc(k.note)}</div></td><td>${esc(String(k.measured))}</td><td>${esc(String(k.expected))}</td><td>${tag(k.ok ? 'ok' : 'bad', k.ok ? 'pass' : 'fail')}</td></tr>`).join('')}</tbody></table>` : ''}
          ${(rp.checks || []).length ? checksTable(rp.checks) : ''}
          ${cfg.extra ? cfg.extra(x) : ''}
          ${f['plot.png'] || f['layout.png'] ? `<img class="wd-prev hp-img" src="${esc(f['plot.png'] || f['layout.png'])}" alt="${esc(cfg.title)} picture" loading="lazy">` : ''}
          <div class="acts">${Object.entries(f).filter(([k]) => !k.endsWith('.png')).map(([k, u]) => `<a class="btn soft gs-mini" href="${esc(u)}">${esc(k)}</a>`).join('')}
            ${x.status === 'draft' ? `<button class="btn go gs-mini" type="button" data-rp="approve" data-id="${esc(x.id)}">OK</button><button class="btn soft gs-mini" type="button" data-rp="reject" data-id="${esc(x.id)}">No</button>` : ''}</div></section>`; }).join('') || '<div class="empty">Nothing yet.</div>'}`;
    const again = () => gsReportPage(el, cfg);
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } again(); };
    el.querySelector('#rpBack').addEventListener('click', () => roleBack(el));
    el.querySelector('#rpGo').addEventListener('click', e => { e.target.disabled = true; e.target.textContent = 'Checking…';
      go(() => api('POST', `/api/gamedesk/${cfg.base}`, {...cfg.body(el), studio: sid}), 'Checked.'); });
    el.querySelector('#rpApply')?.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/${cfg.base}/apply`, {studio: sid}), 'Rebuilding the game.'));
    el.querySelectorAll('[data-rp]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/gamedesk/${cfg.base}/${encodeURIComponent(b.dataset.id)}/${b.dataset.rp}`), b.dataset.rp === 'approve' ? 'Approved.' : '')));
  }

  function gsSim(el) {
    return gsReportPage(el, {base: 'sim', title: 'Simulators', who: 'Simulation Engineer', formTitle: 'New training model', go: 'Validate the model', apply: true,
      intro: 'Orbit, light-aircraft and car-handling models, each checked against its textbook answer, with the data source, time step and integrator stated and every scenario run twice. A training aid, not a certified device. Weapon or combat simulators are refused.',
      form: d => `<div class="acts"><select id="smKind" aria-label="Kind">${(d.kinds || []).map(k => `<option value="${esc(k)}">${esc(k)}</option>`).join('')}</select>
        <input id="smWords" maxlength="300" placeholder="Anything special (e.g. 800 km orbit at 98 degrees)" aria-label="Notes"></div>`,
      body: el2 => ({kind: el2.querySelector('#smKind').value, words: el2.querySelector('#smWords').value.trim()}),
      sub: x => `${x.kind} · ${(x.report || {}).integrator || ''}`,
      extra: x => (x.report || {}).source ? `<p class="muted em-small">Data: ${esc(x.report.source)}</p>` : ''});
  }

  function gsTwin(el) {
    return gsReportPage(el, {base: 'twin', title: 'Digital twin', who: 'Digital Twin Architect', formTitle: 'Check and simulate a twin', go: 'Run the twin', apply: false,
      intro: 'Your line as data, simulated: throughput, load per station, work in progress, lead time, the bottleneck and what-ifs. Every number must trace to your data tag or a stated assumption; the engine is checked against exact answers and queueing theory; it reads your data and never controls your plant. Without your real week it is NOT ASSESSED.',
      form: () => `<textarea id="twModel" rows="4" placeholder='Your model as JSON (leave empty for the worked example to copy)' aria-label="Model JSON"></textarea>
        <input id="twActual" maxlength="200" placeholder="Your real daily output, e.g. 540, 560, 548 (optional)" aria-label="Actual output">`,
      body: el2 => { let model = null; const t = el2.querySelector('#twModel').value.trim(); if (t) { try { model = JSON.parse(t); } catch { toast('The model is not valid JSON.', true); } }
        const actual = el2.querySelector('#twActual').value.split(/[,\s]+/).filter(Boolean).map(Number).filter(v => !isNaN(v)); return {model, actual}; },
      sub: x => `${(x.model.stations || []).length} stations · read-only`,
      extra: x => { const b = (x.report || {}).base, w = (x.report || {}).what_ifs || []; return b ? `<p class="em-small"><b>${num(b.per_day)} parts / day</b> · bottleneck ${esc(b.bottleneck)} · WIP ${num(b.wip_avg)} · lead time ${num(b.lead_time_min)} min</p>
        <table class="ph-tbl"><thead><tr><th>What if</th><th>Parts / day</th><th>Change</th><th>Bottleneck then</th></tr></thead><tbody>${w.map(r => `<tr><td>${esc(r.what_if)}</td><td>${num(r.per_day)}</td><td>${num(r.change_pct)}%</td><td>${esc(r.bottleneck)}</td></tr>`).join('')}</tbody></table>` : ''; }});
  }

  function gsVfx(el) {
    return gsReportPage(el, {base: 'vfx', title: 'VFX pipeline', who: 'VFX Pipeline TD', formTitle: 'Check a pipeline', go: 'Check the pipeline', apply: false,
      intro: 'Naming and versions, ACES colour from every source to your screen (converted and measured), a real ACEScg EXR test frame read back, a render queue with re-queued frames and cost per shot, and every frame traced to its scene. Blender and OpenColorIO are not installed on Hoola\'s server - the render script is for your machines.',
      form: () => `<textarea id="vxPlan" rows="4" placeholder='Your pipeline as JSON (leave empty for the worked example)' aria-label="Pipeline JSON"></textarea>`,
      body: el2 => { const t = el2.querySelector('#vxPlan').value.trim(); let plan = null; if (t) { try { plan = JSON.parse(t); } catch { toast('The pipeline is not valid JSON.', true); } } return {plan}; },
      sub: x => `${x.show} · ${((x.plan || {}).shots || []).length} shots`,
      extra: x => { const q = (x.report || {}).queue; return q ? `<p class="em-small">${num(q.frames)} frames · ${num(q.requeued)} re-queued · farm ${num(q.wall_hours)} h · ${esc(Object.entries(q.cost_inr || {}).map(([s, c]) => s + ' Rs ' + c).join(' · '))}</p>` : ''; }});
  }

  async function gsBoard(el, id) {
    clearTimeout(GTIMER);
    if (GS_BIBLE) return gsBible(el, id);
    if (GS_ASSETS) return gsAssets(el, id);
    if (GS_QA) return gsQa(el, id);
    if (GS_REL) return gsRelease(el, id);
    let p;
    try { p = await api('GET', `/api/gamestudio/${encodeURIComponent(id)}`); }
    catch (e) { GS_OPEN = ''; toast(e.message, true); return game(el); }
    const g = p.game || {}, n = p.night || {};
    const url = typeof g.play_url === 'string' && /^(https:\/\/|http:\/\/127\.0\.0\.1|\/play\/)/.test(g.play_url) ? g.play_url : '';
    const cols = GS_COLS.map(([k, label]) => {
      const ts = (p.tasks || []).filter(t => t.status === k);
      const show = k === 'done' ? ts.slice(-12).reverse() : ts;
      return `<div class="gs-col gs-c-${k}"><h4>${label} <span class="muted">${num(ts.length)}</span></h4>${show.map(t => gsTask(t, p)).join('') || '<p class="muted em-small">Nothing here.</p>'}</div>`;
    }).join('');
    el.innerHTML = `<div class="vh"><button class="btn soft" type="button" id="gsBack">← Game Desk</button><h2>${esc(p.number)} · ${esc(p.title)}</h2>
        ${url ? `<a class="btn go" href="${esc(url)}" target="_blank" rel="noopener">Play v${num(g.version)}</a>` : ''}
        <button class="btn soft" type="button" id="gsBib">Game Bible${(p.bible || {}).version ? ' v' + num(p.bible.version) : ''}${(p.bible || {}).errors ? ' · ' + num(p.bible.errors) + ' to fix' : ''}${(p.bible || {}).draft ? ' · draft waiting' : ''}</button>
        <button class="btn soft" type="button" id="gsRelBtn">Release</button>
        <button class="btn soft" type="button" id="gsWorldBtn">Worlds</button>
        <button class="btn soft" type="button" id="gsPhysBtn">Physics</button>
        <button class="btn soft" type="button" id="gsAudBtn">Audio</button>
        <button class="btn soft" type="button" id="gsHapBtn">Haptics</button>
        <button class="btn soft" type="button" id="gsNetBtn">Multiplayer</button>
        <button class="btn soft" type="button" id="gsXrBtn">VR / AR</button>
        <button class="btn soft" type="button" id="gsSimBtn">Simulator</button>
        <button class="btn soft" type="button" id="gsQaBtn">QA${(p.qa || {}).verdict ? ' · ' + esc(p.qa.verdict) : ''}${(p.qa || {}).open ? ' · ' + num(p.qa.open) + ' bug' + (p.qa.open === 1 ? '' : 's') : ''}</button>
        <button class="btn soft" type="button" id="gsAst">Assets${(p.assets || {}).count ? ' · ' + num(p.assets.in_game) + ' in game' : ''}${(p.assets || {}).waiting_ok ? ' · ' + num(p.assets.waiting_ok) + ' for your OK' : ''}${(p.assets || {}).priced ? ' · ₹' + num(p.assets.priced) + ' card' : ''}</button></div>
      <p class="muted em-sub">${esc(p.goal || '')}</p>
      ${gsBars(p.milestones, p.gates || [])}
      ${(p.gates || [])[0] ? (() => { const gt = p.gates[0]; return `<div class="tile gl gs-gatecard"><b>Gate check · ${esc(gt.name)}: ${esc(gt.verdict)}</b>
        ${[...gt.blockers.map(x => ['bad', x]), ...gt.concerns.map(x => ['warn', x]), ...gt.missing.map(x => ['', x])].map(([c, x]) => `<div class="em-small">${tag(c, c === 'bad' ? 'Blocker' : c === 'warn' ? 'Concern' : 'Missing')} ${esc(x)}</div>`).join('')}
        ${Object.entries(gt.views || {}).map(([k, v]) => `<p class="em-small"><b>${esc(k.replace(/_/g, ' '))}:</b> ${esc(v)}</p>`).join('')}
        <p class="muted em-small">${esc(gt.note)}</p></div>`; })() : ''}
      <details class="tile gl gs-crewbox" id="gsCrewBox"${GS_CREW_OPEN ? ' open' : ''}><summary>Crew: ${num((p.crew || {}).count || 49)} studio roles · ${num(((p.crew || {}).busy || []).length)} on open tasks</summary>
        <div class="acts gs-team"><select id="gsTeam" aria-label="Team">${((p.crew || {}).teams || []).map(t => `<option value="${esc(t.key)}">${esc(t.name)}</option>`).join('')}</select>
          <input id="gsTeamW" maxlength="400" placeholder="What the team should make, e.g. a boss fight on the rooftops" aria-label="Team brief">
          <button class="btn soft" type="button" id="gsTeamGo">Let the team plan it</button></div>
        <div id="gsCrewList">${gsCrew(p)}</div></details>
      <div class="tile gl gs-add"><input id="gsT" maxlength="200" placeholder="New task, one small change: e.g. add a nitro boost (double tap)" aria-label="New task">
        <select id="gsM" aria-label="Milestone">${(p.milestones || []).map(m => `<option value="${esc(m.key)}"${m.key === p.milestone ? ' selected' : ''}>${esc(m.name)}</option>`).join('')}</select>
        <select id="gsR" aria-label="Role"><option value="">Role: picked from the words</option>${(GS_CREW ? GS_CREW.tiers.flatMap(t => t.roles) : []).map(r => `<option value="${esc(r.key)}">${esc(r.name)}${r.mode === 'writes' ? ' (writes)' : ''}</option>`).join('')}</select>
        <select id="gsP" aria-label="Priority"><option value="2">Normal</option><option value="1">High</option><option value="3">Low</option></select>
        <button class="btn go" type="button" id="gsAdd">Add task</button>
        <button class="btn soft" type="button" id="gsPlan">Let Hoola plan the next tasks</button></div>
      <div class="gs-board" id="gsBoard">${cols}</div>
      <div class="gs-grid">
        <section class="tile gl"><h3>Decisions</h3>
          <div class="acts"><input id="gsD" maxlength="600" placeholder="A decision, e.g. no guns: it is for kids" aria-label="Decision"><button class="btn soft" type="button" id="gsDec">Save</button></div>
          <div class="acts"><input id="gsQ" maxlength="300" placeholder="Ask why, e.g. why is the jump so high?" aria-label="Ask why"><button class="btn soft" type="button" id="gsWhy">Find</button></div>
          <div id="gsWhyOut"></div>
          <ul class="gs-log">${(p.decisions || []).slice(0, 30).map(d => `<li><span class="muted">${esc((d.at || '').slice(0, 10))}</span> ${esc(d.text)}${d.why ? ` <span class="muted">- ${esc(d.why)}</span>` : ''}</li>`).join('')}</ul></section>
        <section class="tile gl"><h3>Nightly build</h3>
          <p class="em-small">${n.at ? `${n.ok ? tag('ok', 'Passed') : tag('bad', 'Failed')} ${esc((n.at || '').slice(0, 16).replace('T', ' '))} · v${num(n.version)}${n.fps ? ' · ' + num(n.fps) + ' fps' : ''}${n.load_s ? ' · ' + num(n.load_s) + ' s to start' : ''}` : 'No nightly build yet.'}</p>
          ${n.errors && n.errors.length && !n.ok ? `<p class="badc em-small">${esc(n.errors.slice(0, 2).join('; '))}</p>` : ''}
          ${n.suspects && n.suspects.length ? `<p class="em-small">Probably from: ${esc(n.suspects.join(', '))}</p>` : ''}
          <div class="acts"><button class="btn soft" type="button" id="gsNight">Run it now</button><button class="btn soft" type="button" id="gsSum">Morning report now</button></div>
          <pre class="gs-sum" id="gsSumOut" hidden></pre>
          <h3>Settings</h3>
          <label class="gs-sw"><input type="checkbox" id="gsAuto"${p.auto ? ' checked' : ''}> After my OK, start the next task by itself</label>
          <label class="gs-sw"><input type="checkbox" id="gsNo"${p.nightly_on ? ' checked' : ''}> Build and play it every night</label>
          <label class="gs-sw"><input type="checkbox" id="gsSo"${p.summary_on ? ' checked' : ''}> Morning report at <input type="number" id="gsH" min="5" max="12" value="${num(p.summary_hour)}" aria-label="Report hour"> am</label>
          <div class="acts"><button class="btn soft" type="button" id="gsGh">Save code to my GitHub</button>
            <button class="btn soft" type="button" id="gsPause">${p.status === 'paused' ? 'Resume project' : 'Pause project'}</button>
            <button class="btn soft em-leave" type="button" id="gsArch">Archive</button></div></section>
        <section class="tile gl"><h3>Versions</h3><ul class="gs-log">${(p.versions || []).map(v => `<li>${v.live ? tag('ok', 'Live') : v.rejected ? tag('', 'Sent back') : v.ok ? '' : tag('bad', 'Failed')}
          <b>v${num(v.n)}</b> ${esc(v.task ? v.task + ' ' + v.task_title : (v.words || 'first build'))} <span class="muted">${esc((v.at || '').slice(0, 10))}</span>
          ${v.ok && !v.live ? `<button class="btn soft gs-mini" type="button" data-gsv="${num(v.n)}">Bring back</button>` : ''}</li>`).join('')}</ul></section>
      </div>`;
    const q = encodeURIComponent(p.id);
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } gsBoard(el, id); };
    el.querySelector('#gsBack').addEventListener('click', () => { GS_OPEN = ''; GS_BIBLE = false; GS_ASSETS = false; GS_QA = false; GS_REL = false; GS_ROLE = ''; el.innerHTML = ''; game(el); });
    el.querySelector('#gsBib').addEventListener('click', () => { GS_BIBLE = true; gsBible(el, id); });
    el.querySelector('#gsAst').addEventListener('click', () => { GS_ASSETS = true; gsAssets(el, id); });
    el.querySelector('#gsQaBtn').addEventListener('click', () => { GS_QA = true; gsQa(el, id); });
    el.querySelector('#gsRelBtn').addEventListener('click', () => { GS_REL = true; gsRelease(el, id); });
    el.querySelector('#gsWorldBtn').addEventListener('click', () => { GS_ROLE = 'world'; GS_ROLE_SID = id; gsWorld(el); });
    el.querySelector('#gsPhysBtn').addEventListener('click', () => { GS_ROLE = 'physics'; GS_ROLE_SID = id; gsPhysics(el); });
    el.querySelector('#gsAudBtn').addEventListener('click', () => { GS_ROLE = 'audio'; GS_ROLE_SID = id; gsAudio(el); });
    el.querySelector('#gsHapBtn').addEventListener('click', () => { GS_ROLE = 'haptics'; GS_ROLE_SID = id; gsHaptics(el); });
    el.querySelector('#gsNetBtn').addEventListener('click', () => { GS_ROLE = 'net'; GS_ROLE_SID = id; gsNet(el); });
    el.querySelector('#gsXrBtn').addEventListener('click', () => { GS_ROLE = 'xr'; GS_ROLE_SID = id; gsXr(el); });
    el.querySelector('#gsSimBtn').addEventListener('click', () => { GS_ROLE = 'sim'; GS_ROLE_SID = id; gsSim(el); });
    el.querySelector('#gsAdd').addEventListener('click', () => {
      const title = el.querySelector('#gsT').value.trim();
      if (title.length < 3) { toast('Write the task in one line.', true); return; }
      go(() => api('POST', `/api/gamestudio/${q}/tasks`, {title, milestone: el.querySelector('#gsM').value, priority: el.querySelector('#gsP').value, role: el.querySelector('#gsR').value}), 'Added to To do.');
    });
    if (!GS_CREW) api('GET', '/api/gamestudio/crew').then(c => { GS_CREW = c; const box = el.querySelector('#gsCrewList'); if (box) box.innerHTML = gsCrew(p);
      const sel = el.querySelector('#gsR'); if (sel) sel.insertAdjacentHTML('beforeend', c.tiers.flatMap(t => t.roles).map(r => `<option value="${esc(r.key)}">${esc(r.name)}${r.mode === 'writes' ? ' (writes)' : ''}</option>`).join('')); }).catch(() => {});
    el.querySelector('#gsCrewBox').addEventListener('toggle', e => { GS_CREW_OPEN = e.target.open; });
    el.querySelector('#gsTeamGo').addEventListener('click', e => { e.target.disabled = true; e.target.textContent = 'The team is planning…';
      go(() => api('POST', `/api/gamestudio/${q}/plan`, {team: el.querySelector('#gsTeam').value, words: el.querySelector('#gsTeamW').value.trim()}), 'The team added its tasks to To do.'); });
    el.querySelectorAll('[data-gs-gate]').forEach(b => b.addEventListener('click', () => { b.disabled = true; b.textContent = 'Checking…';
      go(() => api('POST', `/api/gamestudio/${q}/gate`, {milestone: b.dataset.gsGate})); }));
    el.querySelector('#gsPlan').addEventListener('click', e => { e.target.disabled = true; e.target.textContent = 'Planning…';
      go(() => api('POST', `/api/gamestudio/${q}/plan`, {words: el.querySelector('#gsT').value.trim()}), 'Hoola added the next tasks to To do. Drop any you do not want.'); });
    el.querySelectorAll('[data-gst]').forEach(b => b.addEventListener('click', () => {
      const a = b.dataset.gst, t = encodeURIComponent(b.dataset.id);
      if (a === 'start') return go(() => api('POST', `/api/gamestudio/${q}/start`, {task: b.dataset.id}), 'Started. It will wait for your OK.');
      if (a === 'review') { b.disabled = true; b.textContent = 'Reviewing…'; return go(() => api('POST', `/api/gamestudio/${q}/task/${t}`, {action: 'review'}), 'The lead has reviewed it.'); }
      let note = '';
      if (a === 'back') { note = prompt('What was wrong? (Hoola tries again with this)') ?? null; if (note === null) return; }
      if (a === 'ok') { note = prompt('Anything to remember about this? (optional, saved as a decision)') || ''; }
      if (a === 'drop' && !confirm('Drop this task?')) return;
      go(() => api('POST', `/api/gamestudio/${q}/task/${t}`, {action: a, note}));
    }));
    el.querySelector('#gsDec').addEventListener('click', () => { const text = el.querySelector('#gsD').value.trim(); if (text) go(() => api('POST', `/api/gamestudio/${q}/decide`, {text}), 'Saved.'); });
    el.querySelector('#gsWhy').addEventListener('click', async () => {
      const qq = el.querySelector('#gsQ').value.trim(); if (!qq) return;
      try { const r = await api('GET', `/api/gamestudio/${q}/why?q=${encodeURIComponent(qq)}`);
        el.querySelector('#gsWhyOut').innerHTML = r.found.length ? `<ul class="gs-log">${r.found.map(f => `<li><b>${esc(f.text)}</b>${f.why ? ' - ' + esc(f.why) : ''} <span class="muted">${esc((f.at || '').slice(0, 10))}</span></li>`).join('')}</ul>`
          : '<p class="muted em-small">Nothing in the log about this.</p>'; } catch (e) { toast(e.message, true); }
    });
    el.querySelector('#gsNight').addEventListener('click', e => { e.target.disabled = true; e.target.textContent = 'Building…'; go(() => api('POST', `/api/gamestudio/${q}/nightly`)); });
    el.querySelector('#gsSum').addEventListener('click', async () => {
      try { const r = await api('GET', `/api/gamestudio/${q}/summary`); const o = el.querySelector('#gsSumOut'); o.textContent = r.text; o.hidden = false; } catch (e) { toast(e.message, true); }
    });
    const save = () => go(() => api('POST', `/api/gamestudio/${q}/settings`, {auto: el.querySelector('#gsAuto').checked, nightly_on: el.querySelector('#gsNo').checked,
      summary_on: el.querySelector('#gsSo').checked, summary_hour: Number(el.querySelector('#gsH').value) || 9}), 'Saved.');
    ['#gsAuto', '#gsNo', '#gsSo', '#gsH'].forEach(s => el.querySelector(s).addEventListener('change', save));
    el.querySelector('#gsPause').addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/settings`, {status: p.status === 'paused' ? 'active' : 'paused'})));
    el.querySelector('#gsArch').addEventListener('click', () => { if (!confirm('Archive this project? The game stays on the desk.')) return;
      go(async () => { await api('POST', `/api/gamestudio/${q}/settings`, {status: 'archived'}); GS_OPEN = ''; }); });
    el.querySelector('#gsGh').addEventListener('click', () => go(() => api('POST', `/api/gamestudio/${q}/github`, {private: true}), 'The GitHub card is in your chat; your tap sends it.'));
    el.querySelectorAll('[data-gsv]').forEach(b => b.addEventListener('click', () => {
      if (confirm(`Bring back version ${b.dataset.gsv}? It is built and played again as a new version.`)) go(() => api('POST', `/api/gamestudio/${q}/restore`, {n: Number(b.dataset.gsv)}), 'Bringing it back…');
    }));
    if ((p.counts || {}).working || BUSYG.includes(g.status)) GTIMER = setTimeout(() => { if (visible(el) && GS_OPEN === id) gsBoard(el, id); }, 5000);
  }

  function gcard(g) {
    const [c, n] = GST[g.status] || ['', g.status];
    const busy = BUSYG.includes(g.status);
    const nums = g.numbers || {};
    const url = typeof g.play_url === 'string' && /^(https:\/\/|http:\/\/127\.0\.0\.1|\/play\/)/.test(g.play_url) ? g.play_url : '';
    return `<article class="tile gl gd-card"><div class="em-h"><h3>${esc(g.number || '')} · ${esc(g.title || 'Game')}</h3>${tag(c, n)}</div>
      ${busy ? `<div class="pbar"><i style="width:${Math.max(4, Math.min(100, g.pct || 0))}%"></i></div><p class="muted em-small">${esc(g.stage || '')}</p>` : ''}
      ${g.error ? `<p class="badc em-small">${esc(g.error)}</p>` : ''}
      ${g.status === 'design_ready' ? `<details class="gd-design" open><summary>Design doc</summary><div class="gd-doc">${esc(g.design || '')}</div></details>
        <textarea rows="2" maxlength="1500" data-fb="${esc(g.id)}" placeholder="Want changes? Write them here, or just build it" aria-label="Design changes"></textarea>
        <div class="acts"><button class="btn go" type="button" data-gd="build" data-id="${esc(g.id)}">Build it</button>
          <button class="btn soft" type="button" data-gd="redesign" data-id="${esc(g.id)}">Change the design</button></div>` : ''}
      ${url ? `<div class="gd-play"><iframe title="${esc(g.title || 'Game')}" src="${esc(url)}" sandbox="allow-scripts allow-pointer-lock" loading="lazy" class="gd-frame gd-${esc(g.orientation || 'portrait')}"></iframe>
        <div class="gd-side"><a class="btn go" href="${esc(url)}" target="_blank" rel="noopener">Open full screen</a>
          <img data-qr="${esc(url)}" alt="QR code to play on your phone" class="gd-qr"><p class="muted em-small">Scan to play on your phone. Private: only people with this link can play.</p>
          <div class="gd-nums">${nums.fps_server ? `<span><b>${num(nums.fps_server)}</b> fps on the server</span>` : ''}${nums.load_s ? `<span><b>${num(nums.load_s)}</b> s to start</span>` : ''}${nums.download_mb ? `<span><b>${num(nums.download_mb)}</b> MB download</span>` : ''}</div>
          ${g.notes ? `<p class="em-small">${esc(g.notes)}</p>` : ''}</div></div>
        ${(g.shots || []).length ? `<div class="gd-shots">${g.shots.map(s => `<img src="${esc(s)}" alt="Screenshot from Hoola's playtest" loading="lazy">`).join('')}</div>` : ''}
        <textarea rows="2" maxlength="1500" data-ch="${esc(g.id)}" placeholder="What should change? e.g. make it faster, add a shield power-up" aria-label="Change the game"></textarea>
        <div class="acts"><button class="btn go" type="button" data-gd="change" data-id="${esc(g.id)}">Make a new version</button>
          <button class="btn soft" type="button" data-gd="source" data-id="${esc(g.id)}">Download Godot project</button>
          <button class="btn soft em-leave" type="button" data-gd="delete" data-id="${esc(g.id)}">Delete</button></div>` : ''}
      ${busy ? `<div class="acts"><button class="btn soft" type="button" data-gd="cancel" data-id="${esc(g.id)}">Stop</button></div>` : ''}
      ${!url && !busy && g.status !== 'design_ready' ? `<div class="acts"><button class="btn soft em-leave" type="button" data-gd="delete" data-id="${esc(g.id)}">Delete</button></div>` : ''}</article>`;
  }

  async function gact(el, what, id, btn) {
    const q = encodeURIComponent(id);
    try {
      if (what === 'build') { btn.disabled = true; await api('POST', `/api/game/${q}/approve`, {}); toast('Building. Hoola plays it before it reaches you.'); }
      if (what === 'redesign') {
        const fb = el.querySelector(`[data-fb="${CSS.escape(id)}"]`)?.value.trim();
        if (!fb) { toast('Write what should change in the design.', true); return; }
        await api('POST', `/api/game/${q}/approve`, {feedback: fb}); toast('Rewriting the design…');
      }
      if (what === 'change') {
        const w = el.querySelector(`[data-ch="${CSS.escape(id)}"]`)?.value.trim();
        if (!w) { toast('Write what should change first.', true); return; }
        await api('POST', `/api/game/${q}/change`, {words: w}); toast('Making a new version. The current one keeps working.');
      }
      if (what === 'cancel') await api('POST', `/api/game/${q}/cancel`, {});
      if (what === 'delete') { if (!confirm('Delete this game and its play link?')) return; await api('DELETE', `/api/game/${q}`); }
      if (what === 'source') {
        const r = await api('GET', `/api/game/${q}/source`, undefined, {raw: true});
        const blob = await r.blob(); const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = (r.headers.get('content-disposition') || '').split('filename=')[1]?.replace(/"/g, '') || 'game.zip';
        document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
        return;
      }
    } catch (e) { toast(e.message, true); }
    game(el);
  }

  // ------------------------------------------------------------ v0.410 the Architecture Desk (Principal Software Architect)
  let ATIMER = null, AOPEN = '';
  const AST = {reading: ['v', 'Reading the repo'], designing: ['v', 'Writing the design'], drawing: ['v', 'Drawing diagrams'],
               waiting_her: ['warn', 'Waiting for your OK'], approved: ['ok', 'Approved'], failed: ['bad', 'Did not work'],
               cancelled: ['', 'Stopped']};
  const ABUSY = ['reading', 'designing', 'drawing'];
  const VERD = {fits: ['ok', 'Fits the design'], drifts: ['warn', 'Drifts from the design'], breaks: ['bad', 'Breaks the design']};
  async function arch(el) {
    clearTimeout(ATIMER);
    if (AOPEN) return archOne(el, AOPEN);
    let d;
    try { d = await api('GET', '/api/arch/projects'); }
    catch (e) { el.innerHTML = `<div class="vh"><h2>Architecture Desk</h2></div><p class="badc">${esc(e.message)}</p>`; return; }
    const ps = d.projects || [];
    el.innerHTML = `<div class="vh"><h2>Architecture Desk</h2><span class="muted em-sub">Your Principal Software Architect. Describe the system (and your GitHub repo, if there is one): you get decisions, diagrams, capacity in numbers, risks and a PDF - then your pull requests are checked against it.</span></div>
      <article class="tile gl cad-new"><textarea id="arBrief" rows="4" maxlength="6000" placeholder="What the system must do, who uses it, how many people a day, anything it must work with. e.g. A food-delivery backend for 3 cities: customers order in the app, restaurants accept, riders deliver with live tracking. 50,000 orders a day at launch, UPI payments, Hindi + English."></textarea>
      <div class="cad-in"><label>GitHub repo to read first (optional) <input id="arRepo" placeholder="owner/name"></label>
      <label>Users a day <input id="arDau" inputmode="numeric" placeholder="e.g. 200000"></label>
      <label>Requests per user a day <input id="arReq" inputmode="numeric" placeholder="e.g. 30"></label></div>
      <div class="acts"><button class="btn go" type="button" id="arGo">Design it</button>${d.health && !d.health.diagrams ? '<span class="muted">Diagram drawing is not set up on this server - designs come without pictures.</span>' : ''}</div></article>
      ${ps.length ? ps.map(p => { const st = AST[p.status] || ['', p.status];
        return `<article class="tile gl cad-card"><div class="em-h"><h3>${esc(p.title)}${p.version ? ` <small class="muted">v${esc(String(p.version))}</small>` : ''}</h3>${tag(st[0], ABUSY.includes(p.status) ? p.stage || st[1] : st[1])}</div>
          <p class="muted">${p.repo ? 'Repo ' + esc(p.repo) : 'New system'} · ${esc(when(p.created_at))}</p>${p.error ? `<p class="badc">${esc(p.error)}</p>` : ''}
          <div class="acts"><button class="btn soft" type="button" data-aropen="${esc(p.id)}">Open</button>${p.pdf ? `<a class="btn soft" href="${esc(p.pdf)}" target="_blank" rel="noopener">PDF</a>` : ''}</div></article>`; }).join('') : '<div class="empty">No designs yet.</div>'}`;
    el.querySelector('#arGo').addEventListener('click', async ev => {
      const brief = el.querySelector('#arBrief').value.trim();
      if (!brief) return;
      const scale = {};
      const dau = el.querySelector('#arDau').value.replace(/[, ]/g, ''), req = el.querySelector('#arReq').value.replace(/[, ]/g, '');
      if (dau) scale.dau = Number(dau);
      if (req) scale.requests_per_user_per_day = Number(req);
      ev.target.disabled = true;
      try { const p = await api('POST', '/api/arch/projects', {brief, repo: el.querySelector('#arRepo').value.trim(), scale}); AOPEN = p.id; toast('Designing. A design takes a few minutes.'); }
      catch (e) { toast(e.message, true); }
      arch(el);
    });
    el.querySelectorAll('[data-aropen]').forEach(b => b.addEventListener('click', () => { AOPEN = b.dataset.aropen; arch(el); }));
    if (ps.some(p => ABUSY.includes(p.status))) ATIMER = setTimeout(() => { if (visible(el)) arch(el); }, 5000);
  }
  async function archOne(el, pid) {
    let p;
    try { p = await api('GET', `/api/arch/projects/${encodeURIComponent(pid)}`); }
    catch (e) { AOPEN = ''; toast(e.message, true); return arch(el); }
    const st = AST[p.status] || ['', p.status], busy = ABUSY.includes(p.status), d = p.design || {}, cap = p.capacity || {};
    const md = s => window.HoolaMD ? window.HoolaMD.render(String(s || '')) : `<p>${esc(s)}</p>`;
    const rows = (head, xs) => `<table class="cad-bom"><thead><tr>${head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${xs.map(r => `<tr>${r.map(c => `<td>${esc(c ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    const pics = (p.diagrams || []).map(g => `<figure class="ar-dia"><figcaption>${esc(g.name)}</figcaption>${g.ok && (g.svg || g.png)
      ? `<a href="${esc(g.svg || g.png)}" target="_blank" rel="noopener"><img src="${esc(g.png || g.svg)}" alt="${esc(g.name)}" loading="lazy"></a>`
      : `<p class="badc">Could not be drawn: ${esc(g.error || '')}</p><pre>${esc(g.mermaid || '')}</pre>`}</figure>`).join('');
    const capHtml = cap.rows ? rows(['Result', 'Value', 'How'], cap.rows.map(r => [r.what, r.value, r.formula]))
      + (cap.assumed && cap.assumed.length ? `<p class="muted">Assumed, please confirm: ${esc(cap.assumed.join(', '))}</p>` : '')
      : `<p class="muted">${esc(cap.error || '–')}</p>`;
    const adrs = (d.adrs || []).map(a => `<details><summary><b>${esc(a.id)}</b> ${esc(a.title)}</summary><p><b>Decision:</b> ${esc(a.decision)}</p><p class="muted"><b>Context:</b> ${esc(a.context)}</p>${(a.alternatives || []).length ? `<p class="muted"><b>Not chosen:</b> ${esc(a.alternatives.join(' · '))}</p>` : ''}<p class="muted"><b>Consequences:</b> ${esc(a.consequences)}</p></details>`).join('');
    const risks = (d.risks || []).length ? rows(['Risk', 'Likelihood', 'Impact', 'Mitigation'], d.risks.map(r => [r.risk, r.likelihood, r.impact, r.mitigation])) : '';
    const revs = (p.reviews || []).map(r => { const v = VERD[r.verdict] || ['', r.verdict];
      return `<article class="tile gl"><div class="em-h"><h4>PR #${esc(String(r.pr))} ${esc(r.title)}</h4>${tag(v[0], v[1])} ${tag('', r.status)}</div>${md(r.summary)}
        ${(r.findings || []).map(f => `<p><b>${esc(f.severity)}</b> · ${esc(f.area)}${f.adr ? ' (' + esc(f.adr) + ')' : ''}: ${esc(f.finding)}<br><span class="muted">→ ${esc(f.fix)}</span></p>`).join('')}
        ${r.status === 'draft' ? `<div class="acts"><button class="btn go" type="button" data-arpost="${esc(r.id)}">Post on PR</button><button class="btn soft" type="button" data-ardisc="${esc(r.id)}">Discard</button></div>` : ''}</article>`; }).join('');
    el.innerHTML = `<div class="vh"><h2>${esc(p.title)}${p.version ? ` <small class="muted">v${esc(String(p.version))}</small>` : ''}</h2>${tag(st[0], busy ? p.stage || st[1] : st[1])}</div>
      <div class="acts"><button class="btn soft" type="button" id="arBack">← All designs</button>${p.pdf ? `<a class="btn soft" href="${esc(p.pdf)}" target="_blank" rel="noopener">Download PDF</a>` : ''}
        ${p.status === 'waiting_her' ? `<button class="btn go" type="button" id="arOk">Approve design</button>` : ''}
        ${busy ? '<button class="btn soft" type="button" id="arStop">Stop</button>' : '<button class="btn soft em-leave" type="button" id="arDel">Delete</button>'}</div>
      ${p.error ? `<p class="badc">${esc(p.error)}</p>` : ''}
      ${busy ? '<div class="empty">Working on it - this page refreshes by itself.</div>' : ''}
      ${d.summary ? `<article class="tile gl">${md(d.summary)}</article>` : ''}
      ${pics ? `<h3 class="em-group">Diagrams</h3><div class="ar-dias">${pics}</div>` : ''}
      ${d.title ? `<h3 class="em-group">Capacity (worked out in code)</h3><article class="tile gl">${capHtml}</article>` : ''}
      ${(d.components || []).length ? `<h3 class="em-group">Components</h3><article class="tile gl">${rows(['Component', 'Kind', 'Does', 'Tech'], d.components.map(c => [c.name, c.kind, c.responsibility, c.tech]))}</article>` : ''}
      ${adrs ? `<h3 class="em-group">Decisions (ADRs)</h3><article class="tile gl">${adrs}</article>` : ''}
      ${risks ? `<h3 class="em-group">Risks</h3><article class="tile gl">${risks}</article>` : ''}
      ${(d.open_questions || []).length ? `<h3 class="em-group">Open questions</h3><article class="tile gl"><ul>${d.open_questions.map(q => `<li>${esc(q)}</li>`).join('')}</ul></article>` : ''}
      ${p.markdown ? `<details class="tile gl"><summary>Full design document</summary>${md(p.markdown)}</details>` : ''}
      ${!busy && p.version ? `<div class="cad-change"><input id="arWords" maxlength="2000" placeholder="Change it, e.g. use Postgres not MongoDB; add an admin panel; plan for 10x users"><button class="btn soft" type="button" id="arCh">Make next version</button></div>` : ''}
      ${p.status === 'approved' && p.repo ? `<h3 class="em-group">Pull requests against this design</h3><article class="tile gl"><label class="em-row"><input type="checkbox" id="arWatch" ${p.watch_prs ? 'checked' : ''}> Read new pull requests on its own (draft notes only)</label>
        <div class="cad-change"><input id="arPr" inputmode="numeric" placeholder="PR number"><button class="btn soft" type="button" id="arRev">Check this PR</button></div></article>${revs}` : revs}`;
    const go = async (fn, ok) => { try { await fn(); if (ok) toast(ok); } catch (e) { toast(e.message, true); } archOne(el, pid); };
    el.querySelector('#arBack').addEventListener('click', () => { AOPEN = ''; arch(el); });
    el.querySelector('#arOk')?.addEventListener('click', () => go(() => api('POST', `/api/arch/projects/${encodeURIComponent(pid)}/approve`, {}), 'Approved.'));
    el.querySelector('#arStop')?.addEventListener('click', () => go(() => api('POST', `/api/arch/projects/${encodeURIComponent(pid)}/cancel`), 'Stopped.'));
    el.querySelector('#arDel')?.addEventListener('click', async () => { if (!confirm('Delete this design, its versions and its PR notes?')) return;
      try { await api('DELETE', `/api/arch/projects/${encodeURIComponent(pid)}`); AOPEN = ''; } catch (e) { toast(e.message, true); } arch(el); });
    el.querySelector('#arCh')?.addEventListener('click', () => { const w = el.querySelector('#arWords').value.trim(); if (w) go(() => api('POST', `/api/arch/projects/${encodeURIComponent(pid)}/change`, {words: w}), 'Making the next version.'); });
    el.querySelector('#arWatch')?.addEventListener('change', ev => go(() => api('PUT', `/api/arch/projects/${encodeURIComponent(pid)}/watch`, {watch_prs: ev.target.checked})));
    el.querySelector('#arRev')?.addEventListener('click', ev => { const n = parseInt(el.querySelector('#arPr').value, 10); if (!n) return; ev.target.disabled = true; go(() => api('POST', `/api/arch/projects/${encodeURIComponent(pid)}/review`, {pr: n}), 'Checked - the notes are a draft until you post them.'); });
    el.querySelectorAll('[data-arpost]').forEach(b => b.addEventListener('click', () => { if (confirm('Post these notes as one comment on the pull request?')) go(() => api('POST', `/api/arch/reviews/${encodeURIComponent(b.dataset.arpost)}/post`), 'Posted on the PR.'); }));
    el.querySelectorAll('[data-ardisc]').forEach(b => b.addEventListener('click', () => go(() => api('POST', `/api/arch/reviews/${encodeURIComponent(b.dataset.ardisc)}/discard`))));
    if (busy) ATIMER = setTimeout(() => { if (visible(el) && AOPEN === pid) archOne(el, pid); }, 5000);
  }

  return {hub, desk, social, cad, game, arch};
};
