/* HOOLA DESIGN - hd-core.js
 *
 * HD.frac   fractional index strings (base 62, plain string order)
 * HD.store  the document: a tree of nodes, each node a flat bag of properties
 * HD.sel    the selection + the current page
 * HD.Emitter  the tiny event emitter the three use (on / off / emit)
 *
 * READ-ONLY RESULTS. get(id) returns the LIVE node object and children(id) returns a FROZEN shared array:
 * never change them (copy first: children(id).slice()). Property values (fills, layout, ...) are immutable
 * by convention: build a NEW array / object and pass it to set(). localMatrix / worldMatrix / worldBounds /
 * subtreeBounds return fresh copies. A missing property means "the default": read with prop(id, name).
 *
 * EDITS. Every edit goes through tx(label, fn). Inside the outermost tx all changes are collected; when fn
 * returns the store calls HD.layout.run(changedIds, changedProps) (if HD.layout exists; its set() calls join
 * the same tx), then closes the tx: ONE op batch (sets merged per node, later value wins), ONE undo entry
 * (the inverse ops), ONE 'change' event. create / set / remove / move called outside a tx open their own.
 * If fn throws, everything it did is put back and nothing is sent. Defaults are never written into ops.
 *
 * THE SYNC HANDSHAKE (HD.store <-> HD.net)
 *   store.tracking(true)            net switches pending-tracking on while a file is connected (off = no
 *                                   book-keeping at all, for a local-only document).
 *   store.onOps(fn(ops, b))         fires once per closed local tx. `ops` is the batch, `b` the store's own
 *                                   batch number (1, 2, 3, ...). The op OBJECTS are the handles: keep them,
 *                                   do not clone or change them.
 *   store.rollback(ops)             the server REJECTED these ops (the same objects it was given). Each prop
 *                                   goes back to what the server has: the last remote value that arrived
 *                                   while it was pending, else the value before the edit. A rejected create
 *                                   is removed, a rejected delete is put back.
 *   store.acked(b)                  every op of batch b has been answered (call rollback for the rejected
 *                                   ones FIRST). Releases the batch's pending marks; in the rare case that an
 *                                   accepted op is not on screen yet (it could not be applied after a reload,
 *                                   or the node was re-made by someone meanwhile) it is put on screen now.
 *   store.applyRemote(ops)          ops of other people. While a local write to (node, prop) is un-acked a
 *                                   remote value for that same (node, prop) is NOT applied (it is remembered
 *                                   as the server's value in case our write is rejected). Ops on a node we
 *                                   deleted (not confirmed yet) are skipped: the server will delete it too.
 *   store.load(doc, cid, {keep:true})   after a reconnect: the fresh document is loaded, the undo stack is
 *                                   kept, and every still-pending batch is applied again on top (an op that
 *                                   does not fit stays pending; its answer settles it).
 *   store.on('desync', fn)          the store can not tell what the server has: a remote delete took a node
 *                                   we had moved in from elsewhere, a node left something we are deleting, a
 *                                   remote reparent would be a cycle here, a rollback hit a node that is
 *                                   gone... net then reconnects and reloads with {keep:true}; nothing typed
 *                                   is lost. server/tests/web/design_core_test.js runs three editors against
 *                                   a contract server with crossing messages to prove they always end equal.
 *   store.readOnly = true           net sets it for a view-only file / a full offline queue: tx() and the
 *                                   editing calls then do nothing and return undefined.
 */
