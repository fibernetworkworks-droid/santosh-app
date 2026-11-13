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
// v0.222 what the console adds to her words for Hoola (language, deep research, Hoola PC) never shows in her bubble
const stripHints = t => t.replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
async function api(method, path, body, {raw = false, form = null, signal} = {}) {
  const headers = {};
  if (TOKEN) headers.Authorization = 'Bearer ' + TOKEN;
  let payload;
  if (method === 'POST' && /\/conversations\/[^/]+\/(messages|edit)$/.test(path) && body && typeof body.text === 'string') {
    const hints = (body.hints || []).map(h => '\n\n[Web console ' + h + ']').join('');
    body = {...body, text: body.text + hints + '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]'};
    delete body.hints;
  }
  if (form) payload = form; else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const r = await fetch(path, {method, headers, body: payload, signal, credentials: 'omit', cache: 'no-store'});
  if (raw) { if (!r.ok) throw new ApiError(r.status, await r.text()); return r; }
  let data = null; try { data = await r.json(); } catch {}
  if (!r.ok) {
    // v0.310 a 422 lists the field it did not like: say which and why ("seconds: must be 6 or more"), never a bare code
    const bad = data && Array.isArray(data.detail) && data.detail[0];
    const why = bad ? `${(bad.loc || []).filter(x => x !== 'body').join(' ') || 'value'}: ${String(bad.msg || '').replace(/^Input should be /, 'must be ').replace(/^Value error, /, '')}` : '';
    const msg = (data && (data.detail?.message || (typeof data.detail === 'string' ? data.detail : '') || why || data.message)) || `The server refused the request (${r.status})`;
    if (r.status === 401 && path !== '/api/console/login' && path !== '/api/console/exchange') logout(true);
    throw new ApiError(r.status, msg);
  }
  return data;
}
function toast(msg, bad) { const t = $('#toast'); t.textContent = msg; t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false; clearTimeout(toast._t); toast._t = setTimeout(() => t.hidden = true, 4200); }

/* ================= login ================= */
let CONFIG = {google: false, v2: true};
/* v0.743 SAAF INSAANI (owner: "DO NOT CHANGE EXISTING DESIGN BUT MAKE IT MORE USER FRIENDLY AND HUMAN MADE" -> GO on the
   canvas): same layout, colours and fonts; the screens talk like a person - her name + what happened on the home, the
   real step and time on work cards, "1 needs you" in the sidebar, plain spend, Ask again / Good answer / Not right,
   "Slide to approve / Not now", one-colour start icons, no emoji headings. Switch console_human (server) -> CONFIG.human. */
let HUMAN = false;
const HOUR_WORD = h => h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
function soFar(iso) {   // "6 min so far" from a server time
  const t = Date.parse(iso || ''); if (!t) return '';
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  return m < 1 ? 'just started' : m < 60 ? m + ' min so far' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min so far';
}
function humanTagline() {   // one plain sentence: what is waiting, what is running, else ready
  if (!HUMAN) return; const el = document.querySelector('.tagline'); if (!el) return;
  const w = QUEUE.length, r = JOBS.filter(j => j.state === 'working').length;
  const n = (k, one, many) => k === 1 ? one : k + ' ' + many;
  el.innerHTML = w ? `${esc(AV)} has ${n(w, 'one thing', 'things')} waiting for your OK. <button type="button" class="tlink" data-v="aaj">Review →</button>`
    : r ? `${esc(AV)} is working on ${n(r, 'one job', 'jobs')} for you right now.`
    : `${esc(AV)} is ready. Say what you need done, in your own words.`;
}
function showLogin(err) {
  $('#app').hidden = true; $('#login').hidden = false; if (err) { $('#lerr').textContent = err; $('#lerr').hidden = false; }
  $('#gbtn').disabled = false;
}
async function boot() {
  try { CONFIG = await api('GET', '/api/console/config'); } catch {}
  HUMAN = !!CONFIG.human; document.documentElement.classList.toggle('human', HUMAN);   // v0.743 SAAF INSAANI
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
  WORKSPACE?.reset(); CREATE?.reset(); PN?.reset(); clearSimpleProgress();
  clearTimeout(DRAFT_T); FILES = []; CONV = null; ACC_LAST = 0; msg.value = ''; drawFiles();
  clearInterval(GAUGE_T); clearInterval(PENDING_TIMER); clearInterval(JOBS_T); JOBS = [];
  if (TOKEN && !expired) { try { await api('POST', '/api/logout'); } catch {} }
  setToken(''); showLogin(expired ? 'Your session expired. Please sign in again.' : '');
}

/* ================= state + shell ================= */
let ME = null, CONV = null, VIEW = 'chat', AV = 'Santosh';
let CREATE = null;      // v0.259 the Create Studio (studio.js): the Create button lands on it, OpenArt-style
/* v0.222 R2: the sidebar is Claude-style - New chat + Search on top, then the places; Chat is the brand mark (home),
   Account is the user card at the bottom. The phone tabbar keeps its own five. */
const SMOOTH = () => matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';   // v0.226 R6: no smooth scroll under reduced motion
const NAV = [['computer','Hoola Computer'],['creative','Create'],['webdev','Web Development'],['appdev','App Development'],['gamedev','Game Dev'],['aaj','Today'],['kaam','Tools'],['connectors','Connectors'],['baat','Voice call']];   // v0.774 Connectors (was phone-only)   // v0.456 her ask: no Lab / Systems rows
// (was ['lab','Lab'] since v0.415): Prayogshala opens from the Education Desk's Lab tab, Systems from an Enterprise
// employee's Open desk - both views (#v-lab, #v-systems) and go('lab' | 'systems', arg) stay as they were.
IC.creative = '<path d="M12 3l2.4 5.6L20 11l-5.6 2.4L12 19l-2.4-5.6L4 11l5.6-2.4z"/>';
IC.bana = '<path d="M4 5h16v14H4zM4 10h16M10 10v9"/>';
IC.arena = '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3"/>';   // v0.312 Design Arena (owner only)
let AR = null;         // v0.312 the Arena screen (arena.js)
IC.systems = '<path d="M4 7h16M4 12h16M4 17h16M7 4v16"/>';   // v0.396 CONNECT: her own ERP / CRM systems
IC.hire = '<path d="M14 20v-1.5a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20M8 10.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M18 2.5l1.1 2.4 2.4 1.1-2.4 1.1L18 9.5l-1.1-2.4L14.5 6l2.4-1.1z"/>';   // v0.443 AI Employees (person + spark)
IC.skills = '<path d="M4 19.5V6a2 2 0 0 1 2-2h6v16H6a2 2 0 0 0-2 1.5zM12 4h6a2 2 0 0 1 2 2v13.5M12 4v16M8 8h1M8 12h1M15 8h1M15 12h1"/>';   // v0.481 the Skill Desk (an open book)
IC.seodesk = '<path d="M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.35-4.35M8 11h6M11 8v6"/>';                     // v0.317 SEO Desk
IC.caddesk = '<path d="M12 2l9 5v10l-9 5-9-5V7l9-5zM3 7l9 5 9-5M12 12v10"/>';   // v0.357 CAD Desk
IC.archdesk = '<path d="M3 21h18M5 21V10l7-6 7 6v11M9 21v-6h6v6M9 13h.01M15 13h.01"/>';   // v0.410 Architecture Desk
IC.gamedesk = '<path d="M6 12h4M8 10v4M15 13h.01M18 11h.01M17.3 5H6.7A4.7 4.7 0 0 0 2 9.7v4.1A3.2 3.2 0 0 0 5.2 17c1 0 2-.5 2.6-1.4L9 14h6l1.2 1.6c.6.9 1.6 1.4 2.6 1.4a3.2 3.2 0 0 0 3.2-3.2V9.7A4.7 4.7 0 0 0 17.3 5z"/>';   // v0.370 Game Desk
IC.socialdesk = '<path d="M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>';   // v0.353 Social Desk
let EMP = null;
let SKH = null;         // v0.718 the HOOLA AI Video Learner (seekh.js) - opens from the AI Employees hub
let HVO = null;         // v0.787 HOOLA VOCAL (vocal.js) - the voice studio, its own full page
let HIV = null;         // v0.747 HOOLA INTERACTIVE (interactive.js) - the video studio, its own sidebar row
let HCD = null;         // v0.748 HOOLA CODE (code.js) - Developer Sahayak as a console page
let IMP = null, IMP_BACK = null, IMP_DONE = '';   // HOOLA PROMPTING: the Improve sheet (improve.js); her original text for Undo
IC.prompting = '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>';
let FLW = null;         // v0.751 HOOLA FLOW (flow.js) - the Kaan pack as a console page
let FLOW_TEXT = '';   // v0.777 text from the Hoola Flow page waiting for the chat box
let FMIC = null;        // v0.751 the chat box mic through Kaan (flow.js HoolaFlowMic)
IC.code = '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 5l-3 14"/>';
IC.flow = '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8"/>';   // v0.751 HOOLA FLOW
IC.vocal = '<path d="M4 10v4M8 6v12M12 3v18M16 7v10M20 10v4"/>';   // v0.787 HOOLA VOCAL: a sound wave
IC.interactive = '<rect x="3" y="4" width="18" height="13" rx="2.5"/><circle cx="9" cy="10" r="2.2"/><path d="M5.8 15.2c.7-1.6 1.9-2.4 3.2-2.4s2.5.8 3.2 2.4"/><path d="M15 8.5l3 1.8-3 1.8z" fill="currentColor" stroke="none"/><path d="M8 20h8"/>';
IC.seekh = '<path d="M2 5.5a2 2 0 0 1 2-2h9l2.5 2.5H20a2 2 0 0 1 2 2V16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z"/><path d="M10 9.5l4 2.5-4 2.5z" fill="currentColor" stroke="none"/>';   // v0.718 a video folder with a play
let SK = null;         // v0.481 the Skill Desk (account menu > Skills)
let CX = null;         // v0.774 the Connectors page (connectors.js): Composio apps, MCP servers, plugins, public APIs, limits
IC.connectors = '<path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 0 1-10 0zM12 16v5"/>';   // v0.774 a plug
let FD = null;         // v0.565 the Film Desk (filmdesk.js)
IC.design = '<rect x="3" y="3" width="11" height="11" rx="2.5"/><circle cx="15.5" cy="15.5" r="5.5"/><path d="M3 20.5l3.2-.8 1.2-1.2-2.4-2.4-1.2 1.2z"/>';   // v0.777 Hoola Design (a square, a circle, a pen tip)
let BAHI = null;       // v0.807 BAHI: the GST & Accounts desk (bahi.js)
let DDK = null;        // v0.799 DESK ROOM (built as 0.796): the department desks (deptdesk.js) - Finance, Retail, Health Insurance, Construction
let AIA = null;        // v0.772 HOOLA AI APPS (aiapps.js): AIs that answer her customers
IC.aiapps = '<rect x="3" y="4" width="18" height="13" rx="3"/><path d="M8 21l2.5-4M7.5 9.5h.01M12 9.5h.01M16.5 9.5h.01M8 13c1.2 1 2.5 1.4 4 1.4s2.8-.4 4-1.4"/>';   // a chat bubble with a face
IC.appdev = '<rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10.5 18.5h3M9.5 9l-2 2 2 2M14.5 9l2 2-2 2"/>';   // v0.693 App Development (phone + code)
IC.gamedev = '<rect x="2.5" y="7" width="19" height="11" rx="5"/><path d="M7.5 10.5v4M5.5 12.5h4"/><circle cx="16" cy="11.5" r="1"/><circle cx="18" cy="13.8" r="1"/>';   // v0.783 Hoola Game Dev (a game controller)
IC.computer = '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>';   // v0.890 Hoola Computer
IC.webdev = '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M9 14l-2 2 2 2M15 14l2 2-2 2"/>';   // v0.635 Web Development
let ENT = null;        // v0.317 the Employee Hub + desks (employees.js)
const EDU_KEYS = ['tutor', 'school_office', 'curriculum', 'research', 'school_register', 'lab'];   // v0.453 any of them opens the Education Desk
function syncEmployees(hired) {                     // v0.317 desks exist only while their employee is hired
  // v0.456 her ask: NO desk rows in the sidebar ("REMOVE THIS FROM SIDE BAR" - Education / Social / SEO Desk). Every desk
  // opens from AI Employees > Open desk; the sidebar keeps only the AI Employees entry. A desk that is open when its
  // employee is let go still falls back to the hub.
  if (ME) ME.employees = hired || {};
  for (const [key, view] of [['seo', 'seodesk', 'SEO Desk'], ['social', 'socialdesk', 'Social Desk'], ['cad', 'caddesk', 'CAD Desk'], ['game_dev', 'gamedesk', 'Game Desk'], ['architect', 'archdesk', 'Architecture Desk'], ['edu', 'edudesk', 'Education Desk'], ['film', 'filmdesk', 'Film Desk'], ['leads', 'leadsdesk', 'Leads Desk']]) {
    const want = !!(hired && (hired[key] || (key === 'edu' && EDU_KEYS.some(k => hired[k])) || (key === 'game_dev' && (hired.procgen_dev || hired.physics_dev || hired.audio_dev || hired.haptics_dev || hired.netcode_dev || hired.xr_dev || hired.sim_dev || hired.twin_arch || hired.vfx_td))));   // v0.420 any Game Desk role opens the Game Desk
    if (!want && VIEW === view) go('hire');
  }
  const before = NAV.length;
  for (let i = NAV.length - 1; i >= 0; i--) if (/desk$/.test(NAV[i][0])) NAV.splice(i, 1);   // never a desk row
  if (NAV.length !== before) drawNav();
}
IC.edudesk = '<path d="M12 6c-2.5-1.4-5.5-1.6-9-1v13c3.5-.6 6.5-.4 9 1 2.5-1.4 5.5-1.6 9-1V5c-3.5-.6-6.5-.4-9 1zM12 6v13"/>';   // v0.453 Education Desk
IC.lab = '<path d="M9 3h6M10 3v6L4.5 18.5A2 2 0 0 0 6.2 21.5h11.6a2 2 0 0 0 1.7-3L14 9V3M7 15h10"/>';   // Prayogshala
IC.call = '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/>';
let JOBS = [];          // v0.222 her live jobs (working / waiting) for the home row and the Today badge
function navBadge(k) {
  if (k !== 'aaj') return '';
  if (HUMAN) {   // v0.743 words, not bare numbers
    const r = JOBS.filter(j => j.state === 'working').length;
    return (QUEUE.length ? `<span class="ct hx txt" title="Waiting for your approval">${QUEUE.length} need${QUEUE.length === 1 ? 's' : ''} you</span>`
      : r ? `<span class="lv txt" title="${r} running now"><i></i>${r} working</span>` : '');
  }
  const live = JOBS.length ? `<span class="lv txt" title="${JOBS.length} running now"><i></i>${JOBS.length}</span>` : '';
  return live + (QUEUE.length ? `<span class="ct txt" title="Waiting for your approval">${QUEUE.length}</span>` : '');
}
function drawNav() {
  $('#snav').innerHTML = NAV.map(([k, n]) => `<button class="sn" data-v="${k}" aria-current="${k === VIEW || (k === 'hire' && /desk$/.test(VIEW))}">${svg(IC[k === 'baat' ? 'call' : k])}<span class="txt">${n}</span>${navBadge(k)}</button>`).join('');
  const T = [['chat','Chat'],['aaj','Today'],['baat',''],['kaam','Tools'],['main','Account']];
  $('#tabbar').innerHTML = T.map(([k, n]) => k === 'baat' ? `<div class="mid"><button class="baat" data-v="baat" aria-label="Voice call">${svg(IC.baat).replace('currentColor', '#1B1030')}</button></div>`
    : `<button class="sn" data-v="${k}" aria-current="${k === VIEW}">${svg(IC[k])}<span>${n}</span></button>`).join('');
}
function go(v, arg) {
  if (v === 'creative' && CREATE) { CREATE.open(); return; }    // v0.259 Create = the full-screen Create Studio
  if (v === 'gamedev') { location.assign('/console/games' + (arg ? '#/game/' + encodeURIComponent(arg) : '')); return; }   // v0.783 Hoola Game Dev = its own app
  if (v === 'appdev') { location.assign('/console/apps' + (arg ? '#/app/' + encodeURIComponent(arg) : '')); return; }   // v0.693 App Studio = its own app
  if (v === 'prompting') { location.assign('/console/prompting'); return; }   // HOOLA PROMPTING = its own page
  if (v === 'flow') { location.assign('/console/flow' + (arg ? '#/t/' + encodeURIComponent(arg) : '')); return; }   // v0.777 Hoola Flow = its own page, like Wispr Flow
  if (v === 'code') { location.assign('/console/code' + (arg ? '#/s/' + encodeURIComponent(arg) : '')); return; }   // v0.768 Hoola Code = its own page with its own sidebar
  if (v === 'design') { location.assign('/console/design' + (arg ? '#/f/' + encodeURIComponent(arg) : '')); return; }   // v0.777 Hoola Design = its own app
  if (v === 'computer') { location.assign('/console/computer' + (arg ? '#/' + encodeURIComponent(arg) : '')); return; }   // v0.890 Hoola Computer = its own page
  if (v === 'webdev') { location.assign('/console/web' + (arg ? '#/site/' + encodeURIComponent(arg) : '')); return; }   // v0.649 Web Studio = its own app
  VIEW = v; $$('.view').forEach(x => x.hidden = x.id !== 'v-' + v);
  $('#ttl').textContent = {chat: chatFolder(), aaj:'· Today', kaam:'· All tools', baat:'· Baat', main:'· Main', bana:'· Creations', project:'· Folder', arena:'· Design Arena', lab:'· Prayogshala', hire:'· AI Employees', seekh:'· Video Learner', interactive:'· Hoola Interactive', code:'· Hoola Code', seodesk:'· SEO Desk', socialdesk:'· Social Desk', caddesk:'· CAD Desk', gamedesk:'· Game Desk', archdesk:'· Architecture Desk', edudesk:'· Education Desk', skills:'· Skills', connectors:'· Connectors', aiapps:'· AI Apps', filmdesk:'· Film Desk', leadsdesk:'· Leads Desk', deptdesk:'· Department desk', accountsdesk:'· GST & Accounts'}[v] || '';
  if (v !== 'project') PJ?.draw();
  drawNav(); $('#app').classList.remove('drawer');
  if (v === 'aaj') drawToday(); if (v === 'main') drawMain(); if (v === 'baat') drawBaat();
  if (v === 'bana') PN?.library($('#bana'));
  if (v === 'arena') AR?.draw($('#arena'));
  if (v === 'lab' && arg) $('#labframe').src = '/static/prayog/lab.html?id=' + encodeURIComponent(arg);   // v0.453 a lab opened from the Education Desk
  else if (v === 'lab' && !$('#labframe').src) $('#labframe').src = '/static/prayog/index.html';   // Prayogshala (public labs)
  if (v === 'systems') ENT?.open($('#systems'), arg || 'erp');   // v0.453 an Enterprise employee's Open desk lands on its own role   // v0.396 CONNECT: her own ERP / CRM address + key
  if (v === 'hire') EMP?.hub($('#hire'));
  if (v !== 'interactive') HIV?.leave();
  if (v !== 'vocal') HVO?.leave();
  if (v !== 'seekh') SKH?.leave();   // v0.785 the Video Learner stops polling when its page is left
  if (v !== 'flow') FLW?.leave();
  if (v !== 'connectors') CX?.leave();
  if (v !== 'aiapps') AIA?.leave();
  if (v === 'aiapps') AIA?.open($('#aiapps'), arg);   // v0.772 HOOLA AI APPS
  if (v === 'connectors') CX?.open($('#connectors'), arg);   // v0.774 the Connectors page
  if (v === 'flow') FLW?.open($('#flow'));   // v0.751 HOOLA FLOW
  if (v === 'seekh') SKH?.open($('#seekh'));   // v0.718 the HOOLA AI Video Learner (from the AI Employees hub)
  if (v === 'vocal') HVO?.open();                          // v0.787 HOOLA VOCAL
  if (v === 'interactive') HIV?.open($('#interactive'));   // v0.747 HOOLA INTERACTIVE
  if (v === 'seodesk') EMP?.desk($('#seodesk'));
  if (v === 'socialdesk') EMP?.social($('#socialdesk'));
  if (v === 'caddesk') EMP?.cad($('#caddesk'));
  if (v === 'gamedesk') EMP?.game($('#gamedesk'));
  if (v === 'archdesk') EMP?.arch($('#archdesk'));   // v0.410
  if (v === 'edudesk') EMP?.edu($('#edudesk'));   // v0.453 Education, Research & Lab
  if (v === 'filmdesk') FD?.open($('#filmdesk'));   // v0.565 Film Desk
  if (v === 'leadsdesk') EMP?.leads($('#leadsdesk'));   // v0.686.0 Leads Desk (the Lead Generation employee)
  if (v === 'deptdesk') DDK?.open($('#deptdesk'), arg);
  if (v === 'accountsdesk') BAHI?.open($('#accountsdesk'));   // v0.807 BAHI: the GST & Accounts employee's desk   // v0.799 DESK ROOM (built as 0.796): a department desk, opened on one employee
  if (v === 'skills') SK?.draw($('#skills'));   // v0.481 the Skill Desk
  if (v === 'creative') WORKSPACE?.open();
  if (v === 'creative') $('#ttl').textContent = '· Creative workspace';
}
document.addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (b) go(b.dataset.v); });
$('#menu').addEventListener('click', () => $('#app').classList.add('drawer'));
$('#scrim').addEventListener('click', () => $('#app').classList.remove('drawer'));
$('#collapse').addEventListener('click', () => $('#app').classList.toggle('collapsed'));
/* v0.237 the sidebar adapts to its own width (drag / collapse / small screens): under ~260px (236 inside the padding) the shortcut hints hide so
   New chat, Search and every label stay on one line instead of wrapping */
