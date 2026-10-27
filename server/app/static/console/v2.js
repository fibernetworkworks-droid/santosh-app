/* v0.170 Hoola Console v2 (CONSOLE_V2): the Night-Glass shell on the same APIs as the phone.
   Same contract as the previous console (app.js), re-skinned and tightened for v2:
   login (Google one-time code | Hoola ID + console password | server key) -> session token (Bearer).
   Chat: /api/conversations (+ /messages, /files, /stop, /timeline, /edit, /retry, /branch, /feedback),
   one account stream for all chats (v0.162), streamed replies word by word (v0.161, HoolaStream.Pacer),
   cards act on the real endpoints; money cards need her phone's fingerprint (HTTP 428).
   Feature modules reused unchanged: kaam.js, build.js (HoolaBuild), md.js (HoolaMD), stream.js (HoolaStream),
   chatlist.js (HoolaChats), panel.js (HoolaPanel), projects.js (HoolaProjects), vendor/qrcode.js.
   The previous console stays available at /console/?legacy=1 (v2.css is the only styling here). */
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
  if (method === 'POST' && /\/conversations\/[^/]+\/(messages|edit)$/.test(path) && body && typeof body.text === 'string') {
    body = {...body, text: body.text + '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]'};
  }
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
let CONFIG = {google: false, v2: true};
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
  try { await enter(); if (gApps) toast('Google apps connected: Gmail, Calendar, Drive, Docs and Sheets.'); } catch (e) { if (e.status !== 401) showLogin(e.message); }
}
function setToken(t) { TOKEN = t || ''; if (TOKEN) store.set('hoola.console.token', TOKEN); else store.del('hoola.console.token'); }
$('#gbtn').addEventListener('click', () => {
  if (!CONFIG.google) { $('#lerr').textContent = 'Google sign-in is unavailable. Use your Hoola ID and password.'; $('#lerr').hidden = false; return; }
  $('#gbtn').innerHTML = '<span class="spin"></span> Opening Google…'; location.href = '/auth/google/start?web=1';
});
$('#lform').addEventListener('submit', async e => {
  e.preventDefault(); $('#lerr').hidden = true; const btn = $('#lbtn'); btn.disabled = true; btn.textContent = 'Signing in…';
  try { const r = await api('POST', '/api/console/login', {handle: $('#hid').value.trim(), password: $('#hpw').value}); setToken(r.session_token); $('#hpw').value = ''; await enter(); }
  catch (er) { $('#lerr').textContent = er.message; $('#lerr').hidden = false; }
  finally { btn.disabled = false; btn.textContent = 'Login'; }
});
$('#kbtn').addEventListener('click', async () => {
  const k = $('#okey').value.trim(); if (!k) return; setToken(k); $('#okey').value = '';
  try { await enter(); } catch (er) { setToken(''); $('#lerr').textContent = er.status === 401 ? 'Invalid key.' : er.message; $('#lerr').hidden = false; }
});
async function logout(expired) {
  stopStream(); endCall(); ACC?.abort(); ACC = null;
  RESULTS?.reset();
  WORKSPACE?.reset(); PN?.reset(); clearSimpleProgress();
  clearTimeout(DRAFT_T); FILES = []; CONV = null; ACC_LAST = 0; msg.value = ''; drawFiles();
  clearInterval(GAUGE_T); clearInterval(PENDING_TIMER);
  if (TOKEN && !expired) { try { await api('POST', '/api/logout'); } catch {} }
  setToken(''); showLogin(expired ? 'Your session expired. Please sign in again.' : '');
}

