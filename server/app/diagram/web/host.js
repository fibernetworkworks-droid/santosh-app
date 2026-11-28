/* HOOLA DIAGRAM D3 - the page around the draw.io editor (/diagram-edit/<token>).

Sandboxed like every Hoola page (its own origin: it never sees the console's sign-in); it talks to the server ONLY with
the short-lived token in its own address, for this ONE diagram:
  - loads the diagram into the editor (draw.io's embed protocol);
  - her edits: the editor's autosave -> a moment of quiet -> the editor's own SVG export -> saved as her version;
  - her selection -> the server, so Hoola can "change only these";
  - Hoola's changes: polled, handed to the bridge inside the editor (one undoable step, outlined);
  - Download .drawio. Words come from window.HOOLA_WORDS (the server writes them in her language). */
(function () {
  'use strict';
  var C = window.HOOLA_DIAGRAM || {}, W = window.HOOLA_WORDS || {};
  var BASE = '/api/diagram/live/' + encodeURIComponent(C.token || '');
  var ed = document.getElementById('ed'), st = document.getElementById('st');
  var applied = 0, loaded = false, timer = 0, busy = false, again = false, lastXml = '', polling = 0, wantSvg = false;
  function say(k, n) { st.textContent = (W[k] || k).replace('{n}', n == null ? '' : n); st.dataset.state = k; }
  function post(m) { try { ed.contentWindow.postMessage(JSON.stringify(m), '*'); } catch (e) {} }
  function call(method, path, body) {
    return fetch(BASE + path, {method: method, headers: body ? {'Content-Type': 'application/json'} : {},
                               body: body ? JSON.stringify(body) : undefined, credentials: 'omit', cache: 'no-store'})
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j.status = r.status; return j; }); });
  }
  function saveNow(svg) {
    if (busy) { again = true; return; }
    busy = true; say('saving');
    call('POST', '/save', {xml: lastXml, svg: svg || '', applied_rev: applied}).then(function (r) {
      busy = false;
      if (r.ok) { applied = Math.max(applied, r.rev || 0); say(r.changed ? 'saved' : 'uptodate'); }
      else if (r.stale) { say('syncing'); poll(); again = true; }
      else say('notsaved');
      if (again) { again = false; setTimeout(function () { wantSvg = true; post({action: 'export', format: 'xmlsvg'}); }, 400); }
    }).catch(function () { busy = false; say('offline'); });
  }
  function poll() {
    call('GET', '/poll?rev=' + applied).then(function (r) {
      (r.changes || []).forEach(function (ch) {
        if (ch.rev <= applied) return;
        post({type: 'hoola:apply', rev: ch.rev, ops: ch.ops || null, model: ch.model || null, ids: ch.ids || []});
        say('hoola', (ch.ids || []).length);
      });
    }).catch(function () {});
  }
  window.addEventListener('message', function (e) {
    if (e.source !== ed.contentWindow) return;
    var m; try { m = JSON.parse(e.data); } catch (x) { return; }
    if (!m) return;
    if (m.event === 'init') {
      call('GET', '/state').then(function (s) {
        if (!s.xml) { say('gone'); return; }
        applied = s.rev || 0;
        post({action: 'load', xml: s.xml, autosave: 1, title: s.title || ''});
      });
    } else if (m.event === 'load') {
      loaded = true; say('ready');
      clearInterval(polling); polling = setInterval(poll, 2500);
    } else if (m.event === 'autosave') {
      lastXml = m.xml || ''; clearTimeout(timer);
      timer = setTimeout(function () { wantSvg = true; post({action: 'export', format: 'xmlsvg'}); }, 1200);
    } else if (m.event === 'export' && wantSvg) {
      wantSvg = false; if (m.xml) lastXml = m.xml;
      var svg = '';
      try { svg = m.data && m.data.indexOf('base64,') > 0 ? atob(m.data.split('base64,')[1]) : (m.data || ''); } catch (x) { svg = ''; }
      saveNow(svg);
    } else if (m.type === 'hoola:selection') {
      call('POST', '/select', {ids: m.ids || []});
    } else if (m.type === 'hoola:applied') {
      applied = Math.max(applied, m.rev || 0);
    } else if (m.type === 'hoola:error') {
      say('notapplied');
    }
  });
  document.getElementById('dl').addEventListener('click', function () {
    var a = document.createElement('a'); a.href = BASE + '/file'; a.download = (C.title || 'diagram') + '.drawio';
    document.body.appendChild(a); a.click(); a.remove();
  });
  say('loading');
})();
