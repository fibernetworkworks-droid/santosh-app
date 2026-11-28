// v0.999.51 D1 the kit: Clients / partners (real only) - the names she works with as a slow text marquee, a grid of
// names, or grouped by the sector they come from. Names are text; a logo shows only when she gives the file.
import * as React from "react";
import { Section, Container, SectionHead, type Tone } from "./_kit";
import { Marquee } from "@/components/effects";
import { cn } from "@/lib/utils";

export const variants = ["marquee", "grid", "sectors"] as const;
export type LogosMarqueeVariant = (typeof variants)[number];

export interface ClientName {
  name: string;
  sector?: string;
  place?: string;
  /** her logo file, shown only when given (with the client's permission) */
  logo?: string;
}

export interface LogosMarqueeProps {
  variant?: LogosMarqueeVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  names?: ClientName[];
  /** a short line under the names, e.g. how long they have worked together */
  note?: string;
}

export const sample: Required<Omit<LogosMarqueeProps, "variant" | "tone">> = {
  title: "People who order from us again",
  intro: "Offices, schools and families across Pune who have stayed with us for years.",
  names: [
    { name: "Kulkarni & Associates", sector: "Offices", place: "Deccan" },
    { name: "Sahyadri Public School", sector: "Schools", place: "Kothrud" },
    { name: "Bhide Clinic", sector: "Clinics", place: "Aundh" },
    { name: "Shree Ganesh Traders", sector: "Shops", place: "Market Yard" },
    { name: "Lokmanya Co-op Bank", sector: "Offices", place: "Shivaji Nagar" },
    { name: "Gokhale Dental Care", sector: "Clinics", place: "Baner" },
    { name: "Vidya Niketan Junior College", sector: "Schools", place: "Hadapsar" },
    { name: "Patil Hardware", sector: "Shops", place: "Pimpri" },
    { name: "Nirmal Housing Society", sector: "Housing societies", place: "Wakad" },
    { name: "Ankur Montessori", sector: "Schools", place: "Viman Nagar" },
    { name: "Green Valley CHS", sector: "Housing societies", place: "Bavdhan" },
    { name: "Joshi Opticians", sector: "Shops", place: "Camp" },
  ],
  note: "Sample names - replace with clients who have agreed to be listed.",
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function Name({ c, className }: { c: ClientName; className?: string }) {
  if (c.logo) {
    return <img src={c.logo} alt={c.name} loading="lazy" className={cn("h-8 w-auto max-w-40 object-contain", className)} />;
  }
  return <span className={cn("font-head font-semibold tracking-tight whitespace-nowrap", className)}>{c.name}</span>;
}

export default function LogosMarquee({ variant = "marquee", tone, ...rest }: LogosMarqueeProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);

  if (variant === "grid") {
    return (
      <Section block="logos_marquee" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <SectionHead title={p.title} intro={p.intro} />
          <ul className="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line lg:grid-cols-4">
            {p.names.map((c) => (
              <li key={c.name} className="flex min-h-28 min-w-0 flex-col justify-center gap-1 bg-surface px-4 py-6 text-ink sm:px-5 transition-colors hover:bg-bg">
                <Name c={c} className="text-base whitespace-normal break-words" />
                {c.sector || c.place ? (
                  <span className="text-xs text-muted">{[c.sector, c.place].filter(Boolean).join(" · ")}</span>
                ) : null}
              </li>
            ))}
          </ul>
          {p.note ? <p className={cn("mt-5 text-xs", muted)}>{p.note}</p> : null}
        </Container>
      </Section>
    );
  }

  if (variant === "sectors") {
    const groups = new Map<string, ClientName[]>();
    for (const c of p.names) {
      const k = c.sector || "Others";
      groups.set(k, [...(groups.get(k) ?? []), c]);
    }
    return (
      <Section block="logos_marquee" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid gap-10 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
              {p.note ? <p className={cn("mt-6 text-xs", muted)}>{p.note}</p> : null}
            </div>
            <dl className="grid min-w-0 gap-x-10 gap-y-8 sm:grid-cols-2 lg:col-span-8">
              {Array.from(groups.entries()).map(([sector, list]) => (
                <div key={sector} className="min-w-0 border-t border-line pt-4">
                  <dt className="flex items-baseline justify-between gap-3">
                    <span className="font-head text-lg font-semibold">{sector}</span>
                    <span className={cn("text-sm tabular-nums", muted)}>{list.length}</span>
                  </dt>
                  {list.map((c) => (
                    <dd key={c.name} className={cn("mt-2 text-sm break-words", muted)}>
                      {c.name}
                      {c.place ? <span className="opacity-70"> - {c.place}</span> : null}
                    </dd>
                  ))}
                </div>
              ))}
            </dl>
          </div>
        </Container>
      </Section>
    );
  }

  const half = Math.ceil(p.names.length / 2);
  const rows = [p.names.slice(0, half), p.names.slice(half)].filter((r) => r.length);
  return (
    <Section block="logos_marquee" variant={variant} tone={tone ?? "plain"} className="overflow-hidden [&_h2]:text-inherit">
      <Container>
        <SectionHead title={p.title} intro={p.intro} align="center" />
      </Container>
      <div className="flex flex-col gap-6" aria-hidden="true">
        {rows.map((row, i) => (
          <Marquee key={i} reverse={i % 2 === 1} seconds={40 + i * 8}>
            {row.map((c) => (
              <span key={c.name} className="flex items-center gap-12">
                <Name c={c} className="text-2xl opacity-80 sm:text-3xl" />
                <span aria-hidden="true" className="size-1.5 rounded-full bg-primary" />
              </span>
            ))}
          </Marquee>
        ))}
      </div>
      <ul className="sr-only">
        {p.names.map((c) => (
          <li key={c.name}>{c.name}</li>
        ))}
      </ul>
      {p.note ? (
        <Container>
          <p className={cn("mt-8 text-center text-xs", muted)}>{p.note}</p>
        </Container>
      ) : null}
    </Section>
  );
}
