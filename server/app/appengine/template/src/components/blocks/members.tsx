// v0.999.82 D8 wave 3 block: Members - the people of a community, club or group: a name, what they do in it, one line
// (only the people she lists - nobody is shown without her writing them in). Initials stand in for photos.
import * as React from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["grid"] as const;
export type MembersVariant = (typeof variants)[number];

export interface Member {
  name: string;
  role?: string;
  note?: string;
}

export interface MembersProps {
  variant?: MembersVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  members?: Member[];
  action?: { label: string; href: string };
}

export const sample: Required<Omit<MembersProps, "variant" | "tone">> = {
  title: "Who we are",
  intro: "Neighbours who meet every Sunday morning to clean and plant the lake shore.",
  members: [
    { name: "Ravi Deshmukh", role: "Started the group", note: "Retired teacher, knows every tree here." },
    { name: "Fatima Shaikh", role: "Plants and seeds" },
    { name: "Joseph Dsouza", role: "Sunday mornings" },
  ],
  action: { label: "Join us", href: "#contact" },
};

const initials = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() || "").join("");

export default function Members({ variant = "grid", tone, ...rest }: MembersProps) {
  const p = { ...sample, ...rest };
  return (
    <Section block="members" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {p.members.map((m) => (
            <li key={m.name} className="flex items-start gap-4 rounded-card border border-line bg-surface p-5">
              <span aria-hidden="true" className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/10 font-head text-lg font-semibold text-primary">
                {initials(m.name)}
              </span>
              <div className="flex flex-col gap-1">
                <h3 className="font-semibold">{m.name}</h3>
                {m.role ? <p className="text-sm text-primary">{m.role}</p> : null}
                {m.note ? <p className="text-sm text-muted">{m.note}</p> : null}
              </div>
            </li>
          ))}
        </ul>
        {p.action?.href ? (
          <Button asChild size="lg" className="mt-10 w-fit">
            <a href={p.action.href}>
              {p.action.label}
              <ArrowRight className="size-4" aria-hidden="true" />
            </a>
          </Button>
        ) : null}
      </Container>
    </Section>
  );
}
