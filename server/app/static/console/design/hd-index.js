/* HOOLA DESIGN - hd-index.js (D9b speed)
 *
 * HD.index: a spatial index of every layer's WORLD box, one per page, kept up to date from HD.store's change
 * events (a node that moves takes its whole subtree along; removed nodes leave; a load starts again). Built on the
 * first question about a page (bulk load), then patched: the changes are only marked, and worked in when the next
 * question comes, so a drag that changes a frame 60 times a second costs nothing until somebody asks.
 *
 *   query(rect, pageId, opts) -> ids     the layers whose world box (store.worldBounds: the axis-aligned box around
 *                                        the node's own, possibly turned, 0..w x 0..h) touches rect {x, y, w, h}.
 *                                        No order. opts.visible: only layers that are visible (they and every parent)
 *                                        opts.ordered: in paint order, lowest first
 *   at(x, y, pageId, opts) -> ids        the layers whose OWN box really contains the world point (turned boxes are
 *                                        tested exactly), top-most first = the reverse of paint order (tree order).
 *                                        opts.visible as above; opts.tol = grow every box by this much (world units)
 *   rebuild(pageId?)                     throw the page's index (or every page's) away; built again when asked
 *   stats() -> {engine, pages, nodes, dirty, builds, patches, buildMs, cell}
 *   engine(name?)                        'grid' (default: measured faster, see below) | 'rtree'; switching rebuilds
 *
 * What it is NOT: a hit test. A box is not the drawn shape (strokes and shadows reach outside it, an ellipse does
 * not fill its corners, a clipping frame hides what is outside it) - the renderer decides; the index only says
 * which few layers to look at instead of all of them. A layer on a page that is not loaded yet (D9b page by page)
 * is simply not in it until the page arrives.
 *
 * Measured (server/tests/web/design_perf_test.js, 100,000 layers on ONE page, headless Chromium, 4 cores):
 *            build    viewport query   point    a frame (20 layers) moves, worked in
 *   grid     66 ms    10 us            3.9 us   36 us
 *   R-tree   105 ms   8 us             2.0 us   89 us
 * The grid (cell = 3 x the median layer size; 1.5 and 6 were slower) wins what happens every frame of a drag - a
 * move plus a viewport query, 46 us against 97 us - and the build; the R-tree (rbush's algorithms: bulk load,
 * least-enlargement insert, overlap-minimising split) answers a lone point faster. Both stay, `engine()` switches.
 */
