import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const badgeVariants = cva("inline-flex items-center rounded-control px-2 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "bg-bg text-muted border border-line",
      primary: "bg-primary text-primary-ink",
      ok: "bg-ok text-primary-ink",
      warn: "bg-warn text-ink",
      bad: "bg-bad text-primary-ink",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export function Badge({ className, tone, ...props }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
