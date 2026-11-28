// Hoola App Engine - locked by Hoola. v0.999.64 D3: an ISLAND = a part of a page that needs JavaScript (a form, a
// booking picker, an accordion, a cart). On a pre-rendered site page everything else is plain HTML that never loads
// any script; only islands wake up in the browser, each when it scrolls near.
//
// Write "use client"; at the top of a component file under src/components/ or src/islands/ and its default export
// becomes an island by itself (the build wraps it, named after its file):
//
//   // src/islands/ContactForm.tsx
//   "use client";
//   export default function ContactForm({ title }: { title: string }) { ... }
//
// Props must be plain data (text, numbers, true/false, lists, objects): they are written into the page and read back
// in the browser. A function, a React element or children cannot travel, so such a use stays plain HTML (the build
// report names it).
import * as React from "react";

export type Plain = string | number | boolean | null | undefined | Plain[] | { [k: string]: Plain };

/** what the server render gives islands: whether this page is a site page (islands on), and how to render one island
 *  as a root of its own (so its ids match the browser, which wakes each island as its own root) */
export interface IslandRun {
  on: boolean;
  used: Set<string>;
  stuck: Set<string>;
  n: number;
  render: (node: React.ReactNode, idPrefix: string) => string;
}
export const IslandSink = React.createContext<IslandRun | null>(null);

function travels(v: unknown, depth = 0): boolean {
  if (depth > 12) return false;
  if (v === null || v === undefined) return true;
  const t = typeof v;
  if (t === "string" || t === "number" || t === "boolean") return true;
  if (Array.isArray(v)) return v.every((x) => travels(x, depth + 1));
  if (t === "object") {
    if (React.isValidElement(v)) return false;
    const proto = Object.getPrototypeOf(v);
    if (proto !== Object.prototype && proto !== null) return false;
    return Object.values(v as Record<string, unknown>).every((x) => travels(x, depth + 1));
  }
  return false;
}

/** an island inside another island wakes with its outer one */
const Inside = React.createContext(false);

export function island<P extends object>(name: string, Comp: React.ComponentType<P>) {
  function Island(props: P) {
    const run = React.useContext(IslandSink);
    const inside = React.useContext(Inside);
    // in the browser (the whole app, or the island itself waking) and on an app page: just the component
    if (!run || !run.on || inside) return <Comp {...props} />;
    const { children, ...rest } = props as P & { children?: React.ReactNode };
    if (children !== undefined || !travels(rest)) {
      run.stuck.add(name);
      return <Comp {...props} />;
    }
    run.used.add(name);
    const idp = `i${run.n++}-`;
    const html = run.render(
      <Inside.Provider value={true}>
        <Comp {...props} />
      </Inside.Provider>,
      idp,
    );
    return (
      <div data-island={name} data-props={JSON.stringify(rest)} data-idp={idp} style={{ display: "contents" }}
           dangerouslySetInnerHTML={{ __html: html }} />
    );
  }
  Island.displayName = `island(${name})`;
  return Object.assign(Island, { raw: Comp, island: name });
}