/* ================= state + shell ================= */
let ME = null, CONV = null, VIEW = 'chat', AV = 'Santosh';
const NAV = [['chat','Chat'],['creative','Creative studio'],['aaj','Today'],['kaam','Tools'],['baat','Voice'],['main','Account']];
IC.creative = '<path d="M4 4h16v16H4zM8 4v16M4 10h16M4 16h16"/>';
IC.bana = '<path d="M4 4h16v5H4zM4 11h7v9H4zM13 11h7v9h-7z"/>';
function drawNav() {
  $('#snav').innerHTML = NAV.map(([k, n]) => `<button class="sn" data-v="${k}" aria-current="${k === VIEW}">${svg(IC[k])}<span class="txt">${n}</span>${k === 'aaj' && QUEUE.length ? `<span class="ct txt">${QUEUE.length}</span>` : ''}</button>`).join('');
  const T = [['chat','Chat'],['aaj','Today'],['baat',''],['kaam','Kaam'],['main','Main']];
  $('#tabbar').innerHTML = T.map(([k, n]) => k === 'baat' ? `<div class="mid"><button class="baat" data-v="baat" aria-label="Baat, live voice">${svg(IC.baat).replace('currentColor', '#1B1030')}</button></div>`
    : `<button class="sn" data-v="${k}" aria-current="${k === VIEW}">${svg(IC[k])}<span>${n}</span></button>`).join('');
}
function go(v) {
  VIEW = v; $$('.view').forEach(x => x.hidden = x.id !== 'v-' + v);
  $('#ttl').textContent = {chat: chatFolder(), aaj:'· Today', kaam:'· All tools', baat:'· Baat', main:'· Main', bana:'· Creations', project:'· Folder'}[v] || '';
  if (v !== 'project') PJ?.draw();
  drawNav(); $('#app').classList.remove('drawer');
  if (v === 'aaj') drawToday(); if (v === 'main') drawMain(); if (v === 'baat') drawBaat();
  if (v === 'bana') PN?.library($('#bana'));
  if (v === 'creative') WORKSPACE?.open();
  if (v === 'creative') $('#ttl').textContent = '· Creative workspace';
}
document.addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (b) go(b.dataset.v); });
$('#menu').addEventListener('click', () => $('#app').classList.add('drawer'));
$('#scrim').addEventListener('click', () => $('#app').classList.remove('drawer'));
$('#collapse').addEventListener('click', () => $('#app').classList.toggle('collapsed'));
$('#collapse').addEventListener('click', () => {
  $('#collapse').setAttribute('aria-expanded', String(!$('#app').classList.contains('collapsed')));
});
$('#liveBtn').addEventListener('click', () => {
  if (B?.isOpen()) { B.close(); $('#app').classList.add('open'); return; }
  if (PN?.isOpen()) { PN.close(); $('#app').classList.add('open'); return; }     // v0.163 one right-hand column at a time
  $('#app').classList.toggle('open');
});
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
  $('#greet').textContent = `${h < 12 ? 'Good morning' : h < 17 ? 'Hello' : 'Good evening'}${first ? ', ' + first : ''}`;
  $('#login').hidden = true; $('#app').hidden = false; drawNav(); drawKaam(); go('chat');
  if (CONFIG.sessions && window.HoolaChats && window.HoolaStream && !CH) {   // v0.162 many chats (v0.170: on with CONSOLE_V2)
    CH = HoolaChats({api, esc, toast, current: () => CONV, open: id => { go('chat'); openConv(id); },
                     jump: (c, e) => jumpTo(c, e), newChat: () => $('#newChat').click(), avatar: () => AV,
                     get pickProject() { return PJ ? c => PJ.pick(c) : null; },
                     get openSection() { return PJ ? pid => PJ.open(pid) : null; },   // v0.193 session name opens its page
                     newChatIn: async pid => {                                        // v0.193 "+" on a session header
                       try { const c = await api('POST', `/api/conversations?project_id=${encodeURIComponent(pid)}`);
                             await openConv(c.id, true); go('chat'); loadRecents(); }
                       catch (e) { toast(e.message, true); }
                     }});
    $('#searchBtn').hidden = false;
  }
  if (CONFIG.projects && window.HoolaProjects && !PJ) {   // v0.164 Project folders
    PJ = HoolaProjects({api, esc, toast, go, avatar: () => AV, current: () => CONV,
      openChat: (id, fresh) => { go('chat'); openConv(id, fresh); }, reloadChats: () => loadRecents()});
    PJ.load();
  }
  if (CONFIG.panel && window.HoolaPanel && !PN) {   // v0.163 finished work opens beside the chat
    PN = HoolaPanel({api, esc, toast, token: () => TOKEN, conv: () => CONV, goLibrary: () => go('bana'),
      say: text => { go('chat'); msg.value = text; msg.dispatchEvent(new Event('input')); composer.requestSubmit(); },
      closeStudio: () => { if (B?.isOpen()) B.close(); },
      studio: (kind, p) => { go('chat'); const b = col.querySelector(`[data-key="${CSS.escape(kind + ':' + p.id)}"] [data-ba="studio"]`); if (b) b.click(); else toast('Studio ke liye chat mein us kaam ka card kholiye.'); }});
    NAV.splice(3, 0, ['bana', 'Creations']); drawNav();
  }
  const list = await loadRecents();
  const fromUrl = (location.pathname.match(/^\/console\/c\/([^/?#]+)/) || [])[1];
  const firstChat = async () => list[0]?.id || (await api('POST', '/api/conversations')).id;
  if (CH) accountStream();
  loadGauge(); clearInterval(GAUGE_T); GAUGE_T = setInterval(loadGauge, 300000);   // v0.173 the kharcha line stays honest
  if (CH && fromUrl) await openConv(decodeURIComponent(fromUrl), false, {noPush: true, fallback: async () => {
    toast('Woh chat nahi mili (shayad delete ho gayi). Haal ki chat khol raha hoon.'); await openConv(await firstChat()); }});
  else await openConv(await firstChat());
  refreshPending(); clearInterval(PENDING_TIMER); PENDING_TIMER = setInterval(refreshPending, 30000);
}

/* ================= recents ================= */
let CH = null;          // chatlist.js (CHAT_SESSIONS; on by default under CONSOLE_V2)
async function loadRecents() {
  if (CH) { const l = await CH.load(); if (VIEW === 'chat') $('#ttl').textContent = chatFolder(); return l; }
  let list = [];
  try { list = (await api('GET', '/api/console/conversations')).conversations || []; } catch {}
  $('#recents').innerHTML = list.map(c => `<button class="rc" data-conv="${esc(c.id)}" title="${esc(timeOf(c.updated_at))}"${c.id === CONV ? ' aria-current="true"' : ''}>${esc(c.title)}</button>`).join('') || '<div class="empty" style="padding:8px 12px">No conversations yet.</div>';
  return list;
}
$('#recents').addEventListener('click', e => { if (CH) return; const b = e.target.closest('[data-conv]'); if (b) { openConv(b.dataset.conv); go('chat'); } });
$('#searchBtn').addEventListener('click', () => CH?.openSearch());
$('#newChat').addEventListener('click', async () => {
  try { const c = await api('POST', '/api/conversations'); await openConv(c.id, true); go('chat'); loadRecents(); } catch (e) { toast(e.message, true); }
});

/* ================= chat view ================= */
const composer = $('#composer'), msg = $('#msg'), col = $('#col'), thread = $('#thread');
$('#slotLand').appendChild(composer);
/* stick to the bottom: the newest line stays in view while a reply grows; scrolling up stops the pull and shows
   "Neeche jao". Handled here (Safari has no overflow-anchor): a ResizeObserver re-pins only while she is at the bottom. */
let STICK = true;
const scrollDown = force => { if (force) STICK = true; if (STICK) thread.scrollTop = thread.scrollHeight; $('#jump').hidden = STICK; };
const unstick = () => { if (thread.scrollHeight - thread.clientHeight > 4) { STICK = false; $('#jump').hidden = false; } };
thread.addEventListener('scroll', () => { const d = thread.scrollHeight - thread.scrollTop - thread.clientHeight; if (d < 48) { STICK = true; $('#jump').hidden = true; } else if (!STICK) $('#jump').hidden = false; }, {passive: true});
thread.addEventListener('wheel', e => { if (e.deltaY < 0) unstick(); }, {passive: true});
let touchY = 0;
thread.addEventListener('touchstart', e => { touchY = e.touches[0]?.clientY || 0; }, {passive: true});
thread.addEventListener('touchmove', e => { if ((e.touches[0]?.clientY || 0) > touchY + 6) unstick(); }, {passive: true});
thread.addEventListener('keydown', e => { if (['PageUp', 'ArrowUp', 'Home'].includes(e.key)) unstick(); });
if (window.ResizeObserver) new ResizeObserver(() => { if (STICK) thread.scrollTop = thread.scrollHeight; }).observe(col);
$('#jump').addEventListener('click', () => { thread.scrollTo({top: thread.scrollHeight, behavior: 'smooth'}); STICK = true; $('#jump').hidden = true; });
function landing(on) {
  $('#landing').hidden = !on; $('#thread').hidden = on; $('#dock').hidden = on;
  (on ? $('#slotLand') : $('#slotDock')).appendChild(composer);
}
let TURN = null;          // the open Hoola turn: {bd, tools, tl, text, steps:{}}
let USER_ECHO = [];       // texts she sent from here (their echo from the server is not drawn twice)
const RCPTS = new Map();  // v0.173 client_id -> {el, chip} receipts of messages sent while Hoola was busy

let SINK = col;           // where new rows go (an off-screen box while an older page is drawn above)
let STEPBUF = null;       // v0.171 replay: consecutive step events fold into one closed group, like a live turn
function replayStep(p) {
  const id = String(p.id || p.tool || Math.random());
  if (p.args) STEPS_ARGS.set(id, p.args);
  if (p.state === 'running') return;      // the done / error step of the same call follows it
  if (!STEPBUF) {
    STEPBUF = document.createElement('details'); STEPBUF.className = 'tools'; STEPBUF.open = false;
    STEPBUF.innerHTML = `<summary><span class="ic" style="width:18px;height:18px;font-size:10px">✓</span><span class="sm"></span><span class="chev">⌄</span></summary><div class="tl"></div>`;
    SINK.appendChild(STEPBUF);
  }
  const row = p.state === 'error' ? `<span class="ic" style="background:rgba(248,113,113,.18);color:var(--bad)">!</span>${esc(p.label || p.tool)} <code>${esc(p.tool || '')}</code>${p.detail ? `<span class="tm">${esc(String(p.detail).slice(0, 60))}</span>` : ''}`
    : `<span class="ic">✓</span>${esc(p.label || p.tool)} <code>${esc(p.tool || '')}</code>`;
  const has = !!STEPS_ARGS.get(id)?.length;
  const el = document.createElement(has ? 'details' : 'div'); el.className = 'ts ' + (p.state === 'error' ? 'err' : 'done');
  if (has) { el.innerHTML = `<summary>${row}<span class="chev" aria-hidden="true">⌄</span></summary>${stepArgsHtml(id)}`; el.open = false; }
  else el.innerHTML = row;
  STEPBUF.querySelector('.tl').appendChild(el);
}
function flushStepBuf() {
  if (!STEPBUF) return;
  const n = STEPBUF.querySelectorAll('.ts').length;
  if (!n) STEPBUF.remove();
  else STEPBUF.querySelector('.sm').textContent = `${n} kadam${n > 1 ? '' : ''}`;
  STEPBUF = null;
}
function userBubble(text, files, eid, cid, at) {
  const d = document.createElement('div'); d.className = 'mu';
  d.innerHTML = (files?.length ? `<div class="att">${files.map(f => `<span class="chip">📎 ${esc(f.name || f)}</span>`).join('')}</div>` : '') + `<span class="mut">${esc(text)}</span>`;
  if (cid) d.dataset.cid = cid;
  if (eid && !files?.length) attachEdit(d, text, eid);
  if (at) d.dataset.at = at;                             // v0.178 the jump rail reads the day off this
  SINK.appendChild(d); if (SINK === col) scrollDown(true); TURN = null; return d;
}
/* v0.173 receipts: a message sent while Hoola works shows what became of it — queue mein (take-back possible),
   turant jawab (the quick lane answered beside the running kaam), bhej diya (the queued turn took it). */
function receipt(d, cid, state) {
  const R = RCPTS.get(cid) || {};
  R.el = d; R.state = state; RCPTS.set(cid, R);
  d.querySelector('.rq')?.remove();
  if (state === 'queue') {
    d.insertAdjacentHTML('beforeend', `<span class="rq">⏳ queue mein — Hoola ke is kaam ke baad chalega <button type="button" class="rqx">Wapas lo</button></span>`);
    d.querySelector('.rqx').addEventListener('click', async e => {
      e.stopPropagation();
      try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/takeback`, {client_id: cid});
        d.style.transition = 'opacity .25s, transform .25s'; d.style.opacity = '0'; d.style.transform = 'translateY(6px)';
        setTimeout(() => d.remove(), 240); RCPTS.delete(cid); toast('Wapas le liya — Hoola tak pahunchi hi nahi.'); }
      catch (er) { receipt(d, cid, 'sent'); toast(er.status === 409 ? 'Yeh chal padi hai — Stop dabaiye.' : er.message, er.status !== 200); }
    });
  } else if (state === 'quick') {
    d.insertAdjacentHTML('beforeend', `<span class="rq ok">⚡ turant jawab alag se diya</span>`);
    setTimeout(() => { d.querySelector('.rq')?.remove(); RCPTS.delete(cid); }, 6000);
  } else {
    d.insertAdjacentHTML('beforeend', `<span class="rq ok">✓ bhej diya</span>`);
    setTimeout(() => { d.querySelector('.rq')?.remove(); RCPTS.delete(cid); }, 3000);
  }
}
function receiptUpdate(cid, state) { const R = RCPTS.get(cid); if (R && R.state === 'queue') receipt(R.el, cid, state); }
function attachEdit(d, text, eid) {   // v0.171 her message gets a hover toolbar: Copy + Edit (a new version from here)
  d.dataset.eid = eid;
  if (!CH || d.querySelector('.utbar')) return;
  d.insertAdjacentHTML('beforeend', `<span class="utbar" role="group" aria-label="Message actions">`
    + `<button type="button" class="ua" data-ua="copy" aria-label="Copy">${svg('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>')}</button>`
    + `<button type="button" class="ua" data-ua="edit" aria-label="Message badlo">${svg('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>')}</button></span>`);
  bindUserBar(d, text);
}
function bindUserBar(d, text) {   // separate: Edit ka Cancel the same toolbar dobara jodta hai
  d.querySelector('[data-ua="copy"]')?.addEventListener('click', async e => {
    e.stopPropagation();
    if (await copyText(text)) { const b = e.currentTarget; b.classList.add('did'); setTimeout(() => b.classList.remove('did'), 1200); }
  });
  d.querySelector('[data-ua="edit"]')?.addEventListener('click', e => { e.stopPropagation(); editBubble(d, text); });
}
function editBubble(d, text) {
  if (TYPING) return toast(`${AV} abhi kaam kar raha hai. First Stop.`, true);
  const keep = d.innerHTML; d.classList.add('editing');
  d.innerHTML = `<textarea aria-label="Message badlo" rows="2"></textarea><div class="acts"><button type="button" class="btn soft" data-x>Cancel</button><button type="button" class="btn go" data-s>Bhejo</button></div>`;
  const ta = d.querySelector('textarea'); ta.value = text; ta.focus(); ta.setSelectionRange(text.length, text.length);
  ta.style.height = Math.min(220, ta.scrollHeight) + 'px'; ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(220, ta.scrollHeight) + 'px'; });
  const cancel = () => { d.classList.remove('editing'); d.innerHTML = keep; bindUserBar(d, text); };
  const save = async () => {
    const t = ta.value.trim(); if (!t || t === text) return cancel();
    d.querySelector('[data-s]').disabled = true;
    try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/edit`, {event_id: +d.dataset.eid, text: t}); await openConv(CONV, false, {noPush: true}); }
    catch (e) { toast(e.message, true); cancel(); }
  };
  d.querySelector('[data-x]').addEventListener('click', cancel); d.querySelector('[data-s]').addEventListener('click', save);
  ta.addEventListener('keydown', e => { if (e.key === 'Escape') cancel(); if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); save(); } });
}
function hoolaBlock() {
  const d = document.createElement('div'); d.className = 'mh';
  d.innerHTML = `<span class="av"><img src="${$('#uimg').src}" alt=""></span><div class="bd"></div>`;
  SINK.appendChild(d); return d.querySelector('.bd');
}
function turn() { if (!TURN) TURN = {bd: hoolaBlock(), groups: [], text: null, afterText: false, t0: Date.now()}; return TURN; }
/* new content of the turn goes above the typing dots */
function put(t, el) { t.bd.insertBefore(el, TYPING && TYPING.parentNode === t.bd ? TYPING : null); }

const md = text => window.HoolaMD ? HoolaMD.render(text, false) : esc(text);
function hoolaText(text, source, eid, at) {   // a reply without a turn id (streaming off, notes, greetings): as before
  const t = turn();
  if (t.text && (text.startsWith(t.text.dataset.raw) || t.text.dataset.raw === text)) { t.text.dataset.raw = text; t.text.innerHTML = md(text); if (eid) t.text.dataset.eid = eid; if (at) t.text.closest('.mh').dataset.at = at; scrollDown(); return; }
  const el = document.createElement('div'); el.className = 'txt textmd'; el.dataset.raw = text; el.innerHTML = md(text);
  if (eid) el.dataset.eid = eid;
  if (source === 'worker' || source === 'greeting') el.classList.add('note-in');
  put(t, el); t.text = el; t.afterText = true;
  if (at && t.bd.closest('.mh')) t.bd.closest('.mh').dataset.at = at;   // v0.178 rail day stamp
  scrollDown();
}

/* steps (tool calls) inside the turn + the live panel: in the order they happened (text -> steps -> text);
   each run of steps is one group that folds into "N kadam · Xs" when the turn is over.
   v0.171 every step opens: what the model asked (masked args brief) + what came back (the work line's facts). */
const STEPS_ARGS = new Map();   // step id -> [[k, v], ...] from the server (secrets dropped server-side)
const STEPS_DATA = new Map();   // step id -> the `work` event's display facts (site, amount, note...)
function stepArgsHtml(id) {
  const rows = [];
  for (const [k, v] of STEPS_ARGS.get(id) || []) rows.push(`<span>${esc(k)}</span><b>${esc(v)}</b>`);
  for (const [k, v] of Object.entries(STEPS_DATA.get(id) || {})) {
    if (v == null || typeof v === 'boolean') continue;
    if (Array.isArray(v)) {
      const s = v.map(x => typeof x === 'string' ? x : Array.isArray(x) ? x.join(': ') :
        [x.from, x.subject, x.name, x.device].filter(Boolean).join(' · ') || '').filter(Boolean).slice(0, 4).join(', ');
      if (s) rows.push(`<span>${esc(k)}</span><b>${esc(s.slice(0, 140))}</b>`);
      continue;
    }
    if (typeof v === 'object') continue;
    rows.push(`<span>${esc(k)}</span><b>${esc(String(v).slice(0, 140))}</b>`);
  }
  return rows.length ? `<div class="targs"><div class="kv">${rows.join('')}</div></div>` : '';
}
const PROGRESS_POLICY = window.HoolaProgressPolicy;
let SIMPLE_PROGRESS = null;
function simpleProgress(kind,p={}) {
  if(kind!=='typing' && !TYPING)return;
  if (!SIMPLE_PROGRESS) {
    SIMPLE_PROGRESS=document.createElement('div');SIMPLE_PROGRESS.className='simple-progress';
    SIMPLE_PROGRESS.setAttribute('role','status');SIMPLE_PROGRESS.setAttribute('aria-live','polite');
    $('#slotDock').before(SIMPLE_PROGRESS);
  }
  SIMPLE_PROGRESS.hidden=false;
  const label=PROGRESS_POLICY.phase(kind,p);
  if(SIMPLE_PROGRESS.textContent!==label)SIMPLE_PROGRESS.textContent=label;
}
function clearSimpleProgress(){if(SIMPLE_PROGRESS)SIMPLE_PROGRESS.hidden=true;}
function stepEvent(p) { simpleProgress('step',p); }
function closeTurnTools(t = TURN) {
  if (!t) return;
  for (const g of t.groups || []) {
    if (g.closed) continue; g.closed = true;
    const secs = Math.round((Date.now() - g.t0) / 1000);
    g.el.querySelector('summary').innerHTML = `<span class="ic" style="width:18px;height:18px;border-radius:50%;display:grid;place-items:center;background:rgba(52,211,153,.18);color:var(--ok);font-size:10px;font-weight:900">✓</span><span>${g.n} kadam · ${secs < 1 ? '<1' : secs} s</span><span class="chev">⌄</span>`;
    g.el.open = false;
  }
}
let TYPING = null;
function typing(on) {
  $('#stopBtn').hidden=!on;
  if(on){TYPING ||= document.createElement('div');simpleProgress('typing');live('run');}
  else {
    TYPING=null;clearSimpleProgress();closeTurnTools();
    for(const [cid,R] of [...RCPTS])if(R.state==='queue')receiptUpdate(cid,'sent');
    live(QUEUE.length?'ask':'idle');TURN=null;
  }
}

/* ================= thinking card (v0.171): the model's reasoning while it thinks — Claude thinking /
   GLM reasoning arrive as live-only `think` events (turn:seg, like the text blocks). Live: open, counting.
   Reply over: folded to "ne socha · 8s". Never stored, so a reload builds it only from a /live resume. */
const THINKS = new Map();   // turn:seg -> {el, tb, t0, timer}
function thinkEvent(p) { simpleProgress('think',p); }
function closeThinks(turnId) {
  for (const [key, K] of [...THINKS]) {
    if (!key.startsWith(turnId + ':')) continue;
    THINKS.delete(key); clearInterval(K.timer);
    if (!K.raw.trim()) { K.el.remove(); continue; }        // thought but never said anything worth keeping
    const s = Math.max(1, Math.round((Date.now() - K.t0) / 1000)), tt = K.el.querySelector('.tt'), sm = K.el.querySelector('.tsm');
    if (tt) tt.textContent = s < 60 ? s + 's' : Math.floor(s / 60) + 'm' + String(s % 60).padStart(2, '0');
    if (sm) sm.textContent = `${AV} ne socha`;
    K.el.open = false;
  }
}

/* ================= streamed replies: one per turn id, text blocks (seg) paced word by word ================= */
const REPLIES = new Map();   // turn -> {turn, t, segs: Map(seg -> {el, live, pacer}), seq, done, acts, fb}
let LAST_TURN = null;
function reply(turnId) {
  let R = REPLIES.get(turnId);
  if (!R) { R = {turn: turnId, t: turn(), segs: new Map(), seq: 0, done: false, acts: null, fb: ''}; REPLIES.set(turnId, R); }
  return R;
}
function seg(R, n) {
  let S = R.segs.get(n);
  if (S) return S;
  const el = document.createElement('div'); el.className = 'txt textmd'; el.dataset.seg = n;
  put(R.t, el); R.t.afterText = true;
  if (TYPING && TYPING.parentNode === R.t.bd) TYPING.hidden = true;    // the words themselves show that it is working
  const view = new HoolaMD.Live(el);
  S = {el, view, pacer: new HoolaStream.Pacer((text, fin) => { view.update(text, !fin); scrollDown(); })};
  R.segs.set(n, S);
  return S;
}
function replyMessage(p, instant, eid, at) {
  const R = reply(p.turn), S = seg(R, p.seg ?? 0);
  if (eid) S.el.dataset.eid = eid;
  if (at && !S.el.dataset.at) S.el.dataset.at = at;   // v0.178 rail day stamp (first seg wins)
  if (instant) { S.pacer.finalText = p.text || ''; S.pacer.flush(); } else S.pacer.final(p.text || '');
  S.el.classList.toggle('stopped', !!p.stopped);
  if (instant) R.done = true;
}
function replyText(R) { return [...R.segs.values()].map(S => S.pacer.finalText ?? S.pacer.target).filter(Boolean).join('\n\n'); }
function drawActs(R) {
  R.acts?.remove();
  if (!R.done || !R.segs.size) return;
  const a = document.createElement('div'); a.className = 'racts'; a.setAttribute('role', 'group'); a.setAttribute('aria-label', 'Reply actions');
  const can = !!CONFIG.stream, last = R.turn === LAST_TURN;
  a.innerHTML = `<button type="button" class="ra" data-act="copy" aria-label="Copy reply">${svg('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>')}<span>Copy</span></button>`
    + `<button type="button" class="ra" data-act="quote" aria-label="Quote karein" title="Composer mein quote karein">${svg('<path d="M4 5h16v11H8l-4 4z"/><path d="M8 9h8M8 12h5"/>')}<span>Quote</span></button>`
    + (can && last ? `<button type="button" class="ra" data-act="retry" aria-label="Retry">${svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>')}<span>Dobara</span></button>` : '')
    + (can ? `<button type="button" class="ra" data-act="up" aria-label="Accha jawab" aria-pressed="${R.fb === 'up'}">${svg('<path d="M7 10v11H3V10zM7 10l5-8a3 3 0 0 1 3 3v4h5a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7"/>')}</button>`
      + `<button type="button" class="ra" data-act="down" aria-label="Kharab jawab" aria-pressed="${R.fb === 'down'}">${svg('<path d="M17 14V3h4v11zM17 14l-5 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.4 3H17"/>')}</button>` : '')
    + (R.stopped ? '<span class="rstop">Roka gaya</span>' : '');
  a.addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (b) replyAct(R, b.dataset.act, b); });
  R.t.bd.appendChild(a); R.acts = a;
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; }
  catch { const ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch {} ta.remove(); return ok; }
}
async function replyAct(R, act, b) {
  if (act === 'copy') { if (await copyText(replyText(R))) { b.querySelector('span').textContent = 'Copied ✓'; setTimeout(() => { const s = b.querySelector('span'); if (s) s.textContent = 'Copy'; }, 1500); } else toast('Could not copy.', true); return; }
  if (act === 'quote') {   // v0.171 the reply goes into the composer as a quote, so she can point at any line of it
    const q = (replyText(R) || '').trim().split('\n').map(l => '> ' + l).join('\n');
    if (!q) return;
    go('chat'); msg.value = (msg.value ? msg.value.replace(/\s*$/, '\n\n') : '') + q + '\n\n';
    msg.dispatchEvent(new Event('input')); msg.focus(); msg.setSelectionRange(msg.value.length, msg.value.length);
    return;
  }
  if (act === 'up' || act === 'down') {
    const value = R.fb === act ? 'none' : act;
    try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/feedback`, {turn: R.turn, value}); R.fb = value === 'none' ? '' : value; drawActs(R);
      if (value === 'down') toast('Shukriya. Behtar jawab ke liye "Dobara" dabaiye ya bataiye kya galat tha.'); }
    catch (e) { toast(e.message, true); }
    return;
  }
  if (act === 'retry') {
    if (TYPING) return toast(`${AV} abhi kaam kar raha hai. First Stop.`, true);
    b.disabled = true;
    try {
      await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/retry`);
      for (const S of R.segs.values()) { S.pacer.reset(); S.el.remove(); }   // the old words go; cards and steps stay
      R.acts?.remove(); REPLIES.delete(R.turn); if (LAST_TURN === R.turn) LAST_TURN = null; TURN = null; scrollDown(true);
    } catch (e) { b.disabled = false; toast(e.message, true); }
  }
}
document.addEventListener('click', async e => {     // Copy on a code block
  const b = e.target.closest('[data-copy]'); if (!b) return;
  const code = b.closest('.cb')?.querySelector('code'); if (!code) return;
  if (await copyText(code.textContent || '')) { b.textContent = 'Copied ✓'; setTimeout(() => b.textContent = 'Copy', 1500); }
});
document.addEventListener('visibilitychange', () => { if (document.hidden) REPLIES.forEach(R => R.segs.forEach(S => { if (S.pacer.raf) S.pacer.flush(); })); });

