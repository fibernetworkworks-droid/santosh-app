/* HOOLA DESIGN - the WebGL2 tile renderer (docs/HOOLA_DESIGN_PLAN.md section 8, D9a). Same HD.render contract:
   hd-render.js stays the one renderer and calls in here, through HD.render.init, when WebGL2 is there and the setting
   (localStorage 'hd.renderer' = 'gl' | '2d' | 'auto', default auto) allows it.
   - The visible world at a zoom is a grid of TILES (256 x 256 device pixels); each tile is one layer of a WebGL2
     texture array. A frame = ONE instanced draw call that puts the tiles on the screen, so a pan over tiles already made
     costs one draw call and no painting at all.
   - Tiles are kept per scale ("level"). While a zoom moves, the nearest levels are shown scaled and tiles are made at a
     power-of-two bucket; when it rests the exact level is made, so text is as crisp as Canvas2D.
   - What a tile shows is painted by hd-render.js's OWN Canvas2D code (HD.render's tilePaint: paints, effects, masks,
     booleans, text, images), into a small canvas, then uploaded: the pixels are the Canvas2D pixels. A tile that holds
     only plain shapes (solid rects / rounded rects / ellipses, no stroke or effect) is drawn by the GPU straight into its
     layer instead (instanced quads, analytic coverage), within a small tolerance of the Canvas2D picture.
   - Only tiles that changed are made again: the store's change events give the old + new world box of every changed
     node; a visible tile repaints only the part that changed. LRU texture budget (256 MB), a time budget per frame.
   - Lost context -> hd-render.js goes back to Canvas2D at once and stays there for the session.
   Plain browser JS, no dependencies, no eval. The only element made is a <canvas>. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const TS = 256;                                   /* tile size, device pixels */
  const TILE_BYTES = TS * TS * 4;
  const SOFTWARE = /swiftshader|llvmpipe|softpipe|software rasterizer|microsoft basic render/i;
  const now = () => performance.now();

  const VS_COMP = '#version 300 es\n' +
    'in vec4 b0; in vec4 b1; in vec4 b2;\n' +
    'uniform vec2 uView;\n' +
    'out vec2 vSrc; flat out float vLayer; flat out float vExact;\n' +
    'void main() {\n' +
    '  vec2 k = vec2(float(gl_VertexID & 1), float(gl_VertexID >> 1));\n' +
    '  vec2 p = mix(b0.xy, b0.zw, k);\n' +
    '  vSrc = mix(b1.xy, b1.zw, k); vLayer = b2.x; vExact = b2.y;\n' +
    '  gl_Position = vec4(p.x / uView.x * 2.0 - 1.0, 1.0 - p.y / uView.y * 2.0, 0.0, 1.0);\n' +
    '}\n';
  const FS_COMP = '#version 300 es\n' +
    'precision highp float; precision highp sampler2DArray;\n' +
    'uniform sampler2DArray uTex; uniform float uTS;\n' +
    'in vec2 vSrc; flat in float vLayer; flat in float vExact;\n' +
    'out vec4 o;\n' +
    'void main() {\n' +
    '  if (vExact > 0.5) o = texelFetch(uTex, ivec3(clamp(ivec2(floor(vSrc)), ivec2(0), ivec2(int(uTS) - 1)), int(vLayer)), 0);\n' +
    '  else o = texture(uTex, vec3(vSrc / uTS, vLayer));\n' +
    '}\n';
  /* the plain shapes, drawn into one tile layer: a0..a1 = device -> local matrix + box size, a2 = corner radii (or, for
     kind 0, the upright device rect), a3 = premultiplied colour, a4 = clip rect, a5 = the quad, a6 = kind + scale */
  const VS_SHAPE = '#version 300 es\n' +
    'in vec4 a0; in vec4 a1; in vec4 a2; in vec4 a3; in vec4 a4; in vec4 a5; in vec4 a6;\n' +
    'uniform float uTS;\n' +
    'out vec4 v0; out vec4 v1; out vec4 v2; out vec4 v3; out vec4 v4; flat out float vKind; flat out float vScale;\n' +
    'void main() {\n' +
    '  vec2 k = vec2(float(gl_VertexID & 1), float(gl_VertexID >> 1));\n' +
    '  vec2 p = mix(a5.xy, a5.zw, k);\n' +
    '  v0 = a0; v1 = a1; v2 = a2; v3 = a3; v4 = a4; vKind = a6.x; vScale = a6.y;\n' +
    '  gl_Position = vec4(p / uTS * 2.0 - 1.0, 0.0, 1.0);\n' +
    '}\n';
  const FS_SHAPE = '#version 300 es\n' +
    'precision highp float;\n' +
    'in vec4 v0; in vec4 v1; in vec4 v2; in vec4 v3; in vec4 v4; flat in float vKind; flat in float vScale;\n' +
    'out vec4 o;\n' +
    'float cov(float lo, float hi, float x) { return clamp(min(x + 0.5, hi) - max(x - 0.5, lo), 0.0, 1.0); }\n' +
    'void main() {\n' +
    '  vec2 fc = gl_FragCoord.xy;\n' +
    '  float c;\n' +
    '  if (vKind < 0.5) c = cov(v2.x, v2.z, fc.x) * cov(v2.y, v2.w, fc.y);\n' +
    '  else {\n' +
    '    vec2 p = vec2(v0.x * fc.x + v0.z * fc.y + v1.x, v0.y * fc.x + v0.w * fc.y + v1.y);\n' +
    '    vec2 hs = v1.zw * 0.5; vec2 q = p - hs; float d;\n' +
    '    if (hs.x <= 0.0 || hs.y <= 0.0) discard;\n' +
    '    if (vKind < 1.5) {\n' +
    '      float r = q.x < 0.0 ? (q.y < 0.0 ? v2.x : v2.w) : (q.y < 0.0 ? v2.y : v2.z);\n' +
    '      vec2 e = abs(q) - hs + r;\n' +
    '      d = (length(max(e, 0.0)) + min(max(e.x, e.y), 0.0) - r) * vScale;\n' +
    '    } else {\n' +
    '      vec2 u = q / hs; float f = dot(u, u) - 1.0; vec2 g = 2.0 * q / (hs * hs);\n' +
    '      d = f / max(length(g), 1e-6) * vScale;\n' +
    '    }\n' +
    '    c = clamp(0.5 - d, 0.0, 1.0);\n' +
    '  }\n' +
    '  c *= cov(v4.x, v4.z, fc.x) * cov(v4.y, v4.w, fc.y);\n' +
    '  if (c <= 0.0) discard;\n' +
    '  o = v3 * c;\n' +
    '}\n';

  function compile(g, vs, fs) {
    const mk = (type, src) => { const s = g.createShader(type); g.shaderSource(s, src); g.compileShader(s); if (!g.getShaderParameter(s, g.COMPILE_STATUS) && !g.isContextLost()) throw new Error('shader: ' + g.getShaderInfoLog(s)); return s; };
    const p = g.createProgram();
    g.attachShader(p, mk(g.VERTEX_SHADER, vs)); g.attachShader(p, mk(g.FRAGMENT_SHADER, fs));
    g.linkProgram(p);
    if (!g.getProgramParameter(p, g.LINK_STATUS) && !g.isContextLost()) throw new Error('program: ' + g.getProgramInfoLog(p));
    return p;
  }

  function create(main, host, opts) {
    const parent = main && main.parentNode;
    if (!parent) return {ok: false, why: 'the canvas is not in the page'};
    const cv = document.createElement('canvas');
    let g = null;
    try { g = cv.getContext('webgl2', {alpha: false, antialias: false, depth: false, stencil: false, premultipliedAlpha: true, preserveDrawingBuffer: false, powerPreference: 'high-performance'}); } catch (e) { g = null; }
    if (!g) return {ok: false, why: 'no WebGL2 here'};
    let info = '';
    try { const d = g.getExtension('WEBGL_debug_renderer_info'); info = String(d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER)); } catch (e) { info = ''; }
    const loseExt = g.getExtension('WEBGL_lose_context');
    if (!(opts && opts.force) && HD.renderGL.allowSoftware !== true && SOFTWARE.test(info)) {
      try { if (loseExt) loseExt.loseContext(); } catch (e) { /* gone */ }
      return {ok: false, why: 'software WebGL (' + info + '): Canvas2D is faster on this machine; set hd.renderer = gl to force'};
    }
    let pC, pS;
    try { pC = compile(g, VS_COMP, FS_COMP); pS = compile(g, VS_SHAPE, FS_SHAPE); } catch (e) { return {ok: false, why: String(e.message || e)}; }

    /* ---------------------------------------------------------------- GL objects */
    const maxLayersHW = Math.max(16, g.getParameter(g.MAX_ARRAY_TEXTURE_LAYERS) || 256);
    let maxLayers = Math.max(16, Math.min(maxLayersHW, Math.floor((HD.renderGL.budgetMB || 256) * 1048576 / TILE_BYTES)));
    let tex = null, depth = 0;
    const free = [];
    function makeArray(n) {
      const t = g.createTexture();
      g.bindTexture(g.TEXTURE_2D_ARRAY, t);
      g.texStorage3D(g.TEXTURE_2D_ARRAY, 1, g.RGBA8, TS, TS, n);
      g.texParameteri(g.TEXTURE_2D_ARRAY, g.TEXTURE_MIN_FILTER, g.LINEAR);
      g.texParameteri(g.TEXTURE_2D_ARRAY, g.TEXTURE_MAG_FILTER, g.LINEAR);
      g.texParameteri(g.TEXTURE_2D_ARRAY, g.TEXTURE_WRAP_S, g.CLAMP_TO_EDGE);
      g.texParameteri(g.TEXTURE_2D_ARRAY, g.TEXTURE_WRAP_T, g.CLAMP_TO_EDGE);
      return t;
    }
    const fbo = g.createFramebuffer(), rfbo = g.createFramebuffer();
    function grow() {
      const n = Math.min(maxLayers, depth ? depth * 2 : 64);
      if (n <= depth) return false;
      const t = makeArray(n);
      if (tex !== null) {
        /* the tiles already made move along: copy every layer of the old array */
        g.bindFramebuffer(g.READ_FRAMEBUFFER, rfbo);
        for (let l = 0; l < depth; l++) {
          g.framebufferTextureLayer(g.READ_FRAMEBUFFER, g.COLOR_ATTACHMENT0, tex, 0, l);
          g.copyTexSubImage3D(g.TEXTURE_2D_ARRAY, 0, 0, 0, l, 0, 0, TS, TS);
        }
        g.bindFramebuffer(g.READ_FRAMEBUFFER, null);
        g.deleteTexture(tex);
      }
      for (let l = n - 1; l >= depth; l--) free.push(l);
      tex = t; depth = n;
      return true;
    }
    grow();
    const vaoC = g.createVertexArray(), bufC = g.createBuffer();
    g.bindVertexArray(vaoC);
    g.bindBuffer(g.ARRAY_BUFFER, bufC);
    for (let i = 0; i < 3; i++) { const loc = g.getAttribLocation(pC, 'b' + i); g.enableVertexAttribArray(loc); g.vertexAttribPointer(loc, 4, g.FLOAT, false, 48, i * 16); g.vertexAttribDivisor(loc, 1); }
    const vaoS = g.createVertexArray(), bufS = g.createBuffer();
    g.bindVertexArray(vaoS);
    g.bindBuffer(g.ARRAY_BUFFER, bufS);
    for (let i = 0; i < 7; i++) { const loc = g.getAttribLocation(pS, 'a' + i); g.enableVertexAttribArray(loc); g.vertexAttribPointer(loc, 4, g.FLOAT, false, 112, i * 16); g.vertexAttribDivisor(loc, 1); }
    g.bindVertexArray(null);
    const uView = g.getUniformLocation(pC, 'uView'), uTexC = g.getUniformLocation(pC, 'uTex'), uTSC = g.getUniformLocation(pC, 'uTS'), uTSS = g.getUniformLocation(pS, 'uTS');
    g.pixelStorei(g.UNPACK_FLIP_Y_WEBGL, false);
    g.pixelStorei(g.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    g.pixelStorei(g.UNPACK_COLORSPACE_CONVERSION_WEBGL, g.NONE);
    g.pixelStorei(g.UNPACK_ALIGNMENT, 1);

    /* ---------------------------------------------------------------- the canvas, under the 2D one */
    cv.className = 'hd-canvas-gl';
    cv.setAttribute('aria-hidden', 'true');
    const st = cv.style;
    st.position = 'absolute'; st.pointerEvents = 'none'; st.display = 'block'; st.margin = '0'; st.padding = '0'; st.border = '0';
    parent.insertBefore(cv, main);
    let placed = '';
    function place() {
      const k = main.offsetLeft + ',' + main.offsetTop + ',' + main.clientWidth + ',' + main.clientHeight;
      if (k === placed) return;
      placed = k;
      st.left = main.offsetLeft + 'px'; st.top = main.offsetTop + 'px'; st.width = main.clientWidth + 'px'; st.height = main.clientHeight + 'px';
    }

    /* ---------------------------------------------------------------- tiles */
    const levels = new Map();                     /* scale -> {s, id, tiles: Map key -> tile} */
    let levelSeq = 0, frameNo = 0, page = null, lastTarget = null, alive = true;
    const S = {rendered: 0, gpuTiles: 0, cpuTiles: 0, partial: 0, instances: 0, drawCalls: 0, renderMs: 0, composeMs: 0, evicted: 0, uploads: 0};
    function levelOf(s, make) {
      let L = levels.get(s);
      if (L === undefined && make) { L = {s, id: ++levelSeq, tiles: new Map()}; levels.set(s, L); }
      return L;
    }
    const key = (i, j) => i + ',' + j;
    function dropTile(L, k, t) { L.tiles.delete(k); if (t.slot >= 0) free.push(t.slot); t.slot = -1; t.ready = false; }
    function clearAll() { for (const L of Array.from(levels.values())) for (const [k, t] of Array.from(L.tiles)) dropTile(L, k, t); levels.clear(); }
    function count() { let n = 0; for (const L of levels.values()) n += L.tiles.size; return n; }
    function slotFor() {
      if (free.length) return free.pop();
      if (depth < maxLayers && grow() && free.length) return free.pop();
      /* full: the least recently used tiles that were not on screen in this frame go */
      const all = [];
      for (const L of levels.values()) for (const [k, t] of L.tiles) if (t.used < frameNo && t.slot >= 0) all.push([t.used, L, k, t]);
      all.sort((a, b) => a[0] - b[0]);
      const n = Math.max(1, Math.min(all.length, Math.ceil(depth / 16)));
      for (let i = 0; i < n; i++) { dropTile(all[i][1], all[i][2], all[i][3]); S.evicted++; }
      return free.length ? free.pop() : -1;
    }
    /* changed world rects -> tiles: a tile on screen at the level being shown repaints the changed part, any other goes */
    function invalidate(rects) {
      for (const L of Array.from(levels.values())) {
        const s = L.s, onScreenLevel = L === lastTarget;
        for (let r = 0; r < rects.length; r += 4) {
          const x0 = Math.floor(rects[r] * s) - 2, y0 = Math.floor(rects[r + 1] * s) - 2, x1 = Math.ceil(rects[r + 2] * s) + 2, y1 = Math.ceil(rects[r + 3] * s) + 2;
          if (!(x1 > x0 && y1 > y0)) continue;
          const i0 = Math.floor(x0 / TS), j0 = Math.floor(y0 / TS), i1 = Math.floor((x1 - 1) / TS), j1 = Math.floor((y1 - 1) / TS);
          const hit = (i, j, k, t) => {
            if (onScreenLevel && t.used === frameNo && t.ready) {
              const a = Math.max(0, x0 - i * TS), b = Math.max(0, y0 - j * TS), c = Math.min(TS, x1 - i * TS), d = Math.min(TS, y1 - j * TS);
              if (c <= a || d <= b) return;
              if (t.dirty === null) t.dirty = [a, b, c, d];
              else { t.dirty[0] = Math.min(t.dirty[0], a); t.dirty[1] = Math.min(t.dirty[1], b); t.dirty[2] = Math.max(t.dirty[2], c); t.dirty[3] = Math.max(t.dirty[3], d); }
            } else dropTile(L, k, t);
          };
          if ((i1 - i0 + 1) * (j1 - j0 + 1) > L.tiles.size) {
            for (const [k, t] of Array.from(L.tiles)) if (t.i >= i0 && t.i <= i1 && t.j >= j0 && t.j <= j1) hit(t.i, t.j, k, t);
          } else {
            for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) { const k = key(i, j), t = L.tiles.get(k); if (t !== undefined) hit(i, j, k, t); }
          }
        }
      }
    }
    /* ---------------------------------------------------------------- making one tile (or the changed part of one) */
    const scratch = new Map();
    function scratchOf(w, h) {
      const k = w + 'x' + h;
      let e = scratch.get(k);
      if (e === undefined) {
        if (scratch.size >= 12) { const first = scratch.keys().next().value; const o = scratch.get(first); o.cv.width = 0; o.cv.height = 0; scratch.delete(first); }
        /* an OffscreenCanvas: Chrome takes a <canvas> that is uploaded to WebGL again and again off the GPU (its curves then
           come out of a different rasteriser than the scene's); an OffscreenCanvas keeps the scene's rasteriser */
        const c = typeof OffscreenCanvas === 'function' ? new OffscreenCanvas(w, h) : document.createElement('canvas');
        c.width = w; c.height = h;
        e = {cv: c, ctx: c.getContext('2d', {alpha: false})};
        scratch.set(k, e);
      } else { scratch.delete(k); scratch.set(k, e); }
      return e;
    }
    function render(L, i, j, sub, t0, budget) {
      const k = key(i, j);
      let t = L.tiles.get(k);
      if (t === undefined) {
        const slot = slotFor();
        if (slot < 0) return false;
        t = {i, j, slot, ready: false, dirty: null, used: frameNo, gpu: false};
        L.tiles.set(k, t);
      }
      const sx = sub ? sub[0] : 0, sy = sub ? sub[1] : 0, sw = sub ? sub[2] - sub[0] : TS, sh = sub ? sub[3] - sub[1] : TS;
      const ox = i * TS, oy = j * TS, s = L.s;
      const shapes = host.tileShapes(page, s, ox, oy, sx, sy, sw, sh);
      if (shapes !== null) {
        drawShapes(t.slot, sx, sy, sw, sh, shapes);
        S.gpuTiles++; S.instances += shapes.n; t.gpu = true;
      } else {
        const M = Math.max(host.margin ? host.margin(page, s) : 0, HD.renderGL.margin || 0);
        const A = scratchOf(sw + 2 * M, sh + 2 * M);
        host.tilePaint(A.ctx, page, s, ox + sx - M, oy + sy - M, sw + 2 * M, sh + 2 * M, t0, budget);
        let src = A.cv;
        if (M > 0) { const B = scratchOf(sw, sh); B.ctx.setTransform(1, 0, 0, 1, 0, 0); B.ctx.globalCompositeOperation = 'copy'; B.ctx.drawImage(A.cv, M, M, sw, sh, 0, 0, sw, sh); B.ctx.globalCompositeOperation = 'source-over'; src = B.cv; }
        g.bindTexture(g.TEXTURE_2D_ARRAY, tex);
        g.texSubImage3D(g.TEXTURE_2D_ARRAY, 0, sx, sy, t.slot, sw, sh, 1, g.RGBA, g.UNSIGNED_BYTE, src);
        S.cpuTiles++; S.uploads++; t.gpu = false;
      }
      if (sub) S.partial++;
      t.ready = true; t.dirty = null; t.used = frameNo;
      S.rendered++;
      return true;
    }
    function drawShapes(slot, sx, sy, sw, sh, shp) {
      const bg = host.bgColor(page);
      g.bindFramebuffer(g.DRAW_FRAMEBUFFER, fbo);
      g.framebufferTextureLayer(g.DRAW_FRAMEBUFFER, g.COLOR_ATTACHMENT0, tex, 0, slot);
      g.viewport(0, 0, TS, TS);
      g.enable(g.SCISSOR_TEST);
      g.scissor(sx, sy, sw, sh);
      g.clearColor(bg[0], bg[1], bg[2], 1);
      g.clear(g.COLOR_BUFFER_BIT);
      if (shp.n > 0) {
        g.useProgram(pS);
        g.uniform1f(uTSS, TS);
        g.bindVertexArray(vaoS);
        g.bindBuffer(g.ARRAY_BUFFER, bufS);
        g.bufferData(g.ARRAY_BUFFER, shp.buf.subarray(0, shp.n * 28), g.STREAM_DRAW);
        g.enable(g.BLEND);
        g.blendFunc(g.ONE, g.ONE_MINUS_SRC_ALPHA);
        g.drawArraysInstanced(g.TRIANGLE_STRIP, 0, 4, shp.n);
        g.disable(g.BLEND);
        g.bindVertexArray(null);
        S.drawCalls++;
      }
      g.disable(g.SCISSOR_TEST);
      g.bindFramebuffer(g.DRAW_FRAMEBUFFER, null);
    }
    /* ---------------------------------------------------------------- the composite: ONE instanced draw call */
    let inst = new Float32Array(12 * 256), instN = 0, lastBg = [0.96, 0.96, 0.96, 1], lastW = 0, lastH = 0;
    function addQuad(x0, y0, x1, y1, u0, v0, u1, v1, slot, exact) {
      if (inst.length < (instN + 1) * 12) { const n = new Float32Array(inst.length * 2); n.set(inst); inst = n; }
      const o = instN * 12;
      inst[o] = x0; inst[o + 1] = y0; inst[o + 2] = x1; inst[o + 3] = y1; inst[o + 4] = u0; inst[o + 5] = v0; inst[o + 6] = u1; inst[o + 7] = v1;
      inst[o + 8] = slot; inst[o + 9] = exact ? 1 : 0; inst[o + 10] = 0; inst[o + 11] = 0;
      instN++;
    }
    function draw() {
      const t = now();
      g.bindFramebuffer(g.FRAMEBUFFER, null);
      g.viewport(0, 0, cv.width, cv.height);
      g.clearColor(lastBg[0], lastBg[1], lastBg[2], 1);
      g.clear(g.COLOR_BUFFER_BIT);
      if (instN > 0) {
        g.useProgram(pC);
        g.uniform2f(uView, cv.width, cv.height);
        g.uniform1f(uTSC, TS);
        g.activeTexture(g.TEXTURE0);
        g.bindTexture(g.TEXTURE_2D_ARRAY, tex);
        g.uniform1i(uTexC, 0);
        g.bindVertexArray(vaoC);
        g.bindBuffer(g.ARRAY_BUFFER, bufC);
        g.bufferData(g.ARRAY_BUFFER, inst.subarray(0, instN * 12), g.STREAM_DRAW);
        g.drawArraysInstanced(g.TRIANGLE_STRIP, 0, 4, instN);
        g.bindVertexArray(null);
        S.drawCalls++;
      }
      S.composeMs += now() - t;
    }
    /* the tile index range of level s that covers the canvas */
    function rangeOf(s, bs, tx, ty, W, H, ring) {
      const k = s / bs;
      const x0 = (0 - tx) * k, y0 = (0 - ty) * k, x1 = (W - tx) * k, y1 = (H - ty) * k;
      return [Math.floor(x0 / TS) - ring, Math.floor(y0 / TS) - ring, Math.floor((x1 - 1e-6) / TS) + ring, Math.floor((y1 - 1e-6) / TS) + ring];
    }
    function bucket(bs) { return Math.pow(2, Math.round(Math.log2(bs))); }

    function frame(a) {
      if (!alive) return {drawn: false, more: false, done: true};
      const t0 = a.t0 || now();
      for (const k in S) S[k] = 0;
      place();
      let resized = false;
      if (cv.width !== a.W || cv.height !== a.H) { cv.width = a.W; cv.height = a.H; resized = true; }
      if (a.page !== page) { clearAll(); page = a.page; }
      if (a.flushAll) clearAll();
      else if (a.rects && a.rects.length) invalidate(a.rects);     /* before the frame number moves: "on screen" = the last frame */
      frameNo++;
      for (const [s, L] of Array.from(levels)) if (!L.tiles.size && L !== lastTarget) levels.delete(s);
      const bs = a.bs, tx = a.tx, ty = a.ty, W = a.W, H = a.H;
      const exactL = levelOf(bs, false);
      /* the level made this frame: the exact one when the zoom rests, else a power-of-two bucket (or the exact one, if it
         is already there) */
      const target = a.zooming ? (exactL !== undefined ? bs : bucket(bs)) : bs;
      const TL = levelOf(target, true);
      lastTarget = TL;
      const rg = rangeOf(target, bs, tx, ty, W, H, 0);
      const cxT = ((W / 2 - tx) * target / bs) / TS - 0.5, cyT = ((H / 2 - ty) * target / bs) / TS - 0.5;
      const must = [], miss = [];
      for (let i = rg[0]; i <= rg[2]; i++) for (let j = rg[1]; j <= rg[3]; j++) {
        const t = TL.tiles.get(key(i, j));
        if (t === undefined || !t.ready) miss.push([i, j, (i - cxT) * (i - cxT) + (j - cyT) * (j - cyT)]);
        else { t.used = frameNo; if (t.dirty !== null) must.push(t); }
      }
      miss.sort((p, q) => p[2] - q[2]);
      const budget = a.moving || a.zooming ? (HD.renderGL.budgetMoving || 6) : (HD.renderGL.budgetIdle || 12);
      const tr = now();
      let did = false;
      /* 1. the parts of tiles on screen that changed: now, so nothing stale is ever shown (capped) */
      for (const t of must) { if (now() - tr > 40) break; render(TL, t.i, t.j, t.dirty, t0, budget); did = true; }
      /* 2. nothing at all to show for much of the screen (a first paint, a jump): a coarse level first, 1/4 of the scale */
      if (miss.length > 6) {
        let bare = 0;
        for (const m of miss) if (!coveredElsewhere(TL, m[0], m[1], target)) bare++;
        if (bare > 6) {
          const cs = Math.pow(2, Math.floor(Math.log2(target)) - 2), CL = levelOf(cs, true), cr = rangeOf(cs, bs, tx, ty, W, H, 0);
          for (let i = cr[0]; i <= cr[2]; i++) for (let j = cr[1]; j <= cr[3]; j++) {
            const t = CL.tiles.get(key(i, j));
            if (t !== undefined && t.ready) { t.used = frameNo; continue; }
            if (did && now() - tr > budget) break;
            render(CL, i, j, null, t0, budget); did = true;
          }
        }
      }
      /* 3. the missing tiles of the level being made, nearest the middle first */
      let left = 0;
      for (let q = 0; q < miss.length; q++) {
        if (did && now() - tr > budget) { left = miss.length - q; break; }
        render(TL, miss[q][0], miss[q][1], null, t0, budget); did = true;
      }
      /* 4. time to spare: the ring just outside the screen, so a pan finds its tiles made */
      let ringLeft = 0;
      if (!left && !a.zooming) {
        const rr = rangeOf(target, bs, tx, ty, W, H, 1);
        for (let i = rr[0]; i <= rr[2]; i++) for (let j = rr[1]; j <= rr[3]; j++) {
          if (i >= rg[0] && i <= rg[2] && j >= rg[1] && j <= rg[3]) continue;
          const t = TL.tiles.get(key(i, j));
          if (t !== undefined && t.ready) { t.used = frameNo; continue; }
          if (now() - tr > budget * 0.75 || depth - free.length > maxLayers - 64) { ringLeft++; continue; }
          render(TL, i, j, null, t0, budget); did = true;
        }
      }
      S.renderMs = now() - tr;
      /* compose: other levels under the holes (coarsest first), the level being made on top */
      instN = 0;
      const k = target / bs, exact = target === bs;
      const holes = [];
      for (let i = rg[0]; i <= rg[2]; i++) for (let j = rg[1]; j <= rg[3]; j++) {
        const t = TL.tiles.get(key(i, j));
        if (t === undefined || !t.ready) holes.push([i * TS / k + tx, j * TS / k + ty, (i + 1) * TS / k + tx, (j + 1) * TS / k + ty]);
      }
      if (holes.length) {
        const others = Array.from(levels.values()).filter(L => L !== TL && L.tiles.size).sort((p, q) => Math.abs(Math.log2(q.s / bs)) - Math.abs(Math.log2(p.s / bs)));
        for (const L of others) {
          const kk = L.s / bs;
          for (const hr of holes) {
            const i0 = Math.floor((hr[0] - tx) * kk / TS), j0 = Math.floor((hr[1] - ty) * kk / TS), i1 = Math.floor(((hr[2] - tx) * kk - 1e-6) / TS), j1 = Math.floor(((hr[3] - ty) * kk - 1e-6) / TS);
            if ((i1 - i0 + 1) * (j1 - j0 + 1) > 256) continue;
            for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
              const t = L.tiles.get(key(i, j));
              if (t === undefined || !t.ready || t.q === frameNo) continue;
              t.used = frameNo; t.q = frameNo;
              addQuad(i * TS / kk + tx, j * TS / kk + ty, (i + 1) * TS / kk + tx, (j + 1) * TS / kk + ty, 0, 0, TS, TS, t.slot, false);
            }
          }
        }
      }
      for (let i = rg[0]; i <= rg[2]; i++) for (let j = rg[1]; j <= rg[3]; j++) {
        const t = TL.tiles.get(key(i, j));
        if (t === undefined || !t.ready) continue;
        t.used = frameNo;
        addQuad(i * TS / k + tx, j * TS / k + ty, (i + 1) * TS / k + tx, (j + 1) * TS / k + ty, 0, 0, TS, TS, t.slot, exact);
      }
      lastBg = host.bgColor(page);
      const viewKey = bs + ',' + tx + ',' + ty + ',' + W + ',' + H;
      const drawn = did || a.flushAll || resized || viewKey !== lastView || holes.length > 0 && instN > 0 && lastInst !== instN;
      if (drawn) { draw(); lastView = viewKey; lastInst = instN; }
      const done = exact && left === 0 && holes.length === 0 && must.every(t => t.dirty === null);
      return {drawn, done, more: !done || ringLeft > 0, level: target, exact, missing: holes.length, rendered: S.rendered, gpuTiles: S.gpuTiles,
        cpuTiles: S.cpuTiles, partial: S.partial, instances: S.instances, quads: instN, drawCalls: S.drawCalls, renderMs: Math.round(S.renderMs * 100) / 100,
        composeMs: Math.round(S.composeMs * 100) / 100, tiles: count(), levels: levels.size, texMB: Math.round(depth * TILE_BYTES / 1048576), usedMB: Math.round((depth - free.length) * TILE_BYTES / 1048576 * 10) / 10,
        evicted: S.evicted};
    }
    let lastView = '', lastInst = -1;
    function coveredElsewhere(TL, i, j, s) {
      const cx = (i + 0.5) * TS / s, cy = (j + 0.5) * TS / s;       /* the tile's middle, in world units */
      for (const L of levels.values()) {
        if (L === TL) continue;
        const t = L.tiles.get(key(Math.floor(cx * L.s / TS), Math.floor(cy * L.s / TS)));
        if (t !== undefined && t.ready) return true;
      }
      return false;
    }
    function finish() { if (!alive) return; const px = new Uint8Array(4); g.readPixels(0, 0, 1, 1, g.RGBA, g.UNSIGNED_BYTE, px); }
    /* the last picture, read back (draws it again first: the drawing buffer is not kept) */
    function snapshot() {
      if (!alive || !cv.width || !cv.height) return null;
      draw();
      const w = cv.width, h = cv.height, px = new Uint8Array(w * h * 4);
      g.readPixels(0, 0, w, h, g.RGBA, g.UNSIGNED_BYTE, px);
      const out = document.createElement('canvas');
      out.width = w; out.height = h;
      const c = out.getContext('2d'), im = c.createImageData(w, h), row = w * 4;
      for (let y = 0; y < h; y++) im.data.set(px.subarray((h - 1 - y) * row, (h - y) * row), y * row);
      c.putImageData(im, 0, 0);
      return out;
    }
    function onLost(e) { if (alive) host.lost('WebGL2 context lost'); }
    cv.addEventListener('webglcontextlost', onLost);
    function destroy(lost) {
      if (!alive) return;
      alive = false;
      cv.removeEventListener('webglcontextlost', onLost);
      try { if (!g.isContextLost()) { clearAll(); if (tex) g.deleteTexture(tex); if (!lost && loseExt) loseExt.loseContext(); } } catch (e) { /* gone */ }
      for (const e of scratch.values()) { e.cv.width = 0; e.cv.height = 0; }
      scratch.clear();
      if (cv.parentNode) cv.parentNode.removeChild(cv);
    }
    return {ok: true, why: '', info, canvas: cv, frame, finish, snapshot, destroy, tileSize: TS,
      get stats() { return {tiles: count(), levels: levels.size, layers: depth, freeLayers: free.length, maxLayers, texMB: Math.round(depth * TILE_BYTES / 1048576)}; },
      lose() { if (loseExt) loseExt.loseContext(); }};
  }
  HD.renderGL = {create, TILE: TS, budgetMB: 256, budgetMoving: 6, budgetIdle: 12, allowSoftware: false};
})();
