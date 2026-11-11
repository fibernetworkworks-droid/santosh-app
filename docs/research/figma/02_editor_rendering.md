# Figma: the editor, the renderer and the design model (primary sources)

Read on 11 Nov 2026. Sources are Figma's own blog (figma.com/blog), the Figma Help Center (help.figma.com), Figma's developer
docs (developers.figma.com / figma.com/plugin-docs) and Evan Wallace's own writing. Every claim names its URL. Where a source
does **not** say something we wanted to know, this file says so instead of guessing. Nothing here was copied from Figma's code
(none is public); it is a reading of what they chose to publish.

Short version: Figma is a C++ program with its own document model, its own layout engine, its own text layout and its own GPU
renderer; the browser gives it a canvas, input events and a network, and very little else. The DOM is used for the panels
around the canvas, never for the design itself.

---

## 1. Engine: C++ to the web, a custom GPU renderer, no DOM for the canvas

### 1.1 C++ compiled for the browser

- 2015: "The editor is written in C++ and cross-compiled to JavaScript" with **Emscripten**, targeting **asm.js**; "the generated
  code is pre-optimized using LLVM's advanced optimizer." Source: Evan Wallace, *Building a professional design tool on the web*,
  https://www.figma.com/blog/building-a-professional-design-tool-on-the-web/
- Memory is managed by hand inside one typed array: "All C++ objects are just reserved ranges in a pre-allocated typed array so
  the JavaScript GC is never involved." Compact 32-bit floats and bytes replace 64-bit JS doubles. Large image and geometry
  buffers live outside the main heap through an internal API called **IndirectBuffer**, to reduce fragmentation and survive
  address-space limits (32-bit Chrome on Windows sometimes could not allocate a 256 MB typed array because ASLR fragmented the
  address space). Same source.
- 2017, *WebAssembly cut Figma's load time by 3x*: load time (app init + file download + first full render) improved "more than
  3x" after switching from asm.js to WebAssembly, "regardless of document size". Download size barely changed (compressed asm.js
  is only slightly larger than compressed wasm); the win is **parsing** (wasm parses ~20x faster than asm.js per the WebAssembly
  rationale) and skipped optimisation passes. Firefox cached the wasm-to-native translation, Chrome did not yet (Chromium bug
  719172), and a V8 crash (Chromium bug 729768) meant wasm shipped only in Firefox at first; debug builds stayed on asm.js
  because wasm debugging was immature. Wasm also has native 64-bit integers. Source:
  https://www.figma.com/blog/webassembly-cut-figmas-load-time-by-3x/
- 2023: "A 2018 renderer and WebAssembly overhaul made Figma 3x faster." Source: *Keeping Figma fast*,
  https://www.figma.com/blog/keeping-figma-fast/
- 2025: the same C++ renderer "compiles to WebAssembly with Emscripten for the web app and to native x64/arm64 for server-side
  rendering and testing". Source: *Figma rendering: powered by WebGPU*,
  https://www.figma.com/blog/figma-rendering-powered-by-webgpu/
- Note: the 2017 wasm post does not itself name Emscripten (it says "LLVM toolchain"); the 2015 and 2025 posts do.

### 1.2 Why a custom WebGL renderer instead of HTML / SVG / Canvas2D

