/* v0.999.169 PAYROLL DESK - the Payroll employee's own section, built the same way as Books & Accounts (owner: "WE WILL WORK ON
   NEXT AI EMPLOYEE SAME WAY A PAYROLL" -> the design claude.ai/artifact/M5ukAtPfTjN89y7NzqT8pt -> "GO").
   The Payroll chat (its own conversation, kind 'payroll') beside the desk's pages: Today, People, Inputs, Run payroll,
   Payslips & pay, Dates & filings, Settings. Pages call /api/payroll/do/<part> on the business picked here. Every figure comes
   from her payroll. Approving a run is her tap on the hash of the run she saw; Hoola never pays anyone and never files; account
   numbers typed for a payment file are used for that file only. Routes: #/<page>[/<arg>]. */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  const APP = $('#sd');
  if (!TOKEN) { location.replace('/console/'); return; }

  async function api(method, path, body, opts) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (opts && opts.form) payload = opts.form;
    else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    if (opts && opts.blob) { if (!r.ok) throw new Error(`The server refused the request (${r.status})`); return r.blob(); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4600);
  }
  function save(name, blob) {
    const u = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 4000);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', pay: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    warn: '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['people', 'People'], ['inputs', 'Inputs'], ['run', 'Run payroll'], ['pay', 'Payslips & pay'],
    ['dates', 'Dates & filings'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me before pay day?', 'How much will this payroll cost?', 'Who is new this month?'],
    people: ['Add a new person', 'Who has no tax ID?', 'Who leaves this month?'],
    inputs: ['Read this timesheet', 'Whose hours are missing?', 'Why is this row waiting?'],
    run: ['Explain the changes from last month', 'Why did tax go up for this person?', 'Prepare this payroll'],
    pay: ['How much leaves the bank on pay day?', 'What goes to each authority?', 'Show me a payslip'],
    dates: ['What is due this month?', 'Which filings are overdue?', 'What did I file last?'],
    settings: ['Which rules still need a check?', 'Where do I check my country rates?', 'What will you never do?']};
  const SIZES = {solo: 'My own work (sole trader, freelancer)', business: 'My business with a team'};
  const LANGS = {en: 'English', hi: 'Hindi', mr: 'Marathi', es: 'Spanish', fr: 'French', de: 'German', pt: 'Portuguese'};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    people: null, inputs: null, run: null, rules: null, filings: null, team: null, boxes: null, setupPv: null, start: null, edit: ''};
  try { ST.side = localStorage.getItem('hoola.payroll.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.payroll.folded') === '1'; } catch {}

  const ws = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const cur = () => K().currency || (ws() && ws().currency) || '';
  const money = (v, c) => { const n = Number(v || 0); try { return new Intl.NumberFormat(undefined, {style: 'currency', currency: c || cur() || 'USD'}).format(n); } catch { return n.toFixed(2); } };
  async function pr(part, a) { return api('POST', `/api/payroll/do/${part}`, Object.assign({workspace: ws().id}, a || {})); }
  const can = x => ((ST.d && ST.d.can) || []).includes(x);
  const role = () => (ST.d && ST.d.role) || 'owner';
  let PICK = ''; try { PICK = localStorage.getItem('hoola.payroll.ws') || ''; } catch {}
  const deskUrl = () => '/api/payroll/desk' + (PICK ? '?workspace=' + enc(PICK) : '');
  const head = (t, s) => `<div><h1 class="sd-h">${esc(t)}</h1>${s ? `<p class="lead">${esc(s)}</p>` : ''}</div>`;
  const loading = '<section class="card"><p class="mut" style="margin:0">Reading your payroll…</p></section>';
  const kpi = (l, v, cls, sub) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${esc(v)}</div>${sub ? `<div class="bk-sub">${esc(sub)}</div>` : ''}</div>`;
  const STATUS = {none: ['', 'Not prepared'], draft: ['v', 'Waiting for your approval'], approved: ['warn', 'Approved · waiting for the bank'], paid: ['ok', 'Paid']};

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', deskUrl()); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.pay, '')}</div>
        <h1 class="sd-h">Payroll is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="prHire">Hire Payroll</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#prHire').onclick = async () => { try { await api('POST', '/api/employees/payroll_worldwide/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame(); readTab(); paintTabs(); showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 60000));
  }
  function readTab() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    ST.arg = decodeURIComponent(parts.slice(1).join('/') || '');
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today';
    if (!ws() && ST.tab !== 'settings') ST.tab = 'settings';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.pay, '')}</div>
          <div style="min-width:0"><div class="sd-name">Payroll</div><div class="sd-site" id="prSite"></div></div>
          <span id="prState"></span>
        </div>
        <div class="sd-acts">
          <label class="sr" for="prBiz">Business</label>
          <select class="in bk-biz hide-sm" id="prBiz"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Payroll chat">
          <div class="sd-chathead"><div class="t"><b>Payroll chat</b><span>Drop a timesheet · it never pays or files</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="mdFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="mdPick" multiple hidden accept=".csv,.xlsx,.xls,.tsv,.pdf,image/*,.txt">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Payroll desk" id="sdTabs"></nav>
          <div id="mdPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about pay, people or dates, or drop a timesheet…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#mdPick').click()});
    $('#mdPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.payroll.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`; foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.payroll.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/payroll/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#prBiz').addEventListener('change', async e => {
      PICK = e.target.value; try { localStorage.setItem('hoola.payroll.ws', PICK); } catch {}
      try { await api('PUT', '/api/payroll/workspace', {workspace: PICK}); } catch {}
      clearCache(); await refreshDesk(true); location.hash = '#/today'; toast('Switched business.');
    });
    $('#sdRefresh').addEventListener('click', () => { clearCache(); refreshDesk(true); });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#mdPage').addEventListener('click', onPageClick);
    $('#mdPage').addEventListener('submit', onSubmit);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#prState'); if (!el) return;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !ws() ? ['warn', 'Set up your business'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(role() === 'owner' ? (d.trust || 'Learning') : ((d.roles || {})[role()] || role()))}</span>`;
    const w = ws(), k = K();
    $('#prSite').textContent = w ? `${w.name} · ${k.country || (w.countries || []).join(', ')} · ${k.currency || w.currency}` : 'No business set up yet';
    const sel = $('#prBiz');
    sel.hidden = (d.businesses || []).length < 2;
    sel.innerHTML = (d.businesses || []).map(b => `<option value="${esc(b.id)}"${w && b.id === w.id ? ' selected' : ''}>${esc(b.name)}</option>`).join('');
  }
  function paintTabs() {
    const k = K(), w = (k.inputs || {}).waiting || 0, run = (k.run || {}).status;
    $('#sdTabs').innerHTML = TABS.map(([t, name]) => `<button type="button" role="tab" data-tab="${t}" aria-selected="${t === ST.tab}"${!ws() && t !== 'settings' ? ' disabled' : ''}>${esc(name)}${
      t === 'inputs' && w ? `<span class="n">${esc(w)}</span>` : t === 'run' && run === 'draft' ? '<span class="n">1</span>' : t === 'settings' && (k.rules_to_check || []).length ? `<span class="n">${esc(k.rules_to_check.length)}</span>` : ''}</button>`).join('');
  }
  function clearCache() { ST.people = ST.inputs = ST.run = ST.rules = ST.filings = ST.team = ST.boxes = ST.start = null; }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', deskUrl()); } catch { return; }
    stateLine(); paintTabs();
    if (repaint || ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  const PAGES = () => ({today: pToday, people: pPeople, inputs: pInputs, run: pRun, pay: pPay, dates: pDates, settings: pSettings});
  function showPage(keep) {
    const box = $('#mdPage'); if (!box) return;
    box.innerHTML = (PAGES()[ST.tab] || pToday)();
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
    load();
  }
  async function load() {
    if (!ws()) return;
    const t = ST.tab, per = K().period;
    try {
      if (t === 'people' && !ST.people) ST.people = (await pr('people')).employees || [];
      else if (t === 'inputs' && !ST.inputs) {
        const [i, b, p] = await Promise.all([pr('inputs', {period: per}), pr('mailboxes'), ST.people ? {employees: ST.people} : pr('people')]);
        ST.inputs = i; ST.boxes = b; ST.people = p.employees || [];
      } else if (t === 'run' && !ST.run) {
        ST.run = await pr('changes', {period: per}).then(c => ({changes: c})).catch(() => ({none: true}));
        if (!ST.run.none) ST.run.payments = await pr('payments', {period: per}).catch(() => null);
      } else if (t === 'pay' && !ST.run) {
        ST.run = await pr('changes', {period: lastPaid()}).then(c => ({changes: c})).catch(() => ({none: true}));
        if (!ST.run.none) ST.run.payments = await pr('payments', {period: lastPaid()}).catch(() => null);
      } else if (t === 'dates' && !ST.filings) ST.filings = await pr('filings', {year: new Date().getFullYear()}).catch(e => ({error: e.message}));
      else if (t === 'settings' && !ST.rules) {
        const [r, tm] = await Promise.all([pr('rules'), pr('team').catch(() => ({team: []}))]);
        ST.rules = r; ST.team = tm.team || [];
        const cc = r.country || (ws().countries || [])[0];
        if (cc) ST.start = await pr('starting_list', {country: cc}).catch(() => null);
      } else return;
    } catch (e) { toast(e.message, true); return; }
    if (ST.tab === t) $('#mdPage').innerHTML = PAGES()[t]();
  }
  const lastPaid = () => { const k = K(); return (k.run || {}).status && k.run.status !== 'none' ? k.period : ((k.last_run || {}).period || k.period); };

  function steps(st) {
    const k = K(), i = k.inputs || {}, order = ['none', 'draft', 'approved', 'paid'], n = order.indexOf(st || 'none');
    const s = [['Inputs', `${i.checked || 0} checked${i.waiting ? ' · ' + i.waiting + ' waiting' : ''}`, (i.checked || 0) > 0 && !i.waiting ? 'done' : 'now'],
      ['Check', n >= 1 ? 'prepared' : 'not prepared', n >= 1 ? 'done' : (i.checked ? 'now' : '')],
      ['Approve', n >= 2 ? 'approved' : 'your tap', n >= 2 ? 'done' : (n === 1 ? 'now' : '')],
      ['Pay file', n >= 2 ? 'ready' : 'for your bank', n >= 2 ? 'done' : ''],
      ['Paid', n >= 3 ? 'bank line found' : 'bank line', n >= 3 ? 'done' : (n === 2 ? 'now' : '')],
      ['Filed', 'your reference', '']];
    return `<div class="pr-steps">${s.map(([a, b, c]) => `<div class="pr-step ${c}"><b>${esc(a)}</b>${esc(b)}</div>`).join('')}</div>`;
  }
  function pToday() {
    if (ST.d.desk_error) return `<section class="md-alert">${svg(IC.warn)}<div><div class="t">The payroll could not be read</div><div class="s">${esc(ST.d.desk_error)}</div></div></section>`;
    const k = K(), run = k.run || {}, t = run.totals || (k.last_run || {}).totals || {};
    const needs = [];
    if (!k.rules_set) needs.push(['Set your country pay rules', 'From the country starting list, or your own rates with their source', 'warn', 'Rules', 'settings', 'Set up']);
    if ((k.rules_to_check || []).length) needs.push([`${k.rules_to_check.length} rule${k.rules_to_check.length > 1 ? 's' : ''} to check`, k.rules_to_check.slice(0, 3).join(' · '), 'warn', 'Check this', 'settings', 'Check']);
    if (!k.people) needs.push(['Add your people', 'Name, pay, start date - or move them over from the older payroll', 'v', 'People', 'people', 'Add']);
    (k.missing || []).slice(0, 3).forEach(m => needs.push([`${m.name}'s hours for ${k.period} are missing`, 'They come in from your sheet, payroll email or programs', 'warn', 'Waiting', 'inputs', 'See inputs']));
    if ((k.inputs || {}).waiting) needs.push([`${k.inputs.waiting} input${k.inputs.waiting > 1 ? 's' : ''} waiting for you`, 'A name that matches nobody, a date outside the period, too many hours', 'warn', 'Inputs', 'inputs', 'Look']);
    (k.no_tax_id || []).slice(0, 2).forEach(n => needs.push([`${n} has no tax ID yet`, 'Kept masked; needed on the return', '', 'People', 'people', 'Add it']));
    if (run.status === 'draft') needs.push([`${k.period} is ready for your approval`, `Net pay ${money((run.totals || {}).net)}`, 'v', 'Your tap', 'run', 'Look and approve']);
    (k.awaiting_paid || []).forEach(p => needs.push([`${p} approved - waiting for the bank line`, 'Paid shows when Bank & matching has it', 'warn', 'Not paid yet', 'pay', 'Payment file']));
    (k.overdue_filings || []).forEach(f => needs.push([`${f.filing} for ${f.for} is overdue`, `Was due ${f.due}`, 'bad', 'Overdue', 'dates', 'Record']));
    (k.filings_soon || []).filter(f => f.status !== 'overdue').slice(0, 3).forEach(f => needs.push([`${f.filing} for ${f.for}`, `Due ${f.due}`, 'warn', 'Due soon', 'dates', 'See']));
    const rows = needs.map(([a, s, c, p, go, b]) => `<tr><td><b>${esc(a)}</b><div class="mut" style="font-size:13px">${esc(s)}</div></td><td><span class="pill ${c}">${esc(p)}</span></td><td style="text-align:right"><button class="btn soft sm" type="button" data-go="${go}">${esc(b)}</button></td></tr>`).join('');
    return `${head(`Pay period ${k.period || ''}`, `${k.start || ''} to ${k.end || ''} · ${k.frequency || ''}. Hoola never pays anyone and never files - you do.`)}
      <div class="bk-4">${kpi('Next pay day', k.pay_day || '-')}${kpi('People', S(k.people || 0))}
        ${kpi(run.totals ? 'Cost this run' : 'Cost last run', t.cost !== undefined ? money(t.cost) : '-', '', t.net !== undefined ? `Net pay ${money(t.net)}` : 'Not prepared yet')}
        ${kpi('Needs you', S(needs.length), needs.length ? 'bk-wv' : 'ok')}</div>
      ${steps(run.status)}
      <section class="card tight"><div style="padding:12px 0 4px"><h2 class="md-h2" style="margin:0">Needs you</h2></div>
        ${rows ? `<div style="overflow-x:auto"><table class="tb"><tbody>${rows}</tbody></table></div>` : '<p class="mut" style="margin:6px 0 12px">Nothing needs you right now.</p>'}</section>`;
  }

  function personForm(p) {
    p = p || {};
    const kind = p.pay_kind || 'annual';
    return `<form class="card" data-form="person"><h2 class="md-h2">${p.id ? 'Change ' + esc(p.name) : 'Add a person'}</h2><div class="md-form">
      <div class="md-field"><label for="ppN">Name</label><input class="in" id="ppN" name="name" required value="${esc(p.name)}"${p.id ? ' readonly' : ''}></div>
      <div class="md-field"><label for="ppR">Job</label><input class="in" id="ppR" name="role" value="${esc(p.role)}"></div>
      <div class="md-field"><label for="ppK">Pay</label><select class="in" id="ppK" name="kind">${[['annual', 'Salary a year'], ['per_period', 'Pay each period'], ['hourly', 'Rate an hour']].map(([v, l]) => `<option value="${v}"${v === kind ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="md-field"><label for="ppA">Amount (${esc(cur())})</label><input class="in" id="ppA" name="amount" type="number" step="0.01" min="0" value="${esc(p.pay)}"${p.id ? '' : ' required'}></div>
      <div class="md-field"><label for="ppS">Start date</label><input class="in" id="ppS" name="start" type="date" value="${esc(p.start)}"></div>
      <div class="md-field"><label for="ppF">New pay from (for a change)</label><input class="in" id="ppF" name="from" type="date"></div>
      <div class="md-field"><label for="ppT">Tax ID</label><input class="in" id="ppT" name="tax_id" autocomplete="off" placeholder="${p.tax_id ? 'Kept as ' + esc(p.tax_id) : 'Kept masked'}"></div>
      <div class="md-field"><label for="ppE">Email (for the payslip)</label><input class="in" id="ppE" name="email" type="email" value="${esc(p.email)}"></div>
      <div class="md-field"><label for="ppL">Payslip language</label><select class="in" id="ppL" name="lang">${Object.entries(LANGS).map(([v, l]) => `<option value="${v}"${v === (p.lang || 'en') ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="md-field"><label for="ppP">Your bank's payee reference</label><input class="in" id="ppP" name="payee_ref" value="${esc(p.payee_ref)}" placeholder="The name you saved them under at your bank"></div>
      <div class="md-field"><label for="ppPT">Before-tax deduction (% of pay)</label><input class="in" id="ppPT" name="pre_tax_pct" type="number" step="0.01" min="0" value="${esc(p.pre_tax_pct)}"></div>
      <div class="md-field"><label for="ppH">Usual hours a period (hourly people)</label><input class="in" id="ppH" name="hours" type="number" step="0.25" min="0" value="${esc(p.hours)}"></div></div>
      <div class="md-acts"><span class="mut" style="font-size:12.5px">Bank account numbers are never kept here.</span><div style="display:flex;gap:8px">${p.id ? '<button class="btn soft" type="button" data-cancel="1">Cancel</button>' : ''}<button class="btn" type="submit">${p.id ? 'Save' : 'Add'}</button></div></div></form>`;
  }
  function pPeople() {
    if (!ST.people) return head('People') + loading;
    const active = ST.people.filter(p => !p.left), left = ST.people.filter(p => p.left);
    const pay = p => p.pay_kind === 'annual' ? `${money(p.pay)} a year` : p.pay_kind === 'hourly' ? `${money(p.pay)} an hour` : `${money(p.pay)} a period`;
    const row = p => `<tr><td><b>${esc(p.name)}</b>${p.role ? `<div class="mut" style="font-size:12.5px">${esc(p.role)}</div>` : ''}</td><td class="num">${esc(pay(p))}</td>
      <td class="mono">${esc(p.tax_id || '-')}</td><td>${esc(LANGS[p.lang] || 'English')}</td>
      <td>${p.left ? `<span class="pill">Left ${esc(p.left)}</span>` : p.start && p.start >= K().start ? `<span class="pill warn">Joined ${esc(p.start)}</span>` : '<span class="pill ok">Ready</span>'}</td>
      <td style="text-align:right;white-space:nowrap">${!p.left && can('employee') ? `<button class="btn soft sm" type="button" data-editp="${esc(p.id)}">Change</button> <button class="btn soft sm" type="button" data-leave="${esc(p.name)}">Leaves</button>` : ''}</td></tr>`;
    const editing = ST.edit && ST.people.find(p => p.id === ST.edit);
    const india = ((ws().countries || []).includes('IN') || K().country === 'IN');
    return `${head('People', 'Everyone you pay. Joiners and leavers are paid for the days they worked.')}
      <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Name</th><th class="num">Pay</th><th>Tax ID</th><th>Payslip</th><th>State</th><th></th></tr></thead>
        <tbody>${active.map(row).join('') || '<tr><td colspan="6" class="mut">No one yet.</td></tr>'}${left.map(row).join('')}</tbody></table></div></section>
      ${can('employee') ? personForm(editing || null) : ''}
      ${india && can('employee') ? `<section class="card"><h2 class="md-h2">From the older payroll</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Move your people over from the earlier India payroll. Their past payrolls stay readable there.</p><button class="btn soft" type="button" data-import="1">Move my people over</button></section>` : ''}`;
  }

  function pInputs() {
    if (!ST.inputs) return head('Inputs') + loading;
    const k = K(), b = ST.boxes || {}, i = ST.inputs, items = i.items.filter(x => x.status !== 'dropped');
    const opts = (ST.people || []).filter(p => !p.left).map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
    const vals = v => Object.entries(v || {}).map(([a, n]) => `${a.replace('_', ' ')} ${n}`).join(' · ');
    const rows = items.map(x => `<tr><td><b>${esc(x.person || x.name)}</b><div class="mut" style="font-size:12.5px">${esc(x.file || x.source)}${x.date ? ' · ' + esc(x.date) : ''}</div></td>
      <td>${esc(vals(x.values))}</td>
      <td>${x.status === 'checked' ? '<span class="pill ok">Checked</span>' : `<span class="pill warn">Waiting</span><div class="mut" style="font-size:12.5px;margin-top:4px">${esc((x.why || []).join('; '))}</div>`}</td>
      <td style="text-align:right;white-space:nowrap">${x.status === 'waiting' && can('input_match') ? `<label class="sr" for="m_${esc(x.id)}">Match to</label><select class="in sm" id="m_${esc(x.id)}"><option value="">Match to…</option>${opts}</select> <button class="btn soft sm" type="button" data-match="${esc(x.id)}">Match</button> ` : ''}${can('input_drop') && x.status !== 'dropped' ? `<button class="btn soft sm" type="button" data-drop="${esc(x.id)}">Drop</button>` : ''}</td></tr>`).join('');
    const sw = Object.entries(b.software || {}).map(([key, name]) => `<label class="md-check"><input type="checkbox" name="sw_${esc(key)}"${(b.ticked || []).includes(key) ? ' checked' : ''}> ${esc(name)}</label>`).join('');
    const mails = (b.boxes || []).map(a => `<div class="bk-kv"><span>${esc(a)}</span>${(b.attached || []).includes(a) ? `<span class="bk-pick"><span class="pill ok">Read for payroll</span><button class="btn soft sm" type="button" data-mdetach="${esc(a)}">Stop</button></span>` : `<button class="btn soft sm" type="button" data-mattach="${esc(a)}">Use for payroll</button>`}</div>`).join('');
    return `${head('Inputs', `Hours, overtime, bonus and leave for ${i.period}. Every row is checked: the name is one of your people, the date is in the period, hours stay under your limit, nothing is counted twice.`)}
      ${(k.missing || []).length ? `<section class="md-alert">${svg(IC.warn)}<div><div class="t">Hours missing</div><div class="s">${esc(k.missing.map(m => m.name).join(', '))}</div></div></section>` : ''}
      <section class="card tight"><div style="padding:12px 0 4px"><h2 class="md-h2" style="margin:0">This period</h2></div>
        <div style="overflow-x:auto"><table class="tb"><tbody>${rows || '<tr><td class="mut">Nothing came in yet.</td></tr>'}</tbody></table></div></section>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="sheet"><h2 class="md-h2">A sheet</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Your Google Sheet of hours, read every half hour. Columns: Name, Hours, and any of Date, Overtime hours, Bonus, Unpaid days, Leave days.</p>
          <div class="md-form"><div class="md-field wide"><label for="inSh">Sheet link</label><input class="in" id="inSh" name="spreadsheet" value="${esc((b.sheet || {}).spreadsheet)}"></div>
          <div class="md-field"><label for="inTb">Tab (optional)</label><input class="in" id="inTb" name="tab" value="${esc((b.sheet || {}).tab)}"></div></div>
          <div class="md-acts"><span class="mut" style="font-size:12.5px">Needs your Google account connected.</span><div style="display:flex;gap:8px">${(b.sheet || {}).spreadsheet ? '<button class="btn soft" type="button" data-sheetnow="1">Read now</button>' : ''}<button class="btn" type="submit">Save</button></div></div></form>
        <section class="card"><h2 class="md-h2">Payroll email</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Timesheets (CSV or Excel) mailed to an email you choose come in by themselves.</p>
          ${mails || '<p class="mut" style="margin:0">Connect an email in Hoola first (Gmail, Outlook or another).</p>'}</section>
        <form class="card" data-form="software"><h2 class="md-h2">Time or HR software</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Hoola uses only their read tools. Connect each one in Connectors first.</p>
          <div class="bk-checks">${sw}</div><div class="md-acts"><a class="btn soft sm" href="/console/?v=connectors">Connectors</a><div style="display:flex;gap:8px"><button class="btn soft" type="button" data-swnow="1">Read now</button><button class="btn" type="submit">Save</button></div></div></form>
        <section class="card"><h2 class="md-h2">Upload or your own system</h2>
          <form data-form="upload" class="bk-acc" style="grid-template-columns:minmax(0,1fr) auto"><label class="sr" for="inUp">Timesheet file</label><input class="in sm" id="inUp" name="file" type="file" accept=".csv,.xlsx,.xls,.tsv" required><button class="btn soft sm" type="submit">Read it</button></form>
          <div class="bk-kv" style="margin-top:10px"><span>Payroll key for your system ${b.api_on ? '<span class="pill ok">On</span>' : ''}</span><span class="bk-pick"><button class="btn soft sm" type="button" data-key="1">${b.api_on ? 'New key' : 'Make a key'}</button>${b.api_on ? '<button class="btn soft sm" type="button" data-keystop="1">Stop</button>' : ''}</span></div>
          <div id="inKey"></div></section></div>`;
  }

  function pRun() {
    const k = K(), run = k.run || {}, st = run.status || 'none', [pc, pn] = STATUS[st] || STATUS.none;
    const top = `${head(`Run payroll · ${k.period}`, 'Worked out from your people, your rules and the checked inputs. Look at what changed, then approve.')}
      <div class="bk-bar"><span class="pill ${pc}">${esc(pn)}</span><div style="display:flex;gap:8px;flex-wrap:wrap">${st !== 'approved' && st !== 'paid' && can('prepare') ? `<button class="btn ${st === 'none' ? '' : 'soft'}" type="button" data-prepare="1">${st === 'none' ? 'Prepare this payroll' : 'Prepare again'}</button>` : ''}</div></div>`;
    if (!ST.run) return top + loading;
    if (ST.run.none || st === 'none') return top + `<section class="card"><p class="mut" style="margin:0">Not prepared yet. ${(k.missing || []).length ? 'Some hours are still missing - you can prepare now and again when they arrive.' : ''}</p></section>`;
    const c = ST.run.changes, pay = ST.run.payments || {};
    const rows = c.people.map(p => `<tr><td><b>${esc(p.name)}</b></td><td class="num">${money(p.gross)}</td><td class="num">${money(p.net)}</td>
      <td class="num">${p.diff === null || p.diff === undefined ? '-' : (p.diff > 0 ? '+' : '') + money(p.diff)}</td><td>${(p.why || []).map(w => `<span class="pill v">${esc(w)}</span>`).join(' ') || '<span class="mut">same as before</span>'}</td></tr>`).join('');
    const t = run.totals || {};
    const approve = st === 'draft' && can('approve') ? `<section class="card"><h2 class="md-h2">Approve</h2>
      <p style="margin:0 0 10px">Net pay ${money(t.net)} · to the authorities ${money(Object.values(pay.to_authorities || {}).reduce((a, b) => a + b, 0))} · your cost ${money(t.cost)}.</p>
      <p class="mut" style="margin:0 0 12px;font-size:13px">Approving locks ${esc(k.period)} for good and puts the wage journal in Books &amp; Accounts.${K().approve_limit ? ` Above ${money(K().approve_limit)} net, someone other than the person who prepared it approves.` : ''} Hoola still pays no one.</p>
      <button class="btn" type="button" data-approve="${esc(run.hash)}">Approve this payroll</button></section>` : '';
    return `${top}<div class="bk-4">${kpi('Gross pay', money(t.gross))}${kpi('Income tax', money(t.tax))}${kpi('Contributions', money((t.ee || 0) + (t.er || 0)), '', `${money(t.ee)} from pay · ${money(t.er)} on top`)}${kpi('Net pay', money(t.net))}</div>
      ${(c.gone || []).length ? `<section class="md-alert">${svg(IC.warn)}<div><div class="t">Not paid this period</div><div class="s">${esc(c.gone.map(g => g.name).join(', '))}</div></div></section>` : ''}
      <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Person</th><th class="num">Gross</th><th class="num">Net</th><th class="num">Change</th><th>Why${c.before ? ' (against ' + esc(c.before) + ')' : ''}</th></tr></thead><tbody>${rows}</tbody></table></div></section>
      ${approve}`;
  }

  function pPay() {
    const k = K(), per = lastPaid(), fl = per === k.period ? (k.run || {}) : (k.last_run || {});
    const st = fl.status || 'none', [pc, pn] = STATUS[st] || STATUS.none;
    const top = head(`Payslips & pay · ${per || ''}`, 'The file for your bank, the payslips and the wage journal. You pay; Hoola marks Paid when the bank line arrives.');
    if (st !== 'approved' && st !== 'paid') return top + `<section class="card"><p class="mut" style="margin:0">Approve the payroll first (Run payroll). The payment file and payslips are made from an approved payroll.</p></section>`;
    if (!ST.run) return top + loading;
    const people = (ST.run.changes || {}).people || [];
    const slips = people.map(p => `<div class="bk-kv"><span>${esc(p.name)} <span class="mut">· ${money(p.net)}</span></span><button class="btn soft sm" type="button" data-slip="${esc(p.id)}">Payslip PDF</button></div>`).join('');
    const ibans = people.map((p, n) => `<div class="md-field"><label for="ib${n}">${esc(p.name)} - IBAN</label><input class="in" id="ib${n}" name="ib_${esc(p.id)}" autocomplete="off"></div>`).join('');
    return `${top}<div class="bk-bar"><span class="pill ${pc}">${esc(pn)}</span>${st === 'approved' ? '<button class="btn soft sm" type="button" data-paidnow="1">Check the bank now</button>' : ''}</div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Payment file</h2>
          <div class="bk-kv"><span>Your bank's bulk CSV<div class="mut" style="font-size:12.5px">Names, your payee references, amounts</div></span><button class="btn soft sm" type="button" data-csv="1">Download</button></div>
          <details style="margin-top:10px"><summary>ISO 20022 file (pain.001)</summary>
            <form data-form="pain" style="margin-top:10px"><div class="md-form"><div class="md-field wide"><label for="ibFrom">Account you pay from - IBAN</label><input class="in" id="ibFrom" name="from" autocomplete="off" required></div>${ibans}</div>
              <div class="md-acts"><span class="mut" style="font-size:12.5px">Account numbers are used for this one file and never kept.</span><button class="btn" type="submit">Make the file</button></div></form></details>
          ${(ST.run.payments || {}).to_authorities ? `<h3 class="pr-h3">To the authorities</h3>${Object.entries(ST.run.payments.to_authorities).map(([n, v]) => `<div class="bk-kv"><span>${esc(n)}</span><span class="num">${money(v)}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">Payslips</h2>${slips}
          ${can('payslip_drafts') ? '<div class="md-acts"><span class="mut" style="font-size:12.5px">Each in the person\'s language. You send them from your mailbox.</span><button class="btn" type="button" data-drafts="1">Put payslip emails in my Drafts</button></div>' : ''}
          <div class="bk-kv" style="margin-top:12px"><span>Wage journal in Books &amp; Accounts</span>${fl.journal ? '<span class="pill ok">Posted</span>' : `<span class="bk-pick"><span class="pill warn">Not posted</span>${can('post_journal') ? '<button class="btn soft sm" type="button" data-journal="1">Post it</button>' : ''}</span>`}</div>
          ${fl.journal_why ? `<p class="mut" style="font-size:12.5px;margin:6px 0 0">${esc(fl.journal_why)}</p>` : ''}</section></div>`;
  }

  function pDates() {
    const f = ST.filings;
    const top = head('Dates & filings', 'Due dates from your own rules. You (or your adviser) file on the official service and type the reference here.');
    if (!f) return top + loading;
    if (f.error) return top + `<section class="card"><p class="mut" style="margin:0">${esc(f.error)}</p><button class="btn soft sm" type="button" data-go="settings" style="margin-top:10px">Set your filings</button></section>`;
    const rows = f.items.map((x, n) => `<tr><td><b>${esc(x.filing)}</b><div class="mut" style="font-size:12.5px">for ${esc(x.for)}</div></td><td>${esc(x.due)}</td>
      <td>${x.status === 'done' ? `<span class="pill ok">Done · ${esc((x.done || {}).reference || '')}</span>` : x.status === 'overdue' ? '<span class="pill bad">Overdue</span>' : '<span class="pill">Upcoming</span>'}</td>
      <td style="text-align:right">${x.status !== 'done' && can('done') ? `<form data-form="done" data-filing="${esc(x.filing)}" data-for="${esc(x.for)}" class="bk-pick"><label class="sr" for="rf${n}">Reference</label><input class="in sm" id="rf${n}" name="reference" placeholder="Reference" required><button class="btn soft sm" type="submit">I filed it</button></form>` : ''}</td></tr>`).join('');
    return `${top}<section class="card tight"><div style="overflow-x:auto"><table class="tb"><tbody>${rows || '<tr><td class="mut">No filings set.</td></tr>'}</tbody></table></div></section>`;
  }

  function setupForm() {
    return `<form class="card" data-form="setup"><h2 class="md-h2">Set up your business</h2>
      <p class="mut" style="margin:0 0 12px;font-size:14px">The same business as Books &amp; Accounts. Payroll is kept for each business apart.</p><div class="md-form">
        <div class="md-field"><label for="pfSN">Business name</label><input class="in" id="pfSN" name="name" required></div>
        <div class="md-field"><label for="pfSZ">Who it is for</label><select class="in" id="pfSZ" name="size">${Object.entries(SIZES).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="pfSC">Country (two letters, e.g. GB)</label><input class="in" id="pfSC" name="country" maxlength="2" pattern="[A-Za-z]{2}" required></div>
        <div class="md-field"><label for="pfSK">Currency (three letters, e.g. GBP)</label><input class="in" id="pfSK" name="currency" maxlength="3" pattern="[A-Za-z]{3}"></div></div>
      ${ST.setupPv ? `<div class="bk-pv"><b>What turns on</b><ul>${(ST.setupPv.lines || []).map(l => `<li>${esc(l)}</li>`).join('')}</ul></div>` : ''}
      <div class="md-acts"><span class="mut" style="font-size:12.5px">${ST.setupPv ? 'Look it over, then confirm.' : 'You see what turns on before anything is made.'}</span>
        ${ST.setupPv ? '<div style="display:flex;gap:8px"><button class="btn soft" type="button" data-setupcancel="1">Change</button><button class="btn" type="button" data-setupok="1">Confirm</button></div>' : '<button class="btn" type="submit">Show me</button>'}</div></form>`;
  }
  function ruleText(r) {
    const x = r.rule || {};
    if (r.key === 'income_tax') return x.method === 'none' ? 'Not taken from pay here' : `${x.method}${x.allowance ? ', allowance ' + x.allowance : ''}${(x.bands || []).length ? ', bands ' + x.bands.map(b => `${b.pct}% to ${b.upto === null ? 'any' : b.upto}`).join(' / ') : ''}${x.flat_pct ? ', ' + x.flat_pct + '%' : ''}`;
    if (x.slabs) return 'Fixed amounts: ' + x.slabs.map(s => `${s.employee} up to ${s.upto === null ? 'any' : s.upto}`).join(', ');
    return [x.employee_pct ? `${x.employee_pct}% from pay` : '', x.employer_pct ? `${x.employer_pct}% on top` : '', x.from ? `from ${x.from}` : '', x.upto ? `up to ${x.upto}` : '', x.only_upto ? `only when pay is up to ${x.only_upto}` : ''].filter(Boolean).join(', ');
  }
  function pSettings() {
    const w = ws();
    if (!w) return head('Set up payroll', 'Tell Hoola which business this payroll is for.') + setupForm();
    if (!ST.rules) return head('Settings') + loading;
    const R = ST.rules, sl = ST.start, cc = R.country || (w.countries || [])[0] || '';
    const rows = R.rules.map((r, n) => `<div class="pr-rule"><div><b>${esc(r.name)}</b> ${r.status === 'checked' ? '<span class="pill ok">Checked</span>' : '<span class="pill warn">Check this</span>'}
        <div class="mut" style="font-size:13px">${esc(ruleText(r))}</div>${r.note ? `<div class="mut" style="font-size:12.5px">${esc(r.note)}</div>` : ''}
        ${r.status === 'checked' ? `<div class="mut" style="font-size:12.5px">${esc([r.source, r.checked_on, r.by].filter(Boolean).join(' · '))}</div>` : ''}</div>
      ${r.status !== 'checked' && can('check_rule') ? `<form data-form="check" data-key="${esc(r.key)}" class="bk-pick"><label class="sr" for="rs${n}">Where you checked it</label><input class="in sm" id="rs${n}" name="source" placeholder="Official page you checked" required><button class="btn soft sm" type="submit">Checked</button></form>` : ''}</div>`).join('');
    const team = (ST.team || []).filter(m => m.active).map(m => `<div class="bk-kv"><span>${esc(m.name || m.email)}</span><span class="pill">${esc((ST.d.roles || {})[m.role] || m.role)}</span></div>`).join('');
    return `${head('Settings', 'Your pay rules, each with where it comes from. A rule from a starting list is used only after someone checked it.')}
      <section class="card"><h2 class="md-h2">Country rules · ${esc(cc || 'not set')}</h2>
        ${R.where ? `<p class="mut" style="margin:0 0 10px;font-size:13px">Check at: ${esc(R.where)}</p>` : ''}
        ${rows || `<p class="mut" style="margin:0 0 10px">No rules yet.</p>`}
        ${can('apply_starting_list') && sl && sl.list ? `<div class="md-acts"><span class="mut" style="font-size:12.5px">${esc(sl.says)}</span><button class="btn ${rows ? 'soft' : ''}" type="button" data-startlist="${esc(cc)}">${rows ? 'Start again from the' : 'Use the'} ${esc(cc)} starting list</button></div>` : sl && !sl.list ? `<p class="mut" style="font-size:13px;margin:10px 0 0">${esc(sl.says)} Ask in the chat to put your own rates in.</p>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="desk"><h2 class="md-h2">Pay calendar and limits</h2><div class="md-form">
          <div class="md-field"><label for="dsPD">Pay day (day of the month)</label><input class="in" id="dsPD" name="pay_day" type="number" min="1" max="31" value="${esc(R.pay_day || '')}"></div>
          <div class="md-field"><label for="dsMH">Most hours one person in a period</label><input class="in" id="dsMH" name="max_hours" type="number" min="1" step="1" placeholder="${R.frequency === 'weekly' ? 65 : R.frequency === 'fortnightly' ? 130 : 260}"></div>
          <div class="md-field"><label for="dsOX">Overtime rate (x hourly pay)</label><input class="in" id="dsOX" name="overtime_x" type="number" min="1" step="0.05" placeholder="1.5"></div>
          <div class="md-field"><label for="dsAL">A second person approves above (net, ${esc(cur())}; 0 = never)</label><input class="in" id="dsAL" name="approve_limit" type="number" min="0" step="0.01" value="${esc(K().approve_limit || 0)}"></div></div>
          <div class="md-acts"><span class="mut" style="font-size:12.5px">Paid ${esc(R.frequency)}.</span><button class="btn" type="submit">Save</button></div></form>
        <section class="card"><h2 class="md-h2">Team</h2><p class="mut" style="margin:0 0 10px;font-size:14px">The Books &amp; Accounts team works here too. Accountant prepares, Approver approves, Auditor and Viewer read.</p>
          ${team || '<p class="mut" style="margin:0 0 10px">Only you so far.</p>'}<a class="btn soft sm" href="/console/books#/settings">Change the team in Books &amp; Accounts</a></section></div>
      ${setupForm().replace('Set up your business', 'Add another business')}`;
  }

  /* ---------------------------------------------------------------- page actions */
  async function onPageClick(e) {
    const t = e.target.closest('button,a'); if (!t || t.tagName === 'A') return;
    const ds = t.dataset;
    try {
      if (ds.go) { location.hash = '#/' + ds.go; return; }
      if (ds.editp) { ST.edit = ds.editp; showPage(true); $('#ppA') && $('#ppA').focus(); return; }
      if (ds.cancel) { ST.edit = ''; showPage(true); return; }
      if (ds.leave) { await pr('employee', {name: ds.leave, leave: true, left_on: new Date().toISOString().slice(0, 10)}); ST.people = null; toast(`${ds.leave} marked as leaving today. Their last pay is for the days they worked.`); await refreshDesk(false); showPage(true); return; }
      if (ds.import) { const r = await pr('import_old'); ST.people = null; toast(r.says); await refreshDesk(false); showPage(true); return; }
      if (ds.match) { const v = $('#m_' + ds.match).value; if (!v) { toast('Pick the person first.', true); return; } await pr('input_match', {item: ds.match, person: v}); ST.inputs = null; await refreshDesk(false); showPage(true); return; }
      if (ds.drop) { await pr('input_drop', {item: ds.drop}); ST.inputs = null; await refreshDesk(false); showPage(true); return; }
      if (ds.mattach) { const r = await pr('mail_attach', {address: ds.mattach}); ST.inputs = null; toast(r.says); showPage(true); return; }
      if (ds.mdetach) { await pr('mail_detach', {address: ds.mdetach}); ST.inputs = null; showPage(true); return; }
      if (ds.sheetnow) { t.disabled = true; const r = await pr('sheet_read'); ST.inputs = null; toast(r.says); await refreshDesk(false); showPage(true); return; }
      if (ds.swnow) { t.disabled = true; const r = await pr('software_read'); ST.inputs = null; toast(r.says || 'Read.'); await refreshDesk(false); showPage(true); return; }
      if (ds.key) { const r = await pr('api_key'); ST.boxes = null; $('#inKey').innerHTML = `<div class="bk-pv"><b>Copy it now</b><div class="mono" style="word-break:break-all;margin:6px 0">${esc(r.key)}</div><div class="mut">POST ${esc(location.origin + r.url)} · ${esc(r.header)}</div><div class="mono" style="font-size:12px;margin-top:6px">${esc(r.body)}</div></div>`; return; }
      if (ds.keystop) { await pr('api_stop'); ST.inputs = null; showPage(true); return; }
      if (ds.prepare) { t.disabled = true; await pr('prepare', {period: K().period}); ST.run = null; await refreshDesk(false); toast('Prepared. Look at the changes, then approve.'); showPage(true); return; }
      if (ds.approve) { t.disabled = true; const r = await pr('approve', {period: K().period, hash: ds.approve}); ST.run = null; await refreshDesk(false); toast(r.says); location.hash = '#/pay'; return; }
      if (ds.csv) { const r = await pr('pay_file', {period: lastPaid(), format: 'csv'}); save(r.name, new Blob([r.text], {type: r.mime})); toast(r.says); return; }
      if (ds.slip) { const b = await api('GET', `/api/payroll/payslip?workspace=${enc(ws().id)}&period=${enc(lastPaid())}&employee=${enc(ds.slip)}`, undefined, {blob: true}); save(`payslip-${lastPaid()}-${ds.slip}.pdf`, b); return; }
      if (ds.drafts) { t.disabled = true; const r = await pr('payslip_drafts', {period: lastPaid()}); toast(r.says); t.disabled = false; return; }
      if (ds.journal) { const r = await pr('post_journal', {period: lastPaid()}); toast(r.posted ? 'The wage journal is in your books.' : (r.why || 'Not posted.'), !r.posted); await refreshDesk(true); return; }
      if (ds.paidnow) { const r = await pr('paid_check', {period: lastPaid()}); const x = (r.runs || [])[0]; toast(x && x.paid ? 'Paid - the bank line is in.' : 'No matching bank line yet.'); await refreshDesk(true); return; }
      if (ds.startlist) { t.disabled = true; const r = await pr('apply_starting_list', {country: ds.startlist}); ST.rules = null; toast(r.says); await refreshDesk(true); return; }
      if (ds.setupcancel) { ST.setupPv = null; showPage(true); return; }
      if (ds.setupok) {
        t.disabled = true;
        const r = await api('POST', '/api/fin/setup/apply', {answers: ST.setupPv.answers, hash: ST.setupPv.hash});
        const id = r.id || (r.workspace && r.workspace.id);
        ST.setupPv = null;
        if (id) { PICK = id; try { localStorage.setItem('hoola.payroll.ws', id); } catch {} await api('PUT', '/api/payroll/workspace', {workspace: id}); }
        clearCache(); await refreshDesk(false); toast('Your business is ready. Now set your pay rules.'); location.hash = '#/settings'; showPage(); return;
      }
    } catch (err) { toast(err.message, true); t.disabled = false; }
  }
  async function onSubmit(e) {
    const f = e.target.closest('form[data-form]'); if (!f) return;
    e.preventDefault();
    const kind = f.dataset.form, fd = new FormData(f), v = k => S(fd.get(k)).trim();
    const btn = e.submitter || f.querySelector('button[type=submit]'); if (btn) btn.disabled = true;
    try {
      if (kind === 'person') {
        const a = {name: v('name'), role: v('role'), start: v('start') || undefined, email: v('email'), lang: v('lang'), payee_ref: v('payee_ref')};
        if (v('amount')) a[v('kind')] = Number(v('amount'));
        if (v('from')) a.from = v('from');
        if (v('tax_id')) a.tax_id = v('tax_id');
        if (v('pre_tax_pct')) a.pre_tax_pct = Number(v('pre_tax_pct'));
        if (v('hours')) a.hours = Number(v('hours'));
        await pr('employee', a); ST.people = null; ST.edit = ''; toast(`${a.name} saved.`); await refreshDesk(false); showPage(true); return;
      }
      if (kind === 'sheet') { await pr('desk_settings', {sheet: {spreadsheet: v('spreadsheet'), tab: v('tab')}}); ST.inputs = null; toast('Saved. Hoola reads it every half hour.'); showPage(true); return; }
      if (kind === 'software') { const keys = Object.keys((ST.boxes || {}).software || {}).filter(k => fd.get('sw_' + k)); await pr('desk_settings', {software: keys}); ST.inputs = null; toast('Saved.'); showPage(true); return; }
      if (kind === 'upload') {
        const file = fd.get('file'); if (!file || !file.size) throw new Error('Choose the file.');
        if (file.size > 10 * 1024 * 1024) throw new Error('The file is over 10 MB.');
        const buf = new Uint8Array(await file.arrayBuffer()); let bin = ''; for (let i = 0; i < buf.length; i += 32768) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
        const r = await pr('upload', {name: file.name, data_b64: btoa(bin)}); ST.inputs = null; toast(r.says); await refreshDesk(false); showPage(true); return;
      }
      if (kind === 'pain') {
        const people = ((ST.run || {}).changes || {}).people || [], accounts = {};
        people.forEach(p => { accounts[p.id] = {iban: v('ib_' + p.id)}; });
        const r = await pr('pay_file', {period: lastPaid(), format: 'pain001', from: {iban: v('from')}, accounts});
        f.reset(); save(r.name, new Blob([r.text], {type: r.mime})); toast(r.says); return;
      }
      if (kind === 'done') { await pr('done', {filing: f.dataset.filing, for: f.dataset.for, reference: v('reference')}); ST.filings = null; toast('Recorded as you filed it.'); await refreshDesk(false); showPage(true); return; }
      if (kind === 'check') { const r = await pr('check_rule', {key: f.dataset.key, source: v('source')}); ST.rules = null; toast(r.left ? `${r.left} still to check.` : 'Every rule is checked. The payroll can run.'); await refreshDesk(true); return; }
      if (kind === 'desk') {
        const a = {}; ['pay_day', 'max_hours', 'overtime_x', 'approve_limit'].forEach(k => { if (v(k) !== '') a[k] = v(k); });
        await pr('desk_settings', a); ST.rules = null; toast('Saved.'); await refreshDesk(true); return;
      }
      if (kind === 'setup') {
        ST.setupPv = await api('POST', '/api/fin/setup/preview', {answers: {size: v('size'), countries: [v('country').toUpperCase()], currency: v('currency').toUpperCase(), name: v('name'), wants: ['payroll']}});
        const vals = {}; f.querySelectorAll('input[id],select[id]').forEach(x => { vals[x.id] = x.value; });
        showPage(true); Object.entries(vals).forEach(([id, val]) => { const x = document.getElementById(id); if (x) x.value = val; }); return;
      }
    } catch (err) { toast(err.message, true); }
    finally { if (btn) btn.disabled = false; }
  }

  /* ---------------------------------------------------------------- files in the chat */
  function addFiles(list) {
    for (const f of list) {
      if (ST.files.length >= MAXF) { toast(`Up to ${MAXF} files in one message.`, true); break; }
      if (f.size > MAXB) { toast(`${f.name} is over 30 MB.`, true); continue; }
      const item = {name: f.name || 'file', id: '', state: 'up', key: Math.random().toString(36).slice(2)};
      ST.files.push(item); paintFiles();
      (async () => {
        try {
          if (!ST.chat) throw new Error('The chat is not open yet.');
          const fd = new FormData(); fd.append('file', f, f.name || 'file');
          const r = await api('POST', `/api/conversations/${enc(ST.chat)}/files`, undefined, {form: fd});
          item.id = S(r.file_id || r.id); item.state = item.id ? 'ok' : 'bad';
        } catch (e) { item.state = 'bad'; item.err = e.message; toast(`${item.name}: ${e.message}`, true); }
        paintFiles();
      })();
    }
    if (ST.folded) $('#sdFold').click();
  }
  function paintFiles() {
    const box = $('#mdFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/payroll/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    box.innerHTML = (STARTERS[ST.tab] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-q]'); if (b) send(b.dataset.q); };
  }
  function merge(rows) {
    if (!ST.rows.length || !rows.length) { if (rows.length || !ST.rows.length) ST.rows = rows; return; }
    const got = new Set(rows.map(r => r.id)), have = new Map(ST.rows.map(r => [r.id, r]));
    if (ST.rows.some(r => r.id >= rows[0].id && !got.has(r.id))) { ST.rows = rows; return; }
    const max = ST.rows[ST.rows.length - 1].id;
    for (const r of rows) { if (r.id > max) ST.rows.push(r); else if (have.has(r.id)) have.get(r.id).text = r.text; }
  }
  const lastIsHers = () => { const l = ST.rows[ST.rows.length - 1]; return !!l && l.role === 'user'; };
  const stripHints = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  async function loadMsgs(first) {
    if (!ST.chat || ST.loading || !ST.thread) return;
    const chat = ST.chat; ST.loading = true;
    try {
      const ask = async () => { const seq = ST.seq; let r = null;
        try { r = await api('GET', `/api/conversations/${enc(chat)}/result`); } catch {}
        if (seq === ST.seq) ST.res = r; };
      if (!first && (ST.sending || ST.working || lastIsHers() || (ST.res && ST.res.needs_you))) await ask();
      let rows;
      try { rows = (await api('GET', `/api/conversations/${enc(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      if (chat !== ST.chat) return;
      merge(rows);
      if (first && lastIsHers()) await ask();
      paintThread();
    } finally { ST.loading = false; }
  }
  function paintThread() {
    if (!ST.thread) return;
    const st = ST.res ? S(ST.res.status) : null;
    const working = ST.sending || (st === null ? lastIsHers() : st === 'working' || st === 'queued');
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Working…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text),
      files: r.role === 'user' && Array.isArray(r.files) ? r.files : undefined}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) { clearCache(); refreshDesk(true); }
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Read these timesheets into this period' : 'Read this timesheet into this period';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(text, {pending: true, files: names});
    ST.files = []; paintFiles(); paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text, files, client_id: 'pr' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
    catch (e) { ok = false; toast(e.message, true); mine.remove(); if (ST.bar) ST.bar.value = text; ST.files = ready; paintFiles(); }
    ST.sending = false;
    if (ok) { ST.seq++; ST.res = {status: 'queued', needs_you: false, line: ''}; await loadMsgs(false); }
    paintThread();
  }
  async function stopTurn() {
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/stop`); toast('Stopping.'); }
    catch (e) { toast(e.message, true); }
  }

  start();
})();
