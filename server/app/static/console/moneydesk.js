/* v0.999.156 MONEY SAFETY DESK - the Money Safety Assistant's own section, like the business desks (owner: "Money Safety
   Assistant --- now lets make a seperate panel as same as in bussiness section has" -> the design
   claude.ai/artifact/BWjghhnCL3daja6RgrkMeE -> "go").
   A thin top bar, then the Money Safety chat (its own conversation, kind 'money': she pastes a message or tells what went
   wrong, attaches a screenshot) beside the desk's pages: Today, Check before paying, My cases (+ one case, + a new case),
   Is my money safe, Settings. The pages call the F1 engine (/api/fin/safety/*). Every letter is a draft SHE sends; her
   taps only move a case's state. Nothing here moves money. Every date carries its level: Confirmed (a person checked
   the rule) / Reminder (read from the official page) / Not confirmed - check this. Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    warn: '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h0"/>', alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const CC = {GB: 'United Kingdom', US: 'United States', IN: 'India', AE: 'United Arab Emirates', SG: 'Singapore', AU: 'Australia',
    CA: 'Canada', IE: 'Ireland', DE: 'Germany', SA: 'Saudi Arabia'};
  const TABS = [['today', 'Today'], ['check', 'Check before paying'], ['cases', 'My cases'], ['deposit', 'Is my money safe'], ['settings', 'Settings']];
  const KINDS = [
    ['refund_claim', 'Scam refund claim', 'You were tricked into paying, or a payment you never made. A letter asking your bank to pay it back.'],
    ['card_dispute', 'Card dispute', 'Not delivered, not as described, charged twice or cancelled.'],
    ['complaint_global', 'Complaint to my bank', 'A formal complaint, then the free ombudsman if they don\'t put it right.'],
    ['credit_dispute', 'Credit report dispute', 'Something wrong on your report. A letter to the agency (and the lender).'],
    ['id_theft', 'Identity theft', 'Someone used your name or documents. Step by step recovery.'],
    ['deposit', 'Is my money protected', 'How much of your savings the deposit scheme covers, bank by bank.']];
  const KNAME = Object.fromEntries(KINDS.map(k => [k[0], k[1]]));
  KNAME.complaint = KNAME.complaint_global;
  const STATE = {drafted: ['warn', 'Letter ready · not sent'], sent: ['', 'Sent · waiting'], tracking: ['', 'Waiting for an answer'], closed: ['ok', 'Closed']};
  const TRUST = {seekh: ['Learning', 'Checks and drafts. Every letter waits for you to send it.'],
                 saathi: ['Partner', 'Also keeps your cases up to date on its own. Letters still wait for you.'],
                 bharosa: ['Trusted', 'Does more on its own. Sending letters and moving money always stay yours.']};
  const STARTERS = {
    today: ['Is this message a scam?', 'My card was charged twice', 'Is my money safe in my bank?'],
    check: ['Is this link safe?', 'Someone called from my bank', 'I already paid - what now?'],
    cases: ['What should I do next on my case?', 'Make my letter firmer', 'Which case is most urgent?'],
    deposit: ['Do two of my banks share one limit?', 'What happens if my bank fails?', 'Is a joint account covered twice?'],
    settings: ['Which countries do you know?', 'Why are dates not confirmed?', 'What will you never ask me?']};
  const FIELDS = {
    refund_claim: [['bank', 'Your bank', 'text'], ['account', 'Account - last 4 digits only', 'text'], ['amount', 'Amount', 'number'],
      ['txn_date', 'Date you paid', 'date', true], ['noticed_on', 'Date you noticed', 'date'], ['txn_ref', 'Payment reference', 'text'],
      ['kind', 'What happened', ['scam:I was tricked into paying', 'unauthorised:I did not make this payment']],
      ['narrative', 'In your own words', 'area'], ['name', 'Your name (for the letter)', 'text']],
    card_dispute: [['bank', 'Your card provider', 'text'], ['account', 'Card - last 4 digits only', 'text'], ['amount', 'Amount', 'number'],
      ['merchant', 'The shop', 'text'], ['txn_date', 'Date of the payment', 'date', true], ['contacted_on', 'Date you contacted the shop', 'date'],
      ['reason', 'What went wrong', ['not_received:It never arrived', 'not_as_described:Not as described', 'charged_twice:Charged twice', 'cancelled:I cancelled and was still charged', 'unauthorised:I did not make this payment']],
      ['name', 'Your name (for the letter)', 'text']],
    complaint_global: [['bank', 'The bank or firm', 'text'], ['account', 'Account - last 4 digits only', 'text'],
      ['complained_on', 'Date you complain', 'date'], ['final_answer_on', 'Date of their final answer (if any)', 'date'],
      ['narrative', 'What went wrong', 'area'], ['outcome', 'What would put it right', 'area'], ['name', 'Your name (for the letter)', 'text']],
    credit_dispute: [['bureau', 'Credit agency', 'text'], ['item', 'The wrong entry (lender and account shown)', 'text'],
      ['sent_on', 'Date you send it', 'date'], ['narrative', 'Why it is wrong', 'area'], ['name', 'Your name (for the letter)', 'text']],
    id_theft: [['lost', 'What was taken (comma separated: passport, phone, cards…)', 'text']]};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], filter: 'open',
    last: {}, checkText: '', checkRes: null, banks: [{bank: '', amount: ''}], depRes: null, idRes: null};
  try { ST.side = localStorage.getItem('hoola.money.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.money.folded') === '1'; } catch {}

  const cname = cc => CC[cc] || cc || '';
  const today = () => new Date().toISOString().slice(0, 10);

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/money/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.shield, '')}</div>
        <h1 class="sd-h">Your Money Safety Assistant is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="mdHire">Hire Money Safety</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#mdHire').onclick = async () => { try { await api('POST', '/api/employees/paisa_sahayak/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
    ST.tab = ['case', 'new'].includes(parts[0]) || TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.shield, '')}</div>
          <div style="min-width:0"><div class="sd-name">Money Safety</div><div class="sd-site" id="mdSite"></div></div>
          <span id="mdState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Money Safety chat">
          <div class="sd-chathead"><div class="t"><b>Money Safety chat</b><span>Paste a message, attach a screenshot · never a PIN or code</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="mdFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="mdPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.eml,.csv">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Money Safety desk" id="sdTabs"></nav>
          <div id="mdPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a message or tell me what happened…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#mdPick').click()});
    $('#mdPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.money.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.money.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/money/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
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
    const d = ST.d, el = $('#mdState'); if (!el) return;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !d.country ? ['warn', 'Choose your country'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#mdSite').textContent = `${d.country ? cname(d.country) : 'No country chosen yet'} · ${d.open} case${d.open === 1 ? '' : 's'} open`;
  }
  function paintTabs() {
    const d = ST.d || {}, cur = ST.tab === 'case' || ST.tab === 'new' ? (ST.arg === 'deposit' ? 'deposit' : 'cases') : ST.tab;
    $('#sdTabs').innerHTML = TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === cur}">${esc(n)}${
      k === 'cases' && d.open ? `<span class="n">${esc(d.open)}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/money/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint || ['today', 'cases'].includes(ST.tab)) showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#mdPage'); if (!box) return;
    const fn = {today: pToday, check: pCheck, cases: pCases, case: pCase, new: pNew, deposit: pDeposit, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    if (typeof html === 'string') box.innerHTML = html;
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  const level = t => t.kind === 'deadline' ? ['ok', `Confirmed: ${t.date}`] : t.kind === 'reminder' ? ['', `Reminder ${t.date}`]
    : t.kind === 'unknown' ? ['warn', 'No time limit known'] : ['warn', 'Not confirmed - check this'];
  const duePill = c => c.state === 'closed' ? '' : c.due ? `<span class="pill ok">Confirmed: ${esc(c.due)}</span>`
    : c.state === 'drafted' ? '<span class="pill warn">Send it soon</span>' : '';
  const statePill = c => { const [k, n] = STATE[c.state] || ['', c.state]; return `<span class="pill ${k}">${esc(n)}</span>`; };
  const kindOf = part => KNAME[part] || part;

  function pToday() {
    const d = ST.d, open = (d.cases || []).filter(c => c.state !== 'closed'), draft = open.find(c => c.state === 'drafted');
    const alert = !d.country
      ? `<section class="md-alert">${svg(IC.warn)}<div><div class="t">Choose your country</div><div class="s">Hoola uses its rules - who to complain to and the time limits.</div></div><button class="btn sm" type="button" data-go="settings">Choose</button></section>`
      : draft ? `<section class="md-alert">${svg(IC.warn)}<div><div class="t">Send your ${esc(kindOf(draft.part).toLowerCase())}</div><div class="s">The letter is ready. Send it to the bank yourself - the sooner the better.</div></div><button class="btn sm" type="button" data-go="case/${esc(draft.id)}">Open the letter</button></section>` : '';
    const rows = open.slice(0, 6).map(c => `<tr><td><b>${esc(kindOf(c.part))}</b><div class="mut" style="font-size:13px">Opened ${esc(c.created_at.slice(0, 10))}</div></td>
      <td>${statePill(c)}</td><td>${duePill(c)}</td><td style="text-align:right"><button class="btn soft sm" type="button" data-go="case/${esc(c.id)}">Open</button></td></tr>`).join('');
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${open.length ? `${open.length} case${open.length > 1 ? 's' : ''} open.` : 'No cases open.'} Nothing here moves money - letters are drafts you send yourself.</p></div>
      ${alert}
      <div class="md-2">
        <form class="card" data-form="quickcheck"><h2 class="md-h2">Check before you pay</h2>
          <div class="md-field"><label for="mdQc">Paste the message, link or payment request</label><textarea class="in" id="mdQc" name="text" rows="3">${esc(ST.checkText)}</textarea></div>
          <div class="md-acts"><span class="mut" style="font-size:12.5px">Links are read, never opened</span><button class="btn" type="submit">Check it</button></div></form>
        <section class="card"><h2 class="md-h2">Something went wrong?</h2><div class="md-mini">${KINDS.map(([k, n]) =>
          `<button type="button" data-go="${k === 'deposit' ? 'deposit' : 'new/' + k}">${esc({refund_claim: 'I was scammed', card_dispute: 'Dispute a card payment', complaint_global: 'Complain to my bank', credit_dispute: 'Wrong on my credit report', id_theft: 'Someone used my identity', deposit: 'Is my money protected'}[k] || n)}</button>`).join('')}</div></section>
      </div>
      <section class="card tight"><div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0 4px"><h2 class="md-h2" style="margin:0">Open cases</h2><button class="btn soft sm" type="button" data-go="cases">All cases</button></div>
        ${rows ? `<div style="overflow-x:auto"><table class="tb"><tbody>${rows}</tbody></table></div>` : '<p class="mut" style="margin:6px 0 12px">No cases yet. Start one when something goes wrong.</p>'}</section>
      ${legend()}`;
  }
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  function legend() {
    return `<div class="md-legend"><span><i style="background:var(--ok)"></i>Confirmed by a person</span><span><i style="background:var(--dim)"></i>Reminder from the official page</span><span><i style="background:var(--warn)"></i>Not confirmed - check this</span></div>`;
  }
  function countrySelect(id) {
    const cur = ST.d.country || '';
    return `<select class="in" id="${id}" name="country">${cur ? '' : '<option value="">Choose…</option>'}${(ST.d.countries || Object.keys(CC)).map(c =>
      `<option value="${esc(c)}"${c === cur ? ' selected' : ''}>${esc(cname(c))}</option>`).join('')}</select>`;
  }

  function pCheck() {
    const r = ST.checkRes;
    return `<div><h1 class="sd-h">Check before paying</h1><p class="lead">Paste what you got. Hoola reads it for the signs of a scam. Links are read as text and never opened.</p></div>
      <div class="md-2" style="align-items:start">
        <div style="display:flex;flex-direction:column;gap:16px">
          <form class="card" data-form="check">
            <div class="md-field"><label for="mdMsg">What did you get?</label><textarea class="in" id="mdMsg" name="text" rows="5" required>${esc(ST.checkText)}</textarea></div>
            <div class="md-form" style="margin-top:10px">
              <div class="md-field"><label for="mdSnd">Who sent it</label><input class="in" id="mdSnd" name="sender"></div>
              <div class="md-field"><label for="mdCc">Your country</label>${countrySelect('mdCc')}</div>
              <label class="md-check"><input type="checkbox" name="payee_new"> A new payee I've never paid</label>
              <label class="md-check"><input type="checkbox" name="pressure"> I'm being rushed or told to keep it secret</label>
            </div>
            <div class="md-acts"><button class="btn soft sm" type="button" data-attach="1">Add a screenshot in the chat</button><button class="btn" type="submit">Check it</button></div>
          </form>
          <section class="card"><h2 class="md-h2">Before you pay anyone</h2><ol class="md-ol">
            <li>Stop. Call them back on a number you find yourself.</li>
            <li>Never pay to "release" a parcel, prize, refund or account.</li>
            <li>A real bank, police or tax office never asks you to move money to keep it safe.</li>
            <li>Never share a PIN, password, card number or a code.</li></ol></section>
        </div>
        <div style="display:flex;flex-direction:column;gap:16px">${r ? checkResult(r) : `<section class="card"><p class="mut" style="margin:0">The result shows here.</p></section>`}</div>
      </div>`;
  }
  function checkResult(r) {
    const sc = r.scam_check || {}, v = S(sc.verdict);
    const [k, label] = v === 'critical-pattern' || v === 'high-risk-pattern' ? ['bad', 'Looks like a scam'] : v === 'suspicious' ? ['warn', 'Be careful'] : ['ok', 'No known scam pattern'];
    const fam = sc.families || [], links = (sc.links || []).filter(l => (l.flags || []).length || l.verdict === 'high-risk'), extra = r.extra_signs || [];
    let i = 0;
    const signs = [...fam.map(f => `<div class="md-sign"><span class="n">${++i}</span><div><b>${esc(f.name)}.</b> <span class="mut">${esc(f.why)}</span></div></div>`),
      ...links.map(l => `<div class="md-sign"><span class="n">${++i}</span><div><b>Link: ${esc(l.host || l.url)}</b> <span class="mut">${esc((l.flags || []).join('; '))}</span></div></div>`),
      ...(sc.pressure_words ? [`<div class="md-sign"><span class="n">${++i}</span><div><b>Rush.</b> <span class="mut">It pushes you to act before you check.</span></div></div>`] : []),
      ...(sc.secrets_mentioned || []).length ? [`<div class="md-sign"><span class="n">${++i}</span><div><b>Asks for a secret:</b> <span class="mut">${esc(sc.secrets_mentioned.join(', '))}. Never give it.</span></div></div>`] : [],
      ...extra.map(x => `<div class="md-sign"><span class="n">${++i}</span><div><b>${esc(x)}</b></div></div>`)].join('');
    const route = r.route ? routeList(r.route) : '';
    return `<section class="card"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><span class="md-verdict ${k}">${svg(IC.alert)}${esc(label)}</span>
        <span class="mut" style="font-size:13px">${i ? `${i} sign${i > 1 ? 's' : ''} found` : 'No signs found'}</span></div>
        ${signs ? `<div style="margin-top:12px">${signs}</div>` : ''}
        ${(sc.what_to_do || []).length ? `<h2 class="md-h2" style="margin-top:14px">What to do</h2><ol class="md-ol">${sc.what_to_do.map(x => `<li>${esc(x)}</li>`).join('')}</ol>` : ''}
        <p class="mut" style="margin:12px 0 0;font-size:12.5px">${esc(sc.note || 'The link was read as text and never opened.')}</p></section>
      <section class="card"><h2 class="md-h2">If you already paid</h2><ol class="md-ol">${(r.if_already_paid || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>
        ${route ? `<h2 class="md-h2" style="margin-top:14px">Who to go to</h2>${route}` : ''}
        <div style="margin-top:14px"><button class="btn" type="button" data-go="new/refund_claim">Start a refund claim</button></div></section>`;
  }
  function routeList(route) {
    return `<ol class="md-route">${route.map((x, n) => `<li><span class="k">${n + 1}</span><div><b>${esc(x.who)}</b><div class="s">${esc(x.how || '')}${x.phone ? ' · ' + esc(x.phone) : ''}${x.site ? ' · ' + esc(x.site) : ''}</div></div></li>`).join('')}</ol>`;
  }

  function pCases() {
    const all = ST.d.cases || [], list = all.filter(c => ST.filter === 'open' ? c.state !== 'closed' : c.state === 'closed');
    const nOpen = all.filter(c => c.state !== 'closed').length, nClosed = all.length - nOpen;
    const rows = list.map(c => `<tr><td><b>${esc(kindOf(c.part))}</b><div class="mut" style="font-size:13px">${esc(c.title)} · opened ${esc(c.created_at.slice(0, 10))}</div></td>
      <td>${statePill(c)}</td><td>${duePill(c)}</td><td style="text-align:right"><button class="btn soft sm" type="button" data-go="case/${esc(c.id)}">Open</button></td></tr>`).join('');
    return `<div><h1 class="sd-h">Start a case</h1></div>
      <div class="md-3">${KINDS.map(([k, n, s]) => `<button class="md-kind" type="button" data-go="${k === 'deposit' ? 'deposit' : 'new/' + k}"><b>${esc(n)}</b><span>${esc(s)}</span></button>`).join('')}</div>
      <section class="card tight"><div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;gap:10px;flex-wrap:wrap">
        <h2 class="md-h2" style="margin:0">Your cases</h2>
        <div role="group" aria-label="Filter cases" style="display:flex;gap:6px">
          <button class="chip" type="button" data-filter="open" aria-pressed="${ST.filter === 'open'}">Open ${nOpen}</button>
          <button class="chip" type="button" data-filter="closed" aria-pressed="${ST.filter === 'closed'}">Closed ${nClosed}</button></div></div>
        ${rows ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Case</th><th>Where it is</th><th>Next date</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
          : `<p class="mut" style="margin:0 0 12px">${ST.filter === 'open' ? 'No open cases.' : 'No closed cases.'}</p>`}</section>
      ${legend()}`;
  }

  function pNew() {
    const part = ST.arg;
    if (!FIELDS[part]) { location.hash = '#/cases'; return ''; }
    const fields = FIELDS[part].map(([k, label, t, req]) => {
      const id = 'mdF_' + k;
      const ctl = Array.isArray(t) ? `<select class="in" id="${id}" name="${k}">${t.map(o => { const [v, n] = o.split(/:(.*)/); return `<option value="${esc(v)}">${esc(n)}</option>`; }).join('')}</select>`
        : t === 'area' ? `<textarea class="in" id="${id}" name="${k}" rows="3"></textarea>`
        : `<input class="in" id="${id}" name="${k}" type="${t}"${t === 'number' ? ' min="0" step="0.01"' : ''}${req ? ' required' : ''}${t === 'date' && req ? ` value="${today()}"` : ''}${k === 'account' ? ' inputmode="numeric" maxlength="4" pattern="[0-9]{0,4}"' : ''}>`;
      return `<div class="md-field${t === 'area' ? ' wide' : ''}"><label for="${id}">${esc(label)}</label>${ctl}</div>`;
    }).join('');
    const res = part === 'id_theft' && ST.idRes ? `<section class="card"><h2 class="md-h2">What to do, in this order</h2><ol class="md-ol">${(ST.idRes.steps || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>
      ${ST.idRes.route ? `<h2 class="md-h2" style="margin-top:14px">Who to go to</h2>${routeList(ST.idRes.route)}` : ''}${ST.idRes.says ? `<p class="mut" style="margin:12px 0 0;font-size:13px">${esc(ST.idRes.says)}</p>` : ''}</section>` : '';
    return `<a class="md-back" href="#/cases">← My cases</a>
      <div><h1 class="sd-h">${esc(kindOf(part))}</h1><p class="lead">${esc((KINDS.find(k => k[0] === part) || [])[2] || '')} Leave a box empty and the letter shows a blank to fill in.</p></div>
      <form class="card" data-form="new" data-part="${esc(part)}">
        <div class="md-form"><div class="md-field"><label for="mdF_cc">Your country</label>${countrySelect('mdF_cc')}</div>${fields}</div>
        <p class="mut" style="font-size:12.5px;margin:12px 0 0">Only the last 4 digits of an account. Never type a PIN, password, card number or a code here.</p>
        <div class="md-acts"><button class="btn soft" type="button" data-go="cases">Cancel</button><button class="btn" type="submit">${part === 'id_theft' ? 'Show the steps' : 'Draft the letter'}</button></div>
      </form>${res}`;
  }

  function pCase() {
    const id = ST.arg;
    const c = (ST.d.cases || []).find(x => x.id === id);
    if (!ST.case || ST.case.id !== id) {
      ST.case = null;
      api('GET', `/api/money/cases/${enc(id)}`).then(r => { ST.case = r; if (ST.tab === 'case' && ST.arg === id) showPage(true); })
        .catch(e => { toast(e.message, true); location.hash = '#/cases'; });
      return `<a class="md-back" href="#/cases">← My cases</a><section class="card"><p class="mut" style="margin:0">Opening the case…</p></section>`;
    }
    const k = ST.case, more = {...k, ...(ST.last[id] || {})};
    const letter = esc(k.letter || '').replace(/\[([^\]\n]{1,80})\]/g, '<span class="blank">[$1]</span>');
    const limits = (more.time_limits || more.clocks || []).map(t => { const [p, n] = level(t); return `<div class="md-limit"><span class="pill ${p}">${esc(n)}</span><div>${esc(t.says)}</div></div>`; }).join('');
    const ev = (more.evidence || []).map((x, n) => `<label class="md-check"><input type="checkbox" data-ev="${n}"> ${esc(x)}</label>`).join('');
    const next = k.state === 'drafted' ? ['sent', "I've sent it"] : k.state === 'closed' ? ['drafted', 'Open it again'] : ['closed', 'Close the case'];
    return `<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap"><a class="md-back" href="#/cases">← My cases</a>
        <h1 class="sd-h" style="font-size:22px">${esc(kindOf(k.part))}</h1>${statePill(k)}<span style="flex:1"></span>
        ${k.state === 'sent' ? '<button class="btn soft sm" type="button" data-state="tracking">Waiting for an answer</button>' : ''}
        <button class="btn sm" type="button" data-state="${next[0]}">${esc(next[1])}</button></div>
      <div class="md-2" style="grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);align-items:start">
        <section class="card md-card0"><div class="md-lhead"><h2 class="md-h2" style="margin:0">The letter</h2>
          <div style="display:flex;gap:6px"><button class="btn soft sm" type="button" data-copy="1">Copy</button><button class="btn soft sm" type="button" data-dl="1">Download</button>
          <button class="btn soft sm" type="button" data-ask="Change my ${esc(kindOf(k.part).toLowerCase())} letter">Change it in the chat</button></div></div>
          <pre class="md-letter">${letter || '<span class="mut">No letter in this case.</span>'}</pre>
          <div class="md-lfoot">You send this yourself. Hoola does not send it for you.</div></section>
        <div style="display:flex;flex-direction:column;gap:16px">
          <section class="card"><h2 class="md-h2">Time limits</h2>${limits || (k.due ? `<div class="md-limit"><span class="pill ok">Confirmed: ${esc(k.due)}</span><div>The confirmed deadline for this case.</div></div>`
            : '<p class="mut" style="margin:0;font-size:14px">No confirmed deadline for this case. Act as early as you can and check the time limit with your bank.</p>')}
            <p class="mut" style="margin:10px 0 0;font-size:12.5px">"Confirmed" only appears once a qualified person has checked the rule.</p></section>
          ${ev ? `<section class="card"><h2 class="md-h2">Evidence to keep</h2>${ev}</section>` : ''}
          ${more.route ? `<section class="card"><h2 class="md-h2">If they say no</h2>${routeList(more.route)}</section>` : ''}
          ${more.also ? `<section class="card"><p style="margin:0;font-size:14px">${esc(more.also)}</p></section>` : ''}
        </div></div>`;
  }

  function pDeposit() {
    const r = ST.depRes;
    const rows = ST.banks.map((b, n) => `<div class="md-brow"><input class="in" aria-label="Bank ${n + 1}" placeholder="Bank (or banking group)" data-bank="${n}" value="${esc(b.bank)}">
      <input class="in" aria-label="Amount at bank ${n + 1}" placeholder="Amount" type="number" min="0" step="0.01" data-amt="${n}" value="${esc(b.amount)}">
      <button class="ib" type="button" aria-label="Remove bank ${n + 1}" data-rm="${n}">×</button></div>`).join('');
    let out = '';
    if (r) {
      const banks = r.banks || [];
      const tot = banks.reduce((a, b) => a + Number(b.total || 0), 0);
      const conf = banks.some(b => 'protected' in b);
      const over = banks.reduce((a, b) => a + Number(b.above_limit ?? b.estimate_above_limit ?? b.above_unconfirmed_limit ?? 0), 0);
      const money = x => Number(x).toLocaleString(undefined, {maximumFractionDigits: 2});
      out = `<div class="md-3"><div class="md-kpi"><div class="l">Your savings</div><div class="v">${money(tot)}</div></div>
          <div class="md-kpi"><div class="l">Within the limit${conf ? '' : ' (if it holds)'}</div><div class="v ok">${money(tot - over)}</div></div>
          <div class="md-kpi"><div class="l">Above the limit${conf ? '' : ' (if it holds)'}</div><div class="v bad">${money(over)}</div></div></div>
        <section class="card tight"><h2 class="md-h2" style="margin:12px 0 0">Bank by bank</h2>${banks.map(b => {
          const o = Number(b.above_limit ?? b.estimate_above_limit ?? b.above_unconfirmed_limit ?? 0), t = Number(b.total || 0), pin = t ? Math.round((t - o) / t * 100) : 0;
          return `<div class="md-bank"><div class="hd"><b>${esc(b.bank)}</b><span class="num">${money(t)}</span></div>
            <div class="md-bar" role="img" aria-label="${money(t - o)} within the limit, ${money(o)} above"><div class="in" style="width:${pin}%"></div><div class="${conf ? 'over' : 'unk'}" style="width:${100 - pin}%"></div></div>
            ${o ? `<div class="s bad">${money(o)} above the limit.</div>` : ''}</div>`; }).join('')}</section>
        <section class="${conf ? 'card' : 'md-alert'}">${conf ? '' : svg(IC.warn)}<div><div class="${conf ? '' : 't'}">${esc(r.says || '')}</div>
          <div class="s" style="margin-top:4px">${esc(r.scheme ? 'Scheme: ' + r.scheme + '. ' : '')}Banks in one group can share one limit - put them on one row. Hoola never moves your money.</div></div></section>`;
    }
    return `<div><h1 class="sd-h">Is my money protected?</h1><p class="lead">If a bank fails, the deposit scheme pays back up to a limit per person, per banking licence.</p></div>
      <form class="card" data-form="deposit"><div class="md-form" style="margin-bottom:12px"><div class="md-field"><label for="mdDc">Your country</label>${countrySelect('mdDc')}</div></div>
        ${rows}<div class="md-acts"><button class="btn soft sm" type="button" data-addbank="1">Add a bank</button><button class="btn" type="submit">Check</button></div></form>
      ${out}`;
  }

  function pSettings() {
    const d = ST.d, cur = Object.keys(TRUST).find(k => TRUST[k][0] === d.trust) || 'seekh';
    return `<div><h1 class="sd-h">Settings</h1></div>
      <form class="card" data-form="country"><h2 class="md-h2">Your country</h2>
        <div class="md-form"><div class="md-field"><label for="mdSc">Hoola uses this country's rules</label>${countrySelect('mdSc')}</div></div>
        <p class="mut" style="margin:10px 0 0;font-size:13.5px">Hoola knows ${esc((d.countries || []).map(cname).join(', '))}. Its rules are from memory until a person checks them, so dates show as "Not confirmed - check this". Elsewhere it gives the steps that are true everywhere.</p>
        <div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div></form>
      <section class="card"><h2 class="md-h2">How much it does on its own</h2>
        <div role="radiogroup" aria-label="Trust" style="display:flex;gap:6px;flex-wrap:wrap">${Object.entries(TRUST).map(([k, [n]]) =>
          `<button type="button" class="btn ${k === cur ? '' : 'soft'} sm" role="radio" aria-checked="${k === cur}" data-trust="${k}">${esc(n)}</button>`).join('')}</div>
        <p class="mut" style="margin:10px 0 0;font-size:13.5px">${esc(TRUST[cur][1])}</p>
        <div style="display:flex;gap:8px;margin-top:12px">${d.status === 'paused' ? '<button class="btn soft sm" type="button" data-emp="resume">Resume</button>' : '<button class="btn soft sm" type="button" data-emp="pause">Pause</button>'}
          <button class="btn soft sm bad" type="button" data-emp="leave">Let go</button></div></section>
      <section class="card"><h2 class="md-h2">What it will never do</h2><ol class="md-ol">
        <li>Ask for your PIN, password, card number or a one-time code.</li><li>Send a letter or move money for you.</li><li>Open a link from a message.</li></ol></section>`;
  }

  /* ---------------------------------------------------------------- page actions */
  async function onPageClick(e) {
    const t = e.target;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const f = t.closest('[data-filter]'); if (f) { ST.filter = f.dataset.filter; showPage(true); return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    if (t.closest('[data-attach]')) { const m = $('#mdMsg'); if (m) ST.checkText = m.value; $('#mdPick').click(); return; }
    if (t.closest('[data-addbank]')) { readBanks(); ST.banks.push({bank: '', amount: ''}); showPage(true); return; }
    const rm = t.closest('[data-rm]'); if (rm) { readBanks(); ST.banks.splice(Number(rm.dataset.rm), 1); if (!ST.banks.length) ST.banks.push({bank: '', amount: ''}); showPage(true); return; }
    if (t.closest('[data-copy]') && ST.case) { try { await navigator.clipboard.writeText(ST.case.letter || ''); toast('Copied.'); } catch { toast('Select the letter and copy it.', true); } return; }
    if (t.closest('[data-dl]') && ST.case) {
      const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([ST.case.letter || ''], {type: 'text/plain'}));
      a.download = `${kindOf(ST.case.part).replace(/\W+/g, '-').toLowerCase()}-letter.txt`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); return;
    }
    const sb = t.closest('[data-state]');
    if (sb && ST.case) {
      try { ST.case = await api('POST', `/api/money/cases/${enc(ST.case.id)}/state`, {state: sb.dataset.state});
        toast(sb.dataset.state === 'sent' ? 'Marked as sent. Hoola keeps it on your list until you close it.' : 'Saved.');
        await refreshDesk(false); showPage(true); } catch (err) { toast(err.message, true); }
      return;
    }
    const tr = t.closest('[data-trust]'), emp = t.closest('[data-emp]');
    try {
      if (tr) { await api('PUT', '/api/employees/paisa_sahayak/settings', {trust: tr.dataset.trust}); toast('Saved.'); await refreshDesk(true); }
      if (emp) {
        if (emp.dataset.emp === 'leave' && !confirm('Let your Money Safety Assistant go? Its desk closes. Your cases stay.')) return;
        await api('POST', `/api/employees/paisa_sahayak/${emp.dataset.emp}`);
        if (emp.dataset.emp === 'leave') { location.href = '/console/?v=hire'; return; }
        toast(emp.dataset.emp === 'pause' ? 'Paused.' : 'Working again.'); await refreshDesk(true);
      }
    } catch (err) { toast(err.message, true); }
  }
  function readBanks() {
    document.querySelectorAll('[data-bank]').forEach(el => { const n = Number(el.dataset.bank); if (ST.banks[n]) ST.banks[n].bank = el.value; });
    document.querySelectorAll('[data-amt]').forEach(el => { const n = Number(el.dataset.amt); if (ST.banks[n]) ST.banks[n].amount = el.value; });
  }
  async function saveCountry(cc) {
    if (!cc || cc === ST.d.country) return;
    try { await api('PUT', '/api/money/country', {country: cc}); ST.d.country = cc; stateLine(); } catch (e) { toast(e.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = form.querySelector('[type=submit]');
    const cc = S(fd.get('country'));
    if (kind === 'quickcheck') { ST.checkText = S(fd.get('text')); location.hash = '#/check'; if (ST.checkText.trim() && ST.d.country) runCheck({text: ST.checkText, country: ST.d.country}); return; }
    if (kind !== 'country' && !cc) { toast('Choose your country first.', true); return; }
    if (btn) btn.disabled = true;
    try {
      if (kind === 'country') { await saveCountry(cc); toast('Saved.'); await refreshDesk(true); }
      else if (kind === 'check') {
        ST.checkText = S(fd.get('text')); await saveCountry(cc);
        await runCheck({text: ST.checkText, sender: S(fd.get('sender')), country: cc, payee_new: !!fd.get('payee_new'), pressure: !!fd.get('pressure')});
      } else if (kind === 'deposit') {
        readBanks(); await saveCountry(cc);
        const balances = ST.banks.filter(b => S(b.bank).trim()).map(b => ({bank: S(b.bank).trim(), amount: Number(b.amount) || 0}));
        if (!balances.length) { toast('Add at least one bank.', true); return; }
        ST.depRes = await api('POST', '/api/fin/safety/deposit_check', {country: cc, balances}); showPage(true);
      } else if (kind === 'new') {
        const part = form.dataset.part, a = {country: cc};
        for (const [k] of FIELDS[part]) { const v = S(fd.get(k)).trim(); if (v) a[k] = k === 'amount' ? Number(v) : v; }
        if (part === 'id_theft') a.lost = S(a.lost).split(',').map(x => x.trim()).filter(Boolean);
        await saveCountry(cc);
        const r = await api('POST', `/api/fin/safety/${enc(part)}`, a);
        if (part === 'id_theft') { ST.idRes = r; showPage(true); return; }
        if (r.case_id) { ST.last[r.case_id] = r; await refreshDesk(false); toast('Letter drafted. Read it, fill any blank, then send it yourself.'); location.hash = '#/case/' + r.case_id; }
        else { ST.idRes = r; toast(r.says || 'Hoola has no rules for this country yet - these steps hold everywhere.'); showPage(true); }
      }
    } catch (err) { toast(err.message, true); }
    finally { if (btn) btn.disabled = false; }
  }
  async function runCheck(a) {
    try { ST.checkRes = await api('POST', '/api/fin/safety/check_pay', a); } catch (e) { toast(e.message, true); return; }
    if (ST.tab === 'check') showPage(true);
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
    try { const r = await api('GET', '/api/money/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    const key = ST.tab === 'case' || ST.tab === 'new' ? 'cases' : ST.tab;
    box.innerHTML = (STARTERS[key] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
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
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Checking…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text),
      files: r.role === 'user' && Array.isArray(r.files) ? r.files : undefined}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) refreshDesk(false);      // a turn ended: a case it drafted shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Is this a scam? Look at these' : 'Is this a scam? Look at this';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'md' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
