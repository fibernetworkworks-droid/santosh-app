// v0.999.51 D1 the kit: the frame every section block shares (docs/WEB_DESIGN_ENGINE_PLAN.md P1). A block is a
// <section data-block="<id>"> that reads ONLY the design tokens, so any design system (genome) restyles it.
import * as React from "react";
import { ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type Tone = "plain" | "surface" | "primary" | "ink";

const TONES: Record<Tone, string> = {
  plain: "bg-bg text-ink",
  surface: "bg-surface text-ink",
  // on a coloured tone the headings follow the section's own text colour (the base style makes them ink)
  primary: "bg-primary text-primary-ink [&_h2]:text-inherit [&_h3]:text-inherit [&_h4]:text-inherit",
  ink: "bg-ink text-bg [&_h2]:text-inherit [&_h3]:text-inherit [&_h4]:text-inherit",
};

export interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  block: string;
  variant?: string;
  tone?: Tone;
  tight?: boolean;
}

/** The outer <section>: block name + variant as data attributes, the tone's colours, the vertical rhythm. */
export function Section({ block, variant, tone = "plain", tight, className, children, ...props }: SectionProps) {
  return (
    <section
      data-block={block}
      // v0.999.64 D3: an app screen (dashboard, table, sign-in...) makes its page run as the full app on a site
      data-hoola-app={block.startsWith("screen-") ? "" : undefined}
      data-variant={variant}
      className={cn("relative w-full", tight ? "py-10 sm:py-14" : "py-16 sm:py-24", TONES[tone], className)}
      {...props}
    >
      {children}
    </section>
  );
}

/** The content column: one width for every block so sections line up down the page. */
export function Container({ className, wide, ...props }: React.HTMLAttributes<HTMLDivElement> & { wide?: boolean }) {
  return <div className={cn("mx-auto w-full px-4 sm:px-6", wide ? "max-w-7xl" : "max-w-6xl", className)} {...props} />;
}

/** A section's heading and one-line intro. No tiny label above it (an AI-look tell): the heading says it. */
export function SectionHead({ title, intro, align = "left", className, children }: {
  title: React.ReactNode;
  intro?: React.ReactNode;
  align?: "left" | "center";
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className={cn("mb-10 flex flex-col gap-3 sm:mb-14", align === "center" ? "mx-auto max-w-2xl items-center text-center" : "max-w-2xl", className)}>
      <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h2>
      {intro ? <p className="text-base text-muted sm:text-lg">{intro}</p> : null}
      {children}
    </div>
  );
}

/** A picture: her photo when there is one, else a quiet stand-in in the design's own colours (never a grey box). */
export function Picture({ src, alt, ratio = "4/3", className, label }: {
  src?: string;
  alt: string;
  ratio?: "1/1" | "4/3" | "3/2" | "16/9" | "3/4" | "4/5";
  className?: string;
  label?: string;
}) {
  const r = { "1/1": "aspect-square", "4/3": "aspect-4/3", "3/2": "aspect-3/2", "16/9": "aspect-video", "3/4": "aspect-3/4", "4/5": "aspect-4/5" }[ratio];
  if (src) {
    return <img src={src} alt={alt} loading="lazy" className={cn("w-full rounded-card object-cover", r, className)} />;
  }
  return (
    <div role="img" aria-label={alt} className={cn("relative flex w-full items-center justify-center overflow-hidden rounded-card bg-primary/10 text-primary", r, className)}>
      <div aria-hidden="true" className="absolute -right-8 -top-8 size-32 rounded-full bg-accent/20" />
      <div aria-hidden="true" className="absolute -bottom-10 -left-6 size-40 rounded-full bg-primary/15" />
      <div className="relative flex flex-col items-center gap-2 px-4 text-center">
        <ImageIcon className="size-7 opacity-70" aria-hidden="true" />
        {label ? <span className="text-xs font-medium text-current opacity-80">{label}</span> : null}
      </div>
    </div>
  );
}

/** Indian rupees, the way people write them: Rs 1,499 -> "₹1,499". */
export function rupees(n: number): string {
  return "₹" + n.toLocaleString("en-IN");
}
