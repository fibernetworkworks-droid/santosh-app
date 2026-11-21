// Hoola App Engine - locked by Hoola. v0.999.64 D3 (docs/WEB_DESIGN_ENGINE_PLAN.md P6): after the build, every page
// of the app is rendered to finished HTML here, in the build box (no network). Run as: node hoola.prerender.mjs
//   - pages are found by following the app's own links from "/" (at most 200)
//   - a SITE app (hoola.render.json mode "site"): a page is plain HTML + CSS and loads JavaScript only for its islands;
//     a page wrapped in <AppPage> stays the full app
//   - an APP (mode "app", the default): every page is pre-rendered and the whole app picks it up in the browser
//   - writes <page>/index.html, sitemap.xml, robots.txt and __pages.json (what happened, for Hoola); never fails
//     the build: a page that cannot be rendered keeps the plain app page and says why
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const t0 = Date.now();
const DIST = path.resolve("dist");
const MAX = 200;
const B = "/__hoola_base__";
const report = { mode: "app", pages: [], failed: [], seconds: 0, ok: false, why: "" };

function read(p, d = "") {
  try { return fs.readFileSync(p, "utf8"); } catch { return d; }
}
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function done() {
  report.seconds = Math.round((Date.now() - t0) / 10) / 100;
  fs.writeFileSync(path.join(DIST, "__pages.json"), JSON.stringify(report, null, 1));
  fs.rmSync(path.join(DIST, ".vite"), { recursive: true, force: true });
}

