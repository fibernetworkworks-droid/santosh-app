import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center gap-1 whitespace-nowrap rounded-control px-2 py-0.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary [&_svg]:size-3 [&_svg]:shrink-0",
  {
    variants: {
      tone: {
        neutral: "border border-line bg-bg text-muted",
        primary: "bg-primary text-primary-ink",
        accent: "bg-accent text-primary-ink",
        ok: "bg-ok text-primary-ink",
        warn: "bg-warn text-ink",
        bad: "bg-bad text-primary-ink",
        outline: "border border-line bg-transparent text-ink",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

/** shadcn's `variant` names, mapped onto the tones. */
const VARIANT_TONE = {
  default: "primary",
  secondary: "neutral",
  destructive: "bad",
  outline: "outline",
} as const;

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  /** shadcn name; `tone` wins when both are given */
  variant?: keyof typeof VARIANT_TONE | null;
  asChild?: boolean;
}

export function Badge({ className, tone, variant, asChild = false, ...props }: BadgeProps) {
  const Comp = asChild ? Slot : "span";
  const t = tone ?? (variant ? VARIANT_TONE[variant] : undefined);
  return <Comp className={cn(badgeVariants({ tone: t }), className)} {...props} />;
}
