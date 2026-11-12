/* v0.481 HOOLA SKILL DESK - the owner's surface over the learned skills (account menu > Skills,
   or /skills): the library with its usage, park/unpark, create/edit/delete, import/export,
   the Pack bazaar (the anonymised share shelf) and the Shares ledger (the curator's
   nominations - nothing leaves her tenant without her tap). Talks to /api/coder/skills*.
   Every server value goes through esc(). Server-only surface: the phone app is untouched. */
'use strict';
window.HoolaSkills = function ({api, esc, toast}) {
  let TAB = 'mine', SKILLS = [], PACKS = [], SHARES = null, Q = '';
  const when = iso => { if (!iso) return ''; const d = new Date(String(iso).slice(0, 10) || iso); return isNaN(d) ? '' : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); };
  const tag = (c, n) => `<span class="tag ${c}">${esc(n)}</span>`;

  async function reload() {
    try {
      const [a, b, c] = await Promise.all([
        api('GET', '/api/coder/skills'),
        api('GET', '/api/coder/skills/packs'),
        api('GET', '/api/coder/skills/shares')]);
      SKILLS = a.skills || []; PACKS = b.packs || []; SHARES = c;
    } catch (e) { toast(e.message || 'Skills did not open', true); SKILLS = []; }
  }

  /* ------------------------------------------------------------ the three tabs */
  function row(s) {
    const parked = s.enabled === false;
    return `<div class="skrow" style="border:1px solid var(--hair);border-radius:14px;padding:14px 16px;margin:10px 0;background:var(--glass2)">
      <div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap">
        <b style="font-size:15px">${esc(s.name)}</b>
        ${parked ? tag('warn', 'parked') : ''}
        <span style="color:var(--mut);font-size:13px;flex:1;min-width:160px">${esc(s.description || '')}</span>
        ${tag('', `${s.shown || 0} shown`)}${tag('', `${s.read || 0} read`)}${tag('', `${s.chars} chars`)}
      </div>
      <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center">
        <button class="btn soft" data-sk="read" data-n="${esc(s.name)}">Read</button>
        <button class="btn soft" data-sk="edit" data-n="${esc(s.name)}">Edit</button>
        <button class="btn soft" data-sk="toggle" data-n="${esc(s.name)}" data-on="${parked ? '1' : '0'}">${parked ? 'Unpark' : 'Park'}</button>
        <button class="btn soft" data-sk="del" data-n="${esc(s.name)}" style="color:var(--bad)">Delete</button>
        <span style="color:var(--mut);font-size:12px">${s.last_read ? 'last read ' + when(s.last_read) : 'never read yet'}</span>
      </div>
      <div data-body="${esc(s.name)}" hidden style="margin-top:10px"></div>
    </div>`;
  }

  function editor(s) {
    return `<div style="border:1px solid var(--hair);border-radius:14px;padding:14px 16px;margin:10px 0;background:var(--glass3)">
      <label style="font-size:12px;color:var(--mut)">name (lowercase-hyphenated)</label>
      <input data-f="name" value="${esc(s && s.name || '')}" ${s ? 'readonly' : ''} style="width:100%;border:1px solid var(--hair);border-radius:10px;padding:8px 10px;background:var(--bg);color:var(--ink)">
      <label style="font-size:12px;color:var(--mut)">description (<= 60 chars, one sentence)</label>
      <input data-f="desc" maxlength="60" value="${esc(s && s.description || '')}" style="width:100%;border:1px solid var(--hair);border-radius:10px;padding:8px 10px;background:var(--bg);color:var(--ink)">
      <label style="font-size:12px;color:var(--mut)">the instructions (markdown, <= 4000 chars)</label>
      <textarea data-f="body" rows="10" style="width:100%;border:1px solid var(--hair);border-radius:10px;padding:8px 10px;background:var(--bg);color:var(--ink);font-family:var(--mono,monospace);font-size:13px">${esc(s && s.body || '')}</textarea>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn go" data-sk="save" data-n="${esc(s && s.name || '')}">${s ? 'Save' : 'Create'}</button>
        <button class="btn soft" data-sk="cancel">Cancel</button>
      </div>
      <div data-err style="color:var(--bad);font-size:13px;margin-top:6px"></div>
    </div>`;
  }

  function mine() {
    const live = SKILLS.filter(s => s.enabled !== false).length;
    const head = `<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0 2px">
      ${tag('', `${SKILLS.length} skills`)}${tag('', `${live} live`)}
      ${tag('', `${SKILLS.reduce((a, s) => a + (s.read || 0), 0)} reads`)}
      <span style="flex:1"></span>
      <button class="btn soft" data-sk="new">New skill</button>
      <button class="btn soft" data-sk="import">Import</button>
      <button class="btn soft" data-sk="export">Export</button>
    </div>
    <input id="skq" placeholder="Search your skills…" value="${esc(Q)}" style="width:100%;max-width:420px;border:1px solid var(--hair);border-radius:10px;padding:8px 12px;background:var(--bg);color:var(--ink);margin:8px 0">`;
    const q = Q.trim().toLowerCase();
    const list = SKILLS.filter(s => !q || (s.name + ' ' + s.description).toLowerCase().includes(q));
    return head + (list.length ? list.map(row).join('')
      : `<p style="color:var(--mut);padding:18px 4px">${SKILLS.length ? 'Nothing matched.' : 'No skill has been learned yet - Santosh will write them (skill_manage), or you can Import.'}</p>`)
      + `<div id="skedit"></div>`;
  }

  function bazaar() {
    return `<p style="color:var(--mut);font-size:13px;margin:6px 0">Published by owners across Hoola, anonymous by construction — no tenant name travels with a pack.</p>`
      + (PACKS.length ? PACKS.map(p => `<div style="border:1px solid var(--hair);border-radius:14px;padding:14px 16px;margin:10px 0;background:var(--glass2)">
          <b>${esc(p.name)}</b> ${tag('', `${p.chars} chars`)}
          <div style="color:var(--mut);font-size:13px;margin:4px 0">${esc(p.description || '')}</div>
          <button class="btn soft" data-sk="packread" data-n="${esc(p.name)}">Read</button>
          <button class="btn go" data-sk="install" data-n="${esc(p.name)}">Install</button>
          <div data-body="${esc(p.name)}" hidden style="margin-top:10px"></div>
        </div>`).join('')
        : `<p style="color:var(--mut);padding:18px 4px">The shelf is empty - the first pack will be published from your Shares tab.</p>`);
  }

  function shares() {
    if (!SHARES) return '<p style="color:var(--mut)">…</p>';
    const pend = SHARES.pending || [], done = SHARES.decided || [];
    return `<p style="color:var(--mut);font-size:13px;margin:6px 0">The curator nominates a skill only when the telemetry proves it was followed (${(SHARES.min_reads) || 3}+ reads) - nothing goes out without your tap.</p>`
      + (pend.length ? pend.map(r => `<div style="border:1px solid var(--hair);border-radius:14px;padding:14px 16px;margin:10px 0;background:var(--glass2)">
          <b>${esc(r.name)}</b> ${tag('warn', 'waiting for you')}
          <div style="color:var(--mut);font-size:13px;margin:4px 0">${esc(r.note || '')}</div>
          <button class="btn go" data-sk="approve" data-n="${esc(r.name)}">Publish to the shelf</button>
          <button class="btn soft" data-sk="reject" data-n="${esc(r.name)}">Reject</button>
        </div>`).join('')
        : `<p style="color:var(--mut);padding:14px 4px">No nomination pending.</p>`)
      + (done.length ? `<h3 style="margin:18px 0 4px;font-size:14px">Decided</h3>` + done.map(r =>
        `<div style="padding:8px 2px;border-bottom:1px solid var(--hair);font-size:14px">${esc(r.name)} ${r.status === 'published' ? tag('ok', 'published') : tag('', 'rejected')}</div>`).join('') : '');
  }

  /* ------------------------------------------------------------ draw + actions */
  function draw(el) {
    el.innerHTML = `<div style="max-width:860px;margin:0 auto">
      <h2 style="margin:8px 0 0">Learned Skills</h2>
      <p style="color:var(--mut);margin:4px 0 10px;font-size:14px">What your Hoola knows how to do - its own how-to for the work it does again and again. Injected when an ask matches; parked skills stay but never ride.</p>
      <div style="display:flex;gap:6px;margin:6px 0 10px;border-bottom:1px solid var(--hair)">
        ${[['mine', 'My skills'], ['bazaar', 'Pack bazaar'], ['shares', `Shares${SHARES && SHARES.pending && SHARES.pending.length ? ' (' + SHARES.pending.length + ')' : ''}`]]
          .map(([k, n]) => `<button class="btn ${TAB === k ? 'go' : 'soft'}" data-tab="${k}" style="border-radius:12px 12px 0 0">${n}</button>`).join('')}
      </div>
      <div id="sktab">${TAB === 'mine' ? mine() : TAB === 'bazaar' ? bazaar() : shares()}</div>
    </div>`;
    const q = el.querySelector('#skq');
    if (q) q.oninput = () => { Q = q.value; const t = el.querySelector('#sktab'); t.innerHTML = mine(); wire(el); const nq = el.querySelector('#skq'); nq.focus(); nq.setSelectionRange(nq.value.length, nq.value.length); };
  }

  async function showBody(el, name, fromPack) {
    const box = el.querySelector(`[data-body="${CSS.escape(name)}"]`);
    if (!box) return;
    if (!box.hidden) { box.hidden = true; return; }
    box.hidden = false; box.textContent = '…';
    try {
      const full = fromPack
        ? await api('POST', '/api/coder/skills/packs/read', {name})
        : await api('POST', '/api/coder/skills', {operations: [{action: 'read', name}]});
      const body = fromPack ? full.body : (full.results && full.results[0] && full.results[0].body);
      box.innerHTML = `<pre style="white-space:pre-wrap;background:var(--bg);border:1px solid var(--hair);border-radius:10px;padding:12px;font-size:13px;color:var(--ink)">${esc(body || '')}</pre>`;
    } catch (e) { box.textContent = e.message || 'Did not open'; }
  }

  function wire(el) {
    el.onclick = async ev => {
      const t = ev.target.closest('[data-tab],[data-sk]');
      if (!t) return;
      if (t.dataset.tab) { TAB = t.dataset.tab; draw(el); return; }
      const k = t.dataset.sk, n = t.dataset.n;
      try {
        if (k === 'read') return void showBody(el, n, false);
        if (k === 'packread') return void showBody(el, n, true);
        if (k === 'toggle') { await api('POST', '/api/coder/skills/enabled', {name: n, enabled: t.dataset.on === '1'}); toast('OK'); await reload(); draw(el); return; }
        if (k === 'del') { if (!confirm(`Delete skill "${n}"? This cannot be undone.`)) return; await api('POST', '/api/coder/skills', {operations: [{action: 'read', name: n}]}); await api('POST', '/api/coder/skills', {operations: [{action: 'delete', name: n}]}); toast('Deleted'); await reload(); draw(el); return; }
        if (k === 'install') { const r = await api('POST', '/api/coder/skills/packs/install', {name: n}); if (r.error) throw new Error(r.error); toast('Installed'); await reload(); draw(el); return; }
        if (k === 'approve' || k === 'reject') { const r = await api('POST', '/api/coder/skills/shares/decide', {name: n, approve: k === 'approve'}); if (r.error) throw new Error(r.error); toast(k === 'approve' ? 'Published to the shelf' : 'Rejected'); await reload(); draw(el); return; }
        if (k === 'new') { el.querySelector('#skedit').innerHTML = editor(null); el.querySelector('#skedit [data-f=name]').focus(); return; }
        if (k === 'edit') { const s = SKILLS.find(x => x.name === n); const r = await api('POST', '/api/coder/skills', {operations: [{action: 'read', name: n}]}); el.querySelector('#skedit').innerHTML = editor({...s, ...(r.results && r.results[0])}); return; }
        if (k === 'cancel') { el.querySelector('#skedit').innerHTML = ''; return; }
        if (k === 'save') {
          const wrap = t.closest('#skedit');
          const name = wrap.querySelector('[data-f=name]').value.trim();
          const desc = wrap.querySelector('[data-f=desc]').value.trim();
          const body = wrap.querySelector('[data-f=body]').value;
          const err = wrap.querySelector('[data-err]');
          try {
            if (t.dataset.n) await api('POST', '/api/coder/skills', {operations: [{action: 'update', name: t.dataset.n, description: desc, body}]});
            else await api('POST', '/api/coder/skills', {operations: [{action: 'create', name, description: desc, body}]});
            toast('Skill saved'); el.querySelector('#skedit').innerHTML = ''; await reload(); draw(el);
          } catch (e) { err.textContent = e.message || 'Not saved'; }
          return;
        }
        if (k === 'import') {
          const txt = prompt('Paste a SKILL.md file (or a JSON array of {name, description, body}):');
          if (!txt) return;
          let items;
          try { items = txt.trim().startsWith('[') ? JSON.parse(txt) : txt.split(/\n(?=---\s*\nname:)/).map(s => s.trim()).filter(Boolean); }
          catch (e) { return toast('Could not read the JSON', true); }
          const r = await api('POST', '/api/coder/skills/import', {items});
          if (r.error) throw new Error(r.error);
          toast(`Import: ${r.created.length} bane, ${r.skipped.length} already the`); await reload(); draw(el);
          return;
        }
        if (k === 'export') {
          const r = await api('GET', '/api/coder/skills/export');
          const blob = new Blob([JSON.stringify(r, null, 2)], {type: 'application/json'});
          const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
          a.download = 'hoola-skills.json'; a.click(); URL.revokeObjectURL(a.href);
          return;
        }
      } catch (e) { toast(e.message || 'Something went wrong', true); }
    };
  }

  return {draw: el => reload().then(() => draw(el))};
};
