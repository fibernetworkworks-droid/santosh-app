/* v0.160 Hoola Console · Build studio: what the phone app shows while Hoola builds a website, an app design or the
   real Android app, now on the web too. Live from the same events (site_board, app_board, app_android):
   chat card (stages, now line, progress, the right buttons) + a studio beside the chat:
   website = live preview (computer + phone, refreshed after every finished part), board of pages and parts, steps,
   checks (scores, screenshots, scroll video); app = every screen with its real picture, prototype, design DNA, checks,
   Android build (Kotlin screens, compile rounds, APK + QR). Pictures need her login: fetched with the Bearer token into
   blob: URLs. Previews are public-by-token pages and run in a sandboxed frame (no same-origin, so they can't see the
   console's login). Money / launch / domain still go through her Haan cards. */
'use strict';
window.HoolaBuild = function (C) {
  const {api, esc, toast} = C;
  const KINDS = new Set(['site_board', 'app_board', 'app_android']);
  const P = new Map();                 // 'site:<id>' | 'app:<id>' -> project
  let CUR = null;                      // key shown in the studio
  const studio = document.getElementById('studio'), appEl = document.getElementById('app'), sbtn = document.getElementById('studioBtn');

  /* ---------------- small helpers ---------------- */
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const N = v => Number.isFinite(+v) ? +v : 0;
  const L = v => Array.isArray(v) ? v : [];
  const M = v => (v && typeof v === 'object' && !Array.isArray(v)) ? v : {};
  const hex = h => /^#[0-9a-f]{3,8}$/i.test(S(h)) ? S(h) : '';
  const ago = t => { const s = Math.max(0, Math.round((Date.now() - t) / 1000)); return s < 5 ? 'just now' : s < 60 ? `${s}s ago` : `${Math.round(s / 60)} min ago`; };
  const clock = t => new Date(t).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit', hour12: false});
  const spin = (sz = 14) => `<span class="spin" style="width:${sz}px;height:${sz}px"></span>`;
  const btn = (a, label, cls = 'soft', extra = '') => `<button class="btn ${cls}" type="button" data-ba="${a}"${extra}>${label}</button>`;
  function previewPath(u) {          // only our own preview pages, always as a same-server path
    let p = S(u); if (!p) return '';
    if (!p.startsWith('/')) { try { const x = new URL(p); p = x.pathname; } catch { return ''; } }
    return /^\/api\/(site|app)-preview\/[\w-]+\/$/.test(p) ? p : '';
  }
  function shotPath(type, id, name) {
    name = S(name); if (!name || name.includes('..') || !/^[\w./-]+$/.test(name)) return '';
    return `/api/${type === 'site' ? 'sites' : 'apps'}/${encodeURIComponent(id)}/shots/${name.split('/').map(encodeURIComponent).join('/')}`;
  }
  function publicLink(u) {           // apk / zip links: our server only
    const s = S(u); if (!s) return '';
    try { const x = new URL(s, location.origin); return /^\/api\/app-(apk|zip)\//.test(x.pathname) ? x.pathname : ''; } catch { return ''; }
  }
  const BLOB = new Map();            // path -> Promise<objectURL>
  function blob(path) {
    if (!BLOB.has(path)) {
      const pr = api('GET', path, undefined, {raw: true}).then(r => r.blob()).then(b => URL.createObjectURL(b));
      pr.catch(() => BLOB.delete(path)); BLOB.set(path, pr);
      if (BLOB.size > 240) { const [k, old] = BLOB.entries().next().value; BLOB.delete(k); old.then(u => URL.revokeObjectURL(u)).catch(() => {}); }
    }
    return BLOB.get(path);
  }
  const pic = (path, alt, cls = '') => path ? `<img class="${cls}" data-src="${esc(path)}" alt="${esc(alt)}" loading="lazy">` : '';
  function hydrate(root) {
    root.querySelectorAll('[data-src]').forEach(el => {
      const p = el.dataset.src; el.removeAttribute('data-src');
      blob(p).then(u => { el.src = u; el.classList.add('in'); }).catch(() => { el.classList.add('miss'); el.alt = 'Picture not found'; });
    });
  }

  /* ---------------- words ---------------- */
  const ST = {
    site: {draft: 'Starting', planned: 'Plan: needs your Haan', looks: 'Pick a look', building: 'Building', checking: 'Checking', ready: 'Ready', failed: 'Problem', stopped: 'Stopped'},
    app: {draft: 'Starting', planned: 'Plan: needs your Haan', looks: 'Pick a look', designing: 'Designing screens', checking: 'Checking', ready: 'Design ready', approved: 'Design approved', failed: 'Problem', stopped: 'Stopped'},
    an: {writing: 'Writing Kotlin', building: 'Compiling', fixing: 'Fixing errors', ready: 'APK ready', zip: 'Project ZIP', failed: 'Problem'}};
  const TILE = {todo: ['to do', 'todo'], writing: ['writing', 'run'], written: ['written', 'ok'], compiling: ['compiling', 'run'], fixing: ['fixing', 'fix'], done: ['✓', 'ok'], code: ['simple version', 'fix']};
  const making = o => S(o.v?.status) === 'looks' && !L(o.v?.looks).length;      // the 3 looks are still being made
  const working = o => making(o) || (o.type === 'site' ? ['building', 'checking'].includes(S(o.v?.status)) : ['designing', 'checking'].includes(S(o.v?.status)));
  const anWorking = o => ['writing', 'building', 'fixing'].includes(S(o.an?.status));
  const busy = o => working(o) || anWorking(o);
  function stTag(o) {
    if (anWorking(o)) return [ST.an[o.an.status], 'run'];
    if (o.an && ['ready', 'zip', 'failed'].includes(S(o.an.status)) && S(o.v?.status) === 'approved') return [ST.an[o.an.status], o.an.status === 'failed' ? 'bad' : 'ok'];
    const s = S(o.v?.status); const t = ST[o.type][s] || s || '…';
    return [t, ['ready', 'approved'].includes(s) ? 'ok' : s === 'failed' ? 'bad' : ['planned', 'looks'].includes(s) ? 'ask' : s === 'stopped' ? 'v' : 'run'];
  }
  const title = o => { const v = o.v || o.an || {}; return `${S(v.number)}${v.number ? ' · ' : ''}${S(v.name) || S(v.field_label) || (o.type === 'site' ? 'Website' : 'App')}`; };

  /* ---------------- projects + their step log ---------------- */
  function upsert(kind, p) {
    const type = kind === 'site_board' ? 'site' : 'app', k = type + ':' + S(p.id);
    let o = P.get(k);
    if (!o) { o = {k, type, id: S(p.id), v: null, an: null, log: [], phase: '', done: -1, ver: -1, last: 0, shown: 0}; P.set(k, o); }
    const prev = kind === 'app_android' ? o.an : o.v;
    if (kind === 'app_android') o.an = p; else o.v = p;
    o.last = Date.now();
    track(o, kind, p, prev);
    return o;
  }
  function logLine(o, text, state) {
    text = S(text).trim(); if (!text) return;
    const done = /\s*✓$/.test(text), base = text.replace(/\s*✓$/, '').trim();
    if (done) {
      const e = [...o.log].reverse().find(x => x.text === base && x.state === 'run');
      if (e) { e.state = 'ok'; e.secs = Math.round((Date.now() - e.t) / 1000); return; }
      if (o.log.some(x => x.text === base)) return;
      o.log.push({t: Date.now(), text: base, state: 'ok'}); return;
    }
    const last = o.log[o.log.length - 1];
    if (last && last.text === base) { if (state) last.state = state; return; }
    o.log.forEach(x => { if (x.state === 'run') x.state = 'ok'; });
    o.log.push({t: Date.now(), text: base, state: state || 'run'});
    if (o.log.length > 80) o.log.splice(0, o.log.length - 80);
  }
  function track(o, kind, p, prev) {
    if (kind === 'app_android') {
      const s = S(p.status);
      if (p.now) logLine(o, 'Android: ' + p.now, ['ready', 'zip'].includes(s) ? 'ok' : s === 'failed' ? 'bad' : 'run');
      if (s === 'failed' && p.error) logLine(o, 'Android: ' + p.error, 'bad');
      if (s === 'ready' && S(prev?.status) !== 'ready') logLine(o, `APK taiyaar (build ${S(p.build)})`, 'ok');
      return;
    }
    const s = S(p.status), b = M(p.board);
    if (b.now) logLine(o, b.now, ['ready', 'approved'].includes(s) ? 'ok' : s === 'failed' ? 'bad' : s === 'stopped' ? 'stop' : undefined);
    if (prev && S(prev.status) !== s) {
      if (s === 'failed') logLine(o, 'Problem: ' + S(p.error), 'bad');
      if (s === 'stopped') logLine(o, 'Stopped', 'stop');
      if (s === 'ready') logLine(o, `${o.type === 'site' ? 'Website' : 'App design'} v${S(p.version)} taiyaar`, 'ok');
    }
  }

  /* ---------------- shared pieces ---------------- */
  function stages(o, small) {
    const v = o.v; if (!v) return '';
    const list = L(v.stages); let cur = list.findIndex(x => x.id === v.stage);
    if (o.type === 'app' && o.an && S(o.an.status)) cur = Math.max(cur, list.findIndex(x => x.id === 'android'));
    const fin = ['ready', 'approved'].includes(S(v.status)) && !anWorking(o);
    return `<div class="bst${small ? ' sm' : ''}">${list.map((x, i) => {
      const done = i < cur || (fin && i <= cur) || (x.id === 'android' && ['ready', 'zip'].includes(S(o.an?.status)));
      const now = i === cur && !done;
      return `<span class="${done ? 'ok' : now ? 'now' : ''}">${done ? '✓ ' : ''}${esc(x.label)}</span>`;
    }).join('')}</div>`;
  }
  function progress(o) {
    const b = M(o.v?.board), unit = o.type === 'site' ? 'hisse' : 'screens';
    return `<div class="bbar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${N(b.pct)}"><i style="width:${Math.min(100, N(b.pct))}%"></i></div>
      <div class="bsub">${N(b.done)} / ${N(b.total)} ${unit} · ${N(b.pct)}%</div>`;
  }
  const chip = (label, state) => { const c = {done: 'ok', building: 'run', fixing: 'fix', failed: 'bad'}[state] || 'todo';
    return `<span class="bchip ${c}">${state === 'done' ? '✓ ' : state === 'building' ? '⋯ ' : state === 'fixing' ? 'fixing: ' : ''}${esc(label)}</span>`; };
  function checksBlock(o, ttl) {
    const c = M(o.v?.checks), bl = L(c.blocking), wa = L(c.warnings);
    if (!bl.length && !wa.length && c.passed !== true) return '';
    const where = x => S(x.screen) ? esc(x.screen) + ': ' : '';
    return `<section class="bbox"><h4>${esc(ttl)}</h4>
      ${bl.slice(0, 8).map(x => `<div class="badc bln">⛔ ${where(x)}${esc(x.text)}</div>`).join('')}
      ${wa.slice(0, 8).map(x => `<div class="warnc bln">⚠ ${where(x)}${esc(x.text)}</div>`).join('')}
      ${!bl.length && c.passed === true ? '<div class="okc bln" style="font-weight:500">✓ All required checks passed</div>' : ''}
      ${N(c.blanks) ? `<div class="faint bln">${N(c.blanks)} spot(s) still need your details (the […] boxes)</div>` : ''}</section>`;
  }
  function scoresBlock(sc) {
    sc = M(sc); if (!Object.keys(sc).length) return '';
    const one = (k, lab) => { const n = sc[k]; const col = n == null ? '' : n >= 90 ? 'okc' : n >= 50 ? 'warnc' : 'badc';
      return `<div><b class="${col}">${n == null ? '–' : esc(Math.round(n))}</b><span>${lab}</span></div>`; };
    return `<div class="bscores">${one('performance', 'Speed')}${one('accessibility', 'Access')}${one('seo', 'SEO')}${one('best_practices', 'Best')}</div>`;
  }

  /* ---------------- chat card ---------------- */
  function card(kind, p, el, live) {
    const o = upsert(kind, p);
    el.classList.add('bcard');
    if (kind === 'app_android') el.innerHTML = androidCard(o);
    else el.innerHTML = o.type === 'site' ? siteCard(o) : appCard(o);
    hydrate(el);
    el.onclick = e => act(e, o);
    if (live && !o.dismissed && !C.narrow() && (busy(o) || ['planned', 'looks'].includes(S(o.v?.status))) && (!CUR || CUR === o.k || !busy(P.get(CUR)))) open(o.k);
    else if (CUR === o.k && isOpen()) draw();
    showBtn();
  }
  function cardHead(o, icon, extra = '') {
    const [t, c] = stTag(o);
    return `<div class="hd"><span class="bic" aria-hidden="true">${icon}</span><b>${esc(title(o))}${extra}</b><span class="tag ${c === 'ok' ? 'ok' : c === 'bad' ? 'bad' : c === 'ask' ? 'warn' : 'v'}">${esc(t)}</span></div>`;
  }
  const IC_WEB = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/></svg>';
  const IC_APP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/></svg>';
  const IC_AND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="5" y="9" width="14" height="10" rx="2"/><path d="M8 9V7a4 4 0 0 1 8 0v2M9 14h.01M15 14h.01"/></svg>';
  function nowLine(text, run) { return text ? `<div class="bnow">${run ? spin() : ''}<span>Now: <b>${esc(text)}</b></span></div>` : ''; }
  function siteCard(o) {
    const v = o.v, s = S(v.status), b = M(v.board), pv = previewPath(v.preview);
    let body = '';
    if (s === 'planned' && v.mapping) body = nowLine('Planning the site map (big site)…', true);   // v0.315
    else if (s === 'planned') body = (v.size ? sizeLine(v) : '') + L(v.plan?.pages).slice(0, 8).map(p => `<div class="bln faint">• ${esc(p.title)}: ${esc(L(p.sections).join(', '))}</div>`).join('')
      + `<div class="acts">${btn('studio', 'Review / answer')}${btn('plan', 'Haan, make 3 looks', 'go')}</div>`;
    else if (s === 'looks') body = lookThumbs(o) + `<div class="acts">${btn('studio', 'Pick in studio', 'go')}</div>`;
    else if (working(o)) body = nowLine(b.now, true) + progress(o)
      + `<div class="acts">${btn('stop', 'Stop')}${pv ? `<a class="btn soft" href="${esc(pv)}" target="_blank" rel="noopener">Preview in new tab</a>` : ''}${btn('studio', 'Open studio', 'go')}</div>`;
    else if (s === 'ready') body = scoresBlock(v.scores)
      + `<div class="acts">${pv ? `<a class="btn soft" href="${esc(pv)}" target="_blank" rel="noopener">Open preview</a>` : ''}${btn('studio', 'Review / change', 'go')}</div>`;
    else if (s === 'failed' || s === 'stopped') body = (v.error ? `<div class="badc bln">${esc(v.error)}</div>` : '') + `<div class="acts">${btn('studio', 'Studio')}${btn('resume', 'Continue', 'go')}</div>`;
    return cardHead(o, IC_WEB) + stages(o, true) + (v.say ? `<p class="bsay">${esc(v.say)}</p>` : '') + body;
  }
  function appCard(o) {
    const v = o.v, s = S(v.status), b = M(v.board), pv = previewPath(v.preview);
    let body = '';
    if (s === 'planned') body = `<div class="bln faint">${L(v.plan?.screens).length + L(v.plan?.code_screens).length} screens · bottom tabs: ${esc(L(v.plan?.tabs).join(' · '))}</div>`
      + `<div class="acts">${btn('studio', 'Review / answer')}${btn('plan', 'Haan, make 3 looks', 'go')}</div>`;
    else if (s === 'looks') body = lookThumbs(o) + `<div class="acts">${btn('studio', 'Pick in studio', 'go')}</div>`;
    else if (working(o)) body = nowLine(b.now, true) + progress(o) + miniScreens(o)
      + `<div class="acts">${btn('stop', 'Stop')}${pv ? `<a class="btn soft" href="${esc(pv)}" target="_blank" rel="noopener">Prototype</a>` : ''}${btn('studio', 'Open studio', 'go')}</div>`;
    else if (s === 'ready' || s === 'approved') body = miniScreens(o)
      + `<div class="acts">${pv ? `<a class="btn soft" href="${esc(pv)}" target="_blank" rel="noopener">Try the prototype</a>` : ''}${btn('studio', 'Studio')}${s === 'ready' ? btn('approve', 'Approve design', 'go') : (!o.an || !S(o.an.status) ? btn('android', 'Build Android app', 'go') : '')}</div>`;
    else if (s === 'failed' || s === 'stopped') body = (v.error ? `<div class="badc bln">${esc(v.error)}</div>` : '') + `<div class="acts">${btn('studio', 'Studio')}${btn('resume', 'Continue', 'go')}</div>`;
    return cardHead(o, IC_APP) + stages(o, true) + (v.say ? `<p class="bsay">${esc(v.say)}</p>` : '') + body;
  }
  function androidCard(o) {
    const a = o.an, s = S(a.status), dl = publicLink(a.apk_url);
    const run = ['writing', 'building', 'fixing'].includes(s);
    return `<div class="hd"><span class="bic" aria-hidden="true">${IC_AND}</span><b>${esc(S(a.number))} · ${esc(S(a.name))} · Android</b><span class="tag ${s === 'ready' ? 'ok' : s === 'failed' ? 'bad' : 'v'}">${esc(ST.an[s] || s || 'Not started')}</span></div>`
      + (a.say ? `<p class="bsay">${esc(a.say)}</p>` : '') + (run && a.now ? nowLine(a.now, true) : '')
      + (s === 'failed' && a.error ? `<div class="badc bln">${esc(a.error)}</div>` : '')
      + (a.apk && a.apk.file ? `<div class="bln faint">${esc(a.apk.file)} · ${mb(a.apk.size)} · v${esc(S(a.apk.version_name))}</div>` : '')
      + `<div class="acts">${dl ? `<a class="btn go" href="${esc(dl)}" download>APK download</a>` : ''}${btn('studio-android', 'Open studio', dl ? 'soft' : 'go')}</div>`;
  }
  const mb = n => N(n) ? (N(n) / 1048576).toFixed(1) + ' MB' : '';
  function lookThumbs(o) {
    const looks = L(o.v.looks); if (!looks.length) return `<div class="bln faint">${spin()} Making the looks…</div>`;
    return `<div class="blooks">${looks.slice(0, 3).map((lk, i) => `<figure>${pic(shotPath(o.type, o.id, o.type === 'site' ? M(lk.shots)['390'] : M(lk.shots).android), `Look ${i + 1}`)}<figcaption>${i + 1}. ${esc(lk.label)}</figcaption></figure>`).join('')}</div>`;
  }
  function miniScreens(o) {
    const tiles = L(M(o.v.board).pages).flatMap(p => L(p.sections)).slice(0, 9);
    if (!tiles.length) return '';
    return `<div class="bmini">${tiles.map(t => `<span class="${t.state === 'done' ? 'ok' : t.state === 'building' ? 'run' : ''}" title="${esc(t.label)}">${t.thumb ? pic(shotPath('app', o.id, t.thumb), t.label) : t.state === 'building' ? spin(12) : ''}</span>`).join('')}</div>`;
  }

  /* ---------------- studio ---------------- */
  const isOpen = () => appEl.classList.contains('st');
  function showBtn() { if (!sbtn) return; sbtn.hidden = !P.size; const any = [...P.values()].some(busy); sbtn.classList.toggle('on', any); sbtn.querySelector('span').textContent = any ? 'Studio · building' : 'Studio'; }
  function open(k) {
    if (!P.has(k)) return;
    const changed = CUR !== k; CUR = k; P.get(k).dismissed = false;
    appEl.classList.add('st'); appEl.classList.remove('open');      // one right-hand panel at a time
    draw(changed);
  }
  function close() { if (isOpen() && P.get(CUR)) P.get(CUR).dismissed = true; appEl.classList.remove('st'); }   // she closed it: no auto re-open
  function defaultTab(o) {
    const s = S(o.v?.status);
    if (s === 'planned') return 'plan';
    if (s === 'looks') return 'looks';
    if (o.type === 'site') return s === 'ready' ? 'jaanch' : 'preview';
    if (anWorking(o) || (o.an && S(o.an.status) && (s === 'approved' || !o.v))) return 'android';
    return 'screens';
  }
  function tabsOf(o) {
    const s = S(o.v?.status), pre = [];
    if (s === 'planned') pre.push(['plan', 'Plan']);
    if (s === 'looks') pre.push(['looks', 'Looks']);
    return o.type === 'site'
      ? [...pre, ['preview', 'Preview'], ['board', 'Board'], ['kadam', 'Steps'], ['jaanch', 'Checks'], ...(o.v?.version ? [['data', 'App & data']] : [])]
      : [...pre, ['screens', 'Screens'], ['prototype', 'Prototype'], ['dhaancha', 'Structure'], ['android', 'Android'],
         ...(S(o.an?.status) ? [['data', 'App data']] : []), ['kadam', 'Steps']];   // v0.314 the built app's own backend
  }
  function draw(rebuild) {
    const o = P.get(CUR); if (!o || !studio) return;
    const phase = S(o.v?.status) + '/' + S(o.an?.status);
    if (rebuild || o.phase !== phase || !o.tab) { if (rebuild || o.phase !== phase) o.tab = defaultTab(o); o.phase = phase; }
    if (rebuild || studio.dataset.k !== o.k) {
      studio.dataset.k = o.k;
      studio.innerHTML = `<div class="sthd"></div><div class="stnow"></div><div class="stst"></div><div class="sttabs" role="tablist" aria-label="Studio"></div>
        <div class="stpanes"><div class="stpane" data-pane="frames"></div><div class="stpane" data-pane="other"></div></div>
        <form class="stchg" autocomplete="off"><label class="sr" for="stIn">Request a change</label><input id="stIn" placeholder="Describe a change, e.g. 'make the colours a little warmer'"><button class="btn go" type="submit">Edit</button><span class="stq"></span></form>`;
      studio.querySelector('.stchg').addEventListener('submit', e => { e.preventDefault(); change(o); });
      studio.onclick = e => act(e, P.get(CUR));
      studio.onsubmit = async e => {
        if (e.target.dataset.form !== 'answers') return;
        e.preventDefault(); const cur = P.get(CUR); if (!cur) return;
        const answers = {}; new FormData(e.target).forEach((val, key) => { if (String(val).trim()) answers[key] = String(val).trim(); });
        if (!Object.keys(answers).length) return toast('Write at least one answer.', true);
        try { await api('POST', base(cur) + '/answers', {answers}); toast('Answers saved.'); } catch (er) { toast(er.message, true); }
      };
      o.framesFor = '';
    }
    const [t, c] = stTag(o);
    const others = [...P.values()].sort((a, b) => b.last - a.last);
    studio.querySelector('.sthd').innerHTML = `<button class="ib" type="button" data-ba="close" aria-label="Close studio">✕</button>
      <div class="stti"><h3>${o.type === 'site' ? 'Website studio' : 'App studio'}</h3><span>${esc(title(o))}</span></div>
      <span class="tag ${c === 'ok' ? 'ok' : c === 'bad' ? 'bad' : c === 'ask' ? 'warn' : 'v'}">${busy(o) ? '● LIVE · ' : ''}${esc(t)}</span>
      ${others.length > 1 ? `<label class="sr" for="stPick">Project</label><select id="stPick" class="stpick">${others.map(x => `<option value="${esc(x.k)}"${x.k === o.k ? ' selected' : ''}>${esc(title(x))}${busy(x) ? ' · building' : ''}</option>`).join('')}</select>` : ''}
      ${working(o) ? btn('stop', '■ Stop') : ['failed', 'stopped'].includes(S(o.v?.status)) ? btn('resume', 'Continue', 'go') : ''}`;
    const pick = studio.querySelector('#stPick'); if (pick) pick.onchange = () => open(pick.value);
    // now line
    const b = M(o.v?.board), an = o.an || {};
    const anShown = !!S(an.status) && (anWorking(o) || S(o.v?.status) === 'approved' || !o.v);     // the Android build leads now
    const nowText = anWorking(o) ? S(an.now) || ST.an[an.status] : anShown ? (an.status === 'ready' ? `APK taiyaar (build ${S(an.build)})` : ST.an[an.status] || S(an.status)) : S(b.now);
    const run = busy(o);
    studio.querySelector('.stnow').innerHTML = (nowText || o.v) ? `<div class="stn ${run ? 'run' : S(o.v?.status) === 'failed' || an.status === 'failed' ? 'bad' : 'idle'}">
        ${run ? spin(22) : '<span class="stok" aria-hidden="true">✓</span>'}
        <div><b>${run ? 'Now: ' : ''}${esc(nowText || S(o.v?.say) || '')}</b><span>${esc(run ? (anWorking(o) ? `Build machine${an.rounds ? ' · round ' + an.rounds : ''}` : `${S(o.v?.model) || 'Opus 5.5'} is writing · each part shows here as it is built`) : anShown ? S(an.say) : S(o.v?.say && nowText ? o.v.say : ''))}</span></div>
        ${o.v && !anShown && N(b.total) && !['planned', 'looks'].includes(S(o.v.status)) ? `<div class="stpct"><b>${N(b.pct)}%</b><span>${N(b.done)} / ${N(b.total)} ${o.type === 'site' ? 'hisse' : 'screens'}</span></div>` : ''}</div>` : '';
    studio.querySelector('.stst').innerHTML = stages(o);
    const tabs = tabsOf(o); if (!tabs.some(x => x[0] === o.tab)) o.tab = tabs[0][0];
    studio.querySelector('.sttabs').innerHTML = tabs.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === o.tab}">${n}</button>`).join('');
    const q = N(o.v?.queued); studio.querySelector('.stq').textContent = q ? `${q} change(s) queued: applied after the current part` : '';
    studio.querySelector('.stchg').hidden = !o.v || ['planned', 'looks', 'draft'].includes(S(o.v.status));
    // panes: frames (preview / prototype iframes, never rebuilt while they show the same project) + everything else
    const fr = studio.querySelector('[data-pane=frames]'), ot = studio.querySelector('[data-pane=other]');
    const framed = (o.type === 'site' && o.tab === 'preview') || (o.type === 'app' && o.tab === 'prototype');
    fr.hidden = !framed; ot.hidden = framed;
    if (framed) frames(o, fr); else { ot.innerHTML = pane(o); hydrate(ot); qr(ot); if (o.tab === 'data') loadData(o, ot); if (o.tab === 'android' && o.type === 'app') { loadStore(o, ot); loadIos(o, ot); loadAppStore(o, ot); } }
    showBtn();
  }

  /* live preview frames */
  function frames(o, box) {
    const path = previewPath(o.v?.preview), want = o.k + '|' + o.tab + '|' + path + '|' + (o.edit ? 'edit' : '');
    if (!path) { box.innerHTML = `<div class="stempty">${spin()} The preview appears here as soon as it starts.</div>`; o.framesFor = ''; return; }
    if (o.pvPath !== path) { o.pvPath = path; o.pvOk = false; }
    if (!o.pvOk) {           // the preview link exists before its first page: open the frame only once it is really there
      box.innerHTML = `<div class="stempty">${spin()} The live preview opens here once the first part is built.</div>`; o.framesFor = '';
      if (!o.pvCheck) {
        o.pvCheck = true;
        fetch(path, {cache: 'no-store', credentials: 'omit'}).then(r => { o.pvCheck = false; if (r.ok) { o.pvOk = true; if (CUR === o.k && isOpen()) draw(); } })
          .catch(() => { o.pvCheck = false; });
      }
      return;
    }
    if (o.framesFor !== want) {
      o.framesFor = want; o.reloadN = 0;
      const src = o.edit ? path + '__edit/' : path;
      const canEdit = o.type === 'site' && ['ready', 'failed', 'stopped'].includes(S(o.v?.status));
      const edBar = o.edit ? `<div class="sted" role="toolbar" aria-label="Edit mode"><b>✏️ Edit mode</b><span>Click any words to type · click a picture to change it · free, no AI</span>
             ${btn('undo', '↶ Undo')}${btn('theme', 'Colours')}${btn('edit-done', 'Done', 'go')}</div>` : '';
      const fsb = 'allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox';
      box.innerHTML = o.type === 'site'
        ? `${edBar}<div class="pvrow"><figure class="pvpc"><div class="pvbar"><i></i><i></i><i></i><span class="pvurl">${esc(location.host + path)}</span><span class="pvage okc"></span></div>
             <div class="pvfit" data-w="1280" data-h="800"><iframe title="Website preview, computer" sandbox="${fsb}" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div>
             <figcaption>Desktop · refreshes by itself as each part is built</figcaption></figure>
           <figure class="pvph"><div class="pvfit phone" data-w="390" data-h="844"><iframe title="Website preview, phone" sandbox="${fsb}" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div><figcaption>Phone par (390 px)</figcaption></figure></div>
           <div class="acts">${canEdit && !o.edit ? btn('edit', '✏️ Edit', 'go') : ''}<a class="btn soft" href="${esc(path)}" target="_blank" rel="noopener">Open in new tab</a>${btn('reload', 'Refresh')}</div>`
        : `<div class="pvrow center"><figure class="pvph big"><div class="pvfit phone" data-w="390" data-h="844"><iframe title="App prototype" sandbox="${fsb}" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div>
             <figcaption>Tap to try it: the real flow, the real screens</figcaption></figure></div>
           <div class="acts" style="justify-content:center"><a class="btn soft" href="${esc(path)}" target="_blank" rel="noopener">Open in new tab</a>${btn('reload', 'Refresh')}</div>`;
      fit(box); o.loadedAt = Date.now();
    }
    const age = box.querySelector('.pvage'); if (age) age.textContent = 'taaza · ' + ago(o.loadedAt || Date.now());
  }
  const RO = window.ResizeObserver ? new ResizeObserver(es => es.forEach(e => scaleOne(e.target))) : null;
  function scaleOne(w) {
    const fw = +w.dataset.w, fh = +w.dataset.h, fs = w.querySelectorAll('iframe'); if (!fs.length) return;
    const k = Math.min(1, (w.clientWidth || fw) / fw);
    fs.forEach(f => { f.style.width = fw + 'px'; f.style.height = fh + 'px'; f.style.transform = `scale(${k})`; });
    w.style.height = Math.round(fh * k) + 'px';
  }
  function fit(box) { box.querySelectorAll('.pvfit').forEach(w => { scaleOne(w); RO && RO.observe(w); }); }
  function reloadFrames(o, force) {
    if (!studio || studio.dataset.k !== o.k) return;
    const now = Date.now(); if (!force && now - (o.reloadAt || 0) < 3000) { clearTimeout(o.reloadT); o.reloadT = setTimeout(() => reloadFrames(o, true), 3000 - (now - o.reloadAt)); return; }
    o.reloadAt = now; o.reloadN = (o.reloadN || 0) + 1; o.loadedAt = now;
    const path = previewPath(o.v?.preview); if (!path) return;
    // the new version loads behind the old one and replaces it only when it has drawn: no white flash while building
    studio.querySelectorAll('[data-pane=frames] .pvfit').forEach(w => {
      const old = w.querySelector('iframe:last-of-type'); if (!old) return;
      w.querySelectorAll('iframe.next').forEach(x => x.remove());
      const nf = old.cloneNode(false); nf.classList.add('next');
      nf.src = o.edit ? path + '__edit/' + S(o.editPage) + '?r=' + o.reloadN + '#y=' + N(o.editY) : path + '?r=' + o.reloadN;
      nf.addEventListener('load', () => { setTimeout(() => { nf.classList.remove('next'); w.querySelectorAll('iframe').forEach(x => { if (x !== nf) x.remove(); }); }, 250); }, {once: true});
      w.appendChild(nf); scaleOne(w);
    });
    const age = studio.querySelector('.pvage'); if (age) age.textContent = 'fresh · just now';
  }

  /* the other panes */
  function pane(o) {
    const v = o.v || {}, b = M(v.board);
    switch (o.tab) {
      case 'plan': return planPane(o);
      case 'looks': return looksPane(o);
      case 'board': return `<section class="bbox"><h4>Board: pages and their parts</h4>${progress(o)}${L(b.pages).map(p => `<div class="bpg"><b>${esc(p.title)}</b><div class="bchips">${L(p.sections).map(s => chip(s.label, s.state)).join('')}</div></div>`).join('') || '<div class="stempty">Plan pakka hote hi hisse yahan dikhenge.</div>'}</section>`;
      case 'kadam': return kadamPane(o);
      case 'jaanch': return sitePane(o);
      case 'data': return `<div class="stdata"><div class="stempty">${spin()} Loading the app…</div></div>`;
      case 'screens': return screensPane(o);
      case 'dhaancha': return dnaPane(o);
      case 'android': return androidPane(o);
    }
    return '';
  }
  function kadamPane(o) {
    let rows = o.log.slice().reverse();
    if (!rows.length) {     // opened later: what the board already shows as done
      rows = L(M(o.v?.board).pages).flatMap(p => L(p.sections).filter(s => ['done', 'building', 'fixing'].includes(s.state))
        .map(s => ({text: `${p.title} → ${s.label}`, state: s.state === 'done' ? 'ok' : 'run'}))).reverse();
    }
    if (!rows.length) return '<section class="bbox"><h4>Steps</h4><div class="stempty">No steps yet.</div></section>';
    const mk = {ok: '✓', run: '⋯', bad: '✕', stop: '■'};
    return `<section class="bbox"><h4>Steps (the real work, as it happened)</h4><ol class="bsteps">${rows.map(r => `<li class="${r.state}"><time>${r.t ? clock(r.t) : ''}</time><i>${mk[r.state] || '·'}</i><span>${esc(r.text)}${r.secs ? ` <em>· ${r.secs} sec</em>` : ''}</span></li>`).join('')}</ol>
      <p class="faint" style="font-size:12px;margin-top:8px">Timed steps are from after this console opened; earlier ones come from the board.</p></section>`;
  }
  /* v0.315 big sites: how many pages, which come from lists (one designed template each), the menu groups */
  function sizeLine(v) {
    const z = M(v.size);
    return `<div class="bln"><b>${esc(String(z.total || 0))} pages</b> <span class="faint">· ${esc(String(z.designed || 0))} designed · ${esc(String(z.items || 0))} from lists · ${esc(String(z.legal || 0))} legal</span></div>`;
  }
  function bigPlan(v, pl) {
    const byslug = Object.fromEntries(L(pl.pages).map(p => [p.slug, p]));
    const cols = L(v.collections).map(c => `<div class="bln">• <b>${esc(c.label)}</b>: ${esc(String(c.items))} pages from one template <span class="faint">(${esc(L(c.examples).join(', '))}${c.items > L(c.examples).length ? ', …' : ''})</span></div>`).join('');
    const groups = L(pl.groups).map(g => `<div class="bln">${g.group ? `<b>${esc(g.group)}</b>: ` : '• '}${esc(L(g.pages).map(sg => M(byslug[sg]).title || sg).join(' · '))}</div>`).join('');
    return sizeLine(v) + (cols ? `<h5 class="bsub">Lists</h5>${cols}` : '') + (groups ? `<h5 class="bsub">Menu</h5>${groups}` : '')
      + `<h5 class="bsub">Designed pages and their sections</h5>`
      + L(pl.pages).map(p => `<div class="bln faint">• ${esc(p.title)}: ${esc(L(p.sections).join(', '))}</div>`).join('');
  }
  function planPane(o) {
    const v = o.v || {}, pl = M(v.plan), qs = L(v.questions);
    if (o.type === 'site' && v.mapping) return `<div class="stempty">${spin()} Opus is planning the whole site map: pages, menu groups and lists of pages…</div>`;
    const list = o.type === 'site'
      ? (v.size ? bigPlan(v, pl) : L(pl.pages).map(p => `<div class="bln">• <b>${esc(p.title)}</b>: ${esc(L(p.sections).join(', '))}</div>`).join(''))
      : `<div class="bln"><b>${L(pl.screens).length + L(pl.code_screens).length} screens</b>${L(pl.tabs).length ? ` · bottom tabs: ${esc(L(pl.tabs).join(' · '))}` : ''}</div>`
        + (L(pl.flow).length ? `<div class="bln faint">Raasta: ${esc(L(pl.flow).join(' → '))}</div>` : '')
        + L(pl.screens).map(s => `<div class="bln">• ${esc(s.label)}${s.tab ? ' <span class="tag v">tab</span>' : ''}${s.design ? ` <span class="faint">${esc(S(s.design).slice(0, 90))}</span>` : ''}</div>`).join('')
        + L(pl.code_screens).map(s => `<div class="bln">• ${esc(s.label)} <span class="tag ok">kanoon</span> <span class="faint">${esc(s.why)}</span></div>`).join('')
        + (M(pl.scope).request ? `<div class="bln faint" style="font-style:italic">Aapne kaha: "${esc(pl.scope.request)}"</div>` : '');
    return `<section class="bbox"><h4>Plan</h4>${list || '<div class="stempty">Writing the plan…</div>'}</section>`
      + (qs.length ? `<section class="bbox"><h4>A few questions (answer what you know)</h4><form class="bqs" data-form="answers">${qs.map((q, i) => `<label>${esc(q)}<input name="${i}" autocomplete="off"></label>`).join('')}<div class="acts"><button class="btn soft" type="submit">Send answers</button></div></form></section>` : '')
      + (S(v.status) === 'planned' ? `<div class="acts">${btn('plan', 'Haan, make 3 looks', 'go')}</div>` : '');
  }
  function looksPane(o) {
    const looks = L(o.v?.looks);
    if (!looks.length) return `<div class="stempty">${spin()} Making 3 looks: the real Home screen in three styles…</div>`;
    const cf = o.colorsFrom;
    return `<p class="faint" style="font-size:13px">The real Home screen in three styles. The other ${o.type === 'site' ? 'sections' : 'screens'} follow the look you pick.</p>
      <div class="blookgrid">${looks.slice(0, 3).map((lk, i) => {
        const sh = M(lk.shots), art = M(lk.art);
        const cols = L(lk.colors).map(hex).filter(Boolean);
        return `<article class="blook${cf === i ? ' cf' : ''}">
          <div class="blkpics">${o.type === 'site' ? pic(shotPath('site', o.id, sh['390']), `Look ${i + 1} phone`, 'ph') + pic(shotPath('site', o.id, sh['1440']), `Look ${i + 1} computer`, 'pc') : pic(shotPath('app', o.id, sh.android), `Look ${i + 1}`, 'ph')}</div>
          <b>${i + 1} · ${esc(lk.label)}</b>${art.concept ? `<span class="faint">${esc(art.concept)}</span>` : ''}
          <div class="bsw">${cols.map(c => `<i style="background:${c}" role="img" aria-label="Colour ${esc(c)}"></i>`).join('')}</div>
          <div class="acts">${btn('look', 'This one', 'go', ` data-i="${i}"`)}${btn('colors', cf === i ? '✓ Its colours' : 'Its colours', 'soft', ` data-i="${i}" aria-pressed="${cf === i}"`)}</div></article>`;
      }).join('')}</div>${cf != null ? `<p class="acc" style="font-size:13px;font-weight:600">Look ${cf + 1}&rsquo;s colours will be used. The look you pick now gives the structure, these give the colours.</p>` : ''}`;
  }
  function sitePane(o) {
    const v = o.v || {}, sh = M(v.shots);
    const phone = shotPath('site', o.id, sh['home-390.jpg']), pc = shotPath('site', o.id, sh['home-1440.jpg']), vid = shotPath('site', o.id, sh['scroll.mp4']);
    const pv = previewPath(v.preview);
    return (Object.keys(M(v.scores)).length ? `<section class="bbox"><h4>Number (Lighthouse)</h4>${scoresBlock(v.scores)}</section>` : '')
      + ((phone || pc) ? `<section class="bbox"><h4>On phone and computer (real screenshots)</h4><div class="bshots">${pic(phone, 'Phone screenshot', 'ph')}${pic(pc, 'Computer screenshot', 'pc')}</div>
          ${vid ? `<video class="bvid" data-src="${esc(vid)}" controls muted playsinline preload="none" aria-label="Scroll video"></video>` : ''}</section>` : '')
      + (checksBlock(o, 'Checks (small phone, contrast, buttons, links)') || `<div class="stempty">${working(o) ? spin() + ' Checks run after the website is built.' : 'Checks have not run yet.'}</div>`)
      + (S(v.status) === 'ready' ? `<section class="bbox next"><h4>Next: Domain → Hosting + DNS → Live</h4><p class="faint" style="font-size:13px">Buying a domain and going live need your Haan (the card comes in the chat).</p>
          <div class="acts">${pv ? `<a class="btn soft" href="${esc(pv)}" target="_blank" rel="noopener">Open preview</a>` : ''}${btn('say-domain', 'Find a domain', 'go')}${btn('say-live', 'Prepare to go live')}</div></section>` : '');
  }
  function screensPane(o) {
    const v = o.v || {}, b = M(v.board), ov = M(b.overview), plat = o.plat && ov[o.plat] ? o.plat : 'android';
    const labels = Object.fromEntries(L(v.plan?.screens).map(s => [s.id, s.label]));
    const sc = M(b.scores);
    return `<section class="bbox"><h4>Every screen, as a real screenshot</h4>${progress(o)}
      ${L(b.pages).map(p => `<div class="bpg"><b>${esc(p.title)}</b><div class="bscr">${L(p.sections).map(s => {
        const cls = s.state === 'done' ? 'ok' : s.state === 'building' ? 'run' : s.state === 'fixing' ? 'fix' : s.state === 'failed' ? 'bad' : 'todo';
        const th = shotPath('app', o.id, s.thumb), full = shotPath('app', o.id, S(s.thumb).replace(/^thumb\//, ''));
        return `<button type="button" class="bsc ${cls}" ${th ? `data-ba="zoom" data-full="${esc(full)}" data-cap="${esc(s.label)}"` : 'disabled'} aria-label="${esc(s.label)}">
          <span class="fr">${th ? pic(th, s.label) : s.state === 'building' ? spin(20) : `<i>${s.state === 'done' ? '✓' : ''}</i>`}</span>
          <span class="lb">${s.state === 'done' ? '✓ ' : s.state === 'building' ? '⋯ ' : ''}${esc(s.label)}</span></button>`; }).join('')}</div></div>`).join('') || '<div class="stempty">Screens appear here after you pick a look.</div>'}
      <p class="faint" style="font-size:12px">Click a picture to enlarge it. The code-made screens (privacy, delete account) are required by law.</p></section>
      ${ov.android ? `<section class="bbox"><div class="bhrow"><h4>All screens at once</h4><div class="bseg" role="group" aria-label="Phone">${[['android', 'Android'], ['ios', 'iPhone'], ['android-alt', M(v.design).dark ? 'Light' : 'Dark']].filter(([k]) => ov[k]).map(([k, n]) => `<button type="button" data-ba="plat" data-p="${k}" aria-pressed="${k === plat}">${n}</button>`).join('')}</div></div>
          <button type="button" class="bov" data-ba="zoom" data-full="${esc(shotPath('app', o.id, ov[plat]))}" data-cap="All screens">${pic(shotPath('app', o.id, ov[plat]), 'All screens')}</button></section>` : ''}
      ${Object.keys(sc).length ? `<section class="bbox"><h4>Opus’s own scores for its screens</h4><div class="bchips">${Object.entries(sc).map(([k, x]) => { x = M(x); const n = +x.score || 0;
          return `<span class="bchip ${n >= 8 ? 'ok' : n >= 6 ? 'run' : 'bad'}">${esc(labels[k] || k)}: ${x.before ? esc(x.before) + ' → ' : ''}${n.toFixed(1)}/10</span>`; }).join('')}</div></section>` : ''}
      ${checksBlock(o, 'Checks (Android + iPhone, small phone)')}
      ${S(v.status) === 'ready' ? `<div class="acts">${btn('approve', 'Approve design', 'go')}</div>` : ''}`;
  }
  function dnaPane(o) {
    const v = o.v || {}, art = M(v.art), d = M(v.design), pl = M(v.plan);
    const line = (k, t) => t ? `<div class="bkv"><span>${k}</span><b>${esc(t)}</b></div>` : '';
    const cols = L(d.colors).map(hex).filter(Boolean);
    return `<section class="bbox"><h4>${esc(art.concept || 'Design idea')}${v.model ? ` <span class="tag v">${esc(v.model)}</span>` : ''}</h4>
        ${art.idea ? `<p style="font-style:italic;font-size:13.5px">${esc(art.idea)}</p>` : ''}
        ${line('Signature', art.signature)}${line('Layout', art.layout)}${line('Hero', art.hero)}${line('Motion', art.motion)}${art.three_d ? line('3D', L(art.scenes).join(', ') || 'yes') : ''}</section>
      ${Object.keys(d).length ? `<section class="bbox"><h4>Design structure</h4>${cols.length ? `<div class="bsw lg">${cols.map(c => `<i style="background:${c}" role="img" aria-label="Colour ${esc(c)}"></i>`).join('')}</div>` : ''}
        ${line('Navigation', d.nav)}${line('Main button', d.fab)}${line('Card', d.card)}${line('Button', d.button)}${line('Header', d.header)}${line('Transition', d.transition)}${line('Font', L(d.fonts).filter(Boolean).join(' / '))}${line('Mode', d.dark ? 'dark' : d.mode)}</section>` : ''}
      ${L(pl.tabs).length || L(pl.flow).length ? `<section class="bbox"><h4>Flow</h4>${line('Bottom tabs', L(pl.tabs).join(' · '))}${line('Flow', L(pl.flow).join(' → '))}${L(pl.rules).length ? line('Rules', L(pl.rules).join(' · ')) : ''}</section>` : ''}`;
  }
  /* v0.325 HOOLA QA: what the device check found on a real Android emulator after the build compiled */
  function qaBox(o) {
    const q = M(o.an?.qa); if (!Object.keys(q).length) return '';
    if (!q.ran) return `<section class="bbox"><h4>Device check</h4><p class="faint" style="font-size:12.5px">${esc(S(q.why) || 'Not run on this build machine.')}</p></section>`;
    const p = M(q.perf), b = M(q.budget), tag = k => b[k] === 'over' ? 'warn' : 'ok';
    return `<section class="bbox"><h4>Device check · ${N(q.opened)} / ${N(q.total)} screens opened without a crash</h4>
      <div class="bln">${p.cold_ms != null ? `<span class="tag ${tag('cold_ms')}">Cold start ${N(p.cold_ms)} ms</span> ` : ''}${p.jank_pct != null ? `<span class="tag ${tag('jank_pct')}">Janky frames ${esc(S(p.jank_pct))}%</span> ` : ''}${p.apk_mb != null ? `<span class="tag ${tag('apk_mb')}">APK ${esc(S(p.apk_mb))} MB</span> ` : ''}<span class="tag ${N(q.a11y_count) ? 'warn' : 'ok'}">${N(q.a11y_count)} accessibility findings</span></div>
      ${L(q.crashed).length ? `<div class="badc bln">Crashed: ${esc(L(q.crashed).join(', '))} (shipped as the simple version)</div>` : ''}
      ${L(q.a11y).slice(0, 6).map(f => `<div class="bln faint">${esc(S(f.screen))}: ${esc(S(f.text))}</div>`).join('')}
      ${L(q.shots).length ? `<div class="blooks">${L(q.shots).slice(0, 12).map(sh => `<figure>${pic(`${base(o)}/android/qa/${encodeURIComponent(sh)}`, sh)}<figcaption>${esc(sh)}</figcaption></figure>`).join('')}</div>` : ''}</section>`;
  }

  /* v0.330 Google Play from HER OWN developer account: steps, package, her service-account key (file -> sealed, never shown),
     listing, bundle, Internal testing, Production only after a confirm */
  async function loadStore(o, root) {
    const box = root.querySelector('.ststore'); if (!box || !S(o.an?.status)) return;
    let v; try { v = await api('GET', base(o) + '/store'); } catch (er) { return; }
    const step = id => (L(v.steps).find(x => x.id === id) || {}).done, l = M(v.listing);
    box.innerHTML = `<section class="bbox"><h4>Google Play Store · ${L(v.steps).filter(x => x.done).length} / ${L(v.steps).length}</h4>
      ${v.now ? `<div class="bln">${esc(S(v.now))}</div>` : ''}${v.error ? `<div class="badc bln">${esc(S(v.error))}</div>` : ''}
      ${L(v.steps).map(x => `<div class="bln ${x.done ? '' : 'faint'}">${x.done ? '✓' : '○'} ${esc(S(x.label))}${x.value ? ' · ' + esc(S(x.value)) : ''}</div>`).join('')}
      <form class="stapp" data-st="setup"><label for="stPkg"><b>Package name</b> <span>Permanent: Google never lets it change.</span></label>
        <div class="row"><input id="stPkg" value="${esc(S(v.package) || S(v.proposed))}" ${v.locked ? 'disabled' : ''}><button class="btn soft" type="submit" ${v.locked ? 'disabled' : ''}>Confirm</button></div></form>
      ${v.account ? `<div class="bln">Play account linked: ${esc(S(v.account))} <button class="btn soft" type="button" data-st="forget">Remove key</button></div>`
        : `<label class="bln"><b>Your Play service-account key (JSON file)</b> <span class="faint">Play Console > Setup > API access. Sealed on the server, never shown again; never paste it in chat.</span><br><input type="file" accept=".json,application/json" data-st="key"></label>`}
      ${l.title ? `<div class="bln"><b>${esc(S(l.title))}</b><div class="faint">${esc(S(l.short))}</div></div>` : ''}
      <div class="acts"><button class="btn soft" type="button" data-st="listing" ${step('package') ? '' : 'disabled'}>${l.title ? 'Rewrite listing' : 'Write listing'}</button>
        <button class="btn soft" type="button" data-st="build" ${step('package') ? '' : 'disabled'}>Build store bundle</button>
        <button class="btn go" type="button" data-st="internal" ${step('bundle') && step('account') ? '' : 'disabled'}>Send to Internal testing</button>
        <button class="btn soft" type="button" data-st="production" ${step('internal') ? '' : 'disabled'}>Production (everyone)</button></div>
      <div class="bln faint">Privacy policy: ${esc(S(v.privacy_url))}<br>Data deletion: ${esc(S(v.delete_url))}</div>
      ${L(v.console_steps).map(t => `<div class="bln faint">• ${esc(S(t))}</div>`).join('')}
      ${L(v.data_safety).length ? `<div class="bln"><b>Data safety answers</b>${L(v.data_safety).map(x => `<div class="faint">• ${esc(S(x.type))} - ${esc(S(x.why))}</div>`).join('')}</div>` : ''}</section>`;
    const go = async (what, body, ok) => { try { await api('POST', base(o) + '/store/' + what, body); if (ok) toast(ok); loadStore(o, root); } catch (er) { toast(er.message, true); } };
    box.querySelector('form[data-st=setup]')?.addEventListener('submit', e => { e.preventDefault(); go('setup', {package: box.querySelector('#stPkg').value.trim()}, 'Package confirmed.'); });
    box.querySelector('input[data-st=key]')?.addEventListener('change', async e => { const f = e.target.files[0]; if (!f) return; go('credentials', {json: await f.text()}, 'Play account linked.'); });
    box.onclick = e => { const b = e.target.closest('button[data-st]'); if (!b) return;
      const w = b.dataset.st;
      if (w === 'forget') go('forget', {}, 'Key removed.');
      if (w === 'listing') go('listing', {regen: true}, 'Listing written.');
      if (w === 'build') go('build', {}, 'Building the store bundle.');
      if (w === 'internal') go('publish', {track: 'internal'}, 'Sending to Google Play (Internal testing).');
      if (w === 'production' && confirm('Send to Production? After Google review the app is public on the Play Store for everyone.')) go('publish', {track: 'production', her_tap: true}, 'Sending to Production.');
    };
  }

  /* v0.332 IPHONE: the same design + backend as a SwiftUI app, compiled on a Mac (her builds repo), every screen opened in an
     iPhone simulator; TestFlight with HER App Store Connect key (a secret in her builds repo, never here) after a confirm */
  async function loadIos(o, root) {
    const box = root.querySelector('.stios'); if (!box) return;
    let v; try { v = await api('GET', base(o) + '/ios'); } catch (er) { return; }
    const q = M(v.qa), p = M(q.perf), tf = M(v.testflight), run = M(v.runner), st = S(v.status);
    const busy = ['writing', 'building', 'fixing', 'uploading'].includes(st);
    box.innerHTML = `<section class="bbox"><h4>iPhone app${st ? ' · ' + esc(st) : ''}</h4>
      <div class="bln">${esc(S(v.now) || S(v.say))}</div>${v.error ? `<div class="badc bln">${esc(S(v.error))}</div>` : ''}
      <div class="bln faint">Bundle ID: ${esc(S(v.bundle_id))}</div>
      ${tf.build ? `<div class="bln">TestFlight: v${esc(S(tf.version))} (build ${esc(S(tf.build))})</div>` : ''}
      ${q.ran ? `<div class="bln">iPhone simulator: ${esc(S(q.opened))} / ${esc(S(q.total))} screens opened without a crash${p.launch_ms != null ? ` · opens in ${esc(S(p.launch_ms))} ms` : ''}${p.app_mb != null ? ` · ${esc(S(p.app_mb))} MB` : ''}</div>
        ${L(q.shots).length ? `<div class="blooks">${L(q.shots).slice(0, 14).map(sh => `<figure>${pic(`${base(o)}/ios/qa/${encodeURIComponent(sh)}`, sh)}<figcaption>${esc(sh)}</figcaption></figure>`).join('')}</div>` : ''}` : ''}
      ${run.ready ? '' : `<div class="bln faint">iPhone apps compile only on a Mac. Once: put server/app_builder/hoola-ios.yml in your private GitHub builds repo (.github/workflows/). For TestFlight add the repo secrets ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8, APPLE_TEAM_ID (App Store Connect > Users and Access > Integrations; never paste the key here or in chat) and create the app once in App Store Connect with this bundle ID.</div>`}
      <div class="acts"><button class="btn soft" type="button" data-io="sim" ${busy ? 'disabled' : ''}>${v.build ? 'Build the iPhone app again' : 'Build the iPhone app'}</button>
        <button class="btn go" type="button" data-io="testflight" ${busy || st !== 'ready' || !run.ready ? 'disabled' : ''}>Send to TestFlight</button>
        ${v.zip_url ? `<a class="btn soft" href="${esc(S(v.zip_url))}">Xcode project (ZIP)</a>` : ''}</div></section>`;
    box.onclick = async e => { const b = e.target.closest('button[data-io]'); if (!b) return;
      const kind = b.dataset.io;
      if (kind === 'testflight' && !confirm('Send this build to TestFlight on your Apple account? Only your testers see it; sending to the App Store stays your tap in App Store Connect.')) return;
      try { await api('POST', base(o) + '/ios', {kind}); toast(kind === 'testflight' ? 'Sending to TestFlight.' : 'Building the iPhone app.'); loadIos(o, root); } catch (er) { toast(er.message, true); } };
    if (busy) setTimeout(() => { if (document.body.contains(box)) loadIos(o, root); }, 8000);
  }

  /* v0.338 App Store from HER Apple account: listing within Apple's limits, push (listing + 6.9" screenshots + the TestFlight
     build, run in her builds repo with her key), Submit for Review only after her confirm */
  async function loadAppStore(o, root) {
    const box = root.querySelector('.stappstore'); if (!box) return;
    let v; try { v = await api('GET', base(o) + '/appstore'); } catch (er) { return; }
    const step = id => (L(v.steps).find(x => x.id === id) || {}).done, l = M(v.listing), lim = M(v.limits), st = S(v.status);
    const busy = st === 'pushing' || st === 'submitting';
    const fld = (k, label, area) => `<label class="bln"><b>${label}</b> <span class="faint">${S(l[k]).length} / ${esc(S(lim[k]))}</span><br>${area
      ? `<textarea data-as="${k}" rows="5" maxlength="${esc(S(lim[k]))}">${esc(S(l[k]))}</textarea>` : `<input data-as="${k}" maxlength="${esc(S(lim[k]))}" value="${esc(S(l[k]))}">`}</label>`;
    box.innerHTML = `<section class="bbox"><h4>Apple App Store · ${L(v.steps).filter(x => x.done).length} / ${L(v.steps).length}</h4>
      ${v.now ? `<div class="bln">${esc(S(v.now))}</div>` : ''}${v.error ? `<div class="badc bln">${esc(S(v.error))}</div>` : ''}
      ${L(v.steps).map(x => `<div class="bln ${x.done ? '' : 'faint'}">${x.done ? '✓' : '○'} ${esc(S(x.label))}${x.value ? ' · ' + esc(S(x.value)) : ''}</div>`).join('')}
      ${l.name ? fld('name', 'Name') + fld('subtitle', 'Subtitle') + fld('keywords', 'Keywords (comma separated)') + fld('promotionalText', 'Promotional text') + fld('description', 'Description', true) : ''}
      <div class="acts"><button class="btn soft" type="button" data-asb="listing" ${busy ? 'disabled' : ''}>${l.name ? 'Rewrite listing' : 'Write listing'}</button>
        ${l.name ? `<button class="btn soft" type="button" data-asb="save" ${busy ? 'disabled' : ''}>Save edits</button>` : ''}
        <button class="btn soft" type="button" data-asb="push" ${busy || !step('testflight') || !step('listing') ? 'disabled' : ''}>Send to App Store Connect</button>
        <button class="btn go" type="button" data-asb="submit" ${busy || !step('pushed') ? 'disabled' : ''}>Submit for review</button></div>
      <div class="bln faint">Privacy policy: ${esc(S(v.privacy_url))}<br>Support: ${esc(S(v.support_url))}<br>Age rating: ${esc(S(v.age_rating))}</div>
      <div class="bln"><b>Once in App Store Connect</b>${L(v.one_time).map(t => `<div class="faint">• ${esc(S(t))}</div>`).join('')}</div>
      <div class="bln"><b>App Privacy answers</b>${L(v.privacy_answers).map(x => `<div class="faint">• ${esc(S(x.type))} - ${esc(S(x.why))}${x.linked === false ? ' (not linked)' : ''}</div>`).join('')}</div></section>`;
    const go = async (what, body, ok) => { try { await api('POST', base(o) + '/appstore/' + what, body); if (ok) toast(ok); loadAppStore(o, root); } catch (er) { toast(er.message, true); } };
    box.onclick = e => { const b = e.target.closest('button[data-asb]'); if (!b) return;
      const w = b.dataset.asb;
      if (w === 'listing') go('listing', {regen: true}, 'Listing written.');
      if (w === 'save') { const edit = {}; box.querySelectorAll('[data-as]').forEach(x => { edit[x.dataset.as] = x.value.trim(); }); go('listing', {edit}, 'Listing saved.'); }
      if (w === 'push') go('push', {}, 'Sending to App Store Connect (a few minutes).');
      if (w === 'submit' && confirm('Submit this version for Apple review? Apple usually takes 1-2 days; releasing it after approval stays your choice. Are App Information, Age Rating and App Privacy filled in?')) go('submit', {her_tap: true}, 'Submitting for review.');
    };
    if (busy) setTimeout(() => { if (document.body.contains(box)) loadAppStore(o, root); }, 10000);
  }

  /* v0.325 every build of the app: what changed, and Bring back for a kept one */
  function historyBox(o) {
    const h = L(o.an?.history), kept = L(o.an?.kept_builds); if (!h.length) return '';
    return `<section class="bbox"><h4>Versions</h4>${h.slice(0, 8).map((x, i) => `<div class="bln"><b>v${esc(S(x.version_name))}</b> · build ${N(x.build)}${i === 0 ? ' · current' : ''}
      ${L(x.notes).slice(0, 3).map(t => `<div class="faint" style="font-size:12.5px">${esc(S(t))}</div>`).join('')}
      ${i > 0 && kept.includes(x.build) && !anWorking(o) ? btn('rollback', 'Bring back', 'soft', ` data-build="${N(x.build)}"`) : ''}</div>`).join('')}</section>`;
  }

  function androidPane(o) {
    const v = o.v || {}, a = o.an || {}, s = S(a.status);
    if (!v.approved && !s) return `<section class="bbox"><h4>Real Android app</h4><p class="muted" style="font-size:13.5px">Approve the design first: the real app is built from it.</p>${S(v.status) === 'ready' ? `<div class="acts">${btn('approve', 'Approve design', 'go')}</div>` : ''}</section>`;
    if (!s) return `<section class="bbox"><h4>Real Android app</h4><p class="muted" style="font-size:13.5px">Every screen is written in Kotlin + Jetpack Compose and compiled on the build machine into an APK for your phone.</p><div class="acts">${btn('android', 'Build Android app', 'go')}</div></section>`;
    const step = {writing: 0, building: 1, fixing: 2, ready: 4, zip: 4, failed: -1}[s] ?? 0;
    const failAt = s === 'failed' ? (N(a.rounds) ? 2 : L(a.screens).every(x => ['written', 'done', 'code'].includes(x.state)) ? 1 : 0) : -1;
    const pipe = [['Writing screens', `Kotlin + Compose · ${L(a.screens).filter(x => ['written', 'done', 'code', 'compiling'].includes(x.state)).length} / ${L(a.screens).length}`],
      ['Compile', S(a.where) || 'build machine'], ['Error fixes', N(a.rounds) ? `${a.rounds} round(s)` : 'automatic after each round'], ['APK', s === 'zip' ? 'no build machine: project ZIP' : 'for your phone']]
      .map(([t, sub], i) => { const st = failAt === i ? 'bad' : (step === 4 || i < step) ? 'ok' : i === step ? 'run' : 'todo';
        return `<li class="${st}"><i>${st === 'ok' ? '✓' : st === 'bad' ? '✕' : i + 1}</i><b>${t}</b><span>${esc(sub)}</span></li>`; }).join('');
    const apk = M(a.apk), dl = publicLink(a.apk_url), zip = publicLink(a.zip_url), redo = L(a.screens).filter(x => x.state === 'code').map(x => x.id);
    return `<ol class="bpipe">${pipe}</ol>
      ${s === 'failed' && a.error ? `<div class="badc bln">${esc(a.error)}</div>` : ''}${a.note ? `<div class="muted bln">${esc(a.note)}</div>` : ''}
      ${qaBox(o)}${historyBox(o)}<div class="ststore"></div><div class="stios"></div><div class="stappstore"></div>
      <div class="bcols"><section class="bbox"><h4>Screens in Kotlin</h4>${L(a.screens).map(x => { const [t, c] = TILE[x.state] || TILE.todo;
          return `<div class="bscrow"><i class="${c}"></i><span>${esc(x.label)}</span><em class="${c}">${esc(t)}</em></div>`; }).join('') || '<div class="stempty">…</div>'}
          ${N(a.rounds) ? `<p class="faint" style="font-size:12px;margin-top:6px">Fixed compile errors by itself in ${a.rounds} round(s).</p>` : ''}</section>
        <section class="bbox"><h4>APK</h4>${apk.file ? `<div class="bln">${esc(apk.file)} · ${mb(apk.size)} · v${esc(S(apk.version_name))}</div>
            <div class="bln faint">package ${esc(S(apk.package))}${apk.sha256 ? ` · SHA-256 ${esc(S(apk.sha256).slice(0, 8))}…${esc(S(apk.sha256).slice(-6))}` : ''}</div>` : `<div class="stempty">${anWorking(o) ? spin() + ' ' : ''}APK compile poora hone par yahan.</div>`}
          ${dl ? `<div class="bqr"><img data-qr="${esc(location.origin + dl)}" alt="QR code for the APK link" width="148" height="148"><span class="faint">Scan with your phone to download the APK. The link lasts a few days.</span></div>` : ''}
          <p class="faint" style="font-size:12px">This is a preview build for your phone. Publishing on the Play Store is the next step, from your own developer account.</p>
          <div class="acts">${dl ? `<a class="btn go" href="${esc(dl)}" download>APK download</a>` : ''}${zip ? `<a class="btn soft" href="${esc(zip)}" download>Project ZIP${a.zip_size ? ' (' + mb(a.zip_size) + ')' : ''}</a>` : ''}
            ${redo.length && !anWorking(o) ? btn('redo', `Rewrite simple screens (${redo.length})`, 'soft', ` data-ids="${esc(redo.join(','))}"`) : ''}${['ready', 'zip', 'failed'].includes(s) && !redo.length ? btn('android', 'Build again') : ''}</div></section></div>`;
  }
  function qr(root) {
    root.querySelectorAll('img[data-qr]').forEach(img => {
      try { const q = window.qrcode(0, 'M'); q.addData(img.dataset.qr); q.make(); img.src = q.createDataURL(4, 2); } catch { img.replaceWith(Object.assign(document.createElement('span'), {className: 'faint', textContent: 'Could not make the QR code: download from the link.'})); }
      img.removeAttribute('data-qr');
    });
  }

  /* ---------------- actions ---------------- */
  const base = o => `/api/${o.type === 'site' ? 'sites' : 'apps'}/${encodeURIComponent(o.id)}`;
  async function call(o, path, body, ok) {
    try { const r = await api('POST', base(o) + path, Object.assign({conversation_id: C.conv() || ''}, body || {})); if (ok) toast(r?.say || ok); return r; }
    catch (e) { toast(e.message, true); return null; }
  }
  async function change(o) {
    const inp = studio.querySelector('#stIn'), t = inp.value.trim(); if (!t) return;
    inp.value = ''; const r = await call(o, '/change', {instruction: t}, 'Change noted: ' + t); if (!r) inp.value = t;
  }
  async function act(e, o) {
    const tab = e.target.closest('[data-tab]');
    if (tab && o) { o.tab = tab.dataset.tab; draw(); return; }
    const b = e.target.closest('[data-ba]'); if (!b || !o) return;
    const a = b.dataset.ba;
    if (b.tagName === 'BUTTON') b.disabled = true;
    try {
      switch (a) {
        case 'close': close(); break;
        case 'studio': open(o.k); break;
        case 'studio-android': o.tab = 'android'; open(o.k); o.tab = 'android'; draw(); break;
        case 'stop': await call(o, '/stop', {}, 'Stopping: it finishes the current part, then stops.'); break;
        case 'resume': await call(o, '/resume', {}, 'Continuing from where it stopped.'); break;
        case 'plan': await call(o, '/plan', {}, 'Making 3 looks — they will appear here.'); break;
        case 'look': await call(o, '/look', {index: +b.dataset.i, ...(o.colorsFrom != null ? {colors_from: o.colorsFrom} : {})}, 'Look chosen: building starts.'); o.colorsFrom = null; break;
        case 'colors': o.colorsFrom = o.colorsFrom === +b.dataset.i ? null : +b.dataset.i; draw(); break;
        case 'approve': {
          if (!confirm('Approve this design? The real Android / iPhone app is built from it. Later changes make a new version.')) break;
          try { const r = await api('POST', base(o) + '/approve', {hash: S(o.v?.hash)}); toast(r?.say || 'Design approved!'); } catch (er) { toast(er.message, true); }
          break; }
        case 'android': await call(o, '/android', {}, 'Building the Android app: every screen in Kotlin, then compile.'); o.tab = 'android'; break;
        case 'redo': await call(o, '/android', {redo: S(b.dataset.ids).split(',').filter(Boolean)}, 'Rewriting the simple screens.'); break;
        case 'rollback': {   // v0.325 an older build again, as a new version
          if (!confirm(`Bring back build ${S(b.dataset.build)}? It is released as a new version, so phones take it as an update.`)) break;
          await call(o, '/rollback', {build: +b.dataset.build}, `Bringing back build ${S(b.dataset.build)}.`); break; }
        case 'reload': reloadFrames(o, true); break;
        case 'edit': {
          const r = await call(o, '/edit-mode', {}, '');
          if (r) { o.edit = true; o.photos = L(r.photos); o.tokens = M(r.tokens); o.editPage = ''; o.editY = 0; o.framesFor = ''; draw(); toast('Edit mode: click any words on the page and type. Free, no AI.'); }
          break; }
        case 'edit-done': o.edit = false; o.framesFor = ''; draw(); break;
        case 'undo': { const r = await call(o, '/undo', {}, 'Undone.'); if (r) reloadFrames(o, true); break; }
        case 'theme': await themeDialog(o); break;
        case 'plat': o.plat = b.dataset.p; draw(); break;
        case 'zoom': zoom(b.dataset.full, b.dataset.cap); break;
        case 'say-domain': C.say(`${title(o)} website ke liye achha domain dhoondho`); break;
        case 'say-live': C.say(`${title(o)} website live karne ki taiyaari karo (domain, hosting, DNS)`); break;
      }
    } finally { if (b.tagName === 'BUTTON' && b.isConnected) b.disabled = false; }
  }
  function zoom(path, cap) {
    if (!path) return;
    const d = document.createElement('div'); d.className = 'blb'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', cap || 'Screen');
    d.innerHTML = `<button class="ib" type="button" aria-label="Close">✕</button><img alt="${esc(cap || '')}"><span>${esc(cap || '')}</span>`;
    const shut = () => { d.remove(); removeEventListener('keydown', key); }, key = e => { if (e.key === 'Escape') shut(); };
    d.addEventListener('click', shut); addEventListener('keydown', key); document.body.appendChild(d);
    blob(path).then(u => { d.querySelector('img').src = u; }).catch(() => { d.querySelector('span').textContent = 'Picture not found.'; });
  }
  /* ---------------- v0.305 web app: her lists, entries, members (her own login = admin) ---------------- */
  /* v0.314 ASLI APP: the native app's own backend - every list (orders, bookings, a staff app's tables) with its rows,
     the status changed in place, accounts with their role. New entries also reach her chat by themselves. */
  async function loadAppData(o, box) {
    let info;
    try { info = await api('GET', base(o) + '/data'); } catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const cols = L(info.collections), counts = M(info.counts);
    box.innerHTML = `<p class="stnote">${info.live ? 'People using your app order / book here; every new entry also reaches your chat.' : 'Real orders and bookings appear here once the Android app is built.'}</p>
      <p class="stnote">${N(counts.members)} accounts · ${cols.map(c => `${esc(S(c.label))}: ${N(counts[c.key])}`).join(' · ')}</p><div class="stcols"></div><div class="stmem"></div>`;
    const cbox = box.querySelector('.stcols');
    for (const c of cols) {
      let rows = [];
      try { rows = L((await api('GET', `${base(o)}/data/${encodeURIComponent(c.key)}`)).rows); } catch (er) { toast(er.message, true); }
      const fields = L(c.fields);
      const sec = document.createElement('section'); sec.className = 'stcol';
      sec.innerHTML = `<h4>${esc(S(c.label))} <span>${rows.length}</span></h4>` + (rows.length ? `<div class="sttbl"><table><thead><tr>${fields.map(f => `<th>${esc(S(f.label))}</th>`).join('')}<th>When</th></tr></thead><tbody>${rows.map(r => `<tr data-r="${esc(S(r.id))}">${fields.map(f => {
        const v = r[f.key];
        if ((f.key === 'status' || f.key === 'paid') && f.type === 'choice') return `<td><select data-f="${f.key}" aria-label="${esc(S(f.label))}">${L(f.options).map(op => `<option${S(op) === S(v) ? ' selected' : ''}>${esc(S(op))}</option>`).join('')}</select></td>`;
        if (f.type === 'photo') return `<td>${/^f_[0-9a-f]{16}$/.test(S(v)) ? pic(`${base(o)}/files/${S(v)}`, S(f.label), 'stphoto') : ''}</td>`;   // v0.319
        if (f.type === 'location' && S(v)) return `<td><a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(S(v))}" target="_blank" rel="noopener">${esc(S(v))}</a></td>`;
        return `<td>${esc(f.type === 'yes_no' ? (v ? 'Yes' : 'No') : S(v)).replace(/\n/g, '<br>')}</td>`;
      }).join('')}<td>${esc(S(r.created).slice(0, 16).replace('T', ' '))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No entries yet.</p>');
      sec.addEventListener('change', async e => {
        const sl = e.target.closest('select[data-f]'), tr = e.target.closest('tr[data-r]'); if (!sl || !tr) return;
        try { await api('PATCH', `${base(o)}/data/${encodeURIComponent(c.key)}/${encodeURIComponent(tr.dataset.r)}`, {[sl.dataset.f]: sl.value}); toast('Saved.'); }
        catch (er) { toast(er.message, true); }
      });
      cbox.appendChild(sec);
      hydrate(sec);              // v0.319 photos load with her login
    }
    const mbox = box.querySelector('.stmem');
    try {
      const ms = L((await api('GET', base(o) + '/members')).members);
      mbox.innerHTML = `<h4>Accounts <span>${ms.length}</span></h4>` + (ms.length ? `<ul class="stmems">${ms.map(m => `<li data-m="${esc(S(m.id))}"><span>${esc(S(m.name) || S(m.email))} · ${esc(S(m.email))}</span>
        <select aria-label="Role">${['member', 'staff', 'admin'].map(r => `<option${r === S(m.role) ? ' selected' : ''}>${r}</option>`).join('')}</select></li>`).join('')}</ul>` : '<p class="stempty">Nobody has signed up yet.</p>');
      mbox.addEventListener('change', async e => {
        const sl = e.target.closest('select'), li = e.target.closest('li[data-m]'); if (!sl || !li) return;
        try { await api('POST', `${base(o)}/members/${encodeURIComponent(li.dataset.m)}/role`, {role: sl.value}); toast('Role changed: they sign in again.'); }
        catch (er) { toast(er.message, true); }
      });
    } catch (er) { /* no accounts list */ }
  }

  async function loadData(o, root) {
    const box = root.querySelector('.stdata'); if (!box) return;
    if (o.type === 'app') return loadAppData(o, box);
    let info;
    try { info = await api('GET', base(o) + '/app'); } catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const sc = M(info.app), cols = L(sc.collections), counts = M(info.counts);
    const design = `<form class="stapp" autocomplete="off"><label for="stApp"><b>${cols.length ? 'Change the app' : 'Make this website an app'}</b>
        <span>Logins, lists of data with rules, a My account page and a staff panel at /admin/. Say who logs in, what they fill and who sees it.</span></label>
        <div class="row"><input id="stApp" placeholder="e.g. customers log in and track their order; staff update the status"><button class="btn go" type="submit">${cols.length ? 'Update app' : 'Make app'}</button></div></form>
      <div class="acts"><button class="btn soft" type="button" data-x="react">Export as React project</button></div>`;
    box.innerHTML = design + (cols.length ? `<p class="stnote">${N(counts.members)} members · ${cols.map(c => `${esc(S(c.label))}: ${N(counts[c.key])}`).join(' · ')}</p><div class="stcols"></div><div class="stmem"></div>` : '');
    box.querySelector('.stapp').addEventListener('submit', async e => {
      e.preventDefault(); const w = box.querySelector('#stApp').value.trim(); if (!w) return;
      const b = e.target.querySelector('button'); b.disabled = true;
      try { const r = await api('POST', base(o) + '/app-design', {words: w, conversation_id: C.conv() || ''}); toast(S(r?.say) || 'App updated.'); loadData(o, root); }
      catch (er) { toast(er.message, true); b.disabled = false; }
    });
    box.querySelector('[data-x=react]').addEventListener('click', async e => {
      e.target.disabled = true;
      try { const r = await api('POST', base(o) + '/export', {format: 'react'}); toast(S(r?.say) || 'React project ready.'); if (r?.file_id) C.say && toast('The ZIP is in your files: ' + S(r.name)); }
      catch (er) { toast(er.message, true); } finally { e.target.disabled = false; }
    });
    const cbox = box.querySelector('.stcols');
    for (const c of cols) {
      let rows = [];
      try { rows = L((await api('GET', `${base(o)}/app/rows/${encodeURIComponent(c.key)}`)).rows); } catch (er) { toast(er.message, true); }
      const fields = L(c.fields);
      const sec = document.createElement('section'); sec.className = 'stcol';
      sec.innerHTML = `<h4>${esc(S(c.label))} <span>${rows.length}</span></h4>` + (rows.length ? `<div class="sttbl"><table><thead><tr>${fields.map(f => `<th>${esc(S(f.label))}</th>`).join('')}<th></th></tr></thead><tbody>${rows.map(r => `<tr data-r="${esc(S(r.id))}">${fields.map(f => {
        const v = r[f.key];
        if (f.type === 'choice') return `<td><select data-f="${esc(S(f.key))}" aria-label="${esc(S(f.label))}">${L(f.options).map(op => `<option${S(op) === S(v) ? ' selected' : ''}>${esc(S(op))}</option>`).join('')}</select></td>`;
        return `<td>${esc(f.type === 'yes_no' ? (v ? 'Yes' : 'No') : S(v))}</td>`;
      }).join('')}<td><button class="ib" type="button" data-del aria-label="Delete">✕</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No entries yet.</p>');
      sec.addEventListener('change', async e => {
        const s = e.target.closest('select[data-f]'), tr = e.target.closest('tr[data-r]'); if (!s || !tr) return;
        try { await api('PATCH', `${base(o)}/app/rows/${encodeURIComponent(c.key)}/${encodeURIComponent(tr.dataset.r)}`, {[s.dataset.f]: s.value}); toast('Saved.'); }
        catch (er) { toast(er.message, true); }
      });
      sec.addEventListener('click', async e => {
        const b = e.target.closest('[data-del]'), tr = e.target.closest('tr[data-r]'); if (!b || !tr || !confirm('Delete this entry?')) return;
        try { await api('DELETE', `${base(o)}/app/rows/${encodeURIComponent(c.key)}/${encodeURIComponent(tr.dataset.r)}`); tr.remove(); toast('Deleted.'); }
        catch (er) { toast(er.message, true); }
      });
      cbox.appendChild(sec);
    }
    const mbox = box.querySelector('.stmem');
    if (mbox) {
      try {
        const ms = L((await api('GET', base(o) + '/app/members')).members);
        mbox.innerHTML = `<h4>Members <span>${ms.length}</span></h4>` + (ms.length ? `<ul class="stmems">${ms.map(m => `<li data-m="${esc(S(m.id))}"><span>${esc(S(m.name) || S(m.email))} · ${esc(S(m.email))}</span>
          <select aria-label="Role">${['member', 'staff', 'admin'].map(r => `<option${r === S(m.role) ? ' selected' : ''}>${r}</option>`).join('')}</select></li>`).join('')}</ul>` : '<p class="stempty">Nobody has signed up yet.</p>');
        mbox.addEventListener('change', async e => {
          const s = e.target.closest('select'), li = e.target.closest('li[data-m]'); if (!s || !li) return;
          try { await api('POST', `${base(o)}/app/members/${encodeURIComponent(li.dataset.m)}/role`, {role: s.value}); toast('Role changed: they log in again.'); }
          catch (er) { toast(er.message, true); }
        });
      } catch (er) { /* no members list */ }
    }
  }

  /* ---------------- v0.295 edit mode: her own hands in the preview, no AI ---------------- */
  function dialog(title, inner) {
    return new Promise(done => {
      const d = document.createElement('div'); d.className = 'blb sted-dlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', title);
      d.innerHTML = `<form class="sted-card" autocomplete="off"><h3>${esc(title)}</h3>${inner}<div class="acts"><button class="btn soft" type="button" data-x>Cancel</button><button class="btn go" type="submit">Save</button></div></form>`;
      const f = d.querySelector('form'), shut = v => { d.remove(); removeEventListener('keydown', key); done(v); };
      const key = e => { if (e.key === 'Escape') shut(null); };
      d.addEventListener('click', e => { if (e.target === d || e.target.closest('[data-x]')) shut(null); });
      f.addEventListener('submit', e => { e.preventDefault(); shut(new FormData(f)); });
      f.addEventListener('click', e => { const c = e.target.closest('[data-pick]'); if (!c) return; f.querySelectorAll('[data-pick]').forEach(x => x.setAttribute('aria-pressed', String(x === c))); f.elements.pick.value = c.dataset.pick; });
      addEventListener('keydown', key); document.body.appendChild(d);
      const first = f.querySelector('input,button'); if (first) first.focus();
    });
  }
  async function editSend(o, body) {
    try { const r = await api('POST', base(o) + '/edit', body); toast(S(r?.say) || 'Saved.'); reloadFrames(o, true); }
    catch (er) { toast(er.message, true); reloadFrames(o, true); }
  }
  async function themeDialog(o) {
    const tk = M(o.tokens), row = (k, label) => `<label class="sted-c"><span>${label}</span><input type="color" name="${k}" value="${esc(hex(tk[k]) || '#888888')}"></label>`;
    const f = await dialog('Colours', `<div class="sted-cs">${row('primary', 'Main colour')}${row('accent', 'Accent')}${row('bg', 'Page background')}${row('surface', 'Card background')}${row('ink', 'Text')}</div>
      <label class="sted-c"><span>Corner roundness</span><input type="range" name="radius" min="0" max="32" value="${N(tk.radius)}"></label>
      <p class="sted-note">Hoola keeps text readable: if a colour would make words hard to read, the text colour adjusts.</p>`);
    if (!f) return;
    const tokens = {}; ['primary', 'accent', 'bg', 'surface', 'ink'].forEach(k => { const v = S(f.get(k)); if (v && v.toLowerCase() !== S(tk[k]).toLowerCase()) tokens[k] = v; });
    if (N(f.get('radius')) !== N(tk.radius)) tokens.radius = N(f.get('radius'));
    if (!Object.keys(tokens).length) return;
    try { const r = await api('POST', base(o) + '/theme', {tokens}); o.tokens = Object.assign({}, tk, M(r?.tokens)); toast(S(r?.say) || 'Colours changed.'); reloadFrames(o, true); }
    catch (er) { toast(er.message, true); }
  }
  addEventListener('message', async ev => {
    const d = ev.data, o = P.get(CUR);
    if (!d || d.hoola !== 'edit' || !o || !o.edit || !studio) return;
    if (![...studio.querySelectorAll('[data-pane=frames] iframe')].some(f => f.contentWindow === ev.source)) return;   // only our own preview
    o.editPage = /^[\w\-/]*$/.test(S(d.page)) ? S(d.page) : ''; o.editY = N(d.y);
    const k = S(d.k), e = S(d.e);
    if (d.t === 'text') return editSend(o, {k, e, op: 'text', value: S(d.value)});
    if (d.t === 'remove') { if (confirm(`Remove "${S(d.text).slice(0, 60)}" from the page? (Undo brings it back)`)) editSend(o, {k, e, op: 'remove'}); return; }
    if (d.t === 'link') {
      const f = await dialog('Link', `<label class="sted-c wide"><span>Where should "${esc(S(d.text).slice(0, 40))}" go?</span><input name="href" value="${esc(S(d.href))}" placeholder="https://… · tel:+91… · mailto:… · contact/"></label>`);
      if (f) editSend(o, {k, e, op: 'link', value: S(f.get('href')).trim()}); return;
    }
    if (d.t === 'image') {
      const ph = L(o.photos); if (!ph.length) return toast('No photos yet: send photos in the chat and say which section they are for.', true);
      const f = await dialog('Choose a picture', `<input type="hidden" name="pick" value="${esc(S(d.img))}"><div class="sted-ph">${ph.map(p => `<button type="button" class="btn soft" data-pick="${esc(S(p.name))}" aria-pressed="${S(p.name) === S(d.img)}">${esc(S(p.about) || S(p.name))}${p.ai ? ' · AI' : ''}</button>`).join('')}</div>`);
      if (f && S(f.get('pick')) && S(f.get('pick')) !== S(d.img)) editSend(o, {k, e, op: 'image', value: S(f.get('pick'))}); return;
    }
    if (d.t === 'ai') { const inp = studio.querySelector('#stIn'); if (inp) { inp.value = `"${S(d.text).slice(0, 80)}" ko `; inp.focus(); } }
  });
  function reset() { appEl.classList.remove('st'); P.clear(); CUR = null; showBtn(); if (studio) { studio.innerHTML = ''; delete studio.dataset.k; } }

  /* refresh hooks: a finished part reloads the preview; the "taaza" age ticks */
  function after(kind, p) {
    if (kind === 'app_android') return;
    const o = P.get((kind === 'site_board' ? 'site:' : 'app:') + S(p.id)); if (!o) return;
    const b = M(p.board), done = N(b.done), ver = N(p.version);
    if (o.done !== -1 && (done !== o.done || ver !== o.ver)) reloadFrames(o);
    o.done = done; o.ver = ver;
  }
  setInterval(() => { const o = P.get(CUR); if (o && isOpen() && studio.dataset.k === o.k) { const age = studio.querySelector('.pvage'); if (age) age.textContent = 'taaza · ' + ago(o.loadedAt || Date.now()); } }, 5000);
  if (sbtn) sbtn.addEventListener('click', () => { if (isOpen()) return close(); const o = P.get(CUR) || [...P.values()].sort((a, b) => b.last - a.last)[0]; if (o) open(o.k); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen() && !document.querySelector('.blb')) close(); });

  return {
    kinds: KINDS,
    card(kind, p, el, live) { card(kind, p, el, live); after(kind, p); },
    reset, close, isOpen,
  };
};
