/* v0.807 BAHI - the GST & Accounts desk (console). A0: the foundation, shown honestly.
   Tabs: Overview (this month's dates + figures + the trail), Register (every document once, from every engine), Rules (each with its
   source and the day it was checked), Connection (the WhiteBooks pipe - which keys are set, the last sandbox check; never a key),
   Plan (what is built and what comes next).
   Rules this page keeps: every server value goes through esc(); nothing here files, pays or shows a secret; a date the research could
   not confirm on a government page is SAID to be unconfirmed; motion = entrances once (BACKWARDS) + the hero drawing, nothing loops
   under text; styles reuse the Desk Room (`ddk-`) scale + a few `acd-` rules. */
'use strict';
window.HoolaBahi = function ({api, esc, toast, open, title}) {
  let EL = null, OV = null, TAB = 'overview', REG = null, F = {period: '', direction: '', source: ''}, BUSY = false;
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
      <div class="ddk-tabs acd-tabs" role="tablist">${[['overview', 'Overview'], ['register', 'Register'], ['rules', 'Rules'], ['connection', 'Connection'], ['plan', 'Plan']]
        .map(([k, n]) => `<button type="button" role="tab" data-a="tab" data-t="${k}" aria-selected="${TAB === k}">${n}</button>`).join('')}</div>
      <div class="acd-body">${TAB === 'register' ? register() : TAB === 'rules' ? rules() : TAB === 'connection' ? connection() : TAB === 'plan' ? plan() : overview()}</div>
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
        <p class="ddk-fine first">Connecting your GSTIN comes in the next step (A1): you switch on API access on the GST portal once, Hoola asks the portal to send you an OTP, you type it here. Your portal password is never asked for. You can see and cancel Hoola's access on the portal any time.</p></section>`;
  }

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
