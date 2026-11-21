// v0.999.79 D8 wave 3 block: Venue - where it happens: the place, its address, how to get there (her lines), and a
// button that opens the address in the visitor's maps app. No map is drawn on the page (fast, nothing to load).
import * as React from "react";
import { MapPin, Navigation } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["card"] as const;
export type VenueVariant = (typeof variants)[number];

export interface VenueProps {
  variant?: VenueVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  place?: string;
  address?: string;
  ways?: string[];
  mapLabel?: string;
}

export const sample: Required<Omit<VenueProps, "variant" | "tone">> = {
  title: "Where it is",
  intro: "",
  place: "The Banyan Courtyard",
  address: "Off Law College Road, Pune 411004",
  ways: ["Ten minutes by auto from Deccan bus stop", "Parking inside the gate for cars and two-wheelers"],
  mapLabel: "Open in maps",
};

export default function Venue({ variant = "card", tone, ...rest }: VenueProps) {
  const p = { ...sample, ...rest };
  const map = p.address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([p.place, p.address].filter(Boolean).join(", "))}` : "";
  return (
    <Section block="venue" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro || undefined} />
        <div className="grid gap-8 rounded-card border border-line bg-surface p-6 sm:p-8 md:grid-cols-2 md:gap-12">
          <div className="flex flex-col gap-4">
            <p className="inline-flex items-start gap-3">
              <MapPin className="mt-1 size-5 shrink-0 text-primary" aria-hidden="true" />
              <span className="flex flex-col gap-1">
                {p.place ? <span className="font-head text-xl font-semibold">{p.place}</span> : null}
                {p.address ? <span className="text-muted">{p.address}</span> : null}
              </span>
            </p>
            {map ? (
              <Button asChild variant="secondary" className="w-fit">
                <a href={map} target="_blank" rel="noreferrer">
                  <Navigation className="size-4" aria-hidden="true" />
                  {p.mapLabel}
                </a>
              </Button>
            ) : null}
          </div>
          {p.ways.length ? (
            <ul className="flex flex-col gap-3 text-muted">
              {p.ways.map((w) => (
                <li key={w} className="border-l-2 border-primary/40 pl-4">{w}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </Container>
    </Section>
  );
}
