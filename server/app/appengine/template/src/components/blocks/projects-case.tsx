// v0.999.51 D1 the kit: Case stories - one project told as problem / work / result, as numbers with the client's own
// words, or as a dated timeline with the progress she reports. Only her numbers and her client's consented words.
import * as React from "react";
import { Quote } from "lucide-react";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";
import { NumberTicker } from "@/components/effects";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const variants = ["story", "numbers", "timeline"] as const;
export type ProjectsCaseVariant = (typeof variants)[number];

export interface CaseStat {
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

export interface CaseStep {
  when: string;
  what: string;
  /** 0-100: how far this part got, from her own report */
  done?: number;
}

export interface ProjectsCaseProps {
  variant?: ProjectsCaseVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  client?: string;
  place?: string;
  problem?: string;
  work?: string;
  result?: string;
  stats?: CaseStat[];
  quote?: { text: string; name: string; role?: string };
  steps?: CaseStep[];
  image?: string;
  imageAlt?: string;
  action?: { label: string; href: string };
}

export const sample: Required<Omit<ProjectsCaseProps, "variant" | "tone">> = {
  title: "A school library, rebuilt over one summer",
  intro: "Zilla Parishad school, Sinnar taluka - 420 students, one room and nine weeks before the new term.",
  client: "ZP Primary School, Wadgaon",
  place: "Sinnar, Nashik",
  problem:
    "The library was a store room: books in sacks, one tube light, a leaking roof. Children borrowed a book a term, if that.",
  work:
    "We fixed the roof, opened two windows to the east, built low shelves the youngest can reach and catalogued 2,300 books in Marathi and English with the teachers.",
  result:
    "The room opened on the first day of term. Teachers now run a reading hour every Saturday and children take home a book a week.",
  stats: [
    { value: 2300, label: "books catalogued" },
    { value: 9, label: "weeks from start to opening" },
    { value: 4.2, decimals: 1, label: "books a child borrowed per month in the first term" },
  ],
  quote: {
    text: "The children come in before the bell now. Some of them read to their younger brothers on the steps outside.",
    name: "Sunita Deshmukh",
    role: "Head teacher",
  },
  steps: [
    { when: "April", what: "Roof repaired and two east windows opened", done: 100 },
    { when: "May", what: "Shelves built and painted by the village carpenter", done: 100 },
    { when: "May - June", what: "2,300 books sorted, labelled and entered in the register", done: 100 },
    { when: "June", what: "Reading corner and floor mats for classes 1 to 4", done: 80 },
  ],
  image: "",
  imageAlt: "The rebuilt school library with low wooden shelves",
  action: { label: "Plan a project with us", href: "#contact" },
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

export default function ProjectsCase({ variant = "story", tone, ...rest }: ProjectsCaseProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);
  const meta = [p.client, p.place].filter(Boolean).join(" · ");

  if (variant === "numbers") {
    return (
      <Section block="projects_case" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-5">
              <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
              <Picture src={p.image || undefined} alt={p.imageAlt} label={meta} ratio="4/5" className="hidden lg:flex" />
            </div>
            <div className="flex min-w-0 flex-col gap-10 lg:col-span-7">
              <dl className="grid gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-3">
                {p.stats.map((s) => (
                  <div key={s.label} className="flex flex-col gap-2 bg-surface p-6 text-ink">
                    <dt className="order-2 text-sm text-muted">{s.label}</dt>
                    <dd className="order-1 font-head text-4xl font-semibold tracking-tight">
                      <NumberTicker value={s.value} decimals={s.decimals} prefix={s.prefix} suffix={s.suffix} />
                    </dd>
                  </div>
                ))}
              </dl>
              <figure className="flex flex-col gap-5">
                <Quote className="size-8 text-primary" aria-hidden="true" />
                <blockquote className="font-head text-2xl leading-snug font-medium tracking-tight sm:text-3xl">
                  {p.quote.text}
                </blockquote>
                <figcaption className={cn("text-sm", muted)}>
                  <span className="font-semibold text-inherit">{p.quote.name}</span>
                  {p.quote.role ? `, ${p.quote.role}` : null}
                  {p.client ? ` - ${p.client}` : null}
                </figcaption>
              </figure>
              <p className={cn("max-w-prose text-base leading-relaxed", muted)}>{p.result}</p>
              <div>
                <Button asChild>
                  <a href={p.action.href}>{p.action.label}</a>
                </Button>
              </div>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "timeline") {
    return (
      <Section block="projects_case" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid gap-12 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <div className="lg:sticky lg:top-24">
                <SectionHead title={p.title} intro={p.intro} className="mb-6 sm:mb-8" />
                {meta ? <p className={cn("text-sm font-medium", muted)}>{meta}</p> : null}
                <p className="mt-6 max-w-prose text-base leading-relaxed">{p.problem}</p>
              </div>
            </div>
            <ol className="relative flex min-w-0 flex-col gap-10 border-l border-line pl-8 lg:col-span-7">
              {p.steps.map((s, i) => {
                const pct = Math.max(0, Math.min(100, s.done ?? 100));
                return (
                  <li key={`${s.when}-${i}`} className="relative flex flex-col gap-3">
                    <span
                      aria-hidden="true"
                      className={cn(
                        "absolute -left-10 top-1 size-4 rounded-full border-2",
                        pct >= 100 ? "border-primary bg-primary" : "border-primary bg-bg",
                      )}
                    />
                    <p className={cn("text-sm font-medium", muted)}>{s.when}</p>
                    <h3 className="font-head text-xl font-semibold text-inherit break-words">{s.what}</h3>
                    <div className="flex items-center gap-3">
                      <div
                        role="progressbar"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={pct}
                        aria-label={`${s.what}: ${pct}% done`}
                        className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-ink/10"
                      >
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-sm tabular-nums">{pct}%</span>
                    </div>
                  </li>
                );
              })}
              <li className="relative flex flex-col gap-3">
                <span aria-hidden="true" className="absolute -left-10 top-1 size-4 rounded-full border-2 border-ok bg-ok" />
                <p className="text-sm font-medium text-ok">Where it stands</p>
                <p className="text-base leading-relaxed">{p.result}</p>
              </li>
            </ol>
          </div>
        </Container>
      </Section>
    );
  }

  const parts = [
    { head: "What was wrong", body: p.problem },
    { head: "What we did", body: p.work },
    { head: "What changed", body: p.result },
  ];
  return (
    <Section block="projects_case" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <div className="grid items-end gap-8 lg:grid-cols-2">
          <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
          {meta ? <p className={cn("text-sm font-medium lg:text-right", muted)}>{meta}</p> : null}
        </div>
        <div className="mt-10">
          <Picture src={p.image || undefined} alt={p.imageAlt} label={meta} ratio="16/9" />
        </div>
        <div className="mt-12 grid gap-10 md:grid-cols-3 md:gap-12">
          {parts.map((part, i) => (
            <div key={part.head} className="flex min-w-0 flex-col gap-3 border-t border-line pt-6">
              <span className="font-head text-sm font-semibold tabular-nums text-primary">0{i + 1}</span>
              <h3 className="font-head text-xl font-semibold text-inherit">{part.head}</h3>
              <p className={cn("text-base leading-relaxed", i === 2 ? "" : muted)}>{part.body}</p>
            </div>
          ))}
        </div>
        <figure className="mt-14 flex flex-col gap-3 rounded-card bg-primary/10 p-6 sm:p-10">
          <blockquote className="font-head text-xl leading-snug font-medium sm:text-2xl">“{p.quote.text}”</blockquote>
          <figcaption className={cn("text-sm", muted)}>
            {p.quote.name}
            {p.quote.role ? `, ${p.quote.role}` : null}
          </figcaption>
        </figure>
      </Container>
    </Section>
  );
}
