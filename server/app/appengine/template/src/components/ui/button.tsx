import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium transition-colors select-none active:translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-ink hover:bg-primary/90",
        secondary: "border border-line bg-surface text-ink hover:bg-bg",
        outline: "border border-line bg-transparent text-ink hover:bg-ink/5",
        ghost: "text-ink hover:bg-ink/5",
        accent: "bg-accent text-primary-ink hover:bg-accent/90",
        danger: "bg-bad text-primary-ink hover:bg-bad/90",
        link: "text-primary underline-offset-4 hover:underline active:translate-y-0",
        /** shadcn names, kept so any shadcn snippet works */
        default: "bg-primary text-primary-ink hover:bg-primary/90",
        destructive: "bg-bad text-primary-ink hover:bg-bad/90",
      },
      size: {
        sm: "h-8 gap-1.5 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
        xl: "h-14 px-8 text-lg",
        icon: "h-10 w-10",
        /** shadcn names */
        default: "h-10 px-4 text-sm",
        "icon-sm": "h-8 w-8",
        "icon-lg": "h-12 w-12",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";
