// Hoola App Engine - locked by Hoola. Click -> source (L9 of docs/LOVABLE_STUDIO_PLAN.md).
// In a PREVIEW build only (HOOLA_SOURCE=1), every element written in src/**/*.tsx gets
//   data-hs="<file>:<line>:<column>"  and  data-hc="<Component>"
// so a click in the preview finds the exact line that made it, and a line finds every element it made.
// A component used on a page (<CardTitle ...>) is tagged too: the kit spreads its props AFTER its own tag, so the
// element on screen points at the line on the PAGE that used it - the line a free edit should change.
// A published build never runs this: nothing of it reaches visitors.
import { parse } from "@babel/parser";
import MagicString from "magic-string";

const TAGGED = /^[A-Za-z][A-Za-z0-9-]*$/;

function walk(node, visit, names) {
  if (!node || typeof node.type !== "string") return;
  let pushed = false;
  if (node.type === "FunctionDeclaration" && node.id) { names.push(node.id.name); pushed = true; }
  if (node.type === "VariableDeclarator" && node.id && node.id.type === "Identifier" && node.init &&
      /Function|ArrowFunction|CallExpression/.test(node.init.type)) { names.push(node.id.name); pushed = true; }
  visit(node, names);
  for (const key of Object.keys(node)) {
    if (key === "loc" || key === "start" || key === "end" || key === "extra") continue;
    const v = node[key];
    if (Array.isArray(v)) for (const c of v) walk(c, visit, names);
    else if (v && typeof v.type === "string") walk(v, visit, names);
  }
  if (pushed) names.pop();
}

export default function hoolaSource() {
  const on = process.env.HOOLA_SOURCE === "1";
  let root = "";
  return {
    name: "hoola-source",
    enforce: "pre",
    apply: () => on,
    configResolved(c) { root = c.root.replace(/\\/g, "/").replace(/\/$/, "") + "/"; },
    transform(code, id) {
      const file = id.split("?")[0].replace(/\\/g, "/");
      if (!file.endsWith(".tsx") || !file.startsWith(root + "src/")) return null;
      const rel = file.slice(root.length);
      let ast;
      try {
        ast = parse(code, { sourceType: "module", plugins: ["jsx", "typescript"], errorRecovery: true });
      } catch {
        return null;                                 // the build itself reports the syntax error
      }
      const s = new MagicString(code);
      walk(ast.program, (n, names) => {
        if (n.type !== "JSXOpeningElement" || n.name.type !== "JSXIdentifier" || !TAGGED.test(n.name.name) || n.name.name === "Fragment") return;
        if (n.attributes.some((a) => a.type === "JSXAttribute" && a.name && a.name.name === "data-hs")) return;
        const at = `${rel}:${n.loc.start.line}:${n.loc.start.column + 1}`;
        const comp = names[names.length - 1] || "";
        s.appendLeft(n.name.end, ` data-hs="${at}"` + (comp ? ` data-hc="${comp}"` : ""));
      }, []);
      return { code: s.toString(), map: s.generateMap({ hires: true, source: file, includeContent: true }) };
    },
  };
}
