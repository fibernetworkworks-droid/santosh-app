"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 the kit: Areas served - a searchable list of localities and pincodes, locality chips with the
// delivery radius, or one panel per city. Only the areas she serves; "coming soon" ones are marked as such.
import * as React from "react";
import { ArrowRight, MapPin, Search, Truck } from "lucide-react";
import { Section, Container, SectionHead, type Tone } from "./_kit";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const variants = ["search", "chips", "cities"] as const;
export type CoverageAreasVariant = (typeof variants)[number];

export interface Area {
  name: string;
  city: string;
  pincode?: string;
  /** "soon" = she plans to serve it; shown apart, never as served */
  status?: "now" | "soon";
}

export interface CoverageAreasProps {
  variant?: CoverageAreasVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  areas?: Area[];
  /** one plain line, e.g. "Free delivery within 6 km of Kothrud" */
  radius?: string;
  action?: { label: string; href: string };
}

export const sample: Required<Omit<CoverageAreasProps, "variant" | "tone">> = {
  title: "Where we deliver",
  intro: "Search your area or pincode. If it is not here, message us - we often go a little further.",
  radius: "Same-day delivery within 8 km of our Kothrud kitchen. Orders before 11 am.",
  action: { label: "Ask about your area", href: "#contact" },
  areas: [
    { name: "Kothrud", city: "Pune", pincode: "411038" },
    { name: "Karve Nagar", city: "Pune", pincode: "411052" },
    { name: "Erandwane", city: "Pune", pincode: "411004" },
    { name: "Deccan Gymkhana", city: "Pune", pincode: "411004" },
    { name: "Warje", city: "Pune", pincode: "411058" },
    { name: "Bavdhan", city: "Pune", pincode: "411021" },
    { name: "Aundh", city: "Pune", pincode: "411007" },
    { name: "Baner", city: "Pune", pincode: "411045" },
    { name: "Shivaji Nagar", city: "Pune", pincode: "411005" },
    { name: "Wakad", city: "Pimpri-Chinchwad", pincode: "411057" },
    { name: "Pimple Saudagar", city: "Pimpri-Chinchwad", pincode: "411027" },
    { name: "Hinjewadi Phase 1", city: "Pimpri-Chinchwad", pincode: "411057" },
    { name: "Hadapsar", city: "Pune", pincode: "411028", status: "soon" },
    { name: "Kharadi", city: "Pune", pincode: "411014", status: "soon" },
  ],
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function byCity(list: Area[]) {
  const m = new Map<string, Area[]>();
  for (const a of list) m.set(a.city, [...(m.get(a.city) ?? []), a]);
  return Array.from(m.entries());
}

export default function CoverageAreas({ variant = "search", tone, ...rest }: CoverageAreasProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);
  const now = React.useMemo(() => p.areas.filter((a) => a.status !== "soon"), [p.areas]);
  const soon = React.useMemo(() => p.areas.filter((a) => a.status === "soon"), [p.areas]);
  const id = React.useId();
  const [q, setQ] = React.useState("");
  const cities = React.useMemo(() => byCity(now), [now]);
  const [city, setCity] = React.useState<string>(() => cities[0]?.[0] ?? "");

  if (variant === "chips") {
    return (
      <Section block="coverage_areas" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid gap-10 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <SectionHead title={p.title} intro={p.intro} className="mb-6 sm:mb-6" />
              {p.radius ? (
                <p className="flex gap-3 rounded-card border border-line p-4 text-sm">
                  <Truck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                  <span className="min-w-0">{p.radius}</span>
                </p>
              ) : null}
            </div>
            <div className="flex min-w-0 flex-col gap-8 lg:col-span-8">
              {byCity(now).map(([c, list]) => (
                <div key={c} className="flex flex-col gap-3">
                  <h3 className="font-head text-lg font-semibold text-inherit">{c}</h3>
                  <ul className="flex flex-wrap gap-2">
                    {list.map((a) => (
                      <li key={a.name} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-sm text-ink">
                        <MapPin className="size-3.5 text-primary" aria-hidden="true" />
                        {a.name}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {soon.length ? (
                <div className="flex flex-col gap-3 border-t border-line pt-6">
                  <h3 className="font-head text-base font-semibold text-inherit">Coming soon</h3>
                  <ul className="flex flex-wrap gap-2">
                    {soon.map((a) => (
                      <li key={a.name} className={cn("rounded-full border border-dashed border-line px-3 py-1.5 text-sm", muted)}>
                        {a.name}
                      </li>
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

  if (variant === "cities") {
    const current = cities.find(([c]) => c === city) ?? cities[0];
    return (
      <Section block="coverage_areas" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container>
          <SectionHead title={p.title} intro={p.intro} />
          <div className="grid gap-6 lg:grid-cols-12">
            <div role="tablist" aria-label="Cities" className="flex gap-2 overflow-x-auto pb-1 lg:col-span-4 lg:flex-col lg:overflow-visible">
              {cities.map(([c, list]) => {
                const on = current?.[0] === c;
                return (
                  <button
                    key={c}
                    type="button"
                    role="tab"
                    aria-selected={on}
                    onClick={() => setCity(c)}
                    className={cn(
                      "flex min-h-12 shrink-0 items-center justify-between gap-4 rounded-control border px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                      on ? "border-primary bg-primary text-primary-ink" : "border-line bg-bg text-ink hover:border-ink/40",
                    )}
                  >
                    <span className="font-head font-semibold">{c}</span>
                    <span className={cn("text-sm tabular-nums", on ? "opacity-80" : "text-muted")}>{list.length} areas</span>
                  </button>
                );
              })}
            </div>
            <div role="tabpanel" className="min-w-0 rounded-card border border-line bg-bg p-6 text-ink lg:col-span-8">
              {current ? (
                <>
                  <h3 className="mb-4 font-head text-xl font-semibold">{current[0]}</h3>
                  <ul className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
                    {current[1].map((a) => (
                      <li key={a.name} className="flex items-baseline justify-between gap-3 border-b border-line pb-3">
                        <span className="min-w-0 break-words">{a.name}</span>
                        {a.pincode ? <span className="text-sm text-muted tabular-nums">{a.pincode}</span> : null}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
              {p.radius ? <p className="mt-6 text-sm text-muted">{p.radius}</p> : null}
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  const term = q.trim().toLowerCase();
  const hits = term
    ? p.areas.filter((a) => a.name.toLowerCase().includes(term) || (a.pincode ?? "").includes(term) || a.city.toLowerCase().includes(term))
    : p.areas;
  return (
    <Section block="coverage_areas" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container className="max-w-3xl">
        <SectionHead title={p.title} intro={p.intro} />
        <div className="flex flex-col gap-2">
          <Label htmlFor={`${id}-q`}>Your area or pincode</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <Input
              id={`${id}-q`}
              type="search"
              inputMode="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. Baner or 411045"
              className="h-12 pl-9 text-base"
              aria-describedby={`${id}-n`}
            />
          </div>
          <p id={`${id}-n`} aria-live="polite" className={cn("text-sm", muted)}>
            {term ? `${hits.length} ${hits.length === 1 ? "match" : "matches"}` : `${now.length} areas served${soon.length ? `, ${soon.length} coming soon` : ""}`}
          </p>
        </div>
        {!term ? (
          <ul className="mt-6 grid gap-x-8 rounded-card border border-line bg-surface px-4 py-2 text-ink sm:grid-cols-2">
            {p.areas.map((a) => (
              <li key={`${a.name}-${a.city}`} className="flex items-baseline justify-between gap-3 border-b border-line py-2.5 last:border-b-0">
                <span className={cn("min-w-0 break-words", a.status === "soon" ? "text-muted" : "")}>
                  {a.name}
                  {a.status === "soon" ? <span className="text-xs"> - coming soon</span> : null}
                </span>
                {a.pincode ? <span className="text-sm text-muted tabular-nums">{a.pincode}</span> : null}
              </li>
            ))}
          </ul>
        ) : hits.length ? (
          <ul className="mt-6 divide-y divide-line overflow-hidden rounded-card border border-line bg-surface text-ink">
            {hits.map((a) => (
              <li key={`${a.name}-${a.city}`} className="flex items-center gap-3 px-4 py-3">
                <MapPin className={cn("size-4 shrink-0", a.status === "soon" ? "text-muted" : "text-primary")} aria-hidden="true" />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-medium break-words">{a.name}</span>
                  <span className="text-xs text-muted">{[a.city, a.pincode].filter(Boolean).join(" · ")}</span>
                </span>
                {a.status === "soon" ? <Badge tone="warn">Coming soon</Badge> : <Badge tone="ok">We deliver</Badge>}
              </li>
            ))}
          </ul>
        ) : (
          <div className="mt-6 flex flex-col items-start gap-4 rounded-card border border-dashed border-line p-6">
            <p className="text-base">
              <span className="font-medium">“{q.trim()}”</span> is not on our list yet.
            </p>
            <Button asChild variant="primary">
              <a href={p.action.href}>
                {p.action.label} <ArrowRight className="size-4" aria-hidden="true" />
              </a>
            </Button>
          </div>
        )}
        {p.radius ? (
          <p className={cn("mt-6 flex gap-2 text-sm", muted)}>
            <Truck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>{p.radius}</span>
          </p>
        ) : null}
      </Container>
    </Section>
  );
}
