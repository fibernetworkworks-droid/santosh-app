/* v0.142 Hoola Console: the web app on the same APIs as the phone.
   Login (Google one-time code | Hoola ID + console password | server key) -> session token (Bearer).
   Chat: /api/conversations (+ /messages, /files, /stop), live events = SSE read with fetch (Bearer header, reconnect
   with Last-Event-ID). Cards act on the real endpoints; money cards need her phone's fingerprint (HTTP 428).
   Baat: /api/voice/ws (16 kHz PCM16 up, 24 kHz PCM16 down), token in the WebSocket subprotocol, never in the URL. */
'use strict';
(() => {
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const svg = p => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
const IC = {
  chat:'<path d="M4 5h16v11H8l-4 4z"/>', aaj:'<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
  kaam:'<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>', baat:'<path d="M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3"/>',
  main:'<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0"/>'};
const narrow = () => matchMedia('(max-width: 1100px)').matches;
const store = {get: k => { try { return localStorage.getItem(k); } catch { return null; } },
               set: (k, v) => { try { localStorage.setItem(k, v); } catch {} }, del: k => { try { localStorage.removeItem(k); } catch {} }};
const timeOf = iso => { try { return new Date(iso).toLocaleString('en-IN', {day:'numeric', month:'short', hour:'2-digit', minute:'2-digit'}); } catch { return ''; } };

/* ================= API ================= */
let TOKEN = store.get('hoola.console.token') || '';
class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
async function api(method, path, body, {raw = false, form = null, signal} = {}) {
  const headers = {};
  if (TOKEN) headers.Authorization = 'Bearer ' + TOKEN;
  let payload;
  if (form) payload = form; else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const r = await fetch(path, {method, headers, body: payload, signal, credentials: 'omit', cache: 'no-store'});
  if (raw) { if (!r.ok) throw new ApiError(r.status, await r.text()); return r; }
  let data = null; try { data = await r.json(); } catch {}
  if (!r.ok) {
    const msg = (data && (data.detail?.message || (typeof data.detail === 'string' ? data.detail : '') || data.message)) || `Server ne mana kiya (${r.status})`;
    if (r.status === 401 && path !== '/api/console/login' && path !== '/api/console/exchange') logout(true);
    throw new ApiError(r.status, msg);
  }
  return data;
}
function toast(msg, bad) { const t = $('#toast'); t.textContent = msg; t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false; clearTimeout(toast._t); toast._t = setTimeout(() => t.hidden = true, 4200); }

/* ================= login ================= */
let CONFIG = {google: false};
function showLogin(err) {
  $('#app').hidden = true; $('#login').hidden = false; if (err) { $('#lerr').textContent = err; $('#lerr').hidden = false; }
  $('#gbtn').disabled = false;
}
async function boot() {
  try { CONFIG = await api('GET', '/api/console/config'); } catch {}
  const u = new URL(location.href), code = u.searchParams.get('code'), err = u.searchParams.get('error'), gApps = u.searchParams.get('google') === 'apps';
  if (code || err) history.replaceState(null, '', '/console/');
  if (code) {
    try { const r = await api('POST', '/api/console/exchange', {code}); setToken(r.session_token); }
    catch (e) { return showLogin(e.message); }
  }
  if (err) return showLogin(err);
  if (!TOKEN) return showLogin();
  try { await enter(); if (gApps) toast('Google apps jud gaye: Gmail, Calendar, Drive, Docs, Sheets.'); } catch (e) { if (e.status !== 401) showLogin(e.message); }
}
function setToken(t) { TOKEN = t || ''; if (TOKEN) store.set('hoola.console.token', TOKEN); else store.del('hoola.console.token'); }
$('#gbtn').addEventListener('click', () => {
  if (!CONFIG.google) { $('#lerr').textContent = 'Google sign-in is server par abhi set nahi hai. Hoola ID + password se login kijiye.'; $('#lerr').hidden = false; return; }
  $('#gbtn').innerHTML = '<span class="spin"></span> Google khul raha hai…'; location.href = '/auth/google/start?web=1';
});
$('#lform').addEventListener('submit', async e => {
  e.preventDefault(); $('#lerr').hidden = true; const btn = $('#lbtn'); btn.disabled = true; btn.textContent = 'Login ho raha hai…';
  try { const r = await api('POST', '/api/console/login', {handle: $('#hid').value.trim(), password: $('#hpw').value}); setToken(r.session_token); $('#hpw').value = ''; await enter(); }
  catch (er) { $('#lerr').textContent = er.message; $('#lerr').hidden = false; }
  finally { btn.disabled = false; btn.textContent = 'Login'; }
});
$('#kbtn').addEventListener('click', async () => {
  const k = $('#okey').value.trim(); if (!k) return; setToken(k); $('#okey').value = '';
  try { await enter(); } catch (er) { setToken(''); $('#lerr').textContent = er.status === 401 ? 'Key galat hai.' : er.message; $('#lerr').hidden = false; }
});
async function logout(expired) {
  stopStream(); endCall();
  if (TOKEN && !expired) { try { await api('POST', '/api/logout'); } catch {} }
  setToken(''); showLogin(expired ? 'Session khatam ho gaya. Dobara login kijiye.' : '');
}

/* ================= state + shell ================= */
let ME = null, CONV = null, VIEW = 'chat', AV = 'Santosh';
const NAV = [['chat','Chat'],['aaj','Aaj'],['kaam','Saare kaam'],['baat','Baat'],['main','Main']];
function drawNav() {
  $('#snav').innerHTML = NAV.map(([k, n]) => `<button class="sn" data-v="${k}" aria-current="${k === VIEW}">${svg(IC[k])}<span class="txt">${n}</span>${k === 'aaj' && QUEUE.length ? `<span class="ct txt">${QUEUE.length}</span>` : ''}</button>`).join('');
  const T = [['chat','Chat'],['aaj','Aaj'],['baat',''],['kaam','Kaam'],['main','Main']];
  $('#tabbar').innerHTML = T.map(([k, n]) => k === 'baat' ? `<div class="mid"><button class="baat" data-v="baat" aria-label="Baat, live voice">${svg(IC.baat).replace('currentColor', '#1B1030')}</button></div>`
    : `<button class="sn" data-v="${k}" aria-current="${k === VIEW}">${svg(IC[k])}<span>${n}</span></button>`).join('');
}
function go(v) {
  VIEW = v; $$('.view').forEach(x => x.hidden = x.id !== 'v-' + v);
  $('#ttl').textContent = {chat:'', aaj:'· Aaj', kaam:'· Saare kaam', baat:'· Baat', main:'· Main'}[v] || '';
  drawNav(); $('#app').classList.remove('drawer');
  if (v === 'aaj') drawAaj(); if (v === 'main') drawMain(); if (v === 'baat') drawBaat();
}
document.addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (b) go(b.dataset.v); });
$('#menu').addEventListener('click', () => $('#app').classList.add('drawer'));
$('#scrim').addEventListener('click', () => $('#app').classList.remove('drawer'));
$('#collapse').addEventListener('click', () => $('#app').classList.toggle('collapsed'));
$('#liveBtn').addEventListener('click', () => $('#app').classList.toggle('open'));
$('#liveClose').addEventListener('click', () => $('#app').classList.remove('open'));
$('#model').addEventListener('click', () => go('main'));

