// v0.999.82 D8 wave 3 block: Case studies - each piece of work told in three short parts: what was needed, what was
// done, what came of it (her words; a result only when she gave one). Cards side by side, or one under the other.
import * as React from "react";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["cards", "stacked"] as const;
export type CaseStudiesVariant = (typeof variants)[number];

export interface CaseStudy {
  title: string;
  kind?: string;
  need?: string;
  done?: string;
  result?: string;
}

export interface CaseStudiesProps {
  variant?: CaseStudiesVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  cases?: CaseStudy[];
  labels?: { need: string; done: string; result: string };
}

export const sample: Required<Omit<CaseStudiesProps, "variant" | "tone">> = {
  title: "Selected work",
  intro: "Three projects, told the way they happened.",
  cases: [
    { title: "A menu people can read in the dark", kind: "Restaurant", need: "Guests could not read the old menu in a dim room.",
      done: "A larger type, fewer words, prices lined up on the right.", result: "Orders of the new dishes went up in the first month." },
    { title: "A school's admission form on the phone", kind: "School", need: "Parents filled a paper form twice.",
      done: "One short form that saves as they go.", result: "" },
  ],
  labels: { need: "What was needed", done: "What I did", result: "What came of it" },
};

export default function CaseStudies({ variant = "cards", tone, ...rest }: CaseStudiesProps) {
  const p = { ...sample, ...rest };
  const stacked = variant === "stacked";
  return (
    <Section block="case_studies" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <div className={cn("grid gap-6", stacked ? "max-w-3xl" : "md:grid-cols-2 lg:grid-cols-3")}>
          {p.cases.map((c, i) => (
            <article key={i} className="flex flex-col gap-4 rounded-card border border-line bg-surface p-6 sm:p-8">
              {c.kind ? <p className="text-sm font-medium text-primary">{c.kind}</p> : null}
              <h3 className="text-balance font-head text-xl font-semibold leading-snug">{c.title}</h3>
              <dl className={cn("grid gap-4 text-sm", stacked && "sm:grid-cols-3")}>
                {([["need", c.need], ["done", c.done], ["result", c.result]] as const).map(([k, v]) =>
                  v ? (
                    <div key={k} className="flex flex-col gap-1">
                      <dt className="font-semibold text-ink">{p.labels[k]}</dt>
                      <dd className="leading-relaxed text-muted">{v}</dd>
                    </div>
                  ) : null,
                )}
              </dl>
            </article>
          ))}
        </div>
      </Container>
    </Section>
  );
}
