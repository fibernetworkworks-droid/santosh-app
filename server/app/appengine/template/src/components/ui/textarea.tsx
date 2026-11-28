import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-24 w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-ink transition-colors placeholder:text-muted focus-visible:border-primary focus-visible:outline-2 focus-visible:outline-primary/40 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-bad aria-invalid:focus-visible:outline-bad/40",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
