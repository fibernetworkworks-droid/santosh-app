/* The Hoola website: one script for every page (CSP script-src 'self', no inline script, no library).
   Every scene finds its own element (data-*), plays only while it is on screen, and holds a still, complete frame
   under prefers-reduced-motion. The words on the page are in the HTML; this file only moves and switches them. */
(() => {
'use strict';
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const wait = ms => new Promise(r => setTimeout(r, ms));
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/* ---------- on screen? ---------- */
const seen = new Set();
const watchers = new Map();
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { seen.add(e.target); const w = watchers.get(e.target); if (w) w(); }
  else seen.delete(e.target);
}), {threshold: .2});
const visible = el => seen.has(el) && document.visibilityState === 'visible';
const watch = (el, onEnter) => { if (onEnter) watchers.set(el, onEnter); io.observe(el); };

// run fn while the element is on screen, again every gap ms; one run at a time
function loop(el, fn, gap) {
  let running = false;
  const go = async () => {
    if (running) return;
    running = true;
    try {
      do { await fn(); if (RM) break; await wait(gap); } while (visible(el));
    } finally { running = false; }
  };
  watch(el, go);
}

/* ---------- header ---------- */
const top = $('.top');
if (top) addEventListener('scroll', () => top.classList.toggle('scrolled', scrollY > 4), {passive: true});
const mb = $('#menuBtn'), dr = $('#drawer');
if (mb && dr) mb.addEventListener('click', () => { const o = dr.classList.toggle('open'); mb.setAttribute('aria-expanded', String(o)); });

/* ---------- words that land like the console (34 ms a word, soft focus) ---------- */
function landWords(el, html, gap = 34) {
  const tmp = document.createElement('div'); tmp.innerHTML = html;
  const parts = [];
  tmp.childNodes.forEach(n => {
    const bold = n.nodeType === 1;
    (n.textContent || '').split(/(\s+)/).forEach(t => { if (t) parts.push([t, bold]); });
  });
  el.textContent = '';
  if (RM) { el.innerHTML = html; return Promise.resolve(); }
  return new Promise(res => {
    let i = 0;
    const step = () => {
      if (i >= parts.length) return res();
      const [t, b] = parts[i++];
      if (/^\s+$/.test(t)) { el.append(t); return step(); }
      const s = document.createElement(b ? 'b' : 'span'); s.className = 'w'; s.textContent = t; el.append(s);
      setTimeout(step, gap);
    };
    step();
  });
}

/* ---------- hero: the console doing one job ---------- */
$$('[data-hero]').forEach(T => {
  const box = $('[data-hero-tx]', T.closest('.app'));
  const ask = T.dataset.ask, steps = T.dataset.steps.split('|');
  loop(T, async () => {
    await wait(2600);
    if (!visible(T)) return;
    T.textContent = '';
    if (box) {
      box.classList.add('typing');
      for (let i = 0; i <= ask.length; i += 2) { box.textContent = ask.slice(0, i); await wait(18); }
      await wait(250);
      box.classList.remove('typing'); box.textContent = box.dataset.ph;
    }
    T.insertAdjacentHTML('beforeend', `<div class="her w"></div>`); T.lastChild.textContent = ask;
    await wait(500);
    T.insertAdjacentHTML('beforeend', '<div class="working w"><svg class="mk think" fill="currentColor" aria-hidden="true"><use href="#hm"/></svg><span class="lbl"></span><span class="clock">0s</span></div>');
    const wk = T.lastChild, t0 = Date.now();
    const clk = setInterval(() => { $('.clock', wk).textContent = Math.floor((Date.now() - t0) / 100) + 's'; }, 100);
    for (const s of steps) { $('.lbl', wk).textContent = s; await wait(1100); }
    clearInterval(clk);
    wk.outerHTML = `<div class="worked w"><svg aria-hidden="true"><use href="#i-arrow"/></svg>${T.dataset.worked}</div>`;
    T.insertAdjacentHTML('beforeend', '<div class="reply"></div>');
    await landWords(T.lastChild, T.dataset.reply);
    await wait(400);
    T.insertAdjacentHTML('beforeend', T.dataset.card ? $(T.dataset.card).innerHTML : '');
    const card = T.lastElementChild;
    card.classList.add('w');
    const sl = $('.slide', card); sl.classList.remove('done');
    await wait(1600); sl.classList.add('done'); await wait(1100);
    card.insertAdjacentHTML('beforeend', `<div class="paid w"><svg aria-hidden="true"><use href="#i-check"/></svg>${T.dataset.paid}</div>`);
  }, 4200);
});

