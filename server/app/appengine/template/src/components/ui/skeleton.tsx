import * as React from "react";
import { cn } from "@/lib/utils";

/** A grey placeholder shaped like the content that is still loading. */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-control bg-line/70", className)} {...props} />;
}