async function enter() {
  ME = await api('GET', '/api/console/me');
  AV = ME.avatar?.name || 'Santosh';
  $$('.aname').forEach(e => e.textContent = AV);
  const img = ME.avatar?.gender === 'f' ? '/static/santosh-happy.png' : '/static/santosh-head.png';
  $$('.aimg').forEach(e => e.src = img); $('#uimg').src = img;
  $('#uname').textContent = ME.owner || ME.email || 'Aap'; $('#uhandle').textContent = `${AV} · ${ME.handle || ''}`;
  const h = new Date().getHours(), first = (ME.owner && ME.owner !== 'Hoola user') ? ME.owner.split(' ')[0] : '';
  $('#greet').textContent = `${h < 12 ? 'Good morning' : h < 17 ? 'Namaste' : 'Good evening'}${first ? ', ' + first : ''}`;
  $('#login').hidden = true; $('#app').hidden = false; drawNav(); drawKaam(); go('chat');
  const list = await loadRecents();
  const target = list[0]?.id || (await api('POST', '/api/conversations')).id;
  await openConv(target);
  refreshPending(); setInterval(refreshPending, 30000);
}

/* ================= recents ================= */
async function loadRecents() {
  let list = [];
  try { list = (await api('GET', '/api/console/conversations')).conversations || []; } catch {}
  $('#recents').innerHTML = list.map(c => `<button class="rc" data-conv="${esc(c.id)}" title="${esc(timeOf(c.updated_at))}"${c.id === CONV ? ' aria-current="true"' : ''}>${esc(c.title)}</button>`).join('') || '<div class="empty" style="padding:8px 12px">Abhi koi chat nahi.</div>';
  return list;
}
$('#recents').addEventListener('click', e => { const b = e.target.closest('[data-conv]'); if (b) { openConv(b.dataset.conv); go('chat'); } });
$('#newChat').addEventListener('click', async () => {
  try { const c = await api('POST', '/api/conversations'); await openConv(c.id, true); go('chat'); loadRecents(); } catch (e) { toast(e.message, true); }
});

/* ================= chat view ================= */
const composer = $('#composer'), msg = $('#msg'), col = $('#col');
$('#slotLand').appendChild(composer);
const scrollDown = (force) => { const t = $('#thread'); if (force || t.scrollHeight - t.scrollTop - t.clientHeight < 260) t.scrollTop = t.scrollHeight; };
function landing(on) {
  $('#landing').hidden = !on; $('#thread').hidden = on; $('#dock').hidden = on;
  (on ? $('#slotLand') : $('#slotDock')).appendChild(composer);
}
let TURN = null;          // the open Hoola turn: {bd, tools, tl, text, steps:{}}
let USER_ECHO = [];       // texts she sent from here (their echo from the server is not drawn twice)

function userBubble(text, files) {
  const d = document.createElement('div'); d.className = 'mu';
  d.innerHTML = (files?.length ? `<div class="att">${files.map(f => `<span class="chip">📎 ${esc(f.name || f)}</span>`).join('')}</div>` : '') + esc(text);
  col.appendChild(d); scrollDown(true); TURN = null; return d;
}
function hoolaBlock() {
  const d = document.createElement('div'); d.className = 'mh';
  d.innerHTML = `<span class="av"><img src="${$('#uimg').src}" alt=""></span><div class="bd"></div>`;
  col.appendChild(d); return d.querySelector('.bd');
}
function turn() { if (!TURN) TURN = {bd: hoolaBlock(), tools: null, tl: null, text: null, steps: {}, t0: Date.now()}; return TURN; }

/* small, safe markdown: paragraphs, **bold**, `code`, lists, links (http/https only) */
function md(text) {
  const lines = esc(text).split('\n'); let html = '', list = false;
  const inline = s => s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/\[(\d{1,2})\]/g, '<span class="tag v">[$1]</span>')
    .replace(/(https?:\/\/[^\s<]+[^\s<.,;:!?)])/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  for (const l of lines) {
    const m = l.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (m) { if (!list) { html += '<ul>'; list = true; } html += `<li>${inline(m[1])}</li>`; continue; }
    if (list) { html += '</ul>'; list = false; }
    if (l.trim()) html += `<p>${inline(l)}</p>`;
  }
  return html + (list ? '</ul>' : '');
}
function hoolaText(text, source) {
  const t = turn();
  if (t.text && (text.startsWith(t.text.dataset.raw) || t.text.dataset.raw === text)) { t.text.dataset.raw = text; t.text.innerHTML = md(text); scrollDown(); return; }
  const el = document.createElement('div'); el.className = 'txt textmd'; el.dataset.raw = text; el.innerHTML = md(text);
  if (source === 'worker' || source === 'greeting') el.classList.add('note-in');
  t.bd.appendChild(el); t.text = el; scrollDown();
}

/* steps (tool calls) inside the turn + the live panel */
function stepEvent(p) {
  const t = turn();
  if (!t.tools) {
    t.tools = document.createElement('details'); t.tools.className = 'tools'; t.tools.open = true;
    t.tools.innerHTML = `<summary><span class="spin"></span><span class="sm">${esc(AV)} kaam kar raha hai…</span><span class="chev">⌄</span></summary><div class="tl"></div>`;
    t.bd.insertBefore(t.tools, t.text || null); t.tl = t.tools.querySelector('.tl'); t.n = 0;
    $('#lsteps').innerHTML = '';
  }
  const id = String(p.id || p.tool || Math.random());
  const row = p.state === 'running' ? `<span class="spin" style="width:16px;height:16px"></span>${esc(p.label || p.tool)} <code>${esc(p.tool || '')}</code>`
    : p.state === 'error' ? `<span class="ic" style="background:rgba(248,113,113,.18);color:var(--bad)">!</span>${esc(p.label || p.tool)} <code>${esc(p.tool || '')}</code>${p.detail ? `<span class="tm">${esc(String(p.detail).slice(0, 60))}</span>` : ''}`
    : `<span class="ic">✓</span>${esc(p.label || p.tool)} <code>${esc(p.tool || '')}</code>`;
  const cls = 'ts ' + (p.state === 'running' ? 'run' : p.state === 'error' ? 'err' : 'done');
  for (const box of [t.tl, $('#lsteps')]) {
    let el = box.querySelector(`[data-step="${CSS.escape(id)}"]`);
    if (!el) { el = document.createElement('div'); el.dataset.step = id; box.appendChild(el); if (box === t.tl) t.n++; }
    el.className = cls; el.innerHTML = row;
  }
  live(p.state === 'running' ? 'run' : 'idle'); scrollDown();
}
function closeTurnTools() {
  const t = TURN; if (!t || !t.tools) return;
  const secs = ((Date.now() - t.t0) / 1000).toFixed(1);
  t.tools.querySelector('summary').innerHTML = `<span class="ic" style="width:18px;height:18px;border-radius:50%;display:grid;place-items:center;background:rgba(52,211,153,.18);color:var(--ok);font-size:10px;font-weight:900">✓</span><span>${t.n} kadam · ${secs}s</span><span class="chev">⌄</span>`;
  t.tools.open = false;
}
let TYPING = null;
function typing(on) {
  $('#stopBtn').hidden = !on;
  if (on) { if (!TYPING) { const t = turn(); TYPING = document.createElement('div'); TYPING.className = 'typing'; TYPING.innerHTML = '<i></i><i></i><i></i>'; t.bd.appendChild(TYPING); scrollDown(); } live('run'); }
  else { TYPING?.remove(); TYPING = null; closeTurnTools(); live(QUEUE.length ? 'ask' : 'idle'); TURN = null; }
}

