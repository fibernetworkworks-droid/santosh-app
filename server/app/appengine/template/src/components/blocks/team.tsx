// v0.999.51 D1 block: Team. Three layouts - a photo grid with role and one line, a founder spotlight with her note
// above a row of the team, and a credits-style list (name, role, the year they joined).
import * as React from "react";
import { Quote } from "lucide-react";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/effects";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";

export const variants = ["grid", "founder", "list"] as const;
export type TeamVariant = (typeof variants)[number];

export interface TeamMember {
  name: string;
  role: string;
  line?: string;
  since?: string;
  photo?: string;
}

export interface TeamProps {
  variant?: TeamVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  members?: TeamMember[];
  founderNote?: string;
}

export const sample: Required<Omit<TeamProps, "variant" | "tone">> = {
  title: "The people you will meet",
  intro: "A small team that knows every regular by name.",
  members: [
    { name: "Meera Joshi", role: "Founder", line: "Started the place in 2014 with two chairs and a borrowed table.", since: "2014" },
    { name: "Arjun Patil", role: "Head of operations", line: "Keeps the calendar honest and the waiting time short.", since: "2016" },
    { name: "Fatima Shaikh", role: "Senior specialist", line: "Twelve years of practice; the one people ask for by name.", since: "2018" },
    { name: "Karthik Rao", role: "Customer care", line: "Answers every WhatsApp message, usually within ten minutes.", since: "2021" },
  ],
  founderNote:
    "I wanted a place where people are treated the way I would want my own mother treated. Ten years on, that is still the only rule we work by.",
};

function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0] ?? "")
    .join("")
    .toUpperCase();
}

function Face({ m, size }: { m: TeamMember; size: "sm" | "md" }) {
  const box = size === "sm" ? "size-14" : "size-20";
  if (m.photo) {
    return <img src={m.photo} alt={m.name} loading="lazy" className={cn("shrink-0 rounded-full object-cover", box)} />;
  }
  return (
    <span
      role="img"
      aria-label={m.name}
      className={cn("inline-flex shrink-0 items-center justify-center rounded-full bg-primary/10 font-head font-semibold text-primary", box, size === "sm" ? "text-base" : "text-xl")}
    >
      {initials(m.name)}
    </span>
  );
}

export default function Team({ variant = "grid", tone, ...rest }: TeamProps) {
  const d = { ...sample, ...rest };

  if (variant === "founder") {
    const [lead, ...others] = d.members;
    return (
      <Section block="team" variant={variant} tone={tone ?? "plain"}>
        <Container>
          {lead ? (
            <div className="grid items-center gap-10 lg:grid-cols-12 lg:gap-16">
              <div className="lg:col-span-5">
                <Picture src={lead.photo} alt={`${lead.name}, ${lead.role}`} label={lead.name} ratio="4/5" />
              </div>
              <div className="min-w-0 lg:col-span-7">
                <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{d.title}</h2>
                <Quote className="mt-8 size-8 text-primary" aria-hidden="true" />
                <blockquote className="mt-4 font-head text-2xl leading-snug text-ink sm:text-3xl">{d.founderNote}</blockquote>
                <p className="mt-6 text-base">
                  <span className="font-semibold text-ink">{lead.name}</span>
                  <span className="text-muted"> · {lead.role}</span>
                </p>
              </div>
            </div>
          ) : null}
          {others.length ? (
            <div className="mt-16 border-t border-line pt-10">
              <p className="text-base text-muted">{d.intro}</p>
              <ul className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                {others.map((m) => (
                  <li key={m.name} className="flex min-w-0 items-start gap-4">
                    <Face m={m} size="sm" />
                    <div className="min-w-0">
                      <h3 className="text-lg font-semibold text-ink">{m.name}</h3>
                      <p className="text-sm font-medium text-primary">{m.role}</p>
                      {m.line ? <p className="mt-2 text-sm leading-relaxed text-muted">{m.line}</p> : null}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Container>
      </Section>
    );
  }

  if (variant === "list") {
    return (
      <Section block="team" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <div className="grid gap-10 lg:grid-cols-12">
            <SectionHead title={d.title} intro={d.intro} className="lg:col-span-4 lg:mb-0" />
            <ol className="min-w-0 border-t border-line lg:col-span-8">
              {d.members.map((m) => (
                <li key={m.name} className="group grid grid-cols-1 gap-2 border-b border-line py-6 sm:grid-cols-12 sm:items-baseline sm:gap-6">
                  <div className="flex items-center gap-4 sm:col-span-5">
                    <Face m={m} size="sm" />
                    <h3 className="min-w-0 break-words font-head text-2xl font-semibold tracking-tight text-ink transition-colors group-hover:text-primary">
                      {m.name}
                    </h3>
                  </div>
                  <div className="min-w-0 sm:col-span-5">
                    <p className="font-medium text-ink">{m.role}</p>
                    {m.line ? <p className="mt-1 text-sm leading-relaxed text-muted">{m.line}</p> : null}
                  </div>
                  {m.since ? (
                    <p className="text-sm tabular-nums text-muted sm:col-span-2 sm:text-right">Since {m.since}</p>
                  ) : null}
                </li>
              ))}
            </ol>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="team" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={d.title} intro={d.intro} />
        <ul className="grid grid-cols-1 gap-x-6 gap-y-12 sm:grid-cols-2 lg:grid-cols-4">
          {d.members.map((m, i) => (
            <li key={m.name} className="min-w-0">
              <Reveal delay={i * 80}>
                <Picture src={m.photo} alt={`${m.name}, ${m.role}`} label={m.name} ratio="4/5" />
                <h3 className="mt-5 text-lg font-semibold text-ink">{m.name}</h3>
                <p className="text-sm font-medium text-primary">{m.role}</p>
                {m.line ? <p className="mt-2 text-sm leading-relaxed text-muted">{m.line}</p> : null}
              </Reveal>
            </li>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
