/* v0.999.25 HOOLA CREDITS - the console's Credits page (owner: "GO Dodo Payments, Paddle, RAZORPAY, CASHFREE").
   Her wallet (free today, paid credits, her plan), the plans / top-ups / AI-employee packages for HER country (the
   server picks the price level and the payment service), and what came in and went out. Buying opens the provider's
   checkout in a new tab; the order counts only when the provider confirms it (the page polls the server). */
'use strict';
window.HoolaCredits = function (H) {
  const {api, esc, toast} = H;
  const country = () => ((navigator.language || '').split('-')[1] || '').toUpperCase();
  const money = (v, cur) => cur === 'INR' ? '₹' + Number(v).toLocaleString('en-IN') : '$' + Number(v).toLocaleString('en-US', {maximumFractionDigits: 2});
  const n = v => Number(v || 0).toLocaleString('en-US', {maximumFractionDigits: 0});
  let EL = null, D = null, EMPS = [];

  async function load() {
    D = await api('GET', '/api/credits?country=' + encodeURIComponent(country()));
    try { const e = await api('GET', '/api/employees'); EMPS = (e.employees || e.roles || e.items || []).filter(x => x.live !== false); } catch { EMPS = []; }
  }
  function walletCard(w) {
    if (!w || !w.on) return `<section class="crd-card"><h2>Credits are off</h2><p class="crd-mut">This server does not charge credits yet.</p></section>`;
    if (w.exempt) return `<section class="crd-card"><h2>No credits needed</h2><p class="crd-mut">This account is never charged.</p></section>`;
    const plan = w.plan ? `${esc(w.plan_name)} plan until ${new Date(w.plan_until).toLocaleDateString()}` : 'No plan';
    return `<section class="crd-card crd-wallet">
      <div><span class="crd-big">${n(w.paid_left)}</span><span class="crd-mut"> paid credits</span></div>
      <div class="crd-row"><span>${plan}</span><span>${n(w.plan_left)} plan · ${n(w.topup_left)} extra</span></div>
      <div class="crd-row"><span>Free today (Normal only)</span><span>${n(w.free_left)} of ${n(w.free_daily)}</span></div>
      <p class="crd-note">${w.unlocked ? 'Every quality tier is open. Each message takes the credits of the tier it runs on - Ultra goes fastest.'
        : 'Free works on Normal. Buy any plan or extra credits to open Ultra, High, Medium and Low.'}</p></section>`;
  }
  function plans(p) {
    return `<h3 class="crd-h">Monthly plans</h3><div class="crd-grid">${p.plans.map(x => `<article class="crd-card crd-plan">
      <h4>${esc(x.name)}</h4><div class="crd-price">${money(x.price, p.currency)}<small> / month</small></div>
      <p class="crd-mut">${n(x.credits)} credits a month</p>
      <button type="button" class="crd-buy" data-sku="${esc(x.sku)}">Buy ${esc(x.name)}</button></article>`).join('')}</div>
      <h3 class="crd-h">Extra credits</h3><div class="crd-grid">${p.topups.map(x => `<article class="crd-card crd-plan">
      <h4>${n(x.credits)} credits</h4><div class="crd-price">${money(x.price, p.currency)}</div>
      <p class="crd-mut">Last 12 months</p><button type="button" class="crd-buy" data-sku="${esc(x.sku)}">Buy</button></article>`).join('')}</div>`;
  }
  function packs(p, mine) {
    const opts = EMPS.map(e => `<option value="${esc(e.key || e.id)}">${esc(e.name || e.title || e.key)}</option>`).join('');
    const have = (mine || []).map(x => `<li><b>${esc(x.employee)}</b> - ${esc(x.name)}: ${x.active ? `${x.left} of ${x.jobs} jobs left, until ${new Date(x.until).toLocaleDateString()}` : 'ended'}</li>`).join('');
    return `<h3 class="crd-h">AI employees</h3><p class="crd-mut">Each AI employee has its own package: a number of jobs a month on a set tier. It is not paid from your credits.</p>
      ${have ? `<ul class="crd-list">${have}</ul>` : ''}
      <label class="crd-emp">For <select id="crdEmp">${opts || '<option value="">No employees listed</option>'}</select></label>
      <div class="crd-grid">${p.packs.map(x => `<article class="crd-card crd-plan">
      <h4>${esc(x.name)}</h4><div class="crd-price">${money(x.price, p.currency)}<small> / month</small></div>
      <p class="crd-mut">${n(x.jobs)} jobs · ${esc(x.tier[0].toUpperCase() + x.tier.slice(1))}</p>
      <button type="button" class="crd-buy" data-sku="${esc(x.sku)}" data-pack="1">Buy package</button></article>`).join('')}</div>`;
  }
  function history(rows) {
    if (!rows.length) return '';
    return `<h3 class="crd-h">Recent orders</h3><div class="crd-table"><table><thead><tr><th>Item</th><th>Amount</th><th>Paid with</th><th>Status</th></tr></thead><tbody>
      ${rows.map(o => `<tr><td>${esc(o.name)}${o.employee ? ' · ' + esc(o.employee) : ''}</td><td>${money(o.amount, o.currency)}</td><td>${esc(o.provider)}</td><td>${esc(o.status)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function draw() {
    const p = D.prices, prov = (D.providers || []).join(', ') || 'not set up yet';
    EL.innerHTML = `<div class="crd"><header class="crd-head"><h2>Credits</h2>
      <p class="crd-mut">One credit is 0.1 US cent of AI cost. Prices for your country (${esc(p.currency)}); payments by ${esc(prov)}.</p></header>
      ${walletCard(D.wallet)}${D.wallet && D.wallet.on ? plans(p) + packs(p, D.packs) : ''}${history(D.orders || [])}</div>`;
  }
  async function buy(btn) {
    const body = {sku: btn.dataset.sku, country: country()};
    if (btn.dataset.pack) { body.employee = (EL.querySelector('#crdEmp') || {}).value || ''; if (!body.employee) { toast('Pick the AI employee first.', true); return; } }
    btn.disabled = true;
    try {
      const o = await api('POST', '/api/credits/checkout', body);
      window.open(o.redirect || o.pay_url, '_blank', 'noopener');
      toast('Finish the payment in the new tab. Credits are added once the payment service confirms it.');
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 4000));
        const s = await api('GET', '/api/credits/orders/' + encodeURIComponent(o.order));
        if (s.status !== 'pending') { toast(s.status === 'paid' ? 'Payment received.' : 'The payment did not go through.', s.status !== 'paid'); break; }
      }
      await load(); draw();
    } catch (e) { toast(e.message, true); }
    btn.disabled = false;
  }
  async function open(el) {
    EL = el; el.innerHTML = '<p class="crd-mut">Loading…</p>';
    try { await load(); draw(); } catch (e) { el.innerHTML = `<p class="crd-mut">${esc(e.message)}</p>`; }
  }
  document.addEventListener('click', e => { const b = e.target.closest?.('.crd-buy'); if (b && EL && EL.contains(b)) buy(b); });
  return {open};
};
