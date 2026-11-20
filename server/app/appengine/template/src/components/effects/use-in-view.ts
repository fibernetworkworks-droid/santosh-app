// v0.999.51 D1 the kit: true once the element has scrolled into view (and stays true). Ideas from Magic UI / React
// Bits (MIT), written for Hoola; no upstream code.
import * as React from "react";

export function useInView<T extends Element>(options: IntersectionObserverInit = { rootMargin: "0px 0px -10% 0px" }) {
  const ref = React.useRef<T | null>(null);
  const [seen, setSeen] = React.useState(false);
  React.useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    if (typeof IntersectionObserver === "undefined") {
      setSeen(true);
      return;
    }
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        setSeen(true);
        io.disconnect();
      }
    }, options);
    io.observe(el);
    return () => io.disconnect();
  }, [seen]); // eslint-disable-line react-hooks/exhaustive-deps
  return [ref, seen] as const;
}

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}
