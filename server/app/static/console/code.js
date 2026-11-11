/* HOOLA CODE - Developer Sahayak as a console page.
   v0.748 the first page. v0.768 PHASE 1 of docs/HOOLA_CODE_WEB_PLAN.md: the shell and the session laid out like Claude
   Code on the web - three zones (sessions sidebar / chat / a right rail of status cards), steps folded into summaries
   (Normal / Verbose view), a queued note she can take back, rename / archive / delete, an All sessions page.

   THE RULE OF THIS FILE: a refresh never rebuilds what she is typing in. The session is mounted ONCE (title bar, feed,
   queue, bar, the message box, rail) and every 2 s only the regions whose content changed are repainted (paint()).
   The message box is never repainted. Clicks are handled by ONE listener on the root (data-act / data-go / data-tid /
   data-fold / data-menu), so repainted regions need no re-wiring.

   PHASE 2 (the same plan): the Changes pane beside the chat (file by file, line numbers, Compare against a branch), her
   comments on lines that QUEUE and ride her next message, Hoola's one question answered in the same session, the own
   review as a card with "Fix this one", and the pull request's menu (Auto-fix on / off, copy the checkout command).
   The pane is not repainted while she is writing a comment in it.

   PHASE 3 (the same plan): the composer. One box with "+" (files, photos, slash commands) and Send; ONE row of settings
   under it - repo, branch to work from, mode (ask before the PR / work and open it / plan first), model + effort, and
   this month's usage. The kind of work is read from her words (or a slash command). A link can pre-fill the box
   (?prompt= &repo= &branch= &mode=) but never starts anything by itself.

   Nothing reaches GitHub from this page except through the existing tap routes (push / plan-ok / post / decide). */