try {
  const cfg = JSON.parse(read("hoola.render.json", "{}") || "{}");
  report.mode = cfg.mode === "site" ? "site" : "app";
  const spa = read(path.join(DIST, "index.html"));
  if (!spa.includes('<div id="root"></div>')) throw new Error("dist/index.html has no empty root");
  fs.writeFileSync(path.join(DIST, "__spa.html"), spa);
  // the islands build (vite build --mode islands -> dist/isl/); without it a site page keeps the whole app's script
  const manifest = JSON.parse(read(path.join(DIST, "isl", ".vite", "manifest.json"), "{}") || "{}");
  const isl = manifest["src/islands-entry.tsx"];
  const islandsJs = isl && isl.file ? "./isl/" + isl.file : "";
  fs.rmSync(path.join(DIST, "isl", ".vite"), { recursive: true, force: true });
  // the app's own entry: its script + the chunks it preloads (a site page drops them)
  const appTags = [...spa.matchAll(/\s*<script type="module"[^>]*src="[^"]*"[^>]*><\/script>|\s*<link rel="modulepreload"[^>]*>/g)].map((m) => m[0]);
  const ssr = await import(pathToFileURL(path.resolve("dist-ssr/entry-server.js")).href);
  // the heading + text fonts start loading with the page (not after the CSS), so they are usually there before the
  // first paint and the text does not move when they arrive
  const preload = [];
  const cssHref = (spa.match(/<link rel="stylesheet"[^>]*href="\.\/([^"]+\.css)"/) || [])[1];
  if (cssHref) {
    const css = read(path.join(DIST, cssHref));
    const fam = (v) => ((css.match(new RegExp(v + ":\\s*\"([^\"]+)\"")) || [])[1] || "");
    const head = fam("--font-head"), body = fam("--font-body");
    for (const m of css.matchAll(/@font-face\s*{([^}]*)}/g)) {
      const b = m[1];
      if (/unicode-range/.test(b)) continue;                       // Indian scripts load only when a page uses them
      const f = ((b.match(/font-family:\s*"?([^";]+)"?/) || [])[1] || "").trim();   // the minifier drops the quotes
      const w = Number((b.match(/font-weight:\s*(\d+)/) || [])[1] || 400);
      const u = (b.match(/url\(([^)]+\.woff2)\)/) || [])[1];
      if (!u || !f) continue;
      if ((f === head && f !== body) || (f === body && w === 400)) preload.push(u.replace(/^["']|["']$/g, ""));
    }
  }
  const fontTags = [...new Set(preload)].slice(0, 3).map((u) =>
    `\n    <link rel="preload" href="./assets/${u.replace(/^\.\//, "").replace(/^assets\//, "")}" as="font" type="font/woff2" crossorigin />`).join("");

  const queue = ["/"], seen = new Set(queue);
  while (queue.length && report.pages.length + report.failed.length < MAX) {
    const url = queue.shift();
    let r;
    try {
      // a site page: islands only; a page that turns out to hold the app (<AppPage>, an app screen) is rendered
      // again as the whole app, so the browser can take it over
      r = ssr.render(url, { islands: report.mode === "site" });
      if (r.app && report.mode === "site") r = ssr.render(url, { islands: false });
    } catch (e) {
      report.failed.push({ path: url, why: String((e && e.message) || e).slice(0, 300) });
      continue;
    }
    // the router's links (/__hoola_base__/...) and a block's own links ("./page": relative to the page's <base>, which
    // is the app's address) - so a page only a block links to (a blog post) is pre-rendered too
    const found = [...r.html.matchAll(/href="\/__hoola_base__(\/[^"#?]*)?/g)].map((m) => m[1] || "/")
      .concat([...r.html.matchAll(/href="\.(\/[^"#?]*)"/g)].map((m) => m[1] || "/"));
    for (const raw of found) {
      let p = raw.replace(/\/+$/, "") || "/";
      if (/\.[a-z0-9]{2,5}$/i.test(p) || p.includes("__")) continue;
      try { p = decodeURI(p); } catch { continue; }
      if (!seen.has(p)) { seen.add(p); queue.push(p); }
    }
    // a site page needs the islands build when it has islands; without it the page stays the whole app
    const site = report.mode === "site" && !r.app && (!!islandsJs || !r.islands.length);
    const h = r.head || {};
    let page = spa.replace('<div id="root"></div>', `<div id="root">${r.html}</div>`);
    let head = fontTags;
    if (h.title) page = page.replace(/<title>[\s\S]*?<\/title>/, `<title>${esc(h.title)}</title>`);
    if (h.description) {
      page = page.replace(/\s*<meta name="description"[^>]*>/, "");
      head += `\n    <meta name="description" content="${esc(h.description)}" />`;
    }
    head += `\n    <link rel="canonical" href="__hoola_origin__${B}${url === "/" ? "/" : url}" />`;
    if (h.title) head += `\n    <meta property="og:title" content="${esc(h.title)}" />`;
    if (h.description) head += `\n    <meta property="og:description" content="${esc(h.description)}" />`;
    if (h.image) head += `\n    <meta property="og:image" content="${esc(h.image)}" />`;
    if (h.noindex) head += `\n    <meta name="robots" content="noindex" />`;
    // v0.999.77 D8: the page's language and the same page in the site's other languages (Google's hreflang)
    if (h.lang && /^[a-zA-Z-]{2,12}$/.test(h.lang)) {
      const dir = /^(ur|ar|fa|he)\b/.test(h.lang) ? ' dir="rtl"' : "";
      page = page.replace(/<html[^>]*>/, `<html lang="${h.lang}"${dir}>`);
    }
    for (const a of Array.isArray(h.alternates) ? h.alternates.slice(0, 8) : []) {
      if (!a || !/^[a-zA-Z-]{2,12}$/.test(a.hreflang || "") || !/^\/[^"<>\s]*$/.test(a.href || "")) continue;
      head += `\n    <link rel="alternate" hreflang="${a.hreflang}" href="__hoola_origin__${B}${a.href === "/" ? "/" : esc(a.href)}" />`;
    }
    if (h.jsonLd) {
      const list = Array.isArray(h.jsonLd) ? h.jsonLd : [h.jsonLd];
      for (const j of list) {
        const body = JSON.stringify({ "@context": "https://schema.org", ...j }).replace(/</g, "\\u003c");
        head += `\n    <script type="application/ld+json">${body}</script>`;
      }
    }
    if (site) {
      for (const tag of appTags) page = page.replace(tag, "");
      if (r.islands.length) head += `\n    <script type="module" crossorigin src="${islandsJs}"></script>`;
    }
    page = page.replace("</head>", head + "\n  </head>");
    const out = url === "/" ? path.join(DIST, "index.html") : path.join(DIST, ...url.split("/").filter(Boolean), "index.html");
    if (!out.startsWith(DIST + path.sep)) continue;
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, page);
    report.pages.push({ path: url, kind: site ? "site" : "app", islands_js: !!islandsJs, islands: r.islands, stuck: r.stuck,
      title: h.title || "", description: !!h.description, noindex: !!h.noindex, bytes: Buffer.byteLength(page) });
  }
  const listed = report.pages.filter((p) => !p.noindex && (report.mode === "app" || p.kind === "site"));
  fs.writeFileSync(path.join(DIST, "sitemap.xml"), '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    listed.map((p) => `  <url><loc>__hoola_origin__${B}${p.path === "/" ? "/" : esc(p.path)}</loc></url>`).join("\n") + "\n</urlset>\n");
  fs.writeFileSync(path.join(DIST, "robots.txt"), `User-agent: *\nAllow: /\nSitemap: __hoola_origin__${B}/sitemap.xml\n`);
  report.ok = report.pages.length > 0;
  if (!report.ok) report.why = "no page could be rendered";
} catch (e) {
  report.ok = false;
  report.why = String((e && e.message) || e).slice(0, 500);
}
done();
console.log(`hoola prerender: ${report.pages.length} pages, ${report.failed.length} failed, ${report.seconds} s` + (report.why ? ` - ${report.why}` : ""));