/* ---------- scene: a website being built, then checked ---------- */
const SECTIONS = [['hero2', 'Hero', ['k', 'k60', 'a40']], ['', "Today's sweets", ['k40', '', '', '80']],
  ['', 'Order on WhatsApp', ['k50', 'a30']], ['', 'Visit us', ['k30', '', '60']], ['', 'Footer', ['', '50']]];
const lineHTML = spec => { const m = /^(k|a)?(\d+)?$/.exec(spec) || []; return `<div class="ln ${m[1] || ''} grow" style="width:${m[2] || 100}%"></div>`; };
async function buildSite(root) {
  const page = $('.page', root), cks = $$('.ck', root), n = $('.ckn', root);
  page.textContent = ''; cks.forEach(c => c.classList.remove('ok')); if (n) n.textContent = '0/' + cks.length;
  for (const [cls, tag, lines] of SECTIONS) {
    page.insertAdjacentHTML('beforeend', `<div class="blk ${cls}"><span class="tag">${tag}</span>${lines.map(lineHTML).join('')}</div>`);
    if (!RM) await wait(560);
  }
  for (let i = 0; i < cks.length; i++) { cks[i].classList.add('ok'); if (n) n.textContent = (i + 1) + '/' + cks.length; if (!RM) await wait(260); }
}
$$('[data-site]').forEach(r => { if (!r.closest('[data-switch]')) loop(r, () => buildSite(r), 4500); });

/* ---------- scene: phone screens sliding ---------- */
const SCREENS = [
  '<div class="ln k" style="width:60%"></div><div class="tile a" style="height:90px"></div><div class="tile"></div><div class="tile"></div>',
  '<div class="ln k" style="width:40%"></div><div class="tile"></div><div class="tile a"></div><div class="tile"></div><div class="tile"></div>',
  '<div class="ln k" style="width:50%"></div><div class="tile" style="height:120px"></div><div class="ln a" style="width:70%;height:34px;border-radius:999px"></div>'];
function phone(scr) {
  let i = 0; scr.innerHTML = SCREENS[0];
  return async () => {
    if (RM) return;
    scr.style.transform = 'translateX(-110%)'; await wait(600);
    i++; scr.innerHTML = SCREENS[i % 3]; scr.style.transition = 'none'; scr.style.transform = 'translateX(110%)';
    scr.offsetWidth; scr.style.transition = ''; scr.style.transform = 'translateX(0)';
  };
}
$$('[data-phone]').forEach(p => { const next = phone($('.scr', p)); if (!p.closest('[data-switch]')) loop(p, next, 2200); else p._next = next; });

/* ---------- scene: Hoola Code writes the test, fixes, opens the PR ---------- */
const DIFF = [['', '    def line_tax(amount, rate):'], ['m', '        return round(amount * rate / 100, 2)'],
  ['p', '        tax = Decimal(amount) * Decimal(rate) / 100'], ['p', '        return tax.quantize(Decimal("0.01"), ROUND_HALF_UP)'],
  ['', ''], ['', '    def invoice_tax(lines):'], ['m', '        return sum(line_tax(l.amount, l.rate) for l in lines)'],
  ['p', '        return sum((line_tax(l.amount, l.rate) for l in lines), Decimal(0))']];
const CSTEPS = [['Read', 'AGENTS.md, app/billing/'], ['Wrote a failing test', 'tests/test_gst.py'], ['Ran', 'pytest tests/test_gst.py'],
  ['Fixed', 'app/billing/gst.py'], ['Ran all tests', '214 passed']];
async function codeRun(root) {
  const st = $('.steps', root), df = $('.diff', root), pr = $('.prc', root);
  st.textContent = ''; $$('.l', df).forEach(l => l.remove()); pr.hidden = true;
  for (const [a, b] of CSTEPS) {
    st.insertAdjacentHTML('beforeend', `<div class="s w"><svg width="14" height="14" class="okic" aria-hidden="true"><use href="#i-check"/></svg>${a} <code>${b}</code></div>`);
    if (a === 'Fixed') for (const [k, t] of DIFF) {
      const l = document.createElement('div'); l.className = 'l w ' + k;
      l.textContent = (k === 'p' ? '+ ' : k === 'm' ? '- ' : '  ') + t; df.append(l); if (!RM) await wait(140);
    }
    if (!RM) await wait(560);
  }
  pr.hidden = false; pr.classList.add('w');
}
$$('[data-code]').forEach(r => { if (!r.closest('[data-switch]')) loop(r, () => codeRun(r), 5000); });