/* ================= live work line ================= */
const WHERE = {browser:'Hoola ka browser · server', pc:'Aapka PC', email:'Email', payment:'Payment · your approval', network:'Hoola Network', bluetooth:'Ghar', website:'Website'};
function workEvent(p) {
  simpleProgress("work",p);
  const err = p.phase === 'error' || p.phase === 'stopped';
  if (p.id && p.data) STEPS_DATA.set(String(p.id), p.data);   // v0.171 the step's facts join its args in the chip
  $('#stageCap').textContent = err ? (p.phase === 'stopped' ? 'Roka gaya: ' : 'Dikkat: ') + (p.error || p.label || '') : (p.label || p.tool || 'Kaam');
  const site = p.data && (p.data.site || p.data.url) ? ' · ' + String(p.data.site || p.data.url).slice(0, 60) : '';
  $('#stageWhere').textContent = (WHERE[p.scene] || 'Hoola server') + site + (p.phase === 'done' ? ' · ho gaya' : p.phase === 'waiting' ? ' · aapki haan' : '');
  $('#nowline').classList.toggle('err', err);
  // Detailed activity opens only when the user requests it.
}
function live(state) {
  const b = $('#liveBtn'); b.classList.toggle('on', state !== 'idle');
  $('#liveTxt').textContent = state === 'run' ? 'Kaam chal raha' : state === 'ask' ? 'Your approval' : 'Live';
  $('#liveTag').textContent = state === 'run' ? 'chal raha' : state === 'ask' ? 'Approval required' : 'Idle';
  $('#liveTag').className = 'tag ' + (state === 'ask' ? 'warn' : 'ok');
}

/* ================= cards ================= */
const LABEL = {bazar_approval:'Your approval is required', employee_ask:'Employee question', operator_ask:'Website job ko aapki zaroorat', operator_task:'Website job',
  email_draft:'Email draft', hoola_deal:'Hoola Deal', hoola_knock:'Hoola Network', hoola_msg:'Hoola Network message', calendar_event:'Calendar',
  reminders:'Reminders', lists:'Lists', gyaan_sources:'Sources', call_receipt:'Call receipt', procedure:'Seekha', memory_saved:'Saved to memory',
  artifact:'Page', pc_file:'File', photo_made:'Picture', motion:'Reel', video_job:'Video', studio_approval:'AI video cost', gst_return:'GST return',
  payroll_run:'Salary run', google_reconnect:'Google dobara jodiye', campaign:'WhatsApp campaign', share_ask:'Share karein?'};
const CARDS = new Map();      // kind:id -> element (updated in place)
// Build studio (build.js): website / app design / Android builds live, like the phone app
const B = window.HoolaBuild ? window.HoolaBuild({api, esc, toast, narrow, conv: () => CONV,
  say: text => { go('chat'); msg.value = text; msg.dispatchEvent(new Event('input')); composer.requestSubmit(); }}) : null;
let PN = null;          // panel.js (SIDE_PANEL)
let PJ = null;          // projects.js (CHAT_PROJECTS)
const RESULTS = window.HoolaResults ? HoolaResults({api, esc, toast,
  itemOf: (kind, p) => PN?.itemOf(kind, p), open: item => PN?.open(item),
  reuse: item => WORKSPACE?.reuse(item), resize: () => scrollDown()}) : null;
const WORKSPACE = window.HoolaWorkspace ? HoolaWorkspace({api, esc, toast, conv: () => CONV,
  library: () => PN ? go('bana') : toast('Creations workspace is not enabled on this server.',true), show: () => {
    VIEW = 'creative'; $$('.view').forEach(x => x.hidden = x.id !== 'v-creative'); drawNav();
    $('#ttl').textContent = '· Creative workspace'; $('#app').classList.remove('drawer');
  },
  openChat: id => { go('chat'); openConv(id, false, {noPush: true}); },
  submit: async (id, text, files) => {
    const auth = TOKEN;
    const body = {text, files, client_id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())};
    for (let i=0; i<3; i++) {
      if (!auth || TOKEN !== auth) throw new Error('Session changed. Open your conversation and try again.');
      try { return await api('POST', `/api/conversations/${encodeURIComponent(id)}/messages`, body); }
      catch(e) { if(i===2 || (e.status && e.status<500)) throw e; await new Promise(r=>setTimeout(r,600*(i+1))); }
    }
  }}) : null;
