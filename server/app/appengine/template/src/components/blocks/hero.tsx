// v0.999.51 D1 the kit: the hero - the first thing a visitor sees. Three layouts: split (words left, her photo right
// on a soft shape), overlay (full-bleed photo, headline bottom-left over a dark fade), kinetic (huge centred type,
// one word turning). One authored moment each: the headline rises in, or the word turns.
import * as React from "react";
import { ArrowRight, Check, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal, WordRotate } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, Picture, type Tone } from "./_kit";

export const variants = ["split", "overlay", "kinetic"] as const;
export type HeroVariant = (typeof variants)[number];

export interface HeroAction {
  label: string;
  href: string;
}

export interface HeroPhoto {
  src?: string;
  alt: string;
  label: string;
}

export interface HeroProps {
  variant?: HeroVariant;
  tone?: Tone;
  /** the main line (split, overlay) */
  headline?: string;
  /** kinetic: the words before the turning word, the turning words, the words after */
  lead?: string;
  rotate?: string[];
  tail?: string;
  /** one or two sentences under the headline */
  intro?: string;
  primary?: HeroAction;
  secondary?: HeroAction;
  photo?: HeroPhoto;
  /** three short, true facts (hours, area, years) */
  points?: string[];
  /** a small line on the photo or under the buttons, e.g. today's hours */
  note?: string;
}

export const sample: Required<Omit<HeroProps, "variant" | "tone">> = {
  headline: "Bread, cakes and chai, baked fresh every morning in Kothrud.",
  lead: "Fresh",
  rotate: ["sourdough", "nankhatai", "birthday cakes", "pav"],
  tail: "from our oven to your table.",
  intro: "A small family bakery on Karve Road. We start baking at 5 am, so the first loaf you buy is still warm.",
  primary: { label: "See today's bakes", href: "#products" },
  secondary: { label: "Order a cake", href: "#contact" },
  photo: { alt: "The bakery counter with fresh loaves on wooden shelves", label: "Your shop photo" },
  points: ["Open 7 am to 10 pm", "Eggless options on everything", "Home delivery within 4 km"],
  note: "Open today, 7 am to 10 pm",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function Actions({ p, inverted, center }: { p: typeof sample; inverted?: boolean; center?: boolean }) {
  return (
    <div className={cn("flex flex-wrap gap-3", center && "justify-center")}>
      <Button asChild size="lg" className="group">
        <a href={p.primary.href}>
          {p.primary.label}
          <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </a>
      </Button>
      {p.secondary.label ? (
        <Button
          asChild
          size="lg"
          variant="outline"
          className={cn(inverted && "border-bg/40 text-bg hover:bg-bg/10")}
        >
          <a href={p.secondary.href}>{p.secondary.label}</a>
        </Button>
      ) : null}
    </div>
  );
}

export default function Hero({ variant = "split", tone, ...rest }: HeroProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";

  if (variant === "overlay") {
    return (
      <Section block="hero" variant={variant} tone={tone ?? "ink"} className="overflow-hidden py-0 sm:py-0">
        <div className="absolute inset-0">
          <Picture src={p.photo.src} alt={p.photo.alt} label={p.photo.label} ratio="16/9" className="h-full rounded-none" />
          <div aria-hidden="true" className="absolute inset-0 bg-linear-to-t from-ink via-ink/60 to-ink/10" />
        </div>
        <Container wide className="relative flex min-h-140 flex-col justify-end pb-12 pt-40 sm:min-h-168 sm:pb-16">
          <div className="grid items-end gap-10 lg:grid-cols-12">
            <Reveal className="lg:col-span-8">
              <h1 className="max-w-4xl break-words font-head text-4xl font-semibold leading-tight tracking-tight text-bg sm:text-6xl lg:text-7xl lg:leading-none">
                {p.headline}
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-bg/80">{p.intro}</p>
              <div className="mt-8">
                <Actions p={p} inverted />
              </div>
            </Reveal>
            <ul className="flex flex-col gap-3 border-t border-bg/20 pt-6 text-sm text-bg/80 lg:col-span-4 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
              {p.points.map((x) => (
                <li key={x} className="flex items-start gap-2.5">
                  <Check className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden="true" />
                  <span>{x}</span>
                </li>
              ))}
            </ul>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "kinetic") {
    return (
      <Section block="hero" variant={variant} tone={t} className="overflow-hidden">
        <Container className="flex flex-col items-center py-10 text-center sm:py-16">
          <h1 className="max-w-5xl break-words font-head text-5xl font-semibold leading-none tracking-tight sm:text-7xl lg:text-8xl">
            <span className="block">{p.lead}</span>
            <WordRotate words={p.rotate} className="block py-1 text-primary" />
            <span className={cn("mt-4 block text-2xl font-normal leading-snug tracking-normal sm:text-3xl", quiet(t))}>{p.tail}</span>
          </h1>
          <p className={cn("mt-8 max-w-xl text-base leading-relaxed sm:text-lg", quiet(t))}>{p.intro}</p>
          <div className="mt-10">
            <Button asChild size="xl" className="group">
              <a href={p.primary.href}>
                {p.primary.label}
                <ArrowRight className="size-5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </a>
            </Button>
          </div>
          <ul className={cn("mt-14 flex flex-wrap justify-center gap-x-8 gap-y-3 text-sm", quiet(t))}>
            {p.points.map((x) => (
              <li key={x} className="flex items-center gap-2">
                <span aria-hidden="true" className="size-1.5 rounded-full bg-primary" />
                {x}
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="hero" variant={variant} tone={t} className="overflow-hidden">
      <Container wide>
        <div className="grid items-center gap-12 lg:grid-cols-12 lg:gap-16">
          <Reveal className="min-w-0 lg:col-span-6">
            <h1 className="break-words font-head text-4xl font-semibold leading-tight tracking-tight sm:text-6xl lg:text-6xl xl:text-7xl xl:leading-none">
              {p.headline}
            </h1>
            <p className={cn("mt-6 max-w-lg text-lg leading-relaxed", quiet(t))}>{p.intro}</p>
            <div className="mt-9">
              <Actions p={p} />
            </div>
            <ul className={cn("mt-10 grid gap-3 border-t border-line pt-6 text-sm sm:grid-cols-3", quiet(t))}>
              {p.points.map((x) => (
                <li key={x} className="flex items-start gap-2">
                  <Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                  <span>{x}</span>
                </li>
              ))}
            </ul>
          </Reveal>
          <div className="relative min-w-0 lg:col-span-6">
            <div aria-hidden="true" className="absolute -bottom-5 -left-5 h-3/4 w-3/4 rounded-card bg-accent/15 sm:-bottom-8 sm:-left-8" />
            <div aria-hidden="true" className="absolute -right-4 -top-4 size-24 rounded-full border border-primary/30 sm:size-32" />
            <Picture src={p.photo.src} alt={p.photo.alt} label={p.photo.label} ratio="4/5" className="relative shadow-card" />
            {p.note ? (
              <div className="absolute bottom-5 left-5 right-5 flex items-center gap-3 rounded-control border border-line bg-surface/95 px-4 py-3 text-sm text-ink shadow-card sm:right-auto">
                <Clock className="size-4 shrink-0 text-primary" aria-hidden="true" />
                <span className="font-medium">{p.note}</span>
              </div>
            ) : null}
          </div>
        </div>
      </Container>
    </Section>
  );
}