/* ---------- scene: Hoola PC fills a portal form from row 1 of her Excel ---------- */
async function pcRun(root) {
  const desk = $('.desk', root), cur = $('.cursor', root), th = $('[data-thought]', root), fs = $$('.field', root);
  const vals = ['Sharma Sweets', 'ABCDE••••F', 'Akola'];
  const say = $$('[data-say]', root).map(s => s.textContent);
  fs.forEach(f => { $('div', f).textContent = ''; f.classList.remove('focus'); });
  const moveTo = f => { const d = desk.getBoundingClientRect(), r = $('div', f).getBoundingClientRect();
    cur.style.left = (r.left - d.left + 40) + 'px'; cur.style.top = (r.top - d.top + 10) + 'px'; };
  const type = async (f, t) => { f.classList.add('focus'); const b = $('div', f);
    for (let i = 1; i <= t.length; i++) { b.textContent = t.slice(0, i); if (!RM) await wait(55); } f.classList.remove('focus'); };
  th.textContent = say[0]; if (!RM) await wait(900);
  for (let i = 0; i < fs.length; i++) {
    if (i) th.textContent = say[i];
    moveTo(fs[i]); if (!RM) await wait(900); await type(fs[i], vals[i]);
  }
  th.textContent = say[3];
}
$$('[data-pc]').forEach(r => { if (!r.closest('[data-switch]')) loop(r, () => pcRun(r), 4000); });

/* ---------- scene: a storyboard painted in code (no stock pictures) ---------- */
const SHOT_HUES = [[36, 18], [28, 40], [20, 60], [262, 30]];
function paintShot(cv, k, t) {
  const r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1), w = r.width, h = r.height;
  if (!w || !h) return;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  const [hue, light] = SHOT_HUES[k % 4];
  const sky = g.createLinearGradient(0, 0, 0, h);
  sky.addColorStop(0, `hsl(${hue} 70% ${18 + light / 4}%)`); sky.addColorStop(1, `hsl(${hue + 18} 80% ${38 + light / 3}%)`);
  g.fillStyle = sky; g.fillRect(0, 0, w, h);
  const glow = g.createRadialGradient(w * .5, h * (.62 + Math.sin(t / 900 + k) * .02), 4, w * .5, h * .62, w * .7);
  glow.addColorStop(0, `hsla(${hue + 20} 100% 70% / .9)`); glow.addColorStop(1, `hsla(${hue} 100% 50% / 0)`);
  g.fillStyle = glow; g.fillRect(0, 0, w, h);
  g.fillStyle = `hsl(${hue} 40% 10% / .85)`;
  if (k % 4 === 0) { g.fillRect(w * .12, h * .5, w * .76, h * .5); g.fillStyle = `hsl(${hue + 30} 90% 62%)`; for (let i = 0; i < 4; i++) g.fillRect(w * (.18 + i * .17), h * .58, w * .1, h * .08); }
  if (k % 4 === 1) { g.beginPath(); g.ellipse(w / 2, h * .7, w * .38, h * .07, 0, 0, 7); g.fill(); g.fillStyle = 'hsl(40 70% 80%)';
    for (let i = 0; i < 5; i++) { g.save(); g.translate(w * (.3 + i * .1), h * .66); g.rotate(Math.PI / 4); g.fillRect(-7, -7, 14, 14); g.restore(); } }
  if (k % 4 === 2) { const f = 1 + Math.sin(t / 140) * .08; g.fillRect(w * .3, h * .72, w * .4, h * .06); g.fillStyle = 'hsl(45 100% 70%)';
    g.beginPath(); g.ellipse(w / 2, h * .62, 6 * f, 16 * f, 0, 0, 7); g.fill(); }
  if (k % 4 === 3) { g.fillStyle = 'rgb(255 255 255 / .92)'; g.fillRect(w * .14, h * .4, w * .72, 10); g.fillRect(w * .24, h * .48, w * .52, 7);
    g.fillStyle = `hsl(${hue} 90% 60%)`; g.fillRect(w * .3, h * .58, w * .4, 18); }
}

