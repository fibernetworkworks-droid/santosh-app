/* HOOLA DESIGN - D7 bridge C: "Send to App Studio" (docs/HOOLA_DESIGN_PLAN.md section 7 C).
   Select one or more frames (each is one screen of the app) -> context menu / main menu / palette "Send to App
   Studio…" -> a dialog: a NEW app (with a line of what it is for) or one of her existing apps, every frame as a
   thumbnail with its size class and a warning when it is not a phone / tablet size -> Send.
   On Send each frame is drawn with HD.render.toCanvas at 2x (HD.render.ready first, so its images and fonts are in),
   made a PNG and sent as base64 in ONE JSON request: POST /api/design/files/<id>/to-app {nodes, app?, brief?,
   pictures: {frame id: base64 PNG}}. Caps (the server checks them again): 3 MB a picture, 16 MB together - a picture
   over the cap is drawn again smaller, then left out (App Studio reads the structure either way).
   The server matches each frame to a screen of the app and hands it to App Studio through App Studio's own inputs;
   nothing is approved, built or published here - the screens wait for HER OK in App Studio. The dialog says so and
   links to the app. Every text from the document or the server is set with textContent. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h;
  const PICTURE_MAX = 3 * 1024 * 1024, PICTURES_MAX = 16 * 1024 * 1024, MAX_FRAMES = 20;
  const FRAMES = {FRAME: 1, COMPONENT: 1, INSTANCE: 1};
  const S = () => HD.store;
  const canEdit = () => !!(HD.app && HD.app.file) && !!(HD.tools && HD.tools.u && HD.tools.u.canEdit());
  const fileOf = () => (HD.app && HD.app.file) || null;
  const st = {busy: false};

  /* ---------------------------------------------------------------- which frames */
  function topFrame(id) {
    const s = S();
    let cur = id, guard = 0;
    while (cur && s.has(cur) && guard++ < 400) {
      const n = s.get(cur), par = n && n.parent, pn = par ? s.get(par) : null;
      if (pn && pn.type === 'PAGE') return FRAMES[n.type] ? cur : null;
      cur = par;
    }
    return null;
  }
  function framesOf(ids) {
    const out = [];
    for (const id of ids || []) { const f = topFrame(id); if (f && out.indexOf(f) < 0) out.push(f); }
    return out;
  }
  function selected() { return HD.sel && HD.sel.ids ? Array.from(HD.sel.ids).filter(id => S().has(id)) : []; }
  function sizeClass(w, hh) {
    const a = Math.min(w, hh), b = Math.max(w, hh), orient = hh >= w ? 'portrait' : 'landscape';
    if (a >= 300 && a <= 500 && b <= 1100) return {cls: 'phone', orient: orient};
    if (a >= 560 && a <= 1100 && b <= 1400) return {cls: 'tablet', orient: orient};
    return {cls: 'other', orient: orient};
  }
  function num(id, k, d) { const v = S().prop(id, k); return typeof v === 'number' && isFinite(v) ? v : d; }

  /* ---------------------------------------------------------------- pictures */
  function canvasPng(cv) {
    return new Promise((res, rej) => {
      try { cv.toBlob(b => (b ? res(b) : rej(new Error('The picture could not be made.'))), 'image/png'); } catch (e) { rej(e); }
    });
  }
  function b64(blob) {
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result || '').split(',').pop());
      r.onerror = () => rej(new Error('The picture could not be read.'));
      r.readAsDataURL(blob);
    });
  }
  async function picture(id) {
    try { await HD.render.ready(id, 6000); } catch (e) { /* drawn with what has arrived */ }
    for (const scale of [2, 1, 0.75]) {
      const cv = HD.render.toCanvas(id, scale, {});
      if (!cv) return null;
      const blob = await canvasPng(cv);
      if (blob.size <= PICTURE_MAX) return {data: await b64(blob), size: blob.size};
    }
    return null;
  }
  function thumb(id) {
    const w = Math.max(1, num(id, 'w', 100)), hh = Math.max(1, num(id, 'h', 100));
    const k = Math.min(96 / w, 128 / hh, 1);
    try { const cv = HD.render.toCanvas(id, k, {}); if (cv) { cv.className = 'hdba-cv'; return cv; } } catch (e) { /* no picture */ }
    return h('span', {class: 'hdba-cv hdba-none', text: 'No preview'});
  }

  /* ---------------------------------------------------------------- the dialog */
  async function open(ids) {
    if (!canEdit()) { ui.toast('This file is view only.'); return; }
    let frames = framesOf(ids && ids.length ? ids : selected());
    if (!frames.length) { ui.toast('Select one or more frames first: each frame is one screen of the app.'); return; }
    if (frames.length > MAX_FRAMES) { ui.toast('Send at most ' + MAX_FRAMES + ' frames at a time.', true); frames = frames.slice(0, MAX_FRAMES); }
    const file = fileOf();
    let apps = [], appsErr = '';
    try { const got = await ui.api('GET', '/api/apps'); apps = (got && got.apps) || []; } catch (e) { appsErr = (e && e.message) || 'Your apps could not be listed.'; }
    const choice = {mode: apps.length ? 'existing' : 'new', app: apps.length ? String(apps[0].id) : ''};

    const modeNew = h('button', {type: 'button', class: 'hdba-seg', 'aria-pressed': 'false', text: 'A new app'});
    const modeOld = h('button', {type: 'button', class: 'hdba-seg', 'aria-pressed': 'false', text: 'One of my apps', disabled: !apps.length});
    const brief = h('input', {class: 'hdba-in', type: 'text', maxlength: '600', value: (file && file.name) || '', 'aria-label': 'What is the app for?',
      placeholder: 'What is the app for? For example: my sweet shop, home delivery'});
    const pick = h('select', {class: 'hdba-in', 'aria-label': 'Which app'});
    for (const a of apps) pick.appendChild(h('option', {value: String(a.id), text: (a.number ? a.number + '  ' : '') + (a.name || a.field_label || 'App') + '  (' + (a.status || '') + ')'}));
    pick.addEventListener('change', () => { choice.app = pick.value; });
    const newRow = h('label', {class: 'hdba-lab'}, h('span', {text: 'What is the app for?'}), brief);
    const oldRow = h('label', {class: 'hdba-lab'}, h('span', {text: 'Which app'}), pick);
    const paintMode = () => {
      modeNew.setAttribute('aria-pressed', String(choice.mode === 'new')); modeOld.setAttribute('aria-pressed', String(choice.mode === 'existing'));
      newRow.hidden = choice.mode !== 'new'; oldRow.hidden = choice.mode !== 'existing';
    };
    modeNew.addEventListener('click', () => { choice.mode = 'new'; paintMode(); });
    modeOld.addEventListener('click', () => { choice.mode = 'existing'; paintMode(); });

    const list = h('div', {class: 'hdba-list'});
    let others = 0;
    for (const id of frames) {
      const n = S().get(id), w = num(id, 'w', 100), hh = num(id, 'h', 100), sc = sizeClass(w, hh);
      if (sc.cls === 'other') others++;
      list.appendChild(h('div', {class: 'hdba-item'}, thumb(id),
        h('div', {class: 'hdba-meta'}, h('strong', {text: (n && n.name) || 'Frame'}),
          h('span', {class: 'hdba-tag ' + sc.cls, text: sc.cls === 'other' ? Math.round(w) + ' x ' + Math.round(hh) + ' - not a phone size' : sc.cls + ' ' + Math.round(w) + ' x ' + Math.round(hh)}),
          sc.cls === 'other' ? h('span', {class: 'hdba-warn', text: 'App Studio designs for phones: this screen will be laid out for a phone.'}) :
            sc.orient === 'landscape' ? h('span', {class: 'hdba-warn', text: 'Landscape: App Studio designs portrait screens first.'}) : null)));
    }
    const note = h('p', {class: 'hdba-note', text: 'Each frame becomes the design of the matching screen (by its name: Login, Home, Cart …). Nothing is approved, built or published here: the screens wait for your OK in App Studio.'});
    const status = h('p', {class: 'hdba-status', role: 'status', 'aria-live': 'polite', text: appsErr});
    const result = h('div', {class: 'hdba-result', hidden: true});
    const cancel = h('button', {type: 'button', class: 'hd-btn', text: 'Cancel', on: {click: () => ui.closeModal()}});
    const go = h('button', {type: 'button', class: 'hd-btn pri', text: frames.length === 1 ? 'Send 1 screen' : 'Send ' + frames.length + ' screens'});
    go.addEventListener('click', () => { send(frames, choice, brief, go, status, result, list).catch(() => {}); });
    ui.modal('hdba-dialog', 'Send to App Studio', [
      h('div', {class: 'hd-sheethead'}, h('h2', {text: 'Send to App Studio'}), h('button', {type: 'button', class: 'hd-ib', title: 'Close', 'aria-label': 'Close', on: {click: () => ui.closeModal()}}, ui.icon('close'))),
      h('div', {class: 'hdba-body'},
        h('div', {class: 'hdba-segs', role: 'group', 'aria-label': 'Where to'}, modeNew, modeOld), newRow, oldRow,
        others ? h('p', {class: 'hdba-warn', text: others === 1 ? 'One frame is not a phone or tablet size.' : others + ' frames are not a phone or tablet size.'}) : null,
        list, note, result),
      h('div', {class: 'hdba-foot'}, status, cancel, go)]);
    paintMode();
    go.focus({preventScroll: true});
  }

  async function send(frames, choice, brief, go, status, result, list) {
    if (st.busy) return;
    const file = fileOf();
    if (!file) return;
    st.busy = true; go.disabled = true;
    try {
      const pictures = {};
      let total = 0, dropped = 0;
      for (let i = 0; i < frames.length; i++) {
        status.textContent = 'Making picture ' + (i + 1) + ' of ' + frames.length + '…';
        let pic = null;
        try { pic = await picture(frames[i]); } catch (e) { pic = null; }
        if (pic && total + pic.size <= PICTURES_MAX) { pictures[frames[i]] = pic.data; total += pic.size; } else dropped++;
      }
      status.textContent = 'Sending to App Studio…';
      const body = {nodes: frames, pictures: pictures};
      if (choice.mode === 'existing' && choice.app) body.app = choice.app; else body.brief = String(brief.value || '').trim();
      const out = await ui.api('POST', '/files/' + encodeURIComponent(file.id) + '/to-app', body);
      showResult(out, result, dropped);
      list.hidden = true;
      status.textContent = '';
      go.hidden = true;
    } catch (e) {
      status.textContent = (e && e.message) || 'App Studio did not take the screens.';
      go.disabled = false;
    } finally { st.busy = false; }
  }

  const STATE = {drawing: 'App Studio is drawing it from your design', saved: 'Saved on the screen', waiting_plan: 'On the app plan, waiting for your OK',
    not_matched: 'Not matched to a screen: rename the frame (Login, Home, Cart …)', duplicate: 'Another frame was used for this screen'};
  function showResult(out, el, dropped) {
    while (el.firstChild) el.removeChild(el.firstChild);
    el.hidden = false;
    const app = out.app || {};
    el.appendChild(h('p', {class: 'hdba-say', text: (app.created ? 'New app plan ' : '') + (app.number ? app.number + ' ' : '') + (app.name || 'App') + ': ' + (out.say || '')}));
    const ul = h('ul', {class: 'hdba-rows'});
    for (const s of out.screens || []) ul.appendChild(h('li', null, h('strong', {text: s.name}), h('span', {text: s.screen ? ' -> ' + (s.label || s.screen) + (s.added ? ' (new screen)' : '') : ''}),
      h('span', {class: 'hdba-st', text: ' - ' + (STATE[s.state] || s.state || '')})));
    el.appendChild(ul);
    const warns = (out.warnings || []).slice();
    if (dropped) warns.push(dropped === 1 ? 'One picture was too large to send; its structure went.' : dropped + ' pictures were too large to send; their structure went.');
    for (const w of warns) el.appendChild(h('p', {class: 'hdba-warn', text: w}));
    const url = String(out.url || '');
    if (/^\/console\/apps#\/app\/[\w-]+$/.test(url)) el.appendChild(h('a', {class: 'hd-btn pri hdba-open', href: url, target: '_blank', rel: 'noopener', text: 'Open in App Studio'}));
  }

  /* ---------------------------------------------------------------- where it is offered */
  ui.registerMenu('context', ids => (framesOf(ids).length && canEdit() ? {label: 'Send to App Studio…', icon: 'export', run: () => { open(ids); }} : null));
  ui.registerMenu('main', {label: 'Send to App Studio…', icon: 'export', run: () => { open(selected()); }});
  ui.command({id: 'send-to-app', label: 'Send frames to App Studio', group: 'Other', edit: true, run: () => { open(selected()); }});

  HD.bridgeApp = {open: open, framesOf: framesOf, sizeClass: sizeClass};
})();
