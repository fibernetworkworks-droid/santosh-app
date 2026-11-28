// v0.999.51 D1 the kit: a card with a soft light that follows the pointer (React Bits "spotlight card" idea). The light
// is the primary token mixed into transparency, so every design system restyles it.
import * as React from "react";
import { cn } from "@/lib/utils";

export function SpotlightCard({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const [pos, setPos] = React.useState<{ x: number; y: number } | null>(null);
  return (
    <div
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        setPos({ x: e.clientX - r.left, y: e.clientY - r.top });
      }}
      onPointerLeave={() => setPos(null)}
      className={cn("relative overflow-hidden rounded-card border border-line bg-surface p-6 text-ink shadow-card", className)}
      {...props}
    >
      <div
        aria-hidden="true"
        className={cn("pointer-events-none absolute inset-0 transition-opacity duration-300", pos ? "opacity-100" : "opacity-0")}
        style={pos ? { background: `radial-gradient(320px circle at ${pos.x}px ${pos.y}px, color-mix(in oklab, var(--color-primary) 14%, transparent), transparent 70%)` } : undefined}
      />
      <div className="relative">{children}</div>
    </div>
  );
}
