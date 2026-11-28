/* v0.999.176 TAX DESK - the Tax (worldwide) employee's own section, like Payroll and Books & Accounts (owner: "GO" on the design
   claude.ai/artifact/Faegn7ZmcGkTQqdkqRtZ1v).
   A thin top bar, then the Tax chat (its own conversation, kind 'tax': she asks about a return or drops a tax letter) beside the
   desk's pages: Today, Returns, Across borders, Letters, Personal, Dates & settings. The pages call /api/tax/do/<part>, which
   runs the F4 engine on the business she picked. A rate is used only once a person checks it; a date read from a letter is a
   reminder only once she confirms it; "I filed it" is her tap with the reference and locks the period on this desk.
   Hoola prepares the figures. She or her accountant file and pay. Routes: #/<page>[/<arg>]. */
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
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', tax: '<path d="M6 3h9l3 3v15H6z"/><path d="M9 10h6M9 14h6M9 18h3"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const CC = {GB: 'United Kingdom', US: 'United States', IN: 'India', AE: 'United Arab Emirates', SG: 'Singapore', AU: 'Australia',
    CA: 'Canada', IE: 'Ireland', DE: 'Germany', SA: 'Saudi Arabia', FR: 'France', IT: 'Italy', ES: 'Spain', NL: 'Netherlands'};
  const TABS = [['today', 'Today'], ['returns', 'Returns'], ['borders', 'Across borders'], ['letters', 'Letters'], ['personal', 'Personal'], ['settings', 'Dates & settings']];
  const KINDNAME = {rates: 'Your rates', state_rates: 'US state sales tax rates', oss_rates: 'EU country rates (One Stop Shop)', nexus: 'US state sales limits'};
  const CODES = ['std', 'reduced', 'super_reduced', 'zero', 'exempt', 'export', 'eu_goods', 'rc_out', 'rc_in', 'oss', 'outside'];
  const STARTERS = {
    today: ['What is due next?', 'How much VAT do I owe this quarter?', 'Explain my next return'],
    returns: ['Why is this box lower than last time?', 'Which bills are left out?', 'Explain each box'],
    borders: ['Do I need to register for sales tax in America?', 'What do I owe under the One Stop Shop?', 'Make an e-invoice'],
    letters: ['What does this letter ask?', 'Make the reply firmer', 'Which letter is most urgent?'],
    personal: ['What papers am I still missing?', 'What counts as income?', 'Estimate my next payment'],
    settings: ['Add my corporation tax date', 'Which rates still need checking?', 'Why are rates checked by a person?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], ret: null, retFor: '',
    bord: null, bordFor: '', letters: null, letter: null, pers: null, rates: null, cal: 0};
  try { ST.side = localStorage.getItem('hoola.tax.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.tax.folded') === '1'; } catch {}

  const cname = cc => CC[cc] || cc || '';
  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const T = () => K().tax || {};
  const money = (v, cur) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: cur || 'USD', minimumFractionDigits: 2}); } catch { return n.toFixed(2); }
  };
  const cur = () => (W() && W().currency) || 'USD';
  const can = () => !!(ST.d && ST.d.can_write);
  const pname = p => { const m = /^(\d{4})-Q([1-4])$/.exec(S(p)); if (m) return `${['Jan–Mar', 'Apr–Jun', 'Jul–Sep', 'Oct–Dec'][m[2] - 1]} ${m[1]}`;
    const n = /^(\d{4})-(\d{2})$/.exec(S(p)); return n ? new Date(+n[1], +n[2] - 1, 1).toLocaleString(undefined, {month: 'long', year: 'numeric'}) : S(p); };
  const run = (part, a) => api('POST', '/api/tax/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/tax/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.tax, '')}</div>
        <h1 class="sd-h">Your Tax employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="txHire">Hire Tax</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#txHire').onclick = async () => { try { await api('POST', '/api/employees/tax_worldwide/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame();
    readTab();
    paintTabs();
    showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 60000));
  }
  function readTab() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    ST.arg = decodeURIComponent(parts.slice(1).join('/') || '');
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.tax, '')}</div>
          <div style="min-width:0"><div class="sd-name">Tax</div><div class="sd-site" id="txSite"></div></div>
          <span id="txState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="txBiz" aria-label="Business" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Tax chat">
          <div class="sd-chathead"><div class="t"><b>Tax chat</b><span>Ask about a return, or drop a tax letter here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="txFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="txPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.eml,.csv,.xlsx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Tax desk" id="sdTabs"></nav>
          <div id="txPage"></div>
          <p class="tx-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola prepares the figures. You or your accountant file and pay.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your tax…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#txPick').click()});
    $('#txPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.tax.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.tax.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/tax/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#txBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/tax/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#txPage').addEventListener('click', onPageClick);
    $('#txPage').addEventListener('submit', onSubmit);
    $('#txPage').addEventListener('change', onChange);
    window.addEventListener('hashchange', () => { ST.keepT = null; readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function clearCache() { ST.ret = null; ST.retFor = ''; ST.bord = null; ST.bordFor = ''; ST.letters = null; ST.letter = null; ST.pers = null; ST.rates = null; }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#txState'); if (!el) return;
    const k = K(), w = W();
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your business'] : !k.set ? ['warn', 'Add your tax details'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const t = T();
    $('#txSite').textContent = w ? `${w.name} · ${t.country ? cname(t.country) : 'no country yet'}${t.period_kind ? ' · ' + t.period_kind : ''}${d.role && d.role !== 'owner' ? ' · you are ' + (d.roles[d.role] || d.role) : ''}` : 'No business yet';
    const sel = $('#txBiz');
    sel.innerHTML = (d.businesses || []).map(b => `<option value="${esc(b.id)}"${w && b.id === w.id ? ' selected' : ''}>${esc(b.name)}</option>`).join('');
    sel.hidden = (d.businesses || []).length < 2;
  }
  function paintTabs() {
    const k = K();
    const n = {letters: (k.letters_waiting || []).length, settings: (k.rates_to_check || []).length};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/tax/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { clearCache(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  // what she is still typing in other boxes survives a save that redraws the page; a form just sent starts clean
  function keepTyping(box) {
    const out = [], act = document.activeElement, now = Date.now();
    box.querySelectorAll('form[data-form]').forEach(f => {
      if (f.dataset.sent && now - Number(f.dataset.sent) < 30000) return;
      f.querySelectorAll('input[name], textarea[name], select[name]').forEach(el => {
        if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'file' || el.type === 'hidden') return;
        const typed = el.tagName === 'SELECT' ? [...el.options].some(o => o.selected !== o.defaultSelected) : el.value !== el.defaultValue;
        if (typed) out.push({f: f.dataset.form, n: el.name, v: el.value, focus: el === act, s: el.selectionStart, e: el.selectionEnd});
      });
    });
    return out;
  }
  function putTyping(box, kept) {   // returns what could not go back yet (the page is still loading)
    const later = [];
    kept.forEach(k => {
      const el = box.querySelector(`form[data-form="${k.f}"] [name="${k.n}"]`); if (!el) { later.push(k); return; }
      el.value = k.v;
      if (k.focus) { el.focus(); try { if (k.s != null) el.setSelectionRange(k.s, k.e); } catch (_) {} }
    });
    return later.length ? later : null;
  }
  function showPage(keep) {
    const box = $('#txPage'); if (!box) return;
    if (!W()) { box.innerHTML = noBiz(); starters(); return; }
    const fn = {today: pToday, returns: pReturns, borders: pBorders, letters: pLetters, personal: pPersonal, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    if (typeof html === 'string') { const kept = keepTyping(box).concat(ST.keepT || []); box.innerHTML = html; ST.keepT = putTyping(box, kept); }
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  function noBiz() {
    return `<div><h1 class="sd-h">Set up your business first</h1><p class="lead">The Tax desk works on the books of a business in Books & Accounts. Make one there (name, country, currency), then come back.</p></div>
      <div><a class="btn" href="/console/books">Open Books & Accounts</a></div>`;
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }

  function pToday() {
    const k = K(), r = k.return || {}, nd = k.next_due;
    const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
    const toPay = r.blocked ? '—' : esc(money(r.to_pay, r.currency || cur()));
    const setup = !k.set ? `<section class="md-alert">${svg(IC.info)}<div><div class="t">Tell Hoola your tax details</div><div class="s">Your country, tax number and how often you file. Then your dates and returns appear here.</div></div><button class="btn sm" type="button" data-go="settings">Add them</button></section>` : '';
    const needs = (k.needs || []).map(x => `<div class="tx-row"><span class="tx-dot"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go + (x.n ? '/' + x.n : ''))}">Open</button></div>`).join('');
    const soon = (k.coming_up || []).map(x => `<div class="tx-row"><span style="flex:1">${esc(x.what)}</span><span class="mut">${esc(x.due)}</span>${x.from ? `<span class="pill">${esc(fromSay(x.from))}</span>` : ''}</div>`).join('');
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${nd ? `Your next tax date is ${esc(nd.what)} on ${esc(nd.due)}.` : 'No tax date is coming up.'}</p></div>
      ${setup}
      <div class="md-3 tx-4">
        ${kpi('Next due', nd ? esc(nd.due) : '—', nd ? nd.what : 'Add your due rule in Dates & settings')}
        ${kpi(`To pay · ${pname(k.period)}`, toPay, r.blocked ? r.say : r.filed ? `Filed · ${r.filed.reference}` : 'From your own books', r.blocked ? '' : '')}
        ${kpi('Letters waiting', esc((k.letters_waiting || []).length), (k.letters_waiting || []).length ? 'Need a reply' : 'Nothing to answer')}
        ${kpi('Rates to check', esc((k.rates_to_check || []).length), (k.rates_to_check || []).length ? 'Not used until checked' : 'Every rate checked', (k.rates_to_check || []).length ? 'bad' : 'ok')}
      </div>
      <div class="md-2">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needs || '<p class="mut" style="margin:0">Nothing needs you right now.</p>'}</section>
        <section class="card"><h2 class="md-h2">Coming up</h2>${soon || '<p class="mut" style="margin:0">No dates yet. Add your due rule or a date in Dates & settings.</p>'}</section>
      </div>`;
  }
  const fromSay = f => ({'your rule': 'From your VAT period', 'her letter': 'From the letter', you: 'From your words'}[f] || f);

  function pReturns() {
    const k = K(), p = ST.arg || k.period, list = (k.periods || []).includes(p) ? k.periods : [p, ...(k.periods || [])];
    if (ST.retFor !== p) { ST.retFor = p; ST.ret = null; run('return', {period: p}).then(r => { ST.ret = r; if (ST.tab === 'returns') showPage(true); }).catch(e => { ST.ret = {blocked: true, say: e.message}; if (ST.tab === 'returns') showPage(true); }); }
    const r = ST.ret;
    const pick = `<select class="in sm" data-period="1" aria-label="Period">${list.map(x => `<option value="${esc(x)}"${x === p ? ' selected' : ''}>${esc(pname(x))}</option>`).join('')}</select>`;
    const head = `<div class="tx-head"><h1 class="sd-h">${r && r.form ? esc(r.form.split(' (')[0]) : 'Return'} · ${esc(pname(p))}</h1>${r ? (r.filed ? '<span class="pill ok">Filed · locked</span>' : r.blocked ? '<span class="pill warn">Cannot work it out yet</span>' : '<span class="pill warn">Ready to check</span>') : ''}<span style="margin-left:auto">${pick}</span></div>`;
    if (!r) return head + loading();
    if (r.blocked) {
      return head + `<section class="md-alert">${svg(IC.info)}<div><div class="t">This return waits for you</div><div class="s">${esc(r.say)}</div></div>${(r.rates_to_check || []).length ? '<button class="btn sm" type="button" data-go="settings">Check the rates</button>' : ''}</section>`;
    }
    const c = r.currency;
    const rows = (r.boxes || []).map(b => `<tr><td><span class="tx-bx">${esc(b.box)}</span></td><td>${esc(b.label)}</td><td class="num">${esc(money(b.amount, c))}</td></tr>`).join('');
    const checks = (r.checks || []).map(x => `<div class="tx-ck"><span class="${x.ok ? 'ok' : 'wa'}">${x.ok ? '✓' : '!'}</span><span>${esc(x.say)}</span></div>`).join('');
    const filed = r.filed ? `<section class="card"><h2 class="md-h2">Filed</h2><p style="margin:0">Reference <b>${esc(r.filed.reference)}</b> · ${esc(r.filed.on)} by ${esc(r.filed.by)}</p><p class="mut" style="margin:6px 0 0;font-size:13px">This period is locked on this desk.</p></section>` :
      `<section class="card tx-acts">
        <button class="btn" type="button" data-dl="pdf">Download for filing (PDF)</button>
        <button class="btn soft" type="button" data-dl="csv">Download the figures (CSV)</button>
        ${ST.d.can_file ? `<form data-form="filed" class="tx-filed"><label class="mut" for="txRef" style="font-size:13px">After you file on the official site, add its reference</label>
          <div style="display:flex;gap:8px"><input class="in" id="txRef" name="reference" placeholder="Reference" required minlength="3"><button class="btn soft" type="submit">I filed it</button></div></form>` : ''}
        <span class="mut" style="font-size:13px">Hoola does not file or pay. When you have filed, tap “I filed it” with the reference, so the period locks.</span></section>`;
    return head + `<p class="mut" style="margin:0">Laid out like the ${esc(cname(r.country))} form. Every figure comes from your own books (${esc((r.documents || []).length)} sales and bills). ${esc(r.layout || '')}</p>
      <div class="tx-split">
        <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Box</th><th>What it is</th><th class="num">Amount</th></tr></thead><tbody>${rows}</tbody></table></div>
          ${r.rounding ? `<p class="mut" style="font-size:12.5px;margin:8px 0">${esc(r.rounding)}</p>` : ''}</section>
        <div class="tx-side">
          <section class="card"><div class="mut" style="font-size:13px">${r.to_reclaim ? 'To reclaim' : 'To pay'}</div><div class="tx-big">${esc(money(r.to_reclaim || r.to_pay, c))}</div></section>
          <section class="card"><h2 class="md-h2">Checks</h2>${checks}</section>
          ${filed}
        </div>
      </div>`;
  }

  function pBorders() {
    const k = K(), p = ST.arg || k.period;
    if (ST.bordFor !== p) { ST.bordFor = p; ST.bord = null; run('borders', {period: p}).then(r => { ST.bord = r; if (ST.tab === 'borders') showPage(true); }).catch(e => { ST.bord = {error: e.message}; if (ST.tab === 'borders') showPage(true); }); }
    const b = ST.bord;
    const head = `<div class="tx-head"><h1 class="sd-h">Selling across borders</h1></div>`;
    if (!b) return head + loading();
    if (b.error) return head + `<section class="card"><p style="margin:0">${esc(b.error)}</p></section>`;
    const nx = b.nexus || {}, oss = b.oss || {};
    const st = (nx.states || []).map(s => {
      const pct = s.pct, over = s.over, col = over ? 'var(--bad)' : pct >= 75 ? 'var(--warn)' : 'var(--acc)';
      const tag = s.threshold === undefined || s.threshold === null ? '<span class="pill">No limit set</span>'
        : `<span class="pill ${over ? 'bad' : pct >= 75 ? 'warn' : ''}">${over ? 'Over' : esc(pct) + '%'} · ${esc(money(s.sales_12m, 'USD'))}</span>${s.limit_checked ? '' : ' <span class="pill warn">check this</span>'}`;
      return `<div class="tx-st"><span>${esc(s.state)}</span><div class="md-bar"><div class="in" style="width:${Math.min(100, pct || 0)}%;background:${col}"></div></div><span class="num">${tag}</span></div>`;
    }).join('');
    const cc = (oss.countries || []).map(c => `<tr><td>${esc(cname(c.country))}${c.rate !== undefined && c.rate !== null && !c.rate_checked ? ' <span class="pill warn">rate: check this</span>' : ''}</td><td class="num">${c.rate === undefined || c.rate === null ? '—' : esc(c.rate) + '%'}</td><td class="num">${esc(money(c.net, oss.currency))}</td><td class="num">${c.tax_due === null ? esc(c.says || '—') : esc(money(c.tax_due, oss.currency))}</td></tr>`).join('');
    return head + `<div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">United States · sales by state <span class="mut" style="font-weight:400;font-size:13px">last 12 months · limits you entered</span></h2>
          ${st || `<p class="mut" style="margin:0">No US sales in your books.</p>`}
          <p class="mut" style="font-size:12.5px;margin:10px 0 0">${esc(nx.says || '')}</p></section>
        <section class="card tight"><h2 class="md-h2" style="padding-top:12px">EU · One Stop Shop <span class="mut" style="font-weight:400;font-size:13px">${esc(pname(p))}</span></h2>
          ${cc ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Country</th><th class="num">Rate</th><th class="num">Sales</th><th class="num">VAT</th></tr></thead><tbody>${cc}
            <tr><td><b>Total</b></td><td></td><td></td><td class="num"><b>${esc(money(oss.due_total, oss.currency))}</b></td></tr></tbody></table></div>` : `<p class="mut" style="margin:0 0 12px">${esc(oss.error || 'No sales to consumers in other countries this period.')}</p>`}
          ${(oss.warnings || []).map(w => `<p class="mut" style="font-size:12.5px;margin:6px 0">! ${esc(w)}</p>`).join('')}</section>
      </div>
      <div class="md-2">
        <section class="card"><h2 class="md-h2">Tax kept back on payments</h2><p class="mut" style="margin:0 0 10px;font-size:14px">When a client keeps part of your fee as tax, Hoola works it out from the rate you give and lists the certificates to ask for.</p>
          <button class="btn soft sm" type="button" data-ask="Work out the tax kept back on my payments">Work it out in the chat</button></section>
        <section class="card"><h2 class="md-h2">E-invoices</h2><p class="mut" style="margin:0 0 10px;font-size:14px">An invoice from your books as a Peppol / UBL file, checked before you send it through your provider.</p>
          <button class="btn soft sm" type="button" data-ask="Make an e-invoice from my last sale">Make one in the chat</button></section>
      </div>`;
  }

  function pLetters() {
    if (ST.letters === null) { ST.letters = []; run('letters').then(r => { ST.letters = r.letters || []; if (ST.tab === 'letters') showPage(true); }).catch(e => toast(e.message, true)); }
    const n = Number(ST.arg || (ST.letters[0] && ST.letters[0].n) || 0);
    if (n && (!ST.letter || ST.letter.n !== n)) { run('letter', {n}).then(r => { ST.letter = r.letter; if (ST.tab === 'letters') showPage(true); }).catch(() => {}); }
    const say = {needs_you: ['warn', 'Needs you'], read: ['', 'Read'], sent: ['', 'Reply sent'], done: ['ok', 'Done']};
    const list = ST.letters.map(x => `<button type="button" class="tx-li${x.n === n ? ' on' : ''}" data-go="letters/${x.n}"><b>${esc(x.asks && x.asks[0] ? cap(x.asks[0]) : x.name)}</b>
      <span class="mut">${esc(x.authority)} · ${esc(x.added.slice(0, 10))}${x.reply_by ? ' · reply by ' + esc(x.reply_by) : ''}</span><span class="pill ${say[x.state][0]}">${esc(say[x.state][1])}</span></button>`).join('');
    const add = can() ? `<form class="card" data-form="letter"><h2 class="md-h2">Add a letter</h2>
        <div class="md-field"><label for="txLt">Paste the words of the tax letter (or drop the letter in the chat)</label><textarea class="in" id="txLt" name="text" rows="4" required minlength="20"></textarea></div>
        <div class="md-acts"><input class="in" name="name" placeholder="Name it (optional)" style="max-width:260px"><button class="btn" type="submit">Read it</button></div></form>` : '';
    const x = ST.letter && ST.letter.n === n ? ST.letter : null;
    const view = !x ? (ST.letters.length ? loading() : `<section class="card"><p class="mut" style="margin:0">No letters yet. Paste one here or drop it in the chat.</p></section>`) : `
      <h1 class="sd-h">${esc(x.asks && x.asks[0] ? cap(x.asks[0]) : x.name)}</h1>
      <div class="md-3 tx-4">
        <div class="md-kpi"><div class="l">From</div><div class="v sm">${esc(x.authority)}</div></div>
        <div class="md-kpi"><div class="l">Amount asked</div><div class="v sm">${esc(x.amount || '—')}</div></div>
        <div class="md-kpi"><div class="l">Reply by</div><div class="v sm">${esc(x.reply_by || '—')}</div>${x.reply_by ? (x.date_confirmed ? '<span class="pill ok">Confirmed by you</span>' : `<span class="pill warn">Read from the letter · confirm</span>`) : ''}</div>
        <div class="md-kpi"><div class="l">Reference</div><div class="v sm">${esc(x.reference)}</div></div>
      </div>
      ${x.reply_by && !x.date_confirmed && can() ? `<form class="card tx-confirm" data-form="confirm"><span>Is the date in the letter <b>${esc(x.reply_by)}</b>? Check it, then confirm so it goes into your dates.</span>
        <input class="in" type="date" name="reply_by" value="${esc(x.reply_by)}"><button class="btn sm" type="submit">Confirm the date</button></form>` : ''}
      <section class="card"><h2 class="md-h2">What the letter asks</h2><p style="margin:0">${esc((x.asks || []).map(cap).join('; '))}</p>
        ${(x.dates || []).length ? `<p class="mut" style="font-size:13px;margin:6px 0 0">Dates in the letter: ${esc(x.dates.join(', '))}</p>` : ''}</section>
      <section class="card"><div style="display:flex;align-items:center;gap:8px"><h2 class="md-h2" style="margin:0">Draft reply</h2><span class="mut" style="margin-left:auto;font-size:13px">Fill the [blanks] - only facts you give Hoola</span></div>
        <pre class="md-letter tx-draft">${esc(x.draft).replace(/\[[^\]\n]{1,60}\]/g, m => `<span class="blank">${m}</span>`)}</pre>
        <div class="md-acts"><div style="display:flex;gap:8px"><button class="btn" type="button" data-copy="1">Copy the draft</button><button class="btn soft" type="button" data-ask="Change the reply to letter ${esc(x.reference)}">Change it in the chat</button></div>
          ${can() ? (x.state === 'sent' || x.state === 'done' ? `<button class="btn soft sm" type="button" data-lact="reopen">Open it again</button>` : `<button class="btn soft" type="button" data-lact="sent">I sent it</button>`) : ''}</div></section>`;
    return `<div class="tx-letters"><div class="tx-list">${list}${add}</div><div class="tx-view">${view}</div></div>`;
  }
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);

  function pPersonal() {
    if (ST.pers === null) { ST.pers = false; run('personal').then(r => { ST.pers = r; if (ST.tab === 'personal') showPage(true); }).catch(e => { ST.pers = {error: e.message}; if (ST.tab === 'personal') showPage(true); }); }
    const r = ST.pers;
    if (!r) return `<div><h1 class="sd-h">Your own tax</h1></div>` + loading();
    const c = r.currency || cur();
    const inc = Object.entries(r.income || {}).map(([k, v]) => `<div class="tx-row"><span style="flex:1">${esc(cap(k))}</span><span class="num">${esc(money(v, c))}</span></div>`).join('');
    const papers = (r.papers || []).map(p => `<label class="tx-row md-check"><input type="checkbox" data-paper="${esc(p.name)}"${p.have ? ' checked' : ''}${can() ? '' : ' disabled'}><span>${esc(p.name)}</span></label>`).join('');
    const missing = (r.papers || []).filter(p => !p.have).length;
    const est = r.estimate ? `<div class="tx-big">${esc(money(r.estimate.tax, c))}</div><p class="mut" style="margin:4px 0 0;font-size:13px">${esc(r.estimate.says)}</p>`
      : `<p class="mut" style="margin:0;font-size:14px">No estimate yet. Tell Hoola your tax bands and allowance in the chat, or ask your accountant.</p><div style="margin-top:10px"><button class="btn soft sm" type="button" data-ask="Estimate my next tax payment">Estimate in the chat</button></div>`;
    return `<div><h1 class="sd-h">Your own tax${r.since ? ` · ${esc(r.since)} – ${esc(r.upto)}` : ''}</h1>${r.error ? `<p class="lead">${esc(r.error)}</p>` : ''}</div>
      <div class="md-3">
        <section class="card"><h2 class="md-h2">Money in, from your statements</h2>${inc || '<p class="mut" style="margin:0">No statements read yet. Import them in Books & Accounts > Bank.</p>'}
          ${inc ? `<div class="tx-row" style="font-weight:600"><span style="flex:1">Total</span><span class="num">${esc(money(r.total_in, c))}</span></div>` : ''}</section>
        <section class="card"><h2 class="md-h2">Papers for your accountant ${missing ? `<span class="pill warn">${esc(missing)} missing</span>` : '<span class="pill ok">All here</span>'}</h2>${papers}</section>
        <section class="card"><h2 class="md-h2">Next payment</h2>${est}</section>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn soft" type="button" data-dl="organiser">Download the organiser (CSV)</button><button class="btn soft" type="button" data-ask="Write the list of papers for my accountant">Make the list for my accountant</button></div>
      <p class="mut" style="margin:0;font-size:13px">Hoola does not file your personal return. It reads your papers and gets them ready.${r.money_in_not_sorted ? ` ${esc(r.money_in_not_sorted)} payment(s) in could not be sorted.` : ''}</p>`;
  }

  function pSettings() {
    const k = K(), t = T(), items = k.dates || [];
    if (ST.rates === null) { ST.rates = false; run('rates').then(r => { ST.rates = r.rates || []; if (ST.tab === 'settings') showPage(true); }).catch(e => toast(e.message, true)); }
    const base = new Date(); base.setDate(1); base.setMonth(base.getMonth() + ST.cal);
    const y = base.getFullYear(), m = base.getMonth(), first = (new Date(y, m, 1).getDay() + 6) % 7, days = new Date(y, m + 1, 0).getDate();
    const dueOn = {}; items.forEach(x => { if (x.due) (dueOn[x.due] = dueOn[x.due] || []).push(x); });
    let cells = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => `<div class="dh">${d}</div>`).join('') + '<div class="d"></div>'.repeat(first);
    for (let d = 1; d <= days; d++) {
      const key = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`, hit = dueOn[key];
      cells += `<div class="d${hit ? (hit.every(h => h.filed || h.status === 'done') ? ' done' : ' due') : ''}" title="${esc((hit || []).map(h => h.what).join('; '))}">${d}${hit ? `<span>${esc(short(hit[0].what))}</span>` : ''}</div>`;
    }
    const all = items.map(x => `<div class="tx-row"><span style="flex:1">${esc(x.what)}${x.due ? ' · ' + esc(x.due) : ''}</span><span class="mut" style="font-size:13px">${esc(x.says || fromSay(x.from || ''))}</span></div>`).join('');
    const rates = ST.rates || [];
    const groups = Object.keys(KINDNAME).map(kind => {
      const rows = rates.filter(r => r.kind === kind).map(r => `<div class="tx-rt"><span>${esc(kind === 'rates' ? codeSay(r.code) : cname(r.code))}</span><span class="num">${kind === 'nexus' ? esc(money(r.value, 'USD')) : esc(r.value) + '%'}</span>
        <span class="num">${r.checked ? `<span class="pill ok">Checked ${esc(S(r.checked_on).slice(0, 10))}</span>` : (can() ? `<button class="btn sm" type="button" data-check="${esc(kind)}|${esc(r.code)}">I checked it</button>` : '<span class="pill warn">Check this</span>')}</span>
        ${can() ? `<button class="ib" type="button" aria-label="Remove" title="Remove" data-unrate="${esc(kind)}|${esc(r.code)}">×</button>` : ''}</div>`).join('');
      return `<div class="tx-rg"><div class="mut" style="font-size:13px;margin:10px 0 4px">${esc(KINDNAME[kind])}</div>${rows || '<p class="mut" style="margin:0;font-size:13px">None set.</p>'}</div>`;
    }).join('');
    const ro = can() ? '' : ' disabled';
    return `<div class="md-2" style="align-items:start">
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
        <h1 class="sd-h">Tax dates</h1>
        <section class="card"><div style="display:flex;align-items:center;gap:8px"><h2 class="md-h2" style="margin:0">${esc(base.toLocaleString(undefined, {month: 'long', year: 'numeric'}))}</h2>
          <span style="margin-left:auto;display:flex;gap:6px"><button class="btn soft sm" type="button" data-cal="-1" aria-label="Previous month">‹</button><button class="btn soft sm" type="button" data-cal="1" aria-label="Next month">›</button></span></div>
          <div class="tx-cal">${cells}</div></section>
        <section class="card"><h2 class="md-h2">All dates</h2>${all || '<p class="mut" style="margin:0">No dates yet.</p>'}
          ${can() ? `<form data-form="date" class="tx-adddate"><input class="in" name="title" placeholder="What is due" required><input class="in" type="date" name="due" required><button class="btn soft sm" type="submit">Add a date</button></form>` : ''}</section>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
        <h1 class="sd-h">Settings</h1>
        <form class="card" data-form="settings">
          <div class="md-form">
            <div class="md-field"><label for="txCc">Country</label><select class="in" id="txCc" name="country"${ro}>${t.country ? '' : '<option value="">Choose…</option>'}${Object.keys(CC).map(c => `<option value="${c}"${c === t.country ? ' selected' : ''}>${esc(CC[c])}</option>`).join('')}</select></div>
            <div class="md-field"><label for="txSc">Tax</label><select class="in" id="txSc" name="scheme"${ro}>${['vat', 'gst', 'sales_tax', 'none'].map(s => `<option value="${s}"${s === (t.scheme || 'vat') ? ' selected' : ''}>${esc({vat: 'VAT', gst: 'GST', sales_tax: 'Sales tax (US)', none: 'None'}[s])}</option>`).join('')}</select></div>
            <div class="md-field"><label for="txPk">Return period</label><select class="in" id="txPk" name="period_kind"${ro}>${['monthly', 'quarterly', 'yearly'].map(s => `<option value="${s}"${s === (t.period_kind || 'quarterly') ? ' selected' : ''}>${esc(cap(s))}</option>`).join('')}</select></div>
            <div class="md-field"><label for="txDo">Days after the period ends that it is due</label><input class="in" id="txDo" name="due_offset_days" type="number" min="0" max="400" value="${esc(t.due_offset_days ?? '')}" placeholder="From your tax office"${ro}></div>
            <div class="md-field wide"><label for="txId">Tax number</label><input class="in" id="txId" name="tax_id" autocomplete="off" placeholder="${esc(maskId(((t.seller || {}).tax_id) || ''))}"${ro}></div>
          </div>
          ${can() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Hoola does not guess a deadline: the due rule is yours.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <section class="card"><div style="display:flex;align-items:center;gap:8px"><h2 class="md-h2" style="margin:0">Rates Hoola may use</h2><span class="mut" style="margin-left:auto;font-size:13px">A rate is used only once a person checks it</span></div>
          ${ST.rates === false ? '<p class="mut">Loading…</p>' : groups}
          ${can() ? `<form data-form="rate" class="tx-addrate"><select class="in" name="kind">${Object.entries(KINDNAME).map(([k2, n2]) => `<option value="${k2}">${esc(n2)}</option>`).join('')}</select>
            <input class="in" name="code" placeholder="std, CA or IT" required><input class="in" name="value" type="number" step="0.01" min="0" placeholder="20" required><button class="btn soft sm" type="submit">Add</button></form>` : ''}</section>
      </div></div>`;
  }
  const short = s => S(s).replace(/ return for the period ending.*/i, '').replace(/^Reply to /, '').slice(0, 14);
  const codeSay = c => ({std: 'Standard', reduced: 'Reduced', super_reduced: 'Super-reduced', zero: 'Zero', exempt: 'Exempt', export: 'Export',
    eu_goods: 'Goods to EU businesses', rc_out: 'Services abroad (buyer pays)', rc_in: 'Reverse charge', oss: 'One Stop Shop', outside: 'Outside scope'}[c] || c);
  const maskId = v => { v = S(v); return v.length > 4 ? v.slice(0, 2) + ' ••• ' + v.slice(-3) : (v || 'Your VAT / GST number'); };

  /* ---------------------------------------------------------------- page actions */
  async function download(what) {
    const p = ST.retFor || K().period;
    try {
      const r = await fetch(`/api/tax/download?workspace=${enc(W().id)}&what=${enc(what)}&period=${enc(p)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `tax-${what}`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function onPageClick(e) {
    const t = e.target;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const cal = t.closest('[data-cal]'); if (cal) { ST.cal += Number(cal.dataset.cal); showPage(true); return; }
    if (t.closest('[data-copy]') && ST.letter) { try { await navigator.clipboard.writeText(ST.letter.draft || ''); toast('Copied.'); } catch { toast('Select the draft and copy it.', true); } return; }
    try {
      const la = t.closest('[data-lact]');
      if (la && ST.letter) { const r = await run('letter_act', {n: ST.letter.n, act: la.dataset.lact}); ST.letter = r.letter; ST.letters = null;
        toast(la.dataset.lact === 'sent' ? 'Marked as sent.' : 'Saved.'); await refreshDesk(false); showPage(true); return; }
      const ck = t.closest('[data-check]');
      if (ck) { const [kind, code] = ck.dataset.check.split('|'); await run('check_rate', {kind, code}); ST.rates = null; ST.ret = null; ST.retFor = ''; ST.bord = null; ST.bordFor = '';
        toast('Marked as checked by you.'); await refreshDesk(false); showPage(true); return; }
      const ur = t.closest('[data-unrate]');
      if (ur) { const [kind, code] = ur.dataset.unrate.split('|'); if (!confirm('Remove this rate?')) return;
        await run('set_rate', {kind, code, value: null}); ST.rates = null; await refreshDesk(false); showPage(true); return; }
    } catch (err) { toast(err.message, true); }
  }
  async function onChange(e) {
    const t = e.target;
    if (t.matches('[data-period]')) { location.hash = '#/returns/' + enc(t.value); return; }
    if (t.matches('[data-paper]')) {
      try { await run('paper', {name: t.dataset.paper, have: t.checked}); if (ST.pers && ST.pers.papers) { const p = ST.pers.papers.find(x => x.name === t.dataset.paper); if (p) p.have = t.checked; } showPage(true); }
      catch (err) { toast(err.message, true); t.checked = !t.checked; }
    }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return; form.dataset.sent = Date.now();
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = form.querySelector('[type=submit]');
    if (btn) btn.disabled = true;
    try {
      if (kind === 'filed') {
        const p = ST.retFor;
        if (!confirm(`Mark ${pname(p)} as filed with reference ${S(fd.get('reference'))}? The period locks on this desk.`)) return;
        const r = await run('filed', {period: p, reference: S(fd.get('reference'))}); toast(r.say); ST.retFor = ''; await refreshDesk(false); showPage(true);
      } else if (kind === 'letter') {
        const r = await run('add_letter', {text: S(fd.get('text')), name: S(fd.get('name'))}); ST.letters = null; ST.letter = r.letter;
        await refreshDesk(false); location.hash = '#/letters/' + r.letter.n;
      } else if (kind === 'confirm') {
        const r = await run('letter_act', {n: ST.letter.n, act: 'confirm_date', reply_by: S(fd.get('reply_by'))}); ST.letter = r.letter; ST.letters = null;
        toast('Date confirmed and added to your dates.'); await refreshDesk(false); showPage(true);
      } else if (kind === 'date') {
        await run('add_date', {title: S(fd.get('title')), due: S(fd.get('due'))}); toast('Added.'); await refreshDesk(true);
      } else if (kind === 'rate') {
        await run('set_rate', {kind: S(fd.get('kind')), code: S(fd.get('code')), value: Number(fd.get('value'))}); ST.rates = null;
        toast('Added. Check it before Hoola uses it.'); await refreshDesk(false); showPage(true);
      } else if (kind === 'settings') {
        const a = {country: S(fd.get('country')), scheme: S(fd.get('scheme')), period_kind: S(fd.get('period_kind'))};
        if (S(fd.get('due_offset_days')) !== '') a.due_offset_days = Number(fd.get('due_offset_days'));
        if (S(fd.get('tax_id')).trim()) a.seller = {...(T().seller || {}), tax_id: S(fd.get('tax_id')).trim()};
        await run('settings', a); toast('Saved.'); await refreshDesk(true);
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
    const box = $('#txFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/tax/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    box.innerHTML = (STARTERS[ST.tab] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-q]'); if (b) send(b.dataset.q); };
  }
  function setCtx(about) {
    ST.ctx = S(about);
    const box = $('#sdCtx');
    box.hidden = !ST.ctx;
    box.innerHTML = ST.ctx ? `<span class="pill">About: ${esc(ST.ctx)}<button type="button" aria-label="Remove">×</button></span>` : '';
    if (ST.ctx) box.querySelector('button').onclick = () => setCtx('');
    if (ST.folded) $('#sdFold').click();
    ST.bar.focus();
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
    if (ST.working && !working) refreshDesk(true);      // a turn ended: a date or rate it set shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Read these tax letters' : 'Read this tax letter';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'tx' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
