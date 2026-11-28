import * as React from "react";
import { cn } from "@/lib/utils";

/** One key, as in "press Ctrl K". */
export function Kbd({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <kbd
      className={cn(
        "pointer-events-none inline-flex h-5 min-w-5 items-center justify-center gap-1 rounded-control border border-line bg-bg px-1 font-body text-xs font-medium text-muted select-none [&_svg]:size-3",
        className,
      )}
      {...props}
    />
  );
}

/** Several keys pressed together. */
export function KbdGroup({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return <kbd className={cn("inline-flex items-center gap-1", className)} {...props} />;
}