// Workflow entry points stay connected to the same conversation and its real output events.
$('#slotLand').insertAdjacentHTML('beforebegin', '<div class="workflow-entry" aria-label="Create with Hoola"><button type="button" data-create="image">Image creation</button><button type="button" data-create="video">Video & motion</button><button type="button" data-create="research">Research</button><button type="button" data-create="document">Documents</button></div>');
document.addEventListener('click', e => {
  const b=e.target.closest('[data-create]'); if(!b || !WORKSPACE)return;
  go('creative'); WORKSPACE.open(b.dataset.create);
});
function chatFolder() { const c = CH?.find(CONV), p = c?.project_id && PJ?.nameOf(c.project_id); return p ? `· ${p.emoji || '📁'} ${p.name}` : ''; }
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

function renderCard(kind, p, at, live) {
  if(PROGRESS_POLICY.quiet(kind,p)){if(live)simpleProgress(kind,p);return;}
  if (B && B.kinds.has(kind)) { const el = cardShell(kind, p); B.card(kind, p, el, !!live); scrollDown(); return; }
  if (RESULTS?.kinds.has(kind) && PN?.itemOf(kind, p) && (kind !== 'artifact' || p.status === 'ready')) {
    const el = cardShell(kind, p); RESULTS.card(kind, p, el); if (live) PN.update(kind, p); scrollDown(); return;
  }
  if (kind === 'goal') {   // v0.186 lamba kaam pakka: live checklist, one card per goal id
    const el = cardShell(kind, p);
    const st = p.status || 'working';
    const HEAD = {working: 'LAMBA KAAM CHAL RAHA HAI', done: 'LAMBA KAAM POORA HUA', blocked: 'AAPKE JAWAB KA INTEZAAR',
                  failed: 'LAMBA KAAM ADHOORA RAHA', stopped: 'LAMBA KAAM ROK DIYA GAYA'};
    const steps = Array.isArray(p.steps) ? p.steps : [];
    const done = p.done != null ? p.done : steps.filter(x => x.state === 'done').length;
    const total = p.total != null ? p.total : steps.length;
    const ico = {done: '\u2713', current: '\u23F3', failed: '\u2715', skipped: '\u2013', pending: '\u2022'};
    el.innerHTML = head(HEAD[st] || HEAD.working, total ? (done + '/' + total) : '', st === 'done' ? 'ok' : st === 'failed' ? 'bad' : 'v') +
      `<div class="bd" style="margin-top:4px"><b>${esc(p.title || p.goal || 'Lamba kaam')}</b>` +
      (total ? `<div class="pbar"><i style="width:${Math.max(0, Math.min(100, p.pct ?? Math.round(100 * done / total)))}%"></i></div>` : '') +
      steps.slice(0, 15).map(x => `<div class="gstep ${esc(x.state || 'pending')}"><span>${ico[x.state] || '\u2022'}</span> ${esc(x.text || '')}` +
        (x.note ? ` <small>(${esc(x.note)})</small>` : '') + `</div>`).join('') +
      (p.reason && st !== 'working' ? `<div class="note">${esc(p.reason)}</div>` : '') + `</div>`;
    scrollDown(); return;
  }
  if (kind === 'gyaan_sources') {
    const el = document.createElement('details'); el.className = 'result-sources';
    const sources = p.sources || [];
    el.innerHTML = `<summary>Sources · ${sources.length}</summary>` + sources.map((s, i) => {
      const url = safeLink(s.link);
      return `<article><b>[${esc(s.n ?? '')}] ${esc(s.title || s.source || '')}</b>`
        + (s.page ? `<span class="faint">Page ${esc(s.page)}</span>` : '')
        + (s.snippet ? `<p>${esc(s.snippet)}</p>` : '')
        + (url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>` : '')
        + (s.file_id && PN ? `<button class="btn soft" type="button" data-source="${i}">Open file</button>` : '') + '</article>';
    }).join('');
    el.addEventListener('click', e => {
      const b = e.target.closest('[data-source]'); if (!b) return;
      const s = sources[Number(b.dataset.source)];
      PN?.open({type: 'file', ref: s.file_id, title: s.title || 'Source file'});
    });
    turn().bd.appendChild(el); return;
  }
  if (kind === 'memory_saved' || kind === 'procedure') {
    const el = document.createElement('div'); el.className = 'note'; el.textContent = (kind === 'memory_saved' ? '📌 Saved to memory: ' : '🎓 Seekha: ') + (p.text || p.title || ''); turn().bd.appendChild(el); return;
  }
  const el = cardShell(kind, p);
  switch (kind) {
    case 'bazar_approval': {
      el.innerHTML = head(p.title || 'Your approval is required', p.money ? 'paisa' : 'Your approval', p.money ? 'bad' : 'warn')
        + (p.amount ? `<div class="big">${esc(p.amount)}</div>` : '') + (p.payee ? `<div class="faint" style="font-size:13px">${esc(p.payee)}</div>` : '')
        + (p.items || []).map(i => `<div class="ln"><span>${esc(i.name)}</span><b>${esc(i.price)}</b></div>`).join('')
        + (p.disclosures || []).map(i => `<div class="ln"><span>${esc(i.label)}</span><b>${esc(i.value)}</b></div>`).join('')
        + (p.voice_ok && !p.money ? `<p class="faint" style="font-size:12.5px">Bol kar ya chat mein bhi ho jayega — "haan karo" ya "approve" kahiye.</p>` : '');
      if (p.status && p.status !== 'pending') { decided(el, p.status === 'approved', p.status === 'approved' ? '✓ Haan diya' : '✕ ' + p.status); break; }
      decisionRow(el, {
        yes: async () => { try { await api('POST', `/api/bazar/approvals/${encodeURIComponent(p.id)}`, {decision: 'approve'}); decided(el, true, '✓ Haan diya'); }
                           catch (e) { if (e.status === 428) { decided(el, false, '📱 ' + fingerprintMsg); return; } throw e; } },
        no: async () => { await api('POST', `/api/bazar/approvals/${encodeURIComponent(p.id)}`, {decision: 'reject'}); decided(el, false, '✕ Mana kiya'); }});
      break; }
    case 'employee_ask': {
      el.innerHTML = head(p.what || 'Employee question', p.duty_label || 'Employee', 'warn') + `<div class="kv">${[['Kisne', p.who], ['Kyon', p.why], ['Kya', p.detail]].filter(([, v]) => v).map(([k, v]) => `<span>${k}</span><b>${esc(v)}</b>`).join('')}</div>`;
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
          if (typed && !answer) { toast('First jawab likhiye.', true); throw new Error('empty'); }
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
    case 'share_ask': {   // Share from the panel: nothing is public until she says Haan here
      const own = typeof p.url === 'string' && p.url.startsWith(location.origin + '/') ? p.url : '';
      const url = p.status === 'approved' ? (safeLink(p.url) || own) : '';
      el.innerHTML = head(p.title || 'Share karein?', p.status === 'pending' ? 'Your approval' : p.status === 'approved' ? 'shared' : 'nahi', p.status === 'pending' ? 'warn' : 'v')
        + `<div class="kv"><span>Kya</span><b>${esc(p.what || '')}</b></div><p style="font-size:14px">${esc(p.say || '')}</p>`
        + (url ? `<div class="acts"><input class="fld" readonly value="${esc(url)}" aria-label="Share link"><button class="btn soft" type="button" data-copy-link>Copy link</button></div>` : '');
      el.querySelector('[data-copy-link]')?.addEventListener('click', async e => { if (await copyText(url)) e.target.textContent = 'Copied ✓'; });
      if (p.status !== 'pending') break;
      decisionRow(el, {yesLabel: 'Slide karke share karein',
        yes: async () => { const r = await api('POST', `/api/panel/share/${encodeURIComponent(p.id)}`, {approve: true}); renderCard(kind, r); },
        no: async () => { const r = await api('POST', `/api/panel/share/${encodeURIComponent(p.id)}`, {approve: false}); renderCard(kind, r); }});
      break; }
    default: {
      const tk = ['title', 'name', 'label', 'what', 'subject'].find(k => p[k]), sk = ['say', 'summary', 'text', 'reason', 'message'].find(k => p[k]);
      const title = (tk && p[tk]) || LABEL[kind] || kind.replace(/_/g, ' ');
      const sub = (sk && p[sk]) || '';
      const pit = PN?.itemOf(kind, p);     // finished work opens beside the chat, not in a new tab
      const link = pit ? '' : safeLink(p.url || p.link || p.open_url || '');
      const money = /approval|_pay|deal|studio|payroll|spend|bill/.test(kind) && (p.status === 'pending' || p.waiting);
      el.innerHTML = head(title, LABEL[kind] && LABEL[kind] !== title ? LABEL[kind] : (p.status || ''), money ? 'warn' : 'v')
        + (sub ? `<p style="font-size:14px">${esc(String(sub).slice(0, 600))}</p>` : '')
        + (pit ? `<div class="acts"><button class="btn go" type="button" data-pn>Kholo</button></div>` : '')
        + (link ? `<div class="acts"><a class="btn soft" href="${esc(link)}" target="_blank" rel="noopener noreferrer">Kholo</a></div>` : '')
        + (money ? `<p class="faint" style="font-size:12.5px">Is card par Haan Hoola app se hoti hai (fingerprint ya app ka apna screen).</p>` : '');
      el.querySelector('[data-pn]')?.addEventListener('click', () => PN.open(pit));
      if (live) PN?.update(kind, p);
    }
  }
  scrollDown();
}

/* ================= events (SSE over fetch, stream.js) ================= */
let STREAM = null, LAST = 0;
function setConn(state, text) { const c = $('#conn'); c.className = 'conn ' + state; c.querySelector('span').textContent = text; }
function stopStream() { if (STREAM) { STREAM.abort(); STREAM = null; } }
function stream(conv) {
  stopStream();
  const s = HoolaStream.open({url: `/api/conversations/${encodeURIComponent(conv)}/events`, token: TOKEN, after: LAST,
    onState: setConn, onAuth: () => logout(true),
    onEvent: ev => {
      if (STREAM !== s || CONV !== conv) return;
      if (ev.kind === 'resync') { setTimeout(() => openConv(conv), 0); return; }
      if (!ev.live) LAST = ev.id;
      onEvent(ev);
    }});
  STREAM = s;
}
function onEvent(ev) {
  const p = {...(ev.payload || {})};
    if (p.role === 'user' && typeof p.text === 'string') p.text = p.text.replace(/\n\n\[Web console language preference: Reply in English unless I explicitly request another language\.\]$/, '');
  switch (ev.kind) {
    case 'reply_start': {
      simpleProgress('reply_start',p);
      landing(false); const prev = LAST_TURN; LAST_TURN = p.turn; reply(p.turn);
      if (prev && REPLIES.has(prev)) drawActs(REPLIES.get(prev));         // Dobara only on the newest reply
      return; }
    case 'delta': {
      const R = reply(p.turn); if (p.seq <= R.seq) return; R.seq = p.seq;
      landing(false); seg(R, p.seg ?? 0).pacer.push(p.text || ''); return; }
    case 'delta_reset': { const S = REPLIES.get(p.turn)?.segs.get(p.seg ?? 0); if (S) S.pacer.reset(); return; }
    case 'reply_end': {
      const R = REPLIES.get(p.turn); if (!R) return;
      R.segs.forEach(S => S.pacer.flush()); R.done = true; R.stopped = !!p.stopped; drawActs(R); closeTurnTools(R.t);
      closeThinks(p.turn);   // v0.171 the Soch cards fold when the reply is over
      return; }
    case 'message':
      if (p.role === 'user') {
        if (p.client_id && col.querySelector(`.mu[data-cid="${CSS.escape(p.client_id)}"]`)) {
          const b = col.querySelector(`.mu[data-cid="${CSS.escape(p.client_id)}"]`);   // her own send, echoed back
          if (!b.dataset.eid && !p.files?.length) attachEdit(b, p.text, ev.id); else b.dataset.eid = ev.id;
          return;
        }
        const i = USER_ECHO.indexOf(p.text);
        if (i > -1) {   // her own send, already drawn: it now gets its event id (Edit, search jumps)
          USER_ECHO.splice(i, 1); const b = [...col.querySelectorAll('.mu:not([data-eid])')].pop();
          if (b && !p.files?.length) attachEdit(b, p.text, ev.id); else if (b) b.dataset.eid = ev.id;
          return;
        }
        landing(false); userBubble(p.text, p.files, ev.id, null, ev.at); return;
      }
      if (p.source === 'greeting' && !col.children.length) return;        // the landing greets instead
      landing(false);
      if (p.source === 'quick') {   // v0.173 the quick lane answered beside the running kaam: flip the receipt
        const qr = [...RCPTS].reverse().find(([, R]) => R.state === 'queue');
        if (qr) receiptUpdate(qr[0], 'quick');
      }
      if (p.turn && window.HoolaStream) { replyMessage(p, false, ev.id, ev.at); const R = REPLIES.get(p.turn); if (R?.done) drawActs(R); return; }
      hoolaText(p.text || '', p.source, ev.id, ev.at); return;
    case 'typing': typing(!!p.on); return;
    case 'step': landing(false); stepEvent(p); return;
    case 'work': workEvent(p); return;
    case 'say': {
      simpleProgress('say',p);
      // The backend's real result summary is transient progress, never a generic result card.
      $('#stageCap').textContent = p.text || 'Kaam chal raha hai'; return;
    }
    case 'think': landing(false); thinkEvent(p); return;   // v0.171 the model's reasoning, live in its card
    default: landing(false); renderCard(ev.kind, p, ev.at, true);
      if (/ask|approval|draft|_sign|quote|confirm|knock/.test(ev.kind)) refreshPending();
  }
}

/* ================= open a conversation ================= */
let LOADING = false, PENDING = [], BEFORE = 0, HAS_MORE = false, OLDER = false, ANY = false;
function renderEvents(events, any) {
  flushStepBuf();
  for (const ev of events) {
    const p = {...(ev.payload || {})};
    if (p.role === 'user' && typeof p.text === 'string') p.text = p.text.replace(/\n\n\[Web console language preference: Reply in English unless I explicitly request another language\.\]$/, '');
    if (ev.kind === 'message') {
      flushStepBuf();
      if (p.role === 'user') userBubble(p.text, p.files, ev.id, null, ev.at);
      else if (!any) continue;
      else if (p.turn && window.HoolaStream) { replyMessage(p, true, ev.id, ev.at); if (SINK === col) LAST_TURN = p.turn; }
      else hoolaText(p.text || '', p.source, ev.id, ev.at);
    }
    else if (ev.kind === 'step') continue;   // v0.171 the transcript keeps what each turn did (steps=1)
    else { flushStepBuf(); renderCard(ev.kind, p, ev.at); }
  }
  flushStepBuf();
}
async function openConv(id, fresh, opts = {}) {
  if (!CH) stopStream();
  LOADING = true; PENDING = [];
  closeFind();                          // v0.178 find results belong to their chat, like receipts
  RESULTS?.reset(); clearSimpleProgress();
  if (CONV && CONV !== id) { if (msg.value.trim()) store.set('hoola.draft.' + CONV, msg.value); else store.del('hoola.draft.' + CONV); }
  clearTimeout(DRAFT_T);
  if (CONV !== id) { FILES = []; drawFiles(); }
  CONV = id; col.innerHTML = ''; CARDS.clear(); B?.reset(); TURN = null; TYPING = null; USER_ECHO = []; $('#stopBtn').hidden = true;
  REPLIES.forEach(R => R.segs.forEach(S => S.pacer.reset())); REPLIES.clear(); LAST_TURN = null; STICK = true;
  RCPTS.clear();   // v0.173 receipts belong to their chat
  for (const K of THINKS.values()) clearInterval(K.timer);   // v0.171 the old chat's Soch timers stop with it
  THINKS.clear(); STEPS_ARGS.clear(); STEPS_DATA.clear();
  $$('#recents .rc').forEach(b => b.toggleAttribute('aria-current', b.dataset.conv === id));
  if (CH) {   // every chat has its own link; reload / back / a new tab open the same chat
    const url = '/console/c/' + encodeURIComponent(id);
    if (!opts.noPush && location.pathname !== url) history.pushState({conv: id}, '', url);
    CH.draw();
  }
  if (VIEW === 'chat') $('#ttl').textContent = chatFolder();
  slashClose();
  msg.value = store.get('hoola.draft.' + id) || '';   // v0.173 her unfinished words come back with the chat
  msg.style.height = 'auto'; msg.style.height = Math.min(200, msg.scrollHeight) + 'px';
  $('#sendBtn').disabled = !msg.value.trim() && !FILES.length;
  // skeleton rows while the chat loads (not a spinner)
  col.innerHTML = '<div class="skel-chat" aria-hidden="true"><i class="skel r"></i><i class="skel l"></i><i class="skel l s"></i><i class="skel r s"></i><i class="skel l"></i></div>';
  // the chat in order from the server: messages and each card once where it happened (latest state)
  let tl = {events: [], last_event_id: 0};
  try { tl = await api('GET', `/api/conversations/${encodeURIComponent(id)}/timeline?limit=${fresh ? 10 : 80}&steps=1`); }
  catch (e) { LOADING = false; col.innerHTML = ''; if (e.status === 404 && opts.fallback) return opts.fallback(); toast(e.message, true); }
  if (CONV !== id) return;
  col.innerHTML = '';
  const any = tl.events.some(e => e.kind === 'message')
    || (!fresh && !!B && tl.events.some(e => B.kinds.has(e.kind)));           // a chat with a build in it opens on the thread
  ANY = any; landing(!any);
  renderEvents(tl.events, any);
  REPLIES.forEach(R => { drawActs(R); closeTurnTools(R.t); });
  BEFORE = tl.before || 0; HAS_MORE = !!tl.has_more; drawBranches(tl.branches || []);
  TURN = null; LAST = tl.last_event_id || 0;
  if (CH?.isBusy(id)) typing(true);          // that chat is working: Stop shows, the dots wait for its words
  // a reply still being written (she reloaded mid-reply): its words so far, then the stream goes on from there
  if (CONFIG.stream && window.HoolaStream) {
    try {
      const r = await api('GET', `/api/conversations/${encodeURIComponent(id)}/live`, undefined, {raw: true});
      if (r.status === 200 && CONV === id) {
        const s = await r.json(), R = reply(s.turn);
        R.done = false; R.acts?.remove(); R.seq = s.seq; LAST_TURN = s.turn; landing(false);
        if (s.think) thinkEvent({turn: s.turn, seg: s.seg, text: s.think});   // v0.171 mid-thought reload: the card reopens
        const S = seg(R, s.seg); S.pacer.reset(); S.pacer.push(s.text || ''); S.pacer.flush();
        TURN = R.t; $('#stopBtn').hidden = false; live('run');
      }
    } catch {}
  }
  scrollDown(true);
  drawRail();                            // v0.178 the day rail rebuilds with the chat
  if (!CH) { LOADING = false; stream(id); return; }
  // the account stream never stopped: events of this chat that arrived while it loaded, without duplicates
  LOADING = false;
  const held = PENDING; PENDING = [];
  for (const ev of held) if (ev.live || ev.id > LAST) onEvent(ev);
}

/* ================= older messages, jumping to a message, branch arrows ================= */
async function loadOlder() {
  if (OLDER || !HAS_MORE || !BEFORE || !CONV) return false;
  OLDER = true; const id = CONV;
  try {
    const tl = await api('GET', `/api/conversations/${encodeURIComponent(id)}/timeline?limit=60&before=${BEFORE}&steps=1`);
    if (CONV !== id) return false;
    const box = document.createElement('div'), saveTurn = TURN, saveLast = LAST_TURN;
    SINK = box; TURN = null;
    try { renderEvents(tl.events, true); } finally { SINK = col; TURN = saveTurn; LAST_TURN = saveLast; }
    const fromBottom = thread.scrollHeight - thread.scrollTop;          // keep her place (no browser scroll anchoring)
    col.prepend(...box.children);
    thread.scrollTop = thread.scrollHeight - fromBottom;
    REPLIES.forEach(R => { if (!R.acts) { R.done = true; drawActs(R); closeTurnTools(R.t); } });
    BEFORE = tl.before || 0; HAS_MORE = !!tl.has_more && tl.events.length > 0;
    drawRail();                          // v0.178 older days join the rail
    return true;
  } catch (e) { toast(e.message, true); return false; }
  finally { OLDER = false; }
}
thread.addEventListener('scroll', () => { if (thread.scrollTop < 240 && HAS_MORE && !LOADING) loadOlder(); }, {passive: true});

async function jumpTo(conv, eventId) {
  go('chat');
  if (conv !== CONV) await openConv(conv); else if (!col.children.length) await openConv(conv, false, {noPush: true});
  if (!eventId) return;
  let el = null;
  for (let i = 0; i < 25 && CONV === conv; i++) {
    el = col.querySelector(`[data-eid="${eventId}"]`); if (el || !HAS_MORE) break;
    if (!(await loadOlder())) break;
  }
  if (!el) return toast('Woh message ab is chat mein nahi dikh raha (shayad doosre version mein hai).');
  STICK = false; el.scrollIntoView({block: 'center', behavior: 'smooth'});
  el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2200);
  drawRail();
}

function drawBranches(list) {
  for (const b of list) {
    const host = b.kind === 'edit' ? col.querySelector(`.mu[data-eid="${b.at}"]`)
      : col.querySelector(`.mu[data-eid="${b.anchor}"]`)?.nextElementSibling?.querySelector('.bd');
    if (!host) continue;
    host.querySelector(':scope > .barrows')?.remove();
    const n = b.active + 1, w = document.createElement('span'); w.className = 'barrows';
    w.innerHTML = `<button type="button" aria-label="Pichhla version" ${n <= 1 ? 'disabled' : ''} data-i="${b.active - 1}">‹</button>`
      + `<span aria-live="polite">${n}/${b.count}</span>`
      + `<button type="button" aria-label="Agla version" ${n >= b.count ? 'disabled' : ''} data-i="${b.active + 1}">›</button>`;
    w.addEventListener('click', async e => {
      const btn = e.target.closest('button[data-i]'); if (!btn || btn.disabled) return;
      try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/branch`, {group: b.id, index: +btn.dataset.i}); await openConv(CONV, false, {noPush: true}); }
      catch (er) { toast(er.message, true); }
    });
    if (b.kind === 'edit') host.appendChild(w); else host.insertBefore(w, host.querySelector('.racts'));
  }
}

