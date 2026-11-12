/* v0.396 CONNECT: the screen where an enterprise system is actually joined.

   Everything the enterprise suite can do has existed since v0.358 and none of it could touch a real system,
   because there was nowhere to put a credential: the chat refuses a key on purpose (a secret typed into a
   conversation lives in the history, in the model's context and in any export of either). This is that place.

   Three things it does, and nothing else:
     1. joins her own system - address, environment, key -> POST /api/enterprise/<role>/endpoint, where the key
        is sealed server-side the moment it arrives and is never returned by any route;
     2. ASKS THE SYSTEM whether it works (read-only), and shows what it answered rather than a green tick -
        a 401 is not a 403, and a CSRF token that cannot be fetched means a write would fail later;
     3. shows her write runs, including the rows whose answer never arrived, which only she can settle.

   Every value from the server goes through esc(): a system's note, an error from her ERP and a row's reason
   are all data, never markup. The key is typed into a password field, sent once, and the field is cleared -
   the console never holds it and never asks for it again. */
window.HoolaEnterprise = function ({api, esc, toast}) {
  let ROLE = null, EL = null;
  const KINDS = [['bearer', 'Bearer token (OAuth)'], ['basic', 'Basic (user:pass, base64)'],
                 ['header', 'API key in a header']];
  // what each system wants in the address box, in her words - guessing the API URL is the commonest failure
  const HINT = {
    sap: 'https://<your-sap>/sap/opu/odata/sap/<SERVICE>  — ask your Basis team for the full OData service address',
    oracle: 'https://<account>.suitetalk.api.netsuite.com/services/rest/record/v1',
    salesforce: 'https://<your-org>.my.salesforce.com/services/data/v64.0',
    windchill: 'https://<your-windchill>/Windchill/servlet/odata  — if OAuth is on, use /Windchill/oauth/servlet/odata',
    teamcenter: 'Read-only for now; the real Siemens route is SOA and Hoola does not speak it',
    sheet: 'No address needed for a Sheet / CSV',
  };
  const when = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? '–' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const mark = v => v === true ? '<span class="tag ok">theek</span>'
                  : v === false ? '<span class="tag bad">nahi</span>'
                  : '<span class="tag">dhyan</span>';

  async function open(el, role) {
    EL = el; ROLE = role || 'erp';
    el.innerHTML = `<div class="vh"><h2>Systems</h2><span class="muted">Connect your own ERP / CRM. The key goes in here, never through chat.</span></div><div class="empty">Loading…</div>`;
    await draw();
  }

  async function draw() {
    let d;
    try { d = await api('GET', `/api/enterprise/${encodeURIComponent(ROLE)}/endpoint`); }
    catch (e) { EL.querySelector('.empty,.badc')?.remove(); EL.insertAdjacentHTML('beforeend', `<p class="badc">${esc(e.message)}</p>`); return; }
    const joined = d.systems || [], can = d.jod_sakte_hain || [];
    const byKey = {}; for (const s of joined) byKey[s.system] = s;
    let runs = [];
    try { runs = (await api('GET', `/api/enterprise/${encodeURIComponent(ROLE)}/runs`)).runs || []; } catch (e) { /* a missing run list must not hide the connect form */ }

    EL.innerHTML = `<div class="vh"><h2>Systems</h2><span class="muted">Connect your own ERP / CRM. The key goes in here, never through chat.</span></div>
      <div class="card ent-note"><b>Where the key goes</b><p class="muted">A key you enter here is encrypted the moment it arrives. No address returns it - not this screen, not the chat, not the AI. From then on you will see only the <code>${esc('••••')}</code> masked form.</p></div>
      ${can.map(sys => cardFor(sys, byKey[sys.system])).join('')}
      ${runsCard(runs)}`;
    wire();
  }

  function cardFor(sys, live) {
    const readOnly = sys.how === 'read_only';
    const noAddr = sys.system === 'sheet' || sys.how === 'own' && sys.system === 'composio';
    const head = `<div class="ent-head"><b>${esc(sys.label)}</b>
        ${live ? (live.verified ? '<span class="tag ok">jancha hua</span>' : '<span class="tag warn">juda, jancha nahi</span>') : '<span class="tag">juda nahi</span>'}
        ${readOnly ? '<span class="tag">sirf padhna</span>' : ''}
        ${live ? `<span class="tag ${live.env === 'production' ? 'bad' : ''}">${esc(live.env)}</span>` : ''}</div>
      <p class="muted">${esc(sys.note)}</p>`;
    if (noAddr) return `<div class="card ent-sys" data-sys="${esc(sys.system)}">${head}</div>`;
    const body = live
      ? `<table class="kv"><tr><td>Address</td><td><code>${esc(live.base_url)}</code></td></tr>
           <tr><td>Key</td><td><code>${esc(live.auth || '••••')}</code> <span class="muted">(seal ki hui)</span></td></tr></table>
         <div class="row">
           <button class="btn" data-act="verify" data-sys="${esc(sys.system)}">Check (writes nothing)</button>
           <button class="btn ghost" data-act="edit" data-sys="${esc(sys.system)}">Badliye</button>
           <button class="btn ghost bad" data-act="forget" data-sys="${esc(sys.system)}">Hataiye</button>
         </div><div class="ent-res" data-res="${esc(sys.system)}"></div>`
      : `<div class="row"><button class="btn" data-act="edit" data-sys="${esc(sys.system)}">Jodiye</button></div>
         <div class="ent-res" data-res="${esc(sys.system)}"></div>`;
    return `<div class="card ent-sys" data-sys="${esc(sys.system)}">${head}${body}
      <form class="ent-form" data-form="${esc(sys.system)}" hidden>
        <label>API ka address<input name="base_url" placeholder="https://…" value="${esc(live ? live.base_url : '')}" autocomplete="off"></label>
        <p class="muted small">${esc(HINT[sys.system] || 'System ka API address, https:// se')}</p>
        <label>Key kaisi hai<select name="auth_kind">${KINDS.map(([k, n]) => `<option value="${k}">${esc(n)}</option>`).join('')}</select></label>
        <label class="ent-hdr" hidden>Header ka naam<input name="header_name" placeholder="X-API-Key" autocomplete="off"></label>
        <label>Key / token<input name="auth" type="password" placeholder="${live ? 'Leave empty to keep it as it is' : 'Enter it here'}" autocomplete="new-password"></label>
        <label>Kaunsa system hai<select name="env"><option value="test">Test / sandbox</option><option value="production">PRODUCTION (asli)</option></select></label>
        <p class="muted small">Even with Production chosen, nothing is written without your approval - and the approval must include the word 'production'.</p>
        <div class="row"><button class="btn" type="submit">Save karke jaanchiye</button>
          <button class="btn ghost" type="button" data-act="cancel" data-sys="${esc(sys.system)}">Rehne dijiye</button></div>
      </form></div>`;
  }

  function runsCard(runs) {
    if (!runs.length) return '';
    return `<div class="card"><b>Likhne ke kaam</b>
      <table class="tbl"><thead><tr><th>Kaam</th><th>System</th><th>Haal</th><th>Hue</th><th>Kab</th><th></th></tr></thead><tbody>
      ${runs.map(r => `<tr><td>${esc(r.title || r.run)}</td><td>${esc(r.env || '')}</td>
        <td><span class="tag ${r.status === 'done' ? 'ok' : r.status === 'failed' ? 'bad' : 'warn'}">${esc(r.status)}</span></td>
        <td>${esc(String(r.hue || 0))} / ${esc(String(r.total || 0))}${r.fail ? ` <span class="badc">(${esc(String(r.fail))} fail)</span>` : ''}</td>
        <td>${esc(when(r.at))}</td>
        <td><button class="btn ghost small" data-act="run" data-run="${esc(r.run)}">Kholiye</button></td></tr>`).join('')}
      </tbody></table><div class="ent-run"></div></div>`;
  }

  // ------------------------------------------------------------ actions
  function wire() {
    EL.querySelectorAll('[data-act]').forEach(b => b.onclick = ev => {
      ev.preventDefault();
      const a = b.dataset.act, sys = b.dataset.sys;
      if (a === 'edit') return showForm(sys, true);
      if (a === 'cancel') return showForm(sys, false);
      if (a === 'verify') return verify(sys, b);
      if (a === 'forget') return forget(sys);
      if (a === 'run') return openRun(b.dataset.run);
    });
    EL.querySelectorAll('.ent-form').forEach(f => {
      const kind = f.querySelector('[name=auth_kind]'), hdr = f.querySelector('.ent-hdr');
      const sync = () => { hdr.hidden = kind.value !== 'header'; };
      kind.onchange = sync; sync();
      f.onsubmit = ev => { ev.preventDefault(); save(f.dataset.form, f); };
    });
  }

  function showForm(sys, on) {
    const f = EL.querySelector(`.ent-form[data-form="${CSS.escape(sys)}"]`);
    if (f) { f.hidden = !on; if (on) f.querySelector('[name=base_url]')?.focus(); }
  }

  async function save(sys, form) {
    const fd = new FormData(form);
    const body = {system: sys, base_url: String(fd.get('base_url') || '').trim(),
                  auth: String(fd.get('auth') || ''), auth_kind: String(fd.get('auth_kind') || 'bearer'),
                  env: String(fd.get('env') || 'test'), header_name: String(fd.get('header_name') || '')};
    if (!body.base_url) return toast('The API address is needed.');
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Saving…';
    try {
      await api('POST', `/api/enterprise/${encodeURIComponent(ROLE)}/endpoint`, body);
      form.querySelector('[name=auth]').value = '';     // never keep the key on the page
      toast('Connected. Checking now…');
      await draw();
      await verify(sys);
    } catch (e) { toast(e.message); }
    finally { btn.disabled = false; btn.textContent = 'Save karke jaanchiye'; }
  }

  async function verify(sys, btn) {
    const box = EL.querySelector(`[data-res="${CSS.escape(sys)}"]`);
    if (btn) { btn.disabled = true; btn.textContent = 'Checking…'; }
    if (box) box.innerHTML = '<p class="muted">Asking the system… (nothing will be written)</p>';
    try {
      const r = await api('POST', `/api/enterprise/${encodeURIComponent(ROLE)}/endpoint/${encodeURIComponent(sys)}/verify`);
      if (box) box.innerHTML = `<div class="ent-ver ${r.theek ? 'good' : 'bad'}">
        <b>${r.theek ? 'Working' : 'Not working yet'}</b>
        <table class="kv">${(r.jaanch || []).map(j => `<tr><td>${mark(j.theek)}</td><td>${esc(j.kya)}</td><td class="muted">${esc(j.kaha || '')}</td></tr>`).join('')}</table>
        <p class="muted">${esc(r.aage || '')}</p></div>`;
      if (r.theek) { toast('The system is connected and working.'); await draw(); }
    } catch (e) { if (box) box.innerHTML = `<p class="badc">${esc(e.message)}</p>`; }
    finally { if (btn) { btn.disabled = false; btn.textContent = 'Check (writes nothing)'; } }
  }

  async function forget(sys) {
    if (!confirm('This removes the address and key. Past work and papers stay as they are. Remove?')) return;
    try { await api('DELETE', `/api/enterprise/${encodeURIComponent(ROLE)}/endpoint/${encodeURIComponent(sys)}`); toast('Removed.'); await draw(); }
    catch (e) { toast(e.message); }
  }

  // ------------------------------------------------------------ a run, and the rows only she can settle
  async function openRun(id) {
    const box = EL.querySelector('.ent-run');
    if (!box) return;
    box.innerHTML = '<p class="muted">Loading…</p>';
    let r;
    try { r = await api('GET', `/api/enterprise/${encodeURIComponent(ROLE)}/run/${encodeURIComponent(id)}`); }
    catch (e) { box.innerHTML = `<p class="badc">${esc(e.message)}</p>`; return; }
    const unsure = r.pata_nahi || [], fails = r.jo_fail_hue || [];
    box.innerHTML = `<div class="card ent-run1"><b>${esc(r.title || r.run)}</b>
      <p class="muted">${esc(r.status)} · ${esc(String(r.hue || 0))} hue · ${esc(String(r.fail || 0))} fail · ${esc(String(r.baaki || 0))} baaki</p>
      ${unsure.length ? `<div class="ent-unsure"><b>These rows got no answer</b>
        <p class="muted">${esc(r.pata_nahi_kya_karein || 'These may already have been posted. Hoola will not send them again, to avoid posting twice. Check in the system and tell us.')}</p>
        <table class="tbl"><tbody>${unsure.map(u => `<tr><td>#${esc(String(u.n))}</td><td><code>${esc(u.key || '')}</code></td>
          <td class="muted">${esc(u.kyon || '')}</td>
          <td><button class="btn small" data-landed="1" data-n="${esc(String(u.n))}" data-run="${esc(r.run)}">It is in the system</button>
              <button class="btn small ghost" data-landed="0" data-n="${esc(String(u.n))}" data-run="${esc(r.run)}">Not sent - send again</button></td></tr>`).join('')}</tbody></table></div>` : ''}
      ${fails.length ? `<div><b>Jo fail hue</b><table class="tbl"><tbody>${fails.map(f => `<tr><td>#${esc(String(f.n))}</td><td><code>${esc(f.key || '')}</code></td><td class="muted">${esc(f.error || '')}</td></tr>`).join('')}</tbody></table></div>` : ''}
    </div>`;
    box.querySelectorAll('[data-landed]').forEach(b => b.onclick = async () => {
      b.disabled = true;
      try {
        await api('POST', `/api/enterprise/${encodeURIComponent(ROLE)}/run/${encodeURIComponent(b.dataset.run)}/resolve`,
                  {n: Number(b.dataset.n), landed: b.dataset.landed === '1'});
        toast(b.dataset.landed === '1' ? 'Row closed - nothing was sent.' : 'The row is back in the queue.');
        await openRun(b.dataset.run);
      } catch (e) { toast(e.message); b.disabled = false; }
    });
  }

  return {open, draw};
};
