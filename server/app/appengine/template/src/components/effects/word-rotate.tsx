// v0.999.51 D1 the kit: one word in a heading that changes every few seconds (Magic UI "word rotate" idea). Readers of
// the page get every word (aria-label); reduced motion shows the first word only.
import * as React from "react";
import { cn } from "@/lib/utils";
import { prefersReducedMotion } from "./use-in-view";

export function WordRotate({ words, ms = 2600, className }: { words: string[]; ms?: number; className?: string }) {
  const [i, setI] = React.useState(0);
  React.useEffect(() => {
    if (words.length < 2 || prefersReducedMotion()) return;
    const t = setInterval(() => setI((n) => (n + 1) % words.length), ms);
    return () => clearInterval(t);
  }, [words.length, ms]);
  return (
    <span className={cn("inline-block overflow-hidden align-bottom", className)} aria-label={words.join(", ")}>
      <span key={i} className="inline-block animate-word" aria-hidden="true">
        {words[i] ?? ""}
      </span>
    </span>
  );
}