/* ================= v0.178 search power in the thread: in-chat find (Ctrl+F) + the day jump rail ================= */
let FIND = null;   // {q, hits:[eventId], total, i, box, inp, st}
function openFind() {
  if (FIND) { FIND.inp.focus(); FIND.inp.select(); return; }
  if (!CONV || VIEW !== 'chat') return;
  const bar = document.createElement('div'); bar.className = 'fbar gl'; bar.setAttribute('role', 'search'); bar.setAttribute('aria-label', 'Is chat mein dhoondo');
  bar.innerHTML = `<span class="fic" aria-hidden="true">⌕</span><input placeholder="Is chat mein dhoondo…" aria-label="Is chat mein dhoondo" autocomplete="off"><span class="fcount" aria-live="polite"></span>`
    + `<button type="button" class="fb" data-d="-1" aria-label="Pichhla mila (Shift+Enter)">↑</button>`
    + `<button type="button" class="fb" data-d="1" aria-label="Agla mila (Enter)">↓</button>`
    + `<button type="button" class="fb x" aria-label="Close (Esc)">✕</button>`;
  $('#v-chat').appendChild(bar);
  const inp = bar.querySelector('input');
  FIND = {q: '', hits: [], total: 0, i: -1, box: bar, inp, st: 0};
  inp.focus();
  inp.addEventListener('input', () => { clearTimeout(FIND.st); FIND.st = setTimeout(() => findRun(inp.value), 240); });
  inp.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeFind(); }
    else if (e.key === 'Enter') { e.preventDefault(); findGo(e.shiftKey ? -1 : 1); }
  });
  bar.addEventListener('click', e => { const b = e.target.closest('.fb'); if (!b) return;
    if (b.classList.contains('x')) closeFind(); else findGo(+b.dataset.d); });
  highlightHits();
}
function closeFind() {
  if (!FIND) return;
  FIND.box.remove(); FIND = null;
  col.querySelectorAll('.fhit').forEach(x => x.classList.remove('fhit'));
}
function findRun(q) {
  if (!FIND) return;
  FIND.q = q; FIND.hits = []; FIND.total = 0; FIND.i = -1;
  FIND.box.querySelector('.fcount').textContent = '';
  col.querySelectorAll('.fhit').forEach(x => x.classList.remove('fhit'));
  q = q.trim();
  if (!q) return;
  api('GET', `/api/conversations/${encodeURIComponent(CONV)}/find?q=${encodeURIComponent(q)}`).then(r => {
    if (!FIND || FIND.q !== q) return;                    // she typed again while this was out
    FIND.hits = (r.matches || []).map(m => m.event_id).filter(Boolean);
    FIND.total = r.total || FIND.hits.length;
    if (FIND.total) findGo(1, true);
    else FIND.box.querySelector('.fcount').textContent = '0 mile';
    highlightHits();
  }).catch(() => { if (FIND) FIND.box.querySelector('.fcount').textContent = 'dikkat'; });
}
async function findGo(d, first) {
  if (!FIND || !FIND.hits.length) return;
  FIND.i = first ? 0 : (FIND.i + d + FIND.hits.length) % FIND.hits.length;
  FIND.box.querySelector('.fcount').textContent = `${FIND.i + 1}/${FIND.hits.length}${FIND.total > FIND.hits.length ? '+' : ''}`;
  await jumpTo(CONV, FIND.hits[FIND.i]);
}
function highlightHits() {   // loaded bubbles glow; older ones light up as the rail/pages bring them in
  if (!FIND || !FIND.q.trim()) return;
  const q = FIND.q.toLowerCase();
  col.querySelectorAll('.mu, .mh').forEach(el => {
    el.classList.toggle('fhit', (el.textContent || '').toLowerCase().includes(q));
  });
}

