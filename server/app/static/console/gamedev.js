/* v0.783 HOOLA GAME DEV - game making as its own full-screen app (owner approved the 14-page design: "GO BUILD").

   Home (own sidebar): one ask box ("What game should we make today?") -> POST /api/game with a NEW conversation of its
   own, so the talk about that game continues in its own thread; "Waiting for your OK", "Your games", start tiles.
   Workspace (#/game/<id>/<tab>): THIS game's own Hoola thread on the left (a conversation per game, never the home
   chat) and the game on the right: Design · Play · Board · Bible · Scenes · Assets · QA | Release · Live ops ·
   Where it came from | Crew. Design and Play are drawn here from /api/game/<id>; every other page is the console's
   own, tested Game Desk page (employees.js gameEmbed) shown inside the pane.
   Crew / Game Arena / Big studio keep the home sidebar.

   Rules kept: every server value goes through esc(); links only http(s) or same-origin /play/; nothing is built,
   changed, deleted or published without her tap; delete asks first. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const S = v => v == null ? '' : String(v);
  const L = v => Array.isArray(v) ? v : [];
  const M = v => v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  const N = v => Number(v) || 0;
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const store = {get(k) { try { return localStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} }, del(k) { try { localStorage.removeItem(k); } catch {} }};
  const TOKEN = store.get('hoola.console.token');
  const APP = $('#gdv');
  if (!TOKEN) { location.replace('/console/'); return; }
  // v0.799 ENGINE LOOK: a game engine is a dark room (Godot, Unity, Unreal) - this app always opens dark, whatever the
  // console's own Light / Dark choice is; the embedded console pages read the same tokens, so they go dark with it
  document.documentElement.setAttribute('data-theme', 'dark');
  document.documentElement.classList.add('gdv-engine');

  /* ---------- server ---------- */
  class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
  async function api(method, path, body, {raw = false} = {}) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (method === 'POST' && /\/conversations\/[^/]+\/messages$/.test(path) && body && typeof body.text === 'string') {
      const hints = L(body.hints).map(h => '\n\n[Web console ' + h + ']').join('');
      body = {...body, text: body.text + hints + '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]'};
      delete body.hints;
    }
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new ApiError(401, 'Please sign in again.'); }
    if (raw) { if (!r.ok) throw new ApiError(r.status, await r.text()); return r; }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) {
      const bad = data && Array.isArray(data.detail) && data.detail[0];
      const msg = (data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) ||
        (bad ? S(bad.msg) : '') || `The server refused the request (${r.status})`;
      const e = new ApiError(r.status, msg); e.data = data; throw e;
    }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); if (!t) return;
    t.textContent = S(msg); t.className = 'gdv-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }

  /* ---------- the console's own game pages, shown inside a pane ---------- */
  const E = window.HoolaEmployees({api, esc, toast, changed: () => {}, open: () => {},
    say: text => { if (fillBar(text)) return; const t = $('#gdvAsk'); if (t) { t.value = S(text); t.focus(); } }});
  const PROJECT_PAGES = ['board', 'bible', 'scenes', 'assets', 'qa', 'release', 'liveops', 'prov'];   // these need a long project
  let EMBED = null;
  function stopEmbed() { try { E.gameEmbed.stop(); } catch {} if (EMBED) { EMBED.remove(); EMBED = null; } const p = $('#gdvPane'); if (p) p.classList.remove('gdv-pane-embed'); }
  function embed(host, page, sid) {
    stopEmbed();
    const div = document.createElement('div');
    div.className = 'gdv-embed'; div.dataset.page = page;
    div.innerHTML = '<div class="gdv-loading">Loading…</div>';
    host.appendChild(div); EMBED = div;
    host.closest('.gdv-pane')?.classList.add('gdv-pane-embed');
    const fail = e => { if (div.isConnected) div.innerHTML = `<div class="gdv-panel"><p class="gdv-bad">${esc(e && e.message || e)}</p></div>`; };
    try { const p = E.gameEmbed(div, page, sid || ''); if (p && typeof p.catch === 'function') p.catch(fail); }
    catch (e) { fail(e); }
  }

  /* ---------- icons ---------- */
  const ICON = {
    pad: '<rect x="2.5" y="7" width="19" height="11" rx="5"/><path d="M7.5 10.5v4M5.5 12.5h4"/><circle cx="16" cy="11.5" r="1"/><circle cx="18" cy="13.8" r="1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', home: '<path d="M4 11l8-7 8 7v9H4z"/>', grid: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    crew: '<circle cx="9" cy="8" r="3.2"/><path d="M3 19c.6-3.4 3-5.2 6-5.2s5.4 1.8 6 5.2"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14c2.4.2 4.2 1.8 4.8 4.6"/>',
    trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H4.5a3 3 0 0 0 3.5 4M16 6h3.5a3 3 0 0 1-3.5 4M12 13v4M8 20h8"/>',
    cube: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    back: '<path d="M15 5l-7 7 7 7"/>', up: '<path d="M12 19V5M5 12l7-7 7 7"/>', check: '<path d="M5 12l5 5 9-10"/>',
    cross: '<path d="M6 6l12 12M18 6L6 18"/>', circle: '<circle cx="12" cy="12" r="7"/>', doc: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M10 12h5M10 16h5"/>',
    board: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>', school: '<path d="M3 9l9-5 9 5-9 5z"/><path d="M7 11.5V16c3 2 7 2 10 0v-4.5"/>',
    pen: '<path d="M4 20h4L19 9l-4-4L4 16z"/>', copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/>',
    dl: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>', play: '<path d="M7 4.5l12 7.5-12 7.5z" fill="currentColor"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>', full: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>', ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>'};
  const ico = (k, n = 18) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;

  /* ---------- a game's state in plain words ---------- */
  const BUSY = ['designing', 'queued', 'writing', 'building', 'testing'];
  const ST = {designing: ['Writing the design', 'v'], design_ready: ['Your OK', 'warn'], queued: ['Queued', 'v'],
    writing: ['Writing code', 'v'], building: ['Building', 'v'], testing: ['Playing it', 'v'], done: ['Plays', 'ok'],
    failed: ['Did not work', 'bad'], cancelled: ['Stopped', '']};
  const ORL = {portrait: 'Phone, upright', landscape: 'Phone, sideways', square: 'Square'};
  const busy = g => BUSY.includes(S(g.status));
  const pill = (t, c) => `<span class="gdv-pill ${c ? 'gdv-' + c : ''}">${esc(t)}</span>`;
  const stOf = g => ST[S(g.status)] || [S(g.status) || 'Draft', ''];
  const gname = g => S(g.title) || S(g.number) || 'Game';
  function longStatus(g) {
    const s = S(g.status);
    if (s === 'design_ready') return ['Design ready · waiting for your OK', 'warn'];
    if (busy(g)) return [stOf(g)[0] + (N(g.pct) ? ` · ${Math.round(N(g.pct))}%` : ''), 'v'];
    if (N(g.version)) return [`Plays · version ${N(g.version)}`, 'ok'];
    return stOf(g);
  }
  const safeUrl = u => typeof u === 'string' && /^(https:\/\/|http:\/\/127\.0\.0\.1|\/play\/)/.test(u) ? u : '';
  const absUrl = u => { try { return new URL(u, location.origin).href; } catch { return u; } };
  const isoS = x => { const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(S(x)) ? S(x) : S(x) + 'Z'); return isNaN(t) ? 0 : t / 1000; };
  const ago = x => { const t = isoS(x); if (!t) return ''; const d = Math.max(0, Date.now() / 1000 - t);
    return d < 60 ? 'just now' : d < 3600 ? `${Math.floor(d / 60)} min ago` : d < 86400 ? `${Math.floor(d / 3600)} h ago` : `${Math.floor(d / 86400)} d ago`; };
  const nowS = () => Date.now() / 1000;
  const dur = s => { s = Math.max(0, Math.round(s)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s` : `${Math.floor(s / 3600)}h ${String(Math.floor(s / 60) % 60).padStart(2, '0')}m`; };
  const tintOf = id => { let h = 0; for (const c of S(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 6; };
  const defTab = g => safeUrl(g.play_url || g.url) ? 'play' : 'design';
  const clockOf = t => t ? new Date(t * 1000).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}) : '';
  const md = t => window.HoolaMD ? window.HoolaMD.render(S(t), false) : `<p>${esc(t)}</p>`;
  const numStr = v => (v === null || v === undefined || v === '') ? '' : (typeof v === 'number' ? v.toLocaleString('en-IN', {maximumFractionDigits: 1}) : S(v));

  /* ---------- state ---------- */
  let GAMES = [], HEALTH = {}, ORIENT = ['portrait', 'landscape'], PROJECTS = [], EMP = {employees: [], hired: {}}, EMP_OK = false;
  let POLL = null, PENDING = null, HOMEPOLL = null, PENDING_CONV = '', ARENA_OK = null;   // ARENA_OK: null = not asked yet, false = 403 once
  const W = {id: '', game: null, tab: '', sub: '', sig: ''};
  const convKey = id => 'hoola.gamedev.conv.' + id;
  const sidOf = gid => S((PROJECTS.find(p => S(M(p.game).id) === S(gid)) || {}).id);
  const projOf = gid => PROJECTS.find(p => S(M(p.game).id) === S(gid)) || null;
  const devWorking = () => M(EMP.hired).game_dev === 'hired';
  const empOf = key => L(EMP.employees).find(e => e.key === key) || {};
  const hiredState = key => S(M(EMP.hired)[key]);

  async function loadHome() {
    const [d, sp, em] = await Promise.all([api('GET', '/api/game'),
      api('GET', '/api/gamestudio').catch(() => ({projects: []})),
      api('GET', '/api/employees').catch(() => null)]);
    GAMES = L(d.games); HEALTH = M(d.health); ORIENT = L(d.orientations).length ? L(d.orientations) : ORIENT;
    PROJECTS = L(sp.projects);
    if (em) { EMP = {employees: L(em.employees), hired: M(em.hired)}; EMP_OK = true; }
  }
  async function loadProjects() { try { PROJECTS = L((await api('GET', '/api/gamestudio')).projects); } catch {} }

  /* ---------- routing ---------- */
  function stopAll() {
    clearTimeout(POLL); POLL = null; clearTimeout(HOMEPOLL); HOMEPOLL = null;
    clearTimeout(THREAD.timer); THREAD.timer = null; clearInterval(TICK); TICK = null;
    dropKit(); BAR = null;
    stopEmbed();
  }
  function parse() {
    const p = S(location.hash).replace(/^#\/?/, '').split('/').filter(Boolean).map(x => { try { return decodeURIComponent(x); } catch { return x; } });
    if (p[0] === 'game' && p[1]) return {view: 'game', id: p[1], tab: p[2] || '', sub: p[3] || ''};
    if (p[0] === 'crew') return {view: 'crew', role: p[1] || ''};
    if (p[0] === 'arena' || p[0] === 'big' || p[0] === 'games') return {view: p[0]};
    return {view: 'home'};
  }
  async function route() {
    const r = parse();
    if (r.view === 'game') {
      if (W.id === r.id && $('#gdvPane')) { stopEmbed(); clearTimeout(POLL); W.tab = TAB_KEYS.includes(r.tab) ? r.tab : defTab(W.game || {}); W.sub = r.sub; drawTabs(); drawPane(); startPoll(); return; }
      stopAll();
      return openGame(r.id, r.tab, r.sub);
    }
    stopAll(); W.id = ''; W.game = null;
    document.title = 'Hoola Game Dev';
    if (!APP.querySelector('.gdv-shell')) APP.innerHTML = '<div class="gdv-shell"><header class="gdv-ebar" id="gdvEbar"></header><div class="gdv-shrow"><aside class="gdv-side" aria-label="Hoola Game Dev"></aside><main class="gdv-main" id="gdvMain"><div class="gdv-loading">Loading…</div></main></div></div>';
    try { await loadHome(); } catch (e) { drawSide(r.view); $('#gdvMain').innerHTML = `<div class="gdv-panel"><p class="gdv-bad">${esc(e.message)}</p></div>`; return; }
    if (S(location.hash) && parse().view !== r.view) return;   // she moved on while it loaded
    drawSide(r.view === 'games' ? 'games' : r.view); drawEbar();
    const main = $('#gdvMain'); main.scrollTop = 0;
    if (r.view === 'home') drawHome(main);
    else if (r.view === 'games') drawAll(main);
    else if (r.view === 'crew') r.role ? drawRole(main, r.role, '') : drawCrew(main, '', '');
    else if (r.view === 'arena') {
      if (ARENA_OK === null) { try { await api('GET', '/api/gamedesk/arena'); ARENA_OK = true; } catch (e) { if (e.status === 403) { ARENA_OK = false; drawSide('arena'); } } }
      if (parse().view !== 'arena') return;
      drawEmbedPage(main, 'arena', 'Game Arena', 'Are our games getting better? Fixed briefs, built and judged by playing them.');
    }
    else if (r.view === 'big') drawEmbedPage(main, 'big', 'Big studio', 'Your own Unity, Unreal or Godot project on your machines. The crew works inside your editor.');
    if (['home', 'games'].includes(r.view)) homePoll(r.view);
  }
  /* the home / All games poll: only the lists are redrawn - never the ask box, its text, the focus or the scroll */
  function homePoll(view) {
    clearTimeout(HOMEPOLL); HOMEPOLL = null;
    if (!GAMES.some(busy)) return;
    HOMEPOLL = setTimeout(async () => {
      if (parse().view !== view) return;
      try { await loadHome(); } catch { return homePoll(view); }
      if (parse().view !== view) return;
      const rb = $('#gdvRecentBox'); if (rb) rb.innerHTML = recentHtml();
      drawEbar(); const sb = $('#gdvStatsBox'); if (sb) sb.innerHTML = statsHtml();
      if (view === 'home') {
        const wb = $('#gdvWaitBox'); if (wb) wb.innerHTML = waitHtml();
        const gb = $('#gdvGamesBox'); if (gb) gb.innerHTML = gamesHtml();
      } else { const ab = $('#gdvAllBox'); if (ab) ab.innerHTML = allHtml(); }
      homePoll(view);
    }, 5000);
  }

  /* ---------- the home sidebar ---------- */
  function drawSide(on) {
    const side = APP.querySelector('aside.gdv-side'); if (!side) return;
    const nav = (k, href, icon, label) => `<a class="gdv-nav" data-gdv-nav="${k}" href="${href}"${on === k ? ' aria-current="page"' : ''}>${ico(icon, 17)}<span>${esc(label)}</span></a>`;
    const h = HEALTH;
    side.innerHTML = `<div class="gdv-brand"><span class="gdv-mark" aria-hidden="true">${ico('pad', 18)}</span><div><b>Hoola</b><span>Game Dev</span></div></div>
      <a class="gdv-new" href="#/" data-gdv-act="new-game"><span>${ico('plus', 16)}New game</span><kbd>Ctrl K</kbd></a>
      <nav class="gdv-navs" aria-label="Game Dev">${nav('home', '#/', 'home', 'Home')}${nav('games', '#/games', 'grid', 'All games')}${nav('crew', '#/crew', 'crew', 'Crew')}${ARENA_OK === false ? '' : nav('arena', '#/arena', 'trophy', 'Game Arena')}${nav('big', '#/big', 'cube', 'Big studio')}</nav>
      <div id="gdvRecentBox">${recentHtml()}</div>
      <span class="gdv-grow"></span>
      <div class="gdv-health${h.ready ? '' : ' gdv-health-bad'}"><span><span class="gdv-dot gdv-${h.ready ? 'ok' : 'bad'}" aria-hidden="true"></span>${h.ready ? `Godot ${esc(h.version || '')} ready` : 'Godot is not installed'}</span>
        <span class="gdv-small">${h.ready ? 'Builds and test-plays run on your Hoola server.' : 'Designs can be written; builds wait until Godot is set up on the server.'}</span></div>
      <a class="gdv-nav" href="/console/">${ico('back', 17)}<span>Back to Hoola</span></a>`;
  }

  /* ---------- the engine bar: only real numbers (the server's Godot, games being made, games that play) ---------- */
  function drawEbar() {
    const bar = $('#gdvEbar'); if (!bar) return;
    const h = HEALTH, making = GAMES.filter(busy).length, plays = GAMES.filter(g => N(g.version)).length;
    bar.innerHTML = `<span class="gdv-emark" aria-hidden="true">${ico('pad', 17)}</span><b class="gdv-ename">Hoola Game Dev</b><span class="gdv-mono gdv-etag">engine</span>
      <span class="gdv-grow"></span>
      <span class="gdv-echip"><span class="gdv-dot gdv-${h.ready ? 'ok' : 'bad'}${h.ready ? ' gdv-glow' : ''}" aria-hidden="true"></span>${h.ready ? `Godot ${esc(h.version || '')} ready` : 'Godot not installed'}</span>
      ${making ? `<span class="gdv-echip gdv-echip-v"><span class="gdv-dot gdv-v gdv-glow" aria-hidden="true"></span>${making} being made</span>` : ''}
      <span class="gdv-echip">${plays} of ${GAMES.length} play</span>
      <a class="gdv-elink" href="/console/">Back to Hoola</a>`;
  }
  /* studio at a glance - drawn from her games only; a card with nothing real to show is left out */
  function statsHtml() {
    if (!GAMES.length) return '';
    const cnt = {plays: 0, wait: 0, busy: 0, bad: 0};
    GAMES.forEach(g => { if (busy(g)) cnt.busy++; else if (g.status === 'design_ready') cnt.wait++; else if (N(g.version)) cnt.plays++; else if (['failed', 'cancelled'].includes(g.status)) cnt.bad++; });
    const tot = Math.max(1, cnt.plays + cnt.wait + cnt.busy + cnt.bad);
    const seg = (n, c, l) => n ? `<span class="gdv-seg gdv-seg-${c}" style="flex:${n} 1 0" title="${esc(l)}"></span>` : '';
    const key = (n, c, l) => n ? `<span class="gdv-key"><i class="gdv-seg-${c}" aria-hidden="true"></i>${esc(l)} ${n}</span>` : '';
    const built = GAMES.filter(g => N(g.versions)).slice(0, 8), mx = Math.max(1, ...built.map(g => N(g.versions)));
    const fps = GAMES.filter(g => M(g.numbers).fps_server != null && N(M(g.numbers).fps_server) > 0).slice(0, 6);
    const versions = GAMES.reduce((a, g) => a + N(g.versions), 0);
    return `<div class="gdv-stats">
      <div class="gdv-stat"><span class="gdv-mono gdv-mut">your games</span>
        <div class="gdv-segs" role="img" aria-label="${cnt.plays} play, ${cnt.wait} wait for your OK, ${cnt.busy} being made, ${cnt.bad} did not work">${seg(cnt.plays, 'ok', 'Plays')}${seg(cnt.wait, 'warn', 'Waiting for your OK')}${seg(cnt.busy, 'v', 'Being made')}${seg(cnt.bad, 'bad', 'Did not work')}</div>
        <div class="gdv-keys">${key(cnt.plays, 'ok', 'Play')}${key(cnt.wait, 'warn', 'Wait for you')}${key(cnt.busy, 'v', 'Being made')}${key(cnt.bad, 'bad', 'Did not work')}</div>
        <b class="gdv-big">${GAMES.length} game${GAMES.length === 1 ? '' : 's'}</b><span class="gdv-sr">${Math.round(cnt.plays / tot * 100)}% play</span></div>
      ${built.length ? `<div class="gdv-stat"><span class="gdv-mono gdv-mut">versions built</span>
        <div class="gdv-vbars" role="img" aria-label="${built.map(g => `${esc(gname(g))} ${N(g.versions)}`).join(', ')}">${built.map((g, i) => `<span style="height:${Math.max(8, N(g.versions) / mx * 100)}%;animation-delay:${i * 80}ms" title="${esc(gname(g))} · ${N(g.versions)}"></span>`).join('')}</div>
        <b class="gdv-big">${versions} version${versions === 1 ? '' : 's'}</b></div>` : ''}
      ${fps.length ? `<div class="gdv-stat"><span class="gdv-mono gdv-mut">frame rate on the server</span>
        <div class="gdv-fps">${fps.map((g, i) => { const f = N(g.numbers.fps_server); return `<div class="gdv-fpsrow"><span class="gdv-ell">${esc(gname(g))}</span><span class="gdv-fpsbar"><i class="gdv-fps-${f >= 50 ? 'ok' : f >= 30 ? 'warn' : 'bad'}" style="width:${Math.min(100, f / 60 * 100)}%;animation-delay:${i * 90}ms"></i></span><span class="gdv-mono">${esc(numStr(f))}</span></div>`; }).join('')}</div>
        <span class="gdv-small">Measured when Hoola played each game in Godot on your server, not on a phone.</span></div>` : ''}
    </div>`;
  }
  /* the hero drawing: Hoola's real six steps round a loop, work flowing round it; the middle names her newest game that plays */
  const LOOP = 'M90 80 C 180 40, 280 40, 370 80 C 430 130, 430 250, 370 300 C 280 340, 180 340, 90 300 C 30 250, 30 130, 90 80 Z';
  function loopHtml() {
    const g = GAMES.filter(x => N(x.version)).sort((a, b) => isoS(b.created_at) - isoS(a.created_at))[0];
    const nodes = [['19.5%', '21%', 'Design', 'one page'], ['50%', '13%', 'Code', 'GDScript'], ['80.5%', '21%', 'Scenes', 'checked'],
      ['80.5%', '79%', 'Art + sound', 'style locked'], ['50%', '87%', 'Bots play', 'phone speeds'], ['19.5%', '79%', 'Your link', 'then stores']];
    return `<div class="gdv-loop" role="img" aria-label="How Hoola makes a game: design, code, scenes, art and sound, bots play it, then your link">
      <svg viewBox="0 0 460 380" preserveAspectRatio="none" aria-hidden="true"><defs><pattern id="gdvGrid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="currentColor" stroke-width="1"/></pattern></defs>
        <rect class="gdv-gridbg" width="460" height="380" fill="url(#gdvGrid)"/><path class="gdv-edge" d="${LOOP}"/><path class="gdv-flow" d="${LOOP}"/></svg>
      ${['saf', 'teal', 'mag'].map((c, i) => `<span class="gdv-pl gdv-pl-${c}" style="offset-path:path('${LOOP}');animation-delay:${-i * 1.6}s" aria-hidden="true"></span>`).join('')}
      ${nodes.map(([x, y, b, s], i) => `<span class="gdv-node${i === 4 ? ' gdv-node-hot' : ''}" style="left:${x};top:${y}" aria-hidden="true"><b>${b}</b><span class="gdv-mono">${s}</span></span>`).join('')}
      <span class="gdv-loopc" aria-hidden="true"><b>${g ? 'v' + N(g.version) : 'v1'}</b><span class="gdv-mono gdv-ell">${esc(g ? gname(g) : 'your next game')}</span></span></div>`;
  }

  function recentHtml() {
    const recent = GAMES.slice().sort((a, b) => isoS(b.created_at) - isoS(a.created_at)).slice(0, 6);
    return recent.length ? `<div class="gdv-sidelabel">Recent</div><div class="gdv-recent">${recent.map(g => `<a class="gdv-rec" href="#/game/${enc(g.id)}/${defTab(g)}"><span class="gdv-dot gdv-${stOf(g)[1] || 'none'}" aria-hidden="true"></span><span class="gdv-ell">${esc(gname(g))}</span><span class="gdv-sr">${esc(stOf(g)[0])}</span></a>`).join('')}</div>` : '';
  }

  /* ---------- home ---------- */
  const KINDS = [['Endless runner', 'An endless runner where the player '], ['Match-3', 'A match-3 puzzle game about '],
    ['Platformer', 'A platformer where the hero '], ['Puzzle', 'A puzzle game where you '], ['Quiz for a class', 'A quiz game for Class 6 on '],
    ['Idle tycoon', 'An idle tycoon game where you run a '], ['Racing', 'A racing game on '], ['Story game', 'A short story game about ']];
  const STEPS = [['Design doc', 'You read it and say OK'], ['Built in Godot', 'Code, scenes, art, sound'], ['Hoola plays it', 'Bots on phone speeds'],
    ['Fixes itself', "A bug closes only when the bot can't find it"], ['Private link', 'Play on any phone'], ['Store + live', 'Play Store, itch.io, PC, then updates']];
  function hireGate() {
    if (devWorking() || !EMP_OK) return '';
    const st = hiredState('game_dev');
    return `<div class="gdv-gate" role="status"><div><b>${st === 'paused' ? 'The Game Developer is paused' : 'The Game Developer is not on your team yet'}</b>
      <span>Games are made by the Game Developer employee. ${st === 'paused' ? 'Resume it to start a new game.' : 'Hire it once (free to hire, it asks you before every build).'}</span></div>
      <button class="gdv-b gdv-pri" type="button" data-gdv-act="hire">${st === 'paused' ? 'Resume the Game Developer' : 'Hire the Game Developer'}</button></div>`;
  }
  function card(g) {
    const [t, c] = stOf(g), p = projOf(g.id), shot = safeUrl(L(g.shots)[0]);
    const tile = shot ? `<img src="${esc(shot)}" alt="" loading="lazy">` : sceneArt(tintOf(g.id) % 3);
    const badge = busy(g) ? `<span class="gdv-badge gdv-badge-v">● ${esc(stOf(g)[0])} ${Math.round(N(g.pct))}%</span>` : N(g.version) ? `<span class="gdv-badge gdv-badge-ok">● Plays · v${N(g.version)}</span>` : g.status === 'design_ready' ? '<span class="gdv-badge gdv-badge-warn">● Design · your OK</span>' : '';
    const meta = [S(g.number), N(g.version) ? `v${N(g.version)}` : (g.status === 'design_ready' ? 'design' : ''), ORL[g.orientation] || ''].filter(Boolean).join(' · ');
    const line = p && N(M(p.counts).review) ? `${N(p.counts.review)} task${N(p.counts.review) > 1 ? 's' : ''} wait for you` : busy(g) ? S(g.say) : `Started ${ago(g.created_at)}`;
    return `<a class="gdv-card" href="#/game/${enc(g.id)}/${defTab(g)}"><span class="gdv-thumb gdv-tint${tintOf(g.id)}" aria-hidden="true">${tile}${badge}</span>
      <span class="gdv-cbody"><span class="gdv-crow"><b class="gdv-ell">${esc(gname(g))}</b>${pill(p ? 'Long project' : t, p ? 'v' : c)}</span>
        <span class="gdv-small">${esc(meta)}</span><span class="gdv-small gdv-ell">${esc(line)}</span>
        ${busy(g) ? `<span class="gdv-bar" aria-hidden="true"><i style="width:${Math.max(4, Math.min(100, N(g.pct)))}%"></i></span>` : ''}</span></a>`;
  }
  /* a small drawn scene for a game with no screenshot yet (decoration only: a runner, a night skyline, a tile board) */
  function sceneArt(k) {
    if (k === 0) return '<span class="gdv-sc gdv-sc-run"><i class="gdv-sc-par"></i><i class="gdv-sc-floor"></i><i class="gdv-sc-hero"></i><i class="gdv-sc-coin"></i></span>';
    if (k === 1) return '<span class="gdv-sc gdv-sc-city"><i></i><i></i><i></i><i class="gdv-sc-moon"></i><i class="gdv-sc-load"></i></span>';
    return `<span class="gdv-sc gdv-sc-tiles">${Array.from({length: 18}, (_, i) => `<i class="gdv-t${(i * 7 + 3) % 4}${i % 5 === 2 ? ' gdv-tglow' : ''}"></i>`).join('')}</span>`;
  }
  function waitHtml() {
    const wait = GAMES.filter(g => g.status === 'design_ready');
    return wait.length ? `<section class="gdv-sec"><h2>Waiting for your OK</h2>${wait.map(g => `<a class="gdv-wait" href="#/game/${enc(g.id)}/design"><span class="gdv-waitic" aria-hidden="true">${ico('doc', 20)}</span>
          <span class="gdv-waitt"><b>${esc(gname(g))} · design doc is ready</b><span>Read the one-page design. Say "theek hai" and Hoola builds it, or tell it what to change.</span></span>
          <span class="gdv-b">Read the design</span></a>`).join('')}</section>` : '';
  }
  const gamesHtml = () => GAMES.length ? `<div class="gdv-grid">${GAMES.slice(0, 8).map(card).join('')}</div>` : '<div class="gdv-panel gdv-mut">No games yet. Describe one above and Hoola writes its design first.</div>';
  function drawHome(main) {
    const playable = GAMES.find(g => N(g.version) && !projOf(g.id));
    const withProj = GAMES.find(g => projOf(g.id));
    const longHref = withProj ? `#/game/${enc(withProj.id)}/board` : playable ? `#/game/${enc(playable.id)}/board` : '#/games';
    const draft = S(PENDING && PENDING.brief);
    main.innerHTML = `<div class="gdv-home">
      <div class="gdv-herorow">
      <section class="gdv-hero">
        <span class="gdv-eyebrow gdv-mono">Game engine · Godot 4 · the Hoola crew</span>
        <h1>What game should we make today?</h1>
        <p class="gdv-lead">Say it in two lines. Hoola writes a short design doc, builds the game, plays it itself with bots, fixes what breaks, and gives you a private link to play. Nothing goes public until you tap.</p>
        ${hireGate()}
        <form class="gdv-ask" data-gdv-form="ask" aria-label="Describe your game">
          <label class="gdv-sr" for="gdvAsk">Describe your game</label>
          <textarea id="gdvAsk" rows="3" maxlength="2000" placeholder="A chaiwala runs through the station delivering cutting chai before the train leaves. Tap to jump, swipe to switch platforms. For kids 10+.">${esc(draft)}</textarea>
          <div class="gdv-askbar"><label class="gdv-sr" for="gdvOr">Screen</label>
            <select id="gdvOr">${ORIENT.map(o => `<option value="${esc(o)}">${esc(ORL[o] || o)}</option>`).join('')}</select>
            <span class="gdv-grow"></span><span class="gdv-small">Design doc first · then your OK</span>
            <button class="gdv-send" type="submit" aria-label="Start this game">${ico('up', 18)}</button></div>
        </form>
        <div class="gdv-chips gdv-left" role="group" aria-label="Start from a kind of game">${KINDS.map(([k, v]) => `<button class="gdv-chip" type="button" data-gdv-fill="${esc(v)}">${esc(k)}</button>`).join('')}</div>
      </section>
      ${loopHtml()}
      </div>
      <div id="gdvWaitBox">${waitHtml()}</div>
      <section class="gdv-sec" id="gdvStatsBox" aria-label="Your studio at a glance">${statsHtml()}</section>
      <section class="gdv-sec"><div class="gdv-sech"><h2>Your games</h2>${GAMES.length > 8 ? '<a href="#/games">View all</a>' : ''}</div>
        <div id="gdvGamesBox">${gamesHtml()}</div></section>
      <section class="gdv-steps" aria-label="How every game is made">${STEPS.map(([b, s], i) => `<div class="gdv-step" style="animation-delay:${i * 70}ms"><span class="gdv-mono gdv-stepn">0${i + 1}</span><b>${esc(b)}</b><span class="gdv-small">${esc(s)}</span></div>`).join('')}</section>
      <section class="gdv-sec"><h2>Or start from</h2><div class="gdv-starts">
        <button class="gdv-start" type="button" data-gdv-act="focus-ask"><span class="gdv-startic" aria-hidden="true">${ico('pen', 20)}</span><span><b>Describe it</b><span>Two lines in your own words.</span></span></button>
        <a class="gdv-start" href="${longHref}"><span class="gdv-startic" aria-hidden="true">${ico('board', 20)}</span><span><b>A long project</b><span>Turn a game that plays into a board, milestones and nightly builds.</span></span></a>
        <button class="gdv-start" type="button" data-gdv-fill="A game for Class 6 students that teaches "><span class="gdv-startic" aria-hidden="true">${ico('school', 20)}</span><span><b>A school lesson</b><span>A chapter becomes a game. No tracking, ever.</span></span></button>
        <a class="gdv-start" href="#/big"><span class="gdv-startic" aria-hidden="true">${ico('cube', 20)}</span><span><b>Your Unity or Unreal project</b><span>The crew works inside your own editor.</span></span></a>
      </div></section></div>`;
    if (PENDING && PENDING.orientation) { const s = $('#gdvOr'); if (s) s.value = PENDING.orientation; }
  }
  const FILTERS = [['all', 'All'], ['plays', 'Plays'], ['wait', 'Waiting for your OK'], ['busy', 'Being made'], ['failed', 'Did not work']];
  let FILTER = 'all';
  function allHtml() {
    const pick = g => FILTER === 'all' || (FILTER === 'plays' && N(g.version)) || (FILTER === 'wait' && g.status === 'design_ready') ||
      (FILTER === 'busy' && busy(g)) || (FILTER === 'failed' && ['failed', 'cancelled'].includes(g.status));
    const rows = GAMES.filter(pick);
    return rows.length ? `<div class="gdv-grid">${rows.map(card).join('')}</div>` : `<div class="gdv-panel gdv-mut">${GAMES.length ? 'No game in this list.' : 'No games yet.'} <a href="#/">Make one</a></div>`;
  }
  function drawAll(main) {
    main.innerHTML = `<div class="gdv-page"><div class="gdv-pageh"><h1>All games</h1><span class="gdv-mut">${GAMES.length} game${GAMES.length === 1 ? '' : 's'}</span></div>
      <div class="gdv-chips gdv-left" role="group" aria-label="Show">${FILTERS.map(([k, t]) => `<button class="gdv-chip" type="button" data-gdv-filter="${k}" aria-pressed="${FILTER === k}">${esc(t)}</button>`).join('')}</div>
      <div id="gdvAllBox">${allHtml()}</div></div>`;
  }

  /* ---------- start a game from the home ask ---------- */
  async function newConv(title) {
    const c = S((await api('POST', '/api/conversations')).id);
    if (title) api('PATCH', `/api/conversations/${enc(c)}`, {title}).catch(() => {});
    return c;
  }
  let STARTING = false;
  async function startGame(brief, orientation) {
    brief = S(brief).trim();
    if (brief.length < 8) { toast('Write your idea in 2-3 lines first.', true); $('#gdvAsk')?.focus(); return; }
    if (STARTING) return;
    PENDING = {brief, orientation};
    if (EMP_OK && !devWorking()) { drawHome($('#gdvMain')); toast('Hire the Game Developer first, then it starts.', true); return; }
    STARTING = true;
    const btn = APP.querySelector('form[data-gdv-form="ask"] .gdv-send'); if (btn) btn.disabled = true;
    try {
      // one pending conversation for every attempt: a refused start (limits, hire, a word the rules refuse) reuses it
      // next time instead of leaving an empty chat behind per attempt
      const conv = PENDING_CONV || await newConv('Game · new');
      PENDING_CONV = conv;
      let v;
      try { v = await api('POST', '/api/game', {brief, orientation, conversation_id: conv}); }
      catch (e) {
        if (e.status === 400 && /hired|hire/i.test(e.message)) { EMP_OK = true; EMP.hired = {...M(EMP.hired), game_dev: 'none'}; drawHome($('#gdvMain')); }
        throw e;
      }
      PENDING = null; PENDING_CONV = '';
      store.set(convKey(v.id), conv);
      api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Game · ${gname(v)}`}).catch(() => {});
      toast('Writing the design doc. Nothing is built until you say OK.');
      location.hash = `#/game/${enc(v.id)}/design`;
    } catch (e) { toast(e.message, true); if (btn) btn.disabled = false; }
    finally { STARTING = false; }
  }
  async function hire(key) {
    try {
      await api('POST', `/api/employees/${enc(key)}/hire`, {trust: 'seekh'});
      EMP.hired = {...M(EMP.hired), [key]: 'hired'};
      toast(`${S(empOf(key).name) || 'Employee'} is on your team.`);
      if (key === 'game_dev' && PENDING && parse().view === 'home') return startGame(PENDING.brief, PENDING.orientation);
    } catch (e) { toast(e.message, true); }
    try { const em = await api('GET', '/api/employees'); EMP = {employees: L(em.employees), hired: M(em.hired)}; } catch {}
    const r = parse();
    if (r.view === 'game') { drawPane(); } else route();
  }

  /* ---------- crew ---------- */
  const ROLES = [
    {page: 'world', key: 'procgen_dev', name: 'Worlds', line: 'Terrain, dungeons, cities and levels from a seed, checked that every place can be reached.'},
    {page: 'physics', key: 'physics_dev', name: 'Physics', line: 'Gravity, bounce and collisions measured in Godot against the textbook.'},
    {page: 'audio', key: 'audio_dev', name: '3D sound', line: 'Sound that comes from the left or right, rooms that echo, loudness kept even.'},
    {page: 'haptics', key: 'haptics_dev', name: 'Haptics', line: 'One buzz pattern per meaning, with an off switch always.'},
    {page: 'net', key: 'netcode_dev', name: 'Multiplayer', line: 'Bots play over three kinds of network; no two players see a different game.'},
    {page: 'xr', key: 'xr_dev', name: 'VR / AR', line: 'Comfort rules, hand gestures and a test room you open in a headset.'},
    {page: 'sim', key: 'sim_dev', name: 'Simulators', line: 'Orbit, flight and driving, checked against known answers.'},
    {page: 'twin', key: 'twin_arch', name: 'Digital twin', line: 'A model of your shop or warehouse, every number traced to its source.'},
    {page: 'vfx', key: 'vfx_td', name: 'VFX pipeline', line: 'Naming, colour and render queues for film and effects teams.'},
    {page: 'runtime', key: 'game_dev', name: 'Ask Hoola in Godot', line: 'A panel inside your own Godot editor that talks to this crew.', withDev: true}];
  const roleOf = page => ROLES.find(r => r.page === page);
  function hireTag(key, withDev) {
    const st = hiredState(key);
    if (withDev) return st === 'hired' ? pill('With the Game Developer', 'ok') : pill('Needs the Game Developer', '');
    return st === 'hired' ? pill('Hired', 'ok') : st === 'paused' ? pill('Paused', 'warn') : pill('Not hired', '');
  }
  function drawCrew(host, gid, sid) {
    const base = gid ? `#/game/${enc(gid)}/crew/` : '#/crew/';
    const cls = gid ? 'gdv-role gdv-wrole' : 'gdv-role';
    const dev = empOf('game_dev');
    host.innerHTML = `<div class="gdv-page">${gid ? '' : '<div class="gdv-pageh"><h1>The crew</h1></div>'}
      <p class="gdv-lead gdv-left">The Game Developer leads the studio roles that build and review every task. Ten specialists can be hired for deeper work. Every number they give you is measured in code, then checked in the real engine.${gid ? (sid ? ' Here they work on this game’s long project.' : ' This game is not a long project yet, so they work on their own here.') : ''}</p>
      <div class="gdv-roles">
        <a class="${cls}" href="${base}game_dev"><span class="gdv-rh"><span class="gdv-ric" aria-hidden="true">${ico('pad', 18)}</span><b>Game Developer</b></span>${hireTag('game_dev')}<span class="gdv-small">${esc(S(dev.pitch) || 'Design doc, Godot build, bot playtests, the board and nightly builds.')}</span></a>
        ${ROLES.map(r => `<a class="${cls}" href="${base}${r.page}"><span class="gdv-rh"><span class="gdv-ric" aria-hidden="true">${ico(r.page === 'runtime' ? 'cube' : 'crew', 18)}</span><b>${esc(r.name)}</b></span>${hireTag(r.key, r.withDev)}<span class="gdv-small">${esc(r.line)}</span></a>`).join('')}
      </div></div>`;
  }
  function drawRole(host, page, sid, gid) {
    const back = gid ? `#/game/${enc(gid)}/crew` : '#/crew';
    if (page === 'game_dev') {
      const e = empOf('game_dev'), st = hiredState('game_dev');
      host.innerHTML = `<div class="gdv-page"><a class="gdv-backl" href="${back}">${ico('back', 15)}Crew</a>
        <div class="gdv-pageh"><h1>Game Developer</h1>${hireTag('game_dev')}</div>
        <div class="gdv-panel"><p>${esc(S(e.pitch))}</p>
          ${L(e.does).length ? `<h3>What it does</h3><ul>${L(e.does).map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
          ${L(e.never).length ? `<h3>What it never does</h3><ul>${L(e.never).map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
          <div class="gdv-acts">${st === 'hired' ? '<a class="gdv-b gdv-pri" href="#/">Make a game</a><a class="gdv-b" href="#/games">All games</a>' : `<button class="gdv-b gdv-pri" type="button" data-gdv-act="hire">${st === 'paused' ? 'Resume the Game Developer' : 'Hire the Game Developer'}</button>`}</div></div></div>`;
      return;
    }
    const r = roleOf(page);
    if (!r) { host.innerHTML = `<div class="gdv-page"><a class="gdv-backl" href="${back}">${ico('back', 15)}Crew</a><div class="gdv-panel">This role does not exist.</div></div>`; return; }
    const st = hiredState(r.key);
    host.innerHTML = `<div class="gdv-page"><div class="gdv-roleh"><a class="gdv-backl" href="${back}">${ico('back', 15)}Crew</a><span class="gdv-grow"></span>
        ${st !== 'hired' ? `<button class="gdv-b gdv-pri" type="button" data-gdv-act="hire" data-key="${esc(r.key)}">${st === 'paused' ? 'Resume' : 'Hire'} ${esc(S(empOf(r.key).name) || r.name)}</button>` : ''}</div>
      <div class="gdv-embedhost"></div></div>`;
    embed(host.querySelector('.gdv-embedhost'), page, sid);
  }
  function drawEmbedPage(main, page, title, line) {
    main.innerHTML = `<div class="gdv-page"><div class="gdv-pageh"><h1>${esc(title)}</h1></div><p class="gdv-lead gdv-left">${esc(line)}</p><div class="gdv-embedhost"></div></div>`;
    embed(main.querySelector('.gdv-embedhost'), page, '');
  }

  /* ---------- the game workspace ---------- */
  const TABS = [['design', 'Design'], ['play', 'Editor'], ['board', 'Board'], ['bible', 'Bible'], ['scenes', 'Scenes'], ['assets', 'Assets'], ['qa', 'QA'], '|',
    ['release', 'Release'], ['liveops', 'Live ops'], ['prov', 'Where it came from'], '|', ['crew', 'Crew']];
  const TAB_KEYS = TABS.filter(x => x !== '|').map(x => x[0]);
  const TAB_NAME = Object.fromEntries(TABS.filter(x => x !== '|'));
  async function openGame(id, tab, sub) {
    W.id = id; W.game = null; W.sig = '';
    APP.innerHTML = '<div class="gdv-loading gdv-pad">Loading the game…</div>';
    let g;
    try {
      [g] = await Promise.all([api('GET', `/api/game/${enc(id)}`), loadProjects(),
        api('GET', '/api/employees').then(em => { EMP = {employees: L(em.employees), hired: M(em.hired)}; }).catch(() => {})]);
    } catch (e) {
      if (W.id !== id) return;
      document.title = 'Hoola Game Dev';
      APP.innerHTML = `<div class="gdv-pad"><div class="gdv-panel"><p class="gdv-bad">${esc(e.status === 404 || /nahi mila/i.test(e.message) ? 'This game was not found. It may have been deleted.' : e.message)}</p><a class="gdv-b" href="#/">Back to Game Dev</a></div></div>`;
      W.id = ''; return;
    }
    if (W.id !== id) return;
    W.game = g; W.tab = TAB_KEYS.includes(tab) ? tab : defTab(g); W.sub = sub || '';
    document.title = `${gname(g)} · Hoola Game Dev`;
    APP.innerHTML = `<div class="gdv-ws">
      <header class="gdv-top"></header>
      <div class="gdv-body2">
        <section class="gdv-chat" aria-label="Chat with Hoola about this game">
          <div class="gdv-dockh"><span class="gdv-hm" aria-hidden="true"></span><b>Hoola</b><span class="gdv-mono gdv-mut gdv-ell">this game only</span></div>
          <div class="gdv-msgs hck-dark" id="gdvMsgs"></div>
          <form class="gdv-kitcomp hck-dark" data-gdv-form="thread" aria-label="Message Hoola">
            <label class="gdv-sr" for="gdvTh">Message Hoola about this game</label>
            <div id="gdvBar"></div>
            <span class="gdv-small gdv-ell">Only about ${esc(gname(g))}</span>
          </form>
        </section>
        <section class="gdv-game" aria-label="Game"><nav class="gdv-tabs" aria-label="Game pages"></nav><div class="gdv-pane" id="gdvPane"></div></section>
      </div></div>`;
    mountBar();                                                 // the kit's bar, made once: no poll ever redraws it
    drawTop(); drawTabs(); drawPane(); startPoll();
    openThread();
  }
  function drawTop() {
    const g = W.game, top = APP.querySelector('header.gdv-top'); if (!g || !top) return;
    const [t, c] = longStatus(g), fps = M(g.numbers).fps_server;
    top.innerHTML = `<a class="gdv-homemark" href="#/" aria-label="Hoola Game Dev home">${ico('pad', 17)}</a><span class="gdv-slash" aria-hidden="true">/</span>
      <b class="gdv-title gdv-ell">${esc(gname(g))}</b><span class="gdv-small gdv-mono">${esc(g.number)}</span>${pill(t, c)}<span class="gdv-grow"></span>
      ${N(g.version) ? `<span class="gdv-echip gdv-mono">Godot · web build v${N(g.version)}</span>` : ''}
      ${fps != null && N(fps) > 0 ? `<span class="gdv-echip gdv-mono gdv-${N(fps) >= 50 ? 'okt' : 'warnt'}">${esc(numStr(fps))} fps on the server</span>` : ''}
      <button class="gdv-b" type="button" data-gdv-act="history">History</button>
      <a class="gdv-b" href="#/game/${enc(g.id)}/play">Play</a>
      <a class="gdv-b gdv-dark" href="#/game/${enc(g.id)}/release">Publish</a>`;
  }
  function drawTabs() {
    const nav = APP.querySelector('nav.gdv-tabs'); if (!nav || !W.game) return;
    nav.innerHTML = TABS.map(x => x === '|' ? '<span class="gdv-tsep" aria-hidden="true"></span>'
      : `<a class="gdv-tab" data-gdv-tab="${x[0]}" href="#/game/${enc(W.game.id)}/${x[0]}"${W.tab === x[0] ? ' aria-current="page"' : ''}>${esc(x[1])}</a>`).join('');
  }
  function paneEl() { return $('#gdvPane'); }
  function drawPane() {
    const pane = paneEl(), g = W.game; if (!pane || !g) return;
    stopEmbed();
    const sid = sidOf(g.id);
    if (W.tab === 'design') { pane.innerHTML = designHtml(g); W.sig = sigOf(g); return; }
    if (W.tab === 'play') {
      // the game she is playing must never restart because the NEXT version moved on (building -> testing ...): keep the
      // very same iframe node whenever the play link is unchanged, and redraw everything around it
      // (moving an iframe in the DOM reloads it too, so the stage holding it is not touched at all - only the column beside it)
      // the key is the play link + the version: a NEW version reloads the viewport (she should play what is live), a
      // build that is only moving along (building -> testing) leaves the running game alone
      const oldPlay = pane.querySelector('.gdv-play'), oldKey = oldPlay?.querySelector('.gdv-stage')?.dataset.key;
      const tmp = document.createElement('div'); tmp.innerHTML = playHtml(g, sid);
      const newPlay = tmp.querySelector('.gdv-play'), newKey = newPlay?.querySelector('.gdv-stage')?.dataset.key;
      if (oldPlay && newPlay && oldKey && oldKey === newKey) {
        [...oldPlay.children].forEach(c => { if (!c.classList.contains('gdv-stage')) c.remove(); });
        [...newPlay.children].forEach(c => { if (!c.classList.contains('gdv-stage')) oldPlay.appendChild(c); });
      } else { pane.innerHTML = ''; while (tmp.firstChild) pane.appendChild(tmp.firstChild); }
      paintQr(pane); W.sig = sigOf(g);
      pane.querySelectorAll('.gdv-shots img').forEach(img => img.addEventListener('error', () => { const p = img.closest('.gdv-panel'); img.remove(); if (p && !p.querySelector('.gdv-shots img')) p.remove(); }));
      return;
    }
    if (W.tab === 'crew') {
      pane.innerHTML = '';
      const host = document.createElement('div'); pane.appendChild(host);
      return W.sub ? drawRole(host, W.sub, sid, g.id) : drawCrew(host, g.id, sid);
    }
    if (PROJECT_PAGES.includes(W.tab)) {
      if (!sid) { pane.innerHTML = noProjectHtml(g, W.tab); return; }
      pane.innerHTML = '';
      return embed(pane, W.tab, sid);
    }
  }
  // the pane is rebuilt only when the game really changed; pct / stage are written into the progress card in place,
  // so the Play tab's iframe (and anything she typed) survives a build that is still running
  const sigOf = g => [g.status, g.version, g.versions, S(g.design).length, g.error, S(g.play_url || g.url)].join('|');
  function progressInPlace(g) {
    APP.querySelectorAll('.gdv-prog').forEach(card => {
      const pct = Math.round(N(g.pct));
      const say = card.querySelector('[data-gdv-say]'); if (say) say.textContent = S(g.say) || stOf(g)[0];
      const pc = card.querySelector('[data-gdv-pct]'); if (pc) pc.textContent = pct + '%';
      const bar = card.querySelector('.gdv-bar'); if (bar) { bar.setAttribute('aria-valuenow', String(pct)); const i = bar.querySelector('i'); if (i) i.style.width = Math.max(4, Math.min(100, N(g.pct))) + '%'; }
      const st = card.querySelector('[data-gdv-stage]'); if (st) { st.textContent = S(g.stage); st.hidden = !S(g.stage); }
    });
  }

  /* the build pipeline: Hoola's real stages, the one it is on now glowing, work flowing along the line into it */
  const PIPE = [['Design', 'one page'], ['Code', 'GDScript'], ['Build', 'in Godot'], ['Bots play', 'phone speeds'], ['Your link', 'to play']];
  const PIPE_AT = {designing: 0, design_ready: 1, queued: 1, writing: 1, building: 2, testing: 3, done: 4};
  function pipeHtml(g) {
    const at = PIPE_AT[S(g.status)] ?? 0;
    return `<ol class="gdv-pipe" aria-label="Where the build is: step ${at + 1} of ${PIPE.length}, ${esc(PIPE[at][0])}">${PIPE.map(([b, s], i) =>
      `<li class="gdv-pn gdv-pn-${i < at ? 'done' : i === at ? 'now' : 'next'}"><span class="gdv-pnic" aria-hidden="true">${i < at ? ico('check', 14) : `<span class="gdv-mono">${i + 1}</span>`}</span><b>${b}</b><span class="gdv-mono">${s}</span></li>`).join('')}</ol>`;
  }
  function progressHtml(g) {
    return `<div class="gdv-panel gdv-prog" role="status">${pipeHtml(g)}<div class="gdv-progh"><span class="gdv-dot gdv-v gdv-glow" aria-hidden="true"></span><b data-gdv-say>${esc(S(g.say) || stOf(g)[0])}</b><span class="gdv-small gdv-mono" data-gdv-pct>${Math.round(N(g.pct))}%</span></div>
      <div class="gdv-bar" role="progressbar" aria-label="Progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(N(g.pct))}"><i style="width:${Math.max(4, Math.min(100, N(g.pct)))}%"></i></div>
      <p class="gdv-small" data-gdv-stage${g.stage ? '' : ' hidden'}>${esc(g.stage)}</p>
      <p class="gdv-small">${g.status === 'designing' ? 'The design doc usually takes under a minute. Nothing is built until you say OK.' : 'Building takes a few minutes. Hoola plays the game before you see it.'}</p>
      <div class="gdv-acts"><button class="gdv-b" type="button" data-gdv-act="cancel">Stop</button></div></div>`;
  }
  function designHtml(g) {
    const s = S(g.status), doc = S(g.design).trim();
    const docHtml = doc ? `<article class="gdv-doc"><div class="gdv-filebar"><span class="gdv-filetab gdv-mono">design.md</span><span class="gdv-small">Design doc${N(g.versions) ? ` · ${N(g.versions)} version${N(g.versions) > 1 ? 's' : ''} built` : ''}</span></div><div class="gdv-md">${md(doc)}</div>` : '';
    if (busy(g)) return `<div class="gdv-col">${progressHtml(g)}${doc && N(g.version) ? docHtml + '</article>' : ''}</div>`;
    if (s === 'design_ready') return `<div class="gdv-col">${docHtml || '<article class="gdv-doc"><p class="gdv-mut">The design doc is empty.</p>'}
      <div class="gdv-acts gdv-docacts"><button class="gdv-b gdv-dark" type="button" data-gdv-act="approve">Theek hai, bana do</button>
        <button class="gdv-b" type="button" data-gdv-act="change" aria-expanded="false" aria-controls="gdvChBox">Change something</button>
        <a class="gdv-b" href="#/">Not now</a></div>
      <div class="gdv-chbox" id="gdvChBox" hidden><label for="gdvChange">What should change in the design?</label>
        <textarea id="gdvChange" rows="3" maxlength="1500" placeholder="e.g. make it two-player, easier for kids"></textarea>
        <div class="gdv-acts"><button class="gdv-b gdv-pri" type="button" data-gdv-act="send-change">Rewrite the design</button><button class="gdv-b" type="button" data-gdv-act="change-cancel">Cancel</button></div></div>
      <p class="gdv-small">Building takes a few minutes. Hoola plays the game before you see it.</p></article>
      ${dangerHtml(g)}</div>`;
    if (s === 'failed' || s === 'cancelled') {
      const again = N(g.version) ? '' : `<button class="gdv-b gdv-pri" type="button" data-gdv-act="retry">Try again with the same idea</button>`;
      return `<div class="gdv-col"><div class="gdv-panel"><h3>${s === 'failed' ? 'This game did not get built' : 'This game was stopped'}</h3>
        ${g.error ? `<p class="gdv-bad">${esc(g.error)}</p>` : ''}
        <p class="gdv-small">${N(g.version) ? 'The version that played still works. Ask for a change below.' : 'A first build that does not work cannot be retried in place, so “Try again” starts a fresh game from the same words. Or tell Hoola in the chat what to change.'}</p>
        <div class="gdv-acts">${again}</div></div>
        ${N(g.version) ? changeBox() : ''}${doc ? docHtml + '</article>' : ''}${dangerHtml(g)}</div>`;
    }
    return `<div class="gdv-col">${N(g.version) ? `<div class="gdv-panel gdv-okrow"><span>Version ${N(g.version)} plays.</span><a class="gdv-b gdv-dark" href="#/game/${enc(g.id)}/play">Play it</a></div>${changeBox()}` : ''}
      ${docHtml ? docHtml + '</article>' : '<div class="gdv-panel gdv-mut">No design doc yet.</div>'}${dangerHtml(g)}</div>`;
  }
  const changeBox = () => `<div class="gdv-panel"><label for="gdvNewVer"><b>What should change?</b></label>
    <textarea id="gdvNewVer" rows="2" maxlength="1500" placeholder="e.g. make it faster, add a shield power-up"></textarea>
    <div class="gdv-acts"><button class="gdv-b gdv-pri" type="button" data-gdv-act="new-version">Make a new version</button><span class="gdv-small">The current version keeps working.</span></div></div>`;
  const dangerHtml = g => busy(g) ? '' : `<div class="gdv-acts gdv-danger"><button class="gdv-b gdv-del" type="button" data-gdv-act="delete">Delete this game</button></div>`;

  const CHECK = {guard: "The code passed Hoola's safety check", play_headless: 'The game starts and runs in Godot',
    export_web: 'The web build was exported', playtest: 'Hoola played it in a browser'};
  function playHtml(g, sid) {
    const url = safeUrl(g.play_url || g.url);
    if (!url) {
      return `<div class="gdv-col">${busy(g) ? progressHtml(g) : ''}<div class="gdv-panel"><h3>Not built yet</h3>
        <p class="gdv-mut">${g.status === 'design_ready' ? 'The design is waiting for your OK. Say “Theek hai, bana do” on the Design tab and Hoola builds it.' : busy(g) ? 'Hoola is still making it. The play link appears here when it plays.' : 'There is no version that plays yet.'}</p>
        <div class="gdv-acts"><a class="gdv-b" href="#/game/${enc(g.id)}/design">Open the design</a></div></div></div>`;
    }
    const nums = M(g.numbers), abs = absUrl(url), land = S(g.orientation) === 'landscape', sq = S(g.orientation) === 'square';
    const checks = L(g.checks), warns = L(g.warnings), hist = L(g.history).slice().reverse();
    const ckRow = (ok, text, extra) => `<div class="gdv-ck gdv-ck-${ok === true ? 'ok' : ok === false ? 'bad' : 'na'}">${ico(ok === true ? 'check' : ok === false ? 'cross' : 'circle', 15)}<span>${esc(text)}${extra ? `<span class="gdv-small"> ${esc(extra)}</span>` : ''}</span></div>`;
    // performance, only what Hoola measured; each with a bar against a plain target so it reads at a glance
    const meter = (v, unit, label, pctOf, good) => v === null || v === undefined || v === '' ? '' :
      `<div class="gdv-meter"><span class="gdv-meterh"><span>${esc(label)}</span><b class="gdv-mono">${esc(numStr(v))}${unit}</b></span><span class="gdv-meterbar"><i class="gdv-fps-${good ? 'ok' : 'warn'}" style="width:${Math.max(4, Math.min(100, pctOf))}%"></i></span></div>`;
    const fps = nums.fps_server, ld = nums.load_s, mb = nums.download_mb;
    const perf = meter(fps, '', 'Frame rate on the server', N(fps) / 60 * 100, N(fps) >= 50) + meter(ld, ' s', 'Time to start', 100 - N(ld) * 10, N(ld) <= 5) + meter(mb, ' MB', 'Download', N(mb) / 50 * 100, N(mb) <= 25);
    // the output log: the real checks, warnings and version notes, in the order they happened
    const logRows = [];
    // plain strings here; every row is esc()'d where it is drawn below
    checks.forEach(c => logRows.push([c.ok === true ? 'ok' : c.ok === false ? 'err' : 'info', (CHECK[c.step] || S(c.step)) + (L(c.errors).length ? ' · ' + L(c.errors).slice(0, 2).join('; ') : '')]));
    warns.forEach(w => logRows.push(['warn', S(w)]));
    L(g.history).forEach(v => logRows.push([v.ok ? 'ok' : 'err', 'v' + N(v.n) + (v.ok ? ' built and played' : ' did not play') + (S(v.words) ? ' · ' + S(v.words) : ''), v.at]));
    const TAG = {ok: 'ok', err: 'error', warn: 'warn', info: 'note'};
    const key = url + '|' + N(g.version);
    return `<div class="gdv-play gdv-editor">
      <section class="gdv-stage gdv-vp" aria-label="Viewport" data-key="${esc(key)}" data-src="${esc(url)}" data-dev="phone">
        <div class="gdv-vph"><b>Viewport</b><span class="gdv-mono gdv-mut">2D · ${esc(ORL[g.orientation] || 'phone')}</span><span class="gdv-grow"></span>
          <span class="gdv-vplive gdv-mono" data-gdv-vplive><span class="gdv-dot gdv-ok gdv-glow" aria-hidden="true"></span>running · version ${N(g.version)}</span></div>
        <div class="gdv-vptools" role="toolbar" aria-label="Play controls">
          <button class="gdv-tb gdv-tb-go" type="button" data-gdv-vp="play" aria-label="Play from the start" title="Play from the start">${ico('play', 15)}</button>
          <button class="gdv-tb" type="button" data-gdv-vp="stop" aria-label="Stop the game" title="Stop">${ico('stop', 14)}</button>
          <span class="gdv-tbsep" aria-hidden="true"></span>
          <span class="gdv-seg2" role="group" aria-label="Screen size">${[['phone', 'Phone'], ['tablet', 'Tablet'], ['desktop', 'Computer']].map(([k, t]) => `<button class="gdv-tb" type="button" data-gdv-vp="dev" data-dev="${k}" aria-pressed="${k === 'phone'}">${t}</button>`).join('')}</span>
          <span class="gdv-grow"></span>
          <button class="gdv-tb" type="button" data-gdv-vp="full" aria-label="Full screen" title="Full screen">${ico('full', 15)}</button>
          <a class="gdv-tb" href="${esc(url)}" target="_blank" rel="noopener" aria-label="Open in a new tab" title="Open in a new tab">${ico('ext', 15)}</a>
        </div>
        <div class="gdv-vpcanvas">
          <div class="gdv-phone gdv-${land ? 'land' : sq ? 'square' : 'port'}"><iframe title="${esc(gname(g))}" src="${esc(url)}" sandbox="allow-scripts allow-pointer-lock" allow="fullscreen" loading="lazy"></iframe></div>
          <div class="gdv-vpstop" hidden><b>Stopped</b><span class="gdv-small">Press play to start the game again from the beginning.</span><button class="gdv-b gdv-pri" type="button" data-gdv-vp="play">${ico('play', 15)}Play</button></div>
        </div>
        <p class="gdv-small gdv-vpnote">This is the real game, the same web build your private link opens, running here in your browser.</p>
      </section>
      <aside class="gdv-side2 gdv-insp" aria-label="Inspector">
        <div class="gdv-ih">Inspector<span class="gdv-grow"></span><span class="gdv-mono gdv-mut">${esc(g.number)}</span></div>
        <div class="gdv-isec"><span class="gdv-ilabel gdv-mono">game</span>
          <div class="gdv-prop"><span>Version</span><span class="gdv-fld gdv-mono">v${N(g.version)}</span></div>
          <div class="gdv-prop"><span>Screen</span><span class="gdv-fld">${esc(ORL[g.orientation] || S(g.orientation))}</span></div>
          <div class="gdv-prop"><span>Versions</span><span class="gdv-fld gdv-mono">${N(g.versions) || hist.length}</span></div></div>
        ${perf ? `<div class="gdv-isec"><span class="gdv-ilabel gdv-mono">performance</span>${perf}</div>` : ''}
        <div class="gdv-isec"><span class="gdv-ilabel gdv-mono">Hoola played version ${N(g.version)} before you</span>
          ${checks.map(c => ckRow(c.ok === true ? true : c.ok === false ? false : null, CHECK[c.step] || S(c.step), L(c.errors).length ? L(c.errors).slice(0, 2).join('; ') : '')).join('')}
          ${warns.map(w => ckRow(null, 'Worth a look:', S(w))).join('')}
          ${ckRow(null, 'Is it fun? Only you can say. Not assessed.')}
          ${g.notes ? `<p class="gdv-small">${esc(g.notes)}</p>` : ''}</div>
        <div class="gdv-isec gdv-link"><img class="gdv-qr" data-qr="${esc(abs)}" alt="QR code to play on your phone">
          <div><b>Private play link</b><span class="gdv-small">Scan with your phone, or copy the link. Only people you give it to can open it.</span>
            <div class="gdv-acts"><button class="gdv-b" type="button" data-gdv-act="copy" data-url="${esc(abs)}">${ico('copy', 15)}Copy link</button><button class="gdv-b" type="button" data-gdv-act="source">${ico('dl', 15)}Download source</button></div></div></div>
        ${busy(g) ? progressHtml(g) : changeBox()}
      </aside>
      <section class="gdv-dock" aria-label="Output and versions">
        <div class="gdv-docksec"><div class="gdv-ih">Output<span class="gdv-grow"></span><span class="gdv-mono gdv-mut">Hoola's playtest</span></div>
          <div class="gdv-log">${logRows.length ? logRows.map((r, i) => `<div class="gdv-logl" style="animation-delay:${Math.min(i, 12) * 90}ms"><span class="gdv-mono gdv-mut">${esc(r[2] ? clockOf(isoS(r[2])) : '')}</span><span class="gdv-logt gdv-logt-${r[0]} gdv-mono">${TAG[r[0]]}</span><span>${esc(r[1])}</span></div>`).join('') : '<p class="gdv-small">No output yet.</p>'}</div></div>
        <div class="gdv-docksec" id="gdvVersions" tabindex="-1"><div class="gdv-ih">Versions<span class="gdv-grow"></span><span class="gdv-mono gdv-mut">timeline</span></div>
          ${hist.length ? `<div class="gdv-tl" aria-hidden="true">${L(g.history).map(v => `<span class="gdv-kf gdv-kf-${N(v.n) === N(g.version) ? 'live' : v.ok ? 'ok' : 'bad'}" title="v${N(v.n)}"></span>`).join('')}</div>` : ''}
          ${hist.length ? hist.map(v => `<div class="gdv-ver"><b class="gdv-mono">v${N(v.n)}</b><span class="gdv-ell2">${esc(S(v.words) || S(v.notes) || (N(v.n) === 1 ? 'First version' : ''))}${L(v.errors).length && !v.ok ? `<span class="gdv-small gdv-bad"> ${esc(L(v.errors)[0])}</span>` : ''}</span>
            ${N(v.n) === N(g.version) ? pill('Live', 'ok') : !v.ok ? pill('Did not play', 'bad') : sid ? `<button class="gdv-linkb" type="button" data-gdv-act="restore" data-n="${N(v.n)}">Go back to this</button>` : pill('Kept', '')}</div>`).join('') : '<p class="gdv-small">No versions yet.</p>'}
          ${!sid && hist.length > 1 ? '<p class="gdv-small">Going back to an older version needs a long project (Board tab).</p>' : ''}</div>
        ${L(g.shots).length ? `<div class="gdv-docksec"><div class="gdv-ih">From Hoola's playtest</div><div class="gdv-shots">${L(g.shots).map(safeUrl).filter(Boolean).map(s => `<img src="${esc(s)}" alt="Screenshot from Hoola's playtest" loading="lazy">`).join('')}</div></div>` : ''}
      </section></div>`;
  }
  function paintQr(root) {
    root.querySelectorAll('img[data-qr]').forEach(img => { try { const q = window.qrcode(0, 'M'); q.addData(img.dataset.qr); q.make(); img.src = q.createDataURL(4, 2); } catch { img.remove(); } });
  }
  function noProjectHtml(g, tab) {
    const can = N(g.version) > 0;
    return `<div class="gdv-col"><div class="gdv-panel gdv-noproj"><h3>${esc(TAB_NAME[tab])} belongs to a long project</h3>
      <p>A long project wraps this game in a task board, milestones, the Game Bible, scenes, assets, a QA farm, release builds and live ops. Each task is one small change that waits for your OK.</p>
      ${can ? `<label for="gdvGoal">Goal (optional)</label><input id="gdvGoal" maxlength="1500" placeholder="e.g. release on the Play Store in 6 months">` : '<p class="gdv-small">The game must play first: approve its design on the Design tab and let Hoola build it.</p>'}
      <div class="gdv-acts"><button class="gdv-b gdv-pri" type="button" data-gdv-act="make-project"${can ? '' : ' disabled'}>Make it a long project</button></div></div></div>`;
  }

  /* ---------- poll the open game ---------- */
  function startPoll() {
    clearTimeout(POLL); POLL = null;
    if (!W.game || !busy(W.game)) return;
    const id = W.id;
    POLL = setTimeout(async () => {
      if (W.id !== id || parse().view !== 'game') return;
      let g;
      try { g = await api('GET', `/api/game/${enc(id)}`); }
      catch (e) {
        if (e.status === 404 || /nahi mila/i.test(e.message)) { if (W.id === id) { stopAll(); W.id = ''; toast('This game was deleted.'); location.hash = '#/'; } return; }
        return startPoll();
      }
      if (W.id !== id) return;
      const was = busy(W.game); W.game = g; drawTop();
      if (was && !busy(g)) {
        const c = store.get(convKey(id)); if (c && S(g.title)) api('PATCH', `/api/conversations/${enc(c)}`, {title: `Game · ${gname(g)}`}).catch(() => {});
        await loadProjects(); toast(N(g.version) ? 'Ready to play.' : g.status === 'design_ready' ? 'The design doc is ready.' : S(g.say)); }
      const pane = paneEl();
      const typing = pane && ((pane.contains(document.activeElement) && /TEXTAREA|INPUT|SELECT/.test(document.activeElement.tagName)) ||
        ['#gdvChange', '#gdvNewVer', '#gdvGoal'].some(q => S(pane.querySelector(q)?.value).trim()));
      if (['design', 'play'].includes(W.tab) && sigOf(g) !== W.sig && !typing) drawPane();
      else progressInPlace(g);
      if (!THREAD.rows.length) drawMsgs();
      startPoll();
    }, 3000);
  }
  async function reloadGame() {
    if (!W.id) return;
    const id = W.id;
    let g;
    try { g = await api('GET', `/api/game/${enc(id)}`); }
    catch (e) {
      if ((e.status === 404 || /nahi mila/i.test(e.message)) && W.id === id) { stopAll(); W.id = ''; toast('This game was deleted.'); location.hash = '#/'; return; }
      toast(e.message, true); return;
    }
    if (W.id !== id) return;
    W.game = g;
    await loadProjects(); if (W.id !== id) return; drawTop(); drawPane(); startPoll(); drawMsgs();
  }

  /* ---------- actions ---------- */
  async function gameAct(k, el) {
    const g = W.game; if (!g) return;
    const q = enc(g.id);
    try {
      if (k === 'approve') { el.disabled = true; await api('POST', `/api/game/${q}/approve`, {}); toast('Building. Hoola plays it before it reaches you.'); return reloadGame(); }
      if (k === 'change') { const b = $('#gdvChBox'); if (b) { b.hidden = !b.hidden; el.setAttribute('aria-expanded', String(!b.hidden)); if (!b.hidden) $('#gdvChange')?.focus(); } return; }
      if (k === 'change-cancel') { const b = $('#gdvChBox'); if (b) b.hidden = true; return; }
      if (k === 'send-change') {
        const fb = S($('#gdvChange')?.value).trim();
        if (!fb) { toast('Write what should change in the design.', true); return; }
        el.disabled = true; await api('POST', `/api/game/${q}/approve`, {feedback: fb}); toast('Rewriting the design…'); return reloadGame();
      }
      if (k === 'new-version') {
        const w = S($('#gdvNewVer')?.value).trim();
        if (!w) { toast('Write what should change first.', true); return; }
        el.disabled = true; await api('POST', `/api/game/${q}/change`, {words: w}); toast('Making a new version. The current one keeps working.'); return reloadGame();
      }
      if (k === 'cancel') { el.disabled = true; await api('POST', `/api/game/${q}/cancel`, {}); toast('Stopped.'); return reloadGame(); }
      if (k === 'retry') {
        el.disabled = true;
        // the FULL brief (GET /api/game/<id> returns it untruncated) and a FRESH thread: the old game's talk stays with it
        const full = await api('GET', `/api/game/${q}`).catch(() => g);
        const conv = PENDING_CONV || await newConv('Game · new');
        PENDING_CONV = conv;
        const v = await api('POST', '/api/game', {brief: S(full.brief || g.brief), orientation: S(g.orientation) || 'portrait', conversation_id: conv});
        PENDING_CONV = '';
        store.set(convKey(v.id), conv);
        api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Game · ${gname(v)}`}).catch(() => {});
        toast('Starting again from the same idea.');
        location.hash = `#/game/${enc(v.id)}/design`; return;
      }
      if (k === 'delete') {
        if (!confirm(`Delete “${gname(g)}” and its play link? This cannot be undone.`)) return;
        await api('DELETE', `/api/game/${q}`); store.del(convKey(g.id)); toast('Deleted.'); location.hash = '#/'; return;
      }
      if (k === 'restore') {
        const n = N(el.dataset.n), sid = sidOf(g.id);
        if (!sid || !n) return;
        if (!confirm(`Bring version ${n}'s code back as a new version? The checks and Hoola's playtest run again.`)) return;
        el.disabled = true; await api('POST', `/api/gamestudio/${enc(sid)}/restore`, {n}); toast(`Bringing back version ${n}…`); return reloadGame();
      }
      if (k === 'copy') {
        const u = S(el.dataset.url);
        try { await navigator.clipboard.writeText(u); toast('Link copied.'); }
        catch { const t = document.createElement('textarea'); t.value = u; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); toast('Link copied.'); } catch { toast(u); } t.remove(); }
        return;
      }
      if (k === 'source') {
        const r = await api('GET', `/api/game/${q}/source`, undefined, {raw: true});
        const blob = await r.blob(), a = document.createElement('a');
        const m = S(r.headers.get('content-disposition')).match(/filename="?([^";]+)"?/i);
        a.href = URL.createObjectURL(blob); a.download = m ? m[1] : 'game.zip';
        document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
        return;
      }
      if (k === 'make-project') {
        el.disabled = true;
        const goal = S($('#gdvGoal')?.value).trim();
        await api('POST', '/api/gamestudio', {game: g.id, goal, conversation_id: store.get(convKey(g.id)) || ''});
        toast('Long project started. Add tasks or let Hoola plan them.');
        await loadProjects(); drawPane(); return;
      }
      if (k === 'history') {
        if (W.tab !== 'play') { location.hash = `#/game/${q}/play`; setTimeout(() => $('#gdvVersions')?.focus(), 300); }
        else $('#gdvVersions')?.focus();
        $('#gdvVersions')?.scrollIntoView({block: 'start'});
      }
    } catch (e) { toast(e.message, true); if (el) el.disabled = false; }
  }

  /* ---------- this game's own Hoola thread (never the home chat) ----------
     HOOLA CHAT KIT: the thread is drawn by the shared kit (chatkit.js, mounted on #gdvThread) and the box she types
     in is the kit's bar, so words land, work shows and text is spaced exactly as in the main Hoola chat. This page
     still reads the conversation by polling; each read hands the kit the whole list (sync) and the kit lands only what
     is new. History is drawn whole. A poll never touches the bar, so what she is typing stays. */
  const THREAD = {game: '', conv: '', rows: [], live: '', waiting: false, since: 0, started: 0, startedS: 0, timer: null, steps: [], stepsRead: false,
    pend: '', told: new Map(), turns: [], liveTurn: '', liveId: '', turn: '', busy: undefined, haltAt: 0, redo: [], redoSrv: [], held: [], words: 0, kitKey: ''};
  let TICK = null, KIT = null, BAR = null;
  const KIT_ACTS = ['copy', 'aloud'];             // + up / down once the newest reply's turn is known, + again in a real talk
  const KIT_OPTS = {acts: KIT_ACTS, jump: true, onAct: kitAct};
  function tickClocks() { APP.querySelectorAll('[data-t0]').forEach(e => { const t0 = Number(e.dataset.t0); if (t0) e.textContent = dur(nowS() - t0); }); }
  function startTick() { if (!TICK) TICK = setInterval(tickClocks, 1000); tickClocks(); }
  function dropKit() { if (KIT) { try { KIT.clear(); } catch {} } KIT = null; }
  function mountKit() {
    const box = $('#gdvMsgs'); if (!box || !window.HoolaChat) return null;
    if (KIT && KIT.el.isConnected) return KIT;
    dropKit();
    box.innerHTML = '<div id="gdvThread" class="hck-tight"></div>';
    KIT_OPTS.scroller = box;
    KIT = window.HoolaChat.mount(box.firstChild, KIT_OPTS);
    return KIT;
  }
  function mountBar() {
    const host = $('#gdvBar'); BAR = null; if (!host || !window.HoolaChat) return;
    BAR = window.HoolaChat.bar(host, {placeholder: 'Ask Hoola for a change…', onSend: v => ask(v), onStop: stopTurn});
    BAR.input.id = 'gdvTh'; BAR.input.maxLength = 4000;
  }
  function fillBar(v) { const t = $('#gdvTh'); if (!t) return false; if (BAR && BAR.input === t) BAR.value = S(v); else t.value = S(v); t.focus(); return true; }
  // the game's own thread: what this browser remembers, else the conversation the server recorded for the game, else a
  // new one. A stored thread is forgotten ONLY when the server says it does not exist (404); any other failure is a
  // real error (offline, 500) and must not cost her the mapping.
  async function ensureConv() {
    const g = W.game;
    if (THREAD.conv && THREAD.game === g.id && THREAD.ok) return THREAD.conv;
    THREAD.game = g.id;
    let c = THREAD.conv || store.get(convKey(g.id)) || S(g.conversation_id);
    if (c) {
      try { await api('GET', `/api/conversations/${enc(c)}/messages?limit=1`); store.set(convKey(g.id), c); }
      catch (e) { if (e.status === 404) { store.del(convKey(g.id)); c = ''; } else throw e; }
    }
    if (!c) { c = await newConv(`Game · ${gname(g)}`); store.set(convKey(g.id), c); }
    THREAD.conv = c; THREAD.ok = true;
    return c;
  }
  async function openThread() {
    clearTimeout(THREAD.timer);
    let c = store.get(convKey(W.id));
    if (!c && W.game && S(W.game.conversation_id)) { c = S(W.game.conversation_id); store.set(convKey(W.id), c); }
    Object.assign(THREAD, {game: W.id, conv: c, ok: false, rows: [], live: '', waiting: false, since: 0, steps: [], stepsRead: false, startedS: 0,
      pend: '', told: new Map(), turns: [], liveTurn: '', liveId: '', turn: '', busy: undefined, haltAt: 0, redo: [], redoSrv: [], held: [], words: 0, kitKey: ''});
    drawMsgs();
    if (THREAD.conv) await readThread();
  }
  // the console's hint lines ride at the END of her message as "\n\n[Web console ...]"; a ] inside a game title (or a
  // message sent from another screen) must never let them show in her bubble, so cut at the FIRST hint marker
  const clean = t => { const x = S(t), i = x.indexOf('\n\n[Web console '); return i >= 0 ? x.slice(0, i) : x; };
  const tsec = a => { const t = S(a); if (!t) return 0; const ms = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(t) ? t : t + 'Z'); return isNaN(ms) ? 0 : ms / 1000; };
  const talkRows = () => THREAD.rows.filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
  /* one read of the timeline gives the steps of each turn, the turn id of each reply (for Good answer / Not right),
     whether the server is working on this chat right now, and which answers were asked again */
  async function readSteps(c) {
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/timeline?limit=200&steps=1`);
      if (c !== THREAD.conv) return;
      const by = new Map(), turns = [], evs = L(r.events);
      for (const ev of evs) {
        const pl = M(ev.payload), said = S(pl.text).trim();
        if (ev.kind === 'message' && pl.role === 'assistant' && pl.turn && said) turns.push({said, turn: S(pl.turn)});
        if (ev.kind !== 'step') continue;
        const k = S(pl.id) || ('e' + ev.id), at = tsec(ev.at), upd = tsec(ev.updated_at) || at;
        const x = by.get(k) || {k, label: S(pl.label) || S(pl.tool), at, state: 'run'};
        x.at = Math.min(x.at || at, at);
        if (pl.state !== 'running') { x.state = pl.state === 'error' ? 'error' : 'done'; x.end = Math.max(x.end || 0, upd); }
        if (pl.label) x.label = S(pl.label);
        by.set(k, x);
      }
      THREAD.steps = [...by.values()].filter(x => x.at).sort((a, b) => a.at - b.at);
      THREAD.turns = turns;
      if (typeof r.busy === 'boolean') THREAD.busy = r.busy;
      // "Ask again" made on any screen: the place (her message) and how many times it was asked again
      THREAD.redoSrv = L(r.branches).filter(b => b.kind === 'retry' && N(b.count) > 1 && N(b.active) === N(b.count) - 1).map(b => {
        const ev = evs.find(e => e.id === b.anchor); return ev ? {said: clean(M(ev.payload).text), at: tsec(ev.at), n: N(b.count) - 1} : null; }).filter(Boolean);
    } catch {}
  }
  const stepsBetween = (a, b) => L(THREAD.steps).filter(x => x.at >= a - 2 && (!b || x.at <= b + 2));
  /* "Ask again": the server keeps the old answer as an earlier version and runs her message once more, but the message
     list still carries both. The thread shows her message once, with the newest answer under it. */
  function shownRows() {
    const rows = talkRows();
    const cuts = THREAD.redo.map(x => ({...x}));
    for (const b of THREAD.redoSrv) {
      const first = rows.find(r => r.role === 'user' && clean(r.text) === b.said && tsec(r.at) >= b.at - 5);
      if (!first) continue;
      const mine = cuts.find(x => x.lo === Number(first.id));
      if (mine) mine.n = Math.max(mine.n, b.n); else cuts.push({lo: Number(first.id), hi: 0, said: b.said, n: b.n});
    }
    const gone = new Set();
    for (const x of cuts) {
      let seen = 0, cut = x.hi;
      for (const r of rows) if (r.role === 'user' && Number(r.id) > x.lo && seen < x.n && clean(r.text) === x.said) { seen++; cut = Math.max(cut, Number(r.id)); }
      for (const r of rows) if (Number(r.id) > x.lo && Number(r.id) <= cut) gone.add(r.id);
    }
    const all = rows.filter(r => !gone.has(r.id));
    const first = all.findIndex(r => r.role === 'user');
    return first < 0 ? [] : all.slice(first);
  }
  function chips(g) {
    if (g.status === 'design_ready') return ['Make it two-player', 'Easier for kids', 'Add a second level'];
    if (N(g.version)) return ['Make it a little faster', 'Add a power-up', 'Add Hindi words'];
    return ['What will version 1 have?', 'Make it easier for kids', 'Add a story'];
  }
  function introHtml(g) {
    return `<div class="gdv-chips gdv-left" role="group" aria-label="Suggestions">${chips(g).map(t => `<button class="gdv-chip gdv-sm" type="button" data-gdv-fill-th="${esc(t)}">${esc(t)}</button>`).join('')}</div>
      <p class="gdv-small">This chat is only about ${esc(gname(g))}. It stays here, not in your home chat.</p>`;
  }
  function drawMsgs() {
    const g = W.game; if (!g || THREAD.game !== W.id) return;
    const t = mountKit(); if (!t) return;
    if (BAR) BAR.working = !!(THREAD.waiting && THREAD.conv);     // Send is Stop while Hoola works; her typed words stay
    const rows = shownRows();
    if (!rows.length && !THREAD.waiting && !THREAD.pend) {      // nothing said yet: her brief, Hoola's first line, a few asks
      const brief = S(g.brief).trim(), say = S(g.say) || 'Ask for anything in this game.';
      t.sync({key: ['intro', g.id, S(g.status), N(g.version), brief, say].join('|'), working: false,
        messages: [{id: 'brief', role: 'her', text: brief}, {id: 'say', role: 'hoola', text: say}, {id: 'note', role: 'raw', html: introHtml(g)}]});
      return;
    }
    const msgs = []; let uid = '', k = 0, prev = 0;
    for (const r of rows) {
      const at = tsec(r.at);
      if (r.role === 'user') { uid = S(r.id); k = 0; msgs.push({id: 'u' + uid, role: 'her', text: clean(r.text)}); }
      else {
        const st = prev && at ? stepsBetween(prev, at) : [];
        const m = {id: `h${uid}:${k++}`, role: 'hoola', text: S(r.text)};
        if (st.length) { m.worked = dur(Math.max(1, (st[st.length - 1].end || at) - st[0].at)); m.steps = st.map(x => ({label: x.label, time: x.end ? dur(x.end - x.at) : ''})); }
        msgs.push(m);
      }
      prev = at || prev;
    }
    const last = rows[rows.length - 1], live = THREAD.live.trim();
    // the reply being written (a snapshot that grows). It keeps one id from its first word to the saved message, so
    // the kit goes on landing the same block; a block already saved as a message is not shown twice.
    if (THREAD.waiting && live && !THREAD.pend && uid && !(last.role === 'assistant' && S(last.text).trim().startsWith(live))) {
      THREAD.liveId = `h${uid}:${k}`;
      msgs.push({id: THREAD.liveId, role: 'hoola', text: THREAD.live});
    }
    // words she stopped midway stay where they were (until the server's own message takes their place); a turn
    // stopped before any word says so in one quiet line
    for (const h of THREAD.held) {
      if (msgs.some(m => m.id === h.id)) continue;
      const i = msgs.findIndex(m => m.id === h.after); if (i < 0) continue;
      let j = i + 1; while (j < msgs.length && msgs[j].role !== 'her') j++;
      if (!h.note) msgs.splice(j, 0, {id: h.id, role: 'hoola', text: h.said, stopped: true});
      else if (j === i + 1) msgs.splice(j, 0, {id: h.id, role: 'raw', html: '<div class="hck-note">Stopped</div>'});
    }
    const since = THREAD.startedS || nowS();
    const steps = [];
    if (THREAD.waiting) for (const x of stepsBetween(since)) {
      const sig = x.state + '|' + x.label, was = THREAD.told.get(x.k);
      if (was === sig || was === 'folded') continue;            // each step is handed over once per state, never after its row folded
      THREAD.told.set(x.k, sig);
      steps.push({id: x.k, label: x.label, state: x.state === 'run' ? 'running' : x.state, secs: x.end ? Math.max(0, x.end - x.at) : undefined});
    }
    const end = msgs[msgs.length - 1], endSaid = end && end.role === 'hoola' ? S(end.text).trim() : '';
    THREAD.turn = !THREAD.waiting && endSaid ? ((THREAD.turns.filter(x => x.said === endSaid).pop() || {}).turn || THREAD.liveTurn) : '';
    KIT_ACTS.splice(0, KIT_ACTS.length, 'copy', 'aloud', ...(THREAD.turn ? ['up', 'down'] : []), ...(THREAD.conv ? ['again'] : []));
    KIT_OPTS.startedAt = THREAD.waiting ? since * 1000 : 0;
    const st = {key: 'talk|' + g.id + '|' + THREAD.conv, messages: msgs, working: !!THREAD.waiting, steps: []};
    // she wrote again while Hoola was still on the turn before: once her new message is saved, the turn above it closes
    // and the work for the new message shows under it
    const tail = t.el.lastElementChild, lastHer = msgs.map(m => m.role).lastIndexOf('her'), her = msgs[lastHer];
    if (t.busy && !THREAD.pend && her && tail && tail.classList.contains('hck-me') && (tail.dataset.id === her.id || tail._pending === S(her.text).trim())) {
      t.sync({...st, messages: msgs.slice(0, lastHer + 1), steps: []});
      if (t.busy) t.end();
    }
    // steps go in BEFORE the words that came after them: a finished step ticks in its own row, and the rows fold into
    // "Worked for" the moment the words begin (the kit then owns them; they are never handed over again)
    const running = t.busy && THREAD.kitKey === st.key, words = msgs.length - 1 - lastHer;
    if (running) for (const x of steps) t.step(x); else st.steps = steps;
    THREAD.kitKey = st.key;
    t.sync(st);
    if (running && words > THREAD.words) for (const k of THREAD.told.keys()) THREAD.told.set(k, 'folded');
    THREAD.words = THREAD.waiting ? words : 0;
  }
  async function readThread() {
    const c = THREAD.conv; if (!c) return;
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/messages?limit=60`);
      if (c !== THREAD.conv) return;
      // the server sends the newest 60: rows read earlier stay, so the thread never jumps when the window moves
      const next = L(r.messages), at = next.length ? THREAD.rows.findIndex(m => m.id === next[0].id) : -1;
      THREAD.rows = at > 0 ? THREAD.rows.slice(0, at).concat(next) : next; THREAD.ok = true;
    } catch (e) {
      if (e.status === 404 && c === THREAD.conv) { store.del(convKey(THREAD.game)); Object.assign(THREAD, {conv: '', ok: false, waiting: false, pend: ''}); drawMsgs(); }
      return;
    }
    if (THREAD.waiting || !THREAD.stepsRead) { await readSteps(c); THREAD.stepsRead = true; if (c !== THREAD.conv) return; }
    if (THREAD.pend && talkRows().some(m => m.role === 'user' && Number(m.id) > THREAD.since)) THREAD.pend = '';
    if (!THREAD.waiting) {
      // opened while Hoola is still on her last message: the thread picks the turn up where it is
      const talk = talkRows(), last = talk[talk.length - 1];
      if (last && last.role === 'user' && nowS() - tsec(last.at) < 900 && tsec(last.at) > THREAD.haltAt && THREAD.busy !== false) {
        THREAD.waiting = true; THREAD.started = Date.now(); THREAD.startedS = tsec(last.at);
        THREAD.since = (Number(last.id) || 1) - 1;
      }
    }
    if (THREAD.waiting) {
      let snap = null;
      try { const res = await api('GET', `/api/conversations/${enc(c)}/live`, undefined, {raw: true}); if (res.status === 200) snap = await res.json(); } catch {}
      if (c !== THREAD.conv) return;
      THREAD.live = S(snap?.text); if (snap?.turn) THREAD.liveTurn = S(snap.turn);
      const talk = talkRows();
      let lu = -1; talk.forEach((m, i) => { if (m.role === 'user') lu = i; });
      const mine = lu >= 0 && Number(talk[lu].id) > THREAD.since;
      const answered = mine && talk.slice(lu + 1).some(m => m.role === 'assistant');
      // over: her message has its answer, or the server says it is no longer working on this chat
      const idle = mine && THREAD.busy === false && Date.now() - THREAD.started > 20e3;
      if ((answered || idle) && !snap) { THREAD.waiting = false; THREAD.live = ''; THREAD.startedS = 0; await readSteps(c); if (c !== THREAD.conv) return; reloadGame(); }
      else if (Date.now() - THREAD.started > 15 * 60e3) THREAD.waiting = false;
    }
    if (c !== THREAD.conv || parse().view !== 'game') return;
    drawMsgs();
    if (THREAD.waiting) { clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 1500); }
  }
  function waitFor(said) {
    THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
    Object.assign(THREAD, {waiting: true, started: Date.now(), startedS: nowS(), live: '', liveTurn: '', liveId: '', pend: said, told: new Map(), words: 0, busy: undefined});
  }
  function unsend(said) {                                       // it was not sent: her words go back to the box
    THREAD.waiting = false; THREAD.pend = '';
    if (KIT) KIT.el.querySelectorAll('.hck-me').forEach(n => { if (n._pending != null) n.remove(); });
    if (BAR && !BAR.value) BAR.value = said;
    drawMsgs();
  }
  async function ask(text) {
    text = S(text).trim(); const g = W.game; if (!text || !g) return;
    let shown = false;
    try {
      const gid = g.id;
      const c = await ensureConv();
      if (W.id !== gid || c !== THREAD.conv) return;
      const t = mountKit();
      if (t && !shownRows().length && !THREAD.waiting && !THREAD.pend) t.sync({key: 'talk|' + g.id + '|' + c, messages: [], working: false});   // the first lines make way for the talk
      if (t) t.her(text, {pending: true});                      // her words show the moment she sends
      shown = true; waitFor(text); drawMsgs();
      const sid = sidOf(g.id);
      const br = v => S(v).replace(/\s+/g, ' ').replace(/\[/g, '(').replace(/\]/g, ')');   // a ] in a title would end the hint early and clean() could not strip it
      const hints = [`Game Dev: this chat is only about game ${br(g.number)} "${br(gname(g))}" (game id ${S(g.id)}, studio project ${sid || 'none'}). Work on THIS game with game_desk / game_studio and the other game_* tools; never start a new game unless I ask.`];
      await api('POST', `/api/conversations/${enc(c)}/messages`, {text, client_id: 'gdv-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8), hints});
      clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 900);
    } catch (e) { if (shown) unsend(text); else if (BAR && !BAR.value) BAR.value = text; toast(e.message, true); }
  }
  /* Stop: the server stops after the step it is on (POST /stop, the main chat's own route) */
  async function stopTurn() {
    const c = THREAD.conv; if (!c || !THREAD.waiting) return;
    try { await api('POST', `/api/conversations/${enc(c)}/stop`); } catch (e) { return toast(e.message, true); }
    const her = shownRows().filter(r => r.role === 'user').pop();
    if (THREAD.live.trim() && THREAD.liveId) THREAD.held.push({id: THREAD.liveId, after: 'u' + THREAD.liveId.slice(1).split(':')[0], said: THREAD.live});
    else if (her && !THREAD.pend) THREAD.held.push({id: 'stop' + her.id, after: 'u' + her.id, note: true});
    Object.assign(THREAD, {waiting: false, live: '', pend: '', startedS: 0, haltAt: nowS()});
    if (KIT) KIT.stop();
    drawMsgs();
    clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 2500);         // what it had saved by then
  }
  /* the buttons under the newest reply: Good answer / Not right / Ask again are the main chat's own routes */
  async function kitAct(kind, said, value) {
    const c = THREAD.conv; if (!c) return;
    if (kind === 'up' || kind === 'down') {
      try {
        await api('POST', `/api/conversations/${enc(c)}/feedback`, {turn: THREAD.turn, value});
        if (value === 'down') toast('Thanks. Tap Ask again for a better answer, or tell Hoola what was wrong.');
      } catch { if (KIT) KIT.el.querySelectorAll('.hck-acts [data-act="up"],.hck-acts [data-act="down"]').forEach(b => b.setAttribute('aria-pressed', 'false')); toast('Could not save that. Please try again.', true); }
      return;
    }
    if (kind !== 'again') return;
    if (THREAD.waiting) return toast('Hoola is still working. Stop it first.', true);
    const her = shownRows().filter(r => r.role === 'user').pop(); if (!her) return;
    try {
      await api('POST', `/api/conversations/${enc(c)}/retry`);
      const hi = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      const x = THREAD.redo.find(y => y.lo === Number(her.id));
      if (x) { x.n++; x.hi = hi; } else THREAD.redo.push({lo: Number(her.id), hi, said: clean(her.text), n: 1});
      waitFor(''); drawMsgs();                                  // the old answer leaves; her message stays where it is
      clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 900);
    } catch (e) { toast(e.status === 409 ? 'Hoola is still working. Stop it first.' : e.status === 404 ? 'There is no message to ask again.' : e.message, true); }
  }

  /* ---------- the viewport's own controls: the real game frame, never rebuilt by a poll ---------- */
  function viewportAct(el) {
    const st = el.closest('.gdv-stage'); if (!st) return;
    const fr = st.querySelector('iframe'), over = st.querySelector('.gdv-vpstop'), live = st.querySelector('[data-gdv-vplive]');
    const k = el.dataset.gdvVp;
    if (k === 'play' || k === 'stop') {
      const run = k === 'play';
      if (fr) fr.src = run ? S(st.dataset.src) : 'about:blank';
      if (over) over.hidden = run;
      st.classList.toggle('gdv-stopped', !run);
      if (live) live.innerHTML = run ? `<span class="gdv-dot gdv-ok gdv-glow" aria-hidden="true"></span>running · version ${N(W.game && W.game.version)}` : '<span class="gdv-dot" aria-hidden="true"></span>stopped';
      if (run) fr?.focus();
      return;
    }
    if (k === 'dev') {
      st.dataset.dev = S(el.dataset.dev) || 'phone';
      st.querySelectorAll('[data-gdv-vp="dev"]').forEach(b => b.setAttribute('aria-pressed', String(b === el)));
      return;
    }
    if (k === 'full') {
      const c = st.querySelector('.gdv-vpcanvas');
      try { const p = c && c.requestFullscreen && c.requestFullscreen(); if (p && p.catch) p.catch(() => toast('Full screen is not allowed here. Use “Open in a new tab”.', true)); }
      catch { toast('Full screen is not allowed here. Use “Open in a new tab”.', true); }
    }
  }

  /* ---------- events (one set, delegated) ---------- */
  APP.addEventListener('submit', e => {
    const f = e.target.closest('form[data-gdv-form]'); if (!f) return;
    e.preventDefault();
    if (f.dataset.gdvForm === 'ask') return startGame($('#gdvAsk')?.value, $('#gdvOr')?.value || 'portrait');
    if (f.dataset.gdvForm === 'thread') { const t = $('#gdvTh'); const v = S(t?.value); if (!v.trim()) return; if (BAR) BAR.clear(); else t.value = ''; ask(v); }
  });
  APP.addEventListener('keydown', e => {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    if (e.target.id === 'gdvAsk') { e.preventDefault(); e.target.closest('form')?.requestSubmit(); }   // the thread's box is the kit's bar: Enter is its own
  });
  APP.addEventListener('click', async e => {
    if (e.target.closest('.hck')) {                            // the thread is the chat kit's: its buttons are its own (Copy on a code block too)
      const fk = e.target.closest('[data-gdv-fill-th]'); if (fk) fillBar(fk.dataset.gdvFillTh);
      return;
    }
    const fill = e.target.closest('[data-gdv-fill]');
    if (fill) { const t = $('#gdvAsk'); if (t) { t.value = S(fill.dataset.gdvFill); t.focus(); t.setSelectionRange(t.value.length, t.value.length); } return; }
    const fth = e.target.closest('[data-gdv-fill-th]');
    if (fth) { fillBar(fth.dataset.gdvFillTh); return; }
    const flt = e.target.closest('[data-gdv-filter]');
    if (flt) { FILTER = flt.dataset.gdvFilter; APP.querySelectorAll('[data-gdv-filter]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.gdvFilter === FILTER))); const ab = $('#gdvAllBox'); if (ab) ab.innerHTML = allHtml(); return; }
    const vp = e.target.closest('[data-gdv-vp]');
    if (vp) { viewportAct(vp); return; }
    const a = e.target.closest('[data-gdv-act]'); if (!a) return;
    const k = a.dataset.gdvAct;
    if (k === 'hire') { e.preventDefault(); a.disabled = true; return hire(a.dataset.key || 'game_dev'); }
    if (k === 'focus-ask' || k === 'new-game') {
      if (parse().view === 'home' && $('#gdvAsk')) { e.preventDefault(); $('#gdvAsk').focus(); $('#gdvAsk').scrollIntoView({block: 'center'}); }
      return;
    }
    gameAct(k, a);
  });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
      const t = e.target;
      if (t && t.closest && (t.closest('input,textarea,select,[contenteditable="true"]') || t.closest('.gdv-embed'))) return;
      e.preventDefault();
      if (parse().view === 'home' && $('#gdvAsk')) $('#gdvAsk').focus();
      else { location.hash = '#/'; setTimeout(() => $('#gdvAsk')?.focus(), 400); }
    }
  });
  window.addEventListener('hashchange', route);
  route();
})();
