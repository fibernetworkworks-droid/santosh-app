// From the owner's hoola-browser package (Hoola Browser Operator MCP), with inForm / autocomplete added for the gates.
// Page snapshot for an AI: interactive elements with short refs, plus headings, alerts and visible text.
// Walks open shadow roots. Marks elements with data-hoola-ref so actions can find them again.
(args) => {
  const { prefix, maxElements, maxText } = args;
  const SENSITIVE = /(password|passcode|\botp\b|one.?time|\bm?pin\b(?!\s*code)|cvv|cvc|card.?number|aadhaa?r|\bpan\b|account.?number|ifsc)/i;
  const CAPTCHA = /(captcha|recaptcha|hcaptcha|turnstile|cf-chl|verify you are human|i'?m not a robot)/i;
  const INTER = 'a[href],button,input,select,textarea,summary,[role=button],[role=link],[role=checkbox],[role=radio],' +
    '[role=tab],[role=menuitem],[role=option],[role=combobox],[role=textbox],[role=switch],[role=searchbox],' +
    '[contenteditable=""],[contenteditable=true]';

  const all = [];
  (function walk(root) {
    for (const el of root.querySelectorAll('*')) {
      all.push(el);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  })(document);
  // Refs stay attached to the same element across snapshots of the same document, so an AI holding ref e7
  // never ends up clicking a different element after the page updates. A new document gets a new docId.
  if (!window.__hoolaDoc) { window.__hoolaDoc = Math.random().toString(36).slice(2, 10); window.__hoolaSeq = 0; }

  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
  function visible(el) {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && parseFloat(s.opacity || '1') > 0.02;
  }
  function textById(ids) {
    return norm(ids.split(/\s+/).map((id) => { const e = document.getElementById(id); return e ? e.innerText || e.textContent : ''; }).join(' '));
  }
  function labelText(l) {
    // text of a label without the text of controls inside it (e.g. <label>Title <select>..options..</select></label>)
    const c = l.cloneNode(true);
    c.querySelectorAll('select,input,textarea,button,option').forEach((x) => x.remove());
    return norm(c.textContent);
  }
  function labelOf(el) {
    let t = '';
    if (el.labels && el.labels.length) t = norm(Array.from(el.labels).map(labelText).join(' '));
    if (!t) { const l = el.closest && el.closest('label'); if (l) t = labelText(l); }
    return t;
  }
  function nameOf(el) {
    const al = el.getAttribute('aria-label'); if (al) return norm(al);
    const lb = el.getAttribute('aria-labelledby'); if (lb) { const t = textById(lb); if (t) return t; }
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (['input', 'select', 'textarea'].includes(tag)) {
      const l = labelOf(el); if (l) return l;
      if (['submit', 'button', 'reset'].includes(type) && el.value) return norm(el.value);
      const ph = el.getAttribute('placeholder'); if (ph) return norm(ph);
      const ti = el.getAttribute('title'); if (ti) return norm(ti);
      // text just before the field (common on old government sites: <td>Name</td><td><input></td>)
      let p = el.previousElementSibling, guard = 0;
      while (p && guard++ < 3) { const t = norm(p.innerText || p.textContent); if (t) return cut(t, 80); p = p.previousElementSibling; }
      const cell = el.closest('td,th');
      if (cell && cell.previousElementSibling) { const t = norm(cell.previousElementSibling.innerText); if (t) return cut(t, 80); }
      return el.getAttribute('name') || el.id || '';
    }
    if (tag === 'img') return norm(el.getAttribute('alt') || el.getAttribute('title') || '');
    let t = norm(el.innerText || el.textContent);
    if (!t) { const img = el.querySelector && el.querySelector('img[alt]'); if (img) t = norm(img.getAttribute('alt')); }
    if (!t) t = norm(el.getAttribute('title') || el.getAttribute('value') || '');
    return cut(t, 100);
  }
  function roleOf(el) {
    const r = el.getAttribute('role'); if (r) return r;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || 'text').toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button' || tag === 'summary') return 'button';
    if (tag === 'select') return el.multiple ? 'listbox' : 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'input') {
      if (['submit', 'button', 'reset', 'image'].includes(type)) return 'button';
      if (['checkbox', 'radio', 'file', 'date', 'datetime-local', 'time', 'month', 'range', 'color'].includes(type)) return type;
      if (type === 'search') return 'searchbox';
      return 'textbox';
    }
    if (el.isContentEditable) return 'textbox';
    return tag;
  }
  function cssPath(el) {
    const parts = [];
    while (el && el.nodeType === 1 && parts.length < 6) {
      let s = el.tagName.toLowerCase();
      if (el.id && /^[A-Za-z][\w-]*$/.test(el.id)) { parts.unshift(s + '#' + el.id); break; }
      const p = el.parentElement;
      if (p) { const sib = Array.from(p.children).filter((c) => c.tagName === el.tagName); if (sib.length > 1) s += `:nth-of-type(${sib.indexOf(el) + 1})`; }
      parts.unshift(s);
      el = p;
    }
    return parts.join('>');
  }

  const items = [];
  let n = 0;
  const vh = window.innerHeight;
  for (const el of all) {
    if (!el.matches || !el.matches(INTER)) continue;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && type === 'hidden') continue;
    let vis = visible(el);
    // custom-styled checkboxes/radios/file inputs are often invisible while their label is visible
    if (!vis && tag === 'input' && ((el.labels && Array.from(el.labels).some(visible)) || type === 'file')) vis = true;
    if (!vis) continue;
    if (n >= maxElements) break;
    n++;
    let ref = el.getAttribute('data-hoola-ref');
    if (!ref) { ref = prefix + 'e' + (++window.__hoolaSeq); el.setAttribute('data-hoola-ref', ref); }
    const role = roleOf(el);
    const name = nameOf(el);
    const label = ['input', 'select', 'textarea'].includes(tag) ? labelOf(el) : '';
    const sensitive = type === 'password' || SENSITIVE.test(name + ' ' + (el.getAttribute('name') || '') + ' ' + (el.id || ''));
    const it = {
      ref, role, name: cut(name, 120), tag, type, label: cut(label, 120),
      id: el.id || '', nameAttr: el.getAttribute('name') || '', placeholder: el.getAttribute('placeholder') || '',
      href: tag === 'a' ? (el.getAttribute('href') || '') : '', css: cssPath(el),
      required: !!el.required || el.getAttribute('aria-required') === 'true',
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      inView: (() => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < vh; })(),
      sensitive,
      inForm: !!(el.form || (el.closest && el.closest('form'))),
      autocomplete: el.getAttribute('autocomplete') || '',
      captcha: CAPTCHA.test([name, el.id, el.getAttribute('name'), el.className && String(el.className), el.getAttribute('placeholder')].join(' ')),
    };
    if (['input', 'textarea'].includes(tag) && !['checkbox', 'radio', 'file', 'submit', 'button'].includes(type)) {
      it.value = sensitive && el.value ? '•••' : cut(el.value || '', 80);
    }
    if (el.isContentEditable) it.value = cut(norm(el.innerText), 80);
    if (['checkbox', 'radio'].includes(type) || ['checkbox', 'radio', 'switch'].includes(el.getAttribute('role'))) {
      it.checked = type ? !!el.checked : el.getAttribute('aria-checked') === 'true';
      if (type === 'radio') it.group = el.getAttribute('name') || '';
    }
    if (type === 'file') it.files = el.files ? Array.from(el.files).map((f) => f.name) : [];
    if (tag === 'select') {
      it.options = Array.from(el.options).slice(0, 40).map((o) => norm(o.text));
      it.selected = el.selectedIndex >= 0 ? norm(el.options[el.selectedIndex].text) : '';
    }
    items.push(it);
  }

  const headings = all.filter((e) => /^H[1-3]$/.test(e.tagName) && visible(e)).slice(0, 12)
    .map((e) => '#'.repeat(+e.tagName[1]) + ' ' + cut(norm(e.innerText), 100));
  const alerts = all.filter((e) => e.matches && e.matches('[role=alert],[aria-live=assertive],.error,.alert,.alert-danger,.invalid-feedback,.error-message,.text-danger') && visible(e))
    .map((e) => cut(norm(e.innerText), 160)).filter(Boolean).slice(0, 8);
  const captchaEls = all.filter((e) => {
    if (!e.matches) return false;
    if (e.tagName === 'IFRAME' && CAPTCHA.test(e.src || '')) return true;
    if (['IMG', 'SVG', 'svg', 'CANVAS', 'DIV', 'SPAN'].includes(e.tagName) &&
        CAPTCHA.test((e.src || '') + ' ' + (e.id || '') + ' ' + (e.getAttribute && (e.getAttribute('alt') || '')) + ' ' +
                     (typeof e.className === 'string' ? e.className : (e.className && e.className.baseVal) || ''))) return visible(e);
    if (e.classList && (e.classList.contains('g-recaptcha') || e.classList.contains('h-captcha') || e.classList.contains('cf-turnstile'))) return true;
    return false;
  }).map((e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : ''));
  const text = maxText > 0 ? cut(norm(document.body ? document.body.innerText : ''), maxText) : '';
  return { doc: window.__hoolaDoc, url: location.href, title: document.title, items, headings, alerts, captcha: captchaEls, text, truncated: n >= maxElements };
}
