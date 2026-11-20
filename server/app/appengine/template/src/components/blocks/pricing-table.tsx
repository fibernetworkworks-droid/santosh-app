// v0.999.51 D1 the kit: her prices. Three layouts: plans (three plan cards, the one she recommends traced by a thin
// moving light), compare (a monthly / yearly switch over a table that compares the plans line by line), list (a plain
// price list in two columns, "from" prices and a line to call for a quote). Only her own prices.
import * as React from "react";
import { ArrowRight, Check, Minus, Phone } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { BorderBeam } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";

export const variants = ["plans", "compare", "list"] as const;
export type PricingTableVariant = (typeof variants)[number];

export interface PricingPlan {
  name: string;
  /** rupees a month */
  monthly: number;
  /** rupees for a whole year, when she offers yearly */
  yearly?: number;
  line: string;
  features: string[];
  /** the plan she recommends */
  highlight?: boolean;
  cta?: string;
}

export interface PriceLine {
  name: string;
  price: number;
  /** "from" before the price */
  from?: boolean;
  note?: string;
}

export interface PricingTableProps {
  variant?: PricingTableVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  plans?: PricingPlan[];
  /** list: one price per service */
  items?: PriceLine[];
  /** the word on the recommended plan */
  badge?: string;
  ctaHref?: string;
  /** a short line under the prices: taxes, trial, how to pay */
  note?: string;
  /** list: the phone line for a quote */
  quote?: { label: string; href: string };
}