/* ================= live stage (Work Theatre events) ================= */
const SCENE = {
  work:() => `<div class="orb"></div>`,
  browser:() => `<div class="brw"><div class="url"><i></i><i></i><span class="u">website</span></div><div class="pg"><b class="h" style="font-size:12px">Hoola ka browser</b><div class="in f"></div><div class="in"></div><span class="sb">…</span></div></div>`,
  pc:() => `<div class="pcw"><div class="tb"><span>Aapka PC</span></div><div class="gridx">${Array.from({length: 20}, (_, i) => `<i class="${i % 6 === 2 ? 'hl' : ''}"></i>`).join('')}</div></div>`,
  email:() => `<div class="mails"><div>✉️ Inbox</div><div>✉️ Drafts</div><div>✉️ Sent</div></div>`,
  payment:() => `<div class="calc"><div><span>Kul</span><span>₹ …</span></div><div><span>Payee</span><span>pinned</span></div><div><span>Aapki Haan</span><span>zaroori</span></div></div>`,
  network:() => `<div class="netsc"><span class="lk"></span><span class="av a" style="left:6%"><img src="${$('#uimg').src}" alt=""></span><span class="env"></span><span class="av a" style="right:6%"><img src="/static/santosh-happy.png" alt=""></span></div>`,
  bluetooth:() => `<div class="home"><i>❄️</i><i class="on">📺</i><i>🔊</i><i>💡</i><i class="on">🎛</i><i>🚪</i></div>`,
  website:() => `<div class="site"><div class="h"></div><div class="b">${'<i style="min-height:30px"></i>'.repeat(5)}</div></div>`};
let STAGE_KIND = '';
function workEvent(p) {
  const kind = SCENE[p.scene] ? p.scene : 'work';
  if (kind !== STAGE_KIND) { const st = $('#stage'); st.querySelector('.sc')?.remove(); st.insertAdjacentHTML('afterbegin', `<div class="sc">${SCENE[kind]()}</div>`); STAGE_KIND = kind; }
  $('#stageCap').textContent = p.label || p.tool || 'Kaam';
  $('#stageWhere').textContent = {browser:'Hoola ka browser · server', pc:'Aapka PC', email:'Email', payment:'Paisa · aapki Haan', network:'Hoola Network', bluetooth:'Ghar', website:'Website'}[kind] || 'Hoola server';
  const u = $('#stage .u'); if (u && p.data && (p.data.site || p.data.url)) u.textContent = String(p.data.site || p.data.url).slice(0, 60);
  if (p.phase === 'error' || p.phase === 'stopped') $('#stageCap').textContent = (p.phase === 'stopped' ? 'Roka gaya: ' : 'Dikkat: ') + (p.error || p.label || '');
  if (!narrow() && p.phase === 'start') $('#app').classList.add('open');
}
function live(state) {
  const b = $('#liveBtn'); b.classList.toggle('on', state !== 'idle');
  $('#liveTxt').textContent = state === 'run' ? 'Kaam chal raha' : state === 'ask' ? 'Aapki Haan' : 'Live';
  $('#liveTag').textContent = state === 'run' ? 'chal raha' : state === 'ask' ? 'Haan chahiye' : 'khaali';
  $('#liveTag').className = 'tag ' + (state === 'ask' ? 'warn' : 'ok');
}

/* ================= cards ================= */
const LABEL = {bazar_approval:'Aapki Haan chahiye', employee_ask:'Employee ka sawaal', operator_ask:'Website job ko aapki zaroorat', operator_task:'Website job',
  email_draft:'Email draft', hoola_deal:'Hoola Deal', hoola_knock:'Hoola Network', hoola_msg:'Hoola Network message', calendar_event:'Calendar',
  reminders:'Reminders', lists:'Lists', gyaan_sources:'Sources', call_receipt:'Call receipt', procedure:'Seekha', memory_saved:'Yaad rakha',
  artifact:'Page', pc_file:'File', photo_made:'Picture', motion:'Reel', video_job:'Video', studio_approval:'AI video ka kharcha', gst_return:'GST return',
  payroll_run:'Salary run', google_reconnect:'Google dobara jodiye', campaign:'WhatsApp campaign'};
const CARDS = new Map();      // kind:id -> element (updated in place)
const SKIP_FIELDS = /(^id$|_id$|^tenant|token|secret|^sig|hash|nonce|^at$|_at$|preview|thumb|^b64|^data$|^raw)/i;
function kvRows(p, max = 8, used = []) {
  const rows = [];
  for (const [k, v] of Object.entries(p || {})) {
    if (rows.length >= max || SKIP_FIELDS.test(k) || used.includes(k) || k === 'status') continue;
    if (v === null || v === '' || typeof v === 'object') continue;
    const s = String(v); if (s.length > 160) continue;
    rows.push(`<span>${esc(k.replace(/_/g, ' '))}</span><b>${esc(s)}</b>`);
  }
  return rows.length ? `<div class="kv">${rows.join('')}</div>` : '';
}
function safeLink(u) { if (typeof u !== 'string') return ''; if (u.startsWith('/api/') || u.startsWith('/static/')) return u; try { const x = new URL(u); return x.protocol === 'https:' ? x.href : ''; } catch { return ''; } }
function cardShell(kind, p) {
  const key = kind + ':' + (p.id || p.task_id || p.approval_id || p.order_id || Math.random());
  let el = CARDS.get(key);
  if (!el || !el.isConnected) { el = document.createElement('div'); el.className = 'cd'; CARDS.set(key, el); el.dataset.key = key; turn().bd.appendChild(el); }
  return el;
}
function head(title, tag, cls) { return `<div class="hd"><b>${esc(title)}</b>${tag ? `<span class="tag ${cls || 'v'}">${esc(tag)}</span>` : ''}</div>`; }
function decided(el, ok, text) { el.querySelectorAll('.slidec,.acts.dec').forEach(x => x.remove()); el.classList.remove('ask'); el.insertAdjacentHTML('beforeend', `<div class="${ok ? 'okn' : 'badc'}" style="font-weight:800">${esc(text)}</div>`); refreshPending(); }

