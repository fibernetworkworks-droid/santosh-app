// v0.999.51 D1 the kit: quiet background patterns drawn in the line colour (Magic UI "dot / grid pattern" idea).
import * as React from "react";
import { cn } from "@/lib/utils";

export function DotPattern({ className, gap = 20 }: { className?: string; gap?: number }) {
  const id = React.useId().replace(/:/g, "");
  return (
    <svg aria-hidden="true" className={cn("pointer-events-none absolute inset-0 h-full w-full text-line", className)}>
      <defs>
        <pattern id={`d${id}`} width={gap} height={gap} patternUnits="userSpaceOnUse">
          <circle cx={1.5} cy={1.5} r={1.2} fill="currentColor" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#d${id})`} />
    </svg>
  );
}

export function GridPattern({ className, size = 40 }: { className?: string; size?: number }) {
  const id = React.useId().replace(/:/g, "");
  return (
    <svg aria-hidden="true" className={cn("pointer-events-none absolute inset-0 h-full w-full text-line", className)}>
      <defs>
        <pattern id={`g${id}`} width={size} height={size} patternUnits="userSpaceOnUse">
          <path d={`M ${size} 0 L 0 0 0 ${size}`} fill="none" stroke="currentColor" strokeWidth={1} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#g${id})`} />
    </svg>
  );
}
