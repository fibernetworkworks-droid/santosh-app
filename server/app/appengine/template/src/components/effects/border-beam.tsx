// v0.999.51 D1 the kit: a thin light that travels round a card's edge (Magic UI "border beam" idea). For one
// highlighted card on a page (the plan she should pick), never every card.
import * as React from "react";
import { cn } from "@/lib/utils";

export function BorderBeam({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("relative overflow-hidden rounded-card p-px", className)}>
      <div
        aria-hidden="true"
        className="absolute -inset-1/2 animate-beam"
        style={{ background: "conic-gradient(from 0deg, transparent 0 78%, var(--color-primary) 88%, transparent 98%)" }}
      />
      <div className="relative h-full rounded-card bg-surface">{children}</div>
    </div>
  );
}