/* the rail: one slim line on the right edge, one tick per day of the loaded chat (Today / Yesterday / 12 Okt);
   hover says the day, one tap jumps to that day's first message. Only when it earns its place. */
let RAIL_T = 0;
function dayLabel(d) {
  const today = new Date(), start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate()), DAY = 86400000;
  if (day.getTime() === start.getTime()) return 'Today';
  if (day.getTime() === start.getTime() - DAY) return 'Yesterday';
  return d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'});
}
function drawRail() {
  clearTimeout(RAIL_T);
  RAIL_T = setTimeout(() => {
    const rail = $('#jrail');
    if (!rail) return;
    const msgs = [...col.querySelectorAll('[data-at]')];
    const land = !$('#landing').hidden;
    const tall = thread.scrollHeight > thread.clientHeight * 1.6;
    if (VIEW !== 'chat' || land || msgs.length < 6) { rail.hidden = true; return; }
    const base = thread.getBoundingClientRect().top, H = thread.scrollHeight;
    const days = new Map();     // dayKey -> {label, top, n}
    for (const el of msgs) {
      const d = new Date(el.dataset.at); if (isNaN(d)) continue;
      const key = d.toDateString();
      if (!days.has(key)) {
        const top = el.getBoundingClientRect().top - base + thread.scrollTop;
        days.set(key, {label: dayLabel(d), top, n: 0});
      }
      days.get(key).n++;
    }
    if (days.size < 2 && !tall) { rail.hidden = true; return; }
    rail.innerHTML = [...days.values()].map(g =>
      `<b role="button" tabindex="0" aria-label="${esc(g.label)} ke messages" data-top="${Math.round(g.top)}" style="top:${Math.max(2, Math.min(97, (g.top / H) * 100))}%"><span class="lbl">${esc(g.label)} · ${g.n}</span><i></i></b>`).join('');
    rail.hidden = false;
  }, 160);
}
$('#v-chat').insertAdjacentHTML('beforeend', '<div class="jrail" id="jrail" hidden aria-label="Din par jao"></div>');
$('#jrail').addEventListener('click', e => {
  const b = e.target.closest('b[data-top]'); if (!b) return;
  thread.scrollTo({top: +b.dataset.top - 76, behavior: 'smooth'}); STICK = false;
});
$('#jrail').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { const b = e.target.closest('b[data-top]'); if (b) { e.preventDefault(); thread.scrollTo({top: +b.dataset.top - 76, behavior: 'smooth'}); } } });
addEventListener('resize', drawRail);

/* ================= one stream for all her chats (CHAT_SESSIONS; on with CONSOLE_V2) ================= */
// kinds that belong to their own chat only (events.LOCAL_KINDS); every other card of another chat shows here too
const LOCAL = new Set(['typing', 'step', 'work', 'log', 'reply_start', 'delta', 'delta_reset', 'reply_end', 'think', 'say', 'message', 'upload',
  'reminders', 'routines', 'lists', 'email_sent', 'hoola_update', 'galla', 'mshop', 'office', 'employee', 'darzi_order',
  'phonedoc_open', 'phonedoc_check', 'device_action', 'device_action_result', 'home_device', 'bt_request', 'bazar_open',
  'bazar_link', 'gyaan_sources', 'memory_saved', 'procedure', 'open', 'link', 'call_receipt', 'speaker', 'voice',
  'biz_inbox', 'biz_appointment', 'propagent_listing', 'chai_order']);
