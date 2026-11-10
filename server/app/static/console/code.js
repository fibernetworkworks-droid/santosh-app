/* v0.748 HOOLA CODE - Developer Sahayak as a console page (owner: "a design same like Claude Code" -> the 6-screen canvas -> "GO").

   One page, its own sessions sidebar:
     home      what should Hoola code + repo / kind -> Start (POST /tasks/start: the work runs in the background)
     session   her ask, Hoola's words, every step as it happens (read / search / edit + diff / tests pass-fail / her notes),
               Stop, a box to tell Hoola something while it works; a big job's plan waits here for Yes / change / cancel;
               when done: why, the diff, proof, CI, own review, the PR, Open PR (her tap), Merge card (her tap), Ask for a change
     reviews   review a teammate's PR -> draft comments -> post as Comment / Request changes / Approve (her tap)
     settings  GitHub token (typed only here), repos, switches, limits, her rules
   Nothing reaches GitHub from this page except through the existing tap routes (push / plan-ok / post / decide). */
window.HoolaCode = function ({api, esc, toast}) {
  let EL = null, VIEW = 'home', TID = '', OV = null, TASK = null, POLL = 0, KIND = 'fix', REPO = '', MERGE = null;
  const $ = s => EL && EL.querySelector(s);
  const KINDS = [['fix', 'Fix a bug'], ['write', 'Build a feature'], ['tests', 'Write tests'], ['docs', 'Write docs'], ['explain', 'Explain code']];
  const STATUS = {new: 'Starting', plan_wait: 'Plan waits for your OK', ready: 'Ready - open the PR?', pr_open: 'PR open', ci_running: 'CI running',
    checks_failed: 'CI failed', merged: 'Merged', closed: 'PR closed', explained: 'Explained', refused: 'Stopped by a safety rule',
    failed: 'Could not finish', cancelled: 'Stopped'};
  const NEEDS = new Set(['plan_wait', 'ready', 'checks_failed', 'refused']);
  const ICON = {
    read: '<path d="M6 3h9l4 4v14H6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    search: '<circle cx="11" cy="11" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16 16l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    edit: '<path d="M4 20l4-1 11-11-3-3L5 16z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    new: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    list: '<path d="M4 6h16M4 12h10M4 18h7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    ok: '<path d="M5 12l5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>',
    bad: '<path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
    dot: '<circle cx="12" cy="12" r="3" fill="currentColor"/>'};
  const svg = (k, cls = '') => `<svg class="hcd-ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[k] || ICON.dot}</svg>`;
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const since = (a, b) => { const s = Math.max(0, Math.round((Date.parse(b || '') - Date.parse(a || '')) / 1000)); return isFinite(s) ? (s < 60 ? `0:${String(s).padStart(2, '0')}` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`) : ''; };
  const dur = s => { s = Math.round(+s || 0); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`; };
  const isRun = t => !!t.running;
  const group = t => isRun(t) ? 'run' : (NEEDS.has(t.status) || (OV?.actions || []).some(a => a.status === 'waiting' && a.repo === t.repo && a.pr_number === t.pr_number && t.pr_number)) ? 'need' : 'old';
  const dotc = t => ({run: 'run', need: 'warn'}[group(t)] || (t.status === 'merged' ? 'ok' : t.status === 'failed' ? 'bad' : 'soft'));

  async function load() {
    try { OV = await api('GET', '/api/devsahayak'); } catch (e) { OV = {error: e.message, tasks: [], repos: [], reviews: [], actions: [], settings: {}}; }
    if (!REPO) REPO = OV.settings?.default_repo || OV.repos?.[0]?.repo || '';
  }
  async function open(root) { EL = root || EL; if (!EL) return; clearInterval(POLL); await load(); show(VIEW, TID); }
  function leave() { clearInterval(POLL); }

  function show(view, tid) {
    VIEW = view; TID = tid || ''; clearInterval(POLL); MERGE = null;
    if (view === 'session' && TID) return session(TID);
    if (view === 'reviews') return reviews();
    if (view === 'settings') return settings();
    return home();
  }

  function sidebar() {
    const ts = OV?.tasks || [];
    const sec = (g, name) => { const list = ts.filter(t => group(t) === g); if (!list.length) return '';
      return `<p class="hcd-lbl">${name}</p>${list.slice(0, 12).map(t => `<button type="button" class="hcd-sess${t.id === TID ? ' on' : ''}" data-tid="${esc(t.id)}">
        <span class="hcd-st"><i class="hcd-dot ${dotc(t)}"></i>${esc(t.title || t.number)}</span>
        <small>${esc((t.repo || '').split('/')[1] || '')} · ${esc(isRun(t) ? 'working now' : (STATUS[t.status] || t.status))} · ${esc(ago(t.updated || t.at))}</small></button>`).join('')}`; };
    return `<nav class="hcd-side" aria-label="Coding sessions">
      <div class="hcd-sh"><b>Hoola Code</b><button type="button" class="hcd-btn sm" data-go="home">+ New</button></div>
      ${sec('run', 'Running')}${sec('need', 'Needs you')}${sec('old', 'Earlier')}
      ${ts.length ? '' : '<p class="hcd-mut" style="padding:8px 10px">No sessions yet.</p>'}
      <button type="button" class="hcd-sess" data-go="reviews"><span class="hcd-st">Review a teammate's PR</span></button>
      <button type="button" class="hcd-sess" data-go="settings"><span class="hcd-st">Repos, access and rules</span></button></nav>`;
  }
  function frame(inner) {
    EL.innerHTML = `<div class="hcd">${sidebar()}<div class="hcd-body">${inner}</div></div>`;
    EL.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => show(b.dataset.go)));
    EL.querySelectorAll('[data-tid]').forEach(b => b.addEventListener('click', () => show('session', b.dataset.tid)));
  }

  // ------------------------------------------------------------------ home ---
  function home() {
    const st = OV?.settings || {}, repos = OV?.repos || [];
    const setup = !st.github ? `<div class="hcd-block"><b>Connect GitHub first.</b> Add a fine-grained token and a repo in <button type="button" class="hcd-link" data-go="settings">Repos, access and rules</button>. The token is typed only there.</div>`
      : !repos.length ? `<div class="hcd-block"><b>Add a repo first</b> in <button type="button" class="hcd-link" data-go="settings">Repos, access and rules</button>.</div>` : '';
    frame(`<main class="hcd-home">
      ${OV?.error ? `<p class="hcd-err">${esc(OV.error)}</p>` : ''}
      <h1>What should Hoola code today?</h1>
      <p class="hcd-lede">Hoola reads your repo, makes the change on its own branch, runs your tests, and opens a pull request. Nothing is merged without you.</p>
      ${setup}
      <form class="hcd-ask" id="hcdAsk">
        <label for="hcdLine" class="hcd-sr">Describe the change</label>
        <textarea id="hcdLine" rows="4" maxlength="20000" placeholder="Describe the change, or paste the error and stack trace."></textarea>
        <div class="hcd-askrow">
          <label class="hcd-chip">Repo <select id="hcdRepo">${repos.map(r => `<option value="${esc(r.repo)}"${r.repo === REPO ? ' selected' : ''}>${esc(r.repo)}</option>`).join('') || '<option value="">no repo yet</option>'}</select></label>
          <label class="hcd-chip">Issue # <input id="hcdIssue" inputmode="numeric" maxlength="7" size="5"></label>
          <span class="hcd-flex"></span>
          <button class="hcd-btn pri" id="hcdStart" type="submit"${repos.length && st.github ? '' : ' disabled'}>Start</button>
        </div>
      </form>
      <div class="hcd-kinds" role="radiogroup" aria-label="What kind of work">${KINDS.map(([k, n]) => `<button type="button" role="radio" class="hcd-kind" aria-checked="${k === KIND}" data-kind="${k}">${n}</button>`).join('')}
        <button type="button" class="hcd-kind" data-go="reviews">Review a PR</button></div>
      <div class="hcd-facts"><div><b>Tests run for real</b>Your test command runs in a locked box with no internet and no keys, when the lab is on.</div>
        <div><b>Big jobs plan first</b>A large change shows its plan and waits for your OK before any file is touched.</div>
        <div><b>Your repo's rules</b>Hoola reads AGENTS.md, CLAUDE.md, CONTRIBUTING and your CI before it edits.</div></div>
    </main>`);
    EL.querySelectorAll('[data-kind]').forEach(b => b.addEventListener('click', () => { KIND = b.dataset.kind; EL.querySelectorAll('[data-kind]').forEach(x => x.setAttribute('aria-checked', String(x === b))); }));
    $('#hcdAsk').addEventListener('submit', async ev => {
      ev.preventDefault();
      const text = $('#hcdLine').value.trim(), btn = $('#hcdStart'); REPO = $('#hcdRepo').value;
      if (!text) return toast('Describe the change, or paste the error.', true);
      btn.disabled = true; btn.textContent = 'Starting…';
      try { const t = await api('POST', '/api/devsahayak/tasks/start', {kind: KIND, text, repo: REPO, issue: +$('#hcdIssue').value || 0}); await load(); show('session', t.id); }
      catch (e) { toast(e.message, true); btn.disabled = false; btn.textContent = 'Start'; }
    });
  }

  // ------------------------------------------------------------------ session ---
  function stepHTML(s, t0) {
    const at = `<span class="hcd-t">${esc(since(t0, s.at))}</span>`;
    const diff = rows => rows && rows.length ? `<pre class="hcd-diff">${rows.map(r => `<span class="${r.startsWith('+') ? 'add' : r.startsWith('-') ? 'del' : 'ctx'}">${esc(r)}</span>`).join('\n')}</pre>` : '';
    const p = x => `<code>${esc(x)}</code>`;
    switch (s.k) {
      case 'say': return `<p class="hcd-say">${esc(s.text)}</p>`;
      case 'note': return `<div class="hcd-me sm">${esc(s.text)}<small>told Hoola while it worked</small></div>`;
      case 'rules': return `<div class="hcd-step">${svg('list')}<span>Read the repo's rules · ${s.paths.map(p).join(', ')}</span>${at}</div>`;
      case 'read': return `<div class="hcd-step">${svg('read')}<span>Read ${p(s.path)}${s.lines && s.lines[0] ? ` · lines ${s.lines[0]}–${s.lines[1] || 'end'}` : ''}</span>${at}</div>`;
      case 'search': return `<div class="hcd-step">${svg('search')}<span>Searched ${p(s.q)} · ${s.n} file${s.n === 1 ? '' : 's'}</span>${at}</div>`;
      case 'list': return `<div class="hcd-step">${svg('list')}<span>Looked in folder ${p(s.path || '/')}</span>${at}</div>`;
      case 'usages': return `<div class="hcd-step">${svg('search')}<span>Found where ${p(s.name)} is used · ${s.n} place${s.n === 1 ? '' : 's'}</span>${at}</div>`;
      case 'edit': return `<div class="hcd-step">${svg('edit')}<span>Edited ${p(s.path)} <em class="add">+${s.added}</em> <em class="del">−${s.removed}</em></span>${at}</div>${diff(s.diff)}`;
      case 'new': return `<div class="hcd-step">${svg('new')}<span>Created ${p(s.path)} <em class="add">+${s.added}</em></span>${at}</div>${diff(s.diff)}`;
      case 'diff': return `<div class="hcd-step">${svg('read')}<span>Checked its own change · ${s.n} file${s.n === 1 ? '' : 's'}</span>${at}</div>`;
      case 'check': return `<div class="hcd-step ${s.ok ? 'ok' : 'bad'}">${svg(s.ok ? 'ok' : 'bad')}<span><b>Ran your tests</b>${s.only ? ` (${esc(s.only)})` : ''} · <span class="${s.ok ? 'add' : 'del'}">${s.ok ? 'passed' : 'failed'}</span>${s.seconds ? ` · ${esc(String(s.seconds))} s` : ''}${s.cmd ? ` · ${p(s.cmd)}` : ''}</span>${at}</div>${s.tail && s.tail.length ? `<pre class="hcd-diff">${s.tail.map(x => `<span class="${/fail|error|assert/i.test(x) ? 'del' : 'ctx'}">${esc(x)}</span>`).join('\n')}</pre>` : ''}`;
      case 'check_off': return `<div class="hcd-step">${svg('bad')}<span>Your tests could not run here - this change is not measured</span>${at}</div>`;
      case 'grep': return `<div class="hcd-step">${svg('search')}<span>Searched the test log for ${p(s.q)}</span>${at}</div>`;
      case 'refused': return `<div class="hcd-step dim">${svg('bad')}<span>A step was refused: ${esc(s.why)}</span>${at}</div>`;
      case 'stopped': return `<div class="hcd-step bad">${svg('bad')}<span><b>Stopped.</b> Nothing was pushed.</span>${at}</div>`;
      default: return '';
    }
  }
  const PROOF = {proven: ['ok', 'Bug proven: your CI failed the test first'], proven_local: ['ok', 'Bug proven: the test failed before the fix'],
    proven_unnamed: ['ok', 'Your CI went red on the test first'], not_proven: ['warn', 'The test passed on the old code - it does not prove the bug'],
    not_proven_local: ['warn', 'The test passed on the old code - it does not prove the bug'], still_failing: ['bad', 'Your tests still fail after the fix'],
    checked_local: ['ok', 'Your tests passed'], check_failed_local: ['bad', 'Your tests failed'], wait: ['run', 'Waiting for your CI']};
  const CI = {success: ['ok', 'Passed'], failure: ['bad', 'Failed'], pending: ['run', 'Running'], none: ['soft', 'No CI']};

  function checksHTML(t) {
    const rows = [];
    const pf = PROOF[t.proof?.state]; if (pf) rows.push([pf[0], 'Proof', pf[1]]);
    const ci = CI[t.ci?.state]; if (t.pr_number && ci) rows.push([ci[0], 'Your CI on GitHub', ci[1] + (t.rounds ? ` · round ${t.rounds}` : '')]);
    if (t.self_review?.verdict) rows.push([t.self_review.verdict === 'ok' ? 'ok' : 'warn', "Hoola's own review", t.self_review.verdict === 'ok' ? 'Clean' : `${(t.self_review.problems || []).length} point(s) left open`]);
    rows.push([(t.checks || []).length ? 'warn' : 'ok', 'Security and data checks', (t.checks || []).length ? `${t.checks.length} note(s)` : 'Clean']);
    return rows.map(([k, a, b]) => `<div class="hcd-row"><span>${a}</span><b class="hcd-c ${k}">${esc(b)}</b></div>`).join('');
  }

  async function session(tid) {
    await refreshTask(tid, true);
    POLL = setInterval(() => { if (VIEW === 'session' && TID === tid && (TASK?.running || ['ci_running', 'new'].includes(TASK?.status))) refreshTask(tid, false); }, 2000);
  }
  async function refreshTask(tid, first) {
    let t; try { t = await api('GET', `/api/devsahayak/tasks/${encodeURIComponent(tid)}`); } catch (e) { toast(e.message, true); return show('home'); }
    const was = TASK && TASK.id === tid ? TASK : null; TASK = t;
    if (!first && was && was.steps?.length === t.steps?.length && was.status === t.status && was.running === t.running && was.ci?.state === t.ci?.state) {
      const c = $('#hcdClock'); if (c && t.running) c.textContent = `Working · ${dur((Date.now() - Date.parse(t.at)) / 1000)}`; return;
    }
    if (was && was.running && !t.running) await load();
    if (t.pr_number && !t.running && !MERGE) {
      MERGE = (OV?.actions || []).find(a => a.kind === 'merge' && a.status === 'waiting' && a.repo === t.repo && a.pr_number === t.pr_number) || null;
    }
    drawSession();
  }

  function drawSession() {
    const t = TASK, steps = t.steps || [], scroll = $('#hcdFeed');
    const atBottom = !scroll || scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 80;
    const head = t.running ? `<span class="hcd-live" id="hcdClock">${t.stopping ? 'Stopping after this step' : `Working · ${dur((Date.now() - Date.parse(t.at)) / 1000)}`}</span><button type="button" class="hcd-btn" id="hcdStop"${t.stopping ? ' disabled' : ''}>Stop</button>`
      : `<span class="hcd-pill ${dotc(t)}">${esc(STATUS[t.status] || t.status)}</span>`;
    const plan = t.status === 'plan_wait' && t.plan ? planHTML(t) : '';
    const done = !t.running && t.status !== 'plan_wait' ? doneHTML(t) : '';
    const files = t.files || [];
    frame(`<div class="hcd-sess-wrap"><main class="hcd-main">
      <header class="hcd-top"><b>${esc(t.title || t.number)}</b><code class="hcd-br">${esc(t.repo)}${t.branch ? ' · ' + esc(t.branch) : ''}</code><span class="hcd-flex"></span>${head}</header>
      <div class="hcd-feed" id="hcdFeed"><div class="hcd-col">
        <div class="hcd-me">${esc(t.text || '')}</div>
        ${steps.length ? steps.map(s => stepHTML(s, t.at)).join('') : (t.running ? '<p class="hcd-mut">Reading the repo…</p>' : '')}
        ${t.running && !t.stopping ? `<div class="hcd-step dim"><span class="hcd-spin" aria-hidden="true"></span><span>Working on the next step…</span><span></span></div>` : ''}
        ${plan}${done}
      </div></div>
      ${t.running ? `<form class="hcd-steer" id="hcdSteer"><label for="hcdNote" class="hcd-sr">Tell Hoola something while it works</label>
        <input id="hcdNote" maxlength="2000" placeholder="Tell Hoola something while it works - it reads it before its next step"><button class="hcd-btn pri" type="submit">Send</button></form>` : ''}
    </main>
    <aside class="hcd-aside" aria-label="Changes and checks">
      <h2>Changes</h2>${files.length ? files.map(f => `<div class="hcd-file"><code>${esc(f.path)}</code><span><em class="add">+${f.added || 0}</em> <em class="del">−${f.removed || 0}</em></span></div>`).join('')
        : (() => { const ed = {}; steps.forEach(s => { if (s.k === 'edit' || s.k === 'new') { ed[s.path] = ed[s.path] || [0, 0]; ed[s.path][0] += s.added || 0; ed[s.path][1] += s.removed || 0; } });
            const ks = Object.keys(ed); return ks.length ? ks.map(k => `<div class="hcd-file"><code>${esc(k)}</code><span><em class="add">+${ed[k][0]}</em> <em class="del">−${ed[k][1]}</em></span></div>`).join('') : '<p class="hcd-mut">No changes yet.</p>'; })()}
      <h2>Checks</h2>${checksHTML(t)}
      ${t.running ? '<h2>What happens next</h2><p class="hcd-mut">A pull request opens on the hoola/ branch. Your CI runs; if it fails, Hoola fixes it. Merging is your tap.</p>' : ''}
    </aside></div>`);
    const f = $('#hcdFeed'); if (f && (atBottom || !scroll)) f.scrollTop = f.scrollHeight;
    wireSession();
  }

  function planHTML(t) {
    const pl = t.plan || {};
    const li = xs => (xs || []).map(x => `<li>${esc(typeof x === 'string' ? x : `${x.path || ''}${x.why ? ' - ' + x.why : ''}`)}</li>`).join('');
    return `<section class="hcd-card" aria-labelledby="hcdPlanH"><div class="hcd-sh"><h2 id="hcdPlanH">The plan</h2><span class="hcd-pill warn">${esc(t.tier || 'large')} job · waits for your OK</span></div>
      ${pl.goal ? `<p><b>Goal:</b> ${esc(pl.goal)}</p>` : ''}
      ${pl.files?.length ? `<h3>Files it will change</h3><ul class="mono">${li(pl.files)}</ul>` : ''}
      ${pl.steps?.length ? `<h3>Steps</h3><ol>${li(pl.steps)}</ol>` : ''}
      ${pl.done_when?.length ? `<h3>Done when</h3><ul>${li(pl.done_when)}</ul>` : ''}
      ${pl.risk ? `<div class="hcd-risk"><h3>Risks</h3><p>${esc(String(pl.risk))}</p></div>` : ''}
      <div class="hcd-acts"><button type="button" class="hcd-btn pri" id="hcdYes">Yes, start</button>
        <input id="hcdPlanNote" maxlength="1500" placeholder="Or change it - your note rides along with the plan">
        <button type="button" class="hcd-btn" id="hcdPlanChange">Send change</button><button type="button" class="hcd-btn" id="hcdCancel">Cancel job</button></div>
      <p class="hcd-mut">Nothing is touched until you say yes.</p></section>`;
  }

  function doneHTML(t) {
    const parts = [];
    if (t.error && ['failed', 'refused'].includes(t.status)) parts.push(`<div class="hcd-block bad"><b>${t.status === 'refused' ? 'A safety rule stopped this change.' : 'It could not finish.'}</b> ${esc(t.error)}</div>`);
    if (t.explain) parts.push(`<div class="hcd-say">${esc(t.explain)}</div>`);
    if (t.diff) parts.push(`<details class="hcd-fulldiff"${t.files?.length <= 3 ? ' open' : ''}><summary>The full change · ${t.files.length} file(s)</summary><pre class="hcd-diff">${String(t.diff).split('\n').map(r => `<span class="${/^\+(?!\+\+)/.test(r) ? 'add' : /^-(?!--)/.test(r) ? 'del' : 'ctx'}">${esc(r)}</span>`).join('\n')}</pre></details>`);
    if (t.risk) parts.push(`<p class="hcd-mut"><b>Risk:</b> ${esc(t.risk)}</p>`);
    const acts = [];
    if (t.status === 'ready' && t.hash) acts.push(`<button type="button" class="hcd-btn pri" id="hcdPush">Open the pull request</button>`);
    if (t.pr_url) acts.push(`<a class="hcd-btn" href="${esc(t.pr_url)}" target="_blank" rel="noopener noreferrer">PR #${t.pr_number} on GitHub</a>`);
    if (t.status === 'checks_failed') acts.push(`<button type="button" class="hcd-btn" id="hcdFixCi">Fix the CI failure</button>`);
    if (['pr_open', 'checks_failed'].includes(t.status) && t.pr_number && !MERGE) acts.push(`<button type="button" class="hcd-btn" id="hcdMergeReq">Ask to merge</button>`);
    if (['pr_open', 'checks_failed', 'ci_running'].includes(t.status)) acts.push(`<button type="button" class="hcd-btn" id="hcdRefresh">Check CI again</button>`);
    if (acts.length) parts.push(`<div class="hcd-acts">${acts.join('')}</div>`);
    if (MERGE) parts.push(mergeHTML(MERGE));
    if (['pr_open', 'checks_failed', 'ready', 'refused'].includes(t.status)) parts.push(`<form class="hcd-steer inline" id="hcdRevise"><label for="hcdRev" class="hcd-sr">Ask for a change</label>
      <input id="hcdRev" maxlength="4000" placeholder="Ask for a change - Hoola adds a new commit to the same pull request"><button class="hcd-btn" type="submit">Send</button></form>`);
    return parts.join('');
  }

  function mergeHTML(a) {
    return `<section class="hcd-card" aria-labelledby="hcdMergeH"><h2 id="hcdMergeH">Merge PR #${a.pr_number} into ${esc(a.base)}?</h2>
      <p class="hcd-mut">${esc(a.method)} merge of commit <code>${esc(a.head_sha)}</code> · CI ${esc((CI[a.ci_state] || ['', a.ci_state])[1])}. If anything is pushed after this card, it goes stale and asks again.</p>
      ${(a.notes || []).map(n => `<p class="hcd-mut">${esc(n)}</p>`).join('')}
      ${a.needs_force ? '<label class="hcd-f"><span>CI is not green - write why you still want to merge (8+ characters)</span><input id="hcdForce" maxlength="300"></label>' : ''}
      <div class="hcd-acts"><button type="button" class="hcd-btn ok" id="hcdMergeYes">Merge</button><button type="button" class="hcd-btn" id="hcdMergeNo">Not now</button></div></section>`;
  }

  function wireSession() {
    const t = TASK, id = encodeURIComponent(t.id);
    const busy = async (btn, fn) => { if (btn) btn.disabled = true; try { await fn(); } catch (e) { toast(e.message, true); if (btn) btn.disabled = false; } };
    const watch = async () => { await load(); await refreshTask(t.id, true); clearInterval(POLL); session(t.id); };
    $('#hcdStop')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/tasks/${id}/stop`); await refreshTask(t.id, true); }));
    $('#hcdSteer')?.addEventListener('submit', async ev => { ev.preventDefault(); const v = $('#hcdNote').value.trim(); if (!v) return;
      try { await api('POST', `/api/devsahayak/tasks/${id}/note`, {text: v}); $('#hcdNote').value = ''; toast('Hoola reads it before its next step.'); } catch (e) { toast(e.message, true); } });
    $('#hcdYes')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/tasks/${id}/bg/plan_ok`, {hash: t.hash}); await watch(); }));
    $('#hcdPlanChange')?.addEventListener('click', e => busy(e.target, async () => { const n = $('#hcdPlanNote').value.trim(); if (!n) throw new Error('Write what to change.');
      await api('POST', `/api/devsahayak/tasks/${id}/bg/plan_ok`, {hash: t.hash, note: n}); await watch(); }));
    $('#hcdCancel')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/tasks/${id}/cancel`); await load(); await refreshTask(t.id, true); }));
    $('#hcdPush')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/tasks/${id}/push`, {hash: t.hash}); await load(); await refreshTask(t.id, true); }));
    $('#hcdFixCi')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/tasks/${id}/bg/fix_ci`); await watch(); }));
    $('#hcdRefresh')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/tasks/${id}/refresh`); await load(); MERGE = null; await refreshTask(t.id, true); }));
    $('#hcdMergeReq')?.addEventListener('click', e => busy(e.target, async () => { MERGE = await api('POST', `/api/devsahayak/tasks/${id}/merge_request`, {}); await load(); drawSession(); }));
    $('#hcdMergeYes')?.addEventListener('click', e => busy(e.target, async () => {
      const r = await api('POST', `/api/devsahayak/actions/${encodeURIComponent(MERGE.id)}/decide`, {yes: true, hash: MERGE.hash, force_reason: $('#hcdForce')?.value || ''});
      toast(r.say || 'Merged.'); MERGE = null; await load(); await refreshTask(t.id, true); }));
    $('#hcdMergeNo')?.addEventListener('click', e => busy(e.target, async () => { await api('POST', `/api/devsahayak/actions/${encodeURIComponent(MERGE.id)}/decide`, {yes: false, hash: MERGE.hash}); MERGE = null; await load(); drawSession(); }));
    $('#hcdRevise')?.addEventListener('submit', async ev => { ev.preventDefault(); const v = $('#hcdRev').value.trim(); if (!v) return;
      try { await api('POST', `/api/devsahayak/tasks/${id}/bg/revise`, {text: v}); await watch(); } catch (e) { toast(e.message, true); } });
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
    const sw = (k, label, sub) => `<label class="hcd-tg"><span>${label}<small>${sub}</small></span><input type="checkbox" data-sw="${k}"${st[k] ? ' checked' : ''}></label>`;
    frame(`<main class="hcd-page"><h1>Repos, access and rules</h1><div class="hcd-grid">
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
    const save = async body => { try { OV.settings = await api('PUT', '/api/devsahayak/settings', body); toast('Saved.'); } catch (e) { toast(e.message, true); } };
    EL.querySelectorAll('[data-sw]').forEach(c => c.addEventListener('change', () => save({[c.dataset.sw]: c.checked})));
    EL.querySelectorAll('[data-set]').forEach(c => c.addEventListener('change', () => save({[c.dataset.set]: c.type === 'number' ? +c.value : c.value})));
  }

  return {open, leave};
};
