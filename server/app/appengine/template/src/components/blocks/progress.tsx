"use client"; // v0.999.79 D8: ticking steps needs JavaScript - on a pre-rendered site page it is an island
// v0.999.79 D8 wave 3 block: Progress - a learning path: the stages, what each one teaches, and a bar that fills as the
// visitor ticks what they have done. Said on the page: the ticks are kept only while the page is open (a website page
// keeps nothing on her phone or computer).
import * as React from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress as Bar } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["path"] as const;
export type ProgressVariant = (typeof variants)[number];

export interface Stage {
  title: string;
  line?: string;
}

export interface ProgressProps {
  variant?: ProgressVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  stages?: Stage[];
  note?: string;
}

export const sample: Required<Omit<ProgressProps, "variant" | "tone">> = {
  title: "Your path",
  intro: "Four stages from your first chord to your first song.",
  stages: [
    { title: "Hold the guitar", line: "Posture, the pick and tuning by ear." },
    { title: "Three chords", line: "G, C and D, and changing between them." },
    { title: "Strumming", line: "Down-up patterns with a steady count." },
  ],
  note: "Tick what you have done - the ticks stay while this page is open.",
};

export default function Progress({ variant = "path", tone, ...rest }: ProgressProps) {
  const p = { ...sample, ...rest };
  const id = React.useId();
  const [done, setDone] = React.useState<boolean[]>(() => p.stages.map(() => false));
  const n = done.filter(Boolean).length;
  const pct = p.stages.length ? Math.round((n / p.stages.length) * 100) : 0;
  return (
    <Section block="progress" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <div className="flex max-w-3xl flex-col gap-6">
          <div className="flex items-center gap-4">
            <Bar value={pct} aria-label="Stages done" className="flex-1" />
            <span className="text-sm font-medium tabular-nums">{n} of {p.stages.length}</span>
          </div>
          <ol className="flex flex-col gap-3">
            {p.stages.map((s, i) => (
              <li key={i} className={cn("flex items-start gap-4 rounded-card border border-line bg-surface p-5 transition-colors", done[i] && "border-ok")}>
                <Checkbox id={`${id}-${i}`} checked={done[i]} className="mt-1"
                  onCheckedChange={(v) => setDone((d) => d.map((x, j) => (j === i ? v === true : x)))} />
                <label htmlFor={`${id}-${i}`} className="flex cursor-pointer flex-col gap-1">
                  <span className="text-sm tabular-nums text-muted">Stage {i + 1}</span>
                  <span className={cn("font-head text-lg font-semibold", done[i] && "text-muted line-through")}>{s.title}</span>
                  {s.line ? <span className="text-muted">{s.line}</span> : null}
                </label>
              </li>
            ))}
          </ol>
          {p.note ? <p className="text-sm text-muted">{p.note}</p> : null}
        </div>
      </Container>
    </Section>
  );
}