/* ---------- the voice call: light from below, following a voice ---------- */
function voiceFrame(vc, t) {
  const r = vc.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1), w = r.width, h = r.height;
  if (!w) return;
  if (vc.width !== Math.round(w * dpr)) { vc.width = Math.round(w * dpr); vc.height = Math.round(h * dpr); }
  const g = vc.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  const him = Math.sin(t / 2600) > -.2;
  const lvl = RM ? .7 : .55 + .45 * Math.abs(Math.sin(t / 170) * Math.sin(t / 430 + 1));
  const hue = him ? '156 136 255' : '138 180 248';
  const gr = g.createRadialGradient(w / 2, h + 40, 10, w / 2, h + 40, h * (.75 + lvl * .35));
  gr.addColorStop(0, `rgb(${hue} / ${.55 + lvl * .25})`); gr.addColorStop(.55, `rgb(${hue} / .16)`); gr.addColorStop(1, 'rgb(0 0 0 / 0)');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.strokeStyle = `rgb(${hue} / .55)`; g.lineWidth = 1.5; g.beginPath();
  for (let x = 0; x <= w; x += 6) { const y = h * .58 + Math.sin(x / 38 + t / 260) * 10 * lvl + Math.sin(x / 13 + t / 120) * 3 * lvl; x ? g.lineTo(x, y) : g.moveTo(x, y); }
  g.stroke();
}