function slider(label, onDone) {
  const w = document.createElement('div'); w.className = 'slidec'; w.tabIndex = 0; w.setAttribute('role', 'button'); w.setAttribute('aria-label', label + ' (Enter)');
  w.innerHTML = `<span class="fill"></span><span>${esc(label)} →</span><div class="knob">›</div>`;
  const k = w.querySelector('.knob'), f = w.querySelector('.fill'); let x0 = null, max = 0, busy = false;
  const reset = () => { k.style.left = '4px'; f.style.width = '0'; busy = false; };
  const finish = async () => { if (busy) return; busy = true; k.style.left = (w.clientWidth - 48) + 'px'; f.style.width = '100%'; try { await onDone(); } catch (e) { reset(); throw e; } };
  k.addEventListener('pointerdown', e => { if (busy) return; x0 = e.clientX; max = w.clientWidth - 48; k.style.transition = f.style.transition = 'none'; k.setPointerCapture(e.pointerId); });
  k.addEventListener('pointermove', e => { if (x0 === null) return; const d = Math.max(4, Math.min(max, 4 + e.clientX - x0)); k.style.left = d + 'px'; f.style.width = (d + 44) + 'px'; });
  k.addEventListener('pointerup', () => { if (x0 === null) return; k.style.transition = f.style.transition = ''; const d = parseFloat(k.style.left || 4); x0 = null; if (d > max * .8) finish().catch(() => {}); else reset(); });
  w.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); finish().catch(() => {}); } });
  return w;
}
function decisionRow(el, {yes, no, yesLabel = 'Slide karke Haan karein', noLabel = 'Mana karein'}) {
  const s = slider(yesLabel, async () => { try { await yes(); } catch (e) { toast(e.message, true); throw e; } });
  const a = document.createElement('div'); a.className = 'acts dec';
  a.innerHTML = `<button class="btn soft" type="button">${esc(noLabel)}</button>`;
  a.firstChild.addEventListener('click', async () => { try { await no(); } catch (e) { toast(e.message, true); } });
  el.classList.add('ask'); el.append(s, a);
}
const fingerprintMsg = 'Yeh paise wala card hai: Haan sirf aapke phone ke fingerprint se hogi. Hoola app mein yahi card khol kar Haan kijiye.';

function renderCard(kind, p, at) {
  if (kind === 'gyaan_sources') {
    const el = document.createElement('div'); el.className = 'srcs';
    el.innerHTML = (p.sources || []).map(s => `<span class="chip">[${esc(s.n ?? '')}] ${esc(s.title || s.source || '')}</span>`).join(''); turn().bd.appendChild(el); return;
  }
  if (kind === 'memory_saved' || kind === 'procedure') {
    const el = document.createElement('div'); el.className = 'note'; el.textContent = (kind === 'memory_saved' ? '📌 Yaad rakha: ' : '🎓 Seekha: ') + (p.text || p.title || ''); turn().bd.appendChild(el); return;
  }
  const el = cardShell(kind, p);
  switch (kind) {
    case 'bazar_approval': {
      el.innerHTML = head(p.title || 'Aapki Haan chahiye', p.money ? 'paisa' : 'Aapki Haan', p.money ? 'bad' : 'warn')
        + (p.amount ? `<div class="big">${esc(p.amount)}</div>` : '') + (p.payee ? `<div class="faint" style="font-size:13px">${esc(p.payee)}</div>` : '')
        + (p.items || []).map(i => `<div class="ln"><span>${esc(i.name)}</span><b>${esc(i.price)}</b></div>`).join('')
        + (p.disclosures || []).map(i => `<div class="ln"><span>${esc(i.label)}</span><b>${esc(i.value)}</b></div>`).join('');
      if (p.status && p.status !== 'pending') { decided(el, p.status === 'approved', p.status === 'approved' ? '✓ Haan diya' : '✕ ' + p.status); break; }
      decisionRow(el, {
        yes: async () => { try { await api('POST', `/api/bazar/approvals/${encodeURIComponent(p.id)}`, {decision: 'approve'}); decided(el, true, '✓ Haan diya'); }
                           catch (e) { if (e.status === 428) { decided(el, false, '📱 ' + fingerprintMsg); return; } throw e; } },
        no: async () => { await api('POST', `/api/bazar/approvals/${encodeURIComponent(p.id)}`, {decision: 'reject'}); decided(el, false, '✕ Mana kiya'); }});
      break; }
    case 'employee_ask': {
      el.innerHTML = head(p.what || 'Employee ka sawaal', p.duty_label || 'Employee', 'warn') + `<div class="kv">${[['Kisne', p.who], ['Kyon', p.why], ['Kya', p.detail]].filter(([, v]) => v).map(([k, v]) => `<span>${k}</span><b>${esc(v)}</b>`).join('')}</div>`;
      const empDone = st => st === 'done' ? '✓ Ho gaya' : st === 'declined' ? '✕ Mana kiya' : st === 'expired' ? 'Samay nikal gaya' : '✕ Nahi ho paya' + (p.result ? ': ' + String(p.result).slice(0, 140) : '');
      if (p.status && p.status !== 'pending') { decided(el, p.status === 'done', empDone(p.status)); break; }
      decisionRow(el, {
        yes: async () => { const r = await api('POST', `/api/employee/asks/${encodeURIComponent(p.id)}`, {approve: true}); p.result = r.result; decided(el, r.status === 'done', empDone(r.status)); },
        no: async () => { await api('POST', `/api/employee/asks/${encodeURIComponent(p.id)}`, {approve: false}); decided(el, false, '✕ Mana kiya'); }});
      break; }
    case 'operator_ask': {
      const k = p.kind || 'approve', typed = ['otp', 'secret', 'captcha', 'question'].includes(k);
      el.innerHTML = head(p.reason || 'Website ko aapki zaroorat hai', p.site || 'Hoola ka browser', 'warn')
        + (k === 'payment' ? `<p class="muted" style="font-size:13.5px">Paisa wala step: Hoola isse nahi dabata. Phone app mein live view kholkar khud dabaiye.</p>` : '')
        + (k === 'captcha' ? `<img class="cap" alt="CAPTCHA" hidden>` + (p.suggested_answer ? `<div class="faint" style="font-size:13px">Hoola ne padha: <b>${esc(p.suggested_answer)}</b></div>` : '') : '')
        + (typed ? `<input class="fld" type="${k === 'question' ? 'text' : 'password'}" inputmode="${k === 'otp' ? 'numeric' : 'text'}" autocomplete="one-time-code" placeholder="${k === 'otp' ? 'OTP' : k === 'captcha' ? 'CAPTCHA' : 'Jawab'}" aria-label="Answer">
            <p class="faint" style="font-size:12.5px">Yeh sirf page ke box mein jayega. Chat, yaad ya AI ko nahi dikhega.</p>` : '');
      if (p.status && p.status !== 'pending') { decided(el, true, '✓ Jawab diya'); break; }
      if (k === 'captcha') api('GET', `/api/operator/requests/${encodeURIComponent(p.id)}/captcha`, undefined, {raw: true}).then(r => r.blob()).then(b => { const i = el.querySelector('img.cap'); if (i) { i.src = URL.createObjectURL(b); i.hidden = false; } }).catch(() => {});
      if (k === 'payment') break;
      decisionRow(el, {yesLabel: typed ? 'Page mein bharo' : 'Slide karke Haan karein',
        yes: async () => { const inp = el.querySelector('input.fld'); const answer = inp ? inp.value.trim() || (k === 'captcha' ? p.suggested_answer || '' : '') : '';
          if (typed && !answer) { toast('Pehle jawab likhiye.', true); throw new Error('empty'); }
          await api('POST', `/api/operator/requests/${encodeURIComponent(p.id)}`, {status: 'approved', answer}); if (inp) inp.value = ''; decided(el, true, typed ? '✓ Box mein bhar diya (••••)' : '✓ Haan diya'); },
        no: async () => { await api('POST', `/api/operator/requests/${encodeURIComponent(p.id)}`, {status: 'rejected', answer: ''}); decided(el, false, '✕ Mana kiya'); }});
      break; }
    case 'email_draft': {
      el.innerHTML = head(p.subject || 'Email draft', p.status === 'pending' ? 'Bhejo ka intezaar' : p.status, p.status === 'sent' ? 'ok' : 'warn')
        + `<div class="kv"><span>To</span><b>${esc(p.to)}</b>${p.cc ? `<span>Cc</span><b>${esc(p.cc)}</b>` : ''}${p.send_at_label ? `<span>Kab</span><b>${esc(p.send_at_label)}</b>` : ''}</div>`
        + `<textarea aria-label="Email body">${esc(p.body)}</textarea>` + ((p.attachments || []).length ? `<div class="srcs">${p.attachments.map(a => `<span class="chip">📎 ${esc(a.name)}</span>`).join('')}</div>` : '');
      if (!['pending', 'failed'].includes(p.status)) { el.querySelector('textarea').disabled = true; break; }
      const a = document.createElement('div'); a.className = 'acts dec';
      a.innerHTML = '<button class="btn go" type="button" style="padding:9px 18px;font-size:13px">Bhejo</button><button class="btn soft" type="button">Cancel</button>';
      a.children[0].addEventListener('click', async () => { try { const body = el.querySelector('textarea').value; await api('POST', `/api/emails/${encodeURIComponent(p.id)}/send`, body !== p.body ? {body} : {}); decided(el, true, '✓ Bhej diya'); } catch (e) { toast(e.message, true); } });
      a.children[1].addEventListener('click', async () => { try { await api('POST', `/api/emails/${encodeURIComponent(p.id)}/cancel`); decided(el, false, '✕ Cancel'); } catch (e) { toast(e.message, true); } });
      el.classList.add('ask'); el.appendChild(a); break; }
    default: {
      const tk = ['title', 'name', 'label', 'what', 'subject'].find(k => p[k]), sk = ['say', 'summary', 'text', 'reason', 'message'].find(k => p[k]);
      const title = (tk && p[tk]) || LABEL[kind] || kind.replace(/_/g, ' ');
      const sub = (sk && p[sk]) || '';
      const link = safeLink(p.url || p.link || p.open_url || '');
      const money = /approval|_pay|deal|studio|payroll|spend|bill/.test(kind) && (p.status === 'pending' || p.waiting);
      el.innerHTML = head(title, LABEL[kind] && LABEL[kind] !== title ? LABEL[kind] : (p.status || ''), money ? 'warn' : 'v')
        + (sub ? `<p style="font-size:14px">${esc(String(sub).slice(0, 600))}</p>` : '') + kvRows(p, 8, [tk, sk])
        + (link ? `<div class="acts"><a class="btn soft" href="${esc(link)}" target="_blank" rel="noopener noreferrer">Kholo</a></div>` : '')
        + (money ? `<p class="faint" style="font-size:12.5px">Is card par Haan Hoola app se hoti hai (fingerprint ya app ka apna screen).</p>` : '');
    }
  }
  scrollDown();
}