if (window.ResizeObserver) { const SB = document.querySelector('#app .side');
  if (SB) new ResizeObserver(([e]) => SB.classList.toggle('narrow', e.contentRect.width < 236)).observe(SB); }
$('#collapse').addEventListener('click', () => {
  $('#collapse').setAttribute('aria-expanded', String(!$('#app').classList.contains('collapsed')));
});
$('#liveBtn').addEventListener('click', () => {
  if (B?.isOpen()) { B.close(); $('#app').classList.add('open'); return; }
  if (PN?.isOpen()) { PN.close(); $('#app').classList.add('open'); return; }     // v0.163 one right-hand column at a time
  $('#app').classList.toggle('open');
});
$('#liveClose').addEventListener('click', () => $('#app').classList.remove('open'));
// v0.285 the account button opens Claude's account menu (above it): who is signed in, Settings, Library, the theme,
// keyboard shortcuts, Log out
$('#model').addEventListener('click', e => {
  if (!window.HoolaMenu) { go('main'); return; }
  const t = TH?.theme() || 'system', setT = v => () => TH?.setTheme(v);
  HoolaMenu.open(e.currentTarget, [
    {header: ME.email || ME.owner || 'Signed in'},
    {label: 'Settings', icon: 'settings', run: () => go('main')},
    ...(PN ? [{label: 'Library', icon: 'library', run: () => go('bana')}] : []),
    {label: 'Skills', icon: 'skills', run: () => go('skills')},   // v0.481 the Skill Desk
    {sep: true},
    {label: 'Light', icon: 'sun', checked: t === 'light', run: setT('light')},
    {label: 'Dark', icon: 'moon', checked: t === 'dark', run: setT('dark')},
    {label: 'System', icon: 'monitor', checked: t === 'system', run: setT('system')},
    {sep: true},
    {label: 'Keyboard shortcuts', icon: 'keyboard', kbd: '?', run: () => openKeys()},
    {label: 'Log out', icon: 'logout', run: () => logout()},
  ], {align: 'start', place: 'above', width: 'anchor', cls: 'acctm', label: 'Account', keyboard: e.detail === 0});
});