window.HoolaCode = function ({api, esc, toast, standalone = false}) {
  let EL = null, VIEW = 'home', TID = '', OV = null, TASK = null, POLL = 0, KIND = 'fix', REPO = '', MERGE = null;
  let Q = '', ALL = {tab: 'active', q: '', rows: null}, SIG = {}, WIRED = null;
  const OPEN = new Set();                 // folds she opened (kept across repaints)
  let PANE = null;                        // the Changes pane: {path, base, cmp, rows} - null = closed
  let COMMENTS = [], DRAFT = null;        // her comments on lines, waiting for her next message; the one she is writing
  let SIDE_AUTO = false;                  // the sessions sidebar stepped aside for the pane (comes back when it closes)
  const BRANCHES = {};                    // repo -> its branches (for Compare against), fetched once
  const HOME = {text: '', kind: 'auto', issue: 0, base: '', mode: '', model: '', effort: '', files: []};   // the composer, kept while she looks elsewhere
  const PICS = new Map();                 // session id + index -> blob: link of a picture she attached
  const MODES = [['ask', 'Ask before the PR', 'Shows the change and waits for your tap'], ['auto', 'Work and open the PR', 'Private repos only - merging is always yours'],
    ['plan', 'Plan first', 'No file is touched until you say yes']];
  const SLASH = [['plan', 'Plan first, wait for my OK'], ['fix', 'Fix a bug, with a test'], ['feature', 'Build a feature'], ['tests', 'Write tests'],
    ['docs', 'Write docs'], ['explain', 'Explain code, change nothing'], ['issue', 'Work on a GitHub issue: /issue 12'], ['review', 'Review a pull request: /review 12']];
  const rs = n => 'Rs ' + (n >= 100 ? Math.round(n).toLocaleString('en-IN') : (+n || 0).toFixed(2));
  const kb = n => n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1000)) + ' KB';
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
  const canRev = t => CAN_REVISE.has(t.status) || !!t.can_continue;   // v0.784 a session with a working copy takes a follow-up, like a conversation
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
  const needsYou = t => !!t.question || NEEDS.has(t.status) || (!!t.pr_number && (OV?.actions || []).some(a => a.status === 'waiting' && a.repo === t.repo && a.pr_number === t.pr_number));
  const group = t => isRun(t) ? 'run' : needsYou(t) ? 'need' : 'old';
  const dotc = t => ({run: 'run', need: 'warn'}[group(t)] || (t.status === 'merged' ? 'ok' : t.status === 'failed' ? 'bad' : 'soft'));
  const stat = t => { let a = 0, r = 0; (t.files || []).forEach(f => { a += f.added || 0; r += f.removed || 0; }); return (a || r) ? `<em class="add">+${a}</em> <em class="del">−${r}</em>` : ''; };
  const sub = t => isRun(t) ? 'Working' : t.question ? 'Hoola asks you a question' : (STATUS[t.status] || t.status);

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
    if (standalone && location.search) { const u = new URLSearchParams(location.search), g = k => (u.get(k) || '').trim();   // a link may pre-fill the box; it never starts anything
      HOME.text = (g('prompt') || g('q')).slice(0, 20000); HOME.base = g('branch').slice(0, 100); if (MODES.some(m => m[0] === g('mode'))) HOME.mode = g('mode');
      const r = g('repo') || g('repositories').split(',')[0]; if ((OV.repos || []).some(x => x.repo === r)) REPO = r;
      history.replaceState(null, '', location.pathname + location.hash); }
    if (standalone) { [VIEW, TID] = fromHash(); window.addEventListener('hashchange', () => { const [v, t] = fromHash(); if (v !== VIEW || t !== TID) show(v, t); }); }
    show(VIEW, TID); }
  function leave() { clearInterval(POLL); window.HoolaMenu?.close(); }

  function show(view, tid) {
    if (VIEW === 'home') keepHome();
    if ((tid || '') !== TID || view !== 'session') { COMMENTS = []; DRAFT = null; if (PANE) closePane(true); }
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
    EL.addEventListener('change', ev => { const t = ev.target;
      if (t.id === 'hcdCmp') compareWith(t.value);
      else if (t.id === 'hcdFile') { addFiles(t.files); t.value = ''; }
      else if (t.id === 'hcdRepo') { REPO = t.value; HOME.base = ''; keepHome(); home(); }
      else if (t.id === 'hcdBase') HOME.base = t.value;
      else if (t.id === 'hcdMode') HOME.mode = t.value;
      else if (t.id === 'hcdModel') HOME.model = t.value;
      else if (t.id === 'hcdEffort') HOME.effort = t.value; });
    EL.addEventListener('paste', ev => { if (ev.target.id !== 'hcdLine') return; const fs = [...(ev.clipboardData?.files || [])]; if (fs.length) { ev.preventDefault(); addFiles(fs); } });
    EL.addEventListener('dragover', ev => { if (ev.target.closest?.('#hcdAsk')) ev.preventDefault(); });
    EL.addEventListener('drop', ev => { if (!ev.target.closest?.('#hcdAsk')) return; ev.preventDefault(); addFiles(ev.dataTransfer?.files || []); });
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
  function prMenu(btn) {
    const t = TASK; if (!window.HoolaMenu || !t) return;
    const items = [{label: 'Fix a red CI run by itself', sub: t.auto_fix ? 'On for this pull request' : 'Off - a failure waits for you', checked: !!t.auto_fix,
      run: async () => { try { await api('PATCH', `/api/devsahayak/tasks/${tid()}`, {auto_fix: !t.auto_fix}); toast(t.auto_fix ? 'Auto-fix is off for this pull request.' : 'Auto-fix is on.'); await refreshTask(t.id, false); } catch (e) { toast(e.message, true); } }}];
    if (t.branch && t.pr_number) items.push({sep: true}, {label: 'Copy the checkout command', icon: 'braces', run: async () => { const cmd = `git fetch origin ${t.branch} && git checkout ${t.branch}`;
      try { await navigator.clipboard.writeText(cmd); toast('Copied: ' + cmd); } catch (e) { toast(cmd); } }});
    if (t.pr_url) items.push({label: 'Open on GitHub', icon: 'doc', run: () => window.open(t.pr_url, '_blank', 'noopener')});
    if (['pr_open', 'checks_failed', 'ci_running'].includes(t.status)) items.push({label: 'Check CI again', icon: 'restore', run: () => ACTS.refresh(null)});
    HoolaMenu.open(btn, items, {align: 'end', label: 'Pull request', width: 270});
  }
  function setView(v) { P.view = v; keep(); SIG.feed = ''; paint(); }

  // ------------------------------------------------------------------ one listener ---
  function onClick(ev) {
    const b = ev.target.closest('[data-act],[data-go],[data-tid],[data-fold],[data-menu],[data-kind]'); if (!b || !EL.contains(b)) return;
    if (b.dataset.menu) { ev.preventDefault();
      if (b.dataset.menu === 'group') return groupMenu(b);
      if (b.dataset.menu === 'title') return taskMenu(b, TASK, true);
      if (b.dataset.menu === 'pr') return prMenu(b);
      if (b.dataset.menu === 'plus') return plusMenu(b);
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
    else if (f.id === 'hcdCForm') { ev.preventDefault(); addComment(); }
    else if (f.id === 'hcdAsk') { ev.preventDefault(); startSession(); }
    else if (f.id === 'hcdAllF') { ev.preventDefault(); ALL.q = $('#hcdAllQ').value.trim(); ALL.rows = null; allSessions(); }
  }
  function onKey(ev) {
    if (ev.key === 'Escape' && ev.target.id === 'hcdCText') { ev.preventDefault(); return ACTS.ccancel(); }
    if (ev.key !== 'Enter' || ev.shiftKey || ev.isComposing) return;
    if (ev.target.id === 'hcdCText') { ev.preventDefault(); return addComment(); }
    if (ev.target.id === 'hcdNote') { ev.preventDefault(); sendMessage(); }
    else if (ev.target.id === 'hcdLine') { ev.preventDefault(); startSession(); }      // Enter starts, Shift + Enter is a new line
  }
  const grow = ta => { ta.style.height = 'auto'; ta.style.height = Math.min(160, ta.scrollHeight) + 'px'; };

  // ------------------------------------------------------------------ home ---
  const keepHome = () => { const l = $('#hcdLine'); if (l) HOME.text = l.value; };
  function trayHTML() {
    const chips = [];
    if (HOME.kind !== 'auto') chips.push(`<span class="hcd-att">${esc((KINDS.find(k => k[0] === HOME.kind) || [0, HOME.kind])[1])}<button type="button" class="hcd-icb" data-act="unkind" aria-label="Let Hoola read the kind of work from your words">${svg('x')}</button></span>`);
    if (HOME.issue) chips.push(`<span class="hcd-att">Issue #${HOME.issue}<button type="button" class="hcd-icb" data-act="unissue" aria-label="Remove the issue">${svg('x')}</button></span>`);
    HOME.files.forEach((f, k) => chips.push(`<span class="hcd-att">${f.kind === 'image' ? `<img src="${esc(f.url)}" alt="">` : svg('read')}<span>${esc(f.name)}</span><small>${kb(f.size)}</small><button type="button" class="hcd-icb" data-act="unfile" data-i="${k}" aria-label="Remove ${esc(f.name)}">${svg('x')}</button></span>`));
    return chips.join('');
  }
  function drawTray() { const t = $('#hcdTray'); if (t) { t.innerHTML = trayHTML(); t.hidden = !t.innerHTML; } }
  function addFiles(list) {
    [...(list || [])].forEach(file => {
      const img = /^image\/(png|jpeg|webp|gif)$/.test(file.type), n = HOME.files.filter(f => f.kind === (img ? 'image' : 'text')).length;
      if (img) { if (n >= 3) return toast('At most 3 pictures.', true); if (file.size > 3e6) return toast(`${file.name} is over 3 MB.`, true); }
      else { if (/^(video|audio|application\/(pdf|zip|octet))/.test(file.type)) return toast('Attach pictures or text files (code, logs, notes).', true);
        if (n >= 3) return toast('At most 3 text files.', true); if (file.size > 200000) return toast(`${file.name} is over 200 KB - paste the part that matters.`, true); }
      const rd = new FileReader();
      rd.onload = () => { HOME.files.push(img ? {name: file.name, kind: 'image', size: file.size, data: String(rd.result), url: URL.createObjectURL(file)}
        : {name: file.name, kind: 'text', size: file.size, text: String(rd.result)}); drawTray(); };
      rd.onerror = () => toast(`Could not read ${file.name}.`, true);
      img ? rd.readAsDataURL(file) : rd.readAsText(file);
    });
  }
  function plusMenu(btn) {
    if (!window.HoolaMenu) return $('#hcdFile')?.click();
    HoolaMenu.open(btn, [{label: 'Add files or photos', icon: 'doc', sub: 'Screenshots, logs, code - or paste / drop them', run: () => $('#hcdFile')?.click()}, {header: 'Slash commands'},
      ...SLASH.map(([c, d]) => ({label: '/' + c, sub: d, run: () => { if (c === 'issue' || c === 'review') { const l = $('#hcdLine'); l.value = `/${c} ` + l.value; l.focus(); l.setSelectionRange(c.length + 2, c.length + 2); } else slash(c, ''); }}))],
      {align: 'start', place: 'above', label: 'Add', width: 300});
  }
  /* A slash command sets something and leaves her words alone. Returns the words that are left, or null when it did the whole job. */
  function slash(cmd, rest) {
    const kinds = {fix: 'fix', feature: 'write', tests: 'tests', test: 'tests', docs: 'docs', explain: 'explain'};
    if (cmd === 'plan') { HOME.mode = 'plan'; const m = $('#hcdMode'); if (m) m.value = 'plan'; }
    else if (kinds[cmd]) HOME.kind = kinds[cmd];
    else if (cmd === 'issue') { const n = parseInt(rest, 10); if (!(n > 0)) { toast('Write the issue number: /issue 12', true); return null; } HOME.issue = n; rest = rest.replace(/^\s*#?\d+\s*/, ''); }
    else if (cmd === 'review') { const n = parseInt(rest.replace('#', ''), 10); if (!(n > 0)) { toast('Write the pull request number: /review 12', true); return null; }
      keepHome(); HOME.text = ''; reviewPr(REPO, n); return null; }
    else { toast(`Unknown command /${cmd}. Try ${SLASH.map(x => '/' + x[0]).join(' ')}`, true); return null; }
    drawTray(); return rest;
  }
  async function reviewPr(repo, n) {
    show('reviews'); toast(`Reading pull request #${n}…`);
    try { await api('POST', '/api/devsahayak/reviews', {repo, pr: n}); await load(); if (VIEW === 'reviews') reviews(); } catch (e) { toast(e.message, true); }
  }
  function loadBranches(repo) {
    if (!repo || BRANCHES[repo]) return;
    BRANCHES[repo] = [];
    api('GET', `/api/devsahayak/branches?repo=${encodeURIComponent(repo)}`).then(r => { BRANCHES[repo] = r.branches || [];
      const sel = $('#hcdBase'); if (sel && VIEW === 'home' && REPO === repo) sel.innerHTML = baseOptions(repo); }).catch(() => { delete BRANCHES[repo]; });
  }
  const baseOptions = repo => { const r = (OV?.repos || []).find(x => x.repo === repo), def = r?.default_branch || '', own = (BRANCHES[repo] || []).filter(b => b !== def && !b.startsWith('hoola/'));
    if (HOME.base && HOME.base !== def && !own.includes(HOME.base)) own.unshift(HOME.base);
    return `<option value="">${esc(def || 'default branch')}</option>${own.map(b => `<option value="${esc(b)}"${b === HOME.base ? ' selected' : ''}>${esc(b)}</option>`).join('')}`; };

  function home() {
    const st = OV?.settings || {}, repos = OV?.repos || [], ms = OV?.models || {options: []}, us = OV?.usage || {};
    const setup = !st.github ? `<div class="hcd-block"><b>Connect GitHub first.</b> Add a fine-grained token and a repo in <button type="button" class="hcd-link" data-go="settings">Settings</button>. The token is typed only there.</div>`
      : !repos.length ? `<div class="hcd-block"><b>Add a repo first</b> in <button type="button" class="hcd-link" data-go="settings">Settings</button>.</div>` : '';
    const mode = HOME.mode || (st.ask_before_pr ? 'ask' : 'auto');
    const ring = us.limit_inr > 0 ? `<span class="hcd-use" title="${rs(us.spent_inr)} of your ${rs(us.limit_inr)} monthly limit, across all of Hoola"><svg viewBox="0 0 20 20" width="18" height="18" role="img" aria-label="${Math.round(us.pct)} percent of this month's limit used"><circle cx="10" cy="10" r="7.5" fill="none" stroke="var(--hair2)" stroke-width="3"/><circle cx="10" cy="10" r="7.5" fill="none" stroke="${us.over ? 'var(--bad)' : us.pct >= 80 ? 'var(--warn)' : 'var(--pri)'}" stroke-width="3" stroke-linecap="round" stroke-dasharray="${(Math.min(100, us.pct) * 0.4712).toFixed(1)} 47.2" transform="rotate(-90 10 10)"/></svg>${Math.round(us.pct)}%</span>`
      : us.spent_inr > 0 ? `<span class="hcd-use" title="This month, across all of Hoola. No monthly limit is set.">${rs(us.spent_inr)} this month</span>` : '';
    body(`<main class="hcd-home">
      ${OV?.error ? `<p class="hcd-err">${esc(OV.error)}</p>` : ''}
      <h1>What should Hoola code today?</h1>
      ${setup}
      <form class="hcd-ask" id="hcdAsk">
        <div class="hcd-tray" id="hcdTray" hidden></div>
        <label for="hcdLine" class="hcd-sr">Describe the task</label>
        <textarea id="hcdLine" rows="3" maxlength="20000" placeholder="Describe a task, or paste an error and its stack trace">${esc(HOME.text)}</textarea>
        <button type="button" class="hcd-plus" data-menu="plus" aria-label="Add files, photos or a slash command" title="Add files, photos or a command">${svg('new')}</button>
        <input type="file" id="hcdFile" class="hcd-sr" multiple tabindex="-1" aria-hidden="true" accept="image/png,image/jpeg,image/webp,image/gif,text/*,.md,.log,.json,.csv,.py,.js,.ts,.tsx,.jsx,.dart,.kt,.java,.go,.rs,.rb,.php,.c,.cpp,.h,.cs,.sql,.yml,.yaml,.toml,.sh,.xml">
        <button class="hcd-send" id="hcdStart" type="submit" aria-label="Start session" title="Start (Enter)"${repos.length && st.github ? '' : ' disabled'}>${svg('up')}</button>
      </form>
      <div class="hcd-askrow">
        <label class="hcd-chip"><span class="hcd-sr">Repo</span><select id="hcdRepo" aria-label="Repo">${repos.map(r => `<option value="${esc(r.repo)}" title="${esc(r.repo)}"${r.repo === REPO ? ' selected' : ''}>${esc(r.repo.split('/')[1] || r.repo)}</option>`).join('') || '<option value="">no repo yet</option>'}</select></label>
        <label class="hcd-chip"><span class="hcd-sr">Branch to work from</span><select id="hcdBase" aria-label="Branch to work from" title="Hoola works from this branch and opens the pull request against it">${baseOptions(REPO)}</select></label>
        <label class="hcd-chip"><span class="hcd-sr">Mode</span><select id="hcdMode" aria-label="Mode" title="${esc((MODES.find(m => m[0] === mode) || MODES[0])[2])}">${MODES.map(([k, n]) => `<option value="${k}"${k === mode ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
        <span class="hcd-flex"></span>
        ${ms.forced ? `<span class="hcd-chip fixed" id="hcdModelFixed" title="${esc(ms.forced.why)}">${esc(ms.forced.model)}</span>`
          : (ms.options || []).length ? `<label class="hcd-chip"><span class="hcd-sr">Model</span><select id="hcdModel" aria-label="Model">${ms.options.map(o => `<option value="${esc(o.id)}"${o.id === (HOME.model || ms.default) ? ' selected' : ''}>${esc(o.label)}</option>`).join('')}</select></label>
            <label class="hcd-chip"><span class="hcd-sr">Effort</span><select id="hcdEffort" aria-label="Effort" title="How hard the model thinks: higher is slower and costs more">${(ms.efforts || []).map(e => `<option value="${e}"${e === (HOME.effort || ms.default_effort) ? ' selected' : ''}>${e[0].toUpperCase() + e.slice(1)}</option>`).join('')}</select></label>` : ''}
        ${ring}
      </div>
      <p class="hcd-lede">Hoola works on its own branch, runs your tests, and opens a pull request. Nothing is merged without you.</p>
    </main>`);
    drawTray(); loadBranches(REPO);
    $('#hcdLine')?.focus();
  }
  async function startSession() {
    const line = $('#hcdLine'), btn = $('#hcdStart'); let text = line.value.trim();
    const m = /^\/([a-z]+)\b[ \t]*/i.exec(text);
    if (m) { const left = slash(m[1].toLowerCase(), text.slice(m[0].length)); if (left === null) return; text = left.trim(); line.value = text;
      if (!text && !HOME.issue) return toast('Now describe the task.'); }
    if (!text && !HOME.issue) return toast('Describe the task, or paste the error.', true);
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const t = await api('POST', '/api/devsahayak/tasks/start', {kind: HOME.kind, text, repo: REPO, issue: HOME.issue, base: HOME.base, mode: $('#hcdMode').value,
        model: $('#hcdModel')?.value || '', effort: $('#hcdEffort')?.value || '',
        images: HOME.files.filter(f => f.kind === 'image').map(f => ({name: f.name, data: f.data})), docs: HOME.files.filter(f => f.kind === 'text').map(f => ({name: f.name, text: f.text}))});
      HOME.files.forEach(f => f.url && URL.revokeObjectURL(f.url));
      Object.assign(HOME, {text: '', kind: 'auto', issue: 0, files: []}); line.value = '';      // sent: the box starts empty next time
      await load(); show('session', t.id);
    } catch (e) { toast(e.message, true); btn.disabled = false; }
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
      case 'bash': { const ok = s.rc === 0, lab = `<span class="hcd-sh">$ ${esc(s.cmd || '')}</span> · <span class="${ok ? 'add' : 'del'}">${s.timed_out ? 'timed out' : 'exit ' + esc(String(s.rc))}</span>${s.seconds ? ` · ${esc(String(s.seconds))} s` : ''}`;
        return s.tail && s.tail.length ? fold('b' + i, lab, `<pre class="hcd-term">${s.tail.map(x => esc(x)).join('\n')}</pre>`, 'row', verbose || !ok) : `<div class="hcd-step">${svg('list')}<span>${lab}</span>${at}</div>`; }
      case 'todo': return `<div class="hcd-todo">${(s.items || []).map(x => `<div class="hcd-td ${esc(x.status)}"><i aria-hidden="true">${x.status === 'completed' ? '✓' : x.status === 'in_progress' ? '●' : '○'}</i><span>${esc(x.content)}</span></div>`).join('')}</div>`;
      case 'compact': case 'ws': return `<div class="hcd-step dim">${svg('list')}<span>${esc(s.text || '')}</span>${at}</div>`;
      case 'wait': return `<div class="hcd-step">${svg('dot')}<span>${esc(s.text || 'Waiting for a free coding slot')}</span>${at}</div>`;
      case 'ckpt': return `<div class="hcd-step dim">${svg('ok')}<span>Checkpoint ${esc(String(s.n))} saved - you can go back to here</span>${at}</div>`;
      case 'rewind': return `<div class="hcd-step">${svg('list')}<span><b>Went back to checkpoint ${esc(String(s.n))}.</b> The working copy and the conversation are as they were then.</span>${at}</div>`;
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
    if (t.question) return ['need', 'Hoola needs your answer.', 'Nothing was changed. Type your answer below and it continues in this session.'];
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
    const sr = t.self_review || {}, pts = (sr.verdict && sr.verdict !== 'ok' ? sr.problems || [] : []).slice(0, 8), canFix = canRev(t);
    if (pts.length) parts.push(`<section class="hcd-card hcd-rev" aria-labelledby="hcdRevH"><div class="hcd-sh"><h2 id="hcdRevH">Hoola's own review</h2><span class="hcd-pill warn">${plural(pts.length, 'point')} left open</span></div>
      ${pts.map((x, i) => { const o = typeof x === 'string' ? {body: x} : x, where = o.path ? `${o.path}${o.line ? ':' + o.line : ''}` : '';
        return `<div class="hcd-cm"><div>${o.severity ? `<span class="hcd-pill ${o.severity === 'high' ? 'bad' : 'warn'}">${esc(o.severity)}</span>` : ''}${where ? `<code>${esc(where)}</code> ` : ''}${esc(o.body || o.text || o.problem || '')}</div>
          <div class="hcd-acts">${where ? `<button type="button" class="hcd-btn sm" data-act="walk" data-path="${esc(o.path)}">Show in diff</button>` : ''}${canFix ? `<button type="button" class="hcd-btn sm" data-act="fixone" data-i="${i}">Fix this one</button>` : ''}</div></div>`; }).join('')}
      ${canFix && pts.length > 1 ? `<div class="hcd-acts"><button type="button" class="hcd-btn pri" data-act="fixall">Fix all ${pts.length}</button></div>` : ''}</section>`);
    if ((t.file_diffs || []).length || t.diff) parts.push(`<button type="button" class="hcd-fold row" id="hcdFull" data-act="changes">${svg('chev', 'hcd-chev')}<span>See the full change · ${plural((t.files || []).length, 'file')}</span></button>`);
    if (t.risk) parts.push(`<p class="hcd-mut"><b>Risk:</b> ${esc(t.risk)}</p>`);
    const rc = recap(t), acts = actsFor(t); if (rc) parts.push(`<div class="hcd-recap ${rc[0]}"><span><b>${esc(rc[1])}</b> ${esc(rc[2])}</span>${acts.length ? `<div class="hcd-acts">${acts.join('')}</div>` : ''}</div>`);
    return parts.join('');
  }
  function feedHTML(t) {
    const steps = t.steps || [], inner = stepsHTML(t);
    const att = t.attach || []; let pi = 0;
    let h = `<div class="hcd-me">${esc(t.text || '')}${att.length ? `<div class="hcd-atts">${att.map(a => a.kind === 'image'
      ? `<img class="hcd-pic" data-att="${pi++}" alt="${esc(a.name)}" title="${esc(a.name)}"${PICS.has(t.id + ':' + (pi - 1)) ? ` src="${PICS.get(t.id + ':' + (pi - 1))}"` : ''}>`
      : `<span class="hcd-att">${svg('read')}<span>${esc(a.name)}</span><small>${kb(a.size)}</small></span>`).join('')}</div>` : ''}</div>`;
    if (t.running || P.view === 'verbose' || !steps.length) h += inner;
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
    // v0.784 a command run in the box counts as running her tests
    const bs = last('bash'), ck = last('check') || (bs ? {ok: bs.rc === 0} : null), ci = t.ci?.state, rows = [['Read the code', has('read', 'search', 'list', 'usages', 'rules') ? 'done' : 'todo', '']];
    if (t.kind !== 'explain') {
      rows.push(['Make the change', has('edit', 'new') ? 'done' : 'todo', '']);
      rows.push(['Run your tests', ck ? (ck.ok ? 'done' : 'bad') : has('check_off') ? 'off' : 'todo', ck ? (ck.ok ? 'passed' : 'failed') : has('check_off') ? 'could not run' : '']);
      rows.push(['Check its own change', has('diff') || t.self_review?.verdict ? 'done' : 'todo', '']);
      rows.push(['Pull request', t.pr_number ? 'done' : 'todo', t.pr_number ? `#${t.pr_number}` : '']);
      rows.push(['CI on GitHub', ci === 'success' ? 'done' : ci === 'failure' ? 'bad' : 'todo', (CI[ci] || ['', ''])[1] && t.pr_number ? CI[ci][1] : '']);
    }
    let far = -1; rows.forEach((r, i) => { if (r[1] === 'done') far = i; });      // a later stage is done, so the earlier ones happened
    rows.forEach((r, i) => { if (i < far && r[1] === 'todo') { if (r[0] === 'Run your tests') { r[1] = 'off'; r[2] = 'not run here'; } else r[1] = 'done'; } });
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
  function wsCard(t) {      // v0.784 the session's working copy: to-do, checkpoints (rewind), browse files
    const w = t.ws || {}; if (!w.exists) return '';
    const todos = w.todos || [], cps = (w.checkpoints || []).slice(-6).reverse();
    return `<section class="hcd-rc" aria-labelledby="hcdRcW"><h2 id="hcdRcW">Working copy${w.live ? '<span class="hcd-stat">working</span>' : ''}</h2>
      ${todos.length ? `<div class="hcd-todo">${todos.map(x => `<div class="hcd-td ${esc(x.status)}"><i aria-hidden="true">${x.status === 'completed' ? '✓' : x.status === 'in_progress' ? '●' : '○'}</i><span>${esc(x.content)}</span></div>`).join('')}</div>` : ''}
      ${cps.length ? cps.map(c => `<div class="hcd-row"><span title="${esc(c.label || '')}">Checkpoint ${c.n}</span><b>${esc((c.label || '').slice(0, 34))}</b>${!t.running && c.n !== (w.checkpoints || []).length ? `<button type="button" class="hcd-btn sm" data-act="rewind" data-n="${c.n}">Go back</button>` : ''}</div>`).join('') : '<p class="hcd-mut">A checkpoint is saved after every round.</p>'}
      ${(w.hidden || []).length ? `<p class="hcd-mut">${plural(w.hidden.length, 'file')} with secrets hidden from Hoola.</p>` : ''}
      <div class="hcd-acts"><button type="button" class="hcd-btn" data-act="files" data-path="">Browse files</button></div></section>`;
  }
  async function browse(path) {
    let r; try { r = await api('GET', `/api/devsahayak/tasks/${tid()}/files?path=${encodeURIComponent(path || '')}`); } catch (e) { return toast(e.message, true); }
    const up = (r.path || '').split('/').slice(0, -1).join('/');
    const head = `<h2>Working copy${r.path ? ' · <code>' + esc(r.path) + '</code>' : ''}</h2>${r.path ? `<button type="button" class="hcd-btn sm" data-act="files" data-path="${esc(up)}">← Up</button>` : ''}`;
    const html = r.entries ? `${head}<div class="hcd-tree">${r.entries.map(e => `<button type="button" class="hcd-file" data-act="files" data-path="${esc(e.path)}"><code>${esc(e.name)}${e.dir ? '/' : ''}</code><span>${e.changed ? `<em class="${e.changed === 'D' ? 'del' : 'add'}">${e.changed === 'A' ? 'new' : e.changed === 'D' ? 'deleted' : 'changed'}</em>` : ''}</span></button>`).join('') || '<p class="hcd-mut">Empty folder.</p>'}</div>`
      : `${head}<pre class="hcd-term tall">${esc(r.text || '')}</pre>`;
    const d = $('#hcdDlg'); const open = d.open;
    d.innerHTML = `<form method="dialog">${html}<div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button></div></form>`;
    if (!open) d.showModal();
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
        ${files.length ? files.map(f => `<button type="button" class="hcd-file" data-act="file" data-path="${esc(f.path)}" title="Open ${esc(f.path)} in Changes"><code>${esc(f.path)}</code><span><em class="add">+${f.added || 0}</em> <em class="del">−${f.removed || 0}</em></span></button>`).join('') : '<p class="hcd-mut">No changes yet.</p>'}
        ${t.pr_number ? `<div class="hcd-row"><span>Pull request</span><b>#${t.pr_number} · ${esc(STATUS[t.status] || t.status)}</b><button type="button" class="hcd-icb" data-menu="pr" aria-label="Pull request menu: auto-fix, checkout command" title="Pull request menu">${svg('more')}</button></div>` : ''}${checks.join('')}
        ${acts.length ? `<div class="hcd-acts">${acts.join('')}</div>` : ''}</section>
      ${wsCard(t)}
      <section class="hcd-rc" aria-labelledby="hcdRcP"><h2 id="hcdRcP">Progress</h2>${stages(t).map(([name, s, note]) => `<div class="hcd-stage ${s}">${sg[s]}<span>${name}</span><small>${esc(note)}</small></div>`).join('')}</section>
      <section class="hcd-rc" aria-labelledby="hcdRcS"><h2 id="hcdRcS">Session</h2>${kv('Repo', esc(t.repo || ''))}${t.branch ? kv('Branch', `<code>${esc(t.branch)}</code>`) : ''}
        ${t.base ? kv('Works from', `<code>${esc(t.base)}</code>`) : ''}${kv('Kind', esc((KINDS.find(k => k[0] === t.kind) || [0, t.kind])[1]))}
        ${t.mode ? kv('Mode', esc((MODES.find(m => m[0] === t.mode) || [0, t.mode])[1])) : ''}${t.tier ? kv('Job size', esc(t.tier)) : ''}
        ${kv('Model', esc(OV?.models?.forced ? OV.models.forced.model : ((OV?.models?.options || []).find(o => o.id === (t.model || OV?.models?.default)) || {label: t.model || 'server default'}).label) + (t.effort && !OV?.models?.forced ? ' · ' + esc(t.effort) : ''))}
        ${kv('Steps', String((t.steps || []).length))}${t.cost && t.cost.calls ? kv('Cost so far', `<span title="List price of this session's ${t.cost.calls} model calls - an estimate, not a bill">${rs(t.cost.inr)}</span>`) : ''}${kv('Started', esc(ago(t.at)))}</section>`;
  }

  // ------------------------------------------------------------------ session: mount once, paint what changed ---
  async function session(tid) {
    body(`<div class="hcd-sess-wrap"><main class="hcd-main">
        <header class="hcd-top" id="hcdTop"></header>
        <div class="hcd-feed" id="hcdFeed"><div class="hcd-col" id="hcdCol"><p class="hcd-mut">Opening…</p></div></div>
        <div class="hcd-queue" id="hcdQueue"></div>
        <div class="hcd-bar" id="hcdBar"></div>
        <div class="hcd-cc" id="hcdCc"></div>
        <form class="hcd-cp" id="hcdSteer"><label for="hcdNote" class="hcd-sr">Message Hoola</label>
          <textarea id="hcdNote" rows="1" maxlength="4000"></textarea><span class="hcd-cpb" id="hcdCpB"></span></form>
      </main><section class="hcd-pane" id="hcdPane" aria-label="Changes" hidden></section><aside class="hcd-rail" id="hcdRail" aria-label="Session details"></aside></div>`);
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
  function loadPics(t) {            // her own pictures, fetched with her sign-in (an <img> cannot send it) and kept for this visit
    EL.querySelectorAll('#hcdCol img[data-att]:not([src])').forEach(img => { const k = t.id + ':' + img.dataset.att;
      if (PICS.has(k)) { img.src = PICS.get(k); return; }
      PICS.set(k, '');
      api('GET', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}/attach/${img.dataset.att}`, undefined, {raw: true}).then(r => r.blob()).then(b => {
        const u = URL.createObjectURL(b); PICS.set(k, u); const now = EL.querySelector(`#hcdCol img[data-att="${img.dataset.att}"]`); if (now && TASK?.id === t.id) now.src = u; }).catch(() => PICS.delete(k)); });
  }
  const put = (id, key, html) => { if (SIG[key] === html) return false; const el = $(id); if (!el) return false; el.innerHTML = html; SIG[key] = html; return true; };
  function tick() { const c = $('#hcdClock'); if (c && TASK?.running && !TASK.stopping) c.textContent = `Working · ${dur((Date.now() - Date.parse(TASK.at)) / 1000)}`; }
  function paint() {
    const t = TASK; if (!t || !$('#hcdTop')) return;
    const files = editedFiles(t), railOn = railShown();
    put('#hcdTop', 'top', `<button type="button" class="hcd-title" data-act="rename" title="Rename">${esc(t.title || t.number)}</button>
      <button type="button" class="hcd-icb" data-menu="title" aria-label="Session menu: rename, transcript view, archive, delete" title="Session menu">${svg('down')}</button>
      <span class="hcd-flex"></span>
      ${t.running ? `<span class="hcd-live" id="hcdClock">${t.stopping ? 'Stopping after this step' : 'Working'}</span>` : `<span class="hcd-pill ${dotc(t)}">${esc(STATUS[t.status] || t.status)}</span>`}
      ${files.length ? `<button type="button" class="hcd-btn sm" data-act="changes" aria-pressed="${!!PANE}">Changes <span class="hcd-stat">${stat({files})}</span></button>` : ''}
      <button type="button" class="hcd-icb" data-act="rail" aria-pressed="${railOn}" aria-label="${railOn ? 'Hide' : 'Show'} session details" title="${railOn ? 'Hide' : 'Show'} session details">${svg('rail')}</button>`);
    tick();
    const feed = $('#hcdFeed'), atBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 80;
    if (put('#hcdCol', 'feed', feedHTML(t)) && atBottom) feed.scrollTop = feed.scrollHeight;
    loadPics(t);
    put('#hcdQueue', 'queue', (t.running ? (t.notes || []) : []).map((n, i) => `<div class="hcd-q"><span><b>Queued</b> ${esc(n)}</span><button type="button" class="hcd-icb" data-act="unq" data-i="${i}" aria-label="Take this message back" title="Take it back">${svg('x')}</button></div>`).join(''));
    put('#hcdBar', 'bar', barHTML(t));
    put('#hcdRail', 'rail', railHTML(t));
    drawPane(false);
    const canC = t.running || canRev(t);
    put('#hcdCc', 'cc', COMMENTS.length && canC ? `<div class="hcd-ccn"><span><b>${plural(COMMENTS.length, 'comment')}</b> will go with your next message</span><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-act="changes">View</button><button type="button" class="hcd-icb" data-act="cclear" aria-label="Remove the queued comments" title="Remove them">${svg('x')}</button></div>` : '');
    const mode = t.running ? 'note' : t.question ? 'answer' : t.status === 'plan_wait' ? 'plan' : canRev(t) ? 'revise' : 'off', f = $('#hcdSteer'), ta = $('#hcdNote');
    if (f.dataset.mode !== mode) { f.dataset.mode = mode; f.hidden = mode === 'off';
      ta.placeholder = {note: 'Message Hoola - it reads it before its next step', plan: 'Add a note for Hoola - it starts on the plan with your note',
        revise: 'Ask for a change - Hoola adds a commit to the same pull request', answer: 'Type your answer - Hoola continues this session', off: ''}[mode]; }
    put('#hcdCpB', 'cpb', t.running ? `<button type="button" class="hcd-stop" id="hcdStop" data-act="stop"${t.stopping ? ' disabled' : ''}>${svg('stop')}Stop</button>`
      : `<button type="submit" class="hcd-send" aria-label="Send" title="Send (Enter)">${svg('up')}</button>`);
  }
  function barHTML(t) {
    if (t.running) return '';
    if (t.question) return `<div class="hcd-ask2 col" id="hcdQ"><b>Hoola asks before it changes anything:</b><span>${esc(t.question)}</span></div>`;
    if (t.status === 'plan_wait') return `<div class="hcd-ask2"><b>Start on this plan?</b><span class="hcd-flex"></span><button type="button" class="hcd-btn" id="hcdCancel" data-act="cancel">Cancel job</button><button type="button" class="hcd-btn pri" id="hcdYes" data-act="yes">Yes, start</button></div>`;
    if (MERGE) { const a = MERGE; return `<div class="hcd-ask2 col"><div class="hcd-ask2r"><b>${esc(a.method)} merge PR #${a.pr_number} into ${esc(a.base)}?</b><span class="hcd-mut">commit <code>${esc(a.head_sha)}</code> · CI ${esc((CI[a.ci_state] || ['', a.ci_state])[1])}</span><span class="hcd-flex"></span>
        <button type="button" class="hcd-btn" data-act="mergeno">Not now</button><button type="button" class="hcd-btn ok" data-act="mergeyes">Merge</button></div>
        ${(a.notes || []).map(n => `<p class="hcd-mut">${esc(n)}</p>`).join('')}
        ${a.needs_force ? '<label class="hcd-f"><span>CI is not green - write why you still want to merge (8+ characters)</span><input id="hcdForce" maxlength="300"></label>' : ''}
        <p class="hcd-mut">If anything is pushed after this card, it goes stale and asks again.</p></div>`; }
    if (t.status === 'ready' && t.hash) return `<div class="hcd-ask2"><b>The change is ready. Open the pull request?</b><span class="hcd-flex"></span><button type="button" class="hcd-btn pri" id="hcdPush" data-act="push">Open the pull request</button></div>`;
    if (t.status === 'ci_running') return `<div class="hcd-ask2 soft"><span>Waiting for your CI on GitHub. ${t.auto_fix ? 'If it fails, Hoola fixes it and tries again.' : 'Auto-fix is off for this pull request, so a failure waits for you.'}</span><span class="hcd-flex"></span><button type="button" class="hcd-btn" data-act="refresh">Check now</button></div>`;
    if (!canRev(t) && !t.question) return `<div class="hcd-ask2 soft"><span>This session is finished.</span><span class="hcd-flex"></span><button type="button" class="hcd-btn" data-go="home">New session</button></div>`;
    return '';
  }

  // ------------------------------------------------------------------ session: what she can do ---
  const tid = () => encodeURIComponent(TASK.id);
  const busy = async (btn, fn) => { if (btn) btn.disabled = true; try { await fn(); } catch (e) { toast(e.message, true); } finally { if (btn && btn.isConnected) btn.disabled = false; } };   // a repaint draws the true state
  const again = async () => { await load(); drawSide(); await refreshTask(TASK.id, false); };
  async function sendMessage(text) {
    const ta = $('#hcdNote'), v = (text === undefined ? ta.value : text).trim(), mode = $('#hcdSteer').dataset.mode, t = TASK;
    const cs = mode === 'note' || mode === 'revise' ? COMMENTS : [];
    if (!t || mode === 'off' || (!v && !cs.length)) return;
    try {
      if (mode === 'note') { await api('POST', `/api/devsahayak/tasks/${tid()}/note`, {text: v, comments: cs}); }
      else if (mode === 'answer') { await api('POST', `/api/devsahayak/tasks/${tid()}/answer`, {text: v}); }
      else if (mode === 'plan') { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/plan_ok`, {hash: t.hash, note: v}); }
      else { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/revise`, {text: v, comments: cs}); }
      if (cs.length) { COMMENTS = []; DRAFT = null; SIG.pane = ''; }
      if (text === undefined) { ta.value = ''; grow(ta); }
      await again();
    } catch (e) { toast(e.message, true); }
  }

  // ------------------------------------------------------------------ the Changes pane ---
  function parseDiff(text) {
    const rows = []; let o = 0, n = 0;
    String(text || '').replace(/\n$/, '').split('\n').forEach(l => {
      if (l.startsWith('--- ') || l.startsWith('+++ ') || l.startsWith('\\')) return;
      const m = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(l);
      if (m) { o = +m[1]; n = +m[2]; rows.push({t: 'hunk', text: l}); }
      else if (l.startsWith('+')) rows.push({t: 'add', text: l.slice(1), o: '', n: n++});
      else if (l.startsWith('-')) rows.push({t: 'del', text: l.slice(1), o: o++, n: ''});
      else rows.push({t: 'ctx', text: l.slice(1), o: o++, n: n++});
    });
    return rows;
  }
  function paneFiles(t) {
    if (PANE?.cmp) return PANE.cmp.files;
    if ((t.file_diffs || []).length) return t.file_diffs;
    const by = {};                          // while it works: what the steps have shown so far (no line numbers yet)
    (t.steps || []).forEach(s => { if (s.k !== 'edit' && s.k !== 'new') return; const f = by[s.path] = by[s.path] || {path: s.path, added: 0, removed: 0, live: []};
      f.added += s.added || 0; f.removed += s.removed || 0; if (f.live.length) f.live.push({t: 'hunk', text: '…'});
      (s.diff || []).forEach(r => f.live.push({t: r.startsWith('+') ? 'add' : r.startsWith('-') ? 'del' : 'ctx', text: r.replace(/^[+-] ?/, ''), o: '', n: ''})); });
    return Object.values(by);
  }
  function paneHTML(t) {
    const files = paneFiles(t), f = files.find(x => x.path === PANE.path) || files[0], canC = t.running || canRev(t), pushed = !!(t.pr_number && t.branch);
    if (f) PANE.path = f.path;
    const all = f ? (f.live || parseDiff(f.diff)) : [], cap = f && !OPEN.has('all:' + f.path) && all.length > 600, rows = cap ? all.slice(0, 600) : all;
    PANE.rows = rows;
    const shown = new Set(), brs = BRANCHES[t.repo] || [];
    const line = (r, i) => { if (r.t === 'hunk') return `<div class="hcd-dl hunk"><span></span><i></i><i></i><code>${esc(r.text)}</code></div>`;
      let h = `<div class="hcd-dl ${r.t}">${canC && r.t !== 'del' ? `<button type="button" class="hcd-cadd" data-act="cadd" data-i="${i}" aria-label="Comment on ${r.n ? 'line ' + r.n : 'this line'}" title="Comment on this line">+</button>` : '<span></span>'}<i>${r.o}</i><i>${r.n}</i><code>${esc(r.text) || ' '}</code></div>`;
      if (r.t !== 'del') COMMENTS.forEach((c, k) => { if (shown.has(k) || c.path !== f.path || (c.line ? c.line !== r.n : c.code !== r.text.slice(0, 300))) return; shown.add(k);
        h += `<div class="hcd-cq"><span><b>You</b> · queued — ${esc(c.text)}</span><button type="button" class="hcd-icb" data-act="cdel" data-i="${k}" aria-label="Remove this comment" title="Remove">${svg('x')}</button></div>`; });
      if (DRAFT && DRAFT.path === f.path && DRAFT.i === i) h += `<form class="hcd-cbox" id="hcdCForm"><label class="hcd-sr" for="hcdCText">Your comment</label>
        <textarea id="hcdCText" rows="2" maxlength="1000" placeholder="Comment on ${r.n ? 'line ' + r.n : 'this line'} - it goes to Hoola with your next message"></textarea>
        <div class="hcd-acts"><span class="hcd-mut">Enter adds it · Esc cancels</span><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-act="ccancel">Cancel</button><button type="submit" class="hcd-btn sm pri">Add comment</button></div></form>`;
      return h; };
    return `<header class="hcd-ph"><b>Changes</b><span class="hcd-stat">${stat({files})}</span><span class="hcd-mut">· ${plural(files.length, 'file')}</span><span class="hcd-flex"></span>
        ${pushed ? `<label class="hcd-chip">Compare against <select id="hcdCmp" aria-label="Compare against"><option value="">this change</option>${brs.filter(b => b !== t.branch).map(b => `<option value="${esc(b)}"${PANE.base === b ? ' selected' : ''}>${esc(b)}</option>`).join('')}</select></label>` : ''}
        ${t.status === 'ready' && t.hash && !t.running ? `<button type="button" class="hcd-btn sm pri" data-act="push">Open the pull request</button>` : ''}
        <button type="button" class="hcd-icb" data-act="pclose" aria-label="Close the Changes pane" title="Close">${svg('x')}</button></header>
      ${PANE.cmp ? `<p class="hcd-pnote">${esc(t.branch)} against ${esc(PANE.cmp.base)} · ${PANE.cmp.ahead} commit(s) ahead, ${PANE.cmp.behind} behind · as GitHub computes it</p>` : t.running && !(t.file_diffs || []).length ? '<p class="hcd-pnote">Hoola is still working - these are the edits so far. Line numbers come when the change is prepared.</p>' : ''}
      <div class="hcd-pb"><nav class="hcd-pfs" aria-label="Changed files">${files.map(x => `<button type="button" class="hcd-file${f && x.path === f.path ? ' on' : ''}" data-act="file" data-path="${esc(x.path)}"><code>${esc(x.path)}</code><span><em class="add">+${x.added || 0}</em> <em class="del">−${x.removed || 0}</em></span></button>`).join('') || '<p class="hcd-mut">No changes.</p>'}</nav>
        <div class="hcd-dv" id="hcdDv">${f ? `<div class="hcd-dh"><code>${esc(f.path)}</code>${f.new ? '<span class="hcd-pill ok">new file</span>' : ''}${f.why ? `<span class="hcd-mut">${esc(f.why)}</span>` : ''}</div>${rows.map(line).join('')}
          ${cap ? `<button type="button" class="hcd-btn sm hcd-more" data-act="showall">Show all ${all.length} lines</button>` : ''}` : ''}</div></div>`;
  }
  function drawPane(force) {
    const el = $('#hcdPane'); if (!el) return;
    $('.hcd').dataset.pane = PANE ? 'on' : 'off'; el.hidden = !PANE;
    if (!PANE || !TASK) return;
    if (!force && DRAFT && $('#hcdCText')) return;        // she is writing a comment: never repaint under her
    const dv = $('#hcdDv'), top = dv ? dv.scrollTop : 0, html = paneHTML(TASK);
    if (SIG.pane === html) return;
    el.innerHTML = html; SIG.pane = html;
    const dv2 = $('#hcdDv'); if (dv2) dv2.scrollTop = top;
    $('#hcdCText')?.focus();
  }
  function openPane(path) {
    if (!TASK) return;
    if (!PANE) { PANE = {path: path || '', base: '', cmp: null, rows: []};
      if (P.side === 'open' && $('#hcdBody').clientWidth < 1100) { SIDE_AUTO = true; P.side = 'min'; drawSide(); }    // make room; it comes back on close
      const t = TASK; if (t.pr_number && !BRANCHES[t.repo]) api('GET', `/api/devsahayak/branches?repo=${encodeURIComponent(t.repo)}`).then(r => { BRANCHES[t.repo] = r.branches || []; drawPane(false); }).catch(() => { BRANCHES[t.repo] = []; }); }
    else if (path) PANE.path = path;
    DRAFT = null; SIG.top = ''; paint();
  }
  function closePane(quiet) {
    PANE = null; DRAFT = null; SIG.pane = '';
    if (SIDE_AUTO) { SIDE_AUTO = false; P.side = 'open'; if (!quiet) drawSide(); }
    if (!quiet) { SIG.top = ''; paint(); }
  }
  async function compareWith(base) {
    if (!PANE || !TASK) return;
    if (!base) { PANE.base = ''; PANE.cmp = null; return drawPane(true); }
    try { PANE.cmp = await api('GET', `/api/devsahayak/tasks/${tid()}/compare?base=${encodeURIComponent(base)}`); PANE.base = base; PANE.path = ''; }
    catch (e) { toast(e.message, true); PANE.base = ''; PANE.cmp = null; }
    DRAFT = null; drawPane(true);
  }
  function addComment() {
    const ta = $('#hcdCText'), v = ta ? ta.value.trim() : ''; if (!DRAFT || !v) return;
    COMMENTS.push({path: DRAFT.path, line: DRAFT.line, code: DRAFT.code, text: v}); DRAFT = null; SIG.pane = ''; paint();
  }
  const reviewPoints = () => { const sr = TASK?.self_review || {}; return (sr.verdict && sr.verdict !== 'ok' ? sr.problems || [] : []).slice(0, 8).map(x => typeof x === 'string' ? {body: x} : x); };
  const pointText = o => `${o.path ? o.path + (o.line ? ':' + o.line : '') + ' - ' : ''}${o.body || o.text || o.problem || ''}`;
  const ACTS = {
    side: () => { P.side = P.side === 'min' ? 'open' : 'min'; keep(); drawSide(); },
    rail: () => { P.rail = railShown() ? 'off' : ($('#hcdBody').clientWidth < 780 ? 'on' : 'auto'); keep(); $('.hcd').dataset.rail = P.rail; SIG.top = ''; paint(); },   // 'on' = an overlay she opened on a narrow window
    rename: () => askName(TASK),
    files: b => browse(b.dataset.path || ''),
    rewind: async b => { const n = +b.dataset.n;
      const r = await dialog(`<h2>Go back to checkpoint ${n}?</h2><p class="hcd-mut">The working copy and the conversation return to how they were then. Work after it is dropped here. Your pull request on GitHub is not changed until the next push.</p>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Go back</button></div>`);
      if (r !== 'ok') return; await busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/rewind`, {n}); await again(); toast(`Back at checkpoint ${n}.`); }); },
    unkind: () => { HOME.kind = 'auto'; drawTray(); },
    unissue: () => { HOME.issue = 0; drawTray(); },
    unfile: b => { const f = HOME.files.splice(+b.dataset.i, 1)[0]; if (f?.url) URL.revokeObjectURL(f.url); drawTray(); },
    changes: () => { PANE ? closePane() : openPane(''); },
    file: b => openPane(b.dataset.path),
    pclose: () => closePane(),
    walk: b => openPane(b.dataset.path),
    showall: () => { OPEN.add('all:' + PANE.path); drawPane(true); },
    cadd: b => { const r = PANE.rows[+b.dataset.i]; if (!r) return; DRAFT = {path: PANE.path, i: +b.dataset.i, line: r.n || 0, code: r.text.slice(0, 300)}; drawPane(true); },
    ccancel: () => { DRAFT = null; drawPane(true); },
    cdel: b => { COMMENTS.splice(+b.dataset.i, 1); SIG.pane = ''; paint(); },
    cclear: () => { COMMENTS = []; SIG.pane = ''; paint(); },
    fixone: b => busy(b, async () => { const o = reviewPoints()[+b.dataset.i]; if (o) await sendMessage('Fix this point from your own review: ' + pointText(o)); }),
    fixall: b => busy(b, async () => { await sendMessage('Fix every point from your own review:\n' + reviewPoints().map(o => '- ' + pointText(o)).join('\n')); }),
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
        ${sw('archive_after_merge', 'Archive a session when its pull request is merged', 'It stays under View all > Archived')}
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
