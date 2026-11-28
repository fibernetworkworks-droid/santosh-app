// v0.999.51 D1 the kit: content fades up softly as it scrolls into view (Magic UI "blur fade" idea).
// v0.999.64 D3: CSS only (a scroll-driven animation): the text is always in the page and visible without any script,
// so a pre-rendered page never waits for JavaScript to show its words. A browser without scroll-driven animations
// simply shows it still; reduced motion shows it still.
import * as React from "react";
import { cn } from "@/lib/utils";

export interface RevealProps extends React.HTMLAttributes<HTMLDivElement> {
  delay?: number; // ms: a later start in the scroll (about 5% of the entry per 100 ms)
}

export function Reveal({ delay = 0, className, style, children, ...props }: RevealProps) {
  const from = Math.min(40, Math.max(0, Math.round(delay / 20)));
  return (
    <div className={cn("hoola-reveal", className)} style={from ? { ...style, ["--reveal-from" as string]: `${from}%` } : style} {...props}>
      {children}
    </div>
  );
}
