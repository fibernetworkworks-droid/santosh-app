# HOOLA DESIGN — plan + build contract

Owner (11 Nov 2026): "A HOOLA DESIGN — deep research how Figma works in backend — make clone of Figma for Hoola end
to end with all feature, design, backend having same performance as Figma" + "deploy several agents".

Hoola Design is Hoola's OWN design editor: an original product, original look, no Figma name / logo / UI assets / code.
What is taken from Figma is the published ARCHITECTURE (their engineering blog; research in `docs/research/figma/`).

## 0. Said plainly before anything is built

- Figma = C++ compiled to WebAssembly + its own WebGL/WebGPU renderer + a Rust multiplayer server, ~10 years of
  work. Hoola Design v1 = plain JavaScript + Canvas2D (no build step, strict CSP, no WASM) + a Python multiplayer
  room inside the existing FastAPI process. The DESIGN of the system is the same; the raw speed is NOT.
  Target that is honest: smooth (60 fps pan / zoom / drag) up to a few thousand visible layers; 10-20 people in one
  file. A 100,000-layer file at Figma speed is not reachable without a WebGL/WASM engine (phase D9).
- "All features" is a ladder, not one release. Phases below; each ships working.

## 1. Architecture (the Figma ideas kept)

1. Document = a TREE OF NODES, each node a flat bag of properties. One file = one document.
2. Sync = LAST-WRITER-WINS PER PROPERTY, server-authoritative (not OT, not a full CRDT). The server applies ops in
   arrival order, numbers them (`seq`) and fans them out. Two people changing DIFFERENT properties of one node both win.
3. Child order = FRACTIONAL INDEX string (`idx`) on the child; `parent` + `idx` change together in one op.
   The server REFUSES a reparent that would create a cycle.
4. Node ids = `<cid>:<n>`: `cid` = a per-connection client number given by the server, `n` = that client's counter.
   Two clients can never mint the same id.
5. One ROOM per open file, in memory: loaded on first join, ops journaled, snapshot checkpointed, unloaded when empty.
6. Client applies its own edits AT ONCE (optimistic). While a local change to (node, prop) is un-acked, an incoming
   remote value for that same (node, prop) is ignored (the ack will carry the truth). On reconnect: reload the doc,
   re-apply the still-pending local ops.
7. Undo is PER CLIENT and stores inverse ops (redo = inverse of undo); an undo is just a new edit to everyone else.
8. Rendering = own renderer on a `<canvas>`, never DOM nodes per layer: viewport culling, redraw only when dirty,
   bitmap cache for unchanged heavy subtrees, devicePixelRatio aware.

## 2. Data model (THE contract — server and client must agree exactly)

Document JSON: `{"nodes": {"<id>": {<props>}, ...}}`. Root node id is `"0:0"` (type `DOCUMENT`). Its children are
`PAGE` nodes. A new file has `0:0` + one page `0:1` named "Page 1".

Every node: `type`, `parent` (id, absent on root), `idx` (fractional index string), `name`.

Types: `DOCUMENT PAGE FRAME GROUP SECTION RECT ELLIPSE LINE POLYGON STAR VECTOR TEXT COMPONENT COMPONENT_SET INSTANCE`.

Properties (all optional; defaults in brackets). Unknown properties are kept and synced untouched (forward compatible).

