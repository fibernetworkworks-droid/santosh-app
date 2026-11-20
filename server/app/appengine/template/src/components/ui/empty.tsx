import * as React from "react";
import { cn } from "@/lib/utils";

export interface EmptyProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  /** a lucide-react icon element, e.g. <Inbox /> */
  icon?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** buttons that get her out of the empty state ("Add the first one") */
  action?: React.ReactNode;
}

/** The empty state: a list with nothing in it yet, a search that found nothing. Use the props, or compose the parts. */
export function Empty({ className, icon, title, description, action, children, ...props }: EmptyProps) {
  return (
    <div
      className={cn(
        "flex min-w-0 flex-1 flex-col items-center justify-center gap-4 rounded-card border border-dashed border-line p-8 text-center text-balance",
        className,
      )}
      {...props}
    >
      {(icon || title || description) && (
        <EmptyHeader>
          {icon && <EmptyMedia>{icon}</EmptyMedia>}
          {title && <EmptyTitle>{title}</EmptyTitle>}
          {description && <EmptyDescription>{description}</EmptyDescription>}
        </EmptyHeader>
      )}
      {action && <EmptyContent>{action}</EmptyContent>}
      {children}
    </div>
  );
}

export function EmptyHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex max-w-sm flex-col items-center gap-2", className)} {...props} />;
}

/** The icon above the title: pass a lucide-react icon as the child. */
export function EmptyMedia({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "mb-1 flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary [&_svg]:size-6",
        className,
      )}
      {...props}
    />
  );
}

export function EmptyTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("font-head text-lg font-semibold text-ink", className)} {...props} />;
}

export function EmptyDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-muted", className)} {...props} />;
}

/** Buttons that get her out of the empty state ("Add the first one"). */
export function EmptyContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex w-full max-w-sm flex-wrap items-center justify-center gap-2", className)} {...props} />;
}
