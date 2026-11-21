// v0.999.79 D8 wave 3 block: Resume - the work she has done (role, where, when, one line each) on a quiet timeline,
// what she is good at as plain chips, and what she studied. Only what she wrote: nothing is made up.
import * as React from "react";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["timeline"] as const;
export type ResumeVariant = (typeof variants)[number];

export interface ResumeRole {
  role: string;
  place?: string;
  when?: string;
  note?: string;
}

export interface ResumeProps {
  variant?: ResumeVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  roles?: ResumeRole[];
  skills?: string[];
  skillsTitle?: string;
  study?: string[];
  studyTitle?: string;
}

export const sample: Required<Omit<ResumeProps, "variant" | "tone">> = {
  title: "Where I have worked",
  intro: "Fourteen years of building products people use every day.",
  roles: [
    { role: "Design lead", place: "A payments company in Bengaluru", when: "2021 - now", note: "Led the checkout redesign used by small shops." },
    { role: "Product designer", place: "A travel booking start-up", when: "2016 - 2021", note: "Designed the mobile booking flow from the first sketch." },
  ],
  skills: ["Product design", "User research", "Design systems", "Workshops"],
  skillsTitle: "What I am good at",
  study: ["Bachelor of Design, a design college in Ahmedabad"],
  studyTitle: "Studied",
};

export default function Resume({ variant = "timeline", tone, ...rest }: ResumeProps) {
  const p = { ...sample, ...rest };
  return (
    <Section block="resume" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <SectionHead title={p.title} intro={p.intro} />
            <ol className="flex flex-col border-l border-line">
              {p.roles.map((r, i) => (
                <li key={i} className="relative flex flex-col gap-1 pb-8 pl-6 last:pb-0">
                  <span aria-hidden="true" className="absolute -left-1.5 top-1.5 size-3 rounded-full border-2 border-primary bg-bg" />
                  {r.when ? <span className="text-sm tabular-nums text-muted">{r.when}</span> : null}
                  <h3 className="font-head text-xl font-semibold">{r.role}</h3>
                  {r.place ? <p className="text-primary">{r.place}</p> : null}
                  {r.note ? <p className="max-w-prose text-muted">{r.note}</p> : null}
                </li>
              ))}
            </ol>
          </div>
          <div className="flex flex-col gap-10 lg:col-span-5">
            {p.skills.length ? (
              <div className="flex flex-col gap-4">
                <h3 className="font-head text-xl font-semibold">{p.skillsTitle}</h3>
                <ul className="flex flex-wrap gap-2">
                  {p.skills.map((s) => (
                    <li key={s} className="rounded-control bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary">{s}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {p.study.length ? (
              <div className="flex flex-col gap-3">
                <h3 className="font-head text-xl font-semibold">{p.studyTitle}</h3>
                <ul className="flex flex-col gap-2 text-muted">
                  {p.study.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </Container>
    </Section>
  );
}
