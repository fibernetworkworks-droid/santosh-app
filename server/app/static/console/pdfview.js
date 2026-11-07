/* v0.248 Hoola Console · our own PDF reader for the workspace (owner: "AT PDF TOP A BLACK STRIP, WE DONT NEED IT. IN WORKSPACE
   WE ONLY WANT A FULL PDF ONLY WITH MATCHING BACKGROUND OF OUR DESIGN"). The browser's built-in viewer brings its own black
   toolbar and grey canvas we cannot style, so the pages are drawn here with PDF.js (Apache-2.0, vendored in
   vendor/pdfjs, loaded only when a PDF opens): pages fitted to the workspace width on the theme's background, drawn as
   they scroll into view (sharp on any screen), selectable text, and one small floating pill (page n / N, zoom, fit).
   window.HoolaPdf.mount(host, bytes, name) -> Promise<{destroy()}> */
'use strict';
window.HoolaPdf = (() => {
  const V = '3.11.174', BASE = '/static/console/vendor/pdfjs/';
  let lib = null;
  function load() {
    if (lib) return lib;
    lib = new Promise((res, rej) => {
      if (window.pdfjsLib) return res(window.pdfjsLib);
      const s = document.createElement('script'); s.src = `${BASE}pdf.min.js?v=${V}`; s.async = true;
      s.onload = () => { const L = window.pdfjsLib; if (!L) { lib = null; return rej(new Error('The PDF reader did not load')); }
        L.GlobalWorkerOptions.workerSrc = `${BASE}pdf.worker.min.js?v=${V}`; res(L); };
      s.onerror = () => { lib = null; rej(new Error('The PDF reader did not load')); };
      document.head.appendChild(s);
    });
    return lib;
  }
  const ZOOMS = [.5, .67, .8, .9, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.5, 3];

  async function mount(host, bytes, name) {
    const L = await load();
    const doc = await L.getDocument({data: bytes, isEvalSupported: false, disableAutoFetch: true, disableStream: true}).promise;
    const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
    host.innerHTML = `<div class="pdfv" tabindex="0" role="document" aria-label="${esc(name || 'PDF')}">
        <div class="pdfpages"></div>
        <div class="pdfpill" role="toolbar" aria-label="PDF">
          <button type="button" data-z="out" aria-label="Zoom out">−</button>
          <span class="pdfpg" aria-live="polite">1 / ${doc.numPages}</span>
          <button type="button" data-z="in" aria-label="Zoom in">+</button>
          <i aria-hidden="true"></i>
          <button type="button" data-z="fit" class="pdffit" aria-label="Fit to width">Fit</button>
        </div></div>`;
    const root = host.querySelector('.pdfv'), wrap = root.querySelector('.pdfpages'), pg = root.querySelector('.pdfpg');
    const first = await doc.getPage(1), base = first.getViewport({scale: 1});
    let zoom = 1, dead = false;
    const pages = [];
    for (let i = 1; i <= doc.numPages; i++) {
      const el = document.createElement('div'); el.className = 'pdfpage'; el.dataset.n = i;
      el.style.aspectRatio = `${base.width} / ${base.height}`; wrap.appendChild(el);
      pages.push({n: i, el, page: i === 1 ? first : null, drawn: 0, task: null});
    }
    const fitW = () => Math.max(160, wrap.clientWidth - 32);
    const cssW = () => Math.round(fitW() * zoom);
    const size = () => { const w = cssW() + 'px'; pages.forEach(p => { p.el.style.width = w; }); root.classList.toggle('wide', zoom > 1); };

    async function draw(p) {
      const w = cssW(); if (dead || p.drawn === w) return;
      p.drawn = w;
      try {
        p.page = p.page || await doc.getPage(p.n); if (dead) return;
        const v1 = p.page.getViewport({scale: 1});
        p.el.style.aspectRatio = `${v1.width} / ${v1.height}`;
        const vp = p.page.getViewport({scale: w / v1.width}), dpr = Math.min(window.devicePixelRatio || 1, 2.5);
        const c = document.createElement('canvas'); c.width = Math.floor(vp.width * dpr); c.height = Math.floor(vp.height * dpr);
        c.setAttribute('aria-hidden', 'true');
        p.task?.cancel?.();
        p.task = p.page.render({canvasContext: c.getContext('2d', {alpha: false}), viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null});
        await p.task.promise; if (dead || p.drawn !== w) return;
        const tl = document.createElement('div'); tl.className = 'textLayer'; tl.style.setProperty('--scale-factor', vp.scale);
        p.el.replaceChildren(c, tl); p.el.classList.add('in');
        L.renderTextLayer({textContentSource: p.page.streamTextContent(), container: tl, viewport: vp, textDivs: []}).promise.catch(() => {});
      } catch (e) { if (e?.name !== 'RenderingCancelledException') p.drawn = 0; }
    }
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) draw(pages[+e.target.dataset.n - 1]); }),
      {root: wrap, rootMargin: '800px 0px'});
    pages.forEach(p => io.observe(p.el));
    const redraw = () => { size(); pages.forEach(p => { const r = p.el.getBoundingClientRect(), h = wrap.getBoundingClientRect();
      if (r.bottom > h.top - 800 && r.top < h.bottom + 800) draw(p); }); };
    let rt = 0; const ro = new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(redraw, 120); }); ro.observe(wrap);
    const counter = () => { const top = wrap.getBoundingClientRect().top + wrap.clientHeight / 3;
      let cur = 1; for (const p of pages) { if (p.el.getBoundingClientRect().top <= top) cur = p.n; else break; }
      pg.textContent = `${cur} / ${doc.numPages}`; };
    wrap.addEventListener('scroll', counter, {passive: true});
    const setZoom = z => { const keep = wrap.scrollTop / Math.max(1, wrap.scrollHeight); zoom = z; redraw(); wrap.scrollTop = keep * wrap.scrollHeight;
      root.querySelector('.pdffit').classList.toggle('on', zoom === 1); };
    root.querySelector('.pdfpill').addEventListener('click', e => { const b = e.target.closest('[data-z]'); if (!b) return;
      const i = ZOOMS.indexOf(zoom);
      if (b.dataset.z === 'in') setZoom(ZOOMS[Math.min(ZOOMS.length - 1, i + 1)]);
      else if (b.dataset.z === 'out') setZoom(ZOOMS[Math.max(0, i - 1)]); else setZoom(1); });
    root.addEventListener('keydown', e => { if (e.target.closest('button')) return;
      if (e.key === '+' || e.key === '=') { e.preventDefault(); root.querySelector('[data-z="in"]').click(); }
      else if (e.key === '-') { e.preventDefault(); root.querySelector('[data-z="out"]').click(); }
      else if (e.key === '0') { e.preventDefault(); setZoom(1); } });
    root.querySelector('.pdffit').classList.add('on');
    size(); redraw();
    return {destroy() { dead = true; io.disconnect(); ro.disconnect(); pages.forEach(p => p.task?.cancel?.()); doc.destroy(); }};
  }
  return {mount, load};
})();