The 2015 post lists the reasons (https://www.figma.com/blog/building-a-professional-design-tool-on-the-web/):
- DOM overhead, and geometry re-tessellated on every scale change;
- no guarantee the browser uses the GPU;
- masking, blur and blend modes inconsistent across browsers;
- immediate-mode 2D canvas forces geometry to be re-uploaded every frame;
- text layout differs between browsers and platforms;
- no angular (conic) gradients at the time.

What they built instead: "a highly-optimized **tile-based** engine" with masking, blurring, **dithered gradients**, blend modes and
nested layer opacity; "All rendering is done on the GPU and is fully anti-aliased." They also built "their own DOM, compositor,
and text layout engine". Same source. **Not published:** tile size, tile cache policy, or how dirty tiles are tracked — the post
names the technique only.

Browser gaps they had to work around (same source): high-DPI custom cursors broken differently in Chrome / Firefox / WebKit; the
web clipboard only takes `text/plain` and `text/html`, so Figma's own clipboard data is stored **as binary inside an HTML comment**;
trackpad pinch arrives in Chrome as a `wheel` event with `ctrlKey` set (so the page can `preventDefault()` and zoom itself),
while Firefox lagged and Safari pinch-zoom "is impossible to disable". Biggest gap at the time: no web API for glyph outlines or
kerning tables.

### 1.3 The 2025 move to WebGPU

Source for this whole subsection: https://www.figma.com/blog/figma-rendering-powered-by-webgpu/
- Why: WebGPU (shipped in Chromium in 2023) gives **compute shaders** ("used to move work off the CPU and onto the GPU"), no
  WebGL global state, and clearer error handling.
- The graphics interface was refactored first: draw-call inputs became **explicit function arguments** (this alone fixed stale-
  global-binding bugs even before WebGPU was added); uniforms moved from one-at-a-time sets to **one uniform buffer** written with an
  **encode-then-submit** pattern so uploads are batched.
- Shaders: the existing **WebGL 1 GLSL shaders stay the source of truth**; a custom processor translates them to WGSL using the
  open-source **naga** tool, extracts input types / data layouts, and supports includes.
- Bindings: Emscripten's WebGPU bindings (deprecated) are being replaced by Dawn's `emdawnwebgpu`; native builds use **Dawn**.
- Differences they hit: asynchronous readback, asynchronous error reporting, different coordinate systems.
- Performance work: caching and reusing **bind groups**, batching draw calls into **render passes**. Result: gains on some device
  classes, neutral on others, **no regressions**.
- Fallback: a compatibility test at load would cost "hundreds of milliseconds" (async readback), so instead they built a
  **dynamic mid-session switch from WebGPU back to WebGL** (Windows showed device loss followed by failed device requests), then
  **blocklisted devices by average fallback rate** because a switch causes a hitch.
- Next: compute-shader blur, WebGPU MSAA, RenderBundles to cut CPU submit cost.

### 1.4 Text rendering and font shaping

- Figma says it "uses custom text rendering" so designs look the same on every browser and OS, and warns there "may be subtle
  differences between your designs in Figma and the final implementation". Only `.TTF` and `.OTF` font files are supported.
  Source: *Guide to text*, https://help.figma.com/hc/en-us/articles/360039956434-Guide-to-text
- Variable fonts are supported (axes such as weight, width, slant; optical sizes):
  https://help.figma.com/hc/en-us/articles/5579502031511-Use-variable-fonts and
  https://www.figma.com/blog/variable-fonts-a-conversation-with-grilli-type/ . The Plugin API exposes `variationSettings` for every
  OpenType axis (plugin update 138): https://developers.figma.com/docs/plugins/updates/2026/09/03/version-1-update-138/
- The text layout result is **cached** as an expensive derived computation (*Speeding up file load times*,
  https://www.figma.com/blog/speeding-up-file-load-times-one-page-at-a-time/).
- **HarfBuzz: NOT confirmed.** No Figma blog post or help article we found names the shaping library. Do not repeat "Figma uses
  HarfBuzz" as a fact.
- Related, by Figma's co-founder but **not stated to be Figma's production method**: Evan Wallace, *Easy Scalable Text Rendering on
  the GPU* (2016), https://medium.com/@evanwallace/easy-scalable-text-rendering-on-the-gpu-c3f4d782c5ac — fill glyph outlines with
  no stencil buffer and no glyph-texture cache: draw triangles with additive blending of 1/255 so a pixel is inside when its count is
  odd, plus a per-quadratic-segment correction for curves; supports subpixel anti-aliasing and uses far less memory than signed
  distance fields.

### 1.5 The document model under it all

Source: Evan Wallace, *How Figma's multiplayer technology works* (2019), https://www.figma.com/blog/how-figmas-multiplayer-technology-works/
- "Every Figma document is a tree of objects, similar to the HTML DOM": root -> pages -> contents.
- Each object = an ID + properties; the model is `Map<ObjectID, Map<Property, Value>>`, i.e. `(ObjectID, Property, Value)` rows. A
  new feature usually just adds a property.
- Conflicts are **last-writer-wins per property**, ordered by the central server ("we don't need a timestamp because the server can
  define the order of events"); no full CRDT because the server is the authority.
- Child order = **fractional index** in (0, 1); inserting between siblings averages their positions. **Parent link + position are
  one property** so reparenting is atomic, and the link lives on the child, not as a list on the parent.

---

## 2. Vector model, booleans, blend modes, effects, fills, strokes

### 2.1 Vector networks instead of paths

Source: *Introducing vector networks*, https://www.figma.com/blog/introducing-vector-networks/
- "A path is a chain of lines and curves from one endpoint to the other." A vector network allows "lines and curves between any two
  points instead of requiring that they all join up to form a single chain" — a graph of vertices and segments. Three lines can meet
  at one point (impossible with a path).
- Same curve type as paths (cubic Béziers with handles), so existing vector data stays compatible.
- "Stroke cap and join styles just work naturally in vector networks", including junctions of three or more segments.
- Fills: instead of the winding-number rule ("a confusing concept" that depends on drawing direction), **enclosed regions** of the
  graph are filled, and holes are made by toggling regions with the paint bucket.
- The **bend tool** lets you drag a curve directly; the editor computes handle positions.

### 2.2 Boolean operations

Source: https://help.figma.com/hc/en-us/articles/360039957534-Boolean-operations
- Four operations, two pairs of opposites: **union / subtract**, **intersect / exclude**. They produce a non-destructive **boolean
  group**; union merges outer edges so strokes and effects apply to the outer path only.
- **Flatten** is destructive: flattened layers cannot be separated again (undo / version history only).
- Boolean results are derived data: prototypes skip computing "layout and boolean operations" for screens not shown
  (https://www.figma.com/blog/incremental-frame-loading/). **Not published:** the clipping algorithm itself.

### 2.3 Blend modes

Source: https://help.figma.com/hc/en-us/articles/360040667874-Create-unique-effects-with-Blend-modes
- Each **layer, fill or effect** carries exactly one blend mode. **Pass through** is the layer default (no effect by itself, but lets
  fills' and effects' blend modes reach content below); **Normal** isolates. Blend modes apply to drop shadows, inner shadows and
  noise too.

### 2.4 Effects

Source: https://help.figma.com/hc/en-us/articles/360041488473-Apply-effects-to-layers
- Seven types today: glass, drop shadow, inner shadow, layer blur, background blur, noise, texture.
- Only one layer blur or background blur per object; a background blur shows only when fill opacity is between 0.10 % and 99.99 %.
- "Background blurs are typically the slowest effect to render" — many of them slow a file down (this matches WebGPU's "compute-
  shader blur" as named future work).

### 2.5 Fills, strokes, gradients

- Renderer supports dithered gradients and (by 2015) angular gradients that browsers lacked:
  https://www.figma.com/blog/building-a-professional-design-tool-on-the-web/
- SVG export "exports strokes as fills", i.e. strokes are expanded geometry on export:
  https://help.figma.com/hc/en-us/articles/13402894554519-Export-formats-and-settings

---

## 3. Layout: frames, constraints, Auto Layout, grid

### 3.1 Constraints (non-auto-layout frames)

Source: https://help.figma.com/hc/en-us/articles/360039957734-Apply-constraints-to-define-how-layers-resize
- Horizontal: **Left, Right, Left and right** (stretches), **Center, Scale** (proportional: a 70 px layer in a 100 px frame becomes
  140 px at 200 px). Vertical: **Top, Bottom, Top and bottom, Center, Scale**. Default = Top + Left.
- Groups cannot be constrained (constraints apply to their children). Holding Cmd / Ctrl while resizing ignores constraints.
- "It's not possible to apply constraints to ... layers in an auto layout frame."

### 3.2 Auto Layout

- 2019 launch: core concepts of the CSS box model, specifically flexbox, added "directly into Figma":
  https://www.figma.com/blog/announcing-auto-layout/
- 2020 rewrite, *Behind the feature: the making of the new Auto Layout*,
  https://www.figma.com/blog/behind-the-feature-the-making-of-the-new-auto-layout/ :
  - principle: "Auto Layout should be a thoughtful subset of flexbox";
  - each axis is **Fixed / Hug contents / Fill container**; a frame cannot hug and fill on the same axis;
  - alignment moved to the **container** (a 2-D alignment control);
  - **the key engine change**: the first version laid out children, then containers. Stretch/fill makes children depend on parents,
    creating circular dependencies, so the new engine can "go back and forth between container and component to make sure all layout
    demands were met" (multi-pass resolve);
  - migrations preserved old documents' layout; the interaction was prototyped first "completely in HTML".
- Later CSS alignment (border-box sizing for fill children, gap never below zero):
  https://help.figma.com/hc/en-us/articles/42031586813719-Use-auto-layout-with-CSS-Flexbox-in-mind
- **Wrap** (horizontal and vertical flows move children to a new row/column when they no longer fit), **min / max width and height**
  on auto-layout frames and their children (usable with the other resizing options), and **Ignore auto layout** (formerly "absolute
  position") for a child that floats inside an auto-layout frame: https://help.figma.com/hc/en-us/articles/360040451373-Guide-to-auto-layout
  and the plugin property `layoutPositioning` https://www.figma.com/plugin-docs/api/properties/nodes-layoutpositioning/

### 3.3 Grid (Config 2025)

- Grid is a third auto-layout flow for two-dimensional layouts (galleries, bento boxes): rows and columns are **tracks**, row count
  defaults to **auto** (grows with cells), track size defaults to an even share of free space (1fr-like), per-track sizing, children
  set to Fill can take **column span / row span**: https://help.figma.com/hc/en-us/articles/31289469907863-Use-the-grid-auto-layout-flow
  and https://www.figma.com/blog/config-2025-recap/
- Plugin API: `gridColumnCount`, `gridRowSpan`, `gridAutoTracks`:
  https://developers.figma.com/docs/plugins/api/properties/nodes-gridautotracks/
- Launch-time limits per Figma's forum (not the help center): tracks could not hug contents, and grid containers had no min/max.
  Treat as possibly outdated.

---

## 4. Components, instances, variants, properties, variables, styles, libraries

- **Instances depend on their main component**, which may live on another page, and styles and variables work the same way; an
  instance's sublayers are **derived** = backing component + overrides, so Figma stopped materialising them at load for other pages:
  https://www.figma.com/blog/speeding-up-file-load-times-one-page-at-a-time/
- **Component properties** (https://help.figma.com/hc/en-us/articles/5579474826519-Explore-component-properties): **boolean**
  ("currently ... only support layer visibility"), **instance swap** (with **preferred instances** = a curated swap list), **text**
  (editable text content), **variant** (attributes of a component set, e.g. state/size; only on component sets, cannot be detached
  from a nested layer), and **slot** (an area where content can be added inside an instance). Changing a property's default only shows
  on instances that have **no override** of that property — i.e. overrides are stored as deltas over the main component.
- **Variables** (https://help.figma.com/hc/en-us/articles/14506821864087-Overview-of-variables-collections-and-modes): six types —
  color, number, string, boolean, plus timing and easing; a **collection** groups variables (up to 5,000 per collection) and its
  **modes** give one value per variable per mode (light / dark, languages); mode count depends on plan. Variables bind to "all kinds of
  design properties and prototyping actions", can reference (alias) other variables, can be **scoped** to where they may be used, and
  collections can be **extended** for multi-brand systems (https://help.figma.com/hc/en-us/articles/15339657135383-Guide-to-variables-in-Figma).
  Prototypes can use variables with **expressions** (string and math): https://help.figma.com/hc/en-us/articles/15253194385943-Use-expressions-in-prototypes
- **Styles vs variables**: styles are composite (e.g. a whole text style, effect stack); variables are single raw values that can
  switch by mode: https://help.figma.com/hc/en-us/articles/15871097384471-The-difference-between-variables-and-styles
- **Libraries**: publishing variables to team libraries is on paid plans (Professional, Education, Organization, Government,
  Enterprise) per the variables guide above. We did not find a primary source describing the library publish / accept-update protocol
  internals; the dependency mechanics above (QueryGraph edges via `componentID`, styles, variables) are the published part.

---

## 5. Prototyping, Dev Mode, export, plugins, widgets

### 5.1 Prototyping and Smart Animate

- Each connection carries animation settings: transition type, direction, **duration 1 ms - 10,000 ms**, easing (and spring):
  https://help.figma.com/hc/en-us/articles/360040522373-Prototype-animations
- **Smart Animate matches layers by name and by position in the hierarchy** (same name; same parent/grandparent depth). Text layers
  named explicitly must match by name; auto-named text matches by text style. Unchanged layers are not animated; drop/inner-shadow
  layers and shape-to-shape morphs fall back to dissolve:
  https://help.figma.com/hc/en-us/articles/360039818874-Smart-animate-layers-between-frames
- Prototype loading (*Incremental frame loading*, https://www.figma.com/blog/incremental-frame-loading/): load only the current screen
  and screens reachable by one interaction; query -> snapshot -> `changes` sync protocol; dependencies (component backings, styles,
  variables) subscribed transitively; unsubscribed nodes **evicted**; desktop prefetches in the background, mobile loads on navigation
  and evicts old screens; loads split into chunks to avoid UI lockups; Time to Interactive = page answers input within **50 ms**; work
  could not go to a worker because it needs main-thread state.

### 5.2 Dev Mode

- Inspect panel shows code snippets for the selection with language / unit settings:
  https://help.figma.com/hc/en-us/articles/15023202277399-Use-code-snippets-in-Dev-Mode ,
  https://help.figma.com/hc/en-us/articles/15023124644247-Guide-to-Dev-Mode
- **Codegen plugins** read the selection and return text rendered in the Inspect code section, no iframe needed:
  https://developers.figma.com/docs/plugins/working-in-dev-mode/ and https://www.figma.com/blog/figma-dev-mode-codegen-plugins/
- **Code Connect** maps Figma components to a team's real components so Inspect shows real code; CLI templates (`.figma.ts`, `npx
  figma connect publish`) map Figma properties to the component API: https://developers.figma.com/docs/code-connect/quickstart-guide/ ,
  https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect

### 5.3 Export

Source: https://help.figma.com/hc/en-us/articles/13402894554519-Export-formats-and-settings
- PNG (lossless, always with alpha), JPG (no transparency; default quality High), SVG (text exported as **outlines by default**,
  optional live text, strokes as fills, 1x only), PDF (**PDF 1.7**, 1x, text not editable, default Medium). Settings: scale
  multipliers, suffixes, color profile, resampling. Note: the server-side native renderer (section 1.3) is how the same engine can
  render without a browser.

### 5.4 The plugin sandbox

Source: *How to build a plugin system on the web and also sleep well at night*,
https://www.figma.com/blog/how-we-built-the-figma-plugin-system/ and *An update on plugin security*,
https://www.figma.com/blog/an-update-on-plugin-security/
- Rejected: plugins in a **null-origin iframe** only — everything becomes async message passing, and copying the document was too
  slow (one large design-system file took **14 s** to serialise before a plugin could start).
- Prototyped: a C interpreter (**Duktape**) compiled to wasm — on the main thread, no browser APIs by default, but no JIT, ES5 only,
  no devtools. QuickJS appeared months later with ES6.
- Shipped first: the **Realms shim** (`with` + Proxy whitelisting + a same-origin iframe for clean globals) on the main thread — JIT
  speed and devtools, but functions created outside the realm can leak through prototype chains, so all access goes through a small
  auditable ~500-line VM-style interface.
- Split: **document API in the main-thread sandbox** (live document, synchronous API, reuses layout/constraints logic) + **UI and
  network in a null-origin iframe**, joined by `postMessage`. Freezes accepted because plugins run only on explicit user action.
- Then: several Realms escape bugs were reported (no evidence of exploitation); on **25 Sep 2019** Figma switched to **QuickJS, "a
  JavaScript VM written in C and cross-compiled to WebAssembly"**. Reason: Realms runs trusted and untrusted code in the same VM, so
  objects can be confused across the boundary; with wasm the two sides have different object representations. Cost: slower for some
  plugins; kept anyway. A "swappable architecture" made the switch quick.

### 5.5 Widgets

- Widgets are on-canvas, shared objects; `useSyncedState(key, default)` is like `React.useState` but named and stored in the
  document, JSON-serialisable, shared across collaborators, re-renders on change, cannot be set during render; `useSyncedMap` for
  per-entry edits by different users; each user has their own undo stack over synced state:
  https://developers.figma.com/docs/widgets/api/properties/widget-usesyncedstate/ ,
  https://developers.figma.com/docs/widgets/widget-state-and-multiplayer/ , https://developers.figma.com/docs/widgets/undo-redo/
- Widget properties cannot be bound to variables:
  https://help.figma.com/hc/en-us/articles/15339657135383-Guide-to-variables-in-Figma

---

## 6. Published performance techniques

1. **No GC on the hot path**: one pre-allocated heap, 32-bit floats, big buffers outside the heap (IndirectBuffer).
   https://www.figma.com/blog/building-a-professional-design-tool-on-the-web/
2. **Retained GPU geometry, not immediate mode**: the reason given for rejecting Canvas2D is that it re-uploads geometry every frame.
   Same source.
3. **Tiles**: the renderer is tile-based (details unpublished). Same source.
4. **Batch GPU work**: one uniform buffer with encode-then-submit; reuse bind groups; batch draws into render passes; RenderBundles
   next. https://www.figma.com/blog/figma-rendering-powered-by-webgpu/
5. **Load less**: only the current page first; dependencies via an in-memory **QueryGraph** (read edges: instance -> component, styles,
   variables; write edges are mostly the inverse, plus implicit ones such as auto layout). Server sends each client only edits
   reachable from its subscribed pages; a **shadow mode** flagged any edit touching a node outside the computed write set (it found a
   missed cross-page recursive dependency of frame constraints + instances). Results: slowest 5 % of loads **33 % faster** despite files
   growing 18 %/year, **70 % fewer nodes in client memory**, **33 % fewer out-of-memory errors**.
   https://www.figma.com/blog/speeding-up-file-load-times-one-page-at-a-time/
6. **Start before asked**: the first GET tells the multiplayer server to start loading and decoding before the WebSocket opens
   (~300-500 ms off p75); **parallel decoding** using persisted raw offsets (> 40 % less decode time; serial was > 5 s for the largest
   files). Same source.
7. **Derive, don't store**: instance sublayers, layout, booleans and text layout are derived/cached data, computed lazily and skipped
   for what is not visible. Same source + https://www.figma.com/blog/incremental-frame-loading/
8. **Chunk main-thread work** so no single load locks the UI; **evict** what is not subscribed. https://www.figma.com/blog/incremental-frame-loading/
9. **Measure every pull request**: headless Chromium on GPU VMs per PR with a **20 % pass margin** (catches linear->quadratic, not noise),
   checks under **10 minutes**, dozens of stress scenarios (100 multiplayer editors; thousands of layers edited by 50 users; 5,000
   comment pins), p50/p90 FPS and frame lengths, plus a hardware lab of old MacBooks, Windows laptops and Chromebooks for bisecting.
   CPU-instruction counting was rejected (JIT variance; sometimes GPU- or IO-bound). https://www.figma.com/blog/keeping-figma-fast/
10. **Degrade gracefully at runtime**: WebGPU -> WebGL mid-session fallback + device blocklist by fallback rate.
    https://www.figma.com/blog/figma-rendering-powered-by-webgpu/

Not found in any primary source: hit-testing algorithm (spatial index type), incremental-layout algorithm details beyond "back and
forth between container and component", tile size, glyph cache design. Do not invent them.

---

## 7. How a browser-only JS / Canvas2D or WebGL editor for Hoola should copy these ideas

Constraints: no WASM toolchain, no npm build step, plain JS files served statically (like `server/app/static/console/*.js`).
Everything below is an adaptation of the published ideas, not Figma's code.

**Document model (copy almost exactly).**
- One flat `Map<id, {prop: value}>`; each node carries `parent` as **one property `{id, pos}`** where `pos` is a fractional-index
  string/number; children are found by sorting siblings by `pos` (insert = midpoint). Reparent = one property write = atomic.
- Every edit is `(id, prop, value)`. That gives undo (store old value), server sync (last-writer-wins per property, server orders),
  and cheap diffing for free. New features = new properties, never new structures.
- Keep **derived** data (layout boxes, flattened booleans, text line breaks, instance expansions) in a separate cache keyed by id with
  a dirty flag; never persist it. An instance = `{componentId, overrides:{path: {prop: value}}}`, expanded lazily on render.

**Dependencies (the QueryGraph idea, small).**
- Maintain reverse edges: component -> instances, variable/style -> users, auto-layout child -> parent. When a node changes, walk these
  edges to mark dirty exactly what must recompute. This is also what lets you load one page at a time later.

**Rendering.**
- Canvas2D is acceptable for a v1 if you stop doing what Figma said kills it: (a) cache each node's geometry as a `Path2D` built once
  and reused until the node is dirty; (b) render with **dirty rectangles** — union the old and new bounds of changed nodes and redraw
  only that clip; (c) for zoom/pan, render the scene into **tiles** (e.g. 256x256 `OffscreenCanvas` at the current zoom bucket) and
  composite tiles while panning, re-rendering only invalidated tiles, and blitting stale tiles scaled while a new zoom level renders.
- Move to WebGL only for the hot parts (many rectangles, image fills, blur) and keep a Canvas2D fallback that can be switched to at
  runtime if `webglcontextlost` fires — the same "fallback mid-session" pattern as WebGPU -> WebGL.
- Effects: implement blur via `ctx.filter = 'blur()'` into an offscreen layer (cache the result per node; background blur is the
  slowest thing, as Figma says), drop shadows via `shadowBlur`/offsets on the cached layer, blend modes via
  `globalCompositeOperation` (it covers multiply/screen/overlay/darken/lighten/color-dodge/... and hue/saturation/color/luminosity).
  "Pass through" vs "normal" = whether a group is drawn into its own offscreen layer (isolated) or straight onto the parent.
- Gradients: linear/radial native; conic via `createConicGradient` (now in all modern browsers). Dither large gradients with a tiny
  noise pattern overlay to avoid banding (Figma names dithering).
- Text: use the browser's own shaping via `ctx.fillText` / `measureText` (we cannot ship HarfBuzz without a toolchain). Accept that,
  like Figma warns, output may differ subtly from final code — but cache line-break results per (text, style, width), as Figma caches
  text layout. Only allow fonts loaded through `FontFace` so measurement is deterministic.

**Memory.** Use typed arrays (`Float32Array`) for vertex lists of vector networks and big point sets; avoid allocating per frame
(reuse scratch objects), the JS analogue of "the GC is never involved".

**Vector networks.** Store vertices + segments (each segment = two vertex ids + two handle offsets) + regions (lists of segment loops
with a `filled` flag). Draw each region with `fill('evenodd')` on its own loops so holes are explicit toggles, not winding accidents.
Booleans: start with Canvas2D compositing for display (`destination-out` for subtract, `source-in` for intersect, `xor` for exclude)
and only compute real geometry on Flatten/export.

**Layout.** Implement Auto Layout as Figma did — a **subset of flexbox**, not all of it: direction, gap, padding, alignment on the
container, per-axis Fixed / Hug / Fill, min/max, wrap, and an "ignore auto layout" child flag. Use two passes and iterate (measure
hug sizes bottom-up, then distribute fill sizes top-down, repeat until stable or 3 rounds) — that is the "back and forth" fix for
fill-inside-hug. Constraints (left/right/both/center/scale) apply only to children of non-auto-layout frames. Grid later, as tracks
with auto rows and spans. Because our output is HTML, keep the mapping 1:1 with CSS flex/grid so "Dev Mode" export is trivial.

**Components, variables, modes.** Variables = `{id, type, valuesByMode}`; a property value may be `{alias: varId}`; resolve at render
with the frame's current mode. Component properties = boolean (visibility), text, instance swap (with preferred list), variant. A
default change affects only instances without an override of that property.

**Prototyping.** Smart Animate = match layers between two frames by **name + hierarchy path**, tween numeric props (x, y, w, h,
opacity, rotation, corner radius, fill colour), dissolve everything else; drive with `requestAnimationFrame` and a cubic-bezier/
spring easing function.

**Plugins / AI edits.** Do not run untrusted code in the page's own JS realm (Figma's Realms lesson). Options without a toolchain: a
sandboxed `<iframe sandbox="allow-scripts">` (null origin) speaking a small, audited `postMessage` command API of `(id, prop, value)`
edits — accept that it is async, and avoid Figma's 14 s cost by **never copying the document**, only answering targeted queries. For
Hoola, server-side model edits should go through the same property-write API, validated against a whitelist.

**Export.** SVG = walk the tree emitting `<path>`/`<text>` (strokes expanded only if needed); PNG = render to an offscreen canvas at
1x/2x/3x and `toBlob`; PDF = keep using the server's existing HTML->PDF path rather than writing a PDF writer in the browser.

**Performance discipline.** Add a tiny in-page benchmark (a scripted pan/zoom over 5,000 nodes, record p50/p90 frame time via
`performance.now()`), run it in headless Chromium in CI with a generous pass margin (Figma uses 20 %) so only big regressions fail;
chunk any load or import longer than ~16 ms with `setTimeout`/`requestIdleCallback` so input stays under 50 ms; load one page of a
document first and fetch the rest on demand.