let ACC = null, ACC_LAST = 0;
function accountStream() {
  ACC?.abort();
  const s = HoolaStream.open({url: '/api/console/stream', token: TOKEN, after: ACC_LAST, onState: setConn, onAuth: () => logout(true),
    onEvent: ev => {
      if (ACC !== s) return;
      if (ev.kind === 'resync') { ACC_LAST = 0; setTimeout(() => { accountStream(); if (CONV) openConv(CONV, false, {noPush: true}); }, 0); return; }
      if (!ev.live) ACC_LAST = Math.max(ACC_LAST, ev.id);
      const c = ev.conv;
      if (ev.kind === 'typing') { CH.busy(c, !!ev.payload?.on); if (!ev.payload?.on) setTimeout(() => CH.load(), 1500); }   // a new auto title
      if (c === CONV) { if (LOADING) PENDING.push(ev); else onEvent(ev); return; }
      if (ev.kind === 'message' && ev.payload?.role === 'assistant') CH.unread(c);
      if (!ev.live && !LOCAL.has(ev.kind) && !PROGRESS_POLICY.quiet(ev.kind,ev.payload) && !LOADING && CONV) onEvent(ev);
    }});
  ACC = s;
}
addEventListener('popstate', () => {
  const m = location.pathname.match(/^\/console\/c\/([^/?#]+)/);
  if (CH && m && decodeURIComponent(m[1]) !== CONV) { go('chat'); openConv(decodeURIComponent(m[1]), false, {noPush: true}); }
});

/* ================= sending ================= */
let FILES = [];   // {file_id, name}
let DRAFT_T = 0;
msg.addEventListener('input', () => { msg.style.height = 'auto'; msg.style.height = Math.min(200, msg.scrollHeight) + 'px'; $('#sendBtn').disabled = !msg.value.trim() && !FILES.length;
  const draftConv = CONV, draftText = msg.value;
  clearTimeout(DRAFT_T); DRAFT_T = setTimeout(() => {   // v0.173 every chat keeps her unfinished words
    if (draftConv) { if (draftText.trim()) store.set('hoola.draft.' + draftConv, draftText); else store.del('hoola.draft.' + draftConv); }
  }, 300);
  slashMaybe(); });
msg.addEventListener('keydown', e => {
  if (SLASH.open && ['ArrowUp', 'ArrowDown', 'Tab'].includes(e.key)) { e.preventDefault(); SLASH.nav(e.key === 'ArrowUp' ? -1 : 1, e.key === 'Tab'); return; }
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (SLASH.open && SLASH.pick()) return; composer.requestSubmit(); }
});

/* ================= slash commands (v0.172): "/" in the composer runs the console, English ================= */
const SLASH = {open: false, items: [], sel: 0};
const SLASH_CMDS = [
  ['nayi', 'Nayi chat', 'nayi kholo', () => $('#newChat').click()],
  ['dhoondo', 'Chats dhoondo', 'Ctrl K wala search', () => CH?.openSearch()],
  ['export', 'Chat export', 'Markdown ya JSON file', () => $('#exportBtn').click()],
  ['rok', 'Stop', 'chalta kaam rok do', () => $('#stopBtn').click()],
  ['aaj', 'Today', 'aaj ka din', () => go('aaj')],
  ['kaam', 'All tools', 'sab kuch jo Hoola karta hai', () => go('kaam')],
  ['baat', 'Baat', 'live voice call', () => go('baat')],
  ['main', 'Main', 'profile, password, kharcha', () => go('main')],
];
function slashMaybe() {
  const v = msg.value;
  const m = v.startsWith('/') && !v.slice(1).includes(' ');
  if (!m) { slashClose(); return; }
  const q = v.slice(1).toLowerCase();
  SLASH.items = SLASH_CMDS.filter(c => !q || c[0].startsWith(q) || c[1].toLowerCase().includes(q));
  const box = $('#slash');
  if (!SLASH.items.length) { slashClose(); return; }
  SLASH.open = true; SLASH.sel = 0;
  box.hidden = false;
  box.innerHTML = SLASH.items.map((c, i) => `<button type="button" role="option" aria-selected="${i === 0}" data-si="${i}"><b>/${esc(c[0])}</b><span>${esc(c[1])}</span><em>${esc(c[2])}</em></button>`).join('');
}
function slashClose() { SLASH.open = false; const b = $('#slash'); if (b) { b.hidden = true; b.innerHTML = ''; } }
SLASH.pick = () => {
  if (!SLASH.open || !SLASH.items.length) return false;
  SLASH.items[SLASH.sel][3]();
  msg.value = ''; msg.dispatchEvent(new Event('input')); slashClose();
  return true;
};
SLASH.nav = (d, tab) => {
  if (!SLASH.open) return;
  SLASH.sel = (SLASH.sel + d + SLASH.items.length) % SLASH.items.length;
  $$('#slash [data-si]').forEach(b => b.setAttribute('aria-selected', +b.dataset.si === SLASH.sel));
  if (tab) { const it = SLASH.items[SLASH.sel]; msg.value = '/' + it[0]; }   // Tab completes, does not run
  $$('#slash [data-si]')[SLASH.sel]?.scrollIntoView({block: 'nearest'});
};
document.addEventListener('click', e => { const b = e.target.closest('#slash [data-si]'); if (b) { SLASH.sel = +b.dataset.si; SLASH.pick(); } else if (!e.target.closest('#slash') && e.target !== msg) slashClose(); });

/* ================= kharcha gauge (v0.172): this month's AI spend as one thin line on the composer ================= */
let GAUGE_T = 0;
async function loadGauge() {
  try {
    const r = await api('GET', '/api/usage?days=1');
    const m = r.month || {};
    const g = $('#gauge');
    if (!m.limit_usd) { g.hidden = true; return; }   // no limit set: nothing to gauge
    g.hidden = false;
    g.className = 'gauge' + (m.over ? ' over' : m.warn ? ' warn' : '');
    g.querySelector('i').style.width = Math.max(1.5, Math.min(100, m.pct || 0)) + '%';
    g.title = `Is mahine ka AI kharcha: $${m.spent_usd.toFixed(2)} / $${m.limit_usd.toFixed(2)} (${Math.round(m.pct)}%)${m.over ? ' — seema paar' : ''}`;
  } catch {}
}
composer.addEventListener('submit', async e => {
  e.preventDefault(); const text = msg.value.trim(); if ((!text && !FILES.length) || !CONV) return;
  if (FILES.some(f => !f.file_id)) return toast('File upload in progress…');
  const origin = CONV, auth = TOKEN; clearTimeout(DRAFT_T);
  const files = FILES.splice(0); drawFiles(); msg.value = ''; msg.style.height = 'auto'; $('#sendBtn').disabled = true;
  store.del('hoola.draft.' + origin);   // v0.173 the draft went out with the message
  const body = {text: text || 'Ye file dekho', client_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())), files: files.map(f => f.file_id)};
  landing(false); const bbl = userBubble(body.text, files, null, body.client_id);
  if (TYPING) receipt(bbl, body.client_id, 'queue');   // v0.173 steering: she sees it is queued and can take it back
  USER_ECHO.push(body.text);
  for (let i = 0; i < 3; i++) {
    if (!auth || TOKEN !== auth) return;
    try { await api('POST', `/api/conversations/${encodeURIComponent(origin)}/messages`, body); loadRecents(); return; }
    catch (er) { if (i === 2 || er.status === 401 || er.status === 400) { toast('Could not send: ' + er.message, true); store.set('hoola.draft.' + origin, text); if (CONV === origin) { msg.value = text; FILES.push(...files); drawFiles(); } return; } await new Promise(r => setTimeout(r, 800 * (i + 1))); }
  }
});
$('#stopBtn').addEventListener('click', async () => { try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/stop`); toast('Rokne ko kaha. Jo kadam chal raha tha woh beech mein ruk sakta hai.'); } catch (e) { toast(e.message, true); } });
$('#attach').addEventListener('click', () => $('#fileIn').click());
$('#fileIn').addEventListener('change', e => { const picked = [...e.target.files]; e.target.value = ''; addFiles(picked); });
async function addFiles(list) {     // paperclip, drag and drop, pasted screenshots: one path
  const origin = CONV, target = FILES;
  if (!origin) return;
  const picked = list.slice(0, Math.max(0, 6 - target.length));
  if (list.length > picked.length) toast('Ek baar mein 6 files tak.');
  if (picked.length) msg.focus();
  for (const f of picked) {
    if (f.size > 25 * 1024 * 1024) { toast(`${f.name}: 25 MB se badi file nahi chalegi.`, true); continue; }
    const up = await shrink(f);   // v0.173 big pictures shrink here: upload fast, phone data saved
    if (up !== f) toast(`${f.name}: chhota kar diya (${Math.round(f.size / 1024)} KB → ${Math.round(up.size / 1024)} KB).`);
    if (CONV !== origin || FILES !== target) return;
    const item = {name: up.name, file_id: null}; target.push(item); drawFiles();
    try { const fd = new FormData(); fd.append('file', up, up.name); const r = await api('POST', `/api/conversations/${encodeURIComponent(origin)}/files`, undefined, {form: fd}); item.file_id = r.file_id; }
    catch (er) { if (target.includes(item)) target.splice(target.indexOf(item), 1); toast(`${up.name}: ${er.message}`, true); }
    drawFiles();
  }
}
async function shrink(f) {
  if (!f.type.startsWith('image/') || f.type === 'image/gif' || !window.createImageBitmap) return f;
  const img = await createImageBitmap(f).catch(() => null);
  if (!img || (img.width <= 1600 && img.height <= 1600)) return f;
  const k = 1600 / Math.max(img.width, img.height);
  const c = document.createElement('canvas');
  c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  const blob = await new Promise(r => c.toBlob(r, f.type === 'image/png' ? 'image/png' : 'image/jpeg', 0.9));
  if (!blob || blob.size >= f.size) return f;
  return new File([blob], f.name, {type: blob.type});
}
// drag and drop anywhere on the chat; a screenshot pasted into the composer
const chatView = $('#v-chat'); let dragN = 0;
chatView.addEventListener('dragenter', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); dragN++; chatView.classList.add('dropping'); } });
chatView.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) e.preventDefault(); });
chatView.addEventListener('dragleave', () => { if (--dragN <= 0) { dragN = 0; chatView.classList.remove('dropping'); } });
chatView.addEventListener('drop', e => { if (!e.dataTransfer?.files?.length) return; e.preventDefault(); dragN = 0; chatView.classList.remove('dropping'); landing(false); addFiles([...e.dataTransfer.files]); });
msg.addEventListener('paste', e => {
  const files = [...(e.clipboardData?.files || [])];
  if (!files.length) return;
  e.preventDefault();
  const stamp = new Date().toTimeString().slice(0, 8).replace(/:/g, '');
  addFiles(files.map((f, i) => f.name && f.name !== 'image.png' ? f : new File([f], `screenshot-${stamp}${i ? '-' + i : ''}.png`, {type: f.type || 'image/png'})));
});

/* v0.178 shortcuts: one registry (KEYS), one listener — the cheat sheet (?) always tells the truth.
   Ctrl+K search (chatlist.js), Ctrl+F in-chat find, Alt+↑/↓ chat hop, / composer, Ctrl+Shift+O new chat,
   ? this list, Esc the layered exit. Combos normalise so Ctrl+Shift+O and Ctrl+O stay one thing. */
const KEYS = [
  {k: 'Ctrl+F', g: 'Dhoondo', label: 'Is chat mein dhoondo', fn: () => { go('chat'); openFind(); }},
  {k: 'Ctrl+K', g: 'Dhoondo', label: 'Saari chats mein dhoondo', fn: () => CH?.openSearch()},
  {k: 'Alt+ArrowDown', g: 'Chat', label: 'Agli chat', fn: () => chatStep(1)},
  {k: 'Alt+ArrowUp', g: 'Chat', label: 'Pichhli chat', fn: () => chatStep(-1)},
  {k: 'Ctrl+Shift+O', g: 'Chat', label: 'Nayi chat', fn: () => $('#newChat').click()},
  {k: '/', g: 'Composer', label: 'Likhne ka box kholo', when: e => !typingIn(e), fn: () => { go('chat'); msg.focus(); }},
  {k: '?', g: 'Saamaany', label: 'Yahin shorcut list', when: e => !typingIn(e), fn: () => openKeys()},
  {k: 'Escape', g: 'Saamaany', label: 'Close · Stop', fn: escLayer},
];
const typingIn = e => !!(e.target && e.target.closest && e.target.closest('input, textarea, select, [contenteditable="true"], [contenteditable="plaintext-only"]'));
const normCombo = c => { const p = String(c).split('+'), key = p.pop(); const m = new Set(p.map(x => x.toLowerCase()));
  if (key.length === 1) m.delete('shift');                    // Ctrl+Shift+O == Ctrl+O (shift is how she types it)
  return [...m, key.toLowerCase()].join('+'); };
const comboOf = e => {
  if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return '';
  const k = e.key === ' ' ? 'Space' : e.key;
  const mods = [(e.ctrlKey || e.metaKey) ? 'ctrl' : '', e.altKey ? 'alt' : ''].filter(Boolean);
  return normCombo([...mods, k].join('+'));
};
const KEYMAP = KEYS.map(x => ({...x, c: normCombo(x.k)}));
document.addEventListener('keydown', e => {
  if (e.isComposing || $('#app').hidden) return;
  const c = comboOf(e); if (!c) return;
  const hit = KEYMAP.find(x => x.c === c && (!x.when || x.when(e)));
  if (hit) { e.preventDefault(); hit.fn(); }
});
function chatStep(d) {          // Alt+↑/↓: walk the sidebar's order without touching the mouse
  if (!CH) return;
  const ids = CH.ids ? CH.ids() : [];
  if (ids.length < 2) return;
  const i = ids.indexOf(CONV);
  openConv(ids[(i + d + ids.length) % ids.length]);
}
function escLayer() {           // one Esc peels one layer, deepest first
  if (FIND) { closeFind(); return; }
  const kb = document.querySelector('.kbg'); if (kb) { kb.remove(); return; }
  if (!$('#exportMenu').hidden) { $('#exportMenu').hidden = true; return; }
  if (SLASH.open) { slashClose(); return; }
  if (!$('#stopBtn').hidden) $('#stopBtn').click();
}
function openKeys() {           // the cheat sheet: toggle, glass, English
  const old = document.querySelector('.kbg');
  if (old) { old.remove(); return; }
  const groups = [];
  for (const x of KEYS) { let g = groups.find(([n]) => n === x.g); if (!g) { g = [x.g, []]; groups.push(g); } g[1].push(x); }
  const w = document.createElement('div'); w.className = 'kbg'; w.setAttribute('role', 'dialog'); w.setAttribute('aria-modal', 'true'); w.setAttribute('aria-label', 'Keyboard shortcuts');
  w.innerHTML = `<div class="kbox gl"><h3>Shorcut ke list</h3>
    ${groups.map(([g, xs]) => `<div class="kgrp"><b>${esc(g)}</b>${xs.map(x => `<div class="krow"><span>${esc(x.label)}</span><kbd>${esc(x.k)}</kbd></div>`).join('')}</div>`).join('')}
    <p class="faint">Composer mein "/" likhiye — /nayi /dhoondo /export jaise commands khud aa jaate hain. Ctrl+K search bhi hai.</p></div>`;
  document.body.appendChild(w);
  w.addEventListener('click', e => { if (e.target === w) w.remove(); });
}

/* ================= export (v0.171): this chat as a Markdown file to read, or JSON to keep ================= */
$('#exportBtn').addEventListener('click', () => { const m = $('#exportMenu'); m.hidden = !m.hidden; });
document.addEventListener('click', e => { if (!e.target.closest('#exportMenu, #exportBtn')) $('#exportMenu').hidden = true; });
$('#exportMenu').addEventListener('click', async e => {
  const b = e.target.closest('[data-fmt]'); if (!b || !CONV) return;
  $('#exportMenu').hidden = true;
  try {
    const r = await api('GET', `/api/conversations/${encodeURIComponent(CONV)}/export?fmt=${b.dataset.fmt}`, undefined, {raw: true});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(await r.blob());
    a.download = (r.headers.get('content-disposition') || '').match(/filename="?([^";]+)"?/)?.[1] || `hoola-chat.${b.dataset.fmt}`;
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast('Chat export ho gayi.');
  } catch (er) { toast('Export failed: ' + er.message, true); }
});
function drawFiles() {
  $('#files').innerHTML = FILES.map((f, i) => `<span class="fchip${f.file_id ? '' : ' up'}">📎 ${esc(f.name)}${f.file_id ? '' : ' · upload…'}<button type="button" data-rm="${i}" aria-label="Remove ${esc(f.name)}">✕</button></span>`).join('');
  $('#sendBtn').disabled = !msg.value.trim() && !FILES.length;
}
$('#files').addEventListener('click', e => { const b = e.target.closest('[data-rm]'); if (b) { FILES.splice(+b.dataset.rm, 1); drawFiles(); } });
$('#micBtn').title = 'Bolo karke likhiye (dictation)';
$('#toolsBtn').addEventListener('click', () => go('kaam'));

/* v0.173 dictation in the composer: mic button speaks hi-IN into the box (Chrome / Android); the live call
   stays on Baat. No speech recognition in this browser = the old jump to Baat, with a one-line why. */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let DICT = null;
$('#micBtn').addEventListener('click', () => {
  if (!SR) { go('baat'); return; }
  if (DICT) { DICT.stop(); return; }
  const r = new SR();
  r.lang = 'hi-IN'; r.interimResults = true; r.continuous = true;
  let base = msg.value ? msg.value.replace(/\s*$/, ' ') : '';
  DICT = r;
  $('#micBtn').classList.add('on');
  r.onresult = ev => {
    let fin = '', mid = '';
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      if (ev.results[i].isFinal) fin += ev.results[i][0].transcript; else mid += ev.results[i][0].transcript;
    }
    if (fin) { base += (base && !/\s$/.test(base) ? ' ' : '') + fin.trim(); }
    msg.value = base + (mid ? (base ? ' ' : '') + mid : '');
    msg.dispatchEvent(new Event('input')); scrollDown(true);
  };
  const stop = () => { DICT = null; $('#micBtn').classList.remove('on'); };
  r.onend = stop; r.onerror = ev => { stop(); if (ev.error === 'not-allowed') toast('Allow microphone access in your browser address bar.', true); };
  try { r.start(); toast('Speak to dictate. Click the microphone again to stop.'); } catch { stop(); go('baat'); }
});

/* ================= landing ideas + "All tools" (real prompts) ================= */
const KAAM = window.KAAM || [], KI = window.KAAM_ICON || {};
let CAT = null;
$('#cats').innerHTML = KAAM.map(g => `<button class="cat" type="button" data-cat="${g[0]}" aria-pressed="false"><span>${g[1]}</span>${esc(g[2])}</button>`).join('');
$('#cats').addEventListener('click', e => { const b = e.target.closest('.cat'); if (!b) return; CAT = CAT === b.dataset.cat ? null : b.dataset.cat;
  $$('.cat').forEach(x => x.setAttribute('aria-pressed', x.dataset.cat === CAT));
  const g = KAAM.find(x => x[0] === CAT); $('#sugs').innerHTML = g ? g[4].map((t, i) => `<button class="sug" type="button" data-say="${esc(t[0])}" style="animation-delay:${i * 30}ms"><span>${KI[t[0]] || '↗'}</span>${esc(t[3])}<em>${esc(t[1])}</em></button>`).join('') : ''; });
function usePrompt(id) {
  const t = KAAM.flatMap(g => g[4]).find(x => x[0] === id); if (!t) return;
  go('chat'); msg.value = t[3].replace(/^\[[^\]]+\]\s*/, ''); msg.dispatchEvent(new Event('input'));
  if (t[4]) { toast(`First file jodiye (${t[4]}), phir bhejiye.`); $('#fileIn').click(); } else composer.requestSubmit();
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
let QUEUE = [], PENDING_TIMER = 0;
async function refreshPending() {
  try { QUEUE = (await api('GET', '/api/console/pending')).pending || []; } catch { return; }
  $('#qcount').textContent = QUEUE.length;
  $('#queue').innerHTML = QUEUE.length ? '' : '<div class="empty">Nothing here yet.</div>';
  for (const q of QUEUE) {
    const holder = document.createElement('div'); $('#queue').appendChild(holder);
    const saveTurn = TURN; TURN = {bd: holder, steps: {}}; const k = q.kind + ':' + q.id; CARDS.delete(k);
    renderCard(q.kind, q.card || q); CARDS.delete(k); TURN = saveTurn;
  }
  if (!TYPING) live(QUEUE.length ? 'ask' : 'idle'); drawNav();
}

/* ================= Today ================= */
async function drawToday() {
  const box = $('#aaj'); box.innerHTML = '<div class="vh"><h2>Today</h2></div><div class="empty">Loading…</div>';
  let d = {reminders: [], lists: {}, pending: []}; try { d = await api('GET', '/api/console/today'); } catch (e) { box.innerHTML += `<p class="badc">${esc(e.message)}</p>`; return; }
  const date = new Date().toLocaleDateString('en-IN', {weekday: 'long', day: 'numeric', month: 'long'});
  box.innerHTML = `<div class="vh"><h2>Today · ${esc(date)}</h2></div>
    <div class="kpis"><div class="kpi gl"><b>${d.pending.length}</b><span>aapki Haan ka intezaar</span></div><div class="kpi gl"><b>${d.reminders.length}</b><span>aane wale reminders</span></div>
    <div class="kpi gl"><b>${Object.values(d.lists).reduce((n, l) => n + l.length, 0)}</b><span>list mein cheezein</span></div><div class="kpi gl"><b class="hid">${esc(ME?.handle || '')}</b><span>aapka Hoola ID</span></div></div>
    <div class="grid2">
      <div class="tile gl"><h3>Reminders</h3>${d.reminders.length ? `<div class="ag">${d.reminders.map(r => `<div><time>${esc(timeOf(r.due_at))}</time><span>${esc(r.text)}</span></div>`).join('')}</div>` : '<div class="empty">No reminders.</div>'}</div>
      <div class="tile gl"><h3>Lists</h3>${Object.keys(d.lists).length ? Object.entries(d.lists).map(([n, items]) => `<b style="font-size:13px" class="acc">${esc(n)}</b><div class="lst">${items.map(i => `<label><input type="checkbox" disabled> ${esc(i.text)}</label>`).join('')}</div>`).join('') : '<div class="empty">Koi list nahi. Chat mein kahiye: "doodh shopping list mein daalo".</div>'}</div>
      <div class="tile gl"><h3>Your approval is required <span class="tag warn">${d.pending.length}</span></h3>${d.pending.length ? d.pending.map(q => `<div class="ln"><span>${esc(q.title)}</span><b>${q.money ? '📱 phone' : 'console'}</b></div>`).join('') + '<button class="btn soft" type="button" id="toQueue">Open cards</button>' : '<div class="empty">Nothing yet.</div>'}</div>
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
        <form class="pwbox" id="pwf" autocomplete="off">${m.has_password ? '<input type="password" id="pwc" placeholder="Current password" autocomplete="current-password" aria-label="Current password">' : ''}
          <input type="password" id="pwn" placeholder="New password (10+ characters)" autocomplete="new-password" aria-label="New password" minlength="10">
          <input type="password" id="pwn2" placeholder="Confirm new password" autocomplete="new-password" aria-label="Repeat new password">
          <button class="btn go" type="submit">${m.has_password ? 'Password badlo' : 'Password banao'}</button></form></div>
      <div class="tile gl"><h3>Google apps <span class="tag ${gOn(m) ? 'ok' : 'warn'}">${gOn(m) ? 'jude hain' : 'jode nahi'}</span></h3>
        <p class="muted" style="font-size:13.5px">Login sirf naam aur email leta hai. Gmail, Calendar, Drive, Docs aur Sheets par kaam ke liye Google se alag se ijazat dijiye.</p>
        <div class="feat">${['gmail', 'calendar', 'drive', 'docs', 'sheets'].map(k => `<span class="chip">${(m.google_apps || {})[k] ? '✓' : '○'} ${k[0].toUpperCase() + k.slice(1)}</span>`).join('')}</div>
        <div class="acts" style="margin-top:12px"><button class="btn ${gOn(m) ? 'soft' : 'go'}" type="button" id="gAppsBtn">${gOn(m) ? 'Dobara jodiye' : 'Google apps jodiye'}</button></div></div>
      <div class="tile gl"><h3>Yaad <span class="tag v" id="memc">…</span></h3><div class="mfacts" id="mfacts"><div class="empty">Loading…</div></div></div>
      <div class="tile gl"><h3>Server</h3><div class="feat" id="feat"><span class="empty">…</span></div></div>
    </div>
    <div class="acts" style="margin-top:22px"><button class="btn soft" type="button" id="logoutBtn">Logout</button>
      ${CONFIG.v2 ? '<a class="btn soft" href="/console/?legacy=1" style="text-decoration:none">Legacy console</a>' : ''}</div>`;
  $('#logoutBtn').addEventListener('click', () => logout(false));
  $('#gAppsBtn').addEventListener('click', () => { if (!CONFIG.google) return toast('Google sign-in is not configured.', true); location.href = '/auth/google/start?web=1&apps=1'; });
  $('#pwf').addEventListener('submit', async e => { e.preventDefault(); const n = $('#pwn').value, n2 = $('#pwn2').value;
    if (n !== n2) return toast('The new passwords do not match.', true);
    try { const r = await api('PUT', '/api/console/password', {password: n, current: $('#pwc')?.value || ''}); ME.has_password = true; toast(`Password set. Ab ${r.handle} + password se login ho sakta hai.`); drawMain(); } catch (er) { toast(er.message, true); } });
  api('GET', '/api/memory').then(r => { const f = r.facts || []; $('#memc').textContent = f.length; $('#mfacts').innerHTML = f.slice(0, 40).map(x => `<div>${x.pinned ? '📌 ' : ''}${esc(x.text)}</div>`).join('') || '<div class="empty">No memories yet.</div>'; }).catch(() => { $('#mfacts').innerHTML = '<div class="empty">—</div>'; });
  fetch('/healthz').then(r => r.json()).then(h => { $('#feat').innerHTML = `<span class="chip">v${esc(h.version)}</span>` + (h.features || []).slice(0, 60).map(f => `<span class="chip">${esc(f.replace(/_/g, ' '))}</span>`).join(''); }).catch(() => {});
}

/* ================= Baat: live voice in the browser ================= */
let CALL = null;
function drawBaat() {
  const v = $('#v-baat');
  if (v.dataset.drawn) return; v.dataset.drawn = '1';
  v.innerHTML = `<div class="call"><div class="callav"><span class="av"><img src="${$('#uimg').src}" alt=""></span></div>
    <div><h2 style="font-size:26px">${esc(AV)}</h2><div class="callst okc" id="cst">Click to start a call</div><div class="faint" style="font-size:12.5px">Use headphones for clearer audio · English</div></div>
    <div class="wave" id="cwave" aria-hidden="true" style="opacity:.3">${Array.from({length: 13}, (_, i) => `<i style="animation-delay:${(i * .09) % 1}s"></i>`).join('')}</div>
    <div class="caption" aria-live="polite" id="caption"></div>
    <div class="cbtns" id="cbtns"><button class="btn go callgo" type="button" id="callBtn">📞 Start call</button></div></div>`;
  $('#callBtn').addEventListener('click', startCall);
}
function callUI(state, text) {
  const s = $('#cst'); if (s) s.textContent = text; const w = $('#cwave'); if (w) w.style.opacity = state === 'live' ? 1 : .3;
  const b = $('#cbtns'); if (!b) return;
  if (state === 'idle') { b.innerHTML = '<button class="btn go callgo" type="button" id="callBtn">📞 Start call</button>'; $('#callBtn').addEventListener('click', startCall); }
  else if (!$('#hang')) { b.innerHTML = `<button class="cbx" type="button" id="muteBtn" aria-label="Mute">${svg(IC.baat)}</button><button class="cbx end" type="button" id="hang" aria-label="Hang up">${svg('<path d="M3 15c5-4 13-4 18 0l-2 3-4-1v-3c-2-.6-4-.6-6 0v3l-4 1z"/>')}</button>`;
    $('#hang').addEventListener('click', () => endCall(true)); $('#muteBtn').addEventListener('click', toggleMute); }
}
async function startCall() {
  if (CALL) return;
  let media;
  try { media = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1}}); }
  catch { return callUI('idle', 'Allow microphone access in your browser address bar.'); }
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const q = new URLSearchParams({conv: CONV, voice: ME?.avatar?.voice || '', lang: 'en-IN'});
  let ws; try { ws = new WebSocket(`${proto}//${location.host}/api/voice/ws?${q}`, ['hoola', 'hoola-key.' + TOKEN]); } catch { media.getTracks().forEach(t => t.stop()); ctx.close(); return callUI('idle', 'Could not start the call.'); }
  ws.binaryType = 'arraybuffer';
  CALL = {ws, ctx, media, muted: false, playAt: 0, sources: new Set(), ping: null};
  callUI('connecting', 'Connecting…');
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
    if (m.type === 'ready') { callUI('live', 'Live · speak now'); CALL.ping = setInterval(() => ws.readyState === 1 && ws.send('{"type":"ping"}'), 15000); }
    else if (m.type === 'user_text') caption('Aap', m.text);
    else if (m.type === 'santosh_text') caption(AV, m.text);
    else if (m.type === 'interrupted') cutSpeech();
    else if (m.type === 'tool') callUI('live', (m.state === 'done' ? '✓ ' : '… ') + (m.label || 'kaam'));
    else if (m.type === 'status') callUI('live', m.state === 'reconnecting' ? 'Reconnecting…' : 'Live');
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
