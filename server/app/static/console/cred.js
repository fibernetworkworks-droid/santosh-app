/* v0.999.54 HOOLA CRED - her password manager. Zero knowledge: the master password, the vault key and every decrypted
   value live only in this page's memory. The server gets the salt, the round count, the wrapped vault key and each
   item as AES-256-GCM ciphertext. Locks itself after 10 idle minutes. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const APP = $('#cr');
  const ITERS = 600000;
  const IDLE_MS = 10 * 60 * 1000;
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const te = new TextEncoder(), td = new TextDecoder();

  const ST = {meta: null, vk: null, items: [], view: 'all', sel: '', edit: null, q: '', timers: [], idle: 0, otpTick: 0};

  async function api(method, path, body, raw) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const r = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
    if (!r.ok) {
      let m = r.statusText;
      try { const j = await r.json(); m = j.detail || m; } catch {}
      throw new Error(typeof m === 'string' ? m : 'Request failed');
    }
    return raw ? r.text() : r.json();
  }
  let toastT = 0;
  function toast(msg, err) {
    const t = $('#toast'); t.textContent = msg; t.className = 'cr-toast' + (err ? ' err' : ''); t.hidden = false;
    clearTimeout(toastT); toastT = setTimeout(() => { t.hidden = true; }, 3200);
  }

  /* ---------------------------------------------------------------- crypto (WebCrypto only) */
  const b64 = u8 => { let s = ''; for (const b of u8) s += String.fromCharCode(b); return btoa(s); };
  const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const rand = n => crypto.getRandomValues(new Uint8Array(n));
  async function kek(pw, salt, iters) {
    const base = await crypto.subtle.importKey('raw', te.encode(pw), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey({name: 'PBKDF2', hash: 'SHA-256', salt, iterations: iters}, base,
      {name: 'AES-GCM', length: 256}, false, ['encrypt', 'decrypt']);
  }
  async function seal(key, bytes) {
    const iv = rand(12);
    const ct = new Uint8Array(await crypto.subtle.encrypt({name: 'AES-GCM', iv}, key, bytes));
    return {iv: b64(iv), ct: b64(ct)};
  }
  async function open(key, box) {
    return new Uint8Array(await crypto.subtle.decrypt({name: 'AES-GCM', iv: unb64(box.iv)}, key, unb64(box.ct)));
  }
  const vkOf = raw => crypto.subtle.importKey('raw', raw, {name: 'AES-GCM'}, false, ['encrypt', 'decrypt']);
  async function unwrap(pw, meta) {
    const k = await kek(pw, unb64(meta.salt), meta.iters);
    return open(k, meta.wrapped);              // throws on a wrong master password (GCM tag)
  }
  const encItem = data => seal(ST.vk, te.encode(JSON.stringify(data)));
  const decItem = async box => JSON.parse(td.decode(await open(ST.vk, box)));

  /* ---------------------------------------------------------------- 2-step codes (RFC 6238) */
  function b32(s) {
    const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    const t = String(s || '').toUpperCase().replace(/[^A-Z2-7]/g, '');
    let bits = '', out = [];
    for (const c of t) bits += A.indexOf(c).toString(2).padStart(5, '0');
    for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2));
    return new Uint8Array(out);
  }
  function totpSecret(v) {
    let t = String(v || '').trim();
    if (/^otpauth:\/\//i.test(t)) { try { t = new URL(t).searchParams.get('secret') || ''; } catch { t = ''; } }
    t = t.replace(/[\s-]/g, '').toUpperCase();
    return /^[A-Z2-7]+=*$/.test(t) && t.length >= 16 ? t : '';
  }
  async function totp(v, at) {
    const sec = totpSecret(v); if (!sec) return '';
    const key = await crypto.subtle.importKey('raw', b32(sec), {name: 'HMAC', hash: 'SHA-1'}, false, ['sign']);
    const ctr = Math.floor((at || Date.now()) / 1000 / 30);
    const msg = new Uint8Array(8); let c = ctr;
    for (let i = 7; i >= 0; i--) { msg[i] = c & 0xff; c = Math.floor(c / 256); }
    const mac = new Uint8Array(await crypto.subtle.sign('HMAC', key, msg));
    const o = mac[19] & 0x0f;
    const n = ((mac[o] & 0x7f) << 24 | mac[o + 1] << 16 | mac[o + 2] << 8 | mac[o + 3]) % 1e6;
    return String(n).padStart(6, '0');
  }

  /* ---------------------------------------------------------------- passwords */
  const SETS = {lower: 'abcdefghijkmnopqrstuvwxyz', upper: 'ABCDEFGHJKLMNPQRSTUVWXYZ', digits: '23456789', symbols: '!@#$%^&*-_=+?'};
  function generate(len, opts) {
    const pool = Object.keys(SETS).filter(k => opts[k]).map(k => SETS[k]);
    if (!pool.length) pool.push(SETS.lower);
    const all = pool.join('');
    const pick = s => { const lim = 256 - (256 % s.length); let b; do { b = rand(1)[0]; } while (b >= lim); return s[b % s.length]; };
    let out;
    do { out = Array.from({length: len}, () => pick(all)).join(''); }
    while (!pool.every(s => [...out].some(ch => s.includes(ch))) && len >= pool.length);
    return out;
  }
  function strength(pw) {
    const p = String(pw || '');
    const cls = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter(r => r.test(p)).length;
    let s = Math.min(4, Math.floor(p.length / 4)) + cls - 2;
    if (/^(.)\1+$/.test(p) || /^(password|qwerty|12345|admin)/i.test(p)) s = 0;
    const score = Math.max(0, Math.min(4, s));
    return {score, label: ['Very weak', 'Weak', 'Fair', 'Good', 'Strong'][score],
            color: ['var(--bad)', 'var(--bad)', 'var(--warn)', 'var(--ok)', 'var(--ok)'][score]};
  }
  async function sha1hex(s) {
    const h = new Uint8Array(await crypto.subtle.digest('SHA-1', te.encode(s)));
    return [...h].map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase();
  }
  async function copy(text, what) {
    try { await navigator.clipboard.writeText(text); } catch { toast('Copy is blocked here - select and copy it yourself', true); return; }
    toast(`${what} copied - cleared from the clipboard in 30 s`);
    setTimeout(() => { navigator.clipboard.writeText('').catch(() => {}); }, 30000);
  }
  const host = u => { try { return new URL(/:\/\//.test(u) ? u : 'https://' + u).hostname.replace(/^www\./, ''); } catch { return ''; } };

  /* ---------------------------------------------------------------- lock / unlock */
  function lock(msg) {
    ST.vk = null; ST.items = []; ST.edit = null; ST.sel = '';
    ST.timers.forEach(clearInterval); ST.timers = [];
    start(msg);
  }
  function bumpIdle() { ST.idle = Date.now(); }
  ['mousemove', 'keydown', 'pointerdown', 'scroll', 'touchstart'].forEach(e => addEventListener(e, bumpIdle, {passive: true}));
  setInterval(() => { if (ST.vk && Date.now() - ST.idle > IDLE_MS) lock('Locked after 10 minutes without use.'); }, 15000);

  async function start(msg) {
    if (!TOKEN) { APP.innerHTML = `<div class="cr-lock"><h1>Hoola Cred</h1><p>Sign in to the Hoola console first.</p><a class="btn pri" href="/console/">Open the console</a></div>`; return; }
    try { ST.meta = await api('GET', '/api/cred/vault'); } catch (e) { APP.innerHTML = `<div class="cr-empty">${esc(e.message)}</div>`; return; }
    const mark = '<div class="cr-mark" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></div>';
    if (!ST.meta.exists) {
      APP.innerHTML = `<form class="cr-lock" id="mk" autocomplete="off">${mark}<h1>Make your Hoola Cred</h1>
        <p>One master password opens all your passwords. It never leaves this device - not even Hoola can read your vault.</p>
        <div class="cr-warn"><b>Remember it.</b> If you forget the master password, nobody can open the vault - not Hoola, not support.</div>
        <div><label class="lbl" for="m1">Master password</label><input class="in" id="m1" type="password" autocomplete="new-password" required minlength="10"></div>
        <div class="cr-meter"><i id="m1bar"></i></div><span class="mut" id="m1lab" style="font-size:13px">At least 10 characters - a short sentence works well.</span>
        <div><label class="lbl" for="m2">Type it again</label><input class="in" id="m2" type="password" autocomplete="new-password" required></div>
        <button class="btn pri" type="submit">Make my vault</button></form>`;
      $('#m1').addEventListener('input', e => { const s = strength(e.target.value); const b = $('#m1bar'); b.style.width = (s.score + 1) * 20 + '%'; b.style.background = s.color; $('#m1lab').textContent = s.label; });
      $('#mk').addEventListener('submit', async e => {
        e.preventDefault();
        const a = $('#m1').value, b = $('#m2').value;
        if (a.length < 10) return toast('Use at least 10 characters', true);
        if (a !== b) return toast('The two do not match', true);
        if (strength(a).score < 2) return toast('Too easy to guess - make it longer', true);
        const btn = e.target.querySelector('button'); btn.disabled = true; btn.textContent = 'Making…';
        try {
          const salt = rand(16), raw = rand(32);
          const k = await kek(a, salt, ITERS);
          await api('POST', '/api/cred/vault', {salt: b64(salt), iters: ITERS, wrapped: await seal(k, raw)});
          ST.vk = await vkOf(raw); raw.fill(0); ST.items = []; bumpIdle();
          ST.meta = await api('GET', '/api/cred/vault');
          toast('Your Hoola Cred is ready'); draw();
        } catch (err) { toast(err.message, true); btn.disabled = false; btn.textContent = 'Make my vault'; }
      });
      return;
    }
    APP.innerHTML = `<form class="cr-lock" id="un" autocomplete="off">${mark}<h1>Unlock Hoola Cred</h1>
      ${msg ? `<p>${esc(msg)}</p>` : '<p>Your master password opens the vault on this device only.</p>'}
      <div><label class="lbl" for="mp">Master password</label><input class="in" id="mp" type="password" autocomplete="current-password" required autofocus></div>
      <button class="btn pri" type="submit">Unlock</button></form>`;
    $('#un').addEventListener('submit', async e => {
      e.preventDefault();
      const btn = e.target.querySelector('button'); btn.disabled = true; btn.textContent = 'Unlocking…';
      const pw = $('#mp').value; $('#mp').value = '';
      try {
        const raw = await unwrap(pw, ST.meta);
        ST.vk = await vkOf(raw); raw.fill(0);
      } catch { btn.disabled = false; btn.textContent = 'Unlock'; return toast('That is not the master password', true); }
      await loadItems(); bumpIdle(); draw();
    });
  }
  async function loadItems() {
    const out = [];
    for (const it of ST.meta.items || []) {
      try { out.push({id: it.id, version: it.version, hoola: it.hoola, updated: it.updated, data: await decItem(it)}); }
      catch { out.push({id: it.id, version: it.version, hoola: it.hoola, broken: true, data: {title: '(cannot be opened)'}}); }
    }
    ST.items = out;
  }
  async function reload() { ST.meta = await api('GET', '/api/cred/vault'); await loadItems(); }

  /* ---------------------------------------------------------------- layout */
  const VIEWS = [['all', 'All items'], ['hoola', 'Hoola may use'], ['otp', '2-step codes'], ['safety', 'Safety check'],
                 ['gen', 'Password generator'], ['import', 'Import'], ['settings', 'Settings']];
  function counts() {
    return {all: ST.items.length, hoola: ST.items.filter(i => i.hoola).length, otp: ST.items.filter(i => totpSecret(i.data.totp)).length};
  }
  function filtered() {
    const q = ST.q.trim().toLowerCase();
    let rows = ST.items;
    if (ST.view === 'hoola') rows = rows.filter(i => i.hoola);
    if (ST.view === 'otp') rows = rows.filter(i => totpSecret(i.data.totp));
    if (ST.view.startsWith('f:')) rows = rows.filter(i => (i.data.folder || '') === ST.view.slice(2));
    if (q) rows = rows.filter(i => [i.data.title, i.data.username, ...(i.data.urls || []), i.data.folder].join(' ').toLowerCase().includes(q));
    return rows.slice().sort((a, b) => String(a.data.title || '').localeCompare(String(b.data.title || '')));
  }
  function draw() {
    ST.timers.forEach(clearInterval); ST.timers = [];
    const c = counts();
    const folders = [...new Set(ST.items.map(i => i.data.folder).filter(Boolean))].sort();
    const listView = ['all', 'hoola', 'otp'].includes(ST.view) || ST.view.startsWith('f:');
    APP.className = 'cr' + ((!listView || ST.sel || ST.edit) ? ' detail' : '');
    APP.innerHTML = `<nav class="cr-side" aria-label="Hoola Cred">
        <div class="cr-brand"><i aria-hidden="true">●</i>Hoola Cred</div>
        <div class="cr-navs">${VIEWS.map(([k, t]) => `<button class="cr-nav" type="button" data-view="${k}" ${ST.view === k ? 'aria-current="page"' : ''}>${t}${c[k] !== undefined ? `<span>${c[k]}</span>` : ''}</button>`).join('')}
        ${folders.length ? `<div class="cr-lab">Folders</div>` + folders.map(f => `<button class="cr-nav" type="button" data-view="f:${esc(f)}" ${ST.view === 'f:' + f ? 'aria-current="page"' : ''}>${esc(f)}</button>`).join('') : ''}</div>
        <div class="cr-foot"><button class="btn sm" type="button" id="lockBtn">Lock now</button><a class="btn sm" href="/console/">Back to Hoola</a></div>
      </nav>
      ${listView ? `<section class="cr-list" aria-label="Items">
        <div class="cr-listhead"><input class="in" id="q" type="search" placeholder="Search" aria-label="Search" value="${esc(ST.q)}">
          <button class="btn pri" type="button" id="addBtn">New</button></div>
        <div class="cr-items" id="items">${itemRows()}</div></section>` : ''}
      <main class="cr-main" id="main"></main>`;
    APP.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => { ST.view = b.dataset.view; ST.sel = ''; ST.edit = null; draw(); }));
    $('#lockBtn').addEventListener('click', () => lock('Locked.'));
    if (listView) {
      $('#q').addEventListener('input', e => { ST.q = e.target.value; $('#items').innerHTML = itemRows(); });
      $('#items').addEventListener('click', e => { const b = e.target.closest('[data-id]'); if (b) { ST.sel = b.dataset.id; ST.edit = null; draw(); } });
      $('#addBtn').addEventListener('click', () => { ST.sel = ''; ST.edit = {title: '', username: '', password: generate(20, {lower: 1, upper: 1, digits: 1, symbols: 1}), urls: [], totp: '', notes: '', folder: ST.view.startsWith('f:') ? ST.view.slice(2) : ''}; draw(); });
    }
    const m = $('#main');
    if (ST.edit) return drawEdit(m);
    if (ST.view === 'gen') return drawGen(m);
    if (ST.view === 'safety') return drawSafety(m);
    if (ST.view === 'import') return drawImport(m);
    if (ST.view === 'settings') return drawSettings(m);
    if (ST.sel) return drawItem(m);
    m.innerHTML = ST.items.length
      ? `<p class="cr-sub" style="margin-top:40px;text-align:center">Pick an item, or press New.</p>`
      : `<h1>Your vault is empty</h1><p class="cr-sub">Add your first login with New, or bring them in from Chrome, 1Password or Bitwarden under Import.</p>`;
  }
  function itemRows() {
    const rows = filtered();
    if (!rows.length) return `<p class="mut" style="padding:16px">${ST.q ? 'Nothing matches.' : 'Nothing here yet.'}</p>`;
    return rows.map(i => `<button class="cr-item" type="button" data-id="${esc(i.id)}" ${i.id === ST.sel ? 'aria-current="true"' : ''}>
      <span class="cr-av" aria-hidden="true">${esc((i.data.title || '?').trim().charAt(0).toUpperCase())}</span>
      <div><b>${esc(i.data.title || '(no title)')}</b><small>${esc(i.data.username || host((i.data.urls || [])[0] || '') || '')}</small></div>
      ${i.hoola ? '<span class="cr-tag">Hoola</span>' : ''}</button>`).join('');
  }
  const back = '<button class="btn sm cr-back" type="button" data-back>← Back</button>';
  function wireBack(m) { const b = m.querySelector('[data-back]'); if (b) b.addEventListener('click', () => { ST.sel = ''; ST.edit = null; draw(); }); }

  /* ---------------------------------------------------------------- one item */
  function drawItem(m) {
    const it = ST.items.find(i => i.id === ST.sel); if (!it) { ST.sel = ''; return draw(); }
    const d = it.data;
    m.innerHTML = `${back}<h1>${esc(d.title || '(no title)')}</h1><p class="cr-sub">${d.folder ? esc(d.folder) + ' · ' : ''}${it.hoola ? 'Hoola may use it on the Hoola PC (on your tap)' : 'Only you'}</p>
      ${d.username ? `<div class="cr-field"><span class="k">User name</span><span class="v mono">${esc(d.username)}</span><button class="btn sm" type="button" data-copy="username">Copy</button></div>` : ''}
      ${d.password ? `<div class="cr-field"><span class="k">Password</span><span class="v mono" id="pwv">••••••••••••</span>
        <button class="btn sm" type="button" id="showPw">Show</button><button class="btn sm" type="button" data-copy="password">Copy</button></div>` : ''}
      ${totpSecret(d.totp) ? `<div class="cr-field"><span class="k">2-step code</span><span class="v"><span class="cr-otp" id="otp">······</span> <span class="cr-ring" id="otpLeft"></span></span><button class="btn sm" type="button" id="copyOtp">Copy</button></div>` : ''}
      ${(d.urls || []).map(u => `<div class="cr-field"><span class="k">Website</span><span class="v"><a href="${esc(/:\/\//.test(u) ? u : 'https://' + u)}" target="_blank" rel="noopener noreferrer">${esc(u)}</a></span></div>`).join('')}
      ${d.notes ? `<div class="cr-field"><span class="k">Notes</span><span class="v" style="white-space:pre-wrap">${esc(d.notes)}</span></div>` : ''}
      <div class="row" style="margin-top:18px;flex-wrap:wrap"><button class="btn pri" type="button" id="editBtn">Edit</button><button class="btn bad" type="button" id="delBtn">Delete</button></div>`;
    wireBack(m);
    m.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => copy(d[b.dataset.copy], b.dataset.copy === 'password' ? 'Password' : 'User name')));
    const sp = $('#showPw'); if (sp) sp.addEventListener('click', () => { const v = $('#pwv'); const on = sp.textContent === 'Show'; v.textContent = on ? d.password : '••••••••••••'; sp.textContent = on ? 'Hide' : 'Show'; });
    if (totpSecret(d.totp)) {
      const tick = async () => { const o = $('#otp'); if (!o) return; o.textContent = await totp(d.totp); $('#otpLeft').textContent = `${30 - Math.floor(Date.now() / 1000) % 30}s`; };
      tick(); ST.timers.push(setInterval(tick, 1000));
      $('#copyOtp').addEventListener('click', async () => copy(await totp(d.totp), '2-step code'));
    }
    $('#editBtn').addEventListener('click', () => { ST.edit = {...d, urls: [...(d.urls || [])], _id: it.id, _hoola: it.hoola}; draw(); });
    $('#delBtn').addEventListener('click', async () => {
      if (!confirm(`Delete "${d.title || 'this item'}"? This cannot be undone.`)) return;
      try { await api('DELETE', `/api/cred/items/${enc(it.id)}`); await reload(); ST.sel = ''; toast('Deleted'); draw(); } catch (e) { toast(e.message, true); }
    });
  }
  function drawEdit(m) {
    const e = ST.edit, isNew = !e._id;
    m.innerHTML = `${back}<h1>${isNew ? 'New login' : 'Edit'}</h1><p class="cr-sub">Encrypted on this device before it is saved.</p>
      <form class="cr-form" id="ef" autocomplete="off">
        <div><label class="lbl" for="et">Title</label><input class="in" id="et" value="${esc(e.title)}" placeholder="GST portal" required></div>
        <div><label class="lbl" for="eu">User name</label><input class="in mono" id="eu" value="${esc(e.username)}" autocomplete="off" spellcheck="false"></div>
        <div><label class="lbl" for="ep">Password</label><div class="row"><input class="in mono" id="ep" type="password" value="${esc(e.password)}" autocomplete="new-password" spellcheck="false">
          <button class="btn sm" type="button" id="epShow">Show</button><button class="btn sm" type="button" id="epGen">Generate</button></div>
          <div class="cr-meter"><i id="epBar"></i></div><span class="mut" id="epLab" style="font-size:13px"></span></div>
        <div><label class="lbl" for="ew">Websites (one per line)</label><textarea class="ta" id="ew" spellcheck="false" placeholder="https://services.gst.gov.in">${esc((e.urls || []).join('\n'))}</textarea></div>
        <div><label class="lbl" for="eo">2-step key (optional)</label><input class="in mono" id="eo" value="${esc(e.totp)}" placeholder="The setup key or otpauth:// link from the site" spellcheck="false"></div>
        <div><label class="lbl" for="ef2">Folder</label><input class="in" id="ef2" value="${esc(e.folder)}" placeholder="Work, Family…"></div>
        <div><label class="lbl" for="en">Notes</label><textarea class="ta" id="en">${esc(e.notes)}</textarea></div>
        <label class="cr-sw"><input type="checkbox" id="eh" ${e._hoola ? 'checked' : ''}><span><b>Hoola may use this login</b>
          <small>The Hoola PC can sign in to these websites for you - only when you tap "Use saved sign-in". This one login is then also kept in a form Hoola's server can open. Never for bank or payment logins.</small></span></label>
        <div class="row"><button class="btn pri" type="submit">Save</button><button class="btn" type="button" data-back2>Cancel</button></div>
      </form>`;
    wireBack(m);
    const meter = () => { const s = strength($('#ep').value); $('#epBar').style.width = (s.score + 1) * 20 + '%'; $('#epBar').style.background = s.color; $('#epLab').textContent = s.label; };
    meter(); $('#ep').addEventListener('input', meter);
    $('#epShow').addEventListener('click', ev => { const p = $('#ep'); p.type = p.type === 'password' ? 'text' : 'password'; ev.target.textContent = p.type === 'password' ? 'Show' : 'Hide'; });
    $('#epGen').addEventListener('click', () => { $('#ep').value = generate(20, {lower: 1, upper: 1, digits: 1, symbols: 1}); $('#ep').type = 'text'; $('#epShow').textContent = 'Hide'; meter(); });
    m.querySelector('[data-back2]').addEventListener('click', () => { ST.edit = null; draw(); });
    $('#ef').addEventListener('submit', async ev => {
      ev.preventDefault();
      const data = {title: $('#et').value.trim(), username: $('#eu').value.trim(), password: $('#ep').value,
        urls: $('#ew').value.split('\n').map(s => s.trim()).filter(Boolean).slice(0, 10), totp: $('#eo').value.trim(),
        folder: $('#ef2').value.trim(), notes: $('#en').value, updated: new Date().toISOString()};
      if (data.totp && !totpSecret(data.totp)) return toast('That 2-step key is not valid', true);
      const wantHoola = $('#eh').checked;
      const btn = ev.target.querySelector('[type=submit]'); btn.disabled = true;
      try {
        const box = await encItem({...data, created: e.created || data.updated});
        let id = e._id;
        if (isNew) id = (await api('POST', '/api/cred/items', box)).id;
        else await api('PUT', `/api/cred/items/${enc(id)}`, {...box, version: ST.items.find(i => i.id === id).version});
        if (wantHoola || e._hoola) {
          await api('PUT', `/api/cred/items/${enc(id)}/hoola`, wantHoola
            ? {on: true, title: data.title, username: data.username, password: data.password, urls: data.urls, totp: data.totp}
            : {on: false});
        }
        await reload(); ST.edit = null; ST.sel = id; toast('Saved'); draw();
      } catch (err) { btn.disabled = false; toast(err.message, true); if (!isNew) { await reload().catch(() => {}); } }
    });
  }

  /* ---------------------------------------------------------------- generator */
  function drawGen(m) {
    const o = {len: 20, lower: 1, upper: 1, digits: 1, symbols: 1};
    m.innerHTML = `${back}<h1>Password generator</h1><p class="cr-sub">Made on this device with the browser's secure random numbers.</p>
      <div class="cr-gen" id="gv"></div>
      <div class="row" style="margin:12px 0;flex-wrap:wrap"><button class="btn pri" type="button" id="gCopy">Copy</button><button class="btn" type="button" id="gNew">New one</button></div>
      <label class="lbl" for="gl">Length: <span id="glv">20</span></label><input id="gl" type="range" min="8" max="64" value="20" style="width:100%;max-width:420px">
      <div class="row" style="flex-wrap:wrap;margin-top:10px">${['lower', 'upper', 'digits', 'symbols'].map(k => `<label class="row"><input type="checkbox" data-o="${k}" checked> ${({lower: 'a-z', upper: 'A-Z', digits: '0-9', symbols: '!@#'})[k]}</label>`).join('')}</div>`;
    wireBack(m);
    const make = () => { $('#gv').textContent = generate(o.len, o); };
    make();
    $('#gNew').addEventListener('click', make);
    $('#gCopy').addEventListener('click', () => copy($('#gv').textContent, 'Password'));
    $('#gl').addEventListener('input', e => { o.len = +e.target.value; $('#glv').textContent = o.len; make(); });
    m.querySelectorAll('[data-o]').forEach(c => c.addEventListener('change', () => { o[c.dataset.o] = c.checked ? 1 : 0; make(); }));
  }

  /* ---------------------------------------------------------------- safety check */
  function drawSafety(m) {
    const logins = ST.items.filter(i => i.data.password);
    const byPw = {};
    logins.forEach(i => { (byPw[i.data.password] = byPw[i.data.password] || []).push(i); });
    const weak = logins.filter(i => strength(i.data.password).score < 2);
    const reused = Object.values(byPw).filter(g => g.length > 1);
    const no2 = logins.filter(i => !totpSecret(i.data.totp));
    m.innerHTML = `${back}<h1>Safety check</h1><p class="cr-sub">Worked out on this device. The breach check sends only the first 5 characters of each password's fingerprint (SHA-1) - never the password.</p>
      <div class="cr-card"><b>${weak.length} weak password${weak.length === 1 ? '' : 's'}</b>${weak.map(i => `<div><span class="cr-pill bad">${esc(strength(i.data.password).label)}</span><a href="#" data-go="${esc(i.id)}">${esc(i.data.title)}</a></div>`).join('') || '<span class="mut">None - good.</span>'}</div>
      <div class="cr-card"><b>${reused.length} password${reused.length === 1 ? '' : 's'} used on more than one site</b>${reused.map(g => `<div><span class="cr-pill warn">${g.length} sites</span>${g.map(i => `<a href="#" data-go="${esc(i.id)}">${esc(i.data.title)}</a>`).join(', ')}</div>`).join('') || '<span class="mut">None - good.</span>'}</div>
      <div class="cr-card"><b>Found in data breaches</b><div id="br" class="mut">Not checked yet.</div><button class="btn sm" type="button" id="brBtn" style="margin-top:8px">Check now</button></div>
      <div class="cr-card"><b>${no2.length} login${no2.length === 1 ? '' : 's'} without a 2-step code</b><span class="mut">Turn on 2-step sign-in on the site and paste its setup key here.</span></div>`;
    wireBack(m);
    m.addEventListener('click', e => { const a = e.target.closest('[data-go]'); if (a) { e.preventDefault(); ST.view = 'all'; ST.sel = a.dataset.go; draw(); } });
    $('#brBtn').addEventListener('click', async ev => {
      ev.target.disabled = true; const out = $('#br'); out.textContent = 'Checking…';
      const hits = [];
      for (const [pw, group] of Object.entries(byPw)) {
        try {
          const h = await sha1hex(pw); const body = await api('GET', `/api/cred/pwned/${h.slice(0, 5)}`, undefined, true);
          const line = body.split('\n').find(l => l.split(':')[0].trim() === h.slice(5));
          const n = line ? parseInt(line.split(':')[1], 10) : 0;
          if (n > 0) hits.push({group, n});
        } catch { out.textContent = 'The breach check is not reachable right now.'; ev.target.disabled = false; return; }
      }
      out.innerHTML = hits.length ? hits.map(h => `<div><span class="cr-pill bad">seen ${h.n.toLocaleString()} times</span>${h.group.map(i => `<a href="#" data-go="${esc(i.id)}">${esc(i.data.title)}</a>`).join(', ')} - change it</div>`).join('')
        : '<span class="cr-pill ok">None found</span>';
      ev.target.disabled = false;
    });
  }

  /* ---------------------------------------------------------------- import */
  function csv(text) {
    const rows = []; let row = [], cell = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; continue; }
      if (ch === '"') q = true;
      else if (ch === ',') { row.push(cell); cell = ''; }
      else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
      else cell += ch;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    return rows.filter(r => r.some(c => c.trim()));
  }
  function mapRows(rows) {
    const head = rows[0].map(h => h.trim().toLowerCase());
    const col = (...names) => { for (const n of names) { const i = head.indexOf(n); if (i >= 0) return i; } return -1; };
    const c = {title: col('name', 'title'), url: col('url', 'login_uri', 'website', 'urls'), user: col('username', 'login_username', 'user name', 'email'),
               pw: col('password', 'login_password'), totp: col('login_totp', 'one-time password', 'otpauth', 'totp'), notes: col('note', 'notes', 'extra'),
               folder: col('folder', 'vault', 'grouping'), type: col('type')};
    if (c.pw < 0) return null;
    return rows.slice(1).filter(r => c.type < 0 || !r[c.type] || r[c.type].toLowerCase() === 'login').map(r => {
      const g = i => (i >= 0 ? String(r[i] || '').trim() : '');
      const url = g(c.url);
      return {title: g(c.title) || host(url) || 'Imported login', username: g(c.user), password: g(c.pw), urls: url ? url.split(/[\s,]+/).filter(Boolean).slice(0, 10) : [],
              totp: totpSecret(g(c.totp)) ? g(c.totp) : '', notes: g(c.notes), folder: g(c.folder)};
    }).filter(x => x.password);
  }
  function drawImport(m) {
    m.innerHTML = `${back}<h1>Import</h1><p class="cr-sub">From a CSV file exported by Chrome (Settings › Passwords › Export), 1Password, Bitwarden or a spreadsheet with a password column. The file is read and encrypted on this device - it is never uploaded as it is.</p>
      <input type="file" id="fi" accept=".csv,text/csv"><div id="pv" style="margin-top:14px"></div>`;
    wireBack(m);
    $('#fi').addEventListener('change', async e => {
      const f = e.target.files[0]; if (!f) return;
      if (f.size > 5 * 1024 * 1024) return toast('That file is too big', true);
      const rows = csv(await f.text()); e.target.value = '';
      const items = rows.length > 1 ? mapRows(rows) : null;
      if (!items || !items.length) return toast('No logins with a password column were found in that file', true);
      $('#pv').innerHTML = `<div class="cr-card"><b>${items.length} login${items.length === 1 ? '' : 's'} ready</b><span class="mut">${esc(items.slice(0, 5).map(i => i.title).join(', '))}${items.length > 5 ? '…' : ''}</span>
        <div class="row" style="margin-top:10px"><button class="btn pri" type="button" id="doImp">Import ${items.length}</button></div></div>`;
      $('#doImp').addEventListener('click', async ev => {
        ev.target.disabled = true;
        let n = 0;
        for (const it of items) {
          try { await api('POST', '/api/cred/items', await encItem({...it, created: new Date().toISOString(), updated: new Date().toISOString()})); n++; ev.target.textContent = `Importing ${n}/${items.length}…`; }
          catch (err) { toast(err.message, true); break; }
        }
        await reload();
        $('#pv').innerHTML = `<div class="cr-card"><b>${n} imported.</b><span class="mut">Now delete the CSV file from your computer - it holds your passwords in plain text.</span></div>`;
      });
    });
  }

  /* ---------------------------------------------------------------- settings */
  function drawSettings(m) {
    m.innerHTML = `${back}<h1>Settings</h1>
      <h2>Change the master password</h2>
      <form class="cr-form" id="cm" autocomplete="off" style="max-width:420px">
        <input class="in" id="c0" type="password" placeholder="Current master password" autocomplete="current-password" required>
        <input class="in" id="c1" type="password" placeholder="New master password (10+ characters)" autocomplete="new-password" required minlength="10">
        <input class="in" id="c2" type="password" placeholder="New master password again" autocomplete="new-password" required>
        <div><button class="btn pri" type="submit">Change it</button></div></form>
      <h2>Lock</h2><p class="cr-sub">Hoola Cred locks itself after 10 minutes without use, and when you close this page.</p>
      <h2>Delete the vault</h2><p class="cr-sub">Deletes every item here and the copies Hoola may use. This cannot be undone.</p>
      <button class="btn bad" type="button" id="dv">Delete my Hoola Cred</button>`;
    wireBack(m);
    $('#cm').addEventListener('submit', async e => {
      e.preventDefault();
      const a = $('#c1').value; if (a !== $('#c2').value) return toast('The two new ones do not match', true);
      if (a.length < 10 || strength(a).score < 2) return toast('Make the new one longer', true);
      let raw;
      try { raw = await unwrap($('#c0').value, ST.meta); } catch { return toast('The current master password is wrong', true); }
      try {
        const salt = rand(16); const k = await kek(a, salt, ITERS);
        await api('PUT', '/api/cred/vault', {salt: b64(salt), iters: ITERS, wrapped: await seal(k, raw)});
        raw.fill(0); ['c0', 'c1', 'c2'].forEach(id => { $('#' + id).value = ''; });
        ST.meta = await api('GET', '/api/cred/vault'); toast('Master password changed');
      } catch (err) { toast(err.message, true); }
    });
    $('#dv').addEventListener('click', async () => {
      if (prompt('Type DELETE to delete every item in Hoola Cred') !== 'DELETE') return;
      try { await api('DELETE', '/api/cred/vault?confirm=DELETE'); lock(); toast('Hoola Cred deleted'); } catch (e) { toast(e.message, true); }
    });
  }

  addEventListener('pagehide', () => { ST.vk = null; ST.items = []; });
  start();
})();
