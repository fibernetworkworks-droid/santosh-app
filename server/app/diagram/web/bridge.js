/* HOOLA DIAGRAM D3 - Hoola's bridge INSIDE the draw.io editor page (served with index.html, never a vendored edit).

The editor runs in its own sandboxed origin; the page around it (host.js) cannot reach into it, so this small script
does the three things the embed protocol has no message for, and talks to the host by postMessage only:
  - her SELECTION: every change sends the selected cell ids up (so "change only these" works);
  - an AI CHANGE: applied as ONE undoable step (id by id - her other shapes, even unsaved, are untouched; or a whole
    new model when Hoola redrew it), then the changed cells are outlined for a few seconds (never part of the diagram);
  - nothing else: no network, no storage. Finding the editor = the same trick next-ai-draw-io uses (Apache-2.0): wrap a
    method draw.io calls on start, the first call hands over the EditorUi. */
(function () {
  'use strict';
  var ui = null, marks = [], fade = 0;
  function tell(m) { try { parent.postMessage(JSON.stringify(m), '*'); } catch (e) { /* host gone */ } }
  function hook(proto, name) {
    if (!proto || typeof proto[name] !== 'function' || proto[name].__hoola) return;
    var orig = proto[name];
    var wrapped = function () { if (!ui) { ui = this; ready(); } return orig.apply(this, arguments); };
    wrapped.__hoola = 1; proto[name] = wrapped;
  }
  var wait = setInterval(function () {
    if (window.EditorUi) { hook(window.EditorUi.prototype, 'updateActionStates'); if (window.App) hook(window.App.prototype, 'fileLoaded'); clearInterval(wait); }
  }, 20);
  function graph() { return ui && ui.editor && ui.editor.graph; }
  function ready() {
    tell({type: 'hoola:ready'});
    var g = graph();
    if (g && g.getSelectionModel) {
      var t = 0;
      g.getSelectionModel().addListener('change', function () {
        clearTimeout(t);
        t = setTimeout(function () {
          var ids = (g.getSelectionCells() || []).map(function (c) { return String(c.id); }).slice(0, 200);
          tell({type: 'hoola:selection', ids: ids});
        }, 250);
      });
    }
  }
  function clearMarks() { marks.forEach(function (h) { try { h.destroy(); } catch (e) {} }); marks = []; clearTimeout(fade); }
  function outline(ids) {
    clearMarks();
    var g = graph(); if (!g || !window.mxCellHighlight) return;
    (ids || []).slice(0, 200).forEach(function (id) {
      var c = g.model.getCell(id), st = c ? g.view.getState(c) : null; if (!st) return;
      var h = new mxCellHighlight(g, '#7C5CFF', 3); h.highlight(st); marks.push(h);
    });
    fade = setTimeout(clearMarks, 4000);
  }
  function num(v, d) { var n = Number(v); return isFinite(n) ? n : d; }
  function applyOps(ops) {
    var g = graph(), m = g.model, parent0 = g.getDefaultParent();
    m.beginUpdate();
    try {
      ops.forEach(function (o) {
        var id = String(o.id || ''), c = m.getCell(id);
        if (o.op === 'delete') { if (c) g.removeCells([c], true); return; }
        if (o.op === 'add') {
          if (c) return;
          var p = o.parent ? (m.getCell(String(o.parent)) || parent0) : parent0;
          if (o.edge) g.insertEdge(p, id, o.value || '', o.source ? m.getCell(String(o.source)) : null, o.target ? m.getCell(String(o.target)) : null, o.style || null);
          else g.insertVertex(p, id, o.value || '', num(o.x, 0), num(o.y, 0), num(o.width, 120), num(o.height, 60), o.style || null);
          return;
        }
        if (o.op === 'update' && c) {
          if ('value' in o) m.setValue(c, o.value == null ? '' : String(o.value));
          if ('style' in o) m.setStyle(c, o.style == null ? '' : String(o.style));
          if (o.source) m.setTerminal(c, m.getCell(String(o.source)), true);
          if (o.target) m.setTerminal(c, m.getCell(String(o.target)), false);
          if (['x', 'y', 'width', 'height'].some(function (k) { return k in o; }) && c.geometry) {
            var geo = c.geometry.clone();
            ['x', 'y', 'width', 'height'].forEach(function (k) { if (k in o) geo[k] = num(o[k], geo[k]); });
            m.setGeometry(c, geo);
          }
        }
      });
    } finally { m.endUpdate(); }       /* one endUpdate = one undo step: Ctrl+Z takes the whole AI change back */
  }
  function replaceAll(modelXml) {
    var g = graph(), m = g.model, doc = mxUtils.parseXml(modelXml).documentElement;
    m.beginUpdate();
    try { m.execute(new ReplaceDiagram(ui, doc)); } finally { m.endUpdate(); }
  }
  window.addEventListener('message', function (e) {
    if (e.source !== parent) return;
    var m; try { m = JSON.parse(e.data); } catch (x) { return; }
    if (!m || typeof m.type !== 'string' || m.type.indexOf('hoola:') !== 0 || !ui) return;
    try {
      if (m.type === 'hoola:apply') {
        if (m.ops && m.ops.length) applyOps(m.ops); else if (m.model) replaceAll(m.model);
        setTimeout(function () { outline(m.ids || []); }, 60);
        tell({type: 'hoola:applied', rev: m.rev});
      } else if (m.type === 'hoola:select') {
        var g = graph(); g.setSelectionCells((m.ids || []).map(function (id) { return g.model.getCell(String(id)); }).filter(Boolean));
      }
    } catch (err) { tell({type: 'hoola:error', message: String(err && err.message || err).slice(0, 300), rev: m.rev}); }
  });
})();
