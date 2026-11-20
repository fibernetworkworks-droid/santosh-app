// v0.999.51 D1 the kit: a number that counts up once when it comes into view (Magic UI "number ticker" idea).
import * as React from "react";
import { cn } from "@/lib/utils";
import { prefersReducedMotion, useInView } from "./use-in-view";

export interface NumberTickerProps extends React.HTMLAttributes<HTMLSpanElement> {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  duration?: number; // ms
}

export function NumberTicker({ value, decimals = 0, prefix = "", suffix = "", duration = 1200, className, ...props }: NumberTickerProps) {
  const [ref, seen] = useInView<HTMLSpanElement>();
  const [shown, setShown] = React.useState(0);
  React.useEffect(() => {
    if (!seen) return;
    if (prefersReducedMotion()) {
      setShown(value);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / duration);
      setShown(value * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [seen, value, duration]);
  const text = shown.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <span ref={ref} className={cn("tabular-nums", className)} aria-label={`${prefix}${value}${suffix}`} {...props}>
      {prefix}
      {text}
      {suffix}
    </span>
  );
}
