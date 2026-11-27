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

   PHASE 5 (the same plan): around the session. A Thinking view (the model's own thinking, kept per step), the passes
   that ran beside the main work (plan / own review / CI fix / reviewers' comments) as a card, people's comments on her
   pull request with "Fix them", a suggested next message as ghost text (Tab takes it), the Scheduled page (a task that
   starts by itself, Run now, history, a trigger address for her own program), and a read-only link to one session.
   With `shared` set, this file draws ONLY that read-only session: no sidebar, no box, no buttons that act.

   PHASE 6 (the same plan): per repo - what a command in the box may reach (no network / package registries + her hosts /
   any public site), keys that are added OUTSIDE the box for one host each, and GitHub events (a signed webhook) that
   may start a scheduled task. In the composer "+" > Add another repo: read it, or change it too (its own session and
   its own pull request). A key is typed only on the settings screen and is never shown again.

   HOOLA CHAT KIT (chatkit.js): the session's thread is the main chat's own thread. Her messages are its bubbles,
   Hoola's words are its replies (they land word by word when they arrive while she watches; what is already there is
   drawn whole), the working state is its ONE working row (the running step + the clock), and Copy / Read aloud sit
   under the newest reply. The step rows stay this page's own (diffs, test output, the Thinking / Verbose views): they
   sit inside the turn, in order, and fold into "Worked for" the moment words follow them. The thread is built once
   per session + view; a refresh only ADDS what is new (thread()).

   Nothing reaches GitHub from this page except through the existing tap routes (push / plan-ok / post / decide). */
window.HoolaCode = function ({api, esc, toast, standalone = false, shared = ''}) {
  let EL = null, VIEW = 'home', TID = '', OV = null, TASK = null, POLL = 0, KIND = 'fix', REPO = '', MERGE = null;
  let Q = '', ALL = {tab: 'active', q: '', rows: null, repo: ''}, SIG = {}, WIRED = null;
  const OPEN = new Set();                 // folds she opened (kept across repaints)
  let PANE = null;                        // the Changes pane: {path, base, cmp, rows} - null = closed
  let COMMENTS = [], DRAFT = null;        // her comments on lines, waiting for her next message; the one she is writing
  let SIDE_AUTO = false;                  // the sessions sidebar stepped aside for the pane (comes back when it closes)
  const BRANCHES = {};                    // repo -> its branches (for Compare against), fetched once
  const HOME = {text: '', kind: 'auto', issue: 0, base: '', mode: '', model: '', effort: '', files: [], refs: [], also: [], env: ''};
  let ENVS = {envs: [], auto: {id: 'auto', name: 'Auto', sub: 'Follows your repositories'}, pick: 'auto', net_on: false};   // v0.878 cloud environments   // the composer, kept while she looks elsewhere
  const PICS = new Map();                 // session id + index -> blob: link of a picture she attached
  const STYLE_NAME = {default: 'Default', explanatory: 'Explanatory', learning: 'Learning'};
  const MODES = [['ask', 'Ask first', 'Ask before the PR: shows the change and waits for your tap'], ['auto', 'Auto PR', 'Works and opens the PR (private repos only) - merging is always yours'],
    ['plan', 'Plan first', 'Plan first: no file is touched until you say yes'], ['steps', 'Ask each step', 'Asks before every command and every file edit, like Claude Code']];
  const SLASH = [['init', 'Write the repo\u2019s AGENTS.md'], ['plan', 'Plan first, wait for my OK'], ['fix', 'Fix a bug, with a test'], ['feature', 'Build a feature'], ['tests', 'Write tests'],
    ['docs', 'Write docs'], ['explain', 'Explain code, change nothing'], ['issue', 'Work on a GitHub issue: /issue 12'], ['review', 'Review a pull request: /review 12']];
  // v0.999.33 AI spend in credits (the server's rupee rate for a credit, from /api/credits), never rupees
  let RATE = 0.088;
  const rs = n => { const c = Math.round((+n || 0) / RATE); return (+n || 0) > 0 && c < 1 ? 'under 1 credit' : c.toLocaleString('en-US') + (c === 1 ? ' credit' : ' credits'); };
  const kb = n => n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1000)) + ' KB';
  const $ = s => EL && EL.querySelector(s);
  const P = (() => { let p = {}; try { p = JSON.parse(localStorage.getItem('hoola.code.ui') || '{}') || {}; } catch (e) { /* private window */ }
    return {side: p.side === 'min' ? 'min' : p.side === 'open' ? 'open' : (window.innerWidth < 760 ? 'min' : 'open'),   // a narrow window starts with the slim bar
      rail: ['on', 'off'].includes(p.rail) ? p.rail : 'auto',
      group: ['status', 'repo'].includes(p.group) ? p.group : 'none', show: ['run', 'need'].includes(p.show) ? p.show : 'all',
      view: ['verbose', 'thinking'].includes(p.view) ? p.view : 'normal'}; })();
  const keep = () => { try { localStorage.setItem('hoola.code.ui', JSON.stringify(P)); } catch (e) { /* fine without it */ } };

  const KINDS = [['fix', 'Fix a bug'], ['write', 'Build a feature'], ['tests', 'Write tests'], ['docs', 'Write docs'], ['explain', 'Explain code']];
  const STATUS = {new: 'Starting', plan_wait: 'Plan waits for your OK', ready: 'Ready - open the PR?', pr_open: 'PR open', ci_running: 'CI running',
    checks_failed: 'CI failed', merged: 'Merged', closed: 'PR closed', explained: 'Explained', refused: 'Stopped by a safety rule',
    failed: 'Could not finish', cancelled: 'Stopped'};
  const NEEDS = new Set(['plan_wait', 'ready', 'checks_failed', 'refused']);
  const CAN_REVISE = new Set(['pr_open', 'checks_failed', 'ready', 'refused']);
  const canRev = t => !shared && (CAN_REVISE.has(t.status) || !!t.can_continue);   // v0.784 a session with a working copy takes a follow-up, like a conversation
  const ICON = {
    repo: '<path d="M5 4h11l3 3v13H5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M9 4v5h6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    branch: '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 8v8M18 10c0 4-6 3-12 6"/></g>',
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
    stop: '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>',
    pr: '<circle cx="6" cy="6" r="2.4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="6" cy="18" r="2.4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="18" cy="18" r="2.4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M6 8.4v7.2M18 15.6V10a4 4 0 0 0-4-4h-2.5M13.5 3.5L11 6l2.5 2.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    clock: '<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    gear: '<circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
    stack: '<path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    back: '<path d="M10 6l-6 6 6 6M4 12h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    bug: '<rect x="8" y="7" width="8" height="12" rx="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9.5 7a2.5 2.5 0 0 1 5 0M4 13h4M16 13h4M5 8l3 2M19 8l-3 2M5 19l3-2M19 19l-3-2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    cloud: '<path d="M7 18h10.5a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.6 9.1 4.5 4.5 0 0 0 7 18z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    warn: '<path d="M12 4l9 16H3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4M12 17v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    pencil: '<path d="M4 20h4L19 9l-4-4L4 16z M13.5 6.5l4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    term: '<rect x="3" y="4.5" width="18" height="15" rx="2.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M7 10l3 2.5L7 15M12.5 15H17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    web: '<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3.5 12h17M12 3.5c2.5 2.6 2.5 14.4 0 17M12 3.5c-2.5 2.6-2.5 14.4 0 17" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    folder: '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    share: '<path d="M12 15V4M8 8l4-4 4 4M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    spark: '<path d="M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    auto: '<circle cx="6" cy="6" r="2.2" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="18" cy="6" r="2.2" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="6" cy="18" r="2.2" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="18" cy="18" r="2.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M8.2 6h7.6M6 8.2v7.6M18 8.2v7.6M8.2 18h7.6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>'};
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
  // v0.947 HOOLA AUTO (hoolaauto.js): whole client projects run by specialist agents, drawn into this page's body at #/auto/...
  const AUTO = !shared && window.HoolaAuto ? window.HoolaAuto({api, esc, toast, svg, nav: (v, t) => show(v, t), dialog: h => dialog(h),
    step: (s, t0, i) => stepHTML(s, t0, i, false)}) : null;

  async function load() {
    const ev = api('GET', '/api/devsahayak/envs').then(r => { ENVS = r; if (!HOME.env) HOME.env = r.pick || 'auto'; }).catch(() => {});
    try { OV = await api('GET', '/api/devsahayak'); } catch (e) { OV = {error: e.message, tasks: [], repos: [], reviews: [], actions: [], settings: {}}; }
    await ev;
    if (!REPO) REPO = OV.settings?.default_repo || OV.repos?.[0]?.repo || '';
    if (!TIERS && !shared) loadQuality();
    if (!shared && !qFresh.on) { qFresh.on = true; addEventListener('focus', qFresh); document.addEventListener('visibilitychange', qFresh); setInterval(qFresh, 60000);
      setInterval(sideFresh, 20000); }
  }
  // v0.999.245 the sessions list beside the work: other sessions finish / need her while she reads one - read the list
  // again every 20 s while the page is in front and redraw the sidebar only when something in it changed
  let SIDE_SIG = '';
  async function sideFresh() {
    if (document.visibilityState !== 'visible' || !OV || OV.error) return;
    let o; try { o = await api('GET', '/api/devsahayak'); } catch (e) { return; }
    const sig = JSON.stringify((o.tasks || []).map(t => [t.id, t.status, t.title, t.archived, t.running]));
    if (sig === SIDE_SIG) return;
    SIDE_SIG = sig; OV = o; drawSide();
  }
  // v0.999.33 WIRED: her credits go down as Hoola works - read them again when she comes back and every minute
  let Q_AT = 0;
  function qFresh() { if (document.visibilityState === 'visible' && Date.now() - Q_AT >= 20000 && (TASK || $('#hcdQual'))) loadQuality(); }
  // On its own page (/console/code) every screen has an address: #/s/<id>, #/reviews, #/settings, #/all - so Back works
  // and a link can open one session.
  const fromHash = () => { const m = /^#\/(s|reviews|settings|all|scheduled|auto)(?:\/(.+))?$/.exec(location.hash || '');
    return !m ? ['home', ''] : m[1] === 's' ? ['session', decodeURIComponent(m[2] || '')] : ['scheduled', 'auto'].includes(m[1]) ? [m[1], decodeURIComponent(m[2] || '')] : [m[1], '']; };
  const toHash = (view, tid) => view === 'session' && tid ? '#/s/' + encodeURIComponent(tid) : view === 'scheduled' && tid ? '#/scheduled/' + encodeURIComponent(tid)
    : view === 'auto' ? '#/auto' + (tid ? '/' + tid.split('/').map(encodeURIComponent).join('/') : '') : view === 'home' ? '#/' : '#/' + view;
  async function open(root) { EL = root || EL; if (!EL) return; clearInterval(POLL); if (shared) return openShared(); await load(); shell();
    if (standalone && location.search) { const u = new URLSearchParams(location.search), g = k => (u.get(k) || '').trim();   // a link may pre-fill the box; it never starts anything
      HOME.text = (g('prompt') || g('q')).slice(0, 20000); HOME.base = g('branch').slice(0, 100); if (MODES.some(m => m[0] === g('mode'))) HOME.mode = g('mode');
      const r = g('repo') || g('repositories').split(',')[0], en = g('environment').toLowerCase();
      const fe = (ENVS.envs || []).find(e => e.id === en || e.name.toLowerCase() === en); if (fe) HOME.env = fe.id; else if (en === 'auto') HOME.env = 'auto'; if ((OV.repos || []).some(x => x.repo === r)) REPO = r;
      history.replaceState(null, '', location.pathname + location.hash); }
    if (standalone) { [VIEW, TID] = fromHash(); window.addEventListener('hashchange', () => { const [v, t] = fromHash(); if (v !== VIEW || t !== TID) show(v, t); }); }
    show(VIEW, TID); }
  function leave() { clearInterval(POLL); liveClose(); window.HoolaMenu?.close(); dropThread(); }

  function show(view, tid) {
    if (VIEW === 'home') keepHome();
    if ((tid || '') !== TID || view !== 'session') { COMMENTS = []; DRAFT = null; if (PANE) closePane(true); }
    VIEW = view; TID = tid || ''; clearInterval(POLL); liveClose(); MERGE = null; SIG = {}; window.HoolaMenu?.close(); AUTO?.leave(); dropThread();
    if (standalone && location.hash !== toHash(VIEW, TID) && !(VIEW === 'home' && !location.hash)) location.hash = toHash(VIEW, TID);
    if (standalone) document.title = VIEW === 'session' ? 'Hoola Code' : ({reviews: 'Review a PR', settings: 'Settings', all: 'All sessions', scheduled: 'Scheduled tasks', auto: 'Hoola Auto'}[VIEW] || 'Hoola Code') + (VIEW === 'home' ? '' : ' · Hoola Code');
    drawSide();
    AUTO?.refresh().then(ch => { if (ch) drawSide(); });       // v0.947 the sidebar's Hoola Auto row + projects
    if (view === 'auto' && AUTO) return AUTO.draw(TID, $('#hcdBody'));
    const bd = $('#hcdBody'); if (bd) { bd.classList.add('hcd-enter'); clearTimeout(show._t); show._t = setTimeout(() => bd.classList.remove('hcd-enter'), 320); }   // a page comes in once; a later repaint does not move
    if (view === 'session' && TID) return session(TID);
    if (view === 'reviews') return reviews();
    if (view === 'settings') return settings();
    if (view === 'all') return allSessions();
    if (view === 'scheduled') return scheduled();
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
    if (!window.__hcdEsc) { window.__hcdEsc = true; document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !EL.contains(ev.target)) onKey(ev); }); }
    EL.addEventListener('change', ev => { const t = ev.target;
      if (t.id === 'hcdCmp') compareWith(t.value);
      else if (t.id === 'hcdFile') { addFiles(t.files); t.value = ''; }
      else if (t.name === 'event' && t.form && t.form.id === 'hcdSchedF') schedFields(t.form)
      ; });
    EL.addEventListener('paste', ev => { if (ev.target.id !== 'hcdLine') return; const fs = [...(ev.clipboardData?.files || [])]; if (fs.length) { ev.preventDefault(); addFiles(fs); } });
    EL.addEventListener('dragover', ev => { if (ev.target.closest?.('#hcdAsk')) ev.preventDefault(); });
    EL.addEventListener('drop', ev => { if (!ev.target.closest?.('#hcdAsk')) return; ev.preventDefault(); addFiles(ev.dataTransfer?.files || []); });
    if (window.ResizeObserver) new ResizeObserver(() => { const b = $('[data-act="rail"]'); if (!b) return; const on = railShown();   // the window got narrower / wider: the button tells the truth
      b.setAttribute('aria-pressed', String(on)); b.title = `${on ? 'Hide' : 'Show'} session details`; b.setAttribute('aria-label', b.title); }).observe($('#hcdBody'));
    EL.addEventListener('input', envForm); EL.addEventListener('change', envForm);
    EL.addEventListener('input', ev => { if (ev.target.id === 'hcdSearch') { Q = ev.target.value; drawList(); } if (ev.target.id === 'hcdNote') { grow(ev.target); pickFor(ev.target); } });
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
        ${AUTO ? `<button type="button" class="hcd-icb${VIEW === 'auto' ? ' on' : ''}" data-auto="" aria-label="Hoola Auto" title="Hoola Auto">${svg('auto')}</button>` : ''}
        <button type="button" class="hcd-icb" data-act="find" aria-label="Search sessions" title="Search sessions">${svg('search')}</button>
        ${ts.map(t => `<button type="button" class="hcd-icb" data-tid="${esc(t.id)}" title="${esc(t.title || t.number)}" aria-label="${esc(t.title || t.number)}"><i class="hcd-dot ${dotc(t)}"></i></button>`).join('')}`;
      return;
    }
    // v0.914 the sidebar as in the approved design (docs/design/hoola_code/Sidebar.dc.html): mark + name, search and
    // collapse; New session / Search / Scheduled / Reviews / Environments; Recents with their status marks; you + settings.
    const nSched = (OV?.schedules || []).filter(x => x.enabled).length, who = (OV?.settings?.login || 'You');
    const aps = AUTO ? AUTO.cached() : [], aNeed = aps.filter(x => x.state === 'need').length, apid = VIEW === 'auto' ? TID.split('/')[0] : '';
    const aMark = x => x.state === 'need' ? `<span class="hcd-mk need" role="img" aria-label="Needs you">${svg('warn')}</span>` : x.state === 'run' ? '<span class="hcd-mk run" role="img" aria-label="Agents working"><i></i></span>'
      : x.state === 'done' ? `<span class="hcd-mk hca-okmk" role="img" aria-label="Handed over">${svg('ok')}</span>` : '';
    const aGroup = aps.length ? `<div class="hcd-lbl"><span>Hoola Auto</span></div>${aps.slice(0, 8).map(x => `<div class="hcd-sess${x.id === apid ? ' on' : ''}"><button type="button" class="hcd-sessb" data-auto="${esc(x.id)}" title="${esc(x.phase_label)}">
      <span class="hcd-st"><span>${esc(x.name)}</span></span></button><span class="hcd-marks">${x.state === 'run' || x.state === 'intake' ? `<small class="hca-sp">${esc(x.pct)}%</small>` : ''}${aMark(x)}</span></div>`).join('')}` : '';
    side.innerHTML = `<div class="hcd-sh">${standalone ? '<img class="hcd-mark" src="/static/hoola-mark.png" alt="" width="24" height="24">' : ''}<b class="hcd-brand">Hoola Code</b><span class="hcd-flex"></span>
        <button type="button" class="hcd-icb" data-act="find" aria-label="Search sessions" title="Search sessions">${svg('search')}</button>
        <button type="button" class="hcd-icb" data-act="side" aria-label="Collapse the sessions sidebar" title="Collapse sidebar">${svg('side')}</button></div>
      <div class="hcd-navs">
        <button type="button" class="hcd-new${VIEW === 'home' ? ' on' : ''}" data-go="home">${svg('new')}<span>New session</span></button>
        ${AUTO ? `<button type="button" class="hcd-nav${VIEW === 'auto' ? ' on' : ''}" data-auto="">${svg('auto')}<span>Hoola Auto</span>${aNeed ? `<span class="hcd-count hca-cnt">${aNeed}</span>` : ''}</button>` : ''}
        <button type="button" class="hcd-nav${VIEW === 'all' ? ' on' : ''}" data-go="all">${svg('search')}<span>Search</span></button>
        <button type="button" class="hcd-nav${VIEW === 'scheduled' ? ' on' : ''}" data-go="scheduled">${svg('clock')}<span>Scheduled</span>${nSched ? `<span class="hcd-count">${nSched}</span>` : ''}</button>
        <button type="button" class="hcd-nav${VIEW === 'reviews' ? ' on' : ''}" data-go="reviews">${svg('pr')}<span>Reviews</span></button>
        <button type="button" class="hcd-nav" data-act="envs">${svg('cloud')}<span>Environments</span></button>
        ${standalone ? `<button type="button" class="hcd-nav" data-menu="more">${svg('more')}<span>More</span></button>` : ''}
      </div>
      <label class="hcd-sr" for="hcdSearch">Search sessions</label><input id="hcdSearch" class="hcd-search" type="search" placeholder="Search sessions" value="${esc(Q)}" autocomplete="off"${Q || P.find ? '' : ' hidden'}>
      ${aGroup}
      <div class="hcd-list" id="hcdList"></div>
      <span class="hcd-flex"></span>
      <div class="hcd-me-row"><span class="hcd-av" aria-hidden="true">${esc(who.charAt(0).toUpperCase())}</span><span class="hcd-who">${esc(who)}</span>
        <button type="button" class="hcd-icb${VIEW === 'settings' ? ' on' : ''}" data-go="settings" aria-label="Settings" title="Settings">${svg('gear')}</button></div>`;
    drawList();
  }
  // one line per session, like the design: the name, then its marks (pull request, working, needs you), the cloud
  const marks = t => `${t.pr_number && ['pr_open', 'checks_failed', 'ci_running'].includes(t.status) ? `<span class="hcd-mk pr" role="img" aria-label="Pull request open">${svg('pr')}</span>` : ''}${isRun(t)
    ? '<span class="hcd-mk run" role="img" aria-label="Working"><i></i></span>' : needsYou(t) ? `<span class="hcd-mk need" role="img" aria-label="Needs you">${svg('warn')}</span>` : ''}<span class="hcd-mk cl" role="img" aria-label="Cloud session">${svg('cloud')}</span>`;
  const row = t => `<div class="hcd-sess${t.id === TID && VIEW === 'session' ? ' on' : ''}"><button type="button" class="hcd-sessb" data-tid="${esc(t.id)}" title="${esc((t.repo || '') + ' · ' + sub(t) + ' · ' + ago(t.updated || t.at))}">
      <span class="hcd-st"><span>${esc(t.title || t.number)}</span></span></button>
      <span class="hcd-marks">${marks(t)}</span>
      <button type="button" class="hcd-icb hcd-rowm" data-menu="row" data-id="${esc(t.id)}" aria-label="More for ${esc(t.title || t.number)}">${svg('more')}</button></div>`;
  function drawList() {
    const box = $('#hcdList'); if (!box) return;
    const q = Q.trim().toLowerCase();
    let ts = (OV?.tasks || []).filter(t => !q || `${t.title} ${t.repo} ${t.number}`.toLowerCase().includes(q));
    if (P.show !== 'all') ts = ts.filter(t => group(t) === P.show);
    const head = (name, first) => `<div class="hcd-lbl"><span>${esc(name)}</span>${first ? `<button type="button" class="hcd-icb" data-menu="group" aria-label="Group and sort" title="Group and sort">${svg('sort')}</button>` : ''}</div>`;
    let out = '';
    if (!ts.length) out = head('Recents', true) + `<p class="hcd-mut hcd-none">${q || P.show !== 'all' ? 'No sessions match.' : 'No sessions yet.'}</p>`;
    else if (P.group === 'repo') {
      const by = new Map(); ts.forEach(t => { const k = (t.repo || '').split('/')[1] || t.repo || 'No repo'; (by.get(k) || by.set(k, []).get(k)).push(t); });
      let first = true; by.forEach((list, k) => { out += head(k, first) + list.map(row).join(''); first = false; });
    } else if (P.group === 'status') {
      let first = true; [['run', 'Running'], ['need', 'Needs you'], ['old', 'Earlier']].forEach(([g, name]) => { const list = ts.filter(t => group(t) === g);
        if (list.length) { out += head(name, first) + list.map(row).join(''); first = false; } });
    } else out = head('Recents', true) + ts.map(row).join('');
    box.innerHTML = out;
  }

  // ------------------------------------------------------------------ dialogs + menus ---
  function dialog(html) {
    const d = $('#hcdDlg'); d.innerHTML = `<form method="dialog">${html}</form>`;
    return new Promise(res => { d.addEventListener('close', () => { res(d.returnValue);
      setTimeout(() => { if (!d.open) d.innerHTML = ''; }, 0); }, {once: true});      // a closed dialog keeps nothing (a one-time token or secret must not stay in the page)
      d.returnValue = ''; d.showModal(); });
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
    const views = [{header: 'Transcript view'},
      {label: 'Normal', sub: 'Steps folded into summaries', checked: P.view === 'normal', run: () => setView('normal')},
      {label: 'Thinking', sub: "Also what Hoola thought before each step", checked: P.view === 'thinking', run: () => setView('thinking')},
      {label: 'Verbose', sub: 'Every step, every diff, and the thinking', checked: P.view === 'verbose', run: () => setView('verbose')}];
    if (shared) return HoolaMenu.open(btn, views, {align: 'start', label: 'Transcript view', width: 270});
    const items = [{label: 'Rename', icon: 'pencil', run: () => askName(t)}];
    if (inSession) items.push({label: 'Cloud environment…', icon: 'gear', sub: (t.env?.name || 'Auto') + ' · applies from the next message', run: () => envMenu(btn, t)});
    if (inSession) items.push({label: 'Terminal', icon: 'braces', sub: 'Commands running in the background', run: () => openTerm()},
      {label: 'Compact the conversation', icon: 'doc', sub: '/compact - summarise it so far, your words kept', disabled: isRun(t), run: () => compactNow()},
      {label: 'Write AGENTS.md', icon: 'pencil', sub: '/init - the repo\u2019s rules for coding agents', disabled: isRun(t), run: () => initNow()},
      {label: 'Fork this session', icon: 'restore', sub: 'A copy to try another way', disabled: isRun(t), run: () => forkNow(0)},
      {label: 'This repo\u2019s Claude Code setup', icon: 'gear', sub: '.claude/ commands, agents, skills, hooks, MCP', run: () => repoSetup()},
      {label: 'Edit Claude Code files…', icon: 'pencil', sub: 'Agents, commands, skills, hooks, rules, CLAUDE.md', disabled: isRun(t), run: () => claudeFiles()},
      {label: 'Output style…', icon: 'spark', sub: (STYLE_NAME[t.style || ''] || t.style || 'Default') + ' · how Hoola explains its work', run: () => styleMenu(btn)},
      {label: 'Plugins…', icon: 'plus', sub: 'Add commands, agents and hooks from GitHub', run: () => pluginsDlg()},
      {label: 'Export the conversation', icon: 'doc', sub: '/export - download it as a Markdown file', run: () => exportNow()});
    if (inSession) items.push(...views, {sep: true}, {label: t.share?.on ? 'Read-only link…' : 'Share a read-only link…', icon: 'doc', sub: t.share?.on ? 'On - anyone with the link can read this session' : '', disabled: isRun(t), run: () => shareDialog(t)});
    if (inSession && (t.branch || t.pr_url)) items.push({header: 'Open in'});
    if (inSession && t.branch && t.pr_number) items.push({label: 'Copy checkout command', icon: 'braces', sub: `git checkout ${t.branch}`, run: async () => { const cmd = `git fetch origin ${t.branch} && git checkout ${t.branch}`;
      try { await navigator.clipboard.writeText(cmd); toast('Copied: ' + cmd); } catch (e) { toast(cmd); } }});
    if (t.pr_url) items.push(inSession ? {label: 'GitHub', icon: 'doc', sub: `Pull request #${t.pr_number}`, run: () => window.open(t.pr_url, '_blank', 'noopener')} : {sep: true}, ...(inSession ? [] : [{label: 'Open the pull request on GitHub', icon: 'doc', run: () => window.open(t.pr_url, '_blank', 'noopener')}]));
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
  // ------------------------------------------------------------------ v0.878 cloud environments (Claude Code's environment selector) ---
  const LEVEL = {none: 'No network', limited: 'Limited network', full: 'Full network'};
  const envName = id => !id || id === 'auto' ? 'Auto' : ((ENVS.envs || []).find(e => e.id === id)?.name || 'Auto');
  function envMenu(btn, t) {
    if (!window.HoolaMenu) return;
    const cur = t ? (t.env?.id || 'auto') : (HOME.env || 'auto');
    const pick = id => async () => {
      if (!t) { HOME.env = id; if (VIEW === 'home') { keepHome(); home(); } return; }
      try { await api('PUT', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}/env`, {env: id}); toast(`${envName(id)} from the next message.`); await refreshTask(t.id, false); }
      catch (e) { toast(e.message, true); } };
    const items = [{header: 'Cloud environments'},
      {label: 'Auto', sub: 'Follows your repositories', icon: 'cloud', checked: cur === 'auto', run: pick('auto')},
      ...(ENVS.envs || []).filter(e => !e.archived).map(e => ({label: e.name, icon: 'cloud', checked: cur === e.id,
        sub: LEVEL[e.net.level] + (e.net.on || e.net.level === 'none' ? '' : ' (not on yet)') + (e.setup ? ' · setup script' : ''), run: pick(e.id)})),
      {sep: true}];
    const mine = (ENVS.envs || []).find(e => e.id === cur);
    if (mine) items.push({label: `Edit ${mine.name}…`, icon: 'gear', run: () => envDialog(mine)});
    items.push({label: 'New environment…', icon: 'new', run: () => envDialog(null)});
    HoolaMenu.open(btn, items, {align: 'start', label: 'Cloud environment', width: 290});
  }
  async function envDialog(e) {
    if (e && !e.id) e = {...e, _new: true};
    const isNew = !e || e._new;
    const n = e?.net || {level: 'limited', pkgs: true, hosts: []}, vars = Object.entries(e?.env_vars || {}).map(([k, v]) => `${k}=${v}`).join('\n');
    const lv = (k, title, sub) => `<label class="hcd-envlv"><input type="radio" name="hcdEnvLv" value="${k}"${n.level === k ? ' checked' : ''}><span><b>${title}</b><small>${sub}</small></span></label>`;
    const wait = dialog(`<h2>${!isNew ? 'Edit environment' : 'New environment'}</h2>
      <p class="hcd-mut">Cloud environments are where Hoola Code runs your repo's commands. You can change them any time.</p>
      <div class="hcd-envcols"><div class="hcd-envcol">
      <label class="hcd-lab" for="hcdEnvName">Name</label><input id="hcdEnvName" maxlength="60" value="${esc(e?.name || '')}" placeholder="Default" autocomplete="off">
      <fieldset class="hcd-envnet"><legend class="hcd-lab">Network access</legend>
        ${lv('none', 'None', 'Sessions cannot reach the internet.')}${lv('limited', 'Limited <em class="hcd-rec">Recommended</em>', 'Sessions reach only what you allow below.')}${lv('full', 'Full', 'Sessions can reach any public site.')}
        <div id="hcdEnvLim"${n.level === 'limited' ? '' : ' hidden'}>
          <label class="hcd-chk"><input type="checkbox" id="hcdEnvPkgs"${n.pkgs !== false ? ' checked' : ''}> Allow package managers (PyPI, npm, Maven, crates, Go, RubyGems…)</label>
          <label class="hcd-lab" for="hcdEnvHosts">Allowed domains <small>one per line, *.example.com for subdomains</small></label>
          <textarea id="hcdEnvHosts" rows="3" spellcheck="false">${esc((n.hosts || []).join('\n'))}</textarea></div>
        ${ENVS.net_on ? '' : '<p class="hcd-mut">The network is not switched on for this server yet, so commands run offline until the server check passes. Your choice is kept.</p>'}
      </fieldset></div><div class="hcd-envcol">
      <label class="hcd-lab" for="hcdEnvVars">Environment variables <small>.env format, one NAME=value per line - never keys or passwords</small></label>
      <textarea id="hcdEnvVars" rows="3" spellcheck="false" placeholder="NODE_ENV=test">${esc(vars)}</textarea>
      <label class="hcd-lab" for="hcdEnvSetup">Setup script <small>runs once with the network, before the first command, and is cached</small></label>
      <textarea id="hcdEnvSetup" rows="4" spellcheck="false" placeholder="pip install -r requirements.txt">${esc(e?.setup || '')}</textarea>
      <p class="hcd-mut">Keys for an outside API are added in Settings &gt; Repositories &gt; Keys added outside the box: the proxy adds them after the request leaves the box, so Hoola never sees them.</p></div></div>
      <div class="hcd-dlgb">${!isNew ? '<button class="hcd-btn danger" value="archive" formnovalidate>Archive</button><span class="hcd-flex"></span>' : ''}<button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">${!isNew ? 'Save changes' : 'Create'}</button></div>`);
    envForm({target: $('#hcdEnvName')});
    const r = await wait;
    if (r === 'archive' && !isNew) { try { await api('POST', `/api/devsahayak/envs/${encodeURIComponent(e.id)}/archive`); toast(`${e.name} archived. Sessions already in it keep running.`);
      if (HOME.env === e.id) HOME.env = 'auto'; await load(); if (VIEW === 'home') home(); else if (VIEW === 'settings') settings(); } catch (err) { toast(err.message, true); } return; }
    if (r !== 'ok') return;
    const body = {name: (FORM.name || '').trim() || 'Default', net: {level: FORM.level, pkgs: FORM.pkgs, hosts: FORM.hosts}, env_vars: FORM.vars, setup: FORM.setup};
    try { const out = !isNew ? await api('PATCH', `/api/devsahayak/envs/${encodeURIComponent(e.id)}`, body) : await api('POST', '/api/devsahayak/envs', body);
      toast(!isNew ? 'Saved.' : `${out.name} created.`); if (isNew) HOME.env = out.id; await load(); if (VIEW === 'home') home(); else if (VIEW === 'settings') settings(); }
    catch (err) { toast(err.message, true); envDialog({...(e || {}), id: isNew ? '' : e.id, name: body.name, net: {level: body.net.level, pkgs: body.net.pkgs, hosts: (body.net.hosts || '').split(/\s+/).filter(Boolean)},
      env_vars: Object.fromEntries((body.env_vars || '').split('\n').filter(x => x.includes('=')).map(x => [x.split('=')[0], x.slice(x.indexOf('=') + 1)])), setup: body.setup}); }
  }
  let FORM = {};     // the environment dialog's fields, read as she types (a closed dialog empties itself)
  function envForm(ev) {
    const d = ev.target.closest('#hcdDlg'); if (!d || !$('#hcdEnvName')) return;
    if (ev.target.name === 'hcdEnvLv') { const lim = $('#hcdEnvLim'); if (lim) lim.hidden = ev.target.value !== 'limited'; }
    FORM = {name: $('#hcdEnvName').value, level: (d.querySelector('input[name=hcdEnvLv]:checked') || {}).value || 'limited', pkgs: !!$('#hcdEnvPkgs')?.checked,
      hosts: $('#hcdEnvHosts')?.value || '', vars: $('#hcdEnvVars')?.value || '', setup: $('#hcdEnvSetup')?.value || ''};
  }
  function setView(v) { P.view = v; keep(); paint(); }      // thread() sees the view changed and draws it again, whole
  function moreMenu(btn) {
    if (!window.HoolaMenu) return;
    HoolaMenu.open(btn, [{label: 'All sessions', icon: 'doc', run: () => show('all')}, {label: 'Settings', icon: 'gear', run: () => show('settings')},
      {sep: true}, {label: 'Back to Hoola', icon: 'restore', run: () => { location.href = '/console/'; }}], {align: 'start', label: 'More', width: 220});
  }

  // ------------------------------------------------------------------ one listener ---
  function onClick(ev) {
    const b = ev.target.closest('[data-act],[data-go],[data-tid],[data-fold],[data-menu],[data-kind],[data-auto]'); if (!b || !EL.contains(b)) return;
    if (b.dataset.auto !== undefined && !b.disabled) { ev.preventDefault(); return show('auto', b.dataset.auto); }   // v0.947 HOOLA AUTO
    if (b.dataset.menu) { ev.preventDefault();
      if (b.dataset.menu === 'group') return groupMenu(b);
      if (b.dataset.menu === 'title' || b.dataset.menu === 'smenu') return taskMenu(b, TASK, true);
      if (b.dataset.menu === 'pr') return prMenu(b);
      if (b.dataset.menu === 'plus') return plusMenu(b);
      if (b.dataset.menu === 'env') return envMenu(b, null);
      if (b.dataset.menu === 'repo') return repoMenu(b);
      if (b.dataset.menu === 'base') return baseMenu(b);
      if (b.dataset.menu === 'mode') return modeMenu(b);
      if (b.dataset.menu === 'smode') return sessModeMenu(b);
      if (b.dataset.menu === 'tier') return tierMenu(b);
      if (b.dataset.menu === 'senv') return envMenu(b, TASK);
      if (b.dataset.menu === 'more') return moreMenu(b);
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
    else if (f.id === 'hcdSchedF') { ev.preventDefault(); newSchedule(f); }
    else if (f.id === 'hcdAllF') { ev.preventDefault(); ALL.q = $('#hcdAllQ').value.trim(); ALL.rows = null; allSessions(); }
  }
  function onKey(ev) {
    if (PICK && ev.target.id === 'hcdNote' && (ev.key === 'Tab' || (ev.key === 'Enter' && !ev.shiftKey))) { ev.preventDefault(); return pickTake(0); }
    if (PICK && ev.key === 'Escape') { ev.preventDefault(); return pickClose(); }
    if (ev.key === 'Escape' && VIEW === 'session' && TASK?.running && !TASK.stopping && !shared && !(ev.target.value || '').trim()
        && !EL.querySelector('dialog[open]')) { const b = $('#hcdStop'); if (b) { ev.preventDefault(); return ACTS.stop(b); } }   // v0.999 Esc stops, like Claude Code
    if (ev.key === 'Escape' && ev.target.id === 'hcdCText') { ev.preventDefault(); return ACTS.ccancel(); }
    if (ev.key === 'Tab' && !ev.shiftKey && ev.target.id === 'hcdNote' && !ev.target.value && ev.target.dataset.hint) {    // the suggestion: Tab takes it, she can still edit it
      ev.preventDefault(); ev.target.value = ev.target.dataset.hint; grow(ev.target); return; }
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
    const short = r => r.split('/')[1] || r;
    HOME.refs.forEach(r => chips.push(`<span class="hcd-att">Reads ${esc(short(r))}<button type="button" class="hcd-icb" data-act="unref" data-repo="${esc(r)}" aria-label="Do not use ${esc(short(r))}">${svg('x')}</button></span>`));
    HOME.also.forEach(r => chips.push(`<span class="hcd-att">Also changes ${esc(short(r))}<button type="button" class="hcd-icb" data-act="unref" data-repo="${esc(r)}" aria-label="Do not use ${esc(short(r))}">${svg('x')}</button></span>`));
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
    const others = (OV?.repos || []).filter(r => r.repo !== REPO);
    HoolaMenu.open(btn, [{label: 'Add files or photos', icon: 'doc', sub: 'Screenshots, logs, code - or paste / drop them', run: () => $('#hcdFile')?.click()},
      ...(others.length ? [{label: 'Add another repo…', icon: 'braces', sub: 'Let Hoola read it, or change it too', run: () => otherRepos()}] : []), {header: 'Slash commands'},
      ...SLASH.map(([c, d]) => ({label: '/' + c, sub: d, run: () => { if (c === 'issue' || c === 'review') { const l = $('#hcdLine'); l.value = `/${c} ` + l.value; l.focus(); l.setSelectionRange(c.length + 2, c.length + 2); } else slash(c, ''); }}))],
      {align: 'start', place: 'above', label: 'Add', width: 300});
  }
  /* A slash command sets something and leaves her words alone. Returns the words that are left, or null when it did the whole job. */
  const INIT_ASK = 'Read this repository and write AGENTS.md at the root (improve CLAUDE.md / AGENTS.md if one exists): what the project is, how to install, build, run, test and lint it (check each command), the layout, the code style, and rules a newcomer must not break. Change no other file.';
  function slash(cmd, rest) {
    const kinds = {fix: 'fix', feature: 'write', tests: 'tests', test: 'tests', docs: 'docs', explain: 'explain'};
    if (cmd === 'init') { HOME.kind = 'docs'; return rest || INIT_ASK; }
    if (cmd === 'plan') { HOME.mode = 'plan'; const m = $('#hcdModeBtn span'); if (m) m.textContent = (MODES.find(x => x[0] === 'plan') || [0, 'Plan first'])[1]; }
    else if (kinds[cmd]) HOME.kind = kinds[cmd];
    else if (cmd === 'issue') { const n = parseInt(rest, 10); if (!(n > 0)) { toast('Write the issue number: /issue 12', true); return null; } HOME.issue = n; rest = rest.replace(/^\s*#?\d+\s*/, ''); }
    else if (cmd === 'review') { const n = parseInt(rest.replace('#', ''), 10); if (!(n > 0)) { toast('Write the pull request number: /review 12', true); return null; }
      keepHome(); HOME.text = ''; reviewPr(REPO, n); return null; }
    else { toast(`Unknown command /${cmd}. Try ${SLASH.map(x => '/' + x[0]).join(' ')}`, true); return null; }
    drawTray(); return rest;
  }
  /* Phase 6: this job needs more than one repo. "Read" = Hoola can look into it. "Change it too" = that repo gets its own
     session and its own pull request, started together with this one. */
  async function otherRepos() {
    keepHome();
    const others = (OV?.repos || []).filter(r => r.repo !== REPO);
    const r = await dialog(`<h2>Other repos for this task</h2>
      <p class="hcd-mut">Hoola changes <b>${esc(REPO.split('/')[1] || REPO)}</b>. It can also read up to 3 of your other repos, or change up to 2 of them as well - each in its own session, with its own pull request and the same checks.</p>
      ${others.map((x, i) => `<label class="hcd-f hcd-orow"><span>${esc(x.repo.split('/')[1] || x.repo)}</span><select data-orepo="${esc(x.repo)}" aria-label="${esc(x.repo)}">
        <option value="">Not used</option><option value="read"${HOME.refs.includes(x.repo) ? ' selected' : ''}>Read it</option><option value="also"${HOME.also.includes(x.repo) ? ' selected' : ''}>Change it too</option></select></label>`).join('')}
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Cancel</button><button class="hcd-btn pri" value="ok">Use these</button></div>`);
    if (r !== 'ok') return;
    const refs = [], also = []; EL.querySelectorAll('#hcdDlg [data-orepo]').forEach(sel => { if (sel.value === 'read') refs.push(sel.dataset.orepo); else if (sel.value === 'also') also.push(sel.dataset.orepo); });
    if (also.length > 2) return toast('At most 2 other repos can be changed in one go.', true);
    if (refs.length + also.length > 3) return toast('At most 3 other repos in one task.', true);
    HOME.refs = refs; HOME.also = also; drawTray();
  }
  async function reviewPr(repo, n) {
    show('reviews'); toast(`Reading pull request #${n}…`);
    try { await api('POST', '/api/devsahayak/reviews', {repo, pr: n}); await load(); if (VIEW === 'reviews') reviews(); } catch (e) { toast(e.message, true); }
  }
  function loadBranches(repo) {
    if (!repo || BRANCHES[repo]) return;
    BRANCHES[repo] = [];
    api('GET', `/api/devsahayak/branches?repo=${encodeURIComponent(repo)}`).then(r => { BRANCHES[repo] = r.branches || []; }).catch(() => { delete BRANCHES[repo]; });
  }
  // v0.999.27 THE BOTTOM ROW (owner: "KEEP HOOLA CODE AS IT IS JUST CHANGE STALE THINGS IN BOTTOM LIKE A REPO SHEET AND A
  // ULTRA TO LOW AND A CREDIT"): repo, branch and mode open the console's own menu (a find box for repos and branches),
  // and the model + effort pickers and the rupee line are now her quality tier (the chat's five) and her credits.
  const baseName = repo => HOME.base || (OV?.repos || []).find(x => x.repo === repo)?.default_branch || 'default branch';
  const pickRepo = r => () => { if (r === REPO) return; REPO = r; HOME.base = ''; HOME.refs = []; HOME.also = []; keepHome(); home(); };
  function repoMenu(btn) {
    if (!window.HoolaMenu) return;
    const repos = OV?.repos || [];
    const items = [];
    if (repos.length > 5) items.push({search: 'Search repositories', empty: 'No repository matches'});
    if (repos.length) items.push({header: 'Your repositories'});
    repos.forEach(r => { const [owner, name] = r.repo.includes('/') ? r.repo.split('/') : ['', r.repo];
      items.push({label: name, icon: 'repo', checked: r.repo === REPO, run: pickRepo(r.repo),
        sub: [owner, r.private === false ? 'Public' : r.private ? 'Private' : '', r.language || ''].filter(Boolean).join(' · ')}); });
    if (repos.length) items.push({sep: true});
    items.push({label: 'Add repositories from GitHub', icon: 'plus', run: () => show('settings')});
    items.push({note: 'Hoola sees only the repositories you allow on GitHub.'});
    HoolaMenu.open(btn, items, {align: 'start', label: 'Repository', width: 340});
  }
  function baseMenu(btn) {
    if (!window.HoolaMenu || !REPO) return;
    const r = (OV?.repos || []).find(x => x.repo === REPO), def = r?.default_branch || '';
    const own = (BRANCHES[REPO] || []).filter(b => b !== def && !b.startsWith('hoola/'));
    if (HOME.base && HOME.base !== def && !own.includes(HOME.base)) own.unshift(HOME.base);
    const pick = b => () => { HOME.base = b; keepHome(); const s = $('#hcdBaseBtn span'); if (s) s.textContent = baseName(REPO); };
    const items = [];
    if (own.length > 5) items.push({search: 'Find a branch', empty: 'No branch matches'});
    items.push({header: 'Work from'},
      {label: def || 'Default branch', icon: 'branch', tag: 'Default', checked: !HOME.base || HOME.base === def, run: pick('')},
      ...own.map(b => ({label: b, icon: 'branch', checked: HOME.base === b, run: pick(b)})));
    if (!BRANCHES[REPO]) { loadBranches(REPO); items.push({note: 'Loading the other branches…'}); }
    items.push({sep: true}, {note: `Hoola makes its own branch from this one and opens a pull request. It never pushes to ${def || 'your default branch'}.`});
    HoolaMenu.open(btn, items, {align: 'start', label: 'Branch to work from', width: 320});
  }
  function modeMenu(btn) {
    if (!window.HoolaMenu) return;
    const cur = HOME.mode || (OV?.settings?.ask_before_pr ? 'ask' : 'auto');
    HoolaMenu.open(btn, MODES.map(([k, n, why]) => ({label: n, sub: why, checked: k === cur, run: () => {
      HOME.mode = k; keepHome(); const s = $('#hcdModeBtn span'); if (s) s.textContent = n; $('#hcdModeBtn')?.setAttribute('title', why); }})),
      {align: 'start', label: 'Mode', width: 320});
  }
  // the quality tier (the same five as the chat, the same choice everywhere) and her credits
  const TIER_NAME = {'': 'Normal', ultra: 'Ultra', high: 'High', medium: 'Medium', low: 'Low'};
  let TIERS = null, WALLET = null, PLAN_CREDITS = 0;
  const num = v => Math.round(+v || 0).toLocaleString('en-US');
  const pie = f => { const p = Math.max(0, Math.min(1, f)), a = 2 * Math.PI * Math.max(p, 0.1);
    const x = (9 + 5 * Math.sin(a)).toFixed(2), y = (9 - 5 * Math.cos(a)).toFixed(2);
    return `<svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="7.2" fill="none" stroke="currentColor" stroke-width="1.5"/>${p >= 1
      ? '<circle cx="9" cy="9" r="5" fill="currentColor"/>' : `<path fill="currentColor" d="M9 9V4A5 5 0 ${p > 0.5 ? 1 : 0} 1 ${x} ${y}Z"/>`}</svg>`; };
  function qualityRow() {
    const w = WALLET, out = [];
    if (w && w.on && !w.exempt) {
      const paid = w.unlocked, left = paid ? w.paid_left : w.free_left;
      const frac = paid ? (w.plan && PLAN_CREDITS ? w.plan_left / PLAN_CREDITS : 1) : (w.free_daily ? w.free_left / w.free_daily : 0);
      const say = paid ? `${num(left)} credits` : `${num(left)} free today`;
      const tip = paid ? `${num(left)} credits left${w.plan_name ? ' · ' + w.plan_name + ' plan' : ''}. Tap for plans and extra credits.`
        : `${num(w.free_left)} of ${num(w.free_daily)} free credits left today (Normal only). Tap to see plans.`;
      out.push(`<a class="hcd-use hcd-credits" href="/console/?v=credits" title="${esc(tip)}" aria-label="${esc(tip)}">${pie(frac)}<span>${esc(say)}</span></a>`);
    }
    if (TIERS && TIERS.available) {
      const name = TIER_NAME[TIERS.selected || ''] || 'Normal';
      out.push(`<button type="button" class="hcd-chip hcd-envchip hcd-tierbtn" data-menu="tier" aria-haspopup="menu" aria-label="Quality: ${esc(name)}" title="Quality: ${esc(name)}"><span>${esc(name)}</span>${svg('down')}</button>`);
    }
    return out.join('');
  }
  async function loadQuality() {
    const cc = ((navigator.language || '').split('-')[1] || '').toUpperCase();
    const [t, c] = await Promise.all([api('GET', '/api/model/tier').catch(() => null), api('GET', '/api/credits?country=' + encodeURIComponent(cc)).catch(() => null)]);
    Q_AT = Date.now();
    if (+c?.inr_per_credit > 0) RATE = +c.inr_per_credit;
    if (document.querySelector('.hmenu')) return;              // a menu is open on these buttons: the next look redraws
    TIERS = t; WALLET = c?.wallet || null;
    PLAN_CREDITS = ((c?.prices?.plans || []).find(p => p.id === WALLET?.plan) || {}).credits || 0;
    const q = $('#hcdQual'); if (q) q.innerHTML = qualityRow();
    if (TASK) drawMeta(TASK);
  }
  async function setTier(id) {
    try { TIERS = await api('PUT', '/api/model/tier', {tier: id, confirm_ultra: id === 'ultra'});
          toast(id ? 'Your next message runs on ' + TIER_NAME[id] + '.' : "Back to Hoola's normal setup.");
          const q = $('#hcdQual'); if (q) q.innerHTML = qualityRow(); if (TASK) drawMeta(TASK); }
    catch (e) { toast(e.message, true); }
  }
  // v0.999.27 under a session's box: her quality tier (no model name) and the mode
  const ctxHTML = t => !shared && t.ctx >= 0 ? `<button type="button" class="hcd-ctx${t.ctx >= 80 ? ' hi' : ''}" data-act="ctxinfo" title="How full the conversation is before Hoola summarises it"><i style="--p:${t.ctx}" aria-hidden="true"></i>Context ${t.ctx}%${t.ctx >= 80 ? ' · /compact' : ''}</button>` : '';
  const metaHTML = t => `${ctxHTML(t)}${TIERS && TIERS.available ? `<span>${esc(TIER_NAME[TIERS.selected || ''] || 'Normal')}</span>` : ''}${shared ? '' : `<button type="button" class="hcd-modechip" data-menu="smode" title="Change how Hoola works in this session">${esc((MODES.find(m => m[0] === (t.mode || '')) || [0, 'Default mode'])[1])}${svg('down')}</button>`}`;
  function sessModeMenu(btn) {        // v0.999 her mode, switched while the session runs (Claude Code's Shift+Tab)
    const t = TASK; if (!window.HoolaMenu || !t) return;
    HoolaMenu.open(btn, MODES.map(([k, n, why]) => ({label: n, sub: why, checked: k === (t.mode || ''), run: async () => {
      try { await api('PATCH', `/api/devsahayak/tasks/${tid()}`, {mode: k}); toast(`${n}${t.running ? ' - from the next step' : ''}.`); await refreshTask(t.id, false); } catch (e) { toast(e.message, true); } }})),
      {align: 'start', label: 'Mode', width: 330});
  }
  function drawMeta(t) { const m = $('#hcdCpMeta'); if (!m || !m.innerHTML) return; const h = metaHTML(t); m.innerHTML = h; SIG.cpm = h; }
  const toCredits = () => { location.href = '/console/?v=credits'; };
  function tierMenu(btn, again) {
    if (!window.HoolaMenu || !(TIERS && TIERS.available)) return;
    if (again) HoolaMenu.close(false);
    const sel = TIERS.selected || '', lock = !!TIERS.locked;
    const rows = ['', 'ultra', 'high', 'medium', 'low'].map(id => ({label: TIER_NAME[id], checked: sel === id,
      tag: id === '' ? 'Recommended' : lock ? '🔒 Buy credits' : id === 'ultra' ? '⚠ Up to 70× credit' : '', warn: id === 'ultra' && !lock,
      run: () => id && lock ? toCredits() : id === 'ultra' && sel !== 'ultra' ? ultraAsk(btn) : setTier(id)}));
    HoolaMenu.open(btn, [{note: lock ? 'Free works on Normal. Buy any plan or extra credits to open the other tiers.'
      : 'Better models give better answers and use your credit faster.'}, ...rows],
      {align: 'end', place: 'above', cls: 'tiers', label: 'Quality', width: 300, keyboard: !!again});
  }
  function ultraAsk(btn) {
    HoolaMenu.open(btn, [
      {title: 'Use Ultra?', tag: '⚠ Up to 70× credit', warn: true, backLabel: 'Back to the tiers', back: () => tierMenu(btn, true)},
      {note: 'Ultra runs the best and most expensive models in every field: chat, coding, AI employees, apps and videos.'},
      {note: 'Your credit runs out up to 70 times faster than on Medium.'},
      {actions: [{label: 'Not now', run: () => {}}, {label: 'Use Ultra', primary: true, run: () => setTier('ultra')}]},
    ], {align: 'end', place: 'above', cls: 'tierask', label: 'Use Ultra?', width: 340, keyboard: true});
  }

  function home() {
    const st = OV?.settings || {}, repos = OV?.repos || [];
    const setup = !st.github ? `<div class="hcd-block"><b>Connect GitHub first.</b> Add a fine-grained token and a repo in <button type="button" class="hcd-link" data-go="settings">Settings</button>. The token is typed only there.</div>`
      : !repos.length ? `<div class="hcd-block"><b>Add a repo first</b> in <button type="button" class="hcd-link" data-go="settings">Settings</button>.</div>` : '';
    const mode = HOME.mode || (st.ask_before_pr ? 'ask' : 'auto');
    const env = HOME.env || 'auto', envSub = env === 'auto' ? 'Follows your repositories' : (() => { const e = (ENVS.envs || []).find(x => x.id === env); return e ? LEVEL[e.net.level] + (e.setup ? ' · setup script' : '') : ''; })();
    body(`<main class="hcd-home"><div class="hcd-hbar">New session</div>
      <div class="hcd-hero">
      ${OV?.error ? `<p class="hcd-err">${esc(OV.error)}</p>` : ''}
      ${window.HoolaMark?.think ? `<span class="hcd-heromark" aria-hidden="true">${HoolaMark.think(56)}</span>` : '<img class="hcd-heromark" src="/static/hoola-mark.png" alt="" width="56" height="56">'}
      <h1>What should we build today?</h1>
      <div class="hcd-envcard"><div class="hcd-envnow">${svg('cloud')}<span><b>${esc(envName(env))}</b><small>${esc(envSub)}</small></span>${svg('ok', 'ok')}</div>
        <button type="button" class="hcd-envpick" data-menu="env">Choose environment${svg('down')}</button></div>
      ${setup}
      <p class="hcd-lede">Hoola works on its own branch in a cloud environment, runs your tests and opens a pull request. Nothing is merged without you.</p>
      </div>
      <div class="hcd-dock">
      <form class="hcd-ask" id="hcdAsk">
        <div class="hcd-tray" id="hcdTray" hidden></div>
        <label for="hcdLine" class="hcd-sr">Describe the task</label>
        <textarea id="hcdLine" rows="3" maxlength="20000" placeholder="Describe a task, or paste an error and its stack trace">${esc(HOME.text)}</textarea>
        <button type="button" class="hcd-plus" data-menu="plus" aria-label="Add files, photos or a slash command" title="Add files, photos or a command">${svg('new')}</button>
        <input type="file" id="hcdFile" class="hcd-sr" multiple tabindex="-1" aria-hidden="true" accept="image/png,image/jpeg,image/webp,image/gif,text/*,.md,.log,.json,.csv,.py,.js,.ts,.tsx,.jsx,.dart,.kt,.java,.go,.rs,.rb,.php,.c,.cpp,.h,.cs,.sql,.yml,.yaml,.toml,.sh,.xml">
        <button class="hcd-send" id="hcdStart" type="submit" aria-label="Start session" title="Start (Enter)"${repos.length && st.github ? '' : ' disabled'}>${svg('up')}</button>
      </form>
      <div class="hcd-askrow">
        <button type="button" class="hcd-chip hcd-envchip" id="hcdEnv" data-menu="env" aria-haspopup="menu" title="The cloud environment this session runs in: network access, variables and a setup script">${svg('cloud')}<span>${esc(envName(HOME.env))}</span>${svg('down')}</button>
        <button type="button" class="hcd-chip hcd-envchip" id="hcdRepoBtn" data-menu="repo" aria-haspopup="menu" title="${esc(REPO || 'Pick a repository')}">${svg('repo')}<span>${esc((REPO || '').split('/')[1] || REPO || 'No repository yet')}</span>${svg('down')}</button>
        <button type="button" class="hcd-chip hcd-envchip" id="hcdBaseBtn" data-menu="base" aria-haspopup="menu" title="Hoola works from this branch and opens the pull request against it">${svg('branch')}<span>${esc(baseName(REPO))}</span>${svg('down')}</button>
        <button type="button" class="hcd-chip hcd-envchip" id="hcdModeBtn" data-menu="mode" aria-haspopup="menu" title="${esc((MODES.find(m => m[0] === mode) || MODES[0])[2])}">${svg('pr')}<span>${esc((MODES.find(m => m[0] === mode) || MODES[0])[1])}</span>${svg('down')}</button>
        <span class="hcd-flex"></span>
        <span class="hcd-qual" id="hcdQual">${qualityRow()}</span>
      </div></div>
    </main>`);
    drawTray(); loadBranches(REPO); loadQuality();
    $('#hcdLine')?.focus();
  }
  // A starting point she can tap: it only fills the box (she finishes the sentence and sends it herself).
  const STARTS = [['bug', 'Fix a bug', 'Fix this bug: '], ['spark', 'Build a feature', 'Build this: '], ['ok', 'Write tests', 'Write tests for '], ['read', 'Explain the code', '/explain How does ']];
  async function startSession() {
    const line = $('#hcdLine'), btn = $('#hcdStart'); let text = line.value.trim();
    const m = /^\/([a-z]+)\b[ \t]*/i.exec(text);
    if (m) { const left = slash(m[1].toLowerCase(), text.slice(m[0].length)); if (left === null) return; text = left.trim(); line.value = text;
      if (!text && !HOME.issue) return toast('Now describe the task.'); }
    if (!text && !HOME.issue) return toast('Describe the task, or paste the error.', true);
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const t = await api('POST', '/api/devsahayak/tasks/start', {kind: HOME.kind, text, repo: REPO, issue: HOME.issue, base: HOME.base, mode: HOME.mode || (OV?.settings?.ask_before_pr ? 'ask' : 'auto'),
        model: '', effort: '',
        images: HOME.files.filter(f => f.kind === 'image').map(f => ({name: f.name, data: f.data})), docs: HOME.files.filter(f => f.kind === 'text').map(f => ({name: f.name, text: f.text})),
        refs: HOME.refs, also: HOME.also, env: HOME.env || ''});
      HOME.files.forEach(f => f.url && URL.revokeObjectURL(f.url));
      Object.assign(HOME, {text: '', kind: 'auto', issue: 0, files: [], refs: [], also: []}); line.value = '';      // sent: the box starts empty next time
      await load(); show('session', t.id);
    } catch (e) { toast(e.message, true); btn.disabled = false; }
  }

  // ------------------------------------------------------------------ session: the steps ---
  const QUIET = new Set(['rules', 'read', 'search', 'list', 'usages', 'grep', 'diff', 'refused', 'pass']);
  const PASS = {plan: 'Plan pass', review: "Hoola's own review", ci_fix: 'CI fix round', comments: "Reviewers' comments"};
  const showThink = () => P.view !== 'normal';
  const diffHTML = rows => rows && rows.length ? `<pre class="hcd-diff">${rows.map(r => `<span class="${r.startsWith('+') ? 'add' : r.startsWith('-') ? 'del' : 'ctx'}">${esc(r)}</span>`).join('\n')}</pre>` : '';
  const p = x => `<code>${esc(x)}</code>`;
  // v0.999 the real change, as Claude Code shows it: old and new line numbers, red removed, green added, context dim
  const hunkHTML = rows => rows && rows.length ? `<pre class="hcd-diff num">${rows.map(r => r[0] === '@' ? '<span class="gap">⋯</span>'
    : r[0] === '…' ? `<span class="gap">${esc(r[3] || '')}</span>`
    : `<span class="${r[0] === '+' ? 'add' : r[0] === '-' ? 'del' : 'ctx'}"><b>${r[1] ?? ''}</b><b>${r[2] ?? ''}</b><i>${r[0] === ' ' ? ' ' : esc(r[0] === '-' ? '−' : '+')}</i>${esc(r[3] || '')}</span>`).join('')}</pre>` : '';
  const SEEN = new Set();          // v0.999 a small change shows open the first time, like Claude Code; closing it is remembered
  const openFirst = (key, small) => { if (!SEEN.has(key)) { SEEN.add(key); if (small) OPEN.add(key); } return key; };
  const changeHTML = s => s.hunk && s.hunk.length ? hunkHTML(s.hunk) : diffHTML(s.diff);
  const todoHTML = items => `<div class="hcd-todo">${(items || []).map(x => `<div class="hcd-td ${esc(x.status)}"><i aria-hidden="true">${x.status === 'completed' ? '✓' : x.status === 'in_progress' ? '●' : '○'}</i><span>${esc(x.content)}</span></div>`).join('')}</div>`;
  const srch = s => { const n = s.num ?? s.n ?? 0;
    return s.files != null && s.files !== n ? `${plural(n, 'match', 'matches')} in ${plural(s.files, 'file')}` : n ? plural(n, 'file') : 'no matches'; };
  const fold = (key, label, inner, cls = '', forced = false) => { const on = forced || OPEN.has(key);
    return `<button type="button" class="hcd-fold ${cls}" data-fold="${esc(key)}" aria-expanded="${on}">${svg('chev', 'hcd-chev')}<span>${label}</span></button><div class="hcd-fin"${on ? '' : ' hidden'}>${inner}</div>`; };
  function stepHTML(s, t0, i, verbose) {
    const at = `<span class="hcd-t">${esc(since(t0, s.at))}</span>`;
    switch (s.k) {
      case 'say': return `<p class="hcd-say">${esc(s.text)}</p>`;
      case 'round': return `<div class="hcd-step dim">${svg('ok')}<span>${esc(s.text || 'Worked')}</span>${at}</div>`;   // v0.944 one piece of work ended
      case 'think': return fold('th' + i, `Thought${s.secs ? ' for ' + esc(HoolaChat.fmtSecs(s.secs)) : ''}`, `<div class="hcd-think">${esc(s.text)}</div>`, 'row think', showThink());
      case 'pass': return `<div class="hcd-step dim">${svg(s.state === 'end' ? (s.ok === false ? 'bad' : 'ok') : 'dot')}<span>${esc(PASS[s.name] || s.name)} ${s.state === 'end' ? 'ended' : 'started'}${s.note ? ' · ' + esc(s.note) : ''}</span>${at}</div>`;
      case 'note': return `<div class="hcd-me sm">${esc(s.text)}<small>you, while Hoola worked</small></div>`;
      case 'rules': return `<div class="hcd-step">${svg('list')}<span>Read the repo's rules · ${(s.paths || []).map(p).join(', ')}</span>${at}</div>`;
      case 'read': return `<div class="hcd-step">${svg('read')}<span>Read ${p(s.path)}${s.lines && s.lines[0] ? ` · lines ${s.lines[0]}–${s.lines[1] || 'end'}` : ''}</span>${at}</div>`;
      case 'search': return `<div class="hcd-step">${svg('search')}<span>Searched ${p(s.q)} · ${srch(s)}</span>${at}</div>`;
      case 'list': return s.glob ? `<div class="hcd-step">${svg('search')}<span>Found ${plural(s.num ?? s.n ?? 0, 'file')} · ${p(s.path)}</span>${at}</div>`
        : `<div class="hcd-step">${svg('list')}<span>Listed ${p(s.path || '/')}</span>${at}</div>`;
      case 'usages': return `<div class="hcd-step">${svg('search')}<span>Found where ${p(s.name)} is used · ${plural(s.num ?? s.n, 'place')}</span>${at}</div>`;
      case 'edit': case 'new': { const lab = s.cell != null ? `Edited cell ${esc(String(s.cell))} of ${p(s.path)}` : `${s.k === 'new' ? 'Created' : 'Edited'} ${p(s.path)} <em class="add">+${s.added || 0}</em>${s.k === 'edit' ? ` <em class="del">−${s.removed || 0}</em>` : ''}${s.by ? ` · by ${esc(s.by)}` : ''}`;
        return (s.hunk && s.hunk.length) || (s.diff && s.diff.length) ? fold(openFirst('e' + i, (s.hunk || s.diff || []).length <= 40), lab, changeHTML(s), 'row', verbose) : `<div class="hcd-step">${svg(s.k === 'new' ? 'new' : 'edit')}<span>${lab}</span>${at}</div>`; }
      case 'diff': return `<div class="hcd-step">${svg('read')}<span>Checked its own change · ${plural(s.num ?? s.n, 'file')}</span>${at}</div>`;
      case 'check': return `<div class="hcd-step ${s.ok ? 'ok' : 'bad'}">${svg(s.ok ? 'ok' : 'bad')}<span><b>Ran your tests</b>${s.only ? ` (${esc(s.only)})` : ''} · <span class="${s.ok ? 'add' : 'del'}">${s.ok ? 'passed' : 'failed'}</span>${s.seconds ? ` · ${esc(String(s.seconds))} s` : ''}${s.cmd ? ` · ${p(s.cmd)}` : ''}</span>${at}</div>${!s.ok && s.tail && s.tail.length ? `<pre class="hcd-diff">${s.tail.map(x => `<span class="${/fail|error|assert/i.test(x) ? 'del' : 'ctx'}">${esc(x)}</span>`).join('\n')}</pre>` : ''}`;
      case 'check_off': return `<div class="hcd-step">${svg('bad')}<span>Your tests could not run here - this change is not measured</span>${at}</div>`;
      case 'grep': return `<div class="hcd-step">${svg('search')}<span>Searched the test log for ${p(s.q)}</span>${at}</div>`;
      case 'refused': return `<div class="hcd-step dim">${svg('bad')}<span>A step was refused: ${esc(s.why)}</span>${at}</div>`;
      case 'bash': { const ok = s.rc === 0, what = s.did || (s.desc ? 'Ran: ' + s.desc.charAt(0).toLowerCase() + s.desc.slice(1) : 'Ran a command'),
          lab = `${esc(what)} · <span class="${ok ? 'add' : 'del'}">${s.timed_out ? 'timed out' : 'exit ' + esc(String(s.rc))}</span>${s.seconds ? ` · ${esc(String(s.seconds))} s` : ''}${s.by ? ` · by ${esc(s.by)}` : ''}`,
          inner = `<pre class="hcd-term"><span class="hcd-cmd">$ ${esc(s.cmd || '')}</span>${(s.tail || []).length ? '\n' + s.tail.map(x => esc(x)).join('\n') : ''}</pre>`;
        return fold('b' + i, lab, inner, 'row', verbose || !ok); }
      case 'todo': { const items = s.items || [], done = items.filter(x => x.status === 'completed').length;   // v0.999 the list shows once, the newest, updated in place
        return s.last === false ? `<div class="hcd-step dim">${svg('list')}<span>Updated the to-do list · ${done} of ${items.length} done</span>${at}</div>` : todoHTML(items); }
      case 'look': return `<div class="hcd-step ${s.errors ? 'bad' : ''}">${svg('read')}<span>Opened ${p(s.path || 'the page')} in a browser · ${plural((s.shots || []).length, 'screenshot')}${s.errors ? ` · <span class="del">${plural(s.errors, 'page error')}</span>` : ''}</span>${at}</div>`;
      case 'made': return `<div class="hcd-step ok">${svg('new')}<span>Made version ${esc(String(s.v || 1))} of the document</span>${at}</div>`;
      case 'server': return `<div class="hcd-step ${s.state === 'refused' || s.state === 'offline' ? 'bad' : ''}">${svg('list')}<span>${s.state === 'waiting' ? 'Waiting for your tap to run' : s.state === 'refused' ? 'Refused on your server:' : s.state === 'offline' ? 'Your server is offline' : 'Ran on your server'}${s.cmd ? ' ' + p(s.cmd) : ''}${s.server ? ' · ' + esc(s.server) : ''}${s.reason ? ' · ' + esc(s.reason) : ''}</span>${at}</div>`;
      case 'bgstart': return `<div class="hcd-step">${svg('term')}<span>${esc(s.did || 'Started a command in the background')} · <span class="hcd-cmd">${esc(s.id)}</span></span>${at}</div>`;
      case 'bgout': { const lab = `Read the output of <span class="hcd-cmd">${esc(s.id)}</span> · ${s.running ? 'still running' : s.rc == null ? 'ended' : 'exited ' + esc(String(s.rc))}`;
        return (s.tail || []).length ? fold('o' + i, lab, `<pre class="hcd-term">${s.tail.map(x => esc(x)).join('\n')}</pre>`, 'row', verbose) : `<div class="hcd-step">${svg('term')}<span>${lab}</span>${at}</div>`; }
      case 'bgkill': return `<div class="hcd-step dim">${svg('stop')}<span>Stopped <span class="hcd-cmd">${esc(s.id)}</span>${s.by === 'you' ? ' · by you' : ''}</span>${at}</div>`;
      case 'perm': return `<div class="hcd-step ${s.answer === 'no' ? 'bad' : 'ok'}">${svg(s.answer === 'no' ? 'bad' : 'ok', s.answer === 'no' ? 'bad' : 'ok')}<span>${s.answer === 'no' ? 'You said no' : 'You allowed'}: ${esc(s.what || '')}${s.note ? ` · <i>${esc(s.note)}</i>` : ''}</span>${at}</div>`;
      case 'web': { let host = String(s.url || ''); try { host = new URL(host).host + new URL(host).pathname.replace(/\/$/, ''); } catch (e) { /* not a link */ }
        return `<div class="hcd-step ${s.ok === false ? 'bad' : ''}">${svg('web')}<span>${s.ok === false ? 'Could not read' : 'Read'} <a href="${esc(s.url || '#')}" target="_blank" rel="noopener noreferrer">${esc(host.slice(0, 80))}</a></span>${at}</div>`; }
      case 'lsp': { /* v0.999 code intelligence (Claude Code's LSP tool) */
        const W = {goToDefinition: 'Found the definition', goToImplementation: 'Found the implementation', findReferences: 'Found the references',
          hover: 'Read the type', documentSymbol: 'Listed the symbols', workspaceSymbol: 'Searched the symbols', prepareCallHierarchy: 'Found the function',
          incomingCalls: 'Found the callers', outgoingCalls: 'Found what it calls', diagnostics: 'Checked for problems'};
        const where = s.q ? ` for ${p(s.q)}` : s.path ? ` in ${esc(s.path)}${s.line ? ':' + s.line : ''}` : '';
        return `<div class="hcd-step${s.ok === false ? ' dim' : ''}">${svg('search')}<span>${s.ok === false ? esc(s.text || 'The language server could not answer') : `${W[s.op] || 'Asked the language server'}${where}${s.num != null ? ' · ' + esc(String(s.num)) : ''}`}</span>${at}</div>`; }
      case 'diagnostics': return fold('dg' + i, `<b>The language server found problems</b> in what was just edited`, `<pre class="hcd-term">${esc(s.text || '')}</pre>`, 'row', verbose);
      case 'websearch': return `<div class="hcd-step">${svg('web')}<span>Searched the web for ${p(s.q || '')} · ${plural(s.num ?? 0, 'result')}</span>${at}</div>`;
      case 'mcp': return `<div class="hcd-step">${svg('spark')}<span>${s.action === 'list' ? 'Looked at your MCP servers' : `Used ${esc(s.server || 'an MCP server')} · ${p(s.tool || '')}`}</span>${at}</div>`;
      case 'skill': return `<div class="hcd-step dim">${svg('read')}<span>${s.action === 'list' ? 'Looked at your skills' : `Read the skill ${p(s.name || '')}`}</span>${at}</div>`;
      case 'asked': return `<div class="hcd-step">${svg('dot')}<span>Asked you: <b>${esc(s.question || '')}</b>${s.answer ? ` · you said <i>${esc(s.answer)}</i>` : ' · no answer'}</span>${at}</div>`;
      case 'judge': return `<div class="hcd-step${s.verdict === 'deny' ? ' bad' : ''}">${svg(s.verdict === 'deny' ? 'x' : 'spark')}<span>${s.verdict === 'deny' ? '<b>The safety reviewer stopped a step</b>' : '<b>The safety reviewer asked you</b>'}${s.what ? ' · ' + esc(s.what) : ''}${s.reason ? ` <span class="hcd-mut">- ${esc(s.reason)}</span>` : ''}</span>${at}</div>`;
      case 'fallback': return `<div class="hcd-step dim">${svg('spark')}<span>${esc(s.text || 'A backup model answered')}</span>${at}</div>`;
      case 'title': return '';
      case 'claudefile': return `<div class="hcd-step dim">${svg('pencil')}<span>You ${s.what === 'deleted' ? 'deleted' : 'changed'} <code>${esc(s.path || '')}</code></span>${at}</div>`;
      case 'cmd': return `<div class="hcd-step dim">${svg('spark')}<span>${s.repo ? 'Ran your command' : 'Started'} <span class="hcd-cmd">/${esc(s.name || '')}</span>${s.repo ? ' from this repo' : ''}</span>${at}</div>`;
      case 'mention': return `<div class="hcd-step">${svg('read')}<span>Read the files you pointed at · ${(s.files || []).map(p).join(', ')}</span>${at}</div>`;
      case 'hook': {   /* v0.999 what the repo's hook decided, Claude Code's JSON answers included */
        const did = s.stop ? ' · <span class="del">stopped the work</span>' : s.block ? ' · <span class="del">stopped it</span>'
          : s.decision === 'allow' ? ' · allowed it' : s.decision === 'ask' ? ' · asked you first' : s.changed ? ' · changed the step' : '';
        const head = s.event === 'stop' ? 'This repo\u2019s hook <span class="del">stopped the work</span>'
          : `This repo\u2019s ${esc(s.event || '')} hook ran${s.tool ? ' for ' + esc(s.tool) : ''}${did}${s.changed && did.indexOf('changed') < 0 ? ' · changed the step' : ''}`;
        const msg = s.msg ? `<p class="hcd-hookmsg">${esc(s.msg)}</p>` : '';
        return s.text || s.msg ? fold('h' + i, head, msg + (s.text ? `<pre class="hcd-term">${esc(s.text)}</pre>` : ''), 'row', verbose || !!s.block || !!s.stop || !!s.msg)
          : `<div class="hcd-step dim">${svg('gear')}<span>${head}</span>${at}</div>`; }
      case 'gap': return `<div class="hcd-step dim">${svg('list')}<span>${esc(s.text || 'Earlier steps folded')}</span></div>`;
      case 'compact': case 'ws': return `<div class="hcd-step dim">${svg('list')}<span>${esc(s.text || '')}</span>${at}</div>`;
      case 'wait': return `<div class="hcd-step">${svg('dot')}<span>${esc(s.text || 'Waiting for a free coding slot')}</span>${at}</div>`;
      case 'ckpt': return `<div class="hcd-step dim">${svg('ok')}<span>Checkpoint ${esc(String(s.num ?? s.n))} saved - you can go back to here</span>${at}</div>`;
      case 'rewind': return `<div class="hcd-step">${svg('list')}<span><b>${s.what === 'code' ? 'Put the files back' : s.what === 'conversation' ? 'Took the conversation back' : 'Went back'} to checkpoint ${esc(String(s.num ?? s.n))}.</b> ${s.what === 'code' ? 'The conversation is unchanged.' : s.what === 'conversation' ? 'The files keep every change made since.' : 'The working copy and the conversation are as they were then.'}</span>${at}</div>`;
      case 'agent': { /* v0.794 ECC agents (Claude Code-style subagents) */
        if (s.state === 'start') return `<div class="hcd-step">${svg('dot')}<span><b>${s.background ? 'Started' : 'Asked'} ${esc(s.title || s.name)}</b>${s.background ? ` <span class="hcd-bgtag">in the background${s.id ? ' · ' + esc(s.id) : ''}</span>` : ''}${s.worktree ? ` <span class="hcd-bgtag">in its own copy · ${esc(s.worktree)}</span>` : ''} (${esc(s.tools || 'read')}${s.model ? ' · on ' + esc(s.model) : ''}) · ${esc(s.task || '')}</span>${at}</div>`;
        const lab = `<b>${esc(s.title || s.name)}</b> reported · ${plural(s.steps || 0, 'step')}${s.edits ? ` · changed ${plural(s.edits, 'file')}` : ''}${s.secs ? ` · ${esc(String(s.secs))} s` : ''}`;
        return s.report ? fold('a' + i, lab, `<pre class="hcd-term">${esc(s.report)}</pre>`, 'row', verbose) : `<div class="hcd-step ok">${svg('ok')}<span>${lab}</span>${at}</div>`; }
      case 'worktree': { /* v0.999 an agent's own copy (Claude Code's worktrees): kept until it is brought in */
        const who = esc(s.title || s.agent || 'The agent'), id = esc(s.id || '');
        if (s.state === 'removed') return `<div class="hcd-step dim">${svg('list')}<span>${who} worked in its own copy ${id}; it changed nothing, so the copy was removed.</span>${at}</div>`;
        if (s.state === 'applied') return `<div class="hcd-step ${s.conflicts && s.conflicts.length ? 'bad' : 'ok'}">${svg(s.conflicts && s.conflicts.length ? 'bad' : 'ok')}<span><b>${s.by_her ? 'You brought in' : 'Brought in'} the changes from ${id}</b>${s.conflicts && s.conflicts.length ? ` · <span class="del">conflicts in ${esc(s.conflicts.join(', '))}</span>` : ''}</span>${at}</div>`;
        if (s.state === 'discarded') return `<div class="hcd-step dim">${svg('x')}<span>${s.by_her ? 'You discarded' : 'Discarded'} the changes in ${id}.</span>${at}</div>`;
        const fl = (s.files || []).map(x => String(x).replace(/^[A-Z] /, ''));
        return `<div class="hcd-step hcd-wt">${svg('list')}<span><b>${who}'s own copy ${id}</b> · ${plural(fl.length, 'file')} waiting (<span class="add">+${s.added || 0}</span> <span class="del">-${s.removed || 0}</span>)${fl.length ? ' · ' + esc(fl.slice(0, 4).join(', ')) + (fl.length > 4 ? ' …' : '') : ''}
          <span class="hcd-wtb"><button type="button" class="hcd-btn sm" data-act="wtshow" data-wt="${id}">Show changes</button><button type="button" class="hcd-btn sm" data-act="wtapply" data-wt="${id}">Bring in</button><button type="button" class="hcd-btn sm" data-act="wtdiscard" data-wt="${id}">Discard</button></span></span>${at}</div>`; }
      case 'memory': { /* Hoola Code memory: the repo's notes from earlier sessions */
        const what = s.action === 'remembered' ? `Wrote ${plural(s.num ?? s.n ?? 0, 'note')} to this repo's memory` : s.action === 'save' ? `Saved a note to this repo's memory${s.title ? ': ' + esc(s.title) : ''}`
          : s.action === 'search' ? `Searched this repo's memory${s.q ? ' for ' + p(s.q) : ''} · ${plural(s.num ?? s.n ?? 0, 'note')}` : `Read ${plural(s.num ?? s.n ?? 0, 'note')} from this repo's memory`;
        return `<div class="hcd-step dim">${svg('list')}<span>${what}</span>${at}</div>`; }
      case 'reality': { /* v0.814 The Agency's reality checker, the last look before a round finishes */
        const ok = s.verdict === 'ready', lab = `<b>Reality check</b> · <span class="${ok ? 'add' : s.verdict === 'needs_work' ? 'del' : ''}">${ok ? 'ready' : s.verdict === 'needs_work' ? 'needs work - back to it' : 'no clear verdict'}</span>`;
        return s.text ? fold('r' + i, lab, `<pre class="hcd-term">${esc(s.text)}</pre>`, 'row', verbose || !ok) : `<div class="hcd-step">${svg(ok ? 'ok' : 'bad')}<span>${lab}</span>${at}</div>`; }
      case 'gate': return `<div class="hcd-step bad">${svg('bad')}<span><b>Quality check before finishing</b> · ${plural(s.num ?? s.n ?? 0, 'thing')} to clean up${(s.items || []).length ? ': ' + (s.items || []).slice(0, 3).map(x => p(x)).join(', ') : ''}</span>${at}</div>`;
      case 'stopped': return `<div class="hcd-step bad">${svg('bad')}<span><b>Stopped.</b> Nothing was pushed.</span>${at}</div>`;
      default: return '';
    }
  }
  function summary(list) {
    const n = k => list.filter(s => s.k === k).length, parts = [];
    if (n('rules')) parts.push("read the repo's rules");
    if (n('read')) parts.push(`read ${plural(new Set(list.filter(s => s.k === 'read').map(s => s.path)).size, 'file')}`);
    const se = n('search') + n('usages') + n('grep'); if (se) parts.push(`searched for ${plural(se, 'pattern')}`);
    const gl = list.filter(s => s.k === 'list' && s.glob).length, ls = n('list') - gl;
    if (gl) parts.push(`found files ${gl === 1 ? 'once' : gl + ' times'}`);
    if (ls) parts.push(`listed ${plural(ls, 'folder')}`);
    if (n('diff')) parts.push('checked its own change');
    if (n('refused')) parts.push(`${plural(n('refused'), 'step')} refused`);
    const ps = list.filter(s => s.k === 'pass' && s.state === 'start').length; if (ps) parts.push(`ran ${plural(ps, 'pass', 'passes')}`);
    if (!parts.length && n('pass')) parts.push('a pass ended');
    const s = parts.join(', '); return s.charAt(0).toUpperCase() + s.slice(1);
  }
  // the rows of ONE piece of work: steps a..b of the session (her messages and Hoola's words are not in it - the thread draws those)
  function rowsHTML(t, a, b) {
    const steps = t.steps || [], verbose = P.view === 'verbose'; let out = '', i = a;
    let lastTodo = -1; steps.forEach((x, j) => { if (x && x.k === 'todo') lastTodo = j; });
    steps.forEach((x, j) => { if (x && x.k === 'todo') x.last = j === lastTodo; });
    const skip = s => s.k === 'round' && !verbose;          // "Worked for" is on the fold itself
    while (i < b) {
      if (skip(steps[i])) { i++; continue; }
      if (!verbose && QUIET.has(steps[i].k)) { const from = i, list = []; while (i < b && QUIET.has(steps[i].k)) list.push(steps[i++]);
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
    const nf = (pl.files || []).length;
    return `<section class="hcd-card hcd-plan" aria-labelledby="hcdPlanH"><div class="hcd-sh"><span class="hcd-badge warn">Plan · waits for you</span><span class="hcd-mut">${esc((t.tier || 'large').replace(/^./, c => c.toUpperCase()))} change${nf ? ' · ' + plural(nf, 'file') : ''}</span></div>
      <h2 id="hcdPlanH">${esc(pl.goal || 'The plan')}</h2>
      ${pl.steps?.length ? `<ol class="hcd-plsteps">${li(pl.steps)}</ol>` : ''}
      ${pl.files?.length ? `<h3>Files it will change</h3><ul class="mono">${li(pl.files)}</ul>` : ''}
      ${pl.done_when?.length ? `<p class="hcd-mut"><b>Done when:</b> ${esc(pl.done_when.map(x => typeof x === 'string' ? x : x.why || '').join('; '))}</p>` : ''}
      ${pl.risk ? `<div class="hcd-risk"><h3>Risks</h3><p>${esc(String(pl.risk))}</p></div>` : ''}
      ${shared ? '' : `<div class="hcd-acts"><button type="button" class="hcd-btn pri" id="hcdYes" data-act="yes">Approve plan</button><button type="button" class="hcd-btn" id="hcdCancel" data-act="cancel">Not now</button><span class="hcd-mut">Nothing is touched until you approve. A note in the box below goes with it.</span></div>`}</section>`;
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
    const sr = t.self_review || {}, pts = (sr.verdict && sr.verdict !== 'ok' ? sr.problems || [] : []).slice(0, 8), canFix = canRev(t);
    if (pts.length) parts.push(`<section class="hcd-card hcd-rev" aria-labelledby="hcdRevH"><div class="hcd-sh"><h2 id="hcdRevH">Hoola's own review</h2><span class="hcd-pill warn">${plural(pts.length, 'point')} left open</span></div>
      ${pts.map((x, i) => { const o = typeof x === 'string' ? {body: x} : x, where = o.path ? `${o.path}${o.line ? ':' + o.line : ''}` : '';
        return `<div class="hcd-cm"><div>${o.severity ? `<span class="hcd-pill ${o.severity === 'high' ? 'bad' : 'warn'}">${esc(o.severity)}</span>` : ''}${where ? `<code>${esc(where)}</code> ` : ''}${esc(o.body || o.text || o.problem || '')}</div>
          <div class="hcd-acts">${where ? `<button type="button" class="hcd-btn sm" data-act="walk" data-path="${esc(o.path)}">Show in diff</button>` : ''}${canFix ? `<button type="button" class="hcd-btn sm" data-act="fixone" data-i="${i}">Fix this one</button>` : ''}</div></div>`; }).join('')}
      ${canFix && pts.length > 1 ? `<div class="hcd-acts"><button type="button" class="hcd-btn pri" data-act="fixall">Fix all ${pts.length}</button></div>` : ''}</section>`);
    if ((t.file_diffs || []).length || t.diff) parts.push(`<button type="button" class="hcd-fold row" id="hcdFull" data-act="changes">${svg('chev', 'hcd-chev')}<span>See the full change · ${plural((t.files || []).length, 'file')}</span></button>`);
    if (t.risk) parts.push(`<p class="hcd-mut"><b>Risk:</b> ${esc(t.risk)}</p>`);
    const rc = shared ? null : recap(t), acts = actsFor(t); if (rc) parts.push(`<div class="hcd-recap ${rc[0]}"><span><b>${esc(rc[1])}</b> ${esc(rc[2])}</span>${acts.length ? `<div class="hcd-acts">${acts.join('')}</div>` : ''}</div>`);
    return parts.join('');
  }
  // ------------------------------------------------------------------ session: the thread (chatkit.js) ---
  /* HOOLA CHAT KIT. One turn = everything Hoola does between two of her messages: its step rows and its words sit in
     ONE kit block, in the order they happened, with the kit's working row at the end while it works.
       her message      -> the kit's bubble (her first message, her notes and follow-ups)
       a "say" step     -> the kit's reply; new ones land word by word, one after the other (K.chain), what was already
                           there when the page opened is shown whole
       the other steps  -> this page's rows (a piece of work = the steps between two of Hoola's messages). While it is
                           the newest thing of a running round the rows show as they come; once words follow it (or
                           the round ends) it folds into "Worked for ..." - the kit's own fold, the rich rows inside
       working          -> the kit's ONE working row: the step running now (the server's `now`) + the clock (`run_at`)
     thread(t) is called on every refresh. It adds only what is new; the thread is drawn again from the start only for
     another session, another transcript view, or when the list of steps is no longer the one that was drawn. */
  const DN = '<svg class="hck-dn" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3"/></svg>';   // the kit's fold arrow
  const NOWHERE = document.createElement('div');     // while history is drawn the kit follows nothing (no layout per message)
  let K = null;                                      // the mounted thread: what is drawn, what waits to land
  function dropThread() { if (!K) return; const k = K; K = null; try { k.t.clear(); } catch (e) { /* already gone */ } }
  const stepId = (s, i) => (s && s.n != null ? s.n : i);
  const headOf = t => JSON.stringify([t.text || '', (t.attach || []).map(a => [a.name, a.kind, a.size])]);
  const nowLabel = t => { if (t.stopping) return 'Stopping after this step…';
    const s = stepSecs(t); return (t.now ? t.now + '…' : nowDoing(t)) + (t.now && s >= 1 ? ' · ' + HoolaChat.fmtSecs(s) : '') + (t.running && !shared ? ' · Esc to stop' : ''); };
  // what is new waits its turn (words land one message after the other); history is drawn at once
  const thLater = fn => { const k = K; if (k.hist) return void fn();
    k.q++; k.chain = k.chain.then(() => (K === k ? fn() : null)).catch(() => {}).then(() => { k.q--; }); };
  const thTail = () => { const k = K; if (k.col.lastElementChild !== k.tail) k.col.append(k.tail); };      // the cards stay under the thread
  function thOpen() {               // a turn of Hoola's: the kit's block, the working row at its end
    const k = K; if (k.open) return;
    k.o.startedAt = k.task.running ? (Date.parse(k.task.run_at || k.task.at || '') || 0) : 0;     // the clock counts from the round's start
    k.t.begin(nowLabel(k.task));
    k.ho = [...k.col.children].filter(n => n.classList.contains('hck-ho')).pop(); k.work = k.ho.querySelector(':scope > .hck-work');
    k.open = true; k.liveSeg = false; thTail();
  }
  function thEnd() { const k = K; if (!k.open) return; k.t.end({stopped: !k.task.running && k.task.status === 'cancelled'}); k.open = false; k.liveSeg = false; k.ho = k.work = null; thTail(); }
  function thSay(text) {            // Hoola's words
    const k = K; text = String(text || '').trim(); if (!text) return;
    thGroupDone(); k.lastSay = text;
    if (k.hist) { thOpen(); k.t.nextBlock(); k.t.delta(text.startsWith('⁠') ? ' ' : '⁠'); k.t.final(text); return; }   // already there: a final text that does not continue what is shown is shown at once (stream.js)
    thLater(() => { thOpen(); if (k.liveSeg) k.liveSeg = false; else k.t.nextBlock(); return k.t.final(text); });               // new: lands; continues the words she watched being written
  }
  function thHer(s) {               // her note / follow-up
    const k = K, text = String(s.text || ''); thGroupDone();
    if (k.pend) { const p = k.pend; k.pend = null;                                  // shown when she sent it: this step is that bubble
      return thLater(() => { const b = p.node && p.node.querySelector('.hck-bub'); if (b && text && b.textContent !== text) b.textContent = text; }); }
    const still = k.hist;
    thLater(() => { thEnd(); editable(k.t.her(text, {still}), s.n, text); thTail(); if (!still && k.task.running) thOpen(); });
  }
  /* v0.999 the box's pickers, as in Claude Code: '@' + letters = files of the working copy, '/' at the start = commands
     (Hoola's and this repo's own .claude/commands). Click (or Tab / Enter on the first) puts it in the box. */
  let PICK = null, PICK_T = 0, REPOCMD = null;
  // v0.999 every Claude Code built-in command, typed in the box (built-in names win over a repo command of the same name)
  const TERMINAL_ONLY = ['vim', 'terminal-setup', 'statusline', 'ide', 'exit', 'quit', 'upgrade', 'bug', 'release-notes', 'privacy-settings'];
  const BUILTIN = {
    help: {d: 'Every command you can type here', run: () => helpDlg()},
    clear: {d: 'Start fresh: a new session on this repo (this one stays in the list)', run: () => clearNow()},
    compact: {d: 'Summarise the conversation so far · add what to keep after it', args: true, run: a => compactNow(a)},
    context: {d: 'How full the conversation is', run: () => ACTS.ctxinfo()},
    init: {d: 'Write the repo\u2019s AGENTS.md', run: () => initNow()},
    review: {d: 'Review this branch\u2019s changes - nothing is changed', args: true,
      send: 'Review the changes on this branch like a careful reviewer: bugs, risks and missing tests. Change nothing; report each finding with path:line.'},
    'pr-comments': {d: 'Read the reviewers\u2019 comments on the pull request', run: () => prComments()},
    export: {d: 'Download the conversation as a file', run: () => exportNow()},
    rewind: {d: 'Go back to a checkpoint: code, conversation or both', run: () => rewindPick()},
    resume: {d: 'Open another session', run: () => show('all')},
    model: {d: 'The quality tier, which picks the model', run: () => modelNow()},
    'output-style': {d: 'How Hoola explains its work', args: true, run: a => a ? setStyle(a) : styleMenu($('#hcdNote'))},
    style: {d: 'Same as /output-style', args: true, run: a => a ? setStyle(a) : styleMenu($('#hcdNote')), alias: true},
    cost: {d: 'What this session has cost so far', run: () => costDlg()},
    usage: {d: 'This session\u2019s cost and your month', run: () => costDlg()},
    status: {d: 'Repo, branch, mode, environment, pull request, context', run: () => statusDlg(false)},
    doctor: {d: 'Check this session\u2019s setup for problems', run: () => statusDlg(true)},
    todos: {d: 'Hoola\u2019s to-do list in this session', run: () => todosDlg()},
    bashes: {d: 'Commands running in the background', run: () => openTerm()},
    agents: {d: 'This repo\u2019s agents: add or change them', run: () => claudeFiles('.claude/agents/')},
    hooks: {d: 'This repo\u2019s hooks (.claude/settings.json)', run: () => settingsFile()},
    permissions: {d: 'Allow / ask / deny rules (.claude/settings.json)', run: () => settingsFile()},
    memory: {d: 'The repo\u2019s rules for Hoola (CLAUDE.md)', run: () => memoryFile()},
    mcp: {d: 'MCP servers this repo names', run: () => repoSetup()},
    plugin: {d: 'Your Claude Code plugins', run: () => pluginsDlg()},
    plugins: {d: 'Same as /plugin', run: () => pluginsDlg(), alias: true},
    config: {d: 'Hoola Code settings', run: () => show('settings')},
    'add-dir': {d: 'Other repos for this session', run: () => toast('Attach other repos when you start a session (Other repos). A running session keeps its repos.')},
    login: {d: 'GitHub access (Settings)', run: () => show('settings')},
    logout: {d: 'GitHub access (Settings)', run: () => show('settings'), alias: true},
    'install-github-app': {d: 'GitHub access (Settings)', run: () => show('settings'), alias: true},
  };
  TERMINAL_ONLY.forEach(n => { BUILTIN[n] = {d: 'Terminal only', terminal: true, run: () => toast(`/${n} is a terminal command of Claude Code - Hoola Code does not need it.`)}; });
  const HOOLA_CMDS = Object.entries(BUILTIN).filter(([, w]) => !w.terminal && !w.alias).map(([n, w]) => [n, w.d])
    .concat([['security-review', 'Review the changes for security problems']])      // sent to Hoola as it is (the server knows it)
    .sort((a, b) => a[0] < b[0] ? -1 : 1);
  function pickClose() { PICK = null; const b = $('#hcdPick'); if (b) b.remove(); }
  function pickFor(ta) {
    if (!TASK || shared) return pickClose();
    const pos = ta.selectionStart || 0, before = ta.value.slice(0, pos), at = /(^|\s)@([\w./-]*)$/.exec(before), sl = /^\/([\w-]*)$/.exec(before);
    clearTimeout(PICK_T);
    if (at) { PICK_T = setTimeout(async () => { let r; try { r = await api('GET', `/api/devsahayak/tasks/${tid()}/find?q=${encodeURIComponent(at[2])}`); } catch (e) { return pickClose(); }
        pickShow((r.files || []).slice(0, 8).map(f => ({v: '@' + f + ' ', label: f, mono: true})), at[2].length + 1); }, 220); return; }
    if (sl) { (async () => { if (!REPOCMD || REPOCMD.tid !== TASK.id) { try { REPOCMD = {tid: TASK.id, ...(await api('GET', `/api/devsahayak/tasks/${tid()}/commands`))}; } catch (e) { REPOCMD = {tid: TASK.id, commands: []}; } }
        const q = sl[1].toLowerCase(), rows = HOOLA_CMDS.map(([n, d]) => ({v: '/' + n + ' ', label: '/' + n, sub: d}))
          .concat((REPOCMD.commands || []).map(c => ({v: '/' + c.name + ' ', label: '/' + c.name, sub: (c.description || '') + (c.hint ? ' · ' + c.hint : ''), repo: true})));
        pickShow(rows.filter(r => r.label.slice(1).startsWith(q)).slice(0, 8), sl[1].length + 1); })(); return; }
    pickClose();
  }
  function pickShow(rows, cut) {
    const ta = $('#hcdNote'); if (!ta || !rows.length) return pickClose();
    PICK = {rows, cut};
    let b = $('#hcdPick'); if (!b) { b = document.createElement('div'); b.id = 'hcdPick'; b.className = 'hcd-pick'; b.setAttribute('role', 'listbox'); $('#hcdSteer').append(b); }
    b.innerHTML = rows.map((r, i) => `<button type="button" role="option" class="hcd-pickr" data-act="pick" data-i="${i}">${r.mono ? `<code>${esc(r.label)}</code>` : `<b>${esc(r.label)}</b>`}${r.sub ? `<small>${esc(r.sub)}</small>` : ''}${r.repo ? '<em>this repo</em>' : ''}</button>`).join('');
  }
  function pickTake(i) {
    const ta = $('#hcdNote'), r = PICK && PICK.rows[i]; if (!ta || !r) return;
    const pos = ta.selectionStart || 0, a = ta.value.slice(0, pos - PICK.cut), z = ta.value.slice(pos);
    ta.value = a + r.v + z; const c = (a + r.v).length; ta.focus(); ta.setSelectionRange(c, c); grow(ta); pickClose();
  }
  function editable(node, n, text) {   // v0.999 edit an earlier message of hers and ask again
    if (!node || shared || n == null || !text) return node;
    const b = document.createElement('button'); b.type = 'button'; b.className = 'hcd-editmsg'; b.dataset.act = 'editmsg'; b.dataset.n = String(n);
    b.setAttribute('aria-label', 'Edit this message and ask again'); b.title = 'Edit and ask again'; b.innerHTML = svg('pencil') + '<span>Edit</span>';
    node.append(b); return node;
  }
  function thWork(i) {              // a step of work: into the piece of work it belongs to
    const k = K;
    if (!k.cur) { const g = k.cur = {from: i, to: i, node: document.createElement('div'), html: null, done: false}; g.node.className = 'hcd-wgrp'; g.node.hidden = true;
      thLater(() => { thOpen(); k.ho.insertBefore(g.node, k.work); }); }
    k.cur.to = i + 1;
  }
  function thGroupDraw(g) {
    const t = K.task, steps = t.steps || [], inner = rowsHTML(t, g.from, g.to); let html = inner;
    if (inner && g.done && P.view === 'normal') {
      const secs = Math.round((Date.parse(steps[g.to - 1].at) - Date.parse(g.from > 0 ? steps[g.from - 1].at : t.at)) / 1000), key = 'w' + g.from;
      html = `<details class="hck-fold" data-wk="${key}"${OPEN.has(key) ? ' open' : ''}><summary><span class="sm">Worked${isFinite(secs) ? ' for ' + esc(HoolaChat.fmtSecs(Math.max(1, secs))) : ''}</span>${DN}</summary><div class="hck-tl hcd-wk">${inner}</div></details>`;
    }
    if (html === g.html) return; g.html = html; g.node.innerHTML = html; g.node.hidden = !html;
  }
  function thGroupDone() { const g = K.cur; if (!g) return; K.cur = null; g.done = true; thGroupDraw(g); }     // words follow it, or the round is over: it folds
  function thStep(s, i) {
    if (!s) return;
    if (s.k === 'note') thHer(s);
    else if (s.k === 'say') thSay(s.text);
    else if (s.k === 'round' && P.view !== 'verbose') { /* its time is on the folds */ }
    else thWork(i);
  }
  function thStart(t, col, key) {
    const feed = $('#hcdFeed'), same = K && K.col === col;
    const o = same ? K.o : {acts: ['copy', 'aloud'], jump: true, scroller: feed, startedAt: 0};
    let kit = same ? K.t : null; K = null;
    if (!kit) { kit = HoolaChat.mount(col, o);
      col.addEventListener('toggle', ev => { const d = ev.target; if (d.dataset && d.dataset.wk) d.open ? OPEN.add(d.dataset.wk) : OPEN.delete(d.dataset.wk); }, true); }
    kit.clear();
    const tail = document.createElement('div'); tail.className = 'hcd-tail'; tail.hidden = true;
    K = {col, o, t: kit, key, head: headOf(t), ids: [], task: t, cur: null, open: false, ho: null, work: null, chain: Promise.resolve(), q: 0,
      liveSeg: false, lastSay: '', said: '', pend: null, tail, tailSig: '', hist: true};
    o.scroller = NOWHERE;
    const att = t.attach || []; let pi = 0;
    if (t.text || att.length) { const me = editable(kit.her(t.text || '', {still: true}), -1, t.text || '');
      if (att.length) { const d = document.createElement('div'); d.className = 'hcd-atts';
        d.innerHTML = att.map(a => a.kind === 'image'
          ? `<img class="hcd-pic" data-att="${pi++}" alt="${esc(a.name)}" title="${esc(a.name)}"${PICS.has(t.id + ':' + (pi - 1)) ? ` src="${PICS.get(t.id + ':' + (pi - 1))}"` : ''}>`
          : `<span class="hcd-att">${svg('read')}<span>${esc(a.name)}</span><small>${kb(a.size)}</small></span>`).join('');
        me.prepend(d); } }
    col.append(tail);
  }
  function thread(t) {
    const col = $('#hcdCol'), feed = $('#hcdFeed'); if (!col || !feed || !window.HoolaChat) return;
    const steps = t.steps || [], ids = steps.map(stepId), key = t.id + '|' + P.view;
    const more = K && K.col === col && K.key === key && K.head === headOf(t) && K.ids.length <= ids.length && K.ids.every((x, i) => x === ids[i]);
    const atEnd = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 90, y = K && K.col === col && K.task && K.task.id === t.id ? feed.scrollTop : -1;
    if (!more) thStart(t, col, key);
    const k = K, fresh = k.hist; k.task = t;
    for (let i = k.ids.length; i < steps.length; i++) thStep(steps[i], i);
    k.ids = ids;
    if (k.cur) thGroupDraw(k.cur);                                               // the work going on now: its rows, as they come
    if (!t.running) {
      thGroupDone();
      const ex = String(t.explain || '').trim();
      if (ex && ex !== k.said && !steps.some(x => x.final)) { k.said = ex; if (ex !== k.lastSay) thSay(ex); }   // an older session's closing answer is a reply too
      if (k.open || k.q) thLater(thEnd);
    } else if (!k.open) thLater(thOpen);
    if (fresh) {                                                                 // history is in: whole and still
      col.querySelectorAll('.hck-txt .w').forEach(w => w.replaceWith(w.textContent));
      col.querySelectorAll('.hck-acts').forEach(a => { a.style.animation = 'none'; });
      if (k.open) { k.ho.append(k.work); k.work.hidden = false; }
      k.o.scroller = feed; k.hist = false;
    }
    if (t.running && k.open) { k.t.label(nowLabel(t)); liveOut(t); } else liveOut({});
    const live = t.running ? String(t.live || '').trim() : '';                  // the words being written right now land as they come
    if (live && !k.q && live !== k.lastSay && !k.lastSay.startsWith(live)) { thGroupDone(); thOpen(); if (!k.liveSeg) { k.t.nextBlock(); k.liveSeg = true; } k.t.text(live); }
    const th = t.status === 'plan_wait' && t.plan ? planHTML(t) : !t.running ? doneHTML(t) : '';      // the cards under the thread
    if (th !== k.tailSig) { k.tailSig = th; k.tail.innerHTML = th; k.tail.hidden = !th; }
    thTail();
    k.stick = !k.t.holding && (fresh ? y < 0 : atEnd);                                             // she is at the newest: stay there (paint() asks again once the bar under the feed is drawn)
    if (fresh && y >= 0) feed.scrollTop = y; else if (k.stick) feed.scrollTop = feed.scrollHeight;
  }
  function threadStay() { const feed = $('#hcdFeed'); if (K && K.stick && !K.t.holding && feed) feed.scrollTop = feed.scrollHeight; }
  function herNow(text) {           // her follow-up / answer shows the moment she sends; the step that carries it is this bubble
    const k = K; if (!k) return null; const p = {text, node: null}; k.pend = p;
    thLater(() => { thEnd(); p.node = k.t.her(text); thTail(); }); return p;
  }
  function herBack(p) {             // it did not go: the bubble goes, her words are back in the box
    if (!p) return; const k = K; if (!k) return void (p.node && p.node.remove());
    if (k.pend === p) k.pend = null; thLater(() => { if (p.node) p.node.remove(); });
  }
  function nowDoing(t) {
    const s = (t.steps || []).filter(x => !['say', 'note', 'think', 'pass'].includes(x.k)).pop();
    if (!s) return 'Reading the repo…';
    return ({edit: 'Checking the edit…', new: 'Checking the new file…', check: s.ok ? 'Finishing up…' : 'Looking at the failure…', read: 'Reading the code…', search: 'Searching the code…'})[s.k] || 'Working on the next step…';
  }

  // ------------------------------------------------------------------ session: the rail ---
  function stages(t) {
    const st = t.steps || [], has = (...ks) => st.some(s => ks.includes(s.k)), last = k => st.filter(s => s.k === k).pop();
    // v0.784 a command run in the box counts as running her tests
    const bs = last('bash'), ck = last('check') || (bs ? {ok: bs.rc === 0} : null), ci = t.ci?.state, rows = [['Read the code', has('read', 'search', 'list', 'usages', 'rules') ? 'done' : 'todo', '']];
    if (t.kind !== 'explain') {               // v0.999 the stages of the approved design ("The run")
      const pl = t.plan || {}, hasPlan = !!(pl.goal || (pl.steps || []).length) || t.status === 'plan_wait';
      if (hasPlan) rows.push(['Plan', t.status === 'plan_wait' ? 'now' : 'done', t.status === 'plan_wait' ? 'Waiting for your yes' : 'Approved by you']);
      rows.push(['Write the change', has('edit', 'new') ? 'done' : 'todo', has('edit', 'new') ? plural(editedFiles(t).length, 'file') : '']);
      rows.push(['Run your tests', ck ? (ck.ok ? 'done' : 'bad') : has('check_off') ? 'off' : 'todo', ck ? (ck.ok ? 'passed' : 'failed') : has('check_off') ? 'could not run' : '']);
      rows.push(['Own review', has('diff') || t.self_review?.verdict ? 'done' : 'todo', t.self_review?.verdict ? (t.self_review.verdict === 'ok' ? 'Clean' : 'Points open') : '']);
      rows.push(['Pull request', t.pr_number ? 'done' : 'todo', t.pr_number ? `#${t.pr_number}${t.branch ? ' on ' + t.branch : ''}` : '']);
      rows.push(['GitHub checks', ci === 'success' ? 'done' : ci === 'failure' ? 'bad' : 'todo', (CI[ci] || ['', ''])[1] && t.pr_number ? CI[ci][1] : '']);
      rows.push(['Merge', t.status === 'merged' ? 'done' : 'todo', t.status === 'merged' ? 'Merged by you' : t.pr_number && ci === 'success' ? 'Your tap' : '']);
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
    const acts = []; if (t.running || shared) return acts;
    if (['pr_open', 'checks_failed'].includes(t.status) && (t.pr_comments || []).length) acts.push(`<button type="button" class="hcd-btn" data-act="fixcomments">Fix ${plural(t.pr_comments.length, "reviewer comment")}</button>`);
    if (t.status === 'ready' && t.hash) acts.push(`<button type="button" class="hcd-btn pri" data-act="push">Open the pull request</button>`);
    if (t.status === 'checks_failed') acts.push(`<button type="button" class="hcd-btn pri" data-act="fixci">Fix the CI failure</button>`);
    if (['pr_open', 'checks_failed'].includes(t.status) && t.pr_number && !MERGE) acts.push(`<button type="button" class="hcd-btn${t.status === 'pr_open' && t.ci?.state === 'success' ? ' ok' : ''}" data-act="mergereq">Merge…</button>`);
    if (t.pr_url) acts.push(`<a class="hcd-btn" href="${esc(t.pr_url)}" target="_blank" rel="noopener noreferrer">View PR</a>`);
    if (['pr_open', 'checks_failed', 'ci_running'].includes(t.status)) acts.push(`<button type="button" class="hcd-btn" data-act="refresh">Check CI again</button>`);
    return acts;
  }
  function wsCard(t) {      // v0.784 the session's working copy: checkpoints (rewind), browse files (v0.999.245 the to-do list shows once, in the conversation)
    const w = t.ws || {}; if (!w.exists) return '';
    const todos = w.todos || [], cps = (w.checkpoints || []).slice(-6).reverse();
    return `<section class="hcd-rc" aria-labelledby="hcdRcW"><h2 id="hcdRcW">Working copy${w.live ? '<span class="hcd-stat">working</span>' : ''}</h2>
      ${todos.length ? `<p class="hcd-mut">${plural(todos.filter(x => x.status === 'completed').length, 'step')} of ${todos.length} done - the list is in the conversation.</p>` : ''}
      ${cps.length ? cps.map(c => `<div class="hcd-row"><span title="${esc(c.label || '')}">Checkpoint ${c.n}</span><b>${esc((c.label || '').slice(0, 34))}</b>${!t.running && c.n !== (w.checkpoints || []).length ? `<button type="button" class="hcd-btn sm" data-act="rewind" data-n="${c.n}">Go back</button>` : ''}${!t.running && !shared ? `<button type="button" class="hcd-btn sm" data-act="forkcp" data-n="${c.n}" title="A new session from this point">Fork</button>` : ''}</div>`).join('') : '<p class="hcd-mut">A checkpoint is saved after every round.</p>'}
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
  function passList(t) {          // the passes beside the main work, each start paired with its end
    const out = []; (t.steps || []).forEach(s => { if (s.k !== 'pass') return;
      if (s.state === 'start') out.push({name: s.name, at: s.at, note: s.note || '', run: true});
      else { const x = [...out].reverse().find(y => y.name === s.name && y.run); if (x) { x.run = false; x.end = s.at; x.ok = s.ok; if (s.note) x.res = s.note; } } });
    if (!t.running) out.forEach(x => { x.run = false; });
    return out;
  }
  function passCard(t) {
    const ps = passList(t); if (!ps.length) return '';
    return `<section class="hcd-rc" aria-labelledby="hcdRcA"><h2 id="hcdRcA">Passes<span class="hcd-stat">${ps.length}</span></h2>
      ${ps.map(x => `<div class="hcd-stage ${x.run ? 'now' : x.ok === false ? 'bad' : 'done'}">${x.run ? '<i class="hcd-pulse sm" aria-hidden="true"></i>' : svg(x.ok === false ? 'bad' : 'ok', x.ok === false ? 'bad' : 'ok')}<span>${esc(PASS[x.name] || x.name)}</span><small title="${esc(x.note)}">${esc(x.run ? 'running' : (x.res || 'done'))}${x.end ? ' · ' + esc(since(x.at, x.end)) : ''}</small></div>`).join('')}</section>`;
  }
  function commentsCard(t) {      // people's comments on her pull request (read from GitHub, shown as data)
    if (shared || !t.pr_number || !['pr_open', 'checks_failed', 'ci_running'].includes(t.status)) return '';
    const pc = t.pr_comments || [];
    return `<section class="hcd-rc" aria-labelledby="hcdRcR"><h2 id="hcdRcR">Reviewers' comments${pc.length ? `<span class="hcd-stat">${pc.length} new</span>` : ''}</h2>
      ${pc.length ? pc.slice(0, 6).map(c => `<div class="hcd-pc"><b>${esc(c.who || 'someone')}</b>${c.path ? ` <code>${esc(c.path)}${c.line ? ':' + c.line : ''}</code>` : ''}<p>${esc(String(c.text || '').slice(0, 240))}</p></div>`).join('') + (pc.length > 6 ? `<p class="hcd-mut">and ${pc.length - 6} more</p>` : '')
        : '<p class="hcd-mut">No new comments from people on this pull request.</p>'}
      <div class="hcd-acts">${pc.length && !t.running && t.status !== 'ci_running' ? `<button type="button" class="hcd-btn pri" data-act="fixcomments">Fix ${plural(pc.length, 'comment')}</button>` : ''}<button type="button" class="hcd-btn" data-act="readcomments">Check for comments</button></div>
      <p class="hcd-mut">Hoola decides which comments are right and says which it did not follow.${t.auto_fix ? '' : ' Auto-fix is off, so they wait for your tap.'}</p></section>`;
  }
  function railHTML(t) {
    const files = editedFiles(t), kv = (a, b) => `<div class="hcd-row"><span>${a}</span><b>${b}</b></div>`;
    const checks = []; const pf = PROOF[t.proof?.state]; if (pf) checks.push(kv('Proof', `<span class="hcd-c ${pf[0]}">${esc(pf[1])}</span>`));
    const ci = CI[t.ci?.state]; if (t.pr_number && ci) checks.push(kv('CI on GitHub', `<span class="hcd-c ${ci[0]}">${esc(ci[1])}${t.rounds ? ` · round ${t.rounds}` : ''}</span>`));
    if (t.self_review?.verdict) checks.push(kv("Hoola's own review", `<span class="hcd-c ${t.self_review.verdict === 'ok' ? 'ok' : 'warn'}">${t.self_review.verdict === 'ok' ? 'Clean' : plural((t.self_review.problems || []).length, 'point') + ' open'}</span>`));
    if (!t.running && t.kind !== 'explain' && files.length) checks.push(kv('Security checks', `<span class="hcd-c ${(t.checks || []).length ? 'warn' : 'ok'}">${(t.checks || []).length ? plural(t.checks.length, 'note') : 'Clean'}</span>`));
    const acts = actsFor(t).filter(a => !a.includes('data-act="fixcomments"'));      // the reviewers' card below has that button
    const sg = {done: svg('ok', 'ok'), bad: svg('bad', 'bad'), now: '<i class="hcd-pulse sm" aria-hidden="true"></i>', off: svg('bad'), todo: '<i class="hcd-ring" aria-hidden="true"></i>'};
    const env = t.env || {id: 'auto', name: 'Auto'}, rows = stages(t), doneN = rows.filter(r => r[1] === 'done').length;
    const last = (t.steps || []).length ? (t.steps || [])[(t.steps || []).length - 1].at : '', mins = Math.max(1, Math.round(((t.running ? Date.now() : Date.parse(last || t.at)) - Date.parse(t.at)) / 60000));
    return `<section class="hcd-rc hcd-runrc" aria-labelledby="hcdRcP"><h2 id="hcdRcP">The run<span class="hcd-stat">${doneN} of ${rows.length} · ${mins} min</span></h2>
        <ol class="hcd-run" role="list" aria-label="The run, stage by stage">${rows.map(([name, s, note], i) => `<li class="hcd-rs ${s}"><span class="hcd-rsd" aria-hidden="true">${s === 'done' ? '\u2713' : s === 'bad' ? '!' : ''}</span>${i < rows.length - 1 ? '<span class="hcd-rsl" aria-hidden="true"></span>' : ''}<span class="hcd-rst"><b>${name}</b>${note ? `<small>${esc(note)}</small>` : ''}</span><span class="hcd-sr">${{done: 'done', now: 'working now', bad: 'failed', off: 'not run', todo: 'not yet'}[s] || ''}</span></li>`).join('')}</ol></section>
      <section class="hcd-rc hcd-envrc" aria-labelledby="hcdRcE"><h2 id="hcdRcE">Environment</h2>
        <div class="hcd-envl">${svg('cloud')}<b>${esc(env.name || 'Auto')}</b><span class="hcd-flex"></span>${t.running ? '<span class="hcd-c ok">Ready</span>' : ''}${shared ? '' : `<button type="button" class="hcd-icb" data-menu="senv" aria-label="Change the cloud environment" title="Cloud environment">${svg('gear')}</button>`}</div>
        <div class="hcd-envl">${svg('read')}<span>${esc(t.repo || '')}</span></div>
        ${t.branch ? `<div class="hcd-envl">${svg('pr')}<code class="hcd-br">${esc(t.branch)}</code></div>` : ''}</section>
      <section class="hcd-rc" aria-labelledby="hcdRcC"><h2 id="hcdRcC">Changes<span class="hcd-stat">${stat({files})}</span></h2>
        ${files.length ? files.map(f => `<button type="button" class="hcd-file" data-act="file" data-path="${esc(f.path)}" title="Open ${esc(f.path)} in Changes"><code>${esc(f.path)}</code><span><em class="add">+${f.added || 0}</em> <em class="del">−${f.removed || 0}</em></span></button>`).join('') : '<p class="hcd-mut">No changes yet.</p>'}
        ${t.pr_number ? `<div class="hcd-row"><span>Pull request</span><b>#${t.pr_number} · ${esc(STATUS[t.status] || t.status)}</b>${shared ? '' : `<button type="button" class="hcd-icb" data-menu="pr" aria-label="Pull request menu: auto-fix, checkout command" title="Pull request menu">${svg('more')}</button>`}</div>` : ''}${checks.join('')}
        ${acts.length ? `<div class="hcd-acts">${acts.join('')}</div>` : ''}</section>
      ${commentsCard(t)}${wsCard(t)}${passCard(t)}

      <section class="hcd-rc" aria-labelledby="hcdRcS"><h2 id="hcdRcS">Session</h2>${kv('Repo', esc(t.repo || ''))}${t.branch ? kv('Branch', `<code>${esc(t.branch)}</code>`) : ''}
        ${t.base ? kv('Works from', `<code>${esc(t.base)}</code>`) : ''}${kv('Kind', esc((KINDS.find(k => k[0] === t.kind) || [0, t.kind])[1]))}
        ${t.mode ? kv('Mode', esc((MODES.find(m => m[0] === t.mode) || [0, t.mode])[1])) : ''}${t.tier ? kv('Job size', esc(t.tier)) : ''}
        ${(t.refs || []).length ? kv('Also reads', esc(t.refs.join(', '))) : ''}${(t.group || []).map(g => `<div class="hcd-row"><span>Same job in</span><b>${esc(g.repo)}${g.pr_number ? ' · PR #' + g.pr_number : ''}</b>${shared ? '' : `<button type="button" class="hcd-btn sm" data-tid="${esc(g.id)}">Open</button>`}</div>`).join('')}
        ${t.sched_id ? kv('Started by', 'a scheduled task') : ''}
        ${kv('Steps', String((t.steps || []).filter(s => s.k !== 'think' && s.k !== 'pass').length))}${t.cost && t.cost.calls ? kv('Cost so far', `<span title="List price of this session's ${t.cost.calls} model calls - an estimate, not a bill">${rs(t.cost.inr)}</span>`) : ''}${kv('Started', esc(ago(t.at)))}</section>`;
  }

  // ------------------------------------------------------------------ session: mount once, paint what changed ---
  const sessFrame = () => `<div class="hcd-sess-wrap"><main class="hcd-main">
        <header class="hcd-top" id="hcdTop"></header>
        <div class="hcd-feed" id="hcdFeed"><div class="hcd-col" id="hcdCol"><p class="hcd-mut">Opening…</p></div></div>
        <div class="hcd-queue" id="hcdQueue"></div>
        <div class="hcd-bar" id="hcdBar"></div>
        <div class="hcd-cc" id="hcdCc"></div>
        <form class="hcd-cp" id="hcdSteer"><label for="hcdNote" class="hcd-sr">Message Hoola</label>
          <textarea id="hcdNote" rows="1" maxlength="4000"></textarea><span class="hcd-hintk" id="hcdHintK" aria-hidden="true"></span><span class="hcd-cpb" id="hcdCpB"></span></form>
        <div class="hcd-cpmeta" id="hcdCpMeta"></div>
      </main><section class="hcd-pane" id="hcdPane" aria-label="Changes" hidden></section><aside class="hcd-rail" id="hcdRail" aria-label="Session details"></aside></div>`;
  /* The read-only page of ONE shared session (/console/code/shared/<token>): the same drawing, nothing that acts. */
  async function openShared() {
    EL.innerHTML = `<div class="hcd" data-side="none" data-rail="${P.rail}"><div class="hcd-body" id="hcdBody"></div><dialog class="hcd-dlg" id="hcdDlg"></dialog></div>`;
    if (WIRED !== EL) { WIRED = EL; EL.addEventListener('click', onClick); }
    let t; try { t = await api('GET', '/api/devsahayak/shared/' + encodeURIComponent(shared)); }
    catch (e) { body(`<main class="hcd-home"><h1>This link is not active</h1><p class="hcd-lede">Its owner stopped sharing it, or its 7 days are over.</p></main>`); return; }
    VIEW = 'session'; TID = t.id; TASK = t; SIG = {}; document.title = (t.title || 'A shared session') + ' · Hoola Code';
    body(sessFrame()); paint();
  }
  async function session(tid) {
    body(sessFrame());
    await refreshTask(tid, true);
    liveOpen(tid);
    let beat = 0;
    POLL = setInterval(() => { if (VIEW !== 'session' || TID !== tid || !EL.isConnected) return;
      beat++; stepClock();
      if (beat % 2) return;                                              // the page asks every 2 s ...
      if (LIVE && LIVE.ok && TASK?.running && beat % 6) return;           // ... every 6 s while the live stream carries the words
        if (PANE && PANE.term && beat % 2 === 0) termLoad();
      if (TASK?.running || ['ci_running', 'new'].includes(TASK?.status)) refreshTask(tid, false); else tick(); }, 1000);
  }
  /* v0.999 THE LIVE STREAM, as Claude Code shows its work: the words as they are written, the step running now with its
     own clock, and the last lines its command printed - pushed every 100 ms over /stream (fetch, so her sign-in goes with
     it). A new step number fetches the steps at once; a dropped stream comes back by itself, the 2 s refresh covers the gap. */
  let LIVE = null, LIVE_RAF = 0, SKEW = 0;
  function liveClose() { if (LIVE) { try { LIVE.ctrl.abort(); } catch (e) { /* gone */ } LIVE = null; } }
  function liveOpen(tid) {
    liveClose(); if (shared || !window.TextDecoder) return;
    const me = LIVE = {tid, ctrl: new AbortController(), ok: false, tries: 0};
    (async function run() {
      while (LIVE === me) {
        try {
          const r = await api('GET', `/api/devsahayak/tasks/${encodeURIComponent(tid)}/stream`, undefined, {raw: true, signal: me.ctrl.signal});
          if (!r.body) return; me.ok = true; me.tries = 0;
          const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
          for (;;) { const {value, done} = await rd.read(); if (done || LIVE !== me) break;
            buf += dec.decode(value, {stream: true}); let at;
            while ((at = buf.indexOf('\n\n')) >= 0) { const chunk = buf.slice(0, at); buf = buf.slice(at + 2);
              const line = chunk.split('\n').find(x => x.startsWith('data: ')); if (!line) continue;
              try { liveEvent(JSON.parse(line.slice(6))); } catch (e) { /* a bad line is skipped */ } } }
        } catch (e) { if (LIVE !== me) return; }
        me.ok = false; me.tries++;
        await new Promise(res => setTimeout(res, Math.min(15000, 1000 * me.tries)));
      }
    })();
  }
  function liveEvent(ev) {
    const t = TASK, tid = LIVE && LIVE.tid; if (!t || t.id !== tid && t.number !== tid) return;
    const p = ev && ev.payload || {};
    if (ev.kind === 'code_open') { if (p.srv) SKEW = Date.now() / 1000 - p.srv; }
    if ('live' in p) t.live = p.live; if ('add' in p) t.live = String(t.live || '') + p.add;
    if ('now' in p) t.now = p.now;
    const ni = t.now_info = {...(t.now_info || {})}; ['out', 't0', 'tool'].forEach(k => { if (k in p) ni[k] = p[k]; });
    if ('ask' in p) { t.ask = p.ask; if (TASK === t) { put('#hcdBar', 'bar', barHTML(t)); } }
    if ('ctx' in p) { t.ctx = p.ctx; if (TASK === t) drawMeta(t); }
    if (('n' in p && p.n > (t.last_n ?? -1)) || ('running' in p && p.running !== t.running)) { liveRefresh(); return; }
    if (LIVE_RAF) return;
    LIVE_RAF = requestAnimationFrame(() => { LIVE_RAF = 0; if (VIEW === 'session' && TASK === t) thread(t); });
  }
  async function liveRefresh() {    // one refresh at a time; a step that came in meanwhile asks once more after it
    const me = LIVE; if (!me) return; if (me.busy) { me.again = true; return; }
    me.busy = true; try { await refreshTask(TID, false); } finally { me.busy = false; if (me.again && LIVE === me) { me.again = false; liveRefresh(); } }
  }
  const stepSecs = t => { const t0 = +(t.now_info && t.now_info.t0) || 0; return t0 ? Math.max(0, Math.floor(Date.now() / 1000 - SKEW - t0)) : -1; };
  function stepClock() { if (K && K.open && TASK?.running && K.task === TASK) { K.t.label(nowLabel(TASK)); liveOut(TASK); } }
  function liveOut(t) {             // the last lines the running command printed, under the working row (her live terminal)
    const k = K; if (!k || !k.work) return;
    const ni = t.now_info || {}, lines = t.running && ni.tool === 'bash' ? (ni.out || []).slice(-8) : [];
    let pre = k.work.nextElementSibling; if (!pre || !pre.classList.contains('hcd-out')) pre = null;
    if (!lines.length) { if (pre) pre.remove(); return; }
    if (!pre) { pre = document.createElement('pre'); pre.className = 'hcd-term hcd-out'; pre.setAttribute('aria-live', 'off'); k.work.after(pre); }
    const txt = lines.join('\n'); if (pre.textContent !== txt) pre.textContent = txt;
  }
  async function refreshTask(tid, first) {
    let t; try { t = await api('GET', `/api/devsahayak/tasks/${encodeURIComponent(tid)}`); } catch (e) { if (first) { toast(e.message, true); show('home'); } return; }
    if (VIEW !== 'session' || TID !== tid) return;
    if (t.srv_now) SKEW = Date.now() / 1000 - t.srv_now;
    const was = TASK && TASK.id === tid ? TASK : null; TASK = t;
    if (was && was.running && !t.running) { await load(); drawSide();
      setTimeout(() => { if (VIEW === 'session' && TID === tid && TASK && !TASK.running && !TASK.hint) refreshTask(tid, false); }, 4000); }   // the suggestion is written a moment after the run ends
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
  // v0.999 the one status pill of the design: Working / Needs your yes / Ready to merge / Merged
  const yesPill = t => t.ask ? 'Needs your yes' : t.status === 'plan_wait' ? 'Plan needs your yes' : (!t.running && t.question) ? 'Hoola asks you' : t.status === 'ready' ? 'Needs your yes' : '';
  function tick() { const c = $('#hcdClock'); if (c && TASK?.running && !TASK.stopping) c.textContent = `Working · ${dur(Math.max(0, (Date.now() - Date.parse(TASK.run_at || TASK.at)) / 1000))}`; }
  function paint() {
    const t = TASK; if (!t || !$('#hcdTop')) return;
    const files = editedFiles(t), railOn = railShown();
    put('#hcdTop', 'top', `${shared ? `<img class="hcd-mark" src="/static/hoola-mark.png" alt="" width="24" height="24"><b class="hcd-title ro">${esc(t.title || t.number)}</b>` : `<button type="button" class="hcd-title" data-act="rename" title="Rename">${esc(t.title || t.number)}</button>`}
      <button type="button" class="hcd-icb" data-menu="title" aria-label="${shared ? 'Transcript view' : 'Session menu: rename, transcript view, share, archive, delete'}" title="${shared ? 'Transcript view' : 'Session menu'}">${svg('down')}</button>
      <span class="hcd-flex"></span>
      ${yesPill(t) ? `<span class="hcd-pill need">${svg('dot')}${esc(yesPill(t))}</span>` : t.running ? `<span class="hcd-live" id="hcdClock">${t.stopping ? 'Stopping after this step' : 'Working'}</span>` : t.status === 'merged' ? `<span class="hcd-pill ok">Merged</span>` : t.pr_number && t.ci?.state === 'success' && !shared ? `<a class="hcd-prpill ok" href="${esc(t.pr_url || '#')}" target="_blank" rel="noopener noreferrer" title="Open the pull request on GitHub">${svg('pr')}Ready to merge · PR #${t.pr_number}</a>` : t.pr_number && !shared ? `<a class="hcd-prpill ${dotc(t)}" href="${esc(t.pr_url || '#')}" target="_blank" rel="noopener noreferrer" title="Open the pull request on GitHub">${svg('pr')}PR #${t.pr_number} · ${esc(t.ci?.state === 'success' ? 'checks passing' : t.ci?.state === 'failure' ? 'checks failing' : STATUS[t.status] || t.status)}</a>` : `<span class="hcd-pill ${dotc(t)}">${esc(STATUS[t.status] || t.status)}</span>`}
      ${files.length ? `<button type="button" class="hcd-btn sm hcd-chg" data-act="changes" aria-pressed="${!!PANE}" title="${PANE ? 'Close' : 'Open'} the Changes pane">Changes <span class="hcd-stat">${stat({files})}</span></button>` : ''}
      <button type="button" class="hcd-icb" data-act="rail" aria-pressed="${railOn}" aria-label="${railOn ? 'Hide' : 'Show'} session details" title="${railOn ? 'Hide' : 'Show'} session details">${svg('rail')}</button>
      ${!shared && t.ws?.exists ? `<button type="button" class="hcd-icb" data-act="files" data-path="" aria-label="Browse the working copy" title="Browse the working copy">${svg('folder')}</button>` : ''}
      ${!shared && t.ws?.exists ? `<button type="button" class="hcd-icb" data-act="term" aria-pressed="${!!(PANE && PANE.term)}" aria-label="Terminal: commands running in the background" title="Terminal">${svg('term')}</button>` : ''}
      ${shared ? '' : `<button type="button" class="hcd-icb" data-menu="smenu" aria-label="More for this session" title="More">${svg('more')}</button>
      <button type="button" class="hcd-btn sm hcd-sharebtn${t.share?.on ? ' hcd-shon' : ''}" data-act="share" title="${t.share?.on ? 'Anyone with the link can read this session' : 'Share a read-only copy'}">${svg('share')}${t.share?.on ? 'Shared' : 'Share'}</button>`}`);
    tick();
    thread(t);
    loadPics(t);
    put('#hcdQueue', 'queue', (t.running ? (t.notes || []) : []).map((n, i) => `<div class="hcd-q"><span><b>Queued</b> ${esc(n)}</span><button type="button" class="hcd-icb" data-act="unq" data-i="${i}" aria-label="Take this message back" title="Take it back">${svg('x')}</button></div>`).join(''));
    put('#hcdBar', 'bar', barHTML(t));
    put('#hcdRail', 'rail', railHTML(t));
    drawPane(false);
    const canC = t.running || canRev(t);
    put('#hcdCc', 'cc', COMMENTS.length && canC ? `<div class="hcd-ccn"><span><b>${plural(COMMENTS.length, 'comment')}</b> will go with your next message</span><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-act="changes">View</button><button type="button" class="hcd-icb" data-act="cclear" aria-label="Remove the queued comments" title="Remove them">${svg('x')}</button></div>` : '');
    const mode = shared ? 'off' : t.running ? 'note' : t.question ? 'answer' : t.status === 'plan_wait' ? 'plan' : canRev(t) ? 'revise' : 'off', f = $('#hcdSteer'), ta = $('#hcdNote');
    const hint = mode === 'revise' && t.hint ? String(t.hint) : '';      // a suggested next message: shown as ghost text, Tab takes it
    const ph = hint || {note: 'Message Hoola - it reads it before its next step', plan: 'Add a note for Hoola - it starts on the plan with your note',
      revise: 'Ask for a change - Hoola adds a commit to the same pull request', answer: 'Type your answer - Hoola continues this session', off: ''}[mode];
    if (f.dataset.mode !== mode || ta.dataset.ph !== ph) { f.dataset.mode = mode; f.hidden = mode === 'off'; ta.placeholder = ph; ta.dataset.ph = ph; ta.dataset.hint = hint;
      ta.setAttribute('aria-description', hint ? 'Suggested message. Press Tab to use it.' : ''); }
    put('#hcdHintK', 'hintk', hint ? '<kbd>Tab</kbd>' : '');
    put('#hcdCpMeta', 'cpm', shared || mode === 'off' ? '' : metaHTML(t));
    put('#hcdCpB', 'cpb', t.running ? `<button type="button" class="hcd-stop" id="hcdStop" data-act="stop"${t.stopping ? ' disabled' : ''}>${svg('stop')}Stop</button>`
      : `<button type="submit" class="hcd-send" aria-label="Send" title="Send (Enter)">${svg('up')}</button>`);
    threadStay();
  }
  // v0.999 'Ask each step': the step waits here for her yes, like Claude Code's permission prompt
  function askHTML(a) {
    if (a.tool === 'question') return `<div class="hcd-ask2 col hcd-perm hcd-qask" id="hcdPerm" data-id="${esc(a.id)}"><span class="hcd-badge info">Hoola asks</span><p class="hcd-qtext"><b>${esc(a.what || '')}</b></p>
      ${(a.choices || []).length ? `<div class="hcd-acts">${a.choices.map(c => `<button type="button" class="hcd-btn" data-act="qans" data-v="${esc(c)}">${esc(c)}</button>`).join('')}</div>` : ''}
      <div class="hcd-qrow"><label class="hcd-sr" for="hcdQAns">Your answer</label><input id="hcdQAns" maxlength="2000" placeholder="Or type your answer" autocomplete="off"><button type="button" class="hcd-btn pri" data-act="qsend">Send</button></div></div>`;
    const always = a.tool === 'bash' ? (a.prefix ? `Yes, and don\u2019t ask again for <code>${esc(a.prefix)}</code> commands` : '')
      : a.tool === 'mcp' ? `Yes, and allow <code>${esc(a.server || '')}</code> for this session` : 'Yes, allow all edits in this session';
    const body = a.tool === 'bash' ? `<pre class="hcd-term hcd-askcmd"><span class="hcd-cmd">$ ${esc(a.cmd || '')}</span>${a.background ? '\n<span class="hcd-dim">keeps running in the background</span>' : ''}</pre>`
      : (a.rows || []).length ? hunkHTML(a.rows) : '';
    return `<div class="hcd-ask2 col hcd-perm" id="hcdPerm" data-id="${esc(a.id)}"><span class="hcd-badge info">Hoola wants to</span><p class="hcd-qtext"><b>${esc(a.what || '')}</b>${a.path && a.tool !== 'bash' ? ` <code>${esc(a.path)}</code>` : ''}</p>${body}
      <div class="hcd-acts"><button type="button" class="hcd-btn pri" data-act="permit" data-a="yes">Yes</button>${always ? `<button type="button" class="hcd-btn" data-act="permit" data-a="always">${always}</button>` : ''}<button type="button" class="hcd-btn" data-act="permitno">No, tell Hoola what to do</button></div></div>`;
  }
  function barHTML(t) {
    if (shared) return `<div class="hcd-ask2 soft"><span><b>Read-only.</b> Someone shared this coding session with you from Hoola Code. You can read it; nothing here can change anything.${t.until ? ' The link works until ' + esc(new Date(t.until).toLocaleDateString(undefined, {day: 'numeric', month: 'short'})) + '.' : ''}</span></div>`;
    if (t.ask) return askHTML(t.ask);
    if (t.running) return '';
    if (t.question) { const ch = (t.ws || {}).choices || [];          // Hoola may offer 2-4 answers to tap; her own words still work
      return `<div class="hcd-ask2 col hcd-qcard" id="hcdQ"><span class="hcd-badge info">Hoola asks</span><p class="hcd-qtext">${esc(t.question)}</p>
        <div class="hcd-acts" id="hcdChoices">${ch.map((c, i) => `<button type="button" class="hcd-btn" data-act="choice" data-i="${i}">${esc(c)}</button>`).join('')}<button type="button" class="hcd-btn ghost" data-act="ownanswer">Type my own answer</button></div></div>`; }
    if (t.status === 'plan_wait') return '';
    if (MERGE) { const a = MERGE; return `<div class="hcd-ask2 col"><span class="hcd-badge bad">Needs your OK</span><div class="hcd-ask2r"><b>${esc(a.method)} merge PR #${a.pr_number} into ${esc(a.base)}?</b><span class="hcd-mut">commit <code>${esc(a.head_sha)}</code> · CI ${esc((CI[a.ci_state] || ['', a.ci_state])[1])}</span><span class="hcd-flex"></span>
        <button type="button" class="hcd-btn" data-act="mergeno">Not now</button><button type="button" class="hcd-btn ok" data-act="mergeyes">Merge</button></div>
        ${(a.notes || []).map(n => `<p class="hcd-mut">${esc(n)}</p>`).join('')}
        ${a.needs_force ? '<label class="hcd-f"><span>CI is not green - write why you still want to merge (8+ characters)</span><input id="hcdForce" maxlength="300"></label>' : ''}
        <p class="hcd-mut">If anything is pushed after this card, it goes stale and asks again.</p></div>`; }
    if (t.status === 'ready' && t.hash) return `<div class="hcd-ask2 col"><span class="hcd-badge bad">Needs your OK</span><p>The change is ready. Open a pull request on <b>${esc(t.repo)}</b>?${(OV?.repos || []).find(r => r.repo === t.repo && !r.private) ? ' It is a public repository, so Hoola always asks first.' : ''}</p><div class="hcd-acts"><button type="button" class="hcd-btn pri" id="hcdPush" data-act="push">Open the pull request</button></div></div>`;
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
    const sc = /^\/([a-z][\w-]*)(?:\s+([\s\S]*))?$/.exec(v);      // v0.999 Claude Code's built-in commands, typed
    if (sc && BUILTIN[sc[1]]) {
      const w = BUILTIN[sc[1]], arg = (sc[2] || '').trim();
      if (w.args || !arg) {
        if (text === undefined) { ta.value = ''; grow(ta); }
        return w.send ? sendMessage(w.send + (arg ? '\n' + arg : '')) : w.run(arg);
      }
    }
    const typed = text === undefined, mine = v && (mode === 'revise' || mode === 'answer') ? herNow(v) : null;      // her words show the moment she sends
    if (typed && mine) { ta.value = ''; grow(ta); }
    try {
      if (mode === 'note') { await api('POST', `/api/devsahayak/tasks/${tid()}/note`, {text: v, comments: cs}); }
      else if (mode === 'answer') { await api('POST', `/api/devsahayak/tasks/${tid()}/answer`, {text: v}); }
      else if (mode === 'plan') { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/plan_ok`, {hash: t.hash, note: v}); }
      else { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/revise`, {text: v, comments: cs}); }
      if (cs.length) { COMMENTS = []; DRAFT = null; SIG.pane = ''; }
      if (typed && !mine) { ta.value = ''; grow(ta); }
      await again();
    } catch (e) { herBack(mine); if (typed && mine && !ta.value) { ta.value = v; grow(ta); } toast(e.message, true); }
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
  function termHTML() {            // v0.999 the Terminal pane: commands Hoola keeps running in the background
    const sh = PANE.shells;
    const rows = sh == null ? '<p class="hcd-mut">Loading…</p>' : !sh.length ? '<p class="hcd-mut">No background commands. When Hoola starts a dev server or a watcher, it shows here with its output.</p>'
      : sh.map(x => `<section class="hcd-shell"><div class="hcd-shellh"><b>${esc(x.desc || x.id)}</b><span class="hcd-pill ${x.state === 'running' ? 'run' : x.rc ? 'bad' : ''}">${x.state === 'running' ? 'Running' : x.state === 'killed' ? 'Stopped' : 'Exited ' + esc(String(x.rc ?? ''))}</span><span class="hcd-flex"></span>${x.state === 'running' && !shared ? `<button type="button" class="hcd-btn sm" data-act="termstop" data-id="${esc(x.id)}">Stop</button>` : ''}</div>
        <pre class="hcd-term hcd-shellout"><span class="hcd-cmd">$ ${esc(x.cmd || '')}</span>${(x.lines || []).length ? '\n' + x.lines.map(l => esc(l)).join('\n') : ''}</pre></section>`).join('');
    return `<div class="hcd-ph"><h2>Terminal</h2><span class="hcd-flex"></span><button type="button" class="hcd-icb" data-act="pclose" aria-label="Close the terminal" title="Close">${svg('x')}</button></div><div class="hcd-termwrap">${rows}</div>`;
  }
  async function openTerm() {
    if (!TASK) return; PANE = {term: true, shells: null, path: ''}; SIG.top = ''; paint(); await termLoad();
  }
  async function termLoad() {
    if (!PANE || !PANE.term || !TASK) return;
    try { const r = await api('GET', `/api/devsahayak/tasks/${tid()}/terminal`); if (PANE && PANE.term) { PANE.shells = r.shells || []; drawPane(true); } } catch (e) { toast(e.message, true); }
  }
  async function answerQ(v) {
    const a = TASK?.ask; if (!a) return;
    await api('POST', `/api/devsahayak/tasks/${tid()}/permit`, {id: a.id, answer: 'answer', note: v}); TASK.ask = null; SIG.top = ''; paint();
  }
  async function repoSetup() {      // v0.999 what Hoola reads from this repo's .claude/
    let r; try { r = await api('GET', `/api/devsahayak/tasks/${tid()}/commands`); } catch (e) { return toast(e.message, true); }
    const rows = (h, xs) => xs.length ? `<h3>${h}</h3>${xs.join('')}` : '';
    const rl = r.rules || {}, any = (r.commands || []).length || (r.agents || []).length || (r.hooks || []).length || rl.allow || rl.ask || rl.deny
      || (r.skills || []).length || (r.mcp || []).length || (r.env || []).length || r.mode;
    await dialog(`<h2>This repo\u2019s Claude Code setup</h2><p class="hcd-mut">Hoola follows <code>.claude/</code> in this repo, like Claude Code: its commands, agents, hooks and permission rules. Hooks run in the locked box, never on Hoola\u2019s server.</p>
      ${any ? rows('Commands', (r.commands || []).map(c => `<div class="hcd-row"><span><code>/${esc(c.name)}</code></span><b>${esc(c.description || '')}</b></div>`))
        + rows('Agents', (r.agents || []).map(a => `<div class="hcd-row"><span><code>${esc(a.name)}</code></span><b>${esc(a.description || '')} · ${esc(a.tools)}${a.model && a.model !== 'inherit' ? ' · model ' + esc(a.model) : ''}</b></div>`))
        + rows('Skills', (r.skills || []).map(k => `<div class="hcd-row"><span><code>${esc(k.name)}</code></span><b>${esc(k.description || '')}</b></div>`))
        + rows('MCP servers', (r.mcp || []).map(m => `<div class="hcd-row"><span><code>${esc(m.name)}</code></span><b>${m.ok ? (m.kind === 'stdio' ? 'Runs in the locked box' + (m.program ? ' · <code>' + esc(m.program) + '</code>' : '') : 'Online') + ' · asks you before its first use' : esc(m.why || 'Not reachable')}</b></div>`))
        + rows('Hooks', (r.hooks || []).map(h => `<div class="hcd-row"><span>${esc(h)}</span></div>`))
        + (r.mode ? `<h3>Starting mode</h3><p>${esc((MODES.find(m => m[0] === r.mode) || [0, r.mode])[1])} <span class="hcd-mut">from settings.json defaultMode</span></p>` : '')
        + ((r.env || []).length ? `<h3>Variables from settings.json</h3><p><code>${(r.env || []).map(esc).join('</code> <code>')}</code></p>` : '')
        + (rl.allow || rl.ask || rl.deny ? `<h3>Permission rules</h3><p>${rl.allow || 0} allowed · ${rl.ask || 0} ask first · ${rl.deny || 0} denied</p>` : '')
        : '<p>This repo has no <code>.claude/</code> setup yet. Add commands in <code>.claude/commands</code>, agents in <code>.claude/agents</code>, rules and hooks in <code>.claude/settings.json</code>.</p>'}
      ${(r.plugins || []).filter(p => p.enabled).length ? `<h3>Your plugins</h3><p>${(r.plugins || []).filter(p => p.enabled).map(p => esc(p.name)).join(' · ')}</p>` : ''}
      <div class="hcd-dlgb"><button class="hcd-btn" value="plug" formnovalidate>Plugins…</button><button class="hcd-btn" value="edit" formnovalidate>Edit the files…</button><span class="hcd-flex"></span><button class="hcd-btn" value="no">Close</button></div>`)
      .then(v => v === 'edit' ? claudeFiles() : v === 'plug' ? pluginsDlg() : null);
  }
  // v0.999 the dialogs behind the typed commands
  async function helpDlg() {
    if (!REPOCMD || REPOCMD.tid !== TASK.id) { try { REPOCMD = {tid: TASK.id, ...(await api('GET', `/api/devsahayak/tasks/${tid()}/commands`))}; } catch (e) { REPOCMD = {tid: TASK.id, commands: []}; } }
    const row = (n, d) => `<div class="hcd-row"><span><code>/${esc(n)}</code></span><b>${esc(d)}</b></div>`;
    await dialog(`<h2>Commands</h2><p class="hcd-mut">Type them in the box, like in Claude Code.</p>
      <div class="hcd-cmdlist">${HOOLA_CMDS.map(([n, d]) => row(n, d)).join('')}</div>
      ${(REPOCMD.commands || []).length ? `<h3>This repo\u2019s commands</h3><div class="hcd-cmdlist">${REPOCMD.commands.map(c => row(c.name, (c.description || '') + (c.hint ? ' · ' + c.hint : ''))).join('')}</div>` : ''}
      <p class="hcd-mut">Terminal-only commands of Claude Code (${TERMINAL_ONLY.map(n => '/' + n).join(', ')}) are not needed here.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button></div>`);
  }
  function clearNow() {
    const r = TASK && TASK.repo; if (r && (OV?.repos || []).some(x => x.repo === r)) REPO = r;
    show('home'); toast('A fresh start: a new session on ' + (r || 'this repo') + '. The last one stays in the list.');
  }
  function modelNow() {
    const b = $('.hcd-tierbtn') || $('#hcdNote');
    if (TIERS && TIERS.available) return tierMenu(b);
    toast('Hoola Code picks the model for you: ' + (TIER_NAME[(TIERS && TIERS.selected) || ''] || 'Normal') + ' quality.');
  }
  async function costDlg() {
    const t = TASK, c = t.cost || {}, us = OV?.usage || {};
    await dialog(`<h2>Cost</h2><div class="hcd-row"><span>This session</span><b>${c.calls ? rs(c.inr) + ' · ' + plural(c.calls, 'model call') : 'Nothing yet'}</b></div>
      <div class="hcd-row"><span>This month, all of Hoola</span><b>${us.spent_inr > 0 ? rs(us.spent_inr) : 'Nothing yet'}${us.limit_inr > 0 ? ' of ' + rs(us.limit_inr) : ''}</b></div>
      <p class="hcd-mut">The session figure is the list price of its model calls - an estimate, not a bill.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button></div>`);
  }
  async function statusDlg(doctor) {
    const t = TASK, row = (k, v) => v ? `<div class="hcd-row"><span>${k}</span><b>${v}</b></div>` : '';
    let probs = [];
    if (doctor) {
      const st = OV?.settings || {};
      if (!st.github) probs.push('GitHub is not connected - Settings > GitHub access.');
      if (!(OV?.repos || []).some(x => x.repo === t.repo)) probs.push(`${t.repo} is not in your list of repositories.`);
      try { const r = await api('GET', `/api/devsahayak/tasks/${tid()}/commands`);
        (r.mcp || []).filter(m => !m.ok).forEach(m => probs.push(`MCP server ${m.name} cannot be used: ${m.why}`)); } catch (e) { probs.push('Could not read this repo\u2019s Claude Code setup: ' + e.message); }
      if (t.ctx >= 80) probs.push(`The conversation is ${t.ctx}% full - /compact makes room.`);
    }
    await dialog(`<h2>${doctor ? 'Doctor' : 'Status'}</h2>
      ${row('Repo', esc(t.repo || ''))}${row('Branch', t.branch ? '<code>' + esc(t.branch) + '</code>' : '')}${row('Works from', esc(t.base || ''))}
      ${row('Mode', esc((MODES.find(m => m[0] === (t.mode || '')) || [0, 'Default'])[1]))}${row('Environment', esc((t.env || {}).name || 'Auto'))}
      ${row('Quality', esc(TIER_NAME[(TIERS && TIERS.selected) || ''] || 'Normal'))}${row('Pull request', t.pr_number ? '#' + t.pr_number + ' · ' + esc(STATUS[t.status] || t.status) : 'Not yet')}
      ${row('Context', t.ctx >= 0 ? t.ctx + '% used' : '')}${row('Checkpoints', String(((t.ws || {}).checkpoints || []).length))}
      ${doctor ? (probs.length ? `<h3>Found</h3>${probs.map(p => `<p>${esc(p)}</p>`).join('')}` : '<h3>Found</h3><p>Nothing wrong.</p>') : ''}
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button></div>`);
  }
  async function todosDlg() {
    const td = [...(TASK.steps || [])].reverse().find(s => s.k === 'todo'), items = (td && td.items) || [];
    await dialog(`<h2>To-dos</h2>${items.length ? items.map(x => `<div class="hcd-row"><span>${x.status === 'completed' ? '\u2713' : x.status === 'in_progress' ? '\u25cf' : '\u25cb'}</span><b>${esc(x.content || x.text || '')}</b></div>`).join('')
      : '<p class="hcd-mut">Hoola has not made a to-do list in this session.</p>'}<div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button></div>`);
  }
  async function rewindPick() {
    const cps = ((TASK.ws || {}).checkpoints || []).slice().reverse();
    if (!cps.length) return toast('No checkpoint yet - one is saved after every round.');
    if (TASK.running) return toast('Hoola is working - stop it first, then go back.');
    const v = await dialog(`<h2>Rewind</h2><p class="hcd-mut">Pick the checkpoint to go back to.</p>
      <div class="hcd-cflist">${cps.map(c => `<button class="hcd-row hcd-cfrow" value="${c.n}"><span>Checkpoint ${c.n}</span><b>${esc((c.label || '').slice(0, 60))}</b></button>`).join('')}</div>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Never mind</button></div>`);
    if (+v > 0) ACTS.rewind({dataset: {n: v}});
  }
  async function prComments() {
    if (!TASK.pr_number) return toast('There is no pull request in this session yet.');
    ACTS.readcomments({});
  }
  async function settingsFile() {
    let have = false; try { await api('GET', `/api/devsahayak/tasks/${tid()}/claude-file?path=.claude/settings.json`); have = true; } catch (e) { have = false; }
    claudeEdit('.claude/settings.json', have ? undefined : CF_NEW.find(n => n[0] === '.claude/settings.json')[2]);
  }
  async function memoryFile() {
    let have = false; try { await api('GET', `/api/devsahayak/tasks/${tid()}/claude-file?path=CLAUDE.md`); have = true; } catch (e) { have = false; }
    claudeEdit('CLAUDE.md', have ? undefined : CF_NEW.find(n => n[0] === 'CLAUDE.md')[2]);
  }
  async function compactNow(focus) {
    try { await api('POST', `/api/devsahayak/tasks/${tid()}/compact`, {focus: focus || ''}); toast(focus ? 'Summarised, keeping: ' + focus : 'The conversation is summarised - your words are kept.'); await again(); } catch (e) { toast(e.message, true); }
  }
  // v0.999 /export: the conversation as a Markdown file on her computer
  async function exportNow() {
    try { const r = await api('GET', `/api/devsahayak/tasks/${tid()}/export`, undefined, {raw: true}), b = await r.blob();
      const m = /filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') || ''), a = document.createElement('a'), u = URL.createObjectURL(b);
      a.href = u; a.download = m ? m[1] : 'hoola-code-session.md'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 4000);
      toast('Downloaded ' + a.download); } catch (e) { toast(e.message, true); }
  }
  // v0.999 output styles (Claude Code's /output-style): default, explanatory, learning, or the repo's own
  async function styleMenu(btn) {
    if (!window.HoolaMenu) return;
    let r; try { r = await api('GET', `/api/devsahayak/tasks/${tid()}/commands`); } catch (e) { return toast(e.message, true); }
    HoolaMenu.open(btn, [{header: 'Output style'}, ...(r.styles || []).map(x => ({label: STYLE_NAME[x.name] || x.name, sub: (x.description || '') + (x.origin && x.origin !== 'hoola' ? ' · ' + x.origin : ''),
      checked: (r.style || 'default') === x.name, run: () => setStyle(x.name)}))], {align: 'start', label: 'Output style', width: 300});
  }
  async function setStyle(name) {
    try { await api('PUT', `/api/devsahayak/tasks/${tid()}/style`, {style: name}); if (TASK) TASK.style = name; toast('Output style: ' + (STYLE_NAME[name] || name) + ' - from the next message.'); } catch (e) { toast(e.message, true); }
  }
  // v0.999 the repo's Claude Code files, changed from the screen (Claude Code's /agents, /hooks, /permissions, /memory)
  const CF_NEW = [['.claude/agents/NAME.md', 'An agent', '---\nname: NAME\ndescription: When Hoola should hand work to this agent\ntools: Read, Grep, Bash\n---\nYou are ...\n'],
    ['.claude/commands/NAME.md', 'A slash command', '---\ndescription: What /NAME does\nargument-hint: <what to give it>\n---\nDo this with $ARGUMENTS ...\n'],
    ['.claude/skills/NAME/SKILL.md', 'A skill', '---\nname: NAME\ndescription: When this skill is the right one\n---\nSteps ...\n'],
    ['.claude/output-styles/NAME.md', 'An output style', '---\ndescription: How replies should look\n---\nAnswer ...\n'],
    ['.claude/settings.json', 'Rules and hooks (settings.json)', '{\n  "permissions": {"allow": [], "ask": [], "deny": []},\n  "hooks": {}\n}\n'],
    ['.mcp.json', 'MCP servers (.mcp.json)', '{\n  "mcpServers": {}\n}\n'], ['CLAUDE.md', 'CLAUDE.md (rules for the repo)', '# Rules\n\n']];
  async function claudeFiles(only) {
    let r; try { r = await api('GET', `/api/devsahayak/tasks/${tid()}/commands`); } catch (e) { return toast(e.message, true); }
    const have = (r.files || []).filter(f => !only || f.startsWith(only));
    const v = await dialog(`<h2>Claude Code files in this repo</h2><p class="hcd-mut">Change them here like Claude Code\u2019s /agents, /hooks and /permissions. A change is made in this session\u2019s copy of the repo, so it goes into its pull request. Never put a key or a password in them.</p>
      ${have.length ? `<div class="hcd-cflist">${have.map(f => `<button class="hcd-row hcd-cfrow" value="open:${esc(f)}"><code>${esc(f)}</code><span class="hcd-flex"></span>${svg('pencil')}</button>`).join('')}</div>` : '<p>This repo has none of them yet.</p>'}
      <h3>Add</h3><div class="hcd-acts">${CF_NEW.filter(n => (!only || n[0].startsWith(only)) && (n[0].includes('NAME') || !have.includes(n[0]))).map(n => `<button class="hcd-btn sm" value="new:${CF_NEW.indexOf(n)}">${esc(n[1])}</button>`).join('')}</div>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button></div>`);
    if (!v || v === 'no') return;
    if (v.startsWith('open:')) return claudeEdit(v.slice(5));
    const n = CF_NEW[+v.slice(4)];
    if (!n[0].includes('NAME')) return claudeEdit(n[0], n[2]);
    const nm = await dialog(`<h2>${esc(n[1])}</h2><label class="hcd-f"><span>Name <small>letters, numbers and dashes</small></span><input id="hcdCfName" maxlength="60" pattern="[A-Za-z0-9._-]+" required autocomplete="off"></label>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Next</button></div>`).then(x => x === 'ok' ? (CF_LAST || '') : '');
    if (nm) claudeEdit(n[0].replace('NAME', nm), n[2].split('NAME').join(nm));
  }
  let CF_LAST = '';
  document.addEventListener('input', e => { if (e.target && e.target.id === 'hcdCfName') CF_LAST = e.target.value.trim(); });
  async function claudeEdit(path, fresh) {
    let text = fresh || '';
    if (!fresh) { try { text = (await api('GET', `/api/devsahayak/tasks/${tid()}/claude-file?path=${encodeURIComponent(path)}`)).text || ''; } catch (e) { return toast(e.message, true); } }
    let body = text;
    const d = $('#hcdDlg');
    const v = await new Promise(res => { dialog(`<h2><code>${esc(path)}</code></h2>
      <label class="hcd-sr" for="hcdCfText">The file</label><textarea id="hcdCfText" class="hcd-cfed" rows="16" spellcheck="false">${esc(text)}</textarea>
      <p class="hcd-mut">${/\.json$/.test(path) ? 'It must be valid JSON. ' : ''}Save with an empty file to delete it.</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Save</button></div>`).then(res);
      setTimeout(() => { const ta = d.querySelector('#hcdCfText'); if (ta) { ta.focus(); ta.addEventListener('input', () => { body = ta.value; }); } }, 0); });
    if (v !== 'ok') return;
    try { const out = await api('PUT', `/api/devsahayak/tasks/${tid()}/claude-file`, {path, text: body}); REPOCMD = null;
      toast(out.what === 'deleted' ? 'Deleted ' + path : 'Saved ' + path + ' - it rides in this session\u2019s pull request.'); await again(); }
    catch (e) { toast(e.message, true); claudeEdit(path, body || ' '); }
  }
  // v0.999 plugins (Claude Code's /plugin): commands, agents, skills and hooks from a GitHub repo or marketplace
  async function pluginsDlg() {
    let r; try { r = await api('GET', '/api/devsahayak/plugins'); } catch (e) { return toast(e.message, true); }
    const has = h => Object.entries(h || {}).filter(([, n]) => n).map(([k, n]) => `${n} ${k}`).join(' · ');
    const v = await dialog(`<h2>Plugins</h2><p class="hcd-mut">A plugin brings commands, agents, skills, hooks and MCP servers to every session of yours, like Claude Code\u2019s /plugin. Add one or a whole marketplace by its public GitHub link. Its hooks run in the locked box, never on Hoola\u2019s server.</p>
      ${(r.plugins || []).length ? (r.plugins || []).map(p => `<div class="hcd-repo hcd-plug"><div><b>${esc(p.name)}</b>${p.version ? ` <span class="hcd-mut">${esc(p.version)}</span>` : ''}<p class="hcd-mut">${esc(p.description || p.url)}${has(p.has) ? ' · ' + esc(has(p.has)) : ''}</p></div><span class="hcd-flex"></span>
        <button class="hcd-btn sm" value="${p.enabled ? 'off' : 'on'}:${esc(p.name)}">${p.enabled ? 'Turn off' : 'Turn on'}</button><button class="hcd-btn sm danger" value="rm:${esc(p.name)}">Remove</button></div>`).join('') : '<p>No plugins yet.</p>'}
      <label class="hcd-f"><span>Add from GitHub</span><input id="hcdPlugUrl" placeholder="https://github.com/owner/repo" maxlength="200" autocomplete="off"></label>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Close</button><button class="hcd-btn pri" value="add">Add</button></div>`);
    if (!v || v === 'no') return;
    try {
      if (v === 'add') { if (!PLUG_URL) return toast('Paste the plugin\u2019s GitHub link.', true); toast('Downloading the plugin…'); await api('POST', '/api/devsahayak/plugins', {url: PLUG_URL}); PLUG_URL = ''; toast('Added. It joins your sessions from the next message.'); }
      else { const [op, ...nm] = v.split(':'), name = nm.join(':');
        if (op === 'rm') await api('DELETE', `/api/devsahayak/plugins/${encodeURIComponent(name)}`);
        else await api('PATCH', `/api/devsahayak/plugins/${encodeURIComponent(name)}`, {enabled: op === 'on'}); }
      REPOCMD = null;
    } catch (e) { toast(e.message, true); }
    pluginsDlg();
  }
  let PLUG_URL = '';
  document.addEventListener('input', e => { if (e.target && e.target.id === 'hcdPlugUrl') PLUG_URL = e.target.value.trim(); });
  async function initNow() {
    try { await api('POST', `/api/devsahayak/tasks/${tid()}/init`); toast('Hoola is writing AGENTS.md for this repo.'); await again(); } catch (e) { toast(e.message, true); }
  }
  async function forkNow(n) {
    try { const f = await api('POST', `/api/devsahayak/tasks/${tid()}/fork`, {checkpoint: n || 0}); await load(); toast('Forked. This is the copy - the original is unchanged.'); show('session', f.id); } catch (e) { toast(e.message, true); }
  }
  function paneHTML(t) {
    if (PANE && PANE.term) return termHTML();
    const files = paneFiles(t), f = files.find(x => x.path === PANE.path) || files[0], canC = t.running || canRev(t), pushed = !shared && !!(t.pr_number && t.branch);
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
      if (!shared && P.side === 'open' && $('#hcdBody').clientWidth < 1100) { SIDE_AUTO = true; P.side = 'min'; drawSide(); }    // make room; it comes back on close
      const t = TASK; if (!shared && t.pr_number && !BRANCHES[t.repo]) api('GET', `/api/devsahayak/branches?repo=${encodeURIComponent(t.repo)}`).then(r => { BRANCHES[t.repo] = r.branches || []; drawPane(false); }).catch(() => { BRANCHES[t.repo] = []; }); }
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
    find: () => { if (P.side === 'min') { P.side = 'open'; keep(); } P.find = true; drawSide(); const s = $('#hcdSearch'); if (s) { s.hidden = false; s.focus(); } },
    envs: () => { P.stab = 'envs'; show('settings'); },
    plugins: () => pluginsDlg(),
    rail: () => { P.rail = railShown() ? 'off' : ($('#hcdBody').clientWidth < 780 ? 'on' : 'auto'); keep(); $('.hcd').dataset.rail = P.rail; SIG.top = ''; paint(); },   // 'on' = an overlay she opened on a narrow window
    rename: () => askName(TASK),
    share: () => shareDialog(TASK),
    fixcomments: b => busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/bg/fix_comments`); await again(); }),
    readcomments: b => busy(b, async () => { const r = await api('GET', `/api/devsahayak/tasks/${tid()}/comments`); toast(r.open.length ? `${plural(r.open.length, 'new comment')} from reviewers.` : 'No new comments from reviewers.'); await refreshTask(TASK.id, false); }),
    schedrun: b => busy(b, async () => { const t = await api('POST', `/api/devsahayak/schedules/${encodeURIComponent(b.dataset.id)}/run`); await load(); show('session', t.id); }),
    schedtoggle: b => busy(b, async () => { await api('PATCH', `/api/devsahayak/schedules/${encodeURIComponent(b.dataset.id)}`, {enabled: b.dataset.on !== '1'}); await load(); drawSide(); scheduled(); }),
    scheddel: async b => { const sc = (OV?.schedules || []).find(x => x.id === b.dataset.id); if (!sc) return;
      const r = await dialog(`<h2>Delete "${esc(sc.title)}"?</h2><p class="hcd-mut">It will not run again and its trigger address stops working. The sessions it already made stay in your list.</p>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no">Cancel</button><button class="hcd-btn danger" value="ok">Delete</button></div>`);
      if (r !== 'ok') return; await busy(b, async () => { await api('DELETE', `/api/devsahayak/schedules/${encodeURIComponent(sc.id)}`); await load(); show('scheduled', ''); }); },
    schednew: () => schedForm(),
    schedopen: b => show('scheduled', b.dataset.id),
    schedtab: b => { P.stabS = b.dataset.tab; scheduled(); },
    sjump: b => { const s = $('#' + b.dataset.to); if (s) s.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      EL.querySelectorAll('.hcd-snavb').forEach(x => x.classList.toggle('on', x.dataset.to === b.dataset.to)); },
    envnew: () => envDialog(null),
    envedit: b => envDialog((ENVS.envs || []).find(e => e.id === b.dataset.id)),
    dlgclose: () => { const d = $('#hcdDlg'); if (d.open) d.close(); },
    schedtrig: b => triggerDialog((OV?.schedules || []).find(x => x.id === b.dataset.id)),
    copy: async b => { try { await navigator.clipboard.writeText(b.dataset.text || ''); toast('Copied.'); } catch (e) { toast('Select the text and copy it.', true); } },
    ownanswer: () => { const ta = $('#hcdNote'); if (ta) ta.focus(); },
    choice: b => busy(b, async () => { const c = ((TASK.ws || {}).choices || [])[+b.dataset.i]; if (c) await sendMessage(c); }),
    files: b => browse(b.dataset.path || ''),
    term: () => { PANE && PANE.term ? closePane() : openTerm(); },
    pick: b => pickTake(+b.dataset.i),
    qans: b => busy(b, () => answerQ(b.dataset.v)),
    qsend: b => { const v = ($('#hcdQAns') || {}).value || ''; if (v.trim()) busy(b, () => answerQ(v.trim())); },
    ctxinfo: async () => { const t = TASK; if (!t) return;
      const r = await dialog(`<h2>Context ${t.ctx}% used</h2><p class="hcd-mut">This is how full the conversation is. At 100% Hoola summarises the older part by itself and keeps your own words whole. <b>Compact now</b> does it at once, so the next message starts light.</p>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Close</button><button class="hcd-btn pri" value="ok"${t.running ? ' disabled' : ''}>Compact now</button></div>`);
      if (r === 'ok') compactNow(); },
    repoconf: () => repoSetup(),
    permit: b => busy(b, async () => { const a = TASK?.ask; if (!a) return; await api('POST', `/api/devsahayak/tasks/${tid()}/permit`, {id: a.id, answer: b.dataset.a}); TASK.ask = null; SIG.top = ''; paint(); }),
    permitno: async b => { const a = TASK?.ask; if (!a) return;
      const r = await dialog(`<h2>Not this step</h2><p class="hcd-mut">${esc(a.what || '')} will not run. Tell Hoola what to do instead (you can leave it empty).</p><label class="hcd-f"><span class="hcd-sr">What to do instead</span><textarea name="note" rows="3" maxlength="2000" placeholder="e.g. run only the cart tests"></textarea></label>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Send</button></div>`);
      if (r !== 'ok') return; const note = ($('#hcdDlg textarea[name=note]') || {}).value || '';
      await busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/permit`, {id: a.id, answer: 'no', note}); TASK.ask = null; SIG.top = ''; paint(); }); },
    termstop: b => busy(b, async () => { const r = await api('POST', `/api/devsahayak/tasks/${tid()}/terminal/${encodeURIComponent(b.dataset.id)}/stop`); if (PANE && PANE.term) { PANE.shells = r.shells || []; drawPane(true); } }),
    forkcp: b => forkNow(+b.dataset.n),
    editmsg: async b => { const t = TASK; if (!t) return; if (t.running) return toast('Hoola is working - stop it first, then edit.', true);
      const n = +b.dataset.n, old = (b.closest('.hck-me')?.querySelector('.hck-bub')?.textContent) || '';
      const r = await dialog(`<h2>Edit your message</h2><p class="hcd-mut">${n < 0 ? 'Your first message: Hoola starts again in a new session with these words. This session stays as it is.' : 'Hoola goes back to just before this message (files and conversation) and works from your new words. Work after it is dropped here.'}</p>
        <label class="hcd-f"><span class="hcd-sr">Your message</span><textarea name="msg" rows="5" maxlength="8000" required>${esc(old)}</textarea></label>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Cancel</button><button class="hcd-btn pri" value="ok">Send</button></div>`);
      if (r !== 'ok') return; const text = (($('#hcdDlg textarea[name=msg]') || {}).value || '').trim(); if (!text) return;
      try { const out = await api('POST', `/api/devsahayak/tasks/${tid()}/edit`, {step: n, text});
        if (n < 0 && out && out.id && out.id !== t.id) { await load(); show('session', out.id); } else await again(); } catch (e) { toast(e.message, true); } },
    rewind: async b => { const n = +b.dataset.n;
      const r = await dialog(`<h2>Go back to checkpoint ${n}</h2><p class="hcd-mut">What should go back? Your pull request on GitHub is not changed until the next push.</p>
        <div class="hcd-rwopts">
          <button class="hcd-rwopt" value="both"><b>Code and conversation</b><span>The files and the conversation return to how they were then.</span></button>
          <button class="hcd-rwopt" value="conversation"><b>Conversation only</b><span>The conversation goes back; the files keep every change made since.</span></button>
          <button class="hcd-rwopt" value="code"><b>Code only</b><span>The files go back; the conversation stays as it is.</span></button></div>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Never mind</button></div>`);
      if (!['both', 'code', 'conversation'].includes(r)) return;
      await busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/rewind`, {n, what: r}); await again();
        toast(r === 'code' ? `Files back at checkpoint ${n}. The conversation is unchanged.` : r === 'conversation' ? `Conversation back at checkpoint ${n}. The files keep their changes.` : `Back at checkpoint ${n}.`); }); },
    wtshow: async b => { const w = b.dataset.wt;   /* v0.999 an agent's own copy: its diff */
      try { const r = await api('GET', `/api/devsahayak/tasks/${tid()}/worktrees/${encodeURIComponent(w)}`);
        await dialog(`<h2>Changes in the agent's own copy ${esc(w)}</h2><p class="hcd-mut">Not in your working copy yet.</p>${diffHTML(String(r.diff || '').split('\n').slice(0, 3000)) || '<p>No changes.</p>'}
          <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Close</button></div>`); } catch (e) { toast(e.message, true); } },
    wtapply: async b => { const w = b.dataset.wt;
      await busy(b, async () => { const r = await api('POST', `/api/devsahayak/tasks/${tid()}/worktrees/${encodeURIComponent(w)}/apply`); await again();
        toast(r.conflicts && r.conflicts.length ? `Brought in ${w} - settle the conflicts in ${r.conflicts.join(', ')}.` : `Brought ${w}'s changes into the working copy.`, !!(r.conflicts && r.conflicts.length)); }); },
    wtdiscard: async b => { const w = b.dataset.wt;
      const ok = await dialog(`<h2>Discard ${esc(w)}?</h2><p class="hcd-mut">The agent's changes in its own copy are thrown away. Your working copy is not touched.</p>
        <div class="hcd-dlgb"><button class="hcd-btn" value="no" formnovalidate>Keep them</button><button class="hcd-btn pri" value="yes">Discard</button></div>`);
      if (ok !== 'yes') return;
      await busy(b, async () => { await api('POST', `/api/devsahayak/tasks/${tid()}/worktrees/${encodeURIComponent(w)}/discard`); await again(); toast(`Discarded ${w}.`); }); },
    starter: b => { const l = $('#hcdLine'), st = STARTS[+b.dataset.i]; if (!l || !st) return; l.value = st[2]; l.focus(); l.setSelectionRange(l.value.length, l.value.length); },
    unkind: () => { HOME.kind = 'auto'; drawTray(); },
    unissue: () => { HOME.issue = 0; drawTray(); },
    unfile: b => { const f = HOME.files.splice(+b.dataset.i, 1)[0]; if (f?.url) URL.revokeObjectURL(f.url); drawTray(); },
    unref: b => { HOME.refs = HOME.refs.filter(r => r !== b.dataset.repo); HOME.also = HOME.also.filter(r => r !== b.dataset.repo); drawTray(); },
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
    alltab: b => { const was = ALL.tab === 'archived', now = b.dataset.tab === 'archived'; ALL.tab = b.dataset.tab; if (was !== now) ALL.rows = null; allSessions(); },
    unarch: b => setArchived(findTask(b.dataset.id), false),
    arch: b => setArchived(findTask(b.dataset.id), true),
    del: b => askDelete(findTask(b.dataset.id)),
  };

  // ------------------------------------------------------------------ all sessions ---
  async function allSessions() {
    const arch = ALL.tab === 'archived';
    const rowA = t => `<div class="hcd-arow"><i class="hcd-dot ${dotc(t)}"></i><button type="button" class="hcd-sessb" data-tid="${esc(t.id)}"><span class="hcd-st"><span>${esc(t.title || t.number)}</span></span>
          <small>${esc((t.repo || '').split('/')[1] || t.repo || '')}${t.env?.name ? ' · ' + esc(t.env.name) : ''} · ${t.question ? 'asks: "' + esc(String(t.question).slice(0, 60)) + '"' : esc(sub(t))}${t.pr_number ? ' · PR #' + t.pr_number : ''}</small></button>
          <span class="hcd-stat">${stat(t)}</span><span class="hcd-when">${esc(ago(t.updated || t.at).replace(' ago', ''))}</span>
          ${arch ? `<button type="button" class="hcd-btn sm" data-act="unarch" data-id="${esc(t.id)}">Unarchive</button>` : ''}
          <button type="button" class="hcd-icb" data-menu="row" data-id="${esc(t.id)}" aria-label="More for ${esc(t.title || t.number)}">${svg('more')}</button></div>`;
    const draw = () => {
      const rows = ALL.rows || [], f = ALL.repo ? rows.filter(t => t.repo === ALL.repo) : rows, by = g => f.filter(t => group(t) === g);
      const tab = (k, name, n) => `<button type="button" role="tab" aria-selected="${ALL.tab === k}" data-act="alltab" data-tab="${k}">${name}${n ? ` · ${n}` : ''}</button>`;
      let list = '';
      if (ALL.rows === null) list = '<p class="hcd-mut">Loading…</p>';
      else if (arch) list = f.length ? f.map(rowA).join('') : '<p class="hcd-mut">Nothing archived.</p>';
      else { const shown = ALL.tab === 'run' ? [['run', 'Working']] : ALL.tab === 'need' ? [['need', 'Needs you']] : [['run', 'Working'], ['need', 'Needs you'], ['old', 'Earlier']];
        shown.forEach(([g, name]) => { const xs = by(g); if (xs.length) list += `<h2 class="hcd-grp">${name}</h2>${xs.map(rowA).join('')}`; });
        if (!list) list = '<p class="hcd-mut">No sessions found.</p>'; }
      body(`<main class="hcd-page hcd-allp"><h1>Sessions</h1>
      <form class="hcd-inline hcd-allbar" id="hcdAllF"><label class="hcd-sr" for="hcdAllQ">Search sessions</label><input id="hcdAllQ" type="search" placeholder="Search by words, title or repo" value="${esc(ALL.q)}">
        <label class="hcd-chip hcd-filter"><span class="hcd-sr">Repo</span><select id="hcdAllRepo" aria-label="Repo"><option value="">Repo: all</option>${(OV?.repos || []).map(r => `<option value="${esc(r.repo)}"${ALL.repo === r.repo ? ' selected' : ''}>${esc(r.repo.split('/')[1] || r.repo)}</option>`).join('')}</select></label>
        <button class="hcd-btn" type="submit">Search</button></form>
      <div class="hcd-tabs" role="tablist">${tab('active', 'All', 0)}${tab('run', 'Working', arch || ALL.rows === null ? 0 : by('run').length)}${tab('need', 'Needs you', arch || ALL.rows === null ? 0 : by('need').length)}${tab('archived', 'Archived', 0)}</div>
      <div class="hcd-alist">${list}</div></main>`);
      const rf = $('#hcdAllRepo'); if (rf) rf.addEventListener('change', () => { ALL.repo = rf.value; draw(); });
    };
    draw();
    if (ALL.rows === null) {
      try { ALL.rows = (await api('GET', `/api/devsahayak/tasks?limit=100&archived=${arch ? 1 : 0}&q=${encodeURIComponent(ALL.q)}`)).tasks || []; } catch (e) { ALL.rows = []; toast(e.message, true); }
      if (VIEW === 'all') draw();
    }
  }

  // ------------------------------------------------------------------ scheduled tasks (Phase 5) ---
  const DAYS = [['daily', 'Every day'], ['weekdays', 'Monday to Friday'], ['weekly:0', 'Every Monday'], ['weekly:1', 'Every Tuesday'], ['weekly:2', 'Every Wednesday'], ['weekly:3', 'Every Thursday'],
    ['weekly:4', 'Every Friday'], ['weekly:5', 'Every Saturday'], ['weekly:6', 'Every Sunday'], ['off', 'Only on Run now or its trigger']];
  const until = iso => { const m = Math.round((Date.parse(iso || '') - Date.now()) / 60000); return !isFinite(m) ? '' : m < 1 ? 'in a minute' : m < 60 ? `in ${m} min` : m < 1440 ? `in ${Math.round(m / 60)} h` : `in ${Math.round(m / 1440)} days`; };
  const runStat = r => r ? ({merged: ['ok', 'Merged'], pr_open: ['ok', 'Succeeded'], ready: ['ok', 'Succeeded'], explained: ['ok', 'Succeeded'], failed: ['bad', 'Failed'],
    checks_failed: ['bad', 'Failed'], refused: ['bad', 'Failed'], cancelled: ['warn', 'Cancelled']}[r.status] || ['soft', STATUS[r.status] || r.status_label || r.status]) : ['soft', 'Never run'];
  const trigBadge = sc => sc.event ? '<span class="hcd-badge gh">GitHub</span>' : sc.days === 'off' ? '<span class="hcd-badge api">API</span>' : '<span class="hcd-badge sch">Schedule</span>';
  const sw = (on, attrs, label) => `<button type="button" class="hcd-sw" role="switch" aria-checked="${on}" aria-label="${esc(label)}" ${attrs}><i></i></button>`;
  function scheduled() {
    const list = OV?.schedules || [], repos = OV?.repos || [], ready = repos.length && OV?.settings?.github;
    if (TID) { const sc = list.find(x => x.id === TID); if (sc) return schedDetail(sc); }
    const tab = P.stabS || 'all', shown = list.filter(x => tab === 'all' || (tab === 'on' ? x.enabled : !x.enabled));
    const t2 = (k, name, n) => `<button type="button" role="tab" aria-selected="${tab === k}" data-act="schedtab" data-tab="${k}">${name} · ${n}</button>`;
    frame(`<main class="hcd-page hcd-schedp"><div class="hcd-phead"><div><h1>Scheduled tasks</h1>
      <p class="hcd-lede">Hoola starts a session by itself on a schedule, when your program calls it, or on a GitHub event. Every run opens its own branch and pull request; merging stays yours.</p></div>
      <button type="button" class="hcd-btn pri" data-act="schednew"${ready ? '' : ' disabled title="Connect GitHub and add a repo in Settings first"'}>${svg('new')}New task</button></div>
      <div class="hcd-tabs" role="tablist">${t2('all', 'All', list.length)}${t2('on', 'Active', list.filter(x => x.enabled).length)}${t2('off', 'Paused', list.filter(x => !x.enabled).length)}</div>
      ${shown.length ? `<div class="hcd-table" role="table" aria-label="Scheduled tasks"><div class="hcd-tr hcd-th" role="row"><span role="columnheader">Task</span><span role="columnheader">Trigger</span><span role="columnheader">Repository</span><span role="columnheader">Next run</span><span role="columnheader">Last run</span><span role="columnheader">On</span></div>
        ${shown.map(sc => { const last = (sc.runs || [])[0], ls = runStat(last); return `<div class="hcd-tr" role="row" data-sched="${esc(sc.id)}">
          <button type="button" class="hcd-tcell hcd-tname" data-act="schedopen" data-id="${esc(sc.id)}"><b>${esc(sc.title)}</b><small>${esc(sc.text)}</small></button>
          <span class="hcd-tcell">${trigBadge(sc)}<span>${esc(sc.when)}</span></span>
          <span class="hcd-tcell"><code class="hcd-br">${esc((sc.repo || '').split('/')[1] || sc.repo)}</code></span>
          <span class="hcd-tcell">${!sc.enabled ? 'Paused' : sc.event ? 'On event' : sc.next_run ? 'Next run ' + esc(until(sc.next_run)) : 'On call'}</span>
          <span class="hcd-tcell"><span class="hcd-c ${ls[0]}">${esc(ls[1])}</span></span>
          <span class="hcd-tcell">${sw(!!sc.enabled, `data-act="schedtoggle" data-id="${esc(sc.id)}" data-on="${sc.enabled ? 1 : 0}"`, (sc.enabled ? 'Pause ' : 'Resume ') + sc.title)}</span></div>`; }).join('')}</div>`
        : `<p class="hcd-mut">${list.length ? 'Nothing here.' : 'No scheduled tasks yet.'}</p>`}
      <p class="hcd-mut">Times are India time. A schedule runs at most once a day; a run still working is not started twice. If GitHub access is lost, runs are skipped and you are told.</p></main>`);
  }
  function schedDetail(sc) {
    const runs = sc.runs || [], card = (k, v) => `<div class="hcd-kv"><small>${k}</small><b>${v}</b></div>`;
    frame(`<main class="hcd-page hcd-schedp" data-sched="${esc(sc.id)}"><button type="button" class="hcd-back" data-go="scheduled">${svg('chev', 'hcd-flip')}Scheduled tasks</button>
      <div class="hcd-phead"><h1>${esc(sc.title)}</h1><span class="hcd-flex"></span>${sw(!!sc.enabled, `data-act="schedtoggle" data-id="${esc(sc.id)}" data-on="${sc.enabled ? 1 : 0}"`, sc.enabled ? 'Pause it' : 'Resume it')}
        <button type="button" class="hcd-btn" data-act="schedtrig" data-id="${esc(sc.id)}">Trigger address…</button><button type="button" class="hcd-btn" data-act="scheddel" data-id="${esc(sc.id)}">Delete</button>
        <button type="button" class="hcd-btn pri" data-act="schedrun" data-id="${esc(sc.id)}">Run now</button></div>
      <div class="hcd-kvs">${card('Trigger', esc(sc.when) + (sc.days !== 'off' && !sc.event ? ' IST' : ''))}${card('Next run', !sc.enabled ? 'Paused' : sc.event ? 'On event' : sc.next_run ? esc(until(sc.next_run)) : 'On call')}
        ${card('Repository', esc((sc.repo || '').split('/')[1] || sc.repo))}${card('After the change', sc.mode === 'auto' ? 'Opens the pull request' : 'Waits for your tap')}</div>
      <p class="hcd-prompt">${esc(sc.text)}</p>
      ${sc.last_note ? `<p class="hcd-err">${esc(sc.last_note)}</p>` : ''}
      ${sc.event && !((OV?.repos || []).find(r => r.repo === sc.repo)?.events || {}).on ? `<p class="hcd-err">GitHub events are not connected for this repo yet. Connect them in <button type="button" class="hcd-link" data-go="settings">Settings</button>.</p>` : ''}
      <h2 class="hcd-grp">History</h2>
      ${runs.length ? `<div class="hcd-table hcd-hist">${runs.map(r => { const ls = runStat(r); return `<button type="button" class="hcd-tr" data-tid="${esc(r.id)}"><span class="hcd-tcell">${esc(ago(r.at))}</span><span class="hcd-tcell"><span class="hcd-c ${ls[0]}">${esc(ls[1])}</span></span>
          <span class="hcd-tcell hcd-tgrow">${esc(r.title || r.number)}${r.pr_number ? ' · PR #' + r.pr_number : ''}</span></button>`; }).join('')}</div>` : '<p class="hcd-mut">It has not run yet.</p>'}</main>`);
  }
  function schedForm() {
    const repos = OV?.repos || [], d = $('#hcdDlg');
    d.innerHTML = `<form class="hcd-schedf" id="hcdSchedF"><h2>New scheduled task</h2>
        <label class="hcd-f"><span>Name <small>optional - Hoola names it from the task</small></span><input name="title" maxlength="120" placeholder="Nightly dependency check"></label>
        <label class="hcd-f"><span>What should Hoola do each time?</span><textarea name="text" rows="3" maxlength="6000" required placeholder="Update the dependencies that have a security fix, run the tests, and say what changed"></textarea></label>
        <div class="hcd-trig"><div class="hcd-trigh"><b>Trigger</b></div>
          <div class="hcd-inline"><label class="hcd-chip">Starts <select name="event" aria-label="What starts it"><option value="">On a schedule</option>${EVENTS.map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select></label>
          <label class="hcd-chip" data-for="clock">When <select name="days" aria-label="When">${DAYS.map(([k, n]) => `<option value="${k}"${k === 'weekdays' ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
          <label class="hcd-chip" data-for="clock">At <input type="time" name="at" value="09:00" aria-label="Time, India time" title="India time"></label>
          <label class="hcd-chip" data-for="issue_opened issue_labeled" hidden>Label <input name="label" maxlength="60" size="10" placeholder="hoola" aria-label="Issue label"></label>
          <label class="hcd-chip" data-for="ci_failed push" hidden>Branch <input name="branch" maxlength="100" size="10" placeholder="default" aria-label="Branch"></label>
          <label class="hcd-chip" data-for="issue_opened issue_labeled pr_opened push" hidden>By <select name="who" aria-label="Whose events count"><option value="me">Only me</option><option value="anyone">Anyone in the repo (private repos)</option></select></label></div>
          <p class="hcd-mut" data-for="clock">India time. A task runs at most once a day; a run still working is not started twice. Your own program can also start it - make a trigger token after saving.</p>
          <p class="hcd-mut" data-for="issue_opened issue_labeled pr_opened ci_failed push" hidden>GitHub events must be connected for the repo first (Settings > the repo > GitHub events). The event's own words reach Hoola as information, never as instructions. A new pull request from someone else gets a draft review; posting it is your tap.</p></div>
        <div class="hcd-grid2"><label class="hcd-f"><span>Repository</span><select name="repo" aria-label="Repo">${repos.map(r => `<option value="${esc(r.repo)}"${r.repo === REPO ? ' selected' : ''}>${esc(r.repo)}</option>`).join('') || '<option value="">no repo yet</option>'}</select></label>
          <label class="hcd-f"><span>After the change</span><select name="mode" aria-label="What happens with the change"><option value="ask">Ask first</option><option value="auto">Open the pull request</option></select></label></div>
        <p class="hcd-mut">"Open the pull request" works on private repos - a public repo always waits for your tap.</p>
        <div class="hcd-dlgb"><span class="hcd-flex"></span><button type="button" class="hcd-btn" data-act="dlgclose">Cancel</button><button class="hcd-btn pri" type="submit">Create task</button></div></form>`;
    d.showModal(); d.querySelector('[name=text]').focus();
    d.addEventListener('close', () => setTimeout(() => { if (!d.open) d.innerHTML = ''; }, 0), {once: true});
  }
  const EVENTS = [['issue_labeled', 'On an issue label'], ['issue_opened', 'On a new issue'], ['pr_opened', 'On a new pull request'], ['ci_failed', 'On a CI failure'], ['push', 'On a push']];
  function schedFields(f) {       // show only the fields the chosen start needs
    const ev = f.event.value; f.querySelectorAll('[data-for]').forEach(x => { x.hidden = !x.dataset.for.split(' ').includes(ev || 'clock'); });
    if (ev === 'pr_opened' && !f.text.value.trim()) f.text.value = 'Review the pull request';
  }
  function schedHTML(sc) {
    const runs = sc.runs || [];
    return `<section class="hcd-card hcd-sched" data-sched="${esc(sc.id)}"><div class="hcd-sh"><h2>${esc(sc.title)}</h2>
        <span class="hcd-pill ${!sc.enabled ? 'soft' : sc.next_run || sc.event ? 'ok' : 'soft'}">${!sc.enabled ? 'Paused' : sc.event ? 'On a GitHub event' : sc.next_run ? 'Next run ' + esc(until(sc.next_run)) : 'On demand'}</span></div>
      <p class="hcd-mut">${esc((sc.repo || '').split('/')[1] || sc.repo)} · ${esc(sc.when)}${sc.days !== 'off' ? ' (India time)' : ''} · ${sc.mode === 'auto' ? 'opens the pull request' : 'waits for your tap before the pull request'}${sc.trigger ? ' · has a trigger address' : ''}</p>
      <p class="hcd-schedt">${esc(sc.text.length > 320 ? sc.text.slice(0, 320) + '…' : sc.text)}</p>
      ${sc.last_note ? `<p class="hcd-err">${esc(sc.last_note)}</p>` : ''}
      ${sc.event && !((OV?.repos || []).find(r => r.repo === sc.repo)?.events || {}).on ? `<p class="hcd-err">GitHub events are not connected for this repo yet. Connect them in <button type="button" class="hcd-link" data-go="settings">Settings</button>.</p>` : ''}
      <div class="hcd-acts"><button type="button" class="hcd-btn pri" data-act="schedrun" data-id="${esc(sc.id)}">Run now</button>
        <button type="button" class="hcd-btn" data-act="schedtoggle" data-id="${esc(sc.id)}" data-on="${sc.enabled ? 1 : 0}">${sc.enabled ? 'Pause' : 'Resume'}</button>
        <button type="button" class="hcd-btn" data-act="schedtrig" data-id="${esc(sc.id)}">Trigger address…</button>
        <span class="hcd-flex"></span><button type="button" class="hcd-btn" data-act="scheddel" data-id="${esc(sc.id)}">Delete</button></div>
      <h3>History</h3>
      ${runs.length ? runs.map(r => `<div class="hcd-arow"><button type="button" class="hcd-sessb" data-tid="${esc(r.id)}"><span class="hcd-st"><i class="hcd-dot ${r.status === 'merged' ? 'ok' : r.status === 'failed' ? 'bad' : NEEDS.has(r.status) ? 'warn' : 'soft'}"></i><span>${esc(r.title || r.number)}</span></span>
          <small>${esc(STATUS[r.status] || r.status_label || r.status)}${r.pr_number ? ' · PR #' + r.pr_number : ''} · ${esc(ago(r.at))}</small></button></div>`).join('') : '<p class="hcd-mut">It has not run yet.</p>'}</section>`;
  }
  async function newSchedule(f) {
    const b = f.querySelector('button[type="submit"]'); b.disabled = true;
    const ev = f.event.value, body = {text: f.text.value.trim(), repo: f.repo.value, days: ev ? 'off' : f.days.value, at: f.at.value || '09:00', mode: f.mode.value};
    if (f.title && f.title.value.trim()) body.title = f.title.value.trim();
    if (ev) { body.event = ev; body.filter = {label: f.label.value.trim(), branch: f.branch.value.trim(), who: f.who.value}; }
    try { await api('POST', '/api/devsahayak/schedules', body);
      toast('Scheduled.'); const d = $('#hcdDlg'); if (d.open) d.close(); await load(); drawSide(); scheduled(); }
    catch (e) { toast(e.message, true); b.disabled = false; }
  }
  async function triggerDialog(sc) {
    if (!sc) return; const url = location.origin + '/api/devsahayak/hooks/' + sc.id;
    const r = await dialog(`<h2>Trigger address</h2>
      <p class="hcd-mut">Your own program can start a run of "${esc(sc.title)}" by calling this address with a token - for example when a deploy fails. At most 10 runs an hour.</p>
      <pre class="hcd-term">${esc(url)}</pre>
      <p class="hcd-mut">${sc.trigger ? 'A token exists. It was shown once, when it was made. A new token stops the old one.' : 'No token yet. It is shown once - keep it where your program keeps its secrets.'}</p>
      <div class="hcd-dlgb"><button class="hcd-btn" value="no">Close</button>${sc.trigger ? '<button class="hcd-btn" value="drop">Remove the trigger</button>' : ''}<button class="hcd-btn pri" value="make">${sc.trigger ? 'Make a new token' : 'Make a token'}</button></div>`);
    try {
      if (r === 'drop') { await api('DELETE', `/api/devsahayak/schedules/${encodeURIComponent(sc.id)}/trigger`); toast('The trigger is removed.'); await load(); return scheduled(); }
      if (r !== 'make') return;
      const k = await api('POST', `/api/devsahayak/schedules/${encodeURIComponent(sc.id)}/trigger`); await load(); scheduled();
      const curl = `curl -X POST ${url} \\\n  -H "Authorization: Bearer ${k.token}" \\\n  -H "Content-Type: application/json" \\\n  -d '{"text": "what happened, in a line"}'`;
      await dialog(`<h2>Your trigger token</h2><p class="hcd-mut"><b>Copy it now - it is not shown again.</b> Hoola keeps only a fingerprint of it.</p>
        <pre class="hcd-term" id="hcdTok1">${esc(k.token)}</pre>
        <p class="hcd-mut">The text your program sends is added to the task as information about that run. It is never read as an instruction.</p>
        <pre class="hcd-term">${esc(curl)}</pre>
        <div class="hcd-dlgb"><button type="button" class="hcd-btn" data-act="copy" data-text="${esc(k.token)}">Copy the token</button><button class="hcd-btn pri" value="ok">Done</button></div>`);
    } catch (e) { toast(e.message, true); }
  }
  // ------------------------------------------------------------------ a read-only link to one session (Phase 5) ---
  async function shareDialog(t) {
    if (!t) return;
    const radio = (on, title, sub2, v) => `<label class="hcd-vis${on ? ' on' : ''}"><input type="radio" name="hcdVis" value="${v}"${on ? ' checked' : ''}><span><b>${title}</b><small>${sub2}</small></span></label>`;
    try {
      if (!t.share?.on) {
        const r = await dialog(`<h2>Share this session</h2>
          <p class="hcd-mut">People get a read-only copy of the conversation as it is now: your words, Hoola's steps and the code changes in <b>${esc((t.repo || '').split('/')[1] || t.repo)}</b>. Your code, keys and environment are never shared, and they cannot change, send or start anything.</p>
          <fieldset class="hcd-visg"><legend class="hcd-sr">Who can open it</legend>${radio(true, 'Private', 'Only you', 'private')}${radio(false, 'Anyone with the link', 'No sign-in needed · stops working after 7 days', 'link')}</fieldset>
          <div class="hcd-dlgb"><span class="hcd-flex"></span><button class="hcd-btn" value="no">Cancel</button><button class="hcd-btn pri" value="ok" id="hcdShareGo">Make the link</button></div>`);
        if (r !== 'ok') return;
        // "Private" (the safe choice, ticked first) makes no link at all; only "Anyone with the link" makes one
        if (!(EL.querySelector('#hcdDlg input[name=hcdVis][value=link]') || {}).checked) { toast('It stays private - no link was made.'); return; }
        await api('POST', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}/share`, {on: true}); await refreshTask(t.id, false); t = TASK;
      }
      const url = location.origin + t.share.path;
      const r = await dialog(`<h2>Share this session</h2>
        <p class="hcd-mut">Anyone with this link can read the session until ${esc(new Date(t.share.until).toLocaleDateString(undefined, {day: 'numeric', month: 'short'}))}. Attached files and your account name are not shown.</p>
        <fieldset class="hcd-visg"><legend class="hcd-sr">Who can open it</legend>${radio(false, 'Private', 'Only you - stops the link', 'private')}${radio(true, 'Anyone with the link', 'Stops working after 7 days', 'link')}</fieldset>
        <div class="hcd-linkrow"><code id="hcdShareUrl">${esc(url)}</code><button type="button" class="hcd-btn sm pri" data-act="copy" data-text="${esc(url)}">Copy link</button></div>
        <div class="hcd-dlgb"><button class="hcd-btn danger ghost" value="stop">Stop sharing</button><span class="hcd-flex"></span><button class="hcd-btn" value="ok">Done</button></div>`);
      const pick = r === 'ok' && !(EL.querySelector('#hcdDlg input[name=hcdVis][value=link]') || {}).checked;
      if (r === 'stop' || pick) { await api('POST', `/api/devsahayak/tasks/${encodeURIComponent(t.id)}/share`, {on: false}); toast('The link no longer works.'); await refreshTask(t.id, false); }
    } catch (e) { toast(e.message, true); }
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
    const us = OV?.usage || {}, envs = (ENVS.envs || []).filter(e => !e.archived);
    const nav = [['hcdSecGit', 'GitHub and pull requests'], ['hcdSecRepos', 'Repositories'], ['hcdSecEnvs', 'Environments'], ['hcdSecRules', 'Limits and your rules'], ['hcdSecPlug', 'Plugins'], ['hcdSecUse', 'Usage']];
    frame(`<main class="hcd-page hcd-setp"><h1>Settings</h1><div class="hcd-setgrid">
      <nav class="hcd-snav" aria-label="Settings sections">${nav.map(([id, n], i) => `<button type="button" class="hcd-snavb${i === 0 ? ' on' : ''}" data-act="sjump" data-to="${id}">${n}</button>`).join('')}</nav>
      <div class="hcd-grid">
      <section class="hcd-card" id="hcdSecGit"><h2>GitHub access</h2><p class="hcd-mut">A fine-grained token, typed only here. It is locked away on the server and never shown to the AI or the chat.</p>
        <p>${st.github ? `<span class="hcd-c ok">Connected</span>${st.login ? ' as <b>' + esc(st.login) + '</b>' : ''}${st.token_label ? ' · ' + esc(st.token_label) : ''}` : '<span class="hcd-c warn">Not connected</span>'}</p>
        <form class="hcd-inline" id="hcdTok"><label for="hcdTokIn" class="hcd-sr">GitHub token</label><input id="hcdTokIn" type="password" autocomplete="off" placeholder="github_pat_…"><button class="hcd-btn" type="submit">Save</button>${st.github ? '<button class="hcd-btn" type="button" id="hcdTokDel">Forget</button>' : ''}</form>
        ${(st.permissions || []).length ? `<p class="hcd-mut">Needs: ${esc(st.permissions.join(', '))}.</p>` : ''}</section>
      <section class="hcd-card" id="hcdSecRepos"><h2>Repositories Hoola may work in</h2>
        ${repos.map(r => `<div class="hcd-repo"><code>${esc(r.repo)}</code><span class="hcd-mut">${r.private ? 'private' : 'public · asks before a PR'}${r.language ? ' · ' + esc(r.language) : ''}</span><button type="button" class="hcd-btn sm" data-rmrepo="${esc(r.repo)}">Remove</button></div>
          <details class="hcd-rbox"${r.setup_cmd || r.test_cmd || Object.keys(r.env_vars || {}).length || (r.net || {}).level !== 'none' || ((r.net || {}).secrets || []).length || (r.events || {}).on ? ' open' : ''}><summary>How this repo runs in the box</summary>
            <form class="hcd-rboxf" data-repobox="${esc(r.repo)}">
              <label class="hcd-f"><span>Setup command <small>installs the dependencies once, with internet</small></span><input name="setup" maxlength="380" value="${esc(r.setup_cmd || '')}" placeholder="pip install -r requirements.txt"></label>
              <label class="hcd-f"><span>Test command <small>Hoola is told to run exactly this</small></span><input name="test" maxlength="380" value="${esc(r.test_cmd || '')}" placeholder="python3 -m pytest -q"></label>
              <label class="hcd-f"><span>Environment variables <small>one NAME=value a line - never a key or a password</small></span><textarea name="env" rows="2" maxlength="2000" placeholder="APP_ENV=test">${esc(Object.entries(r.env_vars || {}).map(([k, v]) => k + '=' + v).join('\n'))}</textarea></label>
              <label class="hcd-f"><span>Network for commands <small>the one-time setup step always has it</small></span><select name="net" aria-label="Network for commands">
                <option value="none"${(r.net || {}).level === 'none' || !(r.net || {}).level ? ' selected' : ''}>No network</option>
                <option value="limited"${(r.net || {}).level === 'limited' ? ' selected' : ''}>Package registries and the hosts below</option>
                <option value="full"${(r.net || {}).level === 'full' ? ' selected' : ''}>Any public website</option></select></label>
              <label class="hcd-f"><span>Allowed hosts <small>one a line, like api.example.com or *.example.com</small></span><textarea name="hosts" rows="2" maxlength="2000" placeholder="api.example.com">${esc(((r.net || {}).hosts || []).join('\n'))}</textarea></label>
              ${(OV?.net || {}).on ? '' : '<p class="hcd-mut" data-netoff>Network levels are switched off on this server until its check passes. Your choice is saved and used once they are on.</p>'}
              <div class="hcd-acts"><span class="hcd-mut">Empty = Hoola reads them from the repo (.hoola/lab.json, AGENTS.md, CI).</span><span class="hcd-flex"></span><button class="hcd-btn sm" type="submit">Save</button></div></form>
            <div class="hcd-rsec" data-secrets="${esc(r.repo)}"><h3>Keys added outside the box</h3>
              <p class="hcd-mut">A key for one outside website. It is added to the request after it leaves the box, so the AI and the box never see it. It is not shown again after you save it.</p>
              ${((r.net || {}).secrets || []).map(x => `<div class="hcd-srow"><span><code>${esc(x.host)}</code><small class="hcd-mut">${esc(x.header)}${x.prefix ? ' · ' + esc(x.prefix) : ''} · saved ${esc(ago(x.at))}</small></span><button type="button" class="hcd-btn sm" data-rmsecret="${esc(x.host)}" data-repo="${esc(r.repo)}">Remove</button></div>`).join('')}
              <form class="hcd-inline hcd-secf" data-secretf="${esc(r.repo)}"><input name="host" placeholder="api.example.com" maxlength="200" aria-label="Host" required>
                <input name="header" value="Authorization" maxlength="40" aria-label="Header name" class="sm"><input name="prefix" value="Bearer" maxlength="16" aria-label="Word before the key" class="xs">
                <input name="value" type="password" autocomplete="off" placeholder="the key" maxlength="4000" aria-label="The key" required><button class="hcd-btn sm" type="submit">Save key</button></form></div>
            <div class="hcd-rsec" data-mem="${esc(r.repo)}"><h3>What Hoola remembers</h3>
              <p class="hcd-mut">Notes Hoola keeps from earlier sessions on this repo; a new session starts with them. Your &lt;private&gt; text and anything that looks like a key are never kept.</p>
              <div class="hcd-acts"><button type="button" class="hcd-btn sm" data-memshow="${esc(r.repo)}">Show</button></div><div data-memlist></div></div>
            <div class="hcd-rsec"><h3>GitHub events</h3>
              <p class="hcd-mut">${(r.events || {}).on ? `<span class="hcd-c ok">Connected</span>${(r.events.last || {}).at ? ' · last event ' + esc(ago(r.events.last.at)) : ' · nothing received yet'}${r.events.by_hoola ? '' : ' · webhook added by you'}` : 'GitHub can tell Hoola when an issue is labelled, a pull request is opened, a CI run fails or something is pushed - to start one of your scheduled tasks.'}</p>
              <div class="hcd-acts"><button type="button" class="hcd-btn sm" data-events="${esc(r.repo)}" data-on="${(r.events || {}).on ? 1 : 0}">${(r.events || {}).on ? 'Disconnect' : 'Connect GitHub events'}</button></div></div></details>`).join('') || '<p class="hcd-mut">No repos yet.</p>'}
        <form class="hcd-inline" id="hcdAddRepo"><label for="hcdRepoIn" class="hcd-sr">Repo</label><input id="hcdRepoIn" placeholder="owner/name" maxlength="200"><button class="hcd-btn" type="submit">Add</button></form></section>
      <section class="hcd-card"><h2>Pull requests</h2>
        ${sw('ask_before_pr', 'Ask me before opening a pull request', 'Public repos always ask')}
        ${sw('draft_pr', 'Open pull requests as drafts', 'Marked ready when CI is green')}
        ${sw('allow_workflows', 'Allow edits to .github/workflows', 'Off: CI files are never touched')}
        ${sw('archive_after_merge', 'Archive a session when its pull request is merged', 'It stays under View all > Archived')}
        <label class="hcd-f"><span>Merge method</span><select data-set="merge_method">${['squash', 'merge', 'rebase'].map(m => `<option${m === st.merge_method ? ' selected' : ''}>${m}</option>`).join('')}</select></label>
        <label class="hcd-f"><span>Reviews of teammates' PRs</span><select data-set="review_post"><option value="draft"${st.review_post === 'draft' ? ' selected' : ''}>Draft - I post them</option><option value="direct"${st.review_post === 'direct' ? ' selected' : ''}>Post comments directly</option></select></label></section>
      <section class="hcd-card" id="hcdSecEnvs"><div class="hcd-sh"><h2>Cloud environments</h2><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-act="envnew">${svg('new')}New environment</button></div>
        <p class="hcd-mut">Where Hoola Code runs your repo's commands: network access, variables and a setup script. "Auto" follows each repo's own settings.</p>
        ${envs.length ? envs.map(e => `<div class="hcd-repo">${svg('cloud')}<b>${esc(e.name)}</b><span class="hcd-mut">${esc(LEVEL[e.net.level])}${e.net.level === 'limited' && e.net.pkgs !== false ? ' · package managers' : ''}${e.setup ? ' · setup script' : ''}</span><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-act="envedit" data-id="${esc(e.id)}">Edit</button></div>`).join('') : '<p class="hcd-mut">No environments yet.</p>'}</section>
      <section class="hcd-card" id="hcdSecRules"><h2>Limits and your rules</h2>
        <label class="hcd-f"><span>Files per change</span><input type="number" min="1" max="60" data-set="max_files" value="${+st.max_files || 20}"></label>
        <label class="hcd-f"><span>Lines per change</span><input type="number" min="20" max="5000" data-set="max_lines" value="${+st.max_lines || 1500}"></label>
        <label class="hcd-f"><span>Your coding rules (Hoola follows them every time)</span><textarea rows="4" data-set="rules" maxlength="4000">${esc(st.rules || '')}</textarea></label>
        <p class="hcd-mut">Always on: ${esc((st.never || []).slice(0, 4).join(' · '))}</p></section>
      <section class="hcd-card" id="hcdSecPlug"><div class="hcd-sh"><h2>Plugins</h2><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-act="plugins">${svg('new')}Manage plugins</button></div>
        <p class="hcd-mut">Claude Code plugins from GitHub: their commands, agents, skills and hooks join every session of yours.</p></section>
      <section class="hcd-card" id="hcdSecUse"><h2>Usage this month</h2>
        ${us.limit_inr > 0 ? `<div class="hcd-prog"><i style="width:${Math.min(100, Math.round(us.pct || 0))}%"></i></div><div class="hcd-row"><span>${rs(us.spent_inr || 0)} of ${rs(us.limit_inr)}</span><b>${Math.round(us.pct || 0)}%</b></div>`
          : `<p class="hcd-mut">${us.spent_inr > 0 ? rs(us.spent_inr) + ' this month across all of Hoola. No monthly limit is set.' : 'Nothing spent this month yet.'}</p>`}</section>
    </div></div></main>`);
    if (P.stab) { const id = {envs: 'hcdSecEnvs', repos: 'hcdSecRepos'}[P.stab]; P.stab = ''; if (id) setTimeout(() => ACTS.sjump({dataset: {to: id}}), 0); }
    EL.querySelectorAll('[data-repobox]').forEach(f => f.addEventListener('submit', async ev => { ev.preventDefault();
      const env = {}; String(f.env.value || '').split('\n').forEach(l => { const i = l.indexOf('='); if (i > 0) env[l.slice(0, i).trim()] = l.slice(i + 1).trim(); });
      const [o, n] = f.dataset.repobox.split('/');
      try { await api('PATCH', `/api/devsahayak/repos/${encodeURIComponent(o)}/${encodeURIComponent(n)}`, {setup_cmd: f.setup.value, test_cmd: f.test.value, env_vars: env, net_level: f.net.value, net_hosts: String(f.hosts.value || '').split(/[\s,]+/).filter(Boolean)}); toast('Saved.'); await load(); } catch (e) { toast(e.message, true); } }));
    const rp = full => full.split('/').map(encodeURIComponent).join('/');
    EL.querySelectorAll('[data-secretf]').forEach(f => f.addEventListener('submit', async ev => { ev.preventDefault();
      try { await api('PUT', `/api/devsahayak/repos/${rp(f.dataset.secretf)}/secrets`, {host: f.host.value.trim(), header: f.header.value.trim(), prefix: f.prefix.value.trim(), value: f.value.value});
        f.value.value = ''; toast('Saved. The key is not shown again.'); await load(); settings(); } catch (e) { toast(e.message, true); } }));
    EL.querySelectorAll('[data-rmsecret]').forEach(b => b.addEventListener('click', async () => { if (!confirm(`Remove the key for ${b.dataset.rmsecret}?`)) return;
      try { await api('DELETE', `/api/devsahayak/repos/${rp(b.dataset.repo)}/secrets/${encodeURIComponent(b.dataset.rmsecret)}`); await load(); settings(); } catch (e) { toast(e.message, true); } }));
    // Hoola Code memory (claude-mem's idea): what Hoola remembers about each repo - see, delete one, forget all
    const memPaint = async box => { const full = box.dataset.mem, list = box.querySelector('[data-memlist]');
      try { const m = await api('GET', `/api/devsahayak/memory?repo=${encodeURIComponent(full)}`);
        const obs = m.observations || [], sums = m.summaries || [];
        list.innerHTML = (!obs.length && !sums.length) ? '<p class="hcd-mut">Nothing yet. Hoola writes notes when a session on this repo ends.</p>' :
          sums.slice(0, 3).map(x => `<div class="hcd-srow"><span><b>Session</b> ${esc(x.request || '')}<small class="hcd-mut"> · ${esc(x.completed || '')}</small></span><button type="button" class="hcd-btn sm" data-memdel="${x.id}" data-kind="summary">Delete</button></div>`).join('')
          + obs.map(o => `<div class="hcd-srow"><span><code>#${o.id}</code> <b>${esc(o.type)}</b> ${esc(o.title)}${o.hits > 1 ? ` <small class="hcd-mut">×${o.hits}</small>` : ''}${(o.files || []).length ? `<small class="hcd-mut"> · ${esc(o.files.slice(0, 3).join(', '))}</small>` : ''}</span><button type="button" class="hcd-btn sm" data-memdel="${o.id}" data-kind="obs">Delete</button></div>`).join('')
          + `<div class="hcd-acts"><span class="hcd-flex"></span><button type="button" class="hcd-btn sm" data-memall>Forget everything about this repo</button></div>`;
        list.querySelectorAll('[data-memdel]').forEach(b => b.addEventListener('click', async () => {
          try { await api('DELETE', `/api/devsahayak/memory/${b.dataset.memdel}?kind=${b.dataset.kind}`); await memPaint(box); } catch (e) { toast(e.message, true); } }));
        list.querySelector('[data-memall]')?.addEventListener('click', async () => { if (!confirm(`Forget everything Hoola remembers about ${full}?`)) return;
          try { await api('DELETE', `/api/devsahayak/memory?repo=${encodeURIComponent(full)}`); toast('Forgotten.'); await memPaint(box); } catch (e) { toast(e.message, true); } });
      } catch (e) { toast(e.message, true); } };
    EL.querySelectorAll('[data-memshow]').forEach(b => b.addEventListener('click', () => memPaint(b.closest('[data-mem]'))));
    EL.querySelectorAll('[data-events]').forEach(b => b.addEventListener('click', async () => { const full = b.dataset.events; b.disabled = true;
      try {
        if (b.dataset.on === '1') { if (!confirm(`Stop GitHub events for ${full}? Tasks that start on an event will no longer start.`)) { b.disabled = false; return; }
          const r = await api('DELETE', `/api/devsahayak/repos/${rp(full)}/events`); toast(r.left_on_github ? 'Disconnected. Remove the webhook on GitHub too (repo > Settings > Webhooks).' : 'Disconnected.'); }
        else { const r = await api('POST', `/api/devsahayak/repos/${rp(full)}/events`);
          if (r.by_hoola) toast('Connected. Hoola added the webhook on GitHub.');
          else await dialog(`<h2>Add this webhook on GitHub</h2><p class="hcd-mut">Your token may not add webhooks, so add it yourself once. <b>The secret is shown only now.</b></p>
            <ol class="hcd-how">${(r.how || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>
            <p class="hcd-mut">Payload URL</p><pre class="hcd-term" id="hcdHookUrl">${esc(r.url)}</pre><p class="hcd-mut">Secret</p><pre class="hcd-term" id="hcdHookSecret">${esc(r.secret)}</pre>
            <div class="hcd-dlgb"><button type="button" class="hcd-btn" data-act="copy" data-text="${esc(r.url)}">Copy the URL</button><button type="button" class="hcd-btn" data-act="copy" data-text="${esc(r.secret)}">Copy the secret</button><button class="hcd-btn pri" value="ok">Done</button></div>`); }
        await load(); settings();
      } catch (e) { toast(e.message, true); b.disabled = false; } }));
    $('#hcdTok')?.addEventListener('submit', async ev => { ev.preventDefault(); const v = $('#hcdTokIn').value.trim(); if (!v) return;
      try { await api('PUT', '/api/devsahayak/token', {token: v}); $('#hcdTokIn').value = ''; toast('GitHub connected.'); await load(); settings(); } catch (e) { toast(e.message, true); } });
    $('#hcdTokDel')?.addEventListener('click', async () => { if (!confirm('Forget the GitHub token?')) return; try { await api('DELETE', '/api/devsahayak/token'); await load(); settings(); } catch (e) { toast(e.message, true); } });
    $('#hcdAddRepo')?.addEventListener('submit', async ev => { ev.preventDefault(); const v = $('#hcdRepoIn').value.trim(); if (!v) return;
      try { await api('POST', '/api/devsahayak/repos', {repo: v}); await load(); settings(); } catch (e) { toast(e.message, true); } });
    EL.querySelectorAll('[data-rmrepo]').forEach(b => b.addEventListener('click', async () => { if (!confirm(`Remove ${b.dataset.rmrepo}? Nothing changes on GitHub.`)) return;
      const [o, n] = b.dataset.rmrepo.split('/'); try { await api('DELETE', `/api/devsahayak/repos/${encodeURIComponent(o)}/${encodeURIComponent(n)}`); await load(); settings(); } catch (e) { toast(e.message, true); } }));
    const save = async b => { try { OV.settings = await api('PUT', '/api/devsahayak/settings', b); toast('Saved.'); } catch (e) { toast(e.message, true); } };
    EL.querySelectorAll('[data-sw]').forEach(c => c.addEventListener('change', () => save({[c.dataset.sw]: c.checked})));
    EL.querySelectorAll('[data-set]').forEach(c => c.addEventListener('change', () => save({[c.dataset.set]: c.type === 'number' ? +c.value : c.value})));
  }

  return {open, leave};
};
