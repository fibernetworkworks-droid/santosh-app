/* v0.999.60 HOOLA WALLET inside the console (owner: "AI WALLET ... USER WILL PUT SOME MONEY THERE AND AI WILL MAKE
   TRANSACTION ... WITH APPROVAL FROM USER" + "ENTIRE WORLD", design claude.ai/artifact/6saoWTun5YqusMghbLzYgn, "GO BUILD ALL").
   Hoola asks, she approves. A computer can never approve a payment: the console sends the approval to her phone, where her
   fingerprint on the unlocked phone says yes. Hoola holds no money; a balance needs a licensed partner in her country. */
window.HoolaWallet = function HoolaWallet(ctx) {
  'use strict';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const toast = (m, bad) => (ctx && ctx.toast ? ctx.toast(m, bad) : console.log(m));
  let EL = null, TIMER = 0;
  const ST = {d: null, tab: 'home', filter: 'all', setup: {region: 'IN', mode: 'each', monthly: 10000, cats: ['groceries', 'food', 'bills', 'recharge']}, busy: false};
  const $ = s => EL && EL.querySelector(s);

  function token() { try { return localStorage.getItem('hoola.console.token') || ''; } catch { return ''; } }
  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + token()};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const r = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
    if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = j.detail || m; } catch { /* plain */ } throw new Error(typeof m === 'string' ? m : 'Request failed'); }
    return r.json();
  }

  const IC = {
    wallet: '<path d="M4 7.5A2.5 2.5 0 016.5 5H18v3"/><rect x="4" y="8" width="16" height="11" rx="2.5"/><path d="M16 13.5h.01"/>',
    bag: '<path d="M5 8h14l-1.5 11h-11L5 8zM9 8V6a3 3 0 016 0v2"/>',
    food: '<path d="M7 3v8M5 3v4a2 2 0 004 0V3M7 11v10M17 3c-2 0-3 2-3 5s1 4 3 4v9"/>',
    bills: '<path d="M7 3h10v18l-2.5-1.5L12 21l-2.5-1.5L7 21zM10 8h4M10 12h4"/>',
    recharge: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M12 8l-1.5 3h3L12 14"/>',
    shopping: '<path d="M6 7h12l1 13H5zM9 7a3 3 0 016 0"/>',
    travel: '<path d="M3 13l18-7-7 18-2-8z"/>',
    finger: '<path d="M12 4a7 7 0 017 7v2M5 11a7 7 0 012.2-5.1M12 8a3 3 0 013 3v3a8 8 0 01-1 4M9 11a3 3 0 01.4-1.5M9 14a12 12 0 00-1.5 5M12 11v3a12 12 0 01-1.5 6"/>',
    phone: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
    shield: '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    pause: '<path d="M9 5v14M15 5v14"/>',
  };
  const ico = (k, sz = 18) => `<svg width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[k] || IC.bag}</svg>`;
  const CATI = {groceries: 'bag', food: 'food', bills: 'bills', recharge: 'recharge', shopping: 'shopping', travel: 'travel'};
  const ST_LABEL = {waiting: 'Waiting for you', approved: 'Approved, paying', paid: 'Paid', declined: 'You said no', stopped: 'Not allowed',
                    expired: 'Expired', failed: 'Did not go through', refunded: 'Refunded'};
  const ST_TONE = {waiting: 'acc', approved: 'acc', paid: 'ok', declined: 'mut', stopped: 'bad', expired: 'mut', failed: 'bad', refunded: 'mut'};

  const sym = () => (ST.d && ST.d.symbol) || '₹';
  function fmt(minor) {
    const d = ST.d || {}, v = (minor || 0) / 100, region = d.region || 'IN';
    if (region === 'IN') return sym() + ' ' + v.toLocaleString('en-IN', {maximumFractionDigits: 2});
    return sym() + v.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }
  function when(iso) {
    if (!iso) return '';
    const t = new Date(iso), n = new Date(), day = 864e5;
    const d0 = new Date(n.getFullYear(), n.getMonth(), n.getDate()).getTime();
    if (t.getTime() >= d0) return 'today, ' + t.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
    if (t.getTime() >= d0 - day) return 'yesterday';
    return t.toLocaleDateString([], {day: 'numeric', month: 'short'});
  }
  function left(iso) {
    const ms = new Date(iso).getTime() - Date.now();
    if (!(ms > 0)) return 'expired';
    const m = Math.ceil(ms / 60000);
    return 'expires in ' + m + ' min';
  }

  async function load(quiet) {
    try { ST.d = await api('GET', '/api/wallet'); } catch (e) { if (!quiet) toast(e.message, true); ST.d = ST.d || {exists: false}; }
    draw();
  }

  /* ---------------------------------------------------------------- frame */
  const TABS = [['home', 'Wallet'], ['activity', 'Activity'], ['bills', 'Bills'], ['limits', 'Limits and rules'], ['add', 'Add money']];
  function head() {
    const d = ST.d;
    return `<header class="hw-head"><div class="hw-top"><h1 class="hw-h1">Hoola Wallet</h1>
      <span class="hw-pill">${ico('finger', 15)}Every payment needs your fingerprint</span></div>
      <p class="hw-sub">Hoola gets your order ready and stops before paying. You approve each payment on your phone.${d && d.paused ? ' <b class="hw-bad">All spending is paused.</b>' : ''}</p>
      <nav class="hw-tabs" role="tablist">${TABS.map(([k, l]) => `<button type="button" role="tab" class="hw-tab${ST.tab === k ? ' on' : ''}" aria-selected="${ST.tab === k}" data-hwtab="${k}">${l}</button>`).join('')}</nav></header>`;
  }
  function draw() {
    if (!EL) return;
    const d = ST.d;
    if (!d) { EL.innerHTML = '<div class="hw"><p class="hw-loading">Opening your wallet…</p></div>'; return; }
    if (!d.exists) { EL.innerHTML = `<div class="hw">${setupPage()}</div>`; return; }
    const body = {home, activity, bills, limits, add}[ST.tab] || home;
    EL.innerHTML = `<div class="hw">${head()}<div class="hw-body">${body()}</div></div>`;
  }

  /* ---------------------------------------------------------------- setup */
  function setupPage() {
    const d = ST.d || {}, s = ST.setup, regions = d.regions || {IN: {name: 'India', symbol: '₹'}};
    const cats = d.categories || {};
    const partner = !!d.partner;
    return `<div class="hw-setup"><div class="hw-setcol">
      <span class="hw-pill">${ico('shield', 15)}Hoola never holds your money</span>
      <h1 class="hw-h1 big">Let Hoola pay for the everyday things</h1>
      <p class="hw-lead">Groceries, food orders, bills and recharges. Hoola fills the cart, checks the total, and stops. You approve with your fingerprint, and only then does the money move.</p>
      <ol class="hw-steps"><li><b>You set the limits</b>A monthly amount, a limit for each kind of spending, and the shops Hoola may use.</li>
        <li><b>Hoola gets it ready</b>It opens the shop, fills the cart and stops at the checkout.</li>
        <li><b>You approve on your phone</b>One touch of your fingerprint. Nothing is paid without it.</li></ol>
    </div><form class="hw-card hw-form hw-setform" id="hwSetup">
      <b class="hw-h3">Set up your wallet</b>
      <label class="hw-lab">Country<select class="hw-in" name="region">${Object.entries(regions).map(([k, v]) => `<option value="${k}"${s.region === k ? ' selected' : ''}>${esc(v.name)} · ${esc(v.symbol)}</option>`).join('')}</select></label>
      <div class="hw-lab">How Hoola pays
        <div class="hw-opts">
          <label class="hw-opt${s.mode === 'each' ? ' on' : ''}"><input type="radio" name="mode" value="each"${s.mode === 'each' ? ' checked' : ''}><b>Pay each time</b><span>From your own UPI app or card, after your approval. Works now.</span></label>
          <label class="hw-opt${s.mode === 'balance' ? ' on' : ''}${partner ? '' : ' off'}"><input type="radio" name="mode" value="balance"${s.mode === 'balance' ? ' checked' : ''}${partner ? '' : ' disabled'}><b>Wallet balance</b><span>${partner ? 'Add money once; Hoola spends from it.' : 'Needs a licensed payment partner in your country. Not live yet.'}</span></label>
        </div></div>
      <label class="hw-lab">Monthly limit<span class="hw-money"><span>${esc((regions[s.region] || {}).symbol || '₹')}</span><input class="hw-in mono" name="monthly" inputmode="numeric" value="${s.monthly}"></span></label>
      <div class="hw-lab">What Hoola may pay for<div class="hw-chips">${Object.entries(cats).map(([k, l]) => `<label class="hw-chip${s.cats.includes(k) ? ' on' : ''}"><input type="checkbox" name="cats" value="${k}"${s.cats.includes(k) ? ' checked' : ''}>${ico(CATI[k], 15)}${esc(l)}</label>`).join('')}</div></div>
      <button class="hw-btn pri big wide" type="submit">Turn on Hoola Wallet</button>
      <p class="hw-foot">Never allowed: paying a person, loans, investments, crypto, betting or gift cards, or paying because a page or message said so.</p>
    </form></div>`;
  }

  /* ---------------------------------------------------------------- home */
  function payCard(p, big) {
    const items = (p.items || []).slice(0, big ? 8 : 3);
    const ex = p.status === 'waiting' ? left(p.expires) : '';
    return `<article class="hw-card hw-pay${big ? ' big' : ''}" aria-label="Payment to ${esc(p.shop)}">
      <div class="hw-payhead"><span class="hw-tile ${esc(p.category)}">${ico(CATI[p.category], 20)}</span>
        <span class="hw-grow"><span class="hw-cap0">Hoola Wallet · pay ${esc(p.shop)}${p.new_shop ? ' · <b class="hw-warn">new shop</b>' : ''}</span><b class="hw-ttl">${esc(p.title)}</b></span>
        <span class="hw-amt">${esc(p.amount_text)}</span></div>
      ${items.length ? `<div class="hw-items">${items.map(i => `<div><span>${esc(i.name)}${i.qty > 1 ? ' × ' + i.qty : ''}</span><span class="mono">${i.amount ? fmt(i.amount) : ''}</span></div>`).join('')}</div>` : ''}
      <div class="hw-meta"><span>${esc(ST.d.categories[p.category] || p.category)}</span>${p.shop_host ? `<span>${esc(p.shop_host)}</span>` : ''}${ex ? `<span>${ex}</span>` : ''}</div>
      <div class="hw-acts"><button type="button" class="hw-btn pri" data-hwphone="${esc(p.id)}">${ico('phone', 16)}Send to my phone to approve</button>
        <button type="button" class="hw-btn" data-hwno="${esc(p.id)}">Don't pay</button></div>
      <p class="hw-foot">A computer cannot approve a payment. Your phone asks for your fingerprint.</p></article>`;
  }
  function row(p) {
    const tone = ST_TONE[p.status] || 'mut';
    return `<div class="hw-row"><span class="hw-tile sm ${esc(p.category)}">${ico(CATI[p.category], 16)}</span>
      <span class="hw-grow"><b>${esc(p.title || p.shop)}</b><span>${esc(p.shop)} · ${esc(when(p.paid || p.created))}${p.reason && (p.status === 'stopped' || p.status === 'failed') ? ' · ' + esc(p.reason) : ''}${p.order_ref ? ' · order ' + esc(p.order_ref) : ''}</span></span>
      <span class="hw-st ${tone}">${esc(ST_LABEL[p.status] || p.status)}</span><span class="hw-amt sm">${esc(p.amount_text)}</span></div>`;
  }
  function home() {
    const d = ST.d, sp = d.spent || {}, L = d.limits || {};
    const pct = L.monthly ? Math.min(100, Math.round(100 * (sp.month || 0) / L.monthly)) : 0;
    const waiting = (d.payments || []).filter(p => p.status === 'waiting');
    const recent = (d.payments || []).filter(p => p.status !== 'waiting').slice(0, 6);
    const month = new Date().toLocaleDateString([], {month: 'long'});
    const cats = Object.entries(L.cats || {}).filter(([, c]) => c.on);
    return `<div class="hw-grid">
      <div class="hw-col">
        <section class="hw-hero" aria-label="Spending this month">
          <span class="hw-herocap">${d.balance != null ? 'Wallet balance' : 'Left to spend this month'}</span>
          <span class="hw-herobig">${esc(d.balance != null ? fmt(d.balance) : d.text.left)}</span>
          <div class="hw-bar"><i style="width:${pct}%"></i></div>
          <div class="hw-herorow"><span>${esc(d.text.month)} spent of ${esc(d.text.monthly)}</span><span>${esc(month)}</span></div>
          <div class="hw-heroacts"><button type="button" class="hw-btn inv" data-hwtab="add">Add money</button><button type="button" class="hw-btn ghost" data-hwtab="limits">Limits</button></div>
        </section>
        ${waiting.length ? `<div><h2 class="hw-cap">Waiting for you</h2><div class="hw-stack">${waiting.map(p => payCard(p, false)).join('')}</div></div>` : ''}
        <div><h2 class="hw-cap">Recent</h2>${recent.length ? `<div class="hw-card hw-list">${recent.map(row).join('')}</div>` :
          `<div class="hw-card hw-empty"><b>Nothing paid yet</b><span>Ask Hoola in the chat: "Order milk, bread and eggs for home". It gets the cart ready and asks you here.</span></div>`}</div>
      </div>
      <aside class="hw-col">
        <h2 class="hw-cap">This month by kind</h2>
        <div class="hw-card hw-list">${cats.map(([k, c]) => {
          const used = (sp.by || {})[k] || 0, p = c.limit ? Math.min(100, Math.round(100 * used / c.limit)) : 0;
          return `<div class="hw-catrow"><span class="hw-tile sm ${k}">${ico(CATI[k], 16)}</span><span class="hw-grow"><b>${esc(d.categories[k])}</b>
            <span class="hw-mini"><i style="width:${p}%"></i></span></span><span class="mono hw-small">${esc(d.text.by[k])} / ${esc(d.text.cat_limit[k])}</span></div>`;
        }).join('') || '<div class="hw-empty"><span>Every kind is switched off.</span></div>'}</div>
        <h2 class="hw-cap" style="margin-top:6px">Your safety</h2>
        <div class="hw-card hw-rules">
          <span>${ico('finger', 16)}Your fingerprint on your unlocked phone for every payment</span>
          <span>${ico('shield', 16)}${L.known_only ? 'Only shops you have paid before, unless you say yes to a new one' : 'New shops are allowed, and marked on the card'}</span>
          <span>${ico('bills', 16)}Up to ${esc(d.text.per_buy)} a payment, ${esc(d.text.per_day)} a day</span>
          <span>${ico('pause', 16)}Never pays a person, a loan, investments, crypto, betting or gift cards</span>
        </div>
        <button type="button" class="hw-btn ${d.paused ? 'pri' : 'badline'} wide" data-hwpause="${d.paused ? 0 : 1}">${d.paused ? 'Turn spending back on' : 'Pause all spending'}</button>
      </aside></div>`;
  }

  /* ---------------------------------------------------------------- activity */
  function activity() {
    const all = ST.d.payments || [];
    const F = [['all', 'All'], ['paid', 'Paid'], ['waiting', 'Waiting'], ['stopped', 'Not allowed'], ['declined', 'Said no']];
    const list = ST.filter === 'all' ? all : all.filter(p => p.status === ST.filter || (ST.filter === 'declined' && p.status === 'expired'));
    return `<div class="hw-seg" role="group">${F.map(([k, l]) => `<button type="button" class="${ST.filter === k ? 'on' : ''}" data-hwf="${k}">${l}</button>`).join('')}</div>
      ${list.length ? `<div class="hw-card hw-list">${list.map(row).join('')}</div>` : '<div class="hw-card hw-empty"><span>Nothing here yet.</span></div>'}
      <p class="hw-foot">"Not allowed" means Hoola checked your limits and did not ask you. You see it here so nothing is hidden.</p>`;
  }

  /* ---------------------------------------------------------------- bills */
  function bills() {
    const b = ST.d.bills || [];
    return `<div class="hw-grid"><div class="hw-col">
      <h2 class="hw-cap">Your bills</h2>
      ${b.length ? `<div class="hw-card hw-list">${b.map(x => `<div class="hw-row"><span class="hw-tile sm bills">${ico('bills', 16)}</span>
        <span class="hw-grow"><b>${esc(x.name)}</b><span>${esc(x.kind || 'Bill')}${x.account ? ' · ' + esc(x.account) : ''}${x.due ? ' · due ' + esc(x.due) : ''}</span></span>
        <span class="hw-st ${x.status === 'paid' ? 'ok' : 'mut'}">${x.status === 'paid' ? 'Paid' : 'Due'}</span>
        <span class="hw-amt sm">${esc(x.amount_text || '')}</span>
        ${x.status !== 'paid' && x.amount ? `<button type="button" class="hw-btn sm" data-hwbill="${esc(x.id)}">Ask Hoola to pay</button>` : ''}
        <button type="button" class="hw-x" aria-label="Remove ${esc(x.name)}" data-hwdel="${esc(x.id)}">×</button></div>`).join('')}</div>` :
        '<div class="hw-card hw-empty"><b>No bills yet</b><span>Add electricity, water, phone or broadband. Hoola reminds you before the due date and asks before it pays.</span></div>'}
    </div><form class="hw-card hw-form" id="hwBill">
      <b class="hw-h3">Add a bill</b>
      <label class="hw-lab">Name<input class="hw-in" name="name" required maxlength="80" placeholder="Electricity, home"></label>
      <label class="hw-lab">Kind<select class="hw-in" name="kind"><option>Electricity</option><option>Water</option><option>Gas</option><option>Mobile</option><option>Broadband</option><option>DTH</option><option>Insurance</option><option>Other</option></select></label>
      <label class="hw-lab">Biller website<input class="hw-in" name="site" maxlength="200" placeholder="https://…"></label>
      <label class="hw-lab">Consumer or account number<input class="hw-in mono" name="account" maxlength="40" autocomplete="off"><span class="hw-hint">Kept sealed; shown with only the last digits.</span></label>
      <div class="hw-two"><label class="hw-lab">Due date<input class="hw-in" type="date" name="due"></label>
        <label class="hw-lab">Amount<span class="hw-money"><span>${esc(sym())}</span><input class="hw-in mono" name="amount" inputmode="decimal"></span></label></div>
      <button type="submit" class="hw-btn pri wide">Save bill</button>
    </form></div>`;
  }

  /* ---------------------------------------------------------------- limits */
  function limits() {
    const d = ST.d, L = d.limits, maj = v => Math.round((v || 0) / 100);
    return `<form id="hwLimits" class="hw-grid"><div class="hw-col">
      <div class="hw-card hw-form"><b class="hw-h3">Spending limits</b>
        <div class="hw-three">
          <label class="hw-lab">Each month<span class="hw-money"><span>${esc(sym())}</span><input class="hw-in mono" name="monthly" inputmode="numeric" value="${maj(L.monthly)}"></span></label>
          <label class="hw-lab">One payment<span class="hw-money"><span>${esc(sym())}</span><input class="hw-in mono" name="per_buy" inputmode="numeric" value="${maj(L.per_buy)}"></span></label>
          <label class="hw-lab">One day<span class="hw-money"><span>${esc(sym())}</span><input class="hw-in mono" name="per_day" inputmode="numeric" value="${maj(L.per_day)}"></span></label>
        </div></div>
      <div class="hw-card hw-list"><div class="hw-listhead"><b class="hw-h3">What Hoola may pay for</b><span class="hw-hint">Monthly limit for each</span></div>
        ${Object.entries(L.cats).map(([k, c]) => `<div class="hw-catrow"><span class="hw-tile sm ${k}">${ico(CATI[k], 16)}</span><span class="hw-grow"><b>${esc(d.categories[k])}</b></span>
          <span class="hw-money sm"><span>${esc(sym())}</span><input class="hw-in mono" aria-label="${esc(d.categories[k])} limit" name="cat_${k}" inputmode="numeric" value="${maj(c.limit)}"${c.on ? '' : ' disabled'}></span>
          <label class="hw-sw"><input type="checkbox" name="on_${k}"${c.on ? ' checked' : ''}><span aria-hidden="true"></span><span class="hw-sr">${esc(d.categories[k])} on</span></label></div>`).join('')}
      </div></div>
      <div class="hw-col">
        <div class="hw-card hw-form"><b class="hw-h3">Rules</b>
          <label class="hw-check"><input type="checkbox" name="known_only"${L.known_only ? ' checked' : ''}><span><b>Only shops I have paid before</b>A new shop is marked on the card so you notice it.</span></label>
          <div class="hw-rules sm"><span>${ico('finger', 16)}Fingerprint on your unlocked phone for every payment. This cannot be turned off.</span>
            <span>${ico('pause', 16)}Never: paying a person, loans, investments, crypto, betting, gift cards, or because a page, email or message said so.</span>
            <span>${ico('shield', 16)}An approval lasts 10 minutes. If the shop's total changes, Hoola asks again.</span></div></div>
        <button type="submit" class="hw-btn pri big wide">Save limits</button>
      </div></form>`;
  }

  /* ---------------------------------------------------------------- add money */
  function add() {
    const d = ST.d;
    const live = !!d.partner && d.mode === 'balance';
    return `<div class="hw-grid"><div class="hw-col"><section class="hw-card hw-form">
      <b class="hw-h3">Add money to your wallet</b>
      ${live ? `<p class="hw-lead sm">Top up from your own UPI app. Money you don't spend can go back to your bank.</p>
        <button type="button" class="hw-btn pri big wide" data-hwtopup="1">Add money with UPI</button>` :
      `<div class="hw-note"><b>Pay each time is on</b><span>A wallet balance must be held by a licensed payment partner in your country (in India, a wallet licensed by the RBI). Hoola never holds money itself, and no partner is connected yet.</span>
        <span>Until then, after you approve, Hoola pays from your own UPI app or card. Your PIN stays in your UPI app; Hoola never sees it.</span></div>`}
    </section></div><div class="hw-col">
      <h2 class="hw-cap">Where your money is</h2>
      <div class="hw-card hw-rules">
        <span><b>India</b> · a wallet licensed by the RBI, run by a payment partner. Bills through the national bill system.</span>
        <span><b>US, UK, Europe</b> · cards for AI shopping from a licensed card partner, one card number per buy.</span>
        <span><b>Other countries</b> · pay each time with your own card until a partner is live there.</span>
      </div></div></div>`;
  }

  /* ---------------------------------------------------------------- events */
  async function act(fn, okMsg) {
    if (ST.busy) return;
    ST.busy = true;
    try { const r = await fn(); if (r && r.exists !== undefined) ST.d = r; if (okMsg) toast(okMsg); await load(true); }
    catch (e) { toast(e.message, true); }
    finally { ST.busy = false; }
  }
  const num = v => Math.max(0, Math.round(parseFloat(String(v || '').replace(/[^\d.]/g, '')) || 0));

  function onClick(e) {
    const t = e.target.closest('button,[data-hwtab]');
    if (!t || !EL.contains(t)) return;
    if (t.dataset.hwtab) { ST.tab = t.dataset.hwtab; draw(); return; }
    if (t.dataset.hwf) { ST.filter = t.dataset.hwf; draw(); return; }
    if (t.dataset.hwphone) return act(() => api('POST', `/api/wallet/payments/${encodeURIComponent(t.dataset.hwphone)}/to-phone`), 'Sent to your phone. Approve it there with your fingerprint.');
    if (t.dataset.hwno) return act(() => api('POST', `/api/wallet/payments/${encodeURIComponent(t.dataset.hwno)}/decide`, {approve: false}), 'Not paid. Hoola is told.');
    if (t.dataset.hwpause) return act(() => api('PUT', '/api/wallet/limits', {paused: t.dataset.hwpause === '1'}), t.dataset.hwpause === '1' ? 'All spending paused.' : 'Spending is on again.');
    if (t.dataset.hwbill) return act(() => api('POST', `/api/wallet/bills/${encodeURIComponent(t.dataset.hwbill)}/pay`), 'Hoola asked you to approve it on your phone.');
    if (t.dataset.hwdel) { if (!confirm('Remove this bill?')) return; return act(() => api('DELETE', `/api/wallet/bills/${encodeURIComponent(t.dataset.hwdel)}`), 'Bill removed.'); }
    if (t.dataset.hwtopup) return act(() => api('POST', '/api/wallet/add-money'));
  }
  function onChange(e) {
    const f = e.target.form;
    if (f && f.id === 'hwSetup') {
      const fd = new FormData(f);
      ST.setup = {region: fd.get('region') || 'IN', mode: fd.get('mode') || 'each', monthly: num(fd.get('monthly')), cats: fd.getAll('cats')};
      draw();
    }
    if (f && f.id === 'hwLimits' && e.target.name && e.target.name.startsWith('on_')) {
      const inp = f.querySelector(`[name="cat_${e.target.name.slice(3)}"]`);
      if (inp) inp.disabled = !e.target.checked;
    }
  }
  function onSubmit(e) {
    const f = e.target;
    if (!EL.contains(f)) return;
    e.preventDefault();
    const fd = new FormData(f);
    if (f.id === 'hwSetup') {
      const s = {region: fd.get('region'), mode: fd.get('mode') || 'each', monthly: num(fd.get('monthly')) * 100, cats: fd.getAll('cats')};
      return act(() => api('POST', '/api/wallet/setup', s), 'Hoola Wallet is on.');
    }
    if (f.id === 'hwBill') {
      const amt = Math.round((parseFloat(String(fd.get('amount') || '').replace(/[^\d.]/g, '')) || 0) * 100);
      return act(() => api('POST', '/api/wallet/bills', {name: fd.get('name'), kind: fd.get('kind'), site: fd.get('site') || '',
        account: fd.get('account') || '', due: fd.get('due') || '', amount: amt}), 'Bill saved.');
    }
    if (f.id === 'hwLimits') {
      const cats = {};
      for (const k of Object.keys(ST.d.limits.cats)) cats[k] = {on: !!fd.get('on_' + k), limit: num(f.querySelector(`[name="cat_${k}"]`).value) * 100};
      return act(() => api('PUT', '/api/wallet/limits', {monthly: num(fd.get('monthly')) * 100, per_buy: num(fd.get('per_buy')) * 100,
        per_day: num(fd.get('per_day')) * 100, known_only: !!fd.get('known_only'), cats}), 'Limits saved.');
    }
  }

  return {
    open(el) {
      if (EL !== el) {
        EL = el;
        el.addEventListener('click', onClick);
        el.addEventListener('change', onChange);
        el.addEventListener('submit', onSubmit);
      }
      draw();
      load();
      clearInterval(TIMER);
      TIMER = setInterval(() => { if (document.visibilityState === 'visible' && !ST.busy && !(EL && EL.contains(document.activeElement) && /INPUT|SELECT/.test(document.activeElement.tagName))) load(true); }, 8000);
    },
    leave() { clearInterval(TIMER); TIMER = 0; },
  };
};
