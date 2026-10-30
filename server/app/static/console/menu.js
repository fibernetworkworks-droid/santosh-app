/* v0.285 MENUS LIKE CLAUDE: one dropdown for the whole console (chat ⋯ menus, export, the account menu).
   Claude's look: a plain surface with a hairline border and a soft shadow, 12px corners, rows 32px high in the
   interface sans at 14px / 400 (never bold), a 16px line icon in a muted grey, 8px row corners, a grey hover,
   hairline separators, a small grey header line, Delete in red, a tick on the right for the current choice.
   Opens in 120ms (fade + 3% scale from the anchor's side), below the button or above when there is no room; closes
   on a pick, an outside press, Esc (focus goes back to the button), Tab, scroll or resize. Keys: ↑ ↓ Home End,
   Enter / Space, a letter jumps to the next item starting with it. One menu at a time.
   window.HoolaMenu.open(anchor, items, {align: 'start'|'end', place: 'below'|'above', cls, label, width, keyboard})
   items: {label, icon, sub, kbd, danger, checked (true / false = a choice), disabled, run} | {sep: true} | {header} */
'use strict';
window.HoolaMenu = (() => {
const P = {
  pencil: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  pin: '<path d="M12 17v4"/><path d="M8 4h8l-1 6 3 3v2H6v-2l3-3z"/>',
  unpin: '<path d="M12 17v4"/><path d="M8 4h8l-1 6 3 3v2H6v-2l3-3z"/><path d="M4 4l16 16"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  compress: '<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>',
  archive: '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8M10 12h4"/>',
  restore: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  trash: '<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M10 11v6M14 11v6"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  braces: '<path d="M8 4H7a2 2 0 0 0-2 2v4a2 2 0 0 1-2 2 2 2 0 0 1 2 2v4a2 2 0 0 0 2 2h1M16 4h1a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2 2 2 0 0 0-2 2v4a2 2 0 0 1-2 2h-1"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  keyboard: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  library: '<path d="M4 4h16v5H4zM4 11h7v9H4zM13 11h7v9h-7z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
};
const icon = k => P[k] ? `<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[k]}</svg>` : '';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
let M = null;          // {el, anchor, items, onClose}

function close(focusBack) {
  if (!M) return;
  const {el, anchor, onClose} = M; M = null;
  anchor?.setAttribute('aria-expanded', 'false');
  el.classList.remove('on'); el.remove();
  removeEventListener('pointerdown', outside, true); removeEventListener('resize', onResize);
  removeEventListener('scroll', onScroll, true); removeEventListener('blur', onBlur);
  if (focusBack) anchor?.focus?.({preventScroll: true});
  onClose?.();
}
function outside(e) { if (M && !M.el.contains(e.target) && !M.anchor.contains(e.target)) close(false); }
function onResize() { close(false); }
function onScroll(e) { if (M && !M.el.contains(e.target)) close(false); }
function onBlur() { close(false); }

function open(anchor, items, opts = {}) {
  if (M && M.anchor === anchor) { close(true); return null; }        // the same button again = close (a toggle)
  close(false);
  const el = document.createElement('div');
  el.className = 'hmenu' + (opts.cls ? ' ' + opts.cls : '');
  el.setAttribute('role', 'menu'); el.tabIndex = -1;
  if (opts.label) el.setAttribute('aria-label', opts.label);
  const live = [];
  el.innerHTML = items.map(it => {
    if (it.sep) return '<div class="msep" role="separator"></div>';
    if (it.header) return `<div class="mh" role="presentation" title="${esc(it.header)}">${esc(it.header)}</div>`;
    const i = live.push(it) - 1, choice = typeof it.checked === 'boolean';
    return `<button type="button" class="mi${it.danger ? ' danger' : ''}" role="${choice ? 'menuitemradio' : 'menuitem'}"${choice ? ` aria-checked="${it.checked}"` : ''}`
      + `${it.disabled ? ' aria-disabled="true"' : ''} data-mi="${i}" tabindex="-1">${icon(it.icon)}`
      + `<span class="mt"><span>${esc(it.label)}</span>${it.sub ? `<small>${esc(it.sub)}</small>` : ''}</span>`
      + `${it.kbd ? `<kbd class="mk">${esc(it.kbd)}</kbd>` : ''}${choice ? `<span class="mc">${it.checked ? icon('check') : ''}</span>` : ''}</button>`;
  }).join('');
  document.body.appendChild(el);
  // place: below the button (or above when there is no room), its start or end edge lined up with the button's
  const r = anchor.getBoundingClientRect(), gap = 6, pad = 8;
  if (opts.width) el.style.width = (opts.width === 'anchor' ? Math.max(r.width, 236) : opts.width) + 'px';
  const w = el.offsetWidth, h = el.offsetHeight;
  const roomBelow = innerHeight - r.bottom - gap - pad, roomAbove = r.top - gap - pad;
  const up = opts.place === 'above' ? roomAbove >= Math.min(h, 200) || roomAbove > roomBelow : h > roomBelow && roomAbove > roomBelow;
  el.style.maxHeight = Math.max(120, up ? roomAbove : roomBelow) + 'px';
  const left = opts.align === 'start' ? r.left : r.right - w;
  el.style.left = Math.round(Math.max(pad, Math.min(innerWidth - w - pad, left))) + 'px';
  if (up) el.style.bottom = Math.round(innerHeight - r.top + gap) + 'px'; else el.style.top = Math.round(r.bottom + gap) + 'px';
  el.style.transformOrigin = `${opts.align === 'start' ? 'left' : 'right'} ${up ? 'bottom' : 'top'}`;
  el.classList.toggle('up', up);
  anchor.setAttribute('aria-haspopup', 'menu'); anchor.setAttribute('aria-expanded', 'true');
  M = {el, anchor, items: live, onClose: opts.onClose};
  requestAnimationFrame(() => el.classList.add('on'));

  const btns = () => [...el.querySelectorAll('.mi:not([aria-disabled="true"])')];
  const focusAt = i => { const b = btns(); if (b.length) b[(i + b.length) % b.length].focus({preventScroll: true}); };
  if (opts.keyboard) focusAt(0); else el.focus({preventScroll: true});
  el.addEventListener('pointermove', e => { const b = e.target.closest('.mi'); if (b && document.activeElement !== b && b.getAttribute('aria-disabled') !== 'true') b.focus({preventScroll: true}); });
  el.addEventListener('pointerleave', () => { if (M?.el === el) el.focus({preventScroll: true}); });
  el.addEventListener('click', e => {
    const b = e.target.closest('.mi'); if (!b || b.getAttribute('aria-disabled') === 'true') return;
    const it = live[+b.dataset.mi]; close(true); it.run?.();
  });
  el.addEventListener('keydown', e => {
    const b = btns(), i = b.indexOf(document.activeElement);
    const to = {ArrowDown: i + 1, ArrowUp: i < 0 ? b.length - 1 : i - 1, Home: 0, End: b.length - 1}[e.key];
    if (to !== undefined) { e.preventDefault(); focusAt(to); }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(true); }
    else if (e.key === 'Tab') { e.preventDefault(); close(true); }
    else if ((e.key === 'Enter' || e.key === ' ') && i >= 0) { e.preventDefault(); b[i].click(); }
    else if (e.key.length === 1 && /\S/.test(e.key)) {          // a letter jumps to the next item starting with it
      const k = e.key.toLowerCase(), n = b.length;
      for (let s = 1; s <= n; s++) { const x = b[(i + s + n) % n]; if (x.textContent.trim().toLowerCase().startsWith(k)) { x.focus({preventScroll: true}); break; } }
    }
  });
  addEventListener('pointerdown', outside, true); addEventListener('resize', onResize);
  addEventListener('scroll', onScroll, true); addEventListener('blur', onBlur);
  return el;
}
return {open, close, isOpen: () => !!M, icon};
})();