(function () {
  'use strict';
  var W = window;
  var HD = W.HD = W.HD || {};
  var store = HD.store;
  var ROOT = store.ROOT;

  var GEO = {x: 1, y: 1, w: 1, h: 1, rot: 1, flipH: 1, flipV: 1, parent: 1, type: 1};
  var engineName = 'grid';
  var pages = new Map();        /* page id -> structure */
  var ent = new Map();          /* node id -> entry {id, page, x0, y0, x1, y1, ...} */
  var dirty = new Set();        /* node ids whose subtree must be worked in again */
  var gone = new Set();         /* node ids that were removed */
  var all = false;              /* everything must be built again (a load) */
  var st = {builds: 0, patches: 0, buildMs: 0};
  var stamp = 1;
  var now = (W.performance && W.performance.now) ? function () { return W.performance.now(); } : function () { return Date.now(); };

  /* ---------------------------------------------------------------- the uniform grid */
  function Grid(cell) {
    this.cs = cell; this.inv = 1 / cell;
    this.cells = new Map();     /* "cx,cy" as a number key -> array of entries */
    this.big = [];              /* entries over BIG cells: looked at every time */
    this.n = 0; this.built = 0;
  }
  var BIG = 64, KX = 1048576;    /* cell numbers fit +-524288 per axis */
  var CELLF = 3;                 /* cell = CELLF x the median layer size (1.5 / 3 / 6 measured: 3 wins) */
  function ckey(cx, cy) { return (cx + 524288) * KX + (cy + 524288); }
  Grid.prototype.insert = function (e) {
    var inv = this.inv, cx0 = Math.floor(e.x0 * inv), cy0 = Math.floor(e.y0 * inv), cx1 = Math.floor(e.x1 * inv), cy1 = Math.floor(e.y1 * inv);
    this.n++;
    if ((cx1 - cx0 + 1) * (cy1 - cy0 + 1) > BIG || cx0 < -524000 || cx1 > 524000 || cy0 < -524000 || cy1 > 524000) {
      e.slot = -1; e.bi = this.big.length; this.big.push(e); return;
    }
    e.slot = 1; e.cx0 = cx0; e.cy0 = cy0; e.cx1 = cx1; e.cy1 = cy1;
    for (var cx = cx0; cx <= cx1; cx++) for (var cy = cy0; cy <= cy1; cy++) {
      var k = ckey(cx, cy), a = this.cells.get(k);
      if (!a) { a = []; this.cells.set(k, a); }
      a.push(e);
    }
  };
  Grid.prototype.remove = function (e) {
    if (e.slot === -1) {
      if (this.big[e.bi] !== e) return;
      var last = this.big.pop();
      if (last !== e) { this.big[e.bi] = last; last.bi = e.bi; }
      this.n--; e.slot = 0;
      return;
    }
    if (e.slot !== 1) return;
    var found = false;
    for (var cx = e.cx0; cx <= e.cx1; cx++) for (var cy = e.cy0; cy <= e.cy1; cy++) {
      var k = ckey(cx, cy), a = this.cells.get(k);
      if (!a) continue;
      var i = a.indexOf(e);
      if (i >= 0) { a[i] = a[a.length - 1]; a.pop(); found = true; }
      if (!a.length) this.cells.delete(k);
    }
    if (found) this.n--;
    e.slot = 0;
  };
  Grid.prototype.search = function (x0, y0, x1, y1, out) {
    var inv = this.inv, cx0 = Math.floor(x0 * inv), cy0 = Math.floor(y0 * inv), cx1 = Math.floor(x1 * inv), cy1 = Math.floor(y1 * inv);
    var s = ++stamp, i, e, a, cx, cy, big = this.big;
    for (i = 0; i < big.length; i++) { e = big[i]; if (e.x0 <= x1 && e.x1 >= x0 && e.y0 <= y1 && e.y1 >= y0) out.push(e); }
    if ((cx1 - cx0 + 1) * (cy1 - cy0 + 1) > this.cells.size) {          /* a rect wider than the drawing: walk the cells */
      var self = this;
      this.cells.forEach(function (arr) {
        for (var j = 0; j < arr.length; j++) { var f = arr[j]; if (f.seen !== s && f.x0 <= x1 && f.x1 >= x0 && f.y0 <= y1 && f.y1 >= y0) { f.seen = s; out.push(f); } }
      });
      return self;
    }
    for (cx = cx0; cx <= cx1; cx++) for (cy = cy0; cy <= cy1; cy++) {
      a = this.cells.get(ckey(cx, cy));
      if (!a) continue;
      for (i = 0; i < a.length; i++) { e = a[i]; if (e.seen !== s && e.x0 <= x1 && e.x1 >= x0 && e.y0 <= y1 && e.y1 >= y0) { e.seen = s; out.push(e); } }
    }
    return this;
  };
  function gridFor(list) {
    var sz = [], i, step = Math.max(1, Math.floor(list.length / 2000));
    for (i = 0; i < list.length; i += step) sz.push(Math.max(list[i].x1 - list[i].x0, list[i].y1 - list[i].y0));
    sz.sort(function (a, b) { return a - b; });
    var med = sz.length ? sz[sz.length >> 1] : 100;
    var g = new Grid(Math.min(8192, Math.max(8, (med || 100) * CELLF)));
    for (i = 0; i < list.length; i++) g.insert(list[i]);
    g.built = list.length;
    return g;
  }

  /* ---------------------------------------------------------------- the R-tree (rbush's algorithms) */
  var MAXE = 9, MINE = 4;
  function RNode(children, leaf) { this.children = children; this.leaf = leaf; this.height = 1; this.x0 = Infinity; this.y0 = Infinity; this.x1 = -Infinity; this.y1 = -Infinity; }
  function extend(a, b) { if (b.x0 < a.x0) a.x0 = b.x0; if (b.y0 < a.y0) a.y0 = b.y0; if (b.x1 > a.x1) a.x1 = b.x1; if (b.y1 > a.y1) a.y1 = b.y1; return a; }
  function calcBox(n) { n.x0 = Infinity; n.y0 = Infinity; n.x1 = -Infinity; n.y1 = -Infinity; for (var i = 0; i < n.children.length; i++) extend(n, n.children[i]); }
  function area(a) { return (a.x1 - a.x0) * (a.y1 - a.y0); }
  function margin(a) { return (a.x1 - a.x0) + (a.y1 - a.y0); }
  function RTree() { this.data = new RNode([], true); this.n = 0; this.built = 0; }
  RTree.prototype.search = function (x0, y0, x1, y1, out) {
    var node = this.data, stack = [], i, c;
    if (!(node.x0 <= x1 && node.x1 >= x0 && node.y0 <= y1 && node.y1 >= y0)) return this;
    while (node) {
      for (i = 0; i < node.children.length; i++) {
        c = node.children[i];
        if (c.x0 <= x1 && c.x1 >= x0 && c.y0 <= y1 && c.y1 >= y0) { if (node.leaf) out.push(c); else stack.push(c); }
      }
      node = stack.pop();
    }
    return this;
  };
  function cmpX(a, b) { return a.x0 - b.x0; }
  function cmpY(a, b) { return a.y0 - b.y0; }
  function multiSelect(arr, left, right, n, cmp) {            /* rbush: sort into groups of n (quickselect per pivot) */
    var stack = [left, right], mid;
    while (stack.length) {
      right = stack.pop(); left = stack.pop();
      if (right - left <= n) continue;
      mid = left + Math.ceil((right - left) / n / 2) * n;
      quickselect(arr, mid, left, right, cmp);
      stack.push(left, mid, mid, right);
    }
  }
  function quickselect(arr, k, left, right, cmp) {
    while (right > left) {
      var t = arr[k], i = left, j = right, tmp;
      tmp = arr[left]; arr[left] = arr[k]; arr[k] = tmp;
      if (cmp(arr[right], t) > 0) { tmp = arr[left]; arr[left] = arr[right]; arr[right] = tmp; }
      while (i < j) {
        tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; i++; j--;
        while (cmp(arr[i], t) < 0) i++;
        while (cmp(arr[j], t) > 0) j--;
      }
      if (cmp(arr[left], t) === 0) { tmp = arr[left]; arr[left] = arr[j]; arr[j] = tmp; }
      else { j++; tmp = arr[j]; arr[j] = arr[right]; arr[right] = tmp; }
      if (j <= k) left = j + 1;
      if (k <= j) right = j - 1;
    }
  }
  function build(items, left, right, height) {
    var N = right - left + 1, M = MAXE, node;
    if (N <= M) { node = new RNode(items.slice(left, right + 1), true); calcBox(node); return node; }
    if (!height) { height = Math.ceil(Math.log(N) / Math.log(M)); M = Math.ceil(N / Math.pow(M, height - 1)); }
    node = new RNode([], false); node.height = height;
    var N2 = Math.ceil(N / M), N1 = N2 * Math.ceil(Math.sqrt(M)), i, j, r2, r3;
    multiSelect(items, left, right, N1, cmpX);
    for (i = left; i <= right; i += N1) {
      r2 = Math.min(i + N1 - 1, right);
      multiSelect(items, i, r2, N2, cmpY);
      for (j = i; j <= r2; j += N2) { r3 = Math.min(j + N2 - 1, r2); node.children.push(build(items, j, r3, height - 1)); }
    }
    calcBox(node);
    return node;
  }
  RTree.prototype.load = function (items) { if (items.length) this.data = build(items.slice(), 0, items.length - 1, 0); this.n = items.length; this.built = items.length; return this; };
  RTree.prototype.insert = function (e) {
    var level = this.data.height - 1, node = this.data, path = [];
    while (!node.leaf && path.length !== level) {                /* choose the subtree that grows least */
      path.push(node);
      var best = Infinity, bestA = Infinity, target = null;
      for (var i = 0; i < node.children.length; i++) {
        var c = node.children[i], a = area(c);
        var en = (Math.max(e.x1, c.x1) - Math.min(e.x0, c.x0)) * (Math.max(e.y1, c.y1) - Math.min(e.y0, c.y0)) - a;
        if (en < best || (en === best && a < bestA)) { best = en; bestA = a; target = c; }
      }
      node = target || node.children[0];
    }
    node.children.push(e);
    extend(node, e);
    path.push(node);
    for (var lv = path.length - 1; lv >= 0; lv--) {
      if (path[lv].children.length > MAXE) { this._split(path, lv); } else break;
    }
    for (var k = path.length - 1; k >= 0; k--) extend(path[k], e);
    this.n++;
  };
  RTree.prototype._split = function (path, level) {
    var node = path[level], M = node.children.length, m = MINE;
    var ax = this._margins(node, m, M, cmpX), ay = this._margins(node, m, M, cmpY);
    if (ax < ay) node.children.sort(cmpX);
    var split = this._splitIndex(node, m, M);
    var nn = new RNode(node.children.splice(split, node.children.length - split), node.leaf);
    nn.height = node.height;
    calcBox(node); calcBox(nn);
    if (level) path[level - 1].children.push(nn);
    else {
      var root = new RNode([node, nn], false);
      root.height = node.height + 1;
      calcBox(root);
      this.data = root;
    }
  };
  RTree.prototype._splitIndex = function (node, m, M) {
    var index = M - m, minOverlap = Infinity, minArea = Infinity;
    for (var i = m; i <= M - m; i++) {
      var b1 = boxOf(node, 0, i), b2 = boxOf(node, i, M);
      var ov = Math.max(0, Math.min(b1.x1, b2.x1) - Math.max(b1.x0, b2.x0)) * Math.max(0, Math.min(b1.y1, b2.y1) - Math.max(b1.y0, b2.y0));
      var ar = area(b1) + area(b2);
      if (ov < minOverlap) { minOverlap = ov; index = i; minArea = ar < minArea ? ar : minArea; }
      else if (ov === minOverlap && ar < minArea) { minArea = ar; index = i; }
    }
    return index;
  };
  RTree.prototype._margins = function (node, m, M, cmp) {
    node.children.sort(cmp);
    var l = boxOf(node, 0, m), r = boxOf(node, M - m, M), s = margin(l) + margin(r), i;
    for (i = m; i < M - m; i++) { extend(l, node.children[i]); s += margin(l); }
    for (i = M - m - 1; i >= m; i--) { extend(r, node.children[i]); s += margin(r); }
    return s;
  };
  function boxOf(node, k, p) { var b = {x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity}; for (var i = k; i < p; i++) extend(b, node.children[i]); return b; }
  RTree.prototype.remove = function (e) {
    var node = this.data, path = [], idxs = [], i = 0, parent = null, goingUp = false;
    while (node || path.length) {
      if (!node) { node = path.pop(); parent = path[path.length - 1]; i = idxs.pop(); goingUp = true; }
      if (node.leaf) {
        var at = node.children.indexOf(e);
        if (at !== -1) {
          node.children.splice(at, 1);
          path.push(node);
          for (var j = path.length - 1; j >= 0; j--) {          /* condense: drop empty nodes, tighten the boxes */
            if (path[j].children.length === 0) {
              if (j > 0) { var sib = path[j - 1].children; sib.splice(sib.indexOf(path[j]), 1); }
              else { this.data = new RNode([], true); }
            } else calcBox(path[j]);
          }
          this.n--;
          return;
        }
      }
      if (!goingUp && !node.leaf && node.x0 <= e.x0 && node.y0 <= e.y0 && node.x1 >= e.x1 && node.y1 >= e.y1) {
        path.push(node); idxs.push(i); i = 0; parent = node; node = node.children[0];
      } else if (parent) { i++; node = parent.children[i]; goingUp = false; }
      else node = null;
    }
  };

  /* ---------------------------------------------------------------- entries */
  function topOf(id) {
    var c = id, n, g = 0;
    while (c !== undefined && ++g < 100000) {
      n = store.get(c);
      if (!n) return null;
      if (n.parent === ROOT) return c;
      c = n.parent;
    }
    return null;
  }
  function boxEntry(id, pg) {
    var b = store.worldBounds(id), e = ent.get(id);
    if (!e) { e = {id: id, page: pg, x0: 0, y0: 0, x1: 0, y1: 0, slot: 0, seen: 0}; ent.set(id, e); }
    e.page = pg; e.x0 = b.x; e.y0 = b.y; e.x1 = b.x + b.w; e.y1 = b.y + b.h;
    return e;
  }
  function makeIndex(list) { return engineName === 'rtree' ? new RTree().load(list) : gridFor(list); }
  function buildPage(pg) {
    var t0 = now(), list = [];
    store.walk(pg, function (id, n) {
      if (id === pg) return true;
      var old = ent.get(id);
      if (old && old.page !== pg && pages.has(old.page)) pages.get(old.page).remove(old);
      list.push(boxEntry(id, pg));
      return true;
    });
    pages.set(pg, makeIndex(list));
    st.builds++; st.buildMs = now() - t0;
  }
  function drop(id) {
    var e = ent.get(id);
    if (!e) return;
    ent.delete(id);
    var ix = pages.get(e.page);
    if (ix) ix.remove(e);
  }
  function settle() {
    if (all) {
      all = false; dirty.clear(); gone.clear(); pages = new Map(); ent = new Map();
      return;
    }
    if (gone.size) { gone.forEach(drop); gone.clear(); }
    if (!dirty.size) return;
    var done = new Set(), list = Array.from(dirty);
    dirty.clear();
    for (var i = 0; i < list.length; i++) {
      var id = list[i];
      if (done.has(id)) continue;
      if (!store.has(id)) { drop(id); done.add(id); continue; }
      var n = store.get(id);
      if (n.type === 'DOCUMENT') continue;                            /* the root: its pages answer for themselves */
      if (n.type === 'PAGE' && !pages.has(id)) continue;              /* a page itself: its subtree, if it is built */
      var pg = topOf(id);
      if (pg === null || !pages.has(pg)) {                              /* not on a built page (or the page is new) */
        store.walk(id, function (k) { done.add(k); drop(k); return true; });
        continue;
      }
      store.walk(id, function (k, kn) {
        if (done.has(k)) return false;
        done.add(k);
        if (k === pg || kn.type === 'DOCUMENT') return true;
        var old = ent.get(k);
        if (old) { var ox = pages.get(old.page); if (ox) ox.remove(old); }
        var e = boxEntry(k, pg);
        pages.get(pg).insert(e);
        st.patches++;
        return true;
      });
    }
    pages.forEach(function (ix, pg) {                                  /* grown a lot since it was built: build again */
      if (ix.n > 64 && ix.n > ix.built * 2) pages.delete(pg);
    });
  }
  function ready(pg) {
    settle();
    if (!pg || !store.has(pg)) return null;
    if (!pages.has(pg)) buildPage(pg);
    return pages.get(pg);
  }
  function shown(id) {
    var c = id, n, g = 0;
    while (c !== undefined && ++g < 100000) {
      n = store.get(c);
      if (!n) return false;
      if (n.visible === false) return false;
      if (n.parent === ROOT) return true;
      c = n.parent;
    }
    return true;
  }
  function normRect(r) {
    var x = +r.x || 0, y = +r.y || 0, w = +r.w || 0, h = +r.h || 0;
    if (w < 0) { x += w; w = -w; }
    if (h < 0) { y += h; h = -h; }
    return [x, y, x + w, y + h];
  }

  /* ---------------------------------------------------------------- public */
  var index = HD.index = {};
  index.query = function (rect, pageId, opts) {
    var pg = pageId || (HD.sel && HD.sel.page), ix = ready(pg), out = [], hits = [];
    if (!ix || !rect) return out;
    var r = normRect(rect);
    ix.search(r[0], r[1], r[2], r[3], hits);
    var vis = opts && opts.visible;
    for (var i = 0; i < hits.length; i++) if (!vis || shown(hits[i].id)) out.push(hits[i].id);
    return opts && opts.ordered ? store.order(out) : out;
  };
  index.at = function (x, y, pageId, opts) {
    var pg = pageId || (HD.sel && HD.sel.page), ix = ready(pg), hits = [], out = [];
    if (!ix) return out;
    var tol = opts && typeof opts.tol === 'number' ? Math.max(0, opts.tol) : 0, vis = opts && opts.visible, i, e, n, m, w, h, d, lx, ly;
    ix.search(x - tol, y - tol, x + tol, y + tol, hits);
    for (i = 0; i < hits.length; i++) {
      e = hits[i];
      n = store.get(e.id);
      if (!n) continue;
      if (vis && !shown(e.id)) continue;
      if (n.rot || n.flipH || n.flipV || hasTurn(e.id)) {             /* a turned box: test it in its own space */
        m = store.worldMatrix(e.id);
        d = m[0] * m[3] - m[1] * m[2];
        if (!d) continue;
        lx = (m[3] * (x - m[4]) - m[2] * (y - m[5])) / d;
        ly = (m[0] * (y - m[5]) - m[1] * (x - m[4])) / d;
        w = store.prop(e.id, 'w') || 0; h = store.prop(e.id, 'h') || 0;
        var sc = Math.sqrt(Math.abs(d)) || 1, t = tol / sc;
        if (lx < -t || ly < -t || lx > w + t || ly > h + t) continue;
      }
      out.push(e.id);
    }
    return out.length > 1 ? store.order(out).reverse() : out;
  };
  function hasTurn(id) {                                              /* a parent turned or flipped */
    var c = store.parent(id), n, g = 0;
    while (c !== undefined && ++g < 100000) {
      n = store.get(c);
      if (!n || n.parent === undefined) return false;
      if (n.rot || n.flipH || n.flipV) return true;
      c = n.parent;
    }
    return false;
  }
  index.rebuild = function (pageId) {
    settle();
    if (pageId) { pages.delete(pageId); return; }
    pages = new Map(); ent = new Map();
  };
  index.engine = function (name, opts) {
    if (name === undefined) return engineName;
    if (opts && typeof opts.cell === 'number' && opts.cell > 0) CELLF = opts.cell;
    if (name !== 'grid' && name !== 'rtree') throw new Error('HD.index.engine: grid or rtree');
    engineName = name;
    all = true;
    return engineName;
  };
  index.stats = function () {
    var n = 0, cell = null;
    pages.forEach(function (ix) { n += ix.n; if (ix.cs) cell = ix.cs; });
    return {engine: engineName, pages: pages.size, nodes: n, dirty: dirty.size + gone.size, builds: st.builds, patches: st.patches, buildMs: st.buildMs, cell: cell};
  };
  index.bounds = function (id) {
    var e = ent.get(id);
    return e ? {x: e.x0, y: e.y0, w: e.x1 - e.x0, h: e.y1 - e.y0, page: e.page} : null;
  };

  /* ---------------------------------------------------------------- kept up to date */
  store.on('change', function (ch) {
    if (!ch || all) return;
    if (ch.removed && ch.removed.size) ch.removed.forEach(function (id) { gone.add(id); dirty.delete(id); });
    if (!ch.ids) return;
    ch.ids.forEach(function (id) {
      if (ch.removed && ch.removed.has(id)) return;
      var ps = ch.props && ch.props.get(id);
      if (!ps) { dirty.add(id); return; }                              /* made, or arrived */
      var geo = false;
      ps.forEach(function (k) { if (GEO[k] === 1) geo = true; });
      if (geo) dirty.add(id);
    });
  });
  store.on('load', function () { all = true; });
})();
