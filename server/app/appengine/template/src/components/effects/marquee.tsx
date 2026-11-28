// v0.999.51 D1 the kit: a row that scrolls slowly on its own (logos / names). Pauses on hover; still under reduced
// motion. Use it where scrolling carries meaning (a strip of real partner logos), not by reflex.
import * as React from "react";
import { cn } from "@/lib/utils";

export interface MarqueeProps extends React.HTMLAttributes<HTMLDivElement> {
  reverse?: boolean;
  pauseOnHover?: boolean;
  seconds?: number;
}

export function Marquee({ reverse, pauseOnHover = true, seconds = 32, className, children, ...props }: MarqueeProps) {
  return (
    <div className={cn("group flex overflow-hidden", className)} {...props}>
      <div
        className={cn("flex w-max shrink-0 animate-marquee gap-12 pr-12", pauseOnHover && "group-hover:[animation-play-state:paused]")}
        style={{ animationDuration: `${seconds}s`, animationDirection: reverse ? "reverse" : "normal" }}
      >
        {children}
        <div aria-hidden="true" className="flex shrink-0 gap-12">
          {children}
        </div>
      </div>
    </div>
  );
}
