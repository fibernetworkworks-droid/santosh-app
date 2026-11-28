// v0.999.51 D1 the kit: how it works, step by step. Three layouts: numbered (steps in a row joined by a line, they
// rise in one after another), timeline (a vertical rail with a marker per step and how long it takes), sticky (the
// title and the action stay on the left while large numbered steps scroll on the right).
import * as React from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["numbered", "timeline", "sticky"] as const;
export type ProcessStepsVariant = (typeof variants)[number];

export interface ProcessStep {
  title: string;
  line: string;
  /** how long it takes or when it happens: "Day 1", "15 minutes" */
  time?: string;
}

export interface ProcessStepsProps {
  variant?: ProcessStepsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  steps?: ProcessStep[];
  action?: { label: string; href: string };
}

export const sample: Required<Omit<ProcessStepsProps, "variant" | "tone">> = {
  title: "From first call to finished room",
  intro: "Most homes in Hyderabad take four to six weeks. You will always know what happens next and who is doing it.",
  steps: [
    { title: "A free visit", line: "We come to your home, measure every wall and listen to how you use the space.", time: "Day 1" },
    { title: "Drawings and a fixed quote", line: "You get 3D views and one price for the whole job, with no extras added later.", time: "Within 5 days" },
    { title: "Work on site", line: "One site supervisor, a daily photo update on WhatsApp, and a clean site every evening.", time: "3 to 5 weeks" },
    { title: "Handover and care", line: "We walk through every room with you and fix anything you point out, free for a year.", time: "Final week" },
  ],
  action: { label: "Book a free visit", href: "#contact" },
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function ActionLink({ a, size = "lg" }: { a: { label: string; href: string }; size?: "lg" | "md" }) {
  return (
    <Button asChild size={size} className="group">
      <a href={a.href}>
        {a.label}
        <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
      </a>
    </Button>
  );
}

export default function ProcessSteps({ variant = "numbered", tone, ...rest }: ProcessStepsProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";

  if (variant === "timeline") {
    return (
      <Section block="process_steps" variant={variant} tone={t}>
        <Container className="max-w-3xl">
          <SectionHead title={p.title} intro={p.intro} />
          <ol className="relative">
            {p.steps.map((s, i) => (
              <li key={s.title} className="relative grid grid-cols-12 gap-4">
                <div className="col-span-3 pt-0.5 text-right sm:col-span-2">
                  {s.time ? <span className={cn("text-sm font-medium tabular-nums", quiet(t))}>{s.time}</span> : null}
                </div>
                <div className={cn("relative col-span-9 pl-8 sm:col-span-10", i < p.steps.length - 1 && "border-l border-line pb-12")}>
                  <span
                    aria-hidden="true"
                    className="absolute -left-3 top-0 flex size-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-ink"
                  >
                    {i + 1}
                  </span>
                  <Reveal delay={i * 80}>
                    <h3 className="font-head text-xl font-semibold tracking-tight sm:text-2xl">{s.title}</h3>
                    <p className={cn("mt-2 text-base leading-relaxed", quiet(t))}>{s.line}</p>
                  </Reveal>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-14 border-t border-line pt-8">
            <ActionLink a={p.action} />
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "sticky") {
    return (
      <Section block="process_steps" variant={variant} tone={t}>
        <Container>
          <div className="grid gap-12 lg:grid-cols-12 lg:gap-20">
            <div className="lg:col-span-5">
              <div className="lg:sticky lg:top-24">
                <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-5xl sm:leading-tight">{p.title}</h2>
                <p className={cn("mt-5 max-w-md text-lg leading-relaxed", quiet(t))}>{p.intro}</p>
                <div className="mt-8">
                  <ActionLink a={p.action} />
                </div>
              </div>
            </div>
            <ol className="flex flex-col gap-6 lg:col-span-7">
              {p.steps.map((s, i) => (
                <li
                  key={s.title}
                  className="group rounded-card border border-line bg-surface p-7 text-ink transition-colors hover:border-primary/40 sm:p-10"
                >
                  <div className="flex items-start justify-between gap-6">
                    <span className="font-head text-6xl font-semibold leading-none tracking-tight text-primary/20 transition-colors group-hover:text-primary sm:text-7xl">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    {s.time ? <span className="mt-2 rounded-full border border-line px-3 py-1 text-xs font-medium text-muted">{s.time}</span> : null}
                  </div>
                  <h3 className="mt-8 font-head text-2xl font-semibold tracking-tight">{s.title}</h3>
                  <p className="mt-3 max-w-lg text-base leading-relaxed text-muted">{s.line}</p>
                </li>
              ))}
            </ol>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="process_steps" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} align="center" />
        <ol className="relative grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8">
          <span aria-hidden="true" className="absolute left-0 right-0 top-6 hidden h-px bg-line lg:block" />
          {p.steps.map((s, i) => (
            <li key={s.title} className="relative min-w-0">
              <Reveal delay={i * 140}>
                <span className="relative flex size-12 items-center justify-center rounded-full border border-line bg-surface font-head text-lg font-semibold text-primary shadow-card">
                  {i + 1}
                </span>
                {s.time ? <p className={cn("mt-6 text-sm font-medium", quiet(t))}>{s.time}</p> : null}
                <h3 className={cn("font-head text-xl font-semibold tracking-tight", s.time ? "mt-1" : "mt-6")}>{s.title}</h3>
                <p className={cn("mt-2 text-base leading-relaxed", quiet(t))}>{s.line}</p>
              </Reveal>
            </li>
          ))}
        </ol>
        <div className="mt-14 flex justify-center">
          <ActionLink a={p.action} />
        </div>
      </Container>
    </Section>
  );
}
