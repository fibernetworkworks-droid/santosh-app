// Hoola App Engine - locked by Hoola. v0.999.64 D3: the only script a pre-rendered SITE page loads, and only when the
// page has islands. It is tiny: it watches each island and, when one comes near the screen and the browser is free,
// loads React + that island's code (islands-wake.tsx) and wakes it. Nothing else on the page runs any code.
const all = [...document.querySelectorAll<HTMLElement>("[data-island]")].filter((el) => !el.parentElement?.closest("[data-island]"));

let wakeMod: Promise<typeof import("./islands-wake")> | null = null;
const woke = new Set<HTMLElement>();
function wake(el: HTMLElement) {
  if (woke.has(el)) return;                        // each island wakes once
  woke.add(el);
  wakeMod = wakeMod || import("./islands-wake");
  void wakeMod.then((w) => w.wake(el));
}
function later(fn: () => void) {
  if ("requestIdleCallback" in window) window.requestIdleCallback(fn, { timeout: 2000 });
  else setTimeout(fn, 200);
}

// a link inside an island goes to the next page the normal way (each page is its own finished HTML)
document.addEventListener(
  "click",
  (e) => {
    const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
    if (!a || !a.closest("[data-island]") || a.target || a.hasAttribute("download")) return;
    if ((a.getAttribute("href") || "").startsWith("#")) return;   // v0.999.77 an in-page link is the island's own (Add to cart)
    if (a.origin === location.origin) e.stopPropagation();
  },
  true,
);

// v0.999.77 D8: a page-wide island (src/islands/: the shop's cart) wakes as soon as the browser is free - it must hear
// an "Add to cart" from any section, wherever the page is scrolled
const pageWide = (el: HTMLElement) => /^islands\//.test(el.dataset.island || "");
for (const el of all) if (pageWide(el)) later(() => wake(el));

if (all.length) {
  if (typeof IntersectionObserver === "undefined") all.forEach((el) => later(() => wake(el)));
  else {
    const owner = new Map<Element, HTMLElement>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const el = owner.get(e.target);
          if (!e.isIntersecting || !el) continue;
          io.unobserve(e.target);
          owner.delete(e.target);
          later(() => wake(el));
        }
      },
      { rootMargin: "300px 0px" },
    );
    for (const el of all) {
      // a wrapper with display:contents has no box of its own: watch its first child
      const box = el.firstElementChild || el;
      owner.set(box, el);
      io.observe(box);
    }
    // a visitor who taps an island before it woke: wake it at once (that first tap may need repeating)
    document.addEventListener("pointerdown", (e) => {
      const el = (e.target as Element | null)?.closest?.("[data-island]") as HTMLElement | null;
      if (!el || woke.has(el) || !all.includes(el)) return;
      for (const [box, owned] of owner) if (owned === el) { io.unobserve(box); owner.delete(box); }
      wake(el);
    }, { capture: true, passive: true });
  }
}
export {};
