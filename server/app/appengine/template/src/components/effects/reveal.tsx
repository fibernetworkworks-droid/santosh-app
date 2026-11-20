// v0.999.51 D1 the kit: content fades up softly the first time it scrolls into view (Magic UI "blur fade" idea).
import * as React from "react";
import { cn } from "@/lib/utils";
import { useInView } from "./use-in-view";

export interface RevealProps extends React.HTMLAttributes<HTMLDivElement> {
  delay?: number; // ms
}

export function Reveal({ delay = 0, className, style, children, ...props }: RevealProps) {
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={cn(seen ? "animate-fade-up" : "opacity-0", className)}
      style={{ ...style, animationDelay: delay ? `${delay}ms` : undefined }}
      {...props}
    >
      {children}
    </div>
  );
}
