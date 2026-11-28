import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SpinnerProps extends React.SVGProps<SVGSVGElement> {
  /** what is loading, read out by screen readers */
  label?: string;
}

export function Spinner({ className, label = "Loading", ...props }: SpinnerProps) {
  return (
    <Loader2 role="status" aria-label={label} className={cn("size-4 animate-spin text-muted", className)} {...props} />
  );
}
