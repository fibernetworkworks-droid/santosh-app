/* HOOLA DESIGN - browser walk of the editor shell, tools and panels (hd-tools.js, hd-ui.js, hd-app.js) against the
   REAL hd-math / hd-core / hd-net / hd-layout / hd-render, with a small mock of the server: the REST routes of
   docs/HOOLA_DESIGN_PLAN.md and a one-file WebSocket room (hand-written frames, no dependency).
   Run:  node server/tests/web/design_ui_test.js        (DESIGN_SHOTS=<dir> also writes screenshots)
   It draws with the mouse, moves / resizes / rotates, types text, edits a fill in the panel, groups, reorders in the
   layers list and undoes - asserting on HD.store - and checks that no control overlaps or is clipped at
   1280x800 and 1440x900, in light and in dark. */
'use strict';
const http = require('http'), fs = require('fs'), path = require('path'), crypto = require('crypto'), assert = require('node:assert/strict');
const STATIC = path.resolve(__dirname, '../../app/static');
const MIME = {'.js': 'application/javascript', '.css': 'text/css', '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json'};
const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'";

function wsFrame(text) {
  const p = Buffer.from(text, 'utf8'), n = p.length; let head;
  if (n < 126) head = Buffer.from([0x81, n]); else if (n < 65536) { head = Buffer.alloc(4); head[0] = 0x81; head[1] = 126; head.writeUInt16BE(n, 2); } else { head = Buffer.alloc(10); head[0] = 0x81; head[1] = 127; head.writeBigUInt64BE(BigInt(n), 2); }
  return Buffer.concat([head, p]);
}
function wsReader(onText, onClose) {
  let buf = Buffer.alloc(0), parts = [];
  return chunk => {
    buf = Buffer.concat([buf, chunk]);
    for (;;) {
      if (buf.length < 2) return; const fin = !!(buf[0] & 0x80), op = buf[0] & 0x0f, masked = !!(buf[1] & 0x80); let len = buf[1] & 0x7f, off = 2;
      if (len === 126) { if (buf.length < 4) return; len = buf.readUInt16BE(2); off = 4; } else if (len === 127) { if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); off = 10; }
      const need = off + (masked ? 4 : 0) + len; if (buf.length < need) return;
      let data = buf.subarray(off + (masked ? 4 : 0), need);
      if (masked) { const mask = buf.subarray(off, off + 4), out = Buffer.alloc(len); for (let i = 0; i < len; i++) out[i] = data[i] ^ mask[i & 3]; data = out; }
      buf = buf.subarray(need);
      if (op === 8) { onClose(); return; }
      if (op === 0 || op === 1) { parts.push(data); if (fin) { const t = Buffer.concat(parts).toString('utf8'); parts = []; onText(t); } }
    }
  };
}
function newDoc() { return {nodes: {'0:0': {type: 'DOCUMENT', name: 'Document'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a0', name: 'Page 1'}}}; }

/* the mock: {port, files, rooms, close(), inject(fileId, frame), opsLog} */
function startMock(seedDoc) {
  const files = new Map(), rooms = new Map(), assets = new Map(), log = {ops: [], rest: []}; let nextCid = 1, nextFile = 1;
  const row = f => ({id: f.id, name: f.name, star: f.star, trashed: !!f.trashed_at, trashed_at: f.trashed_at, nodes: Object.keys(f.doc.nodes).length, seq: f.seq, thumb_at: f.thumb ? f.thumb_at : null, created_at: f.created_at, updated_at: f.updated_at});
  const make = (name, doc) => { const now = new Date().toISOString(), f = {id: 'f' + (nextFile++), name: name || 'Untitled', star: false, trashed_at: null, doc: doc || newDoc(), seq: 0, thumb: null, thumb_at: null, created_at: now, updated_at: now}; files.set(f.id, f); return f; };
  make('Shop poster', seedDoc);
  const server = http.createServer((req, res) => {
    const u = new URL(req.url, 'http://localhost'), p = u.pathname;
    const json = (o, code) => { res.writeHead(code || 200, {'Content-Type': 'application/json', 'Cache-Control': 'no-store'}); res.end(JSON.stringify(o)); };
    if (p.startsWith('/api/design/')) {
      const chunks = []; req.on('data', c => chunks.push(c)); req.on('end', () => {
        const raw = Buffer.concat(chunks), seg = p.slice('/api/design/'.length).split('/'), body = () => { try { return JSON.parse(raw.toString('utf8') || '{}'); } catch (e) { return {}; } };
        if ((req.headers.authorization || '') !== 'Bearer fixture-only') return json({detail: 'Not signed in'}, 401);
        log.rest.push(req.method + ' ' + p);
        if (seg[0] === 'files' && seg.length === 1) { if (req.method === 'POST') return json(row(make(body().name)));
          const q = (u.searchParams.get('q') || '').toLowerCase(), trash = u.searchParams.get('trash') === '1'; return json({files: Array.from(files.values()).filter(f => !!f.trashed_at === trash && f.name.toLowerCase().includes(q)).sort((a, b) => (b.star - a.star) || (a.updated_at < b.updated_at ? 1 : -1)).map(row)}); }
        if (seg[0] === 'assets' && seg[1]) { const a = assets.get(seg[1]); if (!a) return json({detail: 'Not found'}, 404); res.writeHead(200, {'Content-Type': a.type}); return res.end(a.data); }
        const f = files.get(seg[1]); if (seg[0] !== 'files' || !f) return json({detail: 'File not found'}, 404);
        if (seg.length === 2) { if (req.method === 'GET') return json(row(f)); if (req.method === 'PATCH') { const b = body(); if (b.name !== undefined) { f.name = String(b.name); const r = rooms.get(f.id); if (r) for (const c of r.clients) c.send({t: 'file', name: f.name}); } if (b.star !== undefined) f.star = !!b.star; return json(row(f)); }
          if (req.method === 'DELETE') { if (u.searchParams.get('forever')) { files.delete(f.id); return json({ok: true, deleted: true}); } f.trashed_at = new Date().toISOString(); return json({ok: true, trashed: true, file: row(f)}); } }
        if (seg[2] === 'restore') { f.trashed_at = null; return json(row(f)); }
        if (seg[2] === 'duplicate') return json(row(make(f.name + ' copy', JSON.parse(JSON.stringify(f.doc)))));
        if (seg[2] === 'doc') return json({seq: f.seq, doc: f.doc});
        if (seg[2] === 'thumb') { if (req.method === 'PUT') { f.thumb = raw; f.thumb_at = new Date().toISOString(); return json({ok: true, thumb_at: f.thumb_at}); } if (!f.thumb) return json({detail: 'No thumbnail'}, 404); res.writeHead(200, {'Content-Type': 'image/png'}); return res.end(f.thumb); }
        if (seg[2] === 'assets' && req.method === 'POST') { const hash = crypto.createHash('sha256').update(raw).digest('hex'); assets.set(hash, {data: raw, type: req.headers['content-type'] || 'image/png'}); return json({hash: hash}); }
        return json({detail: 'Not found'}, 404);
      }); return;
    }
    let file = null;
    if (p === '/console/design' || p === '/console/design/') file = path.join(STATIC, 'console/design/design.html');
    else if (p.startsWith('/static/')) file = path.join(STATIC, p.slice(8));
    else if (p === '/console/' || p === '/console') { res.writeHead(200, {'Content-Type': 'text/html'}); return res.end('<!doctype html><title>Console</title><p id="console-stub">Console</p>'); }
    if (!file || !file.startsWith(STATIC) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    const head = {'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store'}; if (file.endsWith('.html')) head['Content-Security-Policy'] = CSP;
    res.writeHead(200, head); res.end(fs.readFileSync(file));
  });
  const socks = new Set();
  server.on('upgrade', (req, socket) => {
    if (server.down) { socket.destroy(); return; }
    socks.add(socket); socket.on('close', () => socks.delete(socket)); socket.on('error', () => {});
    const u = new URL(req.url, 'http://localhost'), f = files.get(u.searchParams.get('file')), protos = String(req.headers['sec-websocket-protocol'] || '').split(',').map(s => s.trim());
    const accept = crypto.createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + '\r\n' + (protos.includes('hoola') ? 'Sec-WebSocket-Protocol: hoola\r\n' : '') + '\r\n');
    const closeWith = code => { const b = Buffer.alloc(4); b[0] = 0x88; b[1] = 2; b.writeUInt16BE(code, 2); try { socket.write(b); socket.end(); } catch (e) { /* gone */ } };
    if (!protos.includes('hoola-key.fixture-only')) return closeWith(4401); if (u.pathname !== '/api/design/ws' || !f || f.trashed_at) return closeWith(4404);
    let room = rooms.get(f.id); if (!room) { room = {clients: new Set(), ghosts: []}; rooms.set(f.id, room); }
    const me = {cid: nextCid++, name: 'Meghana', color: '#5B45E0', send: o => { try { socket.write(wsFrame(JSON.stringify(o))); } catch (e) { /* gone */ } }};
    const role = server.viewOnly ? 'view' : 'edit';
    me.send({t: 'init', cid: me.cid, seq: f.seq, doc: f.doc, file: {id: f.id, name: f.name, role: role}, users: Array.from(room.clients).map(c => ({cid: c.cid, name: c.name, color: c.color})).concat(room.ghosts)});
    for (const c of room.clients) c.send({t: 'join', user: {cid: me.cid, name: me.name, color: me.color}}); room.clients.add(me);
    const gone = () => { if (!room.clients.delete(me)) return; for (const c of room.clients) c.send({t: 'leave', cid: me.cid}); };
    socket.on('data', wsReader(text => { let m; try { m = JSON.parse(text); } catch (e) { return; }
      if (m.t === 'ping') return me.send({t: 'pong'});
      if (m.t === 'pres') { for (const c of room.clients) if (c !== me) c.send(Object.assign({}, m, {cid: me.cid})); return; }
      if (m.t === 'ops') { const rejected = [], ok = [];
        (m.ops || []).forEach((op, i) => { if (role === 'view') { rejected.push(i); return; } const nodes = f.doc.nodes;
          if (op.del) { const kill = id => { for (const k in nodes) if (nodes[k].parent === id) kill(k); delete nodes[id]; }; if (op.id === '0:0') { rejected.push(i); return; } kill(op.id); ok.push(op); return; }
          let n = nodes[op.id]; if (!n) { if (!op.p || !op.p.type) return; if (!nodes[op.p.parent]) { rejected.push(i); return; } n = nodes[op.id] = {}; }
          for (const k in op.p) { if (op.p[k] === null) delete n[k]; else n[k] = op.p[k]; } ok.push(op); });
        f.seq++; f.updated_at = new Date().toISOString(); log.ops.push(ok); me.send({t: 'ack', n: m.n, seq: f.seq, rejected: rejected}); for (const c of room.clients) if (c !== me) c.send({t: 'ops', seq: f.seq, by: me.cid, ops: ok}); } }, gone));
    socket.on('close', gone); socket.on('error', gone);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve({port: server.address().port, files: files, rooms: rooms, log: log, server: server, close: () => new Promise(r => { for (const so of socks) { try { so.destroy(); } catch (e) { /* gone */ } } if (server.closeAllConnections) server.closeAllConnections(); const t = setTimeout(r, 1500); server.close(() => { clearTimeout(t); r(); }); }),
    /* the connection drops (and stays down until down(false)) */
    down(on) { server.down = on; if (on) for (const so of socks) { try { so.destroy(); } catch (e) { /* gone */ } } },
    /* a second person in the room, driven by the test */
    ghost(fileId, user, pres) { const room = rooms.get(fileId); if (!room) return; room.ghosts.push(user); for (const c of room.clients) { c.send({t: 'join', user: user}); if (pres) c.send(Object.assign({t: 'pres', cid: user.cid}, pres)); } }})));
}

/* ---------------------------------------------------------------- the walk */
function seed() {
  const doc = newDoc(), solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}];
  Object.assign(doc.nodes, {
    '9:1': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Phone', x: 0, y: 0, w: 390, h: 844, fills: solid('#FFFFFF')},
    '9:2': {type: 'RECT', parent: '9:1', idx: 'a0', name: 'Hero', x: 24, y: 60, w: 342, h: 200, radius: 20, fills: [{type: 'linear', stops: [{pos: 0, color: '#6E55F0', opacity: 1}, {pos: 1, color: '#EE8F35', opacity: 1}], from: [0, 0], to: [1, 1], opacity: 1, visible: true}]},
    '9:3': {type: 'ELLIPSE', parent: '9:1', idx: 'a1', name: 'Badge', x: 270, y: 300, w: 80, h: 80, fills: solid('#EE8F35')},
    '9:5': {type: 'RECT', parent: '0:1', idx: 'a1', name: 'Card', x: 480, y: 80, w: 220, h: 140, radius: 12, fills: solid('#D9D9D9'), strokes: solid('#1A1A1F'), effects: [{type: 'drop', x: 0, y: 4, blur: 12, spread: 0, color: '#000000', opacity: 0.25, visible: true}]}
  });
  return doc;
}
/* runs in the page: everything that overlaps, is cut off or breaks the type rules */
function layoutProblems() {
  const vw = innerWidth, vh = innerHeight, bad = [];
  const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const desc = el => (el.tagName.toLowerCase() + '.' + String(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className).split(' ').join('.') + ' "' + (el.getAttribute('aria-label') || el.title || el.textContent || '').trim().slice(0, 30) + '"');
  const cut = (a, b) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
  const ctrls = Array.from(document.querySelectorAll('.hd-top button, .hd-top .hd-status, .hd-tabs button, .hd-left button, .hd-right button, .hd-right input, .hd-right select, .hd-pop button, .hd-pop input')).filter(vis);
  for (const el of ctrls) { const r = el.getBoundingClientRect(); if (r.left < -0.5 || r.right > vw + 0.5 || r.top < -0.5) bad.push('outside the window: ' + desc(el));
    const box = el.closest('.hd-right, .hd-left, .hd-top, .hd-pop'); if (box) { const b = box.getBoundingClientRect(); if (r.left < b.left - 0.5 || r.right > b.right + 0.5) bad.push('cut off by its panel: ' + desc(el)); }
    if (r.width < 14 || r.height < 14) bad.push('too small to hit: ' + desc(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
  const groups = [Array.from(document.querySelectorAll('.hd-top-l > *, .hd-toolbar, .hd-top-r > *'))];
  for (const row of document.querySelectorAll('.hd-row, .hd-paint, .hd-alignrow, .hd-shead, .hd-selhead, .hd-tabs, .hd-toolbar, .hd-lrow, .hd-prow')) groups.push(Array.from(row.children));
  for (const g of groups) { const list = g.filter(vis).map(el => [el, el.getBoundingClientRect()]); for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) if (cut(list[i][1], list[j][1])) bad.push('overlap: ' + desc(list[i][0]) + ' and ' + desc(list[j][0])); }
  for (const p of document.querySelectorAll('.hd-top, .hd-left, .hd-right, .hd-stage')) { if (!vis(p)) continue; const r = p.getBoundingClientRect(); if (r.right > vw + 0.5 || r.bottom > vh + 0.5 || r.left < -0.5) bad.push('panel outside the window: ' + desc(p)); }
  const shell = ['.hd-top', '.hd-left', '.hd-stage', '.hd-right'].map(q => document.querySelector(q)).filter(el => el && vis(el)).map(el => [el, el.getBoundingClientRect()]);
  for (let i = 0; i < shell.length; i++) for (let j = i + 1; j < shell.length; j++) if (cut(shell[i][1], shell[j][1])) bad.push('shell overlap: ' + desc(shell[i][0]) + ' and ' + desc(shell[j][0]));
  for (const el of document.querySelectorAll('.hd-editor *, .hd-pop *')) { if (!vis(el) || !el.firstChild || el.firstChild.nodeType !== 3 || !el.textContent.trim()) continue; const cs = getComputedStyle(el);
    if (parseFloat(cs.fontSize) < 12) bad.push('text under 12px: ' + desc(el) + ' ' + cs.fontSize); if (Number(cs.fontWeight) > 600) bad.push('weight over 600: ' + desc(el)); if (cs.textTransform === 'uppercase') bad.push('all caps: ' + desc(el)); }
  for (const el of document.querySelectorAll('.hd-stitle, .hd-selname, .hd-tab, .hd-btn-t, .hd-check span')) { if (vis(el) && el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).textOverflow !== 'ellipsis') bad.push('text cut off: ' + desc(el)); }
  return bad;
}
async function walk() {
  const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  const stub = process.env.HD_RENDER_STUB || '', dir = path.join(STATIC, 'console/design');
  for (const f of ['hd-math.js', 'hd-core.js', 'hd-net.js', 'hd-layout.js', 'hd-tools.js', 'hd-ui.js', 'hd-app.js', 'design.html', 'design.css'].concat(stub ? [] : ['hd-render.js'])) assert.ok(fs.existsSync(path.join(dir, f)), 'missing ' + f);
  const mock = await startMock(seed());
  const browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']});
  const errors = [];
  async function newPage(viewport, scheme) {
    const page = await browser.newPage({viewport: viewport, colorScheme: scheme || 'light'});
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
    if (stub) await page.route('**/hd-render.js*', r => r.fulfill({contentType: 'application/javascript', body: fs.readFileSync(stub, 'utf8')}));
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(() => localStorage.setItem('hoola.console.token', 'fixture-only'));
    return page;
  }
  const base = 'http://127.0.0.1:' + mock.port + '/console/design';
  const mounted = page => page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0, null, {timeout: 20000});
  /* wait until the picture is at rest: the view (a zoom can be animated) and the panels have stopped changing */
  const settle = page => page.evaluate(() => new Promise(done => { let last = '', same = 0, n = 0; const tick = () => { const v = window.HD && HD.render && HD.render.view ? [HD.render.view.x, HD.render.view.y, HD.render.view.zoom].join() : ''; same = v === last ? same + 1 : 0; last = v; if (same >= 3 || ++n > 90) setTimeout(done, 30); else requestAnimationFrame(tick); }; requestAnimationFrame(tick); }));
  const shot = async (page, name) => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };
  try {
    /* ---- your files ---- */
    const page = await newPage({width: 1440, height: 900});
    await page.goto(base); await page.locator('.hd-card').first().waitFor();
    assert.equal(await page.locator('.hd-cname').first().textContent(), 'Shop poster');
    assert.ok(await page.locator('.hd-newcard').isVisible(), 'the New design file tile');
    await page.locator('.hd-hsearch input').fill('zzz'); await page.locator('.hd-empty h2').waitFor(); assert.match(await page.locator('.hd-empty h2').textContent(), /Nothing called/);
    await page.locator('.hd-hsearch input').fill(''); await page.locator('.hd-card').first().waitFor(); await shot(page, 'files-light');
    await page.locator('.hd-cstar').first().click({force: true}); await page.waitForFunction(() => document.querySelector('.hd-cstar.on'));
    assert.equal(mock.files.get('f1').star, true, 'the star reached the server');
    await page.locator('.hd-open').first().click();

    /* ---- the editor opens on the live room ---- */
    await mounted(page); await settle(page);
    const ev = (fn, arg) => page.evaluate(fn, arg);
    const pt = async (wx, wy) => page.evaluate(([x, y]) => { const s = HD.render.worldToScreen(x, y), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; }, [wx, wy]);
    const dragW = async (a, b, o) => { const p = await pt(a[0], a[1]), q = await pt(b[0], b[1]); await page.mouse.move(p[0], p[1]); await page.mouse.down(); await page.mouse.move((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, {steps: 4}); await page.mouse.move(q[0], q[1], {steps: 6}); if (o && o.hold) await o.hold(); await page.mouse.up(); await settle(page); };
    const node = id => page.evaluate(i => { const n = HD.store.get(i); return n ? JSON.parse(JSON.stringify(Object.assign({}, n, {w: HD.store.prop(i, 'w'), h: HD.store.prop(i, 'h'), x: HD.store.prop(i, 'x'), y: HD.store.prop(i, 'y'), rot: HD.store.prop(i, 'rot')}))) : null; }, id);
    const near = (a, b, tol, what) => assert.ok(Math.abs(a - b) <= (tol || 1), what + ': ' + a + ' is not ' + b);
    assert.equal(await page.locator('.hd-fname-t').textContent(), 'Shop poster');
    assert.equal(await ev(() => HD.app.file.role), 'edit');
    assert.deepEqual(await page.locator('.hd-lrow .hd-lname').allTextContents(), ['Card', 'Phone'], 'layers: top layer first');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with nothing selected');
    await shot(page, 'editor-empty-selection');

    /* ---- draw a rectangle with the mouse ---- */
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('r'); assert.equal(await ev(() => HD.tools.current), 'rect');
    assert.equal(await page.locator('.hd-tool.on').getAttribute('data-tool'), 'rect');
    const before = await ev(() => HD.store.children(HD.sel.page).length);
    await dragW([480, 300], [680, 400]);
    assert.equal(await ev(() => HD.store.children(HD.sel.page).length), before + 1, 'one new layer');
    assert.equal(await ev(() => HD.tools.current), 'move', 'back to the move tool');
    const rid = await ev(() => HD.sel.ids[0]); let r = await node(rid);
    assert.equal(r.type, 'RECT'); near(r.x, 480, 1, 'x'); near(r.y, 300, 1, 'y'); near(r.w, 200, 1.5, 'w'); near(r.h, 100, 1.5, 'h'); assert.match(r.name, /^Rectangle/);
    await shot(page, 'drawn-rect');

    /* ---- move, resize, rotate ---- */
    const undo0 = r;
    await dragW([r.x + r.w / 2, r.y + r.h / 2], [r.x + r.w / 2 + 60, r.y + r.h / 2 + 40]); let m = await node(rid);
    near(m.x, r.x + 60, 1.5, 'moved x'); near(m.y, r.y + 40, 1.5, 'moved y'); near(m.w, r.w, 0.01, 'size kept');
    await dragW([m.x + m.w, m.y + m.h], [m.x + m.w + 40, m.y + m.h + 20]); let z = await node(rid);
    near(z.w, m.w + 40, 2, 'resized w'); near(z.h, m.h + 20, 2, 'resized h'); near(z.x, m.x, 0.01, 'the opposite corner stays');
    const c = await pt(z.x + z.w, z.y), ctr = await pt(z.x + z.w / 2, z.y + z.h / 2);
    await page.mouse.move(c[0] + 12, c[1] - 12); await page.mouse.down(); await page.keyboard.down('Shift'); await page.mouse.move(c[0] + 40, c[1] + 30, {steps: 5}); await page.mouse.move(ctr[0] + 160, ctr[1] + 150, {steps: 5}); await page.mouse.up(); await page.keyboard.up('Shift'); await settle(page);
    let ro = await node(rid); assert.ok(Math.abs(ro.rot) >= 15, 'rotated: ' + ro.rot); near(Math.round(ro.rot / 15) * 15, ro.rot, 0.01, 'shift snaps to 15 degrees');
    near(ro.x + ro.w / 2, z.x + z.w / 2, 0.6, 'rotates about its centre');
    await page.keyboard.press('Control+z'); await settle(page); near((await node(rid)).rot, 0, 0.001, 'ONE undo takes the whole rotation back');
    await page.keyboard.press('Control+z'); await settle(page); near((await node(rid)).w, m.w, 0.01, 'undo the resize');
    await page.keyboard.press('Control+Shift+z'); await settle(page); near((await node(rid)).w, z.w, 0.01, 'redo the resize');
    await page.keyboard.press('ArrowRight'); await page.keyboard.press('Shift+ArrowDown'); await settle(page); let k = await node(rid); near(k.x, z.x + 1, 0.01, 'arrow nudges 1'); near(k.y, z.y + 10, 0.01, 'shift arrow nudges 10');

    /* ---- type text (Hindi too) ---- */
    await page.keyboard.press('t'); assert.equal(await ev(() => HD.tools.current), 'text');
    const tp = await pt(480, 560); await page.mouse.click(tp[0], tp[1]); await page.locator('.hd-textedit').waitFor();
    await page.keyboard.type('Namaste नमस्ते'); await shot(page, 'typing'); await page.keyboard.press('Escape'); await settle(page);
    const tid = await ev(() => HD.sel.ids[0]); const tx = await node(tid);
    assert.equal(tx.type, 'TEXT'); assert.equal(tx.chars, 'Namaste नमस्ते'); near(tx.x, 480, 1, 'text x'); assert.ok(tx.w > 20, 'the layout engine sized the text: ' + tx.w);
    assert.equal(await page.locator('.hd-textedit').count(), 0, 'the editor closed');
    /* edit it again in place */
    const tc = await pt(tx.x + 10, tx.y + tx.h / 2); await page.mouse.dblclick(tc[0], tc[1]); await page.locator('.hd-textedit').waitFor(); await page.keyboard.press('End'); await page.keyboard.type('!'); await page.keyboard.press('Escape'); await settle(page);
    assert.equal((await node(tid)).chars, 'Namaste नमस्ते!');

    /* ---- the Design panel: fill, number maths, colour picker ---- */
    const rc = await pt(k.x + k.w / 2, k.y + k.h / 2); await page.mouse.click(rc[0], rc[1]); await settle(page); assert.deepEqual(await ev(() => HD.sel.ids.slice()), [rid]);
    const hex = page.locator('.hd-right .hd-sec[aria-label="Fill"] .hd-hex'); await hex.fill('FF0000'); await hex.press('Enter'); await settle(page);
    assert.equal((await node(rid)).fills[0].color, '#FF0000');
    const wIn = page.locator('.hd-right input[aria-label="Width"]'); await wIn.fill('100+20'); await wIn.press('Enter'); await settle(page); near((await node(rid)).w, 120, 0.01, 'maths in a number box');
    await wIn.fill('50%'); await wIn.press('Enter'); await settle(page); near((await node(rid)).w, 60, 0.01, 'percent of the current value');
    await wIn.press('Shift+ArrowUp'); await settle(page); near((await node(rid)).w, 70, 0.01, 'shift + arrow = 10');
    await page.locator('.hd-right input[aria-label="Corner radius"]').fill('12'); await page.keyboard.press('Enter'); await settle(page); assert.equal((await node(rid)).radius, 12);
    await page.locator('.hd-right .hd-sec[aria-label="Fill"] .hd-sw.big').click(); await page.locator('.hd-picker').waitFor();
    assert.deepEqual(await ev(layoutProblems), [], 'layout with the colour picker open');
    await shot(page, 'picker-light');
    const svb = await page.locator('.hd-sv').boundingBox(); await page.mouse.move(svb.x + svb.width * 0.5, svb.y + svb.height * 0.5); await page.mouse.down(); await page.mouse.move(svb.x + svb.width * 0.8, svb.y + svb.height * 0.25, {steps: 4}); await page.mouse.up(); await settle(page);
    const picked = (await node(rid)).fills[0].color; assert.notEqual(picked, '#FF0000', 'the square changed the colour'); assert.match(picked, /^#[0-9A-F]{6}$/);
    await page.locator('.hd-ptypes [data-v="linear"]').click(); await settle(page); assert.equal((await node(rid)).fills[0].type, 'linear'); assert.equal((await node(rid)).fills[0].stops.length, 2);
    await page.locator('.hd-ptypes [data-v="solid"]').click(); await settle(page); assert.equal((await node(rid)).fills[0].type, 'solid');
    await page.keyboard.press('Escape'); assert.equal(await page.locator('.hd-picker').count(), 0);
    await page.locator('.hd-right .hd-sec[aria-label="Stroke"] button[aria-label^="Add"]').click(); await settle(page); assert.equal((await node(rid)).strokes.length, 1);
    await page.locator('.hd-right .hd-sec[aria-label="Effects"] button[aria-label^="Add"]').click(); await settle(page); assert.equal((await node(rid)).effects[0].type, 'drop');
    await page.locator('.hd-right input[aria-label="Opacity"]').fill('50'); await page.keyboard.press('Enter'); await settle(page); near((await node(rid)).opacity, 0.5, 0.001, 'opacity');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with a full Design panel');
    await shot(page, 'design-panel-light');

    /* ---- several layers: mixed values, one transaction, group ---- */
    await page.locator('.hd-canvas').focus(); const tcc = await pt(tx.x + 10, tx.y + tx.h / 2); await page.keyboard.down('Shift'); await page.mouse.click(tcc[0], tcc[1]); await page.keyboard.up('Shift'); await settle(page);
    assert.equal(await ev(() => HD.sel.ids.length), 2); assert.equal(await page.locator('.hd-right input[aria-label="X position"]').inputValue() !== '', true);
    assert.equal(await page.locator('.hd-right input[aria-label="Width"]').inputValue(), 'Mixed');
    const undoN = await ev(() => { let n = 0; const s = HD.store; while (false) n++; return s.undoLabel ? s.undoLabel() : ''; });
    const op = page.locator('.hd-right input[aria-label="Opacity"]'); await op.fill('80'); await op.press('Enter'); await settle(page);
    near((await node(rid)).opacity, 0.8, 0.001, 'both layers'); near((await node(tid)).opacity, 0.8, 0.001, 'both layers');
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+z'); await settle(page); near((await node(rid)).opacity, 0.5, 0.001, 'one undo for both'); assert.equal((await node(tid)).opacity === undefined || (await node(tid)).opacity === 1, true); void undoN;
    await page.keyboard.press('Control+g'); await settle(page);
    const gid = await ev(() => HD.sel.ids[0]); const g = await node(gid); assert.equal(g.type, 'GROUP');
    assert.deepEqual((await ev(() => HD.store.children(HD.sel.ids[0]).slice())).sort(), [rid, tid].sort(), 'both layers are inside the group');
    const rin = await ev(() => { const id = HD.store.children(HD.sel.ids[0])[0]; return HD.store.worldBounds(id); }); assert.ok(rin.x >= g.x - 0.6, 'children keep their place on the canvas');

    /* ---- layers list: both ways, reorder by dragging ---- */
    assert.equal(await page.locator('.hd-lrow.sel .hd-lname').textContent(), g.name, 'canvas selection shows in the list');
    await page.locator('.hd-lrow', {hasText: 'Card'}).click(); assert.deepEqual(await ev(() => HD.sel.ids.slice()), ['9:5'], 'list selection reaches the canvas');
    await settle(page);
    const order0 = await ev(() => HD.store.children(HD.sel.page).slice()); assert.equal(order0[order0.length - 1], gid);
    const from = await page.locator('.hd-lrow', {hasText: 'Card'}).boundingBox(), to = await page.locator('.hd-lrow.hd-lrow', {hasText: g.name}).first().boundingBox();
    await page.mouse.move(from.x + 80, from.y + 14); await page.mouse.down(); await page.mouse.move(from.x + 84, from.y + 4, {steps: 3}); await page.mouse.move(to.x + 80, to.y + 3, {steps: 6}); await shot(page, 'layer-drag'); await page.mouse.up(); await settle(page);
    const order1 = await ev(() => HD.store.children(HD.sel.page).slice()); assert.equal(order1[order1.length - 1], '9:5', 'Card is on top now'); assert.equal(order1[order1.length - 2], gid);
    assert.deepEqual((await page.locator('.hd-lrow .hd-lname').allTextContents()).slice(0, 2), ['Card', g.name]);
    await page.locator('.hd-lrow', {hasText: g.name}).first().locator('.hd-lcaret').click(); await settle(page); assert.ok((await page.locator('.hd-lrow').count()) >= 5, 'the group opened');
    await page.locator('.hd-lrow', {hasText: 'Card'}).hover(); await page.locator('.hd-lrow', {hasText: 'Card'}).locator('.hd-leye').click(); await settle(page); assert.equal((await node('9:5')).visible, false, 'hidden from the list');
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+z'); await settle(page); assert.notEqual((await node('9:5')).visible, false);

    /* ---- undo walks back: the reorder, then the group ---- */
    await page.keyboard.press('Control+z'); await settle(page); assert.deepEqual(await ev(() => HD.store.children(HD.sel.page).slice()), order0, 'undo the reorder');
    await page.keyboard.press('Control+z'); await settle(page); assert.equal(await ev(() => Array.from(HD.store.children(HD.sel.page)).some(id => HD.store.get(id).type === 'GROUP')), false, 'undo the group');
    assert.equal(await ev(i => HD.store.parent(i), rid), '0:1'); near((await node(rid)).x, k.x, 0.6, 'and the rectangle is where it was');
    void undo0;

    /* ---- menus, palette, shortcuts, duplicate, delete ---- */
    const kc = await pt(k.x + 20, k.y + 20); await page.mouse.click(kc[0], kc[1], {button: 'right'}); await page.locator('.hd-pop-menu').waitFor(); assert.ok(await page.locator('.hd-mi', {hasText: 'Bring to front'}).isVisible());
    assert.deepEqual(await ev(layoutProblems), [], 'layout with the context menu open'); await shot(page, 'context-menu'); await page.keyboard.press('Escape'); assert.equal(await page.locator('.hd-pop').count(), 0);
    await page.keyboard.press('Control+k'); await page.locator('.hd-pal').waitFor(); await page.keyboard.type('zoom to fit'); await shot(page, 'palette'); await page.keyboard.press('Enter'); assert.equal(await page.locator('.hd-pal').count(), 0);
    await page.keyboard.press('Shift+?'); await page.locator('.hd-sheet').waitFor(); assert.ok((await page.locator('.hd-keyrow').count()) > 40, 'every shortcut is listed'); await shot(page, 'shortcuts'); await page.keyboard.press('Escape');
    await page.mouse.click(kc[0], kc[1]); await settle(page); assert.deepEqual(await ev(() => HD.sel.ids.slice()), [rid]);
    const n1 = await ev(() => HD.store.children(HD.sel.page).length); await page.keyboard.press('Control+d'); await settle(page); assert.equal(await ev(() => HD.store.children(HD.sel.page).length), n1 + 1, 'duplicate');
    await page.keyboard.press('Delete'); await settle(page); assert.equal(await ev(() => HD.store.children(HD.sel.page).length), n1, 'delete');
    await page.keyboard.press('Control+a'); assert.equal(await ev(() => HD.sel.ids.length), n1, 'select all'); await page.keyboard.press('Escape');
    await page.keyboard.press('Shift+1'); await settle(page); const z1 = await ev(() => HD.render.view.zoom); const cb = await page.locator('.hd-canvas').boundingBox();
    await page.mouse.move(cb.x + cb.width / 2, cb.y + cb.height / 2); const w0 = await ev(() => { const r = HD.tools.canvas.getBoundingClientRect(); return HD.render.screenToWorld(r.width / 2, r.height / 2); });
    await page.keyboard.down('Control'); await page.mouse.wheel(0, -200); await page.keyboard.up('Control'); await settle(page);
    assert.ok(await ev(() => HD.render.view.zoom) > z1, 'ctrl + wheel zooms in'); const w1 = await ev(() => { const r = HD.tools.canvas.getBoundingClientRect(); return HD.render.screenToWorld(r.width / 2, r.height / 2); }); near(w1[0], w0[0], 1.5, 'zoom keeps the point under the cursor'); near(w1[1], w0[1], 1.5, 'zoom keeps the point under the cursor');
    await page.mouse.wheel(0, 120); await settle(page); const w2 = await ev(() => { const r = HD.tools.canvas.getBoundingClientRect(); return HD.render.screenToWorld(r.width / 2, r.height / 2); }); assert.ok(w2[1] > w1[1], 'wheel pans down');
    await page.keyboard.press('Shift+1'); await settle(page);

    /* ---- pen: a VECTOR whose path sits in the node's own 0..w / 0..h box; copy + paste; snapping ---- */
    await page.keyboard.press('p'); assert.equal(await ev(() => HD.tools.current), 'pen');
    for (const w of [[520, 660], [620, 660], [570, 740], [520, 660]]) { const s = await pt(w[0], w[1]); await page.mouse.click(s[0], s[1]); await page.waitForTimeout(40); } await settle(page);
    const vid = await ev(() => HD.sel.ids[0]), vec = await node(vid); assert.equal(vec.type, 'VECTOR'); near(vec.x, 520, 1, 'vector x'); near(vec.w, 100, 1, 'vector w'); near(vec.h, 80, 1, 'vector h');
    assert.match(vec.path, /^M0 0L100 0L50 80(L0 0)?Z$/, 'a closed triangle in its own box: ' + vec.path); assert.equal(await ev(() => HD.tools.current), 'move');
    await page.locator('.hd-right input[aria-label="Width"]').fill('200'); await page.keyboard.press('Enter'); await settle(page); assert.match((await node(vid)).path, /^M0 0L200 0L100 80/, 'resizing a vector rescales its path');
    await page.locator('.hd-canvas').focus(); const nb = await ev(() => HD.store.children(HD.sel.page).length);
    await ev(() => { const dt = new DataTransfer(); document.dispatchEvent(new ClipboardEvent('copy', {clipboardData: dt, bubbles: true, cancelable: true})); window.__copied = dt.getData('text/plain'); document.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }); await settle(page);
    assert.equal(await ev(() => window.__copied), vec.name, 'the system clipboard gets the layer name'); assert.equal(await ev(() => HD.store.children(HD.sel.page).length), nb + 1, 'paste adds a copy'); assert.notEqual(await ev(() => HD.sel.ids[0]), vid);
    await page.keyboard.press('Delete'); await settle(page);
    const cardB = await node('9:5'); await page.mouse.move(...(await pt(cardB.x + 110, cardB.y + 70))); await page.mouse.down(); await page.mouse.move(...(await pt(cardB.x + 30, cardB.y + 70)), {steps: 4}); await page.mouse.move(...(await pt(cardB.x + 110 - 87, cardB.y + 71)), {steps: 3});
    assert.ok(await ev(() => HD.tools.state.guides.length > 0), 'a smart guide shows while it snaps'); const sx = await ev(() => HD.store.prop('9:5', 'x')); assert.ok(Math.abs(sx - 393) <= 6 && sx !== 393, 'the card left the raw pointer position (393) for a neighbour edge: ' + sx); await shot(page, 'snapping'); await page.mouse.up(); await settle(page);
    await page.keyboard.press('Control+z'); await settle(page); near((await node('9:5')).x, 480, 0.01, 'undo the snap move');

    /* ---- later phases plug in: a panel, a menu item, a shortcut, a hook ---- */
    await ev(() => { window.__got = []; HD.ui.registerPanel('right', 'prototype', {title: 'Prototype', render(el) { if (!el.firstChild) el.appendChild(HD.ui.h('p', {class: 'hd-note pad', text: 'from a later phase'})); }});
      HD.ui.registerMenu('context', {label: 'Create component', run: () => window.__got.push('menu')}); HD.ui.registerShortcut('mod+alt+k', () => window.__got.push('key')); HD.ui.hook('export', ids => window.__got.push('export:' + ids.length)); }); await settle(page);
    { const tabs = await page.locator('.hd-right .hd-tab').allTextContents(); assert.equal(tabs[0], 'Design'); assert.ok(tabs.includes('Prototype'), 'a later phase adds its tab: ' + tabs); } await page.locator('.hd-tab', {hasText: 'Prototype'}).click(); await settle(page); assert.equal(await page.locator('.hd-right .hd-pbody.custom').textContent(), 'from a later phase');
    await page.locator('.hd-tab', {hasText: 'Design'}).click(); await settle(page); await page.locator('.hd-canvas').focus(); await page.keyboard.press('Control+Alt+k'); await page.locator('.hd-top .hd-btn', {hasText: 'Export'}).click();
    await page.mouse.click(kc[0], kc[1], {button: 'right'}); await page.locator('.hd-mi', {hasText: 'Create component'}).click(); assert.deepEqual(await ev(() => window.__got), ['key', 'export:1', 'menu']);
    await ev(() => HD.ui.hook('share', f => window.__got.push('share:' + (f && f.id)))); await page.locator('.hd-top .hd-btn', {hasText: 'Share'}).click(); await page.waitForFunction(() => window.__got.includes('share:f1'));

    /* ---- the server has it, another person shows up, the file renames ---- */
    await page.waitForFunction(() => HD.net.pending() === 0); const saved = mock.files.get('f1').doc.nodes;
    assert.ok(saved[rid] && saved[rid].type === 'RECT' && saved[rid].fills[0].type === 'solid', 'the rectangle reached the server'); assert.equal(saved[tid].chars, 'Namaste नमस्ते!');
    mock.ghost('f1', {cid: 77, name: 'Asha', color: '#E0457B'}, {x: 200, y: 200, page: '0:1', sel: ['9:5'], vp: [0, 0, 1]}); await page.locator('.hd-person').waitFor(); assert.equal(await page.locator('.hd-person').textContent(), 'A');
    await page.locator('.hd-fname').click(); await page.locator('.hd-fname-in').fill('Diwali poster'); await page.keyboard.press('Enter'); await page.waitForFunction(() => document.querySelector('.hd-fname-t') && document.querySelector('.hd-fname-t').textContent === 'Diwali poster'); await page.waitForTimeout(150); assert.equal(mock.files.get('f1').name, 'Diwali poster');
    await settle(page); await shot(page, 'editor-light-1440');

    /* ---- nothing overlaps or is cut off: 1440x900 and 1280x800, light and dark ---- */
    await page.mouse.click(kc[0], kc[1]); await settle(page);
    for (const vp of [[1440, 900], [1280, 800]]) for (const theme of ['light', 'dark']) {
      await page.setViewportSize({width: vp[0], height: vp[1]}); await ev(th => window.HoolaTheme.setTheme(th), theme); await settle(page);
      const kk = await pt(k.x + 20, k.y + 20); await page.mouse.click(kk[0], kk[1]); await settle(page);
      assert.equal(await ev(() => document.documentElement.getAttribute('data-theme')), theme);
      assert.deepEqual(await ev(layoutProblems), [], 'layout ' + vp.join('x') + ' ' + theme);
      const bg = await ev(() => getComputedStyle(document.querySelector('.hd-right')).backgroundColor); assert.equal(bg, theme === 'dark' ? 'rgb(24, 21, 43)' : 'rgb(255, 255, 255)', 'panel colour in ' + theme);
      await shot(page, 'editor-' + theme + '-' + vp[0]);
      await page.locator('.hd-right .hd-sec[aria-label="Fill"] .hd-sw.big').click(); await page.locator('.hd-picker').waitFor(); assert.deepEqual(await ev(layoutProblems), [], 'picker ' + vp.join('x') + ' ' + theme); await shot(page, 'picker-' + theme + '-' + vp[0]); await page.keyboard.press('Escape');
    }
    await page.setViewportSize({width: 1024, height: 720}); await settle(page); assert.deepEqual(await ev(layoutProblems), [], 'layout at 1024 wide'); await shot(page, 'editor-1024');
    await page.setViewportSize({width: 700, height: 800}); await settle(page); assert.ok(await ev(() => document.querySelector('.hd-editor').classList.contains('hd-small')), 'small-screen mode');
    assert.equal(await page.locator('.hd-right').isVisible(), false); assert.match(await page.locator('.hd-banner').textContent(), /bigger screen/); assert.equal(await ev(() => HD.tools.current), 'hand'); await shot(page, 'small-screen');
    await ev(() => window.HoolaTheme.setTheme('light')); await page.setViewportSize({width: 1440, height: 900}); await settle(page); assert.equal(await ev(() => HD.tools.current), 'move');

    /* ---- the connection drops: a banner, edits are kept, and they arrive when it is back ---- */
    mock.down(true); await page.waitForFunction(() => HD.net.status === 'offline', null, {timeout: 45000}); await page.waitForFunction(() => /offline/i.test(document.querySelector('.hd-banner').textContent));
    assert.match(await page.locator('.hd-status').getAttribute('class'), /offline/); const kx = (await node(rid)).x;
    await page.locator('.hd-canvas').focus(); const ko = await pt(k.x + 20, k.y + 20); await page.mouse.click(ko[0], ko[1]); await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight'); await settle(page);
    near((await node(rid)).x, kx + 2, 0.01, 'editing goes on offline'); assert.ok(await ev(() => HD.net.pending() > 0), 'the edits wait'); await shot(page, 'offline');
    assert.equal(await ev(() => { const e = new Event('beforeunload', {cancelable: true}); window.dispatchEvent(e); return e.defaultPrevented; }), true, 'leaving with unsent changes asks first');
    mock.down(false); await page.waitForFunction(() => HD.net.status === 'live' && HD.net.pending() === 0, null, {timeout: 30000}); await page.waitForFunction(() => document.querySelector('.hd-banner').hidden);
    near(mock.files.get('f1').doc.nodes[rid].x, kx + 2, 0.01, 'the offline edits reached the server'); near((await node(rid)).x, kx + 2, 0.01, 'and stayed on screen');

    /* ---- back to the files: the thumbnail was sent, the new name shows ---- */
    await page.locator('.hd-top button[aria-label="Back to your files"]').click(); await page.locator('.hd-card').first().waitFor();
    assert.equal(await page.locator('.hd-cname').first().textContent(), 'Diwali poster'); await page.waitForFunction(() => document.querySelector('.hd-thumb img'), null, {timeout: 8000}); assert.ok(mock.files.get('f1').thumb && mock.files.get('f1').thumb.length > 100, 'thumbnail uploaded on leaving');
    await ev(() => window.HoolaTheme.setTheme('dark')); await settle(page); await shot(page, 'files-dark'); await ev(() => window.HoolaTheme.setTheme('light'));
    /* open it again in the same tab: one editor, one set of listeners */
    await page.locator('.hd-open').first().click(); await mounted(page); await settle(page); const again = await ev(() => HD.store.children(HD.sel.page).length);
    await page.locator('.hd-canvas').focus(); await page.keyboard.press('o'); await dragW([760, 300], [840, 380]); assert.equal(await ev(() => HD.store.children(HD.sel.page).length), again + 1, 'exactly one ellipse after reopening');
    assert.equal(await ev(() => HD.store.get(HD.sel.ids[0]).type), 'ELLIPSE'); await page.keyboard.press('Control+z'); await settle(page); assert.equal(await ev(() => HD.store.children(HD.sel.page).length), again);
    await page.waitForFunction(() => HD.net.pending() === 0); await page.close();

    /* ---- a view-only file: tools off, a banner, nothing changes ---- */
    mock.server.viewOnly = true; const v = await newPage({width: 1280, height: 800}); await v.goto(base + '#/f/f1'); await mounted(v); await settle(v);
    assert.equal(await v.evaluate(() => HD.app.file.role), 'view'); assert.match(await v.locator('.hd-banner').textContent(), /View only/); assert.ok(await v.locator('.hd-tool[data-tool="rect"]').isDisabled());
    const nBefore = await v.evaluate(() => HD.store.count()); await v.locator('.hd-canvas').focus(); await v.keyboard.press('r'); assert.equal(await v.evaluate(() => HD.tools.current), 'move');
    const vp2 = await v.evaluate(() => { const s = HD.render.worldToScreen(590, 150), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; });
    await v.mouse.move(vp2[0], vp2[1]); await v.mouse.down(); await v.mouse.move(vp2[0] + 60, vp2[1] + 40, {steps: 4}); await v.mouse.up(); await v.keyboard.press('Delete');
    assert.equal(await v.evaluate(() => HD.store.count()), nBefore); assert.equal(await v.evaluate(() => HD.store.prop('9:5', 'x')), 480, 'a view-only layer does not move'); assert.deepEqual(await v.evaluate(() => HD.sel.ids.slice()), ['9:5'], 'but it can be selected');
    assert.deepEqual(await v.evaluate(layoutProblems), [], 'layout, view only'); await shot(v, 'view-only'); await v.close();
    assert.deepEqual(errors, [], 'no script errors');
    console.log('design_ui_test: ok');
  } catch (e) { if (shots && browser.contexts().length) { for (const c of browser.contexts()) for (const pg of c.pages()) { try { await pg.screenshot({path: path.join(shots, 'FAILED.png')}); } catch (e2) { /* closed */ } } } throw e;
  } finally { await browser.close().catch(() => {}); await mock.close(); }
}
module.exports = {startMock, newDoc, seed, layoutProblems};
if (require.main === module) walk().catch(e => { console.error(e); process.exit(1); });
