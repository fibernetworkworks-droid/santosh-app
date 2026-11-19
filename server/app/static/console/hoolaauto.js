/* v0.947 HOOLA AUTO inside Hoola Code (/console/code#/auto): a whole client project run by specialist agents, each on its
   own Hoola Code session. Design: claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz. Server: server/app/hoolaauto (/api/auto/*).
   code.js owns the shell, the sidebar and the address; this file draws the Auto screens into #hcdBody:
     #/auto                       home - every project
     #/auto/<pid>                 the right screen for the project's phase
     #/auto/<pid>/mission|intake|sources|env|gates|monitor
     #/auto/<pid>/talk            v0.949 talk to the Intake agent (the browser hears and speaks; the server gets text)
     #/auto/<pid>/gate/<gid>      one gate (her tap carries the gate's hash)
     #/auto/<pid>/agent/<role>    one agent: its chat, its session's steps, its tasks
   HOOLA CHAT KIT (chatkit.js): the agent's chat and the intake talk are the main chat's own thread - her bubble, the
   reply landing word by word, ONE working row, Copy / Read aloud under the newest reply, the same typing box.
   Strict CSP: no inline handlers; every server string goes through esc(). */
'use strict';
window.HoolaAuto = function ({api, esc, toast, nav, svg, dialog, step}) {
  let LASTVIEW = '', MSIG = '', BODY = null, TIMER = 0, ROUTE = '', LIST = null, SIG = '', FILTER = 'all', HOMETAB = 'all', BUSY = false;
  const A = '/api/auto';
  const enc = encodeURIComponent;
  const rs = n => 'Rs ' + Math.round(+n || 0).toLocaleString('en-IN');
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const clock = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const s = Math.max(0, Math.round((Date.now() - t) / 1000));
    return s < 3600 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s` : `${Math.floor(s / 3600)}h ${String(Math.floor(s % 3600 / 60)).padStart(2, '0')}m`; };
  const hhmm = iso => { const t = new Date(iso || ''); return isNaN(t) ? '' : t.toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false}); };
  const pct = n => Math.max(0, Math.min(100, Math.round(+n || 0)));
  const bar = (n, cls = '') => `<span class="hca-bar ${cls}"><i style="width:${pct(n)}%"></i></span>`;
  const DOT = {run: 'run', working: 'run', queued: 'run', need: 'warn', needs: 'warn', done: 'ok', intake: '', paused: '', wait: ''};
  const STATE = {working: 'Working', queued: 'Waiting for a slot', needs: 'Needs you', done: 'Done', wait: 'Not started'};
  const GATES = [['G1', 'Scope sign-off'], ['G2', 'Design approval'], ['G3', 'Plan + price'], ['G4', 'Sprint demo'], ['G5', 'Change approval'],
    ['G6', 'UAT sign-off'], ['G7', 'Go-live'], ['G8', 'Handover']];
  const STEPS5 = [['Attach environments', 'Code, CI, test keys'], ['Client intake', 'Every answer with its source'], ['Review and start', 'You sign off scope, plan and cost'],
    ['Agents build', 'Each in its own live session'], ['You approve gates', 'Demo, changes, UAT, go-live, handover']];

  // ------------------------------------------------------------------ plumbing
  function leave() { clearInterval(TIMER); TIMER = 0; talkQuiet(); setTimeout(sweep, 0); }
  // a thread whose screen is gone is let go (its working clock stops)
  function sweep() {
    if (AG && !AG.root.isConnected) { const a = AG; AG = null; a.t.clear(); }
    if (TALK.kit && !TALK.root.isConnected) { const k = TALK.kit; TALK.kit = null; TALK.bar = null; TALK.busy = false; k.clear(); }
  }
  // chatkit.js helpers: a reply that was already there is shown whole (a final text that does not continue what is shown
  // is shown at once - stream.js), and nothing of it moves
  const whole = (k, text) => { k.nextBlock(); k.delta(String(text).startsWith('\u2060') ? ' ' : '\u2060'); return k.final(String(text)); };
  const still = root => { root.querySelectorAll('.hck-txt .w').forEach(w => w.replaceWith(w.textContent)); root.querySelectorAll('.hck-acts').forEach(a => { a.style.animation = 'none'; }); };
  const lastTurn = root => [...root.children].filter(n => n.classList.contains('hck-ho')).pop();
  // the kit's box with no Stop to offer: Send (and the mic) simply wait while a reply is on its way
  function hold(bar, on) { if (!bar) return; bar._hold = !!on; const go = bar.input.parentElement.querySelector('.go'), mic = bar.input.parentElement.querySelector('[data-b="mic"]');
    if (go) go.disabled = !!on || !bar.input.value.trim(); if (mic) mic.disabled = !!on; }
  function boxOf(host, o) { const bar = window.HoolaChat.bar(host, o), go = host.querySelector('.go');
    bar.input.addEventListener('input', () => { if (bar._hold && go) go.disabled = true; }); return bar; }
  function poll(fn, ms) { clearInterval(TIMER); const me = ROUTE; TIMER = setInterval(() => { if (ROUTE !== me) return leave(); if (!document.hidden) fn(); }, ms); }
  async function refresh() {
    try { const r = await api('GET', A + '/projects'); const s = JSON.stringify(r.projects.map(p => [p.id, p.name, p.state])); const changed = s !== SIG; SIG = s; LIST = r; return changed; }
    catch (e) { return false; }
  }
  const cached = () => (LIST && LIST.projects) || [];
  const go = path => nav('auto', path);
  function wire(root) {
    if (root._hca) return; root._hca = true;
    root.addEventListener('click', ev => { const b = ev.target.closest('[data-ha]'); if (!b || !root.contains(b)) return; const f = ACT[b.dataset.ha]; if (f) { ev.preventDefault(); f(b); } });
    root.addEventListener('submit', ev => { const f = ev.target; if (!f.dataset || !f.dataset.haf) return; ev.preventDefault(); const h = SUB[f.dataset.haf]; if (h) h(f); });
  }
  const page = (inner, cls = '', keepScroll = false) => { const y = keepScroll ? (BODY.querySelector('.hca-page') || {}).scrollTop || 0 : 0;
    BODY.innerHTML = `<main class="hca-page ${cls}"><div class="hca-in">${inner}</div></main>`; if (y) BODY.querySelector('.hca-page').scrollTop = y; };
  const fail = e => { BODY.innerHTML = `<main class="hca-page"><div class="hca-in"><button type="button" class="hcd-back" data-auto="">${svg('chev', 'hcd-flip')}Hoola Auto</button><p class="hcd-err">${esc(e.message || e)}</p></div></main>`; };

  // ------------------------------------------------------------------ routing
  async function draw(path, root) {
    BODY = root; wire(root); leave(); ROUTE = path || '';
    const [pid, view, arg] = ROUTE.split('/');
    if ((view || '') !== LASTVIEW) { FILTER = 'all'; LASTVIEW = view || ''; }
    try {
      if (!pid) return await home();
      if (!view) return await routeProject(pid);
      if (view === 'mission') return await mission(pid);
      if (view === 'intake') return await intake(pid);
      if (view === 'sources') return await sources(pid);
      if (view === 'env') return await envs(pid);
      if (view === 'gates') return await gateList(pid);
      if (view === 'talk') return await talk(pid);
      if (view === 'monitor') return await monitor(pid);
      if (view === 'gate' && arg) return await gate(pid, arg);
      if (view === 'agent' && arg) return await agent(pid, arg);
      return await routeProject(pid);
    } catch (e) { fail(e); } finally { sweep(); }
  }
  async function routeProject(pid) {
    const p = await api('GET', `${A}/projects/${enc(pid)}`);
    if (p.phase === 'setup') return go(`${pid}/env`);
    if (p.phase === 'intake') return go(`${pid}/intake`);
    if (['review', 'design', 'plan'].includes(p.phase)) {
      const gs = await api('GET', `${A}/projects/${enc(pid)}/gates`); const now = gs.find(g => g.state === 'now');
      if (now) return go(`${pid}/gate/${now.id}`);
    }
    return go(`${pid}/mission`);
  }
  // the project's title bar + its sub-nav (Mission / Intake / Sources / Environments / Gates / Monitor)
  function head(p, on, right = '') {
    document.title = `${p.name} · Hoola Auto`;
    const tab = (k, name) => `<button type="button" role="tab" aria-selected="${on === k}" data-auto="${esc(p.id)}/${k}">${name}</button>`;
    return `<button type="button" class="hcd-back" data-auto="">${svg('chev', 'hcd-flip')}Hoola Auto</button>
      <div class="hca-phead"><div><h1>${esc(p.name)}</h1><p class="hca-sub">${esc(p.client || 'No client name yet')} · ${esc(p.phase_label || '')}${p.paused ? ' · <b class="hca-warn">Paused</b>' : ''}</p></div>${right}</div>
      <div class="hcd-tabs hca-ptabs" role="tablist">${tab('mission', 'Mission control')}${tab('intake', 'Intake')}${tab('sources', 'Sources')}${tab('env', 'Environments')}${tab('gates', 'Gates')}${tab('monitor', 'Monitor')}</div>`;
  }

  // ------------------------------------------------------------------ home
  async function home() {
    document.title = 'Hoola Auto · Hoola Code';
    const arch = HOMETAB === 'archived';
    const r = await api('GET', `${A}/projects${arch ? '?archived=true' : ''}`); if (!arch) LIST = r;
    const all = r.projects || [];
    const keep = p => HOMETAB === 'all' || HOMETAB === 'archived' || (HOMETAB === 'run' ? p.state === 'run' : HOMETAB === 'need' ? p.state === 'need' : p.phase === 'done');
    const shown = all.filter(keep);
    const n = k => (LIST?.projects || []).filter(p => k === 'run' ? p.state === 'run' : k === 'need' ? p.state === 'need' : p.phase === 'done').length;
    const tab = (k, name) => `<button type="button" role="tab" aria-selected="${HOMETAB === k}" data-ha="hometab" data-tab="${k}">${name}</button>`;
    const groups = [['Building', p => p.state === 'run'], ['Needs you', p => p.state === 'need'], ['Intake', p => p.state === 'intake'], ['Paused', p => p.state === 'paused'], ['Handed over', p => p.state === 'done']];
    const row = p => `<div class="hca-prow"><button type="button" class="hca-prowb" data-auto="${esc(p.id)}">
        <i class="hcd-dot ${DOT[p.state] || ''}" aria-hidden="true"></i>
        <span class="hca-pname"><b>${esc(p.name)}</b><small>${esc(p.sub)}</small></span>
        <span class="hca-pprog"><span class="hca-pl"><span>${esc(p.phase_label)}</span><em>${pct(p.pct)}%</em></span>${bar(p.pct, p.state === 'need' ? 'warn' : p.phase === 'done' ? 'ok' : '')}</span>
        <span class="hca-pgate ${p.state === 'need' ? 'warn' : p.phase === 'done' ? 'ok' : ''}">${esc(p.gate || (p.phase === 'done' ? 'All 8 gates approved' : ''))}</span>
        <span class="hca-pcost">${rs(p.spent_inr)} / ${rs(p.cap_inr)}</span></button>
      <button type="button" class="hcd-icb" data-ha="parch" data-id="${esc(p.id)}" data-on="${p.archived ? 0 : 1}" aria-label="${p.archived ? 'Restore' : 'Archive'} ${esc(p.name)}" title="${p.archived ? 'Restore' : 'Archive'}">${svg(p.archived ? 'up' : 'x')}</button></div>`;
    const body = arch ? (shown.length ? shown.map(row).join('') : '<p class="hcd-mut">Nothing archived.</p>')
      : !all.length ? `<div class="hca-empty"><h2>No Auto projects yet</h2><p class="hcd-mut">Start one: attach the repos, collect the client's answers, approve the plan, and the agents build it while you watch.</p></div>`
      : groups.map(([name, f]) => { const rows = shown.filter(f); return rows.length ? `<div class="hca-grp"><span class="hca-glbl">${name}</span>${rows.map(row).join('')}</div>` : ''; }).join('') || '<p class="hcd-mut">Nothing here.</p>';
    page(`<div class="hca-phead"><div><h1>Hoola Auto</h1><p class="hca-sub">Give Hoola a whole client project. Specialist agents build it side by side, each in its own session you can open and talk to. Every gate waits for your tap.</p></div>
        <button type="button" class="hcd-btn pri" data-ha="newproj">${svg('new')}New Auto project</button></div>
      <ol class="hca-steps">${STEPS5.map((s, i) => `<li><span class="hca-n">${i + 1}</span><span><b>${s[0]}</b><small>${s[1]}</small></span></li>`).join('')}</ol>
      <div class="hcd-tabs" role="tablist">${tab('all', `All · ${(LIST?.projects || []).length}`)}${tab('run', `Building · ${n('run')}`)}${tab('need', `Needs you · ${n('need')}`)}${tab('done', `Handed over · ${n('done')}`)}${tab('archived', 'Archived')}</div>
      ${body}
      <p class="hcd-mut hca-foot">Costs are model use against each project's cap. Every agent works on the project's own branch; merging into your main branch and going live are always your tap.${LIST ? ` This server runs ${LIST.live_limit} Hoola Code sessions at a time; the rest wait their turn.` : ''}</p>`);
  }

  async function newProject() {
    let repos = [], envs = {envs: []};
    try { [repos, envs] = await Promise.all([api('GET', '/api/devsahayak/repos'), api('GET', '/api/devsahayak/envs')]); } catch (e) { /* the dialog still opens */ }
    const rl = Array.isArray(repos) ? repos : (repos.repos || []);
    const r = await dialog(`<h2>New Auto project</h2>
      <label class="hcd-f"><span>Project name</span><input id="hcaNName" maxlength="120" required placeholder="Clinic booking app" autocomplete="off"></label>
      <label class="hcd-f"><span>Client</span><input id="hcaNClient" maxlength="120" placeholder="Sai Dental Clinic, Pune" autocomplete="off"></label>
      <label class="hcd-f"><span>Client email <small>for the intake link</small></span><input id="hcaNMail" type="email" maxlength="160" autocomplete="off"></label>
      <fieldset class="hca-fs"><legend>Repositories the agents work in</legend>${rl.length ? rl.map((x, i) => `<label class="hca-chk"><input type="checkbox" name="hcaNRepo" value="${esc(x.repo)}"${i === 0 ? ' checked' : ''}><span>${esc(x.repo)}</span></label>`).join('')
        : '<p class="hcd-mut">No repositories yet. Add one in Hoola Code Settings; you can attach it later.</p>'}</fieldset>
      <label class="hcd-f"><span>Environment</span><select id="hcaNEnv"><option value="">Each repo's own settings</option>${(envs.envs || []).map(e => `<option value="${esc(e.id)}">${esc(e.name)}</option>`).join('')}</select></label>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Create project</button></div>`);
    if (r !== 'ok') return;
    const d = document.getElementById('hcdDlg'), q = s => d.querySelector(s);
    const b = {name: q('#hcaNName').value.trim(), client_name: q('#hcaNClient').value.trim(), client_email: q('#hcaNMail').value.trim(),
      repos: [...d.querySelectorAll('input[name=hcaNRepo]:checked')].map(x => x.value), env_id: q('#hcaNEnv').value};
    if (!b.name) return toast('Give the project a name.', true);
    try { const p = await api('POST', A + '/projects', b); await refresh(); go(p.id); } catch (e) { toast(e.message, true); }
  }

  // ------------------------------------------------------------------ environments
  async function envs(pid) {
    const [p, v] = await Promise.all([api('GET', `${A}/projects/${enc(pid)}`), api('GET', `${A}/projects/${enc(pid)}/env`)]);
    const st = (ok, yes, no) => `<span class="hcd-c ${ok ? 'ok' : 'warn'}">${ok ? yes : no}</span>`;
    page(`${head(p, 'env')}
      <div class="hca-meter"><span>${v.connected} of ${v.required} required connected</span>${bar(100 * v.connected / Math.max(1, v.required), v.ready ? 'ok' : 'warn')}</div>
      <section class="hca-card"><h3>Code and CI</h3>
        <div class="hca-erow"><span class="hca-ini">GH</span><span class="hca-en"><b>GitHub</b><small>Branches and pull requests on the project branch only</small></span>${st(v.github, 'Connected', 'Not connected')}
          ${v.github ? '' : '<a class="hcd-btn sm" href="#/settings">Connect</a>'}</div>
        ${(v.repos || []).map(r => `<div class="hca-erow"><span class="hca-ini">${esc((r.repo.split('/')[1] || r.repo).slice(0, 2).toUpperCase())}</span>
          <span class="hca-en"><b>${esc(r.repo)}</b><small>CI: ${esc(r.ci || 'not read')}${r.setup ? ' · setup command set' : ''}${r.test ? ' · test command set' : ''}</small></span>
          ${st(r.added, 'Added', 'Not added in Hoola Code')}${r.added ? '' : '<a class="hcd-btn sm" href="#/settings">Add</a>'}</div>`).join('') || '<p class="hcd-mut">No repository attached yet.</p>'}
        <form class="hca-inline" data-haf="repos"><label class="hcd-sr" for="hcaRepos">Repositories</label><input id="hcaRepos" value="${esc((p.repos || []).join(', '))}" placeholder="owner/repo, owner/repo">
          <button class="hcd-btn sm">Save repos</button></form></section>
      <section class="hca-card"><h3>Environment</h3>
        <div class="hca-erow"><span class="hca-ini">${svg('cloud')}</span><span class="hca-en"><b>${esc(v.env?.name || "Each repo's own settings")}</b><small>Network, variables and the setup script the sessions run with</small></span>
          <button type="button" class="hcd-btn sm" data-ha="pickenv" data-cur="${esc(v.env_id || '')}">Change</button></div></section>
      <section class="hca-card"><h3>Keys added outside the box</h3>
        ${(v.repos || []).map(r => `<div class="hca-erow"><span class="hca-en"><b>${esc(r.repo)}</b><small>${r.keys.length ? esc(r.keys.join(', ')) : 'No test keys yet'}</small></span>${st(r.keys.length, `${r.keys.length} key${r.keys.length === 1 ? '' : 's'}`, 'None')}</div>`).join('')}
        <p class="hcd-mut">Add test keys per host in Hoola Code Settings &gt; the repo. Agents never see their values; agents that need a missing key wait and ask.</p></section>
      <section class="hca-card"><h3>Rules for the agents</h3><ul class="hca-rules">${(v.rules || []).map(x => `<li>${svg('ok', 'ok')}<span>${esc(x)}</span></li>`).join('')}</ul>
        <form class="hca-inline" data-haf="cap"><label for="hcaCap">Cost cap (Rs)</label><input id="hcaCap" type="number" min="100" step="100" value="${Math.round(p.cap_inr || 0)}"><button class="hcd-btn sm">Save cap</button></form></section>
      ${v.needed && v.needed.length ? `<section class="hca-card hca-need"><h3>Still needed</h3><ul>${v.needed.map(x => `<li>${esc(x)}</li>`).join('')}</ul></section>` : ''}
      <p class="hcd-mut">${esc(v.not_connected || '')} This server runs ${esc(v.live_limit)} Hoola Code sessions at a time; the rest wait their turn.</p>
      <div class="hca-actions"><button type="button" class="hcd-btn pri" data-auto="${esc(pid)}/intake"${p.repos && p.repos.length ? '' : ' disabled'}>Continue to client intake</button></div>`);
  }

  // ------------------------------------------------------------------ intake
  const STATEW = {confirmed: ['Confirmed', 'ok'], found: ['Client to confirm', 'warn'], conflict: ['Conflict', 'bad'], missing: ['Missing', 'soft']};
  function fieldHTML(pid, f) {
    const sw = STATEW[f.state] || STATEW.missing;
    const src = f.state === 'missing' ? '' : `<small class="hca-src">${esc(f.source_label)}${f.source_ref ? ' · ' + esc(f.source_ref) : ''}</small>`;
    let act = '';
    if (f.state === 'found') act = `<button type="button" class="hcd-btn sm" data-ha="confirm" data-key="${esc(f.key)}" data-pick="a">Confirm</button>`;
    if (f.state === 'conflict') act = `<span class="hca-pick"><button type="button" class="hcd-btn sm" data-ha="confirm" data-key="${esc(f.key)}" data-pick="a">Keep: ${esc(f.value.slice(0, 40))}</button>
      <button type="button" class="hcd-btn sm" data-ha="confirm" data-key="${esc(f.key)}" data-pick="b">Take: ${esc((f.alt?.value || '').slice(0, 40))}</button></span>`;
    return `<form class="hca-field" data-haf="answer" data-key="${esc(f.key)}"><label for="hcaF_${esc(f.key)}"><i class="hcd-dot ${sw[1] === 'soft' ? '' : sw[1]}" aria-hidden="true"></i>${esc(f.q)}</label>
      <div class="hca-frow"><input id="hcaF_${esc(f.key)}" name="v" value="${esc(f.value)}" maxlength="4000" autocomplete="off" placeholder="${f.choices.length ? esc(f.choices.join(' / ')) : 'Type the answer'}">
      <button class="hcd-btn sm">Save</button></div><div class="hca-fmeta"><span class="hcd-c ${sw[1]}">${sw[0]}</span>${src}${act}</div>
      ${f.state === 'conflict' && f.alt ? `<small class="hca-src">Other source: ${esc(f.alt.source_ref || '')}</small>` : ''}</form>`;
  }
  let SEC = 0;
  async function intake(pid) {
    const v = await api('GET', `${A}/projects/${enc(pid)}/intake`);
    const p = v.project, secs = v.sections || [], cur = secs[Math.min(SEC, secs.length - 1)] || {fields: []};
    const nx = v.next, link = v.client_link || {};
    const asks = nx ? `<section class="hca-card hca-ask"><span class="hcd-badge info">Hoola asks</span><p class="hca-q">${esc(nx.q)}</p>
        ${nx.state === 'conflict' ? `<p class="hcd-mut">Two sources disagree: “${esc(nx.value)}” (${esc(nx.source_ref)}) or “${esc(nx.alt?.value || '')}” (${esc(nx.alt?.source_ref || '')}).</p>
          <div class="hca-choices"><button type="button" class="hcd-btn" data-ha="confirm" data-key="${esc(nx.key)}" data-pick="a">Keep the first</button><button type="button" class="hcd-btn" data-ha="confirm" data-key="${esc(nx.key)}" data-pick="b">Take the second</button></div>`
        : `<div class="hca-choices">${(nx.choices || []).map(c => `<button type="button" class="hcd-btn" data-ha="choose" data-key="${esc(nx.key)}" data-val="${esc(c)}">${esc(c)}</button>`).join('')}</div>
          <form class="hca-inline" data-haf="answer" data-key="${esc(nx.key)}"><label class="hcd-sr" for="hcaAsk">Your answer</label><input id="hcaAsk" name="v" maxlength="4000" placeholder="Type my own answer" autocomplete="off"><button class="hcd-btn sm">Answer</button></form>`}
        <small class="hca-src">${esc(nx.section)} · ${v.of - v.answered} questions left · never type passwords or keys here</small></section>`
      : `<section class="hca-card hca-ask"><span class="hcd-badge gh">All answered</span><p class="hca-q">Every question has an answer. Send it for review when you are ready.</p></section>`;
    page(`${head(p, 'intake', `<div class="hca-hbtns"><button type="button" class="hcd-btn" data-auto="${esc(pid)}/talk">${MIC}Talk to the Intake agent</button><button type="button" class="hcd-btn" data-ha="addsrc">Add a source</button>
        <button type="button" class="hcd-btn pri" data-ha="review"${v.can_review ? '' : ' disabled title="Attach a repository first, or the scope is already signed off"'}>Send for review</button></div>`)}
      <div class="hca-meter"><span>${v.answered} of ${v.of} answered · ${v.counts.found} for the client to confirm · ${v.counts.conflict} conflict${v.counts.conflict === 1 ? '' : 's'}</span>${bar(100 * v.answered / Math.max(1, v.of))}</div>
      <div class="hca-linkrow">${link.on ? `Client link on (…${esc(link.tail)}), works until ${esc(new Date(link.until).toLocaleDateString('en-IN'))}${link.signed ? ' · <b class="hca-ok">client signed off</b>' : ''}
        <button type="button" class="hcd-btn sm" data-ha="link" data-on="1">New link</button><button type="button" class="hcd-btn sm" data-ha="link" data-on="0">Stop the link</button>`
        : `No client link yet. <button type="button" class="hcd-btn sm" data-ha="link" data-on="1">Make a client link</button>`}</div>
      <div class="hca-split3"><nav class="hca-secs" aria-label="Intake sections">${secs.map((s, i) => `<button type="button" class="hca-sec${i === SEC ? ' on' : ''}" data-ha="sec" data-i="${i}">
          <i class="hca-mark ${s.done === s.of ? 'ok' : s.done ? 'part' : ''}" aria-hidden="true">${s.done === s.of ? svg('ok') : ''}</i><span>${esc(s.name)}</span><em>${s.done}/${s.of}</em></button>`).join('')}</nav>
        <section class="hca-card hca-fields"><h3>${esc(cur.name || '')}</h3>${(cur.fields || []).map(f => fieldHTML(pid, f)).join('')}</section>
        <div class="hca-side">${asks}
          <section class="hca-card"><h3>Sources</h3>${(v.sources || []).slice(0, 6).map(s => `<div class="hca-srow"><span><b>${esc(s.name)}</b><small>${esc(s.kind)} · ${esc(ago(s.at))}</small></span>
            <span class="hcd-c ${s.status === 'done' ? 'ok' : s.status === 'failed' ? 'bad' : 'run'}">${s.status === 'done' ? `${s.answers} answers` : s.status === 'failed' ? 'Failed' : 'Reading…'}</span></div>${s.status === 'failed' && s.note ? `<p class="hcd-err">${esc(s.note)}</p>` : ''}`).join('') || '<p class="hcd-mut">No sources yet.</p>'}
            <button type="button" class="hcd-link" data-auto="${esc(pid)}/sources">Where each answer came from</button></section></div></div>
      <p class="hcd-mut">You can send with gaps. Agents that need a missing answer wait and ask.</p>`);
    if ((v.sources || []).some(s => s.status === 'reading')) poll(() => { const a = document.activeElement;   // never while she is typing
      if (!BUSY && !(a && BODY.contains(a) && /INPUT|TEXTAREA|SELECT/.test(a.tagName))) draw(ROUTE, BODY); }, 4000);
  }

  // ------------------------------------------------------------------ sources
  async function sources(pid) {
    const v = await api('GET', `${A}/projects/${enc(pid)}/sources`);
    const st = v.counts || {};
    const rows = (v.rows || []).filter(f => FILTER === 'all' || f.state === FILTER);
    const tab = (k, name, n) => `<button type="button" role="tab" aria-selected="${FILTER === k}" data-ha="srcfilter" data-f="${k}">${name} · ${n}</button>`;
    page(`${head(v.project, 'sources', `<button type="button" class="hcd-btn pri" data-ha="addsrc">${svg('new')}Add a source</button>`)}
      <div class="hca-chips">${Object.entries(v.per_source || {}).map(([k, n]) => `<span class="hcd-pill">${esc(k)} · ${n}</span>`).join('')}</div>
      ${(v.conflicts || []).map(f => `<section class="hca-card hca-conf"><span class="hcd-badge bad">Conflict</span><p class="hca-q">${esc(f.q)}</p>
        <p><b>${esc(f.source_ref || f.source_label)}:</b> ${esc(f.value)}<br><b>${esc(f.alt?.source_ref || 'Other source')}:</b> ${esc(f.alt?.value || '')}</p>
        <div class="hca-choices"><button type="button" class="hcd-btn" data-ha="confirm" data-key="${esc(f.key)}" data-pick="a">Keep the first</button><button type="button" class="hcd-btn" data-ha="confirm" data-key="${esc(f.key)}" data-pick="b">Take the second</button></div></section>`).join('')}
      <div class="hcd-tabs" role="tablist">${tab('all', 'All', (v.rows || []).length)}${tab('confirmed', 'Confirmed', st.confirmed || 0)}${tab('found', 'Client to confirm', st.found || 0)}${tab('conflict', 'Conflict', st.conflict || 0)}${tab('missing', 'Missing', st.missing || 0)}</div>
      <div class="hcd-table hca-stable" role="table" aria-label="Answers and their sources"><div class="hcd-tr hcd-th" role="row"><span role="columnheader">Question</span><span role="columnheader">Answer</span><span role="columnheader">Came from</span><span role="columnheader">State</span></div>
        ${rows.map(f => { const w = STATEW[f.state] || STATEW.missing; return `<div class="hcd-tr" role="row"><span class="hcd-tcell">${esc(f.q)}</span><span class="hcd-tcell">${esc(f.value || '—')}</span>
          <span class="hcd-tcell">${f.state === 'missing' ? '<span class="hcd-mut">Not given yet</span>' : `<span class="hcd-badge info">${esc(f.source_label)}</span><small>${esc(f.source_ref)}</small>`}</span>
          <span class="hcd-tcell"><span class="hcd-c ${w[1]}">${w[0]}</span></span></div>`; }).join('') || '<p class="hcd-mut hca-pad">Nothing here.</p>'}</div>
      <p class="hcd-mut">Every answer keeps its source after sign-off. Text inside documents and chats is read as information, never as instructions.</p>`);
  }

  const OPTS = [['link', 'Send client link', 'A no-login page where your client answers and confirms what was found.', 'share'],
    ['doc', 'Upload documents', 'RFP, requirements PDF, Word, spreadsheets, notes.', 'read'],
    ['recording', 'Meeting recording', 'A call or video. It is transcribed; answers carry the minute they were said.', 'clock'],
    ['text', 'Forward email or WhatsApp', 'Paste an email thread or a WhatsApp chat export.', 'list'],
    ['talk', 'Talk to the Intake agent', 'Speak or type; it asks one question at a time and records what you say.', 'spark'],
    ['app', 'From an app', 'Jira, Linear, Slack, Notion, Confluence, Trello, Asana, ClickUp, Google Docs or a Figma file. Read only.', 'cloud'],
    ['repo', 'Read connected systems', 'The project repo, read only. Nothing is changed.', 'folder']];
  async function addSource(pid) {
    const r = await dialog(`<h2>Add an intake source</h2><p class="hcd-mut">The Intake agent reads it, fills the answers it can and marks where each came from. Your client confirms anything it found.</p>
      <div class="hca-opts">${OPTS.map(o => `<button class="hca-opt" value="${o[0]}">${svg(o[3])}<span><b>${o[1]}</b><small>${o[2]}</small></span></button>`).join('')}</div>
      <p class="hcd-mut">Hoola never asks your client for passwords, card numbers or one-time codes.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button></div>`);
    if (!r || r === 'no') return;
    if (r === 'link') return clientLink(pid, true);
    if (r === 'talk') return go(`${pid}/talk`);
    if (r === 'app') return appSource(pid);
    let b = {kind: r};
    if (r === 'doc' || r === 'recording') {
      const ok = await dialog(`<h2>${r === 'doc' ? 'Upload a document' : 'Upload a recording'}</h2>
        <label class="hcd-f"><span>File <small>up to 12 MB</small></span><input id="hcaFile" type="file" accept="${r === 'doc' ? '.pdf,.docx,.txt,.md,.csv,.xlsx,.pptx' : 'audio/*,video/mp4,.m4a,.mp3,.wav,.ogg'}" required></label>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Read it</button></div>`);
      const f = document.querySelector('#hcdDlg #hcaFile')?.files?.[0];
      if (ok !== 'ok' || !f) return;
      if (f.size > 12 * 1024 * 1024) return toast('Files up to 12 MB.', true);
      b.name = f.name; b.data = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(',')[1] || ''); fr.onerror = rej; fr.readAsDataURL(f); });
    } else if (r === 'text') {
      const ok = await dialog(`<h2>Paste an email or chat</h2><label class="hcd-f"><span>Name</span><input id="hcaTName" maxlength="200" placeholder="Email from the client, 14 Nov"></label>
        <label class="hcd-f"><span>Text</span><textarea id="hcaText" rows="10" required></textarea></label>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Read it</button></div>`);
      const d = document.getElementById('hcdDlg');
      if (ok !== 'ok') return;
      b.name = d.querySelector('#hcaTName')?.value.trim() || ''; b.text = d.querySelector('#hcaText')?.value || '';
    }
    try { await api('POST', `${A}/projects/${enc(pid)}/sources`, b); toast('Reading it now. Answers appear as they are found.'); draw(ROUTE, BODY); } catch (e) { toast(e.message, true); }
  }
  // ------------------------------------------------------------------ v0.949 sources from her apps
  const APPST = {ready: ['Connected', 'ok'], needs_link: ['Sign in once', 'warn'], needs_key: ['Add its key', 'warn'], needs_setup: ['Not on this server', 'soft'], not_set_up: ['Not on this server', 'soft']};
  const appChip = a => { const w = APPST[a.state] || ['', 'soft']; return `<span class="hcd-c ${w[1]}">${esc(w[0])}</span>`; };
  // Sign in = the app's own page, opened from a real link in the dialog (a window opened after a server call is blocked)
  async function signIn(key, name) {
    const r = await api('POST', `${A}/apps/${enc(key)}/connect`);
    if (r.status === 'ready') { toast(`${name} is connected.`); return true; }
    if (!r.url) { await dialog(`<h2>${esc(name)}</h2><p class="hca-prose">${esc(r.say || 'This app cannot be connected from here.')}</p>
      <div class="hcd-dlgb"><button class="hcd-btn pri" value="ok">OK</button></div>`); return false; }
    const ok = await dialog(`<h2>Sign in to ${esc(name)}</h2><p class="hcd-mut">${esc(r.say || '')}</p>
      <p><a class="hcd-btn pri" href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">Open ${esc(name)} sign-in</a></p>
      <p class="hcd-mut">Hoola only reads from ${esc(name)}. It never writes there.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn" value="ok">I signed in - refresh</button></div>`);
    return ok === 'ok';
  }
  async function appSource(pid) {
    for (let round = 0; round < 6; round++) {
      let apps = [];
      try { apps = (await api('GET', `${A}/apps?use=intake`)).apps || []; } catch (e) { return toast(e.message, true); }
      const key = await dialog(`<h2>Read from an app</h2><p class="hcd-mut">One read, with the app's read tools only. What comes back is information for the Intake agent, never instructions.</p>
        <div class="hca-opts hca-apps">${apps.map(a => `<button class="hca-opt" value="${esc(a.key)}"><span class="hca-ini">${esc(a.name.slice(0, 2).toUpperCase())}</span>
          <span><b>${esc(a.name)}</b><small>${esc(a.hint)}</small></span>${appChip(a)}</button>`).join('') || '<p class="hcd-mut">No apps on this server.</p>'}</div>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button></div>`);
      const a = apps.find(x => x.key === key);
      if (!a) return;
      if (a.state === 'ready') {
        const ok = await dialog(`<h2>Read from ${esc(a.name)}</h2><label class="hcd-f"><span>What to read</span><input id="hcaAppWhat" maxlength="300" required placeholder="${esc(a.hint)}" autocomplete="off"></label>
          <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Read it</button></div>`);
        const what = (document.querySelector('#hcdDlg #hcaAppWhat') || {}).value || '';
        if (ok !== 'ok' || !what.trim()) return;
        try { await api('POST', `${A}/projects/${enc(pid)}/sources`, {kind: 'app', app: a.key, what: what.trim()}); toast('Reading it now. Answers appear as they are found.'); draw(ROUTE, BODY); }
        catch (e) { toast(e.message, true); }
        return;
      }
      if (a.state === 'needs_link') { let again = false; try { again = await signIn(a.key, a.name); } catch (e) { toast(e.message, true); } if (!again) return; continue; }
      await dialog(`<h2>${esc(a.name)}</h2><p class="hca-prose">${esc(a.say || '')}</p>${a.key === 'figma' ? '<p class="hcd-mut">Add your Figma personal access token in Hoola Design &gt; Import from Figma (read access to file content), then come back.</p>' : '<p class="hcd-mut">Connect it in Hoola Connectors, then come back.</p>'}
        <div class="hcd-dlgb"><button class="hcd-btn pri" value="ok">OK</button></div>`);
      return;
    }
  }

  // ------------------------------------------------------------------ v0.949 talk to the Intake agent
  const MIC = '<svg class="hcd-ic" viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="12" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  let TALK = {pid: '', msgs: [], aloud: true, rec: null, listening: false, last: null, kit: null, root: null, bar: null, busy: false};
  function talkQuiet() {
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* nothing to stop */ }
    if (TALK.rec) { try { TALK.rec.abort(); } catch (e) { /* already stopped */ } TALK.rec = null; }
    TALK.listening = false;
  }
  function sayAloud(text) {
    if (!TALK.aloud || !text || !window.speechSynthesis || typeof SpeechSynthesisUtterance === 'undefined') return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text), vs = window.speechSynthesis.getVoices() || [];
      u.lang = 'en-IN'; u.voice = vs.find(v => v.lang === 'en-IN') || vs.find(v => /^en/i.test(v.lang)) || null;
      window.speechSynthesis.speak(u);
    } catch (e) { /* a browser without a voice: the words stay on the screen */ }
  }
  const heard = () => { const s = document.createElement('small'); s.className = 'hca-heard'; s.innerHTML = MIC + 'heard'; return s; };
  function gotsInto(root, got) {          // what the reply recorded sits under its words, inside the same turn
    if (!(got || []).length) return; const ho = lastTurn(root); if (!ho) return;
    const d = document.createElement('div'); d.className = 'hca-gots';
    d.innerHTML = got.map(g => `<span class="hca-got">${svg('ok', 'ok')}Recorded: ${esc(g.q)} - ${esc(g.value)}</span>`).join(''); ho.append(d);
  }
  function talkReplay() {                  // coming back to the talk: what was said is drawn whole
    const k = TALK.kit, root = TALK.root; if (!k) return;
    for (const m of TALK.msgs) {
      if (m.who === 'you') { const me = k.her(m.text, {still: true}); if (m.spoken) me.append(heard()); }
      else { k.begin(); whole(k, m.text); gotsInto(root, m.got); k.end(); }
    }
    still(root);
  }
  function talkSide() {
    const el = document.getElementById('hcaTalkSide'), v = TALK.last; if (!el || !v) return;
    el.innerHTML = `<h3>Progress</h3><div class="hca-meter"><span>${esc(v.answered)} of ${esc(v.of)} answered</span>${bar(100 * v.answered / Math.max(1, v.of), v.complete ? 'ok' : '')}</div>
      ${v.next ? `<p class="hcd-mut">Next question</p><p class="hca-q">${esc(v.next.q)}</p>${(v.next.choices || []).length ? `<div class="hca-choices">${v.next.choices.map(c => `<button type="button" class="hcd-btn sm" data-ha="talkpick" data-val="${esc(c)}">${esc(c)}</button>`).join('')}</div>` : ''}`
        : '<p class="hca-ok">Every question has an answer.</p>'}
      <p class="hcd-mut">Spoken answers come in as <b>Found</b>: a word can be heard wrong, so you confirm them on the intake list.</p>
      <button type="button" class="hcd-btn sm" data-auto="${esc(TALK.pid)}/intake">Back to the intake list</button>`;
  }
  function talkMic() {
    const b = document.querySelector('#hcaTalkBar [data-b="mic"]'); if (!b) return;
    b.setAttribute('aria-pressed', TALK.listening ? 'true' : 'false');
    b.setAttribute('aria-label', TALK.listening ? 'Stop listening' : 'Speak');
  }
  async function talkSend(said, spoken) {
    const pid = TALK.pid, k = TALK.kit; if (!k || TALK.busy) return;
    let me = null;
    if (said) { TALK.msgs.push({who: 'you', text: said, spoken, at: new Date().toISOString()}); me = k.her(said); if (spoken) me.append(heard()); }
    const live = document.getElementById('hcaTalkLive'); if (live) live.textContent = '';
    TALK.busy = true; hold(TALK.bar, true); k.begin('Thinking…');
    let r = null;
    try { r = await api('POST', `${A}/projects/${enc(pid)}/talk`, {said, spoken: !!spoken}); }
    catch (e) {
      toast(e.message, true);
      if (said) TALK.msgs.pop();
      if (TALK.kit === k) { k.end(); if (me) me.remove(); if (said && TALK.bar && !TALK.bar.value) TALK.bar.value = said; }
    }
    if (r && TALK.kit === k && TALK.pid === pid) {
      TALK.msgs.push({who: 'agent', text: r.reply || '', got: r.got || [], at: new Date().toISOString()}); TALK.last = r;
      if (r.warn) toast(r.warn, true);
      talkSide(); sayAloud(r.speak || r.reply);
      await k.final(r.reply || '');                                      // the reply lands word by word
      if (TALK.kit === k) { gotsInto(TALK.root, r.got); k.end(); }
    }
    if (TALK.kit === k) { TALK.busy = false; hold(TALK.bar, false); }
  }
  function talkListen() {
    if (!SR) return;
    if (TALK.listening && TALK.rec) { try { TALK.rec.stop(); } catch (e) { /* stopped */ } return; }
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* no voice */ }
    const rec = new SR(); let final = '';
    rec.lang = 'en-IN'; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
    rec.onresult = ev => { let interim = ''; for (let i = ev.resultIndex; i < ev.results.length; i++) { const t = ev.results[i][0].transcript;
      if (ev.results[i].isFinal) final += t; else interim += t; }
      const l = document.getElementById('hcaTalkLive'); if (l) l.textContent = (final + ' ' + interim).trim(); };
    rec.onerror = ev => { const why = ev && ev.error; if (why === 'not-allowed' || why === 'service-not-allowed') toast('The microphone is blocked. Allow it in the browser, or type instead.', true);
      else if (why && why !== 'no-speech' && why !== 'aborted') toast('Could not hear that. Try again or type.', true); };
    rec.onend = () => { TALK.listening = false; TALK.rec = null; talkMic(); const t = final.trim();
      const l = document.getElementById('hcaTalkLive'); if (l && !t) l.textContent = '';
      if (t && document.getElementById('hcaTalkList')) { if (TALK.busy) { if (TALK.bar) TALK.bar.value = t; } else talkSend(t, true); } };
    TALK.rec = rec; TALK.listening = true; talkMic();
    try { rec.start(); } catch (e) { TALK.listening = false; TALK.rec = null; talkMic(); toast('Could not start the microphone.', true); }
  }
  async function talk(pid) {
    const p = await api('GET', `${A}/projects/${enc(pid)}`);
    const fresh = TALK.pid !== pid;
    if (TALK.kit) { TALK.kit.clear(); TALK.kit = null; }
    if (fresh) TALK = {pid, msgs: [], aloud: TALK.aloud, rec: null, listening: false, last: null, kit: null, root: null, bar: null, busy: false};
    page(`${head(p, 'intake')}
      <div class="hca-split2 hca-talk"><section class="hca-card hca-tmain"><div class="hca-sh"><b>Talk to the Intake agent</b>
          <label class="hca-aloud"><input type="checkbox" id="hcaAloud"${TALK.aloud ? ' checked' : ''}> Read replies aloud</label></div>
        <div class="hca-tlist" id="hcaTalkScroll"><div id="hcaTalkList"></div></div>
        <p id="hcaTalkLive" class="hca-tlive" aria-live="polite"></p>
        <div id="hcaTalkBar"></div>
        <p class="hcd-mut hca-cnote">${SR ? 'Your browser hears your words and reads the replies aloud; Hoola gets the text only.' : 'This browser cannot hear speech - type instead.'} Never say passwords, OTPs or card numbers.</p></section>
        <aside class="hca-card hca-tside" id="hcaTalkSide"><p class="hcd-mut">Starting…</p></aside></div>`);
    document.getElementById('hcaAloud').addEventListener('change', ev => { TALK.aloud = ev.target.checked; if (!TALK.aloud) { try { window.speechSynthesis && window.speechSynthesis.cancel(); } catch (e) { /* none */ } } });
    TALK.root = document.getElementById('hcaTalkList'); TALK.busy = false;
    TALK.kit = window.HoolaChat.mount(TALK.root, {scroller: document.getElementById('hcaTalkScroll')});
    TALK.bar = boxOf(document.getElementById('hcaTalkBar'), {placeholder: SR ? 'Tap the mic and speak, or type' : 'Type your answer', mic: !!SR,
      onSend: text => { if (TALK.busy || BUSY) { TALK.bar.value = text; return; } busy(null, '', () => talkSend(text.slice(0, 2000), false)); }, onMic: () => talkListen()});
    TALK.bar.input.maxLength = 2000; talkMic();
    talkReplay(); talkSide();
    if (fresh || !TALK.msgs.length) await talkSend('', false);
  }

  // ------------------------------------------------------------------ v0.949 the Monitor (after go-live)
  const AKIND = {site: ['Site down', 'bad'], slow: ['Slow', 'warn'], ci: ['CI red', 'bad'], feed: ['Feed', 'warn']};
  const ASTATE = {open: ['Open', 'warn'], fixing: ['Fixing', 'run'], dismissed: ['Dismissed', 'soft'], resolved: ['Cleared', 'ok']};
  let WFEEDS = null;
  function feedRows(apps) {
    const opt = (f, a) => `<option value="${esc(a.key)}"${f.app === a.key ? ' selected' : ''}>${esc(a.name)}${a.state === 'ready' ? '' : ' (not connected)'}</option>`;
    return WFEEDS.map((f, i) => { const a = apps.find(x => x.key === f.app);
      return `<div class="hca-feedrow"><label class="hcd-sr" for="hcaFApp${i}">App</label><select id="hcaFApp${i}" name="fapp">${apps.map(x => opt(f, x)).join('')}</select>
        <label class="hcd-sr" for="hcaFWhat${i}">What to watch</label><input id="hcaFWhat${i}" name="fwhat" maxlength="300" value="${esc(f.what || '')}" placeholder="${esc(a ? a.hint : '')}" autocomplete="off">
        ${a && a.state !== 'ready' ? `<button type="button" class="hcd-btn sm" data-ha="appsign" data-key="${esc(a.key)}" data-name="${esc(a.name)}" data-state="${esc(a.state)}" data-say="${esc(a.say || '')}">${a.state === 'needs_link' ? 'Sign in' : 'How to connect'}</button>` : ''}
        <button type="button" class="hcd-icb" data-ha="feeddel" data-i="${i}" aria-label="Remove this feed" title="Remove">${svg('x')}</button></div>`; }).join('');
  }
  function watchBody(f, on) {
    const feeds = []; const apps = f.querySelectorAll('[name=fapp]'), whats = f.querySelectorAll('[name=fwhat]');
    apps.forEach((s, i) => { const w = (whats[i] || {}).value || ''; if (s.value) feeds.push({app: s.value, what: w.trim()}); });
    return {url: f.querySelector('#hcaWUrl').value.trim(), every_min: +f.querySelector('#hcaWEvery').value || 60, feeds, on};
  }
  function keepFeeds() { const f = BODY.querySelector('form[data-haf=watch]'); if (f) WFEEDS = watchBody(f, false).feeds; }
  let WAPPS = [];
  async function monitor(pid, keep = false) {
    const [p, v] = await Promise.all([api('GET', `${A}/projects/${enc(pid)}`), api('GET', `${A}/projects/${enc(pid)}/watch`)]);
    WAPPS = v.apps || [];
    if (!keep || !WFEEDS) WFEEDS = (v.feeds || []).map(x => ({...x}));
    const every = [[15, '15 minutes'], [30, '30 minutes'], [60, '1 hour'], [180, '3 hours'], [360, '6 hours'], [1440, '1 day']];
    const alerts = v.alerts || [];
    const arow = a => { const k = AKIND[a.kind] || [a.kind, 'soft'], st = ASTATE[a.state] || [a.state, 'soft'];
      return `<div class="hca-alert ${esc(a.state)}"><div class="hca-ahead"><span class="hcd-badge ${k[1]}">${esc(k[0])}</span><b>${esc(a.title)}</b><span class="hcd-flex"></span><span class="hcd-c ${st[1]}">${esc(st[0])}</span></div>
        ${a.detail ? `<p class="hca-adet">${esc(a.detail)}</p>` : ''}
        <small class="hca-src">${a.repo ? esc(a.repo) + ' · ' : ''}seen ${esc(a.times)} time${a.times === 1 ? '' : 's'} · first ${esc(ago(a.first_at))}${a.times > 1 ? ` · last ${esc(ago(a.last_at))}` : ''}</small>
        ${a.state === 'fixing' && a.fix ? `<p class="hca-afix">${esc(a.fix.say || 'A fix is running in Hoola Code.')}${a.fix.url ? ` <a class="hcd-link" href="${esc(a.fix.url)}" target="_blank" rel="noopener">Pull request #${esc(a.fix.pr)}</a>` : ''}${a.fix.id ? ` <a class="hcd-link" href="#/s/${esc(a.fix.id)}">Open the session</a>` : ''}</p>` : ''}
        <div class="hca-choices">${a.state === 'open' ? `<button type="button" class="hcd-btn pri sm" data-ha="afix" data-id="${esc(a.id)}">Fix it</button><button type="button" class="hcd-btn sm" data-ha="aact" data-what="dismiss" data-id="${esc(a.id)}">Dismiss</button>`
          : a.state === 'dismissed' ? `<button type="button" class="hcd-btn sm" data-ha="aact" data-what="reopen" data-id="${esc(a.id)}">Reopen</button>` : ''}</div></div>`; };
    page(`${head(p, 'monitor', `<div class="hca-hbtns"><button type="button" class="hcd-btn" data-ha="wcheck">Check now</button></div>`)}
      <section class="hca-card hca-wtop"><div class="hca-erow"><span class="hca-ini">${svg('spark')}</span><span class="hca-en"><b>Monitor agent</b><small>${esc(v.says || '')}</small></span>
        <button type="button" class="hcd-sw" role="switch" aria-checked="${v.on ? 'true' : 'false'}" aria-label="Monitor on" data-ha="wtoggle"><i></i></button><span class="hca-swl">${v.on ? 'On' : 'Off'}</span></div>
        <p class="hca-wlast">${v.last_at ? `Last check ${esc(ago(v.last_at))}: ${esc(v.last_say || '')} · ${esc(v.checks)} check${v.checks === 1 ? '' : 's'} so far` : 'No check yet.'}${v.live ? '' : ' <b class="hca-warn">Runs after go-live.</b>'}</p></section>
      <form class="hca-card hca-wform" data-haf="watch"><h3>What it watches</h3>
        <label class="hcd-f"><span>Live app address <small>checked from the server, public addresses only</small></span><input id="hcaWUrl" type="url" maxlength="400" value="${esc(v.url || '')}" placeholder="https://shop.example.com" autocomplete="off"></label>
        <label class="hcd-f"><span>Check every</span><select id="hcaWEvery">${every.map(([m, l]) => `<option value="${m}"${+v.every_min === m ? ' selected' : ''}>${l}</option>`).join('')}</select></label>
        <p class="hcd-mut">CI on the main branch of ${esc((v.repos || []).join(', ') || 'no repo yet')} is read every time.</p>
        <fieldset class="hca-fs"><legend>Feeds from your apps <small>up to 5 · read only</small></legend><div id="hcaFeeds">${feedRows(WAPPS)}</div>
          ${WFEEDS.length < 5 ? `<button type="button" class="hcd-btn sm" data-ha="feedadd"${WAPPS.length ? '' : ' disabled'}>${svg('new')}Add a feed</button>` : ''}</fieldset>
        <div class="hca-actions"><button class="hcd-btn pri">Save</button></div></form>
      <section class="hca-card"><h3>Problems${v.open ? ` · <span class="hca-warn">${esc(v.open)} open</span>` : ''}</h3>${alerts.map(arow).join('') || '<p class="hcd-mut">Nothing found yet.</p>'}
        <p class="hcd-mut">A fix starts only on your tap: Hoola Code opens a pull request against your main branch, and you merge it yourself.</p></section>`);
  }
  async function clientLink(pid, on) {
    try {
      const r = await api('POST', `${A}/projects/${enc(pid)}/client-link`, {on});
      if (on && r.url) {
        await dialog(`<h2>Client intake link</h2><p class="hcd-mut">${esc(r.note)}</p><label class="hcd-f"><span>Link</span><input id="hcaLinkUrl" readonly value="${esc(r.url)}"></label>
          <p class="hcd-mut">No login for the client. Works until ${esc(new Date(r.until).toLocaleDateString('en-IN'))}, only for this project. You can stop it any time.</p>
          <div class="hcd-dlgb"><button type="button" class="hcd-btn" data-hacopy="1">Copy link</button><button class="hcd-btn pri" value="ok">Done</button></div>`);
      } else toast('The client link is stopped.');
      draw(ROUTE, BODY);
    } catch (e) { toast(e.message, true); }
  }
  document.addEventListener('click', ev => { const b = ev.target.closest && ev.target.closest('[data-hacopy]'); if (!b) return;
    const i = document.getElementById('hcaLinkUrl'); if (!i) return; i.select(); (navigator.clipboard ? navigator.clipboard.writeText(i.value) : Promise.reject()).then(() => toast('Copied.'), () => { document.execCommand && document.execCommand('copy'); toast('Copied.'); }); });

  // ------------------------------------------------------------------ gates
  async function gateList(pid) {
    const [p, gs] = await Promise.all([api('GET', `${A}/projects/${enc(pid)}`), api('GET', `${A}/projects/${enc(pid)}/gates`)]);
    page(`${head(p, 'gates')}<div class="hcd-table hca-gtable" role="table" aria-label="Gates"><div class="hcd-tr hcd-th" role="row"><span role="columnheader">Gate</span><span role="columnheader">When</span><span role="columnheader">What your tap means</span><span role="columnheader">State</span></div>
      ${gs.map(g => `<button type="button" class="hcd-tr" role="row" data-auto="${esc(pid)}/gate/${esc(g.id)}"><span class="hcd-tcell"><b>${esc(g.code)} · ${esc(g.name)}${g.code === 'G4' && g.n ? ` · sprint ${g.n}` : g.code === 'G5' && g.n ? ` · CR-${String(g.n).padStart(2, '0')}` : ''}</b></span>
        <span class="hcd-tcell">${esc(g.when)}</span><span class="hcd-tcell"><small>${esc(g.means)}</small></span><span class="hcd-tcell">${gstate(g)}</span></button>`).join('')}</div>`);
  }
  const gstate = g => g.state === 'now' ? '<span class="hcd-c warn">Waits for you</span>' : g.state === 'approved' ? '<span class="hcd-c ok">Approved</span>' : g.state === 'changes' ? '<span class="hcd-c soft">Changes asked</span>' : '<span class="hcd-c soft">Later</span>';
  const ul = xs => xs && xs.length ? `<ul class="hca-list">${xs.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
  const prl = x => x.pr ? (x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">PR #${esc(x.pr)}</a>` : `PR #${esc(x.pr)}`) : '';
  function gateBody(g, p) {
    const b = g.body || {};
    const stat = (v, k) => `<span class="hca-stat"><b>${esc(v)}</b><small>${esc(k)}</small></span>`;
    const team = t => t && t.length ? `<div class="hca-team">${t.map(a => `<span class="hca-trow"><i class="hca-g ${esc(a.group)}" aria-hidden="true"></i><span>${esc(a.label)}</span><em>${a.session ? `${a.tasks} task${a.tasks === 1 ? '' : 's'}` : 'planning'}</em></span>`).join('')}</div>` : '';
    switch (g.code) {
      case 'G1': return `<h2 class="hca-gt">${esc(b.title || p.name)}</h2>${b.summary ? `<p class="hca-prose">${esc(b.summary)}</p>` : ''}
        <h3>What will be built</h3><ol class="hca-list">${(b.scope || []).map(s => `<li>${esc(s.title)} <small>· ${esc(s.stories)} stories</small></li>`).join('')}</ol>
        ${b.out && b.out.length ? `<p class="hcd-mut"><b>Not in this project:</b> ${esc(b.out.join(', '))}</p>` : ''}${b.done_when ? `<p class="hcd-mut"><b>Done when:</b> ${esc(b.done_when)}</p>` : ''}
        ${b.assumptions && b.assumptions.length ? `<h3>Assumptions to check</h3>${ul(b.assumptions)}` : ''}
        <div class="hca-stats">${stat(b.stories, 'user stories')}${stat(b.tasks, 'tasks')}${stat(`${b.weeks} wk`, `${b.sprints} sprints`)}${stat(rs(b.cap_inr), 'proposed cost cap')}</div>
        <h3>The team</h3>${team(b.team)}<p class="hcd-mut">Estimate ${rs(b.est_inr)}; real spend is counted as it happens.</p>`;
      case 'G2': return `<h2 class="hca-gt">Design</h2>${b.stack ? `<p class="hca-prose">${esc(b.stack)}</p>` : ''}<h3>Architecture</h3>${ul(b.architecture)}
        <h3>Data</h3>${(b.data || []).map(d => `<p><b>${esc(d.name)}</b> <small class="hcd-mut">${esc((d.fields || []).join(', '))}</small></p>`).join('')}
        <h3>API</h3>${(b.api || []).length ? `<pre class="hca-code">${esc((b.api || []).join('\n'))}</pre>` : ''}
        <h3>Screens</h3>${(b.screens || []).map(s => `<p><b>${esc(s.name)}</b> <small class="hcd-mut">for ${esc(s.for)} · ${esc(s.shows)}</small></p>`).join('')}
        <h3>Risks</h3>${(b.risks || []).map(r => `<p><b>${esc(r.risk)}</b><br><small class="hcd-mut">${esc(r.plan)}</small></p>`).join('')}`;
      case 'G3': return `<h2 class="hca-gt">Plan and price</h2><div class="hca-stats">${stat(b.tasks, 'tasks')}${stat(b.sprints, 'sprints')}${stat(`${b.weeks} wk`, 'about')}${stat(rs(b.est_inr), 'estimate')}</div>
        <h3>Per sprint</h3>${(b.per_sprint || []).map(s => `<p>Sprint ${esc(s.sprint)} · ${esc(s.tasks)} tasks</p>`).join('')}<h3>The team</h3>${team(b.team)}
        <form class="hca-inline" data-haf="cap"><label for="hcaCap">Cost cap (Rs)</label><input id="hcaCap" type="number" min="100" step="100" value="${Math.round(p.cap_inr || b.cap_inr || 0)}"><button class="hcd-btn sm">Save cap</button></form>
        <p class="hcd-mut">${esc(b.est_note || '')}</p><p class="hcd-mut"><b>Project branch:</b> <code>${esc(b.branch)}</code> in ${esc((b.repos || []).join(', '))}. ${esc(b.merge_rule || '')}</p>`;
      case 'G4': return `<h2 class="hca-gt">Sprint ${esc(b.sprint)} of ${esc(b.of)} demo</h2><p class="hcd-mut">Everything below joined the project branch <code>${esc(b.branch)}</code> with its proof.</p>
        <div class="hca-done">${(b.done || []).map(x => `<div class="hca-drow">${svg('ok', 'ok')}<span><b>${esc(x.title)}</b><small>${esc(x.role)}${x.pr ? ' · ' : ''}${prl(x)}${x.ci ? ' · ' + esc(x.ci) : ''}${x.added ? ` · <em class="add">+${esc(x.added)}</em> <em class="del">−${esc(x.removed || 0)}</em>` : ''}</small></span></div>`).join('')}</div>`;
      case 'G5': return `<h2 class="hca-gt">Change request ${esc(b.cr)}: ${esc(b.title)}</h2><p class="hca-prose">${esc(b.detail)}</p>
        <div class="hca-stats">${stat(`${b.minutes} min`, 'of agent work')}${stat(rs(b.cost_inr), 'model use')}${stat(b.tests, 'tests')}${stat(b.role, 'asked of')}</div><p class="hcd-mut">${esc(b.says || '')}</p>`;
      case 'G6': return `<h2 class="hca-gt">Your UAT</h2><p class="hca-prose">${esc(b.says || '')}</p><p class="hcd-mut">${esc(b.tasks_done)} tasks done on <code>${esc(b.branch)}</code>.</p>
        <div class="hca-done">${(b.proof || []).map(x => `<div class="hca-drow">${svg('ok', 'ok')}<span><b>${esc(x.title)}</b><small>${prl(x)}${x.ci ? ' · ' + esc(x.ci) : ''}</small></span></div>`).join('')}</div>`;
      case 'G7': return `<h2 class="hca-gt">Go-live</h2><p class="hca-prose">${esc(b.says || '')}</p>
        ${(g.golive || []).length ? `<div class="hca-done">${g.golive.map(x => `<div class="hca-drow">${svg(x.state === 'merged' ? 'ok' : 'pr', x.state === 'merged' ? 'ok' : '')}<span><b>${esc(x.repo)} → ${esc(x.base)}</b>
          <small>${prl(x)}${x.ci ? ' · ' + esc(x.ci) : ''}${x.error ? ' · ' + esc(x.error) : ''}</small></span>${x.state === 'open' && x.sha ? `<button type="button" class="hcd-btn sm pri" data-ha="merge" data-i="${esc(x.index)}" data-sha="${esc(x.sha)}" data-ci="${esc(x.ci || '')}" data-repo="${esc(x.repo)}">Merge into ${esc(x.base)}</button>` : x.state === 'merged' ? '<span class="hcd-c ok">Merged</span>' : ''}</div>`).join('')}</div>` : ''}`;
      case 'G8': return `<h2 class="hca-gt">Handover</h2><div class="hca-done">${(b.docs || []).map(x => `<div class="hca-drow">${svg('ok', 'ok')}<span><b>${esc(x.title)}</b><small>${prl(x)}</small></span></div>`).join('')}</div>
        ${(b.golive || []).map(x => `<p class="hcd-mut">${esc(x.repo)}: ${prl(x)} · ${esc(x.state)}</p>`).join('')}`;
    }
    return `<pre class="hca-code">${esc(JSON.stringify(b, null, 2))}</pre>`;
  }
  async function gate(pid, gid) {
    const [p, g, gs] = await Promise.all([api('GET', `${A}/projects/${enc(pid)}`), api('GET', `${A}/projects/${enc(pid)}/gates/${enc(gid)}`), api('GET', `${A}/projects/${enc(pid)}/gates`)]);
    const title = g.code === 'G1' ? 'Review and start' : `${g.code} · ${g.name}`;
    const badge = g.state === 'now' ? `<span class="hcd-badge warn">${g.code === 'G1' ? 'Plan' : 'Gate'} · waits for you</span>` : `<span class="hcd-badge">${esc(g.state === 'approved' ? 'Approved' : g.state === 'changes' ? 'Changes asked' : 'Later')}</span>`;
    const side = `<section class="hca-card"><h3>Your 8 gates</h3>${GATES.map(([c, n]) => { const mine = gs.filter(x => x.code === c), any = mine.find(x => x.state === 'now') || mine[mine.length - 1];
      const st = !any ? 'wait' : any.state; return `<button type="button" class="hca-glrow${any && any.id === g.id ? ' on' : ''}"${any ? ` data-auto="${esc(pid)}/gate/${esc(any.id)}"` : ' disabled'}>
        <span class="hca-gc ${st === 'now' ? 'warn' : st === 'approved' ? 'ok' : ''}">${c}</span><span>${n}${mine.length > 1 ? ` · ${mine.length}` : ''}</span><em>${st === 'now' ? 'now' : st === 'approved' ? 'done' : ''}</em></button>`; }).join('')}</section>`;
    page(`${head(p, 'gates')}<div class="hca-split2"><section class="hca-card hca-gcard"><div class="hca-gbadge">${badge}<span class="hcd-mut">${esc(g.means)}</span></div>
        ${gateBody(g, p)}
        ${g.state === 'now' ? `<div class="hca-actions"><button type="button" class="hcd-btn pri" data-ha="approve" data-gid="${esc(g.id)}" data-hash="${esc(g.hash)}">${g.code === 'G1' ? 'Approve and start the design' : g.code === 'G3' ? 'Approve and start building' : g.code === 'G7' ? 'Approve go-live: open the pull requests' : 'Approve'}</button>
          <button type="button" class="hcd-btn" data-ha="changes" data-gid="${esc(g.id)}" data-hash="${esc(g.hash)}">Ask for changes</button></div>
          <p class="hcd-mut">Your tap is the approval. What you see here is exactly what it approves.</p>` : g.note ? `<p class="hcd-mut">Your note: ${esc(g.note)}</p>` : ''}</section>${side}</div>`);
  }

  // ------------------------------------------------------------------ mission control
  async function mission(pid, again = false) {
    const [m, p] = await Promise.all([api('GET', `${A}/projects/${enc(pid)}/mission`), api('GET', `${A}/projects/${enc(pid)}`)]);
    const sig = JSON.stringify([m, p.golive, FILTER]);
    if (again && sig === MSIG) return; MSIG = sig;
    const pr = m.project, ag = m.agents || [];
    const keep = a => FILTER === 'all' || (FILTER === 'working' ? ['working', 'queued'].includes(a.state) : FILTER === 'needs' ? a.state === 'needs' : FILTER === 'done' ? a.state === 'done' : true);
    const n = k => ag.filter(a => k === 'working' ? ['working', 'queued'].includes(a.state) : a.state === k).length;
    const tab = (k, name, c) => `<button type="button" role="tab" aria-selected="${FILTER === k}" data-ha="filter" data-f="${k}">${name} · ${c}</button>`;
    const gateNow = (m.needs || []).find(x => x.kind === 'gate');
    const right = `<div class="hca-hbtns">${pr.paused ? `<button type="button" class="hcd-btn pri" data-ha="pause" data-on="0">Resume</button>` : `<button type="button" class="hcd-btn" data-ha="pause" data-on="1">Pause all</button>`}</div>`;
    const need = x => x.kind === 'gate' ? `<div class="hca-needc"><span class="hcd-badge warn">Needs your OK</span><span>${esc(x.text)}</span><button type="button" class="hcd-btn pri sm" data-auto="${esc(pid)}/gate/${esc(x.id)}">Open</button></div>`
      : x.kind === 'task' ? `<div class="hca-needc"><span class="hcd-badge warn">Needs you</span><span>${esc(x.text)}</span><button type="button" class="hcd-btn sm" data-auto="${esc(pid)}/${x.role === 'monitor' ? 'monitor' : 'agent/' + esc(x.role)}">Open agent</button></div>`
      : `<div class="hca-needc"><span class="hcd-badge">Paused</span><span>${esc(x.text)}</span><button type="button" class="hcd-btn pri sm" data-ha="pause" data-on="0">Resume</button></div>`;
    const tasks = pr.tasks || {};
    const gl = (p.golive || []).filter(x => x.pr);
    page(`${head(pr, 'mission', right)}
      <div class="hca-meta"><span><b>${tasks.done || 0} of ${tasks.total || 0}</b> tasks done with proof</span>${m.day ? `<span>Day <b>${m.day}</b>${m.weeks ? ` of ${m.weeks * 7}` : ''}</span>` : ''}
        <span><b>${rs(pr.spent_inr)}</b> of ${rs(pr.cap_inr)}</span>${pr.gate ? `<span>Next: <b>${esc(pr.gate)}</b></span>` : ''}${m.branch ? `<span><code>${esc(m.branch)}</code></span>` : ''}</div>
      <div class="hca-whole"><span class="hca-pl"><span>Whole project</span><em>${pct(pr.pct)}%</em></span>${bar(pr.pct)}</div>
      <ol class="hca-phases">${(m.phases || []).map(ph => `<li class="${ph.done ? 'done' : ph.now ? 'now' : ''}"><span class="hca-bar sm ${ph.done ? 'ok' : ''}"><i style="width:${pct(ph.pct)}%"></i></span><span>${ph.done ? svg('ok', 'ok') : ''}${esc(ph.label)}</span></li>`).join('')}</ol>
      ${(m.needs || []).map(need).join('')}
      ${gl.length ? `<div class="hca-needc"><span class="hcd-badge info">Go-live</span><span>${gl.map(x => `${esc(x.repo)} ${prl(x)} · ${esc(x.state)}`).join(' · ')}</span>${gateNow ? '' : ''}</div>` : ''}
      <div class="hca-split2 hca-msplit"><div>
        <div class="hcd-tabs" role="tablist">${tab('all', 'All', ag.length)}${tab('working', 'Working', n('working'))}${tab('needs', 'Needs you', n('needs'))}${tab('done', 'Done', n('done'))}</div>
        <div class="hcd-table hca-atable" role="table" aria-label="Agents"><div class="hcd-tr hcd-th" role="row"><span role="columnheader">Agent · working on</span><span role="columnheader">Its tasks</span><span role="columnheader">Share</span><span role="columnheader">State</span><span role="columnheader">Time</span></div>
          ${ag.filter(keep).map(a => `<button type="button" class="hcd-tr" role="row" data-auto="${esc(pid)}/${a.role === 'monitor' ? 'monitor' : 'agent/' + esc(a.role)}">
            <span class="hcd-tcell hca-aname"><b>${esc(a.label)}</b><small>${esc(a.step || '')}</small></span>
            <span class="hcd-tcell">${a.session ? `<span class="hca-pl"><span>${a.done} of ${a.tasks}</span><em>${pct(a.pct)}%</em></span>${bar(a.pct, a.state === 'done' ? 'ok' : a.state === 'needs' ? 'warn' : '')}` : '<span class="hcd-mut">planning</span>'}</span>
            <span class="hcd-tcell hca-mono">${a.role === 'reviewer' ? 'every change' : a.share !== '' && a.share != null ? esc(a.share) + '%' : ''}</span>
            <span class="hcd-tcell"><span class="hca-st ${DOT[a.state] || ''}"><i class="hcd-dot ${DOT[a.state] || ''}"></i>${esc(STATE[a.state] || a.state)}</span></span>
            <span class="hcd-tcell hca-mono">${a.since && ['working', 'queued'].includes(a.state) ? esc(clock(a.since)) : a.state === 'done' ? 'idle' : '—'}</span></button>`).join('') || '<p class="hcd-mut hca-pad">No agents here.</p>'}</div>
        <p class="hcd-mut">Open any agent to see its session and talk to it. Share = its tasks out of all tasks; the Reviewer checks every change. This server runs ${esc(m.live_limit)} Hoola Code sessions at a time and this project uses up to ${esc(m.parallel)}; the rest wait their turn.</p></div>
        <aside class="hca-card hca-feed" aria-label="Live feed"><h3><i class="hcd-dot run" aria-hidden="true"></i>Live feed</h3>
          ${(m.feed || []).map(e => `<div class="hca-ev"><span class="hca-evi">${e.kind === 'done' ? svg('ok', 'ok') : e.kind === 'need' ? svg('warn', 'warnc') : '<i class="hcd-dot run"></i>'}</span>
            <span><span class="hca-evt"><b>${esc(e.who)}</b> ${esc(e.text)}</span><small>${esc(hhmm(e.at))}</small></span></div>`).join('') || '<p class="hcd-mut">Nothing yet.</p>'}</aside></div>`, '', again);
    const live = ['build', 'uat', 'golive', 'handover'].includes(pr.phase);
    if (!TIMER) poll(() => { if (!BUSY) mission(pid, true).catch(() => {}); }, live ? 5000 : 15000);
  }

  // ------------------------------------------------------------------ one agent
  let AG_SIG = '', AG = null;        // AG = the agent chat's thread (chatkit.js): what was handed to it, her message on its way
  function agentExtra(c) {           // what rides under a reply: its tag, a priced change that waits for her
    return `${c.tag ? `<span class="hcd-badge gh">${svg('ok')}${esc(c.tag)}</span>` : ''}
      ${c.change ? `<div class="hca-card hca-cr"><span class="hcd-badge ${c.change.state === 'wait' ? 'warn' : c.change.state === 'approved' ? 'gh' : ''}">${c.change.state === 'wait' ? 'Needs your OK' : c.change.state === 'approved' ? 'Approved' : 'Not now'}</span>
          <b>${esc(c.change.cr)} · ${esc(c.change.title)}</b><small>About ${esc(c.change.minutes)} min of work · ${rs(c.change.cost_inr)} of model use · not in the approved stories</small>
          ${c.change.state === 'wait' && c.change.hash ? `<div class="hca-choices"><button type="button" class="hcd-btn pri sm" data-ha="cr" data-yes="1" data-gid="${esc(c.change.gate)}" data-hash="${esc(c.change.hash)}">Approve change</button>
            <button type="button" class="hcd-btn sm" data-ha="cr" data-yes="0" data-gid="${esc(c.change.gate)}" data-hash="${esc(c.change.hash)}">Not now</button></div>` : ''}</div>` : ''}`;
  }
  function agentSync(st) {
    const a = AG, fresh = st.messages.slice(a.n);
    // her message from elsewhere while the working row is up: the row closes first, so her words are not left above it
    if (a.t.busy && fresh.some(m => m.role === 'her' && m.text.trim() !== a.mine)) a.t.end();
    if (!a.t.busy) a.o.startedAt = a.sending ? a.sending.at : (st.since || 0);
    a.t.sync(st); a.st = st; a.n = st.messages.length;
  }
  function agentPlace(id, x, landed) {   // the tag / change card sits in its reply's own block, under the words
    const a = AG; if (!a || x.node.isConnected) return;
    const ho = [...a.root.children].find(n => n.classList.contains('hck-ho') && n.dataset.id === id) || (landed ? lastTurn(a.root) : null); if (!ho) return;
    ho.insertBefore(x.node, [...ho.children].find(n => n.classList.contains('hck-work') || n.classList.contains('hck-acts')) || null);
  }
  function agentThread(v) {          // the chat: only what is new is added - a new reply lands, nothing is drawn twice
    const a = AG, ag = v.agent || {}, ss = v.session || {}, first = !a.st, landed = [];
    for (const c of v.chat || []) {
      const id = `${c.at}|${c.who}|${String(c.text || '').length}`;
      if (!a.seen.has(id)) { a.seen.add(id); a.list.push({id, role: c.who === 'you' ? 'her' : 'hoola', text: String(c.text || '')}); if (!first) landed.push(id); }
      if (c.who !== 'you' && (c.tag || c.change)) {
        let x = a.x.get(id); if (!x) { x = {node: document.createElement('div'), sig: ''}; x.node.className = 'hca-x'; a.x.set(id, x); }
        const h = agentExtra(c); if (h !== x.sig) { x.sig = h; x.node.innerHTML = h; }
      }
    }
    const hint = document.getElementById('hcaHint'); if (hint) hint.hidden = !!(a.list.length || a.sending);
    agentSync({key: a.key, messages: a.list.slice(), working: !!(a.sending || ss.running || ss.now), label: a.sending ? 'Thinking…' : (ss.now || 'Working…'),
      since: ['working', 'queued'].includes(ag.state) ? Date.parse(ag.since || '') || 0 : 0});
    Promise.resolve().then(() => { if (AG === a) for (const [id, x] of a.x) agentPlace(id, x, landed.includes(id)); });   // after the kit has opened the reply's block
  }
  async function agentSend(pid, role, text) {
    const a = AG; if (!a || BUSY) { if (a) a.bar.value = text; return; }
    await busy(null, '', async () => {
      if (a.t.busy) a.t.end();                                             // her words go under what is there, the working row under her words
      a.sending = {text, at: Date.now()}; a.mine = text.trim();
      const me = a.t.her(text, {pending: true});                            // shown the moment she sends
      agentSync({...a.st, working: true, label: 'Thinking…'});
      const hint = document.getElementById('hcaHint'); if (hint) hint.hidden = true;
      try { const r = await api('POST', `${A}/projects/${enc(pid)}/agents/${enc(role)}/message`, {text}); if (r && r.warn) toast(r.warn, true); }
      catch (e) { a.sending = null; a.mine = '';
        if (AG === a) { a.t.end(); me.remove(); if (!a.bar.value) a.bar.value = text; }
        throw e; }
      a.sending = null;
      if (AG === a && ROUTE === `${pid}/agent/${role}`) { AG_SIG = ''; await agent(pid, role); }
    });
  }
  async function agent(pid, role) {
    const v = await api('GET', `${A}/projects/${enc(pid)}/agents/${enc(role)}`);
    const a = v.agent || {}, ss = v.session || {};
    if (!document.getElementById('hcaAgent') || BODY.dataset.agent !== `${pid}/${role}` || !AG || !AG.root.isConnected) {
      AG_SIG = ''; if (AG) { const old = AG; AG = null; old.t.clear(); }
      BODY.dataset.agent = `${pid}/${role}`;
      document.title = `${a.label || role} · ${v.project.name}`;
      BODY.innerHTML = `<div class="hca-agent" id="hcaAgent"><div class="hca-amain">
          <header class="hca-atop"><button type="button" class="hcd-link" data-auto="${esc(pid)}/mission">${esc(v.project.name)}</button><span class="hcd-mut">/</span><b>${esc(a.label || role)}</b><span class="hcd-flex"></span>
            <button type="button" class="hcd-btn sm" data-auto="${esc(pid)}/mission">All agents</button></header>
          <div class="hca-acol"><div class="hca-scroll" id="hcaScroll"><p class="hcd-mut" id="hcaHint">${esc(v.does)} Say what it should know; it reads it before its next step.</p>
              <div id="hcaChat"></div><div id="hcaSess"></div></div>
            <div id="hcaBar"></div>
            <p class="hcd-mut hca-cnote">It reads your message before its next step. Something outside the approved stories becomes a priced change request.</p></div></div>
        <aside class="hca-arail" id="hcaRail"></aside></div>`;
      const root = document.getElementById('hcaChat'), o = {jump: true, scroller: document.getElementById('hcaScroll'), startedAt: 0};
      AG = {root, o, t: window.HoolaChat.mount(root, o), key: `${pid}/${role}`, list: [], seen: new Set(), x: new Map(), n: 0, st: null, sending: null, mine: ''};
      AG.bar = boxOf(document.getElementById('hcaBar'), {placeholder: `Message ${a.label || role}, or tell it what to change`, onSend: text => agentSend(pid, role, text.slice(0, 4000))});
      AG.bar.input.maxLength = 4000;
    }
    agentThread(v);
    const sig = JSON.stringify([ss.id, ss.steps && ss.steps.length, ss.status, ss.question, ss.error, ss.files, v.current, v.tasks, a]);
    if (sig === AG_SIG) return pollAgent(pid, role);
    AG_SIG = sig;
    let steps = '';
    if (ss.id) {
      const rows = (ss.steps || []).map((s, i) => { try { return step(s, (ss.steps[0] || {}).at, i); } catch (e) { return s.text ? `<div class="hcd-step">${esc(s.text)}</div>` : ''; } }).join('');
      steps = `<section class="hca-card hca-sess"><div class="hca-sh"><b>${v.current ? `Task ${esc(v.current.seq)}: ${esc(v.current.title)}` : 'Its session'}</b><a class="hcd-link" href="#/s/${esc(ss.id)}">Open full session</a></div>
        ${rows || '<p class="hcd-mut">Starting…</p>'}
        ${ss.question ? `<p class="hca-ask2">${esc(ss.question)} <a class="hcd-link" href="#/s/${esc(ss.id)}">Answer in the session</a></p>` : ''}
        ${ss.error ? `<p class="hcd-err">${esc(ss.error)}</p>` : ''}</section>`;
    } else if (v.current && v.current.why) steps = `<section class="hca-card"><span class="hcd-badge warn">Needs you</span><p>${esc(v.current.why)}</p></section>`;
    document.getElementById('hcaSess').innerHTML = steps;                 // its session's last steps, under the chat
    const tstate = t => t.state === 'done' ? svg('ok', 'ok') : ['working', 'queued'].includes(t.state) ? '<i class="hcd-dot run"></i>' : t.state === 'needs' ? svg('warn', 'warnc') : '<i class="hca-ringo"></i>';
    const files = ss.files || [];
    document.getElementById('hcaRail').innerHTML = `
      <section><small>Agent</small><p class="hca-rl"><i class="hcd-dot ${DOT[a.state] || ''}"></i><b>${esc(a.label || role)}</b><span class="hcd-flex"></span><span class="hca-st ${DOT[a.state] || ''}">${esc(STATE[a.state] || a.state || '')}</span></p>
        <p class="hcd-mut">${esc(v.does)}${ss.model ? ` · ${esc(ss.model)}` : ''}</p></section>
      <section><small>Environment</small><p class="hca-mono">${esc(v.repo || '')}</p><p class="hca-mono">${esc(v.branch || 'the project branch is made at G3')}</p></section>
      ${v.kind ? `<section><small>My tasks</small><p class="hca-pl"><span><b>${a.done || 0} of ${a.tasks || 0}</b></span><em>${pct(a.pct)}%</em></p>${bar(a.pct)}
        <div class="hca-tl">${(v.tasks || []).map(t => `<div class="hca-tr2 ${t.state}">${tstate(t)}<span>${esc(t.seq)}. ${esc(t.title)}${t.sprint ? ` <small>S${esc(t.sprint)}</small>` : ''}</span>
          ${t.state === 'needs' ? `<span class="hca-tact"><button type="button" class="hcd-btn sm" data-ha="task" data-what="retry" data-tid="${esc(t.id)}">Retry</button><button type="button" class="hcd-btn sm" data-ha="task" data-what="skip" data-tid="${esc(t.id)}">Skip</button></span>` : ''}</div>
          ${t.state === 'needs' && t.why ? `<p class="hcd-err hca-why">${esc(t.why)}</p>` : ''}`).join('') || '<p class="hcd-mut">No tasks yet.</p>'}</div></section>
      <section class="hca-kvr"><small>Share of project</small><b class="hca-mono">${a.share !== '' && a.share != null ? esc(a.share) + '%' : '—'}</b></section>` : ''}
      ${files.length ? `<section><small>Changes</small>${files.slice(0, 8).map(f => `<p class="hca-mono">${esc(f.path)} <em class="add">+${esc(f.added || 0)}</em> <em class="del">−${esc(f.removed || 0)}</em></p>`).join('')}${ss.pr_url ? `<a class="hcd-link" href="${esc(ss.pr_url)}" target="_blank" rel="noopener">Pull request #${esc(ss.pr_number)}</a>` : ''}</section>` : ''}
      <section><small>Proof so far</small><p>${esc(v.proof?.done || 0)} tasks done · ${esc(v.proof?.prs || 0)} pull requests joined the branch${v.proof?.added ? ` · +${esc(v.proof.added)} lines` : ''}</p></section>
      <section class="hca-kvr"><small>Cost</small><b class="hca-mono">${rs(a.cost_inr || 0)}</b></section>`;
    pollAgent(pid, role);
  }
  function pollAgent(pid, role) { if (!TIMER) poll(() => { if (!BUSY) agent(pid, role).catch(() => {}); }, 4000); }

  // ------------------------------------------------------------------ actions
  const pidOf = () => ROUTE.split('/')[0];
  async function busy(btn, label, fn) {
    if (BUSY) return; BUSY = true; const old = btn ? btn.innerHTML : ''; if (btn) { btn.disabled = true; btn.innerHTML = `<span class="hca-ring" aria-hidden="true"></span>${esc(label)}`; }
    try { await fn(); } catch (e) { toast(e.message, true); } finally { BUSY = false; if (btn && btn.isConnected) { btn.disabled = false; btn.innerHTML = old; } }
  }
  const ACT = {
    hometab: b => { HOMETAB = b.dataset.tab; home().catch(fail); },
    newproj: () => newProject(),
    parch: b => busy(null, '', async () => { await api('POST', `${A}/projects/${enc(b.dataset.id)}/archive`, {on: b.dataset.on === '1'}); await refresh(); await home(); }),
    sec: b => { SEC = +b.dataset.i || 0; draw(ROUTE, BODY); },
    confirm: b => busy(null, '', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/intake/${enc(b.dataset.key)}/confirm`, {pick: b.dataset.pick || 'a'}); await draw(ROUTE, BODY); }),
    choose: b => busy(b, 'Saving', async () => { await api('PUT', `${A}/projects/${enc(pidOf())}/intake/${enc(b.dataset.key)}`, {value: b.dataset.val}); await draw(ROUTE, BODY); }),
    addsrc: () => addSource(pidOf()),
    link: b => clientLink(pidOf(), b.dataset.on === '1'),
    review: b => busy(b, 'Writing the plan… this can take a minute', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/review`, {}); toast('The plan is ready for your review.'); await refresh(); go(pidOf()); }),
    srcfilter: b => { FILTER = b.dataset.f; sources(pidOf()).catch(fail); },
    filter: b => { FILTER = b.dataset.f; mission(pidOf(), true).catch(fail); },
    pause: b => busy(b, '', async () => { await api('PATCH', `${A}/projects/${enc(pidOf())}`, {paused: b.dataset.on === '1'}); await refresh(); await mission(pidOf(), true); }),
    pickenv: async b => {
      let envs = {envs: []}; try { envs = await api('GET', '/api/devsahayak/envs'); } catch (e) { /* the dialog still opens */ }
      const r = await dialog(`<h2>Environment</h2><label class="hcd-f"><span>The sessions of this project run in</span><select id="hcaEnvPick"><option value="">Each repo's own settings</option>
        ${(envs.envs || []).map(e => `<option value="${esc(e.id)}"${e.id === b.dataset.cur ? ' selected' : ''}>${esc(e.name)}</option>`).join('')}</select></label>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Save</button></div>`);
      const v = document.querySelector('#hcdDlg #hcaEnvPick')?.value;
      if (r !== 'ok') return;
      try { await api('PATCH', `${A}/projects/${enc(pidOf())}`, {env_id: v || ''}); draw(ROUTE, BODY); } catch (e) { toast(e.message, true); }
    },
    approve: b => busy(b, 'Approving…', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/gates/${enc(b.dataset.gid)}/decide`, {yes: true, hash: b.dataset.hash}); toast('Approved.'); await refresh(); go(pidOf()); }),
    changes: async b => {
      const r = await dialog(`<h2>Ask for changes</h2><label class="hcd-f"><span>What should change?</span><textarea id="hcaNote" rows="5" maxlength="3000" required></textarea></label>
        <p class="hcd-mut">This step runs again with your words.</p><div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Send</button></div>`);
      const note = document.querySelector('#hcdDlg #hcaNote')?.value || '';
      if (r !== 'ok' || !note.trim()) return;
      busy(b, 'Working on your changes…', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/gates/${enc(b.dataset.gid)}/decide`, {yes: false, hash: b.dataset.hash, note}); toast('Sent.'); go(pidOf()); });
    },
    merge: async b => {
      const red = /fail|running|chal/i.test(b.dataset.ci || '');
      const r = await dialog(`<h2>Merge into your main branch?</h2><p>${esc(b.dataset.repo)} · ${esc(b.dataset.ci || '')}</p><p class="hcd-mut">This changes your main branch. The pull request must still be at <code>${esc(b.dataset.sha)}</code>.</p>
        ${red ? '<label class="hcd-f"><span>CI is not green. Why merge anyway? <small>8 letters or more</small></span><textarea id="hcaWhy" rows="3"></textarea></label>' : ''}
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Merge</button></div>`);
      const why = document.querySelector('#hcdDlg #hcaWhy')?.value || '';
      if (r !== 'ok') return;
      busy(b, 'Merging…', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/golive/${enc(b.dataset.i)}/merge`, {sha: b.dataset.sha, reason: why}); toast('Merged.'); await draw(ROUTE, BODY); });
    },
    cr: b => busy(b, '', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/gates/${enc(b.dataset.gid)}/decide`, {yes: b.dataset.yes === '1', hash: b.dataset.hash});
      AG_SIG = ''; await draw(ROUTE, BODY); }),
    task: b => busy(b, '', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/tasks/${enc(b.dataset.tid)}/${b.dataset.what}`); AG_SIG = ''; await draw(ROUTE, BODY); }),
    // v0.949 talk, the Monitor
    talkpick: b => { if (!BUSY) busy(null, '', () => talkSend(b.dataset.val, false)); },
    appsign: async b => {
      keepFeeds();
      if (b.dataset.state !== 'needs_link') { await dialog(`<h2>${esc(b.dataset.name)}</h2><p class="hca-prose">${esc(b.dataset.say || '')}</p><div class="hcd-dlgb"><button class="hcd-btn pri" value="ok">OK</button></div>`); return; }
      let again = false; try { again = await signIn(b.dataset.key, b.dataset.name); } catch (e) { toast(e.message, true); }
      if (again) monitor(pidOf(), true).catch(fail);
    },
    feedadd: () => { keepFeeds(); if (WFEEDS.length < 5) { const first = WAPPS.find(a => a.state === 'ready') || WAPPS[0]; WFEEDS.push({app: first ? first.key : '', what: ''}); }
      const box = document.getElementById('hcaFeeds'); if (box) monitor(pidOf(), true).catch(fail); },
    feeddel: b => { keepFeeds(); WFEEDS.splice(+b.dataset.i, 1); monitor(pidOf(), true).catch(fail); },
    wtoggle: b => { const f = BODY.querySelector('form[data-haf=watch]'); if (!f) return; const on = b.getAttribute('aria-checked') !== 'true';
      busy(null, '', async () => { await api('PUT', `${A}/projects/${enc(pidOf())}/watch`, watchBody(f, on)); toast(on ? 'The Monitor is on.' : 'The Monitor is off.'); await monitor(pidOf()); }); },
    wcheck: b => busy(b, 'Checking…', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/watch/check`); await monitor(pidOf()); }),
    afix: async b => {
      const r = await dialog(`<h2>Fix this problem?</h2><p class="hca-prose">Hoola Code will open a pull request against your main branch. You merge it yourself.</p>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Start the fix</button></div>`);
      if (r !== 'ok') return;
      busy(b, 'Starting…', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/alerts/${enc(b.dataset.id)}/fix`); toast('The fix started in Hoola Code.'); await monitor(pidOf()); });
    },
    aact: b => busy(b, '', async () => { await api('POST', `${A}/projects/${enc(pidOf())}/alerts/${enc(b.dataset.id)}/${b.dataset.what}`); await monitor(pidOf()); }),
  };
  const SUB = {
    answer: f => { const val = (f.querySelector('[name=v]') || {}).value || ''; busy(f.querySelector('button'), 'Saving', async () => {
      const r = await api('PUT', `${A}/projects/${enc(pidOf())}/intake/${enc(f.dataset.key)}`, {value: val}); if (r && r.warn) toast(r.warn, true); await draw(ROUTE, BODY); }); },
    repos: f => { const v = f.querySelector('input').value.split(/[\s,]+/).filter(Boolean); busy(f.querySelector('button'), 'Saving', async () => { await api('PATCH', `${A}/projects/${enc(pidOf())}`, {repos: v}); await draw(ROUTE, BODY); }); },
    cap: f => { const v = +f.querySelector('input').value; busy(f.querySelector('button'), 'Saving', async () => { await api('PATCH', `${A}/projects/${enc(pidOf())}`, {cap_inr: v}); toast('Cost cap saved.'); await draw(ROUTE, BODY); }); },
    watch: f => { const on = (BODY.querySelector('[data-ha=wtoggle]') || {}).getAttribute?.('aria-checked') === 'true';
      busy(f.querySelector('button.pri'), 'Saving', async () => { const v = await api('PUT', `${A}/projects/${enc(pidOf())}/watch`, watchBody(f, on)); WFEEDS = null; toast('Saved.'); await monitor(pidOf()); }); },
  };
  return {draw, leave, refresh, cached};
};
