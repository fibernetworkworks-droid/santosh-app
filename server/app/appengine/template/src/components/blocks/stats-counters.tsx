// v0.999.51 D1 the kit: her numbers, counting up once as they come into view. Three layouts: row (four counters
// split by thin rules under a heading), band (the numbers on a full colour band, centred), feature (one very large
// number with its context, the rest in a short list beside it). Only her own numbers.
import * as React from "react";
import { NumberTicker } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["row", "band", "feature"] as const;
export type StatsCountersVariant = (typeof variants)[number];

export interface StatItem {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  label: string;
  /** a short line under the label: since 2012, across 14 areas */
  note?: string;
}

export interface StatsCountersProps {
  variant?: StatsCountersVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  stats?: StatItem[];
  /** feature: a few sentences that make the big number mean something */
  context?: string;
}

export const sample: Required<Omit<StatsCountersProps, "variant" | "tone">> = {
  title: "Twelve years of fixing Chennai's homes",
  intro: "Counted from our own job sheets, not guessed.",
  stats: [
    { value: 18400, suffix: "+", label: "Repairs finished", note: "Since we opened in 2013" },
    { value: 46, label: "Areas we cover", note: "From Tambaram to Ennore" },
    { value: 4.8, decimals: 1, suffix: " / 5", label: "Average rating", note: "From 2,310 Google reviews" },
    { value: 90, suffix: " min", label: "Usual arrival time", note: "For calls before 6 pm" },
  ],
  context:
    "That is roughly four homes every day for twelve years: leaking taps, tripped mains, ceiling fans that wobble. Most of them called us again the next time something broke.",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function Num({ s, className }: { s: StatItem; className?: string }) {
  return (
    <NumberTicker
      value={s.value}
      decimals={s.decimals ?? 0}
      prefix={s.prefix ?? ""}
      suffix={s.suffix ?? ""}
      className={cn("font-head font-semibold tracking-tight", className)}
    />
  );
}

export default function StatsCounters({ variant = "row", tone, ...rest }: StatsCountersProps) {
  const p = withSample(sample, rest);

  if (variant === "band") {
    const t = tone ?? "primary";
    return (
      <Section block="stats_counters" variant={variant} tone={t} tight>
        <Container wide>
          <h2 className="mx-auto max-w-2xl text-center font-head text-2xl font-semibold tracking-tight sm:text-3xl">{p.title}</h2>
          <dl className="mt-10 grid grid-cols-2 gap-y-10 sm:mt-12 lg:grid-cols-4">
            {p.stats.map((s) => (
              <div key={s.label} className="flex min-w-0 flex-col-reverse items-center px-3 text-center">
                <dt className={cn("mt-2 text-sm sm:text-base", quiet(t))}>{s.label}</dt>
                <dd>
                  <Num s={s} className="text-4xl sm:text-6xl" />
                </dd>
              </div>
            ))}
          </dl>
        </Container>
      </Section>
    );
  }

  const t = tone ?? "plain";

  if (variant === "feature") {
    const [big, ...more] = p.stats;
    if (!big) return null;
    return (
      <Section block="stats_counters" variant={variant} tone={t}>
        <Container>
          <div className="grid items-end gap-12 lg:grid-cols-12 lg:gap-16">
            <div className="min-w-0 lg:col-span-7">
              <h2 className={cn("text-base font-medium sm:text-lg", quiet(t))}>{p.title}</h2>
              <p className="mt-4 break-words">
                <Num s={big} className="text-7xl leading-none text-primary sm:text-9xl" />
              </p>
              <p className="mt-4 font-head text-2xl font-semibold tracking-tight sm:text-3xl">{big.label}</p>
              <p className={cn("mt-5 max-w-xl text-lg leading-relaxed", quiet(t))}>{p.context}</p>
            </div>
            <dl className="divide-y divide-line border-y border-line lg:col-span-5">
              {more.map((s) => (
                <div key={s.label} className="flex items-baseline justify-between gap-6 py-5">
                  <dt className="min-w-0">
                    <span className="block font-medium">{s.label}</span>
                    {s.note ? <span className={cn("mt-0.5 block text-sm", quiet(t))}>{s.note}</span> : null}
                  </dt>
                  <dd className="shrink-0">
                    <Num s={s} className="text-3xl sm:text-4xl" />
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="stats_counters" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <dl className="grid grid-cols-2 gap-x-6 gap-y-12 lg:grid-cols-4">
          {p.stats.map((s) => (
            <div key={s.label} className="flex min-w-0 flex-col-reverse border-l border-line pl-5 sm:pl-6">
              <dt className="mt-3">
                <span className="block font-medium">{s.label}</span>
                {s.note ? <span className={cn("mt-1 block text-sm leading-snug", quiet(t))}>{s.note}</span> : null}
              </dt>
              <dd>
                <Num s={s} className="text-3xl sm:text-5xl lg:text-6xl" />
              </dd>
            </div>
          ))}
        </dl>
      </Container>
    </Section>
  );
}
