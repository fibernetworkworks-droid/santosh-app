"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 the kit: what she offers. Three layouts: cards (three columns, a soft light follows the pointer),
// numbered (a title that stays put on the left, a list of large numbers 01, 02 on the right whose detail opens on
// hover / focus), tabs (one tab per kind of service, rows with her prices).
import * as React from "react";
import { ArrowRight, Cake, Coffee, Gift, Package, Sparkles, Truck, Wheat, Users, type LucideIcon } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SpotlightCard } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";

export const variants = ["cards", "numbered", "tabs"] as const;
export type ServicesGridVariant = (typeof variants)[number];

const ICONS = { cake: Cake, coffee: Coffee, gift: Gift, package: Package, sparkles: Sparkles, truck: Truck, wheat: Wheat, users: Users } satisfies Record<string, LucideIcon>;
export type ServiceIcon = keyof typeof ICONS;

export interface ServiceItem {
  name: string;
  line: string;
  /** a longer line shown when the row opens (numbered) */
  detail?: string;
  /** her price, in rupees; leave out when she has none */
  price?: number;
  /** "from" before the price */
  from?: boolean;
  category: string;
  icon?: ServiceIcon;
}

export interface ServicesGridProps {
  variant?: ServicesGridVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  services?: ServiceItem[];
  /** where "Ask about this" goes */
  askHref?: string;
  askLabel?: string;
}

