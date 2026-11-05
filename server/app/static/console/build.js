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
  const KINDS = new Set(['site_board', 'app_board', 'app_android', 'site_spec']);   // v0.407 + the Architect's spec card
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
      ${N(c.blanks) ? `<div class="faint bln">${N(c.blanks)} spot(s) still need your details (the […] boxes)</div>` : ''}
      ${L(c.journeys).length ? `<div class="bln faint" style="margin-top:6px">Visitor tests (Hoola used the site like a customer on a phone):</div>${L(c.journeys).map(j => `<div class="${j.ok ? 'okc' : 'badc'} bln">${j.ok ? '✓' : '✗'} ${esc(JOURNEY[S(j.name)] || S(j.name))}${j.ok ? '' : ' - ' + esc(S(j.detail))}</div>`).join('')}` : ''}</section>`;
  }
  const JOURNEY = {menu: 'Phone menu opens and leads to a page', form: 'Enquiry form sends', shop: 'Add to cart → checkout → order',
                   blog: 'Blog post opens', lang: 'Language switch works'};   // v0.400
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
      ? [...pre, ['preview', 'Preview'], ['board', 'Board'], ['kadam', 'Steps'], ['jaanch', 'Checks'], ...(o.v?.version ? [['dash', 'Dashboard'], ['code', 'Code'], ['blog', 'Blog'], ['langs', 'Languages'], ['data', 'App & data'], ['shop', 'Shop']] : [])]
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
    if (framed) frames(o, fr); else { ot.innerHTML = pane(o); hydrate(ot); qr(ot); if (o.tab === 'data') loadData(o, ot); if (o.tab === 'shop') loadShop(o, ot); if (o.tab === 'dash') loadDash(o, ot); if (o.tab === 'blog') loadBlog(o, ot); if (o.tab === 'code') loadCodeMode(o, ot); if (o.tab === 'langs') loadLangs(o, ot); if (o.tab === 'android' && o.type === 'app') { loadStore(o, ot); loadIos(o, ot); loadAppStore(o, ot); loadCode(o, ot); loadMatch(o, ot); loadBhasha(o, ot); } }
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
      case 'shop': return `<div class="stshop"><div class="stempty">${spin()} Loading the shop…</div></div>`;
      case 'dash': return `<div class="stdash"><div class="stempty">${spin()} Loading the dashboard…</div></div>`;
      case 'blog': return `<div class="stblog"><div class="stempty">${spin()} Loading the blog…</div></div>`;
      case 'code': return `<div class="stcode"><div class="stempty">${spin()} Opening the code…</div></div>`;
      case 'langs': return `<div class="stblog"><div class="stempty">${spin()} Loading the languages…</div></div>`;
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
      ${M(q.flows).tapped ? `<div class="bln">${esc(S(M(q.flows).tapped))} buttons tapped: ${L(M(q.flows).crashed).length} crashed, ${L(M(q.flows).dead).length} did nothing${L(M(q.flows).dead).slice(0, 4).map(d => `<div class="faint">• ${esc(S(d.screen))}: "${esc(S(d.label))}" did nothing</div>`).join('')}</div>` : ''}
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

  /* v0.347 BHASHA: the languages her app carries (customers pick on My account), from the next build */
  async function loadBhasha(o, root) {
    const box = root.querySelector('.stbhasha'); if (!box) return;
    let v; try { v = await api('GET', base(o) + '/bhasha'); } catch (er) { return; }
    const on = new Set(L(v.langs)), cov = M(v.coverage);
    box.innerHTML = `<section class="bbox"><h4>App languages${v.words ? ' · ' + esc(S(v.words)) + ' words' : ''}</h4>
      <div class="bln faint">Customers pick the language on My account; the app starts in the first one. Her data (product names, prices) is never translated. Up to 6.</div>
      <div class="bln">${Object.entries(M(v.all)).map(([k, n]) => `<label style="margin-right:12px"><input type="checkbox" data-bh="${esc(k)}" ${on.has(k) ? 'checked' : ''}> ${esc(S(n))}${cov[k] != null ? ' (' + esc(S(cov[k])) + '%)' : ''}</label>`).join('')}</div>
      <div class="acts"><button class="btn soft" type="button" data-bhs="1">Save languages</button></div></section>`;
    box.onclick = async e => { if (!e.target.closest('button[data-bhs]')) return;
      const langs = [...box.querySelectorAll('[data-bh]')].filter(x => x.checked).map(x => x.dataset.bh);
      try { await api('POST', base(o) + '/bhasha', {langs}); toast('Saved: from the next build.'); loadBhasha(o, root); } catch (er) { toast(er.message, true); } };
  }

  /* v0.343 DESIGN SE MILAAN: each real screen beside her approved design, 0-100, Opus's differences, rebuild on her confirm */
  async function loadMatch(o, root, plat) {
    const box = root.querySelector('.stmatch'); if (!box) return;
    plat = plat || box.dataset.plat || 'android'; box.dataset.plat = plat;
    let v; try { v = await api('GET', base(o) + '/match'); } catch (er) { return; }
    const m = M(M(v.match)[plat]), rows = L(m.screens), min = m.min || 70, low = rows.filter(x => x.score < min).length;
    box.innerHTML = `<section class="bbox"><h4>Design match${m.avg != null ? ' · ' + esc(S(m.avg)) + '%' : ''}</h4>
      <div class="acts"><button class="btn ${plat === 'android' ? 'go' : 'soft'}" type="button" data-mt="android">Android</button><button class="btn ${plat === 'ios' ? 'go' : 'soft'}" type="button" data-mt="ios">iPhone</button></div>
      ${rows.length ? `<div class="bln ${low ? 'badc' : ''}">${low ? low + ' screens look different from the approved design.' : 'Every screen matches the approved design.'}</div>`
        : '<div class="bln faint">Shown after a build with the device check.</div>'}
      ${rows.slice(0, 12).map(x => `<div class="bln"><b>${esc(S(x.label))}</b> · ${esc(S(x.score))}%
        <div class="blooks">${x.design ? `<figure>${pic(`${base(o)}/shots/${encodeURIComponent(x.design)}`, 'design')}<figcaption>Design</figcaption></figure>` : ''}<figure>${pic(`${base(o)}/${plat}/qa/${encodeURIComponent(x.id)}`, 'app')}<figcaption>App</figcaption></figure></div>
        ${L(x.differences).map(d => `<div class="faint">• ${esc(S(d))}</div>`).join('')}</div>`).join('')}
      <div class="acts"><button class="btn soft" type="button" data-mt="check">Ask Opus for the differences</button>
        <button class="btn go" type="button" data-mt="fix" ${low ? '' : 'disabled'}>Rebuild those screens</button></div></section>`;
    box.onclick = async e => { const b = e.target.closest('button[data-mt]'); if (!b) return;
      const w = b.dataset.mt;
      if (w === 'android' || w === 'ios') return loadMatch(o, root, w);
      if (w === 'fix' && !confirm('Rebuild only the screens that look different, with the list of differences? The rest of the app stays as it is.')) return;
      try { const r = await api('POST', base(o) + '/match', {platform: plat, fix: w === 'fix'}); toast(S(r.say)); loadMatch(o, root, plat); } catch (er) { toast(er.message, true); } };
  }

  /* v0.342 her app's code in HER GitHub: the button makes the card in the chat; her tap on that card pushes */
  async function loadCode(o, root) {
    const box = root.querySelector('.stcode'); if (!box) return;
    let v; try { v = await api('GET', base(o) + '/github'); } catch (er) { return; }
    box.innerHTML = `<section class="bbox"><h4>Code in your GitHub${L(v.commits).length ? ' · ' + L(v.commits).length + ' commits' : ''}</h4>
      <div class="bln faint">The whole Android + iPhone code, one new commit per build, with a README and a changelog. Signing keys never go. You confirm before anything is sent.</div>
      ${v.linked ? '' : '<div class="bln badc">Link your GitHub token first (Website > Hosting, typed in the app only).</div>'}
      <label class="bln"><input type="checkbox" data-cd="private" checked> Private repo</label>
      <div class="acts"><button class="btn soft" type="button" data-cd="go" ${v.linked && v.ready ? '' : 'disabled'}>Send code to GitHub</button></div>
      ${L(v.commits).slice(0, 3).map(x => `<div class="bln faint">✓ build ${esc(S(x.build))} · ${esc(S(x.repo))} · ${esc(S(x.at).slice(0, 10))}</div>`).join('')}</section>`;
    box.onclick = async e => { const b = e.target.closest('button[data-cd="go"]'); if (!b) return;
      try {
        const card = await api('POST', base(o) + '/github', {private: box.querySelector('[data-cd="private"]').checked});
        if (!confirm(`Send ${card.files} files (build ${card.version}) to ${card.private ? 'PRIVATE' : 'PUBLIC'} repo ${card.repo} on your GitHub? Signing keys never go.`)) { toast('Not sent.'); return; }
        const done = await api('POST', '/api/sites-github/' + encodeURIComponent(card.id) + '/push', {hash: card.hash});
        toast('Sent: ' + S(done.url)); loadCode(o, root);
      } catch (er) { toast(er.message, true); } };
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
      ${qaBox(o)}${historyBox(o)}<div class="ststore"></div><div class="stios"></div><div class="stappstore"></div><div class="stbhasha"></div><div class="stmatch"></div><div class="stcode"></div>
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
          if (r) { o.edit = true; o.photos = L(r.photos); o.media = L(r.media); o.tokens = M(r.tokens); o.editPage = ''; o.editY = 0; o.framesFor = ''; draw(); toast('Edit mode: click any words on the page and type. Free, no AI.'); }
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
  /* v0.407 ABHI ABHI: her app data page is live - a new order / a status change / a chat shows without a reload, and who is
     online right now. One stream per open page (closed when she leaves it); while she is typing in a form on the page the
     update waits behind a "Show" button so nothing she is filling is wiped. */
  async function liveApp(o, box) {
    if (box._live) box._live.abort();
    const ctl = new AbortController(); box._live = ctl;
    const line = box.querySelector('.stlive');
    const people = new Map();
    let fresh = 0, timer = 0, gotEvent = false;
    const draw = () => {
      if (!line) return;
      const names = [...people.values()];
      line.hidden = false;
      line.innerHTML = `<span class="stdot" aria-hidden="true"></span>Live${names.length ? ' · Online: ' + names.map(n => esc(n)).join(', ') : ''}${fresh ? ` · ${fresh} new change${fresh > 1 ? 's' : ''} <button class="ib" type="button" data-livego>Show</button>` : ''}`;
      const b = line.querySelector('[data-livego]'); if (b) b.onclick = () => { ctl.abort(); loadAppData(o, box); };
    };
    const changed = () => {
      fresh++; clearTimeout(timer);
      timer = setTimeout(() => {
        if (!box.isConnected) return ctl.abort();
        if (box.contains(document.activeElement) && /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) return draw();
        ctl.abort(); loadAppData(o, box);
      }, 600);
      draw();
    };
    try { for (const p of L((await api('GET', base(o) + '/live/presence')).online)) people.set(S(p.member), S(p.name)); } catch (er) { /* older server */ }
    try {
      const res = await api('GET', base(o) + '/live', undefined, {raw: true, signal: ctl.signal});
      const rd = res.body.getReader(), dec = new TextDecoder(); let buf = '';
      draw();
      for (;;) {
        const {value, done} = await rd.read(); if (done) break;
        if (!box.isConnected) { ctl.abort(); break; }
        buf += dec.decode(value, {stream: true});
        let i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, i); buf = buf.slice(i + 2);
          const data = block.split('\n').filter(x => x.startsWith('data: ')).map(x => x.slice(6)).join('\n'); if (!data) continue;
          let e; try { e = JSON.parse(data); } catch { continue; }
          if (e.type === 'pos') { box.dispatchEvent(new CustomEvent('hoolapos', {detail: e})); continue; }   // v0.412 a rider moved
          if (e.type === 'row' || e.type === 'chat') { gotEvent = true; changed(); }
          else if (e.type === 'presence') { if (e.online) people.set(S(e.member), S(e.name)); else people.delete(S(e.member)); draw(); }
          else if (e.type === 'reset') changed();
        }
      }
      if (box.isConnected && !ctl.signal.aborted) setTimeout(() => { if (box.isConnected && box._live === ctl) liveApp(o, box); }, gotEvent ? 1000 : 3000);
    } catch (er) {
      if (!ctl.signal.aborted && box.isConnected && line) { line.hidden = true; setTimeout(() => { if (box.isConnected && box._live === ctl) liveApp(o, box); }, 30000); }
    }
  }
  /* v0.412 the riders map: MapLibre (vendored on her server) + OpenFreeMap tiles, no key. Moves with the live stream's
     "pos" events (liveApp re-sends them on the data box). */
  function mapLib() {
    if (window.maplibregl) return Promise.resolve();
    if (mapLib._p) return mapLib._p;
    mapLib._p = new Promise((ok, bad) => {
      const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = '/static/vendor/maplibre/maplibre-gl.css'; document.head.appendChild(css);
      const s = document.createElement('script'); s.src = '/static/vendor/maplibre/maplibre-gl.js'; s.onload = ok; s.onerror = () => { mapLib._p = null; bad(new Error('map')); };
      document.head.appendChild(s);
    });
    return mapLib._p;
  }
  async function ridersMap(el, riders) {
    try { await mapLib(); } catch { el.innerHTML = '<p class="stempty">The map could not load.</p>'; return; }
    const map = new maplibregl.Map({container: el, style: 'https://tiles.openfreemap.org/styles/liberty', center: [78.96, 22.6], zoom: 4, attributionControl: {compact: true}});
    const marks = new Map();
    const put = (id, name, lat, lng) => {
      if (typeof lat !== 'number' || typeof lng !== 'number') return;
      let m = marks.get(id);
      if (!m) { const d = document.createElement('div'); d.className = 'strider'; d.title = name; m = new maplibregl.Marker({element: d}).setLngLat([lng, lat]).setPopup(new maplibregl.Popup({offset: 12}).setText(name)).addTo(map); marks.set(id, m); }
      else m.setLngLat([lng, lat]);
    };
    riders.forEach(r => put(S(r.member), S(r.name), r.lat, r.lng));
    const fit = () => { if (!marks.size) return; const b = new maplibregl.LngLatBounds(); marks.forEach(m => b.extend(m.getLngLat())); map.fitBounds(b, {padding: 48, maxZoom: 15, duration: 0}); };
    map.on('load', fit);
    const box = el.closest('.stcols') ? el.closest('.stcols').parentNode : el.parentNode.parentNode;
    const on = e => { const p = e.detail; if (!el.isConnected) return box.removeEventListener('hoolapos', on); if (p.off) { const m = marks.get(S(p.member)); if (m) { m.remove(); marks.delete(S(p.member)); } } else put(S(p.member), S(p.name), p.lat, p.lng); };
    box.addEventListener('hoolapos', on);
  }
  async function loadAppData(o, box) {
    let info;
    try { info = await api('GET', base(o) + '/data'); } catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const cols = L(info.collections), counts = M(info.counts);
    box.innerHTML = `<p class="stnote">${info.live ? 'People using your app order / book here; every new entry also reaches your chat.' : 'Real orders and bookings appear here once the Android app is built.'}</p>
      <p class="stnote">${N(counts.members)} accounts · ${cols.map(c => `${esc(S(c.label))}: ${N(counts[c.key])}`).join(' · ')}</p><p class="stlive" hidden></p><div class="stcols"></div><div class="stmem"></div>`;
    if (info.live) liveApp(o, box);
    const cbox = box.querySelector('.stcols');
    let staff = [];                // v0.352 KAAM BAANTO: her staff accounts for "With" on every row
    try { staff = L((await api('GET', base(o) + '/members')).members).filter(m => ['staff', 'admin'].includes(S(m.role))); } catch (er) { /* none */ }
    const withCell = r => staff.length ? `<td><select data-f="assign" aria-label="With"><option value="">Nobody</option>${staff.map(m => `<option value="${esc(S(m.id))}"${S(m.id) === S(r.assigned_to) ? ' selected' : ''}>${esc(S(m.name) || S(m.email))}</option>`).join('')}</select></td>` : '';
    for (const c of cols) {
      let rows = [];
      try { rows = L((await api('GET', `${base(o)}/data/${encodeURIComponent(c.key)}`)).rows); } catch (er) { toast(er.message, true); }
      const fields = L(c.fields);
      const sec = document.createElement('section'); sec.className = 'stcol';
      sec.innerHTML = `<h4>${esc(S(c.label))} <span>${rows.length}</span></h4>` + (rows.length ? `<div class="sttbl"><table><thead><tr>${fields.map(f => `<th>${esc(S(f.label))}</th>`).join('')}${staff.length ? '<th>With</th>' : ''}${rows.some(r => r.rating) ? '<th>Rating</th>' : ''}${rows.some(r => r.receipt) ? '<th>Receipt</th>' : ''}<th>When</th></tr></thead><tbody>${rows.map(r => `<tr data-r="${esc(S(r.id))}">${fields.map(f => {
        const v = r[f.key];
        if ((f.key === 'status' || f.key === 'paid') && f.type === 'choice') return `<td><select data-f="${f.key}" aria-label="${esc(S(f.label))}">${L(f.options).map(op => `<option${S(op) === S(v) ? ' selected' : ''}>${esc(S(op))}</option>`).join('')}</select></td>`;
        if (f.type === 'photo') return `<td>${/^f_[0-9a-f]{16}$/.test(S(v)) ? pic(`${base(o)}/files/${S(v)}`, S(f.label), 'stphoto') : ''}</td>`;   // v0.319
        if (f.type === 'location' && S(v)) return `<td><a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(S(v))}" target="_blank" rel="noopener">${esc(S(v))}</a></td>`;
        return `<td>${esc(f.type === 'yes_no' ? (v ? 'Yes' : 'No') : S(v)).replace(/\n/g, '<br>')}</td>`;
      }).join('')}${withCell(r)}${rows.some(x => x.rating) ? `<td>${r.rating ? esc('★'.repeat(N(r.rating)) + ' ' + N(r.rating) + '/5' + (S(r.rating_note) ? ' · ' + S(r.rating_note) : '')) : ''}</td>` : ''}${rows.some(x => x.receipt) ? `<td>${r.receipt ? `<button class="ib" type="button" data-receipt>${r.receipt_kind === 'credit_note' ? 'Credit note' : r.receipt_kind === 'invoice' ? 'Invoice' : 'PDF'}</button>` : ''}${r.receipt_kind === 'credit_note' ? ' <button class="ib" type="button" data-receipt="invoice">Invoice</button>' : ''}${r.receipt_kind === 'invoice' ? ' <button class="ib" type="button" data-cn>Credit note…</button>' : ''}</td>` : ''}<td>${esc(S(r.created).slice(0, 16).replace('T', ' '))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No entries yet.</p>');
      sec.addEventListener('change', async e => {
        const sl = e.target.closest('select[data-f]'), tr = e.target.closest('tr[data-r]'); if (!sl || !tr) return;
        try { await api('PATCH', `${base(o)}/data/${encodeURIComponent(c.key)}/${encodeURIComponent(tr.dataset.r)}`, {[sl.dataset.f]: sl.value}); toast(sl.dataset.f === 'assign' ? (sl.value ? 'Given to ' + sl.selectedOptions[0].textContent + '.' : 'Taken back.') : 'Saved.'); }
        catch (er) { toast(er.message, true); }
      });
      sec.addEventListener('click', async e => {     // v0.356 WAPSI: her credit note for an invoiced row (a return / wrong bill)
        const b = e.target.closest('[data-cn]'), tr = e.target.closest('tr[data-r]'); if (!b || !tr) return;
        const why = prompt('Credit note for the full invoice value. Reason (e.g. goods returned):', 'Goods returned'); if (why === null) return;
        try { const v = await api('POST', `${base(o)}/data/${encodeURIComponent(c.key)}/${encodeURIComponent(tr.dataset.r)}/credit-note`, {reason: why}); toast('Credit note ' + S(v.credit_note) + ' made. Any refund is yours to make.'); }
        catch (er) { toast(er.message, true); }
      });
      sec.addEventListener('click', async e => {     // v0.354 RASEED: her copy of a finished row's receipt
        const b = e.target.closest('[data-receipt]'), tr = e.target.closest('tr[data-r]'); if (!b || !tr) return;
        b.disabled = true;
        try {
          const res = await api('GET', `${base(o)}/data/${encodeURIComponent(c.key)}/${encodeURIComponent(tr.dataset.r)}/receipt${b.dataset.receipt === 'invoice' ? '?doc=invoice' : ''}`, undefined, {raw: true});
          const a = document.createElement('a'); a.href = URL.createObjectURL(await res.blob()); a.download = 'receipt.pdf'; a.click();
          setTimeout(() => URL.revokeObjectURL(a.href), 30000);
        } catch (er) { toast(er.message, true); } finally { b.disabled = false; }
      });
      cbox.appendChild(sec);
      hydrate(sec);              // v0.319 photos load with her login
    }
    // v0.412 NAKSHA LIVE: her tracking switch (which list, which statuses mean "on the way") + every rider on shift, live
    const trbox = document.createElement('section'); trbox.className = 'stcol sttrack'; box.appendChild(trbox);
    const drawTrack = tr => {
      const lists = L(tr.lists).filter(x => L(x.statuses).length), cur = lists.find(x => S(x.key) === S(tr.coll)) || lists[0];
      if (!cur) { trbox.remove(); return; }
      trbox.innerHTML = `<h4>Live tracking <span>${tr.on ? 'On' : 'Off'}</span></h4>
        <p class="stnote">Staff tap Start shift in the app; their location is shared only during the shift. A customer sees only the rider bringing her order, only while it is on its way. A new app build adds the shift button and the maps.</p>
        <form class="stapp" autocomplete="off"><div class="row"><label>List <select name="coll">${lists.map(x => `<option value="${esc(S(x.key))}"${x === cur ? ' selected' : ''}>${esc(S(x.label))}</option>`).join('')}</select></label>
        <span class="stnote">On the way when the status is:</span>${L(cur.statuses).map(s => `<label class="chk"><input type="checkbox" name="st" value="${esc(S(s))}"${L(tr.statuses).includes(s) ? ' checked' : ''}> ${esc(S(s))}</label>`).join('')}</div>
        ${cur.location ? '' : '<p class="stnote">This list has no location field, so the map shows the rider but not the customer\'s place.</p>'}
        <div class="row"><button class="btn go" type="submit" data-on="1">${tr.on ? 'Save' : 'Turn on tracking'}</button>${tr.on ? '<button class="btn" type="submit" data-on="0">Turn off</button>' : ''}</div></form>
        ${tr.on ? `<p class="stnote">${L(tr.riders).length ? L(tr.riders).length + ' on shift now' : 'Nobody is on shift right now.'}</p><div class="stmap" role="img" aria-label="Riders on shift"></div>` : ''}`;
      const f = trbox.querySelector('form');
      f.coll.addEventListener('change', () => drawTrack({...tr, coll: f.coll.value, statuses: []}));
      f.addEventListener('submit', async e => {
        e.preventDefault(); const on = e.submitter ? e.submitter.dataset.on === '1' : true;
        const st = [...f.querySelectorAll('input[name=st]:checked')].map(x => x.value);
        try { const v = await api('PUT', base(o) + '/track', {on, coll: f.coll.value, statuses: st}); drawTrack({...tr, ...v}); toast(on ? 'Live tracking is on. Build the app again to add it to phones.' : 'Live tracking is off.'); }
        catch (er) { toast(er.message, true); }
      });
      const el = trbox.querySelector('.stmap'); if (el) ridersMap(el, L(tr.riders));
    };
    try { drawTrack(await api('GET', base(o) + '/track')); } catch (er) { trbox.remove(); }
    // v0.455 SURAKSHIT LOGIN + SURAKSHA GATE: the ways into her app, the permissions matrix, and the security check
    const sgbox = document.createElement('section'); sgbox.className = 'stcol stsign'; box.appendChild(sgbox);
    const drawSign = sg => {
      const ways = L(sg.ways), ids = sg.ids || {}, probs = sg.problems || {}, g = sg.gate || {};
      const WAYS = [['email_password', 'Email + password'], ['phone_otp', 'Mobile number + OTP'], ['google', 'Sign in with Google'], ['apple', 'Sign in with Apple']];
      const IDS = [['google_web_client_id', 'Google WEB client id (Android uses this one)'], ['google_ios_client_id', 'Google iOS client id'],
                   ['apple_bundle_id', "Apple: the app's bundle id"], ['apple_service_id', 'Apple Services ID (web / Android)']];
      sgbox.innerHTML = `<h4>Login &amp; security <span>${ways.length} way${ways.length === 1 ? '' : 's'}${g.ok === false ? ' · check failed' : ''}</span></h4>
        <p class="stnote">How the people of your app sign in. The code or token is always checked on the server - never by the phone. You never need a client SECRET here: native sign-in does not use one.</p>
        <form class="stapp sgset" autocomplete="off">
          <div>${WAYS.map(([k, lbl]) => `<label class="stchk"><input type="checkbox" name="way" value="${k}"${ways.includes(k) ? ' checked' : ''}> ${esc(lbl)}</label>`).join(' ')}</div>
          ${IDS.map(([k, lbl]) => `<div class="row"><label class="stnote" style="flex:1">${esc(lbl)}<input name="${k}" value="${esc(S(ids[k]))}" maxlength="200" placeholder="(not set)"></label></div>`).join('')}
          <label class="stchk"><input type="checkbox" name="staff_2fa"${sg.staff_2fa ? ' checked' : ''}> Every staff account must keep the authenticator second step</label>
          <div class="row"><button class="btn go" type="submit">Save</button><span class="stnote">${sg.otp_ready ? 'SMS provider is set up.' : 'Mobile OTP also needs a DLT-registered SMS template on the server.'}</span></div>
        </form>
        ${Object.values(probs).map(v => `<p class="stnote">${esc(S(v))}</p>`).join('')}
        <h5>Security check</h5>
        <p class="stnote">Runs on the newest build: keys inside the app, permissions, release settings, library CVEs (OSV.dev), login and data rules. A failing check blocks the store upload.</p>
        ${g.at ? `<p class="stnote">${esc(S(g.platform))} build ${esc(S(g.build))}: <b>${g.ok ? 'passed' : g.fail + ' failed'}</b> · ${Number(g.pass) || 0} pass, ${Number(g.warn) || 0} warn, ${Number(g.not_checked) || 0} not checked${L(g.blocks).length ? '<br>' + L(g.blocks).map(x => esc(S(x))).join('<br>') : ''}</p>` : '<p class="stempty">Not run yet.</p>'}
        <div class="row"><button class="btn" type="button" data-sgrun="android">Check the Android build</button><button class="btn" type="button" data-sgrun="ios">Check the iPhone build</button></div>
        <div data-sgout></div>
        ${L(sg.matrix).length ? `<h5>Who may do what</h5><div class="tw"><table><thead><tr><th>List</th><th>Add</th><th>See</th><th>Change</th><th>Delete</th><th>Staff-only fields</th></tr></thead><tbody>${L(sg.matrix).map(m => `<tr><td>${esc(S(m.label || m.list))}</td><td>${esc(S(m.create))}</td><td>${esc(S(m.read))}</td><td>${esc(S(m.update))}</td><td>${esc(S(m.delete))}</td><td>${esc([...(m.staff_set || []), ...(m.staff_see || [])].join(', '))}</td></tr>`).join('')}</tbody></table></div>` : ''}
        ${L(sg.audit).length ? `<h5>Who changed what</h5><ul class="stlines">${L(sg.audit).slice(0, 12).map(x => `<li>${esc(S(x.at || '').slice(0, 16).replace('T', ' '))} · ${esc(S(x.by))} · ${esc(S(x.op))} ${esc(S(x.list))}${L(x.fields).length ? ' (' + esc(L(x.fields).join(', ')) + ')' : ''}</li>`).join('')}</ul>` : ''}`;
      const f = sgbox.querySelector('.sgset');
      f.addEventListener('submit', async e => {
        e.preventDefault();
        const picked = [...f.querySelectorAll('input[name=way]:checked')].map(x => x.value);
        const idv = {}; IDS.forEach(([k]) => { idv[k] = f[k].value.trim(); });
        try { drawSign({...sg, ...(await api('PUT', base(o) + '/sign', {ways: picked, ids: idv, staff_2fa: f.staff_2fa.checked}))}); toast('Saved. The next build carries it.'); }
        catch (er) { toast(er.message, true); }
      });
      sgbox.querySelectorAll('[data-sgrun]').forEach(b => b.addEventListener('click', async () => {
        const out = sgbox.querySelector('[data-sgout]');
        out.textContent = 'Checking…';
        try {
          const v = await api('POST', base(o) + '/security/check', {platform: b.dataset.sgrun});
          out.innerHTML = `<p class="stnote"><b>${v.ok ? 'Passed' : v.fail + ' failed'}</b> · ${v.pass} pass, ${v.warn} warn, ${v.not_checked} not checked</p>
            <ul class="stlines">${L(v.rows).map(x => `<li><b>${esc(S(x.state))}</b> · ${esc(S(x.check))}: ${esc(S(x.say))}</li>`).join('')}</ul>`;
        } catch (er) { out.textContent = er.message; }
      }));
    };
    try { drawSign(await api('GET', base(o) + '/sign')); } catch (er) { sgbox.remove(); }
    // v0.435 PARIVAAR: the apps on this business (customer / delivery partner / partner shop / staff) + partners + web admin
    const fmbox = document.createElement('section'); fmbox.className = 'stcol stfam'; box.appendChild(fmbox);
    const drawFam = fm => {
      const st = fm.settings || {}, rd = st.rider || {}, vd = st.vendor || {}, opts = L(st.statuses);
      const have = new Set(L(fm.faces).map(f => f.kind));
      const chk = (name, on) => opts.map(x => `<label class="stchk"><input type="checkbox" name="${name}" value="${esc(x)}"${L(on).includes(x) ? ' checked' : ''}> ${esc(x)}</label>`).join(' ');
      const waiting = L(fm.partners).filter(p => p.state === 'waiting').length;
      fmbox.innerHTML = `<h4>App family <span>${L(fm.faces).length} app${L(fm.faces).length === 1 ? '' : 's'}${waiting ? ' · ' + waiting + ' waiting' : ''}</span></h4>
        <p class="stnote">More apps on the SAME data: a delivery partner app, a partner shop (restaurant / seller) app, a staff app. Each gets its own plan, design and builds; accounts, orders and rules stay one. Partners apply from their app and only you (or an app admin) approve them.</p>
        <ul class="stlines">${L(fm.faces).map(f => `<li><b>${esc(S(f.name || f.number))}</b> <span class="stnote">${esc(f.kind === 'main' ? 'Main app' : S(f.label))} · ${esc(S(f.number))} · ${esc(S(f.status))}${f.android ? ' · Android ' + esc(S(f.android)) : ''}</span></li>`).join('')}</ul>
        <div class="row">${['rider', 'vendor', 'staff'].filter(k => !have.has(k)).map(k => `<button class="btn" type="button" data-fmadd="${k}"${fm.problems && fm.problems[k] ? ' title="' + esc(S(fm.problems[k])) + '"' : ''}>Add ${esc(S((fm.kinds || {})[k] || k))}</button>`).join('')}</div>
        ${Object.entries(fm.problems || {}).filter(([k, v]) => v && !have.has(k)).map(([k, v]) => `<p class="stnote">${esc(S((fm.kinds || {})[k]))}: ${esc(S(v))}</p>`).join('')}
        ${fm.admin_url ? `<p class="stnote">Web admin for your staff: <a href="${esc(S(fm.admin_url))}" target="_blank" rel="noopener noreferrer">${esc(S(fm.admin_url))}</a></p>` : `<p class="stnote">${esc(S(fm.admin_note))}</p>`}
        ${opts.length ? `<form class="stapp fmset" autocomplete="off"><p class="stnote">Work list: <b>${esc(S(st.jobs))}</b>. Riders see these as new jobs:</p><div>${chk('offer', rd.offer)}</div>
          <p class="stnote">Rider steps:</p><div>${chk('rsteps', rd.steps)}</div>
          <p class="stnote">Partner shop steps${vd.link ? ' (shops = ' + esc(S(vd.link)) + ')' : ''}:</p><div>${chk('vsteps', vd.steps)}</div>
          <div class="row"><label class="stnote">Jobs one rider may hold <input name="max" type="number" min="1" max="20" value="${Number(rd.max) || 3}" style="width:5em"></label><button class="btn go" type="submit">Save rules</button></div></form>` : ''}
        <h5>Partners</h5>
        ${L(fm.partners).map(p => `<div class="cnact" data-p="${esc(S(p.id))}" data-k="${esc(S(p.kind))}"><b>${esc(S(p.name))}</b> <span class="stnote">${esc(S(p.label))} · ${esc(S(p.state))}${p.link_name ? ' · ' + esc(S(p.link_name)) : ''}</span>
          <div class="row">${p.state !== 'approved' ? '<button class="btn go" type="button" data-pok>Approve</button>' : ''}${p.state === 'waiting' ? '<button class="btn" type="button" data-pno>Refuse</button>' : ''}${p.state === 'approved' ? '<button class="btn" type="button" data-px>Remove</button>' : ''}</div></div>`).join('') || '<p class="stempty">No partner has applied yet.</p>'}`;
      const f = fmbox.querySelector('.fmset');
      if (f) f.addEventListener('submit', async e => {
        e.preventDefault();
        const pick = n => [...f.querySelectorAll(`input[name=${n}]:checked`)].map(x => x.value);
        try { await api('PUT', base(o) + '/family/settings', {rider: {offer: pick('offer'), steps: pick('rsteps'), max: Number(f.max.value) || 3}, vendor: {steps: pick('vsteps')}}); drawFam(await api('GET', base(o) + '/family')); toast('Saved.'); }
        catch (er) { toast(er.message, true); }
      });
    };
    fmbox.addEventListener('click', async e => {
      const add = e.target.closest('[data-fmadd]');
      try {
        if (add) {
          const words = prompt('Anything special for this app? (optional)', ''); if (words === null) return;
          const v = await api('POST', base(o) + '/family/face', {kind: add.dataset.fmadd, words});
          toast(S(v.say) || 'Planned.'); drawFam(await api('GET', base(o) + '/family')); return;
        }
        const it = e.target.closest('.cnact'); if (!it) return;
        const pid = it.dataset.p;
        if (e.target.closest('[data-pok]')) {
          let link_row = '';
          if (it.dataset.k === 'vendor') {
            const shops = (await api('GET', base(o) + '/data/' + encodeURIComponent((((await api('GET', base(o) + '/family')).settings || {}).vendor || {}).link || ''))).rows || [];
            const pickd = prompt('Which shop is this partner? Type its number:\n' + shops.slice(0, 40).map((x, i) => `${i + 1}. ${S(x.name || x.title || x.id)}`).join('\n'), '');
            if (pickd === null) return; const sh = shops[Number(pickd) - 1]; if (!sh) { toast('Pick a shop number from the list.', true); return; }
            link_row = sh.id;
          }
          await api('POST', `${base(o)}/family/partners/${encodeURIComponent(pid)}`, {action: 'approve', link_row});
        }
        if (e.target.closest('[data-pno]')) await api('POST', `${base(o)}/family/partners/${encodeURIComponent(pid)}`, {action: 'refuse'});
        if (e.target.closest('[data-px]')) { if (!confirm('Remove this partner? They are signed out and their open jobs go back to the pool.')) return; await api('POST', `${base(o)}/family/partners/${encodeURIComponent(pid)}`, {action: 'remove'}); }
        if (e.target.closest('[data-pok],[data-pno],[data-px]')) drawFam(await api('GET', base(o) + '/family'));
      } catch (er) { toast(er.message, true); }
    });
    try { drawFam(await api('GET', base(o) + '/family')); } catch (er) { fmbox.remove(); }
    // v0.425 RANG: custom native components (Kotlin + Swift) - house rules checked in code, her approval, proved by the next build
    const ccbox = document.createElement('section'); ccbox.className = 'stcol stcomp'; box.appendChild(ccbox);
    const drawComp = cc => {
      ccbox.innerHTML = `<h4>Custom components <span>${L(cc.components).filter(x => x.approved).length} approved</span></h4>
        <p class="stnote">When no ready piece fits, describe it and Hoola writes one native component for Android and iPhone. It is UI only (no internet, files or web views - checked by code). It goes into the app only after you approve it; the next build compiles it and opens it on the device check, and one that fails is left out of that build.</p>
        <form class="stapp ccnew" autocomplete="off"><div class="row"><input name="words" maxlength="800" placeholder="e.g. a horizontal bar per star level showing how many ratings" aria-label="Describe the component"><button class="btn go" type="submit">Write it</button></div></form>
        ${L(cc.components).map(x => `<div class="cnact" data-n="${esc(S(x.name))}"><b>${esc(S(x.name))}</b> <span class="stnote">${esc(S(x.status))}${x.approved ? ' · approved' : ''}</span>
          <p class="stnote">${esc(S(x.purpose))} · ${esc(S(x.params))}${x.error ? '<br>Build said: ' + esc(S(x.error).slice(0, 300)) : ''}</p>
          <details><summary>Code</summary><pre class="ccode">${esc(S(x.kotlin))}</pre><pre class="ccode">${esc(S(x.swift))}</pre></details>
          <div class="row">${x.approved ? '' : '<button class="btn go" type="button" data-ccok>Approve</button>'}<button class="btn" type="button" data-ccx>Remove</button></div></div>`).join('') || '<p class="stempty">None yet.</p>'}`;
      const f = ccbox.querySelector('.ccnew');
      f.addEventListener('submit', async e => { e.preventDefault(); const b = f.querySelector('button'); b.disabled = true; b.textContent = 'Writing…';
        try { await api('POST', base(o) + '/components/draft', {words: f.words.value}); drawComp(await api('GET', base(o) + '/components')); toast('Drafted - read it and approve.'); }
        catch (er) { toast(er.message, true); b.disabled = false; b.textContent = 'Write it'; } });
      ccbox.addEventListener('click', async e => {
        const it = e.target.closest('.cnact'), n = it && it.dataset.n;
        try {
          if (e.target.closest('[data-ccok]')) { if (!confirm('Approve ' + n + '? It goes into the next build of the app.')) return; await api('POST', `${base(o)}/components/${encodeURIComponent(n)}/approve`, {her_tap: true}); drawComp(await api('GET', base(o) + '/components')); }
          if (e.target.closest('[data-ccx]')) { if (!confirm('Remove ' + n + '?')) return; drawComp(await api('DELETE', `${base(o)}/components/${encodeURIComponent(n)}`)); }
        } catch (er) { toast(er.message, true); }
      });
    };
    try { drawComp(await api('GET', base(o) + '/components')); } catch (er) { ccbox.remove(); }
    // v0.424 JODO: connectors - ready packs or her own declared action; each needs HER approval; secrets never shown again
    const cnbox = document.createElement('section'); cnbox.className = 'stcol stconn'; box.appendChild(cnbox);
    const drawConn = cn => {
      const packs = L(cn.packs);
      cnbox.innerHTML = `<h4>Connectors <span>${L(cn.actions).filter(a => a.approved).length} on</span></h4>
        <p class="stnote">Your app talks to your courier, SMS, WhatsApp, e-mail, Google Sheets / Calendar, Zoho / QuickBooks or KYC provider with YOUR keys. Nothing runs until you approve it, and any change needs approving again. Keys are locked away and never shown again.</p>
        <form class="stapp cnpack" autocomplete="off"><div class="row"><label>Add <select name="pack">${packs.map(p => `<option value="${esc(S(p.key))}">${esc(S(p.group))}: ${esc(S(p.label))}</option>`).join('')}</select></label></div><div class="cnf"></div>
          <div class="row"><button class="btn go" type="submit">Add pack</button></div></form>
        ${L(cn.actions).map(a => { const lv = M(a.leaves); return `<div class="cnact" data-k="${esc(S(a.key))}"><b>${esc(S(a.label))}</b> <span class="stnote">${a.approved ? 'Approved' : 'Waiting for your approval'}</span>
          <p class="stnote">${esc(S(lv.method))} to <b>${esc(S(lv.host))}</b> · when: ${esc(S(lv.when))} · sends: ${esc(L(lv.fields).join(', ') || 'no customer data')} · keys used: ${esc(L(lv.secrets).join(', ') || 'none')}${L(lv.writes_back).length ? ' · writes back: ' + esc(L(lv.writes_back).join(', ')) : ''}${a.staff ? ' · staff button in the app' : ''}</p>
          <div class="row">${a.approved ? '' : '<button class="btn go" type="button" data-cnok>Approve</button>'}<button class="btn" type="button" data-cnrun>Run on an entry…</button><button class="btn" type="button" data-cnx>Remove</button></div></div>`; }).join('') || '<p class="stempty">No connectors yet.</p>'}
        <h5>Keys</h5><p class="stnote">${L(cn.secrets).map(s => esc(S(s))).join(', ') || 'none'} (values never shown)</p>
        <form class="stapp cnsec" autocomplete="off"><div class="row"><input name="name" placeholder="key name (e.g. hub_token)" aria-label="Key name" spellcheck="false"><input name="value" type="password" placeholder="value" aria-label="Key value" autocomplete="off"><button class="btn" type="submit">Save key</button></div></form>
        <h5>Incoming (webhooks)</h5>${L(cn.hooks).map(h => `<p class="stnote">${esc(S(h.key))} → ${esc(S(h.coll))} · <code>${esc(S(h.url))}</code> · signed ${esc(S(M(h.sig).type))} in ${esc(S(M(h.sig).header))} <button class="ib" type="button" data-hkx="${esc(S(h.key))}">Remove</button></p>`).join('') || '<p class="stempty">None.</p>'}
        <form class="stapp cnhook" autocomplete="off"><div class="row"><input name="key" placeholder="name (e.g. courier)" aria-label="Hook name"><input name="coll" placeholder="list (e.g. orders)" aria-label="List"><input name="match" placeholder="match: field=$.path" aria-label="Match"><input name="set" placeholder="set: status=$.state, note=$.msg" aria-label="Set"><button class="btn" type="submit">Add webhook</button></div></form>
        ${L(cn.runs).length ? `<h5>Last runs</h5><div class="sttbl"><table><thead><tr><th>When</th><th>Action</th><th>Why</th><th>Result</th><th>Note</th></tr></thead><tbody>${L(cn.runs).map(x => `<tr><td>${esc(S(x.at).slice(0, 16).replace('T', ' '))}</td><td>${esc(S(x.action))}</td><td>${esc(S(x.trigger))}</td><td>${esc(S(x.status))}${x.code ? ' ' + N(x.code) : ''}</td><td>${esc(S(x.note))}</td></tr>`).join('')}</tbody></table></div>` : ''}`;
      const pf = cnbox.querySelector('.cnpack'), ff = pf.querySelector('.cnf');
      const fields = () => { const p = packs.find(x => x.key === pf.pack.value) || {};
        ff.innerHTML = `<p class="stnote">${esc(S(p.note))}${L(p.needs_fields).length ? ' Needs these fields on the list: ' + esc(L(p.needs_fields).join(', ')) + '.' : ''} ${esc(S(p.not_verified))}</p>` +
          (p.no_actions ? '' : `<div class="row">${Object.entries(M(p.settings)).map(([k, v]) => `<input name="s_${esc(k)}" value="${esc(S(v))}" placeholder="${esc(k.replace(/_/g, ' '))}" aria-label="${esc(k)}">`).join('')}</div>
          <div class="row">${L(p.secrets).map(k => `<input name="k_${esc(S(k))}" type="password" placeholder="${esc(S(k).replace(/_/g, ' '))}" aria-label="${esc(S(k))}" autocomplete="off">`).join('')}</div>`); };
      pf.pack.addEventListener('change', fields); fields();
      pf.addEventListener('submit', async e => { e.preventDefault(); const settings = {}, secrets = {};
        pf.querySelectorAll('input').forEach(i => { if (i.name.startsWith('s_')) settings[i.name.slice(2)] = i.value.trim(); if (i.name.startsWith('k_') && i.value) secrets[i.name.slice(2)] = i.value; });
        try { const v = await api('POST', base(o) + '/connect/pack', {pack: pf.pack.value, settings, secrets}); drawConn(v); toast(L(v.made).length ? `Added ${L(v.made).length} action(s) - approve each one.` + (L(v.problems).length ? ' Some need list fields first: ' + L(v.problems).join('; ') : '') : (L(v.problems).join('; ') || S(v.note))); }
        catch (er) { toast(er.message, true); } });
      cnbox.addEventListener('click', async e => {
        const act = e.target.closest('.cnact'), k = act && act.dataset.k;
        try {
          if (e.target.closest('[data-cnok]')) { if (!confirm('Approve this connector? It will send exactly what is listed to that address with your key.')) return; drawConn(await api('POST', `${base(o)}/connect/actions/${encodeURIComponent(k)}/approve`, {her_tap: true})); }
          if (e.target.closest('[data-cnrun]')) { const row = prompt('Entry id to run it on (blank = none):', ''); if (row === null) return; const v = await api('POST', `${base(o)}/connect/actions/${encodeURIComponent(k)}/run`, {row: row.trim(), her_tap: true}); toast('Result: ' + S(v.status) + (v.why ? ' - ' + S(v.why) : '')); drawConn(await api('GET', base(o) + '/connect')); }
          if (e.target.closest('[data-cnx]')) { if (!confirm('Remove this connector?')) return; drawConn(await api('DELETE', `${base(o)}/connect/actions/${encodeURIComponent(k)}`)); }
          const hx = e.target.closest('[data-hkx]'); if (hx) { drawConn(await api('DELETE', `${base(o)}/connect/hooks/${encodeURIComponent(hx.dataset.hkx)}`)); }
        } catch (er) { toast(er.message, true); }
      });
      const sf = cnbox.querySelector('.cnsec');
      sf.addEventListener('submit', async e => { e.preventDefault(); try { await api('PUT', `${base(o)}/connect/secrets/${encodeURIComponent(sf.name.value.trim())}`, {value: sf.value.value}); sf.value.value = ''; drawConn(await api('GET', base(o) + '/connect')); toast('Key saved and locked.'); } catch (er) { toast(er.message, true); } });
      const hf = cnbox.querySelector('.cnhook');
      hf.addEventListener('submit', async e => { e.preventDefault();
        const pair = s => { const [k, ...v] = s.split('='); return [k.trim(), v.join('=').trim()]; };
        const set = {}; hf.set.value.split(',').filter(x => x.includes('=')).forEach(x => { const [k, v] = pair(x); set[k] = v; });
        const [mk, mv] = pair(hf.match.value);
        try { const v = await api('PUT', base(o) + '/connect/hooks', {hook: {key: hf.key.value.trim(), coll: hf.coll.value.trim(), match: {[mk]: mv}, set}}); drawConn(v); if (v.new_secret) prompt('Webhook secret - shown only now. Put it in your service (HMAC-SHA256 hex of the body in x-signature):', S(v.new_secret)); }
        catch (er) { toast(er.message, true); } });
    };
    try { drawConn(await api('GET', base(o) + '/connect')); } catch (er) { cnbox.remove(); }
    // v0.419 PAISA: her own gateway (keys typed here, sealed, never shown again), payments + refunds (her tap), links, AutoPay, split
    const pybox = document.createElement('section'); pybox.className = 'stcol stpay'; box.appendChild(pybox);
    const rs = p => 'Rs ' + (N(p) / 100).toLocaleString('en-IN', {maximumFractionDigits: 2});
    const drawPay = py => {
      if (!py.on) {
        const f = py.fields || {};
        pybox.innerHTML = `<h4>Online payments <span>Off</span></h4>
          <p class="stnote">Join YOUR payment gateway. Customers pay on the gateway's own page and the money goes to your bank account; Hoola never holds it. An order is marked paid only when the gateway itself confirms it. Your keys are checked with the gateway, locked away, and never shown again.</p>
          <form class="stapp" autocomplete="off"><div class="row"><label>Gateway <select name="gw">${L(py.gateways).map(g => `<option value="${esc(S(g))}">${esc(S(g).replace(/^./, c => c.toUpperCase()))}</option>`).join('')}</select></label>
          <label class="chk"><input type="checkbox" name="test"> Test mode</label></div><div class="row pyf"></div>
          <div class="row"><button class="btn go" type="submit">Check and join</button></div></form>`;
        const fm = pybox.querySelector('form'), ff = fm.querySelector('.pyf');
        const fields = () => { ff.innerHTML = L(f[fm.gw.value]).map(k => `<input name="${esc(S(k))}" placeholder="${esc(S(k).replace(/_/g, ' '))}" aria-label="${esc(S(k))}" autocomplete="off" spellcheck="false" ${/secret|password/.test(k) ? 'type="password"' : ''}>`).join(''); };
        fm.gw.addEventListener('change', fields); fields();
        fm.addEventListener('submit', async e => {
          e.preventDefault(); const b = fm.querySelector('button.go'); b.disabled = true;
          const keys = {}; ff.querySelectorAll('input').forEach(i => { keys[i.name] = i.value.trim(); });
          try { drawPay(await api('PUT', base(o) + '/pay/keys', {gateway: fm.gw.value, keys, test: fm.test.checked})); toast('Gateway joined. Now add the webhook address shown here in your gateway dashboard.'); }
          catch (er) { toast(er.message, true); b.disabled = false; }
        });
        return;
      }
      const tot = M(py.totals), can = L(py.can);
      pybox.innerHTML = `<h4>Online payments <span>${esc(S(py.gateway))}${py.test ? ' · test' : ''}</span></h4>
        <p class="stnote">Received ${esc(rs(tot.paid))} in ${N(tot.count)} payments · refunded ${esc(rs(tot.refunded))}${N(tot.mismatch) ? ` · <b>${N(tot.mismatch)} amount mismatch to check</b>` : ''}</p>
        <p class="stnote">Webhook address for your gateway: <code>${esc(S(py.webhook_url))}</code><br>${esc(S(py.webhook_how))}</p>
        <div class="row"><button class="btn" type="button" data-pyset>Settlements</button><button class="btn" type="button" data-pyoff>Remove gateway</button></div><div class="pyset"></div>
        ${L(py.payments).length ? `<div class="sttbl"><table><thead><tr><th>When</th><th>What</th><th>Amount</th><th>Status</th><th>Refunded</th><th></th></tr></thead><tbody>${L(py.payments).map(p => `<tr data-p="${esc(S(p.id))}"><td>${esc(S(p.created).slice(0, 16).replace('T', ' '))}</td><td>${esc(S(p.label))}${p.url ? ` <a href="${esc(S(p.url))}" target="_blank" rel="noopener">link</a>` : ''}</td><td>${esc(S(p.amount_rs))}</td><td>${esc(S(p.status))}${p.why ? ' · ' + esc(S(p.why)) : ''}</td><td>${N(p.refunded) ? esc(rs(p.refunded)) : ''}${L(p.refunds).filter(f => ['ambiguous', 'pending', 'sending'].includes(f.status)).map(f => ` <button class="ib" type="button" data-rfchk="${esc(S(f.id))}">Check ${esc(S(f.amount_rs))}</button>`).join('')}</td><td>${p.status === 'paid' && N(p.refunded) < N(p.amount) && can.includes('refund') ? '<button class="ib" type="button" data-rf>Refund…</button>' : ''}</td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No online payments yet.</p>'}
        ${can.includes('links') ? `<form class="stapp pylink" autocomplete="off"><div class="row"><input name="amount" inputmode="decimal" placeholder="Amount (Rs)" aria-label="Amount"><input name="purpose" placeholder="For what (e.g. udhaar)" aria-label="Purpose"><input name="phone" inputmode="tel" placeholder="Customer phone (optional)" aria-label="Phone"><button class="btn go" type="submit">Make payment link</button></div></form>` : ''}
        ${can.includes('subscriptions') ? `<h5>AutoPay plans</h5>${L(py.plans).map(p => `<p class="stnote">${esc(S(p.name))} · ${esc(rs(p.amount))} every ${esc(S(p.period))} × ${N(p.count)} <button class="ib" type="button" data-plx="${esc(S(p.key))}">Stop offering</button></p>`).join('') || '<p class="stempty">No plans.</p>'}
          <form class="stapp pyplan" autocomplete="off"><div class="row"><input name="name" placeholder="Plan name (e.g. Daily milk)" aria-label="Plan name"><input name="amount" inputmode="decimal" placeholder="Amount (Rs)" aria-label="Amount"><select name="period" aria-label="Every"><option value="month">every month</option><option value="week">every week</option><option value="year">every year</option></select><input name="count" inputmode="numeric" placeholder="How many times" aria-label="How many times" value="12"><button class="btn go" type="submit">Add plan</button></div></form>
          ${L(py.subs).filter(x => !['created'].includes(x.status)).map(x => `<p class="stnote">Subscription ${esc(S(x.plan))} · ${esc(S(x.status))} · ${N(x.charges)} charged ${['cancelled', 'completed'].includes(x.status) ? '' : `<button class="ib" type="button" data-subx="${esc(S(x.id))}">Cancel</button>`}</p>`).join('')}` : ''}
        ${can.includes('split') ? `<h5>Vendor payouts${M(py.split).hash ? ' · rule ' + esc(S(M(py.split).hash)) + ' approved' : ''}</h5>
          <p class="stnote">One line per vendor: name, the vendor's account id from your gateway (Razorpay Route linked account / Cashfree vendor id), percent of each order. The rest stays with you.</p>
          <form class="stapp pysplit"><textarea name="lines" rows="3" aria-label="Vendor lines" placeholder="Kisan Dairy, acc_ABC123, 20">${esc(L(M(py.split).rules).map(x => { const v = L(M(py.split).vendors).find(v => v.key === x.vendor) || {}; return `${S(v.name)}, ${S(v.account)}, ${x.percent}`; }).join('\n'))}</textarea>
          <div class="row"><button class="btn go" type="submit">Approve this payout rule</button></div></form>` : ''}`;
      const reload = async () => drawPay(await api('GET', base(o) + '/pay'));
      pybox.querySelector('[data-pyoff]').onclick = async () => { if (!confirm('Remove the gateway? Online payment stops in the app; past payments stay.')) return; try { drawPay(await api('DELETE', base(o) + '/pay/keys')); } catch (er) { toast(er.message, true); } };
      pybox.querySelector('[data-pyset]').onclick = async () => {
        const bx = pybox.querySelector('.pyset');
        try { const s = await api('GET', base(o) + '/pay/settlements'); bx.innerHTML = L(s.settlements).length ? `<div class="sttbl"><table><thead><tr><th>Settlement</th><th>Amount</th><th>Fees + tax</th><th>Status</th><th>UTR</th></tr></thead><tbody>${L(s.settlements).map(x => `<tr><td>${esc(S(x.id))}</td><td>${esc(rs(x.amount))}</td><td>${esc(rs(N(x.fees) + N(x.tax)))}</td><td>${esc(S(x.status))}</td><td>${esc(S(x.utr))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No settlements.</p>'; }
        catch (er) { bx.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; }
      };
      pybox.addEventListener('click', async e => {
        const rf = e.target.closest('[data-rf]'), chk = e.target.closest('[data-rfchk]'), plx = e.target.closest('[data-plx]'), sx = e.target.closest('[data-subx]');
        try {
          if (rf) { const tr = rf.closest('tr[data-p]'); const amt = prompt('Refund amount in Rs (blank = everything not yet refunded):', ''); if (amt === null) return;
            const v = await api('POST', `${base(o)}/pay/${encodeURIComponent(tr.dataset.p)}/refund`, {amount: amt.trim() || null, her_tap: true}); toast(S(v.say)); await reload(); }
          if (chk) { const v = await api('POST', `${base(o)}/pay/refunds/${encodeURIComponent(chk.dataset.rfchk)}/check`); toast('Refund: ' + S(v.status)); await reload(); }
          if (plx) { drawPay(await api('DELETE', `${base(o)}/pay/plans/${encodeURIComponent(plx.dataset.plx)}`)); }
          if (sx) { if (!confirm('Cancel this customer\'s AutoPay?')) return; await api('POST', `${base(o)}/pay/subs/${encodeURIComponent(sx.dataset.subx)}/cancel`); await reload(); }
        } catch (er) { toast(er.message, true); }
      });
      const lf = pybox.querySelector('.pylink');
      if (lf) lf.addEventListener('submit', async e => { e.preventDefault();
        try { const v = await api('POST', base(o) + '/pay/link', {amount: lf.amount.value, purpose: lf.purpose.value, phone: lf.phone.value, her_tap: true}); toast(S(v.say)); if (v.url) prompt('Payment link (copy and send it yourself):', S(v.url)); await reload(); }
        catch (er) { toast(er.message, true); } });
      const pf = pybox.querySelector('.pyplan');
      if (pf) pf.addEventListener('submit', async e => { e.preventDefault();
        try { drawPay(await api('POST', base(o) + '/pay/plans', {name: pf.name.value, amount: pf.amount.value, period: pf.period.value, count: pf.count.value, her_tap: true})); toast('Plan added. Customers see it under AutoPay in the app.'); }
        catch (er) { toast(er.message, true); } });
      const sf = pybox.querySelector('.pysplit');
      if (sf) sf.addEventListener('submit', async e => { e.preventDefault();
        const vendors = [], rules = [];
        sf.lines.value.split('\n').map(x => x.split(',').map(y => y.trim())).filter(x => x.length >= 3 && x[1]).forEach((x, i) => { const k = 'v' + (i + 1); vendors.push({key: k, name: x[0], account: x[1]}); rules.push({vendor: k, percent: Number(x[2])}); });
        if (!confirm(`Approve this payout rule? ${rules.map(r => r.percent + '%').join(' + ')} of every paid order goes to these vendors through ${S(py.gateway)}.`)) return;
        try { drawPay(await api('PUT', base(o) + '/pay/split', {vendors, rules, her_tap: true})); toast('Payout rule approved.'); }
        catch (er) { toast(er.message, true); } });
    };
    try { drawPay(await api('GET', base(o) + '/pay')); } catch (er) { pybox.remove(); }
    // v0.355 GST BILL: her GST details -> finished rows get a tax invoice (GST-inclusive prices)
    const gbox = document.createElement('section'); gbox.className = 'stcol stgst'; box.appendChild(gbox);
    const drawGst = g => {
      gbox.innerHTML = `<h4>GST invoices <span>${g.on ? 'On' : 'Off'}</span></h4><p class="stnote">${esc(S(g.note))}</p>
        <form class="stapp" autocomplete="off"><div class="row"><input name="gstin" maxlength="15" placeholder="GSTIN (blank = plain receipts)" value="${esc(S(g.gstin))}" aria-label="GSTIN">
        <input name="legal_name" maxlength="120" placeholder="Legal name (as on GST certificate)" value="${esc(S(g.legal_name))}" aria-label="Legal name"></div>
        <div class="row"><label>Default rate <select name="rate">${L(g.rates).map(x => `<option value="${x}"${N(x) === N(g.rate) ? ' selected' : ''}>${x}%</option>`).join('')}</select></label>
        <input name="hsn" maxlength="8" placeholder="Default HSN / SAC" value="${esc(S(g.hsn))}" aria-label="Default HSN or SAC">
        <button class="btn go" type="submit">Save GST</button></div>
        ${L(g.products).length ? `<div class="sttbl"><table><thead><tr><th>Product</th><th>Price</th><th>HSN / SAC</th><th>Rate</th></tr></thead><tbody>${L(g.products).map(p => `<tr data-p="${esc(S(p.id))}"><td>${esc(S(p.name))}</td><td>${esc(S(p.price))}</td>
          <td><input data-k="hsn" maxlength="8" value="${esc(S(p.hsn))}" aria-label="HSN for ${esc(S(p.name))}"></td>
          <td><select data-k="rate" aria-label="Rate for ${esc(S(p.name))}"><option value="">Default</option>${L(g.rates).map(x => `<option value="${x}"${p.rate !== undefined && p.rate !== null && N(x) === N(p.rate) ? ' selected' : ''}>${x}%</option>`).join('')}</select></td></tr>`).join('')}</tbody></table></div>` : ''}
        </form>${g.on ? `<p class="stnote">Invoices issued: ${N(g.issued)} · ${esc(S(g.state))}</p>` : ''}`;
      gbox.querySelector('form').addEventListener('submit', async e => {
        e.preventDefault(); const f = e.target, b = f.querySelector('button.go'); b.disabled = true;
        const items = {}; f.querySelectorAll('tr[data-p]').forEach(tr => { items[tr.dataset.p] = {hsn: tr.querySelector('[data-k=hsn]').value.trim(), rate: tr.querySelector('[data-k=rate]').value}; });
        try { drawGst(await api('PUT', base(o) + '/gst', {gstin: f.gstin.value.trim(), legal_name: f.legal_name.value.trim(), rate: f.rate.value, hsn: f.hsn.value.trim(), items})); toast('GST details saved.'); }
        catch (er) { toast(er.message, true); b.disabled = false; }
      });
    };
    try { drawGst(await api('GET', base(o) + '/gst')); } catch (er) { gbox.remove(); }
    // v0.362 VARIANTS: sizes / weights with their own price (one line per product: "1 kg 60, 5 kg 280")
    const vbox = document.createElement('section'); vbox.className = 'stcol stvariants'; box.appendChild(vbox);
    const drawV = v => {
      const ps = L(v.products); if (!ps.length) { vbox.remove(); return; }
      vbox.innerHTML = `<h4>Sizes <span>${ps.filter(p => L(p.variants).length).length} products</span></h4><p class="stnote">${esc(S(v.note))} Write sizes as "1 kg 60, 5 kg 280".</p>
        <div class="sttbl"><table><thead><tr><th>Product</th><th>Sizes (name price, ...)</th><th></th></tr></thead><tbody>${ps.map(p => `<tr data-p="${esc(S(p.id))}"><td>${esc(S(p.name))}</td>
        <td><input data-k="v" value="${esc(L(p.variants).map(x => S(x.name) + ' ' + N(x.price)).join(', '))}" placeholder="e.g. 1 kg 60, 5 kg 280" aria-label="Sizes of ${esc(S(p.name))}"></td>
        <td><button class="ib" type="button" data-vsave>Save</button></td></tr>`).join('')}</tbody></table></div>`;
    };
    vbox.addEventListener('click', async e => {
      const b = e.target.closest('[data-vsave]'), tr = e.target.closest('tr[data-p]'); if (!b || !tr) return;
      const raw = tr.querySelector('[data-k=v]').value.split(',').map(x => x.trim()).filter(Boolean);
      const variants = raw.map(x => { const m = x.match(/^(.*?)\s+(?:₹|rs\.?\s*)?([\d.,]+)$/i); return m ? {name: m[1].trim(), price: m[2].replace(/,/g, '')} : {name: x, price: ''}; });
      b.disabled = true;
      try { drawV(await api('PUT', base(o) + '/variants', {product: tr.dataset.p, variants})); toast('Sizes saved.'); } catch (er) { toast(er.message, true); b.disabled = false; }
    });
    try { if (S(info.order)) drawV(await api('GET', base(o) + '/variants')); else vbox.remove(); } catch (er) { vbox.remove(); }
    // v0.357 STOCK: how many of each product she has (blank = unlimited) and when to warn her
    const kbox = document.createElement('section'); kbox.className = 'stcol ststock'; box.appendChild(kbox);
    const drawStock = v => {
      const ps = L(v.products);
      if (!ps.length) { kbox.remove(); return; }
      kbox.innerHTML = `<h4>Stock <span>${N(v.tracked)} counted · ${N(v.sold_out)} sold out</span></h4><p class="stnote">${esc(S(v.note))}</p>
        <form autocomplete="off"><div class="sttbl"><table><thead><tr><th>Product</th><th>Price</th><th>In stock</th><th>Warn at</th></tr></thead><tbody>${ps.map(p => `<tr data-p="${esc(S(p.id))}"${p.sold_out ? ' class="soldout"' : ''}><td>${esc(S(p.name))}${p.sold_out ? ' · Sold out' : ''}</td><td>${esc(S(p.price))}</td>
          <td><input data-k="qty" inputmode="numeric" placeholder="unlimited" value="${p.qty === null || p.qty === undefined ? '' : N(p.qty)}" aria-label="Stock of ${esc(S(p.name))}"></td>
          <td><input data-k="low" inputmode="numeric" value="${N(p.low)}" aria-label="Warning level for ${esc(S(p.name))}"></td></tr>`).join('')}</tbody></table></div>
        <div class="acts"><button class="btn go" type="submit">Save stock</button></div></form>`;
      kbox.querySelector('form').addEventListener('submit', async e => {
        e.preventDefault(); const b = e.target.querySelector('button.go'); b.disabled = true;
        const items = {}; kbox.querySelectorAll('tr[data-p]').forEach(tr => { const q = tr.querySelector('[data-k=qty]').value.trim(); items[tr.dataset.p] = {qty: q === '' ? null : q, low: tr.querySelector('[data-k=low]').value.trim()}; });
        try { drawStock(await api('PUT', base(o) + '/stock', {items})); toast('Stock saved.'); } catch (er) { toast(er.message, true); b.disabled = false; }
      });
    };
    try { drawStock(await api('GET', base(o) + '/stock')); } catch (er) { kbox.remove(); }
    // v0.358 COUPON: her discount codes
    const cpbox = document.createElement('section'); cpbox.className = 'stcol stcoupon'; box.appendChild(cpbox);
    const drawCp = v => {
      const cs = L(v.coupons);
      cpbox.innerHTML = `<h4>Coupon codes <span>${cs.filter(c => c.live).length} live</span></h4><p class="stnote">${esc(S(v.note))}</p>
        ${cs.length ? `<div class="sttbl"><table><thead><tr><th>Code</th><th>Discount</th><th>Min order</th><th>Last date</th><th>Used</th><th></th></tr></thead><tbody>${cs.map(c => `<tr data-c="${esc(S(c.code))}"><td>${esc(S(c.code))}${c.live ? '' : ' · off'}</td>
          <td>${c.kind === 'percent' ? N(c.value) + '%' + (c.cap ? ' (max ₹' + N(c.cap) + ')' : '') : '₹' + N(c.value)}</td><td>${c.min ? '₹' + N(c.min) : '-'}</td><td>${esc(S(c.until) || '-')}</td>
          <td>${N(c.used)}${c.uses ? ' / ' + N(c.uses) : ''}${c.once ? ' · once each' : ''}</td><td><button class="ib" type="button" data-cpdel aria-label="Delete ${esc(S(c.code))}">✕</button></td></tr>`).join('')}</tbody></table></div>` : ''}
        <form class="stapp" autocomplete="off"><div class="row"><input name="code" maxlength="16" placeholder="CODE (e.g. DIWALI10)" aria-label="Code">
        <select name="kind" aria-label="Kind"><option value="percent">% off</option><option value="flat">₹ off</option></select>
        <input name="value" inputmode="decimal" placeholder="10" aria-label="Discount"><input name="cap" inputmode="decimal" placeholder="max ₹ (optional)" aria-label="Maximum discount">
        <input name="min" inputmode="decimal" placeholder="min order ₹" aria-label="Minimum order"><input name="until" type="date" aria-label="Last date">
        <input name="uses" inputmode="numeric" placeholder="total uses" aria-label="Total uses"><label><input name="once" type="checkbox"> once per customer</label>
        <button class="btn go" type="submit">Add code</button></div></form>`;
      cpbox.querySelector('form').addEventListener('submit', async e => {
        e.preventDefault(); const f = e.target, b = f.querySelector('button.go'); b.disabled = true;
        const body = {code: f.code.value.trim(), kind: f.kind.value, value: f.value.value.trim(), cap: f.cap.value.trim(), min: f.min.value.trim(), until: f.until.value, uses: f.uses.value.trim(), once: f.once.checked};
        try { drawCp(await api('PUT', base(o) + '/coupons', body)); toast('Code saved.'); } catch (er) { toast(er.message, true); b.disabled = false; }
      });
      if (!cpbox.dataset.wired) {          // one click listener for the box (the table is redrawn)
        cpbox.dataset.wired = '1';
        cpbox.addEventListener('click', async e => {
          const b = e.target.closest('[data-cpdel]'), tr = e.target.closest('tr[data-c]'); if (!b || !tr || !confirm('Delete code ' + tr.dataset.c + '?')) return;
          try { drawCp(await api('PUT', base(o) + '/coupons', {code: tr.dataset.c, delete: true})); toast('Deleted.'); } catch (er) { toast(er.message, true); }
        });
      }
    };
    try { if (S(info.order)) drawCp(await api('GET', base(o) + '/coupons')); else cpbox.remove(); } catch (er) { cpbox.remove(); }
    // v0.360 DELIVERY: fee, free above, PIN codes, opening hours (orders outside them are still taken, with a note)
    const dbox = document.createElement('section'); dbox.className = 'stcol stdelivery'; box.appendChild(dbox);
    const drawDl = v => {
      const h = M(v.hours), days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      dbox.innerHTML = `<h4>Delivery <span>${v.on ? (v.open_now ? 'open now' : 'closed now') : 'no rules'}</span></h4><p class="stnote">${esc(S(v.note))}</p>
        <form class="stapp" autocomplete="off"><div class="row"><label>Charge ₹ <input name="fee" inputmode="decimal" value="${v.on ? N(v.fee) : ''}" aria-label="Delivery charge"></label>
        <label>Free above ₹ <input name="free_above" inputmode="decimal" value="${v.free_above === null || v.free_above === undefined ? '' : N(v.free_above)}" aria-label="Free delivery above"></label></div>
        <div class="row"><textarea name="pins" rows="2" placeholder="PIN codes you deliver to (blank = everywhere)" aria-label="PIN codes">${esc(L(v.pins).join(', '))}</textarea></div>
        <div class="row"><label>Opens <input name="open" type="time" value="${esc(S(h.open))}"></label><label>Closes <input name="close" type="time" value="${esc(S(h.close))}"></label>
        ${days.map((d, i) => `<label><input type="checkbox" name="d${i}"${L(h.days).includes(i) ? ' checked' : ''}> ${d}</label>`).join('')}</div>
        <div class="acts"><button class="btn go" type="submit">Save delivery</button>${v.on ? '<button class="btn soft" type="button" data-dloff>Remove rules</button>' : ''}</div></form>
        <form class="stapp" autocomplete="off" data-slots><p class="stnote">Delivery time slots (one per line: label, start, end, orders) - e.g. "Morning, 09:00, 11:00, 10". Blank = no slots.</p>
        <div class="row"><textarea name="slots" rows="3" aria-label="Slots">${esc(L(v.slots).map(x => [S(x.label), S(x.start), S(x.end), N(x.cap)].join(', ')).join('\n'))}</textarea></div>
        <div class="row"><label>Days ahead <input name="days" inputmode="numeric" value="${N(v.days)}"></label><label>Cut-off minutes <input name="cutoff" inputmode="numeric" value="${N(v.cutoff)}"></label>
        <button class="btn go" type="submit">Save slots</button></div></form>
        <form class="stapp" autocomplete="off" data-hol><p class="stnote">Holidays (shop closed): one date per line or comma, YYYY-MM-DD. Orders on those days are still taken, with a note; no slots are offered.</p>
        <div class="row"><textarea name="h" rows="2" aria-label="Holidays">${esc(L(v.holidays).join(', '))}</textarea><button class="btn go" type="submit">Save holidays</button></div></form>`;
      const fh = dbox.querySelector('[data-hol]');
      fh.addEventListener('submit', async e => { e.preventDefault(); try { drawDl(await api('PUT', base(o) + '/delivery', {holidays: fh.h.value})); toast('Holidays saved.'); } catch (er) { toast(er.message, true); } });
      const fs = dbox.querySelector('[data-slots]');
      fs.addEventListener('submit', async e => {
        e.preventDefault();
        const slots = fs.slots.value.split('\n').map(l => l.split(',').map(x => x.trim())).filter(a => a[0]).map(a => ({label: a[0], start: a[1], end: a[2], cap: a[3]}));
        try { drawDl(await api('PUT', base(o) + '/delivery', {slots, days: fs.days.value.trim() || 0, cutoff: fs.cutoff.value.trim() || 0})); toast('Slots saved.'); } catch (er) { toast(er.message, true); }
      });
      const f = dbox.querySelector('form');
      f.addEventListener('submit', async e => {
        e.preventDefault(); const b = f.querySelector('button.go'); b.disabled = true;
        const body = {fee: f.fee.value.trim() || 0, free_above: f.free_above.value.trim(), pins: f.pins.value,
                      hours: {open: f.open.value, close: f.close.value, days: days.map((_, i) => f['d' + i].checked ? i : -1).filter(i => i >= 0)}};
        try { drawDl(await api('PUT', base(o) + '/delivery', body)); toast('Delivery saved.'); } catch (er) { toast(er.message, true); b.disabled = false; }
      });
      const off = dbox.querySelector('[data-dloff]');
      if (off) off.addEventListener('click', async () => { try { drawDl(await api('PUT', base(o) + '/delivery', {off: true})); toast('Delivery rules removed.'); } catch (er) { toast(er.message, true); } });
    };
    try { if (S(info.order)) drawDl(await api('GET', base(o) + '/delivery')); else dbox.remove(); } catch (er) { dbox.remove(); }
    // v0.367 TURANT: instant notifications for her Android app's phones (her tap)
    const tbox = document.createElement('section'); tbox.className = 'stcol stturant'; box.appendChild(tbox);
    const drawT = v => {
      const ik = M(v.ios_key);
      tbox.innerHTML = `<h4>Instant notifications <span>${v.on ? 'Android on' : 'Android off'} · ${v.ios ? 'iPhone on' : 'iPhone off'}</span></h4><p class="stnote">${esc(S(v.note))}${v.on || v.ios ? ' Phones registered: ' + N(v.tokens) + '.' : ''}</p>
        <div class="acts">${v.configured ? `<button class="btn ${v.on ? 'soft' : 'go'}" type="button" data-turant="${v.on ? '0' : '1'}">${v.on ? 'Switch off' : 'Switch on (next Android build)'}</button>` : ''}</div>
        <form class="stapp" autocomplete="off" data-ios><p class="stnote">iPhone: your Apple push key (Apple Developer > Keys > Apple Push Notifications service). Sealed on the server, never shown again. ${ik.key_id ? 'Set: key ' + esc(S(ik.key_id)) + ', team ' + esc(S(ik.team_id)) + '.' : ''}</p>
        <div class="row"><input name="key_id" maxlength="10" placeholder="Key ID" aria-label="Apple Key ID"><input name="team_id" maxlength="10" placeholder="Team ID" aria-label="Apple Team ID">
        <input name="p8" type="file" accept=".p8" aria-label="AuthKey .p8 file"><button class="btn go" type="submit">Save iPhone key</button>${v.ios ? '<button class="btn soft" type="button" data-iosclear>Remove</button>' : ''}</div></form>`;
      const fi = tbox.querySelector('[data-ios]');
      fi.addEventListener('submit', async e => {
        e.preventDefault(); const f = fi.p8.files[0]; if (!f) { toast('Choose the .p8 file', true); return; }
        try { drawT(await api('PUT', base(o) + '/turant/ios', {key_id: fi.key_id.value.trim(), team_id: fi.team_id.value.trim(), p8: await f.text()})); toast('iPhone key saved (sealed). It reaches iPhones with the next iPhone build.'); }
        catch (er) { toast(er.message, true); }
      });
      const ic = tbox.querySelector('[data-iosclear]');
      if (ic) ic.addEventListener('click', async () => { try { drawT(await api('PUT', base(o) + '/turant/ios', {clear: true})); } catch (er) { toast(er.message, true); } });
      const b = tbox.querySelector('[data-turant]');
      if (b) b.addEventListener('click', async () => { b.disabled = true; try { drawT(await api('PUT', base(o) + '/turant', {on: b.dataset.turant === '1'})); toast('Saved. It reaches phones with the next Android build.'); } catch (er) { toast(er.message, true); b.disabled = false; } });
    };
    try { drawT(await api('GET', base(o) + '/turant')); } catch (er) { tbox.remove(); }
    // v0.382 DIMAAG: the app's brain - linked lists, formulas, rules, workflows + approvals, triggers, timed jobs, locked functions.
    // Opus drafts it from her words, the checker proves it, ONLY her "Apply" tap makes it live.
    const lbox = document.createElement('section'); lbox.className = 'stcol stlogic'; box.appendChild(lbox);
    const drawL = v => {
      const d = v.draft ? M(v.draft) : null;
      const li = a => L(a).map(x => `<li>${esc(S(x))}</li>`).join('');
      const apps = L(v.approvals).filter(a => a.status === 'pending');
      const jobs = L(M(v.spec).schedules);
      lbox.innerHTML = `<h4>App logic <span>${v.has_logic ? (v.on ? 'on' : 'off') + ' · rev ' + N(v.rev) : 'none yet'}</span></h4>
        <p class="stnote">Linked lists (customer → orders → items), totals and formulas, rules, workflows with approvals, automatic actions, timed jobs and locked custom functions. Hoola drafts; nothing changes in the app until you press Apply.</p>
        ${v.has_logic ? `<ul class="stlines">${li(v.summary)}</ul>` : ''}
        <form class="stapp" autocomplete="off" data-ldraft><div class="row"><textarea name="w" rows="2" maxlength="2000" placeholder="${v.has_logic ? 'What should change? e.g. quotes above 50,000 need manager then director approval' : 'Leave blank for the full logic from the app brief, or describe it'}" aria-label="Logic in your words"></textarea></div>
        <div class="acts"><button class="btn go" type="submit">Draft logic</button>${v.has_logic ? `<button class="btn soft" type="button" data-lsw="${v.on ? '0' : '1'}">${v.on ? 'Switch logic off' : 'Switch logic on'}</button>` : ''}</div></form>
        ${d ? `<div class="stdraft"><h5>Draft ${d.errors && d.errors.length ? '· ' + N(d.errors.length) + ' problem(s)' : '· ready'}</h5>
          ${d.summary ? `<p>${esc(S(d.summary))}</p>` : ''}<ul class="stlines">${li(d.lines)}</ul>
          ${L(d.schema_changes).length ? `<p class="stnote">New lists / fields: ${esc(L(d.schema_changes).join('; '))}</p>` : ''}
          ${L(d.questions).length ? `<p class="stnote">Questions: ${esc(L(d.questions).join(' '))}</p>` : ''}
          ${L(d.errors).length ? `<ul class="sterr">${li(d.errors)}</ul>` : ''}${L(d.warnings).length ? `<ul class="stwarn">${li(d.warnings)}</ul>` : ''}
          <div class="acts">${L(d.errors).length ? '' : `<button class="btn go" type="button" data-lapply="${esc(S(d.hash))}">Apply to my app</button>`}<button class="btn soft" type="button" data-ldiscard>Discard draft</button></div></div>` : ''}
        ${apps.length ? `<h5>Approvals waiting (${apps.length})</h5><ul class="stmems">${apps.map(a => `<li><b>${esc(S(a.title))}</b> · ${esc(S(a.label))}: ${esc(S(a.from))} → ${esc(S(a.to))} · step ${N(a.step)}/${N(a.of)} (${esc(S(a.waiting_for))})${a.maker ? ' · asked by ' + esc(S(a.maker)) : ''}
          <button class="btn go" type="button" data-ldec="approve" data-aid="${esc(S(a.id))}">Approve</button> <button class="btn soft" type="button" data-ldec="reject" data-aid="${esc(S(a.id))}">Reject</button></li>`).join('')}</ul>` : ''}
        ${jobs.length ? `<h5>Timed jobs</h5><ul class="stmems">${jobs.map(j => `<li>${esc(S(j.label || j.name))} · ${esc(S(j.every))} IST${M(v.ran)[j.name] ? ' · last ' + esc(S(M(v.ran)[j.name]).slice(0, 16).replace('T', ' ')) : ''} <button class="ib" type="button" data-lrun="${esc(S(j.name))}">Run now</button></li>`).join('')}</ul>` : ''}
        ${L(v.audit).length ? `<details><summary>What the logic did (last ${Math.min(12, L(v.audit).length)})</summary><ul class="stlines">${L(v.audit).slice(0, 12).map(x => `<li>${esc(S(x.at).slice(5, 16).replace('T', ' '))} · ${esc(S(x.kind))}${x.coll ? ' · ' + esc(S(x.coll)) : ''} · ${esc(S(x.what))}${x.by ? ' · ' + esc(S(x.by)) : ''}</li>`).join('')}</ul></details>` : ''}
        ${v.has_logic ? `<details><summary>Edit the logic directly (advanced)</summary><form class="stapp" data-ljson><div class="row"><textarea name="j" rows="10" spellcheck="false" aria-label="Logic JSON">${esc(JSON.stringify(M(v.spec), null, 1))}</textarea></div><div class="acts"><button class="btn go" type="submit">Check and apply</button></div></form></details>` : ''}`;
      const fd = lbox.querySelector('[data-ldraft]');
      fd.addEventListener('submit', async e => {
        e.preventDefault(); const b = fd.querySelector('button.go'); b.disabled = true; b.textContent = 'Drafting…';
        try { const r = await api('POST', base(o) + '/logic/draft', {words: fd.w.value.trim()}); toast(S(r.say).slice(0, 200)); drawL(await api('GET', base(o) + '/logic')); }
        catch (er) { toast(er.message, true); b.disabled = false; b.textContent = 'Draft logic'; }
      });
      const ap = lbox.querySelector('[data-lapply]');
      if (ap) ap.addEventListener('click', async () => { ap.disabled = true; try { const r = await api('POST', base(o) + '/logic/apply', {hash: ap.dataset.lapply}); toast(S(r.say)); drawL(await api('GET', base(o) + '/logic')); } catch (er) { toast(er.message, true); ap.disabled = false; } });
      const dc = lbox.querySelector('[data-ldiscard]');
      if (dc) dc.addEventListener('click', async () => { try { await api('DELETE', base(o) + '/logic/draft'); drawL(await api('GET', base(o) + '/logic')); } catch (er) { toast(er.message, true); } });
      const sw = lbox.querySelector('[data-lsw]');
      if (sw) sw.addEventListener('click', async () => { try { const r = await api('POST', base(o) + '/logic/switch', {on: sw.dataset.lsw === '1'}); toast(S(r.say)); drawL(await api('GET', base(o) + '/logic')); } catch (er) { toast(er.message, true); } });
      lbox.querySelectorAll('[data-ldec]').forEach(b => b.addEventListener('click', async () => {
        b.disabled = true;
        try { const r = await api('POST', base(o) + '/approvals/' + encodeURIComponent(b.dataset.aid), {decision: b.dataset.ldec}); toast(S(r.say)); drawL(await api('GET', base(o) + '/logic')); }
        catch (er) { toast(er.message, true); b.disabled = false; }
      }));
      lbox.querySelectorAll('[data-lrun]').forEach(b => b.addEventListener('click', async () => {
        try { const r = await api('POST', base(o) + '/logic/run/' + encodeURIComponent(b.dataset.lrun)); toast(`${N(r.acted)} entries done.`); drawL(await api('GET', base(o) + '/logic')); } catch (er) { toast(er.message, true); }
      }));
      const fj = lbox.querySelector('[data-ljson]');
      if (fj) fj.addEventListener('submit', async e => {
        e.preventDefault(); let spec;
        try { spec = JSON.parse(fj.j.value); } catch (er) { toast('That is not valid JSON.', true); return; }
        try { const r = await api('PUT', base(o) + '/logic', {logic: spec}); if (r.ok === false) toast(L(r.errors).slice(0, 3).join(' · '), true); else { toast(S(r.say)); drawL(await api('GET', base(o) + '/logic')); } }
        catch (er) { toast(er.message, true); }
      });
    };
    try { drawL(await api('GET', base(o) + '/logic')); } catch (er) { lbox.remove(); }
    // v0.390 PAKKI NEEV: her app's data is safe - how much it uses (and its limits), backups, a restore to any minute
    // (preview first, then HER tap), and the whole data as a ZIP.
    const sbox = document.createElement('section'); sbox.className = 'stcol stsafe'; box.appendChild(sbox);
    const drawS = async () => {
      const [u, b] = await Promise.all([api('GET', base(o) + '/usage'), api('GET', base(o) + '/backups')]);
      const lim = M(u.limits), pc = M(u.percent);
      const bar = (k, used, label) => `<li><span>${label}: ${N(used).toLocaleString('en-IN')} / ${N(lim[k]).toLocaleString('en-IN')}</span><span class="stmeter"><i style="width:${Math.min(100, N(pc[k]))}%"></i></span><span>${N(pc[k])}%</span></li>`;
      sbox.innerHTML = `<h4>Data safety <span>${L(b.backups).length} backups · ${N(u.backups_mb)} MB</span></h4>
        <p class="stnote">Every change to this app's data is written to a journal; a full backup is taken every day and before every risky change. You can bring the data back to any minute. Nothing changes until you press Restore.</p>
        <ul class="stmems">${bar('rows', u.rows, 'Entries')}${bar('files_mb', u.files_mb, 'Files (MB)')}${bar('writes_day', u.writes_today, 'Writes today')}</ul>
        <form class="stapp" data-slim autocomplete="off"><div class="row"><label>Entries limit <input name="rows" inputmode="numeric" value="${N(lim.rows)}"></label><label>Files MB <input name="files_mb" inputmode="numeric" value="${N(lim.files_mb)}"></label><label>Writes a day <input name="writes_day" inputmode="numeric" value="${N(lim.writes_day)}"></label><button class="btn soft" type="submit">Save limits</button></div></form>
        <div class="acts"><button class="btn go" type="button" data-snap>Back up now</button><button class="btn soft" type="button" data-exp>Download all data (ZIP)</button></div>
        <form class="stapp" data-pitr autocomplete="off"><p class="stnote">Bring the data back to a moment (your time, IST):</p><div class="row"><input name="at" type="datetime-local" step="60" aria-label="Moment"><button class="btn soft" type="submit">Preview</button></div><div data-pv></div></form>
        ${L(b.backups).length ? `<details><summary>Backups (${L(b.backups).length})</summary><ul class="stmems">${L(b.backups).slice(0, 30).map(x => `<li><span>${esc(S(x.at).slice(0, 16).replace('T', ' '))} UTC · ${esc(S(x.kind))} · ${esc(S(x.why))} · ${N(x.rows)} entries</span><button class="ib" type="button" data-rname="${esc(S(x.name))}">Restore this</button></li>`).join('')}</ul></details>` : ''}`;
      const fl = sbox.querySelector('[data-slim]');
      fl.addEventListener('submit', async e => { e.preventDefault(); try { await api('PUT', base(o) + '/usage', {rows: fl.rows.value, files_mb: fl.files_mb.value, writes_day: fl.writes_day.value}); toast('Limits saved.'); drawS(); } catch (er) { toast(er.message, true); } });
      sbox.querySelector('[data-snap]').addEventListener('click', async e => { e.target.disabled = true; try { const r = await api('POST', base(o) + '/backups/now'); toast(`Backed up: ${N(r.rows)} entries.`); drawS(); } catch (er) { toast(er.message, true); e.target.disabled = false; } });
      sbox.querySelector('[data-exp]').addEventListener('click', async e => {
        e.target.disabled = true;
        try { const res = await api('GET', base(o) + '/export', undefined, {raw: true}); const a = document.createElement('a'); a.href = URL.createObjectURL(await res.blob()); a.download = 'app-data.zip'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30000); }
        catch (er) { toast(er.message, true); }
        e.target.disabled = false;
      });
      const doRestore = async (body, label) => {
        if (!confirm(`Restore the app's data to ${label}? A safety backup of the data as it is now is taken first.`)) return;
        try { const r = await api('POST', base(o) + '/backups/restore', body); toast(S(r.say)); drawS(); } catch (er) { toast(er.message, true); }
      };
      const fp = sbox.querySelector('[data-pitr]');
      fp.addEventListener('submit', async e => {
        e.preventDefault(); if (!fp.at.value) return;
        const pv = fp.querySelector('[data-pv]');
        try {
          const v = await api('POST', base(o) + '/backups/preview', {at: fp.at.value});
          pv.innerHTML = `<p class="stnote">Then: ${esc(Object.entries(M(v.lists_then)).map(([k, n]) => k + ' ' + n).join(', ') || 'nothing')}. Now: ${esc(Object.entries(M(v.lists_now)).map(([k, n]) => k + ' ' + n).join(', ') || 'nothing')}. ${N(v.come_back)} come back, ${N(v.go_away)} go away, ${N(v.change)} change.</p><button class="btn go" type="button" data-rat>Restore to ${esc(fp.at.value.replace('T', ' '))}</button>`;
          pv.querySelector('[data-rat]').addEventListener('click', () => doRestore({at: fp.at.value}, fp.at.value.replace('T', ' ')));
        } catch (er) { pv.innerHTML = `<p class="stnote">${esc(er.message)}</p>`; }
      });
      sbox.querySelectorAll('[data-rname]').forEach(btn => btn.addEventListener('click', () => doRestore({name: btn.dataset.rname}, 'that backup')));
    };
    try { await drawS(); } catch (er) { sbox.remove(); }
    // v0.396 APNA DATABASE: this app's data in HER own database (Supabase, Neon, RDS ... any PostgreSQL-wire database)
    const obox = document.createElement('section'); obox.className = 'stcol stowndb'; box.appendChild(obox);
    const drawO = async () => {
      const v = await api('GET', base(o) + '/owndb');
      const ln = M(v.link), live = v.linked;
      const conns = L(v.connections);
      obox.innerHTML = `<h4>Own database <span>${live ? esc(S(ln.name)) + ' · ' + esc(S(ln.mode)) + ' · ' + esc(S(ln.status)) : 'Hoola database'}</span></h4>
        <p class="stnote">Run this app's data in your own database: PostgreSQL (Supabase, Neon, AWS, Google, Azure...), MySQL (PlanetScale, TiDB, MariaDB...), MongoDB (Atlas...) or Firebase - ${L(v.providers).length} kinds listed below. Primary: every entry is saved there first, and what you edit there comes back into the app. Copy: a live read copy for reports.</p>
        ${live ? `<ul class="stmems"><li><span>Where: ${esc(S(ln.label))} · schema <b>${esc(S(ln.schema))}</b></span></li>
          <li><span>Waiting to sync: ${N(v.lag)} · last sync ${esc(S(ln.last_sync || ln.live_at).slice(0, 16).replace('T', ' '))} UTC</span></li>
          ${ln.last_error ? `<li><span class="sterr">Last problem: ${esc(S(ln.last_error))}</span></li>` : ''}</ul>
          <div class="acts"><button class="btn soft" type="button" data-osync>Sync now</button><button class="btn soft" type="button" data-over>Compare counts</button><button class="btn soft" type="button" data-ooff>Disconnect</button></div><div data-oout></div>`
        : `${conns.length ? `<form class="stapp" data-olink><div class="row"><label>Database <select name="conn">${conns.map(c => `<option value="${esc(S(c.id))}">${esc(S(c.name))} · ${esc(S(c.kind || 'postgres'))} (${esc(S(c.label))})${c.can_write === false ? ' - read only' : ''}</option>`).join('')}</select></label>
            <label>Mode <select name="mode"><option value="primary">Primary - data lives there</option><option value="mirror">Copy - Hoola stays main</option></select></label></div>
            <div class="acts"><button class="btn go" type="submit">Move this app's data there</button></div></form>` : '<p class="stnote">No database connected yet. Add one below.</p>'}
          <form class="stapp" data-oadd autocomplete="off"><p class="stnote">Add a database: pick its type and paste its connection (sealed on the server, never shown again; never paste it in chat).</p>
            <div class="row"><select name="kind" aria-label="Type"><option value="postgres">PostgreSQL (Supabase, Neon, RDS...)</option><option value="mysql">MySQL (PlanetScale, TiDB, MariaDB...)</option><option value="mongodb">MongoDB (Atlas...)</option><option value="firestore">Firebase (Firestore)</option></select>
            <input name="name" maxlength="60" placeholder="Name, e.g. Shop database" aria-label="Name"></div>
            <div class="row"><textarea name="dsn" rows="2" autocomplete="off" spellcheck="false" placeholder="postgresql://... | mysql://user:password@host:3306/db | mongodb+srv://user:password@cluster/db | the Firebase service-account JSON" aria-label="Connection"></textarea><button class="btn soft" type="submit">Connect</button></div></form>
          <details><summary>Where to find the connection (${L(v.providers).length} databases)</summary><ul class="stlines">${L(v.providers).map(p => `<li><b>${esc(S(p.name))}</b> <span class="stnote">${esc(S(p.kind))}</span>: ${esc(S(p.how))}${p.note ? ' - ' + esc(S(p.note)) : ''}</li>`).join('')}</ul></details>`}`;
      const out = obox.querySelector('[data-oout]');
      const fl = obox.querySelector('[data-olink]');
      if (fl) fl.addEventListener('submit', async e => {
        e.preventDefault();
        const name = fl.conn.selectedOptions[0].textContent;
        if (!confirm(`Move this app's data to ${name}? A backup is taken first; every entry is copied and the counts are compared before it goes live.`)) return;
        const b = fl.querySelector('button.go'); b.disabled = true; b.textContent = 'Copying…';
        try { const r = await api('POST', base(o) + '/owndb/link', {conn: fl.conn.value, mode: fl.mode.value}); toast(S(r.say)); drawO(); }
        catch (er) { toast(er.message, true); b.disabled = false; b.textContent = "Move this app's data there"; }
      });
      const fa = obox.querySelector('[data-oadd]');
      if (fa) fa.addEventListener('submit', async e => {
        e.preventDefault();
        try { const r = await api('POST', '/api/owndb/conns', {kind: fa.kind.value, name: fa.name.value.trim(), secret: fa.dsn.value.trim()}); fa.dsn.value = ''; toast(S(r.say)); drawO(); }
        catch (er) { fa.dsn.value = ''; toast(er.message, true); }
      });
      const bs = obox.querySelector('[data-osync]');
      if (bs) bs.addEventListener('click', async () => { try { await api('POST', base(o) + '/owndb/sync'); toast('Synced.'); drawO(); } catch (er) { toast(er.message, true); } });
      const bv = obox.querySelector('[data-over]');
      if (bv) bv.addEventListener('click', async () => {
        try { const r = await api('POST', base(o) + '/owndb/verify'); out.innerHTML = `<p class="stnote">${r.ok ? 'All counts match: ' : 'Different: '}${esc(Object.entries(M(r.counts)).map(([k, x]) => `${k} ${N(x.app)}/${N(x.database)}`).join(', '))}</p>`; }
        catch (er) { toast(er.message, true); }
      });
      const bo = obox.querySelector('[data-ooff]');
      if (bo) bo.addEventListener('click', async () => {
        if (!confirm('Disconnect? The app goes back to Hoola\'s database; your data stays in your database too.')) return;
        try { const r = await api('POST', base(o) + '/owndb/unlink'); toast(S(r.say)); drawO(); } catch (er) { toast(er.message, true); }
      });
    };
    try { await drawO(); } catch (er) { obox.remove(); }
    // v0.378 BAAT: her customers' messages from the app (their words = data); she replies by her own tap
    const cbx = document.createElement('section'); cbx.className = 'stcol stchat'; box.appendChild(cbx);
    const drawC = async (v, open) => {
      const ts = L(v.threads); if (!ts.length) { cbx.remove(); return; }
      let thread = '';
      if (open) {
        const t = await api('GET', base(o) + '/chat?member=' + encodeURIComponent(open));
        thread = `<div class="stthread">${L(t.messages).map(m => `<p class="${m.staff ? 'me' : 'them'}"><b>${esc(S(m.name))}</b>: ${esc(S(m.text))}</p>`).join('')}</div>
          <form class="stapp" data-reply="${esc(open)}"><div class="row"><input name="t" maxlength="1000" placeholder="Reply" aria-label="Reply"><button class="btn go" type="submit">Send</button></div></form>`;
      }
      cbx.innerHTML = `<h4>Customer messages <span>${N(v.unread)} unread</span></h4>
        <ul class="stmems">${ts.map(t => `<li><button class="ib" type="button" data-thr="${esc(S(t.member))}">${esc(S(t.name))}${t.unread ? ' (' + N(t.unread) + ')' : ''}</button> <span>${esc(S(t.last))}</span></li>`).join('')}</ul>${thread}`;
    };
    cbx.addEventListener('click', async e => {
      const b = e.target.closest('[data-thr]'); if (!b) return;
      try { await drawC(await api('GET', base(o) + '/chat'), b.dataset.thr); } catch (er) { toast(er.message, true); }
    });
    cbx.addEventListener('submit', async e => {
      const f = e.target.closest('[data-reply]'); if (!f) return; e.preventDefault();
      const t = f.t.value.trim(); if (!t) return;
      try { await api('POST', base(o) + '/chat/' + encodeURIComponent(f.dataset.reply), {text: t, her_tap: true}); await drawC(await api('GET', base(o) + '/chat'), f.dataset.reply); }
      catch (er) { toast(er.message, true); }
    });
    try { await drawC(await api('GET', base(o) + '/chat')); } catch (er) { cbx.remove(); }
    // v0.375 KHATA YAAD: payment reminders for customers who owe - her own WhatsApp (link) or her approved template (her tap)
    const ybox = document.createElement('section'); ybox.className = 'stcol stkhata'; box.appendChild(ybox);
    const drawY = v => {
      const cs = L(v.customers); if (!cs.length) { ybox.remove(); return; }
      ybox.innerHTML = `<h4>Khata yaad <span>${cs.length} owe</span></h4><p class="stnote">${esc(S(v.note))}</p>
        <div class="row"><input data-tpl placeholder="Approved UTILITY template name (for business WhatsApp)" aria-label="Template name"></div>
        <div class="sttbl"><table><thead><tr><th>Customer</th><th>Owes</th><th>Phone</th><th></th></tr></thead><tbody>${cs.map(c => `<tr data-m="${esc(S(c.member))}"><td>${esc(S(c.name))}</td><td>₹${N(c.balance)}</td><td>${esc(S(c.phone) || '-')}</td>
          <td>${c.link ? `<a class="ib" href="${esc(S(c.link))}" target="_blank" rel="noopener">Open in WhatsApp</a>` : ''} ${c.phone && !c.recent ? '<button class="ib" type="button" data-ysend>Send via business</button>' : (c.recent ? 'reminded recently' : '')}</td></tr>`).join('')}</tbody></table></div>`;
    };
    ybox.addEventListener('click', async e => {
      const b = e.target.closest('[data-ysend]'), tr = e.target.closest('tr[data-m]'); if (!b || !tr) return;
      const tpl = (ybox.querySelector('[data-tpl]') || {}).value || '';
      if (!tpl.trim()) { toast('Type your approved template name first', true); return; }
      if (!confirm('Send this reminder from your WhatsApp Business number now?')) return;
      b.disabled = true;
      try { const r = await api('POST', base(o) + '/khata-yaad/' + encodeURIComponent(tr.dataset.m), {template: tpl.trim(), her_tap: true}); toast(S(r.say) || 'Sent.'); drawY(await api('GET', base(o) + '/khata-yaad')); }
      catch (er) { toast(er.message, true); b.disabled = false; }
    });
    try { drawY(await api('GET', base(o) + '/khata-yaad')); } catch (er) { ybox.remove(); }
    // v0.361 HISAAB: the month's accounts + GST summary for her CA (CSV files in a ZIP)
    const hbox = document.createElement('section'); hbox.className = 'stcol sthisaab'; box.appendChild(hbox);
    const drawH = v => {
      hbox.innerHTML = `<h4>Accounts <span>${esc(S(v.month))}</span></h4><p class="stnote">${esc(S(v.say))}</p>
        <form class="stapp" autocomplete="off"><div class="row"><input name="month" type="month" value="${esc(S(v.month))}" aria-label="Month">
        <button class="btn soft" type="submit">Show</button><button class="btn go" type="button" data-hdl>Download for CA (CSV)</button><button class="btn soft" type="button" data-gstr1>GSTR-1 file (JSON)</button><button class="btn soft" type="button" data-tally>Tally (XML)</button></div></form>
        <p class="stnote">Sales register, invoice register, credit notes, HSN and rate-wise summary, udhaar. Nothing is filed - give the files to your CA.</p>`;
      const f = hbox.querySelector('form');
      f.addEventListener('submit', async e => { e.preventDefault(); try { drawH(await api('GET', base(o) + '/hisaab?month=' + encodeURIComponent(f.month.value))); } catch (er) { toast(er.message, true); } });
      hbox.querySelector('[data-tally]').addEventListener('click', async e => {     // v0.374 Gateway of Tally > Import > Vouchers
        e.target.disabled = true;
        try {
          const res = await api('GET', base(o) + '/tally?month=' + encodeURIComponent(f.month.value), undefined, {raw: true});
          const a = document.createElement('a'); a.href = URL.createObjectURL(await res.blob()); a.download = 'tally-' + f.month.value + '.xml'; a.click();
          setTimeout(() => URL.revokeObjectURL(a.href), 30000);
        } catch (er) { toast(er.message, true); } finally { e.target.disabled = false; }
      });
      hbox.querySelector('[data-gstr1]').addEventListener('click', async e => {     // v0.373 for the GST offline tool
        e.target.disabled = true;
        try {
          const res = await api('GET', base(o) + '/gstr1?month=' + encodeURIComponent(f.month.value), undefined, {raw: true});
          const a = document.createElement('a'); a.href = URL.createObjectURL(await res.blob()); a.download = 'GSTR1-' + f.month.value + '.json'; a.click();
          setTimeout(() => URL.revokeObjectURL(a.href), 30000);
        } catch (er) { toast(er.message, true); } finally { e.target.disabled = false; }
      });
      hbox.querySelector('[data-hdl]').addEventListener('click', async e => {
        e.target.disabled = true;
        try {
          const res = await api('GET', base(o) + '/hisaab?download=1&month=' + encodeURIComponent(f.month.value), undefined, {raw: true});
          const a = document.createElement('a'); a.href = URL.createObjectURL(await res.blob()); a.download = 'hisaab-' + f.month.value + '.zip'; a.click();
          setTimeout(() => URL.revokeObjectURL(a.href), 30000);
        } catch (er) { toast(er.message, true); } finally { e.target.disabled = false; }
      });
    };
    try { drawH(await api('GET', base(o) + '/hisaab')); } catch (er) { hbox.remove(); }
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

  /* v0.351 DUKAAN: her shop - settings, products, orders (no AI; prices only hers; money confirmed only by her) */
  const OSTEP = {confirmed: 'Confirm (money received)', packed: 'Packed', shipped: 'Shipped', delivered: 'Delivered', cancelled: 'Cancel'};
  // ---------------------------------------------------------------- v0.373 CODE MODE: the site's real code, by hand or by asking
  const CODE_OPEN = {};
  function diffHtml(d) {
    return S(d).split('\n').map(l => {
      const c = l.startsWith('+++') || l.startsWith('---') ? 'f' : l.startsWith('@@') ? 'h' : l.startsWith('+') ? 'a' : l.startsWith('-') ? 'd' : '';
      return `<span class="dl${c ? ' ' + c : ''}">${esc(l) || ' '}</span>`;
    }).join('\n');
  }
  async function loadCodeMode(o, root) {
    const box = root.querySelector('.stcode'); if (!box) return;
    let t;
    try { t = await api('GET', base(o) + '/code'); } catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const groups = L(t.files), all = groups.flatMap(g => L(g.files));
    let cur = CODE_OPEN[o.id] && all.some(f => f.path === CODE_OPEN[o.id]) ? CODE_OPEN[o.id] : S(all[0]?.path);
    box.innerHTML = `<div class="stcode-bar"><p>Your website's real code: every section's HTML, CSS and script, and the design kit. Edit by hand or ask Hoola; every save is checked for safety, becomes a new version, and Undo brings it back.</p>
        <div class="acts"><button class="btn soft" type="button" data-x="undo">Undo last change</button><button class="btn soft" type="button" data-x="react">Download React project</button><button class="btn soft" type="button" data-x="zip">Download ZIP</button></div></div>
      <div class="stcode-main"><nav class="stcode-files" aria-label="Files">${groups.map(g => `<div class="stcode-g"><b>${esc(S(g.title))}</b>${L(g.files).map(f => `<button type="button" data-p="${esc(S(f.path))}" class="${f.path === cur ? 'on' : ''}" title="${esc(S(f.path))}">${esc(S(f.label))}</button>`).join('')}</div>`).join('')}</nav>
        <div class="stcode-ed"><div class="stcode-path"><code></code><span class="stcode-state"></span></div>
          <div class="stcode-area"><pre class="stcode-ln" aria-hidden="true"></pre><textarea spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="Code"></textarea></div>
          <div class="acts"><button class="btn go" type="button" data-x="save">Save (Ctrl+S)</button><span class="stnote">Scripts may not use the network, cookies or storage; outside files and on*= handlers are removed.</span></div>
          <form class="stcode-ask" autocomplete="off"><input name="q" placeholder="Ask Hoola to change this file - e.g. make the pricing table compare 3 plans" aria-label="Ask Hoola to change the code"><button class="btn go" type="submit">Ask</button></form>
          <div class="stcode-out" hidden></div></div></div>`;
    const ta = box.querySelector('textarea'), ln = box.querySelector('.stcode-ln'), pathEl = box.querySelector('.stcode-path code'),
      state = box.querySelector('.stcode-state'), out = box.querySelector('.stcode-out');
    let saved = '';
    const lines = () => { const n = ta.value.split('\n').length; ln.textContent = Array.from({length: n}, (_, i) => i + 1).join('\n'); ln.scrollTop = ta.scrollTop; };
    const dirty = () => { state.textContent = ta.value !== saved ? 'Not saved' : ''; };
    async function open(p) {
      if (ta.value !== saved && !window.confirm('This file has changes that are not saved. Leave it?')) return;
      cur = p; CODE_OPEN[o.id] = p;
      box.querySelectorAll('.stcode-files button').forEach(b => b.classList.toggle('on', b.dataset.p === p));
      pathEl.textContent = p; ta.value = ''; ta.disabled = true;
      try { const r = await api('GET', `${base(o)}/code?path=${encodeURIComponent(p)}`); saved = ta.value = S(r.code); }
      catch (er) { toast(er.message, true); }
      ta.disabled = false; lines(); dirty();
    }
    async function save() {
      const b = box.querySelector('[data-x=save]'); b.disabled = true;
      try {
        const r = await api('PUT', base(o) + '/code', {path: cur, code: ta.value});
        saved = ta.value = S(r.code); lines(); dirty();
        toast(S(r.say) || 'Saved.', L(r.removed).length > 0);
      } catch (er) { toast(er.message, true); }
      b.disabled = false;
    }
    ta.addEventListener('input', () => { lines(); dirty(); });
    ta.addEventListener('scroll', () => { ln.scrollTop = ta.scrollTop; });
    ta.addEventListener('keydown', e => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); save(); return; }
      if (e.key === 'Tab' && !e.shiftKey) { e.preventDefault(); const a = ta.selectionStart, z = ta.selectionEnd; ta.setRangeText('  ', a, z, 'end'); lines(); dirty(); }
    });
    box.querySelectorAll('.stcode-files button').forEach(b => b.addEventListener('click', () => open(b.dataset.p)));
    box.querySelector('[data-x=save]').addEventListener('click', save);
    box.querySelector('[data-x=undo]').addEventListener('click', async () => {
      if (!window.confirm('Undo your last change to this website?')) return;
      try { const r = await api('POST', base(o) + '/undo', {}); toast(S(r?.say) || 'Undone.'); saved = ''; ta.value = ''; open(cur); } catch (er) { toast(er.message, true); }
    });
    for (const [x, fmt] of [['react', 'react'], ['zip', 'zip']]) box.querySelector(`[data-x=${x}]`).addEventListener('click', async e => {
      e.target.disabled = true;
      try { const r = await api('POST', base(o) + '/export', {format: fmt}); toast(S(r?.say) || 'Ready - the ZIP is in your files.'); }
      catch (er) { toast(er.message, true); } finally { e.target.disabled = false; }
    });
    box.querySelector('.stcode-ask').addEventListener('submit', async e => {
      e.preventDefault(); const f = e.target, q = S(f.q.value).trim(), btn = f.querySelector('button');
      if (!q) return;
      if (ta.value !== saved && !window.confirm('Your unsaved changes in this file will be replaced. Go on?')) return;
      btn.disabled = true; out.hidden = false; out.innerHTML = `<p class="stempty">${spin()} Hoola is changing the code…</p>`;
      try {
        let r = await api('POST', base(o) + '/code/ask', {instruction: q, path: cur, conversation_id: C.conv?.() || ''});
        for (let i = 0; i < 120 && r.status === 'working'; i++) { await new Promise(res => setTimeout(res, 3000)); r = await api('GET', `${base(o)}/code/task/${encodeURIComponent(S(r.task))}`); }
        out.innerHTML = `<p>${esc(S(r.say))}</p>` + (L(r.removed).length ? `<p class="stnote">Removed for safety: ${esc(L(r.removed).join('; '))}</p>` : '') +
          (S(r.diff) ? `<pre class="stcode-diff">${diffHtml(r.diff)}</pre>` : '');
        if (r.status === 'done') { f.q.value = ''; saved = ''; ta.value = ''; await open(cur); }
      } catch (er) { out.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; }
      btn.disabled = false;
    });
    if (cur) open(cur);
  }

  // ---------------------------------------------------------------- v0.366 BLOG: Kalam writes, her Haan publishes on this site
  const BSTAT = {published: 'Live', scheduled: 'Scheduled', hidden: 'Hidden'};
  async function loadBlog(o, root) {
    const box = root.querySelector('.stblog'); if (!box) return;
    let b, drafts;
    try { [b, drafts] = await Promise.all([api('GET', base(o) + '/blog'), api('GET', '/api/kalam/pieces?kind=blog').catch(() => ({pieces: []}))]); }
    catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const posts = L(b.posts), photos = L(b.photos);
    const waiting = L(drafts.pieces || drafts.items || drafts).filter(x => x && S(x.kind) === 'blog' && !['published', 'rejected'].includes(S(x.status)));
    const prev = S(b.preview).replace(/\/$/, '');
    box.innerHTML = `<form class="stapp" data-f="write" autocomplete="off"><b>Write a new post</b>
        <label><span>What should it be about? Your own facts, offers and experience (Hoola never makes them up)</span>
        <textarea name="brief" rows="3" placeholder="Diwali par mithai kaise chunein - hamari kaju katli roz subah banti hai, 1985 se Akot mein"></textarea></label>
        <div class="acts"><button class="btn go" type="submit">Write draft</button><span class="stnote">Written in your voice by the Content writer; facts are checked before it goes up.</span></div></form>
      ${waiting.length ? `<section class="stcol"><h4>Drafts <span>${waiting.length}</span></h4>${waiting.map(d => `<div class="stblog-d" data-id="${esc(S(d.id))}">
        <div class="stblog-row"><b>${esc(S(d.title) || 'Untitled')}</b><small>${esc(S(d.number))} · ${N(d.words)} words · ${esc(S(d.status))}</small></div>
        <div class="acts"><button class="btn soft" type="button" data-x="open">Read / edit</button>
        <label class="stblog-when"><span>Publish at (empty = now)</span><input type="datetime-local" name="when"></label>
        <button class="btn go" type="button" data-x="publish">Publish on this website…</button></div><div class="stblog-ed" hidden></div></div>`).join('')}</section>` : ''}
      <section class="stcol"><h4>Posts <span>${posts.length}</span></h4>${posts.length ? `<div class="sttbl"><table><thead><tr><th>Post</th><th>Status</th><th>Cover</th><th></th></tr></thead><tbody>${posts.map(p => `<tr data-s="${esc(S(p.slug))}">
        <td><b>${esc(S(p.title))}</b><br><small>${esc(S(p.date))} · ${N(p.minutes)} min${p.category ? ' · ' + esc(S(p.category)) : ''}${L(p.languages).length ? ' · ' + esc(L(p.languages).join(', ')) : ''}</small></td>
        <td>${esc(BSTAT[S(p.status)] || S(p.status))}</td>
        <td><select data-x="cover" aria-label="Cover photo"><option value="">No cover</option>${photos.map(n => `<option${n === S(p.cover) ? ' selected' : ''}>${esc(S(n))}</option>`).join('')}</select></td>
        <td>${p.status === 'published' ? `<a class="btn soft" target="_blank" rel="noopener" href="${esc(prev)}/blog/${esc(S(p.slug))}/">View</a> <button class="btn soft" type="button" data-x="hide">Hide</button>` : `<button class="btn soft" type="button" data-x="show">Show</button>`}
          <button class="btn soft danger" type="button" data-x="delete">Delete</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No posts yet. Write one above, or ask in chat: "blog likho: …".</p>'}</section>
      <p class="stnote">${esc(S(b.say))} Every post has its own page, a category page, an RSS feed and Google's article data; your site's other languages get it translated.</p>`;
    const reload = () => loadBlog(o, root);
    box.querySelector('[data-f=write]').addEventListener('submit', async e => {
      e.preventDefault(); const f = e.target, btn = f.querySelector('button'), brief = S(f.brief.value).trim();
      if (!brief) { toast('Write a line about the post first.', true); return; }
      btn.disabled = true; btn.textContent = 'Writing… (about a minute)';
      try { const r = await api('POST', '/api/kalam/write', {brief, kind: 'blog'}); toast(S(r?.say) || 'Draft ready.'); reload(); }
      catch (er) { toast(er.message, true); btn.disabled = false; btn.textContent = 'Write draft'; }
    });
    box.querySelectorAll('.stblog-d').forEach(row => {
      const id = row.dataset.id, ed = row.querySelector('.stblog-ed');
      row.querySelector('[data-x=open]').addEventListener('click', async () => {
        if (!ed.hidden) { ed.hidden = true; return; }
        try {
          const r = await api('GET', `/api/kalam/pieces/${encodeURIComponent(id)}`), p = M(r.piece || r);
          ed.innerHTML = `<label><span>Title</span><input name="title" value="${esc(S(p.title))}"></label>
            <label><span>Post (Markdown: ## heading, - list, **bold**)</span><textarea name="body" rows="14">${esc(S(p.body))}</textarea></label>
            <div class="acts"><button class="btn go" type="button" data-x="save">Save</button></div>`;
          ed.hidden = false;
          ed.querySelector('[data-x=save]').addEventListener('click', async () => {
            try { await api('PUT', `/api/kalam/pieces/${encodeURIComponent(id)}`, {title: ed.querySelector('[name=title]').value, body: ed.querySelector('[name=body]').value}); toast('Saved.'); }
            catch (er) { toast(er.message, true); }
          });
        } catch (er) { toast(er.message, true); }
      });
      row.querySelector('[data-x=publish]').addEventListener('click', async ev => {
        const btn = ev.currentTarget, w = S(row.querySelector('[name=when]').value).replace('T', ' ');
        btn.disabled = true; btn.textContent = 'Checking the facts…';
        try {
          const r = await api('POST', `/api/kalam/pieces/${encodeURIComponent(id)}/publish`, {dest: 'site', where: o.id, status: w ? 'future' : 'publish', when: w});
          if (r.status === 'blocked') { toast(S(r.say), true); btn.disabled = false; btn.textContent = 'Publish on this website…'; return; }
          const card = M(r.card);
          // her tap IS the Haan: the same card the chat shows, confirmed here
          if (!window.confirm(`${S(card.where_label)}\n\n"${S(card.title)}"\n\nPublish this post?`)) { btn.disabled = false; btn.textContent = 'Publish on this website…'; return; }
          const d = await api('POST', `/api/kalam/pieces/${encodeURIComponent(id)}/decide`, {yes: true, hash: S(card.hash)});
          toast(S(d?.say) || 'Published.'); reload();
        } catch (er) { toast(er.message, true); btn.disabled = false; btn.textContent = 'Publish on this website…'; }
      });
    });
    box.querySelectorAll('tr[data-s]').forEach(tr => {
      const slug = tr.dataset.s, act = async (body, ask) => {
        if (ask && !window.confirm(ask)) return;
        try { const r = await api('POST', `${base(o)}/blog/${encodeURIComponent(slug)}`, body); toast(S(r?.say) || 'Done.'); reload(); }
        catch (er) { toast(er.message, true); }
      };
      tr.querySelector('[data-x=hide]')?.addEventListener('click', () => act({action: 'hide'}, 'Take this post off the website? You can show it again later.'));
      tr.querySelector('[data-x=show]')?.addEventListener('click', () => act({action: 'show'}, 'Put this post back on the website?'));
      tr.querySelector('[data-x=delete]').addEventListener('click', () => act({action: 'delete'}, 'Delete this post for good? This cannot be undone.'));
      tr.querySelector('[data-x=cover]').addEventListener('change', e => act({action: 'cover', cover: e.target.value}));
    });
  }

  // ---------------------------------------------------------------- v0.366 BHASHAYEN: the site's languages
  async function loadLangs(o, root) {
    const box = root.querySelector('.stblog'); if (!box) return;
    let b;
    try { b = await api('GET', base(o) + '/blog'); } catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const have = new Set(L(b.extra)), max = N(b.max_extra) || 4;
    box.innerHTML = `<form class="stapp" data-f="langs"><b>Languages of this website</b>
        <p class="stnote">First language: <b>${esc(S(b.language))}</b>. Pick up to ${max} more - every page (and every blog post) is translated by Hoola, with a language menu on the site and the right signals for Google.</p>
        <div class="stshop-sw">${L(b.choices).map(c => `<label class="sted-kind"><input type="checkbox" name="lang" value="${esc(S(c.code))}"${have.has(c.code) ? ' checked' : ''}> ${esc(S(c.label))} <small>${esc(S(c.english))}</small></label>`).join('')}</div>
        <div class="acts"><button class="btn go" type="submit">Save languages</button></div></form>`;
    const f = box.querySelector('form');
    f.addEventListener('change', () => {
      const n = f.querySelectorAll('[name=lang]:checked').length;
      f.querySelectorAll('[name=lang]:not(:checked)').forEach(x => { x.disabled = n >= max; });
    });
    f.dispatchEvent(new Event('change'));
    f.addEventListener('submit', async e => {
      e.preventDefault(); const btn = f.querySelector('button[type=submit]');
      const langs = [...f.querySelectorAll('[name=lang]:checked')].map(x => x.value);
      btn.disabled = true;
      try { const r = await api('POST', base(o) + '/languages', {languages: langs}); toast(S(r?.say) || 'Saved.'); }
      catch (er) { toast(er.message, true); }
      btn.disabled = false;
    });
  }

  // ---------------------------------------------------------------- v0.357 DASHBOARD: her website's numbers as charts
  const DASH_DAYS = {};
  async function loadDash(o, root) {
    const box = root.querySelector('.stdash'); if (!box) return;
    const days = DASH_DAYS[o.id] || 30;
    let d;
    try { d = await api('GET', `${base(o)}/dashboard?days=${days}`); }
    catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const HC = window.HoolaChart, sr = M(d.series), dl = L(sr.days).map(x => S(x).slice(5));
    const money = v => '₹' + (HC ? HC.fmt(N(v)) : N(v));
    const kpi = k => {
      const ch = k.change_pct, v = k.money ? money(k.value) : (HC ? HC.fmt(N(k.value)) : N(k.value)) + S(k.suffix);
      const cls = ch == null ? '' : (ch >= 0 ? 'up' : 'down');
      return `<div class="stdash-kpi"><span>${esc(S(k.label))}</span><b>${esc(v)}</b><small class="${cls}">${ch == null ? (k.key === 'aov' ? '' : 'no earlier data') : (ch >= 0 ? '▲ ' : '▼ ') + Math.abs(ch) + '% vs previous ' + N(d.days) + ' days'}</small></div>`;
    };
    const card = (id, title, wide) => `<section class="stdash-card${wide ? ' wide' : ''}"><h4>${esc(title)}</h4><div data-c="${id}"></div></section>`;
    const app = M(d.app), lists = L(app.lists);
    box.innerHTML = `<div class="stdash-top"><p>${esc(S(d.say))}</p><div class="stdash-days" role="group" aria-label="Period">${[7, 30, 90, 365].map(n => `<button type="button" data-days="${n}" aria-pressed="${n === N(d.days)}">${n === 365 ? '1 year' : n + ' days'}</button>`).join('')}</div></div>
      <div class="stdash-kpis">${L(d.kpis).map(kpi).join('')}</div>
      <div class="stdash-grid">${card('visits', 'Visits a day', true)}${card('leads', 'Enquiries and bookings')}${card('pages', 'Top pages')}
        ${d.shop ? card('sales', 'Sales a day (confirmed, ₹)') + card('orders', 'Orders a day') + card('mix', 'Order status') + card('prods', 'Top products (₹)') : ''}
        ${lists.length ? card('app', 'Web app: new records a day', true) : ''}</div>
      <p class="stnote">Visits are counted by Hoola's own server (no cookies, no tracker; bots and Hoola's uptime checks are not counted). Sales count only orders you confirmed.</p>`;
    box.querySelectorAll('[data-days]').forEach(b => b.addEventListener('click', () => { DASH_DAYS[o.id] = N(b.dataset.days); loadDash(o, root); }));
    if (!HC) return;
    const put = (id, spec, empty) => {
      const el = box.querySelector(`[data-c="${id}"]`); if (!el) return;
      const any = L(spec.series).some(x => L(x.values).some(v => N(v) !== 0));
      if (!any) { el.innerHTML = `<p class="stempty">${esc(empty)}</p>`; return; }
      HC.live(el, {animate: false, ...spec});
    };
    put('visits', {type: 'area', labels: dl, series: [{name: 'This period', values: L(sr.visits)}, {name: 'Previous period', values: L(sr.visits_prev)}]}, 'No visits counted yet. Visits are counted once the site is live on its address.');
    put('leads', {type: 'bar', labels: dl, series: [{name: 'Enquiries', values: L(sr.enquiries)}, {name: 'Bookings', values: L(sr.bookings)}]}, 'No enquiries or bookings in this period.');
    const tp = L(d.top_pages);
    put('pages', {type: 'hbar', labels: tp.map(x => S(x[0])), series: [{name: 'Visits', values: tp.map(x => N(x[1]))}]}, 'No page visits yet.');
    if (d.shop) {
      put('sales', {type: 'bar', labels: dl, unit: '₹', series: [{name: 'Sales', values: L(sr.sales)}]}, 'No confirmed sales in this period.');
      put('orders', {type: 'line', labels: dl, series: [{name: 'Orders', values: L(sr.orders)}]}, 'No orders in this period.');
      const mx = L(d.status_mix);
      put('mix', {type: 'donut', labels: mx.map(x => S(x[0])), series: [{name: 'Orders', values: mx.map(x => N(x[1]))}], totalLabel: 'orders'}, 'No orders in this period.');
      const pr = L(d.top_products);
      put('prods', {type: 'hbar', unit: '₹', labels: pr.map(x => `${S(x[0])} × ${N(x[1])}`), series: [{name: 'Sales', values: pr.map(x => N(x[2]))}]}, 'No confirmed sales yet.');
    }
    if (lists.length) put('app', {type: 'line', labels: dl, series: lists.slice(0, 6).map(x => ({name: S(x.label), values: L(x.days)}))}, 'No new records in this period.');
  }

  /* v0.446 DUKAAN PAISA: her own gateway (keys typed HERE only, sealed, shown nowhere), payments, coupons, reviews */
  async function payBox(o, box, info, reload) {
    const on = M(info.online), sec = document.createElement('section'); sec.className = 'stcol stpay';
    box.prepend(sec);
    if (!on.app) {
      sec.innerHTML = `<h4>Online payments <span>off</span></h4><p class="stnote">Take card / UPI / netbanking through YOUR own Razorpay, Cashfree or PhonePe account. Orders are marked paid only when the gateway confirms.</p><div class="acts"><button class="btn go" type="button" data-p="connect">Set up online payments</button></div>`;
      sec.querySelector('[data-p=connect]').onclick = async e => { e.target.disabled = true; try { await api('POST', base(o) + '/payments/connect'); reload(); } catch (er) { toast(er.message, true); e.target.disabled = false; } };
      return;
    }
    const A = `/api/apps/${encodeURIComponent(S(on.app))}`;
    let st = {}, cps = {}, rv = [];
    try { [st, cps, rv] = await Promise.all([api('GET', A + '/pay'), api('GET', A + '/coupons').catch(() => ({})), api('GET', base(o) + '/shop/reviews').then(j => L(j.reviews)).catch(() => [])]); } catch (er) { sec.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const F = M(st.fields), gw = S(st.gateway) || 'razorpay';
    const codes = L(M(cps).coupons || (Array.isArray(cps) ? cps : []));
    sec.innerHTML = `<h4>Online payments <span>${st.on ? esc(S(st.gateway)) + (st.test ? ' · test mode' : ' · live') : 'not connected'}</span></h4>
      ${st.on ? `<p class="stnote">Webhook address for your ${esc(S(st.gateway))} dashboard: <code>${esc(S(st.webhook_url))}</code><br>${esc(S(st.webhook_how))}</p>
        <p class="stnote">${N(M(st.totals).count)} paid · ${esc(S(M(st.totals).paid))} paise received · ${N(M(st.totals).mismatch)} amount mismatches</p>` : ''}
      <form class="stapp" data-p="keys" autocomplete="off"><b>${st.on ? 'Change gateway keys' : 'Connect your gateway'}</b>
        <label><span>Gateway</span><select name="gateway">${L(st.gateways).map(g => `<option${g === gw ? ' selected' : ''}>${esc(S(g))}</option>`).join('')}</select></label>
        <div class="row">${L(F[gw]).map(k => `<label><span>${esc(S(k))}</span><input name="k_${esc(S(k))}" type="password" autocomplete="off"></label>`).join('')}</div>
        <label class="sted-kind"><input type="checkbox" name="test"> Test mode</label>
        <div class="acts"><button class="btn go" type="submit">Check and save</button></div></form>
      <h4 style="margin-top:12px">Coupons <span>${codes.length}</span></h4>
      ${codes.length ? `<ul class="stmems">${codes.map(c => `<li><span>${esc(S(c.code))} · ${c.kind === 'flat' ? '₹' + esc(S(c.value)) : esc(S(c.value)) + '%'} off${c.min ? ' · min ₹' + esc(S(c.min)) : ''}${c.until ? ' · till ' + esc(S(c.until)) : ''} · used ${N(c.used)}</span></li>`).join('')}</ul>` : '<p class="stempty">No codes yet.</p>'}
      <form class="stapp" data-p="coupon" autocomplete="off"><div class="row"><label><span>Code</span><input name="code" placeholder="DIWALI10" maxlength="16"></label>
        <label><span>Kind</span><select name="kind"><option value="percent">% off</option><option value="flat">₹ off</option></select></label>
        <label><span>Value</span><input name="value" inputmode="decimal"></label><label><span>Min order ₹</span><input name="min" inputmode="decimal"></label>
        <label><span>Last date</span><input name="until" type="date"></label></div>
        <label class="sted-kind"><input type="checkbox" name="once" checked> Once per customer</label>
        <div class="acts"><button class="btn soft" type="submit">Add coupon</button></div></form>
      <h4 style="margin-top:12px">Reviews (verified buyers) <span>${rv.length}</span></h4>
      ${rv.length ? `<ul class="stmems">${rv.map(r => `<li data-r="${esc(S(r.id))}"><span>${'★'.repeat(N(r.stars))} ${esc(S(r.slug))} · ${esc(S(r.name))}: ${esc(S(r.text))}</span><button class="btn soft" type="button" data-hide="${r.status === 'hidden' ? '0' : '1'}">${r.status === 'hidden' ? 'Show' : 'Hide'}</button></li>`).join('')}</ul>` : '<p class="stempty">No reviews yet.</p>'}`;
    const kf = sec.querySelector('[data-p=keys]');
    kf.gateway.onchange = () => { const g = kf.gateway.value; kf.querySelector('.row').innerHTML = L(F[g]).map(k => `<label><span>${esc(S(k))}</span><input name="k_${esc(S(k))}" type="password" autocomplete="off"></label>`).join(''); };
    kf.onsubmit = async e => {
      e.preventDefault(); const keys = {}; [...kf.querySelectorAll('input[name^=k_]')].forEach(i => { keys[i.name.slice(2)] = i.value.trim(); });
      const b = kf.querySelector('button'); b.disabled = true;
      try { await api('PUT', A + '/pay/keys', {gateway: kf.gateway.value, keys, test: kf.test.checked}); toast('Gateway connected. Add the webhook address in its dashboard.'); reload(); }
      catch (er) { toast(er.message, true); b.disabled = false; } finally { [...kf.querySelectorAll('input[type=password]')].forEach(i => { i.value = ''; }); }
    };
    sec.querySelector('[data-p=coupon]').onsubmit = async e => {
      e.preventDefault(); const f = e.target, b = {code: f.code.value, kind: f.kind.value, value: f.value.value, once: f.once.checked};
      if (f.min.value) b.min = f.min.value; if (f.until.value) b.until = f.until.value;
      try { await api('PUT', A + '/coupons', b); toast('Coupon saved.'); reload(); } catch (er) { toast(er.message, true); }
    };
    sec.onclick = async e => {
      const h = e.target.closest('[data-hide]'), li = e.target.closest('li[data-r]'); if (!h || !li) return;
      try { await api('POST', base(o) + '/shop/reviews/' + encodeURIComponent(li.dataset.r), {hide: h.dataset.hide === '1'}); reload(); } catch (er) { toast(er.message, true); }
    };
  }

  /* v0.452 DUKAAN PLUS: sellers (her approval, commission, Route account), product approvals, Shiprocket, cart reminders */
  async function plusBox(o, box, reload, info) {
    let vs = {}, cr = {}, ca = {};
    try { [vs, cr, ca] = await Promise.all([api('GET', base(o) + '/shop/vendors'), api('GET', base(o) + '/shop/courier'), api('GET', base(o) + '/shop/carts')]); } catch (er) { return; }
    const sec = document.createElement('section'); sec.className = 'stcol';
    sec.innerHTML = `<h4>Sellers (marketplace) <span>${L(vs.vendors).length}</span></h4>
      <p class="stnote">Sellers apply at <code>/api/site-shop/…/seller</code> (link it from your site). You approve each seller and each of their products; their share goes through Razorpay Route.</p>
      ${L(vs.vendors).length ? `<div class="sttbl"><table><thead><tr><th>Seller</th><th>Status</th><th>Commission %</th><th>Route account</th><th></th></tr></thead><tbody>${L(vs.vendors).map(v => `<tr data-v="${esc(S(v.id))}"><td>${esc(S(v.name))}<br><small>${esc(S(v.phone))}${v.gstin ? ' · ' + esc(S(v.gstin)) : ''}</small></td><td>${esc(S(v.status))}${v.portal ? `<br><small>seller link: ?k=${esc(S(v.portal))}</small>` : ''}</td>
        <td><input name="commission" value="${N(v.commission)}" inputmode="numeric" aria-label="Commission"></td><td><input name="account" value="${esc(S(v.account))}" placeholder="acc_…" aria-label="Route account"></td>
        <td><button class="btn soft" type="button" data-vs="approved">Approve / save</button> <button class="btn soft" type="button" data-vs="blocked">Block</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No sellers yet.</p>'}
      ${L(vs.pending_products).length ? `<h4 style="margin-top:12px">Products waiting for you</h4><ul class="stmems">${L(vs.pending_products).map(p => `<li data-ps="${esc(S(p.slug))}"><span>${esc(S(p.title))} · ${esc(S(p.price))}</span><span><button class="btn soft" type="button" data-pok="1">Approve</button> <button class="btn soft" type="button" data-pok="0">Reject</button></span></li>`).join('')}</ul>` : ''}
      <h4 style="margin-top:12px">GST bills <span>${M(info?.online).app ? 'your one invoice series (website + app)' : 'set up online payments / the app link first'}</span></h4>
      ${M(info?.online).app ? `<form class="stapp" data-c="gst" autocomplete="off"><div class="row"><label><span>Your GSTIN</span><input name="gstin" maxlength="15"></label><label><span>Legal name</span><input name="legal_name"></label></div><div class="acts"><button class="btn soft" type="submit">Save GST details</button></div></form>` : ''}
      <h4 style="margin-top:12px">Courier <span>${cr.on ? 'Shiprocket · pickup ' + esc(S(cr.pickup)) : 'not connected'}</span></h4>
      <form class="stapp" data-c="courier" autocomplete="off"><div class="row"><label><span>Shiprocket API user email</span><input name="email" type="email"></label><label><span>API user password</span><input name="password" type="password" autocomplete="off"></label>
        <label><span>Pickup nickname</span><input name="pickup" value="${esc(S(cr.pickup || 'Primary'))}"></label><label><span>Parcel kg</span><input name="weight" value="${esc(S(cr.weight || '0.5'))}" inputmode="decimal"></label></div>
        <div class="acts"><button class="btn soft" type="submit">${cr.on ? 'Change' : 'Connect Shiprocket'}</button></div></form>
      <h4 style="margin-top:12px">Carts to remind <span>${L(ca.carts).length}</span></h4><p class="stnote">${esc(S(ca.note))}</p>
      ${L(ca.carts).length ? `<ul class="stmems">${L(ca.carts).map(c => `<li data-cart="${esc(S(c.id))}"><span>${esc(S(c.name))} ${esc(S(c.phone))} · ${esc(S(c.items))}</span><a class="btn soft" target="_blank" rel="noopener" href="${esc(S(c.wa))}" data-sent>Send on WhatsApp</a></li>`).join('')}</ul>` : ''}`;
    box.appendChild(sec);
    sec.onclick = async e => {
      const vb = e.target.closest('[data-vs]'), tr = e.target.closest('tr[data-v]');
      if (vb && tr) { try { await api('POST', base(o) + '/shop/vendors/' + encodeURIComponent(tr.dataset.v), {status: vb.dataset.vs, commission: tr.querySelector('[name=commission]').value, account: tr.querySelector('[name=account]').value.trim()}); reload(); } catch (er) { toast(er.message, true); } return; }
      const pb = e.target.closest('[data-pok]'), li = e.target.closest('li[data-ps]');
      if (pb && li) { try { await api('POST', base(o) + '/shop/products/' + encodeURIComponent(li.dataset.ps) + '/approve', {ok: pb.dataset.pok === '1'}); reload(); } catch (er) { toast(er.message, true); } return; }
      const sent = e.target.closest('[data-sent]'), cl = e.target.closest('li[data-cart]');
      if (sent && cl) { api('POST', base(o) + '/shop/carts/' + encodeURIComponent(cl.dataset.cart) + '/reminded').then(reload).catch(() => {}); }
    };
    const gf = sec.querySelector('[data-c=gst]');
    if (gf) gf.onsubmit = async e => {
      e.preventDefault();
      try { await api('PUT', `/api/apps/${encodeURIComponent(S(M(info.online).app))}/gst`, {gstin: gf.gstin.value.trim(), legal_name: gf.legal_name.value.trim()}); toast('GST details saved.'); }
      catch (er) { toast(er.message, true); }
    };
    sec.querySelector('[data-c=courier]').onsubmit = async e => {
      e.preventDefault(); const f = e.target, b = f.querySelector('button'); b.disabled = true;
      try { await api('PUT', base(o) + '/shop/courier', {email: f.email.value, password: f.password.value, pickup: f.pickup.value, weight: f.weight.value}); toast('Shiprocket connected.'); reload(); }
      catch (er) { toast(er.message, true); b.disabled = false; } finally { f.password.value = ''; }
    };
  }

  async function loadShop(o, root) {
    const box = root.querySelector('.stshop'); if (!box) return;
    let info, ord;
    try { [info, ord] = await Promise.all([api('GET', base(o) + '/shop'), api('GET', base(o) + '/shop/orders')]); }
    catch (er) { box.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const st = M(info.settings), sm = M(ord.summary), prods = L(info.products), orders = L(ord.orders);
    const num = v => S(v).replace(/[₹,]/g, '');
    box.innerHTML = `<form class="stapp" data-f="settings" autocomplete="off"><b>Shop settings</b>
        <div class="stshop-sw">${[['on', 'Shop on'], ['cod', 'Cash on delivery'], ['pickup', 'Store pickup']].map(([k, n]) => `<label class="sted-kind"><input type="checkbox" name="${k}"${st[k] ? ' checked' : ''}> ${n}</label>`).join('')}</div>
        <div class="row"><label><span>Delivery charge ₹</span><input name="delivery" value="${esc(num(st.delivery))}" inputmode="decimal"></label>
        <label><span>Free delivery above ₹</span><input name="free_above" value="${esc(num(st.free_above))}" inputmode="decimal"></label>
        <label><span>Minimum order ₹</span><input name="min_order" value="${esc(num(st.min_order))}" inputmode="decimal"></label></div>
        <label><span>Her UPI ID (customers pay here)</span><input name="upi" value="${esc(S(info.upi))}" placeholder="name@okhdfcbank"></label>
        <label><span>Delivery pincodes (empty = all)</span><input name="pincodes" value="${esc(L(st.pincodes).join(', '))}" placeholder="444101, 444102"></label>
        <div class="acts"><button class="btn go" type="submit">Save settings</button></div></form>
      <p class="stnote">${N(sm.orders)} orders · ${N(sm.open)} open · ${N(sm.to_check)} payments to check · sales ${esc(S(sm.sales) || '₹0')}</p>
      <section class="stcol"><h4>Orders <span>${orders.length}</span></h4>${orders.length ? `<div class="sttbl"><table><thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Total</th><th>Status</th><th></th></tr></thead><tbody>${orders.map(x => `<tr data-n="${esc(S(x.number))}">
        <td><b>${esc(S(x.number))}</b><br><small>${esc(S(x.created).slice(0, 16).replace('T', ' '))}</small></td>
        <td>${esc(S(x.name))}<br><small>${esc(S(x.phone))} · ${esc(S(x.address).slice(0, 60))} ${esc(S(x.pincode))}</small></td>
        <td>${L(x.items).map(i => `${esc(S(i.title))} × ${N(i.qty)}`).join('<br>')}</td>
        <td>${esc(S(x.total))}${x.discount ? `<br><small>${esc(S(x.coupon))} −${esc(S(x.discount))}</small>` : ''}<br><small>${x.method === 'cod' ? 'COD' : x.method === 'online' ? (x.paid_online ? 'Online · paid (gateway)' : 'Online · not paid yet') : 'UPI'}${x.utr ? ' · ' + (x.method === 'online' ? 'pay ' : 'UTR ') + esc(S(x.utr)) : ''}</small>${x.paid_online ? `<br><button class="btn soft" type="button" data-refund="${esc(S(x.number))}">Refund…</button>` : ''}
        ${['confirmed', 'packed', 'shipped', 'delivered', 'cancelled'].includes(S(x.status)) ? `<br><button class="btn soft" type="button" data-inv="${esc(S(x.number))}" data-doc="${x.status === 'cancelled' ? 'credit' : ''}">${x.status === 'cancelled' ? 'Credit note' : 'GST bill'}</button>` : ''}
        ${['confirmed', 'packed'].includes(S(x.status)) ? `<button class="btn soft" type="button" data-ship="${esc(S(x.number))}">Ship (Shiprocket)</button>` : ''}</td>
        <td>${esc(S(x.status_text))}</td>
        <td>${L(x.next).map(t => `<button class="btn soft" type="button" data-to="${esc(S(t))}">${esc(OSTEP[t] || t)}</button>`).join(' ')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No orders yet.</p>'}</section>
      <section class="stcol"><h4>Products <span>${prods.length}</span></h4>
        <div class="sttbl"><table><thead><tr><th>Name</th><th>Price ₹</th><th>Unit</th><th>Stock (empty = not counted)</th><th>On sale</th></tr></thead><tbody>
        ${prods.map(p => `<tr data-s="${esc(S(p.slug))}"><td><input name="title" value="${esc(S(p.title))}" aria-label="Name"></td><td><input name="price" value="${esc(num(p.price_text))}" inputmode="decimal" aria-label="Price"></td>
          <td><input name="unit" value="${esc(S(p.unit))}" aria-label="Unit"></td><td><input name="stock" value="${p.stock == null ? '' : N(p.stock)}" inputmode="numeric" aria-label="Stock"></td>
          <td><input type="checkbox" name="active"${p.active ? ' checked' : ''} aria-label="On sale"></td></tr>`).join('')}
        <tr data-s=""><td><input name="title" placeholder="New product" aria-label="New product name"></td><td><input name="price" inputmode="decimal" aria-label="Price"></td><td><input name="unit" placeholder="1 kg" aria-label="Unit"></td><td><input name="stock" inputmode="numeric" aria-label="Stock"></td><td><input type="checkbox" name="active" checked aria-label="On sale"></td></tr>
        </tbody></table></div>
        <div class="acts"><button class="btn go" type="button" data-x="save-products">Save products</button>${N(info.from_lists) ? `<button class="btn soft" type="button" data-x="from-lists">Add my priced list items (${N(info.from_lists)})</button>` : ''}</div></section>`;
    const send = async (body, b) => { if (b) b.disabled = true; try { const r = await api('POST', base(o) + '/shop', body); toast(S(r?.say) || 'Saved.'); loadShop(o, root); } catch (er) { toast(er.message, true); if (b) b.disabled = false; } };
    box.querySelector('[data-f=settings]').addEventListener('submit', e => {
      e.preventDefault(); const f = new FormData(e.target), settings = {};
      ['on', 'cod', 'pickup'].forEach(k => { settings[k] = !!f.get(k); });
      ['delivery', 'free_above', 'min_order', 'pincodes'].forEach(k => { settings[k] = S(f.get(k)).trim(); });
      if (S(f.get('upi')).trim()) settings.upi = S(f.get('upi')).trim();
      send({settings}, e.target.querySelector('button'));
    });
    box.querySelector('[data-x=save-products]').addEventListener('click', e => {
      const products = [...box.querySelectorAll('tr[data-s]')].map(tr => {
        const g = n => tr.querySelector(`[name=${n}]`);
        const row = {title: g('title').value.trim(), price: g('price').value.trim(), unit: g('unit').value.trim(), active: g('active').checked,
                     stock: g('stock').value.trim() === '' ? null : g('stock').value.trim()};
        if (tr.dataset.s) row.slug = tr.dataset.s;
        return row;
      }).filter(r => r.slug || (r.title && r.price));
      send({products}, e.target);
    });
    const fl = box.querySelector('[data-x=from-lists]'); if (fl) fl.addEventListener('click', e => send({from_lists: true}, e.target));
    payBox(o, box, info, () => loadShop(o, root));
    plusBox(o, box, () => loadShop(o, root), info);
    box.addEventListener('click', async e => {
      const iv = e.target.closest('[data-inv]');
      if (iv) {                                          // v0.452 her GST bill / credit note (her one series)
        try { const r = await api('GET', `${base(o)}/shop/orders/${encodeURIComponent(iv.dataset.inv)}/invoice${iv.dataset.doc ? '?doc=credit' : ''}`, undefined, {raw: true});
          window.open(URL.createObjectURL(await r.blob()), '_blank', 'noopener'); } catch (er) { toast(er.message, true); }
        return;
      }
      const sh = e.target.closest('[data-ship]');
      if (sh) {
        if (!confirm(`Book Shiprocket pickup for ${sh.dataset.ship}? Shiprocket charges your wallet.`)) return;
        sh.disabled = true;
        try { const r = await api('POST', `${base(o)}/shop/orders/${encodeURIComponent(sh.dataset.ship)}/ship`); toast(`AWB ${S(r.awb)} (${S(r.courier)})`); if (r.label) window.open(r.label, '_blank', 'noopener'); loadShop(o, root); }
        catch (er) { toast(er.message, true); sh.disabled = false; }
        return;
      }
      const rf = e.target.closest('[data-refund]');
      if (rf) {                                          // v0.446 HER tap: the gateway's own refund for an online order
        const amt = prompt(`Refund order ${rf.dataset.refund}: amount in ₹ (leave empty = the full amount left)`, '');
        if (amt === null || !confirm(`Refund ${amt ? '₹' + amt : 'the full amount'} for ${rf.dataset.refund} through your gateway?`)) return;
        rf.disabled = true;
        try { const r = await api('POST', `${base(o)}/shop/orders/${encodeURIComponent(rf.dataset.refund)}/refund`, {amount: amt || null, why: 'refund'}); toast('Refund ' + S(r?.status || 'sent') + '.'); loadShop(o, root); }
        catch (er) { toast(er.message, true); rf.disabled = false; }
        return;
      }
      const b = e.target.closest('[data-to]'), tr = e.target.closest('tr[data-n]'); if (!b || !tr) return;
      if (b.dataset.to === 'cancelled' && !confirm(`Cancel order ${tr.dataset.n}? Its stock goes back.`)) return;
      if (b.dataset.to === 'confirmed' && !confirm(`Did you see the money for ${tr.dataset.n} in your bank / UPI app?`)) return;
      b.disabled = true;
      try { const r = await api('POST', `${base(o)}/shop/orders/${encodeURIComponent(tr.dataset.n)}`, {to: b.dataset.to}); toast(S(r?.say) || 'Updated.'); loadShop(o, root); }
      catch (er) { toast(er.message, true); b.disabled = false; }
    });
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
      <div class="acts"><button class="btn soft" type="button" data-x="react">Export as React project</button>${cols.length ? '<button class="btn soft" type="button" data-x="phone">Make phone app (same data)</button>' : ''}</div>`;
    box.innerHTML = design + (info.linked ? `<section class="stlogic" aria-label="Logic"></section>` : '') + (cols.length ? `<p class="stnote">${N(counts.members)} members · ${cols.map(c => `${esc(S(c.label))}: ${N(counts[c.key])}`).join(' · ')}</p><div class="stcols"></div><div class="stmem"></div>` : '');
    box.querySelector('.stapp').addEventListener('submit', async e => {
      e.preventDefault(); const w = box.querySelector('#stApp').value.trim(); if (!w) return;
      const b = e.target.querySelector('button'); b.disabled = true;
      try { const r = await api('POST', base(o) + '/app-design', {words: w, conversation_id: C.conv() || ''}); toast(S(r?.say) || 'App updated.'); loadData(o, root); }
      catch (er) { toast(er.message, true); b.disabled = false; }
    });
    const ph = box.querySelector('[data-x=phone]');
    if (ph) ph.addEventListener('click', async e => {
      if (!confirm('Plan an Android / iPhone app on the same data as this website? Nothing is built until you say Haan on its plan card.')) return;
      e.target.disabled = true;
      try { const r = await api('POST', base(o) + '/phone-app', {conversation_id: C.conv() || ''}); toast(S(r?.say) || 'Phone app plan ready.'); }
      catch (er) { toast(er.message, true); e.target.disabled = false; }
    });
    box.querySelector('[data-x=react]').addEventListener('click', async e => {
      e.target.disabled = true;
      try { const r = await api('POST', base(o) + '/export', {format: 'react'}); toast(S(r?.say) || 'React project ready.'); if (r?.file_id) C.say && toast('The ZIP is in your files: ' + S(r.name)); }
      catch (er) { toast(er.message, true); } finally { e.target.disabled = false; }
    });
    if (info.linked) logicBox(o, box.querySelector('.stlogic'), M(info.linked), () => loadData(o, root));
    if (info.linked) auditBox(o, box);
    catalogBox(o, box);
    if (info.linked) liveBox(o, box, M(info.linked), S(info.site_id), S(info.api));
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

  /* v0.407 EK DIMAAG: the linked app's logic - what runs now, the draft waiting for her tap, approvals waiting */
  async function logicBox(o, el, link, reload) {
    if (!el) return;
    let v;
    try { v = await api('GET', base(o) + '/logic'); } catch (er) { el.innerHTML = `<p class="stempty">${esc(er.message)}</p>`; return; }
    const d = v.draft ? M(v.draft) : null;
    el.innerHTML = `<h4>Logic <span>app ${esc(S(link.number))}${v.rev ? ' · rev ' + esc(S(v.rev)) : ''}</span></h4>`
      + (L(v.summary).length ? L(v.summary).slice(0, 12).map(x => `<div class="bln faint">• ${esc(S(x))}</div>`).join('') : '<p class="stempty">No rules yet. Say what should happen in "Change the app" above.</p>')
      + (d ? `<div class="stdraft"><b>Draft waiting for you</b>${L(d.lines).slice(0, 14).map(x => `<div class="bln">• ${esc(S(x))}</div>`).join('')}
          ${L(d.errors).slice(0, 4).map(x => `<div class="badc bln">${esc(S(x))}</div>`).join('')}
          ${L(d.errors).length ? '' : `<div class="acts"><button class="btn go" type="button" data-lg="apply">Apply this logic</button></div>`}</div>` : '')
      + (L(v.approvals).length ? `<div class="bln"><b>${L(v.approvals).length} approval(s) waiting</b> - staff decide them at /admin/.</div>` : '');
    const ap = el.querySelector('[data-lg=apply]');
    if (ap) ap.addEventListener('click', async () => {
      if (!confirm('Apply this logic to the live website and its app? Old entries are recalculated; nothing is deleted.')) return;
      ap.disabled = true;
      try { const r = await api('POST', base(o) + '/logic/apply', {hash: S(d.hash)}); toast(S(r?.say) || 'Applied.'); reload(); }
      catch (er) { toast(er.message, true); ap.disabled = false; }
    });
  }

  /* v0.434 who changed what (every change to the app's data, with the person) + who may do what */
  async function auditBox(o, box) {
    let v; try { v = await api('GET', base(o) + '/audit?limit=60'); } catch (er) { return; }
    const sec = document.createElement('section'); sec.className = 'stlogic';
    sec.innerHTML = `<h4>Who changed what <span>last ${L(v.audit).length}</span></h4>`
      + (L(v.audit).length ? `<div class="sttbl"><table><thead><tr><th>When</th><th>Who</th><th>List</th><th>Change</th><th>Fields</th></tr></thead><tbody>${L(v.audit).map(a => `<tr><td>${esc(new Date(S(a.at)).toLocaleString())}</td><td>${esc(S(a.by))}</td><td>${esc(S(a.list))}</td><td>${esc(S(a.op))}</td><td>${esc(L(a.fields).join(', '))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="stempty">No changes yet.</p>')
      + `<h4 style="margin-top:12px">Who can do what</h4><div class="sttbl"><table><thead><tr><th>List</th><th>Add</th><th>See</th><th>Change</th><th>Delete</th><th>Only staff see</th></tr></thead><tbody>${L(v.matrix).map(m => `<tr><td>${esc(S(m.label))}</td><td>${esc(S(m.create))}</td><td>${esc(S(m.read))}</td><td>${esc(S(m.update))}</td><td>${esc(S(m['delete']))}</td><td>${esc(L(m.staff_see).join(', '))}</td></tr>`).join('')}</tbody></table></div>`
      + `<p class="stnote">Mobile OTP login: ${v.otp ? 'on' : 'off (needs an SMS provider on the server)'}</p>`;
    box.appendChild(sec);
  }

  /* v0.459 ABHI ABHI WEBSITE: live chat (her reply = her tap), the clinic queue, browser notifications, connectors */
  async function liveBox(o, box, link, siteId, apiBase) {
    const A = `/api/apps/${encodeURIComponent(S(link.app))}`;
    let q = {}, ch = {}, cn = {}, pu = {};
    try { [q, ch, cn, pu] = await Promise.all([api('GET', A + '/queue'), api('GET', A + '/chat'), api('GET', A + '/connect'), api('GET', A + '/push').catch(() => ({}))]); }
    catch (er) { return; }
    const st = M(q.settings), bd = M(q.board), host = S(apiBase).replace(/\/api\/site-app\/.*$/, '');
    const boardUrl = `${host}/api/site-app/${encodeURIComponent(siteId)}/queue/board`;
    const sec = document.createElement('section'); sec.className = 'stlogic';
    const packs = L(cn.packs).filter(p => !p.no_actions);
    sec.innerHTML = `<h4>Live <span>${N(pu.browsers)} browser(s) said yes to notifications</span></h4>
      <p class="stnote">Signed-in visitors see changes as they happen (orders, tickets, dashboards), can message your team and get browser notifications only after they tap "Notify me".</p>
      <h4 style="margin-top:12px">Messages <span>${N(ch.unread)} new</span></h4>
      ${L(ch.threads).length ? `<ul class="stmems">${L(ch.threads).slice(0, 20).map(t => `<li data-th="${esc(S(t.member))}"><span><b>${esc(S(t.name))}</b>${t.unread ? ' (' + N(t.unread) + ')' : ''} · ${esc(S(t.last))}</span><span class="row"><input aria-label="Reply" placeholder="Reply…"><button class="btn soft" type="button" data-rep>Send</button></span></li>`).join('')}</ul>` : '<p class="stempty">No messages yet.</p>'}
      <h4 style="margin-top:12px">Queue <span>${st.on ? (bd.now != null ? 'now serving ' + N(bd.now) + ' · ' : '') + N(bd.waiting) + ' waiting' : 'off'}</span></h4>
      <form class="stapp" data-q="cfg" autocomplete="off"><div class="row">
        <label><input type="checkbox" name="on"${st.on ? ' checked' : ''}> Queue on</label><label><span>Name</span><input name="label" value="${esc(S(st.label))}"></label>
        <label><input type="checkbox" name="self_take"${st.self_take ? ' checked' : ''}> Patients take tokens on the site</label><label><input type="checkbox" name="open"${st.open ? ' checked' : ''}> Open today</label>
        <label><span>Minutes each</span><input name="avg_min" value="${N(st.avg_min)}" inputmode="numeric"></label><label><span>Tell when this many are ahead</span><input name="near" value="${N(st.near)}" inputmode="numeric"></label></div>
        <div class="acts"><button class="btn soft" type="submit">Save queue</button>${st.on ? `<a class="btn soft" target="_blank" rel="noopener" href="${esc(boardUrl)}">Open TV board</a><button class="btn go" type="button" data-q="next">Call next</button>` : ''}</div></form>
      ${st.on ? `<form class="stapp" data-q="add" autocomplete="off"><div class="row"><label><span>Walk-in name</span><input name="name"></label><label><span>Mobile (for the SMS)</span><input name="phone" inputmode="numeric" maxlength="10"></label></div><div class="acts"><button class="btn soft" type="submit">Add token</button></div></form>
        ${L(q.tokens).length ? `<div class="sttbl"><table><thead><tr><th>Token</th><th>Name</th><th>Status</th><th>Told</th></tr></thead><tbody>${L(q.tokens).map(k => `<tr><td>${N(k.token)}</td><td>${esc(S(k.name))}</td><td>${esc(S(k.status))}</td><td>${k.near_sent ? 'yes' : ''}</td></tr>`).join('')}</tbody></table></div>` : ''}` : ''}
      <h4 style="margin-top:12px">Connectors <span>${L(cn.actions).length} action(s)</span></h4>
      <p class="stnote">Each action does nothing until you approve it; a change needs approving again. Keys are sealed and never shown again. SMS / WhatsApp use your own DLT / approved templates.</p>
      ${L(cn.actions).length ? `<ul class="stmems">${L(cn.actions).map(a => `<li data-ak="${esc(S(a.key))}"><span><b>${esc(S(a.label))}</b> · ${esc(S(M(a.leaves).when))} · to ${esc(S(M(a.leaves).host))}${L(M(a.leaves).fields).length ? ' · sends ' + esc(L(M(a.leaves).fields).join(', ')) : ''}</span>
        <span>${a.approved ? '<em>approved</em>' : '<button class="btn go" type="button" data-ok>Approve</button>'} <button class="btn soft" type="button" data-rm>Remove</button></span></li>`).join('')}</ul>` : ''}
      <form class="stapp" data-c="pack" autocomplete="off"><div class="row"><label><span>Add a ready pack</span><select name="pack">${packs.map(p => `<option value="${esc(S(p.key))}">${esc(S(p.group))}: ${esc(S(p.label))}</option>`).join('')}</select></label></div><div class="stpk"></div><div class="acts"><button class="btn soft" type="submit">Add (waits for your approval)</button></div></form>
      ${L(cn.runs).length ? `<div class="sttbl"><table><thead><tr><th>When</th><th>Action</th><th>Why</th><th>Result</th></tr></thead><tbody>${L(cn.runs).slice(0, 12).map(r => `<tr><td>${esc(new Date(S(r.at)).toLocaleString())}</td><td>${esc(S(r.action))}</td><td>${esc(S(r.trigger))}</td><td>${esc(S(r.status))} ${esc(S(r.note))}</td></tr>`).join('')}</tbody></table></div>` : ''}
      ${L(cn.hooks).length ? `<p class="stnote">Incoming (signed) webhooks: ${L(cn.hooks).map(h => `<code>${esc(host)}/api/site-app/${esc(siteId)}/hook/${esc(S(h.key))}</code>`).join(' · ')}</p>` : ''}`;
    box.appendChild(sec);
    const reload = () => { sec.remove(); liveBox(o, box, link, siteId, apiBase); };
    const pf = sec.querySelector('[data-c=pack]'), pk = sec.querySelector('.stpk');
    const fields = () => { const p = packs.find(x => S(x.key) === pf.pack.value); if (!p) return;
      pk.innerHTML = `<p class="stnote">${esc(S(p.note))}</p><div class="row">${Object.entries(M(p.settings)).map(([k, v]) => `<label><span>${esc(k)}</span><input data-set="${esc(k)}" value="${esc(S(v))}"></label>`).join('')}
        ${L(p.secrets).map(k => `<label><span>${esc(k)} (sealed)</span><input type="password" autocomplete="off" data-sec="${esc(k)}"></label>`).join('')}</div>`; };
    if (pf) { pf.pack.onchange = fields; fields();
      pf.onsubmit = async e => { e.preventDefault(); const settings = {}, secrets = {};
        pk.querySelectorAll('[data-set]').forEach(i => { settings[i.dataset.set] = i.value.trim(); });
        pk.querySelectorAll('[data-sec]').forEach(i => { if (i.value) secrets[i.dataset.sec] = i.value; });
        try { const r = await api('POST', A + '/connect/pack', {pack: pf.pack.value, settings, secrets}); toast(L(r.problems).length ? L(r.problems).join(' · ') : 'Added. Approve it to switch it on.', L(r.problems).length > 0); reload(); }
        catch (er) { toast(er.message, true); } }; }
    const qf = sec.querySelector('[data-q=cfg]');
    qf.onsubmit = async e => { e.preventDefault();
      try { await api('PUT', A + '/queue', {on: qf.on.checked, label: qf.label.value, self_take: qf.self_take.checked, open: qf.open.checked, avg_min: qf.avg_min.value, near: qf.near.value}); toast('Queue saved.'); reload(); }
      catch (er) { toast(er.message, true); } };
    const af = sec.querySelector('[data-q=add]');
    if (af) af.onsubmit = async e => { e.preventDefault(); try { await api('POST', A + '/queue/add', {name: af.name.value, phone: af.phone.value}); reload(); } catch (er) { toast(er.message, true); } };
    sec.onclick = async e => {
      if (e.target.closest('[data-q=next]')) { try { await api('POST', A + '/queue/call', {}); reload(); } catch (er) { toast(er.message, true); } return; }
      const li = e.target.closest('li[data-ak]');
      if (li && e.target.closest('[data-ok]')) {
        if (!confirm('Switch this action on? It will send the listed fields to the listed address whenever its moment comes.')) return;
        try { await api('POST', A + '/connect/actions/' + encodeURIComponent(li.dataset.ak) + '/approve', {her_tap: true}); reload(); } catch (er) { toast(er.message, true); } return; }
      if (li && e.target.closest('[data-rm]')) { if (!confirm('Remove this action?')) return; try { await api('DELETE', A + '/connect/actions/' + encodeURIComponent(li.dataset.ak)); reload(); } catch (er) { toast(er.message, true); } return; }
      const th = e.target.closest('li[data-th]');
      if (th && e.target.closest('[data-rep]')) { const inp = th.querySelector('input'), v = inp.value.trim(); if (!v) return;
        try { await api('POST', A + '/chat/' + encodeURIComponent(th.dataset.th), {text: v, her_tap: true}); toast('Sent.'); reload(); } catch (er) { toast(er.message, true); } }
    };
  }

  /* v0.531 BADA CATALOGUE: her products / doctors / properties from her file, Google Sheet or a dataset -> pages by code.
     Preview first (nothing written, every count + rejected row shown), then her Apply tap writes it. */
  async function catalogBox(o, box) {
    let v; try { v = await api('GET', base(o) + '/catalog'); } catch (er) { return; }
    const sec = document.createElement('section'); sec.className = 'stlogic';
    const im = M(v.images);
    sec.innerHTML = `<h4>Catalogue <span>${L(v.lists).length} list(s) · up to ${N(M(v.limits).rows).toLocaleString()} rows each</span></h4>
      <p class="stnote">Products, doctors, properties, courses… from your CSV / Excel file, Google Sheet or a dataset. Each row becomes a page (made by code, no AI cost), with listing pages, filters and sitemaps. Pages with almost nothing of their own, or copies of another row, are shown but not sent to Google.</p>
      ${L(v.lists).length ? `<div class="sttbl"><table><thead><tr><th>List</th><th>Live</th><th>Good</th><th>Thin</th><th>Copies</th><th>Photos</th><th>Filters</th><th></th></tr></thead><tbody>${L(v.lists).map(c => { const k = M(c.counts); return `<tr data-cl="${esc(S(c.coll))}"><td>${esc(S(c.label))}<br><small>/${esc(S(c.coll))}/</small></td><td>${N(k.live)}</td><td>${N(k.ok)}</td><td>${N(k.thin)}</td><td>${N(k.dup)}</td><td>${N(k.photos)}${k.photos_todo ? ' (+' + N(k.photos_todo) + ' waiting)' : ''}</td><td>${esc(L(c.filters).join(', '))}</td><td><button class="btn soft" type="button" data-rm>Remove</button></td></tr>`; }).join('')}</tbody></table></div>` : ''}
      ${im.running ? `<p class="stnote">Making photos: ${N(im.done)} / ${N(im.todo)}…</p>` : (L(v.lists).some(c => N(M(c.counts).photos_todo)) ? '<div class="acts"><button class="btn soft" type="button" data-img>Fetch waiting photos</button></div>' : '')}
      <form class="stapp" data-cat="file" autocomplete="off"><div class="row">
        <label><span>List address</span><input name="coll" placeholder="products" required pattern="[a-zA-Z0-9-]+"></label>
        <label><span>Name on the site</span><input name="label" placeholder="Products"></label>
        <label><span>File (CSV / Excel)</span><input name="file" type="file" accept=".csv,.tsv,.xlsx,.json,text/csv"></label>
        <label><span>…or Google Sheet link / name</span><input name="sheet" placeholder="https://docs.google.com/spreadsheets/…"></label>
        <label><span>…or dataset id</span><input name="dataset" placeholder="ds_…"></label></div>
        <div class="acts"><button class="btn soft" type="submit">Preview (nothing is written)</button></div></form>
      <div class="stcatp"></div>`;
    box.appendChild(sec);
    const reload = () => { sec.remove(); catalogBox(o, box); };
    const f = sec.querySelector('[data-cat=file]'), pv = sec.querySelector('.stcatp');
    f.onsubmit = async e => {
      e.preventDefault();
      const b = f.querySelector('button'); b.disabled = true; pv.innerHTML = '<p class="stnote">Reading…</p>';
      try {
        let p;
        if (f.file.files[0]) {
          const fd = new FormData(); fd.append('file', f.file.files[0]); fd.append('coll', f.coll.value.trim()); fd.append('label', f.label.value.trim());
          p = await api('POST', base(o) + '/catalog/preview', undefined, {form: fd});
        } else {
          p = await api('POST', base(o) + '/catalog/preview', {coll: f.coll.value.trim(), label: f.label.value.trim(), sheet: f.sheet.value.trim(), dataset: f.dataset.value.trim()});
        }
        const mp = M(p.mapping);
        pv.innerHTML = `<div class="stdraft"><b>${N(p.items).toLocaleString()} items ready</b> - ${N(p.new)} new, ${N(p.changed)} changed, ${N(p.same)} same, ${N(p.rejected)} rows left out · ${N(p.thin)} thin, ${N(p.dup)} copies · ${N(p.photos)} photos
          <div class="bln faint">Name: ${esc(S(mp.title))} · Key: ${esc(S(mp.key))} · Price: ${esc(S(mp.price) || '-')} · Photo: ${esc(S(mp.image) || '-')} · Filters: ${esc(L(mp.filters).join(', ') || '-')}</div>
          ${L(p.rejected_rows).slice(0, 8).map(x => `<div class="badc bln">Row ${N(x.row)}: ${esc(S(x.why))}</div>`).join('')}
          ${L(p.sample).length ? `<div class="sttbl"><table><thead><tr><th>Page</th><th>Address</th><th>Price</th></tr></thead><tbody>${L(p.sample).map(x => `<tr><td>${esc(S(x.title))}</td><td>${esc(S(x.address))}</td><td>${esc(S(x.price))}</td></tr>`).join('')}</tbody></table></div>` : ''}
          <div class="acts"><label><input type="checkbox" data-rep> Hide items that are not in this file (${N(p.hidden_if_replace)})</label>
          <button class="btn go" type="button" data-apply>Apply</button></div></div>`;
        pv.querySelector('[data-apply]').onclick = async ev => {
          ev.target.disabled = true;
          try { const r = await api('POST', base(o) + '/catalog/apply', {hash: S(p.hash), replace: pv.querySelector('[data-rep]').checked}); toast(S(r.say) || 'Saved.'); reload(); }
          catch (er) { toast(er.message, true); ev.target.disabled = false; }
        };
      } catch (er) { pv.innerHTML = ''; toast(er.message, true); }
      finally { b.disabled = false; }
    };
    sec.onclick = async e => {
      if (e.target.closest('[data-img]')) { try { await api('POST', base(o) + '/catalog/images'); toast('Photos are being made.'); reload(); } catch (er) { toast(er.message, true); } return; }
      const tr = e.target.closest('tr[data-cl]');
      if (tr && e.target.closest('[data-rm]')) {
        if (!confirm('Take this list off the website? Its rows are kept (hidden) and come back on the next import.')) return;
        try { await api('DELETE', base(o) + '/catalog/' + encodeURIComponent(tr.dataset.cl)); reload(); } catch (er) { toast(er.message, true); }
      }
    };
  }

  /* ---------------- v0.295 edit mode: her own hands in the preview, no AI ---------------- */
  function dialog(title, inner, setup) {
    return new Promise(done => {
      const d = document.createElement('div'); d.className = 'blb sted-dlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', title);
      d.innerHTML = `<form class="sted-card" autocomplete="off"><h3>${esc(title)}</h3>${inner}<div class="acts"><button class="btn soft" type="button" data-x>Cancel</button><button class="btn go" type="submit">Save</button></div></form>`;
      const f = d.querySelector('form'), shut = v => { d.remove(); removeEventListener('keydown', key); done(v); };
      const key = e => { if (e.key === 'Escape') shut(null); };
      d.addEventListener('click', e => { if (e.target === d || e.target.closest('[data-x]')) shut(null); });
      f.addEventListener('submit', e => { e.preventDefault(); shut(new FormData(f)); });
      f.addEventListener('click', e => { const c = e.target.closest('[data-pick]'); if (!c) return; f.querySelectorAll('[data-pick]').forEach(x => x.setAttribute('aria-pressed', String(x === c))); f.elements.pick.value = c.dataset.pick; });
      addEventListener('keydown', key); document.body.appendChild(d);
      if (setup) setup(f);
      const first = f.querySelector('input,button'); if (first) first.focus();
    });
  }
  /* v0.338 EDIT MEIN SAB JODO: a photo / video / YouTube / audio / file she adds after what she clicked */
  const ADD_KINDS = [['photo', 'Photo', 'image/jpeg,image/png,image/webp'], ['video', 'Video', 'video/mp4,video/webm,.m4v'],
                     ['youtube', 'YouTube link', ''], ['audio', 'Audio', 'audio/mpeg,audio/mp4,audio/ogg,audio/wav,.m4a'],
                     ['file', 'File to download', '.pdf,.docx,.xlsx,.pptx,.txt,.csv']];
  async function uploadTo(o, kind, file, about = '') {
    const fd = new FormData(); fd.append('file', file); fd.append('about', about);
    toast(`Uploading ${file.name}…`);
    try {
      const r = await api('POST', base(o) + (kind === 'photo' ? '/photo' : '/media'), undefined, {form: fd});
      if (kind === 'photo') o.photos = L(o.photos).concat([{name: S(r.name), about}]);
      else o.media = L(o.media).concat([{name: S(r.name), kind: S(r.kind), ext: S(r.ext), size: S(r.size), about}]);
      return S(r.name);
    } catch (er) { toast(er.message, true); return ''; }
  }
  async function addDialog(o, k, e) {
    const have = kind => kind === 'photo' ? L(o.photos).map(p => [S(p.name), S(p.about) || S(p.name)])
      : L(o.media).filter(m => S(m.kind) === kind).map(m => [S(m.name), `${S(m.about) || S(m.name)} (${S(m.ext).toUpperCase()}, ${S(m.size)})`]);
    const f = await dialog('Add below this', `<div class="sted-kinds" role="radiogroup" aria-label="What to add">${ADD_KINDS.map(([v, n], i) => `<label class="sted-kind"><input type="radio" name="kind" value="${v}"${i ? '' : ' checked'}> ${n}</label>`).join('')}</div>
      ${ADD_KINDS.filter(([v]) => v !== 'youtube').map(([v, , acc]) => `<div class="sted-for" data-for="${v}"${v === 'photo' ? '' : ' hidden'}>
        ${have(v).length ? `<label class="sted-c wide"><span>Use one you already added</span><select name="have_${v}"><option value="">—</option>${have(v).map(([nm, lab]) => `<option value="${esc(nm)}">${esc(lab)}</option>`).join('')}</select></label>` : ''}
        <label class="sted-c wide"><span>${have(v).length ? 'Or upload' : 'Upload'}</span><input type="file" name="file_${v}" accept="${acc}"></label></div>`).join('')}
      <div class="sted-for" data-for="youtube" hidden><label class="sted-c wide"><span>YouTube link</span><input name="url" placeholder="https://youtu.be/…"></label></div>
      <label class="sted-c wide"><span>Caption / button text (optional)</span><input name="caption" maxlength="160"></label>
      <p class="sted-note">Videos up to 60 MB (MP4 / WebM), audio and files up to 20 MB. Visitors see it right away after you save.</p>`,
      dlg => dlg.addEventListener('change', ev => { if (ev.target.name === 'kind') dlg.querySelectorAll('.sted-for').forEach(x => { x.hidden = x.dataset.for !== ev.target.value; }); }));
    if (!f) return;
    const kind = S(f.get('kind')), caption = S(f.get('caption')).trim();
    const spec = {kind, caption};
    if (kind === 'youtube') { spec.url = S(f.get('url')).trim(); if (!spec.url) return toast('Paste the YouTube link.', true); }
    else {
      const file = f.get('file_' + kind);
      spec.name = file && file.size ? await uploadTo(o, kind, file, caption) : S(f.get('have_' + kind));
      if (!spec.name) return toast('Choose a file to add.', true);
    }
    editSend(o, {k, e, op: 'insert', value: JSON.stringify(spec)});
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
    if (d.t === 'image') {     // v0.338 her own photo can be uploaded right here
      const ph = L(o.photos);
      const f = await dialog('Change the picture', `<input type="hidden" name="pick" value="${esc(S(d.img))}">${ph.length ? `<div class="sted-ph">${ph.map(p => `<button type="button" class="btn soft" data-pick="${esc(S(p.name))}" aria-pressed="${S(p.name) === S(d.img)}">${esc(S(p.about) || S(p.name))}${p.ai ? ' · AI' : ''}</button>`).join('')}</div>` : ''}
        <label class="sted-c wide"><span>${ph.length ? 'Or upload a new photo' : 'Upload a photo'} (JPEG, PNG, WebP)</span><input type="file" name="file" accept="image/jpeg,image/png,image/webp"></label>`);
      if (!f) return;
      let pick = S(f.get('pick'));
      const file = f.get('file');
      if (file && file.size) { pick = await uploadTo(o, 'photo', file); if (!pick) return; }
      if (pick && pick !== S(d.img)) editSend(o, {k, e, op: 'image', value: pick}); return;
    }
    if (d.t === 'add') return addDialog(o, k, e);
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
  /* ---------------- v0.407 HOOLA ARCHITECT: her one line -> the spec card, module by module -> her Haan builds ---------------- */
  function specCard(p, el) {
    const c = M(p), mods = L(c.modules), built = S(c.status) === 'built';
    el.classList.add('bcard', 'stspec');
    el.innerHTML = `<div class="hd"><span class="bic" aria-hidden="true">${IC_WEB}</span><b>${esc(S(c.name) || 'Website plan')} · ${esc(S(c.number))}</b><span class="tag ${built ? 'ok' : 'warn'}">${built ? 'Building ' + esc(S(c.site)) : 'Spec: needs your Haan'}</span></div>`
      + (c.summary ? `<p class="bsay">${esc(S(c.summary))}</p>` : '')
      + mods.map(m => `<fieldset class="stmod"><legend><label><input type="checkbox" data-mod="${esc(S(m.key))}"${m.required || built ? ' disabled' : ''} checked> <b>${esc(S(m.title))}</b>${m.ready === false ? ' <span class="badc">needs a fix</span>' : ''}</label></legend>
          ${L(m.lines).slice(0, 14).map(x => `<div class="bln faint">• ${esc(S(x))}</div>`).join('')}</fieldset>`).join('')
      + L(c.questions).map(q => `<div class="warnc bln">? ${esc(S(q))}</div>`).join('')
      + (built ? '' : `<div class="acts"><button class="btn soft" type="button" data-sp="data">Change anything</button><button class="btn go" type="button" data-sp="ok">Haan, build it</button></div>`);
    el.onclick = async e => {
      const b = e.target.closest('[data-sp]'); if (!b) return;
      const url = `/api/site-architect/${encodeURIComponent(S(c.id))}`;
      if (b.dataset.sp === 'data') {
        const w = prompt('What should change? (e.g. add an alumni page, teachers also mark attendance, fees by UPI)'); if (!w) return;
        b.disabled = true;
        try { const r = await api('POST', url + '/revise', {words: w}); specCard(r, el); toast(S(r?.say) || 'Updated.'); } catch (er) { toast(er.message, true); b.disabled = false; }
        return;
      }
      const keep = [...el.querySelectorAll('[data-mod]')].filter(x => x.checked).map(x => x.dataset.mod);
      if (!confirm(`Build ${S(c.name) || 'this website'} with: ${keep.join(', ')}?`)) return;
      b.disabled = true;
      try { const r = await api('POST', url + '/approve', {hash: S(c.hash), modules: keep, conversation_id: C.conv() || ''}); toast(S(r?.say) || 'Building.'); specCard({...c, status: 'built', site: r?.number}, el); }
      catch (er) { toast(er.message, true); b.disabled = false; }
    };
  }

  setInterval(() => { const o = P.get(CUR); if (o && isOpen() && studio.dataset.k === o.k) { const age = studio.querySelector('.pvage'); if (age) age.textContent = 'taaza · ' + ago(o.loadedAt || Date.now()); } }, 5000);
  if (sbtn) sbtn.addEventListener('click', () => { if (isOpen()) return close(); const o = P.get(CUR) || [...P.values()].sort((a, b) => b.last - a.last)[0]; if (o) open(o.k); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen() && !document.querySelector('.blb')) close(); });

  return {
    kinds: KINDS,
    card(kind, p, el, live) { if (kind === 'site_spec') return specCard(p, el); card(kind, p, el, live); after(kind, p); },
    reset, close, isOpen,
  };
};
