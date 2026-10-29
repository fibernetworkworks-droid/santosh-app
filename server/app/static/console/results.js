/* Web console only: typed results in the conversation, using existing authenticated APIs.
   The panel remains the editing surface. No credentials enter result frames or result URLs. */
'use strict';
window.HoolaResults = ctx => {
  const {api, esc} = ctx;
  const KINDS = new Set(['photo_made', 'pc_file', 'motion', 'video_job', 'artifact']);
  const active = new Map();
  const own = (url, pattern) => {
    try {
      const u = new URL(url, location.origin);
      return u.origin === location.origin && pattern.test(u.pathname) ? u.pathname + u.search : '';
    } catch { return ''; }
  };
  const alive = s => active.get(s.el) === s && s.el.isConnected;
  function release(s) {
    s.controller.abort();
    s.el.querySelectorAll('video,audio').forEach(m => { m.pause(); m.removeAttribute('src'); m.load(); });
    s.urls.forEach(u => URL.revokeObjectURL(u));
    s.urls.length = 0;
  }
  function reset() { active.forEach(release); active.clear(); }
  function visible(s) {
    if (!window.IntersectionObserver) return Promise.resolve();
    return new Promise(resolve => {
      const done = () => { observer.disconnect(); s.controller.signal.removeEventListener('abort', done); resolve(); };
      const observer = new IntersectionObserver(entries => { if (entries.some(e => e.isIntersecting)) done(); }, {rootMargin: '600px'});
      observer.observe(s.el); s.controller.signal.addEventListener('abort', done, {once: true});
    });
  }
  function state(el) {
    const old = active.get(el); if (old) release(old);
    const s = {el, controller: new AbortController(), urls: []}; active.set(el, s); return s;
  }
  async function objectURL(s, path) {
    const r = await api('GET', path, undefined, {raw: true, signal: s.controller.signal});
    const b = await r.blob();
    if (!alive(s)) return '';
    const u = URL.createObjectURL(b); s.urls.push(u); return u;
  }
  function actions(s, item, download, name) {
    const row = document.createElement('div'); row.className = 'result-actions';
    row.innerHTML = '<button type="button" class="btn soft" data-expand>Open in workspace</button>'
      + (ctx.reuse && !item.url && item.type !== 'page' ? '<button type="button" class="btn soft" data-reuse>Use as reference</button>' : '')
      + (download ? '<button type="button" class="btn soft" data-download>Download</button>' : '');
    row.querySelector('[data-expand]').onclick = () => ctx.open(item);
    row.querySelector('[data-reuse]')?.addEventListener('click', () => ctx.reuse(item));
    row.querySelector('[data-download]')?.addEventListener('click', async e => {
      const button = e.currentTarget; button.disabled = true;
      try {
        const u = await objectURL(s, download); if (!u) return;
        const a = document.createElement('a'); a.href = u; a.download = name || 'hoola-result'; a.click();
        // Keep the URL until reset: a browser may start downloading asynchronously.
      } catch (er) { if (er.name !== 'AbortError') ctx.toast(er.message, true); }
      finally { button.disabled = false; }
    });
    s.el.appendChild(row);
  }
  async function card(kind, p, el) {
    if (!KINDS.has(kind)) return false;
    const item = ctx.itemOf(kind, p);
    // Failed/pending work without a real output stays with the ordinary status renderer.
    if (!item || (kind === 'artifact' && p.status !== 'ready')) return false;
    const s = state(el);
    el.className = 'cd result-card';
    el.innerHTML = `<div class="hd"><b>${esc(p.title || p.name || item.title || 'Hoola result')}</b>`
      + `<span class="tag ok">${kind === 'photo_made' || p.ai ? 'AI-generated' : 'Ready'}</span></div>`
      + '<div class="result-preview" aria-busy="true"><span class="muted">Loading preview…</span></div>';
    const view = el.querySelector('.result-preview');
    try {
      if (item.type === 'page') {
        // Interactive pages keep their existing panel bridge; chat shows a compact launch surface.
        view.innerHTML = `<div class="result-document"><span aria-hidden="true">◈</span><div><b>Interactive page · v${Number(p.version) || 1}</b><p>${esc(p.summary || 'Open in the workspace to use it.')}</p></div></div>`;
        actions(s, item, '', '');
      } else if (item.url) {
        const url = own(item.url, /^\/api\/(motion|video)\/files\//);
        if (!url) throw new Error('No preview link is available for this result.');
        const m = document.createElement('video'); m.controls = true; m.playsInline = true;
        m.preload = 'metadata'; m.src = url; m.setAttribute('aria-label', item.title || 'Video result'); view.replaceChildren(m);
        actions(s, item, url, p.name || 'hoola-video.mp4');
      } else {
        const base = `/api/panel/files/${encodeURIComponent(item.ref)}`;
        const info = await api('GET', base + '/info', undefined, {signal: s.controller.signal});
        if (!alive(s)) return true;
        const inline = info.inline && ['image', 'video', 'audio', 'pdf'].includes(info.media);
        // Office conversion is loaded on demand in the workspace, never once per chat replay.
        if (inline && info.media !== 'pdf') {
          await visible(s); if (!alive(s)) return true;
          const u = await objectURL(s, base); if (!u) return true;
          const m = document.createElement(info.media === 'image' ? 'img' : info.media);
          if (info.media === 'image') { m.alt = info.name || 'Hoola image'; m.loading = 'lazy'; }
          else { m.controls = true; m.preload = 'metadata'; m.playsInline = true; }
          m.src = u; view.replaceChildren(m);
        } else {
          view.innerHTML = `<div class="result-document"><span aria-hidden="true">▤</span><div><b>${esc(info.name || item.title)}</b><p>${Math.max(1, Math.round((info.size || 0) / 1024))} KB · ${esc(info.media || 'file')}</p></div></div>`;
        }
        actions(s, item, base + '?download=1', info.name);
      }
      if (alive(s)) {
        const media = view.querySelector('img,video,audio');
        if (media) media.addEventListener('error', () => {
          if (alive(s)) view.innerHTML = '<p class="muted">Preview could not load. Try opening the workspace or downloading the file.</p>';
        }, {once: true});
      }
    } catch (er) {
      if (!alive(s) || er.name === 'AbortError') return true;
      view.innerHTML = `<p class="muted">${esc(er.message || 'Preview is unavailable.')}</p>`;
      actions(s, item, '', '');
    } finally {
      if (alive(s)) { view.setAttribute('aria-busy', 'false'); ctx.resize?.(); }
    }
    return true;
  }
  return {kinds: KINDS, card, reset};
};