export const sample: Required<Omit<ServicesGridProps, "variant" | "tone">> = {
  title: "What we bake and make",
  intro: "Everything is made in our own kitchen. Order a day ahead for cakes and boxes.",
  services: [
    { name: "Custom cakes", line: "Birthday, anniversary and naming-day cakes in your flavour.", detail: "Tell us the size, the flavour and the message. Eggless on request, ready in 24 hours.", price: 850, from: true, category: "Cakes", icon: "cake" },
    { name: "Daily breads", line: "Sourdough, multigrain and soft pav, out of the oven by 7 am.", detail: "Sliced on request. Ask for a standing order and we keep yours aside every morning.", price: 60, from: true, category: "Breads", icon: "wheat" },
    { name: "Festival boxes", line: "Diwali, Rakhi and Eid boxes of cookies and dry cakes.", detail: "Choose from three sizes, add a printed note, and we deliver to up to 20 addresses.", price: 499, from: true, category: "Gifting", icon: "gift" },
    { name: "Office orders", line: "Breakfast trays and evening snacks for teams of 10 to 200.", detail: "Weekly menus, GST bills and one person you can call. Delivered by 9 am.", category: "Gifting", icon: "users" },
    { name: "Cafe corner", line: "Cutting chai, filter coffee and a fresh puff at the counter.", detail: "Six seats by the window, open all day. Bring your laptop, the Wi-Fi is free.", price: 30, from: true, category: "Cafe", icon: "coffee" },
    { name: "Home delivery", line: "Within 4 km of Karve Road, in under an hour.", detail: "Free above ₹500. Order on WhatsApp or call the shop; we confirm the time with you.", category: "Cafe", icon: "truck" },
  ],
  askHref: "#contact",
  askLabel: "Ask about this",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function priceText(s: ServiceItem) {
  if (s.price === undefined) return null;
  return (s.from ? "from " : "") + rupees(s.price);
}

export default function ServicesGrid({ variant = "cards", tone, ...rest }: ServicesGridProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";

  if (variant === "numbered") {
    return (
      <Section block="services_grid" variant={variant} tone={t}>
        <Container>
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
            <div className="lg:col-span-4">
              <div className="lg:sticky lg:top-24">
                <SectionHead title={p.title} intro={p.intro} className="mb-0" />
              </div>
            </div>
            <ol className="divide-y divide-line border-y border-line lg:col-span-8">
              {p.services.map((s, i) => (
                <li key={s.name} className="group">
                  <a
                    href={p.askHref}
                    className="grid grid-cols-12 items-start gap-4 py-7 transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary sm:py-9"
                  >
                    <span className="col-span-3 font-head text-4xl font-semibold tabular-nums tracking-tight text-primary/30 transition-colors group-hover:text-primary group-focus-within:text-primary sm:col-span-2 sm:text-5xl">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div className="col-span-9 min-w-0 sm:col-span-10">
                      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
                        <h3 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{s.name}</h3>
                        {priceText(s) ? <span className="text-sm font-medium tabular-nums">{priceText(s)}</span> : null}
                      </div>
                      <p className={cn("mt-2 text-base leading-relaxed", quiet(t))}>{s.line}</p>
                      {s.detail ? (
                        <p className={cn("mt-3 max-w-xl text-sm leading-relaxed transition-opacity duration-300 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100", quiet(t))}>
                          {s.detail}
                        </p>
                      ) : null}
                    </div>
                  </a>
                </li>
              ))}
            </ol>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "tabs") {
    const cats = Array.from(new Set(p.services.map((s) => s.category)));
    return (
      <Section block="services_grid" variant={variant} tone={t}>
        <Container>
          <SectionHead title={p.title} intro={p.intro} align="center" />
          <Tabs defaultValue={cats[0]} className="mx-auto max-w-4xl">
            <div className="-mx-4 flex justify-start overflow-x-auto px-4 sm:justify-center">
              <TabsList className="border border-line bg-surface">
                {cats.map((c) => (
                  <TabsTrigger key={c} value={c} className="min-h-10 px-4">
                    {c}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            {cats.map((c) => (
              <TabsContent key={c} value={c} className="mt-8">
                <ul className="overflow-hidden rounded-card border border-line bg-surface text-ink shadow-card">
                  {p.services
                    .filter((s) => s.category === c)
                    .map((s) => {
                      const Icon = ICONS[s.icon ?? "sparkles"];
                      return (
                        <li key={s.name} className="border-b border-line last:border-b-0">
                          <div className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:gap-8 sm:p-8">
                            <div className="min-w-0 flex-1">
                              <h3 className="flex items-center gap-2.5 font-head text-xl font-semibold tracking-tight">
                                <Icon className="size-5 shrink-0 text-primary" aria-hidden="true" />
                                {s.name}
                              </h3>
                              <p className="mt-2 text-base leading-relaxed text-muted">{s.detail ?? s.line}</p>
                            </div>
                            <div className="flex items-center justify-between gap-6 sm:flex-col sm:items-end sm:justify-center">
                              <span className="text-lg font-semibold tabular-nums">{priceText(s) ?? "On request"}</span>
                              <a
                                href={p.askHref}
                                className="group inline-flex min-h-10 items-center gap-1.5 text-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                              >
                                {p.askLabel}
                                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                              </a>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                </ul>
              </TabsContent>
            ))}
          </Tabs>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="services_grid" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {p.services.map((s) => {
            const Icon = ICONS[s.icon ?? "sparkles"];
            return (
              <li key={s.name} className="flex">
                <SpotlightCard className="flex w-full flex-col p-7 transition-transform duration-300 hover:-translate-y-0.5">
                  <h3 className="flex items-center gap-2.5 font-head text-xl font-semibold tracking-tight">
                    <Icon className="size-5 shrink-0 text-primary" aria-hidden="true" />
                    {s.name}
                  </h3>
                  <p className="mt-3 flex-1 text-base leading-relaxed text-muted">{s.line}</p>
                  <div className="mt-6 flex items-center justify-between gap-4 border-t border-line pt-5">
                    <a
                      href={p.askHref}
                      className="group inline-flex min-h-10 items-center gap-1.5 text-sm font-medium text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                    >
                      {p.askLabel}
                      <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                    </a>
                    {priceText(s) ? <span className="text-sm font-medium tabular-nums text-muted">{priceText(s)}</span> : null}
                  </div>
                </SpotlightCard>
              </li>
            );
          })}
        </ul>
      </Container>
    </Section>
  );
}
