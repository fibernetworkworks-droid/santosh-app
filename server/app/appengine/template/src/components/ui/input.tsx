import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "h-10 w-full min-w-0 rounded-control border border-line bg-surface px-3 text-sm text-ink transition-colors placeholder:text-muted focus-visible:border-primary focus-visible:outline-2 focus-visible:outline-primary/40 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-bad aria-invalid:focus-visible:outline-bad/40 file:mr-3 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-ink",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
