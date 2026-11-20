/* v0.999.57 HOOLA CRED inside the console (owner: "MAKE HOOLA CRED MORE PREMIUM ... KEEP SIDE BAR ... NATIVE", design:
   claude.ai/artifact/H71Uojvg4ha8RzvtSTqevz, "GO BUILD ALL"). A view of the console (#v-cred), so the console sidebar
   stays. Zero knowledge as before: the master password, the vault key and every opened value live only in this page's
   memory; the server gets the salt, the rounds, the wrapped vault key and AES-256-GCM items. Locks itself when idle. */
window.HoolaCred = function HoolaCred(ctx) {
  'use strict';
  const ITERS = 600000;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const te = new TextEncoder(), td = new TextDecoder();
  const toast = (m, bad) => (ctx && ctx.toast ? ctx.toast(m, bad) : console.log(m));
  const pref = (k, d) => { try { const v = localStorage.getItem('hoola.cred.' + k); return v == null ? d : +v; } catch { return d; } };
  const setPref = (k, v) => { try { localStorage.setItem('hoola.cred.' + k, String(v)); } catch { /* private window */ } };

  let EL = null;
  const ST = {meta: null, vk: null, items: [], uses: {}, tab: 'all', sel: '', edit: null, q: '', folder: '', timers: [],
              idle: Date.now(), breach: null, breachBusy: false, gen: {mode: 'random', len: 18, upper: 1, digits: 1, symbols: 1, plain: 0},
              imp: null, pwShown: false, master: false};
  const $ = s => EL && EL.querySelector(s);
  const $$ = s => EL ? [...EL.querySelectorAll(s)] : [];

  function token() { try { return localStorage.getItem('hoola.console.token') || ''; } catch { return ''; } }
  async function api(method, path, body, raw) {
    const headers = {Authorization: 'Bearer ' + token()};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const r = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
    if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = j.detail || m; } catch { /* plain */ } throw new Error(typeof m === 'string' ? m : 'Request failed'); }
    return raw ? r.text() : r.json();
  }

  /* ---------------------------------------------------------------- crypto (WebCrypto only) */
  const b64 = u8 => { let s = ''; for (const b of u8) s += String.fromCharCode(b); return btoa(s); };
  const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const rand = n => crypto.getRandomValues(new Uint8Array(n));
  async function kek(pw, salt, iters) {
    const base = await crypto.subtle.importKey('raw', te.encode(pw), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey({name: 'PBKDF2', hash: 'SHA-256', salt, iterations: iters}, base, {name: 'AES-GCM', length: 256}, false, ['encrypt', 'decrypt']);
  }
  async function seal(key, bytes) { const iv = rand(12); return {iv: b64(iv), ct: b64(new Uint8Array(await crypto.subtle.encrypt({name: 'AES-GCM', iv}, key, bytes)))}; }
  async function open(key, box) { return new Uint8Array(await crypto.subtle.decrypt({name: 'AES-GCM', iv: unb64(box.iv)}, key, unb64(box.ct))); }
  const vkOf = raw => crypto.subtle.importKey('raw', raw, {name: 'AES-GCM'}, false, ['encrypt', 'decrypt']);
  async function unwrap(pw, meta) { return open(await kek(pw, unb64(meta.salt), meta.iters), meta.wrapped); }
  const encItem = data => seal(ST.vk, te.encode(JSON.stringify(data)));
  const decItem = async box => JSON.parse(td.decode(await open(ST.vk, box)));

  /* ---------------------------------------------------------------- 2-step codes (RFC 6238) */
  function b32(s) {
    const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567', t = String(s || '').toUpperCase().replace(/[^A-Z2-7]/g, '');
    let bits = ''; const out = [];
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
    let c = Math.floor((at || Date.now()) / 30000); const msg = new Uint8Array(8);
    for (let i = 7; i >= 0; i--) { msg[i] = c & 0xff; c = Math.floor(c / 256); }
    const mac = new Uint8Array(await crypto.subtle.sign('HMAC', key, msg)), o = mac[19] & 0x0f;
    return String(((mac[o] & 0x7f) << 24 | mac[o + 1] << 16 | mac[o + 2] << 8 | mac[o + 3]) % 1e6).padStart(6, '0');
  }
  const left = () => 30 - Math.floor(Date.now() / 1000) % 30;
  const fmtCode = c => c ? c.slice(0, 3) + ' ' + c.slice(3) : '··· ···';

  /* ---------------------------------------------------------------- passwords */
  const SETS = {lower: 'abcdefghijkmnopqrstuvwxyz', upper: 'ABCDEFGHJKLMNPQRSTUVWXYZ', digits: '23456789', symbols: '!@#$%^&*-_=+?'};
  const LOOK = {lower: 'l', upper: 'IO', digits: '01', symbols: ''};
  function pickFrom(s) { const lim = 256 - (256 % s.length); let b; do { b = rand(1)[0]; } while (b >= lim); return s[b % s.length]; }
  function generate(o) {
    if (o.mode === 'pin') return Array.from({length: Math.max(4, Math.min(12, o.len))}, () => pickFrom('0123456789')).join('');
    if (o.mode === 'say') {        // pronounceable syllables: easy to read out or type on a phone
      const C = 'bdfghjklmnprstvz', V = 'aeiou', words = Math.max(3, Math.min(8, Math.round(o.len / 5)));
      const w = () => { let s = ''; for (let i = 0; i < 3; i++) s += pickFrom(C) + pickFrom(V); return s; };
      const parts = Array.from({length: words}, w).map((x, i) => i === 0 && o.upper ? x[0].toUpperCase() + x.slice(1) : x);
      return parts.join('-') + (o.digits ? '-' + pickFrom('23456789') + pickFrom('23456789') : '');
    }
    const keep = k => (o.plain ? [...SETS[k]].filter(ch => !LOOK[k].includes(ch)).join('') : SETS[k]);
    const pool = ['lower'].concat(o.upper ? ['upper'] : [], o.digits ? ['digits'] : [], o.symbols ? ['symbols'] : []).map(keep);
    const all = pool.join(''); let out;
    do { out = Array.from({length: o.len}, () => pickFrom(all)).join(''); } while (!pool.every(s => [...out].some(ch => s.includes(ch))) && o.len >= pool.length);
    return out;
  }
  const NEWPW = () => generate({mode: 'random', len: 20, upper: 1, digits: 1, symbols: 1});
  function strength(pw) {
    const p = String(pw || ''), cls = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter(r => r.test(p)).length;
    let s = Math.min(4, Math.floor(p.length / 4)) + cls - 2;
    if (/^\d+$/.test(p)) s = Math.min(s, p.length >= 8 ? 1 : 0);
    if (/^(.)\1+$/.test(p) || /^(password|qwerty|12345|admin|india|welcome)/i.test(p)) s = 0;
    const score = Math.max(0, Math.min(4, s));
    return {score, label: ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'][score], tone: ['bad', 'bad', 'warn', 'ok', 'ok'][score]};
  }
  const meter = (pw, wide) => { const s = strength(pw);
    return `<span class="hc-meter${wide ? ' wide' : ''}" aria-hidden="true">${[0, 1, 2, 3, 4].map(i => `<i class="${i <= s.score ? s.tone : ''}"></i>`).join('')}</span><span class="hc-ml ${s.tone}">${s.label}</span>`; };
  async function sha1hex(s) { const h = new Uint8Array(await crypto.subtle.digest('SHA-1', te.encode(s))); return [...h].map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase(); }
  async function copy(text, what) {
    try { await navigator.clipboard.writeText(text); } catch { toast('Copy is blocked here - select and copy it yourself', true); return; }
    const secs = pref('clip', 30);
    toast(`${what} copied - cleared from the clipboard in ${secs} s`);
    setTimeout(() => { navigator.clipboard.writeText('').catch(() => {}); }, secs * 1000);
  }
  const host = u => { try { return new URL(/:\/\//.test(u) ? u : 'https://' + u).hostname.replace(/^www\./, ''); } catch { return ''; } };
  const MONEY = /\b(bank|banking|netbanking|credit\s*card|debit\s*card|card|upi|paytm|phonepe|gpay|google\s*pay|razorpay|payment|wallet|sbi|hdfc|icici|axis|kotak|pnb|yes\s*bank|demat|zerodha|groww|upstox|broker)\b/i;
  const isMoney = d => MONEY.test(`${d.title || ''} ${(d.urls || []).join(' ')}`.replace(/[.\-_/]/g, ' '));
  const TONES = ['#2F6B4F', '#8A4B12', '#1F4E8C', '#5C4A8F', '#3B6E8F', '#7A3E5C', '#3D5A99', '#6E7A2E', '#2D7A86', '#9A4A2E'];
  function tile(d, size) {
    const t = String(d.title || '?').trim(); let h = 0; for (const ch of t) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return `<span class="hc-tile${size ? ' ' + size : ''}" style="background:${TONES[h % TONES.length]}" aria-hidden="true">${esc(t.charAt(0).toUpperCase() || '?')}</span>`;
  }
  const when = iso => { if (!iso) return ''; const d = new Date(iso); if (isNaN(d)) return ''; const now = new Date();
    if (d.toDateString() === now.toDateString()) return 'Today ' + d.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
    const y = new Date(now); y.setDate(now.getDate() - 1); if (d.toDateString() === y.toDateString()) return 'Yesterday';
    return d.toLocaleDateString([], {day: 'numeric', month: 'short'}); };
  const IC = {
    lock: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V7.5a4 4 0 018 0v3"/></svg>',
    plus: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
    search: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/></svg>',
    pc: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M9 20h6M12 16v4"/></svg>',
    redo: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 12a8 8 0 0114-5.3M20 12a8 8 0 01-14 5.3M18 3v4h-4M6 21v-4h4"/></svg>',
    file: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z"/><path d="M14 3v5h5"/></svg>',
    warn: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 3l9.5 17h-19L12 3z"/><path d="M12 10v4.5M12 17.5v.1"/></svg>',
    clock: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v5l3 2"/></svg>',
    shield: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z"/></svg>',
    globe: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.6 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.6-3.5-8.5s1-5.9 3.5-8.5z"/></svg>',
    phone: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M11 18h2"/></svg>',
  };
  const ring = (frac, size, stroke, color, label) => { const r = 15, c = 2 * Math.PI * r;
    return `<svg width="${size}" height="${size}" viewBox="0 0 36 36" role="img" aria-label="${esc(label)}"><circle cx="18" cy="18" r="${r}" fill="none" stroke="var(--line)" stroke-width="${stroke}"/><circle cx="18" cy="18" r="${r}" fill="none" stroke="${color}" stroke-width="${stroke}" stroke-linecap="round" stroke-dasharray="${(c * frac).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 18 18)"/></svg>`; };

  /* ---------------------------------------------------------------- lock / unlock */
  function clearTimers() { ST.timers.forEach(clearInterval); ST.timers = []; }
  function lock(msg) { ST.vk = null; ST.items = []; ST.edit = null; ST.sel = ''; ST.breach = null; ST.imp = null; clearTimers(); start(msg); }
  const bump = () => { ST.idle = Date.now(); };
  ['mousemove', 'keydown', 'pointerdown', 'scroll', 'touchstart'].forEach(e => addEventListener(e, bump, {passive: true}));
  setInterval(() => {
    if (!ST.vk) return;
    const mins = pref('lock', 10);
    if (Date.now() - ST.idle > mins * 60000) { lock(`Locked after ${mins} minutes without use.`); return; }
    const p = $('#hcStatus'); if (p) p.textContent = statusLine();
  }, 15000);
  addEventListener('pagehide', () => { ST.vk = null; ST.items = []; });
  function statusLine() { const mins = pref('lock', 10), l = Math.max(1, Math.ceil((mins * 60000 - (Date.now() - ST.idle)) / 60000)); return `Unlocked on this device · locks in ${l} min`; }

  async function start(msg) {
    if (!EL) return;
    clearTimers();
    EL.innerHTML = '<div class="hcv"><div class="hc-loading">Opening Hoola Cred…</div></div>';
    try { ST.meta = await api('GET', '/api/cred/vault'); } catch (e) { EL.innerHTML = `<div class="hcv"><div class="hc-loading">${esc(e.message)}</div></div>`; return; }
    if (ST.vk) { await loadItems(); return draw(); }
    if (!ST.meta.exists) return drawCreate();
    drawUnlock(msg);
  }
  function drawCreate() {
    EL.innerHTML = `<div class="hcv hc-center"><div class="hc-hero">
      <div class="hc-intro">
        <span class="hc-pill"><i class="dot acc"></i>New · your own password manager</span>
        <h1 class="hc-h1 big">Make your Hoola Cred</h1>
        <p class="hc-lead">One master password locks every login and 2-step code you keep here. It is turned into a key on this device and never leaves it.</p>
        <ul class="hc-points">
          <li><span class="i">${IC.lock}</span><span><b>Only you hold the key</b>Hoola's server keeps your logins only in locked form.</span></li>
          <li><span class="i">${IC.pc}</span><span><b>Hoola uses a login only when you say</b>Switch on “Hoola may use” for a site; bank and payment logins never.</span></li>
          <li><span class="i">${IC.clock}</span><span><b>Locks itself when you stop</b>Copied passwords clear from the clipboard by themselves.</span></li>
        </ul>
      </div>
      <form class="hc-card hc-form-card" id="hcMk" autocomplete="off">
        <div><label class="hc-lbl" for="hcM1">Master password</label><input class="hc-in" id="hcM1" type="password" autocomplete="new-password" required minlength="10">
          <div class="hc-mrow" id="hcM1m">${meter('')}<span class="hc-hint">At least 10 characters</span></div></div>
        <div><label class="hc-lbl" for="hcM2">Type it again</label><input class="hc-in" id="hcM2" type="password" autocomplete="new-password" required></div>
        <div class="hc-note warn">${IC.warn}<span>If you forget it, nobody can open this vault, not even Hoola. Write it down somewhere safe.</span></div>
        <label class="hc-check"><input type="checkbox" id="hcWrote">I have written my master password down</label>
        <button class="hc-btn pri big" type="submit">Make my vault</button>
      </form></div></div>`;
    $('#hcM1').addEventListener('input', e => { $('#hcM1m').innerHTML = meter(e.target.value) + '<span class="hc-hint">At least 10 characters</span>'; });
    $('#hcMk').addEventListener('submit', async e => {
      e.preventDefault();
      const a = $('#hcM1').value, b = $('#hcM2').value;
      if (a.length < 10) return toast('Use at least 10 characters', true);
      if (a !== b) return toast('The two do not match', true);
      if (strength(a).score < 2) return toast('Too easy to guess - make it longer', true);
      if (!$('#hcWrote').checked) return toast('Write your master password down first, then tick the box', true);
      const btn = e.target.querySelector('button'); btn.disabled = true; btn.textContent = 'Making your vault…';
      try {
        const salt = rand(16), raw = rand(32);
        await api('POST', '/api/cred/vault', {salt: b64(salt), iters: ITERS, wrapped: await seal(await kek(a, salt, ITERS), raw)});
        ST.vk = await vkOf(raw); raw.fill(0); ST.items = []; bump();
        ST.meta = await api('GET', '/api/cred/vault'); toast('Your Hoola Cred is ready'); ST.tab = 'all'; draw();
      } catch (err) { toast(err.message, true); btn.disabled = false; btn.textContent = 'Make my vault'; }
    });
  }
  function drawUnlock(msg) {
    const n = (ST.meta.items || []).length;
    EL.innerHTML = `<div class="hcv hc-center"><form class="hc-unlock" id="hcUn" autocomplete="off">
      <span class="hc-badge">${IC.lock.replace('width="16" height="16"', 'width="30" height="30"')}</span>
      <h1 class="hc-h1 big">Welcome back</h1>
      <p class="hc-lead">${msg ? esc(msg) + ' ' : ''}Hoola Cred is locked. ${n} login${n === 1 ? '' : 's'} ${n === 1 ? 'is' : 'are'} waiting.</p>
      <div class="hc-field-col"><label class="hc-lbl" for="hcMp">Master password</label><input class="hc-in" id="hcMp" type="password" autocomplete="current-password" required></div>
      <button class="hc-btn pri big wide" type="submit">Unlock</button>
      <div class="hc-meta"><span>${IC.shield}Unlocked only on this device</span><span>${IC.clock}Locks after ${pref('lock', 10)} min idle</span></div>
      <p class="hc-foot">Forgot it? Nobody can open this vault without it, not even Hoola.</p>
    </form></div>`;
    setTimeout(() => $('#hcMp') && $('#hcMp').focus(), 30);
    $('#hcUn').addEventListener('submit', async e => {
      e.preventDefault();
      const btn = e.target.querySelector('button'); btn.disabled = true; btn.textContent = 'Unlocking…';
      const pw = $('#hcMp').value; $('#hcMp').value = '';
      try { const raw = await unwrap(pw, ST.meta); ST.vk = await vkOf(raw); raw.fill(0); }
      catch { btn.disabled = false; btn.textContent = 'Unlock'; return toast('That is not the master password', true); }
      bump(); await loadItems(); ST.tab = 'all'; draw();
    });
  }
  async function loadItems() {
    const out = [];
    for (const it of ST.meta.items || []) {
      try { out.push({id: it.id, version: it.version, hoola: it.hoola, updated: it.updated, data: await decItem(it)}); }
      catch { out.push({id: it.id, version: it.version, hoola: it.hoola, broken: true, data: {title: '(cannot be opened)'}}); }
    }
    ST.items = out;
    try { ST.uses = (await api('GET', '/api/cred/hoola-uses')).uses || {}; } catch { ST.uses = {}; }
  }
  async function reload() { ST.meta = await api('GET', '/api/cred/vault'); await loadItems(); }

  /* ---------------------------------------------------------------- shell: header + tabs */
  const TABS = [['all', 'All logins'], ['hoola', 'Hoola may use'], ['otp', '2-step codes'], ['safety', 'Safety check'], ['gen', 'Generator'], ['import', 'Import'], ['settings', 'Settings']];
  function issues() {
    const logins = ST.items.filter(i => i.data.password), byPw = {};
    logins.forEach(i => { (byPw[i.data.password] = byPw[i.data.password] || []).push(i); });
    return {logins, byPw, weak: logins.filter(i => strength(i.data.password).score < 2), reused: Object.values(byPw).filter(g => g.length > 1),
            no2: logins.filter(i => !totpSecret(i.data.totp)), breached: ST.breach || []};
  }
  function counts() {
    const s = issues();
    return {all: ST.items.length, hoola: ST.items.filter(i => i.hoola).length, otp: ST.items.filter(i => totpSecret(i.data.totp)).length,
            safety: s.weak.length + s.reused.length + s.breached.length};
  }
  function draw() {
    if (!EL) return;
    if (!ST.vk) return start();
    clearTimers();
    const c = counts();
    EL.innerHTML = `<div class="hcv">
      <header class="hc-head">
        <div class="hc-headrow">
          <div class="hc-titles">
            <span class="hc-pill"><i class="dot ok"></i><span id="hcStatus">${statusLine()}</span></span>
            <h1 class="hc-h1">Hoola Cred</h1>
            <p class="hc-sub">Your passwords and 2-step codes, locked with a master password only you know.</p>
          </div>
          <div class="hc-actions"><button class="hc-btn" type="button" id="hcLock">${IC.lock}Lock now</button><button class="hc-btn pri" type="button" id="hcNew">${IC.plus}New login</button></div>
        </div>
        <nav class="hc-tabs" aria-label="Hoola Cred pages">${TABS.map(([k, n]) => `<button class="hc-tab" type="button" data-tab="${k}" ${ST.tab === k ? 'aria-current="page"' : ''}>${n}${c[k] ? `<b>${c[k]}</b>` : ''}</button>`).join('')}</nav>
      </header>
      <div class="hc-body" id="hcBody"></div></div>`;
    $('#hcLock').addEventListener('click', () => lock('Locked.'));
    $('#hcNew').addEventListener('click', () => newLogin());
    $$('[data-tab]').forEach(b => b.addEventListener('click', () => { ST.tab = b.dataset.tab; ST.edit = null; if (ST.tab !== 'all') ST.sel = ''; draw(); }));
    const B = $('#hcBody');
    if (ST.edit) return drawEdit(B);
    ({all: drawAll, hoola: drawHoola, otp: drawCodes, safety: drawSafety, gen: drawGen, import: drawImport, settings: drawSettings}[ST.tab] || drawAll)(B);
  }
  function newLogin(seed) { ST.tab = 'all'; ST.sel = ''; ST.edit = Object.assign({title: '', username: '', password: NEWPW(), urls: [], totp: '', notes: '', folder: ST.folder || ''}, seed || {}); ST.pwShown = !!(seed && seed.password); draw(); }

  /* ---------------------------------------------------------------- All logins: list + one login */
  function listRows(dim) {
    const q = ST.q.trim().toLowerCase();
    let rows = ST.items.filter(i => !ST.folder || (i.data.folder || '') === ST.folder);
    if (q) rows = rows.filter(i => [i.data.title, i.data.username, ...(i.data.urls || []), i.data.folder].join(' ').toLowerCase().includes(q));
    rows.sort((a, b) => String(a.data.title || '').localeCompare(String(b.data.title || '')));
    if (!rows.length) return `<p class="hc-empty-s">${q ? 'Nothing matches.' : 'Nothing here yet.'}</p>`;
    const groups = {}; rows.forEach(i => { (groups[i.data.folder || 'Other'] = groups[i.data.folder || 'Other'] || []).push(i); });
    const names = Object.keys(groups).sort((a, b) => (a === 'Other') - (b === 'Other') || a.localeCompare(b));
    return names.map(g => `${names.length > 1 ? `<div class="hc-group">${esc(g)}</div>` : ''}${groups[g].map(i => {
      const weak = i.data.password && strength(i.data.password).score < 2;
      return `<button class="hc-row" type="button" data-id="${esc(i.id)}" ${i.id === ST.sel ? 'aria-current="true"' : ''} ${dim ? 'tabindex="-1"' : ''}>${tile(i.data)}
        <span class="hc-rowtext"><b>${esc(i.data.title || '(no title)')}</b><small>${esc([i.data.username, host((i.data.urls || [])[0] || '')].filter(Boolean).join(' · '))}</small></span>
        ${i.hoola ? '<span class="hc-tag acc">Hoola</span>' : weak ? '<span class="hc-tag warn">Weak</span>' : ''}</button>`; }).join('')}`).join('');
  }
  function listPane(dim) {
    const folders = [...new Set(ST.items.map(i => i.data.folder).filter(Boolean))].sort();
    return `<section class="hc-card hc-list${dim ? ' dim' : ''}" aria-label="Logins">
      <div class="hc-listhead"><label class="hc-search">${IC.search}<input id="hcQ" type="search" placeholder="Search ${ST.items.length} login${ST.items.length === 1 ? '' : 's'}" aria-label="Search logins" value="${esc(ST.q)}"></label>
        ${folders.length ? `<label class="hc-sr" for="hcF">Folder</label><select class="hc-select" id="hcF"><option value="">All folders</option>${folders.map(f => `<option ${f === ST.folder ? 'selected' : ''}>${esc(f)}</option>`).join('')}</select>` : ''}</div>
      <div class="hc-rows" id="hcRows">${listRows(dim)}</div></section>`;
  }
  function wireList() {
    const q = $('#hcQ'); if (q) q.addEventListener('input', e => { ST.q = e.target.value; $('#hcRows').innerHTML = listRows(); });
    const f = $('#hcF'); if (f) f.addEventListener('change', e => { ST.folder = e.target.value; $('#hcRows').innerHTML = listRows(); });
    $('#hcRows').addEventListener('click', e => { const b = e.target.closest('[data-id]'); if (b) { ST.sel = b.dataset.id; ST.edit = null; ST.pwShown = false; draw(); } });
  }
  function drawAll(B) {
    if (!ST.items.length) {
      B.innerHTML = `<div class="hc-emptybig"><span class="hc-badge soft">${IC.lock.replace('width="16" height="16"', 'width="26" height="26"')}</span>
        <h2 class="hc-h2">Your vault is empty</h2><p class="hc-lead">Add your first login, or bring them in from Chrome, 1Password or Bitwarden.</p>
        <div class="hc-btnrow"><button class="hc-btn pri" type="button" id="hcE1">${IC.plus}New login</button><button class="hc-btn" type="button" id="hcE2">Import</button></div></div>`;
      $('#hcE1').addEventListener('click', () => newLogin()); $('#hcE2').addEventListener('click', () => { ST.tab = 'import'; draw(); });
      return;
    }
    const it = ST.items.find(i => i.id === ST.sel);
    B.innerHTML = `<div class="hc-split${it ? ' open' : ''}">${listPane()}<section class="hc-card hc-detail" id="hcDetail" aria-label="Login"></section></div>`;
    wireList();
    const D = $('#hcDetail');
    if (!it) { D.innerHTML = `<div class="hc-pick"><p>Pick a login on the left to see it here.</p></div>`; return; }
    drawDetail(D, it);
  }
  function drawDetail(D, it) {
    const d = it.data, use = ST.uses[it.id] || {}, money = isMoney(d), s = d.password ? strength(d.password) : null;
    D.innerHTML = `<button class="hc-btn sm hc-back" type="button" id="hcBack">← All logins</button>
      <div class="hc-dhead">${tile(d, 'lg')}<div class="hc-dtitle"><h2 class="hc-h2">${esc(d.title || '(no title)')}</h2><span>${esc([d.folder, d.updated ? 'edited ' + when(d.updated).toLowerCase() : ''].filter(Boolean).join(' · '))}</span></div>
        <button class="hc-btn sm" type="button" id="hcEdit">Edit</button><button class="hc-btn sm bad" type="button" id="hcDel">Delete</button></div>
      <div class="hc-fields">
        ${d.username ? `<div class="hc-f"><span class="k">User name</span><span class="v mono">${esc(d.username)}</span><button class="hc-btn sm" type="button" data-copy="username">Copy</button></div>` : ''}
        ${d.password ? `<div class="hc-f"><span class="k">Password</span><span class="v mono pw" id="hcPw">${ST.pwShown ? esc(d.password) : '••••••••••••••'}</span><span class="hc-tag ${s.tone}">${s.label}</span>
          <button class="hc-btn sm" type="button" id="hcShow">${ST.pwShown ? 'Hide' : 'Show'}</button><button class="hc-btn sm" type="button" data-copy="password">Copy</button></div>` : ''}
        ${totpSecret(d.totp) ? `<div class="hc-f"><span class="k">2-step code</span><span class="v hc-otp"><span class="code" id="hcOtp">··· ···</span><span id="hcRing"></span><span class="hc-secs" id="hcSecs"></span></span><button class="hc-btn sm" type="button" id="hcCopyOtp">Copy</button></div>` : ''}
        ${(d.urls || []).map(u => `<div class="hc-f"><span class="k">Website</span><a class="v" href="${esc(/:\/\//.test(u) ? u : 'https://' + u)}" target="_blank" rel="noopener noreferrer">${esc(u)}</a></div>`).join('')}
        ${d.notes ? `<div class="hc-f"><span class="k">Note</span><span class="v" style="white-space:pre-wrap">${esc(d.notes)}</span></div>` : ''}
      </div>
      ${money ? `<div class="hc-hcard muted"><span class="hc-hico">${IC.lock}</span><span><b>A bank or payment login</b>Hoola never uses these. They stay for you alone.</span></div>`
        : `<div class="hc-hcard"><span class="hc-hico">${IC.pc}</span><span><b>Hoola may use this login</b>${it.hoola
            ? `The Hoola PC signs in to ${esc((use.sites || [host((d.urls || [])[0] || '')]).filter(Boolean).join(', ') || 'this site')} only when you tap “Use saved sign-in”${totpSecret(d.totp) ? ', and fills the 2-step code for you' : ''}. ${use.used ? 'Last used ' + esc(when(use.used).toLowerCase()) + '.' : 'Not used yet.'}`
            : 'Switch on to let the Hoola PC sign in to this site for you, only when you tap. You can switch it off any time.'}</span>
          <button class="hc-sw" type="button" id="hcHoola" role="switch" aria-checked="${it.hoola}" aria-label="Hoola may use ${esc(d.title || 'this login')}"></button></div>`}`;
    $('#hcBack').addEventListener('click', () => { ST.sel = ''; draw(); });
    $$('[data-copy]').forEach(b => b.addEventListener('click', () => copy(d[b.dataset.copy], b.dataset.copy === 'password' ? 'Password' : 'User name')));
    const sh = $('#hcShow'); if (sh) sh.addEventListener('click', () => { ST.pwShown = !ST.pwShown; $('#hcPw').textContent = ST.pwShown ? d.password : '••••••••••••••'; sh.textContent = ST.pwShown ? 'Hide' : 'Show'; });
    if (totpSecret(d.totp)) {
      const tick = async () => { const o = $('#hcOtp'); if (!o) return; o.textContent = fmtCode(await totp(d.totp)); const l = left();
        $('#hcRing').innerHTML = ring(l / 30, 22, 4, 'var(--pri)', `${l} seconds left`); $('#hcSecs').textContent = `${l} s`; };
      tick(); ST.timers.push(setInterval(tick, 1000));
      $('#hcCopyOtp').addEventListener('click', async () => copy(await totp(d.totp), '2-step code'));
    }
    $('#hcEdit').addEventListener('click', () => { ST.edit = {...d, urls: [...(d.urls || [])], _id: it.id, _hoola: it.hoola}; ST.pwShown = false; draw(); });
    $('#hcDel').addEventListener('click', async () => {
      if (!confirm(`Delete "${d.title || 'this login'}"? This cannot be undone.`)) return;
      try { await api('DELETE', `/api/cred/items/${enc(it.id)}`); await reload(); ST.sel = ''; toast('Deleted'); draw(); } catch (e) { toast(e.message, true); }
    });
    const hs = $('#hcHoola'); if (hs) hs.addEventListener('click', () => setHoola(it, !it.hoola));
  }
  async function setHoola(it, on) {
    const d = it.data;
    try {
      await api('PUT', `/api/cred/items/${enc(it.id)}/hoola`, on ? {on: true, title: d.title, username: d.username, password: d.password, urls: d.urls || [], totp: d.totp || ''} : {on: false});
      await reload(); toast(on ? `Hoola may now use ${d.title} - only on your tap` : `Hoola's copy of ${d.title} is removed`); draw();
    } catch (e) { toast(e.message, true); }
  }

  /* ---------------------------------------------------------------- New / edit */
  function drawEdit(B) {
    const e = ST.edit, isNew = !e._id;
    B.innerHTML = `<div class="hc-split open edit">${listPane(true)}<form class="hc-card hc-detail hc-editor" id="hcEf" autocomplete="off" aria-label="${isNew ? 'New login' : 'Edit login'}">
      <div class="hc-edhead"><h2 class="hc-h2">${isNew ? 'New login' : 'Edit ' + esc(e.title || 'login')}</h2><span class="hc-hint">Locked on this device before it is saved</span></div>
      <div class="hc-grid2">
        <div><label class="hc-lbl" for="hcEt">Name</label><input class="hc-in" id="hcEt" value="${esc(e.title)}" placeholder="GST portal" required></div>
        <div><label class="hc-lbl" for="hcEw">Website</label><input class="hc-in" id="hcEw" value="${esc((e.urls || []).join(', '))}" placeholder="https://services.gst.gov.in" spellcheck="false"></div>
        <div><label class="hc-lbl" for="hcEu">User name</label><input class="hc-in mono" id="hcEu" value="${esc(e.username)}" autocomplete="off" spellcheck="false"></div>
        <div><label class="hc-lbl" for="hcEf2">Folder</label><input class="hc-in" id="hcEf2" value="${esc(e.folder)}" placeholder="Government, Work, Family…" list="hcFolders"><datalist id="hcFolders">${[...new Set(ST.items.map(i => i.data.folder).filter(Boolean))].map(f => `<option value="${esc(f)}">`).join('')}</datalist></div>
      </div>
      <div><label class="hc-lbl" for="hcEp">Password</label><div class="hc-inrow"><input class="hc-in mono" id="hcEp" type="${ST.pwShown ? 'text' : 'password'}" value="${esc(e.password)}" autocomplete="new-password" spellcheck="false">
        <button class="hc-btn" type="button" id="hcEpShow">${ST.pwShown ? 'Hide' : 'Show'}</button><button class="hc-btn" type="button" id="hcEpGen">${IC.redo}New one</button></div>
        <div class="hc-mrow" id="hcEpM">${meter(e.password, true)}</div></div>
      <div><label class="hc-lbl" for="hcEo">2-step key <span class="hc-hint">(optional · the setup key or otpauth:// link the site shows)</span></label><input class="hc-in mono" id="hcEo" value="${esc(e.totp)}" spellcheck="false"></div>
      <div><label class="hc-lbl" for="hcEn">Note</label><textarea class="hc-in hc-ta" id="hcEn">${esc(e.notes)}</textarea></div>
      <div class="hc-hcard" id="hcEhCard"><span><b>Hoola may use this login</b><span id="hcEhTxt"></span></span>
        <button class="hc-sw" type="button" id="hcEh" role="switch" aria-checked="${!!e._hoola}" aria-label="Hoola may use this login"></button></div>
      <div class="hc-btnrow end"><button class="hc-btn" type="button" id="hcCancel">Cancel</button><button class="hc-btn pri" type="submit">Save login</button></div>
    </form></div>`;
    let hoola = !!e._hoola;
    const sync = () => { const money = isMoney({title: $('#hcEt').value, urls: [$('#hcEw').value]}); const card = $('#hcEhCard'), sw = $('#hcEh');
      if (money) { hoola = false; card.classList.add('muted'); sw.disabled = true; $('#hcEhTxt').textContent = 'A bank or payment login - Hoola never uses these.'; }
      else { card.classList.remove('muted'); sw.disabled = false; $('#hcEhTxt').textContent = 'Sent once, sealed for the Hoola PC, used only on your tap. Never for bank or payment sites.'; }
      sw.setAttribute('aria-checked', String(hoola)); };
    sync(); ['hcEt', 'hcEw'].forEach(id => $('#' + id).addEventListener('input', sync));
    $('#hcEh').addEventListener('click', () => { hoola = !hoola; sync(); });
    $('#hcEp').addEventListener('input', ev => { $('#hcEpM').innerHTML = meter(ev.target.value, true); });
    $('#hcEpShow').addEventListener('click', ev => { const p = $('#hcEp'); ST.pwShown = p.type === 'password'; p.type = ST.pwShown ? 'text' : 'password'; ev.currentTarget.textContent = ST.pwShown ? 'Hide' : 'Show'; });
    $('#hcEpGen').addEventListener('click', () => { const p = $('#hcEp'); p.value = NEWPW(); p.type = 'text'; ST.pwShown = true; $('#hcEpShow').textContent = 'Hide'; $('#hcEpM').innerHTML = meter(p.value, true); });
    $('#hcCancel').addEventListener('click', () => { ST.edit = null; draw(); });
    $('#hcEf').addEventListener('submit', async ev => {
      ev.preventDefault();
      const now = new Date().toISOString();
      const data = {title: $('#hcEt').value.trim(), username: $('#hcEu').value.trim(), password: $('#hcEp').value,
        urls: $('#hcEw').value.split(/[\s,]+/).map(s => s.trim()).filter(Boolean).slice(0, 10), totp: $('#hcEo').value.trim(),
        folder: $('#hcEf2').value.trim(), notes: $('#hcEn').value, created: e.created || now, updated: now};
      if (!data.title) return toast('Give it a name', true);
      if (data.totp && !totpSecret(data.totp)) return toast('That 2-step key is not valid', true);
      if (hoola && !data.urls.length) return toast('Add the website, so Hoola knows where to use it', true);
      const btn = ev.target.querySelector('[type=submit]'); btn.disabled = true; btn.textContent = 'Saving…';
      try {
        const box = await encItem(data);
        let id = e._id;
        if (isNew) id = (await api('POST', '/api/cred/items', box)).id;
        else await api('PUT', `/api/cred/items/${enc(id)}`, {...box, version: ST.items.find(i => i.id === id).version});
        if (hoola || e._hoola) await api('PUT', `/api/cred/items/${enc(id)}/hoola`, hoola ? {on: true, title: data.title, username: data.username, password: data.password, urls: data.urls, totp: data.totp} : {on: false});
        await reload(); ST.edit = null; ST.sel = id; ST.pwShown = false; toast('Saved'); draw();
      } catch (err) { btn.disabled = false; btn.textContent = 'Save login'; toast(err.message, true); if (!isNew) await reload().catch(() => {}); }
    });
    setTimeout(() => { const t = $('#hcEt'); if (t && !t.value) t.focus(); }, 30);
  }

  /* ---------------------------------------------------------------- Hoola may use */
  function drawHoola(B) {
    const rows = ST.items.slice().sort((a, b) => (b.hoola - a.hoola) || String(a.data.title).localeCompare(String(b.data.title)));
    B.innerHTML = `<div class="hc-steps">
        <div class="hc-card hc-step"><span class="n">1</span><span><b>You switch a login on</b>Your device sends it once; it is sealed for the Hoola PC.</span></div>
        <div class="hc-card hc-step"><span class="n">2</span><span><b>The site asks to sign in</b>Hoola stops and shows you “Use saved sign-in”.</span></div>
        <div class="hc-card hc-step"><span class="n">3</span><span><b>Your tap, then it signs in</b>The 2-step code is filled too. The AI never sees either.</span></div></div>
      <section class="hc-card hc-table" aria-label="Logins Hoola may use">
        <div class="hc-tr th"><span>Login</span><span>Sites it opens</span><span>2-step code</span><span>Last used by Hoola</span><span>Allowed</span></div>
        ${rows.length ? rows.map(i => { const d = i.data, u = ST.uses[i.id] || {}, money = isMoney(d), sites = (u.sites && u.sites.length ? u.sites : (d.urls || []).map(host)).filter(Boolean).join(', ');
          if (money) return `<div class="hc-tr muted"><span class="hc-who">${tile({title: d.title})}<b>${esc(d.title)}</b></span><span>${esc(sites || '—')}</span><span class="span2"><span class="hc-tag bad">Bank or payment login · never given to Hoola</span></span><span class="hc-lockic">${IC.lock}</span></div>`;
          return `<div class="hc-tr"><span class="hc-who">${tile(d)}<b>${esc(d.title || '(no title)')}</b></span><span>${esc(sites || 'Add its website first')}</span>
            <span>${totpSecret(d.totp) ? `<span class="hc-tag ok">${i.hoola ? 'Filled by Hoola' : 'Has a code'}</span>` : '<span class="hc-tag">None</span>'}</span>
            <span class="hc-mut">${i.hoola ? esc(u.used ? when(u.used) : 'Not yet') : '—'}</span>
            <span><button class="hc-sw" type="button" data-hoola="${esc(i.id)}" role="switch" aria-checked="${i.hoola}" aria-label="Hoola may use ${esc(d.title || 'this login')}" ${(d.urls || []).length && d.password ? '' : 'disabled'}></button></span></div>`; }).join('')
          : '<p class="hc-empty-s">No logins yet.</p>'}
      </section>
      <p class="hc-foot">Switching a login off removes Hoola's copy at once. Every use is shown in that task's chat.</p>`;
    $$('[data-hoola]').forEach(b => b.addEventListener('click', () => { const it = ST.items.find(i => i.id === b.dataset.hoola); if (it) setHoola(it, !it.hoola); }));
  }

  /* ---------------------------------------------------------------- 2-step codes */
  function drawCodes(B) {
    const rows = ST.items.filter(i => totpSecret(i.data.totp)).sort((a, b) => String(a.data.title).localeCompare(String(b.data.title)));
    B.innerHTML = `${rows.length ? `<div class="hc-codehead"><span id="hcCRing"></span><span>All codes change in <b id="hcCSecs">${left()}</b> seconds. Your authenticator app, built in.</span></div>
      <div class="hc-codes">${rows.map(i => `<div class="hc-card hc-code"><div class="hc-who">${tile(i.data)}<span class="hc-rowtext"><b>${esc(i.data.title)}</b><small>${esc(i.data.username || '')}</small></span>${i.hoola ? '<span class="hc-tag acc">Hoola</span>' : ''}</div>
        <div class="hc-coderow"><span class="code" data-code="${esc(i.id)}">··· ···</span><button class="hc-btn sm" type="button" data-copycode="${esc(i.id)}">Copy</button></div></div>`).join('')}</div>` : ''}
      <div class="hc-card hc-add"><span class="hc-addic">${IC.plus}</span><span><b>Add a 2-step code</b>On the site, turn on “authenticator app”, then paste the setup key into that login here.</span>${rows.length ? '' : '<button class="hc-btn" type="button" id="hcGoAll">Open a login</button>'}</div>`;
    const tick = async () => {
      const l = left(); const r = $('#hcCRing'); if (!r) return;
      r.innerHTML = ring(l / 30, 40, 3.5, 'var(--pri)', `${l} seconds until new codes`); $('#hcCSecs').textContent = l;
      for (const i of rows) { const el = $(`[data-code="${CSS.escape(i.id)}"]`); if (el) el.textContent = fmtCode(await totp(i.data.totp)); }
    };
    if (rows.length) { tick(); ST.timers.push(setInterval(tick, 1000)); }
    $$('[data-copycode]').forEach(b => b.addEventListener('click', async () => { const i = ST.items.find(x => x.id === b.dataset.copycode); if (i) copy(await totp(i.data.totp), '2-step code'); }));
    const g = $('#hcGoAll'); if (g) g.addEventListener('click', () => { ST.tab = 'all'; draw(); });
  }

  /* ---------------------------------------------------------------- Safety check */
  async function runBreach() {
    if (ST.breachBusy) return; ST.breachBusy = true;
    const {byPw} = issues(), hits = [];
    try {
      for (const [pw, group] of Object.entries(byPw)) {
        const h = await sha1hex(pw), body = await api('GET', `/api/cred/pwned/${h.slice(0, 5)}`, undefined, true);
        const line = body.split('\n').find(l => l.split(':')[0].trim() === h.slice(5)), n = line ? parseInt(line.split(':')[1], 10) : 0;
        if (n > 0) group.forEach(i => hits.push({item: i, n}));
      }
      ST.breach = hits; ST.breachAt = new Date().toISOString();
    } catch { ST.breach = []; ST.breachFail = true; toast('The breach check is not reachable right now.', true); }
    ST.breachBusy = false;
    if (ST.tab === 'safety' && ST.vk) draw();
  }
  function drawSafety(B) {
    const s = issues();
    if (ST.breach === null && !ST.breachBusy && s.logins.length) runBreach();
    const score = Math.max(0, 100 - s.weak.length * 8 - s.reused.length * 6 - s.breached.length * 15 - s.no2.length * 2);
    const fix = s.weak.length + s.reused.length + s.breached.length;
    const tone = score >= 80 ? 'var(--ok)' : score >= 55 ? 'var(--warn)' : 'var(--bad)';
    const go = i => `<button class="hc-link" type="button" data-go="${esc(i.id)}">${esc(i.data.title)}</button>`;
    const li = (i, label) => `<div class="hc-irow">${tile(i.data, 'sm')}<span>${esc(i.data.title)}</span><button class="hc-btn sm" type="button" data-fix="${esc(i.id)}">${label}</button></div>`;
    const bTag = ST.breach === null ? (ST.breachBusy ? 'Checking' : 'Not checked') : ST.breachFail ? 'Not reachable' : s.breached.length ? 'Change now' : 'All clear';
    B.innerHTML = `<div class="hc-safety">
      <section class="hc-card hc-score" aria-label="Vault health">
        <div class="hc-big">${ring(s.logins.length ? score / 100 : 0, 168, 3.2, tone, `Health ${score} out of 100`)}<span><b>${s.logins.length ? score : '—'}</b><small>out of 100</small></span></div>
        <h2 class="hc-h2">${!s.logins.length ? 'Nothing to check yet' : !fix ? (score >= 90 ? 'Looking strong' : 'Good') : score >= 80 ? `Good, ${fix} to fix` : score >= 55 ? `${fix} things to fix` : `Needs work: ${fix} to fix`}</h2>
        <p class="hc-lead sm">Worked out on this device. The breach check sends only the first 5 characters of each password's fingerprint, never the password.</p>
        <button class="hc-btn pri wide" type="button" id="hcRecheck" ${ST.breachBusy ? 'disabled' : ''}>${ST.breachBusy ? 'Checking…' : 'Check again'}</button>
        <span class="hc-hint">${ST.breachAt ? 'Last checked ' + esc(when(ST.breachAt).toLowerCase()) : ''}</span>
      </section>
      <div class="hc-issues">
        <div class="hc-card hc-issue"><div class="hc-ihead"><span class="n ${s.weak.length ? 'warn' : 'ok'}">${s.weak.length}</span><span class="hc-tag ${s.weak.length ? 'warn' : 'ok'}">${s.weak.length ? 'Fix soon' : 'All clear'}</span></div><b>Weak passwords</b>
          ${s.weak.map(i => li(i, 'Make strong')).join('') || '<span class="hc-mut">None - good.</span>'}</div>
        <div class="hc-card hc-issue"><div class="hc-ihead"><span class="n ${s.reused.length ? 'warn' : 'ok'}">${s.reused.length}</span><span class="hc-tag ${s.reused.length ? 'warn' : 'ok'}">${s.reused.length ? 'Fix soon' : 'All clear'}</span></div><b>Used on more than one site</b>
          ${s.reused.map(g => `<div class="hc-irow">${tile(g[0].data, 'sm')}<span>${g.map(go).join(' and ')} share one</span><button class="hc-btn sm" type="button" data-fix="${esc(g[1].id)}">Change one</button></div>`).join('') || '<span class="hc-mut">None - good.</span>'}</div>
        <div class="hc-card hc-issue"><div class="hc-ihead"><span class="n ${s.breached.length ? 'bad' : 'ok'}">${ST.breach === null ? '·' : s.breached.length}</span><span class="hc-tag ${s.breached.length ? 'bad' : ST.breachFail ? 'warn' : 'ok'}">${bTag}</span></div><b>Found in data breaches</b>
          ${ST.breach === null ? '<span class="hc-mut">Checking your passwords against known leaks…</span>' : ST.breachFail ? '<span class="hc-mut">The check could not reach the breach list. Try again in a moment.</span>' : s.breached.map(h => `<div class="hc-irow">${tile(h.item.data, 'sm')}<span>${esc(h.item.data.title)} · seen ${h.n.toLocaleString()} times</span><button class="hc-btn sm" type="button" data-fix="${esc(h.item.id)}">Change</button></div>`).join('') || `<span class="hc-mut">None of your ${s.logins.length} passwords appear in known leaks.</span>`}</div>
        <div class="hc-card hc-issue"><div class="hc-ihead"><span class="n acc">${s.no2.length}</span><span class="hc-tag acc">Suggested</span></div><b>Logins without a 2-step code</b>
          <span class="hc-mut">${s.no2.length ? s.no2.slice(0, 3).map(go).join(', ') + (s.no2.length > 3 ? ` and ${s.no2.length - 3} more` : '') + '. Turn on the site\'s authenticator option and paste its key here.' : 'Every login has one - great.'}</span></div>
      </div></div>`;
    $('#hcRecheck').addEventListener('click', () => { ST.breach = null; ST.breachFail = false; runBreach(); draw(); });
    $$('[data-go]').forEach(b => b.addEventListener('click', () => { ST.tab = 'all'; ST.sel = b.dataset.go; draw(); }));
    $$('[data-fix]').forEach(b => b.addEventListener('click', () => { const it = ST.items.find(i => i.id === b.dataset.fix); if (!it) return;
      ST.tab = 'all'; ST.sel = it.id; ST.edit = {...it.data, urls: [...(it.data.urls || [])], password: NEWPW(), _id: it.id, _hoola: it.hoola}; ST.pwShown = true; draw();
      toast('A new strong password is filled in - change it on the site too, then save'); }));
  }

  /* ---------------------------------------------------------------- Generator */
  function drawGen(B) {
    const o = ST.gen;
    const cur = o.mode === 'pin' ? (o.pin || 6) : o.len;
    B.innerHTML = `<section class="hc-gen" aria-label="Password generator">
      <div class="hc-seg" role="group" aria-label="Kind">${[['random', 'Random'], ['say', 'Easy to say'], ['pin', 'PIN']].map(([k, n]) => `<button type="button" data-mode="${k}" aria-pressed="${o.mode === k}">${n}</button>`).join('')}</div>
      <div class="hc-genbox"><output class="hc-genout" id="hcGv"></output><div class="hc-mrow" id="hcGm"></div>
        <div class="hc-btnrow"><button class="hc-btn pri" type="button" id="hcGc">Copy</button><button class="hc-btn" type="button" id="hcGn">${IC.redo}New one</button><button class="hc-btn" type="button" id="hcGs">Save as a new login</button></div></div>
      <div class="hc-opts">
        <div class="hc-opt"><label for="hcGl">${o.mode === 'say' ? 'Words' : 'Length'}</label><span class="hc-range"><input id="hcGl" type="range" min="${o.mode === 'pin' ? 4 : o.mode === 'say' ? 15 : 8}" max="${o.mode === 'pin' ? 12 : o.mode === 'say' ? 40 : 64}" step="${o.mode === 'say' ? 5 : 1}" value="${cur}"><b id="hcGlv"></b></span></div>
        ${o.mode === 'pin' ? '' : `<div class="hc-opt"><span>${o.mode === 'say' ? 'Capital first letter' : 'Capital letters (A–Z)'}</span><button class="hc-sw" type="button" data-o="upper" role="switch" aria-checked="${!!o.upper}" aria-label="Capital letters"></button></div>
        <div class="hc-opt"><span>Numbers (0–9)</span><button class="hc-sw" type="button" data-o="digits" role="switch" aria-checked="${!!o.digits}" aria-label="Numbers"></button></div>
        ${o.mode === 'say' ? '' : `<div class="hc-opt"><span>Symbols (! @ # $)</span><button class="hc-sw" type="button" data-o="symbols" role="switch" aria-checked="${!!o.symbols}" aria-label="Symbols"></button></div>
        <div class="hc-opt"><span>Skip look-alikes (0 O 1 l I)</span><button class="hc-sw" type="button" data-o="plain" role="switch" aria-checked="${!!o.plain}" aria-label="Skip look-alikes"></button></div>`}`}
      </div>
      <p class="hc-foot">Made on this device. Nothing you generate is kept unless you save it.</p></section>`;
    const make = () => {
      const len = +$('#hcGl').value, v = generate({...o, len});
      if (o.mode === 'pin') o.pin = len; else o.len = len;
      $('#hcGlv').textContent = o.mode === 'say' ? Math.round(len / 5) : len;
      $('#hcGv').innerHTML = [...v].map(ch => /[A-Za-z]/.test(ch) ? esc(ch) : /\d/.test(ch) ? `<span class="d">${esc(ch)}</span>` : `<span class="s">${esc(ch)}</span>`).join('');
      $('#hcGv').dataset.v = v; $('#hcGm').innerHTML = meter(v, true);
    };
    make();
    $('#hcGl').addEventListener('input', make);
    $('#hcGn').addEventListener('click', make);
    $('#hcGc').addEventListener('click', () => copy($('#hcGv').dataset.v, o.mode === 'pin' ? 'PIN' : 'Password'));
    $('#hcGs').addEventListener('click', () => newLogin({password: $('#hcGv').dataset.v}));
    $$('[data-mode]').forEach(b => b.addEventListener('click', () => { o.mode = b.dataset.mode; if (o.mode === 'say' && (o.len < 15 || o.len > 40)) o.len = 20; if (o.mode === 'random' && (o.len < 8 || o.len > 64)) o.len = 18; draw(); }));
    $$('[data-o]').forEach(b => b.addEventListener('click', () => { o[b.dataset.o] = o[b.dataset.o] ? 0 : 1; b.setAttribute('aria-checked', String(!!o[b.dataset.o])); make(); }));
  }

  /* ---------------------------------------------------------------- Import */
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
      const g = i => (i >= 0 ? String(r[i] || '').trim() : ''), url = g(c.url);
      return {title: g(c.title) || host(url) || 'Imported login', username: g(c.user), password: g(c.pw), urls: url ? url.split(/[\s,]+/).filter(Boolean).slice(0, 10) : [],
              totp: totpSecret(g(c.totp)) ? g(c.totp) : '', notes: g(c.notes), folder: g(c.folder)};
    }).filter(x => x.password);
  }
  const already = x => ST.items.some(i => (i.data.username || '') === (x.username || '') && ((i.data.title || '').toLowerCase() === (x.title || '').toLowerCase()
    || (x.urls[0] && (i.data.urls || []).some(u => host(u) && host(u) === host(x.urls[0])))));
  function drawImport(B) {
    const src = ST.impSrc || 'chrome';
    const S = {chrome: ['Chrome', 'Settings › Passwords › Export passwords. You get a .csv file.'], onepw: ['1Password', 'File › Export › your account › CSV.'], bitwarden: ['Bitwarden', 'Tools › Export vault › .csv format.']};
    const imp = ST.imp, on = imp ? imp.rows.filter(r => r.on).length : 0;
    B.innerHTML = `<div class="hc-srcs">${Object.entries(S).map(([k, [n, t]]) => `<button class="hc-card hc-src" type="button" data-src="${k}" aria-pressed="${src === k}"><b>${n}</b><span>${t}</span></button>`).join('')}</div>
      <label class="hc-drop" for="hcFile"><span class="hc-addic">${IC.file}</span><span class="hc-rowtext"><b>${imp ? esc(imp.name) : 'Choose the .csv file'}</b><small>${imp ? `${imp.rows.length} login${imp.rows.length === 1 ? '' : 's'} found · read on this device, never uploaded as it is` : `From ${S[src][0]}, or any sheet with a password column`}</small></span>
        <span class="hc-btn">${imp ? 'Choose another file' : 'Choose file'}</span><input type="file" id="hcFile" accept=".csv,text/csv" class="hc-sr"></label>
      ${imp ? `<section class="hc-card hc-table imp" aria-label="Preview">
        <div class="hc-tr th"><span><input type="checkbox" id="hcAllChk" aria-label="Select all" ${imp.rows.every(r => r.on) ? 'checked' : ''}></span><span>Name</span><span>Website</span><span>User name</span><span>Status</span></div>
        ${imp.rows.slice(0, 200).map((r, i) => `<div class="hc-tr"><span><input type="checkbox" data-imp="${i}" ${r.on ? 'checked' : ''} aria-label="Import ${esc(r.x.title)}"></span><b>${esc(r.x.title)}</b><span>${esc(host(r.x.urls[0] || '') || '—')}</span><span class="hc-mut">${esc(r.x.username || '—')}</span>
          <span><span class="hc-tag ${r.dup ? 'warn' : 'ok'}">${r.dup ? 'Already here' : 'New'}</span></span></div>`).join('')}
        ${imp.rows.length > 200 ? `<div class="hc-tr"><span></span><span class="hc-mut">… and ${imp.rows.length - 200} more (all imported if ticked)</span></div>` : ''}
      </section>
      <div class="hc-btnrow"><button class="hc-btn pri" type="button" id="hcDoImp">Import ${on} login${on === 1 ? '' : 's'}</button>
        <span class="hc-hint">Each one is locked here before it is saved. Delete the .csv file afterwards; it is not locked.</span></div>` : ''}`;
    $$('[data-src]').forEach(b => b.addEventListener('click', () => { ST.impSrc = b.dataset.src; draw(); }));
    $('#hcFile').addEventListener('change', async e => {
      const f = e.target.files[0]; if (!f) return;
      if (f.size > 5 * 1024 * 1024) return toast('That file is too big', true);
      const rows = csv(await f.text()); e.target.value = '';
      const items = rows.length > 1 ? mapRows(rows) : null;
      if (!items || !items.length) return toast('No logins with a password column were found in that file', true);
      ST.imp = {name: f.name, rows: items.map(x => { const dup = already(x); return {x, dup, on: !dup}; })}; draw();
    });
    if (!imp) return;
    const recount = () => { const n = imp.rows.filter(r => r.on).length; $('#hcDoImp').textContent = `Import ${n} login${n === 1 ? '' : 's'}`; };
    $('#hcAllChk').addEventListener('change', e => { imp.rows.forEach(r => { r.on = e.target.checked; }); $$('[data-imp]').forEach(c => { c.checked = e.target.checked; }); recount(); });
    $$('[data-imp]').forEach(c => c.addEventListener('change', () => { imp.rows[+c.dataset.imp].on = c.checked; recount(); }));
    $('#hcDoImp').addEventListener('click', async ev => {
      const todo = imp.rows.filter(r => r.on); if (!todo.length) return toast('Tick at least one login', true);
      ev.target.disabled = true; let n = 0;
      for (const r of todo) {
        try { const now = new Date().toISOString(); await api('POST', '/api/cred/items', await encItem({...r.x, created: now, updated: now})); n++; ev.target.textContent = `Importing ${n} of ${todo.length}…`; }
        catch (err) { toast(err.message, true); break; }
      }
      await reload(); ST.imp = null; toast(`${n} imported. Now delete the .csv file from your computer.`); ST.tab = 'all'; draw();
    });
  }

  /* ---------------------------------------------------------------- Settings */
  function drawSettings(B) {
    const sel = (id, k, opts, d) => `<label class="hc-sr" for="${id}">${k === 'lock' ? 'Lock after' : 'Clear copied passwords after'}</label><select class="hc-select" id="${id}">${opts.map(([v, n]) => `<option value="${v}" ${pref(k, d) === v ? 'selected' : ''}>${n}</option>`).join('')}</select>`;
    const hn = ST.items.filter(i => i.hoola).length;
    B.innerHTML = `<div class="hc-settings">
      <div><h2 class="hc-cap">Lock</h2><div class="hc-card hc-srows">
        <div class="hc-sr-row"><span><b>Master password</b>Changing it re-locks the key on this device; your logins stay as they are.</span><button class="hc-btn sm" type="button" id="hcChg">${ST.master ? 'Close' : 'Change'}</button></div>
        ${ST.master ? `<form class="hc-sr-form" id="hcCm" autocomplete="off">
          <input class="hc-in" id="hcC0" type="password" placeholder="Current master password" autocomplete="current-password" required aria-label="Current master password">
          <input class="hc-in" id="hcC1" type="password" placeholder="New master password (10+ characters)" autocomplete="new-password" required minlength="10" aria-label="New master password">
          <input class="hc-in" id="hcC2" type="password" placeholder="New master password again" autocomplete="new-password" required aria-label="New master password again">
          <div class="hc-btnrow"><button class="hc-btn pri" type="submit">Change it</button></div></form>` : ''}
        <div class="hc-sr-row"><span><b>Lock after</b>When you stop using Hoola Cred on this device.</span>${sel('hcLockSel', 'lock', [[5, '5 minutes'], [10, '10 minutes'], [30, '30 minutes'], [60, '1 hour']], 10)}</div>
        <div class="hc-sr-row"><span><b>Clear copied passwords</b>From the clipboard after you copy one.</span>${sel('hcClipSel', 'clip', [[15, '15 seconds'], [30, '30 seconds'], [60, '1 minute']], 30)}</div>
      </div>
      <h2 class="hc-cap">Hoola</h2><div class="hc-card hc-srows"><div class="hc-sr-row"><span><b>Logins Hoola may use</b>${hn} login${hn === 1 ? '' : 's'} · switch any off at once.</span><button class="hc-btn sm" type="button" id="hcRev">Review</button></div></div></div>
      <div><h2 class="hc-cap">Your devices</h2><div class="hc-card hc-srows">
        <div class="hc-sr-row"><span class="hc-addic">${IC.globe}</span><span><b>Hoola extension in Chrome or Edge</b>Fills a sign-in on your click. Pair it once with your phone's code, then unlock it with your master password.</span></div>
        <div class="hc-sr-row"><span class="hc-addic">${IC.phone}</span><span><b>Hoola app on your phone</b>Tools › Hoola Cred opens this same vault with your master password.</span></div>
      </div>
      <h2 class="hc-cap">Danger zone</h2><div class="hc-card hc-srows danger"><div class="hc-sr-row"><span><b>Delete my vault</b>Every login and 2-step code, and Hoola's copies, gone for good.</span><button class="hc-btn sm bad" type="button" id="hcDv">Delete vault</button></div></div></div>
    </div>`;
    $('#hcChg').addEventListener('click', () => { ST.master = !ST.master; draw(); });
    $('#hcLockSel').addEventListener('change', e => { setPref('lock', +e.target.value); bump(); toast(`Hoola Cred now locks after ${e.target.selectedOptions[0].textContent}`); const p = $('#hcStatus'); if (p) p.textContent = statusLine(); });
    $('#hcClipSel').addEventListener('change', e => { setPref('clip', +e.target.value); toast('Saved'); });
    $('#hcRev').addEventListener('click', () => { ST.tab = 'hoola'; draw(); });
    const cm = $('#hcCm');
    if (cm) cm.addEventListener('submit', async e => {
      e.preventDefault();
      const a = $('#hcC1').value; if (a !== $('#hcC2').value) return toast('The two new ones do not match', true);
      if (a.length < 10 || strength(a).score < 2) return toast('Make the new one longer', true);
      let raw; try { raw = await unwrap($('#hcC0').value, ST.meta); } catch { return toast('The current master password is wrong', true); }
      try {
        const salt = rand(16);
        await api('PUT', '/api/cred/vault', {salt: b64(salt), iters: ITERS, wrapped: await seal(await kek(a, salt, ITERS), raw)});
        raw.fill(0); ST.meta = await api('GET', '/api/cred/vault'); ST.master = false; toast('Master password changed'); draw();
      } catch (err) { toast(err.message, true); }
    });
    $('#hcDv').addEventListener('click', async () => {
      if (prompt('Type DELETE to delete every login and code in Hoola Cred') !== 'DELETE') return;
      try { await api('DELETE', '/api/cred/vault?confirm=DELETE'); ST.vk = null; ST.items = []; toast('Hoola Cred deleted'); start(); } catch (e) { toast(e.message, true); }
    });
  }

  return {
    open(el) { EL = el; bump(); if (ST.vk) draw(); else start(); },
    leave() { clearTimers(); },
    locked: () => !ST.vk,
  };
};