(function () {
  'use strict';
  var W = window;
  var HD = W.HD = W.HD || {};
  var M = HD.math;
  var hasOwn = Object.prototype.hasOwnProperty;
  var isArr = Array.isArray;

  function report(err) { if (W.console && W.console.error) W.console.error('[HD]', err); }

  /* ================================================================ emitter */
  function Emitter() { this._m = Object.create(null); }
  Emitter.prototype.on = function (evt, fn) {
    var self = this;
    if (typeof fn !== 'function') return function () {};
    (this._m[evt] || (this._m[evt] = [])).push(fn);
    return function () { self.off(evt, fn); };
  };
  Emitter.prototype.off = function (evt, fn) {
    var l = this._m[evt];
    if (!l) return;
    var i = l.indexOf(fn);
    if (i >= 0) this._m[evt] = l.slice(0, i).concat(l.slice(i + 1));
  };
  Emitter.prototype.emit = function (evt, a, b) {
    var l = this._m[evt];
    if (!l) return;
    for (var i = 0; i < l.length; i++) {
      try { l[i](a, b); } catch (err) { report(err); }
    }
  };
  Emitter.prototype.count = function (evt) { var l = this._m[evt]; return l ? l.length : 0; };
  HD.Emitter = Emitter;

  /* ================================================================ HD.frac
   * Keys are base-62 strings ("0-9A-Za-z", which is also ASCII order) compared as PLAIN STRINGS, and a key
   * NEVER ends in "0" (the rule of the plain base-62 fraction the server uses: its own between() refuses such
   * a key). Keys made here have a short counting head ("a1", "a2", ... "az", "b01", ...; below "a1": "Zz",
   * "Zy", ...) so adding at the end or the start 50,000 times still gives 4-character keys, plus a fraction
   * tail for inserts in between ("a1V"). Keys from any other correct implementation are accepted: next to a
   * key that is not in that shape the plain string midpoint / one-digit step is used. Only the ordering matters.
   */
  var DIG = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
  var DI = Object.create(null);
  (function () { for (var i = 0; i < DIG.length; i++) DI[DIG.charAt(i)] = i; })();
  var SMALLEST = 'A00000000000000000000000000';
  var FIRST = 'a1';

  function di(ch) {
    var v = DI[ch];
    if (v !== undefined) return v;
    for (var i = DIG.length - 1; i >= 0; i--) if (DIG.charAt(i) <= ch) return i;   /* a foreign character */
    return 0;
  }

  /* a string strictly between a ('' = lowest) and b (null = highest) in plain string order; never ends in '0' */
  function mid(a, b) {
    var out = '', i = 0, ca, cb;
    for (;;) {
      ca = i < a.length ? di(a.charAt(i)) : 0;
      if (b === null) cb = 62;
      else if (i < b.length) cb = di(b.charAt(i));
      else return out + 'V';                       /* b is a + zeros: there is no room, stay next to it */
      if (ca === cb) { out += DIG.charAt(ca); i++; continue; }
      if (cb < ca) return out + DIG.charAt(ca) + 'V';              /* not a < b: keep going, never throw */
      if (cb - ca > 1) return out + DIG.charAt((ca + cb + 1) >> 1);
      if (b !== null && b.length > i + 1) return out + DIG.charAt(cb);
      out += DIG.charAt(ca); i++; b = null;
    }
  }
  /* one digit step above a / below b, for a neighbour that is not in the counting shape (cheap repeated adds) */
  function stepAfter(a) {
    var h = 0;
    while (h < a.length && di(a.charAt(h)) === 61) h++;
    return h === a.length ? a + '1' : a.slice(0, h) + DIG.charAt(di(a.charAt(h)) + 1);
  }
  function stepBefore(b) {
    var h = 0;
    while (h < b.length && di(b.charAt(h)) === 0) h++;
    if (h === b.length) return mid('', b);
    var d = di(b.charAt(h));
    return d > 1 ? b.slice(0, h) + DIG.charAt(d - 1) : b.slice(0, h) + '0z';
  }

  function headLen(key) {
    var c = key.charCodeAt(0);
    if (c >= 97 && c <= 122) return c - 97 + 2;
    if (c >= 65 && c <= 90) return 90 - c + 2;
    return 0;
  }
  function validKey(key) {
    if (typeof key !== 'string' || !key || key === SMALLEST) return false;
    var L = headLen(key);
    if (!L || key.length < L) return false;
    for (var i = 1; i < key.length; i++) if (DI[key.charAt(i)] === undefined) return false;
    return !(key.length > L && key.charAt(key.length - 1) === '0');
  }
  function inc1(x) {
    var head = x.charAt(0), d = x.slice(1).split(''), carry = true;
    for (var i = d.length - 1; carry && i >= 0; i--) {
      var v = DI[d[i]] + 1;
      if (v === 62) d[i] = '0'; else { d[i] = DIG.charAt(v); carry = false; }
    }
    if (!carry) return head + d.join('');
    if (head === 'Z') return 'a0';
    if (head === 'z') return null;
    var h = String.fromCharCode(head.charCodeAt(0) + 1);
    if (h > 'a') d.push('0'); else d.pop();
    return h + d.join('');
  }
  function dec1(x) {
    var head = x.charAt(0), d = x.slice(1).split(''), borrow = true;
    for (var i = d.length - 1; borrow && i >= 0; i--) {
      var v = DI[d[i]] - 1;
      if (v === -1) d[i] = 'z'; else { d[i] = DIG.charAt(v); borrow = false; }
    }
    if (!borrow) return head + d.join('');
    if (head === 'a') return 'Zz';
    if (head === 'A') return null;
    var h = String.fromCharCode(head.charCodeAt(0) - 1);
    if (h < 'Z') d.push('z'); else d.pop();
    return h + d.join('');
  }
  /* the next / previous counting head that does not end in "0" */
  function incInt(x) { var n = inc1(x); return n !== null && n.charAt(n.length - 1) === '0' ? inc1(n) : n; }
  function decInt(x) { var n = dec1(x); return n !== null && n.charAt(n.length - 1) === '0' ? dec1(n) : n; }

  function keyBetween(a, b) {
    var ia, ib, fa, fb, n;
    if (a === null) {
      if (b === null) return FIRST;
      ib = b.slice(0, headLen(b)); fb = b.slice(ib.length);
      if (ib === SMALLEST) return ib + mid('', fb);
      if (ib < b) return ib;
      n = decInt(ib);
      return n === null ? mid('', b) : n;
    }
    ia = a.slice(0, headLen(a)); fa = a.slice(ia.length);
    if (b === null) {
      n = incInt(ia);
      return n === null ? ia + mid(fa, null) : n;
    }
    ib = b.slice(0, headLen(b)); fb = b.slice(ib.length);
    if (ia === ib) return ia + mid(fa, fb);
    n = incInt(ia);
    if (n !== null && n < b) return n;
    return ia + mid(fa, null);
  }
  function fnorm(k) { return (k === undefined || k === null || k === '') ? null : String(k); }

  /* between(a|null, b|null) -> a key k with a < k < b.  null = no bound on that side. */
  function between(a, b) {
    a = fnorm(a); b = fnorm(b);
    if (a !== null && b !== null) {
      if (a === b) return a + 'V';                 /* two equal keys: nothing fits, go right after them */
      if (a > b) { var t = a; a = b; b = t; }
    }
    var k;
    if ((a === null || validKey(a)) && (b === null || validKey(b))) {
      k = keyBetween(a, b);
      if (k.charAt(k.length - 1) !== '0') return k;
    } else if (b === null) return a < FIRST ? FIRST : stepAfter(a);          /* on top of a foreign key */
    else if (a === null) return b > FIRST ? FIRST : stepBefore(b);          /* under a foreign key */
    return mid(a === null ? '' : a, b);
  }
  /* nBetween(a, b, n) -> n keys in rising order, all between a and b */
  function nBetween(a, b, n) {
    var out = [], c, i;
    n = n | 0;
    if (n <= 0) return out;
    if (n === 1) return [between(a, b)];
    a = fnorm(a); b = fnorm(b);
    if (b === null) {
      c = between(a, null); out.push(c);
      for (i = 1; i < n; i++) { c = between(c, null); out.push(c); }
      return out;
    }
    if (a === null) {
      c = between(null, b); out.push(c);
      for (i = 1; i < n; i++) { c = between(null, c); out.push(c); }
      return out.reverse();
    }
    var h = n >> 1;
    c = between(a, b);
    return nBetween(a, c, h).concat([c], nBetween(c, b, n - h - 1));
  }
  HD.frac = {between: between, nBetween: nBetween, valid: validKey, DIGITS: DIG};

  /* ================================================================ HD.store */
  var ROOT = '0:0';
  var LABEL = {
    DOCUMENT: 'Document', PAGE: 'Page', FRAME: 'Frame', GROUP: 'Group', SECTION: 'Section', RECT: 'Rectangle',
    ELLIPSE: 'Ellipse', LINE: 'Line', POLYGON: 'Polygon', STAR: 'Star', VECTOR: 'Vector', TEXT: 'Text',
    COMPONENT: 'Component', COMPONENT_SET: 'Component set', INSTANCE: 'Instance'
  };
  var TYPES = Object.keys(LABEL);

  var COMMON = {
    x: 0, y: 0, w: 100, h: 100, rot: 0, flipH: false, flipV: false,
    visible: true, locked: false, opacity: 1, blend: 'normal', mask: false,
    fills: [], strokes: [], strokeWeight: 1, strokeAlign: 'center', strokeCap: 'butt', strokeJoin: 'miter', dash: [],
    radius: 0, effects: [], clip: false,
    layout: {mode: 'none', gap: 0, pad: [0, 0, 0, 0], alignMain: 'start', alignCross: 'start', wrap: false},
    grids: [], sizeH: 'fixed', sizeV: 'fixed', layoutPos: 'auto', cons: {h: 'left', v: 'top'},
    reactions: [], protoStart: false, scroll: 'none', fixed: false, exports: []
  };
  var BY_TYPE = {
    FRAME: {clip: true},
    COMPONENT: {clip: true, desc: ''},
    INSTANCE: {clip: true, ov: {}},
    LINE: {h: 0},
    POLYGON: {sides: 3},
    STAR: {sides: 5, ratio: 0.5},
    VECTOR: {path: '', fillRule: 'nonzero'},
    TEXT: {
      chars: '', font: 'Inter', fontSize: 16, fontWeight: 400, italic: false, lineHeight: 'auto', letterSpacing: 0,
      align: 'left', alignV: 'top', autoResize: 'wh', decoration: 'none', textCase: 'none'
    },
    PAGE: {bg: '#F5F5F5'},
    DOCUMENT: {styles: {}, vars: {}, modes: []}
  };
  function clone(v) {
    if (v === null || typeof v !== 'object') return v;
    if (isArr(v)) { var a = new Array(v.length); for (var i = 0; i < v.length; i++) a[i] = clone(v[i]); return a; }
    var o = {};
    for (var k in v) if (hasOwn.call(v, k)) o[k] = clone(v[k]);
    return o;
  }
  function deepFreeze(v) {
    if (v !== null && typeof v === 'object' && !Object.isFrozen(v)) {
      Object.freeze(v);
      for (var k in v) if (hasOwn.call(v, k)) deepFreeze(v[k]);
    }
    return v;
  }
  var DEF = Object.create(null);
  (function () {
    for (var i = 0; i < TYPES.length; i++) {
      var t = TYPES[i], d = clone(COMMON), x = BY_TYPE[t];
      if (x) for (var k in x) d[k] = clone(x[k]);
      DEF[t] = deepFreeze(d);
    }
  })();
  var NO_DEF = Object.freeze({});
  var EMPTY = Object.freeze([]);
  var IDENT = [1, 0, 0, 1, 0, 0];

  /* ---------- state ---------- */
  var nodes = new Map();      /* id -> node (the props bag) */
  var kidSet = new Map();     /* parent id -> Set of child ids */
  var sorted = new Map();     /* parent id -> frozen array, children sorted by (idx, id); dropped when stale */
  var tail = new Map();       /* parent id -> last child id | null; a missing entry = not known */
  var lm = new Map();         /* id -> local matrix */
  var wm = new Map();         /* id -> world matrix      (a cached child always has a cached parent) */
  var wb = new Map();         /* id -> world bounds of the node's own box */
  var sb = new Map();         /* id -> world bounds of the node and all it shows (see subtreeBounds) */
  var cid = 0, counter = 0;
  var nameN = new Map();      /* type -> highest "Rectangle N" seen */
  var em = new Emitter();

  /* ---------- undo ---------- */
  var undoS = [], redoS = [], UNDO_MAX = 500;
  var depth = 0, cur = null;  /* the open tx */
  var gKey = null, gSeq = 0;

  /* ---------- pending (un-acked local writes) ---------- */
  var tracking = false;
  var batchNo = 0;
  var pendQ = [];             /* batches in the order they were made: {b, recs} */
  var pendB = new Map();      /* b -> batch */
  var opRec = new WeakMap();  /* op object -> its record */
  var pcnt = new Map();       /* "id\nprop" -> how many un-acked local writes */
  var pbase = new Map();      /* "id\nprop" -> the value the server has (undefined = no such prop) */
  var pdel = new Map();       /* id -> count: nodes inside a subtree we deleted, not confirmed yet */
  var pghost = new Set();     /* ids the server has (for now) and we do not show: they sit under something we deleted */
  var pmove = new Set();      /* ids with an un-acked local `parent` write: the server still has them elsewhere */

  var store = HD.store = {ROOT: ROOT, TYPES: TYPES, readOnly: false};
  var sel;                    /* HD.sel, defined below */

  function same(a, b) {
    if (a === b) return true;
    if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
    var aa = isArr(a), i;
    if (aa !== isArr(b)) return false;
    if (aa) {
      if (a.length !== b.length) return false;
      for (i = 0; i < a.length; i++) if (!same(a[i], b[i])) return false;
      return true;
    }
    var ka = Object.keys(a);
    if (ka.length !== Object.keys(b).length) return false;
    for (i = 0; i < ka.length; i++) if (!hasOwn.call(b, ka[i]) || !same(a[ka[i]], b[ka[i]])) return false;
    return true;
  }
  function toArr(ids) { return isArr(ids) ? ids : (ids === undefined || ids === null) ? [] : (ids instanceof Set ? Array.from(ids) : [ids]); }

  /* ================================================================ tree primitives (no recording) */
  function cmpChild(a, b) {
    var na = nodes.get(a), nb = nodes.get(b);
    var ia = na && na.idx !== undefined ? na.idx : '', ib = nb && nb.idx !== undefined ? nb.idx : '';
    return ia < ib ? -1 : ia > ib ? 1 : a < b ? -1 : a > b ? 1 : 0;
  }
  function attach(pid, id) {
    if (pid === undefined || pid === null) return;
    var ks = kidSet.get(pid);
    if (!ks) { ks = new Set(); kidSet.set(pid, ks); if (!tail.has(pid)) tail.set(pid, null); }
    ks.add(id);
    sorted.delete(pid);
    if (tail.has(pid)) {
      var t = tail.get(pid);
      if (t === null || cmpChild(id, t) > 0) tail.set(pid, id);
    }
  }
  function detach(pid, id) {
    var ks = kidSet.get(pid);
    if (ks) ks.delete(id);
    sorted.delete(pid);
    if (tail.get(pid) === id) tail.delete(pid);
  }
  function childrenOf(id) {
    var s = sorted.get(id);
    if (s) return s;
    var ks = kidSet.get(id);
    if (!ks || !ks.size) return EMPTY;
    s = Array.from(ks);
    if (s.length > 1) s.sort(cmpChild);
    Object.freeze(s);
    sorted.set(id, s);
    return s;
  }
  function lastChild(pid) {
    if (tail.has(pid)) return tail.get(pid);
    var s = sorted.get(pid), t = null;
    if (s) t = s.length ? s[s.length - 1] : null;
    else {
      var ks = kidSet.get(pid);
      if (ks) ks.forEach(function (k) { if (t === null || cmpChild(k, t) > 0) t = k; });
    }
    tail.set(pid, t);
    return t;
  }

  /* cache invalidation: the subtree bounds of `id`'s ancestors */
  function dirtyUpFrom(pid) {
    var c = pid, n;
    while (c !== undefined && sb.has(c)) { sb.delete(c); n = nodes.get(c); c = n ? n.parent : undefined; }
  }
  function dirtyUp(id) {
    sb.delete(id);
    var n = nodes.get(id);
    if (n) dirtyUpFrom(n.parent);
  }
  /* the world matrix of `id` and of everything under it (only the part that was ever computed) */
  function dirtyWorld(id) {
    if (!wm.has(id)) return;
    var stack = [id], c, ks;
    while (stack.length) {
      c = stack.pop();
      wm.delete(c); wb.delete(c); sb.delete(c);
      ks = kidSet.get(c);
      if (ks && ks.size) ks.forEach(function (k) { if (wm.has(k)) stack.push(k); });
    }
  }

  var KIND = {x: 1, y: 1, w: 2, h: 2, rot: 3, flipH: 3, flipV: 3, parent: 4, idx: 5, visible: 6, clip: 6, type: 7};

  /* write props into an existing node. Returns null (nothing changed) or [changed, previous]:
     changed = {prop: new value | null}, previous = {prop: old value | null (it did not exist)}. */
  function rawSet(id, n, p) {
    var prev = null, chg = null, flags = 0, k, v, old, f;
    for (k in p) {
      v = p[k];
      if (v === undefined) continue;
      old = n[k];
      if (v === null) {
        if (old === undefined) continue;
        delete n[k];
      } else {
        if (typeof v === 'number' && v !== v) continue;                       /* NaN never enters the document */
        if (old === v ? typeof v !== 'object' : same(old, v)) continue;
        n[k] = v;
      }
      if (prev === null) { prev = {}; chg = {}; }
      prev[k] = old === undefined ? null : old;
      chg[k] = v;
      f = KIND[k];
      if (f !== undefined) flags |= 1 << f;
    }
    if (prev === null) return null;
    if (flags) afterSet(id, n, prev, flags);
    return [chg, prev];
  }
  function afterSet(id, n, prev, flags) {
    var pid;
    if (flags & 16) {                                   /* parent */
      if (prev.parent !== null) { detach(prev.parent, id); dirtyUpFrom(prev.parent); }
      attach(n.parent, id);
      dirtyWorld(id); dirtyUp(id);
    } else if (flags & 32) {                            /* idx alone */
      pid = n.parent;
      if (pid !== undefined) { sorted.delete(pid); tail.delete(pid); }
    }
    if (flags & (2 | 8 | 128)) {                        /* x y / rot flips / type */
      lm.delete(id); dirtyWorld(id); dirtyUp(id);
    } else if (flags & 4) {                             /* w h */
      if (n.rot || n.flipH || n.flipV) { lm.delete(id); dirtyWorld(id); } else wb.delete(id);
      dirtyUp(id);
    }
    if (flags & 64) dirtyUp(id);                        /* visible / clip */
  }
  function rawCreate(id, node) {
    nodes.set(id, node);
    attach(node.parent, id);
    dirtyUpFrom(node.parent);
  }
  /* remove a node and its subtree; returns [[id, node], ...] parents before children */
  function rawDelete(id) {
    var n0 = nodes.get(id), out = [];
    if (!n0) return out;
    if (n0.parent !== undefined) { detach(n0.parent, id); dirtyUpFrom(n0.parent); }
    var stack = [id], c, n, ks;
    while (stack.length) {
      c = stack.pop();
      n = nodes.get(c);
      if (!n) continue;
      out.push([c, n]);
      nodes.delete(c);
      lm.delete(c); wm.delete(c); wb.delete(c); sb.delete(c);
      ks = kidSet.get(c);
      if (ks) { ks.forEach(function (k) { stack.push(k); }); kidSet.delete(c); }
      sorted.delete(c); tail.delete(c);
    }
    return out;
  }
  function isAncestor(a, b) {             /* is a an ancestor of b */
    var n = nodes.get(b), c = n ? n.parent : undefined, guard = 0;
    while (c !== undefined && ++guard < 200000) {       /* the guard: a loop in stored data never hangs the page */
      if (c === a) return true;
      n = nodes.get(c);
      c = n ? n.parent : undefined;
    }
    return guard >= 200000;
  }
  function okParent(id, pid) {
    return id !== ROOT && typeof pid === 'string' && pid !== id && nodes.has(pid) && !isAncestor(id, pid);
  }
  function cleanCopy(p) {
    var o = {}, k, v;
    for (k in p) { v = p[k]; if (v !== null && v !== undefined) o[k] = v; }
    return o;
  }

  /* ================================================================ matrices + bounds */
  function localRaw(id) {
    var m = lm.get(id);
    if (m) return m;
    var n = nodes.get(id);
    if (!n) return IDENT;
    if (n.type === 'PAGE' || n.type === 'DOCUMENT') m = IDENT;
    else {
      var d = DEF[n.type] || NO_DEF;
      m = M.nodeMatrix(+n.x || 0, +n.y || 0,
        n.w === undefined ? (d.w || 0) : +n.w || 0, n.h === undefined ? (d.h || 0) : +n.h || 0,
        +n.rot || 0, !!n.flipH, !!n.flipV);
    }
    lm.set(id, m);
    return m;
  }
  function worldRaw(id) {
    var m = wm.get(id);
    if (m) return m;
    var chain = [], c = id, base = IDENT, n, guard = 0;
    while (c !== undefined) {
      m = wm.get(c);
      if (m) { base = m; break; }
      n = nodes.get(c);
      if (!n || ++guard > 100000) break;
      chain.push(c);
      c = n.parent;
    }
    for (var i = chain.length - 1; i >= 0; i--) {
      m = localRaw(chain[i]);
      base = m === IDENT ? base : base === IDENT ? m : M.mul(base, m);
      wm.set(chain[i], base);
    }
    return base;
  }
  function boundsRaw(id) {
    var n = nodes.get(id);
    if (!n) return null;
    if (n.type === 'PAGE' || n.type === 'DOCUMENT') return subtreeRaw(id);
    var r = wb.get(id);
    if (r) return r;
    var d = DEF[n.type] || NO_DEF;
    r = M.boundsOf(worldRaw(id), n.w === undefined ? (d.w || 0) : +n.w || 0, n.h === undefined ? (d.h || 0) : +n.h || 0);
    wb.set(id, r);
    return r;
  }
  var ZERO = {x: 0, y: 0, w: 0, h: 0};
  function subtreeRaw(id) {
    var r = sb.get(id);
    if (r) return r;
    var n = nodes.get(id);
    if (!n) return null;
    var page = n.type === 'PAGE' || n.type === 'DOCUMENT';
    r = page ? null : boundsRaw(id);
    var clip = n.clip === undefined ? !!(DEF[n.type] || NO_DEF).clip : !!n.clip;
    if (page || !clip) {
      var ks = kidSet.get(id);
      if (ks && ks.size) {
        var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, any = false;
        if (r) { x0 = r.x; y0 = r.y; x1 = r.x + r.w; y1 = r.y + r.h; any = true; }
        ks.forEach(function (k) {
          var kn = nodes.get(k);
          if (!kn || kn.visible === false) return;
          var b = subtreeRaw(k);
          if (!b) return;
          any = true;
          if (b.x < x0) x0 = b.x;
          if (b.y < y0) y0 = b.y;
          if (b.x + b.w > x1) x1 = b.x + b.w;
          if (b.y + b.h > y1) y1 = b.y + b.h;
        });
        if (any) r = {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
      }
    }
    if (!r) r = ZERO;
    sb.set(id, r);
    return r;
  }
  function copyRect(r) { return r ? {x: r.x, y: r.y, w: r.w, h: r.h} : {x: 0, y: 0, w: 0, h: 0}; }

  /* ================================================================ the open tx: recording */
  function newTx(label, kind, key) {
    return {
      label: label || '', kind: kind, key: key || null,
      steps: [],                 /* [forward op, inverse op | inverse ops[] | null] in the order things happened */
      made: new Set(),           /* ids created in this tx */
      changed: new Set(), removed: new Set(), extra: new Set(), props: new Map(),
      structural: false,
      first: tracking ? new Map() : null,   /* "id\nprop" -> value before this tx (null = absent) */
      created: tracking ? new Set() : null, /* forward ops that create a node */
      again: tracking ? new Set() : null,   /* ...those of them that bring back a node that existed before (undo of a delete) */
      dels: null,                /* Map forward del op -> inverse creates */
      sel0: sel.ids
    };
  }
  function noteProps(t, id, chg) {
    var s = t.props.get(id);
    if (!s) { s = new Set(); t.props.set(id, s); }
    for (var k in chg) s.add(k);
  }
  /* set on an existing node, recorded. The caller has checked a parent change. */
  function recSet(id, n, p) {
    var oldParent = n.parent;
    var r = rawSet(id, n, p);
    if (!r) return false;
    var t = cur, chg = r[0], prev = r[1];
    t.steps.push([{id: id, p: chg}, {id: id, p: prev}]);
    t.changed.add(id);
    noteProps(t, id, chg);
    if (hasOwn.call(chg, 'parent')) {
      t.structural = true;
      if (oldParent !== undefined) t.extra.add(oldParent);
      t.extra.add(n.parent);
    } else if (hasOwn.call(chg, 'idx') || hasOwn.call(chg, 'type')) {
      t.structural = true;
      if (n.parent !== undefined) t.extra.add(n.parent);
    }
    if (t.first) {
      for (var k in prev) {
        var key = id + '\n' + k;
        if (!t.first.has(key)) t.first.set(key, prev[k]);
      }
    }
    return true;
  }
  function recCreate(id, node, again) {
    rawCreate(id, node);
    var t = cur, op = {id: id, p: Object.assign({}, node)};
    /* created under a node that this tx created too: undoing the outer one removes it, no delete of its own */
    t.steps.push([op, t.made.has(node.parent) ? null : {id: id, del: 1}]);
    t.made.add(id);
    t.changed.add(id);
    t.extra.add(node.parent);
    t.structural = true;
    if (t.created) { t.created.add(op); if (again) t.again.add(op); }
  }
  function recDelete(id) {
    var n0 = nodes.get(id);
    if (!n0 || id === ROOT) return false;
    var pid = n0.parent, list = rawDelete(id), t = cur, inv = new Array(list.length);
    for (var i = 0; i < list.length; i++) {
      inv[i] = {id: list[i][0], p: list[i][1]};
      t.changed.add(list[i][0]);
      t.removed.add(list[i][0]);
    }
    var op = {id: id, del: 1};
    t.steps.push([op, inv]);
    if (pid !== undefined) t.extra.add(pid);
    t.structural = true;
    if (tracking) (t.dels || (t.dels = new Map())).set(op, inv);
    return true;
  }
  /* apply one op the way the server would, recorded (undo / redo use this) */
  function recOp(op) {
    if (!op || typeof op.id !== 'string') return false;
    if (op.del) return recDelete(op.id);
    var p = op.p, n = nodes.get(op.id);
    if (!p) return false;
    if (n) {
      if (p.parent !== undefined && p.parent !== n.parent && !okParent(op.id, p.parent)) return false;
      if (p.type !== undefined && p.type !== null && !hasOwn.call(DEF, p.type)) return false;
      return recSet(op.id, n, p);
    }
    if (p.type === undefined || !hasOwn.call(DEF, p.type) || op.id === ROOT || !nodes.has(p.parent)) return false;
    recCreate(op.id, cleanCopy(p), true);
    return true;
  }
  /* the same without recording (abort, re-apply after a reload) */
  function rawOp(op) {
    if (!op || typeof op.id !== 'string') return null;
    if (op.del) {
      if (op.id === ROOT || !nodes.has(op.id)) return null;
      return {del: rawDelete(op.id)};
    }
    var p = op.p, n = nodes.get(op.id);
    if (!p) return null;
    if (n) {
      if (p.parent !== undefined && p.parent !== n.parent && !okParent(op.id, p.parent)) return null;
      var r = rawSet(op.id, n, p);
      return r ? {set: r} : {set: null};
    }
    if (p.type === undefined || !hasOwn.call(DEF, p.type) || op.id === ROOT || !nodes.has(p.parent)) return null;
    rawCreate(op.id, cleanCopy(p));
    return {create: true};
  }

  /* merge a list of ops: sets on one node fold into its earlier op (later value wins). A set that changes
     `parent` only folds into the op right before it (reordering a reparent could build a cycle on the server),
     and nothing folds across a delete. */
  function mergeOps(list) {
    if (list.length < 2) return list;
    var out = [], last = new Map(), holes = 0, i, op, j, t, k;
    for (i = 0; i < list.length; i++) {
      op = list[i];
      if (op.del) {
        j = last.get(op.id);                 /* a plain set right before its own delete says nothing */
        if (j !== undefined && out[j].p.type === undefined) { out[j] = null; holes++; }
        out.push(op); last.clear();
        continue;
      }
      j = last.get(op.id);
      if (j !== undefined && (j === out.length - 1 || !hasOwn.call(op.p, 'parent'))) {
        t = out[j].p;
        for (k in op.p) t[k] = op.p[k];
        continue;
      }
      last.set(op.id, out.length);
      out.push(op);
    }
    if (holes) out = out.filter(function (o) { return o !== null; });
    return out;
  }

  function register(b, ops, t) {
    var recs = new Array(ops.length), i, op, rec, k, key, keys, props, inv, j, c;
    for (i = 0; i < ops.length; i++) {
      op = ops[i];
      rec = {op: op, kind: 'set', keys: null, props: null, ids: null, snap: null, live: true, done: false, again: false};
      if (op.del) {
        rec.kind = 'del';
        inv = t.dels ? t.dels.get(op) : null;
        rec.snap = inv || [];
        rec.ids = new Array(rec.snap.length);
        for (j = 0; j < rec.snap.length; j++) {
          rec.ids[j] = rec.snap[j].id;
          pdel.set(rec.ids[j], (pdel.get(rec.ids[j]) || 0) + 1);
        }
      } else {
        var made = t.created.has(op);
        if (made) { rec.kind = 'create'; rec.again = t.again.has(op); }
        keys = []; props = [];
        for (k in op.p) {
          key = op.id + '\n' + k;
          c = pcnt.get(key);
          if (c === undefined) {
            var was = made ? undefined : t.first.get(key);
            pbase.set(key, was === null ? undefined : was);
            pcnt.set(key, 1);
          } else pcnt.set(key, c + 1);
          keys.push(key); props.push(k);
          if (k === 'parent') pmove.add(op.id);
        }
        rec.keys = keys; rec.props = props;
      }
      recs[i] = rec;
      opRec.set(op, rec);
    }
    var batch = {b: b, recs: recs};
    pendQ.push(batch);
    pendB.set(b, batch);
  }

  function layoutIds(t) {
    var s = new Set();
    t.changed.forEach(function (id) { if (nodes.has(id)) s.add(id); });
    t.extra.forEach(function (id) { if (nodes.has(id)) s.add(id); });
    return s;
  }

  function abortTx() {
    var steps = cur.steps, i, inv, j;
    cur = null; depth = 0;
    for (i = steps.length - 1; i >= 0; i--) {
      inv = steps[i][1];
      if (inv === null) continue;
      if (isArr(inv)) for (j = 0; j < inv.length; j++) rawOp({id: inv[j].id, p: inv[j].p});
      else rawOp(inv);
    }
  }

  function commitTx() {
    var t = cur, steps = t.steps, i, j, inv, fwd, back;
    cur = null; depth = 0;
    if (!steps.length) return false;
    if (steps.length === 1) {
      fwd = [steps[0][0]];
      back = isArr(steps[0][1]) ? steps[0][1] : steps[0][1] === null ? [] : [steps[0][1]];
    } else {
      fwd = new Array(steps.length);
      for (i = 0; i < steps.length; i++) fwd[i] = steps[i][0];
      fwd = mergeOps(fwd);
      back = [];
      for (i = steps.length - 1; i >= 0; i--) {
        inv = steps[i][1];
        if (inv === null) continue;
        if (isArr(inv)) for (j = 0; j < inv.length; j++) back.push(inv[j]); else back.push(inv);
      }
      back = mergeOps(back);
    }
    var b = ++batchNo;
    if (tracking) register(b, fwd, t);

    var entry = {label: t.label, ops: back, sel0: t.sel0, key: t.key};
    if (t.kind === 'do') {
      redoS.length = 0;
      var top = undoS[undoS.length - 1];
      if (t.key !== null && top && top.key === t.key) top.ops = mergeOps(back.concat(top.ops));
      else { undoS.push(entry); if (undoS.length > UNDO_MAX) undoS.shift(); }
    } else if (t.kind === 'undo') redoS.push(entry);
    else { undoS.push(entry); if (undoS.length > UNDO_MAX) undoS.shift(); }

    if (t.removed.size) sel._drop(t.removed);
    em.emit('ops', fwd, b);
    em.emit('change', {
      ids: t.changed, structural: t.structural, remote: false, removed: t.removed, props: t.props,
      label: t.label, undo: t.kind !== 'do'
    });
    return true;
  }

  function runTx(label, kind, fn, key) {
    cur = newTx(label, kind, key);
    depth = 1;
    var out;
    try { out = fn(); } catch (err) { abortTx(); throw err; }
    if (cur.steps.length && HD.layout && typeof HD.layout.run === 'function') {
      try { HD.layout.run(layoutIds(cur), cur.props); } catch (err2) { report(err2); }
    }
    commitTx();
    return out;
  }
  var warned = false;
  function blocked() {
    if (!store.readOnly) return false;
    if (!warned && W.console && W.console.warn) { warned = true; W.console.warn('[HD] the document is read-only: edit ignored'); }
    return true;
  }
  function inTx(label, fn) {
    if (depth > 0) return fn();
    if (blocked()) return undefined;
    return runTx(label, 'do', fn, gKey);
  }

  /* ================================================================ public: reading */
  store.get = function (id) { return nodes.get(id); };
  store.has = function (id) { return nodes.has(id); };
  /* the value of a property, or its default for the node's type when the node does not carry it */
  store.prop = function (id, name) {
    var n = nodes.get(id);
    if (!n) return undefined;
    var v = n[name];
    return v !== undefined ? v : (DEF[n.type] || NO_DEF)[name];
  };
  store.defaults = function (type) { return clone(DEF[type] || NO_DEF); };
  store.children = function (id) { return childrenOf(id); };
  store.parent = function (id) { var n = nodes.get(id); return n ? n.parent : undefined; };
  store.pageOf = function (id) {
    var c = id, n;
    while (c !== undefined) {
      n = nodes.get(c);
      if (!n) return undefined;
      if (n.type === 'PAGE') return c;
      c = n.parent;
    }
    return undefined;
  };
  store.pages = function () {
    var ks = childrenOf(ROOT), out = [];
    for (var i = 0; i < ks.length; i++) if (nodes.get(ks[i]).type === 'PAGE') out.push(ks[i]);
    return out;
  };
  /* [parent, grandparent, ..., root] */
  store.ancestors = function (id) {
    var out = [], n = nodes.get(id), c = n ? n.parent : undefined;
    while (c !== undefined && nodes.has(c)) { out.push(c); c = nodes.get(c).parent; }
    return out;
  };
  store.isAncestor = function (a, b) { return isAncestor(a, b); };
  /* depth-first, parents first, children in z order. fn(id, node, depth); return false to skip that subtree. */
  store.walk = function (id, fn) {
    if (!nodes.has(id)) return;
    var stack = [id], ds = [0], c, d, ks, i;
    while (stack.length) {
      c = stack.pop(); d = ds.pop();
      if (fn(c, nodes.get(c), d) === false) continue;
      ks = childrenOf(c);
      for (i = ks.length - 1; i >= 0; i--) { stack.push(ks[i]); ds.push(d + 1); }
    }
  };
  /* the ids sorted in document order (parents before children, lower layers first) */
  store.order = function (ids) {
    ids = toArr(ids).filter(function (id) { return nodes.has(id); });
    if (ids.length < 2) return ids.slice();
    var paths = new Map();
    ids.forEach(function (id) {
      var p = [], c = id;
      while (c !== undefined && nodes.has(c)) { p.push(c); c = nodes.get(c).parent; }
      paths.set(id, p.reverse());
    });
    return ids.slice().sort(function (a, b) {
      var pa = paths.get(a), pb = paths.get(b), n = Math.min(pa.length, pb.length);
      for (var i = 0; i < n; i++) if (pa[i] !== pb[i]) return cmpChild(pa[i], pb[i]);
      return pa.length - pb.length;
    });
  };
  store.count = function () { return nodes.size; };
  store.toDoc = function () {
    var out = {};
    nodes.forEach(function (n, id) { out[id] = n; });
    return {nodes: out};
  };
  store.localMatrix = function (id) { return localRaw(id).slice(); };
  store.worldMatrix = function (id) { return worldRaw(id).slice(); };
  /* world box of the node's own (0,0)..(w,h); for a PAGE: of everything on it */
  store.worldBounds = function (id) { return copyRect(boundsRaw(id)); };
  /* world box of the node AND what it shows outside itself: visible descendants, stopped at a clipping frame */
  store.subtreeBounds = function (id) { return copyRect(subtreeRaw(id)); };

  /* ================================================================ public: editing */
  store.newId = function () {
    var id;
    do { id = cid + ':' + (++counter); } while (nodes.has(id));
    return id;
  };
  function nextName(type) {
    var label = LABEL[type] || type, n = nameN.get(type);
    if (n === undefined) {
      n = 0;
      var pre = label + ' ', L = pre.length;
      nodes.forEach(function (nd) {
        if (nd.type !== type || typeof nd.name !== 'string' || nd.name.length <= L || nd.name.slice(0, L) !== pre) return;
        var tail2 = nd.name.slice(L);
        if (/^\d{1,9}$/.test(tail2)) { var v = +tail2; if (v > n) n = v; }
      });
    }
    n++;
    nameN.set(type, n);
    return label + ' ' + n;
  }
  function idxOf(id) { var n = nodes.get(id); return n && n.idx !== undefined ? n.idx : null; }
  /* [a, b]: the idx bounds for a new child of pid placed before beforeId (or last). skip = ids to look past */
  function slot(pid, beforeId, skip) {
    var ks, i;
    if (beforeId !== undefined && beforeId !== null) {
      var bn = nodes.get(beforeId);
      if (bn && bn.parent === pid) {
        ks = childrenOf(pid);
        i = ks.indexOf(beforeId) - 1;
        while (i >= 0 && skip && skip.has(ks[i])) i--;
        return [i >= 0 ? idxOf(ks[i]) : null, idxOf(beforeId)];
      }
    }
    if (!skip) return [idxOf(lastChild(pid)), null];
    ks = childrenOf(pid);
    i = ks.length - 1;
    while (i >= 0 && skip.has(ks[i])) i--;
    return [i >= 0 ? idxOf(ks[i]) : null, null];
  }

  store.create = function (type, parentId, props, beforeId) {
    if (!hasOwn.call(DEF, type)) throw new Error('HD.store.create: unknown type ' + type);
    return inTx('Create', function () {
      if (!nodes.has(parentId)) throw new Error('HD.store.create: no such parent ' + parentId);
      var id = store.newId(), s = slot(parentId, beforeId, null);
      var node = {type: type, parent: parentId, idx: between(s[0], s[1]), name: ''}, k, v;
      if (props) {
        for (k in props) {
          v = props[k];
          if (v === undefined || v === null || k === 'type' || k === 'parent' || k === 'idx') continue;
          if (typeof v === 'number' && v !== v) continue;
          node[k] = v;
        }
      }
      if (typeof node.name !== 'string' || !node.name) node.name = nextName(type);
      recCreate(id, node);
      return id;
    });
  };

  store.set = function (id, props) {
    if (!props) return false;
    return inTx('Change', function () {
      var n = nodes.get(id);
      if (!n) return false;
      if (props.parent !== undefined && props.parent !== n.parent && !okParent(id, props.parent)) {
        props = Object.assign({}, props);            /* a reparent that can not be: keep the rest of the edit */
        delete props.parent; delete props.idx;
      }
      if (props.type !== undefined && !hasOwn.call(DEF, props.type)) {
        props = Object.assign({}, props); delete props.type;
      }
      return recSet(id, n, props);
    }) || false;
  };

  store.remove = function (ids) {
    ids = toArr(ids);
    return inTx('Delete', function () {
      var any = false;
      for (var i = 0; i < ids.length; i++) if (recDelete(ids[i])) any = true;     /* a child of an already removed node is simply gone */
      return any;
    }) || false;
  };

  /* reparent / reorder. The nodes keep their place on the canvas: x, y, rot (and flipH) are rewritten for the
     new parent. They keep their order among themselves and land before beforeId (null = on top). */
  store.move = function (ids, parentId, beforeId) {
    ids = toArr(ids);
    return inTx('Move', function () {
      if (!nodes.has(parentId)) return false;
      var seen = new Set(), list = [], i, id;
      for (i = 0; i < ids.length; i++) {
        id = ids[i];
        if (seen.has(id) || !nodes.has(id) || !okParent(id, parentId)) continue;
        seen.add(id); list.push(id);
      }
      list = list.filter(function (x) {                 /* a node whose ancestor moves too goes along with it */
        var p = nodes.get(x).parent;
        while (p !== undefined) { if (seen.has(p)) return false; p = nodes.get(p) ? nodes.get(p).parent : undefined; }
        return true;
      });
      if (!list.length) return false;
      list = store.order(list);
      var moving = new Set(list), ks, j;
      if (beforeId !== undefined && beforeId !== null) {
        var bn = nodes.get(beforeId);
        if (!bn || bn.parent !== parentId) beforeId = null;
        else if (moving.has(beforeId)) {
          ks = childrenOf(parentId);
          j = ks.indexOf(beforeId) + 1;
          while (j < ks.length && moving.has(ks[j])) j++;
          beforeId = j < ks.length ? ks[j] : null;
        }
      }
      var s = slot(parentId, beforeId, moving), keys = nBetween(s[0], s[1], list.length);
      var ip = null, any = false;
      for (i = 0; i < list.length; i++) {
        id = list[i];
        var n = nodes.get(id), p = {parent: parentId, idx: keys[i]};
        if (n.parent !== parentId && n.type !== 'PAGE' && n.type !== 'DOCUMENT') {
          if (ip === null) ip = M.inv(worldRaw(parentId));
          var d = DEF[n.type] || NO_DEF;
          var w = n.w === undefined ? (d.w || 0) : +n.w || 0, h = n.h === undefined ? (d.h || 0) : +n.h || 0;
          var m = M.mul(ip, worldRaw(id));
          var fy = n.flipV ? -1 : 1, fx = (m[0] * m[3] - m[1] * m[2] < 0 ? -1 : 1) * fy;
          var rot = M.round(M.normDeg(Math.atan2(m[1] * fx, m[0] * fx) * 180 / Math.PI), 6);
          var c = M.apply(m, w / 2, h / 2), x = M.round(c[0] - w / 2, 6), y = M.round(c[1] - h / 2, 6);
          if (x !== (+n.x || 0)) p.x = x;
          if (y !== (+n.y || 0)) p.y = y;
          if (rot !== M.normDeg(+n.rot || 0)) p.rot = rot;
          if ((fx < 0) !== !!n.flipH) p.flipH = fx < 0;
        }
        if (recSet(id, n, p)) any = true;
      }
      return any;
    }) || false;
  };

  /* tx(label, fn [, {merge: key}])  everything inside = ONE undo step and ONE op batch; a tx inside a tx joins it.
     {merge: key}: this tx joins the previous undo step when that one was made with the same key (a drag that
     sends an update on every pointer move and still undoes in one step). Use a key that is unique per gesture,
     or gesture() / gestureEnd(). */
  store.tx = function (label, fn, opts) {
    if (typeof label === 'function') { opts = fn; fn = label; label = ''; }
    if (typeof fn !== 'function') return undefined;
    if (depth > 0) { depth++; try { return fn(); } finally { depth--; } }
    if (blocked()) return undefined;
    return runTx(label, 'do', fn, opts && opts.merge !== undefined && opts.merge !== null ? 'm:' + opts.merge : gKey);
  };
  store.inTx = function () { return depth > 0; };
  /* from now until gestureEnd() every tx lands in ONE undo step (ops still go out per tx) */
  store.gesture = function () { gKey = 'g:' + (++gSeq); };
  store.gestureEnd = function () {
    gKey = null;
    var top = undoS[undoS.length - 1];
    if (top) top.key = null;                           /* sealed: nothing merges into it any more */
  };

  function replay(from, kind) {
    if (depth > 0 || !from.length || blocked()) return false;
    var e = from.pop();               /* a step whose nodes other people removed is simply used up */
    runTx(e.label, kind, function () {
      for (var i = 0; i < e.ops.length; i++) recOp(e.ops[i]);
    }, null);
    var ids = e.sel0 ? e.sel0.filter(function (id) { return nodes.has(id); }) : [];
    if (ids.length) {
      var pg = store.pageOf(ids[0]);
      if (pg && pg !== sel.page) sel.setPage(pg);
    }
    sel.set(ids);
    return true;
  }
  store.undo = function () { return replay(undoS, 'undo'); };
  store.redo = function () { return replay(redoS, 'redo'); };
  store.canUndo = function () { return undoS.length > 0; };
  store.canRedo = function () { return redoS.length > 0; };
  store.undoLabel = function () { var e = undoS[undoS.length - 1]; return e ? e.label : null; };
  store.redoLabel = function () { var e = redoS[redoS.length - 1]; return e ? e.label : null; };

  /* ================================================================ public: events */
  store.on = function (evt, fn) { return em.on(evt, fn); };
  store.off = function (evt, fn) { em.off(evt, fn); };
  store.onOps = function (fn) { return em.on('ops', fn); };

  /* ================================================================ sync: pending, ack, rollback, remote */
  store.tracking = function (on) {
    if (on === undefined) return tracking;
    on = !!on;
    if (on === tracking) return tracking;
    tracking = on;
    clearPending();
    return tracking;
  };
  function clearPending() {
    pendQ = []; pendB.clear(); pcnt.clear(); pbase.clear(); pdel.clear(); pghost.clear(); pmove.clear();
    opRec = new WeakMap();
  }
  store.pendingCount = function () { return pendQ.length; };

  function release(rec, accepted) {
    var i, key, c;
    if (rec.keys) {
      for (i = 0; i < rec.keys.length; i++) {
        key = rec.keys[i];
        c = pcnt.get(key);
        if (c === undefined) continue;
        if (c <= 1) { pcnt.delete(key); pbase.delete(key); if (rec.props[i] === 'parent') pmove.delete(rec.op.id); }
        else {
          pcnt.set(key, c - 1);
          if (accepted) { var v = rec.op.p[rec.props[i]]; pbase.set(key, v === null ? undefined : v); }
        }
      }
    }
    if (rec.ids) {
      for (i = 0; i < rec.ids.length; i++) {
        c = pdel.get(rec.ids[i]);
        if (c === undefined) continue;
        if (c <= 1) pdel.delete(rec.ids[i]); else pdel.set(rec.ids[i], c - 1);
      }
      if (!pdel.size) pghost.clear();        /* every delete of ours is answered: nothing is doomed any more */
    }
  }
  store.acked = function (b) {
    var batch = pendB.get(b);
    if (!batch) return false;
    pendB.delete(b);
    if (pendQ[0] === batch) pendQ.shift();
    else { var qi = pendQ.indexOf(batch); if (qi >= 0) pendQ.splice(qi, 1); }
    var ch = null, desync = false, j, i, rec, op, n, key, c, v, fix, r;
    for (j = 0; j < batch.recs.length; j++) {
      rec = batch.recs[j];
      if (rec.done) continue;
      rec.done = true;
      if (!rec.live) continue;
      if (rec.kind === 'del') { release(rec, true); continue; }
      /* a set / create the server took. Normally the node already shows exactly this. It does not when the op
         could not be applied here at the time (after a reload) or the node was re-made by someone meanwhile:
         then what the server now has is put on screen. */
      op = rec.op; n = nodes.get(op.id); fix = null;
      for (i = 0; i < rec.keys.length; i++) {
        key = rec.keys[i];
        c = pcnt.get(key);
        if (c === undefined) continue;
        v = op.p[rec.props[i]];
        if (c <= 1) {
          pcnt.delete(key); pbase.delete(key);
          if (rec.props[i] === 'parent') pmove.delete(op.id);
          if (n && (v === null ? n[rec.props[i]] !== undefined : !same(n[rec.props[i]], v))) (fix || (fix = {}))[rec.props[i]] = v;
        } else { pcnt.set(key, c - 1); pbase.set(key, v === null ? undefined : v); }
      }
      if (n) {
        if (!fix) continue;
        /* the node is here only because a LATER edit of ours re-made it: whether the server had it when this
           op arrived can not be known from here */
        if (pcnt.has(op.id + '\ntype')) { desync = true; continue; }
        if (hasOwn.call(fix, 'parent') && fix.parent !== n.parent && !okParent(op.id, fix.parent)) {
          desync = true;
          delete fix.parent; delete fix.idx;
        }
        r = rawSet(op.id, n, fix);
        if (r) chSet(ch || (ch = newChange()), op.id, r[0]);
      } else if (op.p.type !== undefined && !pdel.has(op.id) && !pghost.has(op.id)) {
        if (hasOwn.call(DEF, op.p.type) && nodes.has(op.p.parent)) {
          rawCreate(op.id, cleanCopy(op.p));
          ch = ch || newChange();
          ch.ids.add(op.id); ch.structural = true;
        } else if (!pdel.has(op.p.parent) && !pghost.has(op.p.parent)) desync = true;
      }
    }
    if (ch || desync) finish(ch || newChange(), desync);
    return true;
  };

  function newChange() { return {ids: new Set(), structural: false, remote: true, removed: new Set(), props: new Map()}; }
  function chSet(ch, id, chg) {
    ch.ids.add(id);
    var s = ch.props.get(id);
    if (!s) { s = new Set(); ch.props.set(id, s); }
    for (var k in chg) s.add(k);
    if (hasOwn.call(chg, 'parent') || hasOwn.call(chg, 'idx') || hasOwn.call(chg, 'type')) ch.structural = true;
  }
  function chDel(ch, list) {
    for (var i = 0; i < list.length; i++) { ch.ids.add(list[i][0]); ch.removed.add(list[i][0]); }
    if (list.length) ch.structural = true;
  }
  function finish(ch, desync) {
    if (ch.removed.size) sel._drop(ch.removed);
    if (ch.ids.size) em.emit('change', ch);
    if (desync) em.emit('desync', {});
  }
  function findRec(op) {                    /* a rejected op that is not the object we handed out: match by content */
    for (var i = 0; i < pendQ.length; i++) {
      var recs = pendQ[i].recs;
      for (var j = 0; j < recs.length; j++) {
        var r = recs[j];
        if (!r.done && r.op.id === op.id && !!r.op.del === !!op.del && (op.del || same(r.op.p, op.p))) return r;
      }
    }
    return null;
  }
  store.rollback = function (ops) {
    ops = toArr(ops);
    var ch = newChange(), desync = false, i, j, op, rec, n, key, c, r;
    for (i = 0; i < ops.length; i++) {
      op = ops[i];
      rec = opRec.get(op) || findRec(op);
      if (!rec || rec.done) continue;
      rec.done = true;
      if (!rec.live) continue;
      if (rec.kind === 'del') {
        release(rec, false);
        for (j = 0; j < rec.snap.length; j++) {
          var s = rec.snap[j];
          if (nodes.has(s.id)) continue;
          if (!nodes.has(s.p.parent)) { desync = true; continue; }
          rawCreate(s.id, cleanCopy(s.p));
          ch.ids.add(s.id); ch.structural = true;
        }
      } else if (rec.kind === 'create') {
        release(rec, false);
        /* a brand-new node the server refused: gone. A node being brought BACK (undo of a delete) may still be
           alive on the server, where our delete perhaps never reached it: only a reload can tell. */
        if (rec.again) desync = true;
        else if (nodes.has(op.id)) {
          var lostList = rawDelete(op.id);
          if (pmove.size && movedIn(lostList, 1)) desync = true;      /* something we moved into it lives on elsewhere */
          chDel(ch, lostList);
        }
      } else {
        var back = null;
        for (j = 0; j < rec.keys.length; j++) {
          key = rec.keys[j];
          c = pcnt.get(key);
          if (c === undefined) continue;
          if (c <= 1) {
            var v = pbase.get(key);
            (back || (back = {}))[rec.props[j]] = v === undefined ? null : v;
            pcnt.delete(key); pbase.delete(key);
            if (rec.props[j] === 'parent') pmove.delete(op.id);
          } else pcnt.set(key, c - 1);              /* a later local write is still waiting: it stays on screen */
        }
        if (!back) continue;
        n = nodes.get(op.id);
        /* the node is not here. Fine when it sits in something we deleted and the server has it there too;
           not fine when the rejected op was the very move that took it there. */
        if (!n) { if (!pdel.has(op.id) || hasOwn.call(op.p, 'parent')) desync = true; continue; }
        if (hasOwn.call(back, 'parent') && back.parent !== n.parent && !okParent(op.id, back.parent)) {
          desync = true;
          delete back.parent; delete back.idx;
        }
        r = rawSet(op.id, n, back);
        if (r) chSet(ch, op.id, r[0]);
      }
    }
    finish(ch, desync);
  };

  /* where the SERVER has x right now: an un-acked local move does not count yet */
  function serverParent(x) {
    var key = x + '\nparent';
    if (pcnt.has(key)) return pbase.get(key);
    var n = nodes.get(x);
    return n ? n.parent : undefined;
  }
  /* a remote delete of `id`: nodes we moved OUT of it (not acked yet) were still inside it on the server, so
     they are gone too. Returns true when that can not be worked out here (ask for a reload). */
  function remoteDelMoved(id, ch) {
    var extra = null, unsure = false;
    pmove.forEach(function (m) {
      if (m === id || !nodes.has(m)) return;
      var c = serverParent(m), guard = 0;
      while (c !== undefined && ++guard < 100000) {
        if (c === id) { (extra || (extra = [])).push(m); return; }
        if (!nodes.has(c)) { unsure = true; return; }       /* its old home is something we deleted ourselves */
        c = serverParent(c);
      }
    });
    if (extra) {
      for (var i = 0; i < extra.length; i++) {
        if (!nodes.has(extra[i])) continue;
        var gone = rawDelete(extra[i]);
        if (movedIn(gone, 1)) unsure = true;
        chDel(ch, gone);
      }
    }
    return unsure;
  }
  /* a subtree was just removed here because the server removed it. A node inside that WE moved in (not acked
     yet) was somewhere else on the server and may well be alive there: that needs a reload. */
  function movedIn(list, from) {
    for (var i = from; i < list.length; i++) if (pmove.has(list[i][0])) return true;
    return false;
  }

  store.applyRemote = function (ops) {
    if (!isArr(ops)) return;
    var ch = newChange(), desync = false, i, op, id, p, n, k, key, use, r, gone, guard = tracking && (pcnt.size || pdel.size);
    for (i = 0; i < ops.length; i++) {
      op = ops[i];
      if (!op || typeof op.id !== 'string') continue;
      id = op.id;
      if (op.del) {
        if (id === ROOT) continue;
        if (guard && pcnt.has(id + '\ntype')) { desync = true; continue; }   /* we are (re)making this very node */
        if (guard && pmove.size && remoteDelMoved(id, ch)) desync = true;
        if (nodes.has(id)) {
          gone = rawDelete(id);
          if (guard && pmove.size && movedIn(gone, 1)) desync = true;
          chDel(ch, gone);
        }
        continue;
      }
      p = op.p;
      if (!p || typeof p !== 'object') continue;
      if (guard && (pdel.has(id) || pghost.has(id))) {
        /* we deleted it and the server will too - unless this op carries it out of what we deleted */
        if (typeof p.parent === 'string' && !pdel.has(p.parent) && !pghost.has(p.parent)) desync = true;
        continue;
      }
      n = nodes.get(id);
      if (n) {
        use = p;
        if (guard && pcnt.size) {
          use = null;
          for (k in p) {
            key = id + '\n' + k;
            if (pcnt.has(key)) {                        /* ours is on its way: skip, remember */
              pbase.set(key, p[k] === null ? undefined : p[k]);
              /* on the server it now sits in something we are deleting; whether our own move saves it depends
                 on which of our two edits lands first */
              if (k === 'parent' && (pdel.has(p[k]) || pghost.has(p[k]))) desync = true;
            } else (use || (use = {}))[k] = p[k];
          }
          if (!use) continue;
        }
        if (use.parent !== undefined && use.parent !== n.parent) {
          if (guard && (pdel.has(use.parent) || pghost.has(use.parent))) {
            gone = rawDelete(id);                      /* moved into something we deleted: it goes with it */
            if (pmove.size && movedIn(gone, 1)) desync = true;
            for (k = 0; k < gone.length; k++) pghost.add(gone[k][0]);
            chDel(ch, gone);
            continue;
          }
          if (!okParent(id, use.parent)) {
            if (use.parent !== null && id !== ROOT) desync = true;
            use = Object.assign({}, use);
            delete use.parent; delete use.idx;
          }
        }
        r = rawSet(id, n, use);
        if (r) chSet(ch, id, r[0]);
      } else if (p.type !== undefined) {
        if (!hasOwn.call(DEF, p.type) || id === ROOT) continue;
        if (guard && (pdel.has(p.parent) || pghost.has(p.parent))) { pghost.add(id); continue; }   /* born inside what we deleted */
        if (!nodes.has(p.parent)) { desync = true; continue; }
        if (guard && pcnt.size) {                     /* an edit of ours for this id is still on its way */
          for (k in p) { key = id + '\n' + k; if (pcnt.has(key)) pbase.set(key, p[k] === null ? undefined : p[k]); }
        }
        rawCreate(id, cleanCopy(p));
        ch.ids.add(id); ch.structural = true;
      }
    }
    finish(ch, desync);
  };

  /* ================================================================ load */
  /* load(doc, cid)               a new document: undo and pending are forgotten
     load(doc, cid, {keep:true})  the same file again after a reconnect: undo is kept, pending batches are put back on top */
  store.load = function (doc, newCid, opts) {
    var keep = !!(opts && opts.keep), src = doc && doc.nodes ? doc.nodes : {}, id, n, k;
    if (depth > 0) { cur = null; depth = 0; }
    nodes = new Map(); kidSet = new Map(); sorted = new Map(); tail = new Map();
    lm = new Map(); wm = new Map(); wb = new Map(); sb = new Map();
    nameN = new Map();
    newCid = (newCid === undefined || newCid === null) ? 0 : newCid;
    if (!(keep && newCid === cid)) counter = 0;      /* same client number again: ids of waiting edits stay taken */
    cid = newCid;
    var pre = cid + ':', pl = pre.length, ks;
    for (id in src) {
      n = src[id];
      if (!n || typeof n !== 'object' || typeof n.type !== 'string') continue;
      nodes.set(id, n);
      k = n.parent;
      if (k !== undefined && k !== null && id !== ROOT) {
        ks = kidSet.get(k);
        if (!ks) { ks = new Set(); kidSet.set(k, ks); }
        ks.add(id);
      } else if (k === null) delete n.parent;
      if (id.length > pl && id.charCodeAt(0) === pre.charCodeAt(0) && id.slice(0, pl) === pre) {
        var num = +id.slice(pl);
        if (num > counter) counter = num;
      }
    }
    if (!nodes.has(ROOT)) nodes.set(ROOT, {type: 'DOCUMENT', name: 'Document'});
    if (!keep) {
      undoS = []; redoS = []; gKey = null;
      clearPending();
    } else if (tracking && pendQ.length) reapply();
    else clearPending();
    sel._load();
    em.emit('load', {keep: keep});
  };
  /* put the still-pending local batches back on top of a fresh document and rebuild the pending marks.
     An op that does not fit the fresh document (its node is gone) is not applied but STAYS pending: net sends it
     again, and what happens to it is settled when its answer comes (see acked / rollback). */
  function reapply() {
    var i, j, rec, op, k, key, r, list, n, c;
    pcnt.clear(); pbase.clear(); pdel.clear(); pghost.clear(); pmove.clear();
    for (i = 0; i < pendQ.length; i++) {
      var recs = pendQ[i].recs;
      for (j = 0; j < recs.length; j++) {
        rec = recs[j]; op = rec.op;
        rec.keys = null; rec.props = null; rec.ids = null; rec.live = false;
        if (rec.done) continue;
        rec.live = true;
        if (op.del) {
          rec.kind = 'del';
          list = op.id !== ROOT && nodes.has(op.id) ? rawDelete(op.id) : [];
          rec.snap = new Array(list.length); rec.ids = new Array(list.length);
          for (k = 0; k < list.length; k++) {
            rec.snap[k] = {id: list[k][0], p: list[k][1]};
            rec.ids[k] = list[k][0];
          }
          if (!list.length) rec.ids = [op.id];         /* not there now; should it come back before our delete lands, it is doomed */
          for (k = 0; k < rec.ids.length; k++) pdel.set(rec.ids[k], (pdel.get(rec.ids[k]) || 0) + 1);
          continue;
        }
        n = nodes.get(op.id);
        var before = n ? Object.assign({}, n) : null;
        r = rawOp({id: op.id, p: op.p});
        rec.kind = (r && r.create) || (!n && op.p.type !== undefined) ? 'create' : 'set';
        rec.keys = []; rec.props = [];
        for (k in op.p) {
          key = op.id + '\n' + k;
          c = pcnt.get(key);
          if (c === undefined) { pbase.set(key, before ? before[k] : undefined); pcnt.set(key, 1); }
          else pcnt.set(key, c + 1);
          rec.keys.push(key); rec.props.push(k);
          if (k === 'parent') pmove.add(op.id);
        }
      }
    }
  }

  /* ================================================================ HD.sel */
  var sem = new Emitter(), selSet = new Set();
  sel = HD.sel = {ids: EMPTY, page: null};
  function selEmit() { sem.emit('change', {ids: sel.ids, page: sel.page}); }
  function selWrite(arr) {
    sel.ids = arr.length ? Object.freeze(arr) : EMPTY;
    selSet = new Set(arr);
  }
  sel.set = function (ids) {
    var arr = [], seen = new Set(), src = toArr(ids), i;
    for (i = 0; i < src.length; i++) {
      if (typeof src[i] !== 'string' || seen.has(src[i]) || !nodes.has(src[i])) continue;
      seen.add(src[i]); arr.push(src[i]);
    }
    if (arr.length === sel.ids.length) {
      for (i = 0; i < arr.length; i++) if (arr[i] !== sel.ids[i]) break;
      if (i === arr.length) return false;
    }
    selWrite(arr);
    selEmit();
    return true;
  };
  sel.add = function (id) { return selSet.has(id) ? false : sel.set(sel.ids.concat(toArr(id))); };
  sel.remove = function (id) { return selSet.has(id) ? sel.set(sel.ids.filter(function (x) { return x !== id; })) : false; };
  sel.toggle = function (id) { return selSet.has(id) ? sel.remove(id) : sel.add(id); };
  sel.clear = function () { return sel.set([]); };
  sel.has = function (id) { return selSet.has(id); };
  sel.on = function (evt, fn) { return sem.on(evt, fn); };
  sel.off = function (evt, fn) { sem.off(evt, fn); };
  sel.setPage = function (id) {
    var n = nodes.get(id);
    if (!n || n.type !== 'PAGE') return false;
    if (id === sel.page) return false;
    sel.page = id;
    selWrite([]);
    selEmit();
    return true;
  };
  function firstPage() { var ps = store.pages(); return ps.length ? ps[0] : null; }
  sel._drop = function (removed) {
    var changed = false, arr = sel.ids;
    for (var i = 0; i < arr.length; i++) if (removed.has(arr[i])) { changed = true; break; }
    if (changed) selWrite(arr.filter(function (id) { return !removed.has(id); }));
    if (sel.page !== null && removed.has(sel.page)) { sel.page = firstPage(); if (!changed) selWrite([]); changed = true; }
    if (changed) selEmit();
  };
  sel._load = function () {
    var n = sel.page !== null ? nodes.get(sel.page) : null;
    if (!n || n.type !== 'PAGE') sel.page = firstPage();
    selWrite(sel.ids.filter(function (id) { return nodes.has(id); }));
    selEmit();
  };

  /* start with an empty document, so every call works before the first load */
  nodes.set(ROOT, {type: 'DOCUMENT', name: 'Document'});
})();
