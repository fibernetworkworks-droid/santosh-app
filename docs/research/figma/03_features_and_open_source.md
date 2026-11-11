# 03 — Feature inventory of a 2026 design tool + the open-source shelf

Research for **Hoola Design**, an original product. This file lists what a professional
canvas design tool does today, using Figma Design as the reference point, so we can decide
what to build first. It copies no Figma branding, names, icons or UI. Figma is named only to
cite sources. Every licence verdict below comes from the project's own repository on
11 Nov 2026. Re-check a licence before any code is vendored.

Read this with `00`–`02` in this folder, if they exist. Tier legend:

- **MVP**: a design tool without it is not usable.
- **v2**: expected by working designers within the first year.
- **Adv**: advanced, team-scale or a separate product.

---

## Part A — Feature inventory

Main sources: the Figma Help Center (https://help.figma.com), the Config 2025 page
(https://help.figma.com/hc/en-us/articles/30965205437975-What-s-new-from-Config-2025), the
Config 2025 forum post
(https://forum.figma.com/product-updates-3/let-s-talk-about-the-new-features-we-announced-at-config-2025-40301),
the Config 2026 recap (https://www.figma.com/blog/config-2026-recap/) and the Config 2026
forum list (https://forum.figma.com/product-updates-3/everything-announced-at-config-2026-55221).

Config 2024 brought a redesigned interface ("UI3"), the first AI features (later called
First Draft, visual search, rename layers, AI text tools), Slides and Code Connect in Dev
Mode. Config 2025 brought Sites, Make, Draw, Buzz and Grid auto layout. Config 2026 (23–25
June) brought code layers on the canvas, built-in Motion, shader fills and effects,
generative plugins, Weave tools and an agent. Most of these roll out in phases.

### A1. Canvas and core tools

| Feature | What it does | Tier |
|---|---|---|
| Infinite canvas, zoom and pan | Unbounded 2-D space. Zoom about 2%–25,600%, zoom to fit or to the selection, pixel preview, pixel grid at high zoom | MVP |
| Move / select tool (V) | Click and marquee select, shift-add, deep select (cmd-click) through groups, drag to move, nudge with the arrow keys (shift = 10 px) | MVP |
| Scale tool (K) | Scales a layer and its children together: stroke, text size and effects grow in proportion | v2 |
| Frame tool (F/A) | Containers with fills, clipping, layout and device presets (phone, desktop, paper, social). Frames can nest | MVP |
| Section tool | Large labelled areas that group frames on the canvas. They also mark "ready for dev" status | v2 |
| Shapes (R, O, L, shift-L, polygon, star) | Rectangle, ellipse with arc and ratio, line, arrow, polygon with a side count, star with points and ratio | MVP |
| Pen tool (P) | Bézier paths. Vector networks (one point can join more than two segments), bend handles, close a path, boolean-friendly | MVP |
| Pencil (shift-P) | Freehand strokes simplified into vectors | v2 |
| Vector edit mode | Edit points and handles, point types (mirrored or asymmetric), paint bucket to fill regions of a vector network | v2 |
| Draw tools (2025) | Brushes, textured strokes, variable width, stroke profiles, shape builder and illustration tools inside the design tool | Adv |
| Text tool (T) | Point text and fixed-width text, auto width and auto height, rich spans (mixed styles), lists, links, OpenType features, vertical trim | MVP |
| Hand tool (H / space) | Pan while held | MVP |
| Comment tool (C) | Pin a thread to a point or area. Threads, @mentions, emoji, resolve | v2 |
| Image fill and place image | Drop or paste images. Fill, fit, crop and tile modes, simple image adjustments | MVP |
| Boolean operations | Union, subtract, intersect and exclude, kept live and non-destructive. Flatten, outline stroke | v2 |
| Mask | Use a layer as an alpha or vector mask for the layers above it | v2 |
| Smart selection / tidy up | Equal spacing handles on a selection, swap positions, reorder in a grid | v2 |
| Measure and red lines | Alt-hover shows the distances between layers | MVP |
| Snapping and smart guides | Snap to edges, centres, the pixel grid and equal spacing | MVP |
| Rulers and guides (shift-R) | Drag guides from the rulers onto frames | v2 |
| Copy / paste as | Copy as SVG, PNG or CSS. Paste and replace, paste over selection | v2 |
| Find and replace (text, layers) | Search the layer tree, replace text across a file | v2 |

### A2. Layers panel and pages

| Feature | What it does | Tier |
|---|---|---|
| Layers tree | Shows the scene graph as a tree. Drag to reorder or reparent, rename, lock, hide, expand and collapse, layer icons by type | MVP |
| Groups (cmd-G) | Plain grouping with no layout. Ungroup with shift-cmd-G | MVP |
| Pages | Many pages per file, each its own canvas. Reorder, duplicate, divider pages | MVP |
| Multi-select editing | Edit the shared properties of mixed selections, shown as "Mixed" values | MVP |
| Select matching layers | Select every layer that shares a property, or every instance of a component | v2 |
| AI rename layers | Generate meaningful layer names | Adv |

### A3. Properties panel (right side)

The sections a single selection can show:

| Section | What it does | Tier |
|---|---|---|
| Position and size | X, Y, W, H, rotation, corner radius (per corner, corner smoothing), constrain proportions. Number fields take arithmetic and scrub | MVP |
| Layout (auto layout) | Direction, gap, padding, alignment, wrap, hug / fill / fixed sizing, min and max, absolute position for one child | MVP |
| Constraints | How a child resizes with a non-auto-layout parent: left, right, left and right, centre, scale | MVP |
| Layer | Blend mode, opacity, pass-through | MVP |
| Fill | Several fills: solid, linear / radial / angular / diamond gradient, image, video. Shader fills arrived in 2026 | MVP (solid, linear), v2 (rest) |
| Stroke | Several strokes, inside / centre / outside, per-side weights, dashes, caps and joins, arrowheads | MVP |
| Effects | Drop shadow, inner shadow, layer blur, background blur, noise and texture (2025), shader effects (2026) | v2 |
| Selection colours | Every colour in the selection in one place, editable together | v2 |
| Layout guides / grids | Column, row and square grids on frames, with styles | v2 |
| Export | Export settings per layer (see A10) | MVP |
| Prototype tab | Interactions and flows (see A8) | v2 |

### A4. Auto layout, constraints and grids

| Feature | What it does | Tier |
|---|---|---|
| Auto layout (shift-A) | Flexbox-like stacks: horizontal, vertical, wrap, gap, padding, alignment | MVP |
| Hug / fill / fixed sizing | A child's size follows its content, fills the parent, or stays fixed. Min and max widths | MVP |
| Spacing "auto" (space-between) | Spreads children apart evenly | MVP |
| Absolute position inside auto layout | Takes one child out of the flow, for things like badges | v2 |
| Canvas stacking / text baseline alignment | Controls z-order inside a stack and aligns text on its baseline | v2 |
| Grid auto layout (2025) | CSS-grid-like layout: rows and columns, a child can span cells | v2 |
| Constraints | Anchors for responsive resizing outside auto layout | MVP |
| Layout grids | Visual column grids that children can snap to. They do not change layout | v2 |

### A5. Components, variants and properties

| Feature | What it does | Tier |
|---|---|---|
| Component (main) and instance | One main definition and many linked copies. Edits to the main spread to every instance | MVP |
| Overrides | Change text, fills or a nested instance on an instance while keeping the link. "Reset" brings back the main's values | MVP |
| Detach instance | Breaks the link and turns the instance into plain layers | MVP |
| Variants / component sets | Group components by properties, for example Size=S/M/L and State=Hover | v2 |
| Component properties | Boolean (show/hide), text, instance-swap and variant properties shown on the instance | v2 |
| Preferred values / slots | A curated list of swaps for nested instances. Flexible slot content came later | Adv |
| Nested instances exposed | Shows a child instance's properties on the parent instance | Adv |
| Component descriptions and links | Documentation and links to docs on a component | v2 |
| Swap instance / assets panel | Browse components and drag them in or swap them | v2 |

### A6. Variables, modes and styles

| Feature | What it does | Tier |
|---|---|---|
| Styles | Named colour, text, effect and grid styles you can share | v2 |
| Variables | Typed tokens (colour, number, string, boolean) in collections, with aliases | v2 |
| Modes | Each variable gets one value per mode, for example light/dark or brand A/B. A frame chooses its mode | v2 |
| Scoping | Limits where a variable can be applied, such as fills only or gap only | Adv |
| Variables in prototypes | Variables and conditionals drive the logic of an interactive prototype | Adv |
| Code syntax | A variable can carry its token name for each platform (CSS, iOS, Android) | Adv |
| Extended collections (2025) | A brand collection that inherits from a base and overrides a few values | Adv |
| Import / export tokens | JSON tokens in the W3C Design Tokens format | v2 |

### A7. Libraries

| Feature | What it does | Tier |
|---|---|---|
| Publish a library | Turns a file's components, styles and variables into a team library | v2 |
| Enable a library / assets panel | Use a published library in other files | v2 |
| Update review | When a library changes, files that use it get "Updates available" and can accept or reject per item | v2 |
| Library analytics | Shows how often components are used and detached | Adv |
| Community / UI kits | Public files and libraries anyone can duplicate | Adv |

### A8. Prototyping

| Feature | What it does | Tier |
|---|---|---|
| Connections | Triggers (click, hover, press, drag, key, delay, mouse enter or leave) lead to actions (navigate, open overlay, swap, back, scroll to, open link, set variable, conditional) | v2 |
| Transitions | Instant, dissolve, move in/out, push, slide, Smart Animate (matches layers by name), easing and springs | v2 |
| Flows and starting points | Several named flows per page | v2 |
| Overlays | Modals and dropdowns with position, background and close on outside click | v2 |
| Scroll behaviour | Overflow scroll, sticky and fixed elements | v2 |
| Interactive components | Variant-to-variant interactions inside a component, for example a hover state | Adv |
| Presentation / prototype viewer and mirror app | Plays the prototype in a browser or on a phone | v2 |
| Video and audio in prototypes | Video fills and on-click sound | Adv |
| Motion (2026) | A built-in timeline: position, opacity, scale, rotation, fade and easing | Adv |

### A9. Collaboration

| Feature | What it does | Tier |
|---|---|---|
| Real-time multiplayer | Shows every editor's live cursor and selection, follow mode (spotlight), names on cursors | MVP for a cloud product, otherwise v2 |
| Comments | Threaded, pinned to a spot, @mentions, notifications, resolve, filters | v2 |
| Version history | Autosaved checkpoints, named versions, restore, view an old version, duplicate it | MVP (autosave + restore) |
| Branching and merging | Branch a file, review the diff and merge back, with conflicts settled per layer | Adv |
| Sharing and permissions | Link sharing (view, edit, prototype only), teams, projects, seats | MVP |
| Audio and chat on the canvas | Cursor chat, stamps, voice | Adv |
| Observation mode / spotlight | Makes everyone follow the presenter | v2 |

### A10. Handoff: Dev Mode and export

| Feature | What it does | Tier |
|---|---|---|
| Export | PNG, JPG, SVG and PDF, per layer, with scale suffixes (@2x), slices and batch export | MVP |
| Inspect panel | CSS, iOS (SwiftUI) or Android (Compose) snippets, measurements, assets and variables used | v2 |
| Ready-for-dev status and compare changes | Marks sections ready for dev and shows a diff since the last time they were ready | Adv |
| Code Connect | Maps a design component to the code component in a real repo, so Dev Mode shows the real usage | Adv |
| Annotations and measurements | Notes and spec lines that designers pin for developers | v2 |
| Dev Mode plugins and IDE extension | Jira and GitHub links, and the inspect panel inside VS Code | Adv |
| MCP server (2025+) | Agents read design context and write designs (Dev Mode and remote MCP) | Adv |
| Code layers (2026) | Real code components on the canvas. Clone a repo, edit, sync back | Adv |

### A11. Extensibility

| Feature | What it does | Tier |
|---|---|---|
| Plugins | Sandboxed JavaScript gets the document API (node tree) and an iframe UI. Run once or keep a panel open | v2 |
| Widgets | Interactive objects on the canvas that everyone shares (counters, voting, tables). Built with a React-like API | Adv |
| REST API and webhooks | Read files, images and comments, and receive change events | v2 |
| Generative plugins (2026) | Plugins built from a prompt and run with AI | Adv |

### A12. AI features (2024–2026)

| Feature | What it does | Tier |
|---|---|---|
| First Draft (formerly "Make Designs") | Turns a prompt into an editable starting layout from library-like kits | Adv |
| Make (2025) | Prompt-to-code app or prototype builder that can start from a design | Adv |
| Visual / asset search | Search libraries by image or by meaning | Adv |
| Text tools | Rewrite, shorten, translate, add realistic content to many layers | v2 |
| Image tools | Generate images, edit them, remove backgrounds, boost resolution | v2 |
| Rename layers / add interactions | Automatic housekeeping | Adv |
| Agent (2026) | An assistant on the canvas that works through several steps. Weave tools for image and video generation | Adv |

### A13. Sister products (same platform, separate editors)

| Product | What it does | Tier for Hoola |
|---|---|---|
| Whiteboard (FigJam) | Sticky notes, connectors, shapes, stamps, timers, voting, templates, diagrams | Adv (consider Excalidraw instead, see B) |
| Slides | Slide decks with layouts, themes, presenter view and live polls | Adv |
| Sites (2025) | Publishes responsive websites from frames, with breakpoints, interactions, a CMS and code components | Adv. Hoola already has Web Studio (v0.650+) |
| Buzz (2025) | Brand templates at scale for marketers: bulk-fill from a sheet | v2. Fits Hoola's Create Studio |
| Make (2025) | Prompt to app | Hoola already has App Studio and Lovable plans |

### A14. Keyboard shortcuts essentials (the set users expect)

Hoola should keep these key conventions because they are industry standard across design
tools. We use the conventions only, not anyone's UI.

| Action | Keys |
|---|---|
| Move / Frame / Rect / Ellipse / Line / Arrow | V / F (A) / R / O / L / shift-L |
| Pen / Pencil / Text / Hand / Comment | P / shift-P / T / H or space / C |
| Group / Ungroup / Frame selection | cmd-G / shift-cmd-G / opt-cmd-G |
| Auto layout / Remove it | shift-A / opt-shift-A |
| Create component / Detach | opt-cmd-K / opt-cmd-B |
| Duplicate / Copy / Paste over / Paste to replace | cmd-D / cmd-C / shift-cmd-V / shift-cmd-R |
| Zoom in, out / 100% / fit all / fit selection | +, − / shift-0 / shift-1 / shift-2 |
| Bring forward / to front / Send back / to back | cmd-] / opt-cmd-] / cmd-[ / opt-cmd-[ |
| Align left / centre / right / top / middle / bottom | opt-A / opt-H / opt-D / opt-W / opt-V / opt-S |
| Hide / Lock | shift-cmd-H / shift-cmd-L |
| Rename / Select all / Deep select | cmd-R / cmd-A / cmd-click |
| Show/hide UI / Rulers / Pixel grid | cmd-\ / shift-R / shift-' |
| Quick actions / command palette | cmd-/ (or cmd-K style) |
| Undo / Redo | cmd-Z / shift-cmd-Z |

### A15. Proposed MVP cut for Hoola Design

- An infinite canvas with pages and a layers tree.
- Frame, rectangle, ellipse, line, pen, text and image tools.
- Select, move, resize and rotate with snapping, measuring and multi-select.
- A properties panel with position, layout (auto layout with hug/fill/fixed), constraints,
  fill (solid, linear), stroke, opacity and export.
- Components with instances and overrides.
- Autosave, version restore and link sharing.
- PNG, SVG and PDF export.
- The shortcut set above.

**v2** adds variants and properties, styles, then variables and modes, libraries, comments,
multiplayer, prototyping, boolean operations, effects, an inspect panel and plugins.
**Advanced** covers everything else.

Hoola-specific advantages to plan in early:

- AI layout generation that uses the house design kit (`fe-ui-kit`).
- Export straight into Web Studio and App Studio.
- Bulk brand templates in the Buzz style for Create Studio.

---

## Part B — The open-source shelf: what to learn and what can be reused

The rule that matters for a commercial, closed-source SaaS:

- **MIT, Apache-2.0, BSD, ISC and CC0** can be reused. Keep the notice. Apache-2.0 adds a
  NOTICE file and a patent grant.
- **MPL-2.0** is file-level copyleft. Changes to *those files* must be published, but the
  rest of our code can stay closed.
- **AGPL-3.0** network copyleft forces publishing our whole server if we link it. Avoid it.
- **Source-available** licences, such as tldraw's, are not open source for production use.
  Avoid them unless we pay.

### B1. Full editors

**Penpot**: https://github.com/penpot/penpot

- **Licence:** MPL-2.0, copyright Kaleidos.
- **Architecture:** A Clojure (JVM) backend on PostgreSQL with Redis for real-time
  messaging, and a ClojureScript frontend. Rendering has historically been SVG/DOM: every
  shape is an SVG element. The repo now has a `render-wasm` crate, a Rust renderer built
  with Emscripten on Skia (through rust-skia). It renders to a canvas with tiling, viewport
  culling and tile caching, and gets document state from the CLJS side as binary data. It
  shipped behind a feature flag through 2025 (talk:
  https://www.wearedevelopers.com/videos/1353/rendering-design-software-in-the-browser-at-penpot).
  Separate services handle export (headless browser), media, plugins and an MCP server.
  Penpot's file format is open, and design is stored as SVG/CSS-native concepts: flex and
  grid layout map directly to CSS.
- **Lessons:**
  - (a) SVG-in-DOM rendering stops scaling at a few thousand shapes. That is why they moved
    to a WASM and GPU renderer. Start Hoola on canvas or WebGL, not on the SVG DOM.
  - (b) Mapping layout one-to-one onto CSS flex and grid makes handoff trivial.
  - (c) A plugin API with a sandbox and a separate exporter service is a clean split.
- **Reusable commercially?** **Partly.** MPL lets us *use and change* files if we publish
  our changes to those files. Clojure does not fit our Python/JS stack, so treat Penpot as a
  **reference architecture**, not a code donor. Self-hosting Penpot unmodified beside Hoola
  is allowed.

**Graphite**: https://github.com/GraphiteEditor/Graphite

- **Licence:** MIT or Apache-2.0, our choice. Some files may carry other terms, so check
  each file.
- **Architecture:** A Rust procedural graphics engine compiled to WASM for the web editor,
  with a desktop build. Every tool is a front end over a node-graph document, which makes
  editing non-destructive. It is built more like a game engine than a classic app.
- **Lessons:** Non-destructive, node-based history and effects. A Rust/WASM core with a thin
  web UI.
- **Reusable commercially?** **Yes.** It is permissive, so crates such as the vector and
  path maths can be lifted with attribution. It is still young (alpha), so pin a commit.

**Excalidraw**: https://github.com/excalidraw/excalidraw

- **Licence:** MIT.
- **Architecture:** A React and TypeScript whiteboard drawn on canvas 2D through Rough.js.
  The scene is a flat element array with version and versionNonce on each element, which
  makes reconciliation for collaboration simple. Collaboration uses an end-to-end-encrypted
  relay. The `@excalidraw/excalidraw` npm package can be embedded.
- **Lessons:** The per-element version-plus-nonce merge is a cheap alternative to a full
  CRDT for whiteboards. Files are plain JSON.
- **Reusable commercially?** **Yes.** It is the obvious base for a whiteboard-style Hoola
  board, embedded as is.

**tldraw**: https://github.com/tldraw/tldraw (licence:
https://github.com/tldraw/tldraw/blob/main/LICENSE.md)

- **Licence:** The **tldraw licence** (source-available, not OSI).
  - Free to use in development, testing and staging.
  - **Production use needs a commercial agreement and a licence key.** The software checks
    the key, detects the environment, can send usage data, and makes sure a watermark is
    shown. One trial is allowed per business unit.
- **Architecture:** A React-rendered infinite canvas with a reactive signals store (records
  with migrations), a shape-utility class per shape type, a sync server package, and DOM/SVG
  rendering that culls shapes outside the view.
- **Lessons:** Its record store with schema migrations and its shape-util pattern are
  excellent designs to *learn from*.
- **Reusable commercially?** **No, unless we pay.** Do not vendor or fork it into Hoola.
  Copying its ideas is fine, copying its code is not.

**Plasmic**: https://github.com/plasmicapp/plasmic

- **Licence:** **MIT for everything outside `platform/`**: loaders, `@plasmicapp/*` and
  `@plasmicpkgs/*`. **AGPL for `platform/`**, which is the visual builder (Studio) and its
  server.
- **Architecture:** A visual React page builder. Code components are registered with
  `registerComponent`. Pages render through framework loaders from a CDN, or as generated
  React code. Publishing fires webhooks or ISR.
- **Lessons:** The "register your real code components so the canvas can use them" pattern
  is the same idea as code layers and Code Connect.
- **Reusable commercially?** The **loaders and SDK: yes (MIT)**. The **Studio/platform: no**,
  because AGPL would infect our server.

**Onlook**: https://github.com/onlook-dev/onlook

- **Licence:** Apache-2.0.
- **Architecture:** "Cursor for designers." It loads a Next.js + Tailwind project into a web
  container, shows its preview in an iframe, and instruments the code so every DOM element
  maps to a source location. Visual edits are written back into the code, and an AI chat
  edits the code through tools.
- **Lessons:** This is exactly the pattern Hoola's Web Studio "visual edit" (v0.295) and
  the planned React App Engine need: element-to-source mapping.
- **Reusable commercially?** **Yes**, with the NOTICE and the patent terms. It is the best
  donor for design-to-code editing.

### B2. Rendering libraries

| Library | Licence | Architecture | Reusable commercially |
|---|---|---|---|
| **Konva** (https://github.com/konvajs/konva) | MIT | A canvas-2D scene graph (Stage > Layer > Group > Shape) with its own hit canvas for events, transformer handles, and React/Vue bindings | Yes. Good for a fast first MVP, but slows past about 10k nodes with no WebGL |
| **Fabric.js** (https://github.com/fabricjs/fabric.js) | MIT | A canvas-2D object model with interactive controls, SVG import/export and JSON serialisation | Yes. Its SVG round-trip is its strength; its layout model is weak |
| **Paper.js** (https://github.com/paperjs/paper.js) | MIT | A vector-graphics scripting framework with a strong Bézier and path-boolean engine (unite, subtract, intersect) | Yes. The **path boolean ops and curve maths** are the reusable gem, even with a different renderer |
| **CanvasKit (Skia WASM)** (https://skia.org/docs/user/modules/canvaskit/) | BSD-3 | Google's Skia compiled to WASM with WebGL. The renderer class that Penpot's new engine and Figma-style tools use | Yes. The serious long-term renderer: text shaping, paths and effects at GPU speed |

### B3. Collaboration and ordering primitives

| Library | Licence | What it is | Reusable commercially |
|---|---|---|---|
| **Yjs** (https://github.com/yjs/yjs) | MIT | A fast operation-based CRDT (Y.Map, Y.Array, Y.Text), with awareness for cursors and providers (websocket, webrtc, IndexedDB). It has a mature ecosystem, and pycrdt / y-py let Python servers speak it | Yes. **Recommended** for Hoola multiplayer. A Python server can hold the document through `pycrdt` |
| **Automerge** (https://github.com/automerge/automerge) | MIT | A JSON-like CRDT with a Rust core, full history, branching and merging, and compact binary storage. automerge-repo handles sync | Yes. A better fit if **branching and merging plus history** matter more than raw speed |
| **fractional-indexing** (https://github.com/rocicorp/fractional-indexing) | CC0 | `generateKeyBetween(a, b)` gives string keys that sort between two keys. This is how layer z-order and child order work under concurrent edits without renumbering | Yes, as public domain. There is also a Python port (`fractional-indexing` on PyPI, CC0) |

The collaboration approach that design tools have described publicly fits Hoola well:

- The server is the authority, with properties as last-writer-wins per (object, property).
- Ordering inside a parent uses fractional indices.
- Reparenting is checked on the server to stop cycles.

Yjs can be used for the hard parts, mainly text, or the simple model can be built directly.
Either way a CRDT is optional. A central server with LWW registers is simpler and is the
right first step.

### B4. Verdict table

| Project | Licence | Reuse in closed Hoola Design? | Use it for |
|---|---|---|---|
| Penpot | MPL-2.0 | Partly (publish changes to its files) | Reference architecture, CSS-native layout model, render-wasm study |
| Graphite | MIT/Apache-2.0 | Yes | Node-graph ideas, Rust vector maths |
| Excalidraw | MIT | Yes | Whiteboard mode, embedded as is |
| tldraw | tldraw licence (key + watermark, paid for production) | **No** (unless licensed) | Study the patterns only |
| Plasmic | MIT outside `platform/`, AGPL `platform/` | SDK yes, Studio **no** | The code-component registration pattern |
| Onlook | Apache-2.0 | Yes | Element-to-source visual editing |
| Konva | MIT | Yes | Fast MVP canvas |
| Fabric.js | MIT | Yes | SVG import/export |
| Paper.js | MIT | Yes | Boolean ops and Bézier maths |
| CanvasKit/Skia | BSD-3 | Yes | Production GPU renderer |
| Yjs | MIT | Yes | Multiplayer and text CRDT |
| Automerge | MIT | Yes | History, branches, merges |
| fractional-indexing | CC0 | Yes | Layer ordering |

**Suggested stack to try first:**

- A TypeScript document model: a flat map of nodes with a parent id and a fractional index.
- A canvas-2D renderer (Konva or our own), with a planned move to CanvasKit once files grow
  past about 5–10k layers.
- Paper.js maths for booleans.
- Auto layout as our own flex/grid solver that matches CSS, following Penpot's lesson.
- A FastAPI websocket server with LWW per property, plus Yjs (pycrdt) only for rich text.
- Excalidraw embedded for a whiteboard mode.
- Onlook's mapping ideas for "edit the real code".
- Never tldraw code without a paid licence.

---

## Caveats

- The tier guesses are judgement, not measurements.
- Some 2026 items are in phased rollout according to Figma's own pages. They are listed from
  the announcement pages, not from use.
- The Penpot render-wasm status beyond 2025 was not confirmed in this pass. Check Penpot's
  release notes.
- Graphite says some files carry other terms. Check each file before lifting code.
- The Python CRDT/fractional ports are named from memory. Verify them on PyPI before use
  (house rule: `prog-library-registry`).