/* ================= v0.240 CALM BRAND: Light / Dark / System, text size, reduce motion, live border glow ================= */
const TH = window.HoolaTheme;
function themeSync() {
  if (!TH) return;
  const t = TH.theme(), z = TH.size();
  $$('[data-theme-set]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.themeSet === t)));
  $$('[data-size-set]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.sizeSet === z)));
  const f = TH.chatFont ? TH.chatFont() : 'serif';
  $$('[data-font-set]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.fontSet === f)));
  const c = $('#calmSw'); if (c) c.setAttribute('aria-checked', String(TH.calm()));
  const g = $('#glowSw'); if (g) g.setAttribute('aria-checked', String(TH.glow()));
  $$('.themeseg').forEach(seg => { const bs = $$('button', seg), i = Math.max(0, bs.findIndex(b => b.getAttribute('aria-checked') === 'true'));
    const p = seg.querySelector('.tpill'), on = bs[i]; if (p && on) { p.style.width = on.offsetWidth + 'px'; p.style.transform = `translateX(${on.offsetLeft - 3}px)`; } });
}
TH?.onChange(themeSync); themeSync();
if (window.ResizeObserver) new ResizeObserver(() => themeSync()).observe(document.querySelector('#app .side') || document.body);
document.addEventListener('click', e => {
  const b = e.target.closest('[data-theme-set],[data-size-set],[data-font-set],#calmSw,#glowSw'); if (!b || !TH) return;
  if (b.dataset.themeSet) TH.setTheme(b.dataset.themeSet, e);
  else if (b.dataset.sizeSet) TH.setSize(b.dataset.sizeSet);
  else if (b.dataset.fontSet) TH.setChatFont(b.dataset.fontSet);
  else if (b.id === 'calmSw') TH.setCalm(!TH.calm());
  else if (b.id === 'glowSw') TH.setGlow(!TH.glow());
});
function appearanceHTML() {
  const card = (k, n, pv) => `<button type="button" class="tcard" role="radio" data-theme-set="${k}" aria-checked="false"><span class="pv">${pv}</span><span class="nm">${n}<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span></button>`;
  const mini = c => `<span class="pvm ${c}"><i></i><b></b><u></u></span>`;
  return `<div class="tile gl appear" id="appearance"><h3>Appearance</h3>
    <p class="muted" style="font-size:13.5px;margin:-2px 0 12px">System follows your computer: light by day, dark at night.</p>
    <div class="tcards" role="radiogroup" aria-label="Theme">${card('light', 'Light', `<span class="pvs pvL"></span>${mini('pvL')}`)}${card('dark', 'Dark', `<span class="pvs pvD"></span>${mini('pvD')}`)}${card('system', 'System', mini('pvL') + mini('pvD'))}</div>
    <div class="aprow"><div><b>Text size</b><span>Chat text and the sidebar.</span></div>
      <div class="themeseg sizeseg" role="radiogroup" aria-label="Text size"><span class="tpill" aria-hidden="true"></span><button type="button" role="radio" data-size-set="sm" aria-checked="false">Small</button><button type="button" role="radio" data-size-set="md" aria-checked="false">Default</button><button type="button" role="radio" data-size-set="lg" aria-checked="false">Large</button></div></div>
    <div class="aprow"><div><b>Chat font</b><span>How Hoola's replies are written. Your messages stay as they are.</span></div>
      <div class="themeseg fontseg" role="radiogroup" aria-label="Chat font"><span class="tpill" aria-hidden="true"></span><button type="button" role="radio" data-font-set="serif" aria-checked="false">Serif</button><button type="button" role="radio" data-font-set="sans" aria-checked="false">Sans</button><button type="button" role="radio" data-font-set="system" aria-checked="false">System</button><button type="button" role="radio" data-font-set="dyslexic" aria-checked="false">Dyslexic</button></div></div>
    <div class="aprow"><div><b>Reduce motion</b><span>Replies appear at once. No glow, fades or moving borders.</span></div><button type="button" class="swt" role="switch" id="calmSw" aria-checked="false" aria-label="Reduce motion"><i></i></button></div>
    <div class="aprow"><div><b>Live border glow</b><span>The soft light that runs round a card while Hoola works or waits for you.</span></div><button type="button" class="swt" role="switch" id="glowSw" aria-checked="true" aria-label="Live border glow"><i></i></button></div>
  </div>`;
}

// v0.740 MODEL DROPDOWN: she picks the chat model from the owner's list; her next message runs on it.
let MODELS = null;
const mlabel = m => (m && (m.name || m.id || '')).replace(/^[^:]*:\s*/, '').replace(/\s*\((free|Google Gemini|Groq|Mistral|NVIDIA|Z\.ai|OpenRouter)\)\s*$/i, '');
async function loadModels() {
  const b = $('#modelBtn'); if (!b) return;
  try { MODELS = await api('GET', '/api/model/choices'); } catch { MODELS = null; }
  if (!MODELS || !MODELS.available || !(MODELS.models || []).length) { b.hidden = true; return; }
  const cur = MODELS.models.find(m => m.selected) || MODELS.models[0];
  b.querySelector('.mname').textContent = mlabel(cur);
  b.title = 'Model: ' + (cur.name || cur.id);
  b.hidden = false;
}
function modelMenu() {
  const b = $('#modelBtn'); if (!MODELS || !window.HoolaMenu) return;
  const items = [{header: 'Model for your chats'}];
  for (const m of MODELS.models) {
    const plan = m.free === true ? 'Free' : m.free === false ? 'Paid' : (m.provider || '');   // v0.741 another provider: its name
    const bits = [plan, (m.reads || []).includes('image') ? 'reads pictures' : 'text only'].filter(Boolean);
    if (m.default) bits.push('default');
    items.push({label: mlabel(m), sub: m.pickable ? bits.join(' · ') : m.note, checked: !!m.selected,
                disabled: !m.pickable, run: async () => {
                  try { MODELS = await api('PUT', '/api/model/choice', {model: m.id}); await loadModels();
                        toast('Your next message runs on ' + mlabel(m) + '.'); }
                  catch (e) { toast(e.message, true); }
                }});
  }
  HoolaMenu.open(b, items, {align: 'end', place: 'above', label: 'Choose the model', width: 300});
}
document.addEventListener('click', e => { if (e.target.closest && e.target.closest('#modelBtn')) modelMenu(); });

async function enter() {
  ME = await api('GET', '/api/console/me');
  AV = ME.avatar?.name || 'Santosh';
  $$('.aname').forEach(e => e.textContent = AV);
  const img = ME.avatar?.gender === 'f' ? '/static/santosh-happy.png' : '/static/santosh-head.png';
  $$('.aimg').forEach(e => e.src = img); $('#uimg').src = img;
  $('#uname').textContent = ME.owner || ME.email || 'You'; $('#uhandle').textContent = `${AV} · ${ME.handle || ''}`;
  $('#uini').textContent = (ME.owner || ME.email || 'H').trim().charAt(0).toUpperCase();
  const h = new Date().getHours(), first = (ME.owner && ME.owner !== 'Hoola user') ? ME.owner.split(' ')[0] : '';
  $('#greet').innerHTML = esc(HUMAN ? HOUR_WORD(h) : h < 12 ? 'Good morning' : h < 17 ? 'Hello' : 'Good evening') + (first ? `, <span class="gname">${esc(first)}</span>` : '');
  humanTagline();
  loadModels();                                  // v0.740 the model dropdown in the composer
  if (window.HoolaEmployees && !EMP) {           // v0.317 Employees for everyone; a desk only once its employee is hired
    EMP = HoolaEmployees({api, esc, toast, changed: syncEmployees, open: (v, arg) => go(v, arg),   // v0.453 desks open Systems / a lab directly
                          say: text => { go('chat'); msg.value = text; msg.dispatchEvent(new Event('input')); composer.requestSubmit(); }});
    if (!NAV.some(([k]) => k === 'hire')) NAV.unshift(['hire', 'AI Employees']);   // v0.443 her AI staff is the FIRST section
  }
  if (CONFIG.prompting && window.HoolaImprove && !IMP) {   // HOOLA PROMPTING: a sidebar row + the Improve button in the chat box
    IMP = HoolaImprove({api, esc, toast});
    if (!NAV.some(([k]) => k === 'prompting')) NAV.splice(NAV.findIndex(([k]) => k === 'creative') + 1, 0, ['prompting', 'Hoola Prompting']);
    const ib = $('#impBtn'), it = $('#impTxt');
    ib.hidden = false;
    const reset = () => { IMP_BACK = null; IMP_DONE = ''; it.textContent = 'Improve'; ib.title = 'See what Hoola understood and turn this into a complete prompt'; };
    msg.addEventListener('input', () => { if (IMP_BACK !== null && msg.value !== IMP_DONE) reset(); });
    ib.addEventListener('click', () => {
      if (IMP_BACK !== null && msg.value === IMP_DONE) {          // Undo: her own words back, exactly as she typed them
        const back = IMP_BACK; reset(); msg.value = back; msg.dispatchEvent(new Event('input')); msg.focus(); return; }
      const mine = msg.value;
      if (!mine.trim()) { msg.focus(); toast('Write a few words first.'); return; }
      IMP.open(mine, {conversationId: () => CONV, useText: p => (p.out.run.to === 'chat' ? p.out.run.text : p.out.prompt), onUse: t => {
        msg.value = t; msg.dispatchEvent(new Event('input')); IMP_BACK = mine; IMP_DONE = msg.value;
        it.textContent = 'Undo'; ib.title = 'Put my own words back'; msg.focus(); }});
    });
  }
  if (CONFIG.flow && window.HoolaFlow && !FLW) {   // v0.751 HOOLA FLOW: a row right under Create (with Interactive / Code)
    FLW = HoolaFlow({api, esc, toast, say: (text, send) => { go('chat'); msg.value = text; msg.dispatchEvent(new Event('input')); msg.focus(); if (send) composer.requestSubmit(); }});
    if (!NAV.some(([k]) => k === 'flow')) NAV.splice(NAV.findIndex(([k]) => k === 'creative') + 1, 0, ['flow', 'Hoola Flow']);
  }
  try {                                            // v0.777 'Put in the Hoola chat' from the Hoola Flow page: lands in the chat box, never sent
    const d = localStorage.getItem('hoola.flow.toChat');
    if (d) { localStorage.removeItem('hoola.flow.toChat'); FLOW_TEXT = d;       // the chat that opens next takes it (see openChat)
      setTimeout(() => { if (!FLOW_TEXT) return; go('chat'); msg.value = d; msg.dispatchEvent(new Event('input')); msg.focus(); }, 0);
      setTimeout(() => { FLOW_TEXT = ''; }, 6000); }
  } catch (e) { /* private window */ }
  if (CONFIG.flow_mic && window.HoolaFlowMic && !FMIC) {   // v0.751 the chat box mic dictates through Kaan when its engine is ready
    FMIC = HoolaFlowMic({api, toast, onText: t => { msg.value = t; msg.dispatchEvent(new Event('input')); scrollDown(true); },
      onState: (on, why) => { $('#micBtn').classList.toggle('on', !!on); $('#micBtn').classList.toggle('busy', why === 'writing');
        $('#micBtn').title = on ? 'Hoola Flow is listening - click (or Ctrl + Space) to finish' : 'Speak to type (Hoola Flow) - Ctrl + Space'; }});
  }
  if (CONFIG.design) {   // v0.777 HOOLA DESIGN: the design editor, a row right under Create; opens /console/design
    if (!NAV.some(([k]) => k === 'design')) NAV.splice(NAV.findIndex(([k]) => k === 'creative') + 1, 0, ['design', 'Hoola Design']);
  }
  if (CONFIG.hoola_code) {   // v0.748 HOOLA CODE: a row right under Create / Hoola Interactive; v0.768 the row opens /console/code
    if (!NAV.some(([k]) => k === 'code')) NAV.splice(NAV.findIndex(([k]) => k === 'creative') + 1, 0, ['code', 'Hoola Code']);
  }
  if (CONFIG.interactive && window.HoolaInteractive && !HIV) {   // v0.747 HOOLA INTERACTIVE: a row right under Create
    HIV = HoolaInteractive({api, esc, toast, back: () => go('chat'), upload: async file => {   // v0.772 its own full page; Console = back to chat
      let id = CONV;
      if (!id) { const c = await api('POST', '/api/conversations?reuse=1'); id = c.id; }
      const fd = new FormData(); fd.append('file', file, file.name);
      return api('POST', `/api/conversations/${encodeURIComponent(id)}/files`, undefined, {form: fd});
    }});
    if (!NAV.some(([k]) => k === 'interactive')) NAV.splice(NAV.findIndex(([k]) => k === 'creative') + 1, 0, ['interactive', 'Hoola Interactive']);
  }
  if (CONFIG.vocal && window.HoolaVocal && !HVO) {               // v0.787 HOOLA VOCAL: the voice studio, a row under Hoola Interactive
    HVO = HoolaVocal({api, esc, toast, back: () => go('chat'), go: v => go(NAV.some(([k]) => k === v) ? v : 'chat'), upload: async file => {
      let id = CONV;
      if (!id) { const c = await api('POST', '/api/conversations?reuse=1'); id = c.id; }
      const fd = new FormData(); fd.append('file', file, file.name);
      return api('POST', `/api/conversations/${encodeURIComponent(id)}/files`, undefined, {form: fd});
    }});
    if (!NAV.some(([k]) => k === 'vocal')) { const at = NAV.findIndex(([k]) => k === 'interactive'); NAV.splice((at < 0 ? NAV.findIndex(([k]) => k === 'creative') : at) + 1, 0, ['vocal', 'Hoola Vocal']); }
  }
  if (window.HoolaSeekh && !SKH) {               // v0.718 the Video Learner: stays on its page while Hoola works
    SKH = HoolaSeekh({api, esc, toast, open: (v, arg) => go(v, arg), live: () => $('#app').classList.add('open'),
                      chat: async id => { if (id && id !== CONV) { try { await openConv(id); } catch { /* the chat view still opens */ } } go('chat'); },   // v0.785 Answer opens the run's own chat
                      send: async (text, files) => {        // one honest chat turn without leaving the panel (v0.785: + the files a step uploads)
                        let id = CONV;
                        if (!id) { const c = await api('POST', '/api/conversations?reuse=1'); id = c.id; }
                        const r = await api('POST', `/api/conversations/${encodeURIComponent(id)}/messages`,
                                   {text: String(text || ''), client_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())), files: (files || []).filter(Boolean), hints: []});
                        return {...(r || {}), conversation_id: id};   // v0.745 the learner follows this run on its own page
                      },
                      upload: async file => {      // the panel's video picker rides the chat file lane (25 MB)
                        let id = CONV;
                        if (!id) { const c = await api('POST', '/api/conversations?reuse=1'); id = c.id; }
                        const fd = new FormData(); fd.append('file', file, file.name);
                        return api('POST', `/api/conversations/${encodeURIComponent(id)}/files`, undefined, {form: fd});
                      }});
  }
  syncEmployees(ME.employees || {});
  if (window.HoolaEnterprise && !ENT) {        // v0.396 CONNECT: the only door an enterprise credential has
    ENT = HoolaEnterprise({api, esc, toast});
  }
  if (window.HoolaFilmDesk && !FD) FD = HoolaFilmDesk({api, esc, toast});   // v0.565
  if (window.HoolaBahi && !BAHI) BAHI = HoolaBahi({api, esc, toast, open: (v, arg) => go(v, arg), title: t => { if (VIEW === 'accountsdesk') $('#ttl').textContent = t; }});   // v0.806
  if (window.HoolaDeptDesk && !DDK) DDK = HoolaDeptDesk({api, esc, toast, open: (v, arg) => go(v, arg),   // v0.799 DESK ROOM (built as 0.796)
    ask: text => { go('chat'); msg.value = text; msg.dispatchEvent(new Event('input')); msg.focus(); },   // lands in the chat box, never sent by itself
    title: t => { if (VIEW === 'deptdesk') $('#ttl').textContent = t; }});
  if (window.HoolaConnectors && !CX) {         // v0.774 Connectors: "Ask Hoola" lines go into the composer, never sent by themselves
    CX = HoolaConnectors({api, esc, toast, say: text => { go('chat'); msg.value = text; msg.dispatchEvent(new Event('input')); msg.focus(); }});
  }
  if (window.HoolaAiApps && !AIA) {           // v0.772 HOOLA AI APPS: a row right under App Development
    AIA = HoolaAiApps({api, esc, toast});
    if (!NAV.some(([k]) => k === 'aiapps')) NAV.splice(NAV.findIndex(([k]) => k === 'appdev') + 1, 0, ['aiapps', 'AI Apps']);
  }
  if (window.HoolaSkills && !SK) {             // v0.481 the Skill Desk
    SK = HoolaSkills({api, esc, toast});
  }
  if (ME.arena && window.HoolaArena && !AR) { AR = HoolaArena({api, esc, toast}); if (!NAV.some(([k]) => k === 'arena')) NAV.push(['arena', 'Arena']); }   // v0.312 owner only
  $('#login').hidden = true; $('#app').hidden = false; drawNav(); drawKaam(); go('chat');
  if (CONFIG.sessions && window.HoolaChats && window.HoolaStream && !CH) {   // v0.162 many chats (v0.170: on with CONSOLE_V2)
    CH = HoolaChats({api, esc, toast, current: () => CONV, open: id => { go('chat'); openConv(id); }, loaded: () => drawHead(),
                     jump: (c, e) => jumpTo(c, e), newChat: () => $('#newChat').click(), avatar: () => AV,
                     get pickProject() { return PJ ? c => PJ.pick(c) : null; },
                     get openSection() { return PJ ? pid => PJ.open(pid) : null; },   // v0.193 session name opens its page
                     newChatIn: async pid => {                                        // v0.193 "+" on a session header
                       try { const c = await api('POST', `/api/conversations?reuse=1&project_id=${encodeURIComponent(pid)}`);
                             go('chat'); await openConv(c.id, true); loadRecents(); }
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
      studio: (kind, p) => { go('chat'); const b = col.querySelector(`[data-key="${CSS.escape(kind + ':' + p.id)}"] [data-ba="studio"]`); if (b) b.click(); else toast('To open the studio, open that job’s card in the chat.'); }});
    NAV.splice(Math.max(0, NAV.findIndex(([k]) => k === 'creative')), 0, ['bana', 'Library']); drawNav();   // v0.447 just above Create, never inside the AI Employees group
  }
  const list = await loadRecents();
  const fromUrl = (location.pathname.match(/^\/console\/c\/([^/?#]+)/) || [])[1];
  const firstChat = async () => list[0]?.id || (await api('POST', '/api/conversations')).id;
  if (CH) accountStream();
  loadGauge(); clearInterval(GAUGE_T); GAUGE_T = setInterval(loadGauge, 300000);   // v0.173 the kharcha line stays honest
  if (CH && fromUrl) await openConv(decodeURIComponent(fromUrl), false, {noPush: true, fallback: async () => {
    toast('That chat was not found (it may have been deleted). Opening your latest chat.'); await openConv(await firstChat()); }});
  else await openConv(await firstChat());
  refreshPending(); clearInterval(PENDING_TIMER); PENDING_TIMER = setInterval(refreshPending, 30000);
  loadJobs(); clearInterval(JOBS_T); JOBS_T = setInterval(loadJobs, 20000); loadPcPill();
}

/* ================= recents ================= */
let CH = null;          // chatlist.js (CHAT_SESSIONS; on by default under CONSOLE_V2)
async function loadRecents() {
  if (CH) { const l = await CH.load(); if (VIEW === 'chat') $('#ttl').textContent = chatFolder(); drawHead(); return l; }
  let list = [];
  try { list = (await api('GET', '/api/console/conversations')).conversations || []; } catch {}
  $('#recents').innerHTML = list.map(c => `<button class="rc" data-conv="${esc(c.id)}" title="${esc(timeOf(c.updated_at))}"${c.id === CONV ? ' aria-current="true"' : ''}>${esc(c.title)}</button>`).join('') || '<div class="empty" style="padding:8px 12px">No conversations yet.</div>';
  return list;
}
$('#recents').addEventListener('click', e => { if (CH) return; const b = e.target.closest('[data-conv]'); if (b) { openConv(b.dataset.conv); go('chat'); } });
$('#searchBtn').addEventListener('click', () => CH?.openSearch());
/* v0.250 incognito chat: Hoola reads her memory there but keeps nothing from it (no facts, search, diary, page) */
var INCOG = new Set();   // var: drawHead may run before this line during start-up
async function newIncognito() {
  try { const c = await api('POST', '/api/conversations?incognito=1'); INCOG.add(c.id); go('chat'); await openConv(c.id, true);
        drawHead(); msg.focus(); toast('Incognito chat - nothing from here goes into Hoola\'s memory.'); }
  catch (e) { toast(e.message, true); }
}
$('#newChat').addEventListener('click', async () => {
  // v0.231 New chat opens her untouched empty chat if she has one (never a pile of identical "Naya chat" rows)
  try { const c = await api('POST', '/api/conversations?reuse=1'); go('chat'); await openConv(c.id, true); loadRecents(); msg.focus(); }
  catch (e) { toast(e.message, true); }
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
$('#jump').addEventListener('click', () => { thread.scrollTo({top: thread.scrollHeight, behavior: SMOOTH()}); STICK = true; $('#jump').hidden = true; });
function landing(on) {
  $('#landing').hidden = !on; $('#thread').hidden = on; $('#dock').hidden = on;
  (on ? $('#slotLand') : $('#slotDock')).appendChild(composer);
  msg.placeholder = HUMAN ? (on ? `What should ${AV} do? For example: “Reply to my supplier and attach the invoice”` : `Reply to ${AV}…`)
    : on ? 'Ask anything, attach a file, or describe what you want to create' : `Reply to ${AV}…  (/ for commands)`;
  drawHead();
}
/* v0.222 R3: the conversation header - title, its session, export and the chat's own menu */
function drawHead() {
  const on = !$('#thread').hidden; $('#chead').hidden = !on; if (!on) return;
  const c = CH?.find(CONV), p = c?.project_id && PJ?.nameOf(c.project_id);
  $('#ctitle').textContent = c?.title || 'New chat';
  const inc = !!(c?.incognito || INCOG?.has(CONV));   // v0.250
  const t = $('#ctag'); t.hidden = !p && !inc; t.textContent = p ? `${p.emoji || '📁'} ${p.name}` : inc ? '🕶 Incognito' : '';
  $('#cMore').hidden = !c;
  meter();
}
/* v0.244 PHASE 3A the "how full" meter (Claude Code's context meter): % of the window, compaction at 75% */
let METER_T = 0;
async function meter() {
  const el = $('#cMeter'); if (!el) return;
  const id = CONV; if (!id) { el.hidden = true; return; }
  clearTimeout(METER_T);
  METER_T = setTimeout(async () => {
    try {
      const r = (await api('GET', `/api/conversations/${encodeURIComponent(id)}/context`)).context || {};
      if (id !== CONV) return;
      if (r.mode !== 'claude') { el.hidden = true; return; }
      const pct = Math.round(Number(r.percent || 0));
      el.textContent = `Memory ${pct}%`; el.hidden = false;
      el.classList.toggle('hot', pct >= 60);
    } catch (e) { el.hidden = true; }
  }, 300);
}
$('#cMeter')?.addEventListener('click', async () => {
  if (!CONV) return;
  let text = 'This chat has not been summarised yet - every message still goes to Hoola word for word.';
  try { const r = await api('GET', `/api/conversations/${encodeURIComponent(CONV)}/compact`); if (r.active?.summary) text = r.active.summary; }
  catch (e) { toast(e.message, true); return; }
  const d = document.createElement('dialog'); d.className = 'gl cmdlg';
  d.innerHTML = `<h3 style="margin:0 0 8px">Older messages, summarised</h3><div class="faint" style="white-space:pre-wrap;font-size:13px;max-height:60vh;overflow:auto"></div><p style="text-align:right;margin:10px 0 0"><button class="btn soft" type="button">Close</button></p>`;
  d.querySelector('div').textContent = text;
  d.querySelector('button').addEventListener('click', () => d.close());
  d.addEventListener('close', () => d.remove());
  document.body.appendChild(d); d.showModal();
});
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
    STEPBUF = document.createElement('details'); STEPBUF.className = 'tools hmfold'; STEPBUF.open = false;   // v0.718 the same fold as a live turn
    STEPBUF.innerHTML = `<summary><span class="sm"></span>${HM_DN}</summary><div class="tl"></div>`;
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
  else STEPBUF.querySelector('.sm').textContent = 'Worked';   // v0.721 no count - the arrow opens the steps
  STEPBUF = null;
}
// v0.279 attach.js: her files as Claude-style tiles (composer tray, above her sent bubble, full-screen viewer)
const ATT = window.HoolaAttach ? HoolaAttach({api, esc, toast, token: () => TOKEN,
  itemOf: (kind, p) => PN?.itemOf(kind, p), open: item => PN ? (PN.open(item), true) : false}) : null;
const FILE_ONLY = 'Ye file dekho';   // the words a files-only message carries to Hoola
function userBubble(text, files, eid, cid, at) {
  const d = document.createElement('div'); d.className = 'mu';
  const tiles = files?.length && ATT ? ATT.sent(files) : null;   // v0.279 her files sit above the bubble, like Claude
  d.innerHTML = (files?.length && !ATT ? `<div class="att">${files.map(f => `<span class="chip">📎 ${esc(f.name || f)}</span>`).join('')}</div>` : '') + `<span class="mut">${esc(text)}</span>`;
  if (tiles && text === FILE_ONLY) d.classList.add('fonly');    // a files-only message shows just the tiles
  if (cid) d.dataset.cid = cid;
  if (eid && !files?.length) attachEdit(d, text, eid);
  if (at) d.dataset.at = at;                             // v0.178 the jump rail reads the day off this
  if (tiles) { if (at) tiles.dataset.at = at; SINK.appendChild(tiles); d._tiles = tiles; }
  SINK.appendChild(d); if (SINK === col) scrollDown(true); TURN = null; return d;
}
/* v0.173 receipts: a message sent while Hoola works shows what became of it — queue mein (take-back possible),
   turant jawab (the quick lane answered beside the running kaam), bhej diya (the queued turn took it). */
function receipt(d, cid, state) {
  const R = RCPTS.get(cid) || {};
  R.el = d; R.state = state; RCPTS.set(cid, R);
  d.querySelector('.rq')?.remove();
  if (state === 'queue') {
    d.insertAdjacentHTML('beforeend', `<span class="rq">⏳ Queued — runs after Hoola’s current job <button type="button" class="rqx">Take back</button></span>`);
    d.querySelector('.rqx').addEventListener('click', async e => {
      e.stopPropagation();
      try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/takeback`, {client_id: cid});
        d.style.transition = 'opacity .25s, transform .25s'; d.style.opacity = '0'; d.style.transform = 'translateY(6px)';
        setTimeout(() => { d._tiles?.remove(); d.remove(); }, 240); RCPTS.delete(cid); toast('Taken back — it never reached Hoola.'); }
      catch (er) { receipt(d, cid, 'sent'); toast(er.status === 409 ? 'It has already started — press Stop.' : er.message, er.status !== 200); }
    });
  } else if (state === 'quick') {
    d.insertAdjacentHTML('beforeend', `<span class="rq ok">⚡ Answered right away</span>`);
    setTimeout(() => { d.querySelector('.rq')?.remove(); RCPTS.delete(cid); }, 6000);
  } else {
    d.insertAdjacentHTML('beforeend', `<span class="rq ok">✓ Sent</span>`);
    setTimeout(() => { d.querySelector('.rq')?.remove(); RCPTS.delete(cid); }, 3000);
  }
}
function receiptUpdate(cid, state) { const R = RCPTS.get(cid); if (R && R.state === 'queue') receipt(R.el, cid, state); }
function attachEdit(d, text, eid) {   // v0.171 her message gets a hover toolbar: Copy + Edit (a new version from here)
  d.dataset.eid = eid;
  if (!CH || d.querySelector('.utbar')) return;
  d.insertAdjacentHTML('beforeend', `<span class="utbar" role="group" aria-label="Message actions">`
    + `<button type="button" class="ua" data-ua="copy" aria-label="Copy">${svg('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>')}</button>`
    + `<button type="button" class="ua" data-ua="edit" aria-label="Edit message">${svg('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>')}</button></span>`);
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
  if (TYPING) return toast(`${AV} is working right now. Stop it first.`, true);
  const keep = d.innerHTML; d.classList.add('editing');
  d.innerHTML = `<textarea aria-label="Edit message" rows="2"></textarea><div class="acts"><button type="button" class="btn soft" data-x>Cancel</button><button type="button" class="btn go" data-s>Send</button></div>`;
  const ta = d.querySelector('textarea'); ta.value = text; ta.focus(); ta.setSelectionRange(text.length, text.length);
  ta.style.height = Math.min(220, ta.scrollHeight) + 'px'; ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(220, ta.scrollHeight) + 'px'; });
  const cancel = () => { d.classList.remove('editing'); d.innerHTML = keep; bindUserBar(d, text); };
  const save = async () => {
    const t = ta.value.trim(); if (!t || t === text) return cancel();
    if (t.length > 32000) return toast('An edited message can be up to 32,000 characters. Send longer text as a new message (it goes as a file).', true);
    d.querySelector('[data-s]').disabled = true;
    try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/edit`, {event_id: +d.dataset.eid, text: t}); await openConv(CONV, false, {noPush: true}); }
    catch (e) { toast(e.message, true); cancel(); }
  };
  d.querySelector('[data-x]').addEventListener('click', cancel); d.querySelector('[data-s]').addEventListener('click', save);
  ta.addEventListener('keydown', e => { if (e.key === 'Escape') cancel(); if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); save(); } });
}
function hoolaBlock() {
  // v0.299: no avatar in the chat space (owner: "REMOVE AVATHAR ICON ENTIERLY FROM CHAT SPACE"). The face is not
  // drawn at all rather than hidden with CSS, so nothing holds a 44px slot and nothing has to hang outside the
  // column to make the words line up - which is also what put the reply row 44px wider than the composer.
  const d = document.createElement('div'); d.className = 'mh';
  d.innerHTML = `<div class="bd"></div>`;
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
   each run of steps is one group that folds into "N steps · Xs" when the turn is over.
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
/* v0.293 KITNA SAMAY: while Hoola works, the row next to the avatar counts the seconds, like Claude. The turn's
   own tool groups already fold to "4 steps · 12 s" and a Soch card to "thought for 8s", but those only appear
   AFTER the work, and a think card only when the model actually reasoned - so for an ordinary wait there was no
   number at all and no way to tell a slow turn from a stuck one. The clock starts with the turn and runs across
   every phase, so it reads total elapsed, not time-in-this-step. It stays blank for the first second so a quick
   reply never flashes "0s". */
let PROGRESS_T0 = 0, PROGRESS_TIMER = 0;
let LAST_WORD_AT = 0;   // v0.302: when a word was last written into the chat, for the watchdog above
function fmtSecs(s) { return s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + String(s % 60).padStart(2, '0') + 's'; }
function progressTick() {
  if (!SIMPLE_PROGRESS) return;
  // v0.302: the watchdog. Hooking "the block finished" (fin) was not enough, because fin only fires when the
  // pacer was given a FINAL text. Measured against the real pacer, two shapes never reach it: deltas followed by
  // reply_end's flush(), and - her case - deltas that simply stop while Hoola goes off to run a long tool. In
  // both the queue drains, no fin ever comes, and the row stays hidden. "No words for a moment" is the signal
  // that actually means the screen has gone quiet, whatever the delivery shape.
  if (TYPING && SIMPLE_PROGRESS.hidden && Date.now() - LAST_WORD_AT > 600) placeProgress();
  const el = SIMPLE_PROGRESS.querySelector('.progress-secs');
  if (!el) return;
  const s = Math.floor((Date.now() - PROGRESS_T0) / 1000);
  const want = s >= 1 ? fmtSecs(s) : '';
  if (el.textContent !== want) el.textContent = want;
}
function simpleProgress(kind,p={}) {
  if(kind!=='typing' && !TYPING)return;
  if (!SIMPLE_PROGRESS) {
    SIMPLE_PROGRESS=document.createElement('div');SIMPLE_PROGRESS.className='simple-progress';
    SIMPLE_PROGRESS.setAttribute('role','status');SIMPLE_PROGRESS.setAttribute('aria-live','polite');SIMPLE_PROGRESS.setAttribute('aria-atomic','true');
    const mark=document.createElement('span');mark.className='progress-mark';mark.setAttribute('aria-hidden','true');   // v0.718 the 3D Hoola mark while she waits
    if(window.HoolaMark)mark.innerHTML=HoolaMark.think(24);
    const label=document.createElement('span');label.className='progress-label';   // v0.299: no avatar here either
    const secs=document.createElement('span');secs.className='progress-secs';secs.setAttribute('aria-hidden','true');   // v0.293 the clock is decoration; the label is what a screen reader reads
    // v0.721 EK HI KAAM-ROW: the ONE working row. The step list (the backend feed) sits under it, folded behind a
    // small arrow - the arrow shows only once there is a step, and opening it is her choice for the whole reply.
    const tog=document.createElement('button');tog.type='button';tog.className='wtog';tog.hidden=true;
    tog.setAttribute('aria-label','Show steps');tog.setAttribute('aria-expanded','false');tog.innerHTML=HM_DN;
    const steps=document.createElement('div');steps.className='tools hmlive wsteps';steps.innerHTML='<div class="tl"></div>';
    tog.addEventListener('click',()=>{const t=TURN;const on=!SIMPLE_PROGRESS?.classList.contains('wopen');
      if(t)t.stepsOpen=on;SIMPLE_PROGRESS?.classList.toggle('wopen',on);tog.setAttribute('aria-expanded',String(on));tog.setAttribute('aria-label',on?'Hide steps':'Show steps');});
    SIMPLE_PROGRESS.append(mark,label,secs,tog,steps);
    if(TURN?.stepsOpen){SIMPLE_PROGRESS.classList.add('wopen');tog.setAttribute('aria-expanded','true');}
    PROGRESS_T0=Date.now();clearInterval(PROGRESS_TIMER);PROGRESS_TIMER=setInterval(progressTick,1000);
  }
  placeProgress();
  let label=PROGRESS_POLICY.phase(kind,p);
  const cur=TURN?.live?.cur;   // v0.721 the row says what is happening NOW, in the step's own words
  if(cur&&/^(Working on it|Thinking|Still working)/.test(label))label=cur;
  const text=SIMPLE_PROGRESS.querySelector('.progress-label');
  if(text.textContent!==label){text.textContent=label;text.classList.remove('wswap');void text.offsetWidth;text.classList.add('wswap');}
  scrollDown();
}
/* v0.299 (owner: "WHEN HOOLA PERFECOM LONG TASK THE LODING, THINGING SECTION GET HIDE FOR WHILE - FIND ROUTE
   CAUSE AND FIX THIS"). The root cause: seg() hides this row the moment a text block starts streaming - right,
   because the words themselves show it is working - but NOTHING brought it back when those words ended. It was
   only ever un-hidden by the NEXT progress event. So on a long job the shape was: narration line arrives, row
   hides, Hoola runs a 40-second tool with no events to send, and the screen sits dead with no loader and no
   clock until the next step. placeProgress() is now called again the moment a block finishes streaming while the
   turn is still running, so the gap between "what I'm doing" and the next step is never silent. */
function placeProgress(){
  if(!SIMPLE_PROGRESS)return;
  if(SIMPLE_PROGRESS.parentElement!==col||SIMPLE_PROGRESS.nextElementSibling)col.appendChild(SIMPLE_PROGRESS);   // v0.227.3 always the last row
  SIMPLE_PROGRESS.hidden=false;
}
function clearSimpleProgress(){SIMPLE_PROGRESS?.remove();SIMPLE_PROGRESS=null;clearInterval(PROGRESS_TIMER);PROGRESS_TIMER=0;}
/* v0.716 NAYA ROOP (her pick 5): like Claude, the turn's tool steps show LIVE as rows - a spinner while a step runs,
   a tick that draws itself when it is done - and fold into one "Worked for 12s · 3 steps" line the moment the words
   start (or the turn ends). Before, a live turn showed only the one-line progress label; the rows existed only on a
   reload (replayStep). */
const HM_TICK = '<svg viewBox="0 0 16 16"><path d="M3 8.5l3.2 3L13 5"/></svg>';
const HM_CHEV = '<svg class="hm-chev" viewBox="0 0 12 12"><path d="M4 2l4 4-4 4"/></svg>';
const HM_DN = '<svg class="hm-dn" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3"/></svg>';   // v0.721 the only control: an arrow
function liveStep(p) {
  if (!TYPING) return;
  const t = turn();
  if (!SIMPLE_PROGRESS) simpleProgress('step', p);
  let g = t.live;
  if (!g) {
    // v0.721: no second "Working" block in the chat any more - the steps live inside the ONE working row; this
    // hidden anchor only keeps their place, so the fold ("Worked for 12s") lands where the work happened
    const el = document.createElement('details'); el.className = 'tools hmfold'; el.open = false; el.hidden = true;
    el.innerHTML = `<summary><span class="sm"></span>${HM_DN}</summary><div class="tl"></div>`;
    const tl = SIMPLE_PROGRESS.querySelector('.wsteps .tl'); tl.innerHTML = '';
    g = t.live = {el, tl, rows: new Map(), t0: Date.now(), n: 0, cur: ''};
    put(t, el);
    if (SIMPLE_PROGRESS) placeProgress();
  }
  const tog = SIMPLE_PROGRESS?.querySelector('.wtog'); if (tog) tog.hidden = false;
  const id = String(p.id || p.tool || g.n);
  let r = g.rows.get(id);
  if (!r) {
    r = document.createElement('div'); r.className = 'ts run';
    r.innerHTML = '<span class="ic"><span class="hm-spin"></span></span><span class="tx"></span><span class="tm"></span>';
    r._t0 = Date.now(); g.rows.set(id, r); g.n++; g.tl.appendChild(r);
  }
  r.querySelector('.tx').textContent = p.label || p.tool || 'Working';
  if (p.state !== 'done' && p.state !== 'error') g.cur = p.label || p.tool || g.cur;
  if (p.state === 'done' || p.state === 'error') {
    r.classList.remove('run'); r.classList.toggle('err', p.state === 'error');
    const ic = r.querySelector('.ic'); ic.className = p.state === 'error' ? 'ic' : 'ic hm-tick';
    ic.innerHTML = p.state === 'error' ? '!' : HM_TICK;
    const s = (Date.now() - r._t0) / 1000; r.querySelector('.tm').textContent = s < 1 ? '<1s' : s.toFixed(1) + 's';
  }
  scrollDown();
}
function foldLive(t = TURN) {
  const g = t?.live; if (!g) return;
  t.live = null;
  const secs = Math.max(1, Math.round((Date.now() - g.t0) / 1000));
  const tl = g.el.querySelector('.tl'); while (g.tl.firstChild) tl.appendChild(g.tl.firstChild);
  g.el.hidden = false; g.el.open = !!t.stepsOpen;
  g.el.querySelector('.sm').textContent = `Worked for ${fmtSecs(secs)}`;   // v0.721 no step count, just the arrow
  const tog = SIMPLE_PROGRESS?.querySelector('.wtog'); if (tog) tog.hidden = true;
  g.el.querySelectorAll('.ts.run').forEach(r => { r.classList.remove('run'); });
  // the rows keep their live look inside the fold (spinner never left spinning)
  g.el.querySelectorAll('.ts .hm-spin').forEach(sp => { sp.parentElement.className = 'ic hm-tick'; sp.parentElement.innerHTML = HM_TICK; });
  g.el.querySelector('.tl').classList.add('hmrows');
}
/* parity Phase 5: the turn's work receipt ("4/24 steps · 2 calls (2 ok) · done ✓ · tools") is step data, not a chat
   row - it sits small and grey at the bottom of the folded "Worked for" steps; nothing shows when there is no fold */
function ledgerLine(line, root = col, t = TURN) {
  if (!line) return;
  const tl = t?.live?.tl || [...root.querySelectorAll('.hmfold')].pop()?.querySelector('.tl');
  if (!tl) return;
  tl.querySelector('.wledger')?.remove();
  const d = document.createElement('div'); d.className = 'wledger'; d.textContent = String(line).replace(/^\(Kaam:\s*/, '').replace(/\)$/, '');
  tl.appendChild(d);
}
function stepEvent(p) { liveStep(p); simpleProgress('step',p); }   // v0.721 one row: liveStep fills its list, simpleProgress its words
function closeTurnTools(t = TURN) {
  if (!t) return;
  for (const g of t.groups || []) {
    if (g.closed) continue; g.closed = true;
    const secs = Math.round((Date.now() - g.t0) / 1000);
    g.el.querySelector('summary').innerHTML = `<span class="ic" style="width:18px;height:18px;border-radius:50%;display:grid;place-items:center;background:rgba(52,211,153,.18);color:var(--ok);font-size:10px;font-weight:900">✓</span><span>${g.n} step${g.n > 1 ? "s" : ""} · ${secs < 1 ? '<1' : secs} s</span><span class="chev">⌄</span>`;
    g.el.open = false;
  }
}
let TYPING = null;
function typing(on) {
  $('#stopBtn').hidden=!on;
  if(on){TYPING ||= document.createElement('div');simpleProgress('typing');live('run');}
  else {
    foldLive();TYPING=null;clearSimpleProgress();closeTurnTools();
    for(const [cid,R] of [...RCPTS])if(R.state==='queue')receiptUpdate(cid,'sent');
    live(QUEUE.length?'ask':'idle');TURN=null;
  }
}

/* ================= thinking card (v0.171): the model's reasoning while it thinks — Claude thinking /
   GLM reasoning arrive as live-only `think` events (turn:seg, like the text blocks). Live: open, counting.
   Reply over: folded to "thought for 8s". Never stored, so a reload builds it only from a /live resume. */
const THINKS = new Map();   // turn:seg -> {el, tb, t0, timer}
function thinkEvent(p) { simpleProgress('think',p); }
function closeThinks(turnId) {
  for (const [key, K] of [...THINKS]) {
    if (!key.startsWith(turnId + ':')) continue;
    THINKS.delete(key); clearInterval(K.timer);
    if (!K.raw.trim()) { K.el.remove(); continue; }        // thought but never said anything worth keeping
    const s = Math.max(1, Math.round((Date.now() - K.t0) / 1000)), tt = K.el.querySelector('.tt'), sm = K.el.querySelector('.tsm');
    if (tt) tt.textContent = s < 60 ? s + 's' : Math.floor(s / 60) + 'm' + String(s % 60).padStart(2, '0');
    if (sm) sm.textContent = `${AV} thought for`;
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
  foldLive(R.t);                                                         // v0.718 the steps so far fold into one line
  const el = document.createElement('div'); el.className = 'txt textmd'; el.dataset.seg = n;
  put(R.t, el); R.t.afterText = true;
  if (TYPING && TYPING.parentNode === R.t.bd) TYPING.hidden = true;    // the words themselves show that it is working
  if (SIMPLE_PROGRESS) SIMPLE_PROGRESS.hidden = true;                    // v0.227.3 one row: the streaming words replace the progress line
  const view = new HoolaMD.Live(el, {soft: true});   // v0.718 the newest words land out of a soft focus
  S = {el, view, pacer: new HoolaStream.Pacer((text, fin) => {
    view.update(text, !fin);
    LAST_WORD_AT = Date.now();                       // v0.302 feeds the watchdog in progressTick
    // v0.299: the block is finished and the turn is still going - bring the loader straight back rather than
    // leaving the screen dead until the next step event. This covers the shapes that DO end in a final text;
    // the watchdog covers the ones that do not (deltas that just stop while a long tool runs).
    if (fin && TYPING) placeProgress();
    scrollDown();
  })};
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
    + `<button type="button" class="ra" data-act="quote" aria-label="Quote" title="Quote in the composer">${svg('<path d="M4 5h16v11H8l-4 4z"/><path d="M8 9h8M8 12h5"/>')}<span>Quote</span></button>`
    + (can && last ? `<button type="button" class="ra" data-act="retry" aria-label="Retry">${svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>')}<span>${HUMAN ? 'Ask again' : 'Retry'}</span></button>` : '')
    + (can ? `<button type="button" class="ra" data-act="up" aria-label="Good reply" aria-pressed="${R.fb === 'up'}">${svg('<path d="M7 10v11H3V10zM7 10l5-8a3 3 0 0 1 3 3v4h5a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7"/>')}${HUMAN ? '<span>Good answer</span>' : ''}</button>`
      + `<button type="button" class="ra" data-act="down" aria-label="Bad reply" aria-pressed="${R.fb === 'down'}">${svg('<path d="M17 14V3h4v11zM17 14l-5 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.4 3H17"/>')}${HUMAN ? '<span>Not right</span>' : ''}</button>` : '')
    + (R.stopped ? '<span class="rstop">Stopped</span>' : '');
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
      if (value === 'down') toast('Thanks. Press Retry for a better answer, or tell Hoola what was wrong.'); }
    catch (e) { toast(e.message, true); }
    return;
  }
  if (act === 'retry') {
    if (TYPING) return toast(`${AV} is working right now. Stop it first.`, true);
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
const WHERE = {browser:'Hoola’s browser · server', pc:'Your PC', email:'Email', payment:'Payment · your approval', network:'Hoola Network', bluetooth:'Home devices', website:'Website'};
function workEvent(p) {
  simpleProgress("work",p);
  const err = p.phase === 'error' || p.phase === 'stopped';
  if (p.id && p.data) STEPS_DATA.set(String(p.id), p.data);   // v0.171 the step's facts join its args in the chip
  $('#stageCap').textContent = err ? (p.phase === 'stopped' ? 'Stopped: ' : 'Problem: ') + (p.error || p.label || '') : (p.label || p.tool || 'Working');
  const site = p.data && (p.data.site || p.data.url) ? ' · ' + String(p.data.site || p.data.url).slice(0, 60) : '';
  $('#stageWhere').textContent = (WHERE[p.scene] || 'Hoola server') + site + (p.phase === 'done' ? ' · done' : p.phase === 'waiting' ? ' · needs your Haan' : '');
  $('#nowline').classList.toggle('err', err);
  // Detailed activity opens only when the user requests it.
}
function live(state) {
  const b = $('#liveBtn'); b.classList.toggle('on', state !== 'idle');
  $('#liveTxt').textContent = state === 'run' ? 'Working' : state === 'ask' ? 'Your approval' : 'Live';
  $('#liveTag').textContent = state === 'run' ? 'Running' : state === 'ask' ? 'Approval required' : 'Idle';
  $('#liveTag').className = 'tag ' + (state === 'ask' ? 'warn' : 'ok');
}

/* ================= cards ================= */
const LABEL = {bazar_approval:'Your approval is required', employee_ask:'Employee question', operator_ask:'The website job needs you', operator_task:'Website job',
  email_draft:'Email draft', hoola_deal:'Hoola Deal', hoola_knock:'Hoola Network', hoola_msg:'Hoola Network message', calendar_event:'Calendar',
  reminders:'Reminders', lists:'Lists', gyaan_sources:'Sources', call_receipt:'Call receipt', procedure:'Learned', memory_saved:'Saved to memory', memory_used:'From memory',
  artifact:'Page', pc_file:'File', photo_made:'Picture', motion:'Reel', video_job:'Video', studio_approval:'AI video cost', gst_return:'GST return',
  payroll_run:'Salary run', google_reconnect:'Reconnect Google', campaign:'WhatsApp campaign', share_ask:'Share this?'};
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
  gallery: () => !!PN, open: item => PN?.open(item),
  library: () => PN ? go('bana') : toast('Creations workspace is not enabled on this server.',true), show: () => showWorkspace(),
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
// v0.243 the research / document workspace (workspace.js) keeps its own view; Create itself is the studio below.
function showWorkspace() {
  VIEW = 'creative'; $$('.view').forEach(x => x.hidden = x.id !== 'v-creative'); drawNav();
  $('#ttl').textContent = '· Creative workspace'; $('#app').classList.remove('drawer');
}
// v0.259 CREATE STUDIO: Create (sidebar, slash command, the home pills for pictures and video) opens the full-screen
// studio; Research and Document pills keep the brief workspace on the same conversation.
CREATE = window.HoolaCreate ? HoolaCreate({api, esc, toast, conv: () => CONV,
  newConv: async () => { const c = await api('POST', '/api/conversations'); await openConv(c.id, false, {noPush: true}); return c.id; },
  avatar: () => ME?.avatar?.gender === 'f' ? '/static/santosh-happy.png' : '/static/santosh-head.png',
  cinema: () => !!CONFIG?.cinema,   // v0.807 Hoola Cinema inside Create
  artcraft: () => !!CONFIG?.artcraft,   // v0.752 ArtCraft in Create (the shilp lane's page door)
  owner: () => !!ME?.arena,   // v0.327 Create > Engines shows the services + server steps only to the owner
  version: (document.querySelector('script[src*="/studio.js"]')?.getAttribute('src') || '').split('v=')[1] || '',
  onClose: () => drawNav()}) : null;
document.addEventListener('click', e => {
  const b=e.target.closest('[data-create]'); if(!b)return;
  if (CREATE && (b.dataset.create === 'image' || b.dataset.create === 'video')) { CREATE.open(b.dataset.create); return; }
  if (!WORKSPACE) return;
  showWorkspace(); WORKSPACE.open(b.dataset.create);
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
function decided(el, ok, text) { el.querySelectorAll('.decrow,.slidec,.acts.dec').forEach(x => x.remove()); el.classList.remove('ask'); el.insertAdjacentHTML('beforeend', `<div class="${ok ? 'okn' : 'badc'}" style="font-weight:800">${esc(text)}</div>`); refreshPending(); }

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
function decisionRow(el, {yes, no, yesLabel = 'Slide for Haan', noLabel = 'Mana'}) {
  if (HUMAN) {   // v0.743 plain English on every approval, and the promise said once
    if (yesLabel === 'Slide for Haan') yesLabel = 'Slide to approve';
    if (noLabel === 'Mana') noLabel = 'Not now';
    el.insertAdjacentHTML('beforeend', '<p class="hxnote">Nothing happens until you approve.</p>');
  }
  const s = slider(yesLabel, async () => { try { await yes(); } catch (e) { toast(e.message, true); throw e; } });
  const a = document.createElement('div'); a.className = 'acts dec';
  a.innerHTML = `<button class="btn soft" type="button">${esc(noLabel)}</button>`;
  a.firstChild.addEventListener('click', async () => { try { await no(); } catch (e) { toast(e.message, true); } });
  const row = document.createElement('div'); row.className = 'decrow'; row.append(s, a);   // v0.222 slider + Mana on one row
  el.classList.add('ask'); el.append(row);
}
const fingerprintMsg = 'This card moves money: Haan needs your phone’s fingerprint. Open this card in the Hoola app to approve.';

// v0.228 the four-part final report of a long job: what was done / what was made / what is left / her part
function goalReport(r) {
  if (!r || typeof r !== 'object') return '';
  const part = (h, xs) => (Array.isArray(xs) && xs.length) ? `<div class="grep"><small>${h}</small>` +
    xs.slice(0, 10).map(x => { const u = safeLink(x); return `<div>\u2022 ${u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(x)}</a>` : esc(x)}</div>`; }).join('') + `</div>` : '';
  return `<div class="greport">` + (r.summary ? `<div class="note">${esc(r.summary)}</div>` : '') +
    part(HUMAN ? 'What was done' : '✅ What was done', r.hua) + part(HUMAN ? 'What was made' : '📎 What was made', r.bana) +
    part(HUMAN ? 'What is left' : '⏳ What is left', r.baaki) + (r.aapka ? part(HUMAN ? 'Your part' : '👉 Your part', [r.aapka]) : '') + `</div>`;
}

/* v0.725 PAGE CARD (owner: "CHECK THE INTERACTIVE WEB UI BAR -- DONT HAVE A TIMING AND WORK IN PROGRESS" -> the
   approved preview -> GO): one card per page, drawn in all its states from the server's real fields. While it is made:
   a live clock from started_at (server clock, so a skewed PC clock never shows a wrong number), the usual time, the
   step the builder is really on (writing / checking), a moving bar that shows work and never a made-up percentage,
   and Stop. Ready: a small picture, what the page holds, version, how long it took, Share + Open. Not made: the
   reason in plain words + Try again. */
const PAGE_STEPS = [['read', 'Brief read'], ['writing', 'Writing the page'], ['checking', 'Checking it opens'], ['done', 'Ready']];
function pageClock(s) { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function pageCard(p, live) {
  const el = cardShell('artifact', p); el.className = 'cd hmpage';
  clearInterval(el._tick);
  const st = p.status || 'building', stage = p.stage || (st === 'building' ? 'writing' : '');
  const building = st === 'building', failed = st === 'failed';
  const stopped = stage === 'stopped', kept = st === 'ready' && (stopped || stage === 'failed') && Number(p.version) > 0;
  const title = esc(p.title || 'Page');
  const pill = building ? '<span class="hp-pill work"><span class="d"></span>Building</span>'
    : failed ? `<span class="hp-pill bad"><span class="d"></span>${stopped ? 'Stopped' : 'Not made'}</span>`
    : '<span class="hp-pill ok"><span class="d"></span>Ready</span>';
  const thumb = `<div class="hp-thumb${building ? ' live' : ''}" aria-hidden="true"><i></i><i></i><i></i>${st === 'ready' ? '<b></b><b></b><b></b>' : ''}</div>`;
  const now0 = Date.parse(p.now || '') || Date.now(), skew = now0 - Date.now();
  const t0 = Date.parse(p.started_at || '') || 0;
  const took = p.build_s != null ? pageClock(p.build_s) : '';
  let sub, acts = '', below = '';
  if (building) {
    const cur = Math.max(1, PAGE_STEPS.findIndex(x => x[0] === stage));
    sub = `<span data-step>${esc(PAGE_STEPS[cur][1])}</span><span class="sep">·</span><span class="hp-clock" data-clock>${t0 ? pageClock((Date.now() + skew - t0) / 1000) : '0:00'}</span><span class="sep">·</span><span>${p.draft ? `${Number(p.chars || 0).toLocaleString('en-IN')} characters` : 'usually 20–90 s'}</span>`;
    acts = p.draft ? '' : '<button class="btn soft" type="button" data-stop>Stop</button>';
    below = '<div class="hp-bar" aria-hidden="true"><span></span></div><div class="hp-steps">' + PAGE_STEPS.map((x, i) =>
      `<span class="hp-st${i < cur ? ' done' : i === cur ? ' now' : ''}"><span class="ic">${i < cur ? '✓' : ''}</span>${esc(x[1])}</span>`).join('') + '</div>';
  } else if (failed) {
    sub = `<span>${esc(p.error || 'The page could not be made.')}${took ? ` After <span class="hp-clock">${took}</span>.` : ''}</span>`;
    acts = stopped ? '' : '<button class="btn" type="button" data-retry>Try again</button>';
  } else {
    sub = `<span>${esc(p.summary || 'Open it to use the page.')}</span>`;
    acts = '<button class="btn soft" type="button" data-share>Share</button><button class="btn" type="button" data-open>Open</button>';
    below = `<div class="hp-foot"><span>Version ${Number(p.version) || 1}</span>${took ? `<span class="sep">·</span><span>made in <span class="hp-clock">${took}</span></span>` : ''}`
      + (kept ? `<span class="sep">·</span><span>${esc(stopped ? 'The new version was stopped; this one stays.' : 'The new version could not be made; this one stays.')}</span>` : '') + '</div>';
  }
  el.setAttribute('aria-label', `Page ${p.title || ''}: ${building ? 'being made' : failed ? 'not made' : 'ready'}`);
  el.innerHTML = `<div class="hp-top">${thumb}<div class="hp-meta"><div class="hp-r1"><span class="hp-title">${title}</span>${pill}</div>`
    + `<div class="hp-sub"${building ? ' aria-live="polite"' : ''}>${sub}</div></div><div class="hp-acts">${acts}</div></div>${below}`;
  if (building && t0) {
    const c = el.querySelector('[data-clock]');
    el._tick = setInterval(() => { if (!el.isConnected) return clearInterval(el._tick); c.textContent = pageClock((Date.now() + skew - t0) / 1000); }, 1000);
  }
  el.querySelector('[data-stop]')?.addEventListener('click', async e => {
    e.currentTarget.disabled = true; e.currentTarget.textContent = 'Stopping…';
    try { await api('POST', `/api/artifacts/${encodeURIComponent(p.id)}/stop`); } catch (er) { toast(er.message, true); }
  });
  el.querySelector('[data-retry]')?.addEventListener('click', () => {
    msg.value = `Make the page "${p.title || 'page'}" again`; msg.dispatchEvent(new Event('input')); composer.requestSubmit();
  });
  el.querySelector('[data-open]')?.addEventListener('click', () => { const it = PN?.itemOf('artifact', p); if (it) PN.open(it); });
  el.querySelector('[data-share]')?.addEventListener('click', async () => {
    try {
      const r = await api('POST', `/api/artifacts/${encodeURIComponent(p.id)}/share`, {on: true});
      try { await navigator.clipboard.writeText(r.share_url); toast('Share link copied.'); } catch (er) { toast('Share link: ' + r.share_url); }
    } catch (er) { toast(er.message, true); }
  });
  if (live && st === 'ready') PN?.update('artifact', p);
  scrollDown();
}

/* parity Phase 6: while the chat model writes a page in its tool call, its card shows Writing + the size so far; the
   stored version's own card takes its place (an edit of an existing page updates that page's card in place). */
const DRAFT_T0 = new Map();
function draftCard(p) {
  const key = p.artifact_id || ('draft:' + p.turn + ':' + p.idx);
  if (!DRAFT_T0.has(key)) DRAFT_T0.set(key, new Date().toISOString());
  pageCard({id: key, draft: true, status: 'building', stage: 'writing', title: p.title || 'Page', chars: p.chars,
            started_at: DRAFT_T0.get(key), now: new Date().toISOString()}, false);
}
function endDraftCards(p) {
  DRAFT_T0.delete(p.id);
  if (p.status === 'ready') for (const [k, el] of [...CARDS]) if (k.startsWith('artifact:draft:')) { el.remove(); CARDS.delete(k); DRAFT_T0.delete(k.slice(9)); }
}
function renderCard(kind, p, at, live) {
  if (kind === 'artifact' && p && p.id && !p.draft) endDraftCards(p);
  if (kind === 'artifact' && p && p.id) { pageCard(p, live); return; }
  if(PROGRESS_POLICY.quiet(kind,p)){if(live)simpleProgress(kind,p);return;}
  if (B && B.kinds.has(kind)) { const el = cardShell(kind, p); B.card(kind, p, el, !!live); scrollDown(); return; }
  if (RESULTS?.kinds.has(kind) && PN?.itemOf(kind, p) && (kind !== 'artifact' || p.status === 'ready')) {
    const el = cardShell(kind, p); RESULTS.card(kind, p, el); if (live) PN.update(kind, p); scrollDown(); return;
  }
  if (kind === 'goal') {   // v0.186 lamba kaam pakka: live checklist, one card per goal id
    // v0.716 NAYA ROOP (her pick 5): drawn as Claude's to-do list - a Plan card with the mark, n of m, and each step
    // ticking itself off (spinner while current, a drawn tick when done). HEAD stays the job's state for readers.
    const el = cardShell(kind, p); el.classList.add('hmplan');
    const st = p.status || 'working';
    const HEAD = {working: 'LONG JOB RUNNING', done: 'LONG JOB DONE', blocked: 'WAITING FOR YOUR ANSWER',
                  failed: 'LONG JOB INCOMPLETE', stopped: 'LONG JOB STOPPED'};
    const SAY = {working: 'Working', done: 'Done', blocked: 'Waiting for you', failed: 'Not finished', stopped: 'Stopped'};
    const steps = Array.isArray(p.steps) ? p.steps : [];
    const done = p.done != null ? p.done : steps.filter(x => x.state === 'done').length;
    const total = p.total != null ? p.total : steps.length;
    const box = {done: `<span class="b hm-tick">${HM_TICK}</span>`, current: '<span class="b"><span class="hm-spin"></span></span>',
                 failed: '<span class="b">!</span>', skipped: '<span class="b">–</span>', pending: '<span class="b"><span class="r0"></span></span>'};
    const mark = window.HoolaMark ? (st === 'working' && !HUMAN ? HoolaMark.think(16) : `<span style="width:16px;height:16px;display:inline-block">${HoolaMark.svg()}</span>`) : '';
    el.setAttribute('aria-label', HEAD[st] || HEAD.working);
    el.innerHTML = `<div class="ph">${mark}<span>Plan</span><span class="pc">${esc(SAY[st] || SAY.working)}${total ? ' · ' + done + ' of ' + total : ''}</span></div>` +
      `<div class="pt">${esc(p.title || p.goal || 'Long job')}</div>` +
      `<ol>` + steps.slice(0, 15).map((x, i) => `<li class="${esc(x.state || 'pending')}${x.state === 'done' && el._done?.has(i) ? ' old' : ''}">${box[x.state] || box.pending}<span>${esc(x.text || '')}` +
        (x.note ? ` <small>(${esc(x.note)})</small>` : '') + `</span></li>`).join('') + `</ol>` +
      (p.reason && st !== 'working' && !p.report ? `<div class="note">${esc(p.reason)}</div>` : '') +
      goalReport(p.report) +
      (st === 'blocked' && p.hold === 'limit' ? `<div class="row" style="margin-top:8px"><button class="btn" type="button" data-goal-go>Continue</button></div>` : '');
    el._done = new Set(steps.slice(0, 15).map((x, i) => x.state === 'done' ? i : -1).filter(i => i >= 0));   // a tick draws once
    const go = el.querySelector('[data-goal-go]');   // v0.223 the budget ran out: the job ASKS, her tap carries it on
    if (go) go.onclick = async () => {
      go.disabled = true;
      try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/goal/continue`); go.textContent = 'Continuing…'; }
      catch (e) { go.disabled = false; go.textContent = 'Try again'; }
    };
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
  if (kind === 'compact') {   // v0.242 FULL CLAUDE MODE Phase 2: older messages folded into one checkpoint summary
    const el = document.createElement('details'); el.className = 'note';
    const n = Number(p.exchanges || 0);
    el.innerHTML = `<summary>🗜 Older messages summarised${n ? ` (${n} exchanges)` : ''} · ${esc(String(p.before_pct ?? '?'))}% → ${esc(String(p.after_pct ?? '?'))}% full · View</summary><div class="faint" style="white-space:pre-wrap;font-size:13px;margin-top:6px">${esc(p.preview || '')}…</div>`;
    let loaded = false;
    el.addEventListener('toggle', async () => {
      if (!el.open || loaded) return; loaded = true;
      try { const r = await api('GET', `/api/conversations/${encodeURIComponent(CONV)}/compact`);
            if (r.active?.summary) el.querySelector('div').textContent = r.active.summary; }
      catch (e) { loaded = false; }
    });
    turn().bd.appendChild(el); return;
  }
  if (kind === 'memory_saved' || kind === 'procedure') {
    const el = document.createElement('div'); el.className = 'note'; el.textContent = (kind === 'memory_saved' ? (HUMAN ? 'Saved to memory: ' : '📌 Saved to memory: ') : (HUMAN ? 'Learned: ' : '🎓 Learned: ')) + (p.text || p.title || ''); turn().bd.appendChild(el); return;
  }
  // v0.612 YAAD SE (Grok's "which memory did this use"): the memory this reply leaned on, each one forgettable
  if (kind === 'memory_used') {
    const items = Array.isArray(p.items) ? p.items : [];
    if (!items.length) return;
    const el = document.createElement('details'); el.className = 'note memused';
    const labels = [...new Set(items.map(i => i.label || 'Memory'))].join(' · ');
    el.innerHTML = `<summary>📖 From memory: ${esc(labels)}</summary>` + items.map((it, n) =>
      `<div class="mu" style="display:flex;gap:8px;align-items:flex-start;margin-top:6px;font-size:13px"><span style="flex:1"><b>${esc(it.label || '')}</b> — <span class="faint">${esc(it.text || '')}</span></span><button type="button" class="btn soft" data-mu="${n}" style="padding:2px 8px">Forget</button></div>`).join('');
    el.addEventListener('click', async e => {
      const b = e.target.closest('[data-mu]'); if (!b) return;
      const it = items[Number(b.dataset.mu)]; if (!it) return;
      const ask = it.source === 'chat' ? 'Stop using this chat as memory? The chat itself stays in your list.' : 'Forget this?';
      if (!confirm(ask)) return;
      try { await api('POST', '/api/memory/unremember', {source: it.source, id: it.id, conversation_id: it.conversation_id || '', text: it.text || ''});
            b.closest('.mu').remove(); if (!el.querySelector('.mu')) el.remove(); }
      catch (er) { toast(er.message, true); }
    });
    turn().bd.appendChild(el); return;
  }
  const el = cardShell(kind, p);
  switch (kind) {
    // v0.449 Phase 2 NAKSHA DIKHE: places as readable cards instead of a wall of addresses.
    // Deliberately NO map: Google's terms allow Places content with no map (SST 14.1) and forbid it on a
    // non-Google map (SST 14.2 / ToS 3.2.3(e)), so free tiles here would be a licence breach. Attribution is
    // required wherever this content is shown, with or without a map (ToS 3.2.2(b)).
    case 'maps_places': {
      const ps = Array.isArray(p.places) ? p.places : [];
      const bits = x => [x.type, x.distance_km != null ? x.distance_km + ' km' : '',
                         x.rating != null ? '\u2605 ' + x.rating + (x.reviews ? ' (' + x.reviews + ')' : '') : '',
                         x.open_now === true ? 'Khula hai' : x.open_now === false ? 'Band hai' : '',
                         x.status && x.status !== 'OPERATIONAL' ? x.status.replace(/_/g, ' ').toLowerCase() : '']
                        .filter(Boolean).join(' \u00b7 ');
      el.innerHTML = head(p.title || 'Jagahein', ps.length ? String(ps.length) : '', 'v') +
        `<div class="bd">` + (p.near ? `<div class="faint" style="font-size:12.5px">${esc(p.near)} ke aas-paas</div>` : '') +
        ps.map(x => {
          const ml = safeLink(x.maps_link), web = safeLink(x.website);
          return `<div class="ln" style="display:block;padding:7px 0">` +
            `<b>${esc(x.name || '')}</b>` +
            (bits(x) ? `<div class="faint" style="font-size:12.5px">${esc(bits(x))}</div>` : '') +
            (x.address ? `<div style="font-size:13px">${esc(x.address)}</div>` : '') +
            (Array.isArray(x.hours) && x.hours.length ? `<div class="faint" style="font-size:12px">${esc(x.hours.join(' \u00b7 '))}</div>` : '') +
            `<div class="row" style="gap:10px;margin-top:3px;font-size:12.5px">` +
            (x.phone ? `<a href="tel:${esc(String(x.phone).replace(/[^\d+]/g, ''))}">${esc(x.phone)}</a>` : '') +
            (web ? `<a href="${esc(web)}" target="_blank" rel="noopener noreferrer">Website \u2197</a>` : '') +
            (ml ? `<a href="${esc(ml)}" target="_blank" rel="noopener noreferrer">Google Maps \u2197</a>` : '') +
            `</div></div>`;
        }).join('') +
        `<div class="faint" style="font-size:11.5px;margin-top:6px">${esc(p.attribution || 'Google')}` +
        (p.cost_inr ? ` \u00b7 \u20b9${esc(String(p.cost_inr))}` : (p.cost_inr === 0 ? ' \u00b7 free' : '')) +
        `</div></div>`;
      break; }
    case 'bazar_approval': {
      el.innerHTML = head(p.title || 'Your approval is required', p.money ? 'paisa' : 'Your approval', p.money ? 'bad' : 'warn')
        + (p.amount ? `<div class="big">${esc(p.amount)}</div>` : '') + (p.payee ? `<div class="faint" style="font-size:13px">${esc(p.payee)}</div>` : '')
        + (p.items || []).map(i => `<div class="ln"><span>${esc(i.name)}</span><b>${esc(i.price)}</b></div>`).join('')
        + ((p.disclosures || []).length ? `<div class="kvg">${p.disclosures.map(i => `<span>${esc(i.label)}<b>${esc(i.value)}</b></span>`).join('')}</div>` : '')
        + (p.voice_ok && !p.money ? `<p class="faint" style="font-size:12.5px">You can also approve by voice or in chat — say "haan karo" or "approve".</p>` : '');
      if (p.status && p.status !== 'pending') { decided(el, p.status === 'approved', p.status === 'approved' ? '✓ Approved' : '✕ ' + p.status); break; }
      decisionRow(el, {
        yes: async () => { try { await api('POST', `/api/bazar/approvals/${encodeURIComponent(p.id)}`, {decision: 'approve'}); decided(el, true, '✓ Approved'); }
                           catch (e) { if (e.status === 428) { decided(el, false, '📱 ' + fingerprintMsg); return; } throw e; } },
        no: async () => { await api('POST', `/api/bazar/approvals/${encodeURIComponent(p.id)}`, {decision: 'reject'}); decided(el, false, '✕ Declined'); }});
      break; }
    case 'employee_ask': {
      el.innerHTML = head(p.what || 'Employee question', p.duty_label || 'Employee', 'warn') + `<div class="kv">${[['Who', p.who], ['Why', p.why], ['What', p.detail]].filter(([, v]) => v).map(([k, v]) => `<span>${k}</span><b>${esc(v)}</b>`).join('')}</div>`;
      const empDone = st => st === 'done' ? '✓ Done' : st === 'declined' ? '✕ Declined' : st === 'expired' ? 'Expired' : '✕ Could not finish' + (p.result ? ': ' + String(p.result).slice(0, 140) : '');
      if (p.status && p.status !== 'pending') { decided(el, p.status === 'done', empDone(p.status)); break; }
      decisionRow(el, {
        yes: async () => { const r = await api('POST', `/api/employee/asks/${encodeURIComponent(p.id)}`, {approve: true}); p.result = r.result; decided(el, r.status === 'done', empDone(r.status)); },
        no: async () => { await api('POST', `/api/employee/asks/${encodeURIComponent(p.id)}`, {approve: false}); decided(el, false, '✕ Declined'); }});
      break; }
    case 'operator_ask': {
      const k = p.kind || 'approve', typed = ['otp', 'secret', 'captcha', 'question'].includes(k);
      el.innerHTML = head(p.reason || 'The website needs you', p.site || 'Hoola’s browser', 'warn')
        + (k === 'payment' ? `<p class="muted" style="font-size:13.5px">Payment step: Hoola never presses this. Open the live view in the phone app and press it yourself.</p>` : '')
        + (k === 'captcha' ? `<img class="cap" alt="CAPTCHA" hidden>` + (p.suggested_answer ? `<div class="faint" style="font-size:13px">Hoola read: <b>${esc(p.suggested_answer)}</b></div>` : '') : '')
        + (typed ? `<input class="fld" type="${k === 'question' ? 'text' : 'password'}" inputmode="${k === 'otp' ? 'numeric' : 'text'}" autocomplete="one-time-code" placeholder="${k === 'otp' ? 'OTP' : k === 'captcha' ? 'CAPTCHA' : 'Jawab'}" aria-label="Answer">
            <p class="faint" style="font-size:12.5px">This goes only into the page’s box. It is never shown to the chat, memory or the AI.</p>` : '');
      if (p.status && p.status !== 'pending') { decided(el, true, '✓ Answered'); break; }
      if (k === 'captcha') api('GET', `/api/operator/requests/${encodeURIComponent(p.id)}/captcha`, undefined, {raw: true}).then(r => r.blob()).then(b => { const i = el.querySelector('img.cap'); if (i) { i.src = URL.createObjectURL(b); i.hidden = false; } }).catch(() => {});
      if (k === 'payment') break;
      decisionRow(el, {yesLabel: typed ? 'Fill the page' : 'Slide for Haan',
        yes: async () => { const inp = el.querySelector('input.fld'); const answer = inp ? inp.value.trim() || (k === 'captcha' ? p.suggested_answer || '' : '') : '';
          if (typed && !answer) { toast('Type the answer first.', true); throw new Error('empty'); }
          await api('POST', `/api/operator/requests/${encodeURIComponent(p.id)}`, {status: 'approved', answer}); if (inp) inp.value = ''; decided(el, true, typed ? '✓ Filled in the box (••••)' : '✓ Approved'); },
        no: async () => { await api('POST', `/api/operator/requests/${encodeURIComponent(p.id)}`, {status: 'rejected', answer: ''}); decided(el, false, '✕ Declined'); }});
      break; }
    case 'email_draft': {
      el.innerHTML = head(p.subject || 'Email draft', p.status === 'pending' ? 'Waiting to send' : p.status, p.status === 'sent' ? 'ok' : 'warn')
        + `<div class="kv"><span>To</span><b>${esc(p.to)}</b>${p.cc ? `<span>Cc</span><b>${esc(p.cc)}</b>` : ''}${p.send_at_label ? `<span>Kab</span><b>${esc(p.send_at_label)}</b>` : ''}</div>`
        + `<textarea aria-label="Email body">${esc(p.body)}</textarea>` + ((p.attachments || []).length ? `<div class="srcs">${p.attachments.map(a => `<span class="chip">📎 ${esc(a.name)}</span>`).join('')}</div>` : '');
      if (!['pending', 'failed'].includes(p.status)) { el.querySelector('textarea').disabled = true; break; }
      const a = document.createElement('div'); a.className = 'acts dec';
      a.innerHTML = '<button class="btn go" type="button" style="padding:9px 18px;font-size:13px">Send</button><button class="btn soft" type="button">Cancel</button>';
      a.children[0].addEventListener('click', async () => { try { const body = el.querySelector('textarea').value; await api('POST', `/api/emails/${encodeURIComponent(p.id)}/send`, body !== p.body ? {body} : {}); decided(el, true, '✓ Sent'); } catch (e) { toast(e.message, true); } });
      a.children[1].addEventListener('click', async () => { try { await api('POST', `/api/emails/${encodeURIComponent(p.id)}/cancel`); decided(el, false, '✕ Cancel'); } catch (e) { toast(e.message, true); } });
      el.classList.add('ask'); el.appendChild(a); break; }
    case 'share_ask': {   // Share from the panel: nothing is public until she says Haan here
      const own = typeof p.url === 'string' && p.url.startsWith(location.origin + '/') ? p.url : '';
      const url = p.status === 'approved' ? (safeLink(p.url) || own) : '';
      el.innerHTML = head(p.title || 'Share this?', p.status === 'pending' ? 'Your approval' : p.status === 'approved' ? 'shared' : 'declined', p.status === 'pending' ? 'warn' : 'v')
        + `<div class="kv"><span>What</span><b>${esc(p.what || '')}</b></div><p style="font-size:14px">${esc(p.say || '')}</p>`
        + (url ? `<div class="acts"><input class="fld" readonly value="${esc(url)}" aria-label="Share link"><button class="btn soft" type="button" data-copy-link>Copy link</button></div>` : '');
      el.querySelector('[data-copy-link]')?.addEventListener('click', async e => { if (await copyText(url)) e.target.textContent = 'Copied ✓'; });
      if (p.status !== 'pending') break;
      decisionRow(el, {yesLabel: 'Slide to share',
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
        + (pit ? `<div class="acts"><button class="btn go" type="button" data-pn>Open</button></div>` : '')
        + (link ? `<div class="acts"><a class="btn soft" href="${esc(link)}" target="_blank" rel="noopener noreferrer">Open</a></div>` : '')
        + (money ? `<p class="faint" style="font-size:12.5px">Approve this card in the Hoola app (fingerprint or the app’s own screen).</p>` : '');
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
      if (ev.conv && ev.conv !== conv) return;   // v0.227.4 another chat's card never lands here
      if (ev.kind === 'resync') { setTimeout(() => openConv(conv), 0); return; }
      if (!ev.live) LAST = ev.id;
      onEvent(ev);
    }});
  STREAM = s;
}
function onEvent(ev) {
  const p = {...(ev.payload || {})};
    if (p.role === 'user' && typeof p.text === 'string') p.text = stripHints(p.text);
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
      meter();               // v0.244 the meter moves after every reply
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
      if (p.source === 'greeting') return;        // v0.234 the console never draws the old greeting (the home greets), like Claude
      if (p.ack) { if (TYPING) simpleProgress('ack', p); return; }        // v0.227.3 the 5-second comfort line: one progress row, never a second avatar
      landing(false);
      if (p.source === 'quick') {   // v0.173 the quick lane answered beside the running kaam: flip the receipt
        const qr = [...RCPTS].reverse().find(([, R]) => R.state === 'queue');
        if (qr) receiptUpdate(qr[0], 'quick');
      }
      if (p.turn && window.HoolaStream) { replyMessage(p, false, ev.id, ev.at); const R = REPLIES.get(p.turn); if (R?.done) drawActs(R); return; }
      hoolaText(p.text || '', p.source, ev.id, ev.at); return;
    case 'typing': typing(!!p.on); return;
    case 'step': landing(false); stepEvent(p); return;
    case 'ledger': ledgerLine(p.line); return;   // parity Phase 5: the receipt lives in the steps fold
    case 'work': workEvent(p); return;
    case 'say': {
      simpleProgress('say',p);
      // The backend's real result summary is transient progress, never a generic result card.
      $('#stageCap').textContent = p.text || 'Working…'; return;
    }
    case 'think': landing(false); thinkEvent(p); return;   // v0.171 the model's reasoning, live in its card
    case 'artifact_draft': landing(false); draftCard(p); PN?.draft?.(p); return;   // parity Phase 6: a page being written
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
    if (p.role === 'user' && typeof p.text === 'string') p.text = stripHints(p.text);
    if (ev.kind === 'message') {
      flushStepBuf();
      if (p.role === 'user') userBubble(p.text, p.files, ev.id, null, ev.at);
      else if (!any || p.source === 'greeting') continue;   // v0.234 no greeting row in the thread
      else if (p.turn && window.HoolaStream) { replyMessage(p, true, ev.id, ev.at); if (SINK === col) LAST_TURN = p.turn; }
      else hoolaText(p.text || '', p.source, ev.id, ev.at);
    }
    else if (ev.kind === 'step') continue;   // v0.171 the transcript keeps what each turn did (steps=1)
    else if (ev.kind === 'ledger') { flushStepBuf(); ledgerLine(p.line, SINK, null); }   // parity Phase 5
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
  msg.value = FLOW_TEXT || store.get('hoola.draft.' + id) || '';   // v0.173 her unfinished words come back with the chat (v0.777: text handed over from Hoola Flow first)
  if (FLOW_TEXT) { FLOW_TEXT = ''; setTimeout(() => { msg.dispatchEvent(new Event('input')); msg.focus(); }, 0); }
  msg.style.height = 'auto'; msg.style.height = Math.min(200, msg.scrollHeight) + 'px';
  $('#sendBtn').disabled = !msg.value.trim() && !FILES.length;
  // skeleton rows while the chat loads (not a spinner)
  col.innerHTML = '<div class="skel-chat" aria-hidden="true"><i class="skel r"></i><i class="skel l"></i><i class="skel l s"></i><i class="skel r s"></i><i class="skel l"></i></div>';
  // the chat in order from the server: messages and each card once where it happened (latest state)
  let tl = {events: [], last_event_id: 0};
  try { tl = await api('GET', `/api/conversations/${encodeURIComponent(id)}/timeline?limit=${fresh ? 10 : 80}&steps=1&own=1`); }
  catch (e) { LOADING = false; col.innerHTML = ''; if (e.status === 404 && opts.fallback) return opts.fallback(); toast(e.message, true); }
  if (CONV !== id) return;
  col.innerHTML = '';
  const any = tl.events.some(e => e.kind === 'message' && e.payload?.source !== 'greeting')   // v0.231 only the greeting = home
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
      const s = r.status === 200 && CONV === id ? await r.json() : null;
      if (s?.turn) {
        const R = reply(s.turn);
        R.done = false; R.acts?.remove(); R.seq = s.seq; LAST_TURN = s.turn; landing(false);
        if (s.think) thinkEvent({turn: s.turn, seg: s.seg, text: s.think});   // v0.171 mid-thought reload: the card reopens
        const S = seg(R, s.seg); S.pacer.reset(); S.pacer.push(s.text || ''); S.pacer.flush();
        TURN = R.t; $('#stopBtn').hidden = false; live('run');
      }
    } catch {}
  }
  scrollDown(true); drawHead();
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
    const tl = await api('GET', `/api/conversations/${encodeURIComponent(id)}/timeline?limit=60&before=${BEFORE}&steps=1&own=1`);
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
  if (!el) return toast('That message is not in this chat any more (it may be in another version).');
  STICK = false; el.scrollIntoView({block: 'center', behavior: SMOOTH()});
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
  const bar = document.createElement('div'); bar.className = 'fbar gl'; bar.setAttribute('role', 'search'); bar.setAttribute('aria-label', 'Find in this chat');
  bar.innerHTML = `<span class="fic" aria-hidden="true">⌕</span><input placeholder="Find in this chat…" aria-label="Find in this chat" autocomplete="off"><span class="fcount" aria-live="polite"></span>`
    + `<button type="button" class="fb" data-d="-1" aria-label="Previous match (Shift+Enter)">↑</button>`
    + `<button type="button" class="fb" data-d="1" aria-label="Next match (Enter)">↓</button>`
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
$('#v-chat').insertAdjacentHTML('beforeend', '<div class="jrail" id="jrail" hidden aria-label="Jump to a day"></div>');
$('#jrail').addEventListener('click', e => {
  const b = e.target.closest('b[data-top]'); if (!b) return;
  thread.scrollTo({top: +b.dataset.top - 76, behavior: SMOOTH()}); STICK = false;
});
$('#jrail').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { const b = e.target.closest('b[data-top]'); if (b) { e.preventDefault(); thread.scrollTo({top: +b.dataset.top - 76, behavior: SMOOTH()}); } } });
addEventListener('resize', drawRail);

/* ================= one stream for all her chats (CHAT_SESSIONS; on with CONSOLE_V2) ================= */
// kinds that belong to their own chat only (events.LOCAL_KINDS). v0.227.4 a card of another chat never lands in the open chat;
// that chat gets the unread dot instead (Today still counts every approval)
const LOCAL = new Set(['typing', 'step', 'work', 'log', 'reply_start', 'delta', 'delta_reset', 'reply_end', 'think', 'say', 'artifact_draft', 'message', 'upload',
  'reminders', 'routines', 'lists', 'email_sent', 'hoola_update', 'galla', 'mshop', 'office', 'employee', 'darzi_order',
  'phonedoc_open', 'phonedoc_check', 'device_action', 'device_action_result', 'home_device', 'bt_request', 'bazar_open',
  'bazar_link', 'gyaan_sources', 'memory_saved', 'memory_used', 'procedure', 'compact', 'open', 'link', 'call_receipt', 'speaker', 'voice',
  'maps_places', 'ledger',
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
      if (ev.kind === 'message' && ev.payload?.role === 'assistant' && ev.payload?.source !== 'greeting') CH.unread(c);
      if (!ev.live && !LOCAL.has(ev.kind) && !PROGRESS_POLICY.quiet(ev.kind,ev.payload)) CH.unread(c);   // v0.227.4 stays in its own chat
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
  ['new', 'New chat', 'start a new chat', () => $('#newChat').click()],
  ['incognito', 'Incognito chat', 'Hoola remembers nothing from it', () => newIncognito()],
  ['search', 'Search chats', 'the Ctrl K search', () => CH?.openSearch()],
  ['export', 'Export chat', 'Markdown or JSON file', () => $('#exportBtn').click()],
  ['stop', 'Stop', 'stop the running job', () => $('#stopBtn').click()],
  ['today', 'Today', 'your day', () => go('aaj')],
  ['tools', 'All tools', 'everything Hoola can do', () => go('kaam')],
  ['call', 'Voice call', 'live voice call', () => go('baat')],
  ['account', 'Account', 'profile, password, AI spend', () => go('main')],
  ['skills', 'Learned Skills', 'what your Hoola knows', () => go('skills')],   // v0.481
  ['connectors', 'Connectors', 'link Slack, Notion, Tally and 1,600+ apps', () => go('connectors')],   // v0.774
  ['appearance', 'Appearance', 'Light, Dark or System', () => { go('main'); setTimeout(() => $('#appearance')?.scrollIntoView({block: 'center', behavior: SMOOTH()}), 60); }],
  ['light', 'Light theme', 'switch to light', () => TH?.setTheme('light')],
  ['dark', 'Dark theme', 'switch to dark', () => TH?.setTheme('dark')],
  ['system', 'System theme', 'follow the computer', () => TH?.setTheme('system')],
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
    const g = $('#gauge'), sp = $('#spend');
    if (!m.limit_usd) { g.hidden = true; sp.hidden = true; return; }   // no limit set: nothing to gauge
    const pct = Math.max(1.5, Math.min(100, m.pct || 0)), cls = m.over ? ' over' : m.warn ? ' warn' : '';
    const money = (usd, inr) => inr != null ? '₹' + Math.round(inr).toLocaleString('en-IN') : '$' + usd.toFixed(2);
    const tip = `This month's AI spend: ${money(m.spent_usd, m.spent_inr)} / ${money(m.limit_usd, m.limit_inr)} (${Math.round(m.pct)}%)${m.over ? ' — over the limit' : ''}`;
    g.hidden = false; g.className = 'gauge' + cls; g.querySelector('i').style.width = pct + '%'; g.title = tip;
    // v0.222 R2: the same numbers as a card at the bottom of the sidebar
    sp.hidden = false; sp.className = 'spend' + cls; sp.title = tip;
    $('#spMonth').textContent = new Date().toLocaleString('en-IN', {month: 'short'});
    $('#spAmt').textContent = HUMAN ? `${money(m.spent_usd, m.spent_inr)} of ${money(m.limit_usd, m.limit_inr)}` : `${money(m.spent_usd, m.spent_inr)} / ${money(m.limit_usd, m.limit_inr)}`;
    if (HUMAN) sp.querySelector('.sp1 span').textContent = 'AI spend this month';
    sp.querySelector('.spbar i').style.width = pct + '%';
  } catch {}
}
const INLINE_MAX = 30000;   // v0.227.2 the server takes 32000 (room for the console hints); longer = an attached file
composer.addEventListener('submit', async e => {
  e.preventDefault(); let text = msg.value.trim(); if ((!text && !FILES.length) || !CONV) return;
  if (FILES.some(f => f.err)) return toast('A file did not upload. Tap Retry on it, or remove it.', true);
  if (FILES.some(f => !f.file_id)) return toast('File upload in progress…');
  if (text.length > INLINE_MAX) {   // v0.227.2 very long text rides as an attached .txt file, like a pasted-text chip
    if (FILES.length >= 6) return toast('This text is very long. Remove a file so it can go as an attachment.', true);
    const origin0 = CONV, pasted = new File([text], `pasted-text-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.txt`, {type: 'text/plain'});
    msg.value = ''; await addFiles([pasted]);
    if (CONV !== origin0 || !FILES.some(f => f.name === pasted.name && f.file_id)) { msg.value = text; return; }
    toast(`Long text (${text.length.toLocaleString('en-IN')} characters) attached as ${pasted.name}.`);
    text = 'Please read the attached text file (my full message) and follow it.';
  }
  const origin = CONV, auth = TOKEN; clearTimeout(DRAFT_T);
  const files = FILES.splice(0); drawFiles(); msg.value = ''; msg.style.height = 'auto'; $('#sendBtn').disabled = true;
  store.del('hoola.draft.' + origin);   // v0.173 the draft went out with the message
  const body = {text: text || FILE_ONLY, client_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())), files: files.map(f => f.file_id), hints: takeHints()};
  landing(false); const bbl = userBubble(body.text, files, null, body.client_id);
  if (TYPING) receipt(bbl, body.client_id, 'queue');   // v0.173 steering: she sees it is queued and can take it back
  USER_ECHO.push(body.text);
  for (let i = 0; i < 3; i++) {
    if (!auth || TOKEN !== auth) return;
    try { await api('POST', `/api/conversations/${encodeURIComponent(origin)}/messages`, body); loadRecents(); return; }
    catch (er) { if (i === 2 || (er.status >= 400 && er.status < 500)) { toast('Could not send: ' + er.message, true); store.set('hoola.draft.' + origin, text); if (CONV === origin) { msg.value = text; FILES.push(...files); drawFiles(); } return; } await new Promise(r => setTimeout(r, 800 * (i + 1))); }
  }
});
$('#stopBtn').addEventListener('click', async () => { try { await api('POST', `/api/conversations/${encodeURIComponent(CONV)}/stop`); toast('Stopping. The step that was running may stop halfway.'); } catch (e) { toast(e.message, true); } });
$('#attach').addEventListener('click', () => $('#fileIn').click());
$('#fileIn').addEventListener('change', e => { const picked = [...e.target.files]; e.target.value = ''; addFiles(picked); });
async function addFiles(list) {     // paperclip, drag and drop, pasted screenshots: one path
  const origin = CONV, target = FILES;
  if (!origin) return;
  const picked = list.slice(0, Math.max(0, 6 - target.length));
  if (list.length > picked.length) toast('Up to 6 files at a time.');
  if (picked.length) msg.focus();
  const jobs = [];
  for (const f of picked) {
    if (f.size > 25 * 1024 * 1024) { toast(`${f.name}: files over 25 MB are not supported.`, true); continue; }
    const up = await shrink(f);   // v0.173 big pictures shrink here: upload fast, phone data saved
    if (up !== f) toast(`${f.name}: shrunk (${Math.round(f.size / 1024)} KB → ${Math.round(up.size / 1024)} KB).`);
    if (CONV !== origin || FILES !== target) return;
    // v0.279 the tile shows her picture at once (local blob:), then the real upload %
    const item = {name: up.name, file_id: null, size: up.size, type: up.type, pct: 0, local: up,
                  url: up.type.startsWith('image/') ? URL.createObjectURL(up) : ''};
    target.push(item); drawFiles();
    jobs.push(sendOne(origin, target, item));   // uploads run side by side; the long-text path waits for them
  }
  await Promise.all(jobs);
}
async function sendOne(origin, target, item) {
  item.err = ''; item.pct = 0; drawFiles();
  try {
    const r = ATT ? await ATT.upload(origin, item.local, p => { item.pct = p; drawPct(item); })
      : await api('POST', `/api/conversations/${encodeURIComponent(origin)}/files`, undefined, {form: (() => { const fd = new FormData(); fd.append('file', item.local, item.name); return fd; })()});
    if (!target.includes(item)) return;
    Object.assign(item, {file_id: r.file_id, media: r.media, preview: r.preview, pages: r.pages, duration: r.duration,
                         width: r.width, height: r.height, snippet: r.snippet, size: r.size || item.size});
    ATT?.remember(r.file_id, item.url);
  } catch (er) {
    if (!target.includes(item)) return;
    if (er.status === 401) { target.splice(target.indexOf(item), 1); }
    else { item.err = er.message || 'Upload failed'; toast(`${item.name}: ${item.err}`, true); }
  }
  drawFiles();
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
  {k: 'Ctrl+F', g: 'Search', label: 'Find in this chat', fn: () => { go('chat'); openFind(); }},
  {k: 'Ctrl+K', g: 'Search', label: 'Search all chats', fn: () => CH?.openSearch()},
  {k: 'Alt+ArrowDown', g: 'Chat', label: 'Agli chat', fn: () => chatStep(1)},
  {k: 'Alt+ArrowUp', g: 'Chat', label: 'Pichhli chat', fn: () => chatStep(-1)},
  {k: 'Ctrl+Shift+O', g: 'Chat', label: 'Nayi chat', fn: () => $('#newChat').click()},
  {k: '/', g: 'Composer', label: 'Focus the message box', when: e => !typingIn(e), fn: () => { go('chat'); msg.focus(); }},
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
  if (e.isComposing || $('#app').hidden || CREATE?.isOpen()) return;    // the Create Studio owns the keys while open
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
  if (window.HoolaMenu?.isOpen()) { HoolaMenu.close(true); return; }
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
    <p class="faint">Type "/" in the message box for commands like /nayi /dhoondo /export. Ctrl+K searches all chats.</p></div>`;
  document.body.appendChild(w);
  w.addEventListener('click', e => { if (e.target === w) w.remove(); });
}

/* ================= export (v0.171): this chat as a Markdown file to read, or JSON to keep ================= */
// v0.285 export = the console's Claude-style dropdown (menu.js), like every other menu
const exportMenu = e => window.HoolaMenu?.open(e.currentTarget, [
  {header: 'Export this chat'},
  {label: 'Markdown', sub: 'A .md file to read or share', icon: 'doc', run: () => exportChat('md')},
  {label: 'JSON', sub: 'Every message and card, to keep', icon: 'braces', run: () => exportChat('json')},
], {align: 'end', label: 'Export format', keyboard: e.detail === 0});
$('#exportBtn').addEventListener('click', exportMenu);
$('#cShare').addEventListener('click', exportMenu);
$('#cMore').addEventListener('click', e => { if (CONV) CH?.menu(CONV, e.currentTarget, e.detail === 0); });
async function exportChat(fmt) {
  if (!CONV) return;
  const b = {dataset: {fmt}};
  try {
    const r = await api('GET', `/api/conversations/${encodeURIComponent(CONV)}/export?fmt=${b.dataset.fmt}`, undefined, {raw: true});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(await r.blob());
    a.download = (r.headers.get('content-disposition') || '').match(/filename="?([^";]+)"?/)?.[1] || `hoola-chat.${b.dataset.fmt}`;
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast('Chat exported.');
  } catch (er) { toast('Export failed: ' + er.message, true); }
}
function drawFiles() {
  $('#files').innerHTML = ATT ? ATT.tray(FILES)
    : FILES.map((f, i) => `<span class="fchip${f.file_id ? '' : ' up'}">📎 ${esc(f.name)}${f.file_id ? '' : ' · upload…'}<button type="button" data-rm="${i}" aria-label="Remove ${esc(f.name)}">✕</button></span>`).join('');
  $('#sendBtn').disabled = !msg.value.trim() && !FILES.length;
}
function drawPct(item) {      // v0.279 only the bar moves while bytes go up (no re-draw, no flicker)
  const i = FILES.indexOf(item), bar = i < 0 ? null : $('#files').querySelectorAll('.at')[i]?.querySelector('.aup');
  if (!bar) return;
  const pct = Math.max(4, Math.min(100, Math.round(item.pct)));
  bar.firstElementChild.style.width = pct + '%'; bar.setAttribute('aria-valuenow', pct);
}
$('#files').addEventListener('click', e => {
  const b = e.target.closest('[data-rm]');
  if (b) { const [f] = FILES.splice(+b.dataset.rm, 1); f?.local?._xhr?.abort(); if (f && !f.file_id) ATT?.forget(f); drawFiles(); return; }
  const r = e.target.closest('[data-retry]');
  if (r) { const f = FILES[+r.dataset.retry]; if (f?.local) sendOne(CONV, FILES, f); return; }
  const v = e.target.closest('[data-view]');
  if (v && ATT) ATT.view(FILES, +v.dataset.view);
});
$('#micBtn').title = 'Bolo karke likhiye (dictation)';
$('#toolsBtn').addEventListener('click', () => go('kaam'));

/* v0.173 dictation in the composer: mic button speaks hi-IN into the box (Chrome / Android); the live call
   stays on Baat. No speech recognition in this browser = the old jump to Baat, with a one-line why. */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let DICT = null;
async function flowMic() {   // v0.751 Kaan first (her own server), the browser's speech service only when Kaan cannot hear
  if (FMIC?.on) { FMIC.stop(); return true; }
  if (!FMIC || DICT || !(await FMIC.canUse())) return false;
  try { await FMIC.start(msg.value); toast('Hoola Flow is listening. Click the microphone (or Ctrl + Space) to finish.'); return true; }
  catch (e) { toast(/denied|NotAllowed|Permission/i.test(String(e?.message)) ? 'Allow the microphone for this site in your browser address bar.' : (e.message || 'The microphone could not start.'), true); return true; }
}
document.addEventListener('keydown', e => {   // v0.751 Ctrl + Space starts / finishes dictation while the chat box has focus
  if (!FMIC || !e.ctrlKey || e.code !== 'Space' || document.activeElement !== msg) return;
  e.preventDefault(); $('#micBtn').click();
});
$('#micBtn').addEventListener('click', async () => {
  if (await flowMic()) return;
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
function usePrompt(id) {
  const t = KAAM.flatMap(g => g[4]).find(x => x[0] === id); if (!t) return;
  go('chat'); msg.value = t[3].replace(/^\[[^\]]+\]\s*/, ''); msg.dispatchEvent(new Event('input'));
  if (t[4]) { toast(`Attach a file first (${t[4]}), then send.`); $('#fileIn').click(); } else composer.requestSubmit();
}
document.addEventListener('click', e => { const b = e.target.closest('[data-say]'); if (b) usePrompt(b.dataset.say); });
function drawKaam(q = '') {
  const qq = q.trim().toLowerCase(), total = KAAM.reduce((n, g) => n + g[4].length, 0);
  $('#kaam').innerHTML = `<div class="vh"><h2>What ${esc(AV)} can do</h2><span class="faint" style="font-weight:500">${total} jobs · a tap sends it to the real ${esc(AV)}</span></div>
    <label class="ksearch gl"><span aria-hidden="true">⌕</span><input id="kq" placeholder="Search: GST, reel, OTP, TV…" value="${esc(q)}" aria-label="Search"></label>
    <div class="kchips">${KAAM.map(g => `<a class="chip" href="#k-${g[0]}" style="text-decoration:none"><span>${g[1]}</span>${esc(g[2])}</a>`).join('')}</div>
    ${KAAM.map(g => { const items = g[4].filter(t => !qq || (t[1] + ' ' + t[2] + ' ' + t[3] + ' ' + g[2]).toLowerCase().includes(qq)); if (!items.length) return '';
      return `<div class="kgroup" id="k-${g[0]}"><h3><span>${g[1]}</span>${esc(g[2])}<small>${items.length}</small></h3><div class="kgrid">${items.map(t => `<button class="kt" type="button" data-say="${esc(t[0])}"><i style="background:${g[3]}22">${KI[t[0]] || g[1]}</i><b>${esc(t[1])}</b><span>${esc(t[2])}</span></button>`).join('')}</div></div>`; }).join('')}`;
  const kq = $('#kq'); kq.addEventListener('input', () => { const p = kq.selectionStart; drawKaam(kq.value); const n = $('#kq'); n.focus(); n.setSelectionRange(p, p); });
}

/* ================= v0.222 R2: home - quick chips, action pills, live jobs, Hoola PC pill ================= */
// Deep research / Hoola PC ride ONE message as a hint for Hoola (never in her bubble), then switch off again.
$$('.qc').forEach(b => b.addEventListener('click', () => b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true'))));
function takeHints() {
  const h = [];
  if ($('#qDeep').getAttribute('aria-pressed') === 'true') h.push('mode: deep research - research this thoroughly from several good sources and cite them');
  if ($('#qPc').getAttribute('aria-pressed') === 'true') h.push('place: do this on Hoola PC (your own cloud computer)');
  $$('.qc').forEach(b => b.setAttribute('aria-pressed', 'false'));
  return h;
}
$('#callBtn').addEventListener('click', () => go('baat'));
document.addEventListener('click', e => {
  const b = e.target.closest('[data-fill]'); if (!b) return;
  go('chat'); msg.value = b.dataset.fill; msg.dispatchEvent(new Event('input')); msg.focus();
  msg.setSelectionRange(msg.value.length, msg.value.length);
});
let JOBS_T = 0;
const JOB_IC = {site_board: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18"/>',
  app_board: '<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/>',
  video_job: '<rect x="2" y="5" width="15" height="14" rx="2"/><path d="M17 10l5-3v10l-5-3"/>',
  motion: '<rect x="2" y="5" width="15" height="14" rx="2"/><path d="M17 10l5-3v10l-5-3"/>',
  studio: '<rect x="2" y="5" width="15" height="14" rx="2"/><path d="M17 10l5-3v10l-5-3"/>',
  browser: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>'};
async function loadJobs() {
  let list = [];
  try { list = ((await api('GET', '/api/kaam')).jobs || []).filter(j => j.state === 'working' || j.state === 'waiting'); } catch { return; }
  JOBS = list; drawJobs(); drawNav(); humanTagline();
}
function drawJobs() {
  const box = $('#liveJobs'); box.hidden = !JOBS.length; if (!JOBS.length) return;
  const show = JOBS.slice().sort((a, b) => (b.state === 'waiting') - (a.state === 'waiting')).slice(0, 3);
  $('#jobGrid').innerHTML = show.map(j => {
    const wait = j.state === 'waiting', pct = Math.max(4, Math.min(100, +j.pct || 0));
    const icon = wait ? '<path d="M12 8v5M12 16.5v.5"/><circle cx="12" cy="12" r="9"/>' : (JOB_IC[j.kind] || IC.kaam);
    const sub = HUMAN ? [j.stage || j.detail || (wait ? 'Waiting for your OK' : 'Working'), wait ? '' : soFar(j.started_at)].filter(Boolean).join(' · ')
                      : j.stage || j.detail || (wait ? 'Waiting for you' : 'Working…');
    const real = +j.pct > 0 && +j.pct < 100;   // v0.743 a bar only when the job reports real progress
    return `<button type="button" class="job${wait ? ' wait' : ''}" data-job="${esc(j.conversation_id || '')}">
      <span class="jt"><span class="ji">${svg(icon)}</span><span class="jn"><b>${esc(j.title || j.label || 'Job')}</b><span>${esc(j.label && j.title ? j.label + ' · ' : '')}${esc(sub)}</span></span></span>
      ${HUMAN ? `<span class="jtag">${wait ? 'Waiting for you' : 'Working'}</span>` : ''}
      ${wait ? '<span class="jact">Review &amp; approve</span>'
             : HUMAN && !real ? '' : `<span class="jbar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="Progress"><i style="width:${pct}%"></i></span>`}
    </button>`;
  }).join('');
}
$('#jobGrid').addEventListener('click', e => {
  const b = e.target.closest('[data-job]'); if (!b) return;
  if (b.dataset.job) { go('chat'); openConv(b.dataset.job); } else go('aaj');
});
async function loadPcPill() {
  try { const d = (await api('GET', '/api/pc/hoola')).devices || []; const pc = d[0];
    const el = $('#pcPill'); el.hidden = !pc; if (!pc) return;
    el.classList.toggle('off', !pc.online); el.querySelector('span').textContent = pc.online ? 'Hoola PC online' : 'Hoola PC offline';
  } catch {}
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
  if (!TYPING) live(QUEUE.length ? 'ask' : 'idle'); drawNav(); humanTagline();
}

/* ================= Today ================= */
async function drawToday() {
  const box = $('#aaj'); box.innerHTML = '<div class="vh"><h2>Today</h2></div><div class="empty">Loading…</div>';
  let d = {reminders: [], lists: {}, pending: []}; try { d = {...d, ...(await api('GET', '/api/console/today') || {})}; d.reminders ||= []; d.lists ||= {}; d.pending ||= []; } catch (e) { box.innerHTML += `<p class="badc">${esc(e.message)}</p>`; return; }
  const date = new Date().toLocaleDateString('en-IN', {weekday: 'long', day: 'numeric', month: 'long'});
  box.innerHTML = `<div class="vh"><h2>Today · ${esc(date)}</h2></div>
    <div class="kpis"><div class="kpi gl"><b>${d.pending.length}</b><span>waiting for your Haan</span></div><div class="kpi gl"><b>${d.reminders.length}</b><span>upcoming reminders</span></div>
    <div class="kpi gl"><b>${Object.values(d.lists).reduce((n, l) => n + l.length, 0)}</b><span>items in lists</span></div><div class="kpi gl"><b class="hid">${esc(ME?.handle || '')}</b><span>your Hoola ID</span></div></div>
    <div class="grid2">
      <div class="tile gl"><h3>Reminders</h3>${d.reminders.length ? `<div class="ag">${d.reminders.map(r => `<div><time>${esc(timeOf(r.due_at))}</time><span>${esc(r.text)}</span></div>`).join('')}</div>` : '<div class="empty">No reminders.</div>'}</div>
      <div class="tile gl"><h3>Lists</h3>${Object.keys(d.lists).length ? Object.entries(d.lists).map(([n, items]) => `<b style="font-size:13px" class="acc">${esc(n)}</b><div class="lst">${items.map(i => `<label><input type="checkbox" disabled> ${esc(i.text)}</label>`).join('')}</div>`).join('') : '<div class="empty">No lists yet. Ask in chat, for example: "doodh shopping list mein daalo".</div>'}</div>
      <div class="tile gl" id="todayWork"><h3>Work</h3><div class="empty">Loading…</div></div>
      <div class="tile gl"><h3>Your approval is required <span class="tag warn">${d.pending.length}</span></h3>${d.pending.length ? d.pending.map(q => `<div class="ln"><span>${esc(q.title)}</span><b>${q.money ? '📱 phone' : 'console'}</b></div>`).join('') + '<button class="btn soft" type="button" id="toQueue">Open cards</button>' : '<div class="empty">Nothing yet.</div>'}</div>
    </div>`;
  $('#toQueue')?.addEventListener('click', () => { $('#app').classList.add('open'); go('chat'); });
  drawTodayWork();
}
/* v0.648 KAAM KA HISAAB: running / waiting for her / finished in the last 7 days; a row opens its chat or call */
async function drawTodayWork() {
  const box = $('#todayWork'); if (!box) return;
  let d; try { d = await api('GET', '/api/kaam/list'); } catch (e) { box.innerHTML = `<h3>Work</h3><p class="badc">${esc(e.message)}</p>`; return; }
  const when = iso => { try { return new Date(iso).toLocaleString('en-IN', {weekday: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return ''; } };
  const row = r => `<button type="button" class="ln wkrow" data-wconv="${esc(r.conversation_id || '')}" ${r.conversation_id ? '' : 'disabled'}>
      <span>${esc(r.title || r.label || 'Work')}${r.from_call ? ' <span class="tag v">call</span>' : ''}</span>
      <b>${esc(r.say || r.state || '')}${r.at ? ' · ' + esc(when(r.at)) : ''}</b></button>`;
  const sec = (name, rows) => rows.length ? `<b style="font-size:13px" class="acc">${esc(name)} (${rows.length})</b>${rows.slice(0, 12).map(row).join('')}` : '';
  const html = sec('Waiting for you', d.waiting || []) + sec('Running now', d.running || []) + sec('Done in the last 7 days', d.done || []);
  box.innerHTML = '<h3>Work</h3>' + (html || '<div class="empty">No work this week yet.</div>');
}
document.addEventListener('click', e => {
  const b = e.target.closest('#todayWork [data-wconv]'); if (!b || !b.dataset.wconv) return;
  go('chat'); openConv(b.dataset.wconv);
});

/* ================= Main (profile + console password) ================= */
const gOn = m => { const g = m.google_apps || {}; return !!(g.gmail && g.calendar && g.drive); };
async function drawMain() {
  const m = ME || {}; const box = $('#mainp');
  box.innerHTML = appearanceHTML() + `<div class="prof gl"><span class="av"><img src="${$('#uimg').src}" alt=""></span><div><h2>${esc(AV)}</h2><div class="muted">${esc(m.handle || '')} · ${esc(m.owner || '')}${m.email ? ' · ' + esc(m.email) : ''}</div></div></div>
    <div class="grid2">
      <div class="tile gl"><h3>Console password <span class="tag ${m.has_password ? 'ok' : 'warn'}">${m.has_password ? 'set' : 'not set'}</span></h3>
        <p class="muted" style="font-size:13.5px">Sign in on any computer with <b>${esc(m.handle || 'Hoola ID')}</b> + this password. Every sign-in is reported in your chat.</p>
        <form class="pwbox" id="pwf" autocomplete="off">${m.has_password ? '<input type="password" id="pwc" placeholder="Current password" autocomplete="current-password" aria-label="Current password">' : ''}
          <input type="password" id="pwn" placeholder="New password (10+ characters)" autocomplete="new-password" aria-label="New password" minlength="10">
          <input type="password" id="pwn2" placeholder="Confirm new password" autocomplete="new-password" aria-label="Repeat new password">
          <button class="btn go" type="submit">${m.has_password ? 'Change password' : 'Set password'}</button></form></div>
      <div class="tile gl"><h3>Google apps <span class="tag ${gOn(m) ? 'ok' : 'warn'}">${gOn(m) ? 'connected' : 'not connected'}</span></h3>
        <p class="muted" style="font-size:13.5px">Sign-in only reads your name and email. To work in Gmail, Calendar, Drive, Docs and Sheets, give Google permission separately.</p>
        <div class="feat">${['gmail', 'calendar', 'drive', 'docs', 'sheets'].map(k => `<span class="chip">${(m.google_apps || {})[k] ? '✓' : '○'} ${k[0].toUpperCase() + k.slice(1)}</span>`).join('')}</div>
        <div class="acts" style="margin-top:12px"><button class="btn ${gOn(m) ? 'soft' : 'go'}" type="button" id="gAppsBtn">${gOn(m) ? 'Reconnect' : 'Connect Google apps'}</button></div></div>
      <div class="tile gl"><h3>Yaad <span class="tag v" id="memc">…</span></h3><div class="mfacts" id="mfacts"><div class="empty">Loading…</div></div></div>
      <div class="tile gl"><h3>Server</h3><div class="feat" id="feat"><span class="empty">…</span></div></div>
    </div>
    <div class="acts" style="margin-top:22px"><button class="btn soft" type="button" id="logoutBtn">Logout</button>
      ${CONFIG.v2 ? '<a class="btn soft" href="/console/?legacy=1" style="text-decoration:none">Legacy console</a>' : ''}</div>`;
  themeSync();
  $('#logoutBtn').addEventListener('click', () => logout(false));
  $('#gAppsBtn').addEventListener('click', () => { if (!CONFIG.google) return toast('Google sign-in is not configured.', true); location.href = '/auth/google/start?web=1&apps=1'; });
  $('#pwf').addEventListener('submit', async e => { e.preventDefault(); const n = $('#pwn').value, n2 = $('#pwn2').value;
    if (n !== n2) return toast('The new passwords do not match.', true);
    try { const r = await api('PUT', '/api/console/password', {password: n, current: $('#pwc')?.value || ''}); ME.has_password = true; toast(`Password set. You can now sign in with ${r.handle} + password.`); drawMain(); } catch (er) { toast(er.message, true); } });
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
    else if (m.type === 'hold') { if (m.on) cutSpeech(); callUI('live', m.on ? (AV + ' is on hold · say "' + AV + '" to bring it back') : 'Live'); }
    else if (m.type === 'error') { toast(m.message || 'Call problem', true); callUI('live', m.message || 'Problem'); }
  };
  ws.onclose = e => { endCall(false); callUI('idle', e.code === 4401 ? 'Please sign in again.' : 'Call ended.'); };
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
  callUI('idle', 'Call ended. The call receipt will appear in the chat.');
}
addEventListener('beforeunload', () => endCall(true));

boot();
})();