export const sample: Required<Omit<PricingTableProps, "variant" | "tone">> = {
  title: "Simple monthly plans",
  intro: "No joining fee. Pause your plan for up to a month when you travel.",
  plans: [
    { name: "Morning batch", monthly: 1800, yearly: 18000, line: "For a steady routine before work.", features: ["6 to 8 am, Monday to Saturday", "Yoga and strength classes", "Locker and shower"], cta: "Start morning batch" },
    { name: "Unlimited", monthly: 2900, yearly: 29000, line: "Any class, any time we are open.", features: ["6 to 8 am, Monday to Saturday", "Yoga and strength classes", "Locker and shower", "Evening and weekend classes", "One diet check-in a month"], highlight: true, cta: "Start unlimited" },
    { name: "Couple", monthly: 5200, yearly: 52000, line: "Two people, one plan, one bill.", features: ["6 to 8 am, Monday to Saturday", "Yoga and strength classes", "Locker and shower", "Evening and weekend classes", "One diet check-in a month", "Two guest passes a month"], cta: "Start couple plan" },
  ],
  items: [
    { name: "Single drop-in class", price: 350 },
    { name: "Personal training, one session", price: 900, from: true, note: "Packs of 10 cost less" },
    { name: "Body composition check", price: 500 },
    { name: "Diet plan, four weeks", price: 2500, note: "With two follow-up calls" },
    { name: "Corporate wellness session", price: 8000, from: true, note: "At your office, up to 40 people" },
    { name: "Pregnancy yoga, monthly", price: 3200, note: "Doctor's note needed" },
  ],
  badge: "Most chosen",
  ctaHref: "#contact",
  note: "Prices include GST. Pay by UPI, card or cash at the front desk.",
  quote: { label: "Call for a group quote", href: "#contact" },
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

type Period = "monthly" | "yearly";

function PlanBody({ plan, href, badge }: { plan: PricingPlan; href: string; badge: string }) {
  return (
    <div className="flex h-full flex-col p-7 sm:p-8">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-head text-xl font-semibold tracking-tight">{plan.name}</h3>
        {plan.highlight ? <Badge tone="primary">{badge}</Badge> : null}
      </div>
      <p className="mt-2 text-sm text-muted">{plan.line}</p>
      <p className="mt-8 flex items-baseline gap-1.5">
        <span className="font-head text-5xl font-semibold tracking-tight tabular-nums">{rupees(plan.monthly)}</span>
        <span className="text-sm text-muted">a month</span>
      </p>
      <ul className="mt-8 flex flex-1 flex-col gap-3 border-t border-line pt-6 text-sm">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2.5">
            <Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <Button asChild size="lg" variant={plan.highlight ? "primary" : "outline"} className="mt-8 w-full">
        <a href={href}>{plan.cta ?? "Choose " + plan.name}</a>
      </Button>
    </div>
  );
}

export default function PricingTable({ variant = "plans", tone, ...rest }: PricingTableProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";
  const [period, setPeriod] = React.useState<Period>("monthly");

  if (variant === "compare") {
    const hasYearly = p.plans.some((x) => x.yearly !== undefined);
    const rows = Array.from(new Set(p.plans.flatMap((x) => x.features)));
    const save = (x: PricingPlan) => (x.yearly ? Math.round((1 - x.yearly / (x.monthly * 12)) * 100) : 0);
    return (
      <Section block="pricing_table" variant={variant} tone={t}>
        <Container>
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
            {hasYearly ? (
              <div role="radiogroup" aria-label="Billing period" className="inline-flex w-fit rounded-full border border-line bg-surface p-1 text-ink">
                {(["monthly", "yearly"] as const).map((k) => (
                  <button
                    key={k}
                    type="button"
                    role="radio"
                    aria-checked={period === k}
                    onClick={() => setPeriod(k)}
                    className={cn(
                      "min-h-10 rounded-full px-5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                      period === k ? "bg-primary text-primary-ink" : "text-muted hover:text-ink",
                    )}
                  >
                    {k === "monthly" ? "Monthly" : "Yearly"}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <div className="mt-10 overflow-x-auto rounded-card border border-line bg-surface text-ink shadow-card">
            <Table className="min-w-160">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-2/5 align-bottom">
                    <span className="sr-only">What you get</span>
                  </TableHead>
                  {p.plans.map((x) => {
                    const price = period === "yearly" && x.yearly ? x.yearly : x.monthly;
                    return (
                      <TableHead key={x.name} className={cn("h-auto py-6 align-top", x.highlight && "bg-primary/5")}>
                        <span className="flex flex-col gap-1 text-ink">
                          <span className="flex items-center gap-2 font-head text-lg font-semibold">
                            {x.name}
                            {x.highlight ? <Badge tone="primary">{p.badge}</Badge> : null}
                          </span>
                          <span key={period} className="animate-fade-in font-head text-3xl font-semibold tabular-nums">{rupees(price)}</span>
                          <span className="text-xs font-normal text-muted">
                            {period === "yearly" && x.yearly ? `a year, you save ${save(x)}%` : "a month"}
                          </span>
                        </span>
                      </TableHead>
                    );
                  })}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((f) => (
                  <TableRow key={f}>
                    <TableCell className="py-4 font-medium">{f}</TableCell>
                    {p.plans.map((x) => (
                      <TableCell key={x.name} className={cn("py-4", x.highlight && "bg-primary/5")}>
                        {x.features.includes(f) ? (
                          <Check className="size-4 text-primary" aria-label="Included" />
                        ) : (
                          <Minus className="size-4 text-muted" aria-label="Not included" />
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
                <TableRow className="hover:bg-transparent">
                  <TableCell />
                  {p.plans.map((x) => (
                    <TableCell key={x.name} className={cn("py-6", x.highlight && "bg-primary/5")}>
                      <Button asChild variant={x.highlight ? "primary" : "outline"}>
                        <a href={p.ctaHref}>Choose</a>
                      </Button>
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <p className={cn("mt-6 text-sm", quiet(t))}>{p.note}</p>
        </Container>
      </Section>
    );
  }

  if (variant === "list") {
    return (
      <Section block="pricing_table" variant={variant} tone={t}>
        <Container>
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
            <div className="lg:col-span-4">
              <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{p.title}</h2>
              <p className={cn("mt-4 text-lg leading-relaxed", quiet(t))}>{p.intro}</p>
              <div className="mt-8 flex flex-col items-start gap-3">
                <Button asChild variant="outline" size="lg" className="group">
                  <a href={p.quote.href}>
                    <Phone className="size-4" aria-hidden="true" />
                    {p.quote.label}
                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                  </a>
                </Button>
                <p className={cn("text-sm", quiet(t))}>{p.note}</p>
              </div>
            </div>
            <ul className="grid gap-x-12 border-t border-line sm:grid-cols-2 lg:col-span-8">
              {p.items.map((x) => (
                <li key={x.name} className="flex items-start justify-between gap-6 border-b border-line py-5">
                  <div className="min-w-0">
                    <h3 className="font-medium leading-snug">{x.name}</h3>
                    {x.note ? <p className={cn("mt-1 text-sm", quiet(t))}>{x.note}</p> : null}
                  </div>
                  <p className="shrink-0 text-right">
                    {x.from ? <span className={cn("block text-xs", quiet(t))}>from</span> : null}
                    <span className="font-head text-xl font-semibold tabular-nums">{rupees(x.price)}</span>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="pricing_table" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} align="center" />
        <ul className="grid items-stretch gap-6 lg:grid-cols-3 lg:gap-5">
          {p.plans.map((x) =>
            x.highlight ? (
              <li key={x.name} className="flex lg:-my-4">
                <BorderBeam className="w-full bg-primary/20 shadow-card">
                  <div className="h-full text-ink">
                    <PlanBody plan={x} href={p.ctaHref} badge={p.badge} />
                  </div>
                </BorderBeam>
              </li>
            ) : (
              <li key={x.name} className="flex">
                <div className="w-full rounded-card border border-line bg-surface text-ink transition-transform duration-300 hover:-translate-y-0.5">
                  <PlanBody plan={x} href={p.ctaHref} badge={p.badge} />
                </div>
              </li>
            ),
          )}
        </ul>
        <p className={cn("mt-12 text-center text-sm", quiet(t))}>{p.note}</p>
      </Container>
    </Section>
  );
}
