/* v0.807 BAHI - the GST & Accounts desk (console). A0: the foundation, shown honestly.
   Tabs: Overview (this month's dates + figures + the trail), Register (every document once, from every engine), Rules (each with its
   source and the day it was checked), Connection (the WhiteBooks pipe - which keys are set, the last sandbox check; never a key),
   Plan (what is built and what comes next).
   Rules this page keeps: every server value goes through esc(); nothing here files, pays or shows a secret; a date the research could
   not confirm on a government page is SAID to be unconfirmed; motion = entrances once (BACKWARDS) + the hero drawing, nothing loops
   under text; styles reuse the Desk Room (`ddk-`) scale + a few `acd-` rules. */
'use strict';
window.HoolaBahi = function ({api, esc, toast, open, title}) {
  let EL = null, OV = null, TAB = 'overview', REG = null, F = {period: '', direction: '', source: ''}, BUSY = false, ITC = null, PV = null, G1 = null, G3 = null, EI = null, BL = null;
  const inr = n => '₹' + Number(n || 0).toLocaleString('en-IN', {maximumFractionDigits: 2});
  const fdate = d => { try { return new Date(d + 'T00:00:00').toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); } catch (_) { return d; } };
  const mname = p => { try { const [y, m] = p.split('-'); return new Date(+y, +m - 1, 1).toLocaleDateString('en-IN', {month: 'long', year: 'numeric'}); } catch (_) { return p; } };
  const BASIS = {'primary': 'Read on the government site', 'primary-listing': 'Listed on the government site', 'provider-spec': "WhiteBooks' own spec",
                 'secondary-confirmed': 'Two sources agree', 'unverified': 'Not yet checked on a government site'};
  const ART = '<path d="M60 40h120a18 18 0 0 1 18 18v120a12 12 0 0 0-12-12H60z" stroke-width="2.4"/><path d="M340 40H220a18 18 0 0 0-18 18v120a12 12 0 0 1 12-12h126z" stroke-width="2.4" style="animation-delay:.2s"/><path d="M84 76h84M84 100h84M84 124h56M228 76h84M228 100h60M228 124h84" stroke-width="2" opacity=".7" style="animation-delay:.45s"/><path d="M286 148l14 14 26-30" stroke-width="3" style="animation-delay:.8s"/><path d="M40 190h320" stroke-width="1.5" opacity=".35"/>';
  const art = () => `<svg class="ddk-art" viewBox="0 0 400 210" aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">${ART.replace(/<path/g, '<path class="ddk-draw" pathLength="1"')}</svg>`;
  const svg = p => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  const ICON = '<path d="M5 4h11l3 3v13H5zM9 9h6M9 13h6M9 17h4"/>';

  async function load(first) {
    try { OV = await api('GET', '/api/bahi/overview'); } catch (e) { EL.innerHTML = `<div class="ddk"><p class="ddk-quiet">${esc(e.message)}</p></div>`; return; }
    if (!F.period) F.period = OV.period;
    title?.('· GST & Accounts');
    draw(first);
    if (TAB === 'register') loadRegister();
  }
  async function loadRegister() {
    const q = new URLSearchParams(Object.entries(F).filter(([, v]) => v)).toString();
    try { REG = (await api('GET', '/api/bahi/register' + (q ? '?' + q : ''))).rows; } catch (e) { REG = []; toast(e.message, true); }
    const box = EL.querySelector('#acdReg'); if (box) box.innerHTML = regTable();
  }

  function draw(first) {
    const o = OV, tm = o.this_month, lm = o.last_month;
    const dueSoon = o.dues.filter(d => d.days_left >= 0).length;
    const hired = ['hired', 'paused'].includes(o.employee.status);
    EL.innerHTML = `<div class="ddk acd${first ? ' in' : ''}">
      <nav class="ddk-crumb" aria-label="Where you are"><button type="button" data-a="hub">AI Employees</button><span aria-hidden="true">›</span><span aria-current="page">GST &amp; Accounts</span></nav>
      ${o.enabled ? '' : '<p class="ddk-note">This desk is switched off on the server (BAHI_ENABLED).</p>'}
      ${hired ? '' : `<div class="acd-banner"><span>Hire <b>GST &amp; Accounts</b> in AI Employees to keep this desk in your sidebar. Everything below already reads your own records.</span><button type="button" class="btn go ddk-mid" data-a="hire">Hire</button></div>`}
      <section class="ddk-hero">
        <div class="ddk-herotx">
          <span class="ddk-eyebrow">${svg(ICON)}Your accountant</span>
          <h1 class="ddk-h1">GST &amp; Accounts</h1>
          <p class="ddk-lede">Every bill in one register, counted once. Your GST dates with days left. Filing comes next, from Hoola, only on your OTP.</p>
          <div class="ddk-nums">
            <div><b>${tm.documents}</b><span>documents in ${esc(mname(o.period).split(' ')[0])}</span></div>
            <div><b>${inr(lm.sales.tax)}</b><span>GST on ${esc(mname(o.prev_period).split(' ')[0])} sales</span></div>
            <div><b>${dueSoon}</b><span>dates still ahead</span></div>
          </div>
        </div>
        <div class="ddk-heroart">${art()}</div>
      </section>
      <div class="ddk-tabs acd-tabs" role="tablist">${[['overview', 'Overview'], ['register', 'Register'], ['rules', 'Rules'], ['itc', 'Credit (ITC)'], ['g1', 'GSTR-1'], ['g3', 'GSTR-3B'], ['ei', 'e-Invoice'], ['bl', 'Bills'], ['connection', 'Connection'], ['plan', 'Plan']]
        .map(([k, n]) => `<button type="button" role="tab" data-a="tab" data-t="${k}" aria-selected="${TAB === k}">${n}</button>`).join('')}</div>
      <div class="acd-body">${TAB === 'register' ? register() : TAB === 'rules' ? rules() : TAB === 'itc' ? itcTab() : TAB === 'g1' ? g1Tab() : TAB === 'g3' ? g3Tab() : TAB === 'ei' ? eiTab() : TAB === 'bl' ? blTab() : TAB === 'connection' ? connection() : TAB === 'plan' ? plan() : overview()}</div>
    </div>`;
  }

  // ------------------------------------------------------------------ Overview
  function overview() {
    const o = OV, lm = o.last_month, tm = o.this_month;
    const pill = d => d.days_left < 0 ? `<span class="ddk-pill bad">${-d.days_left}d ago</span>` : d.days_left <= 3 ? `<span class="ddk-pill warn">${d.days_left === 0 ? 'Today' : d.days_left + 'd left'}</span>` : `<span class="ddk-pill ok">${d.days_left}d left</span>`;
    return `<div class="acd-grid">
      <section class="ddk-card acd-due"><div class="acd-cardhd"><h2 class="ddk-h3">Due this month <small>for ${esc(mname(o.prev_period))}</small></h2><span class="ddk-fine first">${esc(o.scheme === 'qrmp' ? 'Quarterly (QRMP) filer' : 'Monthly filer')}</span></div>
        <ol class="acd-dues">${o.dues.map(d => `<li><time>${esc(fdate(d.date))}</time><div><b>${esc(d.what)}</b><small>${esc(d.if_missed)}</small>${d.basis === 'unverified' ? '<small class="acd-unv">Date not yet checked on a government site - confirm it on the portal.</small>' : ''}</div>${pill(d)}</li>`).join('')}</ol>
      </section>
      <section class="ddk-card"><div class="acd-cardhd"><h2 class="ddk-h3">${esc(mname(o.prev_period))}</h2>${lm.locked ? '<span class="ddk-pill mute">Locked</span>' : ''}</div>
        ${month(lm)}
        <div class="acd-cardhd sp"><h2 class="ddk-h3">${esc(mname(o.period))} so far</h2>${tm.locked ? '<span class="ddk-pill mute">Locked</span>' : ''}</div>
        ${month(tm)}
        <div class="ddk-run"><button type="button" class="btn go ddk-mid" data-a="sync" ${BUSY ? 'disabled' : ''}>${BUSY ? 'Reading your records…' : 'Sync the register'}</button>
          <span class="ddk-fine first">Reads GST Sahayak, wholesale, office bills and your app. Nothing in them is changed.</span></div>
      </section>
    </div>
    <section class="ddk-card acd-trail"><h2 class="ddk-h3">What changed</h2>${o.events.length ? `<ul class="acd-ev">${o.events.map(e => `<li><span>${esc(evWord(e.what))}</span><span class="acd-evl">${esc(e.label || e.ref)}</span><time>${esc(new Date(e.at).toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}))}</time></li>`).join('')}</ul>` : '<p class="ddk-quiet">Nothing yet. Press Sync to read your records.</p>'}</section>`;
  }
  const evWord = w => ({added: 'Added', changed: 'Changed', gone_at_source: 'Removed at its source', change_held_locked: 'Change held - month locked', lock: 'Month locked', unlock: 'Month unlocked'}[w] || w);
  function month(m) {
    return `<div class="ddk-tiles acd-tiles">
      <div class="ddk-tile"><span>Sales (${m.sales.count})</span><b>${inr(m.sales.taxable)}</b><em>GST ${inr(m.sales.tax)}</em></div>
      <div class="ddk-tile"><span>Purchases (${m.purchases.count})</span><b>${inr(m.purchases.taxable)}</b><em>GST ${inr(m.purchases.tax)}</em></div>
      <div class="ddk-tile${m.problems ? ' acd-warn' : ''}"><span>Need a look</span><b>${m.problems}</b><em>${m.problems ? 'see Register' : 'all clear'}</em></div></div>`;
  }

  // ------------------------------------------------------------------ Register
  function register() {
    const months = []; const [y0, m0] = OV.period.split('-').map(Number);
    for (let i = 0; i < 12; i++) { const d = new Date(y0, m0 - 1 - i, 1); months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`); }
    const locked = F.period === OV.period ? OV.this_month.locked : F.period === OV.prev_period ? OV.last_month.locked : null;
    return `<div class="acd-filters">
        <label>Month<select data-f="period">${months.map(m => `<option value="${m}"${m === F.period ? ' selected' : ''}>${esc(mname(m))}</option>`).join('')}</select></label>
        <label>Type<select data-f="direction"><option value="">Sales + purchases</option><option value="out"${F.direction === 'out' ? ' selected' : ''}>Sales</option><option value="in"${F.direction === 'in' ? ' selected' : ''}>Purchases</option></select></label>
        <label>From<select data-f="source"><option value="">Every source</option>${Object.entries(OV.sources).map(([k, n]) => `<option value="${esc(k)}"${F.source === k ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
        <span class="acd-sp"></span>
        ${locked === null ? '' : `<button type="button" class="btn soft ddk-mid" data-a="lock" data-on="${locked ? 0 : 1}">${locked ? 'Unlock ' : 'Lock '}${esc(mname(F.period).split(' ')[0])}</button>`}
      </div>
      <div id="acdReg">${REG ? regTable() : '<p class="ddk-quiet">Opening the register…</p>'}</div>`;
  }
  function regTable() {
    if (!REG.length) return '<p class="ddk-quiet">Nothing here yet. Press Sync on Overview to read GST Sahayak, wholesale, office bills and your app.</p>';
    return `<div class="ddk-tbl"><table><thead><tr><th>Date</th><th>Number</th><th>Party</th><th>GSTIN</th><th>Taxable</th><th>GST</th><th>Total</th><th>From</th><th><span class="ddk-sr">Notes</span></th></tr></thead><tbody>${REG.map(r => `
      <tr class="${r.status === 'gone' ? 'acd-gone' : ''}"><td>${esc(r.date)}</td><td>${esc(r.number)}${r.kind === 'cn' ? ' <span class="ddk-pill mute">Credit note</span>' : ''}</td><td>${esc(r.party)}<small class="acd-dir">${r.direction === 'out' ? 'Sale' : 'Purchase'}</small></td>
        <td><code>${esc(r.party_gstin || '–')}</code></td><td>${inr(r.taxable)}</td><td>${inr(r.tax)}</td><td>${inr(r.total)}</td><td>${esc(r.source_name)}</td>
        <td>${r.problems.length ? `<span class="acd-flag" title="${esc(r.problems.map(p => p.text).join(' · '))}">${r.problems.length} note${r.problems.length > 1 ? 's' : ''}</span>` : ''}${r.status === 'gone' ? '<span class="ddk-pill mute">Removed at source</span>' : ''}</td></tr>
      ${r.problems.length ? `<tr class="acd-probs"><td colspan="9">${r.problems.map(p => `<span>${esc(p.text)}</span>`).join('')}</td></tr>` : ''}`).join('')}</tbody></table></div>`;
  }

  // ------------------------------------------------------------------ Rules
  function rules() {
    const f = OV.rules;
    return `<p class="ddk-about">Every date, rate and limit this employee uses is kept as data with where it came from and when it was checked. This year the GST slabs, the GSTR-3B locks, the Income-tax Act and the PF ceiling all changed - a remembered number would already be wrong.</p>
      <div class="ddk-tiles">${Object.entries(f.by_basis).map(([b, n]) => `<div class="ddk-tile${b === 'unverified' && n ? ' acd-warn' : ''}"><span>${esc(BASIS[b] || b)}</span><b>${n}</b></div>`).join('')}</div>
      ${f.unverified.length ? `<section class="ddk-card acd-sec"><h2 class="ddk-h3">Shown as a warning only (${f.unverified.length})</h2><p class="ddk-fine first">These could not be read on a government page from here. Hoola shows them, never computes a tax or a penalty from them, until each is checked.</p>
        <ul class="acd-rl">${f.unverified.map(r => `<li><b>${esc(r.what)}</b><small>${esc(r.file)} · checked ${esc(r.checked_on)} · ${esc(r.source)}</small></li>`).join('')}</ul></section>` : ''}
      ${f.stale.length ? `<section class="ddk-card acd-sec"><h2 class="ddk-h3">Due for a re-check (${f.stale.length})</h2><ul class="acd-rl">${f.stale.map(r => `<li><b>${esc(r.what)}</b><small>review by ${esc(r.review_by)}</small></li>`).join('')}</ul></section>` : ''}
      <section class="ddk-card acd-sec"><h2 class="ddk-h3">The rule files</h2><ul class="acd-rl">${f.files.map(x => `<li><b>${esc(x.name.replace('_', ' '))}</b><small>${x.rows} rows · ${esc(x.about)}</small></li>`).join('')}</ul></section>`;
  }

  // ------------------------------------------------------------------ Bills in, checked
  function blTab() {
    const c = OV.connections[0];
    const head = `<section class="ddk-card"><h2 class="ddk-h3">Bills in, checked</h2>
      <p class="ddk-fine first">Paste the text of a purchase bill (or give the id of a file you sent in chat). Hoola reads it, checks the numbers, the supplier's GSTIN and whether it is already in your books, and makes a <b>draft</b>. It enters your register only when you confirm.</p>
      <div class="acd-row"><input id="acdBG" class="acd-in" placeholder="Your GSTIN" maxlength="15" value="${esc(c ? c.gstin : '')}"><input id="acdBF" class="acd-in" placeholder="File id from chat (optional)"></div>
      <textarea id="acdBT" class="acd-in" rows="5" style="width:100%;height:auto;padding:10px" placeholder="Paste the bill text here"></textarea>
      <div class="acd-row"><button type="button" class="btn go ddk-mid" data-a="blread">Read + check</button><button type="button" class="btn ddk-mid" data-a="blrefresh">Show drafts</button></div></section>`;
    if (!BL) return head;
    const F = [['supplier_gstin', 'Supplier GSTIN'], ['number', 'Invoice no.'], ['date', 'Date (YYYY-MM-DD)'], ['taxable', 'Taxable'], ['cgst', 'CGST'], ['sgst', 'SGST'], ['igst', 'IGST'], ['total', 'Total']];
    const cards = BL.map(b => `<section class="ddk-card acd-sec"><div class="acd-cardhd"><h3 class="ddk-h3">${esc(b.fields.party_name || 'Bill')} · ${esc(b.fields.number || 'no number')}</h3>
        <span class="ddk-pill ${b.state === 'ready' ? 'ok' : 'warn'}">${b.state === 'ready' ? 'looks right' : 'needs you'} · ${Math.round(b.confidence * 100)}%</span></div>
      <ul class="acd-kv">${b.checks.map(x => `<li><span>${esc(x.text)}</span><span class="ddk-pill ${x.level === 'error' ? 'warn' : 'mute'}">${esc(x.level)}</span></li>`).join('') || '<li><span>Every check passed.</span></li>'}</ul>
      <div class="acd-row">${F.map(([k, l]) => `<input class="acd-in" data-b="${esc(b.id)}" data-k="${k}" title="${l}" placeholder="${l}" value="${esc(b.fields[k] || '')}">`).join('')}</div>
      <div class="acd-row"><button type="button" class="btn go ddk-mid" data-a="blconfirm" data-i="${esc(b.id)}">Add to my register</button><button type="button" class="btn ddk-mid" data-a="blreject" data-i="${esc(b.id)}">Throw away</button></div></section>`).join('');
    return head + (cards || '<p class="ddk-quiet">No drafts waiting.</p>');
  }

  // ------------------------------------------------------------------ e-Invoice + e-way bill
  function eiTab() {
    const c = OV.connections[0];
    const g = (EI && EI.g) || (c ? c.gstin : '');
    const head = `<section class="ddk-card"><h2 class="ddk-h3">e-Invoice (IRN) and e-way bill</h2>
      <p class="ddk-fine first">Hoola builds the e-invoice from a sales bill, shows you exactly what is missing, and asks the government portal for the IRN only when you confirm. A mistake can be cancelled only within 24 hours. Your portal password is kept sealed and shown nowhere.</p>
      <div class="acd-row"><input id="acdEG" class="acd-in" placeholder="Your GSTIN" maxlength="15" value="${esc(g)}"><button type="button" class="btn go ddk-mid" data-a="eilist">Show my invoices</button></div></section>`;
    const conn = EI && EI.st && EI.st.connected ? `<p class="ddk-fine">Connected as <b>${esc(EI.st.username)}</b>.</p>` : `<section class="ddk-card acd-sec"><h3 class="ddk-h3">Connect your e-invoice login</h3>
      <div class="acd-row"><input id="acdEU" class="acd-in" placeholder="e-invoice portal username" autocomplete="off"><input id="acdEP" class="acd-in" type="password" placeholder="e-invoice portal password" autocomplete="off"></div>
      <div class="acd-row"><input id="acdEN" class="acd-in" placeholder="Your business legal name"><input id="acdEA" class="acd-in" placeholder="Address line"><input id="acdEL" class="acd-in" placeholder="City"><input id="acdEZ" class="acd-in" placeholder="Pincode" maxlength="6"></div>
      <div class="acd-row"><button type="button" class="btn go ddk-mid" data-a="eiconn">Connect</button></div></section>`;
    if (!EI || !EI.data) return head + (EI && EI.st ? conn : '');
    const d = EI.data;
    const irn = d.irns.map(r => `<li><span><b>${esc(r.doc_no)}</b> ${esc(r.status)}${r.irn ? ' · IRN ' + esc(r.irn.slice(0, 12)) + '…' : ''}${r.ewb_no ? ' · e-way bill ' + esc(r.ewb_no) : ''}${r.error ? ' - ' + esc(r.error) : ''}</span>
      <span>${r.status === 'generated' && !r.ewb_no ? `<button type="button" class="btn ddk-mid" data-a="eiewb" data-i="${esc(r.id)}">e-way bill</button>` : ''}
      ${r.status === 'generated' && r.cancel_hours_left ? `<button type="button" class="btn ddk-mid" data-a="eicancel" data-i="${esc(r.id)}">Cancel (${r.cancel_hours_left}h left)</button>` : ''}</span></li>`).join('');
    const w = d.watch.map(x => `<li><span><b>${esc(x.number)}</b> ${esc(x.date)} · ${esc(x.party || '')} · ${inr(x.total)}${x.days_left != null ? ` · <b>${x.days_left} days left</b> for the IRN` : ''}</span><button type="button" class="btn go ddk-mid" data-a="eibuild" data-d="${esc(x.doc_id)}">Check + make IRN</button></li>`).join('');
    const pv = EI.pv ? (EI.pv.ready ? `<p class="ddk-note">Ready: ${esc(EI.pv.doc.type)} ${esc(EI.pv.doc.number)} to ${esc(EI.pv.doc.party)}, total ${inr(EI.pv.doc.total)}. <button type="button" class="btn go ddk-mid" data-a="eigen" data-d="${esc(EI.pv.doc.id)}" data-h="${esc(EI.pv.plan_hash)}">Confirm - ask the portal for the IRN</button></p>`
      : `<div class="ddk-note">Needed first: ${EI.pv.missing.map(esc).join('; ')}.<div class="acd-row"><input id="acdXH" class="acd-in" placeholder="HSN code"><input id="acdXA" class="acd-in" placeholder="Customer address"><input id="acdXL" class="acd-in" placeholder="Customer city"><input id="acdXP" class="acd-in" placeholder="Customer pincode" maxlength="6"><button type="button" class="btn ddk-mid" data-a="eibuild" data-d="${esc(EI.pv.doc.id)}" data-x="1">Check again</button></div></div>`) : '';
    return head + conn + `<section class="ddk-card acd-sec"><h3 class="ddk-h3">Waiting for an IRN (${d.watch.length})</h3>${w ? `<ul class="acd-kv">${w}</ul>` : '<p class="ddk-quiet">Nothing waiting.</p>'}${pv}</section>
      <section class="ddk-card acd-sec"><h3 class="ddk-h3">Issued</h3>${irn ? `<ul class="acd-kv">${irn}</ul>` : '<p class="ddk-quiet">None yet.</p>'}</section>`;
  }

  // ------------------------------------------------------------------ GSTR-3B
  function g3Tab() {
    const c = OV.connections[0], live = c && c.status === 'connected';
    const prev = new Date(); prev.setDate(1); prev.setMonth(prev.getMonth() - 1);
    const per = (G3 && G3.per) || `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`;
    const head = `<section class="ddk-card"><h2 class="ddk-h3">GSTR-3B and payment</h2>
      <p class="ddk-fine first">Hoola counts your tax and your credit (from the 2B you pulled and the decisions you made), uses credit first so you pay the least cash, and adds interest and late fee if any. You confirm each step on the portal. Hoola never creates the challan or moves money - you pay at your bank. ${OV.filing ? '' : 'Filing from Hoola is switched off on this server; file the saved draft on the GST portal.'}</p>
      <div class="acd-row"><input id="acdG3G" class="acd-in" placeholder="Your GSTIN" maxlength="15" value="${esc(c ? c.gstin : '')}"><input id="acdG3P" class="acd-in" type="month" value="${esc(per)}">
        <button type="button" class="btn go ddk-mid" data-a="g3prep">Prepare</button></div></section>`;
    if (!G3 || !G3.data) return head;
    const d = G3.data, s = d.summary, ct = d.cash_to_pay;
    const ck = d.checks.length ? `<ul class="acd-kv">${d.checks.map(x => `<li><span>${esc(x)}</span></li>`).join('')}</ul>` : '<p class="ddk-quiet">Nothing to fix.</p>';
    const cmp = G3.cmp ? (G3.cmp.compared ? `<ul class="acd-kv">${G3.cmp.rows.map(r => `<li><span>${esc(r.head.toUpperCase())}: Hoola ${inr(r.hoola)} · portal ${inr(r.portal)}${r.cause ? ' - ' + esc(r.cause) : ''}</span><span class="ddk-pill ${Math.abs(r.diff) > 1 ? 'warn' : 'ok'}">${Math.abs(r.diff) > 1 ? 'differs' : 'same'}</span></li>`).join('')}</ul>` : `<p class="ddk-note">${esc(G3.cmp.note)}</p>`) : '';
    const pay = G3.pay ? `<p class="ddk-note">Pay at your bank: <b>${inr(G3.pay.pay_at_bank)}</b>. ${esc(G3.pay.how)}</p>` : '';
    return head + `<section class="ddk-card acd-sec"><h2 class="ddk-h3">${esc(d.period)}</h2>
      <div class="ddk-nums"><div><b>${inr(s.liability)}</b><span>tax to pay in all</span></div><div><b>${inr(s.itc)}</b><span>credit used</span></div><div><b>${inr(ct.total)}</b><span>cash (tax + interest + fee)</span></div></div>
      ${ck}${cmp}${pay}
      <div class="acd-row">${live ? `<button type="button" class="btn ddk-mid" data-a="g3cmp">Compare with the portal</button>
        <button type="button" class="btn go ddk-mid" data-a="g3save" data-h="${esc(d.plan_hash)}">Save draft on the portal</button>
        <button type="button" class="btn go ddk-mid" data-a="g3off" data-h="${esc(d.plan_hash)}">Use my credit (set-off)</button>
        <button type="button" class="btn ddk-mid" data-a="g3pay">What do I pay at the bank?</button>` : '<span class="ddk-fine">Connect first (Connection tab).</span>'}</div>
      ${OV.filing ? `<div class="acd-row"><input id="acdG3Pan" class="acd-in" placeholder="Signatory PAN" maxlength="10"><button type="button" class="btn ddk-mid" data-a="g3otp">Send EVC OTP</button>
        <input id="acdG3Otp" class="acd-in" placeholder="OTP" inputmode="numeric" maxlength="8" autocomplete="one-time-code"><button type="button" class="btn go ddk-mid" data-a="g3file" data-h="${esc(d.plan_hash)}">File GSTR-3B</button></div>` : ''}
    </section>`;
  }

  // ------------------------------------------------------------------ GSTR-1
  function g1Tab() {
    const c = OV.connections[0], live = c && c.status === 'connected';
    const prev = new Date(); prev.setDate(1); prev.setMonth(prev.getMonth() - 1);
    const per = (G1 && G1.per) || `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`;
    const head = `<section class="ddk-card"><h2 class="ddk-h3">GSTR-1 for the month</h2>
      <p class="ddk-fine first">Hoola builds the return from your bills, then checks it against every record you keep: invoices it would miss, a customer GSTIN that is wrong, a rate that is not a slab on that date. Saving puts a <b>draft</b> on the GST portal - it is not filed. ${OV.filing ? 'Filing uses your EVC OTP.' : 'Filing from Hoola is switched off on this server; file the saved draft on the GST portal.'}</p>
      <div class="acd-row"><input id="acdG1G" class="acd-in" placeholder="Your GSTIN" maxlength="15" value="${esc(c ? c.gstin : '')}"><input id="acdG1P" class="acd-in" type="month" value="${esc(per)}">
        <button type="button" class="btn go ddk-mid" data-a="g1prep">Build + check</button></div></section>`;
    if (!G1 || !G1.data) return head;
    const d = G1.data, s = d.summary || {};
    const ck = d.checks.length ? `<ul class="acd-kv">${d.checks.map(x => `<li><span>${esc(x.text)}</span><span class="ddk-pill ${x.kind === 'engine' ? 'mute' : 'warn'}">${esc(x.kind.replace('_', ' '))}</span></li>`).join('')}</ul>` : '<p class="ddk-quiet">Nothing to fix.</p>';
    return head + `<section class="ddk-card acd-sec"><h2 class="ddk-h3">${esc(d.period)} · ${s.b2b_invoices || 0} B2B invoices, ${s.b2cs_rows || 0} B2C lines</h2>
      <div class="ddk-nums"><div><b>${inr(s.txval)}</b><span>taxable value</span></div><div><b>${inr(s.tax)}</b><span>tax</span></div><div><b>${d.checks.length}</b><span>things to look at</span></div></div>
      ${ck}
      <div class="acd-row">${live ? `<button type="button" class="btn go ddk-mid" data-a="g1save" data-h="${esc(d.plan_hash)}">Save as draft on the GST portal</button>` : '<span class="ddk-fine">Connect first (Connection tab) to save a draft.</span>'}</div>
      ${G1.saved ? `<p class="ddk-note">Draft saved (reference ${esc(G1.saved.reference || '-')}). ${esc(G1.saved.validate_hsn || '')}</p>` : ''}
      ${OV.filing && G1.saved ? `<div class="acd-row"><input id="acdG1Pan" class="acd-in" placeholder="Signatory PAN" maxlength="10"><button type="button" class="btn ddk-mid" data-a="g1otp">Send EVC OTP</button>
        <input id="acdG1Otp" class="acd-in" placeholder="OTP" inputmode="numeric" maxlength="8" autocomplete="one-time-code"><button type="button" class="btn go ddk-mid" data-a="g1file" data-h="${esc(d.plan_hash)}">File GSTR-1</button></div>` : ''}
    </section>`;
  }

  // ------------------------------------------------------------------ Credit (ITC)
  function itcTab() {
    const c = OV.connections[0], live = c && c.status === 'connected';
    const prev = new Date(); prev.setDate(1); prev.setMonth(prev.getMonth() - 1);
    const per = (ITC && ITC.per) || `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`;
    const head = `<section class="ddk-card"><h2 class="ddk-h3">Monthly credit check</h2>
      <p class="ddk-fine first">Hoola reads your GSTR-2B for the month, matches it with your purchases and suggests accept / pending / reject with a reason. You decide. Nothing reaches the GST portal until you confirm the exact list.</p>
      ${live ? '' : '<p class="ddk-note">Not connected right now - open Connection and get an OTP first.</p>'}
      <div class="acd-row"><input id="acdItcG" class="acd-in" placeholder="Your GSTIN" maxlength="15" value="${esc(c ? c.gstin : '')}"><input id="acdItcP" class="acd-in" type="month" value="${esc(per)}">
        <button type="button" class="btn go ddk-mid" data-a="itcpull">Read 2B + suggest</button></div></section>`;
    if (!ITC || !ITC.data) return head;
    const d = ITC.data, o = {accept: 'Accept', pending: 'Pending', reject: 'Reject', '': '-'};
    const rows = d.rows.map(r => `<tr class="${r.applied ? 'acd-gone' : ''}"><td>${esc(r.supplier)}<span class="acd-dir">${esc(r.ctin)}</span></td><td>${esc(r.number)}<span class="acd-dir">${esc(r.date)}</span></td><td>${inr(r.tax)}</td>
      <td><b>${esc(o[r.proposal] || 'No action')}</b><span class="acd-dir">${esc(r.reason)}</span></td>
      <td>${r.proposal === 'none' || r.applied ? (r.applied ? 'Sent' : '') : `<select data-i="${esc(r.id)}">${['', 'accept', 'pending', 'reject'].map(a => `<option value="${a}"${(r.decided || '') === a ? ' selected' : ''}>${o[a]}</option>`).join('')}</select>`}</td></tr>`).join('');
    const g = d.groups;
    const miss = d.missing_in_2b.map(m => `<li><b>${esc(m.supplier)}</b> ${esc(m.number)} · ${inr(m.tax)} <a href="${esc(m.nudge.wa_link)}" target="_blank" rel="noopener">Open WhatsApp draft</a></li>`).join('');
    return head + `<section class="ddk-card acd-sec"><div class="acd-cardhd"><h2 class="ddk-h3">${d.rows.length} invoices in 2B</h2>
        <span class="ddk-fine">${g.accept.count} accept · ${g.pending.count} pending · ${g.reject.count} reject</span></div>
      <div class="ddk-tbl"><table><thead><tr><th>Supplier</th><th>Invoice</th><th>Tax</th><th>Hoola suggests</th><th>Your decision</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="acd-row"><button type="button" class="btn ddk-mid" data-a="itcsuggest">Use all suggestions</button><button type="button" class="btn ddk-mid" data-a="itcsave">Save my decisions</button>
        <button type="button" class="btn go ddk-mid" data-a="itcpreview">Review what will be sent</button></div>
      ${PV ? `<p class="ddk-note">${PV.will_send} decisions ready (${PV.counts.accept} accept, ${PV.counts.pending} pending, ${PV.counts.reject} reject). <button type="button" class="btn go ddk-mid" data-a="itcapply" data-h="${esc(PV.plan_hash)}">Confirm and send to the GST portal</button></p>` : ''}
    </section>
    ${d.missing_in_2b.length ? `<section class="ddk-card acd-sec"><h2 class="ddk-h3">Bought, but not in 2B (${inr(d.itc_at_stake_missing)} credit waiting)</h2><ul class="acd-kv">${miss}</ul><p class="ddk-fine">Hoola only drafts the message - you pick the contact and send it.</p></section>` : ''}`;
  }

  // ------------------------------------------------------------------ Connection
  function connection() {
    const w = OV.whitebooks, lc = w.last_check;
    const prod = {gst: 'GST returns', einv: 'e-invoice', ewb: 'e-way bill'};
    return `<div class="acd-grid">
      <section class="ddk-card"><div class="acd-cardhd"><h2 class="ddk-h3">WhiteBooks (GST provider)</h2><span class="ddk-pill ${w.env === 'production' ? 'warn' : 'mute'}">${w.env === 'production' ? 'Production' : 'Sandbox'}</span></div>
        <ul class="acd-kv">${Object.entries(w.products).map(([p, ok]) => `<li><span>${esc(prod[p] || p)}</span>${ok ? '<span class="ddk-pill ok">Keys set</span>' : '<span class="ddk-pill mute">Not set</span>'}</li>`).join('')}
          <li><span>Calls today</span><b>${w.calls_today}${w.daily_cap ? ' / ' + w.daily_cap : ''}</b></li></ul>
        ${w.products.gst ? '' : `<p class="ddk-fine">Put the WhiteBooks keys in the server's <code>.env</code> (never in chat) with these names, then restart:</p><pre class="ddk-pre">${esc(w.env_lines.join('\n'))}</pre>`}
      </section>
      <section class="ddk-card"><div class="acd-cardhd"><h2 class="ddk-h3">Last contract check</h2>${lc ? `<span class="ddk-fine first">${esc(new Date(lc.at).toLocaleString('en-IN'))}</span>` : ''}</div>
        ${lc ? `<ul class="acd-steps">${lc.steps.map(s => `<li class="${s.result.toLowerCase()}"><b>${esc(s.result)}</b><span>${esc(s.step.replace('_', ' '))}</span><small>${esc(s.line)}</small></li>`).join('')}</ul>`
            : '<p class="ddk-quiet">Not run yet. Run Actions → VPS ops → <b>wb_check</b> once the sandbox keys are in place.</p>'}
        <p class="ddk-fine">The check walks every call on the WhiteBooks sandbox and records the shape of each reply - never a value. Production checks never ask for an OTP.</p>
      </section></div>
      <section class="ddk-card acd-sec"><h2 class="ddk-h3">Your GSTIN</h2>
        ${OV.connections.length ? `<ul class="acd-kv">${OV.connections.map(c => `<li><span><code>${esc(c.gstin)}</code></span><span class="ddk-pill ${c.status === 'connected' ? 'ok' : 'mute'}">${esc(c.status)}</span></li>`).join('')}</ul>` : ''}
        ${connectForm()}
        <h3 class="ddk-h3" style="margin-top:18px">Check a supplier</h3>
        <p class="ddk-fine first">No OTP needed. Active or cancelled, and whether they filed.</p>
        <div class="acd-row"><input id="acdSup" class="acd-in" placeholder="Supplier GSTIN" maxlength="15" autocomplete="off"><button type="button" class="btn ddk-mid" data-a="supcheck">Check</button></div>
        <div id="acdSupOut" class="ddk-fine" aria-live="polite"></div>
      </section>`;
  }

  function connectForm() {
    const c = OV.connections[0];
    const live = c && c.status === 'connected';
    const sent = c && c.status === 'otp_sent';
    return `<p class="ddk-fine first">${live ? 'Connected until ' + esc(new Date(c.enabled_until).toLocaleString('en-IN')) + '.' : 'Turn on API access once on the GST portal (My Profile → Manage API Access), then Hoola asks the portal to send you an OTP. Your portal password is never asked for, and nothing is filed from here.'}</p>
      <div class="acd-row">
        <input id="acdGstin" class="acd-in" placeholder="Your GSTIN" maxlength="15" value="${esc(c ? c.gstin : '')}" autocomplete="off">
        <input id="acdUser" class="acd-in" placeholder="GST portal username" value="${esc(c ? c.gst_username : '')}" autocomplete="off">
        ${sent ? `<input id="acdOtp" class="acd-in" placeholder="OTP" inputmode="numeric" maxlength="8" autocomplete="one-time-code"><button type="button" class="btn ddk-mid" data-a="cverify">Connect</button>` : ''}
        <button type="button" class="btn ddk-mid" data-a="cstart">${sent ? 'Send OTP again' : live ? 'New OTP' : 'Send me an OTP'}</button>
        ${live ? '<button type="button" class="btn ddk-mid" data-a="crefresh">Refresh</button><button type="button" class="btn ddk-mid" data-a="cdisc">Disconnect</button>' : ''}
      </div>`;
  }
  const val = id => (EL.querySelector('#' + id)?.value || '').trim();

  // ------------------------------------------------------------------ Plan
  function plan() {
    return `<p class="ddk-about">Built one step at a time; each step ships with its tests. Filing is always on your OTP and money always moves at your bank.</p>
      <ol class="acd-plan">${OV.phases.map(p => `<li class="${esc(p.state)}"><span class="acd-ph">${esc(p.id)}</span><div><b>${esc(p.name)}</b><small>${esc(p.what)}</small></div><span class="ddk-pill ${p.state === 'built' ? 'ok' : p.state === 'next' ? 'warn' : 'mute'}">${p.state === 'built' ? 'Built' : p.state === 'next' ? 'Next' : 'Planned'}</span></li>`).join('')}</ol>`;
  }

  // ------------------------------------------------------------------ events
  function bind(el) {
    if (el._acd) return; el._acd = true;
    el.addEventListener('click', async ev => {
      const b = ev.target.closest('[data-a]'); if (!b || !el.contains(b)) return;
      const a = b.dataset.a;
      if (a === 'hub') { open?.('hire'); return; }
      if (a === 'tab') { TAB = b.dataset.t; draw(false); if (TAB === 'register') loadRegister(); return; }
      if (a === 'hire') { try { await api('POST', '/api/employees/accounts/hire', {trust: 'seekh'}); toast('Hired. Its desk stays here.'); } catch (e) { toast(e.message, true); } load(false); return; }
      if (a === 'cstart' || a === 'cverify' || a === 'crefresh' || a === 'cdisc') {
        const g = val('acdGstin').toUpperCase();
        try {
          const r = a === 'cstart' ? await api('POST', '/api/bahi/connect/start', {gstin: g, gst_username: val('acdUser')})
            : a === 'cverify' ? await api('POST', '/api/bahi/connect/verify', {gstin: g, otp: val('acdOtp')})
            : a === 'crefresh' ? await api('POST', '/api/bahi/connect/refresh', {gstin: g})
            : await api('POST', '/api/bahi/connect/disconnect', {gstin: g});
          toast(r.message || (a === 'cverify' ? 'Connected.' : 'Done.'));
        } catch (e) { toast(e.message, true); }
        await load(false); return;
      }
      if (a === 'supcheck') {
        const out = EL.querySelector('#acdSupOut'); out.textContent = 'Checking...';
        try {
          const r = await api('POST', '/api/bahi/supplier-check', {gstin: val('acdSup').toUpperCase()});
          const f = r.filing ? ` Filing ${esc(r.filing.fy)}: ${r.filing.returns.length ? r.filing.returns.slice(0, 6).map(x => esc(x.form + ' ' + x.period + ' ' + x.status)).join(', ') : 'nothing listed'}.` : '';
          out.innerHTML = `<b>${esc(r.status)}</b> ${esc(r.legal_name)} <small>(${esc(r.source || 'no source')})</small>.${f} ${r.notes.map(esc).join(' ')}`;
        } catch (e) { out.textContent = e.message; }
        return;
      }
      if (a.startsWith('bl')) {
        try {
          const refresh = async () => { BL = (await api('GET', '/api/bahi/bills?status=draft')).bills; draw(false); };
          if (a === 'blrefresh') { await refresh(); return; }
          if (a === 'blread') {
            const fid = val('acdBF');
            await api('POST', '/api/bahi/bills/intake', fid ? {gstin: val('acdBG').toUpperCase(), file_id: fid} : {gstin: val('acdBG').toUpperCase(), text: val('acdBT')});
            await refresh(); return;
          }
          if (a === 'blreject') { await api('POST', `/api/bahi/bills/${encodeURIComponent(b.dataset.i)}/reject`, {}); await refresh(); return; }
          if (a === 'blconfirm') {
            const ov = {}; EL.querySelectorAll(`input[data-b="${b.dataset.i}"]`).forEach(i => { ov[i.dataset.k] = i.value; });
            try { await api('POST', `/api/bahi/bills/${encodeURIComponent(b.dataset.i)}/confirm`, {overrides: ov}); toast('Added to your register.'); await refresh(); return; }
            catch (e) {
              if (!/^Fix first/.test(e.message) || !confirm(e.message + '\n\nAdd it anyway? This is recorded as accepted by you.')) throw e;
              await api('POST', `/api/bahi/bills/${encodeURIComponent(b.dataset.i)}/confirm`, {overrides: ov, accept_errors: true}); toast('Added, with the problems recorded.'); await refresh(); return;
            }
          }
        } catch (e) { toast(e.message, true); }
        return;
      }
      if (a.startsWith('ei')) {
        const g = val('acdEG').toUpperCase() || (EI && EI.g) || '';
        try {
          const reload = async () => { EI = {...(EI || {}), g, st: await api('GET', `/api/bahi/einv/status?gstin=${encodeURIComponent(g)}`), data: await api('GET', `/api/bahi/einv/list?gstin=${encodeURIComponent(g)}`)}; draw(false); };
          if (a === 'eilist') { EI = {g, pv: null}; await reload(); return; }
          if (a === 'eiconn') {
            await api('POST', '/api/bahi/einv/connect', {gstin: g, username: val('acdEU'), password: val('acdEP'),
              seller: {LglNm: val('acdEN'), Addr1: val('acdEA'), Loc: val('acdEL'), Pin: val('acdEZ')}});
            toast('Connected.'); await reload(); return;
          }
          const extra = b.dataset.x ? {hsn: val('acdXH'), buyer_addr1: val('acdXA'), buyer_loc: val('acdXL'), buyer_pin: val('acdXP')} : {};
          if (a === 'eibuild') { EI.pv = await api('POST', '/api/bahi/einv/build', {gstin: g, doc_id: b.dataset.d, extra}); EI.extra = extra; draw(false); return; }
          if (a === 'eigen') {
            if (!confirm('Ask the government portal for the IRN now? It can be cancelled only within 24 hours.')) return;
            const r = await api('POST', '/api/bahi/einv/generate', {gstin: g, doc_id: b.dataset.d, extra: EI.extra || {}, plan_hash: b.dataset.h, confirm: true});
            toast(r.adopted ? 'The portal had already issued it - adopted.' : 'IRN issued.'); EI.pv = null; await reload(); return;
          }
          if (a === 'eicancel') {
            if (!confirm('Cancel this IRN? This is permanent.')) return;
            await api('POST', '/api/bahi/einv/cancel', {irn_id: b.dataset.i, reason: '2', remark: 'Data entry mistake', confirm: true}); toast('IRN cancelled.'); await reload(); return;
          }
          if (a === 'eiewb') {
            const dist = prompt('Distance in km?'); if (!dist) return;
            const veh = prompt('Vehicle number (or leave empty and give the transporter GSTIN next)') || '';
            const tr = veh ? '' : (prompt('Transporter GSTIN') || '');
            await api('POST', '/api/bahi/einv/ewb', {irn_id: b.dataset.i, transport: {distance: dist, vehicle_no: veh, transporter_gstin: tr}, confirm: true});
            toast('e-way bill made.'); await reload(); return;
          }
        } catch (e) { toast(e.message, true); }
        return;
      }
      if (a.startsWith('g3')) {
        const g = val('acdG3G').toUpperCase(), p = val('acdG3P');
        try {
          if (a === 'g3prep') { const data = await api('POST', '/api/bahi/gstr3b/prepare', {gstin: g, period: p}); G3 = {per: p, g, data}; draw(false); return; }
          const k = {gstin: G3.g, period: G3.per};
          if (a === 'g3cmp') { G3.cmp = await api('POST', '/api/bahi/gstr3b/compare', k); draw(false); return; }
          if (a === 'g3pay') { G3.pay = await api('POST', '/api/bahi/gstr3b/payment', k); draw(false); return; }
          if (a === 'g3save') { if (!confirm('Put this GSTR-3B on your GST portal as a draft? It is not filed.')) return;
            await api('POST', '/api/bahi/gstr3b/save', {...k, plan_hash: b.dataset.h, confirm: true}); toast('Draft saved on the portal. Not filed.'); return; }
          if (a === 'g3off') { if (!confirm('Use your credit against this liability on the portal? This cannot be undone.')) return;
            const r = await api('POST', '/api/bahi/gstr3b/setoff', {...k, plan_hash: b.dataset.h, confirm: true}); toast(`Credit used. Cash still to pay: ${inr(r.cash_still_to_pay)}.`); return; }
          if (a === 'g3otp') { const r = await api('POST', '/api/bahi/gstr3b/evc-otp', {gstin: G3.g, pan: val('acdG3Pan')}); toast(r.message); return; }
          if (a === 'g3file') { if (!confirm('File GSTR-3B now? Filing is final.')) return;
            const r = await api('POST', '/api/bahi/gstr3b/file', {...k, pan: val('acdG3Pan'), otp: val('acdG3Otp'), plan_hash: b.dataset.h, confirm: true}); toast(`Filed. ${r.portal_status || ''} ${r.next}`.trim()); return; }
        } catch (e) { toast(e.message, true); }
        return;
      }
      if (a.startsWith('g1')) {
        const g = val('acdG1G').toUpperCase(), p = val('acdG1P');
        try {
          if (a === 'g1prep') { const data = await api('POST', '/api/bahi/gstr1/prepare', {gstin: g, period: p}); G1 = {per: p, g, data}; draw(false); return; }
          if (a === 'g1save') {
            if (!confirm('Put this GSTR-1 on your GST portal as a draft? It is not filed.')) return;
            G1.saved = await api('POST', '/api/bahi/gstr1/save', {gstin: G1.g, period: G1.per, plan_hash: b.dataset.h, confirm: true});
            toast('Draft saved on the portal. Not filed.'); draw(false); return;
          }
          if (a === 'g1otp') { const r = await api('POST', '/api/bahi/gstr1/evc-otp', {gstin: G1.g, pan: val('acdG1Pan')}); toast(r.message); return; }
          if (a === 'g1file') {
            if (!confirm('File GSTR-1 now? Filing is final.')) return;
            const r = await api('POST', '/api/bahi/gstr1/file', {gstin: G1.g, period: G1.per, pan: val('acdG1Pan'), otp: val('acdG1Otp'), plan_hash: b.dataset.h, confirm: true});
            toast(`Filed. ${r.portal_status || ''} ${r.next}`.trim()); return;
          }
        } catch (e) { toast(e.message, true); }
        return;
      }
      if (a.startsWith('itc')) {
        const g = val('acdItcG').toUpperCase(), p = val('acdItcP');
        const key = {gstin: g, period: ITC?.per || p};
        try {
          if (a === 'itcpull') {
            await api('POST', '/api/bahi/itc/pull', {gstin: g, period: p});
            const data = await api('GET', `/api/bahi/itc/proposals?gstin=${encodeURIComponent(g)}&period=${encodeURIComponent(p)}`);
            ITC = {per: p, g, data}; PV = null; draw(false); return;
          }
          if (a === 'itcsuggest') { EL.querySelectorAll('select[data-i]').forEach(s => { const r = ITC.data.rows.find(x => x.id === s.dataset.i); if (r && ['accept', 'pending', 'reject'].includes(r.proposal)) s.value = r.proposal; }); return; }
          const chosen = {}; EL.querySelectorAll('select[data-i]').forEach(s => { if (s.value) chosen[s.dataset.i] = s.value; });
          if (a === 'itcsave' || a === 'itcpreview') {
            await api('POST', '/api/bahi/itc/decide', {gstin: ITC.g, period: ITC.per, decisions: chosen});
            if (a === 'itcpreview') PV = await api('GET', `/api/bahi/itc/preview?gstin=${encodeURIComponent(ITC.g)}&period=${encodeURIComponent(ITC.per)}`);
            ITC.data = await api('GET', `/api/bahi/itc/proposals?gstin=${encodeURIComponent(ITC.g)}&period=${encodeURIComponent(ITC.per)}`);
            toast(a === 'itcsave' ? 'Decisions saved. Nothing was sent.' : 'Review the list, then confirm.'); draw(false); return;
          }
          if (a === 'itcapply') {
            if (!confirm('Send these decisions to the GST portal now? This changes your IMS.')) return;
            const r = await api('POST', '/api/bahi/itc/apply', {gstin: ITC.g, period: ITC.per, plan_hash: b.dataset.h, confirm: true});
            toast(`Sent ${r.sent}. ${r.portal_status || ''} ${r.recompute === 'asked' ? '2B recompute asked.' : ''}`.trim());
            PV = null; ITC.data = await api('GET', `/api/bahi/itc/proposals?gstin=${encodeURIComponent(ITC.g)}&period=${encodeURIComponent(ITC.per)}`); draw(false); return;
          }
        } catch (e) { toast(e.message, true); }
        return;
      }
      if (a === 'sync') {
        BUSY = true; draw(false);
        try { const r = await api('POST', '/api/bahi/sync', {}); toast(`Register: ${r.added} added, ${r.changed} changed${r.held_locked ? `, ${r.held_locked} held (locked month)` : ''}${Object.keys(r.errors).length ? ' - some sources could not be read' : ''}.`, !!Object.keys(r.errors).length); }
        catch (e) { toast(e.message, true); }
        BUSY = false; await load(false); return;
      }
      if (a === 'lock') {
        const on = b.dataset.on === '1';
        if (on && !confirm(`Lock ${mname(F.period)}? Changes to it will be held as amendments for you to approve, never applied.`)) return;
        try { await api('POST', `/api/bahi/periods/${encodeURIComponent(F.period)}/lock`, {on}); toast(on ? 'Month locked.' : 'Month unlocked.'); } catch (e) { toast(e.message, true); }
        await load(false); return;
      }
    });
    el.addEventListener('change', ev => {
      const s = ev.target.closest('[data-f]'); if (!s) return;
      F[s.dataset.f] = s.value; REG = null; draw(false); loadRegister();
    });
  }

  return {open: el => { EL = el; bind(el); return load(true); }};
};