/* ---------- each studio's own small drawing ---------- */
function toolArt(cv, kind, t) {
  const r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1), w = r.width, h = r.height;
  if (!w) return;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  const ink = css('--ink'), acc = css('--acc'), line = css('--line2'), sunk = css('--sunk'), card = css('--card');
  const cx = w / 2, cy = h / 2, s = RM ? 2.2 : t / 1000;
  const rr = (x, y, ww, hh, rad, fill) => { if (ww <= 0) return; g.beginPath(); g.roundRect(x, y, ww, hh, rad); g.fillStyle = fill; g.fill(); };
  g.lineCap = 'round';
  switch (kind) {
    case 'web': { rr(cx - 120, cy - 60, 240, 120, 10, card); g.strokeStyle = line; g.strokeRect(cx - 120, cy - 60, 240, 120);
      const n = RM ? 4 : Math.floor((s * 1.4) % 5); for (let i = 0; i < 4; i++) rr(cx - 104, cy - 44 + i * 26, i < n ? (i ? 150 : 208) : 0, 14, 4, i ? sunk : acc); break; }
    case 'app': { rr(cx - 34, cy - 66, 68, 132, 14, ink); rr(cx - 28, cy - 58, 56, 116, 9, card); const o = (s * 40) % 28;
      g.save(); g.beginPath(); g.rect(cx - 28, cy - 58, 56, 116); g.clip();
      for (let i = 0; i < 5; i++) rr(cx - 22, cy - 50 + i * 28 - o, 44, 20, 5, i % 2 ? sunk : acc); g.restore(); break; }
    case 'code': { g.font = `500 12px ${css('--mono')}`; const L = ['def tax(a, r):', '- round(a*r/100,2)', '+ Decimal(a)*r/100', '  214 passed'];
      const n = RM ? 4 : Math.floor((s * 1.2) % 5); L.slice(0, n).forEach((l, i) => { g.fillStyle = l[0] === '+' ? css('--ok') : l[0] === '-' ? css('--bad') : ink; g.fillText(l, cx - 90, cy - 30 + i * 22); }); break; }
    case 'film': { for (let i = 0; i < 4; i++) { const x = cx - 118 + i * 60, hue = [30, 260, 18, 340][i], k = (s * .8 + i * .25) % 1; rr(x, cy - 46, 52, 92, 7, `hsl(${hue} 70% ${28 + k * 30}%)`); } break; }
    case 'cinema': { const a = s * 1.6; g.fillStyle = acc; g.globalAlpha = .18; g.beginPath(); g.arc(cx, cy, 52, 0, 7); g.fill(); g.globalAlpha = 1;
      g.strokeStyle = acc; g.lineWidth = 2; g.beginPath(); g.arc(cx, cy, 52, a, a + 4); g.stroke(); g.fillStyle = ink; g.beginPath(); g.arc(cx, cy - 8, 16, 0, 7); g.fill(); rr(cx - 24, cy + 12, 48, 30, 15, ink); break; }
    case 'voice': case 'flow': { g.strokeStyle = kind === 'voice' ? acc : ink; g.lineWidth = 4;
      for (let i = -7; i <= 7; i++) { const hh = 12 + Math.abs(Math.sin(s * 3 + i * .7)) * 46 * (1 - Math.abs(i) / 9); g.beginPath(); g.moveTo(cx + i * 14, cy - hh / 2); g.lineTo(cx + i * 14, cy + hh / 2); g.stroke(); } break; }
    case 'inter': { rr(cx - 110, cy - 56, 220, 112, 10, card); g.strokeStyle = line; g.strokeRect(cx - 110, cy - 56, 220, 112);
      [.4, .65, .5, .85, .7].forEach((v, i) => { const k = RM ? 1 : Math.min(1, Math.max(0, s % 4 - i * .2)); rr(cx - 90 + i * 38, cy + 40 - 76 * v * k, 24, 76 * v * k, 4, i === 3 ? acc : sunk); }); break; }
    case 'design': { g.strokeStyle = line; g.lineWidth = 1; for (let x = 0; x < w; x += 20) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
      const x = cx - 60 + Math.sin(s) * 30; rr(x, cy - 40, 120, 80, 10, acc); g.strokeStyle = ink; g.lineWidth = 1.5; g.strokeRect(x - 4, cy - 44, 128, 88);
      [[x - 4, cy - 44], [x + 124, cy - 44], [x - 4, cy + 44], [x + 124, cy + 44]].forEach(([a, b]) => rr(a - 4, b - 4, 8, 8, 1, card)); break; }
    case 'game': { const x = cx - 100 + ((s * 60) % 200), y = cy + 20 - Math.abs(Math.sin(s * 3)) * 40; rr(cx - 120, cy + 34, 240, 8, 4, ink); rr(cx + 20, cy + 6, 40, 28, 4, sunk);
      g.fillStyle = acc; g.beginPath(); g.arc(x, y, 10, 0, 7); g.fill(); break; }
    case 'prompt': { rr(cx - 120, cy - 34, 240, 30, 15, card); g.strokeStyle = line; g.beginPath(); g.roundRect(cx - 120, cy - 34, 240, 30, 15); g.stroke();
      const k = RM ? 1 : Math.min(1, (s % 3) / 1.5); rr(cx - 108, cy - 23, 150 * k, 8, 4, sunk); rr(cx - 120, cy + 10, 240 * Math.max(0, k - .2), 46, 10, acc);
      rr(cx - 108, cy + 22, 120 * Math.max(0, k - .4), 7, 3, card); rr(cx - 108, cy + 36, 170 * Math.max(0, k - .5), 7, 3, card); break; }
    case 'plug': { for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + s * .4, x = cx + Math.cos(a) * 62, y = cy + Math.sin(a) * 50;
        g.strokeStyle = line; g.beginPath(); g.moveTo(cx, cy); g.lineTo(x, y); g.stroke(); rr(x - 14, y - 14, 28, 28, 14, i % 2 ? sunk : card); g.beginPath(); g.arc(x, y, 14, 0, 7); g.stroke(); }
      g.fillStyle = acc; g.beginPath(); g.arc(cx, cy, 18, 0, 7); g.fill(); break; }
  }
}

