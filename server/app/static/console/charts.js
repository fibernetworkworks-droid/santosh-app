/* HoolaChart (v0.353 DASHBOARD, MIT, Newtika). One small chart drawer for the Hoola console (her dashboard) AND for the
   websites Hoola builds (copied into a site as assets/hoola-chart.js). Inline SVG, no library, no network, nothing
   evaluated: bar, line, area, donut and hbar (sideways bars). Colours come from CSS (.hc + data-s="0..5"), so a site
   uses its own brand tokens and the console its own.

   On a website a section writes a plain table and Hoola draws it:
     <figure data-hoola-chart="bar" data-unit="₹" data-suffix=""><figcaption>Sales</figcaption>
       <table><thead><tr><th>Year</th><th>Sales</th></tr></thead><tbody><tr><th>2023</th><td>50 lakh</td></tr>...</tbody></table>
     </figure>
   The table stays in the page for screen readers (and is shown when no script runs).

   API: HoolaChart.draw(box, {type, labels, series: [{name, values}], unit, suffix, title, height})
        HoolaChart.fromTable(table) -> spec | null      HoolaChart.fmt(n, compact)      HoolaChart.auto(root) */
(function (root) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var TYPES = {bar: 1, line: 1, area: 1, donut: 1, hbar: 1};

  // ---------------------------------------------------------------- numbers the Indian way (1,20,000 / 1.2 L / 3.4 Cr)
  function trim(x) { return String(Math.round(x * 10) / 10).replace(/\.0$/, ''); }
  function group(n) {
    var neg = n < 0, s = String(Math.round(Math.abs(n) * 100) / 100), p = s.split('.'), i = p[0];
    var last = i.slice(-3), rest = i.slice(0, -3);
    if (rest) last = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last;
    return (neg ? '-' : '') + last + (p[1] ? '.' + p[1] : '');
  }
  function fmt(n, compact) {
    if (typeof n !== 'number' || !isFinite(n)) return '';
    var a = Math.abs(n);
    if (compact) {
      if (a >= 1e7) return trim(n / 1e7) + ' Cr';
      if (a >= 1e5) return trim(n / 1e5) + ' L';
      if (a >= 1e3) return trim(n / 1e3) + 'K';
      return trim(n);
    }
    return group(n);
  }
  function val(spec, n, compact) { return (spec.unit || '') + fmt(n, compact) + (spec.suffix || ''); }

  // "50 lakh", "₹2.5 Cr", "12k", "1,20,000", "45%" -> number
  function num(text) {
    var t = String(text || '').toLowerCase().replace(/,/g, '').replace(/\s+/g, ' ').trim();
    var m = t.match(/-?\d+(\.\d+)?/);
    if (!m) return null;
    var n = parseFloat(m[0]), after = t.slice(t.indexOf(m[0]) + m[0].length).trim();
    if (/^(cr|crore)/.test(after)) n *= 1e7;
    else if (/^(l\b|lakh|lac)/.test(after)) n *= 1e5;
    else if (/^(k\b|thousand|hazaar|hazar)/.test(after)) n *= 1e3;
    else if (/^(m\b|mn|million)/.test(after)) n *= 1e6;
    return n;
  }

  function fromTable(table) {
    if (!table) return null;
    var rows = [].slice.call(table.querySelectorAll('tr'));
    if (rows.length < 2) return null;
    var head = [].slice.call(rows[0].children).map(function (c) { return c.textContent.trim(); });
    var series = head.slice(1).map(function (h) { return {name: h, values: []}; });
    var labels = [];
    rows.slice(1).forEach(function (r) {
      var cells = [].slice.call(r.children);
      if (cells.length < 2) return;
      labels.push(cells[0].textContent.trim());
      series.forEach(function (s, i) { var c = cells[i + 1]; s.values.push(c ? num(c.textContent) : null); });
    });
    series = series.filter(function (s) { return s.values.some(function (v) { return v !== null; }); });
    if (!labels.length || !series.length) return null;
    return {labels: labels, series: series.slice(0, 6)};
  }

  // ---------------------------------------------------------------- drawing helpers
  function svgEl(tag, attrs, parent) {
    var x = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { if (attrs[k] !== null && attrs[k] !== undefined) x.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(x);
    return x;
  }
  function htmlEl(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text !== undefined) x.textContent = text; return x; }
  function niceStep(span, n) {
    var raw = span / Math.max(1, n), p = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10)), f = raw / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }
  function scale(spec) {
    var lo = 0, hi = 0;
    spec.series.forEach(function (s) { s.values.forEach(function (v) { if (v === null) return; lo = Math.min(lo, v); hi = Math.max(hi, v); }); });
    if (hi === lo) hi = lo + 1;
    var step = niceStep(hi - lo, 4), a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, ticks = [];
    for (var t = a; t <= b + step / 2; t += step) ticks.push(Math.round(t * 1e6) / 1e6);
    return {lo: a, hi: b, ticks: ticks};
  }
  function short(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + '…' : s; }

  function summary(spec) {
    var s = spec.series[0], best = -1;
    s.values.forEach(function (v, i) { if (v !== null && (best < 0 || v > s.values[best])) best = i; });
    var kind = {bar: 'Bar chart', line: 'Line chart', area: 'Area chart', donut: 'Donut chart', hbar: 'Bar chart'}[spec.type];
    return (spec.title ? spec.title + '. ' : '') + kind + ', ' + spec.labels.length + ' items' +
      (best >= 0 ? '; highest ' + spec.labels[best] + ' ' + val(spec, s.values[best]) : '') + '.';
  }

  // ---------------------------------------------------------------- the chart
  function draw(box, spec) {
    if (!box || !spec || !spec.series || !spec.series.length || !spec.labels || !spec.labels.length) return null;
    spec.type = TYPES[spec.type] ? spec.type : 'bar';
    box.classList.add('hc');
    box.textContent = '';
    var W = Math.max(240, Math.round(box.clientWidth || 600));
    var small = W < 480;
    var H = spec.height || (spec.type === 'donut' ? 220 : spec.type === 'hbar' ? Math.max(120, spec.labels.length * 34 + 16) : (small ? 220 : 260));
    var svg = svgEl('svg', {viewBox: '0 0 ' + W + ' ' + H, width: '100%', height: H, role: 'img', tabindex: '0',
      'aria-label': summary(spec), 'class': 'hc-svg' + (spec.animate === false ? '' : ' hc-in'), preserveAspectRatio: 'none'});
    box.appendChild(svg);
    var tip = htmlEl('div', 'hc-tip'); tip.hidden = true; box.appendChild(tip);
    var hits = [];   // [{x, y, w, h, lines, i}] for pointer + keyboard
    var many = spec.series.length > 1;

    if (spec.type === 'donut') donut(svg, spec, W, H, hits);
    else if (spec.type === 'hbar') hbar(svg, spec, W, H, hits);
    else xy(svg, spec, W, H, hits, small);

    if (many || spec.type === 'donut') legend(box, spec);
    wire(box, svg, tip, hits, W, H);
    return svg;
  }

  function xy(svg, spec, W, H, hits, small) {
    var sc = scale(spec), n = spec.labels.length;
    var left = 10 + 7 * Math.max.apply(null, sc.ticks.map(function (t) { return val(spec, t, true).length; }));
    var top = 10, bottom = 26, right = 8, ih = H - top - bottom, iw = W - left - right;
    var y = function (v) { return top + ih - (v - sc.lo) / (sc.hi - sc.lo) * ih; };
    var g = svgEl('g', {'class': 'hc-grid'}, svg);
    sc.ticks.forEach(function (t) {
      svgEl('line', {x1: left, x2: W - right, y1: y(t), y2: y(t), 'class': t === 0 ? 'hc-zero' : 'hc-gl'}, g);
      var tx = svgEl('text', {x: left - 6, y: y(t) + 4, 'text-anchor': 'end', 'class': 'hc-ax'}, g); tx.textContent = val(spec, t, true);
    });
    var band = iw / n, every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(iw / (small ? 44 : 64)))));
    spec.labels.forEach(function (l, i) {
      if (i % every) return;
      var tx = svgEl('text', {x: left + band * i + band / 2, y: H - 8, 'text-anchor': 'middle', 'class': 'hc-ax'}, g);
      tx.textContent = short(l, small ? 8 : 12);
    });
    var k = spec.series.length;
    if (spec.type === 'bar') {
      var gap = Math.min(band * 0.28, 18), bw = Math.max(2, (band - gap) / k);
      spec.series.forEach(function (s, si) {
        var gs = svgEl('g', {'data-s': si}, svg);
        s.values.forEach(function (v, i) {
          if (v === null) return;
          var x = left + band * i + gap / 2 + bw * si, y0 = y(Math.max(0, v)), h = Math.max(1, Math.abs(y(v) - y(0)));
          svgEl('rect', {x: x + 0.5, y: y0, width: Math.max(1, bw - 1), height: h, rx: Math.min(3, bw / 3), 'class': 'hc-bar'}, gs);
        });
      });
    } else {
      spec.series.forEach(function (s, si) {
        var gs = svgEl('g', {'data-s': si}, svg), d = '', first = null, last = null;
        s.values.forEach(function (v, i) {
          if (v === null) return;
          var px = left + band * i + band / 2, py = y(v);
          d += (d ? 'L' : 'M') + px.toFixed(1) + ' ' + py.toFixed(1);
          if (first === null) first = px; last = px;
        });
        if (!d) return;
        if (spec.type === 'area') svgEl('path', {d: d + 'L' + last.toFixed(1) + ' ' + y(Math.max(0, sc.lo)) + 'L' + first.toFixed(1) + ' ' + y(Math.max(0, sc.lo)) + 'Z', 'class': 'hc-area'}, gs);
        svgEl('path', {d: d, 'class': 'hc-line', pathLength: '1'}, gs);
        if (n <= 31) s.values.forEach(function (v, i) { if (v !== null) svgEl('circle', {cx: left + band * i + band / 2, cy: y(v), r: 3, 'class': 'hc-dot'}, gs); });
      });
    }
    var cursor = svgEl('line', {x1: 0, x2: 0, y1: top, y2: top + ih, 'class': 'hc-cur', visibility: 'hidden'}, svg);
    spec.labels.forEach(function (l, i) {
      hits.push({x: left + band * i, y: top, w: band, h: ih, i: i, cx: left + band * i + band / 2, cursor: cursor,
        lines: [l].concat(spec.series.map(function (s) { return (k > 1 ? s.name + ': ' : '') + (s.values[i] === null ? '-' : val(spec, s.values[i])); }))});
    });
  }

  function hbar(svg, spec, W, H, hits) {
    var s = spec.series[0], n = spec.labels.length, max = 0;
    s.values.forEach(function (v) { if (v !== null) max = Math.max(max, v); });
    max = max || 1;
    var lw = Math.min(W * 0.38, 8 + 7 * Math.max.apply(null, spec.labels.map(function (l) { return short(l, 22).length; })));
    var vw = 12 + 7 * val(spec, max, true).length, row = (H - 16) / n, bh = Math.min(22, row * 0.62);
    var gs = svgEl('g', {'data-s': 0}, svg);
    spec.labels.forEach(function (l, i) {
      var cy = 8 + row * i + row / 2, v = s.values[i] || 0, w = Math.max(2, (W - lw - vw) * v / max);
      var t = svgEl('text', {x: lw - 8, y: cy + 4, 'text-anchor': 'end', 'class': 'hc-lab'}, svg); t.textContent = short(l, 22);
      svgEl('rect', {x: lw, y: cy - bh / 2, width: W - lw - vw, height: bh, rx: 3, 'class': 'hc-track'}, svg);
      svgEl('rect', {x: lw, y: cy - bh / 2, width: w, height: bh, rx: 3, 'class': 'hc-bar hc-h'}, gs);
      var tv = svgEl('text', {x: lw + w + 6, y: cy + 4, 'class': 'hc-val'}, svg); tv.textContent = val(spec, v, true);
      hits.push({x: 0, y: cy - row / 2, w: W, h: row, i: i, lines: [l, val(spec, v)]});
    });
  }

  function donut(svg, spec, W, H, hits) {
    var s = spec.series[0], total = 0;
    s.values.forEach(function (v) { if (v > 0) total += v; });
    var cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 6, r = R * 0.62, a0 = -Math.PI / 2;
    if (!total) { svgEl('circle', {cx: cx, cy: cy, r: (R + r) / 2, 'class': 'hc-track hc-ring', 'stroke-width': R - r, fill: 'none'}, svg); }
    s.values.forEach(function (v, i) {
      if (!(v > 0)) return;
      var a1 = a0 + v / total * Math.PI * 2, g = svgEl('g', {'data-s': i % 6}, svg);
      if (v === total) {
        svgEl('circle', {cx: cx, cy: cy, r: (R + r) / 2, fill: 'none', 'stroke-width': R - r, 'class': 'hc-ring'}, g);
      } else {
        var big = a1 - a0 > Math.PI ? 1 : 0, p = function (rad, a) { return (cx + rad * Math.cos(a)).toFixed(2) + ' ' + (cy + rad * Math.sin(a)).toFixed(2); };
        svgEl('path', {d: 'M' + p(R, a0) + 'A' + R + ' ' + R + ' 0 ' + big + ' 1 ' + p(R, a1) + 'L' + p(r, a1) + 'A' + r + ' ' + r + ' 0 ' + big + ' 0 ' + p(r, a0) + 'Z', 'class': 'hc-slice'}, g);
      }
      var mid = (a0 + a1) / 2;
      hits.push({slice: true, a0: a0, a1: a1, cx: cx, cy: cy, r: r, R: R, i: i,
        tx: cx + (R + 4) * Math.cos(mid), ty: cy + (R + 4) * Math.sin(mid),
        lines: [spec.labels[i], val(spec, v) + ' (' + trim(100 * v / total) + '%)']});
      a0 = a1;
    });
    var t1 = svgEl('text', {x: cx, y: cy + 2, 'text-anchor': 'middle', 'class': 'hc-big'}, svg); t1.textContent = val(spec, total, true);
    var t2 = svgEl('text', {x: cx, y: cy + 20, 'text-anchor': 'middle', 'class': 'hc-ax'}, svg); t2.textContent = spec.totalLabel || 'Total';
  }

  function legend(box, spec) {
    var ul = htmlEl('ul', 'hc-leg');
    var names = spec.type === 'donut' ? spec.labels : spec.series.map(function (s) { return s.name; });
    names.forEach(function (nm, i) {
      if (spec.type === 'donut' && !(spec.series[0].values[i] > 0)) return;
      var li = htmlEl('li'), sw = htmlEl('span', 'hc-sw'); sw.setAttribute('data-s', i % 6); sw.setAttribute('aria-hidden', 'true');
      li.appendChild(sw); li.appendChild(document.createTextNode(nm));
      if (spec.type === 'donut') li.appendChild(htmlEl('b', '', ' ' + val(spec, spec.series[0].values[i], true)));
      ul.appendChild(li);
    });
    box.appendChild(ul);
  }

  // ---------------------------------------------------------------- tooltip: pointer + arrow keys
  function wire(box, svg, tip, hits, W, H) {
    if (!hits.length) return;
    var cur = -1;
    function show(i) {
      var h = hits[i]; cur = i;
      tip.textContent = '';
      h.lines.forEach(function (l, k) { tip.appendChild(htmlEl(k ? 'div' : 'strong', '', l)); });
      tip.hidden = false;
      var bw = box.clientWidth || W, sx = bw / W;
      var px = (h.slice ? h.tx : (h.cx !== undefined ? h.cx : h.x + h.w / 2)) * sx;
      var py = (h.slice ? h.ty : h.y + 8) * ((svg.getBoundingClientRect().height || H) / H);
      tip.style.left = Math.max(4, Math.min(bw - tip.offsetWidth - 4, px - tip.offsetWidth / 2)) + 'px';
      tip.style.top = Math.max(0, py - tip.offsetHeight - 8) + 'px';
      if (h.cursor) { h.cursor.setAttribute('x1', h.cx); h.cursor.setAttribute('x2', h.cx); h.cursor.setAttribute('visibility', 'visible'); }
      svg.querySelectorAll('.hc-on').forEach(function (e) { e.classList.remove('hc-on'); });
      var marks = svg.querySelectorAll(h.slice ? '[data-s="' + (h.i % 6) + '"]' : '.hc-bar, .hc-dot');
      if (h.slice) marks.forEach(function (e) { e.classList.add('hc-on'); });
    }
    function hide() { tip.hidden = true; cur = -1; hits.forEach(function (h) { if (h.cursor) h.cursor.setAttribute('visibility', 'hidden'); }); svg.querySelectorAll('.hc-on').forEach(function (e) { e.classList.remove('hc-on'); }); }
    svg.addEventListener('pointermove', function (e) {
      var r = svg.getBoundingClientRect(), x = (e.clientX - r.left) * W / r.width, y = (e.clientY - r.top) * H / r.height;
      for (var i = 0; i < hits.length; i++) {
        var h = hits[i];
        if (h.slice) {
          var dx = x - h.cx, dy = y - h.cy, d = Math.sqrt(dx * dx + dy * dy), a = Math.atan2(dy, dx);
          while (a < h.a0) a += Math.PI * 2;
          if (d >= h.r && d <= h.R && a <= h.a1) { if (cur !== i) show(i); return; }
        } else if (x >= h.x && x < h.x + h.w && y >= h.y - 10 && y <= h.y + h.h + 10) { if (cur !== i) show(i); return; }
      }
      hide();
    });
    svg.addEventListener('pointerleave', hide);
    svg.addEventListener('blur', hide);
    svg.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); show(cur < 0 ? 0 : Math.min(hits.length - 1, cur + 1)); }
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); show(cur < 0 ? hits.length - 1 : Math.max(0, cur - 1)); }
      else if (e.key === 'Escape') hide();
    });
  }

  // ---------------------------------------------------------------- redraw on width change
  function live(box, spec) {
    var w = 0;
    var go = function () { var nw = Math.round(box.clientWidth); if (nw && nw !== w) { w = nw; draw(box, spec); spec.animate = false; } };
    go();
    if (root.ResizeObserver) { var ro = new ResizeObserver(function () { root.requestAnimationFrame(go); }); ro.observe(box); return ro; }
    root.addEventListener('resize', go);
    return null;
  }

  // ---------------------------------------------------------------- websites: <figure data-hoola-chart> + a table
  function auto(scope) {
    var found = (scope || document).querySelectorAll('[data-hoola-chart]');
    [].forEach.call(found, function (fig) {
      if (fig.getAttribute('data-hc-done')) return;
      var table = fig.querySelector('table'), spec = fromTable(table);
      if (!spec) return;                                    // no numbers: the table stays as it is
      spec.type = fig.getAttribute('data-hoola-chart');
      spec.unit = fig.getAttribute('data-unit') || '';
      spec.suffix = fig.getAttribute('data-suffix') || '';
      var cap = fig.querySelector('figcaption');
      spec.title = fig.getAttribute('data-title') || (cap ? cap.textContent.trim() : '');
      if (root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches) spec.animate = false;
      var box = htmlEl('div', 'hc-box');
      table.parentNode.insertBefore(box, table);
      table.classList.add('hc-table');                       // kept for screen readers (visually hidden by CSS)
      fig.setAttribute('data-hc-done', '1');
      live(box, spec);
    });
  }

  root.HoolaChart = {draw: draw, live: live, fromTable: fromTable, fmt: fmt, num: num, auto: auto};
  if (document.querySelector && !document.getElementById('app')) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { auto(document); });
    else auto(document);
  }
})(window);