/* ================= events (SSE over fetch) ================= */
let STREAM = null, LAST = 0, RETRY = 0;
function setConn(state, text) { const c = $('#conn'); c.className = 'conn ' + state; c.querySelector('span').textContent = text; }
function stopStream() { if (STREAM) { STREAM.abort(); STREAM = null; } }
async function stream(conv) {
  stopStream(); const ctl = new AbortController(); STREAM = ctl;
  while (STREAM === ctl) {
    try {
      setConn('', 'Jud raha hai…');
      const r = await fetch(`/api/conversations/${encodeURIComponent(conv)}/events?after=${LAST}`, {headers: {Authorization: 'Bearer ' + TOKEN, 'Last-Event-ID': String(LAST)}, signal: ctl.signal, cache: 'no-store'});
      if (r.status === 401) return logout(true);
      if (!r.ok || !r.body) throw new Error('stream ' + r.status);
      setConn('ok', 'Live'); RETRY = 0;
      const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
      for (;;) {
        const {value, done} = await rd.read(); if (done) break;
        buf += dec.decode(value, {stream: true});
        let i; while ((i = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
          const data = chunk.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trimStart()).join('\n');
          if (!data) continue;
          try { const ev = JSON.parse(data); if (ev.id > LAST) { LAST = ev.id; onEvent(ev); } } catch (e) { console.warn('event', e); }
        }
      }
    } catch (e) { if (ctl.signal.aborted) return; }
    if (STREAM !== ctl) return;
    setConn('bad', 'Dobara jud raha hai…'); RETRY = Math.min(RETRY + 1, 6); await new Promise(r => setTimeout(r, 800 * 2 ** RETRY));
  }
}
function onEvent(ev) {
  const p = ev.payload || {};
  switch (ev.kind) {
    case 'message':
      if (p.role === 'user') { const i = USER_ECHO.indexOf(p.text); if (i > -1) { USER_ECHO.splice(i, 1); return; } landing(false); userBubble(p.text, p.files); return; }
      if (p.source === 'greeting' && !col.children.length) return;        // the landing greets instead
      landing(false); hoolaText(p.text || '', p.source); return;
    case 'typing': typing(!!p.on); return;
    case 'step': landing(false); stepEvent(p); return;
    case 'work': workEvent(p); return;
    default: landing(false); renderCard(ev.kind, p, ev.at);
      if (/ask|approval|draft|_sign|quote|confirm|knock/.test(ev.kind)) refreshPending();
  }
}

/* ================= open a conversation ================= */
async function openConv(id, fresh) {
  stopStream(); CONV = id; col.innerHTML = ''; CARDS.clear(); TURN = null; TYPING = null; USER_ECHO = []; $('#stopBtn').hidden = true;
  $$('#recents .rc').forEach(b => b.toggleAttribute('aria-current', b.dataset.conv === id));
  let msgs = [], recent = {last_event_id: 0, cards: []};
  if (!fresh) {
    try { [msgs, recent] = await Promise.all([api('GET', `/api/conversations/${encodeURIComponent(id)}/messages?limit=120`).then(r => r.messages || []),
                                            api('GET', `/api/console/conversations/${encodeURIComponent(id)}/recent?n=30`)]); }
    catch (e) { toast(e.message, true); }
  } else { try { recent = await api('GET', `/api/console/conversations/${encodeURIComponent(id)}/recent?n=1`); } catch {} }
  const any = msgs.some(m => m.role === 'user');
  landing(!any);
  // history: messages and the last cards merged by time
  const items = [...msgs.map(m => ({t: m.at, m})), ...recent.cards.map(c => ({t: c.at, c}))].sort((a, b) => String(a.t).localeCompare(String(b.t)));
  for (const it of items) {
    if (it.m) { if (it.m.role === 'user') userBubble(it.m.text); else if (any) hoolaText(it.m.text); }
    else renderCard(it.c.kind, it.c.payload, it.c.at);
  }
  TURN = null; LAST = recent.last_event_id || 0; scrollDown(true);
  stream(id);
}