/* ---------- one frame loop for every canvas on the page ---------- */
const canv = [];
$$('canvas[data-k]').forEach(c => { watch(c); canv.push([c, t => toolArt(c, c.dataset.k, t)]); });
$$('[data-board] canvas').forEach((c, i) => { watch(c); canv.push([c, t => paintShot(c, i, t)]); });
$$('canvas[data-voice]').forEach(c => { watch(c); canv.push([c, t => voiceFrame(c, t)]); });
if (canv.length) {
  let first = true;
  const frame = t => {
    canv.forEach(([c, draw]) => { if ((first || visible(c)) && c.offsetParent) draw(t); });
    first = false;
    if (!RM) requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
  if (RM) addEventListener('resize', () => canv.forEach(([c, d]) => c.offsetParent && d(0)));
}

/* ---------- the tool tour: changes by itself every 7 s, her tap pauses it ---------- */
$$('[data-switch]').forEach(sw => {
  const tabs = $$('.tab', sw), scenes = $$('.scene', sw);
  let idx = 0, timer = null, run = 0;
  const play = async key => {
    const sc = scenes.find(s => s.dataset.scene === key), id = ++run;
    if (key === 'web') await buildSite($('[data-site]', sc));
    if (key === 'app') { const p = $('[data-phone]', sc); for (let i = 0; i < 3 && id === run; i++) { await wait(1800); if (id === run && p._next) await p._next(); } }
    if (key === 'code') await codeRun($('[data-code]', sc));
    if (key === 'pc') await pcRun($('[data-pc]', sc));
    if (key === 'emp') { const st = $('[data-live]', sc); if (st) { st.textContent = 'reading'; st.className = 'st'; if (!RM) { await wait(2400); if (id === run) { st.textContent = 'done'; st.className = 'st ok'; } } } }
  };
  const select = (i, user) => {
    idx = (i + tabs.length) % tabs.length;
    tabs.forEach((t, k) => { t.setAttribute('aria-selected', String(k === idx)); t.tabIndex = k === idx ? 0 : -1; });
    const key = tabs[idx].dataset.s;
    scenes.forEach(s => s.classList.toggle('on', s.dataset.scene === key));
    const bar = $('.prog i', tabs[idx]); bar.style.animation = 'none'; bar.offsetWidth; bar.style.animation = '';
    play(key);
    clearTimeout(timer);
    sw.classList.toggle('paused', !!user);
    if (RM) return;
    timer = setTimeout(() => { if (visible(sw)) select(idx + 1); else watchers.set(sw, () => select(idx + 1)); }, user ? 14000 : 7000);
  };
  tabs.forEach((t, i) => t.addEventListener('click', () => select(i, true)));
  sw.addEventListener('keydown', e => {
    const d = {ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1}[e.key];
    if (d && e.target.classList.contains('tab')) { e.preventDefault(); select(idx + d, true); tabs[idx].focus(); }
  });
  watch(sw, () => { watchers.delete(sw); select(idx); });
});

/* ---------- choice groups: a row of buttons that shows one panel (roles, tiers, regions, screens) ---------- */
$$('[data-choose]').forEach(g => {
  const btns = $$('[data-pick]', g), scope = g.dataset.choose ? $(g.dataset.choose) : document;
  const show = v => {
    btns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.pick === v)));
    $$(`[data-of="${g.id}"]`, scope).forEach(p => { p.hidden = p.dataset.panel !== v; });
  };
  btns.forEach(b => b.addEventListener('click', () => { g.dataset.user = '1'; show(b.dataset.pick); }));
  // the quality sheet walks through its levels by itself until she picks one
  if (g.dataset.auto && !RM) {
    let i = btns.findIndex(b => b.getAttribute('aria-pressed') === 'true');
    setInterval(() => { if (!g.dataset.user && visible(g)) { i = (i + 1) % btns.length; show(btns[i].dataset.pick); } }, +g.dataset.auto);
    watch(g);
  }
});

/* ---------- small one-shot scenes ---------- */
$$('[data-pipe]').forEach(p => loop(p, async () => {           // a knock passing its five checks
  const cs = $$('.chk', p); cs.forEach(c => c.classList.remove('ok'));
  for (const c of cs) { if (!RM) await wait(650); c.classList.add('ok'); }
}, 3500));
$$('[data-ladder]').forEach(l => loop(l, async () => {          // the trust ladder climbing
  const L = $$('i', l);
  for (let k = 0; k < L.length; k++) { L.forEach((x, i) => x.classList.toggle('on', i <= k)); if (!RM) await wait(900); }
}, 2500));
$$('[data-flowsteps]').forEach(f => loop(f, async () => {      // the four steps lighting in turn
  const s = $$(':scope > div', f);
  for (let k = 0; k < s.length; k++) { s.forEach((x, i) => x.classList.toggle('lit', i === k)); if (!RM) await wait(1300); }
}, 600));

/* ---------- the real Create Studio screens ---------- */
$$('[data-shots]').forEach(v => {
  const imgs = $$('img', v), btns = $$('[data-shot]', v.parentElement);
  let i = 0, user = false;
  const show = k => { i = k; imgs.forEach((im, j) => im.classList.toggle('on', j === k)); btns.forEach((b, j) => b.setAttribute('aria-pressed', String(j === k))); };
  btns.forEach((b, k) => b.addEventListener('click', () => { user = true; show(k); }));
  watch(v);
  if (!RM) setInterval(() => { if (!user && visible(v)) show((i + 1) % imgs.length); }, 4200);
});
})();
