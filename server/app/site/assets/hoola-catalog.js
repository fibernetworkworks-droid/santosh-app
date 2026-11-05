/* v0.531 Hoola catalogue filter: search + her filter columns + price + sort over the list's compact index
   (assets/catalog/<list>.json, fetched only when the visitor first touches the filter). The numbered pages under it
   stay for visitors without JavaScript and for search engines. No data leaves the page. */
(function () {
  'use strict';
  var d = document;
  function el(t, a, kids) {
    var x = d.createElement(t);
    Object.keys(a || {}).forEach(function (k) { if (k === 'text') x.textContent = a[k]; else x.setAttribute(k, a[k]); });
    (kids || []).forEach(function (c) { if (c) x.appendChild(c); });
    return x;
  }
  function norm(s) { return String(s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, ''); }
  d.querySelectorAll('form[data-hoola-catalog]').forEach(function (f) {
    var url = f.getAttribute('data-hoola-catalog'), root = f.getAttribute('data-root') || '';
    var sec = f.closest('section') || d, grid = sec.querySelector('.hs-cat-grid'), pager = sec.querySelector('.hs-pager');
    var count = sec.querySelector('.hs-cat-count'), data = null, loading = null, shown = 0, list = [], first = grid ? grid.innerHTML : '';
    var coll = (data && data.coll) || '';
    function load() {
      if (data) return Promise.resolve(data);
      if (!loading) loading = fetch(url).then(function (r) { if (!r.ok) throw new Error('index'); return r.json(); })
        .then(function (j) { data = j; coll = j.coll; j.items.forEach(function (it) { it.push(norm(it[1])); }); return j; });
      return loading;
    }
    function state() {
      var s = {q: norm(f.q && f.q.value).trim(), sort: f.sort ? f.sort.value : '', f: {}};
      s.pmin = f.pmin && f.pmin.value !== '' ? Number(f.pmin.value) : null;
      s.pmax = f.pmax && f.pmax.value !== '' ? Number(f.pmax.value) : null;
      (data ? data.facets : []).forEach(function (fc, i) { var e = f.elements[fc.key]; if (e && e.value) s.f[i] = fc.values.indexOf(e.value); });
      return s;
    }
    function active(s) { return s.q || s.sort || s.pmin !== null || s.pmax !== null || Object.keys(s.f).length; }
    function cardOf(it) {
      var a = el('a', {href: root + coll + '/' + it[0] + '/'});
      if (it[4]) a.appendChild(el('img', {src: root + 'assets/img/' + it[4], alt: it[1], loading: 'lazy', decoding: 'async', width: '320', height: '320', 'class': 'hs-cat-img'}));
      a.appendChild(el('span', {'class': 'hs-cat-t', text: it[1]}));
      if (it[3]) a.appendChild(el('span', {'class': 'hs-cat-p', text: it[3]}));
      return el('li', {'class': 'hs-cat-card'}, [a]);
    }
    function more() {
      var per = (data && data.per) || 48, end = Math.min(list.length, shown + per);
      for (var i = shown; i < end; i++) grid.appendChild(cardOf(list[i]));
      shown = end;
      var b = sec.querySelector('.hs-cat-more');
      if (b) b.remove();
      if (shown < list.length) {
        var btn = el('button', {type: 'button', 'class': 'btn btn-ghost hs-cat-more', text: 'Show more (' + (list.length - shown) + ')'});
        btn.addEventListener('click', more);
        grid.parentNode.insertBefore(btn, grid.nextSibling);
      }
    }
    function run() {
      load().then(function () {
        var s = state();
        var qs = new URLSearchParams();
        if (!active(s)) {
          grid.innerHTML = first; if (pager) pager.hidden = false; if (count) count.textContent = '';
          var b0 = sec.querySelector('.hs-cat-more'); if (b0) b0.remove();
          history.replaceState(null, '', location.pathname); return;
        }
        var words = s.q ? s.q.split(/\s+/) : [];
        list = data.items.filter(function (it) {
          for (var w = 0; w < words.length; w++) if (it[6].indexOf(words[w]) < 0) return false;
          for (var k in s.f) if (it[5][k] !== s.f[k]) return false;
          if (s.pmin !== null && (it[2] === null || it[2] < s.pmin)) return false;
          if (s.pmax !== null && (it[2] === null || it[2] > s.pmax)) return false;
          return true;
        });
        if (s.sort === 'az') list.sort(function (a, b) { return a[1].localeCompare(b[1]); });
        if (s.sort === 'lo') list.sort(function (a, b) { return (a[2] === null) - (b[2] === null) || a[2] - b[2]; });
        if (s.sort === 'hi') list.sort(function (a, b) { return (a[2] === null) - (b[2] === null) || b[2] - a[2]; });
        grid.innerHTML = ''; shown = 0; if (pager) pager.hidden = true;
        if (count) count.textContent = list.length + ' found';
        more();
        Array.prototype.forEach.call(f.elements, function (e) { if (e.name && e.value) qs.set(e.name, e.value); });
        history.replaceState(null, '', location.pathname + '?' + qs.toString());
      }).catch(function () { if (count) count.textContent = ''; });
    }
    var t = 0;
    f.addEventListener('input', function () { clearTimeout(t); t = setTimeout(run, 180); });
    f.addEventListener('change', run);
    f.addEventListener('reset', function () { setTimeout(run, 0); });
    f.addEventListener('submit', function (e) { e.preventDefault(); run(); });
    if (location.search) {                         // a shared filtered address opens filtered
      var p = new URLSearchParams(location.search);
      p.forEach(function (v, k) { if (f.elements[k]) f.elements[k].value = v; });
      run();
    }
  });
})();
