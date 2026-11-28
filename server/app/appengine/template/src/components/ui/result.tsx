import * as React from "react";
import { CircleCheck, CircleX, Info, Lock, SearchX, ServerCrash, TriangleAlert, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";

// v0.999.334 the result of something she or a visitor did, and the pages that say something went wrong (Ant Design's
// Result + its result / exception specs, MIT - Hoola's own code): say what happened in one line, what it means in the
// next, then the way on ("Back to orders", "Try again", "Go home"). Never a dead end, never only an error code.
export type ResultStatus = "success" | "error" | "info" | "warning" | "403" | "404" | "500" | "offline";

const LOOK: Record<ResultStatus, { icon: React.ComponentType<{ className?: string }>; tone: string; title: string; sub: string }> = {
  success: { icon: CircleCheck, tone: "bg-ok/10 text-ok", title: "Done", sub: "" },
  error: { icon: CircleX, tone: "bg-bad/10 text-bad", title: "That did not go through", sub: "Nothing was changed. Check the details and try again." },
  info: { icon: Info, tone: "bg-primary/10 text-primary", title: "Good to know", sub: "" },
  warning: { icon: TriangleAlert, tone: "bg-warn/10 text-warn", title: "Please check this", sub: "" },
  "403": { icon: Lock, tone: "bg-primary/10 text-primary", title: "This page is not open to you", sub: "Sign in with another account, or ask the owner for access." },
  "404": { icon: SearchX, tone: "bg-primary/10 text-primary", title: "This page was not found", sub: "The link may be old or typed wrongly." },
  "500": { icon: ServerCrash, tone: "bg-bad/10 text-bad", title: "Something went wrong on our side", sub: "Your work is safe. Try again in a minute." },
  offline: { icon: WifiOff, tone: "bg-warn/10 text-warn", title: "You are offline", sub: "This will load again when you are back online." },
};

export interface ResultProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  status?: ResultStatus;
  /** one line: what happened ("Order 1042 is placed") */
  title?: React.ReactNode;
  /** the next line: what it means / what happens next ("We will call you within an hour") */
  sub?: React.ReactNode;
  /** the way on: one main button and at most one or two more */
  extra?: React.ReactNode;
  /** an icon of your own instead of the status icon */
  icon?: React.ReactNode;
}

export function Result({ status = "info", title, sub, extra, icon, className, children, ...props }: ResultProps) {
  const l = LOOK[status];
  const Icon = l.icon;
  const loud = status === "error" || status === "500";
  return (
    <div role={loud ? "alert" : "status"} className={cn("mx-auto flex max-w-lg flex-col items-center gap-4 px-6 py-12 text-center text-balance", className)} {...props}>
      <div aria-hidden="true" className={cn("flex size-14 items-center justify-center rounded-full [&_svg]:size-7", l.tone)}>
        {icon ?? <Icon />}
      </div>
      <h2 className="font-head text-2xl font-semibold text-ink">{title ?? l.title}</h2>
      {(sub ?? l.sub) ? <p className="text-muted">{sub ?? l.sub}</p> : null}
      {extra ? <div className="flex flex-wrap items-center justify-center gap-3">{extra}</div> : null}
      {children ? <div className="w-full rounded-card border border-line bg-surface p-4 text-left text-sm">{children}</div> : null}
    </div>
  );
}
