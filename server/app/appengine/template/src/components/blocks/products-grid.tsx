// v0.999.51 D1 the kit: her products. Three layouts: grid (photo cards, name, price, order button), filter (category
// chips over a compact list with small photos - for a long catalogue), featured (one large product beside its story,
// a row of others below). Prices only when she gives them.
import * as React from "react";
import { ArrowRight, MessageCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, Picture, rupees, type Tone } from "./_kit";

export const variants = ["grid", "filter", "featured"] as const;
export type ProductsGridVariant = (typeof variants)[number];

export interface ProductItem {
  name: string;
  /** rupees; leave out when she has not given a price */
  price?: number;
  /** a short line: weight, size, what is inside */
  note?: string;
  category: string;
  photo?: string;
  /** a word on the photo: New, Eggless, Bestseller (her own words) */
  tag?: string;
}

export interface ProductsGridProps {
  variant?: ProductsGridVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  products?: ProductItem[];
  orderLabel?: string;
  orderHref?: string;
  /** featured: a few sentences about the first product */
  story?: string;
}

export const sample: Required<Omit<ProductsGridProps, "variant" | "tone">> = {
  title: "Today's bakes",
  intro: "Baked this morning. Order before 6 pm for delivery the same evening.",
  products: [
    { name: "Classic sourdough", price: 180, note: "500 g, 36-hour ferment", category: "Breads", tag: "Bestseller" },
    { name: "Chocolate truffle cake", price: 650, note: "500 g, serves 6", category: "Cakes" },
    { name: "Ladi pav", price: 40, note: "Pack of 6, soft and fresh", category: "Breads" },
    { name: "Nankhatai", price: 220, note: "250 g box, pure ghee", category: "Cookies", tag: "Eggless" },
    { name: "Mango cheesecake", price: 160, note: "One slice, Alphonso season only", category: "Cakes", tag: "New" },
    { name: "Multigrain loaf", price: 120, note: "400 g, seven grains and seeds", category: "Breads" },
    { name: "Atta jaggery cookies", price: 180, note: "250 g box, no refined sugar", category: "Cookies" },
    { name: "Red velvet jar cake", price: 140, note: "Single jar, cream cheese frosting", category: "Cakes" },
  ],
  orderLabel: "Order on WhatsApp",
  orderHref: "#contact",
  story:
    "Our oldest recipe. The dough rests for a day and a half before it meets the oven, so the crust cracks and the inside stays open and soft. It keeps for four days in a cloth bag.",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function Photo({ item, ratio = "4/5", className }: { item: ProductItem; ratio?: "4/5" | "1/1" | "4/3"; className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-card", className)}>
      <Picture
        src={item.photo}
        alt={item.name}
        label="Product photo"
        ratio={ratio}
        className="transition-transform duration-500 group-hover:scale-105"
      />
      {item.tag ? (
        <Badge tone="outline" className="absolute left-3 top-3 border-line bg-surface/95 text-ink shadow-card">
          {item.tag}
        </Badge>
      ) : null}
    </div>
  );
}

export default function ProductsGrid({ variant = "grid", tone, ...rest }: ProductsGridProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";
  const cats = React.useMemo(() => Array.from(new Set(p.products.map((x) => x.category))), [p.products]);
  const [cat, setCat] = React.useState<string>("All");

  if (variant === "filter") {
    const shown = cat === "All" ? p.products : p.products.filter((x) => x.category === cat);
    return (
      <Section block="products_grid" variant={variant} tone={t}>
        <Container>
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
            <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-2">
              {["All", ...cats].map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-pressed={cat === c}
                  onClick={() => setCat(c)}
                  className={cn(
                    "min-h-10 rounded-full border px-4 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                    cat === c ? "border-primary bg-primary text-primary-ink" : "border-line bg-surface text-ink hover:border-primary/50",
                  )}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
          <p className={cn("mt-8 text-sm", quiet(t))} aria-live="polite">
            Showing {shown.length} of {p.products.length}
          </p>
          <ul className="mt-4 grid gap-x-10 border-t border-line lg:grid-cols-2">
            {shown.map((x) => (
              <li key={x.name} className="group flex animate-fade-in items-center gap-4 border-b border-line py-4 sm:gap-5">
                <Photo item={{ ...x, tag: undefined }} ratio="1/1" className="w-20 shrink-0 sm:w-24" />
                <div className="min-w-0 flex-1">
                  <h3 className="break-words font-head text-lg font-semibold leading-snug tracking-tight">{x.name}</h3>
                  {x.note ? <p className={cn("mt-1 text-sm", quiet(t))}>{x.note}</p> : null}
                  {x.price !== undefined ? <p className="mt-1.5 font-semibold tabular-nums">{rupees(x.price)}</p> : null}
                </div>
                <Button asChild size="icon" variant="outline" className="shrink-0" aria-label={`${p.orderLabel}: ${x.name}`}>
                  <a href={p.orderHref}>
                    <MessageCircle className="size-4" aria-hidden="true" />
                  </a>
                </Button>
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  if (variant === "featured") {
    const [hero, ...others] = p.products;
    if (!hero) return null;
    return (
      <Section block="products_grid" variant={variant} tone={t}>
        <Container>
          <SectionHead title={p.title} intro={p.intro} />
          <article className="group grid items-center gap-8 lg:grid-cols-12 lg:gap-16">
            <Photo item={hero} ratio="4/3" className="lg:col-span-7" />
            <Reveal className="min-w-0 lg:col-span-5">
              <h3 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{hero.name}</h3>
              {hero.note ? <p className={cn("mt-2 text-base", quiet(t))}>{hero.note}</p> : null}
              <p className={cn("mt-6 text-lg leading-relaxed", quiet(t))}>{p.story}</p>
              <div className="mt-8 flex flex-wrap items-center gap-6">
                {hero.price !== undefined ? <span className="font-head text-3xl font-semibold tabular-nums">{rupees(hero.price)}</span> : null}
                <Button asChild size="lg">
                  <a href={p.orderHref}>
                    <MessageCircle className="size-4" aria-hidden="true" />
                    {p.orderLabel}
                  </a>
                </Button>
              </div>
            </Reveal>
          </article>
          <ul className="mt-16 grid grid-cols-2 gap-x-5 gap-y-10 border-t border-line pt-10 sm:mt-20 lg:grid-cols-4">
            {others.slice(0, 4).map((x) => (
              <li key={x.name} className="group min-w-0">
                <a href={p.orderHref} className="block rounded-card focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary">
                  <Photo item={x} ratio="1/1" />
                  <div className="mt-4 flex items-start justify-between gap-3">
                    <h3 className="min-w-0 break-words font-medium leading-snug">{x.name}</h3>
                    {x.price !== undefined ? <span className="shrink-0 text-sm font-semibold tabular-nums">{rupees(x.price)}</span> : null}
                  </div>
                  <span className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary">
                    Order
                    <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="products_grid" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <ul className="grid grid-cols-2 gap-x-4 gap-y-10 sm:gap-x-6 lg:grid-cols-4">
          {p.products.map((x) => (
            <li key={x.name} className="group flex min-w-0 flex-col">
              <Photo item={x} />
              <h3 className="mt-4 break-words font-head text-base font-semibold leading-snug tracking-tight sm:text-lg">{x.name}</h3>
              {x.note ? <p className={cn("mt-1 text-sm leading-snug", quiet(t))}>{x.note}</p> : null}
              <div className="mt-auto pt-3">
                {x.price !== undefined ? <p className="text-lg font-semibold tabular-nums">{rupees(x.price)}</p> : null}
                <Button asChild variant="outline" className="mt-3 w-full px-2">
                  <a href={p.orderHref}>
                    <MessageCircle className="size-4" aria-hidden="true" />
                    <span className="truncate">{p.orderLabel}</span>
                  </a>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