/* ================= sending ================= */
let FILES = [];   // {file_id, name}
msg.addEventListener('input', () => { msg.style.height = 'auto'; msg.style.height = Math.min(200, msg.scrollHeight) + 'px'; $('#sendBtn').disabled = !msg.value.trim() && !FILES.length; });
msg.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); composer.requestSubmit(); } });
composer.addEventListener('submit', async e => {
  e.preventDefault(); const text = msg.value.trim(); if ((!text && !FILES.length) || !CONV) return;
  if (FILES.some(f => !f.file_id)) return toast('File abhi upload ho rahi hai…');
  const files = FILES.splice(0); drawFiles(); msg.value = ''; msg.style.height = 'auto'; $('#sendBtn').disabled = true;
  const body = {text: text || 'Ye file dekho', client_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())), files: files.map(f => f.file_id)};
  landing(false); userBubble(body.text, files); USER_ECHO.push(body.text);
  for (let i = 0; i < 3; i++) {
    try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/messages`, body); loadRecents(); return; }
    catch (er) { if (i === 2 || er.status === 401 || er.status === 400) { toast('Bheja nahi gaya: ' + er.message, true); msg.value = text; return; } await new Promise(r => setTimeout(r, 800 * (i + 1))); }
  }
});
$('#stopBtn').addEventListener('click', async () => { try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/stop`); toast('Rokne ko kaha. Jo kadam chal raha tha woh beech mein ruk sakta hai.'); } catch (e) { toast(e.message, true); } });
$('#attach').addEventListener('click', () => $('#fileIn').click());
$('#fileIn').addEventListener('change', async e => {
  const picked = [...e.target.files].slice(0, 6 - FILES.length); e.target.value = '';
  for (const f of picked) {
    if (f.size > 25 * 1024 * 1024) { toast(`${f.name}: 25 MB se badi file nahi chalegi.`, true); continue; }
    const item = {name: f.name, file_id: null}; FILES.push(item); drawFiles();
    try { const fd = new FormData(); fd.append('file', f, f.name); const r = await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/files`, undefined, {form: fd}); item.file_id = r.file_id; }
    catch (er) { FILES.splice(FILES.indexOf(item), 1); toast(`${f.name}: ${er.message}`, true); }
    drawFiles();
  }
});
function drawFiles() {
  $('#files').innerHTML = FILES.map((f, i) => `<span class="fchip${f.file_id ? '' : ' up'}">📎 ${esc(f.name)}${f.file_id ? '' : ' · upload…'}<button type="button" data-rm="${i}" aria-label="Remove ${esc(f.name)}">✕</button></span>`).join('');
  $('#sendBtn').disabled = !msg.value.trim() && !FILES.length;
}
$('#files').addEventListener('click', e => { const b = e.target.closest('[data-rm]'); if (b) { FILES.splice(+b.dataset.rm, 1); drawFiles(); } });
$('#micBtn').addEventListener('click', () => go('baat'));
$('#toolsBtn').addEventListener('click', () => go('kaam'));

/* ================= landing ideas + "Saare kaam" (real prompts) ================= */
const KAAM = window.KAAM || [], KI = window.KAAM_ICON || {};
let CAT = null;
$('#cats').innerHTML = KAAM.map(g => `<button class="cat" type="button" data-cat="${g[0]}" aria-pressed="false"><span>${g[1]}</span>${esc(g[2])}</button>`).join('');
$('#cats').addEventListener('click', e => { const b = e.target.closest('.cat'); if (!b) return; CAT = CAT === b.dataset.cat ? null : b.dataset.cat;
  $$('.cat').forEach(x => x.setAttribute('aria-pressed', x.dataset.cat === CAT));
  const g = KAAM.find(x => x[0] === CAT); $('#sugs').innerHTML = g ? g[4].map((t, i) => `<button class="sug" type="button" data-say="${esc(t[0])}" style="animation-delay:${i * 30}ms"><span>${KI[t[0]] || '↗'}</span>${esc(t[3])}<em>${esc(t[1])}</em></button>`).join('') : ''; });
function usePrompt(id) {
  const t = KAAM.flatMap(g => g[4]).find(x => x[0] === id); if (!t) return;
  go('chat'); msg.value = t[3].replace(/^\[[^\]]+\]\s*/, ''); msg.dispatchEvent(new Event('input'));
  if (t[4]) { toast(`Pehle file jodiye (${t[4]}), phir bhejiye.`); $('#fileIn').click(); } else composer.requestSubmit();
}
document.addEventListener('click', e => { const b = e.target.closest('[data-say]'); if (b) usePrompt(b.dataset.say); });
function drawKaam(q = '') {
  const qq = q.trim().toLowerCase(), total = KAAM.reduce((n, g) => n + g[4].length, 0);
  $('#kaam').innerHTML = `<div class="vh"><h2>${esc(AV)} kya kya karta hai</h2><span class="faint" style="font-weight:700">${total} kaam · tap karte hi asli ${esc(AV)} ko jaata hai</span></div>
    <label class="ksearch gl"><span aria-hidden="true">⌕</span><input id="kq" placeholder="Dhoondhiye: GST, reel, OTP, TV…" value="${esc(q)}" aria-label="Search"></label>
    <div class="kchips">${KAAM.map(g => `<a class="chip" href="#k-${g[0]}" style="text-decoration:none"><span>${g[1]}</span>${esc(g[2])}</a>`).join('')}</div>
    ${KAAM.map(g => { const items = g[4].filter(t => !qq || (t[1] + ' ' + t[2] + ' ' + t[3] + ' ' + g[2]).toLowerCase().includes(qq)); if (!items.length) return '';
      return `<div class="kgroup" id="k-${g[0]}"><h3><span>${g[1]}</span>${esc(g[2])}<small>${items.length}</small></h3><div class="kgrid">${items.map(t => `<button class="kt" type="button" data-say="${esc(t[0])}"><i style="background:${g[3]}22">${KI[t[0]] || g[1]}</i><b>${esc(t[1])}</b><span>${esc(t[2])}</span></button>`).join('')}</div></div>`; }).join('')}`;
  const kq = $('#kq'); kq.addEventListener('input', () => { const p = kq.selectionStart; drawKaam(kq.value); const n = $('#kq'); n.focus(); n.setSelectionRange(p, p); });
}

/* ================= pending queue (Haan list) ================= */
let QUEUE = [];
async function refreshPending() {
  try { QUEUE = (await api('GET', '/api/console/pending')).pending || []; } catch { return; }
  $('#qcount').textContent = QUEUE.length;
  $('#queue').innerHTML = QUEUE.length ? '' : '<div class="empty">Abhi kuch nahi.</div>';
  for (const q of QUEUE) {
    const holder = document.createElement('div'); $('#queue').appendChild(holder);
    const saveTurn = TURN; TURN = {bd: holder, steps: {}}; const k = q.kind + ':' + q.id; CARDS.delete(k);
    renderCard(q.kind, q.card || q); CARDS.delete(k); TURN = saveTurn;
  }
  if (!TYPING) live(QUEUE.length ? 'ask' : 'idle'); drawNav();
}

/* ================= Aaj ================= */
async function drawAaj() {
  const box = $('#aaj'); box.innerHTML = '<div class="vh"><h2>Aaj</h2></div><div class="empty">Laa raha hoon…</div>';
  let d = {reminders: [], lists: {}, pending: []}; try { d = await api('GET', '/api/console/today'); } catch (e) { box.innerHTML += `<p class="badc">${esc(e.message)}</p>`; return; }
  const date = new Date().toLocaleDateString('en-IN', {weekday: 'long', day: 'numeric', month: 'long'});
  box.innerHTML = `<div class="vh"><h2>Aaj · ${esc(date)}</h2></div>
    <div class="kpis"><div class="kpi gl"><b>${d.pending.length}</b><span>aapki Haan ka intezaar</span></div><div class="kpi gl"><b>${d.reminders.length}</b><span>aane wale reminders</span></div>
    <div class="kpi gl"><b>${Object.values(d.lists).reduce((n, l) => n + l.length, 0)}</b><span>list mein cheezein</span></div><div class="kpi gl"><b class="hid">${esc(ME?.handle || '')}</b><span>aapka Hoola ID</span></div></div>
    <div class="grid2">
      <div class="tile gl"><h3>Reminders</h3>${d.reminders.length ? `<div class="ag">${d.reminders.map(r => `<div><time>${esc(timeOf(r.due_at))}</time><span>${esc(r.text)}</span></div>`).join('')}</div>` : '<div class="empty">Koi reminder nahi.</div>'}</div>
      <div class="tile gl"><h3>Lists</h3>${Object.keys(d.lists).length ? Object.entries(d.lists).map(([n, items]) => `<b style="font-size:13px" class="acc">${esc(n)}</b><div class="lst">${items.map(i => `<label><input type="checkbox" disabled> ${esc(i.text)}</label>`).join('')}</div>`).join('') : '<div class="empty">Koi list nahi. Chat mein kahiye: "doodh shopping list mein daalo".</div>'}</div>
      <div class="tile gl"><h3>Aapki Haan chahiye <span class="tag warn">${d.pending.length}</span></h3>${d.pending.length ? d.pending.map(q => `<div class="ln"><span>${esc(q.title)}</span><b>${q.money ? '📱 phone' : 'console'}</b></div>`).join('') + '<button class="btn soft" type="button" id="toQueue">Cards kholo</button>' : '<div class="empty">Kuch nahi.</div>'}</div>
    </div>`;
  $('#toQueue')?.addEventListener('click', () => { $('#app').classList.add('open'); go('chat'); });
}

/* ================= Main (profile + console password) ================= */
const gOn = m => { const g = m.google_apps || {}; return !!(g.gmail && g.calendar && g.drive); };
async function drawMain() {
  const m = ME || {}; const box = $('#mainp');
  box.innerHTML = `<div class="prof gl"><span class="av"><img src="${$('#uimg').src}" alt=""></span><div><h2>${esc(AV)}</h2><div class="muted">${esc(m.handle || '')} · ${esc(m.owner || '')}${m.email ? ' · ' + esc(m.email) : ''}</div></div></div>
    <div class="grid2">
      <div class="tile gl"><h3>Console password <span class="tag ${m.has_password ? 'ok' : 'warn'}">${m.has_password ? 'set hai' : 'set nahi'}</span></h3>
        <p class="muted" style="font-size:13.5px">Isse aap kisi bhi computer par <b>${esc(m.handle || 'Hoola ID')}</b> + password se login kar sakti hain. Har login aapke chat mein bataya jaata hai.</p>
        <form class="pwbox" id="pwf" autocomplete="off">${m.has_password ? '<input type="password" id="pwc" placeholder="Abhi wala password" autocomplete="current-password" aria-label="Current password">' : ''}
          <input type="password" id="pwn" placeholder="Naya password (10+ akshar)" autocomplete="new-password" aria-label="New password" minlength="10">
          <input type="password" id="pwn2" placeholder="Naya password dobara" autocomplete="new-password" aria-label="Repeat new password">
          <button class="btn go" type="submit">${m.has_password ? 'Password badlo' : 'Password banao'}</button></form></div>
      <div class="tile gl"><h3>Google apps <span class="tag ${gOn(m) ? 'ok' : 'warn'}">${gOn(m) ? 'jude hain' : 'jode nahi'}</span></h3>
        <p class="muted" style="font-size:13.5px">Login sirf naam aur email leta hai. Gmail, Calendar, Drive, Docs aur Sheets par kaam ke liye Google se alag se ijazat dijiye.</p>
        <div class="feat">${['gmail', 'calendar', 'drive', 'docs', 'sheets'].map(k => `<span class="chip">${(m.google_apps || {})[k] ? '✓' : '○'} ${k[0].toUpperCase() + k.slice(1)}</span>`).join('')}</div>
        <div class="acts" style="margin-top:12px"><button class="btn ${gOn(m) ? 'soft' : 'go'}" type="button" id="gAppsBtn">${gOn(m) ? 'Dobara jodiye' : 'Google apps jodiye'}</button></div></div>
      <div class="tile gl"><h3>Yaad <span class="tag v" id="memc">…</span></h3><div class="mfacts" id="mfacts"><div class="empty">Laa raha hoon…</div></div></div>
      <div class="tile gl"><h3>Server</h3><div class="feat" id="feat"><span class="empty">…</span></div></div>
    </div>
    <div class="acts" style="margin-top:22px"><button class="btn soft" type="button" id="logoutBtn">Logout</button></div>`;
  $('#logoutBtn').addEventListener('click', () => logout(false));
  $('#gAppsBtn').addEventListener('click', () => { if (!CONFIG.google) return toast('Google sign-in server par set nahi hai.', true); location.href = '/auth/google/start?web=1&apps=1'; });
  $('#pwf').addEventListener('submit', async e => { e.preventDefault(); const n = $('#pwn').value, n2 = $('#pwn2').value;
    if (n !== n2) return toast('Dono naye password ek jaise nahi hain.', true);
    try { const r = await api('PUT', '/api/console/password', {password: n, current: $('#pwc')?.value || ''}); ME.has_password = true; toast(`Password set. Ab ${r.handle} + password se login ho sakta hai.`); drawMain(); } catch (er) { toast(er.message, true); } });
  api('GET', '/api/memory').then(r => { const f = r.facts || []; $('#memc').textContent = f.length; $('#mfacts').innerHTML = f.slice(0, 40).map(x => `<div>${x.pinned ? '📌 ' : ''}${esc(x.text)}</div>`).join('') || '<div class="empty">Abhi kuch yaad nahi.</div>'; }).catch(() => { $('#mfacts').innerHTML = '<div class="empty">—</div>'; });
  fetch('/healthz').then(r => r.json()).then(h => { $('#feat').innerHTML = `<span class="chip">v${esc(h.version)}</span>` + (h.features || []).slice(0, 60).map(f => `<span class="chip">${esc(f.replace(/_/g, ' '))}</span>`).join(''); }).catch(() => {});
}

/* ================= Baat: live voice in the browser ================= */
let CALL = null;
function drawBaat() {
  const v = $('#v-baat');
  if (v.dataset.drawn) return; v.dataset.drawn = '1';
  v.innerHTML = `<div class="call"><div class="callav"><span class="rg"></span><span class="rg"></span><span class="rg"></span><span class="av"><img src="${$('#uimg').src}" alt=""></span></div>
    <div><h2 style="font-size:26px">${esc(AV)}</h2><div class="callst okc" id="cst">Call shuru karne ke liye dabaiye</div><div class="faint" style="font-size:12.5px">Headphone lagayein to awaaz saaf rahegi · Hinglish</div></div>
    <div class="wave" id="cwave" aria-hidden="true" style="opacity:.3">${Array.from({length: 13}, (_, i) => `<i style="animation-delay:${(i * .09) % 1}s"></i>`).join('')}</div>
    <div class="caption" aria-live="polite" id="caption"></div>
    <div class="cbtns" id="cbtns"><button class="btn go callgo" type="button" id="callBtn">📞 Baat shuru karein</button></div></div>`;
  $('#callBtn').addEventListener('click', startCall);
}
function callUI(state, text) {
  const s = $('#cst'); if (s) s.textContent = text; const w = $('#cwave'); if (w) w.style.opacity = state === 'live' ? 1 : .3;
  const b = $('#cbtns'); if (!b) return;
  if (state === 'idle') { b.innerHTML = '<button class="btn go callgo" type="button" id="callBtn">📞 Baat shuru karein</button>'; $('#callBtn').addEventListener('click', startCall); }
  else if (!$('#hang')) { b.innerHTML = `<button class="cbx" type="button" id="muteBtn" aria-label="Mute">${svg(IC.baat)}</button><button class="cbx end" type="button" id="hang" aria-label="Hang up">${svg('<path d="M3 15c5-4 13-4 18 0l-2 3-4-1v-3c-2-.6-4-.6-6 0v3l-4 1z"/>')}</button>`;
    $('#hang').addEventListener('click', () => endCall(true)); $('#muteBtn').addEventListener('click', toggleMute); }
}
async function startCall() {
  if (CALL) return;
  let media;
  try { media = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1}}); }
  catch { return callUI('idle', 'Mic ki permission chahiye. Browser ke address bar se mic allow kijiye.'); }
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const q = new URLSearchParams({conv: CONV, voice: ME?.avatar?.voice || '', lang: 'hi-IN'});
  let ws; try { ws = new WebSocket(`${proto}//${location.host}/api/voice/ws?${q}`, ['hoola', 'hoola-key.' + TOKEN]); } catch { media.getTracks().forEach(t => t.stop()); ctx.close(); return callUI('idle', 'Call shuru nahi hui.'); }
  ws.binaryType = 'arraybuffer';
  CALL = {ws, ctx, media, muted: false, playAt: 0, sources: new Set(), ping: null};
  callUI('connecting', 'Jud raha hai…');
  const src = ctx.createMediaStreamSource(media), proc = ctx.createScriptProcessor(4096, 1, 1), ratio = ctx.sampleRate / 16000;
  proc.onaudioprocess = e => {
    if (!CALL || ws.readyState !== 1) return;
    const inp = e.inputBuffer.getChannelData(0), n = Math.floor(inp.length / ratio), out = new Int16Array(n);
    for (let i = 0; i < n; i++) { const s = CALL.muted ? 0 : inp[Math.floor(i * ratio)]; out[i] = Math.max(-1, Math.min(1, s)) * 0x7fff; }
    ws.send(out.buffer);
  };
  const sink = ctx.createGain(); sink.gain.value = 0; src.connect(proc); proc.connect(sink); sink.connect(ctx.destination);
  CALL.proc = proc; CALL.src = src;
  ws.onmessage = ev => {
    if (typeof ev.data !== 'string') return play(ev.data);
    let m; try { m = JSON.parse(ev.data); } catch { return; }
    if (m.type === 'ready') { callUI('live', 'Live · baat kijiye'); CALL.ping = setInterval(() => ws.readyState === 1 && ws.send('{"type":"ping"}'), 15000); }
    else if (m.type === 'user_text') caption('Aap', m.text);
    else if (m.type === 'santosh_text') caption(AV, m.text);
    else if (m.type === 'interrupted') cutSpeech();
    else if (m.type === 'tool') callUI('live', (m.state === 'done' ? '✓ ' : '… ') + (m.label || 'kaam'));
    else if (m.type === 'status') callUI('live', m.state === 'reconnecting' ? 'Dobara jud raha hai…' : 'Live');
    else if (m.type === 'hold') { if (m.on) cutSpeech(); callUI('live', m.on ? (AV + ' chup hai · "' + AV + '" bolkar bulaiye') : 'Live'); }
    else if (m.type === 'error') { toast(m.message || 'Call mein dikkat', true); callUI('live', m.message || 'Dikkat'); }
  };
  ws.onclose = e => { endCall(false); callUI('idle', e.code === 4401 ? 'Login dobara chahiye.' : 'Call khatam.'); };
}
function caption(who, text) { const c = $('#caption'); if (c) c.innerHTML = `<b>${esc(who)}</b>${esc(text)}`; }
function play(buf) {
  if (!CALL) return; const ctx = CALL.ctx, pcm = new Int16Array(buf), f = new Float32Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) f[i] = pcm[i] / 0x8000;
  const ab = ctx.createBuffer(1, f.length, 24000); ab.copyToChannel(f, 0);
  const s = ctx.createBufferSource(); s.buffer = ab; s.connect(ctx.destination);
  const at = Math.max(ctx.currentTime + 0.05, CALL.playAt); s.start(at); CALL.playAt = at + ab.duration;
  CALL.sources.add(s); s.onended = () => CALL && CALL.sources.delete(s);
}
function cutSpeech() { if (!CALL) return; CALL.sources.forEach(s => { try { s.stop(); } catch {} }); CALL.sources.clear(); CALL.playAt = 0; }
function toggleMute() { if (!CALL) return; CALL.muted = !CALL.muted; try { CALL.ws.send(JSON.stringify({type: CALL.muted ? 'mute' : 'unmute'})); } catch {} const b = $('#muteBtn'); if (b) b.style.background = CALL.muted ? 'var(--bad)' : ''; }
function endCall(send) {
  const c = CALL; if (!c) return; CALL = null;
  try { if (send && c.ws.readyState === 1) c.ws.send('{"type":"end"}'); } catch {}
  clearInterval(c.ping); try { c.proc.disconnect(); c.src.disconnect(); } catch {}
  c.media.getTracks().forEach(t => t.stop()); c.sources.forEach(s => { try { s.stop(); } catch {} });
  try { c.ws.close(); } catch {} try { c.ctx.close(); } catch {}
  callUI('idle', 'Call khatam. Receipt chat mein aayegi.');
}
addEventListener('beforeunload', () => endCall(true));

boot();
})();
