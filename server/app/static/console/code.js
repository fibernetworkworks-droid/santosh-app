/* HOOLA CODE - Developer Sahayak as a console page.
   v0.748 the first page. v0.768 PHASE 1 of docs/HOOLA_CODE_WEB_PLAN.md: the shell and the session laid out like Claude
   Code on the web - three zones (sessions sidebar / chat / a right rail of status cards), steps folded into summaries
   (Normal / Verbose view), a queued note she can take back, rename / archive / delete, an All sessions page.

   THE RULE OF THIS FILE: a refresh never rebuilds what she is typing in. The session is mounted ONCE (title bar, feed,
   queue, bar, the message box, rail) and every 2 s only the regions whose content changed are repainted (paint()).
   The message box is never repainted. Clicks are handled by ONE listener on the root (data-act / data-go / data-tid /
   data-fold / data-menu), so repainted regions need no re-wiring.

   Nothing reaches GitHub from this page except through the existing tap routes (push / plan-ok / post / decide). */
window.HoolaCode = function ({api, esc, toast, standalone = false}) {
  let EL = null, VIEW = 'home', TID = '', OV = null, TASK = null, POLL = 0, KIND = 'fix', REPO = '', MERGE = null;
  let Q = '', ALL = {tab: 'active', q: '', rows: null}, SIG = {}, WIRED = null;
  const OPEN = new Set();                 // folds she opened (kept across repaints)
  const $ = s => EL && EL.querySelector(s);
  const P = (() => { let p = {}; try { p = JSON.parse(localStorage.getItem('hoola.code.ui') || '{}') || {}; } catch (e) { /* private window */ }
    return {side: p.side === 'min' ? 'min' : 'open', rail: ['on', 'off'].includes(p.rail) ? p.rail : 'auto',
      group: ['status', 'none'].includes(p.group) ? p.group : 'repo', show: ['run', 'need'].includes(p.show) ? p.show : 'all',
      view: p.view === 'verbose' ? 'verbose' : 'normal'}; })();
  const keep = () => { try { localStorage.setItem('hoola.code.ui', JSON.stringify(P)); } catch (e) { /* fine without it */ } };

  const KINDS = [['fix', 'Fix a bug'], ['write', 'Build a feature'], ['tests', 'Write tests'], ['docs', 'Write docs'], ['explain', 'Explain code']];
  const STATUS = {new: 'Starting', plan_wait: 'Plan waits for your OK', ready: 'Ready - open the PR?', pr_open: 'PR open', ci_running: 'CI running',
    checks_failed: 'CI failed', merged: 'Merged', closed: 'PR closed', explained: 'Explained', refused: 'Stopped by a safety rule',
    failed: 'Could not finish', cancelled: 'Stopped'};
  const NEEDS = new Set(['plan_wait', 'ready', 'checks_failed', 'refused']);
  const CAN_REVISE = new Set(['pr_open', 'checks_failed', 'ready', 'refused']);
  const ICON = {
    read: '<path d="M6 3h9l4 4v14H6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    search: '<circle cx="11" cy="11" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16 16l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    edit: '<path d="M4 20l4-1 11-11-3-3L5 16z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    new: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    list: '<path d="M4 6h16M4 12h10M4 18h7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    ok: '<path d="M5 12l5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>',
    bad: '<path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
    dot: '<circle cx="12" cy="12" r="3" fill="currentColor"/>',
    chev: '<path d="M9 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    down: '<path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    more: '<circle cx="5" cy="12" r="1.6" fill="currentColor"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/><circle cx="19" cy="12" r="1.6" fill="currentColor"/>',
    side: '<rect x="3" y="4" width="18" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9 4v16" stroke="currentColor" stroke-width="2"/>',
    rail: '<rect x="3" y="4" width="18" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15 4v16" stroke="currentColor" stroke-width="2"/>',
    sort: '<path d="M7 5v14M7 19l-3-3M7 19l3-3M17 19V5M17 5l-3 3M17 5l3 3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    x: '<path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    up: '<path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>'};
  const svg = (k, cls = '') => `<svg class="hcd-ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[k] || ICON.dot}</svg>`;
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const since = (a, b) => { const s = Math.max(0, Math.round((Date.parse(b || '') - Date.parse(a || '')) / 1000)); return isFinite(s) ? (s < 60 ? `0:${String(s).padStart(2, '0')}` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`) : ''; };
  const dur = s => { s = Math.round(+s || 0); return s < 60 ? `${s} s` : s < 3600 ? `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s` : `${Math.floor(s / 3600)} h ${String(Math.floor(s % 3600 / 60)).padStart(2, '0')} min`; };
  const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;
  const isRun = t => !!t.running;
  const needsYou = t => NEEDS.has(t.status) || (!!t.pr_number && (OV?.actions || []).some(a => a.status === 'waiting' && a.repo === t.repo && a.pr_number === t.pr_number));
  const group = t => isRun(t) ? 'run' : needsYou(t) ? 'need' : 'old';
  const dotc = t => ({run: 'run', need: 'warn'}[group(t)] || (t.status === 'merged' ? 'ok' : t.status === 'failed' ? 'bad' : 'soft'));
  const stat = t => { let a = 0, r = 0; (t.files || []).forEach(f => { a += f.added || 0; r += f.removed || 0; }); return (a || r) ? `<em class="add">+${a}</em> <em class="del">−${r}</em>` : ''; };
  const sub = t => isRun(t) ? 'Working' : (STATUS[t.status] || t.status);

  async function load() {
    try { OV = await api('GET', '/api/devsahayak'); } catch (e) { OV = {error: e.message, tasks: [], repos: [], reviews: [], actions: [], settings: {}}; }
    if (!REPO) REPO = OV.settings?.default_repo || OV.repos?.[0]?.repo || '';
  }
  // On its own page (/console/code) every screen has an address: #/s/<id>, #/reviews, #/settings, #/all - so Back works
  // and a link can open one session.
  const fromHash = () => { const m = /^#\/(s|reviews|settings|all)(?:\/(.+))?$/.exec(location.hash || '');
    return !m ? ['home', ''] : m[1] === 's' ? ['session', decodeURIComponent(m[2] || '')] : [m[1], '']; };
  const toHash = (view, tid) => view === 'session' && tid ? '#/s/' + encodeURIComponent(tid) : view === 'home' ? '#/' : '#/' + view;
  async function open(root) { EL = root || EL; if (!EL) return; clearInterval(POLL); await load(); shell();
    if (standalone) { [VIEW, TID] = fromHash(); window.addEventListener('hashchange', () => { const [v, t] = fromHash(); if (v !== VIEW || t !== TID) show(v, t); }); }
    show(VIEW, TID); }
  function leave() { clearInterval(POLL); window.HoolaMenu?.close(); }

  function show(view, tid) {
    VIEW = view; TID = tid || ''; clearInterval(POLL); MERGE = null; SIG = {}; window.HoolaMenu?.close();
    if (standalone && location.hash !== toHash(VIEW, TID) && !(VIEW === 'home' && !location.hash)) location.hash = toHash(VIEW, TID);
    if (standalone) document.title = VIEW === 'session' ? 'Hoola Code' : ({reviews: 'Review a PR', settings: 'Settings', all: 'All sessions'}[VIEW] || 'Hoola Code') + (VIEW === 'home' ? '' : ' · Hoola Code');
    drawSide();
    if (view === 'session' && TID) return session(TID);
    if (view === 'reviews') return reviews();
    if (view === 'settings') return settings();
    if (view === 'all') return allSessions();
    return home();
  }

  // ------------------------------------------------------------------ shell ---
  function shell() {
    if (WIRED === EL && $('.hcd')) return;
    EL.innerHTML = `<div class="hcd" data-side="${P.side}" data-rail="${P.rail}"><nav class="hcd-side" id="hcdSide" aria-label="Coding sessions"></nav>
      <div class="hcd-body" id="hcdBody"></div><dialog class="hcd-dlg" id="hcdDlg"></dialog></div>`;
    WIRED = EL;
    EL.addEventListener('click', onClick);
    EL.addEventListener('submit', onSubmit);
    EL.addEventListener('keydown', onKey);
    if (window.ResizeObserver) new ResizeObserver(() => { const b = $('[data-act="rail"]'); if (!b) return; const on = railShown();   // the window got narrower / wider: the button tells the truth
      b.setAttribute('aria-pressed', String(on)); b.title = `${on ? 'Hide' : 'Show'} session details`; b.setAttribute('aria-label', b.title); }).observe($('#hcdBody'));
    EL.addEventListener('input', ev => { if (ev.target.id === 'hcdSearch') { Q = ev.target.value; drawList(); } if (ev.target.id === 'hcdNote') grow(ev.target); });
  }
  const body = html => { $('#hcdBody').innerHTML = html; };
  const frame = body;                     // the reviews and settings screens draw the whole body

  function drawSide() {
    const side = $('#hcdSide'); if (!side) return;
    $('.hcd').dataset.side = P.side;
    if (P.side === 'min') {
      const ts = (OV?.tasks || []).filter(t => group(t) !== 'old').slice(0, 8);
      side.innerHTML = `<button type="button" class="hcd-icb" data-act="side" aria-label="Open the sessions sidebar" title="Open sidebar">${svg('side')}</button>
        <button type="button" class="hcd-icb line" data-go="home" aria-label="New session" title="New session">${svg('new')}</button>
        ${ts.map(t => `<button type="button" class="hcd-icb" data-tid="${esc(t.id)}" title="${esc(t.title || t.number)}" aria-label="${esc(t.title || t.number)}"><i class="hcd-dot ${dotc(t)}"></i></button>`).join('')}`;
      return;
    }
    side.innerHTML = `<div class="hcd-sh">${standalone ? '<img class="hcd-mark" src="/static/hoola-mark.png" alt="" width="24" height="24">' : ''}<b>Hoola Code</b><span class="hcd-flex"></span><button type="button" class="hcd-icb" data-act="side" aria-label="Collapse the sessions sidebar" title="Collapse sidebar">${svg('side')}</button></div>
      <button type="button" class="hcd-new" data-go="home">${svg('new')}New session</button>
      <button type="button" class="hcd-nav${VIEW === 'reviews' ? ' on' : ''}" data-go="reviews">Review a pull request</button>
      <label class="hcd-sr" for="hcdSearch">Search sessions</label><input id="hcdSearch" class="hcd-search" type="search" placeholder="Search sessions" value="${esc(Q)}" autocomplete="off">
      <div class="hcd-list" id="hcdList"></div>
      <button type="button" class="hcd-nav${VIEW === 'all' ? ' on' : ''}" data-go="all">View all</button>
      <span class="hcd-flex"></span>
      <button type="button" class="hcd-nav${VIEW === 'settings' ? ' on' : ''}" data-go="settings">Settings</button>
      ${standalone ? '<a class="hcd-nav" href="/console/">Back to Hoola</a>' : ''}`;
    drawList();
  }
  const row = t => `<div class="hcd-sess${t.id === TID && VIEW === 'session' ? ' on' : ''}"><button type="button" class="hcd-sessb" data-tid="${esc(t.id)}">
      <span class="hcd-st"><i class="hcd-dot ${dotc(t)}"></i><span>${esc(t.title || t.number)}</span></span>
      <small>${P.group === 'repo' ? '' : esc((t.repo || '').split('/')[1] || '') + ' · '}${esc(sub(t))} · ${esc(ago(t.updated || t.at))}</small></button>
      <span class="hcd-stat">${stat(t)}</span>
      <button type="button" class="hcd-icb hcd-rowm" data-menu="row" data-id="${esc(t.id)}" aria-label="More for ${esc(t.title || t.number)}">${svg('more')}</button></div>`;
  function drawList() {
    const box = $('#hcdList'); if (!box) return;
    const q = Q.trim().toLowerCase();
    let ts = (OV?.tasks || []).filter(t => !q || `${t.title} ${t.repo} ${t.number}`.toLowerCase().includes(q));
    if (P.show !== 'all') ts = ts.filter(t => group(t) === P.show);
    const head = (name, first) => `<div class="hcd-lbl"><span>${esc(name)}</span>${first ? `<button type="button" class="hcd-icb" data-menu="group" aria-label="Group and sort" title="Group and sort">${svg('sort')}</button>` : ''}</div>`;
    let out = '';
    if (!ts.length) out = head('Sessions', true) + `<p class="hcd-mut hcd-none">${q || P.show !== 'all' ? 'No sessions match.' : 'No sessions yet.'}</p>`;
    else if (P.group === 'repo') {
      const by = new Map(); ts.forEach(t => { const k = (t.repo || '').split('/')[1] || t.repo || 'No repo'; (by.get(k) || by.set(k, []).get(k)).push(t); });
      let first = true; by.forEach((list, k) => { out += head(k, first) + list.map(row).join(''); first = false; });
    } else if (P.group === 'status') {
      let first = true; [['run', 'Running'], ['need', 'Needs you'], ['old', 'Earlier']].forEach(([g, name]) => { const list = ts.filter(t => group(t) === g);
        if (list.length) { out += head(name, first) + list.map(row).join(''); first = false; } });
    } else out = head('Sessions', true) + ts.map(row).join('');
    box.innerHTML = out;
  }

  // ------------------------------------------------------------------ dialogs + menus ---
  function dialog(html) {
    const d = $('#hcdDlg'); d.innerHTML = `<form method="dialog">${html}</form>`;
    return new Promise(res => { d.addEventListener('close', () => res(d.returnValue), {once: true}); d.returnValue = ''; d.showModal(); });
  }
  async function askName(t) {
    const r = await dialog(`<h2>Rename session</h2><label class="hcd-sr" for="hcdDlgIn">Session name</label>
      <input id="hcdDlgIn" maxlength="200" value="${esc(t.title || '')}" autocomplete="off">
      <p class="hcd-mut">Only the name in Hoola changes, not the pull request on GitHub.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Rename</button></div>`);
    if (r !== 'ok') return;
    try { await api('PATCH', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}`, {title: $('#hcdDlgIn').value.trim()}); await after(t.id); } catch (e) { toast(e.message, true); }
  }
  async function askDelete(t) {
    const r = await dialog(`<h2>Delete "${esc(t.title || t.number)}"?</h2>
      <p class="hcd-mut">The session and its steps are removed from Hoola for good. Nothing changes on GitHub${t.pr_number ? ` - pull request #${t.pr_number} stays open` : ''}.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Cancel</button><button class="hcd-btn danger" value="ok">Delete</button></div>`);
    if (r !== 'ok') return;
    try { await api('DELETE', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}`); toast('Deleted.'); await load(); ALL.rows = null; show(t.id === TID ? 'home' : VIEW, t.id === TID ? '' : TID); }
    catch (e) { toast(e.message, true); }
  }
  async function setArchived(t, on) {
    try { await api('PATCH', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}`, {archived: on}); toast(on ? 'Archived. Find it under View all.' : 'Back in the list.');
      await load(); ALL.rows = null; show(on && t.id === TID ? 'home' : VIEW, on && t.id === TID ? '' : TID); }
    catch (e) { toast(e.message, true); }
  }
  async function after(tid) { await load(); drawSide(); ALL.rows = null; if (VIEW === 'all') return allSessions(); if (VIEW === 'session' && TID === tid) await refreshTask(tid, true); }
  const findTask = id => (OV?.tasks || []).find(t => t.id === id) || (ALL.rows || []).find(t => t.id === id) || (TASK && TASK.id === id ? TASK : null);
  function taskMenu(btn, t, inSession) {
    if (!window.HoolaMenu || !t) return;
    const items = [{label: 'Rename', icon: 'pencil', run: () => askName(t)}];
    if (inSession) items.push({header: 'Transcript view'},
      {label: 'Normal', sub: 'Steps folded into summaries', checked: P.view === 'normal', run: () => setView('normal')},
      {label: 'Verbose', sub: 'Every step and every diff', checked: P.view === 'verbose', run: () => setView('verbose')});
    if (t.pr_url) items.push({sep: true}, {label: 'Open the PR on GitHub', icon: 'doc', run: () => window.open(t.pr_url, '_blank', 'noopener')});
    items.push({sep: true}, t.archived ? {label: 'Unarchive', icon: 'restore', run: () => setArchived(t, false)} : {label: 'Archive', icon: 'archive', disabled: isRun(t), run: () => setArchived(t, true)},
      {label: 'Delete…', icon: 'trash', danger: true, disabled: isRun(t), run: () => askDelete(t)});
    HoolaMenu.open(btn, items, {align: inSession ? 'start' : 'end', label: 'Session', width: 250});
  }
  function groupMenu(btn) {
    if (!window.HoolaMenu) return;
    const g = v => () => { P.group = v; keep(); drawList(); }, s = v => () => { P.show = v; keep(); drawList(); };
    HoolaMenu.open(btn, [{header: 'Group by'}, {label: 'Repo', checked: P.group === 'repo', run: g('repo')}, {label: 'Status', checked: P.group === 'status', run: g('status')},
      {label: 'None', checked: P.group === 'none', run: g('none')}, {header: 'Show'}, {label: 'All', checked: P.show === 'all', run: s('all')},
      {label: 'Working', checked: P.show === 'run', run: s('run')}, {label: 'Needs you', checked: P.show === 'need', run: s('need')},
      {sep: true}, {label: 'View all and archived', icon: 'archive', run: () => show('all')}], {align: 'end', label: 'Group and sort', width: 220});
  }
  function setView(v) { P.view = v; keep(); SIG.feed = ''; paint(); }

  // ------------------------------------------------------------------ one listener ---
  function onClick(ev) {
    const b = ev.target.closest('[data-act],[data-go],[data-tid],[data-fold],[data-menu],[data-kind]'); if (!b || !EL.contains(b)) return;
    if (b.dataset.menu) { ev.preventDefault();
      if (b.dataset.menu === 'group') return groupMenu(b);
      if (b.dataset.menu === 'title') return taskMenu(b, TASK, true);
      return taskMenu(b, findTask(b.dataset.id), false); }
    if (b.dataset.fold) { const k = b.dataset.fold, on = !OPEN.has(k); on ? OPEN.add(k) : OPEN.delete(k);
      b.setAttribute('aria-expanded', String(on)); const box = b.nextElementSibling; if (box && box.classList.contains('hcd-fin')) box.hidden = !on; return; }
    if (b.dataset.kind) { KIND = b.dataset.kind; return; }
    if (b.dataset.tid) return show('session', b.dataset.tid);
    if (b.dataset.go) return show(b.dataset.go);
    const act = ACTS[b.dataset.act]; if (act) act(b);
  }
  function onSubmit(ev) {
    const f = ev.target; if (f.method === 'dialog') return;
    if (f.id === 'hcdSteer') { ev.preventDefault(); sendMessage(); }
    else if (f.id === 'hcdAsk') { ev.preventDefault(); startSession(); }
    else if (f.id === 'hcdAllF') { ev.preventDefault(); ALL.q = $('#hcdAllQ').value.trim(); ALL.rows = null; allSessions(); }
  }
  function onKey(ev) {
    if (ev.key !== 'Enter' || ev.shiftKey || ev.isComposing) return;
    if (ev.target.id === 'hcdNote') { ev.preventDefault(); sendMessage(); }
    else if (ev.target.id === 'hcdLine' && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); startSession(); }
  }
  const grow = ta => { ta.style.height = 'auto'; ta.style.height = Math.min(160, ta.scrollHeight) + 'px'; };

  // ------------------------------------------------------------------ home ---
  function home() {
    const st = OV?.settings || {}, repos = OV?.repos || [];
    const setup = !st.github ? `<div class="hcd-block"><b>Connect GitHub first.</b> Add a fine-grained token and a repo in <button type="button" class="hcd-link" data-go="settings">Settings</button>. The token is typed only there.</div>`
      : !repos.length ? `<div class="hcd-block"><b>Add a repo first</b> in <button type="button" class="hcd-link" data-go="settings">Settings</button>.</div>` : '';
    body(`<main class="hcd-home">
      ${OV?.error ? `<p class="hcd-err">${esc(OV.error)}</p>` : ''}
      <h1>What should Hoola code today?</h1>
      ${setup}
      <form class="hcd-ask" id="hcdAsk">
        <label for="hcdLine" class="hcd-sr">Describe the task</label>
        <textarea id="hcdLine" rows="3" maxlength="20000" placeholder="Describe a task, or paste an error and its stack trace"></textarea>
        <button class="hcd-send" id="hcdStart" type="submit" aria-label="Start session" title="Start (Ctrl + Enter)"${repos.length && st.github ? '' : ' disabled'}>${svg('up')}</button>
      </form>
      <div class="hcd-askrow">
        <label class="hcd-chip"><span class="hcd-sr">Repo</span><select id="hcdRepo" aria-label="Repo">${repos.map(r => `<option value="${esc(r.repo)}"${r.repo === REPO ? ' selected' : ''}>${esc(r.repo)}</option>`).join('') || '<option value="">no repo yet</option>'}</select></label>
        <label class="hcd-chip"><span class="hcd-sr">Kind of work</span><select id="hcdKind" aria-label="Kind of work">${KINDS.map(([k, n]) => `<option value="${k}"${k === KIND ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
        <label class="hcd-chip">Issue # <input id="hcdIssue" inputmode="numeric" maxlength="7" size="5"></label>
      </div>
      <p class="hcd-lede">Hoola works on its own branch, runs your tests, and opens a pull request. Nothing is merged without you.</p>
    </main>`);
    $('#hcdLine')?.focus();
  }
  async function startSession() {
    const text = $('#hcdLine').value.trim(), btn = $('#hcdStart'); REPO = $('#hcdRepo').value; KIND = $('#hcdKind').value;
    if (!text) return toast('Describe the task, or paste the error.', true);
    btn.disabled = true;
    try { const t = await api('POST', '/api/devsahayak/tasks/start', {kind: KIND, text, repo: REPO, issue: +$('#hcdIssue').value || 0}); await load(); show('session', t.id); }
    catch (e) { toast(e.message, true); btn.disabled = false; }
  }

  // ------------------------------------------------------------------ session: the steps ---
  const QUIET = new Set(['rules', 'read', 'search', 'list', 'usages', 'grep', 'diff', 'refused']);
  const diffHTML = rows => rows && rows.length ? `<pre class="hcd-diff">${rows.map(r => `<span class="${r.startsWith('+') ? 'add' : r.startsWith('-') ? 'del' : 'ctx'}">${esc(r)}</span>`).join('\n')}</pre>` : '';
  const p = x => `<code>${esc(x)}</code>`;
  const fold = (key, label, inner, cls = '', forced = false) => { const on = forced || OPEN.has(key);
    return `<button type="button" class="hcd-fold ${cls}" data-fold="${esc(key)}" aria-expanded="${on}">${svg('chev', 'hcd-chev')}<span>${label}</span></button><div class="hcd-fin"${on ? '' : ' hidden'}>${inner}</div>`; };
  function stepHTML(s, t0, i, verbose) {
    const at = `<span class="hcd-t">${esc(since(t0, s.at))}</span>`;
    switch (s.k) {
      case 'say': return `<p class="hcd-say">${esc(s.text)}</p>`;
      case 'note': return `<div class="hcd-me sm">${esc(s.text)}<small>you, while Hoola worked</small></div>`;
      case 'rules': return `<div class="hcd-step">${svg('list')}<span>Read the repo's rules · ${(s.paths || []).map(p).join(', ')}</span>${at}</div>`;
      case 'read': return `<div class="hcd-step">${svg('read')}<span>Read ${p(s.path)}${s.lines && s.lines[0] ? ` · lines ${s.lines[0]}–${s.lines[1] || 'end'}` : ''}</span>${at}</div>`;
      case 'search': return `<div class="hcd-step">${svg('search')}<span>Searched ${p(s.q)} · ${plural(s.n, 'file')}</span>${at}</div>`;
      case 'list': return `<div class="hcd-step">${svg('list')}<span>Looked in folder ${p(s.path || '/')}</span>${at}</div>`;
      case 'usages': return `<div class="hcd-step">${svg('search')}<span>Found where ${p(s.name)} is used · ${plural(s.n, 'place')}</span>${at}</div>`;
      case 'edit': case 'new': { const lab = `${s.k === 'new' ? 'Created' : 'Edited'} ${p(s.path)} <em class="add">+${s.added || 0}</em>${s.k === 'edit' ? ` <em class="del">−${s.removed || 0}</em>` : ''}`;
        return s.diff && s.diff.length ? fold('e' + i, lab, diffHTML(s.diff), 'row', verbose) : `<div class="hcd-step">${svg(s.k === 'new' ? 'new' : 'edit')}<span>${lab}</span>${at}</div>`; }
      case 'diff': return `<div class="hcd-step">${svg('read')}<span>Checked its own change · ${plural(s.n, 'file')}</span>${at}</div>`;
      case 'check': return `<div class="hcd-step ${s.ok ? 'ok' : 'bad'}">${svg(s.ok ? 'ok' : 'bad')}<span><b>Ran your tests</b>${s.only ? ` (${esc(s.only)})` : ''} · <span class="${s.ok ? 'add' : 'del'}">${s.ok ? 'passed' : 'failed'}</span>${s.seconds ? ` · ${esc(String(s.seconds))} s` : ''}${s.cmd ? ` · ${p(s.cmd)}` : ''}</span>${at}</div>${!s.ok && s.tail && s.tail.length ? `<pre class="hcd-diff">${s.tail.map(x => `<span class="${/fail|error|assert/i.test(x) ? 'del' : 'ctx'}">${esc(x)}</span>`).join('\n')}</pre>` : ''}`;
      case 'check_off': return `<div class="hcd-step">${svg('bad')}<span>Your tests could not run here - this change is not measured</span>${at}</div>`;
      case 'grep': return `<div class="hcd-step">${svg('search')}<span>Searched the test log for ${p(s.q)}</span>${at}</div>`;
      case 'refused': return `<div class="hcd-step dim">${svg('bad')}<span>A step was refused: ${esc(s.why)}</span>${at}</div>`;
      case 'stopped': return `<div class="hcd-step bad">${svg('bad')}<span><b>Stopped.</b> Nothing was pushed.</span>${at}</div>`;
      default: return '';
    }
  }
  function summary(list) {
    const n = k => list.filter(s => s.k === k).length, parts = [];
    if (n('rules')) parts.push("read the repo's rules");
    if (n('read')) parts.push(`read ${plural(new Set(list.filter(s => s.k === 'read').map(s => s.path)).size, 'file')}`);
    const se = n('search') + n('usages') + n('grep'); if (se) parts.push(`searched ${plural(se, 'time')}`);
    if (n('list')) parts.push(`looked in ${plural(n('list'), 'folder')}`);
    if (n('diff')) parts.push('checked its own change');
    if (n('refused')) parts.push(`${plural(n('refused'), 'step')} refused`);
    const s = parts.join(', '); return s.charAt(0).toUpperCase() + s.slice(1);
  }
  function stepsHTML(t) {
    const steps = t.steps || [], verbose = P.view === 'verbose'; let out = '', i = 0;
    while (i < steps.length) {
      if (!verbose && QUIET.has(steps[i].k)) { const from = i, list = []; while (i < steps.length && QUIET.has(steps[i].k)) list.push(steps[i++]);
        out += list.length === 1 ? stepHTML(list[0], t.at, from, false) : fold('g' + from, esc(summary(list)), list.map((s, j) => stepHTML(s, t.at, from + j, false)).join('')); }
      else { out += stepHTML(steps[i], t.at, i, verbose); i++; }
    }
    return out;
  }
  const PROOF = {proven: ['ok', 'Bug proven: your CI failed the test first'], proven_local: ['ok', 'Bug proven: the test failed before the fix'],
    proven_unnamed: ['ok', 'Your CI went red on the test first'], not_proven: ['warn', 'The test passed on the old code - it does not prove the bug'],
    not_proven_local: ['warn', 'The test passed on the old code - it does not prove the bug'], still_failing: ['bad', 'Your tests still fail after the fix'],
    checked_local: ['ok', 'Your tests passed'], check_failed_local: ['bad', 'Your tests failed'], wait: ['run', 'Waiting for your CI']};
  const CI = {success: ['ok', 'Passed'], failure: ['bad', 'Failed'], pending: ['run', 'Running'], none: ['soft', 'No CI']};

  function planHTML(t) {
    const pl = t.plan || {};
    const li = xs => (xs || []).map(x => `<li>${esc(typeof x === 'string' ? x : `${x.path || ''}${x.why ? ' - ' + x.why : ''}`)}</li>`).join('');
    return `<section class="hcd-card" aria-labelledby="hcdPlanH"><div class="hcd-sh"><h2 id="hcdPlanH">The plan</h2><span class="hcd-pill warn">${esc(t.tier || 'large')} job · waits for your OK</span></div>
      ${pl.goal ? `<p><b>Goal:</b> ${esc(pl.goal)}</p>` : ''}
      ${pl.files?.length ? `<h3>Files it will change</h3><ul class="mono">${li(pl.files)}</ul>` : ''}
      ${pl.steps?.length ? `<h3>Steps</h3><ol>${li(pl.steps)}</ol>` : ''}
      ${pl.done_when?.length ? `<h3>Done when</h3><ul>${li(pl.done_when)}</ul>` : ''}
      ${pl.risk ? `<div class="hcd-risk"><h3>Risks</h3><p>${esc(String(pl.risk))}</p></div>` : ''}
      <p class="hcd-mut">Nothing is touched until you say yes.</p></section>`;
  }
  function recap(t) {
    const ci = t.ci?.state;
    if (t.status === 'ready') return ['need', 'Ready for you.', 'The change is prepared. Opening the pull request is your tap.'];
    if (t.status === 'checks_failed') return ['bad', `CI failed on PR #${t.pr_number}.`, 'Hoola can fix it, or you can ask for a change.'];
    if (t.status === 'pr_open' && ci === 'success') return ['ok', 'Ready for you.', `PR #${t.pr_number} is open and CI passed. Merging is your tap.`];
    if (t.status === 'pr_open') return ['soft', `PR #${t.pr_number} is open.`, ci === 'pending' ? 'CI is still running.' : 'Merging is your tap.'];
    if (t.status === 'merged') return ['ok', 'Merged.', `PR #${t.pr_number} is in.`];
    if (t.status === 'cancelled') return ['soft', 'Stopped.', 'Nothing more will be pushed for this session.'];
    return null;
  }
  function doneHTML(t) {
    const parts = [];
    if (t.error && ['failed', 'refused'].includes(t.status)) parts.push(`<div class="hcd-block bad"><b>${t.status === 'refused' ? 'A safety rule stopped this change.' : 'It could not finish.'}</b> ${esc(t.error)}</div>`);
    if (t.explain) parts.push(`<div class="hcd-say">${esc(t.explain)}</div>`);
    const sr = t.self_review || {};
    if (sr.verdict && sr.verdict !== 'ok' && (sr.problems || []).length) parts.push(`<section class="hcd-card"><div class="hcd-sh"><h2>Hoola's own review</h2><span class="hcd-pill warn">${plural(sr.problems.length, 'point')} left open</span></div>
      ${sr.problems.slice(0, 8).map(x => `<div class="hcd-cm">${esc(typeof x === 'string' ? x : (x.body || x.text || x.problem || JSON.stringify(x)))}</div>`).join('')}</section>`);
    if (t.diff) parts.push(`<div id="hcdFull">${fold('full', `The full change · ${plural((t.files || []).length, 'file')}`, `<pre class="hcd-diff tall">${String(t.diff).split('\n').map(r => `<span class="${/^\+(?!\+\+)/.test(r) ? 'add' : /^-(?!--)/.test(r) ? 'del' : 'ctx'}">${esc(r)}</span>`).join('\n')}</pre>`, 'row')}</div>`);
    if (t.risk) parts.push(`<p class="hcd-mut"><b>Risk:</b> ${esc(t.risk)}</p>`);
    const rc = recap(t), acts = actsFor(t); if (rc) parts.push(`<div class="hcd-recap ${rc[0]}"><span><b>${esc(rc[1])}</b> ${esc(rc[2])}</span>${acts.length ? `<div class="hcd-acts">${acts.join('')}</div>` : ''}</div>`);
    return parts.join('');
  }
  function feedHTML(t) {
    const steps = t.steps || [], inner = stepsHTML(t);
    let h = `<div class="hcd-me">${esc(t.text || '')}</div>`;
    if (t.running || P.view === 'verbose' || !steps.length) h += inner || (t.running ? '<p class="hcd-mut">Reading the repo…</p>' : '');
    else h += fold('work', `Worked for ${esc(dur((Date.parse(steps[steps.length - 1].at) - Date.parse(t.at)) / 1000))} · ${plural(steps.length, 'step')}`, inner);
    if (t.running && !t.stopping) h += `<div class="hcd-work"><i class="hcd-pulse" aria-hidden="true"></i><span>${esc(nowDoing(t))}</span></div>`;
    if (t.status === 'plan_wait' && t.plan) h += planHTML(t);
    else if (!t.running) h += doneHTML(t);
    return h;
  }
  function nowDoing(t) {
    const s = (t.steps || []).filter(x => x.k !== 'say' && x.k !== 'note').pop();
    if (!s) return 'Reading the repo…';
    return ({edit: 'Checking the edit…', new: 'Checking the new file…', check: s.ok ? 'Finishing up…' : 'Looking at the failure…', read: 'Reading the code…', search: 'Searching the code…'})[s.k] || 'Working on the next step…';
  }

  // ------------------------------------------------------------------ session: the rail ---
  function stages(t) {
    const st = t.steps || [], has = (...ks) => st.some(s => ks.includes(s.k)), last = k => st.filter(s => s.k === k).pop();
    const ck = last('check'), ci = t.ci?.state, rows = [['Read the code', has('read', 'search', 'list', 'usages', 'rules') ? 'done' : 'todo', '']];
    if (t.kind !== 'explain') {
      rows.push(['Make the change', has('edit', 'new') ? 'done' : 'todo', '']);
      rows.push(['Run your tests', ck ? (ck.ok ? 'done' : 'bad') : has('check_off') ? 'off' : 'todo', ck ? (ck.ok ? 'passed' : 'failed') : has('check_off') ? 'could not run' : '']);
      rows.push(['Check its own change', has('diff') || t.self_review?.verdict ? 'done' : 'todo', '']);
      rows.push(['Pull request', t.pr_number ? 'done' : 'todo', t.pr_number ? `#${t.pr_number}` : '']);
      rows.push(['CI on GitHub', ci === 'success' ? 'done' : ci === 'failure' ? 'bad' : 'todo', (CI[ci] || ['', ''])[1] && t.pr_number ? CI[ci][1] : '']);
    }
    if (t.running) { const i = rows.findIndex(r => r[1] === 'todo'); if (i >= 0) rows[i][1] = 'now'; }
    return rows;
  }
  function editedFiles(t) {
    if ((t.files || []).length) return t.files;
    const ed = {}; (t.steps || []).forEach(s => { if (s.k === 'edit' || s.k === 'new') { ed[s.path] = ed[s.path] || {path: s.path, added: 0, removed: 0}; ed[s.path].added += s.added || 0; ed[s.path].removed += s.removed || 0; } });
    return Object.values(ed);
  }
  // What she can do next. Drawn twice - on the Changes card in the rail AND on the recap card in the chat - so the
  // buttons are still there when the rail is hidden.
  function actsFor(t) {
    const acts = []; if (t.running) return acts;
    if (t.status === 'ready' && t.hash) acts.push(`<button type="button" class="hcd-btn pri" data-act="push">Open the pull request</button>`);
    if (t.status === 'checks_failed') acts.push(`<button type="button" class="hcd-btn pri" data-act="fixci">Fix the CI failure</button>`);
    if (['pr_open', 'checks_failed'].includes(t.status) && t.pr_number && !MERGE) acts.push(`<button type="button" class="hcd-btn${t.status === 'pr_open' && t.ci?.state === 'success' ? ' ok' : ''}" data-act="mergereq">Merge…</button>`);
    if (t.pr_url) acts.push(`<a class="hcd-btn" href="${esc(t.pr_url)}" target="_blank" rel="noopener noreferrer">View PR</a>`);
    if (['pr_open', 'checks_failed', 'ci_running'].includes(t.status)) acts.push(`<button type="button" class="hcd-btn" data-act="refresh">Check CI again</button>`);
    return acts;
  }
  function railHTML(t) {
    const files = editedFiles(t), kv = (a, b) => `<div class="hcd-row"><span>${a}</span><b>${b}</b></div>`;
    const checks = []; const pf = PROOF[t.proof?.state]; if (pf) checks.push(kv('Proof', `<span class="hcd-c ${pf[0]}">${esc(pf[1])}</span>`));
    const ci = CI[t.ci?.state]; if (t.pr_number && ci) checks.push(kv('CI on GitHub', `<span class="hcd-c ${ci[0]}">${esc(ci[1])}${t.rounds ? ` · round ${t.rounds}` : ''}</span>`));
    if (t.self_review?.verdict) checks.push(kv("Hoola's own review", `<span class="hcd-c ${t.self_review.verdict === 'ok' ? 'ok' : 'warn'}">${t.self_review.verdict === 'ok' ? 'Clean' : plural((t.self_review.problems || []).length, 'point') + ' open'}</span>`));
    if (!t.running && t.kind !== 'explain' && files.length) checks.push(kv('Security checks', `<span class="hcd-c ${(t.checks || []).length ? 'warn' : 'ok'}">${(t.checks || []).length ? plural(t.checks.length, 'note') : 'Clean'}</span>`));
    const acts = actsFor(t);
    const sg = {done: svg('ok', 'ok'), bad: svg('bad', 'bad'), now: '<i class="hcd-pulse sm" aria-hidden="true"></i>', off: svg('bad'), todo: '<i class="hcd-ring" aria-hidden="true"></i>'};
    return `<section class="hcd-rc" aria-labelledby="hcdRcC"><h2 id="hcdRcC">Changes<span class="hcd-stat">${stat({files})}</span></h2>
        ${files.length ? files.map(f => `<div class="hcd-file"><code title="${esc(f.path)}">${esc(f.path)}</code><span><em class="add">+${f.added || 0}</em> <em class="del">−${f.removed || 0}</em></span></div>`).join('') : '<p class="hcd-mut">No changes yet.</p>'}
        ${t.pr_number ? kv('Pull request', `#${t.pr_number} · ${esc(STATUS[t.status] || t.status)}`) : ''}${checks.join('')}
        ${acts.length ? `<div class="hcd-acts">${acts.join('')}</div>` : ''}</section>
      <section class="hcd-rc" aria-labelledby="hcdRcP"><h2 id="hcdRcP">Progress</h2>${stages(t).map(([name, s, note]) => `<div class="hcd-stage ${s}">${sg[s]}<span>${name}</span><small>${esc(note)}</small></div>`).join('')}</section>
      <section class="hcd-rc" aria-labelledby="hcdRcS"><h2 id="hcdRcS">Session</h2>${kv('Repo', esc(t.repo || ''))}${t.branch ? kv('Branch', `<code>${esc(t.branch)}</code>`) : ''}
        ${kv('Kind', esc((KINDS.find(k => k[0] === t.kind) || [0, t.kind])[1]))}${t.tier ? kv('Job size', esc(t.tier)) : ''}${kv('Steps', String((t.steps || []).length))}${kv('Started', esc(ago(t.at)))}</section>`;
  }

  // ------------------------------------------------------------------ session: mount once, paint what changed ---
  async function session(tid) {
    body(`<div class="hcd-sess-wrap"><main class="hcd-main">
        <header class="hcd-top" id="hcdTop"></header>
        <div class="hcd-feed" id="hcdFeed"><div class="hcd-col" id="hcdCol"><p class="hcd-mut">Opening…</p></div></div>
        <div class="hcd-queue" id="hcdQueue"></div>
        <div class="hcd-bar" id="hcdBar"></div>
        <form class="hcd-cp" id="hcdSteer"><label for="hcdNote" class="hcd-sr">Message Hoola</label>
          <textarea id="hcdNote" rows="1" maxlength="4000"></textarea><span class="hcd-cpb" id="hcdCpB"></span></form>
      </main><aside class="hcd-rail" id="hcdRail" aria-label="Session details"></aside></div>`);
    await refreshTask(tid, true);
    POLL = setInterval(() => { if (VIEW !== 'session' || TID !== tid || !EL.isConnected) return;
      if (TASK?.running || ['ci_running', 'new'].includes(TASK?.status)) refreshTask(tid, false); else tick(); }, 2000);
  }
  async function refreshTask(tid, first) {
    let t; try { t = await api('GET', `/api/devsahayak/tasks/${encodeURIComponent(tid)}`); } catch (e) { if (first) { toast(e.message, true); show('home'); } return; }
    if (VIEW !== 'session' || TID !== tid) return;
    const was = TASK && TASK.id === tid ? TASK : null; TASK = t;
    if (was && was.running && !t.running) { await load(); drawSide(); }
    if (t.pr_number && !t.running && !MERGE) MERGE = (OV?.actions || []).find(a => a.kind === 'merge' && a.status === 'waiting' && a.repo === t.repo && a.pr_number === t.pr_number) || null;
    paint();
  }
  const railShown = () => { const r = $('#hcdRail'); return !!r && getComputedStyle(r).display !== 'none'; };
  const put = (id, key, html) => { if (SIG[key] === html) return false; const el = $(id); if (!el) return false; el.innerHTML = html; SIG[key] = html; return true; };
  function tick() { const c = $('#hcdClock'); if (c && TASK?.running && !TASK.stopping) c.textContent = `Working · ${dur((Date.now() - Date.parse(TASK.at)) / 1000)}`; }
  function paint() {
    const t = TASK; if (!t || !$('#hcdTop')) return;
    const files = editedFiles(t), railOn = railShown();
    put('#hcdTop', 'top', `<button type="button" class="hcd-title" data-act="rename" title="Rename">${esc(t.title || t.number)}</button>
      <button type="button" class="hcd-icb" data-menu="title" aria-label="Session menu: rename, transcript view, archive, delete" title="Session menu">${svg('down')}</button>
      <span class="hcd-flex"></span>
      ${t.running ? `<span class="hcd-live" id="hcdClock">${t.stopping ? 'Stopping after this step' : 'Working'}</span>` : `<span class="hcd-pill ${dotc(t)}">${esc(STATUS[t.status] || t.status)}</span>`}
      ${files.length && t.diff ? `<button type="button" class="hcd-btn sm" data-act="changes">Changes <span class="hcd-stat">${stat({files})}</span></button>` : ''}
      <button type="button" class="hcd-icb" data-act="rail" aria-pressed="${railOn}" aria-label="${railOn ? 'Hide' : 'Show'} session details" title="${railOn ? 'Hide' : 'Show'} session details">${svg('rail')}</button>`);
    tick();
    const feed = $('#hcdFeed'), atBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 80;
    if (put('#hcdCol', 'feed', feedHTML(t)) && atBottom) feed.scrollTop = feed.scrollHeight;
    put('#hcdQueue', 'queue', (t.running ? (t.notes || []) : []).map((n, i) => `<div class="hcd-q"><span><b>Queued</b> ${esc(n)}</span><button type="button" class="hcd-icb" data-act="unq" data-i="${i}" aria-label="Take this message back" title="Take it back">${svg('x')}</button></div>`).join(''));
    put('#hcdBar', 'bar', barHTML(t));
    put('#hcdRail', 'rail', railHTML(t));
    const mode = t.running ? 'note' : t.status === 'plan_wait' ? 'plan' : CAN_REVISE.has(t.status) ? 'revise' : 'off', f = $('#hcdSteer'), ta = $('#hcdNote');
    if (f.dataset.mode !== mode) { f.dataset.mode = mode; f.hidden = mode === 'off';
      ta.placeholder = {note: 'Message Hoola - it reads it before its next step', plan: 'Add a note for Hoola - it starts on the plan with your note',
        revise: 'Ask for a change - Hoola adds a commit to the same pull request', off: ''}[mode]; }
    put('#hcdCpB', 'cpb', t.running ? `<button type="button" class="hcd-stop" id="hcdStop" data-act="stop"${t.stopping ? ' disabled' : ''}>${svg('stop')}Stop</button>`
      : `<button type="submit" class="hcd-send" aria-label="Send" title="Send (Enter)">${svg('up')}</button>`);
  }
  function barHTML(t) {
    if (t.running) return '';
    if (t.status === 'plan_wait') return `<div class="hcd-ask2"><b>Start on this plan?</b><span class="hcd-flex"></span><button type="button" class="hcd-btn" id="hcdCancel" data-act="cancel">Cancel job</button><button type="button" class="hcd-btn pri" id="hcdYes" data-act="yes">Yes, start</button></div>`;
    if (MERGE) { const a = MERGE; return `<div class="hcd-ask2 col"><div class="hcd-ask2r"><b>${esc(a.method)} merge PR #${a.pr_number} into ${esc(a.base)}?</b><span class="hcd-mut">commit <code>${esc(a.head_sha)}</code> · CI ${esc((CI[a.ci_state] || ['', a.ci_state])[1])}</span><span class="hcd-flex"></span>
        <button type="button" class="hcd-btn" data-act="mergeno">Not now</button><button type="button" class="hcd-btn ok" data-act="mergeyes">Merge</button></div>
        ${(a.notes || []).map(n => `<p class="hcd-mut">${esc(n)}</p>`).join('')}
        ${a.needs_force ? '<label class="hcd-f"><span>CI is not green - write why you still want to merge (8+ characters)</span><input id="hcdForce" maxlength="300"></label>' : ''}
        <p class="hcd-mut">If anything is pushed after this card, it goes stale and asks again.</p></div>`; }
    if (t.status === 'ready' && t.hash) return `<div class="hcd-ask2"><b>The change is ready. Open the pull request?</b><span class="hcd-flex"></span><button type="button" class="hcd-btn pri" id="hcdPush" data-act="push">Open the pull request</button></div>`;
    if (!CAN_REVISE.has(t.status)) return `<div class="hcd-ask2 soft"><span>This session is finished.</span><span class="hcd-flex"></span><button type="button" class="hcd-btn" data-go="home">New session</button></div>`;
    return '';
  }

  // ------------------------------------------------------------------ session: what she can do ---
  const tid = () => encodeURIComponent(TASK.id);
  const busy = async (btn, fn) => { if (btn) btn.disabled = true; try { await fn(); } catch (e) { toast(e.message, true); if (btn && btn.isConnected) btn.disabled = false; } };
  const again = async () => { await load(); drawSide(); await refreshTask(TASK.id, false); };
  async function sendMessage() {
    const ta = $('#hcdNote'), v = ta.value.trim(), mode = $('#hcdSteer').dataset.mode, t = TASK; if (!t || !v || mode === 'off') return;
    try {
      if (mode === 'note') { await api('POST', `/api/devsahayak/tasks/${tid()}/note`, {text: v}); }
      else if (mode === 'plan') { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/plan_ok`, {hash: t.hash, note: v}); }
      else { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/revise`, {text: v}); }
      ta.value = ''; grow(ta); await again();
    } catch (e) { toast(e.message, true); }
  }
  const ACTS = {
    side: () => { P.side = P.side === 'min' ? 'open' : 'min'; keep(); drawSide(); },
    rail: () => { P.rail = railShown() ? 'off' : ($('#hcdBody').clientWidth < 780 ? 'on' : 'auto'); keep(); $('.hcd').dataset.rail = P.rail; SIG.top = ''; paint(); },   // 'on' = an overlay she opened on a narrow window
    rename: () => askName(TASK),
    changes: () => { OPEN.add('full'); SIG.feed = ''; paint(); $('#hcdFull')?.scrollIntoView({block: 'start'}); },
    stop: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/stop`); await again(); }),
    unq: b => busy(b, async () => { const r = await api('DELETE', `/api/devsahayak/tasks/${tid()}/note/${+b.dataset.i}`);
      const ta = $('#hcdNote'); ta.value = ta.value ? `${r.text}\n${ta.value}` : r.text; grow(ta); ta.focus(); await refreshTask(TASK.id, false); }),
    yes: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/plan_ok`, {hash: TASK.hash}); await again(); }),
    cancel: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/cancel`); await again(); }),
    push: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/push`, {hash: TASK.hash}); await again(); }),
    fixci: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/fix_ci`); await again(); }),
    refresh: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/refresh`); MERGE = null; await again(); }),
    mergereq: b => busy(b, async () => { MERGE = await api('POST', `/api/devsahayak/tasks/${tid()}/merge_request`, {}); await again(); }),
    mergeyes: b => busy(b, async () => { const r = await api('POST', `/api/devsahayak/actions/${encodeURIComponent(MERGE.id)}/decide`, {yes: true, hash: MERGE.hash, force_reason: $('#hcdForce')?.value || ''});
      toast(r.say || 'Merged.'); MERGE = null; await again(); }),
    mergeno: b => busy(b, async () => { await api('POST', `/api/devsahayak/actions/${encodeURIComponent(MERGE.id)}/decide`, {yes: false, hash: MERGE.hash}); MERGE = null; await again(); }),
    alltab: b => { ALL.tab = b.dataset.tab; ALL.rows = null; allSessions(); },
    unarch: b => setArchived(findTask(b.dataset.id), false),
    arch: b => setArchived(findTask(b.dataset.id), true),
    del: b => askDelete(findTask(b.dataset.id)),
  };

  // ------------------------------------------------------------------ all sessions ---
  async function allSessions() {
    const arch = ALL.tab === 'archived';
    const draw = () => body(`<main class="hcd-page"><h1>All sessions</h1>
      <div class="hcd-tabs" role="tablist"><button type="button" role="tab" aria-selected="${!arch}" data-act="alltab" data-tab="active">Active</button><button type="button" role="tab" aria-selected="${arch}" data-act="alltab" data-tab="archived">Archived</button>
        <form class="hcd-inline" id="hcdAllF"><label class="hcd-sr" for="hcdAllQ">Search all sessions</label><input id="hcdAllQ" type="search" placeholder="Search by words, title or repo" value="${esc(ALL.q)}"><button class="hcd-btn" type="submit">Search</button></form></div>
      ${ALL.rows === null ? '<p class="hcd-mut">Loading…</p>' : ALL.rows.length ? ALL.rows.map(t => `<div class="hcd-arow"><button type="button" class="hcd-sessb" data-tid="${esc(t.id)}"><span class="hcd-st"><i class="hcd-dot ${dotc(t)}"></i><span>${esc(t.title || t.number)}</span></span>
          <small>${esc(t.repo || '')} · ${esc(sub(t))} · ${esc(ago(t.updated || t.at))}</small></button><span class="hcd-stat">${stat(t)}</span>
          ${arch ? `<button type="button" class="hcd-btn sm" data-act="unarch" data-id="${esc(t.id)}">Unarchive</button>` : `<button type="button" class="hcd-btn sm" data-act="arch" data-id="${esc(t.id)}"${isRun(t) ? ' disabled' : ''}>Archive</button>`}
          <button type="button" class="hcd-btn sm" data-act="del" data-id="${esc(t.id)}"${isRun(t) ? ' disabled' : ''}>Delete</button></div>`).join('')
        : `<p class="hcd-mut">${arch ? 'Nothing archived.' : 'No sessions found.'}</p>`}</main>`);
    draw();
    if (ALL.rows === null) {
      try { ALL.rows = (await api('GET', `/api/devsahayak/tasks?limit=100&archived=${arch ? 1 : 0}&q=${encodeURIComponent(ALL.q)}`)).tasks || []; } catch (e) { ALL.rows = []; toast(e.message, true); }
      if (VIEW === 'all') draw();
    }
  }

  // ------------------------------------------------------------------ reviews ---
  function reviews() {
    const rs = OV?.reviews || [], repos = OV?.repos || [];
    frame(`<main class="hcd-page"><h1>Review a teammate's pull request</h1>
      <p class="hcd-lede">Hoola reads the PR, its callers and tests, and writes a draft review. Nothing is posted until you choose how.</p>
      <form class="hcd-inline" id="hcdRevNew"><label class="hcd-chip">Repo <select id="hcdRvRepo">${repos.map(r => `<option${r.repo === REPO ? ' selected' : ''}>${esc(r.repo)}</option>`).join('')}</select></label>
        <label class="hcd-chip">PR # <input id="hcdRvPr" inputmode="numeric" size="6" required></label><button class="hcd-btn pri" type="submit" id="hcdRvGo">Review it</button></form>
      ${rs.length ? rs.map(revHTML).join('') : '<p class="hcd-mut">No reviews yet.</p>'}</main>`);
    $('#hcdRevNew').addEventListener('submit', async ev => { ev.preventDefault(); const b = $('#hcdRvGo'); b.disabled = true; b.textContent = 'Reading the PR…';
      try { await api('POST', '/api/devsahayak/reviews', {repo: $('#hcdRvRepo').value, pr: +$('#hcdRvPr').value}); await load(); reviews(); }
      catch (e) { toast(e.message, true); b.disabled = false; b.textContent = 'Review it'; } });
    EL.querySelectorAll('[data-post]').forEach(b => b.addEventListener('click', async () => {
      const r = rs.find(x => x.id === b.dataset.post), ev = EL.querySelector(`input[name="ev-${r.id}"]:checked`)?.value || 'COMMENT';
      b.disabled = true; try { await api('POST', `/api/devsahayak/reviews/${encodeURIComponent(r.id)}/post`, {hash: r.hash, event: ev}); toast('Posted on GitHub.'); await load(); reviews(); } catch (e) { toast(e.message, true); b.disabled = false; } }));
    EL.querySelectorAll('[data-discard]').forEach(b => b.addEventListener('click', async () => { try { await api('POST', `/api/devsahayak/reviews/${encodeURIComponent(b.dataset.discard)}/discard`); await load(); reviews(); } catch (e) { toast(e.message, true); } }));
  }
  function revHTML(r) {
    const draft = r.status === 'draft';
    const sev = s => `<span class="hcd-pill ${s === 'high' ? 'bad' : s === 'medium' ? 'warn' : 'soft'}">${esc(s || 'note')}</span>`;
    return `<section class="hcd-card"><div class="hcd-sh"><h2>${esc(r.author || '')} · PR #${r.pr_number} · ${esc(r.pr_title)}</h2><span class="hcd-pill ${draft ? 'warn' : 'soft'}">${draft ? 'Draft - not posted' : esc(r.status + (r.posted_event ? ' · ' + r.posted_event.toLowerCase().replace('_', ' ') : ''))}</span></div>
      <p class="hcd-mut">${esc(r.repo)} · ${esc(ago(r.at))}${r.url ? ` · <a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">on GitHub</a>` : ''}</p>
      ${r.summary ? `<p class="hcd-say">${esc(r.summary)}</p>` : ''}
      ${[...(r.findings || []), ...(r.comments || [])].map(c => `<div class="hcd-cm">${sev(c.severity)}<code>${esc(c.path || '')}${c.line ? ':' + c.line : ''}</code> ${esc(c.body || c.text || '')}</div>`).join('')}
      ${draft ? `<fieldset class="hcd-ev"><legend>Post as</legend>${[['COMMENT', 'Comment'], ['REQUEST_CHANGES', 'Request changes'], ['APPROVE', 'Approve']].map(([v, n]) => `<label><input type="radio" name="ev-${esc(r.id)}" value="${v}"${v === r.suggest ? ' checked' : ''}> ${n}</label>`).join('')}</fieldset>
        <div class="hcd-acts"><button type="button" class="hcd-btn pri" data-post="${esc(r.id)}">Post review</button><button type="button" class="hcd-btn" data-discard="${esc(r.id)}">Discard</button></div>` : ''}</section>`;
  }

  // ------------------------------------------------------------------ settings ---
  function settings() {
    const st = OV?.settings || {}, repos = OV?.repos || [];
    const sw = (k, label, sub2) => `<label class="hcd-tg"><span>${label}<small>${sub2}</small></span><input type="checkbox" data-sw="${k}"${st[k] ? ' checked' : ''}></label>`;
    frame(`<main class="hcd-page"><h1>Settings</h1><div class="hcd-grid">
      <section class="hcd-card"><h2>GitHub access</h2><p class="hcd-mut">A fine-grained token, typed only here. It is locked away on the server and never shown to the AI or the chat.</p>
        <p>${st.github ? `<span class="hcd-c ok">Connected</span>${st.login ? ' as <b>' + esc(st.login) + '</b>' : ''}${st.token_label ? ' · ' + esc(st.token_label) : ''}` : '<span class="hcd-c warn">Not connected</span>'}</p>
        <form class="hcd-inline" id="hcdTok"><label for="hcdTokIn" class="hcd-sr">GitHub token</label><input id="hcdTokIn" type="password" autocomplete="off" placeholder="github_pat_…"><button class="hcd-btn" type="submit">Save</button>${st.github ? '<button class="hcd-btn" type="button" id="hcdTokDel">Forget</button>' : ''}</form>
        <p class="hcd-mut">Needs: ${esc((st.permissions || []).join(', '))}.</p></section>
      <section class="hcd-card"><h2>Repos Hoola may work in</h2>
        ${repos.map(r => `<div class="hcd-repo"><code>${esc(r.repo)}</code><span class="hcd-mut">${r.private ? 'private' : 'public · asks before a PR'}${r.language ? ' · ' + esc(r.language) : ''}</span><button type="button" class="hcd-btn sm" data-rmrepo="${esc(r.repo)}">Remove</button></div>`).join('') || '<p class="hcd-mut">No repos yet.</p>'}
        <form class="hcd-inline" id="hcdAddRepo"><label for="hcdRepoIn" class="hcd-sr">Repo</label><input id="hcdRepoIn" placeholder="owner/name" maxlength="200"><button class="hcd-btn" type="submit">Add</button></form></section>
      <section class="hcd-card"><h2>How Hoola works</h2>
        ${sw('ask_before_pr', 'Ask me before opening a pull request', 'Public repos always ask')}
        ${sw('draft_pr', 'Open pull requests as drafts', 'Marked ready when CI is green')}
        ${sw('allow_workflows', 'Allow edits to .github/workflows', 'Off: CI files are never touched')}
        <label class="hcd-f"><span>Merge method</span><select data-set="merge_method">${['squash', 'merge', 'rebase'].map(m => `<option${m === st.merge_method ? ' selected' : ''}>${m}</option>`).join('')}</select></label>
        <label class="hcd-f"><span>Reviews of teammates' PRs</span><select data-set="review_post"><option value="draft"${st.review_post === 'draft' ? ' selected' : ''}>Draft - I post them</option><option value="direct"${st.review_post === 'direct' ? ' selected' : ''}>Post comments directly</option></select></label></section>
      <section class="hcd-card"><h2>Limits and your rules</h2>
        <label class="hcd-f"><span>Files per change</span><input type="number" min="1" max="60" data-set="max_files" value="${+st.max_files || 20}"></label>
        <label class="hcd-f"><span>Lines per change</span><input type="number" min="20" max="5000" data-set="max_lines" value="${+st.max_lines || 1500}"></label>
        <label class="hcd-f"><span>Your coding rules (Hoola follows them every time)</span><textarea rows="4" data-set="rules" maxlength="4000">${esc(st.rules || '')}</textarea></label>
        <p class="hcd-mut">Always on: ${esc((st.never || []).slice(0, 4).join(' · '))}</p></section>
    </div></main>`);
    $('#hcdTok').addEventListener('submit', async ev => { ev.preventDefault(); const v = $('#hcdTokIn').value.trim(); if (!v) return;
      try { await api('PUT', '/api/devsahayak/token', {token: v}); $('#hcdTokIn').value = ''; toast('GitHub connected.'); await load(); settings(); } catch (e) { toast(e.message, true); } });
    $('#hcdTokDel')?.addEventListener('click', async () => { if (!confirm('Forget the GitHub token?')) return; try { await api('DELETE', '/api/devsahayak/token'); await load(); settings(); } catch (e) { toast(e.message, true); } });
    $('#hcdAddRepo').addEventListener('submit', async ev => { ev.preventDefault(); const v = $('#hcdRepoIn').value.trim(); if (!v) return;
      try { await api('POST', '/api/devsahayak/repos', {repo: v}); await load(); settings(); } catch (e) { toast(e.message, true); } });
    EL.querySelectorAll('[data-rmrepo]').forEach(b => b.addEventListener('click', async () => { if (!confirm(`Remove ${b.dataset.rmrepo}? Nothing changes on GitHub.`)) return;
      const [o, n] = b.dataset.rmrepo.split('/'); try { await api('DELETE', `/api/devsahayak/repos/${encodeURIComponent(o)}/${encodeURIComponent(n)}`); await load(); settings(); } catch (e) { toast(e.message, true); } }));
    const save = async b => { try { OV.settings = await api('PUT', '/api/devsahayak/settings', b); toast('Saved.'); } catch (e) { toast(e.message, true); } };
    EL.querySelectorAll('[data-sw]').forEach(c => c.addEventListener('change', () => save({[c.dataset.sw]: c.checked})));
    EL.querySelectorAll('[data-set]').forEach(c => c.addEventListener('change', () => save({[c.dataset.set]: c.type === 'number' ? +c.value : c.value})));
  }

  return {open, leave};
};