| group | props |
|---|---|
| geometry | `x` `y` (relative to parent's top-left, [0]) · `w` `h` [100] · `rot` degrees clockwise about the node's centre [0] · `flipH` `flipV` [false] |
| state | `visible` [true] · `locked` [false] · `opacity` 0-1 [1] · `blend` [`normal`] (canvas `globalCompositeOperation` names: multiply, screen, overlay, darken, lighten, ...) · `mask` [false] |
| fills / strokes | `fills`: array of paints, drawn bottom to top · `strokes`: array of paints · `strokeWeight` [1] · `strokeAlign` `center|inside|outside` [center] · `strokeCap` `butt|round|square` · `strokeJoin` `miter|round|bevel` · `dash` [] |
| paint | `{type:"solid", color:"#RRGGBB", opacity:1, visible:true}` · `{type:"linear"|"radial"|"angular", stops:[{pos:0..1,color:"#RRGGBB",opacity}], from:[x,y], to:[x,y]}` (from/to in 0..1 of the node box) · `{type:"image", hash:"<asset hash>", mode:"fill"|"fit"|"crop"|"tile", opacity}` |
| corners | `radius` number or `[tl,tr,br,bl]` [0] |
| effects | `effects`: `[{type:"drop"|"inner", x,y,blur,spread,color,opacity,visible}, {type:"blur"|"bgblur", blur, visible}]` |
| frame | `clip` [true for FRAME/COMPONENT/INSTANCE] · `layout`: `{mode:"none"|"h"|"v", gap:0, pad:[t,r,b,l], alignMain:"start"|"center"|"end"|"between", alignCross:"start"|"center"|"end"|"stretch", wrap:false}` · `grids`: `[{type:"grid"|"columns"|"rows", size, count, gutter, margin, align:"stretch"|"start"|"center"|"end", color, opacity, visible}]` (layout grids: drawn over the frame, never exported) |
| boolean group | GROUP `bool`: `union|subtract|intersect|exclude` (absent = a plain group). The group is ONE shape: the outline of its children combined bottom-first (subtract = the first child minus the rest); the group's own `fills` / `strokes` / `effects` style the result, the children's paints are not drawn; text and lines take no part |
| child-in-layout | `sizeH` `sizeV`: `fixed|hug|fill` [fixed] · `layoutPos`: `auto|absolute` [auto] · `minW maxW minH maxH` |
| constraints | `cons`: `{h:"left"|"right"|"leftright"|"center"|"scale", v:"top"|"bottom"|"topbottom"|"center"|"scale"}` [left, top] |
| shapes | POLYGON `sides` [3] · STAR `sides` [5] `ratio` [0.5] · LINE uses `w` as length, `h`=0 · VECTOR `path` (SVG path `d`, coordinates in the node's own 0..w / 0..h box) `fillRule` |
| text | `chars` · `font` [Inter] · `fontSize` [16] · `fontWeight` [400] · `italic` · `lineHeight` (number = px, or `"auto"`) · `letterSpacing` [0] · `align` `left|center|right|justify` · `alignV` `top|middle|bottom` · `autoResize` `wh|h|none` [wh] · `decoration` `none|underline|strike` · `textCase` `none|upper|lower|title` · `runs`: optional `[{s,e,<text props>}]` style overrides for ranges |
| components | INSTANCE: `comp` (id of the COMPONENT) · `ov`: `{"<path of child ids inside the component joined by />": {<prop>: value}}` overrides · COMPONENT: `desc` · COMPONENT_SET children are variants named `Prop=Value, Prop2=Value` |
| styles / variables | kept on the root node: `styles`: `{"<sid>": {kind:"fill"|"text"|"effect", name, value}}` · `vars`: `{"<vid>": {name, type:"color"|"number"|"string"|"bool", modes:{"<mode>":value}}}` · `modes`: [..] · a node links with `fillStyle` `textStyle` `effectStyle` and `bind`: `{"<prop>": "<vid>"}` |
| prototype | `reactions`: `[{trigger:"click"|"hover"|"press"|"drag"|"after", delay, action:"navigate"|"back"|"overlay"|"swap"|"close"|"url"|"scroll", to:"<node id>", url, anim:{type:"instant"|"dissolve"|"smart"|"move"|"push"|"slide", dir, dur, ease}}]` · FRAME `protoStart` [false] · `scroll`: `none|v|h|both` · `fixed` [false] |
| export | `exports`: `[{fmt:"png"|"jpg"|"svg"|"pdf", scale:1, suffix:""}]` |
| page | `bg` ["#F5F5F5"] · `guides`: `[{axis:"x"|"y", pos}]` (ruler guides; axis x = an upright line at world x = pos) |

GROUP: `x y w h` are DERIVED from its children by the editing client (written as normal ops in the same batch).

### Ops

One op = `{"id": "<node id>", "p": {<prop>: <value>, ...}}` (set; a value of `null` REMOVES the property) or
`{"id": "<node id>", "del": 1}` (delete node AND its whole subtree).
Create = a set op on an unknown id whose `p` has `type`, `parent`, `idx`. A set op on an unknown id WITHOUT `type`
is dropped (the node was deleted by someone else).

Server rules for each op, in order: unknown type -> reject · `parent` missing / not existing -> reject ·
reparent creating a cycle -> reject · root `0:0` can not be deleted or reparented · op bigger than 256 KB -> reject ·
document over 200,000 nodes -> reject creates. A rejected op is listed in the ack; the client rolls it back.

### WebSocket `/api/design/ws?file=<file id>`

Auth exactly like `/api/voice/ws` in `main.py` (Authorization header, or subprotocols `hoola, hoola-key.<token>`).
Close codes: 4401 not signed in, 4404 no such file for this tenant, 4403 view-only writer.
All frames are JSON text.

| dir | frame |
|---|---|
| S->C | `{"t":"init","cid":<int>,"seq":<int>,"doc":{"nodes":{...}},"file":{"id","name","role":"edit"|"view"},"users":[{"cid","name","color"}]}` |
| C->S | `{"t":"ops","n":<client batch no>,"ops":[op,...]}` |
| S->C (sender) | `{"t":"ack","n":<same>,"seq":<int>,"rejected":[<index in ops>,...]}` |
| S->C (others) | `{"t":"ops","seq":<int>,"by":<cid>,"ops":[op,...]}` (only the accepted ops) |
| C->S | `{"t":"pres","x":<world x>,"y":<world y>,"page":"<id>","sel":[ids],"vp":[x,y,zoom]}` (throttle 30/s) |
| S->C (others) | `{"t":"pres","cid",...same fields}` · `{"t":"join","user":{cid,name,color}}` · `{"t":"leave","cid"}` |
| both | `{"t":"ping"}` / `{"t":"pong"}` (client pings every 15 s) |
| S->C | `{"t":"file","name":...}` (renamed) · `{"t":"comment",...}` (a comment was added / changed) · `{"t":"reload"}` (a version was restored: fetch again) |

### REST (all under `/api/design`, auth `require_key` + `current_tenant`, every row tenant-checked)

- `GET /files?q=&trash=0` · `POST /files {name?, template?}` · `GET /files/{id}` · `PATCH /files/{id} {name?, star?}` ·
  `DELETE /files/{id}` (to trash; `?forever=1` only from trash) · `POST /files/{id}/restore` · `POST /files/{id}/duplicate`
- `GET /files/{id}/doc` -> `{seq, doc}` · `PUT /files/{id}/thumb` (PNG bytes <= 300 KB) · `GET /files/{id}/thumb`
- `GET /files/{id}/versions` · `POST /files/{id}/versions {label}` · `GET /versions/{vid}/doc` ·
  `POST /versions/{vid}/restore` (saves the current state as a version first, then tells the room to reload)
- `GET /files/{id}/comments` · `POST /files/{id}/comments {node?, x, y, page, text, parent?}` ·
  `PATCH /comments/{cid} {text?, resolved?}` · `DELETE /comments/{cid}`
- `POST /files/{id}/assets` (image bytes; real PNG / JPEG / WebP / GIF / SVG-as-image checked by content, <= 10 MB) ->
  `{hash}` · `GET /assets/{hash}` (tenant-checked)
- `POST /files/{id}/share {role:"view"|"none"}` -> `{token}` · public `GET /api/design/shared/{token}/doc` (read only)
- `POST /files/{id}/ai {prompt, page, x, y}` (phase D5) -> ops applied THROUGH the room, so every open editor sees them

Storage: tables `design_files`, `design_ops` (journal: file_id, seq, by, ops JSON, at), `design_versions`,
`design_comments`, `design_shares`; snapshots in `design_files.snapshot` (zlib JSON) with `snapshot_seq`; a room
checkpoints every 200 ops or 20 s idle and on last leave, then trims the journal below the snapshot.
Auto version every 30 min of editing (keep 50). Assets on disk `data/design/<tenant>/assets/<sha256>`.

## 3. Client contract (plain JS, no build step, `server/app/static/console/design/`)

Page `/console/design` -> `design.html`; files loaded IN THIS ORDER, each an IIFE that adds to `window.HD`:
`hd-math.js hd-core.js hd-net.js hd-layout.js hd-render.js hd-tools.js hd-ui.js hd-app.js` (+ later feature files).
Sign-in = the console token `localStorage['hoola.console.token']`; no token -> `location.replace('/console/')`.
Addresses: `#/` = file browser, `#/f/<file id>` = editor, `#/f/<id>/p/<node id>` = prototype player.
Strict CSP stays: no inline script, no eval, no remote script. Fonts only through Google Fonts stylesheets.

```
HD.math   mat = [a,b,c,d,e,f]; identity() mul(m,n) inv(m) apply(m,x,y)->[x,y] translate rotate scale
          rectUnion(a,b) rectHit(a,b) rectContains(a,b) ptInRect  (rect = {x,y,w,h})
HD.frac   between(a|null, b|null)->string   nBetween(a,b,n)->string[]      (base-62, a < result < b)
HD.store  ROOT='0:0'
          load(doc, cid)            get(id)->node|undefined        has(id)
          children(id)->id[] (sorted by idx, cached)               parent(id)   pageOf(id)   pages()->id[]
          newId()                   create(type, parentId, props, beforeId?)->id
          set(id, props)            remove(ids[])                  move(ids[], parentId, beforeId|null)
          tx(label, fn)             (everything inside = ONE undo step and ONE op batch; nesting joins the outer)
          undo() redo() canUndo() canRedo()
          applyRemote(ops)          onOps(fn(ops))  (local op batches, for HD.net)   rollback(ops)  (rejected)
          on('change', fn({ids:Set, structural:bool, remote:bool}))   on('load', fn)
          localMatrix(id) worldMatrix(id) worldBounds(id)->rect (cached; invalidated on change)
          defaults(type)->props     walk(id, fn)                   ancestors(id)->id[]
HD.sel    ids (array)  set(ids) add(id) toggle(id) clear() has(id)  on('change', fn)   page (current page id)  setPage(id)
HD.net    connect(fileId) close()  status ('connecting'|'live'|'offline')  on('status'|'init'|'presence'|'file'|'comment', fn)
          users (Map cid->{name,color,x,y,page,sel})   sendPresence(p)   role
HD.layout run(changedIds:Set)   (auto layout + constraints + group bounds + text autoResize; writes with HD.store.set
          INSIDE the current tx; called by the store at the end of every local tx, never for remote ops)
          measureText(node)->{w,h,lines}
HD.render init(canvas)  view {x,y,zoom}  setView(v, animate?)  zoomToFit(ids?)  invalidate()
          screenToWorld(sx,sy)->[x,y]   worldToScreen(wx,wy)->[x,y]
          hitTest(wx,wy,{deep:bool})->id|null    nodesInRect(rect, pageId)->id[]
          addOverlay(fn(ctx, view))  (selection boxes, guides, cursors are drawn by overlays, in SCREEN space)
          drawNode(ctx, id)  toCanvas(id, scale, {bg})->HTMLCanvasElement   toSVG(id)->string   image(hash)->HTMLImageElement|null
HD.tools  register(name, {cursor, down(e), move(e), up(e), key(e), dbl(e), enter(), leave()})  set(name)  current
          (pointer event e = {x,y (world), sx,sy (screen), shift, alt, mod, button, target (hit id)})
HD.ui     mount(rootEl)  toast(msg, bad?)  refresh()  api(method, path, body)  esc(s)
          registerPanel(side:'left'|'right', id, {title, render(el), when?()})   registerMenu(...)  registerShortcut(combo, fn)
HD.app    boot()  openFile(id)  closeFile()  file {id,name,role}
```

Rules every client file follows: never touch another module's private state; all document edits go through
`HD.store` inside `HD.store.tx`; nothing draws layers with DOM; every pointer handler works in WORLD coordinates;
all user text is escaped with `HD.ui.esc`; remote text (names, comments, layer names) is data, never HTML.

## 4. Phases

| # | name | what ships | state |
|---|---|---|---|
| D1 | Engine | server room + journal + REST files; client store / net / layout / renderer; select, move, resize, rotate, frame, shapes, text, pen, hand, zoom; layers + properties panels; undo; multiplayer cursors; file browser | building |
| D2 | Design depth | auto layout UI, constraints, gradients, image fills, effects, boolean groups, masks, vector edit mode, rulers / guides / snapping / smart distances, alignment, grids | building |
| D3 | Systems | components, instances, overrides, variants, styles, variables + modes, team library across files | building |
| D4 | Hand-off | export PNG / JPG / SVG / PDF, SVG + image import, inspect panel (CSS / Flutter / Tailwind values), copy as code | building |
| D5 | Together | comments, version history (auto + named, restore), share link (view only), follow a person, AI: one line -> a designed frame; agent tool `hoola_design` | building |
| D6 | Prototype | reactions, flows, player with smart animate, device frames, share a prototype link | building |
| D7 | Bridges | import a .fig-exported SVG / a Figma file through the owner's own Figma token (REST), design -> Web Studio / App Studio (a frame becomes a site section / app screen) | next |
| D8 | Plugins | sandboxed plugin API (iframe sandbox + message bridge), community templates | later |
| D9 | Speed | WebGL2 renderer behind the same `HD.render` contract, tile cache, worker-side layout, binary ops; branches + merge | later |

## 5. Not built / will not be built

No Figma branding or assets. No reading of `.fig` binaries taken from Figma's servers without her own token.
No offline desktop app. FigJam / Slides / Sites equivalents are separate products (Web Studio is Hoola's "Sites").

## 6. As built after the first wave (read this before extending) 

The file headers of `hd-core.js`, `hd-net.js`, `hd-render.js`, `hd-layout.js`, `hd-tools.js`, `hd-ui.js` are the
exact API; this is the short list of what differs from sections 2-3.

- Store: `prop(id, name)` = value with the type default (defaults are never written into ops; always read with it).
  `get(id)` is the LIVE node and `children(id)` a FROZEN array: never mutate, build new arrays / objects for `set`.
  `gesture()` / `gestureEnd()` make a whole drag one undo step. `readOnly` is true for view-only files.
  The store keeps a SHADOW (the server's document); screen = shadow + un-acked local ops.
- Server: the WebSocket is accepted first and then closed with 4401 / 4404 (a browser needs that to read the code).
  A view-only connection is `/api/design/ws?share=<token>` with NO sign-in; its ops are all rejected.
  `init.users` lists the OTHER people; own identity is `init.you`. Comment frame =
  `{"t":"comment","action":"add"|"update"|"delete","comment":{...}}`. Extra public route
  `GET /api/design/shared/{token}/assets/{sha}`. REST lists come wrapped: `{files:[]}` `{versions:[]}` `{comments:[]}`.
  Server-side entry points for other code: `design.room.HUB.apply_ops(...)` and `HUB.new_cid(...)` (ops applied through
  the room reach every open editor), `design.store` = all DB access, `design.doc` = the document rules.
- Render: `view.x / view.y` = SCREEN position of world (0,0). `invalidate()` redraws overlays only, `invalidate(true)`
  forces a document repaint. Extras: `hitChain`, `toCanvas(id, scale, {bg, bounds})`, `toSVG(id, {bg, bounds})`,
  `exportBounds`, `ready(id, ms)`, `loadFont`, `setEditing(id)`, `bounds(ids)`, `on('view'|'frame', fn)`, `stats`.
- UI extension points (use these; do not edit the first-wave files): `HD.ui.hook(name, fn)` with names
  `share(file)` · `export(ids[])` · `exportSection(el, ids[])` · `present(frameId|null)` (also fired by
  `#/f/<id>/p/<node>`) · `comment({x,y,sx,sy,page,node})` · `importSvg(svgText, {x,y,page})` · `ai({page,x,y})` ·
  `versions(file)`; `HD.ui.registerPanel(side, id, {title, render(el), when})`,
  `HD.ui.registerMenu('context'|'main'|'view', item | fn(ids, e))`, `HD.ui.registerShortcut(combo, fn, label)`,
  `HD.ui.command({id, label, group, keys, run, when, edit})`. `HD.ui.api(method, '/files/...')` is prefixed with
  `/api/design`. `HD.tools.current` is the tool NAME; `HD.tools.act.*` holds the edit commands (group, align, paste...).
- Feature files (second wave), loaded after `hd-ui.js` and before `hd-app.js`, each with its own stylesheet
  `design-<name>.css`: `hd-vector.js` `hd-components.js` `hd-export.js` `hd-collab.js` `hd-proto.js` `hd-ai.js`.
- D2 design depth (`hd-vector.js`; path + boolean geometry in `HD.render.geom`): `HD.vector.edit(id) / leave() /
  editing`, `toVector(id)`, `editShape()`, `bool(op)`, `flatten()`, `mask()`, `rulers`, `grids`, `guides()`,
  `setGuides(list)`. New UI extension point `HD.ui.designSection(fn(el, ids))` (a section in the Design panel);
  `HD.ui.state.paint` = the paint open in the colour picker (`get()`, `set(paint, gesture)`, `stop`);
  `HD.tools.snapExtra(parent)` = extra snap boxes (the guides). A mask shows the siblings above it up to the next mask,
  by the ALPHA of its own picture. "auto" line height = the font's own ascent + descent. Radial and sweep gradients live
  in the 0..1 space of the box (an ellipse in a box that is not square). A VECTOR `path` whose bounds are not the box
  is moved and scaled to fit it. An instance at another size than its component is laid out again
  (`HD.layout.virtual`) when the component has auto layout or constraints, scaled otherwise.
  Not exact, said plainly: boolean crossings are found on curves cut into straight pieces (right to about 0.02 of a
  layer unit; the result is written back as the original curves); shadow spread on text / paths / groups is a
  16-sided ring (about 2% of the spread); a sweep gradient in SVG is a picture (up to 1024 px); Flatten does not
  outline strokes or text; text and lines take no part in a boolean.

- D5 together, as built (`hd-collab.js`, `design-collab.css`; test `server/tests/test_v0777_design_collab.py` +
  `web/design_collab_test.js` = two editors and one signed-out link visitor on a real server):
  REST added: `POST /versions/{vid}/duplicate {name?}` (a NEW file from a version) · `POST /files/{id}/versions`
  takes `note` · comments take `ox` / `oy` (the pin's place inside `node`, its own box; `x` / `y` stay the page point) ·
  public `GET /shared/{token}/comments` (read only). Limits (`design/limits.py`, in memory): 30 comment writes a
  minute per person, 120 doc + comment reads and 1,200 images a minute per link and address -> 429. `share none` shows
  the link's guests out (4404); editors stay. `design/assets.sweep()` (worker slot `design_asset_jobs`, once a day)
  deletes images no document, journal or kept version draws AND that were last uploaded over 7 days ago.
  Presence frames may also carry `vs` [canvas w, h], `chat` (cursor chat, 80 chars), `spot` (follow-me stamp); the
  server passes them through untouched. Client: `HD.net.connect(id, {share})`, `net.share`, `net.me`, `net.extra`
  (cid -> {vs, chat, chatAt, spot, at}), `net.setPresence({...})`, `net.hold()` / `net.release()` (a version preview:
  nothing sent, remote ops not applied, store locked; release fetches the live document again), `on('reload')`
  (the status stays `live` while a restored document is fetched). `HD.app.on('open'|'close', fn(file))`,
  `HD.app.link(node?, token?)`, `HD.app.focusNode(id)`, `HD.app.rawFetch`; addresses `#/s/<token>` (view-only, no
  sign-in; while it is open every non-`/shared` `/api` call is answered 403 in the page) and `?node=<id>` on both.
  The built-in commands are now registered when `hd-ui.js` loads, so a feature file may call `HD.ui.command` at load.
  NOT built: unread comments kept on the server (they are per browser, localStorage), edit-role sharing (so every
  comment in a file is its owner's and "Mine" = all), a prototype-only share link, dimming an idle person's cursor.

Measured (headless Chromium, software raster, 1280x800): pan 5 ms / frame with 5,000 layers, under 10 ms with 20,000;
server about 20,000 op batches / s, ack p50 0.23 ms; a killed server lost nothing. 10,000 layers scroll in the layers
panel with 39 DOM rows.
