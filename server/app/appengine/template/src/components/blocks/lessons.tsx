"use client"; // v0.999.82 D8: the opening parts need JavaScript - on a pre-rendered site page it is an island
// v0.999.82 D8 wave 3 block: Lessons - a course in parts: each part (module) opens to its lessons, with how long each
// takes when she said so. The first part is open; every lesson is in the page's HTML for search engines.
import * as React from "react";
import { PlayCircle } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["modules"] as const;
export type LessonsVariant = (typeof variants)[number];

export interface Lesson {
  title: string;
  length?: string;
}

export interface Module {
  title: string;
  line?: string;
  lessons: Lesson[];
}

export interface LessonsProps {
  variant?: LessonsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  modules?: Module[];
}

export const sample: Required<Omit<LessonsProps, "variant" | "tone">> = {
  title: "What the course covers",
  intro: "Six weeks, one part a week, each lesson short enough for a tea break.",
  modules: [
    { title: "Week 1 - Holding the brush", line: "Water, paper and the first wash.", lessons: [
      { title: "Your paper and why it matters", length: "8 min" },
      { title: "The flat wash", length: "12 min" },
    ] },
    { title: "Week 2 - Colour", lessons: [{ title: "Mixing greens from two tubes", length: "10 min" }] },
  ],
};

export default function Lessons({ variant = "modules", tone, ...rest }: LessonsProps) {
  const p = { ...sample, ...rest };
  const total = p.modules.reduce((n, m) => n + m.lessons.length, 0);
  return (
    <Section block="lessons" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro}>
          <p className="text-sm text-muted">{p.modules.length} parts · {total} lessons</p>
        </SectionHead>
        <Accordion type="single" collapsible defaultValue="m0" className="max-w-3xl rounded-card border border-line bg-surface px-5 sm:px-6">
          {p.modules.map((m, i) => (
            <AccordionItem key={i} value={`m${i}`}>
              <AccordionTrigger className="py-5 text-left">
                <span className="flex flex-col gap-1">
                  <span className="font-head text-lg font-semibold">{m.title}</span>
                  {m.line ? <span className="text-sm font-normal text-muted">{m.line}</span> : null}
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <ol className="flex flex-col gap-1 pb-4">
                  {m.lessons.map((l, j) => (
                    <li key={j} className="flex items-center gap-3 rounded-control px-2 py-2">
                      <PlayCircle className="size-4 shrink-0 text-primary" aria-hidden="true" />
                      <span className="flex-1">{l.title}</span>
                      {l.length ? <span className="text-sm tabular-nums text-muted">{l.length}</span> : null}
                    </li>
                  ))}
                </ol>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </Container>
    </Section>
  );
}
