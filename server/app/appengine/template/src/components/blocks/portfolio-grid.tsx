// v0.999.51 D1 the kit: Portfolio - her projects as tiles, a masonry wall or one featured case with the rest listed.
// Category chips filter the work; a tap opens the project large in a lightbox.
import * as React from "react";
import { ArrowRight, ArrowUpRight, MapPin } from "lucide-react";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export const variants = ["tiles", "masonry", "featured"] as const;
export type PortfolioGridVariant = (typeof variants)[number];

export interface PortfolioItem {
  title: string;
  category: string;
  place?: string;
  year?: string;
  /** one plain line about what came of it */
  result?: string;
  summary?: string;
  /** her photo; without one a stand-in in the design's colours is drawn */
  image?: string;
}

export interface PortfolioGridProps {
  variant?: PortfolioGridVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  items?: PortfolioItem[];
  allLabel?: string;
  action?: { label: string; href: string };
}

export const sample: Required<Omit<PortfolioGridProps, "variant" | "tone">> = {
  title: "Selected work",
  intro: "Homes, workspaces and small shops we have planned and built over the last six years.",
  allLabel: "All work",
  action: { label: "Talk about your project", href: "#contact" },
  items: [
    {
      title: "Courtyard house",
      category: "Homes",
      place: "Alibag",
      year: "2025",
      result: "Handed over in 11 months, on the first budget",
      summary: "A weekend home built around an open courtyard and a neem tree the family did not want to lose. Lime plaster walls keep the rooms cool through May.",
    },
    {
      title: "Chartered accountant's office",
      category: "Workspaces",
      place: "Baner, Pune",
      year: "2024",
      result: "Room for 14 desks in 1,100 sq ft",
      summary: "Glass meeting rooms, a quiet records room and a reception that seats five clients during filing season.",
    },
    {
      title: "Filter coffee bar",
      category: "Shops & cafes",
      place: "Jayanagar, Bengaluru",
      year: "2024",
      result: "Opened in 9 weeks",
      summary: "A narrow 300 sq ft front with a standing counter, brass details and seating that folds against the wall.",
    },
    {
      title: "Two-bedroom renovation",
      category: "Homes",
      place: "Thane West",
      year: "2023",
      result: "Kitchen moved, no wall broken",
      summary: "A 1990s flat reworked for a couple who work from home: one bedroom became a study with full-height storage.",
    },
    {
      title: "Saree studio",
      category: "Shops & cafes",
      place: "Nashik Road",
      year: "2023",
      result: "Footfall up after the new window",
      summary: "Display walls for 400 sarees, a trial room with daylight lamps and a deep shop window facing the main road.",
    },
    {
      title: "Clinic and pharmacy",
      category: "Workspaces",
      place: "Aundh, Pune",
      year: "2022",
      result: "Patients wait in a seated, shaded front",
      summary: "Two consultation rooms, a dispensing counter and a waiting area that stays out of the street's dust.",
    },
  ],
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function Chips({ cats, active, onPick, allLabel }: { cats: string[]; active: string; onPick: (c: string) => void; allLabel: string }) {
  return (
    <div role="group" aria-label="Filter projects" className="mb-8 flex flex-wrap gap-2">
      {[allLabel, ...cats].map((c) => {
        const on = c === active;
        return (
          <button
            key={c}
            type="button"
            aria-pressed={on}
            onClick={() => onPick(c)}
            className={cn(
              "h-10 rounded-full border px-4 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
              on ? "border-primary bg-primary text-primary-ink" : "border-line bg-surface text-ink hover:border-ink/40",
            )}
          >
            {c}
          </button>
        );
      })}
    </div>
  );
}

function Meta({ item, className }: { item: PortfolioItem; className?: string }) {
  const bits = [item.place, item.year].filter(Boolean).join(" · ");
  if (!bits) return null;
  return (
    <p className={cn("flex items-center gap-1.5 text-sm", className)}>
      <MapPin className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="min-w-0 truncate">{bits}</span>
    </p>
  );
}

export default function PortfolioGrid({ variant = "tiles", tone, ...rest }: PortfolioGridProps) {
  const p = { ...sample, ...given(rest) };
  const cats = React.useMemo(() => Array.from(new Set(p.items.map((i) => i.category))), [p.items]);
  const [active, setActive] = React.useState(p.allLabel);
  const [open, setOpen] = React.useState<PortfolioItem | null>(null);
  const shown = active === p.allLabel ? p.items : p.items.filter((i) => i.category === active);
  const muted = soft(tone);

  const lightbox = (
    <Dialog open={open !== null} onOpenChange={(o) => !o && setOpen(null)}>
      <DialogContent className="max-w-3xl">
        {open ? (
          <>
            <Picture src={open.image} alt={open.title} label={open.title} ratio="3/2" />
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{open.category}</Badge>
                <Meta item={open} className="text-muted" />
              </div>
              <DialogTitle className="text-2xl">{open.title}</DialogTitle>
              {open.summary ? <DialogDescription className="text-base">{open.summary}</DialogDescription> : null}
              {open.result ? <p className="text-sm font-medium text-ok">{open.result}</p> : null}
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );

  if (variant === "featured") {
    const [lead, ...others] = p.items;
    return (
      <Section block="portfolio_grid" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <SectionHead title={p.title} intro={p.intro} />
          {lead ? (
            <article className="grid items-center gap-8 lg:grid-cols-12 lg:gap-12">
              <div className="lg:col-span-7">
                <Picture src={lead.image} alt={lead.title} label={lead.title} ratio="3/2" />
              </div>
              <div className="flex min-w-0 flex-col gap-4 lg:col-span-5">
                <Meta item={lead} className={muted} />
                <h3 className="font-head text-3xl font-semibold tracking-tight text-inherit sm:text-4xl">{lead.title}</h3>
                {lead.summary ? <p className={cn("text-base leading-relaxed", muted)}>{lead.summary}</p> : null}
                {lead.result ? (
                  <p className="border-l-2 border-primary pl-4 font-head text-lg font-medium">{lead.result}</p>
                ) : null}
                <div className="pt-2">
                  <Button variant="outline" className="border-current/25 text-inherit hover:bg-current/5" onClick={() => setOpen(lead)}>
                    See the project <ArrowRight className="size-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </article>
          ) : null}
          {others.length ? (
            <ul className="mt-14 divide-y divide-line border-y border-line">
              {others.map((item) => (
                <li key={item.title}>
                  <button
                    type="button"
                    onClick={() => setOpen(item)}
                    className="group flex w-full items-center gap-4 py-4 text-left transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:gap-6"
                  >
                    <Picture src={item.image} alt={item.title} ratio="4/3" className="w-24 shrink-0 sm:w-32" />
                    <span className="flex min-w-0 flex-1 flex-col gap-1">
                      <span className="font-head text-lg font-semibold break-words">{item.title}</span>
                      <Meta item={item} className={muted} />
                    </span>
                    <span className={cn("hidden text-sm sm:block", muted)}>{item.category}</span>
                    <ArrowUpRight className="size-5 shrink-0 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {lightbox}
        </Container>
      </Section>
    );
  }

  if (variant === "masonry") {
    const ratios = ["4/5", "4/3", "1/1", "3/4", "3/2", "4/5"] as const;
    return (
      <Section block="portfolio_grid" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container wide>
          <SectionHead title={p.title} intro={p.intro} className="mb-6 sm:mb-8" />
          <Chips cats={cats} active={active} onPick={setActive} allLabel={p.allLabel} />
          <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 [&>*]:mb-4">
            {shown.map((item, i) => (
              <button
                key={item.title}
                type="button"
                onClick={() => setOpen(item)}
                className="group relative block w-full break-inside-avoid overflow-hidden rounded-card text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                <Picture
                  src={item.image}
                  alt={item.title}
                  label={item.title}
                  ratio={ratios[i % ratios.length]}
                  className="transition-transform duration-500 group-hover:scale-105"
                />
                <span className="absolute inset-x-3 bottom-3 flex flex-col gap-0.5 rounded-control bg-surface/95 p-3 text-ink shadow-card transition-opacity duration-300 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-visible:opacity-100">
                  <span className="font-head text-base font-semibold">{item.title}</span>
                  <span className="text-xs text-muted">{[item.category, item.place].filter(Boolean).join(" · ")}</span>
                </span>
              </button>
            ))}
          </div>
          {lightbox}
        </Container>
      </Section>
    );
  }

  return (
    <Section block="portfolio_grid" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <div className="mb-2 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
          <a href={p.action.href} className="inline-flex shrink-0 items-center gap-1.5 text-sm font-medium underline-offset-4 hover:underline">
            {p.action.label} <ArrowRight className="size-4" aria-hidden="true" />
          </a>
        </div>
        <div className="mt-8">
          <Chips cats={cats} active={active} onPick={setActive} allLabel={p.allLabel} />
        </div>
        <ul className="grid gap-x-8 gap-y-12 sm:grid-cols-2">
          {shown.map((item) => (
            <li key={item.title} className="min-w-0">
              <button
                type="button"
                onClick={() => setOpen(item)}
                className="group flex w-full flex-col gap-4 text-left focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
              >
                <span className="block overflow-hidden rounded-card">
                  <Picture
                    src={item.image}
                    alt={item.title}
                    label={item.title}
                    ratio="3/2"
                    className="transition-transform duration-500 group-hover:scale-105"
                  />
                </span>
                <span className="flex items-start justify-between gap-4">
                  <span className="flex min-w-0 flex-col gap-1">
                    <span className="font-head text-xl font-semibold break-words">{item.title}</span>
                    <Meta item={item} className={muted} />
                  </span>
                  <Badge tone="outline" className="mt-1 border-current/25 text-inherit">{item.category}</Badge>
                </span>
                {item.result ? <span className={cn("text-sm", muted)}>{item.result}</span> : null}
              </button>
            </li>
          ))}
        </ul>
        {lightbox}
      </Container>
    </Section>
  );
}
