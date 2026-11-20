// v0.999.51 D1 the kit: a menu. Three layouts: leaders (a printed menu in two columns, dotted lines to the price),
// tabs (one tab per meal with today's special above), board (the whole menu on a dark board, chalk-like headings).
// Veg / non-veg marks only where she says.
import * as React from "react";
import { Flame } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Reveal } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";

export const variants = ["leaders", "tabs", "board"] as const;
export type MenuListVariant = (typeof variants)[number];

export interface MenuItem {
  name: string;
  price: number;
  note?: string;
  /** true = veg, false = non-veg, leave out when it does not apply */
  veg?: boolean;
  spicy?: boolean;
}

export interface MenuCategory {
  name: string;
  /** a line under the category: served 7 am to 11 am */
  line?: string;
  items: MenuItem[];
}

export interface MenuListProps {
  variant?: MenuListVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  categories?: MenuCategory[];
  special?: { name: string; line: string; price: number };
  /** a short line at the bottom: taxes, allergens */
  footnote?: string;
}

export const sample: Required<Omit<MenuListProps, "variant" | "tone">> = {
  title: "The menu",
  intro: "Cooked to order in our kitchen in Indiranagar. Ask us to make anything less spicy.",
  categories: [
    {
      name: "Breakfast",
      line: "7 am to 11 am",
      items: [
        { name: "Ghee podi idli", price: 90, note: "Four mini idlis, gunpowder, ghee", veg: true, spicy: true },
        { name: "Masala dosa", price: 110, note: "Potato palya, coconut chutney, sambar", veg: true },
        { name: "Akki roti", price: 100, note: "Rice roti with dill and onion", veg: true },
        { name: "Egg bhurji pav", price: 120, note: "Two pav, green chilli, coriander", veg: false },
      ],
    },
    {
      name: "Lunch",
      line: "12 noon to 3:30 pm",
      items: [
        { name: "South Indian thali", price: 220, note: "Rice, sambar, rasam, two palyas, curd", veg: true },
        { name: "Bisi bele bath", price: 150, note: "With boondi and papad", veg: true },
        { name: "Chicken ghee roast", price: 290, note: "Mangalorean style, with neer dosa", veg: false, spicy: true },
        { name: "Curd rice", price: 110, note: "Pomegranate, mustard tempering", veg: true },
      ],
    },
    {
      name: "Drinks",
      line: "All day",
      items: [
        { name: "Filter coffee", price: 40, note: "Brass dabara, as it should be", veg: true },
        { name: "Masala chaas", price: 50, note: "Ginger, curry leaf, jeera", veg: true },
        { name: "Tender coconut", price: 70, veg: true },
        { name: "Rose milk", price: 80, note: "Chilled, with sabja seeds", veg: true },
      ],
    },
  ],
  special: { name: "Neer dosa with chicken sukka", line: "Today only, until it runs out", price: 260 },
  footnote: "Prices include GST. Tell us about any allergy when you order.",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

/** The Indian food mark: a square with a dot, green for veg, red for non-veg. */
function FoodMark({ veg }: { veg?: boolean }) {
  if (veg === undefined) return null;
  return (
    <span
      role="img"
      aria-label={veg ? "Vegetarian" : "Non-vegetarian"}
      className={cn("inline-flex size-3.5 shrink-0 items-center justify-center rounded-none border", veg ? "border-ok" : "border-bad")}
    >
      <span className={cn("size-1.5 rounded-full", veg ? "bg-ok" : "bg-bad")} />
    </span>
  );
}

function Line({ item, t, dotted = true }: { item: MenuItem; t: Tone; dotted?: boolean }) {
  return (
    <li className="py-3">
      <div className="flex items-baseline gap-2">
        <span className="flex min-w-0 items-center gap-2">
          <FoodMark veg={item.veg} />
          <span className="break-words font-medium">{item.name}</span>
          {item.spicy ? <Flame className="size-3.5 shrink-0 text-bad" aria-label="Spicy" /> : null}
        </span>
        {dotted ? <span aria-hidden="true" className="min-w-6 flex-1 -translate-y-1 border-b border-dotted border-current opacity-30" /> : <span className="flex-1" />}
        <span className="shrink-0 font-medium tabular-nums">{rupees(item.price)}</span>
      </div>
      {item.note ? <p className={cn("mt-1 pl-5.5 text-sm", quiet(t))}>{item.note}</p> : null}
    </li>
  );
}

export default function MenuList({ variant = "leaders", tone, ...rest }: MenuListProps) {
  const p = withSample(sample, rest);

  if (variant === "tabs") {
    const t = tone ?? "plain";
    const first = p.categories[0]?.name ?? "";
    return (
      <Section block="menu_list" variant={variant} tone={t}>
        <Container className="max-w-4xl">
          <SectionHead title={p.title} intro={p.intro} />
          <div className="mb-10 flex flex-col gap-4 rounded-card border border-primary/30 bg-primary/10 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
            <div className="min-w-0">
              <p className="text-sm font-medium text-primary">Today's special</p>
              <h3 className="mt-1 break-words font-head text-2xl font-semibold tracking-tight">{p.special.name}</h3>
              <p className={cn("mt-1 text-sm", quiet(t))}>{p.special.line}</p>
            </div>
            <span className="shrink-0 font-head text-3xl font-semibold tabular-nums">{rupees(p.special.price)}</span>
          </div>
          <Tabs defaultValue={first}>
            <div className="-mx-4 overflow-x-auto px-4">
              <TabsList className="border border-line bg-surface">
                {p.categories.map((c) => (
                  <TabsTrigger key={c.name} value={c.name} className="min-h-10 px-4">
                    {c.name}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            {p.categories.map((c) => (
              <TabsContent key={c.name} value={c.name} className="mt-6">
                {c.line ? <p className={cn("mb-2 text-sm", quiet(t))}>{c.line}</p> : null}
                <ul className="grid gap-x-12 divide-y divide-line sm:grid-cols-2 sm:divide-y-0">
                  {c.items.map((x) => (
                    <Line key={x.name} item={x} t={t} dotted={false} />
                  ))}
                </ul>
              </TabsContent>
            ))}
          </Tabs>
          <p className={cn("mt-10 text-sm", quiet(t))}>{p.footnote}</p>
        </Container>
      </Section>
    );
  }

  if (variant === "board") {
    const t = tone ?? "plain";
    return (
      <Section block="menu_list" variant={variant} tone={t}>
        <Container>
          <div className="rounded-card bg-ink px-6 py-10 text-bg shadow-card sm:px-12 sm:py-14">
            <div className="flex flex-col items-center text-center">
              <h2 className="font-head text-4xl font-semibold italic tracking-tight sm:text-6xl">{p.title}</h2>
              <p className="mt-3 max-w-lg text-base text-bg/70">{p.intro}</p>
              <div className="mt-8 w-full max-w-md border-y border-dashed border-bg/30 py-5">
                <p className="text-sm text-accent">Today's special</p>
                <p className="mt-1 font-head text-2xl font-semibold">{p.special.name}</p>
                <p className="mt-1 text-sm text-bg/70">
                  {p.special.line} · <span className="font-medium text-bg tabular-nums">{rupees(p.special.price)}</span>
                </p>
              </div>
            </div>
            <div className="mt-12 grid gap-12 md:grid-cols-2 lg:grid-cols-3">
              {p.categories.map((c) => (
                <div key={c.name} className="min-w-0">
                  <h3 className="border-b border-bg/20 pb-3 font-head text-2xl font-semibold italic">{c.name}</h3>
                  {c.line ? <p className="mt-2 text-xs text-bg/60">{c.line}</p> : null}
                  <ul className="mt-2">
                    {c.items.map((x) => (
                      <Line key={x.name} item={x} t="ink" />
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="mt-12 text-center text-sm text-bg/60">{p.footnote}</p>
          </div>
        </Container>
      </Section>
    );
  }

  const t = tone ?? "surface";
  return (
    <Section block="menu_list" variant={variant} tone={t}>
      <Container className="max-w-5xl">
        <SectionHead title={p.title} intro={p.intro} align="center" />
        <div className="grid gap-x-16 gap-y-14 md:grid-cols-2">
          {p.categories.map((c, i) => (
            <Reveal key={c.name} delay={i * 100} className="min-w-0">
              <div className="flex items-baseline justify-between gap-4 border-b-2 border-current pb-3">
                <h3 className="font-head text-2xl font-semibold tracking-tight">{c.name}</h3>
                {c.line ? <span className={cn("text-sm", quiet(t))}>{c.line}</span> : null}
              </div>
              <ul className="mt-2">
                {c.items.map((x) => (
                  <Line key={x.name} item={x} t={t} />
                ))}
              </ul>
            </Reveal>
          ))}
          <div className="flex flex-col justify-center rounded-card border border-dashed border-primary/40 p-8 text-center md:col-start-2">
            <p className="text-sm font-medium text-primary">Today's special</p>
            <p className="mt-2 font-head text-2xl font-semibold tracking-tight">{p.special.name}</p>
            <p className={cn("mt-1 text-sm", quiet(t))}>{p.special.line}</p>
            <p className="mt-4 font-head text-3xl font-semibold tabular-nums">{rupees(p.special.price)}</p>
          </div>
        </div>
        <p className={cn("mt-14 text-center text-sm", quiet(t))}>{p.footnote}</p>
      </Container>
    </Section>
  );
}
